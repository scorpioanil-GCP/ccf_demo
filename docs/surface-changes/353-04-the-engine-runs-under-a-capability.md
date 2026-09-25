# 353-04 — the engine runs under a capability, and the tenant on the write is the capability's

`D-IMPL-353` §1.2/§1.3, Lane ENGINE. Closes the close panel's `P2`
(`D-IMPL-352`): a capability minted for tenant B on tenant A's workflow key
constructed A's handle and filed an execution — state and a pending approval
event — under A. The fork-shaped reproduction failed by *succeeding*:
`WorkflowStateRecord(tenant='acme-bank', execution_id='exec-p2',
status='suspended')` under `acme-bank/exec-p2`, minted from `beta-bank`.

After this change the tenant on every write is the capability's tenant and
nothing else. The artifact's declared tenant is compared with the capability
**once**, at construction, and is never consulted again by the engine or any
driver leg. A cross-tenant invocation is not refused downstream; it is not a
state the surface can reach.

## What did NOT change, stated first

- **The SEC-001 authority checks are untouched.** `_gate_authority`,
  `_escalation_pending` and `_escalation_authority` in
  `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine` answer a different
  question — did a human act — and read the tenant from the capability where
  they read one.
- **No constructor changed.** `WorkflowEngine(...)` and
  `WorkflowFactory(control_plane=...)` are composed exactly as before; the CLI's
  local composition root needs no edit.
- **The store call shapes are pre-353 until the join.** The two derived-write
  sites — state and trace — already receive the capability and the derived key;
  Lane HANDLES's `ControlPlaneStateStore.put` / `ArtifactStoreProtocol.put`
  argument lists land at the join. Both sites are marked `JOIN` in their
  docstrings.

## How the manifest sees this, and why some entries below say `behavior`

The surface manifest records constructor shapes and Protocol `__call__`
shapes. Four of the names below changed a **method** signature —
`construct`, `execute`, `resume`, `start_execution`, `resume_execution` and the
drivers' introspection seams — which the manifest's diff cannot see, exactly as
it cannot see D-02's change to `load_artifact`. Those entries carry
`Change type: behavior`, the one type the gate admits for a change its diff is
blind to, and the entry text is the record. The names whose constructor the
manifest does see — `Workflow`, and the new `WorkflowTenantMismatchError` — carry
their diff direction.

## ccf.workflow.factory.WorkflowFactory

- Surface: ccf.workflow.factory.WorkflowFactory
- Public surface: true
- Change type: behavior
- Before: `construct(*, definition_key: str, definition_version: str)` — the
  caller named the Control Plane key to resolve; no capability was involved and
  the artifact's declared tenant was never compared with anything
- After: `construct(authorized: Authorized[Execute] | Authorized[Resume], *,
  definition_version: str)`. The key IS `authorized.resource`; there is no
  `definition_key` parameter. The capability is verified first (mint, kind,
  retarget, resource — the runtime tooth), then the artifact's declared
  `tenant` is compared with `authorized.tenant` exactly once and a mismatch
  raises `WorkflowTenantMismatchError` before any handle exists
- Why: §1.2 — a handle whose target is the resource the authorizer decided on
  takes it from the capability and has no caller-supplied parameter for it;
  §1.3 — the one tenant comparison lives inside the handle that holds the
  capability, not in a door that might forget. A fabricated, retargeted or
  wrong-kind capability dies in `verify` before the comparison can see it
- Migration: obtain the capability from the gate for `workflow.invoke` or
  `workflow.resume` (both doors already bind their resource to the request's
  `definition_key`, so the value the door decided on is the value the factory
  reads) and pass it first; drop `definition_key=`. A handler with nothing to
  pass is a `mypy --strict` error, pinned by
  `tests/workflow/test_workflow_static.py::test_a_handler_with_no_capability_does_not_type_check`

## ccf.workflow.factory.Workflow

- Surface: ccf.workflow.factory.Workflow
- Public surface: true
- Change type: reshaped
- Before: `Workflow(*, definition, task_definition, identity)`
- After: `Workflow(*, definition, task_definition, identity, definition_key:
  str)` — a required keyword; the empty string is refused — and a read-only
  `definition_key` property carrying the Control Plane key the handle was
  resolved from
- Why: §1.5(f). The engine is handed a handle by its caller, so it binds the
  capability's resource to the handle's own key: an `Execute` minted for
  definition X cannot run a handle built for definition Y. Without the key on
  the handle that bind has nothing to compare against
- Migration: none for callers — the factory is the only construction path
  (CINV-01c) and it supplies the key from `authorized.resource`

## ccf.workflow.Workflow

- Surface: ccf.workflow.Workflow
- Public surface: true
- Change type: reshaped
- Before: the package re-export of `ccf.workflow.factory.Workflow`, same shape
- After: the same re-export; the constructor and `definition_key` property
  described under `ccf.workflow.factory.Workflow`
- Why: one name, two import paths; the record carries both so neither is an
  unclaimed move
- Migration: none

## ccf.workflow.factory.WorkflowTenantMismatchError

- Surface: ccf.workflow.factory.WorkflowTenantMismatchError
- Public surface: true
- Change type: added
- Before: absent — a capability for one tenant could construct another tenant's
  handle, and the execution was then filed under the artifact's tenant
- After: a `WorkflowConstructionError` subclass raised by `construct` when the
  artifact under `authorized.resource` declares a tenant other than
  `authorized.tenant`. The message names both tenants and the key
- Why: §1.3 — the refusal is typed and happens at construction, before any
  handle and therefore before any state. It subclasses the existing
  construction error so handlers that already catch that class keep catching
  this one; the HTTP route currently maps it to 422 through that base and may
  choose a distinct status at the join
- Migration: none required; catch it specifically where a cross-tenant
  attempt should be distinguished from a broken definition

## ccf.workflow.WorkflowTenantMismatchError

- Surface: ccf.workflow.WorkflowTenantMismatchError
- Public surface: true
- Change type: added
- Before: absent
- After: the package re-export, beside `WorkflowConstructionError`, so a caller
  importing the workflow contracts from `ccf.workflow` sees both refusals
- Why: the package already re-exports the construction error family; a new
  member of that family belongs on the same import path
- Migration: none

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: `execute(workflow, *, execution_id)` and
  `resume(workflow, *, execution_id, decision)`; the state key was
  `f"{workflow.definition.tenant}/{execution_id}"`, and the HITL pending event,
  the trace artifact and every typed outcome carried the artifact's tenant
- After: `execute(authorized: Authorized[Execute], workflow, *, execution_id)`
  and `resume(authorized: Authorized[Resume], workflow, *, execution_id,
  decision)`. `verify(authorized, kind=<its own>,
  resource=workflow.definition_key)` is the first statement after the handle
  type check. The state key is derived from `authorized.tenant` and
  `execution_id`; every state-store and trace-store write receives the
  capability and that derived key (the §1.2 derived-writes rule); the pending
  HITL event, the trace artifact and every outcome carry `authorized.tenant`.
  No statement in the module reads the artifact's tenant
- Why: §1.3 verbatim — the engine receives `authorized` for tenant X and files
  under X. `Resume` is its own kind: a deployment that granted *start a
  workflow* has not granted *carry a human decision past its gate* (§1.5), so
  a genuine `Authorized[Execute]` handed to `resume` dies at `verify` before
  the state store is read, and a genuine capability for definition X dies at
  `verify` on a handle for definition Y
- Migration: pass the door's capability first, then the handle. In-process
  callers that constructed and executed with one key now construct and execute
  with one capability; the `tests/workflow/capabilities.py` helpers show the
  minting shape (through the real `mint` over an allowed `AuthzDecision`)

## ccf.orchestration.protocol.OrchestrationProtocol

- Surface: ccf.orchestration.protocol.OrchestrationProtocol
- Public surface: true
- Change type: behavior
- Before: `start_execution(*, workflow, execution_id)` and
  `resume_execution(*, workflow, execution_id, decision)`
- After: `start_execution(*, authorized: Authorized[Execute], workflow,
  execution_id)` and `resume_execution(*, authorized: Authorized[Resume],
  workflow, execution_id, decision)`; still keyword-only throughout, and the
  `authorized` parameter carries no default. The capability type is named
  under `TYPE_CHECKING` from `ccf.authz.capability` — `src` never imports
  `runtime` (D-29)
- Why: a driver threads the capability from whoever invoked it to the engine,
  which verifies it; a driver mints nothing and holds it in no field. The
  Protocol is how a driver receives it
- Migration: an external orchestrator implementing the Protocol adds the
  `authorized` keyword to both verbs and passes it through to the engine
  unchanged. `tests/conformance/test_orchestration.py::test_the_protocol_methods_are_keyword_only_and_typed`
  pins the shape

## ccf_runtime.orchestration.reference.WorkflowEngineOrchestrationAdapter

- Surface: ccf_runtime.orchestration.reference.WorkflowEngineOrchestrationAdapter
- Public surface: true
- Change type: behavior
- Before: the two verbs delegated `(workflow, execution_id[, decision])` to the
  engine
- After: the two verbs take `authorized` and delegate it first, verbatim; the
  adapter reads nothing out of it
- Why: the reference leg is the byte-for-byte comparison target for every
  driver's replay landing; it passes the capability through and adds nothing
- Migration: pass `authorized=` to both verbs

## ccf_runtime.orchestration.langgraph.driver.LangGraphWorkflowDriver

- Surface: ccf_runtime.orchestration.langgraph.driver.LangGraphWorkflowDriver
- Public surface: true
- Change type: behavior
- Before: `start_execution(*, workflow, execution_id)`,
  `resume_execution(*, workflow, execution_id, decision)`,
  `checkpointed_values(*, workflow, execution_id)`; graph position and the
  driver's outcome key used the artifact's tenant
- After: both verbs take `authorized` and close the engine call over it — the
  `drive` node in a start run, the post-interrupt half of `gate` in a resume
  run; the node a run presented no capability for raises the typed driver
  error if reached, which the topology does not do. Position is keyed by
  `authorized.tenant`; `checkpointed_values(*, tenant, execution_id)` takes
  that tenant rather than a handle to read one from
- Why: the capability lives in the closure of the call that received it and
  dies with it — no driver field holds one, pinned by
  `tests/conformance/test_orchestration.py::test_the_driver_retains_no_capability_after_a_drive`
  — and the driver's own position key is the engine's key (§1.3)
- Migration: pass `authorized=` to both verbs; introspection callers pass the
  tenant the engine filed under (the suspend handle's `tenant`)

## ccf_runtime.orchestration.adk.driver.AdkWorkflowDriver

- Surface: ccf_runtime.orchestration.adk.driver.AdkWorkflowDriver
- Public surface: true
- Change type: behavior
- Before: `start_execution(*, workflow, execution_id)`,
  `resume_execution(*, workflow, execution_id, decision)`,
  `persisted_state(*, workflow, execution_id)`; the ADK session id and the
  outcome key used the artifact's tenant
- After: both verbs take `authorized` and the `_EngineSegment` sub-agent runs
  the closure built over it; session id and outcome key use
  `authorized.tenant`; `persisted_state(*, tenant, execution_id)`
- Why: as for the LangGraph leg — the capability travels in the closure, and
  position is keyed by the tenant the engine files under
- Migration: pass `authorized=` to both verbs; introspection callers pass the
  tenant

## ccf_runtime.orchestration.claude_agent.driver.ClaudeAgentWorkflowDriver

- Surface: ccf_runtime.orchestration.claude_agent.driver.ClaudeAgentWorkflowDriver
- Public surface: true
- Change type: behavior
- Before: `start_execution(*, workflow, execution_id)`,
  `resume_execution(*, workflow, execution_id, decision)`,
  `session_transcript(*, workflow, execution_id)`; the session's two tools
  called the engine directly, and an engine exception inside a tool was
  converted by the SDK-MCP server into an `isError` result carrying only
  `str(e)`, after which the turn ended looking successful and the driver
  raised `SegmentNotExecutedError` — the engine's refusal reported as a
  segment that never ran
- After: both verbs take `authorized`; the tools are guarded closures built per
  turn over the engine and the capability; a tool that raises keeps the
  exception in the turn's own box and answers an error result, the scripted
  transport fails the turn visibly, and `_drive` re-raises the engine's
  exception **verbatim** — so a `CapabilityBypassError` surfaces from this leg
  exactly as the other legs propagate it natively. Session id, outcome key and
  transcript use `authorized.tenant`; `session_transcript(*, tenant,
  execution_id)`
- Why: the capability travels in the closure; and a leg must not report the
  engine's refusal as absence of execution. Pinned on every leg by
  `tests/conformance/test_orchestration.py::test_a_wrong_kind_capability_reaches_no_engine_state_through_the_leg`
- Migration: pass `authorized=` to both verbs; introspection callers pass the
  tenant; callers that matched `SegmentNotExecutedError` for an engine failure
  now receive the engine's own exception

## THE DECISION INSIDE THIS, STATED BECAUSE IT IS A POSTURE CHANGE

**There is no tenant in the workflow surface except the capability's.** A
handle constructed under tenant A's capability and executed under tenant B's
capability for the same key files under B — nothing lands under A. The served
path never produces that divergence (the route uses one capability for both
calls); the in-process case is exactly what distinguishes *the key is derived
from the capability* from *the key is derived from the artifact*, and it is
pinned by
`tests/workflow/test_tenant_is_the_capabilitys.py::test_the_execution_is_filed_under_the_capabilitys_tenant_not_the_artifacts`.
Severing it — re-deriving the tenant from the artifact — reddened that test,
the engine's structural control, and the same test through all four driver
legs.

## Regression evidence

`tests/workflow/test_tenant_is_the_capabilitys.py` (new, 12 tests),
`tests/workflow/test_workflow_static.py` (new; mypy against the real
signatures, 3 wrong-kind and 1 no-capability control) and additions to
`tests/workflow/test_factory.py` and
`tests/conformance/test_orchestration.py`; every existing engine, slice,
exception-path, debt-handoff and conformance test migrated to mint through the
real `mint`. The load-bearing red was the fork-shaped
`test_p2_a_capability_for_tenant_b_cannot_file_an_execution_under_a` failing
with a `WorkflowStateRecord` present under `acme-bank/exec-p2` — the finding as
an executable artifact.

**Sabotage-verified, 7 severings, 7 reddened**, each applied alone against
the full owned suites and restored: engine reads the artifact's tenant (6
reds), drop the factory's one comparison (3), skip `verify` in resume (5),
skip `verify` in execute (11), drop the resource bind (4), LangGraph keys
position by the artifact's tenant (2), widen `resume`'s static type (1 — the
static control alone, so the two teeth are two).

## The join this leaves, named

- `runtime/ccf_runtime/http_api/routes/workflow.py` (HTTP lane): the three
  call sites take the gate's capability first. Measured: whole-tree
  `mypy --strict` reports exactly five errors, all in that file, and
  `tests/http_api/test_routes.py::test_workflow_invocation_runs_to_the_typed_terminal`
  fails on `construct()`'s deleted keyword.
- `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine` — the two
  `JOIN`-marked derived-write sites take Lane HANDLES's argument lists. One
  shape question is open there: §1.2's table derives a state key from
  `authorized.tenant` + `authorized.resource`, but for the engine the resource
  is the *definition* key and the state key is `tenant/execution_id`; the
  derived-writes paragraph governs, so the store must accept the derived key
  explicitly.

## What this does not close

The `D-IMPL-350` residual is unchanged: no artifact declares which transition
target a recorded verdict may take, so a recorded rejection can still be
routed down the approving branch. That is a declared-mapping question, not a
tenant question, and it is pinned where it was.
