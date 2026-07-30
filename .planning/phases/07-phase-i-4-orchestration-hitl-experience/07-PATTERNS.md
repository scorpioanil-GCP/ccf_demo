# Phase 7: Phase I.4 — Orchestration, HITL, Experience - Pattern Map

**Mapped:** 2026-07-30
**Files analyzed:** 18 new/modified surfaces
**Analogs found:** 16 / 18 (CLI and HTTP API have no in-repo front-door analog; nearest role-matches noted)

All paths are repo-relative from `/home/parkave/ccf_code`. Line numbers verified against the tree this session (D-24 discipline: re-verify at plan-write time).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/ccf/workflow/definitions.py` (new — `WorkflowDefinition` wrapper, D-11) | model/contract | artifact validation | `src/ccf/agents/definitions.py` | exact |
| Workflow engine + suspended-state record (runtime side per D-14; exact split is Open Question 2) | service (state machine) | event-driven, suspend/resume | `src/ccf/skills/grants.py` `GrantLedger` | exact (same seam, same audit, same injection) |
| `src/ccf/controlplane/state.py` (modified — D-08 token + audited write) | service/config | CRUD over Control Plane state | `src/ccf/peering/admission.py` `AdmittedProduct` (token) + `src/ccf/controlplane/audit.py` (audit path) | exact |
| `src/ccf/skills/grants.py` (modified — retrofit `_put_state` at `:511-517`) | service | CRUD | itself | exact |
| `src/ccf/hitl/` primitives (ApprovalGate, ExceptionEscalation, OverrideBoundary, ReviewQueue) | service + model | request-response / queue | `src/ccf/skills/grants.py` (`ApprovalSink`/`ApprovalOutcome`/`GrantRefusal` family) | exact |
| `HITLTransportProtocol` + `HumanPrincipalBinding` (new, `/src`) | protocol + model | pub-sub / queue | `src/ccf/controlplane/state.py` (Protocol + reference impl shape); `AuditEvent` for binding fields | role-match |
| `src/ccf/replay/record.py` (modified — dims 2/4/5 extensions) | model | transform | itself — the `HarnessTrace` three-edit pattern | exact |
| `src/ccf/skills/catalog.py` (modified — D-IMPL-56: `description`, `SkillArgumentSchema`, `procedure` type) | model | validation | itself (`_BINDING_CONTRACTS` row + Literal member pattern) | exact |
| Shared tool-surface derivation module (new, `/src`, imported by all 3 adapters) | utility | transform | `runtime/ccf_runtime/adapters/claude_agent/adapter.py:127` `_tool_description` (the thing being replaced/centralized) | exact |
| HITL MCP transport + Experience MCP edge (`runtime/ccf_runtime/mcp/`, new module) | server (MCP) | request-response | `runtime/ccf_runtime/mcp/egress.py` | exact |
| HTTP API skeleton (`runtime/ccf_runtime/http_api/`, FastAPI) | controller | request-response | `runtime/ccf_runtime/mcp/egress.py` (injection + no-defaults posture only) | role-match |
| `ccf` CLI (`runtime/ccf_runtime/cli/`, argparse + httpx) | controller | request-response | **no analog** — see No Analog Found | none |
| `OrchestrationProtocol` (new, `/src`) | protocol | request-response | `src/ccf/harness/protocol.py` + `egress.py` `ProductResolverProtocol` | exact |
| `runtime/ccf_runtime/orchestration/{langgraph,adk,claude_agent}/` (×3, D-06) | adapter | event-driven | `runtime/ccf_runtime/adapters/<sdk>/adapter.py` — pattern-copy with A7/D-19 caution | role-match |
| `tools/lints/harness_imports.py` (modified — orchestration carve-out + adapter↔orchestration import ban) | config/lint | batch | itself | exact |
| `tests/conformance/test_orchestration.py` (new) + `test_approval_sink.py` param join | test | — | `tests/conformance/test_harness_adapter.py` (leg struct) + `test_approval_sink.py` (reserved slot) | exact |
| `tests/invariants/test_replay_by_construction.py` (modified — flip 2 checks) | test | — | itself, `:110`/`:119` | exact |
| `tests/workflow/`, `tests/hitl/`, `tests/cli/`, `tests/http_api/` (new trees) | test | — | `tests/conformance/` + `tests/invariants/` fixtures under `tests/fixtures/banking/` | role-match |

## Pattern Assignments

### `WorkflowDefinition` (new artifact contract, D-11)

**Analog:** `src/ccf/agents/definitions.py` — copy its whole discipline.

**Imports pattern** (`definitions.py:34-43`):
```python
from __future__ import annotations
from collections.abc import Mapping
from pydantic import field_validator, model_validator
from ccf.artifacts.protocol import ArtifactStoreError, parse_artifact_uri
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import ArtifactClass, validate_semver
__ccf_mode__ = "algorithmic"
```

**Two-lane versioning base** (`definitions.py:94-110`): subclass the `_TwoLaneVersioned` shape — `schema_version` + `artifact_version`, both `validate_semver`-checked. `WorkflowDefinition` should subclass/mirror `_TwoLaneVersioned` exactly as `TaskDefinition` (`:288`) does.

**Ref validation** (`definitions.py:79-91`): pinned-URI refs via `_validate_artifact_ref` → `parse_artifact_uri`; `@latest` refused. Per-node exception refs (D-13) and the task-definition ref on the wrapper use this exact helper.

**Validator voice** (`definitions.py:269-285`, `_ref_agrees_with_kind`): `model_validator(mode="after")` raising `ValueError` with a message citing the ruling and CLAUDE.md section. **D-12: this validator stays byte-identical** — approval-policy bindings key gates **by step name on the wrapper**, never a step-level ref.

**Artifact class registration** (`definitions.py:330-337`):
```python
TASK_DEFINITION = ArtifactClass(class_id="ccf.task-definition", contract=TaskDefinition)
```
New: `WORKFLOW_DEFINITION = ArtifactClass(class_id="ccf.workflow-definition", contract=WorkflowDefinition)`.

---

### Workflow engine + suspended-state record

**Analog:** `src/ccf/skills/grants.py` `GrantLedger` (`:410-525`) — the only shipped state machine over the Control Plane state seam. Copy four things:

**Constructor injection** (`grants.py:468-492`): registry, catalog/audit/sink/clock all keyword-only injected; audit log constrained to `control_plane.audit_log` with `SplitAuditPlaneError` on any other log (`:477-485` — INV-CH7-71, one audit plane). The engine takes clock, state store, audit, harness bindings the same way; **no wall clock** (D-14 note; `record.py:31-32` "Nothing here reads a clock").

**Opaque-record discipline** (`grants.py:496-517` + `state.py:24-28`): typed record defined next to the machine (`GrantStateRecord` under record class `GRANT_STATE`), `get` with `isinstance` check raising a typed error on a foreign record (`:501-508`), writes through one private helper:
```python
def _put_state(self, grant_hash, state, grant) -> None:
    self._state_store.put(GRANT_STATE, grant_hash, GrantStateRecord(state=state, grant=grant))
```
Workflow state record follows: `WORKFLOW_STATE` record class + `WorkflowStateRecord`, keyed `(tenant, execution_id)` (D-23 multi-principal). This `_put_state` is also the **single textual `put` call site** the D-20 closure retrofits (research corrected D-09's "8 sites").

**Audit-every-transition** (`grants.py:529-539` `_record`): every transition, refusals included, through `self._audit.append(action=..., resolved=..., actor=...)`. New `AuditAction` members are enum-literal additions to `src/ccf/controlplane/audit.py:62-76` with a doctrinal comment, per the `skill_invoked` precedent (`audit.py:56-61`).

**Terminal-trace to ArtifactStore, live state native** (D-IMPL-18/27): mirror `state.py:1-22` module-docstring split.

---

### D-20 state-seam closure (`src/ccf/controlplane/state.py` modified)

**Analog for the token:** `src/ccf/peering/admission.py:496-530` `AdmittedProduct` — the shape that already produced a `DID NOT RAISE` counterfactual in D-GATE-I.3. Key properties to copy: not constructible outside its module; holding one *is* the evidence the checks ran; the consuming surface (`AssemblyWorker.ingest_admitted`) takes *that type* so bypass is unrepresentable. Here: `put(record_class, key, record)` (`state.py:76`, currently token-free) gains a required token parameter only the audited write path can mint; `InMemoryStateStore.put` (`state.py:108`) changes signature identically.

**Analog for the audited surface:** `src/ccf/controlplane/audit.py` `AuditLog.append` (`:124-147`) — the one existing log; no parallel log type (D-08). Docstrings must state the earned claim per D-22.

**Proof pattern (D-10):** counterfactual + adversarial test, per the admission precedent — an active attempt at an unaudited write asserting it cannot succeed.

---

### HITL primitives (`src/ccf/hitl/` new)

**Analog:** the `ApprovalSink` family in `src/ccf/skills/grants.py`.

**Protocol shape** (`grants.py:345-360`):
```python
@runtime_checkable
class ApprovalSink(Protocol):
    def decide(self, grant: SkillGrant) -> ApprovalOutcome: ...
```
The state machine owns every transition and audit record so a sink *cannot* drop the audit obligation. `ApprovalGate` conforms to this existing Protocol (`grants.py:439`: "inherits this seam") and joins the reserved parametrization slot (below) — do not fork a suite.

**Refusal doctrine** (`grants.py:303-342`): rejected approval = typed returned outcome/refusal (`ApprovalOutcome(approved=False, approver_id=...)`, `ApprovalRejected(GrantRefusal)`), never an exception; broken wiring raises. ExceptionEscalation/OverrideBoundary/ReviewQueue verdicts follow the same typed-value shape, audited with `resolved=False` where refused.

**`HumanPrincipalBinding` field style:** `AuditEvent` (`audit.py:79-107`) — required fields, injected `occurred_at`, and the actor doctrine at `:90-94` ("The SDK does not synthesize an identity … identity binding is D-IMPL-21") is the exact hook this type discharges. Fields per D-IMPL-21: approver identity, authentication context, action time, content hash of the Context Product seen (use `content_hash` from `ccf.contracts.canonical`).

**`HITLTransportProtocol`:** Protocol + in-memory reference impl in one module, exactly `state.py:57-118` (`ControlPlaneStateStore` + `InMemoryStateStore`) — `runtime_checkable`, methods docstring-committed, reference impl "not a placeholder for one".

---

### Replay dimension extensions (`src/ccf/replay/record.py` modified)

**Analog:** the file itself — the `HarnessTrace` three-edit pattern (D-IMPL-55), used thrice:

1. **Doctrine line** in the docstring naming the extending phase (`record.py:16-25`: "extend this dimension in I.4").
2. **Positive-sentinel default** (`record.py:79-90, 203-214`): `NO_HARNESS`, `NO_HARNESS_TRACE = HarnessTrace()`, `NO_AGENT_DEFINITION` — never `None`/absence. New sentinels for "no HITL action" / "no workflow trace" follow this voice.
3. **Verbatim pre-serialized block on `build_replay_record`** (`record.py:346-354, 367-372`): optional keyword, recorded verbatim, `None` → sentinel; "derived from what the adapter reported, never reconstructed here."

Placement is code-authoritative (research A4): HITL actions → dimension 2 (`PolicyBindingsSnapshot`, `record.py:156-163` "HITL actions extend this dimension in I.4"); workflow step sequences → dimension 5 (`record.py:25`, `ContentGenerationPath`); delegation chain → dimension 4's existing `delegation_chain` field (`record.py:258-263` — "extend the same field with no further contract change"). Six dimensions = fidelity defect (INV-CH7-80).

---

### D-IMPL-56 (`src/ccf/skills/catalog.py` modified + shared derivation module)

**Analog:** the file's own new-type recipe (`catalog.py:66-71, 140-149`): a new skill type is a new `SkillType` Literal member + a new `_BINDING_CONTRACTS` row (the symbol is `_BINDING_CONTRACTS`, **not** `BINDING_BY_TYPE` — catalogued wrong belief) + a new binding contract class in the `LocalCallableBinding`/`ToolBinding` style (`:84-137`), enforced by `_binding_agrees_with_skill_type` (`:198-208`). The `procedure` token is ruled (DECISIONS.md:118). `SkillCatalogEntry` (`:173-208`) gains required `description: str` and typed `SkillArgumentSchema` — required-with-no-default per the `SkillRequirements` doctrine (`:152-170`, D-IMPL-38 no-silent-defaults).

**What the derivation module replaces** — the three per-adapter helpers, e.g. `runtime/ccf_runtime/adapters/claude_agent/adapter.py:127-138`:
```python
def _tool_description(entry: SkillCatalogEntry) -> str:
    """...It does **not** author prose about what the skill does..."""
    return f"{entry.name}@{entry.artifact_version} [{entry.skill_type}]"
```
Also `adapters/langgraph/adapter.py:198`, `adapters/adk/adapter.py:162`. The shared derivation lives in `/src` (all three adapters import it; no cross-adapter imports), composes only artifact-carried values (CINV-01), and one three-way equality test (D-17) pins agreement. `procedure`'s SKILL.md body travels via `InstructionBinding` (`definitions.py:180-197`) on seam 1 only.

---

### HITL MCP transport + Experience MCP edge (`runtime/ccf_runtime/mcp/` new module)

**Analog:** `runtime/ccf_runtime/mcp/egress.py` — copy whole-file structure:

**Imports + server construction** (`egress.py:47-56, 127-165`):
```python
from mcp.server.fastmcp import FastMCP
...
server = FastMCP(server_name, stateless_http=True, json_response=True)

@server.resource(PRODUCT_URI_TEMPLATE, mime_type=PRODUCT_MIME_TYPE)
def context_product(tenant: str, product_class: str, version: str) -> str:
    servable = resolver(tenant=tenant, product_class=product_class, version=version)
    return canonical_bytes(servable.product).decode("utf-8")
```
`stateless_http=True` is load-bearing (B3 deadlock); server built, never started — hosting is the deployment's decision (`:144-149`).

**Resolver-injection seam** (`egress.py:95-116`): keyword-only `Protocol` callable so the server holds no fabric handle — HITL queues get a queue-view Protocol the same way. **Canonical bytes, never `model_dump_json`** (`:154-163`). **Tenancy is a URI segment resolved per call, never a constructor field** (`:35-38`). New role = new module + new row in `tests/invariants/test_mcp_role_separation.py`, never a merged server. Auth posture: `runtime/ccf_runtime/mcp/auth.py`. Webhooks are notify-only (D-IMPL-20): authority flows only through the typed MCP action tools bound to `HumanPrincipalBinding`.

---

### HTTP API skeleton (`runtime/ccf_runtime/http_api/`, new — FastAPI 0.140.0)

**Analog (posture only, role-match):** `egress.py` — build the app, don't host it; every dependency (resolvers, Control Plane handles) constructor/factory-injected; no bind address, server name, or tenant defaults in code (CINV-01). Routes take/return existing `extra=forbid` contracts (`CCFContract` subclasses) directly so `app.openapi()` *is* the contract schema. **No L1/write endpoint** — put it in the plan's must-not list. Module docstring should carry the "What this server cannot do" structural-claim paragraph in the `egress.py:9-25` voice, with the honest D-22 scoping.

---

### `OrchestrationProtocol` (new, `/src`)

**Analog:** `src/ccf/harness/protocol.py` (Protocol-with-carefully-scoped-docstring-claims; do **not** copy or upgrade its wording — D-20 carried) and `egress.py:95-116` for the keyword-only `runtime_checkable` Protocol shape. Name carries the `Protocol` suffix (D-IMPL-59 naming doctrine). Identical replay obligations to the in-SDK engine stated in the docstring, scoped per D-22.

### Orchestrator legs (`runtime/ccf_runtime/orchestration/{langgraph,adk,claude_agent}/`, ×3)

**Analog:** `runtime/ccf_runtime/adapters/<sdk>/adapter.py` for module shape and doctrine — copy the `ClaudeAgentAdapter` class-docstring disciplines (`adapters/claude_agent/adapter.py:141-160`): structural conformance ("declared by shape, not by inheritance"), nothing held per-call that the Control Plane owns, deployment values injected. **Do not copy `_build_graph` topology into the engine** (A7/D-19); the D-06 module split plus a bidirectional import ban makes that unrepresentable. LangGraph leg: `interrupt()`/`Command(resume=...)` maps to CCF suspend/resume, but the CCF engine stays authoritative for state + audit — the LangGraph checkpointer holds only graph position.

### Lint extension (`tools/lints/harness_imports.py` modified)

**Analog:** itself. The carve-out is a module-path frozenset constant, never a data file (`:29-31`, `:65`):
```python
HARNESS_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf_runtime.adapters"})
```
Add `ccf_runtime.orchestration` as its **own considered entry** (not a widened prefix), with D-24 negative tests (a harness import in `ccf_runtime.peering`/`ccf_runtime.cdc` must still fail). The adapter↔orchestration import ban follows the `WRITER_MODULE`/`WRITER_OK_MODULES` two-constant + `matches_module` shape (`:67-69`, `:104-117`), dot-bounded matching.

---

### Conformance + invariant tests

**ApprovalGate joins the reserved slot** — `tests/conformance/test_approval_sink.py:56-73`:
```python
@pytest.fixture(params=["scripted-double"])
def sink_factory(request):
    """...I.4's ApprovalGate adds its own param here; the test bodies below do not change (D-09)."""
```
Add the param; test bodies unchanged. Fixtures from `tests/fixtures/banking/` (`:35`), `pytestmark = pytest.mark.conformance`.

**Orchestration conformance suite** — analog `tests/conformance/test_harness_adapter.py:1-80`: real SDK objects on real SDK code paths (no doubles), a per-leg `NamedTuple` (`HarnessLeg`) bundling factory + leg-specific drivers so shared test bodies never name an SDK type; skips visible and self-explaining naming SDK + extra; `CCF_REQUIRE_HARNESSES=1` machinery exists.

**CINV-04 flips** — `tests/invariants/test_replay_by_construction.py:109-126`: change each `Check(... status="not-yet-applicable", phase="I.4")` to `status="active", owning_test="<real test node id>"` for `hitl-action-capture` and `workflow-trace-capture`. The owning test must fail under the broken implementation (D-25).

## Shared Patterns

### Contract base
**Source:** `ccf.contracts.base.CCFContract` (imported everywhere above) — Pydantic, `extra=forbid`, frozen, canonically serializable. **Apply to:** every new model in `/src` and `/runtime`.

### Canonical serialization / content identity
**Source:** `ccf.contracts.canonical.content_hash` / `canonical_bytes` (see `egress.py:154-163`, `record.py:131-140`). Never `model_dump()` into replay/canonical paths. **Apply to:** workflow trace, HITL records, `HumanPrincipalBinding` content hash, MCP bodies.

### Docstring citation discipline
Every public class cites the whitepaper section or CLAUDE.md section + ruling, marks SDK-defined extensions explicitly, and states its `__ccf_mode__ = "algorithmic"` tag where applicable (every `/src` excerpt above). Invariant claims scoped to actual enforcement (D-22).

### Positive sentinels
**Source:** `record.py:71-90` (`MODE_1_MODEL_VERSION`, `NO_GRANTS_SET_HASH`, `NO_HARNESS`, `NO_AGENT_DEFINITION`). Absence is an asserted claim. **Apply to:** all replay extensions; note D-16 deliberately *excludes* skill `description` from sentinel treatment (required, no default).

### Constructor injection + injected clock
**Source:** `grants.py:468-492`. **Apply to:** workflow engine, HITL primitives, transports.

### Error taxonomy
Governance verdict = typed returned refusal/outcome (`GrantRefusal` subclasses, `ApprovalOutcome`); wiring defect = raise (`GrantTransitionError`, `SkillNotInCatalog` at `catalog.py:74-81` — "Raised, never defaulted"). **Apply to:** all four HITL primitives, workflow exception paths.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `runtime/ccf_runtime/cli/` (`ccf` CLI) | controller | request-response | No CLI exists anywhere in the repo. Use stdlib argparse noun-verb subparsers + `[project.scripts]` per RESEARCH; copy only the shared postures above (CINV-01 in help text, B3 one-session-per-call, zero privileged paths per D-IMPL-22) |
| HTTP API framework wiring (FastAPI app/router layout) | controller | request-response | No HTTP controller exists; `egress.py` supplies injection/no-defaults posture but not FastAPI routing shape — follow RESEARCH's stack section and FastAPI-standard `APIRouter`-per-noun structure mirroring the CLI noun set |

## Metadata

**Analog search scope:** `src/ccf/{controlplane,agents,skills,replay,harness,peering,mcp,contracts}`, `runtime/ccf_runtime/{mcp,adapters}`, `tools/lints`, `tests/{conformance,invariants}`
**Files scanned:** ~20 read in-depth; directory listings across `/src`, `/runtime`, `/tests`
**Pattern extraction date:** 2026-07-30
