---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 02
subsystem: examples + lint gates
tags: [runner, seeded-subject, mcp-stdio, no-hardcoding, cinv01a, controls]
requires:
  - "20-01: scenario-rows.yaml, D-IMPL-163, the green retirement baseline, 20-BASE-COMMIT.txt"
  - "examples/hw1-companies-over-revenue: deployment/, server/, consume.py"
  - "src/ccf/client/adapters/binding_document.py::load_binding_document"
provides:
  - "examples/hw1-harness-clients/runner/drive.py — copy, seed, close, resolve, reference-run, compare"
  - "examples/hw1-harness-clients/runner/question.yaml — the declared question"
  - "make example-hw1-harness-clients, a prerequisite of examples:"
  - "tests/examples/test_hw1_harness_clients_wiring.py — the wiring gate + 3 controls"
  - "cinv01a-prompt-shape destination arm + CONTROL 4-8"
affects:
  - "20-03 / 20-04: the runner each leg is wired into; the gate governing every client file"
  - "20-05: --live and the no-model guard hang off drive.py::main"
  - "20-08: the README and criterion-7 assertion"
tech-stack:
  added: []
  patterns:
    - "declared input document + interpreter (D-IMPL-163, D-IMPL-131)"
    - "assertion functions taking their subject as a parameter, with numbered controls"
    - "lint by destination rather than by shape"
key-files:
  created:
    - examples/hw1-harness-clients/runner/drive.py
    - examples/hw1-harness-clients/runner/question.yaml
    - tests/examples/test_hw1_harness_clients_wiring.py
  modified:
    - Makefile
    - tools/lints/no_hardcoding.py
    - tools/lints/tests/test_no_hardcoding.py
    - examples/external/00-hello-context/client_adk.py
    - examples/external/00-hello-context/client_anthropic.py
    - examples/external/00-hello-context/run.py
    - examples/external/00-hello-context/artifacts/experience.yaml
    - public/how-to/run-agents-cross-process.md
    - .planning/REQUIREMENTS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "The runner pins nothing: the demonstration's threshold and boundary live in a declared question.yaml, because CLAUDE.md §6.4 names a threshold in code as a defect"
  - "marker_violations landed in wave 2, not wave 3 — the wave-1 document already cites it and cite03 goes red the moment drive.py exists without it"
  - "The remediated question moved to artifacts/experience.yaml rather than into run.py, so the prompt left client code without re-entering example code"
metrics:
  duration: ~3h
  completed: 2026-08-20
requirements: [CLNT-24, CLNT-27, CLNT-31, CLNT-32]
---

# Phase 20 Plan 02: The Fabric-Side Runner and the Prompt Gate — Summary

A runner that proves criterion 4 with zero client legs wired, and a lint arm
that refuses a prompt by where it goes rather than by how long it is.

## What was built

**`examples/hw1-harness-clients/runner/drive.py`** (686 lines) copies
`deployment/` and `server/` under one temp parent, seeds the copy from the
declared rows document, **closes the writer in a `finally`**, resolves the
door's `command + args` from the copy's own `binding.yaml`, runs the tracked
example's own `consume.py` against the same copy over
`CCF_BINDING=inprocess:<tmp>/deployment`, and reports the content address that
falls out — refusing to proceed on a zero-company answer.

`make example-hw1-harness-clients` runs it, is a prerequisite of `examples:`,
and a test with three controls asserts that membership by reading the Makefile.

`cinv01a-prompt-shape` gained a **destination arm**: a prose-candidate literal
reaching a model-instruction sink is refused without consulting `prompt_score`
at all. It surfaced the two genuine §6.4 violations the plan predicted, both of
which are remediated to a required-env read with `tools/lints/allowlist.yaml`
byte-unchanged.

## Task-by-task

| Task | Commit | What landed |
|---|---|---|
| 1 — the seeded subject | `d21b47a` | `build_subject`, `declared_rows`, `seed`, `seeded_subject`, plus `marker_violations` (see deviations) |
| 2 — door, reference run, comparison | `0050cbe` | `resolve_door`, `build_question`, `request_violations`, `reference_address`, `compare_addresses`, `main`; `question.yaml` |
| 3 — make wiring | `1fd4507` | `Makefile` target + `examples:` membership + help count; the wiring test and its controls; a published page naming the target; the retirement report |
| 4 — the prompt gate (RED) | `2abc9d2` | CONTROL 4-8, failing |
| 4 — the prompt gate (GREEN) + remediation | `3c9cb0d` | the destination arm, the module docstring, both client remediations |
| 4 — `CLNT-32` | `7562469` | the tenth Phase 20 requirement row |

## The measurement that matters

**Measured after the arm landed and before the two remediations**
(`.venv/bin/python -m tools.lints --all`):

- **exactly 2** `cinv01a-prompt-shape` findings, both carrying the **same**
  fingerprint `f92ad0b8…` — one literal, two files;
- `examples/external/00-hello-context/client_adk.py:59`, sink `text=`;
- `examples/external/00-hello-context/client_anthropic.py:59`, sink
  `{"role": ..., "content": ...}`;
- **0** findings in each of `src`, `runtime`, `tests`.

This reproduces the plan's `<lint_blast_radius>` exactly, including the sink
families: one keyword-argument sink, one chat-message mapping, zero positional
sink-call findings.

**And the trap was measured, not merely avoided.** With the arm's
`ast.Name` resolution deleted — the "literal appearing at a sink"
implementation the plan warned about — `tools.lints --all` reports **zero**
findings over the whole tree and exits 0. The literal sits ~20 lines above the
sink in both files and reaches it through a local binding whose value is an
`os.environ.get(NAME, <literal>)` default. An arm that does not follow the
value finds nothing and looks like a clean tree.

**The score arm is unretuned.** `PROMPT_SCORE_THRESHOLD = 2`,
`MIN_SENTENCES = 3`, `PROSE_CHARS = 200`, `MIN_BRACES = 3` — all four grep as
before. The arm added a second way to fire; it did not touch the first.

## Controls, and what was broken to see each one fail

Every control was observed red by mutating the **shipped** function, never by
assertion alone. Each mutation failed exactly its own control and nothing else.

| Control | Mutation applied to the shipped code | Result |
|---|---|---|
| CONTROL 1 (wiring) | deleted the absent-target branch of `wiring_violations` | `test_a_missing_target_is_a_violation` FAILED |
| CONTROL 2 (wiring) | deleted the empty-prerequisites branch | `test_an_empty_prerequisite_tuple_is_a_violation` FAILED |
| CONTROL 3 (wiring) | made `examples_prerequisites` return `(TARGET,)` when no line matched | `test_a_makefile_with_no_examples_line_is_a_violation` FAILED |
| help-text guard | stopped stripping the `##` comment | `test_the_help_text_is_not_read_as_a_prerequisite` FAILED |
| CONTROL 4 | deleted the positional sink-call branch of `instruction_sinks` | `test_control_4_…` FAILED |
| CONTROL 5 | dropped `system` from `INSTRUCTION_SINK_KWARGS` | `test_control_5_…` FAILED |
| CONTROL 6 | deleted `ast.Name` resolution from `resolved_text` (the literal-at-sink mis-implementation) | `test_control_6_…` FAILED |
| CONTROL 7, red half | deleted the chat-message mapping branch | `test_control_7_…` FAILED |
| CONTROL 7, bound half | deleted the `"role" not in keys` requirement | `test_control_7_…` FAILED |
| CONTROL 8 | stopped filtering the sink value with `_is_prose_candidate` | `test_control_8_…` FAILED |

**Controls that could not be made to fail: none.**

Runner-side properties were exercised directly rather than as numbered
controls (their controls belong to `20-03` T3 and `20-05`): an unseeded subject
was driven through `reference_address` and refused with *"the reference answer
names zero companies"*; `compare_addresses` refused both a divergence and an
empty observation; two consecutive `seeded_subject` drives raised no
`SingleWriterViolation`.

## Deviations from plan

### 1. [Rule 3 — Blocking] `marker_violations` landed in wave 2, not wave 3

- **Found during:** Task 1, at the first `tools.lints --all` after `drive.py`
  existed.
- **Issue:** `scenario-rows.yaml`, committed in `20-01`, cites
  `examples/hw1-harness-clients/runner/drive.py::marker_violations`. While
  `drive.py` did not exist the citation was unresolvable and `cite03-node-id`
  stayed quiet; the moment the file existed without that symbol the lint went
  red. `20-03` T3 owns the *payload* assertion, but the symbol the wave-1
  document names had to exist in the commit that created its host.
- **Fix:** `declared_markers` and `marker_violations` implement the four
  properties `scenario-rows.yaml` states in prose — distinctness and a
  4-character floor, no substring pair, no hex-only name, no collision with the
  console vocabulary — plus an empty-set refusal. `main()` calls the check on
  every default-path run, which is what the document already claims.
- **Files:** `examples/hw1-harness-clients/runner/drive.py`
- **Commit:** `d21b47a`

### 2. [Rule 2 — CLAUDE.md §6.4] The threshold and boundary are a document, not constants

- **Issue:** the plan's Task 2 says `--min-revenue` comes "from the question's
  threshold" and pins `--as-of` to `2026-08-01T00:00:00+00:00`. Neither value
  is declared anywhere the runner can read: the only in-tree statements are the
  two `example-hw1*` Makefile recipes and hw1's README. Two module constants
  would have been the obvious reading — and CLAUDE.md §6.4 names *threshold*
  explicitly among the things that may not be code constants, in `/examples` as
  much as in `/src`.
- **Fix:** `examples/hw1-harness-clients/runner/question.yaml`, a second
  declared input document beside the runner, carrying `parameters:` and
  `as_of:`. `D-IMPL-131` is the precedent for a demonstration's number living
  in a document without becoming part of the question's identity;
  `D-IMPL-163` is why an input document under `examples/` is admissible. The
  precedent's own tree is retiring, so it is cited by decision id and not by
  path (`D-IMPL-144`).
- **Strengthened rather than merely relocated:** `request_violations` compares
  the document's parameter names against the deployment's own
  `request_contract.arguments.required` and refuses a mismatch in either
  direction, so the runner spells no parameter name of its own and the two
  documents cannot drift silently.
- **Files:** `examples/hw1-harness-clients/runner/question.yaml`, `drive.py`
- **Commit:** `0050cbe`

### 3. [Rule 3 — Blocking] A composed example target must be named by a published page

- **Found during:** Task 3, at `make gate-tools` after the Makefile edit.
- **Issue:** `tools/docs_tests/test_documented_commands_exist.py` enforces a
  bijection — every `example-*` target composed into `examples:` must be named
  by a page under `public/`, or it is "maintained, tested, and unfindable".
  Both directions of that gate went red on the new target.
- **Fix:** a short section at the end of `public/how-to/run-agents-cross-process.md`
  naming `make example-hw1-harness-clients`, chosen because that page already
  ends by pointing at the MCP-consumption case this example is. Deliberately
  minimal: `20-08` owns this phase's documentation.
- **Commit:** `1fd4507`

### 4. [Rule 3 — Blocking] A-1 forbids the submodule import spelling in `examples/`

- **Issue:** `from ccf.deployment.config import load_config_and_boot` — the
  spelling `tests/client/conftest.py` uses — is refused inside `examples/` by
  `tools/docs_tests/test_advisory_discharge.py::test_a1_no_submodule_import_is_taught_or_demonstrated`,
  because the examples are the snippet source of record for the published tree.
- **Fix:** `from ccf.deployment import load_config_and_boot`.
- **Commit:** `1fd4507`

### 5. [Judgement] The remediated question went to an artifact, not to `run.py`

- The plan permits "the runner or the recipe". Putting the literal in
  `run.py` would have moved a prompt from one file under `examples/` to another
  — no gate would have caught it, and §6.4 scopes to the whole tree. It went to
  `artifacts/experience.yaml` instead, whose own header already says
  *"Everything the MCP surface advertises lives HERE, never in `serve.py`"* and
  which already carries the model names the legs read from env. `run.py` passes
  it to every leg through `CCF_EXAMPLE_QUESTION`; both clients read it as
  required. **The text is byte-identical to the fallback it replaced**, so
  behaviour did not change — and offline CI is unaffected regardless, because
  `replay_server.py::fingerprint` records message content as an intentional
  residual outside its comparison.

### 6. [Deferred] No `_terminate` helper

- Task 2 asks for children terminated in a `finally` in the
  `examples/external/00-hello-context/run.py::_terminate` shape. This plan
  wires no legs, and the only child is `subprocess.run`, which cannot outlive
  the call — the door is spawned by each client's own library (`H-01`), never
  by the runner. A `_terminate` with no caller would be dead code. The
  docstring records the reasoning; `20-03` adds the helper with the first leg
  that needs it.

## Verification

| Command | Result |
|---|---|
| `.venv/bin/python examples/hw1-harness-clients/runner/drive.py` | exit 0, prints a 64-hex address from a 3-of-6 answer |
| `make example-hw1-harness-clients` | exit 0 |
| `make examples` | exit 0 (eleven examples) |
| `make example-ext-00` | exit 0, 8 assertions |
| `make gate-tools` | exit 0, 154 passed |
| `make ci-core` | **exit 0** — 4018 passed, 118 skipped |
| `.venv/bin/python -m tools.lints --all` | exit 0 |
| `.venv/bin/python -m pytest tests/examples -q` | 391 passed, 37 skipped |
| `pytest tools/lints/tests/test_no_hardcoding.py -q` | 30 passed |
| `pytest tests/examples/test_hw1_harness_clients_wiring.py -q` | 5 passed |
| `pytest tests/invariants/test_citation_coverage.py -q` | 5 passed |
| `pytest …test_s2_client_transport_spike.py::test_the_shipped_external_example_is_untouched` | passed, **after** the remediation commit |
| `git diff --stat 9e4bd0e..HEAD -- src/` | empty |
| `git diff 9e4bd0e..HEAD -- tools/lints/allowlist.yaml` | empty |
| `git diff --stat 9e4bd0e..HEAD -- .planning/ROADMAP.md` | empty |
| `git status --porcelain examples/hw1-companies-over-revenue/` | empty |
| `grep -c '^- \[ \] \*\*CLNT-32' / '^\| CLNT-32 \| Phase 20 \|'` | 1 / 1 |
| `git diff .planning/REQUIREMENTS.md \| grep '^-' \| grep -c 'CLNT-'` | 0 |

Layout, as ruled: no `run.py` and no `artifacts/` anywhere under
`examples/hw1-harness-clients/`; no `.py` at the example root.

## Known stubs

**`KNOWN_LEGS` is empty**, and that is the plan's design rather than an
omission: the substrate is proven before any leg exists, because a leg wired
against an unproven substrate measures the substrate's failure and reports it
as the leg's. `compare_addresses` is therefore called with an empty mapping
only in its own probe and never on the default path — and it refuses an empty
observation, so the vacuous pass cannot arrive later by accident. `20-03`
appends legs 1 and 3; `20-04` appends leg 2.

## Threat flags

None. No new network endpoint, auth path, file-access pattern or schema change
at a trust boundary. The plan's `T-20-04`…`T-20-10` dispositions are all
discharged as written: `COPY_IGNORE` keeps a developer's populated graph and
artifact store out of the copy (asserted); the tracked tree is never written
(asserted); the seed writer is closed (two consecutive drives, no
`SingleWriterViolation`); the reference address comes from a run against the
same seeded copy and a zero-count answer is refused; the child environment is
`{**os.environ, CCF_BINDING: …}`, the accepted `T-20-08` posture; the arm only
*adds* findings and the allowlist is byte-unchanged; the remediation was
committed before verification.

## Self-Check: PASSED

Every file this SUMMARY claims exists on disk; every commit hash it cites
resolves in `git log`. Checked mechanically, not by recollection.
