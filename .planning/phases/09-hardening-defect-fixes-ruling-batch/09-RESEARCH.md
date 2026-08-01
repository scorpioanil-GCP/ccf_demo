# Phase 9: Hardening — Defect Fixes & Ruling Batch - Research

**Researched:** 2026-08-01
**Domain:** Python concurrency (threading.Lock, asyncio loop-safety), typed error hierarchies, D-IMPL ruling-batch preparation
**Confidence:** HIGH (defect sites read directly from the codebase; fix patterns are stdlib-verified)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Ruling batch mechanics (HARD-01)**
- **D-01:** Presentation is **decision doc + interactive**: one consolidated mini-cycle document committed to `docs/` (per item: context, 2–3 options with consequences, recommendation), then an interactive walkthrough with Dave via AskUserQuestion; each ruling logged to `docs/DECISIONS.md` as it lands. §3.1 mini-cycle protocol applies (review, triage, D-GATE entry).
- **D-02:** **Rulings first** — the mini-cycle runs at the start of Phase 9, before the WR-02/03 code plans execute.
- **D-03:** Options analysis is **research-backed**: targeted per-item research before drafting (e.g., mkdocs-material publishing options, perf regression-gate practices in comparable SDKs).
- **D-04:** Deferral posture is **partial-proceed**: a deferred item stays an open D-IMPL gating only its downstream phase; WR-02/03 work proceeds; any deferral flagged in the D-GATE-9 presentation.

**Concurrency contract shape (HARD-02, WR-02)**
- **D-05:** `HITLTransportProtocol` **requires thread-safety of every conforming implementation** — Protocol docstring states all methods must be safe for concurrent calls from multiple threads.
- **D-06:** In-memory reference transports synchronize with plain **`threading.Lock`** (restructure rather than RLock if a locked method would call another locked method).
- **D-07:** Stress test is a **mixed-op hammer with invariant checks**: ~16–32 threads concurrently submitting, listing, resolving against one transport for a bounded duration; hard pytest timeout; post-run invariant assertions (no lost/duplicated events, no deadlock); deterministic seed.
- **D-08:** Concurrency contract documented **in the Protocol docstring only**.

**ADK loop-safety strategy (HARD-03, WR-03)**
- **D-09:** **Loop-aware dispatch**: sync API preserved; no running loop → `asyncio.run`; running loop detected → execute the coroutine on a dedicated background thread/loop and join.
- **D-10:** Typed errors form a **small dedicated hierarchy**: driver-error base (e.g., `WorkflowDriverError`) with `SegmentNotExecutedError` replacing the bare `KeyError`, plus a state-retrieval-failure subclass. Mirrors the SignedBinding Required/Invalid split style.
- **D-11:** Loop-safety pattern and error hierarchy apply to **all three drivers** (ADK, Claude Agent SDK, LangGraph) as shared mechanism; parity tests assert identical typed behavior.
- **D-12:** Shared dispatch helper and error hierarchy live in a **common module under `runtime/ccf_runtime/orchestration/`** — out of `/src` core.

**Parity tests & CI-freeze discipline**
- **D-13:** Cross-adapter parity tests assert **behavior + typed errors**: equivalent persisted state/replay records, identical typed errors for unexecuted segments, and loop-safety from both plain sync context and inside a running event loop.
- **D-14:** Byte-identical examples guarantee via the **existing eight-example sweep plus a one-time pre/post hash check** of expected-output files. Any diff is a blocking review event. No permanent standing hash gate.
- **D-15:** Stress and parity tests join the **normal `/tests` suite, always on**; hammer bounded to seconds; no slow/nightly tagging.

### Claude's Discretion
- Exact thread count/duration of the hammer test within the ~16–32 / seconds-bounded envelope.
- Exact names and module layout of the shared driver-error hierarchy and dispatch helper, matching existing runtime orchestration conventions.
- Ordering of the six items within the ruling-batch document.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARD-01 | Six-item D-IMPL ruling batch surfaced to Dave as one Phase D mini-cycle; rulings logged in `docs/DECISIONS.md` | Ruling-item inventory (below), existing D-IMPL entry format (verified in `docs/DECISIONS.md`), per-item research seeds for docs-toolchain and perf-governance items |
| HARD-02 | In-memory HITL transports thread-safe with documented Protocol concurrency contract and passing stress test (WR-02) | Defect analysis of `src/ccf/hitl/transport.py`, `threading.Lock` pattern, hammer-test design, no-new-dependency timeout approach |
| HARD-03 | ADK driver loop-safe (no nested `asyncio.run`), typed errors, cross-adapter parity tests (WR-03) | Defect analysis of `runtime/ccf_runtime/orchestration/adk/driver.py:278-290` and the bare-`KeyError` sites in all three drivers; stdlib loop-aware dispatch pattern; existing conformance-suite leg parametrization to extend |
</phase_requirements>

## Summary

Phase 9 is a hardening phase with zero new external dependencies and a well-bounded surface: (1) run a six-item ruling batch past Dave first (D-02), (2) synchronize `InMemoryHitlTransport` with `threading.Lock` plus a bounded stress test, (3) introduce a shared loop-aware dispatch helper and typed driver-error hierarchy under `runtime/ccf_runtime/orchestration/` and apply it to all three drivers with parity tests, and (4) prove the eight-example sweep stays byte-identical via a one-time pre/post hash check.

All defect sites were read directly. WR-02: `InMemoryHitlTransport` (`src/ccf/hitl/transport.py:292-438`) uses plain `dict`/`deque`/`list` with zero synchronization, and its `submit` path does Control-Plane resolution plus signature verification before appending — so the critical section design matters (verification should happen outside the lock; only queue mutations inside). WR-03: `AdkWorkflowDriver.persisted_state` (`runtime/ccf_runtime/orchestration/adk/driver.py:281`) calls `asyncio.run` inside a sync method — crashing when called from a running loop — and `_run` at line 185 does `self._outcomes[(tenant, execution_id)]`, a bare `KeyError` site; the LangGraph driver has three more bare `_outcomes[...]` lookups (lines 111, 153, 164) and the Claude Agent driver one (line 366).

**Primary recommendation:** Plan the phase as three plans in strict order — (P1) ruling batch mini-cycle, (P2) WR-03 shared dispatch + errors + parity tests, (P3) WR-02 lock + hammer test — with the pre-phase expected-output hash snapshot taken in P1 and asserted at phase close. No new packages; the hammer timeout is implemented with bounded thread joins + `pytest.fail`, not pytest-timeout.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Thread-safe HITL queue (WR-02) | SDK core (`src/ccf/hitl/`) | — | `InMemoryHitlTransport` and the Protocol docstring live in `/src`; `threading` is stdlib, no harness/LLM import, CINV lints unaffected |
| Loop-aware dispatch + driver errors (WR-03) | Runtime (`runtime/ccf_runtime/orchestration/`) | — | D-12 locks the common module here; keeps `/src` free of driver concerns and the `d06-orchestration-split` lint green |
| Parity + stress tests | `/tests` (conformance, hitl) | — | D-15: always-on normal suite; extend `tests/conformance/test_orchestration.py` leg parametrization |
| Ruling batch document | `docs/` | `docs/DECISIONS.md` | D-01: consolidated doc committed to docs/, rulings logged per existing D-IMPL entry format |
| Byte-identical examples check | Phase tooling (one-time hash) | Existing `make examples` CI | D-14: pre/post hash comparison, no permanent gate |

## Standard Stack

No new libraries. Everything needed is stdlib or already installed.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `threading` (stdlib) | Python 3.12+ | `Lock` for transport synchronization (D-06) | Locked decision; matches FastAPI threadpool sync access [VERIFIED: codebase — doors call transports synchronously] |
| `asyncio` (stdlib) | Python 3.12+ | `get_running_loop()` detection + `asyncio.run` on a background thread (D-09) | Stdlib-documented loop-detection idiom [CITED: docs.python.org/3/library/asyncio-runner.html — `asyncio.run` "cannot be called when another asyncio event loop is running in the same thread"] |
| `concurrent.futures` (stdlib) | Python 3.12+ | Background-thread execution + `Future.result(timeout=...)` join | Simplest correct "dedicated thread/loop and join" realization |
| pytest | 9.0.3 (installed) | Stress/parity tests | Existing suite [VERIFIED: `python3 -c "import pytest"` → 9.0.3] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-test bounded joins (`thread.join(timeout)` / `Future.result(timeout)`) + `pytest.fail` | `pytest-timeout` plugin | pytest-timeout is the ecosystem-standard hard-timeout tool but is **not installed** [VERIFIED: `pip show pytest-timeout` empty] and adds a dependency for one test. Bounded joins satisfy D-07's "hard pytest timeout" intent (the test cannot hang: every join is bounded and a missed deadline fails the test) with zero new packages. If the planner prefers the plugin, it is `pytest-timeout` on PyPI [ASSUMED — not slopcheck-verified this session] and must be gated per the audit note below. |
| Per-thread `asyncio.run` on a fresh executor thread | Persistent background loop + `asyncio.run_coroutine_threadsafe` | Persistent loop is faster for hot paths but adds lifecycle state (shutdown, thread ownership) to drivers whose sync entry (`persisted_state`) is a test-introspection seam called rarely. A fresh single-use thread per call is simpler and has no teardown hazard. |

**Installation:** none required.

## Package Legitimacy Audit

No new packages are recommended for this phase. If the planner elects `pytest-timeout`, it is tagged `[ASSUMED]` (not slopcheck-verified this session) and must be gated behind a `checkpoint:human-verify` task before install.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### Defect Site Analysis (verified by direct read)

**WR-02 — `src/ccf/hitl/transport.py`:**
- `InMemoryHitlTransport.__init__` (line 324): `self._pending: dict[str, deque[...]]`, `self._submissions: dict[str, list[...]]` — no lock.
- Races: `enqueue`/`dequeue`/`pending` on the same tenant's deque; `setdefault` on the dicts under concurrent first-touch; `submit`'s check-then-append with D-16 verification in between.
- Key design constraint: `submit` calls `_signed_binding_required()` (Control Plane resolve) and `_enforce_signed_binding()` (cryptographic verification) before appending. **Do not hold the lock across Control Plane resolution or signature verification** — only across the queue mutation. This also honors D-06's "restructure rather than RLock" rule since verification never touches the queues.
- `pending()`/`submissions()` return tuples (snapshots) — keep that; take the snapshot under the lock.

**WR-03 — the three drivers:**
- ADK `persisted_state` (line 278-290): `asyncio.run(self._sessions.get_session(...))` — raises `RuntimeError` inside a running loop [CITED: asyncio.Runner docs]. This is the primary nested-`asyncio.run` site named in the audit.
- Bare `KeyError` sites on `_outcomes` lookups: ADK `driver.py:185` (`return self._outcomes[(tenant, execution_id)]`), LangGraph `driver.py:111,153,164`, Claude Agent `driver.py:366`. All become `SegmentNotExecutedError` (D-10). The state-retrieval-failure subclass covers `persisted_state`/`checkpointed_values`-style introspection failures.
- The three drivers' introspection seams differ in name (`persisted_state` on ADK, `checkpointed_values` on LangGraph at line 168) — parity tests assert typed behavior per D-13, not method-name identity.

### Pattern 1: Loop-aware dispatch helper (D-09, D-12)
**What:** One function in a shared module (suggested: `runtime/ccf_runtime/orchestration/_dispatch.py` or `runtime/ccf_runtime/orchestration/common.py` — Claude's discretion) that all three drivers use for any sync-entry coroutine execution.
**Example:**
```python
# Source: stdlib idiom — asyncio.get_running_loop / concurrent.futures
# (docs.python.org/3/library/asyncio-eventloop.html)
import asyncio
from concurrent.futures import ThreadPoolExecutor

def run_coroutine_sync(coro, *, timeout: float | None = None):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)          # plain sync context — today's path
    # A loop is running in this thread: dedicated background thread + own loop.
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout)
```
Typed-error wrapping (raising the driver hierarchy instead of `RuntimeError`/`KeyError`) layers on top per D-10.

**Anti-pattern to avoid:** `loop.run_until_complete` on the detected running loop, or `nest_asyncio` — both are exactly the defect class being removed. Also avoid `asyncio.run_coroutine_threadsafe` against the *caller's* loop — the caller's loop is busy running the caller; you would deadlock joining it from the same thread.

### Pattern 2: Error hierarchy mirroring existing style (D-10)
The codebase's precedent is precise sibling classes with docstrings citing rulings (`SignedBindingRequiredRefused` / `SignedBindingInvalidRefused`, `transport.py:132-157`). Shape:
```python
class WorkflowDriverError(RuntimeError): ...
class SegmentNotExecutedError(WorkflowDriverError, KeyError): ...  # or plain — planner choice
class DriverStateRetrievalError(WorkflowDriverError): ...
```
Note: whether `SegmentNotExecutedError` also subclasses `KeyError` for backward compatibility is a planner micro-decision; existing tests may catch `KeyError` — grep `tests/conformance/test_orchestration.py` during planning. Docstrings cite CLAUDE.md §8.1 / D-IMPL-60 and mark the extension SDK-defined per §11.

### Pattern 3: Mixed-op hammer (D-07)
~16–32 threads (discretion), each thread doing a seeded-random mix of `enqueue`/`dequeue`/`pending`/`submit`/`submissions` across 2–3 tenants; barrier start; bounded per-thread work count (bounds duration to seconds without wall-clock coupling); `thread.join(timeout=…)` with `pytest.fail` on miss (deadlock detection); post-run invariants: every enqueued event either dequeued exactly once or still pending (account by unique `event_key`), no duplicates, submission counts equal per-thread submit tallies, per-tenant order preserved for the single-producer subsets. Run the hammer against an *unconfigured* transport (no D-16 wiring) so verification cost doesn't dominate; a second short case with D-16 wiring confirms no lock-ordering issue against the Control Plane path.

### Pattern 4: Parity test extension (D-13)
`tests/conformance/test_orchestration.py` already parametrizes legs via `build_orchestration_leg` / the `leg` fixture across all three drivers, with skip-vs-required behavior under `CCF_REQUIRE_HARNESSES`. Extend that file (or a sibling using the same fixtures) with: (a) typed-error assertions for unexecuted segments per leg, (b) loop-safety cases invoking each driver's sync introspection both from plain sync and from inside `asyncio.run(...)`-hosted async code. Do not build new fixture infrastructure. [VERIFIED: codebase read]

### Pattern 5: One-time byte-identical check (D-14)
Before any code change lands (first plan): `sha256sum` every expected-output file under `examples/` (identify via existing example verification machinery / `expected*` files — planner confirms the glob) into a committed or plan-artifact manifest. At phase close: recompute and diff; any mismatch is a blocking review event. Plus the standing `make examples` sweep stays green (already in `make ci`). [VERIFIED: Makefile — `ci` = ci-core + examples]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-thread coroutine execution | Custom loop manager / thread-local loop registry | `ThreadPoolExecutor` + `asyncio.run` per call | Lifecycle-free, deadlock-free, three lines |
| Test hang protection | signal-based alarms | Bounded `join(timeout)`/`Future.result(timeout)` + `pytest.fail` | Signals interact badly with threads; bounded joins are deterministic |
| Reentrancy handling | `threading.RLock` | Restructure (private unlocked helpers, lock only at public surface) | D-06 locks this explicitly |

## Ruling-Batch Item Research Seeds (HARD-01, D-03)

Per-item context the planner should route into the mini-cycle document:

1. **WR-01 mapping shape** (per-tenant authorization at HITL doors) — consumed by Phase 10 (HARD-04: deny-by-default, typed 403, authz in audit record, cross-door × cross-action matrix). Options concern where scope enforcement lives (door vs transport vs policy artifact) and how `TokenGrant.scopes` maps to tenant × action. Prior rulings D-IMPL-62/63/67 and T-07-24 residual are the envelope. [VERIFIED: codebase + audit]
2. **ApprovalGate.resolve × D-16 composition** — audit consensus: `resolve` cannot compose with `signed_binding_required` because verification lives on the transport `submit` path (door-only). Adjacent to WR-02's code — D-02's rulings-first ordering exists precisely so the lock work doesn't pre-empt this. [VERIFIED: audit + transport.py read]
3. **Perf governance** — consumed by Phase 11 (PERF-04 already commits to runner-class-keyed baselines + `thresholds.toml` + relative-median gating in opt-in `perf.yml`). Ecosystem data: absolute-time gates on shared runners are flake-by-construction — CodSpeed measured that guaranteeing 1% false-positive on GitHub runners forces a ~7% gate; teams gate on median/min with 10–15% relative thresholds on noisy runners, tightening on dedicated hardware; pytest-benchmark and asv are the standard local tools, asv supports relative continuous benchmarking natively. [MEDIUM: WebSearch, multiple sources — codspeed.io/blog/benchmarks-in-ci-without-noise, bencher.dev pytest-benchmark guide] The ruling scopes what "governance" means (re-baseline ritual authority, threshold ownership, opt-in vs always-on).
4. **Docs toolchain/publishing** — consumed by Phase 14 (DOCS-02 commits mkdocs-material + mkdocstrings; whitepaper never published; repo is private). Options: (a) CI-build-only with the site as an Actions artifact (safest for a private repo; matches DOCS-06's `make docs --strict` always-on CI and REQUIREMENTS' "hosting/publishing decision deferred"); (b) GitHub Pages — note private-repo Pages requires GitHub Enterprise for private visibility, otherwise the site is public [ASSUMED — verify plan tier before presenting]; (c) mike for versioned docs on a gh-pages branch, deferrable until a hosting decision exists. [MEDIUM: WebSearch — squidfunk.github.io/mkdocs-material/publishing-your-site/, setting-up-versioning]
5. **D-10 amendment** — the `make ci` composition ruling (Phase 8 D-10: ci-core + examples) amended so `make docs --strict` joins always-on CI (DOCS-06 names this "logged D-10 amendment"). Note: this is *Phase 8's context decision D-10*, not this phase's CONTEXT D-10 (error hierarchy) — the planner must keep the two namespaces straight in the ruling doc.
6. **create_app warning** — audit consensus: `create_app` defaults unauthenticated (T-07-24 residual) and needs a loud adopter-facing warning on insecure default posture; consumed by Phase 10 (HARD-05). Options concern mechanism (`warnings.warn` category vs startup log vs both) and suppression surface (explicit `insecure_ok=True`-style acknowledgment vs env var).

DECISIONS.md format verified: entries are `**D-IMPL-NN — title.** RESOLVED — option, date, Approver: Dave` with surfacing context, question, and originates line; new numbers, never amendments (new-number-not-amend discipline per D-IMPL-66). Next free numbers appear to be D-IMPL-68+ — planner must confirm the exact next number by reading the log tail.

## Common Pitfalls

### Pitfall 1: Holding the transport lock across Control Plane / crypto calls
**What goes wrong:** Lock held during `resolve_latest` + JWS verification serializes all submissions and creates cross-component lock-ordering risk.
**How to avoid:** Verify first (unlocked), mutate under the lock. A refused submission never touches queues anyway (existing contract: "a refused submission never lands on the queue" — preserved trivially).

### Pitfall 2: Deadlock joining the caller's own loop
**What goes wrong:** Using `run_coroutine_threadsafe(coro, running_loop).result()` from the loop's own thread blocks forever.
**How to avoid:** D-09's dedicated background thread with its *own* loop (`asyncio.run` on the pool thread). Never touch the detected loop.

### Pitfall 3: ADK `InMemorySessionService` cross-loop state
**What goes wrong:** `persisted_state`'s background-thread loop is a *different* loop from the one `start_execution` ran under. If ADK's session service held loop-bound primitives (e.g., `asyncio.Lock` created on the first loop), cross-loop access could raise. `InMemorySessionService` is dict-backed at 2.5.0 per driver usage, but this is unverified against ADK internals. [ASSUMED]
**How to avoid:** Parity test D-13(c) exercises exactly this path (sync-entry from inside a running loop) — the test is the verification.

### Pitfall 4: Expected-output drift from error-message changes
**What goes wrong:** New typed error text or warning output leaking into example stdout would break byte-identity (D-14 blocking event).
**How to avoid:** Take the hash snapshot before any change; run `make examples` per plan, not only at phase close. None of the eight examples should hit unexecuted-segment paths, but verify early.

### Pitfall 5: Ruling-batch scope creep into implementation
**What goes wrong:** Implementing WR-01/create_app/ApprovalGate fixes in Phase 9 — those are Phase 10 requirements (HARD-04/05); Phase 9 only *rules* on them.
**How to avoid:** The mini-cycle document produces rulings and D-GATE-9 entries; only WR-02/03 produce code.

### Pitfall 6: mypy --strict and lint regressions
**What goes wrong:** New shared module under `runtime/ccf_runtime/orchestration/` must survive `mypy --strict`, `tools.lints --all` (harness-import lint, `d06-orchestration-split`, CINV-03 `__ccf_mode__` tagging where applicable). The transport module is tagged `__ccf_mode__ = "algorithmic"` — `threading` import is fine; no LLM/harness import may enter.
**How to avoid:** Run `make ci-core` per task; the shared module imports only stdlib + `ccf`/`ccf_runtime` (no harness SDK — the dispatch helper is harness-free by construction).

## Project Constraints (from CLAUDE.md)

- Phase discipline / §3.1 mini-cycle protocol: review, triage (blocking vs advisory), Dave approval, `D-GATE` entry — applies to the HARD-01 mini-cycle ("Mini-cycles review too").
- No-Hardcoding Rule §6.4 — no new prompts/definitions in code (this phase touches none, but warning text for create_app is a *ruling* topic, not an implementation).
- Harness neutrality §7.3 — zero harness imports in `/src`; the shared driver module lives in `runtime/` (D-12 already conforms); CI import lints must stay green.
- Whitepaper/CLAUDE.md citation in docstrings of touched public classes; SDK extensions marked SDK-defined.
- Surface gaps as D-IMPL entries and stop — do not default any of the six ruling items (REQUIREMENTS "Out of Scope" repeats this).
- `main` is approved-state; phase work on a branch; merge at D-GATE. (Note: `.planning/config.json` has `branching_strategy: "none"` — planner should reconcile with CLAUDE.md §2.2 branch discipline; v0.1 used phase branches.)
- Model mandate: Phase-D-shaped mini-cycle work under Fable 5 high effort; code fixes are Phase-I-shaped (Opus per CLAUDE.md §3) — planner should surface this mixed-mandate wrinkle rather than silently pick.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python + pytest | all tests | ✓ | pytest 9.0.3 | — |
| google-adk, claude-agent-sdk, langgraph | parity tests (CCF_REQUIRE_HARNESSES=1) | ✓ (v0.1 CI green with all three; ADK 2.5.0 referenced in driver) | per lockfile | conformance suite has skip-vs-required machinery |
| pytest-timeout | optional D-07 alternative | ✗ | — | bounded joins + `pytest.fail` (recommended) |
| Makefile targets (`test`, `ci-core`, `ci`, `examples`) | verification | ✓ | — | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (mypy --strict + `tools.lints --all` alongside) |
| Config file | pyproject.toml / Makefile (`make test` = `CCF_REQUIRE_HARNESSES=1 python -m pytest -q`) |
| Quick run command | `python -m pytest tests/hitl tests/conformance/test_orchestration.py -q` |
| Full suite command | `make ci-core` (lint + typecheck + test); phase gate: `make ci` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARD-01 | Rulings logged in DECISIONS.md per format | manual-only (Dave approval is the gate; §3.1) + doc-presence check | `grep -c "D-IMPL-6[89]\|D-IMPL-7" docs/DECISIONS.md` (numbers TBD) | ❌ human gate |
| HARD-02 | No corruption/deadlock under threaded stress; contract in docstring | unit/stress | `python -m pytest tests/hitl/test_transport_concurrency.py -q` (new) | ❌ Wave 0 |
| HARD-03 | Loop-safe sync entry, typed errors, three-driver parity | conformance | `CCF_REQUIRE_HARNESSES=1 python -m pytest tests/conformance/test_orchestration.py -q` | ✅ extend |
| D-14 | Byte-identical expected outputs | integration | pre/post `sha256sum` manifest diff + `make examples` | ❌ Wave 0 (manifest) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/hitl tests/conformance -q` + `make lint typecheck`
- **Per wave merge:** `make ci-core`
- **Phase gate:** `make ci` (includes eight-example sweep) + hash-manifest equality + Dave's D-GATE-9

### Wave 0 Gaps
- [ ] `tests/hitl/test_transport_concurrency.py` — HARD-02 hammer (name per existing tests/hitl conventions)
- [ ] Expected-output hash manifest captured before any code change (D-14)
- [ ] Parity/loop-safety additions to `tests/conformance/test_orchestration.py`

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | ruling-only | create_app warning + WR-01 ruling (implementation is Phase 10) |
| V4 Access Control | ruling-only | WR-01 per-tenant authz mapping shape — deny-by-default is the Phase 10 posture to rule toward |
| V5 Input Validation | yes (existing) | Pydantic `extra=forbid` contracts — unchanged |
| V6 Cryptography | yes (existing) | D-16 JWS verification stays outside the new lock; never hand-rolled — unchanged |
| Concurrency integrity | yes | `threading.Lock` on all queue mutations; no TOCTOU between policy check and append (refusal path never mutates) |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Lost/duplicated HITL events under concurrent doors | Tampering/Repudiation (audit integrity) | Lock + invariant-checked hammer; snapshot-tuple reads |
| Deadlock as availability failure | DoS | Single lock, no nested acquisition (D-06), bounded joins in tests |
| Nested-loop crash masking driver state | DoS/Info | Loop-aware dispatch + typed `DriverStateRetrievalError` instead of raw `RuntimeError` |

## Open Questions

1. **Does `SegmentNotExecutedError` also subclass `KeyError`?** Existing conformance tests may rely on `KeyError`. Recommendation: planner greps test expectations; prefer clean break (parity tests are being rewritten anyway) unless something outside the parity suite catches `KeyError`.
2. **Exact next D-IMPL numbers.** Log tail shows D-IMPL-66+; planner reads `docs/DECISIONS.md` end-to-end to assign the six numbers.
3. **Branching for the mini-cycle.** config.json says `branching_strategy: none` but CLAUDE.md §2.2 mandates phase branches with D-GATE merges. Surface to Dave in the D-GATE-9 presentation if not already settled for v0.2.
4. **Which files count as "expected-output files" for D-14.** Planner enumerates from the examples' verification machinery (e.g., `expected*` fixtures under `examples/`) before snapshotting.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ADK `InMemorySessionService` state is safely readable from a second event loop/thread | Pitfall 3 | Parity test fails → wrap access or snapshot state loop-side; contained |
| A2 | GitHub Pages on a private repo publishes publicly unless on Enterprise | Ruling seed 4 | Wrong option framing in the docs-toolchain ruling — verify before drafting the mini-cycle doc |
| A3 | `pytest-timeout` is the correct PyPI name if the plugin route is chosen | Alternatives | Gated behind checkpoint anyway; recommended route needs no package |

## Sources

### Primary (HIGH confidence)
- Direct codebase reads: `src/ccf/hitl/transport.py`, all three `runtime/ccf_runtime/orchestration/*/driver.py`, `tests/conformance/test_orchestration.py`, `docs/DECISIONS.md`, `.planning/v0.1-MILESTONE-AUDIT.md`, `Makefile`, `.planning/config.json`
- Python stdlib docs (asyncio.run running-loop restriction; threading.Lock semantics)

### Secondary (MEDIUM confidence)
- [Material for MkDocs — Publishing your site](https://squidfunk.github.io/mkdocs-material/publishing-your-site/) and [Setting up versioning (mike)](https://squidfunk.github.io/mkdocs-material/setup/setting-up-versioning/)
- [CodSpeed — Benchmarks in CI without noise](https://codspeed.io/blog/benchmarks-in-ci-without-noise) (7%-gate false-positive analysis on GitHub runners)
- [Bencher — pytest-benchmark guide](https://bencher.dev/learn/benchmarking/python/pytest-benchmark/)

## Metadata

**Confidence breakdown:**
- Defect analysis & fix patterns: HIGH — read directly, stdlib-verified
- Test/CI integration: HIGH — existing infra verified
- Ruling-batch research seeds: MEDIUM — WebSearch-sourced; per-item deep research happens in-plan per D-03

**Research date:** 2026-08-01
**Valid until:** 2026-08-31 (stable domain; stdlib patterns don't move)
