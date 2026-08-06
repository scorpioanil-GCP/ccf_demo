# Deferred items — phase 15.1

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary. Plan 15.1-10 surfaces these to Dave at the phase gate.

**Status at phase close (plan 15.1-10).** Items 1 and 2 below are recorded in
`docs/SURFACE-AUDIT.md` §6.4 item 1 and §6.5 respectively and are put to Dave at
the gate. Items 3 and 4 were found by this plan at phase close and are recorded
here for the first time. The two D-IMPL-86 residuals — **authorship** and
**placement** — are *not* in this file: they are mechanism residuals rather than
out-of-scope discoveries, and they live in `docs/SURFACE-AUDIT.md` §6.4 items 4
and 5 as two distinct carried items.

## The HTTP schema route still serves only the typed-registerable classes

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
- **Why it was not fixed here:** `.planning/ROADMAP.md` is orchestrator-owned in
  worktree mode and this plan is forbidden to write it. It is also not a defect
  this plan can close unilaterally — the sentence may be *intended* to count only
  the pre-15 phases, with 15/16/15.1 minting described separately immediately
  after, in which case the fix is to say "21 pre-Phase-15 requirements" rather
  than to change the number. Which reading is right is an editorial call.
- **Where it belongs:** the post-approval ROADMAP update this phase's gate
  triggers, or Phase 16. Either restate the sentence to name what it counts, or
  move the figure to 42 and drop the separate minting paragraph.

## Three Phase 15.1 acceptance criteria are wrong as written

- **Found during:** plan 15.1-10, phase close
- **What:** three literal checks in this phase's own plan text cannot be
  satisfied without gaming, and one of them would *undo* the phase's fix if it
  were. Fully written up in `docs/SURFACE-AUDIT.md` §6.3; in brief:
  1. `grep -rn "operators_invoked=execution.operators_invoked" examples/` is
     asked to be empty and **must not be** — the survivors are result-carrier
     fields handing the engine's resolution to the paired tests. Observed count
     at close is **5**, not the **8** three prior SUMMARYs predicted; examples
     00/01/02 route the value through a named local, so the literal string is
     absent while the property is identical. The 8 propagated across three
     documents without re-measurement.
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
