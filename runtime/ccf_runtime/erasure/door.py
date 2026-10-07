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
  workflow definition AND the ``ArtifactErase`` capability for exactly this
  request: validate the declaration, VERIFY every requester-named address
  (fix round 1 — not already erased; filed under this tenant (I6); its STORED
  class, from the store's ``names_at``, is not the erasure record's and equals
  the requester's label (C2); a value at a subject key path hashes to
  ``subject_ref`` (iv); no subject in a replay-input field (§7)), judge
  retention and holds against the STORED class and the PINNED policy, then
  start the workflow with the request's content identity as its execution id.
  Nothing is written.
* :meth:`ErasureDoor.complete` — under ``Resume`` and ``ArtifactErase``: hold
  the presented :class:`~ccf.hitl.approval_gate.GateResolution` to the
  engine's RECORDED suspension state and the transport's RECORDED submission
  and take ``requested_by`` and ``actor`` from those (I2), re-judge retention
  (the pinned version AND the newest version under the same key), resume the
  engine on the gate's declared approve route, and only on completion APPEND
  the index entries (write-ahead, I4) and THEN file the
  :class:`~ccf.erasure.ErasureRecord` under the erase capability (I3).

No un-erasure verb exists (U6).

Algorithmic module (CINV-03): the clock is injected.
"""

from __future__ import annotations

import hashlib
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
    REPLAY_INPUT_PATHS,
    ErasedAddress,
    ErasureRecord,
    ErasureRequest,
    ErasureSubjectClass,
    ErasureSubjectDeclaration,
    RetentionDecision,
    RetentionHoldPolicy,
    judge_retention,
)
from ccf.erasure.index import ErasureIndexEntry, ErasureIndexProtocol
from ccf.erasure.store import ErasureIndexUnavailable
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


def _values_at(document: object, path: str) -> tuple[str, ...]:
    """The scalar value(s) at a dotted path — a list contributes its scalar members."""
    node = document
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return ()
        node = node[part]
    members = node if isinstance(node, list) else [node]
    return tuple(str(m) for m in members if isinstance(m, (str, int)) and not isinstance(m, bool))


def _hashes_to(salt: str, values: tuple[str, ...], subject_ref: str) -> bool:
    for value in values:
        material = salt.encode("utf-8") + b"\x00" + value.encode("utf-8")
        if hashlib.sha256(material).hexdigest() == subject_ref:
            return True
    return False


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
        index: The deployment's durable erasure index (C1). **Required.** The
            door is its only writer and appends BEFORE it files the record
            (write-ahead, ruling (ii)).

    Raises:
        ccf.erasure.ErasureIndexUnavailable: ``index`` is not an
            :class:`~ccf.erasure.ErasureIndexProtocol`.
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
        index: ErasureIndexProtocol,
    ) -> None:
        if not isinstance(index, ErasureIndexProtocol):
            raise ErasureIndexUnavailable(
                f"{type(index).__name__} is not an ErasureIndexProtocol; the erasure"
                " door writes the durable index (SEC-009; D-IMPL-374 (4), C1)"
            )
        self._engine = engine
        self._factory = factory
        self._control_plane = control_plane
        self._transport = transport
        self._store = store
        self._clock = clock
        self._index = index

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
        subject, decision, stored = self._admit(tenant, workflow, request, latest=True, erase=erase)
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
                # The STORED class, verified against the requester's label (C2).
                artifact_class=stored[address.content_address],
                key_paths=subject.key_paths,
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
            approval_ref=content_hash(recorded_submission),
            retention_decision=decision,
            reason=request.reason,
            legal_basis=request.legal_basis,
        )
        # WRITE-AHEAD (ruling (ii), I4): the index entries — each naming the
        # record's content address, computed before it exists — are appended
        # FIRST, then the record is filed under the ERASE capability (I3). A
        # completion that dies between the two leaves entries whose record is
        # missing: the consult withholds those addresses and audits
        # `erasure_index_unsupported` (design §8). A record with no entry
        # cannot exist, so nothing has to list the store.
        record_address = content_hash(record)
        for address in addresses:
            self._index.append(
                ErasureIndexEntry(
                    tenant_id=tenant,
                    content_address=address.content_address,
                    erasure_record_address=record_address,
                    subject_ref=record.subject_ref,
                    approval_ref=record.approval_ref,
                    reason=record.reason,
                    erased_at=erased_at,
                )
            )
        self._store.put(
            erase,
            DerivedWrite(artifact_class=ERASURE_RECORD_CLASS, name=record_id, artifact=record),
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
    ) -> tuple[ErasureSubjectClass, RetentionDecision, dict[str, str]]:
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
        stored = self._verify_addresses(tenant, request, subject)
        now = self._clock()
        pinned = resolve_pinned(self._control_plane, request.retention_policy_ref)
        # Retention and hold are judged against the STORED class of every
        # address (C2), never the requester's label.
        judged = request.model_copy(
            update={
                "addresses": tuple(
                    a.model_copy(update={"artifact_class": stored[a.content_address]})
                    for a in request.addresses
                )
            }
        )
        decision = self._judge(pinned, request.retention_policy_ref, judged, now)
        if latest:
            name = parse_artifact_uri(request.retention_policy_ref)
            key = f"{name.tenant_id}/{name.artifact_class}/{name.name}"
            versions = self._control_plane.versions(key)
            newest = self._control_plane.peek(key, versions[-1]) if versions else None
            if newest is not None and newest != pinned:
                semver = getattr(newest, "semver", versions[-1])
                self._judge(newest, f"{key}@{semver}", judged, now)
        return subject, decision, stored

    def _verify_addresses(
        self, tenant: str, request: ErasureRequest, subject: ErasureSubjectClass
    ) -> dict[str, str]:
        """Verify every requester-named address; return each one's STORED class.

        Fix round 1, C2, I6 and ruling (iv): the fabric VERIFIES the addresses
        rather than trusting the request. For each, in order: not already
        erased within the tenant; the store's naming (``names_at``) files it
        under THIS tenant (I6); its stored class is not a mechanism class an
        erasure may never reach (the erasure record — C2) and equals the
        requester's label (C2); a value at one of the subject's key paths
        hashes to the request's ``subject_ref`` (iv); and no replay-input path
        of the stored document carries the subject (design §7,
        ``replay-input``). The stored bytes are read through the UNCONSULTED
        inner store for this check only and never leave the door.
        """
        names_at = getattr(self._store, "names_at", None)
        if not callable(names_at):
            raise ErasureRefused(
                f"the store this door files through ({type(self._store).__name__})"
                " answers no naming, so the stored class and tenant of an address"
                " cannot be verified and a requester's label is never trusted"
                " (SEC-009; D-IMPL-374 (4), C2)",
                reason_code="class-unverifiable",
            )
        reader = getattr(self._store, "inner", self._store)
        stored: dict[str, str] = {}
        for address in request.addresses:
            where = address.content_address
            if self._index.lookup(tenant_id=tenant, content_address=where) is not None:
                raise ErasureRefused(
                    f"{where!r} is already erased within this tenant (SEC-009)",
                    reason_code="already-erased",
                )
            own = [name for name in names_at(content_address=where) if name.tenant_id == tenant]
            if not own:
                raise ErasureRefused(
                    "a requested address is not an artifact of the requesting tenant"
                    " (SEC-009; D-IMPL-374 (4), I6)",
                    reason_code="address-not-in-tenant",
                )
            classes = {name.artifact_class for name in own}
            if ERASURE_RECORD_CLASS in classes:
                raise ErasureRefused(
                    "an erasure record is never erasable: the fact of an erasure stays"
                    " servable at its own address (SEC-009; D-IMPL-374 (4), C2)",
                    reason_code="mechanism-class-not-erasable",
                )
            if classes != {address.artifact_class}:
                raise ErasureRefused(
                    f"the request labels an address {address.artifact_class!r} and the"
                    f" store files it as {sorted(classes)!r}; retention is judged"
                    " against the stored class, never the requester's label (SEC-009;"
                    " D-IMPL-374 (4), C2)",
                    reason_code="class-label-mismatch",
                )
            try:
                document = json.loads(reader.get(content_address=where))
            except (ArtifactStoreError, KeyError, ValueError) as unreadable:
                raise ErasureRefused(
                    "a requested address could not be read to verify its subject (SEC-009)",
                    reason_code="subject-unverifiable",
                ) from unreadable
            if not any(
                _hashes_to(subject.subject_ref_salt, _values_at(document, path), request.subject_ref)
                for path in subject.key_paths
            ):
                raise ErasureRefused(
                    "no value at the subject's declared key paths in a requested"
                    " artifact hashes to the request's subject_ref; the fabric verifies"
                    " every address a request names (SEC-009; D-IMPL-374 (4), ruling (iv))",
                    reason_code="subject-not-found",
                )
            if any(
                _hashes_to(subject.subject_ref_salt, _values_at(document, path), request.subject_ref)
                for path in REPLAY_INPUT_PATHS
            ):
                decision = RetentionDecision(
                    policy_ref=request.retention_policy_ref,
                    verdict="refuse",
                    reason_code="replay-input",
                    address=where,
                )
                raise ErasureRefused(
                    "the subject appears in a replay-input field of a requested record;"
                    " erasing it would make a decision replay a different question"
                    " (SEC-009; D-IMPL-367 §7, §2.2)",
                    reason_code="replay-input",
                    decision=decision,
                )
            stored[where] = address.artifact_class
        return stored

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
