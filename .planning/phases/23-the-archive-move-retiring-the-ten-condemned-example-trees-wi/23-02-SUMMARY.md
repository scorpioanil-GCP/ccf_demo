---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 02
subsystem: publication boundary and prose path walk — the two mechanism fixes the move cannot happen without
tags: [DOCS-17, D-IMPL-194, criterion-17, criterion-18, publish-scan, path-token, phase-base]
status: complete
requires:
  - phase: 23-01
    provides: PHASE_BASE b87fe58 and the 4223 collect total this plan's task 1 starts from
provides:
  - the phase base measured by OBSERVED foreground runs — 4105 passed / 118 skipped / 0 failed
  - a three-chunk test plan with disjointness and set-equality PROVEN, for 23-12 to re-use
  - criterion 17 — the archive root admitted to the publication allowlist, and the allowlist GUARDED for the first time
  - criterion 18 — PATH_TOKEN no longer strips a leading archive/, with controls in BOTH directions
  - proof that both widenings are no-ops on a tree where archive/ does not exist
affects:
  - 23-04 through 23-07 (the include and prose re-point cannot go green without criterion 17)
  - 23-05 / criterion 5 (its independent witness was RED on a correct tree until criterion 18 landed)
  - 23-08 (its sabotage S-4 re-runs the guard this plan added, over a tree that depends on it)
  - 23-12 (re-uses this chunk plan for criterion 15, and gates criterion 7 against 4105 / 118)
tech-stack:
  added: []
  patterns: [red-before-green-by-sabotage, every-figure-carries-its-command, proven-chunk-plan, narrow-prefix-over-inherited-root]
key-files:
  created:
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/23-02-SUMMARY.md
  modified:
    - tools/publish_scan.py
    - tools/publish_scan_tests/test_publish_scan.py
    - tools/docs_tests/test_no_stale_example_paths.py
    - docs/surface/examples/RETIREMENT-COUPLINGS.md  # generated; regenerated twice, LAST at this commit
decisions:
  - "The allowlist member is `archive/examples/`, not `archive/` — the broad form admits every future archive sibling by inheritance"
  - "PATH_TOKEN takes an `archive/examples` ALTERNATION BRANCH, not a widened lookbehind — the lookbehind spelling blinds the check entirely, and S-18b proves it"
  - "The correct-tree control uses a SYNTHETIC repo root, because on today's un-moved tree a stripped token resolves by accident and the control would pass vacuously"
  - "Sabotage restore is by inverse mutation or by `git checkout --` ONLY after the fix is committed — an uncommitted fix is silently destroyed by the restore"
requirements-completed: []
metrics:
  duration: ~70 min
  completed: 2026-08-24
  tasks: 3
  commits: 5
---

# Phase 23 Plan 02: Criteria 17 and 18 — the two mechanism fixes, measured base first — Summary

**The phase base was measured rather than computed — `4105 passed / 118 skipped
/ 0 failed`, summed from three foreground chunks whose coverage was PROVEN
disjoint and set-equal to the full collection before a single test ran — and
both mechanism fixes landed with eight sabotages watched RED, every prediction
holding.** Nothing moved. `archive/` still does not exist, and both widenings
are proven no-ops against that fact rather than against an argument.

---

## Task 1 — the base, by observed runs

### The full collection

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest --collect-only -q > collect-full.txt 2>&1
# EXIT=0
tail -3 collect-full.txt
# 4223 tests collected in 5.16s
```

**4223**, reproducing 23-01's figure independently.

### The chunk plan, PROVEN before anything ran

Three chunks over the top-level `tests/` entries, balanced by collected count
(greedy descending fill):

| Chunk | Members | Collected |
|---|---|---:|
| **A** | `tests/examples` `tests/halflife` `tests/graph` `tests/controlplane` `tests/http_api` `tests/cli` `tests/authz` `tests/lints` `tests/gates` `tests/test_surface_completeness.py` `tests/assembly` `tests/perf_smoke` `tests/test_smoke.py` | 1407 |
| **B** | `tests/products` `tests/deployment` `tests/invariants` `tests/crossproc` `tests/replay` `tests/properties` `tests/peering` `tests/projection` `tests/mcp` `tests/harness` `tests/operators` `tests/perf_synth` `tests/spikes` | 1408 |
| **C** | `tests/client` `tests/conformance` `tests/agents` `tests/skills` `tests/hitl` `tests/workflow` `tests/integration` `tests/contracts` `tests/perf_gate` `tests/test_surface_shape_capture.py` `tests/signal_layer` `tests/test_surface_drift.py` | 1408 |

Coverage proven, not assumed:

```bash
for f in full A B C; do grep -E '^tests/.*::' collect-$f.txt | sort > ids-$f.txt; done
comm -12 ids-A.txt ids-B.txt | wc -l        # 0
comm -12 ids-A.txt ids-C.txt | wc -l        # 0
comm -12 ids-B.txt ids-C.txt | wc -l        # 0
cat ids-A.txt ids-B.txt ids-C.txt | sort > ids-union.txt
wc -l < ids-union.txt                       # 4223
sort -u ids-union.txt | wc -l               # 4223   (no duplicates)
comm -23 ids-union.txt ids-full.txt | wc -l # 0      (nothing extra)
comm -13 ids-union.txt ids-full.txt | wc -l # 0      (nothing missed)
diff -q ids-union.txt ids-full.txt          # set-equal: YES
```

`1407 + 1408 + 1408 = 4223`. **Pairwise disjoint, union set-equal to the full
collection.** `23-12` can re-use this plan verbatim for criterion 15.

### The runs — foreground, one chunk per call

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q $CHUNK_A
# 1348 passed, 59 skipped, 9 warnings in 287.90s (0:04:47)     EXIT=0   real 4m51s
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q $CHUNK_B
# 1408 passed, 104 warnings in 202.56s (0:03:22)               EXIT=0   real 3m25s
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q $CHUNK_C
# 1349 passed, 59 skipped, 4 warnings in 88.92s (0:01:28)      EXIT=0   real 1m31s
```

**Summed: `4105 passed / 118 skipped / 0 failed`.**
`4105 + 118 = 4223`, which reconciles with the collection.

**This is criterion 7's pinned figure exactly, and it had never been observed
in a run before this task** — `23-RESEARCH.md` §14.2 records that the figure
was arithmetic on the 22.1 baseline plus one reproduced failure. It is now a
measurement. **No deviation to report; nothing was absorbed.**

The longest chunk is under five minutes, comfortably inside the ~10-minute
ceiling at which background jobs die on this host. Every run was foreground.

### The other legs, each run separately, no pipe

| Leg | Command | Exit |
|---|---|---:|
| lint | `make lint` | **0** |
| typecheck | `make typecheck` → *Success: no issues found in 211 source files* | **0** |
| gate-tools | `make gate-tools` → `406 passed` + `313 passed` | **0** |
| docs-strict step 1 | `python tools/publish_scan.py --pre-build` → 0 findings | **0** |
| docs-strict step 2 | `python tools/publish_scan.py docs/schemas` → 0 findings | **0** |
| docs-strict step 3 | `python -m mkdocs build --strict` | **0** |
| docs-strict step 4 | `python tools/publish_scan.py site` → 0 findings | **0** |
| lints runner | `python -m tools.lints --all` | **0** |

Exit codes captured with no pipe at all, per §14's measurement hazard. **`make
lint` and `python -m tools.lints --all` are the same command** — the Makefile
recipe is literally the latter — so they are one leg reported twice, not two
independent signals. Recorded rather than presented as corroboration.

`make ci`'s six legs are `lint`, `typecheck`, `test`, `gate-tools`, `examples`
and `docs-strict`. Five of the six are measured above; **`examples` was not
run in this plan** — it is criterion 15's, owed by `23-12`, and this plan's
`must_haves` names `ci-core` and `gate-tools`.

---

## Task 2 — criterion 17: the archive root admitted, and the allowlist guarded

### The defect, re-measured at PHASE_BASE

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -c "from tools.publish_scan import include_escapes, INCLUDE_ALLOWED_PREFIXES; ..."
# INCLUDE_ALLOWED_PREFIXES = ('examples/', 'public/', 'perf/baselines/')
# 'archive/examples/00-quickstart/run.py:boot'          include_escapes=True    <-- every re-pointed include is a pub04 violation
# 'examples/00-quickstart/run.py:boot'                  include_escapes=False
# 'docs/schemas/ccf.agent.json'                         include_escapes=True
# 'src/ccf/products/bind.py'                            include_escapes=True
# 'archive/secrets/x.md'                                include_escapes=True
```

And the unguarded half, re-verified rather than accepted from the ruling:

```bash
git grep -n 'INCLUDE_ALLOWED_PREFIXES' -- .
# only tools/publish_scan.py (3 sites) and planning/docs PROSE.
# ZERO test files. The default-deny publication boundary carried no guard.
```

### RED before GREEN

The guard went in first, against the un-widened tuple:

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/publish_scan_tests -q
# FAILED ...::test_the_publication_allowlist_has_exactly_the_expected_membership
# FAILED ...::test_the_archive_examples_root_is_admitted
# 2 failed, 51 passed          <- commit 7e65351
```

Then the widening:

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/publish_scan_tests -q
# 53 passed                    <- commit 6ef6cc5
```

`43 → 53`: six new test functions, one of them parametrized over five
non-admitted trees.

### What was added, and why narrow

`tools/publish_scan.py::INCLUDE_ALLOWED_PREFIXES` gains **`archive/examples/`**
— not `archive/`. The constant's comment now records what was admitted, by
which ruling (`D-IMPL-194` criterion 17, against the root `D-03` pinned), that
the narrow spelling was deliberate, and where the guard lives. `archive/` would
admit every future sibling under the archive root to the published tree by
inheritance; that is a boundary change nobody would be asked to approve.

The guard in `tools/publish_scan_tests/test_publish_scan.py` asserts, in six
functions:

1. `test_the_publication_allowlist_has_exactly_the_expected_membership` — set
   equality against a literal, not `in` checks. An `in` check passes over a
   tuple that has *grown*, and growth is the direction that publishes
   something new.
2. `test_no_allowlisted_prefix_is_empty` — no member is empty (`("",)` makes
   `str.startswith` admit the entire repository) and every member ends in `/`
   (so `examples` cannot admit a sibling `examples-scratch/` by name prefix).
3. `test_an_internal_tree_still_escapes_the_allowlist` — five representative
   paths from `src/`, `runtime/`, `docs/`, `tests/` and `references/` still
   escape.
4. `test_the_archive_examples_root_is_admitted` — the widening itself, asserted
   both at `include_escapes` and through the directive parser via
   `scan_prebuild`.
5. `test_the_widening_is_the_narrow_one_and_does_not_open_the_archive_tree` —
   `archive/secrets/x.md` still escapes and `archive/` is not a member.
6. `test_the_existing_roots_are_still_admitted` — the widening is a strict
   superset; nothing previously permitted moved.

### The four sabotages — every prediction held

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-17a** | remove `"public/"` from the tuple | the membership assertion fails naming `public/` | `4 failed, 49 passed`. The membership assertion fails with `Extra items in the right set: 'public/'` | **YES** |
| **S-17b** | replace the whole tuple with `("",)` | the empty-member assertion fails AND the five internal-path assertions fail | `14 failed, 39 passed`. `AssertionError: an empty prefix makes str.startswith admit every target — the allowlist stops being an allowlist: ('',)`, plus all five `test_an_internal_tree_still_escapes_the_allowlist[...]` | **YES** |
| **S-17c** | revert the `"archive/examples/"` addition | `include_escapes("archive/examples/00-quickstart/run.py:boot")` is `True` | `include_escapes(...) = True`; `2 failed, 51 passed` — membership + `test_the_archive_examples_root_is_admitted` | **YES** |
| **S-17d** | widen to `"archive/"` instead | `include_escapes("archive/secrets/x.md")` becomes `False` | `include_escapes(...) = False`; `2 failed, 51 passed` — membership + `test_the_widening_is_the_narrow_one_and_does_not_open_the_archive_tree` | **YES** |

Each restored with `git checkout --` and confirmed byte-identical with
`git diff --quiet`, plus a positive sanity grep that the widening survived the
restore (see Correction 2 — the sanity grep is there because the naive form of
this loop destroyed the fix once).

**Bonus catches worth naming.** S-17a also turned two PRE-EXISTING tests red —
`test_the_repo_public_tree_includes_only_permitted_roots` and
`test_main_exits_zero_in_prebuild_mode_on_this_repo` — because the shipped
`public/` tree includes from `public/`. So removing `public/` was already
detectable; removing `perf/baselines/` or emptying the tuple was not, which is
what the new guard closes.

### The widening is a no-op on today's tree — proven, not asserted

```bash
test -e archive                 # $? = 1   (absent)
git ls-files archive | wc -l    # 0
```

```bash
# every include target the published tree actually uses
# (tools.publish_scan.include_targets over public/**/*.md)
# include targets in public/: 120; of which archive/-prefixed: 0
grep -rn 'archive/' public/ --include='*.md' | wc -l    # 0
```

The widened member is reachable by **zero** current targets, so the tuple change
cannot alter any verdict. Confirmed at the output level against the PHASE_BASE
capture:

| docs-strict step | Exit | Findings | vs PHASE_BASE capture |
|---|---:|---:|---|
| 1 `publish_scan.py --pre-build` | 0 | 0 | **byte-identical** |
| 2 `publish_scan.py docs/schemas` | 0 | 0 | **byte-identical** |
| 3 `mkdocs build --strict` | 0 | — | identical modulo its build-duration line |
| **4 `publish_scan.py site`** | **0** | **0** | **byte-identical** |

**Step 4 is recorded separately because `23-RESEARCH.md` §14.4 flags it as never
exercised** — nobody had checked what a widened allowlist does to the post-build
site scan. Run: `EXIT_STEP4=0`, zero findings, output byte-identical to base.
`make docs-strict` as a whole exits 0.

The one `⚠ Warning from the Material for MkDocs team` line in step 3 is present
in the PHASE_BASE capture too — pre-existing, not introduced.

---

## Task 3 — criterion 18: `archive/` stops being stripped, controlled both ways

### The defect, re-measured against the shipped regex

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -c "from tools.docs_tests.test_no_stale_example_paths import PATH_TOKEN; ..."
# PATH_TOKEN at PHASE_BASE: (?<![A-Za-z0-9_.-])(?:tests/examples|examples)/[A-Za-z0-9_./-]*[A-Za-z0-9_/]
# input : 'see archive/examples/04-cross-process/producer_child.py'
# tokens: ['examples/04-cross-process/producer_child.py']       <-- 'archive/' silently stripped
```

Reproduced exactly as `D-IMPL-194` states it. See **Correction 3** for the part
of the plan's framing that did NOT reproduce at PHASE_BASE and what that forced
in the control design.

### RED before GREEN

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_no_stale_example_paths.py -q
# FAILED ...::test_the_alternation_matches_each_prefix_through_its_own_branch
# FAILED ...::test_a_correctly_re_pointed_archive_path_yields_no_offenders
# FAILED ...::test_a_stale_archive_path_is_reported_with_its_prefix_intact
# 3 failed, 14 passed        <- commit 0d3f2a9
```

After the fix:

```bash
# 17 passed                  <- commit 92f11d5
```

### The fix, and the alternative that was rejected

`tools/docs_tests/test_no_stale_example_paths.py::PATH_TOKEN` takes an
**alternation branch**, longest-first:

```
(?<![A-Za-z0-9_.-])(?:archive/examples|tests/examples|examples)/[A-Za-z0-9_./-]*[A-Za-z0-9_/]
```

```
'see archive/examples/04-cross-process/producer_child.py here'
    -> ['archive/examples/04-cross-process/producer_child.py']
'see tests/examples/test_x.py here'      -> ['tests/examples/test_x.py']
'see examples/00-quickstart/run.py here' -> ['examples/00-quickstart/run.py']
```

**Adding `/` to the lookbehind class was rejected and the rejection is recorded
in the constant's comment.** Both are one character; they are not equivalent.
The lookbehind spelling makes `archive/examples/X` match *nothing* — a
false-offender bug traded for total blindness over the archive — and it is
unnecessary, because the lookbehind's stated job (stopping the inner `examples`
of `tests/examples/x` being re-read) is done by leftmost-match consumption:
`re.findall` resumes after the end of the previous match.

The comment's old sentence — *"verified at HEAD, where no `<prefix>/examples/`
token exists anywhere in the published tree"* — was rewritten rather than left
standing, because Phase 23 is precisely what makes it false.

The branch is spelled `archive/examples`, not `archive`, mirroring the narrow
spelling chosen for the publication allowlist.

### The three directional controls, plus two

| Control | Direction | Function |
|---|---|---|
| 1 | correct tree → **ZERO** offenders | `test_a_correctly_re_pointed_archive_path_yields_no_offenders` |
| 2 | stale archive → **≥1** offender, **with the prefix in the TEXT** | `test_a_stale_archive_path_is_reported_with_its_prefix_intact` |
| 3 | stale bare `examples/` → **≥1** offender, and not mis-labelled | `test_a_stale_bare_examples_path_is_still_reported` |
| + | the tokenizer itself, three branches, three whole tokens | `test_the_alternation_matches_each_prefix_through_its_own_branch` |
| + | the include half reports an archive target unstripped | `test_the_include_half_reports_an_archive_target_unstripped` |

Control 2 asserts on the offender **string**, never on a count, because a
stripping tokenizer produces the same count here; only the text distinguishes
"reported the right path" from "reported the stripped path", and the text is
what a reader follows.

Control 1 stands up a **synthetic repo root** under `tmp_path` and points
`_prose.REPO_ROOT` at it, with two non-vacuity preconditions asserted inside
the test: the archive target must exist under the synthetic root, and the
STRIPPED form must not. Without the synthetic root the control passes vacuously
on today's un-moved tree — see Correction 3.

### The four sabotages — every prediction held

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-18a** | revert `PATH_TOKEN` to its PHASE_BASE spelling | control 1 fails, reporting the STRIPPED path | `3 failed, 14 passed`. Control 1: `Left contains one more item: '...page.md:1 -> examples/04-cross-process/producer_child.py'` — the stripped path, exactly as predicted | **YES** |
| **S-18b** | widen the lookbehind to `[A-Za-z0-9_./-]` instead of adding the branch | control 2 fails — zero offenders where one is owed | `findall(...) -> []`; `2 failed, 15 passed`. Control 2: `AssertionError: a stale archive path escaped the scan entirely / assert []` | **YES** |
| **S-18c** | narrow `PATH_TOKEN` so it matches nothing | `test_the_scan_finds_path_tokens_to_check` fails | `9 failed, 8 passed`. The precondition: `no examples/ or tests/examples/ path token found in published prose — this gate is scanning nothing / assert set()` | **YES** |
| **S-18d** | drop the `tests/examples` alternation branch | `test_a_tests_examples_path_is_not_mis_reported_as_a_bare_examples_path` fails | `5 failed, 12 passed`. That test reports `examples/test_does_not_exist.py` — the decapitated form — and `assert 4 == 1` | **YES** |

Restored byte-identically after each; `git diff --quiet` between mutations.

**S-18b is the finding that justifies the "both directions" requirement
empirically rather than by argument: control 1 PASSES under S-18b.** The
blinding mutation satisfies the correct-tree direction perfectly — a page with
correct archive paths yields zero offenders when the scanner sees nothing at
all. Only control 2 refuses it. Had criterion 18 asked for one direction, the
blind spelling would have shipped.

**S-18d also confirms the `tests/examples` branch still carries its own
traffic**, which the plan asks to be confirmed: dropping it makes
`tests/examples/x` match through the bare `examples` branch and be reported as
`examples/x`, which is the exact mis-report the pre-existing control was written
against.

### No-op on today's tree

```bash
make gate-tools                      # EXIT=0 — 406 passed + 328 passed
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest --collect-only -q | tail -1
# 4223 tests collected             (unchanged from task 1)
diff -q ids-full.txt ids-after.txt   # node-id set IDENTICAL to the PHASE_BASE collection
```

`gate-tools` moved `313 → 328`: this plan's own `+10` (task 2) and `+5` (task
3). No pre-existing test moved, and **the `make test` collection did not move at
all**, because `pyproject.toml`'s `testpaths` is `["tests"]` and every file this
plan edited lives under `tools/`.

The test leg was re-run in the same three chunks after both fixes:

```bash
# chunk A: 1348 passed, 59 skipped in 351.33s   EXIT=0
# chunk B: 1408 passed             in 241.39s   EXIT=0
# chunk C: 1349 passed, 59 skipped in 103.98s   EXIT=0
# summed:  4105 passed / 118 skipped / 0 failed  — identical to the base
```

`make lint` 0, `make typecheck` 0 (211 source files), `make docs-strict` 0 on
all four steps with step 4 at 0 findings.

---

## Corrections — measured results that falsified a prediction

### Correction 1 — the plan's "both halves read the same token" is FALSE

The plan's task 3 says *"Apply the same fix to BOTH halves of the module — the
prose walk and the include walk read the same token"*, while also instructing
that the consumers be confirmed rather than assumed. Confirmed, and the
instruction was the right one:

```bash
grep -n 'PATH_TOKEN' tools/docs_tests/test_no_stale_example_paths.py
# 78: the definition
# 101: inside prose_path_offenders
# 126: inside prose_path_tokens
```

**Exactly two consumers, both in the prose walk.**
`tools/docs_tests/test_no_stale_example_paths.py::include_offenders` tokenizes
with `tools.publish_scan.include_targets` and resolves the whole target through
`_include_stem`, so the include half **never had the stripping defect**. Proven:

```
include_offenders on a page containing --8<-- "archive/examples/00-quickstart/run.py"
  -> ['…/inc.md:2 -> archive/examples/00-quickstart/run.py']   (full target, unstripped)
```

`tools/docs_tests/test_retirement_sweep.py::NO_PATH_TOKEN_SHAPES` is a
substring collision on the name, not a consumer.

Rather than leave this as an observation, it is now asserted:
`test_the_include_half_reports_an_archive_target_unstripped` fails if anyone
ever "unifies" the two halves onto the prose tokenizer.

### Correction 2 — `git checkout --` silently destroyed the fix mid-sabotage, and only reading the output caught it

The S-17a sabotage loop mutated the widened tuple, ran, then restored with
`git checkout -- tools/publish_scan.py` and confirmed with `git diff --quiet`.
**Both steps reported success and the restore was wrong**: at that moment only
the RED *test* commit existed, so `HEAD` did not contain the widening, and the
"restore" reverted `tools/publish_scan.py` to its PHASE_BASE state.
`git diff --quiet` passed precisely because the file now matched `HEAD`.

Caught on the very next command, from its output rather than from the diff: a
message-capture run printed `INCLUDE_ALLOWED_PREFIXES = ('examples/',
'perf/baselines/')` — **two** members where three were expected — which is only
possible if the widening was already gone.

Resolution: the fix is committed BEFORE any sabotage that restores from `HEAD`,
and every restore is followed by a positive sanity grep that the fix survived:

```bash
git checkout -- <file> && git diff --quiet <file> && grep -c '<the fix>' <file>   # must print 1
```

All eight sabotages reported above were run under that discipline. This is the
same class as the caution the orchestrator carried into this wave — a command
that looks right and reports success while doing the wrong thing — and it was
visible only in output.

### Correction 3 — the false-offender behaviour is NOT reproducible at PHASE_BASE, and that changed the control design

The plan's task 3 states: *"Proven end-to-end against the shipped function on a
page whose paths are CORRECTLY re-pointed: `prose_path_offenders([page])`
returned two paths the page never wrote."*

**Measured at PHASE_BASE, against the real repo root, that page returns ZERO
offenders.** The reason is the whole point of sequencing this wave before the
move: the stripped token `examples/04-cross-process/producer_child.py` still
RESOLVES today, because the tree has not moved yet. The plan's two-offender
figure was necessarily measured on the researcher's post-move scratch tree.

The tokenizer half of the defect reproduces exactly (`archive/` stripped); the
resolution half cannot, until the move happens.

Consequence, and it is an improvement rather than a workaround: control 1 could
not be written against the real repo root without either creating `archive/`
(out of this wave's scope — nothing moves here) or passing vacuously. It uses a
synthetic repo root instead, with both non-vacuity preconditions asserted
inline. That makes the control RED at PHASE_BASE for the right reason and
independent of when the move lands.

### Not a correction, but recorded: `make lint` and `tools.lints --all` are one leg

The plan's task 1 lists them as separate items. The `lint` recipe is literally
`$(ENV) $(PYTHON) -m tools.lints --all`. Both were run and both exit 0; they are
reported as one signal above rather than as two.

---

## Deviations from Plan

### Rule 3 (blocking, auto-fixed) — the coupling report went stale twice

`docs/surface/examples/RETIREMENT-COUPLINGS.md` is generated by
`tools/retirement_sweep.py::sweep`, which walks `tools/` as well as
`.planning/`. The new tests name condemned trees in their fixtures, so the
committed report went stale the moment they existed:

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests -q
# FAILED tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current
# 1 failed, 274 passed
```

Regenerated in the venv at the criterion-18 commit (`267 → 280` rows), and
regenerated **LAST** again at this summary's commit, since a summary that
enumerates archive paths restales it. This is 23-01's carried-forward finding
holding for a second wave: **a plan whose `files_modified` omits the coupling
report but which writes any swept tree will leave the tree red.** This plan's
`files_modified` omits it, as 23-01's did.

### The RED commits are deliberately red

The plan declares both tasks `tdd="true"`, so each fix is two commits — a `test`
commit watched RED and a `feat`/`fix` commit that turns it GREEN. Commits
`7e65351` (2 failed) and `0d3f2a9` (3 failed) are red by construction. Named
here so a bisect that lands on one can tell "red on purpose" from "regression".

### The plan's `<verification>` file list is short by one

The plan predicts `git diff PHASE_BASE..HEAD --name-only` names only the three
`files_modified` plus `23-02-SUMMARY.md`. Mechanically it also names the
regenerated coupling report and the eight `.planning/` files 23-01 already
carried. Same deviation 23-01 recorded, same cause. The plan's actual
constraints hold exactly:

```bash
git diff b87fe58..HEAD -- src/ runtime/ pyproject.toml | wc -l    # 0
git diff b87fe58..HEAD --name-only -- .planning/STATE.md .planning/ROADMAP.md | wc -l   # 0
```

No Rule 1, Rule 2 or Rule 4 situation arose.

---

## What this plan did NOT do, by design

- **Nothing moved.** `archive/` does not exist; `test -e archive` exits 1 and
  `git ls-files archive` returns nothing. Both widenings are strict supersets
  reachable by zero current targets.
- **`.planning/STATE.md` and `.planning/ROADMAP.md` untouched** (`D-10`, Dave
  2026-08-24; `D-15` forbids the writers regardless). Left by decision, not
  forgotten.
- **No Success Criterion authored, renumbered or edited.** The set is EIGHTEEN
  and LOCKED (`D-GATE-19`).
- **No `CLNT-17` disposition of any kind**, and no `s1` tree touched, named or
  re-pointed. The only `s1` string anywhere in this plan's diff is a
  pre-existing generated report row that shifted line position; it is present
  identically at `PHASE_BASE` and at `HEAD`.
- **No `src/`, `runtime/` or `pyproject.toml` edit.** The four permitted
  citation updates (`D-07`) belong to a later wave.
- **`make examples` not run.** Criterion 15's, owed by `23-12`.

---

## Verification

Against the plan's `<verification>` block:

- [x] `make gate-tools` exits 0 — `406 passed` + `328 passed`
- [x] `make docs-strict` exits 0 on all four steps; **step 4 recorded
      separately: `EXIT_STEP4=0`, 0 findings, byte-identical to base**
- [x] `.venv/bin/python -m pytest --collect-only -q | tail -1` → `4223`,
      matching task 1, with the node-id set proven identical
- [~] `git diff PHASE_BASE..HEAD --name-only` — the three `files_modified` plus
      this summary, **plus the regenerated report and 23-01's eight planning
      files**. Deviation recorded above.
- [x] `git diff PHASE_BASE..HEAD -- src/ runtime/ pyproject.toml` is EMPTY (0 lines)

Against the plan's `<success_criteria>`:

- [x] Criterion 17 discharged — archive root admitted, tuple guarded for the
      first time, guard watched RED by removing a prefix (S-17a) and by three
      more mutations
- [x] Criterion 18 discharged — `archive/` no longer stripped, controls in both
      directions, **both blinding sabotages (S-18b, S-18c) watched RED**
- [x] The phase base measured by observed foreground runs — `4105 / 118 / 0` —
      and a chunk plan recorded for 23-12 with disjointness and set-equality
      PROVEN by recorded command output
- [x] Both widenings proven no-ops on a tree where `archive/` does not exist —
      by absence, by zero reachable targets, by byte-identical scan output, and
      by an unmoved test leg

---

## Key links for the next plans

| From | To | Via |
|---|---|---|
| this summary | `23-04`–`23-07` | the re-pointed includes are now admissible; `docs-strict` step 1 will not reject them |
| this summary | `23-05` / criterion 5 | its independent witness can now be RED for the right reason and GREEN on a correct tree |
| this summary | `23-08` | its sabotage S-4 (`INCLUDE_ALLOWED_PREFIXES` → `("",)`) is S-17b here; expect ≥14 failures, not 1 |
| this summary | `23-12` | the proven three-chunk plan, and criterion 7's `4105 / 118` now measured rather than carried |

---

## Self-Check: PASSED

```bash
[ -f .planning/phases/23-…/23-02-SUMMARY.md ]                       # FOUND
git log --oneline b87fe58..HEAD                                     # 5 commits, all present
git diff b87fe58..HEAD -- src/ runtime/ pyproject.toml | wc -l      # 0
grep -c '"archive/examples/",' tools/publish_scan.py                # 1
grep -c 'archive/examples|tests/examples' tools/docs_tests/test_no_stale_example_paths.py   # 1
make gate-tools                                                     # EXIT=0
```

Every figure above was produced by the command printed beside it and read from
that command's output, not inferred from a diff.
