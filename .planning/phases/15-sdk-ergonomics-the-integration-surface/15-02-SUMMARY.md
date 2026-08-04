---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 02
subsystem: deployment
tags: [d-15a, ergo-02, ergo-04, cinv-02, cinv-03, gate-independence]
requires:
  - docs/surface-changes/ fragment contract
  - tests/test_surface_drift.py
provides:
  - ccf.deployment
  - tools.lints.harness_imports.RULE_DEPLOYMENT_GATES
  - tools.lints.harness_imports.submodule_import_names
  - tests/products/test_gate_independence.py
affects:
  - tools/lints/harness_imports.py
  - tools/lints/__main__.py
tech-stack:
  added: []
  patterns:
    - "guard-before-helper: the standing constraint lands before the code it constrains"
    - "AST identifier walk over source text, so a docstring documenting compliance cannot trip the guard"
    - "paired mechanisms: a lint refuses the import, a test refuses the shape"
key-files:
  created:
    - src/ccf/deployment/__init__.py
    - tests/products/test_gate_independence.py
    - tests/lints/test_deployment_gates_ban.py
    - docs/surface-changes/15-02-deployment-package.md
  modified:
    - tools/lints/harness_imports.py
    - tools/lints/__main__.py
decisions:
  - "The ccf.deployment fragment entry is Public surface: false, not true — dump_surface.py skips modules with a falsy __all__, so an empty shell produces no diff line and a true claim would fail 15-21's completeness cross-check"
  - "The new rule ships inside the existing harness-imports checker rather than a new module, so CHECKERS needs no key and the rule inherits the ('src','runtime') tree scope that already covers ccf.deployment"
  - "submodule_import_names supplements the shared imported_module_names helper only for module-denial rules, leaving the existing two rules' behavior untouched"
metrics:
  duration: ~40m
  completed: 2026-08-04
  tasks: 3
  commits: 3
---

# Phase 15 Plan 02: The ccf.deployment Shell and the D-15A Standing Guard Summary

Created the SDK's adopter-facing wiring package as an empty, documented,
algorithmic-tagged shell and landed the gate-independence guard around it — one
executable test module and one no-allowlist CI lint rule — before any ergonomics
helper exists to be constrained.

## What Was Built

**`src/ccf/deployment/__init__.py`** — the package root. `from __future__ import
annotations`, `__ccf_mode__ = "algorithmic"`, `__all__: list[str] = []`, and
nothing else. The deliverable is the docstring, which carries three things: the
SDK-extension citation in the `boot.py:1-4` form (CLAUDE.md §6.4 and §10 — the
whitepaper specifies the artifacts and the invariants, not the wiring that loads
them); the CINV-03 reading written down so it is not re-derived ("algorithmic"
means no model call, not no I/O, with `boot.py:55` and `artifacts.py:47` cited as
precedent and `tools/lints/algorithmic.py` cited as the checker that says nothing
about the filesystem); and the D-15A abstraction line stated through the
`run_gates` worked example, with three operational prohibitions spelled out.

**`tests/products/test_gate_independence.py`** — four tests.

1. *Perturbation regression.* A minimal valid `ContextProductContract` whose
   `ProductLineage.operators_invoked` is a known three-element frozenset; calling
   `run_gates` with `engine_resolved` set to that frozenset minus one element
   returns a `LineageMismatchRefusal` carrying the right `declared`/`resolved`
   pair, and calling it with the declared set unchanged returns a
   `ServableProduct`. Either half alone is weak — a gate that always refuses
   passes the first, a gate that always admits passes the second — and only the
   pair says the comparison is live.
2. *AST identifier guard.* `_identifiers` copied verbatim from
   `test_adapter_single_writer.py:128-150` including its reasoning, walking
   `ast.Name` / `ast.Attribute` / `ast.alias` and never source text, parametrized
   per file with `ids=lambda p: p.name`. This is not a stylistic preference: the
   package docstring names `run_gates` and `engine_resolved` as its worked
   example, so a grep-based guard would fail on the very documentation recording
   compliance.
3. *Signature inspection.* No public callable exported from any
   `src/ccf/deployment/` module has annotations mentioning both a lineage-shaped
   (`ProductLineage`) and an execution-shaped (`ProjectionExecution`) name, using
   the whole-token `_annotation_names` regex rather than substring matching.
4. *Vacuity.* The discovery glob found at least one module, the directory exists,
   and `ccf.deployment` imports with its tag intact.

The module docstring carries the two-section discipline verbatim — **"What these
tests enforce, exactly"** and **"What they do not enforce"** — the latter naming
three real gaps: these tests do not prove the projection engine computed
`operators_invoked` correctly, do not cover adopter code outside
`ccf.deployment` (where gate execution actually lives and a caller is free to
pass the same value twice), and cannot see a collapse expressed through dynamic
attribute access.

**`tools/lints/harness_imports.py`** — a third rule, `cinv02-deployment-gates`,
folded into the file's existing single AST walk rather than given a new checker
module. New constants `RULE_DEPLOYMENT_GATES`, `GATES_MODULE =
"ccf.products.gates"`, `GATES_DENIED_IMPORTER = "ccf.deployment"`. Both matches
are dot-bounded via the shared `matches_module`, so `ccf.deployment.manifest` is
caught and `ccf.deployment_evil` is not. No allowlist — the governance posture at
`:29-31` is reproduced for the new rule, and the docstring now reads "Three
rules, one AST walk".

**`tools/lints/__main__.py`** — `RULE_TREE_SCOPE`'s comment block now names the
third rule and states why it needs no `CHECKERS` key: it ships inside the
`harness-imports` checker and inherits its `("src", "runtime")` scope, which
already covers `ccf.deployment`.

**`tests/lints/test_deployment_gates_ban.py`** — three tests on the
`test_examples_scope.py` template, driving `tools.lints.__main__.run` over
synthetic tmp trees: the ban fires on `src/ccf/deployment/x.py`; both the
`import ccf.products.gates` and `from ccf.products import gates` spellings are
caught; and the opposite-direction regression guard shows `ccf.products.serve`
may still name the gate module and the sibling `ccf.deployment_evil` is not
caught by accident.

## Key Decisions

**The `ccf.deployment` fragment entry is `Public surface: false`.** The plan
asserted that creating a module defining `__all__` makes `ccf.deployment` a key
in the surface manifest, and that `--report` would list it under `added`. It does
not: `dump_surface.build_surface` skips any module whose `__all__` is falsy
(`if not exported: continue`), and this package's `__all__` is deliberately `[]`.
`--report` confirms empirically — zero added, zero removed, zero reshaped. There
is therefore no fully-qualified name to claim and no diff line for plan 15-21's
completeness cross-check to match, so a `true` classification would fail that
check as an unmet claim at the most expensive point in the phase. The entry is
`false` with `Surface: src/ccf/deployment/__init__.py`, a token that can never
appear in a manifest diff (diff entries are dotted names), so the `false`
direction of 15-21's assertion holds too. The reasoning is recorded in the
fragment itself, not only here. The first real *export* this package gains is a
genuine public-surface addition, claimed as `true` under its own
fully-qualified name by whichever plan adds it.

**The rule needed a submodule-import helper.** `from ccf.products import gates`
binds `ccf.products.gates` exactly as `import ccf.products.gates` does, but the
shared `imported_module_names` reports only `ccf.products` for it — correctly,
since it cannot tell a submodule from an attribute. Rather than widen that shared
helper and change the two existing rules' behavior, a local
`submodule_import_names` supplements it for the new module-denial rule only. A
name that is an attribute rather than a submodule simply never matches a deny
entry, so over-reaching costs nothing. Without this, the ban would have been a
one-spelling ban, which is not a ban; the second lint test pins it.

**One finding per import statement, not one per matching spelling.** The first
implementation emitted two findings for `from ccf.products.gates import
run_gates` — one from each helper. Deduplicated to a set before reporting;
repeating the same line twice is noise, not evidence.

## Verification Performed

| Check | Result |
| --- | --- |
| `pytest tests/products/test_gate_independence.py -q` | 4 passed |
| `pytest tests/lints/ -q` | 44 passed (3 new, 41 pre-existing) |
| `pytest tests/test_surface_drift.py -q` | 5 passed |
| `pytest tests/invariants -q` (regression, shared checker touched) | 78 passed |
| `python -m tools.lints --all` | exit 0, clean |
| `make typecheck` | Success, 162 source files |
| `tools/dump_surface.py --report` | added 0 / removed 0 / reshaped 0 |
| `git status` on `docs/surface/*.json` | untouched — neither manifest appears in the diff |

**The guard was proven to bite, not assumed to.** Appending `from
ccf.products.gates import run_gates` to `src/ccf/deployment/__init__.py` made
test 2 fail naming `__init__.py` and `['run_gates']`. Reverted, re-run, 4 passed.
The lint rule's own bite is proven by its first two tests rather than by a
temporary mutation, since those tests drive real tmp trees through the CI
entrypoint.

## Deviations from Plan

**1. [Rule 1 - Bug] The `ccf.deployment` fragment entry is classified
`Public surface: false`, not `true`**

- **Found during:** Task 3, running `tools/dump_surface.py --report`
- **Issue:** the plan's acceptance criteria required the entry to be
  `Public surface: true` with `Surface` = the dotted name `ccf.deployment`, and
  required `--report` to list `ccf.deployment` under `added`. Both rest on a
  premise that is false against the merged 15-01 mechanism: `build_surface`
  skips modules with a falsy `__all__`, and Task 1's own acceptance criterion
  fixes `__all__` at `[]`. The two criteria are mutually unsatisfiable.
- **Fix:** kept `__all__ == []` (the empty shell is the plan's stated point and
  Task 1's explicit criterion) and classified the entry `false` with the
  repo-relative path as its `Surface` token. Claiming `true` with no diff line
  would have passed the standing drift gate now and failed 15-21's completeness
  cross-check at wave 14. The alternative — teaching `dump_surface.py` to record
  empty-`__all__` modules — was rejected outright: it is a whole-tree change to a
  single-owner artifact this plan does not own, and it would move the manifest
  for 140 modules' worth of unrelated reasons.
- **Files modified:** `docs/surface-changes/15-02-deployment-package.md`
- **Commit:** 675e776

**2. [Rule 3 - Blocking] Symlinked `.venv` into the worktree**

- **Found during:** Task 1 verification
- **Issue:** every verify command invokes `.venv/bin/python`; the git worktree
  has no `.venv` (it lives in the main checkout and is gitignored).
- **Fix:** `ln -s /home/parkave/ccf_code/.venv .venv`. Confirmed via
  `ccf.deployment.__file__` that `PYTHONPATH=src:runtime` resolves the
  **worktree's** sources, so every verification above ran against the code under
  review.
- **Files modified:** none tracked (gitignored, not committed)
- **Commit:** n/a

**3. [Rule 2 - Missing critical functionality] `submodule_import_names` added to
`tools/lints/harness_imports.py`**

- **Found during:** Task 3
- **Issue:** the plan specified emitting a finding when `matches_module(name,
  (GATES_MODULE,))` over the existing `ast.walk`, but the shared helper never
  produces `ccf.products.gates` for `from ccf.products import gates` — while the
  plan's own third lint test requires that spelling to be caught.
- **Fix:** a local helper expanding `ImportFrom` aliases into candidate dotted
  names, applied to the new rule only so the two existing rules are behaviorally
  unchanged (`tests/invariants` and the pre-existing `tests/lints` all still
  green).
- **Files modified:** `tools/lints/harness_imports.py`
- **Commit:** 675e776

Otherwise the plan executed as written.

## Notes for Future Plans

- **The first export added to `ccf.deployment` is the plan that owes the
  `Public surface: true` fragment entry**, under its own fully-qualified dotted
  name. This plan claims only the file, not any name.
- Any helper added to this package must survive `tests/products/
  test_gate_independence.py` tests 2 and 3 — it may not *name* `run_gates`,
  `ProductLineage`, or `engine_resolved`, and no single callable may mention both
  a lineage-shaped and an execution-shaped type. If a helper genuinely needs to
  express gate wiring, that is a D-15A boundary question and a decision, not an
  in-plan workaround.
- `submodule_import_names` is exported and reusable if another module-denial rule
  needs the same expansion.

## Known Stubs

None. The package is deliberately empty and its emptiness is the deliverable —
the guard exists so the package's future contents are constrained from the start.
`ProjectionExecution` does not yet exist anywhere in the tree; test 3 checks for
the token forward-lookingly, which is correct for a standing guard and is why
test 4's vacuity check exists.

## Threat Flags

None. No new network endpoint, auth path, file access pattern, or trust-boundary
schema. The `run_gates` trust boundary is the one this plan *hardens*, and the
STRIDE register's four mitigations all landed: T-15-02-01 (perturbation
regression), T-15-02-02 (AST guard plus no-allowlist lint), T-15-02-03 (package
ships empty; CINV-02 graph-writer ban already denies `ccf.graph._writer`),
T-15-02-04 (vacuity test). No package installs (T-15-02-SC).
