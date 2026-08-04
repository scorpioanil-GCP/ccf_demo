"""D-15A — the two inputs to ``run_gates`` stay independently sourced.

Whitepaper §7.6 / INV-CH7-47 (lineage strict equality); CLAUDE.md §6.4 and §10
for the SDK-defined ``ccf.deployment`` package this guards. Written *before* the
first ergonomics helper exists, so it is a standing constraint on what may be
written rather than a retrofit around what already was.

The risk it exists for: :func:`ccf.products.gates.run_gates` compares the
product's declared ``lineage.operators_invoked`` against the projection engine's
``engine_resolved``. The comparison is a real check only because those two
values arrive from two independent sources. A convenience helper that derived
both from one input would make the gate compare a value against itself — still
green, permanently uninformative, and a whitepaper invariant deleted with no
failing test to say so.

**What these tests enforce, exactly.**

1. Perturbing ``engine_resolved`` away from the product's declared lineage
   produces a :class:`~ccf.products.gates.LineageMismatchRefusal`, and passing
   the declared set unchanged produces a
   :class:`~ccf.products.gates.ServableProduct`. Together: the gate has two
   inputs and something real to check between them.
2. No module shipped under ``src/ccf/deployment/`` *names* ``run_gates``,
   ``ProductLineage``, or ``engine_resolved`` as an identifier.
3. No public callable exported from those modules has a signature mentioning
   both a lineage-shaped and an execution-shaped type — that signature *is* the
   collapse, whatever it is named.
4. The discovery glob found at least one module and ``ccf.deployment`` imports.

**What they do not enforce.** They do not prove the projection engine computed
``operators_invoked`` correctly — only that the gate refuses a mismatch it is
given. They do not cover adopter code outside ``ccf.deployment``, where gate
execution actually lives and where a caller is free to pass the same value
twice. And (2) is an identifier scan: a collapse expressed entirely through
dynamic attribute access — ``getattr(module, "run_" + "gates")`` — is outside
what an AST identifier walk can see. Those are the strengths these assertions
reach; the I.2 retrospective flagged overclaiming in exactly this test class.

The lint rule ``cinv02-deployment-gates`` in ``tools/lints/harness_imports.py``
is this module's paired mechanism, not its duplicate: the lint refuses the
*import*, these tests refuse the *shape*.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import pathlib
import re
from datetime import UTC, datetime, timedelta

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import LineageMismatchRefusal, ServableProduct, run_gates

# Fixture values (test-side vocabulary, never SDK values).
TENANT = "tenant-fixture"
MAX_TTL_KEY = "test/gate-independence/max-ttl"
MAX_TTL_SECONDS = 900
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
POLICY_VERSION = "policy-version-fixture"
DECLARED = frozenset(
    {"policy.principal-subgraph", "traversal.typed-neighborhood", "temporal.as-of"}
)

#: The package this guard is aimed at, and every module file it ships.
DEPLOYMENT_ROOT = (
    pathlib.Path(__file__).resolve().parents[2] / "src" / "ccf" / "deployment"
)
DEPLOYMENT_SOURCES = sorted(DEPLOYMENT_ROOT.rglob("*.py"))

#: Identifiers whose appearance inside ``ccf.deployment`` would mean the package
#: had reached into gate execution.
FORBIDDEN_IDENTIFIERS = frozenset(
    {"run_gates", "ProductLineage", "engine_resolved"}
)

#: The two shapes that must never meet in one signature.
LINEAGE_NAMES = frozenset({"ProductLineage"})
EXECUTION_NAMES = frozenset({"ProjectionExecution"})


# --- helpers ------------------------------------------------------------------


def _identifiers(source: str) -> set[str]:
    """Every name and attribute identifier appearing in ``source``.

    Identifiers, never source text. A text scan cannot tell a violation from a
    docstring that documents compliance — and ``ccf.deployment``'s own package
    docstring names ``run_gates`` and ``engine_resolved`` as its worked example,
    so a grep-based guard would fail on the very documentation that records
    compliance. String constants are not identifiers, so they are outside this
    set and cannot trip it, and a genuine use *is* an identifier and cannot
    escape it.
    """
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.rsplit(".", 1)[-1])
    return names


def _annotation_names(annotation: object) -> set[str]:
    """The bare type names an annotation mentions, as whole tokens.

    Whole tokens rather than substrings, so the assertion does not depend on how
    a future type happens to be spelled. Annotations may be strings
    (``from __future__ import annotations`` is house style), so this reads them
    as text and splits on non-identifier characters rather than resolving them.
    """
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(annotation)))


def _module_name(path: pathlib.Path) -> str:
    """``src/ccf/deployment/x/y.py`` → ``ccf.deployment.x.y``."""
    relative = path.relative_to(DEPLOYMENT_ROOT.parents[1])
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


def _product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
    return register_product_class(
        registry=registry,
        schema_name="fixture.gate-independence",
        schema_version="1.0.0",
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=MAX_TTL_KEY,
        max_ttl_version=version,
    )


def _candidate(
    product_class: RegisteredProductClass, operators: frozenset[str]
) -> ContextProductContract:
    return ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id="fixture.plan",
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=NOW + timedelta(seconds=60),
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=operators,
            policy_bundle_versions=frozenset({POLICY_VERSION}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload={},
    )


# --- (1) the perturbation regression ------------------------------------------


def test_perturbing_engine_resolved_is_refused_and_the_declared_set_is_not() -> None:
    """Two inputs, two sources — proven by moving one and not the other.

    Dropping a single operator from ``engine_resolved`` while the product's
    declared lineage is unchanged must refuse. The mirror case — the same
    declared set passed through untouched — must be servable. Either half alone
    is weak: a gate that always refuses passes the first, a gate that always
    admits passes the second, and only the pair says the comparison is live.
    """
    registry = _registry()
    product_class = _product_class(registry)
    candidate = _candidate(product_class, DECLARED)
    perturbed = frozenset(sorted(DECLARED)[:-1])
    assert perturbed != DECLARED

    refused = run_gates(
        candidate,
        engine_resolved=perturbed,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(refused, LineageMismatchRefusal)
    assert refused.declared == DECLARED
    assert refused.resolved == perturbed

    admitted = run_gates(
        candidate,
        engine_resolved=DECLARED,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(admitted, ServableProduct)
    assert admitted.product.lineage.operators_invoked == DECLARED


# --- (2) no module under ccf.deployment names the gate ------------------------


@pytest.mark.parametrize("source_path", DEPLOYMENT_SOURCES, ids=lambda p: p.name)
def test_no_deployment_module_names_the_gate(source_path: pathlib.Path) -> None:
    """Gate execution stays in adopter code; this package may not name it."""
    named = _identifiers(source_path.read_text(encoding="utf-8"))
    offending = named & FORBIDDEN_IDENTIFIERS
    assert not offending, (
        f"{source_path.name} names {sorted(offending)} as an identifier;"
        " ccf.deployment wires a deployment together and does not run its"
        " validation gates (D-15A; lineage strict equality, whitepaper §7.6)"
    )


# --- (3) no signature holds both shapes ---------------------------------------


@pytest.mark.parametrize("source_path", DEPLOYMENT_SOURCES, ids=lambda p: p.name)
def test_no_deployment_callable_takes_both_shapes(
    source_path: pathlib.Path,
) -> None:
    """One function producing a lineage *from* an execution record is the
    collapse itself — the two values would then have one source."""
    module = importlib.import_module(_module_name(source_path))
    for name in getattr(module, "__all__", []):
        obj = getattr(module, name, None)
        if not callable(obj):
            continue
        try:
            signature = inspect.signature(obj)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            continue
        mentioned: set[str] = set()
        for parameter in signature.parameters.values():
            mentioned |= _annotation_names(parameter.annotation)
        mentioned |= _annotation_names(signature.return_annotation)
        assert not (mentioned & LINEAGE_NAMES and mentioned & EXECUTION_NAMES), (
            f"{_module_name(source_path)}.{name} mentions both a"
            " lineage-shaped and an execution-shaped type; that signature"
            " gives run_gates's two inputs one source (D-15A)"
        )


# --- (4) the scan is only worth anything if it scanned something --------------


def test_the_deployment_package_was_actually_discovered() -> None:
    """A discovery helper that silently returned nothing is the quietest way an
    invariant test stops being one — every parametrized assertion above would go
    vacuously green while staying green."""
    assert DEPLOYMENT_ROOT.is_dir()
    assert len(DEPLOYMENT_SOURCES) >= 1
    module = importlib.import_module("ccf.deployment")
    assert module.__ccf_mode__ == "algorithmic"
