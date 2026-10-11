"""SEC-020, decision 4 (a): the early-withholding stand-in is verified to name nothing, not assumed to. SEC-020 is OPEN.

``D-IMPL-378`` (SDK-defined, CLAUDE.md §11). The configuration: a class whose
plan factory declares the early-withholding policy
(``ccf.products.resolver.SubjectDisclosingPlanFactoryProtocol``, Q8), so every
subject-dependent step is asked about the policy's declared stand-in
(``ccf.products.subject_disclosure.SubjectDisclosurePolicy.undisclosed_subject``)
in place of a subject the policy does not disclose.
``src/ccf/products/subject_disclosure.py::SubjectDisclosurePolicy._the_stand_in_is_admissible``
holds the stand-in only to the subject floor, and the resolver substituted it
unchecked. When the deployment's source holds the stand-in — under the stand-in
itself, or as a record the fabric names otherwise — the withheld subject's
answer is computed over what the source returned for it, an identifier nothing
holds is not, and the two answers differ (the final panel's G-STANDIN, its probe
``p_b01_standin_held``: ``vessel.computed_empty`` and the debt fields; measured
again on this branch's base for both forms).

Dave's ruling on decision 4, 2026-10-09 06:06 MST, confirmed at 06:21 MST, is
kept verbatim as a comment below.

What these tests hold the SDK to, by mechanism:

* **The refusal.** Every question to a deployment in which the stand-in names
  something is refused by name, ``UndisclosedSubjectSubstituteIsHeld`` — the
  withheld subject's, an identifier nothing holds, a second one and an
  ordinarily served subject's alike — with one message, and nothing is
  recorded. Before acquisition: the fabric as read before the subject-keyed
  phase names it (a declared population phase wrote it), or the source holds it
  (the phase acquires for the stand-in what it does not acquire for an
  identifier that names nothing); a refused question never hands the
  subject-keyed phase the asked subject. After acquisition: the fabric the plan
  would read names it.
* **Judged by the closing test's rules.** In such a deployment the withheld and
  nonexistent answers do not differ, at every door: either neither side raised
  and no channel differs beyond the noise floor, or both raised the stand-in
  refusal, by name and worded once — which counts only paired with the same
  deployment, the stand-in held nowhere, answering both questions with nothing
  told apart (CT-A (a)).

The controls are green before and after: the stand-in held nowhere, every
question is answered; and an early policy over a read that acquires the same
content whatever is asked (a population read left in the subject-keyed phase) is
not refused — the stand-in acquires nothing there that an identifier which
names nothing does not.
"""

# Dave, 2026-10-09 06:06 MST, verbatim (D-IMPL-378 dated amendment on main @ d429dcfa),
# item 4, confirmed at 06:21 MST ("4a"):
#   "(a). Verify the stand-in is absent before and after acquisition. A failed
#   check refuses without exposing subject-dependent differences."
# The option it names (records/2026-10-09-d-impl-378-final-panel/PANEL-BRIEF-FOR-DAVE.md
# section 4, decision 4): "(a) verify the stand-in absent like the P6 identifier".
# Dave, 2026-10-08 16:40 MST, on the P6 identifier, verbatim: "Verify that the
# fixed identifier is actually absent; do not assume it."
# Dave, 2026-10-08 12:29 MST, CT-A (a), verbatim: "Construction refusal counts,
# paired with a declared twin that successfully answers."

from __future__ import annotations

import pathlib
import re
from typing import Any

import pytest

from ccf.products.resolver import UnsupportedComposition
from tests.deployment.test_replay_binding import PRODUCT_CLASS
from tests.products import sec020_worlds as w
from tests.products import test_withheld_similarity_registry as low
from tests.products.test_sec020_combined_proof import _compare, _vacuous

#: The refusal decision 4 (a) raises, named as data so this module collects on a
#: tree that does not have it yet (the red commit) and fails there by
#: ``DID NOT RAISE`` rather than by an import error.
REFUSAL = "UndisclosedSubjectSubstituteIsHeld"

#: How the deployment's source holds the declared stand-in — the stand-in world's vocabulary, defined with the world in
#: ``sec020_worlds`` (``STAND_IN_HELD_AS``): ``itself``, ``another-uri``, ``population-phase``.
ITSELF = w.STAND_IN_ITSELF
ANOTHER_URI = w.STAND_IN_ANOTHER_URI
POPULATION_PHASE = w.STAND_IN_POPULATION_PHASE
HELD_AS = w.STAND_IN_HELD_AS
#: The account a source returns for the stand-in under ``another-uri``. Fixture vocabulary.
SHADOW_REF = w.STAND_IN_SHADOW_REF
_stand_in_holding = w.stand_in_holding


def _records(store: Any) -> frozenset[str]:
    """The content-addressed artifacts a deployment's store holds (its records and pins)."""
    root = getattr(store, "inner", store).root
    return frozenset(path.name for path in root.iterdir() if re.fullmatch(r"[0-9a-f]{64}", path.name))


def _early(base: pathlib.Path, anchor: str, *, held_as: str | None, active: bool) -> tuple[w.Deployment, Any]:
    """SEC-020's early-withholding paved deployment holding the subject; ``held_as`` says where the stand-in is held.

    ``held_as=None`` is the twin: the stand-in held nowhere. The stand-in world's own builder
    (``sec020_worlds.build_stand_in``).
    """
    return w.build_stand_in(base, anchor=anchor, held_as=held_as, active=active)


def _refused_by_name(asks: dict[str, Any]) -> dict[str, UnsupportedComposition]:
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
    return refused


# --- the refusal, by mechanism ---------------------------------------------------------


@pytest.mark.parametrize("held_as", HELD_AS)
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_a_stand_in_that_names_something_refuses_every_question_before_acquisition(
    tmp_path: pathlib.Path, anchor: str, held_as: str
) -> None:
    """The withheld subject, two identifiers nothing holds and a served subject: each refused, by name, alike."""
    withholding, withholding_source = _early(tmp_path / "withholding", anchor, held_as=held_as, active=True)
    serving, serving_source = _early(tmp_path / "serving", anchor, held_as=held_as, active=False)
    try:
        _refused_by_name({
            "withheld": (lambda: withholding.ask(w.SUBJECT, None), withholding.store),
            "nonexistent": (lambda: withholding.ask(w.NEVER, None), withholding.store),
            "nonexistent-again": (lambda: withholding.ask(w.NEVER_2, None), withholding.store),
            "served": (lambda: serving.ask(w.SUBJECT, None), serving.store),
        })
    finally:
        withholding.close()
        serving.close()
    asked = {"withholding": withholding_source.asked, "serving": serving_source.asked}
    assert not {w.SUBJECT, w.NEVER, w.NEVER_2} & set(asked["withholding"]), (
        f"a refused question never hands the subject-keyed phase the asked subject: {asked}"
    )
    assert w.SUBJECT not in asked["serving"], (
        f"a refused question never hands the subject-keyed phase the asked subject: {asked}"
    )


class _WritesTheStandInBesideTheSubject(w.SubjectKeyedSource):
    """``acquire`` that, asked about the subject it holds, also returns the stand-in's own record.

    Asked about the stand-in or about anything else it does not hold, it
    returns nothing: so only the fabric read AFTER the question's own
    acquisition names the stand-in.
    """

    def __call__(self, context: Any) -> Any:
        found = super().__call__(context)
        if context.request.subject != w.SUBJECT:
            return found
        extra = w.envelope_for(
            _stand_in_holding(w.STAND_IN_REF), tenant=context.tenant_id, ingested_at=context.instant,
            envelope_id="envelope-stand-in-beside-the-subject",
        )
        return (*found, extra)


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_a_fabric_that_names_the_stand_in_after_acquisition_is_refused_before_anything_is_recorded(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """After acquisition: the subject's own acquisition wrote the stand-in's record, so its question is refused by name."""
    built = w.open_paved(
        tmp_path / "serving", anchor=anchor,
        acquire=_WritesTheStandInBesideTheSubject({w.SUBJECT: w.subject_holding()}),
        project=w.plan_factory(early=True, plan_id=PRODUCT_CLASS, asker=w.ASKER, active=False),
    )
    try:
        _refused_by_name({"served": (lambda: built.ask(w.SUBJECT, None), built.store)})
    finally:
        built.close()


@pytest.mark.parametrize("anchor", (low.FROM_DECISION, low.FROM_ENTITY_FRESHNESS))
def test_a_stand_in_a_preloaded_fabric_names_is_refused_with_no_acquisition_on_the_low_road(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """No acquisition phase: the stand-in names a record the fabric already holds, so every question is refused alike."""

    class _StandInTheFabricHolds(low._EarlyWithholding):
        def subject_disclosure(self) -> Any:
            from ccf.products.subject_disclosure import SubjectDisclosurePolicy  # noqa: PLC0415

            return SubjectDisclosurePolicy(
                undisclosed_subject=low._uri(low.OTHER_REF),
                by_principal={low.PERSPECTIVE.principal_id: frozenset({low.WITHHELD})},
                by_role={},
            )

    def ask(side: str, subject: str) -> tuple[Any, Any]:
        booted = low._boot(tmp_path / side, with_similarity=False, anchor=anchor)

        def question() -> Any:
            try:
                return low._serve(
                    booted, subject, with_similarity=False, acquisition=None,
                    withhold=frozenset({low.WITHHELD}), plan_factory=_StandInTheFabricHolds(),
                )
            finally:
                booted[0].handle.close()

        return question, booted[2]

    _refused_by_name({"withheld": ask("withheld", low.WITHHELD), "nonexistent": ask("nonexistent", low.MISSING)})


# --- judged by the closing test's rules, at every door -------------------------------------

#: The sides one deployment is asked, by the closing test's names for the same-deployment comparison.
_SIDES = ((w.CF_WITHHELD, w.SUBJECT), (w.SAME_NONEXISTENT, w.NEVER), (w.SAME_FLOOR, w.NEVER_2))


@pytest.mark.parametrize("door", w.DOORS)
@pytest.mark.parametrize("held_as", (ITSELF, ANOTHER_URI))
@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_a_stand_in_the_source_holds_leaves_withheld_and_nonexistent_indistinguishable(
    tmp_path: pathlib.Path, anchor: str, held_as: str, door: str
) -> None:
    """The panel's probe as a test: the withheld and nonexistent answers must not differ, by the closing test's rules.

    The run is the stand-in world (``sec020_worlds.stand_in_run``): the withholding deployment asked about the
    subject and two identifiers nothing holds, the same deployment with its policy off asked about the subject, and,
    on the run itself, its declared working twin, the stand-in held nowhere (``sec020_worlds.DECLARED_WORKING_TWIN``).
    """
    run = w.stand_in_run(tmp_path, anchor=anchor, door=door, held_as=held_as)
    channels = w.channels_for(comparison=w.SAME_DEPLOYMENT, shape=w.SUBJECT_KEYED, door=door)
    raised = {side: run.raised(side).get(w.ONLY, "") for side, _ in _SIDES}
    if not any(raised.values()):
        for channel in channels:
            differing, floor, withheld, nonexistent = _compare(run, comparison=w.SAME_DEPLOYMENT, channel=channel)
            assert not differing, (
                f"[{anchor}, {held_as}, {door}, {channel}] a withheld subject is distinguishable from a"
                f" nonexistent one at {sorted(differing)} (noise floor, not counted: {sorted(floor)})\n"
                f"  withheld:    {w.render(withheld)}\n  nonexistent: {w.render(nonexistent)}"
            )
        return
    # CT-A (a): the refusal counts only by name, worded once on every side, and
    # paired with the same deployment, the stand-in held nowhere, answering.
    assert all(message.startswith(f"{REFUSAL}:") for message in raised.values()), raised
    assert len(set(raised.values())) == 1, f"the refusal must be worded once, whatever was asked: {raised}"
    for channel in channels:
        differing, floor, withheld, nonexistent = _compare(run, comparison=w.SAME_DEPLOYMENT, channel=channel)
        assert not differing, (
            f"[{anchor}, {held_as}, {door}, {channel}] the refusal is not identical for the withheld and the"
            f" nonexistent subject at {sorted(differing)}\n  withheld: {w.render(withheld)}\n"
            f"  nonexistent: {w.render(nonexistent)}"
        )
    twin = run.notes[w.DECLARED_WORKING_TWIN]
    vacuous = _vacuous(twin, w.CF_WITHHELD, w.SAME_NONEXISTENT, either=True)
    assert not vacuous, f"[{anchor}, {door}] the twin did not answer, so the refusal is not evidence: {vacuous}"
    for channel in channels:
        differing, floor, _, _ = _compare(twin, comparison=w.SAME_DEPLOYMENT, channel=channel)
        assert not differing, (
            f"[{anchor}, {door}, {channel}] the twin, the stand-in held nowhere, tells the withheld subject"
            f" apart at {sorted(differing)} (noise floor, not counted: {sorted(floor)})"
        )


# --- controls: green before and after --------------------------------------------------


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_control_the_stand_in_held_nowhere_answers_every_question(tmp_path: pathlib.Path, anchor: str) -> None:
    """The same deployment, the stand-in held nowhere: every question answered, nothing raised."""
    withholding, _ = _early(tmp_path / "withholding", anchor, held_as=None, active=True)
    serving, _ = _early(tmp_path / "serving", anchor, held_as=None, active=False)
    try:
        outcomes = {
            "withheld": withholding.ask(w.SUBJECT, None),
            "nonexistent": withholding.ask(w.NEVER, None),
            "served": serving.ask(w.SUBJECT, None),
        }
    finally:
        withholding.close()
        serving.close()
    assert all(type(outcome).__name__ in ("ServedProduct", "RefusalEnvelope") for outcome in outcomes.values()), outcomes


@pytest.mark.parametrize("anchor", w.ANCHORS)
def test_control_an_early_policy_over_a_population_read_is_not_refused(tmp_path: pathlib.Path, anchor: str) -> None:
    """A read that acquires the same content whatever is asked: the stand-in acquires nothing an unheld identifier does not."""
    built = w.build_population(tmp_path / "early", anchor=anchor, holds=True, active=True, early=True)
    try:
        outcomes = {"withheld": built.ask(w.SUBJECT, None), "nonexistent": built.ask(w.NEVER, None)}
    finally:
        built.close()
    assert all(type(outcome).__name__ in ("ServedProduct", "RefusalEnvelope") for outcome in outcomes.values()), outcomes
