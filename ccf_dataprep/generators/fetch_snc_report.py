#!/usr/bin/env python3
"""Wave 18 Task 12 -- fetch and extract the Shared National Credit (SNC)
Program annual report.

`covenant-cross-reference`'s and `syndicated-lending-co-lender`'s §C both
name this document specifically as the public source for supervisory
context on large syndicated credits: it is published jointly by the Board
of Governors of the Federal Reserve System, the FDIC and the OCC.

**Locating it.** Searched federalreserve.gov and occ.gov 2026-08-26. The
narrative commentary lives in the Federal Reserve's short press release
(`bcreg20260112a.htm`); the filed report attachment carrying the actual
exhibits, tables and supervisory findings is served identically from BOTH
agencies:

  - https://www.occ.gov/publications-and-resources/publications/shared-national-credit-report/files/shared-national-credit-report-2025.pdf
  - https://www.federalreserve.gov/newsevents/pressreleases/files/bcreg20260112a1.pdf

The two PDFs are not byte-identical (different embedded producer metadata --
395,743 vs 407,088 bytes) but `pypdf` extracts byte-for-byte identical TEXT
from both (verified 2026-08-26: 20,555 characters, sha256-equal). This
generator fetches the OCC copy -- OCC's URL follows a stable
`shared-national-credit-report-<year>.pdf` pattern for every prior year's
report back to 2009, which the Fed's press-release-linked filename does not.

**Why the PDF, not the HTML landing page.** occ.gov's
`shared-national-credit-report-2025.html` is a stub linking to the PDF; all
content is in the PDF.

**pypdf stability, checked for THIS file specifically** (the caveat in
`generators/extract_advisory_passages.py` is real for at least one other
PDF in this estate): re-extracted the same downloaded file three times in
three separate `uv run python` processes on 2026-08-26 and got the
identical sha256 every time. Still: per that module's own rule, offsets/ids
must never be keyed on a hash of the extracted text, only on content
genuinely stable across runs -- this document has no passages (see below),
and `document_id` is derived from the stable upstream filename, not from
`text_sha256`.

**No passages.** §C's SNC row asks for the document, not span-level
citations into it (unlike Task 11's voting-threshold/assignment work) --
`covenant-cross-reference` and `syndicated-lending-co-lender` cite this
report as supervisory CONTEXT, never as a source of a claim with an offset.
Inventing passages here would be exactly the "second schema nobody asked
for" this estate's docstrings keep warning against.

Output:
  sources/snc/shared-national-credit-report-2025.pdf  (payload, gitignored)
  sources/snc/manifest.json                            (fetch provenance)
  sources/snc/extract.json                              (text + metadata,
                                                           read by
                                                           loaders/load_mongo_wave18.py)

Run: uv run generators/fetch_snc_report.py
"""

from __future__ import annotations

import hashlib
import json
import sys

from pypdf import PdfReader

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch

UA = (
    "ccf-dataprep/wave18 (+https://github.com/ccf-dataprep; "
    "contact: dcastilloaz@gmail.com) research fetch for "
    "syndicated-lending-co-lender / covenant-cross-reference"
)

URL = (
    "https://www.occ.gov/publications-and-resources/publications/"
    "shared-national-credit-report/files/shared-national-credit-report-2025.pdf"
)
FILENAME = "shared-national-credit-report-2025.pdf"
DOCUMENT_ID = "shared-national-credit-report-2025"

SNC_DIR = REPO_ROOT / "sources" / "snc"
EXTRACT_PATH = SNC_DIR / "extract.json"

#: Below this, extraction did not really happen (§F/test floor is 5,000).
_MIN_TEXT_CHARS = 5_000


def extract_pdf_text(path) -> str:
    reader = PdfReader(str(path))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def main() -> int:
    manifest = SourceManifest(
        source="snc",
        description=(
            "Shared National Credit (SNC) Program annual review -- joint "
            "Federal Reserve / OCC / FDIC report on large syndicated credits"
        ),
        licence="US government work / public report",
    ).load()

    path = fetch(URL, manifest, FILENAME, headers={"User-Agent": UA})

    manifest.load()
    rec = next((r for r in manifest.fetches if r.url == URL), None)
    if rec is None:
        print(f"BLOCKED -- fetch() recorded no manifest entry for {URL}")
        return 1

    head = path.read_bytes()[:4] if path.exists() else b""
    if head != b"%PDF":
        print(f"BLOCKED -- payload does not start with %PDF (got {head!r})")
        return 1

    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    text = extract_pdf_text(path)
    text_length = len(text)
    text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    pdf_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

    if text_length <= _MIN_TEXT_CHARS:
        print(f"BLOCKED -- extracted only {text_length} chars "
              f"(<= {_MIN_TEXT_CHARS}); the PDF body did not extract")
        return 1

    SNC_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACT_PATH.write_text(json.dumps({
        "document_id": DOCUMENT_ID,
        "url": URL,
        "source": ("Federal Reserve / OCC / FDIC — Shared National Credit "
                    "Program annual review"),
        "retrieved_at": rec.retrieved_at,
        "page_count": page_count,
        "pdf_bytes": rec.bytes,
        "pdf_sha256": pdf_sha256,
        "text": text,
        "text_length": text_length,
        "text_sha256": text_sha256,
    }, indent=2) + "\n")

    print(f"ok: {rec.bytes:,} PDF bytes, {page_count} pages, "
          f"{text_length:,} extracted chars, sha256:{pdf_sha256[:12]}…")
    print(f"  -> {EXTRACT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
