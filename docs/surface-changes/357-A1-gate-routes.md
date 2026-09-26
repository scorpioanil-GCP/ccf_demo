# 357-A1 — gate_routes on WorkflowDefinition

`D-IMPL-357` A1 (accepted design,
`docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md`
§3.1; ruling locked). Wave 1 Lane A (verdict→target), closing part of the
`SEC-001` residual: a recorded human rejection at a HITL gate could be
routed down the approving branch because no artifact declared which verdict
goes where.

## What did NOT change, stated first

- **No existing field, validator, or export on `WorkflowDefinition` changed
  shape or behavior.** `exception_refs`, `gate_policies`, `transitions`,
  `terminal_states`, and every pre-existing validator are unchanged.
- **The engine does not yet route on this map.** This task adds the
  declared map only; the engine-side compare against it is `D-IMPL-357` A3,
  a later task in this lane. `cursor` and `codex` both flagged "A1 does not
  close the vulnerability at runtime" in review — correct, and it is the
  sheet's sequencing, not a gap in this fragment's claim.
- **No `TaskDefinition` (agent/task definition) contract changed.** The
  wrapped task the workflow references is untouched (D-12).
- **No skill, policy, or half-life value changed.** This is mechanism only:
  the SDK supplies the verdict vocabulary (`GATE_ACTIONS`) and the
  validators; a deployment supplies its own routing values.

## ccf.workflow.WorkflowDefinition

- Surface: ccf.workflow.WorkflowDefinition
- Public surface: true
- Change type: reshaped
- Before: the package-level re-export of the class below, unchanged in shape.
- After: the same re-export of the same reshaped class — `gate_routes` reaches
  a caller importing from `ccf.workflow` exactly as it reaches one importing
  from `ccf.workflow.definitions`. Recorded as its own entry because
  `tools/dump_surface.py` enumerates the re-export as a distinct manifest
  name, so a fragment claiming only the defining module leaves the alias
  unclaimed and `tests/test_surface_completeness.py::
  test_every_diff_line_has_a_matching_public_log_entry` red. Added by A4 on
  finding that red standing; the change itself is A1's and nothing about it
  is A4's.
- Why: as below.
- Migration: none — the same as below.

## ccf.workflow.definitions.WorkflowDefinition

- Surface: ccf.workflow.definitions.WorkflowDefinition
- Public surface: true
- Change type: reshaped
- Before: no field declared which verdict at a gate leads to which
  transition target. A `WorkflowDefinition` could route a `hitl-gate`-kind
  step's approving and rejecting branches from nothing more than whatever
  decision string an engine happened to read at resume time.
- After: a new field, `gate_routes: Mapping[str, Mapping[str, str]]` (gate
  step name → verdict → declared target), default `{}`. A
  `model_validator(mode="after")` refuses: a route key naming no
  non-terminal node in the wrapper's declared transition graph; a verdict
  outside `GATE_ACTIONS` (`ccf.hitl.approval_gate`,
  `frozenset({"approve", "reject"})`); a route target that is not a
  declared outgoing transition target from that gate; and two verdicts from
  one gate naming the same target (a map that would let a recorded
  rejection resolve identically to an approval). The field is marked
  `ccf_hash_transparent: False` (`ccf.contracts.canonical.HASH_TRANSPARENT_KEY`)
  — a declared generation boundary (`D-IMPL-243` amendment 1), not a silent
  default: a stored `WorkflowDefinition` document that predates this field
  is of an earlier generation, named by `generation_mismatch` (by field
  name, before re-execution), never silently treated as compatible. Whether
  a declared key names a `hitl-gate`-kind step is, like `gate_policies`,
  the `WorkflowFactory`'s semantic check, not this contract's.
- Why: `SEC-001` — nothing in the artifact declared which verdict goes
  where, so a recorded rejection had no declared route distinct from an
  approval's. `gate_routes` is that declared map; later tasks in this lane
  (`A2` factory-level completeness check on `hitl-gate`-kind steps, `A3`
  engine-side compare against the recorded decision, `A4` refusal of
  conflicting verdicts on one suspension) consume it by name and shape —
  neither is renamed nor reshaped here.
- A routed gate declares at least TWO distinct outgoing transition targets.
  It follows from the validators rather than being declared separately: every
  route target must be a declared transition target from that gate, two
  verdicts from one gate must not share a target, and `A2`'s factory check
  requires a target for every `GATE_ACTIONS` verdict. A gate with a single
  outgoing edge satisfies no pair of those, so a workflow that relied on
  `D-IMPL-61` propagate-to-terminal for its rejecting branch — as the
  covenant fixture's own comment does for exception refs
  (`tests/fixtures/banking/workflows/covenant_review_workflow.yaml`) — now
  declares an explicit reject edge. That is the lane's intent; what was
  missing is that an author met it as two refusals from two modules with the
  rule stated nowhere. It is now one clause on the `gate_routes` field
  docstring (`src/ccf/workflow/definitions.py`).
- A `hitl-gate`-kind step is never a declared terminal state. `A2`'s factory
  refuses any step whose kind in the resolved TaskDefinition is `hitl-gate`
  and whose name appears in `effective_terminal_states`. Review measured both
  shapes this closes: named in `terminal_states` and reached as a transition
  target, the execution COMPLETES at the gate's name with no suspension and no
  human action; as the START node, it suspends and can never resume. Neither
  was reached by the completeness check, because `routable` subtracts the
  terminal states — so "gate" silently meant two different no-ops depending on
  how it was reached. A gate is a place a human acts, never a terminal
  condition. A deployment whose workflow declares such a step is refused at
  construction, which is a behavior change to `WorkflowFactory.construct` on a
  shape that could not have worked as its author intended.
- Migration: none required for an existing deployment — the field defaults
  to `{}` and every `WorkflowDefinition` document written before this
  change validates unchanged. A workflow author who wants the new refusal
  coverage on a routed gate declares its `gate_routes` entry; `A2`'s
  factory-level check is what will require a complete map once a step is
  `hitl-gate`-kind.
