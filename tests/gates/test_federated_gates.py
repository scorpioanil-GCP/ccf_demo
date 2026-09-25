"""The federated gate sequence: attribution where verification cannot travel.

D-IMPL-57, Dave's ruling of 2026-07-27 (reading (a)): INV-CH7-47 is *verifiable
within a fabric, attributable across one*. Products admitted through a Peering
(D-IMPL-59) are attributable; locally assembled products are verifiable. These
tests are written before the implementation per D-15, and each assertion is
drafted from what a *broken* federated sequence would do:

* a sequence that compared the declared operator set against itself would pass
  every case here while checking nothing — which is the defect B1 named, so the
  attributability case is stated in terms of a *mismatch that must refuse*
  rather than in terms of a passing gate;
* a sequence that dropped the empty-operator guard would admit a product
  computed by nothing merely because it arrived signed;
* a sequence that reimplemented the TTL bound would let a federated product age
  under a different ceiling than a local one.

Every value is fixture-side vocabulary. ``now`` is a literal instant.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    GATE_EMPTY_OPERATOR,
    GATE_LINEAGE_ATTRIBUTABILITY,
    GATE_TTL_BOUNDS,
    EmptyOperatorRefusal,
    LineageAttributionRefusal,
    ServableProduct,
    TTLRefusal,
    run_federated_gates,
)
from tests.controlplane.composition import compose_register

TENANT = "tenant-fixture"
MAX_TTL_KEY = "test/federated/max-ttl"
MAX_TTL_SECONDS = 900
NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 2, 11, 59, 0, tzinfo=UTC)
POLICY_VERSION = "policy-version-fixture"
OPERATORS = frozenset({"policy.principal-subgraph", "traversal.typed-neighborhood"})
#: An address no product in this module hashes to — the stand-in for "the bytes
#: whose signature verified were not these bytes".
FOREIGN_ADDRESS = "0" * 64


@pytest.fixture
def registry() -> ControlPlaneRegistry:
    return ControlPlaneRegistry()


@pytest.fixture
def product_class(registry: ControlPlaneRegistry) -> RegisteredProductClass:
    version = compose_register(registry, MAX_TTL_KEY, MaxTTL(seconds=MAX_TTL_SECONDS))
    return register_product_class(
        registry=registry,
        schema_name="fixture.federated-exposure-summary",
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
) -> ContextProductContract:
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
        payload={},
    )


# --- the happy path: attribution holds when the addresses agree ------------


def test_a_candidate_whose_address_matches_the_attested_one_is_servable(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    product = candidate(product_class=product_class)
    result = run_federated_gates(
        product,
        attested_address=content_hash(product),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, ServableProduct)
    assert result.product.lineage.operators_invoked == OPERATORS


# --- gate 1: the empty-operator guard survives the boundary ---------------


def test_a_federated_product_declaring_no_operators_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """A product computed by nothing is not servable, whoever signed it."""
    product = candidate(product_class=product_class, operators=frozenset())
    result = run_federated_gates(
        product,
        attested_address=content_hash(product),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, EmptyOperatorRefusal)
    assert result.gate == GATE_EMPTY_OPERATOR


# --- gate 2: attributability, with a failure mode that is real -------------


def test_a_candidate_whose_address_differs_from_the_attested_one_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The declared lineage must be covered by what the peer actually signed."""
    product = candidate(product_class=product_class)
    result = run_federated_gates(
        product,
        attested_address=FOREIGN_ADDRESS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, LineageAttributionRefusal)
    assert result.gate == GATE_LINEAGE_ATTRIBUTABILITY
    # Both sides of the mismatch, per the module's refusal discipline.
    assert result.attested_address == FOREIGN_ADDRESS
    assert result.candidate_address == content_hash(product)
    assert result.declared == OPERATORS
    assert result.detail


def test_attributability_is_checked_before_ttl(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """Order is part of the contract, as it is on the local path."""
    product = candidate(
        product_class=product_class, expires_at=NOW - timedelta(seconds=1)
    )
    result = run_federated_gates(
        product,
        attested_address=FOREIGN_ADDRESS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, LineageAttributionRefusal)


def test_the_empty_operator_guard_is_checked_before_attributability(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    product = candidate(product_class=product_class, operators=frozenset())
    result = run_federated_gates(
        product,
        attested_address=FOREIGN_ADDRESS,
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, EmptyOperatorRefusal)


# --- gate 3: TTL, the same bound the local path uses ----------------------


def test_an_expired_federated_product_is_refused(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    product = candidate(
        product_class=product_class, expires_at=NOW - timedelta(seconds=1)
    )
    result = run_federated_gates(
        product,
        attested_address=content_hash(product),
        now=NOW,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(result, TTLRefusal)
    assert result.gate == GATE_TTL_BOUNDS
    assert result.max_ttl_seconds == MAX_TTL_SECONDS


def test_the_max_ttl_is_resolved_from_the_control_plane_at_gate_time(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """The federated ceiling is the *same* pinned artifact, not a second one."""
    product = candidate(product_class=product_class)
    run_federated_gates(
        product,
        attested_address=content_hash(product),
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


def test_a_missing_pinned_max_ttl_raises_rather_than_refuses(
    registry: ControlPlaneRegistry, product_class: RegisteredProductClass
) -> None:
    """A broken deployment and a bad product must not report the same way."""
    from ccf.controlplane.registry import ControlPlaneMissing

    product = candidate(product_class=product_class)
    empty = ControlPlaneRegistry()
    with pytest.raises(ControlPlaneMissing):
        run_federated_gates(
            product,
            attested_address=content_hash(product),
            now=NOW,
            registry=empty,
            product_class=product_class,
        )


# --- structural: nothing here witnesses itself ----------------------------


def test_the_federated_sequence_takes_no_engine_resolved_witness() -> None:
    """The producer's own claim is never passed in as its own witness (B1)."""
    parameters = inspect.signature(run_federated_gates).parameters
    assert "engine_resolved" not in parameters
    assert "attested_address" in parameters
