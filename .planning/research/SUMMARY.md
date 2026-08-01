# Project Research Summary — v0.2 Milestone

**Project:** CCF SDK — v0.2 (Performance Battery, Documentation Suite, Hardening Intake)
**Domain:** Protocol-heavy Python SDK tooling — benchmarking with CI regression gating, docs-as-code, security/concurrency hardening
**Researched:** 2026-07-31
**Confidence:** HIGH

## Executive Summary

v0.2 is a maturation milestone on a shipped, invariant-locked v0.1 (1339 tests, mypy --strict, 8 CI examples): close the audit's hardening debt (WR-01/02/03 plus two posture questions), stand up a credible, reproducible performance battery with committed baselines and relative regression gating, and build the adopter documentation suite the §1 adoptability promise requires. All three categories integrate into the existing monorepo discipline — Makefile as the single command surface (D-10), opt-in CI workflows modeled on `live-legs.yml`, and docstrings-with-whitepaper-citations as the single source of API truth.

The recommended approach is strongly convergent across all four research tracks: **harden first, measure second, document last.** Hardening stabilizes the surface everything else measures and describes; the perf battery captures baselines against the hardened code; docs then describe the hardened postures and cite measured numbers. Tooling is settled and boring: pytest-benchmark 5.2.3 for the battery (pytest-plugin, self-hosted, built-in committed-baseline comparison with relative fail thresholds); mkdocs-material + mkdocstrings for docs (griffe's static analysis handles Protocols correctly, and existing docstring citations flow into the rendered reference with zero duplication); zero new dependencies for hardening (stdlib locks, existing joserfc machinery, typed errors).

The key risks: (1) perf gates that flake on shared runners and die of false-positive fatigue — mitigated by relative-median thresholds against runner-class-keyed committed baselines, opt-in/non-blocking CI initially; (2) hardening that fixes one door while leaving the MCP/CLI doors or adjacent read surfaces open — mitigated by choke-point enforcement plus a cross-door test matrix; (3) docs that duplicate and drift — mitigated by generated reference, literal-includes from CI-run examples, and a strict docs build in CI. Two items are **gated on Dave rulings and must not be defaulted**: the WR-01 scope→tenant mapping shape, and the ApprovalGate.resolve × signed_binding_required composition (already flagged by v0.1 review as a D-IMPL candidate).

## Key Findings

### Recommended Stack

The v0.1 stack is settled and untouched. v0.2 adds two capability sets, both version-verified against PyPI on 2026-07-31.

**Core technologies:**
- **pytest-benchmark 5.2.3**: perf battery — the only candidate that is a pytest plugin (reuses the existing harness), has built-in committed-baseline comparison and relative CI gating (`--benchmark-compare-fail=median:X%`), and is self-hosted (private proprietary repo). No second benchmarking library; scale curves use `benchmark.pedantic` or plain `perf_counter` writing into the same JSON schema.
- **mkdocs-material 9.7.7 + mkdocstrings[python] 1.0.6 + mkdocs-swagger-ui-tag 0.8.1**: docs site, generated API/Protocol reference, and embedded OpenAPI. Decisive argument: griffe does *static* analysis and renders `typing.Protocol` correctly without importing (avoiding the optional-import problem Sphinx autodoc would reintroduce); existing whitepaper-citation docstrings flow straight into the reference.
- **Hardening: zero new dependencies.** `threading.Lock` (WR-02), existing joserfc signed-binding machinery (WR-01 authz over verified identity), adapter-local retry/typed errors (WR-03), `warnings.warn` (create_app posture).

**Rejected:** CodSpeed/any perf SaaS (private-repo vendor coupling), pyperf/asv/richbench (second harness / dashboard-shaped / unmaintained), Sphinx/pdoc, locust/k6, tenacity/backoff, a direct mkdocs pin.

### Expected Features

**Must have (table stakes):**
- Micro-benchmark suite + committed baseline JSON + environment manifest + relative regression thresholds in an opt-in CI job; `make perf` local reproduction; p50/p95/p99 percentiles; deterministic synthetic dataset generator (domain-neutral per No-Hardcoding)
- Adopter's guide (day-1-to-production narrative), Protocol reference (every Protocol: contract, invariants, reference impl, implement-your-own checklist), definition-artifact schema reference (adopters author artifacts, not code — this is their primary API), generated API reference, how-to guides, concepts pages, security & deployment notes, OpenAPI polish, docs build in CI
- WR-01 per-tenant authorization at HITL doors (deny-by-default, 403 not 404-leak, authz decision in audit); WR-02 synchronized in-memory transports + Protocol concurrency contract + stress test; WR-03 typed errors + no nested `asyncio.run` + cross-adapter parity; create_app explicit-insecure posture with loud warning

**Should have (differentiators):**
- "Cost of trust" benchmark (governed path with vs without gates/signing — bench-harness-only flag, never a product path)
- Replay-at-scale battery proving the year-scale replay claim empirically
- Invariants page + whitepaper cross-reference index + "anatomy of a replay record" walkthrough
- Concurrency/authz regression tests folded into the invariant suite

**Defer (post-v0.2):**
- Perf SaaS/dashboarding, docs hosting decisions, HTTP load testing (locust/k6), RBAC/policy engine for the HTTP door, OIDC provider integration, 55MB-blob history rewrite

### Architecture Approach

All three categories bolt onto existing seams without touching core contracts. Perf lives in a new top-level `perf/` tree (sibling of `tests/` — structural exclusion from the blocking suite, parallels the `examples/` precedent) with `suites/`, `baselines/<suite>.<runner-class>.json`, and `thresholds.toml`; the CI job is a new opt-in `perf.yml` modeled on `live-legs.yml`. Docs source lives under `docs/guide/` + `docs/reference/` with a dedicated `docs_dir` so the proprietary whitepaper and phase deliverables are never published; `make docs --strict` joins the always-on pipeline (a logged D-10 amendment, not a silent one). Hardening changes are door-level (authorization between identity derivation and transport submit, via a new `TenantAuthorizerProtocol`), transport-internal (locks guarding mutation only), and adapter-local (ADK driver loop-safety) — authorization never leaks into `/src` core, and the SDK never invents a scope vocabulary (CINV-01).

**Major components:**
1. `perf/` battery — four suites (micro operators, fabric scale curves, cross-process latency, replay-at-scale), runner-class-keyed committed baselines, `make perf`/`make perf-baseline` targets, opt-in `perf.yml`
2. Docs suite — mkdocs toolchain, generated Protocol/API reference from citation-bearing docstrings, adopter guide/how-tos/concepts/security pages, OpenAPI export step, optional docs-citation-coverage lint in `tools/lints/`
3. Hardening set — door-level tenant authorization (HTTP + MCP, cross-door test matrix), locked InMemoryHitlTransport, robust AdkWorkflowDriver, create_app warning, ApprovalGate composition per Dave's ruling

### Critical Pitfalls

1. **Perf gate flake on hosted runners (A1)** — relative-median thresholds only, runner-class-keyed baselines, opt-in/non-blocking initially; promote to blocking only after ~2 weeks of observed variance.
2. **Measuring the wrong layer (A2)** — explicit layer taxonomy (micro / fabric / cross-process / replay), gate only micro+fabric; never time LLM or process startup.
3. **Authorization bypass by surface (C1)** — audit says HITL *doors* plural; enforce at the shared choke point with a cross-door × cross-action test matrix as the acceptance criterion; inventory adjacent read surfaces (C6).
4. **Hardening silently breaking replay byte-equality (C2)** — any expected-output regeneration in examples is a blocking review event; run the full example sweep per hardening task; new replay fields additive only.
5. **Docs duplicating and drifting (B1/B2)** — generated reference from docstrings, literal-include example code by path, strict docs build in CI; never hand-write signatures or paste snippets.
6. **Deadlock at the sync/async seam (C3)** — fix WR-03's `asyncio.run` before or with WR-02's locks; locks guard data mutation only, never held across callbacks/awaits; threaded stress test with timeout.

## Implications for Roadmap

All four research tracks independently converge on the same ordering: **Hardening → Performance → Documentation**, with a D-IMPL ruling batch surfaced to Dave at the very start.

### Phase 1: Hardening — defect fixes + ruling batch
**Rationale:** Small, closes audit debt, no external dependencies, and stabilizes the surface the perf battery will baseline and the docs will describe. WR-02/WR-03 are straight defect fixes needing no rulings — start immediately. Simultaneously surface the D-IMPL batch to Dave (one Phase D mini-cycle, not several): WR-01 mapping shape, ApprovalGate.resolve composition, perf governance, docs toolchain/publishing, D-10 amendment, create_app warning confirmation.
**Delivers:** Thread-safe transports with documented Protocol concurrency contract + stress test; loop-safe ADK driver with typed errors and cross-adapter parity; ruling batch logged.
**Addresses:** WR-02, WR-03 table stakes.
**Avoids:** C3 (order WR-03 → WR-02 so the sync/async seam is clean when locks arrive), C4 (no ApprovalGate code before Dave's ruling), C2 (example sweep per task).

### Phase 2: Hardening — authorization (post-rulings)
**Rationale:** Gated on the Phase 1 ruling batch. WR-01 and ApprovalGate composition are decision-shaped; implement per rulings only.
**Delivers:** Door-level tenant authorization (`TenantAuthorizerProtocol`, deny-by-default, typed 403, audit capture) across HTTP and MCP doors; ApprovalGate composition per ruling; create_app posture per confirmation; examples 05/06 extended to demonstrate tenant authorization.
**Addresses:** WR-01, ApprovalGate item, create_app item.
**Avoids:** C1 (choke-point + cross-door matrix), C6 (Experience Layer read-surface inventory, explicit tech-debt entries for deferrals), C5 (warning not default-flip).

### Phase 3: Performance battery
**Rationale:** Benchmarks must baseline the *hardened* surface; results feed the docs phase. First plan task: smoke-test pytest-benchmark 5.2.3 under pytest 9 (the one MEDIUM-confidence stack point).
**Delivers:** `perf/` tree with four suites, layer taxonomy, deterministic dataset generator built through L2/factory paths (never lint-exempted shortcuts), runner-class-keyed committed baselines, `thresholds.toml`, `make perf`/`make perf-baseline`, opt-in `perf.yml`, re-baseline ritual documented.
**Uses:** pytest-benchmark 5.2.3; `live-legs.yml` opt-in CI pattern.
**Avoids:** A1 (relative medians, non-blocking first), A2 (layer taxonomy, gate micro+fabric only), A3 (calibrated rounds, no xdist), A4 (baseline-match failure + reviewed re-baseline commits), A5 (fixtures through factories/L2).

### Phase 4: Documentation suite
**Rationale:** Last so it documents hardened postures (B5) and cites measured numbers. Toolchain setup and generated reference can start in parallel with Phase 3; adopter-guide *content* lands last.
**Delivers:** mkdocs-material site (dedicated `docs_dir`, whitepaper never published); generated Protocol/API reference via mkdocstrings; adopter's guide, how-tos, concepts, artifact schema reference, security & deployment pages, PERFORMANCE.md with methodology; OpenAPI export + drift check; `make docs --strict` in always-on CI (logged D-10 amendment); optional docs-citation-coverage lint.
**Uses:** mkdocs-material 9.7.7, mkdocstrings[python] 1.0.6, mkdocs-swagger-ui-tag 0.8.1 (new `docs` optional-dependency group).
**Avoids:** B1/B2 (generated reference, literal-includes), B3 (explicitly-scoped lint config for docs tooling), B4 (spec regenerated from `create_app()`, diff-checked in CI).

### Phase Ordering Rationale

- **Hardening first** because everything downstream measures or describes the hardened surface; documenting or baselining pre-hardening behavior is rework by construction (B5, and baseline invalidation).
- **Rulings batched early** because WR-01's mapping shape and ApprovalGate composition gate Phase 2, and perf/docs governance rulings (D-10 amendment, perf scheduling, publishing target) gate Phases 3–4 setup. One mini-cycle, not four.
- **Perf before docs** so PERFORMANCE.md publishes real measured baselines with an environment manifest, and the re-baseline ritual is documented alongside.
- **Docs reference generation parallelizable** with Phase 3 — it depends only on docstrings, which are stable after Phase 2.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (perf):** verify pytest-benchmark 5.2.3 × pytest 9 compatibility and exact compare-flag spellings at plan time (flagged MEDIUM in both STACK and ARCHITECTURE); threshold values and runner-class strategy are plan-level design decisions.
- **Phase 2 (authorization):** shape depends entirely on Dave's WR-01/ApprovalGate rulings — plan after the mini-cycle, not before.

Phases with standard patterns (skip research-phase):
- **Phase 1 (defect fixes):** stdlib locking and typed errors; fully specified in ARCHITECTURE.md/PITFALLS.md.
- **Phase 4 (docs):** mkdocs-material/mkdocstrings is a well-trodden path; the decisions are Dave-rulings (toolchain confirmation, publishing), not research gaps.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI 2026-07-31; one MEDIUM point (pytest 9 × pytest-benchmark 5.2.3 — smoke-test first) |
| Features | HIGH | Perf/docs norms are ecosystem-wide conventions; CCF-specific metric mapping MEDIUM (battery composition is a plan decision) |
| Architecture | HIGH | Integration points read directly from the shipped tree, Makefile, DECISIONS.md, audit register; tooling flag spellings MEDIUM |
| Pitfalls | HIGH (hardening) / MEDIUM-HIGH (perf-CI) / MEDIUM (docs) | Hardening pitfalls grounded directly in this repo's v0.1 audit register |

**Gaps to address during planning:**
- Six items require Dave rulings before implementation (do not default): WR-01 scope→tenant mapping shape; ApprovalGate.resolve × signed_binding_required (options a/b/c drafted in ARCHITECTURE.md); perf governance (schedule, runner classes, threshold values); docs toolchain confirmation + publishing target; D-10 amendment for `make docs` in always-on CI; create_app runtime-warning confirmation (touches ruled posture T-07-24).
- Exact per-suite threshold percentages and graph-size sweep points are plan-time calibration, kept in `perf/thresholds.toml`, never in code.
- `docs_dir` must be verified not to publish the whitepaper or internal deliverables.

## Sources

Aggregated from the four research files:
- Repo state (HIGH, read directly): `pyproject.toml`, `Makefile`, `.github/workflows/{ci.yml,live-legs.yml}`, `docs/DECISIONS.md`, `.planning/v0.1-MILESTONE-AUDIT.md`, `.planning/PROJECT.md`, `src/ccf/hitl/*`, `runtime/ccf_runtime/mcp/auth.py`, `CLAUDE.md` §§3, 6.4, 7.3, 9, 11, 13
- PyPI JSON API (HIGH, queried 2026-07-31): pytest-benchmark, pyperf, pytest-codspeed, richbench, mkdocs-material, mkdocstrings(-python), griffe, mkdocs, sphinx, pdoc, mkdocs-swagger-ui-tag, neoteroi-mkdocs
- CodSpeed / Bencher / pytest-benchmark CI-benchmarking guidance (MEDIUM): hosted-runner variance, relative-threshold norms, baseline caching
- Diátaxis framework + Python.org adoption discussion (HIGH for framing)
