"""The reference debt scorer, and every assertion about it watched failing.

Subject: :mod:`ccf.products.debt_scorer`, the reference
:class:`~ccf.products.resolver.AssemblyDebtScorerProtocol` ruled in
``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``
**Amendment A.1**.

Why this module is shaped the way it is
---------------------------------------
Every defect Phase 17 has found so far was in verification machinery rather
than in mechanism, and all five instances were one shape: *a check that stops
checking without going red.* So no assertion here is written inline against a
fixed subject. **Each is a module-level function taking its subject as a
parameter**, and each control below hands a deliberately divergent subject to
the **shipped** assertion function and asserts that function fails. Nothing
here re-implements an assertion; a control that tested a copy would prove the
copy fires.

The control the other controls depend on
----------------------------------------
:func:`test_the_honest_scorer_satisfies_every_assertion` runs first for the
reason ``tests/client/conformance/test_the_suite_fires.py`` gives for its own
honest pair: an expectation of *failure* is satisfied by any difference at
all, including a fixture that was never valid. Without a subject that passes
everything, a green run of this module would be evidence of nothing.

The controls, and what each proves
----------------------------------
Each names the property it breaks and therefore the property the shipped
assertion is load-bearing for.

``test_control_conformance_fires``
    A callable with the wrong keyword refuses to satisfy the Protocol — proves
    :func:`assert_conforms` is reading the seam and not the type name.
``test_control_freshness_direction_fires``
    A scorer that reports a constant regardless of age passes an "F is a
    number in ``[0, 1]``" check and must fail
    :func:`assert_freshness_falls_as_observations_age`.
``test_control_half_life_is_read_from_the_artifact_fires``
    A scorer that ignores the ``λ_c`` table it was handed produces the same F
    under two different tables — the literal-instead-of-artifact defect the
    No-Hardcoding Rule exists to catch.
``test_control_risk_sensitivity_is_read_from_the_artifact_fires``
    The same, for the ``DebtProfile``'s sensitivity multiplier.
``test_control_bands_come_from_the_profile_fires``
    A scorer that decides its own routing state rather than letting
    :func:`~ccf.halflife.debt.assess_debt` read the profile's bands.
``test_control_scorer_pins_fire``
    A scorer that drops its pins, and one that pins a *different* identity —
    both must fail, because replay resolving the scorer installed today rather
    than the one in force is the substitution the replay plane prevents.
``test_control_empty_assembly_fires``
    **The empty case.** A scorer that reports a confident number about a graph
    that said nothing — the defect ``17-06`` shipped in its own fixture and
    caught before merge.
``test_control_uncalibrated_class_fires``
    **The unresolvable case.** A scorer that substitutes a decay rate for an
    entity class with no declared ``λ_c``, instead of raising
    :class:`~ccf.halflife.decay.MissingHalfLife`.
``test_control_rows_handed_fires``
    A scorer whose answer does not change when rows are removed from the view
    — which would mean it is not measuring the assembly it was handed.

What these tests do not reach
-----------------------------
They do not boot a fabric and therefore do not prove
:class:`~ccf.products.resolver.GovernedResolver` hands this scorer
``execution.view`` rather than the pre-operator view; that binding is
``17-13``'s to prove end to end. They assert the scorer measures **exactly the
view it is handed**, which is the half of the row-selection claim decidable
here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ccf.contracts.claims import EntityClaim, LineageEntry
from ccf.controlplane.artifacts import DebtProfile, HalfLifeEntry, HalfLifeTable
from ccf.graph.protocols import EntityRecord, GraphView
from ccf.halflife.assessment import DebtAssessment, DebtFactors, DebtSignal
from ccf.halflife.debt import (
    FRESHNESS_SCORER_ID,
    FRESHNESS_SCORER_VERSION,
    assess_debt,
)
from ccf.halflife.decay import MissingHalfLife, Observation
from ccf.products.debt_scorer import (
    DECLARED_FACTOR_SCORER_ID,
    DECLARED_FACTOR_SCORER_VERSION,
    AssemblyDebtScorer,
    DeclaredFactor,
)
from ccf.products.resolver import AssemblyDebtScorerProtocol
from ccf.signal.envelope import SourceIdentity

#: The one instant every view below is rendered at. A fixed value rather than
#: a clock read, for the reason the scorer itself reads ``view.as_of``: a test
#: whose subject depends on when it ran cannot be a determinism test.
AT = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)

#: The deployment vocabulary these fixtures declare. Named here so a test that
#: means "the calibrated class" and one that means "the uncalibrated class"
#: cannot drift into each other by a typo.
CALIBRATED = "fixture.widget"
UNCALIBRATED = "fixture.gadget"

#: One half-life, in seconds. A fixture calibration and not an SDK value — the
#: SDK ships no number of this kind (CLAUDE.md §11), which is the whole reason
#: it has to arrive from an artifact for the scorer to read.
HALF_LIFE_SECONDS = 3600

#: A second, deliberately different calibration. The two exist so that "the
#: scorer read the artifact" is provable by *moving* the artifact rather than
#: by inspecting the scorer's source.
OTHER_HALF_LIFE_SECONDS = 360


# ---------------------------------------------------------------------------
# Fixture material — deployment values, all of it, none of it the SDK's.
# ---------------------------------------------------------------------------
def lineage() -> frozenset[LineageEntry]:
    """One lineage entry, because a claim may not carry none."""
    return frozenset(
        {
            LineageEntry(
                source=SourceIdentity(system_id="fixture-source"),
                envelope_id="fixture-envelope",
                observed_at=AT,
            )
        }
    )


def record(
    uri: str, *, age_seconds: int, entity_class: str = CALIBRATED
) -> EntityRecord:
    """One entity record observed ``age_seconds`` before :data:`AT`."""
    observed = AT - timedelta(seconds=age_seconds)
    return EntityRecord(
        claim_id=f"claim-{uri}",
        claim=EntityClaim(
            tenant_id="fixture-tenant",
            observed_at=observed,
            valid_from=observed,
            lineage=lineage(),
            entity_uri=uri,
            entity_class=entity_class,
        ),
        policy_bundle_version="fixture-policy-1",
    )


def view(*records: EntityRecord) -> GraphView:
    """A view over ``records``, rendered as of :data:`AT`."""
    return GraphView(
        tenant_id="fixture-tenant", as_of=AT, entities=tuple(records)
    )


def table(*, half_life_seconds: int = HALF_LIFE_SECONDS) -> HalfLifeTable:
    """A λ_c table calibrating :data:`CALIBRATED` and nothing else.

    Deliberately *not* calibrating :data:`UNCALIBRATED`: the unresolvable case
    needs a class the table has never heard of, and a table that quietly
    covered everything would make that case unreachable.
    """
    return HalfLifeTable(
        semver="1.0.0",
        entries={
            CALIBRATED: HalfLifeEntry(
                half_life_seconds=half_life_seconds,
                decay_driver="fixture-driver",
                supersession_event="fixture-supersession",
            )
        },
    )


def profile(
    *,
    risk_sensitivity: str = "1",
    forced_llm: str = "0.30",
    fail_closed: str = "0.70",
) -> DebtProfile:
    """A debt profile. Every figure is the fixture's; none is the SDK's."""
    return DebtProfile(
        semver="1.0.0",
        risk_sensitivity=Decimal(risk_sensitivity),
        forced_llm_threshold=Decimal(forced_llm),
        fail_closed_threshold=Decimal(fail_closed),
    )


def scorer(
    *,
    half_life_seconds: int = HALF_LIFE_SECONDS,
    risk_sensitivity: str = "1",
    forced_llm: str = "0.30",
    fail_closed: str = "0.70",
    completeness: str = "1",
    semantic_consistency: str = "1",
) -> AssemblyDebtScorer:
    """The shipped scorer, wired against fixture artifacts."""
    return AssemblyDebtScorer(
        table=table(half_life_seconds=half_life_seconds),
        profile=profile(
            risk_sensitivity=risk_sensitivity,
            forced_llm=forced_llm,
            fail_closed=fail_closed,
        ),
        completeness=DeclaredFactor(value=Decimal(completeness)),
        semantic_consistency=DeclaredFactor(value=Decimal(semantic_consistency)),
    )


#: What the shipped scorer's pins must say, factor by factor. Read off the
#: modules that own the identities rather than spelled here, so a rename in
#: `src/` fails this suite instead of drifting past it.
EXPECTED_PINS: dict[str, tuple[str, str]] = {
    "freshness": (FRESHNESS_SCORER_ID, FRESHNESS_SCORER_VERSION),
    "completeness": (DECLARED_FACTOR_SCORER_ID, DECLARED_FACTOR_SCORER_VERSION),
    "semantic_consistency": (
        DECLARED_FACTOR_SCORER_ID,
        DECLARED_FACTOR_SCORER_VERSION,
    ),
}

#: The shape every subject below has: a keyword-only call taking a view.
Subject = Callable[..., DebtAssessment]


# ---------------------------------------------------------------------------
# The assertions. Each takes its subject as a parameter — that is what lets a
# control feed it a broken one.
# ---------------------------------------------------------------------------
def assert_conforms(subject: object) -> None:
    """``subject`` satisfies the Protocol the resolver seam is typed to."""
    assert isinstance(subject, AssemblyDebtScorerProtocol), (
        f"{subject!r} does not satisfy AssemblyDebtScorerProtocol"
    )


def assert_freshness_falls_as_observations_age(
    subject: Subject, *, young: GraphView, old: GraphView
) -> None:
    """F is lower over ``old`` than over ``young``, and both are in ``[0, 1]``."""
    young_f = subject(view=young).factors.freshness
    old_f = subject(view=old).factors.freshness
    assert Decimal(0) <= old_f < young_f <= Decimal(1), (
        f"freshness did not fall with age: young={young_f}, old={old_f}"
    )


def assert_half_life_is_read_from_the_artifact(
    build: Callable[[int], Subject], *, aged: GraphView
) -> None:
    """A shorter declared half-life yields a lower F over the same rows.

    The artifact moves and the number must move with it. A scorer holding a
    rate as a literal answers identically under both tables, which is exactly
    the No-Hardcoding defect this asserts the absence of.
    """
    slow = build(HALF_LIFE_SECONDS)(view=aged).factors.freshness
    fast = build(OTHER_HALF_LIFE_SECONDS)(view=aged).factors.freshness
    assert fast < slow, (
        "freshness did not move when the half-life artifact changed:"
        f" {HALF_LIFE_SECONDS}s gave {slow}, {OTHER_HALF_LIFE_SECONDS}s"
        f" gave {fast}"
    )


def assert_risk_sensitivity_is_read_from_the_artifact(
    build: Callable[[str], Subject], *, aged: GraphView
) -> None:
    """A smaller sensitivity multiplier shortens the budget and lowers F."""
    generous = build("1")(view=aged).factors.freshness
    strict = build("0.25")(view=aged).factors.freshness
    assert strict < generous, (
        "freshness did not move when the profile's risk sensitivity changed:"
        f" 1 gave {generous}, 0.25 gave {strict}"
    )


def assert_bands_come_from_the_profile(
    build: Callable[[str, str], Subject],
    *,
    aged: GraphView,
    expected: Sequence[tuple[str, str, DebtSignal]],
) -> None:
    """The routing state follows the profile's declared bands, band by band.

    Each expectation is asserted on its own rather than in aggregate: a
    property asserted over a collection passes when one member survives and
    licenses the rest, which is this project's recurring defect class.
    """
    for forced_llm, fail_closed, signal in expected:
        actual = build(forced_llm, fail_closed)(view=aged).signal
        assert actual is signal, (
            f"bands (forced_llm={forced_llm}, fail_closed={fail_closed})"
            f" routed to {actual} rather than {signal}"
        )


def assert_pins_identify_the_scorers(
    assessment: DebtAssessment, *, expected: dict[str, tuple[str, str]]
) -> None:
    """Every accounted factor carries the pin naming what produced it."""
    pinned = {
        pin.factor: (pin.scorer_id, pin.scorer_version)
        for pin in assessment.scorers
    }
    assert pinned == expected, (
        f"scorer pins do not identify the shipped scorers: {pinned} !="
        f" {expected}"
    )


def assert_empty_assembly_fails_closed(
    subject: Subject, *, empty: GraphView
) -> None:
    """A view that assembled nothing yields maximal debt and no pin.

    Three separate claims, each asserted on its own: ``D_c`` is one, every
    factor is zero, and **no scorer is named as the producer** — because none
    ran, and pinning one would be a false record.
    """
    assessment = subject(view=empty)
    assert assessment.debt == Decimal(1), (
        f"an empty assembly reported D_c={assessment.debt}, not 1 — a"
        " confident number about a graph that said nothing"
    )
    factors = assessment.factors
    assert (
        factors.freshness,
        factors.completeness,
        factors.semantic_consistency,
    ) == (Decimal(0), Decimal(0), Decimal(0)), (
        f"an empty assembly reported non-zero factors: {factors}"
    )
    assert assessment.scorers == (), (
        "an empty assembly named a scorer as the producer of factors nothing"
        f" measured: {assessment.scorers}"
    )


def assert_refuses_an_uncalibrated_class(
    subject: Subject, *, uncalibrated: GraphView
) -> None:
    """An entity class with no declared λ_c raises rather than being scored."""
    try:
        assessment = subject(view=uncalibrated)
    except MissingHalfLife:
        return
    raise AssertionError(
        "an entity class with no declared half-life was scored at a rate"
        f" nobody declared: {assessment.factors}"
    )


def assert_measures_the_rows_it_is_handed(
    subject: Subject, *, whole: GraphView, subset: GraphView
) -> None:
    """Removing rows from the view moves the number.

    The decidable half of the row-selection claim: the scorer holds no graph
    handle, so what it measures is the view it was given and nothing else. A
    subject whose answer is identical over a strict subset either re-read the
    graph or ignored the rows.
    """
    assert len(subset.entities) < len(whole.entities), (
        "the control's subset is not a strict subset — the fixture is wrong,"
        " not the subject"
    )
    whole_f = subject(view=whole).factors.freshness
    subset_f = subject(view=subset).factors.freshness
    assert whole_f != subset_f, (
        f"freshness was unchanged by dropping rows from the view: {whole_f}"
    )


# ---------------------------------------------------------------------------
# The honest subject — first, because every control below expects a failure.
# ---------------------------------------------------------------------------
YOUNG = view(record("urn:fixture:a", age_seconds=0))
OLD = view(record("urn:fixture:a", age_seconds=HALF_LIFE_SECONDS * 8))
WHOLE = view(
    record("urn:fixture:a", age_seconds=0),
    record("urn:fixture:b", age_seconds=HALF_LIFE_SECONDS * 8),
)
SUBSET = view(record("urn:fixture:a", age_seconds=0))
EMPTY = view()
UNCALIBRATED_VIEW = view(
    record("urn:fixture:z", age_seconds=0, entity_class=UNCALIBRATED)
)

#: The two bands that must route an eight-half-life-old row, which scores
#: ``D_c`` just under one. Fixture calibrations, not SDK values.
BAND_EXPECTATIONS: tuple[tuple[str, str, DebtSignal], ...] = (
    ("0.30", "0.70", DebtSignal.FAIL_CLOSED),
    ("0.30", "0.999999", DebtSignal.FORCED_LLM),
    ("1", "1", DebtSignal.OK),
)


def test_the_honest_scorer_satisfies_every_assertion() -> None:
    """The shipped scorer passes every assertion in this module.

    First by position and by dependency: each control below asserts a
    *failure*, and an expectation of failure is met by any difference at all
    — including a fixture that never worked. This rules that out.
    """
    subject = scorer()
    assert_conforms(subject)
    assert_freshness_falls_as_observations_age(subject, young=YOUNG, old=OLD)
    assert_half_life_is_read_from_the_artifact(
        lambda seconds: scorer(half_life_seconds=seconds), aged=OLD
    )
    assert_risk_sensitivity_is_read_from_the_artifact(
        lambda sensitivity: scorer(risk_sensitivity=sensitivity), aged=OLD
    )
    assert_bands_come_from_the_profile(
        lambda forced, closed: scorer(forced_llm=forced, fail_closed=closed),
        aged=OLD,
        expected=BAND_EXPECTATIONS,
    )
    assert_pins_identify_the_scorers(
        subject(view=YOUNG), expected=EXPECTED_PINS
    )
    assert_empty_assembly_fails_closed(subject, empty=EMPTY)
    assert_refuses_an_uncalibrated_class(subject, uncalibrated=UNCALIBRATED_VIEW)
    assert_measures_the_rows_it_is_handed(subject, whole=WHOLE, subset=SUBSET)


# ---------------------------------------------------------------------------
# Positive facts the assertions above do not state.
# ---------------------------------------------------------------------------
def test_observations_are_one_per_entity_typed_by_its_own_class() -> None:
    """The mapping from records to observations, read directly.

    Asserted rather than inferred from the number that came out: the entity
    class *is* the λ_c vocabulary, and a scorer that typed observations any
    other way would need the deployment to declare a second one.
    """
    observed = AssemblyDebtScorer._observations(WHOLE)
    assert observed == (
        Observation(
            observation_type=CALIBRATED,
            observed_at=AT,
            subject="urn:fixture:a",
        ),
        Observation(
            observation_type=CALIBRATED,
            observed_at=AT - timedelta(seconds=HALF_LIFE_SECONDS * 8),
            subject="urn:fixture:b",
        ),
    )


def test_relationships_are_not_observations() -> None:
    """A view's edges do not enter F, which is the stated boundary."""
    assert AssemblyDebtScorer._observations(EMPTY) == ()


def test_the_instant_is_the_views_own_as_of() -> None:
    """F is measured at ``view.as_of``, so no clock is read.

    Proved by moving only the boundary: two views over the *same* record,
    rendered at different instants, must score differently.
    """
    older_boundary = GraphView(
        tenant_id="fixture-tenant",
        as_of=AT - timedelta(seconds=HALF_LIFE_SECONDS * 4),
        entities=OLD.entities,
    )
    subject = scorer()
    assert (
        subject(view=older_boundary).factors.freshness
        > subject(view=OLD).factors.freshness
    )


def test_declared_factor_reports_its_value_whatever_was_assembled() -> None:
    """The one scorer whose answer does not depend on the assembly."""
    declared = DeclaredFactor(value=Decimal("0.5"))
    assert declared.score((), now=AT) == Decimal("0.5")
    assert declared.score(
        AssemblyDebtScorer._observations(WHOLE), now=AT
    ) == Decimal("0.5")


def test_declared_factor_refuses_a_value_outside_the_unit_interval() -> None:
    """Refused where it was authored, not three frames later."""
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        DeclaredFactor(value=Decimal("1.5"))


def test_the_declared_factors_reach_the_assessment() -> None:
    """C and S on the product are the deployment's numbers, unmodified."""
    assessment = scorer(completeness="0.5", semantic_consistency="0.25")(
        view=YOUNG
    )
    assert assessment.factors.completeness == Decimal("0.5")
    assert assessment.factors.semantic_consistency == Decimal("0.25")


# ---------------------------------------------------------------------------
# Divergent subjects — each conforms to the seam and gets one thing wrong.
# ---------------------------------------------------------------------------
def _assessment(
    *,
    freshness: str,
    completeness: str = "1",
    semantic_consistency: str = "1",
    signal: DebtSignal | None = None,
    scorers: tuple[str, ...] = (),
) -> DebtAssessment:
    """Build an assessment directly, bypassing the shipped scorer."""
    factors = DebtFactors(
        freshness=Decimal(freshness),
        completeness=Decimal(completeness),
        semantic_consistency=Decimal(semantic_consistency),
    )
    honest = assess_debt(factors, profile=profile())
    if signal is None:
        return honest
    return DebtAssessment(
        debt=honest.debt, signal=signal, factors=factors, scorers=honest.scorers
    )


def constant_scorer(*, view: GraphView) -> DebtAssessment:
    """Reports the same number whatever it is handed — including on empty."""
    return _assessment(freshness="0.5")


def rate_substituting_scorer(*, view: GraphView) -> DebtAssessment:
    """Scores an uncalibrated class at a rate nobody declared."""
    return _assessment(freshness="0.9")


def band_deciding_scorer(*, view: GraphView) -> DebtAssessment:
    """Decides its own routing state instead of reading the profile's bands."""
    return _assessment(freshness="0", signal=DebtSignal.OK)


def unpinned_scorer(*, view: GraphView) -> DebtAssessment:
    """Drops its pins, so replay resolves whatever is installed at replay time."""
    return scorer()(view=view).model_copy(update={"scorers": ()})


def misidentified_scorer(*, view: GraphView) -> DebtAssessment:
    """Pins a scorer identity that did not produce the number."""
    honest = scorer()(view=view)
    return honest.model_copy(
        update={
            "scorers": tuple(
                pin.model_copy(update={"scorer_version": "9.9.9"})
                for pin in honest.scorers
            )
        }
    )


class _NotAScorer:
    """Conforms by name and not by seam: the keyword is wrong."""

    def __call__(self, *, graph: GraphView) -> DebtAssessment:
        return _assessment(freshness="1")


def _ignores_its_artifacts(_: object) -> Subject:
    """A builder whose subject is the same whatever artifact it is handed."""
    return constant_scorer


# ---------------------------------------------------------------------------
# The controls. Each hands a divergent subject to the SHIPPED assertion.
# ---------------------------------------------------------------------------
def test_control_conformance_fires() -> None:
    """A subject with no ``__call__`` must not pass conformance."""
    with pytest.raises(AssertionError, match="AssemblyDebtScorerProtocol"):
        assert_conforms(object())


def test_conformance_is_blind_to_the_signature_and_says_so() -> None:
    """What :func:`assert_conforms` cannot see, asserted rather than assumed.

    ``@runtime_checkable`` covers the *presence* of ``__call__`` and never its
    signature — the Protocol's own docstring says the signature is mypy's job.
    :class:`_NotAScorer` takes ``graph`` rather than ``view`` and passes
    anyway. Stating the blind spot as a passing assertion is what keeps a
    reader from mistaking the conformance check for a signature check; the
    standing lesson of this phase is that a check which does not say what it
    is blind to is how a defect class survives review.
    """
    assert_conforms(_NotAScorer())
    with pytest.raises(TypeError):
        _NotAScorer()(view=YOUNG)  # type: ignore[call-arg]


def test_control_freshness_direction_fires() -> None:
    with pytest.raises(AssertionError, match="freshness did not fall with age"):
        assert_freshness_falls_as_observations_age(
            constant_scorer, young=YOUNG, old=OLD
        )


def test_control_half_life_is_read_from_the_artifact_fires() -> None:
    with pytest.raises(
        AssertionError, match="freshness did not move when the half-life"
    ):
        assert_half_life_is_read_from_the_artifact(
            _ignores_its_artifacts, aged=OLD
        )


def test_control_risk_sensitivity_is_read_from_the_artifact_fires() -> None:
    with pytest.raises(
        AssertionError, match="freshness did not move when the profile"
    ):
        assert_risk_sensitivity_is_read_from_the_artifact(
            _ignores_its_artifacts, aged=OLD
        )


def test_control_bands_come_from_the_profile_fires() -> None:
    with pytest.raises(AssertionError, match="routed to"):
        assert_bands_come_from_the_profile(
            lambda _forced, _closed: band_deciding_scorer,
            aged=OLD,
            expected=BAND_EXPECTATIONS,
        )


def test_control_dropped_pins_fire() -> None:
    with pytest.raises(AssertionError, match="do not identify the shipped"):
        assert_pins_identify_the_scorers(
            unpinned_scorer(view=YOUNG), expected=EXPECTED_PINS
        )


def test_control_misidentified_pins_fire() -> None:
    """A wrong *version* must fail as loudly as a missing pin.

    Separate from the dropped-pin control on purpose: a check that only
    noticed absence would let a scorer claim a version it never ran under,
    which is the substitution ``D-IMPL-47`` pins exist to prevent.
    """
    with pytest.raises(AssertionError, match="do not identify the shipped"):
        assert_pins_identify_the_scorers(
            misidentified_scorer(view=YOUNG), expected=EXPECTED_PINS
        )


def test_control_empty_assembly_fires() -> None:
    """The empty case. A confident number about a graph that said nothing."""
    with pytest.raises(AssertionError, match="an empty assembly reported"):
        assert_empty_assembly_fails_closed(constant_scorer, empty=EMPTY)


def test_control_empty_assembly_pin_leg_fires() -> None:
    """The empty case, second leg: right number, wrong record.

    A subject that reaches ``D_c = 1`` and *still* names a producer for the
    zeroes it did not measure. Asserted separately because the three claims in
    :func:`assert_empty_assembly_fails_closed` are three, and a control that
    only broke the first would leave the other two unwatched.
    """

    def pinning_on_empty(*, view: GraphView) -> DebtAssessment:
        honest = scorer()(view=view)
        return honest.model_copy(
            update={"scorers": scorer()(view=YOUNG).scorers}
        )

    with pytest.raises(AssertionError, match="named a scorer as the producer"):
        assert_empty_assembly_fails_closed(pinning_on_empty, empty=EMPTY)


def test_control_uncalibrated_class_fires() -> None:
    """The unresolvable case. A rate substituted for one nobody declared."""
    with pytest.raises(AssertionError, match="was scored at a rate"):
        assert_refuses_an_uncalibrated_class(
            rate_substituting_scorer, uncalibrated=UNCALIBRATED_VIEW
        )


def test_control_rows_handed_fires() -> None:
    with pytest.raises(AssertionError, match="unchanged by dropping rows"):
        assert_measures_the_rows_it_is_handed(
            constant_scorer, whole=WHOLE, subset=SUBSET
        )
