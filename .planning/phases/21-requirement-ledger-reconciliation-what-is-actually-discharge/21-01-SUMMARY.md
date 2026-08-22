---
phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge
plan: 01
subsystem: testing
tags: [ledger, audit, citations, sabotage-controls, ci, git-diff]

requires:
  - phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
    provides: the pinned-diff-base pattern and its two non-vacuity controls
provides:
  - a full-history checkout on the CI `docs` job, which is the job that runs `tools/docs_tests`
  - `21-BASE-COMMIT.txt` — the phase's diff base, pinned before any audit work happened
  - three appended `docs/DECISIONS.md` rulings (`D-IMPL-172`, `D-IMPL-173`, `D-IMPL-174`)
  - the ten `RECON-01`..`RECON-10` rows, minted `Pending` into BOTH ledger channels
  - `tools/docs_tests/test_requirement_ledger.py` — the shared strict parser, Check A, Check B, the four untouched-tree assertions, and CONTROLS 1-5, 6-9, 9b, 11 and A-C
affects: [21-02, 21-03, 21-04, 21-05, 21-06, 21-07]

tech-stack:
  added: []
  patterns:
    - "Every checker is a pure function of its subject, so a control can hand it a doctored subject"
    - "A frozen roster of NAMED ids or paths, never a count (`D-21`)"
    - "A reader RAISES on a missing anchor rather than returning an empty collection"

key-files:
  created:
    - tools/docs_tests/test_requirement_ledger.py
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-BASE-COMMIT.txt
    - .planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/deferred-items.md
  modified:
    - .github/workflows/ci.yml
    - .planning/REQUIREMENTS.md
    - docs/DECISIONS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md

key-decisions:
  - "The `docs` CI job's shallow checkout was fixed BEFORE the base was pinned, so the workflow edit is inside the base and no untouched-tree assertion ever sees it"
  - "The ten `RECON-` rows are minted unbolded `Pending`, matching the 53 existing `Pending` rows rather than `CPS-03`'s bolded one"
  - "CONTROL 4 gained a second, discriminating subject — an EXISTING markdown path — because the specified nonexistent one is refused by the wrong branch"
  - "The zero-CITATION guard is RELOCATED to plan `21-02`, not weakened: zero citation-shaped tokens exist in any status cell today, measured"

patterns-established:
  - "Sabotage the SHIPPED function and watch the numbered control go red, then restore — never a probe narrated in a SUMMARY (`D-08`)"
  - "A diff-base assertion is committed before it is first run, because `git diff <base>..HEAD` compares COMMITS and is blind to the working tree"

requirements-completed: []

duration: 95min
completed: 2026-08-21
---

# Phase 21 Plan 01: Guard the Audit Before It Starts — Summary

**Everything the audit needs in order to be guarded *while* it happens landed before a single verdict was written: a full-history CI checkout, a pinned diff base, three rulings in the append-only log, the phase's own ten requirement rows in both ledger channels, and a strict parser carrying two standing checks whose eleven numbered controls were each watched go red under deliberate mutation of the shipped function.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3 of 3
- **Commits:** 6
- **Tests added:** 33 (module went 0 → 33; `gate-tools` leg 2 went 154 → 187)

## Accomplishments

- **The CI `docs` job can now resolve a pinned base at all.** It runs `pytest tools/publish_scan_tests tools/docs_tests -q` and its checkout carried no `with:` block, so `fetch-depth` defaulted to 1. Every pinned-base assertion this plan ships resolves a SHA that is absent from a depth-1 clone; `git` exits 128 and `fabric_diff` raises by design. The job would have been red from wave 1 for the whole phase, and it passes locally, so nothing would have caught it until push. This is the `D-GATE-20` shallow-clone defect repeating in a different job.
- **Four emptiness assertions now hold the audit inside its own scope** — the fabric (`src/`, `runtime/`), the wider `D-11` scope fence, the eleven `human_verification` records, and `tools/lints/citations.py` — all against a base pinned before any audit work happened, with CONTROL A proving none of them is vacuous.
- **The ledger's invariant properties are enforced from wave 1**, where they are true of a *partially filled* table: citation form, two-channel agreement, verdict vocabulary, one verdict per cell. The completeness count is deliberately absent and belongs to plan `21-06`.
- **The phase's own ten rows entered the ledger under the same discipline as the fifty-four they audit**, in wave 1, so they face every standing check, the close panel and Dave's approval alongside them.

## Task Commits

1. **Task 1 (a0): CI docs-job full-history checkout** — `c51406b` (ci)
2. **Task 1 (a): the pinned diff base** — `3003fc8` (chore)
3. **Task 1 (b)+(c): three rulings, the untouched-tree assertions, CONTROLS A-C** — `d705f35` (test)
4. **Task 1 fix: the ported symbol name** — `baf8efb` (fix)
5. **Task 2: the ten `RECON-` rows, the strict parser, Check B** — `d21c1cf` (feat)
6. **Task 3: Check A** — `845da98` (feat)
7. **This SUMMARY + the regenerated coupling inventory** — final commit (docs)

## The measurements this plan owes the phase record

### The 54-vs-56 predicate, and why the predicate is the thing

The working set is defined by **membership against the Complete family** —
`Complete`, `Complete as ruled`, `Complete over the ruled scope` — and **never**
by a string inequality against `"Complete"`.

Measured with the shipped parser at the pinned base:

| Reading | Rows |
|---|---|
| verdict token not in `COMPLETE_FAMILY` (the correct working set) | **54** |
| verdict token `!= "Complete"` (the literal reading) | **56** |

The literal reading drags in `DCD-09` (`Complete as ruled`) and `DCD-10`
(`Complete over the ruled scope`). Both have already been ruled on by Dave, and
— decisively — both are checked `[x]` in the checkbox channel, so the ledger's
*other* channel already treats them as discharged. If they were "not Complete"
the two channels would sit at drift 2, and they sit at drift 0. A later reader
running `grep -vc "| Complete |"` will get 56 and conclude a row was skipped;
that reader is holding the wrong predicate, not finding a gap. The reason is
written into the module so it survives this SUMMARY.

### The 133-vs-143 row figures, and the fact that no check carries either

Measured with the shipped parser:

| Where | Table rows | Checkbox ids |
|---|---|---|
| at the pinned base `c51406b` | **133** | 133 |
| from task 2 of this plan forward | **143** | 143 |

The difference is exactly this phase's own ten `RECON-` rows. **They are NOT
members of the 54-row working set** — that set is a frozen roster of named ids
taken by the strict parse at the pinned base, and the ten are this phase's own.
Their verdicts are written in plan `21-06`, before the close panel.

**Per `D-21`, neither figure is carried by any standing check in this module.**
Both are reported measurements. What is asserted is that the two channels agree
**id-for-id on every id the ledger contains**, with the id set read from the
ledger rather than compared against a number. Where a fixed set is genuinely
needed it is a frozen roster of NAMED members — `PHASE_OWN_ROSTER`,
`UAT_RECORDS`, `PINNED_FILES` — so that adding a row can neither silently
satisfy nor silently break it. The `#:` provenance comment records 133 and 143
as HISTORY and says plainly that no assertion reads either: a reader who greps
the pinned base and counts 133 has not found a discrepancy.

The guard against a hardcoded count was itself verified. `grep -v '^#' <module>
| grep -Ec "\b1[0-9][0-9]\b|len\([a-z_]+\(?[a-z_]*\)?\) *[=<>!]=+ *[0-9]+"`
returns **0**. This constrained the writing: the pattern matches
`D-IMPL-172`-shaped tokens and `Makefile:138`-shaped citations as readily as it
matches `EXPECTED_ROWS = 143`, so every such reference in the module lives in a
column-0 `#` comment, which the guard strips, rather than in a docstring, which
it does not.

### The 24-vs-27 `human_needed` delta, and its cause

`gsd-sdk query audit-uat` reports **24 items across 9 files**. The files carry
**27 across 11 records**. The query **filters on each record's frontmatter
`status:`**, and therefore drops Phase 12 (`status: passed`, 1 item — whose own
prose reads *"Status: human_needed"*) and Phase 18 (`status: gaps_found`, 2
items). Criterion 11 was amended to say 27 across 11; the ruling is `D-20`.

The roster in the module was **re-derived at execution time** by globbing
`.planning/phases/*/[0-9]*-VERIFICATION.md` and keeping every record whose
frontmatter opens a `human_verification:` block. That glob matches **16** files;
**11** carry the block. The parse agrees with `21-RESEARCH.md` §7's corrected
table exactly — same eleven paths, no disagreement to report.
`test_the_uat_roster_matches_the_records_on_disk` compares the frozen roster to
that derivation **path by path and never by length**, so a roster that shrank
back to `audit-uat`'s nine fails by name, and a twelfth record appearing later
fails by name too.

`audit-uat`'s filter is **named, not fixed** — tooling repair inside an audit
phase, on `D-07`'s reasoning.

### The D-17 reading, and that it is a reading

Criterion 3's `path::symbol` binds as a **reading**, not as a literal form: the
operative clause is the criterion's own final one, *"that the citation lint
resolves."* `path::symbol` stays preferred and is **required wherever the
evidence is Python**; where the evidence is a document, an anchored line
citation the lint resolves is admissible.

The forcing fact is in the tree, not in anyone's convenience:
`tools/lints/citations.py` anchors its `NODE_ID` path group to `\.py`, so a
markdown document has **no `path::symbol` form at all** — such a token matches
neither of the lint's two patterns and is invisible to it — and roughly 24 of
the 54 rows are about documentation.

**This is a reading and NOT a relaxation granted to make the criterion
reachable.** The citation still has to resolve, and the machinery that resolves
it already ships. `D-06` is unchanged: full repo-relative paths, bare basenames
REFUSED. Logged as `D-IMPL-172`, ruled by Dave 2026-08-21, and recorded in the
module directly above `refuse_unresolvable`.

### Why the zero-citation guard is deferred to `21-02`, and that it is deferred

Measured at the pinned base with the shipped extractor:
`citations_in_status_cells(ledger_text())` returns **0** tokens — scanned with
the lint's own symbol and line-citation patterns plus the wider symbol form,
across all 133 status cells.

A guard raising on zero citations, and a precondition asserting the real file
yields a non-empty citation list, would therefore **both fail on landing** and
would redden `ci-core` for five waves — in a phase whose own `Makefile` contract
is that `ci-core` stays green from wave 1 onward. Both are **relocated** to plan
`21-02` task 1, where the first citations exist and the guard is honest.
**Neither is weakened.** Only the zero-ROW guard lands here, because a zero-row
parse is false today and must raise today.

The refusal itself is correct here and needs nothing added later: a citation, IF
present, must resolve as written. That is vacuously true at zero citations —
which is the right behaviour — and becomes load-bearing the instant `21-02`
writes the first one. The module docstring says all of this, so a reader does
not mistake the absent guard for an oversight.

## Every control, and the mutation that made it red

Eleven numbered controls plus two positive twins ship. **Every mutation below was
applied to the SHIPPED function, observed, and reverted from backup.**

| Control | What it falsifies | Mutation applied | Observed |
|---|---|---|---|
| CONTROL A | all four emptiness assertions at once | `return completed.stdout` → `return ""` | RED, while the four emptiness assertions all stayed GREEN |
| CONTROL B | an unresolvable base returning `""` | `if completed.returncode != 0:` → `if False:` | RED |
| CONTROL C | an empty base / empty path list | (argument guards; exercised, not separately sabotaged) | GREEN by refusal |
| `test_the_citation_lint_is_not_modified` | `D-07` enforced by intent rather than a check | `PINNED_FILES` → the module this phase writes | RED |
| `test_the_uat_roster_matches_the_records_on_disk` | a roster that quietly shrank | dropped Phase 12's record from the roster | RED, naming the path |
| CONTROL 6 | a verdict in one channel only | `channel_disagreements` → `return []` | RED |
| CONTROL 7 | an id in one channel only | same mutation | RED, while `test_the_two_status_channels_agree` stayed GREEN |
| CONTROL 8 | a misspelled header reported as "clean" | `traceability_rows` returns `[]` instead of raising | RED |
| CONTROL 9 | a verdict outside the vocabulary (`Done`, `Shipped`, `Closed`) | — (positive/negative pair with 9b) | GREEN by refusal |
| CONTROL 9b | a reader that took the LAST bolded run | `verdict_token` → last bolded run | RED |
| CONTROL 11 | a cell carrying two bolded verdicts | `doubled_verdicts` → `return []` | RED, while `test_no_status_cell_carries_two_verdict_tokens` stayed GREEN |
| CONTROL 1 | an ambiguous bare basename | bare-basename branch removed | RED |
| CONTROL 2 | a *unique* bare basename | same mutation | RED |
| CONTROL 3 | a path not in the tree | existence predicate → always true | RED, while the shipped assertion stayed GREEN |
| CONTROL 4 | `::symbol` on a non-Python path | (two subjects; see deviations) | GREEN by refusal |
| CONTROL 4b | a citation naming a DIRECTORY | existence predicate → always true | RED |
| CONTROL 5 | a zero-row parse reported as clean | `refuse_unresolvable` swallows the empty parse | RED |
| positive: `test_the_positive_control_a_real_citation_is_not_refused` | a checker red on everything | — | GREEN, on a path whose basename is ambiguous |
| positive: `test_the_unmodified_document_passes` | attribution of every Check-B refusal | — | GREEN |

Two of these deserve their names in prose:

- **CONTROL A did not go red on its first run, and the reason was not the
  module.** `fabric_diff` is `git diff --stat <base>..HEAD` — it compares
  COMMITS and is blind to the working tree. The plan anticipated this and said
  to commit `21-BASE-COMMIT.txt` before running the module, which is what
  happened.
- **The `PINNED_FILES` sabotage passed the first time it was run**, for exactly
  the same reason: the module was not yet committed, so pointing the assertion
  at it produced no commit-to-commit diff. It was re-run after the commit and
  went red. A control run at the wrong moment is a control that reports the
  wrong thing, which is this project's own defect class arriving inside the
  machinery built to catch it.

## Deviations from Plan

### 1. [Rule 3 — blocking] The module docstring precedes `from __future__ import annotations`

- **Found during:** Task 1(c)
- **Issue:** The plan specified `from __future__ import annotations` **first**,
  then the module docstring. Python requires a future statement to be preceded
  only by the docstring, comments and blank lines; the specified order makes the
  "docstring" a bare string expression and the module has none.
- **Fix:** Docstring first, then the future import — the order every other module
  in this repo uses.
- **Commit:** `d705f35`

### 2. [Rule 1 — bug] The ported function is `client_surface_diff`, not `fabric_diff`

- **Found during:** Task 1, first `make gate-tools`
- **Issue:** The provenance comment cited
  `tests/examples/test_hw1_harness_clients_readme.py::fabric_diff`. That module
  defines `client_surface_diff`; `fabric_diff` is this module's *new* name for
  the port.
- **Fix:** Corrected the citation. Worth recording because the **citation lint
  caught it** — `cite03-node-id`, on the first gate run after the module landed.
  A symbol RENAME is precisely the class the lint does catch, which is the half
  of its behaviour the module's own docstring credits it with.
- **Commit:** `baf8efb`

### 3. The ten `RECON-` rows are minted **unbolded** `Pending`

- **Found during:** Task 2(a)
- **Issue:** The plan's action text specifies `| RECON-NN | Phase 21 | **Pending** |`,
  while the same task's parser requirement says each row must read *"a bare
  `Pending`"*, and plan `21-06` describes its own job as replacing *"a bare
  `Pending`"*. The plan disagrees with itself.
- **Resolution:** Unbolded, matching the 53 existing `Pending` rows. Bolding ten
  more would deepen the very miscount this phase was commissioned over —
  `grep -c "| Pending |"` already misses `CPS-03` because its cell is bolded,
  and that wrong figure reached `D-GATE-20`, the ROADMAP's first draft of this
  phase and the progress report. `verdict_token` strips `**` either way, so
  nothing mechanical depends on the choice; the honesty of a grep does.
- **Commit:** `d21c1cf`

### 4. [Rule 2 — the control could not prove what it claimed] CONTROL 4 gained a second subject

- **Found during:** Task 3
- **Issue:** The plan's CONTROL 4 cites `docs/foo.md::heading` and asserts the
  refusal fires. That path **does not exist**, so it is refused by the
  *nonexistent-path* branch — CONTROL 3's branch — and the control would have
  passed with the suffix rule deleted entirely.
- **Fix:** The specified subject is kept and still asserted refused. A second,
  discriminating subject was added: `docs/DECISIONS.md::heading` — an
  **existing** markdown path — asserted refused *and* asserted refused for the
  stated reason (the message names "not Python"). The sabotage that removed the
  existence predicate left this half green and the other half red, which is what
  makes the two branches distinguishable.
- **Commit:** `845da98`

### 5. [Rule 3 — the control was inexpressible as written] CONTROL 4b's subject

- **Found during:** Task 3
- **Issue:** CONTROL 4b cites `src/ccf/client`, a directory. Neither citation
  pattern can match it: `NODE_ID` requires `.py::`, `CITATION` requires
  `.ext:NN`, and `src/ccf/client` has no suffix. The token would never be
  extracted, so the control would have asserted a refusal that could not arise —
  and would then have failed, not passed, for a reason unrelated to the
  predicate.
- **Fix:** The subject is a real tracked directory whose name carries a dot, so a
  citation pattern can actually name it:
  `.planning/phases/15.6-decision-completeness-and-defect-closure::x`. To make it
  visible the module's `LOOSE_NODE_ID` permits a leading dot, which is
  deliberately wider than the lint's own pattern and documented as such — a
  `.planning/...` citation is invisible to the lint too. The control is now
  genuinely about `is_file()` versus an existence test, and it went red when the
  predicate was neutered.
- **Commit:** `845da98`

### 6. [Rule 2] `citations_in_status_cells` needed a companion, not a changed signature

- **Found during:** Task 3
- **Issue:** The declared interface is `list[tuple[str, str]]` — `(id,
  cited_path)` — which carries no way to tell that a token arrived in
  `::symbol` form, and the suffix rule needs exactly that.
- **Fix:** The declared signature is preserved **exactly**, and a companion
  `symbol_cited_paths(document_text) -> list[tuple[str, str]]` was added for the
  `::` tokens. Nothing later in the phase has to change; plan `21-02` consumes
  `citations_in_status_cells` and `refuse_unresolvable` as specified.
- **Commit:** `845da98`

### 7. Refusal ordering differs from the plan's enumeration

- **Found during:** Task 3
- **Issue:** The plan enumerates the four refusals as (1) nonexistent, (2) bare
  basename, (3) `::` on non-Python, (4) ambiguous index. Applied in that order,
  the directory subject and the existing-markdown subject both fall to branch 1
  and the later branches are never reached.
- **Fix:** The branches are evaluated bare-basename → existence → suffix →
  index-ambiguity, which is the order in which each is the *most specific* true
  statement about the token. All four refusals are present and each has a
  control that reaches it.
- **Commit:** `845da98`

### 8. A stale `Makefile` citation was found and NOT fixed

- **Found during:** Task 3 verification
- **Issue:** `Makefile`'s `gate-tools` comment says *"The two commands are
  `.github/workflows/ci.yml:35` and `:314` verbatim"*. `:35` is correct. `:314`
  is not — at the pinned base it addressed the `docs` job's bare `steps:` line,
  not a command.
- **Disposition:** **Pre-existing, reported, not fixed.** Verified against
  `21-BASE-COMMIT.txt`'s parent: the pointer was already wrong before this
  plan's `fetch-depth: 0` edit. Nothing in the toolchain can catch it — the
  citation lint reads `.py`, `.md`, `.yaml` and `.yml`, and a `Makefile` has no
  suffix, so a line citation inside one is unchecked by construction. Logged to
  `.planning/phases/21-*/deferred-items.md` with two other named-not-fixed items
  (`audit-uat`'s filter, the citation lint's two holes) for plan `21-05` to carry
  to Dave.

## Verification

| Check | Result |
|---|---|
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **exit 0** — 33 passed |
| `make lint` (`python -m tools.lints --all`) | **exit 0** |
| `make typecheck` (`mypy --strict`) | **exit 0** — 211 source files |
| `make test` | **exit 0** — 4105 passed / 118 skipped, 10m25s |
| `make gate-tools` | **exit 0** — leg 1 406, leg 2 **187** (was 154) |
| `python -m tools.lints --citations` | **exit 0** |
| `git diff --stat <base>..HEAD -- src/ runtime/` | empty |
| `git diff --stat <base>..HEAD -- src/ runtime/ examples/ public/ pyproject.toml` | empty |
| `git diff --stat <base>..HEAD -- tools/lints/citations.py` | empty |
| `git diff --name-only <base>..HEAD -- tools/` | only `tools/docs_tests/test_requirement_ledger.py` |
| `awk '/^  docs:/{f=1;next} f&&/^  [a-z_-]+:/{f=0} f' ci.yml \| grep -c "fetch-depth: 0"` | **1** |
| `grep -c "fetch-depth: 0" .github/workflows/ci.yml` | **2** |
| `grep -c "^\| RECON-" .planning/REQUIREMENTS.md` | **10** |
| `grep -c "^- \[ \] \*\*RECON-" .planning/REQUIREMENTS.md` | **10** |
| `grep -v '^#' <module> \| grep -c "VERIFICATION.md"` | **13** (≥ 11) |
| `grep -c "skipif" <module>` | **0** |
| `grep -c "\.exists()" <module>` | **0** |
| the `D-21` hardcoded-count guard | **0 matches** |
| `grep -c "test_the_scan_finds_citations_to_check\|control_5b" <module>` | **0** |

`make ci-core` is `lint typecheck test gate-tools`. All four ran to exit 0
individually; they were run separately rather than as one command because a
full pipeline cannot complete inside this harness's foreground call budget, and
`make test` alone took 10m25s.

## Threat Flags

None. This plan reads tracked repo files and writes markdown and tests. No
credential, no network call, and no external input crosses any boundary. The
`pyproject.toml` emptiness assertion inside `FENCE` is the mechanical proof that
`T-21-SC` (no package installed by this phase) stayed true.

## Known Stubs

None. One property is deliberately **vacuous at this wave and stated as such** in
its own docstring — `test_every_cited_path_in_a_status_cell_resolves_as_written`
passes over zero citations today. That is the correct behaviour of the refusal,
not a stub: plan `21-02` lands the precondition that makes it non-vacuous, in the
same task as the first citations.

## What plan `21-02` consumes from here

- `ledger_text`, `traceability_rows`, `verdict_token`, `checkbox_channel`
- `COMPLETE_FAMILY`, `VERDICT_VOCABULARY`, `PHASE_OWN_ROSTER`
- `citations_in_status_cells`, `refuse_unresolvable`, `channel_disagreements`
- `phase_base_commit`, `fabric_diff`, `PINNED_FILES`, `FENCE`, `UAT_RECORDS`
- and it owes the zero-CITATION guard, `test_the_scan_finds_citations_to_check`,
  and `CONTROL 5b`, all three of which are deliberately absent here.
