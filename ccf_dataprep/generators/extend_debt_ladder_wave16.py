#!/usr/bin/env python3
"""Wave 16 Task 8b — extend the debt maturity ladder from 30 to 48 obligors.

`ib-opportunity-synthesis`'s §C Data Catalog names a "Debt maturity ladder"
element (public provenance, Postgres, class `E`). Wave 11a's
`generate_instruments.py` already builds one, but `OBLIGOR_COUNT = 30` there
is a **scope choice for `rating-and-spread-migration`**, not an eligibility
ceiling: all 50 anchors carry an Item 2.03 filing. Because only 30 of 50
anchors carry any `debt_instrument` row, two-fifths of the prospect set has
no DCM signal to rank on at all, and the product's central demonstration (the
same signals rank differently for an M&A originator than a DCM banker) is not
satisfiable while that gap exists. This module fills it -- it does not touch
the 30 rows Wave 11a already wrote.

## The discipline this module must not blur

Straight from `generate_instruments.py`'s own docstring, and just as true
here: **the instruments are invented, the issuance events are not.** Every
instrument's `issue_date` is anchored to a real Item 2.03 ("Creation of a
Direct Financial Obligation") 8-K filing date for that obligor, drawn from
`sources/screening/wave11a_issuance.json` -- the same artifact
`generate_instruments.py` reads, and a strictly BETTER source for this than
`wave11b_8k_events.json` (measured: `wave11a_issuance.json` covers all 50
anchors with an Item 2.03 accession + date; `wave11b_8k_events.json`'s
`item == '2.03'` rows cover only 42, missing 5 of the 18 obligors this
module needs to anchor). Both are real EDGAR-derived Item 2.03 sweeps; this
one is just complete for this population and is already the file the sibling
module trusts for the same purpose. If an obligor has no usable event in it,
it is SKIPPED and reported -- never minted with a placeholder date.

## Eligibility

Of the 20 anchors with no `debt_instrument` row, **18 are eligible**: each
has >= 1 Item 2.03 filing AND a `LongTermDebt`-family XBRL fact
(`LongTermDebt` / `LongTermDebtNoncurrent` /
`DebtLongtermAndShorttermCombinedAmount` -- the same three-tag priority
`generate_instruments.py` uses, imported from there rather than re-declared).
**American Healthcare REIT, Inc.** and **SMITH & WESSON BRANDS, INC.** carry
NEITHER of the three tags and are excluded: `validators/conditions.py`
registers a `rating-and-spread-migration` condition that cross-checks
`debt_instrument` against `financial_fact` directly, and giving either of
these two an instrument would misrepresent what the public record supports.
Eligibility is RECOMPUTED against live Postgres on every run, never
hardcoded, so a future data refresh cannot silently drift out of sync with
this module's obligor list. One consequence: after a successful load, the
candidate set (anchors with NO `debt_instrument` row) is just the 2 excluded
obligors, so a re-run of THIS GENERATOR at that point correctly reports 0
obligors to add -- that is the gap being closed, not a bug. The loader's
idempotency (safe to re-run against the SAME generated artifact) is what
`validators/test_ib_rank.py` and this task's step 6 actually require; do not
re-run the generator to "prove" idempotency, since after a load it has
nothing left to regenerate by design.

## Namespace discipline

Every id here is prefixed `w16-i-`, never `syn-i-` -- that is Wave 11a's
namespace, and four loaders in this estate's history have silently rewritten
another wave's rows by assuming position. This module only ever INSERTs new
`w16-i-*` rows (the loader upserts on `instrument_id`, never deletes or
renumbers) and never reads, writes, or counts a `syn-i-*` row for any
purpose other than checking it is undisturbed.

## Laddering

Two instruments per obligor, anchored to the two most recent Item 2.03
filings (falling back to the same single filing twice, exactly as
`generate_instruments.py` does, for an obligor with only one):

  - **near** -- maturity inside 24 months of `AS_OF_IB` (2026-08-24), so
    there is an upcoming maturity wall to rank on. Floored at
    `generate_instruments.WINDOW_FLOOR` (2027-01-01), which is itself
    already comfortably inside that 24-month horizon: reusing it (rather
    than dating the near instrument any closer to `AS_OF_IB`) keeps every
    observation date in the priceable range of the benchmark curve, whose
    shortest tenor is 1 month -- a maturity much closer to the window's own
    end (2026-08-18) would push `years_to_maturity` below that floor for the
    final observation dates and silently drop them from the series.
  - **far** -- maturity well beyond the near instrument (target >= 5 years
    past `AS_OF_IB`, i.e. on or after 2031-08-24), drawn from
    `generate_instruments.TENOR_LADDER` and bounded by the same
    `MATURITY_CEILING` that module derives from the Treasury curve's 30 Yr
    limit. Falls back to the longest tenor the ceiling allows when no rung
    reaches the target.

## Spread observations

Composed the same way `generate_spreads.py` composes them for the original
60 -- `benchmark_bp` from the real Treasury par curve (`load_curve`),
`market_oas_bp` from the real FRED ICE BofA OAS series for the instrument's
rating band (`load_oas`), both re-imported rather than re-fetched or
re-parsed. `idiosyncratic_bp` is the only invented leg: a fixed
per-instrument baseline (`idiosyncratic_baseline_bp`, also imported) plus a
mean-reverting AR(1) day-to-day wiggle, exactly as the original instruments
carry it. What is NEW here is the trajectory: each instrument's idiosyncratic
leg is either flat (baseline + wiggle only) or WIDENING (a linear drift added
across the window, 15-45bp by the end), chosen per instrument by a dedicated
hash-seeded RNG so two runs agree bit for bit. Without this, every new
instrument's spread would carry the same shape and the DCM ranking would not
discriminate between them -- exactly the failure this task exists to fix,
arriving from a different angle. No rating migration, divergence window, or
observation gap is engineered for these instruments: those are
`rating-and-spread-migration`'s specific §F conditions, registered against
the original 60, and are not this task's to extend.

No FIBO term work: this element is Postgres-only structured data (`E`), not
graph state, and reuses `debt_instrument` / `spread_observation`'s existing
columns unchanged.

    uv run generators/extend_debt_ladder_wave16.py --dry-run
    uv run generators/extend_debt_ladder_wave16.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from random import Random

from ccf.config import AS_OF_IB, PG_SCHEMA_V2, REPO_ROOT, pg_connect
from generators.generate_instruments import (
    BASE_COUPON_PCT,
    COUPON_JITTER_PCT,
    DEBT_TAGS,
    FACE_LADDER_USD,
    MATURITY_CEILING,
    SENIORITY_CHOICES,
    SENIORITY_WEIGHTS,
    TENOR_LADDER,
    TERM_PREMIUM_PCT_PER_YEAR,
    WINDOW_FLOOR,
    add_years,
    band_for_leverage,
    eligible_tenors,
    latest_by_tag,
    resolve_by_priority,
)
from generators.generate_spreads import (
    AR1_PHI,
    AR1_SIGMA_BP,
    WINDOW_END,
    WINDOW_START,
    compose_observation,
    idiosyncratic_baseline_bp,
    load_curve,
    load_oas,
    years_to_maturity,
)
from generators.curves import interpolate_tenor

SCREEN = REPO_ROOT / "sources" / "screening"

#: A DIFFERENT seed and a DIFFERENT id salt from generate_instruments.py's
#: SEED (20260817), so a collision between the two modules' digests is
#: structurally impossible, not merely unlikely.
SEED = 16
ID_SALT = "w16"
ID_PREFIX = "w16-i-"

PROVENANCE = "synthetic — engineered"
PROVENANCE_NOTE = (
    "instrument is invented; issue_date anchored to a real Item 2.03 filing "
    "date (Wave 16 extension of the Wave 11a debt ladder, "
    "generators/extend_debt_ladder_wave16.py)")

#: The near rung of the ladder. Lower bound reuses generate_instruments'
#: WINDOW_FLOOR rather than dating closer to AS_OF_IB -- see module docstring
#: for why that specific margin matters (the benchmark curve's shortest
#: tenor is 1 month).
NEAR_LOWER = WINDOW_FLOOR
NEAR_UPPER_MONTHS = 24

#: The far rung's target: comfortably beyond the near rung, not merely past
#: it. Five years past AS_OF_IB, not past NEAR_UPPER, so the two rungs read
#: as genuinely different horizons even for an obligor whose near rung lands
#: early in its own window.
FAR_TARGET_YEARS_PAST_AS_OF = 5

#: Idiosyncratic drift for a "widening" instrument, basis points added
#: linearly across the window. Kept well under BAND_BASELINE_BP's own
#: 12-40bp range (generate_spreads.py) so a widening instrument still reads
#: as a minority engineered contribution, just one that trends rather than
#: sitting flat.
DRIFT_RANGE_BP = (15.0, 45.0)
WIDEN_PROBABILITY = 0.5


def add_months(d: date, months: int) -> date:
    """Calendar-month arithmetic, not a day-count approximation -- so
    "24 months past AS_OF_IB" lands on the same day-of-month, matching how
    a banker would actually describe a maturity wall."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    return date(year, month, d.day)


AS_OF_IB_DATE = date.fromisoformat(AS_OF_IB)
NEAR_UPPER = add_months(AS_OF_IB_DATE, NEAR_UPPER_MONTHS)
FAR_TARGET = add_months(AS_OF_IB_DATE, FAR_TARGET_YEARS_PAST_AS_OF * 12)


# --------------------------------------------------------------------------
# Pure logic
# --------------------------------------------------------------------------

def mint_instrument_id(seed: int, salt: str, lei: str, sequence: int) -> str:
    """`w16-i-<6 hex>`, deterministic from (seed, salt, lei, sequence) via
    SHA-256 -- same shape as generate_instruments.mint_instrument_id, but
    salted separately so the two digests can never collide."""
    digest = hashlib.sha256(
        f"{seed}|{salt}|{lei}|{sequence}".encode()).hexdigest()
    return f"{ID_PREFIX}{digest[:6]}"


def instrument_rng(instrument_id: str) -> Random:
    """Dedicated per-instrument RNG, hash-seeded so the idiosyncratic series
    is independent of iteration order and reproduces bit for bit on rerun --
    same idiom as generate_spreads.instrument_rng, salted separately."""
    digest = hashlib.sha256(
        f"{SEED}|{ID_SALT}|idio|{instrument_id}".encode()).hexdigest()
    return Random(int(digest[:16], 16))


def near_maturity(rng: Random) -> date:
    """A date in [NEAR_LOWER, NEAR_UPPER], independent of `issue_date` (which
    is real and historical) -- `tenor_years` is derived FROM this maturity,
    not the other way around, so the target window is hit exactly rather
    than approximated by snapping to a fixed tenor ladder."""
    span_days = (NEAR_UPPER - NEAR_LOWER).days
    return NEAR_LOWER + timedelta(days=rng.randint(0, span_days))


def far_tenor_years(issue_date: date, rng: Random) -> int:
    """Pick a TENOR_LADDER rung whose resulting maturity clears FAR_TARGET
    where possible, filtered through the same (WINDOW_FLOOR, MATURITY_CEILING)
    bounds `generate_instruments.eligible_tenors` already enforces for
    curve-priceability. Falls back to the longest rung the ceiling allows
    when no rung reaches FAR_TARGET (an obligor whose sole/second anchor
    filing is old enough that even the 25y rung lands short of it)."""
    options = eligible_tenors(issue_date, WINDOW_FLOOR, MATURITY_CEILING,
                               TENOR_LADDER)
    beyond_target = [t for t in options
                      if add_years(issue_date, t) >= FAR_TARGET]
    pool = beyond_target if beyond_target else [max(options)]
    return rng.choice(sorted(pool))


# --------------------------------------------------------------------------
# Postgres reads
# --------------------------------------------------------------------------

def obligors_without_debt(cur) -> list[str]:
    cur.execute(f'SELECT DISTINCT lei FROM "{PG_SCHEMA_V2}".debt_instrument')
    has_debt = {lei.strip() for (lei,) in cur.fetchall()}
    cur.execute(f'''SELECT lei FROM "{PG_SCHEMA_V2}".legal_entity
                     WHERE is_anchor ORDER BY lei''')
    anchors = [lei.strip() for (lei,) in cur.fetchall()]
    return [lei for lei in anchors if lei not in has_debt]


def select_eligible(cur, candidate_leis: list[str]) -> tuple[list[dict], list[str]]:
    """Returns (eligible obligor records, notes). Eligibility is a
    LongTermDebt-family fact -- recomputed live, never hardcoded, so a
    future refresh cannot silently drift out of sync with this list."""
    notes: list[str] = []
    debt_latest = latest_by_tag(cur, DEBT_TAGS)
    assets_latest = latest_by_tag(cur, ["Assets"])
    debt = resolve_by_priority(debt_latest, DEBT_TAGS)
    assets = resolve_by_priority(assets_latest, ["Assets"])

    eligible: list[dict] = []
    excluded: list[str] = []
    for lei in candidate_leis:
        d = debt.get(lei)
        if d is None:
            excluded.append(lei)
            continue
        a = assets.get(lei)
        leverage = (d["value"] / a["value"] if a and a["value"] else None)
        eligible.append({
            "lei": lei,
            "debt_usd": d["value"],
            "debt_tag": d["tag"],
            "assets_usd": a["value"] if a else None,
            "leverage_debt_over_assets": (round(leverage, 4)
                                           if leverage is not None else None),
            "rating_band": band_for_leverage(leverage),
        })

    if excluded:
        notes.append(
            f"NOTE: {len(excluded)} obligor(s) without any debt row also "
            f"lack a LongTermDebt-family fact and are EXCLUDED from this "
            f"extension: {sorted(excluded)}")
    return eligible, notes


def fetch_legal_names(cur, leis: list[str]) -> dict[str, str]:
    cur.execute(
        f'''SELECT lei, legal_name FROM "{PG_SCHEMA_V2}".legal_entity
            WHERE lei = ANY(%s)''', (leis,))
    return {lei.strip(): name for lei, name in cur.fetchall()}


def load_filings_by_lei() -> dict[str, list[dict]]:
    issuance = json.loads((SCREEN / "wave11a_issuance.json").read_text())
    by_lei: dict[str, list[dict]] = defaultdict(list)
    for row in issuance["issuance"]:
        by_lei[row["lei"]].append(row)
    return by_lei


# --------------------------------------------------------------------------
# Instrument construction
# --------------------------------------------------------------------------

def build_instruments(obligors: list[dict],
                       filings_by_lei: dict[str, list[dict]],
                       rng: Random) -> tuple[list[dict], list[str]]:
    """Returns (instruments, skipped_leis). `skipped_leis` are eligible
    obligors with zero usable Item 2.03 events -- excluded entirely rather
    than minted with a placeholder date."""
    instruments: list[dict] = []
    skipped: list[str] = []

    for obligor in obligors:
        lei = obligor["lei"]
        band = obligor["rating_band"]
        filings = sorted(filings_by_lei.get(lei, []),
                          key=lambda f: (f["file_date"], f["accession"]),
                          reverse=True)
        if not filings:
            skipped.append(lei)
            continue

        anchors = [filings[0], filings[1] if len(filings) > 1 else filings[0]]

        for seq, anchor in enumerate(anchors):
            issue_date = date.fromisoformat(anchor["file_date"])
            if seq == 0:
                maturity = near_maturity(rng)
            else:
                tenor = far_tenor_years(issue_date, rng)
                maturity = add_years(issue_date, tenor)
            tenor_years = max(1, round((maturity - issue_date).days / 365.25))

            coupon = (BASE_COUPON_PCT[band]
                      + tenor_years * TERM_PREMIUM_PCT_PER_YEAR
                      + rng.uniform(-COUPON_JITTER_PCT, COUPON_JITTER_PCT))
            face_amount = rng.choice(FACE_LADDER_USD)
            seniority = rng.choices(SENIORITY_CHOICES,
                                     weights=SENIORITY_WEIGHTS, k=1)[0]

            instruments.append({
                "instrument_id": mint_instrument_id(SEED, ID_SALT, lei, seq),
                "lei": lei,
                "coupon_pct": round(coupon, 2),
                "maturity": maturity.isoformat(),
                "issue_date": issue_date.isoformat(),
                "face_amount_usd": face_amount,
                "rating_band": band,
                "seniority": seniority,
                "tenor_years": tenor_years,
                "anchored_to_real_filing": True,
                "anchor_accession": anchor["accession"],
                "provenance": PROVENANCE,
                "provenance_note": PROVENANCE_NOTE,
                "rung": "near" if seq == 0 else "far",
            })

    return instruments, skipped


def build_observations(instruments: list[dict]) -> list[dict]:
    """One observation series per instrument across [WINDOW_START,
    WINDOW_END], reusing the SAME real curve/OAS legs generate_spreads.py
    uses for the original 60. `idiosyncratic_bp` is baseline + AR(1) wiggle
    (+ a linear drift for a "widening" instrument) -- the only invented leg,
    matching the provenance split every existing row already carries."""
    curve = load_curve()
    oas = load_oas()
    window_days = (WINDOW_END - WINDOW_START).days

    observations: list[dict] = []
    skipped_no_benchmark = 0

    for inst in instruments:
        iid = inst["instrument_id"]
        band = inst["rating_band"]
        maturity = date.fromisoformat(inst["maturity"])
        rng = instrument_rng(iid)
        baseline = idiosyncratic_baseline_bp(band, inst["seniority"], rng)
        widening = rng.random() < WIDEN_PROBABILITY
        drift_total = rng.uniform(*DRIFT_RANGE_BP) if widening else 0.0
        inst["idiosyncratic_trajectory"] = "widening" if widening else "flat"
        ar1_state = 0.0

        for d, tenors in curve:
            ar1_state = AR1_PHI * ar1_state + rng.gauss(0.0, AR1_SIGMA_BP)
            years = years_to_maturity(d, maturity)
            benchmark_pct = interpolate_tenor(tenors, years)
            if benchmark_pct is None:
                skipped_no_benchmark += 1
                continue
            benchmark_bp = benchmark_pct * 100.0

            if band not in oas or d not in oas[band]:
                raise RuntimeError(
                    f"no OAS for band {band!r} on curve date {d}. Every "
                    "curve date in the window is present in every band's "
                    "series (measured by generate_spreads.py: 0 gaps across "
                    "all five bands) -- re-measure before weakening this.")
            market_oas_bp = oas[band][d]

            progress = (d - WINDOW_START).days / window_days if window_days else 0.0
            drift_bp = drift_total * max(0.0, min(1.0, progress))
            idiosyncratic_bp = baseline + ar1_state + drift_bp

            obs = compose_observation(benchmark_bp=benchmark_bp,
                                       market_oas_bp=market_oas_bp,
                                       idiosyncratic_bp=idiosyncratic_bp)
            assert obs is not None  # benchmark_pct already checked above

            observations.append({
                "instrument_id": iid,
                "obs_date": d.isoformat(),
                "years_to_maturity": round(years, 4),
                "benchmark_bp": round(obs["benchmark_bp"], 3),
                "market_oas_bp": obs["market_oas_bp"],
                "idiosyncratic_bp": round(obs["idiosyncratic_bp"], 3),
                "spread_bp": round(obs["spread_bp"], 3),
                "yield_bp": round(obs["yield_bp"], 3),
            })

    if skipped_no_benchmark:
        print(f"  [note] {skipped_no_benchmark} observation(s) skipped: "
              f"years_to_maturity fell outside the curve's priceable range")

    return observations


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rng = Random(SEED)

    with pg_connect() as conn, conn.cursor() as cur:
        candidates = obligors_without_debt(cur)
        obligors, notes = select_eligible(cur, candidates)
        legal_names = fetch_legal_names(cur, [o["lei"] for o in obligors])

    filings_by_lei = load_filings_by_lei()
    instruments, skipped_leis = build_instruments(obligors, filings_by_lei, rng)

    ids = [i["instrument_id"] for i in instruments]
    if len(set(ids)) != len(ids):
        dupes = {x for x in ids if ids.count(x) > 1}
        raise RuntimeError(f"instrument_id collision: {dupes}")

    print("Wave 16 Task 8b — extend the debt ladder\n")
    print(f"  anchors without any debt row     {len(candidates)}")
    print(f"  eligible (LongTermDebt-family)   {len(obligors)}")
    print(f"  skipped (no Item 2.03 event)     {len(skipped_leis)}"
          + (f"  {sorted(skipped_leis)}" if skipped_leis else ""))
    print(f"  instruments to add               {len(instruments)}")

    print(f"\n  {'lei':<22} {'legal_name':<38} {'band':<4} "
          f"{'near maturity':<14} {'far maturity':<14} traj(near/far)")
    by_lei: dict[str, list[dict]] = defaultdict(list)
    for i in instruments:
        by_lei[i["lei"]].append(i)
    for lei in sorted(by_lei):
        rows = sorted(by_lei[lei], key=lambda r: r["rung"])
        near = next((r for r in rows if r["rung"] == "near"), None)
        far = next((r for r in rows if r["rung"] == "far"), None)
        name = legal_names.get(lei, "?")[:38]
        band = (near or far)["rating_band"]
        print(f"  {lei:<22} {name:<38} {band:<4} "
              f"{near['maturity'] if near else '-':<14} "
              f"{far['maturity'] if far else '-':<14}")

    obligors_with_instruments = len(by_lei)
    if any(lei in skipped_leis for lei in by_lei):
        raise RuntimeError("internal error: a skipped LEI produced instruments")

    zero_instrument_eligible = [o["lei"] for o in obligors
                                 if o["lei"] not in by_lei
                                 and o["lei"] not in skipped_leis]
    short = 0
    if zero_instrument_eligible:
        short = 1
        print(f"\n  [FAIL] eligible obligor(s) produced zero instruments: "
              f"{sorted(zero_instrument_eligible)}")
    else:
        print(f"\n  [ok] every eligible, anchored obligor produced 2 instruments")

    if notes:
        print("\n  notes:")
        for n in notes:
            print(f"    {n}")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return short

    observations = build_observations(instruments)

    widening_count = sum(1 for i in instruments
                          if i["idiosyncratic_trajectory"] == "widening")
    print(f"\n  spread observations generated     {len(observations)}"
          f"  (target ~{len(instruments) * 499})")
    print(f"  instruments on a widening trajectory   {widening_count}/"
          f"{len(instruments)}")

    payload = {
        "wave": 16,
        "task": "8b",
        "seed": SEED,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_for": "ib-opportunity-synthesis",
        "id_prefix": ID_PREFIX,
        "selection_method": (
            "obligors from the 50-anchor cast with NO existing debt_instrument "
            "row, restricted to a LongTermDebt-family XBRL fact "
            "(LongTermDebt / LongTermDebtNoncurrent / "
            "DebtLongtermAndShorttermCombinedAmount); recomputed live against "
            "Postgres on every run, never hardcoded"),
        "ladder_method": (
            "2 instruments per obligor: 'near' matures inside "
            f"{NEAR_UPPER_MONTHS} months of AS_OF_IB ({AS_OF_IB}), 'far' "
            f"targets >= {FAR_TARGET_YEARS_PAST_AS_OF} years past AS_OF_IB, "
            "both anchored to a real Item 2.03 filing date"),
        "obligor_selection_provenance": "public",
        "instrument_provenance": PROVENANCE,
        "spread_provenance": {
            "benchmark_bp": "public",
            "market_oas_bp": "public",
            "idiosyncratic_bp": "synthetic — engineered",
            "spread_bp": "computed (public + engineered)",
            "yield_bp": "computed (public + public + engineered)",
        },
        "obligors": [
            {**o, "legal_name": legal_names.get(o["lei"])}
            for o in obligors
        ],
        "skipped_no_anchor": sorted(skipped_leis),
        "instruments": instruments,
        "observations": observations,
        "notes": notes,
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    out = SCREEN / "wave16_debt_ladder.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")

    return short


if __name__ == "__main__":
    sys.exit(main())
