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
from datetime import UTC, datetime, timedelta
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


def _serve(example: tuple[Any, Any], *, asked_at: datetime | None = None,
           **kwargs: Any) -> Any:
    """One run of the demonstration facility, in its own scratch fabric.

    ``asked_at`` defaults to now. A determinism comparison must PIN it: the
    decision instant is part of the determination — it sets the product's
    expiry — so two serves a millisecond apart are two different questions and
    correctly reach two different content addresses.
    """
    deployment, produce = example
    asked = deployment.request(
        facility_id=_anchor("DEMONSTRATION_FACILITY"),
        borrower_scope=[_anchor("DEMONSTRATION_SCOPE")],
        asked_at=asked_at or datetime.now(UTC), **kwargs)
    with tempfile.TemporaryDirectory() as scratch:
        return produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))


def _ratio(outcome: Any) -> Decimal:
    return Decimal(outcome.product.payload["coverage"]["coverage_ratio"])


@pytest.fixture(scope="module")
def default(estate: tuple[str, str], example: tuple[Any, Any]) -> Any:
    return _serve(example)


# --- the six measured behaviors, as RELATIONSHIPS ----------------------------


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_haircuts_reduce_coverage(estate: tuple[str, str], example: tuple[Any, Any],
                                  default: Any) -> None:
    """A haircut is a discount, so applying one cannot raise coverage.

    Directional rather than pinned: the estate's haircut schedule is policy and
    will change. What must never change is the sign — if applying haircuts ever
    raised coverage, the schedule would be being read as a premium.

    Declared product gate `CSC-G01` (`CP-SPEC-006` §G.2).
    """
    gross = _serve(example, apply_haircuts=False)
    assert _ratio(gross) > _ratio(default), (
        "applying haircuts did not reduce coverage; the discount is being"
        " applied in the wrong direction or not at all"
    )


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_valid_setoff_increases_coverage(estate: tuple[str, str],
                                         example: tuple[Any, Any],
                                         default: Any) -> None:
    """Deposits the bank may apply are additional recovery, never a deduction.

    Declared product gate `CSC-G02` (`CP-SPEC-006` §G.2).
    """
    without = _serve(example, include_setoff=False)
    assert _ratio(default) > _ratio(without)
    assert Decimal(
        without.product.payload["coverage"]["setoff_value"]) == Decimal(0), (
        "set-off was excluded and still contributed value"
    )


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_contractual_basis_counts_more_setoff_than_enforceable(
    estate: tuple[str, str], example: tuple[Any, Any], default: Any
) -> None:
    """`contractual` is a superset of `enforceable`, so it cannot count less.

    Returning contractual rights as though they were enforceable OVERSTATES
    coverage — which is the point of the parameter, and the reason the default
    is the conservative one.

    Declared product gate `CSC-G03` (`CP-SPEC-006` §G.2).
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


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_priority_and_pro_rata_disagree_on_a_shared_asset(
    estate: tuple[str, str], example: tuple[Any, Any], default: Any
) -> None:
    """The two allocation bases must produce different answers, or the graph
    carried no shared asset and the product proved nothing.

    Which is larger is NOT asserted: it depends on whether the anchor holds the
    senior position, which is a fact about the estate rather than about the
    code. What must hold is that they differ, and that the difference is
    attributable to an asset with another claimant.

    Declared product gate `CSC-G04` (`CP-SPEC-006` §G.2).
    """
    assert default.product.payload["findings"]["shared_assets"] > 0, (
        "no asset is shared with another facility, so allocation basis cannot"
        " matter and this example is not demonstrating its own subject"
    )
    pro_rata = _serve(example, shared_collateral="pro-rata")
    assert _ratio(pro_rata) != _ratio(default)


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
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

    Declared product gate `CSC-G05` (`CP-SPEC-006` §G.2).
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


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_mastec_is_under_covered(estate: tuple[str, str],
                                 example: tuple[Any, Any]) -> None:
    """One engineered receivable against a $600m commitment cannot cover it.

    Declared product gate `CSC-G06` (`CP-SPEC-006` §G.2).
    """
    deployment, produce = example
    asked = deployment.request(
        facility_id="FAC-102496", borrower_scope=["549300TMDIT8WREDOF45"],
        asked_at=datetime.now(UTC))
    with tempfile.TemporaryDirectory() as scratch:
        served = produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))
    assert _ratio(served) < Decimal(1)
    assert Decimal(served.product.payload["coverage"]["shortfall"]) > 0


# --- what the product must keep carrying -------------------------------------


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_valuation_dates_are_per_asset_and_not_flattened(default: Any) -> None:
    """§6.4 refuses to let a one-day mark and a one-year appraisal collapse.

    Declared product gate `CSC-G07` (`CP-SPEC-006` §G.2).
    """
    assets = default.product.payload["assets"]
    assert assets
    for asset in assets:
        assert asset["valuation_date"], f"{asset['uri']} carries no valuation date"
        assert isinstance(asset["valuation_age_days"], int)


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_priority_is_carried_on_the_facility_asset_pair(default: Any) -> None:
    """Priority belongs to the PAIR, and the payload says so per claimant.

    An asset shared at differing priority is the case a collateral column
    cannot express; if the payload reported one position per ASSET it would
    have reintroduced exactly that flattening.

    Declared product gate `CSC-G08` (`CP-SPEC-006` §G.2).
    """
    shared = [a for a in default.product.payload["assets"] if a["shared_with"]]
    assert shared, "no shared asset in the served payload"
    for asset in shared:
        assert asset["allocation_basis"], "a shared asset with no allocation basis"


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_source_ids_are_served_for_business_matching(default: Any) -> None:
    """A payload speaking only in content hashes cannot be joined to anything.

    Declared product gate `CSC-G09` (`CP-SPEC-006` §G.2).
    """
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

    Declared product gate `CSC-G10` (`CP-SPEC-006` §G.2).
    """
    deployment, _ = example
    declared = deployment.config()["product_class"]["declared_product_gate"]
    assert declared["gate_id"] and declared["gate_version"]


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_replay_dimension_two_carries_the_request_contract(default: Any) -> None:
    """`D-IMPL-310` — replay is a SUPERSET of product policy lineage.

    Declared product gate `CSC-G11` (`CP-SPEC-006` §G.2).
    """
    bindings = {b.key for b in default.record.policy_bindings.bindings}
    lineage = set(default.product.lineage.policy_bundle_versions)
    versions = {b.version for b in default.record.policy_bindings.bindings}
    assert "request_contract" in bindings
    assert lineage <= versions


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_the_spec_step_table_names_exactly_the_registered_operators(
    example: tuple[Any, Any], default: Any
) -> None:
    """The step table is the document a reader counts operators in, so it has to
    agree with the declaration and with the lineage.

    **This test exists because the table did not.** As shipped at
    `D-GATE-cp-06` it named `traversal.typed-neighborhood` on all three FLUREE
    rows — those are acquisition reads, source access at L1 — and omitted
    `policy.principal-subgraph` entirely, so the column showed one registered
    operator where the product invokes two. It contradicted §D.2.1 one paragraph
    below it and contradicted `operators_invoked`, and nothing was checking. The
    identical defect was in `CP-SPEC-007` §D.2 and both were corrected together.

    Read structurally off the markdown rather than by substring: the Operator
    column only, split on the table's own pipes. A token elsewhere in the row —
    a store name, a prose mention — is not a claim about which operator ran.
    """
    import re  # noqa: PLC0415

    deployment, _ = example
    declared = set(deployment.config()["product_class"]["required_operator_keys"])
    assert declared, "the deployment declares no operators; this proves nothing"

    spec = next((EXAMPLE / "spec").glob("CP-SPEC-006*.md")).read_text(encoding="utf-8")
    table = spec.split("### D.2 Step table", 1)[1].split("###", 1)[0]

    named: set[str] = set()
    for line in table.splitlines():
        cells = [c.strip() for c in line.split("|")]
        # `| # | Step | Operator | Store | Emits | Budget |` -> leading empty
        # cell, so the Operator column is index 3. cp-06 numbers some rows `3a`,
        # so the step cell is tested for a leading digit rather than `isdigit`.
        if len(cells) < 7 or not cells[1][:1].isdigit():
            continue
        named.update(re.findall(r"`([a-z]+\.[a-z-]+)`", cells[3]))

    assert named == declared, (
        f"the §D.2 step table names {sorted(named)} in its Operator column and"
        f" the product class declares {sorted(declared)}; the table a reader"
        " counts operators in disagrees with the one the fabric invokes"
    )

    # THE SERVED LINEAGE IS THE THIRD WITNESS, so agreement cannot be two
    # documents copied from each other.
    assert named == set(default.product.lineage.operators_invoked), (
        f"the step table names {sorted(named)} and the served product's"
        f" `operators_invoked` carries"
        f" {sorted(default.product.lineage.operators_invoked)}"
    )


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_the_policy_operator_discriminates_rather_than_passing_through(
    estate: tuple[str, str], example: tuple[Any, Any], default: Any
) -> None:
    """A scope the caller does not hold yields an EMPTY graph, not a redacted one.

    Without this, `policy.principal-subgraph` could be declared, invoked,
    recorded in lineage, and admit everything — an operator present in the audit
    trail and absent from the answer. §D.2 now carries the measured contrast and
    this holds the document to it.
    """
    deployment, produce = example
    asked = deployment.request(
        facility_id=_anchor("DEMONSTRATION_FACILITY"),
        borrower_scope=["A-SCOPE-NOBODY-HOLDS"], asked_at=datetime.now(UTC))
    with tempfile.TemporaryDirectory() as scratch:
        denied = produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))

    assert default.product.payload["assets"], "the entitled read returned nothing"
    assert denied.product.payload["assets"] == []
    assert Decimal(denied.product.payload["coverage"]["coverage_ratio"]) == 0


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

    Declared product gate `CSC-G12` (`CP-SPEC-006` §G.2).
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


# --- CP-SPEC-006 conformance: the clauses the six behaviors do not cover ------


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_spec_d5_replay_same_parameters_reach_the_same_address(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """`CP-SPEC-006` §D.5 steps 1-3, and the reason Assembly Mode 1 is declared.

    Two serves of one question against one estate state must agree byte for
    byte. Anything else means something non-deterministic reached the payload,
    which is the claim `assembly_mode: algorithmic` makes at registration time.
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415

    # PINNED, and the pin is the point: the decision instant sets the expiry
    # and therefore enters the address, so determinism is a claim about one
    # question rather than about two moments.
    instant = datetime.now(UTC)
    first = _serve(example, asked_at=instant)
    second = _serve(example, asked_at=instant)
    assert content_hash(first.product) == content_hash(second.product)

    # And the control: the SAME question at a DIFFERENT instant is a different
    # determination. Without this the assertion above would also pass against a
    # product that ignored time entirely.
    later = _serve(example, asked_at=instant + timedelta(hours=1))
    assert content_hash(later.product) != content_hash(first.product)


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_spec_d5_one_changed_parameter_moves_the_payload_not_the_read(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """`CP-SPEC-006` §D.5 step 4 — the clause that proves where the work happens.

    `shared_collateral` is applied at Π, so changing it must change the content
    address while leaving the operator plan identical. If the plan moved, the
    parameter would be conditioning the graph read, and every allocation basis
    would compile to a different query — which is the naive-projection defect
    the SDK records elsewhere.
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415

    instant = datetime.now(UTC)
    baseline = _serve(example, asked_at=instant)
    pro_rata = _serve(example, asked_at=instant, shared_collateral="pro-rata")
    assert content_hash(pro_rata.product) != content_hash(baseline.product)
    assert sorted(pro_rata.record.content_generation_path.operator_plan) == sorted(
        baseline.record.content_generation_path.operator_plan
    ), "the allocation basis changed the READ; it must change only the payload"


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_spec_b1_lineage_carries_exactly_the_two_declared_operators(
    default: Any, example: tuple[Any, Any]
) -> None:
    """`CP-SPEC-006` §B.1(5) and §D.2.1.

    The vault article lists five verbs; only two are registered L4 operators on
    this SDK. A step carrying a Standard verb that is not a registered operator
    must NOT enter `operators_invoked`, or lineage strict equality would be
    sealing a document that claims work no operator did.
    """
    deployment, _ = example
    declared = tuple(deployment.config()["product_class"]["required_operator_keys"])
    assert sorted(default.record.content_generation_path.operator_plan) == sorted(declared)
    assert len(declared) == 2


@pytest.mark.xfail(strict=True, reason="`D-IMPL-341` (validation pass 2026-09-18): the frozen cp-06 declares `ttl_anchor: from_entity_freshness` over a resolver wired with its own `debt_scorer` and no lambda_c table the SDK can read, so every serve is refused `ttl-anchor-refusal` / `ttl-anchor-unresolvable` (R-3, no fallback) — quarantined evidence of the SDK's evolution, `D-IMPL-261`; the specimen is not edited")
def test_spec_c3_unresolved_debtor_names_are_served_not_hidden(default: Any) -> None:
    """`CP-SPEC-006` §C.3 — the register keys on name, the fabric keys on LEI.

    The crosswalk's match is a claim with a score, never filed fact. Names it
    could not resolve are REPORTED: measured, 15 of 16 filed names resolve to
    no LEI, several visibly subsidiaries of the one that does. Hiding them
    would make an entity-resolution gap look like an absence of liens.
    """
    assert len(default.coverage.unresolved_debtors) > 0
