---
phase: 4
slug: phase-i-1-fabric-core
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-25
updated: 2026-07-25
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + hypothesis 6.x (property tests) + testcontainers 4.x (Postgres conformance) |
| **Config file** | none — Wave 1 installs (`pyproject.toml` with pytest config, plan 04-01 Task 1) |
| **Quick run command** | `.venv/bin/pytest tests -x -q -m "not postgres and not chroma"` |
| **Full suite command** | `.venv/bin/pytest tests -q && .venv/bin/python -m tools.lints --all && .venv/bin/mypy --strict src` (CINV lints per D-06 layout) |
| **Estimated runtime** | ~60 seconds quick / ~300 seconds full (containers) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests -x -q -m "not postgres and not chroma"` + `.venv/bin/python -m tools.lints --all`
- **After every plan wave:** Run full suite including Postgres/Chroma legs, CINV lints, and `mypy --strict`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-T1 | 04-01 | 1 | CINV-01..03 (scaffold) | T-04-SC | venv-isolated installs, pinned deps | smoke | `git branch --show-current \| grep -qx phase-i1 && .venv/bin/pytest tests -q && .venv/bin/mypy --strict src` | ❌ W0 (this task creates it) | ⬜ pending |
| 04-01-T2 | 04-01 | 1 | CINV-01..03 (CI) | T-04-SC | lint jobs blocking in CI (D-07/D-09) | config check | `python -c "...ci.yml has lint+test jobs, postgres leg..."` | ❌ W0 | ⬜ pending |
| 04-01-T3 | 04-01 | 1 | governance sync (D-03, D-12) | — | — | doc grep | `grep -qi "horizontal mix" CLAUDE.md && grep -q "2026-07-25" docs/DECISIONS.md && grep -qi "Phase 6" .planning/ROADMAP.md` | ✅ | ⬜ pending |
| 04-02-T1 | 04-02 | 2 | CINV-02, CINV-03 | T-04-02 | harness/LLM import rejection | lint unit (TDD) | `.venv/bin/pytest tools/lints/tests/test_harness_imports.py tools/lints/tests/test_algorithmic.py -q` | ❌ W0→task creates | ⬜ pending |
| 04-02-T2 | 04-02 | 2 | CINV-01 | T-04-01 | prompt-literal rejection + allowlist | lint unit (TDD) | `.venv/bin/pytest tools/lints/tests/test_no_hardcoding.py -q` | ❌ task creates | ⬜ pending |
| 04-02-T3 | 04-02 | 2 | CINV-01..03 | — | clean-tree lint pass, CI green | lint runner | `.venv/bin/python -m tools.lints --all && .venv/bin/pytest tools/lints/tests -q` | ❌ task creates | ⬜ pending |
| 04-03-T1 | 04-03 | 2 | FABR-04 (base) | T-04-03 | `extra=forbid`, sha256 canonical identity | unit (TDD) | `.venv/bin/pytest tests/contracts -q && .venv/bin/python -m tools.lints --all` | ❌ task creates | ⬜ pending |
| 04-03-T2 | 04-03 | 2 | FABR-04, FABR-09 (types) | T-04-03 | boundary validation of envelopes/claims | unit + mypy | `.venv/bin/pytest tests/contracts -q && .venv/bin/mypy --strict src` | ❌ task creates | ⬜ pending |
| 04-03-T3 | 04-03 | 2 | FABR-07 (minimal) | T-04-05 | no-silent-default config resolution | unit | `.venv/bin/pytest tests/controlplane -q && .venv/bin/python -m tools.lints --all` | ❌ task creates | ⬜ pending |
| 04-04-T1 | 04-04 | 3 | FABR-01 | — | read/write Protocol split | conformance scaffold (TDD) | `.venv/bin/pytest tests/conformance/test_graphstore.py --collect-only -q` | ❌ task creates | ⬜ pending |
| 04-04-T2 | 04-04 | 3 | FABR-01 | T-04-04 | tenant-scoped unique index, append-only | conformance (SQLite) | `.venv/bin/pytest tests/conformance/test_graphstore.py -q` | ❌ prior task | ⬜ pending |
| 04-04-T3 | 04-04 | 3 | FABR-01, CINV-04 | T-04-04 | exactly-one-writer boot enforcement | invariant test | `.venv/bin/pytest tests/invariants/test_single_writer_boot.py tests/conformance -q && .venv/bin/mypy --strict src` | ❌ task creates | ⬜ pending |
| 04-05-T1 | 04-05 | 4 | FABR-02, FABR-03 (slice) | — | pure read-only operators | unit | `.venv/bin/pytest tests -q -m "not conformance" && .venv/bin/mypy --strict src` | ✅ (suite) | ⬜ pending |
| 04-05-T2 | 04-05 | 4 | FABR-04 | T-04-03 | three gates as only construction path | gate unit (TDD) | `.venv/bin/pytest tests/gates -q` | ❌ task creates | ⬜ pending |
| 04-05-T3 | 04-05 | 4 | FABR-06, FABR-08 (slice) | T-04-06 | replay write precedes delivery | integration | `.venv/bin/pytest tests/replay tests/integration -q && .venv/bin/pytest tests -q -m "not postgres and not chroma"` | ❌ task creates | ⬜ pending |
| 04-06-T1 | 04-06 | 5 | FABR-02 | — | declared-schema params, registry lookup | unit + mypy | `.venv/bin/pytest tests -q -m "not postgres and not chroma" && .venv/bin/mypy --strict src` | ✅ (suite) | ⬜ pending |
| 04-06-T2 | 04-06 | 5 | FABR-02 | — | `(A∘B)(G)=A(B(G))` all shipped pairs | property (Hypothesis) | `HYPOTHESIS_PROFILE=ci .venv/bin/pytest tests/properties/test_composition.py -q` | ❌ task creates | ⬜ pending |
| 04-06-T3 | 04-06 | 5 | FABR-03 | — | staged == direct (D-08 class 2) | property | `HYPOTHESIS_PROFILE=ci .venv/bin/pytest tests/properties -q` | ❌ task creates | ⬜ pending |
| 04-07-T1 | 04-07 | 5 | FABR-05 | T-04-05 | λ_c values from Control Plane only, missing-value fails | unit | `.venv/bin/pytest tests/halflife/test_decay.py -q && .venv/bin/python -m tools.lints --all` | ❌ task creates | ⬜ pending |
| 04-07-T2 | 04-07 | 5 | FABR-05 | T-04-05 | D_c thresholds gate Forced-LLM/Fail-Closed signals | unit | `.venv/bin/pytest tests/halflife -q` | ❌ task creates | ⬜ pending |
| 04-07-T3 | 04-07 | 5 | FABR-07 | T-04-05 | versioned registry, append-only audit plane | unit + regression | `.venv/bin/pytest tests/controlplane tests/halflife tests/gates -q && .venv/bin/mypy --strict src` | ✅ (suite) | ⬜ pending |
| 04-08-T1 | 04-08 | 5 | FABR-08 | T-04-06 | immutable, hash-addressed artifacts | conformance | `.venv/bin/pytest tests/conformance/test_artifactstore.py -q` | ❌ task creates | ⬜ pending |
| 04-08-T2 | 04-08 | 5 | FABR-06 | T-04-06 | hash-verified re-hydration, exact-version resolution | replay unit | `.venv/bin/pytest tests/replay -q && .venv/bin/mypy --strict src` | ❌ task creates | ⬜ pending |
| 04-08-T3 | 04-08 | 5 | CINV-04 | — | explicit not-yet-applicable markers (no false green) | invariant harness | `.venv/bin/pytest tests/invariants -q -rs \| grep -qi "not-yet-applicable" && .venv/bin/pytest tests/invariants -q` | ❌ task creates | ⬜ pending |
| 04-09-T1 | 04-09 | 5 | FABR-09 | T-04-07 | change events validated into envelopes at boundary | unit | `.venv/bin/pytest tests -q -k envelope_map --collect-only -q; .venv/bin/python -m tools.lints --all` | ❌ task creates | ⬜ pending |
| 04-09-T2 | 04-09 | 5 | FABR-09 | T-04-07 | graph entry via L2 only | integration | `.venv/bin/pytest tests/integration/test_cdc_slice.py -q && .venv/bin/mypy --strict src runtime` | ❌ task creates | ⬜ pending |
| 04-10-T1 | 04-10 | 6 | FABR-01 | T-04-04 | parameterized SQL, tenant scoping | import + lint | `.venv/bin/python -c "import ccf.graph.backends.postgres" && .venv/bin/mypy --strict src` | ❌ task creates | ⬜ pending |
| 04-10-T2 | 04-10 | 6 | FABR-01 | T-04-04 | six semantics identical on Postgres | conformance (testcontainers) | `.venv/bin/pytest tests/conformance -q && .venv/bin/pytest tests/conformance -q -m postgres` | ✅ (suite) | ⬜ pending |
| 04-11-T1 | 04-11 | 6 | FABR-02 (similarity) | — | Protocol conformance, sqlite-vec impl | conformance | `.venv/bin/pytest tests/conformance/test_similarity_index.py -q` | ❌ task creates | ⬜ pending |
| 04-11-T2 | 04-11 | 6 | FABR-02 | T-04-SC | Chroma optional extra, core imports clean | conformance + property re-run | `.venv/bin/pytest tests/conformance/test_similarity_index.py -q -m chroma && HYPOTHESIS_PROFILE=ci .venv/bin/pytest tests/properties -q` | ✅ (suite) | ⬜ pending |
| 04-12-T1 | 04-12 | 7 | CINV-01..04 (gate matrix) | all | full matrix green, per-invariant checklist | full suite | `.venv/bin/pytest tests -q && .venv/bin/python -m tools.lints --all && .venv/bin/mypy --strict src runtime && test -f docs/PHASE_I1_GATE.md` | ✅ (suite) | ⬜ pending |
| 04-12-T2 | 04-12 | 7 | §3.1 self-review | — | blocking/advisory triage recorded | doc grep | `grep -qi "triage" docs/PHASE_I1_GATE.md && grep -qiE "blocking\|advisory" docs/PHASE_I1_GATE.md` | ✅ (T1 output) | ⬜ pending |
| 04-12-T3 | 04-12 | 7 | Dave approval gate | — | approval authority is Dave's | human-check (blocking) | — (checkpoint:human-verify) | — | ⬜ pending |
| 04-12-T4 | 04-12 | 7 | D-GATE-I.1 log + merge | — | merge only after approval | doc + git grep | `grep -q "D-GATE-I.1" docs/DECISIONS.md && git log main --oneline -1 \| grep -qi "D-GATE-I.1"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Covered by plan 04-01 (Wave 1 scaffold) and 04-02 (lint harness):

- [ ] `pyproject.toml` — package + pytest + mypy config, venv bootstrap (PEP-668 host) — 04-01 Task 1
- [ ] `tests/conftest.py` — shared fixtures (SQLite graph store, config artifacts, canonical-serialization helpers) — 04-01 Task 1
- [ ] `tests/test_smoke.py` — import/smoke stubs for the fabric package — 04-01 Task 1
- [ ] CINV lint harness (`python -m tools.lints --all` runnable per D-06 layout, not-yet-applicable checks explicitly marked) — 04-02

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| D-GATE review presentation to Dave (04-12 Task 3) | — | Approval authority is Dave's (CLAUDE.md §3.1) | Present deliverables + review report + triage |

*All other phase behaviors have automated verification per FEASIBILITY.md §11.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (04-12 Task 3 is the sole human checkpoint, by design)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test infra + lint harness land in plans 04-01/04-02 before any `/src` code)
- [x] No watch-mode flags
- [x] Feedback latency < 90s (quick run excludes postgres/chroma legs)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for execution
