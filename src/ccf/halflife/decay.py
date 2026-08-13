"""λ_c — Context Half-life as formal decay (whitepaper §7.7).

The whitepaper commits to one formula::

    R(t) = R₀ × (1/2)^((t − t₀) / λ_c)

and to two properties of λ_c that shape this module more than the arithmetic
does:

**λ_c is Control Plane configuration per observation type, never code**
(INV-CH7-58). A 10-K's half-life is months; a sanctions match's is minutes.
The SDK ships the curve and refuses to ship the calibration — the whitepaper's
own illustrative table says as much ("these values are illustrative, not
empirical"). So there is no table in this module, no fallback rate, and no
``default=`` anywhere: an observation type the deployment never declared raises
:class:`MissingHalfLife` (D-IMPL-38). A fabricated decay rate would express a
confidence nobody chose, and it would express it in the one number the
Conditional Assessment Routing predicate reads.

**λ_c is not a TTL** (INV-CH7-57). Decay is a continuous curve, not a cutoff:
:func:`relevance_ratio` never returns zero and never raises on age, because
data past its half-life stays accessible for historical reconstruction —
Decision Replay depends on it (whitepaper §7.10) — while no longer counting as
current for decision purposes.

Determinism
-----------
Every quantity is :class:`~decimal.Decimal` and every computation runs in a
pinned decimal context, because these numbers reach the replay record. Floats
are excluded by construction: the canonical serializer refuses them (they are
not bit-stable across platforms), and a freshness figure that reproduces
differently on the auditor's machine is not a freshness figure. Elapsed time is
measured in whole microseconds rather than ``timedelta.total_seconds()``, which
returns a float.

The clock is always injected. Decay reads ``now`` as an argument, never from
the wall clock, so a decision's freshness re-computes identically years later.

Algorithmic module (CINV-03): pure functions over typed inputs, no I/O, no
clock, no LLM dependency ever.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from typing import Final

from ccf.controlplane.artifacts import HalfLifeEntry, HalfLifeTable
from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [
    "NO_SUBJECT_IDENTITY",
    "HalfLifeEntry",
    "HalfLifeTable",
    "MissingHalfLife",
    "Observation",
    "TemporalOrderError",
    "effective_half_life",
    "freshness",
    "half_life_of",
    "relevance_ratio",
]

#: Working precision for the decay computation. Pinned rather than inherited
#: from the ambient decimal context so that two processes with different
#: contexts cannot produce two freshness figures for one observation.
DECIMAL_PRECISION = 28

#: Quantum every returned ratio is rounded to. Rounding at a fixed exponent is
#: what makes the value stable enough to compare bit-for-bit in replay; the
#: exponent is deep below any threshold band a deployment would configure.
RATIO_QUANTUM = Decimal(1).scaleb(-18)

_HALF = Decimal(1) / Decimal(2)
_MICROSECOND = timedelta(microseconds=1)


class MissingHalfLife(LookupError):
    """No λ_c is declared for the requested observation type.

    Raised instead of substituting a rate. See the module docstring
    (INV-CH7-58, D-IMPL-38).
    """


class TemporalOrderError(ValueError):
    """An observation is timestamped after the instant it is evaluated at.

    Surfaced rather than clamped to "perfectly fresh": an observation from the
    future means a clock, a source, or an as-of boundary is wrong, and silently
    scoring it at full relevance would convert a data-integrity fault into a
    confident decision.
    """


#: The positive assertion that an observation was recorded **without** a subject
#: identity — *this observation names nothing it is an observation of* — in the
#: voice of :data:`~ccf.halflife.assessment.NO_SCORER_PINS` and
#: :data:`~ccf.replay.record.NO_GRAPH_QUERIES`, and for their reason.
#:
#: ``D-IMPL-120`` ruled the identity **optional** (``qc-optional``) and ruled out
#: expressing its absence as ``None``: an assembler that had no identity to
#: carry and one that dropped the identity it held would then be the same
#: artifact, which is the repudiation failure mode every sentinel in this fabric
#: closes (``D-IMPL-38``'s no-silent-defaults discipline). A marker string rather
#: than an empty container because the field is one opaque string and must stay
#: one shape.
NO_SUBJECT_IDENTITY: Final[str] = "no-subject-identity"


class Observation(CCFContract):
    """One dated observation, typed by the vocabulary λ_c is configured against.

    Whitepaper §7.7 binds λ_c to the observation *type* in Control Plane
    configuration and explicitly not to the individual document, so decay reads
    exactly two things from an observation — which type it is, and when it was
    made. Nothing about the rate travels on the observation itself.

    The third field is **carried, never consumed**: no function in this module
    reads ``subject``, and the freshness figure is identical whether it is
    populated or not. It exists so that a downstream consumer of D_c can say
    *which* observations a debt figure summarises (CLAUDE.md §11 — an SDK
    extension; see below).

    Attributes:
        observation_type: The deployment's observation-type name. Its
            vocabulary is user configuration; the SDK never enumerates it.
        observed_at: When the fabric learned the observation (the T axis's
            ``observed_at``, :mod:`ccf.contracts.claims`). Timezone-aware; a
            naive instant is rejected, because an implicit timezone is a silent
            default (D-IMPL-38).
        subject: What this observation is an observation *of*. An opaque
            identifier the deployment chooses — an entity URI, a claim id, a
            document id, or something else again. Its scheme is user
            configuration; the SDK never enumerates it, never parses it and
            never compares it to anything. Optional (D-IMPL-120), defaulting to
            :data:`NO_SUBJECT_IDENTITY` rather than to ``None``.

            **SDK extension (CLAUDE.md §11), not whitepaper-derived.** Whitepaper
            §7.7 binds λ_c to the observation *type* and says nothing about
            subject identity; this field is the carrying structure D-IMPL-117
            assigns to the SDK, and none of the judgement about which
            observations matter, which D-IMPL-117 assigns away from it.
    """

    observation_type: str
    observed_at: datetime
    subject: str = NO_SUBJECT_IDENTITY


def half_life_of(table: HalfLifeTable, observation_type: str) -> timedelta:
    """Return the declared λ_c for ``observation_type``.

    Raises:
        MissingHalfLife: the table declares no entry for that type. There is no
            fallback rate (INV-CH7-58, D-IMPL-38).
    """
    try:
        entry = table.entries[observation_type]
    except KeyError:
        raise MissingHalfLife(
            f"no half-life declared for observation type {observation_type!r};"
            " declare one in the Control Plane λ_c table (no default rate exists)"
        ) from None
    return timedelta(seconds=entry.half_life_seconds)


def effective_half_life(
    half_life: timedelta, risk_sensitivity: Decimal
) -> timedelta:
    """Scale ``half_life`` into a decision class's Freshness Budget.

    Whitepaper §7.7 defines the Freshness Budget as ``λ_c × Risk Sensitivity``:
    the more consequential the decision class, the less staleness it tolerates,
    so its budget is spent sooner on the same observation. A sensitivity below
    one shortens the effective half-life; above one widens it. The multiplier
    is a per-class Control Plane value
    (:class:`ccf.controlplane.artifacts.DebtProfile`), never an SDK constant.

    Raises:
        ValueError: ``half_life`` or ``risk_sensitivity`` is not positive. Zero
            is not "no decay" and not "instant decay" — it is an undeclared
            calibration, and guessing which meaning was intended is exactly the
            silent default this subsystem refuses.
    """
    if half_life <= timedelta(0):
        raise ValueError("half-life must be positive")
    if risk_sensitivity <= Decimal(0):
        raise ValueError("risk sensitivity must be positive")
    micros = Decimal(half_life // _MICROSECOND) * risk_sensitivity
    scaled = timedelta(microseconds=int(micros))
    if scaled <= timedelta(0):
        raise ValueError(
            "risk sensitivity collapses the freshness budget below the"
            " representable minimum"
        )
    return scaled


def relevance_ratio(*, elapsed: timedelta, half_life: timedelta) -> Decimal:
    """Return ``R(t) / R₀`` for an observation aged ``elapsed`` (whitepaper §7.7).

    The whitepaper's formula with ``R₀`` divided out, so the result is the
    dimensionless retained-relevance fraction the freshness factor F composes
    from. Exactly ``1`` at the observation instant, exactly one half at one
    half-life, and asymptotic toward — never equal to — zero thereafter:
    aged context stays reconstructible (INV-CH7-57).

    Raises:
        ValueError: ``half_life`` is not positive.
        TemporalOrderError: ``elapsed`` is negative.
    """
    if half_life <= timedelta(0):
        raise ValueError("half-life must be positive")
    if elapsed < timedelta(0):
        raise TemporalOrderError(
            "elapsed time is negative: the observation is dated after the"
            " instant it is evaluated at"
        )
    if elapsed == timedelta(0):
        return Decimal(1)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        exponent = Decimal(elapsed // _MICROSECOND) / Decimal(
            half_life // _MICROSECOND
        )
        ratio = _HALF**exponent
    return ratio.quantize(RATIO_QUANTUM)


def freshness(
    observation: Observation,
    *,
    now: datetime,
    table: HalfLifeTable,
    risk_sensitivity: Decimal,
) -> Decimal:
    """Return the retained decision-relevance of ``observation`` at ``now``.

    Composes the two configured inputs — the type's declared λ_c and the
    decision class's risk sensitivity — into the Freshness Budget, then reads
    the decay curve at the observation's age. This is the per-observation input
    the F factor of ``D_c = 1 − (F · C · S)`` aggregates
    (:mod:`ccf.halflife.debt`).

    Args:
        observation: The dated, typed observation.
        now: The decision instant. Injected, never read from a clock, so the
            figure re-computes identically at replay time.
        table: The resolved, versioned λ_c table artifact.
        risk_sensitivity: The decision class's budget multiplier.

    Raises:
        MissingHalfLife: the type has no declared λ_c.
        TemporalOrderError: the observation post-dates ``now``.
        ValueError: ``now`` or ``observed_at`` is naive, or the sensitivity is
            not positive.
    """
    if now.tzinfo is None or observation.observed_at.tzinfo is None:
        raise ValueError(
            "decay requires timezone-aware instants; a naive datetime carries"
            " an implicit timezone, which is a silent default (D-IMPL-38)"
        )
    budget = effective_half_life(
        half_life_of(table, observation.observation_type), risk_sensitivity
    )
    return relevance_ratio(elapsed=now - observation.observed_at, half_life=budget)
