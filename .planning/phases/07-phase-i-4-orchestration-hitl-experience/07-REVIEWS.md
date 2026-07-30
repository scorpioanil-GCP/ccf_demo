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
