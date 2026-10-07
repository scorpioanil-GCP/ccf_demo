"""The erasure door — request, human approval, then the record (SEC-009; `D-IMPL-374` (4)).

SDK-defined (CLAUDE.md §8.1/§8.2), built to design ``D-IMPL-367`` §4.1 with U9
ruled: the request/approval is a **deployment-declared** workflow — the SDK
ships no erasure workflow artifact and no approval shape — that the door
VALIDATES: every nominal path from the workflow's start to a terminal state
must cross a ``hitl-gate`` step bound to a typed ``ccf.approval-policy`` (the
factory already class-checks the policy, ``D-IMPL-366``). A workflow that can
complete without one is refused (:class:`ErasureWorkflowUngated`).

The two halves:

* :meth:`ErasureDoor.request` — under the ``Execute`` capability for the
  workflow definition: validate the declaration and judge retention and holds
  against the PINNED policy, then start the workflow with the request's
  content identity as its execution id, so the human approves exactly this
  request. Nothing is written.
* :meth:`ErasureDoor.complete` — under the ``Resume`` capability: hold the
  presented :class:`~ccf.hitl.approval_gate.GateResolution` to what the HITL
  authority path actually RECORDED for this request's suspension, re-judge
  retention (the pinned version AND the newest version under the same key, so
  a hold placed after the request still refuses), resume the engine on the
  gate's declared approve route, and only on completion file the
  :class:`~ccf.erasure.ErasureRecord` through the store's one write verb (a
  ``DerivedWrite`` under the ``Resume`` capability, which the deployment
  declares for ``ccf.erasure-record``) and append the registry mirror.

**The erase capability (ruling 3; design §4.1).** Both halves also require an
``Authorized[ArtifactErase]`` minted by a door from an authorizer's allow for
exactly ``"<subject_class>/<request_id>"``; general workflow
``Execute``/``Resume`` cannot stand in for it — the parameter is required by
the signature and a wrong-kind or retargeted capability dies in ``verify`` as
``CapabilityBypassError`` — and the record's ``authorizing_decision_id``
is that erase decision's id. No un-erasure verb exists (U6).

Algorithmic module (CINV-03): the clock is injected.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime

from ccf.artifacts.protocol import (
    ArtifactStoreError,
    ArtifactStoreProtocol,
    DerivedWrite,
    parse_artifact_uri,
)
from ccf.authz.capability import (
    ArtifactErase,
    Authorized,
    CompositionRegister,
    Execute,
    Resume,
    verify,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.resolution import resolve_pinned
from ccf.controlplane.state import state_key
from ccf.erasure.contracts import (
    ERASURE_RECORD_CLASS,
    ErasedAddress,
    ErasureRecord,
    ErasureRequest,
    ErasureSubjectClass,
    ErasureSubjectDeclaration,
    RetentionDecision,
    RetentionHoldPolicy,
    judge_retention,
)
from ccf.erasure.index import (
    ErasureIndexEntry,
    append_to_erasure_index,
    erasure_index_key,
)
from ccf.hitl.approval_gate import GATE_APPROVE, GATE_EVENT_CLASS, GateResolution
from ccf.hitl.transport import HITLTransportProtocol
from ccf.workflow.definitions import WORKFLOW_FAILED_STATE
from ccf.workflow.factory import Workflow, WorkflowFactory
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord
from ccf_runtime.workflow.engine import (
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowSuspended,
)

__ccf_mode__ = "algorithmic"

__all__ = ["ErasureDoor", "ErasureRefused", "ErasureWorkflowUngated"]


class ErasureRefused(PermissionError):
    """The door refused a request or a completion, by name; nothing was written (SEC-009; `D-IMPL-374` (4)).

    Attributes:
        reason_code: Mechanism vocabulary for the refusal.
        decision: The retention judgment, when the refusal is one (G7's
            structured audit answer); ``None`` otherwise.
    """

    def __init__(self, message: str, *, reason_code: str, decision: RetentionDecision | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.decision = decision


class ErasureWorkflowUngated(ValueError):
    """The deployment's erasure workflow can complete without a typed approval gate (U9; SEC-009, `D-IMPL-374` (4))."""


def _document_has(document: object, path: str) -> bool:
    node = document
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


class ErasureDoor:
    """The governed door an erasure record is written through — and the only one (SEC-009; `D-IMPL-374` (4)).

    Args:
        engine: The workflow engine the request's workflow runs on.
        factory: The only construction path to a workflow handle.
        control_plane: Where the declaration and the retention policy resolve
            at their pinned versions, and where the mirror is appended.
        transport: The HITL authority path a presented approval is held to.
        store: The artifact store the record is filed through.
        clock: The injected fabric clock (``erased_at`` and the judgment's now).
        index_authorities: One composition-minted ``Register`` per tenant, for
            exactly :func:`~ccf.erasure.erasure_index_key` (``D-IMPL-354``).

    Raises:
        ccf.authz.capability.CapabilityBypassError: an index authority is not
            a genuine ``Register`` for its tenant's mirror key.
        ValueError: none was handed in, or two name one tenant.
    """

    def __init__(
        self,
        *,
        engine: WorkflowEngine,
        factory: WorkflowFactory,
        control_plane: ControlPlaneRegistry,
        transport: HITLTransportProtocol,
        store: ArtifactStoreProtocol,
        clock: Callable[[], datetime],
        index_authorities: tuple[Authorized[CompositionRegister], ...],
    ) -> None:
        held: dict[str, Authorized[CompositionRegister]] = {}
        for authorized in index_authorities:
            tenant = getattr(authorized, "tenant", None)
            expected = erasure_index_key(tenant) if isinstance(tenant, str) and tenant else ""
            verify(authorized, kind=CompositionRegister, resource=expected)
            if authorized.tenant in held:
                raise ValueError(f"two index authorities name tenant {authorized.tenant!r} (SEC-009)")
            held[authorized.tenant] = authorized
        if not held:
            raise ValueError("the erasure door holds no index authority for any tenant (SEC-009)")
        self._engine = engine
        self._factory = factory
        self._control_plane = control_plane
        self._transport = transport
        self._store = store
        self._clock = clock
        self._index_authorities = held

    # -- the two halves -------------------------------------------------------

    async def request(
        self,
        authorized: Authorized[Execute],
        *,
        definition_version: str,
        request: ErasureRequest,
        erase: Authorized[ArtifactErase],
    ) -> WorkflowSuspended:
        """Judge ``request`` and start its approval workflow; write nothing.

        Raises:
            ErasureWorkflowUngated: the workflow can complete without a gate.
            ErasureRefused: tenant, declaration, retention or hold refusal; or
                the workflow did not suspend on its gate.
        """
        workflow = self._factory.construct(authorized, definition_version=definition_version)
        self._admit(authorized.tenant, workflow, request, latest=False, erase=erase)
        outcome = await self._engine.execute(authorized, workflow, execution_id=request.request_id)
        if not isinstance(outcome, WorkflowSuspended):
            raise ErasureRefused(
                f"the erasure workflow did not suspend on an approval gate ({type(outcome).__name__});"
                " an erasure is requested, then approved by a human (SEC-009; D-IMPL-367 §4.1)",
                reason_code="workflow-not-suspended",
            )
        return outcome

    async def complete(
        self,
        authorized: Authorized[Resume],
        *,
        definition_version: str,
        request: ErasureRequest,
        resolution: GateResolution,
        erase: Authorized[ArtifactErase],
    ) -> ErasureRecord | WorkflowSuspended:
        """Resume on a RECORDED approval and, on completion, write the erasure record.

        Returns the record, or the next suspension when the deployment's
        workflow declares a further gate.

        Raises:
            ErasureWorkflowUngated: the workflow can complete without a gate.
            ErasureRefused: any refusal; nothing is written.
        """
        workflow = self._factory.construct(authorized, definition_version=definition_version)
        tenant = authorized.tenant
        subject, decision = self._admit(tenant, workflow, request, latest=True, erase=erase)
        event = resolution.record.event
        submission = resolution.record.submission
        suspension = state_key(tenant=tenant, record_id=request.request_id)
        # I2 (fix round 1): the FABRIC's own record of this suspension — the
        # engine-written state — not anything the caller presents.
        state = self._control_plane.state_store.get(WORKFLOW_STATE, suspension)
        gate = state.current_state if isinstance(state, WorkflowStateRecord) else ""
        recorded_submission = next(
            (s for s in self._transport.submissions(tenant=tenant) if s == submission),
            None,
        )
        recorded = (
            isinstance(state, WorkflowStateRecord)
            and state.status == "suspended"
            and resolution.record.approved
            and recorded_submission is not None
            and recorded_submission.action == GATE_APPROVE
            and recorded_submission.event_key == f"{suspension}/{gate}"
            and recorded_submission.principal.product_content_hash == content_hash(state)
            and event.event_key == recorded_submission.event_key
            and event.event_class == GATE_EVENT_CLASS
            and event.tenant == tenant
            and event.workflow_state_ref == suspension
            and gate in workflow.definition.gate_policies
            and event.policy_ref == workflow.definition.gate_policies[gate]
        )
        if not recorded or recorded_submission is None or not isinstance(state, WorkflowStateRecord):
            raise ErasureRefused(
                "the presented approval is not one the HITL authority path recorded for"
                " this request's suspension; an erasure is written only on a recorded"
                " human approval (SEC-009; D-IMPL-367 §4.1; D-IMPL-366)",
                reason_code="approval-not-recorded",
            )
        # The requester is the starter the ENGINE recorded on the suspended
        # state, and the actor is the approver on the transport's RECORDED
        # submission — never the presented event (I2; probe P3).
        requested_by = state.started_by
        if requested_by is None:
            raise ErasureRefused(
                "the suspended execution records no starter (SEC-009; D-IMPL-366 G1)",
                reason_code="requester-unrecorded",
            )
        actor = recorded_submission.principal.approver
        route = workflow.definition.gate_routes.get(gate, {}).get(GATE_APPROVE)
        if route is None:
            raise ErasureRefused(
                f"gate {gate!r} declares no approve route (SEC-009)", reason_code="approval-route-undeclared"
            )
        outcome = await self._engine.resume(
            authorized, workflow, execution_id=request.request_id, decision=route
        )
        if isinstance(outcome, WorkflowSuspended):
            return outcome
        if not isinstance(outcome, WorkflowCompleted) or outcome.terminal_state == WORKFLOW_FAILED_STATE:
            raise ErasureRefused(
                f"the erasure workflow did not complete ({outcome!r})"[:400],
                reason_code="workflow-refused",
            )
        erased_at = self._clock()
        addresses = tuple(
            ErasedAddress(
                content_address=address.content_address,
                artifact_class=address.artifact_class,
                key_paths=subject.key_paths,
                matched=self._matched(address.content_address, subject),
            )
            for address in sorted(request.addresses, key=lambda a: a.content_address)
        )
        record_id = content_hash(
            {
                "tenant_id": tenant,
                "subject_ref": request.subject_ref,
                "addresses": [a.content_address for a in addresses],
                "erased_at": erased_at.isoformat(),
            }
        )
        record = ErasureRecord(
            tenant_id=tenant,
            record_id=record_id,
            subject_class=request.subject_class,
            subject_ref=request.subject_ref,
            addresses=addresses,
            erased_at=erased_at,
            actor=actor,
            requested_by=requested_by,
            # The authorizer's allow for the ERASE door kind (design §2.3).
            authorizing_decision_id=erase.decision_id,
            approval_policy_ref=str(event.policy_ref),
            retention_decision=decision,
            reason=request.reason,
            legal_basis=request.legal_basis,
        )
        filed = self._store.put(
            authorized,
            DerivedWrite(artifact_class=ERASURE_RECORD_CLASS, name=record_id, artifact=record),
        )
        append_to_erasure_index(
            self._control_plane,
            self._index_authorities[tenant],
            tuple(
                ErasureIndexEntry(
                    content_address=a.content_address,
                    erasure_record_address=filed.content_address,
                    reason=request.reason,
                    erased_at=erased_at,
                )
                for a in addresses
            ),
        )
        return record

    # -- the shared admission ---------------------------------------------------

    def _admit(
        self,
        tenant: str,
        workflow: Workflow,
        request: ErasureRequest,
        *,
        latest: bool,
        erase: Authorized[ArtifactErase],
    ) -> tuple[ErasureSubjectClass, RetentionDecision]:
        # Ruling 3 (`D-IMPL-374` (4); design §4.1): the distinct erase kind, for
        # exactly this request, IN ADDITION to the recorded approval. Required by
        # the signature (D-IMPL-353 §4: no authority parameter may be omitted);
        # a general Execute/Resume, or an erase capability for another request,
        # is refused by name here — CapabilityBypassError.
        verify(erase, kind=ArtifactErase, resource=f"{request.subject_class}/{request.request_id}")
        if erase.tenant != tenant:
            raise ErasureRefused(
                f"the erase capability is for tenant {erase.tenant!r}, not {tenant!r}"
                " (SEC-009; D-IMPL-353 §1.3)",
                reason_code="tenant-mismatch",
            )
        if request.tenant_id != tenant:
            raise ErasureRefused(
                f"the request names tenant {request.tenant_id!r} and the capability is for"
                f" {tenant!r} (SEC-009; D-IMPL-353 §1.3)",
                reason_code="tenant-mismatch",
            )
        if tenant not in self._index_authorities:
            raise ErasureRefused(
                f"this door holds no index authority for tenant {tenant!r} (SEC-009; D-IMPL-354)",
                reason_code="index-unauthorized",
            )
        self._require_gated(workflow)
        declaration = resolve_pinned(self._control_plane, request.subject_declaration_ref)
        if not isinstance(declaration, ErasureSubjectDeclaration) or declaration.tenant_id != tenant:
            raise ErasureRefused(
                f"{request.subject_declaration_ref!r} does not resolve to this tenant's"
                " subject declaration (SEC-009; D-IMPL-367 §2.1)",
                reason_code="declaration-unresolvable",
            )
        subject = declaration.subject(request.subject_class)
        if subject is None:
            raise ErasureRefused(
                f"subject class {request.subject_class!r} is not declared (SEC-009)",
                reason_code="subject-class-undeclared",
            )
        stray = sorted({a.artifact_class for a in request.addresses} - set(subject.artifact_classes))
        if stray:
            raise ErasureRefused(
                f"artifact class(es) {stray!r} are not declared to carry subject class"
                f" {subject.class_id!r} (SEC-009; D-IMPL-367 §2.1)",
                reason_code="artifact-class-undeclared",
            )
        absent = sorted(a.content_address for a in request.addresses if not self._store.exists(content_address=a.content_address))
        if absent:
            raise ErasureRefused(
                f"{len(absent)} requested address(es) hold nothing in this store (SEC-009)",
                reason_code="address-absent",
            )
        now = self._clock()
        pinned = resolve_pinned(self._control_plane, request.retention_policy_ref)
        decision = self._judge(pinned, request.retention_policy_ref, request, now)
        if latest:
            name = parse_artifact_uri(request.retention_policy_ref)
            key = f"{name.tenant_id}/{name.artifact_class}/{name.name}"
            versions = self._control_plane.versions(key)
            newest = self._control_plane.peek(key, versions[-1]) if versions else None
            if newest is not None and newest != pinned:
                semver = getattr(newest, "semver", versions[-1])
                self._judge(newest, f"{key}@{semver}", request, now)
        return subject, decision

    def _judge(self, policy: object, policy_ref: str, request: ErasureRequest, now: datetime) -> RetentionDecision:
        if not isinstance(policy, RetentionHoldPolicy) or policy.tenant_id != request.tenant_id:
            decision = RetentionDecision(policy_ref=policy_ref, verdict="refuse", reason_code="policy-unresolvable")
        else:
            decision = judge_retention(policy, policy_ref=policy_ref, request=request, now=now)
        if decision.verdict != "admit":
            raise ErasureRefused(
                f"retention refuses this erasure: {decision.reason_code}"
                + (f" (hold {decision.hold_id})" if decision.hold_id else "")
                + " (SEC-009; D-IMPL-367 §4.2)",
                reason_code=decision.reason_code,
                decision=decision,
            )
        return decision

    @staticmethod
    def _require_gated(workflow: Workflow) -> None:
        """Every nominal path from start to a terminal crosses a policy-bound gate (U9)."""
        definition = workflow.definition
        gated = set(definition.gate_policies)
        edges: dict[str, set[str]] = {}
        for transition in definition.transitions:
            edges.setdefault(transition.source, set()).add(transition.target)
        terminals = definition.effective_terminal_states - {WORKFLOW_FAILED_STATE}
        frontier = [definition.start]
        seen: set[str] = set()
        while frontier:
            node = frontier.pop()
            if node in seen or node in gated:
                continue
            seen.add(node)
            if node in terminals:
                raise ErasureWorkflowUngated(
                    f"the erasure workflow {definition.name!r} reaches terminal {node!r}"
                    " without crossing a hitl-gate bound to a typed approval policy; an"
                    " erasure is approved by a human through the ApprovalGate (SEC-009;"
                    " D-IMPL-374 (4), U9; D-IMPL-366)"
                )
            frontier.extend(edges.get(node, ()))

    def _matched(self, content_address: str, subject: ErasureSubjectClass) -> bool:
        try:
            document = json.loads(self._store.get(content_address=content_address))
        except (ArtifactStoreError, KeyError, ValueError):
            return False
        return all(_document_has(document, path) for path in subject.key_paths)
