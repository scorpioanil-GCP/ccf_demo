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
ENV_PERF := PYTHONPATH=src:runtime:perf CCF_PERF_RUNNER_CLASS=$(CCF_PERF_RUNNER_CLASS)

.DEFAULT_GOAL := help

.PHONY: help install lint typecheck test ci-core ci examples \
	example-00 example-01 example-02 example-03 example-04 example-05 \
	example-06 example-07 example-08 \
	example-03-live-ollama example-03-live-anthropic \
	perf perf-micro perf-scale perf-xproc perf-replay

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
ci: ci-core examples ## Full local reproduction of the always-on pipeline (D-10)

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

examples: example-00 example-01 example-02 example-03 example-04 example-05 example-06 example-07 example-08 ## Run all nine examples in order, stopping on first failure

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
