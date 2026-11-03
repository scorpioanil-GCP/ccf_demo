#!/usr/bin/env python3
"""Wave 2 — load XBRL financial facts for the anchor cast.

`obligor-financial-spread` (T1) teaches attribute-level temporal validity
before any graph is involved. XBRL `companyfacts` is the right anchor for it
because every fact ships its own temporal metadata natively:

    end   period the figure describes    -> T
    filed date it became public          -> T
    accn  accession that asserted it     -> L

That is `T` and `L` at attribute granularity, for free, with no synthetic date
anywhere. A dashboard shows one number and implies one date; this shows three,
which is the whole lesson.

The §F gate is not a row count, and it is subtler than it first looks. It is
that **>= 3 obligors report the same period at a DIFFERENT VALUE under a later
accession**, so `basis=as-reported` and `basis=latest-restated` return
genuinely different numbers.

Counting distinct accessions alone would pass while proving nothing: XBRL
repeats prior-period figures as comparatives, so FY2023 revenue appears in the
FY2023 10-K and again in the FY2024 10-K under a second accession with an
identical value. On this cast that inflates the count from 116 real
restatements to 457 -- a gate that reads PASS while the `basis` parameter has
nothing to demonstrate.

    uv run loaders/load_xbrl_wave2.py --dry-run
    uv run loaders/load_xbrl_wave2.py

Idempotent: upserts on (cik, tag, unit, period_end, fiscal_period, accession).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.fetch import get_json

ANCHORS = REPO_ROOT / "sources" / "screening" / "anchors_final.json"
COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

#: US-GAAP tags a credit spread is built from. Alternates are listed because
#: filers tag the same economic concept differently — revenue in particular
#: moved to the ASC 606 tag, and older filings still carry the legacy one.
WANTED_TAGS = {
    "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet",
    "OperatingIncomeLoss", "NetIncomeLoss",
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "InterestExpense", "InterestExpenseDebt", "InterestExpenseNonoperating",
    "Assets", "Liabilities", "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "LongTermDebtNoncurrent", "LongTermDebtCurrent", "LongTermDebt",
    "DebtCurrent", "DebtLongtermAndShorttermCombinedAmount",
    "OperatingLeaseLiabilityNoncurrent",
    "EarningsBeforeInterestTaxesDepreciationAndAmortization",
}

#: Keep the load bounded. Eight periods is what §F asks for; taking everything
#: would multiply row count without making anything more demonstrable.
MAX_PERIODS_PER_TAG = 12

#: Periodic reports only. companyfacts also surfaces figures tagged in proxy
#: statements (DEF 14A), registration statements, and current reports; those
#: are not the filer's periodic financial statements and do not belong in a
#: credit spread. They also arrive without a fiscal period, which is part of
#: this table's key.
PERIODIC_FORMS = {
    "10-K", "10-K/A", "10-KT", "10-KT/A",
    "10-Q", "10-Q/A", "10-QT", "10-QT/A",
    "20-F", "20-F/A", "40-F", "40-F/A",
}

DDL = f"""
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".financial_fact (
    lei             CHAR(20) NOT NULL
                    REFERENCES "{PG_SCHEMA_V2}".legal_entity(lei),
    cik             INTEGER  NOT NULL,
    taxonomy        TEXT     NOT NULL,
    tag             TEXT     NOT NULL,
    unit            TEXT     NOT NULL,
    period_start    DATE,
    period_end      DATE     NOT NULL,
    fiscal_year     INTEGER,
    fiscal_period   TEXT,
    form            TEXT,
    filed_date      DATE     NOT NULL,
    accession       TEXT     NOT NULL,
    value           NUMERIC,
    provenance      TEXT     NOT NULL,
    source          TEXT     NOT NULL,
    retrieved_at    DATE     NOT NULL,
    PRIMARY KEY (cik, tag, unit, period_end, fiscal_period, accession)
);
COMMENT ON TABLE "{PG_SCHEMA_V2}".financial_fact IS
  'XBRL facts with native temporal metadata. period_end is what the figure '
  'describes (T), filed_date is when it became public (T), accession is which '
  'document asserted it (L). A restatement is the same (cik, tag, period_end) '
  'reported at a DIFFERENT VALUE under a later accession. A second accession '
  'with the same value is a comparative, not a restatement.';

CREATE INDEX IF NOT EXISTS idx_fact_lei_tag
    ON "{PG_SCHEMA_V2}".financial_fact (lei, tag, period_end);
CREATE INDEX IF NOT EXISTS idx_fact_period
    ON "{PG_SCHEMA_V2}".financial_fact (period_end);
CREATE INDEX IF NOT EXISTS idx_fact_restatement
    ON "{PG_SCHEMA_V2}".financial_fact (cik, tag, period_end, filed_date);
"""


def extract_facts(payload: dict, lei: str, cik: int, today: str) -> list[tuple]:
    rows: list[tuple] = []
    facts = payload.get("facts", {})
    for taxonomy, tags in facts.items():
        if taxonomy not in ("us-gaap", "ifrs-full"):
            continue
        for tag, tag_body in tags.items():
            if tag not in WANTED_TAGS:
                continue
            for unit, entries in (tag_body.get("units") or {}).items():
                # Newest first, so the period cap keeps recent history.
                entries = sorted(
                    entries, key=lambda e: (e.get("end") or "", e.get("filed") or ""),
                    reverse=True,
                )
                seen_periods: set[str] = set()
                for entry in entries:
                    end = entry.get("end")
                    accn = entry.get("accn")
                    filed = entry.get("filed")
                    form = entry.get("form")
                    if not (end and accn and filed and form):
                        continue
                    if form not in PERIODIC_FORMS:
                        continue
                    # fiscal_period is part of the primary key, so a missing
                    # one has to be an explicit sentinel rather than NULL.
                    fp = entry.get("fp") or "NA"
                    # Cap on distinct periods, not rows — a restatement adds a
                    # second accession for a period already counted, and
                    # dropping it would destroy the very condition §F needs.
                    if end not in seen_periods:
                        if len(seen_periods) >= MAX_PERIODS_PER_TAG:
                            continue
                        seen_periods.add(end)
                    rows.append((
                        lei, cik, taxonomy, tag, unit,
                        entry.get("start"), end,
                        entry.get("fy"), fp, form,
                        filed, accn, entry.get("val"),
                        "public", "SEC XBRL companyfacts API", today,
                    ))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0,
                        help="only process the first N anchors (debugging)")
    args = parser.parse_args()

    assert_v2_schema(PG_SCHEMA_V2)
    anchors = json.loads(ANCHORS.read_text())["anchors"]
    if args.limit:
        anchors = anchors[: args.limit]
    today = date.today().isoformat()

    print(f"Wave 2 — XBRL companyfacts for {len(anchors)} anchors\n")

    all_rows: list[tuple] = []
    failed: list[str] = []
    for i, anchor in enumerate(anchors, 1):
        cik = anchor["cik"]
        try:
            payload = get_json(COMPANYFACTS.format(cik=cik), is_sec=True, timeout=60)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{anchor['sec_name']} ({type(exc).__name__})")
            continue
        rows = extract_facts(payload, anchor["lei"], cik, today)
        all_rows.extend(rows)
        if i % 10 == 0:
            print(f"  ...{i}/{len(anchors)}  ({len(all_rows):,} facts so far)")

    print(f"\n  {len(all_rows):,} facts extracted from {len(anchors) - len(failed)} anchors")
    if failed:
        print(f"  {len(failed)} failed: {failed[:5]}")

    # Restatement census, computed before load so the gate is knowable early.
    #
    # A second accession for the same period is NOT by itself a restatement.
    # XBRL repeats prior-period figures as comparatives -- FY2023 revenue
    # appears in the FY2023 10-K and again in the FY2024 10-K, same value,
    # different accession. Counting those would pass the §F gate while
    # `basis=as-reported` and `basis=latest-restated` returned identical
    # numbers, which is precisely the "counted but not created" failure.
    #
    # A real restatement is the same (cik, tag, period) reported at a
    # DIFFERENT VALUE under a later accession.
    by_period: dict[tuple, dict[str, object]] = {}
    for r in all_rows:
        by_period.setdefault((r[1], r[3], r[6]), {})[r[11]] = r[12]

    reported_twice = {k: v for k, v in by_period.items() if len(v) > 1}
    genuinely_restated = {
        k: v for k, v in reported_twice.items()
        if len({str(val) for val in v.values()}) > 1
    }
    restated_ciks = {k[0] for k in genuinely_restated}

    print(f"  {len(reported_twice):,} (cik, tag, period) triples reported under "
          f">1 accession")
    print(f"  {len(genuinely_restated):,} of those carry a DIFFERENT VALUE "
          f"-- a real restatement")
    print(f"  {len(restated_ciks)} distinct obligors genuinely restated  "
          f"(§F floor 3)")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".financial_fact '
            "(lei, cik, taxonomy, tag, unit, period_start, period_end, "
            " fiscal_year, fiscal_period, form, filed_date, accession, value, "
            " provenance, source, retrieved_at) "
            "VALUES (" + ",".join(["%s"] * 16) + ") "
            "ON CONFLICT (cik, tag, unit, period_end, fiscal_period, accession) "
            "DO UPDATE SET value=EXCLUDED.value, retrieved_at=EXCLUDED.retrieved_at",
            all_rows,
        )
        conn.commit()

        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".financial_fact')
        print(f"\n  loaded: {cur.fetchone()[0]:,} rows in financial_fact")

        # DISTINCT value, not DISTINCT accession — see the note above.
        cur.execute(f"""
            SELECT COUNT(DISTINCT cik) FROM (
                SELECT cik, tag, period_end
                FROM "{PG_SCHEMA_V2}".financial_fact
                GROUP BY cik, tag, period_end
                HAVING COUNT(DISTINCT accession) > 1
                   AND COUNT(DISTINCT value) > 1
            ) t
        """)
        n_restated = cur.fetchone()[0]

        cur.execute(f"""
            SELECT COUNT(DISTINCT (lei, period_end))
            FROM "{PG_SCHEMA_V2}".financial_fact
        """)
        n_lei_periods = cur.fetchone()[0]

        cur.execute(f"""
            SELECT e.legal_name, f.tag, f.period_end,
                   COUNT(DISTINCT f.accession) AS accessions,
                   MIN(f.value) AS min_val, MAX(f.value) AS max_val
            FROM "{PG_SCHEMA_V2}".financial_fact f
            JOIN "{PG_SCHEMA_V2}".legal_entity e USING (lei)
            GROUP BY e.legal_name, f.tag, f.period_end
            HAVING COUNT(DISTINCT f.accession) > 1
               AND COUNT(DISTINCT f.value) > 1
            ORDER BY accessions DESC LIMIT 6
        """)
        samples = cur.fetchall()

        print(f"\n  GATE — restatements")
        mark = "PASS" if n_restated >= 3 else "FAIL"
        print(f"    [{mark}] {n_restated} obligors with 2+ accessions for one period "
              f"(§F floor 3)")
        for name, tag, period, n, lo, hi in samples:
            print(f"      {name[:26]:28s} {tag[:28]:30s} {period} x{n}  "
                  f"{lo:,.0f} -> {hi:,.0f}")
        print(f"    {n_lei_periods:,} distinct (entity, period) pairs")

        if n_restated < 3:
            print("\n  Natural sample lacks restatements — Q019 permits engineering "
                  "the subset, but that must be labelled `synthetic — engineered`.")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
