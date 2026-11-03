#!/usr/bin/env python3
"""Replay the `context_debt` rows Wave 6's TRUNCATE destroyed.

    uv run loaders/restore_context_debt.py --dry-run
    uv run loaders/restore_context_debt.py

`ccf_v2.context_debt` is an estate-wide register. Until 2026-08-22
`loaders/load_anchors_wave6.py` opened its write with an unconditional
`TRUNCATE`, so any re-run of it destroyed Wave 10's `subject_kind='person'`
rows and Wave 11a's `subject_kind='rating_action'` rows. The live table was
found holding 1 row where the Wave 11a artifact expects 169. The loader is
fixed (`DEBT_OWNED_BY_WAVE6`); this restores what the defect removed.

**Both populations are pure functions of tracked artifacts**, which is why a
replay is possible at all and why it does not require a re-fetch:

    wave11a_rating_actions.json  every record with confirmed=false, carrying
                                 its own accession and reason
    wave10_persons.json          natural-person roster members ...
    wave10_name_variants.json    ... minus those with a located rendering

**The circularity, stated rather than hidden.**
`validators/artifact_reproduces_store.py` proves the store matches the
artifact by reading the artifact's own `reason` string. Replaying that same
string into the store therefore makes that check pass BY CONSTRUCTION for
these rows -- it can no longer detect a store/artifact divergence it was
partly there to catch. That is inherent to any replay and was accepted
knowingly rather than discovered later.

What claws back the lost information is `--accept-drift`. This script refuses
to replay an artifact whose `reason` text no longer matches the constants the
generators would emit today, so the artifact is checked against live code
before it is allowed to define the store. Note this is deliberately the
OPPOSITE choice from the validator, which imports no constant on purpose
(known-issues.md §9.1): a validator that hard-couples reports false
divergence, whereas a replay that does not hard-couple silently reinstates a
stale sentence. Different jobs, different coupling.

This script touches only rows with `subject_kind IS NOT NULL`. Wave 6's
covenant-shaped population is never read or written here.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from generators.fetch_rating_actions import REASON_SEARCHED, REASON_UNSEARCHED
from loaders.load_postgres_wave10 import REASON_NO_RENDERING

SCREEN = REPO_ROOT / "sources" / "screening"


def _load(name: str, key: str) -> list[dict]:
    return json.loads((SCREEN / name).read_text())[key]


def rating_action_rows() -> tuple[list[tuple], list[str]]:
    """Wave 11a: one row per UNCONFIRMED candidate, keyed by its accession.

    Mirrors `generators/fetch_rating_actions.py`'s own
    `debt_rows.append((accession, None, reason, accession))` exactly.
    """
    actions = _load("wave11a_rating_actions.json", "rating_actions")
    rows, drift = [], []
    for r in actions:
        if r["confirmed"]:
            continue
        expected = REASON_SEARCHED if r["searched"] else REASON_UNSEARCHED
        if r["reason"] != expected:
            drift.append(f"{r['accession']}: reason does not match "
                         f"{'REASON_SEARCHED' if r['searched'] else 'REASON_UNSEARCHED'}")
        rows.append((r["accession"], None, r["reason"], "rating_action",
                     r["accession"]))
    return rows, drift


def person_rows() -> tuple[list[tuple], list[str]]:
    """Wave 10: one row per natural roster member with NO located rendering.

    Mirrors `loaders/load_postgres_wave10.py`'s own predicate --
    `owner_kind == "natural" and person_key not in {v["person_key"] ...}`.
    """
    persons = _load("wave10_persons.json", "persons")
    variants = _load("wave10_name_variants.json", "variants")
    rendered = {v["person_key"] for v in variants}
    rows = [(None, None, REASON_NO_RENDERING, "person", p["person_key"])
            for p in persons
            if p["owner_kind"] == "natural" and p["person_key"] not in rendered]
    return rows, []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--accept-drift", action="store_true",
                    help="replay even though an artifact's reason text no "
                         "longer matches the generator constants")
    args = ap.parse_args()

    print("Restore context_debt — replay from tracked artifacts\n")

    ratings, drift = rating_action_rows()
    persons, _ = person_rows()
    print(f"  rating_action rows (Wave 11a)   {len(ratings):>5}")
    print(f"  person rows        (Wave 10)    {len(persons):>5}")

    if drift:
        print(f"\n  {len(drift)} artifact reason(s) have DRIFTED from the "
              f"generator constants:")
        for d in drift[:5]:
            print(f"    {d}")
        if not args.accept_drift:
            print("\n  REFUSING to replay. The artifact would define the "
                  "store with text\n  the generator no longer produces. "
                  "Re-run the generator, or pass\n  --accept-drift if the "
                  "artifact is knowingly the authority here.")
            return 1
        print("\n  --accept-drift: replaying the artifact text anyway.")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT subject_kind, count(*) FROM "{PG_SCHEMA_V2}"'
                    ".context_debt GROUP BY 1 ORDER BY 1")
        print("\n  before:")
        for kind, n in cur.fetchall():
            print(f"    {kind or '(covenant — Wave 6, untouched)':<40} {n:>5}")

        if args.dry_run:
            print("\n  DRY RUN — nothing written.")
            return 0

        # Same ON CONFLICT form as the two writers this replays, so a re-run
        # refreshes `reason` rather than duplicating or silently keeping a
        # stale sentence. The conflict target repeats ux_context_debt_subject's
        # own WHERE predicate because it is a PARTIAL unique index and
        # Postgres cannot otherwise infer it as the arbiter.
        cur.executemany(
            f'INSERT INTO "{PG_SCHEMA_V2}".context_debt '
            "(accession, covenant_type, reason, recorded_at, subject_kind, "
            "subject_key) VALUES (%s,%s,%s,current_date,%s,%s) "
            "ON CONFLICT (subject_kind, subject_key) "
            "WHERE subject_kind IS NOT NULL "
            "DO UPDATE SET reason = EXCLUDED.reason",
            ratings + persons)
        conn.commit()

        cur.execute(f'SELECT subject_kind, count(*) FROM "{PG_SCHEMA_V2}"'
                    ".context_debt GROUP BY 1 ORDER BY 1")
        print("\n  after:")
        for kind, n in cur.fetchall():
            print(f"    {kind or '(covenant — Wave 6, untouched)':<40} {n:>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
