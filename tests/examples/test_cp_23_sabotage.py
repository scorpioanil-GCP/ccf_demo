"""Positive controls: every declared gate proved able to go RED.

A gate that cannot redden is a proof-machinery defect, not a passing gate
(`UBO-F-05` at rung 15; `ABS-F-07`/`ABS-F-08` at rung 16). Each test feeds the
declared gate a candidate violating exactly one invariant, or exercises a
mechanism the estate alone cannot discriminate.

Four of the nineteen gates of `CP-SPEC-023` §G.1 execute here, plus the two
positive controls the estate cannot supply by itself.
"""

from __future__ import annotations

import copy
import pathlib
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import pytest

from tests.examples.test_cp_23_portfolio import (  # noqa: F401
    COVERAGE,
    CREDIT,
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
    root = tmp_path_factory.mktemp("cp23sab")
    return dict(answer(modules, root / "credit", principal=CREDIT,
                       intent="credit-review").payload)


def _gate(modules: dict[str, Any], payload: Mapping[str, Any]) -> str | None:
    return modules["deployment"].portfolio_gate(candidate=_Candidate(payload))


def test_the_gate_admits_the_honest_payload(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """The control for every control: unsabotaged, the gate says nothing."""
    assert _gate(modules, honest) is None


# =========================================================================
# PEW-G02 / PEW-G03 — containment and population grain
# =========================================================================


def test_the_gate_refuses_a_member_that_does_not_declare_membership(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Declared product gate `PEW-G02` (`CP-SPEC-023` §G.1)."""
    payload = copy.deepcopy(dict(honest))
    payload["population"][0]["in_book"] = "false"
    refusal = _gate(modules, payload)
    assert refusal is not None and "PEW-G02" in refusal, refusal


def test_the_gate_refuses_a_member_count_that_disagrees_with_the_population(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Declared product gate `PEW-G03` (`CP-SPEC-023` §G.1)."""
    payload = copy.deepcopy(dict(honest))
    payload["member_count"] = str(int(payload["member_count"]) + 1)
    refusal = _gate(modules, payload)
    assert refusal is not None and "PEW-G03" in refusal, refusal


# =========================================================================
# PEW-G09 — per-class freshness, and no book-wide timestamp
# =========================================================================


def test_the_gate_refuses_a_single_portfolio_freshness_timestamp(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """One number would let a 12-day class hide a 53-day one.

    THE SHAPE CHECK CATCHES THIS FIRST, and that is worth stating rather than
    hiding: adding any key changes the payload's member set, so `PEW-G07`
    refuses before the freshness limb is reached. The `PEW-G09` limb that
    names `portfolio_freshness_at` is therefore DEFENCE IN DEPTH behind a
    stricter check — it can only fire if the member set were ever widened to
    admit such a key (`PEW-F-03`). The reachable `PEW-G09` sabotage is the
    empty-rows one below.

    Declared product gate `PEW-G09` (`CP-SPEC-023` §C.2, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["portfolio_freshness_at"] = "2026-08-13T00:00:00+00:00"
    refusal = _gate(modules, payload)
    assert refusal is not None, "a book-wide freshness timestamp must not be servable"
    assert "PEW-G07" in refusal or "PEW-G09" in refusal, refusal


def test_the_gate_refuses_freshness_with_no_per_class_rows(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Declared product gate `PEW-G09` (`CP-SPEC-023` §C.2)."""
    payload = copy.deepcopy(dict(honest))
    payload["signal_freshness_by_class"] = []
    refusal = _gate(modules, payload)
    assert refusal is not None and "PEW-G09" in refusal, refusal


# =========================================================================
# PEW-G12 — `Q1`, and it must stay understandable BY FACTOR
# =========================================================================


def test_the_gate_refuses_a_portfolio_debt_law_other_than_the_ruled_one(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """`max(member D_c)` is exactly what the ruling forbids.

    Declared product gate `PEW-G12` (`CP-SPEC-023` §F.4 `Q1`, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["population_debt"]["rule"] = "max-member-debt"
    refusal = _gate(modules, payload)
    assert refusal is not None and "PEW-G12" in refusal, refusal


def test_the_gate_refuses_population_debt_that_names_no_weak_member(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """A weak member must not disappear behind a stronger aggregate.

    Declared product gate `PEW-G12` (`CP-SPEC-023` §F.4 `Q1`, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["population_debt"]["weakest_by_factor"] = {}
    refusal = _gate(modules, payload)
    assert refusal is not None and "PEW-G12" in refusal, refusal


# =========================================================================
# PEW-G17 — the covenant member is never dropped for being quiet
# =========================================================================


def test_the_gate_refuses_a_dropped_covenant_member(
    modules: dict[str, Any], honest: Mapping[str, Any],
) -> None:
    """Zero active pressure is not absent history.

    Declared product gate `PEW-G17` (`CP-SPEC-023` §C.3 trap 2, ruled 2026-09-21).
    """
    payload = copy.deepcopy(dict(honest))
    payload["covenant_history"] = None
    refusal = _gate(modules, payload)
    assert refusal is not None and "PEW-G17" in refusal, refusal


# =========================================================================
# THE TWO CONTROLS THE ESTATE CANNOT SUPPLY
# =========================================================================


def test_the_ruled_law_differs_from_max_member_debt_in_general(
    modules: dict[str, Any],
) -> None:
    """POSITIVE CONTROL for `PEW-G12`, and the reason it is needed.

    On THIS book the two laws happen to agree, because the member weakest on
    freshness also sits at the completeness floor — so the estate alone cannot
    show that the ruled law carries information `max(member D_c)` loses
    (`PEW-F-01`). Three members each weak on a DIFFERENT factor show it.

    Declared product gate `PEW-G12` (`CP-SPEC-023` §F.4 `Q1`).
    """
    from ccf.halflife.debt import DebtFactors, compose_debt_factors, context_debt

    whole = DebtFactors(freshness=Decimal("1.0"), completeness=Decimal("1.0"),
                        semantic_consistency=Decimal("1.0"))
    members = [
        DebtFactors(freshness=Decimal("0.40"), completeness=Decimal("1.00"),
                    semantic_consistency=Decimal("1.00")),
        DebtFactors(freshness=Decimal("1.00"), completeness=Decimal("0.50"),
                    semantic_consistency=Decimal("1.00")),
        DebtFactors(freshness=Decimal("1.00"), completeness=Decimal("1.00"),
                    semantic_consistency=Decimal("0.60")),
    ]
    composed = compose_debt_factors(whole, members)
    assert (composed.freshness, composed.completeness, composed.semantic_consistency) == (
        Decimal("0.40"), Decimal("0.50"), Decimal("0.60")
    ), "the SDK's rule is per-factor minimum across the population"
    assert context_debt(composed) > max(context_debt(m) for m in members), (
        "the ruled law carries all three impairments; max(member D_c) carries none faithfully"
    )


def test_canonicalization_is_the_deployments_and_is_order_insensitive(
    modules: dict[str, Any],
) -> None:
    """POSITIVE CONTROL for `PEW-G05`: the function itself, not just the address.

    Declared product gate `PEW-G05` (`CP-SPEC-023` §F.4 `Q2`, ruled 2026-09-21).
    """
    canonical = modules["acquisition"].canonical_members
    assert canonical(["C", "B", "A"]) == canonical(["A", "B", "C"]) == ("A", "B", "C")
    assert canonical(["A", "A", "B"]) == ("A", "B"), "a set has no duplicates"
    assert canonical([]) == () and canonical(None) == ()
    # And a DIFFERENT membership still differs — the converse limb.
    assert canonical(["A", "B", "D"]) != canonical(["A", "B", "C"])
