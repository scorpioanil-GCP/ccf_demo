---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 05
subsystem: testing
status: paused-at-checkpoint
tags: [examples, kyc, ubo, context-product, snippet-markers, ast-lint, no-hardcoding, decision-replay]

# Dependency graph
requires:
  - phase: 16-02
    provides: "the KYC/UBO source estate (14 entities, 16 relationships, ownershipPercent on 9 edges) plus source_estate.py and the wave-2 run.py placeholder this plan replaced in place"
  - phase: 16-04
    provides: "tools/docs_tests/test_gate_two_wording.py — the standing criterion-8 gate over published prose that the new README and test prose must not trip"
provides:
  - "examples/s1-01-hello-context-product — the phase's reference example, with the CCF call spine physically separated from deployment code"
  - "the seven-marker spine contract (boot/ingest/operators/project/gate/record/serve) as a shape every later example copies"
  - "tests/examples/test_s1_01_output.py — 21 tests on the served Context Product and its five-dimension replay record"
  - "tests/examples/test_section_one_is_agent_free.py — criterion 2's AST gate, armed by glob over examples/s1-*"
  - "tests/examples/test_spine_separation.py — criterion 6's structural half, with five negative controls"
  - "one gate call site, one projecting body and one resolved binder site of fresh headroom on the three tests/products/ floors"
affects: [16-07, 16-08, 16-12, 16-18, "Section 2 and Section 3 examples", "docs surface pages citing the A-1 import convention"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "spine.py / deployment.py split — the CCF call spine in one module, the adopter's own code in another, held together by Protocols rather than by inheritance"
    - "structural-Protocol coupling between example modules (spine.Scenario, spine.DeploymentBinding) so neither module imports the other"
    - "glob-armed test scope (examples/s1-*) so a later example arms a gate by existing rather than by being listed"
    - "negative controls copied from the shipped tree rather than synthesized, so a gate is verified to refuse the real files"

key-files:
  created:
    - examples/s1-01-hello-context-product/spine.py
    - examples/s1-01-hello-context-product/deployment.py
    - examples/s1-01-hello-context-product/README.md
    - examples/s1-01-hello-context-product/artifacts/ (15 documents)
    - tests/examples/test_s1_01_output.py
    - tests/examples/test_section_one_is_agent_free.py
    - tests/examples/test_spine_separation.py
  modified:
    - examples/s1-01-hello-context-product/run.py

key-decisions:
  - "The spine/deployment boundary is enforced structurally (Protocols + marker regions in one module only), not editorially — neither module imports the other"
  - "test_spine_separation.py scopes itself to examples/s1-* rather than to 'any directory with a spine.py', so a renamed spine.py is a failure rather than a vacuous pass"
  - "The agent-free guard uses tools.lints' imported_module_names AND submodule_import_names and defines no local _ccf_imports — the CR-02 hole is reproduced by copying the sibling helper"
  - "Negative-control injections are APPENDED, not prepended: Section-1 modules open with a docstring then `from __future__ import annotations`, and a prepended import makes the copy unparseable"
  - "The multi-hop property is asserted through expected.yaml's boundary_case_party — a party at exactly the threshold one hop down and a fraction of a percent three hops down — so a regression to single-hop lookup goes red"

patterns-established:
  - "Seven canonical marker names and no eighth: D-11 adds no marker vocabulary, and the closure check is as load-bearing as the ordering check"
  - "Two categories of example assertion, stated in the test module's own docstring: independent expectations (from expected.yaml) vs propagation checks (single-sourced from an artifact read by both ends)"
  - "The SURFACE-AUDIT A-4 caveat travels attached to the required_operator_keys assertion and is never promoted into a claim about separate authorship"

requirements-completed: [DOCS-11, DOCS-12, EXAM-01, DEMO-01]

# Metrics
duration: 35min
completed: 2026-08-10
---

# Phase 16 Plan 05: Hello, Context Product — the spine/deployment split Summary

**A deterministic, agent-free KYC/UBO example that answers "who ultimately owns Acme?" by aggregating ownership across a multi-hop chain, with every CCF call in `spine.py` behind seven ordered marker regions and every domain value in an artifact — plus three test modules pinning its output, its agent-freeness and the split itself.**

## Performance

- **Duration:** ~35 min (this session, Tasks 2–3). Task 1 was executed and merged in a prior session.
- **Tasks:** 2 of 3 complete; Task 3 is a blocking human-verify checkpoint and is where execution stops.
- **Files created:** 22 (3 code modules, 15 artifacts, 1 README, 3 test modules)
- **Files modified:** 1 (`run.py`, replaced in place)

## Accomplishments

- **The boundary is visible from the repository, not the rendered site.** `spine.py` (402 lines) holds every call the fabric requires, wrapped in the seven Phase 14 `D-07` regions in order — `boot`, `ingest`, `operators`, `project`, `gate`, `record`, `serve` — and contains no entity class, source system, identifier, threshold, policy version, query or boundary. `deployment.py` (441 lines) holds the projection Π, this deployment's artifact-key vocabulary and scenario setup. Neither module imports the other; they are held together by two Protocols (`Scenario`, `DeploymentBinding`).
- **The example earns its domain.** Jane Doe's real interest in the subject is 12.0% direct plus 60.0% of a holder that itself holds 30.0% — 30.0% in total, stated in no record of any source system. All four operator categories are load-bearing rather than decorative: traversal over the ownership chain, temporal against a transfer effective a month after the boundary, policy substituting out a jurisdiction-restricted director, similarity ranking a below-floor screening candidate out.
- **The multi-hop property is asserted, not assumed.** `test_the_answer_is_a_sum_over_paths_not_a_single_hop` uses `expected.yaml`'s `boundary_case_party`: a natural person at exactly the 25.0% threshold one hop down and at 1.125% of the subject three hops down. A projection that regressed to single-hop lookup would report her as a beneficial owner, and that test would go red.
- **Section 1 is agent-free by construction and by CI.** No module under `examples/s1-*` reaches `ccf.agents`, `ccf.skills`, `ccf.workflow`, `ccf.hitl` or `ccf_runtime.adapters`. The guard is an AST walk over a glob, so plan 16-08's second Section-1 example arms it by existing.
- **Floor headroom restored (W-4).** All three `tests/products/` floors now sit one above their observed minimum, which is what lets them survive waves 8 and 10 until plan 16-18 re-floors at wave 11.

## Task Commits

1. **Task 1: Split the spine from the deployment and author the artifact set** — `1a96b3f` (feat) — executed and merged in a prior session (merge `e948baa`)
2. **Task 2: Ship the output, agent-free and spine-separation assertions** — `e44dc66` (test)
   - **Follow-up fix:** `c6aa4ba` (fix) — sibling-module collision with `tests/deployment`, found by `make ci-core`. See *Deviations*.
3. **Task 3: Read the spine and the deployment side by side** — **blocking checkpoint, not executed.** Awaiting Dave.

## Floor Headroom Measurement (Task 1 acceptance criterion W-4)

Recomputed at `e44dc66` by importing `tests/products/test_gate_two_call_shape.py` and re-running its three discovery helpers against the tree:

| Floor | Constant | Floor value | Observed at `e44dc66` | Headroom | s1-01's contribution |
| --- | --- | --- | --- | --- | --- |
| Gate call sites | `MINIMUM_GATE_CALL_SITES` | 9 | **10** | +1 | `examples/s1-01-hello-context-product/spine.py` |
| Projecting bodies | `MINIMUM_PROJECTING_BODIES` | 11 | **12** | +1 | `examples/s1-01-hello-context-product/spine.py` |
| Resolved binder sites | `MINIMUM_RESOLVED_BINDER_SITES` | 11 | **12** | +1 | `examples/s1-01-hello-context-product/spine.py:275` |

The spine's `run_gates(...)` call and its `plan = deployment.plan_class(plan_id=..., required=...)` construction one statement before `refuse_operator_set_divergence(...)` are what put it in all three sets.

## Files Created/Modified

**Task 1 (merged previously):**
- `examples/s1-01-hello-context-product/spine.py` — the CCF call spine; seven ordered marker regions, `[MECHANISM]` banner, A-1 import discipline (`from ccf.deployment import ...`, never a submodule FQN)
- `examples/s1-01-hello-context-product/deployment.py` — `UltimateBeneficialOwnershipPlan` (the projection), the `KEY_*` artifact vocabulary, `KycDeployment`, plus `expectation()` and `envelope_count()` helpers the test module reads through
- `examples/s1-01-hello-context-product/run.py` — replaced in place; a thin driver that asserts nothing and prints nothing, with an `--estate` path that materialises the enterprise source estate
- `examples/s1-01-hello-context-product/artifacts/` — 15 documents (manifest, resolution spec, policy bundle, product class, projection requirements, product governance, perspective, four `ccf.operator-parameters.*`, the UBO question, the `role: load` signal batch, the decision instants, the expectation), each with a `$schema` header and an `[ADAPT]`/`[MECHANISM]` header

**Task 2 (this session):**
- `tests/examples/test_s1_01_output.py` — 21 tests across preconditions, the gates, the served product, the answer, the declared absences and the five replay dimensions. Carries the two-categories docstring and the A-4 caveat, plus the loader's collision control.
- `tests/examples/test_section_one_is_agent_free.py` — 11 tests: the deny list with a documented reason per entry, a populated-tree precondition, per-module parametrized checks, three parametrized negative controls, and a prose control proving the AST scan does not fire on comments
- `tests/examples/test_spine_separation.py` — 13 tests: precondition, marker-pattern probe, spine presence, canonical ordering (both directions reported by name), closure, non-spanning, an aggregate predicate, a CWD-independence test, and five negative controls
- `examples/s1-01-hello-context-product/README.md` — exactly seven `## ` headings in template order

## Decisions Made

- **Scope of the separation gate: `examples/s1-*`, by glob.** The alternative — "any directory whose modules carry the canonical markers" — would have swept in `examples/00-quickstart/run.py`, which carries the same seven names in a single module as the pre-`D-11` shape, and would have gone silent when `spine.py` was renamed. Scoping by directory convention makes a renamed spine a failure and auto-arms on 16-08.
- **Sibling modules may carry markers, but not canonical ones.** The plan's Task-1 criterion allows a region wholly inside `deployment.py`; `D-11` forbids new marker vocabulary. The gate enforces both: siblings must not open any of the seven names, and whatever markers they do carry must balance within the file.
- **Negative controls append rather than prepend.** A prepended import lands before the module docstring and `from __future__ import annotations`, which is a `SyntaxError` — a control that "caught" a violation by failing to parse would prove nothing.
- **`test_the_product_answers_the_question_the_artifacts_asked` reaches the subject through `deployment.QUESTION_SUBJECT`** rather than through a key literal, so the question document's field names live in exactly one place.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The example's sibling modules resolved to the wrong tree under the full suite**

- **Found during:** Task 2, at the `make ci-core` acceptance check — *after* the targeted verification command in the plan had passed.
- **Issue:** `run.py` puts its own directory on `sys.path` and imports its siblings by bare name (`import deployment`, `import spine`, `import source_estate`). `tests/deployment/` is a package with an `__init__.py`, so pytest imports it as `deployment` while collecting `tests/deployment/test_*.py` — which sorts before `tests/examples/`. By the time this module's fixtures ran, `sys.modules["deployment"]` already held the *test* package, the bare import returned the cached module, and all 20 fixtures failed with `module 'deployment' has no attribute 'KycDeployment'`. **Running the three new test modules alone hides this completely**, which is exactly how it reached a green targeted run and a red `make ci-core`.
- **Fix:** `_load_example()` evicts the three sibling names for the duration of the `exec_module` call — forcing a fresh resolution through `sys.path`, where `run.py` has just put the example directory at index 0 — and restores the originals in a `finally`, so every test collected afterwards still finds `tests/deployment`. The loader then asserts the resolved `deployment` really is the example's, so a future regression fails loudly at the loader rather than as a puzzling `AttributeError`. `test_the_driver_loads_beside_a_same_named_module_from_another_tree` plants a decoy module so the case is exercised regardless of collection order, and pins that the shadowing is temporary.
- **Files modified:** `tests/examples/test_s1_01_output.py`
- **Verification:** `pytest tests/deployment tests/examples/test_s1_01_output.py test_section_one_is_agent_free.py test_spine_separation.py -q` → 194 passed (this ordering reproduces the collision); `make ci-core` green.
- **Committed in:** `c6aa4ba`

**The example itself was deliberately not changed.** A user running `python examples/s1-01-hello-context-product/run.py` has no `tests/deployment` on `sys.path` and was never affected; the collision exists only inside the pytest process, so the fix belongs in the loader that creates the condition. `run.py` and `deployment.py` are also the files the Task 3 checkpoint asks Dave to read, and rewriting them under him during a blocking gate would be the wrong move.

**Observation for Dave, not acted on:** a user who copies this example into a project that already has a top-level `deployment` module would hit the same ambiguity. If that is worth closing, the fix is in `run.py` (load siblings by file path under example-scoped names) and it makes the thin driver noticeably less thin — which is why it is raised here rather than done.

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** No scope creep. The fix is confined to the test module the plan already assigned to Task 2, and it added one test.

### Task 1's shipped output

Read and verified rather than rewritten. **No defect was found, so no corrective commit was needed:**

- `run.py` exits 0 and writes a served Context Product.
- `spine.py` carries exactly the seven canonical markers, correctly named and ordered, with none in `deployment.py`.
- `python -m tools.lints --all` exits 0.
- The served payload matches `expected.yaml` exactly, including the three per-party aggregate percentages.

## Issues Encountered

- **`test_the_gate_refuses_an_unclosed_region` initially removed the first region's `[end:...]`,** which the gate refused as an *interleaving* ("`[start:ingest]` opens while `[start:boot]` is still open") rather than as an unclosed region. Correct refusal, wrong message. Changed the control to remove the **last** region's close, where nothing follows it to notice — so the control now exercises the end-of-file branch it is aimed at. Both branches are refused; only one is asserted per control.
- **A targeted test run is not evidence that the suite is green.** The sibling-module collision above passed every check the plan's Task-2 `<verify>` block names and failed only under `make ci-core`, because the defect is a function of *collection order across directories*. The lesson is recorded rather than just fixed: for any test module that loads an example by file path, the confirming run is the full suite, not the module.

## Upstream Rulings Honoured

- **D-IMPL-94 (Q-2, approved 2026-08-10).** `assembly_mode: algorithmic` is documented in `product-class.yaml` and in the README as a governance choice describing how the **substrate** was assembled, with `llm_packaged` and `swarm_assembled` named as Phase 17 arrivals. `test_the_record_carries_all_five_dimensions` asserts the value propagates into replay dimension 3 (`ModelVersionRecord.assembly_mode`).
- **D-IMPL-95 (Dave, 2026-08-10).** Systems of record are read-only to L1. No assertion written in this plan names an enterprise source store as a graph target; the README states it explicitly under *Run it*, and the `--estate` path is described as writing outside CCF's graph. The example is `backend: sqlite` and CCF-owned, so it complies by construction.
- **D-IMPL-52 / CLAUDE.md §9 (the horizontal-domain mix).** Named in the README's *What this demonstrates* rather than fallen into silently: Section 1 is KYC/UBO because that is where the multi-hop data lives; Sections 2 and 3 carry other domains, so the mix is satisfied across the suite rather than within Section 1.
- **Criterion 8 / D-IMPL-86.** Neither the README nor the test module contains the token "independence" (verified: 0 occurrences in both). The corresponding "What would fail" row is framed as the binder refusing a disagreement before the engine runs, not as two sets being separately witnessed. The superseded D-IMPL-84/85 manifest claim was not copied forward (0 occurrences of "cannot name an author-versioned" under `artifacts/`).

## Verification

All at `c6aa4ba`.

| Check | Result |
| --- | --- |
| `python examples/s1-01-hello-context-product/run.py` | exit 0 |
| `pytest` on the three new modules | **45 passed** (21 output, 11 agent-free, 13 separation) |
| `pytest tests/deployment` + the three new modules (reproduces the collision ordering) | 194 passed |
| `python -m tools.lints --all` | exit 0 — no prompt literal, agent definition or routing constant |
| `python -m mypy` | clean over 186 source files |
| `pytest tools/docs_tests/test_gate_two_wording.py test_snippet_gate.py tests/examples/test_artifact_schema_headers.py test_source_estate.py -q` | 47 passed |
| **`make ci-core`** (lint + mypy + full suite) | **exit 0 — 2509 passed, 81 skipped, 350.7s** |
| README `## ` headings | exactly 7, in template order |
| `git diff --stat d7f2a66..HEAD -- src/ runtime/` | **empty** |
| `git diff --stat d7f2a66..HEAD -- .planning/STATE.md .planning/ROADMAP.md` | **empty** — orchestrator owns those writes |
| `grep -c "independence"` in README and output test | 0 / 0 |
| `grep -c "cannot name an author-versioned"` under `artifacts/` | 0 |

`make docs-strict` was **not** run: no `public/` page includes these files yet, so the publication surface is unchanged by this plan. It is part of the plan-level verification and belongs after the Task 3 gate.

## Known Stubs

None. Every value the example serves is computed from ingested signal through the four operator categories and the projection; nothing is hardcoded, mocked or placeholder.

## Next Phase Readiness

**Blocked on Task 3 — a blocking human-verify checkpoint.** The structural test proves the markers are present, ordered, closed and non-spanning; it cannot prove a reader can *see* which code is CCF's and which is theirs, and Dave's own sentence is the standard. Every other example in the suite copies this shape, so a correction is cheapest now.

Ready once approved:
- **16-07** — the per-backend siblings and `backends.yaml`. The manifest already declares `backend: sqlite` as a kind only, with no DSN, path, host or credential anywhere in the artifact set; the connection value arrives from the caller.
- **16-08** — the second Section-1 example. Both new gates are glob-armed on `examples/s1-*` and will cover it the day it lands, provided it ships a `spine.py`.
- **16-12** — the `make example-s1-01` target the README and `run.py` docstring both name.
- **16-18** — re-flooring the three `tests/products/` counts at wave 11. Current headroom is +1 on each.

## Self-Check: PASSED

- Files claimed created/modified: all 8 named code, doc and test paths present on disk; `artifacts/` holds 16 documents (15 from `1a96b3f`, plus `source-estate.yaml` from plan 16-02).
- Commits claimed: `1a96b3f` (Task 1, merged via `e948baa`), `e44dc66` (Task 2), `c6aa4ba` (Task 2 fix) — all three resolve in `git log`.
- Scope boundaries: `git diff d7f2a66..HEAD -- src/ runtime/` empty; `.planning/STATE.md` and `.planning/ROADMAP.md` untouched.

---
*Phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar*
*Completed: 2026-08-10 (Tasks 1–2; Task 3 awaiting human verification)*
