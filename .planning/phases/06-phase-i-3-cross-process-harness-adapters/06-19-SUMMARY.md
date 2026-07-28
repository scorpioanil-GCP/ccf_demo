---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 19
subsystem: a2a-admission, replay-resolution, artifact-persistence
tags: [gap-closure, D-IMPL-58, D-IMPL-59, D-IMPL-26, D-IMPL-27, lineage-continuity]
requires:
  - ccf.artifacts.protocol.ArtifactStoreProtocol (put/get/exists/resolve_uri, D-IMPL-26)
  - ccf.contracts.canonical.content_hash (content addressing)
  - ccf.a2a.admission.union_lineage (the D-14 set-union law)
  - ccf.controlplane.audit.AuditLog.append (scalar verdicts, unchanged)
provides:
  - ccf.a2a.admission.AdmissionRecord
  - ccf.a2a.admission.ADMISSION_RECORD (class_id "ccf.admission-record")
  - ccf.a2a.admission.AdmissionNotRecorded
  - A2AAdmissionGate(artifact_store=...) — the injected persistence seam
  - ccf.replay.engine.resolve_artifact
  - ccf.replay.engine.resolve_artifact_at_uri
affects:
  - ROADMAP criterion 2 and docs/PHASE_I3_GATE.md row 14 (D-IMPL-58 closure item 6 — 06-22, not this plan)
tech-stack:
  added: []
  patterns:
    - persistence-before-report (the record is written before the crossing is reported admitted)
    - reference-triple-in-the-verdict (audit points at the artifact; no new audit shape)
    - contract-parametrized replay resolution instead of a per-class resolver
key-files:
  created:
    - tests/a2a/test_admission_record.py
  modified:
    - src/ccf/a2a/admission.py
    - src/ccf/replay/engine.py
    - tests/a2a/test_admission.py
    - tests/a2a/test_admission_attributability.py
    - tests/crossproc/test_a2a_exchange.py
decisions:
  - "D-IMPL-58 reading (d) realized: the merged lineage persists as an immutable AdmissionRecord at the Peering boundary, not in graph state"
  - "AdmissionRecord lives beside InboundPayloadCeiling in a2a/admission.py — controlplane/artifacts.py cannot import ProductLineage without a circular import"
  - "A store outage raises rather than refusing: an outage is a broken deployment, not a federation dispute"
  - "The replay read path is parametrized by contract rather than duplicated per artifact class, so no federation special case enters the replay engine"
metrics:
  duration: ~70m
  completed: 2026-07-27
  tasks: 3
  files: 6
---

# Phase 06 Plan 19: The AdmissionRecord (B2 Closure) Summary

The merged federated lineage now persists at the boundary crossing as an
immutable `ccf.admission-record` artifact, resolvable through the replay path at
the exact version the audit triple names — so lineage continuity is a property of
something that is read, rather than of a wrapper L2 discards.

## Verification ran against THIS worktree

Required by the orchestrator, and confirmed before any result was trusted:

```
PYTHONPATH=src /home/parkave/ccf_code/.venv/bin/python -c "import ccf; print(ccf.__file__)"
/home/parkave/ccf_code/.claude/worktrees/agent-acdffeb044a8fae11/src/ccf/__init__.py
```

Every `pytest` / `mypy` / `tools.lints` invocation in this plan was run with the
`PYTHONPATH=src` prefix against that interpreter. No `.venv` was created or
symlinked inside the worktree.

## What Was Built

**Task 1 — the artifact class** (commits `cb80b33` RED, `466f309` GREEN).
`AdmissionRecord` is a `CCFContract` carrying tenant, peer, the admitted
product's content address, the **producer**, **consumer** and **merged**
lineages, and the admission instant. Producer and consumer are carried alongside
the merge because a union that cannot be decomposed cannot be audited.
`ADMISSION_RECORD` registers `class_id="ccf.admission-record"` — the
dot-namespaced kebab-case form D-IMPL-58's 2026-07-27 amendment ruled, pinned by
a test rather than left to review precisely because the amendment records that a
non-conforming literal was one plan-execution away from landing with the decision
log's authority behind it. The docstring cites D-IMPL-58 for why the record
exists, D-IMPL-27 for why it is an ArtifactStore artifact rather than Control
Plane state, and states in full what the audit log does and does not carry.

No `semver` field: `AdmissionRecord` follows `DecisionReplayRecord`, not
`InboundPayloadCeiling`. It is a **record of an event**, not configuration —
there is nothing about a crossing that already happened to version forward, and
content addressing supplies its identity.

**Task 2 — admission persists the record** (commits `dc71c66` RED, `77ef83d`
GREEN). `A2AAdmissionGate.__init__` takes an injected `ArtifactStoreProtocol`;
`_persist_admission_record` writes at the point the union is computed, **before
`AdmittedProduct` is constructed**, which is the ordering T-06-100 turns on. The
existing `a2a_admitted` append now carries the `ArtifactRef`'s
`artifact_class`/`key`/`version` triple. `audit.py` is untouched: no new
`AuditAction` member, no new `AuditEvent` field. A store outage raises
`AdmissionNotRecorded` rather than admitting silently.

**Task 3 — the replay resolution path** (commits `713efde` RED, `0bb79d2` GREEN).
Rather than adding a federation-shaped resolver, `_resolve_record`'s discipline
was **generalized**: `resolve_artifact` and `resolve_artifact_at_uri` are the
replay plane's read path, parametrized by contract. `ccf.admission-record`
resolves by class exactly as any other artifact does, which is what the plan's
"without special-casing federation inside the replay engine" instruction asked
for. `_resolve_record` now delegates, so exact-version resolution, no-fallback,
re-hash-on-arrival and the `@latest` refusal are stated once instead of twice.

## Closure item 6 — the sentence for 06-22, verbatim

> Lineage continuity is a property of the Peering admission boundary, persisted
> as an immutable `AdmissionRecord` and resolvable at an exact version.

## Verification

| Check | Result |
|---|---|
| `pytest` (full suite) | **977 passed, 2 skipped** (baseline 963/2 + 14 new tests) |
| `mypy` (strict) | Success, 99 source files |
| `tools.lints --all` | exit 0 (No-Hardcoding, `@algorithmic` CINV-03, harness imports) |
| `pytest tests/a2a/test_admission_record.py` | 14 passed (criterion: ≥ 5) |
| `pytest tests/invariants/test_a2a_single_writer.py` | passed (re-run explicitly) |
| 06-18's suites (`test_federated_gates`, `test_admission_attributability`) | all pass; attributability gate preserved |
| `grep -c 'ccf.admission-record' src/ccf/a2a/admission.py` | 1 |
| `grep -c '"admission_record"'` (both files) | 0 |
| `git diff --stat src/ccf/replay/` | `engine.py \| 142 +++...` — output, as required |
| `grep -c "from ccf.replay" tests/a2a/test_admission_record.py` | 1 |
| `git diff --stat src/ccf/contracts/claims.py` | **no output** — unchanged |
| `git diff --stat src/ccf/controlplane/audit.py` | **no output** — unchanged |
| `git diff --stat src/ccf/boot.py` | **no output** — does not construct the gate |
| store constructed inside `admission.py` | 0 — injected, not constructed |

**The `GraphWriter` check, result stated as the plan requires:**
`grep -n "GraphWriter" src/ccf/a2a/admission.py` returns **zero hits** — stronger
than the criterion, which allowed docstring-only hits. The single `ccf.graph`
occurrence in the module is one docstring sentence stating the gate imports
nothing from it.

**The counterfactual, per the D-06 "a row is drafted from a failing test"
discipline.** Task 2's store write was temporarily reverted and the new file
re-run. Observed:

```
5 failed, 9 passed
FAILED test_an_admission_persists_an_admission_record
FAILED test_the_audit_append_carries_the_reference_triple
FAILED test_a_store_outage_is_not_reported_as_an_admission
FAILED test_the_union_is_observed_in_persisted_state_through_the_replay_path
FAILED test_a_store_returning_other_bytes_is_caught_not_believed
E  assert 'ccf.a2a-trust-policy' == 'ccf.admission-record'
```

The file's assertions are load-bearing rather than tautological. `admission.py`
was restored with `git checkout --` on that single file and the full suite re-run
green before committing.

## Deviations from Plan

### 1. [Rule 3 — Blocking] `AdmissionRecord` cannot live in `src/ccf/controlplane/artifacts.py`

- **Found during:** Task 1, before writing anything.
- **Issue:** the plan places the contract and its `ArtifactClass` in
  `controlplane/artifacts.py`. `AdmissionRecord` must carry three
  `ProductLineage` values, and that module **cannot import
  `ccf.products.contract`** — `products.contract` imports
  `ccf.controlplane.registry`, which imports `ccf.controlplane.artifacts`.
  Verified empirically rather than reasoned about:

  ```
  ImportError: cannot import name 'ControlPlaneMissing' from partially
  initialized module 'ccf.controlplane.registry'
  (most likely due to a circular import)
  ```

- **Fix:** the contract and `ADMISSION_RECORD` were declared in
  `src/ccf/a2a/admission.py`, following **that module's own established
  precedent for exactly this situation**: `InboundPayloadCeiling` /
  `INBOUND_PAYLOAD_CEILING` is already a Control Plane artifact class declared
  there, importing `ArtifactClass` from `controlplane.artifacts`. Everything
  load-bearing in the plan's Task 1 is preserved — the class-id convention read
  off `artifacts.py:268,270`, immutability per D-IMPL-27, content-addressability,
  the D-IMPL-58 citation — and Task 2's own criterion
  (`grep -c "ccf.admission-record" src/ccf/a2a/admission.py >= 1`) is satisfied
  naturally rather than by a second declaration.
- **Consequence for the plan's file list:** `src/ccf/controlplane/artifacts.py`
  shows no diff and is **dropped from `files_modified`**, per the plan's own
  stated discipline for `serve.py` ("rather than leaving a file listed that was
  never touched"). The three greps the plan aimed at `artifacts.py` were run
  against `admission.py` and are reported above.
- **Not silently improved:** the alternative — relocating `ProductLineage` to
  break the cycle — is a refactor of a load-bearing contract to satisfy a file
  placement, and was rejected.
- **Commit:** `466f309`.

### 2. [Rule 3 — Blocking] `serve.py` was not touched; dropped from `files_modified`

The plan left this to determination from the code and required the decision be
recorded. `serve.py` holds `ReplayWriter` — the **writer** side. Closure item 2
is a *resolution* path, which lives in `engine.py`; `resolve_artifact` /
`resolve_artifact_at_uri` are read-path functions with no writer counterpart to
add (admission does its own `put` through the injected store, and routing it
through a `ReplayWriter` would mint a `DeliveryCapability` for a product nobody
is delivering). `git diff --stat src/ccf/replay/` produces output from
`engine.py`, so the "one of `engine.py` or `serve.py` must show a diff"
requirement is met.

### 3. [Interpretation] `AdmittedProduct` appears in the new test file, but no assertion reads its lineage

The plan's criterion is `grep -c "AdmittedProduct" == 0` "in the assertion
bodies". The literal count is **9**, all of them
`assert isinstance(outcome, AdmittedProduct)` — a type check that *admission
succeeded*, which the union tests need in order to have a record to resolve at
all. The property the criterion protects is nonetheless held exactly:
**no assertion anywhere in the file reads `AdmittedProduct.lineage`.** Verified —
the only `.lineage` references on the wrapper in that file are four prose
mentions in docstrings explaining why reading it is forbidden. Every union
assertion reads the record resolved through `ccf.replay.engine`.

### 4. [Interpretation] A store outage raises rather than refusing

The plan's behaviour list says "surfaces as a typed failure at admission". It is
a raise (`AdmissionNotRecorded`), not a `GateRefusal`, on this module's own
established discipline — `_ceiling`'s docstring already states that a fabric that
cannot resolve its own configuration "is a broken deployment, not a badly behaved
peer, and reporting the two the same way would let an outage read as a federation
dispute". `ReplayWriter` applies the same reasoning to serving. Returning a
refusal would have put a substrate outage into the same channel as a peer's
governance violation.

### 5. [Minor] Baseline is 963 passing, not the plan's 940

The plan's no-regression criterion names a 940/2 baseline. The actual base
commit (`61ed8d4`, wave 1 merged) measures **963 passed, 2 skipped** — wave 1
added more than 06-18's 15 tests. No-regression was checked against the measured
963/2; the result is 977/2.

### 6. [Minor] Fixture vocabulary sources

Peer id, key id, producer hash, ceiling, semver, schema/plan/version, policy
regime and tenant all come from `tests/fixtures/banking/*.yaml`. **Operator keys
do not** — they are read from `ccf.operators.categories` (`PolicyFilter.key`,
`TraversalNeighborhood.key`, `TemporalAsOf.key`), on 06-18's precedent and for
its reason: an operator key is *mechanism* declared in `/src`, so restating one
as a literal would be the one place a drifted name could hide. Test instants are
literal test inputs, never clock reads. The consumer's lineage is deliberately
**disjoint from the producer's on all three axes** — a union asserted against
overlapping sets could pass while dropping a side.

## Vocabulary

Identifiers stay A2A-named, per the plan's explicit "do not half-rename"
instruction; `D-IMPL-59`'s `Peering` re-description lands wholesale in 06-24.
Prose describing the *category* says "a Peering" and cites D-IMPL-59.

## Threat Register Outcomes

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-06-100 (repudiation — a crossing with no record of what crossed) | mitigate | record written before `AdmittedProduct` exists; a failed write raises `AdmissionNotRecorded` and nothing is reported admitted. Both halves asserted. |
| T-06-101 (EoP — the store becoming a second writer to L3) | mitigate | store injected into the gate only; zero `GraphWriter` hits and zero `ccf.graph` imports in `admission.py`; `tests/invariants/test_a2a_single_writer.py` re-run green |
| T-06-102 (tampering — a record resolved at `@latest`) | mitigate | `resolve_artifact_at_uri` propagates `MovingTargetRefused`; additionally the resolved bytes are re-hashed, so a store returning *other* bytes raises `ReplayDivergence`. Both asserted through the replay entry point. |

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, or schema change at a trust boundary.
The one new persistence write is to an already-existing injected substrate inside
the tenant trust boundary (CLAUDE.md §7.4).

## Out of Scope / Follow-on

D-IMPL-58 **closure item 6** — ROADMAP criterion 2 and `docs/PHASE_I3_GATE.md`
row 14 — is **06-22**, per this plan's objective. The verbatim sentence it needs
is above.

## Self-Check: PASSED

- `src/ccf/a2a/admission.py` — FOUND
- `src/ccf/replay/engine.py` — FOUND
- `tests/a2a/test_admission_record.py` — FOUND
- commits `cb80b33`, `466f309`, `dc71c66`, `77ef83d`, `713efde`, `0bb79d2` — all present in `git log`
- `src/ccf/contracts/claims.py`, `src/ccf/controlplane/audit.py`,
  `src/ccf/boot.py`, `src/ccf/replay/serve.py`,
  `src/ccf/controlplane/artifacts.py` — confirmed **no diff** against the base
- STATE.md / ROADMAP.md — not modified (orchestrator owns those writes)
