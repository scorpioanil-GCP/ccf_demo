"""SEC-020 channel 2 under Dave's Q11 ruling: what a public replay reference may identify.

Dave, 2026-10-07 19:31 MST, Q11: *"Amend before approval. Equal public references
must not identify different immutable record contents. Use a caller-visible
reference separate from the internal evidence address, or another design
preserving unique record identity. Test HTTP, MCP, in-memory and refusal
outputs."* The amended proposal it rejected filed a withheld answer's record
under the name a nonexistent subject's record carries, so one name identified
two different records.

Every answer hands its caller a replay reference,
``ccf-artifact://{tenant}/{class}/{name}@{version}``: in memory as
``ServedProduct.replay_ref`` or a refusal's ``replay_reference``, over HTTP as
the ``X-CCF-Replay-Ref`` header or a refusal body's ``replay_reference``, and
over the MCP product tool as the door outcome's ``replay_ref`` (and its
refusal's ``replay_reference``). On the class-seeded paved road, where the
source holds the withheld subject, each surface is asked the withheld subject
twice and two identifiers that name nothing once each, on both TTL anchors
(``from_decision`` serves; ``from_entity_freshness`` refuses, so both the served
and the refusal output are covered). Three properties are held, each in its own
test so each failure is visible on its own:

1. **Issued per answer.** The same question asked twice is handed two different
   references. A reference that is a function of what the answer read and
   decided is the same for the same read, and for a withheld subject the read
   is what must not show.
2. **One identifier, one record.** Two answers whose records differ never share
   the reference's name or its version — Dave's rule in its strictest reading,
   the name segment included.
3. **Nothing from the read.** The name is not the record's dimension-1
   ``graph_snapshot_id``, the hash of what the plan actually read.

Each reference must also resolve, through the store's naming, to the record of
exactly the answer that carried it (checked first, through ``pytest.fail``).

Every domain value is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import json
import pathlib
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from ccf.artifacts.protocol import ArtifactName, parse_artifact_uri
from ccf.products.door import DoorOutcome
from ccf.products.product import OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf_runtime.mcp.product_door import open_door
from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD
from tests.examples.test_cp_04_two_callers import drive, tool_arguments, tool_call
from tests.http_api.test_sec020_withheld_record_dereference import _ask, _door, _reference
from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT
from tests.products.test_paved_road import _open, _write_tree
from tests.products.test_withheld_is_indistinguishable_from_absent import (
    CLASS_SEEDED,
    FROM_DECISION,
    FROM_ENTITY_FRESHNESS,
    PAVED_ABSENT,
    PAVED_WITHHELD,
    _paved_config,
    _paved_withholding_project,
    _RecordingAcquireForSubject,
    _uri,
)

#: The four answers each surface is asked, by label, with the subject each asks.
#: The withheld subject twice (property 1), two identifiers naming nothing
#: (property 2: their records differ, by the subject each asked about).
QUESTIONS: Mapping[str, str] = {
    "withheld#1": PAVED_WITHHELD,
    "withheld#2": PAVED_WITHHELD,
    "nonexistent#1": PAVED_ABSENT,
    "nonexistent#2": _uri("acct-paved-absent-2"),
}

MCP_TOKEN = {"PAVED_FIXTURE_TOKEN": "fixture-token"}
MCP_ISSUER = {"issuer_url": "https://issuer.example", "resource_server_url": "https://door.example/mcp"}

#: A content address or a 256-bit token: 64 lowercase hex characters.
HEX_64 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class _Handed:
    """What one surface handed its caller, and where the records live."""

    references: Mapping[str, str]
    store: Any


@contextmanager
def _paved(tmp_path: pathlib.Path, name: str, *, anchor: str) -> Iterator[OpenedProduct]:
    """The class-seeded paved road, the source holding the withheld subject."""
    base = tmp_path / name
    base.mkdir()
    root = _write_tree(base, config=_paved_config(anchor=anchor, seeding=CLASS_SEEDED))
    with _open(
        root,
        base / "scratch",
        acquire=_RecordingAcquireForSubject(),
        project=_paved_withholding_project,
    ) as opened:
        yield opened


def _question(opened: OpenedProduct, subject: str) -> Any:
    return opened.question(
        subject=subject,
        asked_at=PAVED_ASKED_AT,
        intent="fixture-intent",
        freshness="fixture-freshness",
        parameters={PAVED_THRESHOLD: 1000},
    )


def _in_memory(tmp_path: pathlib.Path, anchor: str) -> _Handed:
    """``ServedProduct.replay_ref`` or a ``RefusalEnvelope``'s ``replay_reference``."""
    references: dict[str, str] = {}
    with _paved(tmp_path, "in-memory", anchor=anchor) as opened:
        for label, subject in QUESTIONS.items():
            outcome = opened.answer(_question(opened, subject))
            if isinstance(outcome, ServedProduct):
                # The in-memory reference is the ArtifactRef; its members must
                # agree with the URI it carries, so the URI stands for it whole.
                parsed = parse_artifact_uri(outcome.replay_ref.uri)
                if (parsed.name, parsed.artifact_version) != (
                    outcome.replay_ref.name,
                    outcome.replay_ref.content_address,
                ):
                    pytest.fail(f"{label}: the ArtifactRef disagrees with its own URI: {outcome.replay_ref!r}")
                references[label] = outcome.replay_ref.uri
            elif isinstance(outcome, RefusalEnvelope):
                references[label] = outcome.replay_reference
            else:
                pytest.fail(f"{label}: neither served nor refused: {outcome!r}")
        return _Handed(references=references, store=opened.artifact_store)


def _http(tmp_path: pathlib.Path, anchor: str) -> _Handed:
    """The ``X-CCF-Replay-Ref`` header, or a refusal body's ``replay_reference``."""
    references: dict[str, str] = {}
    with _door(tmp_path, "http", anchor=anchor, holds_subject=True) as door:
        for label, subject in QUESTIONS.items():
            references[label] = _reference(_ask(door, subject))
        return _Handed(references=references, store=door.opened.artifact_store)


def _mcp(tmp_path: pathlib.Path, anchor: str) -> _Handed:
    """The MCP product tool's door outcome: ``replay_ref``, and a refusal's own reference."""
    references: dict[str, str] = {}
    with _paved(tmp_path, "mcp", anchor=anchor) as opened:
        door = open_door(opened, environ=MCP_TOKEN)
        shim = SimpleNamespace(server=door.server(**MCP_ISSUER), credential=door.credential)
        answered = drive(
            shim,
            {
                label: tool_call(
                    tool_arguments(tenant=opened.tenant_id, typed=_question(opened, subject))
                )
                for label, subject in QUESTIONS.items()
            },
        )
        for label in QUESTIONS:
            _is_error, text = answered[label]
            try:
                outcome = DoorOutcome.model_validate_json(text)
            except ValueError:
                pytest.fail(f"{label}: the MCP door answered no door outcome: {text[:300]}")
            if outcome.replay_ref is None:
                pytest.fail(f"{label}: the MCP door outcome carries no replay_ref: {text[:300]}")
            if outcome.refusal is not None and outcome.refusal.replay_reference != outcome.replay_ref:
                pytest.fail(f"{label}: the refusal's own replay_reference disagrees with the outcome's")
            references[label] = outcome.replay_ref
        return _Handed(references=references, store=opened.artifact_store)


SURFACES = {"in-memory": _in_memory, "http": _http, "mcp": _mcp}


def _resolved(handed: _Handed, *, surface: str) -> dict[str, tuple[ArtifactName, DecisionReplayRecord]]:
    """Each reference, parsed, with the record it names — the precondition of every property.

    Fails through ``pytest.fail`` (never an assertion), so an assertion failure
    in a property test is that property and nothing else.
    """
    resolved: dict[str, tuple[ArtifactName, DecisionReplayRecord]] = {}
    for label, reference in handed.references.items():
        try:
            parsed = parse_artifact_uri(reference)
            address = handed.store.resolve_uri(uri=reference)
            record = DecisionReplayRecord.model_validate_json(handed.store.get(content_address=address))
        except Exception as error:  # noqa: BLE001 — any failure here is a broken precondition
            pytest.fail(f"[{surface}] {label}: the reference {reference!r} does not resolve: {error!r}")
        asked = record.content_generation_path.request
        if asked is None or asked.subject != QUESTIONS[label]:
            pytest.fail(
                f"[{surface}] {label}: the reference names a record of another question"
                f" ({None if asked is None else asked.subject!r})"
            )
        if not (HEX_64.fullmatch(parsed.name) and HEX_64.fullmatch(parsed.artifact_version)):
            pytest.fail(f"[{surface}] {label}: unexpected reference shape {reference!r}")
        resolved[label] = (parsed, record)
    shapes = {(parsed.tenant_id, parsed.artifact_class) for parsed, _record in resolved.values()}
    if len(shapes) != 1:
        pytest.fail(f"[{surface}] the answers' references name different tenants or classes: {shapes}")
    return resolved


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_q11_the_same_question_asked_twice_is_handed_two_references(
    tmp_path: pathlib.Path, surface: str, anchor: str
) -> None:
    """Property 1, issued per answer: the withheld subject asked twice, two references."""
    handed = SURFACES[surface](tmp_path, anchor)
    _resolved(handed, surface=surface)
    first, second = handed.references["withheld#1"], handed.references["withheld#2"]
    assert first != second, (
        f"[{surface}, {anchor}] the same question asked twice was handed the same"
        f" reference {first}: the reference is a function of what the answer read"
        " and decided, not issued per answer"
    )


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_q11_two_answers_with_different_records_never_share_a_reference_identifier(
    tmp_path: pathlib.Path, surface: str, anchor: str
) -> None:
    """Property 2, Dave's rule: equal public references never identify different records.

    Checked on the two answers about identifiers that name nothing — different
    subjects, so different records — in both identifying segments of the
    reference, the name and the version.
    """
    handed = SURFACES[surface](tmp_path, anchor)
    resolved = _resolved(handed, surface=surface)
    (one, record_one), (two, record_two) = resolved["nonexistent#1"], resolved["nonexistent#2"]
    if record_one == record_two:
        pytest.fail(f"[{surface}] the case was not constructed: the two records are equal")
    assert one.name != two.name, (
        f"[{surface}, {anchor}] two different records share the reference name"
        f" {one.name}: one public identifier names two immutable contents"
    )
    assert one.artifact_version != two.artifact_version


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_q11_no_reference_names_its_record_by_what_the_answer_read(
    tmp_path: pathlib.Path, surface: str, anchor: str
) -> None:
    """Property 3: the name is never dimension 1's ``graph_snapshot_id`` (the real read)."""
    handed = SURFACES[surface](tmp_path, anchor)
    resolved = _resolved(handed, surface=surface)
    derived = {
        label: parsed.name
        for label, (parsed, record) in resolved.items()
        if parsed.name == record.context_fabric_snapshot.graph_snapshot_id
    }
    assert not derived, (
        f"[{surface}, {anchor}] references named by the hash of what the plan read:"
        f" {json.dumps(derived, sort_keys=True)}"
    )


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_q11_the_store_names_each_answers_record_only_by_its_content_address(
    tmp_path: pathlib.Path, surface: str, anchor: str
) -> None:
    """Property 3, at the second carrier: every ``(tenant, class, name)`` the store
    holds for an answer's record names it by its content address and nothing else.

    That naming is what the MCP artifact server's names resource returns to an
    owner its governed read admits (``artifact_names``); on ``e9e5e2cd`` it was
    dimension 1's ``graph_snapshot_id`` (the proof lane's finding 2). Named only by
    its own address, it carries no more than the reference the owner already holds.
    """
    handed = SURFACES[surface](tmp_path, anchor)
    resolved = _resolved(handed, surface=surface)
    other_names = {
        label: sorted({named.name for named in handed.store.names_at(content_address=parsed.artifact_version)})
        for label, (parsed, _record) in resolved.items()
        if {named.name for named in handed.store.names_at(content_address=parsed.artifact_version)}
        != {parsed.artifact_version}
    }
    assert not other_names, (
        f"[{surface}, {anchor}] records filed under a name other than their own content address:"
        f" {json.dumps(other_names, sort_keys=True)}"
    )

def test_q11_the_mcp_driver_reaches_the_door_it_is_handed(tmp_path: pathlib.Path) -> None:
    """Instrument: the MCP surface really answers through the paved door (served, from_decision)."""
    handed = _mcp(tmp_path, FROM_DECISION)
    assert set(handed.references) == set(QUESTIONS)
    assert all(reference.startswith("ccf-artifact://") for reference in handed.references.values())
    _resolved(handed, surface="mcp")


def test_q11_http_and_in_memory_answers_resolve_to_their_own_records(tmp_path: pathlib.Path) -> None:
    """Instrument: every reference on the two other surfaces names the record of its own question."""
    for surface, collect in (("in-memory", _in_memory), ("http", _http)):
        directory = tmp_path / surface
        directory.mkdir()
        resolved = _resolved(collect(directory, FROM_DECISION), surface=surface)
        assert set(resolved) == set(QUESTIONS)


def test_q11_an_http_refusal_carries_its_reference_in_the_body(tmp_path: pathlib.Path) -> None:
    """Instrument: under ``from_entity_freshness`` the HTTP answers are refusals, read off the body."""
    with _door(tmp_path, "http-refusal", anchor=FROM_ENTITY_FRESHNESS, holds_subject=True) as door:
        answer = _ask(door, PAVED_ABSENT)
    assert answer.status_code != int(httpx.codes.OK), answer.text[:300]
    assert answer.json()["refusal"]["replay_reference"].startswith("ccf-artifact://")
