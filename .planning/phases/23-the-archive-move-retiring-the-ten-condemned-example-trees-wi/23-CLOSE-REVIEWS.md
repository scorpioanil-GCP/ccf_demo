# Phase 23 — Close-Time Review Record

**Subject: the SHIPPED tree, not the plans.** This file is deliberately distinct
from any pre-execution plan review, per `CLAUDE.md` §3.1, so that an earlier
plan review survives alongside it.

- **Phase base:** `b87fe58`
- **HEAD at the panel:** `c81337b` (68 commits, 363 files, +10800/−1015, **0 files deleted**)
- **Date:** 2026-08-25
- **Executing model:** Opus 5 — **excluded from the panel for independence**, and
  the source of the additive depth pass in § 3, which is recorded separately.

---

## 1. How the panel was assembled, and what was left out of it

**The panel is the set of available external AI reviewers with the executing
model excluded.** It is not a command invocation. `/gsd-review --all` is the
mechanism that ordinarily gathers them; at close it gathers the wrong subject —
`$HOME/.claude/get-shit-done/workflows/review.md` collects `*-PLAN.md`,
`*-CONTEXT.md` and `*-RESEARCH.md` and asks for a **plan** review, which is
right before execution and wrong now. These plans were reviewed before
execution and those decisions are already executed.

**So the payload was assembled BY HAND from the shipped subjects, and the three
reviewer invocations otherwise follow the workflow exactly.** A hand-assembled
close-time payload is **conforming, not a deviation** — but it is said here, and
what was left out is named below.

**The source was INLINED, not pointed at by path.** On this host `codex`'s
sandbox (`bwrap`) fails in a way that lets it exit 0 having read nothing.
Inlining makes a silent sandbox failure unable to empty the review. Payload:
**117,567 bytes**, nine enumerated subjects.

### What was IN the payload

| # | Subject | Why |
|---|---|---|
| 1 | the four permitted `src/`/`runtime/` citation edits, whole diff | criterion 14's boundary; a fifth edit is a scope breach |
| 2 | `tools/publish_scan.py::INCLUDE_ALLOWED_PREFIXES` + its five new guard assertions | criterion 17, a previously **unguarded** publication default-deny boundary |
| 3 | the whole `tools/docs_tests/` diff incl. `test_no_stale_example_paths.py::PATH_TOKEN` and its directional controls | criterion 18, controls required in both directions |
| 4 | the widened lint/scan/citation constants from plans `23-02`/`23-03` + `tools/lints/tests/test_scope.py` | seven boundaries moved |
| 5 | `tools/retirement_sweep.py`'s re-pointed schedule + plan `23-10`'s new assertions | criteria 9 and 10 |
| 6 | the `Makefile` diff and the rewritten `.github/workflows/` jobs | criterion 3 and the always-on job |
| 7 | `git diff --stat` excluding the moved trees, plus the whole-change shortstat and the deletion count | the shape of the change |
| 8 | the `DOCS-17` `Partial` cell, **both** channels, verbatim | criterion 12 and `D-06`'s wording constraint |
| 9 | the four `parents[N]` repairs and the `$schema` header census | criterion 8's runnability |

### What was LEFT OUT of the payload, and named as such

1. **`tests/examples/test_artifact_schema_headers.py`** — the module carrying
   the `ARTIFACT_GLOBS` membership guard. Its absence directly produced a false
   finding (**REJ-2** below), because two reviewers concluded the constant was
   unguarded when a set-equality assertion for it ships in that file.
2. **`tests/lints/test_examples_scope.py`** — the runner-level behavioural proof
   over synthetic trees. Its absence contributed to **REJ-3**.
3. **`tests/products/test_gate_two_call_shape.py` / `test_required_operators_guard.py`** —
   two of the seven widened boundaries were represented only by their
   `tools/`-side constants.
4. **The 265 moved files themselves.** Only a `parents[N]` extract and a header
   census were inlined. The pure-rename property was asserted to the panel
   rather than shown.
5. **`public/`** — none of the 15 re-pointed published pages was inlined.
6. **The plan and summary documents of waves 1–12.** Deliberate: the panel is
   pointed at code, and the known findings were briefed in prose instead.

### How the panel's budget was spent

The panel was **briefed with the ten findings already recorded** and told **not
to re-derive them**, and with the two backlog items (`D-IMPL-192`,
`D-IMPL-194`) as **known and deliberately out of scope**. It was asked four
questions in priority order: (1) what is *adjacent* to each known defect, one
file over; (2) is any of the seven widened boundaries wider than it needs to be,
or wide in a direction nobody asserted; (3) can any control pass over an empty
set, or pass while its subject was **swapped rather than removed**; (4) is any
prose this phase wrote now **false on the tree**.

It was also given the hard boundaries (`CLNT-17` and the `s1` pair out of scope;
exactly four `src`/`runtime` edits; ten trees not nine; nothing deleted) and
required to quote the inlined text each finding rests on.

---

## 2. Did each reviewer actually READ the subject?

**A reviewer that fails this test is recorded as FAILED, not as a reviewer that
found nothing.** The test: do the symbols and figures it cites resolve against
the tree?

| Reviewer | Invocation | Exit | Bytes | Citations resolve? | Verdict |
|---|---|---:|---:|---|---|
| **codex** | `codex exec --skip-git-repo-check -` after `printenv CODEX_API_KEY \| codex login --with-api-key` | 0 | 2,970 | `test_retirement_sweep.py::archive_sweep_problems` ✅, `::scheduled_path_problems` ✅, `retirement_sweep.py::python_hits` ✅, `check_schema_headers.py::ARTIFACT_GLOBS` ✅ — and the quoted source text is verbatim from the payload | **REVIEWED** |
| **cursor** | `cursor agent -p --mode ask` (no `--trust`; the flag does not exist in the installed version) | 0 | 7,766 | seven distinct symbols cited, **all seven resolve**; every quote traced to the payload | **REVIEWED** |
| **gemini** | `gemini -p -` | 0 | 3,398 | `check_schema_headers.py::discover` ✅, `lints/__main__.py::LINTED_TREES` ✅, `PATH_TOKEN` regex quoted **byte-exact** ✅, `docs/09-ruling-batch-minicycle.md` **exists** ✅ | **REVIEWED, with one extrapolation** — see REJ-4 |

**Notes on reliability, measured rather than assumed.**

- `codex` did **not** exhibit the exit-0-having-read-nothing failure this time.
  Its quotes are verbatim from the inlined payload, including a docstring
  sentence (*"The floor is tied to the SCHEDULE rather than set at `>= 1`…"`*)
  that appears nowhere else. **Inlining is what made this checkable.**
- `gemini` did **not** fabricate a symbol this time — its one weak finding is an
  *extrapolation* from a real quote about a real file it was not given, not an
  invention. That distinction is recorded because the failure mode differs.
- **`OPENAI_API_KEY` was not used**; `CODEX_API_KEY` was, per the standing note
  that the former key's project has no credit.

---

## 3. The additive single-agent depth pass — separate, and NOT a substitute

**Both passes ran; neither substitutes for the other.** The panel exists because
independent models catch different blind spots; the depth pass exists because it
reads at a depth a panel prompt cannot carry.

The depth pass was pointed at the two things a diff-scoped review structurally
cannot see:

1. **Prose drift away from changed lines.** 265 files moved and 111 published
   references were re-pointed; the docstrings and comments that *describe* those
   paths are exactly the population at risk, and they sit hundreds of lines from
   any edit. Method: a mechanical sweep of every file this phase changed under
   `tools/`, `tests/`, `src/`, `runtime/`, `Makefile` and `.github/` for
   absence-tense and future-tense prose about the archive — 19 candidate lines,
   each read in context.
2. **The last commit is the least-reviewed one.** Waves `23-11` and `23-12`'s own
   writes were included in the subject, which is where **DP-3** was found.

### Were the two passes disjoint? Measured, not assumed.

**No — and that is recorded rather than smoothed.** Phase 22's close proved them
disjoint by measurement; this close did not reproduce that.

- **The single blocking finding (B1) was found by BOTH**, independently and
  first by the panel — codex F-1 (BLOCKING) and cursor F-1/F-3 (ADVISORY)
  converged on `archive_sweep_problems` before the depth pass reached it.
- **Three findings were the depth pass's alone**: DP-2, DP-3, DP-4.
- **One finding was the panel's alone**: cursor F-5 (later ADV-FIX-1).
- **Four findings were the panel's alone and were REJECTED.**

The honest reading: the panel's convergence on B1 *raised confidence* in a
finding the depth pass would have reached anyway, and the depth pass found the
prose and tracking-file drift the panel could not see because those files were
not in the payload. They overlapped on the one thing both could see.

---

## 4. EVERY finding, with its verification command, observed result and verdict

**Rejected findings are KEPT here as rejected.** Deleting them would lose the
evidence that this panel produces confident, well-formatted, false findings —
which it did, four times.

### 4.1 CONFIRMED — BLOCKING (fixed in-phase)

---

#### **B1 — `archive_sweep_problems` could not turn red on criterion 10's own named mutation**

- **Raised by:** codex F-1 (BLOCKING), cursor F-1/F-3 (ADVISORY), and the depth
  pass independently.
- **Claim:** the check compares a row *count* against the number of scheduled
  archived trees, never per-tree coverage, so a row set concentrated on one tree
  clears the floor while nine trees go unseen.
- **Why it is BLOCKING and not advisory:** criterion 10 reads *"Archived paths
  **STILL COUNT** as live couplings, **proven by a control: suppressing an
  archived path's coupling row is watched RED**, so the sweep cannot go blind to
  the archive."* Against the shipped control that sentence was **false**, so the
  criterion was **not discharged**. That is *a criterion not actually
  discharged* and *a control that cannot fail on the mutation it names*.
- **Verification command:**
  ```
  PYTHONPATH=.:src:runtime .venv/bin/python - <<'PY'
  from tools.docs_tests.test_retirement_sweep import archive_sweep_problems, head, ARCHIVE_PREFIX
  from tools.retirement_sweep import RETIREMENT_SCHEDULE
  rows = head().rows
  victim = "archive/examples/03-harness-portability"
  suppressed = tuple(r for r in rows if r.retiring_path != victim)
  print(archive_sweep_problems(RETIREMENT_SCHEDULE, suppressed) or "PASSES -- BLIND")
  PY
  ```
- **Observed:**
  ```
  archive rows at HEAD: 131   scheduled archived trees: 10
  per-tree row counts: 18 / 3 / 12 / 21 / 29 / 19 / 2 / 9 / 4 / 14
  TEST A  21 rows, ALL from archive/examples/03-harness-portability   -> PASSES (empty) -- BLIND
  TEST B  every one of that tree's 21 rows suppressed, 110 rows left  -> PASSES (empty) -- BLIND
  ```
- **VERDICT: CONFIRMED. BLOCKING. FIXED IN-PHASE at `d6cbca7`.**
- **The fix:** per-tree coverage asserted rather than summed. The count floor is
  **kept**, because it names a different diagnosis — a shrunken row set versus a
  tree gone dark — and a refusal that cannot tell those apart sends its reader
  to the wrong place.
- **Re-sabotaged independently, in BOTH directions:**

  | Mutation | Prediction | Observed | Verdict |
  |---|---|---|---|
  | per-tree clause deleted, count floor kept | the two NEW control cases go red; the four pre-existing cases stay green | **2 failed, 4 passed** — exactly the two new cases, on the `have ZERO coupling rows` fragment | **CORRECT** |
  | count clause deleted, per-tree clause kept | the two pre-existing count cases go red | **2 failed, 4 passed** — `a sweep that produced no rows at all` and `ONE stray archive row…` | **CORRECT** |

  Both clauses are independently load-bearing. The file was restored from a
  backup held **outside the tree** and `diff` confirmed byte-identical after
  each sabotage (standing hazard 2).
- **Anti-vacuity in the new control itself:** the victim tree is derived from
  the schedule and never spelled, and the control asserts `victim_rows` is
  non-empty and that the surviving total stays **above** the floor — otherwise
  the count clause would fire first and the per-tree clause would go unproven.

---

#### **B2 — `DOCS-01`'s channel-1 ledger cell was made measurably false by this phase**

- **Raised by:** the depth pass (DP-3). Not seen by the panel — `.planning/` was
  not in the payload.
- **Claim:** the cell said the adopter's guide *"teaches `make example-00`,
  `-01`, `-02`, `-05`, `-06` and `-ext-00`"*. Criterion 3 **deleted** those
  targets and Wave 8 re-pointed the guide to direct `archive/examples/`
  invocations.
- **Verification command:** `grep -c "make example-" public/tutorial/adopters-guide.md`
- **Observed:** **`0`**. The guide now names `python archive/examples/00-quickstart/run.py`
  and eleven sibling `archive/examples/…` paths; `ccf.client`/`ProductClient`
  re-measured at **0**, unchanged.
- **VERDICT: CONFIRMED. BLOCKING** — a live requirement-ledger cell made false
  by this phase's own deliverable, against `D-19`'s standing rule that a claim
  which moves is re-stated rather than left stale. **FIXED IN-PHASE at `a8c3af9`.**
- **The part that matters more than the fix:** **both channels were checked and
  only channel 1 was false.** Channel 2 (the traceability row) says *"teaches
  the example trees `DOCS-17` condemns"*, which is still true. **That is the
  S-D8a/S-D8b two-channel drift class arriving for real, on a different row —
  and nothing gates it.** `test_requirement_ledger.py` is **114 passed** across
  the false state and the corrected one alike.

---

#### **B3 — deferred item 9's three edits, owed to this plan BY NAME and unmade**

- **Raised by:** the depth pass (DP-4), reading forward from `deferred-items.md`.
- **Claim:** three stale claims that item 9 assigned to `23-13`, with its own
  closing sentence as the finding: *"Nothing gates any of them — which is how
  they went two rulings stale without a red."*
- **Verification and observed:**

  | # | Claim | Command | Observed |
  |---|---|---|---|
  | 1 | `.planning/ROADMAP.md` Phase 23 **goal prose** still said *"limb done — out of live CI"* | `grep -n "out of live CI, sources preserved" .planning/ROADMAP.md` | **1 hit** — the exact clause `D-IMPL-191` ruling 4 amended and that **criterion 12 forbids the shipped cell from claiming** |
  | 2 | `.planning/STATE.md` Current Position said **SIXTEEN** Success Criteria | `grep -n "SIXTEEN Success Criteria LOCKED" .planning/STATE.md` | **1 hit** — the set has been **eighteen** since `D-IMPL-194`, i.e. since before Wave 1 |
  | 3 | Same block said **25 of 31** | `grep -n "because 25 of 31" .planning/STATE.md` | **1 hit** — `D-IMPL-195` ruling 3 amended it to **19**, re-measured 19 at `PHASE_BASE` **and** 19 at `HEAD` |

- **VERDICT: CONFIRMED. BLOCKING** (an unsurfaced-decision defect: the tracking
  files disagreed with two rulings). **FIXED IN-PHASE at `a8c3af9`**, each
  correction **marked inline** rather than made silently.
- **Guarded during the edit:** `CLNT-17`'s row content hash
  `5bcc68caa9f6839df0d870aba10a4897114607995eb21ded0b13cccedc3ba084` **before
  and after** (criterion 13); `DOCS-17`'s cells **byte-identical in both
  channels** (criterion 12); **all eighteen criterion lines byte-identical**,
  and 155 numbered lines still parse **one per line**.

---

### 4.2 CONFIRMED — ADVISORY, FIXED IN-PHASE

These are prose this phase's own move falsified, inside modules this phase owns.
No mechanism changed. Committed at `2044ec1`.

| id | Where | The false sentence | Measured | Disposition |
|---|---|---|---|---|
| **ADV-FIX-1** | `tools/docs_tests/test_no_stale_example_paths.py::test_a_correctly_re_pointed_archive_path_yields_no_offenders` | *"The repo has no `archive/` yet"* and *"today's un-moved tree"* | the archive has held ten trees since Wave 4 | recast; **the synthetic root is KEPT** with the stronger *current* reason stated — it is the only way to hold the second precondition now that `examples/` still holds four surviving trees. Raised by **cursor F-5**. |
| **ADV-FIX-2** | `tests/examples/test_artifact_schema_headers.py::test_the_discovery_globs_reach_the_live_tree_and_the_archive` | *"satisfied by both being blind to the archive at once, because the archive does not exist"* | `discover(require_all=True)` returns **10** archived artifact directories against **1** live one | recast as historical; the direct membership assertion keeps its reason, because a *future* narrowing would re-create exactly that state. Depth pass (**DP-2**). |
| **ADV-FIX-3** | `tools/publish_scan_tests/test_publish_scan.py::test_the_existing_roots_are_still_admitted` | *"nothing that was permitted moved"*, while witnessing `examples/00-quickstart/run.py:boot` — a tree that **did** move | `include_escapes` is a prefix predicate and never touches disk, so the assertion stayed green over a path that no longer exists | **a control witnessing a subject SWAPPED rather than removed** — the phase's own category-3 question, answered against itself. Re-pointed at `examples/s1-01-hello-context-product/spine.py` and `examples/hw1-harness-clients/client_adk.py`, **both confirmed present on disk before the edit**. Raised by **cursor F-4/F-6**. |

---

### 4.3 CONFIRMED — ADVISORY, CARRIED (not fixed)

---

#### **ADV-1 — a `former_path` swapped to a wrong *nonexistent* spelling is not caught by `scheduled_path_problems`** (codex F-2, claimed BLOCKING)

- **Claim verified as a property.** Clause 4 rejects a `former_path` that
  *resolves*; it does not reject one swapped to a different path that also does
  not resolve.
- **Verification:** every `former_path` replaced in memory with
  `former_path + "-typo"`, then `scheduled_path_problems` re-run and the sweep
  re-taken.
- **Observed:** `scheduled_path_problems` -> **EMPTY (passes)**. The sabotage
  costs **270 -> 225 rows** and **13 source files**.
- **BUT — REFUTED as blocking, by measurement.** `tools/measure_examples.py` is
  in `KNOWN_COUPLED_FILES` and is one of the 13 files lost, so
  `test_every_known_coupled_file_is_found` — plan `23-10`'s hand-built floor,
  written for exactly this — **does** go red. The mutation is watched, one test
  over.
- **VERDICT: CONFIRMED as a property, downgraded to ADVISORY, CARRIED.** A
  second clause inside the predicate would make the refusal name its own cause
  instead of relying on a neighbouring floor. Deferred item **13**.

---

#### **ADV-2 — same-line substring shadowing suppresses a `former_path` reference** (codex F-3)

- **Verified:** `python_hits::shadowed` suppresses a target that is a substring
  of a longer one already filed on the same line, and `examples/04-cross-process`
  *is* a substring of `archive/examples/04-cross-process`. A line naming both
  spellings files one row, not two.
- **Not a defect as shipped:** the behaviour is **deliberate and reasoned in the
  shipped comment**, which records the measurement that produced it — without
  it the repo-wide total read **315** rows instead of 264, and two
  single-reference fixtures returned 2 rows where they assert 1. The suppressed
  row is the *shorter* spelling on a line the reader is already sent to.
- **VERDICT: CONFIRMED as a property, ADVISORY, CARRIED.** Documented, not silent.

---

#### **ADV-3 — no REAL-TREE non-vacuity floor on the archive-side discovery or lint walk** (the surviving core of gemini F-1/F-2 and cursor F-2)

- Each of these was **rejected as stated** (see REJ-2, REJ-3). What survives all
  three is narrower and true: the archive-side membership is asserted by
  set-equality, and the behaviour is proven on **synthetic** trees, but nothing
  asserts a **non-empty archive-side result on the real tree**.
- **VERDICT: ADVISORY, CARRIED — and it is the same shape as the already-backlogged
  `D-IMPL-192`.** Recorded as deferred item **14** so the shape is written down
  once rather than re-found. Not fixed: it is a standing-check design question,
  not a Phase 23 obligation.

---

#### **ADV-4 — "both run in CI" in the three re-pointed seam docstrings reads against `make examples`** (cursor F-7)

- **Claim:** the docstrings say the archived call sites *"are shipped, both run
  in CI"* while the `examples` job dropped them.
- **VERIFIED AND REJECTED ON FALSITY.** The claim is **still true** on the
  shipped tree, via a different job: `tests/examples/test_cross_process_output.py`
  **spawns a process** running `archive/examples/04-cross-process/producer_child.py`,
  and `tests/examples/test_ext00_serve_output.py` `exec_module`s
  `archive/examples/external/00-hello-context/serve.py`. Both run in the `test`
  job, and **criterion 8's control proves each RUNS rather than silently
  skipping** — which is precisely why criterion 8 exists.
- **VERDICT: the falsity claim is REJECTED. The readability observation is
  ADVISORY and CARRIED**: a reader checking "runs in CI" would naturally look at
  `make examples` first and find nothing. Deferred item **15**.

---

#### **NOT-NEW — `PATH_TOKEN` does not validate a `::symbol` suffix** (gemini F-4)

- **Verified as a property:** `PATH_TOKEN.findall("… producer_child.py::no_such_symbol …")`
  returns `['archive/examples/04-cross-process/producer_child.py']` — the path
  is checked, the symbol is not.
- **VERDICT: NOT NEW.** This restates **known finding 2** (the `cite03-node-id`
  UNCHECKED disposition) and the backlogged **`D-IMPL-192`**, both of which the
  panel was explicitly told were out of scope. Recorded, not counted.

---

### 4.4 REJECTED — with the refuting evidence

**Four of eleven distinct panel findings were false.** Kept here as evidence.

---

#### **REJ-1 — "the schema-header census prose contradicts the shipped census: 216 vs 220"** (codex F-4)

- **Verification:**
  ```
  grep -rl 'yaml-language-server: \$schema=' archive/examples/ | wc -l              -> 220
  grep -rl 'yaml-language-server: \$schema=' archive/examples/ | grep -E '\.(yaml|yml)$' | wc -l -> 216
  ```
- **The four non-YAML files:** `archive/examples/{01-agent-basics,02-skilling,05-workflow-hitl,external/00-hello-context}/README.md`
  — **README prose about the convention**, not artifact documents.
- **The comment's 216 is exactly right.**
- **VERDICT: REJECTED — AND THE FAULT IS MINE, NOT THE REVIEWER'S.** My payload's
  census line measured *files containing the header string* and labelled it a
  header census. **I put a false premise into the panel payload and the reviewer
  reasoned correctly from it.** Recorded because a payload defect is
  indistinguishable from a reviewer defect unless it is checked, and this one was
  found only by re-measuring.

---

#### **REJ-2 — "`ARTIFACT_GLOBS` is an S-4-class boundary with no membership guard"** (cursor F-2; gemini F-1's premise)

- **Verification:** `grep -rn "ARTIFACT_GLOBS" --include=*.py .`
- **Observed:** `tests/examples/test_artifact_schema_headers.py::test_the_discovery_globs_reach_the_live_tree_and_the_archive`
  asserts `set(ARTIFACT_GLOBS) == {…}` — the **exact** set-equality pattern
  cursor said was absent — plus `::test_the_discovery_finds_an_archived_artifact_directory`
  and `::test_the_discovery_ignores_an_artifact_directory_outside_both_roots`,
  which prove the behaviour on a synthetic tree in **both** directions.
- **VERDICT: REJECTED.** **Caused by my payload omission #1** — the guard lives
  under `tests/examples/`, which I did not inline.

---

#### **REJ-3 — "`discover` reports clean over a missing or empty archive" / "the lint runner is blind to archive-root vacuity"** (gemini F-1, F-2, both claimed BLOCKING)

- **Verification:** `discover(require_all=True)` on the shipped tree.
- **Observed:** `artifact dirs discovered: 11   archive: 10   live: 1`. **The
  discovery reaches the archive.** For the lint half,
  `tools/lints/tests/test_scope.py::EXPECTED_LINTED_TREES` is a set-equality
  membership assertion, and `tests/lints/test_examples_scope.py` drives
  `tools/lints/__main__.py::run` over synthetic trees.
- **VERDICT: REJECTED as stated** — both cited a silence that does not exist.
  The narrower residue is carried as **ADV-3**.

---

#### **REJ-4 — "`docs/09-ruling-batch-minicycle.md` contains false capability prose for `live-legs.yml`"** (gemini F-3)

- **Verification:** `grep -n "live-legs" docs/09-ruling-batch-minicycle.md`
- **Observed:** **two** hits, both incidental — *"the D-11 live-legs pattern"*
  and *"mirroring D-11's live-legs pattern"*. The file **does not** describe
  `live-legs.yml` as the place live example-03 legs run. Gemini extrapolated
  from a real quote in the `live-legs.yml` header (which *was* in the payload and
  which lists five documents referencing it by path) to the contents of a
  document it was never given.
- **The adjacency was then checked anyway, because that is what the finding was
  worth.** All five referencing documents examined: `README.md` — re-pointed
  correctly, its live-legs sentence accurate; `Makefile` — accurate at both
  sites; the coupling report — generated; `.github/workflows/live-legs.yml` —
  its own header. **`docs/PHASE_I5_GATE.md` does name `make example-00`, `-03`
  and `-05`**, and is an append-only historical phase-gate record, disposed of
  the same way the `D-GATE` entries are: history is corrected by appending, not
  by editing.
- **VERDICT: REJECTED. The adjacency check it prompted found nothing new** —
  recorded as a checked-and-clean rather than as silence.

---

### 4.5 Category 2 — nothing found, by two reviewers independently

Both codex and cursor returned **"nothing found in category 2"** on the seven
widened boundaries. Cursor gave a reason worth keeping: the narrow-versus-inheriting
split (`archive/examples/` for publication, path tokens, artifact globs and
example prefixes; bare `archive` for the lint and citation walks) is asserted at
each constant and reasoned by boundary direction — default-deny narrow,
default-allow inheriting. The depth pass concurs and adds nothing.

---

## 5. The own-defect-class hunt — run independently of plan `23-12`'s sweep

**The standing expectation, met eight waves for eight: every wave finds the
phase's own defect class inside its own work.** This phase's class is **a tool
that reports clean because it did not look.**

**Found, and it is B1.** `archive_sweep_problems` — the control written to prove
the sweep cannot go blind to the archive — was itself blind to a tree going
dark. Nine of ten trees could contribute zero rows and it returned empty. **The
class arrived inside the control commissioned to prevent it**, which is exactly
the shape `21.1-09` and Phase 22.1 recorded.

**What else was hunted, so a nothing is a measured nothing:**

| Subject | Method | Result |
|---|---|---|
| all **37** test functions and predicates this phase added | enumerated from the diff, each read for whether an empty subject satisfies it | 30 are set-equality membership assertions, which **cannot** pass over an empty set. Clean. |
| the negative assertions — `test_cinv02_does_not_flag_harness_imports_under_the_archive`, `test_no_core_scoped_rule_reaches_the_archive`, `test_the_discovery_ignores_an_artifact_directory_outside_both_roots` | checked each for a **positive partner** that proves the rule fires at all | each is paired (e.g. `test_cinv02_still_rejects_a_harness_import_in_src`). **Not vacuous.** Clean. |
| the four `chunk` definitions of the test leg | re-derived at this HEAD rather than copied from `23-12` | **the derivation was WRONG on the first attempt** — see § 6. |
| prose in every file this phase changed | mechanical absence/future-tense sweep, 19 candidates read in context | **3 false** (ADV-FIX-1/2/3); 16 accurate historical statements, each read and left. |
| the three tracking files | forward-read from `deferred-items.md` item 9 | **3 stale claims** (B3) plus **1 more** the depth pass found (B2). |

---

## 6. A live demonstration of criterion 15's coverage proof, recorded because it fired on me

Re-deriving chunk 4 at this HEAD with `ls -d tests/*/` produced **1143**
collected against Wave 12's 1184.

```
sum = 1007 + 1056 + 986 + 1143 = 4192      full = 4233      SHORT BY 41
```

**The sum property caught it immediately.** Cause: `ls -d tests/*/` returns
directories only, and **41 tests live in files directly under `tests/`** —
`test_smoke.py`, `test_surface_completeness.py`, `test_surface_drift.py`,
`test_surface_shape_capture.py`. Wave 12's "27 top-level entries" included them;
my 25 directories did not.

This is the same defect class the phase has been hunting — *a subject the walk
did not reach* — arriving in the close's own measurement machinery, and it is
recorded rather than silently corrected because **the proof working is the
evidence that criterion 15 is not ceremony.**

---

## 7. The pipeline, re-run in the FOREGROUND after every fix

`make -n ci` re-printed at this HEAD is the **same ten commands** Wave 12
recorded — the leg set did not change.

| Leg | Exit | Measured at the close, after the fixes |
|---|---:|---|
| `lint` | **0** | `tools.lints --all`, silent |
| `typecheck` | **0** | `Success: no issues found in 211 source files` |
| `test` | **0** | four **foreground** chunks: `970+997+964+1184` = **4115 passed**, `37+59+22+0` = **118 skipped**, **0 failed**. `4115 + 118 = 4233` = the full `--collect-only` total. Unchanged from Wave 12 — the close's three test-file edits are docstrings and witnesses, not new `tests/` cases. |
| `gate-tools` | **0** | **415** (`tools/lints/tests`, unchanged) + **341** (`tools/publish_scan_tests tools/docs_tests`) — **339 + 2**, the two new B1 control cases, each named to this plan |
| `examples` | **0** | **exactly one** example; three harness legs at one content address `5d7bfa49f5b3…`; `legs compared 3` |
| `docs-strict` | **0** | four steps, each exit code read with **no pipe**: `--pre-build` 0, `docs/schemas` 0, `mkdocs build --strict` 0 (`Documentation built in 3.48 seconds`), `site` 0 |

**Coverage proof re-taken at this HEAD, all three properties:** sum
`1007+1056+986+1184 = 4233` = full; set-equality **both directions 0**; all six
pairwise intersections **0**.

### THE DEVIATION CARRIED TO DAVE RATHER THAN RESOLVED

**`make ci` was NOT run as a single command, at this close or at Wave 12's.**
The pipeline measures **≈ 870 s** against a **600 s** foreground tool cap. The
only way to fit it whole is to background it — and **backgrounding is exactly
what criterion 15 exists to forbid**, because a killed background run is
indistinguishable from a pass (Wave 12 reproduced this: a chunk killed at 25 s
returned `137` to a direct `wait`, printed **zero** pytest summary lines, and
read as `0` through a pipe).

It is discharged as its **own ten commands**, each in the foreground, each exit
code read with no pipe, with `make -n ci` printed as proof the ten are the
complete list.

**This is a recorded deviation and it is NOT decided here. It is Dave's.**

---

## 8. Triage summary

| Verdict | Count | Ids |
|---|---:|---|
| **BLOCKING — fixed in-phase, each re-sabotaged** | **3** | B1, B2, B3 |
| **ADVISORY — fixed in-phase** (prose this phase falsified) | **3** | ADV-FIX-1, ADV-FIX-2, ADV-FIX-3 |
| **ADVISORY — carried** | **4** | ADV-1, ADV-2, ADV-3, ADV-4 |
| **NOT NEW** (restates a briefed known finding) | **1** | gemini F-4 |
| **REJECTED as false** | **4** | REJ-1, REJ-2, REJ-3, REJ-4 |

**Zero unfixed blocking findings. No blocking finding required a ruling Dave has
not made, so no new `D-IMPL-NN` is opened and the phase does not stop on one.**

**One thing carried to Dave that is his and not mine:** the `make ci`
single-command deviation in § 7.

**Commits:** `d6cbca7` (B1), `2044ec1` (ADV-FIX-1/2/3), `a8c3af9` (B2, B3).

---

## 9. What this record does NOT claim

- It does not claim the panel read the 265 moved files, the 15 re-pointed
  published pages, or the `.planning/` tree. Those were **out of the payload**
  and are named in § 1.
- It does not claim the two passes were disjoint. They were not, on the one
  finding both could see (§ 3).
- It does not claim `/gsd-review` passing is sufficient. **It is necessary and
  never sufficient. Approval authority is Dave's alone.**
- **No `D-GATE-23` entry is written by this plan. `phase-23` is not merged. The
  phase is presented, and it stops.**
