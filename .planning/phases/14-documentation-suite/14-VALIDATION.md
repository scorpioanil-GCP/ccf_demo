---
phase: 14
slug: documentation-suite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Populated by the planner from `14-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) + `mkdocs build --strict` as an executable gate |
| **Config file** | `pyproject.toml` (pytest), `mkdocs.yml` (Wave 0 creates) |
| **Quick run command** | `{planner fills — targeted pytest selection}` |
| **Full suite command** | `{planner fills — full pytest + make docs}` |
| **Estimated runtime** | ~{N} seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick command
- **After every plan wave:** Run the full suite
- **Before `/gsd:verify-work`:** Full suite green AND `mkdocs build --strict` green
- **Max feedback latency:** {N} seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {planner fills} | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Per research, Wave 0 must land before any drift gate can go green:

- [ ] `mkdocs.yml` — with `check_paths: true` (D-08) and raised `validation.links.*` levels
- [ ] `public/` tree + `docs` dependency extra in `pyproject.toml`
- [ ] `site/` added to `.gitignore`
- [ ] Docstring rework for the 13 verbatim-whitepaper-quoting docstrings (blocks the first green publish scan)
- [ ] Negative-control test fixtures for each drift gate

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| {planner fills} | | | |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < {N}s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
