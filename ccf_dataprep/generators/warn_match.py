#!/usr/bin/env python3
"""Pure lossy obligor <-> WARN-employer name matcher (CLAUDE.md rule 5).

The join between the bank's 50 anchor obligors (Postgres `legal_entity`,
`legal_name` column) and the 3,514 state WARN layoff notices is a NAME join
across two independently-authored public sources. It is supposed to be
imperfect: some real subsidiaries and DBAs resolve cleanly, some genuine
matches are only ambiguous, and the strongest lexical false positive in the
loaded data ("Pregis" scored against "Regis Corp") must NOT resolve even
though a naive `SequenceMatcher` ratio alone scores it *higher* than a real
true positive (Bausch Health).

No network, no file I/O, no DB access here — that lives in
`generators/fetch_warn.py`. This module is pure so it is unit-testable
offline (`validators/test_warn_match.py`).

Scoring design
--------------
`score()` blends a plain character-level ratio with two token-level signals,
each gated to avoid the "high character overlap, wrong company" trap:

1. **Full token containment** — every token of the shorter normalised name
   is an exact token of the longer one (e.g. "charter communications" is
   fully present in "charter communications austin"). This is common, weak
   evidence on its own (a single shared common word can satisfy it by
   accident — see "Regis" inside "St. Regis Houston"), so it gets a modest
   blend weight (`FULL_CONTAINMENT_WEIGHT`) rather than a flat pass. A
   short, dissimilar full-containment pair still lands *ambiguous*, not
   *resolved*.

2. **Leading-brand match** — the FIRST token of both normalised names is
   identical (company names lead with the distinctive brand/identifier and
   trail with descriptors: "Quanex Building Products" / "Quanex
   Homeshield"), AND the employer's NORMALISED form is no longer than the
   anchor's NORMALISED form — both sides are `normalise()` output, not the
   strings as filed (a subsidiary or DBA reference is typically a *simpler*
   name than the full registered legal-entity name, not a longer,
   more-specific one). This is why "Quanex" / "Quanex Homeshield" and
   "Bausch Health" / "Bausch Health US" resolve despite modest raw character
   overlap, while "Boston Omaha" / "Boston Scientific" and "Granite
   Construction" / "Granite Peak Fabrication" — which ALSO share a leading
   token, but whose employer side is the *longer* string — do not: they are
   two different companies that happen to start with a common word, not a
   parent naming a subsidiary.

   The signal additionally requires the shared leading token to be
   DISTINCTIVE (`GENERIC_LEADING`). A shared first token only identifies a
   shared company when the word belongs to that company; "american",
   "national", "standard" and their kind belong to thousands, so for those
   the signal is withheld and the pair falls through to the capped
   plain-ratio branch. Withholding it cannot lose a genuine match: a real
   parent/subsidiary pair satisfies full containment (signal 1), which is
   evaluated first. Added 2026-08-21 after "American Healthcare REIT" was
   measured RESOLVING against "American Woodmark Corporation" at 0.907.

Neither signal fires for "Regis" vs "Pregis": they are not the same first
TOKEN ("regis" != "pregis" — a substring relationship, not a token match),
so the pair falls through to the plain-ratio branch, which is explicitly
CAPPED below `RESOLVE_AT` (`NO_TOKEN_MATCH_CAP`). Without that cap, this
pair's raw character ratio (0.909) would resolve on its own — higher than
the genuine Bausch Health true positive (0.769) — which is exactly the
demonstration this dataset exists to carry: a pure similarity ratio cannot
separate them; token structure can.
"""

from __future__ import annotations

import difflib
import re

from generators.warn_sources import WarnNotice

#: Legal-form / entity-type words that carry no matching signal.
STOPWORDS = {"inc", "corp", "corporation", "co", "company", "llc", "lp",
             "plc", "holdings", "holding", "group", "ltd", "the", "and", "of"}

#: A GLEIF-style state-of-incorporation suffix, e.g. "/MO/", "/DE/" —
#: anchored at the end so it can't eat something mid-name by accident.
_STATE_SUFFIX_RE = re.compile(r"/[A-Za-z]{2}/\s*$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")

RESOLVE_AT = 0.85
AMBIGUOUS_AT = 0.70

#: Blend weight for the full-token-containment signal — deliberately
#: moderate: containment alone is common enough (one shared generic word)
#: that it must not, by itself, guarantee a resolve. A short, dissimilar
#: contained pair (e.g. "Regis" inside "St. Regis Houston") still needs to
#: land ambiguous.
FULL_CONTAINMENT_WEIGHT = 0.65

#: Blend weight for the leading-brand-match signal — a genuine subsidiary
#: pattern (matching first token, employer's NORMALISED form no longer than
#: the anchor's NORMALISED form — `normalise()` output on both sides, not the
#: registered name as filed, which is what this note said until 2026-08-21)
#: is stronger, more specific evidence than plain
#: containment, so it earns a heavier weight even against a middling raw
#: ratio (Quanex Homeshield's raw ratio is only 0.488).
LEADING_BRAND_WEIGHT = 0.8

#: Minimum length for a first token to count as a "brand" rather than a
#: coincidental short-word collision. 4-5 letter common words ("City",
#: "Super") were measured producing spurious real-data resolves ("City
#: Office REIT" / "City of Hope", "Super Micro Computer" / "Super 7")
#: before this was raised — both anchor "brand" tokens this path is meant
#: for (Quanex, Bausch) are 6 letters.
#:
#: Length alone is NOT distinctiveness, which is what `GENERIC_LEADING`
#: below exists to say. Raising this further cannot fix the generic-word
#: problem: "american" is 8 letters.
MIN_BRAND_LEN = 6

#: Ordinary English adjectives and geographies that thousands of unrelated
#: US companies lead with. The leading-brand signal assumes a shared first
#: token identifies a shared *company*; for these words it identifies
#: nothing, so the signal is withheld and the pair falls through to the
#: capped plain-ratio branch.
#:
#: Found 2026-08-21 (Wave 11c) by probing the Virginia WARN source: "American
#: Healthcare REIT" scored 0.907 — RESOLVED — against "American Woodmark
#: Corporation", a cabinet manufacturer. The rule had been live since Wave
#: 11b and had simply never met a generic-prefix pair; no Texas or California
#: in-window notice happened to lead with a word one of the 50 anchors also
#: leads with. It was not wrong-but-tolerated, it was wrong-and-unfired.
#:
#: This list is a FLOOR, not a ceiling — the next generic prefix is not on
#: it. It is safe to extend and safe to be incomplete, because withholding
#: the shortcut does not lose a genuine match: a real parent/subsidiary pair
#: ("Pioneer Natural Resources" / "Pioneer Natural Resources USA") satisfies
#: full token containment, which is tested FIRST and unaffected by this set.
#: Only a pair whose sole evidence is the shared generic word is demoted.
GENERIC_LEADING = {
    "american", "national", "united", "general", "standard", "global",
    "international", "federal", "central", "continental", "atlantic",
    "pacific", "northern", "southern", "eastern", "western", "premier",
    "advanced", "allied", "associated", "consolidated", "universal",
    "superior", "integrated", "republic", "community", "capital",
}

#: A pair with NEITHER containment signal is capped here regardless of raw
#: character ratio — this is what keeps "Regis" / "Pregis" (ratio 0.909)
#: from resolving on character overlap alone.
NO_TOKEN_MATCH_CAP = 0.80


def normalise(name: str) -> str:
    """Lowercase, strip a trailing `/XX/` state suffix and punctuation,
    drop corporate-form stopwords, collapse whitespace.
    """
    name = _STATE_SUFFIX_RE.sub("", name)
    name = name.lower()
    name = _NON_ALNUM_RE.sub(" ", name)
    tokens = [t for t in name.split() if t and t not in STOPWORDS]
    return " ".join(tokens)


def score(anchor_name: str, employer: str) -> float:
    """0.0-1.0 lossy match score between an anchor's legal name and a WARN
    notice's employer string. See module docstring for the design.
    """
    a = normalise(anchor_name)
    b = normalise(employer)
    if not a or not b:
        return 0.0

    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = a.split(), b.split()
    sa, sb = set(ta), set(tb)

    shorter, longer_set = (ta, sb) if len(ta) <= len(tb) else (tb, sa)
    full_containment = bool(shorter) and all(t in longer_set for t in shorter)
    if full_containment:
        return FULL_CONTAINMENT_WEIGHT * 1.0 + (1 - FULL_CONTAINMENT_WEIGHT) * ratio

    leading_brand = (ta and tb and ta[0] == tb[0] and len(ta[0]) >= MIN_BRAND_LEN
                      and ta[0] not in GENERIC_LEADING
                      and len(b) <= len(a))
    if leading_brand:
        return LEADING_BRAND_WEIGHT * 1.0 + (1 - LEADING_BRAND_WEIGHT) * ratio

    return min(ratio, NO_TOKEN_MATCH_CAP)


def classify(score_value: float) -> str:
    """`"resolved"` at `>= RESOLVE_AT`, `"ambiguous"` at `>= AMBIGUOUS_AT`,
    else `"rejected"`.
    """
    if score_value >= RESOLVE_AT:
        return "resolved"
    if score_value >= AMBIGUOUS_AT:
        return "ambiguous"
    return "rejected"


def match_all(anchors: list[tuple[str, str]],
              notices: list[WarnNotice]) -> list[dict]:
    """Score every (anchor, notice) pair; emit every one scoring
    `>= AMBIGUOUS_AT` — resolved AND ambiguous alike. Rejected pairs are not
    emitted, or the table is 50 x len(notices) rows.

    Deliberately NOT best-match-per-anchor: keeping only the single
    highest-scoring notice per obligor can hide a true positive behind a
    higher-scoring false positive (e.g. Quanex Homeshield behind "Gold Bond
    Building Products") and make a real match look absent.
    """
    rows: list[dict] = []
    for lei, anchor_name in anchors:
        for notice in notices:
            s = score(anchor_name, notice.employer)
            verdict = classify(s)
            if verdict == "rejected":
                continue
            rows.append({
                "lei": lei,
                "anchor_name": anchor_name,
                "employer": notice.employer,
                "state": notice.state,
                "score": round(s, 4),
                "verdict": verdict,
                "notice_ref": notice.source_ref,
            })
    return rows
