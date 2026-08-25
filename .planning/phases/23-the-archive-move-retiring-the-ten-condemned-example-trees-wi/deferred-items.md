# Deferred items — phase 23

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary: an executor that closes a gap it discovers on the way past has turned
a planned wave into an unplanned one, and the fix ships without the decision it
needed.

## From plan `23-03`

**1. The `$schema` header gate is blind to a nested `artifacts/<subdir>/`, and
three shipped documents are in that blind spot today.**

`tools/check_schema_headers.py::ARTIFACT_GLOBS` matches one level under
`artifacts/`, so a document at `artifacts/<subdir>/*.yaml` is never discovered.
Measured on the pre-move tree:

```bash
# every file in the ten condemned trees whose FIRST line is a $schema header: 216
# of those, matched by examples/**/artifacts/*.yaml: 213
# NOT matched:
examples/03-harness-portability/artifacts/agents/agent-definition.yaml
examples/03-harness-portability/artifacts/agents/debt-profile.yaml
examples/03-harness-portability/artifacts/agents/policy-regime.yaml
```

All three carry `../../../../docs/schemas/…` headers and all three resolve
today, so nothing is currently wrong — but nothing is currently *checking*
either, and after the archive move all three need the same extra `../` as the
213 the gate does see, with the gate unable to say whether they got it.

- **Pre-existing.** Not caused by Phase 23; the glob has had this shape since
  plan `15-12`. Phase 23 only makes it consequential, because Wave 5's header
  repair will be gated by a check that cannot see three of its subjects.
- **Why it is not a one-character fix.** Deepening the pattern to
  `artifacts/**/*.yaml` puts `…/artifacts/agents` into
  `covered_artifact_directories`. Its parent is `…/artifacts`, which is not an
  example root (no `run.py`), so
  `tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root`
  goes red on a correct tree. Closing the gap therefore means deciding what
  the bijection's right side means for nested artifact directories — a design
  call, not a widening.
- **Carried to Wave 5 as a caveat, not as work**: `23-05`'s header repair
  should repair all **216**, and should record that the gate's green covers
  213 of them.

**2. A lowered count floor is visible to exactly one thing, and it is the
wrong signal.**

Sabotage `S-F3` set `MINIMUM_IMPLEMENTATIONS` to `0`. The module itself passed
(17 passed) as the plan predicted. What the plan did *not* predict is that
`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
FAILED — `tools/retirement_sweep.py::_floors` records each floor's value in the
coupling report, so lowering one makes the committed report stale.

- The detection is real but weak, and weak in a specific way: the message says
  *the report is stale*, not *a floor was lowered*. The reflex it invites is
  `retirement_sweep.py --report`, which turns it green and prints
  `floor 0, 14 witnesses, headroom 14` into a committed file nobody re-reads.
- **Not fixed here.** A gate that refuses a floor DECREASE would need to know
  the previous value, which means pinning floors in a second place — a real
  design decision about where the authority for a floor lives.

**3. The two scan roots in `tests/products/test_gate_two_call_shape.py` are
not as independent as their two constants suggest.**

`_plan_classes()` is derived from `SCANNED_TREES` and is consulted by
`_is_plan_construction`, so the binder scan — which reads
`BINDER_SCANNED_TREES` — depends on `SCANNED_TREES` as well. Measured under
sabotage `S-F2`: dropping `"examples"` from `SCANNED_TREES` alone cost the
binder scan one projecting body (14 → 13), even though `BINDER_SCANNED_TREES`
was untouched.

- **No defect today**, and no action owed by Phase 23: both constants were
  widened together, which is what the coupling requires. Recorded because a
  future reader widening one and not the other would get a partial result with
  no message saying why.

## From plan `23-04`

**4. The citation lint resolves a moved-away path by SUFFIX, so a stale
`examples/…` citation silently keeps passing after the archive move.**

`tools/lints/citations.py::resolve_cited` tries the literal path first and,
failing that, accepts a citation as a **suffix** of exactly one indexed repo
file. After the move, `examples/04-cross-process/producer_child.py` does not
exist — but `archive/examples/04-cross-process/producer_child.py` ends with
`/examples/04-cross-process/producer_child.py`, it is the only candidate, and
the citation resolves and is reported as *checked and passing*.

Measured, on the pre-move tree (`git archive HEAD~1`) against the post-move
tree, with the same checker and the `--base` flag proven live by an empty-tree
control (0 matched) and a `src`-only control (353 matched, 317 unresolvable):

```bash
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations --report --base <premove>
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations --report --base .
# both, byte-identical, all eight lines:
#   citations: 1762 matched in 1111 files (675 files exempt as dated records)
#     checked and passing: 1300   findings: 0   explicitly historical: 50
#     UNCHECKED — no anchor: 345  anchor not resolvable: 13
#     path ambiguous: 15          path unresolvable: 39
```

- **This is a SECOND, stronger hole than the one `D-07`/`D-IMPL-192` records.**
  That entry's measured case is a citation repointed at a *non-existent*
  `archive/…` path, which resolves to nothing and is therefore **unchecked**.
  This case is the mirror: a citation left at the *old* `examples/…` path,
  which resolves to the moved file and is therefore **checked and green**.
  Both are silent; only the second makes a green gate assert something false.
- **Consequence for `23-06`.** The four permitted `D-07` citation edits are
  still correct and still owed, but **no gate goes red if they are skipped**,
  and none goes red if they are made wrongly. `23-06` must not treat a green
  `make lint` as evidence that it made them.
- **Not fixed here.** Narrowing `resolve_cited` is a design call about what a
  suffix citation means — the fallback exists deliberately so `manifest.py`
  and `deployment/manifest.py` resolve — and tightening it would need a rule
  for when a citation's leading segment names a tree it must actually be in.
  That is the durable fix `D-IMPL-192` already backlogs, not a widening.

---

## Wave 5 (`23-05`) — three prose drifts nobody owns, and one that nobody may

**Not fixed here.** All four name paths the move relocated, none is a control,
and each sits in a file outside this plan's `files_modified`. Recorded rather
than fixed so `23-12` can rule on them with the population in front of it.

### 1. Five stale `examples/…` prose references inside `tests/examples/test_artifact_schema_headers.py`

```bash
grep -n 'examples/03-harness-portability/legs\|examples/external/00-hello-context\|examples/08-e2e-demo' \
  tests/examples/test_artifact_schema_headers.py | grep -v archive
#   55, 61, 62, 123, 519   (five lines; line 3 names plan 15-12's original scope and is history, not drift)
```

The module docstring and one control's docstring describe the tree in prose and
still say `examples/…`. The **constants** are re-pointed (this plan, task 2) and
every assertion is green; only the narration drifted. **This matters because no
later plan in the phase owns this module** — `grep -l test_artifact_schema_headers
.planning/phases/23-*/23-*-PLAN.md` returns `23-03` and `23-05` and nothing else.
Left alone because plan `23-05` scopes task 2 to *"the path strings only"*.

### 2. `examples/external/README.md:50` still lists `00-hello-context` as a resident

```bash
git ls-files examples/external   # examples/external/README.md   (the only survivor)
grep -n '00-hello-context' examples/external/README.md   # line 50, an index-table row
```

The tree moved to `archive/examples/external/00-hello-context`; the directory
it left behind keeps a README whose index table still lists it. `D-09` requires
the external example be *"marked historical"*, and this is the surviving half
of that surface. Not in any plan's `files_modified`.

### 3. Sixteen archived prose lines tell a reader to run a path that is gone

```bash
grep -rn 'python examples/' archive/examples/ | wc -l               # 16
grep -rn 'python examples/' archive/examples/*/[a-z]*.py \
  archive/examples/*/*/[a-z]*.py | wc -l                            # 6, in .py docstrings
```

e.g. the module docstring of
`archive/examples/04-cross-process/producer_child.py` — *"Run by `run.py`
as `python examples/04-cross-process/producer_child.py`"*. Task 1 was scoped to
*"only the `parents[N]` index; no other line in any of the four files moves"*,
and `D-04` deletes the `make` targets anyway, so the invitation-to-run prose is
arguably wrong in a second way. Untouched.

### 4. Three headered documents sit outside the header gate — **pre-existing, and NOT to be fixed here**

`archive/examples/03-harness-portability/artifacts/agents/{agent-definition,
debt-profile,policy-regime}.yaml` carry `$schema` headers (all three repaired by
this plan) but are **one level below** `ARTIFACT_GLOBS`' `*/artifacts/*.yaml`.
Pre-existing since plan 15-12. `tools/check_schema_headers.py::ARTIFACT_GLOBS` already
carries a note that deepening the glob *"would turn the bijection's right side red"*,
so this is a real decision, not a one-character fix. Already logged above by
plan `23-03`; repeated here only because this plan measured the exact three.

---

## Logged by plan 23-07

### 5. **BLOCKING FINDING, introduced by plan 23-06 and unreported there** — a Phase-20 fence goes RED on the `D-IMPL-192` permitted edit

`tests/examples/test_hw1_harness_clients_readme.py::test_criterion_seven_no_sdk_mechanism_ships_at_all`
runs `git diff --stat <phase-20-base>..HEAD -- src/` and asserts the result is
empty. It is not empty any more:

```bash
B=$(head -1 .planning/phases/20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a/20-BASE-COMMIT.txt)
git diff --stat $B..2256526^ -- src/    # EMPTY
git diff --stat $B..2256526  -- src/    #  src/ccf/products/bind.py | 2 +-
git diff --stat $B..HEAD     -- src/    #  src/ccf/products/bind.py | 2 +-
```

The bisect is exact: empty at `2256526^`, non-empty at `2256526` — plan
`23-06`'s first `D-07` citation edit. `23-06-SUMMARY.md` does not mention this
test; the wave verified its four edits against the resolver-seam gate and the
whole-tree run that would have surfaced it was not part of that plan.

**Why `D-11`'s "the scope fence is SAFE" (23-CONTEXT `code_context`) does not
cover it:** `D-IMPL-188` bounded the *`test_requirement_ledger.py`* assertions
to `base..951eb4a`. This assertion is a different one and is still `base..HEAD`,
unbounded, so every future commit is inside its window.

**Not fixed here, deliberately.** The test's own docstring instructs: *"A
non-empty result here is a **blocking finding to report**, never a reason to
narrow this assertion back to the client surface."* `D-IMPL-192` explicitly
authorised the edit that trips it, so the two documents now contradict each
other and the reconciliation is a ruling, not an executor's edit — bound the
window the way `D-IMPL-188` bound its twin, or record the permitted edit as an
allowance. **Dave's, and owed before the phase closes.**

### 6. Criterion 12's `25 of 31` does not reproduce — the measured figure is **19 of 31**

```bash
git ls-files tests/examples | wc -l                                      # 31
git grep -lE 'archive/examples/(00-quickstart|…|external/00-hello-context)|"archive" / "examples"' \
    -- tests/examples/ | wc -l                                           # 19
# and at PHASE_BASE, with the pre-move spelling, the same predicate:      19
```

`23-RESEARCH.md` §14.5 already flagged the figure as unverified by the
researcher. It is now measured, at `PHASE_BASE` and at `HEAD`, and it is 19.
`tests/examples` collects **519** (515 at `PHASE_BASE` plus wave 3's four named
additions). Plan `23-11` must write the measured figures into the `DOCS-17`
cell, not the carried ones.
