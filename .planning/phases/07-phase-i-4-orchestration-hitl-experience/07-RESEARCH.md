# Phase 7: Phase I.4 — Orchestration, HITL, Experience - Research

**Researched:** 2026-07-30
**Domain:** In-SDK workflow state machine + HITL primitives + three v0 front doors (MCP egress / CLI / HTTP+OpenAPI) + three external-orchestrator legs (D-IMPL-60)
**Confidence:** HIGH (nearly everything this phase needs already exists in-repo as gated code, reserved extension points, or resolved rulings; the one genuinely open semantic — absent per-node exception refs — is flagged, not defaulted)

<user_constraints>
## User Constraints (from 07-CONTEXT.md)

### Locked Decisions

**Build sequencing & slice**

- **D-01:** **Vertical slice first**, continuing the I.1/I.2/I.3 pattern. The slice is **a two-step workflow that suspends on one real ApprovalGate and resumes on approval**, with the human action and the step sequence both landing in the replay record. Chosen as the thinnest path that exercises everything structurally novel in this phase at once: the engine, the Control Plane state seam (and therefore the D-20 closure), a real HITL primitive replacing I.2's scripted test double, and **both** CINV-04 skips. A straight-line no-gate workflow was rejected deliberately — it would defer suspend/resume, which is the actual hard part, into wave 2.
- **D-02:** Waves widen **engine → HITL → front doors → orchestrators → gate**: (a) Workflow engine + the D-20 state-seam closure + D-IMPL-56 (see D-14); (b) the remaining three HITL primitives (ExceptionEscalation, OverrideBoundary, ReviewQueue) with their transports; (c) the three front doors (MCP egress incl. the Experience edge, HTTP+OpenAPI, CLI); (d) the three `OrchestrationProtocol` driver integrations; (e) gate wave. **Front doors deliberately precede the orchestrator legs** (Dave's ruling over the I.3-mirroring alternative): criterion 4 is banked before the phase's largest external unknown opens, and the orchestrator legs get a real HTTP surface to drive if that proves the cleanest integration path.
- **D-03:** **One phase, one gate.** ORCH + HITL + EXPR ship and gate together as `D-GATE-I.4`, matching the ROADMAP as written. Splitting into I.4a/I.4b and a mid-phase review checkpoint were both offered and declined. Planning should expect this to be the largest plan count yet (I.3 was 25).
- **D-04:** **Test fixtures in I.4, polished examples in I.5** — unchanged from I.3 D-06. Every wave builds its proof as a test fixture; `examples/05` and `examples/06` land in Phase 8.

**OrchestrationProtocol — all three SDKs, not only LangGraph** (a widening of D-IMPL-17, raised unprompted by Dave)

- **D-05:** **Three real driver integrations.** Google ADK, the Claude Agent SDK, and LangGraph each get a real `OrchestrationProtocol` integration in `/runtime` that drives a CCF workflow end-to-end through **that SDK's own topology surface**, all three exercised by one factory-parametrized conformance suite. The "one deep, then two against the suite" staging (I.3's D-07 pattern) was offered and **declined** — all three are real legs. Build *order within the wave* remains planner-level per the `D-GATE-F` precedent (intra-phase staging is sequencing, not a revision of a ruling); that does not reduce the leg count below three.
- **D-06:** **Structural enforcement of the two-seam distinction: separate module trees.** Orchestrator integrations live under `runtime/ccf_runtime/orchestration/<sdk>/` and **never** inside `runtime/ccf_runtime/adapters/<sdk>/`, with a lint or import test pinning that no orchestration module imports an adapter module and vice versa. This makes advisory **A7**'s failure mode — promoting the LangGraph adapter's private `_build_graph` topology into the SDK's engine — structurally unrepresentable rather than merely documented. It also means the CINV-02 harness-import carve-out must be re-examined: `HARNESS_ADAPTER_MODULES` currently admits `ccf_runtime.adapters` only (I.3 D-24), so the new tree needs its own considered carve-out entry — **and D-24's negative test discipline applies**: a harness import in `ccf_runtime.peering` or `ccf_runtime.cdc` must still fail, or the carve-out is an unguarded prefix match.
- **D-07:** **Recorded as a new numbered entry, `D-IMPL-60`** (next free number; 59 is the current highest), as **Dave's own ruling**, with accepted consequences enumerated the way D-IMPL-24 enumerated its three adapter / three CI / three example legs. `D-IMPL-17` itself is **untouched** and is cross-referenced. Amending an approved `D-GATE-D` ruling in place was offered and declined — consistent with D-IMPL-55/57/58/59, all of which took new numbers rather than editing prior text.

**The D-20 state-seam closure (a prerequisite, not a follow-up)** — `docs/PHASE_I3_GATE.md` §5: *"Closing this … is a prerequisite for the first I.4 plan that touches the seam, not a follow-up."*

- **D-08:** **Both mechanisms.** An audit-bearing write path as the ergonomic surface (following the I.2 precedent — transitions audit through the one existing `AuditLog`, no parallel log type), **plus** a token the raw seam requires so `put()` cannot be reached without one. This is the only option under which the D-21-compliant claim can honestly read **"by construction"** rather than "lint-enforced in shipped surfaces" — and per D-21, the wording in docstrings and the gate document must track whichever it actually earns.
- **D-09:** **All 8 existing grant call sites are retrofitted in the same plan that closes the seam.** Exactly one way to write Control Plane state exists at every point in time. Migrating grants later was offered and declined: two coexisting write patterns is precisely the condition that let the convention drift unnoticed through the I.2 gate.
- **D-10:** **Counterfactual *plus* adversarial proof.** A test that goes red when the closure is reverted (output recorded in the gate document), **and** a test that actively attempts an unaudited write and asserts it cannot succeed. Make both explicit `must_haves` on the closure plan.

**Workflow artifact shape and execution model**

- **D-11:** **`TaskDefinition` keeps the step list; a new `WorkflowDefinition` wraps it.** `TaskDefinition`/`TaskStep` (`src/ccf/agents/definitions.py`) continue to declare the ordered steps they already declare — kinds `skill` / `agent` / `hitl-gate`, refs pinned by versioned URI — and `WorkflowDefinition` adds **only** what a state machine needs on top: explicit transitions, terminal conditions, and exception routing (§8.1). Neither artifact duplicates the other.
- **D-12 (consequence of D-11):** the approval-policy binding for a gate lives on the **wrapper**, so I.2's `_ref_agrees_with_kind` validator stays **byte-identical**. Planning must confirm this holds against the actual gate semantics rather than assume it; if a gate genuinely needs a step-level ref, that is a schema change to gated I.2 code and gets recorded as such, not slipped in.
- **D-13:** **Per-node exception refs**, not a workflow-level routing table. Thresholds and routing values are artifact content, never code constants (CINV-01 / No-Hardcoding §6.4). **Residual for research (flagged, not decided):** what a node with **no** exception ref means — see Open Questions below.
- **D-14:** **Async-first engine, per the existing D-IMPL-04 ruling.** The engine sits on the runtime side of that line. Note the I.3 **B3** finding as a live hazard for any sync/async bridging: the held-session `start_blocking_portal()` bridge **deadlocks** (verified at a 120 s timeout); the working shape was a dedicated background event-loop thread plus one session per call against `stateless_http=True`.

**D-IMPL-56 implementation**

- **D-15:** **Wave-1 prerequisite.** The schema change (required `description` + typed `SkillArgumentSchema`), the one shared three-harness derivation, and the fifth `procedure` skill type all land **before the slice**. The `ccf skill import <dir>` importer follows in the CLI wave as a thin front-end over the already-shipped schema.
- **D-16:** **`description` is required, and every existing fixture gains a real one in the same plan.** No optional phase, no default, no sentinel. Constraint that does not move: no prose describing any particular skill may appear in `/src` or `/runtime` (CINV-01) — descriptions are artifact content.
- **D-17:** **Three-way tool-surface equality assertion.** One test asserts all three adapters' rendered tool surfaces agree on description and argument schema for the same catalog entry.
- **D-18:** **SKILL.md is an authoring format, not a canonical artifact.** Import is one-way; frontmatter `name`/`description` map to the entry's fields, the body becomes a registered `ccf.prompt-artifact`, `references/` become further pinned artifacts. `allowed-tools` is **not** auto-mapped onto `SkillRequirements` (D-IMPL-29).

**Constraints inherited from `docs/PHASE_I3_GATE.md` §5 — prerequisites, not notes**

- **D-19 (A7):** the Workflow primitive is built against **D-IMPL-17's boundary**, *not* by generalizing the LangGraph adapter's `_build_graph`.
- **D-20 (D-22 carried):** `tests/invariants/test_consumption_discipline.py` remains a **direct-import** check with no transitive closure. Any widening of `ALLOWED_CCF_PREFIXES` needs a transitive-closure argument — never a precedent argument. Do not upgrade `src/ccf/harness/protocol.py`'s wording.
- **D-21 (D-IMPL-45):** `TraceCorrelationHook` attaches to the **existing** `harness_trace` slot on replay dimension 3 (delivered in I.3 as D-IMPL-55). Do not mint a new location.
- **D-22 (D-21 carried):** **scope every invariant claim to its actual enforcement.** Write "lint-enforced in shipped surfaces" or "audited by the current implementation" rather than "no path" / "by construction" unless the state is genuinely unrepresentable. Bears hardest on HITL-01.
- **D-23:** **any set-identity, admission decision, or replay claim computed over shared Control Plane state carries a multi-principal case in its plan's `must_haves`** — two tenants, two agents, two approvers. Directly relevant to workflow state keyed per tenant and to `HumanPrincipalBinding`.
- **D-24 (process):** five of six I.3 gap-closure plans carried a path, symbol, or criterion defect. **Tell executors to expect one per plan**, and verify every path and symbol a plan names before the plan is written.
- **D-25 (process):** draft gate-checklist rows from **tests that fail under the broken implementation**, not from plan intent.
- **D-26 (execution environment):** worktree agents fork off `main`, not the phase branch — keep the `EXPECTED_BASE` merge-base guard. No `.venv` in agent worktrees; executors must run `PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python` — `src` alone is not enough. **The post-merge gate on `main` is the load-bearing check.** The merge guard blocks deletions outside `.planning/` cumulatively against the `pre-peering` tag.

### Claude's Discretion

- **Front-door build order and HTTP framework choice.** Planner-level under D-IMPL-22 (thin client over HTTP with `--local`) and D-IMPL-23 (minimal skeleton mirroring the CLI noun set, no L1 endpoint). Note `uvicorn==0.51.0` is already a core dependency while FastAPI is not — an added core dependency needs a stated reason. (Recommendation below.)
- **HITL transport v0 scope.** Planner-level under D-IMPL-20 (MCP endpoints primary, webhooks notify-only). Two sub-questions the planner owns: whether the webhook leg ships in v0 or defers, and whether the real `ApprovalGate` joins the parametrization in `tests/conformance/test_approval_sink.py` — whose docstring already reserves the slot — or gets its own suite. The reserved slot is the strong hint.
- **Replay dimension-5 extension shape.** Follows the thrice-used extension pattern documented at `src/ccf/replay/__init__.py:12` and specified in D-IMPL-55: doctrine line, positive-sentinel default, optional pre-serialized block recorded **verbatim** on `build_replay_record`. The five dimensions stay inviolate (INV-CH7-80).
- **How an orchestrator conformance leg behaves when an SDK is absent** — a skipped leg must be visible and self-explaining, naming which SDK and which extra enables it. CI installs `[dev]`, so all three legs run there.
- Module tree details below the D-06 boundary.

### Deferred Ideas (OUT OF SCOPE)

- Absent per-node exception ref semantics is a **real open question**, not a deferral — research resolves or surfaces it (see Open Questions; surfaced as candidate D-IMPL-61).
- Advisory **A3** (the Claude adapter's hand-built `ResultMessage` seam-4 leg) — Phase 8's obligation; do not let a plan claim it.
- Loop-level harness portability — `examples/03` in Phase 8.
- Advisory A7's underlying tension — documented, bounded by D-06's module split, not resolved by generalizing.
- Heavyweight/durable workflow engine — permanently out of scope (§8.1, §13); reachable only via `OrchestrationProtocol`.
- Human task-management inbox or UI — out of scope (§8.2, §13).
- Mobile SDK, chat adapter, web UI — out of scope for v0 (§8.3).
- Supervision Quality — ruled out of v0 (D-IMPL-48).
- The polished `/examples` suite (`examples/05`, `examples/06`, `examples/03`) — Phase 8 / I.5.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORCH-01 | Workflow primitive with agent nodes and HITL gates, suspendable on Control Plane state; workflow definitions as Control Plane artifacts | §Workflow engine pattern; D-11 wrapper shape verified against `definitions.py` (symbols confirmed); `ControlPlaneStateStore` seam verified (`state.py:58/76`); replay extension points verified reserved (`record.py:25/159/184/262`) |
| ORCH-02 | OrchestrationProtocol for external orchestrator integration | §Orchestrator SDK topology surfaces — all three SDK APIs probed against installed pins; D-06 module-tree + lint pattern; conformance-suite pattern from `tests/conformance/` |
| HITL-01 | Four HITL primitives with audit-by-construction into Decision Replay | §HITL patterns; `ApprovalSink` seam verified (`grants.py:346`, reserved slot at `test_approval_sink.py:5,:62`); CINV-04 skips verified at `test_replay_by_construction.py:110,:119`; D-08 both-mechanisms closure |
| EXPR-01 | MCP server (egress) exposing Context Products and agents | Existing egress verified at `runtime/ccf_runtime/mcp/egress.py`; Experience edge is an addition to it, not new machinery; role-separation invariant test exists (`tests/invariants/test_mcp_role_separation.py`) |
| EXPR-02 | `ccf` CLI — workflow invocation, HITL inspection, replay queries, Control Plane config, agent declaration, skilling, artifact inspection | §CLI stack recommendation (stdlib argparse, `[project.scripts]` entry point, httpx client, `--local` mode) |
| EXPR-03 | HTTP API skeleton with valid OpenAPI spec | §HTTP stack recommendation (FastAPI 0.140.0, slopcheck [OK], stated-reason justification vs. Starlette hand-roll) |
</phase_requirements>

## Summary

This phase is unusually well-specified before planning begins: every extension point it needs was deliberately reserved by prior phases and every governing ruling already exists (D-IMPL-17/18/20/21/22/23/27/45/55/56, plus the new D-IMPL-60 to be recorded per D-07). Research therefore concentrated on (1) verifying every path and symbol the CONTEXT names against the actual tree (D-24 discipline), (2) resolving the two genuinely open technical choices left to discretion — HTTP framework and CLI stack — with package-legitimacy verification, (3) probing the three installed orchestrator SDKs' actual topology surfaces so the D-05 legs can be planned against real APIs, and (4) sharpening the one open semantic question (absent exception refs, D-13 residual) into a decision-ready form.

Verification results: all load-bearing symbols named in the CONTEXT exist as described — `ControlPlaneStateStore.put` (`state.py:76`, no token, no audit), `TASK_STEP_KINDS`/`TaskStep`/`_ref_agrees_with_kind` (`definitions.py:239–261`), `ApprovalSink` (`grants.py:346`) with the reserved conformance slot, the three per-adapter `_tool_description` helpers D-IMPL-56 deletes (all three confirmed at `adapters/{claude_agent,langgraph,adk}/adapter.py`), all four reserved replay extension points in `record.py`, both `not-yet-applicable` CINV-04 checks, and `HARNESS_ADAPTER_MODULES` in `tools/lints/harness_imports.py:65`. **One discrepancy found:** D-09's "8 existing grant call sites" does not match a textual count — `grants.py` has exactly **one** `_state_store.put` site (`:515`, inside a helper that multiple logical grant transitions flow through) plus reads at `:498/:523`. The property D-09 protects (one write pattern at a time, all writers retrofitted in the closure plan) is unaffected; the planner should write the closure plan against "every `ControlPlaneStateStore.put` caller" rather than a count. This is exactly the class of defect D-24 predicts.

**Primary recommendation:** plan the waves as ruled (D-02), add FastAPI 0.140.0 as a core dependency with the stated reason below, build the CLI on stdlib `argparse` + a direct `httpx` pin, map each orchestrator leg onto the verified SDK topology surface listed below, and route the absent-exception-ref semantics to Dave as candidate D-IMPL-61 (recommended reading enclosed) rather than defaulting it.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `WorkflowDefinition` contract + validation | `/src` (sync core, `ccf.agents` or new `ccf.workflow` contracts module) | — | Artifact schema is fabric vocabulary; No-Hardcoding interprets it |
| Workflow engine (state machine, suspend/resume) | `/runtime` (async-first, per D-14/D-IMPL-04) | `/src` for the state-record contract defined next to the machine? No — record type lives with the machine per `state.py` docstring; if machine is runtime, record is runtime | Engine is execution; D-IMPL-04 puts async execution runtime-side. Planner must decide the exact split and verify against the `state.py` "defined next to the machine that transitions it" doctrine |
| `OrchestrationProtocol` (the seam) | `/src` (Protocol, suffixed name per D-IMPL-59 naming doctrine) | — | Every pluggable-substrate seam with `/runtime` impls carries the `Protocol` suffix |
| Orchestrator driver integrations (×3) | `runtime/ccf_runtime/orchestration/<sdk>/` | — | D-06 locked; never under `adapters/` |
| HITL primitive contracts + `HITLTransportProtocol` + `HumanPrincipalBinding` | `/src` | — | Typed contracts at the boundary; transport impls pluggable |
| HITL MCP transport (queues as Resources, actions as Tools) | `/runtime` (MCP server side) | — | Same posture as egress/artifact servers |
| D-20 state-seam closure (audit-bearing write + token) | `/src` (`ccf.controlplane.state` + audit) | — | Control Plane is the audit plane (whitepaper §7.8.2) |
| D-IMPL-56 (`description`, `SkillArgumentSchema`, `procedure` type, shared derivation) | `/src` (`ccf.skills.catalog` + one shared derivation module) | `/runtime` adapters consume it (delete `_tool_description` ×3) | Shared derivation must live where all three adapters can import without cross-adapter imports |
| HTTP API skeleton + OpenAPI | `/runtime` | — | Front door; uvicorn-hosted like egress |
| `ccf` CLI | `/runtime` + `[project.scripts]` in pyproject | — | Thin client over HTTP with `--local`; zero privileged paths |
| MCP Experience edge (agents + products) | `runtime/ccf_runtime/mcp/` (extend egress module family) | — | Addition to existing machinery; keep role separation (`test_mcp_role_separation.py`) |
| Replay dimension 4/5 extensions | `/src` (`ccf.replay.record`) | — | Thrice-used three-edit pattern; five dimensions inviolate |

## Standard Stack

### Core (changes this phase)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| fastapi | 0.140.0 | HTTP API skeleton + OpenAPI generation (EXPR-03) | **New core dependency — stated reason:** D-IMPL-23 requires "OpenAPI generated from the existing `extra=forbid` contracts." FastAPI does exactly that natively from Pydantic v2 models; hand-assembling an OpenAPI document from `model_json_schema()` is a hand-roll of a solved problem with a spec-drift failure mode. Its only dependencies (starlette, pydantic, typing-extensions, annotated-doc, typing-inspection) are all already present. `[VERIFIED: slopcheck OK, pypi; already installed at 0.140.0 in the project venv via google-adk's `fastapi>=0.133,<1` constraint — pin is compatible]` |
| httpx | 0.28.1 | CLI HTTP client (EXPR-02) | Already guaranteed transitively via `mcp` (pyproject comment notes this); a **direct pin with stated reason** is the honest posture once first-party code imports it. `[VERIFIED: slopcheck OK, pypi; installed 0.28.1]` |
| (stdlib) argparse | py3.12 | `ccf <noun> <verb>` CLI | Zero new dependency for a thin client; subparser-per-noun matches D-IMPL-22's shape. click 8.4.2 / typer 0.27.0 exist in the venv **only transitively** (harness extras) and must not be relied on in core `[VERIFIED: pip list]` |

Everything else this phase uses is already pinned and gated: `pydantic==2.13.4`, `mcp==1.28.1`, `uvicorn==0.51.0`, `pytest==9.1.1`, `hypothesis==6.161.5`, and the three harness extras `google-adk==2.5.0`, `claude-agent-sdk==0.2.128`, `langgraph==1.2.9` (which the D-05 orchestrator legs reuse — **no new SDK dependencies needed**). `[VERIFIED: pyproject.toml + pip list]`

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Starlette (already transitive) + hand-assembled OpenAPI from `model_json_schema()` | No new direct dep, but the OpenAPI document becomes first-party maintained prose — exactly the "valid OpenAPI spec" criterion turned into an ongoing drift liability. Rejected under Don't-Hand-Roll |
| argparse | click/typer as new core deps | Nicer ergonomics; but D-IMPL-22's CLI is deliberately thin and "an added core dependency needs a stated reason" — there isn't a strong one for a noun-verb dispatcher |

**Installation:** no new install command; add the two pins to `[project] dependencies` in `pyproject.toml` with stated-reason comments matching house style.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| fastapi | PyPI | ~7 yrs | very high | github.com/fastapi/fastapi | [OK] | Approved (new direct pin) |
| starlette | PyPI | ~7 yrs | very high | github.com/encode/starlette | [OK] | Stays transitive (via fastapi/mcp) |
| httpx | PyPI | ~6 yrs | very high | github.com/encode/httpx | [OK] | Approved (promote transitive → direct pin) |

**Packages removed due to slopcheck [SLOP] verdict:** none. **Flagged [SUS]:** none. All slopcheck runs performed 2026-07-30 in this session.

## Architecture Patterns

### Workflow engine (ORCH-01)

- **Artifact shape (D-11):** `WorkflowDefinition` wraps a `TaskDefinition` ref (pinned versioned URI, per D-IMPL-26 doctrine used everywhere else) and adds transitions, terminal conditions, per-node exception refs, and per-gate approval-policy bindings. Verified: `TaskStep` at `definitions.py:242` carries `kind`/`name`/`ref: str | None`, `TASK_STEP_KINDS = {"skill","agent","hitl-gate"}` at `:239`, and the `hitl-gate`-must-not-carry-ref docstring commitment at `:249–252` — D-12's byte-identical constraint is satisfiable because approval-policy bindings key gates **by step name on the wrapper**. `[VERIFIED: codebase]`
- **State machine:** explicit states, transitions, terminal conditions (§8.1). Suspended state = a typed versioned record on `ControlPlaneStateStore` under its own `record_class` (the store is deliberately opaque — `state.py` docstring says the record type is defined next to the machine, never in `state.py`). `[VERIFIED: state.py:58–110 + module docstring]` D-IMPL-18: every transition appends to the execution trace; trace writes through to the ArtifactStore at each suspend and at terminal; D-IMPL-27: live suspended state native, terminal trace ArtifactStore.
- **State keying must be multi-principal from day one (D-23):** key suspended state by `(tenant, workflow execution id)`, and write the two-tenant / two-approver tests into the slice plan's `must_haves`, not a later hardening wave.
- **Clock, store, audit log, sink, harness bindings: constructor-injected** (established pattern; a wall clock in the engine makes suspend/resume timestamps untestable).
- **Agent nodes resolve through `HarnessAdapterProtocol`** — the workflow names an agent definition ref, never a harness. Do not touch `src/ccf/harness/protocol.py` wording (D-20).
- **Replay:** step sequence → dimension 5, delegation chain extension → dimension 4's existing `delegation_chain` field ("I.4 workflow chains extend the same field with no further contract change", `record.py:262`), HITL actions → dimension 2 (`PolicyBindingsSnapshot` docstring: "HITL actions extend this dimension in I.4"). Use the three-edit D-IMPL-55 pattern: doctrine line, positive-sentinel default, verbatim pre-serialized block on `build_replay_record`. `[VERIFIED: record.py:20–30, :155–162, :258–266]` Note the CINV-04 skip text says HITL lands in **dimension 2** while the CONTEXT phase-boundary prose says the whitepaper reserves dimensions 4 and 5 for "workflow traces and HITL actions" — the code's reservations are authoritative here: HITL → dimension 2 (`record.py:159` region), workflow step sequences → dimension 5, delegation chain → dimension 4. Plans should cite the code lines.
- **Hypothesis stateful testing** (`hypothesis.stateful.RuleBasedStateMachine`) is a strong fit for the engine — 73+ properties already wired, and suspend/resume/exception transitions are exactly the interleaving space where example-based tests under-cover. Recommend one stateful suite for the engine core. `[VERIFIED: hypothesis 6.161.5 installed]`

### D-20 state-seam closure (wave 1, before or with the slice)

Current seam: `ControlPlaneStateStore.put(record_class, key, record)` — no token parameter, no audit. `[VERIFIED: state.py:76]` D-08 requires both: (a) an audit-bearing write surface (through the one existing `AuditLog` — see `src/ccf/controlplane/audit.py`), and (b) a required token on the raw `put()` so unaudited writes are unrepresentable. The proven in-repo precedent for the token mechanism is I.3's `AdmittedProduct` admission token (its neutering produced `DID NOT RAISE AdmissionBypassError`, recorded in D-GATE-I.3) — reuse that shape, not a new invention. Retrofit **every** `ControlPlaneStateStore.put` caller in the same plan; the current writers are `grants.py:515` (the single textual site all grant transitions flow through). **D-09's "8 call sites" figure is not literally true against the tree** — record the deviation, preserve the property (one write pattern, zero unmigrated writers). Protocol *implementations* (`InMemoryStateStore.put`, `state.py:108`) change signature too; check for any other `ControlPlaneStateStore` implementations before writing the plan (`peering/admission.py` and `controlplane/registry.py` reference the store — verify read vs. write). `[VERIFIED: grep]`

### HITL primitives (HITL-01)

- All four are typed primitives in `/src` over `HITLTransportProtocol` (D-IMPL-20: typed queue; MCP endpoints primary, webhooks notify-only — notification and authority separated so audit-by-construction cannot be bypassed).
- `ApprovalGate` **conforms to the existing `ApprovalSink` Protocol** — `grants.py:439`: "the suspending ApprovalGate that I.4 brings inherits this seam rather than a re-opened question"; `grants.py:24`: "ApprovalGate joins with zero state-machine change." The conformance slot is pre-reserved at `tests/conformance/test_approval_sink.py:5` and `:62` — join the parametrization (the strong hint) rather than fork a suite. `[VERIFIED: codebase]`
- `HumanPrincipalBinding` (D-IMPL-21): approver identity, authentication context, action time, content hash of the Context Product the approver saw. No HITL action lands without one. `grants.py:337` explicitly defers the human principal to this phase. Multi-approver test required (D-23).
- **Refusal doctrine:** a rejected approval is a typed returned refusal (pattern: `GateRefusal`/`GrantRefusal`/...); a gate wired to a nonexistent artifact raises. Audit refusals with `resolved=False`.
- **The "by construction" claim (criterion 2) is earned by the D-08 token + the CINV-04 check activation.** Flip both `not-yet-applicable` checks (`tests/invariants/test_replay_by_construction.py:110` `hitl-action-capture`, `:119` `workflow-trace-capture`) to `active` with real owning tests; suite skip count goes to zero. Per D-22, if any HITL path's enforcement is lint-shaped rather than unrepresentable, the docstrings must say so.

### Front doors (EXPR-01/02/03)

- **MCP Experience edge:** extend the `runtime/ccf_runtime/mcp/` family (egress exists; artifact server exists; role separation is invariant-tested). Agents exposed as MCP Tools, products as Resources, HITL queues as Resources + actions as Tools (integration point already named in CONTEXT). Keep the new role in its own module — `tests/invariants/test_mcp_role_separation.py` will need a new row, not a merged server.
- **HTTP API:** FastAPI app hosted by the already-pinned uvicorn, mirroring the CLI noun set (D-IMPL-23), **no L1 ingestion endpoint** (single-writer: a generic write endpoint would invite a second writer — this is a named design exclusion, put it in the plan's must-not list). Routes take/return the existing `extra=forbid` contracts directly so the OpenAPI schema *is* the contract schema. OpenAPI validity is testable: `app.openapi()` output validated in a test (FastAPI generates OpenAPI 3.1).
- **CLI:** argparse noun-verb subparsers; `[project.scripts] ccf = ...` entry point in pyproject; thin httpx client over the HTTP API with `--local` constructing the same factories in-process; **zero privileged paths** — every CLI action goes through the same factories and Control Plane actions as any client (D-IMPL-22); `ccf agent declare` takes an artifact file, never inline definition flags; `ccf skill import <dir>` (D-15) is a thin front-end over the D-IMPL-56 schema. CINV-01 applies to the CLI and HTTP layers: no help-prose that describes any *particular* skill/agent/policy, no default thresholds.
- **B3 hazard applies to the CLI's sync entry point calling async servers:** use one-session-per-call (or a dedicated background loop thread) — never a held-session blocking portal.

### Orchestrator legs (ORCH-02, D-IMPL-60) — verified SDK topology surfaces

All three SDKs probed against the installed pins in the project venv `[VERIFIED: import probe, 2026-07-30]`:

| SDK | Pin | Topology surface for the leg | Suspend/resume mapping |
|-----|-----|------------------------------|------------------------|
| LangGraph | 1.2.9 | `langgraph.graph.StateGraph` + `langgraph.types.interrupt` / `Command(resume=...)` + checkpointer (`langgraph.checkpoint.memory.InMemorySaver`) — all confirmed importable | `interrupt()` at the HITL-gate node maps directly onto CCF suspend; `Command(resume=payload)` onto resume. **Natural fit — but the CCF engine remains authoritative for state + audit; the LangGraph checkpointer holds only LangGraph's own graph position, never Control Plane state** |
| Google ADK | 2.5.0 | `google.adk.agents`: `SequentialAgent`, `ParallelAgent`, `LoopAgent`, `BaseAgent` — confirmed present | Drive CCF workflow steps as ADK sub-agents under a `SequentialAgent`; suspension surfaces as the driver returning control to CCF between ADK invocations. ADK owns intra-step topology only |
| Claude Agent SDK | 0.2.128 | `ClaudeSDKClient`, `ClaudeAgentOptions`, `AgentDefinition`, hook surface (`HookCallback`, `CanUseTool`), `ForkSessionResult` — confirmed present | The thinnest topology surface of the three: no first-class DAG. The credible leg drives CCF workflow nodes via a client session with hooks/tools; expect this to be the highest-effort, highest-uncertainty leg — sequence it with slack (build-order is planner's per D-05) |

- **Leg semantics:** each leg drives a CCF workflow end-to-end through the SDK's topology surface with **identical replay obligations** to the in-SDK engine (CONTEXT phase-boundary text). One factory-parametrized conformance suite (pattern: `tests/conformance/test_harness_adapter.py`); absent-SDK skip must name the SDK and the extra (`pytest.mark.harness` machinery + `CCF_REQUIRE_HARNESSES=1` already exist).
- **D-06 lint:** extend `tools/lints/` with a bidirectional import ban between `ccf_runtime.orchestration.*` and `ccf_runtime.adapters.*`, and add `ccf_runtime.orchestration` as its **own** entry in `HARNESS_ADAPTER_MODULES`' carve-out structure (`tools/lints/harness_imports.py:65`) with the D-24 negative test (harness import in `ccf_runtime.peering` / `ccf_runtime.cdc` still fails). `[VERIFIED: lint + its test file exist]`

### D-IMPL-56 (wave 1, before the slice)

`SkillCatalogEntry` (`catalog.py:173`) gains required `description` + typed `SkillArgumentSchema`; `SKILL_TYPES` (`catalog.py:71`, currently a frozenset over a `SkillType` literal) gains `procedure`; `_BINDING_CONTRACTS` (the real symbol — *not* `BINDING_BY_TYPE`, a D-24-catalogued wrong belief) gains the procedure binding whose instruction travels via `InstructionBinding` on **seam 1** only. One shared derivation module renders all three tool surfaces; delete the three `_tool_description` helpers (`adapters/claude_agent/adapter.py:127`, `adapters/langgraph/adapter.py:198`, `adapters/adk/adapter.py:162` — all verified). Three-way equality test per D-17. Every existing fixture gains a real description in the same plan (D-16) — the fixture inventory is a plan-time enumeration task; expect it to be larger than it looks (conformance + gates + skills + harness test trees all construct catalog entries). The `procedure` token is **ruled, not renameable** (DECISIONS.md:118). `[VERIFIED: codebase + DECISIONS.md]`

### Anti-Patterns to Avoid

- **Generalizing `_build_graph`** from the LangGraph adapter into the engine (A7/D-19) — the D-06 module split exists to make this unrepresentable.
- **A sixth replay dimension or a reconstructed trace block** — verbatim pre-serialized blocks only; a record that re-observes anything describes recording-time state (INV-CH7-80).
- **`None`/absence for "no trace yet"** — positive sentinels (`NO_HARNESS_TRACE` doctrine).
- **`model_dump()` into replay/canonical paths** — canonical serialization normalizes field-by-field and refuses lossy types.
- **Any new writer to L3 or generic HTTP write endpoint** — single-writer; L1 ingestion deliberately absent from the HTTP surface.
- **Overclaiming "by construction"** where enforcement is a lint (D-22).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAPI document | Hand-assembled JSON/YAML from `model_json_schema()` | FastAPI's generated `app.openapi()` | Spec drift; 3.1 validity for free; contracts already Pydantic |
| ASGI serving | Custom server loop | uvicorn (pinned) | Already core; egress precedent |
| Human-approval queue transport | Bespoke queue protocol | MCP Resources/Tools on the existing `mcp==1.28.1` server machinery | D-IMPL-20 ruled MCP primary; egress/artifact servers are the template |
| State-machine property coverage | Hand-enumerated interleavings | `hypothesis.stateful` | Suspend/resume/exception interleavings are the risk surface |
| A durable workflow engine | Retries, timers, distributed durability | `OrchestrationProtocol` → external engine | §8.1: "Reinventing Temporal is out of scope" |
| Audit-write bypass prevention | A convention or docstring | The I.3 admission-token shape | The only shape that has already produced a `DID NOT RAISE` counterfactual in this repo |

## Common Pitfalls

1. **The B3 deadlock.** Held-session `start_blocking_portal()` against an MCP/HTTP server deadlocks (verified in I.3 at 120 s). Sync entry points (CLI, tests) use one-session-per-call or a dedicated background event-loop thread with `stateless_http=True`. Warning sign: a test that hangs rather than fails.
2. **Plan-time symbol drift (D-24).** One wrong belief per plan was I.3's measured rate. Already found this phase's first: D-09's "8 grant call sites" (real: one textual `put` site at `grants.py:515`). Verify every named path/symbol before writing each plan; resolve mismatches by preserving the property and recording a deviation.
3. **Carve-out prefix creep.** Adding `ccf_runtime.orchestration` to the harness-import allowlist without its own negative test recreates the unguarded-prefix-match failure D-24 (I.3) warned about.
4. **Worktree execution against unexercised code (D-26).** `PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python` — a bare run reports green against installed (stale) packages. The post-merge gate on `main` is the load-bearing check.
5. **Two coexisting Control Plane write patterns.** The exact condition that let the grants convention drift through the I.2 gate. The seam closure and the grant retrofit are one plan, not two.
6. **DESIGN.md staleness.** I.3 found `docs/DESIGN.md:745` stale-assigning work; expect and correct similar staleness for orchestration/HITL sections rather than coding to it, recording the correction in-phase.
7. **mypy --strict over both trees.** `files = ["src", "runtime"]`, strict; FastAPI decorators are strict-clean in modern versions, but new-module authors should run mypy early, not at the gate. New untyped-boundary overrides must be one-block-per-module with a stated reason (house style in pyproject).
8. **Gate checklist rows from plan intent (D-25).** Draft each row from a test that fails under the broken implementation; I.2's gate prose had to be rewritten for this.
9. **CINV-01 in front doors.** The CLI/HTTP layers are `/runtime`: no default thresholds, no inline approval rules, no skill prose. Help text describes mechanism, never a particular deployment's vocabulary.

## Runtime State Inventory

Not applicable — greenfield feature phase, no rename/refactor/migration. (Section included to record the explicit skip.)

## State of the Art

No external-ecosystem drift affects this phase: all SDK pins were audited in Phase 6 (2026-07-26) and are unchanged; FastAPI 0.140.0 / httpx 0.28.1 are current-in-venv and slopcheck-clean. The only "current approach" note worth recording: FastAPI has emitted OpenAPI 3.1 since 0.99 — a "valid OpenAPI spec" assertion should validate against 3.1, not 3.0. `[ASSUMED — validate the exact emitted version in the test rather than asserting it in prose]`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastAPI emits OpenAPI 3.1 at 0.140.0 | State of the Art | Test asserts wrong version string; trivially corrected at execution |
| A2 | The Claude Agent SDK leg can drive a CCF workflow through `ClaudeSDKClient` + hooks without a first-class DAG surface | Orchestrator legs | Leg needs a different shape (e.g., tool-driven step advancement); D-05 still requires three real legs — budget slack, and if the SDK genuinely cannot express a driver, that is an escalation to Dave, not a silent narrowing |
| A3 | The grant retrofit touches only `grants.py`'s single `put` site (plus any implementations' signatures) | D-20 closure | More writers exist than grep found (e.g., via helper indirection in `registry.py`/`admission.py`); plan must re-enumerate at execution — D-24 discipline |
| A4 | HITL actions extend replay **dimension 2** (per `record.py`), workflow traces dimensions 4/5 | Workflow engine | If the whitepaper reading differs, that is a fidelity question for the gate; the code's reserved slots are the delivered surface and plans should cite them |

## Open Questions

1. **(ROUTED: blocking `checkpoint:decision` in plan 07-01 Task 2, gating 07-04)** **Absent per-node exception ref (D-13 residual) — decision-ready, recommend routing to Dave as candidate D-IMPL-61.**
   - What we know: §8.1 requires exception paths to be first-class state transitions, not glued-on error handling. D-13 rules per-node refs, artifact-carried.
   - Two defensible readings: **(a) propagate-to-terminal** — a node with no exception ref means an exception transitions the workflow to a defined terminal `failed` state, recorded as an explicit transition in the trace (absence is a defined transition, matching the positive-sentinel doctrine: "no handler" is an asserted claim with defined semantics); **(b) validation error at artifact load** — every node must declare a target, making "unhandled" unrepresentable (matching the required-`description` forcing-function precedent of D-16).
   - Recommendation: reading (a), because (b) forces boilerplate refs onto every node of every simple workflow and quietly makes "let it fail" inexpressible — a policy choice the SDK shouldn't impose — while (a) still satisfies §8.1's first-class requirement (the terminal transition is explicit, audited, and in the trace). But this is artifact-schema semantics on an SDK-defined surface with two defensible readings: per CLAUDE.md §15, record it as a `D-IMPL-NN` with the recommendation and get Dave's ruling **before** the `WorkflowDefinition` schema plan executes. Do not default it.
2. **(RESOLVED in plan 07-06 — split resolved explicitly in the engine module docstring per the Responsibility Map)** **Where exactly the engine/contract split falls across `/src` and `/runtime`** (sync-core contracts vs async-first engine, and where the suspended-state record type lives given the `state.py` "next to the machine" doctrine). Planner-level; flag only because the D-14 async ruling and the `state.py` doctrine pull in slightly different directions and the plan should resolve them explicitly, in writing, in the slice plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Project venv (`/home/parkave/ccf_code/.venv`) | everything | ✓ | py3.12 | — |
| fastapi | EXPR-03 | ✓ (venv, transitive today) | 0.140.0 | Starlette hand-roll (rejected) |
| httpx | EXPR-02 | ✓ | 0.28.1 | stdlib urllib (worse) |
| langgraph | ORCH-02 leg | ✓ | 1.2.9 | visible self-explaining skip |
| google-adk | ORCH-02 leg | ✓ | 2.5.0 | visible self-explaining skip |
| claude-agent-sdk | ORCH-02 leg | ✓ | 0.2.128 | visible self-explaining skip |
| slopcheck | package audit | ✓ | `~/.local/bin/slopcheck` | — |
| mcp / uvicorn / pydantic / pytest / hypothesis / mypy | all waves | ✓ | pinned | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + hypothesis 6.161.5, mypy 2.3.0 --strict |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, markers incl. `conformance`, `crossproc`, `harness`) |
| Quick run command | `PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python -m pytest tests/<area> -x` |
| Full suite command | `CCF_REQUIRE_HARNESSES=1 PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python -m pytest && .venv/bin/python -m mypy && .venv/bin/python -m tools.lints --all` |

Baseline at phase start: 987 passed / 2 skipped (the two CINV-04 deferrals this phase activates). Phase exit: **0 skips** under `CCF_REQUIRE_HARNESSES=1`.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORCH-01 | Suspend/resume + trace-to-replay | unit + hypothesis.stateful | `pytest tests/workflow/ -x` (new tree) | ❌ Wave 0/1 |
| ORCH-01 | D-20 closure counterfactual + adversarial unaudited-write | invariant | `pytest tests/invariants/ -k state` | ❌ closure plan |
| ORCH-02 | Three orchestrator legs, one parametrized suite | conformance | `pytest tests/conformance/test_orchestration.py` (new) | ❌ wave (d) |
| HITL-01 | No unrecorded human action; both CINV-04 checks active | invariant | `pytest tests/invariants/test_replay_by_construction.py` | ✅ (checks flip `not-yet-applicable` → `active`) |
| HITL-01 | ApprovalGate conformance | conformance | `pytest tests/conformance/test_approval_sink.py` | ✅ (reserved slot `:5`, `:62`) |
| EXPR-01 | Experience MCP edge + role separation | crossproc + invariant | `pytest tests/crossproc/ tests/invariants/test_mcp_role_separation.py` | ✅ partial, extend |
| EXPR-02 | CLI noun-verb, `--local`, zero privileged paths | integration | `pytest tests/cli/` (new) | ❌ front-door wave |
| EXPR-03 | OpenAPI validity from `extra=forbid` contracts | unit | `pytest tests/http_api/` (new) | ❌ front-door wave |

### Sampling Rate
- **Per task commit:** area quick run + `mypy` over touched modules.
- **Per wave merge:** full suite on `main` post-merge (the load-bearing check per D-26).
- **Phase gate:** full suite green, 0 skips, `tools.lints --all` exit 0, counterfactual outputs recorded in the gate document (D-10/D-25).

### Wave 0 Gaps
- New test trees `tests/workflow/`, `tests/hitl/`, `tests/cli/`, `tests/http_api/`, orchestration conformance module — created in their respective waves (fixture-first per D-04); no framework install needed.

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (HTTP API, artifact/HITL MCP servers) | Reuse `runtime/ccf_runtime/mcp/auth.py` posture (in-boundary but authenticated, per §7.4); HTTP skeleton must state its v0 auth posture explicitly rather than shipping unauthenticated silently — if v0 is "in-trust-boundary, no auth," say so in the OpenAPI description and gate doc (D-22 honesty discipline) |
| V4 Access Control | yes | Zero privileged CLI/HTTP paths (D-IMPL-22) — every action through the same factories and Control Plane checks; HITL authority only via MCP endpoints, webhooks notify-only (D-IMPL-20) |
| V5 Input Validation | yes | Pydantic `extra=forbid` contracts at every boundary (existing house invariant) |
| V6 Cryptography | yes (approver identity) | `HumanPrincipalBinding` should reuse the existing joserfc/IdentityProvider machinery from I.3 rather than a new identity mechanism (D-IMPL-21 ↔ D-IMPL-15 interaction — verify the ruling text before the HITL identity plan) |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Second writer via HTTP | Tampering | No L1/write endpoint (D-IMPL-23, ruled) |
| Unaudited Control Plane write | Repudiation | D-08 token + audit path; adversarial test (D-10) |
| Approval spoofing / notify-channel authority | Elevation | D-IMPL-20 separation: webhooks can never carry authority; `HumanPrincipalBinding` required on every action |
| Replay-record tampering via reconstruction | Repudiation | Verbatim pre-serialized blocks; canonical serialization; content addressing |

## Sources

### Primary (HIGH confidence)
- Codebase verification (this session, 2026-07-30): `src/ccf/controlplane/state.py`, `src/ccf/agents/definitions.py`, `src/ccf/skills/{grants,catalog}.py`, `src/ccf/replay/record.py`, `runtime/ccf_runtime/{mcp,adapters}/`, `tools/lints/harness_imports.py`, `tests/{invariants,conformance}/`, `pyproject.toml`, `.venv` import probes of langgraph 1.2.9 / google-adk 2.5.0 / claude-agent-sdk 0.2.128.
- `docs/DECISIONS.md` (D-IMPL-56 procedure-token ruling at :118; D-GATE-I.3 at :188), `07-CONTEXT.md`, `.planning/REQUIREMENTS.md`.
- slopcheck (pypi) runs: fastapi, starlette, httpx — all [OK].

### Secondary / Tertiary
- None needed — no external doc lookups were load-bearing; all three orchestrator SDKs were probed directly against installed pins rather than via docs, which is the stronger evidence for planning against exact versions.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — everything pinned/installed/slopchecked; two small additions with stated reasons.
- Architecture: HIGH — reserved extension points verified line-by-line; rulings cover nearly every choice.
- Orchestrator legs: MEDIUM-HIGH — APIs verified importable; the Claude Agent SDK leg's driver shape is the residual uncertainty (Assumption A2).
- Pitfalls: HIGH — sourced from this repo's own recorded gate findings, not generic lore.

**Research date:** 2026-07-30
**Valid until:** phase gate (all inputs are in-repo and pinned; no fast-moving external surface)
