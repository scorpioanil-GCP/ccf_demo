# ROADMAP — CCF SDK

## Milestones

- [x] **v0.1** — Whitepaper-faithful v0 SDK: fabric core (L1–L6), Agent Specialization Framework, cross-process + harness adapters, orchestration/HITL/experience, eight-example suite, full CI. Completed 2026-07-31, tag `v0.1.0`, D-GATE-I. → [archive](.planning/milestones/v0.1-ROADMAP.md)
- [ ] **v0.2** — Performance, Documentation & Demonstration: hardening intake (WR-01/02/03 + posture rulings), reproducible perf battery with committed baselines and regression gates, synthetic-data end-to-end demonstration, upgraded examples suite, adopter-grade documentation suite. (current)
- [ ] **v0.3** — Assembly Modes: close the whitepaper-fidelity gap in which two of the three Assembly Modes (§7.6) are declarable but undemonstrated. Pattern 5 unstructured ingestion (D-IMPL-08), a credit-memo exemplar demonstrating Mode 2 (`llm_packaged`) and Mode 3 (`swarm_assembled`) agent-swarm assembly over structured *and* unstructured sources with A2A coordination, and Part 2 of the two-part assembly document. (planned — see `14-HUMAN-UAT.md` G-02 for the evidence)

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
- [x] **Phase 14: Documentation Suite** - mkdocs site with generated Protocol/API reference, adopter's guide, schema reference, security notes, PERFORMANCE.md, narrated demo walkthrough — `make docs --strict` in always-on CI (10/10 plans executed and verified 5/5; **closed as-shipped 2026-08-03**. The G-01 framing defect stands deliberately: the docs describe an integration surface Phase 15 will replace, so the fix lands in Phase 16 against the new surface rather than twice against the old one. The published site carries no provisional banner — this note is roadmap-internal, per Dave, 2026-08-03)
- [ ] ~~**Phase 14.1: Documentation — The Deterministic Path & The Adoption Argument** (INSERTED)~~ — **SUPERSEDED by Phase 16**, 2026-08-03, before any plan was written. Every success criterion is absorbed there
- [x] **Phase 15: SDK Ergonomics — The Integration Surface** (INSERTED) - Loaders, artifact classes, factories, and wiring helpers so the day-1 integration is a fraction of today's ~450-line example; abstraction line held at marshalling-and-wiring so no governance decision leaves adopter code and no replay dimension is hidden (completed 2026-08-05)
- [ ] **Phase 15.1: Ergonomics Gap Closure — Governance Enforced, Not Conventional** (INSERTED) - Closes the two HIGH defects found by post-gate cross-AI review (D-GATE-15 amendment, 2026-08-05): CR-1, author-versioned classes can bypass the D-05 bump check through the manifest, closed by a per-entry `registration: typed | versioned` mode that `load_and_boot` dispatches on and **refuses** when an author-versioned class asks for `typed`; CR-2, Gate 2 (INV-CH7-47) is self-satisfying in all nine examples because lineage and `engine_resolved` are filled from the same `execution.operators_invoked` — and the remedy the review prescribed is itself circular, since `execution.operators_invoked ≡ frozenset(declared.required_operator_keys)` through five pure transforms. Closed instead by **design E2** (D-IMPL-86, Dave, 2026-08-05): the projection's required operator set becomes its own Control Plane artifact, a binder refuses when it diverges from the product-class declaration, and Gate 2 is documented for what it actually verifies — assembly-path integrity. Also corrects `SURFACE-AUDIT.md` §4.1, whose "eight instances" is an undercount, and restates the new AST gates as tripwires rather than structural enforcement (URGENT — Phase 16 must not document a self-satisfying gate)
- [ ] **Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument** - One document, two sections (deterministic + external MCP consumption; CCF-agent assembly + MCP/A2A consumption), banking scenarios from the whitepaper, re-cut snippet markers so a reader can see which code is CCF and which is theirs

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

- [x] 14-05-PLAN.md — Concepts section: five pillar pages with in-page diagrams, invariants, replay anatomy, whitepaper cross-reference index, diagram-coverage test
- [x] 14-06-PLAN.md — Reference section: 12 curated Protocol pages, 8 generated artifact-schema pages, the HTTP contract page, and the mkdocstrings drift control
- [x] 14-07-PLAN.md — snippet markers in six example sources + the adopter's guide, all literal-included; snippet drift control
- [x] 14-08-PLAN.md — five task how-to pages over green CI-run examples + the security & deployment page finished as a how-to
- [x] 14-09-PLAN.md — run the perf battery, Dave-gated baseline commit (D-IMPL-75), PERFORMANCE.md with methodology and environment manifest

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 14-10-PLAN.md — `docs-strict` gate target, `make ci` D-IMPL-72 amendment, always-on CI docs job with artifact upload

### Phase 14.1: Documentation — The Deterministic Path & The Adoption Argument (SUPERSEDED)

**Status**: superseded by Phase 16, 2026-08-03, before any plan was written. Dave's
discuss-phase read of the SDK surface found a defect underneath the documentation defect:
the integration surface the docs describe is itself too verbose to document well. Rewriting
the documentation against a surface we intend to change is wasted work, so the ergonomics
pass (Phase 15) comes first and the documentation rewrite (Phase 16) follows it, carrying
every success criterion below plus the structure Dave specified in this discussion.

Nothing in this entry is dropped — see Phase 16, which absorbs it whole.

### Phase 15: SDK Ergonomics — The Integration Surface

**Goal**: The day-1 integration an adopter writes against CCF is a fraction of what it is
today, because the SDK absorbs the mechanical work it currently leaves to every deployment —
without hiding one governance decision from the adopter or one dimension from the replay
record
**Depends on**: Phase 14 (closed as-shipped; its documentation stands as the record of the
surface being replaced)
**Requirements**: ERGO-01..ERGO-17 (minted 2026-08-04; see `.planning/REQUIREMENTS.md`)
**Origin**: Dave, 2026-08-03, coding against the CCF SDK documentation. "The whole purpose of
the SDK is to provide as much abstraction around details as possible and save me the time of
doing them manually."

**The evidence that opened it** (measured against `examples/00-quickstart/run.py`, 451 lines):

  - ~85 lines are CI assertions and print summaries — no adopter writes them, but they are
    inside the published snippets, inflating the apparent integration cost
  - ~105 lines are YAML→typed-object marshalling: `_resolution_spec`, `_envelopes`, and four
    hand-built operator parameter sets. `src/ccf/controlplane/artifacts.py` registers exactly
    **two** artifact classes with a declarative parse path (`ccf.half-life-table`,
    `ccf.debt-profile`); every other artifact shape is marshalled by hand in example code
  - ~45 lines are the projection Π — genuinely deployment code (whitepaper §7.5) and not a
    target
  - ~55 lines are the actual CCF call spine — roughly eight calls, L1 through L6

  The No-Hardcoding Rule (CLAUDE.md §6.4) pushed the *values* into artifacts correctly and
  left most of the *interpreters* in `/examples`, where they are copy-paste fodder. §6.4 says
  code contains interpreters and factories, never the things interpreted — the interpreter
  for half-life tables lives in `/src` where it belongs; the interpreter for operator
  parameters does not exist.

**Success Criteria** (what must be TRUE):

  1. A holistic audit of the adopter-facing surface exists, naming every point where a
     deployment writes mechanical code the SDK could supply, with the day-1 line count
     measured before and after
  2. Declarative artifact classes and loaders cover the shapes an adopter must currently
     hand-marshal — resolution specs, signal envelopes, operator parameters, product-class
     declarations, perspectives — reached through the same `parse_artifact` seam that already
     serves half-life tables and debt profiles
  3. Boot, registry population, and operator-registry construction are reachable from
     artifacts without per-deployment wiring code
  4. Every shipped helper is answerable to "what does this hide from the replay record?" with
     "nothing" — the abstraction line is **marshalling and wiring only** (D-15A below)
  5. The eight-example suite and `examples/external/` are rewritten to the streamlined
     surface and stay CI-green, with the day-1 example demonstrably smaller
  6. Every removed or reshaped public surface is recorded, so Phase 16 can document the
     surface that exists rather than the one that was

**Rulings carried in from the discussion (Dave, 2026-08-03):**

  - **D-15A — the abstraction line is marshalling and wiring only.** Helpers may absorb
    YAML→typed-object loading, registry population, boot wiring, and operator construction
    from artifacts. Every point where a deployment *asserts something the fabric then
    verifies* stays explicit in adopter code. The worked case: `run_gates()` takes the
    engine's resolved operators separately from the product's own lineage claim precisely so
    lineage strict equality has two independent sources; a helper computing both from one
    input would make the gate tautological and silently delete a whitepaper invariant.
    Dave reserves the right to revisit surface by surface where an ergonomic win requires
    touching a governance boundary — such cases are surfaced as decisions, not resolved by
    the phase.
  - **D-15B — free rein on the public API, pre-1.0.** The phase may reshape, rename, collapse,
    or remove any public surface in the way; examples and docs are rewritten to match.
    `v0.1.0` stays tagged as the historical artifact. Anyone building against v0.1/v0.2 today
    has a migration, and that is accepted.

**Non-goals**: new fabric capability; demonstrating Assembly Modes 2 or 3 (v0.3); the
documentation rewrite itself (Phase 16). Simplification that costs an invariant is not
simplification — it is a fidelity defect, and CLAUDE.md §1 ranks fidelity first.

**Plans**: 21 plans across 14 waves

Plans:
**Wave 1** — the public-surface baseline (nothing else may start first)

- [x] 15-01-PLAN.md — Public-surface baseline: `tools/dump_surface.py` (`--check` + `--report`), committed manifest, documented-drift gate, surface-change fragment home (ERGO-01, ERGO-17)

**Wave 2** — standing guards, built on the baseline

- [x] 15-02-PLAN.md — `ccf.deployment` package shell + the D-15A gate-independence guard + the no-allowlist import ban (ERGO-02, ERGO-04)
- [x] 15-03-PLAN.md — Executable surface audit baseline + falsification of research assumptions A1/A3/A6 (ERGO-03)

**Wave 3**

- [x] 15-04-PLAN.md — D-IMPL-78: widen CINV-01 over `tests/` (two edits: `LINTED_TREES` and `RULE_TREE_SCOPE`) (ERGO-16)
- [x] 15-05-PLAN.md — D-02 timestamp handling in the artifact load path (ERGO-06)
- [x] 15-06-PLAN.md — class-id → `ArtifactClass` lookup + `tests/deployment/` package (ERGO-05)

**Wave 4**

- [x] 15-07-PLAN.md — `ccf.resolution-spec` + `EntityResolutionSpec` semver in place, with its own regeneration checkpoint (D-IMPL-77) (ERGO-07)

**Wave 5**

- [x] 15-08-PLAN.md — Four operator-parameters artifact classes + both `artifacts.py` docstring amendments (ERGO-08)

**Wave 6**

- [x] 15-09-PLAN.md — Signal-batch, perspective, and product-class artifact classes (ERGO-09)

**Wave 7**

- [x] 15-10-PLAN.md — `ccf.deployment-manifest` + `load_and_boot` + the plain pin set (ERGO-10)

**Wave 8**

- [x] 15-11-PLAN.md — `build_operator_registry`, two-phase and view-aware, pin set passed in (D-IMPL-76) (ERGO-11)
- [x] 15-12-PLAN.md — Committed JSON Schemas + `ccf schema export` through an HTTP route (D-IMPL-79) (ERGO-12)

**Wave 9**

- [x] 15-13-PLAN.md — Rewrite example 00 quickstart — the day-1 integration (ERGO-13, ERGO-16, ERGO-12)

**Wave 10**

- [x] 15-14-PLAN.md — Rewrite examples 01 agent-basics and 02 skilling (ERGO-13, ERGO-16, ERGO-12)
- [x] 15-15-PLAN.md — Rewrite examples 03 harness-portability and 07 artifact-store-mcp (ERGO-13, ERGO-16, ERGO-12)
- [x] 15-16-PLAN.md — Rewrite example 08 e2e-demo + the DEMO-03 narration review (ERGO-13, ERGO-16, ERGO-12)

**Wave 11**

- [x] 15-17-PLAN.md — Rewrite example 06 decision-replay, pins kept explicit (ERGO-14, ERGO-16, ERGO-12)
- [x] 15-18-PLAN.md — Rewrite example 04 cross-process + re-domain to banking, as two commits (ERGO-14, ERGO-16, ERGO-12)

**Wave 12**

- [x] 15-19-PLAN.md — Rewrite example 05 workflow-hitl (ERGO-14, ERGO-16, ERGO-12)

**Wave 13**

- [x] 15-20-PLAN.md — Rewrite the external example's `serve.py`, client legs untouched (ERGO-15, ERGO-12)

**Wave 14**

- [x] 15-21-PLAN.md — Phase close: curated surface-change log, the single manifest regeneration and criterion-1 audit, the tree-wide `$schema` and D-14 gates, `/gsd-review` and presentation to Dave (ERGO-01, ERGO-03, ERGO-12, ERGO-17)

### Phase 15.1: Ergonomics Gap Closure — Governance Enforced, Not Conventional (INSERTED)

**Goal**: The two governance guarantees Phase 15 shipped as *convention* become guarantees the code *enforces* — a manifest cannot route an author-versioned artifact class around the D-05 bump check, and the operator set a deployment declares can no longer agree with the set it executes by construction, because the two now come from separately authored artifacts bound by a check — placed between plan construction and `ProjectionEngine.execute`, per the D-IMPL-86 correction of 2026-08-05 — that refuses when they disagree (design E2, D-IMPL-86)
**Depends on**: Phase 15 (closed and gated; D-GATE-15 amended rather than revoked)
**Blocks**: Phase 16 — the documentation rewrite must not describe a self-satisfying gate
**Requirements**: ERGO-18, ERGO-19
**Requirements note**: ERGO-18/19 are minted during this phase's first plan, per the Phase 15/16 precedent recorded in §Coverage. ERGO-01..17 stay Complete — this phase closes defects in what they delivered, it does not reopen them.
**Origin**: Post-gate cross-AI design review commissioned by Dave after D-GATE-15, on
discomfort with the shipped state (`15-REVIEWS-round3.md`, 2026-08-05). Four independent
systems — gemini, codex, cursor, ollama — reviewed the *shipped code*, not the plans, against
"is this a sound design approach, and should this phase have shipped at all?" All four: sound,
yes. Risk LOW (gemini), MEDIUM (codex, cursor). Two HIGH defects, each verified against source
by the orchestrator rather than accepted on report.

**The two confirmed defects:**

  - **CR-1 — author-versioned classes can bypass the D-05 bump check via the manifest.**
    `SDK_ARTIFACT_ROLES` fixes exactly one class, `ccf.signal-batch`.
    `refuse_role_the_sdk_fixes` accepts `role: register` for `ccf.workflow-definition`,
    `ccf.agent-definition` and `ccf.task-definition`, all of which then route through
    `register_typed` — which runs no hash-verified bump check. The 15-19 split ruling is a
    convention the shipped examples follow, not an enforced invariant:
    `test_the_author_versioned_definitions_kept_their_bump_check` proves the examples do it
    right; nothing proves the manifest refuses the wrong thing. Raised independently by codex
    and cursor; gemini raised the same split as its only HIGH. Codex stated the falsifiable
    test: "If adopters can put workflow/task/agent definitions in the manifest with
    `role: register` and thereby use `register_typed`, the design is unsound."
  - **CR-2 — Gate 2 is self-satisfying in every example, a NINTH instance of the phase's own
    signature finding.** Verified across 9 files: each constructs
    `ProductLineage(operators_invoked=execution.operators_invoked, ...)` and then calls
    `run_gates(candidate, engine_resolved=execution.operators_invoked)` — the same value on
    both sides of lineage strict equality. Files: `00-quickstart`, `01-agent-basics`,
    `02-skilling`, `03-harness-portability`, `04-cross-process/producer_child`,
    `06-decision-replay`, `07-artifact-store-mcp`, `08-e2e-demo`,
    `external/00-hello-context/serve`. The phase closed the *upstream* `required_operators()`
    collapse and numbered around this one; `test_gate_independence.py` admits callers outside
    `ccf.deployment` may pass the same value twice. Raised by cursor alone.

**The fix all three substantive reviewers converged on, independently**: a per-entry
registration mode in the manifest — `registration: typed | versioned` — that `load_and_boot`
dispatches on, routing author-versioned classes to `register_versioned` and **refusing** any
manifest that registers them through `register_typed`. Everything stays in the manifest; one
mental model; governance enforced rather than conventional. Gemini's variant:
`version_policy: strict_bump`. Codex adds "tests proving workflow/task/agent definitions
cannot bypass bump checks through the manifest." Cursor: "same ergonomics win without the
split." Both codex and cursor called the shipped split **backwards** — the more
governance-sensitive the artifact, the *less* declarative Phase 15 made it.

**Success Criteria** (what must be TRUE):

  1. A manifest that declares an author-versioned class (`ccf.workflow-definition`, `ccf.agent-definition`, `ccf.task-definition`) for typed registration is **refused at load**, with a test that asserts the refusal — not a test that the examples happen to avoid the pattern
  2. The registration mode is declared per entry in the manifest and dispatched by `load_and_boot`; the artifact author does not have to know which of two registration paths their class belongs to
  3. `lineage.operators_invoked` is filled from the product-class declaration — never from `execution.operators_invoked` — in every example that runs Gate 2, and the projection's required operator set comes from its own Control Plane artifact rather than from the product-class artifact, so the declared and executed sets are separately authored (D-IMPL-86, design E2)
  4. A binder **refuses** when `product_class.required_operator_keys != frozenset(plan.required_operators())`, placed where a plan exists — between plan construction and `ProjectionEngine.execute`, **not** inside `load_and_boot`, which has no plan in scope (D-IMPL-86 correction, 2026-08-05) — and a test proves the refusal fires when the two artifacts are edited into disagreement. This is where authorable drift fails, and it is reachable by editing an artifact rather than only by writing a bug. The residual the placement creates — nothing outside `examples/` holds a deployment to calling the binder — is named in the deliverables and surfaced at the gate, not left in a docstring
  5. Gate 2 is documented for what it verifies — **assembly-path integrity**, the claim transcribed into the Contract equalling the engine's execution of the plan — and every site asserting that it compares two independently authored sets is corrected, including `src/ccf/products/gates.py:14-17` and `:244-250`, the `ProductClassDeclaration` docstring at `src/ccf/controlplane/artifacts.py:514-521`, and `docs/SURFACE-AUDIT.md` §3.1 item 1. D-IMPL-57's intra-fabric "the engine's resolution is an independent witness" premise is corrected with it: the engine is a faithful transcriber of the plan, which holds under every design considered
  6. A tripwire refuses any call site filling both of Gate 2's arguments from `execution`, closing the shape CR-2 found
  7. `docs/SURFACE-AUDIT.md` §4.1 is corrected: "eight instances" is an undercount, and the ninth (the Gate 2 call-site pattern) is entered with the same accounting discipline
  8. The new AST gates are restated as **tripwires** — they catch known patterns — rather than as structural enforcement on par with single-writer DI, strengthened by D-IMPL-86's finding that no AST gate can distinguish an authored literal from a transcribed one
  9. The public-surface manifest and the `--check` drift gate stay green; no replay dimension is hidden by anything this phase adds

**Scope amendment (Dave, 2026-08-05, D-IMPL-86):** the original "two HIGH items only" ruling
is widened by design E2, which adds a projection-requirements artifact class and a
binder — new mechanism, not defect closure. E2 also revises the gated 15-09 decision, so this
phase runs as a Phase D mini-cycle under CLAUDE.md §3.1 with D-IMPL-86 as the ruling of record.
Rationale: shipping the cheaper option first would have Phase 16 document an "assembly-path
integrity" framing that a later phase then rewrites — Phase 14's G-01 defect repeated.

**Non-goals** (everything else the two-HIGHs ruling excluded still stands):
reopening the Phase 15 abstraction line (D-15A stands); **D-IMPL-81** (pinning the manifest
itself) — ruled out, it stays open debt against Phase 16 or later; **codex's per-gate
independence matrix** (`Invariant | Declared source | Observed source | Test proving they can
diverge`, with a divergence test for every gate) — ruled out, CR-2's mutation test covers
Gate 2 only; the Phase 16 documentation rewrite; the remaining agreed concerns from the review
that are not the two HIGH items — `BootedFabric.artifacts` role blurring and erosion pressure
are recorded, not closed here.

**Plans**: 10 plans in 7 waves

Plans:
- [x] 15.1-01-PLAN.md — mint ERGO-18/19, widen `ControlPlaneProtocol` with `register_versioned` (D-IMPL-82), add the `ccf.projection-requirements` artifact class (E2), widen the surface-change fragment glob
- [x] 15.1-02-PLAN.md — `registration: typed | versioned` required-no-default on `ManifestEntry` (D-IMPL-85), dispatch in `load_and_boot`, `ArtifactPin.registration` (D-IMPL-83), 163-entry migration
- [x] 15.1-03-PLAN.md — `SDK_VERSIONED_ARTIFACT_CLASSES`, the registration refusal, the `ccf.`-namespace reservation (D-IMPL-84), and the four refusal tests
- [x] 15.1-04-PLAN.md — the binder `refuse_operator_set_divergence` (E2 element 3) and its divergence/agreement pair
- [x] 15.1-05-PLAN.md — examples 00, 01, 02 onto E2: lineage from the product-class claim, plan from the projection-requirements artifact, binder call
- [x] 15.1-06-PLAN.md — examples 03, 04-producer, 07 onto E2
- [x] 15.1-07-PLAN.md — examples 06, 08, external/00 onto E2; the two correct replay legs and `test_ext00_hardening.py` left untouched
- [x] 15.1-08-PLAN.md — the Gate 2 call-shape tripwire (E2 element 5), the binder-call coverage check, and example-scale divergence coverage
- [x] 15.1-09-PLAN.md — documentation corrections: `gates.py` both sites, `ProductClassDeclaration`, `SURFACE-AUDIT` §3.1 and §4.1 (nine), tripwire restatement, D-IMPL-57's premise
- [ ] 15.1-10-PLAN.md — phase close: surface regeneration, criterion evidence, `/gsd-review` + triage, present to Dave (checkpoint)

**Waves**: 1 → 01; 2 → 02; 3 → 03; 4 → 04; 5 → 05, 06, 07 (parallel); 6 → 08, 09 (parallel); 7 → 10 (checkpoint)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 9. Hardening — Defect Fixes & Ruling Batch | 3/3 | Complete   | 2026-08-01 |
| 10. Hardening — Authorization & Posture | 4/4 | Complete    | 2026-08-01 |
| 11. Performance Battery | 5/5 | Complete    | 2026-08-02 |
| 12. Synthetic-Data Demonstration | 3/3 | Complete    | 2026-08-02 |
| 13. Examples Suite Upgrade | 5/5 | Complete   | 2026-08-02 |
| 13.1. External-Consumer Examples (MCP Egress) | 4/4 | Complete   | 2026-08-02 |
| 14. Documentation Suite | 10/10 | Complete   | 2026-08-03 (verified 5/5; G-01 deliberately deferred to 16) |
| 14.1. Docs — Deterministic Path & Adoption Argument | — | Superseded by 16 | — |
| 15. SDK Ergonomics — The Integration Surface | 21/21 | Complete    | 2026-08-05 (gated with carried debt; CR-1/CR-2 close in 15.1) |
| 15.1. Ergonomics Gap Closure — Governance Enforced, Not Conventional | 9/10 | In Progress|  |
| 16. Documentation Rewrite — Deterministic Path & Adoption Argument | 0/? | Planned   | — |

## Coverage

All **42** v0.2 requirements mapped, each to exactly one phase — the figure
`.planning/REQUIREMENTS.md`'s traceability table carries, counted from it rather
than remembered. It arrives in two halves.

The **21 defined at milestone definition** (2026-08-01), which is what this
sentence used to count before inserted phases minted more and the number was left
behind (corrected 2026-08-05 at the Phase 15.1 close, flagged by plan 15.1-01):
HARD-01..03 → 9; HARD-04..05 → 10; PERF-01..04 → 11;
DEMO-01..03 → 12; EXAM-01..03 → 13; DOCS-01..06 → 14.

The **21 minted since**, by inserted phases at their own planning:
EXAM-04 → 13.1; EXAM-05 → 13.2; ERGO-01..17 → 15; ERGO-18..19 → 15.1.
(Phases 13.3 and 14.1 minted none — 13.3 closed review residuals against existing
requirements, and 14.1 was superseded by 16 before planning.)

Phase 16 mints its own (DOCS-07..NN) at planning and is not yet counted above.
Phases 15 and 16 were inserted 2026-08-03. They extend v0.2 rather than opening a new milestone:
Phase 15 fixes the surface the v0.2 documentation describes, and Phase 16 rewrites that
documentation against it, so the milestone's "adopter-grade documentation suite" goal is not
actually met until both land. v0.3 (Assembly Modes) is unchanged and still follows.
