"""SEC-020, ruling P6 (a): a population read left inside the subject-keyed phase must not run. SEC-020 is OPEN.

``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). The configuration: a class that
may withhold its subject and declares no early policy, so its projection
withholds late, inside the plan; and a subject-keyed acquisition that reads
content which does not depend on the subject asked (a population read left in
``acquire`` rather than declared as Q7's population phase). A withheld subject
is then re-rendered over the fabric as it stood before the subject-keyed phase
(``D-IMPL-376`` (3), route A), while an identifier nothing holds is rendered
over everything that phase read for it, so the two answers differ. SEC-020's
closing test measures it in its ``population`` shape.

Dave ruled P6 (a), a conditional implementation go, on 2026-10-08 at 16:40 MST;
both rulings are kept verbatim as comments below (prose addressed to a reader
is what the No-Hardcoding lint refuses in a string literal, tests included).
The probe is not closure: a source that recognizes the probe identifier is not
detected, and that counterexample is kept visible beside these tests.

What these tests hold the SDK to, by mechanism:

* **The refusal.** Every question to such a product is refused by name,
  ``PopulationReadInSubjectKeyedPhase``, the withheld subject's and an
  identifier nothing holds alike, with one message, and the subject-keyed
  phase is never handed either asked identifier: it is asked about
  ``ccf.products.resolver.UNHELD_SUBJECT_PROBE`` instead, and the question is
  refused before it is asked about anything else. On the paved road
  (``open_product``) and on the low road (``GovernedResolver`` composed by
  hand).
* **The order (Dave's condition: "prove it runs before real-subject
  acquisition").** The subject-keyed phase and the fabric's reads are logged
  in one sequence: the probe identifier is handed to the phase, and the fabric
  is read again (the comparison), strictly before the phase is handed the
  question's subject; when the probe refuses, the phase is never handed the
  question's subject at all. On both roads, and with a declared population
  phase, which runs before both.

The controls are green before and after the restriction: the same read
declared as the population phase (Q7), a source keyed on the subject, the same
read under a declared early policy (Q8), and the same read under a class that
affirms ``subject_withholding: never`` (Q12). Each still answers, and none of
them is asked about the probe identifier unless it is a class the restriction
reads (a class that may withhold and declares no early policy).
"""

# Dave, 2026-10-08 12:29 MST, verbatim (D-IMPL-378 dated amendment on main @ 75229b61):
#   "P6 — (a) NOT approved as sufficient for closure: The sheet says the SDK
#   cannot detect this configuration. Keep its failing cells visible and seek the
#   smallest enforceable admission restriction. Calling it unsupported does not
#   prevent it running."
#
# Dave, 2026-10-08 16:40 MST, verbatim (D-IMPL-378 dated amendment on main @ 35315abf), item 2:
#   "P6: (a), conditional implementation GO. Amend Q10 to permit the probe.
#   Extend CT-A with the working declared-population twin. Do not declare
#   closure based on this probe alone: prove it runs before real-subject
#   acquisition, and retain the counterexample where a source treats the probe
#   identifier differently. Verify that the fixed identifier is actually absent;
#   do not assume it."

from __future__ import annotations

import pathlib
from typing import Any

import pytest

import ccf.products.resolver as resolver_module
from ccf.graph.reader import BaseGraphReader
from ccf.products.resolver import UnsupportedComposition
from tests.products import sec020_worlds as w
from tests.products import test_withheld_similarity_registry as low

#: The refusal the restriction raises, named as data so this module collects on
#: a tree that does not have it yet (the red commit) and fails there by
#: ``DID NOT RAISE`` rather than by an import error.
REFUSAL = "PopulationReadInSubjectKeyedPhase"
#: The identifier the subject-keyed phase is asked about first, read off the
#: resolver module at call time for the same reason.
PROBE_NAME = "UNHELD_SUBJECT_PROBE"


def _probe() -> Any:
    return getattr(resolver_module, PROBE_NAME, None)


def _refused_by_name(ask: Any, subjects: tuple[str, ...]) -> dict[str, UnsupportedComposition]:
    """Ask each subject; every question must raise the restriction's refusal, by type name."""
    refused: dict[str, UnsupportedComposition] = {}
    for subject in subjects:
        with pytest.raises(UnsupportedComposition) as raised:
            ask(subject)
        refused[subject] = raised.value
    names = {subject: type(error).__name__ for subject, error in refused.items()}
    assert set(names.values()) == {REFUSAL}, names
    messages = {str(error) for error in refused.values()}
    assert len(messages) == 1, f"one refusal for every subject, worded once: {sorted(messages)}"
    return refused


# --- the paved road: the closing test's own ``population`` deployment -------------------


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_a_population_read_in_acquire_answers_no_question_on_the_paved_road(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """``open_product`` with a population read in ``acquire`` and a late withhold: refused, by name, before the subject is fetched."""
    built = w.build_population(tmp_path / "withholding", anchor=anchor, holds=True, active=True)
    try:
        _refused_by_name(built.ask, (w.SUBJECT, w.NEVER))
        source = built.notes["opened"]._acquire
    finally:
        built.close()
    assert w.SUBJECT not in source.asked and w.NEVER not in source.asked, (
        f"refused before the subject-keyed phase was handed either asked identifier: {source.asked}"
    )
    assert source.asked == [_probe(), _probe()], (
        f"the subject-keyed phase is asked about the probe identifier, once per question: {source.asked}"
    )


# --- the low road: a hand-composed resolver over the same kind of read -------------------


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_a_population_read_in_the_seam_answers_no_question_on_the_low_road(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """``GovernedResolver(acquisition=...)`` whose seam writes the same claim whatever is asked: refused alike."""
    seams: dict[str, Any] = {}

    def ask(subject: str) -> Any:
        booted = low._boot(tmp_path / f"fabric-{len(seams)}", with_similarity=False, anchor=anchor)
        try:
            seams[subject] = low._PopulationRefresh(booted[0], text=low.QUERY)
            return low._serve(
                booted, subject, with_similarity=False, acquisition=seams[subject],
                withhold=frozenset({low.WITHHELD}),
            )
        finally:
            booted[0].handle.close()

    _refused_by_name(ask, (low.WITHHELD, low.MISSING))
    for subject, seam in seams.items():
        assert set(seam.returned) == {_probe()}, (
            f"[{subject}] the seam is asked about the probe identifier and never about the question's"
            f" subject: {seam.returned}"
        )


# --- the order: the probe and its comparison come before the subject ---------------------


class _Sequence:
    """One ordered log of what the subject-keyed phase was handed and of every read of a fabric.

    ``("phase", <identifier>)`` when the subject-keyed phase is called,
    ``("population", "")`` when a declared population phase is, and
    ``("read", "")`` when any fabric is read as of an instant
    (:meth:`ccf.graph.reader.BaseGraphReader.as_of`, the store read under every
    booted fabric's reader) — so the order between the three is observed, not
    inferred from the resolver's code.
    """

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def phase_calls(self) -> list[str]:
        return [identifier for kind, identifier in self.events if kind == "phase"]

    def reads_between(self, start: int, end: int | None = None) -> int:
        return sum(1 for kind, _ in self.events[start:end] if kind == "read")


@pytest.fixture
def sequence(monkeypatch: pytest.MonkeyPatch) -> _Sequence:
    """Log every as-of read of a fabric into the sequence, in order, for this test only."""
    log = _Sequence()
    as_of = BaseGraphReader.as_of

    def logged_as_of(self: BaseGraphReader, *, tenant_id: str, at: Any) -> Any:
        log.events.append(("read", ""))
        return as_of(self, tenant_id=tenant_id, at=at)

    monkeypatch.setattr(BaseGraphReader, "as_of", logged_as_of)
    return log


class _LoggedAcquire:
    """The paved road's ``acquire``: the subject it is handed goes into the sequence, then the source runs."""

    def __init__(self, source: Any, log: _Sequence) -> None:
        self._source = source
        self._log = log

    def __call__(self, context: Any) -> Any:
        self._log.events.append(("phase", context.request.subject))
        return self._source(context)


class _LoggedPopulation:
    """The paved road's declared population half, logged when it runs."""

    def __init__(self, half: Any, log: _Sequence) -> None:
        self._half = half
        self._log = log

    def __call__(self, context: Any) -> Any:
        self._log.events.append(("population", ""))
        return self._half(context)


class _LoggedSeam:
    """A low-road subject-keyed seam: the subject it is handed goes into the sequence, then the seam runs."""

    def __init__(self, seam: Any, log: _Sequence) -> None:
        self._seam = seam
        self._log = log

    def __call__(self, *, request: Any, perspective: Any) -> None:
        self._log.events.append(("phase", request.subject))
        self._seam(request=request, perspective=perspective)


def _assert_probed_then_asked(log: _Sequence, subject: str, *, case: str) -> None:
    """The probe is handed to the phase, the fabric is read again, and only then is the subject handed."""
    calls = log.phase_calls()
    assert calls == [_probe(), subject], (
        f"[{case}] the subject-keyed phase is handed the probe identifier first, then the question's"
        f" subject, once each: {calls}"
    )
    probe_at = log.events.index(("phase", _probe()))
    subject_at = log.events.index(("phase", subject))
    assert log.reads_between(0, probe_at) >= 1, (
        f"[{case}] no fabric read before the probe, so there is nothing to compare its result against:"
        f" {log.events}"
    )
    assert log.reads_between(probe_at + 1, subject_at) >= 1, (
        f"[{case}] the fabric was not read again between the probe and the question's subject, so the"
        f" comparison did not precede the real acquisition: {log.events}"
    )


def _assert_refused_before_the_subject(log: _Sequence, *, case: str) -> None:
    """The probe is handed to the phase, the fabric is read again, and the subject is never handed."""
    calls = log.phase_calls()
    assert calls == [_probe()], (
        f"[{case}] a refused question hands the subject-keyed phase the probe identifier and nothing"
        f" else: {calls}"
    )
    probe_at = log.events.index(("phase", _probe()))
    assert log.reads_between(0, probe_at) >= 1, f"[{case}] no fabric read before the probe: {log.events}"
    assert log.reads_between(probe_at + 1) >= 1, (
        f"[{case}] the fabric was not read after the probe, so the refusal was not decided by comparing"
        f" it: {log.events}"
    )


def _paved(
    base: pathlib.Path, anchor: str, *, acquire: Any, early: bool = False, **overrides: Any
) -> w.Deployment:
    from tests.deployment.test_replay_binding import PRODUCT_CLASS  # noqa: PLC0415

    return w.open_paved(
        base, anchor=anchor, acquire=acquire,
        project=w.plan_factory(early=early, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=True),
        **overrides,
    )


def _population() -> dict[str, w.Holding]:
    return {w.SIBLING: w.sibling_holding(), w.SUBJECT: w.subject_holding()}


@pytest.mark.parametrize("asked", ["withheld", "never-held"])
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_order_the_probe_and_its_comparison_precede_the_subject_on_the_paved_road(
    tmp_path: pathlib.Path, anchor: str, asked: str, sequence: _Sequence
) -> None:
    """A source keyed on the subject: probe, read, then the subject — and the question is answered."""
    subject = {"withheld": w.SUBJECT, "never-held": w.NEVER}[asked]
    built = _paved(
        tmp_path / "keyed", anchor,
        acquire=_LoggedAcquire(w.SubjectKeyedSource({w.SUBJECT: w.subject_holding()}), sequence),
    )
    try:
        outcome = built.ask(subject)
    finally:
        built.close()
    assert type(outcome).__name__ in {"ServedProduct", "RefusalEnvelope"}, outcome
    _assert_probed_then_asked(sequence, subject, case=f"paved, keyed, {asked}")


@pytest.mark.parametrize("asked", ["withheld", "never-held"])
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_order_a_refused_question_never_hands_the_subject_to_the_phase_on_the_paved_road(
    tmp_path: pathlib.Path, anchor: str, asked: str, sequence: _Sequence
) -> None:
    """A population read in ``acquire``: probe, read, refusal — the subject is never handed to the phase."""
    subject = {"withheld": w.SUBJECT, "never-held": w.NEVER}[asked]
    built = _paved(tmp_path / "population", anchor, acquire=_LoggedAcquire(w.PopulationSource(_population()), sequence))
    try:
        with pytest.raises(UnsupportedComposition) as raised:
            built.ask(subject)
    finally:
        built.close()
    assert type(raised.value).__name__ == REFUSAL, raised.value
    _assert_refused_before_the_subject(sequence, case=f"paved, population in acquire, {asked}")


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_order_a_declared_population_phase_runs_first_then_the_probe_then_the_subject(
    tmp_path: pathlib.Path, anchor: str, sequence: _Sequence
) -> None:
    """Q7's declared population phase is handed no subject and runs before the probe; the subject comes last."""
    built = _paved(
        tmp_path / "declared", anchor,
        acquire=_LoggedAcquire(w.SubjectKeyedSource({}), sequence),
        population=_LoggedPopulation(w.PopulationHalf(_population()), sequence),
    )
    try:
        outcome = built.ask(w.SUBJECT)
    finally:
        built.close()
    assert type(outcome).__name__ in {"ServedProduct", "RefusalEnvelope"}, outcome
    _assert_probed_then_asked(sequence, w.SUBJECT, case="paved, declared population phase")
    assert sequence.events.index(("population", "")) < sequence.events.index(("phase", _probe())), (
        f"the declared population phase runs before the probe: {sequence.events}"
    )


@pytest.mark.parametrize("asked", ["withheld", "never-held"])
@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_order_the_probe_and_its_comparison_precede_the_subject_on_the_low_road(
    tmp_path: pathlib.Path, anchor: str, asked: str, sequence: _Sequence
) -> None:
    """A hand-composed resolver over a seam keyed on the subject: probe, read, then the subject."""
    subject = {"withheld": low.WITHHELD, "never-held": low.MISSING}[asked]
    booted = low._boot(tmp_path / "fabric", with_similarity=False, anchor=anchor)
    try:
        seam = _LoggedSeam(low._SubjectKeyedRefresh(booted[0], text=low.QUERY), sequence)
        outcome = low._serve(
            booted, subject, with_similarity=False, acquisition=seam, withhold=frozenset({low.WITHHELD})
        )
    finally:
        booted[0].handle.close()
    assert type(outcome).__name__ in {"ServedProduct", "RefusalEnvelope"}, outcome
    _assert_probed_then_asked(sequence, subject, case=f"low road, keyed, {asked}")


@pytest.mark.parametrize("asked", ["withheld", "never-held"])
@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_order_a_refused_question_never_hands_the_subject_to_the_phase_on_the_low_road(
    tmp_path: pathlib.Path, anchor: str, asked: str, sequence: _Sequence
) -> None:
    """A hand-composed resolver over a seam that writes whatever is asked: probe, read, refusal."""
    subject = {"withheld": low.WITHHELD, "never-held": low.MISSING}[asked]
    booted = low._boot(tmp_path / "fabric", with_similarity=False, anchor=anchor)
    try:
        seam = _LoggedSeam(low._PopulationRefresh(booted[0], text=low.QUERY), sequence)
        with pytest.raises(UnsupportedComposition) as raised:
            low._serve(booted, subject, with_similarity=False, acquisition=seam, withhold=frozenset({low.WITHHELD}))
    finally:
        booted[0].handle.close()
    assert type(raised.value).__name__ == REFUSAL, raised.value
    _assert_refused_before_the_subject(sequence, case=f"low road, population in the seam, {asked}")


# --- controls: green before the restriction and after it ---------------------------------


def _answers(ask: Any, subjects: tuple[str, ...]) -> None:
    for subject in subjects:
        outcome = ask(subject)
        assert type(outcome).__name__ in {"ServedProduct", "RefusalEnvelope"}, (subject, outcome)


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_control_the_same_read_declared_as_the_population_phase_answers(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Q7's slot: the same population declared through ``open_product(population=...)`` is answered."""
    built = w.build_population(tmp_path / "declared", anchor=anchor, holds=True, active=True, declared=True)
    try:
        _answers(built.ask, (w.SUBJECT, w.NEVER))
    finally:
        built.close()


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_control_a_source_keyed_on_the_subject_answers(tmp_path: pathlib.Path, anchor: str) -> None:
    """The paved road's own shape, which withholds late through route A, is answered."""
    built = w.build_subject_keyed(tmp_path / "keyed", anchor=anchor, holds=True, active=True)
    try:
        _answers(built.ask, (w.SUBJECT, w.NEVER))
    finally:
        built.close()


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_control_an_early_policy_over_the_same_read_answers_and_is_not_probed(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Q8: a declared early policy is outside the restriction; the read is asked about the stand-in in place of the withheld subject.

    Not probed in P6 (a)'s sense: the class is answered, never refused by the
    restriction. ``D-IMPL-378`` decision 4 (a) (Dave, 2026-10-09 06:06 MST,
    confirmed 06:21) verifies its stand-in instead, so before each question the
    read is asked about the probe identifier (the baseline) and then the
    stand-in; a read that acquires the same content whatever is asked adds
    nothing for the stand-in, and the question is answered.
    """
    built = w.build_population(tmp_path / "early", anchor=anchor, holds=True, active=True, early=True)
    try:
        _answers(built.ask, (w.SUBJECT, w.NEVER))
        source = built.notes["opened"]._acquire
    finally:
        built.close()
    assert source.asked == [_probe(), w.STAND_IN, w.STAND_IN, _probe(), w.STAND_IN, w.NEVER], source.asked


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_p6_control_a_class_that_never_withholds_answers_and_is_not_probed(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Q12: a class affirming ``subject_withholding: never`` is outside the restriction."""
    built = w.build_population(tmp_path / "never", anchor=anchor, holds=True, active=False, never=True)
    try:
        _answers(built.ask, (w.SUBJECT, w.NEVER))
        source = built.notes["opened"]._acquire
    finally:
        built.close()
    assert source.asked == [w.SUBJECT, w.NEVER], source.asked


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_p6_control_the_low_road_declared_population_phase_answers(tmp_path: pathlib.Path, anchor: str) -> None:
    """The low road's population phase, declared (Q7), over a seam keyed on the subject, is answered."""

    def ask(subject: str) -> Any:
        booted = low._boot(tmp_path / f"fabric-{subject.rsplit('/', 1)[-1][:12]}", with_similarity=False, anchor=anchor)
        try:
            return low._serve(
                booted, subject, with_similarity=False,
                acquisition=low._SubjectKeyedRefresh(booted[0], text=low.QUERY),
                population_acquisition=low._DeclaredPopulationRefresh(booted[0], text=low.QUERY),
                withhold=frozenset({low.WITHHELD}),
            )
        finally:
            booted[0].handle.close()

    _answers(ask, (low.WITHHELD, low.MISSING))
