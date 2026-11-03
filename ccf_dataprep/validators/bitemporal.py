#!/usr/bin/env python3
"""Prove the bitemporal model does something a single timeline cannot.

This is the flagship's central claim, and it is the one condition that cannot
be established by counting. §F asks for an amendment whose effective and
booking dates differ with a drawdown in the gap; the *point* of that data is
that two queries about the same date return different answers:

    as_of = D, known_as_of = D            what the bank KNEW on D
    as_of = D, known_as_of = today        what was actually TRUE on D

For a drawdown inside a booking gap those must disagree. If they agree, the
model is redundant machinery and the data does not support the product,
regardless of how many amendments were loaded.

Also checked: the policy-version anachronism (§2.4). Evaluating a covenant
against the policy in force *now* rather than the policy in force at `as_of`
produces a finding that is an artefact of the query, not of the borrower.

    uv run validators/bitemporal.py
"""

from __future__ import annotations

import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, pg_connect

L = FLUREE_LEDGER_V2


def bindings(sparql: str) -> list[dict]:
    return fluree.query(sparql)["results"]["bindings"]


def amendments_in_force(as_of: str, known_as_of: str) -> list[dict]:
    """Covenant amendments in force at `as_of`, as known at `known_as_of`.

    TWO filters on TWO axes. The validity filter bounds what was in force; the
    assertion filter bounds what the bank had recorded. Applying only one
    silently answers a different question — which is the failure this validator
    exists to make visible.
    """
    rows = bindings(f"""
        SELECT ?a ?facility ?validFrom ?assertedAt ?lag
        FROM <{L}>
        WHERE {{
            ?a <{EX}validFrom> ?validFrom .
            ?a <{EX}assertedAt> ?assertedAt .
            ?a <{EX}amends> ?facility .
            OPTIONAL {{ ?a <{EX}bookingLagDays> ?lag }}
            FILTER(?validFrom <= "{as_of}")
            FILTER(?assertedAt <= "{known_as_of}")
        }}
    """)
    return [
        {
            "amendment": r["a"]["value"].rsplit("/", 1)[-1],
            "facility": r["facility"]["value"].rsplit("/", 1)[-1],
            "valid_from": r["validFrom"]["value"],
            "asserted_at": r["assertedAt"]["value"],
            "lag": r.get("lag", {}).get("value", "0"),
        }
        for r in rows
    ]


def main() -> int:
    failures: list[str] = []

    # The engineered gap drawdowns are the test cases.
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT d.facility_id, d.drawdown_date, d.amount, d.amendment_number
            FROM "{PG_SCHEMA_V2}".drawdown d
            WHERE d.falls_in_booking_gap
            ORDER BY d.drawdown_date
        """)
        gap_draws = cur.fetchall()

    print("BITEMPORAL DIVERGENCE — the flagship's central claim\n")
    if not gap_draws:
        print("  FAIL: no drawdowns inside a booking gap. Without one, as_of "
              "and known_as_of cannot be shown to diverge.")
        return 1

    print(f"  {len(gap_draws)} engineered gap drawdowns to test\n")

    diverged = 0
    for facility_id, draw_date, amount, amd_no in gap_draws:
        d = draw_date.isoformat()

        # What the bank KNEW on the drawdown date.
        knew = amendments_in_force(as_of=d, known_as_of=d)
        knew_here = [a for a in knew if a["facility"] == facility_id]

        # What was actually TRUE on that date, known with hindsight.
        truth = amendments_in_force(as_of=d, known_as_of="2099-12-31")
        truth_here = [a for a in truth if a["facility"] == facility_id]

        print(f"  {facility_id}  drawdown {d}  ${amount:,.0f}")
        print(f"    known_as_of={d:<12} -> {len(knew_here)} amendment(s) in force")
        print(f"    known_as_of=today        -> {len(truth_here)} amendment(s) in force")

        if len(truth_here) > len(knew_here):
            extra = [a for a in truth_here
                     if a["amendment"] not in {k["amendment"] for k in knew_here}]
            for a in extra:
                print(f"    DIVERGES: {a['amendment']} was effective "
                      f"{a['valid_from']} but not booked until "
                      f"{a['asserted_at']} ({a['lag']}d lag)")
                print(f"              on {d} the bank was operating in good "
                      f"faith against the OLD terms")
            diverged += 1
        else:
            print(f"    NO DIVERGENCE — this case proves nothing")
            failures.append(
                f"{facility_id} drawdown {d}: as_of and known_as_of agree"
            )
        print()

    # --- policy anachronism (§2.4) -----------------------------------------
    print("  POLICY ANACHRONISM — §2.4")
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT policy_version, effective_from, effective_to,
                   leverage_breach_buffer, cure_period_days
            FROM "{PG_SCHEMA_V2}".covenant_policy ORDER BY effective_from
        """)
        policies = cur.fetchall()
    for v, ef, et, buf, cure in policies:
        until = et.isoformat() if et else "current"
        print(f"    {v:22s} {ef} .. {until:10s}  "
              f"buffer={buf}  cure={cure}d")
    if len(policies) >= 2:
        old, new = policies[0], policies[-1]
        if old[3] != new[3] or old[4] != new[4]:
            print(f"    OK: evaluating a covenant from {old[1]} under "
                  f"'{new[0]}' would apply buffer {new[3]} instead of {old[3]}")
            print(f"        -> an anachronism that reads as a finding")
        else:
            failures.append("policy versions do not differ in any value")
    else:
        failures.append("fewer than 2 policy versions")

    # --- ledger replay anchor ----------------------------------------------
    print(f"\n  LEDGER REPLAY ANCHOR")
    t = fluree.ledger_t()
    print(f"    fibo-v2 at t={t} — graph_snapshot_at is an exact block "
          f"reference, not a timestamp query")

    # --- past-breach-now-compliant -----------------------------------------
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT facility_id, covenant_type, breach_date, observed_value,
                   threshold_at_breach, cured_date
            FROM "{PG_SCHEMA_V2}".covenant_breach
            WHERE compliant_today ORDER BY breach_date
        """)
        breaches = cur.fetchall()
    print(f"\n  FORENSIC vs LIVE DISAGREEMENT")
    if not breaches:
        failures.append("no past-breach-now-compliant covenant")
        print("    FAIL: none loaded")
    for fid, ctype, bd, obs, thr, cured in breaches:
        print(f"    {fid} {ctype}: breached {bd} at {obs} vs threshold {thr}, "
              f"cured {cured}")
        print(f"      -> as_of={bd} reports BREACH; as_of=today reports COMPLIANT")

    print(f"\n  {diverged}/{len(gap_draws)} gap drawdowns show divergence")
    if failures:
        print("\n  FAILURES:")
        for f in failures:
            print(f"    {f}")
        return 1
    print("  All bitemporal claims hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
