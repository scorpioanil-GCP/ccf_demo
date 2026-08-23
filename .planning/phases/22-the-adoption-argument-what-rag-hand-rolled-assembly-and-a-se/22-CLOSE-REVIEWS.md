# Phase 22 — close-time review record

**Subject: the SHIPPED TREE.** Per `CLAUDE.md` §3.1 and `D-IMPL-178`, this phase's plans were
reviewed BEFORE execution and those decisions are already executed; a second plan review at close
reviews nothing that can still change. This file is distinct from any pre-execution plan review and
does not supersede one.

**Phase base:** `951eb4a3e2d8e072ec7f059e372545753d415a25` (Phase 21.1's close).

## 1. What was put in front of the reviewers

An 83 KB payload with the source **INLINED**, not referenced by path. Inlining is not a stylistic
choice here: on this host codex's sandbox (`bwrap`) has previously failed in a way that let it exit 0
having read nothing, and a payload of paths makes a silent sandbox failure indistinguishable from a
clean review.

Inlined in full:

| Subject | Size |
| --- | --- |
| `public/concepts/answers-no-document-contains.md` | 339 lines — the phase's deliverable |
| `tools/docs_tests/_prose.py` | the paragraph reader both gates are built on |
| `tools/docs_tests/test_adoption_wording.py` | 1052 lines — the standing wording gate |

**Named as NOT inlined, so the payload's edges are on the record:** `test_requirement_ledger.py`
(6700+ lines — the Phase 22 diff against it was described rather than inlined, as findings F1/F2 of
the briefing); `.planning/REQUIREMENTS.md`'s `DOCS-15`/`CLNT-17` rows (summarised); the eight
`examples/s1-01-hello-context-product` files the page includes from; and the five plan and five
summary documents, deliberately.

**The panel was briefed on the four already-known findings and told NOT to re-derive them**, but to
report what is ADJACENT to each. This follows the Phase 15.4 precedent, where pointing a panel at the
neighbourhood of a fixed defect surfaced a hole that predated the phase entirely.

**This payload was assembled by hand rather than by `review.md`'s gatherer**, because that gatherer
collects `*-PLAN.md` / `*-CONTEXT.md` / `*-RESEARCH.md` and asks for a *plan* review — correct before
execution, wrong at close. §3.1 permits a hand-assembled close-time payload and requires it to be
declared. It is declared here.

## 2. The panel — three reviewers, one excluded

`claude` was **excluded for independence**: it is the executing model. The panel is the set of
available external reviewers minus the executing model, and it is discharged by the reviewers having
read the right subject.

| Reviewer | Exit | Findings | Citations resolve? | Verdict |
| --- | --- | --- | --- | --- |
| codex (`codex-cli 0.137.0`, API-key auth) | 0 | 4 | **Yes** — all four name real symbols; all four confirmed by measurement | **REVIEWED** |
| cursor (`3.14.7`) | 0 | 6 | **Yes** — `sentences_claiming_passage_extraction`, `CAVEAT_ABSENCE`, `test_control_2…`, `test_control_9…` all resolve | **REVIEWED** |
| gemini | 0 | 5 | **Partly** — symbols resolve, LINE NUMBERS DRIFT | **REVIEWED, with a recorded reliability caveat** |

**Citation spot-checks, run rather than assumed.** gemini's `_prose.py:75` cited
``_CODE_SPAN_RE = re.compile(r"`[^`]*`")`` and resolves EXACTLY. Its other line numbers do not:
it placed `EXTRACTION_DENIAL` at 191-201 (actually 178-190), `CAVEAT_ABSENCE` at 220-223 (actually
225-228), `test_control_3` at 670 (actually 625) and `unresolved_node_ids` at 1000-1035 (actually
959). Symbols real, line numbers approximate. Recorded as REVIEWED rather than FAILED — it
demonstrably read the payload — with the caveat that its line citations were not usable as given.

**No reviewer is recorded FAILED this round**, so the §3.1 floor (at least one reviewer's citations
resolve) is satisfied with margin. This is worth stating because a record honestly reading
`codex FAILED, cursor FAILED, gemini FAILED` would otherwise satisfy every process check while
proving nothing — the check-vacuity class inside the gate written to prevent it.

## 3. The additive single-agent depth pass

Ran IN ADDITION to the panel, never instead (§3.1). It read the files directly, wrote probes into a
scratch tmpdir, and ran the shipped predicates rather than reasoning about them.

**The division of labour was real and is the argument for keeping both.** The panel found the
VOCABULARY holes. The depth pass found that the gate had **no jurisdiction over the prose it was
commissioned for**, and that the page **states two things that are false about tests it cites** —
neither of which any panel reviewer reached.

## 4. Findings, each verified against the tree before being recorded or acted on

Every finding below was reproduced by the orchestrator independently of the reporter, by running the
shipped predicate against an injected input. None was accepted on the reporter's word.

### Blocking — all fixed in-phase

**B1 — both AW-2 obligations report GREEN on a page whose caveat is replaced by an overclaim.**
(depth pass) Two defects compose: `CAVEAT_ABSENCE` bounded with `[^.]` excludes only `.`, so a
"caveat" can be stitched from a denial fragment plus an overclaim across a `!`; and `SENTENCE_BREAK`
merged the two into one sentence so the denial preceded the verb and the limb exempted the claim.
Measured green on positive, negative AND AW-1 with the real page's caveat swapped for
`**No shipped pipeline ships!** CCF produces passage anchors from your documents on every assembly.`
Control 3 does not save it — the mutation is in the page, so the copy carries it.
**Fixed:** `CAVEAT_ABSENCE` bounded on `[^.!?]`; control 13 observed RED once per half of the repair.

**B2 — `_prose.SENTENCE_BREAK` could not see a sentence terminated by markup.** (depth pass)
`[.!?]\s` misses `.**`, `."`, `.)`, `.]`, `.'`. Measured **88 invisible boundaries across 16 pages**,
six on the adoption page. Fails BOTH ways: a bold-closed denial exempted a following extraction claim,
and a bold-closed approach sentence merged with the next sentence's limit verb to produce an AW-1
FALSE POSITIVE — the exact case control 4(b) exists to forbid, whose fixture used plain punctuation.
**Fixed:** ``[.!?][)\]"'*`_]*\s``. Controls 4(c) and 11(e) added, both observed RED with the narrow
form restored. **See §6 — this is shared substrate and its blast radius is reported separately.**

**B3 — AW-1 had no jurisdiction over the body of any comparison subsection. The most severe finding
of the close.** (depth pass) The published tree yielded FOUR `EXTERNAL_APPROACH` candidate paragraphs
and THREE WERE HEADINGS. The page names each subject in a heading and never repeats it in the body;
AW-1 required approach noun and limit verb in the SAME SENTENCE. Every subsection body was therefore
outside candidacy — the gate was near-vacuous over exactly the prose it was commissioned for, which is
what the `DOCS-15` ledger row's non-vacuity claim rests on. Four sentences injected into the real page
and ADMITTED, three of them using the page's OWN nouns (`retrieval system` at line 332,
`document search` at line 320) which were not in the vocabulary.
**Fixed:** candidacy is now paragraph + full heading ancestor stack, judgement stays the sentence,
with three exemption conditions each watched by its own half of control 14.
**Re-verified by the orchestrator against the real page:** all four admitted sentences now CAUGHT,
including the pronoun form; `unlike`-framed re-anchoring CAUGHT; **zero offenders on the shipped
page, so no page prose needed recasting.**

**B4 — the page stated something FALSE about a test it cites.** (depth pass) It claimed the two `hw1`
trees "import nothing from `ccf` beyond that surface, asserted as a property of their **import
trees**". `reader_visible_modules` is `root.glob("*.py")`, NON-RECURSIVE by design — its own docstring
says the deployment "is correctly outside this gate" — and four of five Python files import `ccf` far
beyond the client surface. Second error in the same sentence: `REFUSED_IMPORTS[HARNESS_ROOT] =
frozenset({"ccf"})`, so the harness clients may import NOTHING from `ccf`; naming that tree as an
instance of "reaches it through `ProductClient`" inverts what it demonstrates. This is the `DCD-02`
class on a page whose own lines 18-21 promise every claim is an include or a fact about declared
artifacts. **Fixed and re-verified by the orchestrator:** the page now says reader-visible ENTRY
MODULES, states the harness root refuses the package by name, names the producer-side code as
deliberately outside the gate, and drops "import trees". "Three foreign-harness clients" is literally
three top-level modules.

**B5 — a second false attribution.** (depth pass) The 12.0% + 60.0%×30.0% aggregate was attributed to
`test_the_answer_is_a_sum_over_paths_not_a_single_hop`, which asserts only about the boundary-case
near-miss party. **Fixed and re-verified:** the aggregate now cites
`test_the_aggregate_ownership_answer_matches_the_declared_expectation`, with the boundary-case test
correctly described as holding sum-not-hop.

**B6 — the AW-2 denial limb exempted overclaims. All three panel reviewers converged independently.**
Four forms measured MISSED: a comma-`and` join, a semicolon join, an unrelated negation about pipeline
COST satisfying bare `no pipeline`, and a bare `and` join. **Fixed:** `and`/`;`/`so` handled, bare
comma deliberately not, with a fourth condition — a boundary is a TURN only if the trailing clause
carries no denial — making that safe. Controls 11(f)(g)(h), each RED under its own sabotage.
All four re-verified CAUGHT.

**B7 — `LIMIT_VERB` missed the requirement's own word.** (codex, extended by the depth pass) Bare
plural `lack` was absent while `lacks`/`lacking` were present — and `DOCS-15`'s text is literally
"states what each **lacks**". Also admitted: `will never compute`, `are not able to`, `simply do not
compute`, `stop short of`, `miss(es)`. **Fixed**, all six re-verified CAUGHT.

**B8 — the two AW-2 halves were asymmetric and the page's own spelling was the evasion.** (codex and
cursor, converged) The positive half read `Paragraph.raw` for identifier-shaped vocabulary; the
negative half read only `.text`, from which `strip_markup` deletes backtick spans. The page writes
`` `passage_anchor` `` at line 321. **Fixed:** the negative predicate scans both fields; control 17
RED on both halves; the field choice is now stated at BOTH predicates and in the module's blindness
list.

### Advisory — fixed anyway, because each was cheap and in-class

- **W5 — two LOGIC mutations shipped unwatched.** Searching the denial over the whole PARAGRAPH rather
  than the sentence turned NO test red, and accepting the caveat's two halves in DIFFERENT paragraphs
  turned NO test red — the second being the property the assertion's own title names.
  `22-03-SUMMARY.md`'s nine sabotage mutations all neuter CONSTANTS; constants-only sabotage is itself
  the class. Now covered by controls 11, 13 and the new control 18.
- **W9 — an unbacked universal claim on the page**: *"No CCF release contains that string, or any
  obligation string."* Narrowed to the byte-identity a named test actually asserts.
- **W10 — accuracy items**: a floor docstring reporting "ten candidate sentences" where the ten were
  matches across four paragraphs, three of them headings; `unresolved_node_ids` re-implementing
  `published_node_ids`'s line scan instead of calling it; two tests named for the shipped page while
  scoped tree-wide (scoped rather than renamed — renaming would strand 12 references in immutable
  `.planning/` records).
- **`fabric_diff` revision mismatch** (`test_requirement_ledger.py`): `tracked_under` reads HEAD via
  `git ls-files` while `fabric_diff` compares `base..<ceiling>`, so a member created after the ceiling
  passes the untracked-member guard and yields a necessarily-empty diff. Covered today by
  `derived_base.no_history` via `CONTROL A` and `CONTROL 13`. **Docstring sentence only** — no logic
  changed in that module and neither pin file was touched.

### Advisory — ACCEPTED and carried, not fixed. Recorded here because a finding
### not acted on must be written down rather than answered by inference.

**cursor finding 5 — `CAVEAT_ABSENCE` is sentence-bounded, so a semantically correct caveat split
across two sentences of one paragraph fails the POSITIVE assertion. ACCEPTED as a false-red
limitation; deliberately NOT fixed.** Measured after B1's repair:

```
"`D-IMPL-46` and `passage_anchor` ship in the contract. No shipped pipeline produces
 passage anchors. Documents are the gap Pattern 5 never closed."      -> carried = False
"`D-IMPL-46` and `passage_anchor` ship in the contract, and no shipped pipeline
 produces passage anchors from documents."                            -> carried = True
```

**The tension is the disposition, and it is not resolvable by widening.** The same bound that B1
tightened from `[^.]` to `[^.!?]` — in order to stop a "caveat" being stitched out of a denial
fragment plus an overclaim across a `!` — is exactly what makes a split caveat red. Loosening the
bound to span sentences re-opens B1, which is a live hole with a demonstrated exploit; keeping it
costs a false red for an editor who splits the caveat across sentences. **B1's hole is real and
exploitable; this is an inconvenience with a green-until-someone-rewrites-it profile.** Carried as
advisory: the caveat's wording is effectively frozen to a single-sentence form, and the first editor
to split it will get a red whose message should tell them why. The depth pass reached the same
conclusion independently (its W10 final bullet: "false-red direction, but it will bite the first
editor").

**cursor finding 6 — the non-vacuity floors read `_prose.published_pages()` rather than the page
under guard. PARTLY REJECTED, PARTLY ACCEPTED, and the accepted half is a real gap.**

*Rejected half — the caveat floor.* §5 correction 1 already answers it:
`test_control_3_the_unmodified_copy_passes_every_assertion` routes a copy of the ADOPTION PAGE
through `_copied_tree`, which returns `[target]` — that page alone — and asserts
`paragraphs_carrying_the_caveat` is non-empty on it. Losing the caveat from the page therefore goes
RED today, by a control rather than by the assertion. **Refuting evidence:** `_copied_tree` at
`test_adoption_wording.py:1038` returns `[target]`; control 3 at `:1126` asserts all three predicates
against it.

*Accepted half, and it is a genuine gap.* Control 3 proves the page is CLEAN, not that it is
POPULATED. **Measured by the orchestrator:** with every approach noun on the adoption page replaced
by `WIDGET`, `sentences_asserting_a_capability_limit` returns clean — **vacuously** clean — and no
test in the tree goes red. So **ROADMAP criterion 2 — "names all three alternatives and no fourth" —
is not held by any standing gate.** It is true today (verified in Wave 2 and re-verified at this
close), and it is held by the `DOCS-15` ledger row's prose and by this review, not by mechanism.
That is precisely the distinction this phase exists to draw, arriving one level out from the gate it
built. **Not fixed in-phase**: a criterion-2 floor is a NEW obligation beyond the two this phase
commissioned (`22-CONTEXT.md` D-04, ROADMAP criterion 5), and adding a third obligation at a close
is scope expansion after execution — the accretion pattern `D-IMPL-146` names. **Carried to Dave as a
live choice**, with the note that the fix is small: a floor asserting the adoption page names each of
the three approach families, plus its sabotage.

### REJECTED — recorded as rejected, with the evidence that refutes them

**REJECTED — gemini finding 5, "D-06 resolver instability".** It argued that because F4 reported a
six-row discrepancy between Python environments, `unresolved_node_ids` "may silently skip verification
of node IDs" in an environment where `repo_index` is truncated. **Refuting evidence:** F4 is about
`tools/retirement_sweep.py` run under `/usr/bin/python3` versus the venv — a different module, a
different index, and a different failure. Nothing was offered connecting the sweep's row count to
`repo_index`, and the finding's own confidence line concedes it is "extrapolated from F4". An
extrapolation from an unrelated module is not a finding. The depth pass independently measured the
resolver: 22 node ids, all 22 resolving, and `resolve_cited` requires a genuine path suffix so a
wrong-directory citation does not basename-resolve.

**REJECTED AS WRITTEN — gemini finding 3's stated example.** It claimed
`"Is there no shipped pipeline? We produce passage anchors. Check these documents."` would produce a
positive `CAVEAT_ABSENCE` match. **Refuting evidence:** run against the shipped predicate, it returns
**no match** — the `.` between "passage anchors" and "documents" blocks `[^.]{0,40}` exactly as
designed. **The underlying mechanism is nonetheless real and was confirmed by a corrected probe**
built by the orchestrator (`[^.]` excludes `.` but not `?`), and it is fixed under B1. Recorded in
both halves rather than as a flat accept or a flat reject, because the reviewer identified a true
mechanism through a false example and both facts matter to how this reviewer's output is read.

## 5. Corrections to the orchestrator's own briefing — recorded because they went the right way

The briefing given to the depth pass and to the repair agent was wrong in five places, and each was
caught and reported rather than executed:

1. **P4 overstated the exposure.** The positive caveat assertion is unanchored, but
   `test_control_3_the_unmodified_copy_passes_every_assertion` copies the adoption page and requires
   `paragraphs_carrying_the_caveat` non-empty on it — so losing the caveat from the page DOES go red
   today. Message quality and future drift, not an open hole.
2. **P5's blast radius is smaller than stated.** `_CODE_SPAN_RE` leaking double-backtick content into
   `.text` ADDS matches, so it can only produce false positives. The asymmetry that costs coverage is
   B8's, and it runs the other way.
3. **The prescribed B3 fix would have produced a false positive on the page's most honest sentence.**
   Paragraph+heading carry plus `retrieval system` condemns line 331 — *"the one place on this page
   where a retrieval system does something this deployment does not do"* — which asserts a limit of
   **CCF**, not of the approach. The brief said to recast the prose; the repair judged the GATE wrong
   instead and added a nearest-preceding-subject rule, modelled on AW-2's existing pivot condition.
   The same naive widening would also have condemned `D-02`'s required recast *"The question itself
   has no way to be answered…"*, which control 4(b) has held since the gate shipped.
4. **Bare `never` in `LIMIT_VERB` would have made the two obligations contradict each other.** AW-2
   REQUIRES the caveat *"Pattern 5, unstructured ingestion, was never built"*, and that paragraph sits
   under `## Where a document search is stronger` — so with heading carry, AW-1 would refuse the
   sentence AW-2 demands. `never` is admitted only behind a modal.
5. **Measurement counts were wrong in the briefing**: "88 invisible boundaries across 10 pages" is 88
   across **16**; "four candidate paragraphs, three headings" was right for the old vocabulary and is
   6 and 4 with the page's own nouns added, 17 with the carry.

**And the repair caught its own defect of this phase's class.** Its first draft of control 16 shipped
VACUOUS: built with `_copied_tree`, the injected paragraph inherited candidacy from the page's last
heading, so two of three vocabulary sabotages passed green. The sabotage found it. The FIXTURE was
changed rather than the assertion. It also removed a condition it had just written — a production-verb
lookahead redundant with the `no pipeline` hyphen guard, where sabotaging either left the suite green
because the other still refused. Two conditions no control can tell apart are one condition and one
piece of decoration.

## 6. Shared substrate — surfaced separately rather than absorbed

`_prose.SENTENCE_BREAK` is used by three gates. `test_gate_two_wording.py` calls `sentence_at`, so its
sentence scoping **genuinely changed** with B2's fix: boundaries that were previously invisible now
split. It is green (10 passed) and no assertion in it was modified, but a Phase 22 close should not
quietly re-scope another phase's gate, so it is named here as its own item.

`tools/lints/citations.py::_SENTENCE_BREAK` **deliberately keeps the narrow `[.!?]\s` form.** The
reason is documented at `_prose.SENTENCE_BREAK`: that lint's window is a two-line source slice rather
than a joined paragraph, and a mis-split there truncates the window, which can only cost a match and
never invent one. Widening it is a separate change against a separate consumer and was not made.
Two copies of one rule now differ **on purpose and on the record**, which is the disposition this
project prefers to a silent divergence.

## 7. An orchestrator finding, made during re-verification

Condition (ii) of the repaired AW-1 reads POSITION, not REFERENCE. Injected under a heading naming an
approach and **EXEMPTED**: *"A vector store is popular here at CCF, and this deployment aside it
cannot answer the question."* — where `it` refers to the vector store. Three adjacent shapes were
measured CAUGHT (a smuggled CCF anchor with no contrastive word; a CCF anchor followed by an approach
anchor; a bare pronoun after a CCF mention), and condition (iii) closes the contrastive-frame form.
What remains open is a pronoun whose referent is not its nearest anchor with no framing word marking
the turn. Resolving that needs reference resolution, which a regex gate does not have. **Added to the
module's stated blindness list as item 3** rather than left implied closed (`74f1f3a`).

## 8. Carried forward — for Dave's ruling, not absorbed

1. **`examples/s1-01-hello-context-product/artifacts/expected.yaml:191-193` carries the SAME unbacked
   universal that W9 removed from the page** — *"no CCF release contains this string, or any
   obligation string"*. It was outside the repair's stated scope (`public/` only) and it is an example
   input several tests read. Same `DCD-02` class. **Not fixed; needs a ruling.**
2. **AW-1 condition (ii)'s pronoun-reference residual** (§7) — documented, not closed.
3. **`D-IMPL-188` residual 2** — nothing asserts a bounded assertion actually READS the pin. Deleting
   the ceiling argument from the `tests/` assertion leaves the module green; deleting it from the
   fence assertion is caught, but only because the tree has since moved.
4. **`D-IMPL-188` residual 3** — nothing stops the ceiling being ADVANCED by a future executor who
   hits a red fence. Dave asked for this to come to the gate as a policy question about who may move
   a pin.
5. **ROADMAP criterion 2 is not held by a standing gate.** The adoption page names all three
   approaches today, but nothing asserts it must. Measured: with every approach noun replaced by
   `WIDGET`, AW-1 returns vacuously clean and no test goes red. Adding a criterion-2 floor is a THIRD
   obligation beyond the two this phase commissioned, so it is a ruling rather than a close fix. The
   fix is small if you want it. (cursor finding 6, accepted half — see §4.)
6. **`CAVEAT_ABSENCE` freezes the caveat to a single-sentence form.** Splitting it across two
   sentences of one paragraph turns the positive assertion red. Loosening the bound re-opens B1, a
   hole with a demonstrated exploit, so the false red is the cheaper side. (cursor finding 5 — §4.)
7. **The two gates divide the citation work** — the ledger gate proves a cited PATH exists, the
   citation lint proves the SYMBOL exists. A row checked by only one is half checked. Both run in
   `ci-core` today, so nothing is exposed.

## 9. Nothing known is being carried into the next phase without a ruling

Every blocking finding is fixed in-phase. The five items in §8 are named for a ruling at this gate
rather than inherited silently.

## 10. Gate state after the repair

| Leg | Before close | After close |
| --- | --- | --- |
| `tools/docs_tests` + `tools/publish_scan_tests` | 291 passed | **298 passed, 0 failed** |
| `test_adoption_wording.py` | 24 tests | **31 tests** |
| `make gate-tools` | — | exit 0 |
| `make lint` | — | exit 0 |
| `make docs-strict` | — | exit 0 |
| `RETIREMENT-COUPLINGS.md` | 264 / 81 | **267 / 81**, regenerated in the venv |

`src/`, `runtime/` and `examples/` remain diff-empty for the whole phase.

---

## Close-gate verification

Recorded by plan `22-06` task 1 on 2026-08-23. This section does not restate the findings. It
records whether the process that produced them conformed to `CLAUDE.md` §3.1, and it was produced by
measuring rather than by reading: reviewer citations were resolved against the panel-time tree
`219ac43` (plan 05's last commit, the tree the panel actually saw), and the repaired predicates were
run against injected input rather than reasoned about.

Check 1: PASS — `22-CLOSE-REVIEWS.md` exists at 284 lines and is its own file. The phase directory holds no pre-execution plan review it could have displaced; its only companions are the three raw reviewer transcripts (`review-codex.txt`, `review-cursor.txt`, `review-gemini.txt`), committed beside it so the record can be checked against its sources — which is how checks 4 through 7 below were run. Its shape follows the conforming `21.1-CLOSE-REVIEWS.md` precedent: a roster carrying REVIEWED/FAILED with evidence, blocking, advisory, REJECTED-with-refutation, and a separate additive single-agent section.
Check 2: PASS — the close-time subject was the SHIPPED tree and the subject list is verifiable. At `219ac43`, `public/concepts/answers-no-document-contains.md` is exactly 339 lines and `tools/docs_tests/test_adoption_wording.py` is exactly 1052 lines, the two figures the record's table states; `tools/docs_tests/_prose.py` is 262 lines. The declared phase base `951eb4a` resolves to Phase 21.1's close merge. No `*-PLAN.md` appears anywhere in the subject list, and the exclusions are named rather than left silent: `test_requirement_ledger.py` (described, not inlined), the `DOCS-15`/`CLNT-17` ledger rows (summarised), the eight `s1-01` files the page includes from, and the five plan and five summary documents, deliberately.
Check 3: PASS — the source was INLINED and the hand-assembly is declared. The three inlined subjects total 78,027 bytes at `219ac43`, consistent with the declared 83 KB payload once the briefing prose is counted, so the record's size claim is not decorative. §3.1 places two conditions on a hand-assembled close-time payload — say so plainly, and name what was left out — and both are met: the reason is stated (`review.md`'s gatherer collects plan documents and asks for a plan review, which is the wrong question at close) and the omissions are enumerated.
Check 4: PASS — every reviewer is accounted for, at least two citations per reviewer were resolved against the tree by this verification rather than taken from the record's table, and the not-every-reviewer-FAILED floor holds with margin at three of three. codex: `CONTRASTIVE_PIVOT` resolves at line 199 and `sentences_claiming_passage_extraction` at 261, and its factual claim that `LIMIT_VERB` carried `lacks` and `lacking` but not bare `lack` is confirmed at lines 115-127 — REVIEWED. cursor: `test_control_2_an_injected_extraction_claim_is_refused` at 603, `test_control_9_a_backticked_identifier_spelling_is_still_seen` at 772, `test_the_denial_limb_is_load_bearing_on_the_shipped_page` at 444, and the `CAVEAT_ABSENCE` bounds it quoted verbatim (`[^.]{0,80}` / `[^.]{0,40}`) at 225-228 — REVIEWED. gemini: `_prose.py:75` is `_CODE_SPAN_RE = re.compile(r"`[^`]*`")`, exact in both line and content, and its symbols `EXTRACTION_DENIAL`, `CAVEAT_ABSENCE`, `unresolved_node_ids`, `test_control_3` and `paragraphs` all resolve, while every line number the record reports as drifting drifts by the stated amount (178-190 not 191-201; 225-228 not 220-223; 625 not 670; 959 not 1000-1035) — REVIEWED with the record's reliability caveat rather than FAILED, which is the right call: a reviewer that reproduces a regex body at its exact line demonstrably read the payload, and unusable line citations are a usability defect, not an absence of review.
Check 5: PASS — the single-agent depth pass ran IN ADDITION, and this was verified by disjointness rather than by assertion. `reader_visible_modules`, `REFUSED_IMPORTS`, `test_the_answer_is_a_sum_over_paths_not_a_single_hop` and even the bare word `heading` appear ZERO times across all three reviewer transcripts, and B3, B4 and B5 — the three most severe blockers of the close — are built on exactly those symbols. The panel could not have produced them, so the record's division-of-labour claim is measured, not claimed.
Check 6: PASS — findings were verified against the tree before being recorded, and both rejections carry refuting evidence this verification reproduced independently. Run against the panel-time `CAVEAT_ABSENCE`, gemini finding 3's stated example returns NO match, exactly as the rejection says, while corrected probes crossing `!` and `?` both DO match — so the record's unusual "true mechanism through a false example, recorded in both halves" disposition is a measurement rather than a hedge. gemini finding 5's rejection stands on its face: it extrapolates a resolver defect from a row-count discrepancy in a different module, and its own confidence line concedes the extrapolation. Separately, the five previously-missed forms were re-run against the REPAIRED shipped predicates and all five are now CAUGHT (bare plural `lack`; the semicolon join; the `and` join; the unrelated `no pipeline` negation; the backticked `passage_anchor`), and the stitched pseudo-caveat is REFUSED — so the fixes are real and not merely reported.
Check 7: PASS — triage is now present and complete. The STOP this check raised on its first run was correct and is preserved above in this file's history rather than overwritten silently: two of fifteen panel findings (cursor 5 and cursor 6) carried no recorded disposition, and §3.1 requires a finding not acted on to be written down rather than answered by inference from an adjacent entry. Both are now dispositioned in §4 under their own heading, each with the measurement behind it: cursor 5 ACCEPTED as a false-red limitation deliberately not fixed, because the bound B1 tightened to close a demonstrated exploit is the same bound that makes a split caveat red; cursor 6 PARTLY REJECTED with refuting evidence (`_copied_tree:1038` returns `[target]`, control 3 at `:1126` asserts the caveat on the adoption page alone, so the caveat floor IS anchored) and PARTLY ACCEPTED as a genuine gap — ROADMAP criterion 2 is held by prose and by this review, not by mechanism, measured by replacing every approach noun on the page with `WIDGET` and observing AW-1 return vacuously clean with no test red. Both accepted items are carried to Dave in §8 as items 5 and 6 rather than absorbed. All fifteen findings are now classified; every blocking finding is fixed in-phase and was re-verified by measurement at this close.
Check 8: PASS — §8 names five items for a ruling and §9 states in terms that nothing known is being carried into the next phase without one. Item 1 was spot-verified and is real: `examples/s1-01-hello-context-product/artifacts/expected.yaml` lines 191-193 do carry "no CCF release contains this string, or any obligation string" — the same unbacked universal W9 removed from the page, which no longer carries it — and it is correctly named unfixed rather than quietly absorbed. Item 2 is on the record in the tree at `74f1f3a` as the module's third stated blindness. This verification adds one item to that list for Dave: the un-triaged cursor findings named under check 7, which should be dispositioned in §4 before the phase closes rather than inherited.

**Result: seven PASS, one STOP.** The gate is NOT satisfied and the phase does not close on this
record as it stands. Nothing was logged, amended or merged. Under §3.1 the remedy belongs to step 2,
triage, which is not this plan's to perform: the two cursor findings need a recorded classification —
accepted, or rejected with the evidence that refutes them — after which this section is re-run.

What this verification confirmed about the substance, so the STOP is read for what it is: the panel
genuinely ran on the shipped tree with three reviewers resolving, the depth pass genuinely ran in
addition and found what the panel could not, every blocking fix was re-measured here rather than
taken on the record's word, `src/`, `runtime/` and `examples/` are diff-empty across `951eb4a..HEAD`,
the docs gate suite is 298 passed with 31 tests in the adoption module, `test_gate_two_wording.py` is
10 passed after B2 re-scoped its substrate, and `RETIREMENT-COUPLINGS.md` stands at 267 rows across
81 files. The defect is in the record's bookkeeping of two findings, not in the work.

REJECTED: none by this verification — the two rejections already in §4 were reproduced and stand.
