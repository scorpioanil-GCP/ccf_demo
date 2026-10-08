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
  ``subject_ref`` (iv); no subject in a replay-input field of a record the
  fabric's record writer filed (§7; ``D-IMPL-378``)), judge
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

**The door's trust root is fixed at construction** (fix round 5): it takes the
tenant's :class:`~ccf.erasure.ErasureAuthority` — the SAME one every consult
composes with — and refuses, by name, a HITL transport bound to any other HITL
policy key (R5) and a signing key whose signature does not verify under the
authority's declared door key (R2). It runs only the declared erasure workflow
(R1, ``workflow-not-declared``), and it SIGNS every record it files over the
record's canonical bytes (R2): the signature is what lets a consult take
``requested_by`` — the starter the engine recorded, which the door observed —
as the door's statement rather than a filer's. It travels in every index entry
naming the record; a retry reuses its prior attempt's signature, verified, so
the write-ahead entries and the record stay byte-identical.

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
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.resolution import resolve_pinned
from ccf.controlplane.state import state_key
from ccf.erasure.contracts import (
    ERASURE_APPROVAL_CLASS,
    ERASURE_RECORD_CLASS,
    REPLAY_INPUT_PATHS,
    ErasedAddress,
    ErasureApproval,
    ErasureRecord,
    ErasureRequest,
    ErasureSubjectClass,
    ErasureSubjectDeclaration,
    RetentionDecision,
    RetentionHoldPolicy,
    judge_retention,
)
from ccf.erasure.approval import (
    ErasureApprovalInvalid,
    reference_approval_verifier,
    verify_erasure_approval,
)
from ccf.erasure.errors import ErasureCompositionRefused
from ccf.erasure.index import ErasureIndexEntry, ErasureIndexProtocol
from ccf.erasure.store import ErasureIndexUnavailable
from ccf.erasure.trust import (
    DOOR_SIGNATURE_ASSERTION,
    ErasureAuthority,
    ErasureRecordInvalid,
    sign_erasure_record,
    verify_door_signature,
)
from ccf.hitl.approval_gate import GATE_APPROVE, GATE_EVENT_CLASS, GateResolution
from ccf.hitl.transport import HITLTransportProtocol
from ccf.mcp.errors import McpServerUnreachable
from ccf.peering.identity import IdentityError, IdentityProvider
from ccf.replay.provenance import UnattributableRecordStore, filed_by_record_writer
from ccf.workflow.definitions import WORKFLOW_FAILED_STATE
from ccf.workflow.factory import Workflow, WorkflowFactory
from ccf_runtime.workflow.state import WORKFLOW_STATE, WorkflowStateRecord, suspension_left_by
from ccf_runtime.workflow.engine import (
    ExecutionFenced,
    WorkflowCompleted,
    WorkflowEngine,
    WorkflowSuspended,
)

__ccf_mode__ = "algorithmic"

__all__ = ["ErasureDoor", "ErasureRefused", "ErasureWorkflowUngated"]

#: What the door's composition-time probe signature asserts in its protected
#: header — never the record class, so a probe never verifies as a record
#: signature (fix round 5, R2).
_DOOR_PROBE_CLASS = "ccf.erasure-door-probe"


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
            Its bound HITL policy key must be ``authority``'s, or construction
            refuses by name (fix round 5, R5).
        authority: The tenant's :class:`~ccf.erasure.ErasureAuthority` — the
            SAME one every consult composes with: the HITL policy key every
            recorded approval must pin (fix round 4, ruling 1), the erasure
            workflow this door runs (fix round 5, R1), and the door's public
            signing key (R2). **Required, no default** (CINV-01).
        door_signer: The provider holding the door's PRIVATE signing key —
            deployment custody, never a requester's (R2).
        door_key_id: The key id it signs under; one ``authority`` declares,
            whose signature verifies under the declared public key, or
            construction refuses by name.
        store: The artifact store the record is filed through.
        clock: The injected fabric clock (``erased_at`` and the judgment's now).
        index: The deployment's durable erasure index (C1). **Required.** The
            door is its only writer and appends BEFORE it files the record
            (write-ahead, ruling (ii)).

    Raises:
        ccf.erasure.ErasureIndexUnavailable: ``index`` is not an
            :class:`~ccf.erasure.ErasureIndexProtocol`.
        ccf.erasure.ErasureCompositionRefused: ``authority`` is not an
            :class:`~ccf.erasure.ErasureAuthority`; ``transport`` is bound to
            another HITL policy key, or declares none (R5); or ``door_key_id``
            is not a door key ``authority`` declares, or ``door_signer``'s
            signature under it does not verify against the declared key (R2).
    """

    def __init__(
        self,
        *,
        engine: WorkflowEngine,
        factory: WorkflowFactory,
        control_plane: ControlPlaneRegistry,
        transport: HITLTransportProtocol,
        authority: ErasureAuthority,
        door_signer: IdentityProvider,
        door_key_id: str,
        store: ArtifactStoreProtocol,
        clock: Callable[[], datetime],
        index: ErasureIndexProtocol,
        identity_provider: IdentityProvider | None = None,
    ) -> None:
        if not isinstance(index, ErasureIndexProtocol):
            raise ErasureIndexUnavailable(
                f"{type(index).__name__} is not an ErasureIndexProtocol; the erasure"
                " door writes the durable index (SEC-009; D-IMPL-374 (4), C1)"
            )
        if not isinstance(authority, ErasureAuthority):
            raise ErasureCompositionRefused(
                f"the erasure door takes its tenant's ErasureAuthority; got"
                f" {type(authority).__name__} (SEC-009; D-IMPL-374 (4), fix round 5)"
            )
        # Fix round 5, R5: the approvals this door files are the ones ITS
        # transport admitted under the authority's HITL policy — the same key.
        bound = getattr(transport, "hitl_policy_key", None)
        if bound != authority.hitl_policy_key:
            raise ErasureCompositionRefused(
                f"the erasure door's HITL policy key {authority.hitl_policy_key!r} is"
                f" not the key its HITL transport is bound to ({bound!r}); a door"
                " and a transport judging approvals under different policies would"
                " file approvals no consult verifies (SEC-009; D-IMPL-374 (4), fix"
                " round 5, R5)"
            )
        self._engine = engine
        self._factory = factory
        self._control_plane = control_plane
        self._transport = transport
        self._authority = authority
        self._door_signer = door_signer
        self._door_key_id = door_key_id
        self._store = store
        self._clock = clock
        self._index = index
        # Fix round 4: the verifier the approval's signed attestation is checked
        # with — the deployment's HITL identity provider, or the SDK reference.
        self._identity_provider = (
            reference_approval_verifier() if identity_provider is None else identity_provider
        )
        self._require_door_key()

    def _require_door_key(self) -> None:
        """Fix round 5, R2: the door's signing key IS the declared door key — refused by name otherwise.

        A probe — asserting a probe class, never the record class, so it can
        never verify as a record signature — is signed under ``door_key_id``
        and verified against exactly the key the authority declares for it.
        """
        declared = self._authority.door_keys.get(self._door_key_id)
        if declared is None:
            raise ErasureCompositionRefused(
                f"door key {self._door_key_id!r} is not one the authority declares"
                f" ({sorted(self._authority.door_keys)}) (SEC-009; D-IMPL-374 (4), fix round 5, R2)"
            )
        probe = {"probe": _DOOR_PROBE_CLASS, "tenant_id": self._authority.tenant_id}
        try:
            envelope = self._door_signer.sign(
                product=probe, key_id=self._door_key_id, assertions={DOOR_SIGNATURE_ASSERTION: _DOOR_PROBE_CLASS}
            )
            self._identity_provider.verify(signed=envelope, public_keys={self._door_key_id: declared})
        except (IdentityError, ValueError) as unverified:
            raise ErasureCompositionRefused(
                f"the door's signing key {self._door_key_id!r} does not verify under the"
                " door key the authority declares; every record this door signed would"
                " read index-unsupported (SEC-009; D-IMPL-374 (4), fix round 5, R2)"
            ) from unverified

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
            ErasureRefused: tenant, declaration, retention or hold refusal; the
                workflow did not suspend on its gate; or the engine fenced the
                start's suspension, ``execution-fenced`` (``D-IMPL-378``).
        """
        workflow = self._factory.construct(authorized, definition_version=definition_version)
        self._admit(authorized.tenant, workflow, request, latest=False, erase=erase)
        try:
            outcome = await self._engine.execute(authorized, workflow, execution_id=request.request_id)
        except ExecutionFenced as fenced:
            raise self._fenced(fenced, consequence="no approval was requested") from fenced
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
        workflow declares a further gate. A retry of a completion whose
        passage past the gate committed before its engine stopped — the run
        ``running`` — is held to the suspension that passage left, and the
        engine finishes the passage when no step can have run since its commit
        (``D-IMPL-378``, Dave's D2 ruling); otherwise the engine refuses it,
        ``workflow-refused``.

        Raises:
            ErasureWorkflowUngated: the workflow can complete without a gate.
            ErasureRefused: any refusal; nothing is written. Except
                ``execution-fenced`` in the last passage, which the engine fenced
                after the write-ahead append (``D-IMPL-378``): no erasure record
                is filed, and the address stays withheld under the appended
                entries (``index-unsupported``).
            ccf.erasure.ErasureIndexWriteFailed: a write-ahead index append
                could not write its whole line (PC1, panel C1; ``D-IMPL-374``).
                Propagated by name before the workflow resumes: no record is
                filed, the entry is not in the index, and a retry on a working
                disk completes the erasure.
        """
        workflow = self._factory.construct(authorized, definition_version=definition_version)
        tenant = authorized.tenant
        subject, decision, stored = self._admit(tenant, workflow, request, latest=True, erase=erase)
        event = resolution.record.event
        submission = resolution.record.submission
        suspension = state_key(tenant=tenant, record_id=request.request_id)
        # I2 (fix round 1): the FABRIC's own record of this execution — the
        # engine-written state — not anything the caller presents.
        state = self._control_plane.state_store.get(WORKFLOW_STATE, suspension)
        recorded_submission = next(
            (s for s in self._transport.submissions(tenant=tenant) if s == submission),
            None,
        )
        if not isinstance(state, WorkflowStateRecord) or recorded_submission is None:
            raise self._approval_not_recorded()
        # I4 (fix round 2): the entries already appended for THIS request — a
        # prior completion that died after its write-ahead append.
        prior = tuple(
            entry
            for entry in (
                self._index.lookup(tenant_id=tenant, content_address=a.content_address)
                for a in request.addresses
            )
            if entry is not None and entry.request_id == request.request_id
        )
        # The record is DETERMINISTIC across retries: its instant is the one
        # the write-ahead entries already carry, when a prior attempt wrote them.
        erased_at = prior[0].erased_at if prior else self._clock()
        if state.status == "suspended":
            gate = state.current_state
            bound = recorded_submission.principal.product_content_hash == content_hash(state)
        elif state.status == "terminal" and prior:
            # The retry of a completion that appended, resumed, and died before
            # filing its record: the gate it left is the trace's last resume,
            # and the approval is the one the write-ahead entries name.
            resumed = [t for t in state.trace if t.kind == "resume"]
            gate = resumed[-1].source if resumed else ""
            bound = True  # checked against the approval's address below
        elif state.status == "running" and (left := suspension_left_by(state)) is not None:
            # D-IMPL-378 (Dave's D2): the retry of a completion whose passage
            # past the gate committed and whose engine stopped before the
            # passage's next write. The approval is held to the suspension that
            # passage LEFT, rebuilt exactly; the engine, resumed below, finishes
            # the passage when no step can have run since its commit, and
            # refuses it otherwise ("workflow-refused").
            gate = left.current_state
            bound = recorded_submission.principal.product_content_hash == content_hash(left)
        else:
            raise self._approval_not_recorded()
        # Fix round 4: an erasure requires a SIGNED approval (D-IMPL-363). The
        # recorded submission must carry its attestation and the transport's
        # pin of the HITL policy that admitted it; refused by name otherwise.
        attestation = recorded_submission.attestation
        if attestation is None or recorded_submission.hitl_policy_ref is None:
            raise ErasureRefused(
                "an erasure is written only on a SIGNED human approval: the recorded"
                " gate submission carries no signed HITL attestation, or no pinned"
                " HITL policy to verify it against (SEC-009; D-IMPL-374 (4), fix"
                " round 4; D-IMPL-363)",
                reason_code="approval-unsigned",
            )
        # Fix round 3 (I3 part 2, option (a)): the RECORDED approval, as an
        # immutable content-addressed artifact; its address is approval_ref.
        # Its instant is the signer's own (fix round 4), so a retry re-files the
        # same artifact.
        approval = ErasureApproval(
            tenant_id=tenant,
            request_id=request.request_id,
            approver=recorded_submission.principal.approver,
            verdict=recorded_submission.action,
            acted_at=attestation.claims.issued_at,
            gate=gate or "-",
            gate_state_hash=recorded_submission.principal.product_content_hash,
            workflow_definition_hash=content_hash(workflow.definition),
            submission_hash=content_hash(recorded_submission),
            attestation=attestation,
            hitl_policy_ref=recorded_submission.hitl_policy_ref,
        )
        approval_ref = content_hash(approval)
        if prior and any(e.approval_ref != approval_ref for e in prior):
            bound = False
        recorded = (
            bound
            and resolution.record.approved
            and recorded_submission.action == GATE_APPROVE
            and recorded_submission.event_key == f"{suspension}/{gate}"
            and event.event_key == recorded_submission.event_key
            and event.event_class == GATE_EVENT_CLASS
            and event.tenant == tenant
            and event.workflow_state_ref == suspension
            and gate in workflow.definition.gate_policies
            and event.policy_ref == workflow.definition.gate_policies[gate]
        )
        if not recorded:
            raise self._approval_not_recorded()
        # The requester is the starter the ENGINE recorded on the execution,
        # and the actor is the approver on the transport's RECORDED submission
        # — never the presented event (I2; probe P3).
        requested_by = state.started_by
        if requested_by is None:
            raise ErasureRefused(
                "the execution records no starter (SEC-009; D-IMPL-366 G1)",
                reason_code="requester-unrecorded",
            )
        actor = recorded_submission.principal.approver
        # Fix rounds 4 and 5: the SAME verification the consult runs — the
        # approval for THE declared erasure workflow, in its tenant (R1); the
        # pin naming the authority's HITL policy key (ruling 1); the signature
        # against the key that policy declares for the approver, at the pinned
        # version, signed before that version's supersession (ruling 4); the
        # signed claims against this request's gate, tenant, state and verdict;
        # the approver not the requester and eligible under the declared
        # workflow's erasure-gate policy (ruling 2); and the gate that
        # workflow's erasure gate (ruling 3). Refused by name before anything
        # is written.
        try:
            verify_erasure_approval(
                approval,
                tenant_id=tenant,
                request_id=request.request_id,
                approver=actor,
                requested_by=requested_by,
                authority=self._authority,
                control_plane=self._control_plane,
                identity_provider=self._identity_provider,
            )
        except ErasureApprovalInvalid as invalid:
            raise ErasureRefused(
                f"the recorded approval does not verify for this request"
                f" ({invalid}) (SEC-009; fix round 4)"[:400],
                reason_code=invalid.reason_code,
            ) from invalid
        route = workflow.definition.gate_routes.get(gate, {}).get(GATE_APPROVE)
        if route is None:
            raise ErasureRefused(
                f"gate {gate!r} declares no approve route (SEC-009)", reason_code="approval-route-undeclared"
            )
        final = route in workflow.definition.effective_terminal_states
        if not final:
            # A further gate follows: nothing is erased until the last approval.
            try:
                outcome = await self._engine.resume(
                    authorized, workflow, execution_id=request.request_id, decision=route
                )
            except ExecutionFenced as fenced:
                raise self._fenced(fenced, consequence="nothing was erased") from fenced
            if isinstance(outcome, WorkflowSuspended):
                return outcome
            raise ErasureRefused(
                f"the erasure workflow did not suspend on its next gate ({outcome!r})"[:400],
                reason_code="workflow-refused",
            )
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
                "request_id": request.request_id,
                "subject_ref": request.subject_ref,
                "addresses": [a.content_address for a in addresses],
                "erased_at": erased_at.isoformat(),
            }
        )
        record = ErasureRecord(
            tenant_id=tenant,
            record_id=record_id,
            request_id=request.request_id,
            subject_class=request.subject_class,
            subject_ref=request.subject_ref,
            addresses=addresses,
            erased_at=erased_at,
            actor=actor,
            requested_by=requested_by,
            # The authorizer's allow for the ERASE door kind (design §2.3). A
            # retry presents the same erase decision, or its record would not be
            # the one the write-ahead entries name.
            authorizing_decision_id=erase.decision_id,
            approval_ref=approval_ref,
            retention_decision=decision,
            reason=request.reason,
            legal_basis=request.legal_basis,
        )
        record_address = content_hash(record)
        if any(e.erasure_record_address != record_address for e in prior):
            raise ErasureRefused(
                "a retry built a record other than the one its prior attempt's index"
                " entries name; present the same request and erase decision (SEC-009; I4)",
                reason_code="retry-mismatch",
            )
        door_signature, door_key_id = self._door_signature(record, prior)
        # WRITE-AHEAD, BEFORE THE RESUME COMMITS (rulings (ii) and I4): the
        # approval is already recorded by the gate, so the index entries — each
        # naming the record's content address, computed before it exists — are
        # appended FIRST, under the ERASE capability for this request (I3);
        # then the engine resumes; then the record is filed. A completion that
        # dies anywhere after the append leaves the address WITHHELD, and a
        # retry of this method completes it (the entries are idempotent, the
        # record deterministic, and a terminal execution with this request's
        # entries is accepted above — as is a running one whose passage the
        # engine finishes, D-IMPL-378). A record with no entry cannot exist.
        # The approval FIRST (fix round 3): an entry must never name an
        # approval that is not on the substrate. Idempotent — content-addressed.
        self._store.put(
            erase,
            DerivedWrite(artifact_class=ERASURE_APPROVAL_CLASS, name=approval_ref, artifact=approval),
        )
        for address in addresses:
            self._index.append(
                erase,
                ErasureIndexEntry(
                    tenant_id=tenant,
                    content_address=address.content_address,
                    erasure_record_address=record_address,
                    subject_class=record.subject_class,
                    request_id=record.request_id,
                    subject_ref=record.subject_ref,
                    approval_ref=record.approval_ref,
                    reason=record.reason,
                    erased_at=erased_at,
                    door_signature=door_signature,
                    door_key_id=door_key_id,
                ),
            )
        if state.status in ("suspended", "running"):
            try:
                outcome = await self._engine.resume(
                    authorized, workflow, execution_id=request.request_id, decision=route
                )
            except ExecutionFenced as fenced:
                raise self._fenced(
                    fenced,
                    consequence=(
                        "no erasure record was filed, and the address stays withheld"
                        " (index-unsupported) under the index entries this completion appended"
                    ),
                ) from fenced
            if not isinstance(outcome, WorkflowCompleted) or outcome.terminal_state == WORKFLOW_FAILED_STATE:
                raise ErasureRefused(
                    f"the erasure workflow did not complete ({outcome!r}); the address"
                    " stays withheld (index-unsupported) and the audit says so"[:400],
                    reason_code="workflow-refused",
                )
        self._store.put(
            erase,
            DerivedWrite(artifact_class=ERASURE_RECORD_CLASS, name=record_id, artifact=record),
        )
        return record

    def _door_signature(
        self, record: ErasureRecord, prior: tuple[ErasureIndexEntry, ...]
    ) -> tuple[str, str]:
        """The door's signature over ``record`` (fix round 5, R2): a retry's prior one, verified, or a new one.

        An ES256 signature is not deterministic, so a retry REUSES the signature
        its prior attempt appended — the entries must stay identical for the
        index to take them again — and only after verifying that every prior
        entry's signature is the door's over exactly this record; otherwise the
        retry is refused by name rather than completing over an entry the
        consult will never support.
        """
        if not prior:
            return sign_erasure_record(record, signer=self._door_signer, key_id=self._door_key_id), self._door_key_id
        payload = canonical_bytes(record)
        try:
            for entry in prior:
                verify_door_signature(
                    payload,
                    door_signature=entry.door_signature,
                    door_key_id=entry.door_key_id,
                    authority=self._authority,
                    identity_provider=self._identity_provider,
                )
        except ErasureRecordInvalid as invalid:
            raise ErasureRefused(
                "a prior attempt's index entry for this request carries no door signature"
                " that verifies over the record this retry builds; it cannot be completed"
                " (SEC-009; I4; fix round 5, R2)",
                reason_code="retry-mismatch",
            ) from invalid
        return prior[0].door_signature, prior[0].door_key_id

    @staticmethod
    def _fenced(fenced: ExecutionFenced, *, consequence: str) -> ErasureRefused:
        """A passage the engine fenced, as this door's refusal, ``execution-fenced`` (``D-IMPL-378``).

        The engine raises :class:`~ccf_runtime.workflow.engine.ExecutionFenced`
        when another writer moved the execution's record while a passage ran,
        and then writes, audits and enqueues nothing more. The workflow doors
        answer it 409 ``execution-fenced``; this door refuses it by the same name
        rather than let it escape. ``consequence`` says what stands.
        """
        return ErasureRefused(
            "the erasure workflow's passage was fenced: another writer moved the"
            f" execution's record while it ran, and the engine wrote nothing more; {consequence}"
            " (SEC-009; D-IMPL-378)",
            reason_code="execution-fenced",
        )

    @staticmethod
    def _approval_not_recorded() -> ErasureRefused:
        return ErasureRefused(
            "the presented approval is not one the HITL authority path recorded for"
            " this request's execution; an erasure is written only on a recorded"
            " human approval (SEC-009; D-IMPL-367 §4.1; D-IMPL-366)",
            reason_code="approval-not-recorded",
        )

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
        # Fix round 5, R1: this door runs the DECLARED erasure workflow, in its
        # tenant, and nothing else — an approval given under any other workflow
        # is one no consult verifies, so it is refused before anything starts.
        if tenant != self._authority.tenant_id:
            raise ErasureRefused(
                f"this erasure door is tenant {self._authority.tenant_id!r}'s; the"
                f" capability is for {tenant!r} (SEC-009; fix round 5, R1)",
                reason_code="tenant-mismatch",
            )
        if content_hash(workflow.definition) != self._authority.workflow_definition_hash:
            raise ErasureRefused(
                f"workflow definition {workflow.definition.name!r} is not the erasure"
                " workflow declared at composition; this door runs that workflow only"
                " (SEC-009; D-IMPL-374 (4), fix round 5, R1)",
                reason_code="workflow-not-declared",
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
        stored = self._verify_addresses(tenant, request, subject, completing=latest)
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
        self,
        tenant: str,
        request: ErasureRequest,
        subject: ErasureSubjectClass,
        *,
        completing: bool,
    ) -> dict[str, str]:
        """Verify every requester-named address; return each one's STORED class.

        Fix round 1, C2, I6 and ruling (iv): the fabric VERIFIES the addresses
        rather than trusting the request. For each, in order: not already
        erased within the tenant; the store's naming (``names_at``) files it
        under THIS tenant (I6); its stored class is not a mechanism class an
        erasure may never reach (the erasure record — C2) and equals the
        requester's label (C2); a value at one of the subject's key paths
        hashes to the request's ``subject_ref`` (iv); and, for a Decision
        Replay record the fabric's record writer filed, no replay-input path of
        the stored document carries the subject (design §7, ``replay-input``;
        :meth:`_filed_by_record_writer`, ``D-IMPL-378``). The stored bytes are
        read through the UNCONSULTED inner store for this check only and never
        leave the door.
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
            standing = self._index.lookup(tenant_id=tenant, content_address=where)
            if standing is not None and not (completing and standing.request_id == request.request_id):
                raise ErasureRefused(
                    f"{where!r} is already erased within this tenant (SEC-009)",
                    reason_code="already-erased",
                )
            try:
                named = names_at(content_address=where)
            except (McpServerUnreachable, ArtifactStoreError, AttributeError) as unanswered:
                # (d), fix round 2: a substrate whose naming read fails — an
                # older MCP server without the names resource, or a names read
                # the governed dereference refused — has not verified the class.
                # `D-IMPL-378`: so has the erasure-consulting composition of a
                # substrate that answers no naming; the decorator answers
                # `names_at` by delegating and raises AttributeError.
                raise ErasureRefused(
                    f"the store's naming did not answer for a requested address"
                    f" ({type(unanswered).__name__}); its stored class and tenant"
                    " cannot be verified (SEC-009; D-IMPL-374 (4), C2)",
                    reason_code="class-unverifiable",
                ) from unanswered
            own = [name for name in named if name.tenant_id == tenant]
            if not own:
                raise ErasureRefused(
                    "a requested address is not an artifact of the requesting tenant"
                    " (SEC-009; D-IMPL-374 (4), I6)",
                    reason_code="address-not-in-tenant",
                )
            classes = {name.artifact_class for name in own}
            if classes & {ERASURE_RECORD_CLASS, ERASURE_APPROVAL_CLASS}:
                raise ErasureRefused(
                    "an erasure record or recorded approval is never erasable: the"
                    " erasure's evidence stays servable at its own address (SEC-009;"
                    " D-IMPL-374 (4), C2; fix round 3)",
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
            ) and self._filed_by_record_writer(tenant, where):
                decision = RetentionDecision(
                    policy_ref=request.retention_policy_ref,
                    verdict="refuse",
                    reason_code="replay-input",
                    address=where,
                )
                raise ErasureRefused(
                    "the subject appears in a replay-input field of a requested record"
                    " the fabric's record writer filed; erasing it would make a decision"
                    " replay a different question (SEC-009; D-IMPL-367 §7, §2.2;"
                    " D-IMPL-378)",
                    reason_code="replay-input",
                    decision=decision,
                )
            stored[where] = address.artifact_class
        return stored

    def _filed_by_record_writer(self, tenant: str, address: str) -> bool:
        """Whether the fabric's record writer filed ``address`` under ``tenant`` (`D-IMPL-378`).

        Record retention — the ``replay-input`` refusal — protects a Decision
        Replay record, and a record is what the fabric's record writer filed.
        Bytes a principal filed on a client lane are a client artifact whatever
        their shape, and are erased like one (Dave, 2026-10-07 21:11 MST). The
        ONE provenance check decides
        (:func:`~ccf.replay.provenance.filed_by_record_writer`), over the store
        this door files through and under the requesting tenant — the tenant
        the address was verified to be filed under (I6) — so another tenant's
        filing of the same bytes never changes this tenant's answer.

        Asked only where the answer matters: a requested address whose stored
        document carries the subject in a replay-input field.

        Raises:
            ErasureRefused: ``class-unverifiable`` — the store declares no
                ``WriteKinds``, so it cannot say who filed an address
                (:class:`~ccf.replay.provenance.UnattributableRecordStore` is
                the cause), or the naming read this question makes failed. The
                door cannot tell a record from a client artifact, so it refuses
                rather than judge the bytes on their own word. (A store whose
                naming cannot be read at all was already refused by the class
                check, before this is asked.)
        """
        try:
            return filed_by_record_writer(self._store, content_address=address, tenant_id=tenant)
        except UnattributableRecordStore as unattributable:
            raise ErasureRefused(
                f"the store this door files through ({type(self._store).__name__}) cannot"
                " say whether the fabric's record writer filed a requested address whose"
                " subject appears in a replay-input field, so record retention cannot be"
                " judged (SEC-009; D-IMPL-378)",
                reason_code="class-unverifiable",
            ) from unattributable
        except (McpServerUnreachable, ArtifactStoreError) as unanswered:
            raise ErasureRefused(
                f"the store's naming did not answer for a requested address"
                f" ({type(unanswered).__name__}); whether the fabric's record writer"
                " filed it cannot be verified (SEC-009; D-IMPL-378)",
                reason_code="class-unverifiable",
            ) from unanswered

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
