"""The ONE structural declared-obligations gate, proven on both obligations — ledger rows ``24.5-L-14`` and ``24.5-L-26``.

``D-IMPL-237`` amended ``D-IMPL-224`` for exactly one thing: the SDK may ship
ONE serve-time gate mechanism in ``src/`` for the debt ceiling and the lineage
obligation. ``D-IMPL-238`` reads ``D-IMPL-102`` limb 3 as *no PAYLOAD gate* —
structural gates may join ``run_gates``. ``D-IMPL-240`` (3) shapes the ceiling:
**the class declares it; a request may tighten it, never loosen it; an
undeclared class is unaffected.** This module measures each of those sentences
against :mod:`ccf.products.gates` on every run.

What is proven, and by which test:

* **Criterion 21, the debt half** (``L-14``): within → served; over → refused
  by name (``declared-obligations``, ``debt-ceiling``, both numbers carried);
  an undeclared class serves at any ``D_c`` whatever the request says; a
  request tightens; a loosening request is refused by name — the product it
  would have admitted is held to the class's number; a class that declares a
  ceiling cannot be served unmeasured.
* **Criterion 22, the lineage half** (``L-26``): a declared member that is
  absent or empty is refused by name; present → served; an undeclared class
  is unaffected on the same payload; the federated runner carries the same
  step; and — limb 3 — a named member holding garbage still serves, because
  presence and non-emptiness are all that is read.
* **Criterion 21's sabotage**, written as a predicate-inversion control on a
  scratch candidate (the tree is never edited by a test): a within-tolerance
  product forced over its ceiling fails the *served* predicate naming the
  gate.
* **The token census**: both runners' ``GATE_*`` references are collected
  from their SOURCE (the body and one level of ``_refuse_*`` /
  ``refuse_attestation`` helpers, by AST — docstrings do not count) and
  judged by SET EQUALITY against ``D-IMPL-238``'s five plus
  ``declared-obligations``; arrivals and departures reported separately in
  the ``tests/products/test_gate_two_call_shape.py::_roster_problems`` shape.
  A planted token proves the collector is not vacuous. Plan ``24.5-15``
  amends this census when ``empty-operator-result`` joins.

Memory backend, network-free. Every key, name and number below is this
module's own (CINV-01 reaches ``tests/``): the ceilings are test-owned
proportions, never a product's, and no number here lives in ``src/``.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import (
    PRODUCT_CLASS,
    ProductClassDeclaration,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.halflife.assessment import DebtAssessment, DebtFactors, DebtSignal
from ccf.products import gates as gates_module
from ccf.products import resolver as resolver_module
from ccf.products.contract import (
    NO_SERVE_OBLIGATIONS,
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    ServeObligations,
    register_product_class,
)
from ccf.products.gates import (
    GATE_DECLARED_OBLIGATIONS,
    GATE_EMPTY_OPERATOR,
    GATE_LINEAGE_ATTRIBUTABILITY,
    GATE_LINEAGE_EQUALITY,
    GATE_SOURCE_ATTESTATION,
    GATE_TTL_BOUNDS,
    DeclaredObligationRefusal,
    GateRefusal,
    ServableProduct,
    run_federated_gates,
    run_gates,
)

TENANT = "tenant-fixture"
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
POLICY_VERSION = "policy-version-fixture"
OPERATORS = frozenset({"fixture-operator"})
MAX_TTL_KEY = "fixture/max-ttl"
MAX_TTL_SECONDS = 3600
CANDIDATE_TTL_SECONDS = 600
SCHEMA_NAME = "fixture.declared-obligations"
SCHEMA_VERSION = "1.0.0"

#: The test's own proportions. The class ceiling, a D_c under it, one over it,
#: a request that tightens below the within-value, a request looser than the
#: class, and a D_c an undeclared class must still serve.
DECLARED_CEILING = Decimal("0.5")
WITHIN = Decimal("0.3")
OVER = Decimal("0.7")
TIGHTER = Decimal("0.2")
LOOSER = Decimal("0.9")
ANY_DEBT = Decimal("0.99")

#: The member the lineage obligation names, and three payloads against it.
OBLIGED_MEMBER = "inputs"
PAYLOAD_WITH_MEMBER: Mapping[str, Any] = {"value": 1, OBLIGED_MEMBER: ["line-1"]}
PAYLOAD_WITHOUT_MEMBER: Mapping[str, Any] = {"value": 1}
PAYLOAD_EMPTY_MEMBER: Mapping[str, Any] = {"value": 1, OBLIGED_MEMBER: []}

#: D-IMPL-238's five, by name, and the one D-IMPL-237 licenses — the rosters
#: the census judges by set equality. The numerals below are the sizes of
#: these sets and nothing else.
RUN_GATES_TOKENS: frozenset[str] = frozenset(
    {
        "empty-operator-guard",
        "lineage-strict-equality",
        "ttl-bounds",
        "source-attestation",
        "declared-obligations",
    }
)
RUN_FEDERATED_GATES_TOKENS: frozenset[str] = frozenset(
    {
        "empty-operator-guard",
        "lineage-attributability",
        "ttl-bounds",
        "declared-obligations",
    }
)


# --- the drive: registration, candidate, run --------------------------------


def _assessment(debt: Decimal) -> DebtAssessment:
    """A ``D_c`` of exactly ``debt``; the factors are this module's own."""
    return DebtAssessment(
        debt=debt,
        signal=DebtSignal.OK,
        factors=DebtFactors(
            freshness=Decimal("1"),
            completeness=Decimal("1"),
            semantic_consistency=Decimal("1"),
        ),
    )


def _class(
    registry: ControlPlaneRegistry, *, serve_obligations: ServeObligations
) -> RegisteredProductClass:
    """The rehydration ``_Deployment.product_class`` shape, plus the obligations."""
    max_ttl_version = registry.register(MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
    return register_product_class(
        registry=registry,
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=MAX_TTL_KEY,
        max_ttl_version=max_ttl_version,
        serve_obligations=serve_obligations,
    )


def _candidate(
    *, debt: Decimal | None, payload: Mapping[str, Any]
) -> ContextProductContract:
    """A candidate that passes every universal gate; only the declared one can refuse it."""
    return ContextProductContract(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        plan_id="fixture.plan",
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=NOW + timedelta(seconds=CANDIDATE_TTL_SECONDS),
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=OPERATORS,
            policy_bundle_versions=frozenset({POLICY_VERSION}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload=payload,
        debt=None if debt is None else _assessment(debt),
    )


def _serve(
    candidate: ContextProductContract,
    *,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    debt_tolerance: Decimal | None = None,
) -> ServableProduct | GateRefusal:
    return run_gates(
        candidate,
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
        debt_tolerance=debt_tolerance,
    )


def _serve_federated(
    candidate: ContextProductContract,
    *,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    debt_tolerance: Decimal | None = None,
) -> ServableProduct | GateRefusal:
    return run_federated_gates(
        candidate,
        attested_address=content_hash(candidate),
        now=NOW,
        registry=registry,
        product_class=product_class,
        debt_tolerance=debt_tolerance,
    )


def _assert_served(outcome: ServableProduct | GateRefusal) -> ServableProduct:
    """The served predicate. Its failure message names the refusing gate."""
    assert isinstance(outcome, ServableProduct), (
        f"expected a served product; refused by gate {outcome.gate!r}: "
        f"{outcome.detail}"
    )
    return outcome


def _assert_declared_obligation_refusal(
    outcome: ServableProduct | GateRefusal, *, obligation: str
) -> DeclaredObligationRefusal:
    assert isinstance(outcome, DeclaredObligationRefusal), (
        f"expected the {GATE_DECLARED_OBLIGATIONS!r} gate to refuse; got "
        f"{type(outcome).__name__}"
    )
    assert outcome.gate == GATE_DECLARED_OBLIGATIONS == "declared-obligations"
    assert outcome.obligation == obligation
    return outcome


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


@pytest.fixture
def ceiling_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    """A class declaring a ``D_c`` ceiling and no lineage member."""
    return _class(
        registry, serve_obligations=ServeObligations(debt_ceiling=DECLARED_CEILING)
    )


@pytest.fixture
def lineage_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    """A class declaring a lineage member and no ceiling."""
    return _class(
        registry,
        serve_obligations=ServeObligations(
            lineage_inputs_at=frozenset({OBLIGED_MEMBER})
        ),
    )


@pytest.fixture
def undeclared_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    """The control: a class declaring nothing — every pre-phase class."""
    return _class(registry, serve_obligations=NO_SERVE_OBLIGATIONS)


# --- the declaration seat: a proportion, declared as data, carried to serve ---


def test_a_ceiling_outside_the_unit_interval_is_refused_at_declaration() -> None:
    """``D_c`` is a proportion; a ceiling outside ``[0, 1]`` refuses everything or nothing and is refused where the author can fix it."""
    for bad in (Decimal("1.5"), Decimal("-0.1")):
        with pytest.raises(ValidationError, match="24.5-L-14"):
            ServeObligations(debt_ceiling=bad)
    assert ServeObligations(debt_ceiling=Decimal("0")).debt_ceiling == Decimal("0")
    assert ServeObligations(debt_ceiling=Decimal("1")).debt_ceiling == Decimal("1")
    assert ServeObligations() == NO_SERVE_OBLIGATIONS
    assert NO_SERVE_OBLIGATIONS.debt_ceiling is None
    assert NO_SERVE_OBLIGATIONS.lineage_inputs_at == frozenset()


def test_the_authored_declaration_carries_both_obligations_to_the_registered_class(
    registry: ControlPlaneRegistry,
) -> None:
    """The artifact an adopter writes names the ceiling and the member; registration forwards both (the resolver's ``_register`` shape).

    The NUMBER is in the document, never in ``src/``: the declaration below is
    the only place ``0.5`` is authored on this path.
    """
    parsed = parse_artifact(
        {
            "semver": "1.0.0",
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": MAX_TTL_KEY,
            "required_operator_keys": sorted(OPERATORS),
            "serve_obligations": {
                "debt_ceiling": str(DECLARED_CEILING),
                "lineage_inputs_at": [OBLIGED_MEMBER],
            },
        },
        PRODUCT_CLASS,
    )
    assert isinstance(parsed, ProductClassDeclaration)
    assert parsed.serve_obligations.debt_ceiling == DECLARED_CEILING
    assert parsed.serve_obligations.lineage_inputs_at == frozenset({OBLIGED_MEMBER})

    registered = _class(registry, serve_obligations=parsed.serve_obligations)
    assert registered.serve_obligations == parsed.serve_obligations

    # A declaration that says nothing registers the sentinel — every
    # committed declaration in the tree, unchanged.
    silent = parse_artifact(
        {
            "semver": "1.0.0",
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "ttl_anchor": "from_decision",
            "assembly_mode": "algorithmic",
            "max_ttl_key": MAX_TTL_KEY,
            "required_operator_keys": sorted(OPERATORS),
        },
        PRODUCT_CLASS,
    )
    assert isinstance(silent, ProductClassDeclaration)
    assert silent.serve_obligations == NO_SERVE_OBLIGATIONS


def test_the_resolver_threads_the_effective_ceiling_and_no_principal() -> None:
    """``GovernedResolver`` computes the effective ceiling from the class and the request, passes it to ``run_gates``, and hands no principal to any debt path.

    Read by AST off :mod:`ccf.products.resolver` so the key link
    (``resolver → run_gates`` via ``effective_debt_ceiling``) is measured, not
    remembered — and so a future edit that reads the perspective into the
    ceiling goes RED here (``D-IMPL-105``, threat ``T-24.5-34``).
    """
    tree = ast.parse(inspect.getsource(resolver_module))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

    def _named(call: ast.Call) -> str:
        func = call.func
        return func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")

    ceiling_calls = [c for c in calls if _named(c) == "effective_debt_ceiling"]
    assert len(ceiling_calls) == 1, "the resolver computes the effective ceiling exactly once"
    (ceiling_call,) = ceiling_calls
    keywords = {kw.arg: ast.unparse(kw.value) for kw in ceiling_call.keywords}
    assert set(keywords) == {"declared", "requested"}
    assert "serve_obligations.debt_ceiling" in keywords["declared"]
    assert "DEBT_TOLERANCE_PARAMETER" in keywords["requested"]
    assert "request.parameters" in keywords["requested"]
    for forbidden in ("perspective", "principal"):
        assert forbidden not in ast.unparse(ceiling_call), forbidden

    gate_calls = [c for c in calls if _named(c) == "run_gates"]
    assert len(gate_calls) == 1
    (gate_call,) = gate_calls
    gate_keywords = {kw.arg: ast.unparse(kw.value) for kw in gate_call.keywords}
    assert gate_keywords.get("debt_tolerance") == "debt_tolerance"
    assert "serve_obligations" in ast.unparse(tree), "_register forwards the declaration's obligations"


# --- criterion 21: the debt ceiling (24.5-L-14) -----------------------------


def test_a_product_within_its_declared_ceiling_serves(
    registry: ControlPlaneRegistry, ceiling_class: RegisteredProductClass
) -> None:
    """Within tolerance → served; the gate is silent when the obligation holds."""
    served = _assert_served(
        _serve(
            _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=ceiling_class,
        )
    )
    assert served.product.debt is not None
    assert served.product.debt.debt == WITHIN <= DECLARED_CEILING


def test_a_product_over_its_declared_ceiling_is_refused_by_name(
    registry: ControlPlaneRegistry, ceiling_class: RegisteredProductClass
) -> None:
    """Over → :class:`DeclaredObligationRefusal` naming the gate, the obligation and both numbers."""
    refusal = _assert_declared_obligation_refusal(
        _serve(
            _candidate(debt=OVER, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=ceiling_class,
        ),
        obligation="debt-ceiling",
    )
    assert refusal.declared == str(DECLARED_CEILING)
    assert refusal.observed == str(OVER)
    assert Decimal(refusal.observed) > Decimal(refusal.declared)
    # The Standard's §9 sentence travels in the prose; the door maps the kind.
    assert "409" in refusal.detail


def test_an_undeclared_class_serves_at_any_debt(
    registry: ControlPlaneRegistry, undeclared_class: RegisteredProductClass
) -> None:
    """The control (``D-10``, ``D-IMPL-240`` (3)): no ceiling declared → unaffected, whatever the request says."""
    candidate = _candidate(debt=ANY_DEBT, payload=PAYLOAD_WITHOUT_MEMBER)
    _assert_served(_serve(candidate, registry=registry, product_class=undeclared_class))
    # A request cannot CREATE a ceiling: the tightest request in this module
    # still serves a D_c of 0.99 under an undeclared class.
    _assert_served(
        _serve(
            candidate,
            registry=registry,
            product_class=undeclared_class,
            debt_tolerance=TIGHTER,
        )
    )
    # And an unassessed product under an undeclared class serves as it always did.
    _assert_served(
        _serve(
            _candidate(debt=None, payload=PAYLOAD_WITHOUT_MEMBER),
            registry=registry,
            product_class=undeclared_class,
        )
    )


def test_a_request_may_tighten_the_ceiling_and_never_loosen_it(
    registry: ControlPlaneRegistry, ceiling_class: RegisteredProductClass
) -> None:
    """``D-IMPL-240`` (3): declared 0.5, candidate 0.3 — tolerance 0.2 refuses; tolerance 0.9 serves and the ceiling stays 0.5."""
    within = _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER)

    tightened = _assert_declared_obligation_refusal(
        _serve(
            within,
            registry=registry,
            product_class=ceiling_class,
            debt_tolerance=TIGHTER,
        ),
        obligation="debt-ceiling",
    )
    assert tightened.declared == str(TIGHTER), "the request's tighter number is the effective ceiling"
    assert tightened.observed == str(WITHIN)

    _assert_served(
        _serve(
            within,
            registry=registry,
            product_class=ceiling_class,
            debt_tolerance=LOOSER,
        )
    )


def test_a_loosening_request_is_refused_by_name_the_class_ceiling_stands(
    registry: ControlPlaneRegistry, ceiling_class: RegisteredProductClass
) -> None:
    """A request asking for 0.9 against a class ceiling of 0.5 does not admit a D_c of 0.7.

    The loosening is refused by name: the product the looser request would
    have admitted is refused by ``declared-obligations``, and ``declared``
    reports the CLASS's number, not the request's — the class's ceiling is
    the floor of strictness (``D-IMPL-240`` (3); threat ``T-24.5-33``).
    """
    over_class_under_request = _candidate(debt=OVER, payload=PAYLOAD_WITH_MEMBER)
    assert DECLARED_CEILING < OVER < LOOSER

    refusal = _assert_declared_obligation_refusal(
        _serve(
            over_class_under_request,
            registry=registry,
            product_class=ceiling_class,
            debt_tolerance=LOOSER,
        ),
        obligation="debt-ceiling",
    )
    assert refusal.declared == str(DECLARED_CEILING)
    assert refusal.declared != str(LOOSER)
    assert refusal.observed == str(OVER)


def test_a_declared_ceiling_refuses_an_unassessed_product(
    registry: ControlPlaneRegistry, ceiling_class: RegisteredProductClass
) -> None:
    """``debt=None`` under a declared ceiling → refused ``no-assessment``: a class that declares a ceiling cannot be served unmeasured."""
    refusal = _assert_declared_obligation_refusal(
        _serve(
            _candidate(debt=None, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=ceiling_class,
        ),
        obligation="debt-ceiling",
    )
    assert refusal.observed == "no-assessment"
    assert refusal.declared == str(DECLARED_CEILING)


# --- criterion 22: the lineage obligation (24.5-L-26) -----------------------


def test_a_declared_lineage_obligation_refuses_a_dropped_member(
    registry: ControlPlaneRegistry, lineage_class: RegisteredProductClass
) -> None:
    """``lineage_inputs_at={"inputs"}``: absent → refused; empty → refused; present → served."""
    absent = _assert_declared_obligation_refusal(
        _serve(
            _candidate(debt=None, payload=PAYLOAD_WITHOUT_MEMBER),
            registry=registry,
            product_class=lineage_class,
        ),
        obligation="lineage-inputs",
    )
    assert absent.declared == OBLIGED_MEMBER
    assert absent.observed == "absent"

    none_valued = _assert_declared_obligation_refusal(
        _serve(
            _candidate(debt=None, payload={"value": 1, OBLIGED_MEMBER: None}),
            registry=registry,
            product_class=lineage_class,
        ),
        obligation="lineage-inputs",
    )
    assert none_valued.observed == "absent"

    empty = _assert_declared_obligation_refusal(
        _serve(
            _candidate(debt=None, payload=PAYLOAD_EMPTY_MEMBER),
            registry=registry,
            product_class=lineage_class,
        ),
        obligation="lineage-inputs",
    )
    assert empty.declared == OBLIGED_MEMBER
    assert empty.observed == "empty"

    _assert_served(
        _serve(
            _candidate(debt=None, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=lineage_class,
        )
    )


def test_an_undeclared_lineage_obligation_is_unaffected(
    registry: ControlPlaneRegistry, undeclared_class: RegisteredProductClass
) -> None:
    """The control: the same dropped payload under an empty ``lineage_inputs_at`` serves."""
    for payload in (PAYLOAD_WITHOUT_MEMBER, PAYLOAD_EMPTY_MEMBER):
        _assert_served(
            _serve(
                _candidate(debt=None, payload=payload),
                registry=registry,
                product_class=undeclared_class,
            )
        )


def test_the_federated_runner_carries_the_same_step(
    registry: ControlPlaneRegistry,
) -> None:
    """``run_federated_gates`` runs the identical step after TTL: both halves, same refusal, same control."""
    both = _class(
        registry,
        serve_obligations=ServeObligations(
            debt_ceiling=DECLARED_CEILING,
            lineage_inputs_at=frozenset({OBLIGED_MEMBER}),
        ),
    )

    dropped = _assert_declared_obligation_refusal(
        _serve_federated(
            _candidate(debt=WITHIN, payload=PAYLOAD_WITHOUT_MEMBER),
            registry=registry,
            product_class=both,
        ),
        obligation="lineage-inputs",
    )
    assert dropped.declared == OBLIGED_MEMBER
    assert dropped.observed == "absent"

    over = _assert_declared_obligation_refusal(
        _serve_federated(
            _candidate(debt=OVER, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=both,
        ),
        obligation="debt-ceiling",
    )
    assert over.declared == str(DECLARED_CEILING)
    assert over.observed == str(OVER)

    # The debt half precedes the lineage half, a fixed order, in both runners.
    first = _assert_declared_obligation_refusal(
        _serve_federated(
            _candidate(debt=OVER, payload=PAYLOAD_WITHOUT_MEMBER),
            registry=registry,
            product_class=both,
        ),
        obligation="debt-ceiling",
    )
    assert first.obligation == "debt-ceiling"

    _assert_served(
        _serve_federated(
            _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=both,
        )
    )

    # The federated control: an undeclared class serves the dropped payload.
    undeclared_registry = ControlPlaneRegistry()
    undeclared = _class(undeclared_registry, serve_obligations=NO_SERVE_OBLIGATIONS)
    _assert_served(
        _serve_federated(
            _candidate(debt=ANY_DEBT, payload=PAYLOAD_WITHOUT_MEMBER),
            registry=undeclared_registry,
            product_class=undeclared,
        )
    )


def test_no_payload_shape_is_read(
    registry: ControlPlaneRegistry, lineage_class: RegisteredProductClass
) -> None:
    """Limb 3 (``D-IMPL-238``): a named member holding garbage still SERVES — presence and non-emptiness only."""
    garbage_payloads: tuple[Mapping[str, Any], ...] = (
        {OBLIGED_MEMBER: "not a list, not a line, not anything the class meant"},
        {OBLIGED_MEMBER: 7},
        {OBLIGED_MEMBER: {"unrelated": "shape"}},
        {OBLIGED_MEMBER: [None]},
    )
    for payload in garbage_payloads:
        _assert_served(
            _serve(
                _candidate(debt=None, payload=payload),
                registry=registry,
                product_class=lineage_class,
            )
        )
    # And the members the class did NOT name are never looked at.
    _assert_served(
        _serve(
            _candidate(debt=None, payload={OBLIGED_MEMBER: ["x"], "other": []}),
            registry=registry,
            product_class=lineage_class,
        )
    )


# --- criterion 21's sabotage, as a predicate-inversion control ---------------


def test_forcing_a_within_tolerance_product_over_is_red_naming_the_gate(
    registry: ControlPlaneRegistry, ceiling_class: RegisteredProductClass
) -> None:
    """A within-tolerance candidate forced over its ceiling fails the served predicate, naming ``declared-obligations``.

    The predicate-inversion control the criterion asks for: the SAME predicate
    that passes on the within candidate fails on a ``model_copy`` of it whose
    ``debt`` is over the ceiling, and the failure message names the gate. The
    tree is never edited; the forced candidate is a scratch value.
    """
    within = _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER)
    _assert_served(_serve(within, registry=registry, product_class=ceiling_class))

    forced = within.model_copy(update={"debt": _assessment(OVER)})
    assert forced.debt is not None and forced.debt.debt > DECLARED_CEILING

    with pytest.raises(AssertionError, match=GATE_DECLARED_OBLIGATIONS):
        _assert_served(_serve(forced, registry=registry, product_class=ceiling_class))


# --- the token census: both runners, by set equality ------------------------


def _gate_names_in(source: str) -> set[str]:
    """Every ``GATE_*`` :class:`ast.Name` a function body references — never its docstring."""
    tree = ast.parse(textwrap.dedent(source))
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id.startswith("GATE_")
    }


def _helper_names_called_in(source: str) -> set[str]:
    """The ``_refuse_*`` / ``refuse_*`` helpers a runner's body calls, one level."""
    tree = ast.parse(textwrap.dedent(source))
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and (node.func.id.startswith("_refuse_") or node.func.id.startswith("refuse_"))
    }


def _tokens_registered_by(runner: Callable[..., object]) -> list[str]:
    """The gate tokens a runner reaches: its own body plus one level of helpers, resolved to values."""
    source = inspect.getsource(runner)
    names = _gate_names_in(source)
    for helper in sorted(_helper_names_called_in(source)):
        names |= _gate_names_in(inspect.getsource(getattr(gates_module, helper)))
    return sorted(getattr(gates_module, name) for name in names)


def _roster_problems(
    claimed: list[str], *, ruled: frozenset[str], label: str
) -> list[str]:
    """Set equality, arrivals and departures reported separately; empty is red.

    Copied from ``tests/products/test_gate_two_call_shape.py::_roster_problems``
    so the census judges by the same instrument the exemption rosters do: a
    ceiling is blind to a swap, and ``claimed == []`` reports every ruled
    member as departed rather than reading as compliance.
    """
    arrived = sorted(set(claimed) - ruled)
    departed = sorted(ruled - set(claimed))
    problems: list[str] = []
    if arrived:
        problems.append(
            f"{arrived} are registered by {label} and are NOT on its recorded"
            f" roster (D-IMPL-238's five plus D-IMPL-237's one). A gate that"
            f" arrives unruled is the second mechanism 237 forbids."
            f" Recorded: {sorted(ruled)}"
        )
    if departed:
        problems.append(
            f"{departed} are on {label}'s recorded roster and the runner no"
            f" longer registers them — the record has stopped describing the"
            f" tree. Registered: {sorted(claimed)}"
        )
    return problems


def test_both_runners_register_exactly_the_recorded_tokens() -> None:
    """``run_gates`` = five, ``run_federated_gates`` = four, six distinct across both — by set equality."""
    local = _tokens_registered_by(run_gates)
    federated = _tokens_registered_by(run_federated_gates)

    problems = _roster_problems(
        local, ruled=RUN_GATES_TOKENS, label="run_gates"
    ) + _roster_problems(
        federated, ruled=RUN_FEDERATED_GATES_TOKENS, label="run_federated_gates"
    )
    assert not problems, "; ".join(problems)

    # The numerals are the sizes of the enumerated sets and nothing else.
    assert len(set(local)) == len(RUN_GATES_TOKENS)
    assert len(set(federated)) == len(RUN_FEDERATED_GATES_TOKENS)
    assert set(local) | set(federated) == RUN_GATES_TOKENS | RUN_FEDERATED_GATES_TOKENS
    assert GATE_DECLARED_OBLIGATIONS in set(local) & set(federated)
    # And the constants the module exports spell the same five-plus-one.
    assert RUN_GATES_TOKENS == {
        GATE_EMPTY_OPERATOR,
        GATE_LINEAGE_EQUALITY,
        GATE_TTL_BOUNDS,
        GATE_SOURCE_ATTESTATION,
        GATE_DECLARED_OBLIGATIONS,
    }
    assert RUN_FEDERATED_GATES_TOKENS == {
        GATE_EMPTY_OPERATOR,
        GATE_LINEAGE_ATTRIBUTABILITY,
        GATE_TTL_BOUNDS,
        GATE_DECLARED_OBLIGATIONS,
    }


def test_the_census_sees_a_planted_token_and_a_departure() -> None:
    """The collector's own control: a planted ``GATE_*`` name in a scratch body is an arrival; a dropped one is a departure."""
    planted_source = textwrap.dedent(
        '''
        def scratch_runner(candidate):
            """A docstring naming GATE_DOCSTRING_ONLY, which must NOT count."""
            empty = _refuse_empty_operators(candidate)
            if empty is not None:
                return empty
            return GATE_PLANTED
        '''
    )
    names = _gate_names_in(planted_source)
    assert "GATE_PLANTED" in names
    assert "GATE_DOCSTRING_ONLY" not in names
    assert _helper_names_called_in(planted_source) == {"_refuse_empty_operators"}

    # Arrival and departure are different faults, reported separately.
    problems = _roster_problems(
        sorted(RUN_GATES_TOKENS - {GATE_DECLARED_OBLIGATIONS}) + ["planted-gate"],
        ruled=RUN_GATES_TOKENS,
        label="scratch",
    )
    assert len(problems) == 2
    assert "planted-gate" in problems[0]
    assert GATE_DECLARED_OBLIGATIONS in problems[1]
    # Empty is red, not clean.
    assert _roster_problems([], ruled=RUN_GATES_TOKENS, label="scratch")
