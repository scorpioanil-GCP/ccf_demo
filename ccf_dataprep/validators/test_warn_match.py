#!/usr/bin/env python3
"""Pure tests for WARN parsing and the lossy obligor name join.

The join is SUPPOSED to be imperfect (CLAUDE.md rule 5). These tests pin both
directions: the true positives must resolve, and the known false positives
must NOT silently resolve. A match table containing only true positives
passes a row count and destroys the demonstration.

    uv run validators/test_warn_match.py
"""

from __future__ import annotations

import sys

from generators.warn_match import (AMBIGUOUS_AT, RESOLVE_AT, classify,
                                   normalise, score)
from generators.warn_sources import (WarnNotice, parse_ca_pdf_text,
                                     parse_ca_xlsx, parse_tx_socrata)

# Measured true positives — design §1.3. These MUST resolve.
TRUE_PAIRS = [
    # Real name pairs from the real Texas source — kept as scorer fixtures
    # (the scorer must still resolve them as STRINGS), but every Avis
    # notice in Texas dates to 2020 (COVID-era) and none survives the
    # 24-month window, and the Charter/Austin notice is likewise
    # out-of-window. Neither is present in the loaded artifact — see the
    # real in-window resolved set in Step 5 below. Do not read either as
    # evidence Avis or Charter/Austin is in the dataset.
    ("CHARTER COMMUNICATIONS, INC. /MO/", "Charter Communications (Austin)"),
    ("CHARTER COMMUNICATIONS, INC. /MO/", "Charter Communications"),
    ("AVIS BUDGET GROUP, INC.", "Avis Budget Car Rental"),
    ("Quanex Building Products CORP", "Quanex Homeshield LLC"),
    # Real, in-window true positive (measured directly in the loaded
    # artifact — CA, 2025-08-13). Added; was previously untested.
    ("Bausch Health Companies Inc.", "Bausch Health US, LLC"),
]

# Measured false positives — design §1.3. These MUST NOT resolve.
# The last two matched STREET ADDRESSES, not company names.
FALSE_PAIRS = [
    ("Caesars Entertainment, Inc.", "CEC Entertainment, Inc."),
    ("REGIS CORP", "St. Regis Houston"),
    ("BOSTON OMAHA Corp", "Boston Scientific Corporation"),
    ("Container Store Group, Inc.", "Dart Container Corporation"),
    ("GRANITE CONSTRUCTION INC", "Granite Peak Fabrication"),
    ("SMITH & WESSON BRANDS, INC.", "Hill & Smith, Inc."),
    ("GRANITE CONSTRUCTION INC", "182 Granite Street Corona CA 92879"),
    ("MURPHY OIL CORP", "1001 Murphy Ranch Road Milpitas CA 95035"),
    # The strongest false positive in the loaded data (measured): "Pregis"
    # is a packaging company, "Regis Corp" runs hair salons. A naive
    # SequenceMatcher ratio scores this pair 0.909 — HIGHER than the real
    # Bausch Health true positive (0.769). If the scorer resolves this, it
    # is wrong; that is the entire point of the token-containment signal.
    ("REGIS CORP", "Pregis"),
    # Generic-leading-token false positives, found 2026-08-21 by probing the
    # Virginia WARN source (Wave 11c). "American Healthcare REIT" scored
    # 0.907 against "American Woodmark Corporation" — a cabinet manufacturer
    # — i.e. RESOLVED, on nothing but a shared first word. The leading-brand
    # rule's own length guard (MIN_BRAND_LEN = 6) does not catch this:
    # "american" is 8 letters. Length is not distinctiveness. Every pair
    # below shares a first token that is an ordinary English adjective or a
    # geography, which thousands of unrelated US companies also lead with.
    ("American Healthcare REIT, Inc.", "American Woodmark Corporation"),
    ("American Healthcare REIT, Inc.", "American Airlines Group"),
    ("National Fuel Gas Company", "National Vision Holdings"),
    ("United Natural Foods, Inc.", "United Rentals North America"),
    ("General Dynamics Corporation", "General Mills Sales"),
    ("Standard Motor Products", "Standard Register"),
]

# A real row from data.texas.gov resource 8w53-c4f6.
TX_ROW = {
    "notice_date": "2022-01-06T00:00:00.000",
    "job_site_name": "Stearns Lending, LLC - Corporate",
    "county_name": "Denton",
    "total_layoff_number": "348",
    "layoff_date": "2022-03-13T00:00:00.000",
    "city_name": "Lewisville",
}

# A real row from CA EDD warn_report1.xlsx, 'Detailed WARN Report' sheet.
CA_XLSX_HEADER = ["County/Parish", "Notice\nDate", "Processed\nDate",
                  "Effective \nDate", "Company", "Layoff/\nClosure",
                  "No. Of\nEmployees", "Address", "Related Industry"]
CA_XLSX_ROW = ["San Mateo County", "2026-06-26 00:00:00", "2026-07-01 00:00:00",
               "2026-07-29 00:00:00", "Genentech, Inc.", "Layoff Permanent",
               "103", "1 DNA Way  South San Francisco", "Biotech"]


def check_tx() -> list[tuple[str, bool]]:
    got = parse_tx_socrata([TX_ROW])
    n = got[0] if got else None
    return [
        ("one TX row yields one notice", len(got) == 1),
        ("TX state is stamped", n is not None and n.state == "TX"),
        ("TX employer comes from job_site_name",
         n is not None and n.employer == "Stearns Lending, LLC - Corporate"),
        ("TX notice_date is truncated to an ISO date",
         n is not None and n.notice_date == "2022-01-06"),
        ("TX employee count parses as int",
         n is not None and n.employees == 348),
        ("TX city is carried", n is not None and n.city == "Lewisville"),
    ]


def check_ca_xlsx() -> list[tuple[str, bool]]:
    got = parse_ca_xlsx([CA_XLSX_HEADER, CA_XLSX_ROW])
    n = got[0] if got else None
    return [
        ("one CA row yields one notice", len(got) == 1),
        ("CA state is stamped", n is not None and n.state == "CA"),
        ("CA employer comes from the Company column",
         n is not None and n.employer == "Genentech, Inc."),
        ("CA notice_date is an ISO date",
         n is not None and n.notice_date == "2026-06-26"),
        ("CA employee count parses", n is not None and n.employees == 103),
        # The trap: the header carries embedded newlines ("Notice\nDate").
        # Matching the header on its literal text fails; it must be normalised.
        ("the newline-bearing header is located by normalised name",
         n is not None and n.effective_date == "2026-07-29"),
    ]


def check_ca_pdf() -> list[tuple[str, bool]]:
    # Real layout from `pdftotext -layout` over the FY2024-25 report.
    text = ("Notice        Received      Effective\n"
            "Date          Date          Date\n"
            "07/01/2024    07/01/2024    06/30/2024    Lockheed Martin"
            "    Los Angeles County    57 Layoff Permanent"
            "    1011 Lockheed Way Palmdale CA 93599\n")
    got = parse_ca_pdf_text(text)
    n = got[0] if got else None
    return [
        ("a PDF data line yields one notice", len(got) == 1),
        ("PDF employer parses", n is not None and n.employer == "Lockheed Martin"),
        # The trap: the PDF renders MM/DD/YYYY while the XLSX renders ISO, and
        # both land in one table. Wave 11a's `test_curves.py` pinned exactly
        # this shape for Treasury vs FRED. Parse, do not pattern-match.
        ("PDF MM/DD/YYYY is converted to ISO",
         n is not None and n.notice_date == "2024-07-01"),
        ("PDF month and day are NOT transposed",
         parse_ca_pdf_text(
             "03/11/2025    03/11/2025    05/01/2025    Acme Co"
             "    Kern County    10 Layoff Permanent    1 Main St\n"
         )[0].notice_date == "2025-03-11"),
        ("a header line yields nothing",
         parse_ca_pdf_text("Notice        Received      Effective\n") == []),
    ]


def check_normalise() -> list[tuple[str, bool]]:
    return [
        ("state suffix is stripped",
         normalise("CHARTER COMMUNICATIONS, INC. /MO/") == "charter communications"),
        ("corporate form words are dropped",
         normalise("Quanex Building Products CORP") == "quanex building products"),
        ("case is folded", normalise("AVIS BUDGET GROUP, INC.") == "avis budget"),
        ("punctuation is dropped",
         "&" not in normalise("SMITH & WESSON BRANDS, INC.")),
    ]


def check_true_positives() -> list[tuple[str, bool]]:
    out = []
    for anchor, employer in TRUE_PAIRS:
        s = score(anchor, employer)
        out.append((f"RESOLVES: {anchor[:28]} -> {employer[:30]} ({s:.2f})",
                    classify(s) == "resolved"))
    return out


def check_false_positives() -> list[tuple[str, bool]]:
    out = []
    for anchor, employer in FALSE_PAIRS:
        s = score(anchor, employer)
        out.append((f"does NOT resolve: {anchor[:26]} -> {employer[:28]} ({s:.2f})",
                    classify(s) != "resolved"))
    return out


def check_ambiguity_survives() -> list[tuple[str, bool]]:
    # CLAUDE.md rule 5 and §F both want the ambiguity VISIBLE, not merely
    # rejected. At least one measured false pair must land in "ambiguous" so
    # the unresolved case is recorded rather than silently dropped.
    verdicts = [classify(score(a, e)) for a, e in FALSE_PAIRS]
    return [
        ("thresholds are ordered", AMBIGUOUS_AT < RESOLVE_AT),
        (">= 1 measured false pair is AMBIGUOUS, not silently rejected",
         verdicts.count("ambiguous") >= 1),
        ("no measured false pair resolves", verdicts.count("resolved") == 0),
    ]


def main() -> int:
    results = (check_tx() + check_ca_xlsx() + check_ca_pdf()
               + check_normalise() + check_true_positives()
               + check_false_positives() + check_ambiguity_survives())
    failed = [(n, ok) for n, ok in results if not ok]
    for name, ok in results:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {name}")
    print(f"\n  {len(results) - len(failed)}/{len(results)} cases behave as specified\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
