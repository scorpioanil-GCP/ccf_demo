"""examples/06-decision-replay — record, then reproduce exactly (EXAM-07).

The audit-by-construction proof, in an energy/grid-operations domain: a
load-shed authorization is decided against a real fabric — an
``AnalyticsInsightsAgent`` with a skill grant in force, a minimal grid-ops
workflow suspending at an ApprovalGate, and an AUTH-BOUND human approval
through ``create_app(auth=BearerTokenAuth(...))`` with a D-16-required
``SignedPrincipalBinding`` (the replay leg of the D-14 absorption). Then,
**from the replay record alone**, the decision is reproduced: graph
snapshot, policy bundle version, agent version, skill-set in force, and
prompt-artifact version all resolve from the ArtifactStore at their EXACT
recorded versions, and the reproduced Context Product is **byte-equal**
(canonical serializer) to the original.

Structure (review consensus concern 4 mitigation): ``record()`` and
``replay_decision()`` are explicit helper functions inside this example
directory, each with its own artifact-resolution checks, called in
sequence by ``main()``.

What this demonstrates, as assertions:

* **Exact reproduction (whitepaper §7.10; D-IMPL-06/26/44).** The replay
  engine re-executes against the logical snapshot and the reproduced
  product's canonical bytes equal the original's.
* **Exact-version resolution, never a moving target.** The agent
  definition resolves at its recorded content hash; the prompt artifact
  and skill grant resolve content-addressed and are checked against the
  versions the record (and the definition it pins) declares. A ref asking
  for the moving-target token is refused (``MovingTargetRefused``).
* **The hardened HITL surface, in replay (D-14/D-16).** The record's
  dimension 2 carries the grant-derived approver principal AND the signed
  binding; the signature verifies from the record alone and reproduces the
  approver principal exactly as recorded.
* **Version sensitivity.** Bumping the recorded policy-bundle version in a
  COPY of the record (never the canonical one) makes reproduction refuse
  (``ReplayUnresolvable``) — the audit record is version-sensitive.
* **The OverrideBoundary, in replay (§8.2; D-07).** The shift supervisor
  substitutes the agent's shed determination at a typed boundary; the
  override decision's own record resolves from the store and dimension 2
  carries BOTH the original output and the override, byte-assertably,
  with the overrider's signed binding verifying from the record alone.

Every domain value is loaded from ``artifacts/*.yaml`` (CLAUDE.md §6.4).
Run it: ``make example-06``. Exit 0 means every assertion held.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import yaml
from joserfc.jwk import ECKey

from ccf.agents.agent import Agent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    PromptArtifact,
    TaskDefinition,
)
from ccf.agents.factory import AgentFactory
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import (
    LATEST_VERSION_TOKEN,
    MovingTargetRefused,
    artifact_uri,
    parse_artifact_uri,
)
from ccf.assembly.worker import (
    EntityResolutionRule,
    EntityResolutionSpec,
    RelationshipResolutionRule,
)
from ccf.boot import boot
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphReader, GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.hitl.approval_gate import HitlActionRecord
from ccf.hitl.identity_binding import (
    sign_principal_binding,
    verify_principal_binding,
)
from ccf.hitl.override import (
    OverrideActionRecord,
    OverrideBoundary,
    OverrideResolution,
)
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (
    HITL_POLICY,
    HitlPolicy,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from ccf.operators.base import OperatorOutput
from ccf.operators.categories import (
    PolicyFilter,
    PolicyFilterParameters,
    SimilaritySelect,
    SimilaritySelectParameters,
    TemporalAsOf,
    TemporalAsOfParameters,
    TraversalNeighborhood,
    TraversalNeighborhoodParameters,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
)
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import ServableProduct, run_gates
from ccf.projection.engine import OperatorRegistry, ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.engine import (
    ReplayUnresolvable,
    replay,
    resolve_artifact,
    resolve_artifact_at_uri,
)
from ccf.replay.record import DecisionReplayRecord, PolicyBinding, build_replay_record
from ccf.replay.serve import ReplayWriter, serve
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.similarity.protocol import TokenOverlapIndex
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.dispatch import SkillInvocation
from ccf.skills.grants import (
    ApprovalOutcome,
    GrantLedger,
    SkillGrant,
    grant_set_hash,
)
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.authz.artifact import SCOPE_MAPPING, ScopeMappingArtifact
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import ERROR_TENANT_UNAUTHORIZED
from ccf_runtime.mcp.auth import TokenGrant
from ccf_runtime.mcp.egress import ProductNotServable
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38).
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _ticking_clock(base: datetime) -> Any:
    state = {"now": base}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    return EntityResolutionSpec(
        entity_rules=tuple(
            EntityResolutionRule(
                match_key=rule["match_key"],
                entity_class=rule["entity_class"],
                identity_keys=tuple(rule["identity_keys"]),
                attribute_keys=tuple(rule.get("attribute_keys", ())),
            )
            for rule in ontology["entity_rules"]
        ),
        relationship_rules=tuple(
            RelationshipResolutionRule(
                relationship_type=rule["relationship_type"],
                subject_entity_class=rule["subject_entity_class"],
                object_entity_class=rule["object_entity_class"],
            )
            for rule in ontology["relationship_rules"]
        ),
    )


def _envelopes(ontology: Any, events: Any) -> tuple[SignalEnvelope, ...]:
    return tuple(
        SignalEnvelope(
            tenant_id=ontology["tenant_id"],
            envelope_id=item["envelope_id"],
            source=SourceIdentity(system_id=item["source_system_id"]),
            ingestion_timestamp=_instant(item["ingestion_timestamp"]),
            observed_time=_instant(item["observed_time"]),
            raw_payload=dict(item["payload"]),
        )
        for item in events["envelopes"]
    )


class ShedDetermination(CCFContract):
    # The deployment's typed agent-output shape at the OverrideBoundary —
    # deployment code, like the projection: the SDK ships the boundary
    # mechanism only, and every VALUE this shape carries lives in
    # artifacts/hitl.yaml, never here (§6.4; CINV-01). Decimals travel as
    # quoted strings per the artifact convention.

    feeder_ref: str
    shed_megawatts: str
    duration_minutes: str


class GridLoadPlan:
    # The deployment's Π — deployment code, like every projection. Both the
    # record phase and the replay environment construct it identically, so
    # the interpretation the record names is the one the replay resolves.

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "entity_count": len(view.entities),
                "entities": [
                    {
                        "entity_uri": record.claim.entity_uri,
                        "entity_class": record.claim.entity_class,
                    }
                    for record in view.entities
                ],
                "relationship_types": sorted(
                    {edge.claim.relationship_type for edge in view.relationships}
                ),
            },
        )


def _operators(
    *,
    control: Any,
    ontology: Any,
    reader: GraphReader,
    tenant_id: str,
    boundary: datetime,
    policy_version: str,
) -> OperatorRegistry:
    """The four-category operator chain, from artifacts — used identically
    by the record phase and by the replay environment (D-IMPL-38: same
    declared parameters -> same parameter hashes -> the recorded step
    sequence reproduces)."""
    params = control["operator_parameters"]
    operators = OperatorRegistry()
    operators.register(
        PolicyFilter(
            parameters=PolicyFilterParameters(
                permitted_policy_bundle_versions=frozenset({policy_version}),
                classification_attribute_by_class=dict(
                    ontology["classification_attribute_by_class"]
                ),
                permitted_classifications=frozenset(
                    params["policy"]["permitted_classifications"]
                ),
            )
        )
    )
    corpus_attribute = ontology["similarity_corpus_attribute_by_class"]
    view = reader.as_of(tenant_id=tenant_id, at=boundary)
    corpus = {
        (tenant_id, record.claim.entity_uri): record.claim.attributes[
            corpus_attribute[record.claim.entity_class]
        ]
        for record in view.entities
        if record.claim.entity_class in corpus_attribute
    }
    operators.register(
        SimilaritySelect(
            parameters=SimilaritySelectParameters(
                query=params["similarity"]["query"],
                minimum_score_percent=params["similarity"][
                    "minimum_score_percent"
                ],
                ranked_entity_classes=frozenset(
                    params["similarity"]["ranked_entity_classes"]
                ),
            ),
            index=TokenOverlapIndex(
                corpus=corpus,
                index_version=params["similarity"]["index_version"],
            ),
        )
    )
    operators.register(
        TemporalAsOf(
            parameters=TemporalAsOfParameters(
                require_valid_at_boundary=params["temporal"][
                    "require_valid_at_boundary"
                ]
            )
        )
    )
    operators.register(
        TraversalNeighborhood(
            parameters=TraversalNeighborhoodParameters(
                seed_entity_classes=frozenset(
                    params["traversal"]["seed_entity_classes"]
                ),
                relationship_types=frozenset(
                    params["traversal"]["relationship_types"]
                ),
                depth_limit=params["traversal"]["depth_limit"],
            )
        )
    )
    return operators


class ArtifactTokenSource:
    # TokenSourceProtocol over the token-table artifact: only ACTIVE
    # entries yield a grant; the expired entry refuses like an unknown
    # token (fail closed; example-05 pattern).

    def __init__(self, *, path: Path) -> None:
        self._path = path

    def grant_for(self, *, token: str) -> TokenGrant | None:
        import hmac

        table = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        for entry in table["tokens"]:
            if entry["status"] != "active":
                continue
            if hmac.compare_digest(entry["token"], token):
                return TokenGrant(
                    client_id=entry["client_id"],
                    scopes=tuple(entry["scopes"]),
                )
        return None


class NodeBindings:
    # Injected node bindings; outputs come from the artifact.

    def __init__(self, outputs: Mapping[str, Mapping[str, str]]) -> None:
        self._outputs = outputs

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        return dict(self._outputs[step_name])

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        return dict(self._outputs[step_name])


class DeclaredDebt:
    # DebtAssessmentBinding over artifact-declared nominal factors.

    def __init__(self, factors: Mapping[str, str]) -> None:
        self._factors = factors

    async def assess(
        self, *, tenant: str, step_name: str, ref: str
    ) -> DebtAssessment:
        return DebtAssessment(
            debt=Decimal("0"),
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal(self._factors["freshness"]),
                completeness=Decimal(self._factors["completeness"]),
                semantic_consistency=Decimal(
                    self._factors["semantic_consistency"]
                ),
            ),
        )


class UnconsultedSink:
    # The regime declares grant_requires_approval: false — tier 2 must
    # never be consulted; consultation is a hard failure.

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise AssertionError("tier-2 sink consulted under an auto regime")


def _no_product(*, tenant: str, product_class: str, version: str) -> Any:
    raise ProductNotServable(
        f"no gate-admitted product at {tenant}/{product_class}/{version}"
    )


def _call(app: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(go())


class GridReplayEnvironment:
    """The deployment side of the replay seam (``ReplayEnvironment``): the
    projection, the operators as declared, and the product envelope — all
    rebuilt from the same artifacts the record phase used, and VERIFIED by
    the engine against the record rather than trusted."""

    def __init__(
        self,
        *,
        control: Any,
        ontology: Any,
        reader: GraphReader,
        policy_version: str,
        now: datetime,
    ) -> None:
        self._control = control
        self._ontology = ontology
        self._reader = reader
        self._policy_version = policy_version
        self._now = now

    def resolve_plan(self, *, plan_id: str) -> Any:
        declared = self._control["product_class"]
        if plan_id != declared["plan_id"]:
            raise LookupError(plan_id)
        return GridLoadPlan(
            plan_id=declared["plan_id"],
            required=self._registry().keys(),
        )

    def _registry(self) -> OperatorRegistry:
        return _operators(
            control=self._control,
            ontology=self._ontology,
            reader=self._reader,
            tenant_id=self._ontology["tenant_id"],
            boundary=_instant(self._control["decision"]["temporal_boundary"]),
            policy_version=self._policy_version,
        )

    def resolve_operators(
        self, *, operator_keys: tuple[str, ...]
    ) -> OperatorRegistry:
        return self._registry()

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        declared = self._control["product_class"]
        return ContextProductContract(
            schema_name=declared["schema_name"],
            schema_version=declared["schema_version"],
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=self._now
            + timedelta(seconds=declared["product_ttl_seconds"]),
            ttl_anchor=declared["ttl_anchor"],
            lineage=ProductLineage(
                operators_invoked=frozenset(
                    record.content_generation_path.operator_plan
                ),
                policy_bundle_versions=frozenset(
                    binding.version
                    for binding in record.policy_bindings.bindings
                ),
                graph_snapshot_at=record.context_fabric_snapshot.temporal_boundary,
            ),
            payload=projection.payload,
        )


@dataclass
class RecordedDecision:
    """Everything the replay phase needs, plus the originals it must NOT
    need (kept only to assert byte-equality against)."""

    tenant_id: str
    registry: ControlPlaneRegistry
    store: FileArtifactStore
    reader: GraphReader
    environment: GridReplayEnvironment
    record_address: str
    override_record_address: str
    override_original: ShedDetermination
    override_final: ShedDetermination
    override_overridden: bool
    original_product: ContextProductContract
    provider: DetachedJwsIdentityProvider
    trusted: Mapping[str, JsonWebKey]
    active_client_id: str
    definition: AgentDefinition
    grant: SkillGrant
    policy_version: str
    authz_allowed_scope: str
    authz_refused_scope: str
    authz_refusal_code: str


def record(root: Path, handle_holder: dict[str, Any]) -> RecordedDecision:
    """Phase 1: make the decision — fabric, skilled agent, auth-bound
    approval — and land its five-dimension record in the ArtifactStore."""
    ontology = _load("ontology.yaml")
    events = _load("events.yaml")
    control = _load("controlplane.yaml")
    agent_doc = _load("agent.yaml")
    prompt_doc = _load("prompt.yaml")
    skills_doc = _load("skills.yaml")
    task_doc = _load("task.yaml")
    workflow_doc = _load("workflow.yaml")
    hitl_doc = _load("hitl.yaml")
    tokens_doc = _load("tokens.yaml")

    tenant_id: str = ontology["tenant_id"]
    keys = control["keys"]
    boundary = _instant(control["decision"]["temporal_boundary"])
    now = _instant(control["decision"]["now"])
    clock = _ticking_clock(_instant(hitl_doc["clock"]["base"]))

    # --- Control Plane: fabric + agent + workflow + HITL closures -----------
    audit = AuditLog()
    registry = ControlPlaneRegistry(clock=clock, audit_log=audit)
    spec_version = registry.register(
        keys["resolution_spec"], _resolution_spec(ontology)
    )
    policy_version = registry.register(
        keys["policy_bundle"], control["policy_bundle"]
    )
    for doc in (agent_doc, task_doc, workflow_doc):
        for reference in doc.get("referenced_artifacts", {}).values():
            artifact_class = declared_artifact_class(reference["class_id"])
            declared = parse_artifact(
                {
                    "class_id": reference["class_id"],
                    "semver": reference["semver"],
                    "declaration": reference["declaration"],
                },
                artifact_class,
            )
            registry.register_typed(reference["key"], declared, artifact_class)
    prompt = parse_artifact(prompt_doc["prompt_artifact"], PROMPT_ARTIFACT)
    assert isinstance(prompt, PromptArtifact)
    registry.register_typed(
        prompt_doc["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    definition = parse_artifact(agent_doc["agent_definition"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    definition_key = agent_doc["keys"]["agent_definition"]
    definition_version = registry.register_versioned(
        definition_key, definition, AGENT_DEFINITION
    )
    assert isinstance(definition_version, str)
    definition_hash = content_hash(definition)
    task = parse_artifact(task_doc["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    registry.register_versioned(
        workflow_doc["keys"]["task_definition"], task, TASK_DEFINITION
    )
    workflow_definition = parse_artifact(
        workflow_doc["workflow_definition"], WORKFLOW_DEFINITION
    )
    assert isinstance(workflow_definition, WorkflowDefinition)
    workflow_key = workflow_doc["keys"]["workflow_definition"]
    workflow_version = registry.register_versioned(
        workflow_key, workflow_definition, WORKFLOW_DEFINITION
    )
    assert isinstance(workflow_version, str)
    hitl_policy = parse_artifact(hitl_doc["hitl_policy"], HITL_POLICY)
    assert isinstance(hitl_policy, HitlPolicy)
    assert hitl_policy.signed_binding_required is True
    registry.register_typed(
        hitl_doc["keys"]["hitl_policy"], hitl_policy, HITL_POLICY
    )

    # --- the scope-mapping policy artifact (HARD-04; D-IMPL-68) --------------
    # Which scopes reach which tenants and actions is the deployment's
    # statement, registered like every other Control Plane bundle; the
    # driver holds no scope or tenant value (CINV-01).
    scope_doc = _load("scope_mapping.yaml")
    scope_mapping = parse_artifact(scope_doc["scope_mapping"], SCOPE_MAPPING)
    assert isinstance(scope_mapping, ScopeMappingArtifact)
    scope_mapping_version = registry.register_typed(
        scope_doc["keys"]["scope_mapping"], scope_mapping, SCOPE_MAPPING
    )

    # --- boot and ingest -----------------------------------------------------
    handle = boot(
        database_path=root / "grid.sqlite3",
        registry=registry,
        resolution_spec_key=keys["resolution_spec"],
        resolution_spec_version=spec_version,
        policy_bundle_key=keys["policy_bundle"],
        policy_bundle_version=policy_version,
    )
    handle_holder["handle"] = handle
    for envelope in _envelopes(ontology, events):
        handle.worker.ingest(envelope)

    # --- the decision's projection + gates -----------------------------------
    operators = _operators(
        control=control,
        ontology=ontology,
        reader=handle.reader,
        tenant_id=tenant_id,
        boundary=boundary,
        policy_version=policy_version,
    )
    declared_class = control["product_class"]
    plan = GridLoadPlan(
        plan_id=declared_class["plan_id"], required=operators.keys()
    )
    perspective = Perspective(
        principal_id=control["perspective"]["principal_id"],
        role=control["perspective"]["role"],
    )
    execution = ProjectionEngine(
        reader=handle.reader, registry=operators
    ).execute(
        plan=plan,
        perspective=perspective,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
    )
    max_ttl_version = registry.register(
        keys["max_ttl"], MaxTTL(seconds=control["max_ttl_seconds"])
    )
    product_class = register_product_class(
        registry=registry,
        schema_name=declared_class["schema_name"],
        schema_version=declared_class["schema_version"],
        ttl_anchor=declared_class["ttl_anchor"],
        assembly_mode=declared_class["assembly_mode"],
        max_ttl_key=keys["max_ttl"],
        max_ttl_version=max_ttl_version,
    )
    candidate = ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id=execution.plan_id,
        tenant_id=tenant_id,
        temporal_boundary=boundary,
        expires_at=now
        + timedelta(seconds=declared_class["product_ttl_seconds"]),
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=execution.operators_invoked,
            policy_bundle_versions=frozenset({policy_version}),
            graph_snapshot_at=boundary,
        ),
        payload=execution.projection.payload,
    )
    gated = run_gates(
        candidate,
        engine_resolved=execution.operators_invoked,
        now=now,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(gated, ServableProduct), gated
    expected = control["expected"]
    assert gated.product.payload["entity_count"] == expected["entity_count"]

    # --- the skilled agent: grant in force at decision time (D-07) -----------
    catalog = SkillCatalog(registry)
    entry = parse_artifact(
        skills_doc["skills"]["feeder_load_metrics"], SKILL_CATALOG_ENTRY
    )
    assert isinstance(entry, SkillCatalogEntry)
    assert isinstance(catalog.register(entry), str)
    ledger = GrantLedger(
        control_plane=registry,
        catalog=catalog,
        sink=UnconsultedSink(),
        clock=clock,
    )
    callables = CallableRegistry()
    output_record = dict(skills_doc["callable"]["output_record"])
    callables.register(
        skills_doc["callable"]["registered_key"],
        lambda arguments: {**output_record, **arguments},
    )
    agent = AgentFactory(
        control_plane=registry, callable_registry=callables
    ).construct(
        definition_key=definition_key,
        definition_version=definition_version,
        bound_skills=ledger.bound_view(definition_hash),
    )
    assert isinstance(agent, Agent)
    grant = SkillGrant(
        agent_definition_hash=definition_hash, **skills_doc["grant"]
    )
    granted = ledger.request(
        grant, definition=definition, actor=skills_doc["actors"]["requesting_actor"]
    )
    assert granted == content_hash(grant)
    in_force = ledger.grant_set_hash(definition_hash)
    assert in_force == grant_set_hash(frozenset({content_hash(grant)}))
    assert agent.consume(gated.product, now=now) is gated.product
    invocation = agent.invoke_skill(
        skills_doc["grant"]["skill_name"],
        arguments=skills_doc["dispatch"]["arguments"],
    )
    assert isinstance(invocation, SkillInvocation)
    assert dict(invocation.output) == skills_doc["dispatch"]["expected_output"]

    # --- the workflow suspends at the load-shed ApprovalGate ------------------
    key_id: str = hitl_doc["keys"]["signing_key_id"]
    key_dir = root / "keys"
    key_dir.mkdir()
    key = ECKey.generate_key("P-256", parameters={"kid": key_id})
    (key_dir / f"{key_id}.jwk").write_text(
        json.dumps(key.as_dict(private=True)), encoding="utf-8"
    )
    provider = DetachedJwsIdentityProvider(
        key_source=FileBackedKeySource(directory=key_dir)
    )
    trusted: dict[str, JsonWebKey] = {key_id: key.as_dict(private=False)}
    transport = InMemoryHitlTransport(
        control_plane=registry,
        hitl_policy_key=hitl_doc["keys"]["hitl_policy"],
        identity_provider=provider,
        trusted_keys=trusted,
    )
    store = FileArtifactStore(root=root / "artifacts")
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=store,
        hitl_transport=transport,
        skill_binding=NodeBindings(hitl_doc["node_outputs"]),
        agent_binding=NodeBindings(hitl_doc["node_outputs"]),
        clock=clock,
        debt_binding=DeclaredDebt(hitl_doc["debt_factors"]),
    )
    factory = WorkflowFactory(control_plane=registry)
    workflow = factory.construct(
        definition_key=workflow_key, definition_version=workflow_version
    )
    drive = hitl_doc["drive"]
    suspended = asyncio.run(
        engine.execute(workflow, execution_id=drive["execution_id"])
    )
    assert isinstance(suspended, WorkflowSuspended), suspended
    assert suspended.gate == drive["expected_gate"]
    state_key = f"{tenant_id}/{drive['execution_id']}"
    state = registry.state_store.get(WORKFLOW_STATE, state_key)
    assert isinstance(state, WorkflowStateRecord)

    # --- the AUTH-BOUND approval through the hardened door (D-14) -------------
    app = create_app(
        ApiDependencies(
            control_plane=registry,
            artifact_store=store,
            product_resolver=_no_product,
            workflow_factory=factory,
            workflow_engine=engine,
            hitl_transport=transport,
            skill_catalog=catalog,
            grant_ledger=ledger,
        ),
        auth=BearerTokenAuth(
            token_source=ArtifactTokenSource(path=ARTIFACTS / "tokens.yaml")
        ),
        # Tenant authorization at the door (HARD-04; D-IMPL-68): the
        # authorizer interprets the registered scope mapping per request
        # and audits every allow AND deny decision.
        authorizer=ControlPlaneTenantAuthorizer(
            control_plane=registry,
            scope_mapping_key=scope_doc["keys"]["scope_mapping"],
            clock=clock,
        ),
    )
    entries = {e["label"]: e for e in tokens_doc["tokens"]}
    active = entries["approver"]
    outsider = entries["unauthorized"]
    bearer = {"Authorization": f"Bearer {active['token']}"}

    # --- tenant authorization: allowed and refused (Phase 10 D-16) ------------
    # The approver token's scope is mapped to this tenant and both HITL
    # actions; the outsider token is AUTHENTICATED (its entry is active)
    # but its scope is absent from the mapping, so deny-by-default refuses
    # it with the typed 403 — the shared constant, never prose.
    authz_refused = _call(
        app,
        "GET",
        f"/hitl/queue?tenant={tenant_id}",
        headers={"Authorization": f"Bearer {outsider['token']}"},
    )
    assert authz_refused.status_code == 403, authz_refused.text
    authz_refusal_code = authz_refused.json()["detail"]["error_code"]
    assert authz_refusal_code == ERROR_TENANT_UNAUTHORIZED
    # Both outcomes land in the one Control Plane audit log with the exact
    # mapping version in force (D-09/D-10).
    denied = [
        event
        for event in audit.events()
        if event.action == "authz_decision" and not event.resolved
    ]
    assert len(denied) == 1
    assert denied[0].actor == outsider["client_id"]
    assert denied[0].version == scope_mapping_version
    queue = _call(
        app, "GET", f"/hitl/queue?tenant={tenant_id}", headers=bearer
    )
    assert queue.status_code == 200, queue.text
    (pending_doc,) = queue.json()
    pending = PendingHitlEvent.model_validate(pending_doc)
    assert pending.product_content_hash == content_hash(state)
    approver = hitl_doc["approver"]
    binding = HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=_instant(approver["action_time"]),
        product_content_hash=pending.product_content_hash,
    )
    signed = sign_principal_binding(binding, provider=provider, key_id=key_id)
    admitted = _call(
        app,
        "POST",
        "/hitl/actions",
        json={
            "event_key": pending.event_key,
            "tenant": tenant_id,
            "action": drive["approval_action"],
            "principal": binding.model_dump(mode="json"),
            "annotation": None,
            "signed_binding": signed.model_dump(mode="json"),
        },
        headers=bearer,
    )
    assert admitted.status_code == 200, admitted.text
    (submission,) = transport.submissions(tenant=tenant_id)
    assert submission.principal.approver.subject_id == active["client_id"]
    assert submission.signed_binding == signed

    # The door is submit-only (D-IMPL-62): the D-16-verified submission IS
    # the authority-path landing; this driver — the owning composition —
    # consumes the event and resumes.
    action_record = HitlActionRecord(
        event=pending, submission=submission, approved=True
    )
    hitl_actions_block = canonical_bytes(action_record).decode("utf-8")
    assert transport.dequeue(tenant=tenant_id) is not None
    outcome = asyncio.run(
        engine.resume(
            workflow,
            execution_id=drive["execution_id"],
            decision=drive["resume_decision"],
        )
    )
    assert isinstance(outcome, WorkflowCompleted), outcome
    assert outcome.terminal_state == drive["resume_decision"]

    # --- the five-dimension record, served through the ReplayWriter -----------
    conditioning = agent.perspective_conditioning(
        principal_id=perspective.principal_id,
        grant_set_hash=ledger.grant_set_hash(definition_hash),
    ).model_copy(update={"delegation_chain": outcome.delegation_chain})
    replay_record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=perspective,
        policy_bindings=(
            PolicyBinding(key=keys["policy_bundle"], version=policy_version),
        ),
        assembly_mode=declared_class["assembly_mode"],
        recorded_at=now,
        agent_conditioning=conditioning,
        hitl_actions=hitl_actions_block,
        workflow_step_sequence=outcome.step_sequence_block,
    )
    served = serve(
        product=gated,
        record=replay_record,
        replay_writer=ReplayWriter(
            store=store,
            artifact_class=control["artifacts"]["replay_record_class"],
        ),
    )

    # --- the OverrideBoundary: the human substitutes the shed scope -----------
    # The agent's shed determination crosses a typed boundary where the
    # shift supervisor substitutes it. Original and substitute are BOTH
    # artifact values; both must land in the replay record (§8.2 —
    # "the original agent output and the override are both in the replay
    # record"; T-07-16). This driver only interprets (§6.4).
    override_doc = hitl_doc["override"]
    override_boundary: OverrideBoundary[ShedDetermination] = OverrideBoundary(
        transport=transport,
        audit=audit,
        clock=clock,
        control_plane=registry,
        hitl_policy_key=hitl_doc["keys"]["hitl_policy"],
        identity_provider=provider,
        trusted_keys=trusted,
    )
    override_original = ShedDetermination(**override_doc["original"])
    override_substitute = ShedDetermination(**override_doc["substitute"])
    proposed = override_boundary.propose(
        tenant=tenant_id,
        event_key=override_doc["event"]["event_key"],
        workflow_state_ref=override_doc["event"]["workflow_state_ref"],
        original=override_original,
    )
    # The proposal-time content hash is what the overrider's binding must
    # echo (T-07-17/T-07-39 TOCTOU doctrine).
    assert proposed.product_content_hash == content_hash(override_original)
    overrider = override_doc["overrider"]
    overrider_entry = entries[overrider["token_label"]]
    assert overrider_entry["status"] == "active"
    assert (
        overrider["identity"]["subject_id"] == overrider_entry["client_id"]
    )
    overrider_binding = HumanPrincipalBinding(
        approver=ApproverIdentity(**overrider["identity"]),
        authentication=AuthenticationContext(**overrider["authentication"]),
        action_time=_instant(overrider["action_time"]),
        product_content_hash=proposed.product_content_hash,
    )
    overrider_signed = sign_principal_binding(
        overrider_binding, provider=provider, key_id=key_id
    )
    # The artifact decides override vs confirm; the driver interprets.
    overriding = override_doc["drive"]["action"] == "override"
    resolution = override_boundary.resolve(
        tenant=tenant_id,
        event_key=proposed.event_key,
        principal=overrider_binding,
        override=override_substitute if overriding else None,
        signed_binding=overrider_signed,
    )
    assert isinstance(resolution, OverrideResolution)
    assert resolution.record.overridden == overriding
    assert resolution.record.original == override_original
    override_final = override_substitute if overriding else override_original
    assert resolution.record.final == override_final
    # Both values are in the pre-serialized dimension-2 block, byte-
    # assertably (T-07-16 mitigation).
    assert (
        canonical_bytes(override_original).decode("utf-8")
        in resolution.hitl_actions_block
    )
    assert (
        canonical_bytes(override_final).decode("utf-8")
        in resolution.hitl_actions_block
    )

    # The override decision's OWN five-dimension record lands in the same
    # store: dimension 2 carries the override block verbatim.
    override_record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=perspective,
        policy_bindings=(
            PolicyBinding(key=keys["policy_bundle"], version=policy_version),
        ),
        assembly_mode=declared_class["assembly_mode"],
        recorded_at=now,
        agent_conditioning=conditioning,
        hitl_actions=resolution.hitl_actions_block,
        workflow_step_sequence=outcome.step_sequence_block,
    )
    override_served = serve(
        product=gated,
        record=override_record,
        replay_writer=ReplayWriter(
            store=store,
            artifact_class=control["artifacts"]["replay_record_class"],
        ),
    )

    # The artifacts a forensic replay resolves land in the SAME store, at
    # exact content-addressed versions (CLAUDE.md §7.4; D-IMPL-26/27).
    store.put(
        tenant_id=tenant_id,
        artifact_class=control["artifacts"]["agent_definition_class"],
        name=definition.name,
        artifact=definition,
    )
    prompt_name = parse_artifact_uri(
        agent_doc["agent_definition"]["instruction_bindings"][0]["prompt"]
    )
    store.put(
        tenant_id=tenant_id,
        artifact_class=prompt_name.artifact_class,
        name=prompt_name.name,
        artifact=prompt,
    )
    store.put(
        tenant_id=tenant_id,
        artifact_class=control["artifacts"]["skill_grant_class"],
        name=control["artifacts"]["skill_grant_name"],
        artifact=grant,
    )

    return RecordedDecision(
        tenant_id=tenant_id,
        registry=registry,
        store=store,
        reader=handle.reader,
        environment=GridReplayEnvironment(
            control=_load("controlplane.yaml"),
            ontology=ontology,
            reader=handle.reader,
            policy_version=policy_version,
            now=now,
        ),
        record_address=served.replay_ref.content_address,
        override_record_address=override_served.replay_ref.content_address,
        override_original=override_original,
        override_final=override_final,
        override_overridden=overriding,
        original_product=gated.product,
        provider=provider,
        trusted=trusted,
        active_client_id=active["client_id"],
        definition=definition,
        grant=grant,
        policy_version=policy_version,
        authz_allowed_scope=active["scopes"][0],
        authz_refused_scope=outsider["scopes"][0],
        authz_refusal_code=authz_refusal_code,
    )


def replay_decision(ctx: RecordedDecision) -> DecisionReplayRecord:
    """Phase 2: from the record address alone, resolve every recorded
    version exactly and reproduce the decision byte-for-byte."""
    control = _load("controlplane.yaml")
    agent_class: str = control["artifacts"]["agent_definition_class"]

    # --- exact reproduction (whitepaper §7.10) --------------------------------
    outcome = replay(
        record_address=ctx.record_address,
        store=ctx.store,
        reader=ctx.reader,
        control_plane=ctx.registry,
        environment=ctx.environment,
    )
    resolved = outcome.record
    # Byte equality through the canonical serializer: the same bytes.
    assert canonical_bytes(outcome.product) == canonical_bytes(
        ctx.original_product
    )
    assert (
        outcome.product_content_address
        == resolved.content_generation_path.product_content_address
    )

    # --- agent version, from the store at its exact recorded hash -------------
    dimension_four = resolved.perspective_conditioning
    agent_definition = resolve_artifact(
        store=ctx.store,
        content_address=dimension_four.agent_definition_hash,
        contract=AgentDefinition,
    )
    assert dimension_four.agent_definition_uri.endswith(
        f"@{agent_definition.artifact_version}"
    )
    assert content_hash(agent_definition) == content_hash(ctx.definition)

    # --- prompt-artifact version, pinned by the resolved definition -----------
    pinned_prompt = agent_definition.instruction_bindings[0].prompt
    prompt_name = parse_artifact_uri(pinned_prompt)
    (prompt_address,) = ctx.store.versions(
        tenant_id=ctx.tenant_id,
        artifact_class=prompt_name.artifact_class,
        name=prompt_name.name,
    )
    resolved_prompt = resolve_artifact(
        store=ctx.store, content_address=prompt_address, contract=PromptArtifact
    )
    assert resolved_prompt.artifact_version == prompt_name.artifact_version

    # --- skill-set in force, recomputed from the stored grant (D-07) ----------
    (grant_address,) = ctx.store.versions(
        tenant_id=ctx.tenant_id,
        artifact_class=control["artifacts"]["skill_grant_class"],
        name=control["artifacts"]["skill_grant_name"],
    )
    resolved_grant = resolve_artifact(
        store=ctx.store, content_address=grant_address, contract=SkillGrant
    )
    assert dimension_four.grant_set_hash == grant_set_hash(
        frozenset({content_hash(resolved_grant)})
    )

    # --- the hardened HITL surface, reproduced from the record (D-14) ---------
    action = HitlActionRecord.model_validate_json(
        resolved.policy_bindings.hitl_actions
    )
    assert action.submission.signed_binding is not None
    reproduced_principal = verify_principal_binding(
        action.submission.signed_binding,
        provider=ctx.provider,
        public_keys=ctx.trusted,
    )
    # The approver principal and binding reproduce exactly as recorded:
    # the grant-derived subject, and the hash of what the approver saw.
    assert reproduced_principal == action.submission.principal
    assert (
        reproduced_principal.approver.subject_id == ctx.active_client_id
    )
    assert (
        reproduced_principal.product_content_hash
        == action.event.product_content_hash
    )
    # The workflow trace is on dimension 5, verbatim and non-empty.
    assert resolved.content_generation_path.workflow_step_sequence.startswith(
        "["
    )

    # --- the OverrideBoundary, reproduced from ITS record (§8.2; D-07) --------
    # The override decision's record resolves from the store and replays:
    # the reproduced product is byte-equal, and dimension 2 carries BOTH
    # the agent's original output and the human's override, verbatim.
    override_outcome = replay(
        record_address=ctx.override_record_address,
        store=ctx.store,
        reader=ctx.reader,
        control_plane=ctx.registry,
        environment=ctx.environment,
    )
    assert canonical_bytes(override_outcome.product) == canonical_bytes(
        ctx.original_product
    )
    override_block = override_outcome.record.policy_bindings.hitl_actions
    override_action = OverrideActionRecord[
        ShedDetermination
    ].model_validate_json(override_block)
    assert override_action.overridden == ctx.override_overridden
    assert override_action.original == ctx.override_original
    assert override_action.final == ctx.override_final
    # Byte-assertable: both values are literally in the recorded block.
    assert (
        canonical_bytes(ctx.override_original).decode("utf-8")
        in override_block
    )
    assert (
        canonical_bytes(ctx.override_final).decode("utf-8") in override_block
    )
    # The overrider's signed binding verifies from the record alone and
    # reproduces the grant-derived subject (D-14/D-16).
    assert override_action.submission.signed_binding is not None
    reproduced_overrider = verify_principal_binding(
        override_action.submission.signed_binding,
        provider=ctx.provider,
        public_keys=ctx.trusted,
    )
    assert reproduced_overrider == override_action.submission.principal
    assert reproduced_overrider.approver.subject_id == ctx.active_client_id

    # --- negative: a moving-target ref is refused outright --------------------
    # Deliberately-invalid input constructed inline for the refusal test —
    # the only place the moving-target token appears in this example.
    moving_target = artifact_uri(
        tenant_id=ctx.tenant_id,
        artifact_class=agent_class,
        name=agent_definition.name,
        artifact_version=LATEST_VERSION_TOKEN,
    )
    refused = False
    try:
        resolve_artifact_at_uri(
            store=ctx.store, uri=moving_target, contract=AgentDefinition
        )
    except MovingTargetRefused:
        refused = True
    assert refused, "a moving-target ref must be refused (D-IMPL-26)"

    # --- negative: the audit record is version-sensitive ----------------------
    # Mutate a COPY of the record (never the canonical one): bump the
    # recorded policy-bundle version to one that was never registered.
    binding = resolved.policy_bindings.bindings[0]
    mutated_binding = binding.model_copy(
        update={"version": control["artifacts"]["unregistered_policy_version"]}
    )
    mutated = resolved.model_copy(
        update={
            "policy_bindings": resolved.policy_bindings.model_copy(
                update={
                    "bindings": (mutated_binding,)
                    + resolved.policy_bindings.bindings[1:]
                }
            )
        }
    )
    assert mutated != resolved
    mutated_ref = ctx.store.put(
        tenant_id=ctx.tenant_id,
        artifact_class=control["artifacts"]["replay_record_class"],
        name=control["artifacts"]["mutated_record_name"],
        artifact=mutated,
    )
    unresolvable = False
    try:
        replay(
            record_address=mutated_ref.content_address,
            store=ctx.store,
            reader=ctx.reader,
            control_plane=ctx.registry,
            environment=ctx.environment,
        )
    except ReplayUnresolvable:
        unresolvable = True
    assert unresolvable, (
        "a record naming a policy-bundle version the Control Plane never"
        " registered must refuse to reproduce (D-IMPL-26/38)"
    )
    return resolved


def main() -> int:
    handle_holder: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="ccf-decision-replay-") as scratch:
        try:
            ctx = record(Path(scratch), handle_holder)
            resolved = replay_decision(ctx)
        finally:
            handle = handle_holder.get("handle")
            if handle is not None:
                handle.close()

        print("examples/06-decision-replay: OK")
        print(f"  tenant                 {ctx.tenant_id}")
        print(f"  replay record          {ctx.record_address[:16]}…")
        print(
            "  agent (dim 4)          "
            f"{resolved.perspective_conditioning.agent_definition_uri}"
        )
        print(
            "  grant-set hash         "
            f"{resolved.perspective_conditioning.grant_set_hash[:16]}…"
        )
        print(f"  approver (reproduced)  {ctx.active_client_id}")
        print(
            "  authz allowed (200)    "
            f"{ctx.authz_allowed_scope} scope → tenant {ctx.tenant_id}"
        )
        print(
            "  authz refused (403)    "
            f"{ctx.authz_refused_scope} scope → {ctx.authz_refusal_code}"
        )
        print(
            "  override (dim 2)       "
            f"{ctx.override_original.shed_megawatts}MW/"
            f"{ctx.override_original.duration_minutes}min → "
            f"{ctx.override_final.shed_megawatts}MW/"
            f"{ctx.override_final.duration_minutes}min"
            " (both values in the record)"
        )
        print("  reproduction           byte-equal")
        return 0


if __name__ == "__main__":
    sys.exit(main())
