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
- [x] **Phase 11: Performance Battery** - `perf/` tree with four suites, deterministic synthetic dataset generator, committed runner-class-keyed baselines, `make perf`, opt-in regression-gated CI (completed 2026-08-02)
- [x] **Phase 12: Synthetic-Data Demonstration** - Fake data store + end-to-end data→context→agentic-reasoning example, running in CI (completed 2026-08-02)
- [x] **Phase 13: Examples Suite Upgrade** - v0.1 examples 00–07 upgraded with detailed narrated READMEs and richer scenarios/artifacts exercising more SDK surface, CI stays green (completed 2026-08-02)
- [x] **Phase 13.1: External-Consumer Examples (MCP Egress)** (INSERTED) - Independent agents built in their own harness (Anthropic SDK, ADK, bare MCP client) consume CCF context via MCP egress with zero CCF imports client-side — CCF as a black box; demonstrates §7.1 MCP-as-egress as the primary adoption path (completed 2026-08-02)
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

**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 11-01-PLAN.md — Foundation: pytest-benchmark extra + A1 check, gate.py + thresholds.toml + gate unit tests, Makefile perf targets
- [x] 11-02-PLAN.md — Synthetic generator: perf/synth/ neutral artifacts + seeded topology/decision stream, rung fixtures, determinism tests

**Wave 2** *(blocked on Wave 1)*

- [x] 11-03-PLAN.md — Micro-benchmark suite (~10–15 benchmarks incl. composed-vs-sequential, run_coroutine_sync) + fabric-scale assembly/projection curves
- [x] 11-04-PLAN.md — Cross-process latency suite (real subprocess MCP/peering) + replay-at-scale ladder with byte-exact + curve-shape assertions

**Wave 3** *(blocked on Wave 2)*

- [x] 11-05-PLAN.md — Bitrot smoke test, opt-in perf.yml, perf/README.md re-baseline ritual, full-battery budget calibration

### Phase 12: Synthetic-Data Demonstration

**Goal**: A newcomer can run one command and watch raw synthetic data become governed context that lets an agent solve a problem it could not solve from the raw data alone
**Depends on**: Phase 10 (demonstrates hardened postures); independent of Phase 11
**Requirements**: DEMO-01, DEMO-02, DEMO-03
**Success Criteria** (what must be TRUE):

  1. A deterministic, multi-entity synthetic fake data store ships as the demonstration substrate, with every domain value in definition artifacts (No-Hardcoding — example code stays thin and generic)
  2. The runnable example ingests the store through L1→L2, folds it into the Context Graph, projects typed Context Products, and an agent consumes them to solve a concrete reasoning problem unreachable from raw data alone
  3. The demo runs in CI alongside the v0.1 examples with a single documented command, deterministically
  4. A narrated step-by-step walkthrough document ("how data folds into context") exists that literal-includes the example's code and artifacts by path, ready for the docs site

**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 12-01-PLAN.md — Scenario artifact + deterministic SQLite demo generator + checksum pin tests (DEMO-01)

**Wave 2** *(blocked on Wave 1)*

- [x] 12-02-PLAN.md — run.py end-to-end: baseline contrast, L1→L6 pipeline, agent + cycle-detection skill, byte-compared narration, --live (DEMO-02)

**Wave 3** *(blocked on Wave 2)*

- [x] 12-03-PLAN.md — Makefile/CI wiring, README, docs/demo-walkthrough.md with literal includes (DEMO-03)

### Phase 13: Examples Suite Upgrade

**Goal**: The v0.1 examples suite (00–07) teaches the SDK on its own — every example narrates what it demonstrates and why, and its artifacts exercise enough SDK surface that an adopter can adapt it directly
**Depends on**: Phase 10 (hardened postures demonstrated — e.g., examples 05/06 tenant authorization); can run parallel to Phases 11/12
**Requirements**: EXAM-01, EXAM-02, EXAM-03
**Success Criteria** (what must be TRUE):

  1. Every example 00–07 has a detailed narrated README covering what it demonstrates, an artifact-by-artifact explanation, the whitepaper/CLAUDE.md sections exercised, and "what to change first to adapt it"
  2. Example scenarios exercise materially more SDK surface (specialization axes, skilling, HITL, replay) through richer definition artifacts, while example code stays thin and generic per the No-Hardcoding Rule
  3. The upgraded suite runs green in CI with a single documented command per example, and any expected-output change was a reviewed, deliberate event
  4. An adopter reading only an example's README and artifacts can identify the exact artifact to edit for their own domain — the code/artifact boundary is visible in every example

**Plans**: 5 plans

Plans:
**Wave 1**

- [x] 13-01-PLAN.md — Shared README template skeleton + CCF gloss table + [ADAPT]/[MECHANISM] marker convention (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 13-02-PLAN.md — Examples 00 + 01: enrichment + narrated READMEs; 01 exercises all six specialization axes meaningfully (Wave 2)
- [x] 13-03-PLAN.md — Examples 02 + 03 + 04: skilling depth, harness-portability (deterministic leg), A2A admission narration (Wave 2)
- [x] 13-04-PLAN.md — Examples 05 + 06: ReviewQueue into 05, OverrideBoundary into 06, replay-recorded HITL (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 13-05-PLAN.md — Example 07 enrichment + 08 README retrofit + suite-wide `make ci` phase gate (Wave 3)

### Phase 13.3: Review-Residual Hardening (INSERTED)

**Goal:** Close the actionable residuals from the Phase 13.2 cross-AI review (13.2-REVIEWS.md consensus items that were not resolved by execution): (1) allowlist fail-fast semantics — `ValueError` on unknown `tool_allowlist` entries and a serve-time assert that artifact `tools.*.name` values equal the SDK tool constants; (2) mandatory fingerprint-mismatch unit test plus fail-loud replay startup when a response fixture lacks its `*-request.json` sibling; (3) capture-proxy spec tightening — record only HTTP 200 + JSON bodies, forward query strings, never persist headers; (4) CINV-01 consistency — parameterize (or explicitly exempt and pin with a test) the `list_agents`/`invoke_agent` tool descriptions that still ship as docstring prose.
**Requirements**: EXAM-05 (hardening residuals)
**Depends on:** Phase 13.2
**Plans:** 2/2 plans complete

Plans:

- [x] 13.3-01-PLAN.md — SDK builder hardening: allowlist fail-fast, Optional providers, CINV-01 description parameterization (D-01/D-03/D-04/D-12–14) + builder pinning tests (Wave 1)
- [x] 13.3-02-PLAN.md — Example-side hardening: serve.py artifact-name assert, replay orphan scan + path fingerprint, capture-proxy 200+JSON/query spec + permanent tests/examples/ guards (Wave 2)

### Phase 13.2: external-example-hardening (INSERTED)

**Goal:** Harden `examples/external/00-hello-context` against the four-AI cross-review consensus concerns — live-captured diff-reviewed fixtures with a permanent schema guard and request-fingerprint replay matching, a server-side tool allowlist, and byte-path/README/duration assertion hardening — and execute Dave's 2026-08-02 ruling promoting `get_context`, `get_lineage`, and `get_replay_record` into the SDK Experience surface, enabled by default.
**Requirements**: EXAM-05
**Depends on:** Phase 13.1
**Plans:** 5/5 plans complete

Plans:

**Wave 1**

- [x] 13.2-01-PLAN.md — SDK promotion (D-13) + allowlist parameter (D-05) in experience.py, caller/test updates, EXAM-05 minting, D-IMPL entry (D-14)

**Wave 2** *(blocked on Wave 1)*

- [x] 13.2-02-PLAN.md — serve.py shrinks to composition (D-15); artifact-driven 3-tool allowlist wired

**Wave 3** *(blocked on Wave 2)*

- [x] 13.2-03-PLAN.md — Live fixture capture (D-01a/D-02), capture proxy, fixture-diff utility (D-04), D-10 reviewed regeneration (checkpoint)

**Wave 4** *(blocked on Wave 3)*

- [x] 13.2-04-PLAN.md — Fingerprint-checked replay (D-03) + fixture schema smoke-test (D-01b)
- [x] 13.2-05-PLAN.md — run.py assertion hardening (D-07/08/09 + allowlist visibility), .mcp.json docs verification (D-12), fresh-venv one-off (D-11), `make ci` phase gate

### Phase 13.1: External-Consumer Examples (MCP Egress) (INSERTED)

**Goal:** An engineer with an existing agent in their own harness (Anthropic SDK, Google ADK, or a bare MCP client) can point it at the CCF MCP egress server and consume decision-ready, typed Context Products — with zero CCF imports on the client side. CCF operates as a black box behind MCP; the replay record still lands on the fabric side. This demonstrates §7.1 MCP-as-egress / §8.3 Experience Layer as the primary adoption path, rather than asserting it.
**Rationale (Dave, 2026-08-02):** Users must never be forced to construct agents inside CCF — that becomes tech debt. The harness-independent MCP consumption path is the most important example set the suite needs.
**Requirements**: EXAM-04
**Suggested scope:** `examples/external/00-hello-context` (locked D-01 layout — new `examples/external/` family unified by consumption model, examples 00–08 unchanged): four client legs (`client_bare.py`, `client_anthropic.py`, `client_adk.py`, plus the `.mcp.json` leg), CCF only as an authenticated MCP server URL; family charter README per D-02/D-03; runnable in CI (`make example-ext-00`), deterministic leg for CI plus optional live leg.
**Depends on:** Phase 13. Must land before Phase 14 (Documentation Suite) so the docs can literal-include it.
**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 13.1-01-PLAN.md — Groundwork: mint EXAM-04, add `anthropic` extra, `examples/external/` family charter README
- [x] 13.1-02-PLAN.md — Fabric side: finserv artifacts, serve.py (authed experience MCP + get_context/lineage/replay tools + serve-side replay), replay_server.py

**Wave 2**

- [x] 13.1-03-PLAN.md — Client legs: client_bare.py, client_anthropic.py, client_adk.py + versioned model-API fixtures

**Wave 3**

- [x] 13.1-04-PLAN.md — run.py assertions (401, D-15, D-16, zero-CCF-import grep), seven-heading README + .mcp.json leg, Makefile/CI wiring

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

**Plans**: 10 plans in 4 waves

Plans:
**Wave 1**

- [x] 14-01-PLAN.md — docs toolchain foundation: `docs` extra, `site/` gitignored, `public/` docroot + stubs, `mkdocs.yml` with `check_paths: true` and raised link validation
- [x] 14-02-PLAN.md — `tools/publish_scan.py` never-publish gate (no allowlist) + its controls, then the D-20 rework of the 13 whitepaper-quoting docstrings

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 14-03-PLAN.md — committed `openapi.json`, `make openapi` regenerator, and the always-on drift assertion against `create_app()`
- [x] 14-04-PLAN.md — D-03 move: `git mv` walkthrough, security notes and all 11 diagrams into `public/`; repoint inbound refs; Dave rules the CLAUDE.md edit

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 14-05-PLAN.md — Concepts section: five pillar pages with in-page diagrams, invariants, replay anatomy, whitepaper cross-reference index, diagram-coverage test
- [ ] 14-06-PLAN.md — Reference section: 12 curated Protocol pages, 8 generated artifact-schema pages, the HTTP contract page, and the mkdocstrings drift control
- [x] 14-07-PLAN.md — snippet markers in six example sources + the adopter's guide, all literal-included; snippet drift control
- [ ] 14-08-PLAN.md — five task how-to pages over green CI-run examples + the security & deployment page finished as a how-to
- [x] 14-09-PLAN.md — run the perf battery, Dave-gated baseline commit (D-IMPL-75), PERFORMANCE.md with methodology and environment manifest

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 14-10-PLAN.md — `docs-strict` gate target, `make ci` D-IMPL-72 amendment, always-on CI docs job with artifact upload

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 9. Hardening — Defect Fixes & Ruling Batch | 3/3 | Complete   | 2026-08-01 |
| 10. Hardening — Authorization & Posture | 4/4 | Complete    | 2026-08-01 |
| 11. Performance Battery | 5/5 | Complete    | 2026-08-02 |
| 12. Synthetic-Data Demonstration | 3/3 | Complete    | 2026-08-02 |
| 13. Examples Suite Upgrade | 5/5 | Complete   | 2026-08-02 |
| 14. Documentation Suite | 6/10 | In Progress|  |

## Coverage

All 21 v0.2 requirements mapped, each to exactly one phase:
HARD-01..03 → 9; HARD-04..05 → 10; PERF-01..04 → 11;
DEMO-01..03 → 12; EXAM-01..03 → 13; DOCS-01..06 → 14.
