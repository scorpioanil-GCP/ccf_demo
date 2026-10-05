"""SEC-006 at the MCP door — the ``approver-not-eligible`` refusal (`D-IMPL-366`, brief §5 row "S1 at the doors", T2b).

RED-FIRST on `main` @ `a236e6ce`. The MCP submit tool over the REAL transport:
a door-shaped submission by the tool's verified principal against a bound
transport whose approval-gate event pins a ``DeclaredArtifact`` approval policy
— the wrong class under the ruling — must come back as the door's one
refusal-body shape with ``error_code == "approver-not-eligible"`` (G3 (a);
brief §4 (6): "at the MCP door's refusal mapping"), and nothing is recorded.
Today the tool maps only the signed-binding family and the transport judges
nothing, so the tool returns a receipt — **BEHAVIORAL**.

Harness reuse: :mod:`tests.mcp.test_sec005_attestation_door` is imported as a
namespace for its tool builder and submit helper. No existing test or fixture
is modified.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
from tests.hitl.sec006_harness import ELIGIBILITY_CODE, plain_hitl_plane, register_declared_policy
from tests.mcp import test_sec005_attestation_door as door


def test_t2b_the_mcp_door_refuses_an_ineligible_approval_with_the_ruled_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S1 at the doors, T2b — BEHAVIORAL today (a receipt is returned)."""
    registry = ControlPlaneRegistry()
    hitl_key = plain_hitl_plane(registry, key=f"{door.TENANT}/hitl/sec006-plain")
    policy_ref = register_declared_policy(registry, f"{door.TENANT}/approval-policy/door-officers")
    transport = InMemoryHitlTransport(control_plane=registry, hitl_policy_key=hitl_key)
    event = PendingHitlEvent(
        event_key="sec006-mcp-event-1",
        event_class="approval-gate",
        tenant=door.TENANT,
        workflow_state_ref=f"{door.TENANT}/exec-sec006",
        product_content_hash=door.VALID_HASH,
        policy_ref=policy_ref,
    )
    transport.enqueue(event=event)
    tool = door._build_tool(transport, monkeypatch, lambda: datetime.now(UTC))
    receipt, refusal = door._submit(
        tool,
        {
            "tenant": door.TENANT,
            "event_key": event.event_key,
            "action": "approve",
            "product_content_hash": door.VALID_HASH,
        },
    )
    assert receipt is None, (
        "BEHAVIORAL: the MCP door ADMITTED a door-shaped approval of a gate whose"
        " policy is not a typed ccf.approval-policy; it must refuse with"
        f" {ELIGIBILITY_CODE!r} (D-IMPL-366 G3 (a)): {receipt}"
    )
    assert refusal is not None and refusal["error_code"] == ELIGIBILITY_CODE, refusal
    assert transport.submissions(tenant=door.TENANT) == ()
    assert transport.pending(tenant=door.TENANT) == (event,)
