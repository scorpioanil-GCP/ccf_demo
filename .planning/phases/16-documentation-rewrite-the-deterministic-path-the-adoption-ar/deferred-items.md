# Deferred items — phase 16

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary. Each entry names the plan that found it and the plan that should own
it.

## Two `tests/products/` docstrings cross-reference the retired ERGO-03 audit module

- **Found during:** plan 16-01, Task 2, when
  `tests/examples/test_surface_audit.py` was deleted under `D-IMPL-94` / `D-15`.
- **What:** two modules name that file in prose as a live exemplar of the
  "assemble the probe body at runtime so this module's own source is not what a
  scan trips over" discipline. Both statements are present-tense and both became
  false the moment the module was deleted:
  - `tests/products/test_gate_two_call_shape.py`, in the docstring of the
    binder-scan non-vacuity test — *"the discipline
    `test_required_operators_guard.py::test_the_guard_detects_the_shortcut_it_exists_to_refuse`
    and `tests/examples/test_surface_audit.py` both use"*.
  - `tests/products/test_required_operators_guard.py`, in the in-body comment
    above the assembled probe sources — *"the same discipline
    `tests/examples/test_surface_audit.py` uses for the figures it forbids"*.
- **Why it was not fixed in 16-01:** the plan's Task 2 `<files>` list does not
  include either module, and both are owned by later plans in this phase —
  16-15 (limb 2, retiring
  `test_the_plan_recognition_refuses_an_unrelated_required_keyword`) and 16-18
  (limb 1, re-flooring the four non-vacuity constants). Editing them from a
  wave-1 worktree would collide with those plans in a later wave for no benefit.
  Neither reference is a *citation* in the `tools/lints/citations.py` sense —
  both are bare backticked paths with no `:NNN` and no `::symbol` — so nothing
  goes red today; `python -m tools.lints --all` exits 0 with the module gone.
- **Where it belongs:** plan 16-15 and plan 16-18, each correcting the module it
  already has open. The correct redirect is
  `docs/surface/examples/ERGO-03-FROZEN.md`, which records the same discipline
  and states why the module that practised it retired. Both edits are docstring
  prose, not detection logic, so neither is touched by `D-14`'s carry-forward.

## `docs/SURFACE-CHANGES.md` and `docs/surface-changes/15-03-audit-baseline.md` name the retired module

- **Found during:** plan 16-01, Task 2.
- **What:** both name `tests/examples/test_surface_audit.py` as a live module.
  `docs/surface-changes/15-03-audit-baseline.md` is the per-plan fragment that
  recorded its creation; `docs/SURFACE-CHANGES.md:2964` is the assembled mirror
  of that fragment.
- **Why it was not fixed:** these are **dated per-plan records of what a plan
  did at the time**, which is the same class `deferred-items.md` for Phase 15.1
  repeatedly declined to rewrite — correcting them would falsify the record of
  what plan 15-03 built. Whether such records are *corrected* or *annotated* is
  the open editorial judgment `docs/SURFACE-AUDIT.md` §5.4 already carries, and
  `D-IMPL-94`'s Q-6 disposition settles only whether `SURFACE-CHANGES.md`
  publishes, not how its dated fragments age.
- **Where it belongs:** plan 16-20 or 16-21, alongside whatever standing gate
  `DOCS-17` builds for stale prose paths — which is the mechanism that will have
  to decide the general rule, not this one file.
