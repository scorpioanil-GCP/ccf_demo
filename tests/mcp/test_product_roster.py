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
than at setup. Agents are built with ``model_construct`` for the same reason:
on such a tree the undeclared field is dropped and the tool serves, which is the
hole; a validated-construction test of the field lives beside these.

Tenant, principal, scope, class and agent names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

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


def _agent(key: str, classes: frozenset[str]) -> Any:
    from ccf_runtime.mcp.experience import ExposedAgent

    return ExposedAgent.model_construct(
        definition_key=key,
        definition_version="1.0.0",
        name=key,
        artifact_version="1.0.0",
        archetypes=("analytics_insights",),
        skills=(),
        product_classes=classes,
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
    tmp_path: pathlib.Path,
) -> None:
    """SEC-017 on ``invoke_agent``: refused BY NAME, and the invoker never entered."""
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL

    world = _World(tmp_path)
    served, raised = _call(
        world, frozenset({ON_ROSTER}), INVOKE_AGENT_TOOL, _invoke_args(AGENT_OFF)
    )
    assert served is None, f"served an agent touching {OFF_ROSTER}: {served}"
    refusal = _underlying(raised)  # type: ignore[arg-type]
    assert type(refusal).__name__ == "ProductOutsideRosterRefused", repr(raised)
    assert OFF_ROSTER in str(refusal) and INVOKE_AGENT_TOOL in str(refusal)
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
