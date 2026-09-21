"""Replay: the served determination is reconstructible from its record.

One of the twenty-one declared gates of `CP-SPEC-016` §G.1 executes here —
`ABS-G21` — plus the identity property the ladder holds everywhere: the same
question hashes to the same bytes.

**Reads the curated estate, seeds nothing** (CLAUDE.md §9).
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
from ccf.contracts.canonical import content_hash

from tests.examples.test_cp_16_surveillance import (  # noqa: F401
    AFTER_AMENDMENT,
    BEFORE_AMENDMENT,
    DESK,
    RISK,
    Answer,
    answer,
    estate,
    modules,
)

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]


def test_the_determination_replays_from_its_record(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Every input the answer rested on is RESOLVED from the record, not re-derived.

    Declared product gate `ABS-G21` (`CP-SPEC-016` §D.5, §G.1).
    """
    reply = answer(modules, tmp_path, principal=DESK, granularity="cohort")
    record = reply.record

    # Dimension 5 carries the executed operator plan, in order.
    plan = record.content_generation_path.operator_plan
    assert plan, "the executed plan is recorded"
    assert set(plan) == set(reply.product.lineage.operators_invoked), (
        "the ordered plan and the served operator set name the same operators"
    )

    # Dimension 2 is a SUPERSET of the product's own lineage — the record knows
    # at least everything the product claims.
    assert reply.product.lineage.operators_invoked <= set(plan)

    # The decision instant and the granularity that shaped the answer are both
    # resolvable from the determination rather than from today's defaults —
    # dimension 5 carries the effective request the answer was built from.
    parameters = record.content_generation_path.request.parameters
    assert parameters["as_of"] == reply.payload["as_of"]
    assert parameters.get("granularity") == reply.payload["requested_granularity"]

    # The role that chose the ceiling is dimension 4, and the product's stated
    # ceiling belongs to that role.
    assert record.perspective_conditioning.role == reply.role
    assert reply.payload["granularity_ceiling"], "the bound is on the served product"

    # The product the record describes is the product that was served.
    assert record.content_generation_path.product_content_address == content_hash(reply.product)


def test_the_same_question_hashes_to_the_same_bytes(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Content addressing: identical questions, identical address.

    Declared product gate `ABS-G21` (`CP-SPEC-016` §D.5, §G.1).
    """
    first = answer(modules, tmp_path / "a", principal=DESK, granularity="cohort")
    second = answer(modules, tmp_path / "b", principal=DESK, granularity="cohort")
    assert content_hash(first.product) == content_hash(second.product), (
        "the same governed question must hash to the same bytes"
    )


def test_a_different_instant_is_a_different_determination(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The as-of contrast is visible in the ADDRESS, not only in the reading.

    Declared product gate `ABS-G21` (`CP-SPEC-016` §D.5, §G.1).
    """
    after = answer(modules, tmp_path / "after", principal=DESK, as_of=AFTER_AMENDMENT)
    before = answer(modules, tmp_path / "before", principal=DESK, as_of=BEFORE_AMENDMENT)
    assert content_hash(after.product) != content_hash(before.product), (
        "two instants that put different trigger definitions in force are different products"
    )


def test_a_different_role_is_a_different_determination(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Perspective is a dimension of the product, and it reaches the address.

    Declared product gate `ABS-G21` (`CP-SPEC-016` §D.5, §G.1).
    """
    desk = answer(modules, tmp_path / "desk", principal=DESK, granularity="cohort")
    risk = answer(modules, tmp_path / "risk", principal=RISK, granularity="cohort")
    assert desk.payload["granularity_ceiling"] != risk.payload["granularity_ceiling"]
    assert content_hash(desk.product) != content_hash(risk.product), (
        "two roles with different ceilings are different determinations"
    )
