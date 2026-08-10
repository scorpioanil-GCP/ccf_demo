---
phase: 16
slug: documentation-rewrite-the-deterministic-path-the-adoption-ar
status: planned
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-09
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `16-RESEARCH.md` § *Validation Architecture* (V-1..V-10).
> The Per-Task Verification Map is filled by `gsd-planner`; everything above it
> is verified-by-execution and stable.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` (plus `pytest-cov`; `pytest-benchmark` for `perf/` only) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]`, `testpaths = ["tests"]`, 8 registered markers |
| **Quick run command** | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests -q -m "not postgres and not chroma and not neo4j and not mongo and not fluree"` |
| **Full suite command** | `make ci` (= `lint typecheck test examples docs-strict`) |
| **Gate-checker suites CI runs but `make ci` does not** | `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q` — **453 passed / 3 failed at HEAD** |
| **Substrate legs** | `make legs` = `leg-postgres leg-neo4j leg-mongo leg-fluree` |
| **Estimated runtime** | quick ~90s; `make ci` several minutes; `examples` job budget 20 min |

---

## Sampling Rate

- **After every task commit:** `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples -q` + `make lint`
- **After every plan wave:** `make ci` — **must include `docs-strict`**, the gate that catches a dangling snippet include — plus `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q`
- **Before `/gsd:verify-work`:** `make ci` green, the three gate-checker suites green, `make legs` green against containers, the DGX opt-in workflow dispatched once and green
- **Max feedback latency:** 120 seconds for the per-task loop

**Accepted exception — six tasks verify with `make ci`, which exceeds the
120-second target.** Recorded as a decision rather than left as an oversight.
The tasks are `16-12 T1` (bare `make ci`), `16-15 T2`, `16-17 T2`, `16-18 T2`,
`16-18 T3` and `16-19 T2` — measured by `grep -n "<automated>make ci" *-PLAN.md`
across the plan set. The exception is **inherent to this phase's subject**: each
of those tasks either changes the `make ci` composition itself (16-12), deletes
examples that `make ci` runs (16-15, 16-17, 16-18), or gates the phase on the
full pipeline (16-19). A narrower command would verify something other than what
the task changes, which is worse than a slow one. Mitigation is the per-task loop
above (`pytest tests/examples -q` + `make lint`), which stays inside 120 seconds
and runs first; `make ci` is the task's closing gate, not its inner loop. No
other task may adopt `make ci` as its `<automated>` without adding itself here.

---

## Per-Task Verification Map

*Populated by `gsd-planner`. One row per task, anchored to a V-number below.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01 T1 | 16-01 | 1 | DOCS-07 | T-16-01-01 | whitepaper cited by section number only | gate | pytest tools/lints/tests -q && grep -c 'D-IMPL-94' docs/DECISIONS.md | docs/DECISIONS.md | ⬜ pending |
| 16-01 T2 | 16-01 | 1 | DOCS-07 | T-16-01-02 | frozen evidence preserved before deletion | unit | pytest tests -q -m 'not postgres and not chroma and not neo4j and not mongo and not fluree' | docs/surface/examples/ERGO-03-FROZEN.md | ⬜ pending |
| 16-01 T3 | 16-01 | 1 | DOCS-07 | T-16-01-03 | carve-out scope confirmed by a human | manual | checkpoint:human-verify | — | ⬜ pending |
| 16-02 T1 | 16-02 | 2 | DOCS-09 | T-16-02-01, T-16-02-05 | no credential or host literal in artifact; artifact-directory coverage reshaped to a two-sided bijection with per-directory non-vacuity and a proven refusal each way, keyed on the example-root predicate *a directory directly containing `run.py`* and proven to exclude `legs/` and `fixtures/`; **this plan ships that root's minimal `run.py` at wave 2** so the bijection closes on the tree it leaves behind (11 artifact dirs vs 11 example roots) rather than on the wave-3 tree, and the "plus this plan's new root" clause is gone | unit | pytest tests/examples/test_artifact_schema_headers.py -q && test -f examples/s1-01-hello-context-product/run.py | examples/s1-01-hello-context-product/artifacts/source-estate.yaml, examples/s1-01-hello-context-product/run.py, tests/examples/test_artifact_schema_headers.py | ⬜ pending |
| 16-02 T2 | 16-02 | 2 | DOCS-09 | T-16-02-03 | generator holds no graph writer | unit | pytest tests/examples/test_source_estate.py -q | tests/examples/test_source_estate.py | ⬜ pending |
| 16-02 T3 | 16-02 | 2 | DOCS-09 | T-16-02-02 | additive load verified before write | manual | checkpoint:human-verify | — | ⬜ pending |
| 16-03 T1 | 16-03 | 2 | DOCS-13 | T-16-03-SC | no new dependency installed | unit | python -c AST-scan of client_langgraph.py for ccf imports | examples/s2-01-external-consumers/client_langgraph.py | ⬜ pending |
| 16-03 T2 | 16-03 | 2 | DOCS-13 | T-16-03-01 | bearer token from env, no anonymous mode | unit | python -c AST-scan of client_claude_agent.py for ccf imports | examples/s2-01-external-consumers/client_claude_agent.py | ⬜ pending |
| 16-03 T3 | 16-03 | 2 | DOCS-13 | T-16-03-04 | shipped external example untouched | integration | pytest tests/examples/test_s2_client_transport_spike.py -q | tests/examples/test_s2_client_transport_spike.py | ⬜ pending |
| 16-04 T1 | 16-04 | 2 | DOCS-08 | T-16-04-01 | no whitepaper shingle in a published docstring | gate | pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q | src/ccf/controlplane/artifacts.py | ⬜ pending |
| 16-04 T2 | 16-04 | 2 | DOCS-17 | T-16-04-03 | gate proven to refuse an injected violation | gate | pytest tools/docs_tests/test_gate_two_wording.py -q | tools/docs_tests/test_gate_two_wording.py | ⬜ pending |
| 16-04 T3 | 16-04 | 2 | DOCS-17 | T-16-04-03 | no vacuous pass; CWD-independent walk | gate | pytest tools/docs_tests -q | tools/docs_tests/test_no_stale_example_paths.py | ⬜ pending |
| 16-21 T1 | 16-21 | 2 | DOCS-17 | T-16-21-01, T-16-21-02, T-16-21-04 | repo-wide sweep; **all four no-path-token shapes** detected — `MINIMUM_*` constants, module-level scan functions, inline tree-witness assertions, and **indirect executions** (a test under `tests/` running a suite outside `tests/` that constructs a retiring path from `__file__`, measured instance `tests/perf_smoke/test_smoke.py` → `perf/suites/crossproc/conftest.py` → `examples/04-cross-process`, owner 16-17); zero UNASSIGNED rows with no narration escape; CWD-independent, non-vacuous | gate | python tools/retirement_sweep.py --report && pytest tools/docs_tests/test_retirement_sweep.py -q | tools/retirement_sweep.py, tools/docs_tests/test_retirement_sweep.py, docs/surface/examples/RETIREMENT-COUPLINGS.md | ⬜ pending |
| 16-05 T1 | 16-05 | 3 | DOCS-11 | T-16-05-01 | no connection value in a content-hashed manifest; spine contributes one gate call site, projecting body and resolved binder site (floor headroom, W-4); `run.py` **replaced in place** (plan 16-02 created it at wave 2) so the artifact-header bijection never sees a missing example root | integration | python examples/s1-01-hello-context-product/run.py && python -m tools.lints --all && pytest tests/examples/test_artifact_schema_headers.py -q | examples/s1-01-hello-context-product/spine.py, examples/s1-01-hello-context-product/run.py | ⬜ pending |
| 16-05 T2 | 16-05 | 3 | DOCS-12 | T-16-05-04 | agent-free guard catches the CR-02 spelling | unit | pytest tests/examples/test_s1_01_output.py tests/examples/test_section_one_is_agent_free.py tests/examples/test_spine_separation.py -q | tests/examples/test_section_one_is_agent_free.py | ⬜ pending |
| 16-05 T3 | 16-05 | 3 | DOCS-11 | T-16-05-01 | split legible to a repository reader | manual | checkpoint:human-verify | — | ⬜ pending |
| 16-06 T1 | 16-06 | 3 | DOCS-16 | T-16-06-03 | unruled question not published | gate | tools/publish_scan.py --pre-build && make docs-strict | public/how-to/write-a-graph-backend-adapter.md | ⬜ pending |
| 16-06 T2 | 16-06 | 3 | DOCS-16 | T-16-06-01 | maintainer page passes pub02-internal-path | gate | tools/publish_scan.py --pre-build && make docs-strict | public/reference/surface-toolchain.md | ⬜ pending |
| 16-06 T3 | 16-06 | 3 | DOCS-16 | T-16-06-04 | documented boot() signature tracks the code | gate | pytest tools/docs_tests -q && make docs-strict | tools/docs_tests/test_advisory_discharge.py | ⬜ pending |
| 16-07 T1 | 16-07 | 4 | DOCS-10 | T-16-07-01 | backend resolved from a configuration artifact; no per-backend code fork; no DGX host literal; env-supplied endpoints | integration | run.py --backend sqlite && run.py --backend memory && git grep 192.168.4.76 | examples/s1-01-hello-context-product/artifacts/backends.yaml, examples/s1-01-hello-context-product/connection.py | ⬜ pending |
| 16-07 T2 | 16-07 | 4 | DOCS-10 | T-16-07-02, T-16-07-03 | non-loopback egress refused and guard fires; three-part one-driver proof | unit | pytest tests/examples/test_backend_matrix.py -q -m 'not postgres and not neo4j and not mongo and not fluree' -rs | tests/examples/test_backend_matrix.py, examples/s1-01-hello-context-product/guards.py | ⬜ pending |
| 16-08 T1 | 16-08 | 4 | DOCS-12 | T-16-08-01 | thresholds and decay rates in artifacts only; artifact-header gate arms on the new directory with no source edit | integration | python examples/s1-02-freshness-and-debt/run.py && python -m tools.lints --all && pytest tests/examples/test_artifact_schema_headers.py -q | examples/s1-02-freshness-and-debt/spine.py | ⬜ pending |
| 16-08 T2 | 16-08 | 4 | DOCS-12 | T-16-08-02 | no claim that a routing state invokes a model | unit | pytest tests/examples/test_s1_02_output.py -q | tests/examples/test_s1_02_output.py | ⬜ pending |
| 16-09 T1 | 16-09 | 4 | EXAM-04 | T-16-09-02 | tool allowlist omits at registration time; artifact-header gate arms on the new directory with no source edit; spine contributes one gate call site, projecting body and resolved binder site (floor headroom, W-4) | integration | python -m tools.lints --all && pytest tests/examples/test_artifact_schema_headers.py -q | examples/s2-01-external-consumers/serve.py | ⬜ pending |
| 16-09 T2 | 16-09 | 4 | EXAM-05 | T-16-09-03 | determinism transport-level; no leg branch | integration | python examples/s2-01-external-consumers/run.py | examples/s2-01-external-consumers/fixtures/ | ⬜ pending |
| 16-20 T1 | 16-20 | 5 | DOCS-13 | T-16-20-01, T-16-20-02 | AST guard refuses five import spellings; exactly three harnesses by imported package | unit | pytest tests/examples/test_s2_01_output.py -q && test ! -f tests/examples/test_s2_client_transport_spike.py | tests/examples/test_s2_01_output.py | ⬜ pending |
| 16-20 T2 | 16-20 | 5 | EXAM-01 | T-16-20-04 | no credential value and no whitepaper body text in the README | gate | pytest tools/docs_tests -q && pytest tests/examples/test_s2_01_output.py -q | examples/s2-01-external-consumers/README.md | ⬜ pending |
| 16-10 T1 | 16-10 | 4 | DOCS-14 | T-16-10-03 | host app holds no graph write handle; artifact-header gate arms on the new directory with no source edit; spine contributes one gate call site, projecting body and resolved binder site (floor headroom, W-4) | integration | python examples/s3-01-embed-in-your-application/run.py && python -m tools.lints --all && pytest tests/examples/test_artifact_schema_headers.py -q | examples/s3-01-embed-in-your-application/host_app.py | ⬜ pending |
| 16-10 T2 | 16-10 | 4 | DOCS-14 | T-16-10-01, T-16-10-06 | admission verified before L3, no fast path; **the child satisfies the standalone contract `perf/suites/crossproc/conftest.py` spawns against** — bare argv, ephemeral 127.0.0.1 ports, a first-line `READY {mcp_port} {a2a_port}`, SIGTERM-clean teardown, and the five named artifacts — so plan 16-17's wave-10 repoint is a path change and `tests/perf_smoke/test_smoke.py[crossproc]` stays green | integration | python examples/s3-01-embed-in-your-application/run.py && python examples/s3-01-embed-in-your-application/producer_child.py (bare; first stdout line matches `^READY [0-9]+ [0-9]+$`) | examples/s3-01-embed-in-your-application/producer_child.py, examples/s3-01-embed-in-your-application/artifacts/ | ⬜ pending |
| 16-10 T3 | 16-10 | 4 | DOCS-14 | T-16-10-02 | tampered envelope refused with a typed reason | unit | pytest tests/examples/test_s3_01_output.py -q | tests/examples/test_s3_01_output.py | ⬜ pending |
| 16-11 T1 | 16-11 | 4 | DEMO-02 | T-16-11-01 | impermissible grant refused in the run; artifact-header gate arms on the new directory with no source edit; spine contributes one gate call site, projecting body and resolved binder site (floor headroom, W-4) | integration | python -m tools.lints --all && pytest tests/examples/test_spine_separation.py tests/examples/test_artifact_schema_headers.py -q | examples/s3-02-agentic-skills/artifacts/ | ⬜ pending |
| 16-11 T2 | 16-11 | 4 | EXAM-02 | T-16-11-02 | no unrecorded human action; pinned replay | integration | python examples/s3-02-agentic-skills/run.py && pytest tools/docs_tests/test_gate_two_wording.py -q | examples/s3-02-agentic-skills/run.py | ⬜ pending |
| 16-11 T3 | 16-11 | 4 | DOCS-14 | T-16-11-03 | historical skill-set asserted, not current | unit | pytest tests/examples/test_s3_02_output.py tests/examples/test_gate_two_divergence.py -q | tests/examples/test_gate_two_divergence.py | ⬜ pending |
| 16-12 T1 | 16-12 | 5 | EXAM-03 | T-16-12-05, T-16-12-06 | `make ci` composes the gate-checker suites; **W-4 resolved by statement, not by dependency** — `make examples` here executes the wave-4 `examples/s2-01-external-consumers/run.py`, which 16-20 rewrites in this same wave, so an `example-s2-01` guard-wiring failure is attributed to 16-20 and re-run rather than repaired here (adding the dep would cascade every downstream wave by one, the exact cost 16-20's split exists to avoid) | gate | make ci && git diff --stat -- examples/ (must be empty) | Makefile | ⬜ pending |
| 16-12 T2 | 16-12 | 5 | DOCS-10 | T-16-12-01 | no credential in tree; dispatch-only DGX job | gate | pytest tests/examples/test_no_credential_in_tree.py -q && make ci | tests/examples/test_no_credential_in_tree.py | ⬜ pending |
| 16-12 T3 | 16-12 | 5 | DOCS-10 | T-16-12-03 | fail-fast precondition confirmed to fire | manual | checkpoint:human-verify | — | ⬜ pending |
| 16-13 T1 | 16-13 | 6 | DOCS-12 | T-16-13-01 | no whitepaper body text in new prose | gate | make docs-strict && pytest tools/docs_tests -q | public/tutorial/hello-ccf.md | ⬜ pending |
| 16-13 T2 | 16-13 | 6 | DOCS-12 | T-16-13-02 | passage-anchor caveat carried | gate | make docs-strict && pytest tools/docs_tests/test_diagram_coverage.py -q | public/concepts/context-graph-axes.md | ⬜ pending |
| 16-13 T3 | 16-13 | 6 | DEMO-03 | T-16-13-04 | re-point while the old example still exists | gate | make docs-strict && pytest tools/docs_tests -q && python -m tools.lints --all | public/reference/artifacts/product-registration.md | ⬜ pending |
| 16-14 T1 | 16-14 | 7 | DOCS-15 | T-16-14-01 | no overclaim on passage anchors | gate | make docs-strict && tools/publish_scan.py --pre-build | public/concepts/why-ccf.md | ⬜ pending |
| 16-14 T2 | 16-14 | 7 | DOCS-15 | T-16-14-05 | gate proven to fire on a stripped element | gate | pytest tools/docs_tests -q && make docs-strict | tools/docs_tests/test_adoption_argument.py | ⬜ pending |
| 16-14 T3 | 16-14 | 7 | DOCS-15 | T-16-14-04 | argument assessed cold by a human | manual | checkpoint:human-verify | — | ⬜ pending |
| 16-15 T1 | 16-15 | 8 | DOCS-13 | T-16-15-03 | no token value in a published snippet | gate | make docs-strict | public/tutorial/external-agents-over-mcp.md | ⬜ pending |
| 16-15 T2 | 16-15 | 8 | DOCS-17 | T-16-15-01, T-16-15-05 | no-references check before deletion; repo-wide sweep re-run and its 16-15 rows closed (incl. `tests/conformance/` and `tests/lints/`); the example deleted whole so the coverage bijection disarms without an edit; the `n=1` inline tree-witness assertion retired deliberately under D-IMPL-94's D-14 limb 2, measurement preserved, no `MINIMUM_*` constant touched; **the two `live-legs.yml` jobs whose only targets this plan deletes are removed in the same commit** (W-2) so the sweep still confirms rather than discovers, with `fluree-drift` and 16-12's DGX job asserted untouched | gate | python tools/retirement_sweep.py --report && make ci && pytest tools/docs_tests tests/examples/test_artifact_schema_headers.py tests/products/test_gate_two_call_shape.py -q && test ! -d examples/03-harness-portability && git grep -c "03-harness-portability" -- public/ Makefile .github/ | public/how-to/bind-a-harness-adapter.md, tests/products/test_gate_two_call_shape.py, .github/workflows/live-legs.yml | ⬜ pending |
| 16-16 T1 | 16-16 | 9 | DOCS-14 | T-16-16-03 | agents stated as governed identity | gate | make docs-strict && pytest tools/docs_tests -q | public/tutorial/build-an-agentic-skill.md | ⬜ pending |
| 16-16 T2 | 16-16 | 9 | DOCS-17 | T-16-16-05 | mkdocstrings identifiers still resolve | gate | make docs-strict && pytest tools/docs_tests -q | public/reference/artifacts/agent-definitions.md | ⬜ pending |
| 16-16 T3 | 16-16 | 9 | DOCS-17 | T-16-16-01 | all 20 markers mapped before editing | gate | make docs-strict && pytest tools/docs_tests -q && make ci | public/how-to/compose-a-workflow-with-hitl.md | ⬜ pending |
| 16-17 T1 | 16-17 | 10 | DOCS-14 | T-16-17-05 | no store endpoint in a published snippet | gate | make docs-strict && pytest tools/docs_tests -q | public/how-to/embed-ccf-in-your-application.md | ⬜ pending |
| 16-17 T2 | 16-17 | 10 | DOCS-17 | T-16-17-04 | independent statement carried before deletion; repo-wide sweep re-run and its 16-17 rows closed, incl. the `perf/` couplings (`suites/crossproc/conftest.py:52`, `suites/common.py:140`, `synth/artifacts/controlplane.yaml:3`) repointed at `s3-01`; both examples deleted whole so the coverage bijection disarms without an edit; **the indirect-execution coupling closed by execution, not collection** (B-1) — `tests/perf_smoke/test_smoke.py` → `perf/suites/crossproc/conftest.py` → `examples/04-cross-process` is in `make ci`, and `pytest perf --collect-only -q` never instantiates the session fixture that spawns the child | gate | python tools/retirement_sweep.py --report && make ci && pytest tools/docs_tests tests/examples/test_artifact_schema_headers.py -q && pytest tests/perf_smoke/test_smoke.py -q && test ! -d examples/04-cross-process | public/how-to/run-agents-cross-process.md, perf/suites/crossproc/conftest.py, tests/perf_smoke/test_smoke.py | ⬜ pending |
| 16-18 T1 | 16-18 | 11 | DOCS-17 | T-16-18-01, T-16-18-06 | scripted zero-reference proof before deletion; publish-scan clean-page tuple repointed in the same commit | gate | make docs-strict && pytest tools/docs_tests tools/publish_scan_tests -q | mkdocs.yml, tools/publish_scan_tests/test_publish_scan.py | ⬜ pending |
| 16-18 T2 | 16-18 | 11 | DOCS-17 | T-16-18-03, T-16-18-04, T-16-18-06 | survivor modules kept and edited-survivors repointed; PERMANENTLY_DEFERRED emptied with its docstring corrected; CLI schema-export fixture repointed at s1-01; live-legs confirmed clean (16-15 removed its two example-03 jobs at wave 8; no workflow invokes `example-ext-00-live-*`); out-of-swept-tree rows closed in `tests/lints/test_examples_scope.py`, `tools/measure_examples.py` and `README.md`; **the two non-gate stale references repointed** (W-1) — `examples/external/README.md`'s band map, which survives the deletion of the only example it names so `examples/external/` is **not** empty, and `pyproject.toml`'s `test_ext00_fixture_schemas.py` / `examples/external` / `EXAM-04` comments with the now-unconsumed `anthropic` extra | gate | make ci && pytest tests/cli/test_schema_export.py tests/examples/test_artifact_schema_headers.py -q && pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q && git grep -c -e 00-quickstart -e external/00-hello-context -- examples/ pyproject.toml | Makefile, tests/examples/test_artifact_schema_headers.py, tests/cli/test_schema_export.py, .github/workflows/live-legs.yml, examples/external/README.md, pyproject.toml | ⬜ pending |
| 16-18 T3 | 16-18 | 11 | DOCS-17 | T-16-18-05, T-16-18-06 | no gate weakened to reach green; four non-vacuity floors re-counted from the post-retirement tree, removal recorded in git per `test_gate_two_call_shape.py`'s FLOOR_REMOVAL_INSTRUCTION applied to both modules (the guard module has none of its own); the closing repo-wide grep scope widened to `examples/` and `pyproject.toml` so it reaches the two non-gate stale references (W-1) | gate | make ci && pytest tests/products/test_gate_two_call_shape.py tests/products/test_required_operators_guard.py -q && python tools/retirement_sweep.py --report && pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q && pytest tests -q -rs | tests/products/test_gate_two_call_shape.py, tests/products/test_required_operators_guard.py, 16-VALIDATION.md | ⬜ pending |
| 16-19 T1 | 16-19 | 12 | DOCS-18 | T-16-19-02 | one enumerated src/ exception, no report-only | gate | make gate-16 | tools/gates/gate_16.py | ⬜ pending |
| 16-19 T2 | 16-19 | 12 | DOCS-18 | T-16-19-01 | criteria marked from scripted output | gate | make ci && make gate-16 && pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q | docs/PHASE_16_GATE.md | ⬜ pending |
| 16-19 T3 | 16-19 | 12 | DOCS-18 | T-16-19-03 | every review finding verified; rejections recorded | manual | checkpoint:human-verify | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Criterion Verification Map (V-1..V-10)

Every ROADMAP success criterion resolves to a mechanical check. Plans must
anchor their `must_haves` to these V-numbers.

| # | Criterion | Verification |
|---|-----------|--------------|
| **V-1** | Sections 1–3 published, each runs by one documented command; Section 4 absent, named as Phase 17's | `make docs-strict` exit 0 **and** `make examples` exit 0 **and** new `tools/docs_tests/test_documented_commands_exist.py` parsing `Makefile` `.PHONY` + the `examples:` prerequisite list against a regex over `public/**/*.md`. Section 4 absence: `grep -c "llm_packaged\|swarm_assembled" public/` hits only in prose naming Phase 17. |
| **V-2** | Section 1 invokes no agent | New `tests/examples/test_section_one_is_agent_free.py` — AST assertion over Section-1 modules: no import of `ccf.agents`, `ccf.skills`, `ccf.workflow`, `ccf.hitl`, `ccf_runtime.adapters`. **Negative control required** (inject an agent import into a copy; assert the guard refuses) per the `test_ext00_serve_output.py` pattern. |
| **V-3** | Every Section 2 client leg imports nothing from `ccf`, across all three harnesses | Upgrade `_assert_zero_ccf_imports` to an **AST** matcher (catches `importlib.import_module("ccf")`, indented imports, `__import__`) over `client_*.py`. Keep the parametrized negative control. Add an assertion that **exactly three** named harness legs exist, so a dropped leg fails rather than passes silently. |
| **V-4** | One parameterized runner, its backend supplied as **configuration** (Dave's ruling: *"sending in a configuration that tells the example driver which backend to use as opposed to creating six examples"*); matrix asserts equivalent Context Products across six backends; `sqlite`+`memory` always-on and network-free; four DGX opt-in; no credential in tree | (a) `pytest tests/examples/test_backend_matrix.py -q` asserting `content_hash(product_sqlite) == content_hash(product_<b>)` for every backend, parametrized from `artifacts/backends.yaml` rather than a literal tuple. (b) **One-driver proof, three parts:** exactly one driver module exists; **no** Python module under the example carries a substrate-name literal or a backend-keyed `if`/`match` (AST-asserted); and `connection.py`'s per-backend knowledge derives wholly from `artifacts/backends.yaml` — delete the artifact and it refuses rather than falling back. (c) Network-free proof: example 03's socket-guard pattern (`T-08-25`) fails the run on any non-loopback socket during always-on legs. (d) Credential proof: `git grep -c "192.168.4.76" -- examples/ public/ src/ runtime/` is 0 except in an env-defaulted, value-free artifact. |
| **V-5** | `examples/00`–`08` retired; every page sourcing from them re-cut; no partial state | `make docs-strict` exit 0 is the mechanical proof for includes (`check_paths: true` makes a dangling include a build error). For the **silent half** — prose-only path refs — new `tools/docs_tests/test_no_stale_example_paths.py` extracting every `examples/…` / `tests/examples/…` token from `public/**/*.md` and asserting each resolves on disk. Also `test -d examples/00-quickstart` must fail. *Also discharges SURFACE-AUDIT A-5's mis-pointed-include gap for path targets.* |
| **V-6** | Each example separates the CCF call spine from deployment code into distinct markered regions, legible in the repo | New `tests/examples/test_spine_separation.py`: spine module exists; carries the canonical ordered marker set; every marker opened is closed; no marker region spans both modules. **Human check remains the real gate** — carry a `checkpoint:human-verify`. |
| **V-7** | Adoption-argument page names the alternatives and their lacks; worked demonstration is the UBO question | New `tools/docs_tests/test_adoption_argument.py`: page in nav and containing (case-insensitive) a contrast phrase, the three named alternatives, the four named lacks, and the literal UBO question. This is the **exact inverse of G-01's measurement** (zero hits site-wide), so before/after is mechanical, not editorial. |
| **V-8** | Gate 2 documented as assembly-path integrity, nowhere as two independently authored sets | New `tools/docs_tests/test_gate_two_wording.py`, paragraph-scoped over `public/**/*.md`: (i) every paragraph mentioning `INV-CH7-47` or "lineage strict equality" also contains "assembly-path integrity" or an explicit negation; (ii) **zero** paragraphs affirmatively assert independence — an "independent"/"independently" match adjacent to Gate 2 must carry a negation. |
| **V-9** | A-1, A-2, A-3, A-8 discharged in the published tree | **A-1:** `grep -rn "from ccf.deployment import" public/ examples/` non-empty **and** `grep -rn "from ccf\.deployment\.[a-z_]* import" examples/ public/` empty; convention page in nav. **A-2:** maintainer page in nav naming `tools/dump_surface.py`, `make surface`, `tools/assemble_surface_changes.py`, baseline immutability; `tools/publish_scan.py --pre-build` exit 0 on it. **A-3:** `grep -c` over `public/` for `load_and_boot`, `backend`, `ccf backends`, `GraphQuery`, `registry` all > 0; no page describes a `boot()` signature mismatching `inspect.signature(ccf.boot.boot)`. **A-8:** reference page contains both halves — `BootedFabric.artifacts` reachability **and** absence from `pins`/replay dimension 2 — via `tools/docs_tests/test_advisory_discharge.py`. |
| **V-10** | No fabric changed; D-02 is a ruling with no diff | `git diff --stat <phase-base>..HEAD -- src/ runtime/` shows **zero** lines changed, or only a ruled, enumerated exception list *(see Wave 0 blocker below)*. Plus `test ! -d src/ccf/unstructured`; `grep -rn "llm_packaged" src/ \| wc -l` unchanged from base; `docs/DECISIONS.md` carries the new `D-IMPL-94` entry (highest at HEAD is `D-IMPL-93`). CI-runnable as `make gate-16`, in the spirit of the retired `make gate-15.3`, asserting the permitted-change allowlist excludes `src/` and `runtime/`. |

---

## Wave 0 Requirements

**Blocking — nothing can honestly claim green until these are done:**

- [ ] **Fix the 3 pre-existing gate-checker failures:**
  - [ ] `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` — `ProductClassDeclaration`'s docstring in `src/ccf/controlplane/artifacts.py` trips the whitepaper shingle scan with **20 hits**. ⚠ **Requires a `src/` docstring edit, colliding with criterion 10 / V-10.** Needs an explicit recorded exception — RESEARCH Q-1, Dave-facing.
  - [ ] `tools/docs_tests/test_snippet_gate.py::test_the_unmodified_source_builds_clean` — expects an `[start:ontology]` marker in `examples/00-quickstart/run.py` that no longer exists; repoint `SNIPPET_SOURCE`/`SECTION`.
  - [ ] `tools/docs_tests/test_snippet_gate.py::test_a_deleted_section_marker_fails_the_strict_build` — same repoint.
- [ ] Decide `make ci` composition — whether it gains the three gate-checker suites so *"the full local reproduction of the always-on pipeline"* becomes true (RESEARCH Q-8; `deferred-items.md` names it as two separable Phase-16 items). **Ruled yes** in `D-IMPL-94`; plan 16-12 owns the `Makefile`.

**Gates outside the swept trees that couple to retiring paths** (measured at the
plan review; `tools/retirement_sweep.py` re-measures them re-runnably):

| Gate | Coupling | Owner |
|------|----------|-------|
| `tests/examples/test_artifact_schema_headers.py` | `EXPECTED_ARTIFACT_DIRECTORIES` is a literal 10-tuple asserted for **exact equality**; `PERMANENTLY_DEFERRED` names `examples/08-e2e-demo/artifacts/scenario.yaml`; `len(documents) >= 100` over 216 documents | **16-02 owns the reshape** (tuple → two-sided bijection + per-directory non-vacuity, so four parallel wave-4 plans do not collide on one constant); **16-18** empties `PERMANENTLY_DEFERRED`. No other plan edits it. |
| `tests/products/test_gate_two_call_shape.py` | `MINIMUM_GATE_CALL_SITES=9`, `MINIMUM_PROJECTING_BODIES=11`, `MINIMUM_RESOLVED_BINDER_SITES=11` — **no headroom, on purpose**, all fed by retiring examples. Waves 8 and 10 remove three sites of each before 16-18 re-floors at wave 11, so the floors hold only if the new examples replace them — see the W-4 criterion on 16-05/09/10/11 T1. | 16-18 (authorised by `D-IMPL-94`'s D-14 bound, limb 1) |
| `tests/products/test_gate_two_call_shape.py` (second, distinct row) | `test_the_plan_recognition_refuses_an_unrelated_required_keyword` (line 3139) asserts `assert unrelated` over `BINDER_SCANNED_TREES=("examples",)` (line 369). **Verified `n = 1`:** the sole witness is `examples/03-harness-portability/run.py:693`, the only `required=True` under `examples/`. No constant, no named scan function — the scan is inline in the test body, so neither the `MINIMUM_*` re-flooring nor a path-token grep reaches it. | **16-15**, wave 8 — three waves before the `MINIMUM_*` owner. Retired deliberately under `D-IMPL-94`'s D-14 bound, **limb 2**, with the measurement preserved in the module. |
| `tests/products/test_required_operators_guard.py` | `MINIMUM_IMPLEMENTATIONS=9`; 9 of 11 found sites are in retiring examples | 16-18 (same authority) |
| `tests/cli/test_schema_export.py` | `_QUICKSTART_ARTIFACTS` points at `examples/00-quickstart/artifacts` and is globbed with a non-empty assertion | 16-18 |
| `tools/publish_scan_tests/test_publish_scan.py` | `test_the_two_moved_public_docs_are_shingle_clean` reads `public/tutorial/demo-walkthrough.md` off disk | 16-18 |
| `tests/perf_smoke/test_smoke.py` (**fourth shape — indirect execution**) | `testpaths = ["tests"]` puts it in `make test` → `make ci`; `test_suite_runs_untimed[crossproc]` runs `perf/suites/crossproc` in a subprocess, whose `conftest.py:52-54` builds `parents[3] / "examples" / "04-cross-process"` and spawns `producer_child.py`. **No path token at any hop**, no `MINIMUM_*`, no module-level scan function, and shape 3 is scoped to `tests/products/**` — invisible to all three earlier shapes. Measured with example 04 deleted: `FileNotFoundError` on `artifacts/producer-manifest.yaml`, then `AssertionError: perf suite 'crossproc' failed`. | **16-17**, wave 10. Closed by **executing** `pytest tests/perf_smoke/test_smoke.py -q`; `pytest perf --collect-only -q` is refused as evidence (collection never instantiates a session fixture). Plan 16-10 T2 ships the child that satisfies the fixture's contract. |

**References outside the swept trees that are *not* gates** (nothing goes red;
they are stale text, and every grep in their owning plan was widened to reach
them):

| Reference | Coupling | Owner |
|-----------|----------|-------|
| `examples/external/README.md` (103 lines) | Survives the deletion of `examples/external/00-hello-context`; its band map at line 50 names that example, so `examples/external/` is **not** empty afterwards. | 16-18 (W-1) |
| `pyproject.toml` lines ~83 / ~91 / ~129 | The `adk` pin comment cites the deleted `tests/examples/test_ext00_fixture_schemas.py`; the `anthropic` extra and its `dev` entry are justified by `examples/external` / `EXAM-04`, and after wave 11 the extra has no consumer (the new suite's four legs are bare MCP, ADK, LangGraph and `claude-agent-sdk`). | 16-18 (W-1) |
| `.github/workflows/live-legs.yml` | `examples-live-ollama` and `examples-live-anthropic` invoke `make example-03-live-*`, whose recipes run `examples/03-harness-portability/run.py`; the header comment at line 6 cites that example's README. Dispatch-only, so nothing goes red — which is why it would otherwise survive to wave 11. `example-ext-00-live-*` is invoked by **no** workflow. | **16-15** at wave 8 (W-2), in the same commit as the Makefile targets — not deferred to 16-18, whose step (e) is now confirmation only. |

**New test modules to stand up as failing-for-the-right-reason stubs:**

- [ ] `tests/examples/test_backend_matrix.py` (V-4)
- [ ] `tests/examples/test_section_one_is_agent_free.py` (V-2)
- [ ] `tests/examples/test_spine_separation.py` (V-6)
- [ ] `tools/docs_tests/test_no_stale_example_paths.py` (V-5 / A-5)
- [ ] `tools/docs_tests/test_gate_two_wording.py` (V-8)
- [ ] `tools/docs_tests/test_adoption_argument.py` (V-7)
- [ ] `tools/docs_tests/test_advisory_discharge.py` (V-9)
- [ ] `tools/docs_tests/test_documented_commands_exist.py` (V-1)
- [ ] `tools/docs_tests/test_retirement_sweep.py` + `tools/retirement_sweep.py` — the repo-wide coupling sweep and its gate (**plan 16-21**, wave 2; split out of 16-04 T4 at round-2 review). Added at the plan review: the § A.1/§ A.2 retirement inventory swept `examples/`, `tests/examples/` and `public/` only, and always-on gates outside those trees hard-point at retiring paths. Round 2 found a fifth instance in a **third coupling shape** — an inline tree-witness assertion with no constant and no named scan function. Round 3 found a sixth in a **fourth shape** — an *indirect execution*, `tests/perf_smoke/test_smoke.py` → `perf/suites/crossproc/conftest.py` → `examples/04-cross-process`, which carries no path token at any of its three hops and was found only by deleting the examples in a scratch clone and running the always-on path. The sweep must enumerate all **four** shapes.

**New non-test deliverables Wave 0 must unblock:**

- [ ] **FIBO data extension** — corp→corp `hasOwnershipInterestIn` edges carrying per-edge `ownershipPercent`. Today `ownershipPercent` is an attribute of the *Party entity*, not the ownership edge, and every edge runs Party→Corporation in exactly one hop. **The UBO question the adoption argument is built on is not answerable on the shipped data.** Requirement-bearing, must land before any KYC/UBO example or page is written.
- [ ] **LangGraph** and **Claude-Agent-SDK** client legs for Section 2 — neither exists; LangGraph has no in-tree precedent at all.
- [ ] DGX opt-in job in `.github/workflows/live-legs.yml` with secret-gated fail-fast preconditions.

**Framework install:** none needed — `pytest` and the whole toolchain are present in `.venv`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spine/deployment separation is **legible to a human reading the repository** | V-6 / criterion 6 | The structural test proves markers are present, ordered and closed; it cannot prove a reader can *see* which code is CCF and which is theirs. Dave's wording makes the human read the real gate. | Open each new example's spine and deployment modules side by side without the rendered site. Confirm a reader who has never seen CCF can name which calls are the fabric's. |
| DGX opt-in live leg is green | V-4 | `NEO4J_PASSWORD` / `PGPASSWORD` for `192.168.4.76` are **not present in this environment**. The leg cannot be proven from this machine. | Configure GitHub Actions secrets, dispatch `live-legs.yml` once, confirm green. Dave-facing prerequisite, not a code task. |
| The adoption argument is *persuasive*, not merely present | V-7 | `test_adoption_argument.py` asserts the alternatives and lacks are named; it cannot assess whether the argument lands. | Read the page cold against the UBO question. Confirm each of the four lacks cites shipped mechanism rather than asserting. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (8 new test modules + 3 pre-existing failures + FIBO extension + 2 harness legs)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] Every plan's `must_haves` anchors to a V-number
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
