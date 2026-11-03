#!/usr/bin/env python3
"""Wave 11a Task 4 — generate the instrument set.

`rating-and-spread-migration` needs ~60 engineered debt instruments over ~30
real obligors. Per-CUSIP TRACE history is licensed and unreachable (see
`docs/wave11a-design.md` §1.1), so the instruments themselves are invented —
but the **obligor selection and issuance events are not.** Selection is a
deterministic public ranking over XBRL, and each instrument's `issue_date` is
anchored to a real Item 2.03 ("Creation of a Direct Financial Obligation") 8-K
filing date wherever that obligor has one. That is what keeps the issuance
*event* public even though the instrument that supposedly resulted from it is
`synthetic — engineered`. Do not blur the two: the filing is real, the bond is
not.

## Obligor selection

The 30 largest, by most-recent reported `LongTermDebt`-family value in
`ccf_v2.financial_fact`, restricted to obligors with >= 1 Item 2.03 filing
(checked against `ccf_v2.filing_profile.count_8k_item_2_03`, the canonical
public count — not re-derived from the issuance JSON, though the two agree).
Ties broken by LEI ascending. "Most recent" means highest `period_end`, tied
by `filed_date`, tied by `accession` — never `MAX(value)`, which would silently
answer a different question (largest EVER reported, not most recently).

Three XBRL tags carry this concept and issuers do not agree on which one they
use, so a fixed priority order applies per obligor: `LongTermDebt` (46 of 50
issuers use it) > `LongTermDebtNoncurrent` (fills 2 more) >
`DebtLongtermAndShorttermCombinedAmount`. Once a tag is chosen for an obligor,
only that tag's most-recent value is used — never an average or max across
tags, which would mix distinct accounting concepts.

**Force-include the confirmed rating-action anchors, regardless of debt rank.**
§F condition 6 wants >= 1 obligor with a rating action in a real 8-K, and
tying that to a debt ranking means a future refresh could silently drop the
condition. The confirmed set is read from `wave11a_rating_actions.json`
(`confirmed: true`), never hardcoded — Task 3's own design-time note flagged a
prior draft that hardcoded "5" when a fixed confirmation gate later produced 4
(Targa Resources, Celanese, Independence Realty Trust, Vertiv Holdings).
Measured on this run: all 4 already fall inside the top 30 by debt, so
force-inclusion adds nothing THIS run — reported honestly rather than assumed,
per the project's standing "measure it" rule. The mechanism stays in place
because the next XBRL refresh could reorder the ranking and make it load-
bearing.

## Rating band

One of AA / A / BBB / BB / B — no AAA, matching the five FRED ICE BofA OAS
series Task 2 fetched (this cast is mid-market and leveraged; no anchor in it
would plausibly price at AAA). The band is derived, not assigned: a leverage
ratio of most-recent reported `LongTermDebt` (the same value used for ranking)
over most-recent reported `Assets`. Debt/Assets was chosen over Debt/Equity
because equity data is incomplete for this cast (46 of 50 issuers) while
Assets is complete for every obligor actually selected (verified: all 30
selected obligors report `Assets`), and a leverage rule that needs a fallback
branch to run at all is a worse rule than one that does not.

Fixed thresholds (measured against the 30 selected obligors to confirm the
rule discriminates rather than collapsing into one band — see the printed
distribution at the bottom of a run):

    D/A <= 0.15                    AA
    0.15 < D/A <= 0.30             A
    0.30 < D/A <= 0.50             BBB
    0.50 < D/A <= 0.70             BB
    D/A > 0.70 (or no Assets data) B

The band is recorded on the instrument, not implied by the obligor, because it
is a **join key**: Task 5 uses it to pick which of the five FRED series drives
that instrument's market factor.

## Laddering and maturity

Two instruments per obligor (30 x 2 = 60). Each instrument's `issue_date` is a
real Item 2.03 filing date for that obligor — the most recent for instrument 0,
the second-most-recent for instrument 1 (or the same single filing reused, for
the few obligors that have only one). Tenor is drawn from a ladder of common
corporate maturities (2/3/5/7/10/12/15/18/22/25 years), filtered per
instrument against a maturity window with a bound on **both** sides:

- not before `WINDOW_FLOOR` (2027-01-01) — the market data this dataset
  carries (Treasury + FRED) runs through 2026-08-18, so a short tenor off an
  old anchor filing could produce an instrument already dead before Task 5/6
  can observe it;
- not after `MATURITY_CEILING` (`WINDOW_START` + 28 years) — the Treasury par
  curve's longest tenor is 30 Yr, and `curves.interpolate_tenor` correctly
  returns `None` past it rather than extrapolating, so a *long* tenor off a
  *recent* anchor filing could produce an instrument with years-to-maturity
  exceeding 30 for part of the observation window, carrying zero spread
  observations for that stretch. The pre-fix ladder (which reached 30 years)
  produced exactly this: six instruments maturing out to 2056-08-07, up to
  32 years from the window's start. A count-based check for "≥ 2 thinly-
  traded instruments with observation gaps" (§F condition 7) could have been
  satisfied by that accident instead of by the deliberate divergence
  Task 5/6 are supposed to engineer — the "counted but not created" failure
  arriving from the opposite direction.

Both bounds are floors/ceilings, not targets: only the instruments actually
near either edge are constrained by them. Recent filings (most of the cast)
still draw from the full ladder; only the one obligor whose sole anchor
filing is from 2012 is pinned to the floor's longer tenors.

## Identifiers

`syn-i-<6 hex>`, deterministic from `(SEED, lei, sequence)` via SHA-256 so
re-runs are stable without needing a lookup table. Never CUSIP-shaped: a real
CUSIP is nine alphanumeric characters with a check digit; six lowercase hex
digits after `syn-i-` shares no property with one and cannot be looked up
anywhere real.

## Determinism

Fixed `SEED`. No wall-clock reads outside the `generated_at` provenance field
(the Postgres date/RNG-affecting logic never touches `date.today()`). Every
`SELECT` whose row order can reach the RNG carries an explicit `ORDER BY` —
Wave 10's defect was an unordered `deal` query whose *order*, not the seed, was
what varied between runs.

    uv run generators/generate_instruments.py --dry-run
    uv run generators/generate_instruments.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from random import Random

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
SEED = 20260817

OBLIGOR_COUNT = 30
INSTRUMENTS_PER_OBLIGOR = 2

#: Priority order for the three tags that carry "long-term debt" in this
#: corpus. Fixed per obligor -- never averaged or maxed across tags, which
#: would mix distinct XBRL concepts.
DEBT_TAGS = [
    "LongTermDebt",
    "LongTermDebtNoncurrent",
    "DebtLongtermAndShorttermCombinedAmount",
]

#: Debt/Assets leverage -> rating band. No AAA: matches the five FRED series
#: fetched in Task 2 for a mid-market, leveraged cast.
BAND_THRESHOLDS: list[tuple[float, str]] = [
    (0.15, "AA"),
    (0.30, "A"),
    (0.50, "BBB"),
    (0.70, "BB"),
]
DEFAULT_BAND = "B"  # > highest threshold, or no leverage data at all

#: Common corporate note/bond tenors, years. Laddered per instrument (see
#: `eligible_tenors`) so an instrument from an old anchor filing cannot draw a
#: tenor that would mature it before the market data even starts, AND so a
#: recent instrument cannot draw a tenor that outruns the benchmark curve.
#: Capped at 25 (not the Treasury curve's own 30 Yr ceiling): a 25-year note
#: issued near the end of the window still sits under 30 years to maturity
#: at every observation date across the whole window, with margin. A ladder
#: that reached all the way to 30 would let an instrument issued near the
#: window's end need a 30+ Yr point on day one -- `interpolate_tenor`
#: correctly returns None past the curve's longest tenor, so that instrument
#: would carry zero spread observations for its entire life. Six such
#: instruments existed under the pre-fix ladder (maturities out to
#: 2056-08-07, up to 32 years from window start) before this cap was added.
TENOR_LADDER: list[int] = [2, 3, 5, 7, 10, 12, 15, 18, 22, 25]

#: No market-data date this dataset carries is later than 2026-08-18 (Task 2's
#: Treasury/FRED fetch). Every instrument must still be outstanding well past
#: that so Task 5/6 have something to observe across the wave's 24-month
#: window; 2027-01-01 gives comfortable margin without constraining any tenor
#: choice for a recently-filed obligor.
WINDOW_FLOOR = date(2027, 1, 1)

#: The other side of the same bound. Task 5/6's observation window is the
#: most recent 24 months of the Treasury/FRED data (2024-08-19 -> 2026-08-18,
#: per the wave's own §F envelope). A maturity is priceable across the WHOLE
#: window only while years-to-maturity stays under the curve's 30 Yr ceiling
#: at every date in it -- which, measured from the window's START (the
#: hardest point, since years-to-maturity is largest there), means no
#: instrument may mature more than ~28 years past 2024-08-19. 28, not 30:
#: margin, not a knife-edge against the curve's own limit.
WINDOW_START = date(2024, 8, 19)
MATURITY_CEILING_YEARS = 28

BASE_COUPON_PCT = {"AA": 4.00, "A": 4.50, "BBB": 5.25, "BB": 6.75, "B": 8.50}
TERM_PREMIUM_PCT_PER_YEAR = 0.03
COUPON_JITTER_PCT = 0.15

FACE_LADDER_USD = [
    250_000_000, 300_000_000, 350_000_000, 400_000_000, 500_000_000,
    600_000_000, 750_000_000, 800_000_000, 1_000_000_000, 1_250_000_000,
]

SENIORITY_CHOICES = ["senior unsecured", "senior secured", "subordinated"]
SENIORITY_WEIGHTS = [0.65, 0.25, 0.10]

PROVENANCE = "synthetic — engineered"


# --------------------------------------------------------------------------
# Pure logic (kept import-testable, no I/O)
# --------------------------------------------------------------------------

def mint_instrument_id(seed: int, lei: str, sequence: int) -> str:
    """`syn-i-<6 hex>`, deterministic and never CUSIP-shaped."""
    digest = hashlib.sha256(f"{seed}|{lei}|{sequence}".encode()).hexdigest()
    return f"syn-i-{digest[:6]}"


def band_for_leverage(leverage: float | None) -> str:
    """Debt/Assets -> rating band. `None` (no Assets data) falls to the
    weakest band rather than the strongest -- an unmeasured obligor should
    never look artificially safe."""
    if leverage is None:
        return DEFAULT_BAND
    for cutoff, band in BAND_THRESHOLDS:
        if leverage <= cutoff:
            return band
    return DEFAULT_BAND


def add_years(d: date, years: float) -> date:
    return d + timedelta(days=round(years * 365.25))


#: The actual ceiling DATE, derived from WINDOW_START + MATURITY_CEILING_YEARS
#: via the same day-rounding arithmetic used everywhere else in this module
#: (never a separate ad hoc computation that could disagree with it).
MATURITY_CEILING = add_years(WINDOW_START, MATURITY_CEILING_YEARS)


def eligible_tenors(issue_date: date, floor: date, ceiling: date,
                     ladder: list[int]) -> list[int]:
    """Ladder tenors filtered to a maturity window: not before `floor` (the
    instrument must still be alive when the market data starts mattering)
    and not after `ceiling` (the instrument must stay inside the benchmark
    curve's tenor range for the whole observation window, not just at
    issuance). Both bounds are checked as actual dates via `add_years`, never
    as a plain year-count comparison, which would drift under leap years at
    this scale.

    Falls back to the narrowest single tenor that clears the floor, clipped
    to the ceiling, when no ladder rung fits either bound (no obligor in
    this run needs it, but a future, unusually old or unusually recent
    anchor filing could)."""
    filtered = [t for t in ladder
                if floor <= add_years(issue_date, t) <= ceiling]
    if filtered:
        return filtered
    required_years = max(0.0, (floor - issue_date).days / 365.25)
    ceiling_years = max(0.0, (ceiling - issue_date).days / 365.25)
    return [min(math.ceil(required_years), math.floor(ceiling_years))]


# --------------------------------------------------------------------------
# Postgres reads (read-only; no writes in this task)
# --------------------------------------------------------------------------

def latest_by_tag(cur, tags: list[str]) -> dict[tuple[str, str], dict]:
    """Most-recent fact per (lei, tag): highest period_end, tied by
    filed_date, tied by accession. Explicit ORDER BY -- the first row seen
    per key wins, so row order is load-bearing."""
    cur.execute(
        f'''SELECT lei, tag, value, period_end, filed_date, accession
            FROM "{PG_SCHEMA_V2}".financial_fact
            WHERE tag = ANY(%s)
            ORDER BY lei, tag, period_end DESC, filed_date DESC,
                     accession DESC''',
        (tags,))
    latest: dict[tuple[str, str], dict] = {}
    for lei, tag, value, period_end, filed_date, accession in cur.fetchall():
        key = (lei, tag)
        if key not in latest:
            latest[key] = {
                "value": float(value), "period_end": period_end.isoformat(),
                "filed_date": filed_date.isoformat(), "accession": accession,
            }
    return latest


def resolve_by_priority(latest: dict[tuple[str, str], dict],
                         tag_priority: list[str]) -> dict[str, dict]:
    """Priority-resolve a set of tags to one value per lei. `tag_priority`
    must be the SAME list the caller queried `latest_by_tag` with, or every
    lookup silently misses -- this bit once already (Assets queried with one
    tag, resolved against the debt tag list) and is exactly the "dict.get()
    default masking a wrong field name" trap this project keeps hitting."""
    leis = sorted({lei for lei, _ in latest})
    out: dict[str, dict] = {}
    for lei in leis:
        for tag in tag_priority:
            if (lei, tag) in latest:
                out[lei] = {"tag": tag, **latest[(lei, tag)]}
                break
    return out


def fetch_eligible_leis(cur) -> set[str]:
    """Obligors with >= 1 Item 2.03 filing, per the canonical public count in
    filing_profile (not re-derived from the issuance JSON, though the two
    agree on this run)."""
    cur.execute(
        f'''SELECT lei, count_8k_item_2_03
            FROM "{PG_SCHEMA_V2}".filing_profile
            ORDER BY lei''')
    return {lei for lei, count in cur.fetchall() if count >= 1}


def fetch_legal_names(cur) -> dict[str, str]:
    cur.execute(
        f'''SELECT lei, legal_name FROM "{PG_SCHEMA_V2}".legal_entity
            WHERE is_anchor ORDER BY lei''')
    return dict(cur.fetchall())


# --------------------------------------------------------------------------
# Selection and generation
# --------------------------------------------------------------------------

def select_obligors(cur, force_leis: set[str]) -> tuple[list[dict], list[str]]:
    """Returns (obligor records ordered debt-rank-first, notes)."""
    notes: list[str] = []

    debt_latest = latest_by_tag(cur, DEBT_TAGS)
    assets_latest = latest_by_tag(cur, ["Assets"])
    debt = resolve_by_priority(debt_latest, DEBT_TAGS)
    assets = resolve_by_priority(assets_latest, ["Assets"])
    eligible_leis = fetch_eligible_leis(cur)

    cross_check_gap = {lei for lei in debt if lei not in eligible_leis}
    if cross_check_gap:
        notes.append(
            f"NOTE: {len(cross_check_gap)} obligor(s) with reported debt "
            f"lack an Item 2.03 filing per filing_profile and were excluded "
            f"from ranking: {sorted(cross_check_gap)}")

    eligible = {lei: v for lei, v in debt.items() if lei in eligible_leis}
    ranked = sorted(eligible.items(), key=lambda kv: (-kv[1]["value"], kv[0]))
    ranked_leis = [lei for lei, _ in ranked]
    rank_of = {lei: i + 1 for i, lei in enumerate(ranked_leis)}

    top = ranked_leis[:OBLIGOR_COUNT]
    top_set = set(top)

    forced_new = sorted(force_leis - top_set)
    notes.append(
        f"force-include check: {len(force_leis)} confirmed rating-action "
        f"anchor(s) read from wave11a_rating_actions.json; "
        f"{len(force_leis) - len(forced_new)} already inside the top "
        f"{OBLIGOR_COUNT} by debt rank, {len(forced_new)} added purely by "
        f"force-inclusion")

    selected_leis = top_set | force_leis
    # Stable, meaningful order: debt rank where known, force-included-but-
    # unranked obligors (none this run) sorted last by LEI.
    ordered = sorted(
        selected_leis,
        key=lambda lei: (rank_of.get(lei, len(ranked_leis) + 1), lei))

    obligors: list[dict] = []
    for lei in ordered:
        d = debt.get(lei)
        a = assets.get(lei)
        leverage = (d["value"] / a["value"]
                    if d and a and a["value"] else None)
        if d is None:
            notes.append(f"NOTE: force-included obligor {lei} has no "
                          f"reported LongTermDebt-family value at all")
        if a is None:
            notes.append(f"NOTE: obligor {lei} has no reported Assets value; "
                          f"rating band defaults to {DEFAULT_BAND}")
        obligors.append({
            "lei": lei,
            "debt_rank": rank_of.get(lei),
            "force_included": lei in force_leis,
            "force_included_beyond_rank": lei in forced_new,
            "debt_usd": d["value"] if d else None,
            "debt_tag": d["tag"] if d else None,
            "debt_period_end": d["period_end"] if d else None,
            "assets_usd": a["value"] if a else None,
            "leverage_debt_over_assets": (round(leverage, 4)
                                           if leverage is not None else None),
            "rating_band": band_for_leverage(leverage),
        })
    return obligors, notes


def build_instruments(obligors: list[dict],
                       filings_by_lei: dict[str, list[dict]],
                       rng: Random) -> list[dict]:
    instruments: list[dict] = []
    anchored = 0
    unanchored = 0

    for obligor in obligors:
        lei = obligor["lei"]
        band = obligor["rating_band"]
        # Most-recent filing first, tied by accession descending -- the
        # ordering the two instruments draw from is fixed, not incidental.
        filings = sorted(filings_by_lei.get(lei, []),
                          key=lambda f: (f["file_date"], f["accession"]),
                          reverse=True)

        for seq in range(INSTRUMENTS_PER_OBLIGOR):
            anchor = filings[seq] if seq < len(filings) else (
                filings[-1] if filings else None)
            if anchor is not None:
                issue_date = date.fromisoformat(anchor["file_date"])
                anchored += 1
            else:
                # No obligor in this run reaches this branch (all 30
                # selected obligors have >= 1 Item 2.03 filing), but a
                # future refresh that force-includes a filing-less anchor
                # must not fail silently -- fall back to a fixed date and
                # say so plainly rather than reading the clock.
                issue_date = date(2024, 1, 1)
                unanchored += 1

            tenor_options = eligible_tenors(issue_date, WINDOW_FLOOR,
                                             MATURITY_CEILING, TENOR_LADDER)
            tenor_years = rng.choice(sorted(tenor_options))
            maturity = add_years(issue_date, tenor_years)

            coupon = (BASE_COUPON_PCT[band]
                      + tenor_years * TERM_PREMIUM_PCT_PER_YEAR
                      + rng.uniform(-COUPON_JITTER_PCT, COUPON_JITTER_PCT))
            face_amount = rng.choice(FACE_LADDER_USD)
            seniority = rng.choices(SENIORITY_CHOICES,
                                     weights=SENIORITY_WEIGHTS, k=1)[0]

            instruments.append({
                "instrument_id": mint_instrument_id(SEED, lei, seq),
                "lei": lei,
                "coupon_pct": round(coupon, 2),
                "maturity": maturity.isoformat(),
                "issue_date": issue_date.isoformat(),
                "face_amount_usd": face_amount,
                "rating_band": band,
                "seniority": seniority,
                "tenor_years": tenor_years,
                "anchored_to_real_filing": anchor is not None,
                "anchor_accession": anchor["accession"] if anchor else None,
                "provenance": PROVENANCE,
                "provenance_note": (
                    "issue_date anchored to a real Item 2.03 filing date; "
                    "the instrument itself is invented"
                    if anchor is not None else
                    "no Item 2.03 filing was available to anchor this "
                    "instrument's issue_date; a fixed placeholder date was "
                    "used instead"),
            })

    return instruments


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rating_actions = json.loads(
        (SCREEN / "wave11a_rating_actions.json").read_text())
    force_leis = {r["lei"] for r in rating_actions["rating_actions"]
                  if r.get("confirmed")}

    issuance = json.loads((SCREEN / "wave11a_issuance.json").read_text())
    filings_by_lei: dict[str, list[dict]] = defaultdict(list)
    for row in issuance["issuance"]:
        filings_by_lei[row["lei"]].append(row)

    with pg_connect() as conn, conn.cursor() as cur:
        obligors, selection_notes = select_obligors(cur, force_leis)
        legal_names = fetch_legal_names(cur)

    rng = Random(SEED)
    instruments = build_instruments(obligors, filings_by_lei, rng)

    ids = [i["instrument_id"] for i in instruments]
    if len(set(ids)) != len(ids):
        dupes = {x for x in ids if ids.count(x) > 1}
        raise RuntimeError(f"instrument_id collision: {dupes}")

    # This design note is ALWAYS present, not conditional -- a future reader
    # extending TENOR_LADDER or MATURITY_CEILING_YEARS needs to see why the
    # bound exists even on a clean run with nothing else to report.
    selection_notes = [
        f"maturities are bounded to [{WINDOW_FLOOR.isoformat()}, "
        f"{MATURITY_CEILING.isoformat()}] BY DESIGN: the benchmark curve "
        f"(Treasury par yield) tops out at a 30 Yr tenor, and the "
        f"observation window runs {WINDOW_START.isoformat()} -> "
        f"2026-08-18. A maturity outside this range would carry zero "
        f"spread observations for part or all of its life -- do not widen "
        f"TENOR_LADDER or MATURITY_CEILING_YEARS without re-checking that "
        f"every instrument stays priceable across the WHOLE window, not "
        f"just at issuance.",
    ] + selection_notes
    years_from_window_start = [
        (date.fromisoformat(i["maturity"]) - WINDOW_START).days / 365.25
        for i in instruments
    ]
    beyond_ceiling = sum(1 for y in years_from_window_start
                          if y > MATURITY_CEILING_YEARS + 1e-9)
    before_floor = sum(1 for i in instruments
                        if date.fromisoformat(i["maturity"]) < WINDOW_FLOOR)

    band_counts: dict[str, int] = defaultdict(int)
    for i in instruments:
        band_counts[i["rating_band"]] += 1
    tenor_counts: dict[int, int] = defaultdict(int)
    for i in instruments:
        tenor_counts[i["tenor_years"]] += 1
    anchored_count = sum(1 for i in instruments if i["anchored_to_real_filing"])

    print("Wave 11a Task 4 — instrument set\n")
    print(f"  obligors selected      {len(obligors)} "
          f"(target {OBLIGOR_COUNT})")
    print(f"  force-included anchors {len(force_leis)} confirmed, "
          f"{sum(o['force_included_beyond_rank'] for o in obligors)} "
          f"added beyond debt rank")
    print(f"  instruments generated  {len(instruments)} "
          f"(target {OBLIGOR_COUNT * INSTRUMENTS_PER_OBLIGOR})")
    print(f"  anchored to a real Item 2.03 filing  {anchored_count}/"
          f"{len(instruments)}")
    print(f"  rating band distribution  "
          + ", ".join(f"{b}={band_counts.get(b, 0)}"
                       for b in ["AA", "A", "BBB", "BB", "B"]))
    print(f"  tenor ladder used  "
          + ", ".join(f"{t}y={tenor_counts.get(t, 0)}"
                       for t in TENOR_LADDER if tenor_counts.get(t, 0)))
    if instruments:
        maturities = sorted(i["maturity"] for i in instruments)
        print(f"  maturity range  {maturities[0]} -> {maturities[-1]}")
        print(f"  years from window start ({WINDOW_START.isoformat()})  "
              f"min={min(years_from_window_start):.1f}  "
              f"max={max(years_from_window_start):.1f}  "
              f"(ceiling {MATURITY_CEILING_YEARS})")

    if selection_notes:
        print("\n  selection notes:")
        for n in selection_notes:
            print(f"    {n}")

    print("\n  §F conditions")
    checks = [
        ("~30 obligors with publicly traded debt", len(obligors), 25),
        ("~60 instruments, laddered", len(instruments), 55),
        (">= 1 obligor with a real 8-K rating action",
         sum(o["force_included"] for o in obligors), 1),
        ("rating bands actually discriminate (>=3 distinct bands present)",
         sum(1 for c in band_counts.values() if c > 0), 3),
    ]
    short = 0
    for label, actual, floor in checks:
        ok = actual >= floor
        short += not ok
        print(f"    [{'ok  ' if ok else 'FAIL'}] {label:<55} {actual} / {floor}")

    # Zero-tolerance checks, not floors -- either of these firing means an
    # instrument is unpriceable for part of the observation window.
    for label, count in [
        ("zero instruments maturing beyond the curve's priceable range",
         beyond_ceiling),
        (f"zero instruments maturing before {WINDOW_FLOOR.isoformat()} "
         f"(margin past the 2026-08-18 window end)", before_floor),
    ]:
        ok = count == 0
        short += not ok
        print(f"    [{'ok  ' if ok else 'FAIL'}] {label:<55} {count} / 0")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 1 if short else 0

    payload = {
        "wave": "11a",
        "task": 4,
        "seed": SEED,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_for": "rating-and-spread-migration",
        "selection_method": (
            "30 largest by most-recent reported LongTermDebt-family value "
            "in ccf_v2.financial_fact, restricted to obligors with >= 1 "
            "Item 2.03 filing per ccf_v2.filing_profile; ties broken by LEI "
            "ascending; confirmed rating-action anchors force-included "
            "regardless of rank"),
        "rating_band_rule": (
            "Debt/Assets leverage over fixed thresholds: <=0.15 AA, "
            "<=0.30 A, <=0.50 BBB, <=0.70 BB, else B (also B if Assets is "
            "unreported)"),
        # Two different provenance classes live in this one file and must
        # not blur into a single top-level label: WHICH obligors were
        # selected is a public fact (a deterministic ranking over public
        # XBRL and public 8-K filing counts); the instruments those
        # obligors supposedly issued are invented. An anchor filing date
        # makes an issuance EVENT public -- it does not make the bond real.
        "obligor_selection_provenance": "public",
        "instrument_provenance": PROVENANCE,
        "obligors": [
            {**o, "legal_name": legal_names.get(o["lei"])}
            for o in obligors
        ],
        "instruments": instruments,
        "notes": selection_notes,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    out = SCREEN / "wave11a_instruments.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")

    return 1 if short else 0


if __name__ == "__main__":
    sys.exit(main())
