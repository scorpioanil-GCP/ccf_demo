# Phase 9: Hardening — Defect Fixes & Ruling Batch - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-01
**Phase:** 9-Hardening — Defect Fixes & Ruling Batch
**Areas discussed:** Ruling batch mechanics, Concurrency contract shape, ADK loop-safety strategy, Parity test & CI-freeze discipline

---

## Ruling batch mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Decision doc + interactive | Consolidated mini-cycle doc in docs/ plus interactive walkthrough, rulings logged to DECISIONS.md | ✓ |
| Doc only | Doc produced; Dave rules asynchronously | |
| Interactive only | AskUserQuestion session, no standing artifact | |

| Option | Description | Selected |
|--------|-------------|----------|
| Rulings first | Mini-cycle at start of Phase 9 before code plans | ✓ |
| Parallel | Fixes start while doc is drafted | |
| Fixes first | Ruling batch as phase's closing act | |

| Option | Description | Selected |
|--------|-------------|----------|
| Standard D-IMPL depth | Options/consequences/recommendation per item | |
| Research-backed | Targeted per-item research before drafting | ✓ |
| Minimal | One-liner + recommendation per item | |

| Option | Description | Selected |
|--------|-------------|----------|
| Partial-proceed | Deferred items gate only downstream phases; WR fixes proceed | ✓ |
| Hard stop | Phase 9 incomplete until all six rulings logged | |
| You decide | Per-item posture by what it gates | |

---

## Concurrency contract shape

| Option | Description | Selected |
|--------|-------------|----------|
| Protocol requires thread-safety | All conforming transports must be thread-safe | ✓ |
| Refs safe, contract advisory | Only shipped refs synchronized | |
| Caller-side serialization | Serializing shim at the door | |

| Option | Description | Selected |
|--------|-------------|----------|
| threading.Lock | Plain mutex, matches threadpool access | ✓ |
| threading.RLock | Re-entrant variant | |
| asyncio-aware hybrid | Async lock + thread bridge | |

| Option | Description | Selected |
|--------|-------------|----------|
| Mixed-op hammer w/ invariant checks | 16–32 threads, bounded, timeout, invariant assertions | ✓ |
| Targeted race repro | Barrier-orchestrated WR-02 interleavings | |
| Both | Hammer + barrier repro | |

| Option | Description | Selected |
|--------|-------------|----------|
| Protocol docstring only | Single source, picked up by generated reference | ✓ |
| Docstring + docs page | Adds hand-written note | |
| You decide | | |

---

## ADK loop-safety strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Loop-aware dispatch | Sync API kept; background thread/loop when a loop is running | ✓ |
| Async-first + sync wrapper | persisted_state natively async | |
| Detect and raise | Typed error inside running loop | |

| Option | Description | Selected |
|--------|-------------|----------|
| Small dedicated hierarchy | WorkflowDriverError base + SegmentNotExecutedError etc. | ✓ |
| Reuse existing SDK errors | Map onto existing orchestration exceptions | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| All three drivers | Shared mechanism; parity asserts identical typed behavior | ✓ |
| ADK only, others audited | Fix ADK; audit others | |
| ADK only | Strictly WR-03 | |

| Option | Description | Selected |
|--------|-------------|----------|
| runtime orchestration common | Shared module under runtime/ccf_runtime/orchestration/ | ✓ |
| src/ccf/orchestration | Error types in /src public surface | |
| You decide | | |

---

## Parity test & CI-freeze discipline

| Option | Description | Selected |
|--------|-------------|----------|
| Behavior + typed errors | State equivalence + identical typed errors + loop-safety both contexts | ✓ |
| Loop-safety only | Narrow to WR-03 | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Existing sweep + pre/post hash check | One-time Phase 9 hash verification of expected outputs | ✓ |
| Existing sweep only | Trust current comparisons | |
| Permanent hash gate | Standing CI manifest job | |

| Option | Description | Selected |
|--------|-------------|----------|
| Normal suite, always on | Stress + parity in every CI pass, bounded duration | ✓ |
| Marked slow, nightly | Scheduled job only | |
| You decide | | |

## Claude's Discretion

- Hammer test exact thread count/duration within the agreed envelope
- Naming/module layout of the shared driver-error hierarchy and dispatch helper
- Ordering of the six items within the ruling-batch document

## Deferred Ideas

None — discussion stayed within phase scope.
