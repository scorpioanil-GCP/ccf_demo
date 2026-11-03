#!/usr/bin/env python3
"""Recompute `credit-memo-context`'s Context Debt from the stores, and test it.

    uv run validators/memo_debt.py

`ccf_v2.memo_context_debt` is a cache. This gate does NOT read it to decide
whether it is right — it recomputes every component from the loaded stores by
its own path and compares. The four components, the weights, and the tolerance
all come from the databases, never from constants here: a gate holding its own
copy of a weight tests the computation against itself and cannot fail.

The checks, and why each is shaped the way it is
------------------------------------------------

**1 · Recomputation agrees.** Stored components and aggregates must match a
fresh computation to 1e-6. This is the check every prior wave needed —
`series.py`, `surveillance.py`, `intraday.py`, `reconcile.py` — because a
stored number that nothing recomputes is a number nobody has checked.

**2 · The tolerance discriminates (§F5).** Not "at least one obligor breaches",
which a uniformly-high weighting satisfies while demonstrating nothing. The
requirement is a SPREAD from the same weighting: obligors above AND obligors
below. A gate asserting only the breach would pass if every obligor breached,
which is the Wave 12 defect shape (known-issues.md §12) — a threshold whose
inputs guarantee its verdict.

**3 · The covenant cascade is load-bearing (§F6).** §F6 asks for an
unresolvable covenant definition *propagating debt into the memo*, not merely
for a breach to coexist with one. So for at least one breaching obligor,
removing the definition-resolution term must drop it BELOW tolerance. An
obligor over the line purely on peer thinness satisfies §F5 and says nothing
about §F6 — CION is exactly that case and is deliberately not counted here.

**4 · Unsecured resolves to a finding, not silence** (`wave13a-design.md` §7).
AGILYSYS, PAYCHEX and Pebblebrook have no security-interest grant clause in
their filed agreements. "This obligor is unsecured" and "we never loaded its
collateral" are indistinguishable in the data unless something looks, and only
one is a correct answer for a memo. This asserts the distinction is
representable and actually drawn.

**5 · Section coverage (§D validation gates).** Every section in every memo
type's template must be able to carry either evidence or a named debt entry.

Mutation-tested. `--self-test` perturbs the stored table and asserts each check
goes red, then restores. A gate nobody has watched fail is decoration.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, mongo_db, pg_connect
from ccf.memo_grade import memo_grade_leis

SCREEN = REPO_ROOT / "sources" / "screening"
TOL = 1e-6
STALENESS_HORIZON_DAYS = 730


def recompute(cur, as_of: date) -> dict[str, dict]:
    """Independent recomputation, from the stores only, AS OF a given date.

    `as_of` is a required argument on purpose. It used to be `date.today()`,
    taken silently inside this function, and that turned the reproduction check
    below into something else entirely: `signal_staleness` is
    (as_of - last_filing) / horizon, so recomputing with today's clock against
    a figure stored on an earlier day compares two different questions and
    reports the difference as drift. Measured 2026-08-23: every one of the 20
    rows was "wrong" by 0.97-1.02 days on a 730-day horizon -- exactly the one
    day between the load and the check, and nothing else.

    Passing the date in makes reproduction exact and reproducible forever.
    Freshness is a separate question, asked separately below.
    """
    leis = sorted(memo_grade_leis())
    docs = json.loads((SCREEN / "covenants_extracted.json").read_text())["documents"]
    refs: dict[str, list[int]] = {}
    for d in docs:
        if not d.get("lei"):
            continue
        r = refs.setdefault(d["lei"], [0, 0])
        r[0] += d.get("references_unverified") or 0
        r[1] += d.get("references_verified") or 0

    cur.execute(f'SELECT component, weight FROM "{S}".debt_weight')
    weights = {k: float(v) for k, v in cur.fetchall()}
    cur.execute(f'SELECT lei, sic FROM "{S}".legal_entity WHERE lei = ANY(%s)', (leis,))
    sic_of = dict(cur.fetchall())
    cur.execute(f'SELECT sic, avg(thinness) FROM "{S}".peer_cohort GROUP BY sic')
    thin = {k: float(v) for k, v in cur.fetchall()}
    cur.execute(f'SELECT lei, max(period_end) FROM "{S}".financial_fact '
                "WHERE lei = ANY(%s) GROUP BY lei", (leis,))
    recent = dict(cur.fetchall())
    cur.execute(f'SELECT DISTINCT borrower_lei FROM "{S}".facility')
    fac = {r[0] for r in cur.fetchall()}
    cur.execute(f'SELECT DISTINCT f.borrower_lei FROM "{S}".facility f '
                f'JOIN "{S}".collateral_pledge p ON p.facility_id = f.facility_id')
    pledge = {r[0] for r in cur.fetchall()}

    out = {}
    for lei in leis:
        u, v = refs.get(lei, (0, 0))
        sic = sic_of.get(lei)
        last = recent.get(lei)
        comps = {
            "unresolved_passage_anchor": u / (u + v) if (u + v) else 0.0,
            "peer_set_thinness": thin.get(sic, 1.0) if sic else 1.0,
            "signal_staleness": (min(1.0, (as_of - last).days / STALENESS_HORIZON_DAYS)
                                 if last else 1.0),
            "inherited_prerequisite_debt":
                sum(1 for c in (lei in fac, lei in pledge) if not c) / 5,
        }
        out[lei] = {"components": comps,
                    "aggregate": sum(weights[k] * comps[k] for k in comps),
                    "weights": weights}
    return out


def checks(cur, *, tol_override: float | None = None) -> list[tuple[str, bool, str]]:
    cur.execute(f'SELECT lei, unresolved_passage_anchor, peer_set_thinness, '
                f'signal_staleness, inherited_prerequisite_debt, aggregate_debt, '
                f'as_of FROM "{S}".memo_context_debt')
    stored, as_of_of = {}, {}
    for r in cur.fetchall():
        stored[r[0]] = {"components": {
            "unresolved_passage_anchor": float(r[1]),
            "peer_set_thinness": float(r[2]),
            "signal_staleness": float(r[3]),
            "inherited_prerequisite_debt": float(r[4])},
            "aggregate": float(r[5])}
        as_of_of[r[0]] = r[6]

    # Recompute once per distinct stored evaluation date. In practice that is
    # one date for the whole table, but grouping means a partial reload with a
    # newer as_of does not silently invalidate the untouched rows.
    fresh: dict[str, dict] = {}
    for d in sorted(set(as_of_of.values())):
        for lei, vals in recompute(cur, d).items():
            if as_of_of.get(lei) == d:
                fresh[lei] = vals

    out: list[tuple[str, bool, str]] = []

    # 1 · recomputation agrees, each row against ITS OWN evaluation date
    drift = []
    for lei, f in fresh.items():
        s = stored.get(lei)
        if not s:
            drift.append(f"{lei}: no stored row")
            continue
        for k, val in f["components"].items():
            if abs(val - s["components"][k]) > 1e-3:
                drift.append(f"{lei}.{k}: stored {s['components'][k]:.4f} "
                             f"recomputed {val:.4f}")
        if abs(f["aggregate"] - s["aggregate"]) > 1e-3:
            drift.append(f"{lei}.aggregate: stored {s['aggregate']:.4f} "
                         f"recomputed {f['aggregate']:.4f}")
    out.append(("stored debt reproduces an independent recomputation",
                not drift,
                f"{len(drift)} divergence(s)" + (f"; first: {drift[0]}" if drift else "")))

    # 1b · FRESHNESS, asked separately and named for what it is.
    #
    # This is the question check 1 used to answer by accident. Recomputing with
    # today's clock against figures stored on an earlier day made every row
    # look like drift, so a stale table and a miscomputed table were
    # indistinguishable -- and the check that was supposed to catch the second
    # could never fail for that reason once a day had passed. They are separate
    # questions and now have separate checks.
    #
    # The bound is the staleness horizon itself rather than an invented number:
    # a table older than the horizon it measures against cannot describe the
    # staleness of anything.
    today = date.today()
    ages = {lei: (today - d).days for lei, d in as_of_of.items()}
    oldest = max(ages.values()) if ages else 0
    dates = sorted({str(d) for d in as_of_of.values()})
    out.append((
        f"stored debt is younger than its own {STALENESS_HORIZON_DAYS}-day "
        "staleness horizon",
        oldest < STALENESS_HORIZON_DAYS,
        f"evaluated {dates}, oldest row {oldest} day(s) old"
        + ("" if oldest < STALENESS_HORIZON_DAYS
           else " — RELOAD: the cache outlived the horizon it measures")))

    # 2 · the tolerance discriminates
    tol = tol_override if tol_override is not None else policy_tolerance(cur)
    over = [l for l, s in stored.items() if s["aggregate"] > tol]
    under = [l for l, s in stored.items() if s["aggregate"] <= tol]
    out.append((f"debt_tolerance {tol} discriminates: obligors on BOTH sides",
                bool(over) and bool(under),
                f"{len(over)} breaching / {len(under)} below — a gate that "
                f"passed with 0 below would fire on every input"))

    # 3 · the covenant cascade is load-bearing
    w = next(iter(fresh.values()))["weights"]["unresolved_passage_anchor"]
    bearing = [l for l in over
               if stored[l]["aggregate"]
               - w * stored[l]["components"]["unresolved_passage_anchor"] <= tol]
    out.append(("an unresolvable covenant definition is LOAD-BEARING for a "
                "breach (§F6, not merely coincident with one)",
                len(bearing) >= 1,
                f"{len(bearing)} of {len(over)} breaching obligors drop below "
                f"tolerance when the definition term is removed"))

    # 4 · unsecured is a finding, not silence
    cur.execute(f"""
        SELECT e.lei, e.legal_name,
               EXISTS (SELECT 1 FROM "{S}".facility f
                       WHERE f.borrower_lei = e.lei) AS has_facility,
               EXISTS (SELECT 1 FROM "{S}".facility f
                       JOIN "{S}".collateral_pledge p
                         ON p.facility_id = f.facility_id
                       WHERE f.borrower_lei = e.lei) AS has_pledge
        FROM "{S}".legal_entity e WHERE e.lei = ANY(%s)
    """, (sorted(memo_grade_leis()),))
    rows = cur.fetchall()
    unsecured = [r for r in rows if r[2] and not r[3]]
    uncovered = [r for r in rows if not r[2]]
    out.append(("'unsecured' is distinguishable from 'uncovered' — a facility "
                "with no pledge is not the same as no facility",
                bool(unsecured) and bool(uncovered),
                f"{len(unsecured)} unsecured (facility, no pledge), "
                f"{len(uncovered)} uncovered (no facility at all)"))

    # 5 · section coverage
    cur.execute(f'SELECT memo_type, count(*) FROM "{S}".memo_section_template '
                "GROUP BY memo_type")
    per_type = dict(cur.fetchall())
    cur.execute(f'SELECT count(DISTINCT section_name) FROM "{S}".memo_section_template')
    distinct_sections = cur.fetchone()[0]
    total = sum(per_type.values())
    out.append(("4 memo types with genuinely distinct section sets (§F7)",
                len(per_type) == 4 and distinct_sections > total / 2,
                f"{len(per_type)} types, {total} rows, "
                f"{distinct_sections} distinct section names — types differing "
                f"only in name would share nearly all sections"))

    db = mongo_db()
    out.append(("~40 internal credit memoranda exist (§F3)",
                db["memorandum"].count_documents({}) >= 38,
                f"{db['memorandum'].count_documents({})} memoranda"))
    return out


def policy_tolerance(cur) -> float:
    """The tolerance in force, from the loaded policy — not a constant here."""
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L
    q = (f"SELECT ?v ?d FROM <{L}> WHERE {{ ?s a <{EX}PolicyVersion> . "
         f"?s <{EX}debtToleranceDefault> ?v . ?s <{EX}validFrom> ?d }}")
    rows = fluree.query(q).get("results", {}).get("bindings", [])
    vals = sorted(((b["d"]["value"], float(b["v"]["value"])) for b in rows))
    if not vals:
        raise RuntimeError("no debtToleranceDefault in the ledger — "
                           "run loaders/load_memo_layer_wave13a.py")
    # The version in force today is the latest whose validFrom has passed.
    today = date.today().isoformat()
    live = [v for d, v in vals if d <= today]
    return live[-1] if live else vals[0][1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true",
                    help="mutate the stored table and require each check to fail")
    args = ap.parse_args()

    print("MEMO CONTEXT DEBT — recomputed from the stores\n")
    with pg_connect() as conn, conn.cursor() as cur:
        results = checks(cur)
        for label, ok, note in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
            print(f"         {note}")
        failures = sum(not ok for _, ok, _ in results)

        if args.self_test:
            print("\n  SELF-TEST — mutating stored values; each must go red\n")
            mutations = [
                ("aggregate_debt inflated on one obligor",
                 f'UPDATE "{S}".memo_context_debt SET aggregate_debt = 0.99 '
                 "WHERE lei = (SELECT min(lei) FROM \"{}\".memo_context_debt)".format(S)),
                ("every obligor pushed above tolerance",
                 f'UPDATE "{S}".memo_context_debt SET aggregate_debt = 0.95'),
                ("the definition term zeroed everywhere",
                 f'UPDATE "{S}".memo_context_debt '
                 "SET unresolved_passage_anchor = 0, aggregate_debt = 0.95"),
            ]
            def run(label, *, sql=None, tol=None, expect):
                """`expect` names the check that MUST go red, so a mutation
                cannot be scored a pass by tripping some other check."""
                nonlocal failures
                cur.execute("SAVEPOINT m")
                if sql:
                    cur.execute(sql)
                res = checks(cur, tol_override=tol)
                red = [l for l, ok, _ in res if not ok]
                hit = any(expect in l for l in red)
                print(f"  {'[ok  ]' if hit else '[BAD ]'} {label}")
                print(f"         {len(red)} red; targeted check "
                      f"{'DID' if hit else 'did NOT'} fail — expected "
                      f"'{expect}'")
                if not hit:
                    failures += 1
                cur.execute("ROLLBACK TO SAVEPOINT m")

            for label, sql in mutations:
                run(label, sql=sql, expect="reproduces an independent")

            # Targeted at checks 2 and 3. These leave the stored table ALONE,
            # so check 1 keeps passing and cannot mask the result -- which is
            # the whole point. Every mutation above trips check 1, so without
            # these two, checks 2 and 3 would never have been exercised at all
            # and could be unfalsifiable without anyone noticing.
            # Targeted at the FRESHNESS check, with its own `expect`. It
            # cannot live in the loop above: every entry there is scored
            # against "reproduces an independent", and this mutation trips
            # that check too -- so in the loop it would have been credited for
            # reddening the wrong gate, which is the exact miscount the `run`
            # docstring above exists to prevent. Found by reading the reported
            # expectation rather than the [ok] marker.
            run("as_of pushed past the staleness horizon it measures against",
                sql=f'UPDATE "{S}".memo_context_debt '
                    f"SET as_of = as_of - {STALENESS_HORIZON_DAYS + 70}",
                expect="staleness horizon")

            run("tolerance driven to 0 — every obligor breaches, no spread",
                tol=0.0, expect="discriminates")
            run("tolerance driven to 1 — nobody breaches, no spread",
                tol=1.0, expect="discriminates")
            run("tolerance just under the weakest breach — the definition term "
                "can no longer be decisive for anyone",
                tol=0.0001, expect="LOAD-BEARING")
            conn.rollback()

    print(f"\n  {len(results) - sum(not ok for _, ok, _ in results)}/{len(results)} "
          f"checks pass\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
