# Feature Landscape — v0.2: Performance Battery, Documentation Suite, Hardening Intake

**Domain:** Protocol-heavy Python SDK for governed agent context (CCF SDK), post-v0.1
**Researched:** 2026-07-31
**Scope:** NEW v0.2 features only. Existing v0.1 surfaces (fabric L1–L6, archetypes/factory/skilling, MCP/A2A, three harness adapters, Workflow/HITL with signed-binding auth, CLI/HTTP/MCP doors, eight CI examples) are treated as dependencies, not features.

---

## Category A — Performance Test Battery

### What adopters expect (norms for context/graph/agent SDKs)

Adopters of an infrastructure SDK expect three things before trusting it in production: (1) published numbers with the hardware/config they were measured on, (2) a way to reproduce those numbers locally (`make perf`), and (3) evidence that regressions are caught mechanically, not by vigilance. The credible-baseline story is *committed baseline JSON + environment manifest + relative regression thresholds in CI*, not absolute SLO promises — absolute numbers on shared CI runners are noise; relative comparison against a same-run or pinned baseline is the industry norm (pytest-benchmark `--benchmark-compare-fail`, CodSpeed's relative PR deltas, asv's trend detection).

**Metrics that matter for this SDK specifically:**

| Metric class | What to measure (CCF mapping) | Why adopters care |
|---|---|---|
| Micro-latency | Operator invocation, operator composition `(A∘B)`, Π projection, ContextProduct validation-gate cost, λ_c/D_c computation | Per-call overhead of the trust layer — "what does CCF cost me per decision?" |
| Ingest throughput | L1→L2→L3 events/sec (idempotent upsert path, lineage accumulation), single-writer path | Fabric is write-serialized by design; adopters need the ceiling |
| Scale curves | Assembly + product latency vs graph size (1K/10K/100K/1M entities), similarity-index query vs index size | Non-linear cliffs are the #1 graph-store adoption fear |
| Tail latency | p50/p95/p99 for product serving (in-process, MCP egress, A2A round-trip incl. signing/admission verification) | Agent loops are latency-sensitive; p99 governs UX, mean lies |
| Replay-at-scale | Replay resolution time vs artifact-history depth; snapshot restore cost | Year-scale replay tractability is a whitepaper commitment (§7.10, D-IMPL-06) |
| Cross-process overhead | MCP vs A2A vs in-process for the same product; serialization + signature verification share | Quantifies the price of the governance seams |

### Table Stakes

| Feature | Why Expected | Complexity | Depends on (v0.1) |
|---|---|---|---|
| Micro-benchmark suite (pytest-benchmark style, in-repo, `make perf`) | Reproducibility is the baseline credibility unit | Low-Med | Operators, Π, product gates, half-life/debt |
| Committed baseline files + environment manifest (CPU, Python, backend, dataset seed) | Numbers without environment are marketing | Low | — |
| Relative regression thresholds (e.g., fail >20–30% slowdown vs baseline), opt-in CI job | Absolute thresholds flake on shared runners; opt-in keeps main CI fast | Med | ci.yml, Makefile |
| Synthetic dataset generator (parameterized graph sizes, deterministic seed) | Scale curves need reproducible fixtures; must be domain-neutral per No-Hardcoding | Med | L1/L2 ingest, ontology registration |
| Latency percentiles (p50/p95/p99), not just means | Standard for anything on an agent's hot path | Low | benchmark harness |
| Perf results documented (a `docs/PERFORMANCE.md` or docs page with methodology) | The baseline story is a docs deliverable too | Low | docs suite (Category B) |

### Differentiators

| Feature | Value | Complexity | Notes |
|---|---|---|---|
| Governance-overhead decomposition: "cost of trust" benchmark (product path with vs without validation gates / signing / admission) | Directly answers CCF's core adoption question; almost no SDK does this | Med | Needs careful flag design so "without gates" exists only in bench harness, never as a product path |
| Replay-at-scale battery (replay N decisions against M-deep artifact history) | Proves the year-scale replay claim empirically | Med-High | ArtifactStore, snapshot strategy (D-IMPL-06/26) |
| Composition-preservation perf test (`(A∘B)(G)` vs `A(B(G))` timing parity) | Ties an existing CI invariant to a perf property | Low | Existing invariant tests |
| Two-backend curves (SQLite vs Postgres reference impls) | Shows the Protocol seam has no hidden cost cliff | Med | D-IMPL-02 backends; Postgres in CI is extra infra |

### Anti-Features

| Anti-Feature | Why Avoid | Instead |
|---|---|---|
| Absolute-number SLO gates in CI ("must serve <50ms") | Flaky on shared runners; false-failure fatigue kills the gate | Relative thresholds vs committed baseline; absolute numbers live in docs with environment manifest |
| Perf job in the mandatory PR gate | Benchmarks are slow; doubles CI time | Opt-in/nightly/label-triggered job |
| LLM-in-the-loop benchmarks | Measures the vendor, not the SDK; violates cost sanity | Benchmark algorithmic path only; stub semantic stages (consistent with Algorithmic⇄Semantic lint) |
| Building/adopting a dashboarding service (Bencher, CodSpeed SaaS) in v0.2 | Private repo, single-team; infra weight > value now | Committed JSON baselines + comparison script; SaaS is a later option |
| Load-testing the HTTP door with Locust/k6 as SDK scope | That's deployment-topology testing, explicitly not the SDK's problem | One cross-process latency benchmark suffices; note in deployment docs |

---

## Category B — Comprehensive Documentation Suite

### What adopters expect

For a Protocol-heavy Python SDK the Diátaxis quadrants map cleanly, and adopters of *this* SDK have a fifth need most SDKs don't: **artifact schema reference** (because behavior lives in definition artifacts, not code, per the No-Hardcoding Rule). The eight examples are already strong *tutorial* material — the gap is how-to guides, reference, and explanation.

**What the eight examples already cover (tutorial quadrant):** quickstart fabric (00), agent declaration/six axes (01), skilling lifecycle (02), harness portability (03), cross-process MCP/A2A (04), workflow+HITL (05), replay (06), ArtifactStore swap (07). Each has a README. That quadrant is ~done; docs should *link into* examples, not duplicate them.

**What's missing:**

### Table Stakes

| Feature | Why Expected | Complexity | Depends on (v0.1) |
|---|---|---|---|
| Adopter's guide (narrative "day 1 to production" path: install → ontology → projection → policy bundle → agent → workflow → serve) | The §1 adoptability promise ("hours or days") needs a single guided path; examples alone force archaeology | Med | All pillars |
| Protocol reference: every Protocol (storage, similarity, embedder, operator, projection, MCP/A2A transports, harness adapter, artifact store, orchestration, HITL router, experience) with contract, invariants, reference impl pointer, "implement your own" checklist | Protocols ARE the extension surface; undocumented Protocol = unusable seam | Med-High | All Protocols; docstrings already cite whitepaper sections |
| Definition-artifact schema reference (agent, task, workflow, policy bundle, skill entry/grant, prompt artifact; every field, semver lane rules, validation errors) | Adopters author artifacts, not code — this is their primary API | Med | D-IMPL-28 schema, factory validation |
| API reference generated from docstrings (mkdocstrings/Sphinx autodoc), building in CI | Standard for any Python SDK; docstrings already exist with citations | Low-Med | mypy-strict codebase |
| How-to guides for the top adoption tasks (write a custom operator; implement a storage backend; bind a new harness; stand up the MCP artifact server; wire HITL to an external queue; add an A2A peer) | Diátaxis how-to quadrant is empty today | Med | respective Protocols |
| Concepts/explanation pages (pillars, fabric layers, control vs data plane, replay dimensions, dual-channel specialization, harness-neutrality rationale) | Whitepaper is 100+ pages and proprietary framing; adopters need a distilled conceptual layer | Med | CLAUDE.md/whitepaper as source |
| Security & deployment notes (auth posture of each front door, A2A trust boundary, tenant model, what the SDK does NOT secure) | Required for production credibility; pairs with Category C's auth-default warning | Med | HITL auth, create_app, A2A admission |
| OpenAPI polish (descriptions, auth schemes, error models, examples on every endpoint) | The HTTP API skeleton shipped; adopters building UX layers depend on it | Low-Med | HTTP door |
| Docs build in CI (link check, doctest/snippet execution where feasible) | Stale docs are worse than none; matches "broken example is broken build" ethos | Low-Med | ci.yml |

### Differentiators

| Feature | Value | Complexity | Notes |
|---|---|---|---|
| Diátaxis-organized site (MkDocs Material) with explicit quadrant navigation | Signals doc maturity; Canonical/Python-community-endorsed pattern | Low-Med | Framework choice is a decision for planning |
| Invariants page: every CI-enforced invariant, what enforces it, what an adopter must not do to break it | Unique to CCF's audit-by-construction story | Low | lints already exist |
| Whitepaper cross-reference index (docs section ↔ whitepaper § ↔ code module) | Fidelity-first projects rarely make the traceability navigable | Low-Med | existing docstring citations |
| "Anatomy of a replay record" walkthrough with a real example-06 record | Replay is the headline claim; showing the five dimensions concretely sells it | Low | example 06 |

### Anti-Features

| Anti-Feature | Why Avoid | Instead |
|---|---|---|
| Publishing the whitepaper or paraphrasing it wholesale into public-shaped docs | Proprietary IP; repo stays private | Concepts pages distilled and self-contained; cite §s internally |
| Domain-flavored tutorials beyond the existing example domains | Blurs mechanism/values line | Keep domain specifics inside example artifacts |
| Hand-written API reference | Drifts immediately | Generate from docstrings; hand-write only Protocol/concept layers |
| Hosted docs site infrastructure decisions in v0.2 (public hosting, versioned docs portals) | Private repo; premature | Build docs in CI, browse locally/artifact; hosting is a later decision |

---

## Category C — Hardening Intake

### What adopters expect (per item)

**WR-01 — Per-tenant authorization on HITL doors.** Norm: authentication answers "who," authorization answers "which tenant's queue." Expected behavior: `TokenGrant.scopes` enforced at the HTTP door — a token scoped to tenant A gets 403 (not 404-leak, not empty-list-silent) on tenant B's queues; list endpoints filter to granted scopes; the authz decision (grant id, scopes evaluated, outcome) lands in the audit/replay surface like every other Control Plane action. Deny-by-default when scopes are absent. Complexity: **Med**. Depends on: HITL doors, TokenGrant model, signed-binding auth, tenancy model (D-IMPL-05 resolution). Table stakes — an authenticated-but-unauthorized multi-tenant queue is a finding-class defect.

**WR-02 — Thread-safe in-memory transports.** Norm: FastAPI runs sync handlers in a threadpool, so any in-memory reference transport must be safe under concurrent access. Expected behavior: `InMemoryHitlTransport` (and any sibling in-memory reference impls — audit them all, not just the named one) synchronized via `threading.Lock`/`asyncio.Lock` as appropriate to the call surface; documented concurrency contract on the transport Protocol ("implementations MUST be safe under concurrent invocation" or explicitly single-threaded); a concurrency stress test in the suite. Complexity: **Low-Med** (the fix is small; the Protocol-contract documentation and test are the real deliverable). Table stakes.

**WR-03 — ADK driver robustness.** Expected behavior: no `asyncio.run` inside library code paths that may already be in an event loop (`persisted_state` should be restructured — sync accessor over persisted data or async method, per whatever the driver Protocol allows); unexecuted-segment access raises a typed, documented SDK error (e.g., `SegmentNotExecutedError`) instead of bare `KeyError`. Parity check against the other two harness drivers so behavior is uniform across adapters (portability story requires uniform failure semantics). Complexity: **Low-Med**. Depends on: AdkWorkflowDriver, HarnessAdapterProtocol seam contract.

**ApprovalGate.resolve × signed_binding_required (D-16 composition).** Currently `resolve` cannot compose with `signed_binding_required` (door-only path per D-IMPL-62). This is a *decision*, not just code: either (a) programmatic `resolve` accepts a signed binding and becomes a first-class authenticated path, or (b) it is formally restricted (raises a clear error when the policy demands signed binding — arguably the current behavior, made loud and documented). Norm for audit-first systems: no unauthenticated bypass of an authenticated gate, ever; whichever way it lands, replay must record the resolution path. **This is a D-IMPL candidate requiring Dave's ruling before implementation** — flag it as a gating decision for the hardening phase, not a task to default. Complexity: Med (option a) / Low (option b).

**create_app auth-default posture.** Two industry postures: secure-by-default (server refuses to start without auth config unless an explicit `allow_unauthenticated=True`/`--insecure` flag is passed) vs loud-warning (starts, but emits a prominent startup warning + response header/log line). The audit names "loud adopter-facing warning" as the intake item; the stronger norm in 2025-26 security guidance is explicit-opt-in-to-insecure, which is a small step further and cheap while the API is pre-1.0. Recommendation: explicit opt-in flag + loud warning when the flag is used + security-docs cross-link — but the exact posture is a plan-level decision (possible D-IMPL). Complexity: **Low**. Depends on: HTTP door factory, security docs page (Category B).

### Table Stakes / Differentiators / Anti-Features summary

| Feature | Class | Complexity |
|---|---|---|
| WR-01 scope enforcement, deny-by-default, 403 semantics, audit capture | Table stakes | Med |
| WR-02 synchronized in-memory transports + Protocol concurrency contract + stress test | Table stakes | Low-Med |
| WR-03 typed errors + no nested asyncio.run + cross-adapter parity | Table stakes | Low-Med |
| create_app explicit-insecure opt-in with loud warning | Table stakes (posture choice needs ruling) | Low |
| ApprovalGate.resolve composition resolution (D-IMPL first) | Table stakes once ruled | Low-Med |
| Concurrency/authz regression tests added to invariant suite | Differentiator (ties hardening to audit-by-construction brand) | Low |
| Security review checklist doc for adopters | Differentiator | Low |

| Anti-Feature | Why Avoid | Instead |
|---|---|---|
| Building a full RBAC/policy-engine for the HTTP door | Scope creep; policy regimes are Control Plane artifacts already | Enforce existing TokenGrant.scopes; richer authz via policy bundles |
| Shipping a production auth provider (OIDC integration etc.) | Deployment-topology territory | Document the seam; keep token/signing primitives |
| Silent-fix of ApprovalGate.resolve without a D-IMPL entry | Violates §15 discipline — whitepaper/SDK-doc-silent design point | Log D-IMPL, get Dave's ruling |
| History rewrite for the 55MB blob | Explicitly forbidden on main | Remains deferred; not v0.2 |

---

## Feature Dependencies

```
Perf battery ──▶ synthetic dataset generator ──▶ L1/L2 ingest, ontology registration
Perf CI job ──▶ committed baselines ──▶ micro-benchmark suite
Replay-at-scale bench ──▶ ArtifactStore + snapshot strategy (D-IMPL-06/26 as resolved in v0.1)
Docs security page ◀──▶ create_app posture + WR-01 (document what ships)
Artifact schema reference ──▶ D-IMPL-28 schema (resolved in v0.1)
ApprovalGate.resolve fix ──▶ new D-IMPL ruling (GATING)
WR-01 ──▶ D-IMPL-05 tenancy model semantics
PERFORMANCE.md ──▶ perf battery results (perf phase before/with docs phase finalization)
```

## Milestone shape recommendation

1. **Hardening first** (small, closes audit debt, and its outcomes are documented by the docs phase; the ApprovalGate D-IMPL is the only gating decision — surface it immediately).
2. **Performance battery second** (independent of hardening except that benchmarks should run against hardened code; produces numbers docs will publish).
3. **Documentation last/overlapping** (documents the hardened postures and the measured baselines; API-reference generation and Protocol reference can start in parallel with perf).

Defer: perf SaaS/dashboarding, docs hosting, HTTP load testing, RBAC engine, history rewrite.

## Confidence

| Area | Level | Basis |
|---|---|---|
| Perf norms (relative thresholds, pytest-benchmark-family tooling, percentiles) | HIGH | Ecosystem-wide convention, verified via CodSpeed/pytest-benchmark/Bencher guidance |
| CCF-specific metric mapping | MEDIUM | Derived from v0.1 surfaces + whitepaper commitments; exact battery composition is a plan decision |
| Diátaxis docs structure + gap analysis vs eight examples | HIGH | Diátaxis is the established Python-community framing; example coverage read from PROJECT/audit |
| Hardening expected behaviors (deny-by-default, 403, typed errors, lock-under-threadpool) | HIGH | Standard security/concurrency practice; specifics anchored in 08-REVIEW findings |
| create_app posture & ApprovalGate resolution | MEDIUM | Two defensible options each; needs Dave's ruling — flagged, not defaulted |

## Sources

- v0.1 audit tech-debt register: `.planning/v0.1-MILESTONE-AUDIT.md` (WR-01/02/03, D-IMPL-62 note, create_app residual)
- Project scope: `.planning/PROJECT.md`, `CLAUDE.md` §§6.4, 7.3, 9, 13
- [CodSpeed — benchmarking Python with pytest](https://codspeed.io/docs/guides/how-to-benchmark-python-with-pytest); [pytest-codspeed](https://github.com/CodSpeedHQ/pytest-codspeed); [Bencher on pytest-benchmark](https://bencher.dev/learn/benchmarking/python/pytest-benchmark/) — relative-threshold CI norms
- [Diátaxis](https://diataxis.fr/); [Python.org Diátaxis adoption discussion](https://discuss.python.org/t/adopting-the-diataxis-framework-for-python-documentation/15072)
