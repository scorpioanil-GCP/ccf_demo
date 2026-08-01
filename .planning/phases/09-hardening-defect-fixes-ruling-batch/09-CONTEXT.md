# Phase 9: Hardening — Defect Fixes & Ruling Batch - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the v0.1 audit's two ruling-free defects — thread-unsafe in-memory HITL
transports (WR-02) and the ADK workflow driver's nested `asyncio.run` /
bare-`KeyError` behavior (WR-03) — and run the six-item D-IMPL ruling batch
(WR-01 mapping shape, ApprovalGate×D-16 composition, perf governance, docs
toolchain/publishing, D-10 amendment, create_app warning) past Dave as one
Phase D mini-cycle, with every ruling logged in `docs/DECISIONS.md`. The
eight-example CI sweep must pass byte-identically (no expected-output
regeneration). Requirements: HARD-01, HARD-02, HARD-03.

</domain>

<decisions>
## Implementation Decisions

### Ruling batch mechanics (HARD-01)
- **D-01:** Presentation is **decision doc + interactive**: one consolidated
  mini-cycle document committed to `docs/` (per item: context, 2–3 options
  with consequences, recommendation), then an interactive walkthrough with
  Dave via AskUserQuestion; each ruling logged to `docs/DECISIONS.md` as it
  lands. §3.1 mini-cycle protocol applies (review, triage, D-GATE entry).
- **D-02:** **Rulings first** — the mini-cycle runs at the start of Phase 9,
  before the WR-02/03 code plans execute. This unblocks Phases 10/11/14
  planning earliest and avoids fixes pre-empting rulings that touch the same
  surfaces (ApprovalGate×D-16 is adjacent to WR-02's HITL code).
- **D-03:** Options analysis is **research-backed**: targeted per-item
  research before drafting (e.g., mkdocs-material publishing options for the
  docs-toolchain item, perf regression-gate practices in comparable SDKs for
  the perf-governance item). Not a research project — research feeds the
  standard D-IMPL options/consequences/recommendation shape.
- **D-04:** Deferral posture is **partial-proceed**: if Dave defers an item,
  it stays an open D-IMPL gating only its downstream phase (e.g., docs
  toolchain gates Phase 14, not Phase 9's fixes). WR-02/03 work proceeds;
  any deferral is flagged explicitly in the D-GATE-9 presentation.

### Concurrency contract shape (HARD-02, WR-02)
- **D-05:** `HITLTransportProtocol` **requires thread-safety of every
  conforming implementation** — the Protocol's docstring states that all
  methods must be safe for concurrent calls from multiple threads (this is
  how FastAPI's threadpool actually hits the doors).
- **D-06:** In-memory reference transports synchronize with plain
  **`threading.Lock`** — matches the sync threadpool access pattern, no
  event-loop entanglement, simple to stress-test. (If a locked method would
  call another locked method, restructure rather than reach for RLock.)
- **D-07:** Stress test is a **mixed-op hammer with invariant checks**:
  ~16–32 threads concurrently submitting, listing, and resolving events
  against one transport for a bounded duration; hard pytest timeout;
  post-run invariant assertions (no lost or duplicated events, no deadlock);
  deterministic seed.
- **D-08:** The concurrency contract is documented **in the Protocol
  docstring only** — the Phase 14 generated API reference picks it up; no
  separate hand-written docs page (avoids drift and pre-empting the docs
  toolchain ruling).

### ADK loop-safety strategy (HARD-03, WR-03)
- **D-09:** **Loop-aware dispatch**: the sync API is preserved. When no
  event loop is running, dispatch via `asyncio.run` as today; when a running
  loop is detected, execute the coroutine on a dedicated background
  thread/loop and join. Callers in plain scripts and async hosts both work.
- **D-10:** Typed errors form a **small dedicated hierarchy**: a driver-error
  base (e.g., `WorkflowDriverError`) with `SegmentNotExecutedError` replacing
  the bare `KeyError`, plus a state-retrieval-failure subclass. Mirrors the
  SDK's existing precise-exception style (cf. the SignedBinding
  Required/Invalid split).
- **D-11:** The loop-safety pattern and error hierarchy apply to **all three
  drivers** (ADK, Claude Agent SDK, LangGraph) as shared mechanism, so
  parity tests assert identical typed behavior and the defect class cannot
  recur per-adapter.
- **D-12:** The shared dispatch helper and error hierarchy live in a
  **common module under `runtime/ccf_runtime/orchestration/`** — out of
  `/src` core (harness-neutrality lint unaffected), one copy for all
  drivers.

### Parity tests & CI-freeze discipline
- **D-13:** Cross-adapter parity tests assert **behavior + typed errors**:
  the same workflow definition through each driver yields (a) equivalent
  persisted state/replay records, (b) identical typed errors for unexecuted
  segments, and (c) loop-safety — each driver exercised from both a plain
  sync context and inside a running event loop.
- **D-14:** Byte-identical examples guarantee enforced by the **existing
  eight-example sweep plus a one-time pre/post hash check** for Phase 9:
  hash expected-output files before and after the phase's changes and assert
  equality. Any diff is a blocking review event. No permanent standing hash
  gate (Phase 13 owns ongoing reviewed-change discipline).
- **D-15:** Stress and parity tests join the **normal `/tests` suite, always
  on** in every CI pass — hammer duration bounded to seconds so CI doesn't
  bloat. No slow/nightly tagging.

### Claude's Discretion
- Exact thread count/duration of the hammer test within the ~16–32 /
  seconds-bounded envelope.
- Exact names and module layout of the shared driver-error hierarchy and
  dispatch helper, matching existing runtime orchestration conventions.
- Ordering of the six items within the ruling-batch document.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project authority
- `CLAUDE.md` — canonical authority (rev 4); §3.1 mini-cycle/review protocol, §6.4 No-Hardcoding, §7.3 harness neutrality, §8.2 HITL primitives
- `docs/DECISIONS.md` — the decision log the six rulings land in; existing D-IMPL entry format to follow
- `docs/CCF_Whitepaper_1-2.md` — canonical spec (cite sections in any touched docstrings)

### v0.1 audit and defect provenance
- `.planning/v0.1-MILESTONE-AUDIT.md` — WR-01/02/03 definitions and tech-debt intake list
- `.planning/phases-archive/` (v0.1) `08-REVIEW.md` if present — original code-review findings for WR-01/02/03

### Milestone scope
- `.planning/REQUIREMENTS.md` — HARD-01..03 texts; "Out of Scope" (no defaulting ruling items)
- `.planning/ROADMAP.md` — Phase 9 success criteria incl. WR-03-before/with-WR-02 ordering and byte-identical sweep criterion

### Defect sites
- `src/ccf/hitl/transport.py` — `HITLTransportProtocol`, `InMemoryHitlTransport`, `PendingHitlEvent` (WR-02 target)
- `runtime/ccf_runtime/orchestration/adk/driver.py` — `AdkWorkflowDriver.persisted_state` `asyncio.run` at ~line 281 (WR-03 target)
- `runtime/ccf_runtime/orchestration/` — the other two drivers (Claude Agent SDK, LangGraph) for the shared pattern (D-11/D-12)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Typed-refusal exception style already established (`SignedBindingRequiredRefused` / `SignedBindingInvalidRefused` in `src/ccf/hitl/transport.py`) — model for the new driver error hierarchy.
- Existing cross-adapter test infrastructure from v0.1 (three harness adapters shipped with parity assertions in example 03) — extend rather than reinvent for D-13.
- `tools.lints --all` and the harness-import lint — the shared driver module placement (D-12) must keep these green.

### Established Patterns
- Protocol docstrings carry contracts and are citation-bearing (Phase 14 will generate the API reference from them) — the concurrency contract (D-08) rides this.
- D-IMPL entries in `docs/DECISIONS.md` have an established shape (question, options, consequences, ruling, date) — the ruling-batch doc mirrors it.
- Mini-cycles follow the full §3.1 protocol scoped to the revisited decisions: review, triage, Dave approval, D-GATE entry.

### Integration Points
- HITL doors (HTTP in `runtime/`, MCP in `runtime/ccf_runtime/mcp/hitl_server.py`) invoke transports from FastAPI's threadpool — the concurrency reality the stress test must model.
- Phase 10 consumes three of the six rulings (WR-01 mapping shape, ApprovalGate×D-16, create_app warning); Phase 11 consumes perf governance; Phase 14 consumes docs toolchain + D-10 amendment.

</code_context>

<specifics>
## Specific Ideas

- The ruling batch is a single consolidated event, not six drip-fed asks — one document, one interactive session, one D-GATE presentation.
- Research-backed options for the rulings: Dave wants current ecosystem data (docs publishing, perf-gate practices) informing the recommendations, not just first-principles options.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 9-Hardening — Defect Fixes & Ruling Batch*
*Context gathered: 2026-08-01*
