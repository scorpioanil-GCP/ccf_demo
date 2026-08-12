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
- [x] ~~**Phase 14.1: Documentation — The Deterministic Path & The Adoption Argument** (INSERTED)~~ — **SUPERSEDED by Phase 16**, 2026-08-03, before any plan was written. Every success criterion is absorbed there. *(Checkbox marked resolved 2026-08-07 — not because the phase was executed, but because an unchecked box made `roadmap.analyze` return `next_phase: "14.1"`, routing auto-advance into a phase that was deliberately never planned. The strikethrough and this note are the record of what actually happened; the progress table below reads "Superseded by 16".)*
- [x] **Phase 15: SDK Ergonomics — The Integration Surface** (INSERTED) - Loaders, artifact classes, factories, and wiring helpers so the day-1 integration is a fraction of today's ~450-line example; abstraction line held at marshalling-and-wiring so no governance decision leaves adopter code and no replay dimension is hidden (completed 2026-08-05)
- [x] **Phase 15.1: Ergonomics Gap Closure — Governance Enforced, Not Conventional** (INSERTED) - Closes the two HIGH defects found by post-gate cross-AI review (D-GATE-15 amendment, 2026-08-05): CR-1, author-versioned classes can bypass the D-05 bump check through the manifest, closed by a per-entry `registration: typed | versioned` mode that `load_and_boot` dispatches on and **refuses** when an author-versioned class asks for `typed`; CR-2, Gate 2 (INV-CH7-47) is self-satisfying in all nine examples because lineage and `engine_resolved` are filled from the same `execution.operators_invoked` — and the remedy the review prescribed is itself circular, since `execution.operators_invoked ≡ frozenset(declared.required_operator_keys)` through five pure transforms. Closed instead by **design E2** (D-IMPL-86, Dave, 2026-08-05): the projection's required operator set becomes its own Control Plane artifact, a binder refuses when it diverges from the product-class declaration, and Gate 2 is documented for what it actually verifies — assembly-path integrity. Also corrects `SURFACE-AUDIT.md` §4.1, whose "eight instances" is an undercount, and restates the new AST gates as tripwires rather than structural enforcement (URGENT — Phase 16 must not document a self-satisfying gate) (completed 2026-08-06)
- [x] **Phase 15.2: Substrate Adapters and Query Pushdown** (INSERTED) - The fabric asks a substrate a question instead of loading its graph. `GraphReader.as_of()` today returns every entity and relationship for a tenant per read, which does not scale to a financial-services graph and lets a graph-native engine conform without ever being used as one. Introduces the read seam operators express intent against and the adapters that answer it — SQL, Cypher, Gremlin, aggregation pipelines, or client-side scan, each inside its own adapter. **Tier 1** storage adapters and **tier 2** Context-Product-as-a-source (in-process, MCP, or A2A — the §6.6 recursive-enrichment case, whose admission governance already exists in `ccf.peering.admission`) are in scope; **tier 3** raw external sources are deferred but must not require a refactor to add (Dave, 2026-08-07). Must preserve operator purity, as-of correctness (INV-CH7-14), single-writer (INV-CH7-10), and cross-substrate replay determinism (completed 2026-08-08)
- [x] **Phase 15.3: Fluree Adapter (Tier-1 Substrate)** (INSERTED) - A Fluree v4 storage adapter behind the Phase 15.2 read/write seams — the substrate-consolidation option for deployments (notably a financial institution developing its KG on Fluree) that want CCF's Context Graph co-located on Fluree they already operate. openCypher-over-wire translation per the 15.2-12 template; httpx wire client, zero new packages; temporal fields encoded as properties (Fluree's native time travel is transaction-time and MUST NOT implement as-of, per D-IMPL-88); an adapter going green against the unchanged 15.2 conformance/differential suites is the 15.2 no-refactor claim demonstrated on a real substrate. Ruled by D-IMPL-88 (Dave, 2026-08-07); CCF stays substrate-neutral — the bank's KG itself is approached as an external *source* (MCP ingress now; tier 3 later), never CCF's foundation (completed 2026-08-09)
- [x] **Phase 15.4: Backend Registration Seam — The Substrate Stops Naming Its Adapters** (INSERTED) - Commissioned by D-IMPL-93 (Dave, 2026-08-09). Today the dependency arrow points the wrong way: `src/ccf/boot.py` and `src/ccf/graph/_writer.py` **import** `ccf.graph.backends.*`, `_open_backend`/`_preflight_backend` carry two-to-three keyword arguments per substrate, and `controlplane/artifacts.py` hand-maintains a `Literal` naming all six — so adding an adapter costs ~96 added lines across three core files, and both remaining D-IMPL-92 budgets are now exhausted (`manifest.py` 24/25, `artifacts.py` 9/10, tied). Invert it: each backend declares itself (name → factory + required connection config + preflight rule), the core holds a registry and looks up instead of branching, per-substrate kwargs collapse into one config mapping, and the `Literal` derives from the registry. Success is **structural, not numeric** — no import of `ccf.graph.backends.*` from outside `backends/`, and no substrate name in core outside the registry, both lint-enforced in the same machinery as the existing harness-import lint, replacing the line budgets D-IMPL-92 itself calls an admitted proxy. Per-adapter substrate cost goes to zero, which is what "the SDK needs no refactor to accept a new substrate" was always trying to say. Migrates all six existing backends; D-IMPL-92's gate is superseded by the structural check, not deleted (completed 2026-08-09)
- [x] **Phase 15.5: The Context Product Surface — Vessel, Assembler, Debt, Entitlement** (INSERTED) - Commissioned by Dave 2026-08-10, mid-Phase-16, on reading `examples/s1-01-hello-context-product`: *"today I would put an MCP server in front of the fluree database and run a query and return the results. What is the benefit of using CCF?"* The example precomputed one answer to one design-time question at one fixed instant — which Chapter 1 names as the thing CCF replaces, *"the difference between the verb aggregate and the verb assemble."* Measured behind that reaction: three of §6.3's eight committed contract elements (freshness SLA, discovery, addressability) are unimplemented while `contract.py` states they live on `RegisteredProductClass`, where only `assembly_mode` of the four actually is; `register_product_class` takes no payload schema so `payload` is an unchecked dict; `DebtAssessment` is computed by `ccf.halflife.debt`, exercised in five examples, and appears on neither the product nor the replay record; and `Perspective` is passed into `execute()` by the caller with nothing deriving it from the verified grant, so the whole content-shaping layer sits downstream of an unverified claim. Rulings in force: `D-IMPL-96` revokes the "no fabric changed" constraint that concealed this, `D-IMPL-97` rules the Context Product a single standardised vessel whose uniqueness is in how it was assembled and whose assembler is a Protocol implemented by a declared agent, and Dave ruled entitlement requires a fabric change. Phase 16 is parked at 6/21 and resumes against the corrected surface — documenting it first would have documented the defect (completed 2026-08-12)
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
  5. Gate 2 is documented for what it verifies — **assembly-path integrity**, the claim transcribed into the Contract equalling the engine's execution of the plan — and every site asserting that it compares two independently authored sets is corrected, including `src/ccf/products/gates.py:14-17` and `:244-250`, the `ProductClassDeclaration` docstring at `src/ccf/controlplane/artifacts.py::ProductClassDeclaration`, and `docs/SURFACE-AUDIT.md` §3.1 item 1. D-IMPL-57's intra-fabric "the engine's resolution is an independent witness" premise is corrected with it: the engine is a faithful transcriber of the plan, which holds under every design considered
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
- [x] 15.1-10-PLAN.md — phase close: surface regeneration, criterion evidence, `/gsd-review` + triage, present to Dave (checkpoint)

**Waves**: 1 → 01; 2 → 02; 3 → 03; 4 → 04; 5 → 05, 06, 07 (parallel); 6 → 08, 09 (parallel); 7 → 10 (checkpoint)

### Phase 15.2: Substrate Adapters and Query Pushdown (INSERTED)

**Status**: inserted 2026-08-07 from a design conversation with Dave; not yet
discussed or planned. The goal and constraints below are Dave's, recorded at
insertion; success criteria and requirement IDs are `/gsd:discuss-phase 15.2`'s
to write.

**Goal**: The fabric asks a substrate a *question* instead of loading its graph.
Today `GraphReader.as_of()` returns a fully materialized `GraphView` — every
entity and relationship for a tenant, per read — so a substrate can conform but
can never answer. That does not scale to a financial-services graph, and it
forecloses graph-native engines: a Neo4j or Neptune adapter would translate
"give me everything" rather than push traversal into an engine built for it.
This phase introduces the read seam operators express intent against, and
adapters that answer it — SQL in the Postgres adapter, Cypher in Neo4j, Gremlin
in Neptune, aggregation pipelines in Mongo, client-side scan where there is no
query engine at all.

**Depends on**: Phase 15.1 (the binder and registration seams it must not disturb)
**Blocks**: Phase 16 — do not document a read surface this phase will reshape

**Scope: two tiers now, a third designed for.**

- **Tier 1 — storage adapters.** Substrates answering queries over graph state.
  No lineage of their own; L2 supplies it, as today.
- **Tier 2 — a Context Product as a source.** In-process, over MCP, or over A2A,
  from this fabric or another — the recursive enrichment §6.6 names and the
  composition `ContextAssemblyAgent` exists for. The governance already exists in
  `src/ccf/peering/admission.py` (`union_lineage`, `SignatureRefusal`,
  `ContractRefusal`, `PolicyBindingRefusal`, `LineageContinuityRefusal`,
  `AdmissionBypassError`). What is missing is that admission is an *ingress path
  to L3*; nothing lets an operator treat an upstream product as a queryable
  source at read time.
- **Tier 3 — raw external sources** (REST, lake, vector store) are **out of scope
  for this phase and will be added later.** The design must accommodate them
  without a major refactor (Dave, 2026-08-07).

**Design constraints — the tier-3 no-refactor commitment, made testable:**

  1. **Provenance is an explicit per-adapter obligation in the interface, never an
     assumption.** Tier 1 carries none, tier 2 arrives with it, tier 3 will have
     none. An interface that assumes any of the three breaks on the others. Each
     adapter declares what it can attest to; the fabric refuses what does not meet
     the product's requirements.
  2. **Admission is a seam every non-graph source passes through** — wired for
     tier 2 now, reusable by tier 3 — not a tier-2-shaped special case that tier 3
     must route around.
  3. **Canonical ordering and serialization belong to the interface, not the
     adapters**, so replay determinism is inherited rather than re-implemented,
     and two conformant substrates cannot produce two different Context Products
     from the same data.

**Invariants this phase must preserve** (they are why the materialized view exists
and why this is a design phase rather than a Protocol addition):

  - **Operator purity.** An operator is a pure function over graph state
    (whitepaper §7.4). A lazy result that can change under it is not a value it can
    be pure over — whatever the seam returns must be a frozen, deterministic value.
  - **As-of correctness (INV-CH7-14).** Every adapter must answer "the state you
    held at T": claims observed later absent, claims superseded later still
    current. Not every substrate does temporal natively; those adapters must
    implement it.
  - **Single-writer (INV-CH7-10)** and **policy binding at assembly time
    (INV-CH7-03)** hold unchanged. No adapter acquires a write handle.
  - **Replay portability.** The same question against the same data yields the same
    bytes on any conformant substrate.

**Open questions for discuss-phase:** which substrate(s) beyond Postgres/SQLite
prove the seam (Neo4j as the strongest pushdown test; a KV store as the adversarial
floor; Mongo has an in-house triangulation point per CLAUDE.md §2.1); whether a
substrate conformance suite is a deliverable; and whether existing operators change
shape or only what they are handed.

**Requirements**: SUBQ-01..SUBQ-11 — minted at planning, 2026-08-07 (REQUIREMENTS.md
rows land in plan 15.2-01); not counted in Coverage below.

**Plans**: 14 plans in 9 waves *(redrawn 2026-08-07 against the D-IMPL-87 resolution — the prior 13-plan set is void and archived in `void-plans-pre-D-IMPL-87/`; multi-segment pushdown with `allowed_entities` under the uniform rule, CP-valued survivor cap, hash+ArtifactStore replay pin, prose-lane versioning)*

Plans:
**Wave 1**

- [x] 15.2-01-PLAN.md — Query-semantics prose v1 (`GQ-NN` clauses incl. uniform rule, induced subgraph, size cap, fixed point; semver lane per D-12) + SUBQ-01..11 requirement minting (amended texts)
- [x] 15.2-02-PLAN.md — Substrate-neutral write seam: typed `_GraphTxn` operations in `ccf.graph._writer` (entailed by D-05/D-06 + INV-CH7-10)
- [x] 15.2-03-PLAN.md — Substrate-neutral read materialization core extracted from `BaseGraphReader` (rows → records → canonical order → freeze; the read-side twin of 15.2-02)

**Wave 2** *(blocked on Wave 1)*

- [x] 15.2-04-PLAN.md — `GraphQuery` (with `allowed_entities`)/`TraversalSpec`/`QueryFragment`/`SourceAttestation` frozen contracts + hash-pin tests incl. allowed_entities distinctness

**Wave 3** *(blocked on Wave 2)*

- [x] 15.2-05-PLAN.md — `ccf.graph.fallback` (incl. allowed_entities set-intersection) + `GraphReader.query()`/`attestation` widened atomically everywhere + `as_of()` derivation (D-07) + property suite on the fallback incl. resurrection closure

**Wave 4** *(blocked on Wave 3)*

- [x] 15.2-06-PLAN.md — Memory backend (KV floor) + boot/manifest wiring + differential suite + query corpus incl. allowed_entities/resurrection strategies
- [x] 15.2-07-PLAN.md — `read_intent()` + engine-owned multi-segment segmentation (uniform rule, survivors → seeds + allowed_entities) + D-10 cap mechanism + per-plan equivalence with Gate 2 pinned + pushability matrix

**Wave 5** *(blocked on Wave 4)*

- [x] 15.2-08-PLAN.md — Replay pins per D-11: dim-5 hash tuple + query bytes in the ArtifactStore (`ccf.graph-query`) + D-10 cap value on the deployment manifest with dim-2 pin + replay recompute-and-compare
- [x] 15.2-09-PLAN.md — SQLite/Postgres native pushdown (recursive CTE, hop admissibility + allowed_entities membership in the recursive term)
- [x] 15.2-10-PLAN.md — `ProductSource`: tier-2 Context-Product-as-source over the admission gate

**Wave 6** *(blocked on Wave 5)*

- [x] 15.2-11-PLAN.md — Attestation accepted modes on product classes + pre-execute refusal + gate-path enforcement + dim-1 replay pin + combined three-field record-compatibility matrix

**Wave 7** *(blocked on Wave 6)*

- [x] 15.2-12-PLAN.md — Neo4j adapter (Cypher pushdown incl. parameterized allowed_entities) + `neo4j` extra + container-gated CI leg

**Wave 8** *(blocked on Wave 7)*

- [x] 15.2-13-PLAN.md — Mongo adapter ($match + $in first, staged $graphLookup) + `mongo` extra + container-gated CI leg

**Wave 9** *(blocked on Wave 8 — checkpoint)*

- [x] 15.2-14-PLAN.md — Phase close: single surface regeneration, full gates + three container legs, one perf run, §3.1 review, present to Dave with D-IMPL-87 re-ratification evidence

### Phase 15.3: Fluree Adapter (Tier-1 Substrate) (INSERTED)

**Status**: inserted 2026-08-07 by D-IMPL-88 (Dave); **discussed 2026-08-08**
(12 locked decisions D-01..D-12, ratifying D-IMPL-88 precondition (b)) and
**planned 2026-08-08** (five plans, five waves). The goal and the constraints
below are Dave's ruling plus the feasibility research
(`.planning/research/FLUREE-ADAPTER.md`), recorded at insertion; the success
criteria and requirement IDs below were written at planning against
`15.3-CONTEXT.md`, `15.3-RESEARCH.md` and `D-IMPL-92`.

**Goal**: CCF's Context Graph runs on Fluree v4 through the Phase 15.2 seams —
a tier-1 storage adapter answering `GraphQuery` with pushed openCypher and
satisfying the `_GraphTxn` write seam with batched HTTP commits — with zero
changes to the SDK core, the query vocabulary, or the conformance suites. A
post-gate adapter going green against the unchanged 15.2 suites (suite diff:
one fixture parameter) is the 15.2 no-refactor claim demonstrated on a real
substrate.

**Depends on**: Phase 15.2 (the read/write seams, the differential + property
suites and corpus, the container-leg and extras/boot/manifest precedents, and
the 15.2-02 remote-batched-substrate hedge D-IMPL-88 applied)

**Posture (D-IMPL-88):** CCF stays substrate-neutral. Fluree is an adapter
(this phase) and a source (MCP ingress today; tier 3 when it lands) — never a
foundation. The bank's KG is a system of record CCF assembles *from*, not
CCF's graph.

**Constraints recorded at insertion (research-derived; discuss-phase ratifies):**

- **Target the v4 line** (BSL 1.1 → Apache 2.0; Additional Use Grant clean for
  CI containers and wire-only adapters). **Precondition:** confirm the
  institution runs v4, not legacy v2-AGPL — a v2 shop changes the deliverable
  entirely (D-IMPL-88 precondition (a)).
- **Translation template is 15.2-12 (Neo4j):** v4 speaks openCypher — bounded
  var-length paths, hop predicates, `UNWIND`/param for `allowed_entities`.
  SPARQL cannot express bounded depth; Cypher is the traversal target.
- **Temporal fields are properties, filtered like SQL/Neo4j/Mongo.** Fluree's
  native time travel (`t`) is transaction time and MUST NOT implement as-of
  (INV-CH7-14 filters on observed/superseded claim data; divergent on late
  arrivals and supersession — non-conformant against the differential corpus
  by construction).
- **No new Python dependency:** httpx wire client (already a core pin).
  `fluree-py` is not on PyPI (unregistered, squattable — supply-chain hazard;
  do not install); `aioflureedb` targets the dead v2 API.
- **Write posture:** buffered batch recommended — `_FlureeTxn` accumulates
  typed operations, commits as one atomic `POST /update`; per-op rowcounts by
  read-before-buffer, sound under INV-CH7-10 single-writer. Bolt explicit
  transactions rejected (Raft/peer deployments refuse BEGIN); per-op
  autocommit rejected (abandons atomicity). Discuss-phase ratifies
  (D-IMPL-88 precondition (b)).
- **Known pitfalls carried from research:** JSON-LD datatype coercion (fixed
  minimal `@context`, no ledger default context); read-after-write (thread
  last commit `t` via `Fluree-Min-T`); one CCF-owned ledger with `tenant_id`
  as predicate (SQL multi-tenant posture); exact image pin (breaking changes
  have shipped inside a minor); container-gated CI leg per the 15.2 pattern.

**Effort shape (revised at planning, 2026-08-08).** The insertion-time estimate
(one plan-pair, two to three tasks, one wave) was revised **upward on the
stage-2 side** by the phase research and held on the read side. Packaging is
near zero (httpx is a core pin; one pytest marker; no extra, no mypy override,
no lazy import). The store envelope is comparable to Neo4j's. `_FlureeTxn` is
~1.5–2× `_Neo4jTxn`. **Stage-1 read translation is NOT nearly verbatim** — the
policy family cannot use dynamic property access and the 1 MB query-body cap
needs a byte-budget decline. **Stage 2 is the hardest single piece in the
phase**: three Fluree-specific structural breaks require an adapter-internal
physical-model change (edge-as-node interposition), and the openCypher
front-end is six weeks old at the pin. Five plans, five waves, strictly
sequential.

**Success Criteria** (what must be TRUE):

  1. The four probes that fail *silently* — F-A1 container round trip, F-A4
     ground-batch semantics, F-A5 zero datatype coercion, F-A6 dynamic property
     access — run against the pinned `fluree/server:4.1.4` **before any code
     depends on them**, and the two that fail *loudly* (F-A2, F-A3) run before
     any stage-2 promotion code
  2. A fabric boots against Fluree v4 with no extra installed, writes through L2
     as one buffered ground JSON-LD POST, and reports **12 passed** on the
     unchanged `tests/conformance/test_graphstore.py` under `-m fluree`
  3. The `fluree` param answers the **unchanged** differential corpus
     byte-identically against the audited fallback oracle, and the push is
     proven by discriminating `translated_answers`/`fallback_answers` telemetry
     that has been watched to fail — not by byte-identity a degrade would also
     satisfy
  4. Stage 2 either promotes at byte-identity over the full corpus with the
     depth 0/1/2/3 doubling asserted first, **or** ships stage 1 with a
     maintained `DI-15.3-NN` entry — both satisfy SUBQ-12 under its stage hedge
  5. `make gate-15.3` implements `D-IMPL-92` as corrected, has been watched to
     exit non-zero on three distinct violations, and the gate package is
     committed with the phase — including its own stated limits
  6. The `fluree` leg is a fourth **always-on, blocking** service leg in
     `ci.yml` pinned to `4.1.4` exactly, with a scheduled `live-legs.yml` drift
     job against the floating `4.1`, and `docs/GRAPH_QUERY_SEMANTICS.md`,
     `perf/baselines/` and `perf/thresholds.toml` byte-untouched across the
     whole phase

**Requirements**: SUBQ-12, SUBQ-13, SUBQ-14

**Plans:** 6/5 plans complete

Plans:

**Wave 1**

- [x] 15.3-01-PLAN.md — Probes F-A1/F-A4/F-A5/F-A6 before any dependent code, the `fluree` marker/fixture/`leg-fluree` plumbing, and the F-A4(a) ruling gate (checkpoint)

**Wave 2** *(blocked on Wave 1)*

- [x] 15.3-02-PLAN.md — `FlureeGraphStore` envelope, `_FlureeTxn`/`FlureeGraphWriter` buffered-batch write path, Tier-B registration, and the six write semantics green

**Wave 3** *(blocked on Wave 2)*

- [x] 15.3-03-PLAN.md — Stage-1 non-traverse pushdown, the differential param, the fourth always-on CI leg, and the falsification-tested pushdown telemetry

**Wave 4** *(blocked on Wave 3)*

- [x] 15.3-04-PLAN.md — F-A2/F-A3, the interposed bounded undirected walk with depth 0/1/2/3 asserted, and promotion at byte-identity or a recorded stage-1 degrade

**Wave 5** *(blocked on Wave 4)*

- [x] 15.3-05-PLAN.md — `make gate-15.3` implementing D-IMPL-92 (checkpoint), the scheduled drift detector, and the committed gate package

### Phase 15.4: Backend Registration Seam — The Substrate Stops Naming Its Adapters (INSERTED)

**Status**: commissioned 2026-08-09 by `D-IMPL-93` (Dave). The goal and
constraints below are Dave's, recorded at commissioning; success criteria and
requirement IDs are `/gsd:discuss-phase 15.4`'s to write. This section was
added 2026-08-09 to repair a malformed insertion — the summary-list entry was
written without its detail section, which left every GSD handler unable to
resolve the phase.

**Goal**: The dependency arrow between the core and its graph adapters points
the wrong way, and adding a substrate costs roughly 96 lines across three core
files. `src/ccf/boot.py` and `src/ccf/graph/_writer.py` import
`ccf.graph.backends.*`; `_open_backend` and `_preflight_backend` carry two to
three keyword arguments per substrate; `controlplane/artifacts.py` hand-maintains
a `Literal` naming all six. Invert it. Each backend declares itself — name,
factory, the connection configuration it requires, its preflight rule — the core
holds a registry and looks up instead of branching, the per-substrate keyword
arguments collapse into one configuration mapping, and the `Literal` is replaced
by a registry check. Per-adapter cost goes to zero, which is what "the SDK needs
no refactor to accept a new substrate" was always trying to say.

**Success is structural, not numeric.** Two properties, both enforced by lint in
the same machinery as the existing harness-import lint (`tools/lints/`): no
import of `ccf.graph.backends.*` from outside `backends/`, and no substrate name
in core outside the registry. These replace `D-IMPL-92`'s per-file added-line
budgets, which `D-IMPL-92` itself calls an admitted proxy and which are now
exhausted — `manifest.py` at 24 of 25 and `artifacts.py` at 9 of 10, tied, so a
seventh substrate breaches both on arrival. `D-IMPL-92`'s gate is **superseded
by the structural check, not deleted**.

**Depends on**: Phase 15.3 (the sixth backend, whose landing exhausted the
budgets), Phase 15.2 (the read and write seams the registry must not disturb)
**Blocks**: Phase 16 — do not document a backend surface this phase reshapes

**Scope**: all six existing backends migrate — sqlite, postgres, memory, neo4j,
mongo, fluree. Nothing about operator purity, as-of correctness (`INV-CH7-14`),
single-writer (`INV-CH7-10`), or cross-substrate replay determinism may weaken.
`D-11`'s line on mechanism change elsewhere under `src/ccf`, the
`docs/GRAPH_QUERY_SEMANTICS.md` freeze, and the corpus rule all stand.
`D-IMPL-92`'s prohibition on raising a budget to make a gate pass stands: under
`D-IMPL-93` the remedy for an exhausted budget is the registry, never a larger
number.

**Requirements**: none mapped. The phase is measured against the sixteen
decisions plus two corrections in `15.4-CONTEXT.md` (`D-01`..`D-16`, `C-01`,
`C-02`) and the twenty validation claims `V1`..`V20` in `15.4-RESEARCH.md`.

**Success Criteria** (what must be TRUE):

  1. No module under `src/` or `runtime/` outside `ccf.graph.backends` imports
     `ccf.graph.backends.*`, enforced by the `cinv02-backend-import` rule in
     `make lint`
  2. No substrate name appears in `src/ccf` outside the adapters' own package —
     in code or in docstring prose — enforced by the `cinv04-substrate-name` and
     `cinv04-substrate-prose` rules, whose vocabulary is read off disk rather
     than typed into the checker
  3. All six adapters migrate behind the registry; `boot()` and
     `load_and_boot()` take an adapter name and one connection mapping, with the
     `D-15B` migration note written
  4. An adapter installed from outside this repository passes the same
     conformance suites the six built-in adapters pass, and
     `git diff --stat src/ccf` over its arrival is empty
  5. Single-writer, as-of correctness, operator purity and cross-substrate
     replay determinism are unweakened: four container legs green,
     `tests/conformance/query_corpus.py` and `docs/GRAPH_QUERY_SEMANTICS.md`
     byte-untouched for the whole phase

**Plans:** 12/12 plans complete, plus a post-review fix pass (13 SUMMARYs)

Plans:

**Wave 1**

- [x] 15.4-01-PLAN.md — The two structural lint rules and the widened single-writer rule, with negative controls

**Wave 2** *(blocked on Wave 1)*

- [x] 15.4-02-PLAN.md — The registry: registration record, entry-point and in-package discovery, the three refusals
- [x] 15.4-03-PLAN.md — Split `_writer.py` into six per-backend write modules (+ WR-01)

**Wave 3** *(blocked on Wave 2)*

- [x] 15.4-04-PLAN.md — Per-adapter config models and registration records (+ WR-05)

**Wave 4** *(blocked on Wave 3)*

- [x] 15.4-05-PLAN.md — `boot()` becomes a registry lookup; 23 call sites migrate; the handle carries its adapter pin

**Wave 5** *(blocked on Wave 4)*

- [x] 15.4-06-PLAN.md — Manifest and artifacts: registry preflight, secret references, `Literal` dropped, schema regenerated, 20 call sites

**Wave 6** *(blocked on Wave 5)*

- [x] 15.4-07-PLAN.md — Turn the structural lints on; retire the D-IMPL-92 line-budget gate
- [x] 15.4-08-PLAN.md — Decision Replay dimension 2 pins the adapter
- [x] 15.4-09-PLAN.md — `ccf backends list` over `GET /backends`

**Wave 7** *(blocked on Wave 6)*

- [x] 15.4-10-PLAN.md — The out-of-tree proof adapter distribution and its install wiring

**Wave 8** *(blocked on Wave 7)*

- [x] 15.4-11-PLAN.md — Conformance params, param/registry parity, the zero-cost measurement, the authoring guide

**Wave 9** *(blocked on Wave 8)*

- [x] 15.4-12-PLAN.md — Surface record, citations, full sweep, gate package (**checkpoint**)

### Phase 15.5: The Context Product Surface — Vessel, Assembler, Debt, Entitlement

**Status**: planned 2026-08-10, commissioned mid-Phase-16. Phase 16 is parked at
6/21 and resumes against the surface this phase corrects.

**Why it exists.** Dave read `examples/s1-01-hello-context-product` and asked the
question the whole SDK has to answer: *"today I would put an MCP server in front
of the fluree database and run a query and return the results. What is the
benefit of using CCF?"* The example pinned its subject, its temporal boundary and
its `now` as literals in artifacts — one company, one frozen instant, one answer.
Chapter 1 already names that as the thing CCF replaces: *"assembled at decision
time, not precomputed against design-time queries… the difference between the two
is the difference between the verb aggregate and the verb assemble."* By the
whitepaper's own vocabulary the reference example aggregates.

**What was measured behind that reaction** (at `b771468`, field by field, not
inferred):

- Three of §6.3's eight committed elements — **freshness SLA, discovery,
  addressability** — are unimplemented, while `contract.py` states all four
  class-level elements *"live"* on `RegisteredProductClass`, where only
  `assembly_mode` of the four actually is.
- `register_product_class` accepts **no payload schema**, so `payload:
  Mapping[str, Any]` is an unchecked dict — the substantive gap under the vessel
  model, whose entire discipline is the declared schema.
- `DebtAssessment` is computed by `ccf.halflife.debt`, exercised in five shipped
  examples, and appears on **neither** `ContextProductContract` **nor**
  `DecisionReplayRecord`. Five of the six axes reach the wire; the sixth — the one
  saying how much to trust the other five — does not.
- `Perspective` is passed **into** `execute()` by the caller and nothing derives
  it from the verified grant, so Π conditioning and the policy operators both key
  off an unverified claim. `build_egress_server` binds no authorizer at all.
- The `context_assembly` archetype ships but `ArchetypeComponent` is declarative
  — `archetype_id`, `fabric_interaction_pattern`, `replay_obligations`,
  `configuration_defaults` — so it declares the emission *pattern* and carries no
  assembly behaviour. The assembler is a new surface, not a fill-in-the-blank.

**Rulings in force.** `D-IMPL-96` revokes the "no fabric changed" constraint that
concealed all of this — it was an anti-leakage rule that became a no-change rule,
policed by a `git diff --stat` that cannot tell an adapter leaking in from a
defect being fixed. `D-IMPL-97` rules the Context Product **one standardised
vessel**, not a class hierarchy: identity is `schema_name` plus a declared payload
schema, uniqueness is in **how it was assembled**, and the assembler is a Protocol
whose implementation is a **declared agent** from the `context_assembly`
archetype. Dave ruled separately that entitlement requires a fabric change.

**The design agenda, carried from `docs/CONTEXT_PRODUCT_REVISION.md` §9–§10.**
Seven open questions reach planning unresolved, and one gates the others: whether
the **request surface is a typed request contract per class** — Dave's *"company
name and top investors above 25%"* — because that is what makes a product
**callable** rather than configurable, and it collapses the fixed-subject and
fixed-instant defects into one design instead of two patches. The rest: debt's
shape on the wire and whether recency and salience are one field or two; whether
debt lands on the product, the replay record, or both; what *"a material event
transpired"* means mechanically without domain values in the core; whether payload
validation is a fourth gate or a registration-time bind; debt composition
weighting for aggregate products; and the unruled coupling — **if entitlement
bounds what an assembler may consult on a caller's behalf, completeness and
therefore debt differ per principal, so debt cannot be computed once per
product.**

**Success Criteria**

  1. Every Context Product delivered to a consumer carries its Context Debt, and no delivery path exists that drops it
  2. All **nine** elements of the §6.3 contract are present in code, each verified by an executable assertion rather than by prose, so the class of defect that hid three of them cannot recur silently (`D-IMPL-30`, Dave, 2026-07-25, resolved reading (a): the contract has nine elements including Assembly Mode, and every "eight" reference — CLAUDE.md §5's included — is editorial drift the ruling explicitly authorizes treating as such; six are present today, freshness SLA / discovery / addressability are the three absent)
  3. `register_product_class` accepts a declared payload schema and a payload violating it is refused, reusing the JSON-Schema machinery already proven on eight artifact classes
  4. Perspective is derived from the verified identity at every exposed door and a caller cannot assert a role it was not granted, while `execute()` keeps taking a Perspective so replay determinism is untouched
  5. Per-product-class entitlement gates the egress door, reusing the shape `peering/trust_policy.py` already implements per peer
  6. The assembler exists as a Protocol whose implementation is a declared agent from the `context_assembly` archetype, binding sources, tools, enlisted agents and its debt profile through axes 4 and 5 and channel 2
  7. A product answers a runtime request — subject and instant are arguments, never artifact literals — and the question asked is pinned in replay through `graph_query_sequence` and `QueryPinWriter`
  8. Aggregate products compose lineage by union and implement `D-IMPL-31`'s already-resolved mixing-refusal rule — `expires_at = min(class MAX_TTL ceiling, derivation over constituent signal validities)`, with declarable constituent-validity floors whose breach **refuses assembly** rather than emitting a product labelled fresher than its stalest load-bearing constituent (ruled by Dave 2026-07-25 and never implemented; this criterion is implementation of a standing ruling, not a new design decision)
  9. The four anti-leakage lints stay green throughout: zero harness imports in `src/`, no LLM client in an `@algorithmic` module, no prompt or threshold literal outside an artifact, no substrate name outside the backend registry
  10. `examples/s1-01-hello-context-product` demonstrates an agent asking about any company at any time and is the shape every later example copies

**Plans:** 15/15 complete. 15 plans in 7 waves (15.5-15 added at wave 3 by D-IMPL-108). Requirements `CPS-01`..`CPS-14` were minted by plan
15.5-05 at execution (commit `e18f4bf`) and are now present in `.planning/REQUIREMENTS.md`. Three plans
carry blocking checkpoints: 15.5-05 (the eight-question ruling package), 15.5-13
(Dave calls the product for two companies at two instants) and 15.5-14 (the gate).

**Wave 1** *(no dependencies — none of these needs a ruling)*

- [x] 15.5-01-PLAN.md — Ruling evidence: measure what the eight questions cost
- [x] 15.5-02-PLAN.md — The nine-element executable enumeration (the anti-recurrence artifact)
- [x] 15.5-03-PLAN.md — Product-entitlement artifact, in the `PeerTrustGrant` shape
- [x] 15.5-04-PLAN.md — Delete `DeploymentBinding` from `s1-01`

**Wave 2** *(05 blocked on 01; 06 blocked on 03)*

- [x] 15.5-05-PLAN.md — The ruling package + CPS requirement minting (**checkpoint**)
- [x] 15.5-06-PLAN.md — Authenticate, bind entitlement and resolve Perspective at all three exposed doors (MCP egress, HTTP product route, Experience front door)

**Wave 3** *(blocked on the rulings)*

- [x] 15.5-07-PLAN.md — The three absent contract elements + the declared payload schema

**Wave 4** *(blocked on Wave 3)*

- [x] 15.5-08-PLAN.md — The typed request contract (addressability realized)

**Wave 5** *(blocked on Waves 3-4)*

- [x] 15.5-09-PLAN.md — Payload validation enforcement
- [x] 15.5-10-PLAN.md — The assembler Protocol + reference implementation
- [x] 15.5-11-PLAN.md — Context Debt reaches the consumer
- [x] 15.5-12-PLAN.md — Aggregate composition: lineage union, TTL floor, `D-IMPL-31` refusal

**Wave 6** *(blocked on Wave 5)*

- [x] 15.5-13-PLAN.md — `s1-01` answers about any company at any time (**checkpoint**)

**Wave 7** *(blocked on Wave 6)*

- [x] 15.5-15-PLAN.md — Widen the product resolver seam once, carrying the typed request and the authorized Perspective (closes DI-15.5-03)
- [x] 15.5-14-PLAN.md — Phase close: full sweep, surface manifest, review, gate package (**checkpoint**)

**Blocks**: Phase 16 — the documentation rewrite resumes against this surface, not the one it found

### Phase 15.6: Decision-Completeness and Defect Closure

**Why this phase exists.** `D-GATE-15.5` approved Phase 15.5 with debt
*"informative and correctly attributed, and not yet decision-complete"*
(`D-IMPL-112`, Dave's verdict at the `15.5-13` checkpoint). Phase 16's job is
writing examples and the adoption argument — and an example demonstrating debt
an analyst cannot act on teaches the wrong lesson. Dave ruled 2026-08-11 that
15.6 runs **before** Phase 16 resumes.

**The measured reason it goes first, and it is not the defects.** The five
carried defects are API-neutral and could wait. The decision-completeness work
is where every API change lives: `Observation` is public surface and gains an
identity field; `DebtAssessment` gains evidence pointers; and because
`debt: DebtAssessment | None` is a field on `ContextProductContract`
(`src/ccf/products/contract.py::ContextProductContract`), **the product content
address moves a third time**. Phase 16 writes examples, and examples encode
expected outputs — moving the address after ten examples exist regenerates ten;
moving it now regenerates **one**. Phase 16 has already been invalidated once by
exactly this: 6 of 21 plans landed before 15.5 moved the surface, and 4 of the
remainder name the product or door surface directly.

**Two explicit tracks** (Dave, 2026-08-11). They differ in risk and must not be
planned as one.

**Track A — defect closure. API-neutral, bounded, mostly mechanical.**
- `DI-15.5-01` — the `test_run_coroutine_sync_overhead` ±11% flake.
- `DI-15.5-04` — `IntermediateCache` computes a `content_hash` key for a cache
  that is unreachable by construction; ~0.20s of a 0.41s benchmark. Making it
  lazy is behaviour-identical but narrows a `D-IMPL-36` contract.
- `DI-15.5-05` — binder refusals with no calling code path. Rule it as
  `D-IMPL-113` ruled the analogous bind case, or wire it.
- `DI-15.5-06` — `tools/dump_surface.py` records a Protocol's `__init__`, never
  its `__call__`; 56 manifest entries carry the information-free
  `(*args, **kwargs)`, 30 of them `*Protocol`, against 54 Protocol classes. This
  is an **audit** fix, not a surface change — it makes the already-shipped 3-arg
  → 5-arg resolver break visible. `D-IMPL-110` carries the measured inventory.
- `DI-15.5-08` + `D-IMPL-114` — the `path::Symbol` citation sweep. Known
  population: this phase's 3 and `DI-15.4-02`'s 45; never measured tree-wide.

**Track B — decision-completeness. API-affecting; scoped to `D-IMPL-112`'s
three named gaps, NOT to the open question.**
1. **Which observations contributed the decay.** `Observation` carries
   `(observation_type, observed_at)` and no join key, which is exactly why
   `D-IMPL-99` ruled per-subject and per-claim NOT MEASURABLE. **A build, not a
   wiring task.** Dave ruled 2026-08-11: **research spike first, then plan** —
   the `15.5-01` shape, which deleted an option from the decision space for
   free. The spike measures what an `Observation` identity costs across its 10
   files and the manifest, what it does to the content address, and whether
   evidence pointers can ride the **record** rather than the product.
2. **When the underlying source filings were last refreshed** — source-refresh
   recency as a fact distinct from computed freshness. Nothing models it today.
3. **What `forced_llm` obliges** — a declared obligation vocabulary per debt
   signal. Mechanism ships; the vocabulary is user configuration, never `src/`
   values (CLAUDE.md §11).

**The standing test for this phase:** *"would someone act on this?"* rather than
*"is this correct?"* Phase 15.5 answered the second. Only the first makes the
examples honest.

**Verification is `make ci`, not `make ci-core`.** Two 15.5 executors reported
`docs-strict` unverified and both times it was the only thing broken. `make ci`
costs ~75s more. Also sweep `docs/schemas/` and `openapi.json` for whitepaper
shingles — they sit outside the D-20 scanner, and prose republished there fires
no gate.

### Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument

**Status**: discussed 2026-08-09. The scope was expanded at that discussion on
Dave's authority and this entry was rewritten to match (2026-08-09) — the
pre-discussion goal below is absorbed in full, nothing dropped. The authoritative
record is
`.planning/phases/16-documentation-rewrite-the-deterministic-path-the-adoption-ar/16-CONTEXT.md`
(decisions `D-01`..`D-12`); every line here is carried from it or from material
already recorded elsewhere in this roadmap. Requirement IDs (DOCS-07..NN) remain
`/gsd:plan-phase 16`'s to mint.

**Goal**: rebuild the adopter-facing **examples suite** and **published
documentation** against the post-Phase-15 surface, organized as four sections of
increasing depth. Phase 16 ships **Sections 1–3**, all against mechanism the SDK
demonstrably ships today; **Section 4 is Phase 17's**, arriving with the fabric
that enables it (`D-01`).

  - **Section 1 — "Hello CCF."** Deterministic assembly only, agent-free. A
    beginner's path through Context Products, Context Operators, and the six axes
    of `G(E, R, T, P, Π, L)`.
  - **Section 2 — External agents over MCP.** Client agents reach CCF with zero
    CCF dependency. Claude Agent SDK, Google ADK, and LangGraph legs.
  - **Section 3 — Advanced CCF.** Embedding CCF in your own application, and
    developing agentic skills within CCF against a real use case.
  - **Section 4 — LLM packaging and agent swarms.** *Phase 17.* Assembly Mode 2
    (`llm_packaged`) and Mode 3 (`swarm_assembled`).

The examples are **greenfield** — `examples/00`–`08` retire and the suite is
rebuilt against the Phase 15.4 registry seam as one parameterized runner proven
across all six backends. **KYC / UBO resolution and refresh** on the FIBO dataset
is the use-case spine, and the adoption argument gets its own page naming the
alternatives. The pre-discussion goal it replaces, carried verbatim from the
milestone entry above: *"one document, two sections (deterministic + external MCP
consumption; CCF-agent assembly + MCP/A2A consumption), banking scenarios from
the whitepaper, re-cut snippet markers so a reader can see which code is CCF and
which is theirs."*

**What it inherits, already on the record:**

- **Phase 14.1 whole** — superseded 2026-08-03 before any plan was written; every
  success criterion in that entry is absorbed here, plus the structure Dave
  specified in that discussion.
- **Phase 14's G-01 framing defect**, deferred deliberately: the shipped docs
  describe an integration surface Phase 15 replaced, so the fix lands here against
  the new surface rather than twice against the old one.
- **A hard constraint from Phase 15.1, recorded URGENT**: Phase 16 must not
  document a self-satisfying gate. Gate 2 (INV-CH7-47) is **assembly-path
  integrity** — the claim transcribed into the Contract equalling the engine's
  execution of the plan — not a comparison of two independently authored sets.
- **Eleven open residuals** carried at D-GATE-15.1 (re-approved 2026-08-06).
  `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md` is the
  authoritative inheritance list — **not** `docs/SURFACE-AUDIT.md` §6.4, which
  predates the last four remediation rounds.
- **Two process findings** from the 15.1 close: the code-review gate runs *after*
  the phase gate (which cost that phase a withdrawn approval), and `make ci` does
  not reach `tools/` though CI does — three suites there fail pre-existing.

**Requirements**: mints its own DOCS-07..NN at planning; not counted in Coverage
below. DEMO-01..03 and EXAM-01..05 re-home onto the new suite rather than being
retired (`D-08`).
**Plans:** 4/21 plans executed (16-02 at 2/3, paused at its DGX checkpoint)

Plans:
**Wave 1**

- [x] 16-01-PLAN.md — ruling package (`D-IMPL-94`), DOCS-07..18 minted, ERGO-03 measurement frozen

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 16-02-PLAN.md — FIBO source-estate extension: corp→corp ownership edges with per-edge percentages *(2/3 — Task 3 loads the four DGX stores and needs operator credentials; `roadmap.update-plan-progress` marked this `[x]` because it counts SUMMARY files, and 16-02's SUMMARY is `status: paused-at-checkpoint`)*
- [x] 16-03-PLAN.md — Section-2 client-leg transport spike: LangGraph + Claude Agent SDK
- [x] 16-04-PLAN.md — gate-checker unblock, three standing docs tripwires
- [x] 16-21-PLAN.md — repo-wide retirement-coupling sweep, its inventory and its gate (split from 16-04)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 16-05-PLAN.md — Section-1 example 1: spine/deployment split, KYC/UBO deterministic assembly
- [ ] 16-06-PLAN.md — advisory pages A-1/A-2/A-3/A-8 + discharge gate

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 16-07-PLAN.md — one driver, backend from a configuration artifact + six-backend equality matrix
- [ ] 16-08-PLAN.md — Section-1 example 2: freshness (λ_c) and Context Debt (D_c)
- [ ] 16-09-PLAN.md — Section-2 example: MCP fabric + four zero-CCF client legs
- [ ] 16-10-PLAN.md — Section-3 example A: embed CCF in a host application
- [ ] 16-11-PLAN.md — Section-3 example B: agentic skills, workflow, HITL, replay

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 16-12-PLAN.md — Makefile + CI wiring + DGX opt-in job + credential gate
- [ ] 16-20-PLAN.md — Section-2 zero-import AST guard, three-harness assertion, README (split from 16-09)

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 16-13-PLAN.md — Section-1 published pages, six-axes concept, G-01 pillar rewrite

**Wave 7** *(blocked on Wave 6 completion)*

- [ ] 16-14-PLAN.md — the adoption-argument page + its standing gate

**Wave 8** *(blocked on Wave 7 completion)*

- [ ] 16-15-PLAN.md — Section-2 published pages; retire `examples/03-harness-portability`

**Wave 9** *(blocked on Wave 8 completion)*

- [ ] 16-16-PLAN.md — Section-3 skills pages + eight reference/how-to re-cuts

**Wave 10** *(blocked on Wave 9 completion)*

- [ ] 16-17-PLAN.md — Section-3 embed pages; retire `examples/04-cross-process`, `07-artifact-store-mcp`

**Wave 11** *(blocked on Wave 10 completion)*

- [ ] 16-18-PLAN.md — terminal retirement: adopters guide, seven examples, final nav

**Wave 12** *(blocked on Wave 11 completion)*

- [ ] 16-19-PLAN.md — phase close: `make gate-16`, gate package, §3.1 review protocol

**Cross-cutting constraints:**

- The example's spine contributes one gate call site, one projecting body and one resolved binder site, so the three headroom-free tests/products/ floors survive waves 8 and 10 until plan 16-18 re-floors at wave 11
- Every out-of-swept-tree coupling this plan owns is named in files_modified before the sweep runs, so the sweep confirms rather than discovers

**Success Criteria** (what must be TRUE):

  1. Sections 1–3 are published in `public/` and each runs end-to-end by a single documented command, with Section 4 absent and named as Phase 17's (`D-01`)
  2. Section 1 invokes no agent — deterministic assembly only — so UAT gap G-01's agent-first framing is closed by construction rather than by editing the condemned pages (`D-12`)
  3. Every Section 2 client leg imports nothing from `ccf`, with the zero-CCF-dependency claim visible in the client's own import list and asserted in CI, across all three harnesses: Claude Agent SDK, Google ADK, LangGraph (`D-09`, `D-IMPL-24`)
  4. One parameterized example runner, with a CI matrix asserting equivalent Context Products across `sqlite`, `memory`, `postgres`, `neo4j`, `mongo` and `fluree`; `sqlite` + `memory` run in always-on CI which stays deterministic and network-free, the four DGX databases are an opt-in live-legs job, and no credential enters the tree (`D-06`)
  5. `examples/00`–`08` are retired and every published page that sources snippets from them is re-cut in the same phase — there is no partial state (`D-07`)
  6. Each example physically separates the **CCF call spine** from **deployment code** into distinct, separately-markered regions, legible to someone reading the repository and not only the rendered site, using Phase 14's `D-07` marker vocabulary (`D-11`)
  7. An adoption-argument page names what teams build instead — RAG over a vector store, hand-rolled context assembly, a semantic layer plus prompt templates — and states what each lacks: no replay, no policy binding at assembly, no lineage to a passage, no staleness measure; its worked demonstration is the UBO question, "Who ultimately owns Acme?" (`D-10`)
  8. Gate 2 (INV-CH7-47) is documented as **assembly-path integrity** and nowhere as a comparison of two independently authored sets, and the `tests/examples/test_*_output.py` checks that compare `required_operator_keys` against `operators_invoked` are not promoted as independence proofs (`D-IMPL-86`, SURFACE-AUDIT §5.3 A-4)
  9. The carried advisories this phase owns are discharged in the published tree: A-1 (`from ccf.deployment import …` as the single preferred day-1 import), A-2 (a maintainer page for the surface toolchain), A-3 (the pre-15 surface described in the shipped docs), A-8 (`role: load` artifacts reachable on `BootedFabric.artifacts` and absent from the replay pin set)
  10. Nothing leaks into the core: zero harness imports in `src/`, no LLM client in any `@algorithmic` module, no prompt/agent/task/threshold literal outside an artifact, and no substrate name outside the backend registry — all four CI-enforced — while changes to the fabric itself are permitted and expected where this phase finds a defect (`D-IMPL-96`, Dave, 2026-08-10, revoking the former "no fabric changed" wording and with it `D-13`'s docstring carve-out, `D-14`'s two-limb bound, and plan 16-19's `gate_16.py` allowlist; Mode 2 packaging still attaches **above** `serve()` per `D-IMPL-94`, and there is still no Mode 2 packaging stage, no Mode 3 coordinator, no `src/ccf/unstructured/`, and no tier-3 external sources)

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
| 15.1. Ergonomics Gap Closure — Governance Enforced, Not Conventional | 20/10 | Complete    | 2026-08-07 |
| 15.2. Substrate Adapters and Query Pushdown | 14/14 | Complete    | 2026-08-08 |
| 15.3. Fluree Adapter (Tier-1 Substrate) | 6/5 | Complete    | 2026-08-09 |
| 15.5 Context Product Surface — Vessel, Assembler, Debt, Entitlement | 15/15 | Complete | 2026-08-11 |
| 15.6 Decision-Completeness and Defect Closure | 0/? | Planned | — |
| 16. Documentation Rewrite — Deterministic Path & Adoption Argument | 6/21 | Parked (resumes after 15.6) |  |

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
