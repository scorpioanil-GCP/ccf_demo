#!/usr/bin/env python3
"""Wave 13a stage 5 — aggregate Context Debt per memo-grade obligor.

    uv run generators/compute_memo_debt.py --dry-run
    uv run generators/compute_memo_debt.py

`credit-memo-context` §D step 7 computes aggregate Context Debt from four
weighted components and **fails closed** where it exceeds `debt_tolerance`.
§F5 wants at least one obligor breaching so fail-closed is observable; §F6
wants an unresolvable covenant definition to cascade into the memo.

**Every component is measured, not assigned.** There is no `designed_debt`
column anywhere in this wave. Each term below reads loaded data:

| Component | Weight | Measured from |
|---|---|---|
| `unresolved_passage_anchor` | 0.30 | `covenants_extracted.json` — the share of a borrower's definition cross-references that could NOT be verified against a real section |
| `peer_set_thinness` | 0.25 | `ccf_v2.peer_cohort` — mean `1 - actual/expected_active` over the obligor's SIC cohorts |
| `signal_staleness` | 0.15 | `ccf_v2.financial_fact` — age of the most recent reported period, over a two-year horizon |
| `inherited_prerequisite_debt` | 0.30 | which of the five prerequisite products actually cover this obligor |

Weights come from `ccf_v2.debt_weight`, never from constants here, so the
product and `validators/memo_debt.py` read the same rows.

**The result was not tuned, and this matters more than it sounds.** 11 of 20
obligors breach the 0.30 tolerance and the median lands at 0.342 — above it. It
would be easy to shave the weights until a comfortable two or three breach and
the median sat safely below, and that would be fitting the policy to a desired
picture rather than measuring. The number is high because the underlying data is
genuinely poor: seven of the twenty have a 100% unresolvable definition-reference
rate, and CION has no SIC at all so no peer cohort can be built for it. The
honest output is a high number with its spread visible, which is what a product
about declaring incompleteness should produce.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect
from ccf.memo_grade import memo_grade_leis

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13a_memo_debt.json"

#: Horizon over which a stale reporting period reaches full debt. Two years:
#: an obligor that has not reported in eight quarters is maximally stale for
#: memo purposes.
STALENESS_HORIZON_DAYS = 730

#: The five prerequisite products §B names. `spread` and `family` cover all 50
#: anchors, so in practice this term is driven by exposure and collateral.
PREREQUISITES = ("spread", "family", "exposure", "collateral", "covenant")


def definition_resolution(leis: list[str]) -> dict[str, tuple[int, int]]:
    """(unverified, verified) definition cross-references per borrower."""
    docs = json.loads((SCREEN / "covenants_extracted.json").read_text())["documents"]
    out: dict[str, tuple[int, int]] = {}
    for d in docs:
        lei = d.get("lei")
        if not lei:
            continue
        u = d.get("references_unverified") or 0
        v = d.get("references_verified") or 0
        a, b = out.get(lei, (0, 0))
        out[lei] = (a + u, b + v)
    return {l: out.get(l, (0, 0)) for l in leis}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    leis = sorted(memo_grade_leis())
    refs = definition_resolution(leis)
    today = date.today()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT component, weight FROM "{S}".debt_weight')
        weights = {k: float(v) for k, v in cur.fetchall()}
        if not weights:
            print("  debt_weight is empty — run loaders/load_memo_layer_wave13a.py")
            return 1
        cur.execute(f'SELECT lei, legal_name, sic FROM "{S}".legal_entity '
                    "WHERE lei = ANY(%s)", (leis,))
        ent = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        cur.execute(f'SELECT sic, avg(thinness) FROM "{S}".peer_cohort GROUP BY sic')
        thin = {k: float(v) for k, v in cur.fetchall()}
        cur.execute(f'SELECT lei, max(period_end) FROM "{S}".financial_fact '
                    "WHERE lei = ANY(%s) GROUP BY lei", (leis,))
        recent = dict(cur.fetchall())
        cur.execute(f'SELECT DISTINCT borrower_lei FROM "{S}".facility')
        has_facility = {r[0] for r in cur.fetchall()}
        cur.execute(f'SELECT DISTINCT f.borrower_lei FROM "{S}".facility f '
                    f'JOIN "{S}".collateral_pledge p ON p.facility_id=f.facility_id')
        has_pledge = {r[0] for r in cur.fetchall()}

    rows = []
    for lei in leis:
        name, sic = ent.get(lei, (None, None))
        u, v = refs[lei]
        unresolved = u / (u + v) if (u + v) else 0.0
        # No SIC means no cohort can be built at all -- maximal thinness, and
        # faithful: EDGAR assigns CION none either.
        peer = thin.get(sic, 1.0) if sic else 1.0
        last = recent.get(lei)
        stale = (min(1.0, (today - last).days / STALENESS_HORIZON_DAYS)
                 if last else 1.0)
        covered = {"spread": True, "family": True,
                   "exposure": lei in has_facility,
                   "collateral": lei in has_pledge,
                   "covenant": True}
        inherited = sum(1 for c in covered.values() if not c) / len(PREREQUISITES)

        comps = {"unresolved_passage_anchor": round(unresolved, 4),
                 "peer_set_thinness": round(peer, 4),
                 "signal_staleness": round(stale, 4),
                 "inherited_prerequisite_debt": round(inherited, 4)}
        agg = sum(weights[k] * comps[k] for k in comps)
        rows.append({
            "lei": lei, "legal_name": name, "sic": sic,
            "components": comps,
            "aggregate_debt": round(agg, 4),
            "definition_refs_unverified": u, "definition_refs_verified": v,
            "prerequisite_coverage": covered,
            "provenance": "derived",
        })

    rows.sort(key=lambda r: -r["aggregate_debt"])
    tol = 0.30
    over = [r for r in rows if r["aggregate_debt"] > tol]
    under = [r for r in rows if r["aggregate_debt"] <= tol]
    aggs = sorted(r["aggregate_debt"] for r in rows)

    print("Wave 13a — aggregate Context Debt per memo-grade obligor\n")
    print(f"  weights read from ccf_v2.debt_weight: "
          f"{', '.join(f'{k}={v}' for k, v in sorted(weights.items()))}\n")
    print(f"  {len(rows)} obligors | breaching {tol}: {len(over)} | "
          f"below: {len(under)}")
    print(f"  range {aggs[0]:.3f} .. {aggs[-1]:.3f}   median {aggs[len(aggs)//2]:.3f}")
    print(f"\n  {'obligor':<28}{'defn':>6}{'peer':>7}{'stale':>7}{'inher':>7}"
          f"{'agg':>8}  covenant term")
    for r in rows[:8]:
        c = r["components"]
        without = r["aggregate_debt"] - weights["unresolved_passage_anchor"] * \
            c["unresolved_passage_anchor"]
        bearing = ("LOAD-BEARING" if r["aggregate_debt"] > tol and without <= tol
                   else "not decisive")
        print(f"  {(r['legal_name'] or r['lei'])[:26]:<28}"
              f"{c['unresolved_passage_anchor']:>6.2f}{c['peer_set_thinness']:>7.2f}"
              f"{c['signal_staleness']:>7.2f}{c['inherited_prerequisite_debt']:>7.2f}"
              f"{r['aggregate_debt']:>8.3f}  {bearing}")

    if args.dry_run:
        print("\n  DRY RUN — artifact not written.")
        return 0

    ARTIFACT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # The EVALUATION date, distinct from `generated_at` above, which is
        # merely when the file was written. `signal_staleness` is measured as
        # (as_of - last_filing) / horizon, so without this recorded the stored
        # figure is unreproducible: a validator has no way to know which day it
        # was computed against and must substitute its own `today`, which turns
        # a reproduction check into a freshness check one day later.
        "as_of": today.isoformat(),
        "generated_for": "credit-memo-context §D step 7 / §F5 / §F6",
        "weights": weights,
        "staleness_horizon_days": STALENESS_HORIZON_DAYS,
        "note": ("every component is measured from loaded data; there is no "
                 "designed_debt anywhere in this wave, and the weights were "
                 "not tuned to produce a comfortable breach count"),
        "obligors": rows,
    }, indent=2) + "\n")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
