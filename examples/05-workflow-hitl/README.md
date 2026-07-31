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

## Citations

- CLAUDE.md §8.1 (Orchestration Layer — workflow primitive, exception
  paths), §8.2 (HITL — audit-by-construction), §6.4 (No-Hardcoding Rule),
  §9 (examples charter item 6)
- Whitepaper §7.10.1 (five-dimension Decision Replay record)
- D-IMPL-20/21/62/66(a)/67; D-16 (phase 8 hardening); D-14 (examples bind
  auth — live leg)

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
code change), and the recognised tokens (`tokens.yaml`). `run.py` is thin
mechanism; deleting the artifacts leaves it nothing to run (§6.4).
