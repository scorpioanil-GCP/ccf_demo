---
phase: 2
slug: phase-d-design
status: final
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-25
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — docs-only phase; validation via grep/structural checks and `mmdc` diagram compilation |
| **Config file** | none — Wave 0 not required |
| **Quick run command** | `grep`-based structural assertions per task (see plan acceptance criteria) |
| **Full suite command** | `mmdc -i docs/diagrams/<file>.mmd -o /dev/null` for each diagram + inventory-coverage grep sweep |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's grep/structural acceptance checks
- **After every plan wave:** Re-run diagram compilation (`mmdc`) and inventory-coverage sweep
- **Before `/gsd:verify-work`:** All success-criteria greps green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (populated by planner) | — | — | DSGN-01..04 | — | N/A | structural | grep / mmdc | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (docs-only phase; `mmdc` verified available).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dave's approval of D-IMPL rulings and `D-GATE-D` | DSGN-02, DSGN-04 | Human decision authority per CLAUDE.md §2/§3.1 | Present deliverables + review report + triage; log approval in docs/DECISIONS.md |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
