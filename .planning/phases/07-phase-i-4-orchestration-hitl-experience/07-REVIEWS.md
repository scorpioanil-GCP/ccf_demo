---
phase: 7
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-07-30T13:15:23-07:00
plans_reviewed: [07-01-PLAN.md, 07-02-PLAN.md, 07-03-PLAN.md, 07-04-PLAN.md, 07-05-PLAN.md, 07-06-PLAN.md, 07-07-PLAN.md, 07-08-PLAN.md, 07-09-PLAN.md, 07-10-PLAN.md, 07-11-PLAN.md, 07-12-PLAN.md, 07-13-PLAN.md, 07-14-PLAN.md]
---

# Cross-AI Plan Review — Phase 7

## Gemini Review

# Phase I.4 Plan Review: Orchestration, HITL, Experience

## 1. Summary
The implementation plan for Phase I.4 is exceptionally rigorous, demonstrating deep alignment with the Cognitive Context Fabric whitepaper and a disciplined adherence to the architectural rulings of prior phases. The sequencing is strategically sound, prioritizing structural prerequisites (D-20 state-seam closure) and a vertical slice (D-01) to flush out integration risks early. The use of structural enforcement (tokens for audited writes, bidirectional import-ban lints for SDK isolation) and advanced verification (stateful property testing for the workflow engine) elevates the plan from a feature set to a robust systems engineering exercise.

## 2. Strengths
*   **Audit-by-Construction Enforcement:** The closure of the D-20 state-seam using both an ergonomic audited surface and a required token (modelled on the successful Phase I.3 admission token) ensures that "audit by construction" is a structural property, not a convention.
*   **Structural Isolation of Orchestration:** The implementation of D-06/D-IMPL-60 via separate module trees and a bidirectional import-ban lint prevents the SDK from absorbing harness-specific loops, preserving the "harness neutrality" mandate.
*   **Rigorous Replay Integration:** The plan follows the established "three-edit" pattern for Decision Replay extensions, ensuring that workflow traces and HITL actions land in the audit record without violating the 5-dimension invariant (INV-CH7-80).
*   **Vertical Slice First (D-01):** Exercising the engine, the closed state seam, a real HITL primitive, and the activation of CINV-04 checks in a single two-step workflow (Plan 07-07) is an excellent risk-mitigation strategy.
*   **Decision-Ready Escalations:** The plan identifies the one open semantic question (absent exception refs) and routes it to Dave as a `D-IMPL-NN` (Plan 07-01), rather than defaulting to a guess.
*   **Stateful Testing:** Applying `hypothesis.stateful` to the workflow engine (Plan 07-06) is the correct choice for a state machine with complex suspend/resume/exception interleavings.

## 3. Concerns
*   **Claude Agent SDK Topology Uncertainty (A2):**
    *   *Severity:* **MEDIUM**
    *   *Risk:* Unlike LangGraph or ADK, the Claude Agent SDK does not have a first-class DAG/topology surface. Plan 07-13's "A2 escalation rule" handles this honestly, but there is a risk that this leg requires significantly more effort or a different driver shape than initially envisioned.
*   **Sync/Async Bridging (B3 Deadlock):**
    *   *Severity:* **LOW**
    *   *Risk:* The CLI and certain test entry points are synchronous, while the engine and HTTP/MCP servers are async. While the plans cite the B3 finding and mandate avoiding `start_blocking_portal()`, the complexity of the three-front-door architecture increases the surface area for timing/deadlock issues.
*   **Skill Fixture Retrofit Size (D-16):**
    *   *Severity:* **LOW**
    *   *Risk:* Grep suggests the number of `SkillCatalogEntry` constructions across the tree is significant. Plan 07-03's Task 3 may be more time-consuming than its "Wave 1" positioning suggests, potentially delaying the slice.
*   **OpenAPI 3.1 Compatibility:**
    *   *Severity:* **LOW**
    *   *Risk:* FastAPI 0.140.0 emits OpenAPI 3.1. While this is the "valid OpenAPI spec" requested, certain older MCP or client tooling might expect 3.0. This is likely an external concern but worth noting for the "Success Criteria 4" validation.

## 4. Suggestions
*   **State Store Traversal Audit:** In Plan 07-02, ensure that `ControlPlaneStateStore.items` (used for set-identity folds) is also considered in the token/audit strategy if it becomes a vector for unaudited state observation or reconstruction.
*   **Workflow Cycle Detection:** Consider adding a `model_validator` to `WorkflowDefinition` (Plan 07-04) that checks for unreachable nodes or infinite loops in the transition graph (if the state machine is expected to be a DAG).
*   **HumanPrincipalBinding Content Hash Verification:** Ensure the tests in Plan 07-07 explicitly verify that `product_content_hash` matches the hash of the product version *at the time the approver saw it*, guarding against TOCTOU issues if the product is updated between the suspend and the human action.
*   **CLI --local Mocking:** For Plan 07-11's `--local` mode, provide a helper that allows easy injection of `InMemory` variants of the store/registry so the CLI can be used for rapid local prototyping without any infra.

## 5. Risk Assessment
*   **Overall Risk Level:** **MEDIUM**
*   **Justification:** The logic of the async-first workflow engine and its interaction with the Control Plane state seam is high-complexity. Integrating three external orchestrator SDKs (especially the Claude Agent SDK) introduces external dependency risk. However, the plan's **"Research-Strategy-Execution"** lifecycle, the **"Slice-First"** build order, and the **"Verification by Construction"** (lints/tokens) provide very strong mitigations. The "Stop and Escalate" rules for Dave (D-IMPL-61 and A2) ensure that semantic or integration blockers are resolved at the governance level rather than buried in code.

---

## Codex Review

## Summary

The plans are unusually strong on governance: they preserve the phase rulings, require counterfactual evidence, activate the replay invariants, and repeatedly guard against known I.3 failure modes. The main risk is not intent but executability. Several plans ask implementation-time validators or APIs to know things they may not have locally, and a few “by construction” claims still depend on Python runtime convention unless the token/audit surfaces are tightened. Overall, this is a good phase plan, but it is high-risk because Phase I.4 combines a workflow engine, HITL primitives, three front doors, and three orchestrator SDK legs in one gate.

## Strengths

- Clear phase sequencing: seam closure and D-IMPL-56 land before the workflow slice, front doors precede orchestrator legs, and the gate remains one phase / one approval.
- Strong evidence discipline: D-10/D-25 counterfactual outputs, adversarial tests, CINV-04 activation, and “rows from failing tests” are exactly the right standard.
- Good invariant awareness: multi-principal cases, no hardcoding, harness neutrality, replay dimension discipline, and role-separation lints are carried through most plans.
- The plans correctly preserve several sensitive boundaries: `TaskDefinition` remains untouched, LangGraph adapter internals are not generalized, HTTP avoids L1 ingestion, CLI is thin, and SKILL.md remains an authoring format.
- External SDK uncertainty is surfaced honestly, especially the Claude Agent SDK leg with a stop/escalate rule instead of silently narrowing D-IMPL-60.

## Concerns

- **HIGH: `WorkflowDefinition` validation may require data the schema does not have.** Plan 07-04 says validators confirm transitions and gate policies reference `TaskDefinition` step names, but the wrapper only has a pinned task-definition URI. Pure Pydantic validation cannot inspect the referenced artifact without a resolver. Split this into syntactic contract validation plus registry-backed artifact-load validation.

- **HIGH: The state-write token may overclaim “unrepresentable.”** Plan 07-02’s module-private token pattern is strong for public APIs, but Python cannot make construction impossible in an absolute sense. The docs and gate should say “unrepresentable through the public write surface/type contract” unless the implementation uses a robust private capability/nonce check.

- **HIGH: Audit semantics for state writes vs domain transitions are unresolved.** 07-02 says audited state writes append exactly one audit event, while `GrantLedger` already records grant transitions. Replacing transition events loses domain evidence; accompanying them may double audit entries and break existing assertions. This needs a precise rule before execution.

- **HIGH: Plan 07-04 is a dependency bottleneck for too much downstream work.** D-IMPL-61, workflow schema, principal binding, and HITL transport all land together. If identity binding or exception semantics stalls, the entire engine and HITL stack stalls.

- **HIGH: Plan 07-06 is very large.** It includes engine core, skill dispatch, agent-node resolution, audited suspend/resume, ArtifactStore trace write-through, replay integration, typed refusals, and stateful testing. This is likely the highest internal implementation risk before orchestrators.

- **HIGH: External orchestrator legs are still broad despite good stop rules.** 07-12/07-13 require real LangGraph, ADK, and Claude SDK topologies to drive the same workflow with replay equivalence. The Claude leg remains especially uncertain and could block the whole phase.

- **MEDIUM: Plan metadata has some dependency and file-list drift.** 07-05 is marked wave 1 with no dependency despite the roadmap placing it in Wave 2. 07-02 modifies `audit.py` but omits it from `files_modified`; 07-03’s fixture retrofit touches more than listed. This is the same class of planning defect D-24 warns about.

- **MEDIUM: `SkillArgumentSchema` design is under-specified.** 07-03 says “design fields from what the three adapters currently render,” but this is a canonical `/src` contract. The plan should define whether it is JSON Schema, a typed CCF schema model, or a constrained subset.

- **MEDIUM: HTTP and CLI share “same factories” by intent, not by named abstraction.** 07-10/07-11 should identify a shared dependency/provider layer so `--local` cannot accidentally become a privileged parallel path.

- **MEDIUM: Auth posture is accepted but may be too weak.** 07-10 allows in-trust-boundary/no-auth if stated honestly. That may satisfy v0 scope, but HITL and agent invocation are authority-bearing surfaces; the gate should explicitly mark this as residual deployment risk.

- **LOW: Several acceptance criteria use brittle grep/count checks.** Examples: exact baseline count `987 passed / 2 skipped`, `grep -c`, and “zero hits” checks may fail from harmless text changes. Prefer semantic tests where possible.

## Suggestions

- Add a named “artifact semantic validation” layer after 07-04: schema validates local shape; a resolver-backed loader validates step names, gate bindings, exception refs, and terminal reachability.
- In 07-02, define the audit event policy before coding: either domain transition event plus state-write event with tests updated intentionally, or a single event type that carries both transition and write evidence.
- Adjust D-22 wording in 07-02/07-07/07-08 to avoid absolute “no path” unless the implementation truly makes bypass impossible outside private reflection/test-only tricks.
- Split 07-06 internally into stricter milestones: engine transition core, HITL suspend/resume, trace ArtifactStore write-through, replay integration, then stateful testing.
- Make 07-10 create a shared service/dependency container used by HTTP and CLI `--local`, then require CLI tests to assert both paths call the same service object/factory.
- Fix plan metadata before execution: wave number for 07-05, `files_modified` omissions, and direct dependencies on 07-01 where pins or decisions are assumed.
- For 07-13, predefine the escalation artifact if Claude SDK cannot express the leg: expected evidence, attempted API surfaces, and exact D-IMPL question for Dave.

## Risk Assessment

**Overall risk: HIGH.** The plan quality is strong, but the phase scope is large and several core claims depend on subtle implementation details: audited state token enforcement, resolver-backed workflow validation, replay-by-construction HITL paths, and three real external orchestrator drivers. The plans likely achieve the phase goals if executed rigorously, but 07-06 and 07-13 are credible blockers, and 07-04/07-02 need tightening to prevent overclaiming.

---

## Cursor Review

# Phase 7 (I.4) Plan Review — Cursor

## 1. Summary

The 14-plan set is unusually strong: it tracks Dave’s rulings (D-01..D-26, D-IMPL-60/61), puts D-20 seam closure and D-IMPL-56 before the slice, banks front doors before orchestrator legs, and hardens “by construction” with token + counterfactual/adversarial proofs. Dependency order matches the hard prerequisites, reserved extension points are cited correctly against the tree, and out-of-scope items (examples 03/05/06, A3, Temporal) stay out. Residual risk is concentrated in three places: the **ApprovalGate dual face** (`ApprovalSink.decide` vs workflow suspend/resume), a likely **Task/Workflow factory construction gap** against ORCH-01 / D-IMPL-17, and **silent under-delivery of D-IMPL-45 `TraceCorrelationHook`** that I.3’s handoff assigned to I.4. Fix those in planning (not at the gate) and the set should achieve the four ROADMAP criteria.

---

## 2. Strengths

- **Ruling fidelity.** D-08 both-mechanisms, D-09 one-write-pattern, D-10 counterfactual+adversarial, D-11 wrapper / D-12 byte-identical `TaskDefinition`, D-06 module split, A2 escalate-don’t-narrow on Claude, and §3.1 STOP before `D-GATE-I.4` are all load-bearing and correctly placed.
- **Prerequisite sequencing.** 07-02 before any seam consumer; 07-03 before skill-binding nodes; 07-01 blocking checkpoint for D-IMPL-61 before 07-04; front doors (07-09..11) before 07-12/13 per D-02.
- **D-24 discipline already applied.** Research corrected the “8 grant call sites” myth; 07-02 plans against “every `put` caller” and re-grep at execution — verified: one textual writer at `grants.py:515`.
- **Evidence culture.** D-25 owning tests, verbatim red outputs in SUMMARYs/gate, CINV-04 flip with breakage proofs, D-22 scoped wording — matches I.3’s hard-won gate standard.
- **Symbol anchors mostly real.** `ControlPlaneStateStore.put` (no token), `_BINDING_CONTRACTS` (not `BINDING_BY_TYPE`), reserved `test_approval_sink` slot, CINV-04 skips at `:110`/`:119`, replay reservations at `record.py:25/159/184/262`, `HARNESS_ADAPTER_MODULES` at lint `:65`.
- **Orchestrator posture.** Separate `orchestration/<sdk>/` tree, bidirectional import ban + negative carve-out tests, CCF engine authoritative for state/audit, LangGraph checkpointer = graph position only — correctly encodes A7.
- **Scope control.** Fixtures in I.4 / examples in I.5, no L1 HTTP write door, no inbox UI, webhook notify-only separation preserved.

---

## 3. Concerns

### HIGH

- **ApprovalGate dual face underspecified (07-07).**  
  `ApprovalSink.decide(grant) -> ApprovalOutcome` is a **sync, grant-scoped** verdict with `approver_id: str`; the conformance suite **explicitly excludes** D-IMPL-21 binding (`test_approval_sink.py:12–14`). Workflow hitl-gate needs **async suspend**, transport enqueue, and `HumanPrincipalBinding`. Plan 07-07 asserts both faces on one type “with zero state-machine change” for grants, but never specifies how `decide()` behaves when the human has not yet acted (block? raise? return pending?). Risk: either break the reserved conformance bodies, or ship a sink that only works with a pre-scripted human — reintroducing I.2’s double under a new name.

- **ORCH-01 “via the Task Factory” not planned (07-04 / 07-06).**  
  D-IMPL-17 and success criterion 1 require workflow definitions as Control Plane artifacts **through the Task Factory**. Plans register `WORKFLOW_DEFINITION` and execute it in the engine, but never extend `TaskFactory` / add a `WorkflowFactory` / wire CINV-01c factory-bypass. `TaskFactory.construct` still ends at “nothing constructed here can execute.” Without an explicit factory path, No-Hardcoding enforcement for workflows is incomplete.

- **Criterion 2 (“no path… unrecorded”) vs actual enforcement (07-02 / 07-07 / 07-08).**  
  Token-gated state writes + CINV-04 activation prove capture on **exercised** paths. They do not prove **every** HITL resolve path is unrepresentable without replay. Per D-22 this must not be gate-worded as absolute “no path / by construction” unless types make unaudited actions unrepresentable end-to-end (including MCP tool → primitive → `build_replay_record`). Today the plans still risk overclaiming at 07-14.

### MEDIUM

- **D-IMPL-45 `TraceCorrelationHook` omitted.**  
  `PHASE_I3_GATE.md` §5: *“TraceCorrelationHook attaches to the harness_trace slot in I.4.”* CONTEXT parked placement as discretion; **no plan implements** `TraceCorrelationHook` / `ExternalTraceProviderProtocol` (even a no-op). 07-05 correctly refuses a sixth dimension / new slot, then stops. Either add a thin delivery task (hook + no-op provider + attach at existing dim-3 slot) or an **explicit I.5 deferral with Dave-visible rationale** — silent drop is a planning defect.

- **07-04 ↔ 07-08 ↔ 07-09 webhook ownership conflict.**  
  07-04 says 07-09 decides webhook v0 fate; 07-08 says decide in 07-08; 07-09 never mentions webhooks. Low individually, but D-IMPL-20’s secondary transport can fall through the cracks.

- **`SkillArgumentSchema` field design left open (07-03).**  
  “Design fields from what the three adapters currently render plus MCP inputSchema” is execution-time invention on a gated catalog contract. Prefer a must_have listing the concrete schema fields (or a spike task before Task 1) so adapters don’t diverge mid-plan.

- **Wave label vs `depends_on` for 07-05.**  
  Frontmatter `wave: 1` while CONTEXT called contracts “Wave 2.” Parallelism is fine (`depends_on: []`), but executors may mis-order relative to 07-04. Harmless if waves are advisory; confusing if tooling gates on wave number.

- **OrchestrationProtocol identity (07-12).**  
  “Engine structurally satisfies `OrchestrationProtocol`” vs “drivers implement `OrchestrationProtocol` by driving the engine” needs one sentence of doctrine. If both are true, the Protocol is the **caller-facing drive surface**; if only drivers implement it, the engine conformance test is wrong. Ambiguity will produce the wrong isinstance target.

- **HTTP noun set drift (07-10 / 07-11).**  
  D-IMPL-22 nouns include `product` and `config`; plan prose says `controlplane/config` and may under-emphasize `product`. Must_haves should grep-assert the ruling’s noun list, not a paraphrase.

- **ExceptionEscalation ↔ D_c wiring (07-08).**  
  Debt thresholds live in Control Plane artifact classes; there may be no single “escalation trigger” API yet. Plan correctly says grep-first, but underestimates design work to source D_c-shaped conditions without inventing thresholds in code.

### LOW

- **07-02 audit-event doubling.** GrantLedger already audits transitions; adding state-write audits risks duplicate journal noise. Plan flags the decision — good — but should pick a default in the plan (replace vs accompany) so executors don’t invent INV-CH7-71 interpretations.
- **07-06 hitl-gate before real ApprovalGate.** Engine suspends on hitl-gate in 07-06; real gate arrives in 07-07. Fine if 07-06 uses a transport stub / typed suspend handle only — state that explicitly so slice ownership is clear.
- **Claude orchestrator leg cost (07-13).** A2 stop-rule is correct; still the largest schedule risk under one-phase/one-gate (D-03).
- **FastAPI as core dep with ADK already constraining `fastapi>=0.133`.** Pin 0.140.0 is fine; note future ADK bumps may fight the pin — gate should record the constraint.

---

## 4. Suggestions

1. **Add an explicit ApprovalGate shape note to 07-07** (blocking for execution quality):
   - Face A: `ApprovalSink.decide` — sync, grant-only, may use a **non-suspending** path or a bound-in-memory decision for conformance (identity still out of suite scope).
   - Face B: workflow suspend API over `HITLTransportProtocol` + `HumanPrincipalBinding` — the CINV-04 / dim-2 owner.
   - If one class can’t honestly do both without lying to `decide()`, prefer **composition** (gate owns transport; a thin `ApprovalSink` adapter wraps a completed decision) and record the deviation from “joins with zero state-machine change” as property-preserving, not text-worship.

2. **Add a factory task** (07-04 or small 07-04b / front of 07-06): `WorkflowFactory` (or `TaskFactory` extension) resolves `ccf.workflow-definition` + wrapped `TaskDefinition` through Control Plane only; engine accepts only factory-built handles; CINV-01c / factory-bypass coverage extended. Satisfies ORCH-01 literally.

3. **Resolve TraceCorrelationHook in 07-05 or 07-14 prep:** either ship no-op `ExternalTraceProviderProtocol` + hook attaching into existing `harness_trace`, or a CONTEXT-level deferral sentence Dave already owns — do not leave I.3 §5 hanging.

4. **Single owner for webhook v0:** pick 07-08 (with SUMMARY deferral) **or** 07-09; delete the other pointer.

5. **Pre-specify `SkillArgumentSchema`** in 07-03 must_haves (e.g. JSON-Schema-shaped `properties`/`required`/`additionalProperties: false` matching MCP tool inputSchema) before adapter retrofit.

6. **Criterion-2 gate wording template for 07-14:** require each HITL primitive docstring + gate row to state *which* paths are type-unrepresentable vs lint/CI-covered; add one adversarial test per primitive family (MCP tool missing binding → refuse; resolve without dim-2 keyword → owning test red).

7. **07-12 doctrine line:** “`OrchestrationProtocol` is implemented by drivers (and an in-SDK reference adapter over `WorkflowEngine`); the engine is the authority the Protocol drives, not a third peer harness.”

8. **07-10 acceptance:** `assert set(noun_prefixes) == {agent, skill, workflow, hitl, replay, artifact, product, config}` (or exact D-IMPL-22/23 wording).

9. **Keep 07-02’s `grep` zero-raw-`put` criterion honest:** implementations of `put` inside `state.py` must remain; audited surface must be the only *caller* minting tokens — adjust the grep recipe so it can’t false-fail on the Protocol method definition.

---

## 5. Risk Assessment

**Overall: MEDIUM**

| Factor | Judgment |
|--------|----------|
| Phase goals coverage | Strong — ORCH/HITL/EXPR mapped to concrete plans with tests |
| Dependency graph | Sound — few false parallels; D-IMPL-61 correctly gates schema |
| Invariant / fidelity risk | Medium — dual-face gate + factory gap + TraceCorrelationHook omission |
| External unknown | Medium-High on Claude orchestrator leg; mitigated by A2 stop |
| Over-engineering | Low — Async engine, FastAPI, hypothesis stateful are justified |
| Security | Good STRIDE coverage; HTTP auth honesty and no L1 write door are right |
| Schedule (14 plans, one gate) | High effort, but sequencing banks criterion 4 before the hardest wave |

**Verdict:** Plans are ready to execute after addressing the three HIGH items (ApprovalGate shape, factory path, criterion-2 honesty) and explicitly disposing TraceCorrelationHook. No wave reorder needed. Do not treat “reserved conformance slot join” as proof that one object can be both a sync grant sink and an async workflow gate without a written composition rule.

---

### Plan-by-plan quick scores

| Plan | Risk | Note |
|------|------|------|
| 07-01 | LOW | Correct blocking checkpoint; pins justified |
| 07-02 | LOW–MED | Closure design sound; audit-duplication decision needed |
| 07-03 | MED | Schema field invention + large fixture sweep |
| 07-04 | MED | Factory gap; D-IMPL-61 dependent |
| 07-05 | LOW–MED | Pattern correct; TraceCorrelationHook silence |
| 07-06 | MED | Core complexity; stub hitl-gate vs real gate |
| 07-07 | **HIGH** | Dual-face + CINV-04 — phase hinge |
| 07-08 | MED | D_c / lineage symbol discovery; webhook owner |
| 07-09 | LOW–MED | Role separation + B3 — well constrained |
| 07-10 | LOW | FastAPI choice sound; noun-set align |
| 07-11 | LOW–MED | B3 + skill import boundaries clear |
| 07-12 | MED | Protocol doctrine + A7 lint — critical structure |
| 07-13 | **HIGH** | Claude expressibility; A2 stop is mandatory |
| 07-14 | LOW | Process correct; depends on honesty of prior evidence |

---

*Reviewer: Cursor (Ask-mode plan review). Verified against tree: `state.py:76/108`, `grants.py:515`, `catalog.py` `_BINDING_CONTRACTS`, CINV-04 skips, `test_approval_sink` reserved slot, `record.py` reservations, `HARNESS_ADAPTER_MODULES`, D-IMPL-17/20/21/22/23/45/55/56 text, `PHASE_I3_GATE.md` §5.*

---

## Ollama Review (gpt-oss:120b-cloud)

## Phase 7 Review – Orchestration, HITL & Experience (I.4)

### 1. Summary  
The eight‑wave plan set out in the `07‑*‑PLAN.md` files is an impressively detailed blueprint that respects every ruling in `CLAUDE.md` and the Phase I 3 gate.  The work is broken into small, test‑driven increments, each with clear “must‑have” truths, artifact links and acceptance criteria.  Core deliverables – the `WorkflowDefinition` wrapper, the async‑first workflow engine, the four HITL primitives, the three front‑door surfaces (MCP experience edge, HTTP API & CLI) and the three orchestrator driver legs – are all covered.  The plan also anticipates the required “by‑construction” guarantees (state‑seam token, CINV‑04 activation, replay‑dimension extensions) and the strict lint / import‑carve‑out discipline.  

Overall the plan is well‑aligned with the success criteria, but a few high‑impact gaps remain (especially the open decision on per‑node exception‑ref semantics, the feasibility of the Claude‑SDK driver, and the completeness of the security‑posture documentation for the HTTP API).  Addressing those items before the gate will be essential to avoid a last‑minute blocker.

---

### 2. Strengths  

- **Ruling‑driven structure** – every wave maps directly to a `D‑IMPL‑xx` decision; the plan never mutates an existing decision, it only adds new numbered entries (D‑07 compliance).  
- **Vertical‑slice first** – the slice (real `ApprovalGate` + suspend/resume) exercises the engine, state‑seam closure, HITL, and the two CINV‑04 skips in a single end‑to‑end test (D‑01).  
- **Test‑first, fixture‑first** – each wave creates a failing test (or counter‑factual test) before the implementation, guaranteeing that the code cannot be written “by accident”.  
- **Explicit lint enforcement** – the addition of `orchestration_imports` lint and the update to the harness‑import carve‑out prevents the “un‑guarded prefix” problem (D‑24).  
- **Replay‑extension pattern** – the three‑edit pattern (doctrine line, sentinel default, verbatim pre‑serialized block) is reused for dimensions 2, 4 and 5, ensuring invariants are enforced by the type system (D‑55).  
- **Clear dependency justification** – FastAPI and httpx are added as first‑class dependencies with a documented reason, avoiding hidden hand‑rolled OpenAPI generation.  
- **Orchestrator driver split** – the LangGraph driver is implemented first (lowest risk) and the ADK driver follows, giving early confidence before tackling the higher‑risk Claude SDK leg.  
- **Security‑by‑honesty** – the plan repeatedly notes the need for “by‑construction” vs “lint‑enforced” wording (D‑22) and for an explicit auth‑posture statement in the OpenAPI doc (D‑22, security domain).  

---

### 3. Concerns  

| # | Concern | Severity | Why |
|---|----------|----------|-----|
| C1 | **Open semantic D‑IMPL‑61** – per‑node exception‑ref handling is still undecided. If the decision is not recorded **before** `07‑04` is merged, the `WorkflowDefinition` contract may be built on an implicit assumption, violating D‑12 and D‑13. | HIGH | The entire engine’s exception routing (and the slice test) depends on this semantics. |
| C2 | **Claude‑SDK driver feasibility** – the plan assumes an end‑to‑end driver exists. If the SDK cannot express a suspend/resume surface, the leg will have to be escalated, which would break the “three real legs” ruling (D‑05). | HIGH | No concrete proof of concept is shown; a failure would require a new `D‑IMPL‑NN` and could force a re‑plan. |
| C3 | **State‑seam closure writer count** – research discovered only one raw `put` call, not the expected “8”. The plan notes the deviation but does not specify how the mismatch will be recorded in the gate summary (required by D‑24). | MEDIUM | If the count is not documented, the gate checklist may reject the plan for missing a “path‑defect”. |
| C4 | **Security posture of HTTP API** – the plan only mentions an “auth‑posture statement” but does not define what that posture is (e.g., “no auth, in‑trust boundary”). Without an explicit statement the OpenAPI doc may be inconsistent with the actual implementation, violating D‑22. | MEDIUM | Auditors may flag a discrepancy during the gate review. |
| C5 | **Two‑tenant isolation checks** – the state‑seam closure and engine tests each include a “two‑tenant” case, but the replay‑dimension tests (07‑05) do **not** include a multi‑tenant delegation‑chain test. | LOW | Missing coverage could be pointed out as an incomplete invariant. |
| C6 | **Potential import‑cycle in orchestrator lint** – the new `orchestration_imports` lint must also forbid imports *into* `ccf_runtime.orchestration` from adapters *and* the reverse direction. The plan describes this but does not provide a concrete test for the *reverse* direction (adapters → orchestration). | LOW | If missed, a future developer could accidentally create a prohibited import. |
| C7 | **CLI help text adherence to CINV‑01** – the plan states the help text describes mechanisms only, but no explicit check is listed (e.g., lint rule that forbids domain‑specific prose). | LOW | Could lead to accidental policy‑vocabulary leakage. |
| C8 | **Performance of async‑first engine + orchestrator drivers** – no benchmarks or load tests are scheduled. While not a correctness issue, low‑effort “high‑effort” drivers (Claude) could cause unacceptable latency. | LOW | May affect adoptability (success criterion 3). |

---

### 4. Suggestions  

- **S1 – Record D‑IMPL‑61 before any code touches `WorkflowDefinition`.** Add a pre‑flight checkpoint task (e.g., a tiny plan `07‑00‑DECIDE‑61`) that gathers Dave’s ruling, writes the entry to `DECISIONS.md` and verifies it exists with `git grep`. The subsequent `07‑04` implementation can then safely import the ruling.  
- **S2 – Prototype the Claude‑SDK driver early.** Before committing to the full driver, create a minimal “proof‑of‑concept” script that drives a two‑step workflow via `ClaudeSDKClient` and verifies suspend/resume. If this fails, raise a `D‑IMPL‑NN` and stop the leg; otherwise schedule the full driver. This reduces the risk of a last‑minute escalation.  
- **S3 – Capture the writer‑count deviation.** In `07‑02`’s counter‑factual test, output the observed writer count (`echo "Observed put call sites: 1"`). Add a row in the gate document (section 4) that records the deviation from the documented “8”. This satisfies D‑24.  
- **S4 – Make the HTTP API auth posture explicit.** In the FastAPI app’s `title`/`description` field, add a sentence such as “v0 deployment runs in‑trust‑boundary with no authentication; any future auth must be added as a new contract”. Add a test that inspects `app.openapi()["info"]["description"]` for that exact text.  
- **S5 – Add a multi‑tenant replay‑dimension test.** Extend `tests/replay/test_dimension_extensions.py` with a scenario that builds a replay record for a workflow executed by two tenants and asserts that both tenant IDs appear correctly in dimension 4 (delegation chain) and dimension 5 (step sequence).  
- **S6 – Add a reverse‑direction lint test.** In `tests/lints/test_orchestration_imports.py` add a case that tries to import a symbol from `ccf_runtime.adapters` inside a file under `ccf_runtime.orchestration` and expects a lint failure.  
- **S7 – Enforce CINV‑01 on CLI help.** Extend the CLI lint suite (or add a simple regex test) that forbids the presence of words that look like policy nouns (e.g., “policy”, “threshold”, “risk”) in any `argparse` `help=` strings.  
- **S8 – Light performance smoke test.** Add a tiny benchmark (e.g., `timeit` the engine’s `run` on a 10‑step workflow) in a new `tests/performance` module. Even a rough figure will give confidence that the async engine meets “adoptability” (hours vs days).  

---

### 5. Risk Assessment  

**Overall risk: MEDIUM‑HIGH**  

- **Primary risk drivers:** the unresolved `D‑IMPL‑61` decision (C1) and the uncertain Claude‑SDK driver (C2). Both are *gate‑blocking* issues; if either is delayed, the whole Phase I.4 gate will stall.  
- **Secondary risk drivers:** the state‑seam writer‑count mismatch (C3) and missing explicit auth‑posture (C4). These are likely to be caught during the gate sweep but can be remedied quickly if documented.  
- **Mitigating factors:** the plan’s strong test‑first approach, the explicit counter‑factual tests, and the staged orchestrator implementation (LangGraph → ADK → Claude) give early confidence and allow early detection of problems.  

**Conclusion:** Proceed with the plan **provided** the open decision on per‑node exception references (D‑61) and a concrete feasibility check for the Claude‑SDK driver are completed **before** `07‑04` and `07‑13` are merged. Once those are locked in, the remaining work fits comfortably within the constraints and should pass the Phase I.4 gate.

---

## Consensus Summary

Four independent reviewers (Gemini, Codex, Cursor, Ollama/gpt-oss:120b). Overall risk: Gemini MEDIUM · Codex HIGH · Cursor MEDIUM · Ollama MEDIUM-HIGH. All four judge the plan set unusually strong on governance, sequencing, and evidence discipline; risk concentrates in scope size and a handful of specification gaps.

### Agreed Strengths
- **Ruling fidelity and sequencing** (all 4): D-20 seam closure and D-IMPL-56 before the slice; front doors banked before orchestrator legs; one phase, one gate honored; D-IMPL-61 routed to Dave instead of defaulted.
- **Evidence culture** (all 4): counterfactual/adversarial tests (D-10/D-25), CINV-04 activation, verbatim red outputs for the gate document.
- **Structural enforcement** (all 4): state-write token modeled on the I.3 admission token; bidirectional orchestration/adapters import ban with D-24 negative tests; replay three-edit pattern preserving the five-dimension invariant.
- **Honest external-uncertainty handling** (all 4): Claude Agent SDK leg's STOP-and-escalate rule instead of silent narrowing.

### Agreed Concerns (2+ reviewers — highest priority)
1. **Claude Agent SDK driver feasibility (07-13)** — Gemini MEDIUM, Codex HIGH, Cursor HIGH, Ollama HIGH. Largest schedule/blocking risk; Ollama and Codex suggest an early proof-of-concept and a predefined escalation artifact (expected evidence, attempted API surfaces, exact D-IMPL question).
2. **"By construction / no path" overclaim risk on criterion 2 (07-02/07-07/07-08/07-14)** — Codex HIGH, Cursor HIGH. Python cannot make bypass absolutely unrepresentable; gate wording must state which paths are type-unrepresentable vs lint/CI-covered (D-22 honesty).
3. **07-04 WorkflowDefinition validation scope** — Codex HIGH (validators need a resolver to see referenced TaskDefinition step names; split syntactic vs registry-backed semantic validation), Cursor HIGH adjacent (ORCH-01 "via the Task Factory" has no explicit WorkflowFactory/TaskFactory-extension task — factory-bypass enforcement incomplete).
4. **07-02 audit-event semantics unresolved** — Codex HIGH, Cursor LOW-MED, Gemini adjacent: replace vs accompany GrantLedger transition events must be decided in the plan, not invented by executors.
5. **ApprovalSink dual face (07-07)** — Cursor HIGH (sync grant-scoped decide() vs async workflow suspend is unspecified; prefer composition), Codex adjacent via 07-06 size concern.
6. **Plan metadata drift** — Codex MEDIUM, Cursor MEDIUM: 07-05 wave label vs CONTEXT wave 2; files_modified omissions (audit.py in 07-02; 07-03 fixture sweep breadth).
7. **SkillArgumentSchema under-specified (07-03)** — Codex MEDIUM, Cursor MEDIUM: pre-specify the concrete schema shape (JSON-Schema-style properties/required/additionalProperties) before the adapter retrofit.
8. **D-IMPL-61 must be ruled before 07-04** — Ollama HIGH, Gemini/Cursor note the checkpoint exists and is correctly placed (concern is stall risk, not a gap).

### Divergent Views
- **Overall risk**: Codex rates HIGH (phase breadth: engine + HITL + three front doors + three orchestrator legs in one gate); the other three rate MEDIUM(-HIGH) citing the mitigations (slice-first, stop rules, evidence discipline).
- **07-06 engine plan size**: Codex wants it split into stricter internal milestones; others accept it as-is.
- **TraceCorrelationHook (D-IMPL-45)**: Cursor alone flags the I.3 handoff item as silently dropped — either a thin no-op delivery task or an explicit Dave-visible I.5 deferral; no other reviewer noticed.
- **Webhook ownership (07-04/07-08/07-09)**: Cursor alone flags conflicting pointers about which plan decides webhook v0 fate.
- **HTTP auth posture**: Codex marks accepted-but-weak as residual deployment risk for the gate; Ollama wants the exact posture sentence testable in OpenAPI info; others silent.
- **Performance**: Ollama alone suggests a light benchmark smoke test; no other reviewer sees performance as in-scope.

---

# Cross-AI GATE Review — Phase 7 deliverables (07-14, 2026-07-30)

Triage and dispositions: `docs/PHASE_I4_GATE.md` §7. Raw outputs verbatim below.

## Codex (gate review)

**Findings**

1. **BLOCKING** — [docs/DECISIONS.md](/home/parkave/ccf_code/docs/DECISIONS.md:28) / [docs/PHASE_I4_GATE.md](/home/parkave/ccf_code/docs/PHASE_I4_GATE.md:248): D-IMPL-20 still rules **two reference transports**, including webhook notify-only. The gate/design defer the webhook emitter from v0 without a new or amended D-IMPL entry. This is an unsurfaced decision and a missing ruled deliverable.

2. **BLOCKING** — [docs/DECISIONS.md](/home/parkave/ccf_code/docs/DECISIONS.md:31) / [runtime/ccf_runtime/http_api/app.py](/home/parkave/ccf_code/runtime/ccf_runtime/http_api/app.py:55): D-IMPL-23 says the HTTP API adds “auth hooks”; the shipped API explicitly performs **no authentication or authorization**, and the gate treats future auth as “a new contract.” That changes a ruled surface without a D-IMPL entry.

3. **BLOCKING** — [docs/DECISIONS.md](/home/parkave/ccf_code/docs/DECISIONS.md:29) / [runtime/ccf_runtime/http_api/routes/hitl.py](/home/parkave/ccf_code/runtime/ccf_runtime/http_api/routes/hitl.py:43) / [runtime/ccf_runtime/mcp/hitl_server.py](/home/parkave/ccf_code/runtime/ccf_runtime/mcp/hitl_server.py:210): D-IMPL-21 calls for identity binding via the IdentityProvider family plus reference impls from HTTP/MCP auth context and JWS. The implementation accepts caller-supplied principal fields; MCP token identity is not bound to `subject_id`, and HTTP has no auth context. Gate row 7 proves field presence, not identity binding.

4. **BLOCKING** — [docs/PHASE_I4_GATE.md](/home/parkave/ccf_code/docs/PHASE_I4_GATE.md:99) / [tests/invariants/test_replay_by_construction.py](/home/parkave/ccf_code/tests/invariants/test_replay_by_construction.py:103): Row 7/CINV-04 claims “every HITL action — approval, escalation, override, review — lands in replay dimension 2.” The named owning replay test is the ApprovalGate workflow slice; escalation/override/review tests assert their pre-serialized blocks, not a replay append. This claims more than the named test enforces for ROADMAP criterion 2.

5. **BLOCKING** — [src/ccf/hitl/__init__.py](/home/parkave/ccf_code/src/ccf/hitl/__init__.py:14) / [tests/invariants/test_replay_by_construction.py](/home/parkave/ccf_code/tests/invariants/test_replay_by_construction.py:105): D-22 discipline is not contained to marked quotations/scoped rows. The package docstring asserts absolute “no path,” and the CINV registry asserts “every … by construction” for HITL/workflow. The gate’s D-22 sweep does not cover these load-bearing cited artifacts.

6. **ADVISORY** — [.planning/REQUIREMENTS.md](/home/parkave/ccf_code/.planning/REQUIREMENTS.md:115): Phase 7 ORCH/HITL/EXPR boxes are ticked, but Phase I CI invariant rows remain unchecked/pending, including CINV-04, despite the gate claiming the deferrals are discharged and zero skips. Planning-status staleness, not a Phase 7 criterion miss.

## Cursor (gate review)

## Phase I.4 Gate Review — Triage

**Verdict: not gate-ready.** Several BLOCKING items: Experience HITL bypasses primitives/replay, gate rows overclaim CI coverage for all four HITL primitives, and DESIGN §5’s structural audit argument still does not match what shipped. Suite green / mypy / lints are necessary and appear satisfied as stated; they do not discharge these defects.

---

### BLOCKING

1. **HTTP/CLI HITL action path records a bound human action with no primitive resolve and no Decision Replay dim-2 landing.** `POST /hitl/actions` only calls `hitl_transport.submit` (`runtime/ccf_runtime/http_api/routes/hitl.py`); CLI `hitl decide` is the same route (`runtime/ccf_runtime/cli/commands/hitl.py`). No `ApprovalGate`/`OverrideBoundary`/… `resolve`, no `build_replay_record`. Tests assert transport presence only (`tests/http_api/test_routes.py`, `tests/cli/test_cli.py`). Contrasts with MCP HITL child, which does gate.resolve + replay write (`tests/crossproc/servers/mcp_hitl_child.py`). Attaches to: ROADMAP Phase 7 criterion 2; CLAUDE.md §8.2; gate rows 15–16 (silent on this gap); D-IMPL-20 (“serves … the `ccf hitl` CLI”).

2. **`WorkflowEngine.resume` advances on a bare `decision: str` with no required prior HITL resolution or action record.** `runtime/ccf_runtime/workflow/engine.py` `resume()`; HTTP `/workflow/.../resume` mirrors it. DESIGN.md §5 structural arg #2 (“transitions state only when the Workflow primitive receives a validated action record”) is false as shipped; gate §4.6 did not correct it. Attaches to: DESIGN.md §5; CLAUDE.md §8.1/§8.2 composition; criterion 2.

3. **Gate row 7 / CINV-04 overclaim capture completeness for all four HITL primitives.** Row 7 says remaining dim-2-write paths are guarded by CINV-04 owning test + “per-primitive dim-2 byte-equality tests.” CINV-04 `hitl-action-capture` invariant text names “approval, escalation, override, review” (`tests/invariants/test_replay_by_construction.py`) but owning + adversarial tests are ApprovalGate/`test_slice` only. Override/Escalation/Review tests assert `hitl_actions_block == canonical_bytes(record)` and AuditLog — they never call `build_replay_record`. Attaches to: `docs/PHASE_I4_GATE.md` row 7; CINV-04 registry; `tests/hitl/test_{override,escalation,review_queue}.py`.

4. **Gate row 6 claims exception-path “resolution on dim 2”; named test does not land dim 2.** `tests/workflow/test_exception_paths.py` asserts `resolution.hitl_actions_block` truthy and later dim-5 contents — no `build_replay_record` / dim-2 equality. Attaches to: `docs/PHASE_I4_GATE.md` row 6.

5. **DESIGN.md §5 structural arg #3 (“Replay write precedes state transition”) remains asserted and is not enforced.** Engine resume and HTTP resume do not require a prior replay append; primitives return a block for optional caller threading. Gate §4.6 listed four DESIGN corrections and omitted this. Attaches to: DESIGN.md §5 items 2–3; CLAUDE.md §11 write-time replay.

6. **D-IMPL-20 still commits two reference transports (incl. webhooks); v0 webhook emitter deferred only in SUMMARY/DESIGN correction, with no DECISIONS amendment.** `docs/DECISIONS.md` D-IMPL-20 text unchanged; gate §4.2 / DESIGN Phase I.4 correction narrow delivery scope without a new `D-IMPL-NN`. Attaches to: D-IMPL-20; gate §4.2; DESIGN.md §5 Transport.

7. **INV-CH7-68 debt cascade at AgentNode handoffs still listed as an enforced Workflow invariant; not implemented and not D-IMPL-deferred.** DESIGN.md §4 (“Debt cascade honored across handoffs”); engine has no `assess_debt` / fail-closed handoff path; gate §4.6 corrections omit it. Attaches to: DESIGN.md §4; whitepaper INV-CH7-68; unsurfaced deferral.

---

### ADVISORY

8. **Absolute “unbypassable” wording outside a marked quotation.** Gate §4.2: “audit-by-construction unbypassable from a notification channel” — conflicts with the document’s own D-22 / §4.7 discipline. Attaches to: `docs/PHASE_I4_GATE.md` §4.2.

9. **REQUIREMENTS evidence-map row mis-citation.** `.planning/REQUIREMENTS.md`: ORCH-01 → rows 1–5 (omits row 6); HITL-01 → rows 6–10 (row 6 is ORCH/D-IMPL-61). Gate §3 mapping is correct; REQUIREMENTS ticks cite the wrong rows. Attaches to: `.planning/REQUIREMENTS.md` ORCH-01/HITL-01.

10. **D-IMPL-18 `variable_bindings` dropped from `WorkflowStateRecord` without a DECISIONS amendment** (openly noted in gate §4.6 / DESIGN correction — better than silent, still a ruling-text drift). Attaches to: D-IMPL-18; `runtime/ccf_runtime/workflow/state.py`.

11. **DESIGN Transport blurb still says MCP “serves … the `ccf hitl` CLI”; shipped CLI is HTTP-thin-client, not MCP.** DESIGN.md §5 Transport after I.4 correction vs D-IMPL-22 / `cli/commands/hitl.py`. Attaches to: DESIGN.md §5; D-IMPL-20/22 tension.

12. **ROADMAP criterion 4 / EXPR-01 “MCP egress” vocabulary vs shipped Experience-role server** (`ccf-experience-product://`). Functionally aligned with I.3 A5 amendment; wording still drifts. Attaches to: `.planning/ROADMAP.md` Phase 7 SC4; EXPR-01.

13. **Accepted residuals already disclosed (carry forward, not new blockers):** T-07-24 unauthenticated HTTP (gate §4.1); unaudited `ControlPlaneStateStore.items` reads (gate §5); `SequentialAgent` deprecation (gate §5); examples 05/06 deferred to Phase 8 per D-04 (gate §1.1) — consistent with Phase 7 SC given D-04.

---

### What holds (non-findings)

- Harness neutrality in `/src` for workflow/HITL/orchestration contracts: no harness imports observed; agent nodes via injected `AgentNodeBinding`.
- Single-writer front-door leg: HTTP holds no graph/L1 ingest path (`http_api/app.py`; route tests).
- No-Hardcoding / factory path for workflows: `WorkflowFactory` + CINV-01c as row 1 states; agent/skill/HITL-gate kinds exercised (e.g. covenant fixture + engine tests).
- OrchestrationProtocol four-leg conformance surface and d06 split: present as claimed (not re-executed here; user-verified suite green relied on).
- Gate D-22 header discipline is mostly followed; failures are the overclaims and the Experience HITL hole above, not a blanket absolute “no path” in criterion-2 rows.

---

**Dave ask:** treat findings 1–7 as must-fix before `D-GATE-I.4`. Highest leverage: wire HTTP/CLI HITL through the same primitive+replay composition MCP already demonstrates (or remove/refuse raw `transport.submit` as an authority surface), couple or honestly re-scope DESIGN §5 structural args + D-IMPL-20/18 text, and narrow row 7 / CINV-04 to the paths tests actually red under.

---

# Cross-AI POST-EXECUTION Review — Phase 7

reviewed_at: 2026-07-30T18:22:32-07:00
reviewers: [gemini, codex, cursor, ollama gpt-oss:120b-cloud]
scope: all 14 plans + docs/PHASE_I4_GATE.md (as-built state, post D-GATE-I.4 merge)

## Gemini Review (post-execution)

# Cross-AI Review — Phase 7 (Post-Execution): Orchestration, HITL, Experience

## 1. Summary
Phase 7 (I.4) successfully delivers the high-level coordination and interaction surfaces of the CCF SDK. The execution demonstrates exceptional architectural discipline, particularly in the structural separation of orchestration and adapter module trees and the "audit-by-construction" closure of the Control Plane state seam. The transition from the I.3 baseline to a functional multi-agent system with human gates was achieved through a rigorous TDD approach, resulting in a zero-skip test suite of 1280 cases. The phase effectively discharges the deferred Experience MCP edge and manages the significant external risk of the Claude Agent SDK driver through an early feasibility probe. The resulting fabric is now reachable via CLI, HTTP, and MCP, while maintaining strict fidelity to the whitepaper's single-writer and Decision Replay invariants.

## 2. Strengths
*   **Structural Integrity of Seams:** The bidirectional import ban between `ccf_runtime.orchestration` and `ccf_runtime.adapters` (D-06) is a masterclass in preventing "loop absorption." By making the LangGraph adapter's topology unreachable from the engine, the SDK successfully avoids shipping a loop it committed to never shipping.
*   **Honest Contract Hardening (D-IMPL-62):** The decision to make the HTTP/CLI HITL doors "submit-only" with a `Literal["submitted"]` status receipt is a high-signal design choice. It prevents the API from lying about state transitions that it does not own, forcing resolution to happen through the primitive's own governed logic.
*   **State Seam Closure (D-08/D-20):** The implementation of `StateWriteToken` and `AuditedStateWriter` transforms a "convention" into a "structure." Requiring a token that only the audited writer can mint ensures that no Control Plane state can change without a corresponding Audit Log entry, earning the "by construction" claim.
*   **Replay Fidelity:** The use of verbatim pre-serialized blocks for dimensions 2 and 5 prevents "recording-time vs decision-time" observation drift. The five-dimension structural assertion (INV-CH7-80) ensures no contract creep occurs during extension.
*   **Exhaustive Validation:** The `hypothesis.stateful` suite for the `WorkflowEngine` and the four-leg orchestrator conformance suite (D-IMPL-60) provide high confidence in the SDK's ability to coordinate agents across diverse external SDKs without leaking CCF state into foreign checkpointers.

## 3. Concerns
*   **Unauthenticated HTTP Surface (Residual Risk):** **Severity: MEDIUM.** While disclosed and accepted as an in-trust-boundary deployment, the HTTP API currently exposes all authority-bearing surfaces (workflow invocation, HITL submission) without authentication. In a v0 context this is acceptable, but it places a heavy burden on the deployment environment to prevent unauthorized fabric access.
*   **Propagate-to-Terminal Defaults (D-IMPL-61):** **Severity: LOW.** The choice of "propagate-to-terminal" for missing exception refs is fidelity-conservative, but it introduces the risk that an author forgets a handler and the workflow terminates on the first failure. The audit trace mitigates this, but it remains a potential friction point for adoptability.
*   **Sub-agent Deprecation in ADK:** **Severity: LOW.** The deprecation of `SequentialAgent` in Google ADK 2.5.0 is a minor technical debt item. While migration is noted as mechanical, it signals the start of the "SDK maintenance" phase where CCF must track upstream SDK drift.

## 4. Suggestions
*   **Decision Replay Explorer:** Given that dimensions 2, 4, and 5 now carry complex verbatim blocks (HITL actions, delegation chains, step sequences), a dedicated CLI verb (e.g., `ccf replay explain <hash>`) that parses and visualizes these transitions would significantly improve the developer experience for audit forensics.
*   **Workflow Visualization:** Since `WorkflowDefinition` is a pure state machine, a `ccf workflow export-graph <uri>` command that generates a Mermaid or DOT diagram from the artifact would help authors verify their reachability and terminal conditions visually.
*   **HTTP Auth Hook Template:** To mitigate the MEDIUM risk above, Phase 8 could include a "FastAPI Auth Hook" reference in the examples, demonstrating how to wrap the v0 API with an OIDC or API-key provider without changing the SDK core.

## 5. Risk Assessment
**Overall Risk: LOW.**
The phase has successfully navigated its largest technical and external risks. The "blocking" findings from the cross-AI review were effectively triaged into rulings (D-IMPL-62..65) that prioritized structural honesty over convenience. The zero-skip test suite and strict CINV lints ensure that the fabric remains invariant-compliant. The residual risks are either accepted deployment-level considerations or scheduled technical debt. The system is stable, well-documented, and ready for the Phase 8 validation exercises.

---

## Codex Review (post-execution)

## Summary

Phase 7 appears well planned and largely well executed: the plans are unusually explicit about invariants, decision rulings, counterfactual tests, and evidence boundaries, and the gate document shows real post-review correction rather than rubber-stamping. The implementation seems to meet the phase goals on paper: workflow execution/suspend/resume, four HITL primitives, replay extensions, three front doors, and orchestration drivers are all mapped to tests. The main residual risks are not implementation breadth but trust-boundary weakness and evidence freshness: the supplied gate text still says `D-GATE-I.4` is unwritten and awaiting Dave’s approval, while the request says the phase was gated and merged. I could not independently inspect the repo due a local sandbox failure (`bwrap: loopback: Failed RTM_NEWADDR`), so this review is based on the supplied plans and gate package.

## Strengths

- Strong phase discipline: every major ambiguity became a named `D-IMPL` ruling rather than an implicit executor default.

- Good fidelity to prior gate findings: D-20 state seam closure, D-22 scoped wording, D-24 path/symbol skepticism, and D-25 “rows from failing tests” were all carried into planning and execution.

- The TDD/counterfactual pattern is excellent. Recorded reds for state seam closure and CINV-04 replay captures materially improve confidence.

- Good separation of contracts and runtime implementation: `/src` protocols/contracts vs `/runtime` drivers/front doors mostly follows the project architecture.

- HITL wording was narrowed after review. The final gate avoids overclaiming “no path” and distinguishes type-unrepresentable paths from CI-covered paths.

- The plan correctly avoided slipping examples into Phase 7. Tests prove mechanism; examples remain Phase 8 packaging.

- The orchestration/adapters split is well designed. Bidirectional import lints and negative tests are the right answer to the LangGraph topology absorption risk.

## Concerns

- **HIGH: Gate evidence appears stale or internally inconsistent.** The prompt says the phase was gated and merged, but the supplied gate document repeatedly says `D-GATE-I.4` is deliberately unwritten and awaiting Dave’s approval. If the document is the final artifact, the phase is not actually gated per its own protocol. If the phase was later approved and merged, the gate package should include the approval entry, merge commit, and post-merge `main` sweep.

- **HIGH: HTTP API unauthenticated posture is a real security risk.** The gate records this honestly, but the risk is substantial because workflow invocation and HITL submission are authority-bearing. “Deploy inside the tenant trust boundary” is acceptable for a skeleton only if the default hosting path makes accidental exposure difficult.

- **HIGH: D-IMPL-63 identity binding deferral weakens HITL guarantees.** Requiring `HumanPrincipalBinding` by type prevents anonymous actions, but caller-supplied principal fields are spoofable without auth-context-derived or signed bindings. Combined with unauthenticated HTTP, this is the sharpest residual trust gap.

- **MEDIUM: HTTP/CLI HITL submit-only semantics remain easy to misuse.** `ccf hitl decide` and `POST /hitl/actions` submit but do not resolve. The receipt hardening is good, but the user-facing verb can still imply a completed authority decision.

- **MEDIUM: Non-ApprovalGate HITL replay coverage is compositional, not end-to-end.** The narrowing is honest, but escalation, override, and review queue could still have integration bugs between primitive output and replay construction that only a full path would catch.

- **MEDIUM: Orchestrator “real leg” evidence is still bounded.** The Claude leg uses real SDK session machinery but a scripted in-process wire, no model, no network, and no CLI. That may be the correct deterministic test shape, but it should not be read as production SDK behavior coverage.

- **MEDIUM: D-IMPL-65 leaves an engine-level guard to Phase 8.** Composition-root wiring closes this gate, but alternate composition roots could bypass the intended debt-assessment precondition until the engine itself refuses unbound handoffs.

- **LOW: Exact dependency pins may create near-term resolver friction.** The FastAPI/google-adk compatibility note is correctly recorded; this is acceptable but should be expected to surface again.

- **LOW: The gate document has some superseded wording noise.** The webhook deferral section is corrected later by D-IMPL-64, but the document still carries “deferred” language in places. It is explained, but it increases review load.

## Suggestions

- Add a final post-merge addendum to `docs/PHASE_I4_GATE.md` with `D-GATE-I.4`, approval date, approver, merge commit, and post-merge `main` sweep results.

- Treat HTTP auth and identity binding as early Phase 8 blockers, not late polish. At minimum, add explicit unsafe-by-default guardrails for hosted HTTP entry points.

- Add end-to-end replay tests for `ExceptionEscalation`, `OverrideBoundary`, and `ReviewQueue`, each driving through `build_replay_record`, not only checking produced blocks.

- Rename or alias `ccf hitl decide` to a submit-oriented verb, or make the output impossible to misread: `submitted`, `not resolved`, `event still pending`.

- Add a Phase 8 regression test for D-IMPL-65: engine refuses agent-node handoff when the required debt assessment binding is absent.

- Keep the scripted SDK conformance tests, but add at least one non-CI or nightly smoke path for real SDK runtime behavior where feasible.

- Make the accepted unauthenticated HTTP posture visible in generated client docs and CLI help, not only OpenAPI metadata.

## Risk Assessment

**Overall risk: MEDIUM, with a HIGH process caveat.**

The implementation evidence is broad and disciplined, and most scope appears achieved. The risk is not that the phase missed its main mechanics; it is that two authority-boundary items were deliberately deferred or accepted: unauthenticated HTTP and caller-supplied identity bindings. Those are manageable if treated as explicit v0 constraints and addressed early next phase.

If the supplied gate document is still the current final artifact, risk becomes **HIGH** because the documented gate state contradicts the claim that the phase was approved and merged.

---

## Cursor Review (post-execution)

# Cross-AI Post-Execution Review — Phase 7 (I.4)

## 1. Summary

Phase I.4 delivered what it promised: a factory-gated workflow engine with audited suspend/resume, four HITL primitives on a typed transport, three Experience front doors, and four OrchestrationProtocol legs — with CINV-04 at zero skips and claims scoped to actual enforcement after a real §3.1 review/ruling cycle (D-IMPL-62..65). Plans were unusually strong on prerequisites, falsifiability, and anti-overclaim discipline; execution fidelity is high against those plans and against `docs/PHASE_I4_GATE.md` / `07-VERIFICATION.md` (1280/0/0, mypy clean, lints green, `D-GATE-I.4` logged). Residual risk is concentrated in **deployment trust assumptions** (unauthenticated HTTP + caller-supplied principals) and a few **honest coverage narrowings** (compositional HITL replay for three primitives; Claude orchestrator on a scripted wire; deferred engine debt-cascade), not in missing phase deliverables.

## 2. Strengths

- **Prerequisite-first sequencing worked.** D-20 state-seam closure (07-02) and D-IMPL-56 (07-03) landed before the engine multiplied writers/skill surfaces — exactly the I.3 handoff’s failure mode prevention.
- **Vertical slice (D-01) banked the hard path early.** ApprovalGate + suspend/resume + both CINV-04 flips in one path (`tests/workflow/test_slice.py`) is the right structural proof; straight-line-first would have deferred the real risk.
- **“By construction” was earned, then scoped.** Token + `AuditedStateWriter`, required `HumanPrincipalBinding`, factory-only engine input, and bidirectional orchestration/adapters lint are structural. Gate rows use the D-22 template; HITL module docstrings quote CLAUDE.md rather than overclaim.
- **Falsifiable evidence, not intent.** Recorded counterfactuals for state-seam revert and both CINV-04 severances; post-ruling TDD reds for `HitlActionReceipt` and webhook; four-leg conformance with unchanged shared bodies.
- **Review process actually changed the product.** X-1/C-2/C-3/X-6/X-7 became D-IMPL-62..65; webhook deferral was rejected and shipped; submit-only door was hardened rather than papered over.
- **Harness neutrality preserved under pressure.** Engine and `/src` orchestration stay harness-free; D-06 split linted both ways; A7’s “generalize LangGraph `_build_graph`” failure mode is structurally blocked.
- **Front-door discipline.** No L1 write route; MCP roles separated (experience + HITL); CLI thin over HTTP via shared `ApiDependencies`; OpenAPI auth posture is an asserted sentence, not marketing prose.
- **Deviations registered instead of bent to plan counters.** D-09 “8 call sites” → one textual writer; D-IMPL-45 dim wording drift recorded; DESIGN.md corrected in-phase.

## 3. Concerns

- **HIGH — Identity/auth posture is the phase’s real residual, not a footnote.** T-07-24 (unauthenticated HTTP) + D-IMPL-63 (caller-supplied principal fields, no auth-context/JWS binding) means a client inside the trust boundary can mint any `subject_id` / IdP ref. MCP is authenticated, but HTTP/CLI are authority-bearing for HITL and workflow. Gate documents this honestly; Phase 8 / follow-up must treat D-IMPL-63 as load-bearing, not optional polish.
- **MEDIUM — HITL-01 “by construction” is ApprovalGate-strong, three-primitive-compositional.** Row 7 narrowing is correct: only the ApprovalGate slice drives `build_replay_record` end-to-end; escalation/override/review rely on block byte-equality ∘ builder verbatim landing. That is sound composition but weaker than CLAUDE.md §8.2’s absolute sentence. A wiring bug between ExceptionEscalation and replay write in a real composition root could slip past current CI.
- **MEDIUM — HTTP/CLI ↔ MCP HITL asymmetry (D-IMPL-62) is easy to misuse.** `ccf hitl decide` **submits**; it does not resolve. MCP can resolve + land dim-2 in-process. Operators integrating only HTTP need an explicit composition-root resolve step. Verb name `decide` still implies resolution; receipt hardening helps, naming does not.
- **MEDIUM — D-IMPL-65: INV-CH7-68 debt cascade is not engine-enforced.** `assess_debt` exists for ExceptionEscalation, but agent-node handoffs do not refuse missing debt assessment. Composition-root-now is an accepted gate close; until the named next-phase engine refusal ships, deployments can skip debt checks silently.
- **MEDIUM — Claude OrchestrationProtocol leg is expressibility on a scripted Transport, not a model loop.** Gate is honest; still, ORCH-02 “real SDK topology” for Claude is thinner than LangGraph’s interrupt/Command path. Do not treat I.4’s Claude driver as discharging Phase 8 A3 / `examples/03` loop portability.
- **LOW — D-IMPL-18 `variable_bindings` absent from `WorkflowStateRecord`.** Documented advisory; fine for v0 if intentional, but if Dave read D-IMPL-18 as a ruled member list, this is a quiet schema omission until amended.
- **LOW — Unaudited state reads (`items`).** Write-closure claim holds; reads can still reconstruct current state without audit. Acceptable for v0; relevant if Control Plane state becomes an investigative surface.
- **LOW — Process/doc drift.** Gate paste still says “awaiting Dave’s approval” while tree has `D-GATE-I.4` + merge; ROADMAP checklist for 07-14 reportedly stale. Confuses later auditors more than runtime.
- **LOW — `google-adk` `SequentialAgent` deprecation.** Mechanical; deferred correctly, but will bitrot the ADK orchestrator leg at the next pin bump.

## 4. Suggestions

- **Phase 8 must-haves for residual risk:** (1) at least one end-to-end `build_replay_record` drive per non-Approval HITL primitive (or a shared fixture parametrized over all four); (2) start D-IMPL-63 identity-binding reference impls before any external HTTP deployment; (3) implement D-IMPL-65 engine refusal and add a red test for unbound debt at agent handoff.
- **Rename or alias CLI verb** — add `ccf hitl submit` (keep `decide` as deprecated alias) so the D-IMPL-62 contract matches the verb.
- **Composition-root cookbook** in `examples/05-workflow-hitl`: submit via HTTP → resolve via primitive/MCP → resume workflow, with an explicit note that HTTP alone is not authority completion.
- **Amend D-IMPL-18** (or a short D-IMPL-NN) to record that `variable_bindings` is deferred/out of v0 `WorkflowStateRecord`, so the decision log matches the type.
- **Fix bookkeeping:** sync ROADMAP 07-14 checkbox and ensure `PHASE_I4_GATE.md` status banner matches post-`D-GATE-I.4` state so Phase 8 agents don’t re-litigate an open gate.
- **Do not expand OrchestrationProtocol scope in Phase 8** toward durable engines; keep Temporal behind the Protocol. The I.4 seam is already the right size.

## 5. Risk Assessment

**Overall: MEDIUM**

| Axis | Level | Why |
|------|--------|-----|
| Mechanism completeness vs ORCH/HITL/EXPR | **LOW** | Four criteria evidenced; six requirements ticked; verification independently re-ran green |
| Claim honesty / whitepaper–CLAUDE fidelity | **LOW** | Post-review narrowing + rulings closed the overclaim class that burned I.2/I.3 |
| Production front-door / HITL security | **HIGH → overall MEDIUM** | Unauthenticated HTTP + forgeable principals are intentional v0, but they are authority surfaces |
| Phase 8 dependency risk | **MEDIUM** | Examples 03/05/06, A3, D-IMPL-63/65, and fuller HITL E2E coverage are still required for adoptability claims |

**Justification:** Plan quality and execution fidelity are strong enough that the phase goals are met as *mechanism*. The gate does not understate the HTTP auth residual, but the combination of that residual with caller-supplied identity and submit-only HTTP is the one place a competent team could ship an insecure composition while believing CI proved “audit by construction.” Treat that as Phase 8’s first security debt, not as closed by I.4’s green suite.

---

## Ollama Review (post-execution)

## 1. Summary  

Phase 7 (Phase I.4) delivered a very large body of work – a full workflow engine with audited suspend/resume, four HITL primitives, three front‑door entry points (MCP‑experience, MCP‑HITL, HTTP API), a complete OrchestrationProtocol with three real driver legs (LangGraph, Google ADK, Claude‑Agent SDK), and the supporting schema, lint and invariant infrastructure.  The implementation was driven by test‑first development, counter‑factual red‑tests, and a strict “by‑construction” claim‑scoping discipline (D‑22).  All gate‑level check‑lists are satisfied, the CI run reports **1280 passed / 0 skipped**, and the gate document is populated with the required evidence.  In short, the phase meets its stated success criteria, but the breadth of the scope introduces a few lingering risks that deserve attention before Phase 8 begins.

---

## 2. Strengths  

| # | Observation |
|---|--------------|
| **S1 – Test‑driven rigor** | Every artifact (workflow definition, HITL primitive, orchestration driver, replay extensions, front‑doors) is covered by unit, integration and hypothesis‑stateful tests. Counter‑factual red‑tests guarantee that the “by‑construction’’ claims are actually proven. |
| **S2 – Explicit invariant framing** | The D‑22 template forces every “no‑unrecorded‑action’’ statement to be scoped to a concrete type/contract and tied to a failing test. This eliminates the habit of writing unchecked absolute claims. |
| **S3 – Architecture boundaries** | Clear separation of **src** (public contracts) vs **runtime** (implementations) and the **module‑tree split** (orchestration vs adapters) is enforced by custom lint rules that also ban bidirectional imports. |
| **S4 – Reusable patterns** | The three‑edit replay‑extension pattern, the token‑gated `ControlPlaneStateStore.put`, and the `HumanPrincipalBinding` contract are reused across many components, reducing duplication and drift. |
| **S5 – Comprehensive gating process** | The gate document contains per‑criterion rows, verbatim counter‑factual output, a deviation register, and a review triage record, meeting the CLAUDE‑md gating protocol. |
| **S6 – Portability proof** | The vertical‑slice (ApprovalGate + ApprovalSinkAdapter) demonstrates that the engine, HITL, and replay work together in a minimal end‑to‑end scenario. |
| **S7 – Future‑proof orchestration** | The `OrchestrationProtocol` is defined in **src**, drivers live under `runtime/ccf_runtime/orchestration/<sdk>/`, and a conformance suite guarantees replay‑equivalence across all three SDKs. |
| **S8 – Zero‑harness imports in src** | Linting guarantees that the core SDK never pulls in any harness code, preserving the “harness‑neutral’’ guarantee. |
| **S9 – Documentation of decisions** | All design rulings (D‑IMPL‑60, D‑IMPL‑61, etc.) are recorded in `DECISIONS.md` with dates and rationales, making later audits straightforward. |

---

## 3. Concerns  

| Severity | Concern | Why it matters |
|----------|---------|-----------------|
| **HIGH** | **Unauthenticated HTTP surface** – The OpenAPI server is deliberately unauthenticated (residual risk noted). This surface exposes the full authority‑bearing APIs (workflow invoke, HITL decision, agent invoke). If deployed without a perimeter, an attacker can drive arbitrary workflows and record audit‑trail‑bypassing actions. | Security. Needs explicit mitigation plan before any production deployment. |
| **HIGH** | **Token secrecy & reflection bypass** – The token that protects `ControlPlaneStateStore.put` is a module‑private class, but nothing prevents reflection or `type.__new__` from constructing it outside the module. No lint or runtime guard currently blocks such construction. | Could re‑enable unaudited writes, breaking the audit invariant (INV‑CH7‑71). |
| **MEDIUM** | **Orchestrator driver dead‑locks** – The LangGraph driver runs a background event‑loop thread; the ADK and Claude drivers use hook callbacks. No stress or fuzz tests for concurrency, time‑outs, or resource exhaustion. | May surface only under load, causing stalls in orchestrated workflows. |
| **MEDIUM** | **Missing performance verification** – No performance benchmark (throughput, latency, replay‑record size) is required for the engine, orchestrators, or front‑doors. The system may be viable for the test suite but could be too heavy for realistic workloads. | Affects adoptability (criterion 3) and may force later re‑engineering. |
| **MEDIUM** | **Limited multi‑tenant isolation testing** – Tests cover two tenants, but the codebase is designed for arbitrary tenants. Edge cases (tenant ID colliding with reserved URIs, malformed IDs) are not exercised. | Could lead to cross‑tenant data leakage or replay‑record tampering. |
| **MEDIUM** | **Webhook notify‑only leg lacks authentication** – The `HitlEventNotification` endpoint accepts unauthenticated POSTs. Although it is “notify‑only”, a malicious actor could flood the system or inject malformed payloads that affect downstream replay processing. | Potential denial‑of‑service or replay log corruption. |
| **LOW**  | **CLI argument parsing – URL hard‑coding** – While lints check for hard‑coded URLs, the CLI still builds a default `http://localhost:8000` if none is supplied in some wrappers. This could cause accidental connections to a dev server in production. | Minor operational confusion. |
| **LOW**  | **Custom lint maintenance burden** – The bespoke lint suite (`tools.lints`) is extensive; future contributors may forget to run it or may inadvertently edit the rule set, weakening guarantees. | Risk of silent drift. |
| **LOW**  | **Replay‑record field growth** – The three‑edit pattern adds fields to dimensions 2/4/5. If future extensions add a 6th dimension, the invariant (`INV‑CH7‑80`) would be violated. No guard currently detects accidental field addition. | Could break downstream tools that assume exactly five dimensions. |

---

## 4. Suggestions  

| Area | Action |
|------|--------|
| **Security – HTTP API** | • Add a configurable “auth‑required” flag with a simple token‑based scheme for the v0 surface; enforce it in the FastAPI dependency layer. <br>• Document the required deployment‑boundary (e.g., “run behind a reverse‑proxy that enforces mutual TLS”). |
| **Token protection** | • Make the token type a *private* nested class (`_StateWriteToken`) and expose a factory function that verifies the caller’s module via `inspect.stack()`. <br>• Add a lint that flags any use of `type()` or `__new__` on the token class outside `state.py`. |
| **Concurrency & dead‑lock testing** | • Add a fuzz/chaos test that runs many concurrent orchestrator driver sessions with random suspend/resume timing, verifying no hung threads after a timeout. <br>• Instrument the engine with a watchdog that logs any suspend handle that is not resumed within a configurable window. |
| **Performance baseline** | • Implement a lightweight benchmark that runs a representative workflow (e.g., the banking payment‑release example) 1 000× and records latency & memory usage for engine, orchestrator drivers, and HTTP API. <br>• Record the numbers in the gate document as “baseline performance”. |
| **Extended multi‑tenant testing** | • Add parametrized tests for ≥ 5 tenants with intentionally malformed tenant URIs (percent‑encoding, Unicode, reserved words) and verify isolation. |
| **Webhook hardening** | • Require a signed JWT (or HMAC) in the notification payload, even if the endpoint remains “notify‑only”. <br>• Rate‑limit incoming webhook requests via FastAPI’s `starlette.middleware.limits`. |
| **CLI robustness** | • Explicitly require the base URL to be supplied via `--endpoint` or `CCF_ENDPOINT` env var; fail fast if missing instead of defaulting to localhost. |
| **Lint continuity** | • Add a CI step that runs `git diff --check` against `tools/lints` to detect accidental removal of lint rules. <br>• Document in `CONTRIBUTING.md` the requirement to run `tools/lints --all` locally before committing. |
| **Replay dimension guard** | • Add a small runtime assertion in `record.py` that the top‑level dict has exactly the five expected keys; raise a clear error if a new field appears. |
| **Documentation of residual risks** | • Expand the “Residual Risks” section of the gate doc to include concrete mitigation steps (e.g., network isolation for the unauthenticated API, rate‑limits for the webhook). |
| **Future auth integration plan** | • Sketch a short “Version 0 → Version 1” migration path that adds authentication to the HTTP API without breaking replay semantics, and store it as a design note. |

---

## 5. Risk Assessment  

**Overall risk: **`MEDIUM`

*Justification*  

- **Achievement of functional goals** – ✅ All success criteria are demonstrably met; the gate passes with full test coverage.  
- **Security exposure** – The unauthenticated HTTP and webhook surfaces constitute a **high‑impact** vulnerability that could be exploited if the SDK is ever deployed in an environment without a strong perimeter. Although the SDK is intended as a library, the front‑door servers are shipped and could be run by downstream teams who may not apply the required network isolation. This pushes the overall risk to *medium* despite the functional success.  
- **Complexity & integration** – The module‑tree split, three orchestrator drivers, and multi‑tenant replay system are intricate; hidden integration bugs (dead‑locks, token bypass) are possible. Absence of performance and stress testing adds uncertainty.  
- **Mitigations in place** – The extensive test suite, invariant counter‑factuals, and lint rules greatly reduce the chance of regressions, pulling the risk back down from *high* to *medium*.  

If the residual security concerns are addressed (auth flag, token hardening) and at least a baseline performance benchmark is added, the risk would drop to **low**. Until then, treat the Phase 7 delivery as production‑ready **only in a trusted, isolated environment**.

---

## Post-Execution Consensus Summary

Risk verdicts: Gemini LOW · Codex MEDIUM (with a process caveat resolved below) · Cursor MEDIUM · Ollama MEDIUM.

### Agreed Strengths (2+ reviewers)
- Structural "by construction" enforcement earned, not asserted: token-gated state seam, factory-only engine input, D-06 bidirectional orchestration/adapters lint, D-22 scoped claims (all four).
- TDD/counterfactual discipline — recorded reds for seam closure and CINV-04 flips; zero-skip 1280-test suite (all four).
- The §3.1 review cycle materially changed the product: findings became rulings D-IMPL-62..65; webhook deferral rejected and shipped; submit-only door hardened (Gemini, Codex, Cursor).
- Harness neutrality preserved; four-leg conformance on unchanged shared test bodies (Gemini, Cursor, Ollama).

### Agreed Concerns (2+ reviewers — highest priority)
1. **Identity/auth residual is the phase's sharpest gap (HIGH: Codex, Cursor, Ollama; MEDIUM: Gemini).** Unauthenticated v0 HTTP surface (T-07-24) combined with caller-supplied HumanPrincipalBinding fields (D-IMPL-63 deferral) means authority-bearing surfaces accept spoofable principals inside the trust boundary. Consensus: treat D-IMPL-63 identity bindings + HTTP auth as EARLY Phase 8 scope, not polish.
2. **Non-ApprovalGate HITL replay coverage is compositional, not end-to-end (Codex, Cursor — MEDIUM).** Suggested: parametrized end-to-end `build_replay_record` drive per primitive in Phase 8.
3. **`ccf hitl decide` verb still implies resolution despite submit-only semantics (Codex, Cursor — MEDIUM).** Suggested: `ccf hitl submit` alias with `decide` deprecated.
4. **Claude orchestrator leg is expressibility-on-scripted-wire, not model-loop coverage (Codex, Cursor — MEDIUM).** Do not treat it as discharging Phase 8's example-03 loop-portability obligation.
5. **D-IMPL-65 engine debt-cascade refusal must actually land next phase with a red test (Codex, Cursor).**
6. **google-adk SequentialAgent deprecation will bitrot the ADK leg at next pin bump (Gemini, Cursor — LOW).**

### Divergent Views
- **Codex's HIGH process caveat (gate document says "awaiting approval" while phase is merged)** is a prompt-staleness artifact: the review prompt carried the pre-approval gate text; D-GATE-I.4 was logged and phase-i4 merged to main before this review ran. Cursor independently confirmed the tree has D-GATE-I.4 + merge. Actionable residue: add a post-merge addendum/status banner to PHASE_I4_GATE.md so later auditors don't re-litigate (Codex + Cursor bookkeeping suggestion).
- Ollama raises token-reflection bypass of the state seam and missing performance baselines — not echoed by others; recorded as candidate Phase 8 hardening/benchmark items.
- Gemini alone rates overall LOW, weighting the structural discipline; the MEDIUM majority weight the auth residual.

### Disposition
Phase 7 is gated and merged (D-GATE-I.4); these findings are Phase 8 planning inputs, aligning with already-named follow-up scope (D-IMPL-63, D-IMPL-65) plus new candidates: HITL E2E replay parametrization, `hitl submit` alias, gate-doc post-merge addendum, ADK deprecation migration, auth-hook example.
