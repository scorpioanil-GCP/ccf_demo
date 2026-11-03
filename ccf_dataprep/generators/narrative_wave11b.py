#!/usr/bin/env python3
"""Wave 11b Task 8 — the two engineered conditions §F cannot supply.

§F names two conditions the public sources fetched in Tasks 2-6 structurally
cannot produce, because no public source in this catalog files "one event
that invalidates three downstream products at once" or "three unremarkable
signals that happen to cross an internal escalation line together." Both are
manufactured here, deliberately, and labelled `synthetic — engineered` per
CLAUDE.md rule 1 -- never `public`, never `synthetic — internal`.

1. THE SCRIPTED CASCADE (design §3.1). An Item 2.04 acceleration asserted
   against the one obligor whose covenant-carrying facility ALSO carries a
   collateral pledge and a drawdown, so a single event's `signalAbout` edges
   demonstrably reach the covenant product (via the facility), collateral
   coverage (via the pledge) and the exposure rollup (via the drawdown).
   `CASCADE_LEI` is RESOLVED BY QUERY -- never hardcoded by name -- against
   `facility` JOIN `covenant_breach` JOIN `collateral_pledge` JOIN
   `drawdown`, with an assertion that the design's named anchor (Avis
   Budget Group) is among the matches. That query runs LAZILY, on first use
   (`resolve_cascade_lei()`, memoized), not at import time -- fix round 1:
   a module-level query at import meant `is_subthreshold`, a pure predicate
   Task 12 must import rather than reimplement, could not be reached without
   a live Postgres connection. The design doc's own real Item 2.04 filings
   (Tupperware, Murphy Oil, Container Store, §3.2) stay untouched and
   entirely `public` -- this module never touches that population.

2. THE COMPOSITE CASE (design §3.3). Three signals of three distinct types,
   each individually below the `daily-sweep` escalation threshold, whose
   combined weighted score clears it. Placed on an obligor OTHER than
   `CASCADE_LEI` so the two conditions are independently demonstrable --
   one obligor carrying both would let a defect in one mask a defect in the
   other. `is_subthreshold` is the shared predicate both this generator and
   Task 12's `validators/surveillance.py` call: `validators/conditions.py:32`
   already records one prior instance of a validator sharing a loader's wrong
   constants and agreeing with itself while both were wrong. Importing one
   function, rather than each side reimplementing the comparison, is how
   that specific failure is prevented here -- the same reason
   `generators/narrative_wave11a.py` exists.

Nothing here is fetched -- this module only reads the already-committed
Postgres tables (`facility`, `collateral_pledge`, `drawdown`,
`covenant_breach`, `legal_entity`) and the already-written
`sources/screening/wave11b_signals.json` (Task 7's unified ledger, plus the
`weights` and `thresholds` policy tables originated there), and derives
selection and arithmetic over them.

    uv run generators/narrative_wave11b.py --dry-run
    uv run generators/narrative_wave11b.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.currency import record_inputs, verify_current
from generators.generate_signals import ITEM_SEVERITY

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

# --- 1. The scripted cascade -------------------------------------------------
# Placed after the estate's last real drawdown for this facility (2026-08-08)
# and well inside the 24-month surveillance window (WINDOW_END 2026-08-19),
# so the engineered event reads as the most recent thing on file rather than
# colliding with, or predating, real activity on the same facility.
CASCADE_EVENT_DATE = "2026-08-12"

# Visibly synthetic: EDGAR accessions are CIK(10)-YY-SEQUENCE(6) and no real
# filer carries CIK 0000000000. Same discipline CLAUDE.md requires of
# synthetic identifiers generally -- distinct format, never confusable with
# a real one.
CASCADE_ACCESSION = "0000000000-26-000001"


def _resolve_cascade_facility(conn) -> tuple[dict, list[dict]]:
    """The facility satisfying facility AND collateral_pledge AND drawdown
    AND covenant_breach, ALL on the SAME facility_id -- the intersection
    §F's cascade requires, resolved by query rather than assumed.

    Candidacy is scoped to one facility, not "this obligor holds all four
    tables somewhere": a covenant breach on facility A and a drawdown on
    facility B for the same obligor would not let one Item 2.04 touch both,
    because a real 8-K names a specific triggering fact, not the obligor at
    large.

    Returns (winner, all_candidates). Raises if no candidate exists at all,
    or if the design's named anchor (Avis Budget Group) is not among
    whatever candidates DO exist -- per the brief: "If Avis is not among the
    matches, STOP and report — something upstream changed."
    """
    with conn.cursor() as cur:
        cur.execute(f'''
            SELECT cb.facility_id, f.borrower_lei, le.legal_name,
                   (SELECT count(*) FROM "{S}".collateral_pledge cp
                     WHERE cp.facility_id = cb.facility_id) AS n_pledge,
                   (SELECT count(*) FROM "{S}".drawdown d
                     WHERE d.facility_id = cb.facility_id) AS n_drawdown
            FROM "{S}".covenant_breach cb
            JOIN "{S}".facility f USING (facility_id)
            JOIN "{S}".legal_entity le ON le.lei = f.borrower_lei
            ORDER BY cb.facility_id
        ''')
        rows = cur.fetchall()

    candidates = [
        {"facility_id": r[0], "lei": r[1], "legal_name": r[2],
         "n_pledge": r[3], "n_drawdown": r[4]}
        for r in rows if r[3] > 0 and r[4] > 0
    ]
    if not candidates:
        raise AssertionError(
            "no facility satisfies covenant_breach AND collateral_pledge "
            "AND drawdown simultaneously -- the scripted cascade has no "
            "anchor to sit on; something upstream changed")
    if not any("AVIS" in c["legal_name"].upper() for c in candidates):
        raise AssertionError(
            "Avis Budget Group is not among the cascade candidates "
            f"({sorted(c['legal_name'] for c in candidates)}) -- STOP and "
            "report; the design's named anchor (docs/wave11b-design.md "
            "§1.5 / §3.1) is no longer reachable by this query")

    # Deterministic tie-break, stated once here rather than left implicit:
    # most drawdowns on the covenant-carrying facility -- the richest
    # exposure-rollup demonstration surface -- then facility_id ascending.
    # Measured 2026-08-21: two candidates exist (Avis Budget Group,
    # facility_id FAC-044206, 5 drawdowns; Regis Corp, FAC-01BB3F, 3
    # drawdowns). This rule selects Avis, matching the design's named
    # anchor, but the selection is made BY the rule, not by matching the
    # name -- the AVIS assertion above is a sanity check on the rule's
    # output, not the rule itself.
    candidates.sort(key=lambda c: (-c["n_drawdown"], c["facility_id"]))
    return candidates[0], candidates


# LAZY, MEMOIZED. Fix round 1: a module-level `with pg_connect() as _conn:`
# here meant `import generators.narrative_wave11b` alone required a live
# Postgres connection, before any pure function -- including
# `is_subthreshold`, which Task 12's surveillance.py must IMPORT rather than
# reimplement (see module docstring) -- could even be reached. An offline
# unit test, a lint pass, or CI without a DB would fail to import this
# module at all, which creates quiet pressure to copy the four-line
# predicate instead of importing it -- exactly the drift this sharing exists
# to prevent. So resolution happens on first USE, not on import, and is
# cached so repeated calls do not re-query.
_CASCADE_RESOLUTION: dict | None = None


def _get_cascade_resolution() -> dict:
    """{"facility": ..., "candidates": ...} -- queried once, memoized."""
    global _CASCADE_RESOLUTION
    if _CASCADE_RESOLUTION is None:
        with pg_connect() as conn:
            facility, candidates = _resolve_cascade_facility(conn)
        _CASCADE_RESOLUTION = {"facility": facility, "candidates": candidates}
    return _CASCADE_RESOLUTION


def resolve_cascade_lei() -> str:
    """Avis Budget's LEI -- resolved by query, lazily and memoized. Never
    hardcoded by name. See `_resolve_cascade_facility`'s docstring for the
    selection rule and the AVIS sanity assertion. This is the function form
    of what `CASCADE_LEI` used to be a module-level constant computed at
    import time; call this (or access `CASCADE_LEI` via the module, which
    routes here through `__getattr__` below) rather than re-querying."""
    return _get_cascade_resolution()["facility"]["lei"]


def __getattr__(name: str):
    """PEP 562 module `__getattr__`. Keeps `narrative_wave11b.CASCADE_LEI`
    (and `from generators.narrative_wave11b import CASCADE_LEI`) working as
    a plain name for callers that prefer the constant spelling -- the Task 8
    brief's interface lists it as a produced symbol -- while resolving
    lazily on first ACCESS of that name rather than at import time. Plain
    `import generators.narrative_wave11b`, or importing any other name from
    it (`is_subthreshold`, `composite_case`, `cascade_event` itself before
    it is called), never touches Postgres."""
    if name == "CASCADE_LEI":
        return resolve_cascade_lei()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def cascade_event() -> dict:
    """The engineered Item 2.04 and its `signalAbout` targets.

    One event; `signal_about` carries the facility, every collateral pledge
    on it, and every drawdown on it -- so Task 10's Fluree loader can assert
    edges reaching all three downstream products (the covenant product via
    the facility, collateral coverage via the pledges, the exposure rollup
    via the drawdowns) from this one signal, and Task 12's
    `validators/surveillance.py` can walk those edges and confirm it.
    """
    resolution = _get_cascade_resolution()
    facility = resolution["facility"]
    lei = facility["lei"]
    facility_id = facility["facility_id"]
    with pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT asset_id FROM "{S}".collateral_pledge '
                f'WHERE facility_id = %s ORDER BY asset_id', (facility_id,))
            pledge_ids = [r[0] for r in cur.fetchall()]
            cur.execute(
                f'SELECT drawdown_id FROM "{S}".drawdown '
                f'WHERE facility_id = %s ORDER BY drawdown_id', (facility_id,))
            drawdown_ids = [r[0] for r in cur.fetchall()]

    signal_about = (
        [{"target_type": "Facility", "target_id": facility_id}]
        + [{"target_type": "CollateralPledge", "target_id": pid}
           for pid in pledge_ids]
        + [{"target_type": "Drawdown", "target_id": did}
           for did in drawdown_ids]
    )

    return {
        "signal_id": f"sig-8k-engineered-{lei}-2.04",
        "lei": lei,
        "legal_name": facility["legal_name"],
        "signal_type": "8k_event",
        "item": "2.04",
        "observed_at": CASCADE_EVENT_DATE,
        # Reuses the same 8-K item severity scale generate_signals.py
        # applies to every REAL 8-K event, rather than inventing a second
        # number for the one engineered filing -- an acceleration event is
        # the ceiling of that scale (1.00) regardless of provenance.
        "severity": ITEM_SEVERITY["2.04"],
        "source_ref": {
            "accession": CASCADE_ACCESSION,
            "item": "2.04",
            "primary_document": None,
            "facility_id": facility_id,
            "engineered": True,
            "note": (
                "manufactured acceleration/triggering-event filing -- design "
                "§3.1 (\"the scripted cascade\"), §F lists this element as "
                "engineered rather than fetched. The real, public Item 2.04 "
                "population (Tupperware, Murphy Oil, Container Store, design "
                "§3.2) is untouched by this module."),
        },
        "provenance": "synthetic — engineered",
        "signal_about": signal_about,
        "resolution": {
            "candidates": resolution["candidates"],
            "selected_facility_id": facility_id,
            "selected_lei": lei,
            "selection_rule": (
                "facility carrying a covenant_breach row AND >=1 "
                "collateral_pledge AND >=1 drawdown, all on that same "
                "facility_id; ties broken by most drawdowns (richest "
                "exposure-rollup demonstration), then facility_id ascending"),
        },
    }


# --- 2. The composite case ---------------------------------------------------
# Deliberately moderate, not near-ceiling: each signal reads as an ordinary,
# individually-unmemorable observation (design §A's "look unremarkable
# alone"). At this severity every one of the three sits at roughly HALF the
# daily-sweep threshold once weighted, and the three together clear it with
# ~26% margin (measured against the actually-loaded weights/threshold below,
# not assumed) -- comfortable, not razor-edge, and still visibly "ordinary"
# rather than "obviously alarming on its own."
COMPOSITE_SEVERITY = 0.60
COMPOSITE_SIGNAL_TYPES = ("adverse_media", "warn_notice", "spread_widening")
COMPOSITE_OBSERVED_AT = {
    "adverse_media": "2026-07-01",
    "warn_notice": "2026-07-03",
    "spread_widening": "2026-07-05",
}


def _load_signals_artifact() -> dict:
    """Read Task 7's ledger, refusing a STALE one.

    `verify_current` re-hashes the four artifacts `generate_signals.py`
    recorded as its own inputs and raises naming the required order if any
    has changed on disk since — design §5's "current, not merely present".
    """
    doc, _ = verify_current(
        "wave11b_signals.json",
        required_order="fetchers -> generate_trend_deltas.py -> "
                       "generate_signals.py -> narrative_wave11b.py")
    return doc


def _daily_sweep_threshold(thresholds) -> float:
    for t in thresholds:
        if t.get("kind") == "escalation" and t.get("intent") == "daily-sweep":
            return float(t["threshold_score"])
    raise ValueError(
        "no escalation threshold row with intent='daily-sweep' found in "
        "the thresholds passed to _daily_sweep_threshold")


def is_subthreshold(signal: dict, thresholds) -> bool:
    """True iff `signal`'s weighted_score sits AT OR BELOW the daily-sweep
    escalation threshold.

    `thresholds` is polymorphic on purpose, to serve both call sites without
    either reimplementing the comparison:
      - a plain number: used directly (this is what `composite_case()`'s own
        `case["threshold"]` is, and what the Task 8 test passes).
      - an iterable of policy-row dicts (`kind`, `intent`,
        `threshold_score`), the shape both `wave11b_signals.json["thresholds"]`
        and the loaded Postgres `escalation_threshold` table carry: the
        `daily-sweep` row's `threshold_score` is resolved from it.

    Imported by `validators/surveillance.py` (Task 12) rather than
    reimplemented there -- see the module docstring for why that sharing is
    load-bearing, not a style choice.
    """
    value = (thresholds if isinstance(thresholds, (int, float))
             else _daily_sweep_threshold(thresholds))
    return signal["weighted_score"] <= value


def _sector_for_composite_lei(conn, lei: str) -> str:
    from loaders.load_postgres_wave11a import sector_for
    with conn.cursor() as cur:
        cur.execute(f'SELECT sic FROM "{S}".legal_entity WHERE lei = %s', (lei,))
        row = cur.fetchone()
    if row is None:
        raise AssertionError(f"composite candidate {lei!r} not in legal_entity")
    return sector_for(row[0])


def _composite_candidates(signals: list[dict], cascade_lei: str) -> list[str]:
    """Obligors, OTHER than `cascade_lei`, whose real signal_event rows
    already cover all three of adverse_media, warn_notice and
    spread_widening -- the population `composite_case` is scaled from.
    Sorted for a deterministic pick if more than one exists.

    Takes `cascade_lei` as a parameter rather than reading the module-level
    `CASCADE_LEI` name directly: since that name now resolves lazily via
    `__getattr__` (fix round 1), a bare in-module reference to it would
    raise NameError rather than route through the lazy accessor -- only
    external `module.CASCADE_LEI` / `from module import CASCADE_LEI` access
    goes through `__getattr__`. The caller (`composite_case`) resolves it
    once via `resolve_cascade_lei()` and passes it in."""
    by_lei: dict[str, set[str]] = defaultdict(set)
    for s in signals:
        by_lei[s["lei"]].add(s["signal_type"])
    need = set(COMPOSITE_SIGNAL_TYPES)
    return sorted(
        lei for lei, types in by_lei.items()
        if need <= types and lei != cascade_lei)


def composite_case() -> dict:
    """Three individually-subthreshold signals, of three distinct types, on
    one obligor other than CASCADE_LEI, whose combined weighted score
    breaches the daily-sweep escalation threshold.

    The obligor is selected from the REAL ledger (an obligor that already,
    organically, carries all three signal types) so the case sits on a
    plausible candidate rather than an arbitrary one; the three signals
    THEMSELVES are manufactured at `COMPOSITE_SEVERITY` -- design §3.3
    requires the individually-subthreshold-yet-jointly-over condition to
    hold exactly, which the real loaded severities were never built to
    guarantee, and design §2.1's store-partition table lists "Composite
    case signal set" as `synthetic — engineered` for exactly this reason.
    """
    cascade_lei = resolve_cascade_lei()
    artifact = _load_signals_artifact()
    candidates = _composite_candidates(artifact["signals"], cascade_lei)
    if not candidates:
        raise AssertionError(
            "no obligor other than the cascade anchor carries all three "
            "composite signal types (adverse_media, warn_notice, "
            "spread_widening) in the loaded signal ledger -- upstream data "
            "changed")
    composite_lei = candidates[0]

    with pg_connect() as conn:
        sector = _sector_for_composite_lei(conn, composite_lei)
        with conn.cursor() as cur:
            cur.execute(
                f'SELECT legal_name FROM "{S}".legal_entity WHERE lei = %s',
                (composite_lei,))
            legal_name = cur.fetchone()[0]

    weight_by_type = {
        w["signal_type"]: w["weight"]
        for w in artifact["weights"] if w["sector"] == sector
    }
    missing = set(COMPOSITE_SIGNAL_TYPES) - set(weight_by_type)
    if missing:
        raise AssertionError(
            f"sector {sector!r} is missing weights for {sorted(missing)} -- "
            "cannot score the composite case")
    threshold = _daily_sweep_threshold(artifact["thresholds"])

    signals = []
    for st in COMPOSITE_SIGNAL_TYPES:
        weight = weight_by_type[st]
        weighted_score = round(COMPOSITE_SEVERITY * weight, 4)
        signals.append({
            "signal_id": f"sig-composite-{composite_lei}-{st}",
            "lei": composite_lei,
            "signal_type": st,
            "observed_at": COMPOSITE_OBSERVED_AT[st],
            "severity": COMPOSITE_SEVERITY,
            "sector": sector,
            "weight": weight,
            "weighted_score": weighted_score,
            "source_ref": {
                "engineered": True,
                "component": st,
                "basis": (
                    f"design §3.3 composite case: severity fixed at "
                    f"{COMPOSITE_SEVERITY} (moderate, not near-ceiling) "
                    f"times the loaded {sector!r} sector weight for {st!r} "
                    f"({weight})"),
            },
            "provenance": "synthetic — engineered",
        })

    combined_score = round(sum(s["weighted_score"] for s in signals), 4)
    return {
        "lei": composite_lei,
        "legal_name": legal_name,
        "excluded_lei": cascade_lei,
        "sector": sector,
        # MINOR fix round 1: block-level provenance, matching the cascade
        # block's top-level "provenance" key. Each signals[i] already carried
        # its own -- this is a schema-symmetry fix, not a new fact; no
        # emitted value changes as a result.
        "provenance": "synthetic — engineered",
        "signals": signals,
        "threshold": threshold,
        "combined_score": combined_score,
        "candidates_considered": candidates,
        "rationale": (
            f"{legal_name} ({composite_lei}) is the obligor, other than the "
            "cascade anchor, whose real signal_event rows already cover all "
            "three of adverse_media, warn_notice and spread_widening "
            f"(candidates: {candidates}). Each of the three manufactured "
            f"signals sits at severity {COMPOSITE_SEVERITY} -- individually "
            f"{[round(s['weighted_score'], 4) for s in signals]}, all <= "
            f"threshold {threshold} -- and their sum {combined_score} clears "
            f"it by {round(combined_score - threshold, 4)}."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cascade = cascade_event()
    composite = composite_case()

    print("Wave 11b Task 8 — engineered cascade and composite case\n")

    cand_summary = [(c["legal_name"], c["facility_id"], c["n_pledge"],
                     c["n_drawdown"])
                    for c in cascade["resolution"]["candidates"]]
    print("  CASCADE")
    print(f"    candidates: {cand_summary}")
    print(f"    resolved anchor: {cascade['legal_name']} ({cascade['lei']})")
    print(f"    facility: {cascade['resolution']['selected_facility_id']}")
    n_pledge = sum(1 for t in cascade["signal_about"]
                   if t["target_type"] == "CollateralPledge")
    n_draw = sum(1 for t in cascade["signal_about"]
                 if t["target_type"] == "Drawdown")
    print(f"    signalAbout targets: 1 facility, {n_pledge} pledge(s), "
          f"{n_draw} drawdown(s)")
    print(f"    event date: {cascade['observed_at']}  "
          f"accession: {cascade['source_ref']['accession']}")

    print("\n  COMPOSITE CASE")
    print(f"    candidates considered: {composite['candidates_considered']}")
    print(f"    obligor: {composite['legal_name']} ({composite['lei']}), "
          f"sector {composite['sector']}")
    print(f"    excluded (cascade anchor): {composite['excluded_lei']}")
    for s in composite["signals"]:
        print(f"      {s['signal_type']:16} severity={s['severity']} "
              f"weight={s['weight']} weighted_score={s['weighted_score']}")
    print(f"    threshold (daily-sweep): {composite['threshold']}")
    print(f"    combined score: {composite['combined_score']}  "
          f"(each individually subthreshold: "
          f"{all(is_subthreshold(s, composite['threshold']) for s in composite['signals'])})")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11b_narrative.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": (
            "manufactured by generators/narrative_wave11b.py -- design §3.1 "
            "(scripted cascade) and §3.3 (composite case). Both elements are "
            "synthetic — engineered per CLAUDE.md rule 1; never public, "
            "never synthetic — internal."),
        "_inputs": record_inputs("wave11b_signals.json"),
        "cascade": cascade,
        "composite": composite,
    }, indent=2, default=str))
    print("\n  wrote sources/screening/wave11b_narrative.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
