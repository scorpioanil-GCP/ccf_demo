#!/usr/bin/env python3
"""Wave 13a stage 1b — load the real SIC cohorts and their thinness denominators.

    uv run loaders/load_peer_cohorts_wave13a.py --dry-run
    uv run loaders/load_peer_cohorts_wave13a.py

Extends `peer_entity` / `peer_fact` with the cohort members
`generators/fetch_peer_cohorts.py` enumerated from EDGAR, and adds
`peer_cohort` -- the per-`(sic, tag, frame)` denominator table without which
peer thinness cannot be computed honestly.

**Why a denominator table rather than a computed count.** Thinness is
`1 - actual/expected_active`, and `expected_active` is NOT derivable from
`peer_fact` alone: a filer that reported nothing in a period leaves no row, so
counting rows recovers `actual` and loses `expected`. Storing only `peer_fact`
would silently redefine thinness as "1 - actual/actual" = 0 for every cohort --
a debt term that is identically zero for any input, which is precisely the
defect shape Wave 12 shipped seven times (known-issues.md §12). The
denominator has to be recorded at measurement time or it is gone.

Additive and idempotent: no DELETE, no TRUNCATE, upsert-only. `peer_entity`
rows Wave 2 loaded are updated in place, never removed -- and this loader must
never acquire a TRUNCATE, for the reason known-issues.md §12.8 records.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, assert_v2_schema, pg_connect
from ccf.fetch import get_json
from generators.fetch_peer_cohorts import ARTIFACT, frame_for
from loaders.load_xbrl_peers import FRAMES, FRAMES_WANTED, PEER_TAGS

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".peer_cohort (
    sic              TEXT    NOT NULL,
    tag              TEXT    NOT NULL,
    frame            TEXT    NOT NULL,
    sic_cohort_total INTEGER NOT NULL,
    expected_active  INTEGER NOT NULL,
    actual           INTEGER NOT NULL,
    thinness         NUMERIC,
    provenance       TEXT    NOT NULL,
    source           TEXT    NOT NULL,
    retrieved_at     DATE    NOT NULL,
    PRIMARY KEY (sic, tag, frame),
    -- The bound is a constraint, not a convention. A single-concept
    -- denominator produced actual=3 against expected=2 on SIC 8700 CY2023Q4I,
    -- i.e. -50% thinness; the union denominator makes that unrepresentable
    -- and this CHECK makes a regression to it fail the load rather than the
    -- review.
    CONSTRAINT peer_cohort_actual_bounded CHECK (actual <= expected_active),
    CONSTRAINT peer_cohort_thinness_unit  CHECK (thinness IS NULL
                                                 OR (thinness >= 0 AND thinness < 1))
);
COMMENT ON TABLE "{S}".peer_cohort IS
  'Per (sic, tag, frame) peer-cohort denominators for credit-memo-context '
  'peer-thinness Context Debt. expected_active is the EDGAR SIC cohort '
  'intersected with filers reporting ANY tracked concept in that period; '
  'actual is those reporting THIS concept. Not derivable from peer_fact, '
  'which records only what was reported.';
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    assert_v2_schema(S)
    today = date.today().isoformat()

    art = json.loads(ARTIFACT.read_text())
    cohorts = {k: set(v) for k, v in art["sic_cohorts"].items()}
    wanted = set().union(*cohorts.values()) if cohorts else set()

    print("Wave 13a — real peer cohorts into Postgres\n")
    print(f"  {len(cohorts)} SIC cohorts, {len(wanted):,} distinct filers")

    print(f"\nFetching frames for {len(PEER_TAGS)} concepts x "
          f"{len(FRAMES_WANTED)} periods")
    entities: dict[int, tuple] = {}
    facts: list[tuple] = []
    sic_of = {cik: sic for sic, ciks in cohorts.items() for cik in ciks}

    for tag, instant in PEER_TAGS:
        for base in FRAMES_WANTED:
            frame = frame_for(tag, instant, base)
            try:
                payload = get_json(FRAMES.format(tag=tag, frame=frame),
                                   is_sec=True, timeout=90)
            except Exception as exc:  # noqa: BLE001 — one concept failing is a
                # fact about that concept, not grounds to abort the load.
                print(f"  [skip] {tag} {frame}: {type(exc).__name__}")
                continue
            hit = 0
            for e in payload.get("data", []):
                cik = e.get("cik")
                if cik not in wanted:
                    continue
                hit += 1
                entities.setdefault(cik, (
                    cik, (e.get("entityName") or f"CIK {cik}").strip(),
                    sic_of.get(cik), "public",
                    "SEC EDGAR browse-edgar SIC index + XBRL frames API", today))
                facts.append((
                    cik, tag, "USD", frame, e.get("start"), e.get("end"),
                    e.get("fy"), e.get("fp"), e.get("form"), e.get("filed"),
                    e.get("accn"), e.get("val"), "public",
                    "SEC XBRL frames API", today))
            print(f"  {tag:<24}{frame:<10}{hit:>6,} cohort filers")

    cohort_rows = [
        (r["sic"], r["tag"], r["frame"], r["sic_cohort_total"],
         r["expected_active"], r["actual"], r["thinness"], "public",
         "SEC EDGAR browse-edgar SIC index + XBRL frames API", today)
        for r in art["cohorts"]
    ]

    print(f"\n  {len(entities):,} cohort filers with >= 1 fact")
    print(f"  {len(facts):,} peer facts")
    print(f"  {len(cohort_rows)} (sic, tag, frame) denominator rows")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{S}".peer_entity '
            "(cik, entity_name, sic, provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (cik) DO UPDATE SET "
            "entity_name=EXCLUDED.entity_name, sic=COALESCE(EXCLUDED.sic, "
            f'"{S}".peer_entity.sic)',
            list(entities.values()))
        cur.executemany(
            f'INSERT INTO "{S}".peer_fact '
            "(cik, tag, unit, frame, period_start, period_end, fiscal_year, "
            " fiscal_period, form, filed_date, accession, value, provenance, "
            " source, retrieved_at) VALUES (" + ",".join(["%s"] * 15) + ") "
            "ON CONFLICT (cik, tag, frame) DO UPDATE SET value=EXCLUDED.value",
            facts)
        cur.executemany(
            f'INSERT INTO "{S}".peer_cohort '
            "(sic, tag, frame, sic_cohort_total, expected_active, actual, "
            " thinness, provenance, source, retrieved_at) "
            "VALUES (" + ",".join(["%s"] * 10) + ") "
            "ON CONFLICT (sic, tag, frame) DO UPDATE SET "
            "sic_cohort_total=EXCLUDED.sic_cohort_total, "
            "expected_active=EXCLUDED.expected_active, "
            "actual=EXCLUDED.actual, thinness=EXCLUDED.thinness",
            cohort_rows)
        conn.commit()

        for t in ("peer_entity", "peer_fact", "peer_cohort"):
            cur.execute(f'SELECT count(*) FROM "{S}".{t}')
            print(f"  {t:<14} {cur.fetchone()[0]:>8,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
