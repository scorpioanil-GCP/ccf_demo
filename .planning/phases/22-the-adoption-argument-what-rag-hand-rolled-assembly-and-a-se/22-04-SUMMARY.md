---
phase: 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se
plan: 04
subsystem: planning ledger and the retirement-coupling report
tags: [DOCS-15, CLNT-17, ledger-verdict, s1-01-coupling, no-rows-minted, D-06-landed]
status: complete
requires:
  - public/concepts/answers-no-document-contains.md (plan 01/02's shipped page — cited, never edited)
  - tools/docs_tests/test_adoption_wording.py (plan 03's gate — cited by node id, never edited)
  - .planning/phases/22-*/22-02-SUMMARY.md (the client-seam reading, copied verbatim)
  - .planning/phases/22-*/22-03-SUMMARY.md (the D-06 LANDED disposition and its 22-node-id measurement)
provides:
  - "the DOCS-15 verdict — Complete as ruled — in both ledger channels, with ten resolving node ids of which six are the gate's own controls and floors"
  - "the s1-01 coupling recorded on DOCS-15 and CLNT-17 in both channels, and standing mechanically as 20 17-08-owned rows"
  - "the proof that this phase minted no requirement row: 149 ids at 951eb4a, 149 now, diff empty"
affects:
  - .planning/phases/22-*/22-05-PLAN.md (the phase record reads this verdict and the D-06 disposition)
  - docs/surface/examples/RETIREMENT-COUPLINGS.md (regenerated twice — after the ledger edit and after this SUMMARY)
tech-stack:
  added: []
  patterns: [hand-edited-ledger, two-channel-verdict, control-cited-verdict, venv-pinned-regeneration]
key-files:
  created:
    - .planning/phases/22-.../22-04-SUMMARY.md
  modified:
    - .planning/REQUIREMENTS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "Complete as ruled, not Complete — 22-CONTEXT.md D-02 recast the row's *states what each lacks* clause, and the row is discharged in the ruled form rather than the literal one"
  - "The ledger gate stays GREEN on a bad SYMBOL with a good PATH; the citation lint is what refuses it. Measured, not reasoned about"
  - "The client-seam reading is carried with its criterion numbers here and in the ledger, because .planning/ is not the published tree"
metrics:
  duration: ~55 min
  completed: 2026-08-23
  tasks: 2
  commits: 2 (+1 SUMMARY/report follow-up)
---

# Phase 22 Plan 04: The ledger verdict and the mechanical coupling — Summary

`DOCS-15` is verdicted **`Complete as ruled`** in both of the ledger's status
channels, with ten node ids in the cell — **six of them the gate's own controls
and floors**, because a row claiming non-vacuity should cite the proof of
non-vacuity and not only the assertion. The `s1-01` dependency is recorded on
`DOCS-15` and on `CLNT-17`, in both channels each, and it stands mechanically as
**20 `17-08`-owned rows** in the coupling report. **No requirement row was
minted**, and that is a measurement rather than a silence: 149 ids at `951eb4a`,
149 now, diff empty.

`CLNT-17` keeps its `Not built` verdict and its unticked box. Nothing under
`src/`, `runtime/`, `examples/` or `public/` moved.

---

## What shipped

| Task | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | Verdict `DOCS-15` in both channels; record the coupling on `DOCS-15` and `CLNT-17` | `cbe702a` | `.planning/REQUIREMENTS.md` |
| 2 | Regenerate the coupling report, in the venv, last | `391680d` | `docs/surface/examples/RETIREMENT-COUPLINGS.md` |

**Edit method: hand-edited.** Four lines, replaced by exact anchored string
substitution with a uniqueness assertion on each anchor. **No `state.*` writer,
no `roadmap.*` writer and no requirement-writing tool was invoked** — per
`docs/DECISIONS.md` `D-15`. `.planning/STATE.md`, `.planning/ROADMAP.md`,
`docs/DECISIONS.md`, `tools/docs_tests/test_requirement_ledger.py` and
`tools/docs_tests/test_adoption_wording.py` were not touched.

---

## The `DOCS-15` status cell, exactly as written

Written **identically** into both channels — the checkbox bullet at line 40 and
the traceability row at line 334. Identity is not asserted; it is checked: the
table cell's text is a substring of the bullet line (`True`).

```
**Complete as ruled** (`public/concepts/answers-no-document-contains.md`; `tools/docs_tests/test_adoption_wording.py::test_no_published_sentence_asserts_a_capability_limit_of_an_external_approach`, `tools/docs_tests/test_adoption_wording.py::test_no_published_sentence_claims_ccf_extracts_passage_anchors_from_documents`, `tools/docs_tests/test_adoption_wording.py::test_the_passage_anchor_caveat_states_both_halves_in_one_paragraph`, `tools/docs_tests/test_adoption_wording.py::test_every_published_node_id_resolves`; and, because this row claims non-vacuity rather than only assertion, the gate's own controls and floors: `tools/docs_tests/test_adoption_wording.py::test_control_1_an_injected_capability_limit_sentence_is_refused`, `tools/docs_tests/test_adoption_wording.py::test_control_2_an_injected_extraction_claim_is_refused`, `tools/docs_tests/test_adoption_wording.py::test_control_11_a_decoy_negation_does_not_exonerate`, `tools/docs_tests/test_adoption_wording.py::test_control_12_a_renamed_symbol_and_a_missing_file_are_both_refused`, `tools/docs_tests/test_adoption_wording.py::test_some_published_paragraph_names_an_external_approach`, `tools/docs_tests/test_adoption_wording.py::test_the_published_tree_carries_node_ids_to_resolve`) — the page ships at 339 lines, sits under Concepts in the `nav:` tree, names all three approaches this row lists, carries the UBO question as its worked demonstration, and states the passage-anchor honesty caveat with both halves in one paragraph. *Why `as ruled` rather than plainly discharged in the row's literal words*: Phase 22's `22-CONTEXT.md` `D-02` recast the *states what each lacks* clause — every contrast is written as a checkable fact about the question and about shipped mechanism, never as a capability assertion about an external approach, and the reader draws the inference — and the shipped gate then holds the recast in place rather than leaving it to reviewer diligence. No contrast needed the `D-03` paired fallback; the page carries zero of them. *What the code-backed claims ride on*: five `--8<--` snippet includes, all five against `examples/s1-01-hello-context-product` — whole-file `artifacts/ubo-question.yaml` and `artifacts/expected.yaml`, plus the `operators`, `project` and `serve` spine marker regions — and none against `examples/00`–`08` or `examples/external/00-hello-context`, so the page adds nothing to `DOCS-17`'s re-cut burden and starts the replacement direction instead. *The client-seam citation reading, copied from `22-02-SUMMARY.md` rather than paraphrased*: these citations are prose `path::symbol` node ids rather than snippet includes because no file in `src/` carries a snippet section marker at all — `grep -rn -- "--8<--" src/` returns 0 — and the `hw1` trees carry none either, so an include against the client seam is not a form that exists to be chosen; the citations are nonetheless CHECKED, by `cite03-node-id` in the citation lint, which is exactly what ROADMAP criterion 8 requires of the client-seam contrast; and criterion 3's include requirement is discharged by the five includes carrying the page's `s1-01` demonstration, which is where the page's code-backed claims about the fabric live. That is a division of labour between criteria 3 and 8, not a widening of criterion 3. *The staleness claim is narrowed to what the tree actually asserts*: it rests on the band crossing and the moving factor, carried by `expected.yaml`'s declared `debt_signal_first_question`, `debt_signal_third_question` and `debt_weak_factor` fields, because the literal figures are asserted by no test and `debt-profile.yaml` cannot be included — it measures 15 `pub01-whitepaper-shingle` findings against 0 on every source the page does include. *`D-06` LANDED and is not owed*: plan `22-03` shipped the per-claim symbol resolver with its floor and its control, 22 published node ids measured and every one resolving. **The `s1-01` coupling, recorded on `DOCS-15` and `CLNT-17` alike so it is read where either is read**: `public/concepts/answers-no-document-contains.md` now depends on `examples/s1-01-hello-context-product` — its spine marker regions and its definition artifacts — so that tree cannot be retired until the page is re-pointed or its demonstration re-homed, and the dependency lands mechanically as `17-08`-owned rows in `docs/surface/examples/RETIREMENT-COUPLINGS.md` rather than relying on anyone remembering it.
```

The bullet carries this after the requirement's own restated text, which is
unchanged word for word from the pre-edit row, and its checkbox is now `[x]`.

**Why `Complete as ruled` and not `Complete`.** The row's literal words are
*"states what each lacks against cited shipped mechanism."* Phase 22's
`22-CONTEXT.md` `D-02` recast that clause: the page states checkable facts about
the question and about shipped mechanism and lets the reader draw the inference,
and no sentence on it asserts a capability limit of an external approach. The
row is therefore discharged in the ruled form, not the literal one, and
`Complete as ruled` is the vocabulary's word for exactly that. It is a member of
`COMPLETE_FAMILY`, so the checkbox must be — and is — ticked.

**Parse check, run rather than assumed:**

```
DOCS-15 | leading = 'Complete as ruled' | cell_verdicts = ['Complete as ruled'] | checked = True
CLNT-17 | leading = 'Not built'         | cell_verdicts = ['Not built']         | checked = False
channel disagreements: []
doubled verdicts: []
vocabulary offenders: []
unresolvable citations: []
row count: 149
```

`cell_verdicts` is the union reader — the leading token plus every bolded run in
the vocabulary — so a single-member set is the proof that the appended coupling
sentence introduced no second verdict into either cell.

---

## Every node id in the cell, and the command that proved each collects

Command, once per name:

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest "<node id>" --collect-only -q
```

Literal output, all ten:

```
exit=0 | 1 test collected in 0.09s | tools/docs_tests/test_adoption_wording.py::test_no_published_sentence_asserts_a_capability_limit_of_an_external_approach
exit=0 | 1 test collected in 0.08s | tools/docs_tests/test_adoption_wording.py::test_no_published_sentence_claims_ccf_extracts_passage_anchors_from_documents
exit=0 | 1 test collected in 0.08s | tools/docs_tests/test_adoption_wording.py::test_the_passage_anchor_caveat_states_both_halves_in_one_paragraph
exit=0 | 1 test collected in 0.08s | tools/docs_tests/test_adoption_wording.py::test_some_published_paragraph_names_an_external_approach
exit=0 | 1 test collected in 0.08s | tools/docs_tests/test_adoption_wording.py::test_control_1_an_injected_capability_limit_sentence_is_refused
exit=0 | 1 test collected in 0.08s | tools/docs_tests/test_adoption_wording.py::test_control_2_an_injected_extraction_claim_is_refused
exit=0 | 1 test collected in 0.09s | tools/docs_tests/test_adoption_wording.py::test_control_11_a_decoy_negation_does_not_exonerate
exit=0 | 1 test collected in 0.10s | tools/docs_tests/test_adoption_wording.py::test_every_published_node_id_resolves
exit=0 | 1 test collected in 0.07s | tools/docs_tests/test_adoption_wording.py::test_the_published_tree_carries_node_ids_to_resolve
exit=0 | 1 test collected in 0.07s | tools/docs_tests/test_adoption_wording.py::test_control_12_a_renamed_symbol_and_a_missing_file_are_both_refused
```

Four are **shipped assertions** — the two negative limbs (`AW-1`, `AW-2`), the
positive caveat assertion, and the `D-06` resolver. **Six are controls and
floors**, cited on `DOCS-16`'s precedent: `control_1` and `control_2` watch each
negative limb refuse an injected violation, `control_11` watches the decoy
negation, `control_12` watches a renamed symbol and a missing file both refuse,
and the two floors prove the corpus the gate reads is not empty. A row that
cited only the assertions would be claiming non-vacuity with nothing to open.

The eleventh citation in the cell is the bare path
`public/concepts/answers-no-document-contains.md`, which resolves as written.

---

## No row was minted — measured, not assumed

Extracted with the ledger gate's own `traceability_rows` parser at both
revisions, so the count is the gate's reading and not a grep's.

| Revision | Requirement ids in the traceability table |
| --- | --- |
| `951eb4a` | **149** |
| this plan's HEAD | **149** |

```
$ diff <(ids at 951eb4a) <(ids now); echo "DIFF EXIT=$?"
DIFF EXIT=0
```

Empty. `.planning/REQUIREMENTS.md` at `951eb4a` was byte-identical to the file
this plan opened, so the whole delta is this plan's four lines:

```
$ git diff 951eb4a --stat -- .planning/REQUIREMENTS.md
 .planning/REQUIREMENTS.md | 8 ++++----
 1 file changed, 4 insertions(+), 4 deletions(-)
```

Two lines are `DOCS-15`'s two channels; two are `CLNT-17`'s two channels. This
is the explicit discharge of criterion 14's mint clause: the phase acquires no
`PHASE_OWN_ROSTER`, because it minted nothing to roster.

---

## `CLNT-17` — the coupling recorded, the verdict untouched

Its verdict token is still `Not built` in the table, still `**NOT BUILT**` in the
bullet, and its checkbox is still `[ ]`. The diff shows the appended sentence and
nothing else (elided in the middle for length):

```
-| CLNT-17 | Phase 17 | **Not built** — `examples/s1-00-companies-over-revenue/` and `exam  …  oval task on a measurement and returned the `D-27` ruling as an undecided checkpoint. `D-11` forbids closing this here |
+| CLNT-17 | Phase 17 | **Not built** — `examples/s1-00-companies-over-revenue/` and `exam  …  as `17-08`-owned rows in `docs/surface/examples/RETIREMENT-COUPLINGS.md` rather than relying on anyone remembering it. |
```

The appended sentence is **the same sentence in all four places** — both
`DOCS-15` channels and both `CLNT-17` channels:

> **The `s1-01` coupling, recorded on `DOCS-15` and `CLNT-17` alike so it is read
> where either is read**: `public/concepts/answers-no-document-contains.md` now
> depends on `examples/s1-01-hello-context-product` — its spine marker regions
> and its definition artifacts — so that tree cannot be retired until the page is
> re-pointed or its demonstration re-homed, and the dependency lands mechanically
> as `17-08`-owned rows in `docs/surface/examples/RETIREMENT-COUPLINGS.md` rather
> than relying on anyone remembering it.

It carries no vocabulary word in bold, which is why `cell_verdicts` still reads
one verdict per cell.

---

## Sabotage 1 — a cited node id pointing at a symbol that does not exist

Mutation:
`tools/docs_tests/test_adoption_wording.py::test_every_published_node_id_resolves`
→ `…::test_no_such_assertion`, in **both** channels (2 occurrences replaced).

**Both commands were run, and both dispositions are recorded — not a
disjunction.**

**Command A — the citation lint. RED, as required:**

```
$ PYTHONPATH=.:src:runtime .venv/bin/python -m tools.lints --all
2 CCF invariant violation(s). Fix the code, or — for CINV-01 only — add a reviewed entry to tools/lints/allowlist.yaml.
.planning/REQUIREMENTS.md:334 cite03-node-id cites tools/docs_tests/test_adoption_wording.py::test_no_such_assertion, but tools/docs_tests/test_adoption_wording.py defines no 'test_no_such_assertion' — the symbol was renamed or removed; re-resolve it before citing it
.planning/REQUIREMENTS.md:40 cite03-node-id cites tools/docs_tests/test_adoption_wording.py::test_no_such_assertion, but tools/docs_tests/test_adoption_wording.py defines no 'test_no_such_assertion' — the symbol was renamed or removed; re-resolve it before citing it
LINTS SABOTAGE EXIT=1
```

`cite03-node-id` names the rule and the bad symbol, and it names **both**
channels — line 334 (the table) and line 40 (the bullet). The bullet is caught
only because the lint walks the whole file; the ledger gate reads the table
alone.

**Command B — the ledger gate. GREEN, and this is the useful measurement:**

```
$ PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q
113 passed in 10.13s
LEDGER SABOTAGE EXIT=0
```

**It stayed green, and the reason is structural rather than accidental.**
`test_every_cited_path_in_a_status_cell_resolves_as_written` runs
`refuse_unresolvable`, whose predicate is `(REPO_ROOT / cited).is_file()` over
the **path** extracted from each citation. The mutated citation's path —
`tools/docs_tests/test_adoption_wording.py` — still exists, so the row still
resolves by that gate's standard. The gate's own docstring says as much: it
exists to catch a file **move** and the two silent-drop holes in the lint's
resolver, and it says the lint is what catches a symbol **rename**.

So the two checkers divide the guarantee, and the division is worth stating
where a later reader will find it: **the ledger gate guarantees that a cited
file is in the tree; the citation lint guarantees that the cited symbol is in
that file.** A row whose citations were checked by only one of them is half
checked. Both run in `ci-core` — the gate through `make gate-tools`, the lint
through `make lint`.

**Reverted from a byte-copy and re-confirmed:**

```
REVERTED byte-identical
LINTS REVERTED EXIT=0
113 passed in 10.44s
LEDGER REVERTED EXIT=0
```

---

## Sabotage 2 — the two channels made to disagree

Mutation: `- [x] **DOCS-15**:` → `- [ ] **DOCS-15**:`, leaving the table verdict
at `Complete as ruled`.

```
E  DOCS-15 reads '**Complete as ruled** (…)' in the traceability table and checked=False in the checkbox list. The two channels disagree about whether this requirement is discharged
FAILED tools/docs_tests/test_requirement_ledger.py::test_the_two_status_channels_agree
FAILED tools/docs_tests/test_requirement_ledger.py::test_the_unmodified_document_passes
2 failed, 111 passed in 10.51s
LEDGER SABOTAGE-B EXIT=1
```

`test_the_two_status_channels_agree` is RED and **names `DOCS-15`** in its
message. A second test, `test_the_unmodified_document_passes`, went red beyond
the plan's prediction — correctly: it asserts the real ledger passes every check
unmodified, and it had just stopped doing so.

**Reverted and re-confirmed:**

```
REVERTED byte-identical
113 passed in 10.61s
LEDGER REVERTED EXIT=0
LINTS REVERTED EXIT=0
```

---

## The coupling report

**Exact command, and the interpreter that ran it:**

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
```

```
$ .venv/bin/python -c "import sys; print(sys.executable); print(sys.version)"
/home/parkave/ccf_code/.venv/bin/python
3.12.3 (main, Jun 19 2026, 12:46:00) [GCC 13.3.0]
$ .venv/bin/python -c "import joserfc" ; echo EXIT=$?
EXIT=0
```

**Row counts:**

| | Coupling rows | Files |
| --- | --- | --- |
| Committed report at `951eb4a` | **244** | 80 |
| Committed report at this plan's start (after waves 1–3) | **264** | 81 |
| After task 2's regeneration | **264** | 81 |

The count did **not** fall — the silent-drop trap did not fire. It is 264 ≥ 244
against `951eb4a`, and 264 = 264 against the report this plan opened.

**The whole diff, and it is confined to `.planning/` under *Measured but not
assigned* exactly as the plan predicted:**

```
-| `.planning/REQUIREMENTS.md` | 99 | the phase's own planning tree — not shipped, not published |
+| `.planning/REQUIREMENTS.md` | 103 | the phase's own planning tree — not shipped, not published |
```

One line. `.planning/` is an excluded tree, so a ledger edit moves a hit count in
the *Measured but not assigned* section and cannot move a coupling row — which is
why the total held at 264 while the ledger changed.

**The page's coupling rows — 20 of them, every one owned by `17-08`:**

```
| `public/concepts/answers-no-document-contains.md` | 33 | `examples/s1-01-hello-context-product` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 63 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 69 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 77 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 80 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 95 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 121 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 125 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 141 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 145 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 152 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 167 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 172 | `examples/s1-01-hello-context-product` | `snippet-include` | live | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 197 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 205 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 210 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 269 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 300 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 305 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
| `public/concepts/answers-no-document-contains.md` | 308 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
```

```
$ grep -c "answers-no-document-contains" docs/surface/examples/RETIREMENT-COUPLINGS.md
20
$ grep "answers-no-document-contains" docs/surface/examples/RETIREMENT-COUPLINGS.md | grep -v "| 17-08 |"
(prints nothing)
```

**Do they match `22-01-SUMMARY.md`'s?** Yes, and the difference is accounted for
rather than waved past. `22-01-SUMMARY.md` recorded **13** rows (lines 33, 63,
69, 77, 80, 95, 121, 125, 141, 145, 152, 167, 172). All thirteen are present
today, unchanged in line number, path, shape, liveness and owner. The other
**seven** (197, 205, 210, 269, 300, 305, 308) are the ones `22-02-SUMMARY.md`
recorded verbatim as its task-3 delta — the contrast half's prose references to
`tests/examples/test_s1_01_output.py`. 13 + 7 = 20. **Nothing appeared that a
prior wave had not already recorded**, so this plan confirms a standing
measurement rather than discovering one.

**Five of the twenty are `snippet-include` / `live`** — lines 69, 95, 125, 152
and 172 — which is the page's five snippet includes, all against
`examples/s1-01-hello-context-product`. That is the mechanical half of `D-09`:
the coupling survives nobody remembering it.

**Client-surface rows: still none, as `22-02-SUMMARY.md` warned.** `src/ccf/client`
and the two `hw1` trees are not retiring paths, so the sweep has nothing to file
against them. This plan did not go looking for rows that cannot exist; it
measured what the sweep actually files.

### The system-interpreter trap, demonstrated on this tree

Run once with `/usr/bin/python3`, its output **discarded and never committed**:

```
$ python3 -c "import joserfc" ; echo EXIT=$?
ModuleNotFoundError: No module named 'joserfc'
EXIT=1
$ PYTHONPATH=.:src:runtime python3 tools/retirement_sweep.py --report
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
258 coupling rows across 81 files (140 rows outside the three swept trees); 1895 files scanned
SYS SWEEP EXIT=0
```

| Interpreter | `import joserfc` | Rows reported | Sweep exit |
| --- | --- | --- | --- |
| `/usr/bin/python3` | **exit 1** | **258** | **0** |
| `/home/parkave/ccf_code/.venv/bin/python` | exit 0 | **264** | 0 |

**Six rows, gone, at exit 0, with a confident count printed.** The tool cannot
tell *"there is no coupling"* from *"I could not look"* — this repository's own
check-vacuity class, inside the tool that decides what is safe to delete. It is
recorded as a finding and **not fixed here**: that is `CLNT-17` / `DOCS-17`
machinery and out of this plan's scope by ruling.

The venv report was then re-rendered and confirmed byte-identical to the
pre-demonstration venv render, and the staleness gate re-run:

```
venv report byte-identical to the pre-sabotage venv render
$ PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_retirement_sweep.py -q
33 passed in 19.61s
```

---

## Gates

| Gate | Result |
| --- | --- |
| `pytest tools/docs_tests/test_requirement_ledger.py -q` | **113 passed**, exit 0 |
| `pytest tools/docs_tests/test_retirement_sweep.py -q` | **33 passed**, exit 0 |
| `pytest tools/docs_tests -q` | **248 passed**, exit 0, no deselect |
| `PYTHONPATH=.:src:runtime .venv/bin/python -m tools.lints --all` | exit **0** |
| `git status --porcelain src/ runtime/ examples/ public/` | prints nothing |

`test_the_two_status_channels_agree`,
`test_every_verdict_token_is_in_the_vocabulary`,
`test_no_status_cell_carries_two_verdict_tokens` and
`test_every_cited_path_in_a_status_cell_resolves_as_written` all pass, and the
first and the last were each watched failing before being trusted.

---

## `D-06` — LANDED, not owed

Recorded here because this plan's own instructions were written before the
disposition was known. **`D-06` is not owed.** Plan `22-03` shipped the
per-claim symbol resolver in task 3 (`3ed8403`) with its non-vacuity floor
(`test_the_published_tree_carries_node_ids_to_resolve`) and its control
(`test_control_12_a_renamed_symbol_and_a_missing_file_are_both_refused`), taking
the module from 21 tests to 24. Its measurement, from `22-03-SUMMARY.md`: **22
node ids across the published tree, all on
`public/concepts/answers-no-document-contains.md`; 0 unresolvable paths, 0
missing symbols.** ROADMAP criterion 15's naming obligation fires only when the
stretch does not land, so there is no *owed* entry to write.

The `DOCS-15` cell records it as landed rather than silently omitting it.

---

## Deviations from Plan

### Auto-fixed

**1. [Rule 2 — never-publish hygiene, carried forward] the criterion-numbered
client-seam reading is written into the ledger cell with its criterion numbers
intact**

- **Found during:** Task 1, copying the reading.
- **Issue:** Plan 02 moved the criterion-numbered form out of the published page
  into its SUMMARY, because `public/charter.md` bars a reference to `ROADMAP.md`
  from `public/`. That constraint is about the published tree only, and it would
  be easy for a later reader to over-apply it here.
- **Fix:** `.planning/REQUIREMENTS.md` is a planning file and is never published,
  so the reading is carried in the cell **with** its criterion numbers — which is
  what this plan asked for and what makes it useful to a close verifier. No
  paraphrase: the three points and the *division of labour, not a widening*
  sentence are copied from `22-02-SUMMARY.md`'s section
  `Criterion 3 / criterion 8 — the client-seam reading`.
- **Not a widening.** Nothing criterion 3 would have required as an include
  became prose; the include form does not exist at that seam.
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Commit:** `cbe702a`

### Not fixed — nothing escalated

No Rule 4 situation arose. The plan anticipated a possible `D-06` *owed*
disposition and possible client-surface coupling rows; neither expectation
survived contact with the tree, and both are recorded above as measurements
rather than quietly dropped.

---

## Threat Flags

None. This plan ships no runtime surface, no network-reachable code, no request
handler, no persistence and no authentication path.

- `T-22-22` (the coupling report generator's silent drop) — mitigated as
  planned: the interpreter is pinned to `.venv/bin/python`, `joserfc` was
  asserted importable under it, the regeneration was refused the chance to
  reduce the row count (264 → 264), and the divergence was **demonstrated on
  this tree** rather than described.
- `T-22-23` (a ledger verdict with no evidence) — mitigated: every citation
  resolves under the citation lint and collects under pytest, six of the ten are
  the gate's controls and floors, and a bad citation was watched refusing before
  the row was trusted.
- `T-22-24` (silent row minting) — mitigated: the id set is diffed against
  `951eb4a` with the gate's own parser and is identical, 149 to 149.
- `T-22-25`, `T-22-26`, `T-22-27`, `T-22-28`, `T-22-SC` — not applicable,
  unchanged from the plan's register.

## Known Stubs

None.

## Tracking deferred to the orchestrator

Per `docs/DECISIONS.md` **D-15**, no `state.*` or `roadmap.*` SDK writer and no
requirement-writing tool was invoked. `.planning/STATE.md`,
`.planning/ROADMAP.md` and `docs/DECISIONS.md` were not modified;
`.planning/REQUIREMENTS.md` was hand-edited by exact anchored substitution.
`tools/docs_tests/test_requirement_ledger.py` and
`tools/docs_tests/test_adoption_wording.py` were not edited. The generic
execute-plan workflow's `state.advance-plan`, `state.update-progress`,
`state.record-metric`, `state.add-decision`, `state.record-session`,
`roadmap.update-plan-progress` and `requirements.mark-complete` steps were
**deliberately skipped** on that ruling; the orchestrator updates those by hand.

## Self-Check

- `.planning/REQUIREMENTS.md` — exists; `DOCS-15` appears on 6 lines, 8 times;
  both channels carry `Complete as ruled`.
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — exists; 264 rows / 81 files;
  20 rows name the new page, all owned by `17-08`.
- `.planning/phases/22-.../22-04-SUMMARY.md` — exists.
- Commits resolve in `git log`: `cbe702a`, `391680d`.
- `git status --porcelain src/ runtime/ examples/ public/` prints nothing.

---

## The second regeneration — after this SUMMARY was written

`.planning/phases/22-*` files are sweep subjects, so writing this SUMMARY
re-staled the report task 2 had just regenerated. That is precisely why
*"regenerated LAST"* has to mean *after the last write of the plan*, not *after
the last task*. Same command, same interpreter:

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
264 coupling rows across 81 files (146 rows outside the three swept trees); 1896 files scanned
```

Row count unchanged at **264 / 81**. The whole diff is one added line, in the
*Measured but not assigned* section, for this file:

```
+| `.planning/phases/22-…/22-04-SUMMARY.md` | 27 | the phase's own planning tree — not shipped, not published |
```

Nothing in the *Couplings* table moved, and nothing outside `.planning/` moved.
`test_the_committed_report_is_current` is green afterwards.
