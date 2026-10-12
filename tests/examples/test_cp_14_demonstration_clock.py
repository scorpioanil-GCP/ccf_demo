# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""CP-14 — the parent and its producers on ONE declared demonstration time (Dave, 2026-10-11).

Dave, 2026-10-11 20:19 MST, ruling 2, option (a), verbatim: *"Run the parent and its
five producers against the same explicitly declared demonstration time, 2026-09-07.
Keep this confined to the demonstration configuration; it is not permission for a
production caller to change the server's clock."*

cp-14 asks its five producers one dated question (2026-09-07T12:00Z). Three already
serve on that date in their own Control Plane: cp-03-canonical and cp-06-canonical
declare 2026-09-07T12:05Z, and frozen cp-05 (behind `door-cp-05`) declares
2026-09-07T12:00Z. The other two do not: cp-04-canonical serves on the real clock,
and cp-13-canonical declares 2026-09-13T00:05Z for its own spec-dated question. For
CP-14's call, each of those two is booted on a DEMONSTRATION CONFIGURATION committed
under `examples/cp-14-credit-memo-context/producer-demonstration/<tree>/` — the
producer's own two documents with only the clock declaration changed — through the
producer's own `run.py --door --config-root …`. The producers' own trees, default
questions and clocks are unchanged.

What is held, and why each part is needed:

1. **The copy is the producer, but for the clock** (no estate). A demonstration
   configuration that drifted from its producer would demonstrate a different
   producer. Each `ccf_environment.yaml` is byte-identical; each `ccf_config.yaml`
   equals the producer's once both clock declarations are removed; the one block
   that differs declares exactly cp-14's own serve instant; the producers' own
   declarations are what they were.
2. **Both outcomes, on the live estate.** The same diagnostic question, with the
   family and covenant producers booted on their OWN trees, is refused by each
   child's own door `asked-at-outside-temporal-bound`; booted on the demonstration
   configurations, both children are ADMITTED. Nothing else differs between the two
   asks.

**Reads the estate, seeds nothing.**
"""

from __future__ import annotations

import os
import pathlib
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
import yaml

from tests.examples.test_cp_03_canonical_cross_deployment import DEV_TOKEN
from tests.examples.test_cp_14_first_slice import (  # noqa: F401
    BGC, BGC_FACILITY, CHILD_CLASSES, CP14_INSTANT, EXAMPLE, UNREACHABLE, modules,
)
from tests.examples.test_cp_14_fourth_slice import (
    COVENANT_DEMONSTRATION_ROOT, _record_of, covenant_producer,
)
from tests.examples.test_cp_14_second_slice import FAMILY_DEMONSTRATION_ROOT, _rows, family_producer

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEMONSTRATION = EXAMPLE / "producer-demonstration"
PRODUCER_TREES = {
    "cp-04-canonical-corporate-family-tree": FAMILY_DEMONSTRATION_ROOT,
    "cp-13-canonical-covenant-cross-reference": COVENANT_DEMONSTRATION_ROOT,
}
BLOCK_OPEN = "# >>> CP-14 DEMONSTRATION CONFIGURATION"
BLOCK_CLOSE = "# <<< CP-14 DEMONSTRATION CONFIGURATION"
FAMILY, COVENANT = CHILD_CLASSES[1], CHILD_CLASSES[4]
DIAGNOSTIC = "1.0"

ESTATE_VARIABLES = (
    "CCF_CP_14_POSTGRES_DSN", "CCF_CP_14_POSTGRES_SCHEMA", "CCF_CP_14_FLUREE_URL", "CCF_CP_14_FLUREE_LEDGER",
    "CCF_CP_04C_FLUREE_URL", "CCF_CP_04C_FLUREE_LEDGER", "CCF_CP_04C_POSTGRES_DSN", "CCF_CP_04C_POSTGRES_SCHEMA",
    "CCF_CP_13C_POSTGRES_DSN", "CCF_CP_13C_POSTGRES_SCHEMA", "CCF_CP_13C_FLUREE_URL", "CCF_CP_13C_FLUREE_LEDGER",
    "CCF_CP_13C_MONGO_URI", "CCF_CP_13C_MONGO_DB",
)


def _declared_instant(config_text: str) -> datetime | None:
    section = yaml.safe_load(config_text).get("demonstration_serve_instant")
    return None if not section else datetime.fromisoformat(str(section["serve_instant"]))


def _without_producer_clock(text: str) -> str:
    """``text`` with its `demonstration_serve_instant:` section and the comment paragraph above it removed."""
    lines = text.splitlines()
    if "demonstration_serve_instant:" not in lines:
        return text.rstrip("\n")
    start = lines.index("demonstration_serve_instant:")
    end = start + 1
    while end < len(lines) and lines[end].startswith((" ", "\t")):
        end += 1
    while start > 0 and lines[start - 1].startswith("#"):
        start -= 1
    return "\n".join(lines[:start] + lines[end:]).rstrip("\n")


def _without_demonstration_block(text: str) -> tuple[str, str]:
    """``text`` split into (the document outside the one delimited block, the block)."""
    assert text.count(BLOCK_OPEN) == 1 and text.count(BLOCK_CLOSE) == 1, "the copy must carry exactly one delimited block"
    head, rest = text.split(BLOCK_OPEN, 1)
    block, tail = rest.split(BLOCK_CLOSE, 1)
    assert not tail.strip(), "nothing may follow the demonstration block"
    return head.rstrip("\n"), BLOCK_OPEN + block


# --- 1. the copy is the producer, but for the clock --------------------------------------


@pytest.mark.parametrize("tree", sorted(PRODUCER_TREES))
def test_each_demonstration_configuration_is_its_producer_but_for_the_declared_clock(tree: str) -> None:
    producer, copy = REPO_ROOT / "examples" / tree, PRODUCER_TREES[tree]
    assert copy.parent == DEMONSTRATION and copy.name == tree
    assert sorted(path.name for path in copy.iterdir()) == ["ccf_config.yaml", "ccf_environment.yaml"]
    assert (copy / "ccf_environment.yaml").read_bytes() == (producer / "ccf_environment.yaml").read_bytes()

    own = (producer / "ccf_config.yaml").read_text(encoding="utf-8")
    demonstration = (copy / "ccf_config.yaml").read_text(encoding="utf-8")
    outside, block = _without_demonstration_block(demonstration)
    assert outside == _without_producer_clock(own), f"{tree}'s demonstration configuration drifted from its producer"
    assert "demonstration_serve_instant:" not in outside
    # The one block that differs declares cp-14's OWN demonstration instant, labelled.
    cp14 = _declared_instant((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert cp14 is not None and cp14.date() == CP14_INSTANT.date()
    assert _declared_instant(demonstration) == cp14
    assert "Illustrative calibration" in block and "not" in block and "production caller" in block


def test_the_producers_own_clocks_are_unchanged() -> None:
    """Ruling 2 confines the change to the demonstration configuration: cp-04-canonical
    still declares no demonstration instant, and cp-13-canonical still declares its own
    spec-dated 2026-09-13T00:05Z."""
    family = (REPO_ROOT / "examples" / "cp-04-canonical-corporate-family-tree" / "ccf_config.yaml").read_text(encoding="utf-8")
    covenant = (REPO_ROOT / "examples" / "cp-13-canonical-covenant-cross-reference" / "ccf_config.yaml").read_text(encoding="utf-8")
    assert _declared_instant(family) is None
    assert _declared_instant(covenant) == datetime.fromisoformat("2026-09-13T00:05:00+00:00")


# --- 2. both outcomes, on the live estate -----------------------------------------------


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = f"the live estate is not configured: {', '.join(missing)} unset (CLAUDE.md §9)"
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


def _ask_with(modules: tuple[Any, Any], scratch: pathlib.Path, *, demonstration: bool) -> dict[str, Any]:
    """The diagnostic question with the family and covenant doors live — on the
    demonstration configurations, or on their own trees — and the other three slots
    pointed at a port nothing listens on (their rows are not under test here)."""
    produce, deployment = modules
    with ExitStack() as stack:
        family_url = stack.enter_context(family_producer(FAMILY_DEMONSTRATION_ROOT if demonstration else None))
        covenant_url = stack.enter_context(covenant_producer(COVENANT_DEMONSTRATION_ROOT if demonstration else None))
        environ = {
            name: os.environ[name]
            for name in ("CCF_CP_14_POSTGRES_DSN", "CCF_CP_14_POSTGRES_SCHEMA", "CCF_CP_14_FLUREE_URL", "CCF_CP_14_FLUREE_LEDGER")
        }
        environ |= {
            "CCF_CP14_FAMILY_URL": family_url, "CCF_CP14_COVENANT_URL": covenant_url,
            **{f"CCF_CP14_{slot}_URL": UNREACHABLE for slot in ("SPREAD", "EXPOSURE", "COLLATERAL")},
            **{f"CCF_CP14_{slot}_TOKEN": DEV_TOKEN for slot in ("SPREAD", "FAMILY", "EXPOSURE", "COLLATERAL", "COVENANT")},
        }
        with produce.product(scratch, environ=environ) as opened:
            asked = opened.question(
                subject=BGC, asked_at=CP14_INSTANT, intent="annual-review", freshness="decision-scoped",
                parameters={
                    deployment.AS_OF: CP14_INSTANT.isoformat(),
                    deployment.DEBT_TOLERANCE: Decimal(DIAGNOSTIC),
                    deployment.FACILITY_ID: BGC_FACILITY,
                },
            )
            outcome = opened.answer(asked)
            return _rows(_record_of(opened, outcome))


@pytest.fixture(scope="module")
def outcomes(modules: tuple[Any, Any], estate: None, tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict[str, Any]]:
    scratch = tmp_path_factory.mktemp("cp14-clock")
    return {
        "own": _ask_with(modules, scratch / "own", demonstration=False),
        "demonstration": _ask_with(modules, scratch / "demonstration", demonstration=True),
    }


def test_on_their_own_clocks_the_family_and_covenant_producers_refuse_the_cp14_question(
    outcomes: dict[str, dict[str, Any]],
) -> None:
    """Original configuration → REFUSED. Booted on their own trees (cp-04-canonical on
    the real clock, cp-13-canonical at 2026-09-13), each producer's own door refuses
    the 2026-09-07 question `asked-at-outside-temporal-bound`, retained on the row."""
    rows = outcomes["own"]
    for product_class in (FAMILY, COVENANT):
        row = rows[product_class]
        assert row.outcome_status == "ineligible", (product_class, row.outcome_status)
        assert (row.producer_refusal_kind, row.producer_refusal_reason) == (
            "temporal-bound-refusal", "asked-at-outside-temporal-bound",
        ), (product_class, row.producer_refusal_kind, row.producer_refusal_reason)
        assert row.child_content_address is None


def test_on_the_shared_demonstration_time_the_family_and_covenant_children_are_admitted(
    outcomes: dict[str, dict[str, Any]],
) -> None:
    """Demonstration configuration → ADMITTED. The same question, the same doors, booted
    on CP-14's demonstration configurations (2026-09-07T12:05Z): both children are
    admitted under `provider-controls`, asked at the CP-14 instant."""
    rows = outcomes["demonstration"]
    for product_class in (FAMILY, COVENANT):
        row = rows[product_class]
        assert (row.outcome_status, row.eligibility_basis) == ("admitted", "provider-controls"), (
            product_class, row.outcome_status, row.producer_refusal_reason,
        )
        assert row.child_asked_at == CP14_INSTANT and row.child_content_address
        assert row.producer_refusal_kind is None


def test_the_parent_on_the_real_clock_refuses_its_dated_question(
    modules: tuple[Any, Any], estate: None, tmp_path: pathlib.Path,
) -> None:
    """The parent's own declaration, both outcomes. With cp-14's
    `demonstration_serve_instant:` removed (a test-owned copy of its two documents,
    nothing else changed) the deployment serves on the real clock, and the
    2026-09-07 question is refused by the PARENT `asked-at-outside-temporal-bound`,
    by name, with a replay reference — no producer is asked. With the declaration
    (the two tests above) the parent asks every producer."""
    from tests.examples.demonstration_deployment import paved_root_on_the_real_clock  # noqa: PLC0415

    produce, deployment = modules
    root = paved_root_on_the_real_clock(EXAMPLE, directory=tmp_path / "deployment")
    environ = {
        name: os.environ[name]
        for name in ("CCF_CP_14_POSTGRES_DSN", "CCF_CP_14_POSTGRES_SCHEMA", "CCF_CP_14_FLUREE_URL", "CCF_CP_14_FLUREE_LEDGER")
    }
    environ |= {f"CCF_CP14_{slot}_URL": UNREACHABLE for slot in ("SPREAD", "FAMILY", "EXPOSURE", "COLLATERAL", "COVENANT")}
    environ |= {f"CCF_CP14_{slot}_TOKEN": DEV_TOKEN for slot in ("SPREAD", "FAMILY", "EXPOSURE", "COLLATERAL", "COVENANT")}
    with produce.product(tmp_path / "scratch", environ=environ, config_root=root) as opened:
        asked = opened.question(
            subject=BGC, asked_at=CP14_INSTANT, intent="annual-review", freshness="decision-scoped",
            parameters={
                deployment.AS_OF: CP14_INSTANT.isoformat(),
                deployment.DEBT_TOLERANCE: Decimal(DIAGNOSTIC),
                deployment.FACILITY_ID: BGC_FACILITY,
            },
        )
        outcome = opened.answer(asked)
    assert (outcome.kind, outcome.reason) == ("temporal-bound-refusal", "asked-at-outside-temporal-bound"), outcome
    assert outcome.replay_reference
