#!/usr/bin/env python3
"""The one engineered condition: a trigger-definition amendment.

    uv run generators/generate_trigger_amendment.py
    uv run generators/generate_trigger_amendment.py --load

## Why this is invented, and why that is disclosed everywhere it appears

Auto ABS trigger definitions are fixed at issuance. Across 135 ABS-EE periods
and three prospectuses there is no amendment to find and there will not be
one. §F requires one so that as-of evaluation is not a decoration, so it is
built -- labelled `synthetic — engineered` in the JSON artifact and carried as
`ex:provenance "synthetic — engineered"` on its Fluree node, and deliberately
given NO passage anchor, because no filed sentence says it.

Presenting it as filed would be the misrepresentation CLAUDE.md's provenance
rule exists to prevent. Task 9 wrote `ex:passageAnchor` on all ten original
triggers; a reader who sees the predicate on nine nodes out of ten and asks
why one lacks it has found the right question.

## Choosing the new threshold

It must land close to the REAL, unmodified delinquency series. A threshold far
above it changes every proximity by a constant and proves nothing; one below
it would trip the trigger in every period and remove the trajectory. So it is
chosen from the loaded series: just above the window's observed maximum, so
proximity narrows toward it without breaching.

SDART-2022-6's twelve loaded periods run 9.98% to **11.30%**, the peak falling
in 2025-11. The amendment's effective date is the first of that month, so the
new threshold comes into force in the very period the series reaches for it.
13.50% clears the peak by 2.20 points: close enough that proximity moves, far
enough that no period breaches.

(An earlier draft of this task's plan quoted an observed peak of 10.79%. That
is a real filed figure -- it is the 2026-05 reading -- but it is not the
maximum. The guard below recomputes the peak from Postgres on every run rather
than trusting any number written into a comment, this one included.)

## Supersession is written FORWARD, and in the vocabulary that already exists

`ex:supersededBy` has been declared since Wave 5 and carries 215 assertions
since Wave 11a, always as `triple(older, supersededBy, newer)`. The binding
table in `docs/ccf_dataprep_v2.md` names minting `ex:supersedes` beside it as
the failure mode, in bold. So the edge here is

    <abs-trigger-...-delinquency> ex:supersededBy <...-delinquency-amendment>

subject the ORIGINAL, object the amendment. In an append-only store a
backwards edge is not a rename away from correct: both directions would live
in the ledger forever and every existing supersession query would miss this
one.

## The amendment asserts its threshold on a NEW node

Not on the original's. Re-asserting `ex:thresholdValue "13.50"` on the
original subject would leave the ledger holding two values for one
subject-predicate pair with nothing marking which is current -- a
contradiction, not a supersession. That is precisely what Task 9's
`ledger_conflicts` guard refuses to create as a side effect, and it is why
this operation gets its own script and its own deliberate act.

## Labelled, and reachable THROUGH THE CHAIN -- not by a second deal edge

The node carries an `rdfs:label`: Task 9 gave 33 labels to 33 nodes, and an
unlabelled node in the same slice is invisible to every label-driven listing.

It does **not** carry an inbound `specifiesTrigger` edge from the deal, and
that absence is the modelling decision, not an omission. SDART-2022-6
specifies **one** delinquency trigger, not two. A second `specifiesTrigger`
edge would assert the deal has two distinct delinquency triggers, which is
false: what happened is that one trigger's threshold was amended. The route
to the amendment is one hop longer, and that hop is the thing being
demonstrated:

    deal -specifiesTrigger-> original -supersededBy-> amendment

The edge was drafted and then dropped, for two reasons that agree. The
semantic one is above. The mechanical one is that Task 9's `ledger_conflicts`
guard requires the ledger's object set for a (subject, predicate) pair to be a
subset of what its run asserts -- so a fourth `specifiesTrigger` object on the
deal would have made `load_abs_fluree_wave14.py` refuse to re-run, forever, in
an append-only store. When the correct model and the guard agree, the guard
was right.

## Neither date is `now`

Stamping `assertedAt` with today's date would break the divergence check
silently: today is later than the amendment's own assertion date, so
`threshold_known_as_of` inside the gap would find no assertion at or before
the gap day and return `None`. The check would then pass on `13.50 != None`
-- green while measuring nothing. Both dates are literals, fixed here.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect

# Imported, not re-typed. These are the exact constants Task 9 used to write
# the ten original trigger nodes; a copied-and-drifted spelling here would
# produce an amendment that superseded nothing. `P_SPECIFIES_TRIGGER` is
# imported for the VERIFICATION query only -- this task deliberately asserts
# no edge on it, and checks after the write that the deal still specifies
# exactly the three triggers Task 9 gave it.
from loaders.load_abs_fluree_wave14 import (
    C_TRIGGER_EVENT, P_ASSERTED_AT, P_PROVENANCE, P_SPECIFIES_TRIGGER,
    P_THRESHOLD_COMPONENT, P_THRESHOLD_UNIT, P_THRESHOLD_VALUE, P_VALID_FROM,
    RDF_TYPE, RDFS_LABEL, Stmt, render, triple, uri,
)

S = PG_SCHEMA_V2
OUT = REPO_ROOT / "sources" / "absee" / "trigger_amendment.json"

TARGET_DEAL = "SDART-2022-6"
TARGET_TRIGGER = f"{TARGET_DEAL}-delinquency"

#: Bound since Wave 5, 215 assertions since Wave 11a. Do NOT mint
#: `ex:supersedes` -- see the module docstring and the binding table.
P_SUPERSEDED_BY = f"{EX}supersededBy"

#: Effective inside the window; asserted 71 days later. The lag is the point.
AMENDMENT = {
    "deal_id": TARGET_DEAL,
    "trigger_id": TARGET_TRIGGER,
    "effective_from": date(2025, 11, 1),
    "asserted_at": date(2026, 1, 11),
    "new_threshold": "13.50",
    "provenance": "synthetic — engineered",
    "passage_anchor": None,
    "label": "Delinquency Trigger (amended)",
    "rationale": (
        "Engineered so as-of and known-as-of evaluation diverge. Auto ABS "
        "triggers are fixed at issuance; no real amendment exists to load. "
        "The threshold sits just above the deal's observed delinquency "
        "maximum in the window, so proximity narrows without breaching."),
}

#: How far above the observed peak the engineered threshold may sit. Wider
#: than this and it stops biting: every period's proximity shifts by the same
#: constant and the trajectory demonstrates nothing.
MAX_HEADROOM = Decimal("4")


def threshold_as_of(chain: list[dict], when: date) -> str | None:
    """What the threshold WAS on `when`, by effective time."""
    live = [a for a in chain if a["effective_from"] <= when]
    return max(live, key=lambda a: a["effective_from"])["value"] if live else None


def threshold_known_as_of(chain: list[dict], when: date) -> str | None:
    """What we KNEW the threshold to be on `when`, by assertion time.

    The difference from `threshold_as_of` is the whole bitemporal claim: an
    amendment effective in November but booked in January was in force, and
    unknown, for 71 days.
    """
    known = [a for a in chain if a["asserted_at"] <= when]
    return max(known, key=lambda a: a["effective_from"])["value"] if known else None


def build_triples() -> list[Stmt]:
    """The amendment's assertions. Pure -- no store is read to build them.

    Kept separate from `main` so the exact triple list can be reviewed, and
    tested, before anything reaches an append-only ledger.
    """
    g_uri = uri(f"abs-trigger-{TARGET_TRIGGER}-amendment")
    orig = uri(f"abs-trigger-{TARGET_TRIGGER}")
    return [
        # Explicitly typed: Fluree does not reason, so a node answers only the
        # type queries it was given.
        triple(g_uri, RDF_TYPE, C_TRIGGER_EVENT),
        triple(g_uri, RDFS_LABEL, AMENDMENT["label"], literal=True),
        # Forward edge, old -> new. The ONLY inbound edge, and deliberately so
        # -- see "Reachable through the chain" in the module docstring.
        triple(orig, P_SUPERSEDED_BY, g_uri),
        triple(g_uri, P_THRESHOLD_VALUE, AMENDMENT["new_threshold"], literal=True),
        # Single-component, so the component equals the value. Emitted anyway:
        # Task 9 put at least one `thresholdComponent` on all ten originals, so
        # a consumer reading components rather than values would otherwise find
        # the amendment empty rather than find it single-valued.
        triple(g_uri, P_THRESHOLD_COMPONENT, AMENDMENT["new_threshold"],
               literal=True),
        triple(g_uri, P_THRESHOLD_UNIT, "percent_of_pool", literal=True),
        triple(g_uri, P_VALID_FROM,
               AMENDMENT["effective_from"].isoformat(), literal=True),
        triple(g_uri, P_ASSERTED_AT,
               AMENDMENT["asserted_at"].isoformat(), literal=True),
        triple(g_uri, P_PROVENANCE, AMENDMENT["provenance"], literal=True),
        # No ex:passageAnchor, deliberately. Nothing filed says this.
    ]


def observed_maximum() -> Decimal | None:
    """The deal's highest delinquency percentage across the window."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT MAX(published_delinquency_percent)
                        FROM "{S}".abs_servicer_report WHERE deal_id = %s""",
                    (TARGET_DEAL,))
        return cur.fetchone()[0]


def peak_period() -> str | None:
    """The period the maximum falls in -- reported so the figure can be
    checked against a filed report rather than taken on trust."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT period FROM "{S}".abs_servicer_report
                        WHERE deal_id = %s
                        ORDER BY published_delinquency_percent DESC, period
                        LIMIT 1""", (TARGET_DEAL,))
        row = cur.fetchone()
        return row[0].strip() if row else None


def _count(pattern: str) -> int:
    """One aggregate over the v2 ledger, read until consecutive reads agree.

    `stable_scalar`, never a bare query: a read issued immediately after
    INSERT DATA can be served before the index catches up and return 0 --
    a false FAIL as easily as a false PASS. Every statement carries an
    explicit FROM; Fluree answers HTTP 500 without one.
    """
    return fluree.stable_scalar(
        f"SELECT (COUNT(*) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ {pattern} }}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true",
                    help="write the amendment's assertions to Fluree")
    args = ap.parse_args()

    peak = observed_maximum()
    if peak is None:
        raise RuntimeError("no servicer reports loaded; run Task 8 first.")
    new = Decimal(AMENDMENT["new_threshold"])
    if not (peak < new < peak + MAX_HEADROOM):
        raise RuntimeError(
            f"observed delinquency peak is {peak}%; the engineered threshold "
            f"{AMENDMENT['new_threshold']}% must sit just above it so proximity "
            f"narrows without breaching. Adjust AMENDMENT and say so in the "
            f"design doc -- do not widen this guard.")

    period = peak_period()
    payload = {**AMENDMENT,
               "effective_from": AMENDMENT["effective_from"].isoformat(),
               "asserted_at": AMENDMENT["asserted_at"].isoformat(),
               "prior_threshold": "24.00",
               "observed_peak_percent": str(peak),
               "observed_peak_period": period,
               "headroom_over_peak": str(new - peak),
               "lag_days": (AMENDMENT["asserted_at"] - AMENDMENT["effective_from"]).days}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"  engineered amendment: {TARGET_TRIGGER}  24.00% -> "
          f"{AMENDMENT['new_threshold']}%  effective "
          f"{payload['effective_from']}, asserted {payload['asserted_at']} "
          f"({payload['lag_days']}d lag)")
    print(f"  observed peak {peak}% ({period}); engineered threshold sits "
          f"{new - peak} points above it, inside the {MAX_HEADROOM}-point "
          f"headroom the guard allows")
    print(f"  wrote {OUT}")

    stmts = build_triples()
    lines = [render(st) for st in stmts]
    print(f"\n  {len(lines)} triples to assert:")
    for line in lines:
        print(f"    {line}")

    if not args.load:
        print("\n  Not loaded. Re-run with --load.")
        return 0

    orig = uri(f"abs-trigger-{TARGET_TRIGGER}")
    g_uri = uri(f"abs-trigger-{TARGET_TRIGGER}-amendment")
    d_uri = uri(f"abs-deal-{TARGET_DEAL}")

    before = _count("?s ?p ?o")
    fluree.update("INSERT DATA { " + " ".join(lines) + " }")
    after = _count("?s ?p ?o")

    # Every check recomputes from the ledger. None reads back a flag this
    # script set, and none is phrased so that it cannot fail: the four
    # expectations below are 9-or-0, 1, 0, 0 and 3, and each has a way of
    # coming out otherwise.
    checks = [
        # The supersession edge, in the direction the estate already uses.
        ("supersession edges out of the original",
         _count(f"<{orig}> <{P_SUPERSEDED_BY}> ?s"), 1),
        # ...and NOT the reverse. An append-only store keeps both if both are
        # written, so absence has to be asserted, not assumed.
        ("reverse supersession edges (must be none)",
         _count(f"<{g_uri}> <{P_SUPERSEDED_BY}> ?s"), 0),
        # `ex:supersedes` must not exist anywhere in the ledger -- not just on
        # this node. The binding table names minting it as the failure mode.
        ("ex:supersedes assertions anywhere in the ledger",
         _count(f"?s <{EX}supersedes> ?o"), 0),
        # No anchor, deliberately. Nothing filed says this.
        ("passage anchors on the amendment",
         _count(f"<{g_uri}> <{EX}passageAnchor> ?a"), 0),
        # The deal still specifies THREE triggers. A fourth would assert
        # SDART-2022-6 has two distinct delinquency triggers, which is false,
        # and would make Task 9's loader refuse to re-run.
        ("triggers specified by the deal",
         _count(f"<{d_uri}> <{P_SPECIFIES_TRIGGER}> ?t"), 3),
    ]

    print(f"\n  ledger triples: {before} -> {after} "
          f"(delta {after - before}, asserted {len(lines)})")
    failed = [n for n, got, want in checks if got != want]
    for name, got, want in checks:
        print(f"  {name}: {got} (expected {want}){'' if got == want else '  <-- FAIL'}")

    # Set semantics make a re-run a no-op, so a delta of 0 is legitimate the
    # SECOND time and a failure the first. The supersession check above is
    # what distinguishes "already loaded" from "never written".
    if after - before not in (0, len(lines)):
        print(f"  ledger delta {after - before} is neither {len(lines)} (first "
              f"load) nor 0 (re-run)  <-- FAIL")
        failed.append("ledger delta")

    if failed:
        print(f"\n  FAIL: {len(failed)} check(s) disagree with the intended "
              f"write: {', '.join(failed)}")
        return 1
    print("\n  All checks pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
