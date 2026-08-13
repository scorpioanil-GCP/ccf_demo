"""examples/06-decision-replay — record, then reproduce exactly (EXAM-07).

The audit-by-construction proof, in an energy/grid-operations domain: a
load-shed authorization is decided against a real fabric — an
``AnalyticsInsightsAgent`` with a skill grant in force, a minimal grid-ops
workflow suspending at an ApprovalGate, and an AUTH-BOUND human approval through
``create_app(auth=BearerTokenAuth(...))`` with a D-16-required
``SignedPrincipalBinding`` (the replay leg of the D-14 absorption). Then, **from
the replay record alone**, the decision is reproduced: graph snapshot, policy
bundle version, agent version, skill-set in force, and prompt-artifact version
all resolve from the ArtifactStore at their EXACT recorded versions.

This file is the **call spine** an adopter would actually write. It asserts
nothing and prints nothing: its assertions live in
``tests/examples/test_decision_replay_output.py``, where they are run by
``pytest`` and can fail a build (D-09). ``make example-06`` running clean means
the spine executed; the test module is what says it was *right*.

The one thing the spine still does itself, and must: **it selects which policy
bindings were in force.** Every ``PolicyBinding`` below is built from a pin the
adopter read off ``BootedFabric.pins`` by key. ``pins`` is never handed to
``build_replay_record``, and ``ResolvedPins`` grows no helper that would turn a
pin set into bindings — D-06 keeps that selection in adopter code, because
dimension 2 assembled by a rule nobody in the deployment wrote down is not an
audit record. In the file whose whole subject is that record, the selection stays
on the page.

Every domain value is loaded from ``artifacts/*.yaml`` and enumerated by
``artifacts/manifest.yaml`` (CLAUDE.md §6.4, the No-Hardcoding Rule).

Run it: ``make example-06`` (or
``PYTHONPATH=src:runtime python examples/06-decision-replay/run.py``).
"""

from __future__ import annotations

import asyncio
import hmac
import json
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import httpx
import yaml
from joserfc.jwk import ECKey

from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.factory import AgentFactory
from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
    ProjectionRequirements,
    SignalBatch,
    declared_artifact_class,
    load_artifact,
)
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import (
    ResolvedPins,
    build_operator_registry,
    load_and_boot,
    refuse_operator_set_divergence,
)
from ccf.graph.protocols import GraphReader, GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.hitl.approval_gate import HitlActionRecord
from ccf.hitl.identity_binding import sign_principal_binding
from ccf.hitl.override import OverrideBoundary, OverrideResolution
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import HITL_POLICY, InMemoryHitlTransport, PendingHitlEvent
from ccf.operators.base import OperatorOutput
from ccf.operators.registry import OperatorRegistry
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
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.engine import replay, resolve_artifact
from ccf.replay.record import DecisionReplayRecord, PolicyBinding, build_replay_record
from ccf.replay.serve import ReplayWriter, ServedProduct, serve
from ccf.skills.callables import CallableRegistry
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.grants import ApprovalOutcome, GrantLedger, SkillGrant
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.authz.artifact import SCOPE_MAPPING
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.mcp.auth import TokenGrant
from ccf_runtime.mcp.egress import ProductNotServable
from ccf_runtime.workflow.engine import WorkflowEngine, WorkflowSuspended
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
MANIFEST = ARTIFACTS / "manifest.yaml"


def _ticking_clock(base: datetime) -> Any:
    """A monotone audit clock seeded from an artifact, never from the wall.

    Every Control Plane registration and every HITL action is stamped from it,
    so the audit sequence is a function of a declared instant rather than of
    when the example happened to run — which is what makes the run replayable at
    all.
    """
    state = {"now": base}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


class ShedDetermination(CCFContract):
    # The deployment's typed agent-output shape at the OverrideBoundary —
    # deployment code, like the projection: the SDK ships the boundary mechanism
    # only, and every VALUE this shape carries lives in artifacts/hitl-drive.yaml
    # (§6.4; CINV-01). Decimals travel as quoted strings per the artifact
    # convention.

    feeder_ref: str
    shed_megawatts: str
    duration_minutes: str


class GridLoadPlan:
    """The deployment's Π: what the reconciled subgraph means to its reader.

    A projection is deployment code — this is what a user writes, and it is never
    a rewrite target (whitepaper §7.5).

    ``required`` is passed in from ``artifacts/projection-requirements.yaml``
    (``ccf.projection-requirements``) — the projection's OWN document, not the
    product class's and not the operator registry's keys. Under design E2
    (``docs/DECISIONS.md`` D-IMPL-86 and its correction of 2026-08-05) the two
    operator sets a deployment authors are separate documents:
    ``product-class.yaml``'s ``required_operator_keys`` is the Control Plane
    **claim** that fills the product's lineage, and this one is what the plan
    requires. ``refuse_operator_set_divergence`` binds them, between plan
    construction and ``ProjectionEngine.execute``, and that is where **authorable
    drift** fails.

    Feeding ``required`` from the product-class declaration instead would not be
    a second source at all: the declaration would reach the engine's
    ``operators_invoked`` through five pure transforms with no branch, so the
    two would be identical by construction and nothing an author could write
    would separate them. That matters twice over here — the replay environment
    reconstructs this plan, so both sites read the requirements artifact and both
    call the binder.
    """

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


class ArtifactTokenSource:
    # TokenSourceProtocol over the token-table artifact: only ACTIVE entries
    # yield a grant; the expired entry refuses like an unknown token (fail
    # closed; example-05 pattern). The entries arrive already parsed off
    # `booted.artifacts`, so there is no second read of the file to drift.

    def __init__(self, *, entries: tuple[Mapping[str, Any], ...]) -> None:
        self._entries = entries

    def grant_for(self, *, token: str) -> TokenGrant | None:
        for entry in self._entries:
            if entry["status"] != "active":
                continue
            if hmac.compare_digest(entry["token"], token):
                return TokenGrant(
                    client_id=entry["client_id"], scopes=tuple(entry["scopes"])
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
                semantic_consistency=Decimal(self._factors["semantic_consistency"]),
            ),
        )


class UnconsultedSink:
    # The regime declares grant_requires_approval: false — tier 2 must never be
    # consulted; consultation is a hard failure.

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise AssertionError("tier-2 sink consulted under an auto regime")


def _no_product(
    *,
    tenant: str,
    product_class: str,
    version: str,
    perspective: Any,
    request: Any,
) -> Any:
    # Carries the widened D-IMPL-108 signature even though it serves
    # nothing: an empty form that did not conform would not be a template.
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
    """The deployment side of the replay seam (``ReplayEnvironment``).

    The projection, the operators as declared, and the product envelope — all
    rebuilt from the same artifacts the record phase used, and VERIFIED by the
    engine against the record rather than trusted.

    It holds the same ``pins`` the record phase read, because the policy
    operator's admitted-bundle set is completed from them (D-IMPL-76): a replay
    that rebuilt the operator chain from a *different* admission set would
    reproduce a product the original fabric was never permitted to serve.

    It holds BOTH of design E2's authored operator-set documents for the same
    reason it holds the pins. The requirements artifact is what ``resolve_plan``
    plans from; the product-class declaration is the claim the plan is bound to
    by ``refuse_operator_set_divergence``. A reproduction that carried only one
    of the two could rebuild a plan the original deployment's governance
    contradicts and never notice.
    """

    def __init__(
        self,
        *,
        declared: ProductClassDeclaration,
        requirements: ProjectionRequirements,
        governance: Mapping[str, Any],
        parameters: Mapping[str, OperatorParametersArtifact],
        pins: ResolvedPins,
        policy_bundle_key: str,
        reader: GraphReader,
        tenant_id: str,
        boundary: datetime,
        now: datetime,
    ) -> None:
        self._declared = declared
        self._requirements = requirements
        self._governance = governance
        self._parameters = parameters
        self._pins = pins
        self._policy_bundle_key = policy_bundle_key
        self._reader = reader
        self._tenant_id = tenant_id
        self._boundary = boundary
        self._now = now

    def resolve_plan(self, *, plan_id: str) -> Any:
        if plan_id != self._governance["plan_id"]:
            raise LookupError(plan_id)
        # From the PROJECTION's own artifact, exactly as the record phase did —
        # not from `resolve_operators`'s registry, and not from the product
        # class, which under design E2 is the CLAIM rather than the plan's input.
        # The binder runs here too: a reproduction that planned from a
        # requirements document the product class contradicts would rebuild a
        # product the original deployment's own governance disowns, and this is
        # the last point before the engine at which that is still catchable.
        plan = GridLoadPlan(
            plan_id=self._governance["plan_id"],
            required=self._requirements.required_operator_keys,
        )
        refuse_operator_set_divergence(declared=self._declared, plan=plan)
        return plan

    def resolve_operators(self, *, operator_keys: tuple[str, ...]) -> OperatorRegistry:
        return build_operator_registry(
            parameters=self._parameters,
            view=self._reader.as_of(tenant_id=self._tenant_id, at=self._boundary),
            pins=self._pins,
            policy_bundle_key=self._policy_bundle_key,
            similarity_index_version=self._governance["similarity_index_version"],
        )

    def rehydrate_product(
        self, *, record: DecisionReplayRecord, projection: ProjectionOutput
    ) -> ContextProductContract:
        # `debt` is read back off dimension 5, never re-assessed (D-IMPL-100).
        # It is inside the product's content address, and D_c is computed from
        # observations and a `now` the replay does not re-derive — so a fresh
        # assessment here would be a different decision wearing this one's
        # identifier, and the engine's address check would say so.
        return ContextProductContract(
            schema_name=self._declared.schema_name,
            schema_version=self._declared.schema_version,
            plan_id=projection.plan_id,
            tenant_id=record.tenant_id,
            temporal_boundary=record.context_fabric_snapshot.temporal_boundary,
            expires_at=self._now
            + timedelta(seconds=self._governance["product_ttl_seconds"]),
            ttl_anchor=self._declared.ttl_anchor,
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
            debt=record.content_generation_path.debt,
            # And what that debt pointed at, for a harder reason (D-IMPL-118):
            # the carrier is a top-level vessel field, so `(record, projection)`
            # names it nowhere else and omitting it diverges every replay.
            debt_evidence=record.content_generation_path.debt_evidence,
            # And when its sources last published, for the same reason again
            # (D-IMPL-117 gap 2): the second Track B member takes the same
            # top-level placement, so dimension 5 is the only place a
            # `(record, projection)` rehydrator can read it back from.
            source_refresh_recency=(
                record.content_generation_path.source_refresh_recency
            ),
        )


@dataclass(frozen=True)
class ReplayDemonstration:
    """What one run of the spine produced, for a caller to inspect.

    The example returns its state rather than checking it here, so that
    ``tests/examples/test_decision_replay_output.py`` can hold the assertions
    where a test runner will actually run them.

    The ``booted`` fabric is returned still open, unlike the quickstart's: the
    replay leg reads through its ``reader``, and so do the tests' own negative
    probes. Its caller owns closing it.
    """

    booted: Any
    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    registry: ControlPlaneRegistry
    audit: AuditLog
    store: FileArtifactStore
    environment: GridReplayEnvironment

    product: ContextProductContract
    operators_invoked: frozenset[str]
    record: DecisionReplayRecord
    served: ServedProduct
    policy_version: str

    definition: AgentDefinition
    definition_version: str
    prompt: PromptArtifact
    grant: SkillGrant
    granted_address: str
    grant_set_hash: str
    skill_output: Mapping[str, str]
    consumed: ContextProductContract

    suspended_gate: str
    suspended_state_hash: str
    terminal_state: str
    submission: Any
    # The verification material a reader of the record needs, and no more: the
    # detached-JWS provider and the PUBLIC keys. A signed binding verifies from
    # the record alone plus these — never from anything the live run held.
    identity_provider: DetachedJwsIdentityProvider
    trusted_keys: Mapping[str, JsonWebKey]
    approver_client_id: str
    authz_refusal_status: int
    authz_refusal_code: str
    authz_refused_client_id: str
    scope_mapping_version: str

    reproduced: ContextProductContract
    reproduced_record: DecisionReplayRecord
    reproduced_address: str
    resolved_definition: AgentDefinition
    resolved_prompt: PromptArtifact
    resolved_prompt_pinned_version: str
    resolved_grant: SkillGrant
    agent_definition_class: str

    override_record: DecisionReplayRecord
    override_served: ServedProduct
    override_resolution: OverrideResolution[ShedDetermination]
    override_original: ShedDetermination
    override_final: ShedDetermination
    override_overridden: bool
    reproduced_override_record: DecisionReplayRecord
    reproduced_override_product: ContextProductContract

    mutated_record_address: str


def run(*, root: Path) -> ReplayDemonstration:
    """Record a decision against ``root``, then reproduce it from its record."""
    # The audit clock must exist before the FIRST registration, and the first
    # registration happens inside `load_and_boot` — so the one instant that
    # seeds it is read here, through the SDK's own artifact loader, from the very
    # document the manifest names as `decision`. Everything after boot reads that
    # artifact off `booted.artifacts`; this is the single ordering constraint the
    # one-call boot cannot absorb.
    decision_document = (ARTIFACTS / "decision.yaml").read_text(encoding="utf-8")
    decision = cast(
        DeclaredArtifact,
        load_artifact(
            decision_document,
            declared_artifact_class(yaml.safe_load(decision_document)["class_id"]),
        ),
    )
    clock = _ticking_clock(
        datetime.fromisoformat(decision.declaration["clock_base"])
    )
    audit = AuditLog()
    registry = ControlPlaneRegistry(clock=clock, audit_log=audit)

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every artifact in force, `load_and_boot` parses all of them,
    #    registers the `role: register` ones, and boots on the resulting pins.
    booted = load_and_boot(
        MANIFEST,
        registry=registry,
        connection={"database_path": str(root / "grid.sqlite3")},
    )
    # --8<-- [end:boot]

    # Each artifact comes back under its own manifest key, already validated
    # against the class the manifest declared for it — so these casts restate
    # what `load_and_boot` already enforced.
    events = cast(SignalBatch, booted.artifacts["events"])
    governance = cast(
        DeclaredArtifact, booted.artifacts["product-governance"]
    ).declaration
    declared = cast(ProductClassDeclaration, booted.artifacts["product-class"])
    requirements = cast(
        ProjectionRequirements, booted.artifacts["projection-requirements"]
    )
    perspective = cast(PerspectiveArtifact, booted.artifacts["perspective"])
    registration = cast(
        DeclaredArtifact, booted.artifacts["agent-registration"]
    ).declaration
    dispatch = cast(DeclaredArtifact, booted.artifacts["skill-dispatch"]).declaration
    human = cast(DeclaredArtifact, booted.artifacts["hitl-drive"]).declaration
    probes = cast(DeclaredArtifact, booted.artifacts["replay-probes"]).declaration
    token_entries = tuple(
        cast(DeclaredArtifact, booted.artifacts["tokens"]).declaration["tokens"]
    )

    boundary = datetime.fromisoformat(decision.declaration["temporal_boundary"])
    now = datetime.fromisoformat(decision.declaration["now"])

    # 2. Ingest from the batch the manifest declared `role: load`.
    for envelope in events.envelopes:
        booted.handle.worker.ingest(envelope)

    # 3. The graph view at the temporal boundary this deployment named.
    view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=boundary)

    # 4. The operator-parameters mapping, assembled by naming this deployment's
    #    OWN manifest keys. Deliberately not an isinstance filter or a class-id
    #    match: those are type introspection, and copied across nine examples
    #    they would be a new duplication class.
    parameters: Mapping[str, OperatorParametersArtifact] = {
        key: cast(OperatorParametersArtifact, booted.artifacts[key])
        for key in ("traversal", "temporal", "policy", "similarity")
    }

    # 5. The four-category operator chain (L4), from those artifacts.
    operators = build_operator_registry(
        parameters=parameters,
        view=view,
        pins=booted.pins,
        policy_bundle_key="policy-bundle",
        similarity_index_version=governance["similarity_index_version"],
    )

    # 6. Project (L5). The plan's `required` comes from the projection's OWN
    #    artifact — never from the operator registry's keys, and never from the
    #    product class, which is the claim rather than the plan's input.
    #
    #    The plan is a named local so the binder has a statement to occupy: the
    #    refusal belongs BETWEEN plan construction and `execute` (D-IMPL-86's
    #    correction of 2026-08-05), and a plan built inline as `execute`'s own
    #    argument leaves no such line. It is where the deployment's two authored
    #    operator sets are held to each other; edit either document alone and
    #    this run stops before a product is assembled from a set the deployment's
    #    own claim contradicts.
    plan = GridLoadPlan(
        plan_id=governance["plan_id"],
        required=requirements.required_operator_keys,
    )
    refuse_operator_set_divergence(declared=declared, plan=plan)
    execution = ProjectionEngine(
        reader=booted.handle.reader, registry=operators
    ).execute(
        plan=plan,
        perspective=perspective,
        tenant_id=booted.tenant_id,
        temporal_boundary=boundary,
    )

    # 7. L6 — and this cluster stays in adopter code deliberately.
    #
    #    Gate 3 compares the class's TTL CEILING against this product's own
    #    `expires_at`. That is only a check while the two are independently
    #    authored. Registering the MaxTTL value here is what MINTS
    #    `max_ttl_version` — the pin is a content hash of what was registered,
    #    which is why the product-class artifact cannot declare it. A helper that
    #    minted the pin and stamped the product would be comparing a value
    #    against itself, so the SDK ships no such helper.
    max_ttl_version = registry.register(
        declared.max_ttl_key, MaxTTL(seconds=governance["max_ttl_seconds"])
    )
    product_class = register_product_class(
        registry=registry,
        schema_name=declared.schema_name,
        schema_version=declared.schema_version,
        ttl_anchor=declared.ttl_anchor,
        assembly_mode=declared.assembly_mode,
        max_ttl_key=declared.max_ttl_key,
        max_ttl_version=max_ttl_version,
    )

    # 8. The lineage the product CLAIMS, and the gates.
    #
    #    The claim is the product class's `required_operator_keys` — the Control
    #    Plane's authored statement of what this product's assembly depends on.
    #    It is never `execution.operators_invoked`: filling the claim from the
    #    engine's own report would make Gate 2 compare a value against itself.
    #
    #    What Gate 2 then verifies is ASSEMBLY-PATH INTEGRITY: that the product
    #    served was assembled by the path the deployment claimed. The engine is a
    #    faithful transcriber of the plan rather than an independent witness of
    #    it — it builds its invoked set and its steps in one loop over the same
    #    operator plan — so the gate catches an assembly that departed from the
    #    plan, not a claim that was wrong to begin with. Authorable drift fails
    #    upstream, at `refuse_operator_set_divergence` in step 6.
    policy_version = booted.pins.version_for("policy-bundle")
    candidate = ContextProductContract(
        schema_name=product_class.schema_name,
        schema_version=product_class.schema_version,
        plan_id=execution.plan_id,
        tenant_id=booted.tenant_id,
        temporal_boundary=boundary,
        expires_at=now + timedelta(seconds=governance["product_ttl_seconds"]),
        ttl_anchor=product_class.ttl_anchor,
        lineage=ProductLineage(
            operators_invoked=frozenset(declared.required_operator_keys),
            policy_bundle_versions=frozenset({policy_version}),
            graph_snapshot_at=boundary,
        ),
        payload=execution.projection.payload,
    )
    match run_gates(
        candidate,
        engine_resolved=execution.operators_invoked,
        now=now,
        registry=registry,
        product_class=product_class,
    ):
        case ServableProduct() as gated:
            pass
        case refusal:
            raise RuntimeError(
                f"the three validation gates refused this product: {refusal}"
            )

    # --- the SDK classes registered here rather than by the manifest ----------
    # Five are AUTHOR-VERSIONED, and every one of them — prompt artifact
    # included — takes `register_versioned`, which runs the D-05 bump check that
    # `load_and_boot`'s `register_typed` does not. A manifest CAN name them, as
    # `registration: versioned`; declaring `typed` for one is refused at
    # preflight (D-IMPL-85). They stay here so the bump check is visible at the
    # call site. Two more are SDK classes a manifest cannot address at all: they
    # are in neither SDK mapping and the `ccf.` prefix is reserved, so an entry
    # naming either is REFUSED at load (D-IMPL-84) rather than resolved to the
    # open envelope — which is what protects the transport and the authorizer,
    # both of which read their real contracts back off the Control Plane by key.
    # Each still validates against its own contract here.
    prompt = cast(
        PromptArtifact,
        load_artifact(
            (ARTIFACTS / "prompt-artifact.yaml").read_text(encoding="utf-8"),
            PROMPT_ARTIFACT,
        ),
    )
    prompt_version = registry.register_versioned(
        registration["prompt_artifact_key"], prompt, PROMPT_ARTIFACT
    )
    if not isinstance(prompt_version, str):  # pragma: no cover
        raise RuntimeError(f"the prompt artifact was refused: {prompt_version!r}")
    definition = cast(
        AgentDefinition,
        load_artifact(
            (ARTIFACTS / "agent-definition.yaml").read_text(encoding="utf-8"),
            AGENT_DEFINITION,
        ),
    )
    definition_key = registration["agent_definition_key"]
    definition_version = registry.register_versioned(
        definition_key, definition, AGENT_DEFINITION
    )
    definition_hash = content_hash(definition)
    registry.register_versioned(
        registration["task_definition_key"],
        load_artifact(
            (ARTIFACTS / "task-definition.yaml").read_text(encoding="utf-8"),
            TASK_DEFINITION,
        ),
        TASK_DEFINITION,
    )
    workflow_definition = cast(
        WorkflowDefinition,
        load_artifact(
            (ARTIFACTS / "workflow-definition.yaml").read_text(encoding="utf-8"),
            WORKFLOW_DEFINITION,
        ),
    )
    workflow_key = registration["workflow_definition_key"]
    workflow_version = registry.register_versioned(
        workflow_key, workflow_definition, WORKFLOW_DEFINITION
    )
    registry.register_typed(
        registration["hitl_policy_key"],
        load_artifact(
            (ARTIFACTS / "hitl-policy.yaml").read_text(encoding="utf-8"),
            HITL_POLICY,
        ),
        HITL_POLICY,
    )
    scope_mapping_version = registry.register_typed(
        registration["scope_mapping_key"],
        load_artifact(
            (ARTIFACTS / "scope-mapping.yaml").read_text(encoding="utf-8"),
            SCOPE_MAPPING,
        ),
        SCOPE_MAPPING,
    )

    # --- the skilled agent: grant in force at decision time (D-07) ------------
    catalog = SkillCatalog(registry)
    entry = cast(
        SkillCatalogEntry,
        load_artifact(
            (ARTIFACTS / "skill-catalog-entry.yaml").read_text(encoding="utf-8"),
            SKILL_CATALOG_ENTRY,
        ),
    )
    catalog.register(entry)
    ledger = GrantLedger(
        control_plane=registry, catalog=catalog, sink=UnconsultedSink(), clock=clock
    )
    callables = CallableRegistry()
    output_record = dict(dispatch["callable_output_record"])
    callables.register(
        entry.binding.callable_ref,
        lambda arguments: {**output_record, **arguments},
    )
    agent = AgentFactory(
        control_plane=registry, callable_registry=callables
    ).construct(
        definition_key=definition_key,
        definition_version=definition_version,
        bound_skills=ledger.bound_view(definition_hash),
    )
    grant = SkillGrant(
        agent_definition_hash=definition_hash, **dispatch["grant_request"]
    )
    granted_address = ledger.request(
        grant, definition=definition, actor=dispatch["requesting_actor"]
    )
    in_force = ledger.grant_set_hash(definition_hash)
    consumed = agent.consume(gated.product, now=now)
    invocation = agent.invoke_skill(
        dispatch["grant_request"]["skill_name"],
        arguments=dispatch["dispatch"]["arguments"],
    )

    # --- the workflow suspends at the load-shed ApprovalGate ------------------
    key_id: str = human["signing_key_id"]
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
        hitl_policy_key=registration["hitl_policy_key"],
        identity_provider=provider,
        trusted_keys=trusted,
    )
    store = FileArtifactStore(root=root / "artifacts")
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=store,
        hitl_transport=transport,
        skill_binding=NodeBindings(human["node_outputs"]),
        agent_binding=NodeBindings(human["node_outputs"]),
        clock=clock,
        debt_binding=DeclaredDebt(human["debt_factors"]),
    )
    factory = WorkflowFactory(control_plane=registry)
    workflow = factory.construct(
        definition_key=workflow_key, definition_version=workflow_version
    )
    drive = human["drive"]
    suspended = asyncio.run(
        engine.execute(workflow, execution_id=drive["execution_id"])
    )
    if not isinstance(suspended, WorkflowSuspended):  # pragma: no cover
        raise RuntimeError(f"the workflow did not suspend at a gate: {suspended!r}")
    # The suspended state's content identity, captured HERE — before the resume
    # mutates it. This is what the approver is shown the hash of, and what their
    # signed binding must echo (T-07-17 TOCTOU doctrine); reading it after the
    # resume would hash a different state and prove nothing.
    suspended_state = registry.state_store.get(
        WORKFLOW_STATE, f"{booted.tenant_id}/{drive['execution_id']}"
    )
    if not isinstance(suspended_state, WorkflowStateRecord):  # pragma: no cover
        raise RuntimeError("the suspended workflow left no state record")
    suspended_state_hash = content_hash(suspended_state)

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
        auth=BearerTokenAuth(token_source=ArtifactTokenSource(entries=token_entries)),
        # Tenant authorization at the door (HARD-04; D-IMPL-68): the authorizer
        # interprets the registered scope mapping per request and audits every
        # allow AND deny decision.
        authorizer=ControlPlaneTenantAuthorizer(
            control_plane=registry,
            scope_mapping_key=registration["scope_mapping_key"],
            clock=clock,
        ),
    )
    entries = {entry_row["label"]: entry_row for entry_row in token_entries}
    active = entries["approver"]
    outsider = entries["unauthorized"]
    bearer = {"Authorization": f"Bearer {active['token']}"}

    # The outsider token is AUTHENTICATED (its entry is active) but its scope is
    # absent from the mapping, so deny-by-default refuses it.
    authz_refused = _call(
        app,
        "GET",
        f"/hitl/queue?tenant={booted.tenant_id}",
        headers={"Authorization": f"Bearer {outsider['token']}"},
    )
    queue = _call(
        app, "GET", f"/hitl/queue?tenant={booted.tenant_id}", headers=bearer
    )
    (pending_doc,) = queue.json()
    pending = PendingHitlEvent.model_validate(pending_doc)
    approver = human["approver"]
    binding = HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        product_content_hash=pending.product_content_hash,
    )
    signed = sign_principal_binding(binding, provider=provider, key_id=key_id)
    _call(
        app,
        "POST",
        "/hitl/actions",
        json={
            "event_key": pending.event_key,
            "tenant": booted.tenant_id,
            "action": drive["approval_action"],
            "principal": binding.model_dump(mode="json"),
            "annotation": None,
            "signed_binding": signed.model_dump(mode="json"),
        },
        headers=bearer,
    )
    (submission,) = transport.submissions(tenant=booted.tenant_id)

    # The door is submit-only (D-IMPL-62): the D-16-verified submission IS the
    # authority-path landing; this driver — the owning composition — consumes the
    # event and resumes.
    action_record = HitlActionRecord(
        event=pending, submission=submission, approved=True
    )
    transport.dequeue(tenant=booted.tenant_id)
    outcome = asyncio.run(
        engine.resume(
            workflow,
            execution_id=drive["execution_id"],
            decision=drive["resume_decision"],
        )
    )

    # --8<-- [start:record]
    # --- the five-dimension record, served through the ReplayWriter -----------
    # `policy_bindings` is built HERE, from the pin the adopter read off
    # `BootedFabric.pins` by key. `pins` itself is never passed: D-06 keeps the
    # SELECTION of which bindings were in force in adopter hands, because
    # dimension 2 assembled by a rule nobody in the deployment wrote down is not
    # an audit record — and this is the file whose whole subject is that record.
    conditioning = agent.perspective_conditioning(
        principal_id=perspective.principal_id, grant_set_hash=in_force
    ).model_copy(update={"delegation_chain": outcome.delegation_chain})
    record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=perspective,
        policy_bindings=(
            PolicyBinding(key="policy-bundle", version=policy_version),
        ),
        assembly_mode=declared.assembly_mode,
        recorded_at=now,
        agent_conditioning=conditioning,
        hitl_actions=canonical_bytes(action_record).decode("utf-8"),
        workflow_step_sequence=outcome.step_sequence_block,
        # Which adapter answered, at which version, under which credential
        # REFERENCE names — dimension 2, read off the pin the boot reported and
        # off nothing else. The other examples deliberately leave this on its
        # `no-adapter` default, so the always-on run exercises both branches;
        # that is a choice, not an unfinished job.
        adapter=booted.handle.adapter,
    )
    served = serve(
        product=gated,
        record=record,
        replay_writer=ReplayWriter(
            store=store, artifact_class=governance["replay_record_class"]
        ),
    )
    # --8<-- [end:record]

    # --- the OverrideBoundary: the human substitutes the shed scope -----------
    # The agent's shed determination crosses a typed boundary where the shift
    # supervisor substitutes it. Original and substitute are BOTH artifact
    # values; both must land in the replay record (§8.2; T-07-16).
    override_doc = human["override"]
    override_boundary: OverrideBoundary[ShedDetermination] = OverrideBoundary(
        transport=transport,
        audit=audit,
        clock=clock,
        control_plane=registry,
        hitl_policy_key=registration["hitl_policy_key"],
        identity_provider=provider,
        trusted_keys=trusted,
    )
    override_original = ShedDetermination(**override_doc["original"])
    override_substitute = ShedDetermination(**override_doc["substitute"])
    proposed = override_boundary.propose(
        tenant=booted.tenant_id,
        event_key=override_doc["event"]["event_key"],
        workflow_state_ref=override_doc["event"]["workflow_state_ref"],
        original=override_original,
    )
    overrider = override_doc["overrider"]
    overrider_binding = HumanPrincipalBinding(
        approver=ApproverIdentity(**overrider["identity"]),
        authentication=AuthenticationContext(**overrider["authentication"]),
        action_time=datetime.fromisoformat(overrider["action_time"]),
        # The proposal-time content hash is what the overrider's binding must
        # echo (T-07-17/T-07-39 TOCTOU doctrine).
        product_content_hash=proposed.product_content_hash,
    )
    # The artifact decides override vs confirm; the driver interprets.
    overriding = override_doc["drive"]["action"] == "override"
    resolution = override_boundary.resolve(
        tenant=booted.tenant_id,
        event_key=proposed.event_key,
        principal=overrider_binding,
        override=override_substitute if overriding else None,
        signed_binding=sign_principal_binding(
            overrider_binding, provider=provider, key_id=key_id
        ),
    )

    # The override decision's OWN five-dimension record lands in the same store:
    # dimension 2 carries the override block verbatim. Its bindings are selected
    # here too, from the same pin, by the same explicit lookup.
    override_record = build_replay_record(
        execution=execution,
        product=gated.product,
        perspective=perspective,
        policy_bindings=(
            PolicyBinding(key="policy-bundle", version=policy_version),
        ),
        assembly_mode=declared.assembly_mode,
        recorded_at=now,
        agent_conditioning=conditioning,
        hitl_actions=resolution.hitl_actions_block,
        workflow_step_sequence=outcome.step_sequence_block,
        # The override decision ran against the same fabric, so it pins the
        # same adapter. Read from the pin again rather than reused from above:
        # the pin is a fact about the boot, not a local the driver carries.
        adapter=booted.handle.adapter,
    )
    override_served = serve(
        product=gated,
        record=override_record,
        replay_writer=ReplayWriter(
            store=store, artifact_class=governance["replay_record_class"]
        ),
    )

    # The artifacts a forensic replay resolves land in the SAME store, at exact
    # content-addressed versions (CLAUDE.md §7.4; D-IMPL-26/27).
    store.put(
        tenant_id=booted.tenant_id,
        artifact_class=probes["agent_definition_class"],
        name=definition.name,
        artifact=definition,
    )
    prompt_name = parse_artifact_uri(definition.instruction_bindings[0].prompt)
    store.put(
        tenant_id=booted.tenant_id,
        artifact_class=prompt_name.artifact_class,
        name=prompt_name.name,
        artifact=prompt,
    )
    store.put(
        tenant_id=booted.tenant_id,
        artifact_class=probes["skill_grant_class"],
        name=probes["skill_grant_name"],
        artifact=grant,
    )

    environment = GridReplayEnvironment(
        declared=declared,
        requirements=requirements,
        governance=governance,
        parameters=parameters,
        pins=booted.pins,
        policy_bundle_key="policy-bundle",
        reader=booted.handle.reader,
        tenant_id=booted.tenant_id,
        boundary=boundary,
        now=now,
    )

    # --8<-- [start:replay-reproduce]
    # --- exact reproduction (whitepaper §7.10) --------------------------------
    # From the record address alone. The engine re-resolves the graph snapshot,
    # the plan, and the operator chain, and VERIFIES each against the record
    # rather than trusting the environment that offered them.
    outcome_replay = replay(
        record_address=served.replay_ref.content_address,
        store=store,
        reader=booted.handle.reader,
        control_plane=registry,
        environment=environment,
    )
    # --8<-- [end:replay-reproduce]

    # --8<-- [start:replay-agent-version]
    # --- exact-version resolution, never a moving target ----------------------
    # Dimension 4 records WHICH agent, at which content identity, with which
    # skill-set. Each of the three resolves out of the ArtifactStore at the exact
    # version the record (or the definition it pins) names — `resolve_artifact`
    # takes a content address, so there is no "latest" to ask for.
    dimension_four = outcome_replay.record.perspective_conditioning
    resolved_definition = resolve_artifact(
        store=store,
        content_address=dimension_four.agent_definition_hash,
        contract=AgentDefinition,
    )
    pinned_prompt = parse_artifact_uri(
        resolved_definition.instruction_bindings[0].prompt
    )
    (prompt_address,) = store.versions(
        tenant_id=booted.tenant_id,
        artifact_class=pinned_prompt.artifact_class,
        name=pinned_prompt.name,
    )
    resolved_prompt = resolve_artifact(
        store=store, content_address=prompt_address, contract=PromptArtifact
    )
    (grant_address,) = store.versions(
        tenant_id=booted.tenant_id,
        artifact_class=probes["skill_grant_class"],
        name=probes["skill_grant_name"],
    )
    resolved_grant = resolve_artifact(
        store=store, content_address=grant_address, contract=SkillGrant
    )
    # --8<-- [end:replay-agent-version]

    # The override decision's record replays the same way, out of the same store.
    override_replay = replay(
        record_address=override_served.replay_ref.content_address,
        store=store,
        reader=booted.handle.reader,
        control_plane=registry,
        environment=environment,
    )

    # --8<-- [start:replay-version-sensitivity]
    # --- the version-sensitivity probe, prepared -----------------------------
    # A COPY of the record — never the canonical one — with its recorded
    # policy-bundle version bumped to one the Control Plane never registered. The
    # canonical record must stay intact: it is the thing the reproduction above
    # exists to reproduce.
    resolved = outcome_replay.record
    mutated = resolved.model_copy(
        update={
            "policy_bindings": resolved.policy_bindings.model_copy(
                update={
                    "bindings": (
                        resolved.policy_bindings.bindings[0].model_copy(
                            update={
                                "version": probes["unregistered_policy_version"]
                            }
                        ),
                    )
                    + resolved.policy_bindings.bindings[1:]
                }
            )
        }
    )
    mutated_ref = store.put(
        tenant_id=booted.tenant_id,
        artifact_class=governance["replay_record_class"],
        name=probes["mutated_record_name"],
        artifact=mutated,
    )
    # --8<-- [end:replay-version-sensitivity]

    return ReplayDemonstration(
        booted=booted,
        tenant_id=booted.tenant_id,
        artifacts=booted.artifacts,
        registry=registry,
        audit=audit,
        store=store,
        environment=environment,
        product=gated.product,
        operators_invoked=execution.operators_invoked,
        record=record,
        served=served,
        policy_version=policy_version,
        definition=definition,
        definition_version=definition_version,
        prompt=prompt,
        grant=grant,
        granted_address=granted_address,
        grant_set_hash=in_force,
        skill_output=dict(invocation.output),
        consumed=consumed,
        suspended_gate=suspended.gate,
        suspended_state_hash=suspended_state_hash,
        terminal_state=outcome.terminal_state,
        submission=submission,
        identity_provider=provider,
        trusted_keys=trusted,
        approver_client_id=active["client_id"],
        authz_refusal_status=authz_refused.status_code,
        authz_refusal_code=authz_refused.json()["detail"]["error_code"],
        authz_refused_client_id=outsider["client_id"],
        scope_mapping_version=scope_mapping_version,
        reproduced=outcome_replay.product,
        reproduced_record=resolved,
        reproduced_address=outcome_replay.product_content_address,
        resolved_definition=resolved_definition,
        resolved_prompt=resolved_prompt,
        resolved_prompt_pinned_version=pinned_prompt.artifact_version,
        resolved_grant=resolved_grant,
        agent_definition_class=probes["agent_definition_class"],
        override_record=override_record,
        override_served=override_served,
        override_resolution=resolution,
        override_original=override_original,
        override_final=override_substitute if overriding else override_original,
        override_overridden=overriding,
        reproduced_override_record=override_replay.record,
        reproduced_override_product=override_replay.product,
        mutated_record_address=mutated_ref.content_address,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-decision-replay-") as scratch:
        result = run(root=Path(scratch))
        result.booted.handle.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
