#!/usr/bin/env python3
"""Wave 16 Task 14 — the four §F floors for `ib-opportunity-synthesis`.

## What this is not

This is a **build-time validator, not an operator**. See CLAUDE.md, "What
'operator' means -- and what it does not". An Operator is a runtime SDK
entity: registered, composed into a plan, executed in the Data Plane, serving
a principal at request time. This script registers nothing, composes into no
plan, serves no principal, emits no contract. It runs against the loaded
stores and asks whether the data supports what the spec claims.

## What it proves, and how

Four conditions, each recomputed from the stores on every run -- never a
stored score, a cached rank, or a boolean flag. In particular
`prospect_note.rank_changing` is a CLAIM made by loaders/load_sqlite_wave16.py
and is never read here; note materiality is recomputed independently.

1. DIVERGENCE       -- one signal set, two perspectives, opposite orderings.
2. CONTAINMENT       -- >= 2 restricted LEIs never appear in a walled
                        banker's candidate set, and the set carries no
                        marker (at any nesting depth) naming what was
                        suppressed.
3. NOTE MATERIALITY  -- >= 5 banker-local NOTES change their OWN entity's
                        rank position when included.
4. WEIGHT REPLAY     -- the same candidate set, same as_of, reorders under a
                        different weight_version -- and both vectors are
                        confirmed non-empty and distinct before ranking.

    uv run validators/ib_rank.py

Exit code is non-zero if any of the four fails.
"""
from __future__ import annotations

import json
import sqlite3
import sys

from ccf.config import (
    AS_OF_IB,
    PG_SCHEMA_V2 as S,
    REPO_ROOT,
    SQLITE_PATH,
    pg_connect,
)
from ccf.ib_rank import DESK_TO_PERSPECTIVE, rank, score

SCREEN = REPO_ROOT / "sources" / "screening"

#: §F names the named entities' assignment to bankers by desk; the same
#: mapping the loader (loaders/load_sqlite_wave16.py) uses to pick boundary
#: candidates. It is a judgement call, not a stored fact -- there is no
#: banker -> perspective table -- so `DESK_TO_PERSPECTIVE` lives in
#: `ccf/ib_rank.py` once, imported here and by the loader, not duplicated.

DIVERGENT_PROSPECT = "Braemar Hotels & Resorts Inc."
MIRROR_PROSPECT = "Thermon Group Holdings, Inc."


# --- pure ranking helpers (importable, unit-tested against fixtures) -------

def rank_positions(scores: dict[str, float]) -> dict[str, int]:
    """LEI -> 1-indexed rank position, deterministic under ties."""
    return {lei: i + 1 for i, (lei, _) in enumerate(rank(scores))}


def divergence_holds(*, signals, ma_weights, dcm_weights, half_lives,
                      as_of: str) -> bool:
    """True iff at least one LEI ranks top-3 under `ma_weights` and outside
    the top-20 under `dcm_weights`, from the SAME signal set.

    Must be able to say both things: identical weight vectors can never
    produce this (see validators/test_ib_rank.py,
    test_divergence_check_can_actually_fail), and a genuinely divergent
    signal/weight combination must (test_divergence_check_passes_on_a_known_divergent_set).
    """
    ma_rank = rank_positions(score(signals=signals, weights=ma_weights,
                                    half_lives=half_lives, as_of=as_of))
    dcm_rank = rank_positions(score(signals=signals, weights=dcm_weights,
                                     half_lives=half_lives, as_of=as_of))
    shared = set(ma_rank) & set(dcm_rank)
    return any(ma_rank[lei] <= 3 and dcm_rank[lei] > 20 for lei in shared)


def build_candidate_set(coverage_leis: list[str],
                         restricted_leis: set[str]) -> dict:
    """A banker's candidate set with restricted entities silently absent.

    Returns ONLY `{"candidates": [...]}` -- no count of what was removed, no
    flag, no name. A suppressed row with a marker tells the banker exactly
    what the wall exists to hide, so the absence of the marker is itself
    part of the condition (see `containment_holds` below).
    """
    return {"candidates": [lei for lei in coverage_leis
                            if lei not in restricted_leis]}


def _nested_marker_keys(cand: dict) -> list[str]:
    """Every dict key found ANYWHERE in the structure other than the single
    expected top-level 'candidates' key.

    A top-level-only scan (`set(cand) - {"candidates"}`) misses a marker
    tucked inside a candidate entry -- e.g. `{"candidates": ["OK1",
    {"suppressed_because": "RESTRICTED-1"}]}` has exactly one top-level key
    and would pass a flat check while still naming what was suppressed. This
    walks dicts and lists/tuples at any depth.
    """
    found: list[str] = []

    def walk(node, at_top: bool) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if not (at_top and k == "candidates"):
                    found.append(k)
                walk(v, False)
        elif isinstance(node, (list, tuple, set)):
            for item in node:
                walk(item, False)

    walk(cand, True)
    return found


def containment_holds(coverage: list[tuple[str, str]],
                       restricted_leis: set[str],
                       build_fn=build_candidate_set,
                       ) -> tuple[int, set[str], list[tuple[str, str, object]]]:
    """For every banker whose RAW coverage includes an active restricted
    LEI, the candidate set must omit it and carry no marker, at any nesting
    depth (see `_nested_marker_keys`).

    `build_fn` is injectable so the checker itself can be proven sensitive:
    a builder that forgets to filter, or one that filters but leaves a
    marker naming the suppressed LEI (top-level or nested), must both be
    caught (see validators/test_ib_rank.py).

    Returns (affected_banker_count, exercised_restricted_leis, violations).
    `exercised_restricted_leis` is the set of restricted LEIs that were
    actually present in some banker's raw coverage AND confirmed absent
    from that banker's built candidate set -- the unit §F's floor names
    ("prospects ... absent from the affected principals' candidate sets"),
    distinct from `affected_banker_count`. Empty violations with
    `exercised_restricted_leis` non-empty is the passing shape;
    affected_banker_count == 0 means no fixture/data exists that could even
    test the wall, which is a SKIP, not a PASS.
    """
    by_banker: dict[str, list[str]] = {}
    for banker_id, lei in coverage:
        by_banker.setdefault(banker_id, []).append(lei)

    violations: list[tuple[str, str, object]] = []
    affected = 0
    exercised: set[str] = set()
    for banker_id, leis in sorted(by_banker.items()):
        hit = set(leis) & restricted_leis
        if not hit:
            continue
        affected += 1
        cand = build_fn(leis, restricted_leis)
        extra_keys = _nested_marker_keys(cand)
        if extra_keys:
            violations.append((banker_id, "marker key(s) present", extra_keys))
        # Only string entries can BE a leaked LEI; a non-string entry (e.g.
        # a dict smuggled into the candidates list) is caught by the marker
        # walk above instead, and must not blow up a hashability check here.
        cand_leis = {c for c in cand.get("candidates", []) if isinstance(c, str)}
        leaked = cand_leis & restricted_leis
        if leaked:
            violations.append((banker_id, "restricted LEI leaked", leaked))
        exercised |= (hit - leaked)
    return affected, exercised, violations


def rank_changed_positions(candidate_leis: list[str], base_signals: list[dict],
                            note_signals: list[dict], weights: dict[str, float],
                            half_lives: dict[str, int], as_of: str) -> set[str]:
    """LEIs in `candidate_leis` whose rank POSITION differs between a
    without-notes ranking and a with-notes ranking, over the same field.

    Every candidate LEI is forced into both score dicts (even at 0.0) so a
    LEI absent from `base_signals` entirely still participates in the rank
    comparison -- otherwise a LEI that has no public signal at all but does
    get a note would silently be excluded from "position changed" instead
    of moving from unranked-last to ranked-somewhere.
    """
    scoped = [s for s in base_signals if s["lei"] in candidate_leis]
    scoped_notes = [s for s in note_signals if s["lei"] in candidate_leis]

    without = score(signals=scoped, weights=weights, half_lives=half_lives,
                     as_of=as_of)
    with_notes = score(signals=scoped + scoped_notes, weights=weights,
                        half_lives=half_lives, as_of=as_of)
    for lei in candidate_leis:
        without.setdefault(lei, 0.0)
        with_notes.setdefault(lei, 0.0)

    rank_without = rank_positions(without)
    rank_with = rank_positions(with_notes)
    return {lei for lei in candidate_leis if rank_without[lei] != rank_with[lei]}


def note_materiality_counts(
    notes: list[tuple[str, str, str, str]],
    coverage: list[tuple[str, str]],
    desks: dict[str, str],
    weight_vectors: dict[str, dict[str, float]],
    base_signals: list[dict], half_lives: dict[str, int], as_of: str,
) -> tuple[list[str], list[tuple[str, str]]]:
    """The §F unit is NOTES, not (banker, LEI) position changes.

    `notes` is (note_id, banker_id, lei, created_at). Each affected banker's
    coverage is ranked twice -- with and without that banker's note signals
    -- and a note counts iff its OWN lei's rank position differs between the
    two. A note-free entity that gets displaced by someone else's note is a
    collateral position change, not a note "changing a ranking", and a
    single note that vaults its entity past several others must count as
    ONE note, not one per entity it passed -- see
    validators/test_ib_rank.py, test_note_materiality_counts_credits_one_note_once.

    Returns (note_ids_moving_own_entity, all_changed_(banker,lei)_pairs) --
    the second is informative only; the first is the §F floor.
    """
    by_banker_notes: dict[str, list[tuple[str, str, str]]] = {}
    for note_id, banker_id, lei, created_at in notes:
        by_banker_notes.setdefault(banker_id, []).append((note_id, lei, created_at))

    by_banker_coverage: dict[str, list[str]] = {}
    for banker_id, lei in coverage:
        by_banker_coverage.setdefault(banker_id, []).append(lei)

    changed_pairs: list[tuple[str, str]] = []
    notes_moving_own_entity: list[str] = []
    for banker_id, note_rows in sorted(by_banker_notes.items()):
        perspective = DESK_TO_PERSPECTIVE.get(desks.get(banker_id))
        candidate_leis = by_banker_coverage.get(banker_id, [])
        if not perspective or perspective not in weight_vectors or len(candidate_leis) < 2:
            continue
        weights = weight_vectors[perspective]
        note_signals = [
            {"lei": lei, "signal_type": "banker_local_note",
             "observed_at": created_at, "magnitude": 1.0}
            for _note_id, lei, created_at in note_rows]
        changed = rank_changed_positions(candidate_leis, base_signals, note_signals,
                                          weights, half_lives, as_of)
        for lei in changed:
            changed_pairs.append((banker_id, lei))
        for note_id, lei, _created_at in note_rows:
            if lei in changed:
                notes_moving_own_entity.append(note_id)
    return notes_moving_own_entity, changed_pairs


def weight_replay_differs(candidate_leis: list[str], signals: list[dict],
                           weights_v1: dict[str, float],
                           weights_v2: dict[str, float],
                           half_lives: dict[str, int], as_of: str) -> bool:
    """True iff the SAME candidate set, at the SAME as_of, orders differently
    under weight_version v1 vs v2. Holding as_of fixed is the whole point --
    move both the weights and the clock and a reorder can no longer be
    attributed to the weights."""
    scoped = [s for s in signals if s["lei"] in candidate_leis]
    order_v1 = [lei for lei, _ in rank(score(signals=scoped, weights=weights_v1,
                                              half_lives=half_lives, as_of=as_of))]
    order_v2 = [lei for lei, _ in rank(score(signals=scoped, weights=weights_v2,
                                              half_lives=half_lives, as_of=as_of))]
    return order_v1 != order_v2


def require_nonempty_weights(vectors: dict[str, dict[str, float]]) -> None:
    """Refuse to rank against a weight vector that loaded to nothing.

    FIX ROUND 1, finding 1: `load_weights()` returns `{}` on a
    version-string or schema drift -- not an exception. `score()` then
    yields 0.0 for every LEI it sees, and `rank()` falls back to
    alphabetical (LEI-ascending) order. That alphabetical order differs from
    a real one, so a missing vector can make "orders differ" (condition 4)
    or even "ranks top-3" (condition 1) come out True from ABSENCE rather
    than from signal -- exactly the trap this wave has spent all day
    fighting, in the one place built to catch it. So: fail loudly, by name
    and row count, before any ranking happens.
    """
    empty = [f"{name} ({len(vec)} rows)" for name, vec in vectors.items() if not vec]
    if empty:
        raise RuntimeError(
            "refusing to rank: empty weight vector(s) loaded -- " + "; ".join(empty))


def require_versions_differ(name_a: str, vec_a: dict[str, float],
                             name_b: str, vec_b: dict[str, float]) -> None:
    """A weight-replay pair that loaded IDENTICAL (e.g. both resolved to the
    same version by a query bug) would still make `weight_replay_differs`
    return False honestly -- but the honest False would be masking a load
    bug, not reporting "no divergence". Fail loudly instead of reporting a
    condition FAIL that looks like a data finding."""
    if vec_a == vec_b:
        raise RuntimeError(
            f"refusing to replay: {name_a} and {name_b} loaded identical -- "
            "a reorder could never be attributed to the weights")


# --- store reads -------------------------------------------------------

def load_current_signals() -> list[dict]:
    data = json.loads((SCREEN / "wave16_signals.json").read_text())
    return [
        {"lei": s["lei"], "signal_type": s["signal_type"],
         "observed_at": s["observed_at"], "magnitude": s["magnitude"]}
        for s in data["signals"] if s.get("is_current")
    ]


def signal_artifact_counts() -> tuple[int, int]:
    """(total, current) rows in the JSON artifact `load_current_signals()`
    reads -- the raw counts, before `load_current_signals()` narrows to the
    subset conditions 1/3/4 actually rank over."""
    data = json.loads((SCREEN / "wave16_signals.json").read_text())
    total = len(data["signals"])
    current = sum(1 for s in data["signals"] if s.get("is_current"))
    return total, current


def fluree_signal_counts() -> tuple[int, int]:
    """(total, current) `ex:OpportunitySignal` nodes actually asserted in
    Fluree -- the store this product's §C names as authoritative for typed
    edges, not the JSON artifact this module reads for convenience."""
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2

    total_rows = fluree.query(f"""
        SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{
          ?s a <{EX}OpportunitySignal> }}""")
    current_rows = fluree.query(f"""
        SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{
          ?s a <{EX}OpportunitySignal> ; <{EX}isCurrent> "true" }}""")
    total = len(total_rows.get("results", {}).get("bindings", []))
    current = len(current_rows.get("results", {}).get("bindings", []))
    return total, current


def require_signal_parity_with_fluree() -> tuple[int, int]:
    """FINAL FIX WAVE, item 6. `load_current_signals()` reads
    `wave16_signals.json` under a "store reads" header, but a JSON file on
    disk is not a store -- conditions 1/3/4 were proving a property of that
    artifact, and its agreement with what actually loaded into Fluree
    (§C's authoritative store for `OpportunitySignal`) was assumed, not
    checked. Raises loudly on any mismatch rather than letting the four
    conditions silently rank against a stale or hand-edited artifact that
    no longer reflects the ledger. Returns (total, current) on success.
    """
    art_total, art_current = signal_artifact_counts()
    fluree_total, fluree_current = fluree_signal_counts()
    if (art_total, art_current) != (fluree_total, fluree_current):
        raise RuntimeError(
            "refusing to rank: wave16_signals.json disagrees with Fluree -- "
            f"artifact (total={art_total}, current={art_current}) != "
            f"Fluree (total={fluree_total}, current={fluree_current}). "
            "Re-run loaders/load_fluree_wave16.py or regenerate the "
            "artifact before trusting condition 1/3/4.")
    return art_total, art_current


def load_weights(cur, perspective_id: str, version: str) -> dict[str, float]:
    cur.execute(
        f'SELECT signal_type, weight FROM "{S}".perspective_weight '
        "WHERE perspective_id = %s AND weight_version = %s",
        (perspective_id, version))
    return {t: float(w) for t, w in cur.fetchall()}


def load_half_lives(cur) -> dict[str, int]:
    cur.execute(f'SELECT signal_type, half_life_days FROM "{S}".ib_signal_class')
    return dict(cur.fetchall())


def load_coverage(cur) -> list[tuple[str, str]]:
    cur.execute(f'SELECT banker_id, lei FROM "{S}".coverage_assignment')
    return cur.fetchall()


def load_bankers(cur) -> dict[str, str]:
    """banker_id -> desk."""
    cur.execute(f'SELECT banker_id, desk FROM "{S}".banker')
    return dict(cur.fetchall())


def load_restricted(sq: sqlite3.Connection) -> set[str]:
    rows = sq.execute(
        "SELECT lei FROM restricted_list WHERE removed_date IS NULL"
    ).fetchall()
    return {r[0] for r in rows}


def load_notes(sq: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    """(note_id, banker_id, lei, created_at) for every note that resolves to
    a banker -- signal_type is always 'banker_local_note' by table
    convention (see loaders/load_sqlite_wave16.py). `note_id` is carried so
    condition 3 can count the §F UNIT -- notes -- rather than the
    (banker, LEI) pairs a note happens to touch."""
    rows = sq.execute(
        "SELECT note_id, banker_id, lei, created_at FROM prospect_note "
        "WHERE banker_id IS NOT NULL"
    ).fetchall()
    return [(n, b, l, c) for n, b, l, c in rows]


def resolve_lei(cur, legal_name: str) -> str:
    """Resolve by legal_name, never by scanning for whichever LEI currently
    qualifies -- that pattern let an entity satisfy a divergence condition
    earlier in Wave 16 purely because it had no debt data at all."""
    cur.execute(f'SELECT lei FROM "{S}".legal_entity WHERE legal_name = %s',
                (legal_name,))
    rows = cur.fetchall()
    # An explicit raise, not `assert` -- a bare assert vanishes under
    # `python -O`, which would let a 0-or->1 match silently resolve to
    # nothing or to `rows[0][0]` of an arbitrary row.
    if len(rows) != 1:
        raise ValueError(
            f"expected exactly one legal_entity row for {legal_name!r}, "
            f"got {len(rows)}: {rows}")
    return rows[0][0]


def load_legal_names(cur) -> dict[str, str]:
    cur.execute(f'SELECT lei, legal_name FROM "{S}".legal_entity')
    return dict(cur.fetchall())


# --- rendering (house style, see validators/conditions.py) -----------------

def render(state: str, condition: str, detail: str) -> str:
    return f"  [{state}] {condition:52s} {detail}"


def main() -> int:
    signals = load_current_signals()
    shared_leis = sorted({s["lei"] for s in signals})

    with pg_connect() as conn, conn.cursor() as cur:
        ma_v2 = load_weights(cur, "PSP-MA", "v2")
        dcm_v2 = load_weights(cur, "PSP-DCM", "v2")
        sector_v2 = load_weights(cur, "PSP-SECTOR", "v2")
        ma_v1 = load_weights(cur, "PSP-MA", "v1")
        half_lives = load_half_lives(cur)
        coverage = load_coverage(cur)
        desks = load_bankers(cur)
        names = load_legal_names(cur)
        prospect_lei = resolve_lei(cur, DIVERGENT_PROSPECT)
        mirror_lei = resolve_lei(cur, MIRROR_PROSPECT)

    # FIX ROUND 1, finding 1 -- refuse to rank against a vector that loaded
    # to nothing, and refuse a replay pair that loaded identical, BEFORE any
    # of the four conditions below can turn that absence into a false PASS.
    require_nonempty_weights({
        "PSP-MA v2": ma_v2, "PSP-DCM v2": dcm_v2,
        "PSP-SECTOR v2": sector_v2, "PSP-MA v1": ma_v1,
    })
    require_versions_differ("PSP-MA v1", ma_v1, "PSP-MA v2", ma_v2)

    # FINAL FIX WAVE, item 6 -- confirm the JSON artifact conditions 1/3/4
    # rank over still agrees with Fluree, the store §C names as
    # authoritative, instead of assuming it as this module did before.
    parity_total, parity_current = require_signal_parity_with_fluree()

    sq = sqlite3.connect(SQLITE_PATH)
    restricted_leis = load_restricted(sq)
    notes = load_notes(sq)

    failures = 0

    print("IB-OPPORTUNITY-SYNTHESIS — §F floors, recomputed from the "
          f"stores at AS_OF_IB={AS_OF_IB}\n")
    print(render("ok  ", "parity: artifact == Fluree (OpportunitySignal)",
                 f"total={parity_total}  current={parity_current}"))

    # --- 1. DIVERGENCE -------------------------------------------------
    ma_scores = score(signals=signals, weights=ma_v2, half_lives=half_lives,
                       as_of=AS_OF_IB)
    dcm_scores = score(signals=signals, weights=dcm_v2, half_lives=half_lives,
                        as_of=AS_OF_IB)
    ma_order = rank(ma_scores)
    dcm_order = rank(dcm_scores)
    ma_rank = {lei: i + 1 for i, (lei, _) in enumerate(ma_order)}
    dcm_rank = {lei: i + 1 for i, (lei, _) in enumerate(dcm_order)}

    holds = divergence_holds(signals=signals, ma_weights=ma_v2,
                              dcm_weights=dcm_v2, half_lives=half_lives,
                              as_of=AS_OF_IB)

    prospect_ma, prospect_dcm = ma_rank.get(prospect_lei), dcm_rank.get(prospect_lei)
    mirror_ma, mirror_dcm = ma_rank.get(mirror_lei), dcm_rank.get(mirror_lei)
    n = len(shared_leis)

    named_ok = (prospect_ma is not None and prospect_dcm is not None
                and prospect_ma <= 3 and prospect_dcm > 20)
    mirror_ok = (mirror_ma is not None and mirror_dcm is not None
                 and mirror_dcm <= 3 and mirror_ma > 20)
    div_state = "PASS" if (holds and named_ok and mirror_ok) else "FAIL"
    if div_state == "FAIL":
        failures += 1

    print(render(div_state, "1. divergence (generic, >=1 LEI)",
                 f"divergence_holds={holds}  candidate set n={n}"))
    print(render(div_state,
                 f"   named: {DIVERGENT_PROSPECT}",
                 f"M&A #{prospect_ma} / DCM #{prospect_dcm} of {n} "
                 f"(need MA<=3, DCM>20)"))
    print(render(div_state,
                 f"   mirror: {MIRROR_PROSPECT}",
                 f"M&A #{mirror_ma} / DCM #{mirror_dcm} of {n} "
                 f"(need DCM<=3, MA>20)"))

    print("\n     rank  M&A originator" + " " * 30 + "DCM banker")
    top = max(prospect_ma or 0, mirror_dcm or 0, 5)
    for i in range(min(top, n)):
        ma_lei, ma_sc = ma_order[i]
        dcm_lei, dcm_sc = dcm_order[i]
        marker_ma = " <==" if ma_lei in (prospect_lei, mirror_lei) else "    "
        marker_dcm = " <==" if dcm_lei in (prospect_lei, mirror_lei) else "    "
        print(f"     {i + 1:>4}  {names.get(ma_lei, ma_lei)[:34]:34s} "
              f"{ma_sc:6.3f}{marker_ma}   "
              f"{names.get(dcm_lei, dcm_lei)[:34]:34s} {dcm_sc:6.3f}{marker_dcm}")
    print()

    # --- 2. CONTAINMENT -------------------------------------------------
    # FIX ROUND 1, finding 3 -- §F's floor is ">= 2 PROSPECTS ... absent
    # from the affected principals' candidate sets", i.e. distinct
    # restricted LEIs, not distinct bankers. `affected` (banker count) is
    # still printed, but the gate is on `exercised` (LEI count).
    affected, exercised, violations = containment_holds(coverage, restricted_leis)
    cont_state = "PASS" if (len(exercised) >= 2 and not violations) else "FAIL"
    if cont_state == "FAIL":
        failures += 1
    print(render(cont_state, "2. containment (restricted LEI absent, no marker)",
                 f"restricted LEIs exercised={len(exercised)} (need >=2)  "
                 f"walled bankers={affected}  violations={len(violations)}"))
    for banker_id, why, what in violations:
        print(f"       VIOLATION {banker_id}: {why}: {what}")

    # --- 3. NOTE MATERIALITY --------------------------------------------
    # FIX ROUND 1, finding 2 -- §F's unit is NOTES ("~50 ... >= 5 of which
    # change a ranking"), not (banker, LEI) position changes. A note on B
    # can knock A out of first place: A's position changed, but A's own
    # note (if it has one) may not be the cause, and a note-free entity
    # that merely got displaced is not itself a note "changing a ranking".
    # So: count NOTES whose OWN entity's position moved when that banker's
    # notes are included, and report the (banker, LEI) figure separately,
    # clearly labelled, so the two can never be confused again.
    # FINAL FIX WAVE, item 5 -- condition 3 must rank each banker's FILTERED
    # candidate set (restricted LEIs absent), not raw coverage. Condition 2
    # asserts a walled banker's candidate set never contains a restricted
    # LEI; ranking on raw `coverage` here contradicted that by counting
    # notes that sit on a walled entity (PN-0000, PN-0031, PN-0040 measured
    # against the pre-fix data) as if they were live candidates. Filtered
    # the same way `build_candidate_set` filters for condition 2, so the
    # two conditions describe the same world.
    filtered_coverage = [(b, l) for b, l in coverage if l not in restricted_leis]
    weight_vectors = {"PSP-MA": ma_v2, "PSP-DCM": dcm_v2, "PSP-SECTOR": sector_v2}
    notes_moving_own_entity, changed_pairs = note_materiality_counts(
        notes, filtered_coverage, desks, weight_vectors, signals, half_lives,
        AS_OF_IB)
    affected_bankers_with_notes = len({b for _n, b, _l, _c in notes})

    note_state = "PASS" if len(notes_moving_own_entity) >= 5 else "FAIL"
    if note_state == "FAIL":
        failures += 1
    print(render(note_state, "3. note materiality (notes moving OWN entity, >=5)",
                 f"notes={len(notes_moving_own_entity)}/{len(notes)}  "
                 f"(informative: total position changes="
                 f"{len(changed_pairs)}, affected bankers="
                 f"{affected_bankers_with_notes})"))

    # --- 4. WEIGHT REPLAY -------------------------------------------------
    replay_differs = weight_replay_differs(shared_leis, signals, ma_v1, ma_v2,
                                            half_lives, AS_OF_IB)
    replay_state = "PASS" if replay_differs else "FAIL"
    if replay_state == "FAIL":
        failures += 1
    order_v1 = [lei for lei, _ in rank(score(signals=signals, weights=ma_v1,
                                              half_lives=half_lives, as_of=AS_OF_IB))]
    order_v2 = [lei for lei, _ in rank(score(signals=signals, weights=ma_v2,
                                              half_lives=half_lives, as_of=AS_OF_IB))]
    moved = sum(1 for a, b in zip(order_v1, order_v2) if a != b)
    print(render(replay_state,
                 "4. weight replay (PSP-MA v1 vs v2, as_of fixed)",
                 f"orders differ={replay_differs}  positions moved={moved}/{n}"))

    print(f"\n  {4 - failures} passed · {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
