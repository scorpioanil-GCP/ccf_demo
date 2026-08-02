# examples/05-workflow-hitl — auth-bound workflow + three HITL primitives (EXAM-06)

## What this demonstrates

A multi-step **banking** workflow — skill node, agent node, an approval
gate, an exception path, and an asynchronous review — that exercises
three of the four HITL primitives end to end, through a hardened,
authenticated door. **ApprovalGate** (the HITL primitive that suspends a
workflow until a named human approves or rejects — the action lands in
the replay record by construction; CLAUDE.md §8.2 — SDK extension)
suspends the loan disbursement; **ExceptionEscalation** (the HITL
primitive that routes a workflow state to a designated human role when a
condition (e.g., a `D_c` breach) is met; CLAUDE.md §8.2 — SDK extension)
routes a failing node to its declared handler; **ReviewQueue** (the HITL
primitive for asynchronous human review of generated content before
release, integrated with passage-level lineage; CLAUDE.md §8.2 — SDK
extension) holds the generated disbursement briefing until a named
reviewer releases it.

Every human action is authenticated, authorized, cryptographically
bound, and recorded on the **Decision Replay record** (the
five-dimension record — fabric snapshot, policy bindings, model version,
perspective conditioning, generation path — that lets a decision be
reproduced exactly; whitepaper §7.10 ("The Five-Dimension Replay
Record")). The approver and reviewer principals are DERIVED from
verified bearer-token grants, never taken from the caller; unsigned,
tampered, expired, and unmapped-scope submissions all refuse with typed
error constants, fail closed, and never land on the authority path.

## Run it

```
make example-05
```

Raw fallback: `PYTHONPATH=src:runtime python examples/05-workflow-hitl/run.py`.
Exit code 0 means every assertion held; any failure exits nonzero.

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-05`, review the assertion output, then
> deliberately edit the `expected:` block in `artifacts/hitl.yaml`
> (`expected_gate` and the `drive:` values) to match what you reviewed —
> regeneration is a reviewed event, landed in the same commit as the
> enrichment, with the commit body summarizing what changed in the
> output and why. No `make regen-*` targets exist, and none will be
> added.

## The story

1. **The Control Plane closure registers everything.** `run.py` loads
   the workflow's full artifact closure — the task and its steps (see
   `artifacts/task.yaml`), the routing wrapper with transitions,
   terminals, per-node exception refs, and the per-gate approval-policy
   binding (see `artifacts/workflow.yaml`, keys `transitions`,
   `exception_refs`, `gate_policies`), the agent and prompt
   (`artifacts/agent.yaml`, `artifacts/prompt.yaml`), and the D-16 HITL
   policy (see `artifacts/hitl.yaml`, key `hitl_policy` —
   `signed_binding_required: true`).
2. **The workflow suspends at the gate.** The engine executes
   `verify-loan-file` → `assess-disbursement`, then suspends at
   `disbursement-approval` with a persisted `WorkflowStateRecord`
   (CLAUDE.md §8.1: state machines that suspend on a HITL gate and
   resume later).
3. **The hardened door refuses everything it should.** The example
   drives `POST /hitl/actions` through
   `create_app(auth=BearerTokenAuth(...))`: no token → 401; the EXPIRED
   token from `artifacts/tokens.yaml` → 401; authenticated but unsigned
   → 403 `ERROR_SIGNED_BINDING_REQUIRED`; a tampered signature → 403
   `ERROR_SIGNED_BINDING_INVALID`; an authenticated token whose scope
   the mapping in `artifacts/scope_mapping.yaml` does not name → 403
   `tenant-unauthorized`, deny-by-default. Nothing refused ever reaches
   the transport authority path, and both the authorization allow and
   deny are audited with the exact mapping version in force.
4. **The valid, signed approval resumes the workflow.** The audited
   approver subject is the verified `TokenGrant.client_id` — derived,
   never claimed — and the workflow resumes to its declared terminal
   (`disbursed`, from `artifacts/hitl.yaml` key `drive.resume_decision`).
5. **The review before release.** The generated briefing is submitted to
   the ReviewQueue pinned by versioned URI with passage-level lineage
   (see `artifacts/hitl.yaml`, key `review.item` — an item without
   lineage is unconstructible). A second named human — the reviewer,
   whose subject equals the ACTIVE `reviewer` token's `client_id` —
   releases it under a signed binding that echoes the submission-time
   content hash (the TOCTOU guard). The release is audited and its
   pre-serialized block lands on replay dimension 2 byte-for-byte.
6. **The exception path.** A second execution makes `verify-loan-file`
   fail; the engine routes to the handler declared in
   `artifacts/workflow.yaml` under `exception_refs` — a first-class,
   traced, audited transition, not error handling glued on.
7. **Replay dimensions land verbatim.** Dimension 2 carries the human
   actions byte-for-byte (approver, signed binding, content hash of what
   was seen; then the review block); dimension 5 carries the engine's
   step-sequence block; dimension 4's delegation chain names the
   workflow execution.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/workflow.yaml` | Routing only: transitions, terminals, exception refs, gate policy bindings | `[ADAPT]`: tenant, step/terminal names, handler declarations. `[MECHANISM]`: `transitions`, `terminal_states`, `exception_refs`, `gate_policies`, `task_definition_ref` |
| `artifacts/task.yaml` | The three steps (skill, agent, hitl-gate) and their pinned refs | `[ADAPT]`: step names, refs' domain vocabulary. `[MECHANISM]`: step `kind` values, `keys`, `referenced_artifacts` structure |
| `artifacts/agent.yaml` | The declared agent: archetype binding, context contract, perspective, policy regime, debt profile, instruction bindings | `[ADAPT]`: all six axes' values. `[MECHANISM]`: `agent_definition` field names, `referenced_artifacts` structure |
| `artifacts/prompt.yaml` | The versioned prompt template and its declared parameters | `[ADAPT]`: template text, parameters. `[MECHANISM]`: `prompt_artifact` field names |
| `artifacts/hitl.yaml` | The D-16 policy, approver and reviewer identities, drive values, node outputs, review item + lineage, replay values | `[ADAPT]`: identities, instants, outputs, `review.*` content, `drive` values. `[MECHANISM]`: `hitl_policy`, `keys`, `drive`/`review`/`replay` key names |
| `artifacts/tokens.yaml` | The recognised tokens and their lifecycle (active/expired) and scopes — all synthetic | `[ADAPT]`: token strings, client ids, scopes. `[MECHANISM]`: `label`, `status`, `scopes` key names |
| `artifacts/scope_mapping.yaml` | Which scopes reach which tenants and door actions (deny-by-default) | `[ADAPT]`: scope names, tenant patterns. `[MECHANISM]`: mapping grammar keys |

## Whitepaper / CLAUDE.md sections exercised

- whitepaper §7.10 (the five-dimension Decision Replay record —
  dimensions 2, 4, 5 asserted byte-for-byte)
- whitepaper §7.10.3 (passage-level lineage — the ReviewQueue item)
- CLAUDE.md §8.1 (Orchestration Layer: suspend/resume, exception paths)
  — SDK extension
- CLAUDE.md §8.2 (HITL primitives: ApprovalGate, ExceptionEscalation,
  ReviewQueue; audit-by-construction) — SDK extension
- CLAUDE.md §6.4 (No-Hardcoding Rule — every domain value is artifact
  content) — SDK extension
- CLAUDE.md §9 (examples charter item 6)

## What to change first

`artifacts/` is the specialization surface. To move this example to your
domain, edit in this order:

1. `artifacts/workflow.yaml` + `artifacts/task.yaml` — the step names,
   transitions, terminal states, and exception routing (`exception_refs`)
   of your own process; then update `drive.expected_gate`,
   `drive.resume_decision`, and `drive.failing_step` in
   `artifacts/hitl.yaml` to match.
2. `artifacts/hitl.yaml` — the approver/reviewer identities and the
   `review.item` (your generated output's pinned URI and its lineage
   anchors). Flip `hitl_policy.signed_binding_required` to `false` and
   re-run to watch behavior change with zero code change.
3. `artifacts/tokens.yaml` + `artifacts/scope_mapping.yaml` — your token
   table and authorization statement. Add the `reporting` scope to the
   mapping and re-run to watch the 403 leg fail — proving the refusal
   comes from the artifact, not the code.

On the next run expect: new gate/terminal names in the printed summary,
your reviewer subject on the review line, and assertion failures pointing
at any `drive:` value you forgot to update (the reviewed-regeneration
workflow above).

## What would fail

| Invariant | What would fail here |
| --- | --- |
| Suspend/resume with persisted state (CLAUDE.md §8.1) | The workflow does not suspend at the gate, the `WorkflowStateRecord` is missing/not `suspended`, or the declared decision does not reach the declared terminal |
| Auth-bound door, derived principal (D-IMPL-66(a)/67) | The audited approver subject is anything other than the verified `TokenGrant.client_id` |
| D-16 signed-binding requiredness (08-03) | An unsigned submission is admitted, or the refusal is not the typed `ERROR_SIGNED_BINDING_REQUIRED` / `ERROR_SIGNED_BINDING_INVALID` constants |
| Fail-closed token lifecycle (artifact-driven) | The **expired** entry in `artifacts/tokens.yaml` yields anything but a 401 `ERROR_UNAUTHENTICATED` refusal |
| Refusals never land (audit-by-construction, §8.2) | Any refused submission appears on the transport's authority path |
| Replay dimension 2 verbatim (whitepaper §7.10.1) | The recorded block is not byte-equal, or omits the approver, the signed binding, or the content hash of what the approver saw (T-07-39) |
| Replay dimension 5 verbatim (§8.1) | The step-sequence block differs from what the engine serialized |
| ExceptionEscalation as a recorded transition (D-IMPL-61) | The failing node does not route to its declared handler, or the transition is untraced/unaudited |
| Tenant authorization at the door, deny-by-default (HARD-04; D-IMPL-68) | The unmapped-scope token reaches the queue, the refusal is not the typed `ERROR_TENANT_UNAUTHORIZED` 403, or the deny is missing from the audit log (or carries the wrong mapping version) |
| ReviewQueue audit-by-construction (§8.2; §7.10.3) | The review release is absent from the audit log, its block is not byte-equal on replay dimension 2, the item constructs without lineage, or the reviewer's binding echoes a hash other than the submission-time hash (TOCTOU) |
