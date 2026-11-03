"""Derive trade-shaping distributions from real CFTC Part 43 FX records.

Design §1.5 -- Part 43's bulk is NON-DELIVERABLE forwards (KRW, TWD, INR,
BRL), because deliverable FX is carved out of the swap definition by Treasury
determination. Patterning on the whole file yields an all-NDF, Asian-hours
dataset that matches nothing else in the estate.

Design §1.6 -- the G10 majors ARE present, at 5.3% of rows, carrying their own
London/NY execution profile and their own amendment chains. So this module
filters to the six pairs first and derives every distribution from real
records OF THOSE PAIRS.

Only distributions cross this boundary. No real trade is ever loaded as a
trade: the SHAPE is public and cited, the INSTANCES are engineered.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

#: The six, in market convention. Order is fixed so tests can pin it.
G10_PAIRS = ("EUR/USD", "USD/JPY", "AUD/USD", "USD/CAD", "GBP/USD", "EUR/GBP")

#: Market convention is a TABLE, not a rule: USD is the base for JPY and CAD
#: but the quote for EUR, GBP, and AUD. Any rule inferred from one row is
#: wrong for the others, which is exactly the §7.4 trap in another costume.
_CONVENTION = {
    frozenset(("EUR", "USD")): "EUR/USD",
    frozenset(("USD", "JPY")): "USD/JPY",
    frozenset(("AUD", "USD")): "AUD/USD",
    frozenset(("USD", "CAD")): "USD/CAD",
    frozenset(("GBP", "USD")): "GBP/USD",
    frozenset(("EUR", "GBP")): "EUR/GBP",
}


def normalise_pair(c1: str, c2: str) -> str | None:
    """Market-convention pair name, or None if not one of the six."""
    if not c1 or not c2 or c1 == c2:
        return None
    return _CONVENTION.get(frozenset((c1, c2)))


def derive_profile(rows: Iterable[dict]) -> dict:
    """Distributions over G10 rows only.

    Returns pair mix, execution-hour mix, action-type mix, and the
    chain-length histogram (how many dissemination links each original
    accumulated).
    """
    pair_mix: Counter[str] = Counter()
    hour_mix: Counter[str] = Counter()
    action_mix: Counter[str] = Counter()
    per_original: Counter[str] = Counter()
    n = 0

    for r in rows:
        pair = normalise_pair(r.get("Notional currency-Leg 1", ""),
                              r.get("Notional currency-Leg 2", ""))
        if pair is None:
            continue
        n += 1
        pair_mix[pair] += 1
        action_mix[r.get("Action type", "") or "UNKNOWN"] += 1
        ts = r.get("Execution Timestamp", "") or ""
        if len(ts) > 13:
            hour_mix[ts[11:13]] += 1
        odi = r.get("Original Dissemination Identifier", "") or ""
        if odi:
            per_original[odi] += 1

    chain_lengths = Counter(str(v) for v in per_original.values())

    return {
        "n_rows": n,
        "pair_mix": dict(pair_mix),
        "hour_mix": dict(hour_mix),
        "action_mix": dict(action_mix),
        "chain_lengths": dict(chain_lengths),
    }
