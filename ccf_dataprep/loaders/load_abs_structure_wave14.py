#!/usr/bin/env python3
"""Tranche structure, monthly servicer measures and repurchase activity.

    uv run loaders/load_abs_structure_wave14.py --dry-run
    uv run loaders/load_abs_structure_wave14.py

The servicer's published figures land here as EVIDENCE. `abs_servicer_report`
is what `validators/abs_surveillance.py` compares its own loan-level
recomputation against; it is never the source of a trigger answer.

## `subordinate_to` is not a Postgres column

Task 6 made `subordinate_to` a LIST (`TAOT-2022-B-A-3` has two parents, A-2a
and A-2b), and the store-assignment split in CLAUDE.md gives Fluree `R` --
typed relationship edges -- while Postgres owns `E`, entity attributes.
Task 9 writes `isSubordinateTo` into Fluree. A Postgres column, scalar or
array, would duplicate an edge into a store that does not own it. So this
loader drops the column entirely and keeps only `seniority_rank`, which is
an attribute of the tranche, not a relationship between two tranches.

## `abs_tranche_state` is deliberately not built

The Interfaces line above still names `abs_tranche_state`, inherited from an
earlier draft. There is no DDL for it, nothing here produces rows for it,
and nothing in Tasks 9-15 reads it. Building an unread table to satisfy a
stale interface line is scope no one asked for; the omission is recorded
here so it reads as a decision, not an oversight.

## Interest rate: three states, not two

`interest_rate` distinguishes a filed `0.00%` (Toyota's retained Class A-1
and Class B -- genuinely zero-coupon, confirmed against the prospectus cover
table) from "not a fixed number" (Toyota's A-2b floats at SOFR + 0.49%,
carried in `interest_rate_text` but with no single rate to store) from an
ordinary fixed value. NULL means the second case, never the first -- no
coercion, no NOT NULL constraint.

## Every non-key column updates on conflict

The brief's ON CONFLICT clauses updated a handful of columns each,
leaving the rest (`note_balance`, the OC figures, the delinquency measures,
`provenance`, `source`, ...) at their stale values after a re-run that
fixed something upstream -- invisible to a row-count check, the same shape
as a defect already hit once in Task 7's Mongo loader. Fixed by updating
every non-key column, on every table, on every conflict.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.servicer_report import parse_servicer_report

S = assert_v2_schema(PG_SCHEMA_V2)
REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
EXTRACT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".abs_tranche (
    tranche_id          text PRIMARY KEY,
    deal_id             text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    class_name          text NOT NULL,
    seniority_rank      integer NOT NULL,
    cusip               text,
    -- NULL means "not a fixed rate" (e.g. SOFR + 0.49%), never "unfiled" and
    -- never coerced to 0.00 -- a filed 0.00% (Toyota's retained A-1 and B)
    -- is a real, distinct value from a floating note with no single rate.
    -- See the module docstring.
    interest_rate       numeric,
    interest_rate_basis text,
    provenance          text NOT NULL,
    source              text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".abs_servicer_report (
    deal_id  text NOT NULL REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    period   char(7) NOT NULL,
    pool_balance   numeric NOT NULL,
    note_balance   numeric NOT NULL,
    oc_amount      numeric,
    oc_percent     numeric,
    oc_target      numeric,
    -- The servicer's own published figures. Kept so the gate can compare its
    -- recomputation against them, NOT so anything can read the answer here.
    published_delinquency_percent numeric,
    published_delinquency_trigger numeric,
    published_trigger_occurred    boolean,
    -- Toyota publishes neither of these. NULL means NOT PUBLISHED; it is not
    -- zero, and it must not be back-filled with our own arithmetic and then
    -- sit beside genuinely-filed figures.
    sixty_day_delinquent_balance  numeric,
    cumulative_net_loss_percent   numeric,
    receivable_count integer,
    -- Buckets are JSONB keyed by the ISSUER'S OWN boundaries, not fixed
    -- columns. Santander reports 31-60 / 61-90 / 91-120 / 121+; Toyota
    -- reports 30-59 / 60-89 / 90-119 / 120+. Columns named for one issuer's
    -- boundaries would silently relabel the other's -- a 30-59 figure sitting
    -- in a column called bucket_31_60 is a different population wearing the
    -- wrong name, and nothing downstream could tell.
    delinquency_buckets jsonb NOT NULL,
    source_format text NOT NULL,          -- numbered | labelled
    provenance text NOT NULL,
    source     text NOT NULL,
    PRIMARY KEY (deal_id, period)
);

CREATE TABLE IF NOT EXISTS "{S}".abs_repurchase (
    repurchase_id text PRIMARY KEY,
    depositor_cik text NOT NULL,
    deal_id       text REFERENCES "{S}".abs_deal(deal_id) ON DELETE CASCADE,
    form          text NOT NULL,
    accession     text NOT NULL,
    filed_date    date NOT NULL,
    asset_count   integer,
    note          text,
    provenance    text NOT NULL,
    source        text NOT NULL
);
"""


def _rate(raw: str | None) -> Decimal | None:
    """`None` stays `None` -- see the module docstring's rate section."""
    return None if raw is None else Decimal(raw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reg = json.loads(REGISTRY.read_text())
    ext = {d["deal_id"]: d for d in json.loads(EXTRACT.read_text())["deals"]}

    tranche_rows, report_rows, repo_rows = [], [], []
    for deal in reg["deals"]:
        deal_id, base = deal["deal_id"], REPO_ROOT / "sources" / "absee" / deal["slug"]
        for t in ext[deal_id]["tranches"]:
            tranche_rows.append((
                t["tranche_id"], deal_id, t["class_name"], t["seniority_rank"],
                t["cusip"], _rate(t["interest_rate"]), t["interest_rate_basis"],
                "public", "SEC EDGAR Form 424B5"))
        for month in reg["window"]:
            m = parse_servicer_report(
                (base / f"servicer-{month}.htm").read_text(errors="replace"))
            report_rows.append((
                deal_id, month, m["pool_balance"], m["note_balance"],
                m["oc_amount"], m["oc_percent"], m["oc_target"],
                m["delinquency_percent"], m["delinquency_trigger"],
                m["trigger_occurred"], m["sixty_day_delinquent_balance"],
                m["cumulative_net_loss_percent"], m["receivable_count"],
                # Decimal is not JSON-serialisable; stringify the leaf
                # values (count/balance/percent), not the bucket dicts
                # themselves -- each bucket is a nested dict, and str()'ing
                # the dict one level too high produces a Python repr, not
                # JSON, and is unaddressable from SQL (fix round 1).
                json.dumps({k: {kk: str(vv) for kk, vv in v.items()}
                            for k, v in m["delinquency_buckets"].items()}),
                m["source_format"], "public",
                "SEC EDGAR Form 10-D EX-99.1"))

    for r in reg["repurchase"]:
        repo_rows.append((f"{r['depositor_cik']}-{r['accession']}",
                          r["depositor_cik"], None, r["form"], r["accession"],
                          r["filed_date"], None,
                          "depositor-level filing; covers the shelf, not one trust",
                          "public", "SEC EDGAR Form ABS-15G"))

    print(f"  {len(tranche_rows)} tranches, {len(report_rows)} servicer reports, "
          f"{len(repo_rows)} ABS-15G filings")
    if args.dry_run:
        print("\n  DRY RUN -- nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        # RULING F55 -- delete-what-this-run-owns before writing, for the two
        # tables that were upsert-only. Both are derived from a source that can
        # SHRINK: `generators/fetch_abs_deals.py` keeps the most recent four
        # ABS-15G filings per depositor, so a new filing pushes the oldest out
        # of the registry, and a tranche can disappear from prospectus_extract
        # the same way. Upsert alone never removes, so a dropped filing left a
        # Postgres row anchored to an accession the registry no longer names --
        # known-issues.md §14.10, which this wave swept in three other loaders
        # and missed here.
        #
        # Scoped to the deals and depositors THIS RUN carries, never a bare
        # TRUNCATE: a --deal run must not delete another deal's rows.
        run_deals = sorted({r[1] for r in tranche_rows})
        run_depositors = sorted({r[1] for r in repo_rows})
        if run_deals:
            cur.execute(
                f'DELETE FROM "{S}".abs_tranche '
                "WHERE deal_id = ANY(%s) AND tranche_id <> ALL(%s)",
                (run_deals, sorted({r[0] for r in tranche_rows})))
            print(f"  tranches removed as no longer filed: {cur.rowcount}")
        if run_depositors:
            cur.execute(
                f'DELETE FROM "{S}".abs_repurchase '
                "WHERE depositor_cik = ANY(%s) AND repurchase_id <> ALL(%s)",
                (run_depositors, sorted({r[0] for r in repo_rows})))
            print(f"  repurchase rows removed as no longer in the registry: "
                  f"{cur.rowcount}")
        for row in tranche_rows:
            cur.execute(f"""
                INSERT INTO "{S}".abs_tranche VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (tranche_id) DO UPDATE SET
                  deal_id             = EXCLUDED.deal_id,
                  class_name          = EXCLUDED.class_name,
                  seniority_rank      = EXCLUDED.seniority_rank,
                  cusip               = EXCLUDED.cusip,
                  interest_rate       = EXCLUDED.interest_rate,
                  interest_rate_basis = EXCLUDED.interest_rate_basis,
                  provenance          = EXCLUDED.provenance,
                  source              = EXCLUDED.source""", row)
        cur.executemany(f"""
            INSERT INTO "{S}".abs_servicer_report VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (deal_id, period) DO UPDATE SET
              pool_balance                   = EXCLUDED.pool_balance,
              note_balance                   = EXCLUDED.note_balance,
              oc_amount                      = EXCLUDED.oc_amount,
              oc_percent                     = EXCLUDED.oc_percent,
              oc_target                      = EXCLUDED.oc_target,
              published_delinquency_percent  = EXCLUDED.published_delinquency_percent,
              published_delinquency_trigger  = EXCLUDED.published_delinquency_trigger,
              published_trigger_occurred     = EXCLUDED.published_trigger_occurred,
              sixty_day_delinquent_balance   = EXCLUDED.sixty_day_delinquent_balance,
              cumulative_net_loss_percent    = EXCLUDED.cumulative_net_loss_percent,
              receivable_count               = EXCLUDED.receivable_count,
              delinquency_buckets            = EXCLUDED.delinquency_buckets,
              source_format                  = EXCLUDED.source_format,
              provenance                     = EXCLUDED.provenance,
              source                         = EXCLUDED.source
            """, report_rows)
        cur.executemany(f"""
            INSERT INTO "{S}".abs_repurchase VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (repurchase_id) DO UPDATE SET
              depositor_cik = EXCLUDED.depositor_cik,
              deal_id       = EXCLUDED.deal_id,
              form          = EXCLUDED.form,
              accession     = EXCLUDED.accession,
              filed_date    = EXCLUDED.filed_date,
              asset_count   = EXCLUDED.asset_count,
              note          = EXCLUDED.note,
              provenance    = EXCLUDED.provenance,
              source        = EXCLUDED.source""", repo_rows)
        conn.commit()
    print("  written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
