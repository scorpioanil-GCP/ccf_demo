"""The empty-operator gate's ONE half — and the finding that replaced the other.

Ledger row ``24.6-L-06``; ``D-IMPL-242`` **amendment 1** with ``D-IMPL-253``
Q11/Q12 and ``D-IMPL-255`` (2).

Two assertions once shared the name ``empty-operator-guard``: the SDK's — a
product that DECLARED no operators (whitepaper §7.6, INV-CH7-46) — and the
Standard's — an operator that RETURNED an empty set. ``24.5-L-24`` split them
into two named gates and this phase retires the second one. Dave, Q12: *"An
operator successfully evaluating an empty graph did compute something. Calling
it uncomputed conflates absence of input with absence of execution. Serve
computed-empty with the evidence-derived Debt."*

This module is the ``24.5-L-24`` module re-derived under that ruling. **Every
sabotage is kept and one is inverted**: what used to prove the returned half
fires now proves it cannot be put back.

What is proven, and by which test:

* **The declared half still refuses** a product with ``operators_invoked == ∅``
  by ``empty-operator-guard`` — :func:`ccf.products.gates._refuse_empty_operators`,
  which neither this row nor the last one edited. It is the **control**: the
  retirement is of one specific assertion and not of the gate.
* **A computed-empty product is SERVED with its search attached** — the finding
  (:class:`~ccf.products.contract.ComputedEmptyFinding`) names the operators
  that returned empty, every operator invoked, the plan and the store head, so
  a consumer reading an empty payload sees the search rather than silence.
* **The retired half is gone by name**: no token, no kind, no keyword. The
  census in ``tests/products/test_structural_gates.py`` judges the roster; this
  asserts the vocabulary is closed against the retired names.
* **The declared half runs first when both would apply**: a product declaring
  no operators is refused even while carrying a finding.
* **Both runners serve it**, in the same order, local and federated.
* **The sabotage that RESTORES the refusal is RED** — the three-line step is
  inserted into a scratch COPY of ``gates.py`` under ``tmp_path``, never the
  tree, after asserting the insertion anchor appears once per runner; the
  served-empty predicate then fails naming the restored token. The declared
  half's own sabotage is byte-identical to the one ``24.5-L-24`` shipped.

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
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN, StoreSnapshotPin
from ccf.products import gates as gates_module
from ccf.products import resolver as resolver_module
from ccf.products.contract import (
    NO_SERVE_OBLIGATIONS,
    ComputedEmptyFinding,
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    GATE_EMPTY_OPERATOR,
    EmptyOperatorRefusal,
    ServableProduct,
    run_federated_gates,
    run_gates,
)
from ccf.products.refusal import REFUSAL_KINDS
from tests.composition import register_at_composition

TENANT = "tenant-fixture"
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
POLICY_VERSION = "policy-version-fixture"
OPERATOR_KEY = "traversal.typed-neighborhood"
SECOND_OPERATOR_KEY = "policy.principal-subgraph"
OPERATORS = frozenset({OPERATOR_KEY, SECOND_OPERATOR_KEY})
MAX_TTL_KEY = "tenant-fixture/max-ttl"
MAX_TTL_SECONDS = 3600
CANDIDATE_TTL_SECONDS = 600
SCHEMA_NAME = "fixture.empty-operator-halves"
SCHEMA_VERSION = "1.0.0"
PLAN_ID = "fixture.plan"

#: A store head this module authors, so the finding's pin is provably the one
#: it was built with rather than the sentinel by accident.
FIXTURE_PIN = StoreSnapshotPin(substrate="fixture", pin="fixture-head-1")

#: The two retired names, spelled ONCE, here, so every assertion about their
#: absence reads from one place — and so this module is the only file in
#: `tests/` that has to spell them at all.
RETIRED_GATE_TOKEN = "empty-operator-result"
RETIRED_REFUSAL_KIND = "empty-result-refusal"

#: The real module's source, read once at import. The sabotages below mutate
#: COPIES of it; the last test asserts the bytes on disk are still these.
GATES_PATH = pathlib.Path(gates_module.__file__)
GATES_SOURCE = GATES_PATH.read_bytes()


# --- the drive ---------------------------------------------------------------


def _class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    max_ttl_version = register_at_composition(registry, MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
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


def _finding(
    *,
    returned_empty: frozenset[str],
    invoked: frozenset[str] = OPERATORS,
    emptiness: str = "attested",
) -> ComputedEmptyFinding:
    """The finding the governed resolver writes, built here by hand.

    Hand-built rather than driven through an execution: this module's subject
    is what the GATES do with a computed-empty candidate, and
    ``tests/products/test_evidence_derived_debt.py`` is where the finding is
    proved to arrive from a real execution.
    """
    return ComputedEmptyFinding(
        operators_returned_empty=returned_empty,
        operators_invoked=invoked,
        plan_id=PLAN_ID,
        emptiness=emptiness,  # type: ignore[arg-type]
    )


def _candidate(
    *,
    operators: frozenset[str],
    computed_empty: ComputedEmptyFinding | None = None,
) -> ContextProductContract:
    """A candidate that passes every gate but the declared empty-operator half."""
    return ContextProductContract(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        plan_id=PLAN_ID,
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
        computed_empty=computed_empty,
    )


def _serve(
    runner: types.ModuleType,
    candidate: ContextProductContract,
    *,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
) -> object:
    """Run ``runner.run_gates`` — the real module or a scratch copy of it."""
    return runner.run_gates(
        candidate,
        engine_resolved=candidate.lineage.operators_invoked,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )


def _assert_refused_by(outcome: object, token: str) -> object:
    """The refused predicate. Its failure message names the token it expected."""
    gate = getattr(outcome, "gate", None)
    assert gate == token, (
        f"expected the {token!r} gate to refuse; got "
        f"{type(outcome).__name__} (gate={gate!r})"
    )
    return outcome


def _assert_served(outcome: object) -> ServableProduct:
    """The served predicate, by NAME rather than by identity.

    ``type(...).__name__`` rather than ``isinstance``: a sabotaged scratch copy
    of ``gates.py`` defines its own ``ServableProduct``, and an identity check
    would fail against the copy for the wrong reason — reporting a class
    identity mismatch where the subject is whether the product was served.
    """
    assert type(outcome).__name__ == "ServableProduct", (
        f"expected a served product; refused by gate "
        f"{getattr(outcome, 'gate', None)!r}: "
        f"{getattr(outcome, 'detail', outcome)}"
    )
    return outcome  # type: ignore[return-value]


def _served_product(outcome: object) -> ContextProductContract:
    """The product inside a served result, whichever module minted it."""
    product = getattr(_assert_served(outcome), "product", None)
    assert isinstance(product, ContextProductContract)
    return product


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


@pytest.fixture
def product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    return _class(registry)


# --- the half that stays: the control ----------------------------------------


def test_the_declared_half_refuses_a_product_that_declares_no_operators(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """``operators_invoked == ∅`` → ``EmptyOperatorRefusal``, gate ``empty-operator-guard`` (INV-CH7-46).

    The control for the whole row: what ``24.6-05`` retires is one specific
    assertion about a RETURNED empty set, not the guard, and a run in which
    this test also went green-by-absence would be evidence of the wrong thing.
    """
    outcome = _serve(
        gates_module,
        _candidate(operators=frozenset()),
        registry=registry,
        product_class=product_class,
    )

    refusal = _assert_refused_by(outcome, GATE_EMPTY_OPERATOR)
    assert isinstance(refusal, EmptyOperatorRefusal)
    assert refusal.gate == "empty-operator-guard"


# --- the half that went: served, with its search ------------------------------


def test_an_operator_that_returned_empty_is_served_with_its_search_attached(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The inversion, stated positively: computed-empty SERVES, and the finding rides on the product.

    This is the test that read ``empty_results={key}`` → ``EmptyResultRefusal``
    before ``D-IMPL-242`` amendment 1.
    """
    finding = _finding(returned_empty=frozenset({OPERATOR_KEY}))

    outcome = _serve(
        gates_module,
        _candidate(operators=OPERATORS, computed_empty=finding),
        registry=registry,
        product_class=product_class,
    )

    product = _served_product(outcome)
    assert product.computed_empty is not None
    assert product.computed_empty.operators_returned_empty == frozenset({OPERATOR_KEY})
    # The whole search, not only the empty part of it.
    assert product.computed_empty.operators_invoked == OPERATORS
    assert product.computed_empty.plan_id == PLAN_ID
    # The head the search ran against is NOT here (`D-IMPL-309`): it is
    # execution provenance, recorded once per execution in replay
    # dimension 1, so two identical searches under two ambient heads are
    # one finding rather than two.
    assert "store_snapshot_pin" not in type(product.computed_empty).model_fields
    assert product.computed_empty.emptiness == "attested"


def test_every_operator_that_returned_empty_is_carried(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Two operators returned empty: both are named, and the invoked set says out of how many."""
    outcome = _serve(
        gates_module,
        _candidate(
            operators=OPERATORS,
            computed_empty=_finding(returned_empty=OPERATORS),
        ),
        registry=registry,
        product_class=product_class,
    )

    product = _served_product(outcome)
    assert product.computed_empty is not None
    assert product.computed_empty.operators_returned_empty == OPERATORS
    assert product.computed_empty.operators_invoked == OPERATORS


def test_the_retired_half_is_gone_by_name() -> None:
    """No token, no kind, no keyword — the retired half is unreachable, not merely unused.

    ``24.5-L-24``'s test here asserted the two halves were distinguishable by
    name. Under ``D-IMPL-242`` amendment 1 there is one half, so what is
    measurable is that the other one's names are gone from the surface — which
    is the honest re-derivation of "distinguishable" when one of the pair no
    longer exists.
    """
    assert not hasattr(gates_module, "GATE_EMPTY_OPERATOR_RESULT")
    assert not hasattr(gates_module, "EmptyResultRefusal")
    assert not hasattr(gates_module, "_refuse_empty_results")
    assert RETIRED_GATE_TOKEN not in {
        getattr(gates_module, name)
        for name in dir(gates_module)
        if name.startswith("GATE_")
    }
    assert RETIRED_REFUSAL_KIND not in set(REFUSAL_KINDS.values())
    # The keyword is off both runners, so a caller cannot even offer the
    # observation the retired half read.
    for runner in (run_gates, run_federated_gates):
        assert "empty_results" not in inspect.signature(runner).parameters
    # The control: the half that STAYS is still exported under its own name.
    assert gates_module.GATE_EMPTY_OPERATOR == "empty-operator-guard"
    assert REFUSAL_KINDS[EmptyOperatorRefusal] == "empty-operator-refusal"


def test_the_declared_half_still_runs_first_when_both_would_apply(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """A product declaring nothing is refused even while carrying a finding.

    A finding cannot rescue a product computed by nothing: the finding says
    *these operators ran and found nothing*, and a product that declares no
    operators is asserting that none ran (INV-CH7-46).
    """
    outcome = _serve(
        gates_module,
        _candidate(
            operators=frozenset(),
            computed_empty=_finding(
                returned_empty=frozenset({OPERATOR_KEY}), invoked=frozenset()
            ),
        ),
        registry=registry,
        product_class=product_class,
    )

    _assert_refused_by(outcome, GATE_EMPTY_OPERATOR)


# --- the compatibility posture ------------------------------------------------


def test_a_product_with_no_finding_serves_and_says_so(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """``computed_empty=None`` — every pre-phase product — is *no operator returned empty*."""
    outcome = _serve(
        gates_module,
        _candidate(operators=OPERATORS),
        registry=registry,
        product_class=product_class,
    )

    assert _served_product(outcome).computed_empty is None


def test_a_call_site_written_before_the_field_existed_reads_as_it_did(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The default is the positive assertion, and the gates never read it."""
    outcome = run_gates(
        _candidate(operators=OPERATORS),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )

    assert _served_product(outcome).computed_empty is None


def test_the_findings_absence_is_the_only_way_to_say_nothing_returned_empty() -> None:
    """A finding naming no operator is refused at construction.

    Two spellings of one claim would put two content addresses on one product
    (``24.6-L-06``), and the sentinel this field carries is ``None``.
    """
    with pytest.raises(ValueError, match="at least one operator"):
        ComputedEmptyFinding(
            operators_returned_empty=frozenset(),
            operators_invoked=OPERATORS,
            plan_id=PLAN_ID,
            emptiness="attested",
        )


# --- the federated runner -----------------------------------------------------


def test_the_federated_runner_serves_computed_empty_and_keeps_the_declared_half(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Across a Peering too: the declared half refuses, and a peer's computed-empty product serves."""
    declared_nothing = _candidate(operators=frozenset())
    outcome = run_federated_gates(
        declared_nothing,
        attested_address=content_hash(declared_nothing),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(
        _assert_refused_by(outcome, GATE_EMPTY_OPERATOR), EmptyOperatorRefusal
    )

    candidate = _candidate(
        operators=OPERATORS,
        computed_empty=_finding(returned_empty=frozenset({OPERATOR_KEY})),
    )
    outcome = run_federated_gates(
        candidate,
        attested_address=content_hash(candidate),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    product = _served_product(outcome)
    assert product.computed_empty is not None
    assert product.computed_empty.operators_returned_empty == frozenset({OPERATOR_KEY})

    # And the finding is INSIDE the attested address: a peer that recorded a
    # search signed that record with the rest of the product.
    outcome = run_federated_gates(
        candidate,
        attested_address="not-the-candidate-address",
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    _assert_refused_by(outcome, gates_module.GATE_LINEAGE_ATTRIBUTABILITY)


# --- the key link: the resolver writes the finding, and reads nothing else -----


def test_the_resolver_threads_the_engines_emptiness_record() -> None:
    """The plan's key link, read by AST, in its inverted form.

    ``24.5-L-24``'s version asserted the resolver passed
    ``empty_results=execution.empty_results`` INTO ``run_gates``. Under
    ``D-IMPL-242`` amendment 1 the same record goes somewhere else, and both
    halves of that have to be measured: the keyword is **gone** from the gate
    call, and the finding is **built** on the candidate. Asserting only the
    first would pass for a resolver that dropped the record entirely.
    """
    source = textwrap.dedent(inspect.getsource(resolver_module.GovernedResolver))
    tree = ast.parse(source)

    gate_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "run_gates"
    ]
    assert len(gate_calls) == 1, "the governed resolver runs the gates exactly once"
    assert "empty_results" not in {kw.arg for kw in gate_calls[0].keywords}, (
        "the resolver still threads `empty_results` into `run_gates`; the"
        " returned half of the empty-operator gate is retired"
        " (`D-IMPL-242` amendment 1) and the gates read no emptiness record"
    )

    product_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ContextProductContract"
    ]
    assert len(product_calls) == 1, "the resolver builds one candidate"
    keywords = {kw.arg: kw.value for kw in product_calls[0].keywords}
    assert "computed_empty" in keywords, (
        "the resolver no longer writes `computed_empty` onto the candidate;"
        " a served empty answer has lost its search (24.6-L-06)"
    )
    built = keywords["computed_empty"]
    assert isinstance(built, ast.Call)
    assert isinstance(built.func, ast.Attribute) and built.func.attr == "of"
    assert isinstance(built.func.value, ast.Name)
    assert built.func.value.id == "ComputedEmptyFinding"
    # And it is built from the EXECUTION — the engine's own record, which is
    # the only source this finding is allowed to have (`D-IMPL-238` limb 3).
    # SEC-020 (`D-IMPL-370` Q12 (a)): the record is read as `rendered`, which
    # IS the execution unless Π raised the typed withheld signal, and then is
    # the same execution over an empty view — still the engine's record, never
    # the payload. Both halves are measured: the finding reads `rendered`, and
    # `rendered` is bound from `execution` and nothing else.
    names = [node.id for node in ast.walk(built) if isinstance(node, ast.Name)]
    assert "rendered" in names, names
    bindings = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "rendered" for t in node.targets)
    ]
    assert len(bindings) == 1, "`rendered` is bound exactly once"
    assert {
        node.id for node in ast.walk(bindings[0].value) if isinstance(node, ast.Name)
    } == {"execution"}, ast.unparse(bindings[0].value)


# --- the sabotages, on scratch copies -------------------------------------------

#: The declared half's early return, as it appears in BOTH runners. The
#: sabotage removes it from the FIRST occurrence — `run_gates`. Byte-identical
#: to the string `24.5-L-24` shipped: the half it guards did not move.
DECLARED_HALF = (
    "    empty = _refuse_empty_operators(candidate)\n"
    "    if empty is not None:\n"
    "        return empty\n"
)

#: The RETURNED half, as it stood before `24.6-05` deleted it — kept here as
#: the thing a sabotage puts BACK. The inversion of `24.5-L-24`'s sabotage: it
#: removed this step and watched the refusal disappear; this restores it and
#: watches the served product disappear.
RETURNED_HALF = (
    "    returned_empty = _refuse_empty_results(candidate)\n"
    "    if returned_empty is not None:\n"
    "        return returned_empty\n"
)

#: The refusal the restored step returns. Written here, in the sabotage, rather
#: than left in `src/` — which is the point: the assertion no longer exists in
#: the tree, so a control that wants to see it fire has to supply it.
RESTORED_REFUSAL = f'''

def _refuse_empty_results(candidate):
    if not candidate.computed_empty:
        return None
    return GateRefusal(
        gate="{RETIRED_GATE_TOKEN}",
        detail="an empty assembled set fails closed",
    )

'''


def _scratch_gates(
    tmp_path: pathlib.Path, *, name: str, remove: str = "", insert_after: str = ""
) -> types.ModuleType:
    """A copy of ``gates.py`` mutated at its FIRST runner, loaded under ``name``.

    Exactly one of ``remove`` / ``insert_after`` is applied, and in either case
    the anchor is asserted to appear **twice** first — once per runner — so a
    sabotage cannot silently become a no-op because the text it looks for moved
    or was reworded.
    """
    source = GATES_SOURCE.decode("utf-8")
    if remove:
        assert source.count(remove) == 2, "the step must appear once per runner"
        mutated = source.replace(remove, "", 1)
    else:
        assert source.count(insert_after) == 2, (
            "the insertion anchor must appear once per runner"
        )
        mutated = source.replace(insert_after, insert_after + RETURNED_HALF, 1)
        mutated += RESTORED_REFUSAL
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
    scratch = _scratch_gates(
        tmp_path, name="gates_without_declared_half", remove=DECLARED_HALF
    )

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


def test_sabotage_restoring_the_returned_half_refusal_is_red(
    tmp_path: pathlib.Path,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
) -> None:
    """Put the retired refusal back and the served-empty predicate fails naming its token.

    The inversion ``24.6-L-06`` asks for. It proves the served-empty property
    is load-bearing rather than incidental: a tree in which the returned half
    came back — by revert, by merge, by someone reading the Standard's
    sentence without the amendment — is red here, and red **naming the token
    it should not carry**.
    """
    scratch = _scratch_gates(
        tmp_path,
        name="gates_with_the_returned_half_restored",
        insert_after=DECLARED_HALF,
    )

    outcome = _serve(
        scratch,
        _candidate(
            operators=OPERATORS,
            computed_empty=_finding(returned_empty=frozenset({OPERATOR_KEY})),
        ),
        registry=registry,
        product_class=product_class,
    )

    # The sabotaged copy REFUSES the product the fabric computed.
    assert getattr(outcome, "gate", None) == RETIRED_GATE_TOKEN
    with pytest.raises(AssertionError, match=RETIRED_GATE_TOKEN):
        _assert_served(outcome)
    # And the real module serves it, with the finding intact.
    served = _served_product(
        _serve(
            gates_module,
            _candidate(
                operators=OPERATORS,
                computed_empty=_finding(returned_empty=frozenset({OPERATOR_KEY})),
            ),
            registry=registry,
            product_class=product_class,
        )
    )
    assert served.computed_empty is not None


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """The controls above mutate copies under ``tmp_path``; ``gates.py`` on disk is byte-identical."""
    assert GATES_PATH.read_bytes() == GATES_SOURCE
    source = GATES_SOURCE.decode("utf-8")
    assert DECLARED_HALF in source
    # The positive half of the same claim: the restored step is NOT in the
    # tree, so the sabotage above is genuinely adding something rather than
    # re-adding something that never left.
    assert RETURNED_HALF not in source
    assert "def _refuse_empty_results(" not in source
