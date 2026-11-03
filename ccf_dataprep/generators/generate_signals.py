#!/usr/bin/env python3
"""Wave 11b Task 7 — unify all four signal sources into one signal ledger.

Reads the four already-committed artifacts (8-K item events, WARN matches,
GDELT adverse media, XBRL trend deltas) plus the already-loaded
`spread_observation` table, and produces ONE unified `signal_event` ledger,
of the shape `{signal_id, lei, signal_type, observed_at, severity,
source_ref, provenance}`. Everything downstream — the Postgres load
(Task 9), the engineered cascade (Task 8), and `surveillance.py`'s gate
(Task 12) — builds on `signal_rows()` and on the `weights` / `thresholds`
policy tables minted here.

Nothing here is fetched. This module only reads what earlier tasks already
wrote to disk or loaded into Postgres, and derives arithmetic and selection
logic over it — the same posture as `generate_trend_deltas.py`.

WEIGHTS AND THRESHOLDS ARE **ORIGINATED HERE**, not derived from any
upstream artifact — say so plainly, exactly as
`loaders/load_postgres_wave11a.py` says so for `divergence_threshold`. No
source names a per-signal-type weight or an escalation cutoff; these are
internal surveillance policy, invented for this estate, and labelled
`synthetic — internal`. The signals themselves keep the provenance of the
source they were built from (`public`, with one exception below).

FOUR THINGS THIS MODULE MUST GET RIGHT, EACH CARRIED FORWARD FROM PLANNING:

1. TREND-DELTA MATERIALITY. 3,705 trend deltas outnumber 534 8-K events
   7:1. Every delta becoming a `signal_event` would let a fact of pure
   arithmetic (a period-over-period XBRL ratio) dominate every composite
   score, simply because there are more of them. So `trend_delta` reference
   data (the full 3,705, `wave11b_trend_deltas.json`) stays intact and
   untouched — nothing here mutates it — while `signal_event` admits a
   trend delta only where the move is MATERIAL (|pct_change| >= 25%, see
   `TREND_MATERIALITY_PCT`) AND ADVERSE for that specific tag (see
   `ADVERSE_DIRECTION` — a rising `NetIncomeLoss` is not a warning sign, a
   rising `LongTermDebt` is). 25% sits at roughly the 80th percentile of
   the loaded |pct_change| distribution (measured: p75=25.0, p80=33.5,
   p90=73.4) — material by construction, not by round-number intuition —
   and the materiality/direction split is stored as an inspectable POLICY
   ROW in the `thresholds` artifact (kind `trend_delta_materiality`), not
   buried in this constant alone.

   `pct_change is None` (21 rows: a genuine zero prior, not a missing
   value — see `generate_trend_deltas.py`'s own docstring) is handled
   explicitly, never silently dropped and never silently admitted:
     - `value == 0 and prior_value == 0`: no real change occurred (a fact
       that was zero stayed zero). Excluded — there is nothing to signal.
     - `value != 0` (a genuine emergence from a zero base, e.g. a new
       LongTermDebtCurrent obligation appearing where none existed):
       treated as automatically material (a percentage cannot be computed,
       but a debt-like fact going from non-existent to existent is itself
       the material event) and checked against the SAME adverse-direction
       rule as every other row, using the sign of the emergence
       (`value > prior_value` reads as "increase"). This is why the one
       Revenues row in the None set (a $26k revenue line appearing from
       zero) is correctly excluded — revenue increasing is favorable, not
       adverse, regardless of the fact that no percentage exists for it.

2. GDELT / CELANESE — THE FLAG IS NOT ON THE ROWS. `wave11b_gdelt.json`'s
   top-level `coverage[lei].precision_review` records, for Celanese only,
   `recommended_use: "down_weight"` — 25 of 49 sampled mentions are police
   blotters from Celanese, Texas and Celanese Road (Rock Hill, SC), not
   about the company. There is no per-article label to filter on, so this
   module does not (cannot) drop the 25 bad rows individually. Instead it
   reads `precision_review.sampled` / `.off_topic` for any LEI flagged
   `down_weight` and multiplies that LEI's `adverse_media` severities by
   the measured on-topic precision, `(sampled - off_topic) / sampled`
   (Celanese: 24/49 = 0.4898). Generic and data-driven — this fires for
   ANY future LEI the coverage map flags, not a hardcoded Celanese case —
   and the factor itself is written into every affected row's `source_ref`
   and into a `thresholds` policy row (kind `adverse_media_down_weight`)
   so it is inspectable rather than a silent severity haircut.

3. GDELT / EXTREME NETWORKS — WIRE AMPLIFICATION. 200 raw mentions, 115
   distinct titles (one securities class action, republished by the same
   two law firms across newswires). A raw mention count overweights this
   obligor's adverse coverage by ~1.7x. Every `adverse_media` row here is
   built from `(lei, normalized_title)` clusters, not raw mentions: one
   signal per distinct on-topic headline per obligor, with the collapsed
   cluster size recorded in `source_ref.cluster_size` so the amplification
   stays visible rather than merely fixed. This dedup runs for every
   obligor, not only Extreme Networks — it is a general rule the data
   happens to exercise hardest there.

4. THE SPREAD SIGNAL MUST DISTINGUISH ANTICIPATION FROM CONFIRMATION. Per
   `docs/wave11a-migration-transition-design.md`: the composed spread's
   market leg (`market_oas_bp`) is a real published index that STEPS to
   the in-force rating band at the announcement date; the anticipation is
   carried ahead of that date in `idiosyncratic_bp` (`synthetic —
   engineered`) under a per-obligor response profile. At any crossing,
   `alpha = 1 - jump/gap` is recoverable from two adjacent rows — the
   series is exactly invertible — so a detector that reconstructs that
   ratio directly is not detecting anything, it is reading the generator's
   own parameter back out.

   This module never computes a jump/gap ratio and never looks up a band's
   OAS series to find "the other side" of a crossing. Two independent,
   generic DETECTORS run over `spread_observation` alone, but — fix round 1
   correction, below — detection and LABELLING are now two separate steps:
   a detector finding a candidate event does not by itself decide which of
   four phases that event belongs to.

     CONFIRMATION DETECTOR — a single-day rise in `market_oas_bp` (the
     real, public leg) at or above `CONFIRMATION_FRACTION` of the
     obligor's sector `divergence_threshold_bp`. This is the real index
     stepping to a worse band (or, on dates with no crossing at all, a
     real market-wide OAS move — see `_spread_widening_rows`); provenance
     stays `public`, and phase is always `confirmation` — a real, dated,
     public jump does not need ground truth to be labelled, only detected.

     WIDENING-TREND DETECTOR — a sustained rise in the ROLLING MEAN of
     `idiosyncratic_bp` (mean of the trailing `ROLL_WINDOW` observations
     vs. the `ROLL_WINDOW` before that) at or above `ANTICIPATION_FRACTION`
     of the same sector threshold, edge-triggered so one continuing episode
     emits one row rather than one per day it stays elevated. This is a
     trend detector over a single column's own history; it never looks at
     `market_oas_bp` at all and never differences two rows spanning a
     crossing date, which is what would let `alpha` fall out.

     FIX ROUND 1 CORRECTION — this detector's candidate events used to be
     labelled `anticipation` unconditionally. A reviewer decomposed the 11
     rows this produced against the loaded grade chains and Wave 11a's
     `DIVERGENCES` windows: only 2 were genuine pre-crossing anticipation.
     4 were the ramp's own post-announcement discontinuity (design §3.3 —
     `idiosyncratic_bp` snapping back at `M` briefly re-crosses the
     threshold from the other side, 1-3 weeks AFTER an upgrade), 4 were
     real but a DIFFERENT engineered condition (a Wave 11a `DIVERGENCES`
     trapezoid — divergence-with-grade-held, not migration anticipation),
     and 1 was ordinary AR(1) noise with no engineered cause at all. Per
     CLAUDE.md, this project produces labelled data, not the runtime
     detector — so the fix is not a cleverer heuristic, it is reading the
     ground truth this module already has. `_phase_for_trend_event` assigns
     one of four phases from the grade chain's real `asserted_at` dates
     (`generate_spreads.load_band_crossings`) and the `DIVERGENCES`
     windows: `divergence` (event falls inside that instrument's window),
     `anticipation` (strictly before the nearest real crossing's
     `asserted_at`), `confirmation` (at or after it), or `unattributed` (the
     obligor never crosses at all — the row and its magnitude are real,
     only the cause is unknown, so it is kept and labelled honestly rather
     than dropped or mislabelled). Every phase this detector produces stays
     `synthetic — engineered`, because `idiosyncratic_bp` is engineered
     regardless of which of the four labels the event ends up with — per
     `wave11a-migration-transition-design.md` §3.1, "deriving an engineered
     quantity from public inputs does not make it public."

   Both detectors fire ONLY on adverse (widening / rate-rising) moves —
   a jump or a rolling-mean rise, never a fall. This means the two
   REAL upgrade crossings in the loaded data (which tighten, not widen)
   correctly produce zero genuine-anticipation rows: an early-warning
   ledger has no business raising a warning on good news, and this falls
   out of the sign check rather than being special-cased (both upgrades DO
   still produce `confirmation`-phase rows from the post-announcement
   discontinuity — see the fix-round correction above; that is a real,
   honestly-labelled artifact, not a warning about the upgrade itself).
   Both fractions are calibrated against the measured, real distribution of
   day-over-day `market_oas_bp` moves and 20-vs-20 `idiosyncratic_bp`
   rolling deltas (ordinary noise: p95 ~10bp / ~7bp respectively) against
   the four real, loaded crossings (confirmation jumps measured 92-150bp;
   ramps rising tens of bp over their lead window) — comfortably separating
   engineered signal from AR(1) noise on data actually in the store, not by
   intuition. See `ANTICIPATION_FRACTION` / `CONFIRMATION_FRACTION`.

   INSTRUMENT-LEVEL DOUBLE COUNTING — also fix round 1. Every obligor here
   carries 2 debt instruments, both of which react to the same date's real
   or engineered move, so the two detectors above produce CANDIDATE events
   per instrument, not per obligor. `_rollup_to_obligor` collapses
   candidates to one row per `(lei, observed_at, phase)`, keeping the
   max-severity candidate's detail and folding every collapsed
   `instrument_id` into `source_ref["instrument_ids"]` so nothing is lost.
   Pre-fix, 34 of 43 rows (79%) were duplicated instrument pairs; a
   downstream composite summing severities would have double-weighted
   every one of those dates.

    uv run generators/generate_signals.py --dry-run
    uv run generators/generate_signals.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timezone

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.currency import record_inputs, verify_current
from generators.generate_spreads import load_band_crossings
from generators.narrative_wave11a import DIVERGENCES
from loaders.load_postgres_wave11a import sector_for

SCREEN = REPO_ROOT / "sources" / "screening"
S = PG_SCHEMA_V2

POLICY_VERSION = "wave11b-v1"

SIGNAL_TYPES = ("8k_event", "warn_notice", "adverse_media", "spread_widening",
                 "trend_delta")

# Spec §E's lambda_c. `8k_event` is None deliberately: a filed 8-K is a
# permanent fact whose relevance is bounded by supersession (a later filing
# or amendment), not by a half-life. Every other type decays on a clock.
DECAY_DAYS: dict[str, float | None] = {
    "adverse_media": 7,
    "spread_widening": 1,
    "warn_notice": 180,
    "trend_delta": 90,
    "8k_event": None,
}

# --- 1. 8-K item severity ---------------------------------------------------
# Originated: how credit-distress-relevant each item type is, independent of
# any one filing's content. 2.04 (acceleration/triggering event) IS a
# default-adjacent fact by definition, so it sits at the ceiling; 1.01
# (material definitive agreement) is the broadest, least distress-specific
# catch-all, so it sits at the floor.
ITEM_SEVERITY: dict[str, float] = {
    "2.04": 1.00,  # acceleration / triggering event
    "4.02": 0.90,  # non-reliance on previously issued financials
    "4.01": 0.55,  # auditor change
    "2.03": 0.45,  # new direct financial obligation
    "5.02": 0.35,  # officer/director departure
    "1.01": 0.30,  # material definitive agreement (broadest catch-all)
}

# --- 2. WARN notice severity ------------------------------------------------
# Originated: a WARN's severity scales with headcount affected (saturating
# at 200 employees — the largest resolved notice in this cast is 171) and is
# haircut by the match confidence, so an 0.8976-scored resolution never
# reads as more certain than a 1.0-scored one.
WARN_EMPLOYEE_SATURATION = 200.0
WARN_SEVERITY_FLOOR = 0.30  # a 0-employee-reported notice is still a real filing


def _warn_severity(employees: int | None, score: float) -> float:
    headcount_component = min(1.0, (employees or 0) / WARN_EMPLOYEE_SATURATION)
    base = WARN_SEVERITY_FLOOR + (1.0 - WARN_SEVERITY_FLOOR) * headcount_component
    return round(base * score, 4)

# --- 2b. Adverse media (GDELT) ----------------------------------------------
# Originated: every mention already passed GDELT's own tone<-5 filter at
# fetch time (design §2.3), and this artifact carries no per-article tone
# magnitude to grade on (every `tone` field is literally the query string,
# "<-5" — see task report), so every cluster starts at one flat base
# severity. The Celanese down-weight (finding 2, above) is the only
# per-obligor adjustment, and it is measured from `coverage[lei]`, not
# guessed.
ADVERSE_MEDIA_BASE_SEVERITY = 0.5

# --- 3. Trend delta materiality ---------------------------------------------
# Originated (my ruling, CLAUDE.md-required, stated once here rather than
# re-litigated at every call site): a delta must be BOTH material and
# adverse to become a signal_event. 25.0 sits at roughly the measured 80th
# percentile of |pct_change| across the full 3,705-row reference table
# (p75=25.0, p80=33.5, p90=73.4) — chosen so the admitted set is a real
# minority of the reference table, not a majority relabelled.
TREND_MATERIALITY_PCT = 25.0

# Which direction of movement is ADVERSE for each tag, i.e. worsens credit
# risk. Two tags (the D&A pair) are left OUT deliberately: a rising
# depreciation/amortization charge is not unambiguously good or bad for
# credit risk on its own (it can reflect heavy capex or a write-down), and
# forcing a direction onto it would be a guess dressed as a rule. Rows on
# those two tags never enter the signal ledger, whatever their pct_change.
ADVERSE_DIRECTION: dict[str, str] = {
    "Assets": "decrease",
    "CashAndCashEquivalentsAtCarryingValue": "decrease",
    "StockholdersEquity": "decrease",
    "NetIncomeLoss": "decrease",
    "OperatingIncomeLoss": "decrease",
    "Revenues": "decrease",
    "RevenueFromContractWithCustomerIncludingAssessedTax": "decrease",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "decrease",
    "DebtCurrent": "increase",
    "LongTermDebt": "increase",
    "LongTermDebtCurrent": "increase",
    "LongTermDebtNoncurrent": "increase",
    "DebtLongtermAndShorttermCombinedAmount": "increase",
    "Liabilities": "increase",
    "OperatingLeaseLiabilityNoncurrent": "increase",
    "InterestExpense": "increase",
    "InterestExpenseDebt": "increase",
    "InterestExpenseNonoperating": "increase",
    # Deliberately absent: DepreciationAmortizationAndAccretionNet,
    # DepreciationDepletionAndAmortization — see comment above.
}


def _trend_severity(pct: float) -> float:
    """100% move saturates severity at 1.0; smaller material moves scale
    linearly from there. `pct` is expected already |.| >= TREND_MATERIALITY_PCT."""
    return round(min(1.0, abs(pct) / 100.0), 4)


# --- 4. Spread widening: anticipation vs. confirmation ----------------------
ROLL_WINDOW = 20          # trading observations per rolling block
ANTICIPATION_FRACTION = 0.15   # of the obligor's sector divergence_threshold_bp
CONFIRMATION_FRACTION = 0.50   # of the same


def _sha(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


#: Every artifact this generator consumes. Named once, so the currency record
#: written into the output cannot drift from what was actually read.
INPUT_ARTIFACTS = ("wave11b_8k_events.json", "wave11b_warn.json",
                   "wave11b_gdelt.json", "wave11b_trend_deltas.json")


def _load(name: str) -> dict:
    """Read one input artifact, verifying ITS recorded inputs first.

    `wave11b_trend_deltas.json` and the three fetch outputs have no upstream
    artifact of their own, so this is a no-op for them today — but it is the
    call site that makes the chain transitive the moment any of them gains
    one. See `ccf/currency.py` for what the guard does and does not catch.
    """
    doc, _ = verify_current(name)
    return doc


def _norm_title(title: str) -> str:
    """Fold a headline to a comparison key: case-fold, strip punctuation,
    collapse whitespace. Exact-match clustering after this normalisation is
    what collapses Extreme Networks' 200 mentions to 115 distinct stories —
    measured, not assumed (see task report)."""
    t = title.lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def _gdelt_date(seendate: str) -> str:
    """GDELT `seendate` is `YYYYMMDDTHHMMSSZ`; signals elsewhere in this
    ledger carry ISO dates only, so this normalises to match."""
    return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").date().isoformat()


# --- signal builders ---------------------------------------------------------

def _8k_rows(doc: dict) -> list[dict]:
    rows = []
    for e in doc["events"]:
        rows.append({
            "signal_id": f"sig-8k-{_sha(e['accession'], e['item'])}",
            "lei": e["lei"],
            "signal_type": "8k_event",
            "observed_at": e["filing_date"],
            "severity": ITEM_SEVERITY[e["item"]],
            "source_ref": {
                "accession": e["accession"], "item": e["item"],
                "primary_document": e["primary_document"],
            },
            "provenance": "public",
        })
    return rows


def _warn_rows(doc: dict) -> list[dict]:
    """Only VERDICT == 'resolved' matches enter the ledger. `ambiguous`
    pairs stay visible in `wave11b_warn.json["matches"]` (32 of them, per
    CLAUDE.md rule 5 and design §1.3) but are not promoted to a signal
    against a specific obligor — a signal ledger asserts "this obligor had
    this event," and an ambiguous name match has not established that."""
    notices_by_ref = {n["source_ref"]: n for n in doc["notices"]}
    rows = []
    for m in doc["matches"]:
        if m["verdict"] != "resolved":
            continue
        notice = notices_by_ref[m["notice_ref"]]
        rows.append({
            "signal_id": f"sig-warn-{_sha(m['notice_ref'], m['lei'])}",
            "lei": m["lei"],
            "signal_type": "warn_notice",
            "observed_at": notice["notice_date"],
            "severity": _warn_severity(notice.get("employees"), m["score"]),
            "source_ref": {
                "notice_ref": m["notice_ref"], "employer": m["employer"],
                "anchor_name": m["anchor_name"], "match_score": m["score"],
                "state": notice["state"], "employees": notice.get("employees"),
            },
            "provenance": "public",
        })
    return rows


def _adverse_media_rows(doc: dict) -> tuple[list[dict], dict[str, dict]]:
    """Returns (signal rows, per-LEI {raw, distinct} dedup counts) — the
    counts are needed by `main()`'s composition report and are cheaper to
    compute once here than to re-derive from the emitted rows."""
    coverage = doc.get("coverage", {})
    clusters: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for m in doc["mentions"]:
        clusters[(m["lei"], _norm_title(m["title"]))].append(m)

    dedup_counts: dict[str, dict] = defaultdict(lambda: {"raw": 0, "distinct": 0})
    rows = []
    for (lei, _norm), cluster in clusters.items():
        cluster.sort(key=lambda m: m["seendate"])
        rep = cluster[0]
        dedup_counts[lei]["raw"] += len(cluster)
        dedup_counts[lei]["distinct"] += 1

        severity = ADVERSE_MEDIA_BASE_SEVERITY
        source_ref = {
            "title": rep["title"], "domain": rep["domain"], "url": rep["url"],
            "employer_query": rep["employer_query"], "cluster_size": len(cluster),
        }
        review = coverage.get(lei, {}).get("precision_review")
        if review and review.get("recommended_use") == "down_weight":
            factor = round(
                (review["sampled"] - review["off_topic"]) / review["sampled"], 4)
            severity = round(severity * factor, 4)
            source_ref["down_weight_factor"] = factor
            source_ref["down_weight_reason"] = (
                "coverage[lei].precision_review flags this LEI for down_weight "
                f"({review['off_topic']}/{review['sampled']} sampled mentions "
                "off-topic); severity multiplied by measured on-topic precision")
            dedup_counts[lei]["down_weight_factor"] = factor

        rows.append({
            "signal_id": f"sig-media-{_sha(lei, _norm)}",
            "lei": lei,
            "signal_type": "adverse_media",
            "observed_at": _gdelt_date(rep["seendate"]),
            "severity": severity,
            "source_ref": source_ref,
            "provenance": "public",
        })
    return rows, dict(dedup_counts)


def _trend_delta_rows(doc: dict) -> tuple[list[dict], dict]:
    """Returns (signal rows, exclusion counters) for the composition report:
    how many of the 3,705 reference rows were excluded, and why."""
    counters = {
        "total": 0, "excluded_neutral_tag": 0, "excluded_below_threshold": 0,
        "excluded_favorable_direction": 0, "excluded_zero_to_zero": 0,
        "included_from_none_prior": 0, "included": 0,
    }
    rows = []
    for d in doc["deltas"]:
        counters["total"] += 1
        tag = d["tag"]
        wanted = ADVERSE_DIRECTION.get(tag)
        if wanted is None:
            counters["excluded_neutral_tag"] += 1
            continue

        pct = d["pct_change"]
        if pct is None:
            value, prior = d["value"], d["prior_value"]
            if value == 0 and prior == 0:
                counters["excluded_zero_to_zero"] += 1
                continue
            direction = "increase" if value > prior else "decrease"
            if direction != wanted:
                counters["excluded_favorable_direction"] += 1
                continue
            severity = 1.0  # undefined magnitude from a zero base: maximal
            counters["included_from_none_prior"] += 1
        else:
            if abs(pct) < TREND_MATERIALITY_PCT:
                counters["excluded_below_threshold"] += 1
                continue
            direction = "increase" if pct > 0 else "decrease"
            if direction != wanted:
                counters["excluded_favorable_direction"] += 1
                continue
            severity = _trend_severity(pct)

        counters["included"] += 1
        rows.append({
            "signal_id": f"sig-trend-{_sha(d['lei'], tag, d['period_end'])}",
            "lei": d["lei"],
            "signal_type": "trend_delta",
            "observed_at": d["period_end"],
            "severity": severity,
            "source_ref": {
                "tag": tag, "period_end": d["period_end"],
                "prior_period_end": d["prior_period_end"],
                "value": d["value"], "prior_value": d["prior_value"],
                "pct_change": pct,
            },
            "provenance": "public",
        })
    return rows, counters


def _divergence_windows_by_instrument() -> dict[str, list[tuple[date, date]]]:
    """{instrument_id: [(start, end), ...]} from Wave 11a's DIVERGENCES
    literal (`generators/narrative_wave11a.py`) — the four "spread widened,
    grade held" trapezoid windows. Read, never modified: this is ground
    truth for one of the four phases a widening episode can actually be."""
    windows: dict[str, list[tuple[date, date]]] = defaultdict(list)
    for dv in DIVERGENCES:
        windows[dv["instrument_id"]].append((dv["start"], dv["end"]))
    return dict(windows)


def _phase_for_trend_event(instrument_id: str, observed_at: date, lei: str,
                            divergence_windows: dict[str, list[tuple[date, date]]],
                            crossings_by_lei: dict[str, list[dict]]) -> str:
    """Ground-truth phase for a rolling-idiosyncratic-trend candidate event.

    NOT a detection decision — a labelling one (CLAUDE.md: produce the data
    the Assembly Recipe needs, never the runtime detector). We already read
    the grade chains to build `crossings_by_lei`
    (`generate_spreads.load_band_crossings`, keyed on `asserted_at`, the
    announcement date per `wave11a-migration-transition-design.md` decision
    5) and the DIVERGENCES windows, so ground truth is available and is
    used directly rather than inferred from the rolling-window heuristic
    that only ever detects "idiosyncratic_bp trended up" and cannot by
    itself tell anticipation, the post-announcement discontinuity (design
    §3.3: the ramp is CONSUMED by the announcement, not merely followed by
    it), a Wave 11a divergence trapezoid, and AR(1) noise apart.

    Four outcomes, checked in this order:
      1. `divergence`    — the event date falls inside THIS instrument's
                            DIVERGENCES window. A real, different, engineered
                            condition (divergence-with-grade-held), not
                            migration anticipation — checked first because it
                            is unconditional ground truth, independent of
                            whether the obligor ever crosses a band at all.
      2. `anticipation`  — the obligor has a real crossing, and this event's
                            date is STRICTLY BEFORE that crossing's
                            `asserted_at` (the nearest one, by date, if the
                            obligor crosses more than once).
      3. `confirmation`  — the obligor has a real crossing, and this event's
                            date is AT OR AFTER the nearest one's
                            `asserted_at`. This is what the post-announcement
                            discontinuity produces: idiosyncratic_bp's step
                            back toward zero at `M` briefly re-crosses the
                            rolling-trend threshold from the other side, 1-3
                            weeks after the (possibly upgrade) crossing it
                            followed — a real artifact of a real mechanism,
                            just not the one "anticipation" would claim.
      4. `unattributed`  — no crossing exists anywhere in this obligor's
                            grade chain. Ordinary AR(1) noise crossing the
                            sector threshold by chance. Kept, not dropped and
                            not mislabelled — the row and its magnitude are
                            real; only their cause is unknown.
    """
    for start, end in divergence_windows.get(instrument_id, []):
        if start <= observed_at <= end:
            return "divergence"
    crossings = crossings_by_lei.get(lei)
    if not crossings:
        return "unattributed"
    nearest = min(crossings,
                  key=lambda x: abs((x["asserted_at"] - observed_at).days))
    # BOUNDARY, pinned (fix round 2): an event dated EXACTLY on the
    # crossing's own asserted_at is "confirmation", not "anticipation" --
    # `<`, not `<=`. Anticipation is by definition something that precedes
    # the fact it anticipates; the announcement date is the day the fact
    # became known, so an event ON that date is contemporaneous with the
    # announcement, not ahead of it. No row in the loaded artifact lands
    # exactly on this boundary (see test_signals.py's check_rollup_and_phase
    # for the pinned case), so this comparison operator was previously
    # unverified by data, by hand inspection, and by anything downstream.
    return "anticipation" if observed_at < nearest["asserted_at"] else "confirmation"


def _candidate_kind(source_ref: dict) -> str:
    """Which detector produced a spread_widening candidate, read off its
    distinctive field rather than tracked as a separate attribute -- used
    only by `_rollup_to_obligor`'s collision guard, immediately below."""
    if "delta_bp" in source_ref:
        return "confirm"
    if "rolling_mean_delta_bp" in source_ref:
        return "trend"
    raise AssertionError(
        f"candidate source_ref carries neither detector's signature field "
        f"(delta_bp / rolling_mean_delta_bp): {source_ref!r}")


def _rollup_to_obligor(candidates: list[dict]) -> list[dict]:
    """Collapse instrument-level candidate events to one row per
    (lei, observed_at, phase): 79% of the pre-fix rows (34/43) were
    duplicated pairs — the same obligor-level episode counted twice because
    each obligor carries 2 instruments that both react to the same date.
    A downstream composite summing severities would double-weight every one
    of those dates.

    Keeps the max-severity candidate's own fields (its detector-specific
    detail — delta_bp, rolling_mean_delta_bp, market_oas_bp,
    idiosyncratic_bp — describes THAT instrument, not an average), and
    folds every collapsed instrument_id into `source_ref["instrument_ids"]`
    so nothing is lost, per the fix's explicit requirement.

    COLLISION GUARD (fix round 2). Grouping is on (lei, observed_at, phase),
    which is new collision surface since the phase fix: before ground-truth
    labelling, the confirm detector was always "confirmation" and the trend
    detector was always "anticipation", so the two could never land in the
    same group and a cross-detector merge was structurally impossible. Now
    a trend-detector candidate CAN carry "confirmation" (the
    post-announcement discontinuity), so a confirm-detector candidate and a
    trend-detector candidate could in principle share a
    (lei, observed_at, phase) key. Silently picking the max-severity winner
    in that case would DROP the other detector's distinct fields
    (delta_bp/market_oas_bp vs. rolling_mean_delta_bp/idiosyncratic_bp) with
    no trace -- exactly the kind of silent data loss this estate exists to
    avoid. Measured: 0 of the 17 grouped keys in the current 26-row dataset
    mix detector kinds. Rather than leave that as an unverified assumption,
    every group is checked and a real collision RAISES, naming the key,
    instead of merging quietly. See `test_rollup_rejects_cross_detector_
    collision` for a fixture that forces this path.
    """
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for c in candidates:
        groups[(c["lei"], c["observed_at"], c["source_ref"]["phase"])].append(c)

    rows = []
    for (lei, observed_at, phase), members in groups.items():
        kinds = {_candidate_kind(m["source_ref"]) for m in members}
        if len(kinds) > 1:
            raise AssertionError(
                f"cross-detector collision at (lei={lei!r}, "
                f"observed_at={observed_at!r}, phase={phase!r}): "
                f"detector kinds {sorted(kinds)} would merge into one row "
                "and silently drop one detector's distinct fields -- see "
                "_rollup_to_obligor's COLLISION GUARD comment")
        members.sort(key=lambda c: c["severity"], reverse=True)
        winner = members[0]
        source_ref = dict(winner["source_ref"])
        source_ref["instrument_ids"] = sorted(
            {m["source_ref"]["instrument_id"] for m in members})
        source_ref.pop("instrument_id", None)
        source_ref["collapsed_row_count"] = len(members)
        rows.append({
            "signal_id": f"sig-spread-{phase}-{_sha(lei, observed_at, phase)}",
            "lei": lei,
            "signal_type": "spread_widening",
            "observed_at": observed_at,
            "severity": winner["severity"],
            "source_ref": source_ref,
            "provenance": winner["provenance"],
        })
    return rows


def _spread_widening_rows(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(f'SELECT instrument_id, lei FROM "{S}".debt_instrument')
        inst_lei = dict(cur.fetchall())
        cur.execute(f'SELECT lei, sic FROM "{S}".legal_entity')
        sic_by_lei = dict(cur.fetchall())
        cur.execute(
            f'SELECT sector, threshold_bp FROM "{S}".divergence_threshold '
            "WHERE policy_version = %s", ("wave11a-v1",))
        threshold_by_sector = {sec: float(bp) for sec, bp in cur.fetchall()}
        cur.execute(
            f'SELECT instrument_id, obs_date, market_oas_bp, idiosyncratic_bp '
            f'FROM "{S}".spread_observation ORDER BY instrument_id, obs_date')
        obs = cur.fetchall()

    by_inst: dict[str, list[tuple]] = defaultdict(list)
    for inst, obs_date, moas, idio in obs:
        by_inst[inst].append((obs_date, float(moas), float(idio)))

    # Ground truth, read once: which instrument sits in which DIVERGENCES
    # window, and each obligor's real band crossings (asserted_at order).
    divergence_windows = _divergence_windows_by_instrument()
    crossings_by_lei = load_band_crossings()

    default_threshold = threshold_by_sector.get("Unclassified", 100.0)
    candidates: list[dict] = []
    for inst, series in by_inst.items():
        lei = inst_lei.get(inst)
        if lei is None:
            continue
        sector = sector_for(sic_by_lei.get(lei))
        threshold_bp = threshold_by_sector.get(sector, default_threshold)
        anticip_thresh = ANTICIPATION_FRACTION * threshold_bp
        confirm_thresh = CONFIRMATION_FRACTION * threshold_bp

        series.sort(key=lambda p: p[0])
        dates = [p[0] for p in series]
        moas_vals = [p[1] for p in series]
        idio_vals = [p[2] for p in series]

        # CONFIRMATION CANDIDATE: a single-day rise in the real market leg.
        # Adverse (widening) direction only — a band-improving jump
        # (upgrade) is good news and correctly produces no warning. Always
        # phase "confirmation": it is a real, dated, public jump in the
        # published index, whether or not it lines up with one of this
        # obligor's own crossings (a market-wide OAS move confirms real
        # index-level stress regardless), so no ground-truth relabelling
        # applies here — only the trend/idiosyncratic detector below made
        # an engineered-mechanism claim strong enough to need one.
        for i in range(1, len(moas_vals)):
            jump = moas_vals[i] - moas_vals[i - 1]
            if jump < confirm_thresh:
                continue
            candidates.append({
                "lei": lei,
                "observed_at": dates[i].isoformat(),
                "severity": round(min(1.0, jump / (2 * confirm_thresh)), 4),
                "source_ref": {
                    "instrument_id": inst, "phase": "confirmation",
                    "delta_bp": round(jump, 2), "sector": sector,
                    "threshold_bp": threshold_bp,
                    "market_oas_bp": moas_vals[i],
                },
                # market_oas_bp is the real, public leg (Wave 11a §3.1) —
                # deriving a threshold-crossing FROM it stays public.
                "provenance": "public",
            })

        # WIDENING-TREND CANDIDATE: a sustained rise in the rolling mean of
        # the engineered leg, edge-triggered so one continuing episode
        # emits one row. Never references market_oas_bp or a paired band
        # series — a pure trend detector over idiosyncratic_bp's own
        # history, so it cannot reconstruct alpha = 1 - jump/gap even by
        # accident. What phase this becomes (anticipation / confirmation /
        # divergence / unattributed) is decided from ground truth below,
        # NOT asserted here — see `_phase_for_trend_event`.
        active = False
        for i in range(2 * ROLL_WINDOW, len(idio_vals)):
            recent = statistics.mean(idio_vals[i - ROLL_WINDOW:i])
            prior = statistics.mean(idio_vals[i - 2 * ROLL_WINDOW:i - ROLL_WINDOW])
            trend = recent - prior
            over = trend >= anticip_thresh
            if over and not active:
                phase = _phase_for_trend_event(
                    inst, dates[i], lei, divergence_windows, crossings_by_lei)
                candidates.append({
                    "lei": lei,
                    "observed_at": dates[i].isoformat(),
                    "severity": round(min(1.0, trend / (2 * anticip_thresh)), 4),
                    "source_ref": {
                        "instrument_id": inst, "phase": phase,
                        "rolling_mean_delta_bp": round(trend, 2), "sector": sector,
                        "threshold_bp": threshold_bp,
                        "idiosyncratic_bp": idio_vals[i],
                    },
                    # idiosyncratic_bp is synthetic — engineered (Wave 11a
                    # carries the manufactured ramp there) REGARDLESS of
                    # which of the four phases this event lands in — a
                    # divergence-window or unattributed-noise event is
                    # still measured off the engineered leg. Deriving an
                    # engineered quantity from public inputs does not make
                    # it public — wave11a-migration-transition-design.md §3.1.
                    "provenance": "synthetic — engineered",
                })
            active = over

    return _rollup_to_obligor(candidates)

def signal_rows() -> list[dict]:
    """The unified ledger: every signal from every source, one row shape."""
    doc_8k = _load("wave11b_8k_events.json")
    doc_warn = _load("wave11b_warn.json")
    doc_gdelt = _load("wave11b_gdelt.json")
    doc_trend = _load("wave11b_trend_deltas.json")

    rows: list[dict] = []
    rows += _8k_rows(doc_8k)
    rows += _warn_rows(doc_warn)
    media_rows, _dedup = _adverse_media_rows(doc_gdelt)
    rows += media_rows
    trend_rows, _counters = _trend_delta_rows(doc_trend)
    rows += trend_rows

    with pg_connect() as conn:
        rows += _spread_widening_rows(conn)

    rows.sort(key=lambda r: (r["lei"], r["observed_at"], r["signal_type"]))
    return rows


# --- weights (signal_type x sector) -----------------------------------------
# Originated policy: BASE_WEIGHT is a credit-surveillance prior over the
# five signal types independent of sector (sums to 1.0 — an interpretable
# starting allocation, not a probability model fit to anything);
# SECTOR_MULTIPLIER then adjusts for where each type is more or less
# informative. Both are inventions, labelled synthetic — internal, exactly
# like `divergence_threshold`'s sector bucketing precedent.
BASE_WEIGHT: dict[str, float] = {
    "8k_event": 0.30,
    "spread_widening": 0.25,
    "warn_notice": 0.20,
    "adverse_media": 0.15,
    "trend_delta": 0.10,
}

# WARN layoffs are a stronger signal for labor-intensive operating
# businesses than for finance/holding companies.
_LABOR_INTENSIVE = {"Retail Trade", "Services",
                     "Transportation, Communications & Utilities",
                     "Manufacturing", "Construction"}
# Adverse press matters more for consumer-facing and reputation-sensitive
# sectors.
_REPUTATION_SENSITIVE = {"Retail Trade", "Services",
                          "Finance, Insurance & Real Estate"}
# Spread widening is priced uniformly, but capital-intensive / rate-sensitive
# sectors move on it a little more.
_CAPITAL_INTENSIVE = {"Finance, Insurance & Real Estate", "Mining",
                       "Transportation, Communications & Utilities"}
# Balance-sheet deterioration (debt/asset tags) matters most where the
# balance sheet itself is the business.
_BALANCE_SHEET_SENSITIVE = {"Manufacturing", "Mining",
                             "Transportation, Communications & Utilities",
                             "Construction"}


def _sector_multiplier(signal_type: str, sector: str) -> float:
    if signal_type == "warn_notice":
        return 1.30 if sector in _LABOR_INTENSIVE else 0.70
    if signal_type == "adverse_media":
        return 1.30 if sector in _REPUTATION_SENSITIVE else 0.80
    if signal_type == "spread_widening":
        return 1.15 if sector in _CAPITAL_INTENSIVE else 1.00
    if signal_type == "trend_delta":
        return 1.20 if sector in _BALANCE_SHEET_SENSITIVE else 0.90
    if signal_type == "8k_event":
        return 1.10 if sector == "Finance, Insurance & Real Estate" else 1.00
    return 1.00


def _weights(sectors_present: list[str]) -> list[dict]:
    rows = []
    for st in SIGNAL_TYPES:
        for sector in sectors_present:
            mult = _sector_multiplier(st, sector)
            rows.append({
                "signal_type": st, "sector": sector,
                "weight": round(BASE_WEIGHT[st] * mult, 4),
                "policy_version": POLICY_VERSION,
                "rationale": (
                    f"originated in generators/generate_signals.py; "
                    f"base {BASE_WEIGHT[st]} x sector multiplier {mult} "
                    "-- not derived from any upstream artifact"),
                "provenance": "synthetic — internal",
            })
    return rows


# --- thresholds (escalation, per intent; materiality/detection, inspectable) -
# Three escalation intents, increasingly conservative — the same "policy
# bound to intent" shape as generate_exposure.py's LIMIT_DEFINITIONS /
# limit_definition table. threshold_score sits on the composite-score scale
# a downstream consumer computes as sum(severity * weight) over active
# (undecayed) signals; the values below are round multiples of "one
# high-severity signal's own weighted contribution" (~0.30 for an Item 2.04
# at severity 1.0, base weight 0.30) so a reader can sanity-check them
# without running the composite calculation.
ESCALATION_THRESHOLDS = [
    {"intent": "daily-sweep", "threshold_score": 0.30,
     "rationale": "~one high-severity single signal (e.g. an Item 2.04 at "
                  "severity 1.0, weight ~0.30) -- routine automated sweep, "
                  "most sensitive tier; this is the tier the composite case "
                  "(3 subthreshold signals combining) is built to clear"},
    {"intent": "credit-committee-referral", "threshold_score": 0.55,
     "rationale": "~two independent high-severity signals combining -- "
                  "escalates to a human reviewer"},
    {"intent": "board-risk-report", "threshold_score": 0.85,
     "rationale": "~three independent high-severity signals combining -- "
                  "reserved for the most severe composite cases"},
]


def _thresholds(trend_counters: dict, dedup_by_lei: dict) -> list[dict]:
    """Escalation thresholds (kind=escalation) plus every other originated
    numeric policy this module applies, written out as inspectable rows —
    materiality, direction, down-weighting and spread-detection fractions
    alike — per the brief's instruction to keep policy in the policy
    tables, not buried in code."""
    rows = []
    for t in ESCALATION_THRESHOLDS:
        rows.append({
            "kind": "escalation", "intent": t["intent"],
            "threshold_score": t["threshold_score"],
            "rationale": t["rationale"],
            "policy_version": POLICY_VERSION,
            "provenance": "synthetic — internal",
        })

    rows.append({
        "kind": "trend_delta_materiality",
        "threshold_pct": TREND_MATERIALITY_PCT,
        "rationale": (
            "|pct_change| must be >= this AND in the adverse direction for "
            "its tag (see ADVERSE_DIRECTION) to become a signal_event; "
            "chosen at roughly the measured 80th percentile of the "
            "3,705-row reference table's |pct_change| distribution "
            f"(p75=25.0, p80=33.5, p90=73.4). {trend_counters['included']} "
            f"of {trend_counters['total']} reference deltas were admitted: "
            f"{trend_counters['excluded_below_threshold']} excluded below "
            f"threshold, {trend_counters['excluded_favorable_direction']} "
            f"excluded as favorable-direction, "
            f"{trend_counters['excluded_neutral_tag']} excluded as a "
            f"direction-neutral tag, {trend_counters['excluded_zero_to_zero']} "
            "excluded as a genuine zero-to-zero (no real change), "
            f"{trend_counters['included_from_none_prior']} admitted from an "
            "undefined (zero-prior) pct_change on the strength of direction "
            "alone."),
        "policy_version": POLICY_VERSION,
        "provenance": "synthetic — internal",
    })

    down_weighted = {
        lei: r for lei, r in dedup_by_lei.items() if r.get("down_weight_factor")
    }
    rows.append({
        "kind": "adverse_media_down_weight",
        "rule": "severity *= (precision_review.sampled - .off_topic) / .sampled "
                "for any LEI coverage flags recommended_use == 'down_weight'",
        "affected_leis": sorted(down_weighted),
        "policy_version": POLICY_VERSION,
        "provenance": "synthetic — internal",
    })

    rows.append({
        "kind": "spread_detection", "signal_type": "spread_widening",
        "roll_window_obs": ROLL_WINDOW,
        "anticipation_fraction_of_sector_threshold": ANTICIPATION_FRACTION,
        "confirmation_fraction_of_sector_threshold": CONFIRMATION_FRACTION,
        "rationale": (
            "confirmation = single-day market_oas_bp rise >= this fraction "
            "of the obligor's sector divergence_threshold_bp; anticipation "
            "= rolling-mean(idiosyncratic_bp, ROLL_WINDOW) rise vs. the "
            "prior ROLL_WINDOW block >= this fraction. Calibrated against "
            "measured baseline noise (p95 day-over-day market_oas_bp ~10bp, "
            "p95 20-vs-20 idiosyncratic_bp rolling delta ~7bp) and the four "
            "real loaded crossings (confirmation jumps measured 92-150bp)."),
        "policy_version": POLICY_VERSION,
        "provenance": "synthetic — internal",
    })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc_8k = _load("wave11b_8k_events.json")
    doc_warn = _load("wave11b_warn.json")
    doc_gdelt = _load("wave11b_gdelt.json")
    doc_trend = _load("wave11b_trend_deltas.json")

    rows_8k = _8k_rows(doc_8k)
    rows_warn = _warn_rows(doc_warn)
    rows_media, dedup_by_lei = _adverse_media_rows(doc_gdelt)
    rows_trend, trend_counters = _trend_delta_rows(doc_trend)
    with pg_connect() as conn:
        rows_spread = _spread_widening_rows(conn)

        with conn.cursor() as cur:
            cur.execute(f'SELECT lei, sic FROM "{S}".legal_entity ORDER BY lei')
            all_leis_sic = cur.fetchall()
            cur.execute(f'SELECT DISTINCT lei FROM "{S}".debt_instrument')
            spread_addressable_leis = {row[0] for row in cur.fetchall()}

    all_signals = (rows_8k + rows_warn + rows_media + rows_trend + rows_spread)
    all_signals.sort(key=lambda r: (r["lei"], r["observed_at"], r["signal_type"]))

    sectors_present = sorted({sector_for(sic) for _lei, sic in all_leis_sic})
    weights = _weights(sectors_present)
    thresholds = _thresholds(trend_counters, dedup_by_lei)

    # --- composition report: per type, per obligor, never only the total ---
    print(f"Wave 11b Task 7 — unified signal ledger\n")
    print(f"  TOTAL signal_event rows: {len(all_signals)}\n")

    by_type: dict[str, int] = defaultdict(int)
    for r in all_signals:
        by_type[r["signal_type"]] += 1
    print("  by signal_type:")
    for st in SIGNAL_TYPES:
        print(f"    {st:18} {by_type.get(st, 0):>6}")

    by_lei: dict[str, int] = defaultdict(int)
    for r in all_signals:
        by_lei[r["lei"]] += 1
    all_leis = sorted({lei for lei, _sic in all_leis_sic})
    zero_signal_leis = [lei for lei in all_leis if by_lei.get(lei, 0) == 0]
    print(f"\n  by obligor (LEI), {len(all_leis)} total:")
    for lei in all_leis:
        print(f"    {lei}: {by_lei.get(lei, 0)}")
    print(f"\n  obligors with ZERO signals: {len(zero_signal_leis)} "
          f"{zero_signal_leis}")

    print(f"\n  trend_delta materiality gate ({TREND_MATERIALITY_PCT}% + "
          f"adverse direction):")
    for k, v in trend_counters.items():
        print(f"    {k:28} {v}")

    print(f"\n  adverse_media dedup (raw mentions -> distinct on-topic-title "
          f"clusters), by obligor:")
    for lei in sorted(dedup_by_lei):
        d = dedup_by_lei[lei]
        flag = ""
        if d.get("raw", 0) and d["raw"] != d["distinct"]:
            ratio = d["raw"] / d["distinct"]
            flag = f"  (x{ratio:.2f} amplification)" if ratio >= 1.3 else ""
        print(f"    {lei}: {d['raw']:>4} raw -> {d['distinct']:>4} distinct{flag}")

    spread_phase = defaultdict(int)
    for r in rows_spread:
        spread_phase[r["source_ref"]["phase"]] += 1
    spread_firing_leis = {r["lei"] for r in rows_spread}
    print(f"\n  spread_widening by phase: {dict(spread_phase)}")
    print(f"  spread_widening addressable population: "
          f"{len(spread_addressable_leis)} obligors carry a Wave 11a debt "
          f"instrument; {len(spread_firing_leis)} of those actually fire "
          f"a spread_widening row")

    print(f"\n  weights minted: {len(weights)} "
          f"({len(SIGNAL_TYPES)} signal types x {len(sectors_present)} sectors)")
    print(f"  thresholds minted: {len(thresholds)}")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    (SCREEN / "wave11b_signals.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": (
            "derived from wave11b_8k_events.json, wave11b_warn.json, "
            "wave11b_gdelt.json, wave11b_trend_deltas.json, and "
            f'"{S}".spread_observation -- no fetch. weights and thresholds '
            "are ORIGINATED here (synthetic -- internal), see module docstring."),
        "_inputs": record_inputs(*INPUT_ARTIFACTS),
        "decay_days": DECAY_DAYS,
        "signals": all_signals,
        "weights": weights,
        "thresholds": thresholds,
    }, indent=2, default=str))
    print("\n  wrote sources/screening/wave11b_signals.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
