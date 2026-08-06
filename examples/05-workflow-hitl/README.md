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

`run.py` is the **call spine** an adopter would write. It asserts nothing
and prints nothing: exit 0 means the spine executed. What says it was
*right* is `tests/examples/test_workflow_hitl_output.py`, where the
example's assertions live so a test runner can fail a build on them
(D-09). Run them with:

```
PYTHONPATH=src:runtime python -m pytest tests/examples/test_workflow_hitl_output.py
```

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-05`, then run the test module, review the
> failures, and deliberately edit the `drive:` block in
> `artifacts/hitl-drive.yaml` (and any other artifact whose declared
> value moved) to match what you reviewed — regeneration is a reviewed
> event, landed in the same commit as the enrichment, with the commit
> body summarizing what changed and why. No `make regen-*` targets exist,
> and none will be added.

## The story

1. **One call boots the fabric.** `artifacts/manifest.yaml` names every
   artifact in force; `load_and_boot` parses all of them, registers the
   `role: register` ones, and boots on the resulting pins. The five
   documents the workflow's, task's and agent's versioned-URI refs
   resolve against — the agent's policy regime and debt profile, the
   task's skill, the exception handler, the approval policy — are
   manifest entries, not a hand-written closure walking inline
   `referenced_artifacts:` blocks at run time.
2. **Six documents the driver registers itself, deliberately.** Four are
   author-versioned SDK classes (`ccf.agent-definition`,
   `ccf.prompt-artifact`, `ccf.task-definition`,
   `ccf.workflow-definition`): every one of them registers through
   `register_versioned`, whose D-05 bump check holds the author's
   `artifact_version` against content identity. `register_typed` does not
   run that check, so none of the four takes it. A manifest may name them
   as `registration: versioned`, and declaring `typed` for one is refused
   at preflight (D-IMPL-85); they stay at the call site so the bump check
   is visible as the thing being taught. Two more (`ccf.hitl-policy`,
   `ccf.scope-mapping`) are SDK classes a manifest cannot address at all.
3. **The workflow suspends at the gate.** The engine executes
   `verify-loan-file` → `assess-disbursement`, then suspends at
   `disbursement-approval` with a persisted `WorkflowStateRecord`
   (CLAUDE.md §8.1: state machines that suspend on a HITL gate and
   resume later).
4. **The hardened door refuses everything it should.** The example
   drives `POST /hitl/actions` through
   `create_app(auth=BearerTokenAuth(...))`: no token → 401; the EXPIRED
   token from `artifacts/tokens.yaml` → 401; authenticated but unsigned
   → 403 `ERROR_SIGNED_BINDING_REQUIRED`; a tampered signature → 403
   `ERROR_SIGNED_BINDING_INVALID`; an authenticated token whose scope
   the mapping in `artifacts/scope-mapping.yaml` does not name → 403
   `tenant-unauthorized`, deny-by-default. Nothing refused ever reaches
   the transport authority path, and both the authorization allow and
   deny are audited with the exact mapping version in force.
5. **The valid, signed approval resumes the workflow.** The audited
   approver subject is the verified `TokenGrant.client_id` — derived,
   never claimed — and the workflow resumes to its declared terminal
   (`disbursed`, from `artifacts/hitl-drive.yaml` key
   `drive.resume_decision`).
6. **The review before release.** The generated briefing is submitted to
   the ReviewQueue pinned by versioned URI with passage-level lineage
   (see `artifacts/hitl-drive.yaml`, key `review.item` — an item without
   lineage is unconstructible). A second named human — the reviewer,
   whose subject equals the ACTIVE `reviewer` token's `client_id` —
   releases it under a signed binding that echoes the submission-time
   content hash (the TOCTOU guard). The release is audited and its
   pre-serialized block lands on replay dimension 2 byte-for-byte.
7. **The exception path.** A second execution makes `verify-loan-file`
   fail; the engine routes to the handler declared in
   `artifacts/workflow-definition.yaml` under `exception_refs` — a
   first-class, traced, audited transition, not error handling glued on.
8. **Replay dimensions land verbatim.** Dimension 2 carries the human
   actions byte-for-byte (approver, signed binding, content hash of what
   was seen; then the review block); dimension 5 carries the engine's
   step-sequence block; dimension 4's delegation chain names the
   workflow execution.

## Artifact-by-artifact

One artifact class, one document. Each `.yaml` carries a
`# yaml-language-server: $schema=` header naming the schema that accepts
it, so an editor validates it as you type.

### Named by `manifest.yaml`

| Artifact | Role | What it declares |
| --- | --- | --- |
| `artifacts/manifest.yaml` | — | Every artifact in force, enumerated; the tenant; the backend kind |
| `artifacts/resolution-spec.yaml` | `register` | Loans, borrowers, and the edge between them — the deployment's L2 vocabulary |
| `artifacts/policy-bundle.yaml` | `register` | The FABRIC's policy bundle, stamped onto every claim at assembly |
| `artifacts/agent-policy-regime.yaml` | `register` | The AGENT's axis-4 regime, at the key its versioned-URI ref resolves against |
| `artifacts/agent-debt-profile.yaml` | `register` | The agent's axis-5 half-life/debt thresholds |
| `artifacts/task-skill.yaml` | `register` | What the task's first step may invoke |
| `artifacts/exception-handler.yaml` | `register` | Where a failing loan-file verification escalates |
| `artifacts/approval-policy.yaml` | `register` | Who may approve at the gate, and the quorum |
| `artifacts/events.yaml` | `load` | The L1 envelopes the loan under review is assembled from (SDK-fixed role) |
| `artifacts/agent-registration.yaml` | `load` | Where the six driver-registered documents file, plus the signing key's name |
| `artifacts/hitl-drive.yaml` | `load` | What this run's two humans do: identities, drive values, node outputs, the review item |
| `artifacts/replay-values.yaml` | `load` | The product envelope, perspective and policy binding the record is shaped from |
| `artifacts/tokens.yaml` | `load` | The recognised tokens, their lifecycle and scopes — all synthetic |

### Registered by `run.py`, and why

| Artifact | Registered via | Why not the manifest |
| --- | --- | --- |
| `artifacts/agent-definition.yaml` | `register_versioned` | Author-versioned; kept at the call site so the D-05 bump check is visible. A manifest entry would have to declare `registration: versioned` |
| `artifacts/prompt-artifact.yaml` | `register_versioned` | Author-versioned; kept at the call site so the D-05 bump check is visible. A manifest entry would have to declare `registration: versioned` |
| `artifacts/task-definition.yaml` | `register_versioned` | Author-versioned; kept at the call site so the D-05 bump check is visible. A manifest entry would have to declare `registration: versioned` |
| `artifacts/workflow-definition.yaml` | `register_versioned` | Author-versioned; kept at the call site so the D-05 bump check is visible. A manifest entry would have to declare `registration: versioned` |
| `artifacts/hitl-policy.yaml` | `register_typed` | Not manifest-addressable; an entry naming it is refused at load (D-IMPL-84), where it used to resolve to the open envelope and hand the transport the wrong type |
| `artifacts/scope-mapping.yaml` | `register_typed` | Not manifest-addressable; same refusal, and the authorizer reads the real contract back by key |

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

1. `artifacts/workflow-definition.yaml` + `artifacts/task-definition.yaml`
   — the step names, transitions, terminal states, and exception routing
   (`exception_refs`) of your own process; then update
   `drive.expected_gate`, `drive.resume_decision`, and
   `drive.failing_step` in `artifacts/hitl-drive.yaml` to match. Bump
   `artifact_version` on each definition you edit — the D-05 check
   refuses changed content under an unchanged version.
2. `artifacts/hitl-drive.yaml` — the approver/reviewer identities and the
   `review.item` (your generated output's pinned URI and its lineage
   anchors) — plus `artifacts/approval-policy.yaml` for who may approve.
   Flip `signed_binding_required` in `artifacts/hitl-policy.yaml` to
   `false` and re-run to watch behavior change with zero code change.
3. `artifacts/tokens.yaml` + `artifacts/scope-mapping.yaml` — your token
   table and authorization statement. Add the `reporting` scope to the
   mapping and re-run the test module to watch the 403 leg fail — proving
   the refusal comes from the artifact, not the code.

Rename an artifact and `artifacts/manifest.yaml` must move with it; the
manifest enumerates and never globs, so a stale path is a loud failure
before anything is registered rather than a silently missing artifact.

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
| Author-versioned governance (D-05) | A definition's content changes under an unchanged `artifact_version` and the registry admits it — which is what a `registration: typed` entry for those four classes would cause, and is why one is refused at preflight (D-IMPL-85) |
