#!/usr/bin/env python3
"""Wave 11a Task 5 — compose the spread series.

Per-CUSIP FINRA TRACE history is licensed and unreachable (`docs/wave11a-
design.md` §1.1), so the yield each instrument would print is **composed**
from three legs rather than fetched:

    benchmark_bp      = interpolate_tenor(curve[d], years_to_maturity(d)) * 100  [public]
    market_oas_bp     = oas[in_force_band(d)][d]                                [public, already bp]
    idiosyncratic_bp  = per-instrument baseline + AR(1) wiggle + engineered
                        divergence bump + engineered anticipation ramp ahead
                        of a rating-band migration                              [engineered]

    spread_bp = market_oas_bp + idiosyncratic_bp
    yield_bp  = benchmark_bp + spread_bp

`in_force_band(d)` steps to the obligor's new rating band exactly at
`asserted_at` -- the market leg follows the actual migration discovered from
the loaded grade chain, never pinned to the band the instrument had on the
day it was generated. The anticipation ahead of that step is carried
entirely by `idiosyncratic_bp`, scaled by the real, contemporaneous OAS gap
between the two bands, so a migration never blends two indices into one
column (`docs/wave11a-migration-transition-design.md` §§2-3).

The first two legs are the real 2024-2026 credit cycle: a genuine Treasury
par curve and a genuine FRED ICE BofA OAS index that moves because the market
moved, not because a curve was drawn for the demo. Only the third leg is
invented, and it must stay a minority contributor — §7 of the design doc
makes this measurable rather than asserted: outside an engineered divergence
window, median `|idiosyncratic_bp|` must be <= 40% of median `market_oas_bp`.
If the engineered leg dominates, the public index is decoration and the
product's central claim ("the market anticipates the grade") rests on
invented data after all. This script prints the actual ratio; it does not
assume it.

## Years-to-maturity is computed PER OBSERVATION DATE

An instrument's remaining life shrinks as the window advances. Matching
against a fixed tenor (e.g. computed once at issuance) would be the
calendar-proximity error §D forbids, arriving by a different route.

## Where `interpolate_tenor` returns None

No observation is recorded — never a carried-forward value, never an
extrapolation. Every instrument's maturity was bounded at generation time
(Task 4's `MATURITY_CEILING_YEARS`) specifically so this stays rare; a large
count here would mean that bound broke, not that the market was simply quiet.

## The two conditions counting cannot fake

**>= 3 divergence cases, >= 1 confirmed later.** A divergence is a window
where `idiosyncratic_bp` widens materially on one instrument while nothing
about the obligor's internal grade moves. The grade chain is already loaded
by the time this runs (`generate_grades.py` runs first -- see
`load_band_crossings` below) but the divergence bump is placed WITHOUT
consulting it: the windows are a fixed literal in `narrative_wave11a.py`,
independent of whatever the grade chain happens to hold. The migration ramp
elsewhere in this file is the part that reads the grade chain; divergence
placement deliberately does not. Recorded explicitly in `divergence_windows`
so Task 6 can place a confirming rerating and `validators/series.py`
(Task 9) can recompute the widening from the series itself rather than trust
this flag.

**>= 2 thinly-traded instruments with real observation gaps.** Chosen dates
are dropped entirely from the output for those instruments -- not
interpolated, not zeroed, simply absent -- because a validator that counts
observations would pass a fully interpolated series. `sparse_instruments`
records exactly which dates are missing and why.

    uv run generators/generate_spreads.py --dry-run
    uv run generators/generate_spreads.py
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import statistics
import sys
from datetime import date, datetime, timezone
from random import Random

from ccf.config import REPO_ROOT
from generators.curves import interpolate_tenor
from generators.generate_grades import BANDS_BEST_TO_WORST
from generators.narrative_wave11a import (DIVERGENCE_RAMP_FRACTION,
                                          DIVERGENCES,
                                          SEED,
                                          assign_profiles,
                                          band_of_grade,
                                          divergence_windows_for_artifact)

SCREEN = REPO_ROOT / "sources" / "screening"

WINDOW_START = date(2024, 8, 19)
WINDOW_END = date(2026, 8, 18)
DAY_COUNT = 365.25

# --------------------------------------------------------------------------
# The idiosyncratic leg -- engineered, and deliberately kept a minority
# contributor. Values are basis points, chosen against the ACTUAL median OAS
# per band over the window (measured 2026-08-19: AA 48, A 67, BBB 102,
# BB 176, B 301) so each band's baseline sits well under the 40% dominance
# ceiling even before per-instrument and daily variation are added.
# --------------------------------------------------------------------------
BAND_BASELINE_BP: dict[str, float] = {
    "AA": 12.0,
    "A": 16.0,
    "BBB": 20.0,
    "BB": 28.0,
    "B": 40.0,
}

#: A capital-structure tilt: subordinated paper trades wider than senior
#: secured for the same obligor and band, which is a real feature of credit
#: markets and costs nothing to model.
SENIORITY_PREMIUM_BP: dict[str, float] = {
    "senior secured": -5.0,
    "senior unsecured": 0.0,
    "subordinated": 8.0,
}

INSTRUMENT_OFFSET_RANGE_BP = (-4.0, 4.0)  # fixed per instrument, drawn once

#: Day-to-day idiosyncratic wiggle is a mean-reverting AR(1) walk, not iid
#: noise -- real instrument-specific spread drift is autocorrelated, not a
#: fresh coin flip every day. phi=0.90, sigma=1.5bp/day gives a stationary
#: standard deviation of sigma/sqrt(1-phi^2) ~= 3.4bp, a small wiggle next to
#: a 12-40bp baseline -- for the ~54 of 60 instruments that never carry a
#: migration ramp. For the 6 that do, `idiosyncratic_bp` near a crossing is
#: dominated by the ramp, not this wiggle, and can run well outside
#: 12-40bp -- measured minimum -92.7bp (an upgrade's ramp goes negative),
#: 247 of 29,885 rows negative (12 before this change, from AR(1) noise
#: alone). `spread_bp` itself never goes negative (measured minimum 43.3bp,
#: unchanged): the ramp only ever borrows from the idiosyncratic leg, and
#: market_oas_bp stays comfortably larger than the largest ramp.
AR1_PHI = 0.90
AR1_SIGMA_BP = 1.5

#: Sparse instruments: real, deliberate observation gaps. Distinct from every
#: instrument used in DIVERGENCES so the two conditions stay separately
#: legible. Two instruments, two gap episodes each, so "thinly-traded" reads
#: as recurring absence rather than a single missed print.
SPARSE_GAPS: dict[str, list[tuple[date, date]]] = {
    "syn-i-b1a701": [  # A, 2549001IGRCG4F0RLD36
        (date(2025, 1, 6), date(2025, 1, 24)),
        (date(2025, 9, 15), date(2025, 9, 26)),
    ],
    "syn-i-cca248": [  # B, 549300TRW1LZMDJZAQ78
        (date(2024, 12, 2), date(2024, 12, 20)),
        (date(2025, 6, 9), date(2025, 6, 20)),
        (date(2026, 2, 2), date(2026, 2, 10)),
    ],
}

DOMINANCE_CEILING = 0.40


# --------------------------------------------------------------------------
# Pure logic (kept import-testable, no I/O)
# --------------------------------------------------------------------------

def compose_observation(*, benchmark_bp: float | None, market_oas_bp: float,
                         idiosyncratic_bp: float) -> dict | None:
    """Assemble one observation from its three legs.

    A `None` benchmark (outside the curve's priceable range) yields **no
    observation at all** -- never a zero, which would be indistinguishable
    from a genuinely tight benchmark and would silently distort every
    downstream median.
    """
    if benchmark_bp is None:
        return None
    spread_bp = market_oas_bp + idiosyncratic_bp
    yield_bp = benchmark_bp + spread_bp
    return {
        "benchmark_bp": benchmark_bp,
        "market_oas_bp": market_oas_bp,
        "idiosyncratic_bp": idiosyncratic_bp,
        "spread_bp": spread_bp,
        "yield_bp": yield_bp,
    }


def dominance_ratio(observations: list[dict]) -> float:
    """median(|idiosyncratic_bp|) / median(market_oas_bp) over `observations`.

    Median, not mean, on both sides -- so a single engineered divergence
    observation that leaks into the pool cannot flip the ratio by itself.
    Callers wanting the "outside divergence windows" reading must pre-filter
    `observations` to exclude those dates before calling this.
    """
    if not observations:
        return 0.0
    idio = [abs(o["idiosyncratic_bp"]) for o in observations]
    mkt = [o["market_oas_bp"] for o in observations]
    market_median = statistics.median(mkt)
    if market_median == 0:
        idio_median = statistics.median(idio)
        return float("inf") if idio_median else 0.0
    return statistics.median(idio) / market_median


def divergence_weight(d: date, start: date, end: date,
                       ramp_fraction: float = DIVERGENCE_RAMP_FRACTION) -> float:
    """Trapezoid shape over [start, end]: ramps 0->1 over the first
    `ramp_fraction` of the window, holds at 1, ramps 1->0 over the last
    `ramp_fraction`. Zero outside the window. A plateau, not a step, so the
    widening is visible as a genuine build rather than an overnight jump --
    and it fades back to baseline by `end`, which is what lets a later
    confirming rerating read as the grade catching up to a market move that
    had already happened and passed, not as coincident with an ongoing spike.
    """
    total_days = (end - start).days
    if total_days <= 0:
        return 1.0 if d == start else 0.0
    pos = (d - start).days
    if pos < 0 or pos > total_days:
        return 0.0
    ramp_days = max(1, round(total_days * ramp_fraction))
    if pos < ramp_days:
        return pos / ramp_days
    if pos > total_days - ramp_days:
        return (total_days - pos) / ramp_days
    return 1.0


def ramp_start_index(m_idx: int, lead_obs: int, floor_idx: int) -> int:
    """First observation index of the anticipation ramp for a migration at
    `m_idx`, clipped at `floor_idx`.

    `floor_idx` is whichever comes later: the start of the window, or the
    obligor's PREVIOUS migration. Anticipation cannot begin before the
    announcement it follows -- an obligor that crosses twice would otherwise
    have the second ramp running while the first was still being priced.
    """
    return max(floor_idx, m_idx - lead_obs)


def migration_ramp_weight(idx: int, start_idx: int, m_idx: int) -> float:
    """Linear 0 -> 1 across [start_idx, m_idx), and 0 from m_idx onward.

    Zero AT the migration, not 1: the anticipation is CONSUMED by the
    announcement. That is what leaves the composed spread with a residual
    jump of (1 - alpha) * gap rather than a full one.

    Linear, matching `divergence_weight`'s ramps -- one ramp idiom per file.
    An accelerating profile is arguably more faithful to how anticipation
    builds, but adds a shape parameter with nothing real to validate against.
    """
    span = m_idx - start_idx
    if span <= 0 or idx < start_idx or idx >= m_idx:
        return 0.0
    return (idx - start_idx) / span


def instrument_rng(instrument_id: str) -> Random:
    """Dedicated RNG per instrument, seeded from (SEED, instrument_id) via
    SHA-256. Deterministic independent of iteration order: two instruments'
    draws never interleave or depend on which one is processed first, and a
    re-run over the same instrument set reproduces the same idiosyncratic
    series bit for bit."""
    digest = hashlib.sha256(f"{SEED}|idio|{instrument_id}".encode()).hexdigest()
    return Random(int(digest[:16], 16))


def idiosyncratic_baseline_bp(band: str, seniority: str, rng: Random) -> float:
    """Fixed per-instrument level: band baseline + seniority tilt + a small
    per-instrument draw. Computed once per instrument, not per date."""
    offset = rng.uniform(*INSTRUMENT_OFFSET_RANGE_BP)
    return BAND_BASELINE_BP[band] + SENIORITY_PREMIUM_BP.get(seniority, 0.0) + offset


def years_to_maturity(obs_date: date, maturity: date) -> float:
    return (maturity - obs_date).days / DAY_COUNT


# `band_of_grade` is imported from `narrative_wave11a` above -- single
# source shared with `generate_grades.py` and `validators/series.py`.


def crossings_from_chain(chain: list[dict]) -> list[dict]:
    """Band crossings in one obligor's grade chain, in asserted_at order.

    Keyed on `asserted_at`, NOT `valid_from`: the market cannot price what it
    has not been told. The 1-5 day booking lag between the two therefore
    stays visible in the series as a window where the grade is already in
    force and the market leg has not yet stepped -- a free illustration of
    the bitemporal distinction this estate exists to teach.
    """
    rows = sorted(chain, key=lambda a: a["asserted_at"])
    out: list[dict] = []
    for prev, cur in zip(rows, rows[1:]):
        f, t = band_of_grade(prev["grade"]), band_of_grade(cur["grade"])
        if f != t:
            out.append({"asserted_at": date.fromisoformat(cur["asserted_at"]),
                        "from_band": f, "to_band": t})
    return out


# --------------------------------------------------------------------------
# I/O and assembly
# --------------------------------------------------------------------------

def load_curve() -> list[tuple[date, dict[float, float]]]:
    """Curve dates restricted to [WINDOW_START, WINDOW_END], sorted, with
    each date's tenor keys parsed from stringified years to float -- the
    curve file's tenor keys are ALREADY years ("10.000000"), not the
    Treasury column labels `curves.TENORS` maps, so no `tenor_years()` call
    belongs here."""
    payload = json.loads((SCREEN / "wave11a_curve.json").read_text())
    out: list[tuple[date, dict[float, float]]] = []
    for row in payload["curve"]:
        d = date.fromisoformat(row["date"])
        if WINDOW_START <= d <= WINDOW_END:
            tenors = {float(k): v for k, v in row["tenors"].items()}
            out.append((d, tenors))
    out.sort(key=lambda dt: dt[0])
    return out


def load_oas() -> dict[str, dict[date, float]]:
    """{band: {date: oas_bp}}. `oas_bp` is already basis points -- FRED
    serves percent and Task 2 converted once. Do NOT multiply by 100 here;
    that would be the exact contradiction the task brief calls out and
    corrects."""
    payload = json.loads((SCREEN / "wave11a_oas.json").read_text())
    out: dict[str, dict[date, float]] = {}
    for band, series in payload["series"].items():
        out[band] = {date.fromisoformat(p["date"]): p["oas_bp"]
                      for p in series["points"]}
    return out


def load_instruments() -> list[dict]:
    payload = json.loads((SCREEN / "wave11a_instruments.json").read_text())
    return sorted(payload["instruments"], key=lambda i: i["instrument_id"])


def load_band_crossings() -> dict[str, list[dict]]:
    """{lei: [crossing, ...]} from the grade chains. Only LEIs that cross."""
    path = SCREEN / "wave11a_grades.json"
    if not path.exists():
        raise RuntimeError(
            "wave11a_grades.json is absent. Since the migration-transition "
            "change, generate_spreads.py runs AFTER generate_grades.py -- run "
            "generators/generate_grades.py first. (See "
            "docs/wave11a-migration-transition-design.md section 4.)")
    by_lei: dict[str, list[dict]] = {}
    for a in json.loads(path.read_text())["assertions"]:
        by_lei.setdefault(a["lei"], []).append(a)
    out = {lei: crossings_from_chain(chain) for lei, chain in by_lei.items()}
    return {lei: c for lei, c in out.items() if c}


def in_gap(d: date, gaps: list[tuple[date, date]]) -> bool:
    return any(start <= d <= end for start, end in gaps)


def build_observations(
    instruments: list[dict],
    curve: list[tuple[date, dict[float, float]]],
    oas: dict[str, dict[date, float]],
) -> tuple[list[dict], list[dict], dict[str, int], list[dict]]:
    """Returns (observations, skipped_no_benchmark, gap_counts,
    migration_transitions).

    `curve` drives the date loop, never `oas`: every curve date inside the
    window is present in every band's OAS series (measured: 0 gaps across
    all five bands), so driving by curve dates can never manufacture a
    missing-OAS case that would be indistinguishable from a genuine gap.

    `market_oas_bp` follows the obligor's IN-FORCE rating band, stepping at
    `asserted_at`, rather than staying pinned to the band the instrument had
    on day one. An engineered anticipation ramp -- scaled by the real gap
    between the two bands' OAS indices -- is added to `idiosyncratic_bp`
    ahead of the step, so provenance never blends within a column:
    `market_oas_bp` stays public, `idiosyncratic_bp` stays engineered.

    `migration_transitions` records one entry per crossing actually applied
    (i.e. not dropped for announcing after the window), independent of how
    many instruments share the obligor's LEI, so a validator that derives
    its LEI set independently from Fluree can cross-check it against what
    this generator actually used.
    """
    observations: list[dict] = []
    skipped: list[dict] = []
    gap_counts: dict[str, int] = {iid: 0 for iid in SPARSE_GAPS}
    migration_transitions: dict[tuple[str, str], dict] = {}

    divergence_by_instrument: dict[str, dict] = {
        dv["instrument_id"]: dv for dv in DIVERGENCES}

    crossings_by_lei = load_band_crossings()
    profile_by_lei = assign_profiles(sorted(crossings_by_lei))
    dates = [d for d, _ in curve]                     # ordered observation dates
    index_of = {d: i for i, d in enumerate(dates)}

    for inst in instruments:
        iid = inst["instrument_id"]
        band = inst["rating_band"]
        maturity = date.fromisoformat(inst["maturity"])
        rng = instrument_rng(iid)
        baseline = idiosyncratic_baseline_bp(band, inst["seniority"], rng)
        gaps = SPARSE_GAPS.get(iid, [])
        divergence = divergence_by_instrument.get(iid)
        ar1_state = 0.0

        lei = inst["lei"]
        schedule: list[dict] = []
        floor_idx = 0
        for x in crossings_by_lei.get(lei, []):
            # bisect, because asserted_at may fall on a non-observation day
            m_idx = bisect.bisect_left(dates, x["asserted_at"])
            if m_idx >= len(dates):
                continue                              # announced after the window
            prof = profile_by_lei[lei]
            start_idx = ramp_start_index(m_idx, prof["lead_obs"], floor_idx)
            schedule.append({
                "m_idx": m_idx,
                "start_idx": start_idx,
                "from_band": x["from_band"],
                "to_band": x["to_band"],
                "anticipation": prof["anticipation"],
            })
            floor_idx = m_idx        # the next ramp cannot precede this one

            key = (lei, x["asserted_at"].isoformat())
            if key not in migration_transitions:
                migration_transitions[key] = {
                    "lei": lei,
                    "asserted_at": x["asserted_at"].isoformat(),
                    "from_band": x["from_band"],
                    "to_band": x["to_band"],
                    "anticipation": prof["anticipation"],
                    "lead_obs": prof["lead_obs"],
                    "ramp_start_date": dates[start_idx].isoformat(),
                }

        for s in schedule:
            wanted = profile_by_lei[lei]["lead_obs"]
            actual = s["m_idx"] - s["start_idx"]
            if actual < wanted:
                print(f"    [note] {iid} {lei}: ramp truncated "
                      f"{wanted} -> {actual} observation dates "
                      f"(window start or a prior migration)")

        for d, tenors in curve:
            if in_gap(d, gaps):
                gap_counts[iid] += 1
                continue

            ar1_state = AR1_PHI * ar1_state + rng.gauss(0.0, AR1_SIGMA_BP)

            years = years_to_maturity(d, maturity)
            benchmark_pct = interpolate_tenor(tenors, years)
            if benchmark_pct is None:
                skipped.append({
                    "instrument_id": iid, "obs_date": d.isoformat(),
                    "years_to_maturity": round(years, 4),
                })
                continue
            benchmark_bp = benchmark_pct * 100.0

            bump = 0.0
            if divergence is not None:
                bump = divergence["peak_bp"] * divergence_weight(
                    d, divergence["start"], divergence["end"])

            idx = index_of[d]
            in_force = band
            for s in schedule:
                if idx >= s["m_idx"]:
                    in_force = s["to_band"]

            if in_force not in oas or d not in oas[in_force]:
                raise RuntimeError(
                    f"no OAS for band {in_force} on curve date {d}. "
                    "build_observations' invariant is that every curve date "
                    "in the window is present in every band's series "
                    "(measured: 0 gaps across all five bands). Re-measure "
                    "before weakening this.")
            market_oas_bp = oas[in_force][d]

            anticipation_bp = 0.0
            for s in schedule:
                w = migration_ramp_weight(idx, s["start_idx"], s["m_idx"])
                if w:
                    to_b, from_b = s["to_band"], s["from_band"]
                    if (to_b not in oas or d not in oas[to_b]
                            or from_b not in oas or d not in oas[from_b]):
                        raise RuntimeError(
                            f"no OAS for band {from_b!r} or {to_b!r} on "
                            f"curve date {d}. build_observations' invariant "
                            "is that every curve date in the window is "
                            "present in every band's series (measured: 0 "
                            "gaps across all five bands). Re-measure before "
                            "weakening this.")
                    gap = oas[to_b][d] - oas[from_b][d]
                    anticipation_bp += s["anticipation"] * gap * w

            idiosyncratic_bp = baseline + ar1_state + bump + anticipation_bp

            obs = compose_observation(
                benchmark_bp=benchmark_bp, market_oas_bp=market_oas_bp,
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

    migration_transitions_list = sorted(
        migration_transitions.values(),
        key=lambda m: (m["asserted_at"], m["lei"]))

    return observations, skipped, gap_counts, migration_transitions_list


def in_any_divergence_window(instrument_id: str, obs_date: date) -> bool:
    dv = next((d for d in DIVERGENCES if d["instrument_id"] == instrument_id),
              None)
    return dv is not None and dv["start"] <= obs_date <= dv["end"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    curve = load_curve()
    oas = load_oas()
    instruments = load_instruments()

    if not curve:
        print("FATAL: no curve dates fall inside the observation window",
              file=sys.stderr)
        return 1

    observations, skipped, gap_counts, migration_transitions = build_observations(
        instruments, curve, oas)

    # Determinism guard: no duplicate (instrument, date) pairs.
    keys = [(o["instrument_id"], o["obs_date"]) for o in observations]
    if len(set(keys)) != len(keys):
        dupes = {k for k in keys if keys.count(k) > 1}
        raise RuntimeError(f"duplicate observation keys: {sorted(dupes)[:5]}")

    outside = [
        o for o in observations
        if not in_any_divergence_window(o["instrument_id"],
                                         date.fromisoformat(o["obs_date"]))
    ]
    ratio_outside = dominance_ratio(outside)
    ratio_overall = dominance_ratio(observations)

    print("Wave 11a Task 5 — spread series\n")
    covered = len({o["instrument_id"] for o in observations})
    print(f"  instruments covered      {covered} / {len(instruments)}")
    print(f"  observation window       {WINDOW_START.isoformat()} -> "
          f"{WINDOW_END.isoformat()}  ({len(curve)} trading dates)")
    print(f"  observations generated   {len(observations)}")
    print(f"  observations skipped (no benchmark)  {len(skipped)}")
    if skipped:
        sample = skipped[:5]
        print(f"    sample: {sample}")

    print(f"\n  divergence windows placed  {len(DIVERGENCES)} "
          f"(target >= 3, >= 1 confirm_later)")
    for dv in DIVERGENCES:
        print(f"    {dv['instrument_id']:<14} {dv['start'].isoformat()} -> "
              f"{dv['end'].isoformat()}  peak={dv['peak_bp']}bp  "
              f"confirm_later={dv['confirm_later']}")
    confirm_count = sum(1 for dv in DIVERGENCES if dv["confirm_later"])

    print(f"\n  sparse instruments          {len(SPARSE_GAPS)} "
          f"(target >= 2)")
    for iid, gaps in SPARSE_GAPS.items():
        print(f"    {iid:<14} {gap_counts.get(iid, 0)} dates missing across "
              f"{len(gaps)} gap period(s): "
              + ", ".join(f"{s.isoformat()}..{e.isoformat()}" for s, e in gaps))

    band_rank = {b: i for i, b in enumerate(BANDS_BEST_TO_WORST)}
    n_downgrades = sum(1 for m in migration_transitions
                        if band_rank[m["from_band"]] < band_rank[m["to_band"]])
    n_upgrades = sum(1 for m in migration_transitions
                      if band_rank[m["from_band"]] > band_rank[m["to_band"]])
    print(f"\n  migration crossings          {len(migration_transitions)} "
          f"({n_downgrades} downgrade(s), {n_upgrades} upgrade(s))")
    for m in migration_transitions:
        print(f"    {m['lei']:<20} {m['from_band']}->{m['to_band']} "
              f"@{m['asserted_at']}  anticipation={m['anticipation']}  "
              f"lead_obs={m['lead_obs']}")

    print(f"\n  market dominance ratio")
    print(f"    outside divergence windows   {ratio_outside:.4f}  "
          f"(ceiling {DOMINANCE_CEILING}) "
          f"{'OK' if ratio_outside <= DOMINANCE_CEILING else 'FAIL'}")
    print(f"    overall (incl. divergence)   {ratio_overall:.4f}  "
          f"(informational only; divergence windows are excluded above by design)")

    print("\n  §F conditions")
    checks = [
        (">= 3 divergence cases", len(DIVERGENCES), 3),
        (">= 1 divergence confirmed later", confirm_count, 1),
        (">= 2 thinly-traded instruments with real gaps", len(SPARSE_GAPS), 2),
        (">= 1 migration crossing in EACH direction (up and down)",
         min(n_downgrades, n_upgrades), 1),
    ]
    short = 0
    for label, actual, floor in checks:
        ok = actual >= floor
        short += not ok
        print(f"    [{'ok  ' if ok else 'FAIL'}] {label:<48} {actual} / {floor}")
    dominance_ok = ratio_outside <= DOMINANCE_CEILING
    short += not dominance_ok
    print(f"    [{'ok  ' if dominance_ok else 'FAIL'}] "
          f"{'market dominance <= 40% outside divergence windows':<48} "
          f"{ratio_outside:.4f} / {DOMINANCE_CEILING}")
    print(f"    [info] observations skipped for no benchmark: {len(skipped)} "
          f"(expected ~0)")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 1 if short else 0

    payload = {
        "wave": "11a",
        "task": 5,
        "seed": SEED,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_for": "rating-and-spread-migration",
        "window": {
            "start": WINDOW_START.isoformat(),
            "end": WINDOW_END.isoformat(),
            "trading_dates": len(curve),
        },
        "composition_method": (
            "benchmark_bp = interpolate_tenor(curve[d], years_to_maturity(d)) "
            "* 100 [public]; market_oas_bp = oas[in_force_band][d] [public, "
            "already bp] where in_force_band steps to the obligor's new band "
            "at asserted_at (see migration_transitions); idiosyncratic_bp = "
            "per-instrument band/seniority baseline + a small per-instrument "
            "draw + a mean-reverting AR(1) daily wiggle + an engineered "
            "divergence bump inside placed windows + an engineered "
            "anticipation ramp ahead of each migration, scaled by the real "
            "inter-band OAS gap [synthetic — engineered]; spread_bp = "
            "market_oas_bp + idiosyncratic_bp; yield_bp = benchmark_bp + "
            "spread_bp. years_to_maturity recomputed per observation date, "
            "never fixed at issuance."),
        "provenance": {
            "benchmark_bp": "public",
            "market_oas_bp": "public",
            "idiosyncratic_bp": "synthetic — engineered",
            "spread_bp": "computed (public + engineered)",
            "yield_bp": "computed (public + public + engineered)",
        },
        "divergence_windows": divergence_windows_for_artifact(instruments),
        "migration_transitions": migration_transitions,
        "sparse_instruments": [
            {
                "instrument_id": iid,
                "lei": next(i["lei"] for i in instruments
                            if i["instrument_id"] == iid),
                "rating_band": next(i["rating_band"] for i in instruments
                                     if i["instrument_id"] == iid),
                "gap_periods": [
                    {"start": s.isoformat(), "end": e.isoformat()}
                    for s, e in gaps
                ],
                "dates_missing": gap_counts.get(iid, 0),
                "note": "genuine absence -- these dates carry no "
                        "observation at all, not an interpolated value",
            }
            for iid, gaps in SPARSE_GAPS.items()
        ],
        "market_dominance": {
            "ceiling": DOMINANCE_CEILING,
            "ratio_outside_divergence_windows": round(ratio_outside, 4),
            "ratio_overall_informational": round(ratio_overall, 4),
        },
        "observations": observations,
        "skipped_no_benchmark": skipped,
        "notes": [
            f"driven by curve dates only ({len(curve)} in-window trading "
            f"dates): every one of them carries an OAS value for all five "
            f"bands (measured 0 gaps), so `skipped_no_benchmark` isolates "
            f"exactly the interpolate_tenor(None) case and nothing else.",
            f"divergence windows and sparse instruments are disjoint "
            f"instrument sets ({sorted(d['instrument_id'] for d in DIVERGENCES)} "
            f"vs {sorted(SPARSE_GAPS)}) so the two §F conditions stay "
            f"separately legible in the series.",
        ],
    }
    SCREEN.mkdir(parents=True, exist_ok=True)
    out = SCREEN / "wave11a_spreads.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")

    return 1 if short else 0


if __name__ == "__main__":
    sys.exit(main())
