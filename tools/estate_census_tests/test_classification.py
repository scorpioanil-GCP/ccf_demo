"""Controls over `tools/estate_census/classify.py` — the three-state half of
`D-IMPL-358` ruling 8.

Dave's four named controls are here by name: a known base red classifies as
base-existing; a fabricated new node HOLDs; a missing artifact is INDETERMINATE;
a malformed artifact is INDETERMINATE. So is the fifth he singled out — two
result sets with **identical aggregate failure counts and different failing node
ids** must be detected — and every INDETERMINATE cause this project has actually
been burned by.

**The positive control is `test_pass_is_reachable_on_evidence_that_deserves_it`.**
Without it every assertion here could pass because the classifier can never say
PASS, which is the shape of a gate that cannot go green and therefore proves
nothing when it goes red.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from tools.estate_census.classify import (
    HOLD,
    HOLD_CODES,
    INDETERMINATE,
    INDETERMINATE_CODES,
    PASS,
    ReasonCode,
    classify,
    render,
)
from tools.estate_census.evidence import BUNDLE_KIND, BUNDLE_VERSION

NODE = "tests/examples/test_cp_%02d.py::test_%s"


def bundle(outcomes: dict[str, str], *, position: int = 5296, **overrides: Any) -> dict[str, Any]:
    """A well-formed bundle carrying exactly `outcomes`.

    Counts are DERIVED here rather than stated, so a fixture can never
    accidentally assert a disagreement the test did not intend.
    """
    built = {
        node: {"outcome": outcome, "phases": [{"when": "call", "outcome": outcome, "detail": ""}]}
        for node, outcome in outcomes.items()
    }
    tally = {key: 0 for key in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")}
    for outcome in outcomes.values():
        tally[outcome] = tally.get(outcome, 0) + 1
    estate = {
        "fluree/curated": {
            "kind": "fluree",
            "target": "http://192.168.4.76:8090",
            "position": {"ledger_count": 28, "ledger_positions": {"fibo-v2:main": position}},
        }
    }
    payload: dict[str, Any] = {
        "kind": BUNDLE_KIND,
        "version": BUNDLE_VERSION,
        "provenance": {"exit_status": 1 if tally["failed"] or tally["error"] else 0},
        "collected": list(built),
        "outcomes": built,
        "collection_errors": [],
        "counts": {
            "passed": tally["passed"],
            "failed": tally["failed"],
            "errors": tally["error"],
            "skipped": tally["skipped"],
            "xfailed": tally["xfailed"],
            "xpassed": tally["xpassed"],
        },
        "estate": {"before": copy.deepcopy(estate), "after": copy.deepcopy(estate)},
    }
    payload.update(overrides)
    return payload


BASE = bundle(
    {
        NODE % (4, "a"): "passed",
        NODE % (4, "b"): "failed",
        NODE % (5, "a"): "error",
        NODE % (5, "b"): "passed",
    }
)


def aggregates(payload: dict[str, Any]) -> dict[str, int]:
    return {key: payload["counts"][key] for key in ("passed", "failed", "errors", "skipped")}


# --------------------------------------------------------------------------
# Preconditions and the positive control.
# --------------------------------------------------------------------------


def test_the_code_vocabulary_partitions_exactly_into_indeterminate_and_hold() -> None:
    """A code in neither set, or in both, would make `reason_codes` unbranchable —
    the confusion between "I could not tell" and "I found a problem" that the
    three-state model exists to prevent."""
    declared = {value for name, value in vars(ReasonCode).items() if name.isupper()}
    assert declared == INDETERMINATE_CODES | HOLD_CODES
    assert not INDETERMINATE_CODES & HOLD_CODES


def test_pass_is_reachable_on_evidence_that_deserves_it() -> None:
    """THE POSITIVE CONTROL. A classifier that can never say PASS proves nothing
    when it says HOLD."""
    clean = bundle({NODE % (4, "a"): "passed", NODE % (4, "b"): "passed"})
    verdict = classify(clean, clean)
    assert verdict.state == PASS, verdict.reasons
    assert verdict.exit_code == 0
    assert verdict.reason_codes == ()


# --------------------------------------------------------------------------
# Dave's four named controls.
# --------------------------------------------------------------------------


def test_a_known_base_red_classifies_as_base_existing_and_not_as_new() -> None:
    verdict = classify(BASE, copy.deepcopy(BASE))
    assert verdict.state == PASS, verdict.reasons
    assert verdict.base_existing_red == (NODE % (4, "b"), NODE % (5, "a"))
    assert verdict.new_red == ()


def test_a_fabricated_new_node_is_a_hold_and_names_the_node() -> None:
    candidate = bundle(
        {
            NODE % (4, "a"): "passed",
            NODE % (4, "b"): "failed",
            NODE % (5, "a"): "error",
            NODE % (5, "b"): "failed",
        }
    )
    verdict = classify(BASE, candidate)
    assert verdict.state == HOLD
    assert verdict.exit_code == 1
    assert verdict.new_red == (NODE % (5, "b"),)
    assert ReasonCode.NEW_RED in verdict.reason_codes


def test_a_missing_artifact_is_indeterminate_and_never_zero_tests() -> None:
    verdict = classify(BASE, None, candidate_unreadable_reason="no such file")
    assert verdict.state == INDETERMINATE
    assert verdict.exit_code == 2
    assert verdict.reason_codes == (ReasonCode.EVIDENCE_UNREADABLE,)
    assert "no such file" in verdict.reasons[0].detail


@pytest.mark.parametrize(
    "label,broken",
    [
        ("not-an-object", "a string, not a bundle"),
        ("wrong-kind", {**copy.deepcopy(BASE), "kind": "something-else"}),
        ("wrong-version", {**copy.deepcopy(BASE), "version": 999}),
        ("rosters-missing", {"kind": BUNDLE_KIND, "version": BUNDLE_VERSION}),
        ("outcomes-not-an-object", {**copy.deepcopy(BASE), "outcomes": []}),
    ],
)
def test_a_malformed_artifact_is_indeterminate_with_a_code_naming_the_flaw(
    label: str, broken: Any
) -> None:
    verdict = classify(BASE, broken)
    assert verdict.state == INDETERMINATE, label
    assert verdict.exit_code == 2
    assert set(verdict.reason_codes) <= INDETERMINATE_CODES, label
    assert verdict.reason_codes, label


# --------------------------------------------------------------------------
# The control Dave singled out.
# --------------------------------------------------------------------------


def test_an_identical_failure_count_with_a_different_red_set_is_detected() -> None:
    """Dave's explicit requirement. Aggregate equality is not set equality, and an
    aggregate-only comparison passes this pair while seeing nothing at all."""
    swapped = bundle(
        {
            NODE % (4, "a"): "failed",   # was passed
            NODE % (4, "b"): "passed",   # was failed
            NODE % (5, "a"): "error",
            NODE % (5, "b"): "passed",
        }
    )
    assert aggregates(BASE) == aggregates(swapped), (
        "the fixture no longer exercises the property — the aggregates must MATCH"
    )
    verdict = classify(BASE, swapped)
    assert verdict.state == HOLD
    assert verdict.new_red == (NODE % (4, "a"),)
    assert verdict.recovered == (NODE % (4, "b"),)
    assert ReasonCode.NEW_RED in verdict.reason_codes


# --------------------------------------------------------------------------
# Every INDETERMINATE cause this project has been burned by.
# --------------------------------------------------------------------------


def test_a_collection_error_is_indeterminate_because_its_node_ids_never_ran() -> None:
    """Measured: one uncollectable module makes pytest exit 2 having run NOTHING,
    while a summary counting only failures shows none."""
    candidate = bundle(
        {NODE % (4, "a"): "passed"},
        collection_errors=[{"nodeid": "tests/examples/test_cp_05.py", "detail": "ImportError"}],
    )
    verdict = classify(BASE, candidate)
    assert verdict.state == INDETERMINATE
    assert ReasonCode.EXECUTION_COLLECTION_ERROR in verdict.reason_codes


def test_a_collected_node_that_reported_no_outcome_is_execution_incomplete() -> None:
    """`collected` is what pytest SELECTED; `outcomes` is what reported. The gap is
    the measured shape of an aborted run."""
    candidate = bundle({NODE % (4, "a"): "passed"})
    candidate["collected"].append(NODE % (9, "never"))
    verdict = classify(BASE, candidate)
    assert verdict.state == INDETERMINATE
    assert ReasonCode.EXECUTION_INCOMPLETE in verdict.reason_codes
    assert NODE % (9, "never") in verdict.reasons[0].items


def test_zero_reported_tests_is_indeterminate_and_not_a_pass() -> None:
    verdict = classify(BASE, bundle({}))
    assert verdict.state == INDETERMINATE
    assert ReasonCode.EXECUTION_ZERO_TESTS in verdict.reason_codes


@pytest.mark.parametrize("status", [2, 3, 4, 5])
def test_an_abnormal_pytest_exit_status_is_indeterminate(status: int) -> None:
    candidate = bundle({NODE % (4, "a"): "passed"}, provenance={"exit_status": status})
    verdict = classify(BASE, candidate)
    assert verdict.state == INDETERMINATE
    assert ReasonCode.EXECUTION_ABORTED in verdict.reason_codes


def test_counts_that_disagree_with_their_own_roster_are_indeterminate() -> None:
    """A count is a claim about a roster that ships in the same file."""
    candidate = copy.deepcopy(BASE)
    candidate["counts"]["failed"] = 99
    verdict = classify(BASE, candidate)
    assert verdict.state == INDETERMINATE
    assert ReasonCode.COUNTS_DISAGREE_WITH_ROSTER in verdict.reason_codes


def test_an_artifact_carrying_a_credential_is_not_valid_census_evidence() -> None:
    """Dave: *"Raw evidence containing a secret ... is not treated as valid census
    evidence."* A verdict, not a warning."""
    verdict = classify(
        BASE, copy.deepcopy(BASE), candidate_credential="uri-userinfo-password at offset 2989"
    )
    assert verdict.state == INDETERMINATE
    assert ReasonCode.EVIDENCE_CARRIES_CREDENTIAL in verdict.reason_codes


@pytest.mark.parametrize("side", ["before", "after"])
def test_an_unmeasured_estate_position_is_indeterminate_not_an_unmoved_one(side: str) -> None:
    """Comparing two absences would PROVE the estate did not move. An outage is
    *don't know*."""
    candidate = copy.deepcopy(BASE)
    candidate["estate"][side]["fluree/curated"] = {
        "kind": "fluree",
        "target": "http://192.168.4.76:8090",
        "error": "ConnectError: refused",
    }
    verdict = classify(BASE, candidate)
    assert verdict.state == INDETERMINATE
    assert ReasonCode.ESTATE_NOT_MEASURED in verdict.reason_codes


def test_an_entirely_absent_estate_measurement_is_indeterminate() -> None:
    candidate = copy.deepcopy(BASE)
    candidate["estate"] = {"before": {}, "after": {}}
    verdict = classify(BASE, candidate)
    assert verdict.state == INDETERMINATE
    assert verdict.reason_codes.count(ReasonCode.ESTATE_NOT_MEASURED) == 2


def test_a_store_roster_that_changed_between_before_and_after_is_indeterminate() -> None:
    candidate = copy.deepcopy(BASE)
    candidate["estate"]["after"]["postgres/curated"] = {"kind": "postgres", "position": {"rows": 1}}
    verdict = classify(BASE, candidate)
    assert verdict.state == INDETERMINATE
    assert ReasonCode.ESTATE_ROSTER_CHANGED in verdict.reason_codes


def test_a_declared_chunk_that_never_reported_is_indeterminate() -> None:
    """A chunk that timed out contributes no failures at all."""
    verdict = classify(
        BASE,
        copy.deepcopy(BASE),
        declared_chunks=("chunk-a", "chunk-b"),
        reported_chunks=("chunk-a",),
    )
    assert verdict.state == INDETERMINATE
    assert ReasonCode.CHUNK_NEVER_REPORTED in verdict.reason_codes
    assert verdict.reasons[-1].items == ("chunk-b",)


# --------------------------------------------------------------------------
# HOLD causes beyond a new red.
# --------------------------------------------------------------------------


def test_a_moved_estate_position_is_a_hold_even_when_every_test_is_unchanged() -> None:
    """Zero movement is the pass condition: a Fluree ledger is append-only, so an
    accidental write can never be removed."""
    candidate = copy.deepcopy(BASE)
    candidate["estate"]["after"]["fluree/curated"]["position"]["ledger_positions"]["fibo-v2:main"] = 5297
    verdict = classify(BASE, candidate)
    assert verdict.state == HOLD
    assert verdict.moved_stores == ("fluree/curated",)
    assert ReasonCode.ESTATE_POSITION_MOVED in verdict.reason_codes


def test_a_base_red_node_absent_from_the_candidate_is_a_hold_not_a_repair() -> None:
    """A red deleted rather than fixed reads as a pass to every count. `D-IMPL-358`
    ruling 7: *"Do not mass-edit examples to manufacture a green estate run."*"""
    candidate = bundle(
        {NODE % (4, "a"): "passed", NODE % (5, "a"): "error", NODE % (5, "b"): "passed"}
    )
    verdict = classify(BASE, candidate)
    assert verdict.state == HOLD
    assert verdict.vanished == (NODE % (4, "b"),)
    assert ReasonCode.BASE_RED_VANISHED in verdict.reason_codes


def test_a_node_that_passed_at_base_and_now_skips_is_a_hold() -> None:
    """Turning a passing test into a skip is the other way to manufacture green."""
    candidate = bundle(
        {
            NODE % (4, "a"): "skipped",
            NODE % (4, "b"): "failed",
            NODE % (5, "a"): "error",
            NODE % (5, "b"): "passed",
        }
    )
    verdict = classify(BASE, candidate)
    assert verdict.state == HOLD
    assert verdict.coverage_lost == (NODE % (4, "a"),)
    assert ReasonCode.COVERAGE_LOST in verdict.reason_codes


def test_a_red_node_whose_outcome_kind_changed_is_reported_without_being_a_new_red() -> None:
    """failed -> error on the same node id is a different fact, and neither an
    aggregate nor a bare set difference shows it."""
    candidate = bundle(
        {
            NODE % (4, "a"): "passed",
            NODE % (4, "b"): "error",   # was failed
            NODE % (5, "a"): "error",
            NODE % (5, "b"): "passed",
        }
    )
    verdict = classify(BASE, candidate)
    assert verdict.outcome_changed == (NODE % (4, "b"),)
    assert verdict.new_red == ()
    assert verdict.state == PASS


# --------------------------------------------------------------------------
# The distinctions that must not collapse.
# --------------------------------------------------------------------------


def test_an_expected_failure_is_a_declared_known_red_and_not_a_new_red() -> None:
    """`D-IMPL-261` permits quarantining a known gap as an expected failure, so the
    xfail set is this repository's in-code known-red ledger. Counting it red would
    turn every quarantined gap into a new red on the first census; folding it into
    passed or skipped would hide it."""
    candidate = bundle(
        {
            NODE % (4, "a"): "passed",
            NODE % (4, "b"): "failed",
            NODE % (5, "a"): "error",
            NODE % (5, "b"): "xfailed",
        }
    )
    verdict = classify(BASE, candidate)
    assert verdict.state == PASS, verdict.reasons
    assert verdict.new_red == ()
    assert verdict.declared_known_red == (NODE % (5, "b"),)


def test_skip_xfail_and_xpass_remain_three_distinct_outcomes() -> None:
    candidate = bundle(
        {
            NODE % (4, "a"): "skipped",
            NODE % (4, "b"): "xfailed",
            NODE % (5, "a"): "xpassed",
            NODE % (5, "b"): "passed",
        }
    )
    verdict = classify(candidate, copy.deepcopy(candidate))
    assert verdict.skipped == (NODE % (4, "a"),)
    assert verdict.declared_known_red == (NODE % (4, "b"),)
    assert verdict.state == PASS


def test_the_rendered_report_names_the_codes_and_lists_rosters_in_full() -> None:
    """A count is not a roster: a right count with a wrong member audits clean
    forever, so the report prints members."""
    candidate = bundle(
        {
            NODE % (4, "a"): "passed",
            NODE % (4, "b"): "failed",
            NODE % (5, "a"): "error",
            NODE % (5, "b"): "failed",
        }
    )
    text = render(classify(BASE, candidate))
    assert "HOLD" in text
    assert ReasonCode.NEW_RED in text
    assert NODE % (5, "b") in text


def test_the_machine_readable_verdict_round_trips_every_roster() -> None:
    candidate = bundle({NODE % (4, "a"): "failed"})
    payload = classify(BASE, candidate).as_dict()
    assert payload["state"] in (PASS, HOLD, INDETERMINATE)
    assert isinstance(payload["reason_codes"], list)
    assert set(payload["rosters"]) == {
        "new_red", "base_existing_red", "recovered", "vanished", "coverage_lost",
        "outcome_changed", "declared_known_red", "skipped", "moved_stores",
    }
