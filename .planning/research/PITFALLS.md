# Domain Pitfalls — v0.2 Performance, Documentation & Hardening

**Domain:** Adding perf benchmarking + CI regression gating, adopter docs, and auth/thread-safety hardening to a shipped, invariant-locked Python SDK (1339 tests, mypy --strict, 8 CI examples)
**Researched:** 2026-07-31
**Confidence:** Perf-CI pitfalls MEDIUM-HIGH (verified against current CI-benchmarking sources); docs pitfalls MEDIUM; hardening pitfalls HIGH (grounded directly in this repo's v0.1 audit register)

---

## A. Performance Battery Pitfalls

### Critical

### A1: Trusting absolute numbers on GitHub-hosted runners
**What goes wrong:** Regression gate uses absolute thresholds ("assemble < 40ms") or tight relative thresholds on hosted runners. Hosted runners are multi-tenant; identical code can swing ±30% run-to-run (coefficient of variation ~2.6% typical, tail much worse). The gate flaps, gets `continue-on-error`'d or deleted within weeks.
**Why it happens:** Baselines committed from one machine (dev box or one lucky runner) treated as truth everywhere.
**Consequences:** Either false-positive fatigue → gate ignored, or thresholds loosened so far real regressions pass.
**Prevention:**
- Relative thresholds only (PROJECT.md already says relative — hold that line), compared against a baseline *measured on the same runner class in the same job* where possible (run baseline ref + candidate in one job, or use pytest-benchmark `--benchmark-compare` against a cached same-runner baseline).
- Wide gate in CI (e.g., fail only >30–50% regression on medians, min-of-N); tight thresholds live in `make perf` locally where the machine is controlled.
- Keep the CI perf job **opt-in/non-blocking initially**; promote to blocking only after observing variance over ~2 weeks of runs.
- Prefer instruction/allocation counting (CodSpeed-style, or `sys.monitoring`/tracemalloc-based proxies) for the micro layer if wall-clock proves too noisy.
**Detection:** Perf job verdict changes on re-run with no code change.
**Phase:** The perf-battery phase, first plan — the threshold/baseline strategy is a design decision, not an implementation detail.

### A2: Measuring the wrong layer (LLM/IO in the timed path)
**What goes wrong:** Benchmarks time paths that cross the Algorithmic ⇄ Semantic seam or hit disk/network (SQLite fsync, file ArtifactStore, MCP transport), so numbers measure the mock/backend, not fabric mechanism. Cross-process latency benchmarks especially: they end up measuring uvicorn startup or event-loop scheduling.
**Why it happens:** Reusing example 00–07 flows as-is for benchmarks — convenient but they exercise full stacks.
**Consequences:** Regression signals fire on backend/config changes; real operator/projection regressions are invisible in the noise.
**Prevention:** Explicit layer taxonomy in the battery: (1) micro — operators, projection, contract validation, pure in-memory graph, no IO; (2) fabric load curves — in-memory or SQLite-`:memory:`; (3) cross-process — measured as a separate class with separate (much looser) thresholds, timing steady-state request latency after warm connections, never process startup; (4) replay-at-scale. Tag every benchmark with its layer; gate only micro+fabric layers.
**Detection:** A benchmark's variance dominated by IO wait; profiling shows <50% time in `ccf` code.
**Phase:** Perf-battery design.

### A3: Python warmup/GC noise misattributed as regressions
**What goes wrong:** First iterations pay import, JIT-less bytecode cache, Pydantic model build, and allocator warmup costs; GC pauses land inside timed regions. min/mean disagree wildly.
**Prevention:** Use pytest-benchmark (calibrated rounds, warmup on) rather than hand-rolled `time.perf_counter` loops; `gc.disable()` or `gc.collect()` between rounds for micro benchmarks; compare medians/min, never means; never run benchmarks under `pytest-xdist` (corrupts timing) — separate `make perf` target excluded from the parallel test run.
**Detection:** min ≪ median, or first-round outliers dominating.
**Phase:** Perf-battery implementation; encode in benchmark harness fixtures once, centrally.

### Moderate

### A4: Baselines going stale vs code (benchmark rot)
**What goes wrong:** Committed baselines refer to renamed benchmarks or old fixture shapes; comparisons silently compare nothing ("no matching benchmark" is a warning, not a failure) or compare against a baseline from 3 releases ago that legitimized slow drift (boiling-frog: each PR passes the relative gate while cumulative regression compounds).
**Prevention:** (a) Fail the perf job if any current benchmark lacks a baseline match and vice versa; (b) re-baseline ritual documented and *gated* — a baseline update is a reviewed commit with a stated reason, like a decision-log entry; (c) additionally track against the v0.2-release absolute baseline informationally to see cumulative drift.
**Phase:** Perf-battery; the re-baseline policy belongs in docs (ties to milestone B).

### A5: Benchmark fixtures violating the No-Hardcoding Rule or invariants
**What goes wrong:** Perf fixtures shortcut through internals (direct L3 writes to build a big graph fast, inline agent definitions "just for load generation"), breaking single-writer discipline in test code and tripping — or worse, getting exempted from — the No-Hardcoding/harness-import lints.
**Prevention:** Benchmarks construct state through the same factories/L2 path as tests do, from fixture artifacts; if graph-build time makes that impractical, build once per session and snapshot via the ArtifactStore rather than exempting lint scope. Decide lint scope for `benchmarks/` explicitly up front (same rules as `/tests`).
**Phase:** Perf-battery plan — call out fixture strategy explicitly.

### Minor

### A6: Perf suite bloats default CI wall-time
**What goes wrong:** `make ci` grows 10+ minutes; contributors start skipping it.
**Prevention:** Perf job separate workflow/label-triggered; `make ci` unchanged; a single smoke benchmark (seconds) in default CI to catch harness breakage, not performance.

---

## B. Documentation Pitfalls

### Critical

### B1: Duplicated truth — prose restating docstrings, both drifting
**What goes wrong:** Adopter's guide and Protocol reference hand-copy signatures, whitepaper citations, and invariant statements already living in docstrings (which this repo mandates per public class). Six weeks later they disagree; adopters trust the wrong one.
**Prevention:** Docstrings remain the single source for API-level truth; the Protocol reference is generated (autodoc/mkdocstrings/pdoc) from them; prose docs link into generated reference instead of restating signatures. Anything the docs *assert* about behavior that can be executed should be executed: doctest or `pytest --doctest-modules` for snippet-bearing docstrings, and doc code blocks either extracted-and-run in CI or literal-included from files that already run (the examples).
**Detection:** Grep for signatures in `.md`/`.rst` prose; any hit is a drift candidate.
**Phase:** Docs phase, first decision: toolchain + generated-vs-prose boundary.

### B2: Examples-vs-docs divergence
**What goes wrong:** Docs embed pasted snippets from the 8 examples; examples evolve (they're CI-run, so they *stay correct*), pasted copies don't. The docs become the only broken thing in the repo because they're the only untested thing.
**Prevention:** Never paste example code — use literal-include by path (with named regions/markers) so docs render the file CI already runs. A docs-build CI step fails on missing include paths/markers. READMEs per example already exist per §9 discipline; docs should link/transclude them, not fork them.
**Phase:** Docs phase; add docs build to CI in the same PR that adds docs.

### Moderate

### B3: Autodoc breaking the mypy/lint/No-Hardcoding discipline
**What goes wrong:** Doc tooling drags in `conf.py`/plugin code, doctest fixtures with inline agent-definition strings (No-Hardcoding violation in spirit), or type-unclean helper scripts that either get exempted from mypy --strict (eroding the norm) or block the build. Autodoc importing `ccf_runtime` modules can also mask import-order issues or execute side effects at import time.
**Prevention:** Docs tooling in a `docs/` dir with its own explicitly-scoped lint config (an *explicit, reviewed* exemption, not a silent one); doctest fixtures reference the same fixture artifacts tests use; docs build imports modules the same way tests do and runs in CI so import-time side effects surface immediately.
**Phase:** Docs phase setup.

### B4: OpenAPI spec drifting from the FastAPI app
**What goes wrong:** "OpenAPI polish" done by hand-editing an exported spec file; next route change desynchronizes it.
**Prevention:** The spec is always regenerated from `create_app()` (descriptions/examples live in route decorators and Pydantic models); CI check: regenerate and diff against the committed spec, fail on mismatch.
**Phase:** Docs phase (EXPR surface).

### B5: Documenting v0.1 behavior that v0.2 hardening changes
**What goes wrong:** Docs and hardening land in parallel phases; the security/deployment notes describe the pre-WR-01 authorization model or the old `create_app` default.
**Prevention:** Sequence hardening **before** the security/deployment docs section (or same phase, hardening-first tasks). The `create_app` unauthenticated-default warning (audit item) is a docs+code joint deliverable — write them together.
**Phase:** Roadmap-level ordering: hardening phase precedes (or is interleaved before) the security-docs tasks.

---

## C. Hardening Pitfalls

### Critical

### C1: WR-01 fix leaves an alternate door open (authorization bypass by surface)
**What goes wrong:** Per-tenant authorization (TokenGrant.scopes enforcement) is added at the HTTP door but not at the MCP door and CLI path, or not at the transport layer they all converge on. Audit says "HITL **doors**" plural: enforcing scopes in FastAPI dependencies only re-creates the bug one door over. Same class of bug: enforcing on `approve` but not `reject`/queue-inspect/replay-query endpoints.
**Why it happens:** Fixing where the finding was filed (HTTP) rather than at the choke point.
**Prevention:** Enforce authorization at the shared layer all doors pass through (transport/Control-Plane boundary), with doors contributing identity only; write a cross-door test matrix (HTTP × MCP × CLI × {approve, reject, inspect}) asserting tenant-scoped refusal on every cell. Grep for every call site of the transport before declaring done.
**Detection:** A door test suite that only exercises HTTP.
**Phase:** Hardening phase; the cross-door matrix is the acceptance criterion.

### C2: Hardening breaks replay byte-equality / example determinism silently
**What goes wrong:** Adding authz checks, lock acquisition ordering, or new audit fields changes replay-record contents or Context Product bytes; example 06's byte-equal replay and example 03's 915-byte ×3 identity assertions fail — or worse, examples are "fixed" by regenerating expected outputs, silently absorbing a behavior change that should have been a decision.
**Prevention:** Treat any expected-output regeneration in examples as a *blocking review event* with a written rationale; run the full example suite locally per hardening task, not once at phase end. New replay fields must be additive and versioned, not mutations of existing dimensions.
**Phase:** Hardening phase; per-task verification includes `make ci` examples sweep.

### C3: Lock-induced deadlock/starvation in the sync FastAPI threadpool (WR-02)
**What goes wrong:** InMemoryHitlTransport gets a `threading.Lock`, but a handler holds the lock while calling back into something that dispatches to the same threadpool (or awaits a suspended-workflow resume that needs the lock), deadlocking under load; or a lock is held across a blocking wait for human approval — which by design suspends indefinitely. Mixed sync/async is the aggravator: AdkWorkflowDriver already uses `asyncio.run` inside (WR-03) — `asyncio.run` inside a threadpool thread holding a lock that an async path also wants is a classic deadlock recipe.
**Prevention:** Locks guard *data structure mutation only* (enqueue/dequeue/state transition), never held across callbacks, IO, awaits, or workflow resume; keep critical sections small enough to reason about in one screen; fix WR-03's `asyncio.run` (replace with loop-aware scheduling or make persisted_state sync) *before or with* WR-02 so the sync/async seam is clean when locks arrive. Add a threaded stress test (N threads hammering approve/inspect through TestClient) with a timeout as a regression guard.
**Detection:** Test-suite hangs under `pytest-timeout`; requests stuck only when concurrent.
**Phase:** Hardening phase; order WR-03 → WR-02 (or joint).

### C4: ApprovalGate.resolve signature change ripples through the 1339-test suite and D-IMPL-62
**What goes wrong:** Making `resolve` compose with `signed_binding_required` (post-v0 D-IMPL candidate per audit) changes a shipped surface: adding a required parameter breaks every existing call site/test; adding an optional one that defaults to "unsigned allowed" quietly preserves the security gap under a new name. Also this touches D-IMPL-62 (door-only path) — a *design decision*, not a patch.
**Prevention:** This is explicitly a Phase D mini-cycle per CLAUDE.md §3: log the D-IMPL, propose readings (e.g., `resolve()` refuses when the gate's policy requires signed binding, directing callers to the door path; vs. `resolve(binding=...)` accepting a signed binding directly), get Dave's ruling before code. Whatever lands: keyword-only new parameters, explicit refusal (typed error) rather than permissive default, deprecation shim if the old call shape must keep working for examples.
**Phase:** Needs its own decision entry *before* the hardening phase implements it — flag in roadmap as gated-on-Dave.

### Moderate

### C5: `create_app` auth-default change vs "loud warning" scope creep
**What goes wrong:** The audit asks for a **loud adopter-facing warning** on the unauthenticated default; the tempting "real fix" is flipping the default to authenticated — which breaks example flows, quickstart ergonomics, and possibly tests that construct the app bare.
**Prevention:** Do what the audit item says (runtime warning + docs callout + security-notes section); flipping the default is a separate decision for Dave if proposed. If a warning is added, assert it in a test so it can't silently vanish, and silence it explicitly in examples via visible configuration (teaching moment, not `warnings.filterwarnings` buried in a conftest).
**Phase:** Hardening + docs joint task (see B5).

### C6: Tenant scoping added to HITL but not to adjacent query surfaces
**What goes wrong:** WR-01 fix scopes approval actions, but replay queries, artifact inspection, and queue listing over HTTP/CLI still return cross-tenant data — the graph already has `tenant_id` first-class, so the mechanism exists but isn't threaded through the Experience Layer reads.
**Prevention:** During WR-01 work, inventory every Experience Layer read endpoint for tenant filtering; anything out of v0.2 scope gets an explicit tech-debt entry rather than silence.
**Phase:** Hardening phase (inventory task), even if fixes partially defer.

### Minor

### C7: Thread-safety fixes narrowed to InMemory reference impl only
**What goes wrong:** The Protocol contract stays silent on thread-safety; user-supplied transports inherit the same bug.
**Prevention:** Document the concurrency contract on `HitlTransportProtocol` itself (docstring — feeding the generated Protocol reference, B1) and add a reusable transport-conformance test helper adopters can run.

---

## Phase-Specific Warnings (roadmap mapping)

| Phase topic | Likely pitfall | Mitigation |
|---|---|---|
| Hardening (first) | C1 alternate-door bypass; C3 deadlock; C2 replay drift | Choke-point authz + cross-door matrix; WR-03 before WR-02; example sweep per task |
| ApprovalGate × D-16 | C4 shipped-surface break | D-IMPL entry + Dave ruling before code (Phase D mini-cycle) |
| Perf battery | A1 hosted-runner variance; A2 wrong layer; A4 baseline rot | Relative thresholds, non-blocking first; layer taxonomy; baseline-match failure + re-baseline ritual |
| Docs (after hardening) | B1/B2 duplicated truth; B5 documenting pre-hardening behavior | Generated reference + literal-includes, docs build in CI; sequence after hardening |

**Ordering implication for roadmap:** Hardening → Perf → Docs (docs last so they describe hardened behavior and can document the perf/re-baseline rituals; perf before docs also lets docs cite measured numbers). ApprovalGate D-IMPL is a gate before its hardening task.

## Sources

- [CodSpeed — Benchmarks in CI: Escaping the Cloud Chaos](https://codspeed.io/blog/benchmarks-in-ci-without-noise) — hosted-runner CoV ~2.66%, bare-metal 0.56% (MEDIUM)
- [Bencher — Track pytest-benchmark in CI](https://bencher.dev/learn/track-in-ci/python/pytest-benchmark/) — baseline caching, statistical thresholds (MEDIUM)
- [pytest-benchmark guide, QASkills 2026](https://qaskills.sh/blog/pytest-benchmark-performance-testing-guide) — xdist corruption, baseline-compare workflow (LOW-MEDIUM)
- [Sphinx autodoc docs](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html) — docstrings-as-source pattern (HIGH for mechanism)
- This repo: `.planning/v0.1-MILESTONE-AUDIT.md` tech-debt register; `CLAUDE.md` §3, §6.4, §9, §11 (HIGH — direct)
