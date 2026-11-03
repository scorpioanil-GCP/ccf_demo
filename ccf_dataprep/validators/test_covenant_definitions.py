"""Tests for the covenant definition-chain extraction.

Each test feeds an input that made the first cut WRONG. The direction tests in
particular exist because two successive comparator-reading implementations were
wrong on 100% of the corpus, in opposite directions, and nothing caught it
until the loaded value was read back and compared with the covenant's meaning.
"""

from __future__ import annotations

import pytest

from generators.extract_covenant_definitions import (
    CROSS_DOC,
    EXPECTED_DIRECTION,
    component_finder,
    covenant_clause,
    declarations,
    normalise,
)


# --------------------------------------------------------------------------
# direction — the bug
# --------------------------------------------------------------------------

#: Verbatim from BGC Group's agreement. A FLOOR, written negatively.
BGC = ("Net Excess Capital with respect to all Regulated Subsidiaries "
       "to be less than $300,000,000.")

#: Verbatim from Viskase's. Also a FLOOR, written positively. The two phrase
#: the same constraint with opposite comparators, which is why the comparator
#: cannot be the authority.
VISKASE = "Liquidity shall be greater than $10,000,000."


def test_floor_written_negatively_is_min() -> None:
    c = covenant_clause(BGC, "Net Excess Capital", "net_capital")
    assert c is not None
    assert c["direction"] == "min"
    assert c["threshold"] == 300_000_000.0


def test_floor_written_positively_is_also_min() -> None:
    """The case the first implementation got backwards.

    "greater than" was absent from the min-list, so a floor was recorded as a
    ceiling — a covenant pointing the wrong way, which reads as evidence.
    """
    c = covenant_clause(VISKASE, "Liquidity", "minimum_liquidity")
    assert c is not None
    assert c["direction"] == "min"


def test_opposite_comparators_yield_the_same_direction() -> None:
    """The discriminating test: same constraint, opposite words, one answer."""
    a = covenant_clause(BGC, "Net Excess Capital", "net_capital")
    b = covenant_clause(VISKASE, "Liquidity", "minimum_liquidity")
    assert a["direction"] == b["direction"] == "min"


def test_ceiling_type_is_max_regardless_of_phrasing() -> None:
    text = "Consolidated Leverage Ratio to exceed $500,000,000."
    c = covenant_clause(text, "Consolidated Leverage Ratio", "leverage")
    assert c is not None
    assert c["direction"] == "max"


def test_every_creatable_type_has_a_declared_direction() -> None:
    """A covenant type with no declared direction must not produce a clause.

    Otherwise direction would silently be None and the loader would write a
    covenant that points nowhere.
    """
    assert covenant_clause(BGC, "Net Excess Capital", "unknown_type") is None
    for ct in EXPECTED_DIRECTION:
        assert EXPECTED_DIRECTION[ct] in {"min", "max"}


# --------------------------------------------------------------------------
# declaration conventions — one issuer is not the format
# --------------------------------------------------------------------------

@pytest.mark.parametrize(("text", "expected"), [
    ("“Consolidated EBITDA”: without duplication, for any period", "colon"),
    ("“Consolidated EBITDA” means without duplication", "means"),
    ("“Consolidated EBITDA” shall mean without duplication", "shall_mean"),
])
def test_all_three_conventions_are_matched(text: str, expected: str) -> None:
    d = declarations(text)
    assert len(d) == 1
    assert d[0]["term"] == "Consolidated EBITDA"
    assert d[0]["convention"] == expected


def test_term_wrapped_across_a_newline_is_one_term() -> None:
    """Filers' HTML-to-text passes break terms mid-phrase.

    Without normalisation "Consolidated Coverage\\nRatio" is a different term
    from every other occurrence, and the component match silently misses it.
    """
    assert normalise("Consolidated Coverage\nRatio") == "Consolidated Coverage Ratio"
    d = declarations("“Consolidated Coverage\nRatio”: as defined in Schedule 1.1G.")
    assert d[0]["term"] == "Consolidated Coverage Ratio"


def test_first_declaration_wins() -> None:
    text = ("“Applicable Rate” means the first definition. "
            "“Applicable Rate” means the restated one.")
    d = declarations(text)
    assert len(d) == 1
    assert d[0]["decl_offset"] == 0


def test_body_ends_at_the_next_declaration() -> None:
    text = "“A Term Here” means alpha beta. “B Term Here” means gamma."
    d = declarations(text)
    assert len(d) == 2
    assert d[0]["body_end"] <= d[1]["decl_offset"]


# --------------------------------------------------------------------------
# component matching
# --------------------------------------------------------------------------

def test_longest_term_wins() -> None:
    """First-match alternation would record the longer term as the shorter one,
    rewiring the dependency graph to the wrong node."""
    finder = component_finder(["Total Debt", "Consolidated Total Debt"])
    assert finder is not None
    assert finder.search("plus Consolidated Total Debt as of").group(0) == (
        "Consolidated Total Debt")


def test_component_finder_empty_is_none() -> None:
    assert component_finder([]) is None
    assert component_finder(["abc"]) is None  # below the length floor


# --------------------------------------------------------------------------
# the cross-document pattern
# --------------------------------------------------------------------------

def test_cross_doc_matches_a_form_citation() -> None:
    assert CROSS_DOC.search("as shown on the Borrower’s SEC Forms 10-Q and 10-K.")


def test_cross_doc_rejects_annual_reporting_periods() -> None:
    """The false positive that a bare `Annual Report` pattern produced.

    Pebblebrook's "FAS 141R Changes" definition says "effective for annual
    reporting periods that begin in calendar year 2009" — no cross-document
    citation at all. A pattern matching it would have reported a §F condition
    satisfied by prose about accounting standards.
    """
    assert not CROSS_DOC.search(
        "which is effective for annual reporting periods that begin in 2009")
