# Stack Research — v0.2 Additions (Performance Battery, Documentation, Hardening)

**Domain:** Python SDK tooling — benchmarking with CI regression gating, docs-as-code for a Protocol-heavy typed SDK, hardening primitives
**Researched:** 2026-07-31
**Confidence:** HIGH (all versions verified against PyPI on 2026-07-31; recommendations checked against existing pyproject/Makefile/ci.yml)

Scope discipline: this covers only NEW capabilities for the v0.2 milestone. The v0.1 stack (pytest 9.1.1, mypy 2.3.0, FastAPI 0.140.0, mcp 1.28.1, etc.) is settled and not re-litigated here.

## Recommended Stack

### (a) Performance test battery

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest-benchmark | 5.2.3 (2025-11-09) | Micro-benchmark fixture, JSON baseline emit/compare, relative-threshold regression failure | The only candidate that is (1) a pytest plugin — reuses the existing 1339-test harness, fixtures, and markers verbatim; (2) has built-in committed-baseline comparison (`--benchmark-save` / `--benchmark-compare`) and CI gating (`--benchmark-compare-fail=median:X%`) with zero extra infrastructure; (3) self-hosted — no SaaS, which matters for a private proprietary repo. Requires `pytest>=8.1`; project pins pytest 9.1.1 — compatible (5.2.x line released after pytest 9). |

**No second benchmarking library.** The fabric load/scale curves, cross-process latency, and replay-at-scale tests are *measurements*, not micro-benchmarks: use `benchmark.pedantic(rounds=..., iterations=1)` for the ones where per-call timing fits, and plain `time.perf_counter()` loops writing rows into the same `--benchmark-json` output schema (or a small committed CSV) for scale curves. Nothing else is needed.

**Alternatives rejected:**

| Candidate | Version | Why not |
|-----------|---------|---------|
| pyperf | 2.10.0 | Statistically the most rigorous (CPU isolation, calibration), but it is a standalone runner, not a pytest plugin — a second harness, second invocation, and no built-in fail-on-regression comparison for CI. Right tool for one-off CPython-style tuning sessions, wrong tool for a committed regression battery. |
| pytest-codspeed / CodSpeed | 5.0.3 | Instrumentation-based (valgrind/perf) measurement is genuinely noise-free in CI, but it is a hosted SaaS: results, gating, and baselines live in CodSpeed's service. External vendor dependency + shipping benchmark data off a private proprietary repo. Reconsider post-v0 only if runner noise defeats relative thresholds. |
| richbench | 1.0.3 (2022-06-21) | Effectively unmaintained (last release 2022); pretty-print comparison tool, no baselines, no CI gating. |
| asv (airspeed velocity) | — | Historical-tracking dashboard tool; heavyweight repo-checkout model, own config format, poor fit for pytest-first codebase. |

**Baseline storage and comparison approach (the load-bearing design):**

1. Perf tests live in `tests/perf/`, marked `@pytest.mark.perf`, and **deselected from the default suite** — add `perf` to `[tool.pytest.ini_options] markers` and `-m "not perf"` to the default `addopts` (or keep `testpaths` exclusion; markers are cleaner given the existing marker discipline for `postgres`/`crossproc`/etc.).
2. Baselines are **committed JSON** under `tests/perf/baselines/<machine-class>.json`, produced by `pytest --benchmark-save`, then copied/renamed into the tree. Committed baselines are the milestone requirement; pytest-benchmark's default `.benchmarks/` dir is gitignored scratch.
3. CI gating is **relative, not absolute**: `--benchmark-compare=tests/perf/baselines/ci.json --benchmark-compare-fail=median:25%` (median, not mean — shared GitHub runners have long-tail noise; mean gates flake). The CI baseline is recorded *on a CI runner*, never from a dev machine — different machine classes get different baseline files.
4. The CI perf job is **opt-in** (per the milestone spec): `workflow_dispatch` + a `perf` label/path trigger, its own job in `ci.yml` — never in the always-on `ci-core` path, so perf noise can never block a functional merge.
5. `make perf` = run battery locally against local baseline; `make perf-baseline` = regenerate and overwrite baseline (an explicit, reviewed act — baseline churn goes through PR review like any contract change).

### (b) Documentation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| mkdocs-material | 9.7.7 (2026-07-17) | Docs site framework/theme | The de-facto standard for Python SDK adopter docs (Pydantic, FastAPI, Typer, mcp all use it). Markdown-native — the adopter's guide, security/deployment notes, and definition-artifact schema reference are prose, and Markdown authoring friction is far lower than reST. Actively maintained, ships search/nav/versioning out of the box. |
| mkdocstrings | 1.0.6 (2026-07-11) | Autodoc bridge for MkDocs | Renders API reference from docstrings inline in Markdown pages (`::: ccf.products.ContextProduct`). The whitepaper-section citations already living in every public docstring flow straight into the rendered reference — no duplication. |
| mkdocstrings-python | 2.0.5 (2026-06-19) | Python handler (griffe-based) | **The decisive Protocol-heavy-SDK argument:** griffe (2.1.0) does *static* analysis — it understands `typing.Protocol`, `@runtime_checkable`, PEP 695 syntax, Pydantic models, and overloads without importing the package, and cross-links type annotations in signatures. Sphinx autodoc imports modules and historically renders Protocols poorly without extra extensions. |
| mkdocs-swagger-ui-tag | 0.8.1 | Render OpenAPI spec inside the docs site | Embeds Swagger UI against a checked-in `openapi.json`. The spec is *exported* by a tiny script calling `create_app(...).openapi()` (FastAPI already generates it from the existing `extra=forbid` Pydantic contracts — no hand-authored spec, no drift). |

**Alternatives rejected:**

| Candidate | Version | Why not |
|-----------|---------|---------|
| Sphinx (+ furo + autodoc) | 9.1.0 | reST friction for prose-heavy adopter docs; autodoc's import-based model is worse for Protocols and would import harness-optional modules at doc build (the `chroma`/harness optional-import problem all over again). Choose Sphinx only if PDF output or intersphinx inventories become requirements — they aren't. |
| pdoc | 16.0.0 | Excellent zero-config API reference, but API-reference-*only* — no story for the adopter's guide, deployment notes, or schema reference, which are the bulk of this milestone's docs scope. |
| neoteroi-mkdocs (OpenAPI) | 1.2.0 | Renders OpenAPI as static Markdown-ish pages; viable, but Swagger UI's try-it rendering is the more familiar surface and the plugin is simpler. Low-stakes swap either way. |
| mkdocs-render-swagger-plugin | 0.1.2 | Stale (0.1.x), superseded by mkdocs-swagger-ui-tag. |

Note: mkdocs-material vendors its `mkdocs` dependency requirement (mkdocs 1.6.1 arrives transitively; do not pin mkdocs directly).

**Docs integration points:**
- New optional-dependency group `docs = ["mkdocs-material==9.7.7", "mkdocstrings[python]==1.0.6", "mkdocs-swagger-ui-tag==0.8.1"]` (the `[python]` extra pulls mkdocstrings-python 2.0.5 + griffe 2.1.0). Keep it out of `dev` if install weight matters, or fold in — either is defensible; separate group keeps CI's test env lean.
- `mkdocs.yml` at repo root; docs source under `docs/site/` or `docs/` alongside existing deliverables (namespace carefully — `docs/` already holds phase deliverables and the whitepaper; a `mkdocs.yml` `docs_dir` pointing at a dedicated subdirectory avoids publishing internal deliverables).
- `make docs` = `mkdocs build --strict` (`--strict` turns broken cross-references into build failures — the docs equivalent of the invariant lints). Add to the always-on CI as a cheap job: broken docs are a broken build, same D-10 spirit as examples.
- OpenAPI export script lives in `runtime` tooling or `scripts/`; the exported `openapi.json` is generated at docs-build time, not hand-committed (spec-drift discipline already recorded in pyproject comments for fastapi).

### (c) Hardening items

**No new dependencies. Stdlib + already-present libraries only.**

| Need | Use | Notes |
|------|-----|-------|
| WR-02 transport synchronization / thread-safety | `threading.Lock` / `threading.RLock` (stdlib); `anyio.Lock` for async paths | anyio is already present transitively via starlette/mcp — if async locking is needed, use anyio (do **not** add a direct pin unless first-party code imports it, per the httpx-promotion precedent in pyproject: first-party import ⇒ direct pin). |
| WR-01 HITL door authorization | Existing joserfc 1.7.4 signed-binding machinery (D-13/D-16) | Authorization is Control Plane mechanism over existing identity primitives; a new authz library would be scope creep. |
| WR-03 ADK driver robustness | Retry/timeout logic in the adapter, stdlib | Adapter-local; no tenacity/backoff dependency warranted for one driver. |
| create_app auth-default warning | `warnings.warn` (stdlib) | — |

Mechanism-not-values note: perf thresholds (`25%`, machine classes) and doc structure are *SDK development* configuration living in Makefile/ci.yml/baseline files — they never enter `/src`. No hardening item introduces a threshold constant into library code; anything tunable (timeouts, retry counts) belongs in Control Plane configuration per the No-Hardcoding Rule.

## Installation

```bash
# Perf (add to [project.optional-dependencies].dev or a new perf group)
pip install pytest-benchmark==5.2.3

# Docs (new optional group `docs`)
pip install mkdocs-material==9.7.7 "mkdocstrings[python]==1.0.6" mkdocs-swagger-ui-tag==0.8.1

# Hardening: nothing to install
```

## What NOT to add

- **codspeed / any hosted perf service** — private proprietary repo, vendor coupling.
- **pyperf, asv, richbench** — second harness / unmaintained / dashboard-shaped (above).
- **locust / k6** — the "load/scale curves" target is fabric-internal throughput measurement, not HTTP load testing of a deployed service; k6 would measure uvicorn, not the SDK.
- **pytest-xdist for perf runs** — parallel workers destroy timing validity; perf job runs serial.
- **Sphinx, pdoc** — above.
- **tenacity/backoff, an authz framework, a metrics library** — hardening items are stdlib-scale.
- **A direct `mkdocs` pin** — transitive via mkdocs-material.

## Open flags for planning

1. **pytest 9 × pytest-benchmark 5.2.3**: declared `pytest>=8.1`; 5.2.3 postdates pytest 9 and is expected compatible, but the first plan task should smoke-test `pytest --benchmark-only` in the dev env before building the battery (MEDIUM confidence on this single point; everything else HIGH).
2. **CI runner noise**: if the opt-in perf job flakes even at `median:25%`, fall back to trend-reporting (compare, don't fail) before reaching for CodSpeed — record that as a plan decision, not a silent loosening.
3. **docs_dir collision**: `docs/` already contains phase deliverables and the proprietary whitepaper; the mkdocs `docs_dir` must be a dedicated subtree and the site build must be verified not to publish the whitepaper (repo is private, but the discipline should hold for any future publish target).

## Sources

- PyPI JSON API, queried 2026-07-31: pytest-benchmark 5.2.3, pyperf 2.10.0, pytest-codspeed 5.0.3, richbench 1.0.3, mkdocs-material 9.7.7, mkdocstrings 1.0.6, mkdocstrings-python 2.0.5, griffe 2.1.0, mkdocs 1.6.1, sphinx 9.1.0, pdoc 16.0.0, mkdocs-swagger-ui-tag 0.8.1, neoteroi-mkdocs 1.2.0 — HIGH confidence (official index metadata incl. release dates and `requires_dist`).
- Existing repo state: `pyproject.toml` (pins, extras discipline, marker registry, mypy files), `Makefile` (ci-core/examples targets), `.github/workflows/ci.yml` (job layout) — read directly.
