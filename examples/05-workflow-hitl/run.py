"""examples/05-workflow-hitl — auth-bound workflow + HITL gate (EXAM-06).

A multi-step banking workflow (skill node, agent node, ApprovalGate,
ExceptionEscalation path) constructed through the WorkflowFactory from
definition artifacts, executed by the WorkflowEngine, and approved through
the HARDENED Experience-Layer door: ``create_app(auth=BearerTokenAuth(...))``
with a grant-derived principal (D-IMPL-67) and a REQUIRED D-16 signed
principal binding (08-03). This is the live leg of the D-14 absorption:
the auth-bound HITL surface demonstrated end to end, not just tested.

What this demonstrates, as assertions:

* **Suspend/resume with persisted state (§8.1).** The workflow suspends at
  the ApprovalGate with a persisted ``WorkflowStateRecord``; a declared
  decision resumes it to its declared terminal.
* **The auth-bound door (D-IMPL-66(a)/67; D-16).** Submissions travel
  ``POST /hitl/actions`` with a bearer token; the audited principal is
  DERIVED from the verified ``TokenGrant``, never taken from the caller;
  the D-16 policy in force requires a ``SignedPrincipalBinding`` produced
  via ``sign_principal_binding`` and verified at the transport authority
  path before anything lands.
* **Typed refusals, fail closed.** An unauthenticated request and a
  request bearing the EXPIRED token from the token-table artifact refuse
  401 with ``ERROR_UNAUTHENTICATED``; an unsigned submission refuses 403
  with ``ERROR_SIGNED_BINDING_REQUIRED``; a tampered signature refuses 403
  with ``ERROR_SIGNED_BINDING_INVALID`` — all imported constants, never
  parsed prose, and nothing lands on the transport for any refusal.
* **Replay by construction (§8.2; whitepaper §7.10.1).** Dimension 2
  records the human action verbatim — the grant-derived approver, the
  signed binding, and the content hash of exactly what the approver saw —
  and dimension 5 records the engine's step-sequence block byte-for-byte.
* **The ExceptionEscalation path (§8.1; D-IMPL-61).** A failing node
  routes to its declared exception handler as a first-class recorded,
  audited transition.

Every domain value — tenant, steps, routing, policy, approver, tokens,
outputs, instants — is loaded from ``artifacts/*.yaml``; deleting the
artifacts leaves this driver nothing to run (CLAUDE.md §6.4).

Run it: ``make example-05``. Exit 0 means every assertion held.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import yaml
from joserfc.jwk import ECKey

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.hitl.approval_gate import HitlActionRecord
from ccf.hitl.identity_binding import sign_principal_binding
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
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    TASK_DEFINITION,
    AgentDefinition,
    PromptArtifact,
    TaskDefinition,
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
    PerspectiveConditioning,
    PolicyBinding,
    build_replay_record,
)
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import ApprovalOutcome, GrantLedger, SkillGrant
from ccf.workflow.definitions import WORKFLOW_DEFINITION, WorkflowDefinition
from ccf.workflow.factory import WorkflowFactory
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.auth import BearerTokenAuth
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_SIGNED_BINDING_INVALID,
    ERROR_SIGNED_BINDING_REQUIRED,
    ERROR_UNAUTHENTICATED,
)
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


def _load(name: str) -> Any:
    return yaml.safe_load((ARTIFACTS / name).read_text(encoding="utf-8"))


def _instant(value: object) -> datetime:
    # PyYAML resolves `...Z` timestamps to naive datetimes; the canonical
    # serializer refuses naive datetimes (D-IMPL-38).
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _ticking_clock(base: datetime) -> Any:
    # Deterministic injected clock seeded from the artifact-declared base
    # instant — no wall clock anywhere in this driver.
    state = {"now": base}

    def clock() -> datetime:
        state["now"] += timedelta(seconds=1)
        return state["now"]

    return clock


class ArtifactTokenSource:
    # The deployment's TokenSourceProtocol implementation: the recognised
    # tokens and their lifecycle status live in the token-table artifact,
    # never in code. Only ACTIVE entries yield a grant; the expired entry
    # is refused exactly as an unknown token is (fail closed).

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
    # Injected node bindings — the deployment's composition seam. Outputs
    # come from the artifact; `failing` names steps whose invocation raises,
    # driving the declared exception path without any routing value in code.

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
    # DebtAssessmentBinding over artifact-declared nominal factors
    # (D-IMPL-65 composition-root wiring; INV-CH7-68).

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


def _register_closure(registry: ControlPlaneRegistry) -> tuple[str, str]:
    """Register every artifact the workflow's refs resolve to; return the
    workflow definition's (key, version)."""
    agent_doc = _load("agent.yaml")
    prompt_doc = _load("prompt.yaml")
    task_doc = _load("task.yaml")
    workflow_doc = _load("workflow.yaml")

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

    agent = parse_artifact(agent_doc["agent_definition"], AGENT_DEFINITION)
    assert isinstance(agent, AgentDefinition)
    registry.register_versioned(
        task_doc["keys"]["referenced_agent_definition"],
        agent,
        AGENT_DEFINITION,
    )

    task = parse_artifact(task_doc["task_definition"], TASK_DEFINITION)
    assert isinstance(task, TaskDefinition)
    registry.register_versioned(
        workflow_doc["keys"]["task_definition"], task, TASK_DEFINITION
    )

    definition = parse_artifact(
        workflow_doc["workflow_definition"], WORKFLOW_DEFINITION
    )
    assert isinstance(definition, WorkflowDefinition)
    key = workflow_doc["keys"]["workflow_definition"]
    version = registry.register_versioned(key, definition, WORKFLOW_DEFINITION)
    assert isinstance(version, str)
    return key, version


def _replay_execution(replay_doc: Mapping[str, Any]) -> ExecutionResult:
    """A fixture-shaped execution threading the artifact-declared decision
    values into the record builder (the test_slice shape — this example's
    subject is the workflow/HITL dimensions, not the L1-L6 pipeline)."""
    boundary = _instant(replay_doc["temporal_boundary"])
    return ExecutionResult(
        plan_id=replay_doc["plan_id"],
        operators_invoked=frozenset({replay_doc["operator_key"]}),
        steps=(
            ExecutionStep(
                operator_key=replay_doc["operator_key"],
                category=replay_doc["operator_category"],
                parameter_hash=replay_doc["operator_parameter_hash"],
            ),
        ),
        provenance=None,
        projection=ProjectionOutput(
            plan_id=replay_doc["plan_id"], payload=dict(replay_doc["payload"])
        ),
        view=GraphView(
            tenant_id="sterling-mutual"
            if "tenant" not in replay_doc
            else replay_doc["tenant"],
            as_of=boundary,
        ),
    )


def main() -> int:
    hitl_doc = _load("hitl.yaml")
    workflow_doc = _load("workflow.yaml")
    tokens_doc = _load("tokens.yaml")

    tenant: str = workflow_doc["workflow_definition"]["tenant"]
    drive = hitl_doc["drive"]
    clock = _ticking_clock(_instant(hitl_doc["clock"]["base"]))

    with tempfile.TemporaryDirectory(prefix="ccf-workflow-hitl-") as scratch:
        root = Path(scratch)

        # --- Control Plane: full closure + the D-16 HITL policy -------------
        audit = AuditLog()
        registry = ControlPlaneRegistry(clock=clock, audit_log=audit)
        workflow_key, workflow_version = _register_closure(registry)
        policy = parse_artifact(hitl_doc["hitl_policy"], HITL_POLICY)
        assert isinstance(policy, HitlPolicy)
        assert policy.signed_binding_required is True
        registry.register_typed(
            hitl_doc["keys"]["hitl_policy"], policy, HITL_POLICY
        )

        # --- approver signing key (D-IMPL-21 reference impl #2) -------------
        # Key MATERIAL is generated in scratch space at run time; only the
        # key's NAME is artifact content.
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
        trusted: dict[str, JsonWebKey] = {
            key_id: key.as_dict(private=False)
        }

        # --- the ONE transport: policy-enforcing authority path (D-16) ------
        transport = InMemoryHitlTransport(
            control_plane=registry,
            hitl_policy_key=hitl_doc["keys"]["hitl_policy"],
            identity_provider=provider,
            trusted_keys=trusted,
        )
        bindings = NodeBindings(hitl_doc["node_outputs"])
        engine = WorkflowEngine(
            control_plane=registry,
            artifact_store=FileArtifactStore(root=root / "artifacts"),
            hitl_transport=transport,
            skill_binding=bindings,
            agent_binding=bindings,
            clock=clock,
            debt_binding=DeclaredDebt(hitl_doc["debt_factors"]),
        )
        factory = WorkflowFactory(control_plane=registry)
        workflow = factory.construct(
            definition_key=workflow_key, definition_version=workflow_version
        )

        # --- execute: the workflow suspends at the ApprovalGate -------------
        execution_id: str = drive["approval_execution_id"]
        suspended = asyncio.run(
            engine.execute(workflow, execution_id=execution_id)
        )
        assert isinstance(suspended, WorkflowSuspended), suspended
        assert suspended.gate == drive["expected_gate"]
        state_key = f"{tenant}/{execution_id}"
        record = registry.state_store.get(WORKFLOW_STATE, state_key)
        assert isinstance(record, WorkflowStateRecord)
        assert record.status == "suspended"
        assert record.current_state == drive["expected_gate"]

        # --- the hardened door: create_app(auth=BearerTokenAuth(...)) -------
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
            auth=BearerTokenAuth(
                token_source=ArtifactTokenSource(path=ARTIFACTS / "tokens.yaml")
            ),
        )
        entries = {e["status"]: e for e in tokens_doc["tokens"]}
        active = entries["active"]
        expired = entries["expired"]
        bearer = {"Authorization": f"Bearer {active['token']}"}

        # --- the queue view, through the authenticated door -----------------
        queue = _call(app, "GET", f"/hitl/queue?tenant={tenant}", headers=bearer)
        assert queue.status_code == 200, queue.text
        (pending_doc,) = queue.json()
        pending = PendingHitlEvent.model_validate(pending_doc)
        assert pending.event_key == suspended.event_key
        # What the approver is shown IS the suspended state, by content hash
        # (T-07-39 TOCTOU binding).
        assert pending.product_content_hash == content_hash(record)

        # --- the approver's binding, signed (sign_principal_binding) --------
        approver = hitl_doc["approver"]
        binding = HumanPrincipalBinding(
            approver=ApproverIdentity(**approver["identity"]),
            authentication=AuthenticationContext(**approver["authentication"]),
            action_time=_instant(approver["action_time"]),
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

        # --- negative cases: every refusal typed, nothing lands -------------
        # 1. Unauthenticated: no bearer token at all.
        refused = _call(app, "POST", "/hitl/actions", json=submission_body(None))
        assert refused.status_code == 401, refused.text
        assert refused.json()["detail"]["error_code"] == ERROR_UNAUTHENTICATED

        # 2. The EXPIRED token from the token-table artifact — refused by the
        # artifact-driven source exactly like an unknown token (fail closed).
        refused = _call(
            app,
            "POST",
            "/hitl/actions",
            json=submission_body(None),
            headers={"Authorization": f"Bearer {expired['token']}"},
        )
        assert refused.status_code == 401, refused.text
        assert refused.json()["detail"]["error_code"] == ERROR_UNAUTHENTICATED

        # 3. Authenticated but UNSIGNED: the D-16 policy requires a binding.
        refused = _call(
            app, "POST", "/hitl/actions", json=submission_body(None), headers=bearer
        )
        assert refused.status_code == 403, refused.text
        assert (
            refused.json()["detail"]["error_code"]
            == ERROR_SIGNED_BINDING_REQUIRED
        )

        # 4. Authenticated with a TAMPERED signature.
        tampered = signed.model_copy(
            update={"signature": signed.signature[:-4] + "AAAA"}
        )
        refused = _call(
            app,
            "POST",
            "/hitl/actions",
            json=submission_body(tampered.model_dump(mode="json")),
            headers=bearer,
        )
        assert refused.status_code == 403, refused.text
        assert (
            refused.json()["detail"]["error_code"]
            == ERROR_SIGNED_BINDING_INVALID
        )

        # No refusal reached the authority path.
        assert transport.submissions(tenant=tenant) == ()

        # --- the valid signed submission: admitted, principal DERIVED -------
        admitted = _call(
            app,
            "POST",
            "/hitl/actions",
            json=submission_body(signed.model_dump(mode="json")),
            headers=bearer,
        )
        assert admitted.status_code == 200, admitted.text
        receipt = admitted.json()
        assert receipt["status"] == "submitted"
        (submission,) = transport.submissions(tenant=tenant)
        # The audited subject is the one the token source VERIFIED — derived
        # from the TokenGrant (D-IMPL-67), never the caller's claim.
        assert (
            submission.principal.approver.subject_id == active["client_id"]
        )
        assert submission.signed_binding == signed

        # --- resume: the human decision drives the declared terminal --------
        # The door is submit-only by ruling (D-IMPL-62): the submission above
        # IS the authority-path landing (D-16-verified), and the owning
        # composition — this driver — consumes the event and resumes.
        action_record = HitlActionRecord(
            event=pending, submission=submission, approved=True
        )
        hitl_actions_block = canonical_bytes(action_record).decode("utf-8")
        drained = transport.dequeue(tenant=tenant)
        assert drained is not None and drained.event_key == pending.event_key

        outcome = asyncio.run(
            engine.resume(
                workflow,
                execution_id=execution_id,
                decision=drive["resume_decision"],
            )
        )
        assert isinstance(outcome, WorkflowCompleted), outcome
        assert outcome.terminal_state == drive["resume_decision"]
        terminal = registry.state_store.get(WORKFLOW_STATE, state_key)
        assert isinstance(terminal, WorkflowStateRecord)
        assert terminal.status == "terminal"

        # --- replay: dimensions 2 and 5 land verbatim (§7.10.1) -------------
        replay_doc = dict(hitl_doc["replay"])
        replay_doc["tenant"] = tenant
        execution = _replay_execution(replay_doc)
        boundary = _instant(replay_doc["temporal_boundary"])
        product = ContextProductContract(
            schema_name=replay_doc["schema_name"],
            schema_version=replay_doc["schema_version"],
            plan_id=replay_doc["plan_id"],
            tenant_id=tenant,
            temporal_boundary=boundary,
            expires_at=_instant(replay_doc["expires_at"]),
            ttl_anchor=replay_doc["ttl_anchor"],
            lineage=ProductLineage(
                operators_invoked=frozenset({replay_doc["operator_key"]}),
                policy_bundle_versions=frozenset(
                    {replay_doc["policy_binding_version"]}
                ),
                graph_snapshot_at=boundary,
            ),
            payload=dict(replay_doc["payload"]),
        )
        perspective = Perspective(
            principal_id=replay_doc["perspective"]["principal_id"],
            role=replay_doc["perspective"]["role"],
        )
        replay = build_replay_record(
            execution=execution,
            product=product,
            perspective=perspective,
            policy_bindings=(
                PolicyBinding(
                    key=replay_doc["policy_binding_key"],
                    version=replay_doc["policy_binding_version"],
                ),
            ),
            assembly_mode=replay_doc["assembly_mode"],
            recorded_at=_instant(replay_doc["recorded_at"]),
            agent_conditioning=PerspectiveConditioning(
                principal_id=replay_doc["perspective"]["principal_id"],
                role=replay_doc["perspective"]["role"],
                delegation_chain=outcome.delegation_chain,
            ),
            hitl_actions=hitl_actions_block,
            workflow_step_sequence=outcome.step_sequence_block,
        )
        # Dimension 2: the human action, byte-for-byte — grant-derived
        # approver, the signed binding, and the hash of what they saw.
        assert replay.policy_bindings.hitl_actions == hitl_actions_block
        block = replay.policy_bindings.hitl_actions
        assert active["client_id"] in block
        assert pending.product_content_hash in block
        assert signed.signature in block
        restored = HitlActionRecord.model_validate_json(block)
        assert restored.submission.signed_binding == signed
        # Dimension 5: the engine's step-sequence block, byte-for-byte.
        assert (
            replay.content_generation_path.workflow_step_sequence
            == outcome.step_sequence_block
        )
        # Dimension 4: the delegation chain names the workflow execution.
        assert (
            replay.perspective_conditioning.delegation_chain[0]
            == f"workflow:{state_key}"
        )

        # --- the ExceptionEscalation path (D-IMPL-61) ------------------------
        escalation_id: str = drive["escalation_execution_id"]
        bindings.failing = frozenset({drive["failing_step"]})
        routed = asyncio.run(engine.execute(workflow, execution_id=escalation_id))
        bindings.failing = frozenset()
        assert isinstance(routed, WorkflowExceptionRouted), routed
        assert routed.node == drive["failing_step"]
        declared_handler = workflow_doc["workflow_definition"][
            "exception_refs"
        ][drive["failing_step"]]
        assert routed.handler_ref == declared_handler
        escalated = registry.state_store.get(
            WORKFLOW_STATE, f"{tenant}/{escalation_id}"
        )
        assert isinstance(escalated, WorkflowStateRecord)
        assert escalated.trace[-1].kind == "exception"
        assert escalated.trace[-1].target == declared_handler
        exception_events = [
            event
            for event in audit.events()
            if event.action == "workflow_exception"
        ]
        assert len(exception_events) == 1 and exception_events[0].resolved

        print("examples/05-workflow-hitl: OK")
        print(f"  tenant                 {tenant}")
        print(f"  workflow               {workflow_doc['workflow_definition']['name']}")
        print(f"  suspended at gate      {suspended.gate}")
        print(f"  approver (derived)     {submission.principal.approver.subject_id}")
        print(f"  terminal state         {outcome.terminal_state}")
        print(f"  escalation handler     {routed.handler_ref}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
