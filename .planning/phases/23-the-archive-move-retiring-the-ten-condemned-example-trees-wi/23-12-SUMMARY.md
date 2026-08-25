---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 12
subsystem: verification
tags: [ci, criterion-rollup, non-vacuity, sabotage, accounted-delta]
requires:
  - "23-11 (the ledger verdicts and the D-08 movement)"
provides:
  - "the criterion-by-criterion evidence roll-up the close panel and Dave read"
  - "the closing six-leg pipeline measurement, every leg in the foreground"
  - "the non-vacuity register and the checked-and-left register"
affects:
  - ".planning/phases/23-.../deferred-items.md"
  - "docs/surface/examples/RETIREMENT-COUPLINGS.md"
tech-stack:
  added: []
  patterns:
    - "chunked foreground test leg with coverage PROVEN by sum + two-way set-equality + pairwise disjointness"
    - "accounted delta by node id, with the archive re-path treated as recovery rather than loss"
key-files:
  created:
    - ".planning/phases/23-.../23-12-SUMMARY.md"
  modified:
    - ".planning/phases/23-.../deferred-items.md"
decisions:
  - "make ci is discharged as its own ten commands, proven complete by `make -n ci`, because the pipeline measures ~870s against a 600s foreground cap and backgrounding it is the prohibited move"
  - "criterion 7 gated on the empty lost-set and the named-addition roster, never on 4105, 4113, 515 or 521"
metrics:
  duration: "one wave"
  completed: "2026-08-25"
---

# Phase 23 Plan 12: The Closing Pipeline and the Eighteen-Criterion Roll-Up

**Six legs at exit 0, a chunk plan whose coverage is proven three ways, and
eighteen criteria each carrying a command a reader can re-run — plus a `make ci`
that had been RED since Wave 10 and that no wave had seen.**

---

## THE HEADLINE: `make ci` WAS RED, AND THIS IS THE FIRST FULL-SUITE RUN SINCE WAVE 10

Chunk 3's first foreground run came back **`1 failed, 963 passed, 22 skipped`**:

```
tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
  1 unanchored citations of Python targets are in D-IMPL-123's scope, ceiling 0
  - .planning/phases/23-.../deferred-items.md:315
      cites archive/examples/08-e2e-demo/run.py:4
```

Bisected exactly: `git log -S 'archive/examples/08-e2e-demo/run.py:4'` names
**`d0ed316`** — Wave 10's summary commit, which wrote deferred-item 8 and quoted
item 7's two stale lines in the `path.py:LINE` form `D-IMPL-114` forbids and
`D-IMPL-123` pins at a ceiling of **ZERO**.

**This is the `21.1-09` defect class, verbatim: a gate nobody runs is a gate
that cannot fail.** Waves 10 and 11 both recorded `tools/docs_tests`,
`gate-tools` and targeted module runs. Neither ran `tests/invariants`. The brief
for this plan stated the tree had "NO red anywhere" — measured over
`tools/docs_tests` and a `tests/examples` collection, which is exactly the
partial window that let it live for two waves.

**Fixed by CONVERSION, not by raising the ceiling** (`8e431eb`), on `21.1-09`'s
precedent. Line 4 of that file sits inside a module docstring, so no `::Symbol`
anchor exists; the reference is now spelled in prose against the bare path that
the same paragraph's line 263 already used. Re-run: `5 passed`.

---

## Criterion 15 — the chunk plan, PROVEN before it was run

`make ci` is ten commands (`make -n ci`, verbatim, with `gate-tools`
de-duplicated by make itself):

```
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all
PYTHONPATH=src:runtime .venv/bin/python -m mypy
PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 .venv/bin/python -m pytest -q
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/lints/tests -q
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/publish_scan_tests tools/docs_tests -q
PYTHONPATH=src:runtime .venv/bin/python examples/hw1-harness-clients/runner/drive.py
PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py --pre-build
PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py docs/schemas
PYTHONPATH=.:src:runtime .venv/bin/python -m mkdocs build --strict
PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py site
```

### DEVIATION, NAMED RATHER THAN SMOOTHED: `make ci` was NOT run as one command

The plan's task 2 says *"Then run `make ci` end to end and record its exit
code."* **It cannot be done in the foreground on this host.** The foreground
tool cap is **600 s**; the measured pipeline is ≈ **870 s** (test leg 653 s +
gate-tools 72 s + typecheck ≈ 30 s + docs-strict ≈ 30 s + the rest). The only
way to fit it into one call is to background it — the exact move criterion 15
exists to forbid, and the move that has read as green twice in this project's
history while dying at 68 %.

So `make ci` is discharged as **its own ten commands**, each run in the
foreground, each exit code read with no pipe, with `make -n ci` printed above as
the proof that the ten are the complete command list and that nothing was
skipped. This is the same decomposition `22-05` used. **It is a deviation from
the plan's literal instruction and it is recorded as one.**

### The three coverage properties, with the printed output

```
$ .venv/bin/python -m pytest --collect-only -q | tail -1
4233 tests collected in 5.87s
```

| Chunk | Paths | Collected |
|---|---|---:|
| 1 | `tests/examples tests/products` | 1007 |
| 2 | `tests/client tests/conformance tests/deployment` | 1056 |
| 3 | `tests/halflife tests/invariants tests/graph tests/agents tests/controlplane tests/crossproc` | 986 |
| 4 | the remaining 27 top-level entries | 1184 |

```
=== PROPERTY 1: SUM ===
1007 + 1056 + 986 + 1184 = 4233   full=4233
SUM PROPERTY: PASS

=== PROPERTY 2: SET-EQUALITY, BOTH DIRECTIONS ===
union lines=4233  union distinct=4233  full distinct=4233
-- in FULL but not in UNION (comm -23):   count=0
-- in UNION but not in FULL (comm -13):   count=0
SET-EQUALITY: PASS (both directions empty)

=== PROPERTY 3: PAIRWISE DISJOINTNESS ===
chunk 1 ^ chunk 2 = 0
chunk 1 ^ chunk 3 = 0
chunk 1 ^ chunk 4 = 0
chunk 2 ^ chunk 3 = 0
chunk 2 ^ chunk 4 = 0
chunk 3 ^ chunk 4 = 0
```

### The four chunks in the FOREGROUND, summary lines verbatim

| Chunk | Exit | Summary line |
|---|---:|---|
| 1 | 0 | `970 passed, 37 skipped, 9 warnings in 115.73s (0:01:55)` |
| 2 | 0 | `997 passed, 59 skipped, 4 warnings in 96.14s (0:01:36)` |
| 3 (pre-fix) | **1** | `1 failed, 963 passed, 22 skipped, 104 warnings in 125.12s (0:02:05)` |
| 3 (post-fix) | 0 | `964 passed, 22 skipped, 104 warnings in 126.28s (0:02:06)` |
| 4 | 0 | `1184 passed, 4 warnings in 314.45s (0:05:14)` |

**Summed: 970 + 997 + 964 + 1184 = 4115 passed; 37 + 59 + 22 + 0 = 118 skipped;
0 failed. 4115 + 118 = 4233**, equal to the full `--collect-only` total.

**The superseded pin was `4105 passed / 118 skipped`** — the `D-GATE-21` /
`D-GATE-21.1` / `D-GATE-22` / `D-GATE-22.1` baseline. It is **NOT** the gate
here and was not compared against: `D-IMPL-196` replaced it with an accounted
delta precisely because criteria 17, 18 and blocker B2 required guards. **The
`skipped` limb, however, is unmoved at exactly 118**, which is the one limb
`D-IMPL-196` did not have to relax and the one plan `23-07`'s `S-9` finding says
the pass total cannot see.

### Sabotages of the chunk plan itself

| # | Mutation | Prediction | Observed | Verdict |
|---|---|---|---|---|
| **S-K1** | drop `tests/mcp` (28) from chunk 4 | sum short by 28; set-equality names 28 missing ids; disjointness clean | sum `4205`, **SHORT by 28**; `FULL\UNION = 28` beginning `tests/mcp/test_egress_parameters.py::…`; `UNION\FULL = 0`; all pairwise intersections 0 | **CORRECT** |
| **S-K2a** | `tests/perf_gate` (28) in BOTH chunk 3 and chunk 4 | sum exceeds by 28; `c3^c4 = 28`; set-equality clean | sum `4261`, **EXCEEDS by 28**; `c3^c4 = 28`; both set-equality directions 0 | **CORRECT** |
| **S-K2b** | the **sum-still-matches** variant: chunk 3 gains `perf_gate` (28), chunk 4 loses `mcp` (28) | sum `4233` exactly — the sum reports nothing; only disjointness catches it | sum **`4233`, IDENTICAL — THE SUM IS BLIND**; `c3^c4 = 28`; `FULL\UNION = 28` | **CORRECT with a CORRECTION** |
| **S-K3** | a chunk run in the background and killed at 25 s | no summary line in the log; the exit code alone cannot tell a kill from a pass | direct `wait` = **137**; the log ends mid-progress at `[ 27%]`; **zero** pytest summary lines; **zero** lines beginning `F` or `E` | **CORRECT** |

**S-K2b's correction, stated because a wrong prediction teaches nothing:** the
plan's table says *"only disjointness catches it"*. **That is not what happened.**
Disjointness catches the *duplication* (`c3^c4 = 28`) and set-equality
independently catches the *omission* (`FULL\UNION = 28`, naming the `tests/mcp`
ids). The true claim — the one that matters — is narrower: **the SUM alone is
blind to it.** Two of the three properties see it; the arithmetic does not.

**S-K3's second half, reproduced deliberately:**

```
( exit 137 ) | tail -1 ;  echo $?               -> 0     <-- producer failure INVISIBLE
( exit 137 ) | tail -1 ;  echo ${PIPESTATUS[0]} -> 137   <-- the truth
```

A killed background run and a passing one are indistinguishable from a piped
exit code and from an output with no failures printed. **That is the entire
reason criterion 15 says FOREGROUND.**

---

## The other five legs, each in the foreground, each exit code read with no pipe

| Leg | Exit | Measured |
|---|---:|---|
| `lint` | 0 | `tools.lints --all`, silent |
| `typecheck` | 0 | `Success: no issues found in 211 source files` |
| `test` | 0 | four foreground chunks, **4115 passed / 118 skipped / 0 failed** |
| `gate-tools` | 0 | **415** (`tools/lints/tests`) + **339** (`tools/publish_scan_tests tools/docs_tests`); Phase 22 closed at 406 + 291 |
| `examples` | 0 | **exactly one example**, `example-hw1-harness-clients`; three harness legs at ONE content address `5d7bfa49f5b3…`; `legs compared 3` |
| `docs-strict` | 0 | all four steps run and recorded separately: `--pre-build` 0, `docs/schemas` 0, `mkdocs build --strict` 0 (`Documentation built in 3.47 seconds`), `site` 0 |

`make examples` running one target and nothing else **is criterion 3's benefit
made visible** — at `PHASE_BASE` the aggregate pulled eleven.

### Sabotages of the CI reading itself

| # | Mutation | Prediction | Observed | Verdict |
|---|---|---|---|---|
| **S-CI1** | a stray line appended to `pyproject.toml` | the per-member diff for `pyproject.toml` becomes non-empty; `src`/`runtime` unaffected | `pyproject.toml` appears in its own diff (1 name); the other two members unchanged; restored and sha256-verified identical to `PHASE_BASE` | **CORRECT** |
| **S-CI2** | the per-member loop run with misspelled members | `tracked=0` fires; the empty diff is exposed as meaningless | `srcX`/`runtimeX`/`pyprojectX.toml` all `tracked=0 diff-names=0`, **identical output to the genuinely clean `pyproject.toml` (`tracked=1 diff-names=0`)**. Only `tracked > 0` separates them | **CORRECT** |
| **S-CI3** | `make docs-strict` read through `\| tail -5`, over a genuinely broken include | the pipe's exit code is reported, not the build's | `pymdownx.snippets.SnippetMissingError` printed, `make: *** Error 1` printed, and **`EXIT read as $? after the pipe = 0`** against **`EXIT with NO pipe = 2`** | **CORRECT — the measured hazard, reproduced** |

`git status --porcelain` clean after every restore, apart from three
long-standing untracked `references/*.md` files that predate the phase.

---

## THE EIGHTEEN CRITERIA

Every row names a command. *"Verified"* appears nowhere.

| # | What it requires | Evidence (measured at this close) | Re-runnable command | Discharged by |
|---|---|---|---|---|
| **1** | ten trees moved INTACT, 265 files, pure rename set, nothing deleted, no content changed in the move | **R = 265, D = 0, `git ls-files archive/` = 265** at phase end. The content clause evidenced **at `23-04`'s move commit `ef336f3`**, not at phase end: `R=265, D=0, M=0`, and **zero renames below 100 % similarity**. 221 files under `archive/` changed AFTER that commit — Wave 5's deliberate header repairs | `git diff -M --diff-filter=R --name-only b87fe58..HEAD \| wc -l`; `git diff -M --diff-filter=R --summary ef336f3^..ef336f3 \| grep -vc '(100%)'` | `23-04` |
| **2** | `examples/` retains exactly four trees, no `00`–`08`, no `external/00-hello-context`, by `git ls-files` | Four trees + `external/` (README only) + `.gitkeep`. **Zero** tracked paths match `^examples/(0[0-8]-\|external/00-hello-context)` | `git ls-files examples/ \| grep -cE '^examples/(0[0-8]-\|external/00-hello-context)'` | `23-04` |
| **3** | the aggregate names exactly one target; **fourteen** deleted not renamed; no archive-form replacement; `live-legs.yml` names no deleted target | `Makefile:225` → `examples: example-hw1-harness-clients`. `example-*` targets **25 → 11**; the DELETED set is **exactly 14** and the ADDED set is **0**, by `comm` on the two sorted target lists. No target name contains `archive`; no recipe line runs an `archive/examples` path. `live-legs.yml` matches `example-(0[0-8]\|ext-00)` **zero** times | `comm -23 <(git show b87fe58:Makefile \| grep -oE '^example-[a-z0-9-]+:' \| tr -d : \| sort) <(grep -oE '^example-[a-z0-9-]+:' Makefile \| tr -d : \| sort)` | `23-09` (`D-IMPL-195` r1) |
| **4** | 102 includes + 9 prose paths across 15 pages re-pointed; `docs-strict` exit 0 on four steps | **102 includes across exactly 15 pages**, unchanged at every commit from `276f900` to `HEAD`. **ZERO** pre-move-form references remain in `public/`. Prose went **9 → 20**, the whole +11 landing at **`1adc35a`** (Wave 9's thirteen published `make` strings replaced by direct `python` invocations) — an addition, not an un-re-pointed remainder. Four docs-strict steps recorded separately, all 0 | `git grep -nE "$PATA" -- public/ \| grep -c -- '--8<--'`; `git grep -nP "(?<!archive/)examples/(…)" -- public/ \| wc -l` | `23-08`, `23-09` |
| **5** | **CONTROL RED BEFORE GREEN**: one un-repointed include fails the strict build naming the path AND fails `test_no_stale_example_paths.py` independently | Re-run this close as **IS-5**. See the control table below: both witnesses red, from different machinery. **A third gate stayed GREEN** — the pre-build publish scan exits 0, because it checks the publication BOUNDARY and not resolution | `sed -i '16s#archive/examples/05#examples/05#' public/reference/artifacts/task-definitions.md` then the two witnesses | `23-08`, re-proven here |
| **6** | the `D-08` count re-measured at both ends and its movement RECORDED with the new value | **111 at `b87fe58`, 122 at `HEAD`**, with D-08's own grep. Per-page movement: +1 on each of five how-to pages, +6 on `adopters-guide.md`. Recorded in both ledger channels as *moved by design*. **JUDGEMENT, NOT A GATE** — see below | `for r in b87fe58 HEAD; do git grep -cE 'examples/0[0-8]\|examples/external/00-hello-context' $r -- public/ \| awk -F: '{s+=$NF} END {print s}'; done` | `23-11` |
| **7** | paired tests stay under `tests/`; ACCOUNTED DELTA on both limbs — zero lost, every addition named, total re-measured | **Suite: 4223 → 4233. LOST-UNRECOVERED = ZERO.** 63 raw-lost ids, all 63 recovered at their `archive/` re-path; **10 genuine additions, every one named** — 4 (`test_artifact_schema_headers.py`) + 2 (`test_examples_scope.py`) + 1 (`test_gate_two_call_shape.py`) + 1 (`test_required_operators_guard.py`) = Wave 3's eight; plus 2 (`test_hw1_harness_clients_readme.py`) from `D-IMPL-197`. **`tests/examples`: 515 → 521, lost-set EMPTY, 6 named additions** (the same 4 + 2). Total re-measured in proven chunks. **Gated on none of 4105 / 4113 / 515 / 521** | `git archive b87fe58 \| tar -x -C $W/base && env -C $W/base … pytest --collect-only -q`, then the root-normalised set difference with the `(?<!archive/)(?<!tests/)` re-path rule | `23-07`, re-measured here |
| **8** | the two EXECUTING tests still execute against the archive; **a control proves each RUNS rather than skipping** | `46 passed, 1 warning`, **`-rs` skip lines = 0**. `EXAMPLE_DIR` resolves to `archive/…` in both. `test_ext00_hardening.py` spawns `[sys.executable, "run.py"]` with `cwd=EXAMPLE_DIR`; `test_cross_process_output.py`'s spawn is inside the archived source (`archive/examples/04-cross-process/run.py:336 subprocess.Popen`) | `pytest tests/examples/test_cross_process_output.py tests/examples/test_ext00_hardening.py -q -rs` | `23-07` (`S-9`) |
| **9** | the `Retirement` table re-points the ten to Phase 23 plans; the `s1` pair's `17-08` rows untouched | 29 rows. Owners: **`23-04` × 10** (the moved trees, each with a `former_path`), **`23-10` × 14** (the orphans `D-IMPL-195` r2 re-owned), **`17-08` × 5** (untouched). **Rows still owned by a retired `16-*` plan: `[]`** | `python -c "from tools.retirement_sweep import RETIREMENT_SCHEDULE as S; from collections import Counter; print(Counter(r.owner for r in S))"` | `23-10` |
| **10** | archived paths STILL COUNT as couplings, proven by a control | **131 of 270 rows name an archived path; all 10 archived trees covered** (18/3/12/21/29/19/2/9/4/14). Re-sabotaged this close as **IS-4** | `python -c "from tools.retirement_sweep import sweep; …"`; `pytest tools/docs_tests/test_retirement_sweep.py::test_the_sweep_reaches_the_archive` | `23-10` |
| **11** | the report regenerated **LAST**, **in the venv**, committed; the currency test green at the final commit | Green before this summary (`1 passed`); regenerated **after** this summary's commit and verified twice — see the appendix appended below | `.venv/bin/python -m tools.retirement_sweep --report && git diff --stat docs/surface/examples/RETIREMENT-COUPLINGS.md` | `23-12` (this plan) |
| **12** | `DOCS-17` **`Partial`** in BOTH channels, saying *out of the `examples:` aggregate*, NOT *out of live CI*, naming 19 of 31 / 2 execute | Both channels carry `Partial` and both carry the forbidden clause explicitly disclaimed. **Re-measured: 31 tracked files; 19 read an archived tree — the SAME 19 file set at `b87fe58` and at `HEAD`** (18 by the prefixed form + `test_gate_two_divergence.py` by its pathlib form, at both ends); **14 exec_module ARCHIVED source; 2 spawn a process**. **JUDGEMENT, NOT A GATE** — the wording is unenforced (deferred item 10, `S-L2`) | `git grep -lE "archive/examples/(…)\|\"archive\" / \"examples\"" -- tests/examples/ \| wc -l` | `23-11` |
| **13** | `CLNT-17`'s row **BYTE-IDENTICAL** to `efa0044`, by content hash; stays `Not built`; no `s1` tree moved | `5bcc68caa9f6839d…` at `efa0044` and at `HEAD` — **identical**. VAC-01 floor: **2 lines matched**, so the hash is over a non-empty subject. Checkbox unticked. `git diff b87fe58..HEAD -- examples/s1-*` names **0** files over **37** tracked | `diff <(git show efa0044:.planning/REQUIREMENTS.md \| grep -E '^- \[[ x]\] \*\*CLNT-17\*\*\|^\| CLNT-17 \|' \| sha256sum) <(grep -E … \| sha256sum)` | `23-11` |
| **14** | `src`/`runtime`/`pyproject.toml` diff-empty EXCEPT the four `D-IMPL-192` citations; a fifth is a scope breach; VAC-01 per member | `src` **tracked=142** → names exactly `src/ccf/products/bind.py`. `runtime` **tracked=71** → exactly `mcp/egress.py` and `mcp/experience.py`. `pyproject.toml` **tracked=1** → **EMPTY**. Changed lines under `src/`+`runtime/` = **8**, i.e. four edits × both sides, **every one a pure `examples/` → `archive/examples/` prefix**. Five `s1-01` citations byte-identical (1+1+1+2); `request.py` byte-identical in full, sha256 `b1a2b8e33c24ba24…` both ends | the per-member loop with `git ls-files -- $m \| wc -l` beside each diff; `git diff -U0 b87fe58..HEAD -- src/ runtime/ \| grep -c '^[+-][^+-]'` | `23-06`, re-taken here |
| **15** | `make ci` exit 0 on six legs; test leg FOREGROUND chunks with coverage PROVEN | six legs at 0; three properties printed above; four foreground chunks. **The `make ci`-as-one-command deviation is named above** | the ten commands from `make -n ci`, each run separately | `23-12` (this plan) |
| **16** | non-vacuity floors: the include-repoint check saw a NON-EMPTY set of includes; the moved-file check saw a NON-EMPTY set of files | the full register below, every floor with the number it SAW. Re-sabotaged as **IS-6a/IS-6b**; **IS-6b is the proof criterion 16 is not decorative** — with the page walk emptied, the two shipped assertions pass **VACUOUSLY** and only the floors go red | `pytest tools/docs_tests/test_no_stale_example_paths.py -q` with `_prose.PUBLIC_DIR` re-pointed | `23-02`, `23-03`, `23-04`, `23-05`, `23-08`, `23-09`, `23-10` |
| **17** | `INCLUDE_ALLOWED_PREFIXES` admits the archive root AND a test GUARDS the tuple, watched RED by removing a prefix | `("examples/", "public/", "perf/baselines/", "archive/examples/")` with **four** assertions naming it (membership equality, no-empty-member + trailing-slash, `archive/` NOT admitted, existing roots still admitted). Re-sabotaged as **IS-2/IS-2b/IS-3** | `pytest tools/publish_scan_tests/test_publish_scan.py -q` with a prefix removed / broadened | `23-02` (`D-IMPL-194`) |
| **18** | `PATH_TOKEN` no longer strips a leading `archive/`; controls in BOTH directions | shipped tokenizer returns the WHOLE token for all three prefixes. Direction 1 (correct page → **0** offenders) and direction 2 (stale path → **≥1**, prefix intact) both present and both red under **IS-1b**. **A CORRECTION to the module's own narration is recorded below** | `pytest tools/docs_tests/test_no_stale_example_paths.py -q` with the `archive/examples` branch dropped | `23-02` (`D-IMPL-194`) |

### Criteria whose enforcement is JUDGEMENT, not a gate — said plainly

A row implying a gate held something no gate holds is the failure this project
keeps finding in its own verification code. These are the ones:

| Criterion | What is unenforced | Proof it is unenforced |
|---|---|---|
| **6** — the `D-08` movement | both channels; nothing reads the figure | deferred item 10, `S-D8a` (one channel only → **114 passed**) and `S-D8b` (pin overwritten, movement sentence deleted → **114 passed**) |
| **12** — the cell WORDING | nothing forbids *out of live CI* | deferred item 10, `S-L2` — the cell rewritten to the forbidden claim in BOTH channels leaves `test_requirement_ledger.py` at **114 passed** and `tools.lints --all` at 0 |
| **12** — cross-channel verdict equality | `cell_verdicts` enforces *at most one verdict per cell*, never *the same verdict across a row's two cells* | deferred item 10, `S-L4` — the two channels openly disagreeing → **114 passed** |
| `README.md`'s prose, the `CLNT-30` prose obligation | no assertion reads either | `23-09`'s record |
| `cite03-node-id`'s **UNCHECKED** disposition | a node id whose PATH does not resolve is scored UNCHECKED, not failed | `D-GATE-22`'s `D-06` note; and deferred item 4, the mirror case — a citation left at the OLD path resolves by SUFFIX and is scored **checked and passing** |
| **13**'s prose | only the content hash catches a prose typo | deferred item 10, `S-L3b` — `the` → `teh` → **114 passed** |

---

## THE NON-VACUITY REGISTER — every floor with the number it SAW

| Floor | Plan | Number it saw |
|---|---|---:|
| published pages walked | `23-08` | **44** |
| distinct prose path tokens found | `23-08` | **67** |
| snippet include targets found (all forms) | `23-08` | **120** |
| `git ls-files archive/` | `23-04` | **265** |
| per-tree counts (18+24+23+27+33+21+32+19+29+39) | `23-04` | **= 265** |
| schedule paths resolving on disk | `23-10` | **29 of 29** |
| archive-swept coupling rows | `23-10` | **131 of 270** |
| distinct archived trees covered (floor is TIED to the schedule, not to 1) | `23-10` | **10 of 10** |
| `composed_examples` non-empty | `23-09` | **1** (`example-hw1-harness-clients`) |
| `phony_targets` non-empty | `23-09` | **38** |
| documents the `$schema` header gate SEES | `23-05` | **234** (214 under `archive/`) |
| archived `.yaml` whose FIRST line is a `$schema` header | `23-05` | **216** — the gate sees 213 of them; **3 remain in the blind spot** (deferred items 1 and 4) |
| `MINIMUM_GATE_CALL_SITES` | `23-03` | floor **12** |
| `MINIMUM_PROJECTING_BODIES` | `23-03` | floor **14** |
| `MINIMUM_RESOLVED_BINDER_SITES` | `23-03` | floor **12** |
| `MINIMUM_IMPLEMENTATIONS` | `23-03` | floor **9** |
| `MINIMUM_SCANNED_CITATION_HOSTS` | `23-07` | observed **1111**, floor 953 |
| `MINIMUM_CITATIONS_READ` | `23-07` | observed **1772**, floor 797 |
| `MAXIMUM_UNANCHORED_PY_CITATIONS` | `23-07` | observed **0**, ceiling 0 — **after this plan's fix; it was 1 and RED** |
| `VAC-01` per-member tracked counts (criterion 14) | `23-06`/`23-12` | `src` **142**, `runtime` **71**, `pyproject.toml` **1** |
| `VAC-01` on the `CLNT-17` hash subject | `23-11` | **2 lines** |
| `VAC-01` on the `s1-01` citation comparison | `23-06` | **5 citation lines across 4 files** |

`SCANNED_TREES = ('src', 'runtime', 'examples', 'archive')`;
`BINDER_SCANNED_TREES = ('examples', 'archive')` — both widened together, which
deferred item 3 records as a coupling a future reader must not split.

---

## THE INDEPENDENT SECOND SABOTAGE OF THIS PHASE'S OWN VERIFICATION CODE

Seven mutations against the shipped modules, run independently of the plans that
wrote them. **Two predictions were WRONG and both are recorded as corrections,
because a sabotage whose prediction is wrong teaches nothing and the prediction
is part of the sabotage.**

| # | Target (written by) | Mutation | Prediction | Observed | Verdict |
|---|---|---|---|---|---|
| **IS-1** | `PATH_TOKEN` (`23-02`) | add `/` to the negative lookbehind — *the exact mutation the module's own comment calls the blinding one* | the alternation control RED; direction 2 RED | **ALL 17 PASSED.** The mutation is INERT | **PREDICTION WRONG** |
| **IS-1b** | same | drop the `archive/examples` BRANCH from the alternation | the real decapitation | **6 failed**, incl. both direction controls, the alternation control AND the shipped-tree assertion | **CORRECT** |
| **IS-2** | `INCLUDE_ALLOWED_PREFIXES` (`23-02`) | *(mis-aimed — deleted line 121, which is `perf/baselines/`)* | — | 4 failed + pre-build scan exit 1 | **MIS-AIMED, recorded** |
| **IS-2b** | same | remove `archive/examples/` | membership guard RED; pre-build scan RED naming many includes | 4 failed incl. `test_the_archive_examples_root_is_admitted`; pre-build scan exit 1 with **exactly 102 `pub04-include-escape` findings** | **CORRECT** |
| **IS-3** | same | broaden to `archive/` — the convenience substitution | membership + narrow-spelling RED; **the build stays GREEN** | `2 failed` (membership, `test_the_widening_is_the_narrow_one…`); **pre-build scan EXIT 0** | **CORRECT — and this is criterion 17's whole argument** |
| **IS-4** | `retiring_paths()` (`23-10`) | filter every `archive/` spelling out of the sweep | `test_the_sweep_reaches_the_archive` RED; the control unaffected | **6 failed** incl. `test_the_sweep_reaches_the_archive` **and** the control's `one stray archive row` case | **CORRECT with a CORRECTION** |
| **IS-5** | criterion 5's two witnesses (`23-08`) | one include left at the pre-move path | strict build RED naming the path; the standing test RED independently | build **exit 1**, `Snippet at path 'examples/05-workflow-hitl/…' could not be found`; test **2 failed** with no build involved; **pre-build scan exit 0** | **CORRECT, plus a third-gate observation** |
| **IS-6a** | the four product floors (`23-03`) | `SCANNED_TREES = ()` | the floors fire naming the shortfall | **5 failed** incl. `test_the_gate_scan_is_not_vacuous`, `test_the_binder_scan_is_not_vacuous`; and collection fell **486 → 83** | **CORRECT** |
| **IS-6b** | the page-walk floors (`23-02`) | `_prose.PUBLIC_DIR` → a directory that does not exist | the two floors RED; the two shipped assertions VACUOUSLY GREEN | **13 failed, 4 passed** — and the 4 that passed are `test_every_prose_path_reference_resolves_on_disk`, `test_every_snippet_include_resolves_on_disk` and two synthetic-input controls | **CORRECT — the vacuity is exhibited** |
| **IS-7** | `ARTIFACT_GLOBS` (`23-03`) | drop the archive root | the two Wave-3 root guards RED | **4 failed** — `test_the_discovery_globs_reach_the_live_tree_and_the_archive`, `test_the_discovery_finds_an_archived_artifact_directory`, `test_this_module_gates_the_same_set_the_tool_checks`, `test_the_only_deferred_documents_are_the_ruled_permanent_ones`. **`test_the_gated_roots_are_the_live_tree_and_the_archive` stayed GREEN** | **PREDICTION HALF WRONG** |

### FINDING — criterion 18's controls are aimed at a mutation the shipped module makes INERT

`tools/docs_tests/test_no_stale_example_paths.py` carries this comment above its
two direction controls:

> *the obvious one-character alternative (adding `/` to the lookbehind class)
> fixes the false offenders by making `archive/examples/X` match NOTHING —
> trading a noisy check for a blind one. Control 1 alone would pass under that
> mutation; control 2 is what refuses it.*

**Measured, three regexes side by side:**

```
shipped   : ['archive/examples/04-cross-process/producer_child.py']
with '/'  : ['archive/examples/04-cross-process/producer_child.py']   <- IDENTICAL
no branch : ['examples/04-cross-process/producer_child.py']           <- the decapitation
```

Once the `archive/examples` **branch** exists, the branch matches from
`archive`, which is space-preceded, so the lookbehind's character class never
gets a say. The comment describes the repair that was **not** taken and reads —
to anyone checking the controls against the shipped module — as describing a
live mutation. It is not live. **The controls are not mis-aimed: IS-1b proves
they do catch the mutation that actually blinds the check.** But the sentence
naming the lookbehind as the load-bearing part is now false about the shipped
tokenizer, and a future editor removing the branch "because the lookbehind
handles it" would find out the hard way. **Not fixed here** — it is a comment in
a module outside this plan's `files_modified`, and item 11 below carries it.

### IS-4's correction

The control `test_control_the_archive_sweep_check_refuses_a_blind_sweep` did
**not** stay green as predicted: its `ONE stray archive row` case builds its
fixture from `head().rows` and asserts `stray` is non-empty first. With the
sweep blinded there is no archive row to build from, so **the control's own
non-vacuity precondition fired**. That is the control working, not failing — but
the prediction was wrong and is corrected rather than smoothed.

### IS-7's correction

`test_the_gated_roots_are_the_live_tree_and_the_archive` guards the **test
module's** root set; `test_the_discovery_globs_reach_the_live_tree_and_the_archive`
guards the **tool's** globs; `test_this_module_gates_the_same_set_the_tool_checks`
ties the two. Under IS-7 only the tool moved, so only the tool-side guard and
the bijection went red. The division of labour is stated in the docstrings and
is correct; **my prediction conflated the two.**

---

## THE CHECKED-AND-LEFT REGISTER

`23-RESEARCH.md` §10's obligation: *"SAY SO EXPLICITLY … so a later reader can
tell 'researched and decided to leave' from 'never checked'."*

| Left alone | Basis | Coupling rows it carries |
|---|---|---:|
| `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/SURFACE-AUDIT.md`, `docs/SURFACE-CHANGES.md`, `docs/surface-changes/*`, `docs/PHASE_*_GATE.md`, `CLAUDE.md` | append-only; on the sweep's own `EXCLUDED_FROM_ASSIGNMENT` list, each with a stated reason | **0** each |
| `docs/surface/examples/before/`, `after/`, `ERGO-03-FROZEN.md` | frozen `ERGO-03` baseline (`D-15`); also on `EXCLUDED_FROM_ASSIGNMENT` | **0** each |
| `.planning/phases/**` | the planning tree; excluded by prefix | **0** |
| `docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md`, `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md` | *"This document is evidence, not a proposal."* | **1** each |
| `docs/retired/16-external-consumers/*` | *"historical record. Nothing here runs."* | **3** |
| `docs/superpowers/plans/*`, `docs/surface/examples/SECTION-2-TRANSPORT.md` | dated plans and a dated spike record | **1** each |
| `tools/measure_examples.py` and the `before/`/`after/` fragment trees | documentary; `make measure-examples` is in **no** workflow and appears **0** times in `make -n ci` | **1**, and it is on `KNOWN_COUPLED_FILES` |
| `tools/publish_scan_tests/test_publish_scan.py`, `tests/lints/test_examples_scope.py` | `tmp_path` synthetic tokens that outlive their subject by construction | **1** each, both on `KNOWN_COUPLED_FILES` |

### CORRECTION to the register's framing: *"confirm none of them is gated"* is too strong

The true statement, measured: **no standing check RESOLVES a path in any of
them** — `gate-tools` is green at 415 + 339 and none of these files appears in
any offender list. But **six of them DO carry live coupling rows** and **three
are members of `KNOWN_COUPLED_FILES`**, the hand-built floor. Being swept is not
the same as being unwatched, and the register would have been wrong to say
otherwise.

### §14.8's open question, SEARCHED rather than assumed

*Is there a second reader of `tools/measure_examples.py` or the `before/`/`after/`
fragment trees?* The claim rested on one absence, so it was searched for:

1. **The gate the Makefile comment names does not exist.**
   `tests/examples/test_surface_audit.py` is referenced by the `Makefile`'s
   `measure-examples` comment and by comments in
   `tests/products/test_required_operators_guard.py` and
   `tests/products/test_gate_two_call_shape.py` — and
   **`[ -e tests/examples/test_surface_audit.py ]` is FALSE**. Three live source
   files cite a module that is gone.
2. **`git grep -ln measure_examples` returns 54 files.** All but four are
   `.planning/`, `docs/` records or the Makefile. The four in code are
   `tools/measure_examples.py` itself, `tools/retirement_sweep.py` (as a
   `KNOWN_COUPLED_FILES` member) and `tools/docs_tests/test_retirement_sweep.py`
   (the floor). **So it IS reached by a standing check — as a file the sweep must
   FIND, never as paths that must resolve.** Deferred item 8's gap stands.
3. **The one code-tree hit on the fragment trees is
   `tests/examples/test_hw1_harness_clients_retirement.py:104` — a prose mention
   inside a comment, not a read.** No live assertion resolves a path under
   `docs/surface/examples/before/` or `after/`.

**Result: no second reader found for the fragment trees; one floor-level reader
found for `tools/measure_examples.py`.** Recorded so the absence is a
measurement rather than an unexamined assumption.

---

## CRITERION 7 IN FULL — the accounted delta

```
PHASE_BASE ids (root-normalised): 4223
HEAD ids                        : 4233
raw lost   = 63
raw gained = 73
lost RECOVERED at an archive/ re-path = 63
LOST-UNRECOVERED                      = 0   <-- criterion 7 gates on ZERO
GAINED that are NOT a re-path of a lost id = 10
```

The ten, each reconciled to the wave that named it:

| Node id | Named by |
|---|---|
| `test_artifact_schema_headers.py::test_the_gated_roots_are_the_live_tree_and_the_archive` | Wave 3 (`D-IMPL-196`) |
| `…::test_the_discovery_globs_reach_the_live_tree_and_the_archive` | Wave 3 |
| `…::test_the_discovery_finds_an_archived_artifact_directory` | Wave 3 |
| `…::test_the_discovery_ignores_an_artifact_directory_outside_both_roots` | Wave 3 |
| `test_examples_scope.py::test_cinv01_scope_includes_the_archive_tree` | Wave 3 |
| `…::test_cinv02_does_not_flag_harness_imports_under_the_archive` | Wave 3 |
| `test_gate_two_call_shape.py::test_the_scan_root_membership_is_exactly_the_expected_sets` | Wave 3 |
| `test_required_operators_guard.py::test_the_scan_root_membership_is_exactly_the_expected_set` | Wave 3 |
| `test_hw1_harness_clients_readme.py::test_the_pinned_diff_ceiling_resolves` | `D-IMPL-197` |
| `…::test_control_7c_an_empty_ceiling_refuses_instead_of_meaning_head` | `D-IMPL-197` |

**No addition is unnamed. `4223 + 10 = 4233`; `515 + 6 = 521`.**

Two measurement notes carried from `23-07` and re-applied here, because both
were needed again: node ids embed **absolute paths** (six
`tests/crossproc/test_mcp_acquisition.py` ids read as 6 lost / 6 gained until
the root is substituted), and the re-path rule needs **two** lookbehinds —
`(?<!archive/)` and `(?<!tests/)` — or it rewrites the `tests/examples/` module
path inside every node id.

**Criterion 7's ORIGINAL pin was `4105 passed / 118 skipped`.** It is quoted
here once, as the superseded form `D-IMPL-196` replaced, and it was compared
against nothing.

---

## THE LOCKED CRITERIA — sixteen byte-identical, two AMENDED BY RULING

The plan's own verification line says *"the eighteen criteria byte-identical to
`PHASE_BASE`"*. **FALSIFIED, and correctly so.** Per-criterion sha256 against
`b87fe58`:

- **criteria 1–6, 8–11, 13–18: IDENTICAL.**
- **criterion 7: AMENDED** at `a6d7367` (`D-IMPL-196`) and again at `06786db`
  (`D-IMPL-198` ruling 1).
- **criterion 12: AMENDED** at `06786db` (`D-IMPL-198` ruling 2).

Both amendments are **decision commits**, not execution commits, and both follow
`D-IMPL-195`'s stated rule: *a ruling that changes what must be true must also
change the criterion that gates it; otherwise the criterion passes while the
work is unverified.* `.planning/ROADMAP.md`'s whole delta across the phase is
**5 insertions / 4 deletions** — the two criteria, the dated `515` clause, and
`23-11`'s authorised progress row.

---

## CARRIED, NOT CLOSED — the deferred register at phase end

Nothing below was widened into by this plan.

| # | What | Owed |
|---|---|---|
| **1 / 4** | the `$schema` header gate cannot see `artifacts/<subdir>/` — **3 headered documents in the blind spot**, measured again here (216 headered, 213 seen) | a design call on the bijection's right side, not a glob widening |
| **2** | a lowered `MINIMUM_*` floor is caught only by *"the report is stale"*, and the reflex it invites commits `floor 0` | a gate that knows the previous value |
| **3** | `SCANNED_TREES` and `BINDER_SCANNED_TREES` are coupled; widening one alone silently costs a projecting body | nothing today; recorded for a future reader |
| **5 (blocking)** | **RULED and CLOSED by `D-IMPL-197`** — the Phase 20 fence bounded to `20-CLOSE-COMMIT.txt` | none |
| **6** | **RULED and CLOSED by `D-IMPL-195` r3 / `D-IMPL-198` r2** — `19 of 31`, confirmed at both ends here | none |
| **7** | **STILL OPEN, carried by five waves now.** Both stale-path witnesses read page SOURCES; neither reads the RENDERED body a `--8<--` pulls in | `archive/examples/08-e2e-demo/run.py:4`; `archive/examples/05-workflow-hitl/artifacts/task-definition.yaml:6`; and the live output string at `run.py:1095` a fixer must DECIDE about rather than edit blind. The durable fix is a **third witness** that reads rendered include bodies |
| **8** | **STILL OPEN.** Two live `argparse` help strings in `tools/measure_examples.py` advertise directories that are gone (lines 308, 320; line 261 is a docstring). `KNOWN_COUPLED_FILES` cannot tell *the sweep narrowed* from *the coupling was discharged* | whichever plan re-points the help text, which must also rule on what the floor should say afterwards |
| **9** | **STILL OPEN.** `.planning/ROADMAP.md`'s Phase 23 goal prose still says *limb done — out of live CI*, the clause `D-IMPL-191` r4 amended and the shipped cell is FORBIDDEN to claim; `STATE.md`'s Position block still says *SIXTEEN criteria* and *25 of 31* | the three named edits, to **`23-13`**. **Nothing gates any of them** — which is how they went two rulings stale without a red |
| **10** | **STILL OPEN.** Nothing gates a ledger cell's WORDING and the two channels can carry different verdicts for one row (`S-L2`, `S-L3b`, `S-L4`, `S-D8a`, `S-D8b`, all at **114 passed**) | a cross-channel verdict-equality assertion would close `S-L4` and `S-D8a` cheaply; the wording limbs need `R-alpha`'s vocabulary ruling |
| **11** | **NEW, found by this plan.** `test_no_stale_example_paths.py`'s control comment names the lookbehind as the blinding mutation; the shipped alternation makes that mutation inert. The controls catch the real thing (IS-1b); the narration does not describe the shipped module | a one-paragraph comment correction, in a module this plan does not own |
| **12** | **NEW, found by this plan.** `tests/examples/test_surface_audit.py` does **not exist**, and three live source files cite it — the `Makefile`'s `measure-examples` comment and comments in `tests/products/test_required_operators_guard.py` and `tests/products/test_gate_two_call_shape.py` | whoever next touches those comments; and it is a data point for the `cite03-node-id` UNCHECKED hole, since a prose citation of a missing module is exactly what that disposition lets through |

---

## Deviations from Plan

### 1. `[Rule 3 — blocking]` `make ci` was RED on arrival and the plan could not complete around it

Fixed at `8e431eb`, converted rather than ceiling-raised. Full account at the
top of this document. **This is a finding about Waves 10 and 11, not only about
one line of prose:** two consecutive waves reported green pipelines having run
neither `tests/invariants` nor `make ci`.

### 2. `make ci` was not run as a single command

Recorded above under criterion 15, with the arithmetic and the reason. The ten
commands were run separately in the foreground and `make -n ci` is printed as
the proof that the ten are the whole of it.

### 3. Predictions corrected rather than smoothed

Four: **S-K2b** (set-equality catches it too, not disjointness alone), **IS-1**
(the lookbehind mutation is inert), **IS-4** (the control's own non-vacuity
precondition fired), **IS-7** (test-side and tool-side guards are deliberately
distinct). One sabotage, **IS-2**, was itself mis-aimed — it deleted
`perf/baselines/` instead of `archive/examples/` — and is recorded as mis-aimed
rather than quietly re-run.

### 4. Criterion 4's prose limb is 20, not 9

Not a shortfall: the includes are **102** and the pages **15** at every commit
from `276f900` onward, and the pre-move form is at **0**. The +11 lands entirely
at `1adc35a`, Wave 9's replacement of thirteen deleted `make example-*` strings
with direct `python` invocations. Named so nobody reads `20 ≠ 9` as a residue.

---

## Self-Check

- `.planning/phases/23-…/23-12-SUMMARY.md` — written by this task
- `8e431eb` — `fix(23-12)`, the citation ceiling repair
- every figure in this document measured in this session; none inherited from
  the brief, from a decision entry, or from an earlier wave's SUMMARY

---

## Appendix — criterion 11, run AFTER this summary's commit rather than predicted before it

```
$ .venv/bin/python -m tools.retirement_sweep --report          # EXIT=0
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
270 coupling rows across 83 files (142 rows outside the three swept trees); 1940 files scanned

$ git diff docs/surface/examples/RETIREMENT-COUPLINGS.md
+| `.planning/phases/23-…/23-12-SUMMARY.md` | 12 | the phase's own planning tree — not shipped, not published |
```

**Exactly one row, and it is this document.** Committed at `dabd4db`.

**Verified TWICE, as the brief requires:**

```
$ .venv/bin/python -m tools.retirement_sweep --report          # EXIT=0  (second run)
$ git diff --stat docs/surface/examples/RETIREMENT-COUPLINGS.md
(no output — NO DIFF)

$ pytest tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current -q
1 passed
```

**The venv obligation, measured rather than quoted.** `/usr/bin/python3 -m
tools.retirement_sweep` does not merely under-report here — it cannot import
`joserfc` and the sweep's own import walk records
`tests/products/test_gate_two_call_shape.py [import] ModuleNotFoundError`. The
venv is not a preference.

**Handed to `23-13` explicitly:** `docs/surface/examples/RETIREMENT-COUPLINGS.md`
is GENERATED and walks `.planning/`, so plan `23-13`'s own SUMMARY, its
`23-CLOSE-REVIEWS.md`, and every `STATE.md`/`ROADMAP.md` edit will make it stale
again. Regenerate **LAST**, **in the venv**, and verify twice.

**Working tree at this plan's end:** clean apart from three untracked
`references/*.md` files that predate the phase.

## Self-Check: PASSED

- `FOUND` `.planning/phases/23-…/23-12-SUMMARY.md`
- `FOUND` `8e431eb` — `fix(23-12)` the citation ceiling repair
- `FOUND` `a6175b3` — `docs(23-12)` this summary
- `FOUND` `dabd4db` — `chore(23-12)` the report regeneration
- `test_the_committed_report_is_current` green at the final commit

---

## Postscript — this wave reproduced its own headline defect, and the gate it had just repaired caught it

Every wave in this project's recent history has found the phase's own defect
class inside its own work. This one did too, and the instance is unusually
literal.

Writing the `## Current Position` narrative for `STATE.md` and the finding above
into this SUMMARY, I spelled the three stale citations of the missing
`tests/examples/test_surface_audit.py` **in the `path.py:LINE` form** — the exact
form `D-IMPL-114` forbids and whose ceiling of ZERO this plan had repaired
ninety minutes earlier. Run over the hand-edited `STATE.md`:

```
tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
  1 unanchored citations of Python targets are in D-IMPL-123's scope, ceiling 0
  - .planning/STATE.md:1510 cites test_gate_two_call_shape.py:1874
```

Converted the same way Wave 10's was — the references now name the files and say
where in them, with no line anchor — and the module returns to `5 passed`.

**Two things worth carrying out of it.** First, the gate is genuinely load-
bearing: it caught a fresh instance within one wave of being repaired, against
a writer who knew about it. Second, **only ONE of the three was flagged.** The
`Makefile` reference is not a Python target and is out of scope by design, but
`tests/products/test_required_operators_guard.py:322` — written in the same
sentence, in the same form, in the same file — was **not** in the offender set.
The scoping rule that admits one and not the other was not chased down here and
is not asserted anywhere; it is recorded so a later reader does not take the
single-offender output as proof that only one was written.

---

## Closing verification — all six legs RE-RUN at the final tree

The figures in this document were taken before the hand edits to `STATE.md`,
`ROADMAP.md` and this SUMMARY. Four `tests/` directories contain modules that
read `.planning/` or the coupling report — `tests/examples` (2),
`tests/client` (1), `tests/deployment` (2), `tests/invariants` (1) — so the whole
pipeline was re-run at the final commit rather than assumed to have held.

| Leg | Exit | Final measurement |
|---|---:|---|
| `lint` | 0 | silent |
| `typecheck` | 0 | `Success: no issues found in 211 source files` |
| chunk 1 | 0 | `970 passed, 37 skipped, 9 warnings in 114.34s` |
| chunk 2 | 0 | `997 passed, 59 skipped, 4 warnings in 97.49s` |
| chunk 3 | 0 | `964 passed, 22 skipped, 104 warnings in 126.34s` |
| chunk 4 | 0 | `1184 passed, 4 warnings in 315.57s` |
| `gate-tools` | 0 | `415 passed` + `339 passed` |
| `examples` | 0 | `legs compared 3`, one target |
| `docs-strict` | 0 | four steps |

**4115 passed / 118 skipped / 0 failed; `--collect-only` 4233** — identical to
the pre-edit run in every figure. `git status --porcelain` clean apart from the
three pre-existing untracked `references/*.md`.

**The coupling report is current at the final commit** (`7c0d380`): regenerated
in the venv after every `.planning/` write, a second regeneration produces no
diff, and `test_the_committed_report_is_current` is green. **`23-13` inherits the
obligation** — its SUMMARY, its `23-CLOSE-REVIEWS.md` and every `STATE.md` /
`ROADMAP.md` edit will make it stale again.
