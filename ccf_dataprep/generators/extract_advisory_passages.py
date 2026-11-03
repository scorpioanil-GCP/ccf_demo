#!/usr/bin/env python3
"""Wave 17 Task 3 — extract FinCEN advisory PDFs into paragraph passages.

Reads `sources/fincen/selection.json` (Task 1 — one typology per advisory)
and `sources/fincen/manifest.json` (Task 2 — the fetched PDFs), and produces
`sources/screening/wave17_advisory_passages.json`: one `document` record per
advisory PDF plus its `passage` records with character-offset spans.

**Why PDF, not the cached HTML page.** Measured 2026-08-24: the cached
advisory HTML yields only ~2,057 characters of navigation boilerplate: the
advisory body lives solely in the linked PDF. So this is the project's first
generator to read a PDF, via `pypdf` (pure Python, permissive licence, added
to `pyproject.toml` for exactly this task).

**Offsets are computed from the SAME string stored as `document.text`.**
`pypdf` extraction is not byte-stable across re-extractions of the same file
(whitespace can differ), so offsets computed against a second extraction can
silently select the wrong words while still looking well-formed. Every
offset here is computed against the one `text` string that is then written
to the artifact and, unmodified, becomes `document.text` in Mongo.

**Passages split on blank-line paragraph boundaries** (FinCEN advisories are
short memos, not structured credit agreements with ARTICLE/SECTION headings,
so `generators/segment_passages.py`'s structure regex would not fire here).
An oversized paragraph is further windowed so no single passage is
unreasonably long to cite.

**IDs are derived from content, never from a query-result position.**
`document_id` comes from the advisory number (`FIN-2014-A005` -> lowercase,
content-stable). `passage_id` is `{document_id}#{sha256(paragraph text)[:12]}`,
so identical text always earns the identical id and an unrelated re-run (or
a change in how many passages exist) can never shift what an existing id
points at. A same-document hash collision (two identical paragraphs) is
disambiguated with a trailing `-2`, `-3`, ... suffix assigned as duplicates
are found in this document's own list -- not by position in any external
ordering.

**Field names follow the estate convention** (`document_id`, `passage_id`,
`start_offset`, `end_offset`) rather than inventing a second set for the
same offsets -- two fields holding the same value are two things that can
drift apart later. See `docs/wave17-plan.md`'s Task 3 controller ruling.

Run: uv run generators/extract_advisory_passages.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys

from pypdf import PdfReader

from ccf.config import REPO_ROOT

FINCEN = REPO_ROOT / "sources" / "fincen"
SCREEN = REPO_ROOT / "sources" / "screening"
OUT = SCREEN / "wave17_advisory_passages.json"

MIN_CHARS = 200      # shorter than this isn't specific enough to anchor a claim
MAX_CHARS = 3000      # longer than this gets windowed
FALLBACK_WINDOW = 1500

#: Blank-line paragraph boundary. Advisory PDFs are short memos with
#: footnote blocks, not ARTICLE/SECTION-structured credit agreements.
PARA_SEP = re.compile(r"\n[ \t]*\n[ \t\n]*")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_pdf_text(path) -> str:
    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def paragraph_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) spans between blank-line separators, trimmed of the
    whitespace at each edge -- offsets computed purely from separator match
    positions, never by re-searching for the paragraph's own text (which
    would pick the wrong occurrence for any paragraph that repeats)."""
    bounds: list[tuple[int, int]] = []
    cursor = 0
    for m in PARA_SEP.finditer(text):
        bounds.append((cursor, m.start()))
        cursor = m.end()
    bounds.append((cursor, len(text)))

    spans: list[tuple[int, int]] = []
    for start, end in bounds:
        raw = text[start:end]
        lstrip = len(raw) - len(raw.lstrip())
        rstrip = len(raw) - len(raw.rstrip())
        s, e = start + lstrip, end - rstrip
        if e > s:
            spans.append((s, e))
    return spans


def windowed(start: int, end: int) -> list[tuple[int, int]]:
    """Split an oversized span on a fixed character window, still expressed
    as offsets into the ONE extracted-text string the caller holds."""
    if end - start <= MAX_CHARS:
        return [(start, end)]
    out = []
    cursor = start
    while cursor < end:
        stop = min(cursor + FALLBACK_WINDOW, end)
        out.append((cursor, stop))
        cursor = stop
    return out


def build_passages(document_id: str, text: str, advisory_number: str,
                    typology: str) -> list[dict]:
    seen_hash: dict[str, int] = {}
    passages: list[dict] = []
    for start, end in paragraph_spans(text):
        for s, e in windowed(start, end):
            body = text[s:e]
            if len(body) < MIN_CHARS:
                continue
            h = sha256(body)[:12]
            n = seen_hash.get(h, 0)
            seen_hash[h] = n + 1
            pid = f"{document_id}#{h}" if n == 0 else f"{document_id}#{h}-{n + 1}"
            passages.append({
                "passage_id": pid,
                "document_id": document_id,
                "start_offset": s,
                "end_offset": e,
                "length": e - s,
                "text": body,
                "advisory_number": advisory_number,
                "typology": typology,
                "provenance": "public",
            })
    return passages


def main() -> int:
    selection = json.loads((FINCEN / "selection.json").read_text())
    manifest = json.loads((FINCEN / "manifest.json").read_text())
    by_url = {r["url"]: r for r in manifest["fetches"]}

    print("Wave 17 Task 3 — extracting FinCEN advisory PDFs\n")

    documents: list[dict] = []
    all_passages: list[dict] = []

    for t in selection["typologies"]:
        rec = by_url.get(t["pdf_url"])
        if rec is None:
            print(f"  MISSING manifest entry for {t['typology']}: {t['pdf_url']}")
            continue
        path = REPO_ROOT / rec["path"]
        if not path.exists():
            print(f"  MISSING on disk: {rec['path']}")
            continue

        text = extract_pdf_text(path)
        advisory_number = t["advisory_number"]
        document_id = f"fincen-advisory-{advisory_number.lower()}"

        passages = build_passages(document_id, text, advisory_number, t["typology"])

        documents.append({
            "document_id": document_id,
            "doc_type": "fincen_advisory",
            "advisory_number": advisory_number,
            "typology": t["typology"],
            "title": t["title"],
            "issued": t["issued"],
            "url": t["url"],
            "pdf_url": t["pdf_url"],
            "path": rec["path"],
            "text": text,
            "text_length": len(text),
            "text_sha256": sha256(text),
            "passage_count": len(passages),
            "provenance": "public",
            "source": f"FinCEN Advisory {advisory_number} (PDF)",
            "retrieved_at": rec["retrieved_at"],
        })
        all_passages.extend(passages)
        print(f"  {advisory_number:<16} {t['typology']:<22} "
              f"{len(text):>7,} chars -> {len(passages):>3} passages")

    print(f"\n  {len(documents)} documents, {len(all_passages)} passages total "
          f"(brief asks >= 40)")

    OUT.write_text(
        json.dumps(
            {
                "generated_for": "Wave 17 Task 3 — FinCEN advisory passages",
                "note": "Offsets index into each document's own stored `text` "
                        "(the exact string extracted here, never re-extracted). "
                        "document_id and passage_id are derived from the "
                        "advisory number and passage content, not from any "
                        "query-result position.",
                "document_count": len(documents),
                "passage_count": len(all_passages),
                "documents": documents,
                "passages": all_passages,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
