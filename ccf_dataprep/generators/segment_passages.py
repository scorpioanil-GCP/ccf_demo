#!/usr/bin/env python3
"""Wave 6 — segment cached EX-10 documents into structure-aligned passages.

`covenant-cross-reference` §C is specific about how this must work, and the
reasons are worth restating because they are easy to get subtly wrong:

**Structure-aligned, not fixed-window.** A 1200-character window is "a starting
point, not a commitment". Covenant definitions frequently exceed it, and a span
that truncates mid-definition produces a citation that does not support the
claim resting on it. So passages break on section and subsection boundaries,
with the character window only as a fallback where structure is absent.

**Anchors resolve by offset, never by re-searching text.** A re-search can match
a different occurrence and silently relocate the citation. So every passage
carries `{document_id, start_offset, end_offset, sha256}` and the *document text
as segmented* is stored alongside — offsets are meaningless against a
differently-extracted text.

**sha256 per passage** is what makes §8.4 verification possible: a claim whose
anchor no longer hashes to the same span is dropped and recorded as Context
Debt, not silently served.

Embeddings are deliberately NOT computed here. §E notes they are
model-version-driven and re-embedding invalidates the retrieval surface but not
the text, so they belong in a separate re-runnable pass
(`loaders/embed_passages.py`) with a recorded model version.

Output: sources/screening/passages.json  (offsets + hashes, no vectors)

Run: uv run generators/segment_passages.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys

from ccf.config import REPO_ROOT
from generators.extract_facilities import TextExtractor

SCREEN = REPO_ROOT / "sources" / "screening"

#: Section and article headings, which are the preferred break points.
STRUCTURE = re.compile(
    r"(?:^|\n)[ \t]*("
    r"ARTICLE\s+(?:[IVXLC]+|\d+)"
    r"|Article\s+(?:[IVXLC]+|\d+)"
    r"|SECTION\s+\d+(?:\.\d+)*"
    r"|Section\s+\d+(?:\.\d+)*"
    r")\b[.\s]",
)

#: A defined term opens with a quoted capitalised phrase followed by "means".
#: These are natural passage starts inside a definitions article.
DEFINITION_START = re.compile(
    r'(?:^|\n)\s*[“"“]([A-Z][A-Za-z0-9 ,\-\'/()]{3,60})[”"”]\s+'
    r'(?:means|shall\s+mean)',
)

#: Narrative filings (10-K Item 1A/7, 10-Q MD&A, 8-K EX-99) do not use
#: "Section 5.1" headings at all -- they break on standalone ALL-CAPS or
#: Title-Case lines: "OVERVIEW AND BUSINESS ENVIRONMENT", "Cost Reduction
#: Program", "Liquidity and Capital Resources". Wave 13a measured 6 of 3,892
#: passages structure-aligned without these, i.e. the whole corpus fell back to
#: a fixed window -- which is exactly what this module's own docstring says a
#: passage must not be.
#:
#: Passed in explicitly by the caller rather than added to STRUCTURE, so
#: Wave 6's EX-10 segmentation is byte-identical and its stored offsets and
#: sha256s stay valid. Offsets are the join; changing how an existing corpus
#: segments would invalidate every anchor pointing into it.
NARRATIVE_STRUCTURE = re.compile(
    r"(?:^|\n)[ \t]*("
    # ALL-CAPS heading line
    r"[A-Z][A-Z0-9 \-&,'/()]{10,90}"
    # or Title-Case heading line, not ending in a full stop
    r"|[A-Z][A-Za-z0-9]*(?:\s+(?:[A-Z][A-Za-z0-9'\-]*|of|and|the|for|in|to|a|an))"
    r"{1,9}"
    r")[ \t]*(?=\n)",
)

#: Page-furniture the HTML extraction leaves behind on every page break. Not
#: structure, and left in it would break passages every few hundred characters.
NOT_A_HEADING = re.compile(r"^(table\s+of\s+contents|index|page\s*\d*|\d+)$", re.I)

MIN_CHARS = 200
MAX_CHARS = 3000       # split anything longer on the fallback window
FALLBACK_WINDOW = 1500


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def break_points(text: str, *, narrative: bool = False) -> list[tuple[int, str]]:
    """Ordered (offset, kind) break points, structure first.

    `narrative=True` additionally breaks on the heading conventions filed
    narrative text actually uses. Default False keeps Wave 6 byte-identical.
    """
    points: list[tuple[int, str]] = []
    for m in STRUCTURE.finditer(text):
        points.append((m.start(1), "structure"))
    if narrative:
        for m in NARRATIVE_STRUCTURE.finditer(text):
            head = m.group(1).strip()
            if NOT_A_HEADING.match(head):
                continue
            points.append((m.start(1), "structure"))
    for m in DEFINITION_START.finditer(text):
        points.append((m.start(1), "definition"))
    points.sort()
    # Deduplicate near-identical offsets, preferring structure.
    deduped: list[tuple[int, str]] = []
    for offset, kind in points:
        if deduped and offset - deduped[-1][0] < 40:
            continue
        deduped.append((offset, kind))
    return deduped


def segment(text: str, document_id: str, *, narrative: bool = False) -> list[dict]:
    points = break_points(text, narrative=narrative)
    spans: list[tuple[int, int, str]] = []

    if points:
        bounds = [p[0] for p in points] + [len(text)]
        kinds = [p[1] for p in points]
        for i in range(len(points)):
            spans.append((bounds[i], bounds[i + 1], kinds[i]))
        # The head region: text before the FIRST break point. `bounds` starts
        # at that point, so without this the preamble -- parties, recitals,
        # and in a filed exhibit often the whole of a document that numbers
        # its sections late -- is covered by no span at all and no anchor can
        # reach it. Measured over the Wave 15 EX-10 corpus: 880,471 characters
        # unreachable, and `swbi-ex10_107.htm` (first marker at offset 42,968
        # of 43,198) segmented to nothing and dropped out silently.
        #
        # APPENDED, not prepended. `passage_id` is positional
        # (`{document_id}#p{idx:05d}`), so head-first would renumber every
        # later passage in the document, and 43 Fluree `ex:evidencedBy`
        # triples point at those ids in a ledger that cannot delete. Appending
        # leaves every existing id on the span it already named.
        if points[0][0] > 0:
            for start in range(0, points[0][0], FALLBACK_WINDOW):
                spans.append(
                    (start, min(start + FALLBACK_WINDOW, points[0][0]),
                     "window-head"))
    else:
        # No detectable structure — fall back to the character window, and
        # record that this passage is NOT structure-aligned so a consumer can
        # tell a clean citation from a best-effort one.
        for start in range(0, len(text), FALLBACK_WINDOW):
            spans.append((start, min(start + FALLBACK_WINDOW, len(text)), "window"))

    passages: list[dict] = []
    for start, end, kind in spans:
        # Oversized structural spans get split, keeping the alignment flag on
        # the first piece only.
        if end - start > MAX_CHARS:
            cursor = start
            piece = 0
            while cursor < end:
                stop = min(cursor + FALLBACK_WINDOW, end)
                passages.append((cursor, stop, kind if piece == 0 else "window-split"))
                cursor = stop
                piece += 1
        else:
            passages.append((start, end, kind))

    out: list[dict] = []
    for idx, (start, end, kind) in enumerate(passages):
        body = text[start:end]
        if len(body.strip()) < MIN_CHARS:
            continue
        heading = ""
        head_m = STRUCTURE.match("\n" + body[:80])
        if head_m:
            heading = head_m.group(1).strip()
        out.append({
            "passage_id": f"{document_id}#p{idx:05d}",
            "document_id": document_id,
            "start_offset": start,
            "end_offset": end,
            "length": end - start,
            "sha256": sha256(body),
            "alignment": kind,
            "structure_aligned": kind in ("structure", "definition"),
            "heading": heading,
            "text": body,
        })
    return out


def main() -> int:
    index = json.loads((SCREEN / "ex10_index.json").read_text())["documents"]
    print(f"Segmenting {len(index)} cached documents\n")

    documents: list[dict] = []
    all_passages: list[dict] = []

    for doc in index:
        path = REPO_ROOT / doc["path"]
        if not path.exists():
            continue
        parser = TextExtractor()
        try:
            parser.feed(path.read_text(errors="ignore"))
            parser.close()
        except Exception:  # noqa: BLE001
            pass
        text = parser.text()
        if len(text) < 5000:
            continue

        document_id = f"{doc['accession']}:{doc['document']}"
        passages = segment(text, document_id)
        if not passages:
            continue

        documents.append({
            "document_id": document_id,
            "cik": doc["cik"], "lei": doc["lei"],
            "sec_name": doc["sec_name"],
            "accession": doc["accession"], "document": doc["document"],
            "form": doc["form"], "filed_date": doc["filed_date"],
            "url": doc["url"],
            "text_length": len(text),
            "text_sha256": sha256(text),
            "passage_count": len(passages),
            # The extracted text IS the coordinate system for every offset.
            # Storing it is not redundancy; without it the anchors are void.
            "text": text,
            "provenance": "public",
            "source": "SEC EDGAR EX-10 exhibit",
        })
        all_passages.extend(passages)

    aligned = sum(1 for p in all_passages if p["structure_aligned"])
    kinds: dict[str, int] = {}
    for p in all_passages:
        kinds[p["alignment"]] = kinds.get(p["alignment"], 0) + 1

    print(f"  {len(documents)} documents segmented")
    print(f"  {len(all_passages):,} passages  (§F asks ~2,500)")
    print(f"  {aligned:,} structure-aligned ({100 * aligned // max(len(all_passages), 1)}%)")
    print(f"  alignment kinds: {kinds}")
    lengths = sorted(p["length"] for p in all_passages)
    if lengths:
        mid = lengths[len(lengths) // 2]
        print(f"  length: min={lengths[0]} median={mid} max={lengths[-1]}")

    (SCREEN / "passages.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 6 — structure-aligned passages with offsets",
                "note": "Offsets index into each document's stored `text`. "
                        "Anchors resolve BY OFFSET; re-searching for the text "
                        "can match a different occurrence and silently relocate "
                        "the citation. Embeddings are a separate pass.",
                "document_count": len(documents),
                "passage_count": len(all_passages),
                "structure_aligned": aligned,
                "documents": documents,
                "passages": all_passages,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: sources/screening/passages.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
