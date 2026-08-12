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
	example-s1-01 \
	example-00 example-01 example-02 example-03 example-04 example-05 \
	example-06 example-07 example-08 example-ext-00 \
	example-03-live-ollama example-03-live-anthropic \
	example-ext-00-live-anthropic example-ext-00-live-adk \
	legs leg-postgres leg-neo4j leg-mongo leg-fluree \
	perf perf-micro perf-scale perf-xproc perf-replay \
	docs docs-strict docs-serve openapi schemas schema-headers surface \
	surface-changes measure-examples

help: ## List targets with one-line descriptions
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-28s %s\n", $$1, $$2}'

# The second line installs the out-of-tree adapter fixture (plan 15.4-10). It
# is ALWAYS-ON rather than opt-in, and the ruling is recorded rather than left
# as a silence: plan 15.4-11 asserts that the conformance parameter lists and
# `declared_names()` agree in BOTH directions, so under an opt-in target a
# developer who ran `make install` and then `make ci-core` would get a red
# parity test for a step nothing reminded them to take.
#
# The visible consequence is accepted: every development checkout and every CI
# runner reports a seventh name from `ccf backends list`. It is bounded because
# the fixture is not a dependency of the `ccf` distribution — `pip install ccf`
# never pulls it, and a test asserts that — and because this target is the
# developer bootstrap, not an adopter's install path.
#
# Order matters: the fixture imports `ccf`, so the SDK's own install goes first.
install: ## Refresh the editable install with dev extras (pip install -e ".[dev]")
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/pip install -e ./tests/fixtures/ccf-demo-adapter

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

# Section 1's reference example. Its docstrings and `tests/examples/
# test_s1_01_output.py` have referred to this target since phase 16; it did not
# exist and the example therefore ran in no CI job (DI-15.5-02, closed by plan
# 15.5-13). With no arguments it asks the three questions
# `artifacts/questions.yaml` declares — two companies, two instants.
example-s1-01: ## Run examples/s1-01-hello-context-product (three declared questions)
	$(ENV) $(PYTHON) examples/s1-01-hello-context-product/run.py

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

# `s1-01` leads deliberately: it is the smallest and the fastest, so a break in
# the reference example fails the aggregate before ten minutes of the rest.
# Adding it here CHANGES WHAT `make ci` RUNS, which is the intended effect and
# not a side effect — the example was documented as CI-covered and was not
# (DI-15.5-02).
examples: example-s1-01 example-00 example-01 example-02 example-03 example-04 example-05 example-06 example-07 example-08 example-ext-00 ## Run all eleven examples in order, stopping on first failure

# Container-gated substrate legs (DI-15.2-04, D-GATE-15.2). These reproduce the
# ci.yml service-container steps command-for-command, so a developer runs a leg
# the same way CI runs it (D-10). Two properties are load-bearing and must not
# be dropped:
#   - `$(ENV)` puts the *working tree's* src/ on the path. Without it a bare
#     pytest resolves `ccf` through the editable install's hard-coded mapping to
#     the primary checkout, so a worktree tests code it did not change.
#   - `CCF_REQUIRE_*` turns an unreachable server from a skip into a failure. A
#     leg that quietly skips is a green run that proved nothing.
# Each URI is overridable on the command line for a differently-provisioned
# server, e.g. `make leg-mongo CCF_TEST_MONGO_URI=mongodb://localhost:27019`.
#
# Postgres carries no default on purpose: `postgres_dsn` starts a `postgres:16`
# testcontainer when CCF_TEST_POSTGRES_DSN is unset, and baking in a DSN would
# disable that and hang against a server nobody started. Neo4j and Mongo have
# no auto-start path, so they default to the ci.yml service-container URIs.
CCF_TEST_NEO4J_URI ?= neo4j://neo4j:ccf_test_password@localhost:7687
CCF_TEST_MONGO_URI ?= mongodb://localhost:27017/ccf_test
CCF_TEST_FLUREE_URL ?= http://localhost:8090

ifneq ($(strip $(CCF_TEST_POSTGRES_DSN)),)
PG_DSN_ENV := CCF_TEST_POSTGRES_DSN=$(CCF_TEST_POSTGRES_DSN)
endif

legs: leg-postgres leg-neo4j leg-mongo leg-fluree ## Run all four container-gated substrate legs (DI-15.2-04)

leg-postgres: ## Postgres leg against a real server — GraphStore conformance + differential (D-11/D-16)
	$(ENV) CCF_REQUIRE_POSTGRES=1 $(PG_DSN_ENV) \
		$(PYTHON) -m pytest tests -q -m postgres -rs

leg-neo4j: ## Neo4j leg against a real server — Cypher pushdown byte-identical to the fallback (plan 15.2-12)
	$(ENV) CCF_REQUIRE_NEO4J=1 CCF_TEST_NEO4J_URI=$(CCF_TEST_NEO4J_URI) \
		$(PYTHON) -m pytest tests -q -m neo4j -rs

leg-mongo: ## MongoDB leg against a real server — staged aggregation pushdown (plan 15.2-13)
	$(ENV) CCF_REQUIRE_MONGO=1 CCF_TEST_MONGO_URI=$(CCF_TEST_MONGO_URI) \
		$(PYTHON) -m pytest tests -q -m mongo -rs

leg-fluree: ## Fluree leg against a real server — Cypher pushdown byte-identical to the fallback (plan 15.3)
	$(ENV) CCF_REQUIRE_FLUREE=1 CCF_TEST_FLUREE_URL=$(CCF_TEST_FLUREE_URL) \
		$(PYTHON) -m pytest tests -q -m fluree -rs

# The Phase 15.3 permitted-change-surface gate and its `tools/gates/` package
# were RETIRED by plan 15.4-07, in the same commit that registered the two
# structural rules replacing them. D-IMPL-93: the per-file added-line budgets
# that D-IMPL-92 itself calls an admitted proxy are superseded by
# `cinv02-backend-import` and `cinv04-substrate-name`/`-prose`, which run in
# `make lint` above and measure direction and recurrence rather than magnitude.
#
# What is NOT retired: D-IMPL-92's normative rule; D-11's hard line on
# mechanism change elsewhere under `src/ccf`; the `docs/GRAPH_QUERY_SEMANTICS
# .md` freeze; the corpus rule; and the prohibition on raising a budget to make
# a gate pass — under D-IMPL-93 the remedy for an exhausted budget is the seam,
# never a larger number, and the seam is what this phase built.
#
# The retired target's own name is deliberately NOT spelled here. The check for
# its removal is a repository-wide grep for that token, so a comment naming
# what it retires would fail the grep it exists to support — the same
# contradiction plan 15.4-06 hit and resolved the same way.

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

# The whole docs gate as one blocking target (D-IMPL-72), in FOUR ordered
# steps. The pre-build structural scan runs FIRST so a symlink or an escaping
# include is reported before the build has a chance to copy it; then the
# committed-schema content scan; then the strict build; then the post-build
# content scan over the tree that would actually ship (D-02). No `|| true`, no
# `-` prefix, no report-only flag anywhere in this recipe: the exit code is the
# only gate signal, exactly as `tools/lints` and `tools/publish_scan.py` both
# state — a non-blocking mode is how an invariant quietly stops being one.
#
# Step 2, added in plan 15.6-03 (DCD-11), and why it sits SECOND rather than
# last. `docs/schemas/` was the one publication channel nothing scanned:
# mkdocs never reads it (D-01 — `public/` is the only tree it reads), but
# `tools/dump_schemas.py` copies class docstrings VERBATIM into `description`
# fields, and those descriptions leave the repo through the committed tree
# adopters author against and through `ccf schema export` (ERGO-12). Whitepaper
# prose reaching a docstring is therefore published with no gate between.
# `D-GATE-15.5` swept the tree by hand and recorded the verdict in its own
# words — "which is clean but is not a gate."
#
# It is committed SOURCE rather than build output, so it does not depend on the
# build and this recipe's own stated ordering principle applies: a check that
# does not need the build should not wait for it, and a leaking schema should
# fail before the build is spent. Placing it here also runs the scanner's
# `self_test_fires()` guard — which reads `WHITEPAPER` independently of the
# scanned tree — before mkdocs runs, so a dead shingle machinery is reported
# early rather than at the end.
#
# It needs no new flag, no new module constant and no new function: `scan_tree`
# reads every file with no suffix allowlist, and `require_populated` already
# exits non-zero on a missing or empty root, so this root inherits the
# fail-closed posture for free. `$(ENV_DOCS)`, not `$(ENV)`: publish_scan.py is
# invoked AS A SCRIPT, so the repo root must be on PYTHONPATH for its
# `from tools.lints import ...`.
docs-strict: ## Blocking docs gate: pre-build scan + schema scan + strict build + site scan (D-IMPL-72, D-02, DCD-11)
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py --pre-build
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py docs/schemas
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

# ERGO-12's committed half, on the same D-12 reasoning as `openapi`: the
# schemas are what adopters author against in their editor, before anything
# runs, so they are committed and reviewed as diffs. The set comes from
# SDK_ARTIFACT_CLASSES; adding an ArtifactClass without re-running this is a
# red build, because the drift assertion lives in the always-on `test` job.
schemas: ## Regenerate the committed docs/schemas/ tree — the ERGO-12 authoring baseline
	$(ENV_DOCS) $(PYTHON) tools/dump_schemas.py

# The assertion half of the `$schema` headers on example artifact documents.
# Auto-arming: a directory joins the checked set as soon as it carries its
# first header, so each example-rewrite plan gates its own headers at its own
# wave. Pass DIR=<path> to check one directory (what a rewrite plan runs in
# its own verify step); --require-all is the tree-wide form for the phase
# close. Also always-on via tests/cli/test_schema_export.py.
schema-headers: ## Verify example artifact $$schema headers name the class that accepts them (DIR=<path> to narrow)
	$(ENV_DOCS) $(PYTHON) tools/check_schema_headers.py $(DIR)

# D-15's generated half: the public surface of every /src and /runtime module
# with an `__all__`, committed so a removed or reshaped export surfaces as a
# reviewable diff. The live manifest is regenerated by exactly two plans in
# Phase 15 (15-01 at phase start, 15-21 at phase close); in-flight plans run
# `tools/dump_surface.py --report` and write a docs/surface-changes/ fragment
# instead. The drift assertion lives in the always-on `test` job.
surface: ## Regenerate the committed public-surface manifest — the D-15 baseline
	$(ENV) $(PYTHON) tools/dump_surface.py

# D-15's curated half: docs/SURFACE-CHANGES.md assembled from the per-plan
# docs/surface-changes/ fragments. The fragments are written incrementally as
# plans land (a migration note assembled retroactively is a note written from
# the diff); this target joins them. The assembler refuses any entry missing
# one of the seven fields, so an incomplete migration note is a red build
# rather than a shipped document. The drift assertion lives in the always-on
# `test` job (tests/test_surface_drift.py).
surface-changes: ## Assemble docs/SURFACE-CHANGES.md from the per-plan fragments — the D-15B migration note
	$(ENV) $(PYTHON) tools/assemble_surface_changes.py

# ERGO-03's measured half (D-11/D-12): the per-file mechanical, assertion, and
# print line counts of the examples tree, committed as the phase-start baseline
# under docs/surface/examples/before/. Criterion 1's report is a re-measurement
# by this same tool, never a re-estimate. `removable` (mechanical wiring) and
# `relocatable` (assertions/prints D-09 moves to tests/) are separate figures
# and are never summed. The audit assertion lives in the always-on `test` job
# (tests/examples/test_surface_audit.py).
#
# `measure-examples` writes the after/ side, which is what the eight example
# rewrite plans need. The before/ baseline is deliberately NOT reachable from
# a make target: it is written once at phase start and rewriting it mid-phase
# destroys the comparison. Use `python tools/measure_examples.py --baseline`
# if you genuinely mean to re-freeze it. Pass ONLY=<path prefix> to restrict a
# run to one example so parallel worktrees do not overwrite each other.
measure-examples: ## Re-measure examples/ mechanical surface into after/ (ONLY=<prefix> to narrow)
	$(ENV) $(PYTHON) tools/measure_examples.py $(if $(ONLY),--only $(ONLY),)
