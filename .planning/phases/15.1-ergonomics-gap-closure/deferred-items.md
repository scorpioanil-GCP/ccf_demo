# Deferred items — phase 15.1

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary. Plan 15.1-10 surfaces these to Dave at the phase gate.

**Status after the gate (D-GATE-15.1, Dave, 2026-08-05).** The phase is approved.
Dave's verbatim reply was **"Approved"** — one approval of the phase as presented,
not five separate written rulings on the five items the presentation put to him.
The three residuals below marked **carried forward** are therefore **open, accepted
at approval, and not closed by it**. They inherit to Phase 16.

> ### STATUS SUPERSEDED — 2026-08-06. Read this before any "2026-08-05" line below.
>
> **The 2026-08-05 approval was WITHDRAWN on 2026-08-06** (`D-GATE-15.1
> (withdrawal, 2026-08-06)` in `docs/DECISIONS.md`) when the code review that the
> `/gsd:execute-phase` workflow runs *after* the phase gate returned **3 verified
> Critical** findings the gate presentation could not have contained. Five review
> rounds followed — Criticals **3 → 1 → 1 → 1 → 0** across `15.1-REVIEW.md`,
> `15.1-REVIEW-FIXES.md`, `-2.md`, `-3.md`, `-4.md` — closed by remediation plans
> 15.1-11 … 15.1-17.
>
> **The phase was re-approved on 2026-08-06** (`D-GATE-15.1 (re-approved,
> 2026-08-06)`), on the round-5 verdict of **0 Critical, 2 Warning, 4 Info**, with
> Dave choosing *"Approve now — WR-01/WR-02 as residuals"*. ERGO-18 and ERGO-19
> are Complete; **R5-WR-01 and R5-WR-02 are accepted as recorded OPEN residuals,
> not closed**; Phase 16 is unblocked.
>
> **Every "Gate disposition (D-GATE-15.1, 2026-08-05)" line below is re-affirmed
> unchanged by the re-approval** — R-2, R-3 and R-4 remain open, carried, and
> unclosed, in exactly the terms they were carried in. The dates are left as
> written rather than rewritten, so both gates survive in the record. The
> `.planning/ROADMAP.md` §Coverage item marked **CLOSED at the gate** is closed by
> the *work* that corrected the sentence, not by the withdrawn approval, and stays
> closed.
>
> **The residual set this file must carry is larger than it was on 2026-08-05.**
> Five entries are appended below the six that were here: the fifth review's two
> Warnings (R5-WR-01, R5-WR-02), the two module limits carried without an entry of
> their own (augmented-assignment unreadability; attribute and subscript targets),
> and the three `src/` boundary-validation Infos the remediation rounds
> deliberately deferred (IN-F1 / IN-F2 / IN-F4). Every entry in this file now
> names the review document it came from.

Items 1 and 2 were recorded in `docs/SURFACE-AUDIT.md` §6.4 item 1 and §6.5
respectively and were put to Dave at the gate. Items 3 and 4 were found by plan
15.1-10 at phase close. Items 5 and 6 — D-IMPL-86's **placement** and
**authorship** residuals — were originally kept out of this file on the grounds
that they are mechanism residuals rather than out-of-scope discoveries, and lived
only in `docs/SURFACE-AUDIT.md` §6.4 items 5 and 4. They are entered here as well
at the gate close, so that the one file Phase 16 reads for carried work names every
carried item rather than three of five. They remain **two distinct residuals of the
same family, never one residual stated twice** — merging them would understate what
this phase asked Dave to accept.

## The HTTP schema route still serves only the typed-registerable classes

- **Source review document:** `15.1-REVIEWS.md` §5 item **R-4** (the phase-close
  cross-AI review round), from a finding raised by plan 15.1-03 itself. Not
  re-reported by any of the five post-gate code-review rounds, each of which
  explicitly excludes it from scope (`15.1-REVIEW-FIXES-3.md:561`,
  `15.1-REVIEW-FIXES-4.md:502`). **OPEN.**
- **Gate disposition (D-GATE-15.1, 2026-08-05):** surfaced as ruling item **R-4**
  and **carried forward — open, not closed.** The approval covers the phase as
  presented; it does not answer the route's contract question, which this phase
  sharpened rather than resolved. Inherits to Phase 16.
- **Found during:** plan 15.1-03, task 2
- **What:** `runtime/ccf_runtime/http_api/routes/schema.py` (and the
  `ccf schema export` CLI verb, and `tools/dump_schemas.py`) enumerate
  `SDK_ARTIFACT_CLASSES`. Plan 15.1-03 added a second SDK-owned mapping,
  `SDK_VERSIONED_ARTIFACT_CLASSES`, holding the six **author-versioned**
  classes whose contracts declare a string `artifact_version`:

  - `ccf.agent-definition`
  - `ccf.prompt-artifact`
  - `ccf.task-definition`
  - `ccf.workflow-definition`
  - `ccf.skill-catalog-entry`
  - `ccf.skill-grant`

  `docs/schemas/` holds committed schemas for all six (plan 15-14), and the
  route answers **404** for every one of them.

- **Why it was not fixed here:** widening the served set is a runtime surface
  change with `__all__`-visible consequences that nobody has ruled on, and this
  plan's own threat register accepts it explicitly (T-15.1-03-05). Nothing
  serves a *wrong* schema; the committed tree remains the authoritative
  authoring baseline for an adopter's editor.

- **What changed since phase 15 recorded this** — the question is sharper now,
  not answered. Phase 15's `deferred-items.md` framed the route's set as
  defensible because it "documents what a *manifest* may name". After 15.1-03
  that framing is no longer accurate: a manifest **may** name all six, as
  `registration: versioned`, and `load_and_boot` dispatches them through
  `register_versioned`. So the route's actual contract has narrowed to "the
  classes a manifest may name for **typed** registration" — which is a real
  contract, but a narrower and less obvious one than the phrase it inherited.
  The route's docstring now says so precisely; the ruling is still owed.

- **Where it belongs:** a ruling on whether the route's contract is "every
  schema the SDK owns" (serve the union of both mappings) or "the classes a
  manifest may name for typed registration" (keep the set, keep the sharpened
  docstring). Either answer is defensible; the defect is that the code and the
  name have drifted apart. Interacts with the `ccf schema export` CLI verb and
  `tools/dump_schemas.py`, which read the same mapping.

## Example 05 registers an author-versioned class through `register_typed`

- **Source review documents:** `15.1-REVIEWS.md` finding **F-7** (advisory, at
  the phase-close review), then `15.1-REVIEW.md` **CR-02** (post-gate code
  review, **Critical**), which found the same defect at **three** sites rather
  than one and found the guarding test claiming four keys while asserting over
  three.
- **CLOSED 2026-08-06 by plan 15.1-11** (verified against the tree at the
  re-approval, not taken from the SUMMARY): all three sites now take
  `register_versioned` — `examples/05-workflow-hitl/run.py::run`,
  `examples/06-decision-replay/run.py::run`, `examples/08-e2e-demo/run.py::run` —
  each handling the returned `RegistrationRefusal`, and
  `tests/examples/test_workflow_hitl_output.py::test_the_author_versioned_definitions_kept_their_bump_check`
  now asserts over **four** keys including `prompt_artifact_key`. Closure
  confirmed by `15.1-REVIEW-FIXES.md` ("CR-02 is closed at the code level … the
  corrected test was *strengthened*, not relaxed"). **The wider question the
  entry raises stays OPEN** — the SDK refuses the wrong registration path at the
  *manifest* seam and not at the *registry* seam, and whether that asymmetry is
  intended is still worth Dave's word. That half inherits to Phase 16.
- **Found during:** plan 15.1-03, task 2
- **What:** `examples/05-workflow-hitl/run.py` registers `prompt-artifact.yaml`
  with `registry.register_typed(...)` even though `ccf.prompt-artifact` declares
  a string `artifact_version` and is therefore author-versioned. The adjacent
  comment says "Four are AUTHOR-VERSIONED" while only three of the four travel
  `register_versioned`.
- **Why it was not fixed here:** `refuse_registration_the_sdk_fixes` guards the
  **manifest** path, by design — a direct `registry.register_typed` call in
  adopter code is the adopter's own call, and the SDK does not police it.
  Changing the example would change its audit log, and
  `tests/examples/test_workflow_hitl_output.py::test_the_author_versioned_definitions_kept_their_bump_check`
  asserts on exactly **three** definition keys. Flipping the fourth is a
  behavior change to a shipped example plus a test edit, in a plan whose scope
  is the manifest refusal.
- **Where it belongs:** a follow-up that either moves the prompt artifact onto
  `register_versioned` (and widens the example test to four keys), or states in
  the comment why the prompt artifact is deliberately the odd one out. Note the
  wider question it raises: the SDK refuses the wrong registration path at the
  *manifest* seam and not at the *registry* seam, and whether that asymmetry is
  intended is worth Dave's word.

## `.planning/ROADMAP.md` §Coverage undercounts the requirement set

- **Found during:** plan 15.1-01 (flagged), re-verified at phase close by plan
  15.1-10
- **What:** `.planning/ROADMAP.md:528` reads "All 21 v0.2 requirements mapped,
  each to exactly one phase". `.planning/REQUIREMENTS.md`'s traceability table
  now holds **42** rows (verified by count at phase close), 19 of them ERGO.
  15.1-01 added ERGO-18 and ERGO-19 and moved REQUIREMENTS.md's own coverage
  sentence 40 → 42; the ROADMAP sentence was not moved with it.
- **Why it was not fixed at the time:** `.planning/ROADMAP.md` is
  orchestrator-owned in worktree mode and plan 15.1-10's execution was forbidden
  to write it. It was also not a defect an executor could close unilaterally —
  the sentence might have been *intended* to count only the pre-15 phases, in
  which case the fix was to say so rather than to change the number.
- **CLOSED at the gate (D-GATE-15.1, 2026-08-05).** Both readings turned out to
  be partly right and the corrected sentence says so. The enumeration under the
  old figure sums to exactly 21 and is the set defined at milestone definition
  (2026-08-01) — so the 21 was never wrong about what it counted, only about what
  it claimed ("all"). But "pre-Phase-15" would have been wrong too: EXAM-04 →
  13.1 and EXAM-05 → 13.2 are pre-15 and outside the 21. The sentence now reads
  42 in two named halves — the 21 defined at milestone definition, and the 21
  minted since by inserted phases (EXAM-04, EXAM-05, ERGO-01..17, ERGO-18..19) —
  with 13.3 and 14.1 explicitly noted as minting none. Counted from
  `REQUIREMENTS.md`'s traceability table (`42` rows; by phase: 9→3, 10→2, 11→4,
  12→3, 13→3, 13.1→1, 13.2→1, 14→6, 15→17, 15.1→2), not remembered.

## Three Phase 15.1 acceptance criteria are wrong as written

- **Source document:** not a review finding — found by plan 15.1-10 at phase
  close and written up in `docs/SURFACE-AUDIT.md` §6.3. Recorded in the withdrawn
  `D-GATE-15.1` entry and re-recorded in the re-approval, so the corrections
  survive the withdrawal. **OPEN as guidance to Phase 16** — none of the three
  may be inherited as a check.
- **Found during:** plan 15.1-10, phase close
- **What:** three literal checks in this phase's own plan text cannot be
  satisfied without gaming, and one of them would *undo* the phase's fix if it
  were. Fully written up in `docs/SURFACE-AUDIT.md` §6.3; in brief:
  1. `grep -rn "operators_invoked=execution.operators_invoked" examples/` is
     asked to be empty and **must not be** — the survivors are result-carrier
     fields handing the engine's resolution to the paired tests. Observed count
     at close is **5**, not the **8** three prior documents predicted (15.1-07's
     SUMMARY, 15.1-08's SUMMARY, and the phase-close brief); examples 00/01/02
     route the value through a named local (`engine_transcription`, added by
     15.1-05), so the literal string is absent while the property is identical.
     The 8 was correct before wave 5 and propagated three documents deep without
     re-measurement. **Re-measured a third time at the gate (2026-08-05), by the
     orchestrator on `main` and again by the executor writing this line — 5 both
     times**, at `examples/03-harness-portability/run.py::decision`,
     `examples/04-cross-process/producer_child.py::build_covenant_slice_product`,
     `examples/06-decision-replay/run.py::run`,
     `examples/07-artifact-store-mcp/run.py::workload`, and
     `examples/08-e2e-demo/run.py::run`. Recorded in `D-GATE-15.1` as well, so
     the correction survives outside this phase's own directory.
  2. `grep -c "independent witness" src/ccf/products/gates.py == 0` — it is 3,
     all negations or a quoted-then-answered superseded claim, and
     `binder.py` greps to 0 for the *identical negated sentence* only because
     the phrase wraps across a line break.
  3. `docs/SURFACE-CHANGES.md` section order — the assembler groups by change
     type first, so plan order applies within groups, and only four 15.1
     fragments exist (05–09 correctly wrote none).
- **Why it was not fixed here:** a criterion is plan text, and plan text is the
  record of what was *intended*; rewriting it to match what was built destroys
  the audit trail (§5.3 row A-6). The corrections are recorded in the audit
  instead, which is what a later reader consults.
- **Where it belongs:** Phase 16 should not inherit any of the three as a check.
  If a standing gate is wanted for (1), it already exists and is structural:
  `tests/products/test_gate_two_call_shape.py`.

## D-IMPL-86's *placement* residual — the binder is adopter-invoked

- **Source review document:** `15.1-REVIEWS.md` finding **F-4** (cursor,
  confirmed **blocking**), escalated to gate ruling item **R-2**. Re-affirmed as
  out of scope and not re-reported by all five post-gate rounds
  (`15.1-REVIEW-FIXES-3.md:561`, `15.1-REVIEW-FIXES-4.md:502`). **OPEN.**
- **Gate disposition (D-GATE-15.1, 2026-08-05):** surfaced as ruling item **R-2**
  and **carried forward — open, not closed, not resolved.** It is cursor's
  confirmed **blocking** review finding (F-4), escalated rather than fixed because
  closing it is new fabric behavior that moves the D-15A abstraction line, which
  is Dave's ruling to make and was not made at this gate. Inherits to Phase 16.
- **Found during:** Phase 15.1 planning (plan-checker), restated by the
  `D-IMPL-86 (correction, 2026-08-05)` entry, confirmed at the phase-close review
- **What**, in the four parts the binder's module docstring carries:
  1. The binder sits **between plan construction and `ProjectionEngine.execute`**,
     in adopter code, because `load_and_boot` has no `ProjectionPlan` in scope at
     any of its preflights (`src/ccf/deployment/manifest.py::_resolve_tenant` as the
     correction cites it — it named a line inside that helper, where it stood in
     the tree the correction was written against; the durable reference is the
     symbol, not the line). The SDK never invokes it.
  2. It **returns `None`**, so nothing observable at runtime proves it was called
     — no product field, no pin, no audit event. A deployment that omits it
     produces byte-identical output.
  3. **Nothing outside the SDK's own `examples/` tree holds a deployment to
     calling it at all.** An adopter who omits the call gets no error, no
     warning, and no degraded output.
  4. The AST coverage check that enforces the call
     (`tests/products/test_gate_two_call_shape.py`) is **scoped to `examples/`
     only** — a check on the SDK's own teaching material, not on adopters.
- **Why it is the sharpest carried item:** it is the same shape as CR-1, the
  defect this phase was convened to close — a governance guarantee that holds by
  convention outside the tree the SDK controls — at a different seam. That is why
  it was put to Dave explicitly rather than left in a docstring, and why the gate
  records it as accepted-and-open rather than as accepted-as-fine.
- **Where it belongs:** Phase 16, or a Phase D mini-cycle on the D-15A line.
  Also recorded in `docs/SURFACE-AUDIT.md` §6.4 item 5 and `15.1-REVIEWS.md` F-4.

## D-IMPL-86's *authorship* residual — transcription collapses the check

- **Source review document:** `15.1-REVIEWS.md` finding **F-5** (advisory),
  escalated to gate ruling item **R-3**; re-confirmed as distinct-and-open by
  `15.1-REVIEW-FIXES-3.md` ("Nothing in the new docstrings implies R-3 is
  closed") and by `15.1-REVIEW-FIXES-4.md`'s "**R-3 is kept distinct**"
  verification note. **OPEN.**
- **Gate disposition (D-GATE-15.1, 2026-08-05):** surfaced as ruling item **R-3**
  and **carried forward — open, not closed.** Distinct from R-2, never to be
  merged with it. Inherits to Phase 16.
- **Found during:** D-IMPL-86's own ruling, which accepts it in its "Consequences
  accepted" paragraph; re-confirmed at the phase-close review as F-5 (advisory)
- **What:** a deployment that reads one artifact into the other still collapses
  the binder, so dual authorship remains **convention-assisted at the authoring
  boundary** even though the check itself is structural.
- **Why it cannot be closed by a gate:** D-IMPL-86 established that **no AST gate
  can distinguish an authored literal from a transcribed one** — under the
  candidate designs the compliant state (an author typed the keys) and the
  violating state (an author transcribed them from the other artifact) are
  textually identical. This residual is therefore structurally unclosable by the
  mechanism family the SDK has been using, not merely unclosed.
- **Where it belongs:** recorded in the binder's module docstring, in
  `docs/SURFACE-AUDIT.md` §6.4 item 4, and here. Phase 16 must describe the
  binder without claiming it makes dual authorship structural.

## The superseded D-IMPL-85 / D-IMPL-84 claims: what remains after the measured sweep of 2026-08-06 (plan 15.1-20)

- **Source review documents:** `15.1-REVIEW-FIXES.md` **WR-F6** (the finding that
  opened it), `15.1-REVIEW-FIXES-2.md` **WR-03** (the enumeration offered in place
  of finishing the sweep was itself a subset), `15.1-REVIEW-FIXES-3.md` **IN-02**
  (three precision points), `15.1-REVIEW-FIXES-4.md`'s verification note
  confirming the corrected enumeration reads true against the files, and
  `15.1-VERIFICATION.md` findings **W-4 / N-2 / N-3**. **OPEN — the sweep is
  still incomplete for `examples/01`–`04` and for `docs/surface-changes/` +
  `docs/SURFACE-CHANGES.md`. `public/` and `tools/` are CLOSED as of plan
  15.1-20.**

- **SCOPE MEASURED, NOT INHERITED — 2026-08-06, plan 15.1-20.** Read this
  paragraph before working from any list below it.

  **How the scope was decided.** Every top-level tracked directory was
  enumerated from `git ls-files` — `.github`, `.planning`, `docs`, `examples`,
  `perf`, `public`, `references`, `runtime`, `src`, `tests`, `tools`, and the
  repo-root files — and every one was swept. None was assumed clean and none was
  inherited from a prior round. `perf/` and `references/` return zero hits on
  every phrasing; the rest are reported below.

  **How the sweep was run, and why the method matters more than the phrase
  list.** Every prior round grepped **lines**. A wrapped Markdown sentence is
  invisible to that, and it is a mechanical reason the count kept coming back
  low: `public/how-to/compose-a-workflow-with-hitl.md` spells the claim as
  *"What the manifest deliberately does **not**\nname is the four
  author-versioned definition classes"*, and no line-scoped grep of any phrase
  in the seven-phrasing list finds it. This sweep joined each file into one
  whitespace-normalized string, matched there, and mapped the offset back to a
  line. **The phrase list was not the binding constraint; the line boundary
  was.**

  **Result of the tree-wide sweep** (paragraph-scoped, ten claim-specific
  phrasings, hits per tree):
  `.planning` 142 · `examples` 51 · `docs` 48 · `tests` 16 · `tools` 11 ·
  `src` 10 · `runtime` 1 · `public` 0 (after this plan's four corrections) ·
  `.github` 0 · `perf` 0 · `references` 0 · root 0.
  A hit is a candidate, not a defect: `src/`, `runtime/` and `tests/` were read
  and every hit there is either an unrelated true statement or one of the
  quoted-then-corrected withdrawn claims plan 15.1-19 wrote.

- **SCOPE CORRECTED — 2026-08-06, plan 15.1-19 (verification finding W-4).** The
  scope sentence above previously named **two** trees, `examples/01`–`04` and
  `docs/surface-changes/`. That was a subset — **the fourth under-count of this
  same sweep in this phase, and the first located in the record of what
  remains.** The claim also survived in **`tests/`** and in **`tools/`**, neither
  of which any round swept: plan 15.1-15's scope was examples 05/06/08 plus two
  example test modules, plan 15.1-16's was `tests/products/` plus this register,
  and its re-run covered `examples/01..04` and `docs/`. So `tests/cli/`,
  `tests/examples/` and all of `tools/` were never in any round's scope, and this
  entry inherited that gap without saying so. Both trees are enumerated below by
  **measurement** — the seven phrasings re-run over `tests/ tools/ src/ runtime/`
  on 2026-08-06, every hit opened and read individually to separate the false
  from the true.

  **In `tests/` — two modules, five sites. ALL FIXED by plan 15.1-19; listed so
  the record shows what was there, not as outstanding work:**
  - `tests/examples/test_workflow_hitl_output.py`
    `::test_the_author_versioned_definitions_kept_their_bump_check` — the
    docstring's *"The reason is mechanical: the manifest path registers through
    `register_typed`"* **and** the **failure message** *"folding it in silently
    drops the D-05 bump check"*. The failure message is the same shape the
    phase-close review reclassified advisory→**blocking** for
    `test_required_operators_guard.py` (D-GATE-15.1, F-1/F-2/F-3): what an author
    reads at the moment the assertion fires. Corrected to the true reason — the
    four are outside the manifest by this example's **teaching choice**, which is
    what `examples/05-workflow-hitl/artifacts/manifest.yaml` already says.
    Assertion unchanged.
  - `tests/cli/test_schema_export.py` — **three** sites, where the verification
    report named one:
    - `::test_a_schema_grants_no_manifest_addressability` docstring (the site
      W-3 named)
    - `::test_every_author_versioned_class_has_a_committed_schema` docstring —
      *"a manifest must not carry them, because `load_and_boot` registers
      through `register_typed`"* **(found by this plan's re-run; named by
      neither the register nor the verification report)**
    - the same docstring's *"no member is manifest-addressable"* — false as
      written; the members **are** addressable, via
      `SDK_VERSIONED_ARTIFACT_CLASSES`. The assertion is `not in
      SDK_ARTIFACT_CLASSES`, i.e. not *typed*-registerable, which is a
      different statement **(found by this plan's re-run)**

  **In `tools/` — two modules. ALL FIXED by plan 15.1-20 (2026-08-06); listed
  so the record shows what was there.** The register previously enumerated
  **four** sites here and called them the live remainder; the docstrings were
  read whole, as this entry instructed, and there were **seven**:
  - `tools/dump_schemas.py` `author_versioned_classes` summary line — *"SDK-owned
    classes a manifest deliberately cannot address"*. False: a manifest may name
    all six as `registration: versioned`. Now *"The **author-versioned** SDK-owned
    classes"*.
  - the same docstring's *"`register_typed`, which does **not** run that check,
    so these classes are deliberately absent from `SDK_ARTIFACT_CLASSES`: a
    manifest entry naming one would silently drop the governance the class exists
    to carry."* The **canonical statement** of the superseded claim in the tree —
    the docstring the two `tests/cli/` sites were written against. Corrected in
    place with the withdrawn wording quoted and marked, the pattern plan 15.1-19
    established.
  - the same docstring's *"What they do not get is manifest addressability"*
    (verification **N-3**; enumerated by no prior round).
  - `tools/dump_schemas.py` `schema_owned_classes` — *"manifest-addressable
    classes, the author-versioned ones, and the unaddressable remainder"*, which
    is the N-3 conflation at **vocabulary** level: it uses "manifest-addressable"
    as a synonym for `SDK_ARTIFACT_CLASSES` membership. Now typed-registerable /
    versioned-registerable, the vocabulary `ccf.deployment.classes` already uses.
  - `tools/dump_schemas.py` `emit` — the same conflation, same fix.
  - `tools/check_schema_headers.py`'s module docstring — *"a manifest must not
    register them … the `register_versioned` bump check that `load_and_boot` does
    not run"*. Both clauses false; corrected with the withdrawn wording marked.
  - `tools/check_schema_headers.py`'s in-body comment — *"the author-versioned
    ones a manifest deliberately cannot carry"*.

  Left standing in `tools/dump_schemas.py` because they are **TRUE**:
  `unaddressable_classes`'s *"none is manifest-addressable"* and the
  *"an SDK contract question about manifest addressability"* that follows it —
  those five classes are in neither SDK mapping and a `ccf.`-prefixed id in
  neither is refused (D-IMPL-84). A sweep must not edit them.

  **In `public/` — three pages, four sites. ALL FIXED by plan 15.1-20
  (2026-08-06).** This tree was named by **no round of this sweep** and appears
  nowhere in this entry before today; it is `docs_dir` for mkdocs, so these were
  the pages an adopter reads first. Verification finding **N-2**:
  - `public/tutorial/demo-walkthrough.md` — *"`load_and_boot` registers through
    `register_typed`, which does not run that check — so those three classes are
    deliberately not manifest-addressable"*. The canonical claim verbatim, in
    published documentation.
  - `public/tutorial/adopters-guide.md` — *"one of the four author-versioned
    classes a deployment manifest deliberately cannot name … The manifest's
    registration path does not run that check"*. Also corrected "four" to the six
    the SDK actually ships, since `SDK_VERSIONED_ARTIFACT_CLASSES` has six
    members and example 05 registers four of them.
  - `public/tutorial/adopters-guide.md`, the agent-basics section — *"That check
    is the reason those two registrations stay in adopter code."* The **I-1
    rationale defect verbatim** — a choice stated as a necessity — in
    adopter-facing prose.
  - `public/how-to/compose-a-workflow-with-hitl.md` — *"they register through the
    version-bump check that the manifest path does not run"*. **The site no
    line-scoped grep finds** (see the method note above).

  Left standing in `public/` because they are **TRUE and unrelated**:
  `charter.md`'s *"deliberately not made non-blocking"*,
  `concepts/pillars/experience.md`'s *"deliberately not signal ingestion"*, and
  `how-to/swap-the-artifact-store.md`'s *"The store is deliberately not a
  manifest field"*.

  **In `examples/01`–`04` — STILL OPEN, and the enumeration below this entry is
  a subset.** Measured 2026-08-06 by plan 15.1-20; not fixed, because correcting
  eight example directories is beyond a plan scoped to the guard plus `public/`
  and `tools/`. **Two sites appear in no prior list at all**, both the same
  sentence in the same kind of file:
  - `examples/01-agent-basics/artifacts/agent-definition.yaml` — *"`load_and_boot`
    registers through `register_typed`, which does not."*
  - `examples/04-cross-process/artifacts/agent-definition.yaml` — the same
    sentence, one clause longer.

  And several listed spans **start earlier than the register says**: the false
  paragraph in `examples/01-agent-basics/artifacts/manifest.yaml` opens at
  *"What this manifest deliberately does not carry"*, several lines above the
  line the list names, and the same is true of
  `examples/02-skilling/artifacts/manifest.yaml` and
  `examples/04-cross-process/artifacts/producer-manifest.yaml`. A follow-up
  correcting only the named lines leaves the paragraph's opening claim standing.
  **That is the sixth under-count of this same enumeration.**

  **In `docs/surface-changes/` and `docs/SURFACE-CHANGES.md` — STILL OPEN, and
  NOT classified here.** The paragraph-scoped sweep returns 38 candidate sites
  across those two surfaces. Five of the ones this entry does *not* already name
  were opened (`15-14-examples-01-02.md:49`, `15-17-example-06.md:15`,
  `15-19-example-05.md:14`, `docs/SURFACE-CHANGES.md:369`,
  `15-08-operator-parameters.md:128`) and **all five are true statements** — so
  the extra hits are the sweep's wider phrasings, not necessarily extra defects.
  Per-site classification of the remaining candidates was **not** done, and this
  entry does not claim it was. These are dated per-plan records; whether they are
  corrected or annotated is the judgment this entry has always said it is.

  **A borderline sentence family, checked and deliberately left.** *"A class the
  SDK ships that a manifest cannot address is a class no adopter can register"*
  appears at `src/ccf/deployment/classes.py` (twice, on
  `SDK_ARTIFACT_CLASSES` and on the `PROJECTION_REQUIREMENTS` entry),
  `tests/deployment/test_class_lookup.py`, `docs/surface-changes/15-08-operator-
  parameters.md` and its `docs/SURFACE-CHANGES.md` mirror. Read as the rationale
  for *that mapping's* completeness rule it is true; read as a universal it is
  now false, because an author-versioned class is outside that mapping and is
  still registerable. No finding has named it, and rewriting `src/` prose no
  finding named is how a sweep turns a correct sentence into a wrong one — the
  hazard this entry's "checked and left" set exists for. **Recorded for a ruling,
  not fixed.**

  **Is this list exhaustive? No — it is a LOWER BOUND, and this is the sixth
  round to say so.** What can be said precisely, and nothing beyond it: ten
  claim-specific phrasings were run **paragraph-scoped** over **every** tracked
  tree; `public/`, `tools/`, `src/`, `runtime/` and `tests/` had every hit opened
  and read; `examples/` had every hit opened and read; `docs/` and `.planning/`
  did not. The phrase list remains the residual risk — it has under-counted four
  times before, twice by missing a second vocabulary and once by inverted word
  order — and no phrase list can find a paraphrase. The one thing that is *not*
  still a risk is the line boundary, which this round removed.
- **Found during:** plan 15.1-15 (post-gate review WR-F6), while finishing the
  sweep 15.1-12 recorded as complete
- **ENUMERATION CORRECTED — 2026-08-06, plan 15.1-16 (post-gate review WR-03).**
  The list first written here was **itself a subset**, which is the third time
  in this phase that a sweep of this claim has under-counted. It is now the
  output of re-running the phrasings over `examples/01..04` and `docs/` rather
  than a transcription, and the review's own list of what was missing was a
  subset too — it named seven sites; the re-run returns **nine additions**, the
  two it did not name being in `docs/surface-changes/15-19-example-05.md`.
  Everything below carries a measured file and line.
- **What:** two claims the SDK has superseded are still asserted in example
  directories and in the per-plan surface records:

  1. **D-IMPL-85.** *"A manifest entry naming an author-versioned class would
     silently drop the governance."* False since 15.1-02: a manifest **may**
     name all six author-versioned classes as `registration: versioned`, and
     `refuse_registration_the_sdk_fixes` refuses `typed` for them at preflight.
     Surviving in `examples/` at:
     - `examples/01-agent-basics/run.py`'s module docstring — *"Routing them
       through the manifest would silently drop that check"*
     - `examples/01-agent-basics/run.py::run`, the `[start:agent-artifacts]`
       block — *"A manifest entry for either would drop that check silently."*
       **(added 2026-08-06; the register carried the module docstring only)**
     - `examples/01-agent-basics/README.md:126-128`
     - `examples/01-agent-basics/artifacts/manifest.yaml:18`
     - `examples/01-agent-basics/artifacts/agent-registration.yaml:10`
     - `examples/02-skilling/artifacts/manifest.yaml:23-25`
     - `examples/03-harness-portability/run.py::decision`
     - `examples/03-harness-portability/artifacts/manifest.yaml:21-25`
     - `examples/03-harness-portability/artifacts/prompt.yaml:15-20`
       **(added 2026-08-06)**
     - `examples/03-harness-portability/artifacts/agents/agent-definition.yaml:21-25`
       **(added 2026-08-06)**
     - `examples/04-cross-process/artifacts/producer-manifest.yaml:23`
     - `examples/04-cross-process/artifacts/agent-registration.yaml:10`
     - `examples/04-cross-process/producer_child.py::AGENT_DEFINITION_DOCUMENT`
       — *"which `load_and_boot` does not do"*, unqualified, and therefore false
     - ~~`examples/04-cross-process/producer_child.py::build_covenant_slice_product`~~ **REMOVED
       2026-08-06, plan 15.1-17 (fourth review, IN-02.1): as written it is
       TRUE.** It says *"`load_and_boot`'s `register_typed` path does not"* —
       scoped to `register_typed`, which is exactly the wording
       `15.1-15-SUMMARY.md:266-268` sets aside as a true statement that must
       not be edited to match the pattern. Verified against the file
       2026-08-06. Moved to the checked-and-left set below, so the follow-up
       does not "fix" a correct sentence into a wrong one
     - `examples/01-agent-basics/run.py::AGENT_DEFINITION_DOCUMENT` — **added 2026-08-06, plan
       15.1-17 (IN-02.2), and added as a NAVIGATION site rather than a false
       one.** *"the manifest deliberately does not carry … See the module
       docstring"* is true as written and is the **seventh phrasing** below; it
       forwards to the module docstring, which is listed above and is false. Its
       exact analogue `examples/04-cross-process/producer_child.py::AGENT_DEFINITION_DOCUMENT`
       appeared in both
       the site list and the seventh-phrasing sentence while this one appeared
       in neither, and the asymmetry is what a follow-up working from this list
       trips over. Nothing is lost by leaving the line itself alone; it is
       listed so the forward is followed

  2. **D-IMPL-84.** *"Naming them here would resolve them to the open
     envelope."* False on two counts. For an author-versioned class,
     `resolve_artifact_class` returns the **real** class (verified against the
     function). For `ccf.hitl-policy` / `ccf.scope-mapping`, the reserved-prefix
     rule **refuses** the entry at load rather than enveloping it. Surviving in
     `examples/` at **three** sites, not one — the register previously said
     *"Surviving at `03/artifacts/manifest.yaml:23`"*, singular, and that was
     wrong:
     - `examples/03-harness-portability/artifacts/manifest.yaml:23`
     - `examples/03-harness-portability/artifacts/prompt.yaml:18-20`
       **(added 2026-08-06)**
     - `examples/03-harness-portability/artifacts/agents/agent-definition.yaml:24-25`
       **(added 2026-08-06)**

     The two additions matter more than the count suggests: they are the
     **forwarded-to** documents for that directory — the construction WR-F6 was
     written about — and each asserts *both* claims in one sentence.

- **In `docs/`, per-plan records** (dated records of what a plan did at the
  time, so whether they are *corrected* or *annotated* is a judgment, not a
  mechanical fix). Claim family in brackets:
  - `docs/surface-changes/15-14-examples-01-02.md:209` [85]
  - `docs/surface-changes/15-15-examples-03-07.md:31-33` [85]
  - `docs/surface-changes/15-16-example-08.md:29-40` [85]
  - `docs/surface-changes/15-17-example-06.md:38` [85]
  - `docs/surface-changes/15-17-example-06.md:255` [84] **(added 2026-08-06)**
  - `docs/surface-changes/15-18-example-04.md:293` [85] **(added 2026-08-06)**
  - `docs/surface-changes/15-19-example-05.md:22` and `:35-36` [85]
    **(added 2026-08-06 — named by neither the register nor the review)**
  - `docs/surface-changes/15-19-example-05.md:44-46` [84]
    **(added 2026-08-06 — named by neither the register nor the review)**
  - `docs/surface-changes/15-19-example-05.md:237` [84] **(added 2026-08-06)**

- **In `docs/SURFACE-CHANGES.md`, the assembled mirror** — four lines, where the
  register named two. Only bullet-shaped fragment lines are mirrored, which is
  why the prose sites above have no counterpart here:
  - `:1605` [85] — mirrors `15-14-examples-01-02.md:209`
  - `:3207` [84] — mirrors `15-17-example-06.md:255` **(added 2026-08-06)**
  - `:3626` [85] — mirrors `15-18-example-04.md:293` **(added 2026-08-06)**
  - `:3806` [84] — mirrors `15-19-example-05.md:237`

- **Checked and left, because they are TRUE.** A deployment-authored class id
  *does* resolve to the open `DeclaredArtifact` envelope, and every line saying
  so is correct: `docs/surface-changes/15-06-class-lookup.md:37`,
  `15-08-operator-parameters.md:182`, `15.1-03-namespace-reservation.md:46`
  and `:129`, `15-13-example-00.md:138`, `:168` and `:179`,
  `15-16-example-08.md:172`, `15-18-example-04.md:102` and `:323`, plus their
  mirrors at `docs/SURFACE-CHANGES.md:53`, `:1206`, `:1556`, `:1944`, `:2113`,
  `:2833`, `:3397`, `:3662`, `:4225`, `:4361` and `:4372`. Also true and
  unrelated: `examples/03-harness-portability/artifacts/live.yaml:14-17`, whose
  *"Not a manifest entry, deliberately"* is about the opt-in live legs, not
  about registration governance. **A sweep must not edit these to match the
  pattern.**

  **EXTENDED — 2026-08-06, plan 15.1-17 (fourth review, IN-02.1 and IN-02.3).**
  The set above was scoped to `docs/` plus one example file, so six further
  true lines a sweep could wrongly "fix" were unlisted. Each was read against
  the file on 2026-08-06 rather than carried over from the review:

  - `examples/04-cross-process/producer_child.py::build_covenant_slice_product`
    — moved here from the false-claim list; scoped to `register_typed`, and true.
  - `examples/01-agent-basics/artifacts/policy-bundle.yaml:10`
  - `examples/01-agent-basics/artifacts/agent-debt-profile.yaml:13`
  - `examples/02-skilling/artifacts/policy-bundle.yaml:12`
  - `examples/03-harness-portability/artifacts/policy-bundle.yaml:12`
  - `examples/04-cross-process/artifacts/agent-debt-profile.yaml:10`

  The five artifact lines each say that a **deployment-authored** class takes
  the open `DeclaredArtifact` envelope, which is what D-IMPL-84 still says and
  is unaffected by its supersession — that supersession is about SDK
  author-versioned classes and the reserved-prefix refusal. They read close
  enough to the superseded phrasing to attract a mechanical sweep, which is the
  whole reason this set exists.

- **A seventh phrasing, which the six-phrasing list in `15.1-15-SUMMARY.md` does
  not contain:** *"the manifest deliberately does not name"* /
  *"Not a manifest entry, deliberately"* / *"absent from `SDK_ARTIFACT_CLASSES`"*
  / *"`load_and_boot` … does not"*. It is how
  `examples/04-cross-process/producer_child.py::AGENT_DEFINITION_DOCUMENT`,
  `examples/01-agent-basics/run.py::AGENT_DEFINITION_DOCUMENT` **(added 2026-08-06, plan 15.1-17 —
  IN-02.2; the exact analogue of the `producer_child.py` line beside it, and
  absent here as well as from the site list)**,
  `examples/03-harness-portability/artifacts/manifest.yaml:16` and both example-03
  forwarded-to documents spell it, and none of the six finds it. Add it to the
  input list before the follow-up starts.

- **Why it was not fixed here:** plan 15.1-15's scope is `examples/05`, `06`,
  `08` and the two example test modules; plan 15.1-16's scope is
  `tests/products/` plus this register. Editing examples 01–04 in either
  worktree risks colliding with concurrent work and exceeds what was asked.
- **Where it belongs — REWRITTEN 2026-08-06, plan 15.1-20, after `public/` and
  `tools/` were closed.** What is left is **one follow-up over `examples/01`–`04`
  plus a ruling on the `docs/surface-changes/` dated records**, and nothing else
  this entry knows of.

  **Run the sweep paragraph-scoped, not line-scoped.** That single change is what
  found the `public/how-to/` site four rounds of line-scoped grepping could not
  see, and it costs nothing: join the file into one whitespace-normalized string,
  match there, map the offset back to a line. The seven phrasings are still the
  input — the six in `15.1-15-SUMMARY.md` plus the seventh above — and note that
  `examples/01-agent-basics/README.md` and `examples/02-skilling`'s manifest
  spell it *"drop it silently"*, which a search for *"silently drop"* does not
  find, and that `examples/01-agent-basics/run.py` spells it *"drop that check
  silently"*, which neither finds.

  **The canonical statement is no longer in `tools/`.** It was
  `tools/dump_schemas.py::author_versioned_classes`, and plan 15.1-20 corrected
  it, so a site still echoing it is now echoing nothing that is still in the
  tree. The corrected wording to converge on is what
  `examples/05-workflow-hitl/artifacts/manifest.yaml`,
  `examples/08-e2e-demo/artifacts/manifest.yaml` and the three corrected
  `public/` pages now carry: *a manifest **may** name an author-versioned class,
  as `registration: versioned`, and `load_and_boot` dispatches that entry to
  `register_versioned` with its bump check; what is refused, at preflight, is
  `registration: typed` for such a class. The four (or three, or two) stay in
  adopter code by the example's choice, so the check is visible at the call
  site.*

  **Correct whole paragraphs, not the enumerated lines.** Several spans in this
  entry start above the line they name (see the measured note in the scope
  section). Read each document's header comment whole.

## A loop-carried rebinding is out of the Gate-2 tripwires' reach (R4-WR-03)

- **Source review document:** `15.1-REVIEW-FIXES-3.md` **WR-03** (round 4).
  Deliberately not re-reported in round 5 per the brief
  (`15.1-REVIEW-FIXES-4.md:502`), and round 5 relies on it being open — WR-01 is
  classified Warning rather than Critical precisely because its trigger is
  *strictly less reachable* than this one. **OPEN.**
- **Found during:** the fourth post-gate review (`15.1-REVIEW-FIXES-3.md`,
  WR-03), re-measured at plan 15.1-17 before and after that plan's change
- **What:** both tripwires in `tests/products/test_gate_two_call_shape.py`
  resolve a name to *the binding textually last before the position that reads
  it*. That is the right answer for straight-line code and the wrong one for a
  loop, which makes lines execute out of source order. Measured 2026-08-06,
  driving the shipped `_binder_collapses`:

  ```python
  plan = FixturePlan(plan_id=pid, required=requirements.required_operator_keys)
  refuse_operator_set_divergence(declared=declared, plan=plan)
  for item in alts:
      out = ProjectionEngine(reader=r).execute(plan=plan)
      plan = FixturePlan(plan_id=pid, required=declared.required_operator_keys)
  ```

  → **0 problems**. From the second iteration on the engine runs the plan built
  from the binder's own `declared=`, which no binder was handed — CR-03
  variants 1 and 2 at once. The `while` spelling measures identically, and the
  tripwire-(1) form (a lineage read at the top of a loop whose `ops` is rebound
  at the bottom) has the same shape.
- **Why it was not fixed at 15.1-17:** closing it needs **control-flow**
  ordering rather than lexical ordering — a fixed point over a loop body, which
  is a different analysis from the single-pass AST walk this module is, and one
  whose termination argument would have to be rebuilt from scratch (two
  predecessors of `_resolve_at` failed exactly there, one of them by hanging
  `pytest` with no output). 15.1-17's scope was the certification defect and the
  comprehension regression; inventing a dataflow analysis inside it would have
  been the scope creep this phase has been penalised for.
- **What 15.1-17 did instead:** named it in **both** limits lists in the module
  docstring, in the threat table of `15.1-16-SUMMARY.md`, and asserted it *as a
  limit* in `test_a_loop_carried_rebinding_is_out_of_reach_and_says_so` — which
  fails if a later change closes it, so the docstrings and this entry get
  corrected in the same commit rather than quietly becoming false. The
  straight-line spelling of the identical rebinding is asserted **caught** in
  the same test, so the silence is a statement about control flow and not about
  the check having gone quiet.
- **Where it belongs:** Phase 16, beside R-3 and the D-IMPL-86 adopter-scope
  residual, which is where the binder's own module docstring already carries the
  question of what an AST gate can and cannot hold.

## `_Binding.until` covers the comprehension's outermost iterable, which Python evaluates in the enclosing scope (R5-WR-01)

- **Source review document:** `15.1-REVIEW-FIXES-4.md` **WR-01** (the fifth and
  final round, 0 Critical / 2 Warning / 4 Info). **OPEN — accepted as a residual
  at the re-approval (D-GATE-15.1, 2026-08-06), explicitly not closed by it.**
- **What.** Python's comprehension scope **excludes the outermost iterable**: it
  is evaluated in the enclosing scope and passed in as an argument. `_Binding.until`
  is `_after(node)` over the whole comprehension node, and `_at(node)` is its `[`,
  so the outermost iterable sits *inside* the recorded span and `_binding_before`
  attributes its reads to the comprehension's own target. The class docstring of
  `tests/products/test_gate_two_call_shape.py::_Binding` says containment in that
  span "is exactly Python's scope rule". **It is not**, and
  `tests/products/test_gate_two_call_shape.py::_binding_before`'s "in force for
  reads *lexically inside* the comprehension … and for no other read" is wrong
  in the same direction.
- **Measured bidirectionally, with renamed-target controls, against `6cf00d3`.**
  Both consequences were produced by driving the *shipped* helpers, not argued:
  - **(a) A genuine Gate-2 collapse goes silent.** `[x for ops in
    run_gates(candidate, engine_resolved=ops)]`, where both sides read the same
    prior `ops` — CR-2's shape exactly — measures `6cf00d3` **REJECT** →
    `aedf81b` **ADMIT** → now **ADMIT**. Control (target renamed to `y`, nothing
    else changed): REJECT on all three.
  - **(b) Correct code is reported red.** `[row for plan in
    wrap(ProjectionEngine(reader=r).execute(plan=plan))]`, where the engine runs
    the **outer** plan the binder was handed, measures `6cf00d3` **ADMIT** →
    `aedf81b` **REJECT** → now **REJECT**. Control: ADMIT on all three. The
    multi-line spelling measures the same, so it is not a one-liner artifact.
  - It is therefore a **regression against `6cf00d3` in both directions** — the
    same shape and the same predecessor comparison as the R4-WR-01 that round 4
    fixed.
- **Why the reviewer classified it Warning and not Critical, recorded because it
  is why the phase closes with it open.** WR-01's trigger requires a
  comprehension whose target *shadows the very name read in its own outermost
  iterable*, with the gate or engine call inside that iterable. That is
  **strictly less reachable** than R4-WR-03 (the loop-carried rebinding), which
  this phase deliberately leaves open with Dave's knowledge. In the reviewer's
  own words: *"A finding cannot be Critical while a more reachable sibling is an
  accepted open item; calling it one would be inconsistent, not rigorous."* The
  classification was reasoned to on that ground and not to make the phase
  closable.
- **Why it was not fixed:** the round-5 review names two candidate fixes — a
  structural one (anchor the first generator's target at
  `_after(node.generators[0].iter)`, leaving later generators' targets at
  `_at(node)` since their iterables *are* in comprehension scope) and a
  minimum-honest one (withdraw the two over-claiming sentences, add the entry to
  both limits lists with the two measured bodies, add a threat row, correct
  `15.1-17-SUMMARY.md:204-205` and `:401`) — and **certifies neither**, having
  measured neither as a patch. Given this phase's history of proposed remedies
  that recreate the defect one layer down, applying an unmeasured remedy at the
  gate would have been the same mistake a sixth time.
- **What is owed whichever way it goes:** the sentence at `:823-824` cannot stay
  as written. A check that claims an exactness it does not have is the one defect
  shape this phase produced in all five rounds. The remedy belongs to whoever can
  measure it against the outermost-iterable **walrus** case, which the reviewer
  explicitly did not.
- **No body in the tree uses either shape** — 0 problems on both tripwires, 9 / 11
  / 11 / 11 readable / 0 unreadable under both `aedf81b` and HEAD — so `make ci`
  being green does not contradict any of the above. A gap cannot fail itself.
- **Where it belongs:** Phase 16, beside R4-WR-03, R-2 and R-3.

## `15.1-17-SUMMARY.md:229`'s before-column did not measure — and the claim-discipline lesson behind it (R5-WR-02)

- **Source review document:** `15.1-REVIEW-FIXES-4.md` **WR-02** (round 5).
  **Accepted as a recorded OPEN residual at the re-approval (D-GATE-15.1,
  2026-08-06) — not closed by it.**
- **The error itself is CORRECTED, in place and marked, 2026-08-06** as part of
  the re-approval task: `15.1-17-SUMMARY.md:229`'s before-column read **ADMIT**
  where `aedf81b` measures **REJECT** — via property (2), for the wrong reason
  (`handed` resolved to `None`, so the execution read as unbound). The verdict
  did not change between predecessor and HEAD; the **diagnosis** did, moving from
  *"the engine runs a plan no binder was handed"* to *"the binder's two sides are
  one document"*. Rows 1 and 3 of the same table reproduce exactly. A marked
  `CORRECTION` block now sits under the table and `:432`'s success-criterion row
  is re-scoped in place.
- **What stays open is not the cell — it is the discipline finding.** `:432`
  claimed *"Every number in this SUMMARY is one I ran."* One number in it was
  reasoned to rather than run, inside a round whose entire §6 exists to correct
  records that asserted more than the code did, and whose §7 pattern note reads:
  *"A limit that is named in a docstring and not held by a test is a sentence
  that can silently stop being true."* The same applies to a figure in a table
  that was not measured. **Nothing structural prevents the next such claim** — no
  gate holds a SUMMARY's tables to being scripted output, and inventing one is
  not this phase's work.
- **Where it belongs:** Phase 16, as a writing rule rather than a code change —
  a record that claims every figure was measured must either be scripted output
  or must scope the claim to what was.

## The augmented-assignment unreadability (`ops |= x`) is accepted and unclosable by an AST walk

- **Source review documents:** raised across the binding-model rounds and carried
  as a *stated module limit* rather than a fix —
  `15.1-REVIEW-FIXES-2.md` **CR-01** (which closed the *rebinding* half),
  `15.1-16-SUMMARY.md`'s threat table, `15.1-17-SUMMARY.md:412`, and excluded
  from re-report by both later rounds (`15.1-REVIEW-FIXES-3.md:561`,
  `15.1-REVIEW-FIXES-4.md:502`). **OPEN, and open by decision.**
- **What:** `ops |= x` records an **unreadable** binding, so a body that mutates
  the lineage's own set *in place* and hands it to the gate is **ADMITTED**. The
  augmented-assignment *rebinding* spelling is REJECTED (`15.1-16-SUMMARY.md:181`);
  what survives is the **mutable-set** case.
- **Why it is not closable by the mechanism family in use:** no AST walk can tell
  the mutable case from the rebinding one, and recording the pre-`|=` path
  instead would emit a message that is **untrue**. Recorded rather than repaired
  is the correct disposition, and the module's limits list says so.
- **Where it belongs:** with R4-WR-03 and R5-WR-01 in Phase 16's account of what
  the Gate-2 tripwires can and cannot hold. It is a stated limit, not a silent one.

## Attribute and subscript targets are unfollowed — never misfollowed, except from a nested body

- **Source review documents:** stated as a module limit at
  `tests/products/test_gate_two_call_shape.py`'s module docstring; the exception found by
  `15.1-REVIEW-FIXES-4.md` **IN-02** (round 5). Excluded from re-report by rounds
  4 and 5 as a standing item (`15.1-REVIEW-FIXES-3.md:561`,
  `15.1-REVIEW-FIXES-4.md:502`). **OPEN.**
- **What:** a write to an attribute or a subscript (`self._ops = …`, `d['a'] = …`)
  is not followed. A read of such a path resolves to the literal path, so the
  write is **unfollowed, never misfollowed** — the conservative direction, and
  the limits list states it.
- **The exception round 5 measured.** The bullet extends the same "likewise …
  unfollowed, never misfollowed" framing to `global` / `nonlocal`, and that
  extension is **inaccurate when the redirected assignment lives in a nested
  body**: the assignment is recorded in the body that contains it, so the
  enclosing body's stale binding stays in force and answers affirmatively — the
  CR-01 inversion. Measured: a `nonlocal plan; plan = alt` inside a nested `def`,
  between a compliant binder call and an `execute`, is **ADMIT** on both
  `aedf81b` and HEAD; the `global` spelling measures identically. Round 3's note
  that "the nested body is itself a projecting body" holds only when the nested
  body *constructs* a plan, which this one does not. The same reservation applies
  to `from m import *`, which `_binding_records:949` skips and which at module
  level can displace a binding and leave the previous one answering.
- **Why it was not fixed:** both shapes are contrived, and the remedy is one
  clause of docstring in the same register as the R4-WR-03 paragraph beneath it —
  a wording debt, not a mechanism debt. It was not written in round 5 because no
  file was modified during that review.
- **Where it belongs:** Phase 16, with the other limits-list corrections R5-WR-01
  also owes.

## Three `src/` boundary-validation Infos, deliberately deferred (IN-F1 / IN-F2 / IN-F4)

- **Source review document:** `15.1-REVIEW-FIXES.md` **IN-F1**, **IN-F2**,
  **IN-F4** (round 2, the CR-01/CR-02 fix review). Explicitly excluded from
  re-report by rounds 4 and 5 as "`src/`, deliberately deferred"
  (`15.1-REVIEW-FIXES-3.md:561`, `15.1-REVIEW-FIXES-4.md:502`). **All three
  OPEN.**
- **IN-F1 — `path: ""` and `path: "."` pass both containment checks.**
  `PurePosixPath("").parts` and `PurePosixPath(".").parts` are both `()`, so
  neither is absolute, rooted, drive-qualified or `..`-bearing, and
  `(anchor / "").resolve()` is `anchor`, which `is_relative_to(anchor)`. Both are
  ADMITTED at preflight and fail at the read with `IsADirectoryError`, which is
  **not among `load_and_boot`'s documented `Raises:`** — and CLAUDE.md §11 puts
  validation at the boundary. Not a security issue: the read fails and nothing is
  registered. Closable in two lines
  (`Annotated[str, StringConstraints(min_length=1)]` on
  `src/ccf/controlplane/artifacts.py`'s `path` field, plus a `resolved.is_file()`
  check in `_document_inside_the_deployment`).
- **IN-F2 — a hardlink inside the deployment to a file outside it is admitted.**
  `Path.resolve()` follows symlinks and cannot see hardlinks; measured against a
  real deployment directory, an outside file's contents were read. The
  precondition is write access inside the deployment tree, which is also enough
  to copy the file, so the practical gain is narrow — hence Info. What is owed is
  a clause in `_document_inside_the_deployment`'s docstring, which currently says
  *"what is in force is the deployment's own tree, not whatever that tree points
  at"* — a hardlink is **neither**, and the sentence reads as if it were covered.
- **IN-F4 — the two-flavour rule refuses the legal POSIX filename `a:b.yaml`.**
  `PureWindowsPath("a:b.yaml").drive` is `'a:'`, so a one-character stem followed
  by a colon reads as drive-qualified on Linux and is refused. This is a **direct
  and accepted consequence** of the platform-invariance decision, which the
  reviewer agreed with; the defect is only that the cost is stated nowhere. One
  clause in `_leaves_its_own_directory`'s docstring makes it a recorded trade
  rather than a surprise.
- **Also recorded, and deliberately not carried as an item:** **IN-F3** (TOCTOU
  between preflight resolution and the phase-one read) — the reviewer *could not
  construct a case that does not already presuppose write access inside the
  deployment tree*, at which point the attacker can write the content directly.
  If it is ever judged in scope the mitigation is `os.open(..., O_NOFOLLOW)` on
  the final component, not a wider check.
- **Why none was fixed:** all three are `src/` changes to the boundary-validation
  surface, and every round after round 2 was scoped to the tripwire modules with
  **no `src/` change at all** — a property each of those reviews verified and
  relied on. Widening scope to `src/` inside a remediation round would have been
  the scope creep this phase has been penalised for.
- **Where it belongs:** Phase 16, or a small hardening plan of their own. IN-F1
  and IN-F4 are two-line changes plus docstrings; IN-F2 is a docstring clause
  unless Dave rules the hardlink case in scope.

## Cross-file `file.py:NNN` citations go stale silently, and nothing in CI holds them (W-1 / W-5)

- **Source review document:** `15.1-VERIFICATION.md` findings **W-1** and **W-5**,
  extended by **N-1** and **N-4**. **STATUS 2026-08-06: TOOLED and green — the
  class now has a CI gate (`tools/lints/citations.py`), and every instance the
  gate reaches is corrected. It is not CLOSED: the gate reaches anchored and
  symbol citations, and the tree carries 97 unanchored ones it cannot hold. See
  the coverage figures below rather than reading the green gate as the whole
  answer.**
- **Found during:** phase verification (2026-08-06), then extended by plan
  15.1-19's sweep of every `file:line` citation in the phase-touched trees
- **What:** a docstring citing another file as `path/to/file.py:NNN` is a claim
  with a short shelf life. Nothing — no lint, no test, no CI gate — holds such a
  citation to pointing at what it names, so a plan that edits a cited file
  silently falsifies every docstring citing it. **This phase moved cited lines
  three times and swept the citers zero times.**
- **The seven instances, all corrected by plan 15.1-19:**
  - `src/ccf/deployment/binder.py` — *"the signature spans lines 181-188 in the
    tree as it now stands"* for `load_and_boot`, which spanned `manifest.py:248-255`
    where it stood in the tree the correction was written against; 181-188 was
    inside `_document_inside_the_deployment`. **The only one in shipped
    `src/` phrased in the present tense** (W-1).
  - `src/ccf/deployment/__init__.py` — cited
    `src/ccf/controlplane/artifacts.py:47` for the `__ccf_mode__` tag — both
    numbers as they stood in the tree the wrong citation was written against,
    where the tag was in fact at `:84`. **A second false citation in shipped `src/`; the verification report
    states binder.py was the only one, and that was itself an under-count.**
    (Found by plan 15.1-19.)
  - `tests/products/test_gate_two_call_shape.py`, `tests/deployment/test_binder.py`,
    `tests/deployment/test_class_lookup.py` — all three cited
    `test_gate_independence.py:184-187` (the `_candidate` helper's signature) for a
    discipline sentence at `:213-215` — both as they stood in the tree the wrong
    citation was written against (W-5).
  - `tests/examples/test_gate_two_divergence.py` — cited
    `test_gate_independence.py:179` (an `assembly_mode=` keyword argument) for a
    perturbation at `:208-232` — both as they stood in the tree the wrong
    citation was written against (W-5).
  - `tests/products/test_gate_two_call_shape.py` — cited
    `test_required_operators_guard.py:260-262` (about which *spellings* are
    exercised) for the probe-assembly discipline at `:264-267` — both as they
    stood in the tree the wrong citation was written against. (Found by plan
    15.1-19; not in W-5.)
- **A citation was falsified by the act of fixing another one.** Plan 15.1-19's
  two-line docstring addition to `binder.py` moved the binder's comparison from
  `:156-159` to `:158-161`, staling three live citations inside
  `test_gate_two_call_shape.py` in the same commit that fixed five others. This is
  the strongest available argument that the class is structural rather than a
  lapse of care: the defect reproduced under an author actively looking for it.
- **Mitigation applied, short of tooling:** every corrected citation now names a
  **symbol or a pytest node id** (`module.py::test_name`,
  ``refuse_operator_set_divergence``'s comparison) instead of a line number. This
  is not a new convention — `tests/products/test_required_operators_guard.py::_refused_names`
  already cited a sibling test by name. Symbol citations break loudly under rename
  (grep finds zero hits) rather than silently under insertion.
- **A FOURTH reproduction, and it is what closed this entry.** Verification
  finding **N-1**: plan 15.1-19 applied its own lesson to `tests/` and caught the
  three citations it staled there; it staled **five more** it did not catch,
  because its sweep scope was the phase-touched trees and the live citers are in
  `docs/` and `.planning/` — two of them in **this file**, in the R5-WR-01 entry
  it was writing at the time.

- **TOOLED — 2026-08-06, plan 15.1-20. `tools/lints/citations.py`, wired into
  `python -m tools.lints --all`, so into `make lint`, `make ci-core`, `make ci`
  and the CI lint job.** The prediction in the paragraph above — feasible for the
  `::` form, "not feasible for prose line ranges" — was half right and the half
  it got wrong is the useful half:
  - `cite03-node-id` does what was predicted: a `file.py::symbol` citation must
    resolve to a `def`, `class` or module-level binding of that name.
  - `cite01-resolves` checks that a line citation's file exists and that the
    cited lines are inside it. Cheap, and it cannot be wrong about a file it
    resolved.
  - `cite02-anchor` is the one that was thought infeasible. A line citation with
    a backticked **anchor** immediately before it — separated by nothing but
    whitespace, opening punctuation and at most a locator word — must lie inside
    what the anchor names. That covers most citations that carry a claim, because
    a citation that means something is nearly always written next to the symbol
    it is about.
  - Historical citations pass: a citation whose own **sentence** carries a
    historicity marker or a git object id is exempt. Sentence-scoped rather than
    line-scoped, because one `.planning/REQUIREMENTS.md` paragraph opens by
    saying an earlier record's numbers have moved and then makes six
    present-tense citations of its own.
  - A fourth rule was prototyped and **rejected on measurement**: checking a
    quoted claim against the cited lines matched 7 sites tree-wide and failed 3,
    all 3 false positives (two from an abridged RST role, one from `#` comment
    prefixes inside the cited range). Recorded in the module docstring.

- **What the guard found on its first run, before anything was fixed** — three
  findings, all true positives, each opened and confirmed:
  `src/ccf/peering/admission.py` (verification **N-4**, a pre-existing stale
  citation in shipped `src/`), `.planning/REQUIREMENTS.md` (verification **N-1**),
  and `docs/surface-changes/15-06-class-lookup.md`, a node id naming a test that
  **exists nowhere in the tree** and that no prior round had named. All three are
  corrected; the gate is green.

- **What the guard still does NOT reach, stated so a green gate is not read as
  more than it is.** Measured by `python -m tools.lints --citations --report` on
  the tree as this plan leaves it: **163 citations matched** across 786 scanned
  files (258 further files exempt as dated records), **37 checked and passing**,
  **2 explicitly historical**, **0 findings**, and **124 unchecked** — 95 of them
  because they carry no anchor, 14 because the anchor resolves to nothing or to
  two things, 6 ambiguous paths, 9 unresolvable paths. The unanchored population
  is the
  bare-site-list shape this very file uses (`- \`examples/01-agent-basics/run.py:36\``),
  which has nothing to bind to. The guard also cannot see semantics, ambiguous
  bare filenames, extensionless targets (`Makefile:NNN`), bare `:NNN`
  continuations, or — most importantly — **a false claim carrying no citation at
  all**, which is the entire other half of this phase's defect set.

- **`docs/DECISIONS.md` is deliberately out of the gate's scope**, with the
  reason measured rather than assumed: gated, it produces **11 findings across
  nine dated entries**, one of them the entry explicitly marked "preserved
  **unedited**". A file whose record discipline forbids correcting a citation
  cannot be gated on citation freshness, and correcting 2 of 11 would leave a
  reader to infer the other 9 are current. A reader note in that file's
  **preamble** — not in any dated entry — now records the snapshot convention for
  all 63 of its citations. Phase documents under `.planning/phases/` are exempt
  on the same test; `deferred-items.md` is explicitly pulled back **in**, because
  it is the live hand-off contract.

- **Where it belongs:** the class is closed as far as a pointer-checker reaches.
  What is left for Phase 16 is authorial, and the guard makes it cheap to act on:
  run `python -m tools.lints --citations --report` and work the unanchored count
  down by converting bare line citations to `::` symbol form. The standing rule
  the earlier draft of this entry proposed is now enforced rather than proposed —
  but it is enforced only for anchored and symbol citations, so the rule still
  applies to the rest: **a plan that edits a file should sweep the tree for
  citations *of* that file before it commits, and `docs/` and `.planning/` are
  trees, not exceptions.**

## All 172 `registration:` values in the tree are `typed`; the `versioned` branch ships undemonstrated (I-1)

- **Source review document:** `15.1-VERIFICATION.md` finding **I-1** (info).
  **OPEN as a demonstrability gap — explicitly NOT a criterion failure.**
- **Found during:** phase verification (2026-08-06)
- **What:** every one of the 172 `registration:` values across every manifest in
  the tree is `typed`. **Zero declare `versioned`**, so `load_and_boot`'s versioned
  branch is exercised only by
  `tests/deployment/test_manifest.py::test_the_versioned_dispatch_runs_the_bump_check`
  and by no shipped example. Examples 05, 06 and 08 still register their
  author-versioned documents through hand-written `registry.register_versioned`
  calls — the two-mental-models split the converged CR-1 fix was framed as removing
  ("Everything stays in the manifest; one mental model").
- **Ruled on 2026-08-06 by plan 15.1-19, deliberately and with the reasoning
  recorded, because the verification report asked for an explicit decision:**
  **the examples are left exactly as they are.** Three reasons, in order of weight:
  1. **ROADMAP criterion 2 does not require it.** The criterion is that the mode is
     declared per entry and dispatched by `load_and_boot` — verified, and proven by
     a test that asserts the refusal fires rather than that examples avoid the
     pattern. An example adopting the path would be additional evidence for an
     already-verified criterion, not the closing of a gap in it.
  2. **Changing example behavior is new scope on an approved phase.** The gate is
     re-approved; moving four documents out of `run.py` and into
     `05/artifacts/manifest.yaml` is a behavior change to a shipped example, made
     after approval, to improve a demonstration rather than to fix a defect.
  3. **Example 05's own teaching choice argues against it, on the merits.** Its
     manifest states the reason: keeping the four `register_versioned` calls
     visible in `run.py` **is** the lesson, because the D-05 four-outcome table is
     what that example teaches and a manifest line hides it. The example that would
     most naturally demonstrate the declared path is the one with the strongest
     reason not to.
- **What was corrected instead:** the *rationale* in
  `tests/examples/test_workflow_hitl_output.py`, which asserted the four are
  outside the manifest by **necessity** ("the manifest path registers through
  `register_typed`"). That was false, and it made the residual look closed when it
  is a choice. It now says the reason is pedagogical and that the manifest path is
  available — so the residual is visible where a reader meets it.
- **Where it belongs:** Phase 16, as a demonstrability question, not a defect. The
  cheapest honest close is a **new** small example, or one manifest entry in an
  example with no competing teaching obligation — **not** an edit to 05.

## Three gate-checker tests fail, and `make ci` does not run them (found 2026-08-06, plan 15.1-20)

- **Found during:** plan 15.1-20, running `pytest tools/lints/tests
  tools/publish_scan_tests tools/docs_tests -q` — the three suites the CI **lint**
  and **docs** jobs run as their own steps. Out of that plan's scope and **not
  fixed**; recorded here per the scope-boundary rule.
- **What:** three failures, none of them reachable by `make ci`, because `make ci`
  composes `lint typecheck test examples docs-strict` and `[tool.pytest]
  testpaths` is `["tests"]` — so these three suites are run by
  `.github/workflows/ci.yml` and by nothing a developer runs locally.
  - `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text`
    — `ProductClassDeclaration`'s docstring in
    `src/ccf/controlplane/artifacts.py` trips the whitepaper-shingle scan with
    **20 shingle hits**.
  - `tools/docs_tests/test_snippet_gate.py::test_the_unmodified_source_builds_clean`
    and `::test_a_deleted_section_marker_fails_the_strict_build` — both expect an
    `[start:ontology]` snippet marker in `examples/00-quickstart/run.py`, which no
    longer carries one. The fixture reports it plainly: *"fixture drifted from its
    source"*.
- **Not caused by this plan, verified rather than assumed:** `git diff --name-only`
  against the phase base shows plan 15.1-20 touches neither
  `src/ccf/controlplane/artifacts.py` nor `examples/00-quickstart/run.py`.
- **Why it matters beyond the three:** the interesting part is the *gap*, not the
  failures. `make ci` is documented as "the full local reproduction of the
  always-on pipeline (D-10)", and for these three suites it is not — CI can be red
  on a step no local command runs. That is the same shape as every other finding
  in this phase: a claim (`make ci` ≡ the pipeline) that the mechanism does not
  support.
- **Where it belongs:** Phase 16. Two separable items — fix the three, and decide
  whether `make ci` should compose the gate-checker suites so the claim it makes
  becomes true.
