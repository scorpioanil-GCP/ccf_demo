# Controls register — the validation gates, the binder, and the consumer-side check

**What this page is.** The one place that says, for every control the SDK
advertises on the served path, **on which path it can actually fail and which
test turns red when it is removed**. A bank's assurance reviewer reads this page
to be pointed at the control that fails rather than at one that cannot
(`D-IMPL-364`, SEC-011 C2; the Gate 2 disposition at `D-IMPL-86`, `D-IMPL-300`
and `D-IMPL-358` D10). Every row cites a test by `path::name`. A docs test
(`tools/docs_tests/test_gate_assurance_surfaces.py`) refuses the page when a
`GATE_*` token defined in `src/ccf/products/gates.py` has no row or a cited test
does not resolve, so this page cannot quietly lag the module.

**How to read "can fail".** A control that compares a value with a copy of itself
cannot fail and is not a control (`D-IMPL-86`). The rows separate three cases: a
control that fails on the **governed path** (a live serve through
`GovernedResolver.__call__`); one that fails only when its runner is **called
directly**, because an upstream refusal makes its condition unreachable on the
governed path; and one that is **self-satisfying by construction** on the
governed path, kept for assembly-path integrity, with the failable control named
beside it.

## The gate tokens (`src/ccf/products/gates.py`)

The two runners' rosters are pinned by set equality at
`tests/products/test_structural_gates.py::test_both_runners_register_exactly_the_recorded_tokens`
(`RUN_GATES_TOKENS`, `RUN_FEDERATED_GATES_TOKENS`); the "registered by" column
below restates those rosters and the census is the measurement.

| token | registered by | what it refuses | path on which it can fail | the test that reddens it |
| --- | --- | --- | --- | --- |
| `empty-operator-guard` | `run_gates`, `run_federated_gates` | a product whose lineage names no operators | **Direct call only.** On the governed path the declared operator set is `required_operator_keys`, and both documents that declare it — `src/ccf/controlplane/artifacts.py::ProductClassDeclaration` and `src/ccf/controlplane/artifacts.py::ProjectionRequirements` — declare it with `min_length=1`, so an empty set is refused at artifact validation before any gate runs. The guard's own refusal is reachable only by calling the runner directly (`D-IMPL-364` SEC-011 C3). | `tests/products/test_empty_operator_halves.py::test_the_declared_half_refuses_a_product_that_declares_no_operators` |
| `lineage-strict-equality` | `run_gates` | a lineage whose operator set differs from the declaration's | **Self-satisfying on the governed path, by construction** (`D-IMPL-86` element 4; `D-IMPL-300`; `D-IMPL-364` SEC-011 B1): the engine runs exactly the operators the declaration names, so the gate verifies assembly-path integrity — the engine transcribed the plan — and cannot witness a misdeclaration. **The failable control is the pre-execution binder** in the next table. | `tests/products/test_gate_two_call_shape.py::test_no_call_site_fills_both_gate_arguments_from_one_source` (the one-source tripwire); the token's registration is pinned by `tests/products/test_structural_gates.py::test_both_runners_register_exactly_the_recorded_tokens` |
| `lineage-attributability` | `run_federated_gates` | a federated product whose signed-bytes address does not attribute its lineage | **Governed path, federated products.** Independently derived from the producer's signed bytes, so it can fail where strict equality cannot. | `tests/gates/test_federated_gates.py::test_attributability_is_checked_before_ttl` |
| `ttl-bounds` | `run_gates`, `run_federated_gates` | `expires_at <= served_at`, or `expires_at > served_at + MAX_TTL` | **Governed path.** The comparand is the fabric instant `served_at` (`D-IMPL-358` D3; `D-IMPL-364` SEC-011 A1), never the caller's; `MAX_TTL` is resolved from the Control Plane at gate time. | `tests/products/test_served_at_severings.py::test_severing_Gate_the_comparand_returns_to_the_decision_instant`; `tests/gates/test_product_gates.py::test_expiry_beyond_max_ttl_is_refused` |
| `ttl-anchor-unresolvable` | neither runner — minted in `src/ccf/products/expiry.py` where the entity-freshness anchor is resolved, before the gates run | an entity-freshness TTL anchor the record cannot resolve | **Governed path**, `from_entity_freshness` classes. | `tests/products/test_d_impl_341_ttl_anchor.py::test_c5_a_served_set_with_no_source_instant_refuses_by_its_own_reason` |
| `source-attestation` | `run_gates` | a pinned source below the class's accepted attestation modes | **Governed path.** | `tests/projection/test_attestation.py::test_run_gates_refuses_a_below_accepted_modes_pin` |
| `dependency-invalidation` | `run_gates` | a product that touched an entity superseded since it was derived | **Governed path.** | `tests/products/test_dependency_invalidation.py::test_a_product_that_touched_the_changed_entity_is_refused` |
| `declared-obligations` | `run_gates`, `run_federated_gates` | a lineage obligation the declaration names and the product dropped | **Governed path.** | `tests/products/test_structural_gates.py::test_a_declared_lineage_obligation_refuses_a_dropped_member` |

## The controls that are not gate tokens

| control | where | what it refuses | path on which it can fail | the test that reddens it |
| --- | --- | --- | --- | --- |
| the pre-execution binder, `refuse_operator_set_divergence` | `src/ccf/deployment/binder.py::refuse_operator_set_divergence`, called by the resolver before the plan executes | a class declaration whose operator set disagrees with the projection's own requirements artifact (`ccf.projection-requirements`); a second operator set from outside the Control Plane | **Governed path, before execution.** This is the control the lineage gate cannot be: it compares two independently authored documents. | `tests/products/test_resolver_seam.py::test_a_plan_contradicting_the_class_is_refused_before_it_is_executed`; `tests/deployment/test_binder.py::test_one_edited_operator_key_in_one_document_is_refused` |
| the consumer-side expiry check | `src/ccf/agents/agent.py::Agent.consume` | a product the consuming agent is handed that is TTL-expired at its `now`, from another tenant, or outside its contract | **The consume boundary.** `ttl-bounds` bounds the producer's hand-over; this is the consumer's own check at the instant it consumes (`D-IMPL-358` D9: both, named). | `tests/agents/test_agent.py::test_consume_refuses_an_expired_product_rather_than_degrading` |

## Approver eligibility — SEC-006 (`D-IMPL-366`)

Who may approve a gate is the pinned `ccf.approval-policy`'s statement
(`src/ccf/hitl/approval_policy.py::ApprovalPolicy`), judged by ONE helper,
`src/ccf/hitl/transport.py::check_approver_eligibility`, at every site a human
verdict can enter the authority path. Each site is an independent control:
severing one reddens the test named for it whether or not the other sites
still hold (the `D-IMPL-366` item-3 requirement). The requester is the
STARTER (`WorkflowStateRecord.started_by`, copied to every gate event's
`requested_by`), and requester ≠ approver is unconditional under a bound plane.

| control | where | what it refuses | path on which it can fail | the test that reddens it |
| --- | --- | --- | --- | --- |
| eligibility at the transport (S1) | `src/ccf/hitl/transport.py::InMemoryHitlTransport.submit`, after the capability and principal checks, before attestation | a door-shaped submission against an approval-gate event whose principal is not eligible, is the requester, or whose event names no, an unresolvable, or a wrong-class policy, or no requester | **The served path, both doors**: every HTTP and MCP action submission reaches `submit` with a bound plane. | `tests/hitl/test_sec006_eligibility_controls.py::test_t1_bound_transport_refuses_a_wrong_class_policy_ref`; `tests/hitl/test_sec006_eligibility_controls.py::test_t1_bound_transport_refuses_a_principal_outside_the_policy`; `tests/hitl/test_sec006_eligibility_controls.py::test_t1b_bound_transport_refuses_the_requester_approving_their_own_gate`; `tests/hitl/test_sec006_eligibility_controls.py::test_t1c_bound_transport_refuses_a_gate_event_with_no_requester` |
| the door mapping, HTTP | `runtime/ccf_runtime/http_api/routes/hitl.py` — `ApproverNotEligible` → 403 `approver-not-eligible` | the same refusal, rendered as the distinct non-enumerating code | **The HTTP door.** | `tests/http_api/test_sec006_eligibility_door.py::test_t2_the_http_door_refuses_an_ineligible_approval_with_the_ruled_code` |
| the door mapping, MCP | `runtime/ccf_runtime/mcp/hitl_server.py` — `ApproverNotEligible` → the refusal body with `approver-not-eligible` | the same | **The MCP door.** | `tests/mcp/test_sec006_eligibility_door.py::test_t2b_the_mcp_door_refuses_an_ineligible_approval_with_the_ruled_code` |
| eligibility at the primitive (S2) | `src/ccf/hitl/approval_gate.py::ApprovalGate.resolve`, after the TOCTOU equality, before the atomic claim | an ineligible resolution — with `remove` never called and the event still pending | **The primitive path**, with a bound plane. | `tests/hitl/test_sec006_eligibility_controls.py::test_t3_primitive_refuses_before_the_atomic_claim` |
| eligibility at the engine (S3, the backstop) | `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority`, inside the per-submission predicate, before the conflict count | a recorded verdict — stamped or door-shaped — from an ineligible principal or the starter, as authority for the suspension | **Every path**: the engine's plane is always bound, so a verdict that reached the record through an unbound transport is still judged here. | `tests/workflow/test_sec006_engine_controls.py::test_t4_an_ineligible_verdict_through_an_unbound_transport_does_not_resume`; `tests/workflow/test_sec006_engine_controls.py::test_t4_a_self_verdict_through_an_unbound_transport_does_not_resume` (positive control: `tests/workflow/test_sec006_engine_controls.py::test_t4b_an_eligible_non_starter_verdict_resumes`) |
| the factory class check (S4) | `src/ccf/workflow/factory.py::WorkflowFactory.construct`, for every `gate_policies` target | a gate policy whose key the Control Plane binds to anything but `ccf.approval-policy` — every pre-change `DeclaredArtifact` policy. A routed gate with NO entry is not refused here; it constructs and is refused at every approval (fail-closed at runtime; a construction-time refusal is a carried follow-on, ruled 2026-10-05) | **Construction.** | `tests/workflow/test_sec006_engine_controls.py::test_t5_a_declared_artifact_gate_policy_is_refused_at_construction` |
| the requester stamp (S5) | `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.execute` (`started_by`) and `_suspend` (`requested_by`) | nothing by itself — it is the fact the self-approval rule compares against; a second gate reached by a different resumer still names the starter | **Every suspension.** | `tests/workflow/test_sec006_engine_controls.py::test_t6_a_second_gate_reached_by_a_different_resumer_still_names_the_starter` |
| the typed policy (S6) | `src/ccf/hitl/approval_policy.py::ApprovalPolicy` | an empty `eligible_principals` at construction; manifest addressability of `ccf.approval-policy` | **Registration.** | `tests/hitl/test_sec006_eligibility_controls.py::test_t7_an_empty_eligible_set_is_refused_at_construction`; `tests/hitl/test_sec006_eligibility_controls.py::test_t7b_the_approval_policy_class_is_not_manifest_addressable` |
| the primitive-path record (R1) | `src/ccf/hitl/approval_gate.py::GateResolution.hitl_actions_block` carries the event with `requested_by` and `policy_ref` | a record that cannot say who the self-approval rule compared against | **Dimension 2.** | `tests/hitl/test_sec006_eligibility_controls.py::test_t8_the_resolution_block_carries_the_requester_and_the_policy_ref` |
| the door-path record (R2) | `src/ccf/hitl/transport.py::InMemoryHitlTransport.submit` stamps `approval_policy_ref`, `requested_by`, `event_state_at_submit` | a recorded submission that cannot say which policy version or requester judged it, or what state its event was in | **Every recorded submission.** | `tests/hitl/test_sec006_eligibility_controls.py::test_t9_the_recorded_door_submission_is_stamped_from_the_event`; `tests/hitl/test_sec006_eligibility_controls.py::test_carried_1_the_new_stamps_are_the_transports_not_the_callers` |
| the pin (R3) | `src/ccf/hitl/transport.py::check_approver_eligibility` resolves through `resolve_pinned`, never `resolve_latest` | a later policy version silently changing who may approve an already-suspended gate | **Every judgment.** | `tests/hitl/test_sec006_eligibility_controls.py::test_t10_eligibility_resolves_the_pinned_version_never_latest` |
| the revalidation before consumption (C) | `src/ccf/hitl/transport.py::InMemoryHitlTransport.submit`, under the recording lock, before the nonce | a submission whose selected event or state changed between snapshot and record; a nonce spent by a refused presentation | **Every recorded submission.** | `tests/hitl/test_sec006_eligibility_controls.py::test_t11_a_changed_queue_under_the_key_is_refused_and_mutates_nothing`; `tests/hitl/test_sec006_eligibility_controls.py::test_t14_the_nonce_survives_the_refusal_and_is_admitted_once_stable` |
| the missing state (M, the H2 requirement) | `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority` — the `event_state_at_submit != "missing"` conjunct and the unstamped leg's `in (None, "pending")` guard, removed TOGETHER for the required red | a submission recorded while no event was under its key, as authority after a later enqueue or re-enqueue; `SEC-001` conflict detection is unchanged | **Resumption.** | `tests/workflow/test_sec006_engine_controls.py::test_t12_a_missing_state_submission_is_not_authority_after_the_event_is_enqueued`; `tests/workflow/test_sec006_engine_controls.py::test_t12_a_missing_state_submission_is_not_authority_after_a_rollback_re_enqueue`; `tests/workflow/test_sec006_engine_controls.py::test_t12b_a_missing_state_verdict_still_counts_as_a_conflict` |
| eligibility BEFORE attestation (S1 ordering, G2 (a)) | `src/ccf/hitl/transport.py::InMemoryHitlTransport.submit` — the eligibility block precedes `enforce_attestation` | an ineligible, unsigned submission under a signed-required policy being refused for its signature rather than its eligibility | **The served path, bound transport.** | `tests/hitl/test_sec006_eligibility_controls.py::test_t1d_eligibility_is_judged_before_attestation` |
| the SEC-001 hash binding, beside eligibility | `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority` — `product_content_hash == suspension` | an ELIGIBLE approver's verdict over a hash other than the suspension's (the impostor control proves the ineligible path; this one proves the hash term) | **Resumption.** | `tests/workflow/test_engine.py::test_an_eligible_approvers_stale_hash_verdict_is_not_authority` |
| the escalation pin (E) | `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._escalation_authority` and `src/ccf/hitl/escalation.py::ExceptionEscalation.resolve` are NOT instrumented (RULED; the `D-IMPL-366` §9 follow-on) | nothing — the pin records that escalation eligibility is deliberately absent | **Exception-routed resumption.** | `tests/workflow/test_sec006_engine_controls.py::test_t13_escalation_resolution_judges_no_eligibility` |

## What this page does not claim

It does not claim Gate 2 can fail on the governed path; it says where that work
is done instead. It does not claim the empty-operator guard is exercised by a
served product; it says why it is not. It lists every `GATE_*` constant the
module defines, including the one no runner registers, so that a token with no
row cannot exist.
