# examples/05-workflow-hitl — auth-bound workflow + HITL gate (EXAM-06)

A multi-step **banking** workflow — skill node, agent node, ApprovalGate,
ExceptionEscalation path — constructed through the WorkflowFactory from
definition artifacts, suspended at the gate with persisted state, and
approved through the **hardened Experience-Layer door**:
`create_app(auth=BearerTokenAuth(...))`, a grant-derived approver principal
(D-IMPL-67), and a **required D-16 signed principal binding** verified at
the transport authority path. The human action lands in the Decision
Replay record by construction. This is the live leg of the D-14
absorption: the auth-bound HITL surface demonstrated end to end.

Phase 10 extends the door with **tenant authorization** (HARD-04;
D-IMPL-68): a scope-mapping Control Plane artifact
(`artifacts/scope_mapping.yaml`) binds token scopes to
`tenant-pattern × action-id` sets, interpreted per request by
`ControlPlaneTenantAuthorizer` bound at `create_app(authorizer=...)`. The
approver token's scope is mapped and reaches the queue and submit actions
(200); a second, authenticated token whose scope the mapping does not
name is refused deny-by-default with the typed 403
`tenant-unauthorized` — and both the allow and the deny land in the one
Control Plane audit log with the exact mapping version in force.

## Run it

```
make example-05
```

(or `PYTHONPATH=src:runtime python examples/05-workflow-hitl/run.py`).
Exit code 0 means every assertion held; any failure exits nonzero.

## What it demonstrates

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

## Citations

- CLAUDE.md §8.1 (Orchestration Layer — workflow primitive, exception
  paths), §8.2 (HITL — audit-by-construction), §6.4 (No-Hardcoding Rule),
  §9 (examples charter item 6)
- Whitepaper §7.10.1 (five-dimension Decision Replay record)
- D-IMPL-20/21/62/66(a)/67/68; D-16 (phase 8 hardening); D-14 (examples
  bind auth — live leg); Phase 10 D-16 (examples extended in place with
  tenant authorization)

## Domain rationale (D-09)

Banking: approval workflows under regulatory pressure are the canonical
HITL case — a loan disbursement that must not move without a named,
cryptographically bound human approval is the situation the HITL pillar
exists for. Non-adjacent reuse of the example-00 banking domain is
permitted by D-06: every tenant, identifier, and value here is fresh
(`sterling-mutual`, loan disbursement), nothing is shared with example 00
or any test fixture.

The tokens in `artifacts/tokens.yaml` are synthetic, illustrative values
for a runnable demo (T-08-20 accepted) — never production credentials.

## What to change first

`artifacts/` is the specialization surface: the workflow shape and routing
(`workflow.yaml`, `task.yaml`), the agent (`agent.yaml`, `prompt.yaml`),
the approver and the D-16 policy (`hitl.yaml` — flip
`signed_binding_required` and re-run to watch behavior change with zero
code change), the recognised tokens (`tokens.yaml`), and the
authorization statement (`scope_mapping.yaml` — add the `reporting`
scope to the mapping and re-run to watch the 403 leg fail, proving the
refusal comes from the artifact, not the code). `run.py` is thin
mechanism; deleting the artifacts leaves it nothing to run (§6.4).
