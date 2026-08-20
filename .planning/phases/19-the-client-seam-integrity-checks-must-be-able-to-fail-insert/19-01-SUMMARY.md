---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
plan: 01
subsystem: client-seam / product doors / wire shapes
tags: [wire-shape, door, mcp-egress, integrity-check, C-01, C-02, C-04, C-06, C-15, C-16, C-18]
requires:
  - "ccf.products.door (DoorOutcome, served_answer, door_refusal, PRODUCT_REQUEST_TOOL)"
  - "ccf.contracts.canonical.canonical_bytes"
  - "ccf_runtime.mcp.egress.build_egress_server"
provides:
  - "ccf.products.door.WireRequest (moved here from ccf.client.wire)"
  - "ccf.products.door.DoorOutcome — the ONE outcome shape, five members, five validator rules"
  - "ccf.products.door.door_question — parse the caller's encoded question"
  - "ccf.products.door.door_answer — the one emission site for the shape"
  - "ccf.client.wire.WireOutcome — an alias of DoorOutcome"
  - "PRODUCT_REQUEST_TOOL's required `request` argument and the three-axis address cross-check"
affects:
  - "19-02 (the seam retype can now be one commit)"
  - "19-06 (the HTTP echo header reconciles against this shape)"
  - "19-07 (corrective prose; the B0 sentences are preserved for amendment)"
  - "19-08 (the D-IMPL entry, incl. the declared as_of=None residual)"
tech-stack:
  added: []
  patterns:
    - "one shape defined producer-side, re-exported client-side under an alias"
    - "serialize once, claim sha256 of those same bytes"
    - "refuse a call that asks two things, by name, on every axis with a second source"
    - "name the residual where the check is impossible; do not reconstruct an operand"
key-files:
  created:
    - "tests/products/test_door_answer.py"
    - "docs/surface-changes/19-01-one-outcome-shape-and-the-encoded-question.md"
  modified:
    - "src/ccf/products/door.py"
    - "src/ccf/client/wire.py"
    - "runtime/ccf_runtime/mcp/egress.py"
    - "src/ccf/client/adapters/mcp_stdio.py"
    - "tests/mcp/test_egress_parameters.py"
    - "tests/mcp/test_egress_refusal_envelope.py"
    - "tests/crossproc/test_mcp_egress.py"
    - "tests/client/test_mcp_stdio_adapter.py"
    - "docs/SURFACE-CHANGES.md"
    - "docs/surface/examples/RETIREMENT-COUPLINGS.md"
decisions:
  - "The merged DoorOutcome validator carries FIVE rules, not four — counted, and rule 4 (a refused outcome carrying a content address) had no coverage anywhere in the tree before this plan"
  - "The MCP door's three cross-checks live in egress.py, not door.py, because the double source exists only where asked_at is a separate transport argument"
  - "The as_of=None temporal residual is left true and visible rather than closed with a reconstruction"
metrics:
  duration: "~3h"
  tasks: 3
  commits: 7
  collected_delta: "4027 -> 4051 (+24)"
  completed: 2026-08-19
---

# Phase 19 Plan 01: One Outcome Shape, and a Door That States What It Was Asked — Summary

Collapsed `DoorOutcome` and `WireOutcome` into one class carrying the question
the door parsed and a content address the producer computed, and made the MCP
product tool refuse a call that encodes one question while addressing another —
so the client seam's two integrity checks finally have an operand that did not
come from the client.

## What Was Built

**One shape.** `ccf.products.door.DoorOutcome` now has exactly five members —
`request`, `product_json`, `content_address`, `replay_ref`, `refusal` — and
`ccf.client.wire.WireOutcome` is an **alias** of it, not a subclass. `WireRequest`
and `_unstable_parameter` moved to `door.py` verbatim, because the door has to
name the type it echoes and a producer-side shape module cannot import the client
package without reversing the layering `door.py`'s own module docstring
establishes. `ccf.client.wire.__all__` is unchanged, so every published import
path still resolves.

**Two new producer-side entries.** `door_question(asked_json) -> WireRequest`
parses the caller's encoded question — the parameter is **text**, because a door
handed an already-constructed object would be echoing the caller's own copy back
to the caller. `door_answer(resolved, *, echo, resolved_request, product_class,
version) -> bytes` is the one emission site: it serializes the vessel exactly
once and derives `content_address` from those same bytes.

**The MCP door states what it was asked.** `PRODUCT_REQUEST_TOOL` gained
`request` as a **required** argument with no deprecation window, and the handler
refuses a disagreement by name on every axis where a second copy of the fact
exists: `product_class`, `parameters`, and — guarded on `temporal_boundary is
not None` — `asked_at`. The answer resolves from the **decoded** request's
parameters, so there is one source for what is answered and the echo is that
same source. `egress.py` now contains zero `DoorOutcome(` constructions.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | One shape, and a producer-side entry that mints what it parsed | `a91d288` | `src/ccf/products/door.py`, `src/ccf/client/wire.py` |
| 2 | The MCP door states what it was asked, and refuses a call that asks two things | `cbed47d` | `runtime/ccf_runtime/mcp/egress.py`, `src/ccf/client/adapters/mcp_stdio.py`, 4 test modules |
| 3 | The door entry's own controls | `b04868d` | `tests/products/test_door_answer.py` |
| — | Surface fragment + citation anchoring (Rule 3) | `7d83b1d` | `docs/surface-changes/19-01-*.md`, `tests/products/test_door_answer.py` |
| — | Reassemble SURFACE-CHANGES.md (Rule 3) | `bf5a4d1` | `docs/SURFACE-CHANGES.md` |
| — | Refresh retirement-couplings report (Rule 3) | `0b5ae4b` | `docs/surface/examples/RETIREMENT-COUPLINGS.md` |

Plus `08156f3` (pre-existing orchestrator commit marking the phase executing).

## The Measured Arithmetic

### Collected-count delta — every increment names the property it holds

Baseline at plan start: **4027** collected (matches `19-RESEARCH.md`'s measured
baseline at HEAD `192c79d`). After: **4051**. Delta **+24**, and it decomposes
exactly:

| Module | Before | After | Δ | What each increment holds |
|--------|--------|-------|---|---------------------------|
| `tests/products/test_door_answer.py` | 0 | 18 | +18 | see the per-test breakdown below |
| `tests/mcp/test_egress_parameters.py` | 11 | 16 | +5 | the address cross-check on three axes, with vacuity guards |
| `tests/crossproc/test_mcp_egress.py` | 38 | 39 | +1 | the echo and the address over the **real** cross-process path |

**The 18 in `test_door_answer.py`, by property:**

| # | Test | Property |
|---|------|----------|
| 1 | `..._absent_boundary_is_echoed_absent_though_the_door_answered_at_one` | `C-02`/`C-15` — the load-bearing one |
| 2 | `..._explicit_boundary_is_echoed_as_that_boundary` | its **vacuity guard** |
| 3 | `..._echo_is_the_whole_question_and_not_a_projection_of_it` | `C-03` total equality |
| 4 | `..._claimed_address_is_sha256_of_the_vessel_beside_it` | serialize once |
| 5 | `..._single_space_inside_the_vessel_breaks_the_address_it_claims` | its **named sabotage** + discrimination guard |
| 6 | `..._refused_outcome_carries_the_echo_and_nothing_of_the_served_half` | `C-04` |
| 7–12 | `door_question_returns_the_question_that_was_encoded[6 cases]` | round-trip over every admissible parameter/temporal shape |
| 13 | `door_question_raises_on_text_that_is_not_a_well_formed_question` | raises rather than defaulting |
| 14 | `test_rule_1_..._both_halves...` | merged validator rule 1 |
| 15 | `test_rule_2_..._neither_half...` | rule 2 |
| 16 | `test_rule_3_..._served_outcome_without_a_content_address...` | rule 3 |
| 17 | `test_rule_4_..._refused_outcome_carrying_a_content_address...` | **rule 4 — no coverage in the tree before this file** |
| 18 | `test_rule_5_..._refused_outcome_carrying_a_replay_reference...` | rule 5 |

The plan required **five** validator states with **five separate assertions**,
counted by name against Task 1's enumeration. Tests 14–18 are those five, one
per rule, not a parametrization standing for all of them.

### The known red Task 1 left, and Task 2 closing it

Task 1 deliberately left `egress.py`'s two `DoorOutcome(` constructions short of
the two new required members. Measured immediately after Task 1's commit:

- **32 tests failed**, in seven modules: `test_mcp_conformance.py` (8),
  `test_egress_refusal_envelope.py` (7), `test_egress_parameters.py` (5),
  `test_mcp_egress.py` (5), `test_mcp_stdio_adapter.py` (3),
  `test_the_mcp_binding_fires.py` (3),
  `test_the_fixture_serves_a_replay_reference.py` (1). 494 passed.
- **4 mypy errors**, all `egress.py:790` and `:796`, `Missing named argument
  "request"` / `"content_address"`.

After Task 2: **526 passed, 0 failed** over the same three trees (494 + 32), and
`make typecheck` `Success: no issues found in 211 source files`. The closed count
is the measured delta, not an assumption.

**The plan predicted the red would land in `tests/mcp` and `tests/crossproc`.
That was incomplete** — 12 of the 32 were in `tests/client`, because every
conformance and adapter leg that drives the real MCP door parses what the door
emits. The plan was not wrong about the cause, only about the blast radius.

### Task 3's sabotage control on the shipped code — observed red

Run in a scratch copy at
`/tmp/.../scratchpad/sabotage/src`, **outside the tree**, per the standing
hazard that nothing in this phase edits and reverts a tracked source file. The
one-line patch made `door_answer` echo `resolved_request.asked_at` on the
temporal axis instead of the caller's boundary — exactly the design `C-02`
rejected:

```
3 failed, 15 deselected in 0.95s
FAILED ...::test_an_absent_boundary_is_echoed_absent_though_the_door_answered_at_one
FAILED ...::test_an_explicit_boundary_is_echoed_as_that_boundary
FAILED ...::test_the_echo_is_the_whole_question_and_not_a_projection_of_it
```

`git status --short` immediately after showed only the new untracked test file.
No tracked source file was modified.

## Verification

| Step | Result |
|------|--------|
| `pytest tests/client tests/mcp tests/crossproc tests/products` | **1012 passed, 0 failed** |
| `pytest tests/client/conformance` | **69 passed** — including `assert_decision_instant_is_auditable` over both subjects (`P5`) |
| `pytest tests/client/conformance -k decision_instant` | 5 passed |
| `make typecheck` | exit 0, 211 files |
| `make lint` | exit 0 (incl. no-hardcoding over `tests/`) |
| `make ci-core` | **exit 0** — 3933 passed, 118 skipped, 0 failed; 400 conformance/parity; 154 gate-tools |
| Six cold-import subprocesses, each importing one module **first** | all exit 0 |
| `pytest tests/invariants` | 183 passed, incl. `test_src_does_not_import_runtime.py` |

**Source assertions, all met:**

| Assertion | Required | Measured |
|-----------|----------|----------|
| `grep -c '^__ccf_mode__ = "algorithmic"' door.py` | 1 | 1 |
| `grep -nE 'datetime\.now\|time\.time\|open\(' door.py` | nothing | nothing |
| `grep -c 'canonical_bytes(answer.product)' door.py` | 1 | 1 |
| `grep -c 'raise ValueError' door.py` | **exactly 8** | **8** |
| `grep -c 'DoorOutcome(' egress.py` | 0 | 0 |
| `grep -c 'door_answer(' egress.py` | 1 | 1 |
| `grep -c 'asked_wire' egress.py` | ≥ 6 | 10 |
| `grep -c 'temporal_boundary is not None' egress.py` | 1 | 1 |
| `grep -c 'canonical_bytes(request)' mcp_stdio.py` | 1 | 1 |

The `raise ValueError == 8` equality discriminated as designed: 5 in the merged
`_exactly_one_half`, 1 in `door_refusal`, 2 arriving with `WireRequest`'s two
field validators.

**Behavioural check of merged rule 4** (a refused outcome carrying a content
address), run before Task 3 existed: construction raises `ValidationError` with
`carries no content address`.

## The must-have truths, each verified

1. **One outcome shape, `WireOutcome` an alias.** `WireOutcome is DoorOutcome`
   asserted in a subprocess; `WireRequest.__module__` prints `ccf.products.door`.
2. **The outcome carries the question the door parsed, at outcome level, on both
   halves.** `test_..._refused_outcome_carries_the_echo_...` asserts
   `parsed.request == asked` on a refusal captured from the fixture's own gates.
3. **The content address is producer-computed from the same `canonical_bytes`
   call.** One `canonical_bytes(answer.product)` in the tree; asserted over the
   real cross-process path.
4. **The echo is as-asked on the temporal axis.** `None` in / `None` out over
   `mcp+stdio`, with the door's resolved instant absent from the echo's canonical
   bytes; the vacuity guard shows an explicit instant is echoed as that instant.
5. **`request` is REQUIRED on the tool, no deprecation window.**
   `REQUIRED_TOOL_ARGUMENTS` is eight names, asserted by set **equality** against
   the generated input schema.
6. **The door refuses a crossed call on `product_class`, `parameters`, and —
   guarded — the temporal axis.** Five behavioural legs, each with its vacuity
   guard; the temporal guard has all three of `C-18`'s regions.
7. **The impossible axis is named rather than papered over.** Recorded in
   `egress.py`'s tool docstring, in the surface fragment's *Known limit* block,
   and asserted as a **passing** test
   (`test_an_absent_boundary_is_never_compared_against_asked_at`) whose docstring
   says in terms that it is a named residual and not a proof of safety. `19-07`
   and `19-08` carry it into `C-10`'s undetected list and the decision log.
8. **`assert_decision_instant_is_auditable` stays green over `mcp+stdio`.** 5
   passed under `-k decision_instant`; 69 passed over the whole conformance tree.

## Deviations from Plan

### Rule 3 — auto-fixed blocking issues

Three CI gates fired on this plan's own `make ci-core` success criterion. All
three are consequences of what this plan added, not pre-existing failures, and
all three were fixed in-plan.

**1. `[Rule 3 - Blocking] Three surface gates refused the new public names**
- **Found during:** plan verification, first `make ci-core`
- **Issue:** `tests/test_surface_completeness.py::test_every_diff_line_has_a_matching_public_log_entry`
  and `tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added`
  both reported `NO ENTRY` for `ccf.products.door.WireRequest`, `.door_answer`
  and `.door_question`.
- **Fix:** filed `docs/surface-changes/19-01-one-outcome-shape-and-the-encoded-question.md`.
  Named `19-01-*.md` per `D-IMPL-155` — a fragment whose filename does not match
  `[0-9]*-*.md` is silently excluded with every gate green.
- **Not scope creep:** Task 1's own action text predicted this
  (*"a name absent from `__all__` is a name absent from `docs/surface/`"*) and
  `19-RESEARCH.md` §9.4 states the phase must file a fragment regardless. It is
  the **mechanical** fragment; `19-07` still owns the corrective prose.
- **Commit:** `7d83b1d`

**2. `[Rule 3 - Blocking] The new test module cited line ranges**
- **Found during:** same run
- **Issue:** `tests/invariants/test_citation_coverage.py` found 5 unanchored
  citations against a ceiling of 0. `D-IMPL-114` rules that prose cites
  `path.py::Symbol`, because a line anchor is wrong the moment code moves.
- **Fix:** converted all four distinct citations to symbol form. **The ceiling
  constant was not raised** — raising it is what the gate's own failure message
  warns against.
- **Note:** the plan itself cites these as line ranges (e.g.
  `tests/client/test_codec.py:379-383`). The gate is the law; the plan's
  citations were used to *find* the symbols.
- **Commit:** `7d83b1d`

**3. `[Rule 3 - Blocking] Two generated documents were stale**
- **Found during:** subsequent `make ci-core` runs
- **Issue:** `tests/test_surface_drift.py::test_the_curated_log_is_assembled_from_the_current_fragments`
  (a plan can write a fragment and never assemble it) and
  `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`.
- **Fix:** `make surface-changes` (+210/−3, and all three deletions are counter
  lines the regeneration recomputed; counts move **up**, 727→734 entries and
  492→498 public, so `D-IMPL-155`'s drop-a-record hazard did not fire) and
  `tools/retirement_sweep.py --report` (two line numbers in `egress.py` shifted
  by one because the door import block went from four names to three; 234 rows
  across 75 files, unchanged).
- **Commits:** `bf5a4d1`, `0b5ae4b`

### Where the plan was measurably wrong

**1. The known-red blast radius was understated.** Task 1's acceptance criteria
said *"`tests/mcp` and `tests/crossproc` are red."* Measured: 32 failures across
**seven** modules, 12 of them in `tests/client` (`test_mcp_conformance.py` alone
accounted for 8). The cause the plan named was right; the list of affected trees
was not. Recording it because the criterion told the executor to record the exact
failing count so Task 2's green would be a measured delta — and the delta was
32, not the ~17 the named two trees would have given.

**2. A test name counted to seven and had to be renamed.**
`test_the_tool_advertises_exactly_the_seven_argument_names` in
`tests/crossproc/test_mcp_egress.py` is now `..._eight_argument_names`, because
`C-16` made `request` the eighth required argument. The plan's action text said
only *"every direct call to the tool gains the new argument"* and did not
anticipate a test **name** carrying a count. `REQUIRED_TOOL_ARGUMENTS`'s docstring
was **amended** (*"This read seven until `C-16`, and now reads eight"*) rather
than replaced, per the standing amend-never-delete rule.

**3. `_STUB`'s tool signature did not actually need the ninth argument to pass.**
Task 2 predicted the inline stub servers in `test_mcp_stdio_adapter.py` *"are
what a ninth tool argument will reach first."* Measured: FastMCP tolerated the
extra argument and those tests were green **before** the stub was changed. The
argument was added anyway, per the plan and because a stub whose signature the
real adapter could not satisfy is a stub that does not reflect the tool — but the
plan's stated reason for the edit was not the reason it was needed. The leg that
genuinely broke was a different one: `test_the_child_resolves_the_same_ccf_this_client_is_running`,
which drives `McpStdioAdapter._call` with an explicit arguments dict.

### Not done, and deliberately

- **`19-02`'s work is untouched.** `mcp_stdio._decode` still runs and still
  overwrites the door's echo with its own argument, so the `B0` defect is still
  live at the end of this plan and every existing test still passes. That is what
  the plan asked for.
- **`.planning/STATE.md` and `.planning/ROADMAP.md` were NOT written**, per the
  orchestrator's standing instruction that the `state.*`/`roadmap.*` SDK writers
  are known-destructive on this repo. The orchestrator owns those writes.

## Branch Note — Requires Dave's Ruling

The plan's standing hazards say *"phase work belongs on `phase-19` (CLAUDE.md
§2.2), with a single merge to `main` at `D-GATE-19`. The branch does not exist
yet and the executor does not create it — confirm with the orchestrator before
the first commit if the working tree is still on `main`."*

**All seven commits landed on `main`.** The reasons, stated so the ruling is
Dave's rather than inferred:

- the orchestrator spawned this executor with an explicit instruction that it is
  *"a SEQUENTIAL executor agent on the main working tree (branch `main`)"*;
- `.planning/config.json` has `git.branching_strategy: "none"`;
- `D-GATE-18.1` records *"NO MERGE REQUIRED — the work landed on `main`"*, so
  the precedent for the immediately preceding phase is the same.

If §2.2's single-merge-at-gate discipline is to hold for Phase 19's code, the
correction has to be made now rather than at the gate.

## Known Stubs

None. Every member added is set by a producer and read by a check or an
assertion; `C-10`'s rule — *a member nothing sets and nothing reads is the
pattern this phase exists to close* — was applied, and no signature member was
reserved.

## Threat Flags

None beyond the plan's own `<threat_model>`. `T-19-01`'s mitigation is
implemented as the plan revised it, including the explicitly **unmitigated**
`as_of=None` path; `T-19-SC` holds — this plan installed no package and added no
dependency.

## Self-Check: PASSED

Created files:
- FOUND: `tests/products/test_door_answer.py`
- FOUND: `docs/surface-changes/19-01-one-outcome-shape-and-the-encoded-question.md`

Commits (all present in `git log`):
- FOUND: `a91d288` `refactor(19-01): one outcome shape, carrying the question and the address`
- FOUND: `cbed47d` `feat(19-01): the MCP door states what it was asked, and refuses a crossed call`
- FOUND: `b04868d` `test(19-01): the door entry's own controls, each with a control that can fail`
- FOUND: `7d83b1d` `docs(19-01): file the surface fragment and anchor the new citations`
- FOUND: `bf5a4d1` `docs(19-01): reassemble SURFACE-CHANGES.md from the fragments`
- FOUND: `0b5ae4b` `docs(19-01): refresh the retirement-couplings report after the egress import shrank`

Key links (all matched):
- `runtime/ccf_runtime/mcp/egress.py` → `door_answer\(` — 1 match
- `src/ccf/client/adapters/mcp_stdio.py` → `canonical_bytes\(request\)` — 1 match
- `src/ccf/client/wire.py` → `from ccf.products.door import` — 1 match
