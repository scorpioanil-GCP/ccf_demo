"""SEC-009 fix round 1 — the door VERIFIES every requester-named address (`D-IMPL-374` (4)).

Rulings (iii), (iv), C2, I6 and design §7:

* (iv) — every address must hold a value, at one of the subject's declared key
  paths, that hashes to the request's ``subject_ref``; else ``subject-not-found``.
* I6 — every address must be filed under the requesting tenant; else
  ``address-not-in-tenant``.
* C2 / (iii) — a store that answers no naming cannot have its stored class
  verified; the erasure is refused ``class-unverifiable``.
* §7 — a stored document carrying the subject in a replay-input field refuses
  ``replay-input``, with a retention decision naming the code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.authz.capability import ArtifactWrite, mint
from ccf.authz.decision import AuthzDecision
from tests.erasure import harness as h


def _readdress(request: Any, address: str) -> Any:
    first = request.addresses[0].model_copy(update={"content_address": address})
    return type(request).model_validate({**request.model_dump(), "addresses": [first.model_dump()]})


def _request_refused(plane: h.Plane, request: Any, door: Any | None = None) -> Any:
    door = h.door(plane) if door is None else door
    with pytest.raises(h.door_module("ErasureRefused")) as refused:
        h.run(door.request(h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)))
    assert not plane.transport.pending(tenant=h.TENANT), "a refused request starts no approval"
    return refused.value


def test_an_address_whose_document_does_not_carry_the_subject_is_refused(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    other = h.client_put(plane.store, name="someone-else", document={"customer": {"id": "customer-99"}})
    refused = _request_refused(plane, _readdress(h.request(plane), other.content_address))
    assert refused.reason_code == "subject-not-found"


def test_an_address_filed_under_another_tenant_is_refused(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    foreign = "beta-bank"
    authorized = mint(
        ArtifactWrite,
        decision=AuthzDecision(
            allowed=True, matched_scope_pattern=foreign, matched_resource_pattern=f"{h.DOC_CLASS}/n",
            artifact_version="1.0.0", action_id=ArtifactWrite.action_id, tenant=foreign, resource=f"{h.DOC_CLASS}/n",
        ),
        principal="filer", decision_id="foreign",
    )
    ref = plane.store.put(authorized, {"customer": {"id": h.SUBJECT_ID}, "tenant": foreign})
    refused = _request_refused(plane, _readdress(h.request(plane), ref.content_address))
    assert refused.reason_code == "address-not-in-tenant"


class _NoNaming:
    """A store that answers the four Protocol verbs and no naming (an McpArtifactStore-shaped client)."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def put(self, authorized: Any, artifact: Any) -> Any:
        return self._inner.put(authorized, artifact)

    def get(self, *, content_address: str) -> bytes:
        return bytes(self._inner.get(content_address=content_address))

    def exists(self, *, content_address: str) -> bool:
        return bool(self._inner.exists(content_address=content_address))

    def resolve_uri(self, *, uri: str) -> str:
        return str(self._inner.resolve_uri(uri=uri))


def test_a_store_that_answers_no_naming_cannot_verify_a_class_and_refuses(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    door = h.door_module("ErasureDoor")(
        engine=plane.engine,
        factory=h.WorkflowFactory(control_plane=plane.registry),
        control_plane=plane.registry,
        transport=plane.transport,
        hitl_policy_key=plane.hitl_policy_key,
        store=_NoNaming(plane.store),
        clock=plane.clock,
        index=h.index_of(plane),
    )
    refused = _request_refused(plane, h.request(plane), door=door)
    assert refused.reason_code == "class-unverifiable"


def test_a_subject_in_a_replay_input_field_refuses_replay_input(tmp_path: Path) -> None:
    plane = h.compose(tmp_path)
    ref = h.client_put(
        plane.store,
        name="pre-validator",
        document={"customer": {"id": h.SUBJECT_ID}, "perspective_conditioning": {"principal_id": h.SUBJECT_ID}},
    )
    refused = _request_refused(plane, _readdress(h.request(plane), ref.content_address))
    assert refused.reason_code == "replay-input"
    assert refused.decision.reason_code == "replay-input" and refused.decision.verdict == "refuse"
