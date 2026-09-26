# 350-01 — a HITL gate opens on a recorded human action, and an imported skill package is untrusted input

`D-IMPL-350`, Tier 0 of the remedy plan in the security review of 2026-09-23
(`§7`, "this week, before any bank sees the SDK"). Two findings: `SEC-001`
(CRITICAL) — `WorkflowEngine.resume` advanced a gate-suspended execution on
the caller's decision string and audited `resolved=True` with no approver —
and `SEC-003` (HIGH) — `ccf skill import` followed symlinks out of the
imported package and published their targets into the Control Plane.

## What did NOT change, stated first

- **`ApprovalGate` is untouched.** Its resolution path, its TOCTOU guard, its
  signed-binding enforcement and its audit records are byte-identical. The
  engine now *reads* the authority path; it still never writes a verdict to
  it, so resolution stays the primitive's act (CLAUDE.md §8.2).
- **`HITLTransportProtocol` gains no method.** The check reads `submissions`,
  which already existed and is already the authority surface.
- **No workflow artifact schema changed.** `WorkflowDefinition`,
  `WorkflowTransition` and `TaskDefinition` are unchanged, so no shipped
  workflow document needs an edit.
- **Routing is still the artifact's statement (CINV-01).** The engine gained
  an authority precondition, not an opinion about which target a verdict may
  take — see THE LIMIT below.
- **The exception-routed resume path is unchanged.** It crosses no gate, so
  it acquires no approver.
- **`ccf skill import`'s mapping is unchanged** — frontmatter, body,
  `references/` and the `InstructionBinding` reference all register exactly
  as before for a package that is what it claims to be.

## ccf.hitl.approval_gate.GATE_APPROVE

- Surface: ccf.hitl.approval_gate.GATE_APPROVE
- Public surface: true
- Change type: added
- Before: absent — `GATE_ACTIONS` named the pair, and nothing named the
  affirmative member
- After: `"approve"`, the one gate verdict that is an authorization rather
  than merely a recorded action
- Why: the engine's gate-authority check has to distinguish "a human acted"
  from "a human said yes". Reaching for a bare `"approve"` literal in
  `/runtime` would put a vocabulary value outside the module that owns the
  vocabulary
- Migration: none. A new public constant drawn from the existing
  `GATE_ACTIONS`

## ccf_runtime.cli.commands.CommandRefused

- Surface: ccf_runtime.cli.commands.CommandRefused
- Public surface: true
- Change type: added
- Before: absent — only a refusal that had crossed the HTTP boundary could
  reach the documented exit-1-with-body contract, so a verb refusing its own
  local inputs could do nothing but raise
- After: a `ValueError` subclass; `ccf_runtime.cli.main.main` catches it,
  prints it on stdout and returns `EXIT_REFUSED`
- Why: `SEC-003`'s refusals are governance outcomes and have to read like
  one. An operator handed a traceback for a hostile skill package learns
  less than an operator handed a refusal
- Migration: none for existing verbs. A new verb that refuses its own inputs
  should raise this rather than a bare `ValueError`

## ccf_runtime.cli.commands.skill_import.MAX_REFERENCE_BYTES

- Surface: ccf_runtime.cli.commands.skill_import.MAX_REFERENCE_BYTES
- Public surface: true
- Change type: added
- Before: absent — `reference.read_text()` was unbounded
- After: `1_048_576`, the per-file ceiling `_read_contained` enforces
- Why: a skill package exists to be distributed, which makes it untrusted
  input, and an unbounded read of untrusted input is a resource hazard
  independent of what the bytes turn out to be. Public so an operator can
  see the ceiling they are being held to
- Migration: none below the ceiling. A package above it is refused

## ccf_runtime.cli.commands.skill_import.MAX_REFERENCES

- Surface: ccf_runtime.cli.commands.skill_import.MAX_REFERENCES
- Public surface: true
- Change type: added
- Before: absent — one import registered as many prompt artifacts as the
  directory held
- After: `64`, the per-import ceiling on registered reference artifacts
- Why: the same reason as the byte ceiling, one level up: the count is as
  unbounded as the size was
- Migration: none below the ceiling

## ccf_runtime.workflow.state.WorkflowStateRecord

- Surface: ccf_runtime.workflow.state.WorkflowStateRecord
- Public surface: true
- Change type: reshaped
- Before: six fields, the last being `workflow_definition_uri` — whose
  docstring said resume "validates the supplied handle against it, so an
  execution never continues under a definition it was not started with"
- After: a seventh required field, `workflow_definition_hash`, and the pair
  is what resume compares
- Why: the URI could not deliver what its own docstring claimed. The factory
  builds `definition_uri` from the artifact's declared `tenant`, `name` and
  `artifact_version` — never from the Control Plane key it was registered
  under — so a second definition registered under any other key carries a
  byte-identical URI while declaring different routing. Demonstrated: a
  substituted definition adding `credit-officer-approval -> elsewhere`
  completed there **with a genuine approver's action in hand**, spending a
  real human decision on a transition their workflow never declared
  (`SEC-001`, security review 2026-09-23)
- Migration: none for a caller. The engine writes the field; the record is
  the engine's own opaque state (D-IMPL-18/27) and no adopter constructs
  one. An execution suspended under an older record shape is not resumable
  across the change, which is correct rather than regrettable — the whole
  point is that the fabric can no longer be told what it was running

## runtime/ccf_runtime/workflow/engine.py

- Surface: runtime/ccf_runtime/workflow/engine.py
- Public surface: false
- Change type: behavior
- Before: `resume` checked four things and then `if decision not in targets`.
  `self._hitl_transport` appeared once in the whole gate path — at line 619,
  to *enqueue* the pending approval. Nothing ever read it back. The audit
  then recorded `workflow_resumed, resolved=True` with no actor, so the
  record did not merely omit the approval, it asserted a resolution that
  never happened
- After: a gate-suspended execution resumes only when the HITL authority
  path holds a submission that (a) names this gate's pending event, (b)
  echoes `content_hash(record)` — the suspension's own identity, which the
  pending event already binds and `ApprovalGate` already makes the approver
  attest to (T-07-39) — and (c) carries a `GATE_ACTIONS` verdict. The
  approver's `subject_id` is then the audit event's `actor`, and `_append`'s
  `actor` keyword carries no default, so no call site can omit it silently.
  The refusal no longer prints the declared transition targets
- Why: `SEC-001`. The whole HITL pillar is sold on the claim that a human
  authorized the transition
- Migration: a deployment that resumed gates programmatically must now route
  the human action through the HITL transport first — which is the path
  `ApprovalGate`, `POST /hitl/actions` and `ccf hitl submit` already offer.
  The in-tree example and test suites needed exactly that one edit

## runtime/ccf_runtime/cli/commands/skill_import.py

- Surface: runtime/ccf_runtime/cli/commands/skill_import.py
- Public surface: false
- Change type: behavior
- Before: `references.iterdir()` filtered on `reference.is_file()`, which
  **follows symlinks**, and `SKILL.md` was read the same way. No `resolve()`,
  no `is_symlink()`, no containment check, no ceiling anywhere in the module
- After: every read goes through `_read_contained`, which refuses a symlink
  outright, refuses a path resolving outside the package, refuses anything
  that is not a regular file, and refuses a file over the byte ceiling; the
  reference count is checked against `MAX_REFERENCES` before any read
- Why: `SEC-003`, and it chains. A shared package carrying
  `references/usage.md -> ~/.aws/credentials` had those bytes registered as
  a prompt artifact, where `GET /config/resolution` — unauthorized, `SEC-002`
  — served them to any caller. That was the most complete exfiltration path
  the review found. A symlink is refused rather than resolved-and-allowed
  because a link inside a *distributed* package has no legitimate meaning on
  the importing machine, and refusing is the only answer that does not depend
  on where the link happens to point
- Migration: a package that genuinely wants a file's contents ships the file

## THE LIMIT, STATED SO `SEC-001` IS NOT READ AS FULLY CLOSED

**The verdict does not bind which declared target the resume may take.** A
`WorkflowDefinition` carries `transitions` (source→target) and nothing
verdict-shaped, so nothing in the artifact says that `reject` may route to
`rejected` but not to `released`. Deriving that in code would put domain
routing values in `/src` (No-Hardcoding, CLAUDE.md §6.4), so the mapping has
to be *declared* before it can be enforced — an artifact-schema change, and
Dave's ruling.

Until then a recorded rejection can still be routed down the approving
branch. What changed is that some human must have acted on this exact
suspension, and the audit names them.

**What closing it would cost, measured 2026-09-24 so it is not re-derived.**
Three gate-bearing workflow documents would need one line each —
`tests/fixtures/banking/workflows/covenant_review_workflow.yaml`,
`.../payment_release_workflow.yaml` and `perf/synth/artifacts/workflow.yaml`.
The two archived ones are out of scope under `D-IMPL-351`. No live example is
affected: `examples/cp-15` is the only HITL example and it composes
`ccf.hitl` directly, never `WorkflowEngine`. **`WorkflowDefinition` is
constructed nowhere in Python** — the only match for `WorkflowDefinition(` in
the tree is its own class statement — so this is a data migration with no code
to port.

Every gate in the tree has exactly two exits, and each pair uses a different
domain vocabulary: `approved`/`rejected`, `released`/`rejected`,
`accepted`/`declined`, and (archived) `disbursed`/`declined`,
`authorized`/`withheld`. **That is the argument for declaration rather than
derivation**: five vocabularies for two verdicts, none of them guessable from
the verdict name.

**Hash churn is avoidable and was measured both ways.** An unmarked
sentinel-defaulted field renders into `canonical_bytes` and moves the content
hash of every existing definition (`0c3a7bf9…` → `a4578fd0…`). The same field
marked `json_schema_extra={HASH_TRANSPARENT_KEY: True}` leaves it
byte-identical at its sentinel (`0c3a7bf9…` → `0c3a7bf9…`) and moves it only
once routes are actually declared — which is `D-IMPL-243`'s *"silence equals
yesterday"* applied exactly as ruled.

**`D-IMPL-293` decides which of those to take, and it is not the cheap one.**
Hash-transparency exists to buy compatibility with records written before a
field existed. There are none: the SDK has no adopters, and Dave restated the
rule while reviewing this work — *"the SDK has not been used by anyone yet. We
have the liberty of making the correct changes instead of patching something."*
Marking the field `True` would make an unset value mean *unconstrained*, which
is precisely the vulnerable state, bought with compatibility nobody needs.

**So the recommended shape is the honest one: a gate that declares no verdict
routes is refused, and the field is marked `{HASH_TRANSPARENT_KEY: False}` — a
generation boundary.** That mark is `D-IMPL-243`'s own third state and it says
exactly what is true here: a workflow definition written without verdict routes
belongs to an earlier generation of the contract, and the replay engine names
it (`canonical_generation_mismatch`) rather than running it. Hashes move, which
is correct — the artifact really did change — and the three in-tree documents
take one line each. The refusal belongs at factory construction, not at resume,
so a deployment learns at boot rather than at the first approval.

This remains Dave's ruling to make formally; what `D-IMPL-293` removes is the
argument for the weaker shape.

The residual was pinned by a test written to go RED the moment a
verdict→target binding was declared and enforced. **That moment arrived:
`D-IMPL-357` A1 declares `gate_routes` on the workflow definition and A3
enforces it in `resume`, so the ROUTING residual is closed FOR A SINGLE
RECORDED VERDICT, and the pin now asserts the closed behavior** —
`tests/workflow/test_engine.py::test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch`.
Stated with its limit rather than as a full close, because two measured paths
still reach an approving terminal after a rejection was recorded, and both are
verdict SELECTION rather than routing — they decide which recorded verdict
becomes the authority, and A3's compare then faithfully agrees with whichever
one was selected. **Two distinct verdicts on one suspension resolve to the
OLDEST** (`_gate_authority` takes `next((...), None)` over an oldest-first
submission list, and the submit-only action door consumes no pending event, so
both stay eligible), and **a stamp race in the transport** lets a principal
holding submit authority land an approve in the window between the officer's
resolve removing the claim and submitting, so the officer's rejection is
recorded unstamped and ignored. Both are `D-IMPL-357` **task A4**'s; neither is
closed here. *(The rest of this section still reads in the pre-A1 present
tense and contradicts itself in places — assigned to A5, which owns the
published pages.)*

## Regression evidence

`tests/workflow/test_engine.py`: five `SEC-001` tests — resume with no human
action is refused and the execution stays suspended; the refusal does not
enumerate declared targets; a real `ApprovalGate` resolution resumes and the
audit names the approver; another execution's approval does not open this
gate; and the residual above. All five were written first and watched fail
against the pre-fix engine.

`tests/http_api/test_routes.py`: the same claim at the reachable door
(`POST /workflow/resumptions`), plus the no-enumeration claim, plus an
undeclared-decision refusal that now runs *after* a real approval has been
submitted through `POST /hitl/actions`.

`tests/cli/test_cli.py`: the same at `ccf workflow resume`, asserting the
execution is still suspended afterwards.

`tests/workflow/test_engine_stateful.py`: the hypothesis state machine now
resolves each gate through `ApprovalGate` before resuming it, so every
generated interleaving exercises the authority path rather than bypassing it.

`tests/cli/test_skill_import.py`: five `SEC-003` refusals — a symlinked
reference (asserting the secret's bytes appear in no output and no reference
artifact reaches the registry), a symlinked `SKILL.md`, a reference
symlinked at a target *inside* the package, an oversized reference, and too
many references — each with the ordinary package as a live control in the
same module, so the guards are shown refusing the hostile case and passing
the benign one.

## THE FIRST FIX WAS WALK-AROUND-ABLE, AND THE CLOSE PANEL FOUND IT

Stated first because it is the most important thing in this record. The Tier-0
fix as originally written asked `_is_gate(workflow, record.current_state)` —
**the CALLER'S handle** — whether the suspended node was a gate, and skipped
the authority check when the answer was no.

`definition_uri` is built by the factory from the artifact's own declared
`tenant`, `name` and `artifact_version`, **not** from the Control Plane key it
was registered under. So a second workflow definition, registered under any
other key with the same three fields, carries a byte-identical URI while
wrapping a different task definition. Reproduced at `00bfeaa9` before the
repair was written:

```
suspended at credit-officer-approval; approvals pending: 1
honest definition_uri: ...covenant-review-workflow@1.0.0
evil   definition_uri: ...covenant-review-workflow@1.0.0    identical
resume(evil_handle, decision="approved") -> WorkflowCompleted(approved)
human actions recorded: 0
approval still pending : 1
audit: workflow_resumed resolved=True actor=None
```

That is the exact `SEC-001` signature the fix existed to make impossible.

**Two repairs, and the first is the one that matters.**

1. **The authority check is now UNCONDITIONAL on the suspended branch.**
   `status == "suspended"` is written in exactly one place — `_suspend`,
   reachable only from a `hitl-gate` step — so a suspended record *is* a gate
   suspension, as a fact the fabric recorded about itself. `_is_gate` is
   deleted rather than left beside the call site as a trap. **Never ask the
   caller what kind of node the fabric is waiting on.**
2. **The execution is bound to its definition by content, not by name.**
   `WorkflowStateRecord` gains `workflow_definition_hash` and resume compares
   it. The refusal's own message already claimed an execution "continues only
   under the definition it was started with" — comparing self-declared URIs
   could not deliver that. Without this, a *genuine* approver's action could be
   spent on a transition their workflow never declared: a substituted
   definition adding `credit-officer-approval -> elsewhere` completed there
   with a real approval in hand.

**The lesson generalizes past this finding.** The first fix introduced a
precondition and then let the caller supply the input that decides whether the
precondition runs. Any guard whose *applicability* is caller-determined is not
a guard.

## Sabotage verification, including what it caught in these tests

Nine guards were severed one at a time in a detached worktree. **Three
severings left every gate green on the first pass**, and each was a real
gap rather than a formality:

1. **The suspension-hash binding could be removed with nothing going red.**
   `test_another_executions_approval_does_not_open_this_gate` was passing on
   the *event-key* comparison alone, because two executions have different
   event keys — so the hash, which is the load-bearing check, was never
   exercised. Closed by
   `test_a_submission_that_never_saw_this_suspension_is_not_authority`,
   which submits through the transport directly (the shape `POST
   /hitl/actions` makes reachable, since the submit-only door compares no
   hashes) with the right gate and the wrong hash.
2. **Re-enabling the target enumeration reddened nothing.** Both
   no-enumeration tests refused at the *authority* check, which is ordered
   first, and never reached the branch that could leak. Both now approve
   first.
3. **Removing the symlink refusal reddened nothing**, because containment
   caught the same case — the review's exfiltration target sits outside the
   package. Closed by a symlink pointing *inside* the package, which only
   the symlink refusal can refuse.

Two guards are **backstops that cannot currently fail**, and both now say so
in their own docstrings rather than being left to read as independent
evidence: the event-key comparison (the hash already separates any two
suspensions) and the containment check (the symlink refusal and
`iterdir`'s direct children leave it nothing reachable to catch). Recording
which checks are load-bearing and which are belt-and-braces is the same
discipline `SEC-011` exists to enforce — a control that cannot fail is not a
control, and the honest response is to name it, not to imply three
independent guards where there are two.

Three further severings were run after the walk-around repair, and each
reddens its own gate: removing the content-hash binding reddens the
substituted-definition test; severing the authority check reddens five;
restoring the original caller-asked `_is_gate` shape reddens both
substitution tests.

The remaining six severings each reddened exactly the gate that owns them:
the authority precondition (6 tests across engine, HTTP and CLI), the
approver-into-audit assignment (2), the byte ceiling (1), the count ceiling
(1), and the two above once repaired.
