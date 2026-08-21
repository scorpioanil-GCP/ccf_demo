---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 01
subsystem: planning-foundations
tags: [requirements, decisions, retirement-sweep, blocked]
status: BLOCKED — 3 of 4 tasks complete; task 3 raised a Rule 4 architectural stop
requires: []
provides:
  - CLNT-23..CLNT-31 requirement rows
  - D-IMPL-163 (the D-32 narrowing)
  - the phase's pinned diff base for criterion 7
  - a green retirement-currency baseline
affects:
  - .planning/REQUIREMENTS.md
  - docs/DECISIONS.md
  - docs/surface/examples/RETIREMENT-COUPLINGS.md
tech-stack:
  added: []
  patterns: [hand-edited planning documents, append-only decision log, tool-generated inventory]
key-files:
  created:
    - .planning/phases/20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a/20-BASE-COMMIT.txt
  modified:
    - .planning/REQUIREMENTS.md
    - docs/DECISIONS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
  not-created:
    - examples/hw1-harness-clients/artifacts/scenario-rows.yaml
decisions:
  - D-IMPL-163 — D-32 narrowed to producer OUTPUT; a declared INPUT document under examples/ is permitted
metrics:
  tasks-planned: 4
  tasks-complete: 3
  commits: 3
  completed: 2026-08-20
---

# Phase 20 Plan 01: Paper Foundations Summary

Minted `CLNT-23..CLNT-31`, recorded the `D-32` narrowing as `D-IMPL-163`, pinned
the criterion-7 diff base, and turned the phase's retirement-currency gate from
red to green — but **task 3 is blocked by a shipped, always-on CI gate that
structurally refuses the document the plan mandates, at the location the plan
mandates.** The blocker is a Rule 4 architectural stop, measured rather than
inferred, and it also carries a landmine for plan `20-03`.

## Status: BLOCKED

Three of four tasks are complete and committed. Task 3 is not, and the working
tree is deliberately left **green** rather than carrying a red artifact.

| Task | Name | Status | Commit |
| --- | --- | --- | --- |
| 1 | Mint `CLNT-23..31`, pin the diff base | Complete | `03a5ec6` |
| 2 | Record the `D-32` narrowing as `D-IMPL-163` | Complete | `a0cfb5f` |
| 3 | Author `scenario-rows.yaml` | **BLOCKED** | — |
| 4 | Regenerate the retirement inventory | Complete | `c04dc02` |

Task 4 was run last, as the plan requires, and after tasks 1 and 2 had finished
changing the tree.

## What shipped

### Task 1 — `CLNT-23..CLNT-31` and the pinned diff base

Nine rows appended to the `### Client Access (CLNT)` lane in
`.planning/REQUIREMENTS.md`, in the lane's existing
`- [ ] **CLNT-NN**: …` shape, adopting `20-RESEARCH.md` §Q7's wording. Each row
names the Phase 20 criteria it serves and the `H-NN` rulings it derives from. A
short preamble records that the mapping to the ten criteria is deliberately not
1:1 and must not be forced to be. Nine matching
`| CLNT-NN | Phase 20 | Pending |` rows added to the `## Traceability` table.

**The edit was made with the Edit tool only.** No `state.*` and no `roadmap.*`
GSD SDK writer was invoked at any point in this plan.

`.planning/phases/20-…/20-BASE-COMMIT.txt` holds
`9e4bd0e5c54c22133f32c108b96de3aebbf6dfae` alone on its first line, followed by
a comment naming what reads it — plan `20-08`'s criterion-7 assertion,
`git diff --stat <base>..HEAD -- src/ccf/client/`.

Verified: nine lane rows, nine traceability rows, every id present at least
twice, **zero** removed lines matching `CLNT-01..22`, and the base SHA resolves
via `git cat-file -t` as `commit`.

### Task 2 — `D-IMPL-163`

One entry appended to `docs/DECISIONS.md`, recording that `D-32` governs
producer **output** under `examples/` — a committed store file, a populated
graph, fixture data — and not a declared **input** document a fabric-side runner
interprets. It records the forcing collision (`D-32` versus `no-hardcoding`
covering `examples/` through
`tools/lints/__main__.py::RULE_TREE_SCOPE`), the measured boundary (the lint
walk reads only Python modules, via `tools/lints/__main__.py::main`'s
`rglob("*.py")`), the `00-hello-context/artifacts/events.yaml` precedent that
predates the ruling, what stays forbidden so the narrowing cannot widen, and
both rejected alternatives with their costs.

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
  `docs/DECISIONS.md` 51→52, caused by task 2's own `D-IMPL-163` entry citing
  `examples/external/00-hello-context/artifacts/events.yaml`, a path owned by
  retirement plan 16-18. It is a count change inside the same
  measured-but-not-assigned table, not a structural move, and it is exactly the
  self-staling the plan's `<retirement_currency>` section predicts.

Verified: `tools/docs_tests/test_retirement_sweep.py` **33 passed**;
`make gate-tools` **exit 0** (154 passed); regeneration **idempotent** (a second
run left the file byte-identical); `git diff --stat -- tools/retirement_sweep.py`
empty — the tool was not edited, so the report was not made current by moving
the goalposts.

## BLOCKER — task 3: the mandated document collides with a shipped CI gate

**This needs Dave's ruling. It is a Rule 4 architectural stop, and it cannot be
resolved without either contradicting a locked `H-NN` ruling or weakening a
shipped rule that `H-12` forbids weakening.**

### What happened

`examples/hw1-harness-clients/artifacts/scenario-rows.yaml` was authored to the
plan's full specification and **passes every one of the plan's own acceptance
criteria**, including all four `name`-marker properties. It was then rejected by
`tests/examples/test_artifact_schema_headers.py`, an always-on gate inside the
`test` job that the plan did not anticipate. Two independent failures:

```
FAILED tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root
FAILED tests/examples/test_artifact_schema_headers.py::test_every_artifact_directory_passes_the_header_check[examples/hw1-harness-clients/artifacts]
```

**Failure A — the schema header.** Every `examples/**/artifacts/*.yaml`
must carry either a `# yaml-language-server: $schema=` first line or a
`# ccf-schema: deferred(<plan>) <reason>` marker. There is no schema for this
document, so the marker is the mechanism — but
`tests/examples/test_artifact_schema_headers.py` asserts that the set of
documents carrying a marker **equals** its named `PERMANENTLY_DEFERRED` dict, so
using it requires a deliberate edit to that test constant with a reason. That is
a *sanctioned* mechanism, not a weakening — but plan `20-01` is declared
explicitly as "no Python and no test change".

**Failure B — the bijection. This is the hard one.** The gate enforces a
two-sided bijection: an **example root** is a directory *directly containing a
file named `run.py`*; every covered `artifacts/` directory must sit directly
under one, and every example root must own one. `examples/hw1-harness-clients/`
has no `run.py`, so its `artifacts/` is an orphan.

**Under `H-11` it can never have one.** `H-11` locks the example root to holding
only the three `client_*.py`, with the `ccf`-importing runner in a subdirectory
— and that is load-bearing, because it is precisely what puts the runner
structurally outside `H-12`'s purity gate. A `run.py` at the root would be a
`ccf`-importing, reader-visible module, which is the exact thing `H-11` exists
to prevent.

### The landmine for plan `20-03`, measured not predicted

The left side of the same bijection fires as soon as the runner ships. Measured
against a copy of the real tree with `runner/run.py` added:

```
=== CURRENT TREE ===
uncovered(left): []
orphaned(right): ['hw1-harness-clients/artifacts']

=== SIMULATED: plan 20-03 ships runner/run.py ===
uncovered(left): ['hw1-harness-clients/runner']
orphaned(right): ['hw1-harness-clients/artifacts']
```

Naming the runner's module `run.py` makes `runner/` an example root, which then
**requires its own `examples/hw1-harness-clients/runner/artifacts/`**. So the
runner's filename is now load-bearing for a gate, and plan `20-03` was not
written knowing that.

### Why this is not an executor fix

The gate module has *already ruled on this exact question, in writing.*
`tests/examples/test_artifact_schema_headers.py::test_a_single_file_config_example_is_outside_the_bijection`
records that plan `17-09` tried to widen `EXAMPLE_ROOT_MARKER` from the `run.py`
filename to a property, and that **measured, the widening cannot hold** — the
measurement was recorded instead of the widening. `H-12` independently forbids
weakening a rule to accommodate a file. So the two obvious escapes are both
closed by prior rulings, not merely by taste.

### Options, with consequences

| # | Option | Consequence |
| --- | --- | --- |
| **1** | **Move the document out of `artifacts/`** — e.g. `examples/hw1-harness-clients/runner/scenario-rows.yaml` — and name the runner's module something other than `run.py` (e.g. `runner/seed.py`) | **Weakens nothing, edits no test, honours `H-11`, `H-12` and `D-IMPL-163`, and defuses the `20-03` landmine in the same stroke.** The `artifacts/` glob and the `run.py` predicate both simply never see this example. Cost: contradicts plan `20-01`'s `must_haves`, its `key_links` and four acceptance criteria, all of which hard-code `examples/hw1-harness-clients/artifacts/scenario-rows.yaml`; plans `20-02`/`20-03`/`20-04` need the path and the runner filename updated. **Recommended.** |
| 2 | Keep `artifacts/`, add a `# ccf-schema: deferred(20-01)` marker plus a `PERMANENTLY_DEFERRED` entry, and add `hw1-harness-clients` to an exclusion in the bijection | Fixes A by a sanctioned mechanism, but fixes B only by putting a hole in a structural rule — which is what `H-12` names as the thing not to do, and what `17-09`'s recorded measurement argues against. Also still needs the `20-03` runner-filename decision separately. |
| 3 | Put `run.py` and `artifacts/` at the example root | Satisfies the gate exactly as designed, and **violates `H-11` outright** — a `ccf`-importing reader-visible module at the root, which `H-12`'s purity gate would then fail. Not viable. |
| 4 | Give the document a real JSON Schema under `docs/schemas/` with an `x-ccf-class-id` | Fixes A properly, does nothing for B, and asserts something false: the document is explicitly **not** a Control Plane artifact class (`D-IMPL-163`), so giving it an artifact schema header would make it claim a class it does not have — the exact failure `test_a_single_file_config_example_is_outside_the_bijection` already refuses for `binding.yaml`. |

Option 1 is the only one that weakens nothing, and the ruling needs to cover
**both** the document's location and the runner module's name, because the
bijection ties them together.

### State left behind

The authored document is preserved at
`/tmp/claude-1000/-home-parkave-ccf-code/f22dffaf-289d-450d-8ac5-6cfd98427a35/scratchpad/scenario-rows.yaml`
— it is complete and passes every plan criterion; only its path is in question.
`examples/hw1-harness-clients/` was removed entirely (it was untracked and never
committed, removed by explicit path with `rm -f` and `rmdir`; no `git clean`, no
`git stash`, no reset). **The tree is green.**

## Deviations from Plan

### Auto-fixed issues

None. No Rule 1, 2 or 3 fix was required.

### Rule 4 — architectural, escalated

**1. [Rule 4] `examples/hw1-harness-clients/artifacts/` is refused by the
artifact-schema bijection gate**
- **Found during:** Task 3, by running the plan's own `<verification>` block
  (`.venv/bin/python -m pytest tests/examples -q`), which the plan lists but
  whose per-task criteria do not include.
- **Issue:** the plan's mandated path is structurally incompatible with a
  shipped always-on gate, and `H-11` forecloses the gate's own remedy.
- **Action:** stopped, measured both sides of the bijection including the
  `20-03` projection, left the tree green, escalated with four options.
- **Files modified:** none.

## Threat Flags

None. This plan added no network endpoint, no auth path, no file-access pattern
and no schema at a trust boundary. Threat `T-20-01` (tampering with
`.planning/REQUIREMENTS.md`) was mitigated as planned — hand-edit only, with
`CLNT-01..22` asserted byte-unchanged. `T-20-02` (repudiation via
`docs/DECISIONS.md`) was mitigated as planned — zero removed lines. `T-20-38`
(repudiation via a hand-corrected inventory) was mitigated as planned —
tool-generated, idempotency byte-compared, tool asserted unedited. `T-20-SC` did
not fire: **no package was installed by this plan.**

## Verification

Run against the tree at `c04dc02`, exit codes branched on rather than echoed:

| Check | Result |
| --- | --- |
| `pytest tests/invariants/test_citation_coverage.py -q` | 5 passed |
| `pytest tests/examples -q` | 385 passed, 37 skipped (with task 3's file absent) |
| `pytest tests/examples/test_artifact_schema_headers.py -q` | 25 passed |
| `python -m tools.lints --all` | exit 0 |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` | 33 passed |
| `make gate-tools` | **exit 0**, 154 passed |
| `git diff --stat -- src/` | empty — this plan touched no source |
| `git diff --stat -- tools/retirement_sweep.py` | empty |

`.planning/STATE.md` and `.planning/ROADMAP.md` were **not** modified by this
plan.

## Success Criteria

- [x] Nine `CLNT-23..CLNT-31` rows exist in the lane and in the traceability table
- [x] `D-IMPL-163` records the `D-32` narrowing, appended, nothing edited away
- [x] `20-BASE-COMMIT.txt` holds a resolvable SHA
- [ ] **`examples/hw1-harness-clients/artifacts/scenario-rows.yaml` parses to six role-keyed rows split 3/3 around the threshold** — authored and passing every plan criterion, but **not committed**; blocked on the ruling above
- [x] `pytest tests/examples -q` and the citation invariant are both green
- [x] `docs/surface/examples/RETIREMENT-COUPLINGS.md` is regenerated and `make gate-tools` is exit 0 — the phase now opens on a green currency baseline instead of a red one

## Self-Check: PASSED

Files asserted present:

- `FOUND: .planning/phases/20-…/20-BASE-COMMIT.txt`
- `FOUND: .planning/REQUIREMENTS.md` (CLNT-23..31 present, 9 + 9)
- `FOUND: docs/DECISIONS.md` (D-IMPL-163 present, above the gate log)
- `FOUND: docs/surface/examples/RETIREMENT-COUPLINGS.md` (regenerated, current)
- `ABSENT BY DESIGN: examples/hw1-harness-clients/artifacts/scenario-rows.yaml`
  — see the blocker above

Commits asserted present: `03a5ec6`, `a0cfb5f`, `c04dc02`.
