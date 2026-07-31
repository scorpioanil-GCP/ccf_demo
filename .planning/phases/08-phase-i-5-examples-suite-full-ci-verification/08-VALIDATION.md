---
phase: 8
slug: phase-i-5-examples-suite-full-ci-verification
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-30
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — 1315 tests green at Phase 7 close) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=120 -k "<touched area>"` |
| **Full suite command** | `python -m pytest tests/ -q && python -m mypy --strict src runtime` |
| **Estimated runtime** | ~90 seconds full suite |

---

## Sampling Rate

- **After every task commit:** Run quick command scoped to touched area
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green, all 8 examples run end-to-end via their documented commands
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

*(Filled by planner — one row per task; example commands (`make example-NN` or documented single command per example) count as automated verification.)*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01.1 | 01 | 1 | EXAM-09 | — | — | build | `make lint && make typecheck` | ✅ | ⬜ pending |
| 08-01.2 | 01 | 1 | EXAM-09 | T-08-01 | CINV-01 covers examples; CINV-02 src-only | unit | `pytest tests/lints/test_examples_scope.py -q` | ❌ W0 | ⬜ pending |
| 08-02.1 | 02 | 2 | EXAM-06 | — | one HITL verb (D-15) | unit | `pytest tests/cli -q` | ✅ flip | ⬜ pending |
| 08-02.2 | 02 | 2 | EXAM-06 | T-08-02..04 | fail-closed grant; typed error codes | unit | `pytest tests/http_api tests/hitl tests/cli -q` | ❌ new | ⬜ pending |
| 08-03.1 | 03 | 2 | EXAM-06 | T-08-05..07 | signed-binding requiredness (D-16) | unit | `pytest tests/hitl -q` | ❌ new | ⬜ pending |
| 08-03.2 | 03 | 2 | EXAM-06 | T-08-06 | R1 was-called derivation | unit | `pytest tests/hitl/test_was_called_derivation.py -q` | ❌ new | ⬜ pending |
| 08-04.1 | 04 | 2 | EXAM-04 | T-08-09 | ADK migration, behavior preserved | conformance | `pytest tests/conformance/test_orchestration.py -q` | ✅ | ⬜ pending |
| 08-04.2 | 04 | 2 | EXAM-04 | T-08-08 | doc notes | grep | `grep` assertions (plan 08-04) | ❌ | ⬜ pending |
| 08-05.* | 05 | 3 | EXAM-01 | T-08-10 | artifacts-only domain values | e2e | `make example-00` | ❌ | ⬜ pending |
| 08-06.1 | 06 | 3 | EXAM-02 | — | factory-only, six axes | e2e | `make example-01` | ❌ | ⬜ pending |
| 08-06.2 | 06 | 3 | EXAM-03 | T-08-12/13 | governance refusal + replay capture | e2e | `make example-02` | ❌ | ⬜ pending |
| 08-07.* | 07 | 3 | EXAM-05 | T-08-14..16 | admission verification + refusal | e2e | `make example-04` | ❌ | ⬜ pending |
| 08-08.1 | 08 | 3 | EXAM-06 | T-08-17/18 | auth-bound HITL door, signed binding | e2e | `make example-05` | ❌ | ⬜ pending |
| 08-08.2 | 08 | 3 | EXAM-07 | T-08-19 | exact-version replay, no @latest | e2e | `make example-06` | ❌ | ⬜ pending |
| 08-09.* | 09 | 3 | EXAM-08 | T-08-21/22 | config-only store swap | e2e | `make example-07` | ❌ | ⬜ pending |
| 08-10.1 | 10 | 3 | EXAM-04 | T-08-23/25 | 3-harness byte equivalence, no model | e2e | `make example-03` | ❌ | ⬜ pending |
| 08-10.2 | 10 | 3 | EXAM-04 | T-08-24 | A3 discharge (real ResultMessage) | conformance | `pytest tests/conformance/test_a3_discharge.py -q` | ❌ new | ⬜ pending |
| 08-11.1 | 11 | 4 | EXAM-04 | T-08-26/27 | live legs wired, no key literals | lint/import | plan 08-11 smoke + `make lint` | ❌ | ⬜ pending |
| 08-11.2 | 11 | 4 | EXAM-04 | T-08-27 | structural equivalence (D-04) | e2e opt-in | `make example-03-live-ollama` (manual) | ❌ manual | ⬜ pending |
| 08-12.1 | 12 | 5 | EXAM-09 | T-08-28/29 | CI shape D-10/D-11, no continue-on-error | config | yaml-parse assertion (plan 08-12) | ❌ | ⬜ pending |
| 08-12.2 | 12 | 5 | EXAM-09 | — | full sweep green | e2e | `make ci` | ❌ | ⬜ pending |
| 08-13.* | 13 | 6 | EXAM-09 | T-08-30/31 | gate ordering §3.1 | gate | `make ci` + git tag assertions | protocol | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `Makefile` (or documented per-example run commands) — examples runner targets
- [ ] Exit-code `make example-NN` targets — CI-invocable end-to-end runs of examples 00–07 (no separate `tests/examples/` pytest harness; the Makefile targets ARE the harness)
- [ ] CI `examples` job in `.github/workflows/ci.yml`

*Existing pytest infrastructure covers unit/invariant requirements; the examples e2e runner is realized as net-new exit-code `make example-NN` targets wired into the CI `examples` job.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Ollama harness legs on GH Actions | EXAM (03 live legs) | Local model availability differs from runners; opt-in workflow | Run opt-in workflow / local `make example-03-live` with Ollama serving |
| GH Actions green evidence | EXAM-09 | Push authorization gated (flagged for Dave) | Push branch once authorized; observe Actions run |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
