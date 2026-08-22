---
phase: 21
kind: close-review-rerun
subject: shipped artifacts (provenance re-run)
reviewers: [gemini, codex, cursor]
reviewed_at: 2026-08-22
self_reviewer_skipped: claude (executing model — §3.1 independence)
base: c51406be1170259336e8799f5d4c69b2e39d4c8a..HEAD
ordered_by: Dave, immediately after `D-GATE-21`, alongside `D-IMPL-178`
source_inlined: 3540 lines / 266 KB — the whole check module line-numbered, all 143
  traceability rows line-numbered, the whole of `21-FINDINGS.md`, the whole of
  `21-DOCS-16-SPLIT.md`, the first 80 lines of `PROJECT.md`, and the base diff stat
reviewers_reviewed: 3
reviewers_failed: 0
findings_new: 8
findings_new_blocking: 3
findings_matching_first_run: 2
rejected: 3
fixes_applied: 0
---

# Cross-AI CLOSE Review — Phase 21, RE-RUN through the official path

`21-CLOSE-REVIEWS.md` is the first panel's record and is **untouched**. This is a
distinct file, per §3.1's requirement that a pre-existing review survive.

**Why this ran.** The first close-time panel assembled its payload by hand rather than
letting `/gsd-review --all` gather it, declared that as Deviation 1 in `21-07-SUMMARY.md`,
and Dave ruled on it at `D-IMPL-178` — the panel is *the set of external reviewers with
the executing model excluded*, not a command invocation, and at close its payload is *the
committed tree, however invoked*. He ordered this re-run as provenance confirmation. Under
`D-IMPL-178` only a **NEW BLOCKING** finding opens a `21.1` fix wave.

**Nothing was fixed here.** This record is a comparison. Every disposition below is a
recommendation for Dave, not an action taken.

## What changed about the payload, and why it matters

| | First panel | This re-run |
| --- | --- | --- |
| check module, line-numbered | yes | yes |
| all 143 traceability rows, line-numbered | yes | yes |
| `21-FINDINGS.md` | yes | yes |
| **`21-DOCS-16-SPLIT.md`** | **NO — named as left out, given to the single-agent pass** | **yes** |
| `PROJECT.md` context, base diff stat | partial | yes |
| size | 2374 lines / 182 KB | 3540 lines / 266 KB |

`D-IMPL-178` limb (c) requires a hand-assembled payload to name what it left out. The
first panel named `21-DOCS-16-SPLIT.md`. **That naming is what made this re-run worth
running**: two of the eight new findings are in that document, and one of them is
blocking. A left-out subject that is honestly named is recoverable; the mechanism worked.

## Reviewer roster — REVIEWED or FAILED, with the evidence

Invoked **sequentially**, from `$HOME/.claude/get-shit-done/workflows/review.md` with this
host's corrections, credentials from `/home/parkave/homecams_v2/.env`, CLI defaults, source
**inlined** rather than pointed at by path per `D-IMPL-178`.

| Reviewer | Invocation | Outcome |
| --- | --- | --- |
| **gemini** | `cat <prompt> \| gemini -p -`, `GOOGLE_API_KEY` | **REVIEWED.** Four findings. Every citation resolves: module `:251` is `if not tracked_under(paths):`, `:493` is the pathspec assertion, `:1266` is `if candidates and cited not in candidates:`, `FABRIC` is at `:82`; ledger `:331` is `DOCS-18`, `:464` is the `Coverage:` line. Zero fabricated symbols — notable, since this host's gemini has fabricated before. |
| **codex** | `printenv CODEX_API_KEY \| codex login --with-api-key`, then `cat <prompt> \| codex exec --skip-git-repo-check -` | **REVIEWED.** Five findings, 98,590 tokens. It emitted the bubblewrap warning this host always emits (3 occurrences in stderr) — and because the source was inlined, the sandbox failure could not empty its subject. Every citation resolves: `:751` is `def doubled_verdicts`, `:779` is `channel_disagreements`' `table = {`, `:1648` is `roster_verdicts`' `table = {`, `FENCE`'s `"examples/"` is at `:99`, ledger `:335` is `DOCS-22`. |
| **cursor** | `CURSOR_API_KEY` exported, `cat <prompt> \| cursor agent -p --mode ask` (no `--trust`; it does not exist in the installed version) | **REVIEWED.** Five findings plus an explicit "nothing new beyond these". Every citation resolves: `:2041` is `def test_control_13_…`, `:2050` is its `fabric_diff(phase_base_commit(), CHANGED_TREE)`, `:1854` is the `TESTS_TREE` diff, `:1765` is `if not cited.get(req_id):`, `Makefile:172` and `:188-190` are the `ci` and `gate-tools` targets. |
| **claude** | not invoked | **Skipped by design** — §3.1 independence; it is the executing model. |

**No reviewer failed to review.** All fourteen findings cited line numbers, and **every one
of them resolves against the tree** — checked individually, not sampled.

## Verdict

**YES — three NEW BLOCKING findings exist.** `RR-1` is the important one: it is the *same
hole B-1 was fixed for*, still open in the multi-member case, found independently by two
reviewers and reproduced against the shipped function.

## The comparison table

| # | Origin | Finding | vs first run | Class |
| --- | --- | --- | --- | --- |
| **RR-1** | gemini 1 + codex 1, **converged** | `tracked_under` validates the pathspec **tuple**, not its members — a one-key typo in one member of a multi-member spec still voids that limb silently | **NEW** | **BLOCKING** |
| **RR-2** | codex 3 | An unbolded leading verdict plus a later bolded contradicting verdict is two verdicts, and passes every gate | **NEW** | **BLOCKING** |
| **RR-3** | codex 4 | `21-DOCS-16-SPLIT.md` covers eighteen of Phase 16's **nineteen** `DOCS-` rows; the exclusion of `DOCS-22` exists only in `21-04-PLAN.md`/`SUMMARY` | **NEW** | **BLOCKING** |
| RR-4 | codex 2 | Duplicate requirement ids collapse into a `dict`; no gate requires id uniqueness | **NEW** | ADVISORY |
| RR-5 | gemini 2 | The corrected counters (`Coverage: 143/143` and the running totals) are read by no gate and drift silently | **NEW** | ADVISORY |
| RR-6 | gemini 4 | `_index()` alone among `refuse_unresolvable`'s inputs has no non-vacuity guard | **NEW** | ADVISORY |
| RR-7 | gemini 3 | `DOCS-18` still reads "still owed and **in flight** — plans `21-06` and `21-07` close it" in a merged tree | **NEW** | ADVISORY |
| RR-8 | cursor 5 | Split doc `:32` says `gate-tools` "runs **both** gate suites"; its own obligation column and `:84-86` say three | **NEW** | ADVISORY |
| RR-9 | cursor 1 + half of cursor 4 | `CONTROL 13` still diffs `CHANGED_TREE`, and `RECON-02` cites it for a proposition it does not establish | **MATCHES B-1** (residual) | ADVISORY |
| RR-10 | cursor 2 | `uncited_verdicts` is one citation per **row**, not per **limb** | **MATCHES A-6** (generalised) | ADVISORY |
| X-1 | cursor 3 | Split doc calls `DOCS-08` Complete while calling `DOCS-10`..`13` Partial for "the same shape" | **REJECTED** | — |
| X-2 | cursor 4, first half | `RECON-02` overclaims "names that test alongside its citation" | **REJECTED** | — |
| X-3 | codex 5 | `DOCS-20`'s split-doc provenance is stale/weaker than the ledger's | **REJECTED** | — |

---

## The three NEW BLOCKING findings, verified

### RR-1 — the B-1 fix is per-tuple, not per-member: a one-key typo in a multi-member pathspec is still silent

`tracked_under` (`tools/docs_tests/test_requirement_ledger.py:180`), its use inside
`fabric_diff` (`:251`), and `test_every_asserted_pathspec_names_a_tracked_subject` (`:493`).

**Found independently by gemini and codex**, from opposite ends — gemini via `FABRIC`,
codex via `FENCE`. Two reviewers, one hole, and it is *the same hole B-1 closed*, left
open in the case B-1 did not measure.

**What the fix claims.** The pathspec assertion's own docstring (`:483-485`) says: *"a
one-key typo in `FABRIC`, `FENCE`, `PINNED_FILES`, `UAT_RECORDS` or `TESTS_TREE` silently
converts the assertion it feeds into a test of nothing, and the run stays green."* That is
the promise. It is kept for the one-member constants and broken for the rest.

**What it does.** Both `fabric_diff`'s refusal (`if not tracked_under(paths):`) and the
shipped assertion (`assert tracked_under(spec)`) evaluate the **whole tuple**. One live
member makes the aggregate truthy. `git diff` then silently ignores the misspelled member.

**Measured against the shipped function** at the pinned base:

| pathspec | `tracked_under` | `fabric_diff` |
| --- | --- | --- |
| `("src/", "runtime/")` — the real `FABRIC` | 213 files | `""` |
| `("scr/", "runtime/")` — one transposition | **71 files** | **`""`, no refusal** |
| `("src/", "runtimes/")` — one insertion | **142 files** | **`""`, no refusal** |
| `("scr/", "runtimes/")` — both wrong | 0 files | REFUSED |

**The vacuity, demonstrated end to end.** `FENCE` has five members. Against base
`afc4fa58a543583bed8afbd2c90ccef157122882`, chosen because `examples/` changed there and
nothing else in the fence did:

| pathspec | tracked | diff empty? | what the assertion reports |
| --- | --- | --- | --- |
| `FENCE` as shipped | 592 | `False` | **fails, correctly** — the fence was breached |
| `FENCE` with `"example/"` for `"examples/"` | 269 | `True` | **PASSES — "tree untouched"** |

A one-key typo hides a real breach of the `D-11` scope fence, and the refusal added to
close exactly this class does not fire because `src/`, `runtime/`, `public/` and
`pyproject.toml` keep the tuple non-empty.

**Exposure.** Four of the six constants in `asserted_pathspecs()` are multi-member:
`FABRIC` (2), `FENCE` (5), `UAT_RECORDS` (11) and `CHANGED_TREE`. `UAT_RECORDS` is the
worst case — ten of its eleven paths could be wrong and the guard would still pass.
`TESTS_TREE` and `PINNED_FILES` are single-member and are genuinely covered.

**Not a live failure today** — all six constants are spelled correctly and the assertions
are honest as they stand. This is a latent hole in the guard, which is the same standing
B-1 and B-2 were held to.

**A remedy exists and is one line** (quantify per member rather than per tuple), and
`CONTROL 16`'s four near-miss spellings are all single-member, so a fifth subject would be
a mixed tuple. **Not applied — `D-IMPL-178` reserves this for Dave.**

### RR-2 — a mixed-format cell carries two verdicts and every gate agrees it carries one

`verdict_token` (`:701`), `doubled_verdicts` (`:751`), `test_no_status_cell_carries_two_verdict_tokens` (`:910`), `CONTROL 11` (`:1045`), against `RECON-01`.

**What `RECON-01` claims** (ledger `:266`, `:430`, verdict **`Complete`**): *"Every row in
the 54-row working set carries exactly one verdict, counted by a STRICT parse … in the
`DCD-02`..`DCD-12` status-cell shape."*

**The asymmetry.** `verdict_token` strips `**` **before** matching (`:709`), so an
**unbolded** leading verdict is read as the row's verdict. `doubled_verdicts` counts only
`BOLDED_RUN` matches (`:601`). A cell whose first verdict is unbolded and whose second is
bolded therefore presents **one** bolded verdict to the doubling gate and a **different**
verdict to every reader of `verdict_token`. Nothing requires the leading verdict to be
bolded — many shipped rows are bare (`DOCS-22` at `:335` is `| DOCS-22 | Phase 16 | Complete |`), so the permissiveness is deliberate and the doubling gate does not account for it.

**Measured.** `HARD-02`'s cell changed from `**Complete** (` to `Complete — later **Partial** (`, citations untouched:

| checker | real ledger | doctored |
| --- | --- | --- |
| `vocabulary_offenders` | 0 | **0** |
| `doubled_verdicts` | 0 | **0** |
| `channel_disagreements` | 0 | **0** |
| `uncited_verdicts` over both rosters | 0 | **0** |
| `unverdicted(working_set(...))` | 0 | **0** |
| `verdict_token("HARD-02")` | `Complete` | **`Complete`** |

A working-set row that visibly says `Partial` in bold is reported `Complete` by every
gate, and the gate written to refuse exactly this shape (`CONTROL 11`'s subject) does not
see it. This is the phase's defect class inside `RECON-01`'s own machinery.

### RR-3 — the split document rules on eighteen of nineteen rows, and the missing one is named only in a SUMMARY

`21-DOCS-16-SPLIT.md:1` (*"Phase 16's eighteen `DOCS-` rows"*), `:27-48` (the roster),
`:431` (*"Accept the ten `Complete` verdicts"*), against ledger `:335`.

**This is the subject the first panel left out**, and this is what its exposure found.

**Measured.** `grep -c "^| DOCS-[0-9]* | Phase 16 |" .planning/REQUIREMENTS.md` → **19**.
The split's table carries **18**. The absentee is **`DOCS-22`**, and it is the one Phase 16
row that reads a bare, uncited `Complete`.

**Why it is the B-3 shape, exactly.** The exclusion is deliberate and is recorded — in
`21-04-PLAN.md:80` (*"`DOCS-22` is already `Complete` and is outside the 54"*) and
`21-04-SUMMARY.md:77`. It appears **nowhere in the split document itself and nowhere in
`21-FINDINGS.md`** — the two documents Dave rules from. That is `D-IMPL-170`'s pattern and
it is what B-3 was found blocking for at the first close: *a scope decision that lives only
in a wave hand-off*. A reader of the split alone is told the set is "Phase 16's eighteen
`DOCS-` rows" and has no way to learn that Phase 16 minted nineteen.

**Confirmed outside the machinery too:** `DOCS-22` is in neither
`WORKING_SET_ROSTER` (54) nor `PHASE_OWN_ROSTER` (10), so no gate in the module reads it,
and its bare uncited `Complete` is one of the 79 rows already carried as **A-5**.

**Consequence is smaller than B-3's.** The ten `Complete` verdicts the document asks Dave
to accept are unaffected, and the substance of `DOCS-22`'s uncited verdict is already
carried as A-5. What is missing is one sentence of scope in a ruling document. It is
recorded as blocking on the **pattern precedent B-3 set at this same close**, not on
consequence, and Dave should weigh it that way.

---

## The NEW ADVISORY findings, verified

**RR-4 — duplicate requirement ids collapse and nothing objects.** `channel_disagreements`
(`:779`) and `roster_verdicts` (`:1648`) both build `{req_id: status}` dicts; a repeated id
keeps one row. `grep -n "unique\|duplicat"` over the module finds uniqueness enforced only
for `_doctored`'s anchor (`:807`), never for requirement ids. **Measured:** `HARD-02`'s row
duplicated with `Phase 99` and its citations intact — `traceability_rows` returns **144**
rows with `HARD-02` twice, and all five gates return `[]`. The ledger's own `Coverage` line
(`:464`) says *"each to exactly one phase"*; that sentence is falsified and unguarded.

**RR-5 — the counters this phase corrected are read by no gate.** `grep -n "Coverage\|143/143"` over the module returns **nothing**. `RECON-10` corrected `Coverage: 94/94` to
`143/143` and re-derived the running totals by hand under `D-15`. **Measured:** adding one
row to both channels makes the table 144 rows while `:464` still reads `143/143`, and every
gate stays green. `RECON-10` is already `Partial` for a different limb, so this is a
strengthening question and not a wrong verdict. Adjacent to **A-1** — the same "nothing
stops it happening again" shape, aimed at counters rather than at rows.

**RR-6 — `_index()` is the one input to `refuse_unresolvable` with no non-vacuity guard.**
The function raises on empty rows (`:1201`) and on empty citations (`:1208`), then reads
`index = _index()` (`:1216`) unchecked. The ambiguity branch (`:1222`) and the
moved-path branch (`:1266`, `if candidates and cited not in candidates:`) both degrade to
silence on an empty or thinned index — and the moved-path branch is the "second silent
hole" the module says it exists to dodge (`:1249-1252`). `_index()`'s own docstring guards
the *opposite* failure (a bare `rglob` making everything ambiguous) and not this one. The
index holds **5012** basenames today, so nothing is live. Lower-probability than RR-1: it
needs `repo_index` to break, which would likely redden the lint's own suite first.

**RR-7 — `DOCS-18` still says "in flight" in a merged tree.** Ledger `:331`: *"Limb 3 —
still owed and in flight: … plans `21-06` and `21-07` close it."* Both plans ran, the phase
merged, and `RECON-09` at `:438` reads `**Complete**` citing `D-GATE-21` at
`docs/DECISIONS.md:510`. `.planning/REQUIREMENTS.md` is a **maintained** record under the
citation lint's own split (`tools/lints/citations.py:104-107`: *"a reader is entitled to
expect a maintained file's citations true of the current tree"*), so a forward reference to
work that has completed is stale prose in a file held to currency. **Gemini's further
conclusion — that the row is therefore "substantively discharged" and should not read
`Partial` — is rejected**: limb 3 is *"a requirement ledger that matches the tree"*, and
**A-5**'s 79 uncited `Complete` rows mean it demonstrably does not yet. `Partial` is right;
the sentence explaining it is out of date.

**RR-8 — the split document's summary row undercounts its own subject.** `:32` states the
obligation as *"`make ci` composes the **three** gate suites"* and then evidences it with
*"`gate-tools` runs **both** gate suites"*. `Makefile:188-190` runs three directories across
two pytest invocations, and the document's own detailed section at `:84-86` gets it right.
A reader ruling from the summary table alone misjudges what full local reproduction covers.

---

## The two findings that MATCH the first run

**RR-9 — `CONTROL 13` was named in B-1 and left unrepaired. MATCHES B-1.** Cursor arrived
at it independently. `test_control_13_a_changed_tests_tree_would_be_detected` (`:2041`)
calls `fabric_diff(phase_base_commit(), CHANGED_TREE)` at `:2050`, while the assertion it
vouches for calls `fabric_diff(phase_base_commit(), TESTS_TREE)` at `:1854`. B-1's own
write-up says so: *"`CONTROL 13`'s name is `a_changed_tests_tree_would_be_detected` and it
never mentions `tests/`."* B-1 closed the **vacuity** via `tracked_under` — and because
`TESTS_TREE` is single-member, that fix genuinely covers it (unlike RR-1's four). What was
not repaired is the control's aim, and the residual is worth stating: **`RECON-02`'s
shipped status cell (`:431`) says *"with CONTROL 13 proving that comparison compares
something"*** — a shipped `Complete` citing a control for a proposition the control does
not establish. That specific consequence is not in the first record.

**RR-10 — per-row citation, not per-limb. MATCHES A-6, generalised.** `uncited_verdicts`
(`:1718`) asks `if not cited.get(req_id)` (`:1765`) — *any* citation-shaped token in the
cell. A multi-limb row satisfies it while a second limb rests on nothing. B-2's fix was
deliberately scoped to "carries a citation at all", and A-6 already carries the three named
rows (`DOCS-06`, `DOCS-08`, `CLNT-16`). The general form — *no gate requires each limb of a
multi-limb verdict to be separately evidenced* — is the strengthening question underneath
A-6, and it is a policy call, not an executor's.

---

## REJECTED, with the evidence that refutes them

### X-1 (cursor) — "the split calls `DOCS-08` Complete while calling `DOCS-10`..`13` Partial for the same shape"

**The two shapes are different and the document says which is which.** `DOCS-10`..`DOCS-13`
are `Partial` because a limb **does not exist in the tree** — *"limb 2 does not exist —
`backends.yaml` declares one profile and no test compares a served product across
substrates"* (`:34`); *"no published page names a Section-1 example"* (`:36`). `DOCS-08`'s
**both limbs are true**: `Makefile:172` is `ci: ci-core examples docs-strict gate-tools` and
`gate-tools` (`:188-190`) runs all three suites. What is absent is a *guard*, not a limb.
The split names that gap explicitly at `:91-93` — *"No test in this tree reads the `ci`
target's composition… That is a work-list item, not a defect in this row"* — so it is not
laundered. B-3 states the same principle: *"the rows ask whether the property holds, not
whether a test guards it."* **Rejected as a defect**; substance already carried as **A-6**.

### X-2 (cursor) — "`RECON-02` overclaims 'names that test alongside its citation'"

**The row discloses precisely this, in its own text.** Ledger `:431` ends: *"That a named
test genuinely GUARDS the property a row claims is a judgement no assertion can make, and
it is attested by inspection rather than by a green run."* An overclaim is a claim of
enforcement that is not made; this row states the opposite. **Rejected.** (The other half
of cursor's finding — the `CONTROL 13` citation — is upheld and recorded as **RR-9**.)

### X-3 (codex) — "the split's `DOCS-20` evidence carries stale/weaker provenance than the ledger's"

**The split's wording is accurate.** `runtime/ccf_runtime/mcp/egress.py` imports
`PRODUCT_REQUEST_TOOL` at `:123`, lists it in `__all__` at `:140`, and documents at `:171`
that it is *"**Re-exported from** `ccf.products.door.PRODUCT_REQUEST_TOOL`"*. The split says
egress *"carries"* (`:44`) and *"exposes"* (`:355`) it — both true of a re-export. The
ledger row (`:333`) is *more precise* about the citable **definition site**, which is a
different question and is why it says so. Codex's reproduction — that a fabricated symbol in
the split would not redden anything — is true, but for a documented reason:
`exemption_reason(".planning/phases/…/21-DOCS-16-SPLIT.md")` returns *"phase documents are
dated records of a moment…"*, a stated policy with a stated price
(`tools/lints/citations.py:104-113`). That is the same reasoning R-2 was rejected on.
**Rejected.** The adjacent observation is real and is worth a sentence: a *ruling* document
Dave decides from is arguably a maintained record rather than a dated one, and
`MAINTAINED_RECORDS` is the mechanism that would say so. A question for Dave, not a defect.

---

## Every mutation run in this re-run

All against the **shipped** functions, in memory over doctored copies of the real
documents. **No file in the tree was modified.**

| # | Mutation | Result |
| --- | --- | --- |
| 1 | `fabric_diff(base, ("scr/", "runtime/"))` | **`""` — no refusal.** RR-1 demonstrated |
| 2 | `fabric_diff(base, ("src/", "runtimes/"))` | **`""` — no refusal.** RR-1, other member |
| 3 | `fabric_diff(base, ("scr/", "runtimes/"))` | REFUSED — the guard works when *every* member is wrong |
| 4 | `FENCE` with `"example/"`, against a base where `examples/` changed | **GREEN — "tree untouched".** RR-1's vacuity, end to end |
| 5 | `HARD-02` → `Complete — later **Partial** (` | **GREEN on all five gates.** RR-2 |
| 6 | `HARD-02` duplicated with `Phase 99` | **GREEN, 144 rows, id twice.** RR-4 |
| 7 | `| ZZZZ-01 | Phase 22 | Pending |` added to both channels | **GREEN, 144 rows, `Coverage:` still `143/143`.** RR-5 |

Baseline before and after: `pytest tools/publish_scan_tests tools/docs_tests -q` →
**205 passed**.

## What this record does NOT do

**No fix, no plan, no `21.1`, no amendment to `D-GATE-21`, `REQUIREMENTS.md` or
`ROADMAP.md`.** `D-IMPL-178` says a NEW blocking finding is what would open a fix wave, and
three exist — but opening one is Dave's ruling, not an executor's, on the same reasoning
§3.1 step 3 gives for the gate itself. The only files this run writes are this record and
the regenerated coupling inventory.

## What the re-run says about the first panel

The first panel was not wrong about anything it looked at — nothing in
`21-CLOSE-REVIEWS.md` is refuted here, and its three rejections all survive re-examination.
Its limitation was **reach**, in two places, and both were declared rather than concealed:

1. It measured B-1 against single-member pathspecs and shipped a per-tuple fix. RR-1 is
   what the multi-member case does, and two of three reviewers walked straight into it —
   which suggests the first panel would have found it too, given the same brief pointing at
   *the neighbourhood of the fixed defect*. §3.1's "point them at what is adjacent"
   instruction is doing real work here.
2. It left `21-DOCS-16-SPLIT.md` out and **named it**. RR-3 and RR-8 are in that document,
   and RR-3 is blocking. `D-IMPL-178` limb (c) — name what you left out — is the rule that
   made this recoverable, and it recovered.

Provenance, on the narrow question Dave asked: three external reviewers, executing model
excluded, source inlined, every cited symbol and line number resolving against the tree,
raw prompt and raw outputs retained under this session's scratchpad as
`rerun-prompt.md`, `gemini-raw.txt`, `codex-raw.txt` and `cursor-raw.txt` — their absence is
what made the first run's provenance unverifiable. The panel is discharged on the shipped tree.
