#!/usr/bin/env python3
"""Cohort performance and vintage benchmarks -- the materialized layer.

    uv run loaders/load_abs_aggregates_wave14.py

Cohorts are (deal, period, credit band) -- the dimensions in the DDL's
primary key and the `GROUP BY` below. A state-region or vintage-of-origination
cut is NOT materialized here: nothing downstream consumes it yet, and Task 5
already indexed `abs_loan_period` on (deal_id, period, obligor_geographic_
location), so a state cut remains available on demand from the loan level.
That split -- materialize what the granularities read, derive the rest on
demand -- is exactly the cost strategy this product teaches.

## Why tables and not views

Sec E puts everything above loan level in the materialized band. A view would
rescan 1.32M rows per read and `validators/abs_cost.py` would then measure no
difference between granularities, which is precisely the behaviour the
product is meant to expose. `CREATE OR REPLACE VIEW` is also avoided on
principle here for a second reason: Wave 13b found an early loader whose
`CREATE OR REPLACE VIEW` would have silently rebuilt a view *without* a
later wave's source, and every query would still have worked. These are
`CREATE TABLE IF NOT EXISTS` plus an explicit `TRUNCATE` + `INSERT` rebuild.
"""
from __future__ import annotations

import argparse
import sys

from ccf.config import PG_SCHEMA_V2, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)

#: Fix-round-1 migration: an earlier build created abs_vintage_benchmark
#: with the column named `cumulative_chargeoff_percent`, which the reviewer
#: correctly flagged as the wrong name -- the figure is a per-period flow
#: rate (GROUP BY includes c.period), not a life-to-date cumulative one, and
#: this data cannot support a genuine cumulative figure: the reporting
#: window opens 2025-07 while these deals originated in 2022/2024, so
#: charge-offs before the window are missing entirely. Renamed to
#: `period_chargeoff_percent`. This DO block is the idempotent migration --
#: it renames the column exactly once, then becomes a no-op on every
#: subsequent run (and on a fresh environment, where the table does not yet
#: exist at all).
#: Second migration, same shape. `weighted_average_coupon` held a DECIMAL
#: FRACTION (0.1448) and sat one column away from `delinquency_percent`, which
#: holds a TRUE PERCENTAGE (11.18). Two scales in one row with neither name
#: saying which: a consumer comparing "delinquency 11.18" against "coupon 0.14"
#: reads a near-zero-rate loan book. ABS-EE stores rates as fractions despite
#: every element name ending in "Percentage" -- the raw file carries
#: <originalInterestRatePercentage>0.19880000< for a 19.88% APR -- so the
#: LOADER is faithful to the source and this AGGREGATE layer is where the
#: normalisation belongs. Renamed and multiplied by 100.
#:
#: (The zeros in that column are real filed values, not absences coerced to
#: zero: the element is present on all 35,814 assets and 11,553 of the 11,654
#: zero-rate records also carry a zero balance, so they contribute to neither
#: side of the weighted average. The 101 that do not move the WAC by 0.06pp.)
MIGRATE = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = '{S}' AND table_name = 'abs_cohort_performance'
                 AND column_name = 'weighted_average_coupon')
    THEN
        ALTER TABLE "{S}".abs_cohort_performance
            RENAME COLUMN weighted_average_coupon TO weighted_average_coupon_percent;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = '{S}' AND table_name = 'abs_vintage_benchmark'
                 AND column_name = 'cumulative_chargeoff_percent')
    THEN
        ALTER TABLE "{S}".abs_vintage_benchmark
            RENAME COLUMN cumulative_chargeoff_percent TO period_chargeoff_percent;
    END IF;
END $$;
"""

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_cohort_performance (
    deal_id text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    period  char(7) NOT NULL,
    credit_band text NOT NULL,       -- <600 | 600-659 | 660-719 | 720+ | unscored
    loan_count integer NOT NULL,
    pool_balance numeric NOT NULL,
    delinquent_60_plus_balance numeric NOT NULL,
    delinquency_percent numeric NOT NULL,
    chargedoff_amount numeric NOT NULL,
    recovered_amount numeric NOT NULL,
    weighted_average_coupon_percent numeric,   -- PERCENT, like its sibling above
    provenance text NOT NULL,
    PRIMARY KEY (deal_id, period, credit_band)
);

-- RULING F51: the key is (asset_class, vintage, period) -- credit_tier is
-- NOT part of it. Keyed with credit_tier, the three loaded deals fell into
-- three distinct cells and `deal_count` was 1 in all 36 rows: every "benchmark"
-- was a cohort of one, so §F condition 7 and §D step 6 compared each deal
-- against ITSELF. docs/wave14-design.md §2 chose these deals precisely because
-- SDART-2022-6 and TAOT-2022-B share vintage 2022 and differ in tier, calling
-- that "what makes the vintage benchmark interpretable rather than merely
-- computed" -- so tier is the CONTRAST dimension, and grouping by it destroyed
-- the very comparison the selection was for. It survives as `credit_tiers`,
-- the set present in the cell, which is what makes the contrast readable.
CREATE TABLE IF NOT EXISTS "{S}".abs_vintage_benchmark (
    asset_class text NOT NULL,       -- auto-loan
    vintage integer NOT NULL,
    period char(7) NOT NULL,
    credit_tiers text NOT NULL,      -- 'prime+subprime' | 'subprime'
    deal_count integer NOT NULL,
    pool_balance numeric NOT NULL,
    delinquency_percent numeric NOT NULL,
    period_chargeoff_percent numeric NOT NULL,       -- flow rate for THIS period, not life-to-date
    -- (the window opens 2025-07 while these deals originated in 2022/2024,
    -- so a genuine cumulative figure cannot be computed from this data;
    -- naming it "cumulative" would be a plausible number that is wrong)
    provenance text NOT NULL,
    PRIMARY KEY (asset_class, vintage, period)
);
"""

#: Delinquency is measured at >= 60 days, NOT >= 61.
#:
#: Measured 2026-08-23 against SDART 2022-6's 2026-07 file, 35,171 records:
#:
#:   pool balance      301,051,961.82  == servicer item 64, to the penny
#:   60+ balance        32,480,926.13  == servicer item 78, to the penny
#:   delinquency at >=60      10.7891% -> 10.79%, the published figure
#:   delinquency at >=61      10.1139%   0.68pp low, matches nothing filed
#:
#: The servicer's line is "Aggregate Principal Balance of 60 Day Delinquent
#: Receivables", and 60 means 60. An earlier draft of this plan used >= 61 and
#: paired it with a 2.0pp reconciliation tolerance, which would have absorbed
#: the 0.68pp bias silently on every deal-period forever -- a gate wide enough
#: to swallow its own systematic error.
#:
#: Weighting is by BALANCE, never by row count. ABS-EE keeps reporting
#: charged-off loans with a frozen delinquency status and a zero balance:
#: 35,171 records carry only 22,734 nonzero balances, so a count-based ratio
#: reads about 36% against a true 10.79%.
COHORTS = f"""
INSERT INTO "{S}".abs_cohort_performance
SELECT deal_id, period,
       CASE WHEN obligor_credit_score IS NULL THEN 'unscored'
            WHEN obligor_credit_score < 600 THEN '<600'
            WHEN obligor_credit_score < 660 THEN '600-659'
            WHEN obligor_credit_score < 720 THEN '660-719'
            ELSE '720+' END                                   AS credit_band,
       COUNT(*)                                               AS loan_count,
       SUM(reporting_period_actual_end_balance_amount)        AS pool_balance,
       SUM(CASE WHEN current_delinquency_status >= 60
                THEN reporting_period_actual_end_balance_amount
                ELSE 0 END)                                   AS delinquent_60_plus_balance,
       CASE WHEN SUM(reporting_period_actual_end_balance_amount) > 0
            THEN ROUND(100 * SUM(CASE WHEN current_delinquency_status >= 60
                                      THEN reporting_period_actual_end_balance_amount
                                      ELSE 0 END)
                       / SUM(reporting_period_actual_end_balance_amount), 4)
            ELSE 0 END                                        AS delinquency_percent,
       SUM(chargedoff_principal_amount)                       AS chargedoff_amount,
       SUM(recovered_amount)                                  AS recovered_amount,
       -- Conditional denominator: a NULL rate must drop its balance from
       -- BOTH sides, not just the numerator. SUM(rate * balance) already
       -- skips a NULL rate's row; if the denominator kept the total pool
       -- balance, that row's balance would sit in the denominator with no
       -- matching numerator contribution, biasing the average low with no
       -- error and no warning. Guarding on this same conditional sum (not
       -- the total pool balance) also avoids a division-by-zero error if
       -- every rated balance nets to exactly 0.
       CASE WHEN SUM(CASE WHEN reporting_period_interest_rate_percentage IS NOT NULL
                          THEN reporting_period_actual_end_balance_amount END) > 0
            THEN ROUND(100 * SUM(reporting_period_interest_rate_percentage
                                 * reporting_period_actual_end_balance_amount)
                       / SUM(CASE WHEN reporting_period_interest_rate_percentage IS NOT NULL
                                  THEN reporting_period_actual_end_balance_amount END), 4)
            END                                               AS weighted_average_coupon_percent,
       'public'
FROM "{S}".abs_loan_period
GROUP BY deal_id, period, 3;
"""

BENCHMARKS = f"""
INSERT INTO "{S}".abs_vintage_benchmark
SELECT 'auto-loan', d.vintage, c.period,
       STRING_AGG(DISTINCT d.credit_tier, '+' ORDER BY d.credit_tier),
       COUNT(DISTINCT c.deal_id),
       SUM(c.pool_balance),
       CASE WHEN SUM(c.pool_balance) > 0
            THEN ROUND(100 * SUM(c.delinquent_60_plus_balance) / SUM(c.pool_balance), 4)
            ELSE 0 END,
       CASE WHEN SUM(c.pool_balance) > 0
            THEN ROUND(100 * SUM(c.chargedoff_amount) / SUM(c.pool_balance), 4)
            ELSE 0 END,
       'public'
FROM "{S}".abs_cohort_performance c
JOIN "{S}".abs_deal d USING (deal_id)
GROUP BY d.vintage, c.period;
"""


#: RULING F51 migration. `abs_vintage_benchmark` is entirely derived -- the
#: loader TRUNCATEs and rebuilds it every run -- so dropping it loses nothing
#: that is not regenerated four statements later. Guarded on the OLD column so
#: it fires exactly once and a re-run is a no-op.
REKEY_BENCHMARK = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = '{S}' AND table_name = 'abs_vintage_benchmark'
                 AND column_name = 'credit_tier') THEN
        DROP TABLE "{S}".abs_vintage_benchmark;
    END IF;
END $$;
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Build cohort and vintage aggregates")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        # A dry run must touch NOTHING. MIGRATE and DDL used to run above this
        # check and commit -- so `--dry-run` performed a schema migration, which
        # is not a dry run by any reading.
        print("  DRY RUN — no migration, no DDL, no rebuild.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(MIGRATE)
        cur.execute(REKEY_BENCHMARK)
        cur.execute(DDL)
        # Full rebuild, not upsert: a cohort that disappears (a credit band
        # with no remaining loans) must disappear from the table too.
        cur.execute(f'TRUNCATE "{S}".abs_cohort_performance, "{S}".abs_vintage_benchmark')
        cur.execute(COHORTS)
        cohorts = cur.rowcount
        cur.execute(BENCHMARKS)
        benchmarks = cur.rowcount
        conn.commit()
        cur.execute(f"""SELECT deal_id, period, delinquency_percent
                        FROM "{S}".abs_cohort_performance
                        WHERE credit_band = '<600' ORDER BY deal_id, period LIMIT 6""")
        sample = cur.fetchall()

    print(f"  {cohorts} cohort rows, {benchmarks} vintage benchmark rows")
    for r in sample:
        print("    %-14s %s  <600 band delinquency %s%%" % r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
