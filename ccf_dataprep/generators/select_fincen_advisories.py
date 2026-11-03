#!/usr/bin/env python3
"""Wave 17 Task 1 — select the four FinCEN advisories `aml-typology-match`
anchors its typologies to.

Every typology transaction this product invents must be traceable to a real,
published FinCEN advisory passage (CLAUDE.md rule 2 pairs with this: the
entities are synthetic, but the typology definitions are public and must be
cited honestly). This script does the citing — it does not invent the
advisories, it finds them.

FinCEN's public advisory index at

    https://www.fincen.gov/resources/advisoriesbulletinsfact-sheets

lists only five "Recent Advisories" and a "Read More Advisories" button. The
button leads to the actual paginated listing this script walks:

    https://www.fincen.gov/resources/advisoriesbulletinsfact-sheets/advisories?page=N

Older advisories are what this product needs -- structuring, funnel accounts,
shell-company ownership concealment, trade-based laundering are all pre-2018
topics -- so page 1 is not enough. The walk continues until a page yields no
new advisory link (the corpus is exhausted) or PAGE_CAP is hit.

**On the fourth typology.** The original brief asked for `rapid_pass_through`.
An exhaustive walk of the full 194-advisory corpus -- title and description
text, plus manual body-text checks on the strongest candidates -- found
nothing. Per a ruling from the user (not a substitution I made unilaterally):
`rapid_pass_through` is replaced with `shell_company_ownership` -- a
STRUCTURAL typology (shell companies concealing a beneficial owner), chosen
because it composes with Wave 17's existing ICJ-SPV / HLD-* / bo_chain
ownership-chain infrastructure, unlike a subject-matter advisory (who
committed a crime, not what shape the money took).

That typology's defining phrase ("shell compan...") does not appear in the
FinCEN index's title or description text for its advisory -- confirmed
empirically, matching a quick check the user ran independently. Worse, a
GENERIC unscoped scan of every advisory's index text for that phrase family
is actively unsafe here: FinCEN Advisory Issue 40 (2005, North Korean
front-company banking guidance) has "FRONT COMPANIES" sitting right in its
own index description, and an automatic first-match scan picked it --
wrongly, since it is a subject-matter advisory (about North Korean
government agencies, not the shape of the money movement), exactly the kind
of pick the user's ruling rejects. Distinguishing "structural" from
"subject-matter" is a judgment call a keyword regex cannot make safely.

So `shell_company_ownership` is resolved differently from the other three:
`_AUTO_INDEX_TYPOLOGIES` excludes it from the generic index scan, and
`_structural_candidate_pass` fetches ONE explicitly-reasoned candidate
(`_STRUCTURAL_CANDIDATE_SLUG`, with the runner-ups and why they were
rejected recorded in the comment above it) and VERIFIES its live body text
actually carries the keyword before trusting it -- a citation confirmed
against the document every run, never a hardcoded fact taken on faith, but
also never a blind sweep that can rediscover Issue 40's mistake.

**pdf_url is resolved from the advisory page HTML, never constructed.** The
same site serves PDFs under both `/sites/default/files/advisory/...` and
`/system/files/...`, so a fetcher that builds either path by pattern 404s on
about half the corpus while looking correct (this estate has already been
burned once by an assumed-shape index -- see `EDGAR index.json is
incomplete` in project memory). Worse, an advisory page routinely links
several OTHER advisories' PDFs in a "related guidance" footnote, so "the
first .pdf href on the page" is also wrong. The one true primary-document
link lives inside a `field--name-field-media-document` wrapper -- verified
against three known advisory pages during development -- and that is the
only href this script trusts.

If a typology's keyword set matches nothing across the full pagination walk,
this script does NOT emit a partial selection or substitute a loosely-related
advisory: it exits non-zero and names the typology that failed. A wrong
advisory here would silently mis-anchor every downstream typology claim,
which costs far more than stopping to ask.

Output: sources/fincen/selection.json
Run:    uv run generators/select_fincen_advisories.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

from ccf.config import REPO_ROOT
from ccf.fetch import SourceManifest, fetch, get

UA = (
    "ccf-dataprep/wave17 (+https://github.com/ccf-dataprep; "
    "contact: dcastilloaz@gmail.com) research fetch for aml-typology-match"
)

FINCEN = "https://www.fincen.gov"
# The landing page (…/advisoriesbulletinsfact-sheets) only shows the 5 most
# recent advisories plus a "Read More Advisories" link. THIS is the URL that
# actually paginates the full corpus with ?page=N — confirmed empirically
# 2026-08-24 (page=0 == unparameterized page 1; page=13 returns 0 new rows).
INDEX_URL = f"{FINCEN}/resources/advisoriesbulletinsfact-sheets/advisories"
PAGE_CAP = 30  # generous headroom over the 13 pages that exhaust the corpus

OUT_PATH = REPO_ROOT / "sources" / "fincen" / "selection.json"

TYPOLOGY_KEYWORDS = {
    "structuring": ("structuring", "structured transaction",
                     "below the reporting threshold"),
    "funnel_account": ("funnel account", "funnel"),
    "shell_company_ownership": ("shell compan", "nominee owner",
                                 "front compan", "conceal their identit"),
    "trade_based": ("trade-based money laundering", "trade based",
                     "over-invoicing", "under-invoicing"),
}

#: Only these three are matched by the automatic index (title+description)
#: scan below. `shell_company_ownership` is deliberately excluded from it --
#: development turned up a real false positive: FinCEN Advisory Issue 40
#: (2005, North Korea front-company banking guidance) has "FRONT COMPANIES"
#: sitting right in its own index DESCRIPTION text, so an unscoped scan
#: matches it immediately and wrongly. Issue 40 is exactly the disqualifying
#: shape the user's ruling named -- defined by WHO (North Korean government
#: agencies) rather than the shape of the money movement -- so a mechanical
#: "first row whose description contains the phrase" pick is not safe here.
#: `shell_company_ownership` is resolved by `_structural_candidate_pass`
#: instead: a short, explicitly-reasoned candidate list (see below),
#: each candidate verified against its own live body text before being
#: trusted -- never a blind index match, never a hardcoded fact taken on
#: faith.
_AUTO_INDEX_TYPOLOGIES = {"structuring", "funnel_account", "trade_based"}

#: Advisory pages carry the same nav/footer boilerplate on every page,
#: including the literal phrase "Beneficial Ownership Information Reporting"
#: in the site menu -- a body-text keyword scan that didn't strip this would
#: match every single advisory on the corpus on that phrase alone. The real
#: content starts at the "Advisory Information" heading; only text from there
#: onward is eligible for the structural-candidate match below.
_BODY_START_MARKER = "Advisory Information"

#: shell_company_ownership candidates, in the order they were investigated,
#: with why each was accepted or rejected. Only the winner is checked at
#: runtime (verified against live body text, not trusted blindly); the
#: rejects are recorded here so the reasoning survives in the code, not only
#: in the task report.
#:
#:   FIN-2017-A003 (Real Estate GTO advisory, 2017-08-22) -- WINNER. Body text
#:     explicitly describes shell companies used to purchase residential real
#:     estate to conceal the beneficial owner and launder proceeds. Purely
#:     structural (the mechanism is the typology, not a named actor), and it
#:     composes directly with Wave 17's existing ICJ-SPV / HLD-* / bo_chain
#:     ownership-chain infrastructure.
#:   FIN-2012-A010 (Third-Party Payment Processors) -- rejected. Structural
#:     (nested/consolidation accounts concealing the true originator from the
#:     bank), but the concealment is of a payment originator, not a beneficial
#:     OWNER, and it does not compose with the existing ownership-chain
#:     entities.
#:   FIN-2010-A011 (Informal Value Transfer Systems) -- rejected. Structural,
#:     but describes how value MOVES outside the formal system, not how
#:     ownership is concealed; no ownership-chain angle at all.
#:   FIN-2022-A001 (Kleptocracy and Foreign Public Corruption), FIN-2018-A003
#:     (Human Rights Abuses Enabled by Corrupt Senior Foreign Political
#:     Figures) -- rejected twice over. Both are subject-matter advisories
#:     (defined by WHO -- corrupt foreign officials -- not the shape of the
#:     money movement), disqualifying them under the ruling even before
#:     checking; checked anyway, and neither actually contains "shell
#:     compan[y|ies]" or "nominee" in its body text.
#:   FinCEN Advisory Issue 40 (2005, North Korean front-company banking
#:     guidance) -- rejected. This is the false positive an unscoped
#:     index/body keyword scan actually returned during development (see
#:     `_AUTO_INDEX_TYPOLOGIES` above): subject-bound to one country's
#:     government agencies, not a general structural typology.
_STRUCTURAL_CANDIDATE_SLUG = {
    "shell_company_ownership": "fincen-advisory-fin-2017-a003",
}


class _AdvisoryRowParser(HTMLParser):
    """Extracts (href, title, iso_date, description) from the advisories
    listing table. One row per <tr>; column 0 is the title link, column 1
    the <time datetime="...">, column 2 the subject/description text."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []
        self._cur: dict | None = None
        self._cur_href: str | None = None
        self._cell_idx = -1

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self._cur = {"href": "", "title": "", "date": "", "desc": ""}
            self._cell_idx = -1
            self._cur_href = None
        elif tag == "td":
            self._cell_idx += 1
        elif tag == "a" and self._cur is not None and self._cell_idx == 0:
            self._cur_href = a.get("href", "")
        elif tag == "time" and self._cur is not None and self._cell_idx == 1:
            self._cur["date"] = a.get("datetime", "")

    def handle_endtag(self, tag):
        if tag == "tr" and self._cur is not None:
            if self._cur["href"]:
                self.rows.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._cur is None:
            return
        if self._cell_idx == 0:
            self._cur["title"] += data
            if self._cur_href:
                self._cur["href"] = self._cur_href
        elif self._cell_idx == 2:
            self._cur["desc"] += data


def walk_index() -> list[dict]:
    """Walk the paginated advisories listing, returning every distinct
    advisory row found, oldest and newest alike."""
    seen: dict[str, dict] = {}
    page = 0
    while page <= PAGE_CAP:
        url = f"{INDEX_URL}?page={page}"
        resp = get(url, headers={"User-Agent": UA})
        parser = _AdvisoryRowParser()
        parser.feed(resp.text)
        new = 0
        for row in parser.rows:
            href = row["href"]
            if not href.startswith("/resources/advisories/"):
                continue
            if href not in seen:
                seen[href] = row
                new += 1
        print(f"  page {page}: {len(parser.rows)} rows, {new} new "
              f"(total {len(seen)})")
        if new == 0:
            break
        page += 1
    return list(seen.values())


def _index_pass(rows: list[dict]) -> dict[str, dict]:
    """Pass 1: does title+description contain a typology's keyword? Fast --
    no page fetches -- and where structuring, funnel_account, and trade_based
    all resolve. Deterministic tie-break: oldest issue date, then href, so a
    future corpus growing forward never changes today's pick.

    Only `_AUTO_INDEX_TYPOLOGIES` are attempted here -- see the comment on
    that set for why `shell_company_ownership` is excluded (Issue 40's own
    description contains "FRONT COMPANIES" and would win this pass wrongly)."""
    auto_keywords = {t: kw for t, kw in TYPOLOGY_KEYWORDS.items()
                      if t in _AUTO_INDEX_TYPOLOGIES}
    matches: dict[str, list[tuple[str, dict, str]]] = {t: [] for t in auto_keywords}
    for row in rows:
        title = row["title"].strip()
        desc = row["desc"].strip()
        haystacks = [("title", title), ("description", desc)]
        for typology, keywords in auto_keywords.items():
            for field_name, text in haystacks:
                lower = text.lower()
                for kw in keywords:
                    if kw in lower:
                        matched_on = f'"{kw}" in {field_name}: "{text}"'
                        matches[typology].append((row["date"], row, matched_on))
                        break
                else:
                    continue
                break  # one match recorded per row per typology is enough

    chosen: dict[str, dict] = {}
    for typology, hits in matches.items():
        if not hits:
            continue
        hits.sort(key=lambda h: (h[0], h[1]["href"]))
        date, row, matched_on = hits[0]
        chosen[typology] = {"row": row, "matched_on": matched_on, "page_html": None}
    return chosen


def _structural_candidate_pass(
    rows: list[dict], typology: str, manifest: SourceManifest,
) -> dict | None:
    """Resolve a typology whose keyword is too generic to trust an unscoped
    scan over (see `_STRUCTURAL_CANDIDATE_SLUG`'s docstring for the false
    positive that motivated this). Fetches ONLY the one curated, reasoned
    candidate slug and verifies its body text -- from `_BODY_START_MARKER`
    onward, so nav boilerplate can't contribute a match -- actually contains
    one of the typology's keywords. Never trusts the candidate on faith: if
    the live page no longer carries the phrase, this returns None and the
    caller reports the typology unresolved rather than substitute anything.
    """
    slug = _STRUCTURAL_CANDIDATE_SLUG.get(typology)
    if slug is None:
        return None
    row = next((r for r in rows if r["href"].rsplit("/", 1)[-1] == slug), None)
    if row is None:
        return None  # candidate not present in this run's corpus walk
    page_url = f"{FINCEN}{row['href']}"
    page_path = fetch(page_url, manifest, f"{slug}.html", headers={"User-Agent": UA})
    page_html = page_path.read_text()
    plain = re.sub(r"<[^>]+>", " ", page_html)
    plain = re.sub(r"\s+", " ", plain)
    marker_idx = plain.find(_BODY_START_MARKER)
    content = plain[marker_idx:] if marker_idx != -1 else plain
    lower = content.lower()
    for kw in TYPOLOGY_KEYWORDS[typology]:
        idx = lower.find(kw)
        if idx != -1:
            snippet = content[max(0, idx - 60):idx + 100].strip()
            matched_on = f'"{kw}" in advisory body text: "...{snippet}..."'
            return {"row": row, "matched_on": matched_on, "page_html": page_html}
    return None  # candidate no longer carries the phrase -- do not substitute


def match_typologies(rows: list[dict], manifest: SourceManifest) -> dict[str, dict]:
    """Index pass for the three typologies it is safe for (see
    `_AUTO_INDEX_TYPOLOGIES`), curated-candidate pass for the rest."""
    chosen = _index_pass(rows)
    for typology in TYPOLOGY_KEYWORDS:
        if typology in chosen:
            continue
        hit = _structural_candidate_pass(rows, typology, manifest)
        if hit is not None:
            chosen[typology] = hit
    return chosen


def resolve_pdf_url(page_html: str, page_url: str) -> str:
    """Parse the primary document href out of the advisory page.

    The primary link lives inside a `field--name-field-media-document`
    wrapper. Other .pdf hrefs on the page (a "related guidance" footnote
    citing OTHER advisories) live outside that wrapper and must not be
    picked up as this advisory's own PDF.
    """
    m = re.search(
        r'field--name-field-media-document.*?href="([^"]+\.pdf)"',
        page_html, re.IGNORECASE | re.DOTALL,
    )
    if not m:
        raise RuntimeError(
            f"no field--name-field-media-document PDF link found on {page_url}"
        )
    href = m.group(1)
    if href.startswith("http"):
        return href
    return f"{FINCEN}{href}"


def resolve_advisory_number(page_html: str, fallback: str) -> str:
    m = re.search(
        r'field--name-field-fin-no[^>]*>([^<]+)<', page_html,
    )
    return m.group(1).strip() if m else fallback


def main() -> int:
    print(f"Walking {INDEX_URL} ...")
    rows = walk_index()
    print(f"\n{len(rows)} distinct advisories collected across the full "
          f"pagination walk.\n")

    manifest = SourceManifest(
        source="fincen",
        description="FinCEN advisories anchoring aml-typology-match typology claims",
        licence="US government work / public advisory",
    ).load()

    chosen = match_typologies(rows, manifest)

    missing = sorted(set(TYPOLOGY_KEYWORDS) - set(chosen))
    if missing:
        print(f"BLOCKED — no advisory matched for: {', '.join(missing)}")
        print(f"  Searched {len(rows)} advisories across the full walk "
              f"(pages 0..{PAGE_CAP}, corpus exhausted before the cap), "
              f"title/description AND body text.")
        print(f"  Keywords tried for the missing typolog{'y' if len(missing)==1 else 'ies'}:")
        for t in missing:
            print(f"    {t}: {TYPOLOGY_KEYWORDS[t]}")
        print("  Not substituting a loosely-related advisory. Stopping.")
        return 1

    typologies = []
    for typology in sorted(chosen):  # deterministic output order
        hit = chosen[typology]
        row = hit["row"]
        page_url = f"{FINCEN}{row['href']}"
        slug = row["href"].rsplit("/", 1)[-1]
        page_html = hit["page_html"]
        if page_html is None:  # matched in the index pass; page not yet fetched
            page_path = fetch(page_url, manifest, f"{slug}.html",
                               headers={"User-Agent": UA})
            page_html = page_path.read_text()

        advisory_number = resolve_advisory_number(page_html, row["title"].strip())
        pdf_url = resolve_pdf_url(page_html, page_url)

        typologies.append({
            "typology": typology,
            "advisory_number": advisory_number,
            "title": row["title"].strip(),
            "issued": row["date"][:10],
            "url": page_url,
            "pdf_url": pdf_url,
            "matched_on": hit["matched_on"],
        })

    selection = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "index_url": INDEX_URL,
        "typologies": typologies,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(selection, indent=2) + "\n")
    print(f"written: {OUT_PATH.relative_to(REPO_ROOT)}\n")

    print("=" * 78)
    print("SELECTED ADVISORIES — review before Task 2")
    print("=" * 78)
    for t in typologies:
        print(f"\n  typology:  {t['typology']}")
        print(f"  number:    {t['advisory_number']}")
        print(f"  title:     {t['title']}")
        print(f"  issued:    {t['issued']}")
        print(f"  url:       {t['url']}")
        print(f"  pdf_url:   {t['pdf_url']}")
        print(f"  matched_on:{t['matched_on']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
