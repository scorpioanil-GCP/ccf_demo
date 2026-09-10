"""What `examples/cp-06-collateral-and-setoff-coverage` actually serves.

**Directional, never pinned.** Every assertion below is a business relationship
that must hold at any roster size — haircuts reduce coverage, valid set-off
increases it, priority and pro-rata disagree — rather than a number this module
restates. A test that pinned `1.089` would go red on the next legitimate
valuation change for no reason anyone could act on, and would have turned the
curated estate back into a fixture (CLAUDE.md §9).

**Read-only.** This module reads the curated estate and seeds nothing. It
creates no ledger and no schema, so it adds nothing to an append-only store
that could never be removed.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-06-collateral-and-setoff-coverage"

ESTATE_VARIABLES = (
    "CCF_CP_06_FLUREE_URL", "CCF_CP_06_FLUREE_LEDGER",
    "CCF_CP_06_POSTGRES_DSN", "CCF_CP_06_POSTGRES_SCHEMA",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"

#: Module names every example ships. `produce` reaches its sibling by a bare
#: `import deployment`, so the first example imported owns those names for the
#: session — green alone and red beside another example's module.
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve")


def _anchor(name: str) -> str:
    """A demonstration constant, read from `run.py` rather than restated."""
    for node in ast.walk(ast.parse((EXAMPLE / "run.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise AssertionError(f"run.py declares no {name}")


@pytest.fixture(scope="module")
def estate() -> tuple[str, str]:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL"
            " `ccf_v2` — never the v1 names in `ccf_dataprep/.env`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)
    return (os.environ["CCF_CP_06_FLUREE_LEDGER"],
            os.environ["CCF_CP_06_POSTGRES_SCHEMA"])


@pytest.fixture(scope="module")
def example() -> Iterator[tuple[Any, Any]]:
    """This example's own `deployment` and `produce`, whatever ran before."""
    saved = {n: sys.modules.pop(n, None) for n in COLLIDING}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == EXAMPLE
        yield deployment, produce
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


def _serve(example: tuple[Any, Any], **kwargs: Any) -> Any:
    """One run of the demonstration facility, in its own scratch fabric."""
    deployment, produce = example
    asked = deployment.request(
        facility_id=_anchor("DEMONSTRATION_FACILITY"),
        borrower_scope=[_anchor("DEMONSTRATION_SCOPE")],
        asked_at=datetime.now(UTC), **kwargs)
    with tempfile.TemporaryDirectory() as scratch:
        return produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))


def _ratio(outcome: Any) -> Decimal:
    return Decimal(outcome.product.payload["coverage"]["coverage_ratio"])


@pytest.fixture(scope="module")
def default(estate: tuple[str, str], example: tuple[Any, Any]) -> Any:
    return _serve(example)


# --- the six measured behaviors, as RELATIONSHIPS ----------------------------


def test_haircuts_reduce_coverage(estate: tuple[str, str], example: tuple[Any, Any],
                                  default: Any) -> None:
    """A haircut is a discount, so applying one cannot raise coverage.

    Directional rather than pinned: the estate's haircut schedule is policy and
    will change. What must never change is the sign — if applying haircuts ever
    raised coverage, the schedule would be being read as a premium.
    """
    gross = _serve(example, apply_haircuts=False)
    assert _ratio(gross) > _ratio(default), (
        "applying haircuts did not reduce coverage; the discount is being"
        " applied in the wrong direction or not at all"
    )


def test_valid_setoff_increases_coverage(estate: tuple[str, str],
                                         example: tuple[Any, Any],
                                         default: Any) -> None:
    """Deposits the bank may apply are additional recovery, never a deduction."""
    without = _serve(example, include_setoff=False)
    assert _ratio(default) > _ratio(without)
    assert Decimal(
        without.product.payload["coverage"]["setoff_value"]) == Decimal(0), (
        "set-off was excluded and still contributed value"
    )


def test_contractual_basis_counts_more_setoff_than_enforceable(
    estate: tuple[str, str], example: tuple[Any, Any], default: Any
) -> None:
    """`contractual` is a superset of `enforceable`, so it cannot count less.

    Returning contractual rights as though they were enforceable OVERSTATES
    coverage — which is the point of the parameter, and the reason the default
    is the conservative one.
    """
    contractual = _serve(example, jurisdiction_basis="contractual")
    assert Decimal(contractual.product.payload["coverage"]["setoff_value"]) >= (
        Decimal(default.product.payload["coverage"]["setoff_value"]))
    assert _ratio(contractual) >= _ratio(default)
    assert default.product.payload["findings"][
        "setoff_excluded_as_unenforceable"] > 0, (
        "no deposit was excluded as unenforceable, so this comparison could not"
        " have measured the basis at all"
    )


def test_priority_and_pro_rata_disagree_on_a_shared_asset(
    estate: tuple[str, str], example: tuple[Any, Any], default: Any
) -> None:
    """The two allocation bases must produce different answers, or the graph
    carried no shared asset and the product proved nothing.

    Which is larger is NOT asserted: it depends on whether the anchor holds the
    senior position, which is a fact about the estate rather than about the
    code. What must hold is that they differ, and that the difference is
    attributable to an asset with another claimant.
    """
    assert default.product.payload["findings"]["shared_assets"] > 0, (
        "no asset is shared with another facility, so allocation basis cannot"
        " matter and this example is not demonstrating its own subject"
    )
    pro_rata = _serve(example, shared_collateral="pro-rata")
    assert _ratio(pro_rata) != _ratio(default)


def test_the_register_reports_a_released_lien(estate: tuple[str, str],
                                              example: tuple[Any, Any]) -> None:
    """The MasTec case: a lien the contract layer calls secured and the public
    register says was RELEASED.

    The filing numbers and dates are not pinned — the register is live and
    `ccf-dataprep` may load more. What is asserted is the shape: at least one
    filing reached, and at least one carrying a Termination whose date is a
    parseable ISO-8601 string. Dates in this layer are untyped strings by
    necessity (the Fluree build corrupts `^^xsd:date` on write), so a test that
    cast them would be testing the wrong thing.
    """
    deployment, produce = example
    asked = deployment.request(
        facility_id="FAC-102496", borrower_scope=["549300TMDIT8WREDOF45"],
        asked_at=datetime.now(UTC))
    with tempfile.TemporaryDirectory() as scratch:
        served = produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))

    filings = served.product.payload["ucc_filings"]
    assert filings, "the register reached no filing for this debtor"
    released = [f for f in filings if "Termination" in f["amendment_actions"]]
    assert released, "no filing carries a Termination; the contrast is not demonstrated"
    assert served.product.payload["findings"]["terminated_liens"] == len(released)
    for filing in filings:
        # ISO-8601 sorts lexicographically, which is why string comparison is
        # correct here and casting is not.
        assert filing["filed_on"] and filing["filed_on"][:4].isdigit()


def test_mastec_is_under_covered(estate: tuple[str, str],
                                 example: tuple[Any, Any]) -> None:
    """One engineered receivable against a $600m commitment cannot cover it."""
    deployment, produce = example
    asked = deployment.request(
        facility_id="FAC-102496", borrower_scope=["549300TMDIT8WREDOF45"],
        asked_at=datetime.now(UTC))
    with tempfile.TemporaryDirectory() as scratch:
        served = produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))
    assert _ratio(served) < Decimal(1)
    assert Decimal(served.product.payload["coverage"]["shortfall"]) > 0


# --- what the product must keep carrying -------------------------------------


def test_valuation_dates_are_per_asset_and_not_flattened(default: Any) -> None:
    """§6.4 refuses to let a one-day mark and a one-year appraisal collapse."""
    assets = default.product.payload["assets"]
    assert assets
    for asset in assets:
        assert asset["valuation_date"], f"{asset['uri']} carries no valuation date"
        assert isinstance(asset["valuation_age_days"], int)


def test_priority_is_carried_on_the_facility_asset_pair(default: Any) -> None:
    """Priority belongs to the PAIR, and the payload says so per claimant.

    An asset shared at differing priority is the case a collateral column
    cannot express; if the payload reported one position per ASSET it would
    have reintroduced exactly that flattening.
    """
    shared = [a for a in default.product.payload["assets"] if a["shared_with"]]
    assert shared, "no shared asset in the served payload"
    for asset in shared:
        assert asset["allocation_basis"], "a shared asset with no allocation basis"


def test_source_ids_are_served_for_business_matching(default: Any) -> None:
    """A payload speaking only in content hashes cannot be joined to anything."""
    for asset in default.product.payload["assets"]:
        assert not asset["uri"].startswith("collateral_node://"), (
            "the payload serves a fabric URI where the source's own id belongs"
        )


def test_the_over_allocation_gate_is_declared_and_identified(
    example: tuple[Any, Any]
) -> None:
    """A gate with no declared identity gives replay nothing to name.

    The SDK refuses that pairing outright, so this asserts the declaration
    rather than the behavior: the id and version are the Control Plane's half.
    """
    deployment, _ = example
    declared = deployment.config()["product_class"]["declared_product_gate"]
    assert declared["gate_id"] and declared["gate_version"]


def test_replay_dimension_two_carries_the_request_contract(default: Any) -> None:
    """`D-IMPL-310` — replay is a SUPERSET of product policy lineage."""
    bindings = {b.key for b in default.record.policy_bindings.bindings}
    lineage = set(default.product.lineage.policy_bundle_versions)
    versions = {b.version for b in default.record.policy_bindings.bindings}
    assert "request_contract" in bindings
    assert lineage <= versions


def test_the_structural_classifier_reads_this_tree_as_canonical() -> None:
    """`shape_of` is structural — it asks the code, never a roster."""
    spec = importlib.util.spec_from_file_location(
        "_sep", REPO_ROOT / "tests" / "examples" / "test_spine_separation.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.shape_of(EXAMPLE) == "canonical"
    assert module.resolver_ownership(EXAMPLE)
    assert module.governed_seam_calls(EXAMPLE) == {}
    assert module.legacy_governance_regions(EXAMPLE) == []


def test_the_plan_factory_takes_its_operators_only_from_required() -> None:
    """`D-IMPL-137` row C, read off the tree by the SDK's own predicate."""
    spec = importlib.util.spec_from_file_location(
        "_gate2", REPO_ROOT / "tests" / "products" / "test_gate_two_call_shape.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    path = EXAMPLE / "produce.py"
    factory = next(
        n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(n, ast.FunctionDef) and n.name == "plan_factory")
    assert module._sdk_supplied_operator_set(factory, path)
    assert module._constructed_plan_sources(factory, None) == (("required",),)


def test_the_door_declares_its_entrypoint_rather_than_a_script_path() -> None:
    """A consumer asks for a product; it does not learn how the producer starts.

    A client carrying `python examples/…/serve.py` is bound to this
    deployment's directory layout, interpreter and language — none of which is
    part of the product contract.
    """
    import yaml  # noqa: PLC0415

    declared = yaml.safe_load(
        (EXAMPLE / "server" / "door.yaml").read_text(encoding="utf-8"))["declaration"]
    entrypoint = declared["serve_entrypoint"]
    assert ":" in entrypoint, "the entry point is not a module:callable reference"
    assert not entrypoint.endswith(".py"), "the binding names a script path"
    module_name, _, callable_name = entrypoint.partition(":")
    source = (EXAMPLE / "server" / f"{module_name}.py").read_text(encoding="utf-8")
    assert f"def {callable_name}(" in source, (
        f"door.yaml names {entrypoint!r} and that callable does not exist"
    )
