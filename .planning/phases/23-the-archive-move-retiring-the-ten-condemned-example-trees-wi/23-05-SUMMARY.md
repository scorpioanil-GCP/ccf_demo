---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 05
subsystem: archive-consistency
tags: [archive, schema-headers, sys-path, snippet-gate, DOCS-17]
requires:
  - "the ten trees at archive/examples/ (plan 23-04, ef336f3)"
  - "the widened header discovery (plan 23-03, 34df27a)"
provides:
  - "an archive whose four relocated children resolve the repo root"
  - "216 $schema headers that resolve from their own document directory"
  - "a snippet gate whose SNIPPET_SOURCE names a file that exists"
affects:
  - "23-06 (the four citations), 23-07 (test example paths), 23-08 (includes/prose)"
tech-stack:
  added: []
  patterns:
    - "prove a sys.path fix by scrubbing the editable install, not by running under it"
    - "prove a header by RESOLVING it from its own directory, not by matching a pattern"
key-files:
  created: []
  modified:
    - archive/examples/04-cross-process/producer_child.py
    - archive/examples/07-artifact-store-mcp/mcp_store_child.py
    - archive/examples/external/00-hello-context/serve.py
    - archive/examples/external/00-hello-context/run.py
    - "archive/examples/**/artifacts/**/*.yaml (216 files, line 1 only)"
    - tests/examples/test_artifact_schema_headers.py
    - tools/docs_tests/test_snippet_gate.py
    - .planning/phases/23-.../deferred-items.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "The archive is deliberately UNANNOTATED at its root — no archive/README.md"
  - "The two skip reasons naming plans 16-17/16-18 were reworded; the plan's premise that they 'remain accurate' is false on the tree"
metrics:
  duration: "~1h"
  completed: 2026-08-24
---

# Phase 23 Plan 05: Making the Archive Self-Consistent Summary

Four relocated children resolve the repo root again, 216 `$schema` headers
resolve from their own directories again, and the snippet gate names a file
that exists — with the depth proven by *running* rather than by counting, which
is the one control `23-RESEARCH.md` §15 explicitly left open.

**Headline numbers, each with its command below:** 216 headers repaired,
**213** of them witnessed by the gate; 4 `parents[N]` indices; 222 files in
three commits; 0 files outside `archive/`, `tools/docs_tests/` and
`tests/examples/`; collection **4223 → 4223**, 2 node ids lost and 2 gained,
both the same test re-parametrized at its archive path.

---

## THE HEADLINE THE BRIEF ASKED FOR PLAINLY: 216 REPAIRED, 213 WITNESSED

**Do not read this plan as 216/216.** The header gate sees 213 of the 216 it
should. The three it does not see are:

```
archive/examples/03-harness-portability/artifacts/agents/agent-definition.yaml
archive/examples/03-harness-portability/artifacts/agents/debt-profile.yaml
archive/examples/03-harness-portability/artifacts/agents/policy-regime.yaml
```

They sit one directory **below** `ARTIFACT_GLOBS`' `**/artifacts/*.yaml`, whose
last segment must be literally `artifacts`. All three were repaired by this
plan and all three resolve; what is missing is the *witness*, not the fix.
This is pre-existing since plan 15-12, is **not** this wave's to fix
(`D-IMPL-196`), and `tools/check_schema_headers.py::ARTIFACT_GLOBS` already carries the reason:
deepening the glob turns the bijection's right side red.

Measured, not inherited:

```bash
PYTHONPATH=src:runtime .venv/bin/python -c '...discover(require_all=True)...'
# parametrized directories: 11   (10 under archive/, 1 live)
# archive documents the gate witnesses (one level under artifacts/): 214
# HEADERED FILES OUTSIDE THE GATE: 3
#     archive/examples/03-harness-portability/artifacts/agents/agent-definition.yaml
#     archive/examples/03-harness-portability/artifacts/agents/debt-profile.yaml
#     archive/examples/03-harness-portability/artifacts/agents/policy-regime.yaml
```

214 documents witnessed = **213** headered + 1 (`08-e2e-demo/artifacts/
scenario.yaml`, which carries a deferral marker instead of a `$schema` header).

---

## My own census — 216, 220 and 217 all reconciled

Re-measured from scratch, not inherited from the brief or from `23-RESEARCH.md`.

```bash
grep -rl 'yaml-language-server' archive/examples/ | wc -l      # 220 files
grep -rh 'yaml-language-server' archive/examples/ | wc -l      # 220 occurrences
grep -rl 'yaml-language-server' archive/examples/ | sed 's/.*\.//' | sort | uniq -c
#       4 md
#     216 yaml
```

**Depth histogram, before and after, by the plan's own awk:**

```bash
grep -rh 'yaml-language-server' archive/examples/ | sed 's/.*schema=//' \
  | awk -F'docs/' '{print gsub(/\.\.\//,"",$1)}' | sort -n | uniq -c
# BEFORE:   4 at 0      196 at 3      20 at 4
# AFTER:    4 at 0      196 at 4      20 at 5
```

This reproduces `23-RESEARCH.md`'s `{3: 196, 4: 20}` exactly.

**Every off-shape occurrence accounted individually, as the plan required:**

| # | What | Where | Disposition |
|---|---|---|---|
| 4 | prose *about* the convention — the token quoted inline with **no path at all**, hence depth 0 | `01-agent-basics/README.md:134`, `02-skilling/README.md:118`, `05-workflow-hitl/README.md:119`, `external/00-hello-context/README.md:183` | **not headers.** Not edited |
| 1 | `# ccf-schema: deferred(permanent)` instead of a `$schema` header | `08-e2e-demo/artifacts/scenario.yaml` | the `PERMANENTLY_DEFERRED` document. Not edited |

So: **220 token occurrences = 216 headers + 4 prose mentions**, and
**217 YAML under `archive/examples/` = 216 headered + 1 deferral-marked**:

```bash
find archive/examples -name '*.yaml' -type f | wc -l                  # 217
comm -13 headers.txt <(find archive/examples -name '*.yaml' | sort)
# archive/examples/08-e2e-demo/artifacts/scenario.yaml
```

No residue. Every one of the 216 is on **line 1** and matches the exact prefix:

```bash
for f in $(grep -rl 'yaml-language-server' archive/examples/ --include='*.yaml'); do
  grep -n 'yaml-language-server' "$f" | cut -d: -f1; done | sort -n | uniq -c
#     216 1
for f in ...; do head -1 "$f"; done | grep -c '^# yaml-language-server: \$schema=\.\./'
#     216
```

### The repair, and the proof by resolution

Bounded mechanization — only under `archive/examples/`, only line 1, only where
line 1 matches the prefix:

```bash
xargs -a headers.txt sed -i \
  '1s|^# yaml-language-server: \$schema=\.\./|# yaml-language-server: $schema=../../|'
```

```bash
git diff --numstat -- archive/ | awk '{a+=$1;b+=$2} END {print a, b}'   # 216 216
git diff -U0 -- archive/ | grep -E '^@@' | grep -vc '^@@ -1 \+1 @@'     # 0
```

**Zero hunks outside line 1, in any of the 216 files.**

The proof is resolution from the document's own directory — the property the
test states in its own words — not a pattern match:

```
BEFORE:  checked=216  resolved=0    unresolved=216
AFTER:   checked=216  resolved=216  unresolved=0
```

`checked=216` is non-zero on both runs, which is the specific defect
(`0 checked, 0 failed`) this plan exists to prevent.

### The gate, before and after

```bash
PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples/test_artifact_schema_headers.py -q
# BEFORE: 12 failed, 15 passed, 2 skipped
# AFTER:  29 passed
```

---

## The silent PASS→SKIP degradation wave 4 found — repaired, and the plan's premise corrected

Wave 4 measured two controls that went **PASS → SKIP**, invisible to the
collection arithmetic because their node ids did not change:

```
SKIPPED tests/examples/test_artifact_schema_headers.py:489:
  examples/external/00-hello-context/fixtures: retired with the external example at wave 11 (plan 16-18)
SKIPPED ... examples/03-harness-portability/legs: retired with example 03 at wave 8 (plan 16-17)
```

Both directories exist, at `archive/examples/…`:

```bash
ls archive/examples/03-harness-portability/legs/*.py       # deterministic.py __init__.py live.py
ls archive/examples/external/00-hello-context/fixtures/*.py # capture_proxy.py diff_fixtures.py ...
```

Re-pointing the two `PY_BEARING_NON_EXAMPLES` keys makes the directories
present, the skip stop firing, and the control resume controlling. **Skips in
this module: 2 → 0.**

### A CORRECTION to the plan, recorded rather than smoothed

Plan `23-05` task 2 says: *"do not touch the reasons recorded beside them,
which name the retiring wave and **remain accurate**."* That premise is **false
on the tree**. Plans 16-17 and 16-18 retired nothing — `docs/DECISIONS.md`
`D-IMPL-152` RETIRED Phase 16 — and this phase **moved** rather than deleted.
The brief's instruction (*"make the skip condition reflect the tree"*) and the
plan's clause cannot both be honoured, so the reasons were reworded to say what
the tree says: the skip now fires only on a deletion `D-27`'s undecided half has
yet to authorise. **Deviation, Rule 1** — a skip message that asserts a
falsehood is exactly the class of defect the phase is fixing.

`PERMANENTLY_DEFERRED`'s single key was re-pointed with its reason untouched;
that reason (plan 15-16's permanence ruling) *is* accurate.

---

## Task 1 — the four repo-root computations, and S-8 closed by running it

```
archive/examples/04-cross-process/producer_child.py:53        parents[1] -> parents[2]
archive/examples/07-artifact-store-mcp/mcp_store_child.py:32  parents[1] -> parents[2]
archive/examples/external/00-hello-context/serve.py:73        parents[2] -> parents[3]
archive/examples/external/00-hello-context/run.py:64          parents[2] -> parents[3]
```

Four one-token edits, nothing else — `git diff --stat` = `4 files changed,
4 insertions(+), 4 deletions(-)`. The population was verified complete rather
than inherited: `grep -rn "parents\[" archive/examples/` returns exactly these
four and nothing else.

### THE FINDING THAT MATTERS MOST HERE: this venv MASKS the defect

`ccf` and `ccf_runtime` are **editable-installed** in `.venv`:

```bash
.venv/bin/python -c "import ccf, ccf_runtime; print(ccf.__file__)"
# /home/parkave/ccf_code/src/ccf/__init__.py
cat .venv/lib/python*/site-packages/__editable__.ccf-0.1.0.pth
# import __editable___ccf_0_1_0_finder; __editable___ccf_0_1_0_finder.install()
```

So a meta-path finder resolves `ccf` **regardless of `sys.path`**, and the
scripts' own `_REPO_ROOT` insert is dead weight in this environment. Run
straight:

```
PLAIN: OK  _REPO_ROOT=/home/parkave/ccf_code/archive  ccf from .../src/ccf/__init__.py
```

**A wrong `_REPO_ROOT` and a right one are indistinguishable by exit code
here.** That is why the proof was built as a scrubbed-environment probe: it
removes the editable finder from `sys.meta_path`, drops any repo `src`/`runtime`
from `sys.path`, asserts `import ccf` fails *before* loading the target, then
executes the module body — so the script's own insert is the **only** thing that
can find `ccf`.

**RED, all four, before the edit:**

```
PROBE: removed 1 editable finder(s), dropped 0 repo path(s); ccf NOT importable before load
RESULT: ImportError -> No module named 'ccf'
sys.path[0:2] after script insert = ['/home/parkave/ccf_code/archive/runtime',
                                     '/home/parkave/ccf_code/archive/src']
```

**GREEN, all four, after the edit (EXIT=0 each):**

```
RESULT: module body executed; _REPO_ROOT = /home/parkave/ccf_code
RESULT: ccf         from /home/parkave/ccf_code/src/ccf/__init__.py
RESULT: ccf_runtime from /home/parkave/ccf_code/runtime/ccf_runtime/__init__.py
```

`_REPO_ROOT` is **printed and compared**, not inferred from a zero exit.

### And the real thing, run as a real process

```bash
env -u PYTHONPATH timeout 90 .venv/bin/python archive/examples/04-cross-process/producer_child.py
# READY 56355 47181
# EXIT=124  (timeout's kill — the child serves until its parent closes it)
```

It boots the fabric, ingests, runs the operator chain, projects, gates, builds
the agent through the factory, signs, and reports both servers started, from
the archive. `git status --short` after: no stray files.

---

## Task 3 — `SNIPPET_SOURCE`

```
tools/docs_tests/test_snippet_gate.py:57
  REPO_ROOT / "examples" / "00-quickstart" / "run.py"
  -> REPO_ROOT / "archive" / "examples" / "00-quickstart" / "run.py"
```

```bash
PYTHONPATH=src:runtime .venv/bin/python -m pytest tools/docs_tests/test_snippet_gate.py -q
# BEFORE: 2 failed, 1 passed   (FileNotFoundError: .../examples/00-quickstart/run.py)
# AFTER:  3 passed
```

**The plan's open question, answered with its cause:** the module is **NOT
blocked on plan `23-08`**. `test_the_unmodified_source_builds_clean` writes a
throwaway mkdocs project into `tmp_path` from this module's own `CONFIG`
constant (`_project()` at `:78`), so the 102 un-repointed includes under
`public/` cannot reach it. It is green now and stays green independently of the
strict build.

**Inherited ownership recorded in the comment**, as the plan required: the
constant's note named plan 16-18 as the repointing owner; `D-IMPL-152` retired
Phase 16, so nobody owned it, and the note now names `D-IMPL-152`, `23-04` (the
move) and `23-05` (this repoint), with *"Do not go looking for 16-18; it does
not exist."*

---

## Sabotage ledger — 8 mutations, every prediction recorded including the 3 that were wrong

Every mutation was applied **after** the corresponding fix was committed
(wave 2's hazard), restored with `git checkout --`, and confirmed by
`git diff --quiet` **plus a positive sanity grep** on the restored content.

| # | Mutation | Prediction | Observed | Held? |
|---|---|---|---|---|
| **S-8a** | `producer_child.py` back to `parents[1]`, run the child | `ImportError` in the spawned process; `test_cross_process_output.py` errors at collection | scrubbed probe: `ImportError: No module named 'ccf'`, EXIT=1. **Plain venv: the child ran and printed `READY 51691 37613`.** The test errors, but on `FileNotFoundError: .../examples/04-cross-process/producer_child.py` — the un-repointed path, not the depth | **PARTLY — see below** |
| **S-8b** | `serve.py` to `parents[4]`, one too far | `_REPO_ROOT` above the repo; `sys.path` gains a non-repo dir; import fails | scrubbed probe: `sys.path[0:2] = ['/home/parkave/runtime', '/home/parkave/src']`, `ImportError`, EXIT=1. Plain venv: masked, `_REPO_ROOT=/home/parkave`, EXIT=0 | **YES** (under the probe) |
| **S-8c** | edit `03-harness-portability/run.py` "for consistency" | nothing fails; a needless content change in the archive | **not made.** Its insert is `EXAMPLE_DIR = Path(__file__).resolve().parent` — depth-independent. Proven byte-identical by blob SHA at three points: `85aad744` at `PHASE_BASE:examples/…`, at `ef336f3:archive/…` and at `HEAD` | **YES** |
| **S-H1** | revert ONE header to its pre-repair depth | the header test names that file | `1 failed, 28 passed`; `FAILED …[archive/examples/06-decision-replay/artifacts]` and the output names `agent-debt-profile.yaml` twice. Independent resolver: `checked=216 resolved=215 unresolved=1` | **YES** |
| **S-H2** | revert `23-03`'s glob widening with a header broken | the gate reports CLEAN — the silent-gate defect — and *"nothing catches it"* | **The header check went SILENT exactly as predicted**: collection dropped 29 → 19, all ten `test_every_artifact_directory_passes_the_header_check[archive/…]` node ids **vanished**, and the broken file is mentioned **0 times** in the full output. **But "nothing catches it" is WRONG**: four tests went red, three of them `23-03`'s own membership guards | **HALF — the important half held** |
| **S-H3a** | delete ONE artifact YAML | *"the bijection fails, OR nothing fails — run it and record which"* | **nothing fails: `29 passed`.** The bijection is directory-level, not document-level | resolved: nothing |
| **S-H3b** | empty the whole `artifacts/` directory | (my extension of S-H3) | `2 failed`: `test_every_example_root_has_a_covered_artifact_directory` and `test_every_example_roots_artifact_directory_is_non_vacuous` | **YES** |
| **S-SG1** | `SNIPPET_SOURCE` at a non-existent path | module fails at read time | `2 failed, 1 passed`, `FileNotFoundError: .../archive/examples/00-quickstart/no-such-run.py` | **YES** |
| **S-SG2** | `SNIPPET_SOURCE` at the surviving `examples/hw1-harness-clients` | the `[start:SECTION]` marker assertion fails | `AssertionError: fixture drifted from its source / assert '[start:boot]' in …` **and** the strict build: `ERROR - Snippet section 'boot' could not be located` — two independent witnesses | **YES** |

### S-8a — the wrong prediction, and why it matters more than the right ones

The plan predicted the sabotage would surface as an `ImportError` in the spawned
process and as a collection error in `tests/examples/test_cross_process_output.py`.
**Neither is true today**, for two separate reasons:

1. The editable install masks the depth entirely (above). The sabotaged child
   ran to `READY`.
2. `test_cross_process_output.py` does not spawn `producer_child.py` at all for
   its assembly leg — its `assembled` fixture **imports the module in-process**
   (`FileNotFoundError` from `<frozen importlib._bootstrap_external>:1186`). An
   in-process import happens after `ccf` is already imported by the test
   session, so even once `23-07` re-points the path, that test can never
   witness the depth.

**Consequence, stated plainly: no standing gate in this repo can witness S-8.**
The only witness is the scrubbed-environment probe run in this plan. The fix is
correct and proven; the *guard* does not exist. This is the same shape as the
`resolve_cited` suffix-fallback finding wave 4 logged for `23-06` — a green
gate that proves nothing — and it is recorded here so `23-12` can rule on
whether a standing control is owed.

### S-H2 — the empirical closure of `23-03`'s S-S1, with a refinement

The predicted half held decisively. With the walk narrowed:

```
FAILED test_this_module_gates_the_same_set_the_tool_checks
FAILED test_the_discovery_globs_reach_the_live_tree_and_the_archive
FAILED test_the_discovery_finds_an_archived_artifact_directory
FAILED test_the_only_deferred_documents_are_the_ruled_permanent_ones
4 failed, 15 passed          # collection 29 -> 19
grep -c "agent-debt-profile" <full output>    # 0
```

Ten checks did not fail — **they ceased to exist**, and a broken header was
reported by nothing. That is `23-03`'s S-S1 observed rather than argued, and it
belongs in both summaries.

The refinement: the plan's *"nothing catches it; the widening is the fix"* is
**no longer true, because `23-03` shipped the guards.** The header check goes
silent; the **membership** guards go red. The correct statement today is: *a
future narrowing cannot be done silently, even though the header check itself
would still go silent if it were.*

---

## The archive-README question — SETTLED: no README, deliberately

`23-RESEARCH.md` §14.6 left this open and `D-03` pins only the root, so the plan
required an answer either way. **The archive is deliberately unannotated at its
root.** Four reasons, in order of weight:

1. **Criterion 1's evidence stays simple.** `git ls-files archive/ | wc -l` is
   **265** and still is after this plan's 222-file content edit. A new file
   makes it 266 and forces criterion 1's figure to be restated over ten
   pathspecs instead of over `archive/`. That is a real cost for prose.
2. **`D-09` already puts the "marked historical" obligation on the trees' own
   READMEs**, per-tree, and `23-08` owns that prose. An archive-root README
   would be a second place saying the same thing, with no owner and no gate.
3. **`D-04` says the archive ships no `make` targets and is not the teaching
   path.** An unannotated directory is consistent with that; a README at its
   root reads like an invitation.
4. **What the archive *is* already has three owned homes**:
   `docs/surface/examples/RETIREMENT-COUPLINGS.md`, the `Retirement` table
   (`23-10`), and `DOCS-17`'s ledger row (`23-11`).

`git ls-files archive/ | wc -l` → **265**, unchanged. `23-04`'s per-tree proof
reads correctly as written.

---

## CRITERION 7 — the accounted delta for this wave (`D-IMPL-196`)

**Tests added: NONE. Tests removed: NONE.** No test function was written or
deleted by this plan.

**Two node ids changed**, because `test_the_predicate_excludes_the_py_bearing_non_examples`
is parametrized over `PY_BEARING_NON_EXAMPLES`' keys and those keys are paths
that moved. Measured by collecting both sides — the pre-plan modules were
restored from `9da42d5` into the tree, collected, and copied back (verified
`git diff --quiet` after):

**LOST (2):**
```
tests/examples/test_artifact_schema_headers.py::test_the_predicate_excludes_the_py_bearing_non_examples[examples/03-harness-portability/legs]
tests/examples/test_artifact_schema_headers.py::test_the_predicate_excludes_the_py_bearing_non_examples[examples/external/00-hello-context/fixtures]
```

**GAINED (2):**
```
tests/examples/test_artifact_schema_headers.py::test_the_predicate_excludes_the_py_bearing_non_examples[archive/examples/03-harness-portability/legs]
tests/examples/test_artifact_schema_headers.py::test_the_predicate_excludes_the_py_bearing_non_examples[archive/examples/external/00-hello-context/fixtures]
```

Same test, same parametrization, new path in the id — the `23-04` "recovered by
re-path" category. **Net zero.** Both touched modules: 32 collected before,
32 after.

**Whole-suite total re-measured at the close:**

```bash
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest --collect-only -q
# 4223 tests collected in 6.61s
```

**4223**, identical to `23-04`'s post-move figure.

---

## Expected-RED reconciliation — including one the plan got wrong

| Leg | Plan's expectation | Measured | Verdict |
|---|---|---|---|
| `tests/examples` | still RED (`23-07`) | `39 failed, 234 passed, 41 skipped, 197 errors` — was 51 failed at wave 4; the delta is **exactly** the 12 schema-header failures this plan fixed. 197 errors unchanged | **RED as expected** |
| `make docs-strict` | still RED (`23-08`) | `EXIT=2`, `ERROR - Error reading page 'how-to/bind-a-harness-adapter.md': Snippet at path 'examples/03-harness-portability/artifacts/agents/agent-definition.yaml' could not be found` | **RED as expected** |
| `test_the_committed_report_is_current` | still RED (`23-10`) | **`47 passed`** after the report was regenerated last, per standing discipline | **PLAN WRONG — correction below** |
| **the four count floors** | **still RED** | **`114 passed`.** `MINIMUM_IMPLEMENTATIONS = 9`, `MINIMUM_GATE_CALL_SITES = 12`, `MINIMUM_PROJECTING_BODIES = 14`, `MINIMUM_RESOLVED_BINDER_SITES = 12` — every value byte-identical to `PHASE_BASE`, no floor lowered | **PLAN WRONG — correction below** |
| `make gate-tools` | red | `11 failed, 318 passed` — was `13 failed / 316 passed` at wave 4; the delta is **exactly** the two `test_snippet_gate.py` failures this plan fixed | **RED as expected** |
| `python -m tools.lints --all` | GREEN AND FALSE | `EXIT=0`, no output. Unchanged | **the known false green** |

### The correction: the count floors are green, and correctly green

Plan `23-05`'s verification block lists *"the four count floors"* among the legs
expected still red. **They are green and have been since plan `23-03`**, which
widened `SCANNED_TREES` to `('src', 'runtime', 'examples', 'archive')` and
`BINDER_SCANNED_TREES` to `('examples', 'archive')` — so the members that moved
are still counted, from their new home. `23-04`'s chunk breakdown likewise shows
zero failures in `tests/products`. The plan's expectation was carried from a
pre-`23-03` draft. **No floor was lowered to achieve this**, which is the thing
that would have mattered: all four constants are byte-identical to `PHASE_BASE`.

### The second correction: the coupling report went GREEN, and it is a CURRENCY gate

`docs/surface/examples/RETIREMENT-COUPLINGS.md` is generated and walks
`.planning/`, so the standing rule is to regenerate it **last**, in the venv,
after every planning write. Doing that turned
`test_the_committed_report_is_current` from RED to green:

```bash
PYTHONPATH=src:runtime .venv/bin/python tools/retirement_sweep.py --report   # EXIT=0
PYTHONPATH=src:runtime .venv/bin/python -m pytest tools/docs_tests/test_retirement_sweep.py -q
# 47 passed in 28.19s
git diff --stat docs/surface/examples/RETIREMENT-COUPLINGS.md   # 7 insertions(+), 6 deletions(-)
```

The plan expected it red. It was red only because it was **stale** — line
numbers had shifted under wave 4 and again under this plan's 8-line edit to the
header test. **Say plainly what this green does and does not mean:** it asserts
the committed report matches what the tool produces *today*. It asserts nothing
about whether the report is *right*. The whole diff:

- four line-number shifts in `test_artifact_schema_headers.py` rows;
- the `test_snippet_gate.py` row, now noting `constructed as
  archive/examples/00-quickstart/run.py` — **and still attributing the coupling
  to owner `16-18`, a plan `D-IMPL-152` retired.** That re-point is `23-10`'s;
- two rows for this plan's own `.planning/` writes, correctly excluded as *"the
  phase's own planning tree — not shipped, not published."*

Two things worth carrying to `23-10`: the owner column still names retired
plans, and the `path` column still reads `examples/00-quickstart` for a
constructed `archive/…` path — `PATH_TOKEN` stripping `archive/`, which is
exactly criterion 18's subject (`D-08`). The note column happens to preserve the
full path, so the information is not lost, only mis-keyed.

### A green gate that may be lying, restated for `23-06`

`python -m tools.lints --all` exits 0. It is **not** evidence about the four
citations `D-07` permits: `resolve_cited` falls back to **suffix** matching, so
`examples/04-cross-process/producer_child.py::resolve` in `src/ccf/products/
bind.py:74` resolves happily to the archived file and reports *checked and
passing*. Nothing in this plan changed that, and nothing in this plan should be
read as evidence that those four citations are correct.

---

## Boundary verification

```bash
git diff --name-only b87fe58..HEAD -- src/ runtime/ pyproject.toml        # 0
git diff --name-only b87fe58..HEAD -- public/ Makefile README.md .github/ # 0
git diff --name-only f380a68^..HEAD | wc -l                               # 222
git diff --name-only f380a68^..HEAD \
  | grep -v '^archive/' | grep -v '^tools/docs_tests/' | grep -v '^tests/examples/' | wc -l   # 0
git ls-files archive/ | wc -l                                             # 265
```

222 = 216 headers + 4 children + `tests/examples/test_artifact_schema_headers.py`
+ `tools/docs_tests/test_snippet_gate.py`. Nothing outside the three permitted
trees. `.planning/STATE.md` and `.planning/ROADMAP.md` untouched (`D-10`,
`D-15`). No Success Criterion authored, renumbered or edited. `CLNT-17` appears
nowhere — not in a file, not in a commit message.

No line-anchored Python citation was introduced:

```bash
PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/invariants/test_citation_coverage.py -q
# 5 passed        (run before EVERY commit in this plan)
```

---

## Deviations from Plan

**1. [Rule 1 — false statement in a control] The two skip reasons were reworded**
- **Found during:** Task 2
- **Issue:** the plan says the reasons *"remain accurate"*; they name plans
  16-17/16-18 as the retiring wave, and `D-IMPL-152` retired Phase 16 while
  this phase moved rather than deleted
- **Fix:** reworded to name the deletion `D-27`'s undecided half has yet to
  authorise, and to say the move happened at `23-04`
- **Files:** `tests/examples/test_artifact_schema_headers.py`
- **Commit:** `e8818eb`

**2. [Rule 2 — the guard the plan assumed] The `parents[N]` proof needed a
scrubbed environment**
- **Found during:** Task 1
- **Issue:** the plan's before/after run cannot distinguish a right depth from a
  wrong one in this venv, because the editable install masks both
- **Fix:** built a probe that removes the editable finder from `sys.meta_path`
  and drops repo `src`/`runtime` from `sys.path`, then asserts `import ccf`
  fails before loading the target
- **Files:** none in the repo (the probe is a scratch script, deliberately not
  committed — see "Deferred Issues")
- **Commit:** `f380a68` (the fix; the method is recorded in the message)

**3. [Recorded, not fixed] Three classes of prose drift**
- Logged to this phase's `deferred-items.md` under *"Wave 5 — three prose drifts
  nobody owns"*: five stale `examples/…` references in the header test's own
  docstrings (a module **no later plan in the phase owns**), the surviving
  `examples/external/README.md:50` row still listing `00-hello-context`, and 16
  archived prose lines inviting a reader to `python examples/…`. Left alone
  because task 2 is scoped to *"the path strings only"* and task 1 to *"only the
  `parents[N]` index"*.

---

## A defect I shipped and then fixed, recorded rather than smoothed

The final commit `f6d5821` went in **RED**. `deferred-items.md`, as I first
wrote it, carried two line-anchored Python citations:

```
- deferred-items.md:163 cites archive/examples/04-cross-process/producer_child.py:3
- deferred-items.md:174 cites tools/check_schema_headers.py:150-153
assert 2 <= 0
```

`D-IMPL-123`'s ceiling is **ZERO** and `D-IMPL-114` rules that prose cites
`path.py::Symbol`. I ran `tests/invariants/test_citation_coverage.py` before the
first three commits and it passed each time; on the fourth I ran it in the same
tool call as `git add`/`git commit` **without an `&&` between them**, so the
commit proceeded over a failing gate. That is a process defect of mine, not the
plan's, and it is exactly the class the brief warned had *"bitten the phase
twice"*.

Fixed in the following commit by converting both to the ruled form — the
docstring named by file rather than by line, and
`tools/check_schema_headers.py::ARTIFACT_GLOBS` instead of `:150-153`. **The
ceiling was NOT raised.** `5 passed` after.

---

## Deferred Issues

- **No standing gate can witness S-8.** The depth fix is proven, but the only
  witness is an uncommitted probe. Committing it would add a test — a criterion-7
  addition this plan was not authorised to make. `23-12`'s call.
- The three headered documents below the gate's glob (pre-existing, plan 15-12).

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or trust-boundary
schema was introduced; every edit is a path string or a `parents[N]` index.

---

## Commits

| Task | Commit | What |
|---|---|---|
| 1 | `f380a68` | the four relocated children resolve the repo root again |
| 2 | `e8818eb` | every `$schema` header in the archive resolves from its own directory again |
| 3 | `82e1024` | `SNIPPET_SOURCE` names the archived quickstart, and says who inherited it |
| — | (final) | this summary, the deferred items, and the regenerated coupling report |
