"""D_c debt tests (FABR-05; whitepaper §7.7 "`D_c` Formulas — Basic and Extended").

Four things are pinned here, and the third is the one that would be most
expensive to lose silently:

* the **basic** form ``D_c = 1 − (C_available / C_required)``;
* the **extended** multiplicative form ``D_c = 1 − (F · C · S)``;
* the **any-factor-near-zero-collapses-whole** property that makes the
  multiplicative form regulator-defensible — the whitepaper's own guarantor
  worked example is replayed as a test, including the weighted-additive
  masking it rejects (INV-CH7-62/63);
* the CAR band predicate: below both thresholds → Ok, above Forced-LLM →
  ForcedLLM, above Fail-Closed → FailClosed, missing profile → typed error.

Thresholds and the risk-sensitivity multiplier load from
``tests/fixtures/banking/halflife.yaml``. There is no threshold in `/src`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DEBT_PROFILE, DebtProfile, parse_artifact
from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneRegistry
from ccf.halflife.assessment import NO_DEBT_EVIDENCE, DebtEvidencePointer
from ccf.halflife.debt import (
    DebtAssessment,
    DebtFactors,
    DebtSignal,
    FreshnessScorer,
    assess_debt,
    basic_debt,
    context_debt,
)
from ccf.halflife.decay import HalfLifeTable, Observation
from ccf.products.contract import ContextProductContract, ProductLineage

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "halflife.yaml"

NOW = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)

#: A subject identity owned by this test module. **Deployment-side**: the SDK
#: enumerates no identifier scheme and never interprets the value
#: (D-IMPL-117, CLAUDE.md §11). Named here so the suite's identities are a
#: visible test-fixture choice rather than an SDK vocabulary (CINV-01's scope
#: reaches ``tests/``).
SUBJECT = "test-subject-alpha"

#: A second deployment-side identity, on the same discipline, for the scorer
#: assertion that two differently-identified observations still score alike.
OTHER_SUBJECT = "test-subject-beta"


@pytest.fixture(scope="module")
def document() -> Any:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def table(document: Any) -> HalfLifeTable:
    return HalfLifeTable.model_validate(document["half_life_table"])


@pytest.fixture(scope="module")
def profile(document: Any) -> DebtProfile:
    artifact = parse_artifact(document["debt_profile"], DEBT_PROFILE)
    assert isinstance(artifact, DebtProfile)
    return artifact


def _whole(*, freshness: Decimal | None = None) -> DebtFactors:
    """Factors at full strength except where a test says otherwise."""
    return DebtFactors(
        freshness=freshness if freshness is not None else Decimal(1),
        completeness=Decimal(1),
        semantic_consistency=Decimal(1),
    )


# --- the formulas ----------------------------------------------------------


def test_basic_debt_is_zero_at_full_coverage() -> None:
    assert basic_debt(available=7, required=7) == Decimal(0)


def test_basic_debt_is_one_when_nothing_was_assembled() -> None:
    assert basic_debt(available=0, required=7) == Decimal(1)


def test_basic_debt_quantifies_the_gap() -> None:
    assert basic_debt(available=3, required=4) == Decimal(1) / Decimal(4)


def test_basic_debt_refuses_a_zero_requirement() -> None:
    with pytest.raises(ValueError):
        basic_debt(available=0, required=0)


def test_basic_debt_refuses_coverage_beyond_the_requirement() -> None:
    with pytest.raises(ValueError):
        basic_debt(available=8, required=7)


def test_extended_debt_is_zero_when_every_factor_is_whole() -> None:
    assert context_debt(_whole()) == Decimal(0)


def test_extended_debt_is_one_when_any_factor_collapses() -> None:
    for field in ("freshness", "completeness", "semantic_consistency"):
        factors = _whole().model_copy(update={field: Decimal(0)})
        assert context_debt(factors) == Decimal(1)


def test_factors_outside_the_unit_interval_are_refused() -> None:
    with pytest.raises(ValueError):
        DebtFactors(
            freshness=Decimal(2),
            completeness=Decimal(1),
            semantic_consistency=Decimal(1),
        )


def test_the_guarantor_worked_example_reaches_high_debt() -> None:
    """Whitepaper §7.7: F=0.95, C=0.95, S=0.05 → D_c ≈ 0.955 (INV-CH7-62)."""
    factors = DebtFactors(
        freshness=Decimal("0.95"),
        completeness=Decimal("0.95"),
        semantic_consistency=Decimal("0.05"),
    )
    debt = context_debt(factors)
    assert debt == Decimal(1) - (Decimal("0.95") * Decimal("0.95") * Decimal("0.05"))
    assert debt > Decimal("0.95")


def test_the_multiplicative_form_refuses_the_weighted_additive_masking() -> None:
    """The rejected alternative would score the same context as low-debt.

    INV-CH7-63: the rejection is architectural, not a tuning preference, so the
    gap between the two forms is asserted rather than described.
    """
    f = c = Decimal("0.95")
    s = Decimal("0.05")
    multiplicative = context_debt(
        DebtFactors(freshness=f, completeness=c, semantic_consistency=s)
    )
    weighted_additive = Decimal(1) - (
        Decimal("0.4") * f + Decimal("0.4") * c + Decimal("0.2") * s
    )
    assert weighted_additive < Decimal("0.5") < multiplicative


# --- the freshness scorer --------------------------------------------------


def test_freshness_scorer_is_whole_for_a_just_made_observation(
    table: HalfLifeTable, profile: DebtProfile
) -> None:
    scorer = FreshnessScorer(table=table, risk_sensitivity=profile.risk_sensitivity)
    name = next(iter(table.entries))
    score = scorer.score(
        (
            Observation(
                observation_type=name, observed_at=NOW, subject=SUBJECT
            ),
        ),
        now=NOW,
    )
    assert score == Decimal(1)


def test_freshness_scorer_aggregates_every_observation(
    table: HalfLifeTable, profile: DebtProfile
) -> None:
    scorer = FreshnessScorer(table=table, risk_sensitivity=profile.risk_sensitivity)
    name = min(table.entries, key=lambda n: table.entries[n].half_life_seconds)
    fresh = Observation(
        observation_type=name, observed_at=NOW, subject=SUBJECT
    )
    stale = Observation(
        observation_type=name,
        observed_at=NOW - timedelta(days=365),
        subject=OTHER_SUBJECT,
    )
    both = scorer.score((fresh, stale), now=NOW)
    assert scorer.score((stale,), now=NOW) < both < scorer.score((fresh,), now=NOW)


def test_the_freshness_figure_is_unmoved_by_the_subject_identity(
    table: HalfLifeTable, profile: DebtProfile
) -> None:
    """The identity is carried through the debt path, never consumed by it.

    Same types, same instants, three different identity states — one populated,
    one populated differently, one absent and carrying the sentinel — and one
    freshness figure. A scorer that read the identity would be re-deriving F
    from something whitepaper §7.7 does not bind λ_c to.
    """
    scorer = FreshnessScorer(table=table, risk_sensitivity=profile.risk_sensitivity)
    name = min(table.entries, key=lambda n: table.entries[n].half_life_seconds)
    observed_at = NOW - timedelta(days=30)
    figures = {
        scorer.score(
            (
                Observation(
                    observation_type=name, observed_at=observed_at, **identity
                ),
            ),
            now=NOW,
        )
        for identity in (
            {"subject": SUBJECT},
            {"subject": OTHER_SUBJECT},
            {},
        )
    }
    assert len(figures) == 1


def test_freshness_scorer_refuses_an_empty_observation_set(
    table: HalfLifeTable, profile: DebtProfile
) -> None:
    """No observations is not 'perfectly fresh' — it is a coverage question."""
    scorer = FreshnessScorer(table=table, risk_sensitivity=profile.risk_sensitivity)
    with pytest.raises(ValueError):
        scorer.score((), now=NOW)


def test_freshness_scorer_carries_a_versioned_identity(
    table: HalfLifeTable, profile: DebtProfile
) -> None:
    """D-IMPL-47: the scorer version in force is pinned into replay."""
    scorer = FreshnessScorer(table=table, risk_sensitivity=profile.risk_sensitivity)
    assert scorer.scorer_id
    assert scorer.scorer_version


# --- the CAR band predicate ------------------------------------------------


def test_below_both_thresholds_is_ok(profile: DebtProfile) -> None:
    assessment = assess_debt(_whole(), profile=profile)
    assert isinstance(assessment, DebtAssessment)
    assert assessment.signal is DebtSignal.OK
    assert assessment.debt == Decimal(0)


def test_above_the_forced_llm_threshold_signals_forced_llm(
    profile: DebtProfile,
) -> None:
    # Freshness chosen so D_c lands strictly between the two configured bands.
    target = (profile.forced_llm_threshold + profile.fail_closed_threshold) / 2
    factors = _whole(freshness=Decimal(1) - target)
    assessment = assess_debt(factors, profile=profile)
    assert assessment.signal is DebtSignal.FORCED_LLM
    assert profile.forced_llm_threshold < assessment.debt <= profile.fail_closed_threshold


def test_above_the_fail_closed_threshold_signals_fail_closed(
    profile: DebtProfile,
) -> None:
    factors = _whole(freshness=Decimal(0))
    assessment = assess_debt(factors, profile=profile)
    assert assessment.signal is DebtSignal.FAIL_CLOSED
    assert assessment.debt == Decimal(1)


def test_a_threshold_is_a_band_edge_not_a_breach(profile: DebtProfile) -> None:
    """'above the class-specific threshold' — at the edge is not above it."""
    factors = _whole(freshness=Decimal(1) - profile.forced_llm_threshold)
    assessment = assess_debt(factors, profile=profile)
    assert assessment.debt == profile.forced_llm_threshold
    assert assessment.signal is DebtSignal.OK


def test_the_signal_is_a_value_with_no_side_effect(profile: DebtProfile) -> None:
    """I.1 has no LLM path: the signal is data a later consumer routes on."""
    first = assess_debt(_whole(freshness=Decimal(0)), profile=profile)
    second = assess_debt(_whole(freshness=Decimal(0)), profile=profile)
    assert first == second


def test_the_assessment_carries_the_factors_it_was_computed_from(
    profile: DebtProfile,
) -> None:
    factors = _whole(freshness=Decimal(1) / Decimal(2))
    assert assess_debt(factors, profile=profile).factors == factors


def test_a_missing_profile_raises_rather_than_defaulting() -> None:
    registry = ControlPlaneRegistry()
    with pytest.raises(ControlPlaneMissing):
        registry.resolve("acme-bank/debt-profile/never-registered", "deadbeef")


def test_a_profile_missing_a_threshold_is_refused(document: Any) -> None:
    declared = dict(document["debt_profile"])
    declared.pop("fail_closed_threshold")
    with pytest.raises(ValueError):
        parse_artifact(declared, DEBT_PROFILE)


def test_a_profile_with_inverted_bands_is_refused(document: Any) -> None:
    declared = dict(document["debt_profile"])
    declared["fail_closed_threshold"] = declared["forced_llm_threshold"]
    declared["forced_llm_threshold"] = "0.99"
    with pytest.raises(ValueError):
        parse_artifact(declared, DEBT_PROFILE)


def test_module_is_tagged_algorithmic() -> None:
    import ccf.halflife.debt as debt_mod

    assert debt_mod.__ccf_mode__ == "algorithmic"


# --- what the debt points at (D-IMPL-118, D-IMPL-119) ----------------------
#
# The carrier is a TOP-LEVEL field on `ContextProductContract`, a sibling of
# `debt` rather than a member of `DebtAssessment` — which is what D-IMPL-118
# ruled and what makes these assertions about the *delivered bytes* rather than
# about a nested value that would have ridden the assessment for free. The
# vessel is therefore what these cases construct.


#: Handles this test owns. Deployment-side by construction: the SDK enumerates
#: none of them and interprets none of them, and their opacity is the point —
#: under D-IMPL-119 limb 4 a handle a reading principal could interpret is
#: refused outright until the assembly path is principal-scoped.
_HANDLE_A = DebtEvidencePointer(handle="handle-a")
_HANDLE_B = DebtEvidencePointer(handle="handle-b")


def _product(
    evidence: tuple[DebtEvidencePointer, ...] = NO_DEBT_EVIDENCE,
) -> ContextProductContract:
    """The vessel as every construction site builds it, plus the carrier."""
    return ContextProductContract(
        schema_name="test.debt-evidence",
        schema_version="1.0.0",
        plan_id="test/plan",
        tenant_id="tenant-debt",
        temporal_boundary=NOW,
        expires_at=NOW + timedelta(seconds=600),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"temporal.as-of-boundary"}),
            policy_bundle_versions=frozenset({"policy-v1"}),
            graph_snapshot_at=NOW,
        ),
        payload={"answer": "42"},
        debt_evidence=evidence,
    )


def test_the_carrier_round_trips_unchanged() -> None:
    """Populate and extract — exactly and only what D-IMPL-117 says is owed.

    The pair is the whole SDK obligation for this gap: a way to put pointers on
    the delivered product, and a way to read them back off it. There is no
    third thing here, because *which* observations are worth pointing at is
    the context product creator's judgement, not the SDK's.
    """
    product = _product((_HANDLE_A, _HANDLE_B))

    assert product.debt_evidence == (_HANDLE_A, _HANDLE_B)
    rebuilt = ContextProductContract.model_validate(product.model_dump())
    assert rebuilt.debt_evidence == (_HANDLE_A, _HANDLE_B)
    assert content_hash(rebuilt) == content_hash(product)


def test_an_unpopulated_carrier_is_a_positive_claim_and_not_a_silence() -> None:
    """D-IMPL-38: the absent value is an assertion, never `None`-as-unknown.

    What this rules out that nothing else does: a nullable carrier. Under one,
    a product that pointed at nothing and a product whose pointers somebody
    dropped in transit would be the same artifact — the repudiation failure
    mode every sentinel in this fabric closes.
    """
    assert _product().debt_evidence == NO_DEBT_EVIDENCE
    assert NO_DEBT_EVIDENCE is not None
    assert NO_DEBT_EVIDENCE == ()


def test_the_carrier_is_inside_the_delivered_content_address() -> None:
    """D-IMPL-118's authorized cost, executed rather than asserted.

    `canonical_bytes` walks a model field-by-field over `model_fields`, so a
    top-level field is in the address by construction. This is the case that
    would fail if a later change moved the carrier off the vessel and left the
    ruling's reconstruction obligation looking gratuitous.
    """
    assert content_hash(_product((_HANDLE_A,))) != content_hash(_product())
    assert content_hash(_product((_HANDLE_A,))) != content_hash(
        _product((_HANDLE_B,))
    )


def test_declaration_order_does_not_move_the_bytes() -> None:
    """Order-insensitive inside a content address (the `scorers` precedent).

    Declaration order is not a fact about the decision. The field is inside the
    delivered product's address, so an order-sensitive carrier would make two
    identical products hash differently — which is the defect
    `_pins_are_one_per_factor_in_canonical_order` already exists to prevent for
    the scorer pins, restated here because the reason is identical.
    """
    forward = _product((_HANDLE_A, _HANDLE_B))
    reversed_ = _product((_HANDLE_B, _HANDLE_A))

    assert forward.debt_evidence == reversed_.debt_evidence
    assert content_hash(forward) == content_hash(reversed_)


def test_a_repeated_handle_is_refused_at_construction() -> None:
    """Two pointers to one thing is incoherent, not stricter.

    Refused rather than collapsed, which is why the carrier is a sorted tuple
    and not a `frozenset`: a set would have deduplicated the repetition
    silently, and the repetition is exactly the thing worth naming.
    """
    with pytest.raises(ValueError, match="at most once"):
        _product((_HANDLE_A, DebtEvidencePointer(handle=_HANDLE_A.handle)))


def test_a_float_handle_is_refused_rather_than_coerced() -> None:
    """The `_refuse_float` discipline extends to the new member.

    Shared with every other debt value for the same reason, stated once in
    `ccf.halflife.assessment`: these bytes are inside a content address and
    floats are not bit-stable across platforms.
    """
    with pytest.raises(ValueError, match="never float"):
        DebtEvidencePointer(handle=1.0)  # type: ignore[arg-type]


def test_assess_debt_is_unchanged_by_the_carrier(profile: DebtProfile) -> None:
    """The carrier landed on the vessel, so the pure function did not move.

    D-IMPL-118 placed the carrier top-level on `ContextProductContract`, not
    inside `DebtAssessment`, so `assess_debt` gains no parameter and stays pure
    over `(factors, profile)` — the D-IMPL-105 posture. This asserts the
    consequence directly: `debt` and `signal` are what they were.
    """
    factors = _whole(freshness=Decimal("0.8"))
    assessment = assess_debt(factors, profile=profile)

    assert assessment.debt == context_debt(factors)
    assert assessment.signal is DebtSignal.OK
    assert set(DebtAssessment.model_fields) == {
        "debt",
        "signal",
        "factors",
        "scorers",
    }
    assert "evidence" not in DebtAssessment.model_fields
    assert "debt_evidence" not in DebtAssessment.model_fields
