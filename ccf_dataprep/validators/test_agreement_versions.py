#!/usr/bin/env python3
"""Grouping EX-10 texts into agreement versions, so `as_of` can choose.

`covenant-cross-reference` §F asks for ">= 3 agreements with a filed
amendment, SO `as_of` CHANGES WHICH TEXT GOVERNS". The clause after the comma
is the condition: two texts must be identifiable as belonging to the same
agreement, or an `as_of` before the amendment resolves to nothing.

The cases below are the ones that actually broke it, kept as fixtures because
each is a shape a looser rule gets wrong:

  * an amendment whose own date and its agreement's date are 44 characters
    apart in the title -- the first version required them within 40 and
    classified every such document as a base agreement;
  * a title block still wearing the SEC HTML wrapper, so an anchored `^`
    pattern never matched;
  * two amendments to ONE agreement with no base text held (TransDigm), which
    is still a versioned agreement -- `as_of` between them selects;
  * two amendments to DIFFERENT agreements filed the SAME DAY by the same
    filer (PAYCHEX 2017 and 2019), which must NOT group.

    uv run --with pytest pytest validators/test_agreement_versions.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "link_agreement_versions", REPO / "generators" /
    "link_agreement_versions_wave15.py")
lk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lk)

# Verbatim title blocks, SEC wrapper included, as they arrive from Mongo.
PAYCHEX_AMD4 = (
    " EX-10.2 3 payx-ex10_2.htm EX-10.2 EX-10.2 EXECUTION COPY AMENDMENT NO. 4 "
    "Dated as of January 23, 2026 to 2019 CREDIT AGREEMENT Dated as of "
    "July 31, 2019 among PAYCHEX OF NEW YORK LLC, as Borrower")
PAYCHEX_AMD6 = (
    " EX-10.1 2 payx-ex10_1.htm EX-10.1 EX-10.1 EXECUTION COPY AMENDMENT NO. 6 "
    "Dated as of January 23, 2026 to 2017 CREDIT AGREEMENT Dated as of "
    "October 20, 2017 among PAYCHEX OF NEW YORK LLC, as Borrower")
PAYCHEX_BASE = (
    " EX-10.1 2 payx-20190731xex10_1.htm EX-10.1 Exhibit 10.1 Exhibit 10.1 | "
    "EXECUTION COPY | 2019 CREDIT AGREEMENT dated as of July 31, 2019 among "
    "PAYCHEX OF NEW YORK LLC, as Borrower PAYCHEX, INC")
TRANSDIGM_20 = (
    " EX-10.1 3 d83933dex101.htm EX-10.1 EX-10.1 Exhibit 10.1 EXECUTION VERSION "
    "AMENDMENT NO. 20 and INCREMENTAL TERM LOAN ASSUMPTION AGREEMENT dated as "
    "of February 13, 2026 to the Second Amended and Restated Credit Agreement "
    "dated as of June 4, 2014 among TRANSDIGM INC.")
TRANSDIGM_21 = (
    " EX-10.1 3 d108525dex101.htm EX-10.1 EX-10.1 Exhibit 10.1 EXECUTION VERSION "
    "AMENDMENT NO. 21 and INCREMENTAL TERM LOAN ASSUMPTION AGREEMENT dated as "
    "of April 17, 2026 to the Second Amended and Restated Credit Agreement "
    "dated as of June 4, 2014 among TRANSDIGM INC.")
CELANESE_BASE = (
    " EX-10.1 2 tm2523061d1_ex10-1.htm EXHIBIT 10.1 Exhibit 10.1 Published Deal "
    "CUSIP Number: 15089XAQ2 CREDIT AGREEMENT Dated as of August 11, 2025 among "
    "CELANESE CORPORATION, as Holdings")
CELANESE_AMD = (
    " EX-10.1 2 tm2622089d1_ex10-1.htm EXHIBIT 10.1 Exhibit 10.1 Execution "
    "Version FIRST AMENDMENT TO CREDIT AGREEMENT, dated as of July 31, 2026 "
    "(this “First Amendment”), by and among Celanese Corporation, a Delaware "
    "corporation, which amends the Credit Agreement dated as of "
    "August 11, 2025")


# -- role ------------------------------------------------------------------

def test_amendment_with_a_distant_second_date_is_an_amendment():
    """44 characters between the two dates. The original bound was 40."""
    role, governs, underlying = lk.classify(PAYCHEX_AMD4)
    assert role == "amendment"
    assert governs == "2026-01-23"
    assert underlying == "2019-07-31"


def test_amendment_titles_survive_the_sec_wrapper():
    role, _, _ = lk.classify(TRANSDIGM_20)
    assert role == "amendment"


def test_base_agreement_is_not_read_as_an_amendment():
    """The negative control for the role rule.

    Without it, classifying everything as an amendment passes every
    amendment arm above.
    """
    for text in (PAYCHEX_BASE, CELANESE_BASE):
        role, governs, underlying = lk.classify(text)
        assert role == "base", f"base agreement classified {role}: {text[:70]}"
        assert governs == underlying, "a base agreement dates itself"


# -- grouping --------------------------------------------------------------

def _aid(lei: str, text: str) -> str:
    _, _, underlying = lk.classify(text)
    return f"{lei}:{underlying}"


def test_two_amendments_to_one_agreement_group_together():
    """TransDigm: no base text held, and still a versioned agreement."""
    lei = "549300EQD0ZXRSMG3549"
    assert _aid(lei, TRANSDIGM_20) == _aid(lei, TRANSDIGM_21)
    assert lk.classify(TRANSDIGM_20)[1] != lk.classify(TRANSDIGM_21)[1], (
        "the two texts must govern from different dates or as_of cannot choose")


def test_base_and_its_amendment_group_together():
    lei = "529900K900DW6SUBM174"
    assert _aid(lei, PAYCHEX_BASE) == _aid(lei, PAYCHEX_AMD4)


def test_same_filer_same_day_different_agreements_do_not_group():
    """PAYCHEX Amendment No. 4 and No. 6, filed together, must stay apart.

    This is the falsifier for the whole approach: any rule keyed on filer or
    on accession passes every other arm and fails this one.
    """
    lei = "529900K900DW6SUBM174"
    assert _aid(lei, PAYCHEX_AMD4) != _aid(lei, PAYCHEX_AMD6)
    assert lk.classify(PAYCHEX_AMD6)[2] == "2017-10-20"
