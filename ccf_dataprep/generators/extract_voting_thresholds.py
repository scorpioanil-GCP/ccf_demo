#!/usr/bin/env python3
"""Wave 18 Task 11b -- the R half of "Voting thresholds and amendment
mechanics" (§C: MongoDB + Fluree, `L` + `R`). Task 11 built the `L` half
(the filed article text, in Mongo, with span offsets). No task's brief
covered `R` -- this generator, and `loaders/load_fluree_wave18.py`'s
`build_thresholds()`, close that gap: one typed `ex:AmendmentThreshold`
node per (document, consent-standard bucket), linked to the Wave 18
facilities it governs.

## Two extraction strategies, for two different kinds of claim

**The percentage** ("Required Lenders" / "Required Class A|B Lenders", and
the number backing each) is extracted by ONE generic, cross-document regex
(`REQUIRED_LENDERS_RE`) against each filing's own defined-terms article --
"Required Lenders" means..., at least two Lenders having...more than 50%",
etc. This pattern is genuinely general: it needs no per-document tuning and
was verified live against all six filings before being trusted (see the
module's own test fixtures and `validators/test_syndicate.py`), matching
exactly one hit in five documents and exactly two (Class A, Class B) in the
sixth (Sabre) -- `EXPECTED_REQUIRED_LENDERS_HITS` below asserts this count
per document so a text change that breaks the pattern fails loudly rather
than silently returning fewer thresholds.

**The elevated, per-Lender veto standard** ("each affected Lender" / "each
Class A Lender" / "each Class B Lender" / "all Lenders") is NOT reduced to
one generic pattern -- the six filings name it in six different ways
("without the written consent of such Lender", "...each Lender directly
and adversely affected thereby", "...Administrative Agent and each
Lender:"), and forcing one regex to match all of them would either miss
real hits or match unrelated prose elsewhere in a 600,000+ character
filing. `CARVEOUT_SPECS` below is a curated, per-document list -- the
`amendment_type` description is hand-written (summarising which items in
the filing's own enumerated carve-out list the standard covers), but the
`pattern` each entry carries is still run against the LIVE filing text and
asserted to match at generation time (`assert m, ...`), the same discipline
`generate_syndicate_internal.py::extract_amendment_events` applies to its
own "dated as of ..." recital search -- a curated description is not the
same thing as an invented offset; the offset itself is always code-derived
and would fail loudly if the filing text it targets ever changed.

## What is deliberately NOT extracted

Sabre's carve-out (A), "each Servicer" (matters affecting a Servicer's own
rights and duties), is left out. It is a real, distinct consent standard in
the filing, but it governs a third-party SERVICER's rights, not a LENDER's
-- out of scope for a "voting threshold" element about syndicate members
deciding whether an amendment passes. Recorded here, not silently dropped,
per the same discipline `docs/wave18-design.md` §10 applies to
`sharesCollateralWith`.

Percentages are never invented for the elevated carve-outs. No filing among
the six expresses "each affected Lender" or "all Lenders" as a percentage
of anything -- `consent_percent` is `None` on every `CARVEOUT_SPECS` entry,
by construction, and stays `None` all the way to the Fluree loader, which
omits `ex:consentPercent` entirely on those nodes rather than writing a
computed placeholder.

Output: sources/screening/wave18_voting_thresholds.json
Run:    uv run generators/extract_voting_thresholds.py
"""

from __future__ import annotations

import hashlib
import json
import re

from ccf.config import REPO_ROOT
from ccf.syndicate import TRANCHE_TO_FACILITIES, WAVE18_EXCLUDED_FACILITIES
from generators.extract_amendment_assignment_articles import (
    ASSIGN_PATTERNS,
    VOTING_PATTERNS,
    find_heading,
)
from generators.extract_facilities import TextExtractor

EX10 = REPO_ROOT / "sources" / "ex10"
SCREEN = REPO_ROOT / "sources" / "screening"
OUT = SCREEN / "wave18_voting_thresholds.json"

# --- the generic percentage extractor -------------------------------------

#: Matches "Required Lenders" / "Required Class A Lenders" / "Required
#: Class B Lenders" ... means ... (more than|at least) N% -- verified live
#: against all six filings (see module docstring). `re.S` because the
#: filing's own line wrapping puts a newline between the defined term and
#: "means" in some documents (e.g. 'Required Lenders”\nmeans...').
REQUIRED_LENDERS_RE = re.compile(
    r"Required(?:\s+Class\s+([AB]))?\s+Lenders.{0,15}\bmeans\b.{0,400}?"
    r"(?:more than|at least)\s*(\d+(?:\.\d+)?)\s*%",
    re.S,
)

#: How many `REQUIRED_LENDERS_RE` hits each document is expected to yield.
#: Five documents define a single flat "Required Lenders" percentage; Sabre
#: alone splits it Class A / Class B. A document producing a different
#: count than expected is a text change or a pattern regression, not a
#: silently-accepted drift -- `main()` asserts this exactly.
EXPECTED_REQUIRED_LENDERS_HITS: dict[str, int] = {
    "1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm": 1,   # RB Global
    "885590_0001193125-25-149731_d949183dex101.htm": 1,        # Bausch
    "1632970_0001193125-26-145647_ahr-ex10_1.htm": 1,          # AHR
    "716643_0001193125-24-281618_d761586dex101.htm": 1,        # Regis
    "723531_0001193125-26-021794_payx-ex10_1.htm": 1,          # Paychex
    "1597033_0001193125-26-340356_d133770dex101.htm": 2,       # Sabre (A+B)
}


def extract_required_lenders(document: str, text: str) -> list[dict]:
    matches = list(REQUIRED_LENDERS_RE.finditer(text))
    expected = EXPECTED_REQUIRED_LENDERS_HITS[document]
    assert len(matches) == expected, (
        f"{document}: expected {expected} 'Required Lenders' percentage "
        f"definition(s), found {len(matches)} -- refusing to guess which "
        f"is real")

    out: list[dict] = []
    for m in matches:
        cls = m.group(1)  # "A", "B", or None
        pct = m.group(2)
        if cls is None:
            bucket = "required-lenders"
            standard = "Required Lenders"
        else:
            bucket = f"required-class-{cls.lower()}-lenders"
            standard = f"Required Class {cls} Lenders"
        out.append({
            "bucket": bucket,
            "consent_standard": standard,
            "consent_percent": pct,
            "amendment_type": (
                "General amendments and waivers to the Agreement and other "
                "Loan Documents not otherwise carved out to a narrower "
                "consent standard below"
            ),
            "source_passage": f"{document}#offset={m.start()}-{m.end()}",
        })
    return out


# --- the curated, per-document elevated-standard carve-outs ---------------

_SUCH_LENDER = re.compile(
    r"without\s+the\s+written\s+consent\s+of\s+such\s+Lender", re.I)
_EACH_LENDER_ENTITLED = re.compile(
    r"without\s+the\s+written\s+consent\s+of\s+each\s+Lender\s+entitled", re.I)
_AFFECTED_DIRECTLY = re.compile(
    r"each\s+Lender\s+directly\s+(?:and\s+adversely\s+)?affected(?:\s+thereby)?",
    re.I)
_BARE_EACH_LENDER = re.compile(
    r"(?:Administrative\s+Agent\s+and\s+)?each\s+Lender\s*:", re.I)
#: Paychex's "all Lenders" standard genuinely repeats the SAME literal
#: phrase "without the written consent of each Lender" four times, once
#: per enumerated item (iv)-(vii), inside the single sentence that opens
#: the article ("provided that no such agreement shall ... (iv) ... (v)
#: ... (vi) ... (vii) ..."). Scoping alone does not make this unique --
#: all four are genuinely inside the located article. Anchored on item
#: (iv)'s own opening text (the first item this bucket's `amendment_type`
#: describes: the ratable-reduction/pro-rata-sharing/payment-waterfall
#: carve-out, §10.01(b)(iv)) so the pattern matches exactly once; the
#: `clause` group is what gets cited, not the anchor prose, so the citation
#: stays the narrow operative phrase, same shape as every other entry here.
_EACH_LENDER_PLAIN = re.compile(
    r"\(iv\)\s+change\s+Section\s+2\.09\(c\).{0,400}?"
    r"(?P<clause>without\s+the\s+written\s+consent\s+of\s+each\s+Lender\b"
    r"(?!\s+(?:directly|entitled)))", re.I | re.S)
_CLASS_A_LENDER = re.compile(r"each\s+Class\s+A\s+Lender", re.I)
_CLASS_B_LENDER = re.compile(r"each\s+Class\s+B\s+Lender", re.I)

#: document -> ordered list of curated elevated-standard entries. Each
#: entry's `pattern` is searched ONLY inside this document's own located
#: voting/amendment article -- from its own heading (found the same way
#: `extract_amendment_assignment_articles.find_heading()` finds it for the
#: Task 11 Mongo passage) through the start of the NEXT article's heading
#: (`Successors and Assigns.` / `Assignments and Participations.`), not
#: Task 11's 800-3,000-char-capped Mongo passage and not the full
#: 600,000+ character document. Findings round 1 (fix): a document-wide
#: `.search()` for the FIRST match anywhere in the filing shipped four
#: wrong citations -- three in Sabre, one in Bausch -- each landing on a
#: defined-terms block, an unrelated financial-reporting covenant, or a
#: Defaulting-Lender cross-reference that happens to share the pattern's
#: wording, not the real consent clause. The Mongo passage's own 3,000-char
#: cap is too narrow for this purpose: Bausch's real clause sits 33 chars
#: past that passage's captured end. `extract_carveouts()` now REQUIRES
#: exactly one match inside the located article span and raises on 0 or on
#: more than 1 -- never silently takes `[0]`.
CARVEOUT_SPECS: dict[str, list[dict]] = {
    "1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm": [  # RB Global
        {
            "bucket": "each-affected-lender",
            "consent_standard": "each affected Lender",
            "pattern": _SUCH_LENDER,
            "amendment_type": (
                "Extend or increase a Lender's Commitment (or reinstate one "
                "terminated); postpone a scheduled payment date; or reduce "
                "the principal, interest rate, or fees payable to a Lender "
                "-- as to the Lender(s) directly affected (§11.01(a)(i)-"
                "(iii)), except that only Required Lenders' consent is "
                "needed to amend the Default Rate definition"
            ),
        },
    ],
    "885590_0001193125-25-149731_d949183dex101.htm": [  # Bausch
        {
            "bucket": "each-affected-lender",
            "consent_standard": "each affected Lender",
            "pattern": _AFFECTED_DIRECTLY,
            "amendment_type": (
                "Commitment increases; reduction or forgiveness of "
                "principal or amounts due; extension of maturity or "
                "postponement of a scheduled payment; reduction of the "
                "interest rate -- as to the Lender(s) directly and "
                "adversely affected (§10.02(b)(A)(1)-(4))"
            ),
        },
    ],
    "1632970_0001193125-26-145647_ahr-ex10_1.htm": [  # AHR
        {
            "bucket": "each-affected-lender",
            "consent_standard": "each affected Lender",
            "pattern": _AFFECTED_DIRECTLY,
            "amendment_type": (
                "Extend or increase a Lender's Commitment (or reinstate one "
                "terminated); waive non-payment or postpone a scheduled "
                "payment; or reduce principal, interest, or fees -- as to "
                "the Lender(s) directly affected (§11.01(a)(i)-(iii)), "
                "except that only Required Lenders' consent is needed to "
                "amend the Default Rate definition"
            ),
        },
    ],
    "716643_0001193125-24-281618_d761586dex101.htm": [  # Regis
        {
            "bucket": "each-affected-lender",
            "consent_standard": "each affected Lender",
            "pattern": _SUCH_LENDER,
            "amendment_type": (
                "Increase a Lender's Commitment (or reinstate one reduced "
                "or terminated); reduce principal or interest on Loans "
                "payable to a Lender or any fee payable for its account; "
                "or postpone/extend a scheduled payment date -- as to the "
                "Lender directly affected (§11.01(i))"
            ),
        },
    ],
    "723531_0001193125-26-021794_payx-ex10_1.htm": [  # Paychex
        {
            "bucket": "each-affected-lender",
            "consent_standard": "each affected Lender",
            "pattern": _SUCH_LENDER,
            "amendment_type": (
                "Commitment increase (§10.01(b)(i)); reduction of "
                "principal, LC disbursement amount, interest rate or fees, "
                "or postponement of a scheduled payment -- as to the "
                "Lender(s) directly affected (§10.01(b)(ii)-(iii))"
            ),
        },
        {
            "bucket": "all-lenders",
            "consent_standard": "all Lenders",
            "pattern": _EACH_LENDER_PLAIN,
            "amendment_type": (
                "Change the ratable-reduction/pro-rata-sharing provisions "
                "or the payment waterfall (§§2.09(c), 2.18(b)/(d), "
                "2.22(b)); change this amendment section or the definition "
                "of 'Required Lenders' itself; or release the Parent or "
                "Subsidiary Guarantors -- unanimous, every Lender, not only "
                "those directly affected (§10.01(b)(iv)-(vii))"
            ),
        },
    ],
    "1597033_0001193125-26-340356_d133770dex101.htm": [  # Sabre
        {
            "bucket": "each-class-a-lender",
            "consent_standard": "each Class A Lender",
            "pattern": _CLASS_A_LENDER,
            "amendment_type": (
                "Change (directly or indirectly) the definition of Class A "
                "Final Maturity Date (§12.01(b)(B))"
            ),
        },
        {
            "bucket": "each-class-b-lender",
            "consent_standard": "each Class B Lender",
            "pattern": _CLASS_B_LENDER,
            "amendment_type": (
                "Change (directly or indirectly) the definition of Class B "
                "Final Maturity Date (§12.01(b)(C))"
            ),
        },
        {
            "bucket": "all-lenders",
            "consent_standard": "all Lenders",
            "pattern": _BARE_EACH_LENDER,
            "amendment_type": (
                "Change defined terms affecting the Borrowing Base or "
                "Concentration Percentage; reduce or delay payment of "
                "Principal or Interest; change the definition of an Event "
                "of Default; release Collateral; release the Performance "
                "Guarantor; or change §§2.03(f), 3.02(a), 7.01-7.03, 8.01 "
                "-- unanimous, Administrative Agent and every Lender "
                "(§12.01(b)(D))"
            ),
        },
    ],
}


def voting_article_scope(document: str, text: str) -> tuple[int, int]:
    """(start, end) of THIS document's own voting/amendment article -- from
    its own heading (the same heading-location Task 11's
    `extract_amendment_assignment_articles.find_heading()` uses) through
    the start of the next article's heading (assignment/successors). Wider
    than Task 11's own 800-3,000-char-capped Mongo passage on purpose: a
    real carve-out clause can sit past that cap (Bausch, 33 chars past it)
    while still being well inside the article itself, which runs until the
    NEXT article begins. Raises if either heading is not found -- a
    fabricated or approximate scope is worse than no scope."""
    vt_hit = find_heading(text, VOTING_PATTERNS)
    assert vt_hit, f"{document}: voting/amendment article heading not found"
    vt_start = vt_hit[0]
    assign_hit = find_heading(text, ASSIGN_PATTERNS)
    scope_end = assign_hit[0] if assign_hit else len(text)
    assert scope_end > vt_start, (
        f"{document}: assignment article heading does not follow the "
        f"voting article heading -- scope [{vt_start}:{scope_end}) is "
        f"empty or inverted")
    return vt_start, scope_end


def extract_carveouts(document: str, text: str) -> list[dict]:
    scope_start, scope_end = voting_article_scope(document, text)
    out: list[dict] = []
    for spec in CARVEOUT_SPECS[document]:
        pattern = spec["pattern"]
        matches = [
            m for m in pattern.finditer(text)
            if scope_start <= m.start() < scope_end
        ]
        assert len(matches) == 1, (
            f"{document}: {spec['bucket']!r} carve-out pattern matched "
            f"{len(matches)} times inside the voting/amendment article "
            f"span [{scope_start}:{scope_end}) -- refusing to guess which "
            f"is the real clause (0 = filing text no longer demonstrates "
            f"this standard; >1 = the pattern is not specific enough for "
            f"this document, tighten it)")
        m = matches[0]
        start, end = m.span("clause") if "clause" in pattern.groupindex \
            else m.span()
        out.append({
            "bucket": spec["bucket"],
            "consent_standard": spec["consent_standard"],
            "consent_percent": None,
            "amendment_type": spec["amendment_type"],
            "source_passage": f"{document}#offset={start}-{end}",
        })
    return out


def facility_ids_for(document: str) -> list[str]:
    """Every Wave 18 facility_id this document's tranches map to, deduped
    and sorted -- read from `TRANCHE_TO_FACILITIES` (imported, never
    re-derived, per this task's brief), which already excludes Ruling
    T6-R2's two facilities (neither appears as a value anywhere in it)."""
    tranche_map = TRANCHE_TO_FACILITIES.get(document)
    assert tranche_map, f"{document}: not in ccf.syndicate.TRANCHE_TO_FACILITIES"
    ids: set[str] = set()
    for facility_ids in tranche_map.values():
        for fid in facility_ids:
            assert fid not in WAVE18_EXCLUDED_FACILITIES, (
                f"{document}: TRANCHE_TO_FACILITIES names excluded facility "
                f"{fid}")
            ids.add(fid)
    return sorted(ids)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    documents: list[dict] = []
    for document in sorted(TRANCHE_TO_FACILITIES):
        path = EX10 / document
        if not path.exists():
            raise SystemExit(f"missing source document: {path}")
        parser = TextExtractor()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        text = parser.text()

        thresholds = extract_required_lenders(document, text)
        thresholds += extract_carveouts(document, text)

        facility_ids = facility_ids_for(document)
        for t in thresholds:
            t["document"] = document
            t["facility_ids"] = facility_ids
            # Verifiability: the citation must resolve against the SAME
            # extracted text this run just produced -- a wrong offset
            # fails right here, not silently downstream in Fluree.
            off = t["source_passage"].rsplit("=", 1)[1]
            start, end = (int(x) for x in off.split("-"))
            assert text[start:end], (
                f"{document}/{t['bucket']}: offset {start}-{end} resolves "
                f"to empty text")

        print(f"  {document[:52]:54s} {len(thresholds)} thresholds  "
              f"facilities={facility_ids}")
        for t in thresholds:
            pct = f"{t['consent_percent']}%" if t["consent_percent"] else "(no %)"
            print(f"      {t['bucket']:26s} {t['consent_standard']:26s} {pct}")

        documents.append({
            "document": document,
            "facility_ids": facility_ids,
            "thresholds": thresholds,
        })

    total = sum(len(d["thresholds"]) for d in documents)
    artifact = {
        "generated_for": "wave18 · syndicated-lending-co-lender · Task 11b",
        "method": (
            "REQUIRED_LENDERS_RE (generic) for the percentage-of-exposure "
            "standard; CARVEOUT_SPECS (curated, per-document, verified live) "
            "for the elevated per-Lender veto standard"
        ),
        "documents": documents,
        "total_thresholds": total,
    }
    OUT.write_text(json.dumps(artifact, indent=2))
    print(f"\n  {total} threshold rows across {len(documents)} documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
