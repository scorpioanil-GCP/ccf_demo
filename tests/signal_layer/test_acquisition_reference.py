"""`FileRecordAcquisitionSource` — the file-backed L1 acquisition reference impl.

`R-09` / `D-IMPL-282` option 3a, and `D-17` (CLAUDE.md §11 — a reference
implementation ships beside every Protocol). What is under test is a
*conforming implementation of a seam that already existed*, not a new seam:
every assertion here is written against
:class:`ccf.signal.source.SignalSourceProtocol`, and the first test in the
file is the one that says so.

The negative controls carry the weight. "One envelope per record" is easy to
satisfy by accident; "a record the selector excludes produces no envelope",
"an empty result is an empty stream and not an error" and "the payload is
byte-identical to the record" are the three that fail if the implementation
starts interpreting.

Drained through ``asyncio.run`` in a synchronous helper, mirroring
``test_mcp_source.py``: the async surface is I/O shape, and the tests are
about what the adapter emits.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.signal.acquisition import (
    AcquisitionRecordError,
    FileRecordAcquisitionSource,
)
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.signal.source import SignalSourceProtocol

TENANT = "acquisition-reference-tenant"

SOURCE = SourceIdentity(system_id="widget-registry")

CLOCK_READING = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)

#: Records in a vocabulary the SDK does not own and does not read. Deliberately
#: not cp-05's: this module proves the *mechanism*, and the domain evidence
#: lives in ``test_cp05_acquisition_boundary.py`` where the No-Hardcoding Rule
#: allows it (CLAUDE.md §6.4, `D-18`).
RECORDS: list[dict[str, Any]] = [
    {"widget_ref": True, "widget_uri": "urn:widget:1", "batch": "b-1", "mass": 3},
    {"widget_ref": True, "widget_uri": "urn:widget:2", "batch": "b-1", "mass": 5},
    {"widget_ref": True, "widget_uri": "urn:widget:3", "batch": "b-2", "mass": 8},
]


def write_json(path: Path, document: object) -> Path:
    """Write ``document`` as JSON to ``path`` and return the path."""
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def build(path: Path, **kwargs: Any) -> FileRecordAcquisitionSource:
    """Construct the reference implementation over ``path``."""
    return FileRecordAcquisitionSource(
        path=path, source=SOURCE, clock=lambda: CLOCK_READING, **kwargs
    )


def drain(source: FileRecordAcquisitionSource) -> list[SignalEnvelope]:
    """Every envelope the source emits for :data:`TENANT`, in order."""

    async def collect() -> list[SignalEnvelope]:
        return [envelope async for envelope in source.envelopes(tenant_id=TENANT)]

    return asyncio.run(collect())


def test_the_reference_implementation_conforms_to_the_existing_seam(
    tmp_path: Path,
) -> None:
    """It satisfies `SignalSourceProtocol` — no second Protocol was declared.

    This is the assertion the whole `R-09` measurement turns on. The seam the
    acquisition boundary needs already existed; what was missing was a
    reference implementation of it (`D-IMPL-277`, resolved by discoverability).
    """
    source = build(write_json(tmp_path / "records.json", RECORDS))
    assert isinstance(source, SignalSourceProtocol)
    assert source.source_identity() == SOURCE


def test_no_new_protocol_is_declared_in_the_acquisition_module() -> None:
    """`ccf.signal.acquisition` exports implementations, never a contract.

    A second acquisition Protocol shipped on a presumption is the outcome
    `D-IMPL-283` (2) exists to prevent, so the module's export list is
    asserted rather than trusted.
    """
    from ccf.signal import acquisition

    for name in acquisition.__all__:
        exported = getattr(acquisition, name)
        assert not (
            isinstance(exported, type) and getattr(exported, "_is_protocol", False)
        ), f"{name} is a Protocol; R-09 ships no new acquisition contract"


def test_one_envelope_per_record_with_the_payload_carried_verbatim(
    tmp_path: Path,
) -> None:
    """Every record becomes exactly one envelope, uninterpreted.

    ``raw_payload`` compares equal to the record as written — no key renamed,
    no class inferred, no identity minted from a payload value. L1 does not
    interpret (INV-CH7-02).
    """
    envelopes = drain(build(write_json(tmp_path / "records.json", RECORDS)))

    assert len(envelopes) == len(RECORDS)
    assert [dict(envelope.raw_payload) for envelope in envelopes] == RECORDS
    assert all(envelope.tenant_id == TENANT for envelope in envelopes)
    assert all(envelope.source == SOURCE for envelope in envelopes)


def test_observed_time_is_unset_because_a_record_states_none(tmp_path: Path) -> None:
    """``observed_time`` is ``None`` — the answer, not a gap.

    A file of records says nothing about when the underlying events occurred.
    Deriving one from the read time, or from a payload field the SDK guessed
    at, would be L1 interpreting, which is L2's monopoly.
    """
    envelopes = drain(build(write_json(tmp_path / "records.json", RECORDS)))
    assert all(envelope.observed_time is None for envelope in envelopes)
    assert all(
        envelope.ingestion_timestamp == CLOCK_READING for envelope in envelopes
    )


def test_envelope_ids_are_stable_across_two_constructions(tmp_path: Path) -> None:
    """Two acquisitions of the same fixture mint the same identities.

    Replay depends on it: a source that minted a fresh id per read would grow
    the graph forever without learning anything, instead of collapsing under
    the idempotent upsert and lineage set-union (INV-CH7-17).
    """
    path = write_json(tmp_path / "records.json", RECORDS)
    first = [envelope.envelope_id for envelope in drain(build(path))]
    second = [envelope.envelope_id for envelope in drain(build(path))]

    assert first == second
    assert len(set(first)) == len(RECORDS), "distinct records must mint distinct ids"


def test_a_changed_record_is_a_different_signal(tmp_path: Path) -> None:
    """Identity covers the record's content, so an edit is new history."""
    path = tmp_path / "records.json"
    original = drain(build(write_json(path, RECORDS)))
    edited_records = [dict(RECORDS[0]) | {"mass": 4}, *RECORDS[1:]]
    edited = drain(build(write_json(path, edited_records)))

    assert original[0].envelope_id != edited[0].envelope_id
    assert original[1].envelope_id == edited[1].envelope_id


def test_the_constructor_parameters_select_records(tmp_path: Path) -> None:
    """Acquisition parameters are constructor state, not method arguments.

    This is the deployment-side adapter pattern the `R-09` measurement
    established: a deployment constructs its source *for a question*, and the
    fabric then asks the constructed object for its envelopes under the one
    parameter the Protocol carries, ``tenant_id``.
    """
    path = write_json(tmp_path / "records.json", RECORDS)
    envelopes = drain(build(path, selectors={"batch": "b-1"}))

    assert [envelope.raw_payload["widget_uri"] for envelope in envelopes] == [
        "urn:widget:1",
        "urn:widget:2",
    ]


def test_a_record_the_selector_excludes_produces_no_envelope(tmp_path: Path) -> None:
    """Exclusion is exact-match on a top-level member, and a miss is a miss.

    A record that does not carry the selector's key is excluded rather than
    admitted by default: guessing which absence means "matches" would be the
    silent default `D-IMPL-38` forbids.
    """
    path = write_json(
        tmp_path / "records.json",
        [*RECORDS, {"widget_ref": True, "widget_uri": "urn:widget:4"}],
    )
    envelopes = drain(build(path, selectors={"batch": "b-2"}))

    assert [envelope.raw_payload["widget_uri"] for envelope in envelopes] == [
        "urn:widget:3"
    ]


def test_an_empty_result_is_an_empty_stream_and_not_an_error(tmp_path: Path) -> None:
    """"No records matched" is an answer, and this is the negative control.

    A source that raised here would make "this question selects nothing" and
    "this source is broken" the same observation, which is the conflation the
    empty-operator guard exists downstream to catch.
    """
    path = write_json(tmp_path / "records.json", RECORDS)
    assert drain(build(path, selectors={"batch": "b-absent"})) == []
    assert drain(build(write_json(tmp_path / "empty.json", []))) == []


def test_a_malformed_document_stops_the_acquisition(tmp_path: Path) -> None:
    """Malformed input raises rather than being skipped.

    A silently dropped record is a graph that is quietly incomplete, which is
    worse than a stream that stops — the same posture
    :class:`~ccf.signal.mcp_envelope_map.McpMappingError` takes (T-06-25).
    """
    not_json = tmp_path / "broken.json"
    not_json.write_text("{", encoding="utf-8")
    with pytest.raises(AcquisitionRecordError):
        drain(build(not_json))

    not_a_list = write_json(tmp_path / "object.json", {"widget_ref": True})
    with pytest.raises(AcquisitionRecordError):
        drain(build(not_a_list))

    not_records = write_json(tmp_path / "scalars.json", [1, 2])
    with pytest.raises(AcquisitionRecordError) as raised:
        drain(build(not_records))
    assert "0" in str(raised.value), "the failing record's position is named"


def test_a_missing_document_names_what_could_not_be_read(tmp_path: Path) -> None:
    """An unreadable source and an empty one are different facts."""
    with pytest.raises(AcquisitionRecordError):
        drain(build(tmp_path / "absent.json"))


def test_the_source_holds_no_graph_handle(tmp_path: Path) -> None:
    """T-24.10-03-02 — acquisition cannot reach L3, by the shape of the seam.

    `SignalSourceProtocol` declares no graph handle, so there is structurally
    nowhere to put one; this asserts the reference implementation did not
    invent a place. Single-writer (INV-CH7-10, CLAUDE.md §10) holds across the
    acquisition boundary for that reason and not by anyone's discipline.
    """
    source = build(write_json(tmp_path / "records.json", RECORDS))
    for attribute in vars(source).values():
        assert not hasattr(attribute, "upsert_entity")
        assert not hasattr(attribute, "admit_relationship_claim")
