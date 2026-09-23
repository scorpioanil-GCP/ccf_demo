"""Positive controls: every declared gate proved able to go RED.

A gate that cannot redden is a proof-machinery defect, not a passing gate
(`UBO-F-05`, `ABS-F-07`, `PEW-F-05`, `WIF-F-05`). And the durable rule those
three findings produced, applied throughout this file:

    A SABOTAGE MUST MUTATE THE CLAIM THE GATE ASSERTS, not merely one field
    the claim happens to mention.

Five of the twenty-one gates of `CP-SPEC-021` §G.1 execute here against the
declared gate directly, plus the door crossing.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Mapping
from typing import Any

import pytest

from tests.examples import tree_import
from ccf.contracts.canonical import content_hash
from ccf.projection.plan import Perspective
from ccf.replay.serve import ServedProduct

from tests.examples.test_cp_21_large_exposure import (  # noqa: F401
    ASKED_AT,
    AS_OF,
    BREACHING,
    CREDIT_OFFICER,
    EXAMINER,
    EXAMPLE,
    FRESHNESS,
    INTENT,
    Answer,
    answer,
    estate,
    modules,
)

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]


class _Candidate:
    """The gate reads `payload` and `lineage`; both are carried here."""

    def __init__(self, payload: Mapping[str, Any], lineage: Any) -> None:
        self.payload = payload
        self.lineage = lineage


@pytest.fixture(scope="module")
def honest(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Any:
    root = tmp_path_factory.mktemp("cp21sab")
    return answer(modules, root / "officer", anchor=BREACHING["anchor"],
                  proposal=BREACHING["proposal"])


@pytest.fixture(scope="module")
def examiner(estate: None, modules: dict[str, Any], tmp_path_factory: Any) -> Any:
    root = tmp_path_factory.mktemp("cp21sabex")
    return answer(modules, root / "examiner", principal=EXAMINER,
                  intent="supervisory-request", anchor=BREACHING["anchor"])


def _gate(modules: dict[str, Any], served: Any, payload: Mapping[str, Any]) -> str | None:
    return modules["deployment"].large_exposure_gate(
        candidate=_Candidate(payload, served.product.lineage))


def test_the_gate_admits_the_honest_payload(modules: dict[str, Any], honest: Any) -> None:
    """The control for every control: unsabotaged, the gate says nothing."""
    assert _gate(modules, honest, dict(honest.payload)) is None


def test_the_gate_admits_the_honest_examiner_payload(
    modules: dict[str, Any], examiner: Any,
) -> None:
    """The examiner rendering carries the most, so it is controlled separately."""
    assert _gate(modules, examiner, dict(examiner.payload)) is None


# =========================================================================
# LEX-G02 — the group is DERIVED
# =========================================================================


def test_the_gate_refuses_a_group_that_does_not_declare_itself_derived(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G02` (`CP-SPEC-021` §G.1)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["group"]["derived"] = "false"
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G02" in refusal, refusal


# =========================================================================
# LEX-G07 — unit provenance survives normalization
# =========================================================================


def test_the_gate_refuses_a_capital_base_that_lost_its_raw_figure(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G07` (`Q2`, ruled 2026-09-21)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["capital_base"]["raw_value"] = ""
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G07" in refusal, refusal


def test_the_gate_refuses_a_capital_base_reporting_one_unit_twice(
    modules: dict[str, Any], honest: Any,
) -> None:
    """THE CLAIM IS THAT NORMALIZATION HAPPENED, and this mutates it.

    Declared product gate `LEX-G07`. Reporting the source unit as the
    normalized unit is exactly what an implementation that never scaled would
    serve.
    """
    payload = copy.deepcopy(dict(honest.payload))
    payload["capital_base"]["normalized_unit"] = payload["capital_base"]["source_unit"]
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G07" in refusal, refusal


# =========================================================================
# LEX-G06 — the dimensional negative control
# =========================================================================


def test_the_gate_refuses_a_percentage_limit_computed_on_the_raw_base(
    modules: dict[str, Any], honest: Any,
) -> None:
    """THE UNNORMALIZED IMPLEMENTATION, reproduced exactly.

    Declared product gate `LEX-G06` (`CP-SPEC-021` §C.3 trap 1). The sabotage
    does not blank a field — it recomputes the limits the way a product that
    read thousands as dollars would, which is the claim the gate asserts.
    """
    payload = copy.deepcopy(dict(honest.payload))
    from decimal import Decimal  # noqa: PLC0415

    raw = Decimal(str(payload["capital_base"]["raw_value"]))
    for row in payload["limits"]:
        if row["limit_pct_of_capital"]:
            row["limit_value"] = str(raw * Decimal(row["limit_pct_of_capital"]) / Decimal(100))
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G06" in refusal, refusal


# =========================================================================
# LEX-G08 / LEX-G09 / LEX-G10 — the regime and its authority
# =========================================================================


def test_the_gate_refuses_a_provision_that_does_not_resolve(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G08` (ruled 2026-09-21)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["regime_in_force"]["provisions"][0]["quoted_text"] = ""
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G08" in refusal, refusal


def test_the_gate_refuses_a_limit_whose_rule_form_is_assumed(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G09` (ruled 2026-09-21)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["regime_in_force"]["rule_form"] = "percentage"
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G09" in refusal, refusal


def test_the_gate_refuses_a_determination_missing_one_of_the_five_facts(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G10` (`CP-SPEC-021` §G.1)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["regime_in_force"]["authority"] = ""
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G10" in refusal, refusal


# =========================================================================
# LEX-G11 / LEX-G12 / LEX-G13 — the limits
# =========================================================================


def test_the_gate_refuses_a_payload_that_dropped_one_authority(
    modules: dict[str, Any], honest: Any,
) -> None:
    """SILENTLY CHOOSING IS THE FAILURE, and this reproduces it.

    Declared product gate `LEX-G11` (ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest.payload))
    keep = payload["limits"][0]["authority"]
    payload["limits"] = [row for row in payload["limits"] if row["authority"] == keep]
    payload["limit_authority_conflict"] = None
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G11" in refusal, refusal


def test_the_gate_refuses_a_conflict_resolved_without_naming_the_rule(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G11` (ruled 2026-09-21)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["limit_authority_conflict"]["selected_by_rule"] = ""
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G11" in refusal, refusal


def test_the_gate_refuses_an_evaluation_that_names_no_binding_limit(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G12` (`CP-SPEC-021` §G.1)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["evaluation"]["binding_limit_id"] = ""
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G12" in refusal, refusal


def test_the_gate_refuses_a_limit_served_without_its_counting_rule(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G13` (`CP-SPEC-021` §G.1)."""
    payload = copy.deepcopy(dict(honest.payload))
    for row in payload["limits"]:
        if row["authority"] == "relational-limit-register":
            row["counts_undrawn"] = ""
            break
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G13" in refusal, refusal


# =========================================================================
# LEX-G14 — the asymmetry is never fused
# =========================================================================


def test_the_gate_refuses_a_fused_freshness_key(
    modules: dict[str, Any], honest: Any,
) -> None:
    """COLLAPSING TWO CLOCKS INTO ONE is the failure this refuses.

    Declared product gate `LEX-G14` (ruled 2026-09-21).

    THE KEY IS MINTED NESTED, DELIBERATELY. At top level the declared-shape
    check refuses any undeclared member first, so a top-level sabotage reddened
    a DIFFERENT limb and left this one dead — measured, and recorded as
    `LEX-F-05`. Inside `freshness_asymmetry` is both the reachable place and
    the likelier real-world shape.
    """
    payload = copy.deepcopy(dict(honest.payload))
    payload["freshness_asymmetry"]["combined_freshness_at"] = payload["as_of"]
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G14" in refusal, refusal


def test_the_gate_refuses_an_asymmetry_declared_resolved(
    modules: dict[str, Any], honest: Any,
) -> None:
    """THE CLAIM IS THAT THE GAP IS DISCLOSED AND LEFT OPEN.

    Declared product gate `LEX-G14` (ruled 2026-09-21). Declaring it resolved
    is the assertion the gate exists to refuse, and it mutates the claim rather
    than a field the claim mentions.
    """
    payload = copy.deepcopy(dict(honest.payload))
    payload["freshness_asymmetry"]["resolved"] = "true"
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G14" in refusal, refusal


def test_the_gate_refuses_a_ratio_carrying_someone_else_s_capital_date(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G14` (ruled 2026-09-21)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["freshness_asymmetry"]["capital_report_date"] = "2026-06-30"
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G14" in refusal, refusal


def test_the_gate_refuses_a_capital_base_that_lost_its_own_date(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G14` (ruled 2026-09-21)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["capital_base"]["report_date"] = ""
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G14" in refusal, refusal


# =========================================================================
# LEX-G16 / LEX-G17 / LEX-G19 — the proposal
# =========================================================================


def test_the_gate_refuses_a_proposal_served_only_one_way(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G16` (`CP-SPEC-021` §G.1)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["evaluation"].pop("with_proposal")
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G16" in refusal, refusal


def test_the_gate_refuses_a_proposal_labelled_as_evidence(
    modules: dict[str, Any], honest: Any,
) -> None:
    """Declared product gate `LEX-G17` (rung 24's `Q1`, carried)."""
    payload = copy.deepcopy(dict(honest.payload))
    payload["evaluation"]["proposal_basis"] = "observed"
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G17" in refusal, refusal


def test_the_gate_refuses_debt_that_names_a_proposal_input(
    modules: dict[str, Any], honest: Any,
) -> None:
    """A HYPOTHETICAL IS NOT EVIDENCE.

    Declared product gate `LEX-G19` (rung 24's governing rule, carried).
    """
    payload = copy.deepcopy(dict(honest.payload))
    payload["population_debt"]["proposal_adjustment"] = "0.10"
    refusal = _gate(modules, honest, payload)
    assert refusal is not None and "LEX-G19" in refusal, refusal


# =========================================================================
# LEX-G18 / LEX-G21 — the renderings and the replay anchor
# =========================================================================


def test_the_gate_refuses_an_examiner_rendering_without_its_methodology(
    modules: dict[str, Any], examiner: Any,
) -> None:
    """Declared product gate `LEX-G18` (`CP-SPEC-021` §G.1)."""
    payload = copy.deepcopy(dict(examiner.payload))
    payload["methodology"] = {}
    refusal = _gate(modules, examiner, payload)
    assert refusal is not None and "LEX-G18" in refusal, refusal


def test_the_gate_refuses_a_minted_ledger_point(
    modules: dict[str, Any], examiner: Any,
) -> None:
    """AN INVENTED `t` MAKES REPLAY LOOK RECONSTRUCTIBLE WHEN IT IS NOT.

    Declared product gate `LEX-G21` (`LEX-F-04`, measured 2026-09-21). The
    sabotage is the exact shape the finding warns about: a plausible ledger
    point beside a disclosure saying none resolved.
    """
    payload = copy.deepcopy(dict(examiner.payload))
    payload["replay_attribution"]["ledger_t"] = "5296"
    refusal = _gate(modules, examiner, payload)
    assert refusal is not None and "LEX-G21" in refusal, refusal


def test_the_gate_refuses_a_replay_anchor_missing_its_instant(
    modules: dict[str, Any], examiner: Any,
) -> None:
    """Declared product gate `LEX-G21` (`CP-SPEC-021` §G.1)."""
    payload = copy.deepcopy(dict(examiner.payload))
    payload["replay_attribution"]["determination_instant"] = ""
    refusal = _gate(modules, examiner, payload)
    assert refusal is not None and "LEX-G21" in refusal, refusal


# =========================================================================
# THE DOOR — the closed proposal object crosses a shipped door unchanged
# =========================================================================


def test_the_proposal_crosses_the_door_unchanged(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The determination reached through the standard door is the same product.

    Declared product gate `LEX-G21` (`CP-SPEC-021` §G.1). The door's own
    resolver is exercised with the same question, and the product it returns
    must be byte-identical to the in-process one — a closed object that lost a
    member or changed a magnitude on the way through would hash differently.
    """
    # `LEX-F-11`, and the pattern now has ONE home. This block used to evict
    # every `server.*` entry and verify the result by hand; the helper does
    # exactly that, and routing all four door importers through it is what
    # stopped the fourth from being written without a guard at all
    # (`test_cp_24_sabotage`, measured 2026-09-22).
    door_module = tree_import.door_module_of(EXAMPLE)

    deployment, produce = modules["deployment"], modules["produce"]
    inprocess = answer(modules, tmp_path / "direct", anchor=BREACHING["anchor"],
                       proposal=BREACHING["proposal"])

    with produce.product(tmp_path / "door") as opened:
        door = door_module.open_large_exposure_door(opened)
        assert door is not None, "the door opened"
        asked = produce.large_exposure_question(
            opened, anchor=BREACHING["anchor"], asked_at=ASKED_AT, intent=INTENT,
            freshness=FRESHNESS,
            **{deployment.AS_OF: AS_OF, deployment.PROPOSAL: dict(BREACHING["proposal"])},
        )
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=CREDIT_OFFICER[0],
                                           role=CREDIT_OFFICER[1]))
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        assert content_hash(outcome.product) == inprocess.address, (
            "the proposal did not cross the door unchanged"
        )
        recorded = opened.record_of(outcome).content_generation_path.request.parameters["proposal"]
        assert int(recorded["commitment_usd"]) == int(BREACHING["proposal"]["commitment_usd"])
