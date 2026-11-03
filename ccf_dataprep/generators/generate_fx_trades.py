"""Wave 12 Task 12 — 500 FX trades, three observing systems, amendment chains.

Design `markets.fx-reconciliation.v1`. Everything shaping the trade
population — which pair, what hour it executes, whether it gets amended and
how long the chain runs — is **sampled from `wave12_part43_profile.json`**
(`generators/part43.py::derive_profile` over real DTCC Part 43 G10 rows),
never hand-specified. `notional_band` is the one exception: Part 43 caps and
bands large notionals to protect participant anonymity, so `derive_profile`
never reads notional at all — there is no real distribution to sample, and
the spec's own §C caveat is explicit that this product's subject is *when*
systems observed a trade, not exact economics. The bands below are
engineered, clearly so.

## Ruling F19 — do not correct the chain-length undercount

`derive_profile` counts amendment links per dissemination id **within one
day**; the merge across ten days sums those per-day histograms rather than
the raw per-id counts across the whole window. A chain that crosses midnight
(`NEWT` day N, `CORR` day N+1 against the same id) reads as two length-1
chains instead of one length-2 chain — about 4.6% of chained originals. That
bias is conservative (it can only understate long chains), and §F's floors
(≥10 chained, ≥3 with two-or-more) are comfortably inside the observed shape
as measured. This generator samples `chain_lengths` verbatim; it does NOT
inflate lengths to compensate. See `docs/wave12-plan.md` Task 12.

## The value-date pool, and why it is six days, not the profile's ten

The profile's ten real days run 2026-08-06 .. 2026-08-19. `fx_reference_rate`
(loaded from FRED, Task 6) only reaches 2026-08-14 — three of the profile's
days (08-17/18/19) have no rate row for any pair, and 08-14 itself has no
*following* publication, which the intraday tick session below needs as its
closing anchor. So trades draw their `value_date` from the six profile days
that have BOTH a prior and a next close on file: 08-06, 07, 10, 11, 12, 13.
Every one of those six is real Part 43 activity; nothing here shifts the
data toward the floor.

## Ruling F3 — the intraday FX path, and the anchor direction

For every `(pair, value_date)` actually used, a 78-point 5-minute session is
built with `generators/ticks.py` (Task 3/4's already-tested Brownian
bridge), anchored exactly as Task 4 anchors the Treasury curve: the session
OPENS at the closest PRIOR published close and CLOSES at `value_date`'s own
published close, labelled under `value_date`. (The brief's prose — "between
that date's close and the next publication's" — is read as the same
adjacent-publication mechanism Task 4 already implements; this docstring
states the direction chosen so a reader checking against Task 14/15 can
confirm or correct it.) `fx_reference_rate`'s daily closes are the anchors
and are never modified; only the within-day path is engineered. Every tick
carries `provenance: "synthetic — engineered"`.

Each system's `value_rate` in `system_records` is read off this same path at
that event's TRUE time (before the system's own clock offset is applied to
the stored `observed_at`) — so revaluation genuinely happens at each
system's own observation time rather than off one flat daily number, which
is the whole of what F3 asks for. A lookup outside the 288-tick, full-day window (Ruling F21) clamps to the
nearest published anchor rather than extrapolating a value nothing backs.

For this task's baseline population every system observes the SAME true
market moment for a given trade or amendment event, so their `value_rate`
values agree; only their *recorded* `observed_at` differs, by that system's
fixed clock offset. Manufacturing a genuine value discrepancy on top of that
is Task 13's job (`narrative_wave12.py`), not this generator's.

## Two artifacts, one generator

`sources/screening/wave12_fx.json` carries exactly the brief's stated
interface — `trades`, `system_records`, `clock_offsets`, `amendments` — and
`sources/screening/wave12_fx_ticks.json` carries the intraday path, kept
separate for the same reason Task 4 kept `wave12_ticks.json` apart from
`wave12_treasury.json`: one table's rows, one file, no key inside the trade
artifact bloated with a ~78x-larger sibling.

    uv run generators/generate_fx_trades.py --dry-run
    uv run generators/generate_fx_trades.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect         # noqa: E402
from ccf.currency import record_inputs, verify_current             # noqa: E402
from generators.narrative_wave12 import (                          # noqa: E402
    INVERSION_TRADE_ID, MATERIALITY, SURVIVOR_TRADE_ID, build_breaks,
)
from generators.ticks import brownian_bridge                      # noqa: E402

SCREEN = REPO_ROOT / "sources" / "screening"
OUT = SCREEN / "wave12_fx.json"
OUT_TICKS = SCREEN / "wave12_fx_ticks.json"
PROFILE_NAME = "wave12_part43_profile.json"

SEED = 20260821
N_TRADES = 500

#: Two classes, not one (CLAUDE.md rule 1; spec §C, `fx-post-trade-
#: reconciliation`). Only the intraday tick path and the break populations
#: (the latter set directly in `narrative_wave12.py`) are `engineered` --
#: deliberately invented to create a condition public data will not supply.
#: Everything else here -- trades, per-system observation records, the
#: amendment chain, clock offsets, materiality thresholds -- is `internal`:
#: invented because it is bank-internal by nature, not because it was
#: engineered toward a demonstration. Before this fix every row here carried
#: one blanket `PROVENANCE` constant of `"synthetic — engineered"`, which
#: collapsed the two classes into one and let a consumer filtering for
#: "deliberately planted" conditions catch `materiality_threshold` in that
#: set -- implying the break threshold was tuned to produce the break mix,
#: which it was not.
PROVENANCE_INTERNAL = "synthetic — internal"
PROVENANCE_ENGINEERED = "synthetic — engineered"

G10_PAIRS = ("EUR/USD", "USD/JPY", "AUD/USD", "USD/CAD", "GBP/USD", "EUR/GBP")

#: Fixed, recorded clock offsets. Data, destined for Fluree — never a
#: constant inside reconciliation logic (design ruling, Task 12 brief).
SYSTEMS: dict[str, int] = {"trading": 0, "settlement": 47, "risk": -112}

#: Real DTCC action types that amend an existing original. `NEWT` never
#: appears here — it is the original, not a link in its own chain.
NON_ORIGINAL_ACTIONS = ("CORR", "TERM", "MODI", "EROR", "REVI")

#: Six of the profile's ten real days — see module docstring for why the
#: other four (08-14, 17, 18, 19) are excluded.
VALUE_DATE_POOL = [
    date(2026, 8, 6), date(2026, 8, 7), date(2026, 8, 10),
    date(2026, 8, 11), date(2026, 8, 12), date(2026, 8, 13),
]

#: Engineered — Part 43 bands/caps notional precisely so it cannot be
#: sampled from real data (see module docstring). Weighted toward smaller
#: tickets, tapering off at the block-trade cap, matching the general shape
#: of any real OTC size distribution without claiming to measure one.
NOTIONAL_BAND_WEIGHTS: dict[str, int] = {
    "1,000,000-5,000,000": 35,
    "5,000,000-25,000,000": 35,
    "25,000,000-100,000,000": 20,
    "100,000,000-250,000,000": 8,
    "250,000,000+": 2,
}


def weighted_choice(rng: random.Random, mix: dict) -> str:
    """Sample a key with probability proportional to its observed count."""
    keys = sorted(mix)
    weights = [mix[k] for k in keys]
    return rng.choices(keys, weights=weights, k=1)[0]


# --------------------------------------------------------------------------
# Database reads
# --------------------------------------------------------------------------

def fetch_counterparty_leis(cur) -> list[str]:
    """The 50 ANCHORS, which is what FX counterparties are drawn from.

    FILTER ADDED 2026-08-24. This selected every `legal_entity` row and the
    caller asserted the result was exactly 50 -- true when the table held only
    anchors, and already false since Wave 14 put three ABS trusts in it, so
    this generator had been refusing to run (53 != 50) before the 103 GLEIF
    reference subsidiaries arrived. An unfiltered read plus a hardcoded count
    is the positional-identity hazard: it breaks the moment the table grows,
    and it breaks LOUDLY here only by luck -- had the count matched, trades
    would have been booked against securitisation trusts and GLEIF
    subsidiaries the bank does not trade with.
    """
    cur.execute(f'SELECT lei FROM "{PG_SCHEMA_V2}".legal_entity '
                "WHERE is_anchor ORDER BY lei")
    return [r[0] for r in cur.fetchall()]


def fetch_fx_closes(cur, pair: str) -> list[tuple[date, float]]:
    cur.execute(
        f'''SELECT obs_date, rate FROM "{PG_SCHEMA_V2}".fx_reference_rate
             WHERE pair = %s ORDER BY obs_date''', (pair,))
    return [(r[0], float(r[1])) for r in cur.fetchall()]


def fetch_rate_coverage(cur) -> set[tuple[str, str]]:
    cur.execute(f'SELECT pair, obs_date::text FROM "{PG_SCHEMA_V2}".fx_reference_rate')
    return {(r[0], r[1]) for r in cur.fetchall()}


# --------------------------------------------------------------------------
# Intraday FX path (Ruling F3)
# --------------------------------------------------------------------------

#: RULING F21 -- FX trades 24 hours; `generators/ticks.py`'s SESSION_TICKS
#: (78 ticks, 13:30-19:55Z) is that instrument's Treasury-par-yield window,
#: not FX's. Reusing it silently confined every engineered break's real
#: local drift to trades executing in that 6.5h afternoon band -- measured,
#: only 228/500 trades fell inside it, so `local_drift_per_s` came back
#: exactly 0.0 for the other 272 and the timing-break population was
#: structurally an afternoon-only slice, letting a consumer separate timing
#: from genuine breaks by HOUR OF DAY ALONE, without ever calling `align()`.
#: FX gets its OWN 24h calendar -- 288 5-minute ticks -- so drift is defined
#: at every execution hour. Anchored exactly as before: opens at the prior
#: published close, terminates at this date's own close.
#: `generators/ticks.py`'s `SESSION_TICKS`/`session_times()` are NOT touched
#: -- that module is correct, already-gated, for the Treasury product.
FX_SESSION_TICKS = 288  # 24h * (60/5) 5-minute ticks


def fx_session_times(day: date) -> list[datetime]:
    """288 UTC timestamps, 5 minutes apart, spanning the full day from
    00:00Z -- FX's own calendar (Ruling F21), independent of
    `generators/ticks.py`'s Treasury-hours `session_times()`."""
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    return [start + timedelta(minutes=5 * i) for i in range(FX_SESSION_TICKS)]


def build_sessions(pairs_dates: set[tuple[str, str]],
                    closes_by_pair: dict[str, list[tuple[date, float]]]
                    ) -> tuple[list[dict], dict[tuple[str, str], tuple[list, list]]]:
    """288-point (24h) sessions for every `(pair, value_date)` actually
    traded (Ruling F21).

    Returns the flat tick rows (for the artifact) and an index
    `{(pair, value_date_iso): (stamps, path)}` for `rate_at` lookups.
    """
    ticks: list[dict] = []
    index: dict[tuple[str, str], tuple[list, list]] = {}

    for pair, vdate_s in sorted(pairs_dates):
        vdate = date.fromisoformat(vdate_s)
        closes = closes_by_pair[pair]
        idx = next((i for i, (d, _) in enumerate(closes) if d == vdate), None)
        if idx is None:
            raise RuntimeError(f"{pair} {vdate}: no fx_reference_rate row at all")
        if idx == 0:
            raise RuntimeError(f"{pair} {vdate}: no PRIOR close to open the session")
        open_v = closes[idx - 1][1]
        close_v = closes[idx][1]

        # Deterministic per (date, pair) — Python's hash() is not, by design,
        # stable across runs, so the discriminator is the pair's fixed index
        # in G10_PAIRS rather than hash(pair).
        seed = int(vdate.strftime("%Y%m%d")) * 1000 + G10_PAIRS.index(pair)
        stamps = fx_session_times(vdate)
        path = brownian_bridge(open_v, close_v, FX_SESSION_TICKS, seed)

        index[(pair, vdate_s)] = (stamps, path)
        for ts, v in zip(stamps, path, strict=True):
            ticks.append({
                "pair": pair, "obs_ts": ts.isoformat(), "value_date": vdate_s,
                "rate": round(v, 6), "provenance": PROVENANCE_ENGINEERED,
            })
    return ticks, index


def rate_at(index: dict[tuple[str, str], tuple[list, list]],
            pair: str, value_date: str, ts: datetime) -> float:
    """Linear-interpolate the intraday path at `ts`; clamp outside the session.

    Clamping (rather than extrapolating) keeps every returned value backed
    by a point the bridge actually produced.
    """
    stamps, path = index[(pair, value_date)]
    if ts <= stamps[0]:
        return path[0]
    if ts >= stamps[-1]:
        return path[-1]
    for i in range(len(stamps) - 1):
        if stamps[i] <= ts <= stamps[i + 1]:
            span = (stamps[i + 1] - stamps[i]).total_seconds()
            frac = (ts - stamps[i]).total_seconds() / span if span else 0.0
            return path[i] + (path[i + 1] - path[i]) * frac
    return path[-1]


def local_drift_per_s(index: dict[tuple[str, str], tuple[list, list]],
                       pair: str, value_date: str, ts: datetime,
                       probe_s: int = 60) -> float:
    """Real per-second drift AT `ts` -- the secant slope between `ts` and
    `ts + probe_s` on the actual intraday bridge (Ruling F13 companion: Task
    13's engineered breaks need a REAL rate of change, not an invented one,
    and a daily close-to-close series cannot express it -- only the
    tick-to-tick path can. `rate_at` clamps outside the session, so this is
    well-defined even right at either edge (it just reads as locally flat
    there)."""
    r0 = rate_at(index, pair, value_date, ts)
    r1 = rate_at(index, pair, value_date, ts + timedelta(seconds=probe_s))
    return (r1 - r0) / probe_s


# --------------------------------------------------------------------------
# Trades
# --------------------------------------------------------------------------

def build_trades(rng: random.Random, pair_mix: dict, hour_mix: dict,
                  leis: list[str]) -> list[dict]:
    trades = []
    for i in range(1, N_TRADES + 1):
        pair = weighted_choice(rng, pair_mix)
        hour = int(weighted_choice(rng, hour_mix))
        minute, second = rng.randint(0, 59), rng.randint(0, 59)
        vdate = rng.choice(VALUE_DATE_POOL)
        execution_ts = datetime(vdate.year, vdate.month, vdate.day,
                                 hour, minute, second, tzinfo=timezone.utc)
        band = weighted_choice(rng, NOTIONAL_BAND_WEIGHTS)
        trades.append({
            "trade_id": f"TRD-W12-{i:04d}",
            "pair": pair,
            "notional_band": band,
            "execution_ts": execution_ts.isoformat(),
            "value_date": vdate.isoformat(),
            "counterparty_lei": rng.choice(leis),
            "provenance": PROVENANCE_INTERNAL,
        })
    return trades


def build_chains_and_records(
    rng: random.Random, trades: list[dict], chain_lengths: dict,
    action_mix: dict, n_rows: int, tick_index: dict,
) -> tuple[list[dict], list[dict], list[str], list[str]]:
    """Amendment chains and per-system observation records.

    `p_chain` and the conditional chain-length draw together reproduce the
    profile's own ratio exactly: P(trade has length-k chain) =
    chain_lengths[k] / n_rows, sampled verbatim (Ruling F19 — no upward
    correction).
    """
    p_chain = sum(chain_lengths.values()) / n_rows
    non_original_mix = {k: v for k, v in action_mix.items() if k != "NEWT"}

    amendments: list[dict] = []
    system_records: list[dict] = []
    chained_ids: list[str] = []
    two_plus_ids: list[str] = []

    for t in trades:
        pair, value_date = t["pair"], t["value_date"]
        vdate = date.fromisoformat(value_date)
        event_ts = datetime.fromisoformat(t["execution_ts"])

        chain_len = 0
        if rng.random() < p_chain:
            chain_len = int(weighted_choice(rng, chain_lengths))
            chained_ids.append(t["trade_id"])
            if chain_len >= 2:
                two_plus_ids.append(t["trade_id"])

        day_end = datetime.combine(vdate, datetime.max.time().replace(microsecond=0),
                                    tzinfo=timezone.utc)

        for seq in range(0, chain_len + 1):
            if seq > 0:
                action_type = weighted_choice(rng, non_original_mix)
                delay_s = rng.randint(300, 20 * 3600)   # 5 min .. 20h later
                event_ts = min(event_ts + timedelta(seconds=delay_s),
                                day_end - timedelta(seconds=1))
                amendments.append({
                    "trade_id": t["trade_id"],
                    "amendment_seq": seq,
                    "action_type": action_type,
                    "event_ts": event_ts.isoformat(),
                    "provenance": PROVENANCE_INTERNAL,
                })

            true_rate = rate_at(tick_index, pair, value_date, event_ts)
            for system_name, offset_s in SYSTEMS.items():
                observed_at = event_ts + timedelta(seconds=offset_s)
                system_records.append({
                    "trade_id": t["trade_id"],
                    "system_name": system_name,
                    "amendment_seq": seq,
                    "observed_at": observed_at.isoformat(),
                    "value_rate": round(true_rate, 6),
                    "provenance": PROVENANCE_INTERNAL,
                })

    return amendments, system_records, chained_ids, two_plus_ids


# --------------------------------------------------------------------------
# Wave 12 Task 13 — the two break populations and the engineered inversion
# --------------------------------------------------------------------------

def enrich_trades_for_breaks(trades: list[dict],
                              tick_index: dict) -> list[dict]:
    """Attach the three fields `narrative_wave12.build_breaks` needs.

    `narrative_wave12` is PURE — no filesystem, no database — so every
    number its mechanism runs on has to arrive already computed. This is
    the one place allowed to touch the intraday tick artifact
    (`tick_index`/`rate_at`), which is where the real per-second drift
    comes from (a daily close-to-close series cannot express it).
    """
    enriched = []
    for t in trades:
        pair, value_date = t["pair"], t["value_date"]
        ts = datetime.fromisoformat(t["execution_ts"])
        enriched.append({
            "trade_id": t["trade_id"],
            "pair": pair,
            "execution_ts": ts,
            "anchor_rate": rate_at(tick_index, pair, value_date, ts),
            "local_drift_per_s": local_drift_per_s(tick_index, pair, value_date, ts),
        })
    return enriched


def apply_break_overrides(system_records: list[dict], breaks: list[dict]) -> int:
    """RULING F24 -- the engineered break's own values must actually be the
    values `system_trade_record`'s two involved systems carry, or neither
    Postgres nor Fluree holds any trace of the discrepancy
    `break_record.raw_variance` claims.

    `build_chains_and_records()` computes ONE shared `true_rate` per
    `(trade_id, amendment_seq)`, evaluated at ONE `event_ts`, and gives it
    to all three systems -- correct for the baseline population, where
    (module docstring) "every system observes the SAME true market moment
    ... so their value_rate values agree; only their recorded observed_at
    differs." `build_breaks()` (Task 13) then constructs, on top of that,
    a SEPARATE true observation instant and value for the two systems an
    engineered break actually names -- but those numbers previously lived
    ONLY inside the break dict. Per RULING F22 only `raw_variance` (a
    single pip count, not a per-system value) and `designed_class` ever
    reach Postgres `break_record`, and nothing about them reaches Fluree at
    all. Measured before this fix: `system_trade_record` showed all three
    systems agreeing to 6 decimal places on EVERY trade, breaking or not
    (e.g. TRD-W12-0417's trading/settlement/risk all read 1.392039). A
    validator reading only Postgres values and Fluree timestamps -- which
    is what Task 15's gate is required to do -- would then recompute a raw
    difference of exactly zero for all 60 breaks, and neither the
    inversion nor the survivor claim could ever be established by
    recomputation.

    This overrides, at amendment_seq 0 (breaks are always constructed
    against a trade's ORIGINAL booking, never an amendment -- `build_breaks`
    never references `amendment_seq`), the `value_rate` and `observed_at`
    of exactly the two systems each break names, to the break's own
    `raw_a`/`raw_b` and `observed_a`/`observed_b`. The third, uninvolved
    system is left untouched -- it was never part of the constructed
    discrepancy, and overriding it would invent a second, unintended break.
    Idempotent: keyed by `(trade_id, system_name)`, deterministic from the
    same seeded `breaks`, so a re-run applies the identical override.
    """
    override: dict[tuple[str, str], tuple[float, str]] = {}
    for b in breaks:
        override[(b["trade_id"], b["system_a"])] = (b["raw_a"], b["observed_a"])
        override[(b["trade_id"], b["system_b"])] = (b["raw_b"], b["observed_b"])

    applied = 0
    for r in system_records:
        if r["amendment_seq"] != 0:
            continue
        key = (r["trade_id"], r["system_name"])
        if key in override:
            value_rate, observed_at = override[key]
            r["value_rate"] = round(value_rate, 6)
            r["observed_at"] = observed_at
            applied += 1
    return applied


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc, currency_note = verify_current(PROFILE_NAME)
    print(f"  artifact currency: {currency_note}")

    pair_mix, hour_mix = doc["pair_mix"], doc["hour_mix"]
    action_mix, chain_lengths = doc["action_mix"], doc["chain_lengths"]
    n_rows = doc["n_rows"]

    rng = random.Random(SEED)

    with pg_connect() as conn, conn.cursor() as cur:
        leis = fetch_counterparty_leis(cur)
        if len(leis) != 50:
            print(f"FAIL: expected 50 legal_entity anchors, found {len(leis)}",
                  file=sys.stderr)
            return 1
        closes_by_pair = {pair: fetch_fx_closes(cur, pair) for pair in G10_PAIRS}
        rate_coverage = fetch_rate_coverage(cur)

    trades = build_trades(rng, pair_mix, hour_mix, leis)

    pairs_dates = {(t["pair"], t["value_date"]) for t in trades}
    ticks, tick_index = build_sessions(pairs_dates, closes_by_pair)

    amendments, system_records, chained_ids, two_plus_ids = build_chains_and_records(
        rng, trades, chain_lengths, action_mix, n_rows, tick_index)

    clock_offsets = [
        {"system_name": name, "offset_s": offset, "provenance": PROVENANCE_INTERNAL}
        for name, offset in SYSTEMS.items()
    ]

    # ---- Task 13: engineered break populations and the inversion ---------
    # A DEDICATED rng, seeded but separate from `rng` above, so adding this
    # population cannot shift a single draw the existing trades/amendments/
    # system_records depend on (Idempotency — CLAUDE.md — this reload must
    # reproduce every row already committed, unchanged).
    break_rng = random.Random(SEED + 13)
    enriched_trades = enrich_trades_for_breaks(trades, tick_index)
    breaks = build_breaks(enriched_trades, break_rng)
    materiality_thresholds = [
        {"intent": intent, "threshold_pips": threshold, "provenance": PROVENANCE_INTERNAL}
        for intent, threshold in MATERIALITY.items()
    ]

    # RULING F24 -- see apply_break_overrides()'s docstring. Without this,
    # system_trade_record and Fluree's ex:systemObservedAt carry the
    # baseline (no-discrepancy) population for every trade, breaking or
    # not, and Task 15's validator -- required to recompute break variance
    # from those two stores alone -- would find every raw difference to be
    # exactly zero.
    n_overridden = apply_break_overrides(system_records, breaks)
    expected_overrides = 2 * len(breaks)
    if n_overridden != expected_overrides:
        print(f"FAIL: applied {n_overridden} break-value overrides to "
              f"system_records, expected {expected_overrides} (2 systems "
              f"x {len(breaks)} breaks)", file=sys.stderr)
        return 1

    # ---- rate coverage: checked HERE, not left for a validator (§F) -------
    needed = {(t["pair"], t["value_date"]) for t in trades}
    missing = needed - rate_coverage
    if missing:
        print(f"FAIL: {len(missing)} (pair, value_date) combo(s) have no "
              f"fx_reference_rate row: {sorted(missing)[:10]}", file=sys.stderr)
        return 1
    coverage_note = (f"rate coverage: {len(needed)} (pair, value_date) combos, "
                      f"missing a rate: {len(missing)}")

    # ---- reporting ----------------------------------------------------
    gen_pair_counts = Counter(t["pair"] for t in trades)
    obs_total = sum(pair_mix.values())
    print("\n  pair mix — generated vs observed (proportions):")
    for pair in sorted(pair_mix):
        gen_p = gen_pair_counts.get(pair, 0) / len(trades)
        obs_p = pair_mix[pair] / obs_total
        print(f"    {pair:8} generated {gen_p:6.3f}   observed {obs_p:6.3f}")

    gen_chain_hist = Counter()
    chain_len_by_trade = Counter()
    for a in amendments:
        chain_len_by_trade[a["trade_id"]] = max(chain_len_by_trade[a["trade_id"]], a["amendment_seq"])
    for trade_id, length in chain_len_by_trade.items():
        gen_chain_hist[str(length)] += 1

    print("\n  chain-length histogram — generated vs observed (proportions):")
    all_keys = sorted(set(chain_lengths) | set(gen_chain_hist), key=int)
    for k in all_keys:
        gen_p = gen_chain_hist.get(k, 0) / len(trades)
        obs_p = chain_lengths.get(k, 0) / n_rows
        print(f"    length {k:>3}  generated {gen_p:7.4f} ({gen_chain_hist.get(k, 0):3d})"
              f"   observed {obs_p:7.4f} ({chain_lengths.get(k, 0)})")

    n_chained = len(chained_ids)
    n_two_plus = len(two_plus_ids)
    print(f"\n  trades with chains: {n_chained} (floor 10)")
    print(f"  trades with 2+ amendments: {n_two_plus} (floor 3)")
    print(f"  {coverage_note}")
    print(f"  {len(ticks)} intraday tick rows across {len(pairs_dates)} (pair, value_date) sessions")
    print(f"  {len(system_records)} system_trade_record rows, {len(amendments)} amendment rows")

    if n_chained < 10:
        print(f"FAIL: only {n_chained} chained trades; need >= 10", file=sys.stderr)
        return 1
    if n_two_plus < 3:
        print(f"FAIL: only {n_two_plus} trades with 2+ amendments; need >= 3", file=sys.stderr)
        return 1

    # ---- Task 13 reporting: the break mix and the two named cases ---------
    n_timing = sum(1 for b in breaks if b["break_type"] == "timing")
    n_genuine = sum(1 for b in breaks if b["break_type"] == "genuine")
    print(f"\n  breaks: {len(breaks)} total — {n_timing} timing-attributable, "
          f"{n_genuine} genuine (target ~60, ~2/3 timing)")
    print(f"  RULING F24: {n_overridden} system_trade_record rows overridden "
          f"with each break's own value/observed_at "
          f"(expected {expected_overrides} = 2 systems x {len(breaks)} breaks)")

    by_trade_id = {b["trade_id"]: b for b in breaks}
    inversion = by_trade_id.get(INVERSION_TRADE_ID)
    survivor = by_trade_id.get(SURVIVOR_TRADE_ID)
    if inversion is None or survivor is None:
        print("FAIL: named inversion/survivor case missing from build_breaks() "
              "output", file=sys.stderr)
        return 1
    if not (inversion["classification_raw"] == "genuine"
            and inversion["classification_aligned"] == "within-tolerance"):
        print(f"FAIL: {INVERSION_TRADE_ID} did not invert — raw="
              f"{inversion['classification_raw']} aligned="
              f"{inversion['classification_aligned']}", file=sys.stderr)
        return 1
    if not (survivor["classification_raw"] == "genuine"
            and survivor["classification_aligned"] == "genuine"):
        print(f"FAIL: {SURVIVOR_TRADE_ID} did not survive alignment — raw="
              f"{survivor['classification_raw']} aligned="
              f"{survivor['classification_aligned']}", file=sys.stderr)
        return 1

    print(f"\n  INVERSION CASE {INVERSION_TRADE_ID} ({inversion['pair']}, "
          f"{inversion['system_a']} vs {inversion['system_b']}):")
    print(f"    raw:     {inversion['raw_a']} vs {inversion['raw_b']}  "
          f"-> {inversion['raw_diff_pips']} pips  -> {inversion['classification_raw']}")
    print(f"    aligned: {inversion['aligned_a']} vs {inversion['aligned_b']}  "
          f"-> {inversion['aligned_diff_pips']} pips  -> {inversion['classification_aligned']}")
    print(f"    materiality: {inversion['materiality_pips']} pips ({inversion['intent']})")

    print(f"\n  SURVIVOR CASE {SURVIVOR_TRADE_ID} ({survivor['pair']}, "
          f"{survivor['system_a']} vs {survivor['system_b']}):")
    print(f"    raw:     {survivor['raw_a']} vs {survivor['raw_b']}  "
          f"-> {survivor['raw_diff_pips']} pips  -> {survivor['classification_raw']}")
    print(f"    aligned: {survivor['aligned_a']} vs {survivor['aligned_b']}  "
          f"-> {survivor['aligned_diff_pips']} pips  -> {survivor['classification_aligned']}")
    print(f"    materiality: {survivor['materiality_pips']} pips ({survivor['intent']})")

    if args.dry_run:
        print("\n  --dry-run: not written")
        return 0

    artifact = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "seed": SEED,
            "trade_count": len(trades),
            "chained_trades": n_chained,
            "two_plus_amendment_trades": n_two_plus,
            "value_date_pool": [d.isoformat() for d in VALUE_DATE_POOL],
            "note": ("Pair mix, execution-hour mix, action mix, and chain "
                     "lengths are sampled from wave12_part43_profile.json "
                     "verbatim (Ruling F19 — no upward correction for the "
                     "midnight-crossing undercount). notional_band is "
                     "engineered — Part 43 bands/caps real notional so "
                     "there is nothing to sample."),
            "break_count": len(breaks),
            "timing_breaks": n_timing,
            "genuine_breaks": n_genuine,
            "inversion_trade_id": INVERSION_TRADE_ID,
            "survivor_trade_id": SURVIVOR_TRADE_ID,
            "break_value_overrides": n_overridden,
        },
        "_inputs": record_inputs(PROFILE_NAME),
        "clock_offsets": clock_offsets,
        "trades": trades,
        "system_records": system_records,
        "amendments": amendments,
        "breaks": breaks,
        "materiality_thresholds": materiality_thresholds,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=1))
    print(f"\n  wrote {OUT.relative_to(Path.cwd())}")

    ticks_artifact = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "seed": SEED,
            "sessions": len(pairs_dates),
            "session_ticks": FX_SESSION_TICKS,
            "anchor_source": "ccf_v2.fx_reference_rate (FRED, public)",
            "note": ("Ruling F3. Endpoints are real published fx_reference_rate "
                     "closes; only the within-day path is engineered. Anchored "
                     "exactly as generators/generate_ticks.py anchors the "
                     "Treasury curve — see this module's docstring."),
        },
        "_inputs": record_inputs(),
        "ticks": ticks,
    }
    OUT_TICKS.write_text(json.dumps(ticks_artifact, indent=1))
    print(f"  wrote {OUT_TICKS.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
