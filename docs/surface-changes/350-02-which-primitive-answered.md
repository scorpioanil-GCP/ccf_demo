# 350-02 — the exception-routed resume is an authority path too, and a submission says which primitive it answered

`D-IMPL-350`, Tier 0 continued. The follow-up read of 2026-09-24 against the
shipped `SEC-001` remedy found two holes the first fix left, both in the same
place: `WorkflowEngine.resume`.

## What did NOT change, stated first

- **`ApprovalGate` is still untouched.** Its resolution path, TOCTOU guard,
  signed-binding enforcement and audit records are byte-identical. The engine
  reads the authority path; it never writes a verdict to it.
- **`ExceptionEscalation`'s behavior is unchanged.** It enqueues, claims and
  resolves exactly as before. Two inline `"exception-escalation"` literals
  became the named constant this module now exports; the value is the same
  string.
- **No workflow artifact schema changed.** No shipped workflow, task or agent
  document needs an edit.
- **A deployment that composes no escalation is unaffected.** The new
  exception-routed control is keyed on an escalation event *existing* on the
  transport, so a routed resume on a deployment that never composed the
  primitive behaves exactly as it did — pinned by
  `test_an_exception_routed_resume_without_escalation_is_unaffected`, which is
  a positive control as much as a compatibility claim.
- **`HITLTransportProtocol` gains no method.** `remove` and `submit` gain a
  contract obligation, not a signature.

## ccf.hitl.approval_gate.GATE_EVENT_CLASS

- Surface: ccf.hitl.approval_gate.GATE_EVENT_CLASS
- Public surface: true
- Change type: added
- Before: absent — `"approval-gate"` appeared as a bare literal at the two
  sites that produce it (`WorkflowEngine._suspend`) and consume it, outside
  the module that owns the vocabulary
- After: `"approval-gate"`, the `HITL_EVENT_CLASSES` member this primitive
  owns
- Why: the engine now has to ask *which* HITL primitive answered a
  submission. Reaching for a bare `"approval-gate"` literal in `/runtime`
  would put a vocabulary value outside its owning module — exactly the
  reasoning that put `GATE_APPROVE` here in `350-01`
- Migration: none. A new public constant naming a value that already existed

## ccf.hitl.escalation.ESCALATION_EVENT_CLASS

- Surface: ccf.hitl.escalation.ESCALATION_EVENT_CLASS
- Public surface: true
- Change type: added
- Before: absent — `"exception-escalation"` was an inline literal at the two
  sites in `escalation.py` that write and filter on it
- After: `"exception-escalation"`, the `HITL_EVENT_CLASSES` member this
  primitive owns, used by both of those sites and by the engine
- Why: the same reason as `GATE_EVENT_CLASS`, for the primitive on the other
  side of the new check
- Migration: none

## ccf.hitl.transport.HitlActionSubmission

- Surface: ccf.hitl.transport.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: six fields. A recorded submission said **what** a human did and
  **who** they were, and nothing about **which pending event** the action
  answered — so `WorkflowEngine._gate_authority` could not ask, and matched on
  `event_key` + tenant + product hash + `action in GATE_ACTIONS` alone.
  `GATE_ACTIONS` and `ESCALATION_ACTIONS` are the same two verdicts, so an
  action taken against an escalation that named the same event key satisfied
  an approval-gate check
- After: two optional fields, `answered_event_class` and
  `answered_workflow_state_ref`, **stamped by the transport and never by the
  submitter**. `submit` overwrites both from the event the transport itself
  observed being claimed through `remove`, and writes `None` when the
  submitter claimed nothing
- Why: a consumer of the authority path has to be able to ask "which
  primitive answered this, and about which execution?" and get an answer that
  the answerer did not author. Declared on the contract rather than kept in a
  transport side-table because the stamp has to travel with the action
  wherever the recorded submission travels
- Migration: none for a constructor — both fields default to `None` and any
  value a caller supplies is discarded at `submit` rather than rejected. A
  **third-party `HITLTransportProtocol` implementation must stamp**: one that
  does not leaves every submission reading `None`, and the engine's gate check
  then falls back to requiring the gate's own event to be still pending. That
  is fail-closed, which is the right direction, but it is a behavior change
  for such an implementation and it is why the obligation is written into the
  Protocol's `remove` and `submit` docstrings

## ccf.hitl.HitlActionSubmission

- Surface: ccf.hitl.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: the package-level re-export of the six-field contract above
- After: the package-level re-export of the eight-field contract above
- Why: `ccf/hitl/__init__.py` re-exports the name; the reshape is the same one
- Migration: none beyond the entry above

## runtime/ccf_runtime/workflow/engine.py

- Surface: runtime/ccf_runtime/workflow/engine.py
- Public surface: false
- Change type: behavior
- Before: **two holes.** (1) The branch after `if record.status ==
  "suspended":` — the exception-routed path — advanced with *no* authority
  check of any kind and audited `workflow_resumed, resolved=True, actor=None`,
  which is the exact audit signature `SEC-001` named, one branch over. The
  reading that justified it is in the `350-01` record: "the exception-routed
  resume path is unchanged. It crosses no gate, so it acquires no approver."
  That is true of `_route_exception`, which enqueues nothing — and false of
  the deployment, because `ExceptionEscalation` is the shipped primitive *for*
  a routed state and a deployment that composes it really does put a human in
  the loop the engine then walked past. (2) `_gate_authority` never asked
  which primitive a submission answered
- After: (1) a routed resume is refused while the transport holds a pending
  `exception-escalation` event whose `workflow_state_ref` is this execution's
  own state key, and the resolving human is the audit `actor` when one is
  found; (2) the gate check additionally requires that the submission answered
  an `approval-gate` bound to this execution — by the transport's stamp when a
  primitive claimed the event, and otherwise by joining to the gate's own
  still-pending event
- Why: `SEC-001`. The HITL pillar is sold on the claim that a human authorized
  the transition, and a control that holds on one branch of a two-branch
  method is not a control
- Migration: a deployment that composes `ExceptionEscalation` over a routed
  state must resolve the escalation before resuming — which is what the
  primitive is for, and what `tests/workflow/test_exception_paths.py` already
  did. A deployment that composes no escalation is unaffected

## APPLICABILITY IS THE FABRIC'S FACT, NOT THE CALLER'S — AGAIN

`350-01` ends on the lesson that "any guard whose *applicability* is
caller-determined is not a guard". Both new checks are written against it:

- The escalation check reads `pending(tenant=...)` and compares the event's
  own `workflow_state_ref` against a key derived from the tenant the artifact
  declares and the execution id the state store answered under. The resume
  caller supplies nothing that reaches it.
- The answered-class check reads a field the **transport** writes from its own
  `remove` observation and overwrites on every `submit`. A submitter that sets
  it has its value discarded. That is the whole reason the class is not simply
  carried on the submission as a caller-declared field: `ApprovalGate.resolve`
  removes the pending event before it submits, so the class has to come from
  something that watched the removal happen.

## TWO RESIDUALS, STATED SO NEITHER IS READ AS CLOSED

**1. The submit-only door is still weaker than a gate resolution.**
`POST /hitl/actions` is submit-only by ruling (`D-IMPL-62`): it records an
action and resolves nothing, so a submission made through it claims no event
and carries no stamp. The gate check therefore falls back to joining against
the gate's own still-pending `approval-gate` event. That path is not anonymous
— the door derives the principal from a verified token grant (`D-IMPL-67`) and
the suspension-hash binding still holds — but `ApprovalGate.resolve` never
ran, so its TOCTOU guard and its signed-binding enforcement did not either.

Closing it means giving the door a *resolve* route rather than a submit-only
one. That is a change to `D-IMPL-62`'s ruled contract plus
`runtime/ccf_runtime/http_api/routes/hitl.py`, and
`tests/http_api/test_routes.py::_approve_over_http` — which is today's
"put a human action on the authority path" helper and is exactly this
shape — would be rewritten to resolve through a real `ApprovalGate`. **Dave's
ruling, not the engine's.**

**2. Attribution on the exception-routed branch needs the documented
composition.** The resolver is named in the audit when the deployment hands
`escalate` the content hash of the routed `WorkflowStateRecord` — the
composition `product_content_hash`'s own docstring describes and the one
`tests/workflow/test_exception_paths.py` exercises. A deployment that binds
some other hash still cannot resume past an **open** escalation (that check
compares no hashes) but its resolver is not named. Losing an attribution is a
smaller defect than losing the control, and the alternative — naming whoever
last answered any escalation about this execution — would put a human's name
against a decision that may not be theirs.

**3. The claim is addressed, not held.** A claim is keyed
`(tenant, event_key)` and consumed by whichever submission for that pair
arrives first, because `submit` has no caller identity to bind it to. A
submitter that races the window `ApprovalGate.resolve` opens between its
`remove` and its `submit` takes the stamp. Closing it means `remove` minting
an opaque claim token that `submit` requires — a `HITLTransportProtocol`
signature change, and it belongs with the door ruling in residual 1. Recorded
because it **narrows** an existing hole rather than opening one: today the
same submitter is admitted by the unstamped fallback leg with no race at all.

## Regression evidence

`tests/workflow/test_engine.py`, six tests written first and watched fail
against the pre-fix engine:

- `test_a_pending_escalation_holds_the_exception_routed_resume` — observed
  advancing to `WorkflowSuspended` instead of refusing;
- `test_a_resolved_escalation_resumes_and_audits_the_resolver` — observed
  `actor=None`, the `SEC-001` audit signature;
- `test_an_exception_routed_resume_without_escalation_is_unaffected` — the
  positive control, green before and after, so the two above cannot be
  satisfied by an engine that refuses every routed resume;
- `test_another_executions_escalation_does_not_release_this_routing` —
  observed exec-1 resuming past its own open escalation;
- `test_an_escalation_resolution_is_not_an_approval_gate_verdict` — observed
  `WorkflowCompleted(approved)` on a duty officer's escalation verdict;
- `test_a_bare_submission_needs_this_gate_to_still_be_pending` — observed
  `WorkflowCompleted(approved)` on a submission joined to nothing.

## Sabotage verification

Four severings, each run alone, each reddening only the tests that own it:

1. **`_escalation_pending` forced to `False`** — reddens
   `test_a_pending_escalation_holds_the_exception_routed_resume` and
   `test_another_executions_escalation_does_not_release_this_routing`.
2. **`_escalation_authority` forced to `None`** — reddens
   `test_a_resolved_escalation_resumes_and_audits_the_resolver` alone, which
   is the point: it is the attribution half, and severing it must not hide
   the control half.
3. **The `answered_event_class` term dropped from `_gate_authority`** —
   reddens `test_an_escalation_resolution_is_not_an_approval_gate_verdict`
   and `test_a_bare_submission_needs_this_gate_to_still_be_pending`.
4. **`submit`'s stamp replaced by the caller's own values** — reddens
   `test_an_escalation_resolution_is_not_an_approval_gate_verdict`, which is
   the severing that proves the stamp is doing the work rather than the
   contract merely carrying a field.

The `workflow_state_ref` term of the escalation join is a **backstop that
cannot currently fail in isolation** and says so in its own docstring: the
routed record's content hash already separates any two executions. It is kept
because it is what a reader expects to see, and named so nobody counts it as
independent evidence.
