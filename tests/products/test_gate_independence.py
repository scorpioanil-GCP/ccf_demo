"""D-15A — the two inputs to ``run_gates`` stay separately assembled.

Whitepaper §7.6 / INV-CH7-47 (lineage strict equality); CLAUDE.md §6.4 and §10
for the SDK-defined ``ccf.deployment`` package this guards. Written *before* the
first ergonomics helper exists, so it is a standing constraint on what may be
written rather than a retrofit around what already was.

The risk it exists for: :func:`ccf.products.gates.run_gates` compares the
product's declared ``lineage.operators_invoked`` — the Control Plane claim, as
transcribed into the Contract — against the projection engine's
``engine_resolved``. What that comparison verifies is **assembly-path
integrity**, not independent witness: the engine builds ``operators_invoked``
and ``steps`` in one loop over the same operator plan, so it is a faithful
transcriber of the plan (``D-IMPL-86``; the ``D-IMPL-57`` correction of
2026-08-05). The comparison is a check only while the two arguments are
*separately assembled by the deployment*. A convenience helper that derived
both from one input would leave nothing to compare at all — not even a
transcription — so the gate would compare a value against itself: still green,
permanently uninformative, and a whitepaper invariant deleted with no failing
test to say so. **Authorable** drift is refused upstream instead, by
:func:`ccf.deployment.binder.refuse_operator_set_divergence`.

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

**The adopter-code gap named above is now covered, partly.** CR-2 found the
caller passing the same value twice at all nine gate call sites in the SDK's
own example suite, and ``tests/products/test_gate_two_call_shape.py``
(Phase 15.1, D-IMPL-86 element (5)) is the tripwire for it: one lexical body at
a time, it refuses a ``run_gates`` call whose ``engine_resolved`` and a
``ProductLineage`` whose ``operators_invoked`` resolve to the same identifier
path, following each local name to the binding in force *at the source position
that reads it* — ``(line, column)`` and not a line, because two statements
separated by a semicolon and a compound statement's one-line suite each share a
line with the binding they are supposed to be after; and not to a fixed point,
which is what the first predecessor did and what hung on a three-name rotation.

What it still cannot see is **kept in that module and not restated here**, on
purpose: its two limits lists (tripwire (1)'s and tripwire (2)'s) are the
maintained ones, they are explicitly non-exhaustive, and a second copy here
would be a copy that drifts. Three from them are worth naming at this seam
because they bound *this* module's sentence too — a value arriving through a
helper's return value, a container, or dynamic attribute access; a rebinding
carried around a loop, which executes before it is written; and D-IMPL-86's
structural limit, that an authored literal is textually identical to a
transcribed one. The sentence above is amended in reach, not withdrawn.

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
from ccf.products.gates import (
    PYDANTIC_MODEL_FORMS,
    GateBypassError,
    LineageMismatchRefusal,
    ServableProduct,
    ServableProductNotAModel,
    run_gates,
)
from tests.composition import register_at_composition

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
    version = register_at_composition(registry, MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
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


# --- (5) the refusal that states *why* a product is unconstructible ----------
#
# `D-IMPL-126` item (2). Before this, `ServableProduct.model_construct(...)` and
# `servable.model_copy()` each gave a bare `AttributeError`, which a first-time
# reader reads as a pydantic version problem and takes into SDK source to
# diagnose. The type is not a pydantic model on purpose — it is the token that
# proves the three gates ran (INV-CH7-52) — and it now says so.
#
# Parametrized over the enumerated forms **times the two attribute channels**,
# so adding a spelling to the frozenset adds two cases rather than one. A
# metaclass `__getattr__` alone covers the class channel and leaves the instance
# channel bare, and `model_copy`/`model_dump`/`parse_obj` are *instance* methods
# in pydantic — exactly what a reader holding a returned object reaches for.

#: A name no pydantic surface has ever carried — the negative control. The
#: refusal must be scoped to the enumerated forms and must not swallow a typo.
UNRELATED_ATTRIBUTE = "no_such_attribute_at_all"


def _servable() -> ServableProduct:
    """A real ``ServableProduct``, minted the only way one can be."""
    registry = _registry()
    product_class = _product_class(registry)
    admitted = run_gates(
        _candidate(product_class, DECLARED),
        engine_resolved=DECLARED,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(admitted, ServableProduct)
    return admitted


def test_the_enumerated_forms_cover_the_spellings_a_reader_reaches_for() -> None:
    """Enumerated once, exhaustively — the ``CONTAINER_FORMS`` precedent.

    A language's forms are listed in one place rather than discovered one
    instance at a time, so a v1 spelling and a v2 spelling cannot be closed on
    different days.
    """
    for form in (
        "model_construct",
        "model_validate",
        "model_validate_json",
        "model_validate_strings",
        "model_copy",
        "model_dump",
        "construct",
        "parse_obj",
        "parse_raw",
        "parse_file",
        "from_orm",
    ):
        assert form in PYDANTIC_MODEL_FORMS


@pytest.mark.parametrize("form", sorted(PYDANTIC_MODEL_FORMS))
def test_the_class_channel_refuses_every_enumerated_form(form: str) -> None:
    """``ServableProduct.<form>`` states why, naming the gate path and INV."""
    with pytest.raises(GateBypassError) as raised:
        getattr(ServableProduct, form)

    message = str(raised.value)
    assert "run_gates" in message
    assert "INV-CH7-52" in message
    assert form in message


@pytest.mark.parametrize("form", sorted(PYDANTIC_MODEL_FORMS))
def test_the_instance_channel_refuses_every_enumerated_form(form: str) -> None:
    """The channel a reader is *most* likely to hit and least likely covered.

    A metaclass ``__getattr__`` does not run for instance attribute lookup, so
    without a second ``__getattr__`` on the class itself this is the bare
    ``AttributeError`` the whole fix exists to remove.
    """
    servable = _servable()

    with pytest.raises(GateBypassError) as raised:
        getattr(servable, form)

    message = str(raised.value)
    assert "run_gates" in message
    assert "INV-CH7-52" in message
    assert form in message


def test_the_refusal_is_both_a_gate_bypass_and_an_attribute_error() -> None:
    """The dual inheritance, asserted as inheritance rather than as behaviour.

    ``GateBypassError`` subclasses ``TypeError``. A refusal deriving from it
    alone makes ``hasattr`` **raise** instead of returning ``False``, which is a
    hazard this fix would have created. Deriving from ``AttributeError`` as well
    keeps a duck-type probe degrading while ``except GateBypassError`` still
    catches.
    """
    assert issubclass(ServableProductNotAModel, GateBypassError)
    assert issubclass(ServableProductNotAModel, AttributeError)


@pytest.mark.parametrize("form", sorted(PYDANTIC_MODEL_FORMS))
def test_a_duck_type_probe_degrades_rather_than_exploding(form: str) -> None:
    """``hasattr`` is ``False`` and ``getattr(..., None)`` is ``None``.

    On both channels: a probe against the class and a probe against a returned
    instance must each answer rather than raise.
    """
    servable = _servable()

    assert hasattr(ServableProduct, form) is False
    assert hasattr(servable, form) is False
    assert getattr(ServableProduct, form, None) is None
    assert getattr(servable, form, None) is None


def test_an_unrelated_name_raises_a_plain_attribute_error_on_the_class() -> None:
    """The negative control: the refusal is scoped and swallows no typo."""
    with pytest.raises(AttributeError) as raised:
        getattr(ServableProduct, UNRELATED_ATTRIBUTE)

    assert not isinstance(raised.value, GateBypassError)
    assert "INV-CH7-52" not in str(raised.value)


def test_an_unrelated_name_raises_a_plain_attribute_error_on_an_instance() -> None:
    """The same negative control on the channel the class one cannot reach."""
    servable = _servable()

    with pytest.raises(AttributeError) as raised:
        getattr(servable, UNRELATED_ATTRIBUTE)

    assert not isinstance(raised.value, GateBypassError)
    assert "INV-CH7-52" not in str(raised.value)


def test_run_gates_still_mints_and_a_wrong_token_still_refuses() -> None:
    """Neither ``__getattr__`` added a construction path.

    Attribute *lookup* only: ``__init__``'s token check is untouched and no
    ``__call__`` is overridden, so the only way to hold one of these is still
    the gate sequence.
    """
    servable = _servable()
    assert isinstance(servable, ServableProduct)
    assert servable.product.lineage.operators_invoked == DECLARED

    with pytest.raises(GateBypassError):
        ServableProduct(servable.product, object())


def test_the_real_members_are_untouched_by_the_refusal() -> None:
    """``.product`` resolves normally — ``__getattr__`` runs only on a miss."""
    servable = _servable()
    assert isinstance(servable.product, ContextProductContract)
    assert hasattr(servable, "product") is True
