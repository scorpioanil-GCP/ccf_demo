"""Task 1 — the administrative-agent repair.

Every case below is REAL TEXT taken from a filed EX-10 in sources/ex10/.
The four `corrupt` cases are the exact strings currently stored in
ccf_v2.facility.administrative_agent.
"""
import pytest
from generators.extract_facilities import extract_agent

# (agreement text fragment, expected institution name)
REAL_PREAMBLES = [
    ("JPMORGAN CHASE BANK, N.A., in its capacity as administrative agent "
     "for the Lenders", "JPMORGAN CHASE BANK, N.A."),
    ("BANK OF AMERICA, N.A., as Administrative Agent, Swing Line Lender "
     "and L/C Issuer", "BANK OF AMERICA, N.A."),
    ("GOLDMAN SACHS BANK USA, as Administrative Agent and Collateral Agent",
     "GOLDMAN SACHS BANK USA"),
    ("the several banks and other financial institutions from time to time "
     "party hereto, and BANK OF AMERICA, N.A., as Administrative Agent",
     "BANK OF AMERICA, N.A."),
    ("each lender that is a party hereto and identified on the signature "
     "pages hereof and CITIBANK, N.A., as administrative agent",
     "CITIBANK, N.A."),
    ("BARCLAYS BANK PLC, not in its individual capacity but solely as "
     "Administrative Agent", "BARCLAYS BANK PLC"),
]

@pytest.mark.parametrize("text,expected", REAL_PREAMBLES)
def test_extracts_the_institution_not_the_connective(text, expected):
    got = extract_agent(text)
    assert got is not None, f"no agent found in: {text[:60]!r}"
    assert got["name"] == expected


CONNECTIVE_FRAGMENTS = [
    "in its capacity", "in its capacities", "in such capacity",
    "that is a party hereto", "on the signature pages hereof",
    "not in its individual capacity", "and",
]

@pytest.mark.parametrize("text,expected", REAL_PREAMBLES)
def test_no_connective_survives_into_the_name(text, expected):
    """The four stored-corrupt values are all connectives. None may return."""
    got = extract_agent(text)
    lowered = got["name"].lower()
    for frag in CONNECTIVE_FRAGMENTS:
        assert lowered != frag, f"captured the connective {frag!r}"
        assert not lowered.startswith(frag + " "), f"leading {frag!r}"


def test_absent_agent_returns_none():
    """The checker must be able to say NO. A matcher that always matches
    is the defect this task exists to fix."""
    assert extract_agent("This agreement has no agent clause at all.") is None
    assert extract_agent("") is None


def test_offset_points_at_the_captured_name():
    text = "Dated as of June 4, 2014. GOLDMAN SACHS BANK USA, as Administrative Agent"
    got = extract_agent(text)
    assert text[got["offset"]:got["offset"] + len(got["name"])] == got["name"]
    # The general contract is {"name", "offset", "end"} with the invariant
    # " ".join(doc_text[offset:end].split()) == name (see
    # test_offset_end_span_survives_an_embedded_newline for the case where
    # this fixture's simpler offset+len(name) check would NOT have been
    # enough to catch a mismatch).
    assert " ".join(text[got["offset"]:got["end"]].split()) == got["name"]


def test_short_real_alias_is_not_dropped_as_too_short():
    """Regression pin: a length floor of `< 4` silently discarded this real
    3-character defined-term alias during Task 1's own repair -- every one
    of the 14 tests above still passed with that bug in place, and only a
    yield comparison against the pre-fix extraction caught it. Real text
    from REGIS CORP (0001193125-24-281618, d761586dex101.htm): TCW Asset
    Management Company LLC is defined as "TCW" earlier in the agreement,
    and the agreement literally reuses the short form at the anchor.
    """
    text = ('the “Collateral Agent”), TCW, as administrative agent for the '
            'Lenders')
    got = extract_agent(text)
    assert got is not None, "a real 3-character alias must not be dropped"
    assert got["name"] == "TCW"


def test_offset_end_span_survives_an_embedded_newline():
    """Regression pin, reviewer finding (fix round 1): `name` is whitespace-
    NORMALISED but `offset` pointed at the RAW span, so when the captured
    name spans an embedded newline -- which TextExtractor.text() deliberately
    preserves -- doc_text[offset:offset+len(name)] != name. Confirmed against
    real filings: MASTEC INC (0000950170-24-131845, d77261dex101.htm) reads
    "BANK OF AMERICA,\\nN.A." at the anchor. The contract is now
    {"name", "offset", "end"} with the checkable invariant
    " ".join(doc_text[offset:end].split()) == name -- this fixture is built
    from that real text and must satisfy it.
    """
    text = ("MASTEC NORTH AMERICA, INC., as Borrowers, \nBANK OF AMERICA,\n"
            "N.A., \nas Administrative Agent")
    got = extract_agent(text)
    assert got is not None
    assert got["name"] == "BANK OF AMERICA, N.A."
    span = text[got["offset"]:got["end"]]
    assert " ".join(span.split()) == got["name"], (
        f"span {span!r} does not normalise to name {got['name']!r}")
