---
phase: 15
slug: sdk-ergonomics-the-integration-surface
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-03
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `15-RESEARCH.md` §8 (Validation Architecture). The per-task map is
> populated by the planner; the strategy below is fixed at phase start.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (repo venv at `.venv/bin/python`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.mypy]`) |
| **Quick run command** | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/<area> -x -q` |
| **Full suite command** | `make test` (= `CCF_REQUIRE_HARNESSES=1 pytest -q`) |
| **Phase gate command** | `make ci` (= `lint typecheck test examples docs-strict`) |
| **Collected baseline** | **1,548** tests |
| **Estimated runtime** | ~30s quick / full suite per `make test` |

---

## Sampling Rate

- **After every task commit:** `make lint typecheck` + touched area's `pytest -x -q`. Sub-30s.
- **After every plan wave:** `make ci-core` (lint + typecheck + full 1,548-test suite).
- **After every example rewrite:** `make example-NN` for that example + `make docs-strict`.
- **Before `/gsd:verify-work`:** `make ci` fully green.
- **Phase gate:** `make ci` green → `/gsd-review --phase "Phase 15" --all` (CLAUDE.md §3.1)
  → triage blocking/advisory → **STOP and present to Dave**.
- **Max feedback latency:** 30 seconds.

---

## The Standing Guard (D-15A enforcement)

This phase's defining risk is that an ergonomic helper silently deletes a whitepaper
invariant. One test is the phase's constitutional constraint and **must be written in
Wave 0, before any helper exists**, so it is a standing limit rather than a retrofit:

`tests/products/test_gate_independence.py` — two assertions:
1. A `run_gates` call whose `engine_resolved` is deliberately perturbed **must** raise
   `LineageMismatchRefusal`. (Proves the two inputs are still independently sourced.)
2. An AST guard over `src/ccf/deployment/` asserting no function returns or constructs
   both a `ProductLineage` and an `engine_resolved`-shaped value from one parameter.

Paired with a lint-level ban: **`ccf.deployment` must not import `ccf.products.gates`.**

---

## Per-Target Validation Map

| Target | Validation type | Automated command | Exists? |
|---|---|---|---|
| Round-trip — every new artifact class | `parse_artifact` → `content_hash` → re-serialize → re-parse → identical object; hash stable across two parses | `pytest tests/controlplane/test_artifact_roundtrip.py -q` | ❌ W0 |
| Closed-world (D-03) | Unknown key in `ccf.resolution-spec` raises `ArtifactLoadError` | same module | ❌ W0 |
| Timestamps (D-02) | `...Z` → aware UTC; `+00:00` → aware; naive → `ArtifactLoadError` naming D-IMPL-38; PyYAML resolver provably suppressed | `pytest tests/controlplane/test_timestamps.py -q` | ❌ W0 |
| Float rejection unchanged | Existing `_reject_floats` tests still pass | existing | ✅ |
| **Gate-tautology regression** | See "The Standing Guard" above | `pytest tests/products/test_gate_independence.py -q` | ❌ W0 |
| Single-writer preserved | `FabricHandle` from the D-05 entry point exposes no writer; `ccf.deployment` does not import `ccf.graph._writer` | CINV-02 lint + `pytest tests/boot/ -q` | ◐ partial |
| Manifest determinism (D-06) | Same manifest ⇒ byte-identical pin set across two loads; manifest is content-hashable | `pytest tests/deployment/test_manifest.py -q` | ❌ W0 |
| Manifest has no globs | Glob-shaped path refused; adding an unlisted file does not change the pin set | same module | ❌ W0 |
| Backend kind (D-08) | manifest `postgres` + no DSN ⇒ loud failure, never a SQLite fallback | same module | ❌ W0 |
| Ordering constraint (D-07) | Operator-registry builder cannot be called without a `GraphView` | `pytest tests/deployment/test_operator_builder.py -q` | ❌ W0 |
| Composition-preservation | Existing operator-pair tests green after construction changes | existing suite | ✅ |
| Line-count audit (SC 1/5) | Executable check pinning each example's *achieved* mechanical line count so it cannot silently regress; reports before/after delta. Per D-12 there is no target number | `pytest tests/examples/test_surface_audit.py -q` | ❌ W0 |
| Surface manifest drift (D-15) | Committed `docs/surface/*.json` matches live surface | `pytest tests/test_surface_drift.py -q` | ❌ W0 |
| Schema freshness (D-04) | `ccf schema export` output matches committed schemas | `pytest tests/cli/test_schema_export.py -q` | ❌ W0 |
| Eight-example suite | All nine examples + external run and exit 0 | `make examples` | ✅ |
| Relocated assertions (D-09) | Each example has a parallel test module; **no assertion lost in the move** (count compared against the §1.3 pre-phase baseline) | `pytest tests/examples/ -q` | ❌ W0 |
| Docs build | mkdocs strict + publish scan after every surface change | `make docs-strict` | ✅ |

---

## Wave 0 Requirements

Nothing else may start before these land.

- [ ] `tools/dump_surface.py` + the live `docs/surface/v0.2-surface.json` + the frozen
      `docs/surface/v0.2-surface-baseline.json` phase-start copy + `tests/test_surface_drift.py` — **captured before the first surface change, or
      Success Criterion 6 cannot be satisfied honestly**
- [ ] `tests/products/test_gate_independence.py` — the D-15A standing guard
- [ ] `tests/examples/test_surface_audit.py` — records the §1.3 before-numbers as baseline
- [ ] `docs/SURFACE-CHANGES.md` skeleton
- [ ] `tests/deployment/` — new package; `conftest.py` with manifest/artifact fixtures
- [ ] `tests/controlplane/test_artifact_roundtrip.py`
- [ ] `tests/controlplane/test_timestamps.py`
- [ ] `tests/examples/test_*_output.py` ×9 — D-09 relocated assertions
- [ ] Framework install: **none needed** — pytest, mypy, and the lints are all present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live harness legs (`03/legs/live.py`, `ollama_client.py`) | ERGO-13 | Opt-in, excluded from `make ci` per Makefile `:56-57` / `live-legs.yml` | Run `make live-legs` with harness SDKs present. **Not a rewrite target — zero mechanical wiring (Q4)** |
| Postgres backend path (D-08) | ERGO-10 | No Postgres probed in this environment | Unit-level coverage of the loud-failure path only; SQLite is the default for all examples |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] `test_gate_independence.py` landed **before** the first `ccf.deployment` helper
- [ ] Surface baseline captured **before** the first surface change
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
