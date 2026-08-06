"""examples/05-workflow-hitl — auth-bound workflow + three HITL primitives (EXAM-06).

A multi-step banking workflow (skill node, agent node, ApprovalGate,
ExceptionEscalation path) constructed through the ``WorkflowFactory`` from
definition artifacts, executed by the ``WorkflowEngine``, and approved through
the hardened Experience-Layer door: ``create_app(auth=BearerTokenAuth(...))``
with a grant-derived principal (D-IMPL-67) and a REQUIRED D-16 signed principal
binding (08-03). A ``ReviewQueue`` then holds the generated briefing until a
second named human releases it.

This file is the **call spine** an adopter would actually write. It asserts
nothing and prints nothing: its assertions live in
``tests/examples/test_workflow_hitl_output.py``, where they are run by ``pytest``
and can fail a build (D-09). ``make example-05`` running clean means the spine
executed; the test module is what says it was *right*.

The audit-by-construction commitment (CLAUDE.md §8.2) is what this example
exists to demonstrate: **there is no path through the HITL surface that produces
an unrecorded human action.** Every approval, every review release, every
refusal, and every exception transition lands in the Control Plane audit log and
on the five-dimension Decision Replay record. The spine below never opts in to
that recording, because there is no opt-in — which is exactly the point.

What stays in adopter hands, and why
------------------------------------

**Four SDK classes this example keeps at the call site, and two the manifest
genuinely cannot address.** ``ccf.agent-definition``, ``ccf.prompt-artifact``,
``ccf.task-definition`` and ``ccf.workflow-definition`` are author-versioned:
they register through
:meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_versioned`, which
holds the author's ``artifact_version`` claim against content identity (the D-05
bump check). A manifest *may* name them, as ``registration: versioned``, and
:func:`~ccf.deployment.manifest.load_and_boot` then registers them through that
same path; declaring ``typed`` for one is refused at preflight (D-IMPL-85),
because ``register_typed`` runs no bump check. They stay here so the four
``register_versioned`` calls remain visible as the thing being taught. Two more,
``ccf.hitl-policy`` and ``ccf.scope-mapping``, are SDK-owned but in neither SDK
mapping, and the ``ccf.`` prefix is reserved — so a manifest entry naming either
is refused at load (D-IMPL-84), which is what keeps the transport and the
authorizer, both of which read their real contracts back off the Control Plane
by key, from being handed the open ``DeclaredArtifact`` envelope. All six are
registered here.

**The projection stage is fixture-shaped.** The fabric is real — it boots,
ingests, and the graph view below is read from it at the declared boundary — but
the operator/projection leg is declared in ``replay-values.yaml`` rather than
executed. This example's subject is the Orchestration Layer and the HITL
primitives; ``examples/00-quickstart`` and ``examples/06-decision-replay`` are
where the L1–L6 pipeline is exercised end to end.

Every domain value is loaded from ``artifacts/*.yaml`` and enumerated by
``artifacts/manifest.yaml`` (CLAUDE.md §6.4, the No-Hardcoding Rule); deleting
the artifacts leaves this driver nothing to run.

Run it: ``make example-05`` (or
``PYTHONPATH=src:runtime python examples/05-workflow-hitl/run.py``).
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
)
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.contracts.claims import LineageEntry
from ccf.controlplane.artifacts import (
    DeclaredArtifact,
    SignalBatch,
    declared_artifact_class,
    load_artifact,
)
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.hitl.approval_gate import HitlActionRecord
from ccf.hitl.identity_binding import sign_principal_binding
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.review_queue import ReviewQueue, ReviewQueueItem, ReviewResolution
from ccf.hitl.transport import (
    HITL_POLICY,
    HitlPolicy,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from ccf.peering.identity import (
    DetachedJwsIdentityProvider,
    FileBackedKeySource,
    JsonWebKey,
)
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ExecutionResult, ExecutionStep
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.record import (
    DecisionReplayRecord,
    PerspectiveConditioning,
    PolicyBinding,
    build_replay_record,
)
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import ApprovalOutcome, GrantLedger, SkillGrant
from ccf.workflow.definitions import WORKFLOW_DEFINITION
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.authz.artifact import SCOPE_MAPPING
from ccf_runtime.authz.protocol import ControlPlaneTenantAuthorizer
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.mcp.auth import TokenGrant
from ccf_runtime.mcp.egress import ProductNotServable
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowExceptionRouted,
    WorkflowSuspended,
)
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
MANIFEST = ARTIFACTS / "manifest.yaml"


def _ticking_clock(base: datetime) -> Any:
    """A monotone audit clock seeded from an artifact, never from the wall.

    Every Control Plane registration and every HITL action is stamped from it, so
    the audit sequence is a function of a declared instant rather than of when
    the example happened to run — which is what makes the run replayable at all.
    """
    state = {"now": base}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


class ArtifactTokenSource:
    # TokenSourceProtocol over the token-table artifact: only ACTIVE entries
    # yield a grant; the expired entry refuses like an unknown token (fail
    # closed). The entries arrive already parsed off `booted.artifacts`, so there
    # is no second read of the file to drift.

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
    # Injected node bindings — the deployment's composition seam. Outputs come
    # from the artifact; `failing` names steps whose invocation raises, driving
    # the declared exception path without any routing value in code.

    def __init__(self, outputs: Mapping[str, Mapping[str, str]]) -> None:
        self._outputs = outputs
        self.failing: frozenset[str] = frozenset()
        self.ran: list[str] = []

    async def _run(self, step_name: str) -> Mapping[str, str]:
        if step_name in self.failing:
            raise RuntimeError(f"step {step_name!r} failed")
        self.ran.append(step_name)
        return dict(self._outputs[step_name])

    async def run_skill(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        return await self._run(step_name)

    async def run_agent(
        self, *, tenant: str, step_name: str, ref: str
    ) -> Mapping[str, str]:
        return await self._run(step_name)


class DeclaredDebt:
    # DebtAssessmentBinding over artifact-declared nominal factors (D-IMPL-65
    # composition-root wiring; INV-CH7-68).

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
    # ApprovalSink conformance for a driver that requests no grants: a
    # consultation is a hard failure, never a silent approval.

    def decide(self, grant: SkillGrant) -> ApprovalOutcome:
        raise AssertionError("tier-2 sink consulted in a grant-free example")


def _no_product(*, tenant: str, product_class: str, version: str) -> Any:
    # This example serves no gated product through the door; the resolver
    # honestly refuses rather than fabricating one.
    raise ProductNotServable(
        f"no gate-admitted product at {tenant}/{product_class}/{version}"
    )


def _call(app: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
    # One in-process ASGI request — the app is built, never bound to a port.
    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(go())


@dataclass(frozen=True)
class WorkflowHitlDemonstration:
    """What one run of the spine produced, for a caller to inspect.

    The example returns its state rather than checking it here, so that
    ``tests/examples/test_workflow_hitl_output.py`` can hold the assertions where
    a test runner will actually run them (D-09).

    The ``booted`` fabric is returned still open — the relocated assertions read
    through its ``reader`` and its ``pins``. Its caller owns closing it.
    """

    booted: Any
    tenant_id: str
    artifacts: Mapping[str, CCFContract]
    registry: ControlPlaneRegistry
    audit: AuditLog
    transport: InMemoryHitlTransport

    # The verification material a reader of the record needs, and no more: the
    # detached-JWS provider and the PUBLIC keys.
    identity_provider: DetachedJwsIdentityProvider
    trusted_keys: Mapping[str, JsonWebKey]

    # --- suspend ----------------------------------------------------------
    suspended: WorkflowSuspended
    suspended_state: WorkflowStateRecord
    suspended_state_hash: str
    pending: PendingHitlEvent
    state_key: str

    # --- the hardened door ------------------------------------------------
    authz_refusal_status: int
    authz_refusal_code: str
    authz_refused_client_id: str
    scope_mapping_version: str
    refusals: Mapping[str, httpx.Response]
    #: What the transport held after the four refusals and BEFORE the one
    #: admission — the fail-closed evidence, captured at the only instant where
    #: it means anything.
    submissions_after_refusals: tuple[Any, ...]
    admitted: httpx.Response
    submission: Any
    signed: Any
    approver_client_id: str
    hitl_policy_signed_binding_required: bool

    # --- resume -----------------------------------------------------------
    outcome: WorkflowCompleted
    terminal_state_record: WorkflowStateRecord
    hitl_actions_block: str
    drained: Any

    # --- replay -----------------------------------------------------------
    record: DecisionReplayRecord
    review_record: DecisionReplayRecord

    # --- the review queue -------------------------------------------------
    pending_review: PendingHitlEvent
    review_item: ReviewQueueItem
    review_resolution: ReviewResolution
    queued_items: tuple[Any, ...]
    drained_items: tuple[Any, ...]
    reviewer_entry: Mapping[str, Any]

    # --- the exception path -----------------------------------------------
    routed: WorkflowExceptionRouted
    escalated_state: WorkflowStateRecord


def _replay_execution(
    values: Mapping[str, Any], *, view: Any
) -> ExecutionResult:
    """A fixture-shaped execution threading artifact-declared values into the
    record builder, over the REAL graph view this fabric resolved.

    The view is not fabricated: it is what ``booted.handle.reader.as_of`` returned
    at the declared temporal boundary, so dimension 1 of the record names a graph
    this example actually ingested into. The operator step is declared rather than
    executed, for the reason ``replay-values.yaml`` states.
    """
    return ExecutionResult(
        plan_id=values["plan_id"],
        operators_invoked=frozenset({values["operator_key"]}),
        steps=(
            ExecutionStep(
                operator_key=values["operator_key"],
                category=values["operator_category"],
                parameter_hash=values["operator_parameter_hash"],
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(
            plan_id=values["plan_id"], payload=dict(values["payload"])
        ),
        view=view,
    )


def run(*, root: Path) -> WorkflowHitlDemonstration:
    """Execute the workflow against ``root``, approve it, review it, escalate it."""
    # The audit clock must exist before the FIRST registration, and the first
    # registration happens inside `load_and_boot` — so the one instant that seeds
    # it is read here, through the SDK's own artifact loader, from the very
    # document the manifest names as `hitl-drive`. Everything after boot reads
    # that artifact off `booted.artifacts`; this is the single ordering
    # constraint the one-call boot cannot absorb.
    drive_document = (ARTIFACTS / "hitl-drive.yaml").read_text(encoding="utf-8")
    seed = cast(
        DeclaredArtifact,
        load_artifact(
            drive_document,
            declared_artifact_class(yaml.safe_load(drive_document)["class_id"]),
        ),
    )
    clock = _ticking_clock(datetime.fromisoformat(seed.declaration["clock_base"]))
    audit = AuditLog()
    registry = ControlPlaneRegistry(clock=clock, audit_log=audit)

    # --8<-- [start:boot]
    # 1. One call replaces the registration prologue and the boot: the manifest
    #    names every artifact in force, `load_and_boot` parses all of them,
    #    registers the `role: register` ones, and boots on the resulting pins.
    #    The five documents the workflow's, task's and agent's versioned-URI refs
    #    resolve against are manifest entries now, not a hand-written closure
    #    walking `referenced_artifacts:` blocks at run time.
    booted = load_and_boot(
        MANIFEST, registry=registry, database_path=str(root / "lending.sqlite3")
    )
    # --8<-- [end:boot]

    tenant: str = booted.tenant_id
    human = cast(DeclaredArtifact, booted.artifacts["hitl-drive"]).declaration
    keys = cast(DeclaredArtifact, booted.artifacts["agent-registration"]).declaration
    values = cast(DeclaredArtifact, booted.artifacts["replay-values"]).declaration
    token_entries = tuple(
        cast(DeclaredArtifact, booted.artifacts["tokens"]).declaration["tokens"]
    )
    drive = human["drive"]

    # 2. Ingest from the batch the manifest declared `role: load`. The loan the
    #    approver is deciding about is a real entity in the graph.
    events = cast(SignalBatch, booted.artifacts["events"])
    for envelope in events.envelopes:
        booted.handle.worker.ingest(envelope)

    # --8<-- [start:register-definitions]
    # 3. Six SDK classes registered here rather than through the manifest (D-05).
    #    Four are AUTHOR-VERSIONED: `register_versioned` holds the author's
    #    `artifact_version` claim against content identity. A manifest CAN name
    #    them now, as `registration: versioned`, and declaring `typed` for one is
    #    refused at preflight (D-IMPL-85); they stay here so the four-outcome D-05
    #    table is visible as the thing being taught. Two more are SDK classes
    #    deliberately not manifest-addressable — the transport and the authorizer
    #    read their real contracts back off the Control Plane by key — and naming
    #    either in a manifest is now a refusal (reserved `ccf.` prefix, D-IMPL-84).
    prompt_version = registry.register_versioned(
        keys["prompt_artifact_key"],
        load_artifact(
            (ARTIFACTS / "prompt-artifact.yaml").read_text(encoding="utf-8"),
            PROMPT_ARTIFACT,
        ),
        PROMPT_ARTIFACT,
    )
    if not isinstance(prompt_version, str):  # pragma: no cover
        raise RuntimeError(f"the prompt artifact was refused: {prompt_version!r}")
    registry.register_versioned(
        keys["agent_definition_key"],
        load_artifact(
            (ARTIFACTS / "agent-definition.yaml").read_text(encoding="utf-8"),
            AGENT_DEFINITION,
        ),
        AGENT_DEFINITION,
    )
    registry.register_versioned(
        keys["task_definition_key"],
        load_artifact(
            (ARTIFACTS / "task-definition.yaml").read_text(encoding="utf-8"),
            TASK_DEFINITION,
        ),
        TASK_DEFINITION,
    )
    workflow_key: str = keys["workflow_definition_key"]
    workflow_version = registry.register_versioned(
        workflow_key,
        load_artifact(
            (ARTIFACTS / "workflow-definition.yaml").read_text(encoding="utf-8"),
            WORKFLOW_DEFINITION,
        ),
        WORKFLOW_DEFINITION,
    )
    if not isinstance(workflow_version, str):  # pragma: no cover
        raise RuntimeError(f"the workflow definition was refused: {workflow_version!r}")
    hitl_policy = cast(
        HitlPolicy,
        load_artifact(
            (ARTIFACTS / "hitl-policy.yaml").read_text(encoding="utf-8"), HITL_POLICY
        ),
    )
    registry.register_typed(keys["hitl_policy_key"], hitl_policy, HITL_POLICY)
    scope_mapping_version = registry.register_typed(
        keys["scope_mapping_key"],
        load_artifact(
            (ARTIFACTS / "scope-mapping.yaml").read_text(encoding="utf-8"),
            SCOPE_MAPPING,
        ),
        SCOPE_MAPPING,
    )
    # --8<-- [end:register-definitions]

    # --- the approver's signing key (D-IMPL-21 reference impl #2) -------------
    # Key MATERIAL is generated in scratch space at run time; only the key's NAME
    # is artifact content.
    key_id: str = keys["signing_key_id"]
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

    # --- the ONE transport: policy-enforcing authority path (D-16) ------------
    transport = InMemoryHitlTransport(
        control_plane=registry,
        hitl_policy_key=keys["hitl_policy_key"],
        identity_provider=provider,
        trusted_keys=trusted,
    )
    bindings = NodeBindings(human["node_outputs"])
    # --8<-- [start:workflow-construct]
    engine = WorkflowEngine(
        control_plane=registry,
        artifact_store=FileArtifactStore(root=root / "artifacts"),
        hitl_transport=transport,
        skill_binding=bindings,
        agent_binding=bindings,
        clock=clock,
        debt_binding=DeclaredDebt(human["debt_factors"]),
    )
    factory = WorkflowFactory(control_plane=registry)
    workflow = factory.construct(
        definition_key=workflow_key, definition_version=workflow_version
    )
    # --8<-- [end:workflow-construct]

    # --8<-- [start:workflow-suspend]
    # --- execute: the workflow suspends at the ApprovalGate -------------------
    execution_id: str = drive["approval_execution_id"]
    suspended = asyncio.run(engine.execute(workflow, execution_id=execution_id))
    if not isinstance(suspended, WorkflowSuspended):  # pragma: no cover
        raise RuntimeError(f"the workflow did not suspend at a gate: {suspended!r}")
    state_key = f"{tenant}/{execution_id}"
    suspended_state = registry.state_store.get(WORKFLOW_STATE, state_key)
    # --8<-- [end:workflow-suspend]
    if not isinstance(suspended_state, WorkflowStateRecord):  # pragma: no cover
        raise RuntimeError("the suspended workflow left no state record")
    # The suspended state's content identity, captured HERE — before the resume
    # mutates it. This is what the approver is shown the hash of, and what their
    # signed binding must echo (T-07-39 TOCTOU doctrine); reading it after the
    # resume would hash a different state and prove nothing.
    suspended_state_hash = content_hash(suspended_state)

    # --- the hardened door: create_app(auth=BearerTokenAuth(...)) -------------
    catalog = SkillCatalog(registry)
    ledger = GrantLedger(
        control_plane=registry,
        catalog=catalog,
        sink=UnconsultedSink(),
        clock=clock,
    )
    app = create_app(
        ApiDependencies(
            control_plane=registry,
            artifact_store=engine.artifact_store,
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
            scope_mapping_key=keys["scope_mapping_key"],
            clock=clock,
        ),
    )
    entries = {entry["label"]: entry for entry in token_entries}
    active = entries["approver"]
    expired = entries["expired"]
    outsider = entries["unauthorized"]
    bearer = {"Authorization": f"Bearer {active['token']}"}

    # --- tenant authorization: the outsider token is AUTHENTICATED (its entry is
    # active) but its scope is absent from the mapping, so deny-by-default
    # refuses it with the typed 403.
    authz_refused = _call(
        app,
        "GET",
        f"/hitl/queue?tenant={tenant}",
        headers={"Authorization": f"Bearer {outsider['token']}"},
    )

    # --- the queue view, through the authenticated door -----------------------
    queue = _call(app, "GET", f"/hitl/queue?tenant={tenant}", headers=bearer)
    (pending_doc,) = queue.json()
    pending = PendingHitlEvent.model_validate(pending_doc)

    # --8<-- [start:hitl-approval]
    # --- the approver's binding, signed (sign_principal_binding) --------------
    approver = human["approver"]
    binding = HumanPrincipalBinding(
        approver=ApproverIdentity(**approver["identity"]),
        authentication=AuthenticationContext(**approver["authentication"]),
        action_time=datetime.fromisoformat(approver["action_time"]),
        # What the approver is shown IS the suspended state, by content hash
        # (T-07-39 TOCTOU binding) — echoed from the pending event, never
        # recomputed from a state the resume may since have moved.
        product_content_hash=pending.product_content_hash,
    )
    signed = sign_principal_binding(binding, provider=provider, key_id=key_id)

    def submission_body(binding_doc: Any) -> dict[str, Any]:
        return {
            "event_key": pending.event_key,
            "tenant": tenant,
            "action": drive["approval_action"],
            "principal": binding.model_dump(mode="json"),
            "annotation": None,
            "signed_binding": binding_doc,
        }
    # --8<-- [end:hitl-approval]

    # --8<-- [start:hitl-refusals]
    # --- the four negative cases: every refusal typed, nothing lands ----------
    # 1. no bearer token at all; 2. the EXPIRED token from the token-table
    # artifact, refused by the artifact-driven source exactly like an unknown one
    # (fail closed); 3. authenticated but UNSIGNED, which the D-16 policy
    # forbids; 4. authenticated with a TAMPERED signature.
    tampered = signed.model_copy(
        update={"signature": signed.signature[:-4] + "AAAA"}
    )
    refusals = {
        "unauthenticated": _call(
            app, "POST", "/hitl/actions", json=submission_body(None)
        ),
        "expired-token": _call(
            app,
            "POST",
            "/hitl/actions",
            json=submission_body(None),
            headers={"Authorization": f"Bearer {expired['token']}"},
        ),
        "unsigned": _call(
            app, "POST", "/hitl/actions", json=submission_body(None), headers=bearer
        ),
        "tampered-signature": _call(
            app,
            "POST",
            "/hitl/actions",
            json=submission_body(tampered.model_dump(mode="json")),
            headers=bearer,
        ),
    }
    # Captured HERE, before the one admission below: what the transport holds at
    # this instant is the evidence that none of the four refusals crossed.
    # Reading it after the admission — or after the review release — would count
    # legitimate landings and prove nothing.
    submissions_after_refusals = transport.submissions(tenant=tenant)
    # --8<-- [end:hitl-refusals]

    # --8<-- [start:hitl-admitted]
    # --- the valid signed submission: admitted, principal DERIVED -------------
    # The audited subject is the one the token source VERIFIED — derived from the
    # TokenGrant (D-IMPL-67), never the caller's claim about itself.
    admitted = _call(
        app,
        "POST",
        "/hitl/actions",
        json=submission_body(signed.model_dump(mode="json")),
        headers=bearer,
    )
    (submission,) = transport.submissions(tenant=tenant)
    # --8<-- [end:hitl-admitted]

    # --8<-- [start:workflow-resume]
    # --- resume: the human decision drives the declared terminal --------------
    # The door is submit-only by ruling (D-IMPL-62): the submission above IS the
    # authority-path landing (D-16-verified), and the owning composition — this
    # driver — consumes the event and resumes.
    action_record = HitlActionRecord(
        event=pending, submission=submission, approved=True
    )
    hitl_actions_block = canonical_bytes(action_record).decode("utf-8")
    drained = transport.dequeue(tenant=tenant)

    outcome = asyncio.run(
        engine.resume(
            workflow,
            execution_id=execution_id,
            decision=drive["resume_decision"],
        )
    )
    if not isinstance(outcome, WorkflowCompleted):  # pragma: no cover
        raise RuntimeError(f"the resumed workflow did not complete: {outcome!r}")
    terminal = registry.state_store.get(WORKFLOW_STATE, state_key)
    # --8<-- [end:workflow-resume]
    if not isinstance(terminal, WorkflowStateRecord):  # pragma: no cover
        raise RuntimeError("the resumed workflow left no terminal state record")

    # --8<-- [start:hitl-replay]
    # --- replay: dimensions 2, 4 and 5 land verbatim (whitepaper §7.10.1) -----
    # `policy_bindings` is built HERE, from values this deployment authored. D-06
    # keeps that SELECTION in adopter hands: dimension 2 assembled by a rule
    # nobody in the deployment wrote down is not an audit record.
    boundary = datetime.fromisoformat(values["temporal_boundary"])
    view = booted.handle.reader.as_of(tenant_id=tenant, at=boundary)
    execution = _replay_execution(values, view=view)
    product = ContextProductContract(
        schema_name=values["schema_name"],
        schema_version=values["schema_version"],
        plan_id=values["plan_id"],
        tenant_id=tenant,
        temporal_boundary=boundary,
        expires_at=datetime.fromisoformat(values["expires_at"]),
        ttl_anchor=values["ttl_anchor"],
        lineage=ProductLineage(
            operators_invoked=frozenset({values["operator_key"]}),
            policy_bundle_versions=frozenset({values["policy_binding_version"]}),
            graph_snapshot_at=boundary,
        ),
        payload=dict(values["payload"]),
    )
    perspective = Perspective(
        principal_id=values["perspective"]["principal_id"],
        role=values["perspective"]["role"],
    )
    bindings_in_force = (
        PolicyBinding(
            key=values["policy_binding_key"],
            version=values["policy_binding_version"],
        ),
    )
    conditioning = PerspectiveConditioning(
        principal_id=values["perspective"]["principal_id"],
        role=values["perspective"]["role"],
        delegation_chain=outcome.delegation_chain,
    )
    record = build_replay_record(
        execution=execution,
        product=product,
        perspective=perspective,
        policy_bindings=bindings_in_force,
        assembly_mode=values["assembly_mode"],
        recorded_at=datetime.fromisoformat(values["recorded_at"]),
        agent_conditioning=conditioning,
        # Dimension 2 carries the human action byte-for-byte; dimension 5 carries
        # the engine's own step-sequence block. Neither is summarized, and there
        # is no path that omits them (CLAUDE.md §8.2).
        hitl_actions=hitl_actions_block,
        workflow_step_sequence=outcome.step_sequence_block,
    )
    # --8<-- [end:hitl-replay]

    # --8<-- [start:review-queue]
    # --- the ReviewQueue: async review before release (§8.2; §7.10.3) ---------
    # The generated disbursement briefing is queued for asynchronous human review
    # pre-release. Every value — item, lineage anchors, reviewer identity, the
    # release/reject decision — is artifact content; this driver only interprets.
    review_doc = human["review"]
    review_queue = ReviewQueue(
        transport=transport,
        audit=audit,
        clock=clock,
        control_plane=registry,
        hitl_policy_key=keys["hitl_policy_key"],
        identity_provider=provider,
        trusted_keys=trusted,
    )
    item = ReviewQueueItem(
        output_ref=review_doc["item"]["output_ref"],
        lineage=tuple(
            LineageEntry.model_validate(entry)
            for entry in review_doc["item"]["lineage"]
        ),
    )
    pending_review = review_queue.submit_for_review(
        tenant=tenant,
        event_key=review_doc["event"]["event_key"],
        workflow_state_ref=review_doc["event"]["workflow_state_ref"],
        item=item,
    )
    queued_items = review_queue.items(tenant=tenant)

    reviewer = review_doc["reviewer"]
    reviewer_binding = HumanPrincipalBinding(
        approver=ApproverIdentity(**reviewer["identity"]),
        authentication=AuthenticationContext(**reviewer["authentication"]),
        action_time=datetime.fromisoformat(reviewer["action_time"]),
        # The submission-time content hash binds what the reviewer will see
        # (T-07-39 TOCTOU doctrine, same as the ApprovalGate leg).
        product_content_hash=pending_review.product_content_hash,
    )
    # The artifact decides release vs reject; the driver interprets, never
    # decides (§6.4).
    review_action = (
        review_queue.release
        if review_doc["drive"]["action"] == "release"
        else review_queue.reject
    )
    review_resolution = review_action(
        tenant=tenant,
        event_key=pending_review.event_key,
        principal=reviewer_binding,
        signed_binding=sign_principal_binding(
            reviewer_binding, provider=provider, key_id=key_id
        ),
    )
    if not isinstance(review_resolution, ReviewResolution):  # pragma: no cover
        raise RuntimeError(f"the review was refused: {review_resolution!r}")
    drained_items = review_queue.items(tenant=tenant)

    # The review decision's OWN five-dimension record: dimension 2 carries the
    # pre-serialized review block verbatim.
    review_record = build_replay_record(
        execution=execution,
        product=product,
        perspective=perspective,
        policy_bindings=bindings_in_force,
        assembly_mode=values["assembly_mode"],
        recorded_at=datetime.fromisoformat(values["recorded_at"]),
        agent_conditioning=conditioning,
        hitl_actions=review_resolution.hitl_actions_block,
        workflow_step_sequence=outcome.step_sequence_block,
    )
    # --8<-- [end:review-queue]

    # --8<-- [start:exception-path]
    # --- the ExceptionEscalation path (D-IMPL-61) ----------------------------
    # A second execution makes the declared step's binding raise. The engine
    # routes to the handler the workflow definition declares — a first-class,
    # traced, audited transition, not error handling glued on afterwards.
    escalation_id: str = drive["escalation_execution_id"]
    bindings.failing = frozenset({drive["failing_step"]})
    routed = asyncio.run(engine.execute(workflow, execution_id=escalation_id))
    bindings.failing = frozenset()
    if not isinstance(routed, WorkflowExceptionRouted):  # pragma: no cover
        raise RuntimeError(f"the failing step did not route: {routed!r}")
    escalated = registry.state_store.get(
        WORKFLOW_STATE, f"{tenant}/{escalation_id}"
    )
    # --8<-- [end:exception-path]
    if not isinstance(escalated, WorkflowStateRecord):  # pragma: no cover
        raise RuntimeError("the escalated execution left no state record")

    return WorkflowHitlDemonstration(
        booted=booted,
        tenant_id=tenant,
        artifacts=booted.artifacts,
        registry=registry,
        audit=audit,
        transport=transport,
        identity_provider=provider,
        trusted_keys=trusted,
        suspended=suspended,
        suspended_state=suspended_state,
        suspended_state_hash=suspended_state_hash,
        pending=pending,
        state_key=state_key,
        authz_refusal_status=authz_refused.status_code,
        authz_refusal_code=authz_refused.json()["detail"]["error_code"],
        authz_refused_client_id=outsider["client_id"],
        scope_mapping_version=scope_mapping_version,
        refusals=refusals,
        submissions_after_refusals=submissions_after_refusals,
        admitted=admitted,
        submission=submission,
        signed=signed,
        approver_client_id=active["client_id"],
        hitl_policy_signed_binding_required=hitl_policy.signed_binding_required,
        outcome=outcome,
        terminal_state_record=terminal,
        hitl_actions_block=hitl_actions_block,
        drained=drained,
        record=record,
        review_record=review_record,
        pending_review=pending_review,
        review_item=item,
        review_resolution=review_resolution,
        queued_items=queued_items,
        drained_items=drained_items,
        reviewer_entry=entries[reviewer["token_label"]],
        routed=routed,
        escalated_state=escalated,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ccf-workflow-hitl-") as scratch:
        result = run(root=Path(scratch))
        result.booted.handle.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
