---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 01
subsystem: planning-foundations
tags: [requirements, decisions, retirement-sweep, declared-input]
status: COMPLETE — 4 of 4 tasks; task 3 completed under Dave's wave-1 layout ruling
requires: []
provides:
  - CLNT-23..CLNT-31 requirement rows
  - D-IMPL-163 (the D-32 narrowing)
  - the phase's pinned diff base for criterion 7
  - the declared input document the 20-02 runner interprets
  - a green retirement-currency baseline
affects:
  - .planning/REQUIREMENTS.md
  - docs/DECISIONS.md
  - docs/surface/examples/RETIREMENT-COUPLINGS.md
  - examples/hw1-harness-clients/
tech-stack:
  added: []
  patterns:
    - hand-edited planning documents
    - append-only decision log
    - tool-generated inventory
    - declared input document beside its interpreter
key-files:
  created:
    - .planning/phases/20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a/20-BASE-COMMIT.txt
    - examples/hw1-harness-clients/runner/scenario-rows.yaml
  modified:
    - .planning/REQUIREMENTS.md
    - docs/DECISIONS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - D-IMPL-163 — D-32 narrowed to producer OUTPUT; a declared INPUT document under examples/ is permitted
  - "Wave-1 layout ruling (Dave, 2026-08-20): the declared input and the runner both live in runner/; no artifacts/ directory; the runner is drive.py, never run.py"
metrics:
  tasks-planned: 4
  tasks-complete: 4
  commits: 5
  completed: 2026-08-20
---

# Phase 20 Plan 01: Paper Foundations Summary

Minted `CLNT-23..CLNT-31`, recorded the `D-32` narrowing as `D-IMPL-163`, pinned
the criterion-7 diff base, authored the declared input document the `20-02`
runner will interpret, and turned the phase's retirement-currency gate from red
to green.

Task 3 hit a real trap on its first attempt — the location the plan originally
mandated is structurally refused by a shipped, always-on gate — and it was
resolved by Dave's ruling rather than by weakening the gate. The analysis is
preserved below because it is the record of **why the layout is what it is**.

## Status: COMPLETE

| Task | Name | Status | Commit |
| --- | --- | --- | --- |
| 1 | Mint `CLNT-23..31`, pin the diff base | Complete | `03a5ec6` |
| 2 | Record the `D-32` narrowing as `D-IMPL-163` | Complete | `a0cfb5f` |
| 3 | Author `scenario-rows.yaml` | Complete | see below |
| 4 | Regenerate the retirement inventory | Complete | `c04dc02` |

Task 4 was run last, as the plan requires, and re-run after task 3 landed.

## What shipped

### Task 1 — `CLNT-23..CLNT-31` and the pinned diff base

Nine rows appended to the `### Client Access (CLNT)` lane in
`.planning/REQUIREMENTS.md`, in the lane's existing `- [ ] **CLNT-NN**: …`
shape, adopting `20-RESEARCH.md` §Q7's wording. Each row names the Phase 20
criteria it serves and the `H-NN` rulings it derives from. A short preamble
records that the mapping to the ten criteria is deliberately not 1:1 and must
not be forced to be. Nine matching `| CLNT-NN | Phase 20 | Pending |` rows added
to the `## Traceability` table.

**The edit was made with the Edit tool only.** No `state.*` and no `roadmap.*`
GSD SDK writer was invoked at any point in this plan.

`20-BASE-COMMIT.txt` holds `9e4bd0e5c54c22133f32c108b96de3aebbf6dfae` alone on
its first line, followed by a comment naming what reads it — plan `20-08`'s
criterion-7 assertion, `git diff --stat <base>..HEAD -- src/ccf/client/`.

Verified: nine lane rows, nine traceability rows, every id present at least
twice, **zero** removed lines matching `CLNT-01..22`, and the base SHA resolves
via `git cat-file -t` as `commit`.

### Task 2 — `D-IMPL-163`

One entry appended to `docs/DECISIONS.md`, recording that `D-32` governs
producer **output** under `examples/` — a committed store file, a populated
graph, fixture data — and not a declared **input** document a fabric-side runner
interprets. It records the forcing collision (`D-32` versus `no-hardcoding`
covering `examples/` through `tools/lints/__main__.py::RULE_TREE_SCOPE`), the
measured boundary (the lint walk reads only Python modules, via
`tools/lints/__main__.py::main`'s `rglob("*.py")`), the precedent that predates
the ruling, what stays forbidden so the narrowing cannot widen, and both
rejected alternatives with their costs.

Verified: the entry exists, sits above `## Gate Log (D-GATE)`, names all four of
`D-32`, `H-04`, `CLNT-27` and `no-hardcoding`, introduces **zero** unanchored
`.py:NN` citations, and `git diff docs/DECISIONS.md | grep -c '^-[^-]'` returns
`0` — nothing was edited away.

**One observation recorded inside the entry rather than repaired.**
`D-IMPL-147` through `D-IMPL-162` have drifted *below* the
`## Gate Log (D-GATE)` heading, interleaved with the gate entries;
`D-IMPL-163` is placed correctly at the end of `## Open Decisions (D-IMPL)`,
which is also what the plan's acceptance criterion requires. The drift was not
repaired: moving sixteen entries would show as sixteen deletions in a log whose
whole discipline is that nothing is edited away.

### Task 3 — the declared input document

`examples/hw1-harness-clients/runner/scenario-rows.yaml` — six fictional,
domain-neutral companies keyed by the ROLE names
`examples/hw1-companies-over-revenue/deployment/scenario.yaml` declares
(`reference` / `name` / `revenue`), never hw1's raw source keys, so the runner
resolves the mapping through that document and the two cannot drift.

`tenant_id: hw1-demo`, read from the deployment's own `ccf_config.yaml` rather
than restated from memory. `observed_at: 2026-07-01T00:00:00+00:00`, fixed and
strictly before the `--as-of 2026-08-01T00:00:00+00:00` the runner pins, so
every seeded row is inside the temporal boundary and a moving clock cannot move
criterion 4's content address. Revenues are plain integers — never floats, which
`WireRequest` refuses.

Three rows strictly above `1000000000` (Kestrelmark Industries, Volanti
Logistics, Brightpath Materials) and three strictly below (Cindervale Foods,
Halcyon Textiles, Norwind Ceramics). None equal to the threshold, so the answer
cannot depend on whether the projection compares with `>` or `>=`.

**All seven acceptance criteria pass, and the marker assertions were sabotaged
rather than trusted.** The four `name` properties are what `20-03`'s and
`20-04`'s payload assertions rest on, so each was broken deliberately and
watched go red:

| Sabotage | Result |
| --- | --- |
| duplicate name | caught (`distinct`) |
| two-character name | caught (`min length`) |
| name that is a substring of another | caught (`substring`) |
| hex-only name (`deadbeef cafe`) | caught (`hex-only`) |
| chrome-word collision (`Revenue Partners`) | caught (`chrome`) |
| chrome-word collision (`Lineage Holdings`) | caught (`chrome`) |

Baseline passes, every sabotage fails. **Controls that could not be made to
fail: none.** The shipped, authoritative gate remains
`examples/hw1-harness-clients/runner/drive.py::marker_violations` in `20-03`;
this is its wave-1 preview.

The header comment records what the document is, the `D-IMPL-163` narrowing that
permits it, that the runner is an interpreter over it, that the keys are roles,
that it is not a Control Plane artifact and therefore carries no `$schema`, the
full reasoning for the `runner/` location and the `drive.py` name, and the four
marker properties with why each is load-bearing — so a later edit cannot quietly
break `20-03` by renaming a company to something generic.

**One self-correction inside this task, worth recording.** The first draft's
header cited `examples/external/00-hello-context/artifacts/events.yaml` as the
precedent. The retirement sweep then showed the new file had added an
**assigned** coupling row — 234→235 across 76 files, shape `comment`, owner plan
16-18 — because that precedent's tree is owned by a retirement plan. The plan
never asked for that citation in the header, and `D-IMPL-163` already carries the
precedent, so it was replaced with a citation to the **decision id**, per
`D-IMPL-144`'s rule that citations use the stable id rather than a path. After
the change the inventory is **byte-identical to the task-4 baseline**: the new
file introduces **zero** couplings.

### Task 4 — the retirement inventory, red to green

`make ci-core` was red at the phase's base commit, before a line of Phase 20
code existed, and Phase 20 was the cause. That is now fixed.

`.venv/bin/python tools/retirement_sweep.py --report` — no `PYTHONPATH` prefix
needed, as the plan measured.

**Before and after, and the diff's shape:**

| Measure | Before | After |
| --- | --- | --- |
| Coupling rows (assigned, `## Couplings`) | 234 across 75 files | 234 across 75 files |
| Rows outside the three swept trees | 143 across 47 files | 143 across 47 files |
| Rows by owning plan (16-02/16-15/16-17/16-18/17-08) | 9/23/41/103/58 | 9/23/41/103/58 |

**No row moved outside the count section, and no assigned row moved at all.**
The `## Couplings` section is **byte-identical** before and after, verified by
diffing it in isolation. Every changed line sits inside
`## Measured but not assigned`:

- Twelve **new** per-file rows for the Phase 20 planning tree — the eight
  `20-NN-PLAN.md` files plus `20-CONTEXT.md`, `20-DISCUSSION-LOG.md`,
  `20-RESEARCH.md` and `20-VALIDATION.md`.
- Three count bumps: `.planning/REQUIREMENTS.md` 14→15 (task 1's `CLNT-29`
  names `examples/s2-01-external-consumers/`), `.planning/ROADMAP.md` 8→14 and
  `.planning/STATE.md` 1→4.
- One count bump outside `.planning/**`, **named here as the plan instructs**:
  `docs/DECISIONS.md` 51→52, caused by task 2's own `D-IMPL-163` entry citing a
  path owned by retirement plan 16-18. It is a count change inside the same
  measured-but-not-assigned table, not a structural move, and it is exactly the
  self-staling the plan's `<retirement_currency>` section predicts.

The sweep was **re-run after task 3** and again after this SUMMARY, per the
plan's per-plan currency obligation.

Verified: `tools/docs_tests/test_retirement_sweep.py` **33 passed**;
`make gate-tools` **exit 0** (154 passed); regeneration **idempotent** (a second
run left the file byte-identical); `git diff --stat -- tools/retirement_sweep.py`
empty — the tool was not edited, so the report was not made current by moving
the goalposts.

## The wave-1 layout ruling, and the trap that produced it

**Preserved deliberately: this is the record of why the layout is what it is.**
Anyone who later wonders why the declared input is not in an `artifacts/`
directory, or why the runner is `drive.py` rather than the obvious `run.py`,
should read this before "tidying" either.

### The trap

Task 3 was originally written to create
`examples/hw1-harness-clients/artifacts/scenario-rows.yaml`. The document
authored to that path passed **every criterion the plan wrote for it**, and was
then rejected by `tests/examples/test_artifact_schema_headers.py`, an always-on
gate inside the `test` job:

```
FAILED …::test_every_covered_artifact_directory_sits_under_an_example_root
FAILED …::test_every_artifact_directory_passes_the_header_check[examples/hw1-harness-clients/artifacts]
```

**Failure A — the schema header.** Every `examples/**/artifacts/*.yaml` must
carry either a `# yaml-language-server: $schema=` first line or a
`# ccf-schema: deferred(<plan>)` marker, and the marker's use is bounded by a
named `PERMANENTLY_DEFERRED` constant that a test asserts set-equality against —
so using it is a deliberate test edit, which plan `20-01` declared out of scope.

**Failure B — the bijection, the hard one.** An *example root* is defined
mechanically as a directory **directly containing `run.py`**
(`EXAMPLE_ROOT_MARKER`); every covered `artifacts/` must sit directly under one,
and every example root must own one. `H-11` locks this example's root to the
three `client_*.py`, so it can never hold a `run.py` — a `ccf`-importing,
reader-visible module at the root is exactly what `H-11` exists to prevent.

### The landmine, measured before it detonated

The left side of the same bijection fires as soon as the runner ships. Measured
against a copy of the real tree with `runner/run.py` added:

```
=== CURRENT TREE ===
uncovered(left): []
orphaned(right): ['hw1-harness-clients/artifacts']

=== SIMULATED: runner/run.py ===
uncovered(left): ['hw1-harness-clients/runner']
orphaned(right): ['hw1-harness-clients/artifacts']
```

Naming the runner `run.py` makes `runner/` an example root in its own right,
which then demands **its own** `artifacts/`. The natural name for a runner is
precisely the one that breaks the gate. Catching this in wave 1 rather than in
wave 3 was the valuable part.

### Why it was not an executor fix

The gate module has **already ruled on this exact question, in writing**:
`tests/examples/test_artifact_schema_headers.py::test_a_single_file_config_example_is_outside_the_bijection`
records that plan `17-09` tried to widen `EXAMPLE_ROOT_MARKER` from the `run.py`
filename to a property, and that **measured, the widening cannot hold** — the
measurement was recorded instead of the widening. `H-12` independently forbids
weakening a rule to accommodate a file. Both obvious escapes were closed by
prior rulings, not by taste.

### Options put to Dave, and the ruling

| # | Option | Consequence |
| --- | --- | --- |
| **1** | **Move the document beside the runner and rename the runner** — `runner/scenario-rows.yaml`, `runner/drive.py`, no `artifacts/` anywhere | **Weakens nothing, edits no test, honours `H-11`, `H-12` and `D-IMPL-163`, and defuses the wave-3 landmine in the same stroke.** Cost: contradicts `20-01`'s original `must_haves` path; plans `20-02`…`20-08` need the path and runner filename updated. **RULED (Dave, 2026-08-20).** |
| 2 | Keep `artifacts/`, add a deferral marker plus a `PERMANENTLY_DEFERRED` entry, and exclude this example from the bijection | Fixes A by a sanctioned mechanism, fixes B only by putting a hole in a structural rule — what `H-12` names as the thing not to do, and what `17-09`'s recorded measurement argues against. Rejected. |
| 3 | Put `run.py` and `artifacts/` at the example root | Satisfies the gate as designed and **violates `H-11` outright**; `H-12`'s purity gate would then fail. Not viable. |
| 4 | Give the document a real JSON Schema with an `x-ccf-class-id` | Fixes A, does nothing for B, and asserts something false — the document is explicitly **not** a Control Plane artifact class (`D-IMPL-163`). Rejected. |

**Dave ruled Option 1.** The authoritative layout:

```
examples/hw1-harness-clients/
  README.md
  client_adk.py
  client_anthropic.py
  client_langgraph.py
  runner/
    drive.py              # NOT run.py — a run.py here makes runner/ an example root
    scenario-rows.yaml    # the declared input; no artifacts/ directory anywhere
    model_stub.py
```

The coordinator repaired plans `20-01`…`20-08` and `20-VALIDATION.md` at
`dc2c214`; `examples/external/00-hello-context/`'s own `run.py` and
`artifacts/events.yaml` were deliberately left untouched. Task 3 was then
completed against the rewritten plan.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — coupling introduced by my own header] the precedent citation was
re-pointed at a decision id**
- **Found during:** Task 3, by re-running the retirement sweep after writing the
  file.
- **Issue:** the header's path citation to the precedent document added an
  assigned coupling row (234→235 across 76 files) owned by retirement plan
  16-18. The plan did not ask for that citation, and `D-IMPL-163` already
  carries the precedent.
- **Fix:** cite the decision id instead of the path, per `D-IMPL-144`.
- **Files modified:** `examples/hw1-harness-clients/runner/scenario-rows.yaml`.
- **Result:** inventory byte-identical to the task-4 baseline; the new file
  introduces zero couplings.

### Rule 4 — architectural, escalated and ruled

**1. [Rule 4] `examples/hw1-harness-clients/artifacts/` refused by the
artifact-schema bijection gate**
- **Found during:** Task 3, by running the plan's own `<verification>` block
  (`.venv/bin/python -m pytest tests/examples -q`), which the plan lists but
  whose per-task criteria did not include.
- **Action:** stopped, measured both sides of the bijection including the
  wave-3 projection, left the tree green, escalated with four options.
- **Outcome:** Dave ruled Option 1; plans repaired at `dc2c214`; task 3
  completed against the rewritten plan. Full analysis preserved above.

## Threat Flags

None. This plan added no network endpoint, no auth path, no file-access pattern
and no schema at a trust boundary. `T-20-01` (tampering with
`.planning/REQUIREMENTS.md`) mitigated as planned — hand-edit only, with
`CLNT-01..22` asserted byte-unchanged. `T-20-02` (repudiation via
`docs/DECISIONS.md`) mitigated as planned — zero removed lines. `T-20-03`
(information disclosure via the row data) **accepted as planned** — six
fictional domain-neutral companies, no real entity, no credential, no PII.
`T-20-38` (repudiation via a hand-corrected inventory) mitigated as planned —
tool-generated, idempotency byte-compared, tool asserted unedited. `T-20-SC` did
not fire: **no package was installed by this plan.**

## Verification

Exit codes branched on rather than echoed:

| Check | Result |
| --- | --- |
| Task 3's seven acceptance criteria | all pass |
| Marker-property sabotage (6 mutations) | all 6 caught; none inert |
| `pytest tests/examples -q` | 386 passed, 37 skipped |
| `pytest tests/examples/test_artifact_schema_headers.py -q` | 25 passed — **bijection green, no `artifacts/` anywhere** |
| `pytest tests/invariants/test_citation_coverage.py -q` | 5 passed |
| `python -m tools.lints --all` | exit 0 |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` | 33 passed |
| `make gate-tools` | **exit 0**, 154 passed |
| retirement sweep idempotency | byte-identical on second run |
| `git diff --stat 9e4bd0e..HEAD -- src/` | empty — this plan touched no source |
| `git diff --stat -- tools/retirement_sweep.py` | empty |

`.planning/STATE.md` and `.planning/ROADMAP.md` were **not** modified by this
plan.

## Success Criteria

- [x] Nine `CLNT-23..CLNT-31` rows exist in the lane and in the traceability table
- [x] `D-IMPL-163` records the `D-32` narrowing, appended, nothing edited away
- [x] `20-BASE-COMMIT.txt` holds a resolvable SHA
- [x] `examples/hw1-harness-clients/runner/scenario-rows.yaml` parses to six role-keyed rows split 3/3 around the threshold
- [x] `pytest tests/examples -q` and the citation invariant are both green
- [x] `docs/surface/examples/RETIREMENT-COUPLINGS.md` is regenerated and `make gate-tools` is exit 0 — the phase opens on a green currency baseline instead of a red one

## Self-Check: PASSED

Files asserted present:

- `FOUND: .planning/phases/20-…/20-BASE-COMMIT.txt`
- `FOUND: .planning/REQUIREMENTS.md` (CLNT-23..31 present, 9 + 9)
- `FOUND: docs/DECISIONS.md` (D-IMPL-163 present, above the gate log)
- `FOUND: examples/hw1-harness-clients/runner/scenario-rows.yaml`
- `FOUND: docs/surface/examples/RETIREMENT-COUPLINGS.md` (regenerated, current)
- `ABSENT BY DESIGN: examples/hw1-harness-clients/artifacts/` — the ruling

Commits asserted present: `03a5ec6`, `a0cfb5f`, `c04dc02`, `34287cf`.
