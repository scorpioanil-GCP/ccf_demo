#!/usr/bin/env python3
"""Wave 4 — load facility terms into Postgres `ccf_v2.facility`.

Public elements come from EX-10 extraction, pre-parsed at build time into
structured rows. Internal elements are invented because they are bank-internal
by nature: `facility-terms-snapshot` §C marks outstanding balance, undrawn
availability, internal facility rating, and the facility-to-LEI crosswalk as
`synthetic — internal`.

Two things this load takes seriously.

**The TTL anchor.** §A says this product exists to teach `ttl_anchor`. A
facility's terms do not decay on a clock; they are valid until amended. So
`expires_at` derives from the agreement's effective date, not from request
time, and that only works if `effective_date` is actually populated — which is
why it is required rather than nullable.

**Mixed volatility is surfaced, not flattened.** §E splits a 540-day signal
(structural terms) from a 1-day signal (outstanding balance). Storing them in
one row without marking the asymmetry is what §6.4 Temporal Validation refuses
to assemble, so balance carries its own `balance_as_of`.

    uv run loaders/load_facilities_wave4.py --dry-run
    uv run loaders/load_facilities_wave4.py

Idempotent: upserts on facility_id, which is derived deterministically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from datetime import date, datetime, timedelta

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.memo_grade import memo_grade_leis

SCREEN = REPO_ROOT / "sources" / "screening"
TARGET_FACILITIES = 45
SEED = 20260817

DDL = f"""
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".facility (
    facility_id          TEXT PRIMARY KEY,
    borrower_lei         CHAR(20) NOT NULL
                         REFERENCES "{PG_SCHEMA_V2}".legal_entity(lei),
    facility_type        TEXT NOT NULL,
    commitment_amount    NUMERIC,
    currency             CHAR(3) NOT NULL DEFAULT 'USD',
    effective_date       DATE,
    maturity_date        DATE,
    administrative_agent TEXT,
    syndicated           BOOLEAN NOT NULL DEFAULT false,
    amendment_count      INTEGER NOT NULL DEFAULT 0,
    is_amended_restated  BOOLEAN NOT NULL DEFAULT false,
    pricing_grid         JSONB,
    -- synthetic - internal, bank-internal by nature
    outstanding_balance  NUMERIC,
    undrawn_availability NUMERIC,
    balance_as_of        DATE,
    internal_risk_rating TEXT,
    -- lineage back to the filed exhibit
    source_accession     TEXT,
    source_document      TEXT,
    source_offsets       JSONB,
    provenance_public    TEXT NOT NULL,
    provenance_internal  TEXT NOT NULL,
    source               TEXT NOT NULL,
    retrieved_at         DATE NOT NULL
);
COMMENT ON TABLE "{PG_SCHEMA_V2}".facility IS
  'Facility terms extracted from EX-10 at BUILD TIME into structured rows. '
  'The source document is not addressable until MongoDB arrives in Wave 6 -- '
  'a T1 product reaching into a document would silently be a T4 product. '
  'expires_at derives from effective_date (ttl_anchor: from_entity_freshness), '
  'never from request time. outstanding_balance carries its own balance_as_of '
  'because a 1-day signal and a 540-day signal must not share one timestamp.';

CREATE INDEX IF NOT EXISTS idx_facility_borrower
    ON "{PG_SCHEMA_V2}".facility (borrower_lei);
CREATE INDEX IF NOT EXISTS idx_facility_amended
    ON "{PG_SCHEMA_V2}".facility (amendment_count) WHERE amendment_count > 0;
"""

TYPE_LABEL = {
    "revolver": "Revolving Credit Facility",
    "term_a": "Term Loan A",
    "term_b": "Term Loan B",
    "term_loan": "Term Loan",
    "delayed_draw": "Delayed Draw Term Loan",
}

RATINGS = ["1A", "2A", "2B", "3A", "3B", "4A", "4B", "5"]


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def facility_id(accession: str, ftype: str) -> str:
    """Deterministic so re-runs upsert rather than duplicate."""
    digest = hashlib.sha256(f"{accession}:{ftype}".encode()).hexdigest()[:6]
    return f"FAC-{digest.upper()}"


def score(doc: dict) -> int:
    """Prefer documents where extraction was most complete."""
    return (
        (3 if doc["facility_types"] else 0)
        + (2 if doc["commitment_amounts"] else 0)
        + (2 if doc["administrative_agent"] else 0)
        + (1 if doc["maturity_date"] else 0)
        + (2 if doc["effective_date"] else 0)
        + (1 if len(doc["pricing_grid_tiers"]) >= 3 else 0)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    assert_v2_schema(PG_SCHEMA_V2)
    today = date.today()

    docs = json.loads((SCREEN / "facilities_extracted.json").read_text())["documents"]
    docs = [d for d in docs if d["facility_types"] and d["effective_date"]]
    docs.sort(key=score, reverse=True)

    # Wave 13a. `credit-memo-context` §F wants ~20 obligors covered across all
    # five prerequisite products, and exposure was the binding leg at 15 --
    # not because extraction failed but because TARGET_FACILITIES truncates a
    # score-sorted list. So the cap now bounds the GENERAL fill only, and a
    # memo-grade obligor is always admitted.
    #
    # T1-R2 (Wave 18): this used to warn against re-sorting `docs`, because
    # every row's random draws came from ONE positional stream
    # (`random.Random(SEED)`, drawn in append order) -- so changing which
    # facility landed at position N changed what N drew, silently, for
    # every row from the first divergence onward. That is exactly what
    # happened here: repairing extract_agent()'s regex (Task 1) made two
    # documents' scores drop and the eligible set grow, sort order diverged
    # at position 22 of 30, and every facility from there on redrew a new
    # outstanding_balance even though nothing about ITS own data had
    # changed. Measured, not hypothetical -- see the Task 1 fix report.
    #
    # The fix is CONTENT-keyed draws, not a promise to never re-sort: each
    # row now draws from `random.Random(f"{SEED}:{fid}")`, seeded by its own
    # deterministic facility_id, so a given facility's balance/rating/
    # balance_as_of depend only on SEED and that facility_id -- never on
    # `docs`' sort order, iteration order, or what else happens to be in the
    # eligible set. Re-sorting, or growing/shrinking the eligible set, can
    # no longer perturb an unrelated row.
    memo_grade = memo_grade_leis()

    rows: list[tuple] = []
    seen_ids: set[str] = set()
    type_counts: dict[str, int] = {}

    for doc in docs:
        if len(rows) >= TARGET_FACILITIES and doc.get("lei") not in memo_grade:
            continue
        amounts = doc["commitment_amounts"]
        eff = parse_date(doc["effective_date"]["value"])
        mat = parse_date(doc["maturity_date"]["value"]) if doc["maturity_date"] else None

        # One agreement commonly defines a revolver AND term tranches; each
        # becomes its own facility row, which is what the product anchors on.
        for idx, (ftype, offset) in enumerate(
            sorted(doc["facility_types"].items(), key=lambda kv: kv[1])
        ):
            if len(rows) >= TARGET_FACILITIES and doc.get("lei") not in memo_grade:
                break
            fid = facility_id(doc["accession"], ftype)
            if fid in seen_ids:
                continue
            seen_ids.add(fid)

            # T1-R2: content-keyed, not positional -- see the comment above
            # the loop. Every draw for THIS row comes from a generator
            # seeded by SEED plus this row's own deterministic facility_id,
            # so it cannot be perturbed by another row's presence, absence,
            # or position.
            row_rng = random.Random(f"{SEED}:{fid}")

            commitment = amounts[idx]["value"] if idx < len(amounts) else (
                amounts[0]["value"] if amounts else None
            )
            # Engineered: a drawn proportion, and undrawn as the remainder.
            drawn_pct = row_rng.uniform(0.15, 0.85) if ftype == "revolver" else \
                row_rng.uniform(0.85, 1.0)
            outstanding = round(commitment * drawn_pct) if commitment else None
            undrawn = (commitment - outstanding) if commitment and outstanding else None

            tiers = doc["pricing_grid_tiers"]
            grid = (
                {
                    "basis": "Consolidated Leverage Ratio",
                    "tiers": [
                        {"leverage_le": t, "margin_bps": 125 + 25 * i}
                        for i, t in enumerate(tiers[:5])
                    ],
                    "provenance": "public — tier thresholds from EX-10; "
                                  "margins synthetic — internal",
                }
                if len(tiers) >= 3 else None
            )

            offsets = {
                "facility_type": offset,
                "effective_date": doc["effective_date"]["offset"],
            }
            if doc["maturity_date"]:
                offsets["maturity_date"] = doc["maturity_date"]["offset"]
            if doc["administrative_agent"]:
                offsets["administrative_agent"] = doc["administrative_agent"]["offset"]
            if amounts:
                offsets["commitment_amount"] = amounts[min(idx, len(amounts) - 1)]["offset"]

            amend_count = (
                doc["amendment_number"]["value"] if doc["amendment_number"]
                else (1 if doc["is_amended_and_restated"] else 0)
            )

            rows.append((
                fid, doc["lei"], TYPE_LABEL.get(ftype, ftype),
                commitment, "USD", eff, mat,
                doc["administrative_agent"]["name"] if doc["administrative_agent"] else None,
                doc["syndicated"], amend_count, doc["is_amended_and_restated"],
                json.dumps(grid) if grid else None,
                outstanding, undrawn,
                (today - timedelta(days=row_rng.randint(0, 3))).isoformat(),
                row_rng.choice(RATINGS),
                doc["accession"], doc["document"], json.dumps(offsets),
                "public", "synthetic — internal",
                "SEC EDGAR EX-10 credit agreement (build-time extraction)",
                today.isoformat(),
            ))
            type_counts[ftype] = type_counts.get(ftype, 0) + 1

    amended = sum(1 for r in rows if r[9] > 0 or r[10])
    syndicated = sum(1 for r in rows if r[8])
    with_grid = sum(1 for r in rows if r[11])
    with_mat = sum(1 for r in rows if r[6])

    print(f"Wave 4 — facility load into {PG_SCHEMA_V2}\n")
    print(f"  facilities          {len(rows):>4}   (§F asks ~40)")
    print(f"  types               {type_counts}")
    print(f"  with amendment      {amended:>4}   (§F floor 12)")
    print(f"  syndicated          {syndicated:>4}   (§F asks ~4)")
    print(f"  pricing grid 3+     {with_grid:>4}")
    print(f"  maturity date known {with_mat:>4}   (deterministic gap)")
    print(f"  distinct borrowers  {len({r[1] for r in rows}):>4}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".facility '
            "(facility_id, borrower_lei, facility_type, commitment_amount, "
            " currency, effective_date, maturity_date, administrative_agent, "
            " syndicated, amendment_count, is_amended_restated, pricing_grid, "
            " outstanding_balance, undrawn_availability, balance_as_of, "
            " internal_risk_rating, source_accession, source_document, "
            " source_offsets, provenance_public, provenance_internal, source, "
            " retrieved_at) "
            "VALUES (" + ",".join(["%s"] * 23) + ") "
            "ON CONFLICT (facility_id) DO UPDATE SET "
            "commitment_amount=EXCLUDED.commitment_amount, "
            "outstanding_balance=EXCLUDED.outstanding_balance, "
            "balance_as_of=EXCLUDED.balance_as_of, "
            "retrieved_at=EXCLUDED.retrieved_at, "
            # Task 1 fix, Wave 18: this loader is the SOLE writer of both
            # columns repo-wide (grep -rln administrative_agent loaders/
            # generators/ turns up only this file and extract_facilities.py),
            # so refreshing them on conflict clobbers nothing another wave
            # owns. Without this, extract_facilities.py's repaired values
            # never reach Postgres for a facility_id that already existed --
            # confirmed against real data before this line was added.
            "administrative_agent=EXCLUDED.administrative_agent, "
            "source_offsets=EXCLUDED.source_offsets",
            rows,
        )
        conn.commit()

        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".facility')
        n = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".facility '
                    "WHERE amendment_count > 0 OR is_amended_restated")
        n_amend = cur.fetchone()[0]
        cur.execute(f"""
            SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".facility f
            LEFT JOIN "{PG_SCHEMA_V2}".legal_entity e ON e.lei = f.borrower_lei
            WHERE e.lei IS NULL""")
        orphans = cur.fetchone()[0]

        print(f"\n  loaded: {n} facilities, {n_amend} amended, {orphans} orphans")
        if orphans:
            print("  FAIL: facilities reference a borrower not in legal_entity")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
