---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 01
subsystem: ci-invariants
tags: [cinv-02, harness-neutrality, lint, decisions]
requires: []
provides:
  - "HARNESS_ADAPTER_MODULES carve-out unblocking runtime/ccf_runtime/adapters/*"
  - "Negative boundary tests pinning the CINV-02 adapter carve-out"
  - "D-IMPL-53 (CINV-02 scope narrowing)"
affects:
  - "All wave (c) harness adapter plans (Claude Agent SDK, Google ADK, LangGraph)"
tech-stack:
  added: []
  patterns:
    - "Module-path carve-out constant mirroring LLM_ADAPTER_MODULES"
    - "Counterfactual verification of boundary tests before commit"
key-files:
  created: []
  modified:
    - tools/lints/harness_imports.py
    - tools/lints/tests/test_harness_imports.py
    - docs/DESIGN.md
    - docs/DECISIONS.md
decisions:
  - "D-IMPL-53: CINV-02 harness-import lint scoped to core via a structural module-path carve-out, never an allowlist"
metrics:
  duration: ~20 min
  completed: 2026-07-26
  tasks: 3
  commits: 2
---

# Phase 06 Plan 01: CINV-02 Adapter Carve-Out Summary

Narrowed the CINV-02 harness-import lint from all of `/runtime` to "everything
outside `ccf_runtime.adapters.*`" with a reviewed code constant, pinned the new
boundary with four negative tests, and corrected the two documents that were
either overclaiming the enforcement or misallocating the adapters to Phase I.4.

## What Was Built

**Task 1 — `HARNESS_ADAPTER_MODULES` carve-out** (`tools/lints/harness_imports.py`).
Added `HARNESS_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf_runtime.adapters"})`
immediately after `LLM_ADAPTER_MODULES`, computed `in_harness_adapter` alongside
`in_llm_adapter`, and guarded the `HARNESS_DENY` branch with `and not in_harness_adapter`
— structurally identical to the existing vendor-LLM carve-out. `LINTED_TREES` in
`tools/lints/__main__.py` was left untouched (verified by empty `git diff --stat`), so
the rest of `/runtime` remains linted. No allowlist file was created.

The module docstring's absolute claim ("Import restrictions have no legitimate
exceptions") was replaced with a D-21-scoped statement: the rule is lint-enforced as
*"no module outside `ccf_runtime.adapters.*` may import a harness package"*, framed
explicitly as a narrowing to CLAUDE.md §7.3's own word "core" rather than as an
exception. The no-allowlist commitment survives, restated as a claim about mechanism
(carve-outs are module-path constants under review, not data files).

**Task 2 — Boundary tests** (`tools/lints/tests/test_harness_imports.py`). Four new
tests, named for the property rather than the mechanism:
`ccf_runtime.adapters.langgraph.adapter` importing `langgraph` is clean; harness
imports in `ccf_runtime.a2a.lf_a2a`, `ccf_runtime.cdc.adapter`, and the shared-prefix
lookalike `ccf_runtime.adapters_evil` each still yield `[RULE_HARNESS]`. The existing
`/src` case (`ccf.operators.traversal`) is unchanged and still flagged. Shipped in the
same commit as the carve-out.

`matches_module` was already dot-bounded (`name == p or name.startswith(p + ".")`), so
the lookalike case passed without modification — no weakening of the test was needed
and none was made.

**Task 3 — Doc corrections.** `docs/DESIGN.md` §8.9 now attributes the three reference
adapters and their conformance suite to Phase I.3, with a visible parenthetical naming
the correction date and citing ROADMAP Phase 6 criterion 3 and REQUIREMENTS XPRC-03;
the genuinely-I.4 experience-surface content was left alone. `docs/DECISIONS.md` gains
`D-IMPL-53` in the surrounding entries' format, recording the question, the ruling, the
explicit rejection of an allowlist, the D-21-compliant claim wording, and the negative
tests as enforcing evidence. The entry asserts no "no path" or "by construction"
property about the lint.

## Verification

| Check | Result |
| --- | --- |
| `python -m tools.lints --all` | exit 0 |
| `python -m pytest tools/lints/tests/test_harness_imports.py -q` | 14 passed |
| `python -m pytest -q` (full suite) | 627 passed, 2 skipped — no regressions |
| `python -m mypy` | Success, no issues in 65 source files |
| `git diff --stat tools/lints/__main__.py` | empty |

**Counterfactual check on the boundary tests** (plan acceptance criterion): with
`HARNESS_ADAPTER_MODULES` emptied, the adapter-path case produces a `cinv02-harness`
finding (case 1 would fail); with `matches_module` swapped for a naive `startswith`,
the `adapters_evil` case produces no finding (case 4 would fail). Both tests therefore
pin real behavior rather than passing vacuously.

**End-to-end success criterion, verified on disk with throwaway probes** (created,
checked, removed — working tree left clean): a real file at
`runtime/ccf_runtime/adapters/probe/adapter.py` containing `import langgraph` passes
`python -m tools.lints --all` (exit 0), while the same import at
`runtime/ccf_runtime/a2a/probe.py` fails it (exit 1).

## Deviations from Plan

None — plan executed as written.

Two plan expectations resolved without needing action: the `matches_module`
dotted-boundary contingency in Task 2 (already correct, with a pre-existing
`langgraphql` test documenting the intent), and the D-IMPL number (grep confirmed
`D-IMPL-52` was the highest, so `D-IMPL-53` was free as predicted).

## Threat Register Disposition

| Threat ID | Disposition | Evidence |
| --- | --- | --- |
| T-06-01 | mitigated | Carve-out is a `frozenset` constant in reviewed code; no allowlist file created or referenced; four boundary tests |
| T-06-02 | mitigated | Docstring rescoped in the same commit as the guard; D-IMPL-53 logged |
| T-06-03 | mitigated | `adapters_evil` lookalike test passes on the existing dot-bounded `matches_module`; counterfactual confirms the test would fail under a naive prefix match |
| T-06-SC | n/a | No package installs in this plan |

## Known Stubs

None.

## Threat Flags

None — no new network, auth, file-access, or schema surface. The change narrows a CI
lint's scope; the narrowing itself is the surface, and it is bounded by test.

## Notes for Downstream Plans

Wave (c) is unblocked: adapter modules under `runtime/ccf_runtime/adapters/<harness>/`
may now import their harness SDK. Two constraints carry forward:

- The carve-out is **`ccf_runtime.adapters` only**. A harness import anywhere else in
  `/runtime` — including `ccf_runtime.a2a` and `ccf_runtime.cdc` — still fails, by
  test. Adapters must not leak harness imports into shared runtime modules.
- Per D-21, adapter-seam and `effects: unsupported` claims in later plans should be
  worded to their actual enforcement ("conformance-verified", "lint-enforced"), the
  same discipline applied to the lint docstring here.

## Self-Check: PASSED

- `tools/lints/harness_imports.py` — FOUND (modified, contains `HARNESS_ADAPTER_MODULES`)
- `tools/lints/tests/test_harness_imports.py` — FOUND (modified, contains `ccf_runtime.a2a`)
- `docs/DESIGN.md` — FOUND (modified)
- `docs/DECISIONS.md` — FOUND (modified, contains `D-IMPL-53`)
- Commit `794bcef` (lint carve-out + tests) — FOUND
- Commit `6c6ef0b` (doc corrections + D-IMPL-53) — FOUND
