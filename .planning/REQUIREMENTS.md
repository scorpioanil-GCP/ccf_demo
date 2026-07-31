# REQUIREMENTS — CCF SDK v0

Extracted from `CLAUDE.md` (canonical, revision 4) §3 phase deliverables and
§13 v0 scope. CLAUDE.md wins on any disagreement. Requirements are grouped by
phase deliverable and, within Phase I, by Common Pillar (§4).

## v1 (v0 SDK) Requirements

### Phase R — Research

- [ ] **RSCH-01**: `docs/SPEC_INVENTORY.md` catalogs every commitment in
      whitepaper §5–§8: section, paraphrased commitment, type signature where
      given, invariants, dependencies, figure refs, open-question field (§16)
- [ ] **RSCH-02**: Inventory includes sections for governance decisions (D-NN),
      load-bearing figures, named architectural invariants, SDK extensions with
      whitepaper hooks, and pillar-by-pillar mapping (§16)
- [ ] **RSCH-03**: `homecams-patterns` appendix with "candidate pattern" /
      "domain-specific — do not inherit" markers, incl. MongoDB persistence as
      ArtifactStore triangulation data point (§2.1, §16)
- [ ] **RSCH-04**: Every open question carries a `D-IMPL-NN` entry; Phase R
      reviewed via `/gsd-review`, triaged, and Dave-approved with `D-GATE-R`
      logged (§3.1)

### Phase D — Design

- [x] **DSGN-01**: `docs/DESIGN.md` maps every inventory entry to a design
      element or explicit deferral, preserving every named invariant by
      construction on paper (§3.1)
- [x] **DSGN-02**: `docs/DECISIONS.md` — every open `D-IMPL-NN` resolved with
      Dave's ruling or flagged as gating (§12)
- [x] **DSGN-03**: `docs/diagrams/` — one diagram per pillar, plus
      harness-adapter seam and ArtifactStore seam diagrams (§3)
- [x] **DSGN-04**: Phase D reviewed, triaged, Dave-approved, `D-GATE-D` logged

### Phase F — Feasibility & Scoping

- [ ] **FEAS-01**: `docs/FEASIBILITY.md` — per-component verdict (strong fit /
      needs design choice / out of scope for v0) (§3)
- [ ] **FEAS-02**: `docs/ROADMAP.md` — milestone breakdown, explicit v0.1
      minimum viable SDK surface, deferred items (§3)
- [ ] **FEAS-03**: Test strategy names how each CI-enforced invariant is
      verified; Phase I gate list (§12) checked against resolution status (§3.1)
- [ ] **FEAS-04**: Phase F reviewed, triaged, Dave-approved, `D-GATE-F` logged

### Phase I — Data and Context Layer (fabric)

- [ ] **FABR-01**: Context Graph state primitive with reference Postgres +
      SQLite backends (per D-IMPL-02)
- [ ] **FABR-02**: Operator algebra with four canonical operator categories;
      composition-preservation tests for every shipped operator pair
- [ ] **FABR-03**: Projection engine (Π) with structural typing
      (`required_operators()` + `invoke()`, two-stage execution)
- [x] **FABR-04**: Context Product Contract base (`extra=forbid`) + three
      validation gates (empty-operator guard, lineage strict equality, TTL)
- [ ] **FABR-05**: Half-life (`λ_c`) and Context Debt (`D_c`) computation, all
      values from Control Plane config
- [ ] **FABR-06**: Five-dimension Decision Replay record + replay engine,
      extended for HITL actions, workflow traces, agent versions, skill-sets
- [ ] **FABR-07**: Control Plane as in-process versioned registry with remote
      extension point
- [ ] **FABR-08**: ArtifactStore Protocol with MCP-backed reference impl and
      file-backed dev impl (§7.4)
      *(D-12 deferral: Phase I.1 delivers the Protocol + file-backed dev impl
      only; the MCP-backed reference impl lands in Phase 6.)*
- [ ] **FABR-09**: CDC→G ingress reference (Pattern 1)

### Phase I — Core Agent Types

- [x] **AGNT-01**: Unified Agent base + six archetypes (Workflow/Task,
      DocumentIntelligence, AnalyticsInsights, MonitoringSurveillance,
      ContentGeneration, ContextAssembly) as SDK mechanism (§6.1, §6.3)
- [x] **AGNT-02**: Agent & Task Factory + declarative definition-artifact
      schema (per D-IMPL-28); no path to an agent bypassing the factory (§6.4)
- [x] **AGNT-03**: Skill catalog primitives — registration, discovery,
      governance, runtime grant/revoke with policy-compatibility check and
      replay capture (§6.2)

### Phase I — Cross-Process and Harness

- [x] **XPRC-01**: Bidirectional MCP — client at L1/L4/L5/Experience, server
      at L6 and ArtifactStore (§7.1). Evidence: `docs/PHASE_I3_GATE.md` §3.1,
      one row per *consumer* of the client. The Experience-layer consumer is
      **Phase 7 scope** per `06-CONTEXT.md` and is recorded there as a named
      deferral, not claimed as delivered.
- [x] **XPRC-02**: A2A federation — WireProtocol abstraction, identity/signing
      primitives, Control Plane admission verification (§7.2). Evidence:
      `docs/PHASE_I3_GATE.md` §3.2.
- [x] **XPRC-03**: `HarnessAdapterProtocol` + reference adapters per D-IMPL-24,
      binding all four seams (context injection, skill exposure, effect
      capture, replay hooks) (§7.3). Evidence: `docs/PHASE_I3_GATE.md` §3.3.

### Phase I — Orchestration and HITL

- [x] **ORCH-01**: Workflow primitive with agent nodes and HITL gates,
      suspendable on Control Plane state; workflow definitions as artifacts (§8.1).
      Evidence: `docs/PHASE_I4_GATE.md` §2 rows 1–6
- [x] **ORCH-02**: OrchestrationProtocol for external orchestrator integration.
      Evidence: `docs/PHASE_I4_GATE.md` §2 rows 12–13 (D-IMPL-60 four legs)
- [x] **HITL-01**: ApprovalGate, ExceptionEscalation, OverrideBoundary,
      ReviewQueue primitives with audit-by-construction replay integration (§8.2).
      Evidence: `docs/PHASE_I4_GATE.md` §2 rows 7–10

### Phase I — Experience Layer

- [x] **EXPR-01**: MCP server (egress) exposing Context Products and agents.
      Evidence: `docs/PHASE_I4_GATE.md` §2 row 14
- [x] **EXPR-02**: `ccf` CLI — workflow invocation, HITL inspection, replay
      queries, Control Plane config, agent declaration, skilling, artifact
      inspection (§8.3). Evidence: `docs/PHASE_I4_GATE.md` §2 row 16
- [x] **EXPR-03**: HTTP API skeleton with OpenAPI spec.
      Evidence: `docs/PHASE_I4_GATE.md` §2 row 15

### Phase I — CI Invariants

- [ ] **CINV-01**: No-Hardcoding lint (prompt-shaped literals, factory bypass)
- [ ] **CINV-02**: Zero-harness-imports-in-`/src` lint
- [ ] **CINV-03**: `@algorithmic` lint (no LLM client imports in algorithmic
      modules)
- [x] **CINV-04**: Replay-by-construction checks (HITL, workflow, skill-set
      capture) and single-writer enforcement at boot. Completed in Phase 7:
      both I.3 deferrals (`hitl-action-capture`, `workflow-trace-capture`)
      flipped active with red-proven owning tests; suite skip count 0.
      Evidence: `docs/PHASE_I4_GATE.md` §1, rows 5 and 7

### Phase I — Examples Suite (§9)

- [x] **EXAM-01**: `00-quickstart` — minimal fabric, one typed Context Product
- [x] **EXAM-02**: `01-agent-basics` — agent from archetype via artifact +
      factory, all six specialization axes
- [x] **EXAM-03**: `02-skilling` — grant/exercise/revoke skill; governance
      check fires; replay captures grants
- [x] **EXAM-04**: `03-harness-portability` — one agent definition under two
      harnesses with equivalence assertion
- [x] **EXAM-05**: `04-cross-process` — assembler and consumer across
      processes via MCP egress and A2A with admission verification
- [ ] **EXAM-06**: `05-workflow-hitl` — workflow with ApprovalGate +
      ExceptionEscalation, suspend/resume, replay-recorded human action
- [ ] **EXAM-07**: `06-decision-replay` — exact reproduction of a prior
      Context Product from ArtifactStore-resolved versions
- [ ] **EXAM-08**: `07-artifact-store-mcp` — swap file-backed store for
      MCP-backed store with no other change
- [x] **EXAM-09**: All examples runnable end-to-end in CI, code + artifacts
      side by side, README each, one coherent neutral domain

## v2 (Deferred)

- Homecams rebuild on the CCF SDK — post-v0 validation exercise (§9)
- Adapter package/repo split — open remainder of D-IMPL-10
- Third harness adapter (e.g., LangGraph) if excluded by D-IMPL-24 ruling

## Out of Scope

Per CLAUDE.md §13:

- Agent loop / harness of any kind — CCF is trust-and-control plane only
- Pre-built domain ontologies, projections, policy bundles, skill catalogs,
  workflows, HITL policies — example configurations only
- Distributed multi-writer coordination within a tenant — single-writer v0
- Heavyweight workflow engines — via OrchestrationProtocol only
- Production observability stacks — hooks exposed, infra is deployment's problem
- Mobile SDK, chat adapter, web UI, human task inbox — users build on HTTP API
- Conversational Reporting Layer (whitepaper §8.10)
- Domain calibrations and regulatory policy bundles — never the SDK's problem

## Traceability

All 46 v1 requirements mapped (46/46).

| Requirement | Phase | Status |
|-------------|-------|--------|
| RSCH-01 | Phase 1 | Pending |
| RSCH-02 | Phase 1 | Pending |
| RSCH-03 | Phase 1 | Pending |
| RSCH-04 | Phase 1 | Pending |
| DSGN-01 | Phase 2 | Complete |
| DSGN-02 | Phase 2 | Complete |
| DSGN-03 | Phase 2 | Complete |
| DSGN-04 | Phase 2 | Complete |
| FEAS-01 | Phase 3 | Pending |
| FEAS-02 | Phase 3 | Pending |
| FEAS-03 | Phase 3 | Pending |
| FEAS-04 | Phase 3 | Pending |
| FABR-01 | Phase 4 | Pending |
| FABR-02 | Phase 4 | Pending |
| FABR-03 | Phase 4 | Pending |
| FABR-04 | Phase 4 | Complete |
| FABR-05 | Phase 4 | Pending |
| FABR-06 | Phase 4 | Pending |
| FABR-07 | Phase 4 | Pending |
| FABR-08 | Phase 4 | Pending |
| FABR-09 | Phase 4 | Pending |
| CINV-01 | Phase 4 | Pending |
| CINV-02 | Phase 4 | Pending |
| CINV-03 | Phase 4 | Pending |
| CINV-04 | Phase 4 | Complete (deferrals discharged in Phase 7) |
| AGNT-01 | Phase 5 | Complete |
| AGNT-02 | Phase 5 | Complete |
| AGNT-03 | Phase 5 | Complete |
| XPRC-01 | Phase 6 | Delivered |
| XPRC-02 | Phase 6 | Delivered |
| XPRC-03 | Phase 6 | Delivered |
| ORCH-01 | Phase 7 | Complete |
| ORCH-02 | Phase 7 | Complete |
| HITL-01 | Phase 7 | Complete |
| EXPR-01 | Phase 7 | Complete |
| EXPR-02 | Phase 7 | Complete |
| EXPR-03 | Phase 7 | Complete |
| EXAM-01 | Phase 8 | Complete |
| EXAM-02 | Phase 8 | Complete |
| EXAM-03 | Phase 8 | Complete |
| EXAM-04 | Phase 8 | Complete |
| EXAM-05 | Phase 8 | Complete |
| EXAM-06 | Phase 8 | Pending |
| EXAM-07 | Phase 8 | Pending |
| EXAM-08 | Phase 8 | Pending |
| EXAM-09 | Phase 8 | Complete |
