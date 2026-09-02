"""The empty-operator gate's two halves, by name — ledger row ``24.5-L-24``.

Two assertions shared the name ``empty-operator-guard``: the SDK's — a product
that DECLARED no operators (whitepaper §7.6, INV-CH7-46) — and the Standard's
— an operator that RETURNED an empty set, which nothing in ``src/`` said a
word about while cp-00's ``IH-G07`` and cp-01's ``CPR-G08`` carried it as
product gates. ``D-IMPL-238``'s second sentence unlocked exactly that half.
This module measures, on every run, that the two halves are two NAMED
structural gates in :mod:`ccf.products.gates`, adjacent in both runners with
the declared half first, each refusing by its own token — and that each is
provably red under its own sabotage.

What is proven, and by which test (criterion 23):

* **The declared half** refuses a product with ``operators_invoked == ∅`` by
  ``empty-operator-guard`` — :func:`ccf.products.gates._refuse_empty_operators`,
  which this row did not edit.
* **The returned half** refuses a product one of whose operators returned an
  empty set by ``empty-operator-result`` — a NEW name for an assertion that
  had none, read from the engine's own record and never from the payload
  (``D-IMPL-238`` limb 3).
* **The two are distinguishable by name**: two tokens, two kinds, neither a
  substring of the other, so a consumer branching on ``gate`` reads WHICH
  half fired without parsing ``detail``.
* **The compatibility posture** (``D-10``): ``empty_results=None`` — every
  pre-phase call site — is *not observed* and passes; the empty set is the
  engine's positive *no operator returned empty* and passes too.
* **Both runners carry both halves**, in the same order.
* **Two sabotages, each RED naming its own token**, run on a scratch COPY of
  ``gates.py`` under ``tmp_path`` — never the tree — with the real module's
  bytes asserted unchanged afterward. The declared half's early return is
  removed in one copy; the returned half's step is removed in the other. In
  each, the predicate that should have seen the refusal fails naming the
  token it expected, which is the "RED naming itself" the ledger row asks for.

Every domain value — the operator key, the TTL figures, the bundle version —
is this module's own fixture vocabulary, never an SDK value (CINV-01).
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import pathlib
import textwrap
import types
from datetime import UTC, datetime, timedelta

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products import gates as gates_module
from ccf.products import resolver as resolver_module
from ccf.products.contract import (
    NO_SERVE_OBLIGATIONS,
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    GATE_EMPTY_OPERATOR,
    GATE_EMPTY_OPERATOR_RESULT,
    EmptyOperatorRefusal,
    EmptyResultRefusal,
    GateRefusal,
    ServableProduct,
    run_federated_gates,
    run_gates,
)
from ccf.products.refusal import REFUSAL_KINDS

TENANT = "tenant-fixture"
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
POLICY_VERSION = "policy-version-fixture"
OPERATOR_KEY = "traversal.typed-neighborhood"
SECOND_OPERATOR_KEY = "policy.principal-subgraph"
OPERATORS = frozenset({OPERATOR_KEY, SECOND_OPERATOR_KEY})
MAX_TTL_KEY = "fixture/max-ttl"
MAX_TTL_SECONDS = 3600
CANDIDATE_TTL_SECONDS = 600
SCHEMA_NAME = "fixture.empty-operator-halves"
SCHEMA_VERSION = "1.0.0"

#: The real module's source, read once at import. The sabotages below mutate
#: COPIES of it; the last test asserts the bytes on disk are still these.
GATES_PATH = pathlib.Path(gates_module.__file__)
GATES_SOURCE = GATES_PATH.read_bytes()


# --- the drive ---------------------------------------------------------------


def _class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    max_ttl_version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
    return register_product_class(
        registry=registry,
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=MAX_TTL_KEY,
        max_ttl_version=max_ttl_version,
        serve_obligations=NO_SERVE_OBLIGATIONS,
    )


def _candidate(*, operators: frozenset[str]) -> ContextProductContract:
    """A candidate that passes every gate but the empty-operator halves."""
    return ContextProductContract(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        plan_id="fixture.plan",
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=NOW + timedelta(seconds=CANDIDATE_TTL_SECONDS),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=operators,
            policy_bundle_versions=frozenset({POLICY_VERSION}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload={"value": 1},
        debt=None,
    )


def _serve(
    runner: types.ModuleType,
    candidate: ContextProductContract,
    *,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    empty_results: frozenset[str] | None = None,
) -> object:
    """Run ``runner.run_gates`` — the real module or a scratch copy of it."""
    return runner.run_gates(
        candidate,
        engine_resolved=candidate.lineage.operators_invoked,
        now=NOW,
        registry=registry,
        product_class=product_class,
        empty_results=empty_results,
    )


def _assert_refused_by(outcome: object, token: str) -> object:
    """The refused predicate. Its failure message names the token it expected."""
    gate = getattr(outcome, "gate", None)
    assert gate == token, (
        f"expected the {token!r} gate to refuse; got "
        f"{type(outcome).__name__} (gate={gate!r})"
    )
    return outcome


def _assert_served(outcome: ServableProduct | GateRefusal) -> ServableProduct:
    assert isinstance(outcome, ServableProduct), (
        f"expected a served product; refused by gate {outcome.gate!r}: "
        f"{outcome.detail}"
    )
    return outcome


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


@pytest.fixture
def product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    return _class(registry)


# --- the two halves, by name --------------------------------------------------


def test_the_declared_half_refuses_a_product_that_declares_no_operators(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """``operators_invoked == ∅`` → ``EmptyOperatorRefusal``, gate ``empty-operator-guard`` (INV-CH7-46)."""
    outcome = _serve(
        gates_module,
        _candidate(operators=frozenset()),
        registry=registry,
        product_class=product_class,
    )

    refusal = _assert_refused_by(outcome, GATE_EMPTY_OPERATOR)
    assert isinstance(refusal, EmptyOperatorRefusal)
    assert refusal.gate == "empty-operator-guard"
    assert not isinstance(refusal, EmptyResultRefusal)


def test_the_returned_half_refuses_an_operator_that_returned_an_empty_set(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """``empty_results={key}`` → ``EmptyResultRefusal``, gate ``empty-operator-result``, the key named."""
    outcome = _serve(
        gates_module,
        _candidate(operators=OPERATORS),
        registry=registry,
        product_class=product_class,
        empty_results=frozenset({OPERATOR_KEY}),
    )

    refusal = _assert_refused_by(outcome, GATE_EMPTY_OPERATOR_RESULT)
    assert isinstance(refusal, EmptyResultRefusal)
    assert refusal.gate == "empty-operator-result"
    assert refusal.operator_key == OPERATOR_KEY
    assert refusal.empty_operators == frozenset({OPERATOR_KEY})
    assert OPERATOR_KEY in refusal.detail
    assert not isinstance(refusal, EmptyOperatorRefusal)


def test_the_returned_half_names_the_first_key_in_sorted_order_and_carries_all(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Two operators returned empty: ``operator_key`` is the sorted first; both are carried."""
    outcome = _serve(
        gates_module,
        _candidate(operators=OPERATORS),
        registry=registry,
        product_class=product_class,
        empty_results=OPERATORS,
    )

    refusal = _assert_refused_by(outcome, GATE_EMPTY_OPERATOR_RESULT)
    assert isinstance(refusal, EmptyResultRefusal)
    assert refusal.operator_key == min(OPERATORS)
    assert refusal.empty_operators == OPERATORS


def test_the_two_halves_are_distinguishable_by_name() -> None:
    """Two tokens, two kinds; neither token is a substring of the other."""
    assert GATE_EMPTY_OPERATOR != GATE_EMPTY_OPERATOR_RESULT
    assert GATE_EMPTY_OPERATOR not in GATE_EMPTY_OPERATOR_RESULT
    assert GATE_EMPTY_OPERATOR_RESULT not in GATE_EMPTY_OPERATOR
    assert REFUSAL_KINDS[EmptyOperatorRefusal] != REFUSAL_KINDS[EmptyResultRefusal]
    assert REFUSAL_KINDS[EmptyResultRefusal] == "empty-result-refusal"
    # Two types, related only through the family base — neither derives from
    # the other, so an `isinstance` on one never matches the other.
    assert not issubclass(EmptyResultRefusal, EmptyOperatorRefusal)
    assert not issubclass(EmptyOperatorRefusal, EmptyResultRefusal)


def test_the_declared_half_runs_first_when_both_would_fire(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Adjacent, declared half first: a product declaring nothing is refused by the guard even with an emptiness record."""
    outcome = _serve(
        gates_module,
        _candidate(operators=frozenset()),
        registry=registry,
        product_class=product_class,
        empty_results=frozenset({OPERATOR_KEY}),
    )

    _assert_refused_by(outcome, GATE_EMPTY_OPERATOR)


# --- the compatibility posture ------------------------------------------------


def test_an_unobserved_execution_passes_the_returned_half(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """``empty_results=None`` — every pre-phase call site — is *not observed* and serves."""
    outcome = _serve(
        gates_module,
        _candidate(operators=OPERATORS),
        registry=registry,
        product_class=product_class,
        empty_results=None,
    )

    _assert_served(outcome)  # type: ignore[arg-type]


def test_no_empty_result_passes(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The empty set — the engine's positive *no operator returned empty* — serves."""
    outcome = _serve(
        gates_module,
        _candidate(operators=OPERATORS),
        registry=registry,
        product_class=product_class,
        empty_results=frozenset(),
    )

    _assert_served(outcome)  # type: ignore[arg-type]


def test_the_default_is_not_observed(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """A call site written before the keyword existed reads exactly as it did."""
    outcome = run_gates(
        _candidate(operators=OPERATORS),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )

    _assert_served(outcome)


# --- the federated runner -----------------------------------------------------


def test_the_federated_runner_carries_both_halves(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Both halves, same order, on ``run_federated_gates``; ``None`` passes there too."""
    declared_nothing = _candidate(operators=frozenset())
    outcome = run_federated_gates(
        declared_nothing,
        attested_address=content_hash(declared_nothing),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(_assert_refused_by(outcome, GATE_EMPTY_OPERATOR), EmptyOperatorRefusal)

    candidate = _candidate(operators=OPERATORS)
    outcome = run_federated_gates(
        candidate,
        attested_address=content_hash(candidate),
        now=NOW,
        registry=registry,
        product_class=product_class,
        empty_results=frozenset({OPERATOR_KEY}),
    )
    refusal = _assert_refused_by(outcome, GATE_EMPTY_OPERATOR_RESULT)
    assert isinstance(refusal, EmptyResultRefusal)
    assert refusal.operator_key == OPERATOR_KEY

    # The returned half precedes attributability: a mismatched address is
    # never reached when an operator returned empty.
    outcome = run_federated_gates(
        candidate,
        attested_address="not-the-candidate-address",
        now=NOW,
        registry=registry,
        product_class=product_class,
        empty_results=frozenset({OPERATOR_KEY}),
    )
    _assert_refused_by(outcome, GATE_EMPTY_OPERATOR_RESULT)

    # And the compatibility default.
    outcome = run_federated_gates(
        candidate,
        attested_address=content_hash(candidate),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    _assert_served(outcome)


# --- the key link: the governed resolver threads the engine's record ------------


def test_the_resolver_threads_the_engines_emptiness_record() -> None:
    """The plan's key link, read by AST: ``run_gates(..., empty_results=execution.empty_results)``.

    The seeded seam fixture (``tests/products/test_resolver_seam.py``) proves
    the success leg still serves; it cannot prove the threading is PRESENT,
    because a resolver that dropped the keyword would serve that fixture just
    the same. This reads the reference resolver's one ``run_gates`` call and
    asserts the keyword is there and carries the execution's own field —
    the source the returned half is allowed to read (``D-IMPL-238`` limb 3).
    """
    source = textwrap.dedent(inspect.getsource(resolver_module.GovernedResolver))
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_gates"
    ]
    assert len(calls) == 1, "the governed resolver runs the gates exactly once"
    keywords = {keyword.arg: keyword.value for keyword in calls[0].keywords}
    assert "empty_results" in keywords, (
        "the resolver no longer threads `empty_results` into `run_gates`; the"
        " returned half of the empty-operator gate (empty-operator-result)"
        " has nothing to read on the governed path"
    )
    value = keywords["empty_results"]
    assert isinstance(value, ast.Attribute) and value.attr == "empty_results"
    assert isinstance(value.value, ast.Name) and value.value.id == "execution"


# --- the sabotages, on scratch copies -------------------------------------------

#: The declared half's early return, as it appears in BOTH runners. The
#: sabotage removes it from the FIRST occurrence — `run_gates`.
DECLARED_HALF = (
    "    empty = _refuse_empty_operators(candidate)\n"
    "    if empty is not None:\n"
    "        return empty\n"
)

#: The returned half's step, as it appears in BOTH runners.
RETURNED_HALF = (
    "    returned_empty = _refuse_empty_results(candidate, empty_results=empty_results)\n"
    "    if returned_empty is not None:\n"
    "        return returned_empty\n"
)


def _scratch_gates(tmp_path: pathlib.Path, *, name: str, remove: str) -> types.ModuleType:
    """A copy of ``gates.py`` with ``remove`` deleted from its first runner, loaded under ``name``."""
    source = GATES_SOURCE.decode("utf-8")
    assert source.count(remove) == 2, "the step must appear once per runner"
    mutated = source.replace(remove, "", 1)
    assert mutated != source
    path = tmp_path / f"{name}.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sabotage_removing_the_declared_half_is_red_naming_empty_operator_guard(
    tmp_path: pathlib.Path,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
) -> None:
    """With the declared half gone, the declared test's predicate fails naming ``empty-operator-guard``."""
    scratch = _scratch_gates(tmp_path, name="gates_without_declared_half", remove=DECLARED_HALF)

    outcome = _serve(
        scratch,
        _candidate(operators=frozenset()),
        registry=registry,
        product_class=product_class,
    )

    with pytest.raises(AssertionError, match=GATE_EMPTY_OPERATOR):
        _assert_refused_by(outcome, GATE_EMPTY_OPERATOR)
    # And the same candidate on the REAL module is still refused by name.
    _assert_refused_by(
        _serve(
            gates_module,
            _candidate(operators=frozenset()),
            registry=registry,
            product_class=product_class,
        ),
        GATE_EMPTY_OPERATOR,
    )


def test_sabotage_removing_the_returned_half_is_red_naming_empty_operator_result(
    tmp_path: pathlib.Path,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
) -> None:
    """With the returned half gone, the returned test's predicate fails naming ``empty-operator-result``."""
    scratch = _scratch_gates(tmp_path, name="gates_without_returned_half", remove=RETURNED_HALF)

    outcome = _serve(
        scratch,
        _candidate(operators=OPERATORS),
        registry=registry,
        product_class=product_class,
        empty_results=frozenset({OPERATOR_KEY}),
    )

    # The sabotaged copy SERVES the product an operator computed nothing for.
    assert type(outcome).__name__ == "ServableProduct"
    with pytest.raises(AssertionError, match=GATE_EMPTY_OPERATOR_RESULT):
        _assert_refused_by(outcome, GATE_EMPTY_OPERATOR_RESULT)
    # And the real module refuses it.
    _assert_refused_by(
        _serve(
            gates_module,
            _candidate(operators=OPERATORS),
            registry=registry,
            product_class=product_class,
            empty_results=frozenset({OPERATOR_KEY}),
        ),
        GATE_EMPTY_OPERATOR_RESULT,
    )


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """The controls above mutate copies under ``tmp_path``; ``gates.py`` on disk is byte-identical."""
    assert GATES_PATH.read_bytes() == GATES_SOURCE
    assert DECLARED_HALF in GATES_SOURCE.decode("utf-8")
    assert RETURNED_HALF in GATES_SOURCE.decode("utf-8")
