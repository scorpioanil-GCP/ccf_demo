#!/usr/bin/env python3
"""Wave 11b — adverse media mentions via the GDELT DOC 2.0 API.

**The substitution, stated plainly.** `covenant-cross-reference`'s spec (and
this wave's §C) names GDELT's "event and mention streams" — the raw
CAMEO-coded 15-minute CSV files at `data.gdeltproject.org/gdeltv2/`. Twenty-
four months of that is roughly 52,000 files: not tractable, and the cost buys
nothing the product needs. This fetcher substitutes the **GDELT DOC 2.0 API**
(`api.gdeltproject.org/api/v2/doc/doc`), article-level, queried by entity
name, carrying the same 15-minute `seendate` granularity. GDELT's own CAMEO
entity tagging is NOT used here — matching is by name query, which is lossy,
same shape as the WARN employer-name join. See `substitution_note` in the
artifact and `docs/wave11b-design.md` §2.3.

**Throttling, as actually measured.** GDELT answers an over-rate request
with HTTP 429 and the text "Please limit requests to one every 5 seconds."
That stated rate is a FLOOR, not a guarantee. An earlier version of this
script obeyed it exactly, recursively pre-sliced the window per obligor, and
earned a sustained block. Measurements taken while fixing that, on this
machine's IP:

  * 12s between requests -> 2 of 8 succeeded
  * 20s between requests -> 1 of 13 succeeded
  * 30s between requests -> 0 of 7 succeeded
  * 9 minutes of complete silence, then a request -> still 429
  * the same URL retried 13 times in a row -> 429 x12, then 200

So once an IP is in GDELT's penalty state, the 429 is **probabilistic, not
a timed lockout**: waiting longer does not clear it, and cadence barely
moves the success rate. The only thing that works is patience — keep asking
at the stated floor until one gets through. `GDELT_LIMITER` holds the
12-second floor (deliberate headroom over GDELT's stated 5s; do not tune it
down), and `gdelt_get` retries a 429 up to `_MAX_429_ATTEMPTS` times before
RAISING — never swallowing it into an empty result. That distinction is the
whole point: "no adverse coverage" and "we were rate-limited" must never
produce the same artifact (Wave 11a lesson 2 — instability across a sweep is
evidence of incompleteness, not of a changing source).

Consequence for the operator: a full sweep is on the order of an hour or
more of wall clock, most of it spent on 429s. Run it in the foreground and
let it work; if it is interrupted, rerun it and it resumes.

**Resumability**, in the manner of `loaders/embed_passages.py`: the artifact
is written after every obligor, keyed by LEI. `obligors_swept` records every
LEI that has completed a sweep — including ones with zero adverse mentions,
so a quiet obligor is not re-swept forever. A restart skips any LEI already
in `obligors_swept` unless `--force`.

**The window is pre-sliced, and it has to be.** An earlier version issued
one call per obligor across the full 24 months, which looked right — small
result sets, no full pages, no errors. It was silently wrong: GDELT answers
a long range by scanning backwards from `enddatetime` and stopping early,
returning only the trailing ~3 months and stopping well short of
`maxrecords`, so a "did we get exactly 250 back?" test never fires. Proof:
`"TUPPERWARE BRANDS"` over the full window returned zero articles, while the
same query narrowed to 2024-09..2024-11 returns 71 — the Chapter 11 coverage
was there the whole time. See `SLICE_DAYS` for the measurements. The window
is therefore never queried as one span.

**Two phases per obligor.** `mode=timelinevolraw` is NOT clamped — it
returns one bucket per day across all 24 months. So each obligor is first
timelined (one call) to find out exactly which days carry adverse coverage
and how much, and only then are `artlist` calls issued, one per contiguous
run of active days, sized to stay under both the 90-day span limit and the
250-record cap. A quiet obligor costs one call instead of nine, and every
obligor gets an **expected** article count to check the retrieved rows
against — recorded per obligor under `coverage` in the artifact. That check
is the point: a count that came back is not evidence until something
independent says what should have come back. In the run that produced the
artifact the two agreed to within one article in 952.

**Query normalisation (fixed after a real defect).** The first version
quoted the RAW Postgres `legal_name` verbatim, including EDGAR's
state-of-incorporation suffix (`CHARTER COMMUNICATIONS, INC. /MO/`). A
quoted phrase containing `/MO/` cannot match ordinary news prose, so every
query silently returned zero articles — indistinguishable from "no adverse
coverage" while actually meaning "unmatchable query". `_search_name()` below
strips that suffix and trailing corporate-form words before the name is
quoted. `employer_query` in each output row still carries the ORIGINAL
`legal_name` (provenance: which obligor this row belongs to); `gdelt_query`
carries the exact query string sent to the API, so a reader can see both.

    uv run generators/fetch_gdelt.py --dry-run
    uv run generators/fetch_gdelt.py
    uv run generators/fetch_gdelt.py --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.fetch import RateLimiter, SourceManifest, fetch
from generators.fetch_8k_items import WINDOW_END, WINDOW_START, in_window

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT_PATH = SCREEN / "wave11b_gdelt.json"

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

#: Verified by probe: an unthrottled request gets HTTP 429 with an explicit
#: "one every 5 seconds" instruction. Measured afterwards: obeying exactly
#: that rate STILL earned a 25-minute block, so 5s is the rate GDELT states,
#: not the rate it tolerates. 12s is deliberate headroom over the stated
#: floor. It is not what makes the sweep slow — the 429 retries are; the
#: run that produced the artifact made 203 successful calls over roughly
#: three hours of wall clock — 61 timelines and 142 article calls.
GDELT_THROTTLE_SECONDS = 12.0
GDELT_LIMITER = RateLimiter(per_second=1.0 / GDELT_THROTTLE_SECONDS)

#: GDELT's own adverse-tone threshold, per design §2.3 — mentions must be
#: genuinely adverse, not merely name matches.
TONE_FILTER = "tone<-5"
TONE_FILTER_VALUE = "<-5"

#: `mode=artlist` does NOT return a per-article tone score — confirmed by a
#: live probe: the JSON payload carries only url, url_mobile, title,
#: seendate, socialimage, domain, language, sourcecountry. Per-article tone
#: is only exposed by GDELT's aggregate timeline/tonechart modes, not by
#: article-level search. Every row here passed the server-side `tone<-5`
#: filter, so the actual score is provably below -5, but its exact value is
#: not obtainable from this endpoint. Recording the threshold string here
#: rather than fabricating a plausible-looking number: a made-up per-article
#: score would be exactly the kind of silently-wrong data this project
#: exists to avoid producing.

MAXRECORDS = 250

#: `mode=timelinevolraw` returns one bucket per day with the raw count of
#: matching articles — and, unlike `artlist`, it is NOT clamped to the tail
#: of a long range. Verified: "TUPPERWARE BRANDS" tone<-5 over the full
#: 24 months returns 710 daily buckets, 4 of them non-zero, peaking at 45 on
#: 2024-09-18 — the Chapter 11 filing. Those counts sum to exactly the 71
#: articles an `artlist` call over that narrow range returns, which is what
#: makes the timeline usable as an expected total.
TIMELINE_MODE = "timelinevolraw"

#: Expected-article ceiling for one `artlist` slice, kept well under
#: `MAXRECORDS` so a slice cannot be silently cut by the record cap.
MAX_SLICE_VOLUME = 180

#: Retry budget for a persistent 429 on one request. Escalating backoff,
#: capped, before giving up and raising — never returning an empty result
#: that could be misread as "no adverse coverage".
#: Sized against the measured behaviour in the module docstring: a 429 here
#: is a coin flip weighted against you, roughly 1-in-10 per attempt, and
#: escalating waits do NOT improve the odds (9 minutes of silence still
#: returned 429). So the retry policy is "many attempts at the floor cadence"
#: rather than "few attempts with long backoff". The limiter already spaces
#: attempts 12s apart; `_429_EXTRA_AFTER` adds a further pause only for the
#: late attempts, where a genuinely stuck IP becomes the likelier
#: explanation. Worst case per request: 20*12 + 20*(12+30) ~= 18 minutes,
#: then RAISE. Bounded, so a stuck sweep fails loudly instead of hanging.
_MAX_429_ATTEMPTS = 40
_429_EXTRA_AFTER = 20    # attempt number past which extra sleep is added
_429_EXTRA_SECONDS = 30  # seconds of extra sleep on those late attempts

#: **The window must be pre-sliced.** Measured, and the reason this is not
#: one call per obligor:
#:
#:   requested 2025-01-01..2025-04-01 (90d)  -> 45 articles, spanning the
#:                                              whole requested range
#:   requested 2024-08-19..2026-08-19 (24mo) -> 126 articles, ALL of them
#:                                              within 2026-05-22..2026-08-17,
#:                                              i.e. the trailing ~3 months
#:
#: The 24-month row is auditable: that response is in `sources/gdelt/` and
#: its dates can be checked against the claim. (An earlier version of this
#: comment also cited a 6-month probe returning 134 articles confined to
#: 2025-04-02..2025-06-13. That probe was run before the cache existed and
#: is not reproducible from the committed payloads, so it has been dropped —
#: an example a reader cannot audit is worse than no example.)
#:
#: GDELT answers a long range by scanning backwards from `enddatetime` and
#: stopping early — and it stops well short of `maxrecords` (126 of a
#: possible 250), so a "did we get exactly 250 back?" truncation test never
#: fires. The older part of the range is dropped with no error, no warning,
#: and no full page. That is silent truncation: `"TUPPERWARE BRANDS"` over
#: the full window returned ZERO articles, while the same query restricted
#: to 2024-09..2024-11 returns 71 — the Chapter 11 coverage was there the
#: whole time. 90 days is the largest span verified to come back intact.
SLICE_DAYS = 90

WINDOW_START_DT = datetime.strptime(WINDOW_START, "%Y-%m-%d").replace(
    tzinfo=timezone.utc)
WINDOW_END_DT = (datetime.strptime(WINDOW_END, "%Y-%m-%d")
                  + timedelta(days=1) - timedelta(seconds=1)).replace(
    tzinfo=timezone.utc)

#: A GLEIF/EDGAR-style state-of-incorporation suffix, e.g. "/MO/", "/DE/" —
#: anchored at the end. Same shape as `warn_match._STATE_SUFFIX_RE`; kept as
#: a small local copy rather than a cross-module import, since that module
#: is deliberately pure and this one is deliberately I/O (see its docstring).
_STATE_SUFFIX_RE = re.compile(r"/[A-Za-z]{2}/\s*$")

#: Trailing legal-form words, stripped repeatedly so a name with more than
#: one ("..., Inc." after "Corp" is removed) still ends up clean. Narrower
#: than `warn_match.STOPWORDS`: only the classic legal-suffix set the
#: controller named ("`, INC.`, `CORP`, `LLC`, `LP`, …"). Deliberately does
#: NOT strip "Group", "Holdings", "Trust", "Partners", "Brands", "REIT" —
#: those are frequently part of the real public-facing name (e.g.
#: "Independence Realty Trust", "CrossAmerica Partners"), and stripping them
#: on principle risks the same silent-mismatch failure this fix exists to
#: close, just in the other direction.
_TRAILING_FORM_RE = re.compile(
    r"[,\s]+(?:Inc(?:orporated)?|Corp(?:oration)?|Co(?:mpany|mpanies)?|"
    r"L\.?L\.?C\.?|L\.?P\.?|L\.?L\.?P\.?|PLC|Ltd|Limited)\.?\s*$",
    re.IGNORECASE,
)


def _search_name(legal_name: str) -> str:
    """The string actually sent to GDELT: `legal_name` with the EDGAR
    state-of-incorporation suffix and trailing legal-form words removed, so
    the quoted phrase matches how news prose actually refers to the company
    rather than its registrant-index form. See module docstring — this is
    the fix for the defect that made every query unmatchable.
    """
    name = _STATE_SUFFIX_RE.sub("", legal_name).strip()
    while True:
        stripped = _TRAILING_FORM_RE.sub("", name).strip()
        if stripped == name or not stripped:
            break
        name = stripped
    return name or legal_name  # never hand back an empty query


#: **Per-obligor query overrides, each earned by a measured precision
#: failure.** `_search_name()` produces the name the press would plausibly
#: use, which is right for most obligors and catastrophically wrong for a
#: few whose short form is also a place, a person, or an ordinary word. A
#: sampling review of the first full sweep drew 25 random mentions per name
#: and found:
#:
#:   "Regis"    898 mentions, 0/25 true positives — Bognor Regis, Lyme
#:              Regis and Rowley Regis court reports, Regis Resources (an
#:              Australian gold miner), St. Regis hotels
#:   "Sabre"    756 mentions, 0/25 — the wrestler Zack Sabre Jr., and the
#:              idiom "sabre-rattling"
#:   "Griffon"  155 mentions, 0/155 on keywords — the griffon vulture in
#:              Spanish and French wildlife press, and a radio host named
#:              Moon Griffon
#:
#: 75 samples, zero true positives: a rule-of-three 95% upper bound of ~4%
#: precision on 1,809 mentions, 66% of the artifact. Those are not adverse
#: media about these obligors; they are the obligor's name appearing in
#: somebody else's bad news.
#:
#: The qualified forms below were then measured, and every one of them
#: returns **zero** articles across the full 24 months — not "fewer":
#:
#:   "Regis Corp" 0    "Regis Corporation" 0    "Regis Salons" 0
#:   "Sabre Corp" 0    "Sabre Corporation" 0
#:   "Griffon Corp" 0  "Griffon Corporation" 0
#:
#: So two independent lines of evidence agree that these three obligors
#: have no name-attributable adverse coverage in the window. The override
#: is retained rather than the obligor being hard-coded to zero, because
#: the zero is then a FETCHED result with a timeline behind it — the same
#: evidence every other quiet obligor has — instead of an assertion in
#: code. Deliberately NOT overridden: Celanese, PAYCHEX, AMPHENOL, MASTEC,
#: WATSCO. Those names are coined and distinctive; padding them would cost
#: recall with no measured precision gain.
QUALIFIED_NAMES: dict[str, str] = {
    "5493000Q1S5TJIDIQH89": "Regis Corp",    # REGIS CORP
    "529900VKCYZW8GZ4WW58": "Sabre Corp",    # Sabre Corp
    "5493000C2SGNC7ZN3242": "Griffon Corp",  # GRIFFON CORP
}


#: **What the precision review found, carried into the artifact.** Merged
#: into `coverage[lei]` on every save so the finding travels with the data
#: rather than living only in a report. `recommended_use` is the field a
#: consumer should branch on; absence of a `precision_review` entry means
#: the obligor was not reviewed, NOT that it was reviewed and passed.
#:
#: A note on method, because the two verdicts rest on different evidence.
#: "Replaced" rests on human inspection of random samples — reading what
#: each article is actually about — corroborated by the qualified phrase
#: returning zero. "Down-weight" rests on titles that are affirmatively
#: about something else (a police blotter is not chemical-industry news).
#: Neither rests on a name being absent from the title: GDELT matches the
#: article BODY, so a title that does not name the company is no evidence
#: of anything, and no obligor is flagged on that basis.
PRECISION_REVIEW: dict[str, dict] = {
    "5493000Q1S5TJIDIQH89": {
        "verdict": "replaced",
        "recommended_use": "normal",
        "prior_query": '"REGIS" tone<-5',
        "prior_mentions": 898,
        "sampled": 25,
        "true_positives": 0,
        "finding": "Bognor Regis, Lyme Regis and Rowley Regis court and "
                   "crime reports; Regis Resources, an Australian gold "
                   "miner; St. Regis hotels. Every qualified form measured "
                   "(Regis Corp, Regis Corporation, Regis Salons) returns "
                   "zero articles across the window, so the 898 rows were "
                   "replaced by a fetched zero rather than corrected.",
    },
    "529900VKCYZW8GZ4WW58": {
        "verdict": "replaced",
        "recommended_use": "normal",
        "prior_query": '"Sabre" tone<-5',
        "prior_mentions": 756,
        "sampled": 25,
        "true_positives": 0,
        "finding": "The wrestler Zack Sabre Jr., and the idiom "
                   "'sabre-rattling'. Sabre Corp and Sabre Corporation both "
                   "return zero across the window.",
    },
    "5493000C2SGNC7ZN3242": {
        "verdict": "replaced",
        "recommended_use": "normal",
        "prior_query": '"GRIFFON" tone<-5',
        "prior_mentions": 155,
        "sampled": 155,
        "true_positives": 0,
        "finding": "The griffon vulture in Spanish and French wildlife "
                   "press, and a radio host named Moon Griffon. Griffon "
                   "Corp and Griffon Corporation both return zero.",
    },
    "549300FHJQTDPPN41627": {
        "verdict": "retained, mixed precision",
        "recommended_use": "down_weight",
        "sampled": 49,
        "off_topic": 25,
        "finding": "'Celanese' is a place as well as a company — Celanese, "
                   "Texas is a company town named after the corporation, and "
                   "Celanese Road runs through Rock Hill, South Carolina. 25 "
                   "of 49 titles are police blotters and local crime reports "
                   "from those two places, affirmatively about something "
                   "other than the company. The remainder is genuine "
                   "chemical-industry coverage (the Clariant / LyondellBasell "
                   "/ Dow ethylene damages suits, a plant acid spill, Texas "
                   "freeze shutdowns). Not replaced: unlike Regis, Sabre and "
                   "Griffon the qualified form is not empty — 'Celanese "
                   "Corp' returns 4 articles — but swapping 49 mixed rows "
                   "for 4 clean ones would discard real industry coverage to "
                   "buy a precision number. Flagged for down-weighting "
                   "instead, so the choice is the consumer's.",
    },
}


#: GDELT's rejection text for a quoted phrase below its minimum length,
#: returned with HTTP 200 and a plain-text body. Measured: `"XPO"` (from
#: "XPO, Inc.") is rejected this way.
_PHRASE_TOO_SHORT = "phrase is too short"


class PhraseTooShort(RuntimeError):
    """GDELT rejected the quoted phrase as too short to search."""


def _phrase_query(search_name: str) -> str:
    """The normal form: an exact quoted phrase, tone-filtered."""
    return f'"{search_name}" {TONE_FILTER}'


def _bare_query(search_name: str) -> str:
    """Fallback for a name GDELT will not accept as a phrase. Unquoted, so
    GDELT treats it as a term rather than an exact phrase — broader, and
    recorded per row in `gdelt_query` so the looser matching is visible
    rather than hidden inside an otherwise uniform-looking artifact.
    """
    return f"{search_name} {TONE_FILTER}"


SUBSTITUTION_NOTE = (
    "Spec-named source: GDELT's raw event and mention streams "
    "(CAMEO-coded 15-minute CSVs at data.gdeltproject.org/gdeltv2/; "
    "~52,000 files across this 24-month window). "
    "Actually used: the GDELT DOC 2.0 API "
    "(api.gdeltproject.org/api/v2/doc/doc, mode=timelinevolraw to locate "
    "coverage then mode=artlist to retrieve it), article-level, "
    "queried per obligor with GDELT's tone<-5 filter, carrying the same "
    "15-minute seendate granularity as the raw stream. "
    "Cost of the substitution: GDELT's own CAMEO entity tagging is NOT "
    "used here — matching is by name query against a search string, "
    "which is lossy in the same way the WARN employer-name join is "
    "lossy, and near-duplicate articles across adjacent time slices "
    "(same title, different seendate) are real GDELT behaviour, kept as "
    "distinct mentions rather than silently merged. A second, narrower "
    "cost: `mode=artlist` does not return a per-article tone score "
    "(confirmed live — the payload carries only url/url_mobile/title/"
    "seendate/socialimage/domain/language/sourcecountry). Every mention "
    "here passed the server-side tone<-5 filter, so its true tone is "
    "below -5, but the `tone` field records that threshold string rather "
    "than a fabricated per-article number. A third cost, found and fixed "
    "during build: quoting the RAW Postgres `legal_name` verbatim (e.g. "
    "EDGAR's registrant-index form \"CHARTER COMMUNICATIONS, INC. /MO/\") "
    "produces an unmatchable literal phrase and silently returns zero "
    "results — indistinguishable from genuine \"no adverse coverage\". "
    "Each row's `employer_query` field carries the original legal_name "
    "(provenance); `gdelt_query` carries the exact query string sent to "
    "the API, built from the normalised name (state-suffix and trailing "
    "legal-form words stripped, e.g. \"Charter Communications\"). Words "
    "that are often part of the "
    "real public-facing name — Group, Holdings, Trust, Partners, Brands, "
    "REIT — are deliberately NOT stripped, so a handful of obligors whose "
    "media-common name drops one of those (e.g. \"Vertiv\" for \"Vertiv "
    "Holdings Co\") still search under the fuller form and may under-recall. "
    "A fourth cost, also found during build: GDELT rejects a quoted phrase "
    "below a minimum length with HTTP 200 and the plain-text body \"The "
    "specified phrase is too short.\" — another silently-empty result if "
    "unhandled. One obligor is affected (XPO, Inc. -> \"XPO\"); its query "
    "falls back to the UNQUOTED term, which GDELT matches more loosely than "
    "an exact phrase. Its rows are therefore lower-precision than the rest, "
    "and `gdelt_query` shows the unquoted form so that is visible per row "
    "rather than hidden. A fifth cost, the largest: the DOC API silently "
    "truncates a long date range. Asked for the full 24 months it scans "
    "backwards from enddatetime, returns only the trailing ~3 months, and "
    "stops short of maxrecords — so nothing about the response says it was "
    "cut. Measured: \"TUPPERWARE BRANDS\" over the full window returns 0 "
    "articles; the same query over 2024-09..2024-11 returns 71, its "
    "Chapter 11 coverage. The DOC API's timeline modes are NOT clamped, so "
    "this sweep queries mode=timelinevolraw first for each obligor (one "
    "call, daily buckets across all 24 months), then issues mode=artlist "
    "calls only over the day ranges that carry volume, each sized to stay "
    "under the 90-day span limit and the 250-record cap. The timeline's "
    "summed counts are retained per obligor under `coverage` as the "
    "EXPECTED article total, so the retrieved rows can be checked against a "
    "figure the API itself supplied rather than being accepted because they "
    "arrived; in the run that produced this artifact the two agreed to "
    "within one article in 952. Coverage is the full 24-month window: "
    "mentions run 2024-08-19 to 2026-08-14, 353 of them in 2024, 329 in "
    "2025 and 269 in 2026. A sixth cost, and the one a consumer of this "
    "file is most likely to be burned by: matching by name means an "
    "obligor whose short name is also a place, a person or an ordinary "
    "word collects adverse coverage that has nothing to do with it. A "
    "sampling review of the first full sweep found \"Regis\" (898 mentions, "
    "0 of 25 sampled genuine — Bognor Regis and Lyme Regis court reports, "
    "an Australian gold miner, St. Regis hotels), \"Sabre\" (756, 0 of 25 — "
    "a professional wrestler and the idiom \"sabre-rattling\") and "
    "\"Griffon\" (155, 0 of 155 — a vulture and a radio host). Those 1,809 "
    "rows, 66% of the original artifact, were REMOVED: each of those three "
    "obligors was re-queried under its qualified corporate name, every "
    "qualified form measured returns zero articles across the window, and "
    "that fetched zero replaced the noise. \"Celanese\" was reviewed and "
    "RETAINED at 49 rows despite 25 of them being police blotters from "
    "Celanese, Texas and Celanese Road in Rock Hill, South Carolina, "
    "because the rest is genuine chemical-industry coverage that the "
    "qualified form would discard. Findings are recorded per obligor under "
    "coverage[lei].precision_review, whose `recommended_use` field is the "
    "one to branch on; an obligor with no precision_review entry was not "
    "reviewed, which is not the same as having been reviewed and passed."
)


def _gdelt_url(query: str, start: datetime, end: datetime, *,
                mode: str = "artlist") -> str:
    params = {
        "query": query,
        "mode": mode,
        "format": "json",
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
    }
    if mode == "artlist":
        params["maxrecords"] = str(MAXRECORDS)
    else:
        params["timelinesmooth"] = "0"
    return f"{BASE_URL}?{urlencode(params)}"


def _payload_name(lei: str, query: str, tag: str) -> str:
    """Raw-payload filename. The query is hashed in because one obligor can
    legitimately issue two different queries for the same span — the
    quoted-phrase form and, if GDELT rejects it as too short, the unquoted
    fallback. Without the hash those two responses would overwrite each
    other under one name while the manifest recorded two URLs for it.
    """
    digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:8]
    return f"{lei}__{tag}__{digest}.json"


def gdelt_get(url: str, filename: str, manifest: SourceManifest, lei: str,
               *, force: bool, what: str) -> dict:
    """One throttled DOC API call, retried on 429, raised if it persists.

    A 429 is deliberately NOT treated as `ccf.fetch`'s "fact about the
    resource" — GDELT's own message says to slow down and retry, so this
    wraps `fetch()` with its own retry loop rather than letting the
    immediate-raise-on-HTTPError default stand.
    """
    for attempt in range(1, _MAX_429_ATTEMPTS + 1):
        GDELT_LIMITER.wait()
        try:
            path = fetch(url, manifest, filename, force=force, timeout=60)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 429:
                if attempt == _MAX_429_ATTEMPTS:
                    raise RuntimeError(
                        f"GDELT DOC API returned 429 on every attempt "
                        f"({_MAX_429_ATTEMPTS}) for {lei} {what}. "
                        "Not swallowing this into an empty result — "
                        "instability across a sweep is evidence of "
                        "incompleteness, not of a changing source. Rerun to "
                        "resume; obligors already swept are skipped."
                    ) from exc
                extra = _429_EXTRA_SECONDS if attempt > _429_EXTRA_AFTER else 0
                print(f"    [429] {lei} {what} — retrying "
                      f"(attempt {attempt}/{_MAX_429_ATTEMPTS}"
                      f"{f', +{extra}s' if extra else ''})", flush=True)
                if extra:
                    time.sleep(extra)
                continue
            raise

        body = path.read_text(encoding="utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            # GDELT signals some query rejections with HTTP **200** and a
            # plain-text body — no error status, no JSON. Left unhandled
            # this is the same silent-empty failure the query-normalisation
            # fix exists to close, so every non-JSON body is classified
            # here and never returned as "no articles".
            text = body.strip()
            if _PHRASE_TOO_SHORT in text:
                raise PhraseTooShort(text) from None
            raise RuntimeError(
                f"GDELT returned HTTP 200 with a non-JSON body for {lei} "
                f"{what}: {text[:200]!r}. Refusing to treat this as an "
                "empty result."
            ) from None

    raise AssertionError("unreachable — loop always returns or raises")


def fetch_timeline(lei: str, query: str, manifest: SourceManifest,
                    *, force: bool) -> list[tuple[datetime, int]]:
    """Daily adverse-article counts for `query` across the whole window.

    This is the call that makes the sweep both correct and affordable. See
    `SLICE_DAYS`: `mode=artlist` silently truncates a long range, but
    `mode=timelinevolraw` does NOT — it returns one bucket per day across
    the full 24 months. So the timeline is fetched first and it answers two
    questions no article query can:

      * **Where** the coverage is, so article calls are issued only for
        days that actually have volume — most obligors are quiet for most
        of the window, and a quiet obligor costs exactly one call.
      * **How much** there should be, giving `mentions` a checkable
        expected total instead of a number that is whatever came back.
    """
    url = _gdelt_url(query, WINDOW_START_DT, WINDOW_END_DT,
                     mode=TIMELINE_MODE)
    payload = gdelt_get(url, _payload_name(lei, query, "timeline"), manifest,
                        lei, force=force, what="timeline")
    # A missing `timeline` key collapses to "no adverse coverage on any of
    # the 730 days" — the same answer a degraded-but-still-JSON response
    # would produce, and therefore an unnamed member of the silent-empty
    # family this module spends most of its length defending against. It is
    # tolerated rather than raised because the empty case was verified:
    # GDELT genuinely answers a zero-coverage query with `{}`, and **20** of
    # the 50 obligors legitimately land there (the comment said 17 until
    # 2026-08-21; the count rose when the Task 5 fix round removed the 1,809
    # name-collision mentions, which moved Regis, Sabre and Griffon from
    # "noisy coverage" to a fetched, corroborated zero). What makes it safe is that the
    # emptiness is CORROBORATED downstream — a zero timeline yields zero
    # article calls and zero rows, and the artifact records `active_days: 0`
    # for that obligor, so a reader can see the claim rests on the timeline
    # rather than on an article query that came back short. If GDELT ever
    # starts returning a differently-shaped success payload, this is where
    # it would look like silence instead of like a change.
    series = (payload.get("timeline") or [{}])[0].get("data") or []
    out: list[tuple[datetime, int]] = []
    for point in series:
        raw = point.get("date")
        value = int(point.get("value") or 0)
        if not raw or not value:
            continue
        out.append((datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc), value))
    return out


def plan_slices(daily: list[tuple[datetime, int]]) -> list[tuple[datetime, datetime, int]]:
    """Turn non-empty timeline days into the smallest set of article calls.

    Consecutive days are merged into one slice until either the slice would
    span more than `SLICE_DAYS` (past which `artlist` truncates) or its
    expected article count would exceed `MAX_SLICE_VOLUME` (past which
    `maxrecords` truncates). Both ceilings are truncation risks, so both
    close a slice.
    """
    slices: list[tuple[datetime, datetime, int]] = []
    first: datetime | None = None
    last: datetime | None = None
    volume = 0

    def flush() -> None:
        nonlocal first, last, volume
        if first is not None and last is not None:
            slices.append((first,
                           last + timedelta(days=1) - timedelta(seconds=1),
                           volume))
        first = last = None
        volume = 0

    for day, value in sorted(daily):
        if first is None:
            first, last, volume = day, day, value
            continue
        span_days = (day - first).days + 1
        if span_days > SLICE_DAYS or volume + value > MAX_SLICE_VOLUME:
            flush()
            first, last, volume = day, day, value
        else:
            last, volume = day, volume + value
    flush()
    return slices


def sweep_obligor(lei: str, search_name: str, manifest: SourceManifest,
                   *, force: bool) -> tuple[list[dict], str, dict]:
    """Collect every DOC API article for one obligor.

    Returns the articles, **the query string actually sent**, and a coverage
    record. The query is returned because it can diverge from the obvious
    form: a search name too short to be a legal GDELT phrase is retried
    unquoted (see `_bare_query`), and the artifact must show which form
    produced the rows.
    """
    try:
        return _sweep_with_query(lei, _phrase_query(search_name), manifest,
                                 force=force)
    except PhraseTooShort as exc:
        bare = _bare_query(search_name)
        print(f'    [phrase-too-short] {lei} "{search_name}" rejected by '
              f'GDELT ({exc}); retrying unquoted as {bare!r}', flush=True)
        return _sweep_with_query(lei, bare, manifest, force=force)


def _sweep_with_query(lei: str, query: str, manifest: SourceManifest,
                       *, force: bool) -> tuple[list[dict], str, dict]:
    daily = fetch_timeline(lei, query, manifest, force=force)
    expected = sum(v for _, v in daily)
    slices = plan_slices(daily)

    seen_urls: set[str] = set()
    articles: list[dict] = []
    for start, end, slice_expected in slices:
        payload = gdelt_get(
            _gdelt_url(query, start, end),
            _payload_name(lei, query,
                          f"{start:%Y%m%d}-{end:%Y%m%d}"),
            manifest, lei, force=force,
            what=f"[{start:%Y-%m-%d}..{end:%Y-%m-%d}]")
        results = payload.get("articles") or []
        if len(results) == MAXRECORDS:
            # Should not happen — plan_slices caps expected volume well
            # below maxrecords — but a full page is unfalsifiable evidence
            # of truncation, so say so rather than quietly keeping 250.
            print(f"    [WARN] {lei} [{start:%Y-%m-%d}..{end:%Y-%m-%d}] "
                  f"returned a full page of {MAXRECORDS}; expected "
                  f"{slice_expected}. Slice may be truncated.", flush=True)
        for art in results:
            url = art.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            articles.append(art)

    coverage = {
        "expected_from_timeline": expected,
        "articles_returned": len(articles),
        "active_days": len(daily),
        "article_calls": len(slices),
    }
    return articles, query, coverage



def load_artifact() -> dict:
    if ARTIFACT_PATH.exists():
        return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    return {
        "generated_at": None,
        "source": "GDELT DOC 2.0 API (api.gdeltproject.org/api/v2/doc/doc), "
                   "mode=timelinevolraw to locate coverage then mode=artlist "
                   "to retrieve it, per-obligor name query with tone<-5",
        "substitution_note": SUBSTITUTION_NOTE,
        "obligors_swept": [],
        "coverage": {},
        "mentions": [],
    }


def save_artifact(data: dict) -> None:
    data["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data["substitution_note"] = SUBSTITUTION_NOTE  # keep current even on resume
    for lei, review in PRECISION_REVIEW.items():
        if lei in data.get("coverage", {}):
            data["coverage"][lei]["precision_review"] = review
    SCREEN.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                     help="re-sweep every obligor, ignoring prior progress")
    ap.add_argument("--only", metavar="LEI[,LEI...]",
                     help="re-sweep just these LEIs, ignoring prior progress "
                          "for them and leaving every other obligor's rows "
                          "untouched. For correcting one obligor's query "
                          "without spending a full sweep's rate-limit budget.")
    args = ap.parse_args()

    only = {x.strip() for x in args.only.split(",")} if args.only else set()

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, legal_name FROM "{PG_SCHEMA_V2}".legal_entity '
                    "ORDER BY lei")
        obligors = cur.fetchall()

    if only:
        unknown = only - {lei for lei, _ in obligors}
        if unknown:
            raise SystemExit(f"--only names LEIs that are not obligors: "
                             f"{sorted(unknown)}")
        obligors = [(lei, name) for lei, name in obligors if lei in only]

    print(f"{len(obligors)} obligors; window [{WINDOW_START}, {WINDOW_END}]; "
          f"throttle 1 req / {GDELT_THROTTLE_SECONDS:.0f}s\n")

    if args.dry_run:
        for lei, name in obligors:
            resolved = QUALIFIED_NAMES.get(lei) or _search_name(name)
            flag = "  [override]" if lei in QUALIFIED_NAMES else ""
            print(f"  [plan] {lei}  \"{name}\" -> \"{resolved}\" {TONE_FILTER}{flag}")
        print("\n  [dry-run] nothing fetched or written")
        return 0

    manifest = SourceManifest(
        source="gdelt",
        description="GDELT DOC 2.0 API — per-obligor adverse-tone article search",
        licence="GDELT Project, public (see gdeltproject.org/about.html#termsofuse)",
    )

    artifact = load_artifact()
    artifact.setdefault("coverage", {})
    if args.force:
        artifact["obligors_swept"] = []
        artifact["coverage"] = {}
        artifact["mentions"] = []
    swept = set(artifact.get("obligors_swept", []))

    skipped = 0
    for lei, legal_name in obligors:
        if lei in swept and not args.force and lei not in only:
            skipped += 1
            print(f"  [skip] {lei}  \"{legal_name}\" — already swept")
            continue

        search_name = QUALIFIED_NAMES.get(lei) or _search_name(legal_name)
        articles, gdelt_query, coverage = sweep_obligor(
            lei, search_name, manifest, force=args.force)
        prior = sum(1 for m in artifact["mentions"] if m["lei"] == lei)
        rows = [{
            "lei": lei,
            "employer_query": legal_name,
            "gdelt_query": gdelt_query,
            "seendate": art.get("seendate"),
            "domain": art.get("domain"),
            "title": art.get("title"),
            "url": art.get("url"),
            "tone": TONE_FILTER_VALUE,
            "provenance": "public",
        } for art in articles]

        # This obligor's window filter, applied defensively even though the
        # API call already scoped startdatetime/enddatetime server-side.
        rows = [r for r in rows if r["seendate"]
                and in_window(f"{r['seendate'][:4]}-{r['seendate'][4:6]}-{r['seendate'][6:8]}")]

        # Drop any prior rows for this LEI (force / re-sweep case) before
        # adding the fresh set, so a re-run never duplicates.
        artifact["mentions"] = [m for m in artifact["mentions"] if m["lei"] != lei]
        artifact["mentions"].extend(rows)
        swept.add(lei)
        artifact["obligors_swept"] = sorted(swept)
        coverage["mentions_in_window"] = len(rows)
        coverage["gdelt_query"] = gdelt_query
        artifact["coverage"][lei] = coverage

        shortfall = coverage["expected_from_timeline"] - coverage["articles_returned"]
        note = f"  (timeline expected {coverage['expected_from_timeline']}"
        note += f", short by {shortfall}" if shortfall > 0 else ""
        note += f", {coverage['article_calls']} article calls)"
        if lei in only and prior != len(rows):
            note += f"  [replaced {prior} prior rows]"
        print(f"  {lei}: {len(rows)} adverse mentions  "
              f"\"{legal_name}\" -> \"{search_name}\"{note}")
        save_artifact(artifact)  # incremental — safe to interrupt after this line

    # Save once more even when every obligor was skipped: `generated_at`
    # and `substitution_note` are refreshed from the module on every save,
    # so a resumed or no-op run still leaves the artifact describing the
    # code that exists rather than the code that produced the rows.
    save_artifact(artifact)

    print(f"\n{len(artifact['mentions'])} mentions across "
          f"{len({m['lei'] for m in artifact['mentions']})} obligors "
          f"({skipped} obligors skipped as already-swept)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
