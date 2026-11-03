#!/usr/bin/env python3
"""Wave 18 Task 11 -- locate the voting-threshold/amendment-mechanics article
and the assignment-and-transfer article in each of the six governing EX-10
agreements (`ccf.syndicate.TRANCHE_TO_FACILITIES`), with real character
offsets against the SAME extracted text every other Wave 18 offset already
points into (`generators.extract_facilities.TextExtractor`, the extractor
Task 2's schedule parser and Task 9's amendment-date parser both use).

## Locating an article by its own language, not its position

Neither article has a stable section NUMBER across these six filers (RB
Global's assignment article is "11.06"; Sabre's is "SECTION 12.06"; AHR's is
a bare "10.06" under an "X. MISCELLANEOUS" article heading). What is stable
is the WORDING two kinds of clause use to open themselves, and the fact that
a real clause launches straight into operative prose -- almost always its
own first lettered subsection, "(a) ..." -- while a table-of-contents ROW
for the same heading is followed within a few characters by a page number.

    VOTING_PATTERNS   "Amendments, Etc." / "Waivers; Amendments." /
                      "Amendments; Waivers" / "Amendments and Waivers" --
                      every filer's own name for the clause that sets
                      Required-Lenders / each-affected-Lender / all-Lenders
                      consent thresholds for changing the agreement.
    ASSIGN_PATTERNS   "Successors and Assigns." / "Assignments and
                      Participations." -- the clause governing who a Lender
                      may transfer its rights and obligations to.

`_is_heading()` accepts a match only if (a) it is not immediately followed by
a bare page number (`_toc_noise`, the flattened-<table> TOC row shape), and
(b) it is either immediately followed by "(a)" (the clause's own first
subsection) or immediately PRECEDED by a section-number token ("11.06",
"SECTION 12.01", "10.1", "ARTICLE XI"). Verified by hand against all six
filings before being written as a general rule -- see the module's own test
fixtures and `docs/wave18-design.md` §5 -- not tuned to one filer's layout
and then assumed to generalise.

Two documents (Paychex) carry a SECOND "Successors and Assigns." heading
belonging to an attached Guaranty exhibit, not the Credit Agreement itself
(`SECTION 13. Successors and Assigns.`, further into the filing). The
EARLIEST valid heading match is taken deliberately -- the Credit Agreement's
own article always precedes an attached exhibit's restatement of the same
caption in these filings.

## Span length

`_snap_end()` bounds each captured passage between 800 and 3,000 characters
(the same MAX_CHARS a structural passage is capped at in
`generators/segment_passages.py`), preferring the LAST paragraph break
("\\n\\n") inside that window so the passage does not end mid-word. EDGAR's
own page-break furniture (a bare page number between blank lines) sometimes
sits close enough to end a passage earlier than the full window; the passage
is still exactly what `text[start:end]` says it is, which is the only
invariant that matters for a lineage anchor.

## If an article is genuinely absent

Not exercised in this corpus -- both articles were found, by heading, in all
six agreements (see `docs/wave18-design.md` and the Task 11 report for the
per-document offsets and surrounding text). But the rule is enforced in code,
not just observed to hold today: a kind with NO valid heading match is
recorded in `artifact["absent"]`, not given a fabricated or approximate span.

Output: sources/screening/wave18_amendment_assignment.json
Run:    uv run generators/extract_amendment_assignment_articles.py
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date

from ccf.config import REPO_ROOT
from ccf.syndicate import TRANCHE_TO_FACILITIES
from generators.extract_facilities import TextExtractor

EX10 = REPO_ROOT / "sources" / "ex10"
SCREEN = REPO_ROOT / "sources" / "screening"
INDEX = SCREEN / "ex10_index.json"
OUT = SCREEN / "wave18_amendment_assignment.json"

VOTING_PATTERNS = [
    re.compile(r"Amendments,?\s*Etc\.?", re.I),
    re.compile(r"Waivers;\s*Amendments\.?", re.I),
    re.compile(r"Amendments;\s*Waivers", re.I),
    re.compile(r"Amendments\s+and\s+Waivers\b", re.I),
]
ASSIGN_PATTERNS = [
    re.compile(r"Successors\s+and\s+Assigns\.?", re.I),
    re.compile(r"Assignments?\s+and\s+Participations?\.?", re.I),
]

#: A section-number token immediately BEFORE a heading candidate -- the
#: second way (besides a trailing "(a)") a real heading is recognised.
_NUM_PREFIX = re.compile(
    r"(?:SECTION\s+[\dIVXLCM]+(?:\.\d{1,2})?\.?|"
    r"\bARTICLE\s+[IVXLCM]+\.?|"
    r"\d{1,2}\.\d{1,2})\s*$",
    re.I,
)

MIN_LEN = 800
MAX_LEN = 3000


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _toc_noise(text: str, end_pos: int, window: int = 30) -> bool:
    """A flattened <table> TOC row: heading, then almost immediately a bare
    page number (optionally through a "|" cell boundary)."""
    tail = text[end_pos:end_pos + window]
    return bool(re.match(r"[\s|]*\d{1,4}\b", tail))


def _is_heading(text: str, start: int, end: int) -> bool:
    tail = text[end:end + 40]
    if re.match(r"[\s.]{0,20}\([Aa]\)", tail):
        return True
    head = text[max(0, start - 40):start]
    return bool(_NUM_PREFIX.search(head))


def find_heading(text: str, patterns: list[re.Pattern]) -> tuple[int, int, str] | None:
    """Earliest valid heading match across all patterns, or None."""
    candidates: list[tuple[int, int, str]] = []
    for pat in patterns:
        for m in pat.finditer(text):
            if _toc_noise(text, m.end()):
                continue
            if _is_heading(text, m.start(), m.end()):
                candidates.append((m.start(), m.end(), m.group(0)))
    candidates.sort()
    return candidates[0] if candidates else None


def _snap_end(text: str, start: int, *, min_len: int = MIN_LEN,
              max_len: int = MAX_LEN) -> int:
    hard_max = min(start + max_len, len(text))
    idx = text.rfind("\n\n", start + min_len, hard_max)
    return idx if idx != -1 else hard_max


def extract_one(document: str, text: str) -> tuple[list[dict], list[str]]:
    """(passages, absent_kinds) for one document's extracted text."""
    passages: list[dict] = []
    absent: list[str] = []
    for kind, patterns in (("voting_threshold", VOTING_PATTERNS),
                            ("assignment_provision", ASSIGN_PATTERNS)):
        hit = find_heading(text, patterns)
        if hit is None:
            absent.append(kind)
            continue
        start, _, heading_text = hit
        end = _snap_end(text, start)
        body = text[start:end]
        passages.append({
            "passage_kind": kind,
            "document": document,
            "start_offset": start,
            "end_offset": end,
            "length": end - start,
            "heading": heading_text.replace("\n", " ").strip(),
            "text": body,
            "sha256": sha256(body),
        })
    return passages, absent


def main() -> int:
    index = {
        f"{d['cik']}_{d['accession']}_{d['document']}": d
        for d in json.loads(INDEX.read_text())["documents"]
    }

    documents: list[dict] = []
    all_absent: list[dict] = []
    today = date.today().isoformat()

    for document in sorted(TRANCHE_TO_FACILITIES):
        meta = index.get(document)
        if meta is None:
            raise SystemExit(f"{document}: not found in {INDEX}")
        path = EX10 / document
        if not path.exists():
            raise SystemExit(f"missing source document: {path}")

        parser = TextExtractor()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        text = parser.text()

        passages, absent = extract_one(document, text)

        print(f"  {document[:52]:54s} "
              f"{len(passages)}/2 articles found"
              + (f"  ABSENT: {absent}" if absent else ""))
        for p in passages:
            print(f"      {p['passage_kind']:22s} @{p['start_offset']:>8}-"
                  f"{p['end_offset']:<8} {p['length']:>5} chars  "
                  f"heading={p['heading']!r}")
        for kind in absent:
            all_absent.append({"document": document, "passage_kind": kind})

        documents.append({
            "document": document,
            "cik": meta["cik"], "lei": meta["lei"], "sec_name": meta["sec_name"],
            "accession": meta["accession"], "form": meta["form"],
            "filed_date": meta["filed_date"], "url": meta["url"],
            "text": text,
            "text_length": len(text),
            "text_sha256": sha256(text),
            "passages": passages,
        })

    artifact = {
        "generated_for": "wave18 · syndicated-lending-co-lender · Task 11",
        "method": "heading-anchored regex search over TextExtractor'd EX-10 text",
        "retrieved_at": today,
        "documents": documents,
        "absent": all_absent,
    }
    OUT.write_text(json.dumps(artifact, indent=2))

    total = sum(len(d["passages"]) for d in documents)
    print(f"\n  {total} article passages across {len(documents)} documents"
          f"  ({len(all_absent)} absent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
