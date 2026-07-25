"""Hash-verified re-hydration: a served decision reproduced exactly (FABR-06).

Whitepaper §7.10 (a decision is forensically reconstructible years later
against the exact fabric state at decision time); D-IMPL-06 (the snapshot is
*logical* — a temporal boundary plus a manifest, never a physical copy);
D-IMPL-26 (resolution is exact-version, never "latest"); D-IMPL-44 (the
re-hydration path). Written before the engine, per D-15: replay is invariant
surface, so the shape is asserted before it is built.

The load-bearing test in this module is
``test_the_product_replays_exactly_after_the_graph_has_moved_on``. Reproducing
a product from a graph that has not changed proves almost nothing — it is a
determinism check the operator suite already makes. The claim replay actually
owes is that a decision made in March still reproduces in July, after the
entities it read have been superseded twice. That is only possible because the
graph is append-only and bitemporal, and this test is where that stops being an
architectural assertion and becomes an executed one.

Everything domain-shaped here — entity classes, identifiers, operator
parameters, the projection — is test fixture. The engine under test knows none
of it, which is the point: it re-executes what the record says ran.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    RegisteredProductClass,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import ExecutionResult, OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
from ccf.replay import engine as engine_module
from ccf.replay import snapshots as snapshots_module
from ccf.replay.engine import (
    ReplayDivergence,
    ReplayOutcome,
    ReplayUnresolvable,
    replay,
)
from ccf.replay.record import (
    DecisionReplayRecord,
    PolicyBinding,
    build_replay_record,
)
from ccf.replay.serve import ReplayWriter, serve
from ccf.replay.snapshots import SnapshotReader, SnapshotScopeViolation
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT = "tenant-replay"
T_MARCH = datetime(2026, 3, 1, tzinfo=UTC)
BOUNDARY = datetime(2026, 3, 15, tzinfo=UTC)
NOW = datetime(2026, 3, 15, 12, tzinfo=UTC)
T_JULY = datetime(2026, 7, 1, tzinfo=UTC)

POLICY_BUNDLE_KEY = "test/policy-bundle"
MAX_TTL_KEY = "test/max-ttl"
PLAN_ID = "test/exposure-summary"
ARTIFACT_CLASS = "decision-replay-record"
SCHEMA_NAME = "test.exposure-summary"
SCHEMA_VERSION = "1.0.0"
PRODUCT_TTL_SECONDS = 600


def _envelope(
    *, envelope_id: str, payload: Mapping[str, Any], observed_time: datetime
) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=TENANT,
        envelope_id=envelope_id,
        source=SourceIdentity(system_id="core-banking"),
        ingestion_timestamp=observed_time,
        observed_time=observed_time,
        raw_payload=dict(payload),
    )


class _SummaryPlan:
    """The deployment's Π — thin, and entirely test-owned."""

    def required_operators(self) -> tuple[str, ...]:
        return ("temporal.as-of-boundary", "traversal.typed-neighborhood")

    @property
    def plan_id(self) -> str:
        return PLAN_ID

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=PLAN_ID,
            payload={
                "role": perspective.role,
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "name": record.claim.attributes.get("counterparty_name", ""),
                    }
                    for record in view.entities
                ],
            },
        )


class _Deployment:
    """Everything a replay needs, wired the way a deployment wires it."""

    def __init__(
        self,
        *,
        handle: "FabricHandle",
        store: FileArtifactStore,
        policy_version: str,
        depth_limit: int = 1,
    ) -> None:
        self.handle = handle
        self.store = store
        self.policy_version = policy_version
        self.depth_limit = depth_limit
        self.registry: ControlPlaneRegistry = handle.registry  # type: ignore[assignment]

    def operators(self, *, depth_limit: int | None = None) -> OperatorRegistry:
        registry = OperatorRegistry()
        registry.register(
            TemporalAsOf(
                parameters=TemporalAsOfParameters(require_valid_at_boundary=True)
            )
        )
        registry.register(
            TraversalNeighborhood(
                parameters=TraversalNeighborhoodParameters(
                    seed_entity_classes=frozenset({"counterparty"}),
                    relationship_types=frozenset({"obligor_of"}),
                    depth_limit=self.depth_limit if depth_limit is None else depth_limit,
                )
            )
        )
        return registry

    def perspective(self) -> Perspective:
        return Perspective(principal_id="analyst-7", role="credit-analyst")

    def execute(self, *, registry: OperatorRegistry | None = None) -> ExecutionResult:
        return ProjectionEngine(
            reader=self.handle.reader, registry=registry or self.operators()
        ).execute(
            plan=_SummaryPlan(),
            perspective=self.perspective(),
            tenant_id=TENANT,
            temporal_boundary=BOUNDARY,
        )

    def product_class(self) -> RegisteredProductClass:
        max_ttl_version = self.registry.register(MAX_TTL_KEY, MaxTTL(seconds=3600))
        return register_product_class(
            registry=self.registry,
            schema_name=SCHEMA_NAME,
            schema_version=SCHEMA_VERSION,
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key=MAX_TTL_KEY,
            max_ttl_version=max_ttl_version,
        )

    def candidate(self, execution: ExecutionResult) -> ContextProductContract:
        return ContextProductContract(
            schema_name=SCHEMA_NAME,
            schema_version=SCHEMA_VERSION,
            plan_id=execution.plan_id,
            tenant_id=TENANT,
            temporal_boundary=BOUNDARY,
            expires_at=NOW + timedelta(seconds=PRODUCT_TTL_SECONDS),
            ttl_anchor="from_decision",
            lineage=ProductLineage(
                operators_invoked=execution.operators_invoked,
                policy_bundle_versions=frozenset({self.policy_version}),
                graph_snapshot_at=BOUNDARY,
            ),
            payload=execution.projection.payload,
        )


class _Environment:
    """The deployment side of replay: what ran, and what the product looked like.

    The SDK cannot know a deployment's projections, operator parameters, or
    product envelope — they are user code and user configuration. So replay
    takes them as a seam, and *verifies* the deployment's answer against the
    record rather than trusting it.
    """

    def __init__(self, deployment: _Deployment, *, depth_limit: int | None = None) -> None:
        self._deployment = deployment
        self._depth_limit = depth_limit
        self._plans: dict[str, ProjectionPlan] = {PLAN_ID: _SummaryPlan()}

    def resolve_plan(self, *, plan_id: str) -> ProjectionPlan:
        try:
            return self._plans[plan_id]
        except KeyError:
            raise LookupError(plan_id) from None

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> OperatorRegistry:
        return self._deployment.operators(depth_limit=self._depth_limit)

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        return ContextProductContract(
            schema_name=SCHEMA_NAME,
            schema_version=SCHEMA_VERSION,
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=NOW + timedelta(seconds=PRODUCT_TTL_SECONDS),
            ttl_anchor="from_decision",
            lineage=ProductLineage(
                operators_invoked=frozenset(
                    record.content_generation_path.operator_plan
                ),
                policy_bundle_versions=frozenset(
                    binding.version for binding in record.policy_bindings.bindings
                ),
                graph_snapshot_at=record.context_fabric_snapshot.temporal_boundary,
            ),
            payload=projection.payload,
        )


@pytest.fixture
def deployment(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> Iterator[_Deployment]:
    handle = fabric_boot()
    handle.worker.ingest(
        _envelope(
            envelope_id="env-001",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Freight",
                "jurisdiction": "US",
                "facility_id": "FAC-1",
                "facility_type": "revolver",
                "currency": "USD",
            },
            observed_time=T_MARCH,
        )
    )
    policy_version = handle.registry.register(
        POLICY_BUNDLE_KEY, {"regime": "replay-fixture"}
    )
    yield _Deployment(
        handle=handle,
        store=FileArtifactStore(root=tmp_path / "artifacts"),
        policy_version=policy_version,
    )


def _serve(deployment: _Deployment) -> tuple[str, DecisionReplayRecord]:
    """Run the real serve path; return the record's address and the record."""
    execution = deployment.execute()
    product_class = deployment.product_class()
    gated = run_gates(
        deployment.candidate(execution),
        engine_resolved=execution.operators_invoked,
        now=NOW,
        registry=deployment.registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct)
    record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=deployment.perspective(),
        policy_bindings=(
            PolicyBinding(key=POLICY_BUNDLE_KEY, version=deployment.policy_version),
        ),
        assembly_mode="algorithmic",
        recorded_at=NOW,
    )
    served = serve(
        product=gated,
        record=record,
        replay_writer=ReplayWriter(
            store=deployment.store, artifact_class=ARTIFACT_CLASS
        ),
    )
    return served.replay_ref.content_address, record


def _replay(deployment: _Deployment, address: str, **kwargs: Any) -> ReplayOutcome:
    return replay(
        record_address=address,
        store=kwargs.pop("store", deployment.store),
        reader=deployment.handle.reader,
        control_plane=kwargs.pop("control_plane", deployment.registry),
        environment=kwargs.pop("environment", _Environment(deployment)),
    )


# --- the claim: exact reproduction -----------------------------------------


def test_replay_reproduces_the_product_at_the_recorded_content_address(
    deployment: _Deployment,
) -> None:
    address, record = _serve(deployment)
    outcome = _replay(deployment, address)
    assert outcome.product_content_address == (
        record.content_generation_path.product_content_address
    )
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )
    assert outcome.record == record


def test_the_product_replays_exactly_after_the_graph_has_moved_on(
    deployment: _Deployment,
) -> None:
    """The claim replay actually owes (whitepaper §7.10, INV-CH7-04/14).

    Four months later the counterparty has been renamed and a second facility
    exists. The March decision still reproduces byte-for-byte, because the
    March claims were superseded rather than overwritten and the as-of read at
    the recorded boundary cannot see July.
    """
    address, record = _serve(deployment)

    deployment.handle.worker.ingest(
        _envelope(
            envelope_id="env-002",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Logistics PLC",
                "jurisdiction": "GB",
                "facility_id": "FAC-2",
                "facility_type": "term",
                "currency": "GBP",
            },
            observed_time=T_JULY,
        )
    )
    later = deployment.handle.reader.as_of(tenant_id=TENANT, at=T_JULY)
    assert any(
        record_.claim.attributes.get("counterparty_name")
        == "Northwind Logistics PLC"
        for record_ in later.entities
    )

    outcome = _replay(deployment, address)
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )
    assert outcome.graph_snapshot_id == (
        record.context_fabric_snapshot.graph_snapshot_id
    )
    assert outcome.product.payload["entities"][0]["name"] == "Northwind Freight"


def test_the_as_of_view_is_byte_identical_after_the_graph_moves_on(
    deployment: _Deployment,
) -> None:
    """INV-CH7-14, asserted on bytes — the precondition replay stands on.

    "Claims superseded later are still current" has to mean *current*, not
    "present but carrying a pointer to their replacement". Likewise a lineage
    entry the fabric had not received yet is future information. Either leak
    changes the content hash of a view that must be identical to the one the
    decision saw, and would make every replay after any subsequent write
    diverge for a reason that has nothing to do with the decision.
    """
    before = deployment.handle.reader.as_of(tenant_id=TENANT, at=BOUNDARY)
    deployment.handle.worker.ingest(
        _envelope(
            envelope_id="env-later",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Logistics PLC",
                "jurisdiction": "GB",
            },
            observed_time=T_JULY,
        )
    )
    after = deployment.handle.reader.as_of(tenant_id=TENANT, at=BOUNDARY)
    assert content_hash(after) == content_hash(before)


def test_replay_is_idempotent(deployment: _Deployment) -> None:
    address, _record = _serve(deployment)
    assert content_hash(_replay(deployment, address)) == content_hash(
        _replay(deployment, address)
    )


# --- unresolvable: refuse, never substitute --------------------------------


def test_an_unstored_record_address_is_unresolvable(
    deployment: _Deployment,
) -> None:
    with pytest.raises(ReplayUnresolvable):
        _replay(deployment, content_hash({"never": "stored"}))


def test_a_missing_policy_version_is_unresolvable_not_substituted(
    deployment: _Deployment,
) -> None:
    """D-IMPL-26/D-IMPL-38: no fallback, no nearest match, no "latest".

    A control plane that has lost the bundle version the decision was made
    under cannot answer what that decision saw. The only honest outcome is a
    refusal.
    """
    address, _record = _serve(deployment)
    amnesiac = ControlPlaneRegistry()
    with pytest.raises(ReplayUnresolvable, match="policy binding"):
        _replay(deployment, address, control_plane=amnesiac)


def test_an_unresolvable_projection_plan_is_refused(
    deployment: _Deployment,
) -> None:
    class _Empty(_Environment):
        def resolve_plan(self, *, plan_id: str) -> ProjectionPlan:
            raise LookupError(plan_id)

    address, _record = _serve(deployment)
    with pytest.raises(ReplayUnresolvable, match="projection plan"):
        _replay(deployment, address, environment=_Empty(deployment))


# --- divergence: report, never paper over ----------------------------------


def test_drifted_operator_parameters_diverge_rather_than_silently_replay(
    deployment: _Deployment,
) -> None:
    """A parameter change is an identity change (INV-CH7-23).

    Re-running with a different traversal depth produces a different
    ``parameter_hash``, so the replay's step sequence no longer matches the
    recorded one. Reporting that as divergence rather than returning the
    freshly-computed product is the whole difference between replay and
    re-computation.
    """
    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="step"):
        _replay(
            deployment, address, environment=_Environment(deployment, depth_limit=3)
        )


def test_a_rehydrated_product_that_does_not_match_is_divergence(
    deployment: _Deployment,
) -> None:
    class _Wrong(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            return product.model_copy(update={"schema_version": "9.9.9"})

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_Wrong(deployment))


# --- the logical snapshot (D-IMPL-06) --------------------------------------


def test_the_snapshot_reader_refuses_a_read_outside_the_snapshot(
    deployment: _Deployment,
) -> None:
    """The snapshot is a *scope*, not a suggestion.

    A replay that could read at any instant it liked would be re-computation
    wearing a snapshot's name. The reader pins the tenant and the boundary and
    refuses everything else, so a projection that reached past the boundary
    fails loudly instead of silently importing the future.
    """
    _address, record = _serve(deployment)
    reader = SnapshotReader(
        reader=deployment.handle.reader, snapshot=record.context_fabric_snapshot
    )
    view = reader.as_of(tenant_id=TENANT, at=BOUNDARY)
    assert view.as_of == BOUNDARY

    with pytest.raises(SnapshotScopeViolation):
        reader.as_of(tenant_id=TENANT, at=T_JULY)
    with pytest.raises(SnapshotScopeViolation):
        reader.as_of(tenant_id="tenant-other", at=BOUNDARY)


def test_the_snapshot_holds_no_physical_copy_of_the_graph(
    deployment: _Deployment,
) -> None:
    """D-IMPL-06: boundary + tenant + watermark + manifest, and nothing else."""
    _address, record = _serve(deployment)
    snapshot = record.context_fabric_snapshot
    assert set(type(snapshot).model_fields) == {
        "graph_snapshot_id",
        "tenant_id",
        "temporal_boundary",
        "store_watermark",
        "touched_entities",
        "touched_relationships",
    }


# --- structural: no moving targets on the replay path ----------------------


def test_the_replay_path_never_resolves_latest() -> None:
    """CLAUDE.md §7.4, asserted against the source rather than against habit."""
    for module in (engine_module, snapshots_module):
        source = inspect.getsource(module)
        assert "resolve_latest" not in source, module.__name__
