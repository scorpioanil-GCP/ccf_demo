---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 08
subsystem: examples-retirement
tags: [retirement, gates, floors, d-27, d-26, d-25, d-31]
status: blocked-at-task-3
requires:
  - "17-01 (regenerated retirement inventory)"
  - "17-07 (client conformance suite)"
provides:
  - "The measured removal inventory for examples/s1-00-* and examples/s1-01-*"
  - "A measured, reproducible refutation of this plan's removal scope"
affects:
  - "17-09 (the replacement example; now a hard predecessor rather than a successor)"
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - .planning/phases/17-client-access-ccf-client-and-the-transport-agnostic-first-ex/17-08-SUMMARY.md
  modified:
    - Makefile
decisions:
  - "Task 3 is disputed on a measurement, not executed: removing examples/s1-01-* deletes the only shipped examples/ call site of refuse_request, and tools/docs_tests/test_resolver_seam_obligations.py goes red with no honest repair available inside this plan"
  - "Task 2 is held with Task 3: retiring the two shape gates while the trees they guard still ship is an uncompensated coverage loss, not a retirement"
metrics:
  tasks_completed: "1 of 3 (Task 1 complete; Tasks 2-3 disputed; Task 4 returned as checkpoint)"
  commits: 2
---

# Phase 17 Plan 08: Retire the Condemned Section-1 Example Trees — Summary

**One-liner:** The removal inventory was derived from the tree and the removal
was then measured before being executed — it breaks four more test modules than
the plan accounts for and leaves one SDK adopter obligation with no shipped
worked example, so Task 3 is disputed rather than landed.

## Status

| Task | Disposition |
|---|---|
| 1 — Re-derive the removal inventory, classify every reference | **Complete.** No tree change, as the task requires. |
| 2 — Retire the two shape gates, lower the three floors | **Held.** Coupled to Task 3; see *Why Task 2 is held with Task 3*. |
| 3 — Remove the trees and everything that named them | **Disputed on a measurement.** See *The blocker*. One uncoupled sub-item of this task (the stale `Makefile` comment) was executed and committed. |
| 4 — Dave rules on the `00`–`08` half of D-27 | **Returned as a blocking checkpoint**, undecided, with all three figures re-measured. |

Every measurement below was taken **inside the worktree**
`/home/parkave/ccf_code/.claude/worktrees/agent-a6bf426bc84a15635` at base
`e270a01`. Per `DEF-17-04`, a tree-walking gate measured in a worktree is not
evidence about the branch; the counts here are worktree-local. They are
reproducible on the branch because the worktree is a clean checkout of
`e270a01` plus this plan's two commits.

---

## The blocker — why Task 3 was not executed

**Deleting `examples/s1-01-hello-context-product` removes the last shipped
`examples/` call site of `ccf.products.request::refuse_request`, and a standing
gate asserts that call site exists.**

`tools/docs_tests/test_resolver_seam_obligations.py::test_the_seam_cites_a_shipped_example_that_exists`
reads the docstrings of `ccf_runtime.mcp.egress::ProductResolverProtocol` and
`ccf_runtime.mcp.experience::ExperienceProductResolverProtocol`, extracts every
`examples/….py::Symbol` citation, and asserts each resolves on disk. Both
docstrings cite
`examples/s1-01-hello-context-product/spine.py::assemble_and_serve` as the
worked example for the request refusal. A sibling test,
`test_both_seams_cite_both_call_sites`, requires **two distinct** example paths
per seam — one per refusal — so dropping the citation is not a repair either.

This is not a reading. It was measured by performing the deletion in the
worktree, running the gate, and restoring:

```
rm -rf examples/s1-00-companies-over-revenue examples/s1-01-hello-context-product
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
    tools/docs_tests/test_resolver_seam_obligations.py -q
-> EXIT=1
FAILED …::test_the_seam_cites_a_shipped_example_that_exists[…egress.ProductResolverProtocol]
FAILED …::test_the_seam_cites_a_shipped_example_that_exists[…experience.ExperienceProductResolverProtocol]
AssertionError: … cites example paths that are not on disk:
    ['examples/s1-01-hello-context-product/spine.py']
2 failed, 13 passed
```

**There is no honest repair inside this plan's budget.** The candidates, each
checked against the tree:

| Candidate repair | Measured verdict |
|---|---|
| Repoint the citation at another shipped example that calls `refuse_request` | `command grep -rn "refuse_request" examples/ --include=*.py` returns hits in **only** `s1-00/produce.py`, `s1-01/spine.py` and a comment in `s1-00/consume.py`. Both live in the trees being deleted. No survivor. |
| Wire `refuse_request` into `examples/04-cross-process/producer_child.py::resolve` (which already calls `refuse_bound_payload`) | `resolve` hand-rolls the address comparison at its `request is not None` branch instead of calling `refuse_request`. Calling it properly needs the example's class to declare a `ProductRequestContract`; `command grep -rn "request_contract" examples/04-cross-process/` returns nothing. This is new example work with a new Control Plane artifact — plan 17-09's scope, not a deletion plan's. |
| Cite the client conformance suite instead | `EXAMPLE_PREFIX = "examples/"` in the gate, deliberately: *"a citation of a `src/` symbol is not a worked example — the point is that the adopter can read a shipped, CI-run deployment doing the thing."* A `tests/` path is rejected by design. |
| Relax `test_both_seams_cite_both_call_sites` from `>= 2` to `>= 1` | This deletes the property *"each of the two refusals has a shipped demonstration"*. That is a verification regression of exactly the class this phase has produced nine times. Not taken without a ruling. |

**The plans ran out of order.** `examples/hw1-companies-over-revenue` — s1-00's
replacement, which plan 17-09 creates and which inherits `produce.py`'s
`refuse_request` call — is not in the tree (`ls examples/` confirms: no `hw1-*`).
Plan 17-08's own Task 3 text sets the precedent for this response: *"If it did
not, **stop and dispute** — the plans ran out of order and the property would be
unasserted."* It applies that instruction to 17-07's two-thresholds property
(which **did** land — `tests/client/conformance/suite.py` exists and is green).
The same instruction applies here to 17-09's replacement example, which did not.

### The removal is also materially larger than the plan states

With both trees removed, the following go red **beyond** the three test modules
the plan deletes and the two shape gates it retires. None of these are named in
the plan's `<action>` text, and four of them are not in its `files_modified`
either:

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tests/products/test_gate_two_call_shape.py tests/examples tests/deployment \
  tests/products/test_request_contract.py tests/replay/test_engine_rehydration.py \
  tests/halflife/test_debt.py -q
-> 31 failed, 784 passed, 43 skipped, 17 errors
```

| Module | What breaks | In the plan's `files_modified`? |
|---|---|---|
| `tests/products/test_gate_two_call_shape.py` | **Seven tests beyond the three floors** use `examples/s1-00-companies-over-revenue/produce.py` as a *fixture subject*, not as a counted witness: `test_the_premise_detector_reads_the_shipped_tree_correctly`, `test_hw1_claims_the_exemption_for_the_stated_reason`, `test_an_exempt_body_that_calls_the_binder_is_still_refused`, `test_a_second_operator_set_outside_the_control_plane_is_refused`, plus the three non-vacuity preconditions `test_the_gate_scan_is_not_vacuous`, `test_the_binder_scan_is_not_vacuous`, `test_the_binder_argument_scan_is_not_vacuous`. The plan says only *"lower three floors."* | yes, but the action text covers only the floors |
| `tests/products/test_request_contract.py` | Two tests read `examples/s1-01-hello-context-product/artifacts/request-contract.yaml` **from disk** and assert `from_declared` equals the hand-build. The artifact is the fixture; there is no replacement. | listed; no disposition stated |
| `tests/replay/test_engine_rehydration.py` | `test_no_source_identity_reaches_the_delivered_product` reads s1-01's `source-estate.yaml`. | listed; no disposition stated |
| `tests/examples/test_source_estate.py` | Five tests/errors — `EXAMPLE_DIR = REPO_ROOT / "examples" / "s1-01-hello-context-product"` is a live path. | listed as conditional; the condition resolves to **delete** |
| `tools/docs_tests/test_resolver_seam_obligations.py` | The blocker above. | listed — but only for its `:328` negative-control **string literal**, which is test data and needs no change |

So the removal re-homes the fixtures of four test modules that assert **SDK**
properties (request-contract-from-declared equality, source-identity
non-leakage, the one-document exemption, the premise detector) onto artifacts
that will not exist. Those properties have no replacement fixture until 17-09
ships the new example.

---

## Task 1 — the removal inventory, derived from the tree

### The sweep is current

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
-> 230 coupling rows across 71 files (143 rows outside the three swept trees);
   1697 files scanned
git status --porcelain -> (empty)
```

The regenerated report is byte-identical to plan 17-01's committed one, so the
inventory D-31 requires be repaired first is in fact current. `git status` was
clean at the end of Task 1, as its acceptance criteria demand.

### Classification of every referencing file

`command grep -rl "s1-00\|s1-01\|s1_00\|s1_01" --exclude-dir=__pycache__ --exclude-dir=.git .`
returns **163 files**. Of those, **94** are under `.planning/`, which the sweep
excludes as *"the phase's own planning tree — not shipped, not published"* and
which is append-only history; **4** are build artifacts (`.pytest_cache/`,
`site/`), also excluded. The remaining **65** are classified below.

**One of those build artifacts is not inert, and it refutes a claim this plan
makes.** `site/reference/protocols/runtime-surfaces/index.html` carries
`examples/s1-01-hello-context-product/spine.py` — it is the mkdocstrings
rendering of the two resolver Protocol docstrings. So the plan's
*"`command grep -rn "s1-0" public/` → nothing. The `s1-*` trees have **zero**
published exposure"* is true of the `public/` **source** and false of the
**built site**: the citation reaches a published API reference page by way of
the docstring. It is not a snippet include and `docs-strict` does not check it
(`tools/docs_tests/test_no_stale_example_paths.py` scans `public/`, by design),
so it fails silently rather than loudly — but a reader of the published
reference would be sent to a path that no longer exists. This is a second,
independent reason the docstring citations are class (a) and not class (c).

Legend: **(a)** live filesystem path into `examples/s1-*` · **(b)** test-owned
fixture copy · **(c)** docstring/prose reference.

#### Class (a) — live paths. These force a change.

| File | Reference | Disposition |
|---|---|---|
| `Makefile` (`example-s1-01` recipe) | runs `examples/s1-01-hello-context-product/run.py` | delete target + `.PHONY` entry |
| `Makefile` (`example-s1-00` recipe) | runs `examples/s1-00-companies-over-revenue/consume.py` | delete target + `.PHONY` entry |
| `tests/examples/test_s1_00_output.py` | builds `examples/s1-00-companies-over-revenue` | delete module |
| `tests/examples/test_s1_01_output.py` | builds `examples/s1-01-hello-context-product` | delete module |
| `tests/examples/test_s1_00_config_equivalence.py` | reads s1-00's `artifacts/config/*.yaml` | delete module |
| `tests/examples/test_source_estate.py` | `EXAMPLE_DIR = REPO_ROOT / "examples" / "s1-01-hello-context-product"` | **delete module** — the plan left this conditional; the condition resolves to live |
| `tests/examples/test_spine_separation.py` | `SECTION_ONE_GLOB = "s1-*"`, `_copied_example` | retire (D-26) |
| `tests/examples/test_section_one_is_agent_free.py` | `SECTION_ONE_GLOB = "s1-*/**/*.py"` | retire (D-26) |
| `tests/products/test_gate_two_call_shape.py` | three floors **plus seven fixture-subject tests** on `s1-00/produce.py` | floors re-counted; the seven tests need a new subject |
| `tests/products/test_request_contract.py` | reads s1-01's `request-contract.yaml` from disk | needs a replacement fixture |
| `tests/replay/test_engine_rehydration.py` | reads s1-01's `source-estate.yaml` from disk | needs a replacement fixture |
| `runtime/ccf_runtime/mcp/egress.py` | docstring citation **asserted to resolve on disk** by a gate | **reclassified from (c) to (a)** — see the sweep hole below |
| `runtime/ccf_runtime/mcp/experience.py` | same | same |

#### Class (b) — test-owned fixture copies. Unaffected; measured, not assumed.

| File | Evidence |
|---|---|
| `tests/deployment/fixtures/s1-00-multifile/` | a real directory of nine documents, not a symlink; `find` shows regular files |
| `tests/examples/fixtures/s1_00_ccf_config.yaml` | hand-authored fixture in `tests/`, names s1-00 only in a comment |
| `tests/deployment/test_config_document.py` | **all pass** with the trees removed |
| `tests/deployment/test_config_derivation.py` | **all pass** with the trees removed |
| `tests/deployment/test_config_equivalence.py` | **all pass** with the trees removed; its `s1-00-…` strings are tenant/driver *names*, not paths |

The plan asked for this classification to be *established by reading*. It was
established by reading **and** by deleting the trees and observing
`tests/deployment` stay green — the stronger evidence.

#### Class (c) — prose. Update so no reader is sent to a deleted path.

`src/ccf/products/bind.py`, `src/ccf/products/request.py` (two sites),
`src/ccf/deployment/config.py`, `tests/halflife/test_debt.py`,
`tests/products/test_resolver_seam.py`, `tests/client/conformance/suite.py`
(two sites), `tests/client/conformance/test_the_suite_fires.py`,
`tests/deployment/fixtures/s1-00-multifile/README.md`,
`docs/surface/examples/FIBO-EXTENSION.md`,
`tools/docs_tests/test_resolver_seam_obligations.py` (a **string literal** in a
negative control — needs no change; it asserts that a *line-anchored* citation
is not accepted, and the string never touches the filesystem).

Append-only records that name s1 as history and are **not** to be rewritten
(`EXCLUDED_FROM_ASSIGNMENT`): `docs/DECISIONS.md`, `docs/SURFACE-CHANGES.md`,
`docs/surface-changes/*` (11 files), `docs/PHASE_15_5_GATE.md`,
`docs/CONTEXT_PRODUCT_REVISION.md`, `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md`,
`docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md`, `docs/superpowers/**` (4 files),
`tools/retirement_sweep.py` (its own schedule, by design).

### Sweep coverage holes

Reconciling the grep against the report found **17** files the sweep does not
carry. Eleven are `examples/s1-*/…` self-references, which the sweep excludes
by construction (a file inside a retiring tree naming its own tree), and one is
the report itself. The remaining five are real, in three classes:

| Hole | Files | Why the sweep misses it | Recommendation |
|---|---|---|---|
| **1. Bare short name.** The sweep matches full retiring paths (`examples/s1-00-companies-over-revenue`); a reference spelled `s1-00` or `s1-01` alone is invisible to it. | `tests/products/test_resolver_seam.py`, `docs/superpowers/specs/2026-08-15-ccf-client-design.md`, `docs/surface-changes/16-23-mcp-product-tool.md` | matcher is full-path only | Teach the sweep the trailing path segment as a secondary, lower-confidence match, reported in its own column so it cannot be confused with a path coupling. Prose that says `s1-01` still sends a reader somewhere that will not exist. |
| **2. Line-wrapped path.** `src/ccf/deployment/config.py` wraps `examples/s1-00-companies-over-revenue/artifacts/config` / `/policy-bundle.yaml` across two comment lines. | `src/ccf/deployment/config.py` | the sweep reads line by line | `tools/docs_tests/test_no_stale_example_paths.py` already solved this for published prose by joining paragraphs before matching (`test_a_path_reference_split_across_lines_is_still_read_as_one_paragraph`). Reuse that reading rather than writing a second one. |
| **3. Documentary-vs-live misclassification.** | `runtime/ccf_runtime/mcp/egress.py`, `runtime/ccf_runtime/mcp/experience.py` | the sweep classifies a docstring citation as `documentary` | **This is the hole that hid the blocker.** A docstring citation that a gate asserts resolves on disk is **live**. The sweep should mark a `docstring` hit as live when the path is also reachable by an existence-checking gate — minimally, by treating `path::Symbol` citations inside a Protocol docstring as live, since `test_resolver_seam_obligations.py` exists precisely to check them. |

### A fourth hole, in the schedule rather than the scan

`tools/retirement_sweep.py`'s `RETIREMENT_SCHEDULE` comment states: *"Each path
was confirmed to exist before being listed — … a schedule naming a path that is
not there is the same class of defect as one that omits a path."* **Nothing
enforces that.** Measured: with both trees deleted, the sweep exits 0 and
re-renders happily —

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
-> 228 coupling rows across 69 files … ; 1660 files scanned      EXIT=0
```

After the removal lands, the schedule's five `17-08` entries become claims
nothing checks. Recommendation: add a precondition asserting every
`RETIREMENT_SCHEDULE` path either exists on disk or carries an explicit
`retired` marker recording the commit that removed it.

---

## Zero-match behaviour of every gate this plan touches

The standing question — *what does this gate do when it matches nothing?* —
answered by measurement, not by reading:

| Gate | On zero match | Evidence |
|---|---|---|
| `tests/examples/test_spine_separation.py` | **RED**, 13 failures | its `test_the_section_one_tree_is_populated` precondition and `_copied_example`'s `split_examples(...)[0]` both fail hard |
| `tests/examples/test_section_one_is_agent_free.py` | **RED**, 5 failures | same populated-precondition posture |
| `MINIMUM_GATE_CALL_SITES` / `MINIMUM_PROJECTING_BODIES` / `MINIMUM_RESOLVED_BINDER_SITES` | **RED** | floors; observed count drops below the constant |
| `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS` | **passes at zero, by design** | it is a *ceiling*; removal takes the count to 0 and the ceiling still holds. This is the one gate here that goes quiet, and it is intended — 17-09's example claims the slot back. Stated because the plan is right to leave it at 1 and a reader should know why that is not an oversight. |
| `tools/docs_tests/test_resolver_seam_obligations.py` | **RED** | measured above |
| `tools/docs_tests/test_no_stale_example_paths.py` | **unaffected** | it scans `public/`, and `command grep -rn "s1-0" public/` returns **0**; it carries its own populated precondition (`test_the_published_tree_is_populated`) |
| `tools/retirement_sweep.py` schedule | **quiet** | measured above — the fourth hole |
| `tests/products/test_required_operators_guard.py::MINIMUM_IMPLEMENTATIONS` | **stays green, correctly** | floor 9 with 13 witnesses; s1-00 and s1-01 contribute 1 each, leaving 11 ≥ 9. **The plan does not mention this file at all**; it needs no change, but that had to be established rather than assumed. |

### Correction to the plan's and the brief's claim about `test_spine_separation.py`

Both say it goes **blind, not red**. Measured, the truth is scenario-dependent
and both halves matter:

- Against a **removed** `s1-*` tree it goes **RED** (13 failures), because its
  populated precondition and its negative-control fixture builder both index
  `split_examples(EXAMPLES_ROOT)[0]`.
- Against a **new Phase 17 example** it goes **blind**, because
  `SECTION_ONE_GLOB = "s1-*"` simply does not match a differently-named
  directory — the module passes while scanning nothing relevant.

So it is *retired*, not *silently inapplicable*: on the removal path it fails
loudly and must be dealt with, which is what D-26 anticipated.

---

## Post-removal floor counts, measured

Counted by running the module's own scan functions against the tree with both
trees removed — **not** by subtracting from the plan's table, which is wrong in
one row (it says `MINIMUM_GATE_CALL_SITES` has 11 witnesses and no headroom; the
sweep and the scan both say **12** witnesses, headroom 1).

```
PYTHONPATH=.:src:runtime .venv/bin/python -c "<load test_gate_two_call_shape as a module>; \
  print(len(m._gate_scopes()), len(m._projecting_scopes()), len(m._resolved_binder_sites()))"
```

| Constant | Current | Observed post-removal | Witnesses removed |
|---|---:|---:|---|
| `MINIMUM_GATE_CALL_SITES` | 11 | **10** | `s1-00/produce.py`, `s1-01/spine.py` |
| `MINIMUM_PROJECTING_BODIES` | 13 | **11** | the same two |
| `MINIMUM_RESOLVED_BINDER_SITES` | 12 | **11** | `s1-01/spine.py` only — s1-00 contributes **zero**, confirming the plan's note that it is the one-document exemption |
| `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS` | 1 | 1 (unchanged) | ceiling, not floor — leave alone |

**These numbers were not applied.** A floor must be lowered *in the same commit
as the removal that justifies it* (`FLOOR_REMOVAL_INSTRUCTION`), and the removal
did not land. Lowering them now would create headroom against witnesses that
still exist — a gate weakened with nothing to show for it. They are recorded
here so whoever executes the removal counts from a measurement rather than from
this plan's arithmetic.

---

## Why Task 2 is held with Task 3

Task 2 reads as independent of the removal. It is not.

Retiring `tests/examples/test_section_one_is_agent_free.py` while
`examples/s1-00-*` and `examples/s1-01-*` **still ship** deletes a live
assertion over shipped code with nothing standing in its place: the purity gate
that D-25 names as the property's new home arrives with plan 17-09, and
`command grep -rln "purity" tests/ tools/ --include=*.py` finds no such gate in
the tree today. That is *"a coverage loss disguised as a retirement"* — the
exact thing Task 2's own action text forbids. Once the trees are gone the loss
is moot, because there is nothing left for the gate to be about.

The same holds for `test_spine_separation.py`'s P5/P6 (the producer/consumer
print split), whose stated new homes are the purity gate (17-09) and the codec
seam (17-04). 17-04 landed; 17-09 did not.

### Property accounting for both retired modules — prepared, for when they retire

Recorded now so the retirement, whenever it lands, is a decision about each
property rather than a bulk delete.

**`tests/examples/test_spine_separation.py`** — 17 test functions, 38 collected
cases, all green at `e270a01`.

| Property | New home |
|---|---|
| P1/P4 — exactly one module carries the seven canonical `--8<--` regions | **Nowhere, deliberately.** The file-shape aspect of `D-IMPL-127` and `D-IMPL-131` are suspended by D-25. |
| P2 — the spine opens the seven regions in the canonical order | **Nowhere, deliberately.** Same suspension; the seven-name vocabulary is `D-11`'s and `D-11` is suspended. |
| P3 — every region opened anywhere is closed, never interleaved | **Partially, `tools/docs_tests/test_snippet_gate.py::test_a_deleted_section_marker_fails_the_strict_build`.** That gate catches the *consequence* (a published page whose marker is gone fails the strict build) rather than the marker syntax itself. Stated as a partial rather than claimed as equivalent. |
| P5 — the region-carrying module is silent | **The purity gate (17-09).** Not in the tree yet — this is the coupling that holds Task 2. |
| P6 — exactly one fabric-facing module prints | **The purity gate (17-09)** and the codec seam (17-04, landed). Same caveat. |
| The eight negative controls + two non-vacuity preconditions + the CWD-independence control | Machinery for the above; they retire with the properties they guard. |
| `test_the_fabric_facing_scope_admits_and_excludes_on_the_import` | Asserts (deliberately does not skip) that `<example>/scenario/provision.py` exists. Dies with s1-00. No successor needed: it controls a convention that the suspended shape introduced. |

**`tests/examples/test_section_one_is_agent_free.py`** — 6 test functions, 5
collected non-trivially.

| Property | New home |
|---|---|
| No Section-1 module imports an agent surface (`ccf.agents`, `ccf.skills`, `ccf_runtime.adapters`) | **The purity gate (17-09).** Until it lands this is the only assertion of the property, which is why the module cannot retire ahead of the trees. |
| The deny list documents every entry (the reason-column posture) | Cited as precedent by `tests/invariants/test_no_obligation_vocabulary.py`, which carries the same shape independently — the *pattern* survives even though this instance does not. |
| The injected-import and prose-ignoring controls | Machinery; retire with the property. |

---

## What was executed and committed

### `docs(17-08): the examples surface audit gate has not existed since 16-01` — `107081b`

The one sub-item of Task 3 that is genuinely uncoupled from the removal.

The plan said to fix a stale reference to `tests/examples/test_surface_audit.py`
at `Makefile:351-352`. **Both halves of that were wrong and the tree won:**

- The reference is at `Makefile:458`, not 351-352 — 351-352 is
  `example-03-live-anthropic`. The line numbers had moved; the defect had not.
  This is the same failure mode `D-IMPL-144` (`docs/DECISIONS.md`) rules on for
  decision citations, arriving on a `Makefile` comment.
- The plan calls it *"a stale comment, not a live coupling."* Correct that it is
  not a live coupling; wrong about the history. `git log --all --diff-filter=D`
  shows the module **did** ship (plan 15-03) and **was** deleted in `2c52b5f`
  (plan 16-01) without the comment being updated. My first draft of the fix
  asserted git recorded no deletion; I checked before committing and it was
  false. Recorded here because an unverified claim in a comment is how this one
  survived two phases.

The comment now states that there is no standing audit assertion over the
examples surface measurement, names the commit that removed it, and names what
does still gate that tree (`tools/docs_tests/test_retirement_sweep.py`, which
asserts coupling ownership, not line counts).

Fixed in the same commit: the adjacent comment advised
`python tools/measure_examples.py --baseline`. There is no bare `python` on
PATH, so a reader copy-pasting it gets a non-zero exit and no measurement —
the same defect class `D-IMPL-143` (`docs/DECISIONS.md`) closed in CI today.
Now spelled `$(PYTHON)`.

`.github/workflows/ci.yml` was **not touched.** Its seven pytest steps call
Makefile targets under `D-IMPL-143` and no `s1-*` example target appears in any
job, so this plan's CI edit was unnecessary as well as hazardous.

---

## Verification

All exit codes captured directly, never through a pipe (`make … | tail` reports
tail's status).

| Command | Result |
|---|---|
| `make PYTHON=.venv/bin/python gate-tools` | **exit 0** — 400 passed, then 144 passed. Identical to the stated baseline. |
| `PYTHONPATH=.:src:runtime .venv/bin/python -m tools.lints --all` | **exit 0** |
| `make PYTHON=.venv/bin/python docs-strict` | **exit 0** — mkdocs strict build plus `tools/publish_scan.py site` |
| `make PYTHON=.venv/bin/python ci-quick-suite` | see *Quick suite* below |
| `git status --porcelain` after restoring the measurement deletions | **empty** |

### Quick suite

```
make PYTHON=.venv/bin/python ci-quick-suite   (exit captured, not piped)
-> EXIT=0
3695 passed, 2 skipped, 172 deselected, 105 warnings in 379.11s (0:06:19)
```

Identical to the stated main-checkout baseline: 3695 passed / 2 skipped / 172
deselected. **Delta: zero, and zero is the correct answer here** — this plan
deleted no tests. The baseline warns that a deletion plan's counts *will* drop
and that the drop must be accounted for against what was removed; nothing was
removed, so a drop would have been the anomaly.

**Delta accounting.** This plan deletes **no** tests, so no delta is expected
and none is claimed. The one landed change is a `Makefile` comment. Had Task 3
landed, the deletions would have been: `test_s1_00_output.py` (9 tests),
`test_s1_01_output.py`, `test_s1_00_config_equivalence.py`,
`test_source_estate.py` (5), `test_spine_separation.py` (38 collected) and
`test_section_one_is_agent_free.py` (5+) — plus 31 failures and 17 errors in
modules the plan does not account for, which is the substance of the dispute.

### Substrate legs

Not run. Both legs select the modules this plan would have deleted
(`test_s1_00_output.py` is `pytest.mark.postgres`, `test_s1_01_output.py` is
`pytest.mark.fluree`), and since no deletion landed, the legs' collection sets
are unchanged from `e270a01`. The zero-collection question the plan rightly
raises is a question **for the removal**, and is recorded as an obligation on
whoever executes it: `make leg-fluree` after the removal must be checked for
zero collection, because a leg that silently collects nothing is the same
vacuity defect the floors exist to prevent.

---

## Deviations from Plan

**1. [Rule 4 — architectural/sequencing] Task 3 disputed rather than executed.**
- **Found during:** Task 1's classification, confirmed by measurement before Task 3.
- **Issue:** the removal deletes the last shipped worked example of an SDK adopter obligation, and breaks four test modules the plan does not account for.
- **Action:** not executed; returned to the orchestrator with the measurement and three options.
- **Files modified:** none.

**2. [Rule 4 — coupling] Task 2 held with Task 3.**
- **Issue:** retiring the agent-free and shape gates while the trees they guard still ship is an uncompensated coverage loss; the replacement purity gate is 17-09's and is not in the tree.
- **Action:** property accounting prepared and recorded; deletion not performed.

**3. [Rule 1 — bug] The stale `Makefile` comment fixed, with its history corrected.**
- **Found during:** Task 3's uncoupled sub-item.
- **Issue:** a comment pointed a reader at a gate deleted in `2c52b5f`; an adjacent comment advised a `python` spelling that cannot run.
- **Fix:** both corrected, with the removing commit named.
- **Commit:** `107081b`.

**4. [Rule 2 — missing measurement] Four sweep coverage holes recorded.**
- Bare short names, line-wrapped paths, docstring-citations-that-a-gate-checks misclassified as documentary, and an unenforced schedule-path-existence claim. Each carries a recommendation above. None fixed here: `tools/retirement_sweep.py` is D-31's machinery, repaired by 17-01, and changing it now would invalidate the inventory this plan is measured against.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema at a
trust boundary was introduced; the only landed change is a `Makefile` comment.

## Known Stubs

None.
