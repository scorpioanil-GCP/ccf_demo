---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 17
subsystem: orchestration
gap_closure: true
requirements: [ORCH-01]
tags: [workflow-engine, debt-cascade, fail-closed, tdd, d-impl-65, d-impl-66]
dependency_graph:
  requires:
    - runtime/ccf_runtime/workflow/engine.py (WorkflowEngine, _advance agent branch)
    - src/ccf/halflife/debt.py (DebtAssessment, DebtSignal)
  provides:
    - DebtAssessmentBinding Protocol (per-agent-handoff D_c seam)
    - UnboundDebtAssessmentError (typed WorkflowWiringError refusal)
    - engine-enforced fail-closed routing at agent handoffs (INV-CH7-68)
  affects:
    - tests/workflow/* engine construction sites
    - tests/http_api/conftest.py
tech-stack:
  added: []
  patterns:
    - runtime_checkable Protocol seam bound at the composition root
    - band vocabulary read from DebtSignal only — no threshold in engine (CINV-01)
key-files:
  created:
    - tests/workflow/test_debt_handoff.py
  modified:
    - runtime/ccf_runtime/workflow/engine.py
    - tests/workflow/test_engine.py
    - tests/workflow/test_engine_stateful.py
    - tests/workflow/test_exception_paths.py
    - tests/http_api/conftest.py
    - docs/DESIGN.md
decisions:
  - "Breach predicate is `signal is DebtSignal.FAIL_CLOSED` (not `is not OK`): DESIGN.md §4 names *fail-closed routing* for the handoff breach, and DebtSignal's own docstring forbids collapsing FORCED_LLM (more reasoning, proceed with awareness) into FAIL_CLOSED (no decision). The field reused is the assessment's signal band — no numeric threshold re-derived."
  - "cli/local.py --local composition root deliberately left with debt_binding=None: the honest-empty-seam doctrine (D-IMPL-38) — an agent handoff there now raises the typed unbound refusal instead of routing an accidental exception."
  - "tests/workflow/test_engine.py `_engine` helper defaults to a permissive stub binding (debt=True) so pre-existing claims run unchanged; the red test passes debt=False explicitly to construct the unbound engine."
metrics:
  duration: ~15 minutes
  completed: 2026-07-31
  tasks: 3
  tests: 1285 passed / 0 failed / 0 skipped
---

# Phase 7 Plan 17: Engine-Enforced Debt Assessment at Agent Handoffs Summary

Engine now refuses unbound-debt agent handoffs with typed `UnboundDebtAssessmentError` and drives per-handoff D_c assessment through a `DebtAssessmentBinding` Protocol, routing Fail-Closed breaches into the node's exception path before `run_agent` — D-IMPL-65's committed scope, red-test-first.

## What Was Built

- **`DebtAssessmentBinding`** (`runtime/ccf_runtime/workflow/engine.py`) — `@runtime_checkable` Protocol beside the two node-binding Protocols: `async def assess(*, tenant, step_name, ref) -> DebtAssessment`. The composition root binds it onto `ccf.halflife.debt.assess_debt` against the Control Plane's debt-profile artifact; the engine holds no profile and no threshold (CINV-01).
- **`UnboundDebtAssessmentError(WorkflowWiringError)`** — raised (I.1 refusal doctrine: broken deployment) when an agent node is reached on an engine constructed with `debt_binding=None`.
- **Enforcement in `_advance`'s agent branch** — before the try/except and before `run_agent`: unbound → raise; bound → `await assess(...)`; `signal is DebtSignal.FAIL_CLOSED` → `_route_exception` for the node without invoking the agent (declared ref → `WorkflowExceptionRouted`; absent ref → reserved `failed` terminal per D-IMPL-61 option-a, audited as today).
- **Tests** (`tests/workflow/test_debt_handoff.py`) — R1 unbound refusal, R2 skill-only scoping, G1 assessed-once-per-handoff with `(tenant, step_name, ref)`, G2 breach-routed with declared ref and with absent ref, both asserting `run_agent` call count 0.
- **DESIGN.md §4** — INV-CH7-68 correction note gains the 7.1 status sentence; the 07-14 historical correction is preserved, not deleted.

## R1 Red Output (verbatim, before Task 2)

```
ImportError while importing test module '.../tests/workflow/test_debt_handoff.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/workflow/test_debt_handoff.py:41: in <module>
    from ccf_runtime.workflow.engine import (
E   ImportError: cannot import name 'UnboundDebtAssessmentError' from 'ccf_runtime.workflow.engine' (.../runtime/ccf_runtime/workflow/engine.py)
```

Failure reason recorded per plan: the symbols did not exist — the handoff previously proceeded with no assessment.

## Task Commits

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Red test — unbound-debt agent handoff must be refused | 6199364 |
| 2 | DebtAssessmentBinding seam + engine enforcement | 0f0c48b |
| 3 | Full-suite sweep + DESIGN.md §4 status line | f1738e3 |

## Verification

- `pytest -q` (CCF_REQUIRE_HARNESSES=1): **1285 passed / 0 failed / 0 skipped** (baseline 1280; sibling plans add tests in parallel — treated as normal)
- `mypy --strict src runtime tools`: clean (164 files)
- `python -m tools.lints --all`: exit 0
- `grep -c "class UnboundDebtAssessmentError(WorkflowWiringError)" runtime/ccf_runtime/workflow/engine.py` → 1
- `grep -v '^#' runtime/ccf_runtime/workflow/engine.py | grep -c "DebtProfile"` → 0 (no profile import, no threshold)
- `__all__` gains `DebtAssessmentBinding` and `UnboundDebtAssessmentError`
- `grep -c "UnboundDebtAssessmentError" docs/DESIGN.md` → 1

## Deviations from Plan

### Interpretive resolutions (documented, no scope change)

**1. Breach predicate scoped to FAIL_CLOSED, not signal-is-not-OK**
- **Found during:** Task 2
- **Issue:** `ExceptionEscalation` treats any non-OK signal as escalation-worthy, but the plan's must-have truth and DESIGN.md §4 both name *Fail-Closed* routing at the handoff, and `DebtSignal`'s docstring says collapsing FORCED_LLM into FAIL_CLOSED "would make an outage indistinguishable from a hard question."
- **Resolution:** Reused the same field (`DebtAssessment.signal`) with the FAIL_CLOSED band as the routing condition. No threshold vocabulary invented; the band is the DebtProfile artifact's statement.

**2. `_engine` test helper defaults to a bound permissive stub**
- **Found during:** Task 2
- **Issue:** Every pre-existing covenant-workflow test reaches the agent node; without a binding they would all raise the new refusal.
- **Fix:** `_engine(..., debt=True)` default with `_PermissiveDebt` stub; the red test constructs the unbound engine explicitly with `debt=False`. `tests/http_api/conftest.py` got its own local stub (no cross-suite import).

**3. `cli/local.py` left unbound intentionally**
- The `--local` dev fabric's seams are "honest empty forms" (D-IMPL-38); an unbound debt seam raising the typed refusal on an agent handoff is that doctrine, not a regression. No code change made there.

Threshold-carrying return type existed (`DebtAssessment.signal`), so the plan's STOP condition (no usable disposition field) never triggered.

## Known Stubs

None — the permissive test stubs are test doubles for the composition-root seam, which is the designed production shape.

## Threat Flags

None — no new surface beyond the plan's threat model. T-07.1-08 and T-07.1-09 mitigations landed as specified (refusal before handoff; breach routing through the audited `_route_exception` path).

## Self-Check: PASSED

- FOUND: tests/workflow/test_debt_handoff.py
- FOUND: runtime/ccf_runtime/workflow/engine.py (DebtAssessmentBinding, UnboundDebtAssessmentError)
- FOUND commits: 6199364, 0f0c48b, f1738e3
