"""15.2-11 — D-09 attestation enforcement: the pre-check and the gate path.

The two-layer design, each layer pinned by a test that fails if it is done
wrong:

1. **The pre-execute check is a returned value, issuing zero queries** —
   ``ProjectionEngine.check_source_attestation`` consults only the reader's
   ``attestation`` property and the class's accepted-mode sets, returns the
   :class:`~ccf.products.gates.AttestationRefusal` naming the failing
   dimension (never raises), and a counting stub proves no query and no
   ``as_of`` ran on a refused check — the refusal lands before a byte moves.
2. **Accepted modes are an explicit opt-in** — a class declaring the tier-2
   modes accepts the tier-2 stub; the defaulted class refuses it
   (deny-by-default, the tier-1 posture every pre-attestation class already
   lived under).
3. **The gate path is structural** — ``run_gates`` refuses a candidate whose
   pinned ``source_attestation`` is below the class's accepted modes, so no
   :class:`~ccf.products.gates.ServableProduct` exists for it even when the
   caller skipped the pre-check; a tier-1 pin against a defaulted class
   passes; a ``None`` pin passes — the compatibility posture for records
   produced before attestation existed.
4. **No signature widened** — ``execute()`` still returns exactly
   ``ExecutionResult``; the refusal channel is the pre-check and the gate
   union, never a widened execute return.

Every domain value — classes, thresholds, TTLs, the boundary — comes from
``tests/fixtures/banking/*.yaml`` via the quickstart wiring, the same reuse
discipline as ``tests/projection/test_segmentation.py``. The attestation
modes themselves are SDK mechanism vocabulary (D-09), not domain values.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, get_type_hints

import pytest

from ccf.boot import boot
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
    SourceAttestation,
)
from ccf.products.contract import (
    MaxTTL,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import (
    GATE_SOURCE_ATTESTATION,
    AttestationRefusal,
    ServableProduct,
    run_gates,
)
from ccf.projection.engine import ExecutionResult, ProjectionEngine

from tests.integration.test_proto_quickstart import (
    _candidate,
    _envelopes,
    _Fabric,
    _load,
    _operators,
    _product_class,
    _resolution_spec,
)
from tests.projection.test_segmentation import (
    NO_SIMILARITY,
    _perspective,
    _plan,
)
from tests.composition import register_at_composition

#: The three well-known attestation values (D-09): three values of one schema.
TIER_1 = SourceAttestation(
    policy_binding="assembly-stamped", lineage="graph-supplied", peer=None
)
TIER_2 = SourceAttestation(
    policy_binding="admission-verified", lineage="product-carried", peer=None
)
TIER_3 = SourceAttestation(policy_binding="none", lineage="none", peer=None)


# --- fixtures: the booted banking fabric (quickstart wiring, reused) --------


@pytest.fixture(scope="module")
def ontology() -> Any:
    return _load("ontology.yaml")


@pytest.fixture(scope="module")
def control() -> Any:
    return _load("controlplane.yaml")


@pytest.fixture(scope="module")
def events() -> Any:
    return _load("events.yaml")


@pytest.fixture
def fabric(
    tmp_path: Path, ontology: Any, control: Any, events: Any
) -> Iterator[_Fabric]:
    """Boot a fabric from the fixtures and ingest the whole event stream."""
    keys = control["keys"]
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = register_at_composition(registry, keys["policy_bundle"], control["policy_bundle"]
    )
    handle = boot(
        backend="sqlite",
        connection={"database_path": tmp_path / "acme-bank.sqlite3"},
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
        tenant_ids=(ontology["tenant_id"],),
    )
    try:
        for envelope in _envelopes(ontology, events):
            handle.worker.ingest(envelope)
        yield _Fabric(
            handle=handle,
            registry=registry,
            policy_version=policy_version,
            ontology=ontology,
            control=control,
        )
    finally:
        handle.close()


class _StubSource:
    """A ``GraphReader``-shaped source reporting a fixed attestation.

    Counts every read so a test can assert the pre-check's zero-query claim:
    ``check_source_attestation`` touches only the ``attestation`` property,
    and a refused check must leave this counter at zero.
    """

    def __init__(self, attestation: SourceAttestation) -> None:
        self._attestation = attestation
        self.reads = 0

    @property
    def attestation(self) -> SourceAttestation:
        return self._attestation

    def query(self, q: GraphQuery) -> GraphView:
        self.reads += 1
        return GraphView(tenant_id=q.tenant_id, as_of=q.as_of)

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        self.reads += 1
        return GraphView(tenant_id=tenant_id, as_of=at)

    def entity_history(
        self, *, tenant_id: str, entity_uri: str
    ) -> tuple[EntityRecord, ...]:
        self.reads += 1
        return ()

    def relationship_history(
        self, *, tenant_id: str, relationship_key: str
    ) -> tuple[RelationshipRecord, ...]:
        self.reads += 1
        return ()


def _engine(fabric: _Fabric, source: _StubSource) -> ProjectionEngine:
    return ProjectionEngine(reader=source, registry=_operators(fabric))


def _tier2_accepting_class(fabric: _Fabric) -> RegisteredProductClass:
    """Register the fixture class with the explicit tier-2 opt-in (D-09)."""
    declared = fabric.control["product_class"]
    max_ttl_version = register_at_composition(fabric.registry, fabric.control["keys"]["max_ttl"],
        MaxTTL(seconds=fabric.control["max_ttl_seconds"]),
    )
    return register_product_class(
        registry=fabric.registry,
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        ttl_anchor=declared["ttl_anchor"],
        assembly_mode=declared["assembly_mode"],
        max_ttl_key=fabric.control["keys"]["max_ttl"],
        max_ttl_version=max_ttl_version,
        accepted_policy_binding_modes=frozenset(
            {"assembly-stamped", "admission-verified"}
        ),
        accepted_lineage_modes=frozenset(
            {"graph-supplied", "product-carried"}
        ),
    )


# --- 1. the pre-check: a returned value, zero queries ------------------------


def test_the_precheck_refuses_a_tier2_source_for_a_defaulted_class(
    fabric: _Fabric,
) -> None:
    """Deny-by-default: the tier-1 defaults refuse tier-2, naming the dimension.

    The refusal is a *returned value* — the call sits under no
    ``pytest.raises`` and completes normally — and the counting stub proves
    zero queries were issued on the refused check.
    """
    source = _StubSource(TIER_2)
    refused = _engine(fabric, source).check_source_attestation(
        product_class=_product_class(fabric)
    )

    assert isinstance(refused, AttestationRefusal)
    assert refused.gate == GATE_SOURCE_ATTESTATION
    # policy_binding is checked first, so it is the named dimension here.
    assert refused.failing_dimension == "policy_binding"
    assert refused.source_mode == "admission-verified"
    assert refused.accepted_modes == frozenset({"assembly-stamped"})
    assert source.reads == 0


def test_the_precheck_refuses_a_tier3_source_for_a_defaulted_class(
    fabric: _Fabric,
) -> None:
    """Tier 3 is expressible today and refused by default (D-09 no-refactor)."""
    source = _StubSource(TIER_3)
    refused = _engine(fabric, source).check_source_attestation(
        product_class=_product_class(fabric)
    )

    assert isinstance(refused, AttestationRefusal)
    assert refused.failing_dimension == "policy_binding"
    assert refused.source_mode == "none"
    assert source.reads == 0


def test_the_refusal_names_the_lineage_dimension_when_that_is_the_gap(
    fabric: _Fabric,
) -> None:
    """The failing dimension is a per-dimension fact, not an aggregate."""
    declared = fabric.control["product_class"]
    max_ttl_version = register_at_composition(fabric.registry, fabric.control["keys"]["max_ttl"],
        MaxTTL(seconds=fabric.control["max_ttl_seconds"]),
    )
    # Policy binding accepts both modes; lineage keeps the tier-1 default —
    # so the tier-2 stub's gap is exactly the lineage dimension.
    partially_accepting = register_product_class(
        registry=fabric.registry,
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        ttl_anchor=declared["ttl_anchor"],
        assembly_mode=declared["assembly_mode"],
        max_ttl_key=fabric.control["keys"]["max_ttl"],
        max_ttl_version=max_ttl_version,
        accepted_policy_binding_modes=frozenset(
            {"assembly-stamped", "admission-verified"}
        ),
    )
    refused = _engine(fabric, _StubSource(TIER_2)).check_source_attestation(
        product_class=partially_accepting
    )

    assert isinstance(refused, AttestationRefusal)
    assert refused.failing_dimension == "lineage"
    assert refused.source_mode == "product-carried"
    assert refused.accepted_modes == frozenset({"graph-supplied"})


def test_a_class_declaring_the_tier2_modes_accepts_the_tier2_source(
    fabric: _Fabric,
) -> None:
    """The opt-in: acceptance is authored, per dimension, never inferred."""
    source = _StubSource(TIER_2)
    outcome = _engine(fabric, source).check_source_attestation(
        product_class=_tier2_accepting_class(fabric)
    )
    assert outcome is None
    assert source.reads == 0


def test_the_live_graph_passes_the_defaulted_class(fabric: _Fabric) -> None:
    """Tier 1 against tier-1 defaults: every existing deployment's shape."""
    engine = ProjectionEngine(
        reader=fabric.handle.reader, registry=_operators(fabric)
    )
    assert (
        engine.check_source_attestation(product_class=_product_class(fabric))
        is None
    )


# --- 2. the gate path: structural, pre-check skipped -------------------------


def _execute(fabric: _Fabric) -> ExecutionResult:
    return ProjectionEngine(
        reader=fabric.handle.reader, registry=_operators(fabric)
    ).execute(
        plan=_plan(fabric, NO_SIMILARITY),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )


def test_run_gates_refuses_a_below_accepted_modes_pin(fabric: _Fabric) -> None:
    """A candidate pinned below the class's modes never becomes servable.

    The candidate itself passes all three canonical gates — same declaration,
    same TTL — so the refusal isolates the additive attestation gate: the
    structural layer that holds even when a caller skipped the pre-check.
    """
    execution = _execute(fabric)
    product_class = _product_class(fabric)
    refused = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
        source_attestation=TIER_2,
    )

    assert isinstance(refused, AttestationRefusal)
    assert not isinstance(refused, ServableProduct)
    assert refused.gate == GATE_SOURCE_ATTESTATION
    assert refused.failing_dimension == "policy_binding"


def test_run_gates_passes_a_tier1_pin_against_a_defaulted_class(
    fabric: _Fabric,
) -> None:
    """The governed path: the engine's own pin is tier 1 and it passes."""
    execution = _execute(fabric)
    product_class = _product_class(fabric)
    # The engine pinned the live reader's attestation unconditionally.
    assert execution.source_attestation == TIER_1
    gated = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
        source_attestation=execution.source_attestation,
    )
    assert isinstance(gated, ServableProduct)


def test_run_gates_passes_a_none_pin(fabric: _Fabric) -> None:
    """Compatibility: a ``None`` pin — a record produced before attestation
    existed, or a bypassing caller against a pre-phase reader — passes, and
    every pre-attestation call site (which passes nothing) is unchanged."""
    execution = _execute(fabric)
    product_class = _product_class(fabric)
    explicit_none = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
        source_attestation=None,
    )
    assert isinstance(explicit_none, ServableProduct)

    omitted = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
    )
    assert isinstance(omitted, ServableProduct)


def test_a_tier2_accepting_class_passes_the_tier2_pin_at_the_gate(
    fabric: _Fabric,
) -> None:
    """The gate-path twin of the pre-check opt-in test."""
    execution = _execute(fabric)
    gated = run_gates(
        _candidate(fabric, execution, _tier2_accepting_class(fabric)),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=_tier2_accepting_class(fabric),
        source_attestation=TIER_2,
    )
    assert isinstance(gated, ServableProduct)


# --- 3. no signature widened -------------------------------------------------


def test_execute_still_returns_exactly_execution_result() -> None:
    """The placement decision, grep-assertable: ``execute()`` was not widened.

    The refusal channel is the pre-check (``AttestationRefusal | None``) and
    the gate union (``ServableProduct | GateRefusal``) — never a silently
    widened execute return.
    """
    hints = get_type_hints(ProjectionEngine.execute)
    assert hints["return"] is ExecutionResult

    check_hints = get_type_hints(ProjectionEngine.check_source_attestation)
    assert check_hints["return"] == (AttestationRefusal | None)


def test_a_pre_phase_reader_yields_a_none_pin_and_passes(
    fabric: _Fabric,
) -> None:
    """A reader written before the ``attestation`` property existed still
    executes — the compatibility promise — and its execution pins ``None``,
    which the gate passes and dimension 1 records as the positive
    "no attestation was reported" claim."""

    class _PrePhaseReader:
        """Delegates reads; predates the ``attestation`` property."""

        def __init__(self) -> None:
            self._inner = fabric.handle.reader

        def query(self, q: GraphQuery) -> GraphView:
            return self._inner.query(q)

        def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
            return self._inner.as_of(tenant_id=tenant_id, at=at)

        def entity_history(
            self, *, tenant_id: str, entity_uri: str
        ) -> tuple[EntityRecord, ...]:
            return self._inner.entity_history(
                tenant_id=tenant_id, entity_uri=entity_uri
            )

        def relationship_history(
            self, *, tenant_id: str, relationship_key: str
        ) -> tuple[RelationshipRecord, ...]:
            return self._inner.relationship_history(
                tenant_id=tenant_id, relationship_key=relationship_key
            )

    engine = ProjectionEngine(
        reader=_PrePhaseReader(), registry=_operators(fabric)
    )
    product_class = _product_class(fabric)
    assert engine.check_source_attestation(product_class=product_class) is None

    execution = engine.execute(
        plan=_plan(fabric, NO_SIMILARITY),
        perspective=_perspective(fabric),
        tenant_id=fabric.tenant_id,
        temporal_boundary=fabric.boundary,
    )
    assert execution.source_attestation is None
    gated = run_gates(
        _candidate(fabric, execution, product_class),
        engine_resolved=execution.operators_invoked,
        now=fabric.now,
        registry=fabric.registry,
        product_class=product_class,
        source_attestation=execution.source_attestation,
    )
    assert isinstance(gated, ServableProduct)
