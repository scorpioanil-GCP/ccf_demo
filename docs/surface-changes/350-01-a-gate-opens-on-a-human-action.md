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

The residual is pinned by
`tests/workflow/test_engine.py::test_a_rejection_authorizes_resumption_but_does_not_bind_the_target`,
which goes RED the moment a verdict→target binding is declared and enforced.

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

`tests/cli/test_skill_import.py`: four `SEC-003` refusals — a symlinked
reference (asserting the secret's bytes appear in no output and no reference
artifact reaches the registry), a symlinked `SKILL.md`, an oversized
reference, and too many references — each with the ordinary package as a
live control in the same module, so the guards are shown refusing the
hostile case and passing the benign one.
