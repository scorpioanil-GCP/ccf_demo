---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 08
subsystem: examples
tags: [readme, adoption-contract, criterion-7, live-targets, sabotage-controls, phase-close]

requires:
  - phase: 20-07
    provides: "A tree with the prior-vintage duplicates resolved, so the README's claim that these three clients are the canonical foreign-harness demonstration is true of the tree it describes"
  - phase: 20-06
    provides: "The declared budget line, the three documented command blocks, and the per-root COMMAND_SPECS lookup that gates them — all of which this plan wrote around rather than through"
provides:
  - "One README carrying fifteen named elements: the frame, a measured per-harness install list, the literal `json.dumps` encode of the opaque `request` argument, the who-holds-the-MCP-session asymmetry, the per-leg determinism split, `--live` with leg 2's explicit `ANTHROPIC_BASE_URL` requirement, where the prompt comes from, what to change first, the server-assembly out-of-scope sentence, and the runner's placement"
  - "A README-structure assertion with whitespace-normalized markers and five controls"
  - "Three `--live` opt-in make targets, phony, outside `examples:`, with two more controls"
  - "Criterion 7 as an assertion over `git diff --stat <pinned base>..HEAD`, with CONTROL 6 and CONTROL 7 — the controls that separate 'the client surface did not change' from 'nothing was compared'"
  - "D-IMPL-167/168/169: the `H-01`..`H-14` ratification with two measured corrections, ruling 6 with both blast-radius numbers, and the `--question-json` argv shape"
affects: []

tech-stack:
  added: []
  patterns:
    - "A prose gate matches whitespace-normalized markers, so a re-wrap cannot fail a check that is about content"
    - "An emptiness assertion is worthless without a control that hands the same function a subject that is NOT empty"

key-files:
  created:
    - tests/examples/test_hw1_harness_clients_readme.py
  modified:
    - examples/hw1-harness-clients/README.md
    - Makefile
    - docs/DECISIONS.md
    - .planning/REQUIREMENTS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "The criterion-7 assertion lives in `tests/examples/test_hw1_harness_clients_readme.py` rather than a sibling module: it is the same claim from the other side — the README tells an adopter that installing CCF is not part of consuming a Context Product, and criterion 7 is the assertion that the diff kept that promise too"
  - "Three D-IMPL entries were appended, not the two the plan's acceptance criterion counts. The plan's own action block lists three; the count in the criterion is stale, and appending two would have dropped the `--question-json` entry the action asks for"
  - "The plan's `CLNT-01..22 untouched` acceptance grep returns 3, not 0, and it is a false positive rather than a defect: CLNT-25, CLNT-29 and CLNT-32's own bodies cite `CLNT-12` and `CLNT-17`. A precise check by row id was used and reports zero"
  - "`--live` commands are documented as `make` target names rather than as interpreter invocations, because `HARNESS_README_COMMAND` matches any line beginning `.venv/bin/python examples/hw1-harness-clients/` and the gate requires exactly three such lines"

patterns-established:
  - "A README-element marker is a distinctive phrase or literal token, never a full sentence: the check refuses the element going missing, not the element being reworded"

requirements-completed: [CLNT-23, CLNT-24, CLNT-25, CLNT-26, CLNT-27, CLNT-28, CLNT-29, CLNT-30, CLNT-31, CLNT-32]

metrics:
  tasks: 3
  commits: 4
  duration: "~2h"
---

# Phase 20 Plan 08: The one README, the `--live` opt-ins, and the phase close — Summary

The adoption contract is written, its required elements are asserted by name
with five controls, three `--live` targets exist outside the always-on list with
two more, and criterion 7 — *no new SDK mechanism ships* — is an assertion over
a pinned diff base with the two controls that stop it being vacuous.
`git diff --stat 9e4bd0e..HEAD -- src/` prints nothing, and this plan proved
that the command producing that nothing works.

## What the README carries, and why each element is there

Fifteen elements, each asserted by name in
`tests/examples/test_hw1_harness_clients_readme.py::REQUIRED_ELEMENTS`.

| Element | Marker | Why it is required |
| --- | --- | --- |
| The frame | `Same product, same door, three harnesses` | ruling 2 — one README, not three |
| Install, leg 1 | `` `google-adk` `` | criterion 9 |
| Install, leg 2 | `` `claude-agent-sdk` `` | criterion 9 |
| Install, leg 3 | `` `langchain-core` `` | criterion 9 |
| The opaque schema | `{"type": "string"}` | the seam a reader trips on |
| The literal encode | `json.dumps(` | research's sharpest teaching burden |
| Its canonical rendering | `separators=(",", ":")` | the encode is only useful in full |
| The asymmetry | `agent binary you configure` | `H-07` |
| The determinism split | `no network call at all` | criterion 6, per leg |
| `--live`'s one meaning | `one thing across all three legs` | `H-09` |
| Leg 2's `--live` requirement | `ANTHROPIC_BASE_URL` | plan `20-04`'s refusal, agreed word for word |
| The prompt's source | `CCF_HARNESS_PROMPT` | ruling 6(a) |
| What to change first | `## What to change first` | criterion 9 |
| Server assembly is out of scope | the sentence, echoing hw1's own | criterion 9, `H-14`-adjacent |
| The runner's placement | `reader_visible_modules` | `H-11`/`H-12` |

**Markers are matched whitespace-normalized.** A README is wrapped prose; a
marker that failed because the paragraph got re-wrapped at a different column
would be testing the wrapping. `_flat` collapses runs of whitespace on both
sides before comparison.

**The install list is measured, not remembered.** Read off the three clients'
own imports: `google.adk.tools.mcp_tool` + `mcp`; `claude_agent_sdk`;
`langgraph.graph` + `langchain_core.tools` + `mcp`. All four distributions are
already dev dependencies through `pyproject.toml`'s `harnesses` extra
(`ccf[adk,claude-agent,langgraph]`), so nothing needs installing inside this
repository — and outside it, an adopter installs their own harness, an MCP
client, and **nothing from CCF**, which is the claim written as a shopping list.

**The asymmetry is stated as a three-row table plus a paragraph**, not smoothed
over. ADK and LangGraph hold the MCP client in your process; the Claude Agent
SDK holds it in an agent binary you configure, because `claude_agent_sdk` routes
everything it does — its MCP client included — through the `claude` CLI
subprocess it bundles. The README says in as many words that *who holds the MCP
session differs by harness, and what does not differ is CCF*, and then makes the
point Dave's framing implies: **if the three legs printed the same address only
because they were the same program, the demonstration would be about the
programs. They are not the same program, and they still agree.**

**The literal encode is written out** because the door advertises `request` as a
bare `{"type": "string"}` and a string is not a shape. The README shows the
three-field mapping and `json.dumps(..., sort_keys=True, separators=(",", ":"),
ensure_ascii=False)`, names it as the one seam in the "an MCP tool registration
and nothing else" story, and says plainly that it is a **documentation
obligation rather than a defect to fix**: the argument is required by `C-16`,
and publishing a richer schema would be a codec change, which criterion 7
forbids.

**Leg 2's `--live` sentence agrees with the two texts that already say it.**
`examples/hw1-harness-clients/runner/drive.py::main`'s `--live` help and
`examples/hw1-harness-clients/client_anthropic.py::main`'s refusal message both
state it; plan `20-04`'s SUMMARY quotes both in full. The README's wording —
*"the runner deliberately stops injecting the variable, and the client refuses
rather than falling back to a vendor endpoint"* — is taken from them rather than
paraphrased, so an operator who gets the refusal finds the same sentence in all
three places.

## Task-by-task

| Task | Commit | What landed |
| --- | --- | --- |
| 1 — the one README | `3fd38af` | ten new `## ` sections plus the frame sentence and the install table |
| 2 — the structure test and the `--live` targets | `cfa3bd2` | `tests/examples/test_hw1_harness_clients_readme.py`, three Makefile targets, CONTROL 1-5 |
| 3 — the phase close | `569fac1` | `client_surface_diff` + CONTROL 6/7, `D-IMPL-167`/`168`/`169`, ten requirement rows, the regenerated inventory |
| SUMMARY | this commit | the close sequence in `<open_residual>`, followed and recorded |

The criterion-7 assertion went into the **same module**, not a sibling. It is the
same claim from the other side: the README tells an adopter that installing CCF
is not part of consuming a Context Product from a foreign harness, and criterion
7 is the assertion that the phase kept that promise in the diff as well as in
the prose.

## Controls, and what was broken to see each one fail

Every control was observed red by mutating the **shipped function**, never by
assertion alone. The file was restored from a backup after each mutation and
`git diff` verified empty before the next.

| Control | Subject | Mutation applied to the shipped code | Observed |
| --- | --- | --- | --- |
| CONTROL 1 | the real README with `agent binary you configure` removed | `if _flat(marker) not in flat:` → `if False:` | `test_control_1_...` FAILED |
| CONTROL 2 | an empty `required` mapping | `if not required:` → `if False:` | `test_control_2_...` FAILED |
| CONTROL 3 | a whitespace-only README text | `if not text.strip():` → `if False:` | `test_control_3_...` FAILED |
| CONTROL 4 | a synthetic Makefile carrying two of the three live targets | `if target not in declared:` → `if False:` | `test_control_4_...` FAILED |
| CONTROL 5 | a synthetic `examples:` line carrying `…-live-adk` | `if target in prerequisites:` → `if False:` | `test_control_5_...` FAILED |
| CONTROL 6 | base `9e4bd0e`, path `examples/` — a pair that genuinely differs (17 stat lines) | `return completed.stdout` → `return ""` | `test_control_6_...` FAILED **while both shipped emptiness assertions still PASSED** |
| CONTROL 7 | base `0000000000000000000000000000000000000000` | `if completed.returncode != 0:` → `if False:` | `test_control_7_...` FAILED |

**Controls that could not be made to fail: none.**

**CONTROL 6 is the one that earned its place, and the measurement says why.**
Under its mutation — `client_surface_diff` returning an empty string, which is
what a broken, unresolvable or misspelled `git diff` produces — pytest reported
`1 failed, 2 passed`. The two that passed were
`test_criterion_seven_no_file_under_the_client_surface_changed` and
`test_criterion_seven_no_sdk_mechanism_ships_at_all`. Without CONTROL 6 the
phase would have closed on two green assertions over a comparison that never
happened, which is the exact shape this project has recorded across Phases 17,
18.1 and 19.

Two unnumbered guards ship alongside them: an empty target tuple and an empty
path list are both refused rather than reported clean, and a declared-but-not-
`.PHONY` target is a violation with its own doctored subject.

## A defect this plan's own gate caught, in its own gate

The first `phony_declarations` read only lines beginning `.PHONY:`. This
`Makefile`'s main `.PHONY` block is **one logical line spelled across ten
physical ones**, so the parser saw the first line's names and missed everything
after the first backslash — and the shipped assertion immediately reported all
three real targets as non-phony. A confident, specific, wrong finding, produced
by a checker that had been green for nine other tests. The parser now follows
continuations, and its docstring records the measurement rather than the fix.

Worth stating because it is the same defect class the phase has been recording
all along, arriving from the direction nobody guards: not a check that cannot
fail, but a check that fails for a reason that is about the checker.

## Criterion 7, measured

| Diff | Result |
| --- | --- |
| `git diff --stat 9e4bd0e..HEAD -- src/ccf/client/` | **0 lines** |
| `git diff --stat 9e4bd0e..HEAD -- src/` | **0 lines** |
| `git diff --stat 9e4bd0e..HEAD -- examples/` (CONTROL 6's subject) | 17 lines |
| `git diff --stat 9e4bd0e..HEAD -- pyproject.toml .github/workflows/` | 0 lines |

The second row is wider than criterion 7's prose, deliberately: the criterion
names `src/ccf/client/`, but the phase's constraint is that **no SDK mechanism
ships at all**. Both are asserted, and the module's docstring says a non-empty
result on the wider path is a blocking finding to report rather than a reason to
narrow the assertion back.

## The `--live` wiring

Three targets — `example-hw1-harness-clients-live-adk`, `…-live-anthropic`,
`…-live-langgraph` — each `$(ENV) $(PYTHON) … --live --legs <leg>`, each declared
`.PHONY`, each with a `##` help line naming it opt-in and never CI, and **none of
them on the `examples:` line**. Measured: `make -n examples | grep -c ' --live'`
returns `0`, and `grep -E '^examples:' Makefile | grep -c live` returns `0`.

The README documents them as `make` target names rather than as interpreter
invocations, and that is forced rather than preferred:
`tests/examples/test_client_example_purity.py::HARNESS_README_COMMAND` matches
**any** line beginning `.venv/bin/python examples/hw1-harness-clients/` and the
gate requires exactly three such lines paired with three recipes. A fourth
documented invocation would have gone red for a reason that had nothing to do
with the `--live` targets.

The wiring test does **not** re-assert the deterministic target's membership in
`examples:` — `tests/examples/test_hw1_harness_clients_wiring.py` owns that
claim. Its `examples_prerequisites` parser is imported and reused, so the two
modules cannot drift into two notions of what a prerequisite is.

## The decision entries

Three appended above the gate log, nothing edited away
(`git diff docs/DECISIONS.md | grep -c '^-[^-]'` returns `0`):

- **`D-IMPL-167`** ratifies `H-01`..`H-14` as one entry, one line each, and names
  the two whose **stated mechanics were contradicted by measurement and whose
  intent was preserved**. `H-08`: the replay harness could not be copied
  unchanged, because the `claude` CLI always sends `"stream": true` and a JSON
  body is not an acceptable answer to it — what was copied is the fail-loud
  discipline, with server-sent events replacing the JSON response. `H-12`: the
  permitted-import set had to become a **per-root parameter**, because the two
  gated roots say opposite things about `ccf.client` and both are right. Both
  intents hold in full; a ruling whose mechanics changed and whose change was
  never written down is a ruling that quietly stopped meaning what it said.
- **`D-IMPL-168`** records ruling 6 with **the measurement that forced it**:
  `prompt_score` scoring four realistic short agent prompts 0-1 against
  `PROMPT_SCORE_THRESHOLD = 2` (one signal being `MIN_SENTENCES = 3`), so
  `no_hardcoding.check_source` returned **no finding** for a hardcoded system
  instruction in an example client. **Both blast radii are in the entry.**
  Candidate A — lowering the threshold to 1 — **rejected at 94** new findings
  (`src` 58, `runtime` 8, `tests` 28, `examples` 0), effectively all false
  positives, and it would not even have caught two of the four shapes. Candidate
  B — the destination arm — **adopted at 2**, both genuine §6.4 violations in
  `examples/external/00-hello-context/`, both **remediated in the same task
  rather than allowlisted**. The trap is recorded too: with the arm's `ast.Name`
  resolution deleted, the whole tree reports zero findings and exits 0. The
  accepted residual — the sink sets are name enumerations, so a harness spelling
  its instruction API differently escapes — is recorded in the `D-12` class.
- **`D-IMPL-169`** records the `--question-json` argv shape: why `H-03`'s flag
  set is wider than `H-02`'s `command + args` pair (the eight question values are
  deployment facts that CLAUDE.md §9 forbids as literals in example code), and
  why one JSON flag beat eight scalar flags (a client declaring `--tenant`,
  `--product-class`, `--as-of` and five more would be a client that *knows the
  product's request shape*, which is the knowledge this example exists to show is
  unnecessary).

**Three, where the plan's acceptance criterion counts two.** The plan's own
action block asks for three; the count in the criterion is stale. Appending two
would have dropped the `--question-json` entry the action names.

## Requirement rows

`CLNT-23`..`CLNT-32` — **ten** rows, not nine — hand-flipped from `- [ ]` to
`- [x]`, and their traceability rows from `Pending` to `Complete`. No
`gsd-sdk query state.*` or `roadmap.*` writer was run. Leg 2 did not stop, so
`CLNT-23` is flipped with the rest.

`.planning/ROADMAP.md` is **unchanged**:
`git diff --stat -- .planning/ROADMAP.md | wc -l` returns `0`.

## Plan drift, reported rather than worked around

1. **The `CLNT-01..22 untouched` acceptance grep returns `3`, not `0`.** All
   three are false positives: the *bodies* of `CLNT-25`, `CLNT-29` and `CLNT-32`
   cite `CLNT-12` and `CLNT-17`, and a `grep -c 'CLNT-\(0[1-9]\|1[0-9]\|2[0-2]\)'`
   over removed lines counts a citation inside a row it is rewriting. A precise
   check by **row id** — extracting the identifier at the start of each removed
   checkbox or table row — reports the removed set as exactly `CLNT-23`
   through `CLNT-32`, with zero outside it and zero non-`CLNT` removed lines.
2. **"at least 7 tests"** — the module ships **16**.
3. **The measured client sizes are 186 / 288 / 237**, not the plan's "~150" and
   not the brief's 235 for LangGraph. The README quotes none of them, by design:
   plan `20-06`'s budget line is the one enforced number and two numbers is two
   things to keep in step.
4. **The plan's `<retirement_currency>` block and `<open_residual>` both hold as
   written.** No correction needed.

## Gates that stayed armed

| Assertion | Result |
| --- | --- |
| `git diff --stat <plan base>..HEAD -- tools/lints/allowlist.yaml tools/lints/no_hardcoding.py` | empty — the wave-2 prompt arm untouched |
| `git diff --stat 9e4bd0e..HEAD -- src/` | empty |
| `git diff --stat 9e4bd0e..HEAD -- pyproject.toml .github/workflows/` | empty — no package installed, no CI step added |
| `git diff --stat -- .planning/ROADMAP.md` | empty |
| `git diff examples/…/README.md \| grep -c '^-.*[Dd]eclared budget'` | `0` — the gated budget line byte-unchanged |
| `git diff examples/…/README.md \| grep -c '^-\.venv/bin/python'` | `0` — the three gated command blocks byte-unchanged |
| documented harness commands in the README | exactly `3`, paired character-identically with three recipes |
| `.venv/bin/python -m tools.lints --all` | exit 0 |
| `pytest tests/invariants/test_citation_coverage.py` | 5 passed — `MAXIMUM_UNANCHORED_PY_CITATIONS = 0` held across the largest block of new prose in the phase |
| `grep -c '^## ' examples/external/00-hello-context/README.md` | `7` — the seven-heading shape intact |
| `pytest tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` | passed |

## The phase-close sequence, followed and recorded

`<open_residual>`'s sequence was followed: **all plans done → this SUMMARY
written → `tools/retirement_sweep.py --report` run again → committed → `make
ci`.** The second regeneration is the one that absorbs this file, which names
`examples/s2-01-external-consumers/` and other retiring paths and would
otherwise re-stale the committed inventory the moment it landed.

**The residual was not hypothetical, and the second regeneration measured it.**
The sweep run after this file was written added **exactly one row** to
`docs/surface/examples/RETIREMENT-COUPLINGS.md` — this SUMMARY's own, carrying
two counted references. Had the sequence been skipped, `make ci` would have been
red at the phase close on a tree nobody had otherwise changed.

Neither cheaper option was taken. This SUMMARY was not constrained to avoid
naming retiring paths, and the currency test was **not** exempted from the
phase-close `make ci`. The residual is handed up rather than designed around: if
the manual sequence ever proves insufficient, that is a `D-IMPL-NN` and a stop
for Dave, not a disarmed gate.

## Residuals carried up

1. **The post-SUMMARY regeneration window is a manual step, not a mechanism.**
   Every plan in this phase regenerated the inventory as its final action, which
   absorbs the *preceding* plan's SUMMARY. There is no absorber for the last one,
   so the close sequence above is a hand-run step that the next phase's first
   plan must repeat if it edits `.planning/**` before running `make ci`. Stated
   here because a sequence nobody wrote down does not survive the next reader.
2. **That the x86_64 wheel of `claude-agent-sdk==0.2.128` bundles the CLI binary
   remains UNVERIFIED** and cannot be observed from this aarch64 host. Carried
   unchanged from plan `20-04`. No fallback was built and none should be: a
   fallback would be a path CI never exercises, which is the failure mode ruling
   1 and criterion 6 both name. The aarch64 wheel does carry
   `claude_agent_sdk/_bundled/claude`, and every drive in this phase ran against
   it. The README states that the wheel bundles the CLI without qualifying it by
   architecture; if the x86_64 wheel turns out not to, that sentence is the one
   to correct.

## Self-Check: PASSED

Every file this SUMMARY claims was created or modified exists on disk, and every
commit hash it cites resolves in `git log`.
