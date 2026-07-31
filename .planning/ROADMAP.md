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
- [x] **Phase 6: Phase I.3 — Cross-Process & Harness Adapters** - Bidirectional MCP, A2A federation, HarnessAdapterProtocol + reference adapters (completed 2026-07-28)
- [x] **Phase 7: Phase I.4 — Orchestration, HITL, Experience** - Workflow primitive, HITL primitives, MCP egress / CLI / HTTP front doors (completed 2026-07-31)
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

- [x] 08-01-PLAN.md — Scaffold: phase-i5 branch, editable-install refresh, Makefile (ci-core/help), lint posture over /examples

**Wave 2**

- [x] 08-02-PLAN.md — Hardening A: D-15 remove `ccf hitl decide`, fail-closed TokenGrant branch, typed error-code constants (incl. ERROR_SIGNED_BINDING_*)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 08-03-PLAN.md — Hardening B: D-16 signed-binding requiredness + door mapping (HTTP/MCP), R1 was-called assertions
- [x] 08-04-PLAN.md — Hardening C: ADK SequentialAgent migration, D-IMPL-62 verb note, key-management doc note
- [x] 08-05-PLAN.md — examples/00-quickstart (banking) — convention template for Wave 4

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 08-06-PLAN.md — examples/01-agent-basics (field-service) + 02-skilling (clinical-trials ops)
- [x] 08-07-PLAN.md — examples/04-cross-process (property-intelligence, fresh artifacts)
- [ ] 08-08-PLAN.md — examples/05-workflow-hitl (banking, auth-bound) + 06-decision-replay (energy/grid-ops)
- [ ] 08-09-PLAN.md — examples/07-artifact-store-mcp (logistics, store swap)
- [ ] 08-10-PLAN.md — examples/03-harness-portability deterministic leg (e-commerce) + A3 discharge

**Wave 5**

- [ ] 08-11-PLAN.md — example 03 live legs: Ollama (default) + Anthropic (gated), decision table, structural equivalence

**Wave 6**

- [ ] 08-12-PLAN.md — CI examples job + opt-in live-legs workflow + full local sweep + README contract check

**Wave 7**

- [ ] 08-13-PLAN.md — v0 packaging (README, 0.1.0), Phase I gate: /gsd-review, Dave approval, D-GATE-I, merge, tag v0.1.0
**Process notes**: Model mandate — Opus 5 (fallback Opus 4.8), "high" effort. Branch: `phase-i5`. Ends with `/gsd-review --phase Phase I --all` → triage → Dave approval → `D-GATE-I` before v0 is declared. Homecams-on-SDK rebuild is post-v0 (deferred).

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Phase R — Research | 12/12 | Complete   | 2026-07-25 |
| 2. Phase D — Design | 11/11 | Complete   | 2026-07-25 |
| 3. Phase F — Feasibility & Scoping | 4/4 | Complete   | 2026-07-25 |
| 4. Phase I.1 — Fabric Core | 12/12 | Complete | 2026-07-25 |
| 5. Phase I.2 — Agent Specialization Framework | 10/10 | Complete   | 2026-07-26 |
| 6. Phase I.3 — Cross-Process & Harness Adapters | 25/25 | Complete   | 2026-07-28 |
| 7. Phase I.4 — Orchestration, HITL, Experience | 20/20 | Complete   | 2026-07-31 |
| 8. Phase I.5 — Examples Suite & Full CI Verification | 7/13 | In Progress|  |

## Coverage

All 46 v1 requirements mapped, each to exactly one phase:
RSCH-01..04 → 1; DSGN-01..04 → 2; FEAS-01..04 → 3;
FABR-01..09 + CINV-01..04 → 4; AGNT-01..03 → 5; XPRC-01..03 → 6;
ORCH-01..02 + HITL-01 + EXPR-01..03 → 7; EXAM-01..09 → 8.
