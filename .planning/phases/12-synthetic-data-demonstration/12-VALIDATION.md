---
phase: 12
slug: synthetic-data-demonstration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-01
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, 1479 tests) |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/examples/ -x -q` |
| **Full suite command** | `make examples && python -m pytest -q` |
| **Estimated runtime** | ~330 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/examples/ -x -q`
- **After every plan wave:** Run `make examples && python -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*To be filled by planner from RESEARCH.md Validation Architecture — one row per task with automated command per DEMO-01..03.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| — | — | — | DEMO-01 | — | deterministic generation (pinned checksum) | unit | TBD by planner | ❌ W0 | ⬜ pending |
| — | — | — | DEMO-02 | — | end-to-end example run + baseline contrast | integration | TBD by planner | ❌ W0 | ⬜ pending |
| — | — | — | DEMO-03 | — | CI single-command run, deterministic | integration | TBD by planner | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test stubs for the new example (checksum pin, end-to-end run) — planner assigns exact paths
- [ ] Existing pytest infrastructure covers framework needs (no installs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Walkthrough doc reads correctly / narration quality | DEMO-03 | Prose quality is human judgment | Read the walkthrough doc end-to-end; verify literal-includes resolve |
