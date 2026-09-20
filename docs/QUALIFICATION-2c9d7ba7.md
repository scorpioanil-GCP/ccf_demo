# Release qualification — immutable candidate `2c9d7ba7`

**Tested candidate:** `2c9d7ba7b4f9f16d27b2f49eeade7360e17ad36e` (`main` after the qualification
repair package merged; tree `95fb638fb0e0b85e51c65ba8bf3f81a2b0b87d7d`). **Report commit:** the
commit carrying this file, made after measurement; nothing here was measured on it.
**Measurement only:** no fix, test edit, expected-failure mark, retune, configuration or product
change was made; the candidate tree is byte-identical before and after every run.
Date of measurement: 2026-09-19.

---

## 1. The answer

**Yes. The immutable candidate executed the complete applicable launch qualification without an
unexplained failure.**

- One `make test` invocation over the full `tests/` tree with the curated estate and the local
  substrates exported: **8 871 collected, 8 732 passed, 0 failed, 0 errors, 0 unexpected passes,
  137 expected failures, 2 skipped** — and the two skips are the orchestration-conformance nodes
  already recorded as named-unexecutable.
- Every CI job leg and every substrate leg executed and passed: lint job, docs job, examples job,
  schema headers, and the Fluree, MongoDB, Neo4j and Postgres legs.
- Every node reconciled by exact id: zero collected ids without an outcome, zero outcomes without
  a collected id. The 46 previously deferred nodes are green under their corrected instruments and
  the first correction group's 17 targets are green.
- The eight release-instrumentation controls are load-bearing in this run, by node id.

The only items that are not "executed — pass" are named and previously accepted: the two
orchestration nodes (named-unexecutable), the 137 expected failures of frozen example specimens,
and the informational coverage job, which the launch contract does not require. Nothing requires
a new disposition. Readiness is not inferred from the counts; §4 and §5 are the roster.

---

## 2. Candidate freeze and integrity

- `origin/main` verified equal to the candidate before checkout; fresh detached worktree at the
  exact SHA; `git status` 0 modified, 0 untracked, **0 ignored macOS sidecars** (`find` for
  `._*`: none); `ccf` resolving inside the worktree.
- Tree hash recorded before the run (`candidate.tree`) and compared after the one-shot and again
  after the legs: **identical**; working tree clean; empty diff. Logs, junit and the collection
  inventory were written outside the tree throughout.

---

## 3. The single invocation

**Command:** `make test` (Makefile: `PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1
.venv/bin/python -m pytest -q`), run once, detached from the session so no tool limit could cut it,
with junit and the `-rfEsxX` summary added through `PYTEST_ADDOPTS` only. **Posture:** the curated
estate on `192.168.4.76` (read-only) and the local Fluree, MongoDB and Neo4j test containers
exported, so the example suites and the substrate-marked tests executed inside the one process;
`CCF_REQUIRE_ESTATE=1`, so a missing estate name would have failed rather than skipped.

| measure | value |
|---|---|
| collected (same posture, `--collect-only`) | 8 871 (9 096 minus 225 `archived`, deselected by design) |
| passed | 8 732 |
| failed | **0** |
| skipped | 2 |
| xfailed | 137 |
| xpassed | **0** |
| setup / collection errors | **0** |
| runtime | 1 615.75 s (26 min 55 s) |

**Node ids not passing:**

- Skipped (named-unexecutable, §4):
  `tests/conformance/test_orchestration.py::test_a_never_executed_segment_raises_the_same_typed_error_on_every_leg[in-sdk]`,
  `tests/conformance/test_orchestration.py::test_the_introspection_seam_is_loop_safe[in-sdk]` —
  *"in-sdk reference adapter holds no outcome store"*.
- Expected failures: 137, all in `tests/examples/` (§6); the full id list is `xfailed_nodes.txt`
  in the evidence archive.

**Against the previous one-shot** (merge qualification of the first correction group, 8 849
nodes, 46 failed): 22 nodes more, all controls the repair package added (16 in the CLAUDE.md
roster module, 3 in the no-obligation guard, 2 in the CP-14 isolation module, 1 in the peering
guard); 46 fewer failures, the 46 repaired; the same two skips; the same 137 expected failures.

---

## 4. Substrate and integration legs

| leg / check | status | result |
|---|---|---|
| `make leg-fluree` (local `fluree/server` container, `CCF_REQUIRE_FLUREE=1`) | **EXECUTED — PASS** | 288 passed, 11 xfailed, 309 skipped, exit 0, 366 s |
| `make leg-mongo` (local `mongo:7`, `CCF_REQUIRE_MONGO=1`) | **EXECUTED — PASS** | 36 passed, 58 skipped, exit 0 |
| `make leg-neo4j` (local `neo4j:5`, `CCF_REQUIRE_NEO4J=1`) | **EXECUTED — PASS** | 29 passed, exit 0 |
| `make leg-postgres` (a throwaway `postgres:16` the target provisions, `CCF_REQUIRE_POSTGRES=1`) | **EXECUTED — PASS** | 232 passed, 72 xfailed, 365 skipped, exit 0 |
| curated-estate example suites (every `tests/examples` module, `192.168.4.76`, read-only) | **EXECUTED — PASS** | inside the single invocation; every estate-gated node executed (`CCF_REQUIRE_ESTATE=1`) |
| `ci-quick-suite`, `ci-harness-conformance` (CI test job) | **EXECUTED — PASS** | their node sets ran inside the single invocation in a superset posture; not re-run as separate invocations |
| lint job: `tools/lints/tests`, `tools/product_gates_tests`, `make lint`, `make product-gates`, `make typecheck` | **EXECUTED — PASS** | 480 passed; 48 passed; 0 findings; 19 trees, 326 declared, 326 executing; clean, 230 files |
| docs job: `tools/publish_scan_tests` + `tools/docs_tests`, `make docs-strict` | **EXECUTED — PASS** | 349 passed; built |
| examples job: `make examples` (hw1 harness clients: ADK, Anthropic, LangGraph) | **EXECUTED — PASS** | three legs, one content address, all MATCH |
| `make schema-headers` | **EXECUTED — PASS** | 31 artifact directories |
| surface manifest determinism (two independent processes, `tools/dump_surface.py --check`) | **EXECUTED — PASS** | byte-identical; equal to committed; 0 addresses; exit 0 |
| `tests/conformance/test_orchestration.py` — the two `[in-sdk]` nodes above | **NAMED-UNEXECUTABLE** | prerequisite: an outcome store on the in-SDK reference orchestration adapter, which it does not implement; not executable in any environment; recorded as an accepted scope limitation at the first qualification and the first correction-group close; **not required** by the supported launch contract |
| `ci-coverage` | not executed — **not required** | informational only, no numeric gate (`D-17`); no measurement value for the ruling |

The legs' skips are the estate-gated example modules (reasons *"the curated estate is not
configured: CCF_CP_…"*, *"cp-11/12/13 assembles from the live estate"*), because the legs run
without the estate as CI does; every one of those nodes executed with the estate inside the single
invocation. No unavailable infrastructure was recorded as green: every leg above that says
EXECUTED ran to completion with exit 0 and a junit file. No credential or connection string
appears in this report or the evidence (names only, values masked).

---

## 5. Node reconciliation

`collected (8 871) = passed (8 732) + failed (0) + skipped (2) + xfailed (137) + xpassed (0) +
errors (0)`, by exact node id — 0 collected ids without a junit outcome, 0 junit outcomes without a
collected id (`reconciliation.txt`).

| category | nodes |
|---|---:|
| normal passes | 8 732 |
| expected failures that leave behavior unsupported or unproven (§6) | 137 |
| legitimate skips | 0 (none other than the two below) |
| environment-gated checks | 0 in the one-shot (the estate and substrates were present); in the legs, the estate-gated example nodes skipped there and executed in the one-shot |
| named-unexecutable | 2 (the orchestration nodes) |
| unexpected failures | **0** |
| unexpected passes | **0** |
| setup / collection errors | **0** |

**The repaired 46:** 46 of 46 green — 44 by the same id; the CLAUDE.md byte-pin node
(`tests/invariants/test_determination_authority_disclosure_delivery.py` `::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]`)
replaced by `tests/invariants/test_determination_authority_disclosure_delivery.py::test_the_invariant_roster_is_the_seven_it_has_always_been[section-3.1-phase-D-review]`
and `[section-16-named-invariants]`, both green; the peering hash-pin node
(`tests/peering/test_admission_record.py` `::test_claims_py_is_unchanged_so_reading_a_cannot_creep_back_in`)
replaced by `tests/peering/test_admission_record.py::test_lineage_entry_holds_reading_d_so_reading_a_cannot_creep_back_in`,
green. The CP-14 process-order node
`tests/examples/test_cp_14_fourth_slice.py::test_the_consumer_imports_no_producer_and_rebuilds_no_child_material`
passed inside the single invocation, in collection order after the cp-05 suites — the exact
scenario that failed before the repair.

**The first correction group's 17:** the 14 tests-tree targets green by id in this run; the 3
lint-runner targets green inside `tools/lints/tests` (480 passed).

---

## 6. Expected failures, and the capability each leaves unsupported

All 137 are `xfail(strict)` quarantines of frozen example specimens under `D-IMPL-261`/`D-IMPL-263`
(a frozen example is evidence of the SDK's evolution, never repaired to look like the current
SDK); none is counted as proof of the capability it names, and none can pass unexpectedly (0 xpass).

| module(s) | nodes | what stays unsupported by these specimens |
|---|---:|---|
| `test_cp_00_output.py`, `test_cp_00_recipe_steps.py`, `test_cp_01_output.py`, `test_cp_02_output.py`, `test_cp_03_output.py`, the six `test_cp_04_*` modules | 118 | the frozen cp-00 – cp-04 specimens do not construct a Context Product contract on the current SDK (request-contract and replay-completeness rulings of 24.7/24.8); the *capabilities* they once demonstrated are proven today by their canonical successors (cp-03-canonical, cp-04-canonical) and the s1/hw1 suites, which passed |
| `test_cp_06_output.py`, `test_cp_06_mcp_door.py` | 19 | the frozen cp-06 specimen declares an evidence anchor over a resolver with no half-life table and is refused at the builder under the `D-IMPL-341` registration ruling; the capability (evidence-anchored expiry) is proven by cp-06-canonical, which passed |

The legs' 11 (Fluree) and 72 (Postgres) expected failures are these same nodes under their
substrate markers.

---

## 7. Accepted launch limitations carried into the ruling

Recorded before this run, unchanged by it: the six `D-GATE-341` residuals; the lower producer
route's unrecorded pre-acquisition refusal (`D-IMPL-304`); the covenant dual-TTL (`CIF-G15`) out
of scope; the two orchestration nodes named-unexecutable; the CP-14 governed gates `G04`, `G07`,
`G25` partial and `G24` uncovered, open with the memo specification; the repair follow-up's
disclosed tooling residuals (conservative registry refusals in the guarded-provenance reader, the
pathological custom-repr case in the surface renderer, the `mint`-resolution docstring backlog);
and the frozen specimens above.

---

## 8. Release instrumentation, load-bearing in this run

| control | evidence in this run |
|---|---|
| no-obligation vocabulary guard | `test_removing_a_ruled_roster_entry_turns_its_vocabulary_red[DecayBasis]`, `[FreshnessAggregation]`, `test_an_unruled_vocabulary_of_the_same_shape_stays_red`, `test_the_shipped_tree_declares_no_obligation_vocabulary` — green |
| CLAUDE.md two-list invariant guard | `test_the_invariant_roster_is_the_seven_it_has_always_been[…]` ×2, the plant/remove/duplicate/substitute controls, `test_unrelated_prose_elsewhere_in_the_document_leaves_the_roster_green` — green |
| citation ratchet | `test_the_unanchored_python_citation_population_cannot_regrow` — green (population 0) |
| `LineageEntry` semantic guard | `test_lineage_entry_holds_reading_d_so_reading_a_cannot_creep_back_in`, `test_a_lineage_entry_widened_with_a_federated_axis_turns_the_guard_red` — green |
| CP-14 action-scoped import isolation | the gate node after the cp-05 suites in one process, `test_the_import_audit_catches_a_producer_import_the_action_makes_and_ignores_a_cached_one`, `test_the_audit_restores_the_import_hook_and_reports_only_producer_origins` — green |
| surface manifest determinism | `test_the_serialized_manifest_carries_no_memory_addresses`, `test_the_manifest_is_byte_stable_across_two_builds`, the literal-default and function-default controls — green; two separate-process generations byte-identical and equal to the committed file |
| guarded-provenance lint | `tools/lints/tests` 480 passed, including the parse-only registry controls; `make lint` 0 findings on the real tree |
| HTTP refusal-vocabulary closure | `test_the_table_is_closed_over_the_refusal_vocabulary`, `test_the_closure_assertion_catches_a_planted_drift[extra]`, `[removed]` — green |

None of these controls was modified during qualification.

---

## 9. Evidence and integrity proof

- `qualification/2c9d7ba7/evidence.tar.gz` (in the report commit): the one-shot log,
  `collected.txt` (8 871 ids), `reconciliation.txt` (categories, the 46, the 17, the
  instrumentation, by node id), `xfailed_nodes.txt` (137 ids), the four leg logs, the lint, docs,
  examples, product-gate, schema-header, typecheck, docs-strict and surface-check logs,
  `candidate.sha`, `candidate.tree`, `manifest.sha`. Connection strings masked; no environment
  script included.
- The junit files (the one-shot, the four legs, the three tooling suites) are archived outside the
  repository at `~/ccf_qual_evidence/2c9d7ba7/` on the measuring host, same content as the logs.
- Integrity: `candidate.sha` = `2c9d7ba7b4f9f16d27b2f49eeade7360e17ad36e`; `candidate.tree` =
  `95fb638fb0e0b85e51c65ba8bf3f81a2b0b87d7d` recorded before the run and re-read equal after the
  one-shot and after the legs; `git status` 0 changes and `git diff` empty at both checks; the
  worktree removed after this report was written.

---

## 10. Inputs for the release ruling

Stated as inputs, not as a recommendation:

1. The candidate is `main` and is byte-identical to what was measured.
2. Zero unexplained failures, errors or unexpected passes across 8 871 nodes in one process, and
   zero across the four substrate legs and the four CI job legs.
3. The items outside "executed — pass" are all previously accepted and unchanged: two
   named-unexecutable orchestration nodes, 137 frozen-specimen expected failures whose
   capabilities are proven by successors, and an informational coverage job.
4. The eight instrumentation controls that turned the last 62 reds into evidence are load-bearing
   in this run and unmodified.
5. The accepted limitations in §7 are the release's stated limitations; none was reopened, and no
   evidence in this run contradicts any of them.
6. Nothing was authorized or done beyond measurement: no tag, no D-IMPL-345, no paved seam, no
   dual-TTL, no CP-14 assembly, no retune, no cleanup.
