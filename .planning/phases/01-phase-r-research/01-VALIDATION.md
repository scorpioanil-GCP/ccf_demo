---
phase: 1
slug: phase-r-research
status: planned
nyquist_compliant: true
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

- **After every task commit:** Run the task's own structural checklist (each PLAN task carries an `<automated>` grep gate)
- **After every plan wave:** Re-run coverage diffs (36 subsections, 50 figures, 41 D-NN) against inventory sections written so far
- **Before `/gsd:verify-work`:** Full §16 audit green + `/gsd-review` clean of blocking findings
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01/T1 | 01-01 | 1 | RSCH-04 | T-01-01 | no remote push | structural | git branch/gitignore greps (see plan) | ✅ | ⬜ pending |
| 01-01/T2 | 01-01 | 1 | RSCH-04 | — | N/A | structural | skeleton + placeholder existence tests | ✅ | ⬜ pending |
| 01-02/T1 | 01-02 | 2 | RSCH-01 | — | N/A | structural | 50-figure count, per-chapter counts | ✅ | ⬜ pending |
| 01-02/T2–T3 | 01-02 | 2 | RSCH-01 | — | N/A | structural | heading census Ch1–6, glyph-clean grep, Π/⇄ presence | ✅ | ⬜ pending |
| 01-03/T1–T2 | 01-03 | 3 | RSCH-01 | — | N/A | structural | 10 ×`### 7.x`, 28 ×CH07 placeholders, λ_c/D_c greps | ✅ | ⬜ pending |
| 01-04/T1 | 01-04 | 4 | RSCH-01 | — | N/A | structural | 13 ×`### 8.x`, 6 ×CH08, total 50 placeholders | ✅ | ⬜ pending |
| 01-04/T2 | 01-04 | 4 | RSCH-01 | — | D-03 fidelity | manual+structural | spotcheck-report `VERDICT: PASS`, placeholder-file resolution loop | ✅ | ⬜ pending |
| 01-05/T1–T2 | 01-05 | 5 | RSCH-01 | — | N/A | structural | §5.1–§6.6 citation loop greps on ch5-6 fragment | ✅ | ⬜ pending |
| 01-06/T1–T2 | 01-06 | 5 | RSCH-01 | — | N/A | structural | §7.1–7.4 citations, tenant_id / A(B(G)) verbatim greps | ✅ | ⬜ pending |
| 01-07/T1–T2 | 01-07 | 5 | RSCH-01 | — | N/A | structural | extra=forbid, three gates, λ_c greps on ch7b fragment | ✅ | ⬜ pending |
| 01-08/T1–T2 | 01-08 | 5 | RSCH-01 | — | N/A | structural | five replay-dimension name loop on ch7c fragment | ✅ | ⬜ pending |
| 01-09/T1–T2 | 01-09 | 5 | RSCH-01 | — | N/A | structural | Pattern 1–5 loop, §8.5–8.13 citation loop | ✅ | ⬜ pending |
| 01-10/T1 | 01-10 | 2 | RSCH-03 | — | N/A | manual+structural | Marker-column greps (both exact marker strings) | ✅ | ⬜ pending |
| 01-10/T2 | 01-10 | 2 | RSCH-03 | T-01-03 | no secrets committed | structural | `! grep mongodb:// && ! grep 192.168` gate | ✅ | ⬜ pending |
| 01-11/T1 | 01-11 | 6 | RSCH-01 | T-01-01 | no secrets in merge | structural | duplicate-INV-key uniq check, appendix presence | ✅ | ⬜ pending |
| 01-11/T2 | 01-11 | 6 | RSCH-02 | — | N/A | structural | 50 unique figure refs, D-NN gap list, pillar loop | ✅ | ⬜ pending |
| 01-11/T3 | 01-11 | 6 | RSCH-04 | — | N/A | structural | D-IMPL-30 presence, no unnumbered sections remain | ✅ | ⬜ pending |
| 01-12/T1 | 01-12 | 7 | RSCH-04 | — | N/A | procedural | triage report greps, Review Appendix presence | ✅ | ⬜ pending |
| 01-12/T2 | 01-12 | 7 | RSCH-04 | T-01-04 | Dave-only approval | manual (checkpoint) | human gate — "approved" resume signal | ✅ | ⬜ pending |
| 01-12/T3 | 01-12 | 7 | RSCH-04 | T-01-01 | no push without origin | structural | D-GATE-R grep in DECISIONS.md + main merge-log grep | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Placeholder docs (`docs/SPEC_INVENTORY.md`, `docs/DECISIONS.md`) and fragments dir created — covered by plan 01-01 (Wave 1)

*No test-framework installs — docs-only phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF conversion fidelity (D-03 spot-check) | RSCH-01 | Glyph corruption / ligature loss only visible by eye | Per-section heading/figure/table/signature comparison vs source PDF pages (plan 01-04 T2) |
| Homecams appendix marker judgment | RSCH-03 | Inherit vs do-not-inherit classification requires domain judgment | Review each appendix entry against CLAUDE.md §2.1 boundary (plan 01-10) |
| Dave approval gate | RSCH-04 | Approval authority is Dave's alone (§3.1) | Present inventory + review report + triage; log `D-GATE-R` (plan 01-12 T2) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — docs-only)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
