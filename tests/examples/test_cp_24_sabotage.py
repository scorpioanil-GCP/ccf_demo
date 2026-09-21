"""Positive controls: every declared gate proved able to go RED.

A gate that cannot redden is a proof-machinery defect, not a passing gate
(`UBO-F-05`, `ABS-F-07`, `PEW-F-05`). Four of the seventeen gates of
`CP-SPEC-024` §G.1 execute here, plus the door crossing.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Mapping
from typing import Any

import pytest
from ccf.contracts.canonical import content_hash
from ccf.projection.plan import Perspective
from ccf.replay.serve import ServedProduct

from tests.examples.test_cp_24_whatif import (  # noqa: F401
    ASKED_AT,
    AS_OF,
    BOOK,
    COVERAGE,
    CREDIT,
    EXAMPLE,
    FRESHNESS,
    SCENARIO,
    Answer,
    answer,
    estate,
    modules,
)

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]


class _Candidate:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload


@pytest.fixture(scope="module")
def honest(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Mapping[str, Any]:
    root = tmp_path_factory.mktemp("cp24sab")
    return dict(answer(modules, root / "credit", principal=CREDIT,
                       intent="credit-review").payload)


def _gate(modules: dict[str, Any], payload: Mapping[str, Any]) -> str | None:
    return modules["deployment"].what_if_gate(candidate=_Candidate(payload))


def test_the_gate_admits_the_honest_payload(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """The control for every control: unsabotaged, the gate says nothing."""
    assert _gate(modules, honest) is None


# =========================================================================
# WIF-G07 — the labelling
# =========================================================================


def test_the_gate_refuses_an_unlabelled_derived_measure(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Declared product gate `WIF-G07` (`CP-SPEC-024` §D.3)."""
    payload = copy.deepcopy(dict(honest))
    payload["collateral_impact"][0]["basis"] = "observed"
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G07" in refusal, refusal


def test_the_gate_refuses_a_derived_measure_naming_no_assumption(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Declared product gate `WIF-G07` (`CP-SPEC-024` §D.3)."""
    payload = copy.deepcopy(dict(honest))
    payload["interest_impact"][0]["from_assumption"] = ""
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G07" in refusal, refusal


def test_the_gate_refuses_a_scenario_that_claims_to_be_evidence(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """The assumptions must say they are assumptions.

    Declared product gate `WIF-G07` (`CP-SPEC-024` §D.3, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["scenario"]["basis"] = "observed"
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G07" in refusal, refusal


# =========================================================================
# WIF-G08 / WIF-G11 / WIF-G12 — observed beside derived, and stale stays stale
# =========================================================================


def test_the_gate_refuses_a_stressed_figure_served_alone(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Declared product gate `WIF-G08` (`CP-SPEC-024` §D.3)."""
    payload = copy.deepcopy(dict(honest))
    payload["interest_impact"][0]["observed_rate_pct"] = ""
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G08" in refusal, refusal


def test_the_gate_refuses_a_derived_figure_that_lost_its_observation_age(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """LOAD-BEARING: a scenario does not refresh its factual inputs.

    Declared product gate `WIF-G11` (`CP-SPEC-024` §C.3 trap 2, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["collateral_impact"][0]["observed_age_days"] = ""
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G11" in refusal, refusal


def test_the_gate_refuses_an_instant_moved_by_arithmetic(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Nothing is reset because a calculation ran.

    Declared product gate `WIF-G12` (`CP-SPEC-024` §C.3 trap 2, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["collateral_impact"][0]["valuation_instant_used"] = "2026-08-25"
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G12" in refusal, refusal


# =========================================================================
# WIF-G13 / WIF-G14 — the governing rule and the roll-up
# =========================================================================


def test_the_gate_refuses_debt_that_names_a_scenario_input(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Observed evidence determines debt; assumptions never do.

    Declared product gate `WIF-G13` (`CP-SPEC-024` §D.3, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["population_debt"]["scenario_adjustment"] = "0.10"
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G13" in refusal, refusal


def test_the_gate_refuses_a_rollup_that_names_no_members(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Declared product gate `WIF-G14` (`CP-SPEC-024` §B.2)."""
    payload = copy.deepcopy(dict(honest))
    payload["coverage_rollup"].pop("members")
    refusal = _gate(modules, payload)
    assert refusal is not None and "WIF-G14" in refusal, refusal


# =========================================================================
# WIF-G05 — the scenario crosses a DOOR
# =========================================================================


def test_the_scenario_crosses_the_door_unchanged(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The first CLOSED object parameter to cross a shipped door.

    The door's own resolver is exercised with the same question, and the
    product it returns must be byte-identical to the in-process one — a
    closed object that lost a member or changed a magnitude on the way through
    would produce a different address.

    Declared product gate `WIF-G05` (`CP-SPEC-024` §0.2b, §G.1).
    """
    sys_path = str(EXAMPLE)
    import sys  # noqa: PLC0415

    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from server import serve as door_module  # noqa: PLC0415

    deployment, produce = modules["deployment"], modules["produce"]
    inprocess = answer(modules, tmp_path / "direct", principal=COVERAGE)

    with produce.product(tmp_path / "door") as opened:
        door = door_module.open_book_door(opened)
        assert door is not None, "the door opened"
        # The door resolves the SAME governed question through the SDK's
        # resolver, with the scenario carried as a declared object parameter.
        asked = produce.book_question(
            opened, book=BOOK, asked_at=ASKED_AT, intent="stress-test",
            freshness=FRESHNESS, scenario=dict(SCENARIO),
            **{deployment.AS_OF: AS_OF},
        )
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=COVERAGE[0], role=COVERAGE[1]))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        assert content_hash(outcome.product) == inprocess.address, (
            "the scenario must cross the door unchanged"
        )
        # And the scenario really did reach the determination.
        recorded = opened.record_of(outcome).content_generation_path.request.parameters["scenario"]
        assert int(recorded["rate_shift_bp"]) == int(SCENARIO["rate_shift_bp"])
