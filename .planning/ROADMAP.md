# ROADMAP — CCF SDK

## Milestones

- [x] **v0.1** — Whitepaper-faithful v0 SDK: fabric core (L1–L6), Agent Specialization Framework, cross-process + harness adapters, orchestration/HITL/experience, eight-example suite, full CI. Completed 2026-07-31, tag `v0.1.0`, D-GATE-I. → [archive](.planning/milestones/v0.1-ROADMAP.md)
- [ ] **v0.2** — Performance, Documentation & Demonstration: hardening intake (WR-01/02/03 + posture rulings), reproducible perf battery with committed baselines and regression gates, synthetic-data end-to-end demonstration, upgraded examples suite, adopter-grade documentation suite. (current)

## Current Milestone: v0.2 Performance, Documentation & Demonstration

**Canonical authority:** `/home/parkave/ccf_code/CLAUDE.md` (revision 4). Every
phase ends with the §3.1 protocol: `/gsd-review` self-review → blocking/advisory
triage → STOP and present to Dave → approval logged as a `D-GATE` entry in
`docs/DECISIONS.md`. Six items in this milestone are gated on Dave rulings,
surfaced as one Phase D mini-cycle in Phase 9 (HARD-01); no gated item is
implemented before its ruling — implement per rulings only, never defaults.

**Phase ordering (research convergence):** harden first, measure second,
demonstrate, upgrade the examples, document last — docs describe hardened
postures, cite measured numbers, and literal-include the CI-run demonstration
and the upgraded examples.

## Phases

- [x] **Phase 9: Hardening — Defect Fixes & Ruling Batch** - Thread-safe HITL transports, loop-safe ADK driver, and the six-item D-IMPL ruling batch surfaced to Dave as one mini-cycle (completed 2026-08-01)
- [x] **Phase 10: Hardening — Authorization & Posture** - Per-tenant HITL door authorization, ApprovalGate × signed-binding composition, create_app posture warning — implemented per Dave's rulings (completed 2026-08-01)
- [ ] **Phase 11: Performance Battery** - `perf/` tree with four suites, deterministic synthetic dataset generator, committed runner-class-keyed baselines, `make perf`, opt-in regression-gated CI
- [ ] **Phase 12: Synthetic-Data Demonstration** - Fake data store + end-to-end data→context→agentic-reasoning example, running in CI
- [ ] **Phase 13: Examples Suite Upgrade** - v0.1 examples 00–07 upgraded with detailed narrated READMEs and richer scenarios/artifacts exercising more SDK surface, CI stays green
- [ ] **Phase 14: Documentation Suite** - mkdocs site with generated Protocol/API reference, adopter's guide, schema reference, security notes, PERFORMANCE.md, narrated demo walkthrough — `make docs --strict` in always-on CI

## Phase Details

### Phase 9: Hardening — Defect Fixes & Ruling Batch

**Goal**: The v0.1 audit's ruling-free defects are fixed and every decision-shaped v0.2 item has a Dave ruling on record, unblocking the rest of the milestone
**Depends on**: Nothing (first phase of v0.2; builds on v0.1.0 on `main`)
**Requirements**: HARD-01, HARD-02, HARD-03
**Success Criteria** (what must be TRUE):

  1. The six-item D-IMPL ruling batch (WR-01 mapping shape, ApprovalGate×D-16 composition, perf governance, docs toolchain/publishing, D-10 amendment, create_app warning) is presented to Dave as one Phase D mini-cycle and every ruling is logged in `docs/DECISIONS.md`
  2. In-memory HITL transports survive a threaded stress test (with timeout) without corruption or deadlock, and the HITLTransportProtocol carries a documented concurrency contract
  3. The ADK workflow driver runs inside an existing event loop with no nested `asyncio.run`, raises typed errors, and cross-adapter parity tests pass across all three drivers (WR-03 fixed before/with WR-02 so the sync/async seam is clean when locks arrive)
  4. The full eight-example CI sweep still passes byte-identically — no expected-output regeneration (any regeneration is a blocking review event)

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 09-01-PLAN.md — Six-item D-IMPL ruling batch mini-cycle with Dave + D-14 pre-phase hash manifest

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 09-02-PLAN.md — WR-03: shared loop-aware dispatch + typed driver errors across all three drivers + parity tests

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 09-03-PLAN.md — WR-02: threading.Lock transport + concurrency contract + hammer test + phase-close byte-identity check

### Phase 10: Hardening — Authorization & Posture

**Goal**: Every HITL door refuses unauthorized tenants by default and every audited human action carries the authorization decision — implemented exactly per the Phase 9 rulings
**Depends on**: Phase 9 (WR-01 mapping shape, ApprovalGate composition, create_app confirmation rulings)
**Requirements**: HARD-04, HARD-05
**Success Criteria** (what must be TRUE):

  1. An unauthorized principal hitting any HITL door (HTTP and MCP) for any action receives a typed 403 deny-by-default refusal, verified by a cross-door × cross-action test matrix
  2. Every authorization decision lands in the audit record; authorization stays out of `/src` core behind `TenantAuthorizerProtocol`, and the SDK invents no scope vocabulary
  3. ApprovalGate.resolve × signed_binding_required behaves per Dave's ruling, with tests pinning the composed behavior
  4. `create_app` on an insecure default posture emits a loud, visible warning (per the confirmed ruling), and examples 05/06 demonstrate tenant authorization

**Plans:** 4/4 plans complete

Plans:
- [x] 10-01-PLAN.md — Authz foundation: ScopeMappingArtifact, TenantAuthorizerProtocol + interpreter, audit extension, A1/A2 spikes
- [x] 10-02-PLAN.md — Signed-binding verification on all four primitive resolution surfaces (D-IMPL-69)
- [x] 10-03-PLAN.md — Door enforcement (HTTP + MCP) + cross-door × cross-action matrix (D-IMPL-68)
- [x] 10-04-PLAN.md — create_app insecure-default warning (D-IMPL-73), call-site sweep, examples 05/06 + manifest re-baseline

### Phase 11: Performance Battery

**Goal**: Adopters and CI can measure the hardened SDK reproducibly, with committed baselines and relative regression gates that catch real slowdowns without runner-variance flake
**Depends on**: Phase 10 (baselines must measure the hardened surface; perf-governance ruling from Phase 9)
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):

  1. `make perf` runs the micro-benchmark suite (operators, factory, validation gates) locally and reports p50/p95/p99 reproducibly
  2. Fabric load/scale curves for assembly and projection across graph sizes are produced from a deterministic, domain-neutral synthetic dataset generator that builds fixtures only through L2/factory paths (no lint-exempted shortcuts)
  3. Cross-process latency (MCP egress, A2A/peering) and replay-at-scale suites run and empirically support the year-scale replay claim
  4. An opt-in `perf.yml` CI job compares against committed runner-class-keyed baselines using relative-median thresholds from `perf/thresholds.toml`, and the re-baseline ritual is documented

**Plans:** 5 plans

Plans:
**Wave 1**

- [ ] 11-01-PLAN.md — Foundation: pytest-benchmark extra + A1 check, gate.py + thresholds.toml + gate unit tests, Makefile perf targets
- [ ] 11-02-PLAN.md — Synthetic generator: perf/synth/ neutral artifacts + seeded topology/decision stream, rung fixtures, determinism tests

**Wave 2** *(blocked on Wave 1)*

- [ ] 11-03-PLAN.md — Micro-benchmark suite (~10–15 benchmarks incl. composed-vs-sequential, run_coroutine_sync) + fabric-scale assembly/projection curves
- [ ] 11-04-PLAN.md — Cross-process latency suite (real subprocess MCP/peering) + replay-at-scale ladder with byte-exact + curve-shape assertions

**Wave 3** *(blocked on Wave 2)*

- [ ] 11-05-PLAN.md — Bitrot smoke test, opt-in perf.yml, perf/README.md re-baseline ritual, full-battery budget calibration

### Phase 12: Synthetic-Data Demonstration

**Goal**: A newcomer can run one command and watch raw synthetic data become governed context that lets an agent solve a problem it could not solve from the raw data alone
**Depends on**: Phase 10 (demonstrates hardened postures); independent of Phase 11
**Requirements**: DEMO-01, DEMO-02, DEMO-03
**Success Criteria** (what must be TRUE):

  1. A deterministic, multi-entity synthetic fake data store ships as the demonstration substrate, with every domain value in definition artifacts (No-Hardcoding — example code stays thin and generic)
  2. The runnable example ingests the store through L1→L2, folds it into the Context Graph, projects typed Context Products, and an agent consumes them to solve a concrete reasoning problem unreachable from raw data alone
  3. The demo runs in CI alongside the v0.1 examples with a single documented command, deterministically
  4. A narrated step-by-step walkthrough document ("how data folds into context") exists that literal-includes the example's code and artifacts by path, ready for the docs site

**Plans**: TBD

### Phase 13: Examples Suite Upgrade

**Goal**: The v0.1 examples suite (00–07) teaches the SDK on its own — every example narrates what it demonstrates and why, and its artifacts exercise enough SDK surface that an adopter can adapt it directly
**Depends on**: Phase 10 (hardened postures demonstrated — e.g., examples 05/06 tenant authorization); can run parallel to Phases 11/12
**Requirements**: EXAM-01, EXAM-02, EXAM-03
**Success Criteria** (what must be TRUE):

  1. Every example 00–07 has a detailed narrated README covering what it demonstrates, an artifact-by-artifact explanation, the whitepaper/CLAUDE.md sections exercised, and "what to change first to adapt it"
  2. Example scenarios exercise materially more SDK surface (specialization axes, skilling, HITL, replay) through richer definition artifacts, while example code stays thin and generic per the No-Hardcoding Rule
  3. The upgraded suite runs green in CI with a single documented command per example, and any expected-output change was a reviewed, deliberate event
  4. An adopter reading only an example's README and artifacts can identify the exact artifact to edit for their own domain — the code/artifact boundary is visible in every example

**Plans**: TBD

### Phase 14: Documentation Suite

**Goal**: A competent engineering team can go from install to a governed, replayable deployment using the docs alone — with every API signature generated, every number measured, and every snippet literal-included from CI-run code
**Depends on**: Phase 11 (measured baselines for PERFORMANCE.md), Phase 12 (demo walkthrough content), Phase 13 (docs literal-include the upgraded examples), Phase 9 (docs toolchain/publishing + D-10 rulings; reference generation may start in parallel with Phase 11)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06
**Success Criteria** (what must be TRUE):

  1. The adopter's guide walks day-1 to production (install → ontology → agent → workflow → replay) end-to-end, with every code snippet literal-included from CI-run examples — no pasted snippets, no hand-written signatures
  2. The Protocol/API reference is generated from the citation-bearing docstrings via mkdocs-material + mkdocstrings, and the site build provably never publishes the whitepaper or internal phase deliverables
  3. The definition-artifact schema reference covers the adopter's primary authoring surface, and how-to + concepts pages (pillars, invariants, replay anatomy, whitepaper cross-reference index) exist
  4. Security & deployment notes document the hardened postures from Phases 9–10, and the OpenAPI spec is regenerated from `create_app()` with a CI drift check
  5. `make docs --strict` passes in always-on CI (logged D-10 amendment), and PERFORMANCE.md publishes the Phase 11 measured baselines with methodology and environment manifest

**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 9. Hardening — Defect Fixes & Ruling Batch | 3/3 | Complete   | 2026-08-01 |
| 10. Hardening — Authorization & Posture | 4/4 | Complete    | 2026-08-01 |
| 11. Performance Battery | 0/? | Not started | - |
| 12. Synthetic-Data Demonstration | 0/? | Not started | - |
| 13. Examples Suite Upgrade | 0/? | Not started | - |
| 14. Documentation Suite | 0/? | Not started | - |

## Coverage

All 21 v0.2 requirements mapped, each to exactly one phase:
HARD-01..03 → 9; HARD-04..05 → 10; PERF-01..04 → 11;
DEMO-01..03 → 12; EXAM-01..03 → 13; DOCS-01..06 → 14.
