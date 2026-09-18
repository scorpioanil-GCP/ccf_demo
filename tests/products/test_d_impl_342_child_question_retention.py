"""`D-IMPL-342` Limb B (`CP14-F-35`) — the exact historical child question, retained.

Dave's ruling, verbatim: *"retain the exact identity-bearing child-question
bytes in the parent's artifact store, for admitted, refused, and unavailable
outcomes. The retained bytes must reproduce the recorded question identity.
Neither the mapping nor the producer may be called to recreate the historical
question during replay."*

Until 2026-09-18 ``question_identity`` hashed a five-key rendering that was
written nowhere: the row named an address the consumer's store could not
resolve, and the proofs recomputed it by re-running the mapping. This module
holds the repair through the paved consumer over the paved fixture producer in
ANOTHER process, and the reconstruction from a FRESH store instance with that
producer stopped and an environment that raises if consulted.

What is held, exactly (design `docs/D-IMPL-342-DESIGN.md` §2.8):

| control | scenario | holds |
| --- | --- | --- |
| C-B1/2/3/12 | admitted; refused by the door; unreachable; served and rejected inside the gate | the row references a retained artifact; the store resolves the reference to the row's address; **the stored bytes equal, byte for byte, the pre-342 identity preimage** (rendered here from the members, independently of the SDK) and hash to the address; the rehydrated contract hashes back to it; the retained request is the wire request an independent construction predicts |
| C-B5 | identity | the ``ProductQuestion`` itself does NOT hash to the address — retaining it would not have satisfied the ruling |
| C-B6 | replay with the world gone | producer process exited, reader and environment raising if reached: the refused record reconstructs, and the audit read returns the question for the refused and the served record alike |
| C-B7 | tamper | other bytes at the address: the refused reconstruction AND the served replay fail as a divergence — the served one before its environment is reached |
| C-B8 | missing | the artifact deleted: unresolvable by name, nothing substituted |
| C-B9 | pre-342 record | rows without a reference: the record reconstructs (unheld by name); the audit read refuses by name — "not retained", never a recompute |
| C-B10 | persistence failure | a store that cannot file the question: the producer is never contacted, no record is written, the fault propagates |
| C-B11 | idempotent | the same question asked twice files one artifact both records reference |

The sabotages S-B1–S-B7 are run by hand against this module and recorded in
`docs/D-IMPL-342-DESIGN.md` §8.3 (as built).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import socket
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.composite import CHILD_QUESTION_CLASS
from ccf.products.door import WireRequest
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.engine import (
    ReplayDivergence,
    ReplayUnresolvable,
    RefusalReplayOutcome,
    replay,
    replay_refusal,
    retained_child_question,
)
from ccf.replay.record import NO_FABRIC_READ, DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.dispatch import ChildQuestionIdentity, ProductQuestion, question_identity
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import ASKED_AT, CHILD_CLASS, CONSUMER_TENANT, THRESHOLD_PARAMETER
from tests.products.test_paved_consumer import _open, _producer, _question, _the_row, _tree

pytestmark = [pytest.mark.crossproc]

UNREACHABLE = "http://127.0.0.1:1/mcp"


@pytest.fixture(scope="module")
def producer_url() -> Iterator[str]:
    with _producer() as url:
        yield url


class _NeverConsulted:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"{name} was reached; the historical question comes from the store, never from a mapping or a producer")


def _pre_342_preimage(*, request: str, subject: str, intent: str, freshness: str, asked_at: datetime) -> bytes:
    """`question_identity`'s rendering EXACTLY as it read before `D-IMPL-342`
    re-expressed it — the oracle this module holds the retained bytes to. Copied,
    not imported: the point is that the SDK's one canonical form reproduces it."""
    return json.dumps(
        {
            "asked_at": asked_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "freshness": freshness,
            "intent": intent,
            "request": request,
            "subject": subject,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _predicted_request() -> str:
    """The wire request the fixture mapping sends, built independently of the resolver."""
    return canonical_bytes(WireRequest(product_id=CHILD_CLASS, parameters={THRESHOLD_PARAMETER: 1000}, temporal_boundary=ASKED_AT)).decode("utf-8")


def _fresh(opened: Any) -> FileArtifactStore:
    return FileArtifactStore(root=opened.scratch / opened.replay.store_dirname)


def _lane_floor_config() -> dict[str, Any]:
    return fixture.consumer_config(compatible_from="1.5.0", producers={"child": fixture.producer_section(versions_from="1.5.0")})


def _record_address(opened: Any, outcome: Any, store: FileArtifactStore) -> str:
    if isinstance(outcome, ServedProduct):
        return outcome.replay_ref.content_address
    return store.resolve_uri(uri=outcome.replay_reference)


def _hold_retained(opened: Any, row: Any) -> ChildQuestionIdentity:
    """C-B1/2/3's shared body: every claim the ruling makes, from a fresh store."""
    fresh = _fresh(opened)
    address = row.child_question_address
    assert address is not None and row.child_question_ref is not None, row
    assert row.child_question_ref == f"ccf-artifact://{CONSUMER_TENANT}/{CHILD_QUESTION_CLASS}/{address}@{address}"
    assert fresh.resolve_uri(uri=row.child_question_ref) == address
    stored = fresh.get(content_address=address)
    # THE EXECUTING PROOF: stored bytes == the pre-342 identity preimage
    preimage = _pre_342_preimage(request=_predicted_request(), subject="acct-1", intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT)
    assert stored == preimage
    assert hashlib.sha256(stored).hexdigest() == address == hashlib.sha256(preimage).hexdigest()
    question = ChildQuestionIdentity.model_validate_json(stored)
    assert content_hash(question) == address and canonical_bytes(question) == stored
    assert (question.subject, question.intent, question.freshness, question.asked_at, question.request) == ("acct-1", "fixture-intent", "fixture-freshness", ASKED_AT, _predicted_request())
    # the same address the SDK's identity function names — one function, no second one
    assert address == question_identity(request_json=question.request, subject=question.subject, intent=question.intent, freshness=question.freshness, asked_at=question.asked_at)
    # and the audit read agrees, calling nothing
    assert retained_child_question(store=fresh, row=row) == question
    return question


# --- C-B1 / C-B2 / C-B3 / C-B5 ---------------------------------------------------------


def test_c_b1_an_admitted_child_leaves_its_exact_question_on_the_parents_store(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = _the_row(opened, served)
    assert row.outcome_status == "admitted"
    _hold_retained(opened, row)


def test_c_b2_a_child_refused_by_its_door_leaves_its_exact_question_on_the_parents_store(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path, config=_lane_floor_config())
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
    assert row.outcome_status == "ineligible"
    _hold_retained(opened, row)


def test_c_b3_an_unreachable_producer_leaves_its_exact_question_on_the_parents_store(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", UNREACHABLE) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
    assert row.outcome_status == "producer-unavailable"
    _hold_retained(opened, row)


def test_c_b12_a_served_answer_rejected_inside_the_gate_leaves_its_exact_question_on_the_parents_store(tmp_path: pathlib.Path, producer_url: str) -> None:
    """The registration names another producer id: the door serves, the gate
    rejects (`producer-mismatch`). The question was filed before dispatch and
    the row must reference it — the branch the candidate's review found writing
    an address with no reference — and the hold must reach it: other bytes at
    the address are a divergence on the refused reconstruction."""
    config = fixture.consumer_config(producers={"child": fixture.producer_section(producer_id="someone-else")})
    root = _tree(tmp_path, config=config)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
    assert row.refusal_ref == "producer-mismatch"
    _hold_retained(opened, row)
    other = canonical_bytes(ChildQuestionIdentity(asked_at=ASKED_AT, freshness="fixture-freshness", intent="fixture-intent", request=_predicted_request(), subject="acct-2"))
    (_fresh(opened).root / row.child_question_address).write_bytes(other)
    with pytest.raises(ReplayDivergence, match="hash to"):
        _reconstruct(opened, refused)


def test_c_b5_the_product_question_itself_does_not_hash_to_the_identity() -> None:
    """Retaining the `ProductQuestion` would NOT have satisfied the ruling: it
    carries `parameters` and names the request `request_json`, so its content
    hash is another address. Only the five-member preimage is the identity."""
    request = _predicted_request()
    sent = ProductQuestion(subject="acct-1", intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT, parameters={THRESHOLD_PARAMETER: 1000}, request_json=request)
    preimage = _pre_342_preimage(request=request, subject="acct-1", intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT)
    assert sent.address == hashlib.sha256(preimage).hexdigest()
    assert content_hash(sent) != sent.address
    assert canonical_bytes(sent.identity_artifact()) == preimage and content_hash(sent.identity_artifact()) == sent.address


# --- C-B6 / C-B7 / C-B8 / C-B9 ---------------------------------------------------------


def _ask_with_a_producer_that_then_exits(tmp_path: pathlib.Path, *, config: dict[str, Any] | None = None) -> tuple[Any, Any, DecisionReplayRecord]:
    """One question against a DEDICATED producer process that has exited by the
    time this returns — what a later examiner has is the record and the store."""
    root = _tree(tmp_path, config=config)
    with _producer() as url, _open(root, tmp_path / "scratch", url) as opened:
        outcome = opened.answer(_question(opened))
        record = opened.record_of(outcome)
    return opened, outcome, record


def _reconstruct(opened: Any, outcome: Any) -> RefusalReplayOutcome:
    fresh = _fresh(opened)
    return replay_refusal(
        record_address=_record_address(opened, outcome, fresh), store=fresh,
        reader=_NeverConsulted(), control_plane=opened.control_plane, environment=_NeverConsulted(),  # type: ignore[arg-type]
    )


def test_c_b6_replay_and_audit_need_neither_the_mapping_nor_the_producer(tmp_path: pathlib.Path) -> None:
    opened, refused, record = _ask_with_a_producer_that_then_exits(tmp_path / "refused", config=_lane_floor_config())
    assert isinstance(refused, RefusalEnvelope), refused
    reconstructed = _reconstruct(opened, refused)
    assert reconstructed.graph_snapshot_id == NO_FABRIC_READ
    (row,) = record.content_generation_path.child_resolutions
    question = retained_child_question(store=_fresh(opened), row=row)
    assert question.subject == "acct-1" and content_hash(question) == row.child_question_address
    # the served record's admitted row reads the same way, producer gone
    opened, served, record = _ask_with_a_producer_that_then_exits(tmp_path / "served")
    assert isinstance(served, ServedProduct), getattr(served, "detail", served)
    (row,) = record.content_generation_path.child_resolutions
    assert row.outcome_status == "admitted"
    assert retained_child_question(store=_fresh(opened), row=row).request == _predicted_request()


def test_c_b7_other_bytes_at_the_address_are_a_divergence_on_both_replay_paths(tmp_path: pathlib.Path) -> None:
    opened, refused, record = _ask_with_a_producer_that_then_exits(tmp_path / "refused", config=_lane_floor_config())
    (row,) = record.content_generation_path.child_resolutions
    other = canonical_bytes(ChildQuestionIdentity(asked_at=ASKED_AT, freshness="fixture-freshness", intent="fixture-intent", request=_predicted_request(), subject="acct-2"))
    (_fresh(opened).root / row.child_question_address).write_bytes(other)
    with pytest.raises(ReplayDivergence, match="hash to"):
        _reconstruct(opened, refused)
    with pytest.raises(ReplayDivergence, match="hash to"):
        retained_child_question(store=_fresh(opened), row=row)
    # the served path: `replay()` holds the question BEFORE its environment is reached
    opened, served, record = _ask_with_a_producer_that_then_exits(tmp_path / "served")
    (row,) = record.content_generation_path.child_resolutions
    (_fresh(opened).root / row.child_question_address).write_bytes(other)
    fresh = _fresh(opened)
    with pytest.raises(ReplayDivergence, match="hash to"):
        replay(
            record_address=_record_address(opened, served, fresh), store=fresh,
            reader=_NeverConsulted(), control_plane=opened.control_plane, environment=_NeverConsulted(),  # type: ignore[arg-type]
        )


def test_c_b8_a_missing_question_artifact_is_unresolvable_by_name(tmp_path: pathlib.Path) -> None:
    opened, refused, record = _ask_with_a_producer_that_then_exits(tmp_path, config=_lane_floor_config())
    (row,) = record.content_generation_path.child_resolutions
    (_fresh(opened).root / row.child_question_address).unlink()
    with pytest.raises(ReplayUnresolvable, match="not retained in the store"):
        _reconstruct(opened, refused)
    with pytest.raises(ReplayUnresolvable, match="not retained in the store"):
        retained_child_question(store=_fresh(opened), row=row)


def test_c_b9_a_pre_342_record_reconstructs_unheld_and_the_audit_read_refuses_by_name(tmp_path: pathlib.Path) -> None:
    opened, refused, record = _ask_with_a_producer_that_then_exits(tmp_path, config=_lane_floor_config())
    path = record.content_generation_path
    rows = tuple(row.model_copy(update={"child_question_ref": None}) for row in path.child_resolutions)
    older = record.model_copy(update={"content_generation_path": path.model_copy(update={"child_resolutions": rows})})
    fresh = _fresh(opened)
    # even with the artifact gone: a row that never referenced one is not held to it
    (fresh.root / rows[0].child_question_address).unlink()
    filed = fresh.put(tenant_id=record.tenant_id, artifact_class="ccf.replay-record", name="pre-342", artifact=older)
    reconstructed = replay_refusal(
        record_address=filed.content_address, store=fresh,
        reader=_NeverConsulted(), control_plane=opened.control_plane, environment=_NeverConsulted(),  # type: ignore[arg-type]
    )
    assert reconstructed.record_content_address == filed.content_address
    with pytest.raises(ReplayUnresolvable, match="carries no retained-question reference"):
        retained_child_question(store=fresh, row=rows[0])


# --- C-B10 / C-B11 ----------------------------------------------------------------------


class _RefusingStore:
    """The real store, with one artifact class refused at `put` and every put recorded."""

    def __init__(self, inner: FileArtifactStore, *, refuse_class: str) -> None:
        self._inner = inner
        self._refuse = refuse_class
        self.puts: list[str] = []

    def put(self, *, tenant_id: str, artifact_class: str, name: str, artifact: Any) -> Any:
        self.puts.append(artifact_class)
        if artifact_class == self._refuse:
            raise OSError(f"the store refused to file {artifact_class!r}")
        return self._inner.put(tenant_id=tenant_id, artifact_class=artifact_class, name=name, artifact=artifact)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _ConnectionCounter:
    """A listener on a loopback port that counts every connection it accepts."""

    def __init__(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(8)
        self._socket.settimeout(0.2)
        self.connections = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._socket.getsockname()[1]}/mcp"

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                client, _ = self._socket.accept()
            except TimeoutError:
                continue
            self.connections += 1
            client.close()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self._socket.close()


def test_c_b10_a_store_that_cannot_file_the_question_leaves_the_producer_unasked_and_no_record(tmp_path: pathlib.Path) -> None:
    counter = _ConnectionCounter()
    try:
        store = _RefusingStore(FileArtifactStore(root=tmp_path / "store"), refuse_class=CHILD_QUESTION_CLASS)
        root = _tree(tmp_path)
        with _open(root, tmp_path / "scratch", counter.url, artifact_store=store) as opened:
            before = counter.connections
            with pytest.raises(OSError, match="refused to file"):
                opened.answer(_question(opened))
        assert counter.connections == before, "the producer was contacted after the question could not be retained"
    finally:
        counter.close()
    assert store.puts == [CHILD_QUESTION_CLASS], store.puts
    assert not any(tmp_path.joinpath("store").glob("[0-9a-f]" * 64)), "a record or artifact was written"


def test_c_b11_the_same_question_asked_twice_files_one_artifact(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        first = _the_row(opened, opened.answer(_question(opened)))
        second = _the_row(opened, opened.answer(_question(opened)))
        fresh = _fresh(opened)
    assert first.child_question_ref == second.child_question_ref is not None
    assert fresh.versions(tenant_id=CONSUMER_TENANT, artifact_class=CHILD_QUESTION_CLASS, name=first.child_question_address) == (first.child_question_address,)
