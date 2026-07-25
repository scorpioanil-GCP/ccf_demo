---
phase: 04-phase-i-1-fabric-core
plan: 08
subsystem: replay-engine-artifact-conformance
tags: [replay, artifact-store, conformance, snapshots, cinv-04, d-impl-06, d-impl-26, d-impl-44]
requires:
  - 04-03 (CCFContract, canonical_bytes/content_hash)
  - 04-04 (GraphReader/SQLite backend, boot composition root, single-writer boot check)
  - 04-05 (five-dimension replay record, serve path, ArtifactStore Protocol + file store, operators, projection engine, product gates)
provides:
  - ArtifactStore conformance suite, parametrized over a store factory — the acceptance bar the I.3 MCP store implements against
  - typed store errors (ArtifactNotFound, ArtifactUriUnresolvable, MovingTargetRefused) and a shared versioned-URI parser that refuses @latest
  - durable, append-only naming index on the file store, so a versioned URI resolves against a process that never stored it
  - replay engine: exact-address record resolution, exact-version binding resolution, re-execution, step/snapshot/product verification
  - SnapshotReader — a GraphReader pinned to the recorded tenant and boundary (D-IMPL-06 logical snapshot)
  - ReplayEnvironment seam for deployment Π, operators, and product envelope, verified rather than trusted
  - CINV-04 harness with an active/deferred check registry
affects:
  - the I.3 MCP-backed ArtifactStore adds a param to the conformance fixture and changes no test body
  - I.2 (agent version, skill-set) and I.4 (HITL, workflow) flip their CINV-04 registry entries from deferred to active and add their owning tests
  - any consumer of GraphReader.as_of now receives supersession and lineage rendered as of the boundary rather than as of today
tech-stack:
  added: []
  patterns:
    - unresolvable is refused with a typed error and divergence is raised, never returned — a replay caller that could receive divergence as a value could log it and proceed with the freshly-computed product
    - the deployment seam is verified, not trusted: a wrong plan produces a step mismatch, wrong parameters a parameter-hash mismatch, a wrong envelope a content-address mismatch
    - deferred invariant checks are emitted as skips carrying their activating phase, so "suite green" cannot be misread as "invariant holds"
key-files:
  created:
    - src/ccf/replay/engine.py
    - src/ccf/replay/snapshots.py
    - tests/conformance/test_artifactstore.py
    - tests/replay/test_engine_rehydration.py
    - tests/invariants/test_replay_by_construction.py
  modified:
    - src/ccf/artifacts/protocol.py
    - src/ccf/artifacts/file_store.py
    - src/ccf/graph/backends/sqlite.py
    - tests/replay/test_serve_writes_replay.py
    - tests/integration/test_proto_quickstart.py
decisions:
  - "The as-of read renders supersession and lineage *as of the boundary*. A claim still current at the boundary was carrying a pointer to the claim that replaced it four months later, and lineage entries the fabric had not yet received. Both are future information, both changed the content hash of a view that must be identical to the one the decision saw, and together they made every replay after any subsequent write diverge for reasons having nothing to do with the decision. INV-CH7-14 is explicit that claims superseded later are still current; 'current' has to mean current."
  - "Divergence is raised; refusal at L6 is returned. The gates return refusals as data because a caller there holds a candidate it may legitimately discard. A replay has no such option — a decision that does not reproduce is a finding, and a caller that received it as a value could log it and carry on holding the freshly-computed product, which is the substitution the engine exists to prevent."
  - "ReplayEnvironment is a seam because the SDK cannot know a deployment's Π, operator parameters, or product envelope — they are user code and user configuration. It is a *verified* seam: three independent checks (step sequence, snapshot id, product content address) catch a wrong answer from it, so replay does not become 'ask the deployment what it thinks happened'."
  - "URI registration is a side effect of put rather than a separate register_uri. A standalone registration call permits a name that points at content the store does not hold, which is a dangling reference in a replay record — the one artifact class that must never dangle."
  - "@latest is refused in the shared URI parser rather than in each store. The URI is a string, so 'latest' can always be written into it; putting the refusal in the parser means every implementation of the Protocol refuses it identically rather than each remembering to."
  - "The naming index lives on the substrate beside the artifacts, not in the store object's memory. A versioned URI written into a record must resolve years later against a process that never stored anything; an in-memory index would make the URI useful only to its writer."
  - "The CINV-04 registry names each active check's owning test and verifies the reference resolves, rather than restating the assertion. Two copies of one check can disagree; a pointer that stops resolving is caught by the harness itself."
metrics:
  duration: ~45 min
  completed: 2026-07-25
  tasks: 3
  commits: 5
---

# Phase 4 Plan 08: Replay Engine, ArtifactStore Conformance, CINV-04 Harness Summary

"Replay resolves exact artifact versions, never latest" is now a passing named
test, and a decision served in March reproduces byte-for-byte in July after the
entities it read have been superseded.

## What Was Built

**Task 1 — the ArtifactStore acceptance bar** (`30c9ee4` RED, `0b9f5c5` GREEN).
Eighteen conformance tests parametrized over a store factory, asserting content
addressing, byte round-trip, immutability, the absence of any mutation or
graph-write surface, versioned-URI naming, and — the one the plan exists for —
that `@latest` is *refused with a typed error* rather than answered. The refusal
is a refusal, not an absence: it is not enough that the Protocol lacks a
`resolve_latest`, because the URI is a string and a caller can always write
`latest` into it. `parse_artifact_uri` is where that string stops.

The file store gained what the suite demanded: `ArtifactNotFound`,
`ArtifactUriUnresolvable`, and `MovingTargetRefused`; `resolve_uri` backed by an
append-only naming index persisted beside the artifacts; and `versions()` for
introspection that returns the whole history rather than a way to reach the
newest one. Registration happens inside `put`, so a name cannot point at content
the store does not hold.

**Task 2 — the replay engine** (`54b2703` RED, `19e913a` GREEN). Six steps,
each with its failure mode named: resolve the record at its content address and
re-hash the returned bytes; resolve every Control Plane binding at its pinned
version; resolve the plan and operators through the deployment environment;
re-execute against a boundary-pinned `SnapshotReader`; compare the executed step
sequence — keys, categories, *and parameter hashes*, in order — against the
recorded one; compare the derived snapshot id; compare the rehydrated product's
content address. `ReplayOutcome` is constructible only after all of it, so a
caller cannot receive a "probably" and read it as a "yes".

`snapshots.py` carries D-IMPL-06 literally. There is no physical copy anywhere:
the snapshot is a tenant, a boundary, a watermark, and a manifest, and the
`SnapshotReader` delegates to the live reader while refusing every read outside
that scope. A projection that reached past the boundary fails loudly rather than
importing the future.

**Task 3 — the CINV-04 harness** (`45bf078`). A declarative registry of all five
replay-by-construction paths CLAUDE.md names. Three are active and point at the
tests that assert them; three are emitted as pytest skips carrying the phase
that activates them (HITL capture and workflow-trace capture in I.4, skill-set
capture in I.2). The point is the reporting: a suite asserting only what exists
would pass, and "CINV-04: green" would then read identically to "the invariant
holds". `pytest -rs` now prints three named invariants awaiting their pillar.

## Key Implementation Details

- **The load-bearing test is the one that mutates the graph first.** Replaying
  against an unchanged graph is a determinism check the operator suite already
  makes. `test_the_product_replays_exactly_after_the_graph_has_moved_on` renames
  the counterparty and adds a facility four months later, then replays the March
  decision and asserts the March name in the reproduced payload.
- **Parameter drift is divergence, not a different answer.** Re-running with a
  changed traversal depth produces a different `parameter_hash`, so the step
  sequence no longer matches and the engine says so. That distinction —
  reporting rather than returning the freshly-computed product — is the whole
  difference between replay and re-computation.
- **Nothing on the replay path reads a clock or resolves "latest",** and a test
  asserts the latter against the module source rather than against habit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The as-of read leaked future information into historical views**

- **Found during:** Task 2, the moment the first post-serve mutation test ran
- **Issue:** `GraphView` records rendered by `SqliteGraphStore.as_of` carried
  `superseded_by` / `superseded_at` from *after* the read boundary, and their
  lineage included entries the fabric had not yet received at that boundary. The
  SQL row filter was correct — a claim superseded later stays in the view — but
  the rendering was not. INV-CH7-14 says such a claim is *still current*, and a
  claim pointing at its own future replacement is not current. The consequence
  was exact and fatal to the plan's objective: the content hash of the March
  view changed the instant anything was written in July, so `state_watermark()`
  moved, the derived snapshot id moved, and every replay of every decision
  diverged after any subsequent write.
- **Fix:** `as_of` now renders the supersession edge and the lineage set as of
  the read boundary; history reads are unchanged, because a history *is* the
  whole chain. `test_the_as_of_view_is_byte_identical_after_the_graph_moves_on`
  pins it on bytes.
- **Files modified:** `src/ccf/graph/backends/sqlite.py` (not in the plan's
  `files_modified`; the alternative was compensating inside the replay engine,
  which would have left the graph's own as-of contract wrong for every other
  reader and hidden the defect behind replay-specific code)
- **Commit:** `19e913a`

**2. [Rule 3 - Blocking] Two existing tests counted files rather than artifacts**

- **Found during:** Task 1
- **Issue:** `test_identical_content_yields_one_immutable_artifact` and
  `test_serving_twice_converges_on_one_immutable_record` asserted
  `len(list(root.iterdir())) == 1`, which the new naming index broke.
- **Fix:** both now count content-addressed artifacts and ignore the
  dot-prefixed index file (a leading dot cannot collide with a content address,
  which is hexadecimal). The property under test — one artifact, not two — is
  unchanged.
- **Files modified:** `tests/replay/test_serve_writes_replay.py`,
  `tests/integration/test_proto_quickstart.py`
- **Commit:** `0b9f5c5`

### Interpretations

- **`register_uri` is not a separate call.** The plan's behavior list names
  `register_uri(uri, address)` alongside `resolve_uri`. Registration is
  performed by `put`, which already holds the tenant, class, and name; a
  standalone registration call would permit a name pointing at content the store
  does not hold, and a dangling reference in a replay record is the one dangling
  reference the fabric cannot tolerate. `resolve_uri(uri=...)` is the resolution
  half, exactly as specified.
- **`grep -ric "mcp" src/ccf/artifacts/` is 1 in two files, not 0.** Both hits
  are the 04-05 docstring prose stating that the MCP-backed store is Phase 6 and
  is *deliberately not scaffolded* (D-12). The acceptance criterion's subject is
  MCP scaffolding, and removing the sentences that record the deferral would
  make the deferral less legible, not the code more compliant. No MCP import,
  module, class, or dependency exists under `src/ccf/artifacts/`.
- **`resolve_operators` receives the recorded operator keys, not parameter
  hashes.** The plan's `read_first` sketches a parameter-hash argument. The keys
  are what a deployment resolves against; the hashes are what the engine
  *verifies*, and passing them in would invite an environment to reconstruct
  parameters until the hash matched — turning the check into a search.
- **The replay test rig is self-contained rather than reusing the
  proto-quickstart's banking fixtures.** `tests/` is not an importable package,
  and duplicating the fixture-loading rig would have coupled the replay suite to
  the integration suite's YAML. The rig here is a two-operator plan over four
  ingested attributes — smaller, and it exercises the same engine surface.

## Verification

| Check | Result |
|---|---|
| `.venv/bin/pytest tests -q` | 151 passed, 3 skipped |
| `.venv/bin/pytest tests/conformance/test_artifactstore.py -q` | 18 passed |
| `.venv/bin/pytest tests/replay -q` | 25 passed |
| `.venv/bin/pytest tests/invariants -q -rs \| grep -i not-yet-applicable` | 3 lines, each naming its phase |
| `.venv/bin/mypy --strict src` | Success, 38 source files |
| `.venv/bin/python -m tools.lints --all` | exit 0, zero allowlist entries added |
| `grep -rn "latest" src/ccf/replay/` | one docstring line stating that nothing here resolves it |
| `grep -rn "resolve_latest" src/ccf/replay/` | no output (asserted by a test) |
| Writer imported by any file added in this plan | none — CINV-02 green |
| Post-commit deletion check, all 5 commits | no deletions |
| STATE.md / ROADMAP.md modified | no |

## Known Stubs

None. Two bounded-scope items, both named in the plan:

- The MCP-backed ArtifactStore is Phase 6 per D-12 and is deliberately not
  scaffolded. The conformance suite's `store_factory` fixture takes its param
  and no test body changes.
- Three CINV-04 checks are deferred, and the harness reports them as such
  rather than passing over them.

## Deferred Issues

None. No auto-fix attempt limit was reached; both auto-fixes landed on the
first attempt with the full suite green afterwards.

## Threat Flags

None new. The three registered threats are mitigated as planned: T-04-17
(artifact tampering) by content addressing, write-once semantics, and the
re-hash of returned bytes on the replay path — a substrate that returns the
wrong artifact is caught, not believed; T-04-18 (repudiation of decision
provenance) by hash-verified re-hydration and the typed never-latest refusals;
T-04-19 (store as second writer) by the absence of any graph-write surface,
asserted at runtime by the conformance suite in addition to the CINV-02 import
lint.

## Self-Check: PASSED

All five created files exist on disk; all five commit hashes (`30c9ee4`,
`0b9f5c5`, `54b2703`, `19e913a`, `45bf078`) are present in `git log`.
