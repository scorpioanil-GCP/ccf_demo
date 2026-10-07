"""SEC-017 fix round 1: one roster rule on every MCP surface that knows a class.

``D-IMPL-374`` (2), coordinator rulings on the first review:

* **IMPORTANT 1** — the roster on :attr:`~ccf_runtime.mcp.auth.TokenGrant.products`
  binds every surface where a product class is known at the call, not only the
  agent and replay tools: the Experience door's ``context_product`` resource,
  ``get_context`` and ``get_lineage``, and the egress door's product resource,
  product tool and addressed resource.
* **IMPORTANT 2** — the roster refuses BEFORE the authorizer mints, so a refused
  call leaves no ``authz_decision`` allow in the Control Plane audit trail.
* **IMPORTANT 3** — :attr:`~ccf_runtime.mcp.experience.ExposedAgent.product_classes`
  is derived from the agent definition's context contract; a directory entry
  that declares its own set is refused at build, by name.

=========================================  ===================================
Invariant / finding                        What would fail here
=========================================  ===================================
one rule, every class-knowing surface      a rostered principal is admitted to
                                           an off-roster class through a door
                                           the roster was never wired to
no allow for a refused call                the audit trail records an allow
                                           for a call the roster refused
derived, never declared                    a directory narrows an agent's
                                           classes and widens a roster's reach
=========================================  ===================================

Every assertion is evidence of the hole on a tree without the rule: the
authorizer is reached and records an allow, and the seam behind the surface is
entered, for a class the principal's roster does not name.

Tenant, principal, scope, class and agent names are test deployment vocabulary.
"""

from __future__ import annotations

import pathlib
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf_runtime.mcp.auth import PRODUCT_CLAIM, TENANT_CLAIM
from tests.mcp.guarded_servers import (
    PRINCIPAL,
    PRODUCT_CLASS,
    SCOPE,
    TENANT,
    _auth,
    _entitlement_world,
    _perspective,
    _verifier,
    authorizer_granting,
)

#: A class the roster names — never the one the surfaces below serve.
ROSTERED = "class-roster-elsewhere"


def _as_rostered(roster: frozenset[str] | None) -> Any:
    claims: dict[str, Any] = {TENANT_CLAIM: [TENANT]}
    if roster is not None:
        claims[PRODUCT_CLAIM] = sorted(roster)
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process", client_id=PRINCIPAL, scopes=[SCOPE], claims=claims
            )
        )
    )


def _allows(registry: ControlPlaneRegistry) -> int:
    """How many ``authz_decision`` ALLOW events the audit trail holds."""
    return sum(
        1
        for event in registry.audit_log.events()
        if getattr(event, "action", None) == "authz_decision"
        and getattr(event, "resolved", None) is True
    )


def _drive(operation: Any, roster: frozenset[str] | None) -> BaseException | None:
    reset = _as_rostered(roster)
    try:
        try:
            operation()
        except BaseException as raised:  # noqa: BLE001 - the subject under test
            return raised
        return None
    finally:
        auth_context_var.reset(reset)


def _roster_refusal(raised: BaseException | None) -> BaseException | None:
    seen: list[BaseException] = []
    current = raised
    while current is not None and current not in seen:
        if type(current).__name__ == "ProductOutsideRosterRefused":
            return current
        seen.append(current)
        current = current.__cause__ or current.__context__
    return None


class _Seams:
    def __init__(self) -> None:
        self.entered: list[str] = []

    def record(self, name: str, result: Any = "{}") -> Any:
        def seam(*args: Any, **kwargs: Any) -> Any:
            self.entered.append(name)
            if isinstance(result, BaseException):
                raise result
            return result

        return seam


def _experience(tmp_path: pathlib.Path, registry: ControlPlaneRegistry, seams: _Seams) -> Any:
    from ccf_runtime.mcp.experience import (
        ExperienceProductNotServable,
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        build_experience_server,
    )

    source, recorder = _entitlement_world(tmp_path)
    return build_experience_server(
        server_name="roster-surfaces-experience",
        product_resolver=seams.record(
            "product_resolver", ExperienceProductNotServable("absent")
        ),
        context_provider=seams.record("context_provider"),
        lineage_provider=seams.record("lineage_provider"),
        get_context_description="roster fixture",
        get_lineage_description="roster fixture",
        entitled_product_class=PRODUCT_CLASS,
        lineage_tenant=TENANT,
        tool_allowlist=frozenset({GET_CONTEXT_TOOL, GET_LINEAGE_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(registry=registry),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )


def _egress(tmp_path: pathlib.Path, registry: ControlPlaneRegistry, seams: _Seams) -> Any:
    from ccf_runtime.mcp.egress import build_egress_server

    source, recorder = _entitlement_world(tmp_path)
    return build_egress_server(
        server_name="roster-surfaces-egress",
        resolver=seams.record("resolver", LookupError("absent")),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(registry=registry),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
        expose_product_resource=True,
        expose_product_tool=True,
        product_tool_description="roster fixture",
    )


def _calls() -> dict[str, Any]:
    """Each class-knowing MCP surface, called for :data:`PRODUCT_CLASS`."""
    from ccf_runtime.mcp.egress import (
        PRODUCT_REQUEST_TOOL,
        product_uri,
    )
    from ccf_runtime.mcp.experience import (
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        experience_product_uri,
    )

    egress_uri = product_uri(tenant=TENANT, product_class=PRODUCT_CLASS, version="1.0.0")
    return {
        "experience:context_product": (
            "experience",
            lambda s: anyio.run(
                s.read_resource,
                experience_product_uri(
                    tenant=TENANT, product_class=PRODUCT_CLASS, version="1.0.0"
                ),
            ),
        ),
        "experience:get_context": (
            "experience",
            lambda s: anyio.run(
                s.call_tool, GET_CONTEXT_TOOL, {"tenant": TENANT, "entity": "e-1"}
            ),
        ),
        "experience:get_lineage": (
            "experience",
            lambda s: anyio.run(s.call_tool, GET_LINEAGE_TOOL, {}),
        ),
        "egress:product_resource": (
            "egress",
            lambda s: anyio.run(s.read_resource, egress_uri),
        ),
        "egress:product_tool": (
            "egress",
            lambda s: anyio.run(
                s.call_tool,
                PRODUCT_REQUEST_TOOL,
                {
                    "tenant": TENANT,
                    "product_class": PRODUCT_CLASS,
                    "version": "1.0.0",
                    "request": "r",
                    "subject": "s",
                    "intent": "i",
                    "freshness": "f",
                    "asked_at": "2026-05-12T00:00:00+00:00",
                },
            ),
        ),
        "egress:addressed_resource": (
            "egress",
            lambda s: anyio.run(s.read_resource, f"{egress_uri}/q/e30"),
        ),
    }


SURFACES = tuple(_calls())


@pytest.mark.parametrize("surface", SURFACES)
def test_a_rostered_principal_is_refused_an_off_roster_class_on_every_surface(
    surface: str, tmp_path: pathlib.Path
) -> None:
    """IMPORTANT 1 + 2: refused by name, before the authorizer, before the seam."""
    builder, call = _calls()[surface]
    registry = ControlPlaneRegistry()
    seams = _Seams()
    server = (_experience if builder == "experience" else _egress)(
        tmp_path, registry, seams
    )
    before = _allows(registry)
    raised = _drive(lambda: call(server), frozenset({ROSTERED}))
    refusal = _roster_refusal(raised)
    assert refusal is not None, (
        f"{surface}: not refused by the roster (raised {raised!r}); the"
        f" authorizer recorded {_allows(registry) - before} allow(s) and the"
        f" seams entered were {seams.entered}"
    )
    assert PRODUCT_CLASS in str(refusal)
    assert _allows(registry) == before, "an allow was recorded for a refused call"
    assert seams.entered == []


@pytest.mark.parametrize("surface", SURFACES)
def test_the_same_call_without_a_roster_reaches_the_authorizer(
    surface: str, tmp_path: pathlib.Path
) -> None:
    """The control: no roster, same call — the authorizer allows and records it."""
    builder, call = _calls()[surface]
    registry = ControlPlaneRegistry()
    seams = _Seams()
    server = (_experience if builder == "experience" else _egress)(
        tmp_path, registry, seams
    )
    before = _allows(registry)
    raised = _drive(lambda: call(server), None)
    assert _roster_refusal(raised) is None
    assert _allows(registry) == before + 1


def test_a_directory_cannot_declare_an_agents_product_classes(
    tmp_path: pathlib.Path,
) -> None:
    """IMPORTANT 3: a declared (narrower) set is refused at build, by name.

    The agent's definition names two classes; the directory entry declares
    one. Accepting that entry lets a principal rostered on the one class
    dispatch an agent that also reaches the other.
    """
    from ccf_runtime.mcp.experience import (
        INVOKE_AGENT_TOOL,
        ExposedAgent,
        build_experience_server,
    )

    with pytest.raises(ValueError, match="derived") as refused:
        entry = ExposedAgent(
            definition_key="agent-subset",
            definition_version="1.0.0",
            name="agent-subset",
            artifact_version="1.0.0",
            archetypes=("analytics_insights",),
            skills=(),
            # The definition's contract names {ROSTERED, PRODUCT_CLASS}.
            product_classes=frozenset({ROSTERED}),
        )
        invoked: list[str] = []
        source, recorder = _entitlement_world(tmp_path)
        server = build_experience_server(
            server_name="roster-subset",
            product_resolver=lambda **kw: None,
            agent_directory=lambda *, tenant: (entry,),
            agent_invoker=lambda **kw: invoked.append(kw["definition_key"]) or "{}",
            invoke_agent_description="roster fixture",
            tool_allowlist=frozenset({INVOKE_AGENT_TOOL}),
            token_verifier=_verifier(),
            auth_settings=_auth(),
            authorizer=authorizer_granting(),
            entitlement_source=source,
            perspective_resolver=_perspective,
            refusal_recorder=recorder,
        )
        raised = _drive(
            lambda: anyio.run(
                server.call_tool,
                INVOKE_AGENT_TOOL,
                {
                    "tenant": TENANT,
                    "definition_key": "agent-subset",
                    "definition_version": "1.0.0",
                    "skill": "s",
                    "arguments": {},
                },
            ),
            frozenset({ROSTERED}),
        )
        pytest.fail(
            "a directory-declared subset was accepted at build and the agent"
            f" was dispatched for a rostered principal: invoked={invoked},"
            f" raised={raised!r}"
        )
    assert "agent-subset" in str(refused.value)


@pytest.mark.parametrize("tool", ("invoke_agent", "get_replay_record"))
def test_a_roster_refused_agent_or_replay_call_records_no_allow(
    tool: str, tmp_path: pathlib.Path
) -> None:
    """IMPORTANT 2 on the first round's two refusing tools.

    The roster refusal used to run inside the body — after the authorizer had
    already recorded an allow and a capability had been minted from it.
    """
    from ccf_runtime.mcp.experience import (
        GET_REPLAY_RECORD_TOOL,
        INVOKE_AGENT_TOOL,
        build_experience_server,
    )

    registry = ControlPlaneRegistry()
    seams = _Seams()
    source, recorder = _entitlement_world(tmp_path)
    server = build_experience_server(
        server_name="roster-audit",
        product_resolver=lambda **kw: None,
        # The directory exposes nothing, so a rostered invoke is refused
        # whatever the agent: the subject is WHERE the refusal happens.
        agent_directory=lambda *, tenant: (),
        agent_invoker=seams.record("invoker"),
        replay_record_reader=seams.record("replay_reader"),
        invoke_agent_description="roster fixture",
        get_replay_record_description="roster fixture",
        replay_record_tenant=TENANT,
        tool_allowlist=frozenset({INVOKE_AGENT_TOOL, GET_REPLAY_RECORD_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(registry=registry),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )
    args: dict[str, Any] = (
        {
            "tenant": TENANT,
            "definition_key": "agent-absent",
            "definition_version": "1.0.0",
            "skill": "s",
            "arguments": {},
        }
        if tool == INVOKE_AGENT_TOOL
        else {}
    )
    before = _allows(registry)
    raised = _drive(
        lambda: anyio.run(server.call_tool, tool, args), frozenset({ROSTERED})
    )
    assert _roster_refusal(raised) is not None, repr(raised)
    assert _allows(registry) == before, (
        f"{tool}: the authorizer recorded an allow for a call the roster refused"
    )
    assert seams.entered == []
