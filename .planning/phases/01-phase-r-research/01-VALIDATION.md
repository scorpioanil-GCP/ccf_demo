---
phase: 1
slug: phase-r-research
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-24
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — docs-only phase; validation is structural (grep/section-count checks) |
| **Config file** | none — Wave 0 installs nothing |
| **Quick run command** | `grep`-based checklist diffs against verified section/figure/D-NN lists (see RESEARCH.md) |
| **Full suite command** | §16 element-by-element audit of `docs/SPEC_INVENTORY.md` + `/gsd-review --phase "Phase R" --all` |
| **Estimated runtime** | ~60 seconds (mechanical checks) |

---

## Sampling Rate

- **After every task commit:** Run the task's own structural checklist (e.g., chapter subsection list fully ticked)
- **After every plan wave:** Re-run coverage diffs (36 subsections, 50 figures, 41 D-NN) against inventory sections written so far
- **Before `/gsd:verify-work`:** Full §16 audit green + `/gsd-review` clean of blocking findings
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | — | — | RSCH-01 | — | N/A | structural | grep-diff inventory refs vs 36-subsection list | ❌ W0 | ⬜ pending |
| (filled by planner) | — | — | RSCH-02 | — | N/A | structural | heading check + counts (50 figures, 41 D-NN) | ❌ W0 | ⬜ pending |
| (filled by planner) | — | — | RSCH-03 | — | N/A | manual+structural | every appendix entry carries an inherit/do-not-inherit marker | ❌ W0 | ⬜ pending |
| (filled by planner) | — | — | RSCH-04 | — | N/A | procedural | every open question references a D-IMPL-NN; §3.1 steps in order | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Placeholder docs (`docs/SPEC_INVENTORY.md`, `docs/DECISIONS.md`) and section checklists created

*No test-framework installs — docs-only phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF conversion fidelity (D-03 spot-check) | RSCH-01 | Glyph corruption / ligature loss only visible by eye | Per-section heading/figure/table/signature comparison vs source PDF pages |
| Homecams appendix marker judgment | RSCH-03 | Inherit vs do-not-inherit classification requires domain judgment | Review each appendix entry against CLAUDE.md §2.1 boundary |
| Dave approval gate | RSCH-04 | Approval authority is Dave's alone (§3.1) | Present inventory + review report + triage; log `D-GATE-R` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
