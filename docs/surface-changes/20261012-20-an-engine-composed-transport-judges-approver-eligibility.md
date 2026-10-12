# 20261012-20 — a transport a workflow engine is composed over judges approver eligibility, so an ineligible principal cannot wedge a gate

Dave, 2026-10-12 08:45 MST (the improvement-batch GO, step 1), relayed recommendation, verbatim: *"Fix the HTTP
existence leak and enforce eligibility on supported approval transports. These address concrete exposure without
changing the working demonstrations."* The security close-out's map B item 3 (SEC-001-adjacent (f), `D-GATE-357` (2)):
on a transport constructed without a Control Plane, any `HitlSubmit` holder, eligible or not, could record the opposite
verdict and hold a gate for good. Its recorded acceptance: *"An ineligible opposite verdict is refused at submit and the
gate passes on the eligible approval."* Built red test first, with a severing
(`tests/workflow/test_conflict_population_eligibility.py`). **SEC-001 stays OPEN**: a conflicted gate still stays
suspended for good, an eligible approver can still hold one, and a verdict recorded while no event is under its key is
still recorded unjudged and still counts as a conflict (`D-IMPL-366` H2, unchanged). The conflict population is not
narrowed.

## ccf.hitl.transport.InMemoryHitlTransport

- Surface: ccf.hitl.transport.InMemoryHitlTransport
- Public surface: true
- Change type: behavior
- Before: an approval-gate verdict was judged for approver eligibility at `submit` only when a Control Plane was given at construction; a transport constructed without one judged nothing, including when a `WorkflowEngine` was composed over it.
- After: a new method, `bind_approver_eligibility(control_plane)`, adds a Control Plane that judges approval-gate verdicts at `submit` (each plane once, by identity). The planes that judge an `approve` or `reject` on an approval-gate event that names an approval policy are the construction plane, if any, and every bound plane; each must admit it, through the same `check_approver_eligibility`, before attestation, and a refused verdict records nothing (`ApproverNotEligible`; `approver-not-eligible` at both doors). `annotate` and `override`, and any action on an approval-gate event that names no policy (a gate the engine never passes, fail-closed under `D-IMPL-366`), are judged by the construction plane alone, as before. The HITL policy (signed bindings, the `hitl_policy_ref` stamp) still resolves only through the construction plane. A transport constructed without a plane and bound by no engine judges nothing, as before.
- Why: map B item 3; the batch GO above. Red tests: `tests/workflow/test_conflict_population_eligibility.py::test_an_ineligible_principals_opposite_verdict_is_refused_at_submit` (the former `test_an_ineligible_principals_opposite_verdict_still_holds_the_gate`, inverted as the acceptance records) and `::test_the_eligible_approval_passes_the_gate_after_the_ineligible_verdict_is_refused`.
- Migration: none for a deployment that binds a Control Plane at construction to the same plane its engine uses. On a transport constructed without one and composed into an engine, an `approve` or `reject` on an event that names an approval policy, by a principal that policy does not admit, by the requester, or where the policy is unresolvable or of the wrong class or the event names no requester, is now refused at submit instead of recorded. Such a verdict could never authorize passage.

## ccf.hitl.InMemoryHitlTransport

- Surface: ccf.hitl.InMemoryHitlTransport
- Public surface: true
- Change type: behavior
- Before: as for `ccf.hitl.transport.InMemoryHitlTransport`
- After: as for `ccf.hitl.transport.InMemoryHitlTransport`
- Why: as for `ccf.hitl.transport.InMemoryHitlTransport`
- Migration: as for `ccf.hitl.transport.InMemoryHitlTransport`

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: the engine composed any transport offering the whole `HITLTransportProtocol` with a declared scope, whether or not it judged approver eligibility.
- After: at construction the engine calls the transport's `bind_approver_eligibility` with its own Control Plane, and refuses, by name (`WorkflowWiringError`, "offers no bind_approver_eligibility"), a transport that offers none. The refusal precedes every binding, so a refused construction binds nothing. The method is not a member of `HITLTransportProtocol`: a transport the HITL primitives use without an engine need not offer it.
- Why: map B item 3; the batch GO above. Test: `tests/workflow/test_conflict_population_eligibility.py::test_an_engine_refuses_a_transport_it_cannot_bind_for_eligibility`.
- Migration: a third-party transport composed into a `WorkflowEngine` adds `bind_approver_eligibility(control_plane)` and judges every `approve` or `reject` on an approval-gate event that names an approval policy at `submit` with `ccf.hitl.transport.check_approver_eligibility` against that plane, before recording. The engine cannot see whether a transport that offers the method does so.
