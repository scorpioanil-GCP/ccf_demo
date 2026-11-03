# validators/intraday.py
"""Wave 12's treasury gate -- claims `conditions.py` cannot establish by counting.

Five claims, each RECOMPUTED from loaded rows:

  1. some day carries a >=8bp move within a 90-minute window
  2. every session's LAST tick equals its own day's published close (the
     session opens at the PRIOR day's close per Ruling F3 -- there is no
     published-close row to check the first tick against on its own day, so
     only the last tick is checked here)
  3. tick spacing is exactly 5 minutes, 78 per session, no gaps
  4. >=2 clients breach a concentration limit under a naive optimal allocation
  5. >=1 signal is older than the 15-minute bound AND otherwise well-formed,
     AND >=1 signal is inside the bound, so the gate discriminates rather
     than everything reading stale

Claim 1 is the Latency Poisoned instance and claim 4 is the Policy Blind
instance. Neither is catchable by a row count, which is why this file exists
rather than nine more rows in `conditions.py`.

The gate emits NINE PASS/FAIL lines, not five: claim 5 alone is three checks
(stale exists, stale rows are well-formed, a fresh row exists for contrast),
plus a data-population precondition (`intraday_tick is populated`) and a
provenance-labelling check (every tick is `synthetic — engineered`) sit
outside the five numbered claims above.

This module deliberately does NOT import `generators/ticks.py`'s
`max_rolling_move_bp`. It reimplements the arithmetic, so a bug in the
generator's rolling-move logic cannot hide by being reused here. That is the
lesson `series.py` was written from.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccf.config import pg_connect, PG_SCHEMA_V2   # noqa: E402

WINDOW_TICKS = 18            # 90 minutes at 5-minute granularity
THRESHOLD_BP = 8.0
MAX_STALENESS_MIN = 15
EXPECTED_SESSION_TICKS = 78

results: list[tuple[bool, str]] = []


def claim(ok: bool, msg: str) -> None:
    results.append((ok, msg))
    print(f"  {'PASS' if ok else 'FAIL'}  {msg}")


def rolling_max_bp(vals: list[float]) -> float:
    """Independent reimplementation -- see the module docstring."""
    if len(vals) <= WINDOW_TICKS:
        return abs(vals[-1] - vals[0]) * 100 if vals else 0.0
    return max(abs(vals[i + WINDOW_TICKS] - vals[i]) * 100
               for i in range(len(vals) - WINDOW_TICKS))


def main() -> int:
    with pg_connect() as conn:
        cur = conn.cursor()

        cur.execute(f'''SELECT tenor_years, trading_day, obs_ts, value_pct
                          FROM "{PG_SCHEMA_V2}".intraday_tick
                         ORDER BY tenor_years, obs_ts''')
        sessions: dict[tuple, list] = defaultdict(list)
        for tenor, day, ts, val in cur.fetchall():
            sessions[(float(tenor), day)].append((ts, float(val)))

        claim(bool(sessions), f"intraday_tick is populated ({len(sessions)} sessions)")

        # --- claim 1: the 8bp move -------------------------------------
        hits = {day for (tenor, day), rows in sessions.items()
                if rolling_max_bp([v for _, v in rows]) >= THRESHOLD_BP}
        claim(len(hits) >= 1,
              f">=1 day carries a >={THRESHOLD_BP}bp 90-minute move "
              f"(recomputed: {len(hits)} days)")
        for d in sorted(hits):
            print(f"          {d}")

        # --- claim 2: anchor fidelity ----------------------------------
        drift = []
        for (tenor, day), rows in sorted(sessions.items()):
            cur.execute(f'''SELECT par_yield_pct FROM "{PG_SCHEMA_V2}".benchmark_curve
                             WHERE tenor_years = %s AND curve_date = %s''',
                        (tenor, day))
            row = cur.fetchone()
            if row is None:
                drift.append((tenor, day, "no published close"))
                continue
            if abs(rows[-1][1] - float(row[0])) > 1e-6:
                drift.append((tenor, day, f"{rows[-1][1]} != {row[0]}"))
        claim(not drift,
              f"every session closes on its published value "
              f"({len(drift)} drifted)")
        if len(drift) > 5:
            print(f"          (showing 5 of {len(drift)})")
        for d in drift[:5]:
            print(f"          {d}")

        # --- claim 3: spacing ------------------------------------------
        bad = []
        for key, rows in sorted(sessions.items()):
            if len(rows) != EXPECTED_SESSION_TICKS:
                bad.append((key, f"{len(rows)} ticks"))
                continue
            gaps = {(rows[i][0] - rows[i - 1][0]) for i in range(1, len(rows))}
            if gaps != {timedelta(minutes=5)}:
                bad.append((key, f"gaps {sorted(gaps)}"))
        claim(not bad,
              f"every session is {EXPECTED_SESSION_TICKS} ticks, 5 minutes apart "
              f"({len(bad)} malformed)")

        # --- claim 4: the concentration breach -------------------------
        cur.execute(f'''SELECT c.lei, c.mandate_id, c.intent, COALESCE(c.reported_cash, 0)
                          FROM "{PG_SCHEMA_V2}".treasury_client c''')
        clients = cur.fetchall()
        breaching = []
        for lei, mandate_id, intent, cash in clients:
            cur.execute(f'''SELECT instrument_kind FROM "{PG_SCHEMA_V2}".permitted_instrument
                             WHERE mandate_id = %s''', (mandate_id,))
            permitted = {r[0] for r in cur.fetchall()}
            cur.execute(f'''SELECT counterparty_lei, instrument_kind, notional, yield_bp
                              FROM "{PG_SCHEMA_V2}".investment_position
                             WHERE holder_lei = %s''', (lei,))
            positions = cur.fetchall()
            if not positions:
                continue
            eligible = [p for p in positions if p[1] in permitted]
            if not eligible:
                continue
            best = max(eligible, key=lambda p: float(p[3]))
            total = sum(float(p[2]) for p in positions) + float(cash)
            existing = sum(float(p[2]) for p in positions
                           if p[0] == best[0])
            share = (existing + float(cash)) / total if total else 0.0
            # RULING F1: `concentration_limit` is keyed (holder, counterparty,
            # intent). Without the intent filter this returns one row per intent
            # and fetchone() picks arbitrarily, so the breach claim would depend
            # on row order rather than on the data.
            cur.execute(f'''SELECT limit_pct FROM "{PG_SCHEMA_V2}".concentration_limit
                             WHERE holder_lei = %s AND counterparty_lei = %s
                               AND intent = %s''',
                        (lei, best[0], intent))
            row = cur.fetchone()
            if row and share > float(row[0]) / 100.0:
                breaching.append((lei, best[0], round(share * 100, 1),
                                  float(row[0])))
        claim(len(breaching) >= 2,
              f">=2 clients breach a limit under a naive optimal allocation "
              f"(recomputed: {len(breaching)})")
        if len(breaching) > 5:
            print(f"          (showing 5 of {len(breaching)})")
        for lei, cp, share, cap in breaching[:5]:
            print(f"          {lei} -> {cp}  {share}% vs {cap}% cap")

        # --- claim 5: the stale signal (RULING F4) ---------------------
        # §6.1 promises a STALENESS check. Asserting that observation dates
        # exist is an easier question wearing the same label -- the failure
        # `known-issues.md` §10.11 records. Both checks now run.
        # RULING F15: age is measured against the row's recorded `as_of`, NOT
        # against now(). With now(), every signal is stale fifteen minutes after
        # generation, the fresh/stale contrast vanishes, and this claim can
        # never fail -- which would make it a decoration, not a gate.
        cur.execute(f'''SELECT signal_id, series_id, observed_at, value,
                               EXTRACT(EPOCH FROM (as_of - observed_at))/60 AS age_min
                          FROM "{PG_SCHEMA_V2}".stale_signal''')
        signals = cur.fetchall()
        stale = [r for r in signals if r[4] is not None and r[4] > MAX_STALENESS_MIN]
        claim(len(stale) >= 1,
              f">=1 signal is older than the {MAX_STALENESS_MIN}m bound "
              f"({len(stale)} of {len(signals)})")
        # A stale signal that is ALSO malformed would fail a consumer's gate for
        # the wrong reason and prove nothing about staleness.
        wellformed = [r for r in stale if r[1] and r[2] is not None and r[3] is not None]
        claim(len(wellformed) == len(stale),
              f"every stale signal is otherwise well-formed "
              f"({len(stale) - len(wellformed)} are not)")
        # The contrast is the point: a set where EVERYTHING is stale does not
        # demonstrate a staleness gate, it demonstrates a broken feed.
        fresh = [r for r in signals if r[4] is not None and r[4] <= MAX_STALENESS_MIN]
        claim(len(fresh) >= 1,
              f">=1 signal is INSIDE the bound, so the gate discriminates "
              f"({len(fresh)} fresh / {len(stale)} stale)")

        cur.execute(f'''SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".intraday_tick
                         WHERE provenance <> 'synthetic — engineered' ''')
        mislabelled = cur.fetchone()[0]
        claim(mislabelled == 0,
              f"every tick is labelled 'synthetic — engineered' ({mislabelled} are not)")

    failed = [m for ok, m in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
