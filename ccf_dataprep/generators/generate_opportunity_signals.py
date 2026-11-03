#!/usr/bin/env python3
"""Wave 16 Task 10 — assemble the opportunity signal layer.

Every fetched Wave 16 source, plus the inherited institutional/GDELT/spread
layers, becomes ONE flat ledger of `{signal_id, lei, signal_type, observed_at,
asserted_at, magnitude, source_ref, supersedes, is_current, provenance}` rows
that `ccf.ib_rank`'s decay function (built in a later task) reads directly.
This module does no ranking and no decay math -- only assembly.

THREE RULES THIS MODULE EXISTS TO ENFORCE, each stated once here rather than
scattered across builders:

1. ACTIVIST-STAKE DIRECTION. A Schedule 13D is filed BY an activist ABOUT a
   subject company. `wave16_13d.json` carries 963 rows with a `role` resolved
   per filing: SUBJECT (427), FILER (44), UNKNOWN (492, all pre-2011, where
   EDGAR's archive predates the header layout the resolver reads). Only
   `role == "SUBJECT"` becomes an `activist_stake_13d` signal. Reading a
   FILER row as "an activist took a stake in the anchor" inverts the signal
   -- it is the anchor that took the stake -- and that exact inversion is
   what disqualified this product's original centrepiece prospect (Boston
   Omaha Corp, an activist holding company that FILES 13Ds; see
   `docs/wave16-design.md` §6.1). UNKNOWN is excluded too: an unresolved
   direction is not a confirmed SUBJECT, and must not be treated as one just
   because it is not FILER. FILER and UNKNOWN counts are printed, never
   silently absorbed.

2. NO FUTURE-DATED SIGNALS. `fetch_schedule13d.py` applies no date filter, so
   a filing dated after the pinned `AS_OF_IB` could in principle reach this
   generator (none currently do -- checked below -- but the filter is not
   conditioned on that being true today). `ccf.ib_rank.decay()` clamps
   negative age to 1.0 as a defence against clock skew, which is a CAP, not a
   FILTER: relying on the clamp would let a future-dated filing score the
   maximum possible weight and dominate every ranking it entered. Every
   public-source builder below drops `observed_at > AS_OF_IB` and counts what
   it dropped; the count is printed even when it is zero, so the absence of
   the defect is demonstrated rather than assumed.

3. REAL DATES ARE NEVER SHIFTED; ONLY SYNTHETIC ONES ARE WINDOW-DATED. A
   filing date, a report period, an article's `seendate`, an award's
   `start_date` are public facts and are copied verbatim into `observed_at`
   -- no arithmetic on them, ever. The one signal type with no natural
   single anchor date -- `institutional_positioning_13f`, a POSITIONING
   DELTA computed by us between two real 13F report periods, not itself a
   filed document -- is dated with a seeded `random.Random`, uniformly
   across `IB_WINDOW_START..IB_WINDOW_END`, so a rerun reproduces the same
   dates. `banker_local_note`, the other synthetic-internal example named in
   the brief, is Task 13's job and is deliberately absent here.

## `asserted_at` vs `observed_at`

For a signal whose assertion IS the filing itself -- a discrete, per-event
catalyst (13D, 8-K, merger doc, S-4) -- the filed document both happened and
was asserted on the same day: `asserted_at == observed_at == filing_date`.

Every other type is something WE computed at load time, not a document that
was itself filed, so `asserted_at == AS_OF_IB` while `observed_at` still
carries whatever real date underlies the computation:
`institutional_positioning_13f`'s delta, `maturity_wall`'s ratio,
`spread_trajectory`'s 90-day change, and `gov_revenue_concentration`'s share
each use the latest real report period / observation / award start date
respectively. `insider_activity_form4` and `sector_news_gdelt` (fix round 1)
are monthly AGGREGATES -- nobody asserted a (lei, month) bucket on the date
of its newest member; this generator asserted it today, when it computed the
bucket. `observed_at` on those two stays the latest real filing/story date
inside the month (VALID time: when the activity happened); `asserted_at` is
`AS_OF_IB` (ASSERTION time: when we recorded it) -- fix round 2, corrected
from an earlier `asserted_at = observed_at` that conflated the two.

## Magnitude, normalised to [0, 1] per type

Discrete "did this filing happen" event types (13D, 8-K, merger doc, S-4,
Form 4) carry magnitude `1.0` uniformly: an event either occurred or it did
not, and there is no principled within-type continuum to scale against (13D
is `1.0` by the brief's own example). The four DERIVED types are scaled
against a real quantity per the brief and the design doc:
  - `maturity_wall`      = min(1, face_amount_maturing_within_24m / total_face)
  - `spread_trajectory`  = min(1, |90-day change in spread_bp| / 200)
  - `gov_revenue_concentration` = min(1, this obligor's award total /
                                    the grand total across all obligors) --
    literally "concentration": Granite Construction's ~96% share is why the
    signal is named that, not "revenue size".
  - `institutional_positioning_13f` = min(1, |pct change in aggregate 13F
                                    value between consecutive report periods|
                                    / 0.50)

## Fix round 1 (coordinator ruling, both findings from ranking the real data)

FINDING 1 -- supersession must stop a signal from scoring, not just be
recorded. Every signal now carries `is_current`: False if some OTHER
signal's `supersedes` names it, True otherwise. Nothing is deleted --
history stays in the artifact for replay -- but a current-value ranking
query is expected to filter to `is_current == True`. Computed from the
supersession graph itself (which signal_ids appear as someone else's
`supersedes`), not from "newest per entity by date": a chain can fork, and
only a graph read sees that correctly.

FINDING 2 -- `insider_activity_form4` and `sector_news_gdelt` are REPEATED-
OBSERVATION types (a busy obligor can generate dozens of same-magnitude
rows), not discrete one-off catalysts like a 13D or an S-4. Building one
full-magnitude (`1.0`) signal per filing/story let raw paperwork/press
VOLUME stand in for signal STRENGTH -- insider filings alone were 41.5% of
all M&A score mass, earned purely by filing frequency. Both types are now
aggregated to ONE signal per (lei, calendar month); magnitude is that
month's count normalised to [0, 1] against the busiest entity-month for
that type (so the single busiest obligor-month scores 1.0). `observed_at`
is the LATEST REAL underlying date inside the month -- not a synthetic
month-end marker -- both because rule 3 keeps every real-source date
genuine rather than fabricated, and because a month-end date for the
current, still-open month could land after `AS_OF_IB` for no real reason.
The four already-one-per-entity derived types (`institutional_positioning_13f`,
`maturity_wall`, `spread_trajectory`, `gov_revenue_concentration`) and the
four genuinely discrete catalyst types (`activist_stake_13d`, `ma_event_8k`,
`merger_proxy`, `registration_s4`) are unchanged.

    uv run generators/generate_opportunity_signals.py --dry-run
    uv run generators/generate_opportunity_signals.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from ccf.config import AS_OF_IB, IB_WINDOW_END, IB_WINDOW_START
from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import REPO_ROOT, pg_connect
from ccf.currency import verify_current

SCREEN = REPO_ROOT / "sources" / "screening"

#: Every signal type this module must produce, excluding `banker_local_note`
#: (Task 13's job -- see `generate_ib_perspectives.SIGNAL_CLASSES`).
SIGNAL_TYPES = (
    "activist_stake_13d", "ma_event_8k", "merger_proxy", "registration_s4",
    "insider_activity_form4", "institutional_positioning_13f",
    "maturity_wall", "spread_trajectory", "sector_news_gdelt",
    "gov_revenue_concentration",
)

_AS_OF = date.fromisoformat(AS_OF_IB)
_WINDOW_START = date.fromisoformat(IB_WINDOW_START)
_WINDOW_END = date.fromisoformat(IB_WINDOW_END)

#: 13D amendment forms across both EDGAR form-name eras.
_13D_AMENDMENT_FORMS = {"SCHEDULE 13D/A", "SC 13D/A"}
#: 8-K items that read as M&A signals, not the broader credit-surveillance
#: item set `fetch_8k_items.ITEM_CODES` fetches. 2.01 is COMPLETION of an
#: acquisition/disposition (definitive); 1.01 is entry into a material
#: definitive agreement (announced, less certain -- scored lower).
_8K_MA_ITEM_MAGNITUDE = {"2.01": 1.0, "1.01": 0.6}

#: 50% swing in an obligor's aggregate 13F value between two consecutive
#: report periods saturates the positioning-delta signal at full strength.
_POSITIONING_DELTA_SCALE = 0.50
#: 200bp move in spread_bp over 90 days saturates the spread signal, per brief.
_SPREAD_SCALE_BP = 200.0
#: 24-month refinancing horizon a DCM banker works to, per the design doc.
_MATURITY_WALL_MONTHS = 24

#: Fixed seed so `institutional_positioning_13f`'s window dates reproduce on
#: a rerun -- rule 3 above.
_RNG_SEED = "wave16-ib-signals-v1"


def _sha(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def _sig_id(kind: str, *parts: object) -> str:
    return f"sig-{kind}-{_sha(*parts)}"


def _year_month(d: date) -> str:
    """`YYYY-MM` grouping key for the monthly-aggregated repeated-observation
    types (fix round 1, finding 2)."""
    return f"{d.year:04d}-{d.month:02d}"


def _add_months(d: date, months: int) -> date:
    y, m = d.year + (d.month - 1 + months) // 12, (d.month - 1 + months) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


# ---------------------------------------------------------------------------
# 1. activist_stake_13d -- SUBJECT only, amendments supersede
# ---------------------------------------------------------------------------

def _13d_rows(doc: dict) -> tuple[list[dict], dict[str, int]]:
    filings = doc["filings"]
    drops = {"role_filer": 0, "role_unknown": 0, "post_as_of": 0}

    subject: list[dict] = []
    for f in filings:
        if f["role"] == "FILER":
            drops["role_filer"] += 1
            continue
        if f["role"] == "UNKNOWN":
            drops["role_unknown"] += 1
            continue
        # role == "SUBJECT" from here.
        if date.fromisoformat(f["filing_date"]) > _AS_OF:
            drops["post_as_of"] += 1
            continue
        subject.append(f)

    by_lei: dict[str, list[dict]] = defaultdict(list)
    for f in subject:
        by_lei[f["lei"]].append(f)

    rows: list[dict] = []
    for lei, group in by_lei.items():
        group.sort(key=lambda f: (f["filing_date"], f["accession"]))
        prior_signal_id: str | None = None
        for f in group:
            sig_id = _sig_id("13d", f["accession"])
            supersedes = None
            if f["form"] in _13D_AMENDMENT_FORMS and prior_signal_id is not None:
                supersedes = prior_signal_id
            rows.append({
                "signal_id": sig_id,
                "lei": lei,
                "signal_type": "activist_stake_13d",
                "observed_at": f["filing_date"],
                "asserted_at": f["filing_date"],
                "magnitude": 1.0,
                "source_ref": f["accession"],
                "supersedes": supersedes,
                "provenance": "public",
            })
            prior_signal_id = sig_id
    return rows, drops


# ---------------------------------------------------------------------------
# 2. ma_event_8k -- Items 1.01 / 2.01 only, filtered from the broader fetch
# ---------------------------------------------------------------------------

def _8k_rows(doc: dict) -> tuple[list[dict], dict[str, int]]:
    drops = {"post_as_of": 0}
    rows = []
    for e in doc["events"]:
        magnitude = _8K_MA_ITEM_MAGNITUDE.get(e["item"])
        if magnitude is None:
            continue  # not an M&A-relevant item (credit-surveillance item)
        if date.fromisoformat(e["filing_date"]) > _AS_OF:
            drops["post_as_of"] += 1
            continue
        rows.append({
            "signal_id": _sig_id("8k", e["accession"], e["item"]),
            "lei": e["lei"],
            "signal_type": "ma_event_8k",
            "observed_at": e["filing_date"],
            "asserted_at": e["filing_date"],
            "magnitude": magnitude,
            "source_ref": {"accession": e["accession"], "item": e["item"]},
            "supersedes": None,
            "provenance": "public",
        })
    return rows, drops


# ---------------------------------------------------------------------------
# 3/4. merger_proxy (DEFM14A / PREM14A) and registration_s4 (S-4 / S-4/A)
# ---------------------------------------------------------------------------

_MERGER_PROXY_MAGNITUDE = {"DEFM14A": 1.0, "PREM14A": 0.6}
_S4_FORMS = {"S-4", "S-4/A"}


def _merger_doc_rows(doc: dict) -> tuple[list[dict], list[dict], dict[str, int]]:
    drops = {"post_as_of": 0}
    proxy_rows, s4_rows = [], []
    for d in doc["documents"]:
        if date.fromisoformat(d["filing_date"]) > _AS_OF:
            drops["post_as_of"] += 1
            continue
        base = {
            "lei": d["lei"],
            "observed_at": d["filing_date"],
            "asserted_at": d["filing_date"],
            "source_ref": d["accession"],
            "supersedes": None,
            "provenance": "public",
        }
        if d["form"] in _MERGER_PROXY_MAGNITUDE:
            proxy_rows.append({
                "signal_id": _sig_id("proxy", d["accession"]),
                "signal_type": "merger_proxy",
                "magnitude": _MERGER_PROXY_MAGNITUDE[d["form"]],
                **base,
            })
        elif d["form"] in _S4_FORMS:
            s4_rows.append({
                "signal_id": _sig_id("s4", d["accession"]),
                "signal_type": "registration_s4",
                "magnitude": 1.0,
                **base,
            })
    return proxy_rows, s4_rows, drops


# ---------------------------------------------------------------------------
# 5. insider_activity_form4 -- monthly volume, normalised (fix round 1 #2)
# ---------------------------------------------------------------------------

def _form4_rows(doc: dict) -> tuple[list[dict], dict[str, int]]:
    """One signal per (lei, calendar month). Per-day grouping (the pre-fix
    scheme) produced up to 97 discrete magnitude-1.0 signals for a single
    busy obligor, letting raw filing VOLUME stand in for signal STRENGTH.
    Magnitude here is the month's filing count normalised against the
    busiest entity-month for this type -- see module docstring, finding 2.

    Fix round 2, finding 1c: bounded to the 12-month window, not full
    history. This is an intensity measure ("how much insider activity has
    this obligor had recently"), computed and asserted at AS_OF_IB -- unlike
    the discrete catalyst types, which keep their whole historical record --
    so a filing from 2017 has no business feeding a "current volume" bucket."""
    drops = {"post_as_of": 0, "pre_window": 0}
    by_month: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for lei, info in doc["issuers"].items():
        for f in info.get("filings", []):
            fdate = date.fromisoformat(f["filing_date"])
            if fdate > _AS_OF:
                drops["post_as_of"] += 1
                continue
            if fdate < _WINDOW_START:
                drops["pre_window"] += 1
                continue
            by_month[(lei, _year_month(fdate))].append(
                {"accession": f["accession"], "filing_date": f["filing_date"]})

    if not by_month:
        return [], drops
    max_count = max(len(v) for v in by_month.values())

    rows = []
    for (lei, ym), members in by_month.items():
        # Latest REAL filing date inside the month -- never a synthetic
        # month-end marker (rule 3; also avoids a fabricated boundary date
        # for the current, still-open month landing after AS_OF_IB). This is
        # VALID time (when the activity happened); asserted_at (ASSERTION
        # time, fix round 2) is AS_OF_IB, since nobody asserted this monthly
        # bucket on its newest member's date -- this generator asserted it
        # today, when it computed the aggregate.
        observed_at = max(m["filing_date"] for m in members)
        rows.append({
            "signal_id": _sig_id("f4", lei, ym),
            "lei": lei,
            "signal_type": "insider_activity_form4",
            "observed_at": observed_at,
            "asserted_at": AS_OF_IB,
            "magnitude": round(len(members) / max_count, 4),
            "source_ref": {
                "year_month": ym, "filing_count": len(members),
                "accessions": sorted(m["accession"] for m in members),
            },
            "supersedes": None,
            "provenance": "public",
        })
    return rows, drops


# ---------------------------------------------------------------------------
# 6. institutional_positioning_13f -- a DELTA, dated by seeded RNG in-window
# ---------------------------------------------------------------------------

def _parse_report_period(p: str) -> date:
    return datetime.strptime(p, "%d-%b-%Y").date()


def _institutional_positioning_rows(conn) -> tuple[list[dict], dict[str, int]]:
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT lei, report_period, SUM(value_usd) '
            f'FROM "{S}".institutional_holder GROUP BY lei, report_period')
        raw = cur.fetchall()

    by_lei: dict[str, dict[date, float]] = defaultdict(dict)
    for lei, period, total in raw:
        by_lei[lei.strip()][_parse_report_period(period)] = float(total)

    rng = random.Random(_RNG_SEED)
    window_span = (_WINDOW_END - _WINDOW_START).days

    rows = []
    for lei in sorted(by_lei):
        periods = sorted(by_lei[lei])
        if len(periods) < 2:
            continue  # no delta computable -- absent data, not a zero signal
        latest, prior = periods[-1], periods[-2]
        v_latest, v_prior = by_lei[lei][latest], by_lei[lei][prior]
        if v_prior == 0:
            continue  # undefined pct change from a zero base
        pct_change = (v_latest - v_prior) / v_prior
        magnitude = round(min(1.0, abs(pct_change) / _POSITIONING_DELTA_SCALE), 4)

        observed_at = (_WINDOW_START + timedelta(days=rng.randrange(window_span + 1)))
        rows.append({
            "signal_id": _sig_id("13f", lei, latest.isoformat(), prior.isoformat()),
            "lei": lei,
            "signal_type": "institutional_positioning_13f",
            "observed_at": observed_at.isoformat(),
            "asserted_at": AS_OF_IB,
            "magnitude": magnitude,
            "source_ref": {
                "latest_period": latest.isoformat(), "prior_period": prior.isoformat(),
                "latest_value_usd": v_latest, "prior_value_usd": v_prior,
                "pct_change": round(pct_change, 4),
            },
            "supersedes": None,
            "provenance": "synthetic — internal",
        })
    return rows, {}


# ---------------------------------------------------------------------------
# 7. maturity_wall -- min(1, face maturing within 24m / total face)
# ---------------------------------------------------------------------------

def _maturity_wall_rows(conn) -> tuple[list[dict], dict[str, int]]:
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT lei, instrument_id, maturity, face_amount_usd '
            f'FROM "{S}".debt_instrument')
        rows_raw = cur.fetchall()

    cutoff = _add_months(_AS_OF, _MATURITY_WALL_MONTHS)
    by_lei: dict[str, list[tuple[str, date, float]]] = defaultdict(list)
    for lei, inst, maturity, face in rows_raw:
        by_lei[lei.strip()].append((inst, maturity, float(face)))

    rows = []
    for lei in sorted(by_lei):
        instruments = by_lei[lei]
        total_face = sum(face for _i, _m, face in instruments)
        if total_face <= 0:
            continue  # no debt to compute a ratio over -- absent, not zero
        maturing = sum(face for _i, m, face in instruments if m <= cutoff)
        magnitude = round(min(1.0, maturing / total_face), 4)
        rows.append({
            "signal_id": _sig_id("wall", lei, AS_OF_IB),
            "lei": lei,
            "signal_type": "maturity_wall",
            "observed_at": AS_OF_IB,
            "asserted_at": AS_OF_IB,
            "magnitude": magnitude,
            "source_ref": {
                "as_of": AS_OF_IB, "window_months": _MATURITY_WALL_MONTHS,
                "total_face_usd": total_face, "maturing_within_window_usd": maturing,
                "instrument_ids": sorted(i for i, _m, _f in instruments),
            },
            "supersedes": None,
            "provenance": "synthetic — internal",
        })
    return rows, {}


# ---------------------------------------------------------------------------
# 8. spread_trajectory -- min(1, |90-day change in spread_bp| / 200)
# ---------------------------------------------------------------------------

def _spread_trajectory_rows(conn) -> tuple[list[dict], dict[str, int]]:
    with conn.cursor() as cur:
        cur.execute(f'SELECT instrument_id, lei FROM "{S}".debt_instrument')
        inst_lei = {inst: lei.strip() for inst, lei in cur.fetchall()}
        cur.execute(
            f'SELECT instrument_id, obs_date, spread_bp FROM "{S}".spread_observation '
            f'WHERE obs_date <= %s ORDER BY instrument_id, obs_date', (_AS_OF,))
        obs_raw = cur.fetchall()

    # Obligor-level series: mean spread_bp across that obligor's instruments,
    # per date any of them was observed.
    by_lei_date: dict[str, dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
    for inst, obs_date, spread_bp in obs_raw:
        lei = inst_lei.get(inst)
        if lei is None:
            continue
        by_lei_date[lei][obs_date].append(float(spread_bp))

    rows = []
    for lei in sorted(by_lei_date):
        series = {d: sum(v) / len(v) for d, v in by_lei_date[lei].items()}
        dates = sorted(series)
        if not dates:
            continue
        latest = dates[-1]
        target = latest - timedelta(days=90)
        # nearest obs_date at or before target (closest 90-day-back point).
        priors = [d for d in dates if d <= target]
        if not priors:
            continue  # not enough history yet to measure a trajectory
        prior = priors[-1]
        delta_bp = series[latest] - series[prior]
        magnitude = round(min(1.0, abs(delta_bp) / _SPREAD_SCALE_BP), 4)
        rows.append({
            "signal_id": _sig_id("spread", lei, latest.isoformat()),
            "lei": lei,
            "signal_type": "spread_trajectory",
            "observed_at": latest.isoformat(),
            "asserted_at": AS_OF_IB,
            "magnitude": magnitude,
            "source_ref": {
                "latest_obs_date": latest.isoformat(), "latest_spread_bp": round(series[latest], 3),
                "prior_obs_date": prior.isoformat(), "prior_spread_bp": round(series[prior], 3),
                "delta_bp": round(delta_bp, 3),
            },
            "supersedes": None,
            "provenance": "synthetic — internal",
        })
    return rows, {}


# ---------------------------------------------------------------------------
# 9. sector_news_gdelt -- title-deduped, then monthly volume (fix round 1 #2)
# ---------------------------------------------------------------------------

def _gdelt_date(seendate: str) -> date:
    return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").date()


def _norm_title(title: str) -> str:
    import re
    t = title.lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(t.split())


def _gdelt_rows(conn) -> tuple[list[dict], dict[str, int]]:
    """One signal per (lei, calendar month).

    Two dedup layers, not one. Wire-amplified republication is still
    collapsed to one STORY per (lei, normalised title) first -- a securities
    class action republished by two newswires must not count as two stories
    -- and those distinct stories are then aggregated to one signal per
    (lei, month), magnitude = that month's story count normalised against
    the busiest entity-month for this type. Per-story terminal signals (the
    pre-fix scheme) let raw press VOLUME stand in for strength -- see module
    docstring, finding 2.

    Fix round 2, finding 1c: bounded to the 12-month window, not full
    history, for the same reason as `_form4_rows` -- an intensity measure,
    not a historical record. Filtered on the RAW mention before clustering,
    so a cluster's earliest date can never fall outside the window."""
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT lei, title, seendate, url, domain, down_weight_factor '
            f'FROM "{S}".gdelt_mention')
        raw = cur.fetchall()

    drops = {"post_as_of": 0, "pre_window": 0}
    title_clusters: dict[tuple[str, str], list[tuple]] = defaultdict(list)
    for lei, title, seendate, url, domain, down_weight in raw:
        obs = _gdelt_date(seendate)
        if obs > _AS_OF:
            drops["post_as_of"] += 1
            continue
        if obs < _WINDOW_START:
            drops["pre_window"] += 1
            continue
        title_clusters[(lei.strip(), _norm_title(title))].append(
            (obs, title, url, domain, down_weight))

    stories = []
    for (lei, _norm), members in title_clusters.items():
        members.sort(key=lambda m: m[0])
        obs, title, url, domain, down_weight = members[0]
        stories.append({"lei": lei, "date": obs, "title": title,
                         "down_weight": down_weight})

    by_month: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for st in stories:
        by_month[(st["lei"], _year_month(st["date"]))].append(st)

    if not by_month:
        return [], drops
    max_count = max(len(v) for v in by_month.values())

    rows = []
    for (lei, ym), members in by_month.items():
        # VALID time: latest real story date in the month. asserted_at
        # (ASSERTION time, fix round 2) is AS_OF_IB, not this date -- the
        # (lei, month) bucket is an aggregate this generator computed today,
        # not a document asserted on its newest member's date.
        observed_at = max(m["date"] for m in members)
        magnitude = round(len(members) / max_count, 4)
        down_weights = [float(m["down_weight"]) for m in members
                         if m["down_weight"] is not None]
        if down_weights:
            magnitude = round(magnitude * (sum(down_weights) / len(down_weights)), 4)
        rows.append({
            "signal_id": _sig_id("gdelt", lei, ym),
            "lei": lei,
            "signal_type": "sector_news_gdelt",
            "observed_at": observed_at.isoformat(),
            "asserted_at": AS_OF_IB,
            "magnitude": magnitude,
            "source_ref": {
                "year_month": ym, "story_count": len(members),
                "titles": [m["title"] for m in
                           sorted(members, key=lambda m: m["date"])],
            },
            "supersedes": None,
            "provenance": "public",
        })
    return rows, drops


# ---------------------------------------------------------------------------
# 10. gov_revenue_concentration -- min(1, this obligor's total / grand total)
# ---------------------------------------------------------------------------

def _gov_revenue_rows(doc: dict) -> tuple[list[dict], dict[str, int]]:
    drops = {"post_as_of": 0}
    admitted = []
    for a in doc["awards"]:
        if date.fromisoformat(a["start_date"]) > _AS_OF:
            drops["post_as_of"] += 1
            continue
        admitted.append(a)

    by_lei: dict[str, list[dict]] = defaultdict(list)
    for a in admitted:
        by_lei[a["lei"]].append(a)
    grand_total = sum(a["obligated_usd"] for a in admitted)

    rows = []
    if grand_total > 0:
        for lei, awards in by_lei.items():
            total = sum(a["obligated_usd"] for a in awards)
            magnitude = round(min(1.0, total / grand_total), 4)
            latest = max(a["start_date"] for a in awards)
            rows.append({
                "signal_id": _sig_id("gov", lei, AS_OF_IB),
                "lei": lei,
                "signal_type": "gov_revenue_concentration",
                "observed_at": latest,
                "asserted_at": AS_OF_IB,
                "magnitude": magnitude,
                "source_ref": {
                    "award_ids": sorted(a["award_id"] for a in awards),
                    "obligor_total_usd": total, "grand_total_usd": grand_total,
                },
                "supersedes": None,
                "provenance": "public",
            })
    return rows, drops


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def build() -> dict:
    """Assemble the full signal ledger. No side effects -- reads only."""
    doc_13d, _ = verify_current("wave16_13d.json")
    doc_8k, _ = verify_current("wave11b_8k_events.json")
    doc_merger, _ = verify_current("wave16_merger_docs.json")
    doc_usa, _ = verify_current("wave16_usaspending.json")
    doc_form4, _ = verify_current("wave10_form4_index.json")

    rows_13d, drops_13d = _13d_rows(doc_13d)
    rows_8k, drops_8k = _8k_rows(doc_8k)
    rows_proxy, rows_s4, drops_merger = _merger_doc_rows(doc_merger)
    rows_form4, drops_form4 = _form4_rows(doc_form4)
    rows_gov, drops_gov = _gov_revenue_rows(doc_usa)

    with pg_connect() as conn:
        rows_13f, drops_13f = _institutional_positioning_rows(conn)
        rows_wall, drops_wall = _maturity_wall_rows(conn)
        rows_spread, drops_spread = _spread_trajectory_rows(conn)
        rows_gdelt, drops_gdelt = _gdelt_rows(conn)

    all_rows = (rows_13d + rows_8k + rows_proxy + rows_s4 + rows_form4
                + rows_13f + rows_wall + rows_spread + rows_gdelt + rows_gov)

    # Fix round 1, finding 1: `is_current` for a current-value ranking query.
    # Nothing is deleted -- history stays for replay -- but a signal that
    # some OTHER signal's `supersedes` names is not current. Computed from
    # the supersession graph itself, not "newest per entity by date": a
    # chain can fork, and only a graph read sees that correctly.
    superseded_ids = {r["supersedes"] for r in all_rows if r.get("supersedes")}
    for r in all_rows:
        r["is_current"] = r["signal_id"] not in superseded_ids

    all_rows.sort(key=lambda r: (r["signal_type"], r["lei"], r["observed_at"]))

    drops = {
        "activist_stake_13d.role_filer": drops_13d["role_filer"],
        "activist_stake_13d.role_unknown": drops_13d["role_unknown"],
        "activist_stake_13d.post_as_of": drops_13d["post_as_of"],
        "ma_event_8k.post_as_of": drops_8k["post_as_of"],
        "merger_proxy_and_s4.post_as_of": drops_merger["post_as_of"],
        "insider_activity_form4.post_as_of": drops_form4["post_as_of"],
        "insider_activity_form4.pre_window": drops_form4["pre_window"],
        "gov_revenue_concentration.post_as_of": drops_gov["post_as_of"],
        "sector_news_gdelt.post_as_of": drops_gdelt["post_as_of"],
        "sector_news_gdelt.pre_window": drops_gdelt["pre_window"],
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": (
            "derived from wave16_13d.json, wave11b_8k_events.json, "
            "wave16_merger_docs.json, wave16_usaspending.json, "
            "wave10_form4_index.json, and Postgres institutional_holder / "
            "gdelt_mention / spread_observation / debt_instrument -- no fetch."),
        "as_of": AS_OF_IB,
        "drops": drops,
        "signals": all_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = build()
    signals = doc["signals"]

    print("Wave 16 Task 10 -- opportunity signal ledger\n")
    print(f"  TOTAL signal rows: {len(signals)}\n")

    by_type: dict[str, int] = defaultdict(int)
    for r in signals:
        by_type[r["signal_type"]] += 1

    print("  by signal_type:")
    missing = []
    for st in SIGNAL_TYPES:
        count = by_type.get(st, 0)
        flag = "  <-- ZERO ROWS" if count == 0 else ""
        print(f"    {st:32} {count:>6}{flag}")
        if count == 0:
            missing.append(st)

    extra = set(by_type) - set(SIGNAL_TYPES)
    if extra:
        print(f"\n  UNEXPECTED signal types not in SIGNAL_TYPES: {sorted(extra)}")

    print("\n  dropped rows (must be counted, never silently absorbed):")
    for k, v in doc["drops"].items():
        print(f"    {k:40} {v}")

    provenance_counts: dict[str, int] = defaultdict(int)
    for r in signals:
        provenance_counts[r["provenance"]] += 1
    print("\n  by provenance:")
    for k, v in sorted(provenance_counts.items()):
        print(f"    {k:24} {v}")

    amendments = [r for r in signals if r.get("supersedes")]
    print(f"\n  amendments that supersede a parent: {len(amendments)}")

    current_by_type: dict[str, int] = defaultdict(int)
    superseded_by_type: dict[str, int] = defaultdict(int)
    for r in signals:
        (current_by_type if r["is_current"] else superseded_by_type)[r["signal_type"]] += 1
    total_current = sum(current_by_type.values())
    total_superseded = sum(superseded_by_type.values())
    print(f"\n  is_current (fix round 1): {total_current} current, "
          f"{total_superseded} superseded")
    print("  by signal_type:")
    for st in SIGNAL_TYPES:
        c, sp = current_by_type.get(st, 0), superseded_by_type.get(st, 0)
        if c or sp:
            print(f"    {st:32} current {c:>6}   superseded {sp:>6}")

    if missing:
        print(f"\n  FAIL: {len(missing)} signal type(s) produced ZERO rows: "
              f"{missing}. A silently absent type scores as zero for every "
              f"entity and changes every ranking it should have appeared in, "
              f"with nothing failing.")
        return 1

    if args.dry_run:
        print("\n  --dry-run: nothing written")
        return 0

    SCREEN.mkdir(parents=True, exist_ok=True)
    out = SCREEN / "wave16_signals.json"
    out.write_text(json.dumps(doc, indent=2, default=str))
    print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
