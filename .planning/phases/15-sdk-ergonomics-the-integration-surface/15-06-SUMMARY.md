---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 06
subsystem: deployment
tags: [controlplane, artifacts, manifest, surface]
requires:
  - ccf.controlplane.artifacts (ArtifactClass, declared_artifact_class, DeclaredArtifact)
  - ccf.deployment package shell (15-02)
  - docs/surface/v0.2-surface.json baseline (15-01)
provides:
  - ccf.deployment.resolve_artifact_class
  - ccf.deployment.SDK_ARTIFACT_CLASSES
  - tests/deployment/ package with shared conftest fixtures
affects:
  - 15-07..15-09 (each new SDK ArtifactClass must be added to SDK_ARTIFACT_CLASSES)
  - 15-09, 15-10 (extend tests/deployment/conftest.py with manifest fixtures)
  - 15-21 (surface completeness cross-check reads this plan's fragment)
tech-stack:
  added: []
  patterns:
    - hand-maintained dict[str, T] module constant held to its source by a sync test
    - refuse-never-repair on an unnamed identifier
key-files:
  created:
    - src/ccf/deployment/classes.py
    - tests/deployment/__init__.py
    - tests/deployment/conftest.py
    - tests/deployment/test_class_lookup.py
    - docs/surface-changes/15-06-class-lookup.md
  modified:
    - src/ccf/deployment/__init__.py
decisions:
  - "Unknown class-ids resolve to the DeclaredArtifact envelope rather than raising: D-01 says the SDK owns the schema of what it ships and never invents one for what it does not."
  - "SDK ids resolve from the reviewed mapping before the declared fallthrough, so a manifest cannot shadow an SDK class into the permissive envelope (T-15-06-01)."
  - "The anti-drift test scans public module attributes of ccf.controlplane.artifacts rather than its __all__, because the two shipped ArtifactClass instances are not in __all__ and an __all__ scan would pass while proving nothing."
metrics:
  duration: ~25 min
  tasks: 2
  files: 6
  completed: 2026-08-04
---

# Phase 15 Plan 06: Class-ID Lookup Summary

A D-05 manifest's `class` string now resolves to the `ArtifactClass` that validates
the document it names — SDK-owned ids from a reviewed mapping, everything else
through the `DeclaredArtifact` open envelope by design rather than by failure.

## What Was Built

**`src/ccf/deployment/classes.py`** — algorithmic-tagged, SDK-extension-cited
(CLAUDE.md §6.4/§10). Two exports:

- `SDK_ARTIFACT_CLASSES: dict[str, ArtifactClass]` — hand-written by name
  (`ccf.half-life-table`, `ccf.debt-profile`), not scanned out of `globals()`, so a
  new SDK class is a deliberate reviewed two-line addition.
- `resolve_artifact_class(class_id) -> ArtifactClass` — SDK constant first, then
  `declared_artifact_class(class_id)`. Empty/whitespace ids are refused with a
  135-character message naming the property lost and who owns the fix.

Both re-exported from `ccf.deployment.__init__`, whose `__all__` was `[]` before this
plan. The package docstring gained a `Modules` cross-reference and its "ships empty on
purpose" paragraph was moved to past tense.

**`tests/deployment/`** — new package. `conftest.py` carries the fixtures the rest of
the phase shares: `artifacts_dir` (tmp_path-backed), `half_life_document` (minimal
valid λ_c table — one entry, because `entries` has `min_length=1`), and
`write_artifact(dir, name, document)`. `test_class_lookup.py` has 19 tests across
identity, anti-drift, declared fallthrough, refusal, shadowing, and this plan's own
surface claim.

**`docs/surface-changes/15-06-class-lookup.md`** — four entries, seven fields each,
all `Public surface: true`, all `Change type: added`.

## Key Implementation Details

**The `ccf.deployment` surface debt is discharged.** 15-02 recorded that the plan
adding the first real export owes the `Public surface: true` entry. `--report` shows
**four** names, not two — each object is reachable at its defining module *and* at the
package root, and the manifest records module-qualified names, so both spellings are
real entries. All four are claimed.

**The surface manifests were not touched.** `docs/surface/v0.2-surface.json` and
`v0.2-surface-baseline.json` are byte-unchanged; `make surface` was never run.
`tools/dump_surface.py --report` was used instead, and
`test_this_plans_fragment_claims_exactly_what_it_added` asserts subset-equality in
**both** directions at this plan's own wave rather than deferring the discovery to
15-21 at wave 14.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Vacuous assertion] Anti-drift test scans module attributes, not `__all__`**

- **Found during:** Task 2
- **Issue:** The plan specified test 2 over `ccf.controlplane.artifacts.__all__`. That
  list holds the classes and functions, but the two shipped `ArtifactClass`
  **instances** — `HALF_LIFE_TABLE` and `DEBT_PROFILE` — are *not* in it. An
  `__all__`-only scan finds zero instances, so the test that exists specifically to
  keep the hand-maintained mapping honest would have passed while proving nothing.
- **Fix:** `_exported_artifact_classes()` scans every public attribute of the module,
  a superset of the `__all__` names, and a vacuity guard asserts at least two were
  found and that both expected constants are among them. The deviation and its reason
  are recorded in the test module's own docstring so the next reader does not
  re-derive it.
- **Alternative rejected:** adding the two constants to `artifacts.__all__`. Plan 15-05
  owns `src/ccf/controlplane/artifacts.py` this wave; editing it was out of bounds.
- **Files modified:** `tests/deployment/test_class_lookup.py`
- **Commit:** 11caac8

**2. [Rule 2 - Missing coverage] Added a shadowing test for T-15-06-01**

- **Found during:** Task 2
- **Issue:** The threat register names class-id shadowing as `mitigate`, but the four
  planned tests never asserted the *ordering* that mitigates it.
- **Fix:** `test_the_declared_path_cannot_shadow_an_sdk_class` asserts no SDK id
  resolves to `DeclaredArtifact`.
- **Files modified:** `tests/deployment/test_class_lookup.py`
- **Commit:** 11caac8

## Verification

| Check | Result |
| --- | --- |
| `pytest tests/deployment/ -q` | 19 passed |
| `pytest tests/test_surface_drift.py -q` | passed (included in the 19-test run) |
| `pytest tests/products tests/lints tests/controlplane -q` | 118 passed |
| `make typecheck` | Success, 163 source files |
| `.venv/bin/python -m tools.lints --all` | exit 0 |
| `tools/dump_surface.py --report` | 4 added, 0 removed, 0 reshaped |
| Anti-drift test non-vacuity | verified in-process by binding a temporary `ArtifactClass` to the artifacts module — the test failed with the expected message naming `ccf/deployment/classes.py`, and passed again after removal. `artifacts.py` was never edited. |

## Known Stubs

None.

## Threat Flags

None — no new network endpoint, auth path, file-access pattern, or trust-boundary
schema. The one boundary in scope (manifest string → contract selection) is the
plan's own subject and is covered by the register.

## Self-Check: PASSED

- `src/ccf/deployment/classes.py` — FOUND
- `src/ccf/deployment/__init__.py` — FOUND
- `tests/deployment/__init__.py` — FOUND
- `tests/deployment/conftest.py` — FOUND
- `tests/deployment/test_class_lookup.py` — FOUND
- `docs/surface-changes/15-06-class-lookup.md` — FOUND
- commit `3600ae0` — FOUND
- commit `11caac8` — FOUND
