"""Positive controls: every declared gate proved able to go RED.

A gate that cannot redden is a proof-machinery defect, not a passing gate
(`UBO-F-05`, rung 15). Each test here feeds the declared gate a candidate that
violates exactly one invariant and asserts the gate names it — so a later edit
that quietly removes a limb turns these red rather than leaving a green gate
asserting nothing.

The sabotage is IN THE TEST and in process: nothing here touches the estate
beyond one honest serve to borrow a real payload from.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Mapping
from typing import Any

import pytest

from tests.examples.test_cp_16_surveillance import (  # noqa: F401
    DESK,
    QUESTION,
    RISK,
    Answer,
    answer,
    estate,
    modules,
)

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

UNANCHORED: str = QUESTION["unanchored_trigger_id"]


class _Candidate:
    """The smallest thing the declared gate reads: something with a payload."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload


@pytest.fixture(scope="module")
def honest(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Any]:
    """One real served payload, to sabotage copies of."""
    root = tmp_path_factory.mktemp("cp16sab")
    reply = answer(modules, root / "loan", principal=DESK, granularity="loan", loan_sample=20)
    return dict(reply.payload)


def _gate(modules: dict[str, Any], payload: Mapping[str, Any]) -> str | None:
    return modules["deployment"].surveillance_gate(candidate=_Candidate(payload))


def test_the_gate_admits_the_honest_payload(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """The control for every control: unsabotaged, the gate says nothing.

    Without this, a gate that refused everything would pass every test below.
    """
    assert _gate(modules, honest) is None


# =========================================================================
# ABS-G07 — Route B, both directions
# =========================================================================


def test_the_gate_refuses_an_unanchored_threshold_carrying_anchor_fields(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Nothing may imply a prospectus passage exists.

    Declared product gate `ABS-G07` (`CP-SPEC-016` §F.4.0, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    for row in payload["triggers"]:
        if row["anchored"] == "false":
            row["anchor_passage_id"] = ""
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G07" in refusal, refusal
    assert "blank" in refusal or "stated" in refusal


def test_the_gate_refuses_an_unnamed_unanchored_threshold(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Serving one unanchored and naming none is the failure Route B forbids.

    Declared product gate `ABS-G07` (`CP-SPEC-016` §F.4.0, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    assert payload["unanchored_thresholds"], "the estate must have one to remove"
    payload["unanchored_thresholds"] = []
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G07" in refusal, refusal


def test_the_gate_refuses_a_public_threshold_with_no_anchor(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Anchoring invariant ONE, independently.

    Declared product gate `ABS-G06` (`CP-SPEC-016` §F.4.0, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    for row in payload["triggers"]:
        if row["source_classification"] == "public":
            row["anchored"] = "false"
            for key in ("anchor_id", "anchor_text", "anchor_passage_id",
                        "anchor_document_id", "anchor_sha256"):
                row.pop(key, None)
            break
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G06" in refusal, refusal


def test_the_gate_refuses_an_anchor_that_cannot_be_rehashed(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """An anchor with no stored hash is not evidence.

    Declared product gate `ABS-G06` (`CP-SPEC-016` §F.4.0, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    for row in payload["triggers"]:
        if row["anchored"] == "true":
            row["anchor_sha256"] = ""
            break
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G06" in refusal, refusal


# =========================================================================
# ABS-G10 / ABS-G09 — the ceiling, stated and enforced
# =========================================================================


def test_the_gate_refuses_a_stated_ceiling_that_is_not_the_resolved_one(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """THE anti-vacuity control for `ABS-G10`.

    Declared product gate `ABS-G10` (`CP-SPEC-016` §F.4.2, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    payload["granularity_ceiling"] = "deal"
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G10" in refusal, refusal


def test_the_gate_refuses_a_granularity_served_above_its_ceiling(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Serving finer than the ceiling allows is refused even if it got that far.

    Declared product gate `ABS-G09` (`CP-SPEC-016` §B.3, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    payload["perspective"] = RISK[1]           # ceiling `cohort`
    payload["granularity_ceiling"] = "cohort"  # stated honestly for that role
    refusal = _gate(modules, payload)          # but `loan` members are still served
    assert refusal is not None, "a loan-granularity payload under a cohort ceiling must refuse"
    assert "ABS-G09" in refusal or "ABS-G12" in refusal, refusal


# =========================================================================
# ABS-G13 / ABS-G15 — cost honesty
# =========================================================================


def test_the_gate_refuses_a_payload_that_materialized_the_population(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """LOAD-BEARING, and provably reddenable.

    Declared product gate `ABS-G13` (`CP-SPEC-016` §0.2, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    payload["assembly_cost"]["records_materialized"] = "1322453"
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G13" in refusal, refusal


def test_the_gate_refuses_cost_reported_as_time(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Time is never a cost statement on this estate.

    Declared product gate `ABS-G15` (`CP-SPEC-016` §A.2, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    payload["assembly_cost"]["elapsed_ms"] = "40.472"
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G15" in refusal, refusal


def test_the_gate_refuses_a_cost_band_that_contradicts_the_granularity(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """The only step that changes cost materially is loan-or-not.

    Declared product gate `ABS-G15` (`CP-SPEC-016` §A.2, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    payload["assembly_cost"]["cost_band"] = "aggregate-scale"
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G15" in refusal, refusal


def test_the_gate_refuses_a_payload_with_no_cost_at_all(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """What a question cost is part of the answer.

    Declared product gate `ABS-G15` (`CP-SPEC-016` §A.2, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    payload["assembly_cost"] = {}
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G15" in refusal, refusal


# =========================================================================
# ABS-G16 — a finding is not a zero
# =========================================================================


def test_the_gate_refuses_an_uncomputable_proximity_with_no_reason(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """A distance that is absent must say why, or it reads as breached.

    Declared product gate `ABS-G16` (`CP-SPEC-016` §C.3 trap 3, §G.1).
    """
    payload = copy.deepcopy(dict(honest))
    for row in payload["trigger_proximity"]:
        row["distance"] = None
        row.pop("uncomputable_reason", None)
    refusal = _gate(modules, payload)
    assert refusal is not None and "ABS-G16" in refusal, refusal
