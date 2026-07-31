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

.DEFAULT_GOAL := help

.PHONY: help install lint typecheck test ci-core ci examples \
	example-00 example-01 example-02 example-03 example-04 example-05 \
	example-06 example-07 example-03-live-ollama example-03-live-anthropic

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

examples: example-00 example-01 example-02 example-03 example-04 example-05 example-06 example-07 ## Run all eight examples in order, stopping on first failure

example-03-live-ollama: ## Example 03 live leg via Ollama (opt-in, D-11; not part of `examples`)
	$(ENV) $(PYTHON) examples/03-harness-portability/run.py --mode live --provider ollama

example-03-live-anthropic: ## Example 03 live leg via Anthropic (opt-in, D-11; not part of `examples`)
	$(ENV) $(PYTHON) examples/03-harness-portability/run.py --mode live --provider anthropic
