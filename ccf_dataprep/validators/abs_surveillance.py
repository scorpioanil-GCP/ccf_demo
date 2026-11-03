#!/usr/bin/env python3
"""The Wave 14 gate. Seven checks, all recomputed.

    uv run validators/abs_surveillance.py

## What this file refuses to do

`abs_servicer_report.published_trigger_occurred` states, per period, whether
the delinquency trigger fired. `abs_servicer_report.published_delinquency_percent`
states the ratio. `bo_chain.depth` and `person_crosswalk.match_band` were the
Wave 13b equivalents, and reading them is how three of that wave's four
defects survived in conditions already reporting PASS.

So not one of the seven takes a filed result as its answer. Checks 1-3
recompute the pool balance, the 60+ delinquency ratio, and the trigger
trajectory from `abs_loan_period` -- 1.32M loan-periods -- and use the
published figures only to CROSS-CHECK. A disagreement is reported, never
smoothed.

One filed number *is* consumed as an input: `published_delinquency_trigger`,
the threshold itself, present on all 36 deal-periods. That is a term of the
deal rather than a computed result, and the alternative -- a constant baked
into this validator -- would be the same defect moved somewhere harder to
see.

Read-only throughout. Every SPARQL query carries an explicit `FROM`; Fluree
returns HTTP 500, not a helpful 400, without one.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, mongo_db, pg_connect

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2

#: Loan level and filing agree to the precision the filing carries. Measured
#: 2026-08-23 over all 36 deal-periods (three deals x 2025-07..2026-06): worst
#: recomputed-minus-published gap is **0.0050pp** (TAOT-2022-B 2026-01,
#: ours 1.0250% vs filed 1.02%), and every one of the 36 pool balances foots
#: to the filed figure with a difference of exactly 0. On SDART-2022-6
#: 2026-05, for one worked example, the loan file sums to $340,076,028.22 --
#: the published pool balance to the penny -- and the ratio recomputes to
#: 10.7897%, which is the published 10.79%.
#:
#: So the tolerance is tight on purpose: 0.02pp is 4x the worst error present
#: and nothing like a safety margin. A wide one would be decoration. Measured
#: on the same data, moving the delinquency cut from `>= 60` to `>= 61` days
#: shifts the ratio by up to **1.64pp** (SDART-2022-6 2026-04) -- so an
#: earlier draft's 2.0pp tolerance would have passed forever while measuring
#: the wrong population.
RECONCILE_TOLERANCE_PP = Decimal("0.02")

#: Pool balances are filed in cents and reconcile with a difference of exactly
#: 0 on all 36 deal-periods, so one cent is the smallest tolerance that is not
#: zero -- and a single dropped loan moves the sum by thousands of dollars.
POOL_BALANCE_TOLERANCE = Decimal("0.01")

#: The provenance string that exempts a threshold from the anchoring check.
#: Compared exactly, em-dash included: this is the one named exception, and a
#: near-miss must fail loudly rather than silently exempt nothing.
ENGINEERED = "synthetic — engineered"

#: One scan of `abs_loan_period`, per deal-period, with the filed figures
#: alongside. Recomputation is the point: the CASE expression re-derives the
#: 60+ delinquent balance from `current_delinquency_status`, and the SUM
#: re-derives the pool balance, rather than reading either from the filing.
RECOMPUTE_SQL = f"""
    SELECT l.deal_id,
           l.period,
           SUM(l.reporting_period_actual_end_balance_amount) AS pool_ours,
           ROUND(100 * SUM(CASE WHEN l.current_delinquency_status >= 60
                    THEN l.reporting_period_actual_end_balance_amount ELSE 0 END)
                 / NULLIF(SUM(l.reporting_period_actual_end_balance_amount), 0),
                 4) AS delinquency_ours,
           r.pool_balance AS pool_filed,
           r.published_delinquency_percent AS delinquency_filed,
           r.published_delinquency_trigger AS trigger_filed
    FROM "{S}".abs_loan_period l
    JOIN "{S}".abs_servicer_report r USING (deal_id, period)
    GROUP BY l.deal_id, l.period, r.pool_balance,
             r.published_delinquency_percent, r.published_delinquency_trigger
    ORDER BY l.deal_id, l.period"""


@dataclass
class Result:
    name: str
    ok: bool
    detail: str

    @property
    def is_detail_line(self) -> bool:
        """Sub-lines are context under a check, not checks in their own right.

        They are printed but never counted -- otherwise the per-deal lines
        under the trajectory check would inflate "7 pass" to "10 pass" and
        the gate would report a number nobody could reconcile against the
        seven functions.
        """
        return self.name.startswith("  ")


def recompute(cur) -> list[tuple]:
    """Run the loan-level scan. ~0.2s over 1.32M rows on the deal/period index."""
    cur.execute(RECOMPUTE_SQL)
    return cur.fetchall()


def check_pool_balance_reconciles(cur) -> list[Result]:
    """The strongest check in the wave: the loan file must foot to the filing.

    Summing every loan's ending balance must equal the pool balance the
    servicer published, to the cent -- two documents, two preparers, one
    number. This is what proves the load is complete and correctly typed:
    a single dropped record, a truncated period, or a float somewhere would
    all move it.
    """
    name = "pool balance reconciles to the filing"
    rows = recompute(cur)
    if not rows:
        return [Result(name, False, "no loan rows joined to servicer reports")]
    breaks = [(d, p, ours, filed) for d, p, ours, _, filed, _, _ in rows
              if ours is None or filed is None
              or abs(ours - filed) > POOL_BALANCE_TOLERANCE]
    detail = f"{len(rows)} deal-periods; {len(breaks)} off by more than a cent"
    if breaks:
        detail += " -- " + "; ".join(f"{d} {p}: ours {ours} vs filed {filed}"
                                     for d, p, ours, filed in breaks[:4])
    return [Result(name, not breaks, detail)]


def check_delinquency_recomputes(cur) -> list[Result]:
    """Recompute delinquency from loan level; cross-check against the filing."""
    name = "delinquency recomputed from loan level"
    rows = recompute(cur)
    if not rows:
        return [Result(name, False, "no loan rows joined to servicer reports")]
    # A missing value on either side is a break, not a crash: a gate that
    # raises on bad data reports nothing about the data.
    breaks = [(d, p, ours, filed) for d, p, _, ours, _, filed, _ in rows
              if ours is None or filed is None
              or abs(ours - filed) > RECONCILE_TOLERANCE_PP]
    worst = max((abs(ours - filed) for _, _, _, ours, _, filed, _ in rows
                 if ours is not None and filed is not None), default=None)
    detail = (f"{len(rows)} deal-periods recomputed; "
              f"{len(breaks)} beyond {RECONCILE_TOLERANCE_PP}pp")
    if worst is not None:
        detail += f"; worst gap {worst}pp"
    if breaks:
        detail += " -- " + "; ".join(f"{d} {p}: ours {ours} vs filed {filed}"
                                     for d, p, ours, filed in breaks[:4])
    return [Result(name, not breaks, detail)]


def check_trajectory(cur) -> list[Result]:
    """A trajectory, not a static distance.

    Counts PERIODS in which proximity narrowed -- the unit the condition
    names. Counting deals, or trigger definitions, would pass forever.

    The series is the RECOMPUTED ratio, not `published_delinquency_percent`.
    The two agree (0.0050pp worst, all 36), so the verdict is the same either
    way -- but reading the servicer's own percentage would make this the one
    check in the file that trusts a filed result, and the docstring above
    would then be false. The threshold it closes on stays filed:
    `published_delinquency_trigger` is a term of the deal.
    """
    name = "at least one trigger approaching across the series"
    rows = recompute(cur)
    if not rows:
        return [Result(name, False, "no loan rows joined to servicer reports")]
    # A None ratio (empty pool) or a missing filed threshold must FAIL, not
    # raise: a gate that crashes on bad data reports nothing about the data.
    unusable = [(d, p) for d, p, _, ours, _, _, trig in rows
                if ours is None or trig is None]
    if unusable:
        return [Result(name, False,
                       f"{len(unusable)} deal-periods have no recomputable "
                       f"distance, e.g. {unusable[:3]}")]

    series: dict[str, list] = {}
    for deal_id, period, _, ours, _, _, trigger in rows:
        series.setdefault(deal_id, []).append((period, trigger - ours))

    # RULING F61 -- a RUN, not a tally. The old test was
    # `narrowed >= len(points) // 2 and total_move > 0`, i.e. 6 of 11 plus any
    # positive net, and a square wave oscillating 14/15/14/15 clears both while
    # having no trajectory at all -- which is exactly the static case §F's
    # bullet exists to exclude. A run of >= 3 consecutive narrowing periods
    # cannot be produced by an oscillation, whatever its net drift.
    RUN_REQUIRED = 3
    results = []
    narrowing_deals = 0
    for deal_id, points in series.items():
        narrowed = sum(1 for i in range(1, len(points))
                       if points[i][1] < points[i - 1][1])
        total_move = points[0][1] - points[-1][1]
        run = longest_run = 0
        for i in range(1, len(points)):
            if points[i][1] < points[i - 1][1]:
                run += 1
                longest_run = max(longest_run, run)
            else:
                run = 0
        if longest_run >= RUN_REQUIRED and total_move > 0:
            narrowing_deals += 1
        results.append(Result(
            f"  {deal_id} proximity", True,
            f"{deal_id}: {narrowed}/{len(points) - 1} periods narrowed, "
            f"longest consecutive run {longest_run}, "
            f"net {total_move:+.2f}pp toward the trigger"))
    results.insert(0, Result(
        name,
        narrowing_deals >= 1,
        f"{narrowing_deals} of {len(series)} deals narrow across the window"))
    return results


def check_tranche_structure(cur) -> list[Result]:
    """Count DISTINCT tranches per deal, not mentions."""
    cur.execute(f"""SELECT deal_id, COUNT(DISTINCT class_name)
                    FROM "{S}".abs_tranche
                    GROUP BY deal_id ORDER BY deal_id""")
    rows = cur.fetchall()
    if not rows:
        return [Result("every deal carries >= 4 distinct tranches", False,
                       "no tranches loaded")]
    short = [(d, n) for d, n in rows if n < 4]
    return [Result("every deal carries >= 4 distinct tranches", not short,
                   ", ".join(f"{d}: {n}" for d, n in rows))]


def check_restricted_principal_binds(cur) -> list[Result]:
    """The ceiling must LOWER a real request, not merely exist."""
    from loaders.load_abs_overlay_wave14 import effective_granularity
    cur.execute(f'SELECT principal, max_granularity '
                f'FROM "{S}".abs_granularity_entitlement')
    grants = dict(cur.fetchall())
    if not grants:
        return [Result("at least one principal is restricted below the request",
                       False, "no entitlements loaded")]

    lowered = {p: effective_granularity("loan", g)
               for p, g in grants.items()
               if effective_granularity("loan", g) != "loan"}
    shown = (", ".join(f"{p} -> {g}" for p, g in sorted(lowered.items()))
             if lowered else "none lowered")
    return [Result(
        "at least one principal is restricted below the request",
        len(lowered) >= 1,
        f"requesting granularity=loan over {len(grants)} grants: {shown}")]


def check_amendment_diverges() -> list[Result]:
    """as_of and known_as_of must return DIFFERENT answers in the gap.

    If they agree everywhere the bitemporal claim is unfalsifiable, which is
    the same shape as a decomposition that is algebraically zero.
    """
    name = "as_of and known_as_of diverge inside the booking gap"
    rows = fluree.query(f"""
        SELECT ?t ?v ?eff ?asserted
        FROM <{L}>
        WHERE {{
          ?t <{EX}thresholdValue> ?v .
          ?t <{EX}validFrom> ?eff .
          ?t <{EX}assertedAt> ?asserted .
        }}""")["results"]["bindings"]
    chain = [{"value": b["v"]["value"],
              "effective_from": date.fromisoformat(b["eff"]["value"]),
              "asserted_at": date.fromisoformat(b["asserted"]["value"])}
             for b in rows if "delinquency" in b["t"]["value"]
             and "SDART-2022-6" in b["t"]["value"]]
    if len(chain) < 2:
        return [Result(name, False,
                       f"expected 2 assertions in the chain, found {len(chain)}")]

    from generators.generate_trigger_amendment import (
        threshold_as_of, threshold_known_as_of)
    amended = max(chain, key=lambda a: a["effective_from"])
    lag = amended["asserted_at"] - amended["effective_from"]
    gap_day = amended["effective_from"] + lag / 2

    as_of = threshold_as_of(chain, gap_day)
    known = threshold_known_as_of(chain, gap_day)
    return [Result(name, as_of != known,
                   f"on {gap_day}: in force {as_of}, known {known} "
                   f"({lag.days}d lag)")]


def check_every_threshold_is_anchored() -> list[Result]:
    """Every filed threshold resolves to prospectus text.

    The engineered amendment is the ONE exception, by name, because no filed
    sentence says it. Exempting it silently would let any unanchored
    threshold through -- so the exemption is an explicit provenance test
    against `ENGINEERED`, and the exempted subjects are named in the output.
    """
    name = "every filed threshold carries a passage anchor"
    db = mongo_db(write=False)
    # RULING F62 -- an anchor must RESOLVE, not merely exist. The projection
    # was {"trigger_id": 1}, so document_id, the offsets and quoted_text were
    # never read: an anchor pointing at no document, or carrying a zero-length
    # span, satisfied "carries a passage anchor" exactly as well as a real one.
    anchors, malformed = set(), []
    known_docs = set(db["document"].distinct("document_id"))
    for a in db["trigger_anchor"].find(
            {}, {"trigger_id": 1, "document_id": 1, "start_offset": 1,
                 "end_offset": 1, "quoted_text": 1}):
        tid = a.get("trigger_id")
        if a.get("document_id") not in known_docs:
            malformed.append(f"{tid}:no-such-document")
        elif not isinstance(a.get("start_offset"), int) or \
                not isinstance(a.get("end_offset"), int) or \
                a["end_offset"] <= a["start_offset"]:
            malformed.append(f"{tid}:bad-span")
        elif not (a.get("quoted_text") or "").strip():
            malformed.append(f"{tid}:empty-quote")
        else:
            anchors.add(tid)
    rows = fluree.query(f"""
        SELECT ?t ?p
        FROM <{L}>
        WHERE {{ ?t <{EX}thresholdValue> ?v .
                 ?t <{EX}provenance> ?p . }}""")["results"]["bindings"]
    if not rows:
        return [Result(name, False, "no thresholds found in the ledger")]

    unanchored, exempt = [], []
    for b in rows:
        trigger_id = b["t"]["value"].rsplit("abs-trigger-", 1)[-1]
        if b["p"]["value"] == ENGINEERED:
            exempt.append(trigger_id)      # named exception, see docstring
            continue
        if trigger_id not in anchors:
            unanchored.append(trigger_id)
    return [Result(name, not unanchored and not malformed,
                   f"{len(rows) - len(exempt)} filed thresholds vs "
                   f"{len(anchors)} resolving anchors; unanchored: "
                   f"{', '.join(sorted(unanchored)) or 'none'}; "
                   f"malformed: {', '.join(sorted(malformed)) or 'none'}; "
                   f"exempt as engineered: "
                   f"{', '.join(sorted(exempt)) or 'none'}")]


#: The five that take a cursor, in run order. Named so the mutation harness
#: can call the same list this file's `main` calls -- a harness that ran a
#: different set would be evidence about a different program.
PG_CHECKS = (
    check_pool_balance_reconciles,
    check_delinquency_recomputes,
    check_trajectory,
    check_tranche_structure,
    check_restricted_principal_binds,
)

#: The two that read Fluree and Mongo instead.
STORE_CHECKS = (
    check_amendment_diverges,
    check_every_threshold_is_anchored,
)


def run_all() -> list[Result]:
    results: list[Result] = []
    with pg_connect() as conn, conn.cursor() as cur:
        for check in PG_CHECKS:
            results += check(cur)
    for check in STORE_CHECKS:
        results += check()
    return results


def report(results: list[Result]) -> int:
    print("ABS securitization surveillance — Wave 14 gate\n")
    checks = [r for r in results if not r.is_detail_line]
    for r in results:
        if r.is_detail_line:
            print(f"      {r.detail}")
            continue
        state = "PASS" if r.ok else "FAIL"
        print(f"  [{state}] {r.name}\n         {r.detail}")
    failed = sum(1 for r in checks if not r.ok)
    print(f"\n  {len(checks) - failed} of {len(checks)} checks pass, "
          f"{failed} fail")
    return 1 if failed else 0


def main() -> int:
    return report(run_all())


if __name__ == "__main__":
    sys.exit(main())
