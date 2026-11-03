#!/usr/bin/env python3
"""Wave 19 Task 13/14 -- hypothetical exposure proposals, and the debt-tolerance case.

## Task 13 -- proposals never touch `facility`

Section 6 of `docs/wave19-design.md` explicitly rejected inventing ~$74bn of
booked exposure -- that is exactly what a proposal written into
`ccf_v2.facility` would silently re-create, moving every portfolio total in
the estate. Proposals live in their own table (`ccf_v2.exposure_proposal`),
every row flagged hypothetical, every row `synthetic — engineered`.

Both proposals below are sized from LIVE numbers, not the design doc's
rounded ones -- `build()` re-derives tier 1, the in-force large-exposure
percentage limit, and the subject's control-basis group exposure and
post-haircut collateral every run, then asserts its own arithmetic before
handing anything to the loader. A proposal that failed its own sizing check
would be a number nobody verified, which is the exact failure this wave
exists to avoid (CLAUDE.md's "counted but not created").

- **`breaches`** -- subject Bausch Health Companies Inc.
  (`B3BS7ACMDUWISF18KY76`), the largest real control-basis group ($16.0bn).
  **Fix round 1** (coordinator finding, Task 15's floors): the original
  $58bn sizing breached gross but fell back UNDER the limit once its own
  group's real collateral was netted -- indistinguishable from
  `fits_after_mitigation` and, per §B, mitigation defaults to `true` on a
  request, so under the product's own default NEITHER proposal breached.
  A $75bn hypothetical facility fixes this: gross exposure reaches
  ~$91.01bn and NET of the group's $12.58bn post-haircut collateral still
  sits at ~$78.43bn -- over the 25%-of-tier-1 limit (~$73.94bn) both ways,
  so mitigation cannot rescue it. $75bn is more than the estate's entire
  booked commitment total ($55.7bn across 60 facilities) -- unmistakably
  hypothetical, never booked.
- **`fits_after_mitigation`** -- subject TransDigm Group Inc
  (`549300EQD0ZXRSMG3549`), a $14.6bn singleton (zero `connectedTo` edges).
  A $59.4bn hypothetical facility takes gross exposure to exactly $74.0bn --
  just over the line -- but TransDigm already carries $12.9bn of real,
  post-haircut pledged collateral (`ccf_v2.collateral_pledge` joined through
  `ccf_v2.haircut_schedule`). Net of that collateral, exposure falls to
  ~$61.1bn -- back under the line. The flip is real arithmetic over real
  collateral rows; nothing about the flip is stored anywhere.

`expected_outcome` documents intent only. Task 15's floors recompute the
actual gross/net crossing from the stores on every run and never read this
column -- so the arithmetic above must not (and does not) depend on it.

**Why these are now two distinct cases, not one twice.** `breaches` exceeds
the limit gross AND net -- mitigation is not enough to save it, ever.
`fits_after_mitigation` exceeds the limit gross but sits under it net --
mitigation is exactly enough to save it. `verify_proposal_sizing()` below
enforces this distinction as a live assertion on every run, not merely as a
comment: a `breaches` proposal whose net-of-collateral figure ever dropped
under the limit would fail the build rather than silently collapsing back
into the other case.

## Task 14 -- MEASURE first; this task may add nothing

`ccf_v2.context_debt` is a record table (`debt_id`, `reason`, `subject_kind`,
`subject_key`) with no numeric score, and most of its rows key to a person,
not an entity -- aggregating it would either fail on a missing column or
silently mix people into an obligor-level figure. The float this task needs
is `ccf_v2.memo_context_debt.aggregate_debt`, keyed by `lei`, and the bound
is `validators/memo_debt.py::policy_tolerance(cur)` -- read live, never
hard-coded, because a copy of the tolerance here could drift from the policy
version actually in force.

`verify_debt_tolerance_condition()` forms groups from the live Fluree edges
(control-only, and control+dependency), sums `aggregate_debt` across each
group's members, and checks whether any group's sum already exceeds the live
tolerance. Measured 2026-08-27: **Container Store Group, Inc.**
(`529900L7KB2N9KXCDI76`)'s own `aggregate_debt` is 0.4875 against a live
tolerance of 0.25 -- already over on its own, and it sits in a 3-member
control-basis group (5-member under control+dependency). The condition is
satisfied by existing data. **This task adds no debt record.** Manufacturing
one anyway would be inventing data nobody needed, which CLAUDE.md's
provenance discipline exists to prevent -- if this ever stops being true (a
reload changes the debt figures or the policy tolerance), the function below
raises rather than silently doing nothing, so the gap is caught, not papered
over with an invented row nobody asked this session to add.

Output: sources/screening/wave19_proposals.json (`loaders/load_wave19_postgres.py`
reads it and writes `ccf_v2.exposure_proposal`).

    uv run generators/generate_proposals.py
    uv run generators/generate_proposals.py --dry-run   # skip writing the artifact
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from decimal import Decimal

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2 as L, PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect
from validators.memo_debt import policy_tolerance

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave19_proposals.json"

PROVENANCE = "synthetic — engineered"

#: (subject_lei, label, facility_type, commitment_amount, currency,
#:  expected_outcome)
#:
#: expected_outcome documents INTENT ONLY -- see module docstring. It is
#: never read by Task 15's floors, so the numbers above must stand on their
#: own arithmetic, checked live by `verify_proposal_sizing()` below.
PROPOSALS = [
    (
        "B3BS7ACMDUWISF18KY76",   # Bausch Health Companies Inc.
        "Bausch Health Companies Inc.",
        "Term Loan",
        Decimal("75000000000"),
        "USD",
        "breaches",
    ),
    (
        "549300EQD0ZXRSMG3549",  # TransDigm Group Inc
        "TransDigm Group Inc",
        "Revolving Credit Facility",
        Decimal("59400000000"),
        "USD",
        "fits_after_mitigation",
    ),
]


# --------------------------------------------------------------------------
# Live recomputation -- the numbers above are checked, not trusted
# --------------------------------------------------------------------------

def entity_uri_to_lei() -> dict[str, str]:
    q = f"SELECT ?s ?l FROM <{L}> WHERE {{ ?s <{EX}lei> ?l }}"
    return {b["s"]["value"]: b["l"]["value"]
            for b in fluree.query(q)["results"]["bindings"]}


def _components(predicates: list[str]) -> tuple[dict[str, str], "callable"]:
    """Union-find over the named Fluree predicates. `FILTER(?s = ?o)` is not
    needed: on this build `?s <p> ?o` does not enforce `?s != ?o`, but none
    of `connectedTo` / `economicallyDependentOn` ever relates a node to
    itself in this estate, and the loop below only ever compares resolved
    roots, never raw triples -- the same reasoning Task 9's
    `derive_group_exposures()` already documents for this exact code shape.
    """
    par: dict[str, str] = {}

    def find(x: str) -> str:
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for p in predicates:
        q = f"SELECT ?a ?b FROM <{L}> WHERE {{ ?a <{EX}{p}> ?b }}"
        for r in fluree.query(q)["results"]["bindings"]:
            a, b = find(r["a"]["value"]), find(r["b"]["value"])
            if a != b:
                par[a] = b
    return par, find


def control_group_exposure(cur, subject_lei: str) -> tuple[list[str], float, float]:
    """This subject's control-basis (`connectedTo` only) group: member LEIs,
    summed booked exposure, and summed POST-HAIRCUT collateral value.

    Control basis, not control+dependency, because the design doc's own
    measurement of "the largest group is $16.0bn" (Bausch Health, Task 7's
    report) is a control-basis figure -- sizing against the wrong basis
    would size the proposal against a number nobody actually measured.
    """
    uri_to_lei = entity_uri_to_lei()
    uri_by_lei = {lei: uri for uri, lei in uri_to_lei.items()}
    if subject_lei not in uri_by_lei:
        raise AssertionError(f"{subject_lei} has no Fluree node with ex:lei -- "
                              "run loaders/load_group_edges.py first")

    par, find = _components(["connectedTo"])
    root = find(uri_by_lei[subject_lei])
    members = sorted(lei for uri, lei in uri_to_lei.items() if find(uri) == root)

    cur.execute(f'SELECT borrower_lei, SUM(COALESCE(commitment_amount, 0)) '
                f'FROM "{S}".facility WHERE borrower_lei = ANY(%s) '
                f'GROUP BY borrower_lei', (members,))
    exposure = sum(float(amt) for _, amt in cur.fetchall())

    cur.execute(f'''
        SELECT ca.valuation, ca.haircut
        FROM "{S}".collateral_pledge p
        JOIN "{S}".collateral_asset ca ON ca.asset_id = p.asset_id
        JOIN "{S}".facility f ON f.facility_id = p.facility_id
        WHERE f.borrower_lei = ANY(%s)
    ''', (members,))
    collateral = sum(float(val) * (1 - float(hc)) for val, hc in cur.fetchall())

    return members, exposure, collateral


def latest_tier1_usd(cur) -> float:
    """Reporting bank's own most recent tier 1, unit-corrected. Filtered by
    RSSD (not just `ORDER BY report_date DESC LIMIT 1`) because a future
    wave could add a peer bank's row on the same date -- `bank_capital`
    happens to hold only the reporting bank today (852218, 12 rows), but
    filtering explicitly costs nothing and does not rely on that staying
    true."""
    from loaders.load_wave19_postgres import REPORTING_BANK_RSSD
    cur.execute(f'SELECT tier1_capital, unit FROM "{S}".bank_capital '
                f'WHERE rssd = %s ORDER BY report_date DESC LIMIT 1',
                (REPORTING_BANK_RSSD,))
    row = cur.fetchone()
    if row is None:
        raise AssertionError("no bank_capital row for the reporting bank -- "
                              "run loaders/load_reporting_bank.py first")
    amount, unit = row
    return float(amount) * (1000 if unit == "USD_THOUSANDS" else 1)


def current_pct_limit_fraction() -> float:
    """The large-exposure percentage limit actually in force right now, read
    from the live `ex:RegimeVersion` history Task 9/10 loaded -- never a
    bare `0.25` in this file. 'In force' = has `limitPctOfCapital` and no
    `effectiveTo` (open-ended; superseded versions like CRR 2014-2021 carry
    a real `effectiveTo` and are excluded by construction, not by date
    arithmetic against today)."""
    q = (f"SELECT ?s ?pct FROM <{L}> WHERE {{ ?s a <{EX}RegimeVersion> . "
         f"?s <{EX}limitPctOfCapital> ?pct . "
         f"FILTER NOT EXISTS {{ ?s <{EX}effectiveTo> ?end }} }}")
    rows = fluree.query(q).get("results", {}).get("bindings", [])
    pcts = {float(b["pct"]["value"]) for b in rows}
    if not pcts:
        raise AssertionError("no in-force RegimeVersion carries "
                              "limitPctOfCapital -- run loaders/load_policy_fluree.py")
    if len(pcts) > 1:
        raise AssertionError(f"in-force regimes disagree on the percentage "
                              f"limit: {sorted(pcts)} -- which one binds?")
    return pcts.pop() / 100.0


def verify_proposal_sizing(cur, proposal: dict, tier1_usd: float, pct_limit: float) -> None:
    """Refuse to hand the loader a proposal whose own arithmetic does not
    hold, live -- the same discipline `generate_limit_envelope.py`'s
    `verify_appetite_placement()` applies to the internal appetite.  A
    proposal that failed this and got written anyway would be a number
    nobody actually checked."""
    threshold = tier1_usd * pct_limit
    gross = proposal["existing_exposure_usd"] + float(proposal["commitment_amount"])
    net = gross - proposal["existing_collateral_usd"]
    outcome = proposal["expected_outcome"]

    if outcome == "breaches":
        # Net, not just gross -- fix round 1 (coordinator finding). A
        # proposal that only breaches gross is indistinguishable from
        # `fits_after_mitigation` once mitigation is applied, and per section B's
        # request-parameter table `apply_mitigation` defaults to true, so a
        # gross-only breach would breach nothing under the product's own
        # default. `breaches` must survive mitigation entirely.
        if not gross > threshold:
            raise AssertionError(
                f"{proposal['label']}: gross ${gross/1e9:.4f}bn does not "
                f"exceed the ${threshold/1e9:.4f}bn limit -- 'breaches' does "
                "not hold")
        if not net > threshold:
            raise AssertionError(
                f"{proposal['label']}: net-of-collateral ${net/1e9:.4f}bn "
                f"does not exceed the ${threshold/1e9:.4f}bn limit -- this "
                "proposal only breaches gross, which collapses into "
                "'fits_after_mitigation' once mitigation is applied")
    elif outcome == "fits_after_mitigation":
        if not gross > threshold:
            raise AssertionError(
                f"{proposal['label']}: gross ${gross/1e9:.4f}bn does not "
                f"exceed the ${threshold/1e9:.4f}bn limit before mitigation "
                "-- there is no line to fit under AFTER mitigation")
        if not net < threshold:
            raise AssertionError(
                f"{proposal['label']}: net-of-collateral ${net/1e9:.4f}bn "
                f"still exceeds the ${threshold/1e9:.4f}bn limit -- "
                "mitigation is not load-bearing for this proposal")
    else:
        raise AssertionError(f"unknown expected_outcome {outcome!r}")

    proposal["_gross_usd"] = gross
    proposal["_net_of_collateral_usd"] = net
    proposal["_threshold_usd"] = threshold


def build_proposals(cur) -> list[dict]:
    tier1_usd = latest_tier1_usd(cur)
    pct_limit = current_pct_limit_fraction()

    out = []
    for subject_lei, label, facility_type, amount, currency, outcome in PROPOSALS:
        members, exposure, collateral = control_group_exposure(cur, subject_lei)
        proposal = {
            "proposal_id": f"PROP-{subject_lei}-{outcome.upper()}",
            "subject_lei": subject_lei,
            "label": label,
            "facility_type": facility_type,
            "commitment_amount": amount,
            "currency": currency,
            "is_hypothetical": True,
            "expected_outcome": outcome,
            "provenance": PROVENANCE,
            "existing_group_members": members,
            "existing_exposure_usd": exposure,
            "existing_collateral_usd": collateral,
        }
        verify_proposal_sizing(cur, proposal, tier1_usd, pct_limit)
        out.append(proposal)
    return out


# --------------------------------------------------------------------------
# Task 14 -- debt-tolerance condition, MEASURED, not engineered
# --------------------------------------------------------------------------

def _group_debt_sums(cur, predicates: list[str]) -> list[tuple[float, list[str]]]:
    """(sum of aggregate_debt across the group, member LEIs) for every group
    formed over the named Fluree predicates. A member with no
    `memo_context_debt` row contributes 0 -- absence is not evidence of low
    debt, but this task only needs to find groups ALREADY over tolerance,
    and treating a missing row as anything other than 0 could only ever
    raise the sum, never lower it, so it cannot manufacture a false breach.
    """
    uri_to_lei = entity_uri_to_lei()
    par, find = _components(predicates)

    cur.execute(f'SELECT lei, aggregate_debt FROM "{S}".memo_context_debt')
    debt = {lei.strip(): float(v) for lei, v in cur.fetchall()}

    groups: dict[str, list[str]] = defaultdict(list)
    for uri, lei in uri_to_lei.items():
        groups[find(uri)].append(lei)

    return [(sum(debt.get(l, 0.0) for l in leis), leis)
            for leis in groups.values() if any(l in debt for l in leis)]


def verify_debt_tolerance_condition(cur) -> dict:
    """Recompute, live, whether §F's "≥ 1 group breaching debt_tolerance"
    condition already holds. See the module docstring for what was found
    2026-08-27 and why nothing is engineered here.

    Raises if the condition no longer holds against live data -- on
    purpose. This function does not fall back to writing a debt record: if
    a future reload ever moves `aggregate_debt` or the policy tolerance
    enough to close the gap, that is new information this session was never
    asked to act on, and silently inventing a record to paper over it would
    be exactly the "counted but not created" failure CLAUDE.md warns about.
    """
    tol = policy_tolerance(cur)
    control = _group_debt_sums(cur, ["connectedTo"])
    both = _group_debt_sums(cur, ["connectedTo", "economicallyDependentOn"])

    control_breach = max((g for g in control if g[0] > tol), default=None,
                          key=lambda g: g[0])
    both_breach = max((g for g in both if g[0] > tol), default=None,
                       key=lambda g: g[0])

    if control_breach is None and both_breach is None:
        raise AssertionError(
            f"no group exceeds the live debt tolerance {tol} under either "
            "basis -- the condition this task recorded as already-satisfied "
            "no longer holds; this generator does not silently add a debt "
            "record to compensate, ask before engineering one")

    return {
        "tolerance": tol,
        "control_basis": control_breach,
        "both_basis": both_breach,
        "engineered": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("Wave 19 Task 13/14 — proposals + debt-tolerance measurement\n")
    with pg_connect() as conn, conn.cursor() as cur:
        proposals = build_proposals(cur)
        debt = verify_debt_tolerance_condition(cur)
        conn.rollback()  # read-only in this generator; the loader writes

    print("  Proposals (sizing verified live):")
    for p in proposals:
        print(f"    {p['proposal_id']:<32} {p['label']}")
        print(f"      existing group   ${p['existing_exposure_usd']/1e9:.4f}bn "
              f"across {len(p['existing_group_members'])} member(s), "
              f"collateral ${p['existing_collateral_usd']/1e9:.4f}bn")
        print(f"      + proposal       ${float(p['commitment_amount'])/1e9:.4f}bn"
              f"  = gross ${p['_gross_usd']/1e9:.4f}bn"
              f"  vs limit ${p['_threshold_usd']/1e9:.4f}bn")
        print(f"      net of collateral ${p['_net_of_collateral_usd']/1e9:.4f}bn"
              f"   expected_outcome={p['expected_outcome']!r}")

    print(f"\n  Debt tolerance (live, {debt['tolerance']}):")
    if debt["control_basis"]:
        s, leis = debt["control_basis"]
        print(f"    control-basis breach   sum={s:.4f}  n={len(leis)}  {leis}")
    if debt["both_basis"]:
        s, leis = debt["both_basis"]
        print(f"    both-basis breach      sum={s:.4f}  n={len(leis)}  {leis}")
    print("    already satisfied by existing data — nothing engineered")

    if args.dry_run:
        print("\n  [dry-run] artifact not written")
        return 0

    doc = {
        "proposals": [
            {k: (str(v) if isinstance(v, Decimal) else v)
             for k, v in p.items() if not k.startswith("_")}
            for p in proposals
        ],
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
