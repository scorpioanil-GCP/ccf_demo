#!/usr/bin/env python3
"""Falsification harness for `validators/abs_surveillance.py`.

    uv run validators/test_abs_surveillance.py

A gate nobody has seen fail is a gate nobody has verified. `abs_surveillance`
reports 7/7 PASS; this file is the evidence that those seven are measuring
something. It breaks each input in turn and requires the matching check to go
red. **It exits non-zero if any mutation leaves its target green** -- so it is
itself a gate, not a report.

## Why this runs in-process, and why that makes it safe to commit

The first draft of this harness mutated inside an uncommitted transaction on
one connection and ran the validator as a SUBPROCESS, which opened its own.
The subprocess could not see the uncommitted rows, so every mutation reported
exit 0 no matter what it did. Demonstrated against the live database:

    conn A before mutation        18 tranches
    conn A sees, uncommitted       5
    conn B (the subprocess) sees  18   <-- unchanged
    after rollback                18

So the checks are called IN-PROCESS against the mutated cursor. Two
consequences, both load-bearing:

1. The code under test genuinely reads the mutated rows. Each mutation is
   followed by a read-back **through the same cursor the check will use**, and
   that before/after pair is printed. A mutation whose read-back does not move
   is not evidence of anything.
2. Nothing is ever committed. `pg_connect()` is used directly rather than as a
   context manager, because psycopg3's connection `__exit__` COMMITS on clean
   exit -- a `with` block here would write mutations into a live 1.32M-row
   table. Every connection is rolled back in a `finally`, and the run ends by
   re-checking on a fresh connection that the database is clean.

## What this harness CANNOT test, and why

`check_amendment_diverges` and `check_every_threshold_is_anchored` take no
cursor; they read Fluree and MongoDB. Neither can be mutation-tested the way
the five Postgres checks are:

  * **Fluree is append-only.** A "mutation" there is a retraction that cannot
    be rolled back. Breaking the amendment chain to watch the check fail would
    permanently damage the ledger.
  * **The Mongo write has no transaction to roll back** in this setup (no
    session), so deleting a passage anchor to watch the check fail risks
    losing it.

They get `check_store_falsification` instead, which substitutes the store
responses at the module boundary. That is **weaker evidence and is reported
separately, outside the mutation table**: it proves the check LOGIC
distinguishes good input from bad; it does NOT prove the wiring to the live
stores. The green control arm in each pair -- the same check run against the
real Fluree and the real Mongo -- is what covers the wiring.

Read-only against Fluree and MongoDB throughout. Postgres is written only
inside transactions that are always rolled back.
"""
from __future__ import annotations

import sys

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect
from validators import abs_surveillance as V

# ===========================================================================
# The mutation table -- the five checks that take a cursor
# ===========================================================================
#
# `(target, description, mutation_sql, readback_sql)`.
#
# `target` is the exact `Result.name` the mutation must turn red. Matching on
# the check's own reported name, rather than on a position in a list, is what
# stops this harness from silently testing a different check after a rename.
#
# Each mutation is chosen to hit ONE check. That is the second piece of
# evidence in the output: if a mutation reddens more than its target, the
# checks are coupled through something they should not share.

MUTATIONS = [
    (
        "pool balance reconciles to the filing",
        "one loan's ending balance +1000 (TAOT-2022-B 2026-06). Moves the "
        "pool sum by $1000 but the delinquency ratio by only 0.0012pp, which "
        "is inside the 0.02pp tolerance -- so it isolates check 1.",
        f"""UPDATE "{S}".abs_loan_period
            SET reporting_period_actual_end_balance_amount =
                reporting_period_actual_end_balance_amount + 1000
            WHERE deal_id = 'TAOT-2022-B' AND period = '2026-06'
              AND asset_number = (SELECT MIN(asset_number)
                                  FROM "{S}".abs_loan_period
                                  WHERE deal_id = 'TAOT-2022-B'
                                    AND period = '2026-06')""",
        f"""SELECT SUM(reporting_period_actual_end_balance_amount)
            FROM "{S}".abs_loan_period
            WHERE deal_id = 'TAOT-2022-B' AND period = '2026-06'""",
    ),
    (
        "delinquency recomputed from loan level",
        "clear the 60+ delinquency status on TAOT-2022-B 2026-06. The "
        "recomputed ratio drops to 0 while the published figure stays at "
        "1.31 -- so a check reading the published column could not notice.",
        f"""UPDATE "{S}".abs_loan_period SET current_delinquency_status = 0
            WHERE deal_id = 'TAOT-2022-B' AND period = '2026-06'
              AND current_delinquency_status >= 60""",
        f"""SELECT COUNT(*) FROM "{S}".abs_loan_period
            WHERE deal_id = 'TAOT-2022-B' AND period = '2026-06'
              AND current_delinquency_status >= 60""",
    ),
    (
        "at least one trigger approaching across the series",
        "raise the filed trigger 10pp per elapsed period, so every deal's "
        "distance to it widens monotonically and no period narrows.",
        f"""UPDATE "{S}".abs_servicer_report r
            SET published_delinquency_trigger =
                r.published_delinquency_trigger
                + 10 * (SELECT COUNT(*) FROM "{S}".abs_servicer_report q
                        WHERE q.deal_id = r.deal_id AND q.period <= r.period)""",
        f"""SELECT MIN(published_delinquency_trigger),
                   MAX(published_delinquency_trigger)
            FROM "{S}".abs_servicer_report WHERE deal_id = 'TAOT-2022-B'""",
    ),
    (
        "every deal carries >= 4 distinct tranches",
        "collapse every class_name to 'A-1'. Six ROWS survive per deal and "
        "one distinct tranche remains -- this is the mutation that proves "
        "the check counts tranches rather than mentions.",
        f"""UPDATE "{S}".abs_tranche SET class_name = 'A-1'""",
        f"""SELECT deal_id, COUNT(*), COUNT(DISTINCT class_name)
            FROM "{S}".abs_tranche GROUP BY deal_id ORDER BY 1""",
    ),
    (
        "every deal carries >= 4 distinct tranches",
        "delete every tranche except A-1 / A-2. `abs_holding` references "
        "`abs_tranche`, so the holdings go first in the same rolled-back "
        "transaction -- without that the DELETE trips the foreign key and "
        "never reaches the check.",
        f"""DELETE FROM "{S}".abs_holding WHERE tranche_id IN
              (SELECT tranche_id FROM "{S}".abs_tranche
               WHERE class_name NOT IN ('A-1', 'A-2'));
            DELETE FROM "{S}".abs_tranche
            WHERE class_name NOT IN ('A-1', 'A-2')""",
        f"""SELECT deal_id, COUNT(DISTINCT class_name)
            FROM "{S}".abs_tranche GROUP BY deal_id ORDER BY 1""",
    ),
    (
        "at least one principal is restricted below the request",
        "widen every entitlement to loan level, so the ceiling exists but "
        "lowers nothing.",
        f"""UPDATE "{S}".abs_granularity_entitlement
            SET max_granularity = 'loan'""",
        f"""SELECT DISTINCT max_granularity
            FROM "{S}".abs_granularity_entitlement ORDER BY 1""",
    ),
]


def run_pg_checks(cur) -> dict[str, bool]:
    """Run the gate's own `PG_CHECKS` list, keyed by the name it reports.

    Deliberately the same tuple `abs_surveillance.main` runs. A harness that
    assembled its own list would be evidence about a different program.
    """
    return {r.name: r.ok
            for check in V.PG_CHECKS
            for r in check(cur)
            if not r.is_detail_line}


def check_mutations() -> list[tuple[str, bool]]:
    """Break each Postgres input; require the matching check to go red."""
    outcomes: list[tuple[str, bool]] = []
    for target, description, sql, readback in MUTATIONS:
        conn = pg_connect()
        try:
            cur = conn.cursor()
            before = run_pg_checks(cur)
            cur.execute(readback)
            before_value = cur.fetchall()

            cur.execute(sql)
            rowcount = cur.rowcount
            cur.execute(readback)
            after_value = cur.fetchall()

            after = run_pg_checks(cur)
        finally:
            conn.rollback()
            conn.close()

        # A mutation the check cannot see proves nothing. Report the pair.
        visible = before_value != after_value
        flipped = sorted(k for k in after if before[k] and not after[k])
        reddened = target in flipped
        collateral = [k for k in flipped if k != target]

        print(f"\n  === {target}")
        print(f"      mutation      : {description}")
        print(f"      rows affected : {rowcount}")
        print(f"      read-back     : {before_value}")
        print(f"                   -> {after_value}"
              f"{'' if visible else '   <-- UNCHANGED, mutation invisible'}")
        print(f"      before        : {sum(before.values())}/{len(before)} pass")
        print(f"      after         : {sum(after.values())}/{len(after)} pass")
        print(f"      flipped FAIL  : {', '.join(flipped) or 'NOTHING'}")
        if collateral:
            print(f"      collateral    : also reddened {collateral} -- the "
                  f"checks may share an input they should not")
        print(f"      verdict       : "
              f"{'target went red, as required' if reddened and visible else 'DECORATIVE'}")
        outcomes.append((f"mutation: {description.split('.')[0]}",
                         reddened and visible))
    return outcomes


def check_database_is_clean() -> list[tuple[str, bool]]:
    """Every mutation above must have left no trace. Fresh connection."""
    conn = pg_connect()
    try:
        results = run_pg_checks(conn.cursor())
    finally:
        conn.rollback()
        conn.close()
    clean = all(results.values())
    print(f"\n  fresh connection after all rollbacks: "
          f"{sum(results.values())}/{len(results)} checks pass")
    if not clean:
        print("  A mutation escaped its transaction. The database is dirty.")
    return [("database clean after rollback", clean)]


# ===========================================================================
# Falsification arms for the two store checks -- WEAKER EVIDENCE
# ===========================================================================
#
# See "What this harness CANNOT test" in the module docstring. These stub the
# store responses at the module boundary and call the real check function
# unmodified. Each pair opens with a CONTROL against the live stores, because
# a stubbed arm going red says nothing unless the unstubbed one is green.

ORIG = "http://example.org/fibo/abs-trigger-SDART-2022-6-delinquency"
AMEND = ORIG + "-amendment"
NINE_PUBLIC_IDS = (
    "SDART-2022-6-delinquency", "SDART-2022-6-reserve",
    "SDART-2022-6-overcollateralization", "SDART-2024-1-delinquency",
    "SDART-2024-1-reserve", "SDART-2024-1-overcollateralization",
    "TAOT-2022-B-delinquency", "TAOT-2022-B-reserve",
    "TAOT-2022-B-overcollateralization",
)


def binding(uri, value, eff, asserted, provenance=None):
    b = {"t": {"value": uri}, "v": {"value": value},
         "eff": {"value": eff}, "asserted": {"value": asserted}}
    if provenance is not None:
        b["p"] = {"value": provenance}
    return b


class FlureeStub:
    """Stands in for `ccf.fluree`, and asserts the query still carries FROM.

    Fluree answers HTTP 500, not a helpful 400, for a query with no dataset.
    A stub that silently accepted one would hide the exact defect this wave
    hit three times.
    """

    def __init__(self, bindings):
        self.bindings = bindings

    def query(self, sparql, *args, **kwargs):
        assert f"FROM <{V.L}>" in sparql, (
            "the check issued a SPARQL query with no FROM clause; Fluree "
            "would answer 500")
        return {"results": {"bindings": self.bindings}}


class MongoStub:
    """Stands in for the `fibo_v2` handle, exposing only `trigger_anchor`."""

    def __init__(self, trigger_ids):
        self.trigger_ids = list(trigger_ids)

    def __getitem__(self, name):
        assert name == "trigger_anchor", f"unexpected collection {name!r}"
        ids = self.trigger_ids
        return type("StubCollection", (), {
            "find": staticmethod(
                lambda *a, **k: [{"trigger_id": t} for t in ids])})()


def arm(label, check, *, fluree_stub=None, mongo_stub=None, note="",
        want_ok: bool) -> tuple[str, bool]:
    """Run one check with substituted stores; restore them unconditionally."""
    real_fluree, real_mongo = V.fluree, V.mongo_db
    if fluree_stub is not None:
        V.fluree = fluree_stub
    if mongo_stub is not None:
        V.mongo_db = lambda *a, **k: mongo_stub
    try:
        result = check()[0]
    finally:
        V.fluree, V.mongo_db = real_fluree, real_mongo

    print(f"    [{'PASS' if result.ok else 'FAIL'}] {label}")
    if note:
        print(f"           input  : {note}")
    print(f"           detail : {result.detail}")
    return (label, result.ok == want_ok)


def check_store_falsification() -> list[tuple[str, bool]]:
    """Stub-injection arms for the two checks that read Fluree and Mongo."""
    engineered_amendment = binding(
        AMEND, "13.50", "2025-11-01", "2026-01-11", V.ENGINEERED)
    nine_public = [binding(f"http://example.org/fibo/abs-trigger-{t}", "1.00",
                           "2022-01-01", "2022-01-01", "public")
                   for t in NINE_PUBLIC_IDS]

    print("\n  check_amendment_diverges")
    outcomes = [
        arm("control, live Fluree", V.check_amendment_diverges, want_ok=True),
        arm("amendment booked on its own effective date",
            V.check_amendment_diverges, want_ok=False,
            fluree_stub=FlureeStub([
                binding(ORIG, "24.00", "2022-09-14", "2022-09-14"),
                binding(AMEND, "13.50", "2025-11-01", "2025-11-01")]),
            note="assertedAt == validFrom, so there is no gap to diverge in"),
        arm("no amendment in the ledger", V.check_amendment_diverges,
            want_ok=False,
            fluree_stub=FlureeStub([binding(ORIG, "24.00", "2022-09-14",
                                            "2022-09-14")]),
            note="one assertion only"),
    ]

    print("\n  check_every_threshold_is_anchored")
    outcomes += [
        arm("control, live Fluree and Mongo",
            V.check_every_threshold_is_anchored, want_ok=True),
        arm("prospectus anchors missing entirely",
            V.check_every_threshold_is_anchored, want_ok=False,
            fluree_stub=FlureeStub(nine_public + [engineered_amendment]),
            mongo_stub=MongoStub([]),
            note="9 public thresholds, 0 anchors"),
        arm("one real threshold loses its anchor",
            V.check_every_threshold_is_anchored, want_ok=False,
            fluree_stub=FlureeStub(nine_public + [engineered_amendment]),
            mongo_stub=MongoStub(t for t in NINE_PUBLIC_IDS
                                 if t != "TAOT-2022-B-reserve"),
            note="anchors present for 8 of 9"),
        # The one that proves the exemption is a PROVENANCE test rather than a
        # name-shaped hole: same node, same missing anchor, relabelled public.
        arm("the unanchored amendment relabelled `public`",
            V.check_every_threshold_is_anchored, want_ok=False,
            fluree_stub=FlureeStub(nine_public + [
                binding(AMEND, "13.50", "2025-11-01", "2026-01-11", "public")]),
            mongo_stub=MongoStub(NINE_PUBLIC_IDS),
            note="provenance `public`, so it must no longer be exempt"),
    ]
    return outcomes


def main() -> int:
    print("abs_surveillance falsification harness\n")
    print("  Postgres mutations run in-process against the mutated cursor and "
          "are\n  always rolled back. Fluree and MongoDB are never written.")

    print("\n" + "-" * 70)
    print("MUTATION TABLE -- the five checks that take a cursor")
    print("-" * 70)
    mutations = check_mutations()
    clean = check_database_is_clean()

    print("\n" + "-" * 70)
    print("STUB INJECTION -- the two store checks. WEAKER EVIDENCE:")
    print("  proves the check logic separates good input from bad; does NOT")
    print("  prove the wiring to the live stores. That is what the control")
    print("  arms show. Reported outside the mutation table on purpose.")
    print("-" * 70)
    stubs = check_store_falsification()

    print("\n" + "=" * 70)
    sections = [("mutation table", mutations + clean),
                ("stub injection", stubs)]
    failed = 0
    for section, outcomes in sections:
        print(f"\n  {section}")
        for label, good in outcomes:
            failed += not good
            print(f"    {'ok  ' if good else 'BAD '} {label}")
    total = sum(len(o) for _, o in sections)
    print(f"\n  {total - failed} of {total} arms behaved as required")
    if failed:
        print("\n  An arm marked BAD means the gate could not tell the "
              "condition from its absence.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
