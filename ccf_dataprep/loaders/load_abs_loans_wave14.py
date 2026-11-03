#!/usr/bin/env python3
"""Load ABS-EE loan-level records into Postgres.

    uv run loaders/load_abs_loans_wave14.py --dry-run
    uv run loaders/load_abs_loans_wave14.py --deal SDART-2022-6 --period 2026-06
    uv run loaders/load_abs_loans_wave14.py            # all 36, ~1.32M rows

## Delete by period, never upsert

The pool shrinks: SDART 2022-6 carries 44,251 assets at 2025-07 and 35,814
at 2026-06. An upsert-only reload leaves the 8,437-row difference behind,
anchored to a period they are no longer part of. Every query still works and
every count is wrong -- `known-issues.md` §14.10, found in Wave 13b's Mongo
loader and not swept elsewhere until now.

So each (deal, period) is deleted before it is inserted, inside one
transaction, which also makes the loader resumable per period.

## COPY, not executemany

1.32M rows through `executemany` is roughly an hour. `COPY` is a few minutes.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf.absee import ABSEE_FIELDS, coerce, parse_assets, snake
from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect

S = assert_v2_schema(PG_SCHEMA_V2)
REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"

COLUMNS = ("deal_id", "period") + tuple(snake(f) for f in ABSEE_FIELDS)

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_deal (
    deal_id       text PRIMARY KEY,
    legal_name    text NOT NULL,
    cik           text NOT NULL,
    depositor_cik text NOT NULL,
    credit_tier   text NOT NULL,        -- prime | subprime
    vintage       integer NOT NULL,
    servicer      text NOT NULL,
    provenance    text NOT NULL,
    source        text NOT NULL,
    retrieved_at  date NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_loan_period (
    deal_id text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    period  char(7) NOT NULL,                       -- YYYY-MM, the reportDate month
    asset_type_number text,
    asset_number      text NOT NULL,
    reporting_period_beginning_date date,
    reporting_period_ending_date    date,
    originator_name   text,
    origination_date  date,
    original_loan_amount numeric,
    original_loan_term   integer,
    original_interest_rate_percentage numeric,
    interest_calculation_type_code text,
    original_interest_rate_type_code text,
    original_first_payment_date date,
    underwriting_indicator boolean,
    grace_period_number integer,
    payment_type_code text,
    subvented text,
    vehicle_manufacturer_name text,
    vehicle_model_name text,
    vehicle_new_used_code text,
    vehicle_model_year integer,
    vehicle_type_code text,
    vehicle_value_amount numeric,
    vehicle_value_source_code text,
    obligor_credit_score_type text,
    obligor_credit_score integer,
    obligor_income_verification_level_code text,
    obligor_employment_verification_code text,
    co_obligor_indicator boolean,
    payment_to_income_percentage numeric,
    obligor_geographic_location text,          -- US state only; no address
    asset_added_indicator boolean,
    reporting_period_modification_indicator boolean,
    modification_type_code text,
    servicing_advance_method_code text,
    servicing_fee_percentage numeric,
    reporting_period_beginning_loan_balance_amount numeric,
    reporting_period_interest_rate_percentage numeric,
    next_interest_rate_percentage numeric,
    next_reporting_period_payment_amount_due numeric,
    reporting_period_scheduled_payment_amount numeric,
    scheduled_interest_amount numeric,
    scheduled_principal_amount numeric,
    other_principal_adjustment_amount numeric,
    -- Actual cash collected, as against the SCHEDULED amounts above. These
    -- four were missing from the first cut of ABSEE_FIELDS and would have
    -- been dropped silently from all 1.32M rows; both issuers emit them.
    actual_interest_collected_amount numeric,
    actual_principal_collected_amount numeric,
    actual_other_collected_amount numeric,
    total_actual_amount_paid numeric,
    reporting_period_actual_end_balance_amount numeric,
    remaining_term_to_maturity_number integer,
    loan_maturity_date date,
    interest_paid_through_date date,
    payment_extended_number integer,
    -- NULL means the loan is still active. 0 is a real ABS-EE code and does
    -- not mean 'no code' -- see ccf/absee.py.
    zero_balance_effective_date date,
    zero_balance_code text,
    -- NULL means not measured this period; 0 means CURRENT. Conflating them
    -- biases every delinquency ratio downward.
    current_delinquency_status integer,
    primary_loan_servicer_name text,
    most_recent_servicing_transfer_received_date date,
    asset_subject_demand_indicator boolean,
    other_assessed_uncollected_servicer_fee_amount numeric,
    chargedoff_principal_amount numeric,
    recovered_amount numeric,
    repossessed_indicator boolean,
    repossessed_proceeds_amount numeric,
    PRIMARY KEY (deal_id, period, asset_number)
);

CREATE INDEX IF NOT EXISTS abs_loan_period_deal_period_idx
    ON "{S}".abs_loan_period (deal_id, period);
CREATE INDEX IF NOT EXISTS abs_loan_period_delinquency_idx
    ON "{S}".abs_loan_period (deal_id, period, current_delinquency_status)
    WHERE current_delinquency_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS abs_loan_period_state_idx
    ON "{S}".abs_loan_period (deal_id, period, obligor_geographic_location);
"""


def load_period(conn, deal_id: str, period: str, path) -> int:
    """Replace one (deal, period) slice. Returns rows written."""
    with conn.cursor() as cur:
        # The delete is the idempotency contract. It must be inside the same
        # transaction as the insert, or an interrupted run leaves the period
        # empty rather than unchanged.
        cur.execute(f'DELETE FROM "{S}".abs_loan_period '
                    "WHERE deal_id = %s AND period = %s", (deal_id, period))

        collist = ", ".join(f'"{c}"' for c in COLUMNS)
        written = 0
        with cur.copy(f'COPY "{S}".abs_loan_period ({collist}) FROM STDIN') as cp:
            for raw in parse_assets(path):
                rec = coerce(raw)
                cp.write_row((deal_id, period,
                              *(rec[snake(f)] for f in ABSEE_FIELDS)))
                written += 1
    return written


def source_retrieval_date() -> str:
    """The date the source was actually FETCHED, per the manifest.

    Was `date.today()`, which is the date of the RELOAD. Rule 1 requires a
    `public` element to record its retrieval date; substituting today's date
    means a reload next month rewrites the provenance of data fetched this
    month, and no row count changes to betray it. Reading it from the manifest
    makes the value a property of the fetch instead of a property of the run.
    """
    manifest = json.loads((REPO_ROOT / "sources" / "absee" / "manifest.json").read_text())
    fetches = manifest["fetches"]
    if not fetches:
        raise RuntimeError("sources/absee/manifest.json records no fetches")
    return min(f["retrieved_at"] for f in fetches)[:10]


def main() -> int:
    ap = argparse.ArgumentParser(description="Load ABS-EE loans into Postgres")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--deal", help="load one deal only")
    ap.add_argument("--period", help="load one period only, e.g. 2026-06")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    source = "SEC EDGAR Form ABS-EE EX-102"
    retrieved = source_retrieval_date()

    if args.dry_run:
        # A dry run must touch NOTHING. The DDL and the abs_deal upsert used to
        # sit above this check and ran unconditionally, so `--dry-run` created
        # tables and advanced `retrieved_at` on all three deals to the day of
        # the RELOAD -- silently rewriting the recorded retrieval date of a
        # public source, which CLAUDE.md rule 1 requires be accurate.
        for deal in reg["deals"]:
            for period in reg["window"]:
                if args.deal and deal["deal_id"] != args.deal:
                    continue
                if args.period and period != args.period:
                    continue
                path = REPO_ROOT / "sources" / "absee" / deal["slug"] / f"{period}.xml"
                mark = "" if path.exists() else "   MISSING"
                print(f"  would load {deal['deal_id']:14s} {period}  "
                      f"{path.name}{mark}")
        print("\n  DRY RUN — nothing written, no DDL, no upsert")
        return 0

    with pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            for deal in reg["deals"]:
                # Every non-key column refreshes. Refreshing only legal_name and
                # retrieved_at made this reload count-blind: correcting
                # `credit_tier` upstream would never reach Postgres, and
                # abs_vintage_benchmark reports it per cell, so the benchmark
                # would keep publishing the wrong tier with no row count ever
                # changing to betray it.
                cur.execute(f"""
                    INSERT INTO "{S}".abs_deal (deal_id, legal_name, cik,
                        depositor_cik, credit_tier, vintage, servicer,
                        provenance, source, retrieved_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'public',%s,%s)
                    ON CONFLICT (deal_id) DO UPDATE SET
                        legal_name    = EXCLUDED.legal_name,
                        cik           = EXCLUDED.cik,
                        depositor_cik = EXCLUDED.depositor_cik,
                        credit_tier   = EXCLUDED.credit_tier,
                        vintage       = EXCLUDED.vintage,
                        servicer      = EXCLUDED.servicer,
                        provenance    = EXCLUDED.provenance,
                        source        = EXCLUDED.source,
                        retrieved_at  = EXCLUDED.retrieved_at""",
                    (deal["deal_id"], deal["legal_name"], deal["cik"],
                     deal["depositor_cik"], deal["credit_tier"],
                     deal["vintage"], deal["servicer"], source, retrieved))
        conn.commit()

        total = 0
        for deal in reg["deals"]:
            if args.deal and deal["deal_id"] != args.deal:
                continue
            for period in reg["window"]:
                if args.period and period != args.period:
                    continue
                path = REPO_ROOT / "sources" / "absee" / deal["slug"] / f"{period}.xml"
                if not path.exists():
                    raise RuntimeError(
                        f"missing {path}. Run generators/fetch_abs_deals.py. "
                        f"Do not skip the period -- a short window silently "
                        f"breaks the vintage benchmark.")
                if args.dry_run:
                    print(f"  would load {deal['deal_id']} {period}  {path.name}")
                    continue
                n = load_period(conn, deal["deal_id"], period, path)
                conn.commit()           # per period, so a crash costs one period
                total += n
                print(f"  {deal['deal_id']:14s} {period}  {n:>7,} rows")

    print(f"\n  {total:,} loan-period rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
