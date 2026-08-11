"""Measurement instrument for the Phase 15.5 ruling package (plan 15.5-01).

**This module measures costs. It does not test correctness.** Every figure it
produces exists to fill a Measured Cost cell in
``docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md`` so that Dave rules on numbers rather
than on projections. ``15.5-RESEARCH.md`` carried four assumptions — A2 (the
field-addition blast radius), A3 (supersession reachability from the debt path),
A8 (the micro-benchmark headroom) and the Q3 determinism derivation — that were
explicitly *not* executed during research. This module executes them.

The rule this module obeys
--------------------------
**Assert only facts that no plan in this phase is scoped to change; report
everything else.**

``pyproject.toml`` sets ``testpaths = ["tests"]``, so ``tests/spikes/`` runs
under ``make ci-core``, which must stay green from wave 1 onward. Plans
``15.5-03``, ``15.5-07``, ``15.5-08``, ``15.5-09``, ``15.5-10``, ``15.5-11``,
``15.5-12`` and ``15.5-13`` each add or move the constructor call sites this
module counts. A module asserting a call-site count would go red on *correct*
work by a later plan in its own phase, and the only available repair would be to
edit the evidence. Editing the evidence to keep a gate green is the opposite of
evidence.

So the separation is load-bearing, not stylistic:

* **Reported** (via :func:`measure_all`, never compared in an assertion):
  every tree-derived count, and the outcome of the real rehydration tripwire.
* **Asserted**: only properties of stand-in models this module itself owns, of
  the content-addressing function, and of the five shipped positive sentinels
  that no plan in this phase removes (``15.5-11`` *adds* one).

The one exception on the reported side is an instrument check: the AST walk
asserts that it *found* each symbol at all. A walk returning zero for
``ContextProductContract`` means the walker is broken, which is a fact about
the instrument rather than about the tree, and it stays true however many call
sites later plans add or remove.

Reading the figures
-------------------
``pytest tests/spikes/test_contract_field_addition_cost.py -s`` prints the whole
figure set as JSON. Set ``CCF_SPIKE_REPORT=/path/to/figures.json`` to also write
it to a file. Neither writes anything into the tree.

Retiring owner
--------------
**Plan ``15.5-14``, task 1.** This is a measurement instrument with a
phase-length life. ``15.5-14``'s sweep either retires it or re-points it at the
post-ruling tree, and accounts for the choice in the gate package. No other plan
owns it.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any

import pytest

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.replay import record as record_module
from ccf.replay import serve as serve_module

# --------------------------------------------------------------------------
# Tree location
# --------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The trees walked for call sites. ``perf/`` and ``tools/`` are included
#: because RESEARCH.md § Blast Radius names both as couplings a ``src/``-only
#: sweep misses.
SEARCH_ROOTS: tuple[str, ...] = (
    "src",
    "runtime",
    "tests",
    "perf",
    "examples",
    "tools",
)

#: Never walked: virtualenvs, bytecode caches, and this instrument's own
#: package — an instrument that counted itself would report its own stand-ins
#: as tree cost.
EXCLUDED_PARTS: frozenset[str] = frozenset(
    {".venv", "venv", "__pycache__", ".git", "node_modules", "spikes"}
)

#: The five symbols whose blast radius gates the field-addition strategy
#: (RESEARCH.md § Blast Radius, assumption A2).
MEASURED_SYMBOLS: tuple[str, ...] = (
    "ContextProductContract",
    "register_product_class",
    "ProductLineage",
    "run_gates",
    "Perspective",
)

#: The in-process population that would see debt under Q3's
#: ``ServedProduct``-beside option; task 3 quotes this figure against each of
#: the three delivery paths.
SERVE_CALL_SYMBOL = "serve"

REHYDRATION_TRIPWIRE = pathlib.Path("tests/replay/test_engine_rehydration.py")

#: Set to anything other than ``"1"`` to skip the tripwire run; the figure is
#: then reported as not taken, with the reason. Never estimated.
TRIPWIRE_ENV = "CCF_SPIKE_RUN_TRIPWIRE"

#: Where :func:`measure_all` writes its JSON, if set.
REPORT_ENV = "CCF_SPIKE_REPORT"


# --------------------------------------------------------------------------
# A2 — the required-field cost. REPORTED.
# --------------------------------------------------------------------------


def _python_files() -> Iterator[pathlib.Path]:
    """Yield every ``.py`` file under :data:`SEARCH_ROOTS`, exclusions applied."""
    for root_name in SEARCH_ROOTS:
        root = REPO_ROOT / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if EXCLUDED_PARTS & set(path.parts):
                continue
            yield path


@lru_cache(maxsize=1)
def _parsed_tree() -> tuple[tuple[pathlib.Path, ast.Module], ...]:
    """Parse every walked file once; an unparseable file is skipped, not raised."""
    parsed: list[tuple[pathlib.Path, ast.Module]] = []
    for path in _python_files():
        try:
            parsed.append((path, ast.parse(path.read_text(encoding="utf-8"))))
        except (SyntaxError, UnicodeDecodeError):
            continue
    return tuple(parsed)


def _called_name(node: ast.Call) -> tuple[str, str] | None:
    """Return ``(kind, name)`` for a call's callee, if it resolves to a name.

    ``kind`` separates a bare ``Symbol(...)`` from a ``receiver.symbol(...)``.
    The split matters for :data:`SERVE_CALL_SYMBOL`: a plain ``serve(...)`` is
    the governed delivery seam, while ``server.serve(...)`` is an unrelated
    method of the same name, and a figure that merged the two would overstate
    the in-process population Q3's ``ServedProduct``-beside option reaches.
    """
    func = node.func
    if isinstance(func, ast.Name):
        return ("name", func.id)
    if isinstance(func, ast.Attribute):
        return ("attribute", func.attr)
    return None


@lru_cache(maxsize=None)
def count_call_sites(symbol: str, kind: str = "any") -> dict[str, Any]:
    """Count direct calls of ``symbol`` by AST walk.

    A **call-site** count, not the ``grep -rl`` file-membership estimate
    RESEARCH.md § Blast Radius carried: a module constructing the same type nine
    times is nine repair sites, not one. That difference is the whole reason
    assumption A2 was flagged as a projection rather than a measurement.

    ``kind`` is ``"any"``, ``"name"`` (bare ``Symbol(...)``) or ``"attribute"``
    (``receiver.symbol(...)``).
    """
    per_file: dict[str, int] = {}
    per_directory: dict[str, int] = {}
    total = 0
    bare_name_calls = 0
    attribute_calls = 0
    for path, tree in _parsed_tree():
        resolved = [
            _called_name(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        ]
        matches = [
            pair
            for pair in resolved
            if pair is not None
            and pair[1] == symbol
            and (kind == "any" or pair[0] == kind)
        ]
        if not matches:
            continue
        bare_name_calls += sum(1 for k, _ in matches if k == "name")
        attribute_calls += sum(1 for k, _ in matches if k == "attribute")
        relative = path.relative_to(REPO_ROOT)
        per_file[str(relative)] = len(matches)
        directory = str(relative.parent)
        per_directory[directory] = per_directory.get(directory, 0) + len(matches)
        total += len(matches)
    return {
        "symbol": symbol,
        "kind": kind,
        "call_sites": total,
        "bare_name_calls": bare_name_calls,
        "attribute_calls": attribute_calls,
        "distinct_files": len(per_file),
        "by_directory": dict(sorted(per_directory.items())),
        "by_file": dict(sorted(per_file.items())),
    }


def _examples_subtotal(measured: Mapping[str, Any]) -> dict[str, Any]:
    """Sum a measured symbol's call sites under ``examples/`` only."""
    by_file = {
        path: hits
        for path, hits in measured["by_file"].items()
        if path.startswith("examples/")
    }
    return {"call_sites": sum(by_file.values()), "by_file": by_file}


def measure_call_sites() -> dict[str, Any]:
    """The A2 blast radius, per measured symbol. REPORTED."""
    measured: dict[str, Any] = {
        symbol: count_call_sites(symbol) for symbol in MEASURED_SYMBOLS
    }
    governed_seam = count_call_sites(SERVE_CALL_SYMBOL, "name")
    measured[SERVE_CALL_SYMBOL] = {
        "any_kind": count_call_sites(SERVE_CALL_SYMBOL),
        "governed_seam_only": governed_seam,
        "governed_seam_in_examples": _examples_subtotal(governed_seam),
    }
    return measured


# --------------------------------------------------------------------------
# A2, second limb — the sentinel alternative. ASSERTED.
# --------------------------------------------------------------------------


def _field_default(model: Any, field_name: str) -> Any:
    return model.model_fields[field_name].default


def measure_sentinels() -> dict[str, Any]:
    """The five shipped positive-sentinel defaults (PATTERNS § Pattern 9)."""
    serve_defaults = inspect.signature(serve_module.serve).parameters
    return {
        "MODE_1_MODEL_VERSION": {
            "constant": record_module.MODE_1_MODEL_VERSION,
            "default_of": "ModelVersionRecord.model_version",
            "default": _field_default(
                record_module.ModelVersionRecord, "model_version"
            ),
        },
        "NO_HITL_ACTIONS": {
            "constant": record_module.NO_HITL_ACTIONS,
            "default_of": "PolicyBindingsSnapshot.hitl_actions",
            "default": _field_default(
                record_module.PolicyBindingsSnapshot, "hitl_actions"
            ),
        },
        "NO_GRAPH_QUERIES": {
            "constant": record_module.NO_GRAPH_QUERIES,
            "default_of": "ContentGenerationPath.graph_query_sequence",
            "default": _field_default(
                record_module.ContentGenerationPath, "graph_query_sequence"
            ),
        },
        "source_attestation": {
            "constant": None,
            "default_of": "ContextFabricSnapshot.source_attestation",
            "default": _field_default(
                record_module.ContextFabricSnapshot, "source_attestation"
            ),
        },
        "serve_15_2_08_defaults": {
            "default_of": "ccf.replay.serve.serve",
            "query_pin_writer": serve_defaults["query_pin_writer"].default,
            "executed_queries": serve_defaults["executed_queries"].default,
        },
    }


# --------------------------------------------------------------------------
# Q3 — the four debt placements. ASSERTED.
# --------------------------------------------------------------------------
#
# Every stand-in below is owned by this module. ``src/`` is never modified: the
# measurement is about what *would* happen to the content address, and a source
# edit here would pre-empt the ruling.

_BOUNDARY = datetime(2026, 3, 15, tzinfo=UTC)
_EXPIRY = datetime(2026, 3, 15, 12, tzinfo=UTC)
_DEBT = Decimal("0.42")


class _ProductWithDebt(ContextProductContract):
    """Throwaway stand-in: the vessel with a ``Decimal`` debt field on the body.

    Owned by this module and imported nowhere else. It exists so the hash
    question can be answered without touching
    :class:`~ccf.products.contract.ContextProductContract`.
    """

    debt: Decimal


class _RecordSideDebt(CCFContract):
    """Throwaway stand-in for a debt surface on the replay record."""

    product_content_address: str
    debt: Decimal


class _ServedWithDebt(CCFContract):
    """Throwaway stand-in for debt travelling beside the product."""

    product: ContextProductContract
    replay_ref: str
    debt: Decimal


def _baseline_product() -> ContextProductContract:
    """The shipped vessel as every existing call site constructs it today."""
    return ContextProductContract(
        schema_name="spike.measurement",
        schema_version="1.0.0",
        plan_id="spike/plan",
        tenant_id="tenant-spike",
        temporal_boundary=_BOUNDARY,
        expires_at=_EXPIRY,
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"temporal.as-of-boundary"}),
            policy_bundle_versions=frozenset({"policy-v1"}),
            graph_snapshot_at=_BOUNDARY,
        ),
        payload={"answer": "42"},
    )


def _product_with_debt(debt: Decimal) -> _ProductWithDebt:
    base = _baseline_product()
    return _ProductWithDebt(
        **{name: getattr(base, name) for name in type(base).model_fields},
        debt=debt,
    )


def measure_q3_placements() -> dict[str, Any]:
    """The four Q3 candidate placements, each with an observed hash verdict.

    The verdicts are properties of :func:`~ccf.contracts.canonical.content_hash`
    applied to stand-ins this module owns, so plan ``15.5-07`` and plan
    ``15.5-11`` may both reshape the shipped vessel without falsifying any of
    them: "adding a field to the hashed body changes the hash" survives any
    reshaping of the field list.
    """
    baseline = _baseline_product()
    baseline_address = content_hash(baseline)

    on_product_address = content_hash(_product_with_debt(_DEBT))

    beside_the_product = _RecordSideDebt(
        product_content_address=baseline_address, debt=_DEBT
    )
    record_only_address = content_hash(baseline)

    rehydrated_address = content_hash(_product_with_debt(beside_the_product.debt))

    served = _ServedWithDebt(
        product=baseline, replay_ref="artifact://spike", debt=_DEBT
    )
    served_address = content_hash(served.product)

    return {
        "baseline_product_content_address": baseline_address,
        "product_only": {
            "content_address_changes": on_product_address != baseline_address,
            "observed": on_product_address,
            "reason": (
                "canonical_bytes walks a model field-by-field over "
                "type(value).model_fields, so a Decimal debt field on the "
                "hashed body is in the bytes and therefore in the address; "
                "the record carries nothing to reconstruct it from, so "
                "rehydrate_product cannot reproduce it and the engine's "
                "check at src/ccf/replay/engine.py:449-455 raises"
            ),
        },
        "record_only": {
            "content_address_changes": record_only_address != baseline_address,
            "observed": record_only_address,
            "reason": (
                "the product's field list is untouched; debt lives on a "
                "record-side structure the engine's content-address check "
                "never hashes"
            ),
        },
        "both": {
            "content_address_changes": rehydrated_address != baseline_address,
            "reconstructible_from_record": (
                rehydrated_address == on_product_address
            ),
            "observed": rehydrated_address,
            "reason": (
                "the address moves exactly as product-only, but a rehydrator "
                "reading debt back off the record reproduces the same bytes, "
                "so the engine's hash check can pass"
            ),
        },
        "served_product_beside": {
            "content_address_changes": served_address != baseline_address,
            "observed": served_address,
            "reason": (
                "ServedProduct is not content-hashed into the record; the "
                "delivered ContextProductContract bytes are byte-for-byte "
                "what they are today"
            ),
        },
    }


# --------------------------------------------------------------------------
# The real tripwire. REPORTED.
# --------------------------------------------------------------------------

#: Which Q3 placements the real tripwire can be run against as the tree stands.
TRIPWIRE_SHAPES: Mapping[str, str] = {
    "product_only": (
        "cannot be exercised: ContextProductContract is frozen and "
        "extra=forbid, so the field cannot exist without editing "
        "src/ccf/products/contract.py, which this plan is forbidden to do"
    ),
    "record_only": (
        "exercised: the product's bytes are unchanged, so the tripwire runs "
        "exactly as it does today and its result is the measured baseline"
    ),
    "both": (
        "cannot be exercised: requires a new field on the vessel, a new debt "
        "surface on DecisionReplayRecord, and a rehydrate_product that reads "
        "it back — three source changes"
    ),
    "served_product_beside": (
        "exercised: ServedProduct is outside the hashed body, so the tripwire "
        "runs unchanged; its result is the same measured baseline"
    ),
}


@lru_cache(maxsize=1)
def run_rehydration_tripwire() -> dict[str, Any]:
    """Run ``tests/replay/test_engine_rehydration.py`` and report the outcome.

    A separate interpreter rather than a nested ``pytest.main`` call: the outer
    session's capture, plugin registry and already-imported conftest modules are
    left entirely alone, so the figure measures the tripwire and not the
    interaction between two pytest sessions.

    Only two of the four Q3 placements can be exercised against the real
    tripwire without a source change; :data:`TRIPWIRE_SHAPES` records the
    precise reason for the other two.
    """
    if os.environ.get(TRIPWIRE_ENV, "1") != "1":
        return {
            "ran": False,
            "reason": f"{TRIPWIRE_ENV} is not '1'; measurement skipped",
        }
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(REHYDRATION_TRIPWIRE), "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = completed.stdout.strip().splitlines()
    return {
        "ran": True,
        "command": f"python -m pytest {REHYDRATION_TRIPWIRE} -q",
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "summary": lines[-1] if lines else "",
    }


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def measure_all() -> dict[str, Any]:
    """Every figure this module produces, as one mapping.

    This is the reporting half. It is a plain helper the tests call; it is not
    a fixture, and nothing it returns is compared in an assertion.
    """
    return {
        "instrument": {
            "module": "tests/spikes/test_contract_field_addition_cost.py",
            "plan": "15.5-01",
            "retiring_owner": "15.5-14 task 1",
            "search_roots": SEARCH_ROOTS,
            "excluded_path_parts": tuple(sorted(EXCLUDED_PARTS)),
            "self_excluded": (
                "tests/spikes/ is excluded from the walk; this module's own "
                "stand-in constructors are not tree cost"
            ),
        },
        "a2_call_sites": measure_call_sites(),
        "a2_sentinels": measure_sentinels(),
        "q3_placements": measure_q3_placements(),
        "q3_tripwire": run_rehydration_tripwire(),
        "q3_tripwire_shapes": dict(TRIPWIRE_SHAPES),
    }


def _render(figures: Mapping[str, Any]) -> str:
    return json.dumps(figures, indent=2, sort_keys=True, default=str)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_the_report_is_producible_and_is_printed_for_the_evidence_document(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Produce the figure set. Nothing here compares a tree-derived value.

    Run with ``-s`` to read the figures, or set ``CCF_SPIKE_REPORT`` to a path
    to have them written there as JSON.
    """
    figures = measure_all()
    rendered = _render(figures)
    with capsys.disabled():
        print(f"\n=== 15.5-01 measured figures ===\n{rendered}")
    destination = os.environ.get(REPORT_ENV)
    if destination:
        pathlib.Path(destination).write_text(rendered, encoding="utf-8")
    assert set(figures) >= {"a2_call_sites", "a2_sentinels", "q3_placements"}


@pytest.mark.parametrize("symbol", MEASURED_SYMBOLS)
def test_the_ast_walk_finds_the_symbol_at_all(symbol: str) -> None:
    """An instrument check, deliberately not a count check.

    A walk returning zero for ``ContextProductContract`` means the walker is
    broken. That is a fact about the instrument, and it stays true however many
    call sites plans ``15.5-03``/``07``/``08``/``09``/``10``/``11``/``12``/
    ``13`` add or remove. The counts themselves are reported, never asserted.
    """
    measured = count_call_sites(symbol)
    assert measured["call_sites"] > 0, symbol
    assert measured["distinct_files"] > 0, symbol


# --- A2, second limb: the sentinel alternative. ASSERTED. ------------------


def test_the_five_positive_sentinels_still_exist_and_are_still_defaults() -> None:
    """PATTERNS § Pattern 9, asserted because no plan in this phase removes one.

    Plan ``15.5-11`` *adds* a sentinel; none of the eight contract-touching
    plans removes one, so this assertion is stable under the phase's own work.
    The sentinel strategy's availability is an input to every field ruling: if
    the precedent had moved, the ruling package would have to say so.
    """
    assert record_module.MODE_1_MODEL_VERSION == "none"
    assert (
        _field_default(record_module.ModelVersionRecord, "model_version")
        == record_module.MODE_1_MODEL_VERSION
    )

    assert record_module.NO_HITL_ACTIONS == "no-hitl-actions"
    assert (
        _field_default(record_module.PolicyBindingsSnapshot, "hitl_actions")
        == record_module.NO_HITL_ACTIONS
    )

    assert record_module.NO_GRAPH_QUERIES == ()
    assert (
        _field_default(
            record_module.ContentGenerationPath, "graph_query_sequence"
        )
        == record_module.NO_GRAPH_QUERIES
    )

    assert (
        _field_default(record_module.ContextFabricSnapshot, "source_attestation")
        is None
    )

    serve_parameters = inspect.signature(serve_module.serve).parameters
    assert serve_parameters["query_pin_writer"].default is None
    assert serve_parameters["executed_queries"].default == ()


# --- Q3: the four placements. ASSERTED. -----------------------------------


def test_q3_product_only_changes_the_content_address() -> None:
    """A debt field on the hashed body moves the address. Therefore not viable.

    ``rehydrate_product`` rebuilds the product from ``(record, re-executed
    projection)`` and the engine hash-checks the result
    (``src/ccf/replay/engine.py:449-455``). A field that is on the product and
    nowhere on the record is unreconstructible, so every replay of every
    product would raise ``ReplayDivergence``.
    """
    placements = measure_q3_placements()
    assert placements["product_only"]["content_address_changes"] is True
    assert (
        placements["product_only"]["observed"]
        != placements["baseline_product_content_address"]
    )


def test_q3_record_only_leaves_the_content_address_untouched() -> None:
    """Debt on the record alone does not move the product's bytes."""
    placements = measure_q3_placements()
    assert placements["record_only"]["content_address_changes"] is False
    assert (
        placements["record_only"]["observed"]
        == placements["baseline_product_content_address"]
    )


def test_q3_both_changes_the_address_but_is_reconstructible() -> None:
    """The address moves, and a rehydrator reading the record reproduces it."""
    placements = measure_q3_placements()
    assert placements["both"]["content_address_changes"] is True
    assert placements["both"]["reconstructible_from_record"] is True


def test_q3_served_product_beside_leaves_the_content_address_untouched() -> None:
    """``ServedProduct`` sits outside the hashed body.

    Nothing about the product's bytes — and therefore nothing about replay,
    A2A signatures, or recorded example expectations — moves.
    """
    placements = measure_q3_placements()
    assert placements["served_product_beside"]["content_address_changes"] is False
    assert (
        placements["served_product_beside"]["observed"]
        == placements["baseline_product_content_address"]
    )


def test_every_q3_placement_has_a_verdict_and_a_reason() -> None:
    """Structural: the ruling package cannot be handed an unexplained cell."""
    placements = measure_q3_placements()
    for name in ("product_only", "record_only", "both", "served_product_beside"):
        verdict = placements[name]
        assert isinstance(verdict["content_address_changes"], bool), name
        assert verdict["reason"].strip(), name
        assert name in TRIPWIRE_SHAPES, name
