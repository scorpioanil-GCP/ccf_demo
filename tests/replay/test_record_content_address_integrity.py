# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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
with the file and the canonical serializer can verify the address itself"*),
and a store's own ``get`` hands back whatever it holds, so the claim holds only
for a reader that re-hashes the bytes before anything uses them. Held here, for
the readers item 3 names:

1. **Name = version = the content address of the stored canonical bytes**, for
   a served answer and for a refusal.
2. **Altered content is filed under its own new name**: the record writer names
   a record by its content, so an altered record cannot take the old reference,
   and the old reference still names the original bytes.
3. **Bytes altered under the old reference are refused, before anything uses
   them, by each of these readers**: the replay engine's read
   (``src/ccf/replay/engine.py::resolve_artifact``, which re-hashes on arrival,
   ``D-IMPL-89``); ``OpenedProduct.record_of``; the governed evidence read
   (``runtime/ccf_runtime/authz/delivery_boundary.py::govern_dereference``), both
   for bytes altered before it reads and for bytes that change between its
   authorizing read and the read it serves; child admission's read of a child's
   record (``src/ccf/products/child_resolver.py::GrantBoundChildResolver._touched_entities``),
   which raises ``ChildRecordAltered`` before the admission gate receives
   anything; and the erasure door's read of each requested address
   (``runtime/ccf_runtime/erasure/door.py::ErasureDoor._verify_addresses``),
   refused ``subject-unverifiable`` before any approval starts. Each test
   changes what the file-backed store returns under the address (the stored
   file, altered in place; for the governed read's between-reads case, the
   store's second answer), and that store's ``get`` returns what it holds, so
   the reader's own re-hash is what refuses. For child admission and
   the erasure door a control also runs over the MCP-backed store
   (``src/ccf/artifacts/mcp_store.py::McpArtifactStore``), whose ``get``
   re-hashes first and reads altered bytes as absent. The MCP artifact server's
   client lane, which serves artifacts that are not records by address, serves
   only bytes that hash to the address. Not held here, because it is not a
   check: a store's own ``get``, which returns whatever it holds.

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
import types
from collections.abc import Iterator, Mapping
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactNotFound, artifact_uri, parse_artifact_uri
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.child_resolver import GrantBoundChildResolver
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.door import DoorOutcome
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


# --- the readers that decide on a record's bytes, and the MCP client lane --------------------
#
# Lane 378e-integrity (Dave's E1 (a), ``D-IMPL-378``: "Preserve record content-address
# integrity"). Lane 378e-prose measured two readers taking bytes altered under an address as
# the artifact the address names (its ``probe_record_readers.py``, parts A and C), and this
# lane's reader inventory found a third, the MCP artifact server's client lane
# (``probe_mcp_client_lane.py``). Each test asserts the refusal by its mechanism, after a
# control showing the genuine bytes still work.

#: An entity no child read, planted in an altered child record's dimension 1.
FORGED_ENTITY = "forged:entity"


def _child_resolver_module() -> ModuleType:
    """The child resolver module, imported only after a refusal is observed, so
    that before the fix this test fails on the behavior, never on an import."""
    import ccf.products.child_resolver as module  # noqa: PLC0415

    return module


@pytest.fixture()
def composite(tmp_path: pathlib.Path) -> Iterator[Any]:
    """``tests/products/composite_fixture.py::boot_composite``'s deployment: a parent composed over one
    locally dispatched child, wired with a projection that never withholds its subject."""
    from tests.products.composite_fixture import boot_composite  # noqa: PLC0415

    yield from boot_composite(tmp_path, subject_withholding=SUBJECT_WITHHOLDING_NEVER)


class _AlteringChildDoor:
    """The child's REAL door. Every answer records the touched entities of the child's
    own record; with :attr:`alter` set, the record's stored bytes are then altered IN
    PLACE under their address (a valid record of the same product, dimension 1 naming
    :data:`FORGED_ENTITY`) and the answer is handed back unchanged: the same reference,
    now naming bytes that are not the record."""

    def __init__(self, booted: Any) -> None:
        from tests.products.composite_fixture import _child_door  # noqa: PLC0415

        self._inner = _child_door(booted)
        self._store = booted.store
        self.alter = False
        self.genuine_touched: tuple[str, ...] | None = None
        self.altered_address: str | None = None

    def __call__(self, arguments: Mapping[str, str]) -> Mapping[str, str]:
        answered = self._inner(arguments)
        outcome = DoorOutcome.model_validate_json(answered["outcome"])
        assert outcome.replay_ref is not None, outcome
        address = self._store.resolve_uri(uri=outcome.replay_ref)
        record = DecisionReplayRecord.model_validate_json(self._store.get(content_address=address))
        self.genuine_touched = tuple(record.context_fabric_snapshot.touched_entities)
        if self.alter:
            snapshot = record.context_fabric_snapshot.model_copy(update={"touched_entities": (FORGED_ENTITY,)})
            forged = record.model_copy(update={"context_fabric_snapshot": snapshot})
            assert forged.content_generation_path.product_content_address == (
                record.content_generation_path.product_content_address
            )
            _stored_file(pathlib.Path(self._store.root), address).write_bytes(canonical_bytes(forged))
            self.altered_address = address
        return answered


def _gate_receives(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...] | None]:
    """Every child's touched entities, as the composite admission gate receives them."""
    from ccf.products.composite import CompositeAdmissionGate  # noqa: PLC0415

    received: list[tuple[str, ...] | None] = []
    admit = CompositeAdmissionGate.admit

    def recording(self: Any, *, candidate: Any, **rest: Any) -> Any:
        received.append(candidate.invocation.touched_entities)
        return admit(self, candidate=candidate, **rest)

    monkeypatch.setattr(CompositeAdmissionGate, "admit", recording)
    return received


def test_child_admission_refuses_its_childs_record_bytes_altered_under_their_address(
    composite: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Child admission (``GrantBoundChildResolver._touched_entities``) verifies the record before the gate reads it.

    The admission gate establishes a locally dispatched child's eligibility
    from the touched entities its record lists, read through the child's
    replay reference. The control first: the genuine record, so the composite
    serves and the gate receives the record's own entities. Then the child's
    record is altered in place under its address: a valid record of the same
    product, listing an entity the child never read. The composite must refuse
    by name (``ChildRecordAltered``), and the altered entities must never reach
    the gate. Measured before the fix, over the file-backed store the paved
    road uses: the composite served, the gate holding ``('forged:entity',)``.
    """
    from tests.products.composite_fixture import ask_composite  # noqa: PLC0415
    from tests.products.test_d_impl_339_child_contract_view import _ChildReadingFactory, _wired  # noqa: PLC0415

    door = _AlteringChildDoor(composite)
    resolver = _wired(composite, door=door, plan_factory=_ChildReadingFactory())
    received = _gate_receives(monkeypatch)

    assert isinstance(ask_composite(resolver), ServedProduct)
    assert door.genuine_touched and FORGED_ENTITY not in door.genuine_touched
    assert received == [door.genuine_touched], received

    door.alter = True
    try:
        outcome = ask_composite(resolver)
    except ValueError as raised:
        refused = raised
    else:
        pytest.fail(
            "the composite proceeded on its child's record bytes altered under their"
            f" address ({type(outcome).__name__}); the admission gate received {received[1:]!r}"
        )
    assert door.altered_address is not None, "the child was never asked"
    assert isinstance(refused, _child_resolver_module().ChildRecordAltered), repr(refused)
    assert door.altered_address in str(refused), str(refused)
    assert received[1:] == [], f"the altered record's entities reached the admission gate: {received[1:]!r}"


def test_child_admission_over_the_mcp_backed_store_reads_the_genuine_record_and_not_altered_bytes(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same read through the MCP-backed store (``McpArtifactStore``).

    The control: a record the fabric's writer filed answers its touched
    entities. The same bytes altered in place under their address then read as
    absent (``ArtifactNotFound``): the MCP store re-hashes what the server
    sends before the reader parses anything. ``_touched_entities`` reads only
    ``self._store``, so it is driven with that alone.
    """
    from tests.mcp.guarded_servers import PRINCIPAL, REPLAY_RECORD_CLASS, TENANT  # noqa: PLC0415
    from tests.mcp.test_c2_tenant_hold_mcp import _file, _record  # noqa: PLC0415
    from tests.mcp.test_clientlane_record_shaped import _child_record, _client, _world  # noqa: PLC0415

    world = _world(tmp_path)
    reader = types.SimpleNamespace(_store=_client(world, monkeypatch))
    child = {"child": "the product a producer reported"}
    genuine = _child_record(
        _record(tenant=TENANT, principal=PRINCIPAL, subject="integrity-child"), child, ("genuine:entity",)
    )
    address = _file(world, genuine)
    reference = artifact_uri(
        tenant_id=TENANT, artifact_class=REPLAY_RECORD_CLASS, name="record", artifact_version=address
    )
    assert GrantBoundChildResolver._touched_entities(reader, reference, child) == ("genuine:entity",)  # type: ignore[arg-type]

    snapshot = genuine.context_fabric_snapshot.model_copy(update={"touched_entities": (FORGED_ENTITY,)})
    _stored_file(tmp_path / "artifacts", address).write_bytes(
        canonical_bytes(genuine.model_copy(update={"context_fabric_snapshot": snapshot}))
    )
    with pytest.raises(ArtifactNotFound):
        GrantBoundChildResolver._touched_entities(reader, reference, child)  # type: ignore[arg-type]


def test_the_erasure_door_refuses_to_judge_a_record_from_bytes_altered_under_its_address(
    tmp_path: pathlib.Path,
) -> None:
    """The erasure door (``ErasureDoor._verify_addresses``) verifies each address's bytes before judging them.

    The door judges the subject and record retention (the ``replay-input``
    refusal) from the bytes stored at each address a request names, and only
    then starts the approval workflow. The control first: a record the
    fabric's record writer filed, carrying the subject in a replay-input field,
    is refused ``replay-input``. Then its bytes are altered in place under the
    same address so that the subject leaves that field while staying at its
    declared key path. The same request must be refused ``subject-unverifiable``
    in the re-hash's own words, and start no approval. Measured before the fix:
    it was admitted to approval (``WorkflowSuspended``), an erasure decision
    made from bytes that are not the record at that address.
    """
    from ccf_runtime.erasure import ErasureRefused  # noqa: PLC0415

    from tests.erasure import harness as h  # noqa: PLC0415
    from tests.erasure.test_replay_input_retention_provenance import (  # noqa: PLC0415
        _ask,
        _deployment,
        _record_naming_the_subject,
        _request,
    )
    from tests.mcp.guarded_servers import REPLAY_RECORD_CLASS  # noqa: PLC0415
    from tests.replay.authority import replay_writer  # noqa: PLC0415

    plane, store = _deployment(tmp_path)
    record = _record_naming_the_subject()
    replay_writer(store, tenant=h.TENANT, artifact_class=REPLAY_RECORD_CLASS).write_replay_record(record=record)
    address = content_hash(record)
    request = _request(plane, address, REPLAY_RECORD_CLASS)
    door = h.door(plane, store=store)

    with pytest.raises(ErasureRefused) as control:
        _ask(door, plane, request)
    assert control.value.reason_code == "replay-input", control.value.reason_code

    conditioning = record.perspective_conditioning.model_copy(update={"principal_id": "someone-else"})
    moved = record.model_copy(update={"perspective_conditioning": conditioning})
    assert moved.content_generation_path.plan_id == h.SUBJECT_ID, "the subject must stay at its key path"
    _stored_file(tmp_path, address).write_bytes(canonical_bytes(moved))

    try:
        outcome = _ask(door, plane, request)
    except ErasureRefused as raised:
        refused = raised
    else:
        pytest.fail(
            "the door judged bytes altered under a requested address and started an"
            f" approval ({type(outcome).__name__})"
        )
    assert refused.reason_code == "subject-unverifiable", refused.reason_code
    assert "do not hash to that address" in str(refused), str(refused)
    assert not plane.transport.pending(tenant=h.TENANT), "a refused request starts no approval"


def test_the_erasure_door_over_the_mcp_backed_store_admits_genuine_bytes_and_not_altered_ones(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same verification through the MCP-backed store.

    The control: the harness's genuine client filing, the subject at its key
    path, is admitted to approval. A second filing, altered in place under its
    address, reads as absent through the MCP store, which re-hashes what the
    server sends, so the door refuses it ``subject-unverifiable`` with
    ``ArtifactNotFound`` as the cause.
    """
    from ccf_runtime.erasure import ErasureRefused  # noqa: PLC0415
    from ccf_runtime.workflow.engine import WorkflowSuspended  # noqa: PLC0415

    from tests.erasure import harness as h  # noqa: PLC0415
    from tests.erasure.test_replay_input_retention_provenance import _ask, _mcp_client  # noqa: PLC0415
    from tests.erasure.test_sec009_address_verification import _readdress  # noqa: PLC0415

    plane = h.compose(tmp_path)
    door = h.door(plane, store=_mcp_client(tmp_path, plane.store, monkeypatch))
    assert isinstance(_ask(door, plane, h.request(plane)), WorkflowSuspended)

    second = h.client_put(plane.store, name="note-2", document={"customer": {"id": h.SUBJECT_ID}, "note": "second"})
    _stored_file(tmp_path / "artifacts", second.content_address).write_bytes(
        canonical_bytes({"customer": {"id": h.SUBJECT_ID}, "note": "altered"})
    )
    with pytest.raises(ErasureRefused) as refused:
        _ask(door, plane, _readdress(h.request(plane), second.content_address))
    assert refused.value.reason_code == "subject-unverifiable", refused.value.reason_code
    assert isinstance(refused.value.__cause__, ArtifactNotFound), repr(refused.value.__cause__)


def test_the_artifact_servers_client_lane_never_serves_bytes_altered_under_their_address(
    tmp_path: pathlib.Path,
) -> None:
    """The MCP artifact server's client lane (``build_artifact_server``'s ``dereference``) verifies before it serves.

    The server serves a tenant's own client-lane filing as the exact stored
    bytes. The control: the genuine filing crosses the blob resource, and the
    audit trail shows the client lane served it. Then the stored bytes are
    altered in place under the address: still JSON, still not a record, so the
    record-shaped rule cannot be what decides them. The altered bytes must not
    cross as the artifact the address names: blob and presence answer as a
    missing address does, the governed dereference's recorded ``nonexistent``
    / ``evidence-absent`` determination, which is how the server answers bytes
    that do not hash to their address on its governed path. Measured before
    the fix: the altered bytes crossed, the trail recorded a client-lane serve,
    and presence answered ``{"found":true}``.
    """
    from ccf_runtime.authz.delivery_boundary import DEREFERENCE_PRODUCT_ID  # noqa: PLC0415
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT  # noqa: PLC0415
    from ccf_runtime.mcp.artifact_server import artifact_blob_uri, artifact_meta_uri  # noqa: PLC0415

    from tests.mcp.test_c2_tenant_hold_mcp import _internal_cause  # noqa: PLC0415
    from tests.mcp.test_clientlane_record_shaped import (  # noqa: PLC0415
        CLIENT_CLASS,
        _on_client_lane,
        _read,
        _trail,
        _world,
    )

    world = _world(tmp_path)
    document = {"note": "a client-lane artifact", "amount": 100}
    address = _on_client_lane(world, document, name="integrity")
    blob, presence = artifact_blob_uri(content_address=address), artifact_meta_uri(content_address=address)

    since = len(world.audit_log.events())
    assert _read(world, blob) == canonical_bytes(document)
    assert _trail(world, address, since) == [(CLIENT_CLASS, True)]

    altered = canonical_bytes({"note": "an altered client-lane artifact", "amount": 999999})
    with pytest.raises(ValidationError):
        DecisionReplayRecord.model_validate_json(altered)
    _stored_file(tmp_path / "artifacts", address).write_bytes(altered)

    since = len(world.audit_log.events())
    crossed = _read(world, blob)
    assert crossed != altered, "the client lane served bytes altered under their address as the artifact it names"
    assert _internal_cause(world, crossed) == ("nonexistent", ERROR_EVIDENCE_ABSENT)
    assert _trail(world, address, since) == [(DEREFERENCE_PRODUCT_ID, False)]
    assert _internal_cause(world, _read(world, presence)) == ("nonexistent", ERROR_EVIDENCE_ABSENT)
