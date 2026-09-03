"""The supersede-only λ_c class — ledger row ``24.5-L-22`` (whitepaper §7.7.1–§7.7.2).

Phase 24.5 criterion 17: ``HalfLifeEntry`` can express an event-driven class
that does not decay, ``freshness`` honors it, the reference scorer and
``assess_debt`` handle it, and it is stable under replay. Everything is
proven here, in ``tests/``, over test-owned vocabulary; cp-03's artifacts,
whose omitted Restatement row is the finding this row closes, are **not**
re-declared (``examples/`` is closed to this phase).

How criterion 17's "composition and replay tests cover it" is discharged
------------------------------------------------------------------------
The mixed-class ``FreshnessScorer`` → ``assess_debt`` end-to-end test
(:func:`test_assess_debt_handles_a_table_with_a_supersede_only_class`) **is**
the composition test for this row. It composes the reference path — table →
``decay_mode_of`` → ``freshness`` → ``FreshnessScorer.score`` → ``DebtFactors``
→ ``assess_debt`` — over ONE table holding both modes. No operator reads the
λ_c table, so the n² operator suite (``tests/properties/test_composition.py``)
is not the instrument for ``L-22`` and is not edited. Replay is the
determinism test
(:func:`test_the_computation_is_deterministic_and_the_table_hashes_identically_twice`):
two parses hash identically and a decision replays against the pinned
artifact version, so a decision made under a supersede-only class replays
byte-exactly.

Every rate, driver, event name and threshold below is this module's own
(CINV-01 reaches ``tests/``): nothing here is a calibration, and nothing here
is a product's.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    HALF_LIFE_TABLE,
    DebtProfile,
    HalfLifeEntry,
    HalfLifeTable,
    parse_artifact,
)
from ccf.halflife.assessment import DebtSignal
from ccf.halflife.debt import DebtFactors, FreshnessScorer, assess_debt
from ccf.halflife.decay import (
    MissingHalfLife,
    NoDecayCurve,
    Observation,
    TemporalOrderError,
    decay_mode_of,
    freshness,
    half_life_of,
    relevance_ratio,
)

#: The decision instant. A test input, never a clock read.
NOW = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

#: Test-owned observation-type vocabulary. The SDK enumerates none of it.
EVENT_DRIVEN = "test.rewritten-by-event"
CURVE = "test.decays-on-a-curve"
CURVE_SECONDS = 3600

#: The ages the whole-at-any-age claim is measured at: a second, a year, a decade.
AGES = (
    timedelta(seconds=1),
    timedelta(days=365),
    timedelta(days=3650),
)


def _document() -> dict[str, Any]:
    """One table document holding BOTH modes — the shape a deployment authors."""
    return {
        "semver": "1.0.0",
        "entries": {
            EVENT_DRIVEN: {
                "decay": "supersede-only",
                "decay_driver": "test.rewrite",
                "supersession_event": "test.superseding-event",
            },
            CURVE: {
                "half_life_seconds": CURVE_SECONDS,
                "decay_driver": "test.driver",
                "supersession_event": "test.supersession",
            },
        },
    }


@pytest.fixture(scope="module")
def table() -> HalfLifeTable:
    return HalfLifeTable.model_validate(_document())


def _observation(observation_type: str, age: timedelta) -> Observation:
    return Observation(observation_type=observation_type, observed_at=NOW - age)


def _profile() -> DebtProfile:
    return DebtProfile(
        semver="1.0.0",
        risk_sensitivity=Decimal("1.0"),
        forced_llm_threshold=Decimal("0.40"),
        fail_closed_threshold=Decimal("0.90"),
    )


# --- expressibility (criterion 17, the entry shape) --------------------------


def test_a_supersede_only_class_is_expressible_without_a_rate(
    table: HalfLifeTable,
) -> None:
    """The table can now say "this class supersedes and does not decay" with no number."""
    entry = HalfLifeEntry(
        decay="supersede-only",
        decay_driver="test.rewrite",
        supersession_event="test.superseding-event",
    )
    assert entry.decay == "supersede-only"
    assert entry.half_life_seconds is None
    assert entry.supersession_event == "test.superseding-event"

    parsed = table.entries[EVENT_DRIVEN]
    assert parsed.decay == "supersede-only"
    assert parsed.half_life_seconds is None
    # The curve sibling in the same table is the four-column row it always was.
    assert table.entries[CURVE].decay == "curve"
    assert table.entries[CURVE].half_life_seconds == CURVE_SECONDS


def test_a_number_beside_supersede_only_is_refused() -> None:
    """No unused field: a rate the reader never consults is refused, not ignored."""
    with pytest.raises(ValidationError, match="second, unused field"):
        HalfLifeEntry(
            decay="supersede-only",
            half_life_seconds=1,
            decay_driver="test.rewrite",
            supersession_event="test.superseding-event",
        )


def test_a_curve_class_still_declares_its_rate_and_the_rate_is_still_positive() -> None:
    """The two ``curve`` refusals survive the reshaping, message and all."""
    with pytest.raises(ValidationError, match="no default rate exists"):
        HalfLifeEntry(decay_driver="d", supersession_event="s")
    with pytest.raises(ValidationError, match="half_life_seconds must be positive"):
        HalfLifeEntry(half_life_seconds=0, decay_driver="d", supersession_event="s")


def test_supersession_event_is_required_in_both_modes() -> None:
    """Under supersede-only the event is the ONLY thing that ends relevance."""
    with pytest.raises(ValidationError):
        HalfLifeEntry(decay="supersede-only", decay_driver="test.rewrite")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        HalfLifeEntry(half_life_seconds=1, decay_driver="d")  # type: ignore[call-arg]


# --- freshness (criterion 17, the decay reader) ------------------------------


def test_freshness_is_whole_at_any_age_for_a_supersede_only_class(
    table: HalfLifeTable,
) -> None:
    """Retained relevance is exactly 1 at a second, a year and a decade.

    The curve sibling in the SAME table is the control: over the same ages it
    sits strictly below 1 and falls, so a reader cannot mistake "whole" for
    "the curve happens to be flat". At a year and a decade against a one-hour
    half-life the ratio quantizes to the same ``0E-18``, so the control asserts
    a fall from the first age to the last, not three distinct figures.
    """
    for age in AGES:
        figure = freshness(
            _observation(EVENT_DRIVEN, age),
            now=NOW,
            table=table,
            risk_sensitivity=Decimal(1),
        )
        assert figure == Decimal(1), (
            f"a supersede-only observation aged {age} scored {figure}, not 1"
        )

    control = [
        freshness(
            _observation(CURVE, age),
            now=NOW,
            table=table,
            risk_sensitivity=Decimal(1),
        )
        for age in AGES
    ]
    assert all(figure < Decimal(1) for figure in control)
    assert control == sorted(control, reverse=True)
    assert control[0] > control[-1]


def test_risk_sensitivity_does_not_touch_a_supersede_only_class(
    table: HalfLifeTable,
) -> None:
    """The Freshness Budget is ``λ_c × Risk Sensitivity``; with no λ_c there is no budget to spend."""
    figures = {
        freshness(
            _observation(EVENT_DRIVEN, timedelta(days=365)),
            now=NOW,
            table=table,
            risk_sensitivity=sensitivity,
        )
        for sensitivity in (Decimal("0.01"), Decimal(1), Decimal(100))
    }
    assert figures == {Decimal(1)}


def test_half_life_of_refuses_to_hand_a_curve_for_a_supersede_only_class(
    table: HalfLifeTable,
) -> None:
    """A caller that wants a curve for an event-driven class is asking the wrong question."""
    with pytest.raises(NoDecayCurve, match=EVENT_DRIVEN):
        half_life_of(table, EVENT_DRIVEN)
    # The curve sibling still answers.
    assert half_life_of(table, CURVE) == timedelta(seconds=CURVE_SECONDS)
    # And the two lookup refusals are distinct authoring states, not one.
    assert not issubclass(NoDecayCurve, MissingHalfLife)
    assert not issubclass(MissingHalfLife, NoDecayCurve)


def test_decay_mode_of_reports_the_declared_mode_and_refuses_an_undeclared_type(
    table: HalfLifeTable,
) -> None:
    assert decay_mode_of(table, EVENT_DRIVEN) == "supersede-only"
    assert decay_mode_of(table, CURVE) == "curve"
    with pytest.raises(MissingHalfLife):
        decay_mode_of(table, "test.never-declared")


# --- the reference scorer and assess_debt (criterion 17, composition) --------


def test_the_reference_scorer_averages_a_supersede_only_observation_as_whole(
    table: HalfLifeTable,
) -> None:
    """``FreshnessScorer.score`` over one of each equals the mean of 1 and the curve's ratio."""
    scorer = FreshnessScorer(table=table, risk_sensitivity=Decimal(1))
    aged_a_decade = _observation(EVENT_DRIVEN, timedelta(days=3650))
    at_one_half_life = _observation(CURVE, timedelta(seconds=CURVE_SECONDS))

    scored = scorer.score((aged_a_decade, at_one_half_life), now=NOW)

    curve_ratio = relevance_ratio(
        elapsed=timedelta(seconds=CURVE_SECONDS),
        half_life=timedelta(seconds=CURVE_SECONDS),
    )
    assert curve_ratio == Decimal(1) / Decimal(2)
    assert scored == (Decimal(1) + curve_ratio) / Decimal(2)


def test_assess_debt_handles_a_table_with_a_supersede_only_class(
    table: HalfLifeTable,
) -> None:
    """The reference path end to end, over one table holding both modes.

    This is the composition test for ``24.5-L-22`` (module docstring): table →
    ``decay_mode_of`` → ``freshness`` → ``FreshnessScorer.score`` →
    ``DebtFactors`` → ``assess_debt``. The signal follows the profile's
    thresholds as the curve sibling ages; the supersede-only observation stays
    whole throughout and is why the same mix lands in a LOWER band than the
    curve observation would alone.
    """
    scorer = FreshnessScorer(table=table, risk_sensitivity=Decimal(1))
    profile = _profile()
    whole = _observation(EVENT_DRIVEN, timedelta(days=3650))

    def assessed_with(curve_age: timedelta) -> tuple[Decimal, DebtSignal]:
        figure = scorer.score((whole, _observation(CURVE, curve_age)), now=NOW)
        outcome = assess_debt(
            DebtFactors(
                freshness=figure,
                completeness=Decimal(1),
                semantic_consistency=Decimal(1),
            ),
            profile=profile,
        )
        assert outcome.factors.freshness == figure
        return outcome.debt, outcome.signal

    # One half-life: F = (1 + 1/2)/2 = 0.75 → D_c = 0.25, under the 0.40 band.
    low_debt, low_signal = assessed_with(timedelta(seconds=CURVE_SECONDS))
    assert low_signal is DebtSignal.OK
    assert low_debt == Decimal("0.25")

    # Four half-lives: F = (1 + 1/16)/2 = 0.53125 → D_c = 0.46875, Forced LLM.
    high_debt, high_signal = assessed_with(timedelta(seconds=4 * CURVE_SECONDS))
    assert high_signal is DebtSignal.FORCED_LLM
    assert high_debt == Decimal("0.46875")
    assert low_debt < high_debt

    # The control: the curve observation ALONE at four half-lives is a
    # different band again, so the whole observation demonstrably entered.
    alone = assess_debt(
        DebtFactors(
            freshness=scorer.score(
                (_observation(CURVE, timedelta(seconds=4 * CURVE_SECONDS)),),
                now=NOW,
            ),
            completeness=Decimal(1),
            semantic_consistency=Decimal(1),
        ),
        profile=profile,
    )
    assert alone.signal is DebtSignal.FAIL_CLOSED
    assert alone.debt > high_debt


# --- replay (criterion 17, determinism) --------------------------------------


def test_the_computation_is_deterministic_and_the_table_hashes_identically_twice(
    table: HalfLifeTable,
) -> None:
    """Replay pins the artifact version; a decision under a supersede-only class replays byte-exactly."""
    observation = _observation(EVENT_DRIVEN, timedelta(days=365))
    first = freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))
    second = freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))
    assert first == second == Decimal(1)

    one = HalfLifeTable.model_validate(_document())
    other = HalfLifeTable.model_validate(_document())
    assert one == other
    assert content_hash(one) == content_hash(other)

    # The route a deployment's loader takes, and the dump/re-parse round trip.
    parsed = parse_artifact(_document(), HALF_LIFE_TABLE)
    assert content_hash(parsed) == content_hash(one)
    assert parse_artifact(parsed.model_dump(), HALF_LIFE_TABLE) == parsed


def test_the_mode_is_inside_the_content_address() -> None:
    """Flipping a class between modes changes the artifact's identity.

    Otherwise a table re-registered with a class quietly switched from curve to
    supersede-only would satisfy the D-05 bump check against its predecessor.
    """
    document = _document()
    document["entries"][EVENT_DRIVEN] = {
        "half_life_seconds": CURVE_SECONDS,
        "decay_driver": "test.rewrite",
        "supersession_event": "test.superseding-event",
    }
    switched = HalfLifeTable.model_validate(document)
    assert content_hash(switched) != content_hash(
        HalfLifeTable.model_validate(_document())
    )


# --- the ordering: refusals before the mode branch ---------------------------


def test_a_naive_instant_is_still_refused_under_supersede_only(
    table: HalfLifeTable,
) -> None:
    """Declaring a class supersede-only cannot make a clock fault score as fresh."""
    unvalidated = Observation.model_construct(
        observation_type=EVENT_DRIVEN,
        observed_at=datetime(2026, 3, 1, 9, 0, 0),
    )
    assert unvalidated.observed_at.tzinfo is None
    with pytest.raises(ValueError, match="timezone-aware"):
        freshness(unvalidated, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_an_observation_from_the_future_is_still_refused_under_supersede_only(
    table: HalfLifeTable,
) -> None:
    with pytest.raises(TemporalOrderError):
        freshness(
            _observation(EVENT_DRIVEN, timedelta(seconds=-1)),
            now=NOW,
            table=table,
            risk_sensitivity=Decimal(1),
        )


def test_a_non_positive_sensitivity_is_still_refused_under_supersede_only(
    table: HalfLifeTable,
) -> None:
    """An undeclared calibration is refused whether or not the mode would read it."""
    with pytest.raises(ValueError, match="risk sensitivity must be positive"):
        freshness(
            _observation(EVENT_DRIVEN, timedelta(days=1)),
            now=NOW,
            table=table,
            risk_sensitivity=Decimal(0),
        )
