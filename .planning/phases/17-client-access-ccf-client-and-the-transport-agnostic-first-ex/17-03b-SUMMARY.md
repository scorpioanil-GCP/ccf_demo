---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 03b
subsystem: products
tags: [import-cycle, def-17-02, cold-import, adoption, sabotage]
requires: []
provides:
  - tests/invariants/test_cold_import.py
affects:
  - ccf.products.request
  - ccf.products.refusal
tech-stack:
  added: []
  patterns: [module-walk-population, cold-subprocess-probe, sabotage-controls, type-checking-guard, call-time-import]
key-files:
  created:
    - tests/invariants/test_cold_import.py
  modified:
    - src/ccf/products/request.py
    - src/ccf/products/refusal.py
    - tests/products/test_refusal_envelope.py
    - .planning/phases/17-client-access-ccf-client-and-the-transport-agnostic-first-ex/deferred-items.md
decisions:
  - "The cycle is broken at `ccf.products.request` -> `ccf.products.payload`, the only edge on the loop where both needed names are non-structural: one annotation and one call-time value. Every other edge carries a pydantic field type and needs the real class at `model_rebuild()`."
  - "A module walk, not a list of five. A list pins the cycle that was found rather than the property that matters."
  - "Not a structural cycle detector: D-IMPL-56 deliberately keeps cycles where a contract's field type lives across the seam, and a detector would refuse those rulings. The property owed to an adopter is empirical — every entry point works."
  - "The walk is scoped to `src/ccf`. CLAUDE.md 7.3's zero-harness-imports-in-core is what makes an unconditional probe there sound; the same probe over `runtime/` would make optional extras a hard dependency of an always-on test."
  - "DEF-17-01's closure was half wrong and the briefed baseline with it — measured, recorded as DEF-17-04, not fixed (ruling-scope)."
metrics:
  duration: ~2h
  completed: 2026-08-15
  tasks: 4
  commits: 5
---

# Phase 17 Plan 03b: Closing DEF-17-02 — the Cycle, Broken at Source

`import ccf.products.payload` now works as the first import into the tree, and
so does every other one of the **126** modules in the package — each verified in
its own cold subprocess. The edge that closed the cycle is gone rather than
reordered, `17-02`'s ordering workaround is deleted, and its pin now passes with
the two imports **deliberately reversed**.

---

## The cycle, re-derived before it was touched

Measured on `phase-17` @ `7d76205`, not inherited from the report:

```
PYTHONPATH=src:runtime .venv/bin/python -c "import ccf.products.payload"
→ ImportError: cannot import name 'PayloadSchemaViolation' from partially
  initialized module 'ccf.products.payload' (most likely due to a circular import)
```

It stood exactly as `17-02` recorded it — same five edges, same modules, same
line numbers:

| Edge | What it needs | Can it be deferred? |
|---|---|---|
| `payload` → `skills.catalog` | `SkillArgumentSchema`, aliased at module scope as `ProductPayloadSchema` (D-IMPL-103, *"an alias, never a copy"*) | **No** — a module-scope value |
| `skills.catalog` → `agents.definitions` | `InstructionBinding`, a field type of `SkillCatalogEntry` | **No** — `model_rebuild()` needs the class |
| `agents.agent` → `replay.record` | `NO_GRANTS_SET_HASH`, `PerspectiveConditioning` | constructor call + return annotation |
| `replay.record` → `products.request` | `ProductRequest`, a field type of `ContentGenerationPath` | **No** — `model_rebuild()` needs the class |
| `products.request` → `products.payload` | `PayloadSchemaViolation`, `refuse_payload` | **Yes — both** |

Three of the five edges carry a **pydantic field type**, which `TYPE_CHECKING`
cannot serve because `model_rebuild()` needs the real class. That is the
D-IMPL-56 pattern working as ruled, and it was left alone. The last edge was the
only one on the loop where neither name is structural.

**Why the suite could not see it.** `import ccf.products.request` first
*succeeds* — it completes the far side before re-entering — and something always
imports `request`, or a module reaching it, before `payload`. A warm interpreter
cannot observe this defect at all.

---

## What changed — one edge, in one module

`src/ccf/products/request.py`, and nothing else on the loop:

| Name | How it was actually used | Where it went |
|---|---|---|
| `PayloadSchemaViolation` | one parameter annotation on `request.py::_translate` — a plain function, not a contract, under `from __future__ import annotations`, so nothing resolves it at runtime | `TYPE_CHECKING` |
| `refuse_payload` | a *value*, called once inside `request.py::refuse_request` | call-time import in that function |

The bottom-of-module `ccf.skills.catalog` import **stays**, and the comment now
says why it has to: `SkillArgumentSchema` is a field type of
`ProductRequestContract`.

`src/ccf/products/refusal.py`: the two imports return to sorted position —
`payload` first, **the exact order that used to raise** — and the fourteen-line
comment explaining the constraint is deleted.

`git diff --stat` for the source: **2 files, 72 lines**, the budget was three
modules.

---

## Verification — every number measured

| Check | Result |
|---|---|
| `ccf.*` modules failing as a cold first import, **before** | **2** — `ccf.products.payload`, `ccf.products.bind` |
| `ccf.*` modules failing as a cold first import, **after** (126 walked, one subprocess each) | **0** |
| `ccf_runtime.*` modules failing (69 walked) | **0**, before and after |
| `pytest tests/invariants/test_cold_import.py -q` | **6 passed** in 2.6s |
| `pytest tests/products/test_refusal_envelope.py -q` | **36 passed** |
| `pytest tests/products/test_refusal_envelope.py tests/products/test_request_contract.py -q` | **89 passed** |
| `make typecheck` (`mypy --strict`) | **Success: no issues found in 197 source files** |
| `.venv/bin/python -m tools.lints --all` | **exit 0** |
| `make ci-core` | **3345 passed / 2 failed / 118 skipped** |

### The pass-count delta, derived

```
3339  pristine baseline  (phase-17 @ 7d76205 — measured, see DEF-17-04)
3345  after this plan
──────
   6  delta  ==  6 `def test_*` functions in tests/invariants/test_cold_import.py
```

The two failures are the pre-existing citation ratchets. **Neither names a file
this plan touched**, and the finding counts are unchanged at `assert 1 <= 0` and
`assert 14 == 13` — my prose added nothing to either population, which was
checked rather than assumed.

---

## The pin is now independent of import order — proven, not asserted

`tests/products/test_refusal_envelope.py::test_the_cold_and_warm_runs_agree_on_the_enumeration`
**stays**: it is the regression pin for the real fix. The requirement was that
it pass *because the cycle is gone*, not because two lines are in a lucky order.

The two `ccf.products` imports in `refusal.py` were **deliberately reversed**
back to `request`-then-`payload`, bytecode cleared, and the suite re-run:

| Under the reversed order | Result |
|---|---|
| the pin alone | **1 passed** |
| the whole module | **36 passed** |
| `import ccf.products.payload` cold | **OK** |

Before the fix, `17-02` verified by sabotage that this same reversal *failed*
that test. It no longer can, in either direction. The imports were then restored
to sorted order, from a byte-for-byte copy rather than `git checkout --`, per
**DEF-17-03**.

The pin's docstring no longer claims to hold an import order in place, because
it does not — a stale docstring asserting a defect that no longer exists is
exactly the prose drift this project keeps finding away from changed lines.

---

## The guard that replaces the workaround

`tests/invariants/test_cold_import.py`. A **module walk**, not a list of five:
a list pins the cycle that was found rather than the property that matters, and
the next cycle lands somewhere else and passes.

**Deliberately not a structural cycle detector.** Import cycles are not per se
defects here — D-IMPL-56 rules a pattern that keeps some, and a detector would
refuse those rulings. What is owed to an adopter is narrower and empirical:
*whatever the graph looks like, every entry point works.*

### The guards on the instrument

Verification code is where this project's defects land, so each of these was
watched firing:

| Guard | Sabotage | Observed |
|---|---|---|
| the real assertion | module-scope edge restored in `request.py` | **3 modules named**: `payload`, `bind`, and now `refusal` — which fails too, since it no longer orders around the defect |
| `test_the_walk_agrees_with_the_filesystem` | n/a — a live cross-check of `pkgutil` against a filesystem glob, compared as **sets of paths**, so a walk that lost one and invented another cannot net out | 103 walked == 103 on disk |
| `test_a_broken_package_stops_the_walk_instead_of_truncating_it` | planted sub-package whose `__init__` raises | `walk_modules` propagates `ImportError`; `pkgutil.walk_packages` swallows it by default and would have reported a green subset |
| `test_the_probe_reports_a_planted_cycle` | two-module cycle in `tmp_path`, run through the **real** probe | both modules reported, both messages carrying `partially initialized` |
| `test_the_probe_passes_the_same_arrangement_without_the_cycle` | the twin, cycle removed | clean — isolates the cycle as the cause rather than something about `tmp_path` |
| `test_the_five_modules_the_defect_was_reported_against_are_in_the_walk` | n/a — anchors the discovered set to DEF-17-02's named victims | all five present |

`PYTHONDONTWRITEBYTECODE=1` is set on every probe, so the guard cannot itself
contribute to the DEF-17-03 hazard.

### Why the walk stops at `src`

`ccf_runtime` has the same first-contact property and was measured clean
(**69 of 69**). It is not walked unconditionally, for a structural reason:
CLAUDE.md §7.3 guarantees **zero harness imports in core**, which is exactly
what makes an unconditional probe over `src/ccf` sound — nothing there can fail
for want of an optional extra. The runtime's adapter and orchestration modules
import `google.adk` and `langgraph` at module scope, *correctly*, since they are
the adapters. The same probe over `runtime/` would turn optional extras into a
hard dependency of an always-on invariant test. That coverage belongs behind the
`harness` marker, with whoever owns it. Recorded rather than silently skipped.

---

## Deviations from Plan

### 1. [Rule 3 — blocking] The worktree was stale and had no `.venv`

**Found during:** startup. This worktree's branch sat at `6e95da0` (the phase
15.6 merge) — no Phase 17 files existed in it — and `.venv` lives only in the
main checkout.
**Fix:** fast-forwarded to `phase-17` @ `7d76205` with `git merge --ff-only`
after confirming `6e95da0` is a strict ancestor and the tree was clean
(non-destructive; no reset, no local commits at risk), and symlinked `.venv`.
Verified `ccf.__file__` resolves to **this worktree's** `src/`, not the editable
install's. Identical to `17-02`'s deviation 1 — this is now the third executor
to hit it, and it is a spawn-time property rather than a plan property.

### 2. [Rule 2] The pin's docstring asserted a defect that no longer exists

**Found during:** after the workaround removal.
**Issue:** `test_the_cold_and_warm_runs_agree_on_the_enumeration` documented
itself as pinning *"the load-bearing import order"* against *"the tree's
pre-existing cycle"*. Both clauses became false.
**Fix:** rewritten to say what it now asserts and to name where the property is
guarded instead. No assertion changed — the test body is untouched.

### 3. Beyond the brief: `ccf_runtime` measured, and the reason for excluding it recorded

The brief scoped the walk to `ccf.*`. Extending it to `ccf_runtime` looked free
— it was already green at 69/69 — but would have made the `adk` and `langgraph`
extras a hard dependency of an always-on test. Excluded, with the reasoning and
the measurement recorded above rather than left as an unexplained boundary.

### 4. Out of scope, logged not fixed: the briefed baseline is wrong (DEF-17-04)

**Found during:** final verification. `make ci-core` reported 2 failures against
a briefed baseline of *0 failed*.
**Measured, not assumed:** all four of this plan's files were removed from the
tree — the three tracked ones reverted, the new one moved out — and the full
suite re-run on a clean `git status`. Pristine `phase-17` @ `7d76205` is
**3339 passed / 2 failed / 118 skipped**. The two failures are the
citation-coverage ratchets `17-01` and `17-02` both reported.

DEF-17-01 is marked RESOLVED and one of its two claims did not hold: it
attributed the second finding to the sweep counting each executor's own
`deferred-items.md`. That explanation predicts the finding vanishes on a tree
where nobody is documenting it — the pristine run has no such file in play and
still reports it.

Both remaining remedies are **ruling-scope by the gates' own failure text**, and
the third (converting the citation) lands in a phase-16 test file no wave owns.
Logged as **DEF-17-04**, not taken.

---

## Wave coordination

`17-03` (resolver seam) and `17-04` (wire + codec) ran in parallel. Neither
touches the cycle modules, and this plan touched neither
`src/ccf/products/gates.py` nor `src/ccf/replay/serve.py`, which `17-03`'s
composition reads. `git diff --stat` confirms the source footprint is
`src/ccf/products/request.py` and `src/ccf/products/refusal.py` only.

---

## Commits

| Commit | What |
|---|---|
| `4021df2` | `fix(17-03b)` — the cycle broken at source: `TYPE_CHECKING` + call-time import |
| `083bf69` | `refactor(17-03b)` — `17-02`'s ordering workaround and its rationale retired |
| `0625039` | `test(17-03b)` — the cold-import module walk and its five guards |
| `55954aa` | `docs(17-03b)` — DEF-17-02 RESOLVED; DEF-17-04 opened |
| *(this file)* | `docs(17-03b)` — SUMMARY |

---

## Known Stubs

None. The fix removes an import edge; it adds no code path, no placeholder and
no empty value. The new test file has no skipped or xfailed case.

## Threat Flags

None. No network endpoint, auth path, file access or schema at a trust boundary
was added or moved. The change is strictly a reduction in import-time coupling;
no public name moved between modules, and `__all__` is unchanged in both files
— which is why no `docs/surface-changes/` fragment was required, confirmed by
`tests/test_surface_drift.py` staying green.

## Self-Check: PASSED

Files verified present:

- `FOUND: tests/invariants/test_cold_import.py`
- `FOUND: src/ccf/products/request.py`
- `FOUND: src/ccf/products/refusal.py`
- `FOUND: .planning/phases/17-.../deferred-items.md`

Commits verified in `git log`: `4021df2`, `083bf69`, `0625039`, `55954aa` — all
found.
