"""The three validation gates are the only construction path of a product.

Whitepaper §6.3 / §7.6 (INV-CH7-46/47/48); DESIGN.md §2B.3. Written before the
implementation per D-15 (TDD on contracts and invariants).

What these tests pin down, in the order the gates run:

1. an empty ``operators_invoked`` set is refused — a product nothing computed
   is not a cheap product, it is a forged one;
2. the declared operator set must *equal* the engine-resolved set, in both
   directions: omission and forgery are the same defect wearing different
   faces;
3. ``now < expires_at <= now + MAX_TTL``, with MAX_TTL resolved from the
   Control Plane and no SDK default anywhere (D-IMPL-39);
4. a candidate failing several gates reports the *first* in sequence, because
   the order encodes the priority of the questions;
5. the servable type cannot be constructed outside the gate module.

Every value the fixtures use is fixture data. ``now`` is a literal instant
supplied by the test, never a clock read.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductClassRegistrationError,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    EmptyOperatorRefusal,
    GateBypassError,
    LineageMismatchRefusal,
    ServableProduct,
    TTLRefusal,
    run_gates,
)
from tests.controlplane.composition import compose_register

# Fixture values (test-side vocabulary, never SDK values).
TENANT = "tenant-fixture"
MAX_TTL_KEY = "test/product/max-ttl"
MAX_TTL_SECONDS = 900
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
POLICY_VERSION = "policy-version-fixture"
OPERATORS = frozenset({"policy.principal-subgraph", "traversal.typed-neighborhood"})


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


@pytest.fixture
def product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    version = compose_register(registry, MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
    return register_product_class(
        registry=registry,
        schema_name="fixture.exposure-summary",
        schema_version="1.0.0",
        ttl_anchor="from_decision",
        assembly_mode="algorithmic",
        max_ttl_key=MAX_TTL_KEY,
        max_ttl_version=version,
    )


def candidate(
    *,
    product_class: RegisteredProductClass,
    operators: frozenset[str] = OPERATORS,
    expires_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
) -> ContextProductContract:
    """Build a product candidate; every gate-relevant field is overridable."""
    return ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id="fixture.plan",
        tenant_id=TENANT,
        temporal_boundary=BOUNDARY,
        expires_at=expires_at or (NOW + timedelta(seconds=60)),
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=operators,
            policy_bundle_versions=frozenset({POLICY_VERSION}),
            graph_snapshot_at=BOUNDARY,
        ),
        payload=payload or {},
    )


# --- the happy path --------------------------------------------------------


def test_a_conforming_candidate_becomes_servable(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    result = run_gates(
        candidate(product_class=product_class),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, ServableProduct)
    assert result.product.lineage.operators_invoked == OPERATORS


# --- gate 1: empty-operator guard (INV-CH7-46) -----------------------------


def test_an_empty_operator_set_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    result = run_gates(
        candidate(product_class=product_class, operators=frozenset()),
        engine_resolved=frozenset(),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, EmptyOperatorRefusal)
    # A refusal is structured data carrying the failing detail, never a bare
    # None and never a silently-degraded product.
    assert result.gate
    assert result.detail


# --- gate 2: lineage strict equality (INV-CH7-47) --------------------------


def test_declaring_an_operator_that_did_not_run_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Forgery: the product claims provenance it does not have."""
    result = run_gates(
        candidate(product_class=product_class, operators=OPERATORS | {"forged.op"}),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, LineageMismatchRefusal)
    assert "forged.op" in result.declared
    assert "forged.op" not in result.resolved


def test_omitting_an_operator_that_did_run_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Omission: strict *equality*, not containment — both directions fail."""
    declared = frozenset({"policy.principal-subgraph"})
    result = run_gates(
        candidate(product_class=product_class, operators=declared),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, LineageMismatchRefusal)
    assert result.declared == declared
    assert result.resolved == OPERATORS


# --- gate 3: TTL bounds (INV-CH7-48) ---------------------------------------


def test_an_already_expired_product_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    result = run_gates(
        candidate(product_class=product_class, expires_at=NOW - timedelta(seconds=1)),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, TTLRefusal)


def test_expiry_exactly_at_now_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The bound is ``now < expires_at``: a product expiring now is expired."""
    result = run_gates(
        candidate(product_class=product_class, expires_at=NOW),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, TTLRefusal)


def test_expiry_beyond_max_ttl_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    result = run_gates(
        candidate(
            product_class=product_class,
            expires_at=NOW + timedelta(seconds=MAX_TTL_SECONDS + 1),
        ),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, TTLRefusal)
    assert result.max_ttl_seconds == MAX_TTL_SECONDS


def test_expiry_exactly_at_max_ttl_is_allowed(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The upper bound is inclusive: ``expires_at <= now + MAX_TTL``."""
    result = run_gates(
        candidate(
            product_class=product_class,
            expires_at=NOW + timedelta(seconds=MAX_TTL_SECONDS),
        ),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, ServableProduct)


def test_max_ttl_is_read_from_the_control_plane_at_gate_time(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The bound comes from the registry, not from a constant in the SDK.

    Asserted by observation: the gate run leaves a resolve of the MAX_TTL
    artifact in the Control Plane audit log.
    """
    run_gates(
        candidate(product_class=product_class),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert any(
        event.action == "resolve"
        and event.key == MAX_TTL_KEY
        and event.version == product_class.max_ttl_version
        for event in registry.audit_events()
    )


# --- gate ordering ---------------------------------------------------------


def test_a_candidate_failing_every_gate_reports_the_first(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Order is part of the contract: empty-operator, then lineage, then TTL."""
    result = run_gates(
        candidate(
            product_class=product_class,
            operators=frozenset(),
            expires_at=NOW - timedelta(seconds=1),
        ),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, EmptyOperatorRefusal)


def test_lineage_is_checked_before_ttl(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    result = run_gates(
        candidate(
            product_class=product_class,
            operators=frozenset({"only.one"}),
            expires_at=NOW - timedelta(seconds=1),
        ),
        engine_resolved=OPERATORS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, LineageMismatchRefusal)


# --- MAX_TTL registration discipline (D-IMPL-39) ---------------------------


def test_registering_a_product_class_without_a_max_ttl_fails(
    registry: ControlPlaneRegistry,
) -> None:
    """An unregistered MAX_TTL is a registration failure, not a runtime one."""
    with pytest.raises(ProductClassRegistrationError):
        register_product_class(
            registry=registry,
            schema_name="fixture.unregistered",
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key="test/product/never-registered",
            max_ttl_version="0" * 64,
        )


def test_registering_against_a_non_max_ttl_artifact_fails(
    registry: ControlPlaneRegistry,
) -> None:
    """A key that exists but holds the wrong artifact is equally a failure."""
    version = compose_register(registry, MAX_TTL_KEY, {"seconds": MAX_TTL_SECONDS})
    with pytest.raises(ProductClassRegistrationError):
        register_product_class(
            registry=registry,
            schema_name="fixture.mistyped",
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key=MAX_TTL_KEY,
            max_ttl_version=version,
        )


# --- the gates are the only construction path ------------------------------


def test_direct_construction_of_a_servable_product_is_refused(
    product_class: RegisteredProductClass,
) -> None:
    """The one way to hold a servable product is to have passed the gates.

    Enforced the same way single-writer is (04-RESEARCH.md Pattern 4): a
    private token the gate module alone can produce. No unforced path exists.
    """
    with pytest.raises(GateBypassError):
        ServableProduct(candidate(product_class=product_class), object())


def test_the_contract_base_forbids_unknown_fields(
    product_class: RegisteredProductClass,
) -> None:
    """``extra=forbid`` all the way down — an unvalidated product is a type
    error, not a served product (DESIGN.md §9)."""
    with pytest.raises(Exception):
        ContextProductContract(
            **candidate(product_class=product_class).model_dump(),
            smuggled="value",
        )
