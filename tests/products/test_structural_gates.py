"""The ONE structural declared-obligations gate, and the tolerance step that is NOT one — ``24.5-L-26``, ``24.6-L-04``, ``24.6-L-05``.

``D-IMPL-237`` amended ``D-IMPL-224`` for exactly one thing: the SDK may ship
ONE serve-time gate mechanism in ``src/``. ``D-IMPL-238`` reads ``D-IMPL-102``
limb 3 as *no PAYLOAD gate* — structural gates may join ``run_gates``.

**Re-derived at ``24.6-04``, and the shape of the subject changed.** This
module measured two obligations under one gate. ``D-IMPL-251`` C1=A ruled that
a product class's debt figure is a *default tolerance characteristic* and not a
policy boundary — *"a product class cannot independently withhold otherwise
deliverable context because its own debt preference was exceeded"* — and C2=B
ruled that a caller's own tolerance is *"enforced as requested"*. So the gate
now carries ONE obligation (lineage), and the debt comparison moved out of it
entirely, into :func:`~ccf.products.gates.refuse_over_tolerance` over a product
the gates have already ADMITTED. ``D-IMPL-240`` (3)'s *"a request may tighten,
never loosen"* is SUPERSEDED and the tests that asserted it are inverted below,
by name, rather than deleted.

What is proven, and by which test:

* **The tolerance step** (``24.6-L-05``): within → delivered; over → withheld
  by name (``tolerance-exceeded``, the authority and both numbers carried);
  no applicable tolerance → delivered at any ``D_c``; a caller's LOOSER
  tolerance is honored over a class default (the inversion); an applicable
  tolerance withholds an unassessed product with ``observed=None``.
* **The lineage obligation** (``24.5-L-26``): a declared member that is
  absent or empty is refused by name; present → served; an undeclared class
  is unaffected on the same payload; the federated runner carries the same
  step; and — limb 3 — a named member holding garbage still serves, because
  presence and non-emptiness are all that is read.
* **The tolerance step's sabotage**, written as a predicate-inversion control
  on a scratch candidate (the tree is never edited by a test): a
  within-tolerance product forced over fails the *delivered* predicate naming
  ``tolerance-exceeded``.
* **The token census**: both runners' ``GATE_*`` references are collected
  from their SOURCE (the body and one level of ``_refuse_*`` /
  ``refuse_attestation`` helpers, by AST — docstrings do not count) and
  judged by SET EQUALITY against ``D-IMPL-238``'s five plus
  ``declared-obligations``; arrivals and departures reported separately in
  the ``tests/products/test_gate_two_call_shape.py::_roster_problems`` shape.
  A planted token proves the collector is not vacuous. The roster is
  UNCHANGED by ``24.6-04``: the tolerance step is not a gate, and an AST
  assertion below proves it is called in the resolver and in neither runner.

Memory backend, network-free. Every key, name and number below is this
module's own (CINV-01 reaches ``tests/``): the tolerances are test-owned
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
    DEBT_TOLERANCE_PARAMETER,
    GATE_DECLARED_OBLIGATIONS,
    GATE_EMPTY_OPERATOR,
    GATE_EMPTY_OPERATOR_RESULT,
    GATE_LINEAGE_ATTRIBUTABILITY,
    GATE_LINEAGE_EQUALITY,
    GATE_SOURCE_ATTESTATION,
    GATE_TTL_BOUNDS,
    DeclaredObligationRefusal,
    GateRefusal,
    ServableProduct,
    ToleranceExceededRefusal,
    refuse_over_tolerance,
    run_federated_gates,
    run_gates,
)
from ccf.products.provenance import (
    Authority,
    EffectiveParameter,
    ProvenanceSource,
)
from ccf.products.refusal import REFUSAL_KINDS

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

#: The test's own proportions. The class's DEFAULT tolerance, a D_c under it,
#: one over it, a caller tightening below the within-value, a caller looser
#: than the class default, and a D_c a class declaring nothing must still
#: deliver.
DECLARED_DEFAULT = Decimal("0.5")
WITHIN = Decimal("0.3")
OVER = Decimal("0.7")
TIGHTER = Decimal("0.2")
LOOSER = Decimal("0.9")
ANY_DEBT = Decimal("0.99")

#: The test's own provenance vocabulary for the three authorities. Fixture
#: identities: nothing here is resolved, and nothing here lives in `src/`.
CLASS_ARTIFACT_KEY = "fixture/product-class"
CLASS_ARTIFACT_VERSION = "fixture-class-version"
POLICY_ARTIFACT_KEY = "fixture/policy-constraint"
POLICY_ARTIFACT_VERSION = "fixture-policy-version"
REQUEST_IDENTITY = "fixture-request-identity"

#: The member the lineage obligation names, and three payloads against it.
OBLIGED_MEMBER = "inputs"
PAYLOAD_WITH_MEMBER: Mapping[str, Any] = {"value": 1, OBLIGED_MEMBER: ["line-1"]}
PAYLOAD_WITHOUT_MEMBER: Mapping[str, Any] = {"value": 1}
PAYLOAD_EMPTY_MEMBER: Mapping[str, Any] = {"value": 1, OBLIGED_MEMBER: []}

#: D-IMPL-238's five, by name; the one mechanism D-IMPL-237 licenses
#: (`declared-obligations`, plan 24.5-13); and the returned-empty half of the
#: empty-operator gate that D-IMPL-238's second sentence unlocked
#: (`empty-operator-result`, plan 24.5-15, ledger row 24.5-L-24) — the
#: rosters the census judges by set equality. The numerals below are the
#: sizes of these sets and nothing else: six on `run_gates`, five on
#: `run_federated_gates`, seven distinct across the two.
RUN_GATES_TOKENS: frozenset[str] = frozenset(
    {
        "empty-operator-guard",
        "empty-operator-result",
        "lineage-strict-equality",
        "ttl-bounds",
        "source-attestation",
        "declared-obligations",
    }
)
RUN_FEDERATED_GATES_TOKENS: frozenset[str] = frozenset(
    {
        "empty-operator-guard",
        "empty-operator-result",
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
) -> ServableProduct | GateRefusal:
    return run_gates(
        candidate,
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )


def _serve_federated(
    candidate: ContextProductContract,
    *,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
) -> ServableProduct | GateRefusal:
    return run_federated_gates(
        candidate,
        attested_address=content_hash(candidate),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )


def _tolerance(
    value: Decimal, *, authority: Authority
) -> EffectiveParameter:
    """One resolved tolerance, as the Authority layer would have produced it.

    The three authorities carry three provenance shapes, and the shape is not
    decoration: an ``artifact`` source must name a version and a ``request``
    source must not (``ccf.products.provenance``). Building the parameter here
    rather than reaching into the resolver keeps this module a test of
    :func:`~ccf.products.gates.refuse_over_tolerance` — the resolution itself
    is proven end to end in ``tests/products/test_tolerance_exceeded.py``.
    """
    if authority == "caller":
        source = ProvenanceSource(
            kind="request", identity=REQUEST_IDENTITY, version=None
        )
    elif authority == "policy":
        source = ProvenanceSource(
            kind="artifact",
            identity=POLICY_ARTIFACT_KEY,
            version=POLICY_ARTIFACT_VERSION,
        )
    else:
        source = ProvenanceSource(
            kind="artifact",
            identity=CLASS_ARTIFACT_KEY,
            version=CLASS_ARTIFACT_VERSION,
        )
    return EffectiveParameter(
        name=DEBT_TOLERANCE_PARAMETER,
        value=value,
        authority=authority,
        source=source,
    )


def _deliver(
    candidate: ContextProductContract,
    *,
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    tolerance: EffectiveParameter | None = None,
) -> ServableProduct | GateRefusal | ToleranceExceededRefusal:
    """Gates, then the tolerance step — the resolver's own order, in miniature.

    The two are composed here rather than inside ``run_gates`` because that is
    exactly the ``24.6-04`` change: the gates decide whether the product may
    exist, and this decides whether the product that does exist is delivered.
    """
    gated = _serve(candidate, registry=registry, product_class=product_class)
    if not isinstance(gated, ServableProduct):
        return gated
    withheld = refuse_over_tolerance(gated, tolerance=tolerance)
    return gated if withheld is None else withheld


def _assert_served(outcome: ServableProduct | GateRefusal) -> ServableProduct:
    """The served predicate. Its failure message names the refusing gate."""
    assert isinstance(outcome, ServableProduct), (
        f"expected a served product; refused by gate {outcome.gate!r}: "
        f"{outcome.detail}"
    )
    return outcome


def _assert_delivered(
    outcome: ServableProduct | GateRefusal | ToleranceExceededRefusal,
) -> ServableProduct:
    """The DELIVERED predicate — gates admitted it AND no tolerance withheld it.

    Distinct from :func:`_assert_served` on purpose: its failure message names
    whichever of the two said no, so a reader of a red run knows immediately
    whether the product failed to exist or failed to be delivered.
    """
    if isinstance(outcome, ToleranceExceededRefusal):
        raise AssertionError(
            "expected a delivered product; fulfillment was withheld by"
            f" tolerance-exceeded ({outcome.authority} tolerance"
            f" {outcome.tolerance}, observed {outcome.observed}):"
            f" {outcome.detail}"
        )
    return _assert_served(outcome)


def _assert_withheld(
    outcome: ServableProduct | GateRefusal | ToleranceExceededRefusal,
    *,
    authority: str,
) -> ToleranceExceededRefusal:
    """The withheld predicate: `tolerance-exceeded`, and by whose authority."""
    assert isinstance(outcome, ToleranceExceededRefusal), (
        "expected fulfillment to be withheld by tolerance-exceeded; got "
        f"{type(outcome).__name__}"
    )
    assert REFUSAL_KINDS[ToleranceExceededRefusal] == "tolerance-exceeded"
    assert outcome.authority == authority
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
def default_tolerance_class(
    registry: ControlPlaneRegistry,
) -> RegisteredProductClass:
    """A class declaring a DEFAULT ``D_c`` tolerance and no lineage member.

    The gate reads nothing off it any more (``24.6-04``); the number reaches
    the delivery decision only as a resolved default, which is why every test
    below that uses this fixture also builds the ``default``-authority
    tolerance explicitly.
    """
    return _class(
        registry,
        serve_obligations=ServeObligations(
            default_debt_tolerance=DECLARED_DEFAULT
        ),
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


def test_a_default_tolerance_outside_the_unit_interval_is_refused_at_declaration() -> None:
    """``D_c`` is a proportion; a default tolerance outside ``[0, 1]`` withholds everything or nothing and is refused where the author can fix it."""
    for bad in (Decimal("1.5"), Decimal("-0.1")):
        with pytest.raises(ValidationError, match="24.6-L-04"):
            ServeObligations(default_debt_tolerance=bad)
    assert (
        ServeObligations(default_debt_tolerance=Decimal("0")).default_debt_tolerance
        == Decimal("0")
    )
    assert (
        ServeObligations(default_debt_tolerance=Decimal("1")).default_debt_tolerance
        == Decimal("1")
    )
    assert ServeObligations() == NO_SERVE_OBLIGATIONS
    assert NO_SERVE_OBLIGATIONS.default_debt_tolerance is None
    assert NO_SERVE_OBLIGATIONS.lineage_inputs_at == frozenset()
    # The renamed field is the same field, not a second one beside it
    # (`D-IMPL-253` Q9): the old name is not a member of the model at all.
    assert set(ServeObligations.model_fields) == {
        "default_debt_tolerance",
        "lineage_inputs_at",
    }


def test_the_authored_declaration_carries_both_members_to_the_registered_class(
    registry: ControlPlaneRegistry,
) -> None:
    """The artifact an adopter writes names the default tolerance and the member; registration forwards both (the resolver's ``_register`` shape).

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
                "default_debt_tolerance": str(DECLARED_DEFAULT),
                "lineage_inputs_at": [OBLIGED_MEMBER],
            },
        },
        PRODUCT_CLASS,
    )
    assert isinstance(parsed, ProductClassDeclaration)
    assert parsed.serve_obligations.default_debt_tolerance == DECLARED_DEFAULT
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


def test_the_resolver_resolves_then_gates_then_withholds_and_hands_no_principal() -> None:
    """``GovernedResolver`` resolves BEFORE it reads the graph, gates, and only then holds an admitted product to the tolerance — with no principal on that path.

    Read by AST off :mod:`ccf.products.resolver` so the key link
    (``resolver → constraint_resolver.resolve → run_gates →
    refuse_over_tolerance``) is measured, not remembered — and so a future edit
    that reads the perspective into the tolerance goes RED here
    (``D-IMPL-105``, threat ``T-24.5-34``).

    **Re-derived at ``24.6-04``, not weakened.** At ``24.6-03`` it measured a
    ``debt_tolerance`` keyword on the ``run_gates`` call; that keyword is gone
    with the gate's debt half (``24.6-L-04``), so the same three properties are
    measured at the new shape, plus a fourth the new shape makes checkable:

    1. the resolution happens exactly once;
    2. it happens **before** the graph is read and before the gates run;
    3. nothing about the principal or the perspective reaches the tolerance
       the delivery decision is given;
    4. the tolerance step runs **after** the gates — a product is withheld
       only once it is known to exist (``D-IMPL-251``: refusal of fulfillment,
       not of response).
    """
    tree = ast.parse(inspect.getsource(resolver_module))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

    def _named(call: ast.Call) -> str:
        func = call.func
        return func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")

    source = ast.unparse(tree)
    assert "effective_debt_ceiling" not in source, (
        "the scalar fold is deleted; a re-introduced one is the defect"
        " D-IMPL-254 removed, wearing the resolver's name"
    )

    resolutions = [c for c in calls if _named(c) == "resolve"]
    assert len(resolutions) == 1, "the resolver resolves the question exactly once"
    (resolution,) = resolutions
    assert ast.unparse(resolution.func) == "self.constraint_resolver.resolve"
    resolved_keywords = {kw.arg for kw in resolution.keywords}
    assert {
        "request",
        "declared",
        "declared_source",
        "capabilities",
        # 24.6-04: the class's declared default reaches the resolution as a
        # default with its own pin, and never as a ceiling folded downstream.
        "class_defaults",
        "class_source",
    } <= resolved_keywords

    # Ordering, by position in the module's own source: resolution, then the
    # graph read, then the gates, then the tolerance step. A resolution that
    # ran after the read would have bounded a question the engine had already
    # answered; a tolerance step that ran before the gates would withhold a
    # product nobody had established could exist.
    reads = [
        c for c in calls if ast.unparse(c.func).endswith("handle.reader.as_of")
    ]
    assert len(reads) == 1
    gate_calls = [c for c in calls if _named(c) == "run_gates"]
    assert len(gate_calls) == 1
    (gate_call,) = gate_calls
    withholds = [c for c in calls if _named(c) == "refuse_over_tolerance"]
    assert len(withholds) == 1, "the delivery decision is made in one place"
    (withhold,) = withholds
    assert resolution.lineno < reads[0].lineno < gate_call.lineno < withhold.lineno

    # The gate no longer receives a tolerance at all.
    gate_keywords = {kw.arg: ast.unparse(kw.value) for kw in gate_call.keywords}
    assert "debt_tolerance" not in gate_keywords

    # And what the delivery decision IS given carries no principal: the whole
    # call, keywords included, unparsed and scanned.
    withheld_source = ast.unparse(withhold)
    assert "tolerance=" in withheld_source
    for forbidden in ("perspective", "principal"):
        assert forbidden not in withheld_source, forbidden

    assert "serve_obligations" in source, "_register forwards the declaration's obligations"


# --- 24.6-L-05: the tolerance step, over an ADMITTED product ----------------


def test_a_product_within_the_default_tolerance_is_delivered(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """Within the applicable tolerance -> delivered; the step is silent when the observation holds."""
    delivered = _assert_delivered(
        _deliver(
            _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(DECLARED_DEFAULT, authority="default"),
        )
    )
    assert delivered.product.debt is not None
    assert delivered.product.debt.debt == WITHIN <= DECLARED_DEFAULT


def test_a_product_over_the_default_tolerance_is_withheld_by_name(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """Over -> :class:`ToleranceExceededRefusal` naming the authority, the tolerance and the observation.

    The gate is NOT what says no: the candidate passes every gate, including
    the declared-obligations gate, and the product exists before the tolerance
    is consulted. The assertion below on ``_serve`` measures exactly that, so
    a reader cannot mistake this for the retired 409 path.
    """
    candidate = _candidate(debt=OVER, payload=PAYLOAD_WITH_MEMBER)
    # The product IS constructible — the ruling's own sentence, measured.
    _assert_served(
        _serve(candidate, registry=registry, product_class=default_tolerance_class)
    )

    withheld = _assert_withheld(
        _deliver(
            candidate,
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(DECLARED_DEFAULT, authority="default"),
        ),
        authority="default",
    )
    assert withheld.tolerance == DECLARED_DEFAULT
    assert withheld.observed == OVER
    assert withheld.observed > withheld.tolerance
    assert withheld.breakdown is not None
    assert withheld.breakdown == candidate.debt
    assert withheld.source.kind == "artifact"
    assert withheld.source.identity == CLASS_ARTIFACT_KEY
    # D-IMPL-253 Q10's semantic caution, as a grep: the shell says fulfillment
    # was withheld and never that the Debt was invalid.
    assert "fulfillment was withheld" in withheld.detail
    assert "invalid" not in withheld.detail


def test_no_applicable_tolerance_delivers_at_any_debt(
    registry: ControlPlaneRegistry, undeclared_class: RegisteredProductClass
) -> None:
    """The control: nothing declared a tolerance -> delivered, whatever ``D_c`` is.

    ``None`` is not a permissive default; it is the absence of any declaration
    to enforce, which is what a class with no opinion, a caller who said
    nothing and a deployment with no constraint jointly mean.
    """
    candidate = _candidate(debt=ANY_DEBT, payload=PAYLOAD_WITHOUT_MEMBER)
    _assert_delivered(
        _deliver(candidate, registry=registry, product_class=undeclared_class)
    )
    # And an unassessed product with no applicable tolerance is delivered too:
    # a missing assessment only matters when something is holding the product
    # to a number.
    _assert_delivered(
        _deliver(
            _candidate(debt=None, payload=PAYLOAD_WITHOUT_MEMBER),
            registry=registry,
            product_class=undeclared_class,
        )
    )


def test_a_callers_tolerance_is_enforced_as_requested_tighter_or_looser(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """``D-IMPL-251`` C2=B: the caller's number is honored AS REQUESTED, in both directions.

    **This test supersedes ``D-IMPL-240`` (3)'s "a request may tighten, never
    loosen".** That sentence is amended (``D-IMPL-240`` amendment 2): the
    consumer owns fitness, so a caller asking for 0.9 gets 0.9 and a caller
    asking for 0.2 gets 0.2 — the class's 0.5 is a default and fills an
    omission only. Both halves are asserted here, and the looser half is the
    one that would have been RED before this plan.
    """
    within = _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER)

    tightened = _assert_withheld(
        _deliver(
            within,
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(TIGHTER, authority="caller"),
        ),
        authority="caller",
    )
    assert tightened.tolerance == TIGHTER
    assert tightened.observed == WITHIN
    assert tightened.source.kind == "request"
    assert tightened.source.version is None

    # Looser than the observation: delivered. The class's own 0.5 does not
    # stand against it, and 0.3 <= 0.9.
    assert TIGHTER < WITHIN < DECLARED_DEFAULT < LOOSER
    _assert_delivered(
        _deliver(
            within,
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(LOOSER, authority="caller"),
        )
    )


def test_a_looser_caller_tolerance_delivers_what_the_class_default_would_have_withheld(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """The INVERSION (``D-IMPL-251`` C1=A): a product over the class's default is delivered when the caller asked for more.

    This test asserted the opposite until ``24.6-04``, under the name
    ``test_a_loosening_request_is_refused_by_name_the_class_ceiling_stands``:
    a request asking 0.9 against a class figure of 0.5 did NOT admit a ``D_c``
    of 0.7, because the class figure was the floor of strictness. Dave: *"the
    class shouldn't override me merely because its author thought .20 was
    generally preferable"*. So the product is delivered, and the pair below
    proves the class default is still live — it withholds the SAME product
    when the caller states nothing.
    """
    over_class_under_caller = _candidate(debt=OVER, payload=PAYLOAD_WITH_MEMBER)
    assert DECLARED_DEFAULT < OVER < LOOSER

    _assert_delivered(
        _deliver(
            over_class_under_caller,
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(LOOSER, authority="caller"),
        )
    )

    # The control that keeps the assertion above from being vacuous: the same
    # product, the same class, the class's own default in force -> withheld.
    withheld = _assert_withheld(
        _deliver(
            over_class_under_caller,
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(DECLARED_DEFAULT, authority="default"),
        ),
        authority="default",
    )
    assert withheld.tolerance == DECLARED_DEFAULT


def test_a_policy_tolerance_withholds_under_the_same_kind(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """The third authority: a policy bound produces the SAME kind, with ``authority == 'policy'``.

    ``D-IMPL-251``'s three debt concepts are three authorities and ONE shell
    (``D-IMPL-253`` Q10: *"preserve which authority established the
    tolerance"*). A second kind for governance would make a consumer branch on
    the wrong axis — what changed is who set the number, not what happened.
    """
    withheld = _assert_withheld(
        _deliver(
            _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(TIGHTER, authority="policy"),
        ),
        authority="policy",
    )
    assert withheld.source.kind == "artifact"
    assert withheld.source.identity == POLICY_ARTIFACT_KEY
    assert withheld.source.version == POLICY_ARTIFACT_VERSION
    assert REFUSAL_KINDS[type(withheld)] == "tolerance-exceeded"


def test_an_applicable_tolerance_withholds_an_unassessed_product(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """``debt=None`` under an applicable tolerance -> withheld with ``observed=None``.

    ``None`` is the positive *no assessment was produced* — the retired half's
    ``observed="no-assessment"`` string, typed. An unmeasured product is
    neither within a tolerance nor over it, so the tolerance cannot be shown to
    be met; reporting the observation as ``0`` would claim a measurement nobody
    made.
    """
    candidate = _candidate(debt=None, payload=PAYLOAD_WITH_MEMBER)
    # It is constructible: the gates admit an unassessed product.
    _assert_served(
        _serve(candidate, registry=registry, product_class=default_tolerance_class)
    )

    withheld = _assert_withheld(
        _deliver(
            candidate,
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=_tolerance(DECLARED_DEFAULT, authority="default"),
        ),
        authority="default",
    )
    assert withheld.observed is None
    assert withheld.breakdown is None
    assert withheld.tolerance == DECLARED_DEFAULT
    assert "cannot be shown to be met" in withheld.detail
    assert "invalid" not in withheld.detail


def test_the_gate_sequence_reads_no_debt_at_all(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """``24.6-L-04``: neither runner consults ``D_c``, whatever the class declares.

    The deletion, measured as behavior rather than as an absent line: a
    candidate whose ``D_c`` is 0.99 under a class declaring 0.5 passes both
    gate sequences. Before ``24.6-04`` both refused it by name.
    """
    over = _candidate(debt=ANY_DEBT, payload=PAYLOAD_WITH_MEMBER)
    _assert_served(
        _serve(over, registry=registry, product_class=default_tolerance_class)
    )
    _assert_served(
        _serve_federated(
            over, registry=registry, product_class=default_tolerance_class
        )
    )
    # And the source of the deletion, by name: the shared helper takes no
    # tolerance, so there is no keyword a caller could re-thread.
    assert "debt_tolerance" not in inspect.signature(run_gates).parameters
    assert "debt_tolerance" not in inspect.signature(run_federated_gates).parameters
    assert "debt_tolerance" not in inspect.signature(
        gates_module._refuse_declared_obligations
    ).parameters


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
    """``run_federated_gates`` runs the identical step after TTL: same obligation, same refusal, same control.

    **Re-derived at ``24.6-04``**: the class below still declares a default
    tolerance, and the federated runner now ignores it exactly as the local one
    does. What both runners still share is the lineage obligation, which is
    the whole point of the factoring — two runners, one reading of what a class
    obliged.
    """
    both = _class(
        registry,
        serve_obligations=ServeObligations(
            default_debt_tolerance=DECLARED_DEFAULT,
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

    # A federated candidate over the class's declared default is ADMITTED: the
    # consuming class's figure is a default, not an admission boundary
    # (`D-IMPL-251` C1=A). Withholding it, if a tolerance applies, is the
    # consuming layer's call and not this sequence's.
    _assert_served(
        _serve_federated(
            _candidate(debt=OVER, payload=PAYLOAD_WITH_MEMBER),
            registry=registry,
            product_class=both,
        )
    )

    # The lineage obligation still refuses regardless of the debt carried.
    over_and_dropped = _assert_declared_obligation_refusal(
        _serve_federated(
            _candidate(debt=OVER, payload=PAYLOAD_WITHOUT_MEMBER),
            registry=registry,
            product_class=both,
        ),
        obligation="lineage-inputs",
    )
    assert over_and_dropped.observed == "absent"

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


# --- the tolerance step's sabotage, as a predicate-inversion control --------


def test_forcing_a_within_tolerance_product_over_is_red_naming_the_step(
    registry: ControlPlaneRegistry,
    default_tolerance_class: RegisteredProductClass,
) -> None:
    """A within-tolerance candidate forced over fails the DELIVERED predicate, naming ``tolerance-exceeded``.

    The predicate-inversion control, kept in shape from ``24.5-13`` and
    re-pointed at what now decides: the SAME predicate that passes on the
    within candidate fails on a ``model_copy`` of it whose ``debt`` is over the
    tolerance, and the failure message names the step. The tree is never
    edited; the forced candidate is a scratch value.

    The gate token is asserted absent from the message on purpose: if the
    delivery decision were ever folded back into the gate, this would report
    ``declared-obligations`` and the test would still be green on a message
    check that only looked for *a* name.
    """
    tolerance = _tolerance(DECLARED_DEFAULT, authority="default")
    within = _candidate(debt=WITHIN, payload=PAYLOAD_WITH_MEMBER)
    _assert_delivered(
        _deliver(
            within,
            registry=registry,
            product_class=default_tolerance_class,
            tolerance=tolerance,
        )
    )

    forced = within.model_copy(update={"debt": _assessment(OVER)})
    assert forced.debt is not None and forced.debt.debt > DECLARED_DEFAULT

    with pytest.raises(AssertionError, match="tolerance-exceeded") as raised:
        _assert_delivered(
            _deliver(
                forced,
                registry=registry,
                product_class=default_tolerance_class,
                tolerance=tolerance,
            )
        )
    assert GATE_DECLARED_OBLIGATIONS not in str(raised.value)


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
    """``run_gates`` = six, ``run_federated_gates`` = five, seven distinct across both — by set equality.

    How the roster came to be this size, so the numerals are never read as
    a ceiling: ``D-IMPL-238`` recorded FIVE tokens by name; ``D-IMPL-237``
    licensed ONE mechanism beyond them (``declared-obligations``, plan
    ``24.5-13``); and ``D-IMPL-238``'s second sentence unlocked the
    returned-empty half of the empty-operator gate (``empty-operator-result``,
    plan ``24.5-15``, ledger row ``24.5-L-24``) — a NAME for an assertion
    that had none, not a second mechanism. Six on ``run_gates``, five on
    ``run_federated_gates``, seven distinct names across the two runners,
    and no payload gate. Judged by set equality with arrivals and departures
    reported separately; never a superset check.
    """
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
    # Both halves of the empty-operator gate are on BOTH runners (24.5-L-24).
    assert {GATE_EMPTY_OPERATOR, GATE_EMPTY_OPERATOR_RESULT} <= set(local) & set(federated)
    # And the constants the module exports spell the same five-plus-one-plus-one.
    assert RUN_GATES_TOKENS == {
        GATE_EMPTY_OPERATOR,
        GATE_EMPTY_OPERATOR_RESULT,
        GATE_LINEAGE_EQUALITY,
        GATE_TTL_BOUNDS,
        GATE_SOURCE_ATTESTATION,
        GATE_DECLARED_OBLIGATIONS,
    }
    assert RUN_FEDERATED_GATES_TOKENS == {
        GATE_EMPTY_OPERATOR,
        GATE_EMPTY_OPERATOR_RESULT,
        GATE_LINEAGE_ATTRIBUTABILITY,
        GATE_TTL_BOUNDS,
        GATE_DECLARED_OBLIGATIONS,
    }
    assert len(RUN_GATES_TOKENS | RUN_FEDERATED_GATES_TOKENS) == 7


def test_the_tolerance_step_joined_neither_runner(
) -> None:
    """``24.6-04`` added a refusal and NO gate: ``refuse_over_tolerance`` is called in the resolver and in neither runner.

    ``D-IMPL-237`` licenses one serve-time gate mechanism and ``D-IMPL-238``
    records its membership by name, so *"this is not a gate"* is a claim that
    has to be measured rather than asserted in a docstring. The census above
    measures the tokens; this measures the CALL, by AST, on both sides:

    * the two runners' bodies and their one level of ``_refuse_*`` helpers
      contain no call to it — the same collection the token census walks, so
      a step smuggled into a helper is caught too;
    * :mod:`ccf.products.resolver` does call it, which is the positive control:
      an AST scan that found it nowhere would pass the first half vacuously.
    """
    for runner in (run_gates, run_federated_gates):
        source = inspect.getsource(runner)
        bodies = [source] + [
            inspect.getsource(getattr(gates_module, helper))
            for helper in sorted(_helper_names_called_in(source))
        ]
        for body in bodies:
            calls = {
                node.func.id
                for node in ast.walk(ast.parse(textwrap.dedent(body)))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            assert "refuse_over_tolerance" not in calls, (
                f"{runner.__name__} reaches the tolerance step; withholding"
                " fulfillment is not a gate (D-IMPL-237, D-IMPL-251 C1/C2)"
            )

    # The positive control: the scan finds it where it does live.
    resolver_calls = {
        node.func.id
        for node in ast.walk(ast.parse(inspect.getsource(resolver_module)))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "refuse_over_tolerance" in resolver_calls

    # And the kind is not a gate token by construction, not by convention.
    assert not issubclass(ToleranceExceededRefusal, GateRefusal)
    assert "gate" not in ToleranceExceededRefusal.model_fields
    assert REFUSAL_KINDS[ToleranceExceededRefusal] not in (
        RUN_GATES_TOKENS | RUN_FEDERATED_GATES_TOKENS
    )


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
