"""D_c — Context Debt and the debt-driven routing signals (whitepaper §7.7).

Context Debt is "the gap, at assembly time, between contextual coverage the
current decision requires and contextual coverage the fabric can actually
deliver" — and the whitepaper is emphatic that it is "a runtime signal the
agent must consume as a first-class decision input, not a log-line to be read
after the fact." This module computes it and turns it into a typed signal.

Two forms, both committed to by §7.7::

    D_c = 1 − (C_available / C_required)          (basic — quantity of coverage)
    D_c = 1 − (F · C · S)                         (extended — quality of coverage)

**The extended form is multiplicative, and that is an architectural
commitment, not a tuning preference** (INV-CH7-62/63). When any one of
freshness, completeness or semantic consistency approaches zero, D_c approaches
one regardless of the other two. The weighted-additive alternative
``D_c_alt = 1 − (w_F·F + w_C·C + w_S·S)`` masks exactly that case: the
whitepaper's guarantor example scores 0.955 multiplicatively and 0.23
additively on identical context. This module ships no weights and no additive
path — not as a default, at all — because the masking is what makes the
additive form indefensible under an examiner's reading.

The routing bands
-----------------
:func:`assess_debt` returns the D_c value together with a
:class:`DebtSignal` drawn from the Conditional Assessment Routing predicate:
D_c above the class's Forced-LLM threshold routes to Forced LLM ("the LLM must
be invoked with explicit awareness of the debt"); D_c above the class's
Fail-Closed threshold declines rather than deciding. The whitepaper's
conservative bias is the reason both bands exist: "elevated D_c biases urgency
upward, not downward" — debt is a risk amplifier.

**In I.1 the signals are values and nothing more.** No LLM path exists in the
fabric core, and no HITL escalation surface has shipped yet, so
:func:`assess_debt` has no side effects: it does not raise on Fail-Closed, does
not call anything, and does not log. Consumers wire behavior to the signal in
later phases (DESIGN.md §2B.4 — the escalation pathway is owned by §4/§5). A
function that *acted* on the signal here would put the routing policy in code,
which is precisely where it must not live.

Thresholds, weights that do not exist, the risk-sensitivity multiplier and
every λ_c are Control Plane values resolved by pinned version
(:mod:`ccf.controlplane.artifacts`); this module holds none of them
(CLAUDE.md §11, CINV-01; D-IMPL-38).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.halflife.decay import Observation, freshness
from pydantic import field_validator

__ccf_mode__ = "algorithmic"

__all__ = [
    "DebtAssessment",
    "DebtFactorScorerProtocol",
    "DebtFactors",
    "DebtSignal",
    "FreshnessScorer",
    "assess_debt",
    "basic_debt",
    "context_debt",
]

_ZERO = Decimal(0)
_UNIT = Decimal(1)

#: Identity of the reference freshness scorer. Pinned into replay alongside the
#: value it produced, so a decision re-traces against the scorer it actually
#: ran under rather than the one installed today (D-IMPL-47).
FRESHNESS_SCORER_ID = "ccf.reference.freshness-from-decay"
FRESHNESS_SCORER_VERSION = "1.0.0"


class DebtSignal(StrEnum):
    """The routing state an assessed D_c falls into (whitepaper §7.7 CAR).

    Members:
        OK: D_c sits below both configured bands. Nothing about debt changes
            the decision path; this is not an assertion that context is
            perfect, only that its shortfall is within the class's declared
            tolerance.
        FORCED_LLM: D_c is above the class's Forced-LLM threshold — context is
            partial or stale, and a semantic stage must be invoked *with
            explicit awareness of the debt*.
        FAIL_CLOSED: D_c is above the class's Fail-Closed threshold. The fabric
            does not know enough to support the decision. The whitepaper's
            posture is that "the absence of strong evidence against a suspicion
            is treated as an argument for caution", so this state escalates and
            never quietly proceeds.

    The two escalation states are deliberately distinct: Forced-LLM is *more*
    reasoning, Fail-Closed is *no* decision. Collapsing them would make an
    outage indistinguishable from a hard question.
    """

    OK = "ok"
    FORCED_LLM = "forced_llm"
    FAIL_CLOSED = "fail_closed"


class DebtFactors(CCFContract):
    """The three quality factors of the extended form (whitepaper §7.7).

    Attributes:
        freshness: F — the composition of per-observation decay curves against
            the class's ``λ_c × Risk Sensitivity`` budget
            (:class:`FreshnessScorer`).
        completeness: C — the fraction of required fields actually populated
            across the assembled sources.
        semantic_consistency: S — the fraction of assembled sources whose
            structured assertions agree on the entities, relationships and
            magnitudes the decision cares about.

    Each lies in ``[0, 1]``; a factor outside that interval is refused rather
    than clipped, because a clipped factor is a measurement error rendered as a
    plausible number. Decimal throughout: these values reach the replay record,
    and floats are not bit-stable.

    Only F has an SDK reference scorer in I.1. C and S are supplied by the
    caller until their scorers ship (DESIGN.md §2B.4, D-IMPL-47) — the SDK
    would otherwise have to invent a required-field vocabulary and a
    contradiction detector, both of which are deployment knowledge.
    """

    freshness: Decimal
    completeness: Decimal
    semantic_consistency: Decimal

    @field_validator("freshness", "completeness", "semantic_consistency")
    @classmethod
    def _factor_is_in_the_unit_interval(cls, value: Decimal) -> Decimal:
        if not _ZERO <= value <= _UNIT:
            raise ValueError("debt factors must lie in [0, 1]")
        return value


class DebtAssessment(CCFContract):
    """One D_c computation and the routing state it lands in.

    Carries the factors it was computed from, not just the scalar: an examiner
    asking *why* a decision was escalated needs to see which of the three
    dimensions collapsed, and the multiplicative form makes that question
    answerable only if the inputs travel with the answer.

    Attributes:
        debt: D_c in ``[0, 1]``.
        signal: The CAR state (:class:`DebtSignal`).
        factors: The F/C/S inputs.
    """

    debt: Decimal
    signal: DebtSignal
    factors: DebtFactors


@runtime_checkable
class DebtFactorScorerProtocol(Protocol):
    """The seam a per-factor scorer implements (D-IMPL-47; DESIGN.md §2B.4).

    A Protocol rather than a base class so a deployment can substitute its own
    completeness or consistency measurement without inheriting anything, and so
    the SDK's reference scorers carry no privileged status.

    ``scorer_id`` and ``scorer_version`` are part of the surface because the
    ruling requires the scorer version *in force* to be pinned into replay: a
    factor value is only reproducible alongside the computation that produced
    it.
    """

    @property
    def scorer_id(self) -> str:
        """Stable identity of this scorer."""
        ...

    @property
    def scorer_version(self) -> str:
        """Version of this scorer's computation."""
        ...

    def score(
        self, observations: Sequence[Observation], *, now: datetime
    ) -> Decimal:
        """Return this scorer's factor in ``[0, 1]`` for ``observations``."""
        ...


@dataclass(frozen=True)
class FreshnessScorer:
    """The SDK's reference F scorer: decay-ratio aggregation (D-IMPL-47).

    F is the mean of the per-observation relevance ratios at the decision
    instant, each read off the λ_c curve for that observation's own type and
    scaled by the class's risk sensitivity. The mean is the *reference*
    aggregation, chosen because it is the one the whitepaper's "freshness-
    weighted composite" language supports without importing a weighting scheme
    the SDK has no basis to pick; a deployment that needs a different
    aggregation implements :class:`DebtFactorScorerProtocol` and pins its own
    scorer version.

    An empty observation sequence raises rather than scoring 1: "the fabric
    retrieved nothing" is a coverage statement (C), and letting it enter as
    perfect freshness would launder a source outage into a low-debt reading —
    the precise failure the fail-closed posture exists to prevent.

    Attributes:
        table: The resolved, versioned λ_c table.
        risk_sensitivity: The decision class's Freshness Budget multiplier.
    """

    table: HalfLifeTable
    risk_sensitivity: Decimal

    @property
    def scorer_id(self) -> str:
        return FRESHNESS_SCORER_ID

    @property
    def scorer_version(self) -> str:
        return FRESHNESS_SCORER_VERSION

    def score(
        self, observations: Sequence[Observation], *, now: datetime
    ) -> Decimal:
        """Return F for ``observations`` as of ``now``.

        Raises:
            ValueError: ``observations`` is empty.
            ccf.halflife.decay.MissingHalfLife: an observation's type has no
                declared λ_c.
            ccf.halflife.decay.TemporalOrderError: an observation post-dates
                ``now``.
        """
        if not observations:
            raise ValueError(
                "freshness is undefined over zero observations; an empty"
                " assembly is a completeness shortfall, not a fresh one"
            )
        total = sum(
            (
                freshness(
                    observation,
                    now=now,
                    table=self.table,
                    risk_sensitivity=self.risk_sensitivity,
                )
                for observation in observations
            ),
            start=_ZERO,
        )
        return total / Decimal(len(observations))


def basic_debt(*, available: int, required: int) -> Decimal:
    """Return ``D_c = 1 − (C_available / C_required)`` (whitepaper §7.7).

    The quantity-of-coverage form: what a credit-decision agent consumes when
    the question is "did the fabric deliver everything the review asked for".

    Raises:
        ValueError: ``required`` is not positive (a decision class that
            requires nothing has no coverage gap to measure, and dividing by it
            would manufacture one), or ``available`` is negative or exceeds
            ``required`` — over-coverage is a mis-count, not negative debt.
    """
    if required <= 0:
        raise ValueError("required coverage must be positive")
    if available < 0:
        raise ValueError("available coverage cannot be negative")
    if available > required:
        raise ValueError(
            "available coverage exceeds the requirement; D_c has no negative"
            " band, so this is a counting error rather than a surplus"
        )
    return _UNIT - (Decimal(available) / Decimal(required))


def context_debt(factors: DebtFactors) -> Decimal:
    """Return ``D_c = 1 − (F · C · S)`` (whitepaper §7.7; INV-CH7-62).

    Multiplicative-conjunctive by commitment: any factor at zero drives D_c to
    one, which is the algebraic statement of the Trust Triangle's conjunctive
    gating — a product whose lineage leg is weak fails the triangle even when
    the other two legs are strong (INV-CH7-66). There is no weighted-additive
    alternative in this module to fall back to.
    """
    return _UNIT - (
        factors.freshness * factors.completeness * factors.semantic_consistency
    )


def assess_debt(factors: DebtFactors, *, profile: DebtProfile) -> DebtAssessment:
    """Compute D_c and the CAR routing state under ``profile``.

    Bands are read strictly: the whitepaper routes on D_c "above the
    class-specific threshold", so a value *at* a threshold is inside the band
    below it. Fail-Closed is tested before Forced-LLM because the profile
    guarantees it is the higher band, and the more conservative state wins
    wherever both would match.

    The returned signal is a value. Nothing here escalates, invokes, or logs —
    see the module docstring.

    Args:
        factors: The F/C/S measurements.
        profile: The decision class's resolved, versioned debt profile. Passed
            in already resolved so that the caller's pinning of ``(key,
            version)`` is explicit and lands in the replay record; this
            function never reaches for a Control Plane "latest".
    """
    debt = context_debt(factors)
    if debt > profile.fail_closed_threshold:
        signal = DebtSignal.FAIL_CLOSED
    elif debt > profile.forced_llm_threshold:
        signal = DebtSignal.FORCED_LLM
    else:
        signal = DebtSignal.OK
    return DebtAssessment(debt=debt, signal=signal, factors=factors)
