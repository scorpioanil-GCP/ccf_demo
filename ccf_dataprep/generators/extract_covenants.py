#!/usr/bin/env python3
"""Wave 5 — extract covenant structure from cached EX-10 agreements.

Financial covenants are the most conventionally-worded clauses in a credit
agreement, which makes them tractable deterministically:

    "the Consolidated Leverage Ratio ... shall not ... exceed 4.00 to 1.00"
    "the Interest Coverage Ratio ... shall not be less than 3.00 to 1.00"

The **definition chain** is the hard part and where an LLM would earn its cost:
a covenant references a defined term, whose definition sits in a different
article, and whose own components reference further terms. This pass captures
the covenant, its threshold, its test frequency, and the *reference* to its
defining section — then verifies deterministically that the cited section
actually exists in the document. That is §8.4 Algorithmic Verification: an
extracted cross-reference is a candidate until a deterministic check confirms
the target.

Unresolvable references are emitted as Context Debt rather than dropped, which
`covenant-cross-reference` §F explicitly wants (>= 1 covenant with an
unresolvable definition).

Output: sources/screening/covenants_extracted.json

Run: uv run generators/extract_covenants.py
"""

from __future__ import annotations

import json
import re
import sys

from ccf.config import REPO_ROOT
from generators.extract_facilities import TextExtractor

SCREEN = REPO_ROOT / "sources" / "screening"

RATIO = r"(\d{1,2}(?:\.\d{1,2})?)\s*(?::|\s+to\s+)\s*1(?:\.0{1,2})?"

#: (covenant_type, direction, pattern). Direction is which way breach lies.
COVENANT_PATTERNS = [
    ("leverage", "max", re.compile(
        r"(consolidated\s+)?(?:total\s+|net\s+|senior\s+secured\s+)?leverage\s+ratio"
        r"[^.;]{0,240}?(?:to\s+exceed|not\s+(?:to\s+)?exceed|"
        r"no\s+greater\s+than|less\s+than\s+or\s+equal\s+to|"
        r"shall\s+not\s+be\s+greater\s+than|to\s+be\s+greater\s+than)"
        r"[^.;]{0,60}?" + RATIO, re.IGNORECASE)),
    ("interest_coverage", "min", re.compile(
        r"(?:consolidated\s+)?interest\s+(?:expense\s+)?coverage\s+ratio"
        r"[^.;]{0,240}?(?:to\s+be\s+less\s+than|not\s+be\s+less\s+than|"
        r"at\s+least|greater\s+than\s+or\s+equal\s+to|no\s+less\s+than)"
        r"[^.;]{0,60}?" + RATIO, re.IGNORECASE)),
    ("fixed_charge_coverage", "min", re.compile(
        r"(?:consolidated\s+)?fixed\s+charge\s+coverage\s+ratio"
        r"[^.;]{0,240}?(?:to\s+be\s+less\s+than|not\s+be\s+less\s+than|"
        r"at\s+least|greater\s+than\s+or\s+equal\s+to|no\s+less\s+than)"
        r"[^.;]{0,60}?" + RATIO, re.IGNORECASE)),
    ("secured_leverage", "max", re.compile(
        r"secured\s+(?:net\s+)?leverage\s+ratio"
        r"[^.;]{0,200}?(?:not\s+(?:to\s+)?exceed|no\s+greater\s+than)"
        r"[^.;]{0,60}?" + RATIO, re.IGNORECASE)),
    ("debt_service_coverage", "min", re.compile(
        r"debt\s+service\s+coverage\s+ratio"
        r"[^.;]{0,240}?(?:to\s+be\s+less\s+than|not\s+be\s+less\s+than|"
        r"at\s+least)[^.;]{0,60}?" + RATIO, re.IGNORECASE)),
]

#: Minimum liquidity / minimum EBITDA are absolute, not ratios.
LIQUIDITY = re.compile(
    r"(?:minimum\s+)?liquidity[^.;]{0,150}?(?:not\s+be\s+less\s+than|"
    r"at\s+least)[^.;]{0,60}?\$\s?([\d,]{7,})", re.IGNORECASE)

TEST_FREQUENCY = re.compile(
    r"(?:as\s+of\s+the\s+last\s+day\s+of\s+each\s+(fiscal\s+quarter|"
    r"fiscal\s+year|fiscal\s+month)|tested\s+(quarterly|annually|monthly))",
    re.IGNORECASE)

#: The cross-reference a covenant makes to its defining section.
DEFINED_IN = re.compile(
    r"as\s+defined\s+in\s+(?:Section|Article)\s+([0-9]+(?:\.[0-9]+)*)",
    re.IGNORECASE)

#: Section headings actually present, so a reference can be verified.
SECTION_HEADING = re.compile(
    r"(?:^|\n)\s*(?:Section|SECTION|ARTICLE|Article)\s+"
    r"([0-9]+(?:\.[0-9]+)*)", re.MULTILINE)

DEFINED_TERM = re.compile(
    r'[""„]([A-Z][A-Za-z ]{4,48})[""”]\s+(?:means|shall\s+mean)', re.IGNORECASE)


def extract(text: str) -> dict:
    covenants: list[dict] = []

    for ctype, direction, pattern in COVENANT_PATTERNS:
        for m in pattern.finditer(text):
            try:
                threshold = float(m.group(m.lastindex))
            except (TypeError, ValueError):
                continue
            if not (0.2 <= threshold <= 20.0):
                continue
            window = text[max(0, m.start() - 300): m.end() + 300]
            freq = TEST_FREQUENCY.search(window)
            covenants.append({
                "covenant_type": ctype,
                "direction": direction,
                "threshold": threshold,
                "unit": "ratio",
                "offset": m.start(),
                "test_frequency": (freq.group(1) or freq.group(2)).lower()
                                  if freq else "fiscal quarter",
                "excerpt_offset": m.start(),
                "excerpt_length": m.end() - m.start(),
            })
            break        # one instance per type; amendments restate them

    for m in LIQUIDITY.finditer(text):
        value = int(m.group(1).replace(",", ""))
        if 1_000_000 <= value <= 10_000_000_000:
            covenants.append({
                "covenant_type": "minimum_liquidity",
                "direction": "min",
                "threshold": value,
                "unit": "USD",
                "offset": m.start(),
                "test_frequency": "fiscal quarter",
                "excerpt_offset": m.start(),
                "excerpt_length": m.end() - m.start(),
            })
            break

    # --- definition chain, with §8.4 verification -------------------------
    present_sections = {m.group(1) for m in SECTION_HEADING.finditer(text)}
    references: list[dict] = []
    for m in DEFINED_IN.finditer(text):
        section = m.group(1)
        references.append({
            "cited_section": section,
            "offset": m.start(1),
            # A cited section is a CANDIDATE until deterministically confirmed.
            "verified": section in present_sections,
        })

    defined_terms = [
        {"term": " ".join(m.group(1).split()), "offset": m.start(1)}
        for m in DEFINED_TERM.finditer(text)
    ][:40]

    return {
        "covenants": covenants,
        "definition_references": references[:40],
        "references_verified": sum(1 for r in references if r["verified"]),
        "references_unverified": sum(1 for r in references if not r["verified"]),
        "defined_terms_found": len(defined_terms),
        "defined_terms": defined_terms[:15],
        "sections_present": len(present_sections),
    }


def main() -> int:
    index = json.loads((SCREEN / "ex10_index.json").read_text())["documents"]
    print(f"Extracting covenant structure from {len(index)} documents\n")

    results = []
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
        found = extract(text)
        found.update({
            "cik": doc["cik"], "lei": doc["lei"], "sec_name": doc["sec_name"],
            "accession": doc["accession"], "document": doc["document"],
            "filed_date": doc["filed_date"],
        })
        results.append(found)
        if found["covenants"]:
            types = ",".join(c["covenant_type"] for c in found["covenants"])
            print(f"  {doc['sec_name'][:24]:26s} {len(found['covenants'])} cov  "
                  f"refs {found['references_verified']}v/"
                  f"{found['references_unverified']}u  {types[:52]}")

    with_cov = [r for r in results if r["covenants"]]
    four_plus = [r for r in results if len(r["covenants"]) >= 4]
    unverified = [r for r in results if r["references_unverified"] > 0]
    total_cov = sum(len(r["covenants"]) for r in results)

    print(f"\n  {total_cov} covenants across {len(with_cov)} documents")
    print(f"  {len(four_plus)} documents with >= 4 covenant types  "
          f"(§F floor: 4 per facility)")
    print(f"  {len(unverified)} documents carry an UNVERIFIED section reference "
          f"-> Context Debt (§F wants >= 1)")

    type_counts: dict[str, int] = {}
    for r in results:
        for c in r["covenants"]:
            type_counts[c["covenant_type"]] = type_counts.get(c["covenant_type"], 0) + 1
    print(f"  types: {type_counts}")

    (SCREEN / "covenants_extracted.json").write_text(
        json.dumps(
            {
                "generated_for": "Wave 5 — covenant structure from EX-10",
                "method": "conventional-language regex; section references "
                          "verified against headings actually present (§8.4)",
                "note": "An extracted cross-reference is a CANDIDATE until a "
                        "deterministic check confirms the cited section exists. "
                        "Unverified references become Context Debt, not silent "
                        "drops.",
                "total_covenants": total_cov,
                "documents": results,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: sources/screening/covenants_extracted.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
