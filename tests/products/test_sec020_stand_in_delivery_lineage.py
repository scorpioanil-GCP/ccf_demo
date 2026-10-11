# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""SEC-020, repair 1.3: the stand-in check compares what was acquired, delivery lineage set aside. SEC-020 is OPEN.

``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). Decision 4 (a) (lane ``378i-probe``)
verifies, for every question of a class with a declared early policy, that the
policy's stand-in names nothing: the subject-keyed acquisition phase is asked
about ``ccf.products.resolver.UNHELD_SUBJECT_PROBE`` (the baseline) and then
about the stand-in, and the two views of the fabric read after each call are
compared. As built it compared the two ``GraphView`` values whole, lineage
included, so an adapter that gives each DELIVERY its own envelope id was
refused on every question, the stand-in held nowhere (the "i" panel's Fable G1
F-G1-3: every differing path was under ``claim.lineage``). Dave's repair 1.3,
2026-10-09 10:54 MST, is kept verbatim as a comment below.

**What a view difference can consist of** (``src/ccf/graph/protocols.py::GraphView``):
the view's ``tenant_id`` and ``as_of``; its entity records
(``src/ccf/graph/protocols.py::EntityRecord``: ``claim_id``, the claim,
``policy_bundle_version``, ``superseded_by``, ``superseded_at``) and relationship
records (``src/ccf/graph/protocols.py::RelationshipRecord``: the same plus
``relationship_key``); each claim's values (``src/ccf/contracts/claims.py::EntityClaim``,
``src/ccf/contracts/claims.py::RelationshipClaim``: tenant, ``observed_at``,
``valid_from``, ``valid_to``, the URI or the two ends and the type, the
attributes); and each claim's lineage, a set of
``src/ccf/contracts/claims.py::LineageEntry`` values whose components are:

* ``envelope_id`` — the identity of the envelope that DELIVERED the claim, which
  the acquisition seam leaves to the adapter: minted per delivery by an adapter
  that gives each delivery a fresh id (shown here: the views differ only there);
* ``observed_at`` — when the fabric received that delivery: L2 takes it from
  the envelope's ``ingestion_timestamp``
  (``src/ccf/assembly/worker.py::AssemblyWorker._stitch``), so it is minted per
  delivery (shown here on the low road, where a seam stamps each delivery with
  its own receipt instant; the paved road pins every delivery of a question to
  the question's instant);
* ``source`` and ``passage_anchor`` — which system the evidence came from and
  where in its content: properties of the evidence, not of a delivery. They are
  still compared.

What these tests hold the SDK to, by mechanism:

* **R1 (red before repair 1.3).** Under an early policy, a population read
  whose deliveries differ from each other ONLY in delivery lineage — a fresh
  envelope id per delivery, or each delivery's own receipt instant — is
  answered: the withheld subject, an identifier nothing holds and an ordinarily
  served subject, each as data; the withheld and nonexistent answers judged by
  SEC-020's closing test's own rules (``_compare``) at every door. An adapter
  whose envelope ids echo the identifier it was asked is answered too, and an
  envelope id reaches no byte of the answer, of its decision record or of any
  other artifact the deployment's artifact store holds (only the question's own
  graph store holds it) — the reason setting delivery lineage aside loses no
  difference the answer or the record carries.
* **R3 (green before and after: what is preserved).** A difference that is not
  delivery lineage still refuses every question alike, by name
  (``UndisclosedSubjectSubstituteIsHeld``), worded once, nothing recorded: a
  claim value naming the stand-in; a relationship naming it at an end or in its
  attributes; a lineage entry whose source names it; a lineage entry whose
  passage anchor names it.

The existing held-stand-in controls (R2) are
``tests/products/test_sec020_stand_in_is_verified_absent.py``'s, unchanged:
``test_a_stand_in_that_names_something_refuses_every_question_before_acquisition``
(the stand-in held as itself, under another URI, or written by a population
phase), ``test_a_stand_in_the_source_holds_leaves_withheld_and_nonexistent_indistinguishable``,
``test_a_fabric_that_names_the_stand_in_after_acquisition_is_refused_before_anything_is_recorded``
and ``test_a_stand_in_a_preloaded_fabric_names_is_refused_with_no_acquisition_on_the_low_road``.
"""

# Dave, 2026-10-09 10:54 MST, verbatim (D-IMPL-378 dated amendment on main @ f07e558e), repair 1.3:
#   "Compare entities, relationships and claim values, excluding delivery lineage. Preserve
#   security-relevant differences and the existing held-stand-in controls."
# Dave, 2026-10-09 06:06 MST, confirmed at 06:21 MST, decision 4 (a), verbatim: "(a). Verify the
#   stand-in is absent before and after acquisition. A failed check refuses without exposing
#   subject-dependent differences."

from __future__ import annotations

import pathlib
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest

import ccf.products.resolver as resolver_module
from ccf.contracts.claims import LineageEntry, PassageAnchor, RelationshipClaim
from ccf.graph.protocols import GraphView
from ccf.products.resolver import UnsupportedComposition
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from tests.deployment.test_replay_binding import PRODUCT_CLASS
from tests.products import sec020_worlds as w
from tests.products import test_withheld_similarity_registry as low
from tests.products.test_sec020_combined_proof import _compare, _vacuous

#: The refusal decision 4 (a) raises, named as data (the closing test's convention).
REFUSAL = "UndisclosedSubjectSubstituteIsHeld"

#: The sides one deployment is asked, by the closing test's names for the same-deployment comparison.
_SIDES = ((w.CF_WITHHELD, w.SUBJECT), (w.SAME_NONEXISTENT, w.NEVER), (w.SAME_FLOOR, w.NEVER_2))

#: The paths of a view, as ``model_dump(mode="json")`` lays it out, that are a lineage entry's
#: delivery components: ``entities[3].claim.lineage[0].envelope_id`` and the like.
_DELIVERY_PATH = re.compile(r"\A(entities|relationships)\[\d+\]\.claim\.lineage\[\d+\]\.(envelope_id|observed_at)\Z")


def _records(store: Any) -> frozenset[str]:
    """The content-addressed artifacts a deployment's store holds (its records and pins)."""
    root = getattr(store, "inner", store).root
    return frozenset(path.name for path in root.iterdir() if re.fullmatch(r"[0-9a-f]{64}", path.name))


def _paths(value: Any, prefix: str = "") -> dict[str, Any]:
    """Every leaf of a JSON-shaped value, by dotted path."""
    if isinstance(value, dict):
        found: dict[str, Any] = {}
        for key, item in value.items():
            found.update(_paths(item, f"{prefix}.{key}" if prefix else str(key)))
        return found
    if isinstance(value, list):
        found = {}
        for index, item in enumerate(value):
            found.update(_paths(item, f"{prefix}[{index}]"))
        return found
    return {prefix: value}


def _differing(left: GraphView, right: GraphView) -> set[str]:
    """The leaf paths at which two views differ, as ``model_dump(mode="json")`` renders them."""
    a, b = _paths(left.model_dump(mode="json")), _paths(right.model_dump(mode="json"))
    return {path for path in set(a) | set(b) if a.get(path) != b.get(path)}


class _CapturedViews:
    """The two views decision 4 (a)'s check compares, captured off ``GovernedResolver._acquired_for`` (behavior unchanged)."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.views: list[GraphView] = []
        original = resolver_module.GovernedResolver._acquired_for

        def capturing(resolver: Any, *args: Any, **kwargs: Any) -> GraphView:
            view = original(resolver, *args, **kwargs)
            self.views.append(view)
            return view

        monkeypatch.setattr(resolver_module.GovernedResolver, "_acquired_for", capturing)

    def only_delivery_lineage_differs(self) -> None:
        """The precondition, shown rather than assumed: the baseline and the stand-in's view differ, only in delivery lineage."""
        assert len(self.views) >= 2, f"case not constructed: the check read {len(self.views)} view(s)"
        baseline, after = self.views[0], self.views[1]
        differing = _differing(baseline, after)
        assert differing, "case not constructed: the deliveries left the two views equal, so nothing is shown"
        other = sorted(path for path in differing if not _DELIVERY_PATH.match(path))
        # A lineage SET that grew renders its new member at every component; what grew must
        # match an existing member in everything but the delivery components.
        assert not [path for path in other if ".claim.lineage[" not in path], (
            f"case not constructed: the views differ beyond lineage: {other}"
        )
        for records in ("entities", "relationships"):
            for old, new in zip(getattr(baseline, records), getattr(after, records), strict=True):
                kept = {
                    (entry.source, entry.passage_anchor) for entry in old.claim.lineage
                }
                grown = {
                    (entry.source, entry.passage_anchor) for entry in new.claim.lineage
                }
                assert kept == grown, (
                    f"case not constructed: a lineage entry differs in more than its delivery components: {kept} {grown}"
                )


def _answered(outcomes: dict[str, Any]) -> None:
    """Every side was answered as data: a served product or a refusal shell, never an exception."""
    names = {side: type(outcome).__name__ for side, outcome in outcomes.items()}
    assert set(names.values()) <= {"ServedProduct", "RefusalEnvelope"}, names


def _ask(built: w.Deployment, subject: str) -> Any:
    try:
        return built.ask(subject, None)
    except Exception as raised:  # noqa: BLE001 — an exception is the observation the assertion names
        return raised


def _judged(tmp_path: pathlib.Path, anchor: str, door: str, source: Any) -> None:
    """The withheld and the nonexistent answers, judged by SEC-020's closing test's own rules."""
    built = _early(tmp_path / f"judged-{door}", anchor, source)
    try:
        sides = {side: w.observe_side(w.SUBJECT_KEYED, door, built, subject) for side, subject in _SIDES}
    finally:
        built.close()
    run = w.Run(shape="early-delivery-lineage", anchor=anchor, door=door, sides=sides)
    vacuous = _vacuous(run, w.CF_WITHHELD, w.SAME_NONEXISTENT, either=True)
    assert not vacuous, f"[{anchor}, {door}] not evidence: a side raised instead of answering: {vacuous}"
    for channel in w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=w.SUBJECT_KEYED, door=door):
        differing, floor, withheld, nonexistent = _compare(run, comparison=w.SAME_DEPLOYMENT, channel=channel)
        assert not differing, (
            f"[{anchor}, {door}, {channel}] a withheld subject is distinguishable from a nonexistent one at"
            f" {sorted(differing)} (noise floor, not counted: {sorted(floor)})\n"
            f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
        )


def _early(base: pathlib.Path, anchor: str, source: Any, *, active: bool = True) -> w.Deployment:
    """SEC-020's early-withholding paved deployment over ``source``."""
    return w.open_paved(
        base, anchor=anchor, acquire=source,
        project=w.plan_factory(early=True, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=active),
    )


def _population() -> dict[str, w.Holding]:
    return {w.SIBLING: w.sibling_holding(), w.SUBJECT: w.subject_holding()}


# --- R1: deliveries that differ only in delivery lineage are answered -------------------------


class _FreshIdPerDelivery(w.PopulationSource):
    """A population read that gives every DELIVERY its own envelope id (the panel's F-G1-3 adapter)."""

    def __call__(self, context: Any) -> Any:
        self.asked.append(context.request.subject)
        return tuple(
            w.envelope_for(
                holding, tenant=context.tenant_id, ingested_at=context.instant,
                envelope_id=f"envelope-{holding.account_ref}-{uuid.uuid4().hex}",
            )
            for _uri, holding in sorted(self._holdings.items())
        )


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r1_a_fresh_envelope_id_per_delivery_is_answered_on_the_paved_road(
    tmp_path: pathlib.Path, anchor: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stand-in held nowhere, each delivery its own id: every question answered, the views differing only there."""
    captured = _CapturedViews(monkeypatch)
    withholding = _early(tmp_path / "withholding", anchor, _FreshIdPerDelivery(_population()))
    serving = _early(tmp_path / "serving", anchor, _FreshIdPerDelivery(_population()), active=False)
    try:
        outcomes = {
            "withheld": _ask(withholding, w.SUBJECT),
            "nonexistent": _ask(withholding, w.NEVER),
            "served": _ask(serving, w.SIBLING),
        }
    finally:
        withholding.close()
        serving.close()
    captured.only_delivery_lineage_differs()
    _answered(outcomes)


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r1_a_fresh_envelope_id_per_delivery_leaves_withheld_and_nonexistent_indistinguishable(
    tmp_path: pathlib.Path, anchor: str, door: str
) -> None:
    """Answered, and judged by the closing test's rules at every door: no difference beyond the noise floor."""
    _judged(tmp_path, anchor, door, _FreshIdPerDelivery(_population()))


#: The low road's receipt instants: one per delivery, each within the hour the fixture's claims carry.
_FIRST_RECEIPT = datetime.fromisoformat(low.INGESTED.replace("Z", "+00:00"))


class _OwnReceiptInstantPerDelivery(low._SubjectKeyedRefresh):
    """A low-road population read: the same claim and envelope id every time, stamped with each delivery's receipt instant."""

    def __init__(self, fabric: Any, *, text: str) -> None:
        super().__init__(fabric, text=text)
        self.deliveries = 0

    def __call__(self, *, request: Any, perspective: Any) -> None:
        self.deliveries += 1
        envelope = low._claim(low.WITHHELD_REF, self._text, envelope_id="claim-acquired", observed=low.REFRESHED)
        self._fabric.handle.worker.ingest(
            envelope.model_copy(
                update={"ingestion_timestamp": _FIRST_RECEIPT + timedelta(seconds=self.deliveries)}
            )
        )
        self.returned[request.subject] = self.returned.get(request.subject, 0) + 1


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_r1_each_deliverys_own_receipt_instant_is_answered_on_the_low_road(
    tmp_path: pathlib.Path, anchor: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hand-composed resolver whose seam stamps each delivery as received: answered, the views differing only there."""
    captured = _CapturedViews(monkeypatch)
    outcomes: dict[str, Any] = {}
    for side, subject in (("withheld", low.WITHHELD), ("nonexistent", low.MISSING)):
        booted = low._boot(tmp_path / side, with_similarity=False, anchor=anchor)
        try:
            seam = _OwnReceiptInstantPerDelivery(booted[0], text=low.QUERY)
            try:
                outcomes[side] = low._serve(
                    booted, subject, with_similarity=False, acquisition=seam,
                    withhold=frozenset({low.WITHHELD}), plan_factory=low._EarlyWithholding(),
                )
            except Exception as raised:  # noqa: BLE001 — the observation the assertion names
                outcomes[side] = raised
        finally:
            booted[0].handle.close()
    captured.only_delivery_lineage_differs()
    _answered(outcomes)


class _EnvelopeIdEchoesTheAsked(w.PopulationSource):
    """A population read whose envelope ids carry the identifier it was asked — delivery lineage that NAMES what was asked."""

    def __call__(self, context: Any) -> Any:
        asked = context.request.subject
        self.asked.append(asked)
        return tuple(
            w.envelope_for(
                holding, tenant=context.tenant_id, ingested_at=context.instant,
                envelope_id=f"envelope-{holding.account_ref}-for-{asked}",
            )
            for _uri, holding in sorted(self._holdings.items())
        )


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r1_envelope_ids_naming_what_was_asked_reach_neither_the_answer_nor_the_artifact_store(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """What setting delivery lineage aside admits: answered, and no envelope id in the answer or any artifact the store holds.

    The question's own graph store holds them, as it holds everything the question acquired.
    """
    built = _early(tmp_path / "echo", anchor, _EnvelopeIdEchoesTheAsked(_population()))
    try:
        root = getattr(built.store, "inner", built.store).root
        outcomes: dict[str, Any] = {}
        answer_bytes: dict[str, bytes] = {}
        for side, subject in (("withheld", w.SUBJECT), ("nonexistent", w.NEVER)):
            outcome = _ask(built, subject)
            outcomes[side] = outcome
            if hasattr(outcome, "model_dump_json"):
                answer_bytes[side] = outcome.model_dump_json().encode("utf-8")
        _answered(outcomes)
        stored = {path.name: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    finally:
        built.close()
    for side, payload in answer_bytes.items():
        assert b"envelope-" not in payload, f"[{side}] an envelope id reached the answer"
    holding_an_id = sorted(name for name, payload in stored.items() if b"envelope-" in payload)
    assert not holding_an_id, f"an envelope id reached an artifact the deployment's store holds: {holding_an_id}"
    _judged(tmp_path, anchor, w.IN_PROCESS, _EnvelopeIdEchoesTheAsked(_population()))


# --- R3: every difference that is not delivery lineage still refuses ------------------------


def _refused_by_name(asks: dict[str, Any]) -> None:
    """Ask each side; every question must raise decision 4 (a)'s refusal, by type name, worded once, recording nothing."""
    refused: dict[str, UnsupportedComposition] = {}
    for side, (ask, store) in asks.items():
        before = _records(store)
        with pytest.raises(UnsupportedComposition) as raised:
            ask()
        refused[side] = raised.value
        assert _records(store) == before, f"[{side}] a refused question recorded something"
    names = {side: type(error).__name__ for side, error in refused.items()}
    assert set(names.values()) == {REFUSAL}, names
    messages = {str(error) for error in refused.values()}
    assert len(messages) == 1, f"one refusal for every subject, worded once: {sorted(messages)}"


class _RelabelsWhenAskedTheStandIn(w.PopulationSource):
    """A population read that, asked about the stand-in, also delivers the sibling labelled with the stand-in's URI."""

    def __call__(self, context: Any) -> Any:
        found = super().__call__(context)
        if context.request.subject != w.STAND_IN:
            return found
        relabelled = w.envelope_for(
            w.sibling_holding(label=w.STAND_IN), tenant=context.tenant_id, ingested_at=context.instant,
            envelope_id="envelope-sibling-relabelled",
        )
        return (*found, relabelled)


class _AnotherSourceWhenAskedTheStandIn(w.PopulationSource):
    """A population read that, asked about the stand-in, also delivers the sibling's record from a source naming it."""

    def __call__(self, context: Any) -> Any:
        found = super().__call__(context)
        if context.request.subject != w.STAND_IN:
            return found
        again = w.envelope_for(
            w.sibling_holding(), tenant=context.tenant_id, ingested_at=context.instant,
            envelope_id="envelope-acct-sibling",
        )
        named = SignalEnvelope.model_validate(
            {**again.model_dump(), "source": SourceIdentity(system_id=f"system-answering-{w.STAND_IN}").model_dump()}
        )
        return (*found, named)


#: The paved road's R3 sources: each differs from the probe's delivery only when asked about the stand-in.
_PAVED_R3 = {
    "claim-value": _RelabelsWhenAskedTheStandIn,
    "lineage-source": _AnotherSourceWhenAskedTheStandIn,
}


@pytest.mark.parametrize("how", sorted(_PAVED_R3))
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_r3_a_difference_that_is_not_delivery_lineage_refuses_every_question_on_the_paved_road(
    tmp_path: pathlib.Path, anchor: str, how: str
) -> None:
    """A claim value naming the stand-in, or a lineage entry whose source names it: every question refused alike."""
    withholding = _early(tmp_path / "withholding", anchor, _PAVED_R3[how](_population()))
    serving = _early(tmp_path / "serving", anchor, _PAVED_R3[how](_population()), active=False)
    try:
        _refused_by_name({
            "withheld": (lambda: withholding.ask(w.SUBJECT, None), withholding.store),
            "nonexistent": (lambda: withholding.ask(w.NEVER, None), withholding.store),
            "nonexistent-again": (lambda: withholding.ask(w.NEVER_2, None), withholding.store),
            "served": (lambda: serving.ask(w.SIBLING, None), serving.store),
        })
    finally:
        withholding.close()
        serving.close()


class _AdmitsWhenAskedTheStandIn(low._SubjectKeyedRefresh):
    """A low-road population read that, asked about the stand-in, also admits one claim through L2 that names it.

    ``relationship-end``: an edge from the withheld account to the stand-in.
    ``relationship-attribute``: an edge between two accounts the fabric holds, its attribute naming the stand-in.
    ``passage-anchor``: the withheld account's own claim again, its lineage anchored at a passage naming the stand-in.
    """

    def __init__(self, fabric: Any, *, text: str, how: str, stand_in: str) -> None:
        super().__init__(fabric, text=text)
        self._how = how
        self._stand_in = stand_in

    def __call__(self, *, request: Any, perspective: Any) -> None:
        worker = self._fabric.handle.worker
        worker.ingest(low._claim(low.WITHHELD_REF, self._text, envelope_id="claim-acquired", observed=low.REFRESHED))
        self.returned[request.subject] = self.returned.get(request.subject, 0) + 1
        if request.subject != self._stand_in:
            return
        tenant = self._fabric.tenant_id
        at = datetime.fromisoformat(low.INGESTED.replace("Z", "+00:00"))
        lineage = frozenset({
            LineageEntry(
                source=SourceIdentity(system_id="fixture-system"), envelope_id="claim-admitted", observed_at=at,
                passage_anchor=(
                    PassageAnchor(kind="fixture-passage", locator=self._stand_in) if self._how == "passage-anchor" else None
                ),
            )
        })
        if self._how == "passage-anchor":
            current = next(
                record.claim for record in self._fabric.handle.reader.as_of(tenant_id=tenant, at=low.ASKED_AT).entities
                if record.claim.entity_uri == low.WITHHELD and record.superseded_by is None
            )
            worker.admit_entity_claim(
                tenant_id=tenant,
                claim=current.model_copy(update={"lineage": lineage}),
            )
            return
        worker.admit_relationship_claim(
            tenant_id=tenant,
            claim=RelationshipClaim(
                tenant_id=tenant, observed_at=at, lineage=lineage, relationship_type="fixture-linked",
                subject_uri=low.WITHHELD,
                object_uri=self._stand_in if self._how == "relationship-end" else low._uri(low.OTHER_REF),
                attributes={"named": self._stand_in} if self._how == "relationship-attribute" else {},
            ),
        )


_LOW_R3 = ("relationship-end", "relationship-attribute", "passage-anchor")


@pytest.mark.parametrize("how", _LOW_R3)
@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_r3_a_difference_that_is_not_delivery_lineage_refuses_every_question_on_the_low_road(
    tmp_path: pathlib.Path, anchor: str, how: str
) -> None:
    """A relationship naming the stand-in, or a passage anchor naming it: the withheld and nonexistent questions refused alike."""
    stand_in = low._EarlyWithholding().subject_disclosure().undisclosed_subject

    def ask(side: str, subject: str) -> tuple[Any, Any]:
        booted = low._boot(tmp_path / side, with_similarity=False, anchor=anchor)
        seam = _AdmitsWhenAskedTheStandIn(booted[0], text=low.QUERY, how=how, stand_in=stand_in)

        def question() -> Any:
            try:
                return low._serve(
                    booted, subject, with_similarity=False, acquisition=seam,
                    withhold=frozenset({low.WITHHELD}), plan_factory=low._EarlyWithholding(),
                )
            finally:
                booted[0].handle.close()

        return question, booted[2]

    _refused_by_name({"withheld": ask("withheld", low.WITHHELD), "nonexistent": ask("nonexistent", low.MISSING)})


# --- what a failed check refuses: every question alike before acquisition, not after ------------------


class _WritesTheStandInWhenAskedTheSubject(w.SubjectKeyedSource):
    """A source that, asked about the subject it holds, also returns the stand-in's own record (and nothing else differs)."""

    def __call__(self, context: Any) -> Any:
        found = super().__call__(context)
        if context.request.subject != w.SUBJECT:
            return found
        extra = w.envelope_for(
            w.Holding(account_ref=w.STAND_IN_REF, book=w.OPEN_BOOK, label="stand-in label",
                      observed_at=w.asked_at() - timedelta(minutes=5)),
            tenant=context.tenant_id, ingested_at=context.instant, envelope_id="envelope-stand-in-beside-the-subject",
        )
        return (*found, extra)


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_the_check_after_acquisition_refuses_only_a_question_whose_own_acquisition_wrote_the_stand_in(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Measured for the controls register: the after-acquisition refusal depends on the question; the checks before do not.

    The source writes the stand-in only when it is handed the subject itself, so
    the check after acquisition refuses that question by name — the served
    deployment's, where the subject is disclosed — while every other question of
    the same deployment is answered as data, and under the policy the withheld
    subject (asked as the stand-in, never handed to the source) is answered as a
    nonexistent subject is.
    """
    holdings = {w.SUBJECT: w.subject_holding()}
    serving = _early(tmp_path / "serving", anchor, _WritesTheStandInWhenAskedTheSubject(holdings), active=False)
    withholding = _early(tmp_path / "withholding", anchor, _WritesTheStandInWhenAskedTheSubject(holdings))
    try:
        before = _records(serving.store)
        with pytest.raises(UnsupportedComposition) as refused:
            serving.ask(w.SUBJECT, None)
        assert type(refused.value).__name__ == REFUSAL, refused.value
        assert _records(serving.store) == before, "the refused question recorded something"
        answered = {
            "served deployment, an identifier nothing holds": _ask(serving, w.NEVER),
            "withholding deployment, the withheld subject": _ask(withholding, w.SUBJECT),
            "withholding deployment, an identifier nothing holds": _ask(withholding, w.NEVER),
        }
    finally:
        serving.close()
        withholding.close()
    _answered(answered)
