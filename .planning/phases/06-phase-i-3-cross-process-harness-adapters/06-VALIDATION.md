---
phase: 6
slug: phase-i-3-cross-process-harness-adapters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-26
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `06-RESEARCH.md` § Validation Architecture, which carries the
> full requirement→test map and the five-success-criteria coverage rows.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest==9.1.1` + `hypothesis==6.161.5` — already wired |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Async style** | plain `asyncio.run()` inside sync tests — existing repo pattern (`tests/integration/test_cdc_slice.py:182`); no async plugin added |
| **Quick run command** | `python -m pytest tests/<area> -x -q` |
| **Full suite command** | `python -m pytest -q && python -m tools.lints --all && python -m mypy` |
| **Estimated runtime** | ~full suite baseline (627 pass / 2 skip at `D-GATE-I.2`) plus this phase's additions |
| **New markers** | `crossproc` (spawns subprocesses), `harness` (requires a harness extra) — added to `[tool.pytest.ini_options] markers`, matching the existing `postgres` / `chroma` / `conformance` precedent |

---

## Sampling Rate

- **After every task commit:** `python -m pytest tests/<area> -x -q`
- **After every plan wave:** `python -m pytest -q && python -m tools.lints --all && python -m mypy`
- **Before `/gsd:verify-work`:** full suite green, all three lints green, mypy clean
- **Max feedback latency:** target < 60 s for the quick run

**Phase-specific sampling constraint:** cross-process tests (`crossproc`) must
never gate on a sleep (D-16). Any test whose readiness depends on wall-clock
delay is a defect, not a flake.

---

## Per-Task Verification Map

*Populated by the planner — one row per task across all plans.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _pending_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Requirement coverage source of truth:** `06-RESEARCH.md` § "Phase Requirements
→ Test Map" (XPRC-01, XPRC-02, XPRC-03) and § "Success-criteria coverage",
which gives criterion 4 (single-writer) one concrete observable per boundary —
A2A, adapter, and ArtifactStore — and writes out the D-18 governed vs
harness-attributable split as an assertion.

---

## Wave 0 Requirements

Per `06-RESEARCH.md` § "Wave 0 gaps". The slice (D-01) delivers the shared
cross-process fixture the rest of the phase depends on, so fixture creation is
Wave 0 work in practice:

- [ ] `tests/crossproc/conftest.py` — ephemeral-port (`bind(0)`) + stdout
      readiness-handshake fixture with guaranteed teardown (D-15, D-16); no sleeps
- [ ] `crossproc` and `harness` markers registered in `pyproject.toml`
- [ ] Negative lint test pinning the D-24 carve-out boundary — a harness import in
      `ccf_runtime.a2a` / `ccf_runtime.cdc` must still fail
- [ ] Harness-extra skip mechanism: a skipped leg must name which harness and
      which extra enables it (CONTEXT.md Claude's-Discretion constraint; I.1
      CINV-04 deferral-skip precedent)

*Existing infrastructure (pytest, hypothesis, the factory-parametrized
conformance-suite pattern at `tests/conformance/test_approval_sink.py`) covers
the remainder.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none identified_ | — | — | — |

*All phase behaviors have automated verification. Research verified every harness
seam executes with **zero LLM calls** (D-09), so no leg requires a model
credential or a human in the loop.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] No sleep-gated readiness in any `crossproc` test (D-16)
- [ ] Multi-principal case present for every set-identity / admission / replay
      claim over shared Control Plane state (D-23)
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
