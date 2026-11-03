#!/usr/bin/env python3
"""Measure the fan-out cost at each granularity.

    uv run validators/abs_cost.py
    uv run validators/abs_cost.py --repeat 5

§F: "Measured cost figures at each granularity, captured during assembly and
published alongside the spec -- this product's most valuable output for the
SDK."

## What is measured, and what is not

Measured: rows returned, shared buffer blocks accessed, and wall-clock latency
for the canonical query at each granularity, against the loaded stores. That
is a property of the DATA and squarely this project's job.

NOT measured or built here: operators, projection, contracts, TTL. Those are
downstream and out of scope per CLAUDE.md.

## Blocks are the reproducible figure; latency is not

Blocks are exactly stable run to run (2 / 4 / 2 / 1,763 in every run measured
so far, an 882x ratio every time). The TIME multiple is not: measured across
five runs on identical data it ranged 55x to 252x, because the denominator is
a sub-millisecond figure sitting on the noise floor. Publish the block ratio
as the planning number and treat the time multiple as order-of-magnitude.

## The curve is recomputed, never stored as a constant

A hard-coded cost table is the same defect class as a hard-coded threshold:
it reports the same answer after the data changes underneath it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import statistics
import sys
import time

from ccf.config import PG_SCHEMA_V2, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)

#: The three rungs that MUST be materialized. `loan` is the pool itself and is
#: expected to be expensive; these three are the ones a view would silently
#: turn back into a pool rescan.
AGGREGATE_RUNGS = ("deal", "tranche", "cohort")

#: Guard 2's line. Healthy is ~0.002 (measured worst case across all 36
#: deal-periods); a view puts it at ~1.0. Far from both, so it is not a
#: tolerance straddling a known bias.
MAX_AGGREGATE_BLOCK_RATIO = 0.25

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_cost_measurement (
    measured_at timestamptz NOT NULL,
    granularity text NOT NULL,
    deal_id     text NOT NULL,
    period      char(7) NOT NULL,
    rows_returned bigint NOT NULL,
    shared_blocks_accessed bigint,
    median_ms numeric NOT NULL,
    repeats integer NOT NULL,
    row_basis bigint NOT NULL,      -- table size the measurement was taken against
    -- RULING F43: deliberately NO provenance column. CLAUDE.md rule 1 names
    -- exactly three classes and 'derived — measured' would be a fourth. A
    -- latency is not a data element WITH a source, it IS a source: measured_at,
    -- row_basis and repeats already record where the number came from, against
    -- what, and how many times. Verified nothing requires it: no validator or
    -- loader in the repo asserts that a ccf_v2 table carries provenance --
    -- partition.py's only information_schema checks look for supersession and
    -- relationship-edge columns, never provenance, and conditions.py reads
    -- provenance only per-table where the column already exists.
    PRIMARY KEY (measured_at, granularity, deal_id, period)
);
"""

#: One-time migration. The column was `heap_blocks_read`, which was wrong twice
#: over: the figure is Shared Hit + Shared Read across the whole plan subtree,
#: so it counts index pages as well as heap pages, and they are blocks, not
#: bytes. Written as a guarded DO block so a fresh database and an already-
#: loaded one both end up with the same schema.
MIGRATE = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = '{S}' AND table_name = 'abs_cost_measurement'
                 AND column_name = 'heap_blocks_read') THEN
        ALTER TABLE "{S}".abs_cost_measurement
            RENAME COLUMN heap_blocks_read TO shared_blocks_accessed;
    END IF;
END $$;
"""

QUERIES = {
    "deal": f"""
        SELECT deal_id, SUM(pool_balance), SUM(delinquent_60_plus_balance)
        FROM "{S}".abs_cohort_performance
        WHERE deal_id = %(deal)s AND period = %(period)s GROUP BY deal_id""",
    # RULING F44: the tranche rung must return ONE ROW PER TRANCHE. Joining
    # abs_tranche straight to abs_cohort_performance on deal_id alone is a
    # cartesian product -- cohort is keyed (deal_id, period, credit_band), so
    # 6 tranches x 4 bands measured 24 rows and called it tranche granularity.
    # Collapse the pool balance to the deal first. Verified across all 36
    # (deal, period) cells: 6 tranches, 6 rows, every time.
    "tranche": f"""
        SELECT t.tranche_id, t.seniority_rank, c.pool_balance
        FROM "{S}".abs_tranche t
        JOIN (SELECT deal_id, SUM(pool_balance) AS pool_balance
              FROM "{S}".abs_cohort_performance
              WHERE deal_id = %(deal)s AND period = %(period)s
              GROUP BY deal_id) c ON c.deal_id = t.deal_id
        WHERE t.deal_id = %(deal)s""",
    "cohort": f"""
        SELECT credit_band, loan_count, pool_balance, delinquency_percent
        FROM "{S}".abs_cohort_performance
        WHERE deal_id = %(deal)s AND period = %(period)s""",
    "loan": f"""
        SELECT asset_number, reporting_period_actual_end_balance_amount,
               current_delinquency_status, obligor_credit_score
        FROM "{S}".abs_loan_period
        WHERE deal_id = %(deal)s AND period = %(period)s""",
}


def measure(cur, granularity: str, deal: str, period: str, repeats: int) -> dict:
    sql = QUERIES[granularity]
    params = {"deal": deal, "period": period}

    # Explicit warm-up so the first timing does not carry cold-cache noise
    # into a curve that is meant to compare granularities, not cache states.
    cur.execute(sql, params)
    cur.fetchall()

    timings, rows = [], 0
    for _ in range(repeats):
        start = time.perf_counter()
        cur.execute(sql, params)
        fetched = cur.fetchall()
        timings.append((time.perf_counter() - start) * 1000)
        rows = len(fetched)

    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}", params)
    plan = cur.fetchone()[0][0]["Plan"]
    # Top-level node only, and that is correct: Postgres accumulates buffer
    # counts UP the plan tree. Verified on a six-level plan -- the root's
    # hit 255 / read 592 equals the Nested Loop beneath it and is >= every
    # descendant, while summing the leaves gives 23, i.e. nonsense.
    blocks = plan.get("Shared Hit Blocks", 0) + plan.get("Shared Read Blocks", 0)

    return {"granularity": granularity, "deal_id": deal, "period": period,
            "rows_returned": rows, "shared_blocks_accessed": blocks,
            "median_ms": round(statistics.median(timings), 3), "repeats": repeats,
            "relations": plan_relations(plan)}


def plan_relations(node: dict) -> set:
    """Every base relation the plan actually touches, walked to the leaves.

    The ratio guard below is width-dependent: a rescan that happens to be
    CHEAPER than the loan rung slips under it -- `cohort` at 400 blocks against
    loan's 1,763 is 0.227, under the 0.25 line, while still rescanning the pool.
    A covering index would land there. This is the exact test the ratio only
    approximates: an aggregate rung whose plan reads `abs_loan_period` is not
    materialized, at any block count.
    """
    rels = {node["Relation Name"]} if "Relation Name" in node else set()
    for child in node.get("Plans", []):
        rels |= plan_relations(child)
    return rels


def guards(results: list[dict]) -> list[str]:
    """Return the failure messages. Empty means the curve is trustworthy."""
    by = {r["granularity"]: r for r in results}
    loan, deal = by["loan"], by["deal"]
    failures = []

    # Guard 1 -- ROWS. Weaker than it looks, and worth being honest about: the
    # deal query is a GROUP BY under a deal_id filter, so it returns at most
    # one row by construction and this reduces to "loan returned >= 2 rows".
    # What it actually catches is loan data being absent or the --deal/--period
    # naming nothing, which sends both rungs to 0. It does NOT catch a
    # de-materialized aggregate; guard 2 is what does that.
    if loan["rows_returned"] <= deal["rows_returned"]:
        failures.append(
            f"loan granularity returned {loan['rows_returned']} rows against "
            f"deal's {deal['rows_returned']}. There is no fan-out to measure "
            f"-- most likely no loan rows exist for {deal['deal_id']} "
            f"{deal['period']}.")

    # Guard 2 -- BLOCKS, and it is the one that earns its keep. Guard 1 CANNOT
    # see the failure this one names: if an aggregate table were a view over
    # abs_loan_period, its query is still a GROUP BY returning the same row
    # count, so guard 1 stays green while the rung silently rescans the pool.
    #
    # Checked over ALL THREE aggregate rungs, not just `deal`. Checking `deal`
    # alone left a real hole: with `deal` materialized and only `cohort`
    # rescanning, the curve inverted (loan measured 0.3x the deal time) and
    # both guards stayed green.
    # Guard 2a -- EXACT. Any aggregate rung reading the pool table directly is
    # not materialized, whatever it costs.
    rescanning = sorted(g for g in AGGREGATE_RUNGS
                        if "abs_loan_period" in by[g].get("relations", set()))
    if rescanning:
        failures.append(
            f"the {rescanning} rung(s) read abs_loan_period directly. A "
            f"materialized aggregate never touches the pool table -- these are "
            f"views, or the loader built them as views.")

    worst = max(AGGREGATE_RUNGS, key=lambda g: by[g]["shared_blocks_accessed"])
    ratio = by[worst]["shared_blocks_accessed"] / max(loan["shared_blocks_accessed"], 1)
    if ratio >= MAX_AGGREGATE_BLOCK_RATIO:
        failures.append(
            f"the `{worst}` rung accessed {by[worst]['shared_blocks_accessed']:,} "
            f"shared blocks against loan's {loan['shared_blocks_accessed']:,} "
            f"({ratio:.3f} of it, limit {MAX_AGGREGATE_BLOCK_RATIO}). That rung "
            f"is not materialized -- it is rescanning the pool, so the curve "
            f"measures one table twice.")

    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--deal", default="SDART-2022-6")
    ap.add_argument("--period", default="2026-06")
    ap.add_argument("--no-store", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn, conn.cursor() as cur:
        # Only when the run intends to store. `--no-store` used to create the
        # table and run the rename migration anyway, which is a schema change
        # performed by a flag whose whole promise is that it changes nothing.
        if not args.no_store:
            cur.execute(DDL)
            cur.execute(MIGRATE)
            conn.commit()
        cur.execute(f'SELECT COUNT(*) FROM "{S}".abs_loan_period')
        basis = cur.fetchone()[0]

        # Stamped in Python when measurement starts, not by the column default.
        # `now()` is transaction_timestamp() -- it would record when this
        # transaction opened, which with --repeat 5 is several seconds before
        # the rows are written. One timestamp for the whole run, deliberately:
        # it is the run's batch key, and the four rungs belong to one batch.
        measured_at = dt.datetime.now(dt.timezone.utc)

        print(f"Cost curve — {args.deal} {args.period}, "
              f"measured against {basis:,} loan rows\n")
        print(f"  {'granularity':<12}{'rows':>10}{'blocks':>10}{'median ms':>12}"
              f"{'x deal':>9}")
        results, baseline = [], None
        for g in ("deal", "tranche", "cohort", "loan"):
            m = measure(cur, g, args.deal, args.period, args.repeat)
            # RULING F45: `is None`, not `or`. A first median of exactly 0.0 is
            # falsy, and `or` would silently re-baseline every iteration --
            # every ratio would read 1.0x and the curve would look flat.
            if baseline is None:
                baseline = m["median_ms"]
            results.append(m)
            print(f"  {g:<12}{m['rows_returned']:>10,}"
                  f"{m['shared_blocks_accessed']:>10,}"
                  f"{m['median_ms']:>12.3f}"
                  f"{m['median_ms'] / max(baseline, 0.001):>8.1f}x")

        failures = guards(results)
        if failures:
            for f in failures:
                print(f"\n  FAIL: {f}")
            # Deliberately NOT stored. A failed measurement written to
            # abs_cost_measurement is indistinguishable from a good one --
            # there is no verdict column -- and the registered condition
            # counts DISTINCT granularity across the whole table, so four
            # rows from a broken run would satisfy it forever.
            print("\n  measurement NOT stored — a failed curve is not evidence")
            return 1

        if not args.no_store:
            for m in results:
                cur.execute(f"""
                    INSERT INTO "{S}".abs_cost_measurement
                      (measured_at, granularity, deal_id, period, rows_returned,
                       shared_blocks_accessed, median_ms, repeats, row_basis)
                    VALUES (%(measured_at)s,%(granularity)s,%(deal_id)s,%(period)s,
                            %(rows_returned)s,%(shared_blocks_accessed)s,
                            %(median_ms)s,%(repeats)s,%(basis)s)""",
                    {**m, "basis": basis, "measured_at": measured_at})
            conn.commit()

    loan = next(r for r in results if r["granularity"] == "loan")
    deal = next(r for r in results if r["granularity"] == "deal")
    print(f"\n  fan-out {loan['rows_returned'] / max(deal['rows_returned'], 1):,.0f}x "
          f"in rows and "
          f"{loan['shared_blocks_accessed'] / max(deal['shared_blocks_accessed'], 1):,.0f}x "
          f"in blocks — those are the reproducible figures. Time came out "
          f"{loan['median_ms'] / max(deal['median_ms'], 0.001):,.0f}x this run, "
          f"but it swings by several-fold on identical data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
