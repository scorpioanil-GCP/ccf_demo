---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 08
subsystem: the published tree re-pointed at the archive, and the two witnesses proven to be two
tags: [DOCS-17, criterion-4, criterion-5, criterion-6, criterion-16, criterion-17, criterion-18, D-IMPL-189, red-before-green]
status: complete
requires:
  - phase: 23-02
    provides: criterion 17's allowlist member `archive/examples/` and criterion 18's PATH_TOKEN alternation branch — without either this plan is red on a correct tree
  - phase: 23-04
    provides: the ten trees at `archive/examples/`, 265 files
  - phase: 23-05
    provides: the repaired `parents[N]` depths, without which the two re-pointed shell commands would not run
provides:
  - "111 published references re-pointed — 102 includes + 9 prose across exactly 15 pages"
  - "the edit PROVEN a pure prefix substitution: reverse-substitution reproduces all 15 files byte-identically"
  - "criterion 5 discharged — the strict build stayed GREEN on a prose-only mutation the path walk caught"
  - "criterion 16's include half discharged with the non-empty counts measured, and the vacuous pass exhibited"
  - "T-23-29 discharged by DEMONSTRATION — step 4 watched firing over archive-sourced content, not merely watched silent"
  - "a THIRD blind spot found: an included BODY publishes a stale path no witness in this phase reads"
  - "two of the plan's own expected-red predictions falsified, with the reason"
affects:
  - "23-09 (the 13 `make example-*` strings on these same pages; and deferred item 7, the archive's own self-labels)"
  - "23-11 (criterion 6's re-measured value: 111 at the new prefix, 0 at the old)"
  - "23-12 (criterion 7's accounted delta — this plan adds ZERO tests, and that is measured)"
tech-stack:
  added: []
  patterns:
    - "prove a prefix substitution by REVERSING it and diffing against HEAD — a diff line count cannot see a smuggled edit"
    - "a control that only ever goes silent is not a control: plant the violation and watch the silent step fire"
    - "restore by INVERSE MUTATION plus sha256 -c, never by `git checkout --` on an uncommitted fix"
key-files:
  created: []
  modified:
    - public/tutorial/adopters-guide.md
    - public/tutorial/demo-walkthrough.md
    - public/how-to/compose-a-workflow-with-hitl.md
    - public/how-to/run-agents-cross-process.md
    - public/how-to/swap-the-artifact-store.md
    - public/how-to/grant-and-revoke-a-skill.md
    - public/how-to/bind-a-harness-adapter.md
    - public/reference/artifacts/control-plane-artifacts.md
    - public/reference/artifacts/product-registration.md
    - public/reference/artifacts/agent-definitions.md
    - public/reference/artifacts/prompt-artifacts.md
    - public/reference/artifacts/skill-catalog.md
    - public/reference/artifacts/skill-grants.md
    - public/reference/artifacts/task-definitions.md
    - public/reference/artifacts/workflow-definitions.md
    - .planning/phases/23-the-archive-move-retiring-the-ten-condemned-example-trees-wi/deferred-items.md
decisions:
  - "The plan's wave-1 slash-requiring figure of 88 does NOT reproduce — the measured value is 105. Both recorded; the hazard direction is unchanged, the magnitude is not."
  - "Neither of the plan's two named expected-reds is red. Both are green for a stated reason, and the plan's inference (`a green here would mean one of the two halves has drifted`) is itself wrong at this point in the phase."
  - "The stale rendered include bodies are NOT fixed here — the fix is under `archive/examples/`, outside this plan's `<files>`, and `run.py:1095` is a live output string. Deferred item 7, handed to 23-09."
  - "`.planning/STATE.md` and `.planning/ROADMAP.md` left untouched per `D-10`; no `state.*` and no `roadmap.*` writer invoked."
requirements-completed: []
metrics:
  duration: ~75 min
  completed: 2026-08-24
  tasks: 3
  commits: 3
---

# Phase 23 Plan 08: The published tree, re-pointed — and the two witnesses proven to be two — Summary

**All 111 published references now name the archive, `make docs-strict` exits 0
on all four steps, and criterion 5's independence claim held under the mutation
designed to break it: a prose-only revert turned the path walk RED while the
strict build stayed GREEN at exit 0 with zero warnings.** Six controls ran, every
one restored byte-identically and verified by `sha256sum -c`. **Three of the six
produced results the plan did not predict, and all three are recorded as
corrections rather than smoothed.** The wave also found a defect neither witness
can see — an included *body* publishing a stale path into the rendered site —
which is logged as deferred item 7 rather than absorbed.

---

## Task 1 — re-measure, re-point, re-measure

### Before, measured (not carried)

```bash
PAT='examples/(00-quickstart|01-agent-basics|02-skilling|03-harness-portability|04-cross-process|05-workflow-hitl|06-decision-replay|07-artifact-store-mcp|08-e2e-demo|external/00-hello-context)'
git grep -nE "$PAT" -- public/ | wc -l                        # 111
git grep -nE "$PAT" -- public/ | grep -c -- '--8<--'          # 102
git grep -nE "$PAT" -- public/ | grep -v -- '--8<--' | wc -l  #   9
git grep -lE "$PAT" -- public/ | wc -l                        #  15
```

**111 / 102 / 9 / 15 — criterion 4's pinned figures, exactly.** No stop, no
report. The per-page breakdown reproduces `23-RESEARCH.md` §6.1 row for row:

| Page | includes | prose |
|---|---:|---:|
| `public/tutorial/adopters-guide.md` | 35 | 0 |
| `public/tutorial/demo-walkthrough.md` | 14 | 4 |
| `public/how-to/compose-a-workflow-with-hitl.md` | 14 | 1 |
| `public/how-to/run-agents-cross-process.md` | 10 | 1 |
| `public/how-to/swap-the-artifact-store.md` | 6 | 1 |
| `public/how-to/grant-and-revoke-a-skill.md` | 6 | 1 |
| `public/how-to/bind-a-harness-adapter.md` | 6 | 1 |
| `public/reference/artifacts/control-plane-artifacts.md` | 3 | 0 |
| `public/reference/artifacts/product-registration.md` | 2 | 0 |
| six remaining `reference/artifacts/*.md` | 1 each | 0 |
| **total** | **102** | **9** |

### CORRECTION 1 — the wave-1 slash-requiring figure does not reproduce

The plan states, twice and in bold, that a trailing-slash-requiring regex yields
**88**. It does not. Measured at `HEAD` before any edit, and again after:

```bash
git grep -nE "$PAT"  HEAD -- public/ | wc -l   # 111   slash-free
git grep -nE "$PAT/" HEAD -- public/ | wc -l   # 105   slash-REQUIRING
```

**Six references lack a trailing slash, not twenty-three.** All six are prose,
and they are named rather than counted:

```
public/how-to/bind-a-harness-adapter.md:16        `examples/03-harness-portability`
public/how-to/compose-a-workflow-with-hitl.md:17  `examples/05-workflow-hitl`
public/how-to/grant-and-revoke-a-skill.md:15      `examples/02-skilling`
public/how-to/run-agents-cross-process.md:17      `examples/04-cross-process`
public/how-to/swap-the-artifact-store.md:15       `examples/07-artifact-store-mcp`
public/tutorial/demo-walkthrough.md:10            `examples/08-e2e-demo`
```

**The hazard the plan names is real and unchanged in direction — the include
count is 102 under either regex, so a slash-requiring measurement reads as
partially correct rather than broken. Only the magnitude was wrong: the broken
form loses 6, not 23.** The measurement used the slash-free form throughout.

`D-IMPL-189`'s own scope figures (*"99 snippet includes and 108 prose paths"*)
are named here as **not matching the tree** and are quoted nowhere else in this
document.

### The substitution, and why it is provably nothing more

A single bounded `perl -0pi` prefix substitution across the 15 pages the grep
found, with a negative lookbehind `(?<!archive/)` and the ten tree names
enumerated. Verified beforehand that no match had a preceding path segment
(`git grep -ohE ".{0,12}$PAT"` shows only `--8<-- "`, a backtick, or a space)
and that `public/` contained **zero** `archive/` references to double-prefix.

**The purity proof is the reverse substitution, not the diff.** A diff line
count cannot distinguish a prefix insertion from a prefix insertion plus a
smuggled word:

```bash
while read -r f; do
  git show "HEAD:$f" > orig; sed 's|archive/examples/|examples/|g' "$f" > rev
  diff -q orig rev || echo "IMPURE: $f"
done < pages.txt
# PURE PREFIX SUBSTITUTION ACROSS ALL 15 PAGES: YES
```

Every one of the 15 files, reverse-substituted, is **byte-identical to `HEAD`**.
`git diff --shortstat`: `15 files changed, 111 insertions(+), 111 deletions(-)`.

*(Recorded because it cost time: a `grep -vE '^(\+\+\+|---)'` filter over
`git diff -U0` silently swallows all 102 include DELETION lines, because a
deleted `--8<--` line renders as `---8<--` and matches the header filter. The
counts looked wrong — 120 where 222 was expected — for exactly that reason. This
is standing hazard 2 in miniature: the filter went quiet, not red.)*

### After, measured

```bash
PATA='archive/examples/(00-quickstart|…|external/00-hello-context)'
git grep -nE "$PATA" -- public/ | wc -l                        # 111
git grep -nE "$PATA" -- public/ | grep -c -- '--8<--'          # 102
git grep -nE "$PATA" -- public/ | grep -v -- '--8<--' | wc -l  #   9
git grep -lE "$PATA" -- public/ | wc -l                        #  15
# and the un-repointed remainder:
git grep -nE '(^|[^/])\bexamples/(…)' -- public/ | grep -v 'archive/examples/' | wc -l   # 0
```

**Criterion 6's movement, stated with the new value: `examples/…` → 111 → 0;
`archive/examples/…` → 0 → 111.** Same 102 / 9 / 15 decomposition at the new
prefix. Plan `23-11` writes this into the ledger.

Every target checked on disk, not inferred: **102 parsed include targets, 0
missing, 44 distinct files**; all 8 distinct prose targets resolve.

### The three bound checks

| # | Check | Before | After | Verdict |
|---|---|---:|---:|---|
| 1 | `git grep -c 's1-00-companies-over-revenue\|s1-01-hello-context-product' -- public/` | **7** | **7** | UNCHANGED — all seven on `public/concepts/answers-no-document-contains.md`, `D-01` and `D-IMPL-189` intact |
| 2 | `git grep -c 'hw1-' -- public/` | **4** | **4** | UNCHANGED (2 on `answers-no-document-contains.md`, 2 on `run-agents-cross-process.md`) |
| 3 | `git diff --name-only -- public/` | — | **15** | exactly the 15 pages; `git diff --name-only` over the whole tree names nothing else |

### The two runnable commands — run, not asserted

The two sites carry a **byte-identical** command string
(`md5sum` of line 18 == `md5sum` of line 310 == `e87a1d39fcb9914d…`):

```bash
PATH=.venv/bin:$PATH   # so `python` is the venv interpreter the page's reader would have
PYTHONPATH=src:runtime python archive/examples/08-e2e-demo/run.py
# EXIT=0, 50 lines, ending "examples/08-e2e-demo: OK"
```

Run **twice**; the two outputs are byte-identical (`diff -q` clean), so the
re-pointed command is not merely exit-0 but deterministic — which is what the
page claims of it.

### FINDING (not a rewrite) — the page contradicts itself 286 lines apart

Per the plan's instruction that a sentence needing a rewrite is a finding: the
prose immediately under both commands says *"or `make example-08`; it also runs
inside `make examples` and therefore `make ci`, deterministically, on every
commit."* **That sentence becomes false at plan `23-09`**, which deletes
`example-08` and reduces the `examples:` aggregate to one member. It is left
untouched here because the 13 `make example-*` strings and the ten Makefile
targets are bound by a bijection gate and must move in the same wave. Named for
`23-09`.

**The larger finding is deferred item 7** (`deferred-items.md`, commit
`652106b`): two of the 120 resolved includes render a *bare* `examples/` path
into the built site — including, at `demo-walkthrough.md:304`, a docstring
telling the reader to run `examples/08-e2e-demo/run.py`, 286 lines below the
command this wave re-pointed. `grep -rho "examples/08-e2e-demo/run.py" site` →
**3**. Neither witness reads rendered bodies, so all four `docs-strict` steps are
green over it.

**Commit `276f900`.**

---

## Task 2 — criterion 5, RED before GREEN

**Every exit code below was read with no pipe.** `23-RESEARCH.md` §14 records
`mkdocs build --strict 2>&1 | tail -12` printing a `SnippetMissingError`
traceback and then `EXIT=0`; every build here redirected to a file and read `$?`
directly.

**This plan adds ZERO tests** (criterion 7's naming obligation): all six controls
are mutations of the shipped tree, run and reverted. Measured:
`git diff --stat 276f900~1..HEAD -- tools/ tests/` is **empty**; the docs gate
trees collect **329** at both ends and `tests/` collects **4233** at both ends.

### S-0 — the whole-tree pre-fix RED, reproduced rather than inherited

Before running the scoped controls, all 15 pages were reverted to `276f900~1` —
**after** the fix was committed, per `23-02`'s discipline and standing hazard 3.

| Witness | Result |
|---|---|
| `tools/docs_tests/test_no_stale_example_paths.py` | **4 failed / 13 passed**, `EXIT=1` — `test_every_prose_path_reference_resolves_on_disk`, `test_every_snippet_include_resolves_on_disk`, `test_the_unmodified_copy_passes`, `test_a_tests_examples_path_is_not_mis_reported_as_a_bare_examples_path` |
| `mkdocs build --strict` | `EXIT=1`, `SnippetMissingError: Snippet at path 'examples/03-harness-portability/artifacts/agents/agent-definition.yaml' could not be found` |

That reproduces 4 of the 9 reds the orchestrator measured. Restored:
`git diff --quiet HEAD -- public/` clean, both witnesses green
(`17 passed in 0.16s`; build `EXIT=0`).

### The five controls

| # | Mutation | Prediction | Observed | Verdict |
|---|---|---|---|---|
| **S-1** | `bind-a-harness-adapter.md:63` include reverted to `examples/…` | strict build fails with `SnippetMissingError` naming that exact path | `EXIT=1`; `SnippetMissingError: Snippet at path 'examples/03-harness-portability/artifacts/agents/agent-definition.yaml' could not be found` | **HELD** |
| **S-2** | same mutation, build not re-run | `test_every_snippet_include_resolves_on_disk` fails naming `page:line -> target` | `2 failed / 15 passed`; offender `public/how-to/bind-a-harness-adapter.md:63 -> examples/03-harness-portability/artifacts/agents/agent-definition.yaml` | **HELD, plus an unpredicted second red — see CORRECTION 2** |
| **S-3** | `grant-and-revoke-a-skill.md:15` **prose** path reverted | path walk fails **and the strict build stays GREEN** | `1 failed / 16 passed`, offender `…grant-and-revoke-a-skill.md:15 -> examples/02-skilling`; build `EXIT=0`, `0` lines matching `SnippetMissingError|WARNING|ERROR` | **HELD — this is the criterion** |
| **S-14** | `_prose.published_pages()` → `[]` | `test_the_published_tree_is_populated` and `test_the_scan_finds_path_tokens_to_check` fail | `3 failed / 14 passed` — both predicted, **plus** `test_the_walk_does_not_depend_on_the_process_cwd` | **HELD, plus an unpredicted third red — see CORRECTION 3** |
| **S-4** | `INCLUDE_ALLOWED_PREFIXES` → `("",)` | `23-02`'s guard test fails | `14 failed / 39 passed`, including all three of `23-02`'s guards by name | **HELD, harder than predicted** |

### S-3 is the criterion, and it discharged

The strict build over a tree with one prose path reverted:

```
EXIT=0
INFO    -  Documentation built in 3.39 seconds
```

Zero warnings, zero errors, exit 0 — **while the path walk was red naming the
exact page and line.** `check_paths` covers includes; it does not read running
prose. **The two witnesses are genuinely two, and the proof is witness A's
silence, not a second red.**

The asymmetry is worth stating precisely, because it is not symmetric: witness
B's *prose* half sees include lines too (S-2 reddened both halves), but witness
B's *include* half does **not** see prose (S-3 reddened only the prose half).
Witness A sees neither prose form.

### S-4, and what it says about criterion 17

`23-RESEARCH.md` §15 recorded S-4 as catching **NOTHING** — *"No test anywhere
references it… the boundary this phase must widen is itself unguarded."* Plan
`23-02` closed that. Re-run here over a tree that now genuinely depends on the
widening, the guard fires **14 times**, including:

```
FAILED …::test_the_publication_allowlist_has_exactly_the_expected_membership
FAILED …::test_no_allowlisted_prefix_is_empty
FAILED …::test_the_widening_is_the_narrow_one_and_does_not_open_the_archive_tree
FAILED …::test_an_internal_tree_still_escapes_the_allowlist[src/ccf/products/bind.py]           (+4 more params)
FAILED …::test_include_using_traversal_trips_the_include_escape_rule                            (+2 more forms)
```

**And the step-1 scan itself exits 0 with the boundary off** — which is exactly
why the guard had to be a *test* rather than a scan result. Restored:
`sha256sum -c` OK, `git diff --quiet` clean, `53 passed`.

### CORRECTION 2 — S-2 reddens two tests, not one

The plan predicts `test_every_snippet_include_resolves_on_disk`. Both it **and**
`test_every_prose_path_reference_resolves_on_disk` fail, because the prose scan
reads the raw line and an `--8<--` line carries a path token. Both are witness
B, so criterion 5's independence claim is unaffected — but the prediction as
written was incomplete and is corrected rather than glossed.

### CORRECTION 3 — S-14 reddens three tests, and two others pass VACUOUSLY

The plan predicts the two non-vacuity floors. A third fired:
`test_the_walk_does_not_depend_on_the_process_cwd`.

**The more important half is what stayed green.** Over the empty page list,
`test_every_prose_path_reference_resolves_on_disk` and
`test_every_snippet_include_resolves_on_disk` both **passed** — vacuously, on
`[]`. That is the demonstration criterion 16 exists for, exhibited rather than
argued: *the two assertions that matter cannot detect their own subject
disappearing, which is precisely why the two floors sit beside them.*

### CORRECTION 4 — a prediction the plan did not make, recorded because it was checked

The plan's S-1 row cites `bind-a-harness-adapter.md:63` from the research. The
line number still holds after the re-point (the substitution changed no line
counts), and it is the same include the whole-tree S-0 build happened to fail on
first — so S-1's red and S-0's red name the same path. They are distinct runs
(one file mutated vs fifteen) and both are recorded.

### Criterion 16's include half — the counts, measured

A check that could pass over an empty set is not a check, so the sets are
reported with sizes rather than asserted non-empty:

```
_prose.PUBLIC_DIR                     /home/parkave/ccf_code/public   is_dir: True
_prose.published_pages()              44 pages
prose_path_tokens(pages)              66 tokens
  of which archive/-prefixed          50
prose_path_offenders(pages)            0
include_offenders(pages)               0
```

**Both floors saw a non-empty set; both offender lists are empty over it.**

### Restoration discipline

Every mutation reverted by **inverse mutation**, then verified two ways —
`sha256sum -c` against a hash taken before the mutation, and `git diff --quiet`
on the file. All five reported byte-identical. After the last control,
`git status --short` (ignoring three pre-existing untracked files under
`references/`) is empty. **No `git checkout --` was used on an uncommitted fix,
and no `git stash` was used at all.**

**No commit: task 2 changes no tracked file by design. Its evidence is this
section.**

---

## Task 3 — `make docs-strict`, four steps, each on its own

`make docs-strict` → **`EXIT=0`**. Run in the foreground. Each step re-run
individually, and each result recorded separately rather than read off the
target:

| # | Step | Exit | Output |
|---|---|---:|---|
| 1 | `tools/publish_scan.py --pre-build` | **0** | **0 lines. `pub04-include-escape` findings: 0.** This is the step that fails with 102 escapes without criterion 17's allowlist member. |
| 2 | `tools/publish_scan.py docs/schemas` | **0** | 0 lines |
| 3 | `python -m mkdocs build --strict` | **0** | `Documentation built in 3.44 seconds`. **Read from `$?` on an unpiped command.** |
| 4 | `tools/publish_scan.py site` | **0** | **0 lines** — see below, because "0 lines" is not by itself evidence |

### Step 4 — the named unknown, and why its silence is a real green

`23-RESEARCH.md` §14.4: *"I did not verify what a widened
`INCLUDE_ALLOWED_PREFIXES` does to the post-build `site` scan… I did not
exercise it against archive-sourced content."* This is the first run of step 4
over a site built from archive-sourced includes, and threat **T-23-29** puts it
on `mitigate`. A silent step is exactly what T-23-29 is about, so it was
**measured for reach and then made to fire**:

**Reach.** `require_populated(site, "post-build scan")` → **104 files walked**;
45 of them HTML. The archive's content is genuinely in there: the string
`payment-cycle-detect` (which exists only inside the archived e2e demo's run
output) appears on **1** rendered page, as does the `run.py` body.

**Fire (control S-29, new this wave).** A whitepaper shingle taken from
`publish_scan.whitepaper_shingles()` was appended to
`archive/examples/08-e2e-demo/artifacts/scenario.yaml` — an **archived** file
the site includes — and the site rebuilt:

```
mkdocs build --strict            EXIT=0     (the build cannot see this; it is not a path)
tools/publish_scan.py site       EXIT=1
  2 publish-safety violation(s). Rework the content; there is no exception mechanism (D-20).
  site/search/search_index.json:1            pub01-whitepaper-shingle …
  site/tutorial/demo-walkthrough/index.html:1 pub01-whitepaper-shingle …
```

**Step 4 catches a boundary violation that arrives through an archive-sourced
include, and names the rendered page.** Restored by inverse mutation,
`sha256sum -c` OK, rebuilt, step 4 back to `EXIT=0` / 0 lines. **T-23-29 is
discharged by demonstration, not by silence.**

### The docs gate suite

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests tools/publish_scan_tests -q
# 1 failed, 328 passed in 60.20s     EXIT=1
FAILED tools/docs_tests/test_requirement_ledger.py::test_every_cited_path_in_a_status_cell_resolves_as_written
```

**One red, and it is plan `23-11`'s**, exactly as the orchestrator recorded:

```
EXAM-01 cites `examples/external/00-hello-context/run.py`, which is not in the
tree at all. The citation lint counts this as an unresolved path and drops it
WITHOUT a finding — the second silent hole, and the one that catches a file MOVE
```

**The nine measured reds at the start of this wave are now one.** The four in
`test_no_stale_example_paths.py` and the three in `test_mkdocstrings_gate.py`
are green by this wave's re-point.

### CORRECTION 5 — both of the plan's expected-reds are GREEN, and the plan's inference is wrong

```bash
pytest tools/docs_tests/test_documented_commands_exist.py tools/docs_tests/test_retirement_sweep.py -q
# 57 passed in 29.20s     EXIT=0
```

- **`test_documented_commands_exist`** — the plan says *"Expect … to be STILL RED"*
  and *"a green here would mean one of the two halves has drifted."* **Neither
  half has changed.** The 13 `make example-*` strings are untouched (this plan
  edited only path references) and the ten Makefile targets still exist, so the
  bijection holds and green is the *correct* state. It goes red when `23-09`
  deletes the targets, and green again when `23-09` edits the 13 strings in the
  same wave. It was never red — it is not in the orchestrator's measured-red list
  either.
- **`test_the_committed_report_is_current`** — also green. The committed
  `RETIREMENT-COUPLINGS.md` is current at `HEAD`.

**Everything else in the two trees is green.** No other red to treat as a
finding.

### The other legs

```bash
python -m tools.lints --all                     # EXIT=0
python tools/retirement_sweep.py --report       # EXIT=0
#   395 coupling rows across 117 files (274 outside the three swept trees); 1935 files scanned
diff -q <before> docs/surface/examples/RETIREMENT-COUPLINGS.md   # identical
```

Regenerated **last**, in the venv, after this wave's `public/` write, per `D-05`
— and it produced **no diff**, so there is no report commit.

**Standing hazard 1 confirmed live:** `tools.lints --all` exits 0 on this tree.
It exited 0 on the pre-fix tree too. It is not evidence for this wave's work and
was not used as any.

### An observation for `23-10`, and it is a CONFIRMATION rather than a new finding

**111 references changed prefix and the coupling report moved zero bytes.** The
cause is already recorded: `23-CONTEXT.md`'s `D-IMPL-194` backlog item — *"the
coupling report's SOURCE detection is blind to the phase's heaviest pages."*
Confirmed here, and sharper than before: the 15 re-pointed pages appear in the
report **only as targets** of rows sourced elsewhere —

```
| `tools/lints/tests/test_citations.py` | 350 | `public/tutorial/adopters-guide.md` | … |
| `archive/examples/08-e2e-demo/README.md` | 115 | `public/tutorial/demo-walkthrough.md` | … |
```

— and never as sources, though `adopters-guide.md` carries 35 includes into the
ten trees. **Explicitly out of scope** (`23-CONTEXT.md` deferred, and no locked
criterion rests on the report's counts). Recorded so `23-10` does not read the
report's stability as a measurement of this wave.

**No commit: task 3 changes no tracked file.**

---

## Verification block

| Check | Result |
|---|---|
| `make docs-strict` | **EXIT=0**, four steps recorded individually above |
| `git grep -nE 'examples/(…)' -- public/` with no `archive/` prefix | **0** |
| re-pointed references sum | **111** across **15** pages (102 + 9) |
| `git grep -c 's1-0' -- public/` | **7** before, **7** after |
| `git grep -c 'hw1-' -- public/` | **4** before, **4** after |
| `git diff --name-only b87fe58..HEAD -- public/` | **15** files |
| `git diff b87fe58..HEAD -- src/ runtime/ pyproject.toml` | **4** changed lines, the four from `23-06` |
| tests added by this plan | **0**, measured (`git diff --stat 276f900~1..HEAD -- tools/ tests/` empty) |
| docs-gate collection | **329** at both ends |
| `tests/` collection | **4233** at both ends |

Verified below.

---

## Deviations from Plan

**No Rule 1–4 deviations. Nothing was auto-fixed and nothing was absorbed.**

Five corrections to the plan's own predictions, all recorded above rather than
smoothed: the slash-requiring figure (105, not 88); S-2's second red; S-14's
third red plus the two vacuous passes; the S-1 line-number note; and both
expected-reds being green with the plan's inference about that green being
wrong.

One finding raised and **not** fixed, with the reason: deferred item 7, the
included bodies that publish stale paths. It is outside this plan's `<files>`
(the fix lives under `archive/examples/`), it touches a live output string, and
the durable fix is a witness this repo does not have. Handed to `23-09`.

`.planning/STATE.md` and `.planning/ROADMAP.md` are untouched, per `D-10`
(*"Executors leave both files alone"* — updated once at phase completion or at a
checkpoint the orchestrator calls). **No `state.*` and no `roadmap.*` writer was
invoked.** No requirement was marked complete: `DOCS-17` is verdicted once, at
`23-11`.

## Threat Model Dispositions

| Threat | Disposition | How discharged |
|---|---|---|
| T-23-29 — step 4 never exercised against archive-sourced content | mitigate | Step 4 run and recorded on its own (104 files, 0 findings), reach proven (archive content is in the rendered site), and **watched FIRING** via control S-29 |
| T-23-30 — a piped exit code | mitigate | Every exit code read from `$?` on an unpiped command; no `\| tail` before an `echo $?` anywhere in this wave |
| T-23-31 — the seven published `s1-01` references | mitigate | Bound check 1: 7 → 7. Bound check 3: 15 files changed, and `answers-no-document-contains.md` is not among them |
| T-23-32 — one witness masquerading as two | mitigate | S-3: prose-only mutation, path walk RED, strict build `EXIT=0` with zero warnings. Independence proven by A's silence |
| T-23-33 — a walk that looked at nothing | mitigate | S-14 run; 44 pages / 66 tokens / 50 archive-prefixed recorded; and the two vacuous passes exhibited |
| T-23-SC — package installs | accept | No package installed |

## Requirements

`DOCS-17` — advanced, not discharged. Criterion 4, criterion 5, criterion 16's
include half and criterion 6's re-measured value are complete; the row is
verdicted at `23-11`.

## Success Criteria

- [x] Criterion 4 — 102 + 9 across 15 pages re-pointed; `docs-strict` exits 0 on all four steps
- [x] Criterion 5 — S-1 / S-2 / S-3 watched RED, and the strict build's **silence** on the prose mutation recorded as the independence proof
- [x] Criterion 16's include half — non-empty counts recorded (44 / 66 / 50), and the vacuous pass exhibited
- [x] Criterion 6 — re-measured value captured for `23-11`: 111 → 0 at the old prefix, 0 → 111 at the new
- [x] Step 4 recorded on its own, and made to fire

## Commits

| Commit | Task | What |
|---|---|---|
| `276f900` | 1 | 111 references re-pointed across 15 pages, proven a pure prefix substitution |
| `652106b` | 1 (finding) | deferred item 7 — the included-body blind spot |
| _(this)_ | — | SUMMARY |
