---
phase: 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se
plan: 02
subsystem: published documentation surface
tags: [DOCS-15, concepts-page, question-facts, passage-anchor-caveat, node-id-citation]
status: complete
requires:
  - public/concepts/answers-no-document-contains.md (plan 01's spine — extended, not rewritten)
  - src/ccf/client (unmodified; cited only, by resolving node ids)
  - examples/s1-01-hello-context-product (unmodified; cited only)
  - examples/hw1-companies-over-revenue, examples/hw1-harness-clients (unmodified; prose-referenced only)
provides:
  - "public/concepts/answers-no-document-contains.md: the three contrast sections, the narrowed staleness claim, the passage-anchor caveat"
  - the caveat paragraph plan 03's control-7 fixture is built against
affects:
  - docs/surface/examples/RETIREMENT-COUPLINGS.md (7 new 17-08-owned prose rows in task 3; more after this SUMMARY)
  - .planning/phases/22-*/22-03-PLAN.md (the gate reads the caveat this plan shipped)
  - .planning/phases/22-*/22-04-PLAN.md (copies the client-seam reading into the DOCS-15 ledger cell)
  - .planning/phases/22-*/22-05-PLAN.md (copies the client-seam reading into the phase record)
tech-stack:
  added: []
  patterns: [question-fact-recast, prose-node-id-citation, denial-form-caveat]
key-files:
  created:
    - .planning/phases/22-.../22-02-SUMMARY.md
  modified:
    - public/concepts/answers-no-document-contains.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "debt-profile.yaml excluded from the page on a measurement: 15 pub01-whitepaper-shingle findings against 0 on expected.yaml"
  - "The line-slice workaround rejected rather than merely not chosen — an out-of-range slice renders empty at exit 0"
  - "The page states its citation reading in reader-facing terms; the criterion-numbered version lives in this SUMMARY (never-publish hygiene)"
  - "Zero D-03 paired contrasts — every contrast recast as a question-fact"
metrics:
  duration: ~70 min
  completed: 2026-08-23
  tasks: 3
  commits: 3 (+1 SUMMARY/report follow-up)
---

# Phase 22 Plan 02: The contrast half — Summary

Three contrast sections, a staleness claim narrowed to exactly what
`tests/examples/test_s1_01_output.py` asserts, and the passage-anchor honesty
caveat — written so that **not one sentence of the page asserts what any
external approach cannot do**, and so that the caveat's word order survives the
three-condition denial limb plan 03 ships.

The page is now **339 lines**. It carries **five** `--8<--` includes, the same
five plan 01 shipped: this plan added none.

---

## What shipped

| Task | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | Name the three approaches, recast every contrast as a question-fact | `97b50b4` | `public/concepts/answers-no-document-contains.md` |
| 2 | The staleness claim, narrowed to what the tests actually assert | `dc260b1` | `public/concepts/answers-no-document-contains.md` |
| 3 | The passage-anchor caveat, the page audit, the coupling report | `c04416f` | `public/concepts/answers-no-document-contains.md`, `docs/surface/examples/RETIREMENT-COUPLINGS.md` |

Sections appended, in order:

- `## The three approaches this is usually compared against`, with
  `### RAG over a vector store`, `### Hand-rolled context assembly`,
  `### A semantic layer plus prompt templates`
- `## What this deployment measures about its own answer`
- `## Where a document search is stronger, and this is not`

---

## The capability-limit predicate, verbatim, and its literal output

The predicate is paragraph-for-candidacy, sentence-for-judgement, run through
`tools/docs_tests/_prose` so it is the same scoping plan 03's gate will use.
Both vocabularies are case-insensitive:

```python
APPROACH = re.compile(
    r"RAG|vector store|vector database|semantic layer|prompt template|"
    r"hand-rolled|hand rolled|chunked documents|embedding search",
    re.IGNORECASE,
)
LIMIT = re.compile(
    r"cannot|can't|can not|unable to|lacks|lacking|fails to|fail to|has no|"
    r"have no|does not support|doesn't support|do not support|incapable of|"
    r"no way to|falls short",
    re.IGNORECASE,
)

for para in _prose.page_paragraphs(page):
    if para.fenced:
        continue
    for m in APPROACH.finditer(para.text):
        sent = _prose.sentence_at(para.text, m.start())
        candidates += 1
        if LIMIT.search(sent):
            offenders.append(f"{page}:{para.lineno} — {sent.strip()}")
```

Run after task 1, again after task 2, and again on the finished page. Identical
output all three times:

```
approach-token matches (candidate sentences): 10
offenders: 0
```

**Ten candidates, zero offenders.** The candidate count is the non-vacuity
half: the check is reading sentences that genuinely name an external approach,
not passing over an empty set.

**`RAG` is matched case-insensitively and unbounded**, which means it also
matches inside `storage`, `paragraph`, `coverage`, `leverage` and `average`.
None of those five words appears anywhere on the page — measured,
`grep -oiE "storage|paragraph|coverage|leverage|average" ` returns nothing — so
the unbounded reading and the word-bounded reading plan 03 will ship cannot
disagree on this page.

---

## Criterion 3 / criterion 8 — the client-seam reading

*(Verbatim section for plan 04's `DOCS-15` status cell and plan 05's phase
record. Copy it whole; do not paraphrase it.)*

- These citations are prose `path::symbol` node ids rather than snippet
  includes because **no file in `src/` carries a snippet section marker at
  all** — `grep -rn -- "--8<--" src/` returns 0 — and the `hw1` trees carry
  none either, so an include against the client seam is not a form that exists
  to be chosen.
- The citations are nonetheless CHECKED, by `cite03-node-id` in the citation
  lint, which is exactly what ROADMAP criterion 8 requires of the client-seam
  contrast.
- Criterion 3's include requirement is discharged by the five includes carrying
  the page's `s1-01` demonstration, which is where the page's code-backed
  claims about the fabric live.

This is a **division of labour between criteria 3 and 8, not a widening of
criterion 3.** Criterion 3 governs the fabric claims, and those ride five
literal includes from a CI-gated source. Criterion 8 governs the client-seam
contrast, and it asks for citations that resolve under the lint — which these
do, watched refusing a bad symbol below. Nothing that criterion 3 would have
required as an include has been downgraded to prose; the form was never
available at that seam.

**Both greps re-measured at this plan's HEAD:**

```
$ grep -rn -- "--8<--" src/ ; echo "exit=$?"
exit=1
$ grep -rn -- "--8<--" examples/hw1-companies-over-revenue examples/hw1-harness-clients ; echo "exit=$?"
exit=1
```

**How the page states it, and why the wording differs from the above.** The
page carries this reading in its own voice, in the `### Hand-rolled context
assembly` subsection under the bolded lead *"Why the citations in this
subsection are prose and not includes, stated rather than left to be
inferred."* It states all three points — no snippet marker under `src/` or in
either `hw1` tree, so the include form does not exist to be chosen; the node
ids are resolved by the citation lint's `cite03-node-id` rule; the include
obligation is discharged by the five `s1-01` includes. It does **not** carry
the words "criterion 3" or "criterion 8". `public/charter.md`'s never-publish
rule bars any reference to `ROADMAP.md` from the published tree, and ROADMAP
criterion numbers are meaningless to the page's reader; the numbered form lives
here instead. Recorded as a deviation below.

---

## Every node id written on the page, and the command that proved each collects

Command, once per name:

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest "<node id>" --collect-only -q
```

Literal output, all ten:

```
exit=0 | 2 tests collected in 0.09s | tests/examples/test_client_example_purity.py::test_the_client_example_imports_only_the_client_and_stdlib
exit=0 | 1 test collected in 0.45s  | tests/examples/test_hw1_two_transports.py::test_both_documented_transports_return_the_same_answer
exit=0 | 1 test collected in 0.39s  | tests/examples/test_hw1_two_transports.py::test_the_two_documented_transports_are_actually_different
exit=0 | 1 test collected in 0.18s  | tests/examples/test_s1_01_output.py::test_a_different_company_gets_a_different_answer
exit=0 | 1 test collected in 0.19s  | tests/examples/test_s1_01_output.py::test_every_declared_absence_really_is_absent
exit=0 | 1 test collected in 0.22s  | tests/examples/test_s1_01_output.py::test_the_aggregate_ownership_answer_matches_the_declared_expectation
exit=0 | 1 test collected in 0.23s  | tests/examples/test_s1_01_output.py::test_the_answer_is_a_sum_over_paths_not_a_single_hop
exit=0 | 1 test collected in 0.23s  | tests/examples/test_s1_01_output.py::test_the_obligation_in_force_is_pinned_into_the_replay_record
exit=0 | 1 test collected in 0.24s  | tests/examples/test_s1_01_output.py::test_the_product_answers_the_question_the_caller_asked
exit=0 | 1 test collected in 0.23s  | tests/examples/test_s1_01_output.py::test_the_same_company_at_a_later_instant_gets_a_different_answer
```

The purity test collects **2** rather than 1 because it is parameterised over
the client example programs; every other node id collects exactly 1. Three of
the ten (`test_every_declared_absence_really_is_absent`,
`test_the_aggregate_ownership_answer_matches_the_declared_expectation`,
`test_the_obligation_in_force_is_pinned_into_the_replay_record`) were already on
the page from plan 01 and are re-verified here rather than assumed.

Non-test node ids written on the page — all five checked by `cite03-node-id`,
all resolving:

```
src/ccf/client/binding.py::resolve_binding
src/ccf/client/client.py::ProductClient
src/ccf/client/errors.py::TransportError
src/ccf/client/result.py::Result
src/ccf/contracts/claims.py::PassageAnchor
```

`src/ccf/contracts/claims.py::PassageAnchor` is in the caveat paragraph and is
the one node id the plan did not name; it was added so the *"the contract
ships"* half of the caveat is checkable rather than asserted. `passage_anchor`
is a field on `LineageEntry` at `src/ccf/contracts/claims.py`, typed
`PassageAnchor | None`.

---

## The `cite03-node-id` sabotage, run and reverted

Mutation: `src/ccf/client/client.py::ProductClient` →
`src/ccf/client/client.py::ProductClientX` on the page. Then, in the venv,
`PYTHONPATH=.:src:runtime .venv/bin/python -m tools.lints --all`:

```
1 CCF invariant violation(s). Fix the code, or — for CINV-01 only — add a reviewed entry to tools/lints/allowlist.yaml.
public/concepts/answers-no-document-contains.md:224 cite03-node-id cites src/ccf/client/client.py::ProductClientX, but src/ccf/client/client.py defines no 'ProductClientX' — the symbol was renamed or removed; re-resolve it before citing it
SABOTAGE EXIT=1
```

Reverted from a byte-copy; `git diff --stat` showed only the plan's own
insertions; re-run:

```
REVERTED EXIT=0
```

Criterion 8's gating is therefore **live for this page**, watched rather than
assumed.

---

## The two `publish_scan` measurements that decided the include

Run in the venv against `tools.publish_scan.scan_text` with
`whitepaper_shingles()`:

```
expected.yaml     0
ubo-question.yaml 0
debt-profile.yaml 15
```

`debt-profile.yaml` is therefore **not** included, in whole or by line slice.
Its header quotes the whitepaper verbatim at lines 5-6 and carries
`docs/CCF_Whitepaper_1-2.md:2696` at line 7 — confirmed by reading the file.
`make docs-strict`'s fourth step scans the **rendered** tree with HTML stripped
before normalization and with no allowlist and no `--exit-zero`, so an included
`<pre><code>` block is scanned as running words. `examples/` is fenced, so the
file cannot be cleaned.

**The line-slice workaround was evaluated and rejected, not overlooked.** A
sliced include renders clean, but an out-of-range slice renders an EMPTY code
block at exit 0: `check_paths: true` guards a missing file and a missing named
section, and guards a line range not at all. Shipping a silently-blankable
include on the one page whose purpose is modelling honest citation is not a
trade this phase makes. **Do not reinstate it.**

**What carries the claim instead.** Plan 01's whole-file `expected.yaml`
include, which DECLARES the band crossing itself. Rendered-site evidence:

```
$ grep -c "forced_llm" site/concepts/answers-no-document-contains/index.html
3
```

Three occurrences. **Two of them arrive from the include** (`expected.yaml`
carries `forced_llm` twice — `debt_signal_third_question: "forced_llm"` and the
comment above the obligations); **one** from the page's prose. So the evidence
for criterion 11 reaches the rendered page from a CI-gated source, not only from
prose.

---

## The staleness claim's own honesty check

The literal figures appear nowhere:

```
$ grep -n "0\.035\|0\.221" public/concepts/answers-no-document-contains.md ; echo exit=$?
exit=1
$ grep -n "0\.035\|0\.221" examples/s1-01-hello-context-product/artifacts/expected.yaml \
    examples/s1-01-hello-context-product/artifacts/ubo-question.yaml \
    examples/s1-01-hello-context-product/spine.py ; echo exit=$?
exit=1
```

**The first grep is SOURCE-scoped and that is now sufficient rather than merely
convenient.** It reads the markdown, not the rendered page, so it would be blind
to a figure arriving through an include. With `debt-profile.yaml` dropped, the
second grep proves no source the page renders contains either token. Do not let
a later reader mistake the first for a rendered-page assertion.

No `examples/s1-02-*` tree was created:

```
$ grep -rn "s1-02" public/ ; echo exit=$?
exit=1
$ ls examples/ | grep s1-02 ; echo exit=$?
exit=1
```

---

## Caveat paragraph, as shipped

*(Plan 03's control-7 fixture source. If the page and this section ever
disagree, the page is the truth and this section is stale — re-measure.)*

The exact shipped text, `public/concepts/answers-no-document-contains.md:320-328`:

```markdown
The lineage entry a Context Product carries has a `passage_anchor` field, and the
contract behind it ships: `D-IMPL-46` rules the `PassageCitationProvider`
Protocol, and `src/ccf/contracts/claims.py::PassageAnchor` is the typed anchor
that field takes (whitepaper §7.10.3). Pattern 5, unstructured ingestion, was
never built, so no shipped pipeline produces passage anchors from documents.
What the lineage on this page's answer anchors is the source identity and the
observation envelope each ownership claim arrived on, accumulated by set-union
across corroborating sources — which is what this question needs, and it is a
different thing.
```

### The paragraph reader, run both ways

`_prose.page_paragraphs` over the shipped page. **Exactly one** paragraph
carries both halves:

```
=== positive: paragraphs carrying BOTH halves ===
  public/concepts/answers-no-document-contains.md:321
  count = 1

=== .raw vs .text for the identifier half ===
  'D-IMPL-46': .raw=True .text=False
  'passage_anchor': .raw=True .text=False
  CAVEAT_ABSENCE on .text = True
  CAVEAT_ABSENCE on .raw  = True
```

Both identifier tokens are backticked, so `.raw` sees them and `strip_markup`
deletes them from `.text`. **That contrast is the whole reason plan 03's
`CAVEAT_CONTRACT` must match `.raw`**; matched against `.text` it would find
nothing on this correct page. The absence half is ordinary un-backticked prose,
so it survives into `.text`, which is where plan 03 matches `CAVEAT_ABSENCE`.

### The three word-order measurements

`_prose.sentence_at` over the paragraph's `.text`, at the offset of the absence
half. The sentence, **verbatim as `sentence_at` returned it** — which is what
proves where the sentence boundary actually falls:

```
'Pattern 5, unstructured ingestion, was never built, so no shipped pipeline produces passage anchors from documents. '
```

```
EXTRACTION_DENIAL offsets: [(35, 'was never built'), (55, 'no shipped pipeline')]
EXTRACTION_VERB   offsets: [(75, 'produces')]
CONTRASTIVE_PIVOT offsets: []
denial offset 35 < every extraction-verb offset [75]: True
pivots between denial and a later extraction verb: []
PASSAGE_ANCHOR in sentence: True
DOCUMENT_SOURCE in sentence: True
```

1. **Vocabulary** — two `EXTRACTION_DENIAL` matches, the earliest at 35.
2. **Ordering** — the sentence contains exactly **one** extraction verb,
   `produces` at 75. The full verb vocabulary was swept (`extract`, `extracts`,
   `extracted`, `extracting`, `derive`, `derives`, `pull`, `pulls`, `lift`,
   `lifts`, `produce`, `produces`, `generate`, `generates`); 35 < 75 holds
   against **every** one of them, not merely against the first noticed.
3. **Pivot** — zero `CONTRASTIVE_PIVOT` occurrences in the sentence, so nothing
   can stand between the denial and a later extraction verb. The caveat's
   connective is `so`, which is not a pivot: it **denies and then explains**
   rather than denying and then turning.

The preceding sentence ends `(whitepaper §7.10.3).` followed by a space, which
is what makes `SENTENCE_BREAK` (`[.!?]\s`) cut there. No extraction verb of any
kind stands ahead of the denial inside the caveat sentence.

---

## The page audit — all eight checks, literal output

**1. Capability-limit sentence check (whole file).**

```
approach-token matches (candidate sentences): 10
offenders: 0
```

**2. Extraction-claim check, run WITH plan 03's three-condition denial limb.**

```
=== AW-2 negative predicate, WITH the three-condition denial limb ===
  exempted: 1
    public/concepts/answers-no-document-contains.md:321 — Pattern 5, unstructured ingestion, was never built, so no shipped pipeline produces passage anchors from documents.
  offenders: 0

=== the same predicate WITHOUT the limb (the trap) ===
  offenders: 1
    public/concepts/answers-no-document-contains.md:321 — Pattern 5, unstructured ingestion, was never built, so no shipped pipeline produces passage anchors from documents.
```

**Exactly one exempted sentence — the caveat itself — and zero offenders.** Run
without the limb, the same predicate reports the caveat as an offender: that is
the trap this wording invites and the reason the limb exists. The exempted count
is 1 rather than 0, so the caveat is on the page and is shaped as instructed.

**3. Line citations.**

```
$ grep -nE "[A-Za-z0-9_]+\.py:[0-9]+" public/concepts/answers-no-document-contains.md ; echo exit=$?
exit=1
```

**4. Condemned example trees.**

```
$ grep -nE "examples/0[0-8]|examples/external/00-hello-context" public/concepts/answers-no-document-contains.md ; echo exit=$?
exit=1
```

**5. Never-publish names.**

```
$ grep -nE "DECISIONS\.md|SPEC_INVENTORY\.md|DESIGN\.md|FEASIBILITY\.md|ROADMAP\.md|CCF_Whitepaper" public/concepts/answers-no-document-contains.md ; echo exit=$?
exit=1
$ grep -rn "DECISIONS.md" public/concepts/answers-no-document-contains.md ; echo exit=$?
exit=1
```

**6. Every include directive resolves and every named marker exists** — proven
by the build, not by inspection:

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py --pre-build
PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py docs/schemas
PYTHONPATH=.:src:runtime .venv/bin/python -m mkdocs build --strict
INFO    -  Documentation built in 3.73 seconds
PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py site
DOCS-STRICT EXIT=0
```

**7. D-03 paired contrasts on the page: ZERO.** Every contrast in all three
subsections is a fact about the UBO question and its declared artifacts, or a
statement about CCF mechanism carrying a citation. No contrast needed the
fallback, so the page has not made pairing its house style — which is what D-03
guards against.

**8. Include inventory.**

```
$ grep -c -- '--8<--' public/concepts/answers-no-document-contains.md
5
$ grep -c 'debt-profile' public/concepts/answers-no-document-contains.md
0
$ grep -c "forced_llm" site/concepts/answers-no-document-contains/index.html
3
```

Five directives, unchanged from plan 01; zero naming `debt-profile.yaml`; three
rendered `forced_llm` occurrences, two of them from the `expected.yaml` include.

**Plus the published-tree extraction-phrase ban, across the whole tree:**

```
$ grep -rniE "extracts passage anchors|passage anchors from your documents|extract(s|ed|ing)? passage anchors" public/ ; echo exit=$?
exit=1
```

**And the untouched trees:**

```
$ git status --porcelain examples/ src/ runtime/
(prints nothing)
```

---

## Gates

| Gate | Result |
| --- | --- |
| `PYTHONPATH=.:src:runtime .venv/bin/python -m tools.lints --all` | exit **0** |
| `make docs-strict` | exit **0** (all four steps) |
| `pytest tools/publish_scan_tests tools/docs_tests -q` | **267 passed**, no deselect |
| `pytest tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` | **passed** |

Tasks 1 and 2 ran `pytest tools/docs_tests -q` with exactly one deselect —
`--deselect tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
— for the same reason as plan 01: `public/` is a swept tree, so the committed
coupling report is stale from the first edit until task 3 regenerates it. The
deselect was **lifted in task 3** and the full suite is green without it (223
passed / 1 deselected in task 1; 267 passed with nothing deselected in task 3).

**The Phase 21 fence is no longer red.** `D-IMPL-188` bounded the four
untouched-tree assertions to Phase 21.1's close, so plan 01's blocker is
discharged and `tools/docs_tests/test_requirement_ledger.py` is green. This plan
did not touch that module.

---

## The coupling report

Regenerated in task 3 with exactly:

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
```

`.venv/bin/python -c "import joserfc"` exits **0** — the interpreter that ran the
sweep has the dependency whose absence causes the silent six-row drop.

```
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
264 coupling rows across 81 files (146 rows outside the three swept trees); 1892 files scanned
```

| | Coupling rows | Files |
| --- | --- | --- |
| Committed at plan start | **257** | 81 |
| After task 3's regeneration | **264** | 81 |

The count **rose** by 7; it did not fall, so the silent-drop trap did not fire.
Every changed line in the diff, in full:

```
-- Coupling rows: **257** across **81** files
+- Coupling rows: **264** across **81** files
-| 17-08 | 71 |
+| 17-08 | 78 |
-| `prose` | 52 |
+| `prose` | 59 |
+| `public/concepts/answers-no-document-contains.md` | 197 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
+| `public/concepts/answers-no-document-contains.md` | 205 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
+| `public/concepts/answers-no-document-contains.md` | 210 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
+| `public/concepts/answers-no-document-contains.md` | 269 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
+| `public/concepts/answers-no-document-contains.md` | 300 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
+| `public/concepts/answers-no-document-contains.md` | 305 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
+| `public/concepts/answers-no-document-contains.md` | 308 | `tests/examples/test_s1_01_output.py` | `prose` | documentary | - | - | 17-08 |  |
```

All seven new rows name this page, all are owned by `17-08`, all are `prose`.
**The client-surface citations produced no rows** — `src/ccf/client` and the two
`hw1` trees are not retiring paths, so the sweep has nothing to file against
them. Worth knowing before plan 04 reads the report expecting them.

The report is regenerated **once more after this SUMMARY is written**, because
`tools/retirement_sweep.py` is an `os.walk` from the repo root and
`.planning/phases/22-*` files are sweep subjects.

---

## Deviations from Plan

### Auto-fixed

**1. [Rule 2 — CLAUDE.md / charter] The criterion-numbered citation reading is in
this SUMMARY, not on the published page**

- **Found during:** Task 1, writing the client-seam note.
- **Issue:** The plan's task 1 asks the page to state that *"criterion 8, not
  criterion 3, governs it."* `public/charter.md`'s never-publish rule forbids
  any reference to `ROADMAP.md` from `public/`, and ROADMAP criterion numbers
  are project-internal planning vocabulary with no meaning to the page's reader.
  Writing them on the page would be leaking the planning tree into the published
  surface on the one page whose subject is honest citation.
- **Fix:** The page states the **substance** of the reading — all three points,
  in its own voice, under a bolded lead saying it is being stated rather than
  left to be inferred. The criterion-numbered form is carried verbatim in this
  SUMMARY under `Criterion 3 / criterion 8 — the client-seam reading`, which is
  the section plan 04 and plan 05 copy from anyway.
- **Not a widening.** The reading is unchanged; only its audience-facing wording
  is. The plan's stop condition — *"if this reading looks like a widening of
  criterion 3"* — does not fire: nothing that criterion 3 would have required as
  an include became prose, because the include form does not exist at that seam.
- **Files modified:** `public/concepts/answers-no-document-contains.md`
- **Commit:** `97b50b4`

**2. [Rule 2 — missing checkability] One node id added beyond the plan's list**

- **Found during:** Task 3, writing the caveat.
- **Issue:** The plan asks the caveat to say the `passage_anchor` contract ships
  and to cite it as the bare id `D-IMPL-46`. A bare decision id is provenance,
  not a checkable citation — on this page, of all pages, the *"the contract
  ships"* half should be openable.
- **Fix:** Added `src/ccf/contracts/claims.py::PassageAnchor` to the caveat
  paragraph, backticked, so `cite03-node-id` resolves it and it goes red if the
  type is renamed. It does not disturb the `.raw` / `.text` contrast — it is
  inside a code span, like the other two identifiers.
- **Files modified:** `public/concepts/answers-no-document-contains.md`
- **Commit:** `c04416f`

### Not fixed — nothing escalated

No Rule 4 situation arose. No scope-fence question reached Dave: no include was
added against `hw1`, no `examples/s1-02-*` tree was created, and `examples/`,
`src/` and `runtime/` are diff-empty.

---

## Threat Flags

None. This plan ships no runtime surface, no network-reachable code, no request
handler, no persistence and no authentication path.

- `T-22-08` (publishing whitepaper body text through an include) — mitigated as
  planned and by measurement: no include was added at all, `debt-profile.yaml`
  is excluded at 15 findings, and the five surviving sources measure 0 against
  the same scanner `make docs-strict` runs. The line-slice workaround is
  refused, with the reason recorded above so it is not re-derived.
- `T-22-09` (node-id citations into `src/ccf/client`) — mitigated: only public
  exported symbol names are cited, no line citations and no file bodies, and
  `cite03-node-id` was watched refusing `ProductClientX` and then reverted.
- `T-22-10` (the page's own claims) — mitigated: every empirical claim is either
  a literal include from a CI-gated source or a named test node id proven to
  collect, and the eight-check audit ran with its output recorded above.
- `T-22-11` (the honesty caveat) — mitigated: both halves in ONE paragraph,
  verified through the paragraph reader rather than by grep, and the word order
  measured so plan 03's exemption reaches it.
- `T-22-12`, `T-22-13`, `T-22-14`, `T-22-SC` — not applicable, unchanged.

## Known Stubs

None. Every section this plan wrote is complete, every include resolves and
renders, and every cited symbol and test node id resolves.

## Tracking deferred to the orchestrator

Per `docs/DECISIONS.md` **D-15**, no `state.*` or `roadmap.*` SDK writer was
invoked, and `.planning/STATE.md`, `.planning/ROADMAP.md`,
`.planning/REQUIREMENTS.md` and `docs/DECISIONS.md` were not modified. All are
hand-edited by the orchestrator. `tools/docs_tests/test_requirement_ledger.py`
was not edited.

## Self-Check: PASSED

- `public/concepts/answers-no-document-contains.md` — exists, 339 lines.
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — exists, 264 rows.
- `.planning/phases/22-.../22-02-SUMMARY.md` — exists.
- Commits resolve in `git log`: `97b50b4`, `dc260b1`, `c04416f`.
- `git status --porcelain examples/ src/ runtime/` prints nothing.
</content>
</invoke>
