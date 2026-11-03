#!/usr/bin/env python3
"""Wave 17 Task 15 — load the SAR confidentiality classification into the
departmental SQLite store.

## Why this table lives in SQLite, and only here

SQLite owns the departmental slice: restricted lists, trackers, local
workbooks — small, locally-maintained systems the fabric must reach to
enforce an enterprise-critical policy read. A SAR's confidentiality
classification is exactly that: the fact of WHO may know a filing exists.
If the classification also lived in Postgres, nothing would force the fabric
to reach the departmental store, and the architectural point this product
exists to demonstrate would collapse. `validators/test_aml_typology.py`'s
`test_sar_classification_lives_only_in_sqlite` is the single-writer boundary
for this element; this loader is the only thing permitted to write it, and
it never touches Postgres.

## Reads

`sources/screening/wave17_sar_records.json`
(`generators/generate_sar_records.py`) — a digest-selected SUBSET of the
engineered cases (coordinator ruling, fix rounds 2-3 — see the generator's
own docstring for why coverage is deliberately partial, not 1:1). One
narrative + classification per case that actually files.

Fix round 2 selected that subset by aggregate transaction exposure and fix
round 3 REMOVED that, because materiality was recoverable from the alert
`trigger` — the disclosure route the confidentiality floor exists to police.
`select_filed_case_ids` now sorts each typology's cases by
`sha256(salt:case_id)`. Named here because the superseded account is the
unsafe one, and a reader who audits against it audits the wrong thing.

## Idempotent, and reconciled

`INSERT ... ON CONFLICT(sar_id) DO UPDATE`, keyed on `sar_id` — a
content-derived id (see the generator's own docstring), never a row's
position. Re-running this loader against the same input artifact leaves
every value unchanged; `validators/test_aml_typology.py`'s
`test_task15_sqlite_load_is_idempotent_on_a_named_classification_value`
proves this by VALUE, not by row count.

The table is also RECONCILED to the artifact, not merely appended to: any
`sar_id` present in the table but absent from the current artifact is
deleted. This loader is the table's only writer, and the artifact is
authoritative for the full SAR set that should exist at any time -- a case
that used to file (under an older, wider selection) and no longer does
must not leave a phantom row a query could still find.

    uv run loaders/load_sqlite_wave17.py --dry-run
    uv run loaders/load_sqlite_wave17.py
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from ccf.config import REPO_ROOT, SQLITE_PATH

ARTIFACT = REPO_ROOT / "sources" / "screening" / "wave17_sar_records.json"

DDL = """
CREATE TABLE IF NOT EXISTS sar_classification (
    sar_id                  TEXT PRIMARY KEY,
    alert_id                 TEXT NOT NULL,
    classification            TEXT NOT NULL,
    visible_to_perspectives    TEXT NOT NULL,
    provenance                  TEXT NOT NULL
);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not ARTIFACT.exists():
        print(f"missing {ARTIFACT} -- run "
              f"generators/generate_sar_records.py first")
        return 1

    doc = json.loads(ARTIFACT.read_text())
    sars = doc["sars"]

    all_perspectives = {"l1", "l2", "examiner"}
    blind = set(all_perspectives)
    for r in sars:
        blind &= set(r["visible_to_perspectives"])
    excluded = all_perspectives - blind

    print("Wave 17 Task 15 — SQLite load: sar_classification\n")
    print(f"  {len(sars)} SAR records")
    for typ in sorted({r["typology_id"] for r in sars}):
        n = sum(1 for r in sars if r["typology_id"] == typ)
        print(f"    {typ:<12} {n:>2}")
    print(f"  perspective(s) blind to every SAR: {sorted(excluded) or 'NONE'}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(SQLITE_PATH)
    con.execute(DDL)

    rows = [
        (
            r["sar_id"],
            r["alert_id"],
            r["classification"],
            json.dumps(r["visible_to_perspectives"], sort_keys=True),
            r["provenance"],
        )
        for r in sars
    ]
    con.executemany(
        "INSERT INTO sar_classification "
        "(sar_id, alert_id, classification, visible_to_perspectives, provenance) "
        "VALUES (?,?,?,?,?) "
        "ON CONFLICT(sar_id) DO UPDATE SET "
        "alert_id=excluded.alert_id, "
        "classification=excluded.classification, "
        "visible_to_perspectives=excluded.visible_to_perspectives, "
        "provenance=excluded.provenance",
        rows,
    )

    # Reconcile, don't just append. This table's only writer is this
    # loader, and the artifact is authoritative for the FULL set of SARs
    # that should exist -- not a monotonically-growing log of every SAR
    # that ever existed. Coordinator ruling (fix rounds 2-3): SAR
    # coverage went from 1:1 with the cases to a digest-selected subset,
    # so a row for a case that no longer files (or a stale sar_id from a previous
    # numbering) must be removed, not left behind as a phantom record a
    # later query could still find. A plain upsert-only loader would leave
    # exactly that residue on this kind of shrink.
    current_ids = [r["sar_id"] for r in sars]
    placeholders = ",".join("?" for _ in current_ids)
    deleted = con.execute(
        f"DELETE FROM sar_classification WHERE sar_id NOT IN ({placeholders})",
        current_ids,
    ).rowcount
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM sar_classification").fetchone()[0]
    print(f"\n  loaded: {total} sar_classification rows "
          f"({deleted} stale row(s) reconciled away)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
