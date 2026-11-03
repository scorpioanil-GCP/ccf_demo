#!/usr/bin/env python3
"""Wave 4 — extract facility terms from cached EX-10 credit agreements.

The approved approach for this project is LLM-extract plus deterministic
verify. This runs the **deterministic pass first** and reports its yield,
because credit agreements are highly conventional in exactly the places
`facility-terms-snapshot` §C needs:

    facility type      "Revolving Credit Facility", "Term A Loan", "Tranche B"
    commitment         "$750,000,000 aggregate principal amount"
    maturity           "Maturity Date" ... a date
    admin agent        "as Administrative Agent"
    pricing grid       Applicable Margin table keyed on a leverage ratio
    syndication        a lender list, or "Joint Lead Arrangers"

Where deterministic extraction is confident, an LLM adds cost and a
reproducibility problem without adding accuracy. Where it is not confident,
this reports the gap so the LLM pass in Wave 5 (covenants, which are genuinely
hard) knows what it must cover.

Every extracted value carries the character offset it came from, so the Wave 6
MongoDB load can anchor a passage to it and §8.4 verification has something to
check against.

Output: sources/screening/facilities_extracted.json

Run: uv run generators/extract_facilities.py
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"


class TextExtractor(HTMLParser):
    """Flatten HTML to text, preserving approximate offsets."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        elif tag in ("p", "div", "tr", "br", "table", "li"):
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t\xa0]+", " ", raw)
        return re.sub(r"\n{3,}", "\n\n", raw)


MONEY = r"\$\s?([\d,]{7,})"

FACILITY_PATTERNS = [
    ("revolver", re.compile(
        r"(revolving\s+credit\s+(?:facility|commitments?|loans?)|"
        r"revolving\s+commitments?)", re.IGNORECASE)),
    ("term_a", re.compile(
        r"(term\s+(?:loan\s+)?a\s+(?:loans?|facility|commitments?)|"
        r"term\s+a\s+loans?|tranche\s+a\s+term)", re.IGNORECASE)),
    ("term_b", re.compile(
        r"(term\s+(?:loan\s+)?b\s+(?:loans?|facility|commitments?)|"
        r"term\s+b\s+loans?|tranche\s+b\s+term)", re.IGNORECASE)),
    ("delayed_draw", re.compile(
        r"delayed\s+draw\s+term\s+loans?", re.IGNORECASE)),
    ("term_loan", re.compile(
        r"\bterm\s+loan\s+(?:facility|commitments?)\b", re.IGNORECASE)),
]

#: Anchor. The institution name always PRECEDES this phrase, so
#: extract_agent() walks BACKWARDS from it -- see the function docstring
#: for why a forward match can't be trusted here.
AGENT_ANCHOR = re.compile(
    r",?\s*(?:not\s+in\s+its\s+individual\s+capacity\s+but\s+solely\s+)?"
    r"as\s+(?:the\s+)?administrative\s+agent", re.IGNORECASE)

#: Connective phrases that sit between the name and the anchor in real
#: preambles ("JPMORGAN CHASE BANK, N.A., in its capacity as
#: Administrative Agent"). Stripped from the RIGHT of the window,
#: repeatedly, before the backward token walk runs.
AGENT_CONNECTIVES = re.compile(
    r"(?:,?\s*(?:in\s+its\s+capacit(?:y|ies)|in\s+such\s+capacity|"
    r"not\s+in\s+its\s+individual\s+capacity(?:\s+but\s+solely)?|"
    r"acting|solely)\s*)+$", re.IGNORECASE)

#: A parenthetical short-form alias right before the anchor ("Wells Fargo
#: Bank, National Association (“Wells Fargo”), as Administrative
#: Agent") -- the institution name is the FULL name before the
#: parenthetical, not the quoted short form inside it. Stripped from the
#: RIGHT of the window in the same loop as AGENT_CONNECTIVES.
AGENT_PAREN_ALIAS = re.compile(r"\(\s*[^()]{1,80}\)\s*,?\s*$")

#: A single token that can be part of an institution name: starts with a
#: capital letter (upper- or mixed-case text both satisfy this), then any
#: run of letters/digits and the punctuation real legal names use --
#: '&', '.' (for "N.A."/"Inc."), apostrophes, hyphens.
AGENT_NAME_TOKEN = re.compile(r"^[A-Z][A-Za-z0-9&.'\-]*$")

#: The one lowercase word allowed INSIDE a name ("Bank of America") without
#: being able to start or extend one on its own.
AGENT_NAME_CONNECTORS = frozenset({"of"})

#: Boilerplate/clause words that must never be captured as (part of) an
#: institution name, checked case-INsensitively so an ALL-CAPS cover page
#: ("...LENDERS PARTY HERETO, JPMORGAN CHASE BANK, N.A.") is caught too --
#: capitalisation alone can't distinguish a clause word from a name there.
AGENT_STOP_WORDS = frozenset({
    "and", "or", "by", "among", "the", "a", "an", "in", "on", "for", "as",
    "not", "its", "individual", "with", "together", "successors", "assigns",
    "capacity", "capacities", "solely", "acting", "means", "mean", "shall",
    "party", "parties", "hereto", "hereof", "hereby", "thereto", "thereof",
    "signature", "signatures", "pages", "page", "listed", "identified",
    "each", "such", "any", "other", "certain", "from", "time", "to",
    "financial", "institutions", "institution", "lenders", "lender",
    "borrower", "borrowers", "guarantor", "guarantors", "issuer", "issuers",
    "agent", "agents", "collateral", "documentation", "syndication",
    "arranger", "arrangers",
})
#: "the" is in the stop set above because it's overwhelmingly a boilerplate
#: connective ("...party hereto, the Lenders..."), not part of a name --
#: a deliberate tradeoff. It means a name that itself legitimately starts
#: with "The" (e.g. "The Bank of New York Mellon") gets truncated to "Bank
#: of New York Mellon" if the walk reaches back that far. None of the 65
#: cached filings hit this case; noted here rather than special-cased.

#: How far back from the anchor to look for the name. Generous, because
#: the backward walk itself -- not the window size -- is what stops the
#: match at the right boundary.
AGENT_WINDOW_CHARS = 200


def extract_agent(doc_text: str) -> dict | None:
    """The administrative agent's institution name, and the span it came from.

    Returns {"name": str, "offset": int, "end": int} or None. `name` is
    whitespace-NORMALISED (internal newlines/runs of spaces collapsed to one
    space); `offset`/`end` are RAW character positions in `doc_text`, and are
    a checkable, honest pair: " ".join(doc_text[offset:end].split()) == name
    always holds, even when the captured span itself contains an embedded
    newline (TextExtractor.text() deliberately preserves those, and one
    filing's cover page literally reads "BANK OF AMERICA,\nN.A." at the
    anchor). An earlier version of this function returned only `offset` sized
    to the normalised `name`'s length, which broke that invariant on exactly
    such spans -- the bug predated this file's Task 1 repair; fixing it was
    part of "make this field trustworthy," so it belongs here too.

    The regex this replaces used a LAZY quantifier over a character class
    that admits spaces and commas (`[A-Z][A-Za-z0-9&.,'\\- ]{3,60}?`),
    searching FORWARD for the shortest prefix ending in "as ... Administrative
    Agent". On "JPMORGAN CHASE BANK, N.A., in its capacity as administrative
    agent" that shortest satisfying prefix is "in its capacity" -- a
    connective, not a name -- and the same shape of bug also matched "that
    is a party hereto, and BANK OF AMERICA, N.A." and similar fragments on
    other filings. It always matched *something*, so nothing failed loudly,
    and 45 of 51 syndicated facilities carried a wrong value that looked
    plausible enough to pass a casual glance.

    This version searches BACKWARDS from the anchor instead, one
    whitespace-delimited token at a time, and can only extend the name
    through tokens that look like part of one. A connective word, a stop
    word (checked case-insensitively, since cover-page text is often
    ALL-CAPS and loses the signal a mixed-case check would rely on), or a
    paragraph break (two or more newlines -- the boundary between two
    parties listed on separate lines of a cover page) ends the walk on the
    spot. That makes the failure mode "stop one token too early", not
    "silently swallow the wrong clause".
    """
    if not doc_text:
        return None
    anchor = AGENT_ANCHOR.search(doc_text)
    if not anchor:
        return None

    window_start = max(0, anchor.start() - AGENT_WINDOW_CHARS)
    window = doc_text[window_start:anchor.start()]

    # Peel trailing connective phrases and parenthetical short-form
    # aliases from the right, in whichever order they appear, until the
    # window stops changing.
    while True:
        stripped = AGENT_CONNECTIVES.sub("", window)
        stripped = AGENT_PAREN_ALIAS.sub("", stripped)
        stripped = stripped.rstrip(" \t\n,;")
        if stripped == window:
            break
        window = stripped

    tokens = list(re.finditer(r"\S+", window))
    included: list[re.Match] = []
    i = len(tokens) - 1
    while i >= 0:
        bare = tokens[i].group().rstrip(",;")
        lowered = bare.lower()
        is_name = bool(AGENT_NAME_TOKEN.match(bare)) and lowered not in AGENT_STOP_WORDS
        # Deliberate tradeoff, not fixed here: this only checks that the
        # left neighbour LOOKS like a name token (capitalised), not that
        # it also clears AGENT_STOP_WORDS. A stop word that happens to be
        # capitalised immediately to the left of "of" could in principle
        # be pulled in as a false connector target; none of the 65 cached
        # filings hit this, so the walk is left as-is rather than special-
        # cased for a case that hasn't been observed.
        is_connector = (
            lowered in AGENT_NAME_CONNECTORS and included and i > 0
            and bool(AGENT_NAME_TOKEN.match(tokens[i - 1].group().rstrip(",;")))
        )
        if not (is_name or is_connector):
            break
        if included:
            gap = window[tokens[i].end():included[-1].start()]
            if gap.count("\n") >= 2:
                break
        included.append(tokens[i])
        i -= 1

    if not included:
        return None

    included.reverse()
    raw_start, raw_end = included[0].start(), included[-1].end()
    # No further rstrip(",;") here: the stripping loop above already leaves
    # `window` unable to end in one (its own fixed point is
    # `.rstrip(" \t\n,;")`), and `included[-1]` is always the window's
    # rightmost token, so raw_end == len(window) and window[raw_end - 1] is
    # never a comma/semicolon. That keeps `end` exactly bounding `name`
    # after whitespace normalisation, with nothing left to trim after.
    raw_name = window[raw_start:raw_end]
    name = " ".join(raw_name.split())
    # A floor against a single-character walk (e.g. a stray "A" from a
    # cross-reference), not against real short defined-term aliases --
    # one filing literally reuses "TCW" (3 chars) as the agent's name at
    # the anchor, and that is a legitimate value, not a fragment.
    if len(name) < 3:
        return None
    return {
        "name": name,
        "offset": window_start + raw_start,
        "end": window_start + raw_end,
    }


ARRANGER = re.compile(
    r"(joint\s+lead\s+arrangers?|lead\s+arrangers?|bookrunners?|"
    r"syndication\s+agent)", re.IGNORECASE)

MATURITY = re.compile(
    r"maturity\s+date[^.]{0,120}?"
    r"((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+20\d{2})", re.IGNORECASE)

EFFECTIVE = re.compile(
    r"dated\s+as\s+of\s+"
    r"((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+20\d{2})", re.IGNORECASE)

AMENDMENT_NO = re.compile(
    r"amendment\s+(?:no\.?|number)\s*(\d+)", re.IGNORECASE)

AMENDED_RESTATED = re.compile(
    r"amended\s+and\s+restated\s+credit\s+agreement", re.IGNORECASE)

# A pricing grid is a leverage-keyed margin table. Detect the *structure*, not
# a specific layout: tiers expressed as ratio thresholds near a margin figure.
LEVERAGE_TIER = re.compile(
    r"(?:greater\s+than|less\s+than|≥|>=|<=|equal\s+to)[^|\n]{0,40}?"
    r"(\d\.\d{1,2})\s*(?::\s*1(?:\.0{1,2})?)?", re.IGNORECASE)

COMMITMENT_NEAR = re.compile(
    r"(aggregate\s+principal\s+amount|aggregate\s+commitments?|"
    r"in\s+an\s+aggregate\s+amount|commitments?\s+in\s+the\s+aggregate)",
    re.IGNORECASE)


def find_amounts(text: str, window: int = 240) -> list[tuple[int, int]]:
    """Money figures appearing near commitment language, with offsets."""
    out: list[tuple[int, int]] = []
    for m in COMMITMENT_NEAR.finditer(text):
        segment = text[m.start(): m.start() + window]
        money = re.search(MONEY, segment)
        if money:
            value = int(money.group(1).replace(",", ""))
            if 1_000_000 <= value <= 100_000_000_000:
                out.append((value, m.start() + money.start()))
    return out


def extract(doc_text: str) -> dict:
    facility_types: dict[str, int] = {}
    for name, pattern in FACILITY_PATTERNS:
        m = pattern.search(doc_text)
        if m:
            facility_types[name] = m.start()

    amounts = find_amounts(doc_text)
    agent = extract_agent(doc_text)
    maturity_m = MATURITY.search(doc_text)
    effective_m = EFFECTIVE.search(doc_text)
    amend_m = AMENDMENT_NO.search(doc_text)
    restated = bool(AMENDED_RESTATED.search(doc_text))
    arranger_m = ARRANGER.search(doc_text)

    tiers = sorted({float(m.group(1)) for m in LEVERAGE_TIER.finditer(doc_text)
                    if 0.5 <= float(m.group(1)) <= 9.99})

    return {
        "facility_types": facility_types,
        "commitment_amounts": [
            {"value": v, "offset": o} for v, o in sorted(amounts, reverse=True)[:6]
        ],
        "administrative_agent": agent,
        "maturity_date": (
            {"value": maturity_m.group(1), "offset": maturity_m.start(1)}
            if maturity_m else None
        ),
        "effective_date": (
            {"value": effective_m.group(1), "offset": effective_m.start(1)}
            if effective_m else None
        ),
        "amendment_number": (
            {"value": int(amend_m.group(1)), "offset": amend_m.start(1)}
            if amend_m else None
        ),
        "is_amended_and_restated": restated,
        "syndicated": bool(arranger_m),
        "pricing_grid_tiers": tiers[:8],
    }


def main() -> int:
    index = json.loads((SCREEN / "ex10_index.json").read_text())["documents"]
    print(f"Extracting facility terms from {len(index)} cached EX-10 documents\n")

    results = []
    for doc in index:
        path = REPO_ROOT / doc["path"]
        if not path.exists():
            continue
        raw = path.read_text(errors="ignore")
        parser = TextExtractor()
        try:
            parser.feed(raw)
            parser.close()
        except Exception:  # noqa: BLE001
            pass
        text = parser.text()
        found = extract(text)
        found.update({
            "cik": doc["cik"], "lei": doc["lei"], "sec_name": doc["sec_name"],
            "accession": doc["accession"], "document": doc["document"],
            "filed_date": doc["filed_date"], "form": doc["form"],
            "text_chars": len(text),
        })
        results.append(found)

        types = ",".join(found["facility_types"]) or "-"
        print(f"  {doc['sec_name'][:26]:28s} {types:32s} "
              f"amt={len(found['commitment_amounts'])} "
              f"tiers={len(found['pricing_grid_tiers'])} "
              f"{'AR' if found['is_amended_and_restated'] else '  '}"
              f"{' SYN' if found['syndicated'] else ''}")

    # --- yield report: what deterministic extraction actually covered -----
    n = len(results)
    def pct(k: int) -> str:
        return f"{k:>3}/{n}  {100 * k // max(n, 1):>3}%"

    with_type = sum(1 for r in results if r["facility_types"])
    with_amt = sum(1 for r in results if r["commitment_amounts"])
    with_agent = sum(1 for r in results if r["administrative_agent"])
    with_mat = sum(1 for r in results if r["maturity_date"])
    with_eff = sum(1 for r in results if r["effective_date"])
    with_tiers3 = sum(1 for r in results if len(r["pricing_grid_tiers"]) >= 3)
    amended = sum(1 for r in results
                  if r["is_amended_and_restated"] or r["amendment_number"])
    syndicated = sum(1 for r in results if r["syndicated"])

    print(f"\n  DETERMINISTIC YIELD")
    print(f"    facility type identified   {pct(with_type)}")
    print(f"    commitment amount          {pct(with_amt)}")
    print(f"    administrative agent       {pct(with_agent)}")
    print(f"    maturity date              {pct(with_mat)}")
    print(f"    effective date             {pct(with_eff)}")
    print(f"    pricing grid >= 3 tiers    {pct(with_tiers3)}")
    print(f"    amendment detected         {pct(amended)}")
    print(f"    syndicated structure       {pct(syndicated)}")

    # Distinct facility rows this yields, since one agreement often defines
    # a revolver AND one or more term tranches.
    facility_rows = sum(len(r["facility_types"]) or 1 for r in results)
    print(f"\n  {facility_rows} distinct facilities implied "
          f"(§F asks ~40)")

    type_totals: dict[str, int] = {}
    for r in results:
        for t in r["facility_types"]:
            type_totals[t] = type_totals.get(t, 0) + 1
    print(f"  types: {type_totals}")

    (SCREEN / "facilities_extracted.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 4 — deterministic facility extraction",
                "method": "structure + conventional-language regex over EX-10 text",
                "note": "Offsets are recorded per value so Wave 6 can anchor a "
                        "passage and §8.4 verification has something to check. "
                        "Fields left null are the gap an LLM pass must cover.",
                "document_count": n,
                "facility_rows_implied": facility_rows,
                "documents": results,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: sources/screening/facilities_extracted.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
