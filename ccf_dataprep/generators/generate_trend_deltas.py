#!/usr/bin/env python3
"""Wave 11b — period-over-period XBRL trend deltas.

No fetch. `financial_fact` (15,055 rows, loaded by an earlier wave) already
holds every XBRL fact for the 50-anchor cast; this generator only derives
arithmetic over what is already in Postgres.

INSTANT VS. DURATION, NOT Q-VS-FY BY LABEL. Each `financial_fact` row is
itself either a point-in-time snapshot (`period_start IS NULL` — Assets,
Liabilities, StockholdersEquity, the debt and lease tags) or a flow
accumulated over a span (`period_start` set — Revenues, NetIncomeLoss,
OperatingIncomeLoss, the interest and D&A tags, one stray InterestExpenseDebt
row). Comparing two *instant* snapshots is always apples-to-apples regardless
of which filing (10-Q or 10-K) reported them, so instant series are built per
`(lei, tag, unit)` and diffed consecutively by `period_end`.

A *duration* flow is not: a quarter's Revenues and a full fiscal year's
Revenues cover spans roughly 3x apart, so diffing a quarter's flow against a
year's flow produces a huge, meaningless jump that LOOKS like a real signal.

FISCAL_PERIOD IS NOT A RELIABLE SPAN PROXY. An earlier version of this
generator bucketed duration facts by the `fiscal_period` label ("Q1", "FY",
...), on the theory that same label implies same span. It does not: XBRL
issuers routinely report *cumulative year-to-date* figures under a quarterly
label — a fact tagged "Q3" with `period_start` pinned to the start of the
fiscal year has an actual span of ~270 days, not ~90. Measured directly off
this table, the same `fiscal_period` label covers actual spans from ~87 to
~370 days for real (lei, tag) series. Bucketing by label therefore let
mismatched-length deltas through (e.g. a 89-day span diffed against a
365-day span) and, separately, let the same real period_end be sorted into
more than one label-bucket at once, producing conflicting pct_change values
for the same (lei, tag, period_end).

The fix: comparability is decided from the ACTUAL reported span
(`period_end - period_start`), not the label. Spans cluster tightly around
four centers in this data (quarterly ~90d, half-year ~180d, three-quarter
~270d, annual ~365d) with wide gaps between clusters (the nearest two
clusters are >30 days apart at their closest edges), so each duration point
is assigned to the nearest center within a tolerance of ±20 days —
comfortably inside every observed cluster and comfortably short of ever
bridging two clusters. A span that lands in no cluster (outside tolerance of
all four centers) is dropped rather than guessed at. Two duration points are
only ever diffed against each other when they land in the *same* bucket, so
every duration delta compares two spans within 40 days of each other by
construction (2x the per-point tolerance) — enforced by an assertion at
emission time, not just by the bucketing logic.

Each (lei, tag, unit) duration series is walked in period_end order, keeping
one "last seen" anchor per bucket; a delta is emitted whenever a later point
lands in a bucket that already has an anchor. This gives Q1-over-Q1,
FY-over-FY, and so on — effectively year-over-year for a fixed span length —
while a single fact is deduped to one canonical value per (lei, tag, unit,
period_end) *before* bucketing (see DEDUPING below), so a given period_end
can only ever anchor (and be diffed from) exactly one bucket. That closes
off the conflicting-pct_change failure mode by construction, not just by
convention; a second assertion checks it holds on every run regardless.

Instant series are unaffected by any of this — point-in-time snapshots have
no span to bucket, and stay on the original per-(lei, tag, unit) consecutive
diff.

DEDUPING RESTATEMENTS. The same (lei, tag, unit, period_end) fact is often
reported more than once: a filing's comparative columns repeat prior periods
verbatim, and a real subset of those repeats hold genuinely different values
for the same period (restatements/reclassifications) — 407 such groups in
this table, measured by this generator's own dedupe key (lei, tag, unit,
period_end) — the coarser key required by the fix above, dropping
`fiscal_period` from it, merges some previously fine-grained groups and
surfaces more disagreement than a fiscal_period-scoped key would. Each group
is collapsed to the row with the earliest `filed_date` — the fact as FIRST
disclosed, not as later smoothed over. This is deterministic and matches an
early-warning surveillance use: the first-reported figure is what market
participants actually saw at the time. Of those 407 groups, 122 differ by
more than 20% and 47 by more than 100% between the earliest- and
latest-filed values — a real amount of restatement signal is being
discarded by this policy, and that trade should stay visible rather than
implicit.

UNIT IS PART OF THE OUTPUT ROW, NOT JUST THE INTERNAL SERIES KEY. One
issuer/tag pair in this table genuinely reports the same period_end in two
different currencies (CAD and USD) — two distinct facts, same
(lei, tag, period_end). The series key already carried `unit`, so those
were never confused internally, but an earlier version of this generator
omitted `unit` from the *emitted* row. That made two legitimately different
facts collide on (lei, tag, period_end) in the output, which would have
tripped `_assert_no_conflicting_triples` and aborted the whole run — a
benign multi-currency filer turning into a total outage. `unit` is now
carried into every emitted row and into the conflicting-triple guard's key,
so two currencies are no longer a conflict at all.

    uv run generators/generate_trend_deltas.py --dry-run
    uv run generators/generate_trend_deltas.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone

from ccf.config import REPO_ROOT, pg_connect
from generators.fetch_8k_items import WINDOW_END, WINDOW_START, in_window

SCREEN = REPO_ROOT / "sources" / "screening"

# Actual-span comparability buckets for duration (flow) facts. Centers are
# the observed clusters in `financial_fact`; ±20 days sits comfortably
# inside each cluster (the widest, ~87-97d for "quarterly", is ±10 from
# center) and comfortably short of the >30-day gap to its nearest neighbor,
# so no tolerance choice here can bridge two real clusters together.
SPAN_BUCKETS: dict[str, int] = {
    "quarterly": 90,
    "half_year": 180,
    "three_quarter": 270,
    "annual": 365,
}
SPAN_TOLERANCE_DAYS = 20


def _span_bucket(span_days: int) -> str | None:
    """Nearest bucket within tolerance, or None if the span is atypical."""
    best_name, best_diff = None, None
    for name, center in SPAN_BUCKETS.items():
        diff = abs(span_days - center)
        if diff <= SPAN_TOLERANCE_DAYS and (best_diff is None or diff < best_diff):
            best_name, best_diff = name, diff
    return best_name


def pct_change(value: float, prior: float | None) -> float | None:
    """Period-over-period change, or None where it is undefined.

    Returns None rather than skipping the row: a guard written as
    `if not prior: continue` drops the observation entirely, and a delta
    that vanishes from the dataset is a silent failure. None keeps the
    row and makes the undefined case visible downstream.

    Divides by abs(prior), not prior: that keeps the sign of the MOVE, not
    the sign of the base. Going from -100 to -50 is a loss halving, which
    is +50%, not -50%. Negative bases are routine in XBRL (accumulated
    deficit, net loss); dividing by `prior` itself would silently invert
    every improvement on a negative-base series into a deterioration.
    """
    if prior is None or prior == 0:
        return None
    return (value - prior) / abs(prior) * 100.0


def _fetch_facts(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT lei, tag, unit, period_start, period_end, "
            "       filed_date, value "
            "FROM financial_fact "
            "ORDER BY lei, tag, unit, period_end, filed_date"
        )
        return cur.fetchall()


def _dedupe(rows: list[tuple]) -> dict:
    """Collapse repeated (lei, tag, unit, period_end) reports of the same
    fact to the earliest-filed value.

    `fiscal_period` plays no part in the key: it is a filing-context label,
    not a fact identity, and folding it into the key is exactly what let
    the same real period_end anchor more than one comparability bucket (see
    module docstring). One canonical row per (lei, tag, unit, period_end),
    full stop — its own `period_start` (carried through, not the label)
    is what later decides its comparability bucket.
    """
    best: dict = {}
    for lei, tag, unit, period_start, period_end, filed_date, value in rows:
        key = (lei, tag, unit, period_end)
        prior = best.get(key)
        if prior is None or filed_date < prior[0]:
            best[key] = (filed_date, float(value), period_start)
    return best


def _build_series(deduped: dict) -> dict:
    """Group deduped facts into ordered (period_end, value, period_start)
    series keyed by (lei, tag, unit). Instant vs. duration is decided per
    point from that point's own `period_start` (one stray InterestExpenseDebt
    row is instant while the rest of its tag is duration; classifying per
    point rather than per tag keeps that row from corrupting either series).
    """
    series: dict = defaultdict(list)
    for (lei, tag, unit, period_end), (_, value, period_start) in deduped.items():
        series[(lei, tag, unit)].append((period_end, value, period_start))
    for series_key in series:
        series[series_key].sort(key=lambda p: p[0])
    return series


def _instant_deltas(lei: str, tag: str, unit: str, points: list[tuple]) -> list[dict]:
    deltas = []
    for (prior_end, prior_val, _), (cur_end, cur_val, _) in zip(points, points[1:]):
        if not in_window(cur_end.isoformat()):
            continue
        deltas.append({
            "lei": lei, "tag": tag, "unit": unit,
            "period_end": cur_end.isoformat(),
            "prior_period_end": prior_end.isoformat(),
            "value": cur_val, "prior_value": prior_val,
            "pct_change": pct_change(cur_val, prior_val),
            "provenance": "public",
        })
    return deltas


def _duration_deltas(lei: str, tag: str, unit: str, points: list[tuple]) -> list[dict]:
    """Walk one (lei, tag, unit) duration series in period_end order,
    keeping one "last seen" anchor per span bucket, and emit a delta each
    time a later point lands in a bucket that already has an anchor. A
    point whose span fits no bucket neither anchors nor is compared.
    """
    deltas = []
    anchors: dict[str, tuple[date, float, int]] = {}
    for period_end, value, period_start in points:
        span_days = (period_end - period_start).days
        bucket = _span_bucket(span_days)
        if bucket is None:
            continue
        if bucket in anchors:
            prior_end, prior_val, prior_span = anchors[bucket]
            # Loud regression guard: bucketing is only meaningful if it in
            # fact bounds the span mismatch between what it compares.
            assert abs(span_days - prior_span) <= 2 * SPAN_TOLERANCE_DAYS, (
                f"span mismatch within bucket {bucket!r} for {lei} {tag}: "
                f"{prior_end}->{period_end} spans {prior_span}d vs {span_days}d")
            if in_window(period_end.isoformat()):
                deltas.append({
                    "lei": lei, "tag": tag, "unit": unit,
                    "period_end": period_end.isoformat(),
                    "prior_period_end": prior_end.isoformat(),
                    "value": value, "prior_value": prior_val,
                    "pct_change": pct_change(value, prior_val),
                    "provenance": "public",
                })
        anchors[bucket] = (period_end, value, span_days)
    return deltas


def _assert_no_conflicting_triples(deltas: list[dict]) -> None:
    """Loud regression guard: a (lei, tag, unit, period_end) key must never
    carry two different pct_change values in the emitted set.

    Keyed on unit as well as (lei, tag, period_end) — matching the dedupe
    key in `_dedupe` — because a single issuer can genuinely report the
    same tag, for the same period_end, in two different currencies (see
    module docstring). That is two distinct facts, not a conflict; without
    `unit` in the key this guard would raise on a benign multi-currency
    filer and abort the run with zero output.
    """
    seen: dict[tuple, float | None] = {}
    for d in deltas:
        key = (d["lei"], d["tag"], d["unit"], d["period_end"])
        if key in seen and seen[key] != d["pct_change"]:
            raise AssertionError(
                f"conflicting pct_change for {key}: {seen[key]!r} vs "
                f"{d['pct_change']!r}")
        seen[key] = d["pct_change"]


def _build_deltas(series: dict) -> list[dict]:
    deltas = []
    for (lei, tag, unit), points in series.items():
        instant_points = [p for p in points if p[2] is None]
        duration_points = [p for p in points if p[2] is not None]
        deltas.extend(_instant_deltas(lei, tag, unit, instant_points))
        deltas.extend(_duration_deltas(lei, tag, unit, duration_points))
    _assert_no_conflicting_triples(deltas)
    deltas.sort(key=lambda d: (d["lei"], d["tag"], d["unit"], d["period_end"]))
    return deltas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with pg_connect() as conn:
        rows = _fetch_facts(conn)

    deduped = _dedupe(rows)
    series = _build_series(deduped)
    deltas = _build_deltas(series)

    by_lei: dict[str, int] = defaultdict(int)
    by_tag: dict[str, int] = defaultdict(int)
    none_count = 0
    for d in deltas:
        by_lei[d["lei"]] += 1
        by_tag[d["tag"]] += 1
        if d["pct_change"] is None:
            none_count += 1

    all_leis = sorted({lei for lei, *_ in rows})
    zero_coverage = [lei for lei in all_leis if by_lei.get(lei, 0) == 0]

    print(f"  {len(rows)} raw financial_fact rows -> {len(deduped)} deduped facts "
          f"-> {len(series)} series")
    print(f"  {len(deltas)} in-window deltas across {len(by_lei)}/{len(all_leis)} obligors\n")

    print("  by obligor (LEI):")
    for lei in all_leis:
        print(f"    {lei}: {by_lei.get(lei, 0)}")

    print("\n  by tag:")
    for tag in sorted(by_tag):
        print(f"    {tag}: {by_tag[tag]}")

    print(f"\n  zero-coverage obligors: {len(zero_coverage)} {zero_coverage}")
    print(f"  pct_change is None for {none_count}/{len(deltas)} deltas "
          f"(prior value was zero at that period)")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11b_trend_deltas.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "ccf_v2.financial_fact (derived arithmetic, no fetch)",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "deltas": deltas,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
