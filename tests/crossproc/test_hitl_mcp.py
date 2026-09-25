"""The HITL MCP transport (D-IMPL-20): queues as Resources, authority as Tools.

CLAUDE.md §8.2 (SDK-defined) and the D-IMPL-20 ruling: MCP server endpoints
exposing the HITL queues are the Experience-Layer primary; the typed queue
carries authority, and **every action tool requires a complete
HumanPrincipalBinding — the MCP surface cannot bypass audit**. The child
runs the authenticated HITL server over a live transport and a real
``ApprovalGate``; this process acts across a real process boundary.

Every assertion below is drafted from *what would fail here*:

==========================================  ==================================
Invariant / requirement                     What would fail here
==========================================  ==================================
binding by construction (D-IMPL-21, D-22)   an action tool call missing a
                                            binding field would produce an
                                            unbound human action instead of a
                                            typed refusal
replay dimension 2 (CLAUDE.md §8.2)         a completed action's block would
                                            not land verbatim on the record's
                                            ``policy_bindings.hitl_actions``
tenant partitioning (D-23, T-07-21)         one tenant's queue view would show
                                            another tenant's pending events
role separation (§7.1, T-07-22)             the HITL role would merge with, or
                                            import, a sibling MCP role
auth posture (D-26)                         an unrecognised credential would
                                            reach the authority surface
==========================================  ==================================

Every domain value — tenant, event, approver identity, action instant —
comes from ``tests/fixtures/banking/hitl.yaml`` by way of the child's shared
builders.
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from mcp.client.session import ClientSession
from mcp.types import TextResourceContents
from pydantic import AnyUrl

from ccf.contracts.canonical import canonical_bytes
from ccf.hitl.approval_gate import HitlActionRecord
from ccf.hitl.transport import HitlActionSubmission
from ccf.mcp.client import SyncMcpBridge, run_with_session
from ccf.mcp.errors import McpServerUnreachable

from crossproc.servers.mcp_hitl_child import (
    authorized_http_client,
    pending_event,
    principal_binding,
)
from crossproc.servers.wide_authorizer import wide_authorizer

pytestmark = pytest.mark.crossproc

CHILD = Path(__file__).resolve().parent / "servers" / "mcp_hitl_child.py"

CALL_TIMEOUT_SECONDS = 30.0

with_child = pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)


@pytest.fixture
def bridge() -> Iterator[SyncMcpBridge]:
    """One bounded sync bridge per test, closed on teardown."""
    with SyncMcpBridge(call_timeout_seconds=CALL_TIMEOUT_SECONDS) as bridge:
        yield bridge


def _read_text(bridge: SyncMcpBridge, url: str, uri: str) -> str:
    """Read one resource as text over the authenticated transport."""

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return bridge.run(
        run_with_session(
            url=url,
            operation=operation,
            http_client_factory=authorized_http_client,
        )
    )


def _call_tool(
    bridge: SyncMcpBridge, url: str, name: str, arguments: dict[str, Any]
) -> tuple[bool, str]:
    """Call one tool; return ``(is_error, first text content)``."""

    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(name, arguments)
        texts = [
            content.text
            for content in result.content
            if hasattr(content, "text")
        ]
        return bool(result.isError), texts[0] if texts else ""

    return bridge.run(
        run_with_session(
            url=url,
            operation=operation,
            http_client_factory=authorized_http_client,
        )
    )


def _action_arguments() -> dict[str, Any]:
    """The complete action-tool argument set, from the shared builders."""
    event = pending_event()
    binding = principal_binding(product_content_hash=event.product_content_hash)
    # D-IMPL-353 §2 P6: the wire carries no subject, assurance or time — the
    # door mints those from the capability, the verified claims and its clock.
    return {
        "tenant": event.tenant,
        "event_key": event.event_key,
        "action": "approve",
        "product_content_hash": binding.product_content_hash,
    }


# --- the structural claims the module docstring makes -----------------------


def test_the_hitl_module_holds_no_primitive_and_no_graph_handle() -> None:
    """The server fronts an injected queue view; it owns no gate and no fabric.

    Asserted against the module's source: an import of the gate, the graph,
    or a sibling MCP role would be the first step of the merge or bypass the
    role-separation suite exists to prevent (T-07-22).
    """
    import ccf_runtime.mcp.hitl_server as hitl_server

    source = inspect.getsource(hitl_server)
    for forbidden in (
        "ccf.graph",
        "ccf.hitl.approval_gate",
        "ApprovalGate",
        "GraphWriter",
        "GraphReader",
        "InMemoryHitlTransport",
    ):
        assert forbidden not in source, (
            f"{forbidden} appears in the HITL server's source; the server"
            " holds injected Protocol callables only (07-09 key link;"
            " CLAUDE.md §8.2)"
        )


def test_the_hitl_docstring_states_the_authority_separation() -> None:
    """D-IMPL-20: this is the primary authority channel, and it says so."""
    import ccf_runtime.mcp.hitl_server as hitl_server

    docstring = hitl_server.__doc__ or ""
    assert "D-IMPL-20" in docstring
    assert "authority" in docstring
    assert "notify-only" in docstring


# --- the cross-process round trips ------------------------------------------


@with_child
def test_pending_events_are_readable_as_a_tenant_resource(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """The queue is an MCP Resource, per tenant, without consuming anything."""
    from ccf_runtime.mcp.hitl_server import hitl_queue_uri

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    event = pending_event()

    body = _read_text(bridge, url, hitl_queue_uri(tenant=event.tenant))

    view = json.loads(body)
    assert view["tenant"] == event.tenant
    (pending,) = view["events"]
    assert pending == json.loads(canonical_bytes(event).decode("utf-8"))


@with_child
def test_a_foreign_tenant_sees_an_empty_queue(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-23 / T-07-21: two tenants' queues never interleave on this surface."""
    from ccf_runtime.mcp.hitl_server import hitl_queue_uri

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    event = pending_event()

    body = _read_text(
        bridge, url, hitl_queue_uri(tenant=f"{event.tenant}-not-this-one")
    )

    assert json.loads(body)["events"] == []


@with_child
def test_a_bound_action_lands_on_replay_dimension_two(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """The authority round trip: approve with a complete binding, replay it.

    The expected dimension-2 block is recomputed *here* from the shared
    builders — the exact ``HitlActionRecord`` the gate serializes — so a
    server that dropped, paraphrased, or re-serialized the block fails byte
    for byte (the 07-05 verbatim discipline).
    """
    from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    event = pending_event()
    binding = principal_binding(product_content_hash=event.product_content_hash)

    is_error, body = _call_tool(
        bridge, url, SUBMIT_HITL_ACTION_TOOL, _action_arguments()
    )

    assert not is_error, body
    payload = json.loads(body)
    assert payload["refused"] is False
    assert payload["approved"] is True

    record = json.loads(payload["replay_record"])
    block = record["policy_bindings"]["hitl_actions"]
    # The door minted the binding from the token's claims and its clock — both
    # the fixture's, so the recorded binding IS `binding`. The one value a
    # test cannot precompute is the authorizer's decision id (a content
    # address of its audit event); it is read back, shape-checked, and the
    # block is then recomputed byte for byte around it — the event class and
    # state ref the action answered are the fixture event's own.
    decision_id = json.loads(block)["submission"]["authorizing_decision_id"]
    assert isinstance(decision_id, str) and len(decision_id) == 64, decision_id
    expected_block = canonical_bytes(
        HitlActionRecord(
            event=event,
            submission=HitlActionSubmission(
                event_key=event.event_key,
                action="approve",
                principal=binding,
                annotation=None,
                # The transport's recorded copy: which event the action
                # answered (the Tier-0 verdict→target stamps) and which
                # authorization produced it (D-IMPL-353 §9).
                answered_event_class=event.event_class,
                answered_workflow_state_ref=event.workflow_state_ref,
                authorizing_decision_id=decision_id,
            ),
            approved=True,
        )
    ).decode("utf-8")
    assert block == expected_block


@with_child
def test_an_action_missing_a_binding_field_is_refused_typed(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-22: the MCP surface cannot produce an unbound human action.

    A call omitting one binding field is a tool-level typed refusal — and
    the event is still pending afterwards, so nothing was consumed, recorded,
    or resolved on the refused path.
    """
    from ccf_runtime.mcp.hitl_server import (
        SUBMIT_HITL_ACTION_TOOL,
        hitl_queue_uri,
    )

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    event = pending_event()
    incomplete = _action_arguments()
    del incomplete["product_content_hash"]

    is_error, body = _call_tool(
        bridge, url, SUBMIT_HITL_ACTION_TOOL, incomplete
    )

    assert is_error, body
    # Nothing happened: the pending event survived the refused call.
    view = json.loads(_read_text(bridge, url, hitl_queue_uri(tenant=event.tenant)))
    assert [item["event_key"] for item in view["events"]] == [event.event_key]


@with_child
def test_a_caller_typed_subject_has_no_effect_on_the_recorded_binding(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """D-IMPL-353 §2 P6, across the wire: the subject is the capability's.

    The tool has no ``subject_id`` argument. **Measured at the join:** FastMCP's
    argument model DROPS unknown wire arguments rather than refusing them, so
    a call naming one is not a tool error — it is a valid approval by the
    verified officer in which the typed value reaches nothing. What this
    test therefore holds is the security property: the recorded binding's
    subject is the verified identity, and the caller-typed value appears
    nowhere in the replay record. Refusing unknown arguments at the MCP
    boundary (``extra=forbid`` on the tool's argument model) is recorded as
    join finding ``SEC353-J-01`` for a ruling; the HTTP door already refuses
    them (``extra=forbid`` on ``HitlActionRequest``).
    """
    from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL

    url = f"http://127.0.0.1:{child_server_port}/mcp"
    event = pending_event()
    binding = principal_binding(product_content_hash=event.product_content_hash)
    typed = _action_arguments()
    typed["subject_id"] = "someone-else-entirely"
    is_error, body = _call_tool(bridge, url, SUBMIT_HITL_ACTION_TOOL, typed)
    assert not is_error, body
    payload = json.loads(body)
    record = json.loads(payload["replay_record"])
    block = record["policy_bindings"]["hitl_actions"]
    recorded = json.loads(block)["submission"]["principal"]["approver"]
    assert recorded["subject_id"] == binding.approver.subject_id
    assert "someone-else-entirely" not in payload["replay_record"]


def _unit_server(tmp_path: Path, action_route: Any) -> Any:
    """An authenticated HITL server over stub seams, for direct tool calls."""
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    from ccf.hitl.transport import PendingHitlEvent
    from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
    from ccf_runtime.mcp.hitl_server import build_hitl_server

    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
            {
                "unit-token": {
                    "client_id": "auditor-1",
                    "scopes": ["h"],
                    "tenants": [UNIT_TENANT],
                    "authentication": {"method": "bearer-token", "assurance_level": "dev", "identity_provider_ref": "idp://unit/dev-token-file", "session_ref": "unit-session-1"},
                }
            }
        ),
        encoding="utf-8",
    )

    def queue_view(authorized: Any) -> tuple[PendingHitlEvent, ...]:
        return ()

    return build_hitl_server(
        server_name="unit-hitl",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=token_file)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://unit.invalid/mcp"),
            required_scopes=["h"],
        ),
        authorizer=wide_authorizer(scopes=["h"]),
        clock=lambda: UNIT_CLOCK,
    )


#: The instant the unit door stamps on every action (D-IMPL-353 §2 P6).
UNIT_CLOCK = datetime(2026, 7, 30, 12, tzinfo=UTC)


#: The tenant the unit-level HITL fixtures act on. One spelling, so the
#: credential's scope and the tool argument cannot drift apart (`SEC-018`).
UNIT_TENANT = "unit-tenant"


def _unit_arguments() -> dict[str, Any]:
    return {
        "tenant": UNIT_TENANT,
        "event_key": "unit-event-1",
        "action": "approve",
        "product_content_hash": "c" * 64,
    }


def _tool_fn(server: Any) -> Any:
    from ccf_runtime.mcp.hitl_server import SUBMIT_HITL_ACTION_TOOL

    return server._tool_manager.get_tool(SUBMIT_HITL_ACTION_TOOL).fn


def _access_token(client_id: str) -> Any:
    from mcp.server.auth.provider import AccessToken

    from ccf.hitl.principal import AuthenticationClaims
    from ccf_runtime.mcp.auth import TokenGrant, authentication_claims, tenant_claims

    grant = TokenGrant(
        client_id=client_id,
        scopes=("h",),
        tenants=frozenset({UNIT_TENANT}),
        authentication=AuthenticationClaims(
            method="bearer-token",
            assurance_level="dev",
            identity_provider_ref="idp://unit/dev-token-file",
            session_ref="unit-session-1",
        ),
    )
    return AccessToken(
        token="unit-token",
        client_id=client_id,
        scopes=["h"],
        claims={**tenant_claims(grant), **authentication_claims(grant)},
    )


def _verified_as(monkeypatch: Any, client_id: str) -> None:
    """Stand in for the bearer middleware on BOTH readers of the identity.

    Two modules read ``get_access_token``: the HITL door, for the subject
    binding, and :mod:`ccf_runtime.mcp.tenancy`, for the tenancy floor. Each
    imported the name into its own namespace, so patching one leaves the other
    reading the real (empty) context — which fails closed, but for a reason
    that has nothing to do with what these tests are about.
    """
    import ccf_runtime.mcp.hitl_server as hitl_server
    import ccf_runtime.mcp.tenancy as tenancy

    token = _access_token(client_id)
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: token)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: token)


def test_a_caller_typed_subject_is_a_type_error_at_the_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The subject is the capability's (D-IMPL-353 §2 P6): the tool has no
    ``subject_id`` argument, so a caller typing one is refused by the wire
    signature itself and nothing is routed."""
    routed: list[HitlActionSubmission] = []

    def action_route(authorized: Any, *, submission: HitlActionSubmission) -> str:
        routed.append(submission)
        return "{}"

    server = _unit_server(tmp_path, action_route)
    _verified_as(monkeypatch, "auditor-1")
    with pytest.raises(TypeError):
        _tool_fn(server)(**_unit_arguments(), subject_id="someone-else")
    assert routed == []


def test_a_matching_subject_binds_the_verified_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The routed submission's subject IS the capability's principal — the
    verified client_id — and its provider is the verified claim, minted
    through ``principal_from_authorized`` (one mechanism for both doors)."""
    import ccf_runtime.mcp.hitl_server as hitl_server

    routed: list[HitlActionSubmission] = []

    def action_route(authorized: Any, *, submission: HitlActionSubmission) -> str:
        routed.append(submission)
        return "{}"

    server = _unit_server(tmp_path, action_route)
    _verified_as(monkeypatch, "auditor-1")
    _tool_fn(server)(**_unit_arguments())
    (submission,) = routed
    assert submission.principal.approver.subject_id == "auditor-1"
    assert (
        submission.principal.approver.identity_provider_ref
        == "idp://unit/dev-token-file"
    )
    source = inspect.getsource(hitl_server)
    assert "principal_from_authorized" in source


def test_a_missing_access_token_is_a_typed_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No verified token in context: refuse rather than trust the claim."""
    import ccf_runtime.mcp.hitl_server as hitl_server
    from ccf_runtime.mcp.hitl_server import UnverifiedCallerRefused

    routed: list[HitlActionSubmission] = []

    def action_route(authorized: Any, *, submission: HitlActionSubmission) -> str:
        routed.append(submission)
        return "{}"

    import ccf_runtime.mcp.tenancy as tenancy
    from ccf_runtime.mcp.tenancy import UnverifiedTenantCallerRefused

    server = _unit_server(tmp_path, action_route)
    monkeypatch.setattr(hitl_server, "get_access_token", lambda: None)
    monkeypatch.setattr(tenancy, "get_access_token", lambda: None)
    with pytest.raises(UnverifiedTenantCallerRefused):
        _tool_fn(server)(**_unit_arguments())
    assert routed == []
    monkeypatch.setattr(tenancy, "get_access_token", lambda: _access_token("auditor-1"))
    with pytest.raises(UnverifiedCallerRefused):
        _tool_fn(server)(**_unit_arguments())
    assert routed == []


@with_child
def test_an_unrecognised_credential_is_refused(
    child_server_port: int, bridge: SyncMcpBridge
) -> None:
    """The authority surface is authenticated (D-26; auth.py posture)."""
    import httpx

    url = f"http://127.0.0.1:{child_server_port}/mcp"

    async def operation(session: ClientSession) -> None:  # pragma: no cover
        raise AssertionError("the handshake should have been refused")

    with pytest.raises(McpServerUnreachable):
        bridge.run(
            run_with_session(
                url=url,
                operation=operation,
                http_client_factory=lambda: httpx.AsyncClient(
                    headers={"Authorization": "Bearer ccf-not-a-token"}
                ),
            )
        )
