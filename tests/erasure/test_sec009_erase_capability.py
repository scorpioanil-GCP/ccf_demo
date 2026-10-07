"""SEC-009 ruling 3 — the door requires the distinct ``artifact.erase`` capability (`D-IMPL-374` (4)).

Design ``D-IMPL-367`` §4.1: an ``ArtifactErase`` action kind (``action_id
"artifact.erase"``), minted only at a door from an authorizer's allow and never
at composition, whose resource is the erasure request key
``"<subject_class>/<request_id>"``. Required IN ADDITION to the recorded human
approval: a holder of general ``Execute``/``Resume`` without it is refused by
name, and nothing is written.

RED today: Execute + Resume alone erase.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.authz.capability import CapabilityBypassError, mint, mint_at_composition
from ccf.authz.decision import AuthzDecision
from tests.erasure import harness as h


def _erase_capability(request: Any, *, principal: str = h.REQUESTER, resource: str | None = None) -> Any:
    kind = h.contract("ccf.authz.capability", "ArtifactErase")
    target = resource if resource is not None else f"{request.subject_class}/{request.request_id}"
    return mint(
        kind,
        decision=AuthzDecision(
            allowed=True, matched_scope_pattern=h.TENANT, matched_resource_pattern=target,
            artifact_version="1.0.0", action_id=kind.action_id, tenant=h.TENANT, resource=target,
        ),
        principal=principal,
        decision_id="authz-decision-erase",
    )


def _record_count(plane: h.Plane) -> int:
    prefix = f"{h.TENANT}/{h.ERASURE_RECORD_CLASS}/"
    return sum(1 for key in plane.store._read_index() if key.startswith(prefix))


def test_the_erase_kind_exists_and_is_never_composition_mintable() -> None:
    kind = h.contract("ccf.authz.capability", "ArtifactErase")
    assert kind.action_id == "artifact.erase"
    with pytest.raises(CapabilityBypassError):
        mint_at_composition(kind, tenant=h.TENANT, principal="root", resource="x/y", decision_id="d")  # type: ignore[call-overload]


def test_execute_and_resume_alone_do_not_erase(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    # The erase capability is required by the signature (D-IMPL-353 §4: an
    # authority parameter is never optional) ...
    with pytest.raises(TypeError, match="erase"):
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request))
    # ... and the holder of a general Execute handing it in is refused by name.
    with pytest.raises(CapabilityBypassError):
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.execute_cap()))
    assert not plane.transport.pending(tenant=h.TENANT)


def test_a_completion_without_the_erase_capability_writes_nothing(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door(plane)
    request = h.request(plane)
    erase = _erase_capability(request)
    suspended = h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=erase))
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    with pytest.raises(TypeError, match="erase"):
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution))
    assert _record_count(plane) == 0
    # A general Resume handed in as the erase capability is refused by name.
    with pytest.raises(CapabilityBypassError):
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=h.resume_cap()))
    # An erase capability for ANOTHER request is refused by name.
    with pytest.raises(CapabilityBypassError):
        h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=_erase_capability(request, resource=f"{h.SUBJECT_CLASS}/{'0' * 64}")))
    assert _record_count(plane) == 0
    # With it, the same approved completion writes the record.
    record = h.run(door.complete(h.resume_cap(), definition_version=plane.definition_version, request=request, resolution=resolution, erase=erase))
    assert record.actor.subject_id == h.APPROVER
    assert _record_count(plane) == 1
