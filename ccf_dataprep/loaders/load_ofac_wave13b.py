#!/usr/bin/env python3
"""Wave 13b Task 1 — load the OFAC sanctions lists into Postgres.

§C: *"Sanctions lists — OFAC SDN + Consolidated (daily XML/CSV)"* -> **Postgres**,
provenance `public`. Reads `sources/screening/wave13b_ofac.json`, written by
`generators/fetch_ofac.py`.

Two tables:

    sanctions_entry   one row per listed party (19,730)
    sanctions_name    one row per NAME — primary plus every a.k.a. (45,511)

## Why names are a separate table

Screening matches on names, and a listed party has many. Keeping aliases in an
array column would force every screening query to unnest before it could use
an index, and would lose OFAC's own `strong`/`weak` judgement per alias — a
weak alias matching is materially less evidence than a strong one, and §F's
"below certainty" band depends on that distinction being available.

`name_norm` is computed by `ccf.names.normalize`, the same function the
resolution layer scores with. See that module for why it is shared.

## Delisting, and the guard on it

OFAC publishes daily and parties come off the list. A reload therefore has to
be able to REMOVE rows, or the table becomes a union of every snapshot ever
loaded and a delisted party stays sanctioned forever. This loader deletes
entries absent from the artifact — scoped to the lists the artifact actually
carries, since it is the sole writer of these two tables.

That delete is the dangerous operation in this file, so it is capped: if a run
would remove more than `MAX_DELIST_FRACTION` of the existing rows, it aborts.
A truncated or half-written artifact is far more likely than OFAC delisting a
fifth of the world in one day, and the cheap failure is the one that stops.
Override deliberately with `--allow-mass-delisting` when a genuine bulk
removal happens.

    uv run loaders/load_ofac_wave13b.py --dry-run
    uv run loaders/load_ofac_wave13b.py

Idempotent: both upserts key on their natural primary key and set EVERY
non-key column on conflict.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.names import normalize

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_ofac.json"

#: Abort a reload that would delete more than this share of existing entries.
MAX_DELIST_FRACTION = 0.20

#: `name_uid = 0` is reserved for the primary name. OFAC alias uids start at 1,
#: asserted at build time rather than assumed.
PRIMARY_NAME_UID = 0

#: The delisting predicate, as ONE string used by both the loader and
#: `validators/test_sanctions_delisting.py`. A test carrying its own copy of
#: this WHERE clause would verify the test's scoping rather than the loader's,
#: and the two could drift apart without either failing.
#: Parameters: (%s = list names present in the artifact, %s = loaded entry_ids).
STALE_PREDICATE = "list_name = ANY(%s) AND entry_id <> ALL(%s)"


class MassDelistingRefused(RuntimeError):
    """A reload would remove more of the table than a real delisting plausibly does."""


def delisting_decision(before: int, stale: int, *, allow_mass: bool) -> float:
    """Return the delisting fraction, or refuse the delete outright.

    Split out of `main()` so the cap can be falsified directly: a cap that is
    never reachable by any input is decoration, and the only way to show it is
    reachable is to call it with the input that trips it.
    """
    fraction = stale / before if before else 0.0
    if fraction > MAX_DELIST_FRACTION and not allow_mass:
        raise MassDelistingRefused(
            f"refusing to delete {stale:,} entries ({fraction:.1%} of the "
            f"table, cap {MAX_DELIST_FRACTION:.0%}). A truncated artifact "
            f"looks exactly like this. Re-run the fetcher, or pass "
            f"--allow-mass-delisting if the removal is genuine."
        )
    return fraction

DDL = f"""
CREATE TABLE IF NOT EXISTS "{S}".sanctions_entry (
    entry_id        text        PRIMARY KEY,   -- 'SDN-36'
    list_name       text        NOT NULL,      -- SDN | CONS
    ofac_uid        integer     NOT NULL,
    sdn_type        text        NOT NULL,      -- Individual | Entity | Vessel | Aircraft
    primary_name    text        NOT NULL,
    first_name      text,
    last_name       text,
    title           text,
    programs        text[]      NOT NULL,
    nationalities   text[]      NOT NULL,
    citizenships    text[]      NOT NULL,
    countries       text[]      NOT NULL,
    -- Verbatim OFAC strings: 'circa 1965', '1965 to 1967', '05 Mar 1968'.
    -- Normalizing to a date would discard the ambiguity the resolution layer
    -- is meant to reason about, and would need a policy for ranges.
    dates_of_birth  text[]      NOT NULL,
    places_of_birth text[]      NOT NULL,
    publish_date    date        NOT NULL,
    provenance      text        NOT NULL,
    UNIQUE (list_name, ofac_uid)
);

CREATE TABLE IF NOT EXISTS "{S}".sanctions_name (
    entry_id    text        NOT NULL
                REFERENCES "{S}".sanctions_entry(entry_id) ON DELETE CASCADE,
    name_uid    integer     NOT NULL,   -- 0 = the entry's primary name
    name_kind   text        NOT NULL,   -- 'primary' | 'a.k.a.' | 'f.k.a.' | 'n.k.a.'
    category    text        NOT NULL,   -- OFAC's own alias confidence: strong | weak | ''
    first_name  text,
    last_name   text,
    name        text        NOT NULL,
    name_norm   text        NOT NULL,   -- ccf.names.normalize(name)
    provenance  text        NOT NULL,
    PRIMARY KEY (entry_id, name_uid)
);

CREATE INDEX IF NOT EXISTS sanctions_name_norm_idx
    ON "{S}".sanctions_name (name_norm);
CREATE INDEX IF NOT EXISTS sanctions_entry_type_idx
    ON "{S}".sanctions_entry (sdn_type);
"""


def parse_publish_date(raw: str) -> str:
    """OFAC writes MM/DD/YYYY. Fail loudly rather than guess a format."""
    return datetime.strptime(raw, "%m/%d/%Y").date().isoformat()


def build_rows(doc: dict) -> tuple[list[tuple], list[tuple], dict]:
    publications = doc["publications"]
    pub_dates = {k: parse_publish_date(v["publish_date"]) for k, v in publications.items()}

    entry_rows: list[tuple] = []
    name_rows: list[tuple] = []
    seen_entries: set[str] = set()

    for e in doc["entries"]:
        if e["uid"] is None:
            raise RuntimeError(f"entry without a uid: {e['primary_name']!r}")
        entry_id = f"{e['list_name']}-{e['uid']}"
        if entry_id in seen_entries:
            raise RuntimeError(f"duplicate entry_id {entry_id} in artifact")
        seen_entries.add(entry_id)

        entry_rows.append(
            (
                entry_id, e["list_name"], e["uid"], e["sdn_type"],
                e["primary_name"], e["first_name"], e["last_name"], e["title"],
                e["programs"], e["nationalities"], e["citizenships"],
                e["countries"], e["dates_of_birth"], e["places_of_birth"],
                pub_dates[e["list_name"]], "public",
            )
        )

        name_rows.append(
            (
                entry_id, PRIMARY_NAME_UID, "primary", "",
                e["first_name"], e["last_name"], e["primary_name"],
                normalize(e["primary_name"]), "public",
            )
        )

        seen_uids = {PRIMARY_NAME_UID}
        for a in e["aliases"]:
            # The reserved-uid assumption, checked rather than trusted: if OFAC
            # ever emitted an alias with uid 0 it would silently overwrite the
            # entry's primary name under the composite key.
            if a["uid"] == PRIMARY_NAME_UID:
                raise RuntimeError(
                    f"{entry_id}: alias carries uid 0, which this schema "
                    f"reserves for the primary name"
                )
            if a["uid"] in seen_uids:
                raise RuntimeError(f"{entry_id}: duplicate alias uid {a['uid']}")
            seen_uids.add(a["uid"])
            name_rows.append(
                (
                    entry_id, a["uid"], a["type"], a["category"],
                    a["first_name"], a["last_name"], a["name"],
                    normalize(a["name"]), "public",
                )
            )

    stats = {
        "publications": {k: v["publish_date"] for k, v in publications.items()},
        "by_type": Counter(r[3] for r in entry_rows),
        "by_list": Counter(r[1] for r in entry_rows),
        "weak_aliases": sum(1 for r in name_rows if r[3] == "weak"),
        "empty_norm": sum(1 for r in name_rows if not r[7]),
    }
    return entry_rows, name_rows, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Load OFAC sanctions lists into Postgres")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-mass-delisting", action="store_true",
                    help=f"permit a reload removing >{MAX_DELIST_FRACTION:.0%} of entries")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())
    entry_rows, name_rows, stats = build_rows(doc)

    print(f"Wave 13b Task 1 — OFAC sanctions lists into {S}\n")
    print(f"  artifact          {ARTIFACT.relative_to(REPO_ROOT)}")
    for lst, pd in stats["publications"].items():
        print(f"  published {lst:<5}   {pd}")
    print(f"\n  sanctions_entry   {len(entry_rows):>7}   "
          f"{dict(stats['by_list'])}")
    for t, n in stats["by_type"].most_common():
        print(f"      {t:<12}  {n:>6}")
    print(f"  sanctions_name    {len(name_rows):>7}   "
          f"({stats['weak_aliases']:,} weak aliases)")

    # A name that normalizes to nothing cannot be screened against, and would
    # sit in the index as a silent hole. Report it; do not let it pass unseen.
    if stats["empty_norm"]:
        print(f"  WARNING: {stats['empty_norm']} name(s) normalize to empty")

    if len(entry_rows) != doc["entry_count"]:
        raise RuntimeError(
            f"built {len(entry_rows)} entry rows from an artifact declaring "
            f"{doc['entry_count']}"
        )

    if args.dry_run:
        print("\n  [dry-run] no DDL executed, no rows written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        cur.execute(f'SELECT count(*) FROM "{S}".sanctions_entry')
        before = cur.fetchone()[0]

        cur.executemany(
            f'INSERT INTO "{S}".sanctions_entry '
            "(entry_id, list_name, ofac_uid, sdn_type, primary_name, "
            " first_name, last_name, title, programs, nationalities, "
            " citizenships, countries, dates_of_birth, places_of_birth, "
            " publish_date, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (entry_id) DO UPDATE SET "
            "list_name=EXCLUDED.list_name, ofac_uid=EXCLUDED.ofac_uid, "
            "sdn_type=EXCLUDED.sdn_type, primary_name=EXCLUDED.primary_name, "
            "first_name=EXCLUDED.first_name, last_name=EXCLUDED.last_name, "
            "title=EXCLUDED.title, programs=EXCLUDED.programs, "
            "nationalities=EXCLUDED.nationalities, "
            "citizenships=EXCLUDED.citizenships, countries=EXCLUDED.countries, "
            "dates_of_birth=EXCLUDED.dates_of_birth, "
            "places_of_birth=EXCLUDED.places_of_birth, "
            "publish_date=EXCLUDED.publish_date, provenance=EXCLUDED.provenance",
            entry_rows,
        )

        cur.executemany(
            f'INSERT INTO "{S}".sanctions_name '
            "(entry_id, name_uid, name_kind, category, first_name, last_name, "
            " name, name_norm, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (entry_id, name_uid) DO UPDATE SET "
            "name_kind=EXCLUDED.name_kind, category=EXCLUDED.category, "
            "first_name=EXCLUDED.first_name, last_name=EXCLUDED.last_name, "
            "name=EXCLUDED.name, name_norm=EXCLUDED.name_norm, "
            "provenance=EXCLUDED.provenance",
            name_rows,
        )

        # --- delisting, scoped and capped ---------------------------------
        loaded_ids = [r[0] for r in entry_rows]
        lists = sorted({r[1] for r in entry_rows})
        cur.execute(
            f'SELECT count(*) FROM "{S}".sanctions_entry WHERE {STALE_PREDICATE}',
            (lists, loaded_ids),
        )
        stale = cur.fetchone()[0]

        if stale:
            fraction = delisting_decision(
                before, stale, allow_mass=args.allow_mass_delisting
            )
            print(f"\n  delisted since last load: {stale:,} entries "
                  f"({fraction:.2%} of {before:,})")
            cur.execute(
                f'DELETE FROM "{S}".sanctions_entry WHERE {STALE_PREDICATE}',
                (lists, loaded_ids),
            )
            print(f"  removed {cur.rowcount:,} delisted entries "
                  f"(names cascade)")

        conn.commit()

        cur.execute(f'SELECT count(*) FROM "{S}".sanctions_entry')
        n_entries = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".sanctions_name')
        n_names = cur.fetchone()[0]
        cur.execute(
            f"SELECT count(*) FROM \"{S}\".sanctions_entry "
            "WHERE sdn_type = 'Individual'"
        )
        n_individuals = cur.fetchone()[0]

    print(f"\n  loaded: sanctions_entry {n_entries:,} · "
          f"sanctions_name {n_names:,} · individuals {n_individuals:,}")

    if n_entries != len(entry_rows) or n_names != len(name_rows):
        raise RuntimeError(
            f"post-load count mismatch: expected {len(entry_rows):,}/"
            f"{len(name_rows):,}, store holds {n_entries:,}/{n_names:,}"
        )
    print("  store matches the artifact exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
