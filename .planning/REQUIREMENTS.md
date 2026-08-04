# REQUIREMENTS — CCF SDK v0.2

**Milestone:** v0.2 Performance, Documentation & Demonstration
**Defined:** 2026-08-01
**Prior milestone:** v0.1 (shipped 2026-07-31, tag `v0.1.0`) — see `.planning/milestones/v0.1-REQUIREMENTS.md`

## v0.2 Requirements

### Hardening (HARD)

- [ ] **HARD-01**: The D-IMPL ruling batch (WR-01 mapping shape, ApprovalGate×D-16 composition, perf governance, docs toolchain/publishing, D-10 amendment, create_app warning) is surfaced to Dave as one Phase D mini-cycle and rulings logged in `docs/DECISIONS.md`
- [ ] **HARD-02**: In-memory HITL transports are thread-safe with a documented Protocol concurrency contract and a passing stress test (WR-02)
- [ ] **HARD-03**: ADK workflow driver is loop-safe (no nested `asyncio.run`) with typed errors and cross-adapter parity tests (WR-03)
- [x] **HARD-04**: HITL doors enforce per-tenant authorization per Dave's WR-01 ruling — deny-by-default, typed 403, authz decision in the audit record, cross-door × cross-action test matrix (WR-01)
- [x] **HARD-05**: ApprovalGate.resolve × signed_binding_required composed per Dave's ruling; create_app emits a loud warning on insecure default posture

### Performance (PERF)

- [x] **PERF-01**: Adopter can run `make perf` locally and get a reproducible micro-benchmark suite (operators, factory, validation gates) with p50/p95/p99
- [x] **PERF-02**: Fabric load/scale curves measure assembly and projection across graph sizes via a deterministic, domain-neutral synthetic dataset generator (built through L2/factory paths)
- [x] **PERF-03**: Cross-process latency (MCP egress, A2A/peering) and replay-at-scale suites prove the year-scale replay claim empirically
- [x] **PERF-04**: Committed runner-class-keyed baselines + `thresholds.toml` with relative-median regression gating in an opt-in `perf.yml` CI job; re-baseline ritual documented

### Documentation (DOCS)

- [ ] **DOCS-01**: Adopter's guide — day-1-to-production narrative (install → ontology → agent → workflow → replay)
- [ ] **DOCS-02**: Generated Protocol/API reference from citation-bearing docstrings (mkdocs-material + mkdocstrings), whitepaper never published
- [ ] **DOCS-03**: Definition-artifact schema reference — the adopter's primary authoring API
- [ ] **DOCS-04**: How-to guides + concepts pages (pillars, invariants, replay anatomy, whitepaper cross-reference index)
- [ ] **DOCS-05**: Security & deployment notes + OpenAPI polish with drift check
- [ ] **DOCS-06**: `make docs --strict` builds in always-on CI (logged D-10 amendment); PERFORMANCE.md publishes measured baselines with methodology

### Demonstration (DEMO)

- [x] **DEMO-01**: A synthetic fake data store — deterministic, multi-entity, domain values entirely in definition artifacts — ships as the demonstration substrate
- [x] **DEMO-02**: An end-to-end runnable example: data ingested through L1→L2, folded into the Context Graph, projected into typed Context Products, consumed by an agent that solves a concrete reasoning problem it could not solve from raw data alone
- [x] **DEMO-03**: A narrated walkthrough document in the docs site tracing the demo step-by-step ("how data folds into context"), literal-including the example's code and artifacts; demo runs in CI like the v0.1 examples

### Examples (EXAM)

- [ ] **EXAM-01**: Every v0.1 example (00–07) has a detailed narrated README — what it demonstrates, artifact-by-artifact explanation, whitepaper/CLAUDE.md sections exercised, and "what to change first to adapt it"
- [ ] **EXAM-02**: Example scenarios are enriched to exercise more of the SDK surface (specialization axes, skilling, HITL, replay) through richer definition artifacts — example code stays thin and generic per No-Hardcoding
- [ ] **EXAM-03**: The upgraded suite stays CI-green with a single documented command per example; any expected-output change is a reviewed, deliberate event
- [x] **EXAM-04**: An external agent with zero CCF imports client-side consumes typed Context Products, lineage, and the replay record over the authenticated MCP surface, deterministically in CI, across bare-MCP, Anthropic-SDK, and Google-ADK legs (family charter + `examples/external/00-hello-context`)
- [x] **EXAM-05**: The external-consumer example is hardened against the four-AI consensus concerns — live-captured diff-reviewed fixtures with a schema guard and request-fingerprint replay matching, a server-side tool allowlist, byte-path/README/duration assertion hardening — and the three external-consumption tools (`get_context`, `get_lineage`, `get_replay_record`) are promoted into the SDK Experience surface, enabled by default

### SDK Ergonomics (ERGO)

- [ ] **ERGO-01**: A committed public-surface signature manifest + `make surface` regenerator + CI drift assertion, baselined at phase start before any surface change
- [ ] **ERGO-02**: A standing gate-independence guard — `run_gates` keeps two independently sourced inputs, enforced by a perturbation regression test, an AST identifier guard over `src/ccf/deployment/`, and a no-allowlist lint ban on `ccf.deployment` importing `ccf.products.gates`
- [ ] **ERGO-03**: The criterion-1 surface audit is an executable check recording per-example mechanical line counts before and after, reporting relocation and removal as separate figures
- [ ] **ERGO-04**: `ccf.deployment` exists in `/src`, algorithmic-tagged, `mypy --strict`-clean, with a docstring recording the CINV-03 reading ("no model call, not no I/O") and the `run_gates` worked example
- [ ] **ERGO-05**: A class-id → `ArtifactClass` lookup covering SDK-shipped classes with `declared_artifact_class` fallthrough, kept in sync with `artifacts.__all__` by test
- [ ] **ERGO-06**: Timestamp-shaped scalars load as strings and parse via `datetime.fromisoformat`; PyYAML's resolver is suppressed in the artifact path; designator-less timestamps refused naming D-IMPL-38
- [ ] **ERGO-07**: `ccf.resolution-spec` — a closed-world typed artifact class over entity and relationship rules, with `EntityResolutionSpec` gaining `semver` in place (D-IMPL-77) and its own regeneration checkpoint
- [ ] **ERGO-08**: A typed `ArtifactClass` per SDK-shipped operator category contracted by the existing `*Parameters` models; `DeclaredArtifact` remains the documented path for deployment-authored operators; both `artifacts.py` docstring sites amended
- [ ] **ERGO-09**: Typed artifact classes for the signal batch, perspective, and product-class declaration
- [ ] **ERGO-10**: A `ccf.deployment-manifest` artifact class enumerating every artifact explicitly (path, key, class), and one call that loads, validates, registers, and boots — returning the `FabricHandle` plus a plain typed pin set; backend kind declared in the manifest, connection supplied by the caller
- [ ] **ERGO-11**: A two-phase, view-aware operator-registry builder taking artifacts plus a `GraphView`, with the ordering constraint in the signature and the policy pin supplied by the adopter (D-IMPL-76)
- [ ] **ERGO-12**: `ccf schema export` emits JSON Schema per artifact class via a new HTTP route (D-IMPL-79); schemas are committed, example artifacts carry `$schema` headers, and a CI freshness gate guards drift
- [ ] **ERGO-13**: Examples 00–03, 07, 08 are rewritten to the streamlined surface and stay CI-green
- [ ] **ERGO-14**: Examples 04 (both files, including D-10's re-domaining to banking as a separate commit), 05, and 06 are rewritten and stay CI-green
- [ ] **ERGO-15**: `examples/external/00-hello-context/serve.py` is rewritten to the streamlined surface; the client legs keep zero CCF imports
- [ ] **ERGO-16**: Every example's CI assertions and print summaries relocate to a parallel `tests/` module with no loss of assertion coverage, and the No-Hardcoding Rule reaches the relocated domain values (D-IMPL-78 — `tests` added to both `LINTED_TREES` and `RULE_TREE_SCOPE`)
- [ ] **ERGO-17**: A curated surface-change log with rationale and migration guidance, written incrementally as per-plan fragments, covering additions, reshapes, removals **and behavior changes**, handed to Phase 16

## Future Requirements (deferred)

- Perf SaaS/dashboarding integration
- Docs hosting/publishing decision (beyond CI build)
- HTTP load testing (locust/k6)
- RBAC/policy engine for the HTTP door; OIDC provider integration
- 55MB-blob history rewrite

## Out of Scope

- Absolute-time perf gates on shared runners — flake by construction; relative-median thresholds only
- Hand-written API signatures or pasted snippets in docs — generated reference and literal-includes only (drift prevention)
- Domain values in demo/example code — No-Hardcoding Rule (CLAUDE.md §6.4); everything domain-specific in definition artifacts
- Defaulting any of the six Dave-ruling items — implement per rulings only

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARD-01 | Phase 9 | Pending |
| HARD-02 | Phase 9 | Pending |
| HARD-03 | Phase 9 | Pending |
| HARD-04 | Phase 10 | Complete |
| HARD-05 | Phase 10 | Complete |
| PERF-01 | Phase 11 | Complete |
| PERF-02 | Phase 11 | Complete |
| PERF-03 | Phase 11 | Complete |
| PERF-04 | Phase 11 | Complete |
| DEMO-01 | Phase 12 | Complete |
| DEMO-02 | Phase 12 | Complete |
| DEMO-03 | Phase 12 | Complete |
| EXAM-01 | Phase 13 | Pending |
| EXAM-02 | Phase 13 | Pending |
| EXAM-03 | Phase 13 | Pending |
| EXAM-04 | Phase 13.1 | Complete |
| EXAM-05 | Phase 13.2 | Complete |
| DOCS-01 | Phase 14 | Pending |
| DOCS-02 | Phase 14 | Pending |
| DOCS-03 | Phase 14 | Pending |
| DOCS-04 | Phase 14 | Pending |
| DOCS-05 | Phase 14 | Pending |
| DOCS-06 | Phase 14 | Pending |
| ERGO-01 | Phase 15 | Pending |
| ERGO-02 | Phase 15 | Pending |
| ERGO-03 | Phase 15 | Pending |
| ERGO-04 | Phase 15 | Pending |
| ERGO-05 | Phase 15 | Pending |
| ERGO-06 | Phase 15 | Pending |
| ERGO-07 | Phase 15 | Pending |
| ERGO-08 | Phase 15 | Pending |
| ERGO-09 | Phase 15 | Pending |
| ERGO-10 | Phase 15 | Pending |
| ERGO-11 | Phase 15 | Pending |
| ERGO-12 | Phase 15 | Pending |
| ERGO-13 | Phase 15 | Pending |
| ERGO-14 | Phase 15 | Pending |
| ERGO-15 | Phase 15 | Pending |
| ERGO-16 | Phase 15 | Pending |
| ERGO-17 | Phase 15 | Pending |

Coverage: 40/40 v0.2 requirements mapped, each to exactly one phase.
