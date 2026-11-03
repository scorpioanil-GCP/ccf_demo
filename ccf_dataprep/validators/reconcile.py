#!/usr/bin/env python3
"""Wave 12's FX gate -- `markets.fx-reconciliation.v1`, design §6.2.

The product's whole argument: two internal systems report different values
for the same FX trade. Compared naively, the difference exceeds a
materiality threshold and looks like a genuine booking error. But each
system observed the trade at a different TRUE instant, with a different
recorded clock offset, against a rate that was still drifting. Project each
system's reading to a common as-of point using its recorded offset and the
local drift, and a timing-attributable difference collapses to nothing --
while a real error survives untouched.

## The split is the point (ruling F23) -- and it is genuinely load-bearing

  Postgres  `fx_trade`, `system_trade_record` (each system's VALUE -- it no
            longer carries a timestamp), `break_record`, `materiality_threshold`,
            `fx_pip_size`, `fx_intraday_tick` (the per-second drift, ruling
            F3 -- a daily series cannot express it), `fx_reference_rate`.
  Fluree    each system's observation timestamp (`ex:systemObservedAt`) and
            its clock offset (`ex:clockOffsetSeconds`), plus the amendment
            chain (`ex:amendmentSeq` on `amd-*` nodes, chained via `ex:amends`).

Temporal Traversal reads observations from Fluree; Batch Enrich reads values
from Postgres (design §D steps 3/4). This file queries BOTH, every run --
a version that could run against Postgres alone would be evidence the
partition had collapsed, so `fetch_fluree()` is never optional.

## The rule that makes this a gate, not a report

`break_record.designed_class` is the answer key. It is read ONLY inside
`disagreement_report()`, to count where the recomputation disagrees with
what the generator designed. Every PASS/FAIL claim below is computed from
`system_trade_record` values, `ex:systemObservedAt` + `ex:clockOffsetSeconds`
(Fluree), the local drift (adjacent `fx_intraday_tick` rows), and the pip
size for the pair -- never from `designed_class` or `raw_variance`.

## RULING F24 -- why this gate is even possible to write

Before this branch's fix (`generators/generate_fx_trades.py`,
`apply_break_overrides`), `system_trade_record.value_rate` was IDENTICAL
across all three systems for every trade, breaking or not -- the engineered
break's per-system values lived only inside the artifact's `breaks` list,
which per ruling F22 contributes only `raw_variance` (a single pip count)
and `designed_class` to Postgres, and nothing at all to Fluree. A validator
reading only Postgres values and Fluree timestamps would have recomputed a
raw difference of exactly zero for all 60 breaks -- the inversion and
survivor claims could never have been established by recomputation. See
that function's docstring for the full account; `docs/ccf_dataprep_v2.md`
records it as ruling F24.

## Ruling F25 -- the offset is a real but secondary input; test it as one

Measured (coordinator, fix round 1): the clock-offset spread (159s) is a
median 11.9% of the true observation gap (458.7s) the alignment mechanism
corrects. Zeroing offsets alone therefore leaves most timing breaks flipped
by the dominant observation-time gap regardless -- not a defect in the data
(design §A: trading/settlement/risk genuinely observe at different real
MOMENTS, not merely with different clock error) and not fixed by enlarging
the offsets, which would make the dataset less faithful to make a test fail.
Two responses, both to the GATE:

  - `claim_offset_live` below (the "Offset input is live" claim) proves the
    offset is not a dead input: alignment computed WITH the recorded offset
    differs measurably from alignment that ignores it, on >=1 break, purely
    by comparing two in-memory computations -- no data mutated.
  - The decisive inversion mutation (see the report) collapses the TRUE
    observation instant itself (`obs_x - offset_x`) to a single point for
    the two systems in a break, leaving offsets untouched. With no gap left
    to explain, alignment is a no-op and the inversion claim must fail --
    this is the test that actually exercises what design §3.4 claims.

## Pip scaling (ruling F13) -- reimplemented, not imported

A pip is `0.01` for JPY pairs and `0.0001` for the other five
(`fx_pip_size`, read live, never hardcoded). Every comparison in this file
converts to pips before comparing to a threshold, so a USD/JPY break and a
EUR/USD break of the same pip size classify identically -- `claim_pip_scaling`
proves this operationally, not by code inspection.

## Independent reimplementation of `rate_at` / drift

Mirrors `generators/generate_fx_trades.py`'s `rate_at` and
`local_drift_per_s` (piecewise-linear interpolation over the tick path,
clamped at the session edges, secant probe for drift) but is written fresh
here, against `fx_intraday_tick` rows fetched from Postgres -- the same
house rule `validators/intraday.py` states: a bug in the generator's
arithmetic must not be able to hide by being reused in its own gate.

    uv run validators/reconcile.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf import fluree                                                  # noqa: E402
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, pg_connect   # noqa: E402

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2

#: `break_record` carries no `intent` column (RULING F22 -- exactly seven
#: fields), and `generators/narrative_wave12.py`'s `build_breaks()` never
#: varies `_DEFAULT_INTENT` across the population it builds -- every one of
#: the 60 loaded breaks was constructed against this one intent. Recorded
#: here as a named constant (never a bare "2.0") and used only to SELECT
#: which `materiality_threshold` row to read -- the threshold VALUE itself
#: always comes from Postgres.
DEFAULT_INTENT = "break-investigation"

#: Matches `generate_fx_trades.py`'s `local_drift_per_s(..., probe_s=60)`.
DRIFT_PROBE_S = 60

#: RULING F26. Before the fix, `timing_attributable` was derived from the
#: two numbers closure then compared it against -- an algebraic identity,
#: exactly zero for every input, so 1e-6 (and even 1e-9) always passed.
#: With `timing_attributable` recomputed independently (rate drift across
#: the true observation gap), closure is a genuine cross-check: because
#: `pips()` takes an absolute value, `|timing| + |residual|` generally
#: differs from `|raw|` by up to `2*min(|timing|, |raw|)` (reverse
#: triangle inequality) whenever alignment reverses the sign of the
#: value difference -- exactly the inversion cases this gate exists to
#: catch. Measured against the 60 loaded breaks (coordinator, this fix):
#: min 0.0, median ~3.9e-13 (float noise, the 20 non-inverting breaks),
#: max 0.0378 pips (16 of 60 above 1e-6; 5 above 0.01). All are inversion
#: or near-inversion breaks -- the sign flip the gate is meant to see,
#: not a defect. 0.1 pips is chosen as the gating tolerance: >2.6x the
#: observed max, and 5% of the 2.0-pip materiality threshold, so a real
#: dropped observation (which perturbs the true gap by seconds-to-minutes
#: of drift, orders of magnitude larger) still fails it. 1e-6 is kept as
#: an informational tighter tier, reported but not gating.
CLOSURE_TOL = 0.1
CLOSURE_TOL_TIGHT = 1e-6

results: list[tuple[bool, str]] = []


def claim(ok: bool, msg: str) -> None:
    results.append((ok, msg))
    print(f"  {'PASS' if ok else 'FAIL'}  {msg}")


def bindings(sparql: str) -> list[dict]:
    return fluree.query(sparql, ledger=L).get("results", {}).get("bindings", [])


# --------------------------------------------------------------------------
# Postgres reads
# --------------------------------------------------------------------------

def fetch_postgres(cur):
    cur.execute(f'SELECT trade_id, pair, value_date, execution_ts '
                f'FROM "{S}".fx_trade')
    trades = {r[0]: {"pair": r[1], "value_date": r[2], "execution_ts": r[3]}
              for r in cur.fetchall()}

    cur.execute(f'SELECT trade_id, system_name, amendment_seq, value_rate '
                f'FROM "{S}".system_trade_record')
    values: dict[tuple[str, str, int], float] = {}
    for trade_id, system_name, seq, value_rate in cur.fetchall():
        values[(trade_id, system_name, seq)] = float(value_rate)

    # Wave 12 close-out (docs/known-issues.md §12, deferred-minors table):
    # `raw_variance` used to be fetched into a `designed_raw_variance` dict
    # key that no claim in this file read -- only `designed_class` is
    # consulted, deliberately, inside `disagreement_report()`. Dropped from
    # both the query and the dict; `raw_variance` stays in `break_record`
    # (Postgres, RULING F22's named answer-key exception), just not carried
    # into this file's in-memory rows unread.
    cur.execute(f'SELECT break_id, trade_id, system_a, system_b, '
                f'designed_class FROM "{S}".break_record')
    break_rows = [
        {"break_id": r[0], "trade_id": r[1], "system_a": r[2], "system_b": r[3],
         "designed_class": r[4]}
        for r in cur.fetchall()
    ]

    cur.execute(f'SELECT intent, threshold_pips FROM "{S}".materiality_threshold')
    thresholds = {r[0]: float(r[1]) for r in cur.fetchall()}

    cur.execute(f'SELECT pair, pip_size FROM "{S}".fx_pip_size')
    pip_sizes = {r[0]: float(r[1]) for r in cur.fetchall()}

    cur.execute(f'SELECT pair, obs_ts, rate FROM "{S}".fx_intraday_tick '
                f'ORDER BY pair, obs_ts')
    ticks_by_pair: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for pair, obs_ts, rate in cur.fetchall():
        ticks_by_pair[pair].append((obs_ts, float(rate)))

    cur.execute(f'SELECT DISTINCT pair, value_date FROM "{S}".fx_trade')
    trade_pair_dates = {(r[0], r[1]) for r in cur.fetchall()}

    cur.execute(f'SELECT pair, obs_date FROM "{S}".fx_reference_rate')
    rate_coverage = {(r[0], r[1]) for r in cur.fetchall()}

    return (trades, values, break_rows, thresholds, pip_sizes, ticks_by_pair,
            trade_pair_dates, rate_coverage)


# --------------------------------------------------------------------------
# Fluree reads -- observation timestamps, clock offsets, amendment chain
# --------------------------------------------------------------------------

def fetch_fluree():
    """Per RULING F23: `ex:systemObservedAt` and `ex:clockOffsetSeconds`
    live ONLY in Fluree. Queried live, `FROM <{L}>` explicit, every run."""

    observed_at: dict[tuple[str, str, int], datetime] = {}
    for b in bindings(f'SELECT ?s ?o FROM <{L}> '
                       f'WHERE {{ ?s <{EX}systemObservedAt> ?o }}'):
        local = b["s"]["value"][len(EX):]        # "obs-TRD-W12-0417-trading-0"
        assert local.startswith("obs-"), local
        rest, seq_s = local[len("obs-"):].rsplit("-", 1)
        trade_id, system_name = rest.rsplit("-", 1)
        observed_at[(trade_id, system_name, int(seq_s))] = \
            datetime.fromisoformat(b["o"]["value"])

    offsets: dict[str, int] = {}
    for b in bindings(f'SELECT ?s ?o FROM <{L}> '
                       f'WHERE {{ ?s <{EX}clockOffsetSeconds> ?o }}'):
        local = b["s"]["value"][len(EX):]        # "sys-trading"
        assert local.startswith("sys-"), local
        offsets[local[len("sys-"):]] = int(b["o"]["value"])

    # Amendment nodes ALSO carry `ex:amendmentSeq` -- so does every
    # observation node (see load_fluree_wave12_fx.py's `build()`). Filter
    # to the `amd-` prefix so this doesn't double-count the 1,815
    # observation nodes as amendments.
    chain_len: dict[str, int] = defaultdict(int)
    for b in bindings(f'SELECT ?s ?o FROM <{L}> '
                       f'WHERE {{ ?s <{EX}amendmentSeq> ?o }}'):
        local = b["s"]["value"][len(EX):]
        if not local.startswith("amd-"):
            continue
        trade_id, seq_s = local[len("amd-"):].rsplit("-", 1)
        chain_len[trade_id] = max(chain_len[trade_id], int(seq_s))

    return observed_at, offsets, chain_len


# --------------------------------------------------------------------------
# Independent rate-path reimplementation (see module docstring)
# --------------------------------------------------------------------------

def rate_at(ticks: list[tuple[datetime, float]], ts: datetime) -> float:
    if ts <= ticks[0][0]:
        return ticks[0][1]
    if ts >= ticks[-1][0]:
        return ticks[-1][1]
    for i in range(len(ticks) - 1):
        t0, v0 = ticks[i]
        t1, v1 = ticks[i + 1]
        if t0 <= ts <= t1:
            span = (t1 - t0).total_seconds()
            frac = (ts - t0).total_seconds() / span if span else 0.0
            return v0 + (v1 - v0) * frac
    return ticks[-1][1]


def drift_at(ticks: list[tuple[datetime, float]], ts: datetime,
             probe_s: int = DRIFT_PROBE_S) -> float:
    r0 = rate_at(ticks, ts)
    r1 = rate_at(ticks, ts + timedelta(seconds=probe_s))
    return (r1 - r0) / probe_s


def pips(pip_sizes: dict[str, float], pair: str, rate_difference: float) -> float:
    return abs(rate_difference) / pip_sizes[pair]


def classify(pip_sizes: dict[str, float], pair: str, threshold_pips: float,
             a: float, b: float) -> str:
    """'genuine' if the pip-normalised difference exceeds materiality,
    'timing' if alignment (or the raw comparison, for an unbroken pair)
    leaves it inside tolerance."""
    return "genuine" if pips(pip_sizes, pair, a - b) > threshold_pips else "timing"


# --------------------------------------------------------------------------
# Per-break recomputation -- the whole gate
# --------------------------------------------------------------------------

def recompute(b: dict, trades: dict, values: dict, observed_at: dict,
              offsets: dict, ticks_by_pair: dict, pip_sizes: dict,
              threshold_pips: float) -> dict:
    trade_id, sys_a, sys_b = b["trade_id"], b["system_a"], b["system_b"]
    trade = trades.get(trade_id)
    if trade is None:
        return {"ok": False, "reason": f"{trade_id} not in fx_trade"}
    pair = trade["pair"]

    value_a = values.get((trade_id, sys_a, 0))
    value_b = values.get((trade_id, sys_b, 0))
    if value_a is None or value_b is None:
        return {"ok": False, "reason": "missing system_trade_record value"}

    raw_diff_pips = pips(pip_sizes, pair, value_a - value_b)
    raw_class = classify(pip_sizes, pair, threshold_pips, value_a, value_b)

    obs_a = observed_at.get((trade_id, sys_a, 0))
    obs_b = observed_at.get((trade_id, sys_b, 0))
    off_a = offsets.get(sys_a)
    off_b = offsets.get(sys_b)
    if obs_a is None or obs_b is None or off_a is None or off_b is None:
        return {"ok": False, "reason": "missing Fluree observation/offset",
                "raw_diff_pips": raw_diff_pips, "raw_class": raw_class}

    true_a = obs_a - timedelta(seconds=off_a)
    true_b = obs_b - timedelta(seconds=off_b)
    as_of = max(true_a, true_b)

    ticks = ticks_by_pair.get(pair)
    if not ticks:
        return {"ok": False, "reason": f"no fx_intraday_tick rows for {pair}",
                "raw_diff_pips": raw_diff_pips, "raw_class": raw_class}
    drift = drift_at(ticks, trade["execution_ts"])

    aligned_a = value_a + drift * (as_of - true_a).total_seconds()
    aligned_b = value_b + drift * (as_of - true_b).total_seconds()
    aligned_diff_pips = pips(pip_sizes, pair, aligned_a - aligned_b)
    aligned_class = classify(pip_sizes, pair, threshold_pips, aligned_a, aligned_b)

    # RULING F26 -- `timing_attributable` used to be DERIVED as
    # `raw_diff_pips - aligned_diff_pips`, the two numbers closure then
    # compared it against. That is `((raw - aligned) + aligned) - raw`,
    # identically zero for every input; no mutation could ever fail it.
    # Recomputed here INDEPENDENTLY from the mechanism -- the rate drift
    # across the true observation gap (same drift already obtained from
    # adjacent fx_intraday_tick rows, same true instants used to build
    # `aligned_a`/`aligned_b` above) -- so closure is now a genuine
    # cross-check between two separately-derived quantities. Because
    # `pips()` takes an absolute value, this is NOT an algebraic identity:
    # |raw_diff| generally differs from |timing| + |residual| unless the
    # timing effect and the residual point the same direction (triangle
    # inequality).
    #
    # WHAT THIS CATCHES, stated correctly. An earlier version of this comment
    # claimed a break whose observation time was "dropped from the alignment --
    # collapsing the true gap to zero" would fail here. That is FALSE, and it
    # was disproved against the live data at Wave 12's final review: with
    # `true_a == true_b` the timing term is drift x 0 = 0, and both values
    # project to `as_of` from the same instant so `aligned_diff == raw_diff`.
    # The gap is then exactly 0 on all 60 breaks and this check PASSES. That
    # case is caught by the Inversion claim, not by closure.
    #
    # What closure actually catches is an INCONSISTENCY BETWEEN THE TWO PATHS:
    # `timing_attributable` is derived from the drift and the true observation
    # instants, while `residual` comes from the alignment arithmetic. If an
    # offset is applied in one path and not the other, or a timestamp differs
    # between them, the two disagree and the gap opens. Measured at the final
    # review by mutating the fetched observation map: 8.97 pips when one
    # system's instant is replaced by another's, 129.8 pips under a 30-minute
    # shift -- against a 0.1 tolerance.
    timing_attributable = pips(pip_sizes, pair,
                                drift * (true_b - true_a).total_seconds())
    residual = aligned_diff_pips
    closure_gap = abs((timing_attributable + residual) - raw_diff_pips)

    # RULING F25, item 2 -- "offset live" claim support. Recompute alignment
    # a SECOND way, treating each system's recorded offset as 0 (i.e. using
    # the RAW recorded ex:systemObservedAt as if it were the true instant,
    # never touching stored data). If this agrees with the real alignment,
    # the offset term is not actually influencing the result -- it would be
    # a secondary input the gate cannot tell was applied. Fluree's actual
    # `ex:clockOffsetSeconds` is never used to build this branch.
    as_of_no_off = max(obs_a, obs_b)
    aligned_a_no_off = value_a + drift * (as_of_no_off - obs_a).total_seconds()
    aligned_b_no_off = value_b + drift * (as_of_no_off - obs_b).total_seconds()
    aligned_diff_pips_no_off = pips(pip_sizes, pair, aligned_a_no_off - aligned_b_no_off)
    offset_effect_pips = abs(aligned_diff_pips - aligned_diff_pips_no_off)

    return {
        "ok": True, "pair": pair,
        "raw_diff_pips": raw_diff_pips, "raw_class": raw_class,
        "aligned_diff_pips": aligned_diff_pips, "aligned_class": aligned_class,
        "timing_attributable": timing_attributable, "residual": residual,
        "closure_gap": closure_gap,
        "aligned_diff_pips_no_off": aligned_diff_pips_no_off,
        "offset_effect_pips": offset_effect_pips,
    }


def main() -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        (trades, values, break_rows, thresholds, pip_sizes, ticks_by_pair,
         trade_pair_dates, rate_coverage) = fetch_postgres(cur)

    observed_at, offsets, chain_len = fetch_fluree()

    print(f"  loaded: {len(trades)} trades, {len(values)} system_trade_record "
          f"values, {len(break_rows)} breaks (Postgres)")
    print(f"          {len(observed_at)} systemObservedAt, {len(offsets)} "
          f"clockOffsetSeconds, {len(chain_len)} amendment chains (Fluree)")

    if DEFAULT_INTENT not in thresholds:
        print(f"FAIL: no materiality_threshold row for intent="
              f"{DEFAULT_INTENT!r}", file=sys.stderr)
        return 1
    threshold_pips = thresholds[DEFAULT_INTENT]
    print(f"  materiality: {threshold_pips} pips ({DEFAULT_INTENT})\n")

    recomputed = []
    for b in break_rows:
        r = recompute(b, trades, values, observed_at, offsets, ticks_by_pair,
                      pip_sizes, threshold_pips)
        r["break_id"] = b["break_id"]
        r["trade_id"] = b["trade_id"]
        r["designed_class"] = b["designed_class"]
        recomputed.append(r)

    ok_rows = [r for r in recomputed if r["ok"]]
    claim(len(ok_rows) == len(recomputed) and len(recomputed) > 0,
          f"every loaded break recomputes from Postgres values + Fluree "
          f"observation/offset data ({len(recomputed) - len(ok_rows)} of "
          f"{len(recomputed)} could not)")
    for r in recomputed:
        if not r["ok"]:
            print(f"          {r['trade_id']} ({r['break_id']}): {r['reason']}")

    # --- Inversion ----------------------------------------------------------
    inversions = [r for r in ok_rows
                  if r["raw_class"] == "genuine" and r["aligned_class"] == "timing"]
    claim(len(inversions) >= 1,
          f">=1 break classifies genuine on raw values, timing once aligned "
          f"-- both recomputed ({len(inversions)} found)")
    for r in inversions[:5]:
        print(f"          {r['trade_id']} ({r['break_id']}, {r['pair']}): "
              f"raw {r['raw_diff_pips']:.4f} pips ({r['raw_class']}) -> "
              f"aligned {r['aligned_diff_pips']:.4f} pips ({r['aligned_class']})")

    # --- Survivor -------------------------------------------------------------
    survivors = [r for r in ok_rows
                 if r["raw_class"] == "genuine" and r["aligned_class"] == "genuine"]
    claim(len(survivors) >= 1,
          f">=1 break classifies genuine under BOTH comparisons "
          f"({len(survivors)} found)")
    for r in survivors[:5]:
        print(f"          {r['trade_id']} ({r['break_id']}, {r['pair']}): "
              f"raw {r['raw_diff_pips']:.4f} pips -> "
              f"aligned {r['aligned_diff_pips']:.4f} pips (both genuine)")

    # --- Decomposition closure ------------------------------------------------
    bad_closure = [r for r in ok_rows if r["closure_gap"] > CLOSURE_TOL]
    bad_closure_tight = [r for r in ok_rows if r["closure_gap"] > CLOSURE_TOL_TIGHT]
    all_computable = len(ok_rows) == len(recomputed)
    claim(not bad_closure and all_computable,
          f"timing-attributable + residual == total, within {CLOSURE_TOL}, "
          f"on all {len(recomputed)} breaks ({len(bad_closure)} gaps over "
          f"tolerance, {len(recomputed) - len(ok_rows)} uncomputable)")
    print(f"          (at the tighter {CLOSURE_TOL_TIGHT}: "
          f"{len(bad_closure_tight)} gaps over tolerance)")

    # --- Break mix --------------------------------------------------------
    n_timing = sum(1 for r in ok_rows if r["aligned_class"] == "timing")
    n_genuine = sum(1 for r in ok_rows if r["aligned_class"] == "genuine")
    total = len(ok_rows)
    frac_timing = n_timing / total if total else 0.0
    claim(50 <= total <= 70 and 0.55 <= frac_timing <= 0.78,
          f"~2/3 timing / ~1/3 genuine across ~60 breaks, recomputed "
          f"({n_timing} timing / {n_genuine} genuine of {total}, "
          f"{frac_timing:.1%} timing)")

    # --- Pip scaling ------------------------------------------------------
    if "USD/JPY" not in pip_sizes or "EUR/USD" not in pip_sizes:
        claim(False, "pip scaling check needs both USD/JPY and EUR/USD in "
                      "fx_pip_size")
    else:
        jpy_pip, nonjpy_pip = pip_sizes["USD/JPY"], pip_sizes["EUR/USD"]
        same_pip_count = threshold_pips + 3.0   # comfortably over materiality
        diff_jpy = same_pip_count * jpy_pip
        diff_nonjpy = same_pip_count * nonjpy_pip
        class_jpy = classify(pip_sizes, "USD/JPY", threshold_pips,
                              100.0 + diff_jpy, 100.0)
        class_nonjpy = classify(pip_sizes, "EUR/USD", threshold_pips,
                                 1.0 + diff_nonjpy, 1.0)
        claim(jpy_pip != nonjpy_pip and class_jpy == class_nonjpy == "genuine",
              f"a USD/JPY and a EUR/USD break of the same "
              f"{same_pip_count:g} pips classify identically "
              f"({class_jpy} / {class_nonjpy}) despite raw magnitudes "
              f"{diff_jpy:.4f} vs {diff_nonjpy:.6f} (pip sizes {jpy_pip} vs "
              f"{nonjpy_pip}, read from fx_pip_size, never hardcoded)")
        pairs_present = {r["pair"] for r in ok_rows}
        print(f"          pairs actually present among the {total} loaded "
              f"breaks: {sorted(pairs_present)}")
        claim("USD/JPY" in pairs_present and
              any(p != "USD/JPY" for p in pairs_present),
              "the loaded break population itself spans a JPY pair and a "
              "non-JPY pair (not just the synthetic cross-check above)")

    # --- Offset input is live (ruling F25 item 2) ---------------------------
    # A secondary term the gate never exercises is a term the gate cannot
    # tell was applied. Proves the recorded ex:clockOffsetSeconds actually
    # changes the aligned result on at least one break -- computed purely in
    # memory (see recompute()'s `_no_off` branch), no data mutated.
    OFFSET_LIVE_MIN_PIPS = 0.05
    offset_effects = sorted(ok_rows, key=lambda r: -r["offset_effect_pips"])
    max_effect = offset_effects[0]["offset_effect_pips"] if offset_effects else 0.0
    claim(max_effect >= OFFSET_LIVE_MIN_PIPS,
          f"alignment using the recorded clock offsets differs measurably "
          f"(>= {OFFSET_LIVE_MIN_PIPS} pips) from alignment that ignores "
          f"them, on >=1 break (max observed: {max_effect:.4f} pips)")
    for r in offset_effects[:5]:
        print(f"          {r['trade_id']} ({r['break_id']}, {r['pair']}): "
              f"with offsets {r['aligned_diff_pips']:.4f} pips vs without "
              f"{r['aligned_diff_pips_no_off']:.4f} pips "
              f"(delta {r['offset_effect_pips']:.4f})")

    # --- Chain shape --------------------------------------------------------
    chained = {t for t, n in chain_len.items() if n >= 1}
    two_plus = {t for t, n in chain_len.items() if n >= 2}
    claim(len(chained) >= 10 and len(two_plus) >= 3,
          f">=10 trades with amendment chains, >=3 with two-or-more, "
          f"recomputed from Fluree amendment-node subject URIs "
          f"(`amd-<trade_id>-<seq>`; `ex:amends` itself is never queried "
          f"and ex:amendmentSeq's object value is discarded -- the seq is "
          f"parsed out of the node URI, see fetch_fluree()) "
          f"({len(chained)} chained, {len(two_plus)} with 2+)")

    # --- Rate coverage ------------------------------------------------------
    missing = trade_pair_dates - rate_coverage
    claim(len(missing) == 0,
          f"every (pair, value_date) in fx_trade has an fx_reference_rate "
          f"row ({len(trade_pair_dates)} combos, {len(missing)} missing)")
    for m in sorted(missing)[:10]:
        print(f"          missing: {m}")

    # --- Disagreement report (designed_class read ONLY here) ---------------
    disagreements = [r for r in ok_rows if r["aligned_class"] != r["designed_class"]]
    rate = len(disagreements) / len(ok_rows) if ok_rows else 1.0
    print(f"\n  disagreement report: {len(disagreements)} / {len(ok_rows)} "
          f"breaks recompute to a class different from "
          f"break_record.designed_class ({rate:.1%})")
    for r in disagreements:
        print(f"          {r['trade_id']} ({r['break_id']}, {r['pair']}): "
              f"designed={r['designed_class']}  recomputed={r['aligned_class']}  "
              f"(raw {r['raw_diff_pips']:.4f} -> aligned "
              f"{r['aligned_diff_pips']:.4f} pips)")
    if rate > 0.10:
        print("  ^^ ABOVE 10% -- the generator and the reconciliation "
              "disagree about the mechanism (design §7.5's coincidence risk)")

    failed = [m for ok, m in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
