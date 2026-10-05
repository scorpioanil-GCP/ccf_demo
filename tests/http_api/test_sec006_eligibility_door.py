"""SEC-006 at the HTTP door — the ``approver-not-eligible`` mapping (`D-IMPL-366`, brief §5 row "S1 at the doors", T2).

RED-FIRST on `main` @ `a236e6ce`. A door-shaped submission (no primitive, no
claim) by the door's own authenticated principal against a bound transport
whose approval-gate event pins a ``DeclaredArtifact`` approval policy — the
wrong class under the ruling — must come back **403** with the distinct,
non-enumerating code ``approver-not-eligible`` (G3 (a); brief §4 (6): mapped
at the HTTP door as the signed-binding family is), and nothing is recorded.
Today the route maps only the signed-binding family and the transport judges
nothing, so the submission is admitted with HTTP 200 — **BEHAVIORAL**.

Harness reuse: :mod:`tests.http_api.test_sec005_attestation_door` is imported as
a namespace for its app builder, poster and refusal assertion; the
module-scoped ``fabric`` comes from :mod:`tests.http_api.conftest`. No existing
test or fixture is modified.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ccf.hitl.transport import InMemoryHitlTransport, PendingHitlEvent
from tests.hitl.sec006_harness import ELIGIBILITY_CODE, plain_hitl_plane, register_declared_policy
from tests.http_api import test_sec005_attestation_door as door


def test_t2_the_http_door_refuses_an_ineligible_approval_with_the_ruled_code(
    fabric: Any, tmp_path: Path
) -> None:
    """S1 at the doors, T2 — BEHAVIORAL today (HTTP 200, the submission lands)."""
    tenant = door._tenant("required")
    hitl_key = plain_hitl_plane(fabric.registry, key=f"{tenant}/hitl/sec006-plain")
    policy_ref = register_declared_policy(fabric.registry, f"{tenant}/approval-policy/door-officers")
    transport = InMemoryHitlTransport(control_plane=fabric.registry, hitl_policy_key=hitl_key)
    event = PendingHitlEvent(
        event_key="sec006-door-event-1",
        event_class="approval-gate",
        tenant=tenant,
        workflow_state_ref=f"{tenant}/exec-sec006",
        product_content_hash=door._VALID_HASH,
        policy_ref=policy_ref,
    )
    transport.enqueue(event=event)
    app = door._build_app(fabric, transport, tmp_path, lambda: datetime.now(UTC))
    response = door._post(
        app,
        tenant,
        {
            "event_key": event.event_key,
            "action": "approve",
            "product_content_hash": door._VALID_HASH,
            "annotation": None,
            "attestation": None,
        },
    )
    assert response.status_code != 200, (
        "BEHAVIORAL: the HTTP door ADMITTED a door-shaped approval of a gate whose"
        " policy is not a typed ccf.approval-policy; it must refuse 403"
        f" {ELIGIBILITY_CODE!r} (D-IMPL-366 G3 (a)): {response.text[:300]}"
    )
    door._assert_refused(response, transport, tenant, code=ELIGIBILITY_CODE)
    assert transport.pending(tenant=tenant) == (event,)
