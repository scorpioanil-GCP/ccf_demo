---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 03
subsystem: skills-dispatch
tags: [d-19, d-impl-54, in-06, t-05-18, security, registry]
requires: []
provides:
  - "CallableRegistry — boot-time key->callable table with typed Duplicate/NotRegistered errors"
  - "importlib-free local_callable dispatch (the D-19 blocking gate, now closed)"
  - "D-IMPL-54 (registered-callable table as the IN-06 control)"
affects:
  - "Plan 06-06 (MCP transports) and 06-10 (A2A) — the gate blocking non-fixture catalog sources is closed"
  - "Any future composition root: AgentFactory/Agent now take an optional callable_registry"
tech-stack:
  added: []
  patterns:
    - "Structural port of the D-IMPL-37 operator-registry shape to a second registry"
    - "Constructor injection of the registry at the composition root; no ambient singleton"
    - "Deferred (call-time) import to break a module-level package import cycle"
key-files:
  created:
    - src/ccf/skills/callables.py
    - tests/skills/test_callables.py
  modified:
    - src/ccf/skills/dispatch.py
    - src/ccf/skills/catalog.py
    - src/ccf/agents/agent.py
    - src/ccf/agents/factory.py
    - tests/conftest.py
    - tests/skills/test_dispatch.py
    - tests/agents/test_consumption_discipline.py
    - tests/fixtures/banking/skills/covenant_metrics_tool.yaml
    - tests/fixtures/banking/skills/grants.yaml
    - tests/fixtures/banking/skills/callables.py
    - docs/DECISIONS.md
    - docs/PHASE_I2_GATE.md
decisions:
  - "D-IMPL-54: callable_ref becomes a key into a boot-registered CallableRegistry; importlib removed from dispatch"
metrics:
  duration: ~35 min
  completed: 2026-07-26
  tasks: 3
  commits: 3
---

# Phase 06 Plan 03: D-19 local_callable Control Summary

Replaced dotted-path import resolution of `LocalCallableBinding.callable_ref` with a
boot-registered callable table, closing the IN-06 / T-05-18 remote-code-execution gate
that Phase I.2 deliberately deferred to I.3. `importlib` is gone from
`src/ccf/skills/`; a catalog entry naming `os.system` now resolves to nothing because
nothing registered that key, and no module is imported on the way to that answer.

## What Was Built

**Task 1 — `CallableRegistry`** (`src/ccf/skills/callables.py`, commit `d3e1fb1`).
A structural port of `src/ccf/operators/registry.py`, which is what D-IMPL-37 already
ruled for operators: explicit `register(key, fn)` at the composition root, no
decorators and no import side effects; append-only with no `unregister`, no overwrite,
and `DuplicateCallableKey` fatal at registration rather than last-writer-wins;
`resolve` raising `CallableNotRegistered` with `from None`; `keys()` returning
`tuple(sorted(...))`; `__contains__` / `__len__`. `SkillCallable` is typed to exactly
the shape dispatch already invoked (`Mapping[str, str] -> Mapping[str, str]`) rather
than a newly invented one. Algorithmic module, sorted `__all__`, no keys or domain
values of its own (CINV-01).

**Task 2 — dispatch routed through the registry** (commit `2c6f31e`).
`_invoke_local_callable` takes an injected `CallableRegistry` (keyword-only, never a
module global) and resolves `binding.callable_ref` through it; `import importlib` is
deleted. The registry threads `AgentFactory(callable_registry=...)` → `Agent` →
`dispatch_skill`, constructor injection at the composition root in the same shape
`OperatorRegistry` uses (`ProjectionEngine(registry=...)`). `None` is a positive
statement — this deployment registered no callables, so every `local_callable` entry
resolves to nothing, without an import.

Three docstrings amended in the same change so no stale claim survives it: the
`dispatch.py` module bullet, `_invoke_local_callable`'s "Accepted risk" block (replaced
by a statement of the resolved property), and `catalog.py`'s `LocalCallableBinding`
("a dotted callable reference" → a registry key, with the explicit note that the field
name and `str` type are unchanged so no artifact schema version breaks). The
`NotYetBound` tail for `mcp`/`a2a` was left untouched for 06-06 and 06-10 (D-05). The
refusal-vs-exception line is preserved: an unregistered key is an exception (broken
wiring or hostile artifact — the deployment is wrong), not a returned governance
refusal.

**Task 3 — fixtures, tests, decision** (commit `aa01eb6`).
The banking `covenant-metrics-local` entry's `callable_ref` becomes the key
`covenant-metrics` (artifact_version 1.1.0 → 1.2.0 — a binding value change is a
content change, D-05 — with the `metrics_local` grant in `grants.yaml` re-pinned to
match). `tests/conftest.py` gains a `callable_registry` fixture that performs one
explicit `register(key, fn)` call, standing in for a deployment's composition root; the
key is a fixture *value* read from the skills YAML, so test code stays generic.

`tests/skills/test_callables.py` (5 tests):
duplicate-key registration is fatal; an unregistered key resolves to nothing;
`test_a_third_party_catalog_entry_naming_os_system_resolves_to_nothing` dispatches a
structurally-valid hostile entry and asserts both the `CallableNotRegistered` refusal
and that `sys.modules` is unchanged across the call;
`test_the_refusal_is_absence_not_a_denylist` pins that the hostile ref and an
unremarkable absent key are refused by one mechanism (the SDK ships no denylist, so
there is nothing to bypass); and the D-23 case,
`test_two_composition_roots_binding_one_key_cannot_shadow_each_other`, registers the
same key to different callables in two registries and asserts each dispatch resolves to
its own. `tests/skills/test_dispatch.py` was updated to drive the injected registry and
still passes — the migration changed resolution, not behavior.

`D-IMPL-54` appended to `docs/DECISIONS.md` in the surrounding format, and
`docs/PHASE_I2_GATE.md` §5's IN-06 deferral paragraph now carries a RESOLVED marker
pointing at it (left standing as the I.2 record, explicitly not as a live claim).

## Verification

| Check | Result |
| --- | --- |
| `pytest -q` (full suite) | 632 passed, 2 skipped |
| `pytest tests/skills/ -q` | 70 passed |
| `pytest tests/skills/test_callables.py -k os_system` | 1 passed |
| `pytest tests/skills/test_callables.py -k 'two or multi or separate'` | 1 passed |
| `mypy` | Success, 66 source files |
| `python -m tools.lints --all` | exit 0 |
| `grep -rn importlib src/ccf/skills/` | no matches |
| `grep -n 'Accepted risk' src/ccf/skills/dispatch.py` | no matches |
| `grep -c 'dotted callable reference' src/ccf/skills/catalog.py` | 0 |
| `grep -n NotYetBound src/ccf/skills/dispatch.py` | mcp/a2a tail present, unchanged |

Baseline before this plan was 627 passed / 2 skipped; +5 is exactly the new
`test_callables.py` suite, with no pre-existing test regressed.

## Deviations from Plan

**1. [Rule 3 — Blocking] Broke a latent `ccf.skills` ↔ `ccf.agents` import cycle**
- **Found during:** Task 3, on first collection of `tests/skills/test_callables.py`
- **Issue:** `src/ccf/skills/dispatch.py` imports `ccf.agents.errors.NotYetBound`, which
  executes `ccf/agents/__init__.py`, which imports `ccf.agents.agent`, which imported
  `ccf.skills.dispatch` at module level. Pre-existing, and invisible only because every
  existing importer happened to reach `ccf.agents` first. The new test module reaches
  `ccf.skills.dispatch` first and got `ImportError: partially initialized module`. An
  import graph whose success depends on which module a caller reached first is the same
  class of non-determinism D-IMPL-37 rejects for registries.
- **Fix:** `agent.py` now imports `SkillInvocation` / `ToolInvocation` under
  `TYPE_CHECKING` (the annotations are already strings via
  `from __future__ import annotations`) and imports `dispatch_skill` at call time inside
  `invoke_skill`, with the reason stated inline. No behavior change; no public API change.
- **Files:** `src/ccf/agents/agent.py`
- **Commit:** `aa01eb6`

**2. [Rule 3 — Blocking] `ALLOWED_CCF_PREFIXES` widened to admit `ccf.skills.callables`**
- **Found during:** Task 3, `tests/agents/test_consumption_discipline.py` (AGNT-01)
- **Issue:** The agents package's permitted `ccf` import surface is an explicit
  allowlist; the new registry import in `agent.py` and `factory.py` failed it.
- **Fix:** Added `"ccf.skills.callables"` with a rationale comment, same tier as the
  already-permitted `ccf.skills.catalog` / `ccf.skills.dispatch`. AGNT-01 is intact:
  `ccf.skills.callables` has an empty `ccf` import surface (its only imports are
  `collections.abc`), so it opens no path from `Agent` to L1–L5. It is on the list
  precisely *because* dispatch no longer resolves callables by importing what a ref names.
- **Files:** `tests/agents/test_consumption_discipline.py`
- **Commit:** `aa01eb6`

**3. [Rule 2 — Coherence] `docs/PHASE_I2_GATE.md` §5 marked RESOLVED**
- Not in the plan's file list, but leaving §5's "this is a deliberate deferral" standing
  as an unqualified live claim after closing it is exactly the T-06-10 repudiation threat
  the plan's own register names. A four-line RESOLVED marker was added; the original
  paragraph is preserved as the I.2 record.

**Plan/criterion conflict resolved in favor of the criterion:** Task 1's action text asked
the doctrine block to state that "the module contains no `importlib`", while its
acceptance criterion required `grep -c importlib src/ccf/skills/callables.py` to be 0.
The doctrine block makes the same claim without naming the token ("neither this module nor
dispatch imports anything to answer, and neither resolves a dotted path"), so both hold.

**Fixture version bump not spelled out in the plan:** migrating `callable_ref` from a
module path to a key is a binding content change, so the entry took an `artifact_version`
bump under D-05 and `grants.yaml`'s `metrics_local` grant was re-pinned from 1.1.0 to
1.2.0. Grants name an exact entry version by design; a silent follow would have been the
defect.

## Threat Register Disposition

| Threat ID | Disposition | Evidence |
| --- | --- | --- |
| T-06-08 (carries T-05-18 / IN-06) | mitigated | `importlib` absent from `src/ccf/skills/`; `test_a_third_party_catalog_entry_naming_os_system_resolves_to_nothing` asserts refusal *and* an unchanged `sys.modules` |
| T-06-09 | mitigated | `DuplicateCallableKey` fatal at registration; no `unregister`/`clear`/overwrite on the registry; `test_two_composition_roots_binding_one_key_cannot_shadow_each_other` |
| T-06-10 | mitigated | Three docstrings amended in the same commit as the guard, plus the `PHASE_I2_GATE.md` §5 marker; D-IMPL-54 logged |
| T-06-11 | accepted (unchanged) | A registered callable is code the composition root chose to offer; execution-time resource governance is deployment infrastructure (CLAUDE.md §13). Stated in D-IMPL-54 as a residual rather than omitted |
| T-06-SC | n/a | No package installs in this plan |

## Known Stubs

None.

## Threat Flags

None. The change removes a code-execution surface and adds no network, auth, file-access,
or schema surface. `callable_ref`'s name and `str` type are unchanged, so the artifact
schema lane does not move.

## Notes for Downstream Plans

- **The D-19 gate is closed.** Plans 06-06 (MCP) and 06-10 (A2A) may admit non-fixture
  catalog sources: a `callable_ref` arriving over either transport is a key, and a key
  the local composition root did not register resolves to nothing.
- **Composition roots must now register callables.** Any deployment (including future
  examples and the harness adapters) that wants `local_callable` dispatch must construct
  a `CallableRegistry`, register its callables, and pass it to `AgentFactory`. Omitting
  it is safe, not broken: nothing registered means nothing dispatchable.
- **`dispatch_skill` signature changed** — `callable_registry` is a required keyword.
  Any new call site must supply one.
- **The dispatch-side `NotYetBound` tail is untouched** and is still where 06-06/06-10
  plug their transports in (D-05).

## Self-Check: PASSED

- `src/ccf/skills/callables.py` — FOUND
- `tests/skills/test_callables.py` — FOUND
- `src/ccf/skills/dispatch.py` — FOUND (modified, no `importlib`)
- `docs/DECISIONS.md` — FOUND (contains `D-IMPL-54`)
- Commit `d3e1fb1` (CallableRegistry) — FOUND
- Commit `2c6f31e` (dispatch migration) — FOUND
- Commit `aa01eb6` (fixtures, tests, decision) — FOUND
