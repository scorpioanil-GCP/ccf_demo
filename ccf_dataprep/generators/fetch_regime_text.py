#!/usr/bin/env python3
"""Wave 19 Task 2 — the three large-exposure regimes, as citable text.

§C names EUR-Lex for CRR. **EUR-Lex does not work from here.** Measured
2026-08-27: every request returns HTTP 202 with a zero-byte body, including
`eur-lex.europa.eu/homepage.html`, with three user agents and with a cookie
jar; `publications.europa.eu` cellar content negotiation returns HTTP 400.
Recorded the way Wave 17 recorded FATF's 403 -- a measured fact with a date.

legislation.gov.uk carries CRR as assimilated UK law with full point-in-time
history, and it is BETTER than EUR-Lex for this product, because it records
the moment the regime changed hands: Articles 392-403 were omitted on
2022-01-01 by SI 2021/1078, when large exposures moved into the PRA Rulebook.
That is a REAL regime version boundary with a REAL effective date, which is
what §F's ">= 2 regime versions with distinct effective dates" asks for.

**The dates below are not interchangeable.** A fetch of the live CRR URL
returns an omission notice, not rule text. Measured, same day:

    2020-12-31   69,369 B   operative text present
    2021-12-31   69,337 B   operative text present
    2022-01-01   43,449 B   operative text ABSENT
    2023-01-01   43,410 B   operative text ABSENT

And the string "omitted" appears on ALL FOUR, because the textual-amendment
annotation rides along on the in-force versions too. A guard written as
`if "omitted" in html` flags every date and discriminates nothing. This script
asserts on the OPERATIVE SENTENCE and carries both controls.

    uv run generators/fetch_regime_text.py
"""
from __future__ import annotations

import re
import sys

from ccf.fetch import SourceManifest, fetch

#: prarulebook.co.uk 403s the default `python-requests/X.Y` User-Agent (a
#: generic anti-bot heuristic -- curl, a bare TCP client with no UA, and any
#: browser string all pass). Not a real access block: same pattern as
#: fetch_snc_report.py and select_fincen_advisories.py, so the same
#: descriptive, honest UA is used rather than spoofing a browser.
UA = (
    "ccf-dataprep/wave19 (+https://github.com/ccf-dataprep; "
    "contact: dcastilloaz@gmail.com) research fetch for "
    "large-exposure-rwa-concentration"
)

#: The sentence that is present only while Article 395 is in force. Chosen
#: because it is the operative prohibition, not an annotation about it.
CRR_OPERATIVE = "shall not incur an exposure"

#: Positive and negative controls for the CRR fetch. If the in-force date
#: lacks the sentence, or the omitted date carries it, the source has changed
#: shape and every downstream citation is suspect.
CRR_CONTROL_IN_FORCE = "2021-12-31"
CRR_CONTROL_OMITTED = "2022-01-01"

CRR_IN_FORCE_DATES = ("2020-12-31", "2021-12-31")
CRR_ARTICLES = tuple(range(392, 404))
CRR_URL = "https://www.legislation.gov.uk/eur/2013/575/article/{art}/{date}"

ECFR_URL = ("https://www.ecfr.gov/api/versioner/v1/full/2026-01-01/"
            "title-12.xml?part=215")

PRA_ROOT = "https://www.prarulebook.co.uk"
PRA_VERSIONS = ("01-01-2020", "01-01-2022", "01-01-2026")
PRA_GUIDANCE = {
    "pra-ss16-13.html":
        f"{PRA_ROOT}/guidance/supervisory-statements/ss16-13---large-exposures",
    "pra-ss03-25.html":
        f"{PRA_ROOT}/guidance/supervisory-statements/"
        "ss03-25---identification-of-groups-of-connected-clients-for-large-"
        "exposures-purposes",
}


def text_of(path) -> str:
    """Tags stripped, whitespace collapsed. Enough to assert on a sentence."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", raw))


def main() -> int:
    manifest = SourceManifest(
        source="regimes",
        description=("Large-exposure regime text: Regulation O (eCFR), CRR "
                     "as assimilated UK law (legislation.gov.uk, EUR-Lex "
                     "blocked), and the PRA Rulebook Large Exposures Part"),
        licence="US government work; UK Open Government Licence v3.0",
    ).load()

    failures: list[str] = []

    print("Regulation O -- 12 CFR 215, eCFR versioner API")
    rego = fetch(ECFR_URL, manifest, "reg-o-12cfr215.xml")
    body = text_of(rego)
    for needle in ("$500,000", "unimpaired capital and unimpaired surplus"):
        if needle not in body:
            failures.append(f"Reg O text lacks {needle!r}")
    print(f"  {rego.name}  {rego.stat().st_size:,} B")

    print("\nCRR Articles 392-403 -- legislation.gov.uk, point-in-time")
    for date in CRR_IN_FORCE_DATES:
        for art in CRR_ARTICLES:
            fetch(CRR_URL.format(art=art, date=date), manifest,
                  f"crr-art-{art}-{date}.html")
        print(f"  {date}  {len(CRR_ARTICLES)} articles")

    # The omission notice, kept as evidence of the version boundary -- it is
    # version history, NOT rule text, and nothing may cite it as a provision.
    fetch(CRR_URL.format(art=395, date=CRR_CONTROL_OMITTED), manifest,
          f"crr-art-395-{CRR_CONTROL_OMITTED}.html")

    print("\n  controls:")
    in_force = text_of(manifest.directory /
                       f"crr-art-395-{CRR_CONTROL_IN_FORCE}.html")
    omitted = text_of(manifest.directory /
                      f"crr-art-395-{CRR_CONTROL_OMITTED}.html")
    if CRR_OPERATIVE not in in_force:
        failures.append(f"positive control: {CRR_CONTROL_IN_FORCE} lacks the "
                        f"operative sentence")
    if CRR_OPERATIVE in omitted:
        failures.append(f"negative control: {CRR_CONTROL_OMITTED} carries the "
                        f"operative sentence though the article was omitted")
    # The trap, asserted so nobody re-introduces the naive guard.
    if "omitted" not in in_force:
        failures.append("the 'omitted' annotation is absent from the in-force "
                        "version -- the source changed shape; re-read before "
                        "trusting any guard written against it")
    print(f"    in force {CRR_CONTROL_IN_FORCE}: operative sentence present")
    print(f"    omitted  {CRR_CONTROL_OMITTED}: operative sentence absent")
    print(f"    'omitted' appears on BOTH -- never guard on that string")

    print("\nPRA Rulebook -- Large Exposures, point-in-time in the URL")
    for version in PRA_VERSIONS:
        p = fetch(f"{PRA_ROOT}/pra-rules/large-exposures/{version}", manifest,
                  f"pra-large-exposures-{version}.html",
                  headers={"User-Agent": UA})
        if "25%" not in text_of(p):
            failures.append(f"PRA {version} lacks a 25% limit")
        print(f"  {version}  {p.stat().st_size:,} B")
    for filename, url in PRA_GUIDANCE.items():
        p = fetch(url, manifest, filename, headers={"User-Agent": UA})
        print(f"  {filename}  {p.stat().st_size:,} B")

    manifest.save()

    if failures:
        print("\nFAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK -- three regimes fetched, controls hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
