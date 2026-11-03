#!/usr/bin/env python3
"""§F rating-and-spread-migration: the three proofs counting would fake.

Modelled on `validators/traversal.py` (split out in Wave 10 for the identical
reason): some conditions describe a *relationship* in the data, not a tally,
and a validator that only counts rows can be satisfied by data that does not
have the property the count is supposed to stand in for.

1. **Divergence** (§F condition 5). A divergence case is a period where an
   instrument's spread widens materially while the obligor's internal grade
   does not move; a confirmed case is one where a LATER grade action moves in
   the direction the spread already showed. This is recomputed from the
   loaded series and the loaded grade-assertion chain — never from
   `wave11a_spreads.json["divergence_windows"]` or `["confirm_later"]`, which
   are the generator's own claims about what it placed, not evidence that the
   condition is actually present in what got loaded.

   "Materially" is anchored to `divergence_threshold` (Postgres,
   `synthetic — internal`, §F-independent of this validator) rather than to
   an arbitrary constant: the obligor's SIC maps to a sector
   (`loaders.load_postgres_wave11a.sector_for`, reused rather than
   reimplemented) and that sector's `threshold_bp` is the bar an instrument's
   residual (`spread_bp - market_oas_bp`, recomputed here, not trusted from
   the `idiosyncratic_bp` column) has to clear, sustained, before it counts
   as a window at all.

2. **Sparsity** (§F condition 7). Asserts observation DATES are absent for
   >= 2 instruments, against the full date universe every other instrument
   actually observes — not a row count, which a fully-interpolated series
   would also pass.

3. **Market dominance** (§7 risk #1). median(|idiosyncratic_bp|) <=
   40% * median(market_oas_bp), computed with each instrument's OWN detected
   divergence-window dates excluded — never relaxed, only excluded, per the
   design doc.

    uv run validators/series.py
"""

from __future__ import annotations

import json
import statistics
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import groupby

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2
SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
C_ORGANIZATION_CREDIT_RATING = (
    f"{FIBO}FBC/DebtAndEquities/CreditRatings/OrganizationCreditRating"
)
P_CONCERNS_PARTY = f"{FIBO}FBC/DebtAndEquities/CreditRatings/concernsParty"

#: Part of what a "window" MEANS, not an extra condition layered on top of
#: one: §F's divergence is "the spread widened materially" -- a period, not
#: an instant -- so a single elevated day is noise, not a migration signal,
#: regardless of how far over threshold it sits. This is the semantic floor
#: that encodes that distinction.
#:
#: Measured, not assumed, per the Task 3 date-gate lesson -- but the measurement
#: says something different here than it did there. Setting this to 1 and
#: re-running against the live data (2026-08-19) reproduces the IDENTICAL
#: four windows, same instruments, same dates, same observation counts: every
#: one of the 56 non-divergent, non-sparse instruments has a maximum
#: delta-over-baseline of ~9bp against thresholds of 80-120bp -- roughly 25
#: AR(1) standard deviations away -- so no single day ever crosses threshold
#: on its own here. That makes this floor UNTESTED against the current
#: seed/parameters, not MEANINGLESS: Task 3's DATE_RE was dropped because the
#: condition it added was redundant with one already present -- a declarative
#: rating-action sentence already implied a dated event, so DATE_RE could
#: never have discriminated even on different data. This floor is not
#: redundant with anything else detect_windows checks; it is simply not yet
#: exercised by data whose engineered bumps are all sized in the hundreds of
#: bp. Kept as a defensive semantic bound, honestly labelled as
#: verified-present rather than verified-discriminating.
MIN_WINDOW_OBS = 10

DOMINANCE_CEILING = 0.40


@dataclass
class DivergenceWindow:
    instrument_id: str
    lei: str
    start: date
    end: date
    n_obs: int
    sector: str
    threshold_bp: float
    peak_delta_bp: float
    notch_during: int | None
    confirmed: bool
    confirming_valid_from: date | None = None
    confirming_notch: int | None = None


def bindings(sparql: str) -> list[dict]:
    return fluree.query(sparql)["results"]["bindings"]


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------

def load_instrument_series(cur) -> dict[str, list[tuple[date, float, float]]]:
    """{instrument_id: [(obs_date, spread_bp, market_oas_bp), ...]} sorted."""
    cur.execute(
        f'SELECT instrument_id, obs_date, spread_bp, market_oas_bp '
        f'FROM "{S}".spread_observation ORDER BY instrument_id, obs_date'
    )
    out: dict[str, list[tuple[date, float, float]]] = {}
    for iid, grp in groupby(cur.fetchall(), key=lambda r: r[0]):
        out[iid] = [(d, float(sp), float(oas)) for _, d, sp, oas in grp]
    return out


def load_sector_thresholds(cur, leis: set[str]) -> tuple[dict[str, str], dict[str, float]]:
    """(lei -> sector, sector -> threshold_bp), from the loaded divergence_threshold
    table -- ORIGINATED data, not a constant duplicated here. `sector_for` is
    imported (pure function, no I/O) rather than re-derived so the sector
    label used here can never silently diverge from the one the loader used
    to populate the table in the first place."""
    from loaders.load_postgres_wave11a import sector_for

    cur.execute(f'SELECT sector, threshold_bp FROM "{S}".divergence_threshold')
    threshold_by_sector = {sector: float(bp) for sector, bp in cur.fetchall()}

    cur.execute(f'SELECT lei, sic FROM "{S}".legal_entity WHERE lei = ANY(%s)',
                (list(leis),))
    sic_by_lei = {lei.strip(): sic for lei, sic in cur.fetchall()}
    sector_by_lei = {lei: sector_for(sic_by_lei.get(lei)) for lei in leis}
    return sector_by_lei, threshold_by_sector


def load_grade_history() -> dict[str, list[tuple[date, date, int, str, str, date]]]:
    """{lei: [(valid_from, valid_to, notch, trigger, grade, asserted_at), ...]}
    sorted by valid_from. `valid_to` is 9999-12-31 for the still-open final
    assertion, so overlap arithmetic never has to special-case None.

    Reads the assertion CHAIN from Fluree (the only store that has it -- see
    loaders/load_fluree_wave11a.py's module docstring: Postgres holds only
    the static grade->notch scale, never which grade an obligor held on a
    given date) and resolves `grade` to `notch` via the loaded `rating_scale`
    table, so a Fluree grade string that is not in Postgres's scale surfaces
    as a loud KeyError rather than a silently-dropped row.

    `grade` and `asserted_at` are appended (not inserted) beyond the original
    `(valid_from, valid_to, notch, trigger)` tuple so every existing
    positional consumer (`detect_windows`'s `h[0]`/`h[1]`/`h[2]`) keeps
    working unmodified. `asserted_at` is parsed to a `date`, matching
    `valid_from`, so `migration_transitions` can sort and compare it against
    an `obs_date` column without a string/date mismatch.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT grade, notch FROM "{S}".rating_scale')
        notch_by_grade = dict(cur.fetchall())

    q = f"""
    SELECT ?grade ?validFrom ?validTo ?assertedAt ?trigger ?lei FROM <{L}> WHERE {{
      ?a a <{C_ORGANIZATION_CREDIT_RATING}> .
      ?a <{EX}grade> ?grade .
      ?a <{EX}validFrom> ?validFrom .
      OPTIONAL {{ ?a <{EX}validTo> ?validTo }}
      ?a <{EX}assertedAt> ?assertedAt .
      ?a <{EX}trigger> ?trigger .
      ?a <{P_CONCERNS_PARTY}> ?party .
      ?party <{EX}lei> ?lei .
    }}
    """
    out: dict[str, list[tuple[date, date, int, str, str, date]]] = {}
    for b in bindings(q):
        lei = b["lei"]["value"]
        vf = date.fromisoformat(b["validFrom"]["value"])
        vt = (date.fromisoformat(b["validTo"]["value"]) if "validTo" in b
              else date(9999, 12, 31))
        aa = date.fromisoformat(b["assertedAt"]["value"])
        notch = notch_by_grade[b["grade"]["value"]]
        out.setdefault(lei, []).append(
            (vf, vt, notch, b["trigger"]["value"], b["grade"]["value"], aa))
    for lei in out:
        out[lei].sort()
    return out


# --------------------------------------------------------------------------
# Divergence -- the relationship a count cannot express
# --------------------------------------------------------------------------

def detect_windows(
    series: dict[str, list[tuple[date, float, float]]],
    lei_by_instrument: dict[str, str],
    sector_by_lei: dict[str, str],
    threshold_by_sector: dict[str, float],
    history: dict[str, list[tuple[date, date, int, str, str, date]]],
) -> list[DivergenceWindow]:
    """Independently recompute every window where an instrument's residual
    (spread_bp - market_oas_bp, i.e. the market-adjusted level -- arithmetic
    over two stored columns, not a trust of the `idiosyncratic_bp` column
    the generator also wrote) sustains above its sector's materiality bar
    while the obligor's grade holds a single notch throughout.

    A window that does NOT hold a single notch throughout is dropped, not
    counted with a caveat -- "the grade did not move" is part of the
    definition of a divergence, not a footnote on one.
    """
    windows: list[DivergenceWindow] = []
    for iid, obs in series.items():
        lei = lei_by_instrument[iid]
        sector = sector_by_lei[lei]
        threshold = threshold_by_sector.get(sector)
        if threshold is None:
            continue
        dates = [d for d, _, _ in obs]
        residuals = [sp - oas for _, sp, oas in obs]
        baseline = statistics.median(residuals)
        deltas = [r - baseline for r in residuals]
        elevated = [d > threshold for d in deltas]

        i, n = 0, len(elevated)
        while i < n:
            if not elevated[i]:
                i += 1
                continue
            j = i
            while j < n and elevated[j]:
                j += 1
            span = j - i
            if span >= MIN_WINDOW_OBS:
                start, end = dates[i], dates[j - 1]
                peak = max(deltas[i:j])
                overlapping = [h for h in history.get(lei, [])
                               if h[0] < end and h[1] > start]
                notches = {h[2] for h in overlapping}
                if len(notches) == 1:
                    notch_during = next(iter(notches))
                    later_worse = [h for h in history[lei]
                                   if h[0] > end and h[2] > notch_during]
                    confirmed = bool(later_worse)
                    conf = later_worse[0] if later_worse else None
                    windows.append(DivergenceWindow(
                        instrument_id=iid, lei=lei, start=start, end=end,
                        n_obs=span, sector=sector, threshold_bp=threshold,
                        peak_delta_bp=peak, notch_during=notch_during,
                        confirmed=confirmed,
                        confirming_valid_from=conf[0] if conf else None,
                        confirming_notch=conf[2] if conf else None,
                    ))
                else:
                    # A window whose grade moved DURING it is not dropped
                    # silently -- record it so a future run that produces
                    # one is visible in the printed report, but it does not
                    # count toward the floor: "the grade did not move" is
                    # part of what makes it a divergence.
                    windows.append(DivergenceWindow(
                        instrument_id=iid, lei=lei, start=start, end=end,
                        n_obs=span, sector=sector, threshold_bp=threshold,
                        peak_delta_bp=peak, notch_during=None, confirmed=False,
                    ))
            i = j
    return windows


def divergence_windows() -> list[DivergenceWindow]:
    """Public entry point for conditions.py.

    Deliberately does NOT catch anything itself. `load_instrument_series`
    and the `debt_instrument` query below raise `psycopg.errors.UndefinedTable`
    verbatim if the wave has not loaded yet -- that is the caller's
    (`conditions.py`'s `_rsm_divergence`) signal to render this as SKIP
    rather than FAIL, so it propagates unmodified rather than being caught
    and re-raised here. Any OTHER exception also propagates unmodified, for
    the caller to wrap as `CheckFailure` (FAIL, not SKIP) -- see
    `CheckFailure` in conditions.py for why that distinction matters.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        series = load_instrument_series(cur)
        cur.execute(f'SELECT instrument_id, lei FROM "{S}".debt_instrument')
        lei_by_instrument = dict(cur.fetchall())
        leis = set(lei_by_instrument.values())
        sector_by_lei, threshold_by_sector = load_sector_thresholds(cur, leis)

    history = load_grade_history()
    return detect_windows(series, lei_by_instrument, sector_by_lei,
                           threshold_by_sector, history)


# --------------------------------------------------------------------------
# Sparsity -- genuine absence, not a count
# --------------------------------------------------------------------------

def sparse_instruments(cur) -> dict[str, int]:
    """{instrument_id: missing_date_count} for every instrument whose
    observed dates are a STRICT SUBSET of the date universe every other
    instrument in the estate actually observes on.

    Deliberately a set-difference against the union of every OTHER
    instrument's dates, not a `COUNT(*) < some_floor` -- a fully
    interpolated series (every date filled, dense) would pass a count check
    and fail this one, which is the entire reason this condition cannot be
    established by counting.
    """
    cur.execute(f'SELECT DISTINCT obs_date FROM "{S}".spread_observation')
    universe = {r[0] for r in cur.fetchall()}

    cur.execute(f'SELECT instrument_id, obs_date FROM "{S}".spread_observation')
    by_instrument: dict[str, set] = {}
    for iid, d in cur.fetchall():
        by_instrument.setdefault(iid, set()).add(d)

    out: dict[str, int] = {}
    for iid, dates in by_instrument.items():
        missing = universe - dates
        if missing:
            out[iid] = len(missing)
    return out


# --------------------------------------------------------------------------
# Market dominance -- excluded, not relaxed
# --------------------------------------------------------------------------

def dominance_ratio_excluding_windows(
    cur, windows: list[DivergenceWindow]
) -> tuple[float, int, int]:
    """median(|idiosyncratic_bp|) / median(market_oas_bp) over every
    observation EXCEPT an instrument's own detected-window dates.

    Uses the stored `idiosyncratic_bp` / `market_oas_bp` columns directly --
    this is the quantity §7 names, not a re-derivation -- but the EXCLUSION
    set comes from `detect_windows` above, never from
    `wave11a_spreads.json["divergence_windows"]`.

    Returns (ratio, n_excluded_rows, n_total_rows).
    """
    exclude: dict[str, set[date]] = {}
    for w in windows:
        span = exclude.setdefault(w.instrument_id, set())
        d = w.start
        while d <= w.end:
            span.add(d)
            d = date.fromordinal(d.toordinal() + 1)

    cur.execute(f'SELECT instrument_id, obs_date, idiosyncratic_bp, market_oas_bp '
                f'FROM "{S}".spread_observation')
    idio: list[float] = []
    mkt: list[float] = []
    excluded_n = 0
    total_n = 0
    for iid, d, ib, mb in cur.fetchall():
        total_n += 1
        if d in exclude.get(iid, ()):
            excluded_n += 1
            continue
        idio.append(abs(float(ib)))
        mkt.append(float(mb))

    market_median = statistics.median(mkt) if mkt else 0.0
    idio_median = statistics.median(idio) if idio else 0.0
    ratio = (float("inf") if idio_median else 0.0) if market_median == 0 \
        else idio_median / market_median
    return ratio, excluded_n, total_n


# --------------------------------------------------------------------------
# Migration transition -- the response, not just the crossing
# --------------------------------------------------------------------------

TRANSITION_TOLERANCE = 0.15
#: Wide ON PURPOSE. The AR(1) idiosyncratic walk runs underneath every
#: observation, so a tight bound would be asserting that noise is absent
#: rather than that the ramp is present. 15% still fails a pinned band
#: (which produces a 0bp step, not a within-tolerance one).


def _cross_check_artifact(
    crossings: dict[str, list[tuple[date, str, str]]],
    profiles: dict[str, dict],
) -> tuple[str, bool, str]:
    """Cross-check the crossing set derived HERE, from Fluree, against the
    `migration_transitions` block the generator wrote into
    `wave11a_spreads.json` -- and against the alpha each LEI receives from
    `assign_profiles`.

    `assign_profiles` maps profiles by index over a SORTED LEI list. The
    generator built that list from the grade chains at generation time; this
    validator builds it independently, right now, from Fluree. If the two
    sets of migrating LEIs were ever to differ by even one member, every
    index would shift, and every downstream alpha comparison would silently
    compare each crossing against the WRONG profile -- passing while
    measuring the wrong thing, which is worse than failing outright.

    Only the SET of crossings and the alpha assignment are checked against
    the artifact here. Every measured quantity -- the market step, the
    residual jump -- is still recomputed from the loaded rows in
    `_check_one_transition`, never read from this file.
    """
    doc = json.loads((SCREEN / "wave11a_spreads.json").read_text())
    artifact_rows = doc.get("migration_transitions", [])

    derived_set = {
        (lei, m.isoformat(), f, t)
        for lei, xs in crossings.items()
        for m, f, t in xs
    }
    artifact_set = {
        (r["lei"], r["asserted_at"], r["from_band"], r["to_band"])
        for r in artifact_rows
    }

    derived_alpha = {lei: profiles[lei]["anticipation"] for lei in crossings}
    artifact_alpha: dict[str, float] = {}
    for r in artifact_rows:
        artifact_alpha.setdefault(r["lei"], r["anticipation"])

    sets_match = derived_set == artifact_set
    alphas_match = derived_alpha == artifact_alpha
    ok = sets_match and alphas_match

    if ok:
        detail = (f"{len(derived_set)} crossing(s) over {len(derived_alpha)} "
                   f"obligor(s) -- sets and alpha assignments agree")
    else:
        parts = []
        if not sets_match:
            parts.append(
                f"crossing sets differ -- derived-only: "
                f"{sorted(derived_set - artifact_set)}, artifact-only: "
                f"{sorted(artifact_set - derived_set)}")
        if not alphas_match:
            parts.append(f"alpha assignments differ -- derived: "
                         f"{derived_alpha}, artifact: {artifact_alpha}")
        detail = "; ".join(parts)

    return ("derived crossing set and alpha assignment match "
            "wave11a_spreads.json's migration_transitions block", ok, detail)


def _load_ramp_starts() -> dict[tuple[str, str, str, str], date]:
    """{(lei, asserted_at_iso, from_band, to_band): ramp_start_date}, read
    from `wave11a_spreads.json`'s `migration_transitions` block SOLELY to
    locate the pre-announcement window's boundary (the effect of `lead_obs`)
    -- never as a measured quantity in its own right. Every value compared
    against that boundary in `_check_one_transition` still comes from the
    loaded Postgres rows, never from this file.
    """
    doc = json.loads((SCREEN / "wave11a_spreads.json").read_text())
    return {
        (r["lei"], r["asserted_at"], r["from_band"], r["to_band"]):
            date.fromisoformat(r["ramp_start_date"])
        for r in doc.get("migration_transitions", [])
    }


def _check_one_transition(cur, lei, iid, m, f, t, alpha,
                           ramp_start) -> list[tuple[str, bool, str]]:
    """Measure ONE instrument's residual jump and pre-announcement move for
    one crossing, from the loaded rows only.

    Always returns exactly two checks -- never merged, never averaged --
    because a single instrument passing cannot stand in for another
    instrument of the same LEI failing. Both are printed whether or not they
    pass, because a number you can read beats a boolean you have to trust.

    `ramp_start` locates the window boundary only (see `_load_ramp_starts`);
    the residual jump's `gap` and both spread values compared against it are
    recomputed here from `spread_observation`, filtered to this ONE
    `instrument_id` -- the fix for the defect this function used to carry:
    querying all of an LEI's instruments together, unordered by
    `instrument_id`, let `before[-1]`/`after[0]` pair rows across two
    different bonds on a tied `obs_date`, nondeterministically.
    """
    label_jump = (f"{lei[:8]} {iid} {f}->{t} @{m}: residual jump matches "
                  f"alpha={alpha}")
    label_pre = (f"{lei[:8]} {iid} {f}->{t} @{m}: pre-announcement move "
                 f"matches alpha={alpha}")

    lo = min(ramp_start, m - timedelta(days=20))
    hi = m + timedelta(days=20)
    cur.execute(f'''
        SELECT o.obs_date, o.market_oas_bp, o.spread_bp
          FROM "{S}".spread_observation o
         WHERE o.instrument_id = %s AND o.obs_date BETWEEN %s AND %s
         ORDER BY o.obs_date, o.instrument_id''', (iid, lo, hi))
    rows = cur.fetchall()
    before = [r for r in rows if r[0] < m]
    after = [r for r in rows if r[0] >= m]
    if not before or not after:
        reason = "no observations on one side of the announcement"
        return [(label_jump, False, reason), (label_pre, False, reason)]

    b_date, b_mkt, b_spread = before[-1]
    a_date, a_mkt, a_spread = after[0]
    gap = float(a_mkt) - float(b_mkt)
    if abs(gap) < 1.0:
        reason = (f"market_oas_bp did not step at the announcement "
                  f"({b_mkt} -> {a_mkt}) -- the band is still pinned")
        return [(label_jump, False, reason), (label_pre, False, reason)]

    jump = float(a_spread) - float(b_spread)
    expected_jump = (1.0 - alpha) * gap
    jump_ok = abs(jump - expected_jump) <= TRANSITION_TOLERANCE * abs(gap)
    jump_detail = (f"market {b_mkt:.0f}->{a_mkt:.0f} (gap {gap:+.0f}bp), "
                   f"spread jump {jump:+.0f}bp vs expected "
                   f"{expected_jump:+.0f}bp")

    ramp_rows = [r for r in rows if r[0] == ramp_start]
    if not ramp_rows:
        pre_ok = False
        pre_detail = (f"no observation at ramp_start_date "
                      f"{ramp_start.isoformat()} -- cannot measure the "
                      f"pre-announcement move")
    else:
        _, ramp_mkt, ramp_spread = ramp_rows[0]
        pre_move = float(b_spread) - float(ramp_spread)
        # `market_oas_bp` is a real published index, not frozen while a band
        # stays in force -- it keeps moving on its own over the ramp window
        # (measured: up to 23bp over a 110-observation lead). `spread_bp`'s
        # pre-announcement move is that natural market drift PLUS the
        # engineered ramp, so alpha*gap alone under-predicts it whenever the
        # band moved during the lead. Both terms of `expected_pre` come from
        # loaded rows: `market_drift` from market_oas_bp at the two dates
        # already fetched above, `gap` from the same market step the
        # residual-jump check already uses.
        market_drift = float(b_mkt) - float(ramp_mkt)
        expected_pre = market_drift + alpha * gap
        pre_ok = abs(pre_move - expected_pre) <= TRANSITION_TOLERANCE * abs(gap)
        pre_detail = (f"spread {float(ramp_spread):.0f} "
                      f"({ramp_start.isoformat()}) -> {float(b_spread):.0f} "
                      f"({b_date.isoformat()}), pre-announcement move "
                      f"{pre_move:+.0f}bp vs expected {expected_pre:+.0f}bp "
                      f"(market drift {market_drift:+.0f}bp + "
                      f"alpha*gap {alpha * gap:+.0f}bp)")

    return [(label_jump, jump_ok, jump_detail), (label_pre, pre_ok, pre_detail)]


def migration_transitions(cur, history,
                           instruments_by_lei: dict[str, list[str]]
                           ) -> list[tuple[str, bool, str]]:
    """Recompute each band crossing's residual jump AND pre-announcement
    move from the LOADED series -- never from a generator flag, matching how
    divergence and sparsity are already established here.

    Measured PER INSTRUMENT: each of an LEI's instruments is queried and
    checked separately (`_check_one_transition`), and ALL of them must pass
    -- never averaged, never let one instrument's pass mask another's
    failure.
    """
    from generators.generate_grades import BANDS_BEST_TO_WORST
    from generators.narrative_wave11a import assign_profiles, band_of_grade

    crossings = {}
    for lei, rows in history.items():
        seq = sorted(rows, key=lambda r: r[5])          # by asserted_at
        xs = [(cur_r[5], band_of_grade(prev[4]), band_of_grade(cur_r[4]))
              for prev, cur_r in zip(seq, seq[1:])
              if band_of_grade(prev[4]) != band_of_grade(cur_r[4])]
        if xs:
            crossings[lei] = xs

    band_rank = {b: i for i, b in enumerate(BANDS_BEST_TO_WORST)}
    n_downgrades = sum(1 for xs in crossings.values() for _, f, t in xs
                        if band_rank[f] < band_rank[t])
    n_upgrades = sum(1 for xs in crossings.values() for _, f, t in xs
                      if band_rank[f] > band_rank[t])
    out = [("at least one crossing in EACH direction exists in the loaded "
            "chains (upgrade and downgrade, not just one crossing)",
            n_downgrades >= 1 and n_upgrades >= 1,
            f"{len(crossings)} obligor(s), "
            f"{sum(len(v) for v in crossings.values())} crossing(s) "
            f"({n_downgrades} downgrade(s), {n_upgrades} upgrade(s))")]
    if not crossings:
        return out          # the assertion above already failed loudly

    profiles = assign_profiles(sorted(crossings))
    out.append(_cross_check_artifact(crossings, profiles))

    ramp_starts = _load_ramp_starts()

    for lei, xs in sorted(crossings.items()):
        alpha = profiles[lei]["anticipation"]
        for m, f, t in xs:
            key = (lei, m.isoformat(), f, t)
            ramp_start = ramp_starts.get(key)
            if ramp_start is None:
                out.append((f"{lei[:8]} {f}->{t} @{m}: ramp_start_date "
                            f"located in wave11a_spreads.json", False,
                            "no matching migration_transitions entry in "
                            "the artifact"))
                continue
            for iid in instruments_by_lei.get(lei, []):
                out.extend(_check_one_transition(cur, lei, iid, m, f, t,
                                                  alpha, ramp_start))
    return out


# --------------------------------------------------------------------------
def main() -> int:
    print("SERIES VALIDATOR — divergence, sparsity, market dominance, "
          "computed from the loaded series (not a generator flag)\n")

    with pg_connect() as conn, conn.cursor() as cur:
        try:
            cur.execute(f'SELECT 1 FROM "{S}".spread_observation LIMIT 1')
        except Exception as exc:  # noqa: BLE001
            print(f"  [SKIP] spread_observation absent — Wave 11a has not "
                  f"loaded ({type(exc).__name__})")
            return 0
        conn.rollback()

        series = load_instrument_series(cur)
        cur.execute(f'SELECT instrument_id, lei FROM "{S}".debt_instrument')
        lei_by_instrument = dict(cur.fetchall())
        leis = set(lei_by_instrument.values())
        sector_by_lei, threshold_by_sector = load_sector_thresholds(cur, leis)
        instruments_by_lei: dict[str, list[str]] = {}
        for iid, lei in sorted(lei_by_instrument.items()):
            instruments_by_lei.setdefault(lei, []).append(iid)

        print("  DIVERGENCE (§F condition 5) — recomputed from "
              "spread_bp - market_oas_bp vs each obligor's sector threshold\n")
        history = load_grade_history()
        windows = detect_windows(series, lei_by_instrument, sector_by_lei,
                                  threshold_by_sector, history)
        qualifying = [w for w in windows if w.notch_during is not None]
        dropped_unstable = [w for w in windows if w.notch_during is None]
        for w in sorted(qualifying, key=lambda w: w.start):
            print(f"    [ok  ] {w.instrument_id:<14} {w.lei}  "
                  f"{w.start.isoformat()}..{w.end.isoformat()} "
                  f"({w.n_obs} obs, peak {w.peak_delta_bp:.1f}bp over "
                  f"{w.sector} threshold {w.threshold_bp:.0f}bp)  "
                  f"grade held notch={w.notch_during}  "
                  f"{'CONFIRMED -> notch=' + str(w.confirming_notch) + ' on ' + w.confirming_valid_from.isoformat() if w.confirmed else 'not confirmed'}")
        for w in dropped_unstable:
            print(f"    [drop] {w.instrument_id:<14} {w.lei}  "
                  f"{w.start.isoformat()}..{w.end.isoformat()} — grade moved "
                  f"DURING the window; does not count as a divergence")

        n_windows = len(qualifying)
        n_confirmed = sum(1 for w in qualifying if w.confirmed)
        div_ok = n_windows >= 3
        conf_ok = n_confirmed >= 1
        print(f"\n    [{'ok  ' if div_ok else 'FAIL'}] windows with a stable "
              f"grade throughout        {n_windows} / 3")
        print(f"    [{'ok  ' if conf_ok else 'FAIL'}] windows later confirmed "
              f"by a worse rerating   {n_confirmed} / 1")

        print("\n  SPARSITY (§F condition 7) — dates genuinely ABSENT vs the "
              "full date universe\n")
        sparse = sparse_instruments(cur)
        for iid, n_missing in sorted(sparse.items(), key=lambda kv: -kv[1]):
            print(f"    [ok  ] {iid:<14} {n_missing} date(s) absent "
                  f"(no row at all — not interpolated)")
        sparse_ok = len(sparse) >= 2
        print(f"\n    [{'ok  ' if sparse_ok else 'FAIL'}] instruments with "
              f"genuine gaps                  {len(sparse)} / 2")

        print("\n  MARKET DOMINANCE (§7 risk #1) — median|idiosyncratic_bp| "
              "vs 40% of median market_oas_bp, own-window dates excluded\n")
        ratio, excluded_n, total_n = dominance_ratio_excluding_windows(
            cur, qualifying)
        dom_ok = ratio <= DOMINANCE_CEILING
        print(f"    excluded {excluded_n} of {total_n} observations "
              f"(the {len(qualifying)} detected windows' own dates)")
        print(f"    [{'ok  ' if dom_ok else 'FAIL'}] ratio outside windows "
              f"                        {ratio:.4f} / {DOMINANCE_CEILING}")

        print("\n  MIGRATION TRANSITION (known-issues §9.10) — residual jump "
              "and pre-announcement move recomputed PER INSTRUMENT from the "
              "loaded series against each obligor's assigned anticipation "
              "profile\n")
        transition_checks = migration_transitions(cur, history,
                                                    instruments_by_lei)
        for label, ok, detail in transition_checks:
            print(f"    [{'ok  ' if ok else 'FAIL'}] {label} — {detail}")
        transition_ok = all(ok for _, ok, _ in transition_checks)

    failed = not (div_ok and conf_ok and sparse_ok and dom_ok and transition_ok)
    print(f"\n  {'PASS' if not failed else 'FAIL'} — divergence "
          f"{'ok' if div_ok and conf_ok else 'FAIL'}, "
          f"sparsity {'ok' if sparse_ok else 'FAIL'}, "
          f"dominance {'ok' if dom_ok else 'FAIL'}, "
          f"migration transition {'ok' if transition_ok else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
