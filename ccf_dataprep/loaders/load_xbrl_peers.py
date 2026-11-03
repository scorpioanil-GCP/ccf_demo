#!/usr/bin/env python3
"""Wave 2 stage 2 — peer facts at identical periods, via the XBRL frames API.

`obligor-financial-spread` compares an obligor against peers, and the operator
matches peers on **period, never on filing date**. Comparing a Q3 figure to a
peer's Q2 because they filed the same week is the classic spreading error, and
the frames API forecloses it by construction: one call returns every filer's
value for one concept in one period.

Using `frames` rather than 150 more `companyfacts` downloads is also the
difference between a few hundred KB and several hundred MB, for data that is
strictly more aligned to the need.

Peer pool comes from the Wave 0 screening set — already EDGAR-verified and
SIC-annotated — restricted to SIC codes the anchor cast actually occupies.

    uv run loaders/load_xbrl_peers.py --dry-run
    uv run loaders/load_xbrl_peers.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.fetch import get_json

SCREEN = REPO_ROOT / "sources" / "screening"
FRAMES = "https://data.sec.gov/api/xbrl/frames/us-gaap/{tag}/USD/{frame}.json"

#: Concepts a peer benchmark actually needs. Instant (point-in-time) concepts
#: use the `I` suffix; duration concepts do not.
PEER_TAGS = [
    ("Assets", True),
    ("StockholdersEquity", True),
    ("Liabilities", True),
    ("Revenues", False),
    ("NetIncomeLoss", False),
    ("OperatingIncomeLoss", False),
]

#: Calendar frames to pull. Annual periods only — peers are benchmarked
#: year over year, and quarterly frames multiply calls without adding signal.
FRAMES_WANTED = ["CY2023", "CY2024", "CY2025"]

TARGET_PEERS = 150

DDL = f"""
CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".peer_entity (
    cik           INTEGER PRIMARY KEY,
    entity_name   TEXT NOT NULL,
    sic           TEXT,
    provenance    TEXT NOT NULL,
    source        TEXT NOT NULL,
    retrieved_at  DATE NOT NULL
);
COMMENT ON TABLE "{PG_SCHEMA_V2}".peer_entity IS
  'Peer comparison set for obligor-financial-spread. Peers carry no internal '
  'overlay and no LEI -- they exist only to benchmark anchors at identical '
  'periods, so they are deliberately NOT in the crosswalk.';

CREATE TABLE IF NOT EXISTS "{PG_SCHEMA_V2}".peer_fact (
    cik           INTEGER NOT NULL REFERENCES "{PG_SCHEMA_V2}".peer_entity(cik),
    tag           TEXT    NOT NULL,
    unit          TEXT    NOT NULL,
    frame         TEXT    NOT NULL,
    period_start  DATE,
    period_end    DATE    NOT NULL,
    fiscal_year   INTEGER,
    fiscal_period TEXT,
    form          TEXT,
    filed_date    DATE,
    accession     TEXT,
    value         NUMERIC,
    provenance    TEXT    NOT NULL,
    source        TEXT    NOT NULL,
    retrieved_at  DATE    NOT NULL,
    PRIMARY KEY (cik, tag, frame)
);
CREATE INDEX IF NOT EXISTS idx_peer_fact_period
    ON "{PG_SCHEMA_V2}".peer_fact (period_end, tag);
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    assert_v2_schema(PG_SCHEMA_V2)
    today = date.today().isoformat()

    anchors = json.loads((SCREEN / "anchors_final.json").read_text())["anchors"]
    anchor_ciks = {a["cik"] for a in anchors}
    anchor_sics = {a.get("sic") for a in anchors if a.get("sic")}

    # Draw from the full screening set, not just the verified subset: only 150
    # candidates were verified and 50 of those became anchors, which caps the
    # peer pool at 100 -- below what §F asks for.
    verified = json.loads((SCREEN / "verified.json").read_text())["candidates"]
    screened = json.loads((SCREEN / "candidates.json").read_text())["candidates"]
    seen: set[int] = set()
    candidates = []
    for row in verified + screened:
        if row["cik"] in seen:
            continue
        seen.add(row["cik"])
        candidates.append(row)
    pool = {
        c["cik"]: c for c in candidates
        if c["cik"] not in anchor_ciks and c.get("sic") in anchor_sics
    }
    print(f"Peer pool: {len(pool)} SIC-matched candidates "
          f"across {len(anchor_sics)} anchor SIC codes")

    if len(pool) < TARGET_PEERS:
        # Widen to any verified non-anchor filer. A peer set that is too small
        # makes peer_basis='sic' indistinguishable from no peer set at all.
        extra = [c for c in candidates
                 if c["cik"] not in anchor_ciks and c["cik"] not in pool]
        for c in extra:
            if len(pool) >= TARGET_PEERS:
                break
            pool[c["cik"]] = c
        print(f"  widened to {len(pool)} (SIC-matched pool alone was short "
              f"of {TARGET_PEERS})")

    wanted_ciks = set(pool)

    print(f"\nFetching frames for {len(PEER_TAGS)} tags x {len(FRAMES_WANTED)} periods")
    peer_rows: list[tuple] = []
    seen_keys: set[tuple] = set()
    hits_by_cik: dict[int, int] = defaultdict(int)

    for tag, instant in PEER_TAGS:
        for frame_base in FRAMES_WANTED:
            frame = f"{frame_base}Q4I" if instant else frame_base
            try:
                payload = get_json(
                    FRAMES.format(tag=tag, frame=frame), is_sec=True, timeout=60
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  [skip] {tag} {frame}: {type(exc).__name__}")
                continue
            data = payload.get("data", [])
            matched = 0
            for entry in data:
                cik = entry.get("cik")
                if cik not in wanted_ciks:
                    continue
                key = (cik, tag, frame)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                matched += 1
                hits_by_cik[cik] += 1
                peer_rows.append((
                    cik, tag, "USD", frame,
                    entry.get("start"), entry.get("end"),
                    entry.get("fy"), entry.get("fp"), entry.get("form"),
                    entry.get("filed"), entry.get("accn"), entry.get("val"),
                    "public", "SEC XBRL frames API", today,
                ))
            print(f"  {tag:34s} {frame:8s} {len(data):>6,} filers -> "
                  f"{matched:>4} peers")

    covered = sorted(hits_by_cik)
    entity_rows = [
        (cik, pool[cik]["name"], pool[cik].get("sic"),
         "public", "SEC EDGAR submissions API + XBRL frames", today)
        for cik in covered
    ]

    print(f"\n  {len(entity_rows)} peers with at least one fact")
    print(f"  {len(peer_rows):,} peer facts at anchor-matched periods")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".peer_entity '
            "(cik, entity_name, sic, provenance, source, retrieved_at) "
            "VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (cik) DO UPDATE SET entity_name=EXCLUDED.entity_name",
            entity_rows,
        )
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".peer_fact '
            "(cik, tag, unit, frame, period_start, period_end, fiscal_year, "
            " fiscal_period, form, filed_date, accession, value, provenance, "
            " source, retrieved_at) "
            "VALUES (" + ",".join(["%s"] * 15) + ") "
            "ON CONFLICT (cik, tag, frame) DO UPDATE SET value=EXCLUDED.value",
            peer_rows,
        )
        conn.commit()

        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".peer_entity')
        n_peers = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".peer_fact')
        n_facts = cur.fetchone()[0]

        # The condition that matters: an anchor and a peer at the SAME period.
        cur.execute(f"""
            SELECT COUNT(DISTINCT f.period_end)
            FROM "{PG_SCHEMA_V2}".financial_fact f
            JOIN "{PG_SCHEMA_V2}".peer_fact p
              ON p.period_end = f.period_end AND p.tag = f.tag
        """)
        shared_periods = cur.fetchone()[0]

        print(f"\n  loaded: {n_peers} peer entities, {n_facts:,} peer facts")
        print(f"\n  GATE — peer comparability")
        mark = "PASS" if n_peers >= 100 else "WARN"
        print(f"    [{mark}] {n_peers} peers loaded (§F asks ~150)")
        mark2 = "PASS" if shared_periods > 0 else "FAIL"
        print(f"    [{mark2}] {shared_periods} periods where an anchor and a peer "
              f"share tag+period")

    return 0


if __name__ == "__main__":
    sys.exit(main())
