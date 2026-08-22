---
phase: 21
kind: close-review
subject: shipped artifacts
reviewers: [gemini, codex, cursor]
reviewed_at: 2026-08-22T00:00:00-07:00
self_reviewer_skipped: claude (executing model — §3.1 independence)
base: c51406be1170259336e8799f5d4c69b2e39d4c8a..HEAD
source_inlined: 2374 lines / 182 KB (the whole of tools/docs_tests/test_requirement_ledger.py,
  all 143 rows of the traceability table of .planning/REQUIREMENTS.md with real line
  numbers, and the whole of 21-FINDINGS.md)
blocking_found: 3
blocking_fixed_in_phase: 3
advisory_carried: 7
rejected: 3
---

# Cross-AI CLOSE Review — Phase 21 (SHIPPED ARTIFACTS)

Distinct from the pre-execution plan reviews (three checker passes, 10 → 8 → 5
findings, plus two planner revisions and a surgical advisory pass), which survive in
their own files. This panel read the **committed tree** — the verdicts and the check
module, not the plans, whose decisions are already executed.

**Every finding below was verified against the tree before it was recorded.** Three
were confirmed by running the shipped functions against doctored inputs and are
BLOCKING; seven were confirmed and are advisory; **three were rejected** and are
recorded as rejected with the evidence that refutes them.

## Reviewer roster, and what each actually did

| Reviewer | Invocation | Outcome |
| --- | --- | --- |
| **gemini** | `gemini -p -` with 182 KB of inlined source, `GOOGLE_API_KEY` from `/home/parkave/homecams_v2/.env` | **Reviewed.** Cited real line numbers throughout; two findings offered as BLOCKING, both rejected on verification; two advisories, one confirmed. |
| **codex** | `printenv CODEX_API_KEY \| codex login --with-api-key`, then `codex exec --skip-git-repo-check -` on the same file | **Reviewed — genuinely, this time.** Every symbol and line it cited resolves. It emitted the bubblewrap sandbox warning this host always emits, but because the source was inlined rather than referenced by path, the sandbox failure could not silently empty its subject. Four BLOCKING offered (two confirmed, one confirmed-as-advisory, one rejected), one advisory. |
| **cursor** | `CURSOR_API_KEY` exported, `cursor agent -p --mode ask` (no `--trust` flag; it does not exist in the installed version) | **Reviewed.** The most thorough of the three: it built an assertion-to-non-vacuity-anchor table covering every shipped gate. Declared "blocking: none" but two of its advisories are blocking under this phase's own bar, and are promoted below with its finding credited. |
| **claude** | not invoked | **Skipped by design** — §3.1 independence; it is the executing model. The additive single-agent review below is separate and is not a substitute for the panel. |

The panel was briefed on the phase's five known defects and told **not to re-derive
them**, and pointed instead at the defect class: *a check that passes for a reason
unrelated to what it claims to test.* Two reviewers independently walked straight into
the same two instances of that class inside this phase's own machinery.

## Triage

| # | Origin | Finding | Class | Disposition |
| --- | --- | --- | --- | --- |
| **B-1** | codex (blocking) + cursor (advisory 1), converged | Every emptiness assertion's pathspec is unvalidated; a one-key typo makes it vacuous and `CONTROL A`/`CONTROL 13` cannot see it | BLOCKING | **Fixed in-phase**, `CONTROL 16` + positive twin |
| **B-2** | codex (blocking) + cursor (advisory 2), converged | No standing check requires a verdicted row to carry a citation at all; `RECON-02` claims criterion 3 `Complete` | BLOCKING | **Fixed in-phase**, `CONTROL 17` + `CONTROL 17b` |
| **B-3** | codex (blocking, reframed) + cursor (advisory 3) | The `DOCS-06`/`DOCS-08` unguarded-`ci`-composition gap never reached `21-FINDINGS.md`, the document Dave rules from | BLOCKING (missing deliverable element) | **Fixed in-phase**, recorded not closed |
| R-1 | codex | "the citation lint resolves" is stronger than the module checks — no symbol resolution anywhere | — | **REJECTED** — measured false |
| R-2 | gemini | `fabric_diff` is blind to the working tree | — | **REJECTED** — true, documented, and not a defect |
| R-3 | gemini | the completeness gate is blind to rows minted `Pending` after the rosters froze | — | **REJECTED as a defect** — intended and documented; recorded as advisory A-1 |
| A-1 | gemini (reframed) | nothing stops the ledger accumulating *new* unverdicted rows in silence, which is how the 54 arose | ADVISORY | Carried — a ruling for Dave |
| A-2 | gemini | `test_no_row_in_the_working_set_carries_two_verdicts` cannot fail unless the ledger-wide gate also fails | ADVISORY | Carried |
| A-3 | codex | `CONTROL 2` does not assert `spine.py` is unique, so a second one would let it pass through the ambiguity branch | ADVISORY | Carried |
| A-4 | cursor | `test_the_parse_does_not_depend_on_the_process_cwd` asserts less than its docstring claims | ADVISORY | Carried |
| A-5 | cursor | 79 rows outside the 54 carry a Complete-family verdict and no citation — pre-existing criterion-3 debt | ADVISORY | Carried — `D-19` carve-out |
| A-6 | cursor + codex | `DOCS-06`, `DOCS-08`, `CLNT-16` read `Complete` while their cells admit an unguarded or not-yet-loaded limb | ADVISORY | Carried — B-3 puts it in front of Dave |
| A-7 | **single-agent review** | `_table_line` is non-unique for all fourteen `CPS-` rows, because the CPS-lane evidence table is a third status channel no gate reads | ADVISORY | Carried |
| A-8 | **single-agent review** | this phase introduced 28 new uppercase `**COMPLETE**` verdict spellings into the checkbox channel, which the vocabulary gate does not read | ADVISORY | Carried |

---

## BLOCKING findings, verified and fixed

### B-1 — a misspelled pathspec and a clean tree are the same string, and the controls that vouch for the diff machinery diff a different constant

`fabric_diff` (module `tools/docs_tests/test_requirement_ledger.py`),
`CONTROL A` (`test_control_a_a_base_and_path_that_differ_produce_output`),
`CONTROL 13` (`test_control_13_a_changed_tests_tree_would_be_detected`),
and the five assertions built on them.

**Origin:** codex blocking #3, and cursor advisory 1 arrived at the same place from
the other end ("CONTROL 13 differs on `.planning/` only — mislabeled"). Two
independent reviewers, one hole.

**What the module claims.** Five assertions say a tree is untouched by requiring
`git diff --stat <base>..HEAD -- <spec>` to be the empty string: `FABRIC` (criterion
12), `FENCE` (`D-11`), `UAT_RECORDS` (`D-13`/`D-20`), `PINNED_FILES` (`D-07`) and
`TESTS_TREE` (criterion 6, `D-05`). `fabric_diff`'s own docstring names three ways an
empty string lies — empty base, empty path list, non-zero exit — and refuses all
three.

**What it actually did.** It did not refuse the fourth: **a pathspec that matches
nothing.** Measured against the shipped function at the pinned base:

| pathspec | `fabric_diff` before the fix |
| --- | --- |
| `("src/",)` — correct, and genuinely clean | `""` |
| `("scr/",)` — one transposition | `""` |
| `("tests-does-not-exist/",)` | `""` |
| `("tools/lints/citation.py",)` — singular, for `citations.py` | `""` |

`git` exits **zero** on every one. A typo in any of the five constants converts its
assertion into a test of nothing, silently.

**Why the existing controls could not see it.** `CONTROL A` and `CONTROL 13` both
call `fabric_diff(base, CHANGED_TREE)` — `(".planning/",)`. Neither ever passes the
constant the assertion it vouches for actually uses. `CONTROL 13`'s name is
*`a_changed_tests_tree_would_be_detected`* and it never mentions `tests/`.

**The reproduction, run both ways.** `TESTS_TREE` was changed to `("tests-typo/",)`:

| module under test | result |
| --- | --- |
| the module **as it shipped at wave 6** (`773775a`) | **45 passed — all green.** Criterion 6's mechanical limb tests nothing and its own control agrees it is fine. |
| the module **with the fix** | **2 failed** — the new pathspec assertion *and* `test_no_test_was_written_to_manufacture_a_citation` itself, which now refuses instead of reporting clean |

**The fix.** A fourth refusal inside `fabric_diff`: `tracked_under(paths)` runs
`git ls-files -- <spec>` and the function refuses when it returns nothing. Every one
of the five assertions is therefore non-vacuous by construction rather than by a
control aimed elsewhere. Alongside it:

- `test_every_asserted_pathspec_names_a_tracked_subject` — the shipped assertion,
  over a named tuple of all six pathspec constants resolved at call time (`D-21`: it
  names each constant and carries no count).
- **`CONTROL 16`** — four **near-miss** spellings of the real constants (`scr/`,
  `runtimes/`, `tools/lints/citation.py`, `test/`), each first handed to raw `git
  diff` to prove it is the *silent* kind (exit 0, empty stdout) and only then to
  `fabric_diff` to watch the refusal fire. A control that only watched the refusal
  would not show what the refusal adds.
- **positive twin** — `fabric_diff(base, FABRIC)` must still return `""`. The guard
  has to admit the empty result a clean tree produces while refusing the identical
  empty result a typo produces.

**Watched red against the shipped function.** Replacing `if not tracked_under(paths):`
with `if False:` fails `CONTROL 16` and nothing else. Restored byte-identical from a
backup taken first.

### B-2 — a verdict resting on no citation at all was invisible to every gate, which is exactly how `DCD-02` survived five waves

`refuse_unresolvable`, `test_every_cited_path_in_a_status_cell_resolves_as_written`,
`test_the_scan_finds_citations_to_check`, and `RECON-02`.

**Origin:** codex blocking #1 and cursor advisory 2, independently, with the same
reproduction.

**What the row claims.** `RECON-02` reads **`Complete`**: *"Every verdict other than
`Not built` and `Orphaned` cites its evidence in the status cell as a full
repo-relative citation the citation lint resolves."* It cites four standing tests.

**What those tests actually enforce.** A different proposition. `refuse_unresolvable`
answers *given a citation, does it resolve* — plus one **global** floor that *some*
citation-shaped token exists somewhere in the table. There was **no per-row
requirement that a verdicted row carry a citation at all.**

**Measured.** One working-set row was doctored to
`| HARD-02 | Phase 9 | **Complete** — asserted without evidence |`, leaving every
other row's citations intact:

| checker | result on the doctored ledger |
| --- | --- |
| `refuse_unresolvable` | `[]` |
| `vocabulary_offenders` | `[]` |
| `unverdicted(working_set(...))` | `[]` |
| `channel_disagreements` | `[]` |
| `citations_in_status_cells` non-empty | `True` — the global floor is satisfied by the other 63 rows |

**An evidence-free `Complete` passed every gate in the module.**

**This is not hypothetical.** `DCD-02` carried a verdict, two plan numbers and no file
for five waves. It was found in wave 6 only because that plan ran criterion 3's
predicate by hand across the roster — and the wave-6 SUMMARY says so in as many
words: *"Reading would not have found it: the cell is fluent, correctly verdicted, and
cites two plan numbers that look like evidence until you try to open one."* A
predicate that has to be run by hand is a predicate that will not be run again.

**The fix.** `uncited_verdicts(document_text, roster, roster_name)` and
`test_every_verdicted_roster_row_cites_its_evidence`, over
`WORKING_SET_ROSTER | PHASE_OWN_ROSTER`, with:

- **`CONTROL 17`** — a roster row stripped of its citations is refused **by name**,
  with the green-before/red-after guarantee: `HARD-02` is asserted *not already* an
  offender on the real ledger before it is doctored, so the red is attributable to the
  mutation. The doctored cell is deliberately fluent (`**Complete** — verified against
  the tree`) because that is the shape a reader skims past.
- **`CONTROL 17b`** — the discriminator. `D-10` is that a `Not built` row names an
  absence and has no file to point at, so the rule must exempt it. The **same
  doctored cell**, differing only in the verdict word, is required to pass as
  `**Not built**` and to fail as `**Complete**`. Red-on-everything is not a check.

**Roster-scoped, and the choice is load-bearing.** Measured: **79 rows elsewhere in
the table carry a Complete-family verdict and no citation** — the `CPS-`, `DCD-03`+
and `CLNT-23`..`32` lanes, all ruled on in earlier phases and all outside this phase's
working set under `D-19`'s explicit carve-out. A ledger-wide form would be red on the
day it landed for rows `D-11` forbids this phase to touch, and would be narrowed on
its first run — leaving the one place it can honestly hold enforced by nothing. That
pre-existing debt is **carried as advisory A-5**, not smoothed over.

**Measured before writing:** all 64 rows this phase verdicted — the 54 and the ten —
already carry a citation. The new gate is green on landing and is not retrofitting a
standard the phase failed.

**Watched red against the shipped function.** `uncited_verdicts` → `return []` fails
`CONTROL 17` and `CONTROL 17b`. Deleting the `CITATION_EXEMPT_VERDICTS` skip fails
`CONTROL 17b` and the shipped assertion. Both restored byte-identical.

### B-3 — a gap named in a wave hand-off never reached the document Dave rules from

`21-FINDINGS.md`, against `21-03-SUMMARY.md`'s hand-off and the `DOCS-06` / `DOCS-08`
status cells.

**Origin:** codex blocking #4 and cursor advisory 3 both flagged that `DOCS-06` and
`DOCS-08` read `Complete` while their own cells admit the *always-on* limb is
unguarded. Verifying that led to the actual defect, which is a **missing deliverable
element** rather than a wrong verdict.

**Verified against the tree.** Plan `21-03`'s SUMMARY records: *"TWO NAMED GAPS FOR
`21-05` THAT ARE NOT `Not built` ROWS: (1) `DOCS-06` — … no test in this tree reads
the `ci` target's composition or the workflow, so the always-on limb is true by
inspection and would not go red if a later edit dropped it."* The second of the two
(`DOCS-03`'s six uncovered artifact classes) reached `21-FINDINGS.md` §2. The first
did not:

```
$ grep -n "DOCS-06\|ci\` target\|always-on limb" .planning/phases/21-*/21-FINDINGS.md
(no output)
```

It is not in `deferred-items.md` either. It exists only inside two ledger cells and one
SUMMARY — which is precisely the *this-lives-only-in-a-SUMMARY* pattern `D-IMPL-170`
rules against, and the ledger-debt pattern this phase was commissioned to end, one
level up.

**The verdicts themselves are right and were not changed.** `ci` genuinely is
`ci-core examples docs-strict gate-tools`, and `gate-tools` genuinely runs
`tools/publish_scan_tests` and `tools/docs_tests`. The rows ask whether the property
holds, not whether a test guards it. What is missing is the guard, and closing it
means writing a test that reads the `Makefile` — which is **building**, and `D-11`
forbids it here.

**The fix.** `21-FINDINGS.md` §5 gains observation 5, recording the gap, naming its
third instance (`CLNT-16`), saying why it is neither a `Not built` row nor an owed
half of a `Partial`, and saying why an audit cannot close it. **Recorded, not closed.**
The document's closing line now says the observation was added at the phase close and
that nothing else in it changed.

---

## REJECTED findings, with the evidence that refutes them

### R-1 (codex) — "the module never verifies that a cited Python symbol exists; `refuse_unresolvable` checks path existence only, so `src/ccf/client/client.py::DefinitelyMissingSymbol` passes"

**The premise is true of the module and the conclusion is false of the repository.**
`.planning/REQUIREMENTS.md` is inside `tools/lints/citations.py`'s `GATED_TREES` and
carries no `HISTORICAL_RECORDS` exemption, so the citation lint scans it and resolves
every symbol. Run against the lint's own `check_source`:

```
.planning/REQUIREMENTS.md scanned by the lint            : True
exemption_reason(".planning/REQUIREMENTS.md")            : None
check_source(... client.py::DefinitelyMissingSymbol ...)  :
  ['.planning/REQUIREMENTS.md:1 cite03-node-id cites
    src/ccf/client/client.py::DefinitelyMissingSymbol, but
    src/ccf/client/client.py defines no "DefinitelyMissingSymbol" —
    the symbol was renamed or removed; re-resolve it before citing it']
check_source(... client.py::ProductClient ...)            : []
```

`make lint` runs `--citations` and is exit 0. The module says this division of labour
in its own opening docstring: the lint catches a symbol **rename**; the module catches
what the lint drops in silence — an ambiguous basename and a **moved** path. Codex
read one half and inferred the other half was absent. **Rejected.**

### R-2 (gemini) — "`fabric_diff` is blind to the working tree, so an executor can sabotage `src/` and the gate stays green"

**True, documented, and not a defect.** `fabric_diff`'s docstring says it in the
function itself: *"this compares COMMITS and is blind to the working tree, which is
why the base-commit file is committed before this module is first run."* It was
discovered in wave 1 — `CONTROL A` did not go red on its first run for exactly this
reason — and recorded then.

The substantive point: the assertions are about **what the phase shipped**, and an
uncommitted edit is by definition not that. Every wave separately asserted
`git status --porcelain` empty at its final commit, and CI runs on a clean checkout
where working tree and `HEAD` coincide. Gemini offered it as the phase's "primary
defect class"; it is a documented property of a commit-scoped comparison.
**Rejected.**

### R-3 (gemini) — "the completeness check is blind to new rows: add `| ZZZZ-01 | Phase 22 | Pending |` and everything stays green"

**The mechanism is real and was reproduced; the disposition is wrong.** A new id
added to both channels as `Pending` is invisible to `channel_disagreements`,
`vocabulary_offenders`, `unverdicted` over either roster, and `refuse_unresolvable` —
measured, all five return `[]`.

But that is the **intended and documented** behaviour, and the alternative is worse.
`VERDICT_VOCABULARY` admits `Pending` deliberately, and says why in its own comment:
a future phase mints its requirements as `Pending` at planning time and discharges
them at execution. A gate that refused any `Pending` anywhere would be red from the
moment the next phase is planned, and would be relaxed within a day. The rosters are
frozen *because* the phase mutates the predicate that produced them — re-deriving from
today's file returns a shrinking set, which is the failure `Check C` exists to avoid.

Gemini's reproduction command is also wrong on its own terms: `make test` has
`testpaths = ["tests"]` and never runs this module; the target is `make gate-tools`.

**Rejected as a defect.** The *adjacent* observation — that nothing prevents a future
ledger accumulating unverdicted rows in silence the way these 54 did — is real and is
carried as **A-1**, a ruling for Dave rather than a defect of this phase.

---

## Advisory findings, carried

**A-1 — the standing gate stops these rows regressing; it does not stop the same
accumulation happening again.** The frozen rosters protect the 54 and the ten. A row
minted next phase can read `Pending` indefinitely with no check firing. Closing it
means a staleness rule — *a row may not read `Pending` more than N phases after the
phase it is filed against completed* — which is a policy question, not an executor's
choice. **Dave's ruling.**

**A-2 — `test_no_row_in_the_working_set_carries_two_verdicts` cannot fail
independently.** Measured: doctoring a roster row to carry two bolded verdicts turns
both it and the ledger-wide `test_no_status_cell_carries_two_verdict_tokens` red;
doctoring a **non-roster** row turns only the ledger-wide one red. The roster-scoped
test is a strict subset and adds no coverage. Harmless, and it makes criterion 1's
other half legible at the point it is claimed. Not removed at close time.

**A-3 — `CONTROL 2` is branch-fragile.** It cites `spine.py` to prove a *unique* bare
basename is refused for being bare, but asserts only that the message contains
`BARE BASENAME` — which both refusal branches emit. `spine.py` resolves to exactly one
path today (`examples/s1-01-hello-context-product/spine.py`); the day a second appears,
the control passes through the *ambiguity* branch and the unique-basename branch could
be deleted unnoticed. Cheap to close by asserting `len(index["spine.py"]) == 1` first —
deliberately not done at close time, because that is a count and `D-21` reads on the
side of naming rather than counting. **Carried.**

**A-4 — `test_the_parse_does_not_depend_on_the_process_cwd` asserts less than its
docstring.** It checks `TABLE_HEADER in ledger_text()` only. Verified that the stronger
property holds — from a foreign cwd both parsers still return 143 rows and 143
checkboxes — so the test is weak rather than wrong.

**A-5 — 79 rows outside the 54 carry a Complete-family verdict and no citation.**
`CPS-01`..`CPS-14` (bar `CPS-03`), `DCD-03`..`DCD-12` (bar `DCD-02`), and
`CLNT-23`..`CLNT-32`, which are bare `Complete` with nothing at all. Every one was
ruled on in an earlier phase and every one is outside this phase's working set under
`D-19`'s carve-out; `D-11` forbids touching them here. **This is the criterion-3 debt
the next reconciliation would inherit** and is stated so it is not a surprise.

**A-6 — three `Complete` verdicts admit an unguarded or not-yet-loaded limb in their
own cells.** `DOCS-06`, `DOCS-08` (the `ci`-composition guard) and `CLNT-16` (*"before
any example tree moves"* — not yet under load because no condemned tree has moved).
The verdicts are defensible: each row asks whether a property holds, and each does.
Whether `Partial` would be the more honest word is Dave's call. B-3 puts the substance
in front of him.

**A-7 — `_table_line` is non-unique for all fourteen `CPS-` rows.** It scans the whole
document for `| <id> | `, and the CPS-lane evidence table further down the file uses
the same shape. It **refuses** rather than doctoring the wrong line, so it is
fail-safe, but no control can ever be aimed at a `CPS-` row. The more useful reading is
what it exposes: **the CPS-lane evidence table is a third status channel**, read by
neither `traceability_rows` nor `checkbox_channel` and covered by no gate. Wave 3 hit
this from the other side when it found `CPS-03` stated in a third place that still read
`Pending by design`. **Carried.**

**A-8 — this phase introduced 28 new uppercase `**COMPLETE**` spellings into the
checkbox channel.** Measured against the pinned base: 8 rows carried it at the base
(all `DCD-`), 36 do now; the 28 added are `CLNT-01`..`CLNT-22`, `DOCS-01`..`DOCS-06`
and `HARD-01`..`HARD-03`. **Zero** appear in the traceability table, which is the only
channel `vocabulary_offenders` reads, so `D-09`'s six-word rule is not violated where
it is enforced — and the phase was following the house style of the `DCD-` rows the
criterion itself names as the model. It is nevertheless a seventh *spelling* of a fixed
vocabulary, living in a channel no gate reads. Normalising it, or extending the
vocabulary gate to the checkbox channel's long form, is **Dave's call**.

---

## The additive single-agent code review

Run in addition to the panel and never as a substitute — it reads at a depth a panel
prompt cannot carry, and it can *run code*, which no panel member can. In Phase 20 it
found what the panel structurally could not; here it produced two findings the panel
did not raise (**A-7**, **A-8**), performed the empirical verification that
confirmed B-1 and B-2 and refuted R-1, R-2 and R-3, and re-measured every count in
`21-FINDINGS.md` §1 against the shipped parser.

What it checked beyond the panel's reach:

| Check | Result |
| --- | --- |
| the §1 census, re-parsed from the shipped module | **38 `Complete`, 2 `Complete as ruled`, 9 `Partial`, 5 `Not built`, 0 `Orphaned`** — agrees with `21-FINDINGS.md` exactly |
| the phase's own ten, re-parsed | **8 `Complete`, 2 `Partial`** — agrees |
| traceability table row count | **143** — agrees (reported, carried by no check, `D-21`) |
| rows in the 54 with a non-absence verdict and zero citation | **0** |
| rows in the ten with a non-absence verdict and zero citation | **0** |
| rows in the *whole* ledger with a non-absence verdict and zero citation | **79** → advisory A-5 |
| `_table_line` uniqueness across all 143 ids | **14 failures, all `CPS-`** → advisory A-7 |
| uppercase `**COMPLETE**`, base vs HEAD | **8 → 36** → advisory A-8 |
| the parsers from a foreign cwd | 143 rows / 143 checkboxes → advisory A-4 |
| `D-21` hardcoded-count guard over the module, **after** the two fixes | **0 matches** |
| `grep -c "def test_control_16_"` / `_17_` / `_17b_` | **1 / 1 / 1** — no control renumbered or duplicated |
| `grep -c skipif` | **0** |

---

## Every mutation run at close, and where it landed

All against the **shipped** function, each restored byte-identical from a backup taken
first, and each run **after** the relevant edit was on disk — a control run at the
wrong moment reports the wrong thing, which this phase learned in wave 1.

| # | Mutation | Result |
| --- | --- | --- |
| 1 | `if not tracked_under(paths):` → `if False:` | **RED** — `CONTROL 16`, alone |
| 2 | `TESTS_TREE` → `("tests-typo/",)`, against the **wave-6** module | **GREEN — 45 passed.** The defect, demonstrated. |
| 3 | `TESTS_TREE` → `("tests-typo/",)`, against the **fixed** module | **RED** — the pathspec assertion *and* `test_no_test_was_written_to_manufacture_a_citation` |
| 4 | `uncited_verdicts` → `return []` | **RED** — `CONTROL 17` and `CONTROL 17b` |
| 5 | the `CITATION_EXEMPT_VERDICTS` skip removed | **RED** — `CONTROL 17b` and the shipped assertion |
| 6 | a working-set row doctored to an evidence-free `**Complete**`, against the **wave-6** checkers | **GREEN on all five** — the defect, demonstrated |

## Scope fence, re-asserted at the end of the close

| Path set | `git diff --stat <pinned base>..HEAD` | working tree |
| --- | --- | --- |
| `src/ runtime/ examples/ public/ pyproject.toml` | empty | empty |
| `tests/` | empty | empty |
| `tools/lints/citations.py` | empty | empty |
| the eleven `*-VERIFICATION.md` records | empty | empty |

The only files this plan writes are `tools/docs_tests/test_requirement_ledger.py`,
`21-FINDINGS.md` §5, this record, and the regenerated coupling inventory.

## What is NOT in this record, and why

**No `D-GATE-21` entry, no ROADMAP flip, no merge, and no `RECON-09` amendment.**
Those are the gate, and the gate is Dave's. §3.1 step 3 is explicit that a review
passing is *necessary and never sufficient* — approval authority is his alone. A phase
that closed on a green panel would have skipped the gate, which is `T-21-41` in this
plan's own threat register.
