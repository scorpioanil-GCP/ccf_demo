"""Determinism pins for the e2e-demo synthetic data generator (DEMO-01).

Phase 12 CONTEXT D-05..D-08: the generator is a pure interpreter of
``examples/08-e2e-demo/artifacts/scenario.yaml``; determinism is pinned by
regenerating and comparing logical-content checksums against the artifact's
``expected`` block. A mismatch here is the drift alarm working as designed —
changing the scenario or the generator REQUIRES updating the pins in the
same commit.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sqlite3
from typing import Any

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "08-e2e-demo"
SCENARIO_PATH = EXAMPLE_DIR / "artifacts" / "scenario.yaml"


def _load_generator() -> Any:
    """Load the example's generator module from its file path.

    ``08-e2e-demo`` is not an importable package name; the examples suite
    loads example modules by path (same pattern as tests/perf_gate).
    """
    spec = importlib.util.spec_from_file_location(
        "demo_generator_under_test", EXAMPLE_DIR / "generator.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scenario() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(
        SCENARIO_PATH.read_text(encoding="utf-8")
    )
    return document


@pytest.fixture(scope="module")
def generator() -> Any:
    return _load_generator()


def test_generation_is_deterministic(
    scenario: dict[str, Any], generator: Any, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Test 1: two independent generations yield identical logical checksums."""
    first = generator.generate(scenario, tmp_path_factory.mktemp("gen-a"))
    second = generator.generate(scenario, tmp_path_factory.mktemp("gen-b"))
    assert first["checksums"] == second["checksums"]
    assert first["row_counts"] == second["row_counts"]
    assert first["ring_signature"] == second["ring_signature"]


def test_pins_match_the_scenario_expected_block(
    scenario: dict[str, Any], generator: Any, tmp_path: pathlib.Path
) -> None:
    """Test 2: computed checksums/row counts equal the artifact pins."""
    result = generator.generate(scenario, tmp_path)
    expected = scenario["expected"]
    assert result["row_counts"] == expected["row_counts"]
    for source, pin in expected["checksums"].items():
        assert isinstance(pin, str) and len(pin) == 64, (
            f"expected.checksums.{source} must be a pinned sha256 hex string"
        )
        assert result["checksums"][source] == pin


def test_planted_ring_is_in_the_generated_store(
    scenario: dict[str, Any], generator: Any, tmp_path: pathlib.Path
) -> None:
    """Test 3: the circular payment edges exist and match the pinned signature."""
    result = generator.generate(scenario, tmp_path)
    expected = scenario["expected"]
    assert isinstance(expected["ring_signature"], str)
    assert len(expected["ring_signature"]) == 64
    assert result["ring_signature"] == expected["ring_signature"]

    # The edges genuinely exist as rows: every ring reference is present in
    # the transfer-log source's movements table, and following from->to
    # covers all members exactly once and closes into a single cycle.
    edges = scenario["ring"]["edges"]
    members = [m["key"] for m in scenario["ring"]["members"]]
    successor = {e["from"]: e["to"] for e in edges}
    seen, node = [], edges[0]["from"]
    for _ in members:
        seen.append(node)
        node = successor[node]
    assert node == edges[0]["from"], "ring edges must close a single cycle"
    assert sorted(seen) == sorted(expected["cycle_members"])
    assert expected["cycle_count"] == 1

    transfer_source = next(
        s for s in scenario["sources"].values() if s["role"] == "transfer_log"
    )
    table = transfer_source["tables"]["movements"]
    id_column = next(
        c["name"] for c in table["columns"] if c["role"] == "id"
    )
    with sqlite3.connect(tmp_path / transfer_source["db_file"]) as connection:
        for edge in edges:
            rows = connection.execute(
                f'SELECT count(*) FROM "{table["name"]}" WHERE "{id_column}" = ?',
                (edge["reference"],),
            ).fetchone()
            assert rows[0] == 1, f"ring edge {edge['reference']} missing"


def test_row_counts_visible_via_plain_sqlite(
    scenario: dict[str, Any], generator: Any, tmp_path: pathlib.Path
) -> None:
    """A curious newcomer's view (D-06): plain sqlite3 counts match the pins."""
    generator.generate(scenario, tmp_path)
    for source_name, source in scenario["sources"].items():
        with sqlite3.connect(tmp_path / source["db_file"]) as connection:
            for table in source["tables"].values():
                (count,) = connection.execute(
                    f'SELECT count(*) FROM "{table["name"]}"'
                ).fetchone()
                expected = scenario["expected"]["row_counts"][source_name][
                    table["name"]
                ]
                assert count == expected
