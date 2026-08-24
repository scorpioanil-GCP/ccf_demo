---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 03
subsystem: gate scope widenings and root-membership assertions — every tool that decides whether the archive is looked at
tags: [DOCS-17, S-16, B2, CINV-01, count-floors, schema-headers, resolver-seam, phase-base]
status: complete
requires:
  - phase: 23-02
    provides: the measured base 4105/118, the three-chunk test plan, and the narrow-vs-inheriting spelling precedent this plan deliberately inverts
provides:
  - seven constants and one glob-set that reach the archive, each with a membership assertion beside it
  - B2 closed by MEASUREMENT — a prompt literal under archive/ proven unreported with LINTED_TREES widened and RULE_TREE_SCOPE not
  - eleven sabotages run, two predictions falsified and recorded as corrections
  - three findings logged to deferred-items.md rather than fixed
  - a corrected header census — 216 headers, 220 header-string occurrences, all four extras accounted for individually
affects:
  - 23-04 (the move is now the only thing under test; every gate already reaches where the trees are going)
  - 23-05 (the header repair is 216 files, of which the gate can see 213 — the caveat is recorded)
  - 23-06 (D-07's re-pointed seam citations will still be recognised as citations)
  - 23-07 / 23-12 (the four floors stay at 9/12/14/12 and are expected to hold on the moved witnesses)
tech-stack:
  added: []
  patterns: [red-before-green-by-sabotage, membership-not-count, every-figure-carries-its-command, behavioural-control-over-string-assertion, narrow-vs-inheriting-by-boundary-direction]
key-files:
  created:
    - tools/lints/tests/test_scope.py
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/deferred-items.md
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/23-03-SUMMARY.md
  modified:
    - tools/lints/__main__.py
    - tools/lints/citations.py
    - tools/check_schema_headers.py
    - tools/docs_tests/test_resolver_seam_obligations.py
    - tests/lints/test_examples_scope.py
    - tests/products/test_gate_two_call_shape.py
    - tests/products/test_required_operators_guard.py
    - tests/examples/test_artifact_schema_headers.py
    - docs/surface/examples/RETIREMENT-COUPLINGS.md  # generated; regenerated LAST
decisions:
  - "The lint and scan roots take the INHERITING spelling `archive`; the artifact and publication roots take the NARROW `archive/examples/`. The split is by boundary direction, not by tidiness: default-allow should reach a future sibling, default-deny must not."
  - "RULE_TREE_SCOPE[\"no-hardcoding\"] gains `archive` as a SEPARATE and necessary edit — B2. Proven by measurement, not argument."
  - "`discover` gains a `base` parameter so the header-glob widening can be proven by behaviour on a synthetic tree rather than by asserting the glob strings are the glob strings."
  - "No floor constant touched. 9 / 12 / 14 / 12 are byte-identical to PHASE_BASE."
  - "The header census is 216, not 220. The 4-file difference is README prose about the convention, each named."
requirements-completed: []
metrics:
  duration: ~2h20m
  completed: 2026-08-24
  tasks: 3
  commits: 6
---

# Phase 23 Plan 03: Every gate that decides whether the archive is looked at — Summary

**Seven constants and one glob-set now reach the archive, every one of them
proven a no-op on a tree where `archive/` does not exist, and every one of
them guarded by a MEMBERSHIP assertion rather than a count.** Eleven
sabotages were watched RED. **Two predictions were falsified**, both recorded
as corrections rather than smoothed — and one of them (S-S1) was falsified
because this plan built a stronger control than the plan expected to exist.
The blocker B2 was closed by measurement: an identical prompt literal under
`archive/` produces **zero** findings with `LINTED_TREES` widened and
`RULE_TREE_SCOPE` not.

---

## The base, re-measured before anything changed

```bash
test -e archive                                  # EXIT=1 — absent
git ls-files archive | wc -l                     # 0
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all     # EXIT=0, 0 lines of output
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest --collect-only -q | tail -1
# 4223 tests collected            (reproduces 23-02 task 1 exactly)
```

The citation walk, and the four floors, each partitioned by tree:

```bash
# tests/invariants/test_citation_coverage.py::scanned_citation_hosts / citations_read
scanned_citation_hosts = 1109      # floor MINIMUM_SCANNED_CITATION_HOSTS = 953
citations_read         = 1742      # floor MINIMUM_CITATIONS_READ = 797

gate call sites       = 12  floor 12  {'src': 1, 'examples': 11}
projecting bodies     = 14  floor 14  {'examples': 14}
resolved binder sites = 12  floor 12
required_operators    = 14  floor  9  {'src': 2, 'examples': 12}
```

---

## Corrections to figures the plan and the research carried

### Correction 1 — "96 Python modules" is wrong, and the arithmetic behind it is recoverable

The plan's objective (line ~61) and threat `T-23-08` both state, **as
measured**, that a bare move leaves *"265 files — including 96 Python
modules — outside the scope of every CINV lint."*

```bash
TREES="examples/00-quickstart … examples/external/00-hello-context"   # the ten
git ls-files -- $TREES | wc -l            # 265   <- correct
git ls-files -- $TREES | grep -c '\.py$'  #  24   <- NOT 96
git ls-files -- $TREES | sed 's/.*\.//' | sort | uniq -c | sort -rn
#  217 yaml   24 py   12 json   11 md   1 txt
```

**The ten trees hold 24 `.py` files.** The orchestrator's diagnosis — a
citation-host count transcribed as a module count — is directionally right but
the real figure is neither 96 nor 24. Measured:

```bash
# tests/invariants/test_citation_coverage.py::scanned_citation_hosts, partitioned
total hosts                  = 1109
hosts inside the ten trees   =  252     (217 yaml, 24 py, 11 md)
surviving                    =  857
```

**857 reproduces `23-RESEARCH.md` §7.2's figure exactly.** So the research
measured the *surviving* count on its post-move trial tree, then subtracted it
from the FLOOR constant (953) rather than from a measured total, and recorded
the remainder as "inside the ten": `953 − 857 = 96`. The real inside-count is
`1109 − 857 = 252`.

**The action is unaffected** — the citation walk must reach the archive either
way, and after the move it would read 857 against a floor of 953 and go red.
Only the label "measured" was wrong, and the number it labelled.

### Correction 2 — the `$schema` census is 216, and the 220 is a different question

The orchestrator asked for a depth histogram with every off-shape header
accounted for individually. Measured across the ten trees:

```
A. files whose FIRST line is a $schema header : 216
   depth histogram ('../' count)              : {3: 196, 4: 20}

B. files containing the header string ANYWHERE: 220   (220 occurrences)
   depth histogram                            : {0: 4, 3: 196, 4: 20}

C. the 4 off-shape occurrences, individually:
   examples/01-agent-basics/README.md:134
   examples/02-skilling/README.md:118
   examples/05-workflow-hitl/README.md:119
   examples/external/00-hello-context/README.md:183
```

All four are **README prose** — a backticked mention of
`` `# yaml-language-server: $schema=` `` inside a sentence explaining the
convention — at **depth 0**, carrying no relative target. They are not headers,
they need no `../` repair, and the move does not touch them.

**216 is the repair count for Wave 5. Research's figure stands; the planner's
220 answers "how many files mention the string".** Both were right about
different questions and neither said which.

Reconciliation of the 216: 214 `artifacts/*.yaml` documents (213 headered + 1
carrying the `PERMANENTLY_DEFERRED` marker) plus **3 headered documents in a
nested `artifacts/agents/` directory** — see Finding 1 below.

---

## Task 1 — the lint walk, CINV-01 and the citation walk

### B2, closed by measurement rather than by argument

`tools/lints/__main__.py::RULE_TREE_SCOPE` is a **positive** per-rule scope.
The runner reads `RULE_TREE_SCOPE.get(rule, LINTED_TREES)`, so a rule absent
from the mapping inherits every linted tree and a rule PRESENT in it inherits
nothing. `no-hardcoding` is present.

Run with `archive` in `LINTED_TREES` and NOT in `RULE_TREE_SCOPE`, against a
synthetic tree carrying the **identical** prompt literal in both places:

```
LINTED_TREES             = ('src', 'runtime', 'examples', 'tests', 'archive')
RULE_TREE_SCOPE[no-hard] = ('src', 'runtime', 'examples', 'tests')

findings: 1
   /tmp/…/examples/00-quickstart/run.py:1 cinv01a-prompt-shape prompt-shaped string literal …
```

**One finding, not two.** The walk visits `archive/examples/00-quickstart/run.py`
and the rule skips it. 265 archived files would sit outside CINV-01 with
`python -m tools.lints --all` exiting 0 — the phase's own defect class arriving
one layer in from where anyone would look for it.

### The CINV-02 finding stands, and no edit was made

Established by reading the mechanism rather than assumed: `harness-imports`,
`algorithmic`, `orchestration-imports` and `backend-imports` are scoped
`("src", "runtime")` and `substrate-names` to `("src",)`. `"archive"` is not a
member of any of them, so it is excluded **by construction**. No scope entry
was added. The non-edit is now asserted
(`tools/lints/tests/test_scope.py::test_no_core_scoped_rule_reaches_the_archive`)
so a later "consistency" pass cannot quietly add one, and the behavioural half
is asserted through `run()`
(`tests/lints/test_examples_scope.py::test_cinv02_does_not_flag_harness_imports_under_the_archive`).

### The asymmetry with 23-02, written at both constants

| Constant | Spelling | Boundary direction | Why |
|---|---|---|---|
| `tools/lints/__main__.py::LINTED_TREES` | `archive` | default-ALLOW | a future `archive/anything` should be linted the day it appears |
| `tools/lints/citations.py::GATED_TREES` | `archive` | default-ALLOW | same |
| `tests/products/…::SCANNED_TREES` | `archive` | default-ALLOW | same |
| `tools/publish_scan.py::INCLUDE_ALLOWED_PREFIXES` (23-02) | `archive/examples/` | default-DENY | `archive/` would publish every future sibling by inheritance |
| `tools/check_schema_headers.py::ARTIFACT_GLOBS` (this plan) | `archive/examples/` | default-DENY | a future sibling full of YAML is not artifact material |

Each constant's own comment states its direction and names the opposite choice,
so a reader who finds the inconsistency finds the reasoning with it.

### RED before GREEN

```bash
# commit 3055ed8
.venv/bin/python -m pytest tools/lints/tests/test_scope.py -q     # 7 failed, 2 passed
.venv/bin/python -m pytest tests/lints/test_examples_scope.py -q  # 1 failed, 4 passed
# commit 287ce14
.venv/bin/python -m pytest tools/lints/tests tests/lints -q       # 466 passed
```

The 2 that passed at RED are the two non-edit assertions; the CINV-02 archive
exemption also passed at RED, which is what "by construction" means.

### No-op, proven by isolation rather than by absence alone

```bash
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all     # EXIT=0
```

```
with archive   : scanned_files=1110 total=1751
without archive: scanned_files=1110 total=1751       <- GATED_TREES filtered live
archive member contributes: 0 hosts, 0 citations
```

**The host count MOVED, 1109 → 1110, and the plan says to treat that as a
finding.** Accounted for file by file, and the archive member is not the cause:

| File | base | now | delta |
|---|---:|---:|---:|
| `tools/lints/__main__.py` | 0 | 1 | +1 |
| `tools/lints/citations.py` | 6 | 8 | +2 |
| `tools/lints/tests/test_scope.py` (new) | 0 | 6 | +6 |
| `tests/lints/test_examples_scope.py` | 0 | 0 | 0 |

`+1 +2 +6 = +9`, which is the citation delta exactly; the host delta of +1 is
the one new file. This plan's own new `tools/` file is the whole of it.

### Sabotages

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-L1** | `LINTED_TREES = ("src","runtime","archive","tests")` — the swap | membership assertion fails naming `examples`; `test_examples_scope.py` also fails | `3 failed, 6 passed` + `1 failed, 4 passed`. Set-equality, the named-pair test, **and a third: `test_every_scoped_rule_names_only_trees_the_walk_visits`** — `no-hardcoding` was left scoped to a tree the walk no longer visits | **YES**, +1 bonus |
| **S-L2** | drop `"archive"` from `LINTED_TREES` only | membership assertion fails naming `archive` | `5 failed, 9 passed` across both modules | **YES** |
| **S-L4** | drop `"archive"` from `RULE_TREE_SCOPE["no-hardcoding"]` only — **B2's mandated sabotage** | must fail a NAMED test | `3 failed, 11 passed`: `test_cinv01_scope_has_exactly_the_expected_membership`, `test_both_the_live_examples_tree_and_the_archive_are_under_cinv01`, and `tests/lints/test_examples_scope.py:88` — the assertion B2 required | **YES** |
| **S-L3** | `GATED_TREES` with `"examples"` swapped for `"archive"` | membership assertion fails | `2 failed, 7 passed` | **YES** |

**B2's requirement is discharged and did not become a finding**: removing
`"archive"` from `RULE_TREE_SCOPE` fails three named tests, and the assertion
was written before the sabotage rather than widened after it.

Every restore: `git checkout --`, then `git diff --quiet`, then a **positive
sanity grep** printing `1` for each surviving fix — 23-02's Correction 2
discipline, and the fixes were committed before any sabotage that restores from
`HEAD`.

---

## Task 2 — the four count floors' scan roots

### Floors byte-unchanged

```bash
git show b87fe58:tests/products/test_required_operators_guard.py | grep '^MINIMUM_IMPLEMENTATIONS'
# 94:MINIMUM_IMPLEMENTATIONS = 9
grep -n '^MINIMUM_IMPLEMENTATIONS' tests/products/test_required_operators_guard.py
# 112:MINIMUM_IMPLEMENTATIONS = 9          <- value identical, line moved by the comment
```

`MINIMUM_GATE_CALL_SITES = 12`, `MINIMUM_PROJECTING_BODIES = 14`,
`MINIMUM_RESOLVED_BINDER_SITES = 12` — all three likewise identical to
`PHASE_BASE`.

### The widening is a no-op, re-measured partitioned

```
SCANNED_TREES        = ('src', 'runtime', 'examples', 'archive')
BINDER_SCANNED_TREES = ('examples', 'archive')

gate call sites       = 12  floor 12  {'src': 1, 'examples': 11}
projecting bodies     = 14  floor 14  {'examples': 14}
resolved binder sites = 12  floor 12
required_operators    = 14  floor  9  {'src': 2, 'examples': 12}
```

Identical to the pre-widening measurement, member for member. `114 passed`
across both modules.

### Sabotages

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-F1** | `SCANNED_TREES = ("archive",)` in `test_required_operators_guard.py` | two-part, and the plan flagged the first half as possibly wrong | `2 failed, 1 passed, 1 SKIPPED`. `test_the_scan_is_not_vacuous` **FAILED** (0 found vs floor 9) and the membership assertion failed | **CORRECTION — see below** |
| **S-F2** | drop `"examples"` from `test_gate_two_call_shape.py::SCANNED_TREES` | membership assertion fails; the count floors drop below 12/14 | `5 failed, 78 passed` — membership, `test_the_gate_scan_is_not_vacuous`, `test_the_binder_scan_is_not_vacuous`, plus two more | **YES**, +3 bonus |
| **S-F3** | `MINIMUM_IMPLEMENTATIONS = 0` | **nothing fails — record as a finding** | the module passed (`17 passed`) — but `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` **FAILED** | **CORRECTION — see below** |

#### Correction 3 — S-F1's prediction, resolved

The plan's prediction reads *"`test_the_scan_is_not_vacuous` STAYS GREEN today
(archive does not exist → 0 found → actually FAILS today; …)"* — it contains
both answers. **The parenthesis is what happened**: the scan found zero, the
floor of 9 was not met, and the test went red for the ordinary reason.
Recorded as a correction rather than read charitably.

The more interesting half is what did **not** go red. The parametrized
`test_no_required_operators_reads_the_registrys_own_keys` collapsed from 14
cases to a single `[NOTSET]` **SKIPPED** case:

```
4 tests collected            (was 17)
… test_no_required_operators_reads_the_registrys_own_keys[NOTSET] SKIPPED
```

An empty parametrization reports as a skip, and a skip does not turn a suite
red. This is `23-RESEARCH.md`'s S-9 shape — *"a skip and a pass are
indistinguishable in a total"* — reproduced live, and it is precisely why the
membership assertion had to exist beside the floor.

#### Correction 4 — S-F3's "nothing catches it" is FALSE, and the thing that catches it is the wrong signal

`MINIMUM_IMPLEMENTATIONS = 0` was expected to be invisible. It is not:

```
FAILED tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current
```

`tools/retirement_sweep.py::_floors` records each floor's value in the coupling
report, so lowering one restales the committed file:

```diff
-| … | `MINIMUM_IMPLEMENTATIONS` — floor 9, 14 witnesses, headroom 5
+| … | `MINIMUM_IMPLEMENTATIONS` — floor 0, 14 witnesses, headroom 14
```

**Detected, but weakly, and in a way that invites the wrong reflex.** The
message says *the report is stale*, not *a floor was lowered*. The obvious
response is `retirement_sweep.py --report`, which turns it green and commits
`floor 0, headroom 14` into a generated file nobody re-reads. Logged to
`deferred-items.md` rather than fixed: a gate that refuses a floor *decrease*
needs the previous value pinned somewhere, which is a decision about where a
floor's authority lives.

#### Bonus finding from S-F2 — the two scan roots are not independent

`test_the_binder_scan_is_not_vacuous` went red under S-F2 even though
`BINDER_SCANNED_TREES` was untouched:

```
AssertionError: 13 projecting bodies found, 14 expected.
```

`tests/products/test_gate_two_call_shape.py::_plan_classes` is derived from
`SCANNED_TREES` and is consulted by `_is_plan_construction`, so the binder scan
depends on the gate scan's roots through the recognised plan-class vocabulary.
**No defect today** — both constants were widened together, which is what the
coupling requires — but a future reader widening one and not the other would
get a partial result with no message saying why. Logged to `deferred-items.md`.

---

## Task 3 — the schema-header discovery and the resolver-seam prefix

### A design decision worth naming: `discover` gained a `base` parameter

The plan warned against closing S-S1 *"with an assertion that only proves the
glob string is what it is"*. So `tools/check_schema_headers.py::discover` takes
an optional `base`, mirroring the existing precedent in the test module —
`covered_artifact_directories(tree)` is already *"parameterized on the root so a
control can run it over `tmp_path`"* — and the control plants a real
`archive/examples/retired-example/artifacts/thing.yaml` and asserts it is
found. Both roots are planted, so a widening that reached the archive by
*losing* the live tree cannot satisfy it. A second control plants
`archive/scratch/artifacts/` and `tests/fixtures/artifacts/` and asserts
neither is found — the widening is a widening, not an opening.

### RED before GREEN, and the RED was an assertion rather than a collection error

The first RED draft imported `ARTIFACT_GLOBS` before it existed, which errored
at **collection** and would have left a commit where `make test` reports
nothing at all. On this host that is indistinguishable from a pass. So the RED
commit introduces the constant in its NARROW form and the GREEN commit is the
tuple widening in isolation:

```bash
# commit c03cd70
.venv/bin/python -m pytest tests/examples/test_artifact_schema_headers.py -q
# 2 failed, 27 passed          (29 collected — collection intact)
.venv/bin/python -m pytest tools/docs_tests/test_resolver_seam_obligations.py -q
# 1 failed, 15 passed
# commit 34df27a
# 29 passed  /  16 passed
```

### No-op, proven against the PHASE_BASE discovery set

```bash
discover(require_all=True)  ->  11 directories, 0 of them archive-prefixed
diff -q discover-now.txt discover-base.txt   # IDENTICAL
python tools/check_schema_headers.py --require-all   # EXIT=0
```

### Sabotages

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-S1** | revert `ARTIFACT_GLOBS` to the `examples/`-only form | **nothing fails today** — record as a standing gap | **2 failed**: the membership assertion AND the synthetic-tree behavioural control. `gate-tools` stayed at `329 passed` and `check_schema_headers --require-all` still exited 0 | **CORRECTION — see below** |
| **S-S2** | drop `EXAMPLES_ROOT` from the gated root set | membership assertion fails; `example_roots()` returns fewer roots and the parametrization shrinks | `3 failed, 26 passed` — membership, `test_the_example_tree_is_populated`, and `test_this_module_gates_the_same_set_the_tool_checks`. **The parametrization did NOT shrink** | **PARTIAL — see below** |
| **S-S3** | `EXAMPLE_PREFIX = ("archive/examples/",)` only | both seam tests fail TODAY because every citation still says `examples/` | `4 failed, 12 passed`: `test_the_seam_cites_a_shipped_example_that_exists` ×2, `test_both_seams_cite_both_call_sites`, plus the membership assertion | **YES** |

#### Correction 5 — S-S1's "nothing catches it" was true when the plan was written and is false now

The plan's prediction described the tree it was written against. It was
falsified by this task's own decision to give `discover` a `base` parameter:
`test_the_discovery_finds_an_archived_artifact_directory` is RED under S-S1
today, without waiting for Wave 5 and without asserting that a string is a
string.

**The finding underneath the prediction still stands, and is the part worth
carrying**: nothing in the *shipped tooling* notices. Under S-S1, `make
gate-tools` is green (`415` + `329`), `check_schema_headers --require-all`
exits 0, and after the move it would keep exiting 0 over 216 rotten headers.
Only the new control refuses. That is the gap closed, rather than confirmed.

#### Correction 6 — S-S2's second half

The parametrization is fed by `discover()` — the **tool's** roots — not by this
module's root set, so dropping `EXAMPLES_ROOT` here left all 11 parametrized
cases in place. What caught the divergence instead is
`test_this_module_gates_the_same_set_the_tool_checks`, which is exactly the
assertion whose docstring says *"two definitions of one set eventually
disagree — so they are compared here rather than trusted."* The prediction's
mechanism was wrong; a better one was already in the module.

### Left alone deliberately

`PY_BEARING_NON_EXAMPLES` and `PERMANENTLY_DEFERRED` still name `examples/…`
paths, which are correct today and become wrong at Wave 4. `23-05` re-points
them. Their **consumers** were moved onto the union
(`all_example_roots()`), so 23-05's job is a key re-point and nothing more.
`EXAMPLE_ROOT_MARKER` is untouched.

---

## Findings recorded rather than fixed

Logged to
`.planning/phases/23-…/deferred-items.md`:

1. **The header gate is blind to a nested `artifacts/<subdir>/`, and three
   shipped documents are in that blind spot.** Measured:
   `examples/03-harness-portability/artifacts/agents/{agent-definition,debt-profile,policy-regime}.yaml`
   all carry resolving `$schema` headers and are outside
   `ARTIFACT_GLOBS` today. Pre-existing since plan `15-12`; Phase 23 only makes
   it consequential. **Not a one-character fix**: deepening the pattern puts
   `…/artifacts/agents` into the covered set, whose parent is not an example
   root, and the bijection's right side goes red on a correct tree.
   **Carried to Wave 5 as a caveat**: the repair is 216 files; the gate's green
   will cover 213 of them.
2. **A lowered floor is visible only as a stale generated report** (Correction 4).
3. **`SCANNED_TREES` and `BINDER_SCANNED_TREES` are coupled through
   `_plan_classes()`** (S-F2 bonus).

---

## Verification

| Leg | Command | Result |
|---|---|---|
| lint | `.venv/bin/python -m tools.lints --all` | **EXIT=0**, no output |
| typecheck | `.venv/bin/python -m mypy` | **EXIT=0** — *Success: no issues found in 211 source files* |
| test | three foreground chunks (below) | **4113 passed / 118 skipped / 0 failed** |
| gate-tools | `pytest tools/lints/tests` + `pytest tools/publish_scan_tests tools/docs_tests` | **415 passed** + **329 passed** |
| docs-strict 1 | `publish_scan.py --pre-build` | **EXIT=0** |
| docs-strict 2 | `publish_scan.py docs/schemas` | **EXIT=0** |
| docs-strict 3 | `mkdocs build --strict` | **EXIT=0** |
| docs-strict 4 | `publish_scan.py site` | **EXIT=0** |

Exit codes captured with no pipe, per §14's measurement hazard. `make lint` and
`python -m tools.lints --all` are one leg, not two.

### The test leg, in 23-02's chunk plan — re-proven against the new collection

```
chunk A collected 1413   chunk B 1410   chunk C 1408
pairwise intersections: 0 0 0
union 4231 lines, 4231 unique, set-EQUAL to the full collection
```

```bash
pytest -q $CHUNK_A   # 1354 passed, 59 skipped in 331.49s (0:05:31)   EXIT=0
pytest -q $CHUNK_B   # 1410 passed             in 226.78s (0:03:46)   EXIT=0
pytest -q $CHUNK_C   # 1349 passed, 59 skipped in 100.33s (0:01:40)   EXIT=0
```

**Summed: 4113 passed / 118 skipped / 0 failed.** `4113 + 118 = 4231`,
reconciling with the collection. Against 23-02's base of `4105 / 118`: **+8
passed, skips unchanged.** Every chunk foreground, longest under six minutes.

### The plan's other constraints

```bash
git diff b87fe58..HEAD -- src/ runtime/ pyproject.toml | wc -l          # 0
git ls-files src runtime pyproject.toml | wc -l                         # 214   (VAC-01 guard)
git diff b87fe58..HEAD --name-only -- examples/ public/ Makefile | wc -l # 0
git ls-files examples public Makefile | wc -l                           # 380   (VAC-01 guard)
git diff b87fe58..HEAD --name-only -- .planning/STATE.md .planning/ROADMAP.md | wc -l  # 0
test -e archive                                                          # EXIT=1
grep -E '^- \[.\] \*\*CLNT-17\*\*|^\| CLNT-17 \|' .planning/REQUIREMENTS.md | sha256sum
# 5bcc68caa9f6839df0d870aba10a4897114607995eb21ded0b13cccedc3ba084   (23-01's anchor, 2 lines matched)
```

---

## Deviations from Plan

### The collected total MOVED, and the plan's verification cannot hold as written

The plan requires *"`--collect-only -q | tail -1` matches 23-02 task 1's
total"* (4223) while **also** requiring membership assertions in
`tests/lints/test_examples_scope.py` (B2), `tests/products/test_gate_two_call_shape.py`
and `tests/products/test_required_operators_guard.py` — all under `testpaths =
["tests"]`. The two requirements are not simultaneously satisfiable. 23-02
avoided the collision only because every file it edited lived under `tools/`.

Reported as the stronger statement the plan's §7.1 framing actually cares
about — **nothing was lost**:

```bash
comm -23 ids-base.txt ids-after.txt | wc -l   # 0   node ids LOST
comm -13 ids-base.txt ids-after.txt | wc -l   # 8   node ids ADDED
```

All eight, named:

```
tests/examples/test_artifact_schema_headers.py::test_the_discovery_finds_an_archived_artifact_directory
tests/examples/test_artifact_schema_headers.py::test_the_discovery_globs_reach_the_live_tree_and_the_archive
tests/examples/test_artifact_schema_headers.py::test_the_discovery_ignores_an_artifact_directory_outside_both_roots
tests/examples/test_artifact_schema_headers.py::test_the_gated_roots_are_the_live_tree_and_the_archive
tests/lints/test_examples_scope.py::test_cinv01_scope_includes_the_archive_tree
tests/lints/test_examples_scope.py::test_cinv02_does_not_flag_harness_imports_under_the_archive
tests/products/test_gate_two_call_shape.py::test_the_scan_root_membership_is_exactly_the_expected_sets
tests/products/test_required_operators_guard.py::test_the_scan_root_membership_is_exactly_the_expected_set
```

**4223 → 4231 is this plan's own assertions and nothing else.** Wave 12 should
gate criterion 7 against `4113 / 118`, not `4105 / 118`.

### Rule 3 (blocking, auto-fixed) — the coupling report, for the third wave running

`docs/surface/examples/RETIREMENT-COUPLINGS.md` went stale at every commit that
named a condemned tree. Regenerated in the venv three times and **LAST** at
this summary's commit: `280 → 284 → 285` rows. This plan's `files_modified`
omits it, as 23-01's and 23-02's did. **Three waves, three identical
deviations** — the planner should add it to `files_modified` for 23-04 onward
rather than each executor rediscovering it.

### `discover`'s signature changed

Adding `base: pathlib.Path | None = None` is not in the plan's text. It is
keyword-compatible with both existing call sites, and it is the minimal enabler
for the behavioural control the plan asked for in place of a string assertion.
Recorded rather than absorbed.

### The RED commits are deliberately red

`3055ed8` (7+1 failed), `36f5011` (2 failed) and `c03cd70` (2+1 failed) are red
by construction. Named so a bisect landing on one can tell "red on purpose"
from "regression". All three still **collect**.

No Rule 1, Rule 2 or Rule 4 situation arose.

---

## What this plan did NOT do, by design

- **Nothing moved.** `archive/` does not exist. Every widening is a strict
  superset reachable by zero current targets, and each was proven so by
  isolating the new member's contribution rather than by pointing at the
  absence.
- **No floor lowered.** 9 / 12 / 14 / 12, byte-identical to `PHASE_BASE`.
- **No Success Criterion authored, renumbered or edited.** EIGHTEEN, LOCKED
  (`D-GATE-19`).
- **`.planning/STATE.md` and `.planning/ROADMAP.md` untouched** (`D-10`;
  `D-15` forbids the writers regardless). Left by decision, not forgotten.
- **No `CLNT-17` disposition of any kind**, and no `s1` tree touched or named.
  Verified: zero `CLNT-17` or `s1` mentions across all six of this plan's
  commit messages; the only `s1` strings in the diff are pre-existing generated
  report rows that shifted line position.
- **No `src/`, `runtime/` or `pyproject.toml` edit.** `D-07`'s four citation
  updates belong to a later wave.
- **`make examples` not run.** Criterion 15's, owed by `23-12`.
- **`PY_BEARING_NON_EXAMPLES` / `PERMANENTLY_DEFERRED` not re-pointed.**
  `23-05`'s, in the same change that repairs the headers.

---

## Key links for the next plans

| From | To | Via |
|---|---|---|
| this summary | `23-04` | every gate already reaches `archive/`; the move is the only thing under test |
| this summary | `23-05` | the repair is **216** headers, of which the gate sees **213** — Finding 1 |
| this summary | `23-06` | `EXAMPLE_PREFIX` accepts `archive/examples/`, so `D-07`'s re-pointed citations stay citations |
| this summary | `23-07` / `23-12` | the four floors are 9/12/14/12 and must hold on the moved witnesses; a floor that does not hold is a finding, never a constant to lower |
| this summary | `23-12` | criterion 7's comparison base is **4113 / 118**, not 4105 / 118 |

## Self-Check: PASSED

```bash
[ -f tools/lints/tests/test_scope.py ]                    # FOUND
[ -f .planning/phases/23-…/deferred-items.md ]            # FOUND
[ -f .planning/phases/23-…/23-03-SUMMARY.md ]             # FOUND
git log --oneline --all | grep -q 3055ed8                 # FOUND
git log --oneline --all | grep -q 287ce14                 # FOUND
git log --oneline --all | grep -q 36f5011                 # FOUND
git log --oneline --all | grep -q 0e87330                 # FOUND
git log --oneline --all | grep -q c03cd70                 # FOUND
git log --oneline --all | grep -q 34df27a                 # FOUND
```
