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
``test_control_empty_assembly_fires`` / ``..._cardinality_leg_fires`` /
``..._pin_leg_fires``
    **The empty case, re-derived at ``24.6-05``** (ledger row ``24.6-L-06``,
    ``D-IMPL-255`` (2)). The empty assembly no longer fails closed on
    cardinality: F is the multiplicative identity, C and S are the
    deployment's scorers' own answers, and the freshness pin is absent because
    nothing produced it. Three controls, one per claim — including one that
    reproduces the exact branch this row DELETED (every factor at zero from
    the row count) and watches it fail.
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


def assert_empty_assembly_is_scored_from_evidence(
    subject: Subject, *, empty: GraphView, declared: Decimal
) -> None:
    """A view that assembled nothing is scored from evidence, never from its emptiness.

    ``24.6-05``, ledger row ``24.6-L-06``. This assertion previously read
    *"an empty assembly yields maximal debt and no pin"* — ``D_c = 1`` from
    the row count alone. ``D-IMPL-255`` (2) removes exactly that: **"Cardinality
    never determines Context Debt. Evidence determines Context Debt."**

    Three separate claims, each asserted on its own, because the controls
    below break one at a time:

    1. **F is the multiplicative identity**, not zero. Nothing was observed, so
       nothing has decayed; ``D_c = 1 − F·C·S`` and the identity element of a
       product is one. Reporting zero would be a coverage claim wearing
       freshness's name.
    2. **C and S are exactly what the deployment's scorers returned**, and the
       Debt is the algebra over them. ``declared`` is the fixture's own
       figure and the expected Debt is COMPUTED from it — never a literal, so
       a test that started agreeing with a constant instead of with the
       scorers would fail.
    3. **No freshness pin, and C/S pinned.** No scorer produced the identity,
       so naming :class:`~ccf.halflife.debt.FreshnessScorer` as its producer
       would be the false record every pin here exists to prevent — while the
       two scorers that DID answer are named, because they did.
    """
    assessment = subject(view=empty)
    factors = assessment.factors
    assert factors.freshness == Decimal(1), (
        f"an empty assembly reported F={factors.freshness}, not the identity"
        " 1 — nothing was observed, so nothing has decayed, and a lower F is"
        " a coverage claim wearing freshness's name (D-IMPL-255 (2))"
    )
    assert (factors.completeness, factors.semantic_consistency) == (
        declared,
        declared,
    ), (
        "an empty assembly did not report the deployment's own C and S:"
        f" {factors} against a declared {declared}"
    )
    expected = Decimal(1) - (Decimal(1) * declared * declared)
    assert assessment.debt == expected, (
        f"an empty assembly reported D_c={assessment.debt}, not the {expected}"
        " its own factors compose to — a number from the row count rather"
        " than from the evidence (D-IMPL-255 (2))"
    )
    pinned = {pin.factor for pin in assessment.scorers}
    assert "freshness" not in pinned, (
        "an empty assembly named a scorer as the producer of a freshness"
        f" figure nothing measured: {assessment.scorers}"
    )
    assert pinned == {"completeness", "semantic_consistency"}, (
        "an empty assembly dropped the pins of the two scorers that DID"
        f" answer: {assessment.scorers}"
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
    assert_empty_assembly_is_scored_from_evidence(
        subject, empty=EMPTY, declared=Decimal(1)
    )
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

    **Now pins BOTH claim instants** (``D-IMPL-331``). The fixture's records
    carry ``valid_from == observed_at``, so this states the mapping for the
    ordinary case; the pair that DIFFER is
    :func:`test_the_scorer_copies_both_claim_times_onto_each_observation`,
    which is the one a dropped copy fails. Widening the expectation rather
    than relaxing the comparison: an equality that ignored a field would stop
    being the direct read this docstring claims it is.
    """
    observed = AssemblyDebtScorer._observations(WHOLE)
    assert observed == (
        Observation(
            observation_type=CALIBRATED,
            observed_at=AT,
            subject="urn:fixture:a",
            valid_from=AT,
        ),
        Observation(
            observation_type=CALIBRATED,
            observed_at=AT - timedelta(seconds=HALF_LIFE_SECONDS * 8),
            subject="urn:fixture:b",
            valid_from=AT - timedelta(seconds=HALF_LIFE_SECONDS * 8),
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
    """The empty case. A number about a graph that said nothing, from nowhere.

    ``constant_scorer`` reports ``F = 0.5`` whatever it is handed, which is
    exactly the shape the ruling forbids in the other direction too: a figure
    that does not come from the evidence. It fails the identity claim.
    """
    with pytest.raises(AssertionError, match="an empty assembly reported F="):
        assert_empty_assembly_is_scored_from_evidence(
            constant_scorer, empty=EMPTY, declared=Decimal(1)
        )


def test_control_empty_assembly_cardinality_leg_fires() -> None:
    """The empty case, the leg this row exists for: the retired shortcut itself.

    A subject that does what :class:`~ccf.products.debt_scorer.AssemblyDebtScorer`
    did before ``24.6-05`` — every factor at zero, hence ``D_c = 1``, from the
    row count alone. It must fail, and it does: this is the control proving
    the assertion above would have caught the branch that was deleted.
    """

    def cardinality_scorer(*, view: GraphView, **_: object) -> DebtAssessment:
        return assess_debt(
            DebtFactors(
                freshness=Decimal(0),
                completeness=Decimal(0),
                semantic_consistency=Decimal(0),
            ),
            profile=profile(),
        )

    with pytest.raises(AssertionError, match="an empty assembly reported F="):
        assert_empty_assembly_is_scored_from_evidence(
            cardinality_scorer, empty=EMPTY, declared=Decimal(1)
        )


def test_control_empty_assembly_pin_leg_fires() -> None:
    """The empty case, third leg: right numbers, wrong record.

    A subject that reports the honest factors and *still* names
    :class:`~ccf.halflife.debt.FreshnessScorer` as the producer of an identity
    it never computed. Asserted separately because the claims in
    :func:`assert_empty_assembly_is_scored_from_evidence` are several, and a
    control that only broke the first would leave the others unwatched.
    """

    def pinning_on_empty(*, view: GraphView, **_: object) -> DebtAssessment:
        honest = scorer()(view=view)
        return honest.model_copy(
            update={"scorers": scorer()(view=YOUNG).scorers}
        )

    with pytest.raises(AssertionError, match="named a scorer as the producer"):
        assert_empty_assembly_is_scored_from_evidence(
            pinning_on_empty, empty=EMPTY, declared=Decimal(1)
        )


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


# --- `D-IMPL-331` — the scorer carries BOTH claim times -----------------------


def test_the_scorer_copies_both_claim_times_onto_each_observation() -> None:
    """`D-IMPL-331`: which instant decays is the TABLE's call, not this function's.

    **The wiring, tested directly, because sabotage showed nothing else covers
    it.** Setting ``valid_from=None`` in
    :meth:`~ccf.products.debt_scorer.AssemblyDebtScorer._observations` left 233 tests
    green — every basis test in ``tests/halflife`` builds its own
    :class:`~ccf.halflife.decay.Observation` and so never crosses this seam.
    A `valid-from` table would then have refused every observation the fabric
    produced, with `MissingDecayInstant`, and no test would have said why.

    The two instants are asserted to be DIFFERENT values here on purpose: a
    fixture whose ingestion and source instants coincide passes whether the
    copy happens or not.
    """
    ingested = AT
    at_source = AT - timedelta(seconds=3600)
    entity = EntityRecord(
        claim_id="claim-basis",
        claim=EntityClaim(
            tenant_id="fixture-tenant",
            observed_at=ingested,
            valid_from=at_source,
            lineage=lineage(),
            entity_uri="entity://basis",
            entity_class=CALIBRATED,
        ),
        policy_bundle_version="fixture-policy-1",
    )

    observations = AssemblyDebtScorer._observations(view(entity))

    assert len(observations) == 1
    assert observations[0].observed_at == ingested, (
        "the fabric-learning instant must survive: a table declaring"
        " `observed-at` reads it, and every table written before"
        " `D-IMPL-331` declares exactly that"
    )
    assert observations[0].valid_from == at_source, (
        "the SOURCE's instant was dropped, so a row declaring"
        " `decay_basis: valid-from` refuses every observation the fabric"
        " produces and the declaration can never take effect"
    )


# --- `D-IMPL-358` step 7 / S7-F1: the debt instant is the DECISION instant -----


def test_S7F1_the_reference_scorer_measures_at_the_DECISION_instant() -> None:
    """Ruling 6: Context Debt is computed at the decision instant.

    **The defect S7-F1 named.** `decay.freshness`'s own docstring calls its `now`
    *"The decision instant"*, but this scorer passed `view.as_of`, and the resolver
    binds the view to `request.asked_at`. `decided_at` reached a scorer on exactly
    ONE branch — `InstantAwareDebtScorerProtocol.score_at` — which the reference
    scorer did not implement, so it fell to the instant-blind branch and measured
    decay from the question's instant. Wherever a product class declares a
    decision-instant parameter the two differ, and the debt was computed at the
    wrong one.

    **The graph boundary does NOT move with it.** `view.as_of` stays `asked_at` —
    what the graph was observed at is a different fact from when the answer was
    decided, and this asserts the view is untouched so a repair cannot quietly
    move both.

    The oracle is the shipped arithmetic, not a hand-computed constant: the same
    observations put through `FreshnessScorer` at each instant. The two instants
    are two half-lives apart, so the figures are far from each other and far from
    the `1E-18` quantum — a control on the quantum would redden from underflow
    rather than from a moved instant.
    """
    from ccf.halflife.debt import FreshnessScorer
    from ccf.products.resolver import InstantAwareDebtScorerProtocol

    subject = scorer()
    decided_at = AT + timedelta(seconds=HALF_LIFE_SECONDS * 2)
    assert decided_at != AT, "the two instants must be pinned APART"
    observed = view(record("urn:fixture:a", age_seconds=HALF_LIFE_SECONDS))
    assert observed.as_of == AT, "the graph boundary is the question's instant"

    assert isinstance(subject, InstantAwareDebtScorerProtocol), (
        "the reference scorer is not on the instant-aware seam, so the resolver"
        " never hands it `decided_at` and the debt is measured at `asked_at`"
        " (S7-F1)"
    )

    observations = AssemblyDebtScorer._observations(observed)
    assert observations, "the fixture carries no observation, so F is the identity"
    freshness_scorer = FreshnessScorer(
        table=subject.table, risk_sensitivity=subject.profile.risk_sensitivity
    )
    at_decided = freshness_scorer.score(observations, now=decided_at)
    at_asked = freshness_scorer.score(observations, now=AT)
    assert at_decided != at_asked, "the fixture cannot tell the two instants apart"
    assert at_decided > _QUANTUM_FLOOR, (
        f"the decision-instant reading {at_decided} is at the quantization floor,"
        " so this control would measure underflow rather than a moved instant"
    )

    assessed = subject.score_at(
        view=observed, evidence=None, decided_at=decided_at, children=None
    )

    assert assessed.factors.freshness == at_decided, (
        "the debt was not measured at the decision instant:"
        f" {assessed.factors.freshness} against the decision instant's {at_decided}"
    )
    assert assessed.factors.freshness != at_asked, (
        "the debt is still being measured at the question's instant"
    )
    # ...and the graph boundary did not travel with the decay instant.
    assert observed.as_of == AT


#: Comfortably above `RATIO_QUANTUM = 1E-18`, so a reading at the floor is caught.
_QUANTUM_FLOOR = Decimal("1E-12")
