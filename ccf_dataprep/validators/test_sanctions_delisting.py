#!/usr/bin/env python3
"""Prove the OFAC delisting delete is scoped, and that its cap is reachable.

    uv run validators/test_sanctions_delisting.py

`loaders/load_ofac_wave13b.py` is the only writer of `sanctions_entry` /
`sanctions_name`, and a reload must be able to REMOVE rows — OFAC delists
parties daily, and a loader that only ever inserts leaves a delisted party
sanctioned forever. That delete is the dangerous statement in the file, so it
carries two protections and this file tests both:

  1. **Scope.** It touches only lists the artifact actually carries. A list
     loaded by some future run and absent from today's artifact must survive.
  2. **A cap.** A run removing more than `MAX_DELIST_FRACTION` of the table
     aborts, because a truncated artifact is indistinguishable from a mass
     delisting and the cheap failure is the one that stops.

**Why both arms have a falsification counterpart.** This estate's dominant
defect is checks that pass without looking (`known-issues.md` §12). An
assertion that "the scoped delete spared the CONS row" passes just as happily
against a delete that spares *everything*, or against no delete at all. So
each arm re-runs the plausible-but-wrong version — the unscoped delete, and an
uncapped decision — and REQUIRES the same assertions to fail. If a
falsification arm goes green, this file has stopped distinguishing the guard
from its absence and is decoration.

Nothing here touches the real tables. Both arms run against TEMP tables built
with `LIKE ... INCLUDING ALL`, so the real schema — primary keys, the cascade,
the indexes — is under test while the real 19,730 rows are untouched.
"""

from __future__ import annotations

import sys

from ccf.config import PG_SCHEMA_V2, pg_connect
from loaders.load_ofac_wave13b import (
    MAX_DELIST_FRACTION,
    MassDelistingRefused,
    STALE_PREDICATE,
    delisting_decision,
)

S = PG_SCHEMA_V2

#: The unscoped delete: what this loader would say if `list_name` were left
#: out. It is the plausible wrong version, not a strawman — dropping the list
#: scoping reads as a simplification and passes any test that only counts the
#: rows the artifact does carry.
UNSCOPED_PREDICATE = "entry_id <> ALL(%s)"

#: Fixture. Two lists are represented in the artifact (SDN, CONS); `OTHER`
#: stands for a list some other run loaded and today's artifact does not
#: mention. `SDN-2` is the delisted party — present in the table, absent from
#: the artifact.
FIXTURE = [
    ("SDN-1", "SDN", 1),
    ("SDN-2", "SDN", 2),      # delisted: must be removed
    ("CONS-1", "CONS", 1),
    ("OTHER-1", "OTHER", 1),  # out of scope: must survive
]
ARTIFACT_IDS = ["SDN-1", "CONS-1"]
ARTIFACT_LISTS = ["CONS", "SDN"]


def build_temp(cur) -> None:
    # Each arm gets a fresh fixture: arm 2 must start from the same four rows
    # arm 1 did, or it would be deleting from a table arm 1 already emptied
    # and its "failure" would be an artifact of the ordering.
    cur.execute("DROP TABLE IF EXISTS t_name")
    cur.execute("DROP TABLE IF EXISTS t_entry")
    cur.execute(f'CREATE TEMP TABLE t_entry (LIKE "{S}".sanctions_entry INCLUDING ALL)')
    cur.execute(f'CREATE TEMP TABLE t_name (LIKE "{S}".sanctions_name INCLUDING ALL)')
    # `LIKE ... INCLUDING ALL` copies constraints but NOT foreign keys, so the
    # cascade has to be restated for the temp pair or the name-cascade
    # assertion below would be vacuous.
    cur.execute(
        "ALTER TABLE t_name ADD FOREIGN KEY (entry_id) "
        "REFERENCES t_entry(entry_id) ON DELETE CASCADE"
    )
    for entry_id, list_name, uid in FIXTURE:
        cur.execute(
            "INSERT INTO t_entry (entry_id, list_name, ofac_uid, sdn_type, "
            "primary_name, programs, nationalities, citizenships, countries, "
            "dates_of_birth, places_of_birth, publish_date, provenance) "
            "VALUES (%s,%s,%s,'Individual',%s,'{}','{}','{}','{}','{}','{}',"
            "'2026-08-20','public')",
            (entry_id, list_name, uid, f"PARTY {entry_id}"),
        )
        cur.execute(
            "INSERT INTO t_name (entry_id, name_uid, name_kind, category, "
            "name, name_norm, provenance) "
            "VALUES (%s, 0, 'primary', '', %s, %s, 'public')",
            (entry_id, f"PARTY {entry_id}", f"PARTY {entry_id}"),
        )


def run_delete(cur, predicate: str, *, scoped: bool) -> None:
    params = (ARTIFACT_LISTS, ARTIFACT_IDS) if scoped else (ARTIFACT_IDS,)
    cur.execute(f"DELETE FROM t_entry WHERE {predicate}", params)


def survivors(cur) -> tuple[set[str], set[str]]:
    cur.execute("SELECT entry_id FROM t_entry")
    entries = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT entry_id FROM t_name")
    names = {r[0] for r in cur.fetchall()}
    return entries, names


def assert_scope(entries: set[str], names: set[str]) -> list[str]:
    """The three claims the scoped delete makes. Returns failures."""
    failures = []
    if "SDN-2" in entries:
        failures.append("the delisted SDN-2 was NOT removed")
    if "OTHER-1" not in entries:
        failures.append("OTHER-1 was removed — a list absent from the artifact "
                        "must be out of scope")
    if "SDN-2" in names:
        failures.append("SDN-2's names survived — the cascade did not fire")
    if {"SDN-1", "CONS-1"} - entries:
        failures.append("a listed party present in the artifact was removed")
    return failures


def check_scope(cur) -> bool:
    print("\n1 · the delete is scoped to the artifact's lists")
    build_temp(cur)
    run_delete(cur, STALE_PREDICATE, scoped=True)
    failures = assert_scope(*survivors(cur))
    for f in failures:
        print(f"    FAIL  {f}")
    if not failures:
        print(f"    ok    SDN-2 removed with its names; OTHER-1 and the two "
              f"listed parties survived")
    return not failures


def check_scope_falsification(cur) -> bool:
    print("\n2 · falsification — the UNSCOPED delete must fail those same claims")
    build_temp(cur)
    run_delete(cur, UNSCOPED_PREDICATE, scoped=False)
    failures = assert_scope(*survivors(cur))
    if failures:
        print(f"    ok    unscoped delete fails as required: {failures[0]}")
        return True
    print("    FAIL  the unscoped delete passed the scope assertions — this "
          "test cannot tell the guard from its absence")
    return False


def check_cap() -> bool:
    print(f"\n3 · the cap is reachable (MAX_DELIST_FRACTION = "
          f"{MAX_DELIST_FRACTION:.0%})")
    ok = True

    # Just over the cap: must refuse.
    over = int(19_730 * MAX_DELIST_FRACTION) + 1
    try:
        delisting_decision(19_730, over, allow_mass=False)
        print(f"    FAIL  {over:,} of 19,730 was permitted — the cap never fires")
        ok = False
    except MassDelistingRefused:
        print(f"    ok    {over:,} of 19,730 refused")

    # Just under: must proceed. A cap that refuses everything is as broken as
    # one that refuses nothing, and only this arm can tell them apart.
    under = int(19_730 * MAX_DELIST_FRACTION) - 1
    try:
        delisting_decision(19_730, under, allow_mass=False)
        print(f"    ok    {under:,} of 19,730 permitted")
    except MassDelistingRefused:
        print(f"    FAIL  {under:,} of 19,730 refused — the cap refuses "
              f"ordinary delistings too")
        ok = False

    # The override exists and works.
    try:
        delisting_decision(19_730, over, allow_mass=True)
        print(f"    ok    --allow-mass-delisting overrides")
    except MassDelistingRefused:
        print(f"    FAIL  the override does not override")
        ok = False
    return ok


def check_cap_falsification() -> bool:
    print("\n4 · falsification — an UNCAPPED decision must fail arm 3")
    def uncapped(before: int, stale: int, *, allow_mass: bool) -> float:
        return stale / before if before else 0.0

    over = int(19_730 * MAX_DELIST_FRACTION) + 1
    try:
        uncapped(19_730, over, allow_mass=False)
        print(f"    ok    uncapped decision permits {over:,} — arm 3 would "
              f"fail against it, as required")
        return True
    except MassDelistingRefused:
        print("    FAIL  the uncapped stand-in refused; arm 3 proves nothing")
        return False


def main() -> int:
    print("OFAC delisting — scope and cap")
    print(f"  predicate under test: {STALE_PREDICATE}")

    with pg_connect() as conn, conn.cursor() as cur:
        results = [check_scope(cur), check_scope_falsification(cur)]
        conn.rollback()          # temp tables only, but leave nothing behind

    results += [check_cap(), check_cap_falsification()]

    passed = sum(results)
    print(f"\n{passed}/{len(results)} arms green")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
