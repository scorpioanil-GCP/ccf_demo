"""The erasure door hands the store a copy, checks both answers, and returns its own record (``D-IMPL-380``, third round).

Dave, 2026-10-10 09:18 MST (the ``D-IMPL-380`` amendment, ruling 2 (a)), verbatim: *"Fix all three the same way. Copy
before the save. The erasure door also checks the store's answer and does not return the object the store held."*
And at 09:23 MST: *"The reading stands. Both saves get the copy and the answer check."* *"The erasure door checks both
answers and returns its own record."*

``runtime/ccf_runtime/erasure/door.py::ErasureDoor.complete`` makes two saves: the recorded approval (before the
write-ahead index append) and the erasure record (after the engine completes). At ``7d9d2898`` each handed the store
the door's own object and discarded the store's answer, and ``complete`` returned the very record the store had held
(Fable seat 3, F3-1; reproduced by the coordinator): a store that altered the record inside ``put`` had its
alteration reach the caller, under write-ahead index entries naming the record's address as built.

The attacker: a store that rewrites one string field of the artifact of one class with ``object.__setattr__``
inside ``put`` (the record and the approval are frozen models; this is the way to alter them in place), files the
rewritten artifact through the plane's real store, and answers either the reference of the artifact as it was handed
(the original fingerprint) or its own, altered, address.

* **The record, original reference answered**: ``complete`` returns the record as built, with no alteration.
* **The record, altered address answered**: refused ``record-reference-mismatch`` after the store returns; the
  address stays withheld under the write-ahead entries, as on every other failed completion.
* **The approval, altered address answered**: refused ``approval-reference-mismatch`` after the store returns and
  before the write-ahead append; no index entry is appended and no record is filed.
* **The approval, original reference answered**: the completion proceeds and its record names the approval as built.
  The door uses nothing of its approval after that save but the address it derived before it, so this case is a
  guard, not a red: it was green at ``7d9d2898`` too.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf_runtime.erasure import ErasureRefused
from tests.erasure import harness as h
from tests.erasure.test_interrupted_erasure_passage import outcome

#: The field each class's attacker rewrites: a plain string on the frozen model.
FIELDS = {h.ERASURE_RECORD_CLASS: "requested_by", h.ERASURE_APPROVAL_CLASS: "approver"}


class _RewritesAndAnswers:
    """Rewrites a field of the next artifact of ``artifact_class`` it is handed, files it, answers as told."""

    def __init__(self, inner: Any, *, artifact_class: str, answer: str) -> None:
        assert answer in ("original", "altered")
        self._inner = inner
        self._class = artifact_class
        self._answer = answer
        self.armed = True
        self.as_handed: bytes | None = None
        self.address_as_handed: str | None = None
        self.address_as_rewritten: str | None = None

    def put(self, authorized: Any, artifact: Any) -> Any:
        if not (self.armed and isinstance(artifact, DerivedWrite) and artifact.artifact_class == self._class):
            return self._inner.put(authorized, artifact)
        self.armed = False
        held = artifact.artifact
        field = FIELDS[self._class]
        self.as_handed = canonical_bytes(held)
        self.address_as_handed = content_hash(held)
        object.__setattr__(held, field, f"{getattr(held, field)}-laundered")
        self.address_as_rewritten = content_hash(held)
        filed = self._inner.put(authorized, artifact)
        if self._answer == "altered":
            return filed
        # The original fingerprint: the reference of the artifact as it was handed, naming what was filed.
        return filed.model_copy(
            update={
                "content_address": self.address_as_handed,
                "uri": filed.uri.replace(self.address_as_rewritten, self.address_as_handed),
            }
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def _complete(plane: h.Plane, store: _RewritesAndAnswers) -> Any:
    door = h.door(plane, store=store)
    request = h.request(plane)
    suspended = h.run(
        door.request(
            h.execute_cap(), definition_version=plane.definition_version, request=request, erase=h.erase_cap(request)
        )
    )
    resolution = h.approve(plane, h.pending(plane, suspended.event_key))
    return h.run(
        door.complete(
            h.resume_cap(),
            definition_version=plane.definition_version,
            request=request,
            resolution=resolution,
            erase=h.erase_cap(request),
        )
    )


def _constructed(store: _RewritesAndAnswers, case: str) -> bytes:
    assert store.as_handed is not None and store.address_as_handed != store.address_as_rewritten, (
        f"[{case}] the case was not constructed: the store must have changed the artifact's address"
    )
    return store.as_handed


def _record_count(plane: h.Plane) -> int:
    prefix = f"{h.TENANT}/{h.ERASURE_RECORD_CLASS}/"
    return sum(1 for key in plane.store._read_index() if key.startswith(prefix))


def test_a_store_that_alters_the_record_and_answers_the_original_reference_leaves_the_returned_record_as_built(
    tmp_path: Path,
) -> None:
    case = "record, original reference"
    plane = h.compose(tmp_path)
    store = _RewritesAndAnswers(plane.store, artifact_class=h.ERASURE_RECORD_CLASS, answer="original")

    record = _complete(plane, store)

    as_built = _constructed(store, case)
    assert canonical_bytes(record) == as_built, (
        f"[{case}] complete returned the record the store held: requested_by={record.requested_by!r};"
        f" the record as the door built it is {as_built.decode('utf-8')!r}"
    )
    assert content_hash(record) == store.address_as_handed
    assert "-laundered" not in record.requested_by


def test_a_store_that_alters_the_record_and_answers_its_altered_address_is_refused_and_the_address_stays_withheld(
    tmp_path: Path,
) -> None:
    case = "record, altered address"
    plane = h.compose(tmp_path)
    store = _RewritesAndAnswers(plane.store, artifact_class=h.ERASURE_RECORD_CLASS, answer="altered")

    with pytest.raises(ErasureRefused) as refused:
        _complete(plane, store)

    _constructed(store, case)
    assert refused.value.reason_code == "record-reference-mismatch", refused.value.reason_code
    assert outcome(plane) != "supported", f"[{case}] the address is not withheld: {outcome(plane)}"


def test_a_store_that_alters_the_approval_and_answers_its_altered_address_is_refused_before_the_write_ahead_append(
    tmp_path: Path,
) -> None:
    case = "approval, altered address"
    plane = h.compose(tmp_path)
    store = _RewritesAndAnswers(plane.store, artifact_class=h.ERASURE_APPROVAL_CLASS, answer="altered")

    with pytest.raises(ErasureRefused) as refused:
        _complete(plane, store)

    _constructed(store, case)
    assert refused.value.reason_code == "approval-reference-mismatch", refused.value.reason_code
    entry = h.index_of(plane).lookup(tenant_id=h.TENANT, content_address=plane.document.content_address)
    assert entry is None, f"[{case}] a write-ahead entry was appended after the approval's answer failed: {entry!r}"
    assert _record_count(plane) == 0, f"[{case}] an erasure record was filed"


def test_a_store_that_alters_the_approval_and_answers_the_original_reference_leaves_the_record_naming_the_approval_as_built(
    tmp_path: Path,
) -> None:
    case = "approval, original reference"
    plane = h.compose(tmp_path)
    store = _RewritesAndAnswers(plane.store, artifact_class=h.ERASURE_APPROVAL_CLASS, answer="original")

    record = _complete(plane, store)

    _constructed(store, case)
    assert record.approval_ref == store.address_as_handed, (
        f"[{case}] the record names {record.approval_ref!r}, not the approval as built {store.address_as_handed!r}"
    )
