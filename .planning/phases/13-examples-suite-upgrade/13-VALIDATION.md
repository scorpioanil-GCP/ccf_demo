---
phase: 13
slug: examples-suite-upgrade
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-02
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing `tests/` tree) + Make-driven example runs |
| **Config file** | existing repo config (no change) |
| **Quick run command** | `make example-NN && make lint` (per touched example) |
| **Full suite command** | `make ci` (= ci-core + all nine examples) |
| **Estimated runtime** | quick ~seconds per example; `make ci` minutes |

---

## Sampling Rate

- **After every task commit:** Run `make example-NN && make lint` for the touched example
- **After every plan wave:** Run `make examples`
- **Before `/gsd:verify-work`:** `make ci` must be green
- **Max feedback latency:** seconds (per-example run + lint)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | EXAM-01 | — | N/A | source assertion | `test -f .planning/phases/13-examples-suite-upgrade/13-README-TEMPLATE.md` | ✅ | ⬜ pending |
| 13-02-01 | 02 | 2 | EXAM-01/02/03 | — | N/A | smoke | `make example-00 && make lint` | ✅ | ⬜ pending |
| 13-02-02 | 02 | 2 | EXAM-01/02/03 | — | N/A | smoke | `make example-01 && make lint` | ✅ | ⬜ pending |
| 13-03-01 | 03 | 2 | EXAM-01/02/03 | — | N/A | smoke | `make example-02 && make lint` | ✅ | ⬜ pending |
| 13-03-02 | 03 | 2 | EXAM-01/02/03 | — | N/A | smoke + conformance | `make example-03 && pytest tests/conformance/test_harness_portability.py` | ✅ | ⬜ pending |
| 13-03-03 | 03 | 2 | EXAM-01/02/03 | — | N/A | smoke | `make example-04 && make lint` | ✅ | ⬜ pending |
| 13-04-01 | 04 | 2 | EXAM-01/02/03 | T-13-* | Phase-10 auth posture preserved (deny-by-default 403) | smoke | `make example-05 && make lint` | ✅ | ⬜ pending |
| 13-04-02 | 04 | 2 | EXAM-01/02/03 | T-13-* | Phase-10 auth posture preserved | smoke | `make example-06 && make lint` | ✅ | ⬜ pending |
| 13-05-01 | 05 | 3 | EXAM-01/02/03 | — | N/A | smoke | `make example-07 && make lint` | ✅ | ⬜ pending |
| 13-05-02 | 05 | 3 | EXAM-01/03 | — | N/A | e2e phase gate | `make ci` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework, config, or stubs needed. (The Wave-1 shared README template + gloss table is a content prerequisite, not a test-infrastructure gap.)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README prose quality (narration teaches, adapt-it guidance is actionable) | EXAM-01 | Prose quality is judgment, not assertion; heading structure IS automated via `grep -c '^## '` checks in task acceptance | Read each README against the D-02 template; confirm the seven sections and the code/artifact boundary are legible |
| Expected-output changes are reviewed, deliberate events | EXAM-03 | D-09 commit-per-example review is process | Confirm each example's commit body summarizes its expected-output delta |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none)
- [x] No watch-mode flags
- [x] Feedback latency: seconds per task (quick command)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-02
