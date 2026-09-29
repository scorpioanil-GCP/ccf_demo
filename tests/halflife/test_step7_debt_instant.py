"""`D-IMPL-358` step 7: the debt instant is HANDED, never read from a clock.

Ruling 6: Context Debt is computed at the decision instant, and the scorer reads no
wall clock. Gate 3 separately compares against `served_at`; that is a different
question and is not this module's subject.

**What the opening sheet claimed, and what this tree measures.** Sheet §3.7 recorded
*"with a plugin making `FreshnessScorer.score` read a wall clock instead of the
instant handed to it, the suite is 153 passed / 0 failed / 0 errors — unchanged. The
D8 ruling is unprovable as the design stands."* **That does not reproduce.** Measured
on this tree with exactly that substitution: `tests/halflife/` goes 225 → 220 and
`tests/products/` 1724 → 1719 — ten tests redden. `tests/halflife/`,
`src/ccf/halflife/` and `tests/products/test_reference_debt_scorer.py` are
byte-identical between the sheet's baseline `51158a58` and this tree, and all ten
reddening tests were present at that baseline, so the 153/153 run cannot have been
measured over these files. The likeliest reading is a population that never invoked
the subject, or a plugin that never bound the class attribute — a green run over a
population that never calls the thing under test measures nothing.

**But the protection that exists is INCIDENTAL, which is why this module exists.**
Four of the ten redden because they pin freshness at exactly `Decimal(1)` for an
observation dated at the handed instant, and `decay.freshness` returns exactly 1 only
at zero age — so any clock read breaks an equality whose subject is a VALUE, not an
instant. Re-date those fixtures by one second for an unrelated reason and the
protection disappears silently. Of the three control categories, the tree holds many
value controls, exactly ONE deliberate instant control (and it sits one frame above
`FreshnessScorer.score`, framed as a provenance claim, with no severing), and NOTHING
that asserts the scorer reads no clock at all. This module builds the missing two.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ccf.controlplane.artifacts import HalfLifeEntry
from ccf.halflife.debt import FreshnessScorer
from ccf.halflife.decay import HalfLifeTable, Observation

# The ONE widened AST detector, imported rather than restated. Written for
# `src/ccf/peering/` under step 5 section J and widened under its residual 3; a second
# copy here would be a second definition of "what a clock read looks like", and the
# two would drift the first time one of them was improved.
from tests.peering.test_admission_clock import _ambient_clock_calls

_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "ccf"

#: Every module that participates in computing a debt figure.
#:
#: `src/ccf/halflife/` is the scorer's home. `products/debt_scorer.py` is included
#: because it is the shipped reference scorer — the frame that HANDS the instant down
#: — and a clock read there would reach `FreshnessScorer.score` as an argument the
#: scorer could not tell from an honest one.
_DEBT_MODULES = tuple(sorted(_SRC.joinpath("halflife").glob("*.py"))) + (
    _SRC / "products" / "debt_scorer.py",
)


@pytest.mark.parametrize("module", _DEBT_MODULES, ids=lambda p: p.name)
def test_no_debt_module_reads_an_ambient_clock(module: pathlib.Path) -> None:
    """The category the tree had NOTHING in: the scorer reads no clock at all.

    The one near-miss that existed (`test_debt.py::test_the_recency_is_carried_and_never_consumed`)
    is not this control, for four reasons: its subject is `D-IMPL-101`'s salience
    deferral rather than the debt instant; it scans only `halflife/assessment.py`,
    which holds no computation, while `debt.py` and `decay.py` — where
    `FreshnessScorer.score` and `freshness()` actually live — are not scanned; it is a
    raw substring scan, so the prose that states the rule reads as a violation of it
    and an aliased or bare-name read slips past; and it has no positive control, so a
    scan matching nothing would pass forever.
    """
    calls = _ambient_clock_calls(module.read_text(encoding="utf-8"))
    assert calls == [], (
        f"{module.relative_to(_SRC.parent.parent)} reads an ambient clock {calls} —"
        " a debt figure that depends on wall-clock time cannot be recomputed at"
        " replay, which is the whole of ruling 6"
    )


def test_the_debt_sweep_scanned_the_modules_that_compute(tmp_path: pathlib.Path) -> None:
    """The vacuity guard: a glob that matched nothing would pass every case above."""
    names = {p.name for p in _DEBT_MODULES}
    assert {"debt.py", "decay.py", "debt_scorer.py"} <= names, names
    assert len(_DEBT_MODULES) >= 4, _DEBT_MODULES


def test_the_debt_sweeps_detector_can_see_a_planted_clock() -> None:
    """The positive control. The detector is shared, so this is its use here.

    A clean sweep is evidence only once the detector has been shown catching the thing
    it sweeps for — and this module's sweep runs over different files than the one the
    detector was written for, so it earns its own positive control.
    """
    planted = (
        "from datetime import datetime\n"
        "def score(observations, *, now):\n"
        "    return _f(observations, now=datetime.now())\n"
    )
    assert _ambient_clock_calls(planted) == ["datetime.now"]


# --- the instant is the one handed in, measured at the scorer itself -----------

#: A DELIBERATELY LONG half-life, and the reason is arithmetic rather than taste.
#:
#: `relevance_ratio` quantizes to `RATIO_QUANTUM = 1E-18`. At the fixture
#: calibrations in `tests/halflife/` (λ_c of 3600 s, and cp-06's 86400 s) a wall-clock
#: reading is thousands of half-lives old and the freshness figure UNDERFLOWS to
#: `0E-18`. A control built there would go red because both readings collapsed to the
#: quantum, not because a different instant was measured — and a non-strict assertion
#: on the same fixture would go GREEN. **A control must not be built on the quantum.**
#:
#: At 180 days neither reading underflows: an hour of age is 0.00023 half-lives and a
#: year is 2.03, so both figures are far from `0E-18` and far from each other. The
#: assertions below check that distance explicitly rather than trusting this comment.
_LONG_HALF_LIFE_SECONDS = 15_552_000
_QUANTUM = Decimal("1E-18")
_TYPE = "step7.observation"
_OBSERVED_AT = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)


def _scorer() -> FreshnessScorer:
    return FreshnessScorer(
        table=HalfLifeTable(
            semver="1.0.0",
            entries={
                _TYPE: HalfLifeEntry(
                    decay="curve",
                    decay_basis="observed-at",
                    freshness_over="series-mean",
                    series_key_attribute=None,
                    half_life_seconds=_LONG_HALF_LIFE_SECONDS,
                    decay_driver="step 7's own fixture; not a calibration",
                    supersession_event="a newer observation of the same type",
                )
            },
        ),
        risk_sensitivity=Decimal(1),
    )


def test_the_freshness_figure_is_measured_from_THE_HANDED_INSTANT() -> None:
    """Two instants, one observation: the figure follows the argument.

    This is the control the tree did not have AT THIS LEVEL. Every `now=` in
    `tests/halflife/test_debt.py` is the single module constant `NOW`, so nothing there
    can tell the handed instant from any other — and the one deliberate instant
    control in the tree sits a frame above, on `AssemblyDebtScorer.__call__`, where it
    constrains what the wrapper hands DOWN rather than what the scorer READS.

    The same observation, scored at two instants a year apart, must produce two
    different figures, ordered: the later instant is the staler reading. A scorer
    reading its own clock returns the same figure for both, so the pair collapses.
    """
    scorer = _scorer()
    observation = Observation(
        observation_type=_TYPE, observed_at=_OBSERVED_AT, subject="step7-subject"
    )
    near = _OBSERVED_AT + timedelta(hours=1)
    far = _OBSERVED_AT + timedelta(days=365)

    at_near = scorer.score((observation,), now=near)
    at_far = scorer.score((observation,), now=far)

    # THE ORDERING ALONE IS NOT ENOUGH, and the severing proved it: a scorer reading
    # its own clock answers both calls microseconds apart, so the later reading is
    # very slightly staler and `at_near > at_far` STILL HOLDS — by accident of call
    # order, differing in the twelfth decimal place. The first draft of this control
    # asserted only the ordering and would have passed under the exact edit it exists
    # to catch.
    #
    # So the claim is the MAGNITUDE. A year is more than two half-lives at 180 days,
    # so the figure must MORE THAN HALVE. Two clock reads a microsecond apart cannot
    # produce that, whatever their order.
    assert at_far < at_near / 2, (
        "a year of decay at a 180-day half-life did not even halve the figure:"
        f" {at_near} → {at_far}. The scorer is not measuring from the instant it was"
        " handed — two readings this close together come from one clock, not from two"
        " instants a year apart"
    )
    assert at_near > at_far
    # NOT built on the quantum: both readings must be well clear of it, or the
    # inequality above could be satisfied by one or both collapsing to `0E-18`.
    assert at_far > _QUANTUM * 10**6, (
        f"the later reading {at_far} is at or near the quantization floor, so this"
        " control is measuring underflow rather than a moved instant"
    )
    assert at_near < Decimal(1), "an hour-old observation is not perfectly fresh"


def test_the_scorer_cannot_be_asked_without_an_instant() -> None:
    """`now` is keyword-only with no default, so no caller can omit it.

    The structural half of the same property. A default would let a call site fall
    back silently, and the fallback would be the only instant in scope — which is how
    a clock read gets in without anybody writing one.
    """
    import inspect

    parameter = inspect.signature(FreshnessScorer.score).parameters["now"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, parameter.kind
    assert parameter.default is inspect.Parameter.empty, (
        f"`now` acquired the default {parameter.default!r}; a debt figure can now be"
        " computed without anybody naming the instant it was computed at"
    )
    scorer = _scorer()
    observation = Observation(
        observation_type=_TYPE, observed_at=_OBSERVED_AT, subject="step7-subject"
    )
    with pytest.raises(TypeError):
        scorer.score((observation,))  # type: ignore[call-arg]
