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
from ccf.halflife.assessment import (
    NO_DEBT_EVIDENCE,
    NO_OBLIGATION_IN_FORCE,
    NO_SIGNAL_OBLIGATIONS,
    NO_SOURCE_REFRESH_RECENCY,
    DebtEvidencePointer,
    SignalObligation,
    SourceRefresh,
)
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
    *,
    recency: tuple[SourceRefresh, ...] = NO_SOURCE_REFRESH_RECENCY,
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
        source_refresh_recency=recency,
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


# --- when the source was last refreshed (D-IMPL-117, D-IMPL-118) -----------
#
# `D-IMPL-112` gap 2, in Dave's own framing: computed freshness says how much
# the fabric's own decay curve has eaten and says NOTHING about when the
# upstream registry last published. This slot records the second fact. It is a
# TOP-LEVEL field on `ContextProductContract` — `D-IMPL-118` `qa-toplevel`, the
# same branch the evidence carrier above took, and the entry says explicitly
# that it "price[s] all three Track B vessel-carried members identically".
#
# `D-IMPL-101` bounds it: recency ships, salience defers. Nothing below ranks,
# weights or scores anything, and the SDK compares a refresh instant to nothing
# at all — asserted structurally by
# `test_the_recency_is_carried_and_never_consumed`.


#: The repo root, anchored on this file rather than on `Path.cwd()`: a
#: structural check whose scan root depends on the working directory passes or
#: fails for reasons that have nothing to do with the tree.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: Source references and refresh instants this test module owns.
#: **Deployment-side by construction**: the SDK enumerates no source vocabulary
#: and declares no cadence (`D-IMPL-117` — *"a slot for source-refresh recency,
#: owing no definition of a source or a cadence"*). The two instants are
#: deliberately unrelated to `NOW`, because nothing here is allowed to be
#: computed from the fabric's own clock.
_REFRESH_A = SourceRefresh(
    source_ref="test-source-alpha",
    refreshed_at=datetime(2026, 1, 9, 6, 30, tzinfo=UTC),
)
_REFRESH_B = SourceRefresh(
    source_ref="test-source-beta",
    refreshed_at=datetime(2026, 2, 17, 22, 0, tzinfo=UTC),
)


def test_the_recency_slot_round_trips_unchanged() -> None:
    """Populate and extract — exactly and only what D-IMPL-117 says is owed.

    The pair is the whole SDK obligation for this gap: a way to record when an
    upstream source was last refreshed on the delivered product, and a way to
    read it back off it. There is no third thing, because whether a September
    refresh is recent enough for this decision is the context product creator's
    judgement.
    """
    product = _product(recency=(_REFRESH_A, _REFRESH_B))

    assert product.source_refresh_recency == (_REFRESH_A, _REFRESH_B)
    rebuilt = ContextProductContract.model_validate(product.model_dump())
    assert rebuilt.source_refresh_recency == (_REFRESH_A, _REFRESH_B)
    assert content_hash(rebuilt) == content_hash(product)


def test_a_refresh_entry_carries_a_reference_and_an_instant_and_nothing_else() -> None:
    """D-IMPL-117's boundary, asserted on the field set rather than described.

    No source type, no cadence, no refresh interval, no staleness threshold and
    no default. What this rules out that nothing else does: a slot that grew a
    second opinion — the moment the entry carries an interval, the SDK has
    declared what "overdue" means for somebody else's registry.
    """
    assert set(SourceRefresh.model_fields) == {"source_ref", "refreshed_at"}
    assert SourceRefresh.model_fields["source_ref"].is_required()
    assert SourceRefresh.model_fields["refreshed_at"].is_required()


def test_a_naive_refresh_instant_is_refused_rather_than_coerced() -> None:
    """`Observation.observed_at`'s discipline, restated (D-IMPL-38).

    An implicit timezone is a silent default, and this value is inside the
    delivered product's content address — so a coerced zone would make the same
    refresh fact hash differently depending on where the product was assembled.
    Refused at construction, not at first use.
    """
    with pytest.raises(ValueError, match="zone"):
        SourceRefresh(
            source_ref="test-source-alpha",
            refreshed_at=datetime(2026, 1, 9, 6, 30),
        )


def test_an_unrecorded_recency_is_a_positive_claim_and_not_a_silence() -> None:
    """D-IMPL-38: the absent value is an assertion, never `None`-as-unknown.

    What this rules out that nothing else does: a nullable slot. Under one, a
    product whose deployment knows nothing about its sources' publication
    schedule and a product whose recency somebody dropped in transit would be
    the same artifact — the repudiation failure mode every sentinel in this
    fabric closes.
    """
    assert _product().source_refresh_recency == NO_SOURCE_REFRESH_RECENCY
    assert NO_SOURCE_REFRESH_RECENCY is not None
    assert NO_SOURCE_REFRESH_RECENCY == ()


def test_a_changed_refresh_instant_moves_the_delivered_bytes() -> None:
    """The slot is inside the content address, so the instant is load-bearing.

    A decision made against a source refreshed in January is not the decision
    made against one refreshed in February. This is the case that would fail if
    a later change moved the slot off the vessel and left D-IMPL-118's
    reconstruction obligation looking gratuitous.
    """
    later = SourceRefresh(
        source_ref=_REFRESH_A.source_ref,
        refreshed_at=_REFRESH_A.refreshed_at + timedelta(days=40),
    )

    assert content_hash(_product(recency=(_REFRESH_A,))) != content_hash(_product())
    assert content_hash(_product(recency=(_REFRESH_A,))) != content_hash(
        _product(recency=(later,))
    )


def test_recency_declaration_order_does_not_move_the_bytes() -> None:
    """Order-insensitive inside a content address (the `scorers` precedent).

    Declaration order is not a fact about the decision. The slot is inside the
    delivered product's address, so an order-sensitive collection would make
    two products recording the same refresh facts hash differently — which is
    the defect `_pins_are_one_per_factor_in_canonical_order` already exists to
    prevent for the scorer pins, restated here because the reason is identical.
    """
    forward = _product(recency=(_REFRESH_A, _REFRESH_B))
    reversed_ = _product(recency=(_REFRESH_B, _REFRESH_A))

    assert forward.source_refresh_recency == reversed_.source_refresh_recency
    assert content_hash(forward) == content_hash(reversed_)


def test_a_repeated_source_reference_is_refused_at_construction() -> None:
    """Two refresh instants for one source is incoherent, not stricter.

    Refused rather than collapsed, which is why the slot is a sorted tuple and
    not a `frozenset`: a set keyed on the whole entry would keep both, and a
    set keyed on the reference would drop one **silently** — and a source that
    was refreshed at two different instants is exactly the incoherence worth
    naming out loud.
    """
    with pytest.raises(ValueError, match="at most one refresh instant"):
        _product(
            recency=(
                _REFRESH_A,
                SourceRefresh(
                    source_ref=_REFRESH_A.source_ref,
                    refreshed_at=_REFRESH_B.refreshed_at,
                ),
            )
        )


def test_a_float_source_reference_is_refused_rather_than_coerced() -> None:
    """The `_refuse_float` discipline extends to the new member.

    Shared with every other value in `ccf.halflife.assessment` for the reason
    stated once there: these bytes are inside a content address and floats are
    not bit-stable across platforms.
    """
    with pytest.raises(ValueError, match="never float"):
        SourceRefresh(
            source_ref=1.0,  # type: ignore[arg-type]
            refreshed_at=NOW,
        )


def test_the_recency_is_carried_and_never_consumed() -> None:
    """The SDK stores the fact and draws no conclusion from it (D-IMPL-101).

    `Observation.subject`'s *"carried, never consumed"* discipline, restated
    structurally rather than described. The moment the SDK compares a refresh
    instant to `now`, to a cadence or to a threshold, it has decided which
    sources matter — which is salience, which D-IMPL-101 deferred and for which
    *"no mechanism ... lands in this phase"*.

    Asserted as a scan rather than as a unit test because the property is an
    absence: there is no call to make and no value to compare, so the only
    honest assertion is that no module reads the member at all.
    """
    root = REPO_ROOT / "src" / "ccf"
    readers = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "refreshed_at" in path.read_text(encoding="utf-8")
    )

    assert readers == ["halflife/assessment.py"]

    declaring = (root / "halflife" / "assessment.py").read_text(encoding="utf-8")
    assert "datetime.now" not in declaring
    assert "utcnow" not in declaring


def test_assess_debt_is_unchanged_by_the_recency_slot(profile: DebtProfile) -> None:
    """The slot landed on the vessel, so the pure function did not move.

    D-IMPL-118 placed all three Track B members top-level on
    `ContextProductContract`, so `assess_debt` gains no parameter and stays
    pure over `(factors, profile)` — the D-IMPL-105 posture. Asserted on the
    consequence directly: `debt` and `signal` are byte-for-byte what they were
    for the same factors and the same profile, and the assessment's field set
    is untouched.
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
    assert "source_refresh_recency" not in DebtAssessment.model_fields
    assert "refreshed_at" not in DebtAssessment.model_fields


# --- what a debt signal obliges (D-IMPL-112 gap 3, D-IMPL-117, D-IMPL-118) --
#
# `D-IMPL-112` recorded the analyst's third missing item — what operational
# obligation `forced_llm` actually imposes. `15.6-RESEARCH.md` § B4 measured the
# asymmetry that makes it a gap: `DebtSignal.FORCED_LLM` is produced at exactly
# one site and consumed nowhere, while `OK` and `FAIL_CLOSED` each have one
# consumer.
#
# The SDK's whole obligation here is a BINDING MECHANISM. `D-IMPL-117`:
# *"a signal-to-obligation binding that survives replay, and owes no obligation
# vocabulary (that is user configuration ...)"*. Every obligation token below is
# owned by this test module; the SDK enumerates none of them, and
# `tests/invariants/test_no_obligation_vocabulary.py` is the standing gate that
# keeps it that way.
#
# The binding's calibration half lives on `DebtProfile`, which already owns
# `forced_llm_threshold` and `fail_closed_threshold` and is already pinned
# per-agent — so the calibration stays in one artifact. The RESOLVED value rides
# the product vessel as a top-level field under `D-IMPL-118` `qa-toplevel`, the
# same branch the two members above took.


#: Obligation references this test module owns. **Deployment-side by
#: construction**: the SDK enumerates no obligation vocabulary and interprets no
#: obligation reference (`D-IMPL-117`, CLAUDE.md §11). Deliberately not words an
#: analyst used, so nothing here can be mistaken for a recommended set.
_OBLIGATION_FOR_FORCED = "test-obligation-alpha"
_OBLIGATION_FOR_FAILED = "test-obligation-beta"


def _profile_binding(*bindings: SignalObligation) -> DebtProfile:
    """A profile as every artifact declares one, plus the bindings under test."""
    return DebtProfile(
        semver="1.0.0",
        risk_sensitivity=Decimal("1.2"),
        forced_llm_threshold=Decimal("0.20"),
        fail_closed_threshold=Decimal("0.60"),
        signal_obligations=bindings,
    )


def test_a_bound_obligation_round_trips_through_the_profile() -> None:
    """Populate and extract — exactly and only what D-IMPL-117 says is owed.

    The pair is the whole SDK obligation for this gap: a way for a deployment to
    say what a signal obliges, and a way to read that back. There is no third
    thing, because what the obligation *means* is the context product creator's
    judgement and the SDK never interprets it.
    """
    binding = SignalObligation(
        signal=DebtSignal.FORCED_LLM, obligation_ref=_OBLIGATION_FOR_FORCED
    )
    profile = _profile_binding(binding)

    assert profile.signal_obligations == (binding,)
    rebuilt = DebtProfile.model_validate(profile.model_dump())
    assert rebuilt.signal_obligations == (binding,)
    assert content_hash(rebuilt) == content_hash(profile)


def test_the_sdk_accepts_an_obligation_string_it_has_never_seen() -> None:
    """Structure is validated; meaning is not (D-IMPL-117, D-IMPL-29).

    The claim this case exists to assert rather than leave implied: the SDK
    holds no list of permitted obligations, so an arbitrary token no shipped
    module has ever seen is accepted verbatim. A validator that refused it would
    have made the SDK the arbiter of a vocabulary it does not own.
    """
    arbitrary = "urn:acme:obligation:9f2c-never-seen-by-the-sdk"
    profile = _profile_binding(
        SignalObligation(signal=DebtSignal.FAIL_CLOSED, obligation_ref=arbitrary)
    )

    assert profile.obligation_for(DebtSignal.FAIL_CLOSED) == arbitrary


def test_a_key_that_is_not_a_debt_signal_is_refused_and_named() -> None:
    """Keys are the SDK's type, so keys are the SDK's business.

    `DebtSignal` is a whitepaper §7.7 CAR routing state the SDK owns, ships and
    branches on — so a binding naming a state the fabric never produces is
    refused rather than carried, and the offending key is named so the profile
    author is not left diffing against an enum they cannot see.
    """
    with pytest.raises(ValueError, match="not-a-signal"):
        SignalObligation(
            signal="not-a-signal",  # type: ignore[arg-type]
            obligation_ref=_OBLIGATION_FOR_FORCED,
        )


def test_a_duplicate_signal_binding_is_refused_at_construction() -> None:
    """Two obligations for one signal is incoherent, not stricter.

    Refused rather than collapsed, which is why the binding is a sorted tuple
    and not a mapping: a mapping loaded from YAML keeps the last duplicate
    **silently**, and a signal bound twice is exactly the contradiction a
    profile author needs told about.
    """
    with pytest.raises(ValueError, match="at most one obligation"):
        _profile_binding(
            SignalObligation(
                signal=DebtSignal.FORCED_LLM, obligation_ref=_OBLIGATION_FOR_FORCED
            ),
            SignalObligation(
                signal=DebtSignal.FORCED_LLM, obligation_ref=_OBLIGATION_FOR_FAILED
            ),
        )


def test_a_partial_binding_is_accepted_and_the_rest_read_the_sentinel() -> None:
    """"Some signals bound" is the common real case, so it has one reading.

    Pinned by a test rather than left incidental: a deployment that has an
    answer for Fail-Closed and none for Ok is not a malformed deployment, and
    the unbound signal resolves to the named positive sentinel rather than to a
    borrowed neighbour's obligation or to an error.
    """
    profile = _profile_binding(
        SignalObligation(
            signal=DebtSignal.FAIL_CLOSED, obligation_ref=_OBLIGATION_FOR_FAILED
        )
    )

    assert profile.obligation_for(DebtSignal.FAIL_CLOSED) == _OBLIGATION_FOR_FAILED
    assert profile.obligation_for(DebtSignal.OK) == NO_OBLIGATION_IN_FORCE
    assert profile.obligation_for(DebtSignal.FORCED_LLM) == NO_OBLIGATION_IN_FORCE


def test_a_profile_that_binds_nothing_is_a_positive_claim_not_a_silence() -> None:
    """D-IMPL-38: the absent value is an assertion, never `None`-as-unknown.

    What this rules out that nothing else does: a nullable binding. Under one, a
    deployment that deliberately declared no obligations and one whose bindings
    somebody dropped in transit would be the same artifact — the repudiation
    failure mode every sentinel in this fabric closes. It is also exactly what
    every profile written before this field existed was already asserting.
    """
    profile = _profile_binding()

    assert profile.signal_obligations == NO_SIGNAL_OBLIGATIONS
    assert NO_SIGNAL_OBLIGATIONS is not None
    assert NO_SIGNAL_OBLIGATIONS == ()
    assert profile.obligation_for(DebtSignal.FORCED_LLM) == NO_OBLIGATION_IN_FORCE
    assert NO_OBLIGATION_IN_FORCE is not None


def test_two_profiles_differing_only_in_a_binding_have_different_bytes() -> None:
    """The binding is part of the calibration, so it is part of its identity.

    A profile that obliges one thing on Forced-LLM is not the profile that
    obliges another, and the Control Plane addresses artifacts by content — so
    rebinding mints a new address rather than mutating an old one in place,
    which is what D-IMPL-26's exact-version rule then lets replay resolve
    against.
    """
    one = _profile_binding(
        SignalObligation(
            signal=DebtSignal.FORCED_LLM, obligation_ref=_OBLIGATION_FOR_FORCED
        )
    )
    other = _profile_binding(
        SignalObligation(
            signal=DebtSignal.FORCED_LLM, obligation_ref=_OBLIGATION_FOR_FAILED
        )
    )

    assert content_hash(one) != content_hash(other)
    assert content_hash(one) != content_hash(_profile_binding())


def test_binding_declaration_order_does_not_move_the_profile_bytes() -> None:
    """Order-insensitive inside a content address (the `scorers` precedent).

    Declaration order is not a fact about the calibration. The profile is
    content-addressed and version-pinned per agent, so an order-sensitive
    collection would make two identical calibrations resolve as two artifacts —
    the defect `_pins_are_one_per_factor_in_canonical_order` already exists to
    prevent, restated here because the reason is identical.
    """
    forced = SignalObligation(
        signal=DebtSignal.FORCED_LLM, obligation_ref=_OBLIGATION_FOR_FORCED
    )
    failed = SignalObligation(
        signal=DebtSignal.FAIL_CLOSED, obligation_ref=_OBLIGATION_FOR_FAILED
    )

    forward = _profile_binding(forced, failed)
    reversed_ = _profile_binding(failed, forced)

    assert forward.signal_obligations == reversed_.signal_obligations
    assert content_hash(forward) == content_hash(reversed_)


def test_a_half_declared_binding_is_refused() -> None:
    """A signal named with nothing bound to it is not a binding.

    A blank reference is the shape a half-finished profile edit leaves behind,
    and accepting it would make "declared, with nothing to do" and "not
    declared" two spellings of one claim — while only the second has a sentinel
    saying so.
    """
    with pytest.raises(ValueError, match="obligation reference"):
        SignalObligation(signal=DebtSignal.FORCED_LLM, obligation_ref="   ")


def test_the_sentinel_spelling_is_refused_as_a_declared_obligation() -> None:
    """The sentinel keeps one meaning, so nothing may impersonate it.

    Without this, a deployment could declare the sentinel's own spelling and
    make "bound to this" indistinguishable from "bound to nothing" — collapsing
    the very distinction D-IMPL-38 requires the sentinel to hold open.
    """
    with pytest.raises(ValueError, match="reserved"):
        SignalObligation(
            signal=DebtSignal.FORCED_LLM, obligation_ref=NO_OBLIGATION_IN_FORCE
        )


def test_a_float_obligation_reference_is_refused_rather_than_coerced() -> None:
    """The `_refuse_float` discipline extends to the new member.

    Shared with every other value in `ccf.halflife.assessment` for the reason
    stated once there: these bytes reach a content address and floats are not
    bit-stable across platforms.
    """
    with pytest.raises(ValueError, match="never float"):
        SignalObligation(
            signal=DebtSignal.FORCED_LLM,
            obligation_ref=1.0,  # type: ignore[arg-type]
        )


def test_a_declared_profile_parses_its_bindings_through_the_loader(
    document: Any,
) -> None:
    """The binding arrives the way every Control Plane value arrives.

    Through `parse_artifact`, off a declared document, rather than through a
    constructor a test wrote — a field that only ever round-trips in-process has
    not been shown to be declarable (CLAUDE.md §6.4).
    """
    declared = dict(document["debt_profile"])
    declared["signal_obligations"] = [
        {"signal": "forced_llm", "obligation_ref": _OBLIGATION_FOR_FORCED}
    ]
    artifact = parse_artifact(declared, DEBT_PROFILE)

    assert isinstance(artifact, DebtProfile)
    assert artifact.obligation_for(DebtSignal.FORCED_LLM) == _OBLIGATION_FOR_FORCED
    assert artifact.obligation_for(DebtSignal.OK) == NO_OBLIGATION_IN_FORCE


def test_a_declared_profile_naming_an_unknown_signal_is_refused(
    document: Any,
) -> None:
    """The key check fires where a profile author actually meets it."""
    declared = dict(document["debt_profile"])
    declared["signal_obligations"] = [
        {"signal": "forced-llm", "obligation_ref": _OBLIGATION_FOR_FORCED}
    ]
    with pytest.raises(ValueError, match="forced-llm"):
        parse_artifact(declared, DEBT_PROFILE)


def test_the_sdk_names_no_obligation_and_takes_no_action_on_one() -> None:
    """CLAUDE.md §11, asserted structurally rather than promised.

    Two absences, and they are different absences. The first is vocabulary: no
    module under `src/` writes an obligation reference, so the only string a
    replay can carry is one a deployment declared.
    `tests/invariants/test_no_obligation_vocabulary.py` holds the syntactic half
    of that claim; this holds the textual one.

    The second is behaviour, and it is the one a reviewer is most likely to
    misread. `FORCED_LLM` had zero consumers before this plan and still has zero
    **in the SDK**: the fabric carries the binding into the record and branches
    on it nowhere, because branching on it would mean deciding what an
    obligation means — the judgement `D-IMPL-117` assigns to the context product
    creator.
    """
    root = REPO_ROOT / "src" / "ccf"
    writers = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "obligation_ref" in path.read_text(encoding="utf-8")
    )

    assert writers == ["controlplane/artifacts.py", "halflife/assessment.py"]

    for module in writers:
        source = (root / module).read_text(encoding="utf-8")
        assert "re-pull" not in source
        assert "escalate" not in source
        assert "supervised" not in source
