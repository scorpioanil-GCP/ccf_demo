"""D_c — Context Debt and the debt-driven routing signals (whitepaper §7.7).

§7.7 defines D_c as the shortfall measured at assembly time: how much less
coverage the fabric delivered than the decision at hand needs. It is committed
to as a live input the agent reads before deciding, not as after-the-fact
telemetry — which is why this module returns it as a typed value on the
decision path rather than emitting it to a log.

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
D_c above the class's Forced-LLM threshold routes to Forced LLM, where the
semantic stage is invoked knowing what the context is missing; D_c above the
class's Fail-Closed threshold declines rather than deciding. Both bands exist
because §7.7 treats debt as a risk amplifier — a thinner context raises the
urgency of a finding rather than discounting it.

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

Where the shape lives
---------------------
:class:`DebtAssessment`, :class:`DebtFactors`, :class:`DebtSignal` and
:class:`ScorerPin` are defined in :mod:`ccf.halflife.assessment` and re-exported
here, so every existing import of them from this module keeps working. The split
is not cosmetic: D-IMPL-100 carries the assessment on
:class:`~ccf.products.contract.ContextProductContract`, and the vessel cannot
import *this* module — it reaches :mod:`ccf.controlplane.artifacts`, which
imports the vessel. The shape therefore lives below both; the computation stays
here, with the Control Plane values it needs.

**What computing debt is now for** (D-IMPL-100). Until this phase D_c was
computed and discarded: it appeared on neither the product nor the replay
record, so five of the six axes of ``G(E, R, T, P, Π, L)`` reached the wire and
the sixth — the one that says how much to trust the other five — did not.
:func:`assess_debt`'s result is now carried on the delivered product and on the
Decision Replay record, which is what whitepaper ``:2696`` asks for: debt
reaching the agent *while* it decides, conditioning that decision, rather than
settling into an audit trail somebody reads afterwards.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.halflife.assessment import (
    NO_DEBT_EVIDENCE,
    NO_OBLIGATION_IN_FORCE,
    NO_SCORER_PINS,
    NO_SIGNAL_OBLIGATIONS,
    NO_SOURCE_REFRESH_RECENCY,
    DebtAssessment,
    DebtEvidence,
    DebtEvidencePointer,
    DebtFactorName,
    DebtFactors,
    DebtSignal,
    ScorerPin,
    SignalObligation,
    SignalObligations,
    SourceRefreshRecency,
    SourceRefreshWindow,
)
from ccf.halflife.decay import Observation, freshness

__ccf_mode__ = "algorithmic"

__all__ = [
    "NO_DEBT_EVIDENCE",
    "NO_OBLIGATION_IN_FORCE",
    "NO_SCORER_PINS",
    "NO_SIGNAL_OBLIGATIONS",
    "NO_SOURCE_REFRESH_RECENCY",
    "DebtAssessment",
    "DebtEvidence",
    "DebtEvidencePointer",
    "DebtFactorName",
    "DebtFactorScorerProtocol",
    "DebtFactors",
    "DebtSignal",
    "FreshnessScorer",
    "ScorerPin",
    "SignalObligation",
    "SignalObligations",
    "SourceRefreshRecency",
    "SourceRefreshWindow",
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

    **That contract is unchanged, and it is why the assembly scorer does not
    call this method on an empty sequence** (``24.6-05``, ledger row
    ``24.6-L-06``).
    :meth:`~ccf.products.debt_scorer.AssemblyDebtScorer.__call__` uses the
    multiplicative identity for F over zero observations and records **no
    freshness pin**, precisely so that no caller can read that identity as this
    scorer's answer. The two are consistent: a *measurement* over nothing is
    undefined and raises here; the *identity element* of ``1 − F·C·S`` is an
    algebraic fact and belongs to the fold, not to a scorer. Where the coverage
    statement belongs is C, which is the deployment's (``D-IMPL-38``).

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
    one. That is the Trust Triangle's conjunctive gating written algebraically
    — one weak leg condemns the product however strong the remaining two are
    (INV-CH7-66). There is no weighted-additive alternative in this module to
    fall back to.
    """
    return _UNIT - (
        factors.freshness * factors.completeness * factors.semantic_consistency
    )


def assess_debt(
    factors: DebtFactors,
    *,
    profile: DebtProfile,
    scorers: tuple[ScorerPin, ...] = NO_SCORER_PINS,
) -> DebtAssessment:
    """Compute D_c and the CAR routing state under ``profile``.

    Bands are read strictly: the whitepaper routes on D_c "above the
    class-specific threshold", so a value *at* a threshold is inside the band
    below it. Fail-Closed is tested before Forced-LLM because the profile
    guarantees it is the higher band, and the more conservative state wins
    wherever both would match.

    The returned signal is a value. Nothing here escalates, invokes, or logs —
    see the module docstring.

    **Pure over** ``(factors, profile)`` **, and it stays that way** (D-IMPL-105).
    No entitlement, principal or grant argument joins this signature. Under a
    per-principal debt figure the completeness number *moves when a source is
    withheld*, so a caller could infer what they are not allowed to see from
    the debt they are shown — an oracle over the entitlement configuration,
    reachable with ordinary delivery access and quieter than a refusal, because
    nothing in the response says a consultation was declined. A refused
    consultation is simply not part of ``C_required`` for that principal, so
    there is no per-principal figure to differ and nothing to difference. The
    ruling dissolves the coupling rather than redacting it.

    Args:
        factors: The F/C/S measurements.
        profile: The decision class's resolved, versioned debt profile. Passed
            in already resolved so that the caller's pinning of ``(key,
            version)`` is explicit and lands in the replay record; this
            function never reaches for a Control Plane "latest".
        scorers: The scorers in force, one per accounted factor (D-IMPL-47).
            **Carried, never consulted** — the pins do not participate in the
            computation, so passing them changes neither ``debt`` nor
            ``signal``; they travel so that a factor value is reproducible
            alongside what produced it. Defaults to :data:`NO_SCORER_PINS`, so
            every call site written before the pin existed asserts exactly what
            it always asserted.
    """
    debt = context_debt(factors)
    if debt > profile.fail_closed_threshold:
        signal = DebtSignal.FAIL_CLOSED
    elif debt > profile.forced_llm_threshold:
        signal = DebtSignal.FORCED_LLM
    else:
        signal = DebtSignal.OK
    return DebtAssessment(
        debt=debt, signal=signal, factors=factors, scorers=scorers
    )
