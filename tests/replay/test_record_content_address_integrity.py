"""A record's reference names exactly its own bytes, and altered bytes never answer to it.

Dave's E1 (a) (``D-IMPL-378``, 2026-10-08 12:29 MST), verbatim: *"Approve random
per-answer issuance and the named conformance amendments. Preserve record
content-address integrity. Random references must have indistinguishable
distributions; equality is no longer the criterion."*

Under Q11 a Decision Replay record is filed under its own content address —
the reference a caller holds is ``ccf-artifact://{tenant}/{class}/{address}@{address}``
(``src/ccf/replay/serve.py::ReplayWriter``) — so the whole integrity claim is
arithmetic: the address is the sha256 of the stored canonical bytes. The store
is untrusted infrastructure (``src/ccf/artifacts/file_store.py``: *"A reader
with the file and the canonical serializer can verify the address itself"*), so
the claim holds only where every SDK reader of a record by its reference
re-hashes the bytes it hands back. Held here:

1. **Name = version = the content address of the stored canonical bytes**, for
   a served answer and for a refusal.
2. **Altered content is filed under its own new name**: the record writer names
   a record by its content, so an altered record cannot take the old reference,
   and the old reference still names the original bytes.
3. **Bytes altered under the old reference are refused by every reader**: the
   replay engine's read (``src/ccf/replay/engine.py::resolve_artifact``, which
   re-hashes on arrival, ``D-IMPL-89``), ``OpenedProduct.record_of``, and the
   governed evidence read (``runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference``)
   — the last both for bytes altered before it reads and for bytes that change
   between its authorizing read and the read it serves.

Existing golden records still replay to their own addresses: that is
``tests/replay/test_golden_13bd250.py::test_the_record_resolves_byte_first_under_d_impl_89``
and ``tests/replay/test_golden_13bd250.py::test_leg_1_the_13bd250_record_replays_at_head_with_every_hash_matching``,
run beside this module.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Iterator
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import parse_artifact_uri
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.product import OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.engine import ReplayDivergence, resolve_artifact
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

from tests.products.test_paved_road import THRESHOLD_PARAMETER, _open, _question, _write_tree

#: The one member altered throughout: a valid record, a different determination.
ALTERED_PLAN_ID = "a-plan-nobody-ran"


@pytest.fixture()
def opened(tmp_path: pathlib.Path) -> Iterator[OpenedProduct]:
    """The paved road's fixture product, opened over a fresh scratch directory."""
    with _open(_write_tree(tmp_path), tmp_path / "scratch") as product:
        yield product


def _altered(raw: bytes) -> bytes:
    """The same record with one member changed, re-rendered canonically."""
    record = DecisionReplayRecord.model_validate_json(raw)
    path = record.content_generation_path.model_copy(update={"plan_id": ALTERED_PLAN_ID})
    return canonical_bytes(record.model_copy(update={"content_generation_path": path}))


def _stored_file(root: pathlib.Path, address: str) -> pathlib.Path:
    """The one file the file store keeps for ``address`` under ``root``."""
    [found] = [path for path in root.rglob(address) if path.is_file()]
    return found


def _served(opened: OpenedProduct) -> ServedProduct:
    served = opened.answer(_question(opened))
    assert isinstance(served, ServedProduct), served
    return served


def _refused(opened: OpenedProduct) -> RefusalEnvelope:
    # The class's required threshold omitted: a governed, recorded refusal.
    refused = opened.answer(
        opened.question(
            subject="acct-1",
            asked_at=_question(opened).asked_at,
            intent="fixture-intent",
            freshness="fixture-freshness",
            parameters={},
        )
    )
    assert isinstance(refused, RefusalEnvelope), refused
    assert THRESHOLD_PARAMETER in refused.model_dump_json(), refused
    return refused


@pytest.mark.parametrize("leg", ["served", "refused"])
def test_a_records_name_and_version_are_the_content_address_of_its_stored_bytes(
    opened: OpenedProduct, leg: str
) -> None:
    """Claim 1: the reference names one immutable content in both its segments."""
    outcome: Any = _served(opened) if leg == "served" else _refused(opened)
    reference = outcome.replay_ref.uri if leg == "served" else outcome.replay_reference
    named = parse_artifact_uri(reference)
    address = opened.artifact_store.resolve_uri(uri=reference)
    stored = opened.artifact_store.get(content_address=address)
    assert named.name == named.artifact_version == address, reference
    assert hashlib.sha256(stored).hexdigest() == address
    assert canonical_bytes(DecisionReplayRecord.model_validate_json(stored)) == stored, (
        "the stored bytes are not the record's canonical bytes"
    )


def test_an_altered_record_is_filed_under_its_own_name_and_never_takes_the_old_one(
    opened: OpenedProduct, tmp_path: pathlib.Path
) -> None:
    """Claim 2: the record writer names by content, so changed content is a new reference."""
    from ccf.replay.serve import ReplayWriter  # noqa: PLC0415

    from tests.composition import composition_replay_mint  # noqa: PLC0415

    served = _served(opened)
    old_address = served.replay_ref.content_address
    original = opened.artifact_store.get(content_address=old_address)
    altered = DecisionReplayRecord.model_validate_json(_altered(original))

    record = DecisionReplayRecord.model_validate_json(original)
    writer = ReplayWriter(
        store=opened.artifact_store,
        authorized=composition_replay_mint(
            opened.control_plane,
            tenant=record.tenant_id,
            artifact_class=parse_artifact_uri(served.replay_ref.uri).artifact_class,
        ),
    )
    filed = writer.write_replay_record(record=altered)
    new_address = filed.replay_ref.content_address
    assert new_address == content_hash(altered) != old_address
    assert parse_artifact_uri(filed.replay_ref.uri).name == new_address
    assert opened.artifact_store.resolve_uri(uri=served.replay_ref.uri) == old_address
    assert opened.artifact_store.get(content_address=old_address) == original


def test_replay_refuses_bytes_altered_under_the_old_reference(
    opened: OpenedProduct, tmp_path: pathlib.Path
) -> None:
    """Claim 3, the replay engine's one read path: re-hashed on arrival (``D-IMPL-89``)."""
    served = _served(opened)
    address = served.replay_ref.content_address
    resolve_artifact(store=opened.artifact_store, content_address=address, contract=DecisionReplayRecord)
    target = _stored_file(tmp_path, address)
    target.write_bytes(_altered(target.read_bytes()))
    with pytest.raises(ReplayDivergence, match=address):
        resolve_artifact(
            store=opened.artifact_store, content_address=address, contract=DecisionReplayRecord
        )


def test_record_of_refuses_bytes_altered_under_the_old_reference(
    opened: OpenedProduct, tmp_path: pathlib.Path
) -> None:
    """Claim 3, the in-process operator read: the record handed back is the one the reference names.

    The control first: unaltered, ``record_of`` returns the record whose content
    address the reference carries. Then the stored bytes are altered in place —
    a valid record, one member changed — and the same reference must not hand
    back the altered record as the decision's: it is refused by name, as the
    replay engine refuses it.
    """
    served = _served(opened)
    address = served.replay_ref.content_address
    assert content_hash(opened.record_of(served)) == address
    target = _stored_file(tmp_path, address)
    target.write_bytes(_altered(target.read_bytes()))
    with pytest.raises(ReplayDivergence, match=address):
        opened.record_of(served)


@pytest.mark.parametrize("when", ["before-the-read", "between-the-two-reads"])
def test_the_governed_read_never_serves_bytes_altered_under_the_old_reference(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, when: str
) -> None:
    """Claim 3, the governed evidence read, served as bytes (``/artifact/{address}``).

    The world is the readable control of the Q12 tests (a listed class that
    affirms ``never``), so the owner's unaltered read answers 200 with bytes
    that hash to the address — the control, asserted first. Then:

    * **before-the-read** — the stored file is altered: the authorizing read
      re-hashes and answers as a missing address does;
    * **between-the-two-reads** — the store answers the genuine bytes to the
      authorizing read and altered bytes to every later read of that address,
      a substrate that changed between the two. The read that crosses must be
      held to the same arithmetic, and answer as a missing address does.

    Either way the mechanism is named: the refusal's own record carries
    ``evidence-absent``.
    """
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT  # noqa: PLC0415

    from tests.deployment.test_replay_binding import _plan_factory  # noqa: PLC0415
    from tests.http_api.test_sec020_q12_owner_read_back import (  # noqa: PLC0415
        _internal_error_code,
        _owner_get,
    )
    from tests.http_api.test_sec020_withheld_record_dereference import (  # noqa: PLC0415
        PAVED_WITHHELD,
        _ask,
        _door,
        _reference,
    )
    from tests.products.test_withheld_is_indistinguishable_from_absent import (  # noqa: PLC0415
        FROM_DECISION,
    )

    with _door(
        tmp_path, f"integrity-{when}", anchor=FROM_DECISION, holds_subject=True,
        project=_plan_factory, readable=True,
    ) as door:
        store = door.opened.artifact_store
        address = store.resolve_uri(uri=_reference(_ask(door, PAVED_WITHHELD)))
        genuine = store.get(content_address=address)
        control = _owner_get(door, f"/artifact/{address}")
        assert control.status_code == 200, control.text[:400]
        assert hashlib.sha256(control.content).hexdigest() == address

        altered = _altered(genuine)
        if when == "before-the-read":
            _stored_file(tmp_path, address).write_bytes(altered)
        else:
            reads = {"count": 0}
            original_get = FileArtifactStore.get

            def changes_after_the_first_read(self: FileArtifactStore, *, content_address: str) -> bytes:
                payload = original_get(self, content_address=content_address)
                if content_address != address:
                    return payload
                reads["count"] += 1
                return payload if reads["count"] == 1 else altered

            monkeypatch.setattr(FileArtifactStore, "get", changes_after_the_first_read)

        read = _owner_get(door, f"/artifact/{address}")
        monkeypatch.undo()
        assert ALTERED_PLAN_ID.encode() not in read.content, (
            f"[{when}] the governed read served bytes altered under the old reference"
            f" (status {read.status_code})"
        )
        assert read.status_code == 404, f"[{when}] {read.status_code}: {read.text[:400]}"
        shell = json.loads(read.content)["refusal"]
        assert _internal_error_code(store, shell["replay_reference"]) == ERROR_EVIDENCE_ABSENT
