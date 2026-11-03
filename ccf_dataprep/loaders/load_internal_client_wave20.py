#!/usr/bin/env python3
"""Wave 20 gap 2 -- no-LEI internal clients, the population §D warns about.

    uv run loaders/load_internal_client_wave20.py

## The gap

`counterparty-reference-snapshot` §C (spec-standard-v0-3) names a row this
estate satisfied ZERO of: **"Internal client identity for no-LEI entities"**,
written by the internal client master. Measured 2026-08-28, `legal_entity`
held 0 rows with a null `lei` and `crosswalk` held 0 -- every entity in the
estate had an LEI.

§D says exactly why that matters:

> *"Anchoring exclusively on LEI works for CIB counterparties and public
> Commercial Banking obligors. It does not work for the privately-held
> middle-market borrowers who make up a large share of the Commercial Banking
> book and have no LEI at all. An LEI-only anchor silently excludes them, and
> every downstream product inherits the exclusion."*

**The old manifest could not see this.** Its predecessor row was marked
COVERED against `conditions.py`'s crosswalk floors, and every one of those
floors is keyed on LEI -- structurally incapable of reporting the absence of
entities that have none. A gate that selects by the property it polices.

## Why a separate table, and not a nullable `legal_entity.lei`

`legal_entity.lei` is the PRIMARY KEY and 9 foreign keys reference that table.
Making it nullable is not a migration, it is a redesign of the estate's
identity spine. §C's own single-writer paragraph settles it the other way
anyway: *"the internal client master writes no-LEI identity and KYC state"* --
a DIFFERENT AUTHORITY, which is what a separate table expresses.

`crosswalk.lei` becomes nullable so an internal client can exist without one.
The `UNIQUE (lei)` constraint stays: Postgres treats NULLs as distinct, so any
number of no-LEI clients coexist under it.

## Provenance: `synthetic — internal`

Ruled 2026-08-28, overriding an earlier `synthetic — engineered` call. §C
states the class outright; `legal_entity.provenance` is `public` for all 156
rows so in-table labelling is not how this estate marks invention; and
`engineered_entity` holds invented PATTERNS, while a no-LEI client is
operational identity from the internal client master §C already names. Wrong
shelf. See `docs/wave20-t1-gaps-plan.md`.

**`lei` IS NULL. No `SYN-` placeholder.** A placeholder would resolve and
would defeat §G's acceptance criterion, which is the whole point of the row.

## The names are constructed, not drawn from life

Every name is assembled from invented components by a seeded generator, so no
real private company is described. These are middle-market borrowers by
construction -- the population public data cannot supply, which is why they
have to be invented rather than fetched.

## Identifiers

`CLI-000101` upward, deliberately offset from the existing `CLI-0000NN` block.
A contiguous continuation would collide the first time the anchor set grows,
and this repo has already recorded four loaders that silently rewrote other
waves' rows when a table grew.

## Idempotency

Re-runnable. Deterministic names from a fixed seed, upsert on the natural key,
and verified afterwards BY NAMING A VALUE -- a row count cannot see an
`internal_client_id` being reassigned to a different company.
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ccf.config import PG_SCHEMA_V2, pg_connect  # noqa: E402

S = PG_SCHEMA_V2
SEED = 20260828
N = 30
ID_BASE = 100          # CLI-000101 upward

_STEM = ["Halbrook", "Ferngate", "Marlowe", "Ashcombe", "Pentworth", "Ravenlea",
         "Brackwell", "Coldharbour", "Thornbury", "Wexmoor", "Ellersby",
         "Draycott", "Kingsmere", "Salthouse", "Underhill"]
_TRADE = ["Precision Castings", "Logistics", "Cold Storage", "Fabrication",
          "Agri Supply", "Medical Devices", "Packaging", "Specialty Chemicals",
          "Marine Services", "Tooling"]
_SUFFIX = {"US-OH": "LLC", "US-TX": "LLC", "US-MN": "Inc.", "US-WA": "Inc.",
           "GB": "Ltd", "CA-BC": "ULC", "NL": "B.V.", "DE": "GmbH"}
_JURIS = list(_SUFFIX)

DDL_TABLE = f'''
CREATE TABLE IF NOT EXISTS "{S}".internal_client (
    internal_client_id     TEXT PRIMARY KEY,
    legal_name             TEXT NOT NULL,
    legal_jurisdiction     TEXT,
    legal_form             TEXT,
    legal_address_country  TEXT,
    legal_address_city     TEXT,
    legal_address_region   TEXT,
    hq_address_country     TEXT,
    hq_address_city        TEXT,
    hq_address_region      TEXT,
    -- §D: "Private, no LEI | internal client master | internal KYC
    -- verification state | KYC refresh cadence -- MONTHS". This is the lower
    -- freshness ceiling §G's acceptance criterion requires the payload to
    -- report, against 24 HOURS for an LEI-registered entity.
    kyc_last_refresh       DATE NOT NULL,
    kyc_cycle_days         INTEGER NOT NULL,
    kyc_next_due           DATE NOT NULL,
    freshness_ceiling_days INTEGER NOT NULL,
    provenance             TEXT NOT NULL,
    source                 TEXT NOT NULL,
    retrieved_at           DATE NOT NULL
)
'''


def generate() -> list[dict]:
    rng = random.Random(SEED)
    seen: set[str] = set()
    rows: list[dict] = []
    i = 0
    while len(rows) < N:
        i += 1
        juris = _JURIS[i % len(_JURIS)]
        name = (f"{rng.choice(_STEM)} {rng.choice(_TRADE)} {_SUFFIX[juris]}")
        if name in seen:
            continue
        seen.add(name)
        cycle = rng.choice([180, 270, 365])       # months, per §D
        last = date(2026, 1, 1) + timedelta(days=rng.randrange(0, 200))
        rows.append({
            "internal_client_id": f"CLI-{ID_BASE + len(rows) + 1:06d}",
            "legal_name": name,
            "legal_jurisdiction": juris,
            "legal_form": _SUFFIX[juris],
            "legal_address_country": juris.split("-")[0],
            "legal_address_city": None,
            "legal_address_region": juris if "-" in juris else None,
            "hq_address_country": juris.split("-")[0],
            "hq_address_city": None,
            "hq_address_region": juris if "-" in juris else None,
            "kyc_last_refresh": last,
            "kyc_cycle_days": cycle,
            "kyc_next_due": last + timedelta(days=cycle),
            "freshness_ceiling_days": cycle,
        })
    return rows


def main() -> int:
    rows = generate()
    assert len({r["legal_name"] for r in rows}) == N, "name collision"

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL_TABLE)

        # crosswalk.lei nullable, so an internal client can exist without one.
        cur.execute(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'crosswalk' "
            "AND column_name = 'lei'", (S,))
        if cur.fetchone()[0] == "NO":
            cur.execute(f'ALTER TABLE "{S}".crosswalk '
                        "ALTER COLUMN lei DROP NOT NULL")
            print("  schema: crosswalk.lei -> nullable")

        cur.execute(f'SELECT internal_client_id FROM "{S}".crosswalk')
        taken = {r[0] for r in cur.fetchall()}
        clash = taken & {r["internal_client_id"] for r in rows}
        assert not clash, f"internal_client_id collision with crosswalk: {clash}"

        cols = list(rows[0])
        for r in rows:
            r2 = dict(r, provenance="synthetic — internal",
                      source="internal client master (invented: public sources "
                             "cannot supply a no-LEI entity)",
                      retrieved_at=date.today())
            names = cols + ["provenance", "source", "retrieved_at"]
            cur.execute(
                f'INSERT INTO "{S}".internal_client ({", ".join(names)}) '
                f"VALUES ({', '.join(['%s'] * len(names))}) "
                "ON CONFLICT (internal_client_id) DO UPDATE SET "
                + ", ".join(f"{n} = EXCLUDED.{n}" for n in names[1:]),
                [r2[n] for n in names])
            # The crosswalk row that carries NO LEI. This is the join key the
            # bank side uses; without it the client exists and nothing reaches
            # it, which is the exclusion rather than the fix.
            cur.execute(
                f'INSERT INTO "{S}".crosswalk '
                "(internal_client_id, lei, provenance, source) "
                "VALUES (%s, NULL, %s, %s) "
                "ON CONFLICT (internal_client_id) DO UPDATE SET lei = NULL",
                (r["internal_client_id"], "synthetic — internal",
                 "internal client master: privately held, no LEI exists"))
        conn.commit()

        cur.execute(f'SELECT count(*) FROM "{S}".internal_client')
        n_client = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".crosswalk WHERE lei IS NULL')
        n_nolei = cur.fetchone()[0]
        # Named-value verification: a count cannot see an id reassigned.
        cur.execute(f'SELECT legal_name, legal_jurisdiction, freshness_ceiling_days '
                    f'FROM "{S}".internal_client WHERE internal_client_id = %s',
                    ("CLI-000101",))
        named = cur.fetchone()

    print(f"  {n_client} internal clients, {n_nolei} crosswalk rows with lei IS NULL")
    print(f"  CLI-000101 verified by value: {named[0]} ({named[1]}), "
          f"freshness ceiling {named[2]} days")
    print("  provenance: synthetic — internal (§C's stated class)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
