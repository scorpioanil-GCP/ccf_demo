---
phase: 04-phase-i-1-fabric-core
plan: 09
subsystem: cdc-ingress
tags: [l1-signal, ingress, pattern-1, runtime, async]
requires:
  - 04-03 (SignalEnvelope, SignalSourceProtocol, ControlPlaneRegistry)
  - 04-05 (AssemblyWorker, boot, SQLite graph store)
provides:
  - CDCSourceAdapter — the v0 reference L1 ingress (Pattern 1), async, ccf-runtime
  - Debezium-style change-event → SignalEnvelope mapping with typed rejection
  - the FABR-09 validation row (tests/integration/test_cdc_slice.py)
affects:
  - later ingress adapters (MCP-source, semantic-layer import) inherit this shape —
    config-supplied tenancy and source identity, deterministic envelope ids,
    typed rejection, no graph handle
  - proves the L1→L2 seam end to end, so the examples suite has a working ingress
tech-stack:
  added: []
  patterns:
    - change semantics carried as a deployment-named payload key, so L2 needs no
      knowledge of CDC and the SDK holds neither the key nor its meaning
    - deterministic envelope_id as content_hash(source coordinates + commit ts +
      op + row image) — replay collapses instead of manufacturing history
    - injected ingestion clock, so a replayed feed produces identical envelopes
key-files:
  created:
    - runtime/ccf_runtime/cdc/__init__.py
    - runtime/ccf_runtime/cdc/envelope_map.py
    - runtime/ccf_runtime/cdc/adapter.py
    - tests/integration/test_cdc_slice.py
    - tests/fixtures/banking/cdc_events.jsonl
  modified: []
decisions:
  - "A delete is a *tombstone claim*, not a graph operation. The change op travels
    into raw_payload under a deployment-named key (change_op_key) which the
    deployment declares as an attribute in its resolution spec. A `u` therefore
    produces a claim whose content differs from its predecessor and supersedes it;
    a `d` produces a terminal claim that supersedes the last live one. L2 needed
    no CDC-awareness and no code change, and no row is ever deleted (INV-CH7-04)."
  - "The adapter depends on no CDC transport. Kafka/Debezium/replication slots are
    deployment infrastructure per DESIGN.md §2A.4.1; the reference feed is a JSONL
    file or an in-memory line sequence, and a deployment binds its own consumer."
  - "The ingestion clock is an injected seam defaulting to the UTC wall clock
    (the ControlPlaneRegistry precedent). Without it, replay idempotence is
    untestable: lineage entries carry observed_at, so a wall-clock adapter would
    accumulate new lineage on every re-delivery of the same envelope."
  - "envelope_id hashes the row image with values stringified, matching what entity
    resolution does with attributes and keeping floats out of the canonical hash."
  - "change_op_key colliding with a real source column is a refusal, not a merge —
    silently shadowing source data would corrupt the payload the graph is built from."
metrics:
  duration: ~20 min
  completed: 2026-07-25
  tasks: 2
  commits: 2
---

# Phase 4 Plan 09: CDC→G Reference Ingress Summary

Pattern 1 lands end to end: a file-fed Debezium-style change stream normalizes
into `SignalEnvelope`s in `ccf-runtime` and reaches the graph exclusively
through the L2 `AssemblyWorker`, with create, update and delete each producing
the right append-only graph event and a re-run of the same feed producing
nothing at all.

## What Was Built

**Task 1 — `envelope_map.py`** (`6bcda7f`). Pure synchronous mapping from a
Debezium-style record to an envelope. `ChangeEvent` / `ChangeSource` validate
the wire format at what is genuinely the fabric's outermost trust boundary, so
the inherited `extra=forbid` is doing real work: an unrecognized field means
the adapter and the connector disagree about the format, and that is a stop,
not a shrug. Anything unparseable, unknown-op, or missing its required row
image raises `CDCMappingError` — the alternative, skipping the record, is a
graph that is quietly wrong, which is strictly worse than a stream that halts.
`tenant_id` and `system_id` are keyword arguments from adapter configuration
and are never read from the event body (T-04-20). `envelope_id` is the content
hash of source coordinates, commit timestamp, operation and row image, so a
re-delivered change is recognizably the same signal and collapses under
idempotent upsert and lineage set-union.

The load-bearing design choice is how change semantics reach L2 **without L2
knowing what CDC is**: the operation is written into `raw_payload` under a key
the deployment names, and the deployment declares that key as an attribute in
its entity-resolution spec. An update then differs in claim content from its
predecessor and supersedes it; a delete produces a terminal tombstone claim
that supersedes the last live one. No graph DELETE exists anywhere in the path,
and `src/` gained not a line.

**Task 2 — `adapter.py` and the slice test** (`1086339`). `CDCSourceAdapter`
implements `SignalSourceProtocol` as an async generator over a JSONL file or an
in-memory line sequence; file reads go through `asyncio.to_thread` because
blocking the loop in an ingestion adapter is how one slow source stalls every
other one. Exactly one feed must be given — neither and both are refusals, not
guesses (D-IMPL-38). The adapter holds no graph handle, and the test asserts
that structurally rather than trusting the docstring.

The slice test boots a real fabric through the composition root, drains the
adapter with `asyncio.run`, feeds every envelope to `worker.ingest`, and
asserts: creates become readable claims; the update appends a superseding claim
with the prior one still readable *as-of the earlier instant*; the delete
appends a tombstone and history grows from one row to two rather than shrinking
to zero; and a second pass over the same file leaves entity history
byte-identical.

## Key Implementation Details

- Ingestion time is an injected clock. The test's `_StepClock` advances by a
  fixed step from a fixed base, which is the only way to get both properties
  the assertions need at once: ingestion time must *advance* or an as-of read
  cannot distinguish pre- from post-update state, and it must be *reproducible*
  or the replay-is-a-no-op assertion cannot hold, since lineage entries carry
  `observed_at`.
- Every domain value lives in `tests/fixtures/banking/` — the CDC feed itself
  plus the existing `ontology.yaml`, which the test reuses with the change-op
  key appended to each rule's attributes. `grep -ril counterparty runtime/`
  is empty.

## Deviations from Plan

**1. [Rule 3 — Blocking] The slice test boots its own fabric instead of using
the `fabric_boot` fixture**
- **Found during:** Task 2
- **Issue:** The plan's read-first list points at `tests/conftest.py`'s
  `fabric_boot`, but that factory pins a fixed resolution spec with no seam for
  supplying another. The CDC slice needs the change-op key declared as an
  attribute, or a delete is indistinguishable from a re-delivery and the
  terminal-supersession assertion cannot exist.
- **Fix:** The test boots through the same real composition root (`ccf.boot`)
  with its own registry and a spec derived from `tests/fixtures/banking/
  ontology.yaml`. No test-only writer and no fake store is introduced — the
  conftest discipline is preserved, only the spec is parameterized. Editing
  `conftest.py` was rejected deliberately: it is shared with concurrently
  executing wave-5 plans.
- **Files modified:** `tests/integration/test_cdc_slice.py` (no conftest change)
- **Commit:** `1086339`

**2. [Rule 2 — Missing critical functionality] Collision guard on
`change_op_key`**
- **Found during:** Task 1
- **Issue:** Writing the operation into the payload under a configured key
  would silently overwrite a source column of the same name, corrupting the
  row image the graph is built from — a data-integrity defect no test would
  notice until a claim was wrong.
- **Fix:** `to_envelope` raises `CDCMappingError` when the key collides with a
  column of the row image, with a test covering it.
- **Files modified:** `runtime/ccf_runtime/cdc/envelope_map.py`
- **Commit:** `6bcda7f`

## Verification

| Check | Result |
|---|---|
| `pytest tests/integration/test_cdc_slice.py -q` | 14 passed |
| `pytest tests -q` (whole suite) | 129 passed |
| `python -m tools.lints --all` | clean (exit 0) |
| `mypy --strict src runtime` | Success: no issues in 40 source files |
| `grep -c "async def" runtime/ccf_runtime/cdc/adapter.py` | 2 (≥ 1) |
| `grep -rc "async def" src/ccf/` | 0 — the fabric core stays sync |
| `grep -rc "_writer" runtime/` | 0 — no writer reachable from ingress |
| `grep -ril counterparty runtime/` | empty — no domain values in runtime |

## Known Stubs

None. The adapter's file/line feed is the *reference* transport per DESIGN.md
§2A.4.1, not a placeholder for a Kafka client the SDK owes anyone — the CDC
transport is deployment infrastructure by ruling.

## Threat Flags

None beyond the plan's register, all three of which are mitigated as planned:
T-04-20 (tenant from adapter config, keyword-only, asserted in the test),
T-04-21 (Pydantic validation → typed `CDCMappingError`, four malformed-input
cases plus a bad-line case asserted), T-04-22 (the adapter has no writer; the
test asserts no reader or writer attribute exists on it, and `grep -rc
"_writer" runtime/` is 0).

## Self-Check: PASSED

All five created files exist on disk; both commits (`6bcda7f`, `1086339`) are
present in `git log`. `STATE.md` and `ROADMAP.md` were not touched.
