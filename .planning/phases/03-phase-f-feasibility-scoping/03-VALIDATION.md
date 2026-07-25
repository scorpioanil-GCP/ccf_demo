---
phase: 3
slug: phase-f-feasibility-scoping
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-25
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — docs-only phase; verification is mechanical document checking (`grep`/`diff`) |
| **Config file** | none — no Wave 0 needed |
| **Quick run command** | `grep`-based checks per requirement (see map below) |
| **Full suite command** | run all four requirement checks below in sequence |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run the `grep`/`diff` check for the requirement the task addresses
- **After every plan wave:** Run all four requirement checks
- **Before `/gsd:verify-work`:** All four checks must pass
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD at planning | — | — | FEAS-01 | — | N/A | doc-check | key-diff appendix matrix INV keys vs `docs/SPEC_INVENTORY.md` (empty diff); grep verdict column for empty cells | ✅ | ⬜ pending |
| TBD at planning | — | — | FEAS-02 | — | N/A | doc-check | cross-check milestone names vs `.planning/ROADMAP.md` phases 4–8; grep deferral register for 5 mandatory items | ✅ | ⬜ pending |
| TBD at planning | — | — | FEAS-03 | — | N/A | doc-check | row count vs 7 named invariants + D-08/D-09 rows; grep gate table for 12 D-IMPL IDs each RESOLVED with DECISIONS.md refs | ✅ | ⬜ pending |
| TBD at planning | — | — | FEAS-04 | — | N/A | manual + doc-check | review output exists; `grep D-GATE-F docs/DECISIONS.md`; `git log main` shows --no-ff merge | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no test framework needed (docs-only phase).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dave approval of Phase F deliverables | FEAS-04 | Approval authority is Dave's alone (CLAUDE.md §3.1) | Present FEASIBILITY.md, ROADMAP.md, review report + triage; log `D-GATE-F` in docs/DECISIONS.md upon approval |
| Cross-AI review triage quality | FEAS-04 | Blocking-vs-advisory classification requires judgment | Run `/gsd-review --phase Phase F --all`, classify each finding, fix blocking items in-phase |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (doc-check commands defined per requirement)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — no infra needed)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
