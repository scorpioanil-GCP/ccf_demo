"""PM6 (panel C6): a Control Plane ambiguity is not coded as approver ineligibility (SEC-009; `D-IMPL-374`).

``verify_erasure_approval`` caught ``ApproverNotEligible`` and
``AmbiguousPinnedVersionError`` together and coded both
``approver-not-eligible``. The second is not a judgment about the approver: two
different contents declare the pinned version of the erasure gate's approval
policy, so the pin is a moving target the Control Plane refuses to resolve
(D-IMPL-26). It still fails closed; the reason code in the audit and at the door
must name the cause.
"""

from __future__ import annotations

from pathlib import Path

from tests.erasure import harness as h
from tests.erasure.test_sec009_fix5_rulings import _judgment
from tests.hitl.sec006_harness import register_typed_policy


def _genuine(plane: h.Plane) -> str:
    """A genuine erasure through the door: requested by alice, approved by bob."""
    door = h.door(plane)
    request = h.request(plane)
    suspended = h.run(
        door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request))
    )
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    h.run(
        door.complete(
            h.resume_cap(), definition_version=plane.definition_version, request=request,
            resolution=resolution, erase=h.erase_cap(request),
        )
    )
    return str(plane.document.content_address)


def test_pm6_an_ambiguous_approval_policy_pin_is_refused_under_its_own_reason_code(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    address = _genuine(plane)
    # Positive control: the genuine erasure is supported.
    assert _judgment(plane, address) == "supported"

    # A second, different approval policy content declaring the SAME semver
    # under the gate policy's key: the pinned version is now ambiguous.
    register_typed_policy(plane.registry, h.APPROVAL_KEY, eligible=frozenset({h.APPROVER, "pm6-someone-else"}))

    reason = _judgment(plane, address)
    assert reason != "approver-not-eligible", "a Control Plane ambiguity was coded as approver ineligibility"
    assert reason == "approval-policy-ambiguous", reason
