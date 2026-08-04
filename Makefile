# CCF SDK — single documented command surface for CI and developers (D-10).
# Every target CI runs, a developer runs the same way; the Makefile mirrors
# .github/workflows/ci.yml command-for-command (Phase I.5, plan 08-01).
#
# All Python invocations use the project venv interpreter explicitly and set
# PYTHONPATH=src:runtime so src-layout packages resolve without relying on the
# editable install being fresh (08-RESEARCH.md Pitfall 7 — `make install`
# refreshes it regardless).

PYTHON := .venv/bin/python
ENV := PYTHONPATH=src:runtime

# Perf battery environment (Phase 11). CCF_PERF_RUNNER_CLASS is the explicit
# declared runner-class key (D-10) — CI sets gh-ubuntu-24.04; local runs
# default to `local`; users may override: make perf CCF_PERF_RUNNER_CLASS=key.
CCF_PERF_RUNNER_CLASS ?= local

# Docs gate environment (Phase 14). The repo root joins the path because the
# publish scan is invoked as a script (`tools/publish_scan.py`), and a script
# run puts the script's own directory on sys.path, not the cwd — so `from
# tools.lints import ...` needs `.` explicitly, unlike the `-m tools.lints`
# form the `lint` target uses.
ENV_DOCS := PYTHONPATH=.:src:runtime
ENV_PERF := PYTHONPATH=src:runtime:perf CCF_PERF_RUNNER_CLASS=$(CCF_PERF_RUNNER_CLASS)

.DEFAULT_GOAL := help

.PHONY: help install lint typecheck test ci-core ci examples \
	example-00 example-01 example-02 example-03 example-04 example-05 \
	example-06 example-07 example-08 example-ext-00 \
	example-03-live-ollama example-03-live-anthropic \
	example-ext-00-live-anthropic example-ext-00-live-adk \
	perf perf-micro perf-scale perf-xproc perf-replay \
	docs docs-strict docs-serve openapi surface measure-examples

help: ## List targets with one-line descriptions
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-28s %s\n", $$1, $$2}'

install: ## Refresh the editable install with dev extras (pip install -e ".[dev]")
	.venv/bin/pip install -e ".[dev]"

lint: ## CCF invariant lints — CINV-01/02/03 + orchestration split (blocking, D-07)
	$(ENV) $(PYTHON) -m tools.lints --all

typecheck: ## mypy --strict over src + runtime ([tool.mypy] files is authoritative)
	$(ENV) $(PYTHON) -m mypy

test: ## Full pytest suite with harness legs required (CCF_REQUIRE_HARNESSES=1)
	$(ENV) CCF_REQUIRE_HARNESSES=1 $(PYTHON) -m pytest -q

ci-core: lint typecheck test ## Mid-phase verification sweep — MUST stay green from Wave 1 onward

# Finalized in plan 08-12: `ci` = ci-core + examples is the phase gate
# command, reproducing the always-on Actions pipeline (ci.yml lint + test +
# examples jobs) locally command-for-command (D-10). Live legs are opt-in
# (live-legs.yml, D-11) and deliberately not part of `ci`.
#
# Amended in plan 14-10: D-IMPL-72 pre-authorized adding the docs gate to this
# composition, effective at the plan that creates the docs build target. That
# gate is now complete (strict build + publish scan, D-02), so `docs-strict`
# joins `ci` here — never as a half-armed or dead target.
ci: ci-core examples docs-strict ## Full local reproduction of the always-on pipeline (D-10)

example-00: ## Run examples/00-quickstart (reference backends, D-13)
	$(ENV) $(PYTHON) examples/00-quickstart/run.py

example-01: ## Run examples/01-agent-basics
	$(ENV) $(PYTHON) examples/01-agent-basics/run.py

example-02: ## Run examples/02-skilling
	$(ENV) $(PYTHON) examples/02-skilling/run.py

example-03: ## Run examples/03-harness-portability (deterministic leg only, D-12)
	$(ENV) $(PYTHON) examples/03-harness-portability/run.py --mode deterministic

example-04: ## Run examples/04-cross-process
	$(ENV) $(PYTHON) examples/04-cross-process/run.py

example-05: ## Run examples/05-workflow-hitl
	$(ENV) $(PYTHON) examples/05-workflow-hitl/run.py

example-06: ## Run examples/06-decision-replay
	$(ENV) $(PYTHON) examples/06-decision-replay/run.py

example-07: ## Run examples/07-artifact-store-mcp
	$(ENV) $(PYTHON) examples/07-artifact-store-mcp/run.py

example-08: ## Run examples/08-e2e-demo (deterministic; --live is opt-in and never CI, D-10/D-12)
	$(ENV) $(PYTHON) examples/08-e2e-demo/run.py

example-ext-00: ## Run examples/external/00-hello-context — all legs deterministic via replay server
	$(ENV) $(PYTHON) examples/external/00-hello-context/run.py

examples: example-00 example-01 example-02 example-03 example-04 example-05 example-06 example-07 example-08 example-ext-00 ## Run all ten examples in order, stopping on first failure

# Perf battery (Phase 11). `perf` NEVER joins `ci` or `ci-core`: always-on CI
# never times anything (Phase-8 D-10 / D-IMPL-70) — perf runs only via these
# targets locally or via the opt-in workflow_dispatch perf.yml. gate.py is the
# single report+gate pipeline (D-02/D-03): it exits nonzero only on a gated
# slowdown regression against perf/baselines/<runner-class>.json; a missing
# baseline is loud report-only with exit 0 (D-13).
perf: perf-micro perf-scale perf-xproc perf-replay ## Full perf battery (~10 min, D-17); never part of `ci`

perf-micro: ## Micro-benchmarks: operators, factory, gates, run_coroutine_sync (D-23/D-05; 10% gate D-19)
	mkdir -p perf/results
	$(ENV_PERF) $(PYTHON) -m pytest perf/suites/micro -q \
		--benchmark-disable-gc --benchmark-json=perf/results/micro.raw.json
	$(ENV_PERF) $(PYTHON) perf/gate.py perf/results/micro.raw.json --suite micro

perf-scale: ## Fabric-scale curves: assembly + projection over the rung ladder (D-26; 10% gate D-19)
	mkdir -p perf/results
	$(ENV_PERF) $(PYTHON) -m pytest perf/suites/scale -q \
		--benchmark-disable-gc --benchmark-json=perf/results/scale.raw.json
	$(ENV_PERF) $(PYTHON) perf/gate.py perf/results/scale.raw.json --suite scale

perf-xproc: ## Cross-process latency: MCP egress + peering round-trips (D-15; 25% gate D-20)
	mkdir -p perf/results
	$(ENV_PERF) $(PYTHON) -m pytest perf/suites/crossproc -q \
		--benchmark-disable-gc --benchmark-json=perf/results/crossproc.raw.json
	$(ENV_PERF) $(PYTHON) perf/gate.py perf/results/crossproc.raw.json --suite crossproc

perf-replay: ## Replay-at-scale ladder: byte-exact + curve shape (D-16; 15% gate D-21)
	mkdir -p perf/results
	$(ENV_PERF) $(PYTHON) -m pytest perf/suites/replay -q \
		--benchmark-disable-gc --benchmark-json=perf/results/replay.raw.json
	$(ENV_PERF) $(PYTHON) perf/gate.py perf/results/replay.raw.json --suite replay

example-03-live-ollama: ## Example 03 live leg via Ollama (opt-in, D-11; not part of `examples`)
	$(ENV) $(PYTHON) examples/03-harness-portability/run.py --mode live --provider ollama

example-03-live-anthropic: ## Example 03 live leg via Anthropic (opt-in, D-11; not part of `examples`)
	$(ENV) $(PYTHON) examples/03-harness-portability/run.py --mode live --provider anthropic

example-ext-00-live-anthropic: ## External example 00 Anthropic leg live (opt-in, D-11; never in `examples`/`ci`)
	$(ENV) $(PYTHON) examples/external/00-hello-context/run.py --live --legs anthropic

example-ext-00-live-adk: ## External example 00 ADK/Gemini leg live (opt-in, D-11; never in `examples`/`ci`)
	$(ENV) $(PYTHON) examples/external/00-hello-context/run.py --live --legs adk

# Docs (Phase 14, D-IMPL-71). `docs` is the plain build; `docs-strict` is the
# always-on gate wired into `ci` per D-IMPL-72 (plan 14-10).
docs: ## Build the documentation site with mkdocs (D-IMPL-71; built into site/, never hosted)
	$(ENV) $(PYTHON) -m mkdocs build

# The whole docs gate as one blocking target (D-IMPL-72), in three ordered
# steps. The pre-build structural scan runs FIRST so a symlink or an escaping
# include is reported before the build has a chance to copy it; then the strict
# build; then the post-build content scan over the tree that would actually
# ship (D-02). No `|| true`, no `-` prefix, no report-only flag anywhere in this
# recipe: the exit code is the only gate signal, exactly as `tools/lints` and
# `tools/publish_scan.py` both state — a non-blocking mode is how an invariant
# quietly stops being one.
docs-strict: ## Blocking docs gate: pre-build scan + strict build + site scan (D-IMPL-72, D-02)
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py --pre-build
	$(ENV_DOCS) $(PYTHON) -m mkdocs build --strict
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py site

# Interactive authoring server only. Like the perf and live-leg targets, it is
# opt-in and NEVER joins `ci` — it blocks forever by design.
docs-serve: ## Serve the docs locally with live reload (opt-in; never part of `ci`)
	$(ENV) $(PYTHON) -m mkdocs serve

# D-12's deliberate exception to D-11's generate-at-build posture: the HTTP
# contract is committed so endpoint changes surface as reviewable diffs. The
# drift assertion lives in the already-always-on `test` job, so this target
# needs no `ci:` wiring.
openapi: ## Regenerate the committed openapi.json — the D-12 drift baseline
	$(ENV) $(PYTHON) tools/dump_openapi.py

# D-15's generated half: the public surface of every /src and /runtime module
# with an `__all__`, committed so a removed or reshaped export surfaces as a
# reviewable diff. The live manifest is regenerated by exactly two plans in
# Phase 15 (15-01 at phase start, 15-21 at phase close); in-flight plans run
# `tools/dump_surface.py --report` and write a docs/surface-changes/ fragment
# instead. The drift assertion lives in the always-on `test` job.
surface: ## Regenerate the committed public-surface manifest — the D-15 baseline
	$(ENV) $(PYTHON) tools/dump_surface.py

# ERGO-03's measured half (D-11/D-12): the per-file mechanical, assertion, and
# print line counts of the examples tree, committed as the phase-start baseline
# under docs/surface/examples/before/. Criterion 1's report is a re-measurement
# by this same tool, never a re-estimate. `removable` (mechanical wiring) and
# `relocatable` (assertions/prints D-09 moves to tests/) are separate figures
# and are never summed. The audit assertion lives in the always-on `test` job
# (tests/examples/test_surface_audit.py).
measure-examples: ## Re-measure examples/ mechanical surface — the ERGO-03 baseline
	$(ENV) $(PYTHON) tools/measure_examples.py
