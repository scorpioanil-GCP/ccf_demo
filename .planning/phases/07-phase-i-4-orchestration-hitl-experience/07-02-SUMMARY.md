---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 02
subsystem: controlplane
tags: [state-seam, audit, token-gate, D-20, D-08, D-09, D-10, D-22, D-23]
requires: []
provides:
  - "Token-gated ControlPlaneStateStore.put (StateWriteToken, keyword-only, mint-verified)"
  - "AuditedStateWriter — sole minting path; one caller-supplied domain AuditEvent per write"
  - "state_written AuditAction for callers with no domain semantics"
  - "GrantLedger retrofitted onto the audited write surface (D-09)"
  - "tests/invariants/test_state_seam_closure.py — adversarial + counterfactual proofs (D-10)"
affects: [07-06 workflow engine (multiplies put call sites against a closed seam)]
tech-stack:
  added: []
  patterns: ["AdmittedProduct-style module-private token with mint verification at the consuming signature"]
key-files:
  created:
    - tests/invariants/test_state_seam_closure.py
  modified:
    - src/ccf/controlplane/state.py
    - src/ccf/controlplane/audit.py
    - src/ccf/skills/grants.py
    - tests/controlplane/test_state.py
decisions:
  - "Audit policy implemented as fixed in-plan: AuditedStateWriter.write takes the caller's domain AuditEvent as a required parameter and appends exactly that one event; the log reassigns sequence (sequencing belongs to the log per its own stated contract) — no doubled entries, no lost transition evidence (INV-CH7-71)"
  - "Subclass-bypass defeated by mint verification at put (getattr on the module-private sentinel), not isinstance — an isinstance gate would admit a subclass skipping __init__"
metrics:
  duration: "~25 min"
  completed: "2026-07-30"
---

# Phase 07 Plan 02: D-20 State Seam Closure Summary

Token-gated `ControlPlaneStateStore.put` with `AuditedStateWriter` as the sole minting path — one caller-supplied domain AuditEvent per write, GrantLedger retrofitted, adversarial + counterfactual proofs recorded.

## What was built

- **Task 1 (TDD, commits 4ac88aa RED / 0ebdc79 GREEN):** `StateWriteToken` (module-private mint, `AdmissionBypassError` discipline from `peering/admission.py`), token required keyword-only on both `ControlPlaneStateStore.put` (Protocol) and `InMemoryStateStore.put`; `AuditedStateWriter(store=..., audit=...)` mints internally, writes, appends the caller's domain event to the one existing `AuditLog`; `state_written` added to `AuditAction` with doctrinal comment per the `skill_invoked` precedent. Module docstring carries the D-22-scoped wording ("public write surface" enforcement; reflection/private-construction residual named as lint/CI-covered) and states explicitly that reads remain unaudited.
- **Task 2 (commit 4660788):** `GrantLedger._put_state` retrofitted onto the audited surface; its existing domain transition event (`grant_requested`/`grant_pending_approval`/`grant_effective`/`grant_refused`/`grant_revoked`) travels as the write's required event. Adjacent `_record` calls folded in at all eight state-writing sites; `_record` retained only for the no-state-write catalog-miss refusal path.
- **Task 3 (commit 004a840):** `tests/invariants/test_state_seam_closure.py` — adversarial (direct call, forged kwarg, token construction, subclass skipping `__init__`) and counterfactual (token on both signatures, sole-minting-path, D-23 two-tenant) proofs.

## D-09 writer enumeration (execution-time grep)

`grep -rn "\.put(" src runtime` excluding `state.py`:

| Hit | Verdict |
|---|---|
| `src/ccf/skills/grants.py:515` (`_put_state`) | The sole `ControlPlaneStateStore.put` caller — retrofitted |
| `src/ccf/peering/admission.py:716` | `ArtifactStore.put` — different Protocol, not in scope |
| `src/ccf/replay/serve.py:130` | `ArtifactStore.put` — different Protocol, not in scope |
| `runtime/ccf_runtime/mcp/artifact_server.py:314` | `ArtifactStore.put` — different Protocol, not in scope |

Zero unmigrated `ControlPlaneStateStore.put` callers at plan end. Sole Protocol implementation: `InMemoryStateStore`.

## Deviations from Plan

**1. [D-24 stale-belief, pre-flagged] D-09 "8 grant call sites" count deviation** (gate document must carry this row — Ollama C3)
- **Found during:** Task 2 enumeration
- **Reality:** `grants.py` has exactly **one** textual `_state_store.put` site (`:515`, inside `_put_state`); eight *logical* transitions flow through it via eight `_put_state` call sites. All eight call sites were updated to carry their domain event; the single textual writer was retrofitted.
- **Commit:** 4660788

**2. [Rule 1-adjacent, minor] `AuditEvent.sequence` reassigned by the log**
- The plan's fixed policy says the audited surface "appends exactly that one event." `AuditLog.append` assigns sequence itself (its stated contract: callers cannot mis-number the log). The writer therefore appends the caller's event verbatim in every field *except* `sequence`, which the log assigns. Documented in `AuditedStateWriter.write` docstring and asserted field-by-field in tests. Not a second event; not a discrepancy requiring a stop — no doubling, no lost evidence.

No test deletions; no audit-count assertion changes were needed (event ordering and counts unchanged — the writer preserves the prior put-then-append order and one-event-per-transition count).

## Read-surface note (Gemini, in-plan requirement)

Assessed: `get` and `items` remain unaudited by scope of the ruling; the module docstring says so explicitly. **Open observation:** `items` does allow full unaudited *enumeration* of state (e.g., all grant states) — this reconstructs current state but not its history, and does not undermine the write-closure claim (nothing can *change* without a record). Recorded here rather than widening scope in-plan; a future ruling may extend read auditing.

## Counterfactual red output (D-10/D-25, verbatim — reverted closure, then restored)

`src/ccf/controlplane/state.py` reverted to base `2d62b01`, then `pytest tests/invariants/test_state_seam_closure.py -q`:

```
==================================== ERRORS ====================================
_________ ERROR collecting tests/invariants/test_state_seam_closure.py _________
ImportError while importing test module '/home/parkave/ccf_code/.claude/worktrees/agent-abdec5b0708b950d6/tests/invariants/test_state_seam_closure.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/invariants/test_state_seam_closure.py:27: in <module>
    from ccf.controlplane.state import (
E   ImportError: cannot import name 'AuditedStateWriter' from 'ccf.controlplane.state' (/home/parkave/ccf_code/.claude/worktrees/agent-abdec5b0708b950d6/src/ccf/controlplane/state.py)
=========================== short test summary info ============================
ERROR tests/invariants/test_state_seam_closure.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.11s
```

File restored; the same tests pass 7/7 on the closed seam.

## Verification

- `pytest` full suite: **1002 passed, 2 skipped**
- `mypy --strict src runtime`: clean (99 files)
- `tools.lints --all`: clean
- `grep -n "def put" src/ccf/controlplane/state.py`: token parameter on Protocol and InMemoryStateStore
- `grep -c tenant tests/invariants/test_state_seam_closure.py` = 9 (≥ 2); `grep public` present (D-22 scope statement)

## Commits

| Commit | Type | Content |
|---|---|---|
| 4ac88aa | test | RED — failing token-gate/audited-writer/two-tenant tests |
| 0ebdc79 | feat | GREEN — token-gated put + AuditedStateWriter + state_written action |
| 4660788 | feat | GrantLedger retrofit (D-09) |
| 004a840 | test | Seam-closure invariant proofs (D-10) |

## Self-Check: PASSED

- `src/ccf/controlplane/state.py` — FOUND (token + audited surface)
- `tests/invariants/test_state_seam_closure.py` — FOUND
- Commits 4ac88aa, 0ebdc79, 4660788, 004a840 — FOUND in log
- TDD gate compliance: test(4ac88aa) precedes feat(0ebdc79)
