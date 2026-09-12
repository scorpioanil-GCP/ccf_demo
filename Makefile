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

# Test-suite environment. The repo root joins the path EXPLICITLY because test
# modules import their siblings (`from tests.deployment.conftest import ...`)
# and the surface tooling (`from tools.dump_surface import ...`), and neither
# `tests` nor `tools` is an installed package.
#
# `$(PYTHON) -m pytest` also puts the cwd on sys.path, so `$(ENV)` alone works
# today — but that is a property of the `-m` FORM, not of the environment, and
# relying on it is what broke the remote gate. `.github/workflows/ci.yml`
# spelled the same steps as a bare `pytest` console script, which does NOT add
# the cwd; `tests/` has no top-level `__init__.py`, so pytest inserted each
# test file's own directory instead of the repo root. Result: 13 collection
# ImportErrors, 144 deselected, ZERO tests executed — and the job had been red
# that way since at least 2026-08-10 while every local `make` run stayed green,
# because the two gates were never running the same command
# (run 31967852661, diagnosed 2026-08-16).
#
# Stating the root explicitly makes these targets correct under EITHER
# invocation, so the next person to spell it differently does not reopen this.
ENV_TESTS := PYTHONPATH=.:src:runtime

# The no-external-substrate marker expression, defined ONCE. It appears in two
# CI steps (the quick suite and coverage); two hand-copied spellings is one
# edit away from a filter that silently selects a different set.
NO_SUBSTRATE := not postgres and not chroma and not neo4j and not mongo and not fluree

.DEFAULT_GOAL := help

.PHONY: help venv install lint typecheck test ci-core ci examples gate-tools \
	conformance \
	ci-quick-suite ci-harness-conformance ci-coverage \
	example-s1-01 example-s1-00 example-cp-00 example-cp-01 example-cp-02 \
	example-cp-03 example-cp-04 example-cp-04-canonical example-cp-05 example-cp-05-server \
	example-cp-06 example-cp-07 example-cp-09 \
	example-hw1-harness-clients \
	example-hw1-harness-clients-live-adk \
	example-hw1-harness-clients-live-anthropic \
	example-hw1-harness-clients-live-langgraph \
	legs leg-postgres leg-neo4j leg-mongo leg-fluree \
	perf perf-micro perf-scale perf-xproc perf-replay \
	docs docs-strict docs-serve openapi schemas schema-headers product-gates \
	surface surface-changes measure-examples

help: ## List targets with one-line descriptions
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-28s %s\n", $$1, $$2}'

# THE VENV EVERY OTHER TARGET ASSUMES. `PYTHON := .venv/bin/python` at the top
# of this file is not a request — it is a path, and until this target existed
# nothing in the repository created it. A fresh clone's first `make` died on
# "No such file or directory" naming an interpreter, which tells the reader
# nothing about what to run. Idempotent: an existing `.venv` is left alone.
#
# The version gate is here rather than in `install` because pyproject's
# `requires-python = ">=3.12"` is enforced by pip at install time with a
# message about the wheel, not about the venv the developer just made.
venv: ## Create .venv if missing and install into it — the first command in a fresh clone
	@test -x .venv/bin/python || python3 -m venv .venv
	@.venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' \
		|| { echo "ccf requires Python >= 3.12; .venv has $$(.venv/bin/python -V 2>&1)"; exit 1; }
	@$(MAKE) --no-print-directory install

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

lint: ## CCF invariant lints — CINV-01/02/03/04/06 + orchestration split + citations (blocking, D-07)
	$(ENV) $(PYTHON) -m tools.lints --all

typecheck: ## mypy --strict over src + runtime ([tool.mypy] files is authoritative)
	$(ENV) $(PYTHON) -m mypy

test: ## Full pytest suite with harness legs required (CCF_REQUIRE_HARNESSES=1)
	$(ENV) CCF_REQUIRE_HARNESSES=1 $(PYTHON) -m pytest -q

# ---------------------------------------------------------------------------
# The CI test steps, as targets rather than as command strings in ci.yml.
#
# This file's header states that "the Makefile mirrors .github/workflows/ci.yml
# command-for-command". That invariant was FALSE for every pytest step in the
# tests job: ci.yml spelled them as a bare `pytest`, the Makefile as
# `$(PYTHON) -m pytest`, and the difference decided whether the repo root was
# on sys.path (see ENV_TESTS above). A mirror asserted in a comment is not a
# mirror. These targets make it structural — ci.yml now CALLS the command
# instead of restating it, so the two gates cannot drift apart again.
#
# CI has no `.venv`, so it overrides the interpreter on the command line:
#     make PYTHON=python ci-quick-suite
# A command-line assignment beats the `PYTHON :=` above, which is why that
# works without a second variable.
#
# The four substrate legs are NOT restated here — `leg-postgres`, `leg-neo4j`,
# `leg-mongo` and `leg-fluree` already existed, already used the `-m` form, and
# already set their own CCF_REQUIRE_*; ci.yml now calls those. Their `?=` URI
# defaults match the values ci.yml puts in the job env, and an environment
# value wins over `?=`, so the two agree by construction rather than by luck.
# ---------------------------------------------------------------------------

ci-quick-suite: ## CI: the no-external-substrate suite (mirrors the ci.yml step by calling it)
	$(ENV_TESTS) $(PYTHON) -m pytest tests -q -m "$(NO_SUBSTRATE)" -rs

ci-harness-conformance: ## CI: harness adapter conformance — all three legs must RUN, not skip
	$(ENV_TESTS) $(PYTHON) -m pytest tests/conformance -q -rs

ci-coverage: ## CI: informational coverage over the no-substrate suite (D-17 sets no numeric gate)
	$(ENV_TESTS) $(PYTHON) -m pytest tests -q -m "$(NO_SUBSTRATE)" --cov=ccf --cov-report=term

# `gate-tools` belongs here, not only in `ci`. Plan 17-01 added it to `ci`
# alone — but `ci-core` is what every wave actually runs, so the tools/ suites
# stayed invisible in practice and THREE WAVES SHIPPED PAST A RED GATE
# (DEF-17-08, measured 2026-08-16). A gate the working command does not reach
# is not a gate. This is the fifth instance in Phase 17 of a check that stops
# checking without going red.
#
# `product-gates` joins here for the same reason (plan 24.5-09): a roster
# whose declared id has no executing test is exactly the kind of red that
# stays invisible until a close, and `ci-core` is the command every wave runs.
ci-core: lint typecheck test gate-tools product-gates ## Mid-phase verification sweep — MUST stay green from Wave 1 onward

# The client adapter parity gate (D-15, plan 17-07). A NAME, not a second
# collection path: `[tool.pytest] testpaths = ["tests"]` (pyproject.toml:142)
# already collects `tests/client/conformance` on every `make test`, so this
# target is deliberately NOT a prerequisite of `ci` — adding it would run the
# whole suite twice per `make ci`, which is harmless right up until somebody
# "optimizes" it by deleting the wrong one.
#
# What it buys is that the gate is nameable in a CI job, a review and a SUMMARY.
# A parity gate nobody can name is a parity gate nobody is looking at (Phase 16).
# The reachability it depends on is asserted rather than assumed —
# `tests/client/conformance/test_the_suite_fires.py::test_the_conformance_suite_is_inside_the_default_collection`
# holds this target's path and `testpaths` to each other.
conformance: ## Client adapter conformance suite — the D-15 parity gate, by name
	$(ENV) $(PYTHON) -m pytest tests/client/conformance -q

# Finalized in plan 08-12: `ci` = ci-core + examples is the phase gate
# command, reproducing the always-on Actions pipeline (ci.yml lint + test +
# examples jobs) locally command-for-command (D-10). Live legs are opt-in
# (D-11) and deliberately not part of `ci`; since Phase 23 the surviving ones
# are the three `example-hw1-harness-clients-live-*` targets below, and
# `live-legs.yml` carries only the D-09 fluree drift detector.
#
# Amended in plan 14-10: D-IMPL-72 pre-authorized adding the docs gate to this
# composition, effective at the plan that creates the docs build target. That
# gate is now complete (strict build + publish scan, D-02), so `docs-strict`
# joins `ci` here — never as a half-armed or dead target.
# Amended in plan 17-01: `gate-tools` joins the composition. The claim on the
# line below was false until it did — `[tool.pytest] testpaths = ["tests"]`
# (pyproject.toml:142) stops collection at `tests/`, so the three suites under
# `tools/` were invisible to every local gate while two Actions jobs ran them
# on every push. Two of their tests were failing when Phase 17 opened, and the
# phase would have closed green locally and red in Actions. This is the Phase
# 16 lesson applied to the gate itself: a measurement nobody is looking at
# protects nothing.
# Amended in plan 24.5-09: `product-gates` joins the composition, in BOTH
# `ci-core` above and here, so the product-gate coverage checker
# (`D-IMPL-224`, ledger row `24.5-L-10`) runs on every mid-phase sweep and on
# the phase gate command alike.
ci: ci-core examples docs-strict gate-tools product-gates ## Full local reproduction of the always-on pipeline (D-10)

# The three commands are the `lint` job's "Lint checker unit tests" step, the
# `docs` job's "Docs-gate checker unit tests" step and the `lint` job's
# "Product-gate checker unit tests" step of `.github/workflows/ci.yml`,
# verbatim modulo `$(ENV_DOCS) $(PYTHON) -m`, so this target reproduces what
# CI already runs rather than inventing a fourth command for the same suites.
# `$(ENV_DOCS)`, not `$(ENV)`: these suites do
# `from tools.publish_scan import ...`, `from tools.lints import ...` and
# `from tools.check_product_gates import ...`, so the repo root must be on
# PYTHONPATH — the same reason `docs-strict` uses it.
#
# Who reads the number and what fails when it moves: `make ci` reads it on
# every local run and the two named Actions jobs read it on every push, so a
# regression in any of the three suites now fails the local gate instead of
# surfacing after the phase has been presented.
#
# Scope: `DOCS-08` (Phase 16) owns the full "`make ci` composes the three
# suites" requirement. This target discharges the part Phase 17 needs to make
# its own gate honest and does not claim `DOCS-08`.
gate-tools: ## Run the tools/ suites CI runs that `testpaths` excludes from `make test`
	$(ENV_DOCS) $(PYTHON) -m pytest tools/lints/tests -q
	$(ENV_DOCS) $(PYTHON) -m pytest tools/publish_scan_tests tools/docs_tests -q
	$(ENV_DOCS) $(PYTHON) -m pytest tools/product_gates_tests -q

# The runner is `runner/drive.py`, and BOTH halves of that path are load-bearing.
# The subdirectory keeps the one `ccf`-importing file structurally outside
# `tests/examples/test_client_example_purity.py::reader_visible_modules`, whose
# `glob("*.py")` is non-recursive; the NAME avoids `run.py`, which
# `tests/examples/test_artifact_schema_headers.py` reads as the marker of an
# example root and would then require an `artifacts/` directory beside. Neither
# is tidiable.
#
# `$(ENV) $(PYTHON)`, and the obvious reason is NOT the reason. `$(ENV)` is not
# needed so the runner can `import ccf`: measured at plan revision,
# `env -u PYTHONPATH .venv/bin/python -c "import ccf"` resolves through the
# editable install, and `example-hw1` below already runs `consume.py` — which
# imports `ccf.client` — with no `$(ENV)` prefix at all. The two true reasons:
# it is the house spelling (16 of the 18 `example-*` targets), and it keeps the
# target working in a fresh clone that has not run `pip install -e .`.
# `$(PYTHON)` stays overridable by a job that installs into a hosted
# interpreter — that is the *test* job's posture (`make PYTHON=python`), not a
# blanket CI rule: the examples job provisions a `.venv` and runs bare
# `make examples`, so `$(PYTHON)` is `.venv/bin/python` in the very job that
# runs this target.
example-hw1-harness-clients: ## Run examples/hw1-harness-clients — three harnesses, one door, deterministic
	$(ENV) $(PYTHON) examples/hw1-harness-clients/runner/drive.py

# `s1-01` LED THIS LIST AND NO LONGER DOES (plan 16-05). Its
# `artifacts/manifest.yaml` now declares a networked substrate, and ROADMAP
# criterion 4 puts that substrate among the four opt-in databases while `D-06`
# keeps always-on CI deterministic and network-free. An `examples` job that ran
# the target would need a service container — a third option `D-06` did not
# authorize — so the target moved down beside the container-gated legs.
#
# The example is still exercised in CI, by `make leg-fluree`:
# `tests/examples/test_s1_01_output.py` boots it, and the three gates that need
# no substrate (agent-free AST guard, spine separation, artifact headers) still
# run on this leg.
examples: example-hw1-harness-clients ## Run the network-free examples suite (one member since D-04), stopping on first failure

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

# Section 1's reference example, run as a program rather than as a test — which
# is what a newcomer does first and what the phase's blocking checkpoint reads.
# It lives here rather than in `examples:` above because its manifest declares a
# networked substrate; see that target's comment. No new variable: the default
# is the one the four legs already share.
example-s1-01: ## Run examples/s1-01-hello-context-product (three declared questions; needs a Fluree server)
	$(ENV) CCF_TEST_FLUREE_URL=$(CCF_TEST_FLUREE_URL) \
		$(PYTHON) examples/s1-01-hello-context-product/run.py

# HW-1 — the first example a newcomer runs. Same reasoning as `example-s1-01`
# above for why it is NOT in the `examples:` aggregate: it declares a networked
# substrate. It needs no server of its own, though — `scenario/provision.py`
# starts a postgres:16 container when CCF_TEST_POSTGRES_DSN is unset, so the
# default path needs Docker and nothing else. MIN_REVENUE is OPTIONAL: the
# threshold is a REQUEST parameter, not deployment configuration, and a build
# tool is not a request channel. Omitted, `consume.py` asks the demonstration
# question in `scenario/question.yaml`. The contract still requires the
# parameter — a request without one is refused with `missing-required-parameter`
# below this CLI (test_a_missing_threshold_is_refused_not_defaulted).
example-s1-00: ## Run examples/s1-00-companies-over-revenue (MIN_REVENUE=<n> optional; needs Docker or CCF_TEST_POSTGRES_DSN)
	$(ENV) CCF_TEST_POSTGRES_DSN=$(CCF_TEST_POSTGRES_DSN) \
		$(PYTHON) examples/s1-00-companies-over-revenue/consume.py \
		$(if $(MIN_REVENUE),--min-revenue $(MIN_REVENUE))

# CP-00 — the first Context Product, and the first example that points at a
# system of record CI cannot reach. NOT in the `examples:` aggregate above, and
# the omission is deliberate rather than an oversight: this target reads a real
# 13F estate through the environment-variable name `backends.yaml` declares, and
# `24-CONTEXT.md` `D-15` accepts that cost so the example points at a real store
# rather than at a shipped copy of one. There is no in-tree fixture it could
# fall back onto and there must not be.
#
# ITS CODE PATH IS STILL COVERED IN CI, so do not "fix" the omission by adding
# it here. `tests/examples/test_cp_00_output.py` is marked `postgres`, seeds a
# `postgres:16` service container itself from `tests/examples/fixtures/`, and
# runs this example's own modules against it under `make leg-postgres`
# (`24-CONTEXT.md` `D-25`/`D-27`). The target runs the program; the leg proves
# the program.
#
# MIN_POSITION is OPTIONAL, for the same reason MIN_REVENUE is above: the
# threshold is a REQUEST parameter, not deployment configuration, and a build
# tool is not a request channel. Omitted, `run.py` asks the demonstration
# question in `artifacts/question.yaml`. The contract still requires the
# parameter -- a request without one is refused as `missing-required-parameter`
# below this CLI. SPEC is `full` or `brief` and picks how much of the
# specification is printed above the JSON.
example-cp-00: ## Run examples/cp-00-institutional-holders (MIN_POSITION=<n>, SPEC=full|brief optional; needs CCF_CP_00_POSTGRES_DSN)
	$(ENV) $(PYTHON) examples/cp-00-institutional-holders/run.py \
		$(if $(MIN_POSITION),--min-position $(MIN_POSITION)) \
		$(if $(SPEC),--spec $(SPEC))

# CP-01 — the second Context Product, and rung 1 of the vault's complexity
# ladder. Same posture as `example-cp-00` above and for the same reasons: NOT in
# the `examples:` aggregate, because it reads a real counterparty estate through
# the environment-variable name `backends.yaml` declares and there is no in-tree
# fixture it could fall back onto.
#
# ITS CODE PATH IS COVERED IN CI ALREADY, so do not "fix" the omission by adding
# it to `examples:`. `tests/examples/test_cp_01_output.py` sets
# `pytestmark = pytest.mark.postgres`, seeds a `postgres:16` service container
# itself from `tests/examples/fixtures/cp_01_*.sql`, and runs this example's own
# modules against it — so `leg-postgres` selects its 13 tests by MARKER, without
# this file naming them. The target runs the program; the leg proves the program.
#
# EVERY PARAMETER IS OPTIONAL, for the reason MIN_POSITION is optional above:
# these are REQUEST parameters, not deployment configuration, and a build tool is
# not a request channel. Omitted, `run.py` asks the demonstration question in
# `artifacts/question.yaml`. INCLUDE_LAPSED is a flag — set it to any non-empty
# value. AS_OF is declared by the contract and ALWAYS refused at this tier; it is
# exposed here so the refusal is one command away rather than a paragraph.
example-cp-01: ## Run examples/cp-01-counterparty-reference-snapshot (ANCHOR, PRINCIPAL, INCLUDE_LAPSED, AS_OF, DEBT_TOLERANCE optional; needs CCF_CP_01_POSTGRES_DSN)
	$(ENV) $(PYTHON) examples/cp-01-counterparty-reference-snapshot/run.py \
		$(if $(ANCHOR),--anchor $(ANCHOR)) \
		$(if $(PRINCIPAL),--principal $(PRINCIPAL)) \
		$(if $(INCLUDE_LAPSED),--include-lapsed) \
		$(if $(AS_OF),--as-of $(AS_OF)) \
		$(if $(DEBT_TOLERANCE),--debt-tolerance $(DEBT_TOLERANCE))

# cp-02 — rung 02 of the vault's ladder. Like cp-01 it reads a NETWORKED estate
# through an environment variable and is therefore NOT in the `examples:`
# aggregate: there is no in-tree fixture it can fall back onto, and a red check
# nobody can make green is worse than no check. Its code path is still covered
# in CI, by a different mechanism — `tests/examples/test_cp_02_output.py` is
# marked for the postgres leg, seeds its own service container, and the
# `leg-postgres` target selects it BY MARKER. The target runs the program; the
# leg proves it.
#
# EVERY REQUEST PARAMETER IS OPTIONAL. A facility, a principal, an asked-at and
# a debt tolerance are request parameters, not deployment configuration, and a
# build tool is not a request channel. Omitted, `run.py` asks the demonstration
# question declared in `artifacts/question.yaml`.
example-cp-02: ## Run examples/cp-02-facility-terms-snapshot (FACILITY, PRINCIPAL, ASKED_AT, AS_OF, DEBT_TOLERANCE, NO_PRICING_GRID optional; needs CCF_CP_02_POSTGRES_DSN)
	$(ENV) $(PYTHON) examples/cp-02-facility-terms-snapshot/run.py \
		$(if $(FACILITY),--facility $(FACILITY)) \
		$(if $(PRINCIPAL),--principal $(PRINCIPAL)) \
		$(if $(ASKED_AT),--asked-at $(ASKED_AT)) \
		$(if $(NO_PRICING_GRID),--no-pricing-grid) \
		$(if $(AS_OF),--as-of $(AS_OF)) \
		$(if $(DEBT_TOLERANCE),--debt-tolerance $(DEBT_TOLERANCE))

# cp-03 — rung 03 of the vault's ladder and the last of Tier 1. Networked
# estate through an environment variable, so NOT in the `examples:` aggregate,
# for the reason given above cp-02. `tests/examples/test_cp_03_output.py` and
# `test_cp_03_census.py` are both marked for the postgres leg, seed their own
# container from `tests/examples/fixtures/`, and are selected BY MARKER.
#
# EVERY REQUEST PARAMETER IS OPTIONAL. Omitted, `run.py` asks the demonstration
# question in `artifacts/question.yaml`. BASIS is the one this rung exists for:
# both settings are correct and the decision picks, so there is no default that
# is "right" — only one that is declared.
example-cp-03: ## Run examples/cp-03-obligor-financial-spread (LEI, PERIODS, BASIS, PRINCIPAL, ASKED_AT, AS_OF, DEBT_TOLERANCE, PEER_BASIS, NO_PEERS optional; needs CCF_CP_03_POSTGRES_DSN)
	$(ENV) $(PYTHON) examples/cp-03-obligor-financial-spread/run.py \
		$(if $(LEI),--lei $(LEI)) \
		$(if $(PERIODS),--periods $(PERIODS)) \
		$(if $(BASIS),--basis $(BASIS)) \
		$(if $(NO_PEERS),--no-peers) \
		$(if $(PEER_BASIS),--peer-basis $(PEER_BASIS)) \
		$(if $(PRINCIPAL),--principal $(PRINCIPAL)) \
		$(if $(ASKED_AT),--asked-at $(ASKED_AT)) \
		$(if $(AS_OF),--as-of $(AS_OF)) \
		$(if $(DEBT_TOLERANCE),--debt-tolerance $(DEBT_TOLERANCE))

# cp-04 — rung 04 of the vault's ladder and the FIRST of Tier 2: the first
# product that opens more than one store. NOT in the `examples:` aggregate, and
# for a stronger version of the reason cp-01 through cp-03 are not: this example
# declares TWO networked substrates — a Fluree ledger for edges, ontology,
# labels and LEIs, and a PostgreSQL schema for attributes — and there is no
# in-tree fixture it can fall back onto for either. A red check nobody can make
# green is worse than no check.
#
# ITS CODE PATH IS STILL COVERED IN CI, by the MARKER legs rather than by this
# target. `tests/examples/test_cp_04_*.py` carry `pytest.mark.fluree` and
# `pytest.mark.postgres`, seed their own containers from
# `tests/examples/fixtures/` through `tests/examples/cp_04_seed.py`, and
# `leg-fluree` and `leg-postgres` select them BY MARKER over the whole `tests`
# tree without this file naming one of them. The target runs the program; the
# legs prove the program.
#
# EVERY REQUEST PARAMETER IS OPTIONAL. An anchor, a depth, a role, an asked-at
# and an as-of are request parameters, not deployment configuration, and a build
# tool is not a request channel. Omitted, `run.py` asks the demonstration
# question in `artifacts/question.yaml`. MAX_DEPTH is the one this rung exists
# for — above the declared ceiling it is REFUSED BY NAME and never clamped, and
# two depths are two content addresses. AS_OF is declared by the contract and
# ALWAYS refused at this tier; it is exposed so the refusal is one command away
# rather than a paragraph.
#
# FOUR CONNECTION VARIABLES, TWO PER LEG, AND THE TARGET NAMES ONLY THEIR NAMES.
# `examples/cp-04-corporate-family-tree/backends.yaml` holds each name and its
# remedy string; no host, port, path or credential appears here or there.
example-cp-04: ## Run examples/cp-04-corporate-family-tree (LEI, MAX_DEPTH, ROLE, ASKED_AT, AS_OF optional; needs CCF_CP_04_FLUREE_URL, CCF_CP_04_FLUREE_LEDGER, CCF_CP_04_POSTGRES_DSN, CCF_CP_04_POSTGRES_SCHEMA)
	$(ENV) $(PYTHON) examples/cp-04-corporate-family-tree/run.py \
		$(if $(LEI),--lei $(LEI)) \
		$(if $(MAX_DEPTH),--max-depth $(MAX_DEPTH)) \
		$(if $(ROLE),--role $(ROLE)) \
		$(if $(ASKED_AT),--asked-at $(ASKED_AT)) \
		$(if $(AS_OF),--as-of $(AS_OF))

# cp-04-canonical — the CANONICAL rung-4 successor. Same business question as
# `example-cp-04` above, authored against the current SDK surface; cp-04 itself
# stays frozen as the historical specimen (`D-IMPL-261`, `D-IMPL-313`).
#
# NOT in the `examples:` aggregate, for cp-05's reason: it reads the curated
# `.76` estate through declared environment variables and has no in-tree
# fixture to fall back onto, so a red check nobody can make green would be
# worse than no check.
#
# FOUR CONNECTION VARIABLES, AND THE TARGET NAMES ONLY THEIR NAMES.
# `examples/cp-04-canonical-corporate-family-tree/backends.yaml` holds each name
# and its remedy string; no host, port, schema or credential appears here.
#
# POINT THEM AT THE v2 NAMESPACES — Fluree ledger `fibo-v2`, PostgreSQL schema
# `ccf_v2` — never the v1 names in `ccf_dataprep/.env` (CLAUDE.md §9).
example-cp-04-canonical: ## Run examples/cp-04-canonical-corporate-family-tree (LEI, MAX_DEPTH optional; needs CCF_CP_04C_FLUREE_URL, CCF_CP_04C_FLUREE_LEDGER, CCF_CP_04C_POSTGRES_DSN, CCF_CP_04C_POSTGRES_SCHEMA)
	PYTHONPATH=src:runtime:examples/cp-04-canonical-corporate-family-tree \
		$(PYTHON) examples/cp-04-canonical-corporate-family-tree/run.py \
		$(if $(LEI),--lei $(LEI)) \
		$(if $(MAX_DEPTH),--max-depth $(MAX_DEPTH))

# cp-06 — the ladder's rung 6, collateral & set-off coverage. NOT in the
# `examples:` aggregate, for cp-05's reason: it reads the curated estate through
# declared environment variables and has no in-tree fixture to fall back onto,
# so a red check nobody can make green would be worse than no check.
#
# FOUR CONNECTION VARIABLES, AND THE TARGET NAMES ONLY THEIR NAMES. Point them
# at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2` — never the v1
# names in `ccf_dataprep/.env` (CLAUDE.md §9).
example-cp-06: ## Run examples/cp-06-collateral-and-setoff-coverage (FACILITY, SCOPE, HAIRCUTS, SETOFF, BASIS, SHARED optional; needs CCF_CP_06_FLUREE_URL, CCF_CP_06_FLUREE_LEDGER, CCF_CP_06_POSTGRES_DSN, CCF_CP_06_POSTGRES_SCHEMA)
	PYTHONPATH=src:runtime:examples/cp-06-collateral-and-setoff-coverage \
		$(PYTHON) examples/cp-06-collateral-and-setoff-coverage/run.py \
		$(FACILITY) $(SCOPE) $(HAIRCUTS) $(SETOFF) $(BASIS) $(SHARED)

# cp-07 — the ladder's rung 7. NOT in the `examples:` aggregate, for the same
# reason cp-06 is not: it reads a networked estate through declared environment
# variables and has no in-tree fixture to fall back onto.
#
# FOUR CONNECTION VARIABLES, AND THE TARGET NAMES ONLY THEIR NAMES. Point them
# at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2` — never the v1
# names in `ccf_dataprep/.env` (CLAUDE.md §9).
example-cp-07: ## Run examples/cp-07-client-360-coverage-graph (LEI, SCOPE, SINCE, LIMIT, FAMILY, NTK optional; needs CCF_CP_07_FLUREE_URL, CCF_CP_07_FLUREE_LEDGER, CCF_CP_07_POSTGRES_DSN, CCF_CP_07_POSTGRES_SCHEMA)
	PYTHONPATH=src:runtime:examples/cp-07-client-360-coverage-graph \
		$(PYTHON) examples/cp-07-client-360-coverage-graph/run.py \
		$(LEI) $(SCOPE) $(SINCE) $(LIMIT) $(FAMILY) $(NTK)

# cp-09 — the ladder's rung 9. NOT in the `examples:` aggregate, for the reason
# every networked rung is excluded: it reads a live estate through declared
# environment variables and has no in-tree fixture to fall back onto, so a red
# check nobody can make green would be worse than no check
# (`example_delivery.md` §3). Its code path IS covered — by
# `tests/examples/test_cp_09_output.py`, which the `leg-postgres` and
# `leg-fluree` targets select by marker.
#
# EVERY PARAMETER IS OPTIONAL. Omitted, `run.py` asks the demonstration
# question in `artifacts/question.yaml`: a threshold, an anchor and an as-of
# date are REQUEST parameters, and a build tool is not a request channel.
example-cp-09: ## Run examples/cp-09-treasury-liquidity-position (LEI, AS_OF, INTENT, CURRENCIES, MAX_STALENESS optional; needs CCF_CP_09_FLUREE_URL, CCF_CP_09_FLUREE_LEDGER, CCF_CP_09_POSTGRES_DSN, CCF_CP_09_POSTGRES_SCHEMA)
	PYTHONPATH=src:runtime:examples/cp-09-treasury-liquidity-position \
		$(PYTHON) examples/cp-09-treasury-liquidity-position/run.py \
		$(if $(LEI),--lei $(LEI)) $(if $(AS_OF),--as-of $(AS_OF)) \
		$(if $(INTENT),--intent $(INTENT)) \
		$(if $(CURRENCIES),--currencies $(CURRENCIES)) \
		$(if $(MAX_STALENESS),--max-staleness $(MAX_STALENESS))

# cp-05 — the ladder's rung 5. NOT in the `examples:` aggregate: it reads a
# networked estate through declared environment variables and has no in-tree
# fixture to fall back onto, so a red check nobody can make green would be worse
# than no check (`example_delivery.md` §3).
#
# IT HAS NO TEST IN THIS TREE, AND THE ABSENCE IS STATED RATHER THAN IMPLIED.
# An earlier revision of this comment claimed coverage by
# `tests/examples/test_cp_05_output.py`; that file does not exist and never
# did. cp-05's executable evidence is `page/run-transcript.txt` and
# `page/scenario-transcript.txt`, both reproduced against the pinned instant in
# `artifacts/question.yaml`. A regression test is owed when — and only when —
# cp-05 drives an SDK repair, at which point it names the SDK behavior it
# protects (`D-IMPL-276`).
example-cp-05: ## Run examples/cp-05-credit-exposure-rollup (LEI, INTENT, DEPTH, MATERIALITY, DEBT_TOLERANCE, BASIS, SCENARIOS=1 optional; needs CCF_CP_05_FLUREE_URL, CCF_CP_05_FLUREE_LEDGER, CCF_CP_05_POSTGRES_DSN, CCF_CP_05_POSTGRES_SCHEMA)
	$(ENV) $(PYTHON) examples/cp-05-credit-exposure-rollup/run.py \
		$(if $(SCENARIOS),--scenarios) \
		$(if $(LEI),--lei $(LEI)) \
		$(if $(INTENT),--intent $(INTENT)) \
		$(if $(DEPTH),--depth $(DEPTH)) \
		$(if $(MATERIALITY),--materiality $(MATERIALITY)) \
		$(if $(DEBT_TOLERANCE),--debt-tolerance $(DEBT_TOLERANCE)) \
		$(if $(BASIS),--basis $(BASIS))

# cp-05's MCP door. Serves on stdio: the client spawns it, and the transport's
# security boundary is process ownership (stdio carries no bearer channel).
# Reads the same four environment variables `example-cp-05` does.
example-cp-05-server: ## Serve examples/cp-05-credit-exposure-rollup over MCP on stdio
	$(ENV) $(PYTHON) examples/cp-05-credit-exposure-rollup/server/serve.py

# HW-1 — the first example a newcomer reads. NOT in the `examples:` aggregate
# and NOT in any workflow as a target: what CI runs is
# `tests/examples/test_hw1_two_transports.py`, which copies the example, seeds
# the copy from its declared input and runs both documented commands against
# it on every push — the same two strings the two targets below run.
#
# THE SEED STEP. `D-IMPL-245` amendment 2 (Dave, 2026-09-03): the deployment is
# populated by the example's own pre-boot seed program from a committed,
# declared signal-batch input (`runner/signal-batch.yaml`) through the fabric's
# single writer, before either transport boots. The input is committed; the
# store the seed writes (`deployment/graph.sqlite3`, `deployment/artifact-store/`)
# is generated state and is ignored. Both consume targets depend on this one,
# so `make example-hw1` on a clean checkout seeds and then answers. The seed
# rebuilds the store from the document every run, which is what keeps the
# printed content address the same from one run to the next.
.PHONY: example-hw1-seed
example-hw1-seed: ## Populate examples/hw1-companies-over-revenue from its declared signal-batch input (runner/seed.py)
	.venv/bin/python examples/hw1-companies-over-revenue/runner/seed.py

# THIS TARGET DELIBERATELY DOES NOT USE $(PYTHON) OR $(ENV), and that is the
# one place in this file where spelling the interpreter is correct rather than
# sloppy. The README documents this exact string for a reader to type, and
# `$(PYTHON)` is not a string anybody can type; `which python` returns nothing
# in this repository, so a documented bare `python` would not run either.
# `tests/examples/test_client_example_purity.py` asserts the recipe below and
# the README's command block are character-identical. Please do not "fix" this
# back into a variable — it silently breaks that assertion's whole point.
#
# No MIN_REVENUE variable: a threshold is a REQUEST parameter and a build tool
# is not a request channel (the s1-00 ruling, D-18).
.PHONY: example-hw1
example-hw1: example-hw1-seed ## Run examples/hw1-companies-over-revenue (seeds first; never CI)
	CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00

# THE SAME `consume.py`, THE SAME DEPLOYMENT, THE OTHER TRANSPORT. `D-IMPL-150`
# (Dave, 2026-08-17): plan `17-10` claimed this invocation and it did not run,
# because `D-05` requires a scheme to reach the registry by its adapter module
# being imported and `consume.py` imported one. Both are imported now, so the
# only difference between this target and the one above is the value of
# `CCF_BINDING` — which is the client abstraction's entire claim, demonstrated
# rather than asserted.
#
# The address is ONE token, the deployment root — the same token the target
# above names, which is why the two recipes differ by exactly one word. Which
# program this transport launches is the deployment's own business, declared
# under `server:` in its `binding.yaml`, because the SDK ships no server program
# (CINV-01) and cannot. A deployment reached at an endpoint declares no `server:`
# at all.
#
# The same interpreter rule applies as above, for the same reason.
.PHONY: example-hw1-mcp
example-hw1-mcp: example-hw1-seed ## Run examples/hw1-companies-over-revenue over MCP stdio (same consume.py; seeds first)
	CCF_BINDING="mcp+stdio:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00

# ONE LEG AT A TIME, for examples/hw1-harness-clients. These are the DOCUMENTED
# targets — `examples/hw1-harness-clients/README.md` states these three strings
# in fenced blocks for a reader to type, and
# `tests/examples/test_client_example_purity.py` asserts each block is
# character-identical to the recipe below it AND that the three differ at
# exactly one token position: the leg name. That second assertion is this
# example's whole frame — one product, one door, three harnesses — turned into
# a check, and it is why the three recipes must stay structurally identical.
#
# The same interpreter rule as the two targets above, for the same reason:
# `.venv/bin/python` spelled literally, never `$(PYTHON)`, because `$(PYTHON)`
# is not a string a reader can type and `which python` returns nothing in this
# repository. Please do not "fix" these back into a variable.
#
# These are deliberately NOT prerequisites of `examples:`. That list runs
# `example-hw1-harness-clients` above, which drives all three legs plus the
# reference in one pass and uses `$(ENV) $(PYTHON)` because CI has no `.venv`.
# The split is the same two-target shape `example-hw1` / `example-hw1-mcp`
# already have: one spelling for CI, one spelling for a reader.
.PHONY: example-hw1-harness-clients-adk example-hw1-harness-clients-anthropic example-hw1-harness-clients-langgraph
example-hw1-harness-clients-adk: ## Run examples/hw1-harness-clients, Google ADK leg only
	.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk

example-hw1-harness-clients-anthropic: ## Run examples/hw1-harness-clients, Claude Agent SDK leg only
	.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic

example-hw1-harness-clients-langgraph: ## Run examples/hw1-harness-clients, LangGraph leg only
	.venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph

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

# The three `--live` opt-ins for examples/hw1-harness-clients. `--live` means
# ONE thing across every leg (`H-09`): point at the real tracked deployment
# instead of the seeded temporary copy, which requires it to already be
# populated — and for leg 2 it additionally drops the model stand-in, so THAT
# leg needs `ANTHROPIC_BASE_URL` set explicitly. The runner deliberately stops
# injecting it under `--live` and the client refuses rather than falling back to
# a vendor endpoint; the README says the same sentence.
#
# These are deliberately NOT prerequisites of `examples:` and never run in CI.
# A red check nobody can make green is worse than no check: the always-on
# pipeline holds no populated deployment and no credentials, so a live target on
# that line would fail on every push for a reason that has nothing to do with
# the code. `tests/examples/test_hw1_harness_clients_readme.py` asserts both
# halves — that all three exist, and that none of them is on `examples:`.
example-hw1-harness-clients-live-adk: ## examples/hw1-harness-clients ADK leg against a real populated deployment (opt-in; never CI)
	$(ENV) $(PYTHON) examples/hw1-harness-clients/runner/drive.py --live --legs adk

example-hw1-harness-clients-live-anthropic: ## examples/hw1-harness-clients Claude Agent SDK leg live, real model (opt-in; never CI — set ANTHROPIC_BASE_URL)
	$(ENV) $(PYTHON) examples/hw1-harness-clients/runner/drive.py --live --legs anthropic

example-hw1-harness-clients-live-langgraph: ## examples/hw1-harness-clients LangGraph leg against a real populated deployment (opt-in; never CI)
	$(ENV) $(PYTHON) examples/hw1-harness-clients/runner/drive.py --live --legs langgraph

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

# The product-gate coverage checker `D-IMPL-224` ordered (ledger row
# `24.5-L-10`). Every `examples/cp-*` rung must carry `artifacts/gates.yaml`
# with closed keys and a DECLARED test-naming convention; every declared id
# must resolve to a test a REAL `pytest --collect-only` over `tests/examples/`
# collects, and no test may name an id its roster does not declare. Never an
# `id in file` substring match — two earlier instruments keyed on function
# names and on substrings reported 0/8, 0/9, 0/9 falsely across this ladder.
# `hw1-*` and `s1-*` are outside the glob by construction. The checker's own
# tests run under `gate-tools` above; `.github/workflows/ci.yml` CALLS this
# target from the `lint` job rather than restating the command (D-10).
product-gates: ## Verify every examples/cp-* gates.yaml declares exactly the ids with EXECUTING tests (D-IMPL-224; 24.5-L-10)
	$(ENV_DOCS) $(PYTHON) tools/check_product_gates.py

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
# and are never summed. **There is no standing audit assertion over this
# measurement any more.** This comment named
# `tests/examples/test_surface_audit.py` in the always-on `test` job. That
# module shipped in plan 15-03 and was deleted in commit 2c52b5f (plan 16-01)
# without this sentence being updated, so the comment has been pointing a
# reader at a gate that has not existed since. Corrected rather than deleted
# so the absence is legible: the only standing gate over the examples tree's
# retirement surface is `tools/docs_tests/test_retirement_sweep.py`, which
# asserts coupling ownership, not surface line counts. Measured by plan 17-08.
#
# `measure-examples` writes the after/ side, which is what the eight example
# rewrite plans need. The before/ baseline is deliberately NOT reachable from
# a make target: it is written once at phase start and rewriting it mid-phase
# destroys the comparison. Use `$(PYTHON) tools/measure_examples.py --baseline`
# if you genuinely mean to re-freeze it — there is no bare `python` on PATH,
# so the previously-written spelling exits non-zero unconditionally
# (`D-IMPL-143`, `docs/DECISIONS.md`). Pass ONLY=<path prefix> to restrict a
# run to one example so parallel worktrees do not overwrite each other.
measure-examples: ## Re-measure examples/ mechanical surface into after/ (ONLY=<prefix> to narrow)
	$(ENV) $(PYTHON) tools/measure_examples.py $(if $(ONLY),--only $(ONLY),)
