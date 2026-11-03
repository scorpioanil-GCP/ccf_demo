"""Wave 16 — the scoring arithmetic, and nothing else.

## What this is not

This is NOT the SDK's Rank Operator. An Operator is a runtime SDK entity --
resolved through a registry, ordered by the Operator Plan DAG Generator,
executed in the Data Plane, serving a principal at request time
(`cognitive-context-fabric/ccf-architecture`, L4). This module registers
nothing, composes into no plan, serves no principal, and emits no contract.

It exists because the per-perspective weight vectors are OURS to produce (§C
assigns them to Postgres as `synthetic — internal`), and shipping a weight
vector without confirming it separates the M&A and DCM orderings would be a
table of numbers and a promise.

Pure functions, no I/O. `validators/ib_rank.py` does the reading.
"""
from __future__ import annotations

import datetime as _dt

#: A banker's desk implies which perspective's weight vector applies to
#: their coverage -- a judgement call, not a stored fact, since no
#: banker -> perspective table exists. Lives here once (a pure constant, no
#: I/O) and is imported by both `loaders/load_sqlite_wave16.py` and
#: `validators/ib_rank.py`, which is not merely a copy of it deleted for
#: house-keeping: those two modules disagreeing about which desk maps to
#: which perspective is exactly the kind of drift a shared source of truth
#: exists to prevent.
DESK_TO_PERSPECTIVE = {
    "M&A Advisory": "PSP-MA",
    "Leveraged Finance": "PSP-DCM",
    "Treasury Services": "PSP-DCM",
    "CIB Coverage": "PSP-SECTOR",
    "Credit Risk": "PSP-SECTOR",
}


def decay(*, age_days: float, half_life_days: float) -> float:
    """`R(t) = R0 * (1/2) ** (age / lambda_c)` per the CCF half-life formula.

    A signal observed in the future (negative age) is clamped to 1.0 rather
    than amplified -- a clock skew should not make a signal count double.
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def score(*, signals, weights, half_lives, as_of: str) -> dict[str, float]:
    """Weighted, decayed score per LEI.

    `weights` maps signal_type -> weight for ONE perspective and ONE weight
    version. A signal whose type is absent from `weights` contributes zero;
    it is never defaulted to 1.0, which would let a missing weight row
    silently dominate a ranking.
    """
    at = _dt.date.fromisoformat(as_of)
    out: dict[str, float] = {}
    for s in signals:
        # Refuse, do not cap. `decay()` clamps negative age to 1.0 so clock
        # skew cannot amplify a signal past full strength -- but that is a
        # CAP. A signal genuinely dated after the as-of instant would score
        # the maximum and dominate the ranking, so it is an error here
        # rather than something to silently absorb.
        if s["observed_at"] > as_of:
            raise ValueError(
                f"signal {s.get('signal_id', s['lei'])} observed_at "
                f"{s['observed_at']} is after as_of {as_of}")
        weight = weights.get(s["signal_type"])
        if weight is None:
            out.setdefault(s["lei"], 0.0)
            continue
        half_life = half_lives[s["signal_type"]]
        age = (at - _dt.date.fromisoformat(s["observed_at"])).days
        contribution = (
            weight * float(s.get("magnitude", 1.0))
            * decay(age_days=age, half_life_days=half_life))
        out[s["lei"]] = out.get(s["lei"], 0.0) + contribution
    return out


def rank(scores: dict[str, float]) -> list[tuple[str, float]]:
    """Descending by score, ties broken by LEI ascending.

    The tie-break is not cosmetic: without it, two equal scores order by dict
    insertion and a replay diff reports a change that is really just
    iteration order.
    """
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
