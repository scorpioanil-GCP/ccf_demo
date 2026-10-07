"""Within-tenant product entitlement on the token grant (SEC-017; D-IMPL-374 (2)).

``SEC-017`` is the finding of record: ``list_agents``, ``invoke_agent`` and
``get_replay_record`` on the Experience MCP server were authenticated and, after
``SEC-018``, tenant-decided — but WITHIN a tenant any verified principal reached
every agent and the replay record, whatever products the deployment meant that
principal to reach. ``D-IMPL-370`` read the remedy as including within-tenant
entitlement; ``D-IMPL-374`` (2), ruling (a), with the coordinator's option A:

* the grant declares a roster of product CLASS names (schema names) —
  :attr:`~ccf_runtime.mcp.auth.TokenGrant.products`, carried in the verified
  token's ``ccf.products`` claim;
* a principal WITH a roster reaches an agent only when every class in the
  agent's ``consumes ∪ emits`` is on it (``invoke_agent`` refuses by name;
  ``list_agents`` lists only such agents), and the replay record only when the
  deployment declared ``replay_record_product_class`` and it is on the roster;
* a principal WITHOUT a roster is tenant-wide — today's behavior, disclosed as
  the deployment's obligation to declare. No SDK default roster.

=========================================  ===================================
Invariant / finding                        What would fail here
=========================================  ===================================
``SEC-017`` / ``invoke_agent``             a rostered principal dispatches an
                                           agent touching an off-roster class
``SEC-017`` / ``list_agents``              a rostered principal is shown an
                                           agent it may not invoke
``SEC-017`` / ``get_replay_record``        a rostered principal reads a replay
                                           record of an undeclared product
the no-roster control                      absence of a roster narrowed reach
                                           the deployment never restricted
=========================================  ===================================

The roster is carried here as the verified token's claim — the state the bearer
middleware leaves in context after :class:`SourceBackedTokenVerifier` verified a
grant — written with the claim's wire name so that the arrangement exists on a
tree that predates the mechanism and the assertions fail for the hole rather
than at setup. Agents carry their definition's context contract, from which
the SDK derives the classes (fix round 1).

Tenant, principal, scope, class and agent names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import functools
import json
import pathlib
from typing import Any

import anyio
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP

from tests.mcp.guarded_servers import (
    PRINCIPAL,
    SCOPE,
    TENANT,
    _auth,
    _entitlement_world,
    _perspective,
    _verifier,
    authorizer_granting,
)

#: The claim's wire name, spelled as the wire spells it (see module docstring).
PRODUCTS_CLAIM_WIRE_NAME = "ccf.products"
TENANTS_CLAIM_WIRE_NAME = "ccf.tenants"

ON_ROSTER = "class-roster-on"
OFF_ROSTER = "class-roster-off"
AGENT_ON = "agent-roster-on"
AGENT_OFF = "agent-roster-off"


@functools.lru_cache(maxsize=1)
def _base_definition() -> Any:
    from tests.mcp.test_experience_exposable_roster import _bound_world

    return _bound_world("procedure")[0].definition_a


def _agent(key: str, classes: frozenset[str]) -> Any:
    """An exposed agent whose definition's context contract consumes ``classes``.

    Fix round 1 (IMPORTANT 3): the classes are DERIVED from the definition by
    :func:`ccf_runtime.mcp.agent_directory.exposed_agent` — the red commit
    built the entry with ``model_construct`` and a stated set, which an
    entry now refuses.
    """
    from ccf.agents.definitions import ConsumedProduct, ContextContract
    from ccf_runtime.mcp.agent_directory import exposed_agent

    definition = _base_definition().model_copy(
        update={
            "context_contract": ContextContract(
                consumes=tuple(
                    ConsumedProduct(product_class=name, schema_version="1.0.0")
                    for name in sorted(classes)
                )
            )
        }
    )
    return exposed_agent(
        definition, definition_key=key, definition_version="1.0.0", skills=()
    )


class _World:
    """One experience door over a two-agent directory and recording seams."""

    def __init__(
        self, tmp_path: pathlib.Path, **extra: Any
    ) -> None:
        from ccf_runtime.mcp.experience import (
            GET_REPLAY_RECORD_TOOL,
            INVOKE_AGENT_TOOL,
            LIST_AGENTS_TOOL,
            build_experience_server,
        )

        self.invoked: list[str] = []
        self.replay_reads: list[str] = []
        agents = (
            _agent(AGENT_ON, frozenset({ON_ROSTER})),
            _agent(AGENT_OFF, frozenset({ON_ROSTER, OFF_ROSTER})),
        )

        def invoker(**kw: Any) -> str:
            self.invoked.append(kw["definition_key"])
            return json.dumps({"invoked": kw["definition_key"]})

        def reader() -> str:
            self.replay_reads.append("read")
            return json.dumps({"record": "served"})

        source, recorder = _entitlement_world(tmp_path)
        self.server: FastMCP = build_experience_server(
            server_name="roster-experience",
            product_resolver=lambda **kw: None,
            agent_directory=lambda *, tenant: agents,
            agent_invoker=invoker,
            replay_record_reader=reader,
            get_replay_record_description="roster fixture",
            list_agents_description="roster fixture",
            invoke_agent_description="roster fixture",
            replay_record_tenant=TENANT,
            tool_allowlist=frozenset(
                {GET_REPLAY_RECORD_TOOL, INVOKE_AGENT_TOOL, LIST_AGENTS_TOOL}
            ),
            token_verifier=_verifier(),
            auth_settings=_auth(),
            authorizer=authorizer_granting(),
            entitlement_source=source,
            perspective_resolver=_perspective,
            refusal_recorder=recorder,
            **extra,
        )


def _as_caller(roster: frozenset[str] | None) -> Any:
    """Run as a verified caller of TENANT, with or without a declared roster."""
    claims: dict[str, Any] = {TENANTS_CLAIM_WIRE_NAME: [TENANT]}
    if roster is not None:
        claims[PRODUCTS_CLAIM_WIRE_NAME] = sorted(roster)
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process",
                client_id=PRINCIPAL,
                scopes=[SCOPE],
                claims=claims,
            )
        )
    )


def _call(
    world: _World, roster: frozenset[str] | None, tool: str, args: dict[str, Any]
) -> tuple[str | None, BaseException | None]:
    """Call ``tool``; return ``(served text, None)`` or ``(None, refusal)``."""
    reset = _as_caller(roster)
    try:
        try:
            _, structured = anyio.run(world.server.call_tool, tool, args)
        except BaseException as raised:  # noqa: BLE001 - the subject under test
            return None, raised
    finally:
        auth_context_var.reset(reset)
    return str(structured["result"]), None


def _underlying(raised: BaseException) -> BaseException:
    """The typed refusal beneath FastMCP's ToolError wrapping (both chains)."""
    seen: list[BaseException] = []
    current: BaseException | None = raised
    while current is not None and current not in seen:
        if type(current).__name__ == "ProductOutsideRosterRefused":
            return current
        seen.append(current)
        current = current.__cause__ or current.__context__
    return raised


#: The one directory refusal reason the caller is told (fix round 2,
#: I-NEW-1); the specific reason reaches only the server-side log.
OPAQUE = "does not resolve to one this grant's product roster reaches"


def _logged(caplog: Any) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


def _invoke_args(key: str) -> dict[str, Any]:
    return {
        "tenant": TENANT,
        "definition_key": key,
        "definition_version": "1.0.0",
        "skill": "s",
        "arguments": {},
    }


# --- the three holes, as worded ---------------------------------------------


def test_a_rostered_principal_cannot_invoke_an_agent_touching_an_off_roster_product(
    tmp_path: pathlib.Path, caplog: Any
) -> None:
    """SEC-017 on ``invoke_agent``: refused, and the invoker never entered.

    Fix round 2 (I-NEW-1): the caller is told one opaque reason; the
    off-roster class is named in the server-side log only.
    """
    caplog.set_level("INFO", logger="ccf_runtime.mcp.tenancy")
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL

    world = _World(tmp_path)
    served, raised = _call(
        world, frozenset({ON_ROSTER}), INVOKE_AGENT_TOOL, _invoke_args(AGENT_OFF)
    )
    assert served is None, f"served an agent touching {OFF_ROSTER}: {served}"
    refusal = _underlying(raised)  # type: ignore[arg-type]
    assert type(refusal).__name__ == "ProductOutsideRosterRefused", repr(raised)
    assert OPAQUE in str(refusal) and INVOKE_AGENT_TOOL in str(refusal)
    assert OFF_ROSTER not in str(refusal)
    assert OFF_ROSTER in _logged(caplog)
    assert world.invoked == []
    # Positive control in the same world: the on-roster agent IS dispatched,
    # so the refusal above is the roster's and not a broken door's.
    served, raised = _call(
        world, frozenset({ON_ROSTER}), INVOKE_AGENT_TOOL, _invoke_args(AGENT_ON)
    )
    assert raised is None, repr(raised)
    assert world.invoked == [AGENT_ON]


def test_a_rostered_principal_is_listed_only_the_agents_it_may_invoke(
    tmp_path: pathlib.Path,
) -> None:
    """SEC-017 on ``list_agents``: an off-roster agent is not disclosed."""
    from ccf_runtime.mcp.experience import LIST_AGENTS_TOOL

    world = _World(tmp_path)
    served, raised = _call(
        world, frozenset({ON_ROSTER}), LIST_AGENTS_TOOL, {"tenant": TENANT}
    )
    assert raised is None, repr(raised)
    listed = [a["definition_key"] for a in json.loads(served or "")["agents"]]
    assert listed == [AGENT_ON], listed


def test_a_rostered_principal_cannot_read_an_undeclared_replay_record(
    tmp_path: pathlib.Path,
) -> None:
    """SEC-017 on ``get_replay_record``: no declared product class -> refused by name.

    An unrostered reach is the hole: the record belongs to no class the
    deployment named, so a principal whose reach is bounded by a roster has
    nothing on that roster that admits it.
    """
    from ccf_runtime.mcp.experience import GET_REPLAY_RECORD_TOOL

    world = _World(tmp_path)
    served, raised = _call(
        world, frozenset({ON_ROSTER}), GET_REPLAY_RECORD_TOOL, {}
    )
    assert served is None, f"served the replay record: {served}"
    refusal = _underlying(raised)  # type: ignore[arg-type]
    assert type(refusal).__name__ == "ProductOutsideRosterRefused", repr(raised)
    assert "replay_record_product_class" in str(refusal)
    assert world.replay_reads == []


# --- the control: no roster is tenant-wide ----------------------------------


def test_a_principal_without_a_roster_still_reaches_tenant_wide(
    tmp_path: pathlib.Path,
) -> None:
    """The control: no declared roster is today's tenant-wide reach, unchanged.

    Green on every tree by design — it is what the three tests above are
    measured against. Without it a door that refused everything would pass
    them.
    """
    from ccf_runtime.mcp.experience import (
        GET_REPLAY_RECORD_TOOL,
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
    )

    world = _World(tmp_path)
    served, raised = _call(world, None, LIST_AGENTS_TOOL, {"tenant": TENANT})
    assert raised is None, repr(raised)
    listed = sorted(a["definition_key"] for a in json.loads(served or "")["agents"])
    assert listed == sorted([AGENT_ON, AGENT_OFF])
    _, raised = _call(world, None, INVOKE_AGENT_TOOL, _invoke_args(AGENT_OFF))
    assert raised is None, repr(raised)
    assert world.invoked == [AGENT_OFF]
    _, raised = _call(world, None, GET_REPLAY_RECORD_TOOL, {})
    assert raised is None, repr(raised)
    assert world.replay_reads == ["read"]


# --- the mechanism's edges (written with the fix) ---------------------------


def test_the_grant_declares_no_roster_by_default_and_that_means_tenant_wide() -> None:
    """``None`` is undeclared — and it writes no claim, so it cannot read as empty."""
    from ccf_runtime.mcp.auth import TokenGrant, product_claims

    grant = TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,))
    assert grant.products is None
    assert product_claims(grant) == {}


def test_the_verifier_carries_a_declared_roster_into_the_token() -> None:
    """Source grant -> verifier -> claim -> ``verified_grant``: one flow, no loss."""
    from ccf_runtime.authz.product_entitlement import verified_grant
    from ccf_runtime.mcp.auth import (
        PRODUCT_CLAIM,
        SourceBackedTokenVerifier,
        StaticTokenSource,
        TokenGrant,
        granted_products,
    )

    assert PRODUCT_CLAIM == PRODUCTS_CLAIM_WIRE_NAME
    verifier = SourceBackedTokenVerifier(
        source=StaticTokenSource(
            grants={
                "rostered": TokenGrant(
                    client_id=PRINCIPAL,
                    scopes=(SCOPE,),
                    tenants=frozenset({TENANT}),
                    products=frozenset({ON_ROSTER}),
                ),
                "open": TokenGrant(
                    client_id=PRINCIPAL,
                    scopes=(SCOPE,),
                    tenants=frozenset({TENANT}),
                ),
            }
        )
    )
    rostered = anyio.run(verifier.verify_token, "rostered")
    unrostered = anyio.run(verifier.verify_token, "open")
    assert rostered is not None and unrostered is not None
    assert granted_products(rostered) == frozenset({ON_ROSTER})
    assert granted_products(unrostered) is None
    reset = auth_context_var.set(AuthenticatedUser(rostered))
    try:
        assert verified_grant().products == frozenset({ON_ROSTER})
    finally:
        auth_context_var.reset(reset)


def test_an_empty_or_malformed_roster_reaches_no_product() -> None:
    """Declared-but-empty and present-but-unparseable both restrict; neither widens."""
    from ccf_runtime.mcp.auth import PRODUCT_CLAIM, granted_products

    def token(claim: Any) -> AccessToken:
        return AccessToken(
            token="t", client_id=PRINCIPAL, scopes=[SCOPE],
            claims={PRODUCT_CLAIM: claim},
        )

    assert granted_products(token([])) == frozenset()
    assert granted_products(token("class-roster-on")) == frozenset()
    assert granted_products(token(None)) == frozenset()


def test_an_empty_roster_invokes_nothing_and_lists_nothing(
    tmp_path: pathlib.Path,
) -> None:
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL, LIST_AGENTS_TOOL

    world = _World(tmp_path)
    served, raised = _call(world, frozenset(), LIST_AGENTS_TOOL, {"tenant": TENANT})
    assert raised is None, repr(raised)
    assert json.loads(served or "")["agents"] == []
    _, raised = _call(world, frozenset(), INVOKE_AGENT_TOOL, _invoke_args(AGENT_ON))
    assert type(_underlying(raised)).__name__ == "ProductOutsideRosterRefused"  # type: ignore[arg-type]
    assert world.invoked == []


def test_a_rostered_principal_is_refused_an_agent_that_declares_no_classes(
    tmp_path: pathlib.Path, caplog: Any
) -> None:
    """Undeclared is not on any roster: refused by name, and not listed."""
    from ccf_runtime.mcp.experience import (
        INVOKE_AGENT_TOOL,
        LIST_AGENTS_TOOL,
        ExposedAgent,
    )

    caplog.set_level("INFO", logger="ccf_runtime.mcp.tenancy")
    world = _World(tmp_path)
    undeclared = ExposedAgent(
        definition_key="agent-undeclared",
        definition_version="1.0.0",
        name="agent-undeclared",
        artifact_version="1.0.0",
        archetypes=("analytics_insights",),
        skills=(),
    )
    assert undeclared.product_classes is None
    source, recorder = _entitlement_world(tmp_path / "undeclared")
    from ccf_runtime.mcp.experience import build_experience_server

    server = build_experience_server(
        server_name="roster-undeclared",
        product_resolver=lambda **kw: None,
        agent_directory=lambda *, tenant: (undeclared,),
        agent_invoker=lambda **kw: world.invoked.append("x") or "{}",
        list_agents_description="roster fixture",
        invoke_agent_description="roster fixture",
        tool_allowlist=frozenset({INVOKE_AGENT_TOOL, LIST_AGENTS_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )
    world.server = server
    _, raised = _call(
        world, frozenset({ON_ROSTER}), INVOKE_AGENT_TOOL,
        _invoke_args("agent-undeclared"),
    )
    refusal = _underlying(raised)  # type: ignore[arg-type]
    assert type(refusal).__name__ == "ProductOutsideRosterRefused"
    assert OPAQUE in str(refusal) and "agent-undeclared" not in str(refusal)
    assert "carries no product classes derived" in _logged(caplog)
    served, raised = _call(world, frozenset({ON_ROSTER}), LIST_AGENTS_TOOL, {"tenant": TENANT})
    assert raised is None and json.loads(served or "")["agents"] == []
    assert world.invoked == []


def test_a_rostered_principal_is_refused_an_agent_the_directory_does_not_expose(
    tmp_path: pathlib.Path, caplog: Any
) -> None:
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL

    caplog.set_level("INFO", logger="ccf_runtime.mcp.tenancy")
    world = _World(tmp_path)
    _, raised = _call(
        world, frozenset({ON_ROSTER}), INVOKE_AGENT_TOOL, _invoke_args("agent-absent")
    )
    refusal = _underlying(raised)  # type: ignore[arg-type]
    assert type(refusal).__name__ == "ProductOutsideRosterRefused"
    assert OPAQUE in str(refusal) and "agent-absent" not in str(refusal)
    assert "not exposed" in _logged(caplog)
    assert world.invoked == []


def test_a_rostered_invoke_with_no_directory_is_refused(
    tmp_path: pathlib.Path, caplog: Any
) -> None:
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL, build_experience_server

    caplog.set_level("INFO", logger="ccf_runtime.mcp.tenancy")
    world = _World(tmp_path)
    source, recorder = _entitlement_world(tmp_path / "nodir")
    world.server = build_experience_server(
        server_name="roster-nodir",
        product_resolver=lambda **kw: None,
        agent_invoker=lambda **kw: world.invoked.append("x") or "{}",
        invoke_agent_description="roster fixture",
        tool_allowlist=frozenset({INVOKE_AGENT_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )
    _, raised = _call(world, frozenset({ON_ROSTER}), INVOKE_AGENT_TOOL, _invoke_args(AGENT_ON))
    refusal = _underlying(raised)  # type: ignore[arg-type]
    assert type(refusal).__name__ == "ProductOutsideRosterRefused"
    assert OPAQUE in str(refusal)
    assert "no agent directory" in _logged(caplog)
    assert world.invoked == []
    # And the unrostered caller is unaffected by the absent directory.
    _, raised = _call(world, None, INVOKE_AGENT_TOOL, _invoke_args(AGENT_ON))
    assert raised is None, repr(raised)


def test_the_replay_record_follows_its_declared_class(tmp_path: pathlib.Path) -> None:
    """Declared and on the roster: served. Declared and off it: refused by name."""
    from ccf_runtime.mcp.experience import GET_REPLAY_RECORD_TOOL

    world = _World(tmp_path, replay_record_product_class=ON_ROSTER)
    _, raised = _call(world, frozenset({ON_ROSTER}), GET_REPLAY_RECORD_TOOL, {})
    assert raised is None, repr(raised)
    assert world.replay_reads == ["read"]
    _, raised = _call(world, frozenset({OFF_ROSTER}), GET_REPLAY_RECORD_TOOL, {})
    refusal = _underlying(raised)  # type: ignore[arg-type]
    assert type(refusal).__name__ == "ProductOutsideRosterRefused"
    assert ON_ROSTER in str(refusal) and "outside the roster" in str(refusal)
    assert world.replay_reads == ["read"]


def test_a_replay_class_for_an_unexposed_tool_is_refused(tmp_path: pathlib.Path) -> None:
    import pytest

    from ccf_runtime.mcp.experience import LIST_AGENTS_TOOL, build_experience_server

    source, recorder = _entitlement_world(tmp_path)
    with pytest.raises(ValueError, match="replay_record_product_class"):
        build_experience_server(
            server_name="roster-inert",
            product_resolver=lambda **kw: None,
            agent_directory=lambda *, tenant: (),
            list_agents_description="roster fixture",
            replay_record_product_class=ON_ROSTER,
            tool_allowlist=frozenset({LIST_AGENTS_TOOL}),
            token_verifier=_verifier(),
            auth_settings=_auth(),
            authorizer=authorizer_granting(),
            entitlement_source=source,
            perspective_resolver=_perspective,
            refusal_recorder=recorder,
        )
