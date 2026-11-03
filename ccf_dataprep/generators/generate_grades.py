#!/usr/bin/env python3
"""Wave 11a Task 6 — generate the grade history as a supersession chain.

Per §D step 3 of `rating-and-spread-migration`: *"the migration IS the
supersession chain, which is why this product needs a ledger rather than a
current-state table."* A grade is therefore **never overwritten**. Each
rerating writes a new assertion carrying `supersedes` — the `assertion_id`
of the assertion it replaces — and the superseded assertion keeps the
`valid_to` it was given when it was closed out. Reading the chain backwards
(follow `supersedes`) reconstructs the migration exactly.

This reuses Wave 5's bitemporal vocabulary rather than minting anything new:
`ex:validFrom` (223 assertions before this wave), `ex:assertedAt` (29), and
`ex:supersededBy` — declared since Wave 5, populated for the first time by
this task's output, the same shape as `fibo-fnd-rel-rel:controls` sitting
declared-and-empty from Wave 8 until Wave 10's follow-up. Task 8 loads these
JSON fields into Fluree; this task only produces the ledger's contents.

## The internal grade scale

FIBO carries no notion of an internal credit grade, and none is needed here
beyond a total order matching the five FRED OAS bands this wave already
fetched (`docs/wave11a-design.md` §1.3: AA, A, BBB, BB, B — no AAA, because
this is a mid-market leveraged cast, and nothing below B, because there is
no sixth OAS series to price a weaker band against). Each band is split into
three notches (+, flat, -), giving a 15-point scale:

    AA+  AA  AA-  A+  A  A-  BBB+  BBB  BBB-  BB+  BB  BB-  B+  B  B-
     0    1   2   3  4   5    6     7    8     9   10  11  12  13  14

`notch` is that integer position (0 = best, 14 = worst — the standard
direction for a numeric risk grade, e.g. Moody's 1=Aaa..21=C). `grade` is
the string. An obligor's initial grade is the PLAIN letter of its
`rating_band` (e.g. "BB", not "BB+"), which is the middle notch of that
band — so every chain starts consistent with the band that also selects
its FRED market series, per the brief.

## Cadence

Each of the 30 obligors gets 8 quarterly assertions (91-day steps from the
window start, 2024-08-19) plus, for a subset, one additional off-cycle
assertion landing strictly between two quarterly points and carrying a named
`trigger`. Floor is >= 4 off-cycle; this generator places 5 (1 confirming +
4 additional) for margin.

## The confirming rerating

Task 5 placed four divergence windows in `wave11a_spreads.json` and flagged
exactly one `confirm_later: true` — read here, not hardcoded. For that
obligor's LEI, the regular quarterly cadence is held flat (no independent
drift) so the ONLY grade movement in its chain is the deliberate one-notch
downgrade placed after the divergence window closes: the market widened
first, the grade followed. The other three divergence LEIs are also held
completely flat across all 8 quarterly points and receive no off-cycle
event, which guarantees by construction — not by chance — that they carry
no confirming move.

    uv run generators/generate_grades.py --dry-run
    uv run generators/generate_grades.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from random import Random

from ccf.config import REPO_ROOT
from generators.narrative_wave11a import SEED, band_of_grade, divergence_windows_for_artifact  # noqa: F401

SCREEN = REPO_ROOT / "sources" / "screening"

WINDOW_START = date(2024, 8, 19)
WINDOW_END = date(2026, 8, 18)

N_QUARTERS = 8
QUARTER_STEP_DAYS = 91

#: Confirming rerating lands this many days after the divergence window's
#: `end_date` -- long enough that it reads as a credit-committee review
#: acting on a *sustained* widening rather than reacting to a single day's
#: print, short enough that the causal story (market moved, grade followed)
#: stays legible.
CONFIRM_LAG_DAYS = 30

#: Additional off-cycle obligors beyond the one carrying the confirming
#: rerating. 4 + 1 = 5 total, against the >= 4 floor.
N_EXTRA_OFFCYCLE = 4

PROVENANCE_INTERNAL = "synthetic — internal"
PROVENANCE_ENGINEERED = "synthetic — engineered"

# --------------------------------------------------------------------------
# The grade scale -- pure, no I/O
# --------------------------------------------------------------------------

BANDS_BEST_TO_WORST: list[str] = ["AA", "A", "BBB", "BB", "B"]
NOTCH_MODS_BEST_TO_WORST: list[str] = ["+", "", "-"]

GRADE_SCALE: list[str] = [
    f"{band}{mod}" for band in BANDS_BEST_TO_WORST
    for mod in NOTCH_MODS_BEST_TO_WORST
]
NOTCH_OF_GRADE: dict[str, int] = {g: i for i, g in enumerate(GRADE_SCALE)}
MAX_NOTCH = len(GRADE_SCALE) - 1  # 14, worst = B-

# `band_of_grade` is imported from `narrative_wave11a` above -- single
# source shared with `generate_spreads.py` and `validators/series.py`.


def initial_notch_for_band(rating_band: str) -> int:
    """The plain-letter (middle) notch of the given band -- e.g. "BB" -> the
    notch for grade "BB", not "BB+" or "BB-"."""
    return NOTCH_OF_GRADE[rating_band]


def clamp_notch(n: int) -> int:
    return max(0, min(MAX_NOTCH, n))


# --------------------------------------------------------------------------
# Deterministic RNGs -- each keyed off (SEED, purpose, lei[, extra]) so the
# series is reproducible independent of any dict/set iteration order.
# --------------------------------------------------------------------------

def _rng_for(*parts: str) -> Random:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return Random(int(digest[:16], 16))


def quarterly_dates(start: date = WINDOW_START) -> list[date]:
    return [start + timedelta(days=QUARTER_STEP_DAYS * i)
            for i in range(N_QUARTERS)]


def booking_lag_days(lei: str, valid_from: date) -> int:
    """1-5 days -- a small, deterministic gap between a grade becoming
    effective and the credit desk booking the assertion, distinct from
    `valid_from` so `asserted_at` is never a duplicate of it."""
    rng = _rng_for(str(SEED), "booking-lag", lei, valid_from.isoformat())
    return rng.randint(1, 5)


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------

def load_obligors() -> list[dict]:
    payload = json.loads((SCREEN / "wave11a_instruments.json").read_text())
    return sorted(payload["obligors"], key=lambda o: o["lei"])


def load_divergence_windows() -> list[dict]:
    """The declared windows, enriched -- read from the shared narrative
    module, NOT from wave11a_spreads.json. See narrative_wave11a.py's module
    docstring: that artifact read was the dependency cycle.
    """
    payload = json.loads((SCREEN / "wave11a_instruments.json").read_text())
    return sorted(divergence_windows_for_artifact(payload["instruments"]),
                  key=lambda w: w["instrument_id"])


def find_confirming_window(windows: list[dict]) -> dict:
    confirmed = [w for w in windows if w["confirm_later"]]
    if len(confirmed) != 1:
        raise RuntimeError(
            f"expected exactly 1 confirm_later divergence window, "
            f"found {len(confirmed)}: {[w['instrument_id'] for w in confirmed]}")
    return confirmed[0]


# --------------------------------------------------------------------------
# Off-cycle trigger catalogue -- each entry names WHY the review happened
# and the direction it moves the grade (+1 = worse/downgrade, -1 = better).
# --------------------------------------------------------------------------

OFFCYCLE_TRIGGERS: list[tuple[str, int]] = [
    ("leverage covenant breach disclosed in a compliance certificate", +1),
    ("unplanned dividend recapitalization increases leverage", +1),
    ("sector-wide stress review following a regional credit event", +1),
    ("management guidance withdrawal following an investor call", +1),
    ("asset disposition materially reduces net leverage", -1),
    ("refinancing extends the maturity profile and lowers near-term rollover risk", -1),
]

CONFIRMING_TRIGGER = (
    "ad hoc credit review following sustained spread widening "
    "in the obligor's traded debt")


# --------------------------------------------------------------------------
# Chain construction -- pure given its inputs
# --------------------------------------------------------------------------

def pick_offcycle_date(
    lei: str, q_dates: list[date], interval_idx: int,
) -> date:
    """A date strictly inside (q_dates[interval_idx], q_dates[interval_idx+1]),
    kept >= 10 days from both endpoints so it never collides with, or reads
    as, a regular quarterly review."""
    lo, hi = q_dates[interval_idx], q_dates[interval_idx + 1]
    margin = 10
    span = (hi - lo).days
    assert span > 2 * margin, f"quarter interval too short for margin: {span}d"
    rng = _rng_for(str(SEED), "offcycle-date", lei, str(interval_idx))
    offset = rng.randint(margin, span - margin)
    return lo + timedelta(days=offset)


def build_events(
    *,
    lei: str,
    rating_band: str,
    q_dates: list[date],
    frozen: bool,
    offcycle: tuple[date, str, int] | None,
) -> list[tuple[date, int | None, str, bool]]:
    """Returns a sorted list of (event_date, delta_notch, trigger, is_root).

    `delta_notch` is relative (applied cumulatively to the running notch);
    `None` on the root event, whose notch is `initial_notch_for_band`.

    `frozen` obligors (the 4 divergence LEIs) get zero drift on every
    quarterly point -- by construction, not by chance, so they cannot
    coincidentally produce a confirming move.
    """
    events: list[tuple[date, int | None, str, bool]] = [
        (q_dates[0], None, "initial rating (window start)", True),
    ]

    if not frozen:
        rng = _rng_for(str(SEED), "quarterly-drift", lei)
        for q in q_dates[1:]:
            # 20% chance of a 1-notch move; of those, 60% worse / 40% better.
            roll = rng.random()
            if roll < 0.20:
                delta = 1 if rng.random() < 0.60 else -1
            else:
                delta = 0
            events.append((q, delta, "quarterly review", False))
    else:
        for q in q_dates[1:]:
            events.append((q, 0, "quarterly review", False))

    if offcycle is not None:
        ev_date, trigger, delta = offcycle
        events.append((ev_date, delta, trigger, False))

    events.sort(key=lambda e: e[0])
    dates = [e[0] for e in events]
    if len(set(dates)) != len(dates):
        raise RuntimeError(f"{lei}: duplicate event dates in {dates}")
    return events


def mint_assertion_id(lei: str, sequence: int) -> str:
    """`syn-g-<6 hex>`, deterministic from (lei, sequence) -- never
    rating-agency-shaped, mirroring `syn-i-` for instruments."""
    digest = hashlib.sha256(f"{SEED}|grade|{lei}|{sequence}".encode()).hexdigest()
    return f"syn-g-{digest[:6]}"


def build_chain(
    *,
    lei: str,
    rating_band: str,
    q_dates: list[date],
    frozen: bool,
    offcycle: tuple[date, str, int] | None,
) -> list[dict]:
    """Walks the sorted events for one obligor into a fully-linked
    supersession chain: exact valid_from, valid_to = next event's
    valid_from (None on the last), asserted_at = valid_from + a small
    booking lag, supersedes = the previous assertion_id.

    Every assertion is minted `PROVENANCE_INTERNAL` here; the caller
    upgrades exactly one (the confirming rerating) to `PROVENANCE_ENGINEERED`
    afterward, since that classification depends on which LEI carries the
    confirming divergence, not on anything local to this function.
    """
    events = build_events(
        lei=lei, rating_band=rating_band, q_dates=q_dates,
        frozen=frozen, offcycle=offcycle)

    notch = initial_notch_for_band(rating_band)
    assertions: list[dict] = []
    prev_id: str | None = None

    for i, (ev_date, delta, trigger, is_root) in enumerate(events):
        if not is_root:
            notch = clamp_notch(notch + delta)
        grade = GRADE_SCALE[notch]
        assertion_id = mint_assertion_id(lei, i)
        assertions.append({
            "assertion_id": assertion_id,
            "lei": lei,
            "grade": grade,
            "notch": notch,
            "valid_from": ev_date.isoformat(),
            "valid_to": None,  # patched below once the next date is known
            "asserted_at": (ev_date + timedelta(
                days=booking_lag_days(lei, ev_date))).isoformat(),
            "supersedes": prev_id,
            "trigger": trigger,
            "provenance": PROVENANCE_INTERNAL,
        })
        prev_id = assertion_id

    for i in range(len(assertions) - 1):
        assertions[i]["valid_to"] = assertions[i + 1]["valid_from"]

    return assertions


# --------------------------------------------------------------------------
# Chain integrity -- pure, checked against both the real output and a
# hand-built broken case so the checker is proven able to fail.
# --------------------------------------------------------------------------

def check_chain_integrity(assertions: list[dict]) -> dict:
    """Returns counts of defects across the WHOLE assertion set (all
    obligors together): dangling `supersedes`, double-supersession, cycles,
    and per-obligor interval gaps/overlaps. All should be 0 on real output.
    """
    by_id = {a["assertion_id"]: a for a in assertions}

    dangling = [a["supersedes"] for a in assertions
                if a["supersedes"] is not None and a["supersedes"] not in by_id]

    supersedes_targets = [a["supersedes"] for a in assertions
                           if a["supersedes"] is not None]
    double_superseded = sorted(
        {t for t in supersedes_targets if supersedes_targets.count(t) > 1})

    cycles: list[str] = []
    for a in assertions:
        seen = set()
        cur = a["assertion_id"]
        while cur is not None:
            if cur in seen:
                cycles.append(a["assertion_id"])
                break
            seen.add(cur)
            nxt = by_id.get(cur)
            cur = nxt["supersedes"] if nxt else None

    by_lei: dict[str, list[dict]] = {}
    for a in assertions:
        by_lei.setdefault(a["lei"], []).append(a)

    gap_overlap_leis: list[str] = []
    for lei, rows in by_lei.items():
        rows_sorted = sorted(rows, key=lambda r: r["valid_from"])
        ok = True
        for i in range(len(rows_sorted) - 1):
            if rows_sorted[i]["valid_to"] != rows_sorted[i + 1]["valid_from"]:
                ok = False
        if rows_sorted and rows_sorted[-1]["valid_to"] is not None:
            ok = False
        if not ok:
            gap_overlap_leis.append(lei)

    return {
        "dangling_supersedes": dangling,
        "double_superseded": double_superseded,
        "cycles": cycles,
        "gap_or_overlap_leis": sorted(gap_overlap_leis),
    }


def _selftest() -> list[tuple[str, bool]]:
    """Hand-built cases -- including one deliberately broken -- proving the
    checker can both pass and fail."""
    good = [
        {"assertion_id": "a1", "lei": "X", "valid_from": "2024-01-01",
         "valid_to": "2024-04-01", "supersedes": None},
        {"assertion_id": "a2", "lei": "X", "valid_from": "2024-04-01",
         "valid_to": None, "supersedes": "a1"},
    ]
    broken_gap = [
        {"assertion_id": "b1", "lei": "Y", "valid_from": "2024-01-01",
         "valid_to": "2024-04-01", "supersedes": None},
        {"assertion_id": "b2", "lei": "Y", "valid_from": "2024-05-01",
         "valid_to": None, "supersedes": "b1"},
    ]
    broken_dangling = [
        {"assertion_id": "c2", "lei": "Z", "valid_from": "2024-01-01",
         "valid_to": None, "supersedes": "c-does-not-exist"},
    ]
    broken_double = [
        {"assertion_id": "d1", "lei": "W", "valid_from": "2024-01-01",
         "valid_to": "2024-04-01", "supersedes": None},
        {"assertion_id": "d2", "lei": "W", "valid_from": "2024-04-01",
         "valid_to": None, "supersedes": "d1"},
        {"assertion_id": "d3", "lei": "W", "valid_from": "2024-04-01",
         "valid_to": None, "supersedes": "d1"},
    ]

    r_good = check_chain_integrity(good)
    r_gap = check_chain_integrity(broken_gap)
    r_dangling = check_chain_integrity(broken_dangling)
    r_double = check_chain_integrity(broken_double)

    return [
        ("a clean two-assertion chain reports zero defects",
         not any(r_good.values())),
        ("a gap between valid_to and the next valid_from is caught",
         "Y" in r_gap["gap_or_overlap_leis"]),
        ("a supersedes pointing at a nonexistent id is caught",
         "c-does-not-exist" in r_dangling["dangling_supersedes"]),
        ("an assertion superseded twice is caught",
         "d1" in r_double["double_superseded"]),
    ]


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("Wave 11a Task 6 — grade history self-test\n")
    selftest_cases = _selftest()
    for label, ok in selftest_cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    selftest_failures = sum(not ok for _, ok in selftest_cases)
    print(f"\n  {len(selftest_cases) - selftest_failures}/{len(selftest_cases)} "
          f"integrity-checker self-test cases behave as specified\n")
    if selftest_failures:
        print("  integrity checker itself is broken — aborting")
        return 1

    obligors = load_obligors()
    windows = load_divergence_windows()
    confirming = find_confirming_window(windows)

    confirm_lei = confirming["lei"]
    confirm_band = confirming["rating_band"]
    confirm_window_end = date.fromisoformat(confirming["end_date"])

    # Sanity: the confirming LEI is actually one of our 30 obligors, and its
    # instrument-level band agrees with the obligor's own rating_band.
    obligor_by_lei = {o["lei"]: o for o in obligors}
    if confirm_lei not in obligor_by_lei:
        raise RuntimeError(f"confirming LEI {confirm_lei} not among obligors")
    if obligor_by_lei[confirm_lei]["rating_band"] != confirm_band:
        raise RuntimeError(
            f"confirming window band {confirm_band} != obligor rating_band "
            f"{obligor_by_lei[confirm_lei]['rating_band']} for {confirm_lei}")

    non_confirming_leis = sorted(
        w["lei"] for w in windows if not w["confirm_later"])
    if len(non_confirming_leis) != len(windows) - 1:
        raise RuntimeError("expected exactly 3 non-confirming divergence LEIs")
    frozen_leis = set(non_confirming_leis) | {confirm_lei}

    q_dates = quarterly_dates()

    confirm_date = confirm_window_end + timedelta(days=CONFIRM_LAG_DAYS)
    if not confirm_date > confirm_window_end:
        raise RuntimeError("confirming rerating does not land after the "
                            "divergence window closes")
    if confirm_date in q_dates:
        raise RuntimeError("confirming rerating collides with a quarterly date")

    # --- off-cycle obligor selection: 4 more, drawn from obligors that are
    # neither the confirming LEI nor one of the 3 frozen non-confirming
    # divergence LEIs, so every off-cycle story stays clean of the
    # divergence narrative.
    eligible = sorted(o["lei"] for o in obligors if o["lei"] not in frozen_leis)
    selection_rng = _rng_for(str(SEED), "offcycle-selection")
    extra_offcycle_leis = sorted(
        selection_rng.sample(eligible, N_EXTRA_OFFCYCLE))

    trigger_rng = _rng_for(str(SEED), "offcycle-trigger-assignment")
    trigger_choices = trigger_rng.sample(OFFCYCLE_TRIGGERS, N_EXTRA_OFFCYCLE)

    interval_rng = _rng_for(str(SEED), "offcycle-interval-assignment")

    offcycle_by_lei: dict[str, tuple[date, str, int]] = {}
    for lei, (trigger, delta) in zip(extra_offcycle_leis, trigger_choices):
        interval_idx = interval_rng.randint(0, N_QUARTERS - 2)
        ev_date = pick_offcycle_date(lei, q_dates, interval_idx)
        offcycle_by_lei[lei] = (ev_date, trigger, delta)
    offcycle_by_lei[confirm_lei] = (confirm_date, CONFIRMING_TRIGGER, +1)

    all_assertions: list[dict] = []
    off_cycle_count = 0
    regular_count = 0
    for obligor in obligors:
        lei = obligor["lei"]
        band = obligor["rating_band"]
        frozen = lei in frozen_leis
        offcycle = offcycle_by_lei.get(lei)

        chain = build_chain(
            lei=lei, rating_band=band, q_dates=q_dates, frozen=frozen,
            offcycle=offcycle)

        if offcycle is not None:
            # Mark the off-cycle assertion's provenance -- and, for the
            # confirming obligor only, as engineered. The off-cycle event's
            # date never collides with a quarterly or root date (enforced
            # in `build_events`), so exactly one assertion matches.
            offcycle_date_iso = offcycle[0].isoformat()
            matched = 0
            for a in chain:
                if a["valid_from"] == offcycle_date_iso:
                    if lei == confirm_lei:
                        a["provenance"] = PROVENANCE_ENGINEERED
                    off_cycle_count += 1
                    matched += 1
                else:
                    regular_count += 1
            if matched != 1:
                raise RuntimeError(
                    f"{lei}: expected exactly 1 off-cycle assertion, "
                    f"matched {matched}")
        else:
            regular_count += len(chain)

        all_assertions.append(chain)

    assertions = [a for chain in all_assertions for a in chain]

    # Global determinism / uniqueness guard.
    ids = [a["assertion_id"] for a in assertions]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise RuntimeError(f"duplicate assertion_id: {dupes[:5]}")

    integrity = check_chain_integrity(assertions)
    integrity_ok = not any(integrity.values())

    # Verify the confirming move itself, from the data, not by construction
    # alone: find the confirming LEI's chain, locate the assertion whose
    # valid_from == confirm_date, and check grade got worse vs its
    # predecessor and that predecessor was unchanged since window start.
    confirm_chain = sorted(
        (a for a in assertions if a["lei"] == confirm_lei),
        key=lambda a: a["valid_from"])
    confirm_assertion = next(
        a for a in confirm_chain if a["valid_from"] == confirm_date.isoformat())
    confirm_predecessor = next(
        a for a in confirm_chain if a["assertion_id"] == confirm_assertion["supersedes"])
    confirm_moved_worse = confirm_assertion["notch"] > confirm_predecessor["notch"]
    confirm_after_window = confirm_date > confirm_window_end
    confirm_predecessor_unchanged = (
        confirm_predecessor["notch"]
        == initial_notch_for_band(confirm_band))

    # Verify the 3 non-confirming divergence LEIs never move.
    non_confirm_static = all(
        len({a["notch"] for a in assertions if a["lei"] == lei}) == 1
        for lei in non_confirming_leis)

    print("Wave 11a Task 6 — grade history\n")
    obligor_count = len({a["lei"] for a in assertions})
    print(f"  obligors covered            {obligor_count} / {len(obligors)}")
    print(f"  assertions generated        {len(assertions)}")
    print(f"  regular (quarterly) count   {regular_count}")
    print(f"  off-cycle count             {off_cycle_count}  (floor >= 4)")

    print(f"\n  chain integrity")
    print(f"    dangling supersedes       {len(integrity['dangling_supersedes'])}")
    print(f"    double-superseded         {len(integrity['double_superseded'])}")
    print(f"    cycles                    {len(integrity['cycles'])}")
    print(f"    interval gaps/overlaps    {len(integrity['gap_or_overlap_leis'])}")
    print(f"    [{'ok  ' if integrity_ok else 'FAIL'}] chain integrity clean")

    print(f"\n  confirming rerating")
    print(f"    lei                       {confirm_lei}")
    print(f"    band                      {confirm_band}")
    print(f"    divergence window         {confirming['start_date']} -> "
          f"{confirming['end_date']}")
    print(f"    confirming valid_from     {confirm_date.isoformat()}  "
          f"({CONFIRM_LAG_DAYS}d after window close)")
    print(f"    grade before -> after     {confirm_predecessor['grade']} -> "
          f"{confirm_assertion['grade']}")
    print(f"    [{'ok  ' if confirm_after_window else 'FAIL'}] "
          f"lands after the divergence window closes")
    print(f"    [{'ok  ' if confirm_moved_worse else 'FAIL'}] "
          f"moves worse (downgrade), confirming the widening")
    print(f"    [{'ok  ' if confirm_predecessor_unchanged else 'FAIL'}] "
          f"predecessor grade unchanged since window start")

    print(f"\n  other 3 divergence windows (must get NO confirming move)")
    for lei in non_confirming_leis:
        notches = sorted({a["notch"] for a in assertions if a["lei"] == lei})
        print(f"    {lei}   distinct notches over the window: {notches}")
    print(f"    [{'ok  ' if non_confirm_static else 'FAIL'}] "
          f"all 3 stay at a single, unchanged grade")

    checks_ok = (integrity_ok and confirm_after_window and confirm_moved_worse
                 and confirm_predecessor_unchanged and non_confirm_static
                 and off_cycle_count >= 4)

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0 if checks_ok else 1

    payload = {
        "wave": "11a",
        "task": 6,
        "seed": SEED,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_for": "rating-and-spread-migration",
        "window": {"start": WINDOW_START.isoformat(), "end": WINDOW_END.isoformat()},
        "grade_scale": {
            "order": "best to worst",
            "grades": GRADE_SCALE,
            "note": "notch 0 = best (AA+), notch 14 = worst (B-); band split "
                    "into 3 notches (+, flat, -); bands match the 5 FRED OAS "
                    "series this wave fetched, no AAA and nothing below B.",
        },
        "cadence": {
            "quarterly_points_per_obligor": N_QUARTERS,
            "quarterly_step_days": QUARTER_STEP_DAYS,
            "off_cycle_floor": 4,
            "off_cycle_actual": off_cycle_count,
        },
        "confirming_rerating": {
            "lei": confirm_lei,
            "rating_band": confirm_band,
            "divergence_window": {
                "start_date": confirming["start_date"],
                "end_date": confirming["end_date"],
            },
            "confirm_valid_from": confirm_date.isoformat(),
            "confirm_lag_days": CONFIRM_LAG_DAYS,
            "grade_before": confirm_predecessor["grade"],
            "grade_after": confirm_assertion["grade"],
            "assertion_id": confirm_assertion["assertion_id"],
        },
        "non_confirming_divergence_leis": non_confirming_leis,
        "provenance": {
            "grade": PROVENANCE_INTERNAL,
            "notch": PROVENANCE_INTERNAL,
            "trigger": PROVENANCE_INTERNAL,
            "confirming_rerating_assertion": PROVENANCE_ENGINEERED,
        },
        "assertions": assertions,
        "notes": [
            "supersedes points from a new assertion at the one it replaces; "
            "the loader (Task 8) is expected to write ex:supersededBy on the "
            "OLD assertion pointing at the NEW one -- the inverse direction.",
            "the confirming LEI and the 3 non-confirming divergence LEIs are "
            "held flat across all 8 quarterly points BY CONSTRUCTION, so the "
            "confirming case cannot be confused with routine drift and the "
            "other three cannot coincidentally produce a confirming move.",
        ],
    }

    SCREEN.mkdir(parents=True, exist_ok=True)
    out = SCREEN / "wave11a_grades.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")

    return 0 if checks_ok else 1


if __name__ == "__main__":
    sys.exit(main())
