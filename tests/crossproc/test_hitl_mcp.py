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
    return {
        "tenant": event.tenant,
        "event_key": event.event_key,
        "action": "approve",
        "subject_id": binding.approver.subject_id,
        "identity_provider_ref": binding.approver.identity_provider_ref,
        "method": binding.authentication.method,
        "assurance_level": binding.authentication.assurance_level,
        "session_ref": binding.authentication.session_ref,
        "action_time": binding.action_time.isoformat(),
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

    expected_block = canonical_bytes(
        HitlActionRecord(
            event=event,
            submission=HitlActionSubmission(
                event_key=event.event_key,
                tenant=event.tenant,
                action="approve",
                principal=binding,
                annotation=None,
            ),
            approved=True,
        )
    ).decode("utf-8")
    record = json.loads(payload["replay_record"])
    assert record["policy_bindings"]["hitl_actions"] == expected_block


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
    del incomplete["session_ref"]

    is_error, body = _call_tool(
        bridge, url, SUBMIT_HITL_ACTION_TOOL, incomplete
    )

    assert is_error, body
    # Nothing happened: the pending event survived the refused call.
    view = json.loads(_read_text(bridge, url, hitl_queue_uri(tenant=event.tenant)))
    assert [item["event_key"] for item in view["events"]] == [event.event_key]


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
