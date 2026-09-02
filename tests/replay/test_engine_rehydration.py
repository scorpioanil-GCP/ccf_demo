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
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphQuery, GraphView
from ccf.controlplane.artifacts import DebtProfile
from ccf.halflife.assessment import (
    NO_DEBT_EVIDENCE,
    NO_OBLIGATION_IN_FORCE,
    NO_SOURCE_REFRESH_RECENCY,
    DebtAssessment,
    DebtEvidencePointer,
    DebtFactors,
    DebtSignal,
    ScorerPin,
    SignalObligation,
    SourceRefreshWindow,
)
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
from ccf.products.request import ProductRequest, request_seeds
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
    ContentGenerationPath,
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

#: The debt this fixture's decision was made with (D-IMPL-99/100). Test-owned
#: values: the factors are a deployment measurement, never an SDK one. Carried
#: on the product, so it is inside the content address the engine checks — which
#: is the whole reason this module is the tripwire for the debt landing.
DEBT = DebtAssessment(
    debt=Decimal("0.28"),
    signal=DebtSignal.OK,
    factors=DebtFactors(
        freshness=Decimal("0.90"),
        completeness=Decimal("0.80"),
        semantic_consistency=Decimal("1.0"),
    ),
    scorers=(
        ScorerPin(
            factor="freshness",
            scorer_id="ccf.reference.freshness-from-decay",
            scorer_version="1.0.0",
        ),
    ),
)

#: What this fixture's debt points at (D-IMPL-118). Test-owned handles: the SDK
#: enumerates none of them and interprets none of them. They are deliberately
#: unreadable as identities — under D-IMPL-119 limb 4 a pointer a reading
#: principal could interpret is refused outright until the assembly path is
#: principal-scoped, so a fixture whose handles spelled entity URIs would be
#: modelling the forbidden shape. Carried on the product, so it is inside the
#: content address the engine checks — which is what makes this module the
#: tripwire for the evidence landing as well as for the debt landing.
EVIDENCE = (
    DebtEvidencePointer(handle="h-7f3a"),
    DebtEvidencePointer(handle="h-c105"),
)

#: The window this fixture's decision believed its sources last published in
#: (D-IMPL-112 gap 2, D-IMPL-117, D-IMPL-124). Test-owned: the SDK enumerates
#: no source vocabulary and declares no cadence, and these instants are
#: deliberately unrelated to ``NOW`` — nothing about this fact may be computed
#: from the fabric's clock, which is the whole reason it is a fact distinct
#: from the freshness figure in ``DEBT`` above. Carried on the product, so it
#: is inside the content address the engine checks, which is what makes this
#: module the tripwire for the recency landing as well as for the debt and
#: evidence landings.
#:
#: **Populated on purpose, and the population is load-bearing.** Plan 15.6-07
#: measured that deleting this member's read-back over a *sentinel-only*
#: fixture costs nothing, because sentinel-to-sentinel agrees; only a populated
#: fixture makes the omission detectable. The two counts recorded at the
#: read-back line below are what that measurement produced against this shape.
RECENCY = SourceRefreshWindow(
    oldest_source_refresh_at=datetime(2026, 1, 20, 4, 0, tzinfo=UTC),
    newest_source_refresh_at=datetime(2026, 2, 28, 19, 30, tzinfo=UTC),
)

#: The calibration this fixture's decision was made under (D-IMPL-112 gap 3,
#: D-IMPL-117). Test-owned: the SDK enumerates no obligation vocabulary, so
#: every reference below is a token this module invented and the fabric never
#: interprets. Both bands are bound, because the case that matters most —
#: replay substitution — needs a second obligation to substitute *with*.
PROFILE = DebtProfile(
    semver="1.0.0",
    risk_sensitivity=Decimal("1.0"),
    forced_llm_threshold=Decimal("0.50"),
    fail_closed_threshold=Decimal("0.90"),
    signal_obligations=(
        SignalObligation(signal=DebtSignal.OK, obligation_ref="test-duty-alpha"),
        SignalObligation(
            signal=DebtSignal.FORCED_LLM, obligation_ref="test-duty-beta"
        ),
    ),
)

#: The calibration as somebody later rebound it. Same bands, different duty on
#: the state ``DEBT`` lands in — which is the whole substitution threat: a replay
#: that resolved *this* profile rather than the one in force at decision time
#: would reproduce a decision nobody made (D-IMPL-26's exact-version rule).
REBOUND_PROFILE = PROFILE.model_copy(
    update={
        "signal_obligations": (
            SignalObligation(
                signal=DebtSignal.OK, obligation_ref="test-duty-rebound"
            ),
        )
    }
)

#: The obligation in force when this fixture's decision was made — resolved off
#: the pinned profile for the signal ``DEBT`` actually carries, never chosen by
#: hand, so the fixture cannot drift from the mechanism it is testing.
OBLIGATION = PROFILE.obligation_for(DEBT.signal)

#: The intent and freshness this fixture's questions carry (D-IMPL-111 limb
#: (b)). Test-owned tokens: the SDK enumerates neither, and the whole point of
#: recording them is that they are values only the deployment knows.
REQUEST_INTENT = "test-credit-review"
REQUEST_FRESHNESS = "test-as-of-boundary"


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

    def execute(
        self,
        *,
        registry: OperatorRegistry | None = None,
        request: ProductRequest | None = None,
    ) -> ExecutionResult:
        return ProjectionEngine(
            reader=self.handle.reader, registry=registry or self.operators()
        ).execute(
            plan=_SummaryPlan(),
            perspective=self.perspective(),
            tenant_id=TENANT,
            temporal_boundary=BOUNDARY,
            # D-IMPL-111 limb (a), through the one derivation replay also uses.
            seeds=request_seeds(request),
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
            debt=DEBT,
            debt_evidence=EVIDENCE,
            source_refresh_recency=RECENCY,
            obligation_in_force=OBLIGATION,
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
        """Rebuild the product from the record and the re-executed projection.

        ``debt`` comes off the record's dimension 5, never off a fresh
        assessment: D_c is computed from observations and a ``now`` neither the
        record nor the projection re-derives, so a rehydrator that re-measured
        it would produce a *different* decision wearing this one's identifier.
        Reading it back is what makes the D-IMPL-100 address move
        reconstructible rather than merely authorized.
        """
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
                # And the store pin the decision read under (24.5-L-02,
                # D-IMPL-240): it is inside the lineage's content address, so
                # it does not ride the projection back and dimension 1 is
                # the only place a `(record, projection)` rehydrator can read
                # it from. On the memory backend both sides are the sentinel,
                # so this line costs nothing here — the populated-value proof
                # is the fluree-marked module beside this one.
                store_snapshot_pin=record.context_fabric_snapshot.store_snapshot_pin,
            ),
            payload=projection.payload,
            debt=record.content_generation_path.debt,
            # And what that debt pointed at, for a harder reason (D-IMPL-118):
            # the carrier is a top-level vessel field, sibling to `debt` rather
            # than a member of it, so it does NOT ride the assessment back.
            # `ProjectionOutput` carries exactly `(plan_id, payload)`, so
            # dimension 5 is the only place a `(record, projection)` rehydrator
            # can read it from — and omitting it diverges every replay.
            #
            # MEASURED, not inferred (plan 15.6-06 task 2): deleting this one
            # line turns 8 of this module's 30 cases red with
            # `ReplayDivergence`, including the three landings that predate it.
            debt_evidence=record.content_generation_path.debt_evidence,
            # And when its sources last published, for the same reason again
            # (D-IMPL-117 gap 2, plan 15.6-07): the second Track B member takes
            # the same top-level placement `D-IMPL-118` ruled for all three, so
            # it does not ride `debt` back either and dimension 5 is the only
            # place a `(record, projection)` rehydrator can read it from.
            #
            # MEASURED, not inferred, and the measurement has a precondition
            # worth recording (plan 15.6-07, RE-MEASURED against the reshaped
            # window by plan 15.6-13 under D-IMPL-124 — the earlier figures
            # were taken against a per-source tuple and are superseded).
            #
            # Deleted while the fixture product carried the SENTINEL, this line
            # costs NOTHING — **0 of 39 red** (39 passed, 0 failed; the 5 cases
            # that assert a populated value were deselected) — because
            # sentinel-to-sentinel agrees. It is the fixture's POPULATED
            # `RECENCY` above that makes the omission detectable: with the
            # window populated, deleting this line turns **13 of this module's
            # 44 cases red** with `ReplayDivergence`, including the `debt`,
            # `debt_evidence`, `obligation_in_force` and `request` landings
            # that predate it. A read-back seam is only ever proven by a
            # populated value, and reporting only the populated figure would
            # hide the reason the discipline exists.
            source_refresh_recency=(
                record.content_generation_path.source_refresh_recency
            ),
            # And what the signal obliged, for the same reason a third time
            # (D-IMPL-112 gap 3, D-IMPL-117, plan 15.6-08): the third Track B
            # member takes the same top-level placement `D-IMPL-118` ruled for
            # all three, so it does not ride `debt` back either.
            #
            # This one is the seam that matters most, because the alternative
            # is not "omit it" but "resolve it again". A rehydrator that read
            # today's `DebtProfile` instead of this line would reproduce the
            # obligation in force NOW against a decision made under the one in
            # force THEN — the substitution `D-IMPL-26`'s exact-version rule
            # forbids, and the reason the resolved value travels on the product
            # rather than being looked up a second time.
            #
            # MEASURED, not inferred, with the precondition plan 15.6-07
            # recorded and confirmed a second time here. Deleted while the
            # vessel carried the sentinel, this line costs NOTHING — 37 passed
            # and 0 failed (the 6 cases that assert a populated value were
            # deselected), because sentinel-to-sentinel agrees. It is the
            # populated `OBLIGATION` above that makes the omission detectable:
            # with a real binding in force, deleting this line turns 13 of this
            # module's 43 cases red with `ReplayDivergence`, including the
            # `debt`, `debt_evidence`, `source_refresh_recency` and `request`
            # landings that predate it. A read-back seam is only ever proven by
            # a populated value.
            obligation_in_force=record.content_generation_path.obligation_in_force,
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


def _request(deployment: _Deployment, **overrides: Any) -> ProductRequest:
    """A question anchored on an entity that is really in the substate.

    The anchor is derived from the fixture's own executed view rather than
    written down, because entity URIs here are content-addressed: a literal
    would be a copy of a hash, and a copy of a hash is the kind of value that
    rots into naming nothing without failing. An anchor naming nothing would
    still *pin* differently — seeds are inside the query whether or not they
    match — so a literal would make the walk-start half of limb (a) vacuous
    while looking fine.
    """
    counterparty = min(
        record.claim.entity_uri
        for record in deployment.execute().view.entities
        if record.claim.entity_class == "counterparty"
    )
    fields: dict[str, Any] = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "subject": counterparty,
        "intent": REQUEST_INTENT,
        "freshness": REQUEST_FRESHNESS,
        "asked_at": BOUNDARY,
        "parameters": {},
    }
    fields.update(overrides)
    return ProductRequest(**fields)


def _serve(
    deployment: _Deployment, *, request: ProductRequest | None = None
) -> tuple[str, DecisionReplayRecord]:
    """Run the real serve path; return the record's address and the record."""
    execution = deployment.execute(request=request)
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
        request=request,
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


# --- the debt landing, against this very tripwire (D-IMPL-100) -------------


def test_the_delivered_product_carries_the_debt_it_was_assembled_with(
    deployment: _Deployment,
) -> None:
    """Whitepaper ``:2696``: debt is a signal the agent consumes, per factor.

    Asserted on the vessel rather than on the record, because the vessel is
    what every door serializes — so this is the assertion that "a consuming
    agent receives Context Debt with every delivered product" is about.
    """
    execution = deployment.execute()
    product = deployment.candidate(execution)

    assert product.debt == DEBT
    assert product.debt is not None
    assert product.debt.factors.completeness == Decimal("0.80")
    assert product.debt.scorers[0].scorer_version == "1.0.0"


def test_the_record_carries_the_debt_the_product_carries(
    deployment: _Deployment,
) -> None:
    """Dimension 5, derived from the product the builder was handed.

    Derived rather than passed: ``build_replay_record`` already receives the
    gated product, so nothing new is threaded through its 30 call sites and
    no caller can hand the record a debt the product does not carry.
    """
    _address, record = _serve(deployment)

    assert record.content_generation_path.debt == DEBT


def test_the_debt_the_decision_was_made_with_replays_byte_exactly(
    deployment: _Deployment,
) -> None:
    """The D-IMPL-100 claim, executed: the address moves *and* reconstructs.

    The ruling authorized the content address to move on condition that a
    rehydrator reading debt back off the record reproduces the identical
    bytes. This is that condition, run against the real serve path and the
    real engine rather than against the spike's stand-in vessel — and run
    after the graph has moved on, because a reproduction from unchanged state
    proves almost nothing.
    """
    address, record = _serve(deployment)

    deployment.handle.worker.ingest(
        _envelope(
            envelope_id="env-debt-later",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Logistics PLC",
                "jurisdiction": "GB",
            },
            observed_time=T_JULY,
        )
    )

    outcome = _replay(deployment, address)

    assert outcome.product.debt == DEBT
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )


def test_a_rehydration_that_drops_the_debt_is_divergence(
    deployment: _Deployment,
) -> None:
    """The adversarial half: dropping debt is *detected*, not tolerated.

    The field is inside the content address, so a rehydrator that returned
    the vessel without its debt returns a different decision. That it fails
    here is the reason the address move is safe: a silent drop would be
    indistinguishable from a decision made with no assessment at all.
    """

    class _DebtBlind(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            return product.model_copy(update={"debt": None})

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_DebtBlind(deployment))


def test_a_record_written_before_the_debt_seam_still_replays(
    deployment: _Deployment,
) -> None:
    """The sentinel's compatibility promise (D-IMPL-89 lineage).

    A product assembled with no assessment, and a record that therefore pins
    none, still reproduce: ``None`` on both sides is the positive claim "this
    decision carried no debt assessment", and the two agree. A change that
    made debt required would break every pre-seam record instead.
    """
    execution = deployment.execute()
    product_class = deployment.product_class()
    gated = run_gates(
        deployment.candidate(execution).model_copy(update={"debt": None}),
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

    assert record.content_generation_path.debt is None

    outcome = _replay(deployment, served.replay_ref.content_address)

    assert outcome.product.debt is None
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )


# --- what the debt points at, against this same tripwire (D-IMPL-118) ------


def test_the_delivered_product_carries_what_its_debt_points_at(
    deployment: _Deployment,
) -> None:
    """D-IMPL-118 `qa-toplevel`: on the vessel, and beside `debt` not inside it.

    Asserted on the vessel because the vessel is what every door serializes.
    The second assertion is the one that rules out the placement the ruling
    forwent: under `qa-nested` the pointers would be reachable at
    ``product.debt.<member>`` and would have ridden the assessment into the
    record for free. They are not, and that is why the reconstruction seam
    below has to exist at all.
    """
    execution = deployment.execute()
    product = deployment.candidate(execution)

    assert product.debt_evidence == EVIDENCE
    assert "debt_evidence" in type(product).model_fields
    assert product.debt is not None
    assert "debt_evidence" not in type(product.debt).model_fields


def test_the_evidence_lands_on_dimension_five_and_mints_no_sixth(
    deployment: _Deployment,
) -> None:
    """INV-CH7-80: the five dimensions are inviolate.

    The extension lands *inside* dimension 5, beside the ``debt`` it explains,
    and neither the record nor dimension 4 gains a member. What this case and
    only this case rules out: a reconstruction seam bolted on as a sixth
    dimension, which would have satisfied replay and broken the invariant.
    """
    _address, record = _serve(deployment)

    assert record.content_generation_path.debt_evidence == EVIDENCE
    assert "debt_evidence" in type(record.content_generation_path).model_fields
    assert "debt_evidence" not in type(record).model_fields
    assert "debt_evidence" not in type(record.perspective_conditioning).model_fields


def test_what_the_debt_pointed_at_replays_byte_exactly(
    deployment: _Deployment,
) -> None:
    """The D-IMPL-118 obligation, executed: the address moves *and* rebuilds.

    The ruling authorized a third content-address move on the express
    condition that the vessel field be carried on dimension 5 and read back by
    every rehydrator — without which *"every replay of every product raises
    `ReplayDivergence`"*. This is that condition, run against the real serve
    path and the real engine, and run after the graph has moved on, because a
    reproduction from unchanged state proves almost nothing.

    Both recomputations are asserted rather than trusted: the product against
    the address the record names, and the record against the address the store
    resolved it from. The second is where the move is *shown* reconstructible
    instead of asserted.
    """
    address, record = _serve(deployment)

    deployment.handle.worker.ingest(
        _envelope(
            envelope_id="env-evidence-later",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Holdings SA",
                "jurisdiction": "CH",
            },
            observed_time=T_JULY,
        )
    )

    outcome = _replay(deployment, address)

    assert outcome.product.debt_evidence == EVIDENCE
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )
    assert content_hash(record) == address


def test_a_rehydration_that_drops_the_evidence_is_divergence(
    deployment: _Deployment,
) -> None:
    """The adversarial half: dropping the pointers is *detected*, not tolerated.

    The field is inside the content address, so a rehydrator that returned the
    vessel without it returns a different decision. A silent drop would be
    indistinguishable from a decision made with no evidence at all — which is
    exactly the artifact the ``NO_DEBT_EVIDENCE`` sentinel exists to keep
    distinct.
    """

    class _EvidenceBlind(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            return product.model_copy(update={"debt_evidence": NO_DEBT_EVIDENCE})

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_EvidenceBlind(deployment))


def test_a_rehydration_that_swaps_one_pointer_is_divergence(
    deployment: _Deployment,
) -> None:
    """One handle changed is a different decision, and is caught as one.

    Stronger than the drop case and not implied by it: a rehydrator that
    returned the right *number* of pointers would satisfy any cardinality
    check. What this rules out is an implementation that treats the carrier as
    a count or a presence flag rather than as bytes inside the address.
    """
    swapped = (EVIDENCE[0], DebtEvidencePointer(handle="h-not-the-one"))

    class _EvidenceSwapped(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            return product.model_copy(update={"debt_evidence": swapped})

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_EvidenceSwapped(deployment))


def test_a_record_written_before_the_evidence_seam_still_replays(
    deployment: _Deployment,
) -> None:
    """The sentinel's compatibility promise (the ``debt`` case's lineage).

    A product assembled with no pointers, and a record that therefore pins
    none, still reproduce: ``NO_DEBT_EVIDENCE`` on both sides is the same
    positive claim and the two agree. A change that made the carrier required
    would break every pre-seam record instead — which is the cost this case
    prices and the reason the field defaults rather than demands.
    """
    execution = deployment.execute()
    product_class = deployment.product_class()
    gated = run_gates(
        deployment.candidate(execution).model_copy(
            update={"debt_evidence": NO_DEBT_EVIDENCE}
        ),
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

    assert record.content_generation_path.debt_evidence == NO_DEBT_EVIDENCE

    outcome = _replay(deployment, served.replay_ref.content_address)

    assert outcome.product.debt_evidence == NO_DEBT_EVIDENCE
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )


# --- when the sources last published, same tripwire (D-IMPL-117 gap 2) -----


def test_the_delivered_product_carries_when_its_sources_last_published(
    deployment: _Deployment,
) -> None:
    """D-IMPL-118 again: on the vessel, and beside `debt` rather than inside it.

    The ruling is explicit that its four measured placements *"price all three
    Track B vessel-carried members identically"*, so this member takes the same
    branch the evidence carrier took one plan earlier. The second and third
    assertions rule out the two placements that would have been cheaper: nested
    inside `DebtAssessment`, where it would have ridden the assessment into the
    record for free, and folded into `DebtFactors`, where it would have become
    an input to a number the SDK computes rather than a fact it merely carries.
    """
    execution = deployment.execute()
    product = deployment.candidate(execution)

    assert product.source_refresh_recency == RECENCY
    assert "source_refresh_recency" in type(product).model_fields
    assert product.debt is not None
    assert "source_refresh_recency" not in type(product.debt).model_fields
    assert "source_refresh_recency" not in type(product.debt.factors).model_fields


def test_the_recency_lands_on_dimension_five_and_mints_no_sixth(
    deployment: _Deployment,
) -> None:
    """INV-CH7-80: the five dimensions are inviolate.

    The extension lands *inside* dimension 5, beside the ``debt`` whose
    freshness factor it is deliberately not, and neither the record nor
    dimension 4 gains a member. What this case and only this case rules out: a
    second reconstruction seam bolted on as a sixth dimension, which would have
    satisfied replay and broken the invariant.
    """
    _address, record = _serve(deployment)

    assert record.content_generation_path.source_refresh_recency == RECENCY
    assert (
        "source_refresh_recency"
        in type(record.content_generation_path).model_fields
    )
    assert "source_refresh_recency" not in type(record).model_fields
    assert (
        "source_refresh_recency"
        not in type(record.perspective_conditioning).model_fields
    )


def test_when_the_sources_last_published_replays_byte_exactly(
    deployment: _Deployment,
) -> None:
    """The D-IMPL-118 obligation, executed a second time.

    The ruling authorized the address move on the express condition that the
    vessel field be carried on dimension 5 and read back by every rehydrator —
    without which *"every replay of every product raises `ReplayDivergence`"*.
    This is that condition for the recency slot, run against the real serve
    path and the real engine, and run **after the graph has moved on four
    months**, because a reproduction from unchanged state proves almost
    nothing.

    The staleness of the *graph* moving is what makes this case pointed for
    this field in particular: the fabric's own decay has advanced, and the
    recorded refresh instants have not — which is exactly the independence
    between the two facts that the slot exists to express.

    Both recomputations are asserted rather than trusted: the product against
    the address the record names, and the record against the address the store
    resolved it from.
    """
    address, record = _serve(deployment)

    deployment.handle.worker.ingest(
        _envelope(
            envelope_id="env-recency-later",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Holdings SA",
                "jurisdiction": "CH",
            },
            observed_time=T_JULY,
        )
    )

    outcome = _replay(deployment, address)

    assert outcome.product.source_refresh_recency == RECENCY
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )
    assert content_hash(record) == address


def test_a_rehydration_that_drops_the_recency_is_divergence(
    deployment: _Deployment,
) -> None:
    """The adversarial half: dropping the instants is *detected*, not tolerated.

    The field is inside the content address, so a rehydrator that returned the
    vessel without it returns a different decision. A silent drop would be
    indistinguishable from a decision made by a deployment that knew nothing
    about its sources' publication schedule — which is exactly the artifact the
    ``NO_SOURCE_REFRESH_RECENCY`` sentinel exists to keep distinct.
    """

    class _RecencyBlind(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            return product.model_copy(
                update={"source_refresh_recency": NO_SOURCE_REFRESH_RECENCY}
            )

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_RecencyBlind(deployment))


def test_a_rehydration_that_moves_one_refresh_instant_is_divergence(
    deployment: _Deployment,
) -> None:
    """A decision made against a January filing is not one made against February.

    Stronger than the drop case and not implied by it: a rehydrator that
    returned a window of the right *shape* — two tz-aware instants, oldest not
    after newest — would satisfy any structural check. What this rules out is
    an implementation that treats the slot as a shape to be reproduced rather
    than a value to be carried, and it is the case that makes each instant
    load-bearing rather than decorative. Only the oldest end moves, so a
    rehydrator that carried the newest instant and re-derived the other is
    caught too.
    """
    moved = SourceRefreshWindow(
        oldest_source_refresh_at=(
            RECENCY.oldest_source_refresh_at + timedelta(days=30)
        ),
        newest_source_refresh_at=RECENCY.newest_source_refresh_at,
    )

    class _RecencyMoved(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            return product.model_copy(update={"source_refresh_recency": moved})

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_RecencyMoved(deployment))


#: The s1-01 governance artifact, read rather than transcribed. The three
#: human-interpretable references it declares are the exact strings D-IMPL-124
#: rules must not leave the vessel, and reading them from the artifact is what
#: keeps the case below honest: transcribing them here would make it assert
#: that this module agrees with itself, and would leave a renamed source
#: silently unchecked (CLAUDE.md §6.4).
_S1_01_GOVERNANCE = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "s1-01-hello-context-product"
    / "artifacts"
    / "product-governance.yaml"
)


def _declared_source_references_and_window() -> tuple[
    tuple[str, ...], SourceRefreshWindow
]:
    """Read s1-01's declared per-source entries; return its names and its window."""
    import yaml  # noqa: PLC0415

    declaration = yaml.safe_load(_S1_01_GOVERNANCE.read_text(encoding="utf-8"))
    entries = declaration["declaration"]["source_refresh_recency"]
    instants = [datetime.fromisoformat(entry["refreshed_at"]) for entry in entries]
    return (
        tuple(entry["source_ref"] for entry in entries),
        SourceRefreshWindow(
            oldest_source_refresh_at=min(instants),
            newest_source_refresh_at=max(instants),
        ),
    )


def test_no_source_identity_reaches_the_delivered_product(
    deployment: _Deployment,
) -> None:
    """D-IMPL-124's operative sentence, as a property rather than a promise.

    Dave's ruling: *"no `source_ref` strings leave the vessel."* Asserted
    mechanically, in both the directions that can fail.

    The **value** direction: this case populates the vessel with the window
    reduced from s1-01's own three declared entries — `corporate-registry`,
    `kyc-registry`, `name-screening` — serves it through the real gate-and-
    serve path, and asserts that none of those three references appears
    anywhere in the delivered `canonical_bytes`. Both shipped delivery surfaces
    return exactly these bytes, so what this checks is what every principal who
    can reach the product actually receives. The references are read out of the
    artifact rather than transcribed, so renaming a source in the deployment
    cannot quietly retire the assertion.

    The **type** direction: no field reachable from the vessel or from replay
    dimension 5 is *typed* to carry a source reference at all. This is the half
    a value check cannot give, because a product that merely happened not to
    populate an identity-bearing member would pass the first assertion while
    leaving the channel open. Walking the reachable contract types is what
    makes the closure structural — the shape is unavailable, not merely
    unused, which is why D-IMPL-124 deleted `SourceRefresh` rather than
    deprecating it.

    **What this does not claim.** Two instants are still information: a reader
    still learns that *some* source published at each end of the window. What
    is closed is the identity channel — after this, no reader can learn that a
    system called `name-screening` exists, nor when that system in particular
    last published.
    """
    references, window = _declared_source_references_and_window()
    assert len(references) == 3

    execution = deployment.execute()
    gated = run_gates(
        deployment.candidate(execution).model_copy(
            update={"source_refresh_recency": window}
        ),
        engine_resolved=execution.operators_invoked,
        now=NOW,
        registry=deployment.registry,
        product_class=deployment.product_class(),
    )
    assert isinstance(gated, ServableProduct)

    delivered = canonical_bytes(gated.product)
    assert gated.product.source_refresh_recency == window
    for reference in references:
        assert reference.encode() not in delivered

    identity_bearing = {
        f"{model.__name__}.{name}"
        for model in _reachable_contract_types(
            ContextProductContract, ContentGenerationPath
        )
        for name in model.model_fields
        if "source_ref" == name or name.endswith("_source_ref")
    }
    assert identity_bearing == set()

    assert set(SourceRefreshWindow.model_fields) == {
        "oldest_source_refresh_at",
        "newest_source_refresh_at",
    }


def _reachable_contract_types(*roots: type[CCFContract]) -> set[type[CCFContract]]:
    """Every contract type reachable from these roots through their annotations.

    A shallow field scan would miss an identity nested one structure down,
    which is precisely where the deleted per-source entry used to live — so the
    walk is transitive, and it reads annotations rather than values because a
    slot nobody populated is still a slot.
    """
    seen: set[type[CCFContract]] = set()
    pending = list(roots)
    while pending:
        model = pending.pop()
        if model in seen:
            continue
        seen.add(model)
        for field in model.model_fields.values():
            for candidate in _annotation_types(field.annotation):
                if (
                    isinstance(candidate, type)
                    and issubclass(candidate, CCFContract)
                    and candidate not in seen
                ):
                    pending.append(candidate)
    return seen


def _annotation_types(annotation: Any) -> Iterator[Any]:
    """Flatten an annotation into the concrete types it can resolve to."""
    yield annotation
    for argument in get_args(annotation):
        yield from _annotation_types(argument)


def test_a_record_written_before_the_recency_seam_still_replays(
    deployment: _Deployment,
) -> None:
    """The sentinel's compatibility promise (the ``debt_evidence`` lineage).

    A product assembled with no refresh instants, and a record that therefore
    pins none, still reproduce: ``NO_SOURCE_REFRESH_RECENCY`` on both sides is
    the same positive claim and the two agree. A change that made the slot
    required would break every pre-seam record instead — which is the cost this
    case prices and the reason the field defaults rather than demands.
    """
    execution = deployment.execute()
    product_class = deployment.product_class()
    gated = run_gates(
        deployment.candidate(execution).model_copy(
            update={"source_refresh_recency": NO_SOURCE_REFRESH_RECENCY}
        ),
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

    assert (
        record.content_generation_path.source_refresh_recency
        == NO_SOURCE_REFRESH_RECENCY
    )

    outcome = _replay(deployment, served.replay_ref.content_address)

    assert outcome.product.source_refresh_recency == NO_SOURCE_REFRESH_RECENCY
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )


# --- what the signal obliged, same tripwire (D-IMPL-112 gap 3) -------------


def test_the_delivered_product_carries_what_its_signal_obliged(
    deployment: _Deployment,
) -> None:
    """D-IMPL-118 a third time: on the vessel, and beside `debt` not inside it.

    The ruling's four measured placements *"price all three Track B
    vessel-carried members identically"*, so this member takes the branch its
    two siblings took. The later assertions rule out the placements that would
    have been cheaper or more obvious: nested inside `DebtAssessment`, where it
    would have ridden the assessment into the record for free, and on
    `DebtProfile` alone, where the *calibration* legitimately lives but the
    resolved value would then have to be looked up again at replay.

    The last assertion is this field's own: the vessel carries the obligation
    for the signal the decision actually landed in, and **not** the mapping. A
    consumer holding the whole mapping would be holding the calibration rather
    than the decision.
    """
    execution = deployment.execute()
    product = deployment.candidate(execution)

    assert product.obligation_in_force == OBLIGATION
    assert "obligation_in_force" in type(product).model_fields
    assert product.debt is not None
    assert "obligation_in_force" not in type(product.debt).model_fields
    assert "signal_obligations" not in type(product).model_fields
    assert product.obligation_in_force == PROFILE.obligation_for(DebtSignal.OK)
    assert product.obligation_in_force != PROFILE.obligation_for(
        DebtSignal.FORCED_LLM
    )


def test_the_obligation_lands_on_dimension_five_and_mints_no_sixth(
    deployment: _Deployment,
) -> None:
    """INV-CH7-80: the five dimensions are inviolate.

    The extension lands *inside* dimension 5, beside the ``debt`` whose routing
    state it answers to, and neither the record nor dimension 4 gains a member.
    What this case and only this case rules out: a second reconstruction seam
    bolted on as a sixth dimension, which would have satisfied replay and
    broken the invariant.
    """
    _address, record = _serve(deployment)

    assert record.content_generation_path.obligation_in_force == OBLIGATION
    assert (
        "obligation_in_force" in type(record.content_generation_path).model_fields
    )
    assert "obligation_in_force" not in type(record).model_fields
    assert (
        "obligation_in_force"
        not in type(record.perspective_conditioning).model_fields
    )


@pytest.mark.parametrize(
    "blank", ["", "   ", "\t"], ids=["empty", "spaces", "tab"]
)
def test_a_blank_obligation_is_refused_on_dimension_five(
    deployment: _Deployment, blank: str
) -> None:
    """The record is the other door into the vessel's third state.

    The close-time cross-AI panel found ``ContextProductContract`` admitting a
    blank obligation; dimension 5 carries the same field, and
    ``replay_product`` reads it back off *this* structure. A gate on the vessel
    alone would leave a stored record admissible and hand the blank to the
    rehydrated product from the one side that was never checked — which is the
    deferral CLAUDE.md §11 refuses. Asserted through ``model_validate``, the
    door a record on disk actually comes through.
    """
    _address, record = _serve(deployment)
    payload = record.content_generation_path.model_dump()
    payload["obligation_in_force"] = blank

    with pytest.raises(ValueError, match="obligation in force must be"):
        ContentGenerationPath.model_validate(payload)


def test_what_the_signal_obliged_replays_byte_exactly(
    deployment: _Deployment,
) -> None:
    """The D-IMPL-118 obligation, executed a third time.

    The ruling authorized the address move on the express condition that the
    vessel field be carried on dimension 5 and read back by every rehydrator —
    without which *"every replay of every product raises `ReplayDivergence`"*.
    This is that condition for the obligation, run against the real serve path
    and the real engine, and run **after the graph has moved on four months**,
    because a reproduction from unchanged state proves almost nothing.

    Both recomputations are asserted rather than trusted: the product against
    the address the record names, and the record against the address the store
    resolved it from.
    """
    address, record = _serve(deployment)

    deployment.handle.worker.ingest(
        _envelope(
            envelope_id="env-obligation-later",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Holdings SA",
                "jurisdiction": "CH",
            },
            observed_time=T_JULY,
        )
    )

    outcome = _replay(deployment, address)

    assert outcome.product.obligation_in_force == OBLIGATION
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )
    assert content_hash(record) == address


def test_a_replay_reproduces_the_obligation_in_force_at_decision_time(
    deployment: _Deployment,
) -> None:
    """**The case this whole task exists for.** Rebinding does not rewrite history.

    A decision is served under one calibration; somebody then rebinds the
    profile so the same signal obliges something else. The replay must
    reproduce what the decision was actually under — `D-IMPL-26`: replay
    resolves *exact* artifact versions, never "latest". Anything else is a
    tampering-and-repudiation failure: the record would answer *"this decision
    was obliged to do X"* with today's X.

    The rebound profile is registered into the deployment's Control Plane, so
    the substitution is available to be made and is measurably not made. Both
    obligations are asserted — the recorded one reproduces AND the current one
    does not — because asserting only the first would pass against a rebinding
    that never took effect.
    """
    address, record = _serve(deployment)
    rebound_version = deployment.registry.register(
        "test/debt-profile", REBOUND_PROFILE.model_dump()
    )

    outcome = _replay(deployment, address)

    assert rebound_version
    assert REBOUND_PROFILE.obligation_for(DEBT.signal) != OBLIGATION
    assert outcome.product.obligation_in_force == OBLIGATION
    assert outcome.product.obligation_in_force != REBOUND_PROFILE.obligation_for(
        DEBT.signal
    )
    assert record.content_generation_path.obligation_in_force == OBLIGATION
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )


def test_a_rehydration_that_resolves_todays_binding_is_divergence(
    deployment: _Deployment,
) -> None:
    """The substitution attempted, and refused by the address check.

    Stronger than the drop case below and not implied by it: this rehydrator
    returns a *plausible* obligation — the one the current calibration binds to
    the very same signal — rather than an empty one. Nothing about the returned
    product looks wrong on its face; only the content address does. That is the
    property `D-IMPL-100` bought by putting the value inside the address, and
    this is the case that shows it catching a substitution rather than a typo.
    """

    class _ResolvesToday(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            assert product.debt is not None
            return product.model_copy(
                update={
                    "obligation_in_force": REBOUND_PROFILE.obligation_for(
                        product.debt.signal
                    )
                }
            )

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_ResolvesToday(deployment))


def test_a_rehydration_that_drops_the_obligation_is_divergence(
    deployment: _Deployment,
) -> None:
    """The adversarial half: dropping it is *detected*, not tolerated.

    The field is inside the content address, so a rehydrator that returned the
    vessel without it returns a different decision. A silent drop would be
    indistinguishable from a decision made under a calibration that bound
    nothing — which is exactly the artifact the ``NO_OBLIGATION_IN_FORCE``
    sentinel exists to keep distinct.
    """

    class _ObligationBlind(_Environment):
        def rehydrate_product(
            self, *, record: DecisionReplayRecord, projection: ProjectionOutput
        ) -> ContextProductContract:
            product = super().rehydrate_product(record=record, projection=projection)
            return product.model_copy(
                update={"obligation_in_force": NO_OBLIGATION_IN_FORCE}
            )

    address, _record = _serve(deployment)
    with pytest.raises(ReplayDivergence, match="product"):
        _replay(deployment, address, environment=_ObligationBlind(deployment))


def test_a_record_written_before_the_obligation_seam_still_replays(
    deployment: _Deployment,
) -> None:
    """The sentinel's compatibility promise (the ``debt_evidence`` lineage).

    A product assembled under a calibration that bound nothing, and a record
    that therefore pins nothing, still reproduce: ``NO_OBLIGATION_IN_FORCE`` on
    both sides is the same positive claim and the two agree. A change that made
    the field required would break every pre-seam record instead — which is the
    cost this case prices and the reason the field defaults rather than demands.
    """
    execution = deployment.execute()
    product_class = deployment.product_class()
    gated = run_gates(
        deployment.candidate(execution).model_copy(
            update={"obligation_in_force": NO_OBLIGATION_IN_FORCE}
        ),
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

    assert (
        record.content_generation_path.obligation_in_force
        == NO_OBLIGATION_IN_FORCE
    )

    outcome = _replay(deployment, served.replay_ref.content_address)

    assert outcome.product.obligation_in_force == NO_OBLIGATION_IN_FORCE
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )


# --- the question answered, against this same tripwire (D-IMPL-111) --------


def test_the_record_carries_the_question_the_decision_answered(
    deployment: _Deployment,
) -> None:
    """The gap ``DI-15.5-07`` recorded, closed.

    ``intent`` and ``freshness`` were in **no** dimension before this ruling.
    They are not recoverable by inference from anything else the record holds:
    the payload names a subject and dimension 1 names a boundary, but nothing
    anywhere said *for what decision* or *under what temporal requirement* the
    question was asked.
    """
    asked = _request(deployment)
    _address, record = _serve(deployment, request=asked)

    recorded = record.content_generation_path.request
    assert recorded == asked
    assert recorded is not None
    assert recorded.intent == REQUEST_INTENT
    assert recorded.freshness == REQUEST_FRESHNESS


def test_the_question_lands_on_dimension_five_and_mints_no_sixth(
    deployment: _Deployment,
) -> None:
    """INV-CH7-80: the five dimensions are inviolate.

    The extension lands *inside* dimension 5, beside the ``graph_query_sequence``
    it explains, and dimension 4 — *"for whom, with what authority?"* — is
    untouched: a request asserts no role, no principal and no tenant, by
    construction of :class:`~ccf.products.request.ProductRequest` itself.
    """
    _address, record = _serve(deployment, request=_request(deployment))

    assert "request" in type(record.content_generation_path).model_fields
    assert "request" not in type(record).model_fields
    assert "request" not in type(record.perspective_conditioning).model_fields


def test_the_question_the_decision_answered_replays_byte_exactly(
    deployment: _Deployment,
) -> None:
    """The D-IMPL-111 condition, executed: the address moves *and* reconstructs.

    Both limbs are under test at once, and they have to be. Limb (a) put the
    request's subject inside the compiled query, so the pins in dimension 5
    now depend on the question; limb (b) put the question in the record, which
    is the only reason replay can re-derive those seeds. A record that carried
    the pins without the question would be unreplayable *by construction* —
    ``replay`` would re-execute with no seeds and diverge on the very pins it
    recorded.

    Run after the graph has moved on, on the module's standing rule: a
    reproduction from unchanged state proves almost nothing.
    """
    asked = _request(deployment)
    address, record = _serve(deployment, request=asked)

    deployment.handle.worker.ingest(
        _envelope(
            envelope_id="env-request-later",
            payload={
                "counterparty_lei": "LEI-AAA",
                "counterparty_name": "Northwind Logistics PLC",
                "jurisdiction": "GB",
            },
            observed_time=T_JULY,
        )
    )

    outcome = _replay(deployment, address)

    assert outcome.record.content_generation_path.request == asked
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )
    # The record's own address is the bytes the store holds, recomputed rather
    # than trusted: this is where the D-IMPL-111 address move is *shown*
    # reconstructible instead of asserted.
    assert content_hash(record) == address


def test_a_replay_that_re_seeds_from_another_question_diverges(
    deployment: _Deployment,
) -> None:
    """The adversarial twin: the same decision asked about a different anchor.

    Two records identical in every other field, differing only in the recorded
    request's ``subject``. Replaying the second re-executes under the *other*
    anchor's seeds, so the re-executed query sequence no longer matches the
    pins the record carries and the divergence is caught — which is what makes
    the pins meaningful rather than decorative. Before limb (a) both would have
    replayed green, because both compiled the same question.
    """
    asked = _request(deployment)
    address, record = _serve(deployment, request=asked)

    twin = record.model_copy(
        update={
            "content_generation_path": record.content_generation_path.model_copy(
                update={
                    "request": asked.model_copy(
                        update={"subject": f"{asked.subject}-not-this-one"}
                    )
                }
            )
        }
    )
    assert content_hash(twin) != address
    ReplayWriter(
        store=deployment.store, artifact_class=ARTIFACT_CLASS
    ).write_replay_record(record=twin)

    with pytest.raises(ReplayDivergence, match="questions asked of the substrate"):
        _replay(deployment, content_hash(twin))


def test_a_record_written_before_the_request_seam_still_replays(
    deployment: _Deployment,
) -> None:
    """The sentinel's compatibility promise (D-IMPL-89 lineage).

    A decision served with no request — every pre-D-IMPL-111 record, and every
    fabric-direct decision that was never addressed — pins ``None``, replays
    with no seeds, and reproduces. That is the whole cost argument for the
    positive-sentinel default: 32 ``build_replay_record`` call sites across 28
    files, and none of them had to move.
    """
    address, record = _serve(deployment)

    assert record.content_generation_path.request is None

    outcome = _replay(deployment, address)

    assert outcome.record.content_generation_path.request is None
    assert content_hash(outcome.product) == (
        record.content_generation_path.product_content_address
    )


def test_omitting_the_question_is_indistinguishable_from_passing_none(
    deployment: _Deployment,
) -> None:
    """The extension changes no existing behavior — the ``harness_trace`` claim."""
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
    common: dict[str, Any] = {
        "execution": execution,
        "product": gated.product,
        "perspective": deployment.perspective(),
        "policy_bindings": (
            PolicyBinding(key=POLICY_BUNDLE_KEY, version=deployment.policy_version),
        ),
        "assembly_mode": "algorithmic",
        "recorded_at": NOW,
    }
    assert content_hash(build_replay_record(**common)) == content_hash(
        build_replay_record(**common, request=None)
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


def test_the_snapshot_reader_scope_checks_query_before_delegating(
    deployment: _Deployment,
) -> None:
    """``query()`` enforces the pin over the query's own fields.

    The scope check runs on ``q.tenant_id`` / ``q.as_of`` before any
    delegation, so a replayed execution cannot read outside the snapshot
    however its questions are phrased. Raising here — versus the empty view
    a *source* answers on a tenant mismatch — is the deliberate contrast of
    the tenant-mismatch clause (`GQ-27` at
    docs/GRAPH_QUERY_SEMANTICS.md:529): a source answers questions; a pin
    enforces one.
    """
    _address, record = _serve(deployment)
    reader = SnapshotReader(
        reader=deployment.handle.reader, snapshot=record.context_fabric_snapshot
    )
    view = reader.query(GraphQuery(tenant_id=TENANT, as_of=BOUNDARY))
    assert view.as_of == BOUNDARY
    assert view.tenant_id == TENANT

    with pytest.raises(SnapshotScopeViolation):
        reader.query(GraphQuery(tenant_id=TENANT, as_of=T_JULY))
    with pytest.raises(SnapshotScopeViolation):
        reader.query(GraphQuery(tenant_id="tenant-other", as_of=BOUNDARY))


def test_the_snapshot_holds_no_physical_copy_of_the_graph(
    deployment: _Deployment,
) -> None:
    """D-IMPL-06: boundary + tenant + watermark + manifest, and nothing else
    graph-shaped.

    ``source_attestation`` (15.2-11, D-09) is the first non-D-IMPL-06 field:
    the per-dimension provenance modes the reading source reported — a pin,
    not a copy of any graph state, and deliberately outside the
    ``graph_snapshot_id`` derivation, which stays the four D-IMPL-06
    constituents exactly. ``store_snapshot_pin`` (24.5-L-02, D-IMPL-240) is a
    pin, not a copy of graph state, and sits outside the ``graph_snapshot_id``
    derivation (D-IMPL-06).
    """
    _address, record = _serve(deployment)
    snapshot = record.context_fabric_snapshot
    assert set(type(snapshot).model_fields) == {
        "graph_snapshot_id",
        "tenant_id",
        "temporal_boundary",
        "store_watermark",
        "touched_entities",
        "touched_relationships",
        "source_attestation",
        "store_snapshot_pin",
    }


# --- structural: no moving targets on the replay path ----------------------


def test_the_replay_path_never_resolves_latest() -> None:
    """CLAUDE.md §7.4, asserted against the source rather than against habit."""
    for module in (engine_module, snapshots_module):
        source = inspect.getsource(module)
        assert "resolve_latest" not in source, module.__name__
