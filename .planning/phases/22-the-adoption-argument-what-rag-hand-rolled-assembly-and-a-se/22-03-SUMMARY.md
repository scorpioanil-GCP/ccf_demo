---
phase: 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se
plan: 03
subsystem: docs gates (tools/docs_tests)
tags: [DOCS-15, wording-gate, non-vacuity, injected-controls, denial-limb, D-06]
status: complete
requires:
  - public/concepts/answers-no-document-contains.md (plan 02's shipped page — READ, never edited)
  - tools/docs_tests/_prose.py (unmodified; the paragraph reader)
  - tools/lints/citations.py (unmodified; NODE_ID, repo_index, resolve_cited, symbol_spans)
provides:
  - "tools/docs_tests/test_adoption_wording.py: AW-1 and AW-2 as a standing gate over public/, 24 tests"
  - "the D-06 per-claim symbol resolver — LANDED, not owed"
affects:
  - .planning/phases/22-*/22-04-PLAN.md (the DOCS-15 ledger cell reads the D-06 disposition)
  - .planning/phases/22-*/22-05-PLAN.md (the phase record copies the D-06 disposition)
  - docs/surface/examples/RETIREMENT-COUPLINGS.md (regenerated; no new rows)
tech-stack:
  added: []
  patterns: [paragraph-candidacy-sentence-judgement, three-condition-denial-limb, split-corpus-floor, injected-violation-control]
key-files:
  created:
    - tools/docs_tests/test_adoption_wording.py
    - .planning/phases/22-.../22-03-SUMMARY.md
  modified: []
decisions:
  - "CAVEAT_CONTRACT matches Paragraph.raw and is the ONLY constant that does — proven by contrast, not asserted"
  - "The denial limb is THREE conditions; the mutation count tracks the condition count"
  - "D-06 LANDED — the resolver is stronger than cite03 in one place: an unresolvable path is a failure here, unchecked there"
  - "Control 1's cross-assertion reads 'AW-2 behaves as on the clean page', not 'both AW-2 predicates are empty' — the plan's literal wording is unsatisfiable against a fixture that ships the caveat"
metrics:
  duration: ~85 min
  completed: 2026-08-23
  tasks: 3
  commits: 3
---

# Phase 22 Plan 03: The standing wording gate — Summary

One module, `tools/docs_tests/test_adoption_wording.py`, **1052 lines and 24
tests**: two obligations over the published tree, seven non-vacuity floors,
twelve injected-violation controls, and **nine sabotage mutations across eight
sabotage runs**, every one watched RED and reverted.

The page was **read and never written**. `git status --porcelain public/` is
empty at this plan's end and was empty after every full module run.

---

## What shipped

| Task | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | The module, its vocabulary, its floors, its three shipped assertions | `a75da38` | `tools/docs_tests/test_adoption_wording.py` |
| 2 | The eleven injected-violation controls | `967406e` | `tools/docs_tests/test_adoption_wording.py` |
| 3 | D-06 lands — the resolver, its floor, its control | `3ed8403` | `tools/docs_tests/test_adoption_wording.py` |

Test inventory, 24:

- **7 floors** — `test_the_published_directory_exists`,
  `test_the_published_tree_has_pages`,
  `test_some_published_paragraph_names_an_external_approach`,
  `test_the_passage_vocabulary_is_present_in_the_published_tree`,
  `test_the_positive_caveat_assertion_has_something_to_assert_over`,
  `test_the_denial_limb_is_load_bearing_on_the_shipped_page`,
  `test_the_walk_does_not_depend_on_the_process_cwd`.
- **3 shipped assertions** — AW-1's negative, AW-2's negative, AW-2's positive.
- **11 controls** — controls 1 through 11.
- **3 for D-06** — the floor, the resolver assertion, control 12.

---

## The nine `#:` field lines, verbatim

Every vocabulary names the `Paragraph` field it is matched against.
`CAVEAT_CONTRACT` is the only one on `.raw`.

```
#: AW-1's subjects — the external approaches the page is compared against.
#: **Matched against ``Paragraph.text``**: these are prose nouns, and an

#: AW-1's offence — the ``X can't Y`` shape. **Matched against
#: ``Paragraph.text``**: it is ordinary prose, and a limit verb inside a code

#: AW-2's subject. **Matched against ``Paragraph.text``**: the prose forms are
#: what a reader takes away. **Never a bare ``passage``** ...

#: AW-2's verb. **Matched against ``Paragraph.text``**. Note that ``generated``
#: is absent on purpose ...

#: AW-2's object of extraction. **Matched against ``Paragraph.text``**: it is
#: prose. Required alongside ``EXTRACTION_VERB`` ...

#: The denial limb's vocabulary — condition (i). **Matched against
#: ``Paragraph.text``**: it is prose. Deliberately NARROW ...

#: The denial limb's condition (iii). **Matched against ``Paragraph.text``**:
#: a pivot written inside a code span is not a pivot a reader reads.

#: The caveat's first half — the contract ships. **Matched against
#: ``Paragraph.raw``, and it is the only constant here that is.**

#: The caveat's second half — no shipped pipeline produces those anchors.
#: **Matched against ``Paragraph.text``**: it is ordinary un-backticked prose
```

---

## The `.raw`-versus-`.text` contrast, measured on the SHIPPED page

Not asserted. Run over `_prose.published_pages()`:

```
=== A. paragraphs_carrying_the_caveat over the SHIPPED tree ===
  ['public/concepts/answers-no-document-contains.md:321']
=== B. throwaway variant: CAVEAT_CONTRACT matched against .text ===
  []
```

**One paragraph on `.raw`; zero on `.text`.** Matched against `.text`, the
positive AW-2 assertion, the "had something to assert over" floor, control 3
and control 9 would all be red on a CORRECT page, and control 7 would pass for
entirely the wrong reason. Watched: sabotage 6 below produces exactly that.

The bare-`passage` inspection, recorded rather than run as the plan's one-liner:

```
PASSAGE_ANCHOR pattern: passage anchors?|passage-level lineage
PASSAGE_ANCHOR.search("A page that names a proprietary passage fails the build; ...") -> None
```

`public/charter.md`'s proprietary-passage sentence is **not** a PASSAGE_ANCHOR
match. Across the whole tree PASSAGE_ANCHOR finds 3 paragraph occurrences (the
caveat, plus `public/concepts/pillars/hitl.md:24` and
`public/how-to/compose-a-workflow-with-hitl.md:156`), while a bare `\bpassage\b`
would find 4 — the extra one being the charter false positive the vocabulary is
written to avoid.

---

## The denial limb — the `continue` and its inline comment, verbatim

```python
            denials = [found.start() for found in EXTRACTION_DENIAL.finditer(sentence)]
            if denials:
                denial = min(denials)
                precedes = denial < min(verbs)
                turns = any(
                    denial < pivot.start() < verb
                    for pivot in CONTRASTIVE_PIVOT.finditer(sentence)
                    for verb in verbs
                )
                if precedes and not turns:
                    # The sentence DENIES extraction rather than asserting it,
                    # and denies it in the one word order that cannot be read
                    # the other way: an in-vocabulary denial, standing ahead of
                    # every extraction verb, with nothing turning against it
                    # before one. That is a legitimate way to be right, and it
                    # is the way ROADMAP criterion 6 requires the caveat to be
                    # written.
                    continue
```

Three conditions, all required:

- **(i) vocabulary** — `EXTRACTION_DENIAL` matches the sentence (`denials`
  non-empty).
- **(ii) ordering** — the EARLIEST denial precedes the EARLIEST extraction verb
  (`precedes`).
- **(iii) pivot** — no `CONTRASTIVE_PIVOT` stands between that denial and any
  later extraction verb (`not turns`).

### With-limb / without-limb, over the shipped page

```
=== C. with-limb / without-limb over the SHIPPED tree ===
  WITH limb   offenders: []
  WITHOUT limb offenders: ['public/concepts/answers-no-document-contains.md:321 — Pattern 5, unstructured ingestion, was never built, so no shipped pipeline produces passage anchors from documents.']
```

**Exactly one offender without the limb — the criterion-6 caveat itself.** That
is the measurement, not the argument: the limb is load-bearing on the real tree
and `test_the_denial_limb_is_load_bearing_on_the_shipped_page` holds both halves
of it.

### The pivot contrast, on the two VERBATIM measured sentences

```
=== E. S1: No shipped pipeline produces passage anchors, though CCF does extract them from documents.
   THREE-condition limb (shipped) reported: ['.../S1.md:3 — No shipped pipeline produces passage anchors, though CCF does extract them from documents.']
   TWO-condition limb  (no pivot) reported: []
=== E. S2: No shipped pipeline produces passage anchors from documents, but CCF extracts them from your documents anyway.
   THREE-condition limb (shipped) reported: ['.../S2.md:3 — No shipped pipeline produces passage anchors from documents, but CCF extracts them from your documents anyway.']
   TWO-condition limb  (no pivot) reported: []
```

Both were **EXEMPTED — reported by nothing** — under the two-condition form.
Both are refused under the three-condition form. That contrast is what makes
condition (iii) a measurement.

### The criterion-6 caveat is still exempt under all three conditions

```
=== F. criterion-6 caveat sentence under all three conditions ===
   EXTRACTION_DENIAL offsets: [(35, 'was never built'), (55, 'no shipped pipeline')]
   EXTRACTION_VERB   offsets: [(75, 'produces')]
   CONTRASTIVE_PIVOT offsets: []
   connective present: 'so'
```

Identical to plan 02's measurement, re-run here rather than copied. Earliest
denial 35 < the only extraction verb 75, and **zero pivots** — the caveat's
connective is `so`, which is not in `CONTRASTIVE_PIVOT`. It **denies and then
EXPLAINS**; the limb refuses a sentence that **denies and then TURNS**.
`test_the_denial_limb_is_load_bearing_on_the_shipped_page` is **GREEN**.

**Corrected measurement.** The plan states *"Measured across all 43 published
pages [`EXTRACTION_DENIAL`] matches 0 paragraphs and 0 occurrences today."*
That was measured before plan 02 shipped the caveat. At this plan's HEAD, over
44 pages, it matches **1 paragraph — the caveat** — which is precisely what
makes the load-bearing floor satisfiable rather than dead.

---

## The three split-floor messages, verbatim

No one of them can be satisfied by another's red:

1. `"the published tree is missing: _prose.PUBLIC_DIR resolves to {PUBLIC_DIR}, which is not a directory — every assertion in this module would pass over nothing"`
2. `"no markdown pages under {PUBLIC_DIR} — published_pages() returned 0 pages, so AW-1 and AW-2 are both scanning an empty corpus"`
3. `"no published paragraph matches EXTERNAL_APPROACH, so AW-1 is filtering an empty set and its green means nothing — this is AW-1's corpus floor and it is red"`

---

## Controls 1 and 2 — the cross-assertion lines, verbatim

Control 1 (AW-1 fires):

```python
    assert sentences_claiming_passage_extraction(pages) == [], (
        "AW-2's negative predicate fired on an AW-1 violation; the two "
        "obligations are not testing different things"
    )
    assert paragraphs_carrying_the_caveat(pages), (
        "AW-2's positive predicate lost the caveat when an AW-1 violation was "
        "injected; the two obligations are not independent"
    )
```

Control 2 (AW-2 fires):

```python
    assert sentences_asserting_a_capability_limit(pages) == [], (
        "AW-1 fired on an AW-2 violation; the two obligations are not testing "
        "different things"
    )
```

---

## The eight sabotage runs — nine mutations, literal output

Every one was applied, observed, and reverted from a byte-copy backup; the
module returned to green after each. `grep -n "SABOTAGE"` on the shipped file
returns nothing.

### Sabotage 1 — `EXTERNAL_APPROACH` neutered

```
E       AssertionError: no published paragraph matches EXTERNAL_APPROACH, so AW-1 is filtering an empty set and its green means nothing — this is AW-1's corpus floor and it is red
E       assert []
FAILED ...::test_some_published_paragraph_names_an_external_approach
1 failed, 9 passed
```

**Exactly one test RED**, and it is the vocabulary floor.
`test_the_published_directory_exists` and `test_the_published_tree_has_pages`
both stayed **GREEN** — which is the whole point of splitting the floor. Under
the bundled form, a red from either of those would have satisfied a control
asking only for "a red naming the external-approach vocabulary."

**A note worth keeping, because it is the same defect class in miniature.** The
first attempt at this sabotage replaced only the `\bRAG\b` alternative and the
suite stayed **green at 10 passed** — the other nine alternatives still matched
the page. A sabotage that neuters part of a constant proves nothing about the
constant. The mutation was redone against the whole compiled pattern.

### Sabotage 2 — `CAVEAT_ABSENCE` neutered

```
E       AssertionError: AW-2 is violated: no published paragraph states both halves of the passage-anchor caveat. Half a caveat still parses as honest — the contract half alone reads as a shipped capability, and the absence half alone reads as a gap with no contract behind it — which is why both halves are required in ONE paragraph, the contract half matched against Paragraph.raw and the absence half against Paragraph.text
E       assert []
FAILED ...::test_the_passage_anchor_caveat_states_both_halves_in_one_paragraph
1 failed, 9 passed
```

The AW-1 assertion stayed **GREEN**.

### Sabotage 3 — `LIMIT_VERB` neutered

```
E       AssertionError: AW-1 admitted a naked capability claim — the gate is scanning nothing, or EXTERNAL_APPROACH/LIMIT_VERB have drifted
E       AssertionError: a negation in a neighbouring sentence exonerated a capability claim — the scoping regressed from sentence to paragraph
FAILED ...::test_control_1_an_injected_capability_limit_sentence_is_refused
FAILED ...::test_control_4_a_negation_in_a_different_sentence_does_not_exonerate
2 failed, 19 passed
```

- **RED:** control 1, and control 4 (its offending half — the plan did not
  predict control 4, and the extra red is correct: control 4's first half also
  asserts AW-1 fires).
- **GREEN:** `test_control_5_...` and `test_control_6_...`, confirmed by a
  targeted run (`2 passed, 19 deselected`). A neutered negative predicate must
  break the control that vouches for it, not the false-positive controls.

### Sabotage 4 — `EXTRACTION_VERB` neutered

```
E       AssertionError: no published sentence matches PASSAGE_ANCHOR, EXTRACTION_VERB and DOCUMENT_SOURCE together, so the EXTRACTION_DENIAL limb is exempting nothing on this tree — it is dead code and its removal would not be noticed
E       AssertionError: AW-2 admitted a claim that CCF extracts passage anchors from documents — either the gate is scanning nothing, or the denial limb has become unconditional
E       AssertionError: AW-2 admitted a bare positive extraction claim carrying no denial at all — the denial limb has become unconditional and the obligation is switched off
E       AssertionError: condition (i) failed: an out-of-vocabulary negation exonerated a positive extraction claim — EXTRACTION_DENIAL has been widened into a general negation vocabulary
FAILED ...::test_the_denial_limb_is_load_bearing_on_the_shipped_page
FAILED ...::test_control_2_an_injected_extraction_claim_is_refused
FAILED ...::test_control_10_a_positive_extraction_claim_without_any_denial_is_refused
FAILED ...::test_control_11_a_decoy_negation_does_not_exonerate
4 failed, 17 passed
```

Control 2 RED naming AW-2, `test_control_1_...` **GREEN**. The blast radius is
wider than the plan predicted (the load-bearing floor, control 10 and control 11
also go red) and that is correct rather than a defect: neutering the extraction
verb blinds the whole AW-2 negative predicate, so every test that asserts it
fires must fail.

### Sabotage 5 — `_copied_tree` returns an empty page list

```
FAILED ...::test_control_1_an_injected_capability_limit_sentence_is_refused
FAILED ...::test_control_2_an_injected_extraction_claim_is_refused
FAILED ...::test_control_3_the_unmodified_copy_passes_every_assertion
FAILED ...::test_control_4_a_negation_in_a_different_sentence_does_not_exonerate
FAILED ...::test_control_10_a_positive_extraction_claim_without_any_denial_is_refused
FAILED ...::test_control_11_a_decoy_negation_does_not_exonerate
6 failed, 15 passed
```

Named, not disjunctive:

| Test | Outcome | Reason |
| --- | --- | --- |
| control 1 | **RED** | asserts a predicate is non-empty |
| control 2 | **RED** | asserts a predicate is non-empty |
| control 3 | **RED** | asserts the caveat result is non-empty — routed through `_copied_tree` on purpose so it can notice |
| control 4 | **RED** | asserts a predicate is non-empty |
| control 10 | **RED** | asserts a predicate is non-empty |
| control 11 | **RED** | asserts three predicates are non-empty |
| control 5 | GREEN **VACUOUSLY** | asserts `== []`, which an empty page list satisfies |
| control 6 | GREEN **VACUOUSLY** | asserts `== []` |
| control 8 | GREEN **VACUOUSLY** | asserts `== []` |
| control 9 | GREEN, correctly | builds its own page in `tmp_path`; `_copied_tree` is not its fixture route |
| control 7 | GREEN, correctly | uses `_copy`, not `_copied_tree` — see the prediction correction below |

**That contrast is the real discriminator: it is the demonstration that a
false-positive control cannot detect its own fixture disappearing, which is
precisely why controls 1, 2 and 4 exist alongside them.**

No control raised an unrelated exception — no `IndexError`, no
`StopIteration`, no `KeyError`. The source-exists assertion inside `_copy` held.

**Prediction correction.** The plan predicted control 7 would be *"vacuously
GREEN"*. It is green for the **correct** reason: control 7 routes through
`_copy` (it needs the unmutated file in order to substitute a half away), so
breaking `_copied_tree` cannot reach it at all. Recorded as a correction rather
than rerouting the control, on the same reasoning the plan applies to its own
control-9 prediction — a sabotage whose prediction is wrong teaches nothing, and
the prediction is part of the sabotage.

### Sabotage 6 — `CAVEAT_CONTRACT` matched against `Paragraph.text`

```
FAILED ...::test_the_positive_caveat_assertion_has_something_to_assert_over
FAILED ...::test_the_passage_anchor_caveat_states_both_halves_in_one_paragraph
FAILED ...::test_control_1_an_injected_capability_limit_sentence_is_refused
FAILED ...::test_control_3_the_unmodified_copy_passes_every_assertion
FAILED ...::test_control_9_a_backticked_identifier_spelling_is_still_seen
5 failed, 16 passed
```

Control 9's message:

```
E       AssertionError: the backticked identifier spelling was not seen: CAVEAT_CONTRACT must be matched against Paragraph.raw, not .text — got []
E       assert 0 == 1
```

**`test_control_7_a_caveat_missing_its_absence_half_is_refused` stayed GREEN —
for the WRONG reason.** Its predicate returns `[]` whether or not the fixture
removed the right half, because the contract half is invisible in `.text` to
begin with. That is the exact failure mode the field split exists to prevent,
and watching it is what makes the split a decision rather than a preference.
Control 1 and `test_the_passage_anchor_caveat_...` went red beyond the plan's
prediction — both assert the caveat is still found, so both correctly notice.

### Sabotage 7a — the VOCABULARY condition: `EXTRACTION_DENIAL` matches everything

```
E       AssertionError: condition (i) failed: an out-of-vocabulary negation exonerated a positive extraction claim — EXTRACTION_DENIAL has been widened into a general negation vocabulary
FAILED ...::test_control_2_an_injected_extraction_claim_is_refused
FAILED ...::test_control_10_a_positive_extraction_claim_without_any_denial_is_refused
FAILED ...::test_control_11_a_decoy_negation_does_not_exonerate
3 failed, 18 passed
```

- **RED:** controls 2, 10 and 11, all naming AW-2.
- **GREEN for the WRONG reason:**
  `test_the_denial_limb_is_load_bearing_on_the_shipped_page` — an unconditional
  exemption satisfies its "returns no offender" half while its "is a candidate"
  half is untouched. **A floor cannot detect a limb that has become
  unconditional**, which is exactly why controls 10 and 11 exist.
- **GREEN, correctly:** `test_control_3_the_unmodified_copy_passes_every_assertion`.
  (Targeted run: `2 passed, 19 deselected` for the two together.)

### Sabotage 7b — the ORDERING condition: `precedes = True`

```
E       AssertionError: condition (ii) failed: a denial standing AFTER the extraction verb exonerated the claim — the limb has become position-blind
FAILED ...::test_control_11_a_decoy_negation_does_not_exonerate
1 failed, 20 passed
```

- **RED:** control 11 **on its (b) ordering half**, named in the message.
- **GREEN:** control 10, and everything else. **A position-blind limb is
  invisible to every control except the one written for it.**

### Sabotage 7c — the PIVOT condition: `turns = False`

```
E       AssertionError: condition (iii) failed: a leading denial followed by a contrastive pivot exonerated the claim riding the clause after it — this is the exact sentence the two-condition form exempted
FAILED ...::test_control_11_a_decoy_negation_does_not_exonerate
1 failed, 20 passed
```

- **RED:** control 11 **on its (c) pivot half**, and the message says which half.
- **GREEN, named explicitly:** `test_control_10_...`,
  `test_control_2_...`, `test_the_denial_limb_is_load_bearing_on_the_shipped_page`
  and `test_control_3_...` (targeted run: `4 passed, 17 deselected`). Control
  11's (a) and (b) halves also still held — the failure raised at the (c)
  assertion, which is the third in the test, so the first two passed.
  **A pivot-blind limb is invisible to the vocabulary and ordering halves, which
  is exactly the state the two-condition form shipped in.**

### Sabotage 8a — D-06: `NODE_ID` neutered

```
FAILED ...::test_the_published_tree_carries_node_ids_to_resolve
FAILED ...::test_control_12_a_renamed_symbol_and_a_missing_file_are_both_refused
2 failed, 22 passed
```

`test_every_published_node_id_resolves` stayed **GREEN — vacuously**, which is
precisely what its floor and its control exist to catch.

### Sabotage 8b — D-06: the symbol-existence check dropped

```
E       AssertionError: a renamed symbol resolved anyway — the resolver is reading nothing, got []
E       assert False
FAILED ...::test_control_12_a_renamed_symbol_and_a_missing_file_are_both_refused
1 failed, 23 passed
```

Control 12's fixture-integrity assertion (`the fixture's anchor node id is
gone`) passed first, so the red came from the mutation and not from a broken
fixture.

---

## D-06 — LANDED

The plan's decision rule, its three conditions evaluated explicitly:

| Condition | Value |
| --- | --- |
| The module from tasks 1 and 2 is green with every sabotage reverted | **TRUE** — `21 passed` after each of the seven reverts |
| `make gate-tools` is exit 0 | **TRUE** — `288 passed in 46.43s`, `GATE-TOOLS EXIT=0`, **no deselect** |
| The executing context is still under half consumed | **TRUE** — well under half at the point of decision |

All three held, so it landed. Three tests were added, taking the module from 21
to **24** — the number the plan named, and it is the right number because a
resolver ships with its own floor and its own control or it does not ship.

**What it asserts.** Every `path::symbol` node id appearing anywhere under
`public/` resolves: the path resolves to a repo file, and that file defines the
symbol. It reuses `NODE_ID`, `repo_index`, `resolve_cited` and `symbol_spans`
from `tools/lints/citations.py` rather than reimplementing any of them, so the
test and the lint cannot drift apart.

**What it adds over `cite03-node-id`, stated rather than assumed.** The
citation lint already runs `cite03` over `public/`. This is stronger in exactly
one place: `cite03` treats a node id whose **path** does not resolve as
UNCHECKED, on the sound general reasoning that `module.py::test_name` in prose
is more often a placeholder than a broken pointer. On the published tree that
policy leaves a hole — a node id on a page is an invitation to the reader to
open it, and one pointing at a file that no longer exists is precisely the
strong-looking-claim-with-nothing-behind-it defect this phase's page exists to
model the opposite of. Here it is a failure. Control 12's second half is written
against that difference specifically. It is also reached by a different gate:
this runs under `make gate-tools` and the CI docs job, where `cite03` runs under
`make lint`.

**Measured today:** 22 node ids across the published tree, all on
`public/concepts/answers-no-document-contains.md`; **0 unresolvable paths, 0
missing symbols.**

*(There is no `D-06 owed` section in this SUMMARY, and that is the correct
outcome rather than an omission — the naming obligation in ROADMAP criterion 15
fires only when the stretch does not land. Plans 04 and 05 should record the
disposition as LANDED.)*

---

## Gates

| Gate | Result |
| --- | --- |
| `pytest tools/docs_tests/test_adoption_wording.py -q` | **24 passed** |
| `pytest tools/lints/tests -q` | **406 passed** |
| `pytest tools/publish_scan_tests tools/docs_tests -q --deselect ...test_the_committed_report_is_current` | **287 passed, 1 deselected** (at task 2's end) |
| `make gate-tools` (no deselect) | exit **0** — **291 passed** at task 3's end |
| `python -m tools.lints --all` | exit **0** |
| `git status --porcelain examples/ src/ runtime/ public/` | prints nothing |
| `grep -n "subprocess\|os.walk\|glob\|grep"` on the module | no match — the walk is `_prose`'s |
| `grep -n "SABOTAGE"` on the module | no match — every mutation reverted |

---

## The coupling report

Regenerated in task 3 with exactly:

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
```

`.venv/bin/python -c "import joserfc"` prints `joserfc OK` — the interpreter
that ran the sweep has the dependency whose absence causes the silent six-row
drop. The system `python3` was never used for the sweep.

```
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
264 coupling rows across 81 files (146 rows outside the three swept trees); 1894 files scanned
```

| | Coupling rows | Files |
| --- | --- | --- |
| Committed at plan start | **264** | 81 |
| After task 3's regeneration | **264** | 81 |

The count did not fall, so the silent-drop trap did not fire. `git diff` over
the report is **empty**: the new `tools/docs_tests/` module produced **no
coupling rows**, because it names no retiring path.
`test_the_committed_report_is_current` was green before and after
(`make gate-tools` exit 0 with no deselect). The scanned-file count rose from
1892 to 1894, which is the module plus one, and does not affect the row table.

The report is regenerated **once more after this SUMMARY is written**, because
`tools/retirement_sweep.py` is an `os.walk` from the repo root and
`.planning/phases/22-*` files are sweep subjects.

---

## Deviations from Plan

### Auto-fixed

**1. [Rule 1 — an unsatisfiable acceptance] Control 1's cross-assertion reads
"AW-2 behaves as on the clean page", not "AW-2's two predicates return empty"**

- **Found during:** Task 2, writing control 1.
- **Issue:** The plan asks control 1 to assert *"AW-2's two predicates return
  empty."* The fixture is a copy of the adoption page, which **ships the
  caveat** — so `paragraphs_carrying_the_caveat` returns one paragraph, by
  design and by ROADMAP criterion 6. Asserting it empty is unsatisfiable
  against a correct fixture, and satisfying it would require a fixture stripped
  of the caveat, which would destroy control 3's baseline value.
- **Fix:** Control 1 asserts `sentences_claiming_passage_extraction(pages) == []`
  (AW-2's negative predicate is silent on an AW-1 violation) **and**
  `paragraphs_carrying_the_caveat(pages)` is non-empty (AW-2's positive
  predicate is undisturbed). That is the same cross-assertion the plan wants —
  *the two obligations are testing different things* — stated against what the
  clean page actually does.
- **Files modified:** `tools/docs_tests/test_adoption_wording.py`
- **Commit:** `967406e`

**2. [Rule 3 — a blocking fixture bug] `_copy` creates its parent directory**

- **Found during:** Task 2, first run.
- **Issue:** Controls 4 and 11 use per-half subdirectories (`tmp_path / "a"`,
  `tmp_path / "b"`, …) so their copied trees cannot observe each other.
  `shutil.copy` raised `FileNotFoundError` because pytest's `tmp_path` exists
  but its children do not.
- **Fix:** `_copy` calls `tmp_path.mkdir(parents=True, exist_ok=True)` before
  copying. The source-exists assertion is unchanged and still fires first.
- **Files modified:** `tools/docs_tests/test_adoption_wording.py`
- **Commit:** `967406e`

**3. [Rule 2 — a stale measurement carried into a docstring] `EXTRACTION_DENIAL`
matches 1 paragraph today, not 0**

- **Found during:** Task 1, measuring before writing.
- **Issue:** The plan records *"Measured across all 43 published pages it
  matches 0 paragraphs and 0 occurrences today."* That was true before plan 02
  shipped the caveat. Writing it into the module docstring would have published
  a false measurement on a gate whose subject is honest claims.
- **Fix:** The docstring and this SUMMARY record the re-measured value: 44
  pages, **1** matching paragraph — the caveat — which is what makes
  `test_the_denial_limb_is_load_bearing_on_the_shipped_page` satisfiable rather
  than a floor with nothing under it.
- **Files modified:** `tools/docs_tests/test_adoption_wording.py`
- **Commit:** `a75da38`

**4. [Rule 1 — a sabotage that proved nothing] Sabotage 1 redone against the
whole constant**

- **Found during:** Task 1.
- **Issue:** The first attempt neutered only the `\bRAG\b` alternative of
  `EXTERNAL_APPROACH`. The suite stayed green at `10 passed`, because the other
  nine alternatives still matched the page. A partial mutation that leaves the
  suite green is indistinguishable from a control that does not work.
- **Fix:** The mutation was redone against the entire compiled pattern and the
  floor went red as it should. Both runs are recorded above rather than the
  false start being deleted, because the false start is the lesson.
- **Files modified:** none (mutation reverted)
- **Commit:** n/a

### Prediction corrections, recorded rather than smoothed over

- **Sabotage 5, control 7** — predicted "vacuously GREEN"; actually green for
  the correct reason (it routes through `_copy`, not `_copied_tree`).
- **Sabotage 3** — control 4 also went red beyond the plan's named set, because
  its offending half asserts AW-1 fires. Correct.
- **Sabotage 4** — the load-bearing floor, control 10 and control 11 also went
  red beyond the plan's named set, because neutering `EXTRACTION_VERB` blinds
  the whole AW-2 negative predicate. Correct.
- **Sabotage 6** — control 1 and the positive AW-2 assertion also went red
  beyond the plan's named set, because both assert the caveat is still found.
  Correct.

### Not fixed — nothing escalated

No Rule 4 situation arose. **No file under `public/`, `src/`, `runtime/` or
`examples/` was touched**, `tools/docs_tests/test_requirement_ledger.py` was
not edited (it remains green, bounded by `D-IMPL-188`), and no gate went red
on the shipped page — so the inversion the plan warns about, editing the page
to suit the gate, never arose.

---

## Threat Flags

None. This plan ships no runtime surface, no network-reachable code, no request
handler, no persistence and no authentication path.

- `T-22-15` (control fixtures mutating repository content) — mitigated and
  measured: every control copies into `tmp_path` before mutating, `_copy`
  asserts the source exists so a renamed fixture refuses rather than yielding
  an empty list, and `git status --porcelain public/` is empty after a full
  module run.
- `T-22-16` (a gate that passes by matching nothing) — mitigated: seven floors,
  twelve controls, and **nine sabotage mutations** in which each predicate is
  neutered and the failure is required to name the right obligation.
- `T-22-22` (the denial limb becoming an exemption that swallows real
  overclaims) — mitigated: three conditions, three control-11 halves, three
  sabotage mutations, plus control 10 and the load-bearing floor. Each condition
  is watched separately with its named RED and GREEN sets.
- `T-22-17` (failure-message disclosure) — mitigated: messages carry
  `page:line — sentence` from the published tree only.
- `T-22-18` (CI runtime) — accepted: the module runs in 5.8 s including the
  D-06 resolver's repo index.
- `T-22-19`, `T-22-20`, `T-22-21`, `T-22-SC` — not applicable, unchanged. No
  package was installed and `pyproject.toml` was not modified.

## Known Stubs

None. Every predicate, floor, control and sabotage the plan specifies is
implemented and was observed doing what it claims.

## Tracking deferred to the orchestrator

Per `docs/DECISIONS.md` **D-15**, no `state.*` or `roadmap.*` SDK writer was
invoked, and `.planning/STATE.md`, `.planning/ROADMAP.md`,
`.planning/REQUIREMENTS.md` and `docs/DECISIONS.md` were not modified. All are
hand-edited by the orchestrator. `tools/docs_tests/test_requirement_ledger.py`
was not edited.

## Self-Check: PASSED

- `tools/docs_tests/test_adoption_wording.py` — exists, 1052 lines, 24 tests,
  all passing.
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — exists, 264 rows, current.
- `.planning/phases/22-.../22-03-SUMMARY.md` — exists.
- Commits resolve in `git log`: `a75da38`, `967406e`, `3ed8403`.
- `git status --porcelain examples/ src/ runtime/ public/` prints nothing.
</content>
