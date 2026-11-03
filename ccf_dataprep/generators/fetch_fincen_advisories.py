#!/usr/bin/env python3
"""Wave 17 Task 2 — fetch the four selected FinCEN advisory PDFs.

Task 1 (`select_fincen_advisories.py`) already resolved each typology's
primary-document PDF link from the advisory page's own
`field--name-field-media-document` wrapper and recorded it as `pdf_url` in
`sources/fincen/selection.json`. This script does NOT re-resolve or
reconstruct that URL -- it reads `pdf_url` straight from the artifact and
fetches exactly that, through the shared `ccf.fetch.fetch()` harness so the
rate limiter, manifest shape, and `already_fetched()` idempotency
short-circuit are reused rather than reinvented.

It shares `sources/fincen/manifest.json` with Task 1 (which cached the
advisory HTML pages there) -- `SourceManifest.load()` reads whatever is
already on disk, and `fetch()` appends to it, so the four PDF records land
alongside the four HTML records without disturbing them.

FinCEN serves a styled HTML error page with HTTP 200 for a bad path, so a
successful status code proves nothing about what got downloaded. Every fetch
here is verified twice after the fact, against the manifest record `fetch()`
just wrote:

  * the response's `Content-Type` was `application/pdf`
  * the file on disk actually starts with the `%PDF` magic bytes

A mismatch means a mis-served page was captured under a PDF's name. The bad
record and the bad file are both removed rather than left to look like a
successful fetch, and the run is reported as blocked.

Output: sources/fincen/<advisory_number>.pdf (git-ignored payloads),
        sources/fincen/manifest.json (extended, committed)
Run:    uv run generators/fetch_fincen_advisories.py
"""

from __future__ import annotations

import sys

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch

UA = (
    "ccf-dataprep/wave17 (+https://github.com/ccf-dataprep; "
    "contact: dcastilloaz@gmail.com) research fetch for aml-typology-match"
)

SELECTION_PATH = REPO_ROOT / "sources" / "fincen" / "selection.json"

#: Minimum byte count to distinguish a real advisory PDF from an HTML error
#: page served at HTTP 200. Belt-and-suspenders alongside the content-type
#: and magic-byte checks below -- any one of the three would probably catch
#: FinCEN's known failure mode, but all three catch it for the right reason
#: rather than by coincidence.
_MIN_PDF_BYTES = 20_000


def _pdf_filename(advisory_number: str) -> str:
    """`FIN-2014-A005` -> `fin-2014-a005.pdf`. Keyed to the advisory number,
    not the typology label or the messy upstream basename (one selected PDF
    is served as `Risk%20in%20Real%20Estate%20Advisory_FINAL...pdf`) -- the
    advisory number is the stable, citable identifier."""
    return f"{advisory_number.strip().lower()}.pdf"


def main() -> int:
    import json

    if not SELECTION_PATH.exists():
        print(f"BLOCKED — {SELECTION_PATH} does not exist. Run "
              f"generators/select_fincen_advisories.py first.")
        return 1

    selection = json.loads(SELECTION_PATH.read_text())

    manifest = SourceManifest(
        source="fincen",
        description="FinCEN advisories anchoring aml-typology-match typology claims",
        licence="US government work / public advisory",
    ).load()

    failures: list[str] = []

    for t in selection["typologies"]:
        typology = t["typology"]
        pdf_url = t["pdf_url"]
        filename = _pdf_filename(t["advisory_number"])

        print(f"{typology} ({t['advisory_number']}):")
        path = fetch(pdf_url, manifest, filename, headers={"User-Agent": UA})

        # Re-load so we're reading exactly what fetch() just persisted,
        # whether this call fetched fresh bytes or short-circuited on a
        # prior cached fetch.
        manifest.load()
        rec = next((r for r in manifest.fetches if r.url == pdf_url), None)
        if rec is None:
            failures.append(f"{typology}: fetch() returned but recorded no "
                             f"manifest entry for {pdf_url}")
            continue

        content_type = (rec.content_type or "").split(";")[0].strip().lower()
        head = path.read_bytes()[:4] if path.exists() else b""

        bad_reasons = []
        if content_type != "application/pdf":
            bad_reasons.append(f"content-type {rec.content_type!r} != application/pdf")
        if head != b"%PDF":
            bad_reasons.append(f"payload does not start with %PDF (got {head!r})")
        if rec.bytes <= _MIN_PDF_BYTES:
            bad_reasons.append(
                f"{rec.bytes} bytes <= {_MIN_PDF_BYTES} -- too small for an "
                f"advisory PDF, likely an HTML error page"
            )

        if bad_reasons:
            print(f"  BAD FETCH: {'; '.join(bad_reasons)}")
            # Do not leave a record that looks like a successful fetch.
            manifest.fetches = [f for f in manifest.fetches if f.url != pdf_url]
            manifest.save()
            path.unlink(missing_ok=True)
            failures.append(f"{typology} ({pdf_url}): {'; '.join(bad_reasons)}")
            continue

        print(f"  ok: {rec.bytes:,} bytes, sha256:{rec.sha256[:12]}…, "
              f"{rec.content_type}")

    if failures:
        print("\nBLOCKED — one or more advisory PDFs failed verification:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"\nAll {len(selection['typologies'])} advisory PDFs fetched and "
          f"verified. manifest: {manifest.manifest_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
