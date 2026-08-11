"""The debt shape that travels: D_c, its three factors, and the scorers in force.

Whitepaper §7.7 (D_c as the assembly-time shortfall) and
``docs/CCF_Whitepaper_1-2.md:2696`` — debt *"is a runtime signal the agent must
consume as a first-class decision input, not a log-line to be read after the
fact"*. :mod:`ccf.halflife.debt` owns the *computation*; this module owns the
*shape that reaches a consumer*.

**Why this is its own module, and not simply part of** :mod:`ccf.halflife.debt`.
D-IMPL-100 lands :class:`DebtAssessment` on
:class:`~ccf.products.contract.ContextProductContract`, and
:mod:`ccf.products.contract` cannot import :mod:`ccf.halflife.debt`: that module
reaches :mod:`ccf.controlplane.artifacts` for ``DebtProfile`` and
``HalfLifeTable`` — directly, and again transitively through
:mod:`ccf.halflife.decay` — and :mod:`ccf.controlplane.artifacts` imports
:mod:`ccf.products.contract`. A top-level import from the vessel would therefore
close a cycle at load time. The shape lives *below* both: its only dependency is
:class:`~ccf.contracts.base.CCFContract`, which is exactly what lets the vessel
carry it. :mod:`ccf.halflife.debt` re-exports every name here, so no existing
import moves and no construction site changes.

**Per factor, not a scalar** (D-IMPL-99). The three factors travel with the
answer because an examiner asking *why* a decision was escalated needs to see
which of freshness, completeness or semantic consistency collapsed, and the
multiplicative form makes that question answerable only if the inputs are
carried.

**The scorer in force is pinned beside the value** (D-IMPL-47). A factor value
is reproducible only alongside the computation that produced it: a replay that
resolved today's scorer would re-derive a number under a different measurement
and call it the same decision. The ruling committed to this pin from the start;
:class:`ScorerPin` is where it lands.

**Recency ships; salience does not** (D-IMPL-101). Recency is computable today
through :meth:`~ccf.halflife.debt.FreshnessScorer.score`. Salience has no
producer anywhere in the SDK, and none is invented here — the two shapes a
later cycle may choose between are recorded in the ruling, not anticipated in
this module.

**Decimal, never float.** These values reach the replay record and are inside
the product's content address under D-IMPL-100; floats are not bit-stable, so a
float is *refused at construction* rather than coerced. Coercion would be the
worse failure: it produces a plausible number whose provenance is a
platform-dependent binary expansion, and the address carrying it would then
depend on where the product was assembled.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Final, Literal, Protocol

from pydantic import field_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "NO_SCORER_PINS",
    "DebtAssessment",
    "DebtFactorName",
    "DebtFactors",
    "DebtSignal",
    "ScorerPin",
]

_ZERO = Decimal(0)
_UNIT = Decimal(1)

#: The three factors of the extended form, as a closed set of names
#: (whitepaper §7.7). A ``Literal`` rather than a free string so that a pin
#: naming a factor the fabric does not compute is refused at construction: the
#: names are the SDK's own structure, never deployment vocabulary.
DebtFactorName = Literal["freshness", "completeness", "semantic_consistency"]


def _refuse_float(value: object) -> object:
    """Refuse a ``float`` before validation coerces it into a ``Decimal``.

    Shared by every debt value in this module because the reason is the same
    everywhere and stating it twice invites the two statements to drift.
    """
    if isinstance(value, float):
        raise ValueError(
            "debt values are Decimal, never float: they reach the replay "
            "record and sit inside the delivered product's content address "
            "(D-IMPL-100), and floats are not bit-stable across platforms"
        )
    return value


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
            does not know enough to support the decision. §7.7 reads missing
            counter-evidence as grounds for caution rather than reassurance, so
            this state escalates and never quietly proceeds.

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
            (:class:`~ccf.halflife.debt.FreshnessScorer`).
        completeness: C — the fraction of required fields actually populated
            across the assembled sources. **Not per principal** (D-IMPL-105): a
            consultation a principal is not entitled to make is not part of
            that principal's ``C_required``, so its absence is not a shortfall.
        semantic_consistency: S — the fraction of assembled sources whose
            structured assertions agree on the entities, relationships and
            magnitudes the decision cares about.

    Each lies in ``[0, 1]``; a factor outside that interval is refused rather
    than clipped, because a clipped factor is a measurement error rendered as a
    plausible number. Decimal throughout, and a ``float`` is refused at
    construction rather than coerced — see the module docstring.

    Only F has an SDK reference scorer. C and S are supplied by the caller
    until their scorers ship (DESIGN.md §2B.4, D-IMPL-47) — the SDK would
    otherwise have to invent a required-field vocabulary and a contradiction
    detector, both of which are deployment knowledge.
    """

    freshness: Decimal
    completeness: Decimal
    semantic_consistency: Decimal

    @field_validator(
        "freshness", "completeness", "semantic_consistency", mode="before"
    )
    @classmethod
    def _factor_is_not_a_float(cls, value: object) -> object:
        return _refuse_float(value)

    @field_validator("freshness", "completeness", "semantic_consistency")
    @classmethod
    def _factor_is_in_the_unit_interval(cls, value: Decimal) -> Decimal:
        if not _ZERO <= value <= _UNIT:
            raise ValueError("debt factors must lie in [0, 1]")
        return value


class _ScorerIdentity(Protocol):
    """The identity half of :class:`~ccf.halflife.debt.DebtFactorScorerProtocol`.

    Structural, and deliberately narrower than the scorer Protocol itself: a
    pin needs a scorer's *identity*, not its ability to score, and asking for
    less is what lets a deployment pin a scorer it has already run and
    discarded.
    """

    @property
    def scorer_id(self) -> str: ...

    @property
    def scorer_version(self) -> str: ...


class ScorerPin(CCFContract):
    """Which scorer produced one factor, at which version (D-IMPL-47).

    The ruling requires the scorer version *in force* to be pinned into replay,
    because a factor value is only reproducible alongside the computation that
    produced it. A replay that resolved the scorer installed *today* would
    re-derive a number under a different measurement and present it as the
    number the decision was made with — the substitution the replay plane
    exists to prevent (CLAUDE.md §7.4, D-IMPL-26).

    Attributes:
        factor: Which of the three factors this pin accounts for.
        scorer_id: Stable identity of the scorer that produced it.
        scorer_version: The version of that scorer's computation.
    """

    factor: DebtFactorName
    scorer_id: str
    scorer_version: str

    @classmethod
    def of(
        cls, scorer: _ScorerIdentity, *, factor: DebtFactorName
    ) -> "ScorerPin":
        """Pin ``scorer`` as the producer of ``factor``.

        Read off the scorer rather than passed alongside it, so the pin cannot
        name a version the scorer does not claim.
        """
        return cls(
            factor=factor,
            scorer_id=scorer.scorer_id,
            scorer_version=scorer.scorer_version,
        )


#: An assessment whose factors were supplied rather than produced by a declared
#: scorer.
#:
#: The positive assertion, in :data:`~ccf.replay.record.NO_GRAPH_QUERIES`'s
#: voice and for its reason: *no scorer declared itself the producer of these
#: factors*. Only F has an SDK reference scorer, so an unpinned assessment is
#: the ordinary posture rather than a defect — and an unpinned assessment and
#: one whose pins somebody dropped would otherwise be the same artifact, which
#: is the repudiation failure mode every sentinel in this fabric closes. The
#: empty tuple rather than a marker string because each element is a structured
#: pin and the field must stay one shape.
NO_SCORER_PINS: Final[tuple[ScorerPin, ...]] = ()


class DebtAssessment(CCFContract):
    """One D_c computation, the routing state it lands in, and what produced it.

    Carries the factors it was computed from, not just the scalar: an examiner
    asking *why* a decision was escalated needs to see which of the three
    dimensions collapsed, and the multiplicative form makes that question
    answerable only if the inputs travel with the answer (D-IMPL-99).

    **This type is delivered, not merely logged** (D-IMPL-100). It is carried on
    :class:`~ccf.products.contract.ContextProductContract`, so it is inside the
    product's content address and reaches every consumer the vessel reaches; and
    it is carried on the Decision Replay record's dimension 5, so a replay
    rebuilds the same bytes rather than diverging on a value it cannot
    reconstruct.

    Attributes:
        debt: D_c in ``[0, 1]``.
        signal: The CAR state (:class:`DebtSignal`).
        factors: The F/C/S inputs.
        scorers: The scorers in force, one per accounted factor, in a canonical
            order (D-IMPL-47). Defaults to :data:`NO_SCORER_PINS`.
    """

    debt: Decimal
    signal: DebtSignal
    factors: DebtFactors
    scorers: tuple[ScorerPin, ...] = NO_SCORER_PINS

    @field_validator("debt", mode="before")
    @classmethod
    def _debt_is_not_a_float(cls, value: object) -> object:
        return _refuse_float(value)

    @field_validator("scorers")
    @classmethod
    def _pins_are_one_per_factor_in_canonical_order(
        cls, value: tuple[ScorerPin, ...]
    ) -> tuple[ScorerPin, ...]:
        """Refuse a second pin for a factor; store the rest in one order.

        Two pins for one factor describe two computations claiming to have
        produced one value, which is not a stricter record but an incoherent
        one. The ordering follows ``graph_secret_refs``' reasoning exactly:
        declaration order is not a fact about the decision, and this value is
        inside the delivered product's content address, so an order-sensitive
        field would make two identical assessments hash differently.
        """
        factors = [pin.factor for pin in value]
        if len(set(factors)) != len(factors):
            raise ValueError(
                "a factor may carry at most one scorer pin; two pins for one "
                "factor describe two computations claiming to have produced "
                "the same value (D-IMPL-47)"
            )
        return tuple(sorted(value, key=lambda pin: pin.factor))

    @field_validator("debt")
    @classmethod
    def _debt_is_in_the_unit_interval(cls, value: Decimal) -> Decimal:
        if not _ZERO <= value <= _UNIT:
            raise ValueError("D_c must lie in [0, 1]")
        return value
