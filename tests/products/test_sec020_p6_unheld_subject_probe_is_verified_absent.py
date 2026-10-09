"""SEC-020, ruling P6 (a): the probe identifier is verified to name nothing, never assumed to. SEC-020 is OPEN.

``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). The P6 probe asks the
subject-keyed acquisition phase about
``ccf.products.resolver.UNHELD_SUBJECT_PROBE`` as an identifier that names
nothing, and refuses the question when that call changes the fabric
(``tests/products/test_sec020_p6_population_read_in_subject_keyed_phase.py``).
If the identifier named something, the call would not measure what the phase
acquires for an identifier it does not hold. Dave's condition (kept verbatim as
a comment below) is that this is checked, not assumed.

What these tests hold the SDK to, by mechanism. The SDK reads "names" the way
it seeds a walk from a subject (``ccf.products.request.request_seeds``: the
subject is the node whose entity URI it is), on both axes of a view — an entity
whose URI is the identifier, or a relationship with it at either end — in the
view it reads before the probe and in the one it reads after. If either names
the identifier, every question is refused by name, ``UnheldSubjectProbeIsHeld``,
with one message for the withheld subject and an identifier nothing holds, and
the phase is never handed the question's subject; named before the probe, the
phase is not asked about the probe either. Fail closed, and decided by nothing
about the asked subject.

The cases are built on the low road, where a deployment's seam writes through
L2's admission path for an already-resolved claim
(``AssemblyWorker.admit_entity_claim`` / ``admit_relationship_claim``, the path
a replayed snapshot takes), so a node can carry any URI. On the paved road every
write goes through L2's ingest, which mints ``<entity_class>://<content hash>``;
the probe identifier has no such form, so no paved write can name it — a paved
source holding a record FOR the probe identifier writes a node with another
URI, and the question is refused as the population read it then is
(``PopulationReadInSubjectKeyedPhase``, fail closed), measured below.

The controls are green before and after the check: the same deployment with the
identifier named nowhere is answered, the phase handed the probe and then the
subject; and the paved road's measured refusal above.
"""

# Dave, 2026-10-08 16:40 MST, verbatim (D-IMPL-378 dated amendment on main @ 35315abf), item 2:
#   "P6: (a), conditional implementation GO. Amend Q10 to permit the probe.
#   Extend CT-A with the working declared-population twin. Do not declare
#   closure based on this probe alone: prove it runs before real-subject
#   acquisition, and retain the counterexample where a source treats the probe
#   identifier differently. Verify that the fixed identifier is actually absent;
#   do not assume it."

from __future__ import annotations

import pathlib
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.products.resolver import UNHELD_SUBJECT_PROBE, UnsupportedComposition
from ccf.signal.envelope import SourceIdentity
from tests.deployment.conftest import TENANT
from tests.products import sec020_worlds as w
from tests.products import test_withheld_similarity_registry as low

#: The refusal the check raises, named as data so this module collects on a
#: tree that does not have it yet (the red commit) and fails there by name.
REFUSAL = "UnheldSubjectProbeIsHeld"
#: When a node naming the probe identifier is written: the low road's own
#: pre-question ingestion instant, so every as-of read of the question sees it.
WRITTEN_AT = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)


def _lineage(envelope_id: str) -> frozenset[LineageEntry]:
    return frozenset(
        {LineageEntry(source=SourceIdentity(system_id="fixture-system"), envelope_id=envelope_id, observed_at=WRITTEN_AT)}
    )


def _named_node(uri: str) -> EntityClaim:
    """An already-resolved account claim whose entity URI is ``uri`` verbatim."""
    return EntityClaim(
        tenant_id=TENANT, entity_uri=uri, entity_class="account", attributes={"label": "fixture label"},
        observed_at=WRITTEN_AT, valid_from=WRITTEN_AT, lineage=_lineage("claim-named-node"),
    )


def _naming_edge(*, subject_uri: str, object_uri: str) -> RelationshipClaim:
    """An already-resolved relationship claim between two URIs, verbatim."""
    return RelationshipClaim(
        tenant_id=TENANT, relationship_type="fixture-related", subject_uri=subject_uri, object_uri=object_uri,
        attributes={}, observed_at=WRITTEN_AT, valid_from=WRITTEN_AT, lineage=_lineage("claim-naming-edge"),
    )


class _HoldsTheProbeIdentifier(low._SubjectKeyedRefresh):
    """A seam keyed on the subject whose source holds a record for the probe identifier, named by it.

    Asked about the probe identifier, it admits the node its source holds for
    exactly that identifier; asked about anything else, it is the ordinary
    subject-keyed refresh.
    """

    def __call__(self, *, request: Any, perspective: Any) -> None:
        if request.subject != UNHELD_SUBJECT_PROBE:
            super().__call__(request=request, perspective=perspective)
            return
        self._fabric.handle.worker.admit_entity_claim(tenant_id=TENANT, claim=_named_node(request.subject))
        self.returned[request.subject] = self.returned.get(request.subject, 0) + 1


def _ask_low_road(
    root: pathlib.Path, subject: str, *, anchor: str, seam_type: type = low._SubjectKeyedRefresh,
    preload: Any = None,
) -> tuple[Any, Any]:
    """Boot the low road's fabric for one question, apply ``preload`` to its worker, ask, close."""
    booted = low._boot(root, with_similarity=False, anchor=anchor)
    try:
        if preload is not None:
            preload(booted[0].handle.worker)
        seam = seam_type(booted[0], text=low.QUERY)
        try:
            outcome: Any = low._serve(
                booted, subject, with_similarity=False, acquisition=seam, withhold=frozenset({low.WITHHELD})
            )
        except UnsupportedComposition as refused:
            outcome = refused
        return outcome, seam
    finally:
        booted[0].handle.close()


def _assert_refused_by_name(outcomes: dict[str, Any], *, case: str) -> None:
    names = {subject: type(outcome).__name__ for subject, outcome in outcomes.items()}
    assert set(names.values()) == {REFUSAL}, f"[{case}] every question refused by {REFUSAL}: {names}"
    messages = {str(outcome) for outcome in outcomes.values()}
    assert len(messages) == 1, f"[{case}] one refusal for every subject, worded once: {sorted(messages)}"


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_absence_a_fabric_holding_a_node_named_by_the_probe_identifier_is_refused_by_name(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Named BEFORE the probe (an entity): refused by name, and the phase is asked about nothing at all."""
    outcomes: dict[str, Any] = {}
    seams: dict[str, Any] = {}
    for subject in (low.WITHHELD, low.MISSING):
        outcomes[subject], seams[subject] = _ask_low_road(
            tmp_path / f"node-{len(outcomes)}", subject, anchor=anchor,
            preload=lambda worker: worker.admit_entity_claim(tenant_id=TENANT, claim=_named_node(UNHELD_SUBJECT_PROBE)),
        )
    _assert_refused_by_name(outcomes, case="node named by the probe identifier, before the probe")
    for subject, seam in seams.items():
        assert seam.returned == {}, (
            f"[{subject}] refused before the phase was asked about the probe or the subject: {seam.returned}"
        )


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_absence_a_fabric_holding_a_relationship_naming_the_probe_identifier_is_refused_by_name(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Named BEFORE the probe (a relationship's end): refused by name, and the phase is asked about nothing."""
    outcomes: dict[str, Any] = {}
    seams: dict[str, Any] = {}
    for subject in (low.WITHHELD, low.MISSING):
        outcomes[subject], seams[subject] = _ask_low_road(
            tmp_path / f"edge-{len(outcomes)}", subject, anchor=anchor,
            preload=lambda worker: worker.admit_relationship_claim(
                tenant_id=TENANT, claim=_naming_edge(subject_uri=low.WITHHELD, object_uri=UNHELD_SUBJECT_PROBE)
            ),
        )
    _assert_refused_by_name(outcomes, case="relationship naming the probe identifier, before the probe")
    for subject, seam in seams.items():
        assert seam.returned == {}, (
            f"[{subject}] refused before the phase was asked about the probe or the subject: {seam.returned}"
        )


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_absence_a_source_holding_the_probe_identifier_is_refused_by_name(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Named in what the PROBE acquired: refused by name, not as a population read, and the subject never asked."""
    outcomes: dict[str, Any] = {}
    seams: dict[str, Any] = {}
    for subject in (low.WITHHELD, low.MISSING):
        outcomes[subject], seams[subject] = _ask_low_road(
            tmp_path / f"source-{len(outcomes)}", subject, anchor=anchor, seam_type=_HoldsTheProbeIdentifier
        )
    _assert_refused_by_name(outcomes, case="source holding the probe identifier")
    for subject, seam in seams.items():
        assert set(seam.returned) == {UNHELD_SUBJECT_PROBE}, (
            f"[{subject}] the phase is asked about the probe identifier and never about the question's"
            f" subject: {seam.returned}"
        )


# --- controls: green before the check and after it ---------------------------------------


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_absence_control_with_the_identifier_named_nowhere_the_question_is_answered(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """The same deployment, the identifier named nowhere: answered, the phase handed the probe and then the subject."""
    for subject in (low.WITHHELD, low.MISSING):
        outcome, seam = _ask_low_road(tmp_path / f"absent-{subject.rsplit('/', 1)[-1][:12]}", subject, anchor=anchor)
        assert type(outcome).__name__ in {"ServedProduct", "RefusalEnvelope"}, (subject, outcome)
        assert list(seam.returned) == [UNHELD_SUBJECT_PROBE, subject], (subject, seam.returned)


class _HoldsARecordForTheProbeIdentifier(w.SubjectKeyedSource):
    """A paved ``acquire`` keyed on the subject whose source holds a record for the probe identifier too."""

    def __call__(self, context: Any) -> tuple[Any, ...]:
        if context.request.subject != UNHELD_SUBJECT_PROBE:
            return super().__call__(context)
        self.asked.append(context.request.subject)
        held = w.Holding(account_ref=UNHELD_SUBJECT_PROBE, book=w.OPEN_BOOK, label="probe label",
                         observed_at=w.subject_holding().observed_at)
        return (w.envelope_for(held, tenant=context.tenant_id, ingested_at=context.instant),)


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_absence_control_a_paved_source_holding_a_record_for_the_probe_identifier_is_refused_as_a_population_read(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """On the paved road L2 mints the node's URI, so it never names the probe identifier: refused as P6, fail closed."""
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    source = _HoldsARecordForTheProbeIdentifier({w.SUBJECT: w.subject_holding()})
    built = w.open_paved(
        tmp_path / "paved", anchor=anchor, acquire=source,
        project=w.plan_factory(early=False, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=True),
    )
    try:
        refused = {}
        for subject in (w.SUBJECT, w.NEVER):
            with pytest.raises(UnsupportedComposition) as raised:
                built.ask(subject)
            refused[subject] = type(raised.value).__name__
    finally:
        built.close()
    assert set(refused.values()) == {"PopulationReadInSubjectKeyedPhase"}, refused
    assert source.asked == [UNHELD_SUBJECT_PROBE, UNHELD_SUBJECT_PROBE], source.asked
