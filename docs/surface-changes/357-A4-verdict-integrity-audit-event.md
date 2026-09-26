# 357-A4 — a verdict-integrity refusal is a distinct audit record

`D-IMPL-357` A4 (accepted design,
`docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md`
§3.1). Wave 1 Lane A. A1 declared `gate_routes`, A2 made the factory refuse
an incomplete map, A3 made the engine compare the caller's decision against
the declared route, and A4 closes verdict SELECTION: conflicting verdicts on
one suspension refuse the resumption.

The audit half is what this fragment records. Every resume refusal was
audited identically — same `workflow_resumed` action, `resolved=False`,
`actor=None`, and no reason on the event — so *"a caller tried to route a
recorded rejection down the approving branch"* was **byte-identical in the
log** to *"a caller mistyped the decision"*. For a bank that is the one
refusal an investigator would search for, and the log could not answer it.

## What did NOT change, stated first

- **`ccf.controlplane.audit.AuditEvent` gained no field**, so the canonical
  bytes of every pre-existing event are unchanged. That is the same reason
  `AuthzDecisionAuditEvent` is a derived class: the canonical serializer
  renders every declared field, and a field on the base would move the hash
  of events already on a deployment's log.
- **`AuditAction` gained no member.** A verdict-integrity refusal is still a
  `workflow_resumed` interaction — refusals travel in that member as
  `resolved=False`, exactly as before. One log, one `append`, no parallel
  surface (INV-CH7-71).
- **No refusal PROSE gained a verdict or a target.** `SEC-001` remedy 3
  stands: the refusal returned to the caller still names neither the recorded
  verdict nor the target the artifact routes it to. The audit plane is a
  different reader with a different entitlement, and that separation is the
  point of putting the fact there rather than in the reason string.
- **No existing call site of `AuditLog.append` changed shape.** Both new
  keywords default to `None`.

## ccf.controlplane.audit.WorkflowVerdictIntegrityAuditEvent

- Surface: ccf.controlplane.audit.WorkflowVerdictIntegrityAuditEvent
- Public surface: true
- Change type: added
- Before: absent. A `workflow_resumed` refusal caused by a recorded human
  verdict was an `AuditEvent` indistinguishable from any other refusal of
  the same execution — same action, same `resolved=False`, same `actor=None`.
- After: a derived event class carrying two fields —
  `workflow_verdict_integrity` (which rule refused) and
  `workflow_recorded_approver` (the approver whose recorded verdict the
  engine's selection rule reached). `AuditLog.append` returns one of these
  whenever `workflow_verdict_integrity` is supplied, and the workflow engine
  supplies it at exactly two sites: the route-disagreement refusal (A3) and
  the conflicting-verdicts refusal (A4). Both fields are hash-transparent at
  their sentinel (`ccf.contracts.canonical.HASH_TRANSPARENT_KEY`;
  `D-IMPL-243`, *"silence equals yesterday"*), so an event appended with
  either unset renders byte-identically to one appended before the class
  existed. The refusal row also carries the approver in the base `actor`
  field, so an investigator filtering the log by actor finds it — `resolved`
  is still `False`, because a refusal is not an attributed passage.
- Why: `SEC-001`. The remedy this vulnerability's own fix introduced is that
  a gate opens only on a recorded human action; the log then has to be able
  to say when a resumption was refused *because* of one. Recording nothing
  about the human made the log say less than the engine knew — the approver
  is a local in scope at both refusal sites.
- Migration: none. Existing readers of `AuditLog.events()` receive
  `AuditEvent` instances and these are `AuditEvent` subclasses; existing
  canonical hashes do not move. A reader that wants the new facts narrows on
  the class or reads the two fields.

## ccf.controlplane.audit.WorkflowVerdictIntegrityFailure

- Surface: ccf.controlplane.audit.WorkflowVerdictIntegrityFailure
- Public surface: true
- Change type: added
- Before: absent.
- After: a closed `Literal` with two members — `"route_disagreement"` (the
  caller's decision does not name the target the artifact declares for the
  recorded verdict) and `"conflicting_verdicts"` (more than one distinct
  verdict is recorded against one suspension, so no single recorded verdict
  can be routed on at all). Closed rather than free-form prose because an
  investigator queries a vocabulary, and `None` is the honest third state: a
  refusal no verdict-integrity rule produced must never claim one.
- Why: the same reason `AuthzFailingAxis` is closed — *"a deny says what it
  denied"* — applied to the gate. It also keeps the two rules distinguishable
  from each other, which matters because they mean different things about who
  is at fault: a route disagreement is about the caller, a verdict conflict
  is about two humans.
- Migration: none; a new exported type.

## Behavior claim — conflicting verdicts refuse the resumption

- Surface: ccf_runtime.workflow.engine.WorkflowEngine.resume
- Public surface: true
- Change type: behavior
- Before: `resume` selected the OLDEST qualifying submission and routed on
  it, so a rejection recorded after an approval was silently discarded.
  Measured through the served doors: submit approve, then reject on the same
  pending event, then resume claiming the approving decision, and the
  execution completed `approved` with the rejection standing (HTTP 200). The
  transport's stamp race reached the same terminal by a second route.
- After: `resume` refuses when more than one distinct `GATE_ACTIONS` verdict
  is recorded against this suspension, in either arrival order, ahead of the
  declared-target and route compares. The verdicts it counts are a
  deliberately BROADER population than the ones eligible to be the
  authority — every gate-action submission naming this gate's pending event
  and bound to this suspension's content hash, **stamped or not, eligible or
  not** — because the stamp race's recorded end state is one stamped verdict
  beside one unstamped opposite verdict, which an eligibility-filtered set
  sees as a single verdict and waves through.
- Why: `SEC-001`. A bank's answer to *two humans recorded opposite verdicts
  on one decision* is to stop and require reconciliation, not to resolve
  silently in favor of whichever verdict won a race.
- Migration: agreeing submissions carry one distinct verdict, so nothing that
  previously proceeded on agreement now refuses — a second approver recording
  the same verdict (D-23 quorum) is unaffected. A deployment that relied on a
  later verdict superseding an earlier one on the same suspension must now
  reconcile explicitly: there is no supersession rule, deliberately, because
  choosing one would be the fabric deciding which human to believe.
