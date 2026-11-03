#!/usr/bin/env python3
"""Wave 15 — extract the covenant DEFINITION chain from filed EX-10 text.

`covenant-cross-reference` summarises itself as "the covenant sits in one
section and its defined terms in another." Until Wave 15 the estate could not
express that at all: `ex:definedBy`, `ex:measuredBy` and `ex:crossReferences`
had zero assertions, and `ex:CovenantDefinition` / `ex:DefinedTerm` /
`ex:MeasurementPeriod` had zero instances. Three §F bullets were unsatisfiable
and unregistered; a fourth was satisfied by the wrong quantity.

Wave 5's `extract_covenants.py` anticipated this -- its docstring calls the
definition chain "the hard part" -- and got as far as citing section NUMBERS
("430", "4001"), 196 of 295 of them unverifiable, plus six defined terms across
sixty documents. Six is not a defined-terms article. This pass reads the
articles themselves.

## Provenance

`public`, per §C: every definition here is a real span of a real filed EX-10,
recorded with its document id and character offsets. Nothing is invented. The
only engineered element is the unresolvable-definition case, which §F names as
engineered and which `load_covenant_definitions_wave15.py` adds separately and
labels.

## Three declaration conventions, because one issuer is not the format

Measured across the 22 EX-10 documents that carry a COVSRC covenant anchor:

    “Term”: body            Avis Budget 449, Thermon 420, Bausch 468  — colon
    “Term” means body       BGC 195, TransDigm 322, RB Global 376     — means
    “Term” shall mean body  Vertiv 311 in one filing, 6 in another    — shall mean

A parser written against any single one of these returns near-zero for whole
filers -- Vertiv files both conventions in two different agreements. All three
are matched, and `convention` is recorded per declaration so a future skew is
visible rather than silent.

## What "depth 3" means here

    covenant  --definedBy-->  CovenantDefinition  --crossReferences-->  DefinedTerm

A leverage covenant cites "Consolidated Leverage Ratio"; that definition's body
cites "Consolidated EBITDA" and "Consolidated Total Debt", each itself a
declared term in the same article. §F wants >= 5 covenants whose chain reaches
that third hop.

Components are found by matching the document's OWN declared terms inside a
definition body, longest name first so "Consolidated Total Debt" is not
shadowed by "Total Debt". A term is a component only if the agreement declares
it -- a capitalised phrase that is never defined is not a defined term, and
treating it as one would manufacture chain depth that the document does not
have.

Output: sources/screening/covenant_definitions.json

Run: uv run generators/extract_covenant_definitions.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter

from ccf.config import REPO_ROOT, mongo_db

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "covenant_definitions.json"

#: Declaration conventions. Curly quotes only: a straight-quote sweep over the
#: same corpus returns 1 hit in 6,233, so admitting it buys nothing and would
#: match ordinary quoted prose.
CONVENTIONS = [
    ("colon", re.compile(r"“([^”]{3,80})”\s*:")),
    ("means", re.compile(r"“([^”]{3,80})”\s+means\b")),
    ("shall_mean", re.compile(r"“([^”]{3,80})”\s+shall\s+mean\b")),
]

#: A definition body runs to the next declaration. The cap stops a trailing
#: declaration from swallowing the rest of a 600 KB agreement, which would
#: hand it every remaining term in the document as a "component".
MAX_BODY = 3000

#: covenant_type -> the defined term that states how the ratio is computed.
#: Anchored with \b and ordered most-specific-first at match time, so
#: "Secured Leverage Ratio" is not claimed by the plain leverage pattern.
RATIO_TERMS = {
    "secured_leverage": re.compile(
        r"\b(?:consolidated\s+)?(?:senior\s+)?secured\s+(?:net\s+)?leverage\s+ratio\b", re.I),
    "leverage": re.compile(
        r"\b(?:consolidated\s+)?(?:total\s+|net\s+)?leverage\s+ratio\b", re.I),
    "interest_coverage": re.compile(
        r"\b(?:consolidated\s+)?interest\s+(?:expense\s+)?coverage\s+ratio\b", re.I),
    "fixed_charge_coverage": re.compile(
        r"\b(?:consolidated\s+)?fixed\s+charge\s+coverage\s+ratio\b", re.I),
    "minimum_liquidity": re.compile(r"\b(?:minimum\s+)?liquidity\b", re.I),
    # Added after measurement, not by guesswork. The five types above are the
    # ones Wave 5's regex could already find, and searching only for those
    # returned ZERO cross-document references corpus-wide -- which would have
    # sent §F's cross-document bullet to the engineered pile. It is not
    # engineered: BGC Group's agreement carries a real net-capital covenant
    # ("Net Excess Capital ... to be less than $300,000,000", section 7.11(d)),
    # and its defined term incorporates a convention stated elsewhere -- "as
    # shown on the Borrower's SEC Forms 10-Q and 10-K". Wave 5 simply had no
    # pattern for the category. Net capital is a standard broker-dealer
    # covenant under the SEC net-capital rule, not a BGC-specific coinage.
    "net_capital": re.compile(
        r"\b(?:net\s+excess\s+capital|excess\s+net\s+capital|net\s+capital)\b", re.I),
}

#: A financial-covenant clause constraining a defined term to a threshold.
#: Used only for covenant types that have a definition but no COVSRC anchor
#: from Wave 6, so the clause is what evidences the covenant's existence.
CLAUSE = (
    r"[^.]{{0,240}}?(?P<dir>to\s+be\s+less\s+than|not\s+be\s+less\s+than|"
    r"at\s+least|to\s+exceed|not\s+to\s+exceed|greater\s+than)"
    r"[^.$]{{0,40}}\$\s?(?P<amt>[\d,]{{7,20}})"
)


#: Which way breach lies, from the covenant's own semantics. A capital or
#: liquidity floor is breached below it; a leverage ceiling is breached above.
#: This is the SOLE authority for direction.
EXPECTED_DIRECTION = {
    "net_capital": "min",
    "minimum_liquidity": "min",
    "interest_coverage": "min",
    "fixed_charge_coverage": "min",
    "leverage": "max",
    "secured_leverage": "max",
}


def covenant_clause(text: str, term: str, covenant_type: str) -> dict | None:
    """The clause constraining `term` to a dollar threshold, if any.

    Deliberately narrow: a dollar amount, not a ratio. Ratio covenants already
    come from Wave 6's COVSRC anchors and must not be re-derived here -- two
    writers for one covenant is exactly the duplication the store rules forbid.

    ## Direction comes from the covenant type, and the comparator is NOT a check

    The first cut read direction off the comparator and got Viskase backwards:
    "Liquidity shall be greater than $10,000,000" is a FLOOR and was recorded
    as a ceiling. The obvious repair -- invert when the clause is negated --
    was then tried and ALSO failed, in both directions at once:

        BGC      "...to be less than $300,000,000"      negation missed
        Viskase  "Liquidity shall be greater than..."   negation falsely found

    because the negation that governs a covenant list sits in the section
    lead-in ("shall not permit:") an arbitrary distance back, while a fixed
    look-behind window catches whatever neighbouring clause happens to be in
    range. Both readings were wrong, and a comparator check that is wrong on
    100% of the corpus is not a check -- it is a coin flip that would have
    blocked the one real covenant here.

    So direction is taken from the covenant type, which is semantically fixed:
    a net-capital covenant is a floor whatever phrasing the drafter chose. The
    excerpt is recorded verbatim so the reading stays auditable by a human, and
    the loader restricts covenant CREATION to `net_capital` -- the one category
    introduced deliberately -- so a mis-parse cannot manufacture covenants in
    categories Wave 6 already owns.
    """
    pattern = re.compile(re.escape(term) + CLAUSE.format(), re.I)
    m = pattern.search(text)
    if not m:
        return None
    direction = EXPECTED_DIRECTION.get(covenant_type)
    if direction is None:
        return None
    return {
        "threshold": float(m.group("amt").replace(",", "")),
        "unit": "usd",
        "direction": direction,
        "direction_basis": "covenant type semantics; see docstring",
        "clause_offset": m.start(),
        "clause_excerpt": re.sub(r"\s+", " ", m.group(0))[:300],
    }


#: The measurement window a ratio is computed over.
PERIOD_TERM = re.compile(
    r"\b(?:measurement|test|reference)\s+period\b", re.I)

#: A definition that incorporates a convention stated in the periodic report
#: rather than in the agreement -- §F's cross-document reference.
#:
#: `Annual Report` alone is NOT enough and was rejected after measurement: it
#: matches "annual reporting periods", which is how Pebblebrook's "FAS 141R
#: Changes" definition produced a false positive on the first pass. The form
#: designation is what makes the citation a cross-document one.
CROSS_DOC = re.compile(
    r"\bForms?\s+10-[KQ]\b|\bForm\s+10-Q\s+and\s+10-K\b|"
    r"\bAnnual\s+Report\s+on\s+Form\s+10-K\b", re.I)


def normalise(term: str) -> str:
    """Collapse the newlines the filer's HTML-to-text pass leaves mid-term.

    "Consolidated Coverage\\nRatio" and "Consolidated Coverage Ratio" are one
    term; without this they are two, and the component match below would miss
    every wrapped occurrence.
    """
    return re.sub(r"\s+", " ", term).strip()


def declarations(text: str) -> list[dict]:
    """Every defined-term declaration in one document, bodies delimited.

    A term declared more than once keeps its FIRST declaration: agreements
    restate terms in amendments and schedules, and the defined-terms article
    comes first.
    """
    found: list[dict] = []
    for convention, pattern in CONVENTIONS:
        for m in pattern.finditer(text):
            found.append({
                "term": normalise(m.group(1)),
                "convention": convention,
                "decl_offset": m.start(),
                "body_start": m.end(),
            })
    found.sort(key=lambda d: d["decl_offset"])

    starts = [d["decl_offset"] for d in found]
    for i, d in enumerate(found):
        nxt = starts[i + 1] if i + 1 < len(starts) else len(text)
        d["body_end"] = min(nxt, d["body_start"] + MAX_BODY)

    seen: set[str] = set()
    out: list[dict] = []
    for d in found:
        if d["term"] in seen or not d["term"]:
            continue
        seen.add(d["term"])
        out.append(d)
    return out


def component_finder(terms: list[str]) -> re.Pattern | None:
    """One alternation over every declared term, longest first.

    Longest-first is load-bearing: Python's alternation is first-match, so with
    "Total Debt" ahead of "Consolidated Total Debt" every occurrence of the
    longer term would be recorded as the shorter one, quietly rewiring the
    dependency graph to the wrong nodes.
    """
    usable = [t for t in terms if len(t) >= 6]
    if not usable:
        return None
    ordered = sorted(usable, key=len, reverse=True)
    return re.compile("|".join(re.escape(t) for t in ordered))


def main() -> int:
    print("Wave 15 — covenant definition chain from filed EX-10 text\n")
    db = mongo_db()
    coll = db["document"]

    docs = list(coll.find({"text": {"$regex": "CREDIT AGREEMENT"}},
                          {"document_id": 1, "sec_name": 1, "lei": 1,
                           "cik": 1, "accession": 1, "text": 1,
                           "filed_date": 1}))
    print(f"  {len(docs)} candidate credit-agreement documents\n")

    out_docs: list[dict] = []
    conv_tally: Counter[str] = Counter()
    total_defs = total_terms = total_periods = total_cross = 0

    for doc in docs:
        text = doc["text"]
        decls = declarations(text)
        if len(decls) < 20:
            # Not a defined-terms article -- a short amendment or a consent.
            # Recorded so the skip is visible rather than a silent filter.
            out_docs.append({
                "document_id": doc["document_id"],
                "sec_name": doc.get("sec_name"),
                "lei": doc.get("lei"),
                "skipped": f"only {len(decls)} declarations; no definitions article",
                "definitions": [], "measurement_periods": [],
            })
            continue

        by_term = {d["term"]: d for d in decls}
        finder = component_finder(list(by_term))
        for d in decls:
            conv_tally[d["convention"]] += 1

        # --- the ratio definitions this document states -------------------
        definitions: list[dict] = []
        for cov_type, pattern in RATIO_TERMS.items():
            hits = [t for t in by_term if pattern.search(t)]
            if not hits:
                continue
            # Shortest matching term is the ratio itself; longer ones are
            # usually derived ("Consolidated Leverage Ratio Step-Down").
            term = min(hits, key=len)
            d = by_term[term]
            body = text[d["body_start"]:d["body_end"]]

            components: list[dict] = []
            if finder is not None:
                for m in finder.finditer(body):
                    name = normalise(m.group(0))
                    if name == term or name not in by_term:
                        continue
                    if any(c["term"] == name for c in components):
                        continue
                    components.append({
                        "term": name,
                        "declared_at": by_term[name]["decl_offset"],
                        "cited_at": d["body_start"] + m.start(),
                    })

            cross = CROSS_DOC.search(body)
            definitions.append({
                "covenant_type": cov_type,
                "covenant_clause": covenant_clause(text, term, cov_type),
                "term": term,
                "convention": d["convention"],
                "decl_offset": d["decl_offset"],
                "body_start": d["body_start"],
                "body_end": d["body_end"],
                "body_excerpt": re.sub(r"\s+", " ", body[:400]),
                "components": components,
                "cross_document_citation": (
                    re.sub(r"\s+", " ", body[max(0, cross.start() - 160):
                                             cross.end() + 60])
                    if cross else None
                ),
            })
            total_terms += len(components)
            if cross:
                total_cross += 1

        # --- measurement periods ------------------------------------------
        periods = []
        for term, d in by_term.items():
            if PERIOD_TERM.search(term):
                periods.append({
                    "term": term,
                    "decl_offset": d["decl_offset"],
                    "body_excerpt": re.sub(
                        r"\s+", " ", text[d["body_start"]:d["body_end"]][:300]),
                })

        total_defs += len(definitions)
        total_periods += len(periods)
        out_docs.append({
            "document_id": doc["document_id"],
            "sec_name": doc.get("sec_name"),
            "lei": doc.get("lei"),
            "cik": doc.get("cik"),
            "accession": doc.get("accession"),
            "filed_date": str(doc.get("filed_date")),
            "declaration_count": len(decls),
            "definitions": definitions,
            "measurement_periods": periods,
        })

        if definitions:
            chain = sum(1 for x in definitions if x["components"])
            print(f"  {str(doc.get('sec_name'))[:30]:30s} "
                  f"{len(decls):>4} decls · {len(definitions)} ratio defs · "
                  f"{chain} with components · {len(periods)} periods")

    payload = {
        "generated_for": "covenant-cross-reference, covenant-in-force-as-of",
        "wave": 15,
        "provenance": "public — real spans of filed EX-10 agreements",
        "method": (
            "three declaration conventions (colon / means / shall mean); "
            "components are the document's OWN declared terms found inside a "
            "definition body, longest name first"
        ),
        "conventions_seen": dict(conv_tally),
        "totals": {
            "documents": len(out_docs),
            "ratio_definitions": total_defs,
            "component_citations": total_terms,
            "measurement_periods": total_periods,
            "cross_document_definitions": total_cross,
        },
        "documents": out_docs,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"\n  conventions: {dict(conv_tally)}")
    print(f"  {total_defs} ratio definitions · {total_terms} component "
          f"citations · {total_periods} measurement periods")
    print(f"  {total_cross} definitions citing a 10-K/10-Q convention")
    print(f"  written: {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
