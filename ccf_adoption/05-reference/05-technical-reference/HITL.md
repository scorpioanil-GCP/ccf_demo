# Human-in-the-Loop (HITL)

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

HITL provides typed approval, escalation, override and review boundaries. Current main makes both **who acted**, **whether that principal was eligible**, **which event was acted on**, and **whether the gate is still open** explicit governance facts.

## Primary transport surfaces

Current public HITL transport includes:

- `HITLTransportProtocol`;
- `InMemoryHitlTransport`;
- `PendingHitlEvent`;
- `HitlActionRequest`;
- `HitlActionSubmission`;
- `HitlActionReceipt`;
- `GateClosure`;
- `GateAlreadyClosed`;
- `GateVerdictsChanged`;
- `HitlGateClosed`.

A pending approval event can retain its pinned policy reference, requester, workflow state reference and product/content hash.

## Signed human action

Current identity surfaces are:

- `HitlActionClaims`;
- `SignedHitlAction`;
- `sign_hitl_action(...)`;
- `verify_hitl_action(...)`;
- `enforce_attestation(...)`.

The human signs their own action claims. The server compares those claims to the authorized action and its server-minted binding.

The former public `SignedPrincipalBinding` API is not the current surface.

## Approval eligibility

`ApprovalPolicy.eligible_principals` is the pinned statement of who may approve a gate.

`check_approver_eligibility(...)` enforces eligibility and requester/self-approval constraints.

Current workflow-engine composition strengthens this boundary: at construction, the engine binds its Control Plane into the transport's approval-eligibility judgment. A third-party transport used by `WorkflowEngine` must expose `bind_approver_eligibility(control_plane)`; otherwise engine construction refuses with `WorkflowWiringError`.

On an engine-composed reference transport, an ineligible principal's `approve`/`reject`
is refused before recording when the selected event is the gate's own
approval-gate event and names an approval policy. The requester is also refused.

A custom transport must implement the binding method **and use it**: at submit,
call `check_approver_eligibility` against each bound Control Plane before recording
these verdicts. The engine checks that the method exists, but cannot verify its
implementation; no conformance test establishes that a custom transport performs
the judgment. The method is not part of `HITLTransportProtocol`; a transport used
without an engine does not need it.

### Recorded eligibility exceptions

The submit check does not cover `annotate`, `override`, or approval-gate events
without a named policy. Two recorded follow-ups also remain:

- **Late verdict:** while no request for the exact suspended pause is queued or claimed, a principal with `HitlSubmit` can record a hash-bound verdict without the
  eligibility judgment. It never authorizes passage, but an opposite verdict
  holds the gate as a conflict. After closure it refuses `hitl-gate-closed`.
- **Non-gate event under the gate's key:** if deployment code files an escalation
  or other non-gate event under that key with the same pause fingerprint and the transport selects it, eligibility
  is not judged at submit. An opposite verdict can hold the gate. The engine's
  own eligibility check still prevents an ineligible principal or the requester
  from authorizing passage.

Required signed bindings still apply and narrow these cases; they do not close
them. No supported operation reopens a conflicted gate. The exact prerequisites
and queue-selection conditions are preserved in the
[SDK security guide, section 4.13](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/public/how-to/security-and-deployment.md#413-one-approval-one-passage-resume-over-a-shared-store-and-a-shared-transport-d-impl-377-d-impl-378).
These are disclosed follow-ups, not repairs or a new security closure.
See [migration and delivery limits](MIGRATION_AND_LIMITATIONS.md).

This does not mean every HITL conflict is impossible. An eligible principal can still create a conflicting verdict; use the current SDK decision log for the numbered finding status.

## Gate closure

A gate's verdict population and closure are explicit state.

Current public types distinguish:

- an open gate with eligible verdicts;
- a closed gate;
- changed verdicts around closure;
- attempts to act on a gate already closed.

Do not treat "a verdict exists" as equivalent to "the gate is durably open/closed for this passage."

## ReviewQueue and the review door

`ReviewQueue` remains the review primitive.

Current main adds:

- `ccf_runtime.mcp.review_door.ReviewDoor`;
- `open_review_door(...)`;
- `ReviewActionRefused`.

The review door composes the standard authenticated HITL door over a queue and binds the reviewer's scope to the exact review-event key patterns it may act on. `approve` releases, `reject` rejects, and other verdicts refuse before the queue is touched.

A deployment that previously called queue release/reject directly from an external principal path should move that authority through the review door.

## Workflow suspension and legacy recovery

SDK 1.0.2 stamps every workflow state record with the state store's permanent identity. A verdict therefore binds to the store and the exact pause that requested it. Foreign-store records refuse resumption. `ConditionalStateStore.identity` must be stable, unique to the substrate and persisted with its records; a copied durable store must refuse to open. The engine checks shape only.

A retry or resumption restores a missing request without rerunning the workflow step or manufacturing approval. Enqueue is now atomic and deduplicated on `(tenant, event_key, product_content_hash)`; a claimed request is no longer pending and can be returned. Concurrent state transitions can still raise `ExecutionFenced`.

A custom transport must add `retire(*, tenant, event_key, product_content_hash)`, atomically removing matching pending requests without minting a claim, and judge submissions against their exact pause. A pending direct verdict counts at resumption only while that request is still waiting. A claim on another pause is neither used nor consumed. HTTP `event_pending` describes the named pause.

Use `WorkflowEngine.rebind_legacy_suspension` for a durable run suspended before identity existed. It writes the new trace/state, files a fresh request, then retires the old fingerprint. Collect fresh approval; pre-upgrade verdicts cannot release the new pause. Rebind is Python-only. A failure after the state write can leave a stale oldest request blocking progress until an operator retires it; an old in-flight request can also return unanswered. No such window lends an old verdict authority.

Path-backed stores and queues declaring `process` must hold an exclusive lease from open to close and expose `writer_lease()`. The SDK ships in-memory implementations, not a durable approval store. A claim is still held per key, so a concurrent different-pause enqueue can discard the claim and require another approval attempt. Escalations remain shared by execution key across stores. Use one HITL transport per state store for recovery; these changes do not create a distributed transaction over application effects.

See [required custom-component changes](MIGRATION_AND_LIMITATIONS.md#workflow-stores-and-approval-transports-required-changes) and the source [security guide, section 4.13](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/public/how-to/security-and-deployment.md#413-one-approval-one-passage-resume-over-a-shared-store-and-a-shared-transport-d-impl-377-d-impl-378).

## Workflow trace/reference integrity

Current engine surfaces include:

- `ExecutionFenced`;
- `WorkflowTraceReferenceMismatch`;
- `WorkflowResumeRefused`;
- `suspension_left_by(...)`.

When a store returns a reference that is not exactly the trace the engine wrote, the engine refuses rather than returning that reference to the caller.

## Erasure approval

Erasure uses a separate signed/eligible human approval path with deployment-fixed workflow/policy/trust configuration. The erasure read path re-verifies the retained approval evidence.

This is artifact-read withholding, not byte destruction or a statement of regulatory compliance.

See [Artifacts and Stores](ARTIFACTS_AND_STORES.md).

## Developer rule

Do not build an approval API that accepts only a boolean or trusts a caller-supplied principal string.

A governed human action needs:

1. authenticated/authorized principal;
2. event/request binding;
3. product/content binding;
4. eligibility policy where required;
5. attestation when required;
6. gate state/closure semantics;
7. recorded action and policy evidence.

## Exact current shapes

Use [Extensions API](api/extensions.md) and [Runtime API](api/runtime.md).
