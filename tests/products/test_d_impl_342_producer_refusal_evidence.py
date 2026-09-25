"""`D-IMPL-342` Limb A — the refusing producer's OWN evidence on the parent-side row.

Until 2026-09-18 a child refused by its own door reached the parent's record as
`ineligible` with neither the producer's reason nor its replay reference
(`CP03C-F-05`): admission collapsed the producer's kind, reason and key into a
prose ``detail`` and dropped the door's ``replay_ref`` — while the neighboring
branch, a child SERVED and then rejected at the gate, kept its reference. This
module holds the repair, control by control, through the paved consumer over
the paved fixture producer in ANOTHER process — the same posture as
``tests/products/test_paved_consumer.py`` — never through ``_admit``.

What is held, exactly (design `docs/D-IMPL-342-DESIGN.md` §1.9):

| control | scenario | holds |
| --- | --- | --- |
| C-A1 | the door refuses (a lane floor; a typed parameter — the fixture door's two conformity refusals; its `subject-unavailable` refusal arises only under a wrong tenant, where the claims fail: C-A4a) | the row carries the producer's kind, reason and key **equal to what the door itself discloses** — decoded independently from a raw door outcome obtained by a second dispatch, not read back through admission — and the door's replay reference (its tenant and class; each dispatch mints a new producer record, so the oracle cannot witness the exact reference) |
| C-A2 | served and admitted | the three refusal scalars are ``None``; the replay reference as before |
| C-A3 | unreachable producer | ``producer-unavailable``; no producer refusal invented; no reference |
| C-A4a | the door refuses AND the producer's claims fail (a wrong tenant) | no producer refusal carried — the answer was not the producer's — and no reference |
| C-A4b | the door SERVES and the gate rejects (a wrong producer id) | no producer refusal invented; the reported product's identity, the door's replay reference and the retained question's reference are all on the row — the branch the candidate's review found minting rows without the last two |
| C-A5 | disclosure | the served envelope discloses ``product_class`` only — the five new members cross as ``"undisclosed"`` exactly like the existing producer members — while the record's block carries the values |
| C-A6 | vocabulary | a producer reason cannot become an admission reason or an ``outcome_status`` |
| C-A7 | rehydration | a record written WITHOUT the new keys — the pre-342 shape — still rehydrates and reconstructs |
| C-A8 | fabrication | producer refusal evidence on a row whose door did not refuse is refused at construction |

The sabotages S-A1–S-A6 are run by hand against this module and recorded in
`docs/D-IMPL-342-DESIGN.md` §8.3 (as built).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Iterator
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.child_resolver import ChildQuestion
from ccf.products.composite import GATE_CHILD_ADMISSION, ChildAdmissionRefusal, _status_for
from ccf.products.contract import ChildRequirement
from ccf.products.door import DoorOutcome, WireRequest
from ccf.products.refusal import REFUSAL_KINDS, ProductRequestViolation, RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.engine import RefusalReplayOutcome, _rehydrate_refusal_block, replay_refusal
from ccf.replay.record import NO_FABRIC_READ, ChildResolution, DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SkillCatalog
from ccf.skills.dispatch import McpProductInvocation, ProductQuestion, dispatch_skill
from ccf.skills.grants import GrantLedger
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import (
    ADMITTED_AT,
    ASKED_AT,
    CHILD_CLASS,
    PRODUCER_ID,
    PRODUCER_TENANT,
    SKILL,
    THRESHOLD_PARAMETER,
)
from tests.products.test_paved_consumer import _open, _producer, _question, _the_row, _tree

pytestmark = [pytest.mark.crossproc]

#: The members Limb A added to the refusal value (and so to every composite
#: refusal's envelope ``fields``), plus Limb B's reference, which rides on the
#: same value. Named here so the pre-342 shape can be rebuilt exactly.
NEW_REFUSAL_FIELDS = (
    "producer_refusal_kind",
    "producer_refusal_reason",
    "producer_refusal_key",
    "producer_replay_ref",
    "question_ref",
)
NEW_ROW_MEMBERS = ("producer_refusal_kind", "producer_refusal_reason", "producer_refusal_key", "child_question_ref")
UNREACHABLE = "http://127.0.0.1:1/mcp"


@pytest.fixture(scope="module")
def producer_url() -> Iterator[str]:
    with _producer() as url:
        yield url


class _NeverConsulted:
    """A reader or environment that must not be reached on the pre-projection path."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"{name} was reached; the pre-projection refusal reconstructs from the record alone")


def _lane_floor_config() -> dict[str, Any]:
    """The producer serves `1.0.0`; the consumer's floor is `1.5.0`: the door refuses `class-mismatch`."""
    return fixture.consumer_config(compatible_from="1.5.0", producers={"child": fixture.producer_section(versions_from="1.5.0")})


def _typed_wrong(requirement: ChildRequirement, request: ProductRequest) -> ChildQuestion:
    """A mapping that sends a string where the child's contract declares a number."""
    return ChildQuestion(subject=request.subject, intent="fixture-intent", freshness="fixture-freshness", parameters={THRESHOLD_PARAMETER: "not-a-number"})


def _door_outcome_by_a_second_dispatch(opened: Any, *, parameters: dict[str, Any], subject: str = "acct-1") -> DoorOutcome:
    """THE INDEPENDENT ORACLE: ask the producer's door again through the dispatch
    surface alone — the consumer's registry and the granted entry, no admission,
    no `_admit` — and decode the raw door outcome the door returned."""
    ledger = GrantLedger(control_plane=opened.control_plane, catalog=SkillCatalog(opened.control_plane), sink=None, clock=lambda: ADMITTED_AT)  # type: ignore[arg-type]
    entry = ledger.bound_view(content_hash(opened.agent))[SKILL]
    wire = WireRequest(product_id=entry.binding.product_class, parameters=parameters, temporal_boundary=ASKED_AT)  # type: ignore[union-attr]
    dispatched = dispatch_skill(
        entry,
        arguments={},
        callable_registry=CallableRegistry(),
        mcp_skills=opened.mcp_skills,
        question=ProductQuestion(
            subject=subject, intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT,
            parameters=parameters, request_json=canonical_bytes(wire).decode("utf-8"),
        ),
    )
    assert isinstance(dispatched, McpProductInvocation), dispatched
    return DoorOutcome.model_validate_json(dispatched.contents)


def _fresh(opened: Any) -> FileArtifactStore:
    return FileArtifactStore(
        root=opened.scratch / opened.replay.store_dirname,
        write_kinds=opened.artifact_store.write_kinds,
    )


# --- C-A1 -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "config", "questions", "subject", "parameters", "kind", "reason", "key"),
    [
        ("lane-floor", _lane_floor_config(), fixture.questions, "acct-1", {THRESHOLD_PARAMETER: 1000}, REFUSAL_KINDS[ProductRequestViolation], "class-mismatch", "schema_version"),
        ("typed-parameter", fixture.consumer_config(), _typed_wrong, "acct-1", {THRESHOLD_PARAMETER: "not-a-number"}, REFUSAL_KINDS[ProductRequestViolation], "type-mismatch", THRESHOLD_PARAMETER),
    ],
)
def test_c_a1_a_door_refusal_reaches_the_row_as_the_door_disclosed_it(
    tmp_path: pathlib.Path, producer_url: str, label: str, config: dict[str, Any], questions: Any, subject: str,
    parameters: dict[str, Any], kind: str, reason: str, key: str | None,
) -> None:
    root = _tree(tmp_path, config=config)
    with _open(root, tmp_path / "scratch", producer_url, questions=questions) as opened:
        refused = opened.answer(_question(opened, subject=subject))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
        record = opened.record_of(refused)
        oracle = _door_outcome_by_a_second_dispatch(opened, parameters=parameters, subject=subject)
    # the admission verdict is unchanged — the producer's word sits BESIDE it
    assert (row.outcome_status, row.refusal_ref) == ("ineligible", "ineligible")
    assert (row.producer_id, row.producer_tenant) == (PRODUCER_ID, PRODUCER_TENANT)
    # the producer's own refusal, as its door disclosed it
    assert oracle.refusal is not None and oracle.product_json is None
    assert row.producer_refusal_kind == oracle.refusal.kind == kind
    assert row.producer_refusal_reason == oracle.refusal.reason == reason
    assert row.producer_refusal_key == oracle.refusal.key == key
    # and its replay reference: the producer's claim on the producer's tenant, a
    # well-formed versioned URI, never resolved here. Each dispatch mints a new
    # producer record, so the oracle witnesses the reference's tenant and class,
    # not its exact bytes.
    assert oracle.replay_ref is not None and oracle.replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/ccf.replay-record/")
    assert row.child_replay_ref is not None and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/ccf.replay-record/")
    name, _, version = row.child_replay_ref.rpartition("@")
    assert len(version) == 64 and set(version) <= set("0123456789abcdef") and name.rsplit("/", 1)[1] != version
    assert not _fresh(opened).exists(content_address=version), "the consumer did not copy the producer's record"
    # the composite refusal did not erase it: the record's block and the record's row agree
    block = json.loads(record.content_generation_path.assembly_refusal)
    assert json.loads(block["fields"]["producer_refusal_reason"]) == reason
    assert json.loads(block["fields"]["producer_replay_ref"]) == row.child_replay_ref
    assert "no-producing-skill" not in block["detail"] and reason in block["detail"]
    # the reconstruction accepts the row exactly as written, with producers unreached
    fresh = _fresh(opened)
    outcome = replay_refusal(
        record_address=fresh.resolve_uri(uri=refused.replay_reference), store=fresh,
        reader=_NeverConsulted(), control_plane=opened.control_plane, environment=_NeverConsulted(),  # type: ignore[arg-type]
    )
    assert isinstance(outcome, RefusalReplayOutcome) and outcome.graph_snapshot_id == NO_FABRIC_READ


# --- C-A2 / C-A3 / C-A4 -----------------------------------------------------------------


def test_c_a2_an_admitted_child_carries_no_producer_refusal_and_its_reference_as_before(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = _the_row(opened, served)
    assert row.outcome_status == "admitted"
    assert (row.producer_refusal_kind, row.producer_refusal_reason, row.producer_refusal_key) == (None, None, None)
    assert row.child_replay_ref is not None and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/")


def test_c_a3_an_unreachable_producer_stays_unavailable_with_nothing_invented(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    with _open(root, tmp_path / "scratch", UNREACHABLE) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
        block = json.loads(opened.record_of(refused).content_generation_path.assembly_refusal)
    assert (row.outcome_status, row.refusal_ref) == ("producer-unavailable", "producer-unavailable")
    assert (row.producer_refusal_kind, row.producer_refusal_reason, row.producer_refusal_key, row.child_replay_ref) == (None, None, None, None)
    assert all(block["fields"][name] == "null" for name in NEW_REFUSAL_FIELDS if name != "question_ref"), block["fields"]


def test_c_a4a_a_door_refusal_whose_claims_fail_carries_no_producer_refusal(tmp_path: pathlib.Path, producer_url: str) -> None:
    """The registration names another tenant, so the wire asks the door for a
    tenant it does not serve: the door REFUSES (`subject-unavailable`), and then
    the producer's claims fail against the registration. The answer was not the
    producer's, so its refusal is not carried as the producer's word — the row
    reads the consumer's verdict alone. Measured, not assumed: the oracle shows
    the door refusing."""
    config = fixture.consumer_config(producers={"child": fixture.producer_section(producer_tenant="another-tenant")})
    root = _tree(tmp_path, config=config)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
        oracle = _door_outcome_by_a_second_dispatch(opened, parameters={THRESHOLD_PARAMETER: 1000})
    assert oracle.product_json is None and oracle.refusal is not None and oracle.refusal.reason == "subject-unavailable"
    assert row.refusal_ref == "producer-tenant-mismatch" and row.outcome_status != "ineligible"
    assert (row.producer_refusal_kind, row.producer_refusal_reason, row.producer_refusal_key, row.child_replay_ref) == (None, None, None, None)


def test_c_a4b_a_served_answer_rejected_inside_the_gate_carries_its_references_and_no_producer_refusal(tmp_path: pathlib.Path, producer_url: str) -> None:
    """The registration names another producer id, so the door SERVES and the
    gate rejects the served answer (`producer-mismatch`). No producer refusal is
    invented; the reported product's identity (Amendment 2), the door's replay
    reference for the answer it served, and the retained question's reference
    are all on the row. This is the branch the candidate's review found minting
    rows without the last two."""
    config = fixture.consumer_config(producers={"child": fixture.producer_section(producer_id="someone-else")})
    root = _tree(tmp_path, config=config)
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        row = _the_row(opened, refused)
        oracle = _door_outcome_by_a_second_dispatch(opened, parameters={THRESHOLD_PARAMETER: 1000})
        fresh = _fresh(opened)
    assert oracle.product_json is not None and oracle.refusal is None
    assert row.refusal_ref == "producer-mismatch" and row.outcome_status != "ineligible"
    assert (row.producer_refusal_kind, row.producer_refusal_reason, row.producer_refusal_key) == (None, None, None)
    assert row.child_reported_address == oracle.content_address
    assert row.child_replay_ref is not None and row.child_replay_ref.startswith(f"ccf-artifact://{PRODUCER_TENANT}/ccf.replay-record/")
    assert row.child_question_ref is not None and fresh.resolve_uri(uri=row.child_question_ref) == row.child_question_address


# --- C-A5 / C-A6 ------------------------------------------------------------------------


def test_c_a5_the_served_envelope_discloses_nothing_new_while_the_record_holds_the_values(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path, config=_lane_floor_config())
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        block = json.loads(opened.record_of(refused).content_generation_path.assembly_refusal)
    assert refused.disclosure == "minimal"
    assert json.loads(refused.fields["product_class"]) == CHILD_CLASS
    for name in NEW_REFUSAL_FIELDS:
        assert json.loads(refused.fields[name]) == "undisclosed", (name, refused.fields[name])
    assert "class-mismatch" not in refused.detail and "1.5.0" not in refused.detail
    assert json.loads(block["fields"]["producer_refusal_reason"]) == "class-mismatch"
    assert json.loads(block["fields"]["producer_refusal_key"]) == "schema_version"
    assert json.loads(block["fields"]["producer_replay_ref"]).startswith(f"ccf-artifact://{PRODUCER_TENANT}/")


def test_c_a6_a_producer_reason_is_evidence_and_never_an_admission_reason() -> None:
    with pytest.raises(ValidationError):
        ChildAdmissionRefusal(gate=GATE_CHILD_ADMISSION, detail="x", product_class=CHILD_CLASS, reason="tolerance-exceeded")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="outside the closed vocabulary"):
        _status_for("tolerance-exceeded")
    carried = ChildAdmissionRefusal(
        gate=GATE_CHILD_ADMISSION, detail="x", product_class=CHILD_CLASS, reason="ineligible",
        producer_refusal_kind="product-request-violation", producer_refusal_reason="tolerance-exceeded",
    )
    assert carried.reason == "ineligible" and _status_for(carried.reason) == "ineligible"


# --- C-A7 / C-A8 ------------------------------------------------------------------------


def _without(rendered: bytes, members: tuple[str, ...]) -> bytes:
    """Canonical JSON with the named top-level keys DELETED (not nulled), re-rendered canonically."""
    loaded = json.loads(rendered)
    for name in members:
        loaded.pop(name, None)
    return json.dumps(loaded, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _without_rows_members(rendered: bytes, members: tuple[str, ...]) -> bytes:
    """A record's canonical JSON with the named keys deleted from every child row."""
    loaded = json.loads(rendered)
    for row in loaded["content_generation_path"]["child_resolutions"]:
        for name in members:
            row.pop(name, None)
    return json.dumps(loaded, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _pre_342_record(record: DecisionReplayRecord) -> DecisionReplayRecord:
    """The same determination, in the shape a record had before Limb A: the
    refusal block without the five keys and the rows without the four members."""
    path = record.content_generation_path
    envelope = RefusalEnvelope.model_validate_json(path.assembly_refusal)
    stripped = envelope.model_copy(update={"fields": {k: v for k, v in envelope.fields.items() if k not in NEW_REFUSAL_FIELDS}})
    rows = tuple(row.model_copy(update={name: None for name in NEW_ROW_MEMBERS}) for row in path.child_resolutions)
    older = path.model_copy(update={"assembly_refusal": canonical_bytes(stripped).decode("utf-8"), "child_resolutions": rows})
    return record.model_copy(update={"content_generation_path": older})


def test_c_a7_a_record_without_the_new_keys_still_rehydrates_and_reconstructs(tmp_path: pathlib.Path, producer_url: str) -> None:
    root = _tree(tmp_path, config=_lane_floor_config())
    with _open(root, tmp_path / "scratch", producer_url) as opened:
        refused = opened.answer(_question(opened))
        assert isinstance(refused, RefusalEnvelope), refused
        record = opened.record_of(refused)
    older = _pre_342_record(record)
    assert set(json.loads(older.content_generation_path.assembly_refusal)["fields"]).isdisjoint(NEW_REFUSAL_FIELDS)
    # the block re-canonicalizes to itself, as the engine requires of every block
    rehydrated = _rehydrate_refusal_block(block=older.content_generation_path.assembly_refusal, content_address="pre-342")
    assert isinstance(rehydrated, RefusalEnvelope) and rehydrated.kind == "composite-child-refusal"
    # THE PRE-342 BYTES THEMSELVES — the four members deleted from the row's
    # JSON, never merely set to None — reload to the address they were stored
    # at. This is the control on the members' hash posture: marked as a
    # generation boundary instead of transparent, a stored row lacking them
    # would re-canonicalize with four `null`s and hash elsewhere (sabotage S-A5).
    (row,) = older.content_generation_path.child_resolutions
    stripped_row = _without(canonical_bytes(row), NEW_ROW_MEMBERS)
    reloaded = ChildResolution.model_validate_json(stripped_row)
    assert (reloaded.producer_refusal_reason, reloaded.child_question_ref) == (None, None)
    assert content_hash(reloaded) == hashlib.sha256(stripped_row).hexdigest() == content_hash(row)
    # and the whole older record, as BYTES lacking the keys, reconstructs from
    # the store at its own address — the prologue's generation check included —
    # producers unreached.
    fresh = _fresh(opened)
    stripped_record = _without_rows_members(canonical_bytes(older), NEW_ROW_MEMBERS)
    address = hashlib.sha256(stripped_record).hexdigest()
    (fresh.root / address).write_bytes(stripped_record)
    assert content_hash(DecisionReplayRecord.model_validate_json(stripped_record)) == address
    assert address != content_hash(record), "the two shapes hash differently, by design"
    outcome = replay_refusal(
        record_address=address, store=fresh,
        reader=_NeverConsulted(), control_plane=opened.control_plane, environment=_NeverConsulted(),  # type: ignore[arg-type]
    )
    assert outcome.record_content_address == address


def test_c_a8_producer_refusal_evidence_on_a_row_whose_door_did_not_refuse_is_refused() -> None:
    base = dict(required_product_class=CHILD_CLASS, required=True, child_question_address="a" * 64)
    for status in ("admitted", "producer-unavailable", "unauthorized", "rejected-at-admission"):
        with pytest.raises(ValidationError, match="never fabricated"):
            ChildResolution(**base, outcome_status=status, producer_refusal_reason="tolerance-exceeded")  # type: ignore[arg-type]
    # the status token alone is not enough: an eligibility-evidence refusal shares it
    with pytest.raises(ValidationError, match="never fabricated"):
        ChildResolution(**base, outcome_status="ineligible", refusal_ref="eligibility-evidence-missing", producer_refusal_reason="tolerance-exceeded")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="without a question address"):
        ChildResolution(required_product_class=CHILD_CLASS, required=True, outcome_status="ineligible", child_question_ref="ccf-artifact://t/ccf.child-question/x@x")
    row = ChildResolution(**base, outcome_status="ineligible", refusal_ref="ineligible", producer_refusal_kind="product-request-violation", producer_refusal_reason="class-mismatch", producer_refusal_key="schema_version")  # type: ignore[arg-type]
    assert row.producer_refusal_reason == "class-mismatch"
