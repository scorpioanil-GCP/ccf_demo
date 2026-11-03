"""Mutation tests for the trigger-amendment gate.

Each test breaks the data in one specific way and asserts the gate NOTICES.
A gate that passes all of these while passing on correct data is measuring
something; a gate that passes them is decoration.

The second block -- the triple-shape tests -- guards the three things an
append-only store makes unfixable after the fact: the DIRECTION of the
supersession edge, the vocabulary it is written in, and whether the new node
is reachable and labelled at all. Those cannot be checked by re-reading the
ledger afterwards, because by then the wrong triple is permanent.

## Expected values are LITERALS here, and the duplication is deliberate

Three tests in this file once read

    assert f'... "{AMENDMENT["asserted_at"].isoformat()}" .' in rendered

which compares a rendered triple against the very constant that rendered it.
That is true for every possible value of the constant, so it is not an
assertion at all. It was caught in review after `asserted_at = date.today()`
was shown to leave all 21 tests green -- the exact mutation the test's own
docstring said it existed to prevent.

So the expected dates and thresholds below are hard-coded strings, typed out
independently of `AMENDMENT`, and `test_the_amendment_constants_are_pinned`
asserts the constants themselves. Changing a date now means editing it in two
places on purpose: the second edit is the review checkpoint, and a drift that
edits only the generator fails loudly.

The general rule this file follows: **an expected value must not be derived
from the code under test.** Where it cannot be a literal, it comes from an
independent source -- see `test_the_amendment_is_reachable_from_the_deal_in_two_hops`,
which gets its expectation from Task 9's loader rather than from this task's.
"""
from __future__ import annotations

from datetime import date

import pytest

from generators.generate_trigger_amendment import (
    AMENDMENT, build_triples, threshold_as_of, threshold_known_as_of,
)


# Typed out by hand, NOT read from `AMENDMENT`. If these ever agree with the
# generator only because they were copied from it, this block stops being a
# test. See the module docstring.
EFFECTIVE_FROM = "2025-11-01"
ASSERTED_AT = "2026-01-11"
NEW_THRESHOLD = "13.50"
PRIOR_THRESHOLD = "24.00"


def test_the_amendment_constants_are_pinned():
    """The load-bearing test of this file, and the one that was missing.

    Several tests below derive their probe date from `AMENDMENT` itself --
    the gap midpoint, for instance, is
    `effective_from + (asserted_at - effective_from) / 2`. A derived probe
    stays inside the gap for ANY pair of dates, so those tests remain green
    while the dates drift underneath them. That is how
    `asserted_at = date.today()` passed all 21 tests.

    Pinning the constants here is what makes every derived probe in this file
    trustworthy: the derivations may assume the dates, because this test
    proves them. Nothing else in the file needs to re-check them.
    """
    assert AMENDMENT["effective_from"] == date(2025, 11, 1)
    assert AMENDMENT["asserted_at"] == date(2026, 1, 11)
    assert AMENDMENT["new_threshold"] == NEW_THRESHOLD
    # The lag is 71 days, and the mechanism is the lag. Stated as a number
    # rather than as `asserted > effective`, because "positive" is satisfied
    # by one day and one day demonstrates nothing.
    assert (AMENDMENT["asserted_at"] - AMENDMENT["effective_from"]).days == 71


def _chain():
    """The assertion chain as the generator builds it.

    The first entry is Task 9's original, whose 24.00% comes from the filed
    prospectus -- not from this task's generator -- so it is written here as
    the independent value it is.
    """
    return [
        {"value": PRIOR_THRESHOLD, "effective_from": date(2022, 9, 14),
         "asserted_at": date(2022, 9, 14), "provenance": "public"},
        {"value": AMENDMENT["new_threshold"],
         "effective_from": AMENDMENT["effective_from"],
         "asserted_at": AMENDMENT["asserted_at"],
         "provenance": "synthetic — engineered"},
    ]


def test_effective_precedes_assertion():
    """No lag, no demonstration. This is the whole mechanism."""
    assert AMENDMENT["effective_from"] < AMENDMENT["asserted_at"]


def test_as_of_before_effective_returns_the_original():
    assert threshold_as_of(_chain(), date(2025, 8, 1)) == PRIOR_THRESHOLD


def test_as_of_after_effective_returns_the_amendment():
    assert threshold_as_of(_chain(), date(2026, 5, 1)) == AMENDMENT["new_threshold"]


def test_known_as_of_inside_the_gap_returns_the_original():
    """The one a mirroring pipeline loses.

    Between the effective date and the assertion date the amendment was in
    force but not yet known. Asking what we KNEW must return 24.00.
    """
    gap = AMENDMENT["effective_from"] + (AMENDMENT["asserted_at"]
                                         - AMENDMENT["effective_from"]) / 2
    assert threshold_known_as_of(_chain(), gap) == PRIOR_THRESHOLD


def test_known_as_of_after_assertion_returns_the_amendment():
    assert threshold_known_as_of(
        _chain(), AMENDMENT["asserted_at"]) == AMENDMENT["new_threshold"]


def test_as_of_and_known_as_of_actually_diverge():
    """If they agree everywhere, the bitemporal claim is unfalsifiable."""
    gap = AMENDMENT["effective_from"] + (AMENDMENT["asserted_at"]
                                         - AMENDMENT["effective_from"]) / 2
    assert threshold_as_of(_chain(), gap) != threshold_known_as_of(_chain(), gap)


def test_amendment_is_labelled_engineered():
    assert AMENDMENT["provenance"] == "synthetic — engineered"


def test_amendment_carries_no_passage_anchor():
    """No prospectus sentence says this. Claiming an anchor would be a lie
    that the trigger-anchoring gate would happily accept."""
    assert AMENDMENT.get("passage_anchor") is None


def test_mutation_removing_the_lag_breaks_divergence():
    """Collapse the lag and the mechanism must stop working."""
    chain = _chain()
    chain[1]["asserted_at"] = chain[1]["effective_from"]
    gap = chain[1]["effective_from"]
    assert threshold_as_of(chain, gap) == threshold_known_as_of(chain, gap)


def test_new_threshold_is_close_to_the_real_series():
    """A threshold far from the observed series changes proximity by a
    constant and demonstrates nothing. It must actually bite."""
    assert 10 < float(AMENDMENT["new_threshold"]) < 16


# ---------------------------------------------------------------------------
# The triple list. Fluree is append-only, so these are checked BEFORE the
# write or not usefully at all.
# ---------------------------------------------------------------------------

ORIG = "http://example.org/fibo/abs-trigger-SDART-2022-6-delinquency"
AMEND = ORIG + "-amendment"
DEAL = "http://example.org/fibo/abs-deal-SDART-2022-6"
SUPERSEDED_BY = "http://example.org/fibo/supersededBy"
SPECIFIES = ("https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/"
             "CollateralizedDebtObligations/specifiesTrigger")
LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


@pytest.fixture(scope="module")
def rendered():
    return [f"<{s}> <{p}> {o} ." for s, p, o in
            ((st.s, st.p, f'"{st.o}"' if st.literal else f"<{st.o}>")
             for st in build_triples())]


def test_supersession_runs_old_to_new(rendered):
    """The estate writes the FORWARD edge -- `triple(older, supersededBy,
    newer)` in Waves 11a, 11b and 12. Reversing it here would leave 215
    existing assertions pointing one way and this one the other, forever.
    """
    assert f"<{ORIG}> <{SUPERSEDED_BY}> <{AMEND}> ." in rendered


def test_supersession_is_not_written_backwards(rendered):
    assert f"<{AMEND}> <{SUPERSEDED_BY}> <{ORIG}> ." not in rendered


def test_no_ex_supersedes_is_minted(rendered):
    """`ex:supersededBy` is bound and carries 215 assertions. The binding
    table names minting `ex:supersedes` beside it as the failure mode."""
    assert not any("supersedes>" in line for line in rendered)


def test_amendment_is_labelled(rendered):
    """Task 9 gave 33 labels to 33 nodes. An unlabelled node in the same
    slice is invisible to every label-driven listing."""
    labels = [line for line in rendered
              if line.startswith(f"<{AMEND}> <{LABEL}> ")]
    assert len(labels) == 1
    # A prefix match alone passes on `<AMEND> <LABEL> "" .` -- an empty label
    # is exactly as invisible in a listing as no label at all.
    assert labels[0] != f'<{AMEND}> <{LABEL}> "" .'
    assert "amend" in labels[0].lower()


def test_the_deal_does_not_specify_a_second_delinquency_trigger(rendered):
    """The inverse of the test this started as -- and the inversion is the
    finding, so it is kept rather than deleted.

    The first draft asserted `<deal> specifiesTrigger <amendment>`, on the
    reasoning that an amendment with no deal edge is unreachable from any
    deal-scoped query. That reasoning was wrong twice.

    Semantically: SDART-2022-6 specifies ONE delinquency trigger, not two. A
    second `specifiesTrigger` edge would assert the deal has two distinct
    delinquency triggers. What actually happened is that one trigger's
    threshold was amended.

    Mechanically: Task 9's `ledger_conflicts` requires the ledger's object set
    for a (subject, predicate) pair to be a subset of what its run asserts. A
    fourth `specifiesTrigger` object on the deal would make
    `load_abs_fluree_wave14.py` refuse to re-run -- permanently, in an
    append-only store.

    The amendment is reachable, one hop further along, and that hop is the
    thing being demonstrated:

        deal -specifiesTrigger-> original -supersededBy-> amendment
    """
    assert f"<{DEAL}> <{SPECIFIES}> <{AMEND}> ." not in rendered
    assert not any(SPECIFIES in line for line in rendered)


def test_the_amendment_is_reachable_from_the_deal_in_two_hops(rendered):
    """Dropping the deal edge must not make the node an orphan. The chain
    has to be walkable: something Task 9 hangs off the deal must carry the
    supersededBy edge that lands on the amendment."""
    assert f"<{ORIG}> <{SUPERSEDED_BY}> <{AMEND}> ." in rendered
    # ORIG is one of the three triggers load_abs_fluree_wave14.py attaches to
    # the deal, so deal -> ORIG -> AMEND resolves.
    from loaders.load_abs_fluree_wave14 import build_triples as task9_triples
    deal_edges = {t.o for t in task9_triples()
                  if t.s == DEAL and t.p == SPECIFIES}
    assert ORIG in deal_edges


def test_the_amendment_carries_a_threshold_component(rendered):
    """Task 9 put at least one `thresholdComponent` on every one of the ten
    originals. A consumer reading components rather than values would find
    the amendment empty, not single-valued, if this were omitted."""
    assert (f'<{AMEND}> <http://example.org/fibo/thresholdComponent> '
            f'"{NEW_THRESHOLD}" .') in rendered


def test_no_passage_anchor_triple_is_emitted(rendered):
    assert not any("passageAnchor" in line for line in rendered)


def test_provenance_triple_says_engineered(rendered):
    assert (f'<{AMEND}> <http://example.org/fibo/provenance> '
            f'"synthetic — engineered" .') in rendered


def test_the_two_dates_are_carried_as_written(rendered):
    """Neither date may be `now`. A `now` assertedAt is later than the
    amendment's own assertion date, so `threshold_known_as_of` inside the
    gap would find no assertion and return None -- and the divergence check
    would pass on `13.50 != None`, green while measuring nothing."""
    assert (f'<{AMEND}> <http://example.org/fibo/validFrom> '
            f'"{EFFECTIVE_FROM}" .') in rendered
    assert (f'<{AMEND}> <http://example.org/fibo/assertedAt> '
            f'"{ASSERTED_AT}" .') in rendered


def test_the_amendment_asserts_its_threshold_on_its_own_node(rendered):
    """A supersession, not a contradiction. Re-asserting a second
    `thresholdValue` on the ORIGINAL subject would leave the ledger holding
    two values for one predicate with nothing marking which is current."""
    assert not any(line.startswith(f"<{ORIG}> ") and "thresholdValue" in line
                   for line in rendered)
    assert (f'<{AMEND}> <http://example.org/fibo/thresholdValue> '
            f'"{NEW_THRESHOLD}" .') in rendered
