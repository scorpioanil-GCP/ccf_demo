# Deferred items — phase 15.1

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary. Plan 15.1-10 surfaces these to Dave at the phase gate.

**Status after the gate (D-GATE-15.1, Dave, 2026-08-05).** The phase is approved.
Dave's verbatim reply was **"Approved"** — one approval of the phase as presented,
not five separate written rulings on the five items the presentation put to him.
The three residuals below marked **carried forward** are therefore **open, accepted
at approval, and not closed by it**. They inherit to Phase 16.

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
     times**, at `examples/03-harness-portability/run.py:480`,
     `examples/04-cross-process/producer_child.py:438`,
     `examples/06-decision-replay/run.py:1109`,
     `examples/07-artifact-store-mcp/run.py:494`, and
     `examples/08-e2e-demo/run.py:1102`. Recorded in `D-GATE-15.1` as well, so
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
     any of its preflights (`src/ccf/deployment/manifest.py:177` as the correction
     cites it; the signature now spans `:181-188`). The SDK never invokes it.
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

## The superseded D-IMPL-85 / D-IMPL-84 claims survive in examples 01–04

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
     - `examples/01-agent-basics/run.py:36`
     - `examples/01-agent-basics/run.py:249-252` — *"A manifest entry for either
       would drop that check silently."* **(added 2026-08-06; the register
       carried `run.py:36` only)**
     - `examples/01-agent-basics/README.md:126-128`
     - `examples/01-agent-basics/artifacts/manifest.yaml:18`
     - `examples/01-agent-basics/artifacts/agent-registration.yaml:10`
     - `examples/02-skilling/artifacts/manifest.yaml:23-25`
     - `examples/03-harness-portability/run.py:247`
     - `examples/03-harness-portability/artifacts/manifest.yaml:21-25`
     - `examples/03-harness-portability/artifacts/prompt.yaml:15-20`
       **(added 2026-08-06)**
     - `examples/03-harness-portability/artifacts/agents/agent-definition.yaml:21-25`
       **(added 2026-08-06)**
     - `examples/04-cross-process/artifacts/producer-manifest.yaml:23`
     - `examples/04-cross-process/artifacts/agent-registration.yaml:10`
     - `examples/04-cross-process/producer_child.py:113-115` and `:268-270`

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

- **A seventh phrasing, which the six-phrasing list in `15.1-15-SUMMARY.md` does
  not contain:** *"the manifest deliberately does not name"* /
  *"Not a manifest entry, deliberately"* / *"absent from `SDK_ARTIFACT_CLASSES`"*
  / *"`load_and_boot` … does not"*. It is how
  `examples/04-cross-process/producer_child.py:113-115`,
  `examples/03-harness-portability/artifacts/manifest.yaml:16` and both example-03
  forwarded-to documents spell it, and none of the six finds it. Add it to the
  input list before the follow-up starts.

- **Why it was not fixed here:** plan 15.1-15's scope is `examples/05`, `06`,
  `08` and the two example test modules; plan 15.1-16's scope is
  `tests/products/` plus this register. Editing examples 01–04 in either
  worktree risks colliding with concurrent work and exceeds what was asked.
- **Where it belongs:** one follow-up that corrects examples 01–04 to the same
  wording examples 05/06/08 now carry, and rules on the `docs/surface-changes/`
  historical records. **The input is the seven phrasings** — the six in
  `15.1-15-SUMMARY.md` plus the seventh above — and the enumeration in this
  entry. Note in particular that `examples/01-agent-basics/README.md` and
  `examples/02-skilling`'s manifest spell it *"drop it silently"*, which a
  search for *"silently drop"* does not find, and that
  `examples/01-agent-basics/run.py:252` spells it *"drop that check silently"*,
  which neither finds.
