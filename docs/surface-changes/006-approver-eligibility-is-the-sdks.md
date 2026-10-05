# 006 — approver eligibility is the SDK's, not the adopter's intent

`SEC-006` (`D-IMPL-366`, G1–G8 and the H1–H3 amendment; Dave, 2026-10-04 and
2026-10-05). Until this change every `gate_policies` target in the tree was an
untyped `DeclaredArtifact` whose `approver_role` and `quorum` no code read:
"who may approve" was a documented intent and not a control. Measured before
the change on the red-test branch (`0bb6d4b5`): a bound transport admitted a
door-shaped approval of a gate whose policy was of the wrong class, the
primitive resolved it and took the claim, both doors returned a receipt, and
the engine opened the gate on it.

ONE design, recorded at every name the manifest tracks it under: a typed
`ccf.approval-policy` (`eligible_principals`, non-empty, principal-based, no
roles, no quorum, no self-approval switch), one shared eligibility judgment at
the three sites a verdict can enter the authority path (transport, primitive,
engine), a recorded REQUESTER on every gate event (the STARTER, G1 (a)), three
transport-stamped audit fields on the recorded submission (H3 (a), H2), the
revalidation of the selected event before any nonce or claim is consumed
(§4b 6a), and a factory that refuses a non-typed gate policy by name.

The prefix `006` is the finding number, not a phase or decision id; the
assembler uses it only as a sort key.

## ccf.hitl.approval_policy.ApprovalPolicy

- Surface: ccf.hitl.approval_policy.ApprovalPolicy
- Public surface: true
- Change type: added
- Before: absent — a gate's approval policy was a `DeclaredArtifact` under an
  adopter class id, with no contract and no reader
- After: a `CCFContract` with `semver` and `eligible_principals:
  frozenset[str]` (`min_length=1`; an empty set is refused at construction by
  name, G7 (a)); the one artifact approver eligibility is judged against
- Why: an approval policy nothing judges is documentation, not a control
  (`SEC-006`)
- Migration: register one per gate (or share one) through `register_typed`
  against `APPROVAL_POLICY` under a NEW key, and pin it from a NEW workflow
  definition version's `gate_policies` (a key bound to the pre-change
  declared class cannot be rebound; ruled 2026-10-05); the class is
  adopter-registered only and not manifest-addressable (the
  `ccf.hitl-policy` precedent). An in-flight suspension persisted before
  this change carries no starter and REFUSES at resolution under a bound
  plane (G5 (a), fail-closed): pre-change executions do not resume; re-run
  them under the new definition version after upgrading

## ccf.hitl.approval_policy.APPROVAL_POLICY

- Surface: ccf.hitl.approval_policy.APPROVAL_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.approval-policy", contract=ApprovalPolicy)`
- Why: the registration contract for the typed policy (`D-IMPL-366` §4 (1))
- Migration: pass it to `register_typed`; it is deliberately absent from
  `SDK_ARTIFACT_CLASSES`, so a deployment manifest cannot name it

## ccf.hitl.ApprovalPolicy

- Surface: ccf.hitl.ApprovalPolicy
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of the same class
- Why: the HITL package is the adopter's import surface for the pillar
- Migration: none — a re-export

## ccf.hitl.APPROVAL_POLICY

- Surface: ccf.hitl.APPROVAL_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of the artifact class
- Why: same as above
- Migration: none — a re-export

## ccf.hitl.transport.check_approver_eligibility

- Surface: ccf.hitl.transport.check_approver_eligibility
- Public surface: true
- Change type: added
- Before: absent — no site judged who may approve
- After: `check_approver_eligibility(*, policy_ref, requested_by, subject_id,
  control_plane)`: the ONE judgment, shared by the transport, the primitive
  and the engine. Resolves `policy_ref` through `resolve_pinned` (never
  "latest", no clock); refuses `ApproverNotEligible` when the plane is bound
  and the policy is absent, unresolvable or of the wrong class, the requester
  is unrecorded, the subject is not eligible, or the subject is the
  requester; performs no check when `control_plane` is `None`
- Why: three sites with one judgment cannot drift apart (`D-IMPL-366` §4 (3))
- Migration: a user-implemented transport that binds a Control Plane should
  call it before attestation for approval-gate events, as the reference
  transport does

## ccf.hitl.check_approver_eligibility

- Surface: ccf.hitl.check_approver_eligibility
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export of the judgment
- Why: same as above
- Migration: none — a re-export

## ccf.hitl.transport.ApproverNotEligible

- Surface: ccf.hitl.transport.ApproverNotEligible
- Public surface: true
- Change type: added
- Before: absent
- After: a `PermissionError` sibling of `PrincipalMismatchRefused`, raised by
  the judgment; its message names the reason class and the policy reference
  and never a principal (G3 (a), non-enumerating)
- Why: an eligibility refusal must be distinguishable in the audit from an
  identity failure, and must not teach a refused caller who could approve
- Migration: catch it at any door of your own and map it to
  `approver-not-eligible`; the shipped HTTP (403) and MCP doors already do

## ccf.hitl.ApproverNotEligible

- Surface: ccf.hitl.ApproverNotEligible
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export
- Why: same as above
- Migration: none — a re-export

## ccf.hitl.transport.HitlEventRevalidationRefused

- Surface: ccf.hitl.transport.HitlEventRevalidationRefused
- Public surface: true
- Change type: added
- Before: absent — the transport consumed the nonce and recorded against
  whatever was under the key at record time
- After: a `ValueError`-family (`GateActionError`-class) refusal raised under
  the recording lock when the SELECTED event or its state (`claimed` /
  `pending` / `missing`) differs from the snapshot the submission was judged
  against — a different event under the same key, a claim that appeared or
  vanished, an event that arrived where there was none. Nothing is consumed
  or recorded; the same attestation re-presented against the stable state is
  admitted once (`D-IMPL-366` §4b 6a; revision 2's nonce-first order is
  withdrawn). **Ratified (Dave, 2026-10-05, on the close panel's U1): it stays
  a `ValueError` sibling of `GateActionError`, not a subclass and not a
  `PermissionError`**
- Why: a submission judged against one event must not be recorded against
  another, and a refusal must not burn a legitimate nonce
- Migration: a door of your own maps it to a retryable refusal; the shipped
  doors return `hitl-event-revalidation-refused` (HTTP 409)

## ccf.hitl.HitlEventRevalidationRefused

- Surface: ccf.hitl.HitlEventRevalidationRefused
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export
- Why: same as above
- Migration: none — a re-export

## ccf.hitl.transport.APPROVAL_GATE_EVENT_CLASS

- Surface: ccf.hitl.transport.APPROVAL_GATE_EVENT_CLASS
- Public surface: true
- Change type: added
- Before: absent — the string lived only in `ccf.hitl.approval_gate.GATE_EVENT_CLASS`
- After: `"approval-gate"`, beside the `HITL_EVENT_CLASSES` roster: the ONE
  event class eligibility is judged for (RULED: approval gates only; the
  other three classes carry `requested_by` as data, G6 (a))
- Why: the transport dispatches on it and cannot import the primitive's
  module, which imports the transport
- Migration: none; `GATE_EVENT_CLASS` is the same string

## ccf.hitl.APPROVAL_GATE_EVENT_CLASS

- Surface: ccf.hitl.APPROVAL_GATE_EVENT_CLASS
- Public surface: true
- Change type: added
- Before: absent
- After: the `ccf.hitl` package re-export
- Why: same as above
- Migration: none — a re-export

## ccf.hitl.transport.EventStateAtSubmit

- Surface: ccf.hitl.transport.EventStateAtSubmit
- Public surface: true
- Change type: added
- Before: absent
- After: `Literal["claimed", "pending", "missing"]` — the state the transport
  found a submission's event in, stamped on the recorded submission (H2)
- Why: the H2 requirement is enforced on the RECORD, so the vocabulary is
  public
- Migration: none — a type alias for the new field

## ccf_runtime.http_api.errors.ERROR_APPROVER_NOT_ELIGIBLE

- Surface: ccf_runtime.http_api.errors.ERROR_APPROVER_NOT_ELIGIBLE
- Public surface: true
- Change type: added
- Before: absent — an ineligible approver was admitted with HTTP 200
- After: `"approver-not-eligible"`, the HTTP door's 403 and the MCP door's
  refusal-body code for `ApproverNotEligible`, distinct from the
  signed-binding family (G3 (a))
- Why: an eligibility refusal must be identifiable on the wire without
  naming who could have approved
- Migration: clients handling the HITL action door add this 403 code beside
  the four signed-binding codes

## ccf_runtime.http_api.errors.ERROR_HITL_EVENT_REVALIDATION_REFUSED

- Surface: ccf_runtime.http_api.errors.ERROR_HITL_EVENT_REVALIDATION_REFUSED
- Public surface: true
- Change type: added
- Before: absent — the condition did not exist
- After: `"hitl-event-revalidation-refused"`, the HTTP door's 409 and the MCP
  door's refusal-body code for `HitlEventRevalidationRefused`. **Ratified
  (Dave, 2026-10-05, on the close panel's U2)**: the code and the 409 stay
- Why: the client re-presents against the current event; it needs to know
  nothing was consumed
- Migration: clients treat it as retryable after re-reading the queue. A
  retry can legitimately return 200 with a receipt whose
  `submission.event_state_at_submit` is `"missing"` — the event was consumed
  between the refusal and the retry — and that submission authorizes
  nothing; read the receipt's field, not only the status

## ccf.hitl.transport.PendingHitlEvent

- Surface: ccf.hitl.transport.PendingHitlEvent
- Public surface: true
- Change type: reshaped
- Before: six fields — `event_key`, `event_class`, `tenant`,
  `workflow_state_ref`, `product_content_hash`, `policy_ref`; no field named
  who asked for the approval
- After: a seventh, `requested_by: str | None = None`, hash-transparent at
  `None`: the STARTER of the execution (G1 (a)), stamped by the engine at
  every gate suspension and carried as data on the other three classes.
  On a bound approval-gate event `None` is a fail-closed refusal (G5 (a))
- Why: requester ≠ approver cannot be judged without a recorded requester
- Migration: an event document written before this change renders
  byte-identically; a deployment that enqueues gate events itself sets
  `requested_by`, or its approvals are refused under a bound plane

## ccf.hitl.PendingHitlEvent

- Surface: ccf.hitl.PendingHitlEvent
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export with six fields
- After: the same class, with `requested_by`
- Why: same as above
- Migration: same as above

## ccf.hitl.transport.HitlActionSubmission

- Surface: ccf.hitl.transport.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: the recorded copy carried `hitl_policy_ref`,
  `answered_event_class`, `answered_workflow_state_ref` and
  `authorizing_decision_id` as transport stamps
- After: three more transport-stamped, hash-transparent fields —
  `approval_policy_ref` and `requested_by` (the event's, H3 (a)) and
  `event_state_at_submit` (`claimed` / `pending` / `missing`, H2). A
  caller-supplied value on any of the seven stamps is overwritten; a
  `missing`-state submission is recorded unjudged and never becomes
  authority, whatever is enqueued later
- Why: the door path's record must say which policy version and which
  requester the judgment used, and the engine must be able to exclude a
  premature submission structurally
- Migration: a submission recorded before this change rehydrates unchanged
  (`None` on all three keeps today's semantics); readers of recorded
  submissions gain three fields

## ccf.hitl.HitlActionSubmission

- Surface: ccf.hitl.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: the `ccf.hitl` package re-export with four stamps
- After: the same class, with the three new stamps
- Why: same as above
- Migration: same as above

## ccf_runtime.workflow.state.WorkflowStateRecord

- Surface: ccf_runtime.workflow.state.WorkflowStateRecord
- Public surface: true
- Change type: reshaped
- Before: seven fields; nothing recorded who started the execution
- After: `started_by: str | None = None`, hash-transparent at `None`: the
  `Execute` capability's principal, stamped once in `execute` and carried
  unchanged through every later record; copied onto every gate event as
  `requested_by` and judged against at resumption
- Why: the requester of a second gate reached by a different resumer is
  still the starter (G1 (a))
- Migration: a record persisted before this change rehydrates unchanged —
  and REFUSES at resolution under a bound plane (G5 (a)); re-run such
  executions after upgrading

## ccf.hitl.transport.InMemoryHitlTransport

- Surface: ccf.hitl.transport.InMemoryHitlTransport
- Public surface: true
- Change type: behavior
- Before: `submit` verified the capability, the principal and (when required)
  the attestation, consumed the nonce, popped the claim and recorded
- After: `submit` snapshots the selected event under the lock, judges approver
  eligibility for approval-gate events when a Control Plane is bound (BEFORE
  attestation, G2 (a)), verifies the attestation, then under one lock
  revalidates the event (6a), consumes the nonce, pops the claim and records
  with the three new stamps. A submission refused at any step leaves
  `_submissions`, `_claims` and `_seen_nonces` unchanged
- Why: `D-IMPL-366` §4b, the RULED ordering
- Migration: none for admitted submissions; an ineligible approver, a
  wrong-class policy or a changed event is now refused

## ccf.hitl.approval_gate.ApprovalGate

- Surface: ccf.hitl.approval_gate.ApprovalGate
- Public surface: true
- Change type: behavior
- Before: `resolve` verified the capability and the TOCTOU hash, then claimed
  and submitted
- After: with a Control Plane bound, `resolve` judges approver eligibility
  after the TOCTOU equality and BEFORE the atomic claim, raising
  `ApproverNotEligible` with the event still pending and `remove` never
  called
- Why: an ineligible resolution must not take the claim (`D-IMPL-366` §4 (4))
- Migration: callers of a bound gate handle `ApproverNotEligible` beside the
  signed-binding refusals

## ccf.workflow.factory.WorkflowFactory

- Surface: ccf.workflow.factory.WorkflowFactory
- Public surface: true
- Change type: behavior
- Before: `construct` resolved each `gate_policies` target and checked the
  step kind, accepting any artifact class
- After: each `gate_policies` target must be a key the Control Plane binds to
  `ccf.approval-policy`, or construction is refused by name — every
  pre-change `DeclaredArtifact` approval policy included (§4 (5))
- Why: fail-closed at the factory for every gate that NAMES a policy, so a
  workflow whose named gate policy nothing can judge never constructs.
  **Disclosure (D-IMPL-366 close panel 3.2; ruled 2026-10-05):** a routed
  `hitl-gate` with NO `gate_policies` entry still constructs; its event
  carries `policy_ref=None`, and under a bound plane every approval of it is
  refused, so that gate can never be passed. Fail-closed at runtime, not at
  construction. A construction-time refusal of a policy-less routed gate is
  carried as a follow-on, not widened into this repair
- Migration: a typed policy is a NEW key and a NEW workflow definition
  version (D-IMPL-366 close panel 3.3; ruled 2026-10-05). A Control Plane
  key already bound to the pre-change `approval-policy` declared class cannot
  be rebound to `ccf.approval-policy` — `register_typed` refuses the rebind —
  so register the typed policy under a new key, publish a new definition
  version whose `gate_policies` pins it, and start executions under that
  version. Pre-change executions do not resume: their definition hash pins
  the old policy and their state record carries no starter (G5 (a)). The
  banking fixtures register their typed policies in a fresh plane
  (`tests/fixtures/banking/approval_policies.yaml`), which is why they can
  reuse the historical keys; a live deployment cannot

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: `execute` recorded no starter; `_gate_authority` admitted any
  recorded verdict naming the suspension, stamped or (while the gate was
  pending) unstamped
- After: `execute` stamps `started_by` from the `Execute` principal and every
  gate suspension carries it as `requested_by`; the authority predicate
  judges eligibility per submission against `gate_policies[gate]` and the
  record's starter, excludes `missing`-state submissions unconditionally, and
  admits an unstamped submission only when recorded against a pending event
  (or pre-change) while the gate is still pending. `SEC-001` conflict
  detection is unchanged: `_recorded_gate_verdicts` is not narrowed
- Why: the engine is the backstop for every path (`D-IMPL-366` §4 (4), §4c)
- Migration: a suspension persisted before this change refuses at resolution
  (G5 (a)); re-run it
