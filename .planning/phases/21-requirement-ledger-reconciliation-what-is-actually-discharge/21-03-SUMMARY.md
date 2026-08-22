---
phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
plan: 03
subsystem: testing
tags: [ledger, audit, citations, documentation-lane, re-homing, rulings]

requires:
  - phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
    provides: the strict parser, Check A, `refuse_unresolvable`, the pinned diff base, and the calibrated `path.py::symbol` citation form
provides:
  - 14 reconciled rows across five phase lanes — Phase 9, 13, 14, 15.5 and 15.6 — in both ledger channels
  - the phase's first ANCHORED LINE citations, proven checked by sabotage rather than assumed
  - `CPS-03` closed at `Complete as ruled` in all THREE places the row is stated, not the two the plan named
  - the second named absence of the phase — `EXAM-02`, `Not built`, with four surviving checks
  - a measured coverage finding on `DOCS-03` that a page-source count would have got wrong
affects: [21-04, 21-05, 21-06, 21-07]

tech-stack:
  added: []
  patterns:
    - "Where the evidence is not Python, an anchored line citation whose anchor is a dot- or kebab-namespaced token — and the anchor is verified TOKENISH before it is trusted, because `_anchor_verdict` returns `None` on a plain word and the citation is then silently unchecked"
    - "A re-homed requirement is judged against the target the re-homing names, and the status cell says which target"
    - "A measurement taken on page SOURCES is not a measurement of the published tree; snippet includes have to be resolved first"

key-files:
  created:
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-03-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "`EXAM-02` is `Not built` and not `Orphaned`: `RETIRED.md` says retiring Phase 16 retires the APPROACH, not the NEED, and the Phase-13 substance is still tracked and still in the `examples:` aggregate — the named home is what is missing, not the work"
  - "All six Phase 14 rows took D-17 route 1 (cite the guarding test). Route 2 was never needed in this lane, so the concession the D-17 reading grants was not spent here"
  - "`CPS-03` is stated in THREE places in this file, not two. The plan named the traceability table and the checkbox channel; the CPS-lane evidence table still read `Pending by design` and would have been left contradicting both"
  - "`DOCS-03` is `Partial` on a number that had to be re-measured: page sources alone give 5 of 27 class ids named, which is WRONG — the ids arrive through snippet includes. Rendered, it is 21 of 27"

patterns-established:
  - "Before writing an anchored line citation, run the shipped `_anchor_verdict` against it and require `True`, not `None` — then sabotage one and watch `cite02-anchor` go red"

requirements-completed: [RECON-01, RECON-02, RECON-04]

duration: 100min
completed: 2026-08-22
---

# Phase 21 Plan 03: Verdicts for the Remaining 14 Non-Phase-16 Rows — Summary

**Fourteen more rows carry a verdict — bringing the phase to 36 of 54 — and the lane that was supposed to be the hard one for citations turned out not to need the concession it was granted: every one of the six Phase 14 documentation rows had a guarding test to cite, so D-17's route 2 went unused there and was spent instead on `HARD-01` and `DOCS-06`, where the evidence genuinely is a ruling; the seven anchored line citations that resulted were each checked against the shipped `_anchor_verdict` before they were written and then watched going red under sabotage, because an anchor the lint silently skips is a citation that only looks like one.**

## Performance

- **Duration:** ~100 min
- **Tasks:** 3 of 3
- **Commits:** 3 task commits + this one
- **Tests added:** 0 — deliberately. `make gate-tools` is 406 + 189, unmoved from plan `21-02`.

## Task Commits

1. **Task 1: `HARD-01`..`03` and `EXAM-01`..`03`** — `16b6fe2` (feat)
2. **Task 2: `DOCS-01`..`DOCS-06`, the Phase 14 documentation lane** — `1b81927` (feat)
3. **Task 3: `CPS-03`, `DCD-02` confirmed, and the regenerated coupling inventory** — `73bc457` (feat)
4. **This SUMMARY + the regenerated coupling inventory** — final commit (docs)

## The 14 rows

| Id | Verdict | Citation | Guarding test |
|---|---|---|---|
| `HARD-01` | Complete | `D-IMPL-68`..`D-IMPL-73`, anchored at `docs/DECISIONS.md:211`, `:213`, `:215`, `:217`, `:219`, `:221` | **none — stated in the cell.** A process row: the rulings *are* the evidence, and the cell says so rather than leaving a reader to wonder |
| `HARD-02` | Complete | `src/ccf/hitl/transport.py::InMemoryHitlTransport` | `tests/hitl/test_transport_concurrency.py::test_mixed_op_hammer_loses_and_duplicates_nothing`, plus `::test_racing_removes_for_one_event_yield_exactly_one_claim` and the D-16 submit-path hammer |
| `HARD-03` | Complete | `runtime/ccf_runtime/orchestration/common.py::run_coroutine_sync` | `tests/conformance/test_orchestration.py::test_the_introspection_seam_is_loop_safe`, plus `::test_a_never_executed_segment_raises_the_same_typed_error_on_every_leg` parametrized over three legs |
| `EXAM-01` | **Partial** | `examples/external/00-hello-context/run.py::README_HEADINGS` | `tests/examples/test_ext00_serve_output.py::test_the_readme_keeps_its_seven_template_headings` — **and it guards the wrong tree**, which is half the reason the verdict is Partial |
| `EXAM-02` | **Not built** | — (see the absence below) | none — there is nothing to guard |
| `EXAM-03` | **Partial** | `tests/examples/test_s1_01_output.py::test_the_served_shape_matches_the_declared_expectation` | same, gated by `::test_the_expectation_document_declares_something` so an empty expectation cannot make the comparison trivially true |
| `DOCS-01` | Complete | `tools/docs_tests/test_documented_commands_exist.py::test_every_documented_make_target_exists` | same, plus both snippet-gate controls and `tools/docs_tests/test_advisory_discharge.py::test_a3_no_documented_boot_signature_disagrees_with_the_code` |
| `DOCS-02` | Complete | `tools/docs_tests/test_mkdocstrings_gate.py::test_a_renamed_identifier_fails_the_strict_build` | same, plus `tools/publish_scan_tests/test_publish_scan.py::test_whitepaper_text_trips_the_shingle_rule` for the never-published limb |
| `DOCS-03` | **Partial** | `tests/cli/test_schema_export.py::test_the_committed_schemas_match_what_the_classes_emit` | same, plus the three per-advisory content gates on the artifact pages |
| `DOCS-04` | Complete | `tools/docs_tests/test_diagram_coverage.py::test_no_diagram_is_orphaned` | same, in both directions, with `::test_every_embed_names_an_existing_diagram` and `::test_no_diagram_is_embedded_twice` |
| `DOCS-05` | Complete | `tests/http_api/test_openapi.py::test_the_committed_spec_matches_what_the_app_emits` | same, with `tools/docs_tests/test_openapi_drift_control.py::test_a_renamed_endpoint_is_reported_as_a_difference` as the standing negative control |
| `DOCS-06` | Complete | `D-IMPL-72` anchored at `docs/DECISIONS.md:219` | `tools/docs_tests/test_mkdocstrings_gate.py::test_the_unmodified_tree_builds_clean` — **and it does not reach the CI wiring**; see the named gap below |
| `CPS-03` | **Complete as ruled** | `D-IMPL-113` at `docs/DECISIONS.md:390` **and** `D-IMPL-121` at `docs/DECISIONS.md:408` | `tools/docs_tests/test_resolver_seam_obligations.py::test_both_seams_cite_both_call_sites` |
| `DCD-02` | Partial — **confirmed, not rewritten** | unchanged: plans `15.6-05`, `15.6-06`, `D-IMPL-119` limb 3(b) | unchanged |

**No test was written in this plan, anywhere, for any purpose** — `D-05` holds and `git diff --name-only` over the three task commits returns exactly two paths, `.planning/REQUIREMENTS.md` and the generated coupling inventory.

## The D-17 reading, as applied to the six Phase 14 documentation rows

Plan `21-02` warned that this lane would hit the citation-grammar limit harder than the client lane did, *"because far more of its evidence lives in files the lint's path grammar cannot name."* **It did not.** The measured outcome is worth stating precisely, because a later reader will otherwise assume the concession was spent.

**All six Phase 14 rows took route 1 — cite the guarding test.** Every one of `DOCS-01` through `DOCS-06` had a `tools/docs_tests/…py::…` or `tools/publish_scan_tests/…py::…` or `tests/…py::…` symbol available for its load-bearing limb, so all six are fully checked by `cite03-node-id` and all six discharge `D-04` at the same time. **Route 2 was used nowhere in this lane. Route 3 was used nowhere in this lane.**

The reason the lane was easier than forecast is structural and is worth carrying forward: **Phase 14 did not ship pages, it shipped pages plus gates**. The publish scan, the mkdocstrings strict-collection control, the snippet gate, the diagram bijection, the documented-command bijection, the OpenAPI drift control and the per-advisory content gates are all Python, all under `tools/`, and all named after the property they hold. A documentation lane that had shipped prose alone would have had nothing citable; this one had a gate per claim.

Where route 2 *was* used — seven anchored line citations, all into `docs/DECISIONS.md` — the evidence genuinely is a ruling and not a document about the tree: `HARD-01`'s six-item batch (`D-IMPL-68`..`D-IMPL-73`) and `DOCS-06`'s logged D-10 amendment (`D-IMPL-72`), plus `CPS-03`'s two rulings in task 3. **This is D-17's intended case, not its escape hatch.**

**The hazard route 2 carries, and how it was closed rather than trusted.** `_anchor_verdict` in `tools/lints/citations.py` returns `None` — *unchecked, no finding, silently* — for a plain-word anchor, so a citation that reads as anchored can be carrying nothing. Every anchored citation written in this plan was run through the shipped `_anchor_verdict` before the commit, and every one returned `True` rather than `None`; the twelve from task 1 were checked as a batch and both of task 3's individually. Then one was deliberately mis-pointed (`D-IMPL-70` re-aimed at `docs/DECISIONS.md:213`, which holds `D-IMPL-69`) and `python -m tools.lints --citations` went **red** at `cite02-anchor`, naming the row, the anchor and the wrong lines. It was restored from a backup taken first, and `git diff --stat` after restoring showed the file back at its intended twelve changed citations. A route-2 citation nobody watched refuse is exactly the shape `D-17` was ruled *not* to be a relaxation of.

## The one `Not built` row, and what closing it would mean

**`EXAM-02` — the re-homed target of the example-enrichment obligation does not exist.**

The absence is four things, each checked at execution time rather than inferred:

- `examples/s3-02-agentic-skills` is not a directory in this tree.
- **No `s3-` example of any number is tracked under `examples/`.** The tracked example trees are `00-quickstart` … `08-e2e-demo`, `external/`, `hw1-companies-over-revenue`, `hw1-harness-clients`, `s1-00-companies-over-revenue` and `s1-01-hello-context-product`. Sections 2 and 3 are absent entirely.
- No `example-s3-` target exists in the `Makefile`; the only `example-s*` targets are `example-s1-00` and `example-s1-01`.
- Phase 16, which was to build the Section-3 suite, was **retired at `D-IMPL-152`** with fourteen plans unexecuted.

**Why `Not built` and not `Orphaned`, since the target is a Phase-16 artifact.** `RETIRED.md` is explicit that retiring the phase *"retires the approach, not the need"*, and the tree agrees: the Phase-13 delivery the re-homing moved the obligation off — `examples/01-agent-basics`, `examples/02-skilling`, `examples/05-workflow-hitl` and `examples/06-decision-replay` — is still tracked and still inside the `examples:` aggregate `make ci` runs. The substance is in the tree; only the named home is not. `Orphaned` would claim the obligation has no referent, and that is not what was measured.

**For plan `21-05`'s work list, lifted so it need not be re-derived:**

> Closing `EXAM-02` means re-deriving the enrichment obligation against the surface that exists now rather than lifting `abandoned/16-*`'s Section-3 plan — a worked example whose definition artifacts carry the specialization axes, skilling, HITL and replay surface, with the example code staying thin and generic under the No-Hardcoding Rule. **It is coupled to `CLNT-17` and cannot be sequenced independently of it:** the four Phase-13 trees that currently carry this substance are among the nine `DOCS-17` condemns, so building a replacement before they are retired duplicates the surface, and retiring them before it exists deletes the only worked demonstration of skilling and HITL in the tree. It also needs a ruling on whether the replacement keeps the `s3-` naming at all, since the section scheme was Phase 16's and Phase 16 is not resumable. **Nothing on this list was started here:** `D-11` and the ROADMAP's out-of-scope paragraph forbid an executor closing a gap the audit discovers, and the pinned-base fence over `src/ runtime/ examples/ public/ tests/ pyproject.toml` is empty, which is the mechanical proof.

There is no `Orphaned` row in this plan.

## Two measurements this plan owes the record

### `DOCS-03`: the number a page-source count gives is wrong

`DOCS-03` is `Partial` on artifact-class coverage, and the figure in its cell had to be taken twice.

| How it was counted | Class ids named in `public/` |
|---|---|
| grepping the page **sources** | **5 of 27** |
| grepping the **rendered** pages, with every `--8<--` snippet include resolved | **21 of 27** |

The first number is wrong and would have been a defamatory finding against a documentation suite that is substantially better than it says. The class ids do not appear in the page prose; they arrive through the worked-example artifacts the pages include, and `pymdownx.snippets` resolves those at build time. **The cell carries 21 of 27 and states in its own text that the count is on the rendered tree with includes resolved**, so a later reader who greps `public/` and gets 5 knows immediately that they are holding the wrong predicate — the same courtesy plan `21-01`'s module extends to the 54-vs-56 and 133-vs-143 figures.

The six genuinely uncovered class ids are named in the cell rather than counted: `ccf.admission-record`, `ccf.deployment-config`, `ccf.peering-inbound-payload-ceiling`, `ccf.product-entitlement-policy`, `ccf.product-request-contract` and `ccf.scope-mapping`.

### `DOCS-06`: the limb that ships and the limb no gate holds

`DOCS-06` is `Complete` — `docs-strict` **is** a leg of the `ci` target, the workflow **does** carry a blocking `docs` job running the same command string, and `mkdocs.yml` sets `strict: true` so the plain and gated builds cannot diverge. But the row's cell also names a gap, deliberately, because it is the kind that reads as covered:

> **No test in this tree reads the `ci` target's composition or the workflow file.** Measured: `grep -rn "docs-strict" --include=*.py tools/ tests/` returns only prose in docstrings. Every gate cited for `DOCS-06` proves the strict build **passes**; none of them proves it is **wired in**. If a later edit dropped `docs-strict` from `make ci` or softened the `docs` job, nothing would go red.

That is not a defect this plan may fix (`D-11`), and it is not a `Not built` row — the requirement is satisfied. It is a named gap for `21-05` to carry, and it is the same shape as the `Makefile`-citation hole already in `deferred-items.md`: a claim about build wiring that the toolchain has no way to check.

## Deviations from Plan

### 1. [Rule 2 — the row is stated in three places, and the plan named two]

- **Found during:** Task 3(a).
- **Issue:** The plan directs `CPS-03`'s verdict into the traceability table and the checkbox channel. `.planning/REQUIREMENTS.md` states `CPS-03` a **third** time, in the CPS-lane evidence table below the traceability table, and that cell opened `**Pending by design (D-IMPL-113 and D-IMPL-121).**` — the exact phrase `D-IMPL-173` was ruled to replace. Writing only the two channels the plan named would have left the file asserting `Complete as ruled` and `Pending by design` about one row, one screen apart.
- **Fix:** All three were written, each carrying the `by design, not by omission` clause and both entry numbers. The evidence table is not parsed by `traceability_rows`, so nothing mechanical caught this and nothing mechanical would have.
- **Commit:** `73bc457`

### 2. [Rule 1 — a citation named a symbol that does not exist, and the lint caught it]

- **Found during:** Task 2, first `--citations` run after the edit.
- **Issue:** A first draft of `DOCS-06` cited `tools/docs_tests/test_advisory_discharge.py::test_a2_the_maintainer_page_names_its_subject`. The module defines `test_a2_the_maintainer_page_is_published_and_names_its_subject`. `cite03-node-id` went red naming the row, the file and the missing symbol.
- **Fix:** The citation was **dropped** rather than repaired, because A-2 is the surface-toolchain page and was never `DOCS-06`'s subject — the wrong-symbol error was downstream of a wrong-evidence error, and fixing only the name would have left a citation that resolved and did not support the claim.
- **Worth recording:** this is the second time in this phase the citation lint has caught a symbol error inside the work that was correcting citations (plan `21-01`'s `fabric_diff`/`client_surface_diff` was the first). It is the half of the lint's behaviour its own docstring credits it with, arriving twice.
- **Commit:** `1b81927`

### 3. The `EXAM` rows' re-homed targets are mostly absent, which the plan's framing did not anticipate

- **Found during:** Task 1.
- **Issue:** The plan says to judge the three `EXAM` rows against their `[Phase 16 re-homing, D-08]` targets. Two of the three targets do not exist: `examples/s3-02-agentic-skills` is absent outright, and *"every new Section-1/2/3 example"* resolves to two Section-1 trees and nothing else.
- **Resolution:** The verdicts are taken against the re-homed targets **as instructed**, which is what produces one `Not built` and two `Partial`s, and each cell names the target it was judged against so a reader is never left guessing which subject the verdict is about. The alternative — quietly judging against examples `00`–`07`, which are still tracked and largely green — would have produced three `Complete`s and measured the wrong thing, which is precisely threat `T-21-16`.

### 4. `DCD-02` was confirmed against the tree, not taken on report

- **Found during:** Task 3(b).
- **What was checked, rather than assumed:** `examples/s1-01-hello-context-product/deployment.py::KycScenario`'s `debt_evidence` still ends `return NO_DEBT_EVIDENCE` with `del view` above it, which is `D-IMPL-119` limb 3(b)'s omission path taken explicitly — so the cell's *"returns the sentinel unconditionally"* is still true of the tree. `15.6-05-PLAN.md`, `15.6-05-SUMMARY.md`, `15.6-06-PLAN.md` and `15.6-06-SUMMARY.md` all resolve. `refuse_unresolvable` reports zero messages over all 70 citation tokens now in status cells.
- **Disposition:** **The verdict stands exactly as it was written in Phase 15.6.** Not one character of `DCD-02` was edited, in either channel, which `git diff` over this plan's three commits confirms.

### 5. Two `.md` files in `docs/` are untracked and were left alone

- **Found during:** every `git status` in this plan.
- **Disposition:** `docs/CCF_SDK_DE_REQUIREMENTS.md` and `docs/Context_Product_Specification_Standard_v0-3.md` were untracked before plan `21-02` and are untracked still. **Pre-existing, reported, not touched** — same disposition as plan `21-02`, and for the same reason: they are outside this plan's `files_modified` and outside the audit's subject.

## Verification

| Check | Result |
|---|---|
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **exit 0** — 35 passed |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` (with the ledger module) | **exit 0** — 68 passed |
| `python -m tools.lints --citations` | **exit 0**, 0 findings |
| `make lint` | **exit 0** |
| `make typecheck` | **exit 0** — 211 source files |
| `make test` | **exit 0** — **4105 passed / 118 skipped**, 10m33s — identical to the wave-1 and wave-2 baselines |
| `make gate-tools` | **exit 0** — leg 1 **406**, leg 2 **189**; both unmoved, which is the mechanical proof no test was added |
| `refuse_unresolvable(ledger_text())` | **`[]`** over **70** citation tokens in status cells |
| `channel_disagreements` / `vocabulary_offenders` / `doubled_verdicts` | **`[]`**, **`[]`**, **`[]`** |
| frozen roster at the pinned base | **54** rows, all 54 still present in the table |
| roster rows carrying a non-`Pending` verdict | **36 of 54** |
| roster rows still `Pending` | **18** — every one a `DOCS-0x`/`DOCS-1x`/`DOCS-2x` row of the Phase 16 lane, which is plan `21-04`'s |
| the ten `RECON-` rows | untouched, still `Pending` in both channels |
| every anchored line citation, via the shipped `_anchor_verdict` | **`True`** on all 14 occurrences — never `None` |
| sabotage: `D-IMPL-70` re-aimed at `docs/DECISIONS.md:213` | **`cite02-anchor` RED**, restored from backup, lint back to exit 0 |
| `git diff --stat <base>..HEAD -- src/ runtime/ examples/ public/ pyproject.toml` | empty |
| `git diff --stat <base>..HEAD -- tests/` | empty |
| `git diff --name-only <base>..HEAD -- tools/` | only `tools/docs_tests/test_requirement_ledger.py` (plan `21-01`'s) |
| `git diff --stat <base>..HEAD -- tools/lints/citations.py` | empty |
| `git diff --name-only` over this plan's three task commits | exactly two paths |
| `git status --porcelain` after the final commit | only the two pre-existing untracked `docs/` files |

`make ci-core` is `lint typecheck test gate-tools`. Each leg was run individually rather than as one command, because a full pipeline cannot complete inside this harness's foreground call budget and `make test` alone took 10m33s.

## What plans `21-04`..`21-07` inherit

- **Route 2 is now proven, and proven the hard way.** An anchored line citation into `docs/DECISIONS.md` is fully checkable when — and only when — the anchor is a `D-IMPL-NN`-shaped token that literally appears in the cited lines. Fourteen such citations now ship, each verified `True` against `_anchor_verdict` and one watched going red. Plan `21-04`'s Phase 16 lane will need this: much of what it must cite is rulings.
- **The documentation lane was not the citation problem it was forecast to be.** Phase 14 shipped a gate per claim, and gates are Python. `21-04` should look for the gate first and reach for route 2 second, in that order.
- **A second work-list entry**, `EXAM-02`, in the form plan `21-05` needs it — with its coupling to `CLNT-17` stated, since the two cannot be sequenced independently.
- **Two named gaps for `21-05` that are not `Not built` rows:** `DOCS-06`'s unwired-CI-wiring hole, and `DOCS-03`'s six uncovered artifact classes.
- **A warning about counting.** `DOCS-03`'s first measurement was wrong by a factor of four because it read page sources instead of rendered pages. Any figure this phase takes over `public/` has to resolve snippet includes first.

## Threat Flags

None. This plan reads tracked repository files and writes markdown. No credential, no network call, no external input, no package installed — `T-21-SC` stays true by the `pyproject.toml` emptiness assertion inside `FENCE`. `T-21-10` (closing a gap discovered mid-audit) was live at `EXAM-02`, `DOCS-03` and `DOCS-06`, and the empty fence over `src/ runtime/ examples/ public/ tests/` is what proves none of the three was closed. `T-21-14` (a qualifying clause exempting its own evidence) was checked by grepping all six `HISTORICITY_MARKERS` phrases out of every added line: **zero**. `T-21-15` (a silently-skipped anchor) was closed by running `_anchor_verdict` before writing, not after. `T-21-16` (judging a re-homed row against a subject that moved) was live on all three `EXAM` rows and each cell names its target.

## Known Stubs

None.

## Self-Check: PASSED

All three files this plan created or modified exist on disk. All four commits
`16b6fe2`, `1b81927`, `73bc457` and `1ab2cab` resolve in this repository.
Re-verified after the last write: the ledger module is 35 passed, the sweep
module and the ledger module together are 68 passed, `--citations` is exit 0,
`make gate-tools` is exit 0 at 406 + 189, `make test` is exit 0 at 4105 passed
/ 118 skipped, and the pinned-base diff over `src/ runtime/ examples/ public/
tests/ pyproject.toml tools/lints/citations.py` is empty.

Three claims in this document were checked rather than asserted, because all
three read plausibly and could have been wrong.

- **`_anchor_verdict` returns `True` and not `None`** for every anchored line
  citation written here — run against the shipped function, all 14 occurrences,
  before the commits. A `None` verdict is an unchecked citation that looks
  checked, and `D-17` is explicitly not a licence for one.
- **`DOCS-03`'s coverage figure** was taken twice. The page-source count is 5
  of 27 and is wrong; the rendered count with `--8<--` includes resolved is 21
  of 27, and that is what the cell carries and says it carries.
- **`DCD-02`'s qualifying clause is still true of the tree.**
  `examples/s1-01-hello-context-product/deployment.py::KycScenario`'s
  `debt_evidence` was read at execution time: `del view` then
  `return NO_DEBT_EVIDENCE`, unconditional, which is `D-IMPL-119` limb 3(b)'s
  omission path. The row was confirmed, not rewritten, and not one character
  of it changed.
