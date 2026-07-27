# ROADMAP — CCF SDK v0

**Canonical authority:** `/home/parkave/ccf_code/CLAUDE.md` (revision 4). This
roadmap mirrors its phase discipline (§3) exactly. Where they disagree,
CLAUDE.md wins. Every phase ends with the §3.1 protocol: `/gsd-review --phase
<Phase> --all` self-review → blocking/advisory triage → STOP and present to
Dave → Dave approval logged as `D-GATE-<Phase>` in `docs/DECISIONS.md` → merge
phase branch to `main`. No phase begins before the prior phase's D-GATE entry
exists.

## Phases

- [x] **Phase 1: Phase R — Research** - Extract every whitepaper commitment into `docs/SPEC_INVENTORY.md` with homecams-patterns appendix (completed 2026-07-25)
- [x] **Phase 2: Phase D — Design** - SDK architectural shape: `docs/DESIGN.md`, `docs/DECISIONS.md`, full diagram set (completed 2026-07-25)
- [x] **Phase 3: Phase F — Feasibility & Scoping** - Per-component verdicts, v0.1 surface, test strategy; verify Phase I gate list (completed 2026-07-25)
- [x] **Phase 4: Phase I.1 — Fabric Core** - L1–L6 Data and Context Layer plus CI invariant scaffolding
- [x] **Phase 5: Phase I.2 — Agent Specialization Framework** - Agent base, six archetypes, Agent & Task Factory, skilling (completed 2026-07-26)
- [ ] **Phase 6: Phase I.3 — Cross-Process & Harness Adapters** - Bidirectional MCP, A2A federation, HarnessAdapterProtocol + reference adapters
- [ ] **Phase 7: Phase I.4 — Orchestration, HITL, Experience** - Workflow primitive, HITL primitives, MCP egress / CLI / HTTP front doors
- [ ] **Phase 8: Phase I.5 — Examples Suite & Full CI Verification** - Eight-example v0 suite in CI, all invariant lints green, Phase I gate

## Phase Details

### Phase 1: Phase R — Research

**Goal**: Every whitepaper commitment is cataloged in a component-keyed inventory that Phase D can design against, with Homecams patterns triangulated and every open question logged as a `D-IMPL-NN`
**Depends on**: Nothing (first phase)
**Requirements**: RSCH-01, RSCH-02, RSCH-03, RSCH-04
**Success Criteria** (what must be TRUE):

  1. `docs/SPEC_INVENTORY.md` satisfies every §16 element entry-by-entry: one entry per primitive in whitepaper §5–§8 with section, paraphrase, type signature, invariants, dependencies, figure refs, and open-question field — no whitepaper section in §5–§8 lacks coverage
  2. Dedicated sections exist for governance decisions (D-NN), load-bearing figures, named architectural invariants, SDK extensions with whitepaper hooks, and the pillar-by-pillar mapping across all five Common Pillars
  3. The `homecams-patterns` appendix exists with explicit "candidate pattern" / "domain-specific — do not inherit" markers, including MongoDB persistence as an ArtifactStore triangulation data point
  4. Every open question carries a `D-IMPL-NN` number in `docs/DECISIONS.md`; no design choices or code produced
  5. `/gsd-review --phase Phase R --all` run, findings triaged, blocking findings fixed, Dave approval logged as `D-GATE-R`, `phase-r` merged to `main`

**Plans:** 12/12 plans complete

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Repo prerequisites (§14 items 1–5): branches, .gitignore, skeleton, placeholders

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Figure extraction (50) + whitepaper Ch 1–6 conversion (D-01/D-04)
- [x] 01-10-PLAN.md — Homecams review → homecams-patterns appendix (RSCH-03)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Whitepaper Ch 7 conversion (mechanism core, pp. 86–180)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-04-PLAN.md — Ch 8–9 conversion + D-03 spot-check fidelity gate

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 01-05-PLAN.md — Extract Ch 5–6 commitments (13 subsections)
- [x] 01-06-PLAN.md — Extract §7.1–§7.4 (layers, graph, operators)
- [x] 01-07-PLAN.md — Extract §7.5–§7.7 (projection, products, debt/half-life)
- [x] 01-08-PLAN.md — Extract §7.8–§7.10 (planes, closed loop, replay)
- [x] 01-09-PLAN.md — Extract Ch 8 (integration patterns, 13 subsections)

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 01-11-PLAN.md — Synthesis: merge fragments, §16 sections, D-IMPL-30+ numbering

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 01-12-PLAN.md — §3.1 gate: self-audit, /gsd-review, Dave approval, D-GATE-R, merge

**Process notes**: Model mandate — Anthropic Fable 5, "high" effort. Branch: `phase-r`. No production code (§3). Ends with review → triage → Dave approval → `D-GATE-R` before Phase 2 begins.

### Phase 2: Phase D — Design

**Goal**: The SDK's architectural shape exists on paper, preserving every named invariant by construction, with every design decision surfaced for Dave's ruling
**Depends on**: Phase 1 (`D-GATE-R` logged)
**Requirements**: DSGN-01, DSGN-02, DSGN-03, DSGN-04
**Success Criteria** (what must be TRUE):

  1. `docs/DESIGN.md` maps every inventory entry to a design element or an explicit deferral; every named invariant (single-writer, composition-preservation, three validation gates, Algorithmic ⇄ Semantic Alternation, audit-by-construction, No-Hardcoding, zero harness imports in core) is shown preserved structurally on paper
  2. `docs/DECISIONS.md` has every open `D-IMPL-NN` either resolved with Dave's ruling recorded or explicitly flagged as gating
  3. `docs/diagrams/` contains the complete set: one diagram per Common Pillar (five), plus the harness-adapter seam diagram and the ArtifactStore seam diagram
  4. `/gsd-review --phase Phase D --all` run, triaged, Dave approval logged as `D-GATE-D`, phase branch merged to `main`

**Plans:** 11/11 plans complete

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Setup: phase-d branch, DECISIONS.md hygiene, 126-entry ownership map

**Waves 2–4** *(decision marathon — serial, interactive, D-03 gate on drafting)*

- [x] 02-02-PLAN.md — Batch 1 rulings: fabric & runtime fundamentals (16 decisions, D-IMPL-01 first)
- [x] 02-03-PLAN.md — Batch 2 rulings: agent framework, harness, cross-process/trust (14 decisions)
- [x] 02-04-PLAN.md — Batch 3 rulings + 49/49 census + provisional register (19 decisions)

**Wave 5** *(parallel drafting into fragments)*

- [x] 02-05-PLAN.md — Data & Context pillar A (L1–L3, single-writer) + seq diagram
- [x] 02-06-PLAN.md — Data & Context pillar B (L4–L6, replay, planes) + pillar/replay diagrams
- [x] 02-07-PLAN.md — Core Agent Types pillar + diagram
- [x] 02-08-PLAN.md — Orchestration + HITL pillars + 3 diagrams
- [x] 02-09-PLAN.md — Experience pillar + seams chapter + 4 diagrams (both seam diagrams)

**Wave 6**

- [x] 02-10-PLAN.md — Synthesize DESIGN.md: pillars, Invariant Preservation chapter, 126-row traceability matrix

**Wave 7**

- [x] 02-11-PLAN.md — §3.1 gate: self-audit, /gsd-review, Dave approval, D-GATE-D, merge to main

**Process notes**: Model mandate — Fable 5, "high" effort. Branch: `phase-d`. No implementation code (§3). Ends with review → triage → Dave approval → `D-GATE-D` before Phase 3 begins.

### Phase 3: Phase F — Feasibility & Scoping

**Goal**: Every design component has an implementation verdict, the v0.1 minimum viable surface is explicit, and the Phase I gate is verifiably satisfiable
**Depends on**: Phase 2 (`D-GATE-D` logged)
**Requirements**: FEAS-01, FEAS-02, FEAS-03, FEAS-04
**Success Criteria** (what must be TRUE):

  1. `docs/FEASIBILITY.md` carries a verdict (strong fit / needs design choice / out of scope for v0) for every design component
  2. `docs/ROADMAP.md` states the milestone breakdown, an explicit v0.1 minimum viable SDK surface, and what is deferred
  3. Test strategy names how each CI-enforced invariant will be verified; the Phase I gate list (D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28) is checked against actual resolution status — Phase 4 does not start until all are at least provisionally resolved
  4. `/gsd-review --phase Phase F --all` run, triaged, Dave approval logged as `D-GATE-F`, phase branch merged to `main`

**Plans**: 4 plans

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — FEASIBILITY.md component verdicts + 126-entry appendix matrix (FEAS-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — docs/ROADMAP.md milestones, v0.1 surface, deferral register (FEAS-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-03-PLAN.md — Test-strategy table, gate-list check, advisory dispositions, DESIGN.md fixes (FEAS-03)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 03-04-PLAN.md — Review, triage, Dave approval, D-GATE-F, merge to main (FEAS-04)

**Process notes**: Model mandate — Fable 5, "high" effort. Branch: `phase-f`. Ends with review → triage → Dave approval → `D-GATE-F` before Phase 4 begins. **Hard gate:** Phase I cannot start until D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28 are provisionally resolved.

### Phase 4: Phase I.1 — Fabric Core

**Goal**: The L1–L6 Data and Context Layer works end-to-end in-process against reference backends, with the CI invariant lints scaffolded and running
**Depends on**: Phase 3 (`D-GATE-F` logged; Phase I gate decisions resolved)
**Requirements**: FABR-01, FABR-02, FABR-03, FABR-04, FABR-05, FABR-06, FABR-07, FABR-08, FABR-09, CINV-01, CINV-02, CINV-03, CINV-04
**Success Criteria** (what must be TRUE):

  1. Context Graph primitive persists to both reference backends (Postgres + SQLite per D-IMPL-02) with idempotent upsert, multi-source lineage accumulation, and single-writer enforcement at boot; only L2 holds a write handle to L3
  2. All four operator categories ship with composition-preservation tests passing for every shipped operator pair `(A∘B)(G) = A(B(G))`; projection engine executes the two-stage plan via structural typing
  3. Context Product Contract enforces `extra=forbid` and all three validation gates (empty-operator guard, lineage strict equality, TTL bounds); `λ_c`/`D_c` computation draws every value from Control Plane config with zero hard-coded tables in `/src`
  4. Five-dimension Decision Replay record is written at product-serve time by construction; ArtifactStore Protocol works against the file-backed dev impl; CDC→G ingress reference ingests to L1

     > **⚠ SCOPE AMENDMENT (04-CONTEXT.md D-12, Dave, 2026-07-25).** This criterion previously required the ArtifactStore Protocol to work against "both the file-backed dev impl **and the MCP-backed reference impl**." Phase 4 (I.1) scope is now **Protocol + file-backed dev impl only**; the MCP-backed reference implementation is **deferred to Phase 6 (I.3)**, where it lands with the rest of the MCP machinery. Gate review for Phase 4 verifies the amended criterion above, not the original. Phase 6 inherits the MCP-backed impl as an explicit deliverable, and criterion 3 of Phase 8 (example 07's file-backed → MCP-backed swap) depends on it.
  5. CI invariant scaffolding runs green on the fabric: No-Hardcoding lint, zero-harness-imports lint, `@algorithmic` lint, replay-by-construction and single-writer boot checks (CINV-01..04)

**Plans**: 12 plans

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Scaffold: phase-i1 branch, packaging, CI workflow, D-03/D-12 doc amendments
- [x] 04-02-PLAN.md — CINV-01..03 AST lint checkers + allowlist, blocking in CI (D-06..D-08) *(wave 2)*
- [x] 04-03-PLAN.md — Slice contracts, canonical serializer, minimal Control Plane registry *(wave 2)*
- [x] 04-04-PLAN.md — Graph Protocols, SQLite backend, six-semantics conformance, assembly + single-writer boot *(wave 3)*
- [x] 04-05-PLAN.md — Vertical slice serve path: operators/projection/gates/replay/ArtifactStore + banking proto-quickstart *(wave 4)*
- [x] 04-06-PLAN.md — Operator registry/planner + composition-preservation property harness (D-14) *(wave 5)*
- [x] 04-07-PLAN.md — λ_c/D_c mechanism + full Control Plane subsystem *(wave 5)*
- [x] 04-08-PLAN.md — Replay engine + ArtifactStore conformance + CINV-04 harness *(wave 5)*
- [x] 04-09-PLAN.md — CDC→G ingress reference in ccf-runtime *(wave 5)*
- [x] 04-10-PLAN.md — Postgres GraphStore against the conformance suite + CI leg (D-11) *(wave 6)*
- [x] 04-11-PLAN.md — SimilarityIndex: sqlite-vec + Chroma optional extra (D-13) *(wave 6)*
- [x] 04-12-PLAN.md — Gate: per-invariant checklist, /gsd-review, Dave approval, D-GATE-I.1, merge *(wave 7)*
**Process notes**: Model mandate — Opus 5 if available, else Opus 4.8, "high" effort. Branch: `phase-i1` (Phase I work). Redesign needs a Phase D mini-cycle, never in-line. Sub-phase ends with `/gsd-review` → triage → Dave approval → `D-GATE-I.1` before Phase 5 begins.

### Phase 5: Phase I.2 — Agent Specialization Framework

**Goal**: Agents are declared, versioned Control Plane artifacts produced exclusively by the Agent & Task Factory from the six shipped archetypes, specialized through the two governed channels
**Depends on**: Phase 4 (fabric, Control Plane, ArtifactStore, replay in place)
**Requirements**: AGNT-01, AGNT-02, AGNT-03
**Success Criteria** (what must be TRUE):

  1. Unified Agent base + all six archetypes exist as SDK mechanism in `/src` with no agent instances, prompts, or domain values in library code; archetype composition works per the D-IMPL-11/19 rulings
  2. Agent & Task Factory constructs agents and tasks only from definition artifacts (D-IMPL-28 schema); tests demonstrate no supported path to an agent bypassing the factory, and the No-Hardcoding lint rejects factory bypass and prompt-shaped literals
  3. Skill catalog supports registration, discovery, and runtime grant/revoke; the policy-compatibility check refuses a grant exceeding the agent's policy regime or context contract; every grant/revocation and the skill-set in force land in the replay record
  4. All six specialization axes (archetype binding, context contract, perspective, policy regime, half-life/debt profile, instruction bindings) are expressible in the definition artifact and versioned — changing any axis produces a new agent version visible in replay

**Plans:** 10/10 plans complete

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — Slice foundations: jinja2 pin, six-axis definition schemas (D-IMPL-28), prompt parse-only validation (D-13), D-05 hash-verified bump, full D-06 dimension-4 replay extension

**Wave 2**

- [x] 05-02-PLAN.md — Vertical slice (D-01/D-02/D-03): ArchetypeComponent + analytics_insights, concrete Agent, AgentFactory, test-double harness, end-to-end slice test with dimension-4 assertions

**Wave 3**

- [x] 05-03-PLAN.md — All six archetypes + D-IMPL-19 composition rules + consumption-discipline test

**Wave 4**

- [x] 05-04-PLAN.md — Factory hardening: TaskDefinition + TaskFactory (D-11), CINV-01c behavioral lint fixture (D-12), JSON Schema export, six-axis version matrix

**Wave 5**

- [x] 05-05-PLAN.md — Skill catalog: 4-type entry schema (D-IMPL-12), typed requirements declaration, registration/discovery via Control Plane, banking skill fixtures

**Wave 6**

- [x] 05-06-PLAN.md — Skilling governance + dispatch: two-tier grants + ApprovalSink (D-09), grant-set hash (D-07), dispatch + NotYetBound (D-08), replay capture + CINV-04 activation (D-10)

**Wave 7**

- [x] 05-07-PLAN.md — Gate wave: full verification sweep, per-invariant gate checklist, success-criteria evidence map, I.3 handoff notes

**Process notes**: Model mandate — Opus 5 (fallback Opus 4.8), "high" effort. Branch: `phase-i2`. Ends with `/gsd-review` → triage → Dave approval → `D-GATE-I.2` before Phase 6 begins.

### Phase 6: Phase I.3 — Cross-Process & Harness Adapters

**Goal**: Context Products travel governed across process and harness boundaries — MCP in both directions, A2A with Control Plane admission, and harness adapters binding all four seams without a single harness import in core
**Depends on**: Phase 5 (agent definitions and skill-sets exist to expose through adapters)
**Requirements**: XPRC-01, XPRC-02, XPRC-03
**Success Criteria** (what must be TRUE):

  1. Bidirectional MCP works: client ingress at L1/L4/L5/Experience normalizing to the L1 envelope, server egress at L6 exposing Context Products as MCP Resources, and the ArtifactStore MCP role kept in a distinct module from egress
  2. A2A federation exchanges typed Context Products across processes behind the WireProtocol abstraction (D-IMPL-14 default), with identity/signing (D-IMPL-15) and inbound products admitted to L3 only through L2 after Control Plane policy-binding verification, lineage extended by set-union
  3. `HarnessAdapterProtocol` + reference adapters for the D-IMPL-24 harnesses bind all four seams (context injection, skill exposure of exactly the currently-bound skill-set, effect capture with no harness write handle, replay hooks); the zero-harness-imports-in-`/src` lint stays green
  4. Single-writer invariant demonstrably holds across the A2A boundary, the adapter boundary, and the ArtifactStore
  5. **MCP-backed ArtifactStore reference implementation ships** and passes the same shared ArtifactStore Protocol conformance suite as the file-backed dev impl, with no other deployment change required to swap between them *(inherited from Phase 4 per the D-12 scope amendment recorded on Phase 4 criterion 4)*

**Plans:** 15/17 plans executed

Plans:
**Wave 1** *(blockers — D-24 lint carve-out, packaging, D-19 gate)*

- [x] 06-01-PLAN.md — CINV-02 harness-adapter carve-out + negative boundary tests + DESIGN.md B4 (D-24)
- [x] 06-02-PLAN.md — Harness extras, mypy over /runtime, crossproc+harness markers (D-08, B2)
- [x] 06-03-PLAN.md — Registered-callable table replacing importlib dispatch (D-19, blocking)

**Wave 2** *(the D-01 vertical slice, plus the two /src-only plans it does not block)*

- [x] 06-04-PLAN.md — Shared MCP client + sync facade, L6 egress server, THE crossproc fixture (D-01, D-15/16/17)
- [x] 06-07-PLAN.md — IdentityProvider + detached-JWS ES256 + trust-policy artifact (D-13, D-IMPL-16)
- [x] 06-11-PLAN.md — HarnessAdapterProtocol + D-25 harness_trace + sandboxed prompt render

**Wave 3** *(transport wave a + the L4/L5 acquisition leg)*

- [x] 06-05-PLAN.md — MCP-backed ArtifactStore + separate artifact server w/ TokenVerifier (criterion 5, D-26)
- [x] 06-06-PLAN.md — MCP client ingress at L1 + mcp skill dispatch (D-05)
- [x] 06-08-PLAN.md — WireProtocol + admission gate ahead of L2 + lineage set-union property (D-12, D-14)
- [x] 06-12-PLAN.md — Claude Agent SDK adapter deep + conformance suite + skip mechanism (D-07, D-09)
- [x] 06-17-PLAN.md — L4/L5 decision-time content acquisition over the shared MCP client (XPRC-01)

**Wave 4**

- [x] 06-09-PLAN.md — Typed-HTTP transport + real two-process exchange + A2A single-writer leg (D-11)
- [x] 06-13-PLAN.md — LangGraph adapter + Protocol hardening for topology ownership

**Wave 5**

- [x] 06-10-PLAN.md — LF A2A transport (D-IMPL-14 default) + a2a skill dispatch (D-05)
- [x] 06-14-PLAN.md — Google ADK adapter + D-10 effects-inert proof + adapter single-writer leg

**Wave 6**

- [ ] 06-15-PLAN.md — Harness portability: one definition, three harnesses, D-18 equivalence

**Wave 7** *(gate)*

- [ ] 06-16-PLAN.md — Full sweep, CI harness leg, PHASE_I3_GATE.md, present to Dave

**Wave ordering note**: waves are `max(depends_on) + 1`. D-02's transport → trust →
harness widening is a *risk ordering* — it governs where the phase's unknowns land, not
whether independent plans may run concurrently — so the `/src`-only trust and harness
contract plans (06-07, 06-11) sit at wave 2 rather than being held behind the transport
work they do not depend on. The blocking orderings still hold absolutely: D-24 (06-01)
precedes every harness import (first in 06-12, wave 3), D-19 (06-03) precedes every
transport plan (first in 06-04, wave 2), and D-07's within-harness order is preserved
(Claude 06-12 → LangGraph 06-13 → ADK 06-14).

**Known same-wave file overlap**: 06-01 and 06-03 both append to `docs/DECISIONS.md`
(D-IMPL-53 and D-IMPL-54). Both are wave 1. If wave 1 is executed in parallel worktrees
this needs serializing at merge; it is recorded here rather than claimed away.

**Process notes**: Model mandate — Opus 5 (fallback Opus 4.8), "high" effort. Branch: `phase-i3`. Ends with `/gsd-review` → triage → Dave approval → `D-GATE-I.3` before Phase 7 begins.

### Phase 7: Phase I.4 — Orchestration, HITL, Experience

**Goal**: Multi-agent workflows with human gates execute, suspend, and resume with every human action and trace replay-recorded, reachable through the three v0 front doors
**Depends on**: Phase 6 (agent nodes resolve through adapter bindings; MCP egress exists)
**Requirements**: ORCH-01, ORCH-02, HITL-01, EXPR-01, EXPR-02, EXPR-03
**Success Criteria** (what must be TRUE):

  1. Workflow primitive executes state-machine workflows with skill, agent, and HITL-gate nodes; workflow definitions are Control Plane artifacts via the Task Factory; suspended state persists at the Control Plane boundary (per D-IMPL-18) and resumes correctly; execution traces land in the replay record's Perspective Conditioning and Content Generation Path dimensions
  2. All four HITL primitives (ApprovalGate, ExceptionEscalation, OverrideBoundary, ReviewQueue) write to Decision Replay by construction — CI verifies there is no path through the HITL surface producing an unrecorded human action
  3. OrchestrationProtocol allows an external orchestrator to drive workflows without touching SDK internals
  4. All three front doors work: MCP server egress exposing products and agents, the `ccf` CLI covering workflow invocation / HITL inspection / replay queries / Control Plane config / agent declaration / skilling / artifact inspection (per D-IMPL-22), and the HTTP API skeleton with a valid OpenAPI spec (per D-IMPL-23)

**Plans**: TBD
**Process notes**: Model mandate — Opus 5 (fallback Opus 4.8), "high" effort. Branch: `phase-i4`. Ends with `/gsd-review` → triage → Dave approval → `D-GATE-I.4` before Phase 8 begins.

### Phase 8: Phase I.5 — Examples Suite & Full CI Verification

**Goal**: The eight-example adoption contract runs end-to-end in CI in one coherent neutral domain, and every CI-enforced invariant is verified across the whole SDK — the Phase I gate
**Depends on**: Phase 7 (every SDK surface the examples exercise exists)
**Requirements**: EXAM-01, EXAM-02, EXAM-03, EXAM-04, EXAM-05, EXAM-06, EXAM-07, EXAM-08, EXAM-09
**Success Criteria** (what must be TRUE):

  1. All eight examples (`00-quickstart` through `07-artifact-store-mcp`) run end-to-end in CI with a single documented command each, against the reference backends, in one coherent neutral domain (non-banking, non-property-intelligence)
  2. Example 03 asserts harness portability: one agent definition unmodified under two harnesses with equivalent Context Product consumption and replay records; examples 04 + 05 together constitute the full cross-process + HITL deployment with admission verification and a replay-recorded human action
  3. Example 06 reproduces a prior Context Product exactly from ArtifactStore-resolved versions (graph snapshot, policy bundle, agent version, skill-set, prompt artifacts — never "latest"); example 07 swaps file-backed for MCP-backed ArtifactStore with no other change
  4. Every example ships code + artifacts side by side with a README citing the whitepaper and CLAUDE.md sections it exercises; no example's code runs meaningfully with its artifacts deleted (No-Hardcoding demonstrated)
  5. Full Phase I review passes: all CI invariants green (CINV-01..04 across `/src`, `/runtime`, `/examples`), composition-preservation tests for every shipped operator pair, and the whitepaper-fidelity spot check on sampled public class docstrings

**Plans**: TBD
**Process notes**: Model mandate — Opus 5 (fallback Opus 4.8), "high" effort. Branch: `phase-i5`. Ends with `/gsd-review --phase Phase I --all` → triage → Dave approval → `D-GATE-I` before v0 is declared. Homecams-on-SDK rebuild is post-v0 (deferred).

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Phase R — Research | 12/12 | Complete   | 2026-07-25 |
| 2. Phase D — Design | 11/11 | Complete   | 2026-07-25 |
| 3. Phase F — Feasibility & Scoping | 4/4 | Complete   | 2026-07-25 |
| 4. Phase I.1 — Fabric Core | 12/12 | Complete | 2026-07-25 |
| 5. Phase I.2 — Agent Specialization Framework | 10/10 | Complete   | 2026-07-26 |
| 6. Phase I.3 — Cross-Process & Harness Adapters | 15/17 | In Progress|  |
| 7. Phase I.4 — Orchestration, HITL, Experience | 0/? | Not started | - |
| 8. Phase I.5 — Examples Suite & Full CI Verification | 0/? | Not started | - |

## Coverage

All 46 v1 requirements mapped, each to exactly one phase:
RSCH-01..04 → 1; DSGN-01..04 → 2; FEAS-01..04 → 3;
FABR-01..09 + CINV-01..04 → 4; AGNT-01..03 → 5; XPRC-01..03 → 6;
ORCH-01..02 + HITL-01 + EXPR-01..03 → 7; EXAM-01..09 → 8.
