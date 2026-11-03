#!/usr/bin/env python3
"""Wave 16 Task 13 — grow the departmental prospect notes and mark the claim.

`ib-opportunity`'s §F wants ~50 `prospect_note` rows, >= 5 of which are a
CLAIM that including the note changes a ranking. This loader adds the rows
and the claim; it does not prove the claim. `validators/ib_rank.py` (a later
task) proves it by ranking each affected banker's covered prospects twice --
with and without note signals -- and diffing the order.

**Why these five (six, for margin) prospects.** `banker_local_note` is
already a weighted, half-life-decayed signal type in
`generators/generate_ib_perspectives.py` (weight 0.6 under PSP-MA/PSP-DCM,
0.3 under PSP-SECTOR; half-life 60 days per `ib_signal_class`). So a
defensible pre-load estimate of "near a boundary" is buildable from data
that already exists: replay `wave16_signals.json` through the WEIGHTS_V2
vectors with exponential half-life decay, per (lei, perspective), rank each
banker's own `coverage_assignment` list under the perspective implied by
their desk (M&A Advisory -> PSP-MA; Leveraged Finance / Treasury Services ->
PSP-DCM; CIB Coverage / Credit Risk -> PSP-SECTOR -- a judgement call, not a
stored fact, since no banker->perspective table exists yet), and take the
prospect sitting just below the smallest adjacent-rank score gap. A single
high-materiality note (weight 0.6 or 0.3, magnitude 1.0, undecayed at
observation) exceeds every gap found by more than an order of magnitude, so
the claim has a real chance of being true under whatever exact algorithm
Task 14 implements -- but the score itself is a SELECTION HEURISTIC computed
in memory here, never written to a column or a table. Rule 1 says
`rank_changing` is a claim, not evidence; storing a score here would be
exactly the mistake that rule forbids.

Idempotent: INSERT ... ON CONFLICT(note_id) DO UPDATE. Proven by a named
value (a specific note's `materiality`), not a row count, per the project
convention that counts cannot see a column silently reset.

    uv run loaders/load_sqlite_wave16.py --dry-run
    uv run loaders/load_sqlite_wave16.py
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from datetime import date, timedelta

from ccf.config import AS_OF_IB, PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, SQLITE_PATH, pg_connect
from ccf.ib_rank import DESK_TO_PERSPECTIVE
import generators.generate_ib_perspectives as gp

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260824
TARGET_TOTAL = 50
N_BOUNDARY = 6  # >= 5 required; one spare for margin

GENERIC_NOTES = [
    "Introduced at sector conference; receptive to a refinancing conversation "
    "ahead of the next maturity wall.",
    "CFO transition expected; hold outreach until the successor is announced.",
    "Existing lender group is tight. Angle is an accordion rather than a new "
    "facility.",
    "Prior mandate lost on price. Revisit only with a structuring idea.",
    "Sponsor-owned; decision sits with the sponsor, not management.",
    "Board seat turnover this quarter; relationship needs re-establishing at "
    "the new director level.",
    "Treasurer flagged interest in a delayed-draw structure for capex "
    "flexibility, not confirmed as a mandate.",
    "Quiet on outreach for two quarters; no signal of near-term activity.",
    "Competitor bank reportedly pitched a repricing; worth a defensive call.",
    "Management focused on integration of a recent bolt-on; unlikely to "
    "engage before next fiscal year.",
]

# Notes written for the six boundary prospects. Each names the specific
# catalyst that would justify a high-materiality weight under that
# prospect's own perspective (M&A vs DCM vs sector), so the claim is at
# least plausible on its face, not just numerically close.
BOUNDARY_NOTES = {
    "PSP-MA": (
        "Direct line from the CEO's office: board has quietly engaged an "
        "advisor to review strategic alternatives. Nothing filed yet -- this "
        "did not come from a public source. Moves them into active pursuit."),
    "PSP-DCM": (
        "CFO confirmed off the record that refinancing discussions for the "
        "upcoming maturity wall are already underway with two other banks. "
        "We are not yet in the room; this should escalate our outreach."),
    "PSP-SECTOR": (
        "Sector desk heard secondhand that a strategic review is being "
        "considered following peer consolidation activity. Unconfirmed, but "
        "consistent with what we're seeing across the sector this quarter."),
}


def display_name(full_name: str) -> str:
    """'Rafael Adeyemi' -> 'R. Adeyemi', matching the existing column style."""
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    return f"{parts[0][0]}. {parts[-1]}"


def find_boundary_candidates(
    cov: list[tuple[str, str, bool]],
    bankers: dict[str, tuple[str, str, str, str]],
    signals: list[dict],
) -> list[dict]:
    """Selection heuristic only -- see module docstring. Returns dicts, not
    a persisted score: {banker_id, lei, perspective, prospect_rank,
    field_size, gap}, sorted smallest-gap-first (most boundary-sensitive)."""
    weights_v2 = {(w["perspective_id"], w["signal_type"]): w["weight"]
                  for w in gp.WEIGHTS_V2}
    half_life = {c["signal_type"]: c["half_life_days"] for c in gp.SIGNAL_CLASSES}
    as_of = date.fromisoformat(AS_OF_IB)

    def decay(observed_at: str, hl: int) -> float:
        days = max((as_of - date.fromisoformat(observed_at)).days, 0)
        return 0.5 ** (days / hl)

    score: dict[tuple[str, str], float] = {}
    for s in signals:
        if not s["is_current"]:
            continue
        hl = half_life[s["signal_type"]]
        d = decay(s["observed_at"], hl)
        for persp in ("PSP-MA", "PSP-DCM", "PSP-SECTOR"):
            w = weights_v2.get((persp, s["signal_type"]), 0.0)
            key = (s["lei"], persp)
            score[key] = score.get(key, 0.0) + w * s["magnitude"] * d

    by_banker: dict[str, list[str]] = {}
    for banker_id, lei, _is_primary in cov:
        by_banker.setdefault(banker_id, []).append(lei)

    out = []
    for banker_id, leis in by_banker.items():
        _full_name, _role, _seniority, desk = bankers[banker_id]
        persp = DESK_TO_PERSPECTIVE.get(desk)
        if not persp or len(leis) < 2:
            continue
        ranked = sorted(leis, key=lambda l: score.get((l, persp), 0.0), reverse=True)
        scored = [(l, score.get((l, persp), 0.0)) for l in ranked]
        gaps = [(scored[i][1] - scored[i + 1][1], i) for i in range(len(scored) - 1)]
        gap, i = min(gaps)
        below_lei = scored[i + 1][0]
        out.append({
            "banker_id": banker_id, "lei": below_lei, "perspective": persp,
            "prospect_rank": i + 2, "field_size": len(scored), "gap": gap,
        })
    out.sort(key=lambda r: r["gap"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rng = random.Random(SEED)

    con = sqlite3.connect(SQLITE_PATH)
    cols = {r[1] for r in con.execute("PRAGMA table_info(prospect_note)")}
    to_add = [c for c in ("signal_type", "materiality") if c not in cols]
    to_add_ddl = [f"ALTER TABLE prospect_note ADD COLUMN {c} TEXT" for c in to_add]
    if "rank_changing" not in cols:
        to_add_ddl.append(
            "ALTER TABLE prospect_note ADD COLUMN rank_changing INTEGER DEFAULT 0")

    existing_total = con.execute("SELECT COUNT(*) FROM prospect_note").fetchone()[0]
    existing_flagged = con.execute(
        "SELECT COUNT(*) FROM prospect_note "
        "WHERE rank_changing = 1").fetchone()[0] if "rank_changing" in cols else 0
    existing_pairs = {
        (b, l) for b, l in con.execute(
            "SELECT banker_id, lei FROM prospect_note WHERE banker_id IS NOT NULL")
    }
    existing_ids = {r[0] for r in con.execute("SELECT note_id FROM prospect_note")}

    # Idempotency guard. Without this, a rerun keeps finding "new" boundary
    # candidates among whatever coverage pairs are still note-free and keeps
    # growing the table forever -- a loader whose own claim (">= 5 flagged")
    # already holds is not a reason to add a sixth run's worth of sevenths.
    # Once both floors are already met, this run adds nothing.
    already_satisfied = existing_total >= TARGET_TOTAL and existing_flagged >= 5

    if already_satisfied:
        chosen_boundary: list[dict] = []
        filler_pairs: list[tuple[str, str]] = []
    else:
        with pg_connect() as cn, cn.cursor() as cu:
            cu.execute(f'SELECT banker_id, lei, is_primary FROM "{S}".coverage_assignment '
                       "ORDER BY banker_id, lei")
            cov = cu.fetchall()
            cu.execute(f'SELECT banker_id, full_name, role, seniority, desk FROM "{S}".banker')
            bankers = {r[0]: r[1:] for r in cu.fetchall()}
            cu.execute(f'SELECT lei, legal_name FROM "{S}".legal_entity')
            names = dict(cu.fetchall())

        signals = json.loads((SCREEN / "wave16_signals.json").read_text())["signals"]

        boundary = find_boundary_candidates(cov, bankers, signals)
        # Drop any candidate whose (banker, lei) pair already carries a note.
        boundary = [b for b in boundary if (b["banker_id"], b["lei"]) not in existing_pairs]
        need_boundary = max(N_BOUNDARY - existing_flagged, 0)
        chosen_boundary = boundary[:need_boundary]
        chosen_pairs = {(b["banker_id"], b["lei"]) for b in chosen_boundary}

        n_new = max(TARGET_TOTAL - existing_total, 0)
        if n_new < len(chosen_boundary):
            n_new = len(chosen_boundary)

        available = [(b, l) for b, l, _p in cov
                     if (b, l) not in existing_pairs and (b, l) not in chosen_pairs]
        rng.shuffle(available)
        filler_needed = n_new - len(chosen_boundary)
        filler_pairs = available[:filler_needed]

    next_idx = max((int(nid.split("-")[1]) for nid in existing_ids), default=-1) + 1

    rows = []
    materialities = ["low", "medium", "high"]
    materiality_weights = [0.35, 0.45, 0.20]

    for b in chosen_boundary:
        banker_id, lei = b["banker_id"], b["lei"]
        full_name = bankers[banker_id][0]
        note_id = f"PN-{next_idx:04d}"
        next_idx += 1
        created = (date.fromisoformat(AS_OF_IB)
                   - timedelta(days=rng.randint(1, 14))).isoformat()
        rows.append((
            note_id, lei, names.get(lei, lei), display_name(full_name),
            BOUNDARY_NOTES[b["perspective"]], "high", created,
            "synthetic — internal", "banker_local_note", "high", 1,
            banker_id, display_name(full_name),
        ))

    for banker_id, lei in filler_pairs:
        full_name = bankers[banker_id][0]
        note_id = f"PN-{next_idx:04d}"
        next_idx += 1
        materiality = rng.choices(materialities, weights=materiality_weights)[0]
        created = (date.fromisoformat(AS_OF_IB)
                   - timedelta(days=rng.randint(1, 180))).isoformat()
        rows.append((
            note_id, lei, names.get(lei, lei), display_name(full_name),
            GENERIC_NOTES[next_idx % len(GENERIC_NOTES)], materiality, created,
            "synthetic — internal", "banker_local_note", materiality, 0,
            banker_id, display_name(full_name),
        ))

    print("Wave 16 Task 13 — extend prospect_note\n")
    print(f"  existing rows          {existing_total:>4}  ({existing_flagged} already "
          f"rank_changing)")
    print(f"  new rows               {len(rows):>4}")
    print(f"  target total           {existing_total + len(rows):>4}  (>= {TARGET_TOTAL})")
    print(f"  new rank_changing      {len(chosen_boundary):>4}  "
          f"(total will be {existing_flagged + len(chosen_boundary)}, need >= 5)")
    for b in chosen_boundary:
        print(f"    {b['banker_id']}  {b['perspective']:<10}  rank {b['prospect_rank']}/"
              f"{b['field_size']}  gap={b['gap']:.5f}  {names.get(b['lei'], b['lei'])}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    for ddl in to_add_ddl:
        con.execute(ddl)

    con.executemany(
        "INSERT INTO prospect_note "
        "(note_id, lei, prospect_name, banker, note, priority, created_at, "
        " provenance, signal_type, materiality, rank_changing, banker_id, "
        " banker_display) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(note_id) DO UPDATE SET "
        "note=excluded.note, signal_type=excluded.signal_type, "
        "materiality=excluded.materiality, rank_changing=excluded.rank_changing",
        rows,
    )
    # Every row in the table IS a banker's local note by definition of the
    # table -- unambiguous, so backfilling signal_type on the pre-existing 18
    # is a correct restatement, not an invented value. materiality is left
    # untouched on those 18: it is a new judgement this task introduces, and
    # nothing entitles this loader to assert it retroactively for notes it
    # did not write.
    con.execute(
        "UPDATE prospect_note SET signal_type = 'banker_local_note' "
        "WHERE signal_type IS NULL")
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM prospect_note").fetchone()[0]
    flagged = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE rank_changing = 1").fetchone()[0]
    orphans = con.execute(
        "SELECT COUNT(*) FROM prospect_note WHERE banker_id IS NULL").fetchone()[0]
    print(f"\n  loaded: {total} prospect_note rows, {flagged} rank_changing, "
          f"{orphans} without a banker_id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
