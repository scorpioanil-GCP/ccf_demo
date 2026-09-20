# Release qualification — candidate `f0656746`

**Qualification candidate (the commit every measurement below ran on):**
`f0656746ec7cfeb734dfff717f388ce8c3623b6f` — `origin/main` at the start of the run, verified
equal to local `main`, checked out DETACHED in an isolated worktree outside the repository
(`/home/parkave/ccf_qual_f0656746`), with the interpreter attached by symlink and imports proven
to resolve inside the worktree (`ccf` → `…/ccf_qual_f0656746/src/ccf/__init__.py`).

**Behavioral baseline:** `dc7e8177` (`main` at `D-GATE-341`). The candidate is that baseline
plus two documentation-only commits (`f9da0ae6` the launch bar, `f0656746` the launch-scope
package including the adopter-facing replay example).

**Report commit:** the commit carrying this file, created after measurement. Nothing in this
document was measured on it.

**Measurement only.** No source, test, configuration, calibration, skip or expected-failure
change was made during the run. Every log was written outside the checkout. At the end of the
run the worktree had **0 modified tracked files, 0 untracked files, and an empty diff against the
candidate SHA**.

Date of measurement: 2026-09-19.

---

## 1. Fragment-claims and class-lookup, resolved from execution

`tests/deployment/test_class_lookup.py` was run node by node before anything else.

| node | result |
|---|---|
| `tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added` | **FAILED** |
| the other 40 nodes of the module (`test_the_sdk_artifact_classes_were_actually_discovered`, the 19 parametrizations of `test_an_sdk_class_id_resolves_to_the_constant_itself`, `test_every_mapping_entry_is_the_module_constant`, `test_every_exported_artifact_class_is_manifest_addressable`, the refusal and envelope cases, and the rest) | PASSED |

**There is one failure, and "fragment-claims" and "class-lookup" are the same node.** The module
is `test_class_lookup.py`; the failing assertion is the fragment-claims one. No class-lookup
mechanism test fails. The assertion:

> `AssertionError: added but unclaimed: ['ccf.contracts.guarded.GUARDED_TYPES',
> 'ccf.contracts.guarded.GuardedTypeDeclaration', 'ccf.contracts.guarded.declaration_for',
> 'ccf.controlplane.artifacts.MC…', …]` — with `ccf.products.composite.ChildAcquisition` and
> `ccf.halflife.decay.freshness_over_of` among the extra items in the left set.

Public symbols added by recent phases are not claimed by any phase's surface fragment. Earlier
records cited this failure as "1 `test_class_lookup`" and as "the fragment-claims failure"; both
names were pointing at this node.

**Attribution:** recorded red at the merge base `f8c33898` in the `D-IMPL-341` decision entries
(the 341 close measured it as the one standing red of the deployment family). Whether the
*unclaimed set* is the same as at that base is **not yet established**; the names in the message
include symbols from `D-IMPL-333`, `D-IMPL-336`/`338` and `D-IMPL-337`.

---

## 2. What "applicable" means here

Defined from the pipeline, not from what happened to be available. `.github/workflows/ci.yml`
runs four jobs; the Makefile mirrors them target for target.

| CI job | steps | executed here |
|---|---|---|
| `lint` | `pytest tools/lints/tests`; `pytest tools/product_gates_tests`; `python -m tools.lints --all`; `make product-gates`; `mypy` | all |
| `test` | `ci-quick-suite` (`pytest tests -m "<no substrate>"`), `ci-harness-conformance` (`pytest tests/conformance`), `leg-postgres`, `leg-neo4j`, `leg-mongo`, `leg-fluree`, `ci-coverage` (informational) | all but `ci-coverage` |
| `examples` | `make examples` (the network-free `hw1-harness-clients` runner) | yes |
| `docs` | `pytest tools/publish_scan_tests tools/docs_tests`; `make docs-strict` | yes |

Beyond CI, as launch-supported configurations: the **curated estate** on `192.168.4.76`
(Fluree `fibo-v2`, Postgres `ccf_v2`, Mongo `fibo_v2`, read-only) for every `tests/examples`
module, and `make schema-headers`.

**Deviation, stated:** `make test` is one `pytest tests` invocation over `testpaths = ["tests"]`.
Under this host's ten-minute tool limit it was run as **ten chunks** by family, each its own
process with its own junit file. Collection-order interactions between families were therefore
not reproduced. The union of the chunks was reconciled against a single `--collect-only` of the
whole tree: **8 843 nodes collected (225 `archived` deselected by design), 8 843 executed** — the
last one, `tests/spikes/test_claude_driver_probe.py::test_the_claude_sdk_can_express_the_driver_seam`,
found by that reconciliation and run separately (passed).

### Execution environment (names only; no value is recorded here)

- Local services, all reachable: Fluree `fluree/server:4.1.4` on `localhost:8090`; Mongo 7 on
  `localhost:27019`; Neo4j 5 community on `localhost:7687`; Postgres 16 provisioned by the
  postgres leg itself (`CCF_TEST_POSTGRES_DSN` unset, so the target used its own throwaway
  server).
- Estate variables exported for the example chunks, derived from one set for every `CCF_CP_NN_*`
  name the suites read (`FLUREE_URL`, `FLUREE_LEDGER`, `POSTGRES_DSN`, `POSTGRES_SCHEMA`,
  `MONGO_URI`, `MONGO_DB` for `00`–`13`, the canonical `03C`/`04C`/`06C`/`13C`, `14`, and
  `CCF_CP_03_LIVE_DSN`), with `CCF_REQUIRE_ESTATE=1` so a missing name is a failure rather than a
  silent skip. `CCF_REQUIRE_HARNESSES=1` throughout, as `make test` sets it.
- Harness extras installed: `google-adk`, `claude-agent-sdk`, `langgraph`. `ANTHROPIC_API_KEY`
  present; `GOOGLE_API_KEY` absent — no test skipped or failed for it.
- The quick-suite chunks ran in CI's posture (no `CCF_TEST_*` URLs), so substrate-marked tests
  skipped there and were executed by the four legs, exactly as CI does.

### Exact commands

From the worktree root, `PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1`, each with
`-q -p no:cacheprovider -rfEsxX --tb=short --junitxml=<log>.xml`:

```
pytest tests/products tests/replay tests/contracts tests/deployment              # A
pytest tests/invariants                                                          # B
pytest tests/client tests/conformance tests/controlplane tests/graph tests/halflife   # C
pytest tests/http_api tests/properties tests/agents tests/crossproc tests/mcp tests/skills \
       tests/operators tests/hitl tests/peering tests/cli tests/authz tests/lints tests/workflow \
       tests/integration tests/projection tests/signal_layer tests/assembly tests/gates \
       tests/harness tests/test_smoke.py tests/test_surface_completeness.py \
       tests/test_surface_drift.py tests/test_surface_shape_capture.py                  # D
pytest tests/perf_gate tests/perf_smoke tests/perf_synth                          # E
pytest <tests/examples: cp-00..cp-05, door-cp-05, s1-00, s1-01>                  # F (estate)
pytest <tests/examples: cp-06..cp-13, canonical and frozen, doors>               # G (estate)
pytest <tests/examples: cp-03/cp-04 canonical + consumers, CP-14 slices 1–4>     # H (estate)
pytest <tests/examples: every remaining module>                                  # I (estate)
pytest tests/signal_layer/test_cp05_acquisition_boundary.py                      # J (estate)
pytest tests/spikes                                                              # K
make leg-fluree ; make leg-mongo CCF_TEST_MONGO_URI=mongodb://localhost:27019/ccf_test
make leg-neo4j  ; make leg-postgres
make lint ; make typecheck ; make product-gates ; make schema-headers ; make docs-strict ; make examples
pytest tools/lints/tests ; pytest tools/product_gates_tests ; pytest tools/publish_scan_tests tools/docs_tests
```

---

## 3. Result totals

### The `tests/` tree — 8 843 unique nodes, every one accounted for

| chunk | families | passed | failed | skipped | xfailed | xpassed | errors |
|---|---|---|---|---|---|---|---|
| A | products, replay, contracts, deployment | 2 028 | **1** | 1 | 0 | 0 | 0 |
| B | invariants | 1 993 | **44** | 0 | 0 | 0 | 0 |
| C | client, conformance, controlplane, graph, halflife | 1 390 | 0 | 110 | 0 | 0 | 0 |
| D | the nineteen remaining SDK/runtime families + smoke + surface | 1 842 | **13** | 3 | 0 | 0 | 0 |
| E | perf_gate, perf_smoke, perf_synth | 37 | 0 | 0 | 0 | 0 | 0 |
| F | examples: cp-00–cp-05, the exposure door, s1-00, s1-01 | 468 | 0 | 0 | 118 | 0 | 0 |
| G | examples: cp-06–cp-13 canonical and frozen, doors | 244 | 0 | 0 | 19 | 0 | 0 |
| H | examples: cp-03/cp-04 canonical, consumers, CP-14 slices 1–4 | 75 | 0 | 0 | 0 | 0 | 0 |
| I | examples: every remaining module | 455 | **1** | 0 | 0 | 0 | 0 |
| J | `tests/signal_layer/test_cp05_acquisition_boundary.py`, with the estate | 12 (its 12 nodes; 3 had skipped in D) | 0 | 0 | 0 | 0 | 0 |
| K | spikes | 1 | 0 | 0 | 0 | 0 | 0 |
| **unique by node** | | **8 536** | **59** | **111** | **137** | **0** | **0** |

The chunks reported 114 skips; 3 of them (the estate live halves in D) were executed by chunk J,
leaving **111 unique skipped nodes** in the CI quick posture, by reason:

| reason (from the junit message) | nodes | then executed by |
|---|---|---|
| `CCF_TEST_FLUREE_URL` unset | 49 | `leg-fluree` |
| `CCF_TEST_MONGO_URI` unset | 31 | `leg-mongo` |
| `CCF_TEST_NEO4J_URI` unset | 29 | `leg-neo4j` |
| *"in-sdk reference adapter holds no outcome store"* (`tests/conformance/test_orchestration.py`) | 2 | **nobody** — by design (§6) |

The 109 substrate rows are proven by node id, not by count: every one of those node ids is in
the corresponding leg's `--collect-only -m <marker>` selection on the frozen worktree, the legs
run with `CCF_REQUIRE_<SUBSTRATE>=1` (an unset service fails instead of skipping), their `-rs`
summaries show only estate-gated skips, and each leg exited 0 with no failure. So each of the 109
either passed or was an expected failure inside its leg.

### The substrate legs (CI's `make leg-*`, marker-selected over the whole tree)

| leg | passed | skipped | xfailed | failed | exit |
|---|---|---|---|---|---|
| `leg-fluree` | 286 | 309 | 11 | 0 | 0 (321 s run alone; a first attempt under a 280 s tool budget timed out and was discarded) |
| `leg-mongo` | 34 | 58 | 0 | 0 | 0 |
| `leg-neo4j` | 29 | 0 | 0 | 0 | 0 |
| `leg-postgres` | 230 | 365 | 72 | 0 | 0 |

Skips inside the legs are the estate-gated example modules that carry a substrate marker (the
legs ran without the estate, as CI does); those modules were executed with the estate in chunks
F–I. Sampled reason: *"the curated estate is not configured: CCF_CP_05_FLUREE_URL, …"*.

### Tooling, static and documentation checks

| check | result |
|---|---|
| `tools/lints/tests` | **3 failed**, 468 passed |
| `tools/product_gates_tests` | 48 passed |
| `tools/publish_scan_tests` + `tools/docs_tests` | 349 passed |
| `make lint` (`tools.lints --all`) | clean, exit 0 |
| `make typecheck` (mypy strict) | clean, 230 source files |
| `make product-gates` | 19 shipped trees, 326 declared gates, 326 executing |
| `make schema-headers` | 31 artifact directories, clean |
| `make docs-strict` (pre-build scan, schema scan, strict build, site scan) | built, exit 0 |
| `make examples` (`hw1-harness-clients` runner: adk, anthropic, langgraph) | three legs, one content address, all MATCH |
| `tools/proof/tests` | **not in the candidate** — an untracked local directory in the working repository, not in CI; a run at the worktree path collected 0 tests; not applicable |
| `ci-coverage` | **not executed** — informational, no numeric gate (`D-17`) |

**Errors: 0. Unexpected passes: 0.**

---

## 4. Every failure, by node

62 unique failing nodes in 12 modules. Attribution names the historical record where one exists
and says **not yet established** where none does; resemblance to an earlier count is not
attribution.

### 4.1 `tests/deployment/test_class_lookup.py` — 1

Covered in §1. Attribution: recorded red at `f8c33898`; set identity not yet established.

### 4.2 `tests/invariants/test_no_obligation_vocabulary.py` — 42

Every node fails on one finding: *"a closed vocabulary of strings is declared in
`src/ccf/controlplane/artifacts.py`"* — the guard names `DecayBasis` (literal and table, line
259) and `FreshnessAggregation` (line 285), the `Literal` vocabularies `D-IMPL-331`/`D-IMPL-333`
introduced. 28 are the `test_the_guard_refuses_an_injected_obligation_vocabulary` cases, 10 the
`test_the_table_shape_did_not_widen_into_a_ban_on_every_collection` cases, plus `test_the_shipped_tree_declares_no_obligation_vocabulary`,
`test_no_scanned_module_declares_an_obligation_vocabulary[src/ccf/controlplane/artifacts.py]`,
`test_the_guard_ignores_obligation_words_in_prose` and `test_the_walk_sees_the_glob_table_the_exemption_covers`
(*"the exemption stopped covering `_GLOB_CHARACTERS`"*).

**Attribution:** the handoff of 2026-09-17 records this module at **42** red "identical by node
id to `af91c7da` where measured"; the count matches and the module is the same. Node-id identity
against that record was not re-verified here.

### 4.3 `tests/invariants/test_determination_authority_disclosure_delivery.py` — 1

`test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]`: *"CLAUDE.md differs from
`1022ad59`: criterion 27 leaves it to Dave to order a revision."* A content pin on `CLAUDE.md`
at a phase base. **Attribution: not yet established** — the module is named in the decision log,
but no record states this node red at the baseline.

### 4.4 `tests/invariants/test_citation_coverage.py` — 1

`test_the_unanchored_python_citation_population_cannot_regrow`: the message opens *"NOTE BEFORE
READING THE FAILURE: the citation gate is GREEN"* — a ratchet on the population of unanchored
citations, not the citation lint. **Attribution:** cited as "the invariants citation ratchet"
among the standing reds at the `D-IMPL-341` closes.

### 4.5 `tests/http_api/…` — 8

| node | message |
|---|---|
| `test_openapi.py::test_the_committed_spec_matches_what_the_app_emits` | *"The committed openapi.json no longer matches what create_app() emits. Run `make openapi` and commit the result."* |
| `test_product_declared_obligation_409.py::test_no_known_refusal_kind_reaches_served_answer[composite-child-refusal]` and `[dependency-invalidation-refusal]` | *"a '…-refusal' reached the product door and UngovernedResolverResult escaped instead of a response"* |
| `test_product_refusal_statuses.py::test_every_kind_answers_its_row_in_the_one_body[composite-child-refusal]` and `[dependency-invalidation-refusal]` | same message |
| `test_product_refusal_statuses.py::test_the_table_is_closed_over_the_refusal_vocabulary`, `::test_the_closure_assertion_catches_a_planted_drift[extra]`, `[removed]` | the status table's key set ≠ the refusal vocabulary |

Two refusal kinds reach the HTTP door and escape as an internal result rather than a response,
and the door's status table is not closed over `REFUSAL_KINDS`. **Attribution:** the decision log
records "8 `http_api`" as standing at the `D-IMPL-341`/`342` closes; the count matches; the node
ids were not enumerated in that record, so identity by node id is **not yet established**.

### 4.6 `tests/test_surface_completeness.py` — 2, and `tests/test_surface_shape_capture.py` — 2

| node | message |
|---|---|
| `test_surface_completeness.py::test_every_diff_line_has_a_matching_public_log_entry` | *"added: ccf.contracts.guarded.GUARDED_TYPES"* |
| `test_surface_completeness.py::test_every_public_log_entry_has_a_matching_diff_line` | *"336-02-composite-remediation.md claims `added` for ccf.products.composite.ELIGIBILITY_EVIDENCE_POLICY but the manifest does not show this name at all."* |
| `test_surface_shape_capture.py::test_the_serialized_manifest_carries_no_memory_addresses` | two `0x…` addresses in the committed manifest |
| `test_surface_shape_capture.py::test_no_committed_plain_class_or_function_shape_is_disturbed` | `['ccf.products.composite.compose_children', 'ccf.products.product.open_product', 'ccf.products.resolver.build_governed_resolver']` |

**Attribution, in two parts.** The four surface modules are recorded standing at
"`tests/test_surface_*` (4)" before `D-IMPL-341`. **But the fourth node's content is new:** the
three disturbed shapes are signatures `D-IMPL-341` changed — `compose_children` gained
`decided_at` (`8c0388dc`), `build_governed_resolver` gained `evidence_clock_key` (`8f84f710`) —
and the committed surface manifest was not regenerated for them. The fragment
`docs/surface-changes/341-01-evidence-anchored-expiry.md` exists; the manifest the shape gate
reads does not carry the new shapes, and the handoff of 2026-09-17 records the practice that let
that happen (*"the surface manifest regenerates with memory addresses — discard address-only
churn"*). A confirmed defect of this branch's records, owned here.

### 4.7 `tests/peering/test_admission_record.py` — 1

`test_claims_py_is_unchanged_so_reading_a_cannot_creep_back_in`: a content-hash pin on
`claims.py` (`58f97ac2…` observed vs `70a3e8a2…` pinned). **Attribution:** recorded as "1
peering" among the standing reds at the 341 closes; identity by node id plausible (one node in
the module fails) and not re-verified.

### 4.8 `tests/examples/test_hw1_readme_expected_output.py` — 1

`test_the_readme_fence_is_the_in_process_commands_output`: the README's *Expected output* fence
and `consume.py`'s stdout differ on exactly two lines — the **content address** (`cbc7db84…` in
the fence, `a8335bb4…` served) and the **replay record** address; `D_c` (0.4271 → forced_llm) and
`answer expires` (2026-08-01 00:10:00+00:00) are unchanged. **Attribution: not recorded
anywhere; caused by `D-IMPL-341`** — every new serve now carries `ttl_anchor_at` on the contract
(R-2), which moves a decision-anchored product's content address while leaving its expiry value
alone. `hw1-companies-over-revenue` was not on the 341 validation's affected list, and its README
fence was never re-measured. A confirmed defect of this branch, owned here.

### 4.9 `tools/lints/tests/test_runner.py` — 3

`test_the_registered_rule_set_is_exactly_these_seven` (the registered set has extra members),
`test_missing_trees_are_skipped_not_errors` and `test_main_exits_zero_on_a_clean_tree` (both:
`main(['--all', '--base', <empty fixture>])` returns 1). **Attribution:** the handoff of
2026-09-17 records `tools/lints/tests/test_runner.py` at **3**; the count and module match.

---

## 5. Expected failures, and what they do not prove

137 `xfailed` in the tests tree (118 in chunk F, 19 in chunk G), plus 11 and 72 reported by the
Fluree and Postgres legs over overlapping nodes. None is counted as proof of the capability it
names:

- cp-00, cp-01, cp-02 and frozen cp-03 (chunk F, the bulk of the 118): frozen specimens that do
  not construct a contract on the current SDK, quarantined under `D-IMPL-261`/`D-IMPL-263`.
- frozen cp-06 (16 output + 3 door, chunk G): the specimen declares an evidence anchor over a
  resolver wired with no λ_c table and is refused at the builder since the `D-IMPL-341`
  registration ruling; quarantined with that reason, the specimen untouched.
- No `xfail` was added, removed or edited during this run. **Unexpected passes: 0.**

---

## 6. Skipped, unavailable, not executed

| scope | reason | required for launch? |
|---|---|---|
| `tests/conformance/test_orchestration.py` — 2 nodes | *"in-sdk reference adapter holds no outcome store"* — a by-design skip on the reference adapter | a scope decision: the reference adapter does not implement the outcome store these two nodes need; **not executed** anywhere in this run |
| `ci-coverage` | informational, no numeric gate | no; not executed |
| `tools/proof/tests` | not in the candidate (untracked local directory), not in CI | no; not applicable |
| `archived` marker — 225 nodes | deselected by design (`D-IMPL-265`); `--run-archived` not used | no |
| `make test` as ONE invocation | run as ten chunks under the tool's time limit; reconciled node by node against one collection | collection-order interactions **not reproduced** — a validation gap, named |

Every other quick-posture skip was executed by a leg or with the estate (§3).

---

## 7. Coverage accounting for the outstanding CP-14 gates — corrected

Seventeen unique outstanding ids (29 declared in `CP-SPEC-014` §G, 12 executing): seven
enrichment (`G05`, `G08`–`G12`, `G14`) and **ten governed**. The earlier breakdown — five
SDK-covered, two other-example, three partial, one uncovered — summed to eleven because `G15`
was counted twice. Each governed gate appears **once** below; overlapping coverage is labeled, not
partitioned.

| gate | claim | coverage, labeled |
|---|---|---|
| `G01` | empty-operator guard | **SDK control** (`tests/products/test_empty_operator_halves.py`, `test_refusal_envelope.py`) |
| `G04` | the governing debt is computed, never read | **partial** — SDK half controlled (`tests/products/test_evidence_derived_debt.py`, replay rehydration); CP-14 half (no table value routed) has no control; **open with the memo specification** by the launch-scope ruling |
| `G06` | Policy before Similarity on the ordered trace | **SDK control** (`tests/operators/test_planner.py::test_the_plan_runs_categories_in_dependency_order`) |
| `G07` | tolerance from the policy version, boundary `<=` | **partial** — SDK half controlled (`test_tolerance_exceeded.py`, `test_policy_constraints.py`); the date boundary has no control; open with the memo specification |
| `G13` | a refusal carries the governing F/C/S decomposition | **SDK control** (`tests/products/test_d_impl_338_refusal_evidence.py`) |
| `G15` | determinism | **SDK control AND example-level gate** — in-process by `test_delivery_determinism.py`; across processes by cp-06-canonical's and cp-03-canonical's door gates, not by an SDK test |
| `G16` | resolution and auditability kept apart (TRAP 1a) | **example-level gate only** (cp-13-canonical `CXRC-G01`/`G02`); no SDK test |
| `G21` | mixing floors bind | **SDK control** (`test_composite.py` floor tests; `test_d_impl_341_ttl_anchor.py::test_c11_a_composites_mixing_floor_is_measured_from_the_decision_instant`) |
| `G24` | the empty-string `sic` guard on CION | **uncovered** — the consumer's own projection logic; no SDK control can carry it; open with the memo specification |
| `G25` | no policy, no serve | **partial** — SDK half controlled (`test_policy_constraints.py`, `test_provenance_semantics.py`); the policy-version lookup by date has no control; open with the memo specification |

Ten rows, ten gates. Nothing invented, nothing deleted, nothing marked passed. CP-14's full memo
specification remains open.

---

## 8. Proposed dispositions — for review, not a release approval

### 8.1 Confirmed defects requiring correction

1. **The committed public-surface manifest is stale for `D-IMPL-341`'s signature changes**
   (`compose_children`, `build_governed_resolver`, `open_product`), and the surface log does not
   reconcile with the manifest (`GUARDED_TYPES` added and unlogged; `336-02` claims a name the
   manifest lacks). 4 nodes (§4.6). Regenerate the manifest with `make surface`, reconcile the
   fragments against it, and check that the existing 341 fragment names the three changed shapes.
   Owned by this branch.
2. **`hw1-companies-over-revenue`'s README expected-output fence is stale**: `D-IMPL-341` moved
   the content address by putting `ttl_anchor_at` on every new contract. 1 node (§4.8).
   Re-measure the fence from the run and record the cause. Owned by this branch.
3. **The HTTP door does not close over the refusal vocabulary**, and `composite-child-refusal`
   and `dependency-invalidation-refusal` escape it as an internal result rather than a response;
   the committed `openapi.json` also drifts from what the app emits. 8 nodes (§4.5). Standing
   before 341 by count; a real door defect regardless of when it began.
4. **Public symbols added without a phase-fragment claim.** 1 node (§4.1). A records defect:
   claim `GUARDED_TYPES`, `GuardedTypeDeclaration`, `declaration_for`, `ChildAcquisition`,
   `freshness_over_of` and the rest in their phases' fragments.
5. **The lint runner's own tests no longer describe the runner** — the registered rule set grew
   past "exactly these seven", and `main` exits 1 on an empty tree. 3 nodes (§4.9).

### 8.2 Existing limitations requiring explicit acceptance

- The six `D-GATE-341` residuals, as recorded: view-instant versus decision-instant reduction;
  the replay basis from the rehydrated declaration; refusal records pinning no half-life table;
  no child-bound composite floor control; the defensive unpinnable-clock guard; the covenant
  dual-TTL.
- The lower-level producer route's unrecorded pre-acquisition refusal (`D-IMPL-304`).
- The two by-design orchestration-conformance skips (§6).
- The four partial or uncovered CP-14 governed gates, open with the memo specification (§7).

### 8.3 Potentially stale tests requiring investigation

- `tests/invariants/test_no_obligation_vocabulary.py` (42): the guard flags the `Literal`
  vocabularies `D-IMPL-331`/`333` introduced (`DecayBasis`, `FreshnessAggregation`) and reports
  its own exemption no longer covering `_GLOB_CHARACTERS`. Either the exemption was meant to
  cover declared decay vocabularies or the code should not declare them this way; a ruling.
- `test_determination_authority_disclosure_delivery.py::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]` (1): a content pin on
  `CLAUDE.md` whose message says the revision is Dave's to order.
- `test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow` (1): a ratchet whose gate is green by its own
  admission.
- `tests/peering/test_admission_record.py` (1): a content-hash pin on `claims.py`.

### 8.4 Required validation that could not execute

- `make test` as a single invocation (collection-order interactions).
- `tests/conformance/test_orchestration.py`'s two outcome-store nodes.
- `ci-coverage` (informational).

**Nothing in this report infers launch readiness from the totals or from the product-gate
roster.** 8 536 passing nodes and 326 executing gates say the candidate does what its tests say;
the 62 failing nodes and the four unexecuted checks are what the release decision is about.

---

## 9. Evidence

Per-chunk junit files, logs and the parsed node-level inventory are in the session scratchpad
under `qual/` (`A_…xml` … `K_…xml`, `T_…xml`, `class_lookup.xml`, `leg-*.log`, `inventory.md`,
`collected.txt`, and `leg_<marker>_collected.txt` — the three leg selections behind §3's
node-level skip reconciliation). The `estate_env.sh` there derives connection names from one set and is not
committed. The worktree `/home/parkave/ccf_qual_f0656746` was removed after this report was
written.

---

## Subsequent results (added, not rewritten)

The measurements above are historical and stand as measured. Dave's disposition of them is
recorded in `docs/DECISIONS.md` under *RELEASE QUALIFICATION — FIRST CORRECTION GROUP GO*
(2026-09-19). The first correction group's repairs, node-by-node before/after results and
regression are in `docs/QUALIFICATION-f0656746-CORRECTION-1.md`; its evidence is under
`qualification/f0656746/`.

### Corrections to the measurements' attribution (added at the repair package, 2026-09-19)

The observations above stand as measured; two of their attributions were wrong and are corrected
here rather than rewritten there.

- **§4.7 / §8.3, the peering pin** (`tests/peering/test_admission_record.py` `::test_claims_py_is_unchanged_so_reading_a_cannot_creep_back_in`, as named at commit `f0656746`; renamed at the repair package):
  the report offered "the 341 closes" as the likely origin. Measured at the investigation: the
  pinned file is `src/ccf/contracts/claims.py`; it moved exactly twice, at `59cfc0cd` and
  `da14c544` under **D-IMPL-332** (`_TemporalClaim.valid_from` widened to `datetime | None`,
  hash-transparent), and the red entered `main` at `0d19599f`, the D-GATE-cp-09 merge.
  `LineageEntry`, the class the pin guards, is byte-identical throughout. D-IMPL-341 is not involved.
- **§4.2 / §8.3, the no-obligation guard**: the report repeated the last node's message, "the
  exemption stopped covering `_GLOB_CHARACTERS`". That message was hard-coded and misattributed:
  `_GLOB_CHARACTERS` is seen and exempted; the assertion is a whole-file cleanliness check and it
  failed on the same two unexempted declarations (`DecayBasis`, `FreshnessAggregation`) as the
  other 41 nodes. There was one cause, not two. The message now names what it finds.
- **§4.3, the CLAUDE.md pin**: "not yet established" is now established — red on every commit
  since `4683f245`, Phase 24.6's own close commit, and already ruled a proof-machinery defect
  (`D-IMPL-269 (2)`, `D-IMPL-270 (2)`).

Full findings: `docs/QUALIFICATION-f0656746-INVESTIGATION.md`.
