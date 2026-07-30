# Phase 7: Phase I.4 — Orchestration, HITL, Experience - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 7-phase-i-4-orchestration-hitl-experience
**Areas discussed:** OrchestrationProtocol proof, Slice + wave order, State-seam audit closure, Workflow artifact shape, D-IMPL-56 implementation

**Areas offered but not selected:** Front-door build order, HITL transport v0 scope, Replay dimension-5 extension

---

## OrchestrationProtocol proof

Raised by Dave unprompted, as free text on the area-selection question:
*"not only LangGraph but Anthropic Agent SDC and Google SDK"*. This widened the
area from "how do we prove criterion 3" to "against how many external SDKs".

### Q1 — What must each of the three SDKs demonstrate?

| Option | Description | Selected |
|--------|-------------|----------|
| Three real driver integrations | Each of ADK, Claude Agent SDK, LangGraph gets a real `OrchestrationProtocol` integration in `/runtime` driving a CCF workflow end-to-end through its own topology surface; all three in one parametrized conformance suite | ✓ |
| One deep + two against the suite | Build one end-to-end to discover what the Protocol needs, harden Protocol + suite against it, bring the other two up against the fixed suite (I.3's D-07 pattern) | |
| Three legs + a neutral driver | All three real integrations plus a no-SDK external driver, so the Protocol is proven to need nothing harness-shaped | |

**User's choice:** Three real driver integrations
**Notes:** The staged option was offered explicitly and declined. Build order
*within* the wave remains planner-level per the `D-GATE-F` precedent (staging is
sequencing, not a revision of a ruling) — recorded in CONTEXT.md D-05 so it
cannot be read as reducing the leg count. The neutral-driver option was not
taken, so "without touching SDK internals" is proven against three vendor
surfaces rather than against an absence of one.

### Q2 — How is the orchestrator-vs-harness seam distinction enforced?

| Option | Description | Selected |
|--------|-------------|----------|
| Structural: separate module trees | `runtime/ccf_runtime/orchestration/<sdk>/`, never inside `adapters/<sdk>/`, with a lint or import test pinning no cross-import either way | ✓ |
| Structural + a negative test per SDK | The module split plus a per-SDK test asserting the orchestration leg obtains no write handle and no adapter-internal topology (I.3's D-10 "declared and proven inert" pattern) | |
| You decide | Planner's call within A7's prerequisite | |

**User's choice:** Structural: separate module trees
**Notes:** The heavier per-SDK negative test was offered and not taken. The
consequence recorded in CONTEXT.md D-06: the CINV-02 harness-import carve-out
(`HARNESS_ADAPTER_MODULES`, currently `ccf_runtime.adapters` only) needs a
considered entry for the new tree, and I.3's D-24 negative-test discipline
applies — a harness import in `ccf_runtime.peering` or `.cdc` must still fail.

### Q3 — How is the widening of D-IMPL-17 recorded?

| Option | Description | Selected |
|--------|-------------|----------|
| New D-IMPL entry, your ruling | New numbered entry as Dave's ruling, consequences enumerated D-IMPL-24-style; D-IMPL-17 untouched, cross-referenced | ✓ |
| Amend D-IMPL-17 in place | Dated amendment line on the existing entry | |

**User's choice:** New D-IMPL entry, your ruling → **`D-IMPL-60`** (59 is the current highest)
**Notes:** Consistent with D-IMPL-55/57/58/59, all of which took new numbers
rather than editing approved `D-GATE-D` text.

---

## Slice + wave order

### Q1 — What is the vertical slice?

| Option | Description | Selected |
|--------|-------------|----------|
| Suspend/resume on one gate | Two-step workflow suspends on one real ApprovalGate and resumes on approval; human action + step sequence both in replay; flips both CINV-04 skips | ✓ |
| Straight-line workflow, no gate | Two-step workflow (skill node + agent node) to terminal with its trace in replay; no HITL yet | |
| Gate reachable through a front door | The suspend/resume slice driven through `ccf workflow` in `--local` mode | |

**User's choice:** Suspend/resume on one gate
**Notes:** The no-gate option was framed as deferring the hard part (suspend/resume)
into wave 2; the front-door option as pulling CLI scaffolding in before the HTTP
layer it is supposed to be a thin client over exists. Neither taken.

### Q2 — How do the waves widen?

| Option | Description | Selected |
|--------|-------------|----------|
| engine → HITL → orch → doors → gate | Mirrors I.3's transport→trust→harness shape; external SDKs land after every fabric-side seam is proven | |
| engine → HITL → doors → orch → gate | Front doors before the orchestrator legs; criterion 4 banked early, and the orchestrator legs get a real HTTP surface to drive | ✓ |
| You decide | Planner's call within the stated prerequisites | |

**User's choice:** engine → HITL → doors → orch → gate
**Notes:** A deliberate departure from I.3's largest-unknown-last shape. The
tradeoff stated at the time and accepted: front doors get built over an engine
that has not yet been driven externally.

### Q3 — Split the phase?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as one phase | ORCH+HITL+EXPR ship and gate together as `D-GATE-I.4`, matching the ROADMAP as written | ✓ |
| Split into I.4a / I.4b | Orchestration+HITL gate separately from the Experience Layer, two `D-GATE` entries | |
| One phase, two gate checkpoints | One phase and one gate, plus a mid-phase review after the HITL wave | |

**User's choice:** Keep as one phase
**Notes:** Both the split and the mid-phase checkpoint were offered and declined,
with the likely-largest-plan-count-yet consequence stated up front (I.3 was 25).

---

## State-seam audit closure (the D-20 prerequisite)

### Q1 — How is the `ControlPlaneStateStore` audit gap closed?

| Option | Description | Selected |
|--------|-------------|----------|
| Token the store requires | `put()` uncallable without an audit token only the audit log can mint; unaudited write becomes a type error; retrofits 8 grant call sites | |
| Audit-bearing write path | A wrapper performing audit append + state put as one operation, as the only supported surface; raw `put()` still exists, so the claim is "lint-enforced in shipped surfaces" | |
| Both | Wrapper as the ergonomic surface, token underneath; the only option where the D-21-compliant claim can say "by construction" | ✓ |

**User's choice:** Both
**Notes:** Chosen with the churn cost stated. This is the first place in the
project where "by construction" will be fully load-bearing for the state seam;
per D-21, the docstring and gate-document wording must track what is actually
earned.

### Q2 — Retrofit scope for the 8 existing grant call sites?

| Option | Description | Selected |
|--------|-------------|----------|
| Retrofit all sites in the closure plan | Exactly one way to write Control Plane state exists at every point in time | ✓ |
| New sites only, grants follow later | Smaller closure plan; two write patterns coexist | |
| You decide | Planner's call, constrained by D-21 | |

**User's choice:** Retrofit all sites in the closure plan
**Notes:** The rejected option was framed as recreating the exact condition that
let the convention drift unnoticed through the I.2 gate.

### Q3 — What proves the closure is load-bearing?

| Option | Description | Selected |
|--------|-------------|----------|
| Observed counterfactual, required | Revert → red, output recorded in the gate document; an explicit `must_have` rather than a convention | |
| Plus an adversarial test | The counterfactual plus a test actively attempting an unaudited write and asserting it cannot succeed (the 06-20 pattern that produced `DID NOT RAISE` when neutered) | ✓ |

**User's choice:** Plus an adversarial test
**Notes:** Rationale offered and accepted: ADV-02/D-20 was found by inspection,
not by test, so the closure needs a proof that covers "the closure works but a
bypass still exists."

---

## Workflow artifact shape

### Q1 — What does the Workflow primitive interpret?

| Option | Description | Selected |
|--------|-------------|----------|
| `TaskDefinition`, extended | The primitive interprets the existing artifact; `hitl-gate` steps gain the approval-policy ref I.2 withheld. One artifact type; requires a schema change to gated I.2 code | |
| Distinct `WorkflowDefinition` | New artifact beside `TaskDefinition`, leaving I.2's contract byte-identical; two overlapping types, and `TaskDefinition` then interprets nothing | |
| `TaskDefinition` as the step list, `WorkflowDefinition` wrapping it | `TaskDefinition` keeps the ordered steps; `WorkflowDefinition` adds only state-machine needs (transitions, terminal conditions, exception routing) | ✓ |

**User's choice:** `TaskDefinition` as the step list, `WorkflowDefinition` wrapping it
**Notes:** Consequence surfaced immediately after the answer and recorded as
CONTEXT.md D-12: the approval-policy binding can live on the wrapper, so I.2's
`_ref_agrees_with_kind` validator (`definitions.py:249`) stays byte-identical.
Flagged as the *intended reading* the planner must confirm against actual gate
semantics — not an assumption to build on silently.

### Q2 — How are §8.1's first-class exception paths declared?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-node exception ref | Each node declares its own exception-path target in the artifact; explicit and locally readable; verbose, and the absent case needs a defined meaning | ✓ |
| Workflow-level routing table | One declared routing block per workflow mapping conditions (D_c breach, explicit escalation) to targets, per §8.2's ExceptionEscalation framing | |
| You decide | Planner's call, constrained by CINV-01 | |

**User's choice:** Per-node exception ref
**Notes:** The "absent declaration needs a defined meaning" caveat was stated in
the option description and is carried into CONTEXT.md D-13 as an explicit
residual for research — propagate-to-terminal vs. validation-error-at-load.

### Q3 — Sync, async, or both?

| Option | Description | Selected |
|--------|-------------|----------|
| Async-first, per D-IMPL-04 | Engine on the runtime side of the async-first-runtime/sync-core line; consistent with HTTP/MCP front doors and all three orchestrators | ✓ |
| Sync engine, async at the front doors only | Simpler to test; suspend/resume is durable-state rather than awaited — but every orchestrator integration then needs a bridge, and I.3's B3 showed those deadlock when built the intuitive way | |
| You decide | Planner's call within D-IMPL-04 | |

**User's choice:** Async-first, per D-IMPL-04
**Notes:** The I.3 B3 hazard (held-session `start_blocking_portal()` deadlocks at
a 120 s timeout; the working shape is a background event-loop thread plus one
session per call against `stateless_http=True`) is carried into CONTEXT.md D-14
for any bridging that remains.

---

## D-IMPL-56 implementation

### Q1 — Where in the wave order?

| Option | Description | Selected |
|--------|-------------|----------|
| Wave 1 prerequisite | Schema + shared derivation + `procedure` type before the slice; `ccf skill import` follows in the CLI wave as a thin front-end | ✓ |
| Whole thing in the CLI wave | Schema and importer ship together; the slice's agent-nodes bind against the old schema and get migrated twice | |
| Wave 1 schema, derivation with the adapters | Schema early, derivation deferred to the orchestrator wave; risks four more waves of per-adapter helpers with no test that would catch a difference | |

**User's choice:** Wave 1 prerequisite
**Notes:** Driven by the I.3 gate's stated consequence — a divergence in derived
tool prose silently breaks the D-18 harness equivalence and no current test
would catch it, because all three adapters presently follow 06-12's precedent.

### Q2 — `description` becomes required; how is migration handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Required, fixtures updated in the same plan | No optional phase, no default; `extra=forbid` + required means an entry without one cannot be constructed | ✓ |
| Required with a positive sentinel | A `NO_DESCRIPTION`-style constant following the `NO_HARNESS_TRACE`/`NO_GRANTS` doctrine | |
| You decide | Planner's call, constrained by CINV-01 | |

**User's choice:** Required, fixtures updated in the same plan
**Notes:** The sentinel option was offered as the doctrine-consistent choice and
declined as a weaker forcing function. The ruling's premise — *what a skill is
for is the deployment's statement* — is enforced rather than requested. The
CINV-01 constraint stands regardless: no per-skill prose in `/src` or `/runtime`.

### Q3 — What proves the three adapters actually share one derivation?

| Option | Description | Selected |
|--------|-------------|----------|
| Three-way equality assertion | One test asserting all three adapters' rendered tool surfaces agree on description and argument schema for the same catalog entry; fails if any adapter re-derives | ✓ |
| Equality plus a counterfactual | The above plus reverting one adapter to its own helper and recording that the test goes red | |

**User's choice:** Three-way equality assertion
**Notes:** The added counterfactual was offered — and is Dave's standing standard
elsewhere in this project — and not taken here. Recorded in CONTEXT.md D-17 with
the reason it is still adequate: the equality assertion has an intrinsic failure
mode (it goes red if any adapter re-derives), unlike an inspection-only claim.

---

## Claude's Discretion

- **Front-door build order and HTTP framework choice** — not selected for
  discussion; planner-level under D-IMPL-22/23. Noted: `uvicorn` is already a
  core dependency, FastAPI is not.
- **HITL transport v0 scope** — not selected; planner-level under D-IMPL-20.
  Two sub-questions: whether the webhook notify-only leg ships in v0, and
  whether the real `ApprovalGate` joins `test_approval_sink.py`'s already-reserved
  parametrization slot or gets its own suite.
- **Replay dimension-5 extension shape** — not selected; follows the thrice-used
  D-IMPL-55 extension pattern (doctrine line, positive sentinel, verbatim
  pre-serialized block).
- **Orchestrator conformance skip mechanism when an SDK is absent** — under the
  I.3 constraint that a skipped leg is visible and self-explaining, naming the
  SDK and the extra that enables it.
- **Module tree details** below the D-06 boundary.

## Deferred Ideas

- Absent per-node exception ref semantics (a real open question for research,
  not a deferral).
- Advisory **A3** — the Claude adapter's hand-built `ResultMessage` seam-4 leg;
  explicitly Phase 8's obligation, owned by whoever writes
  `examples/03-harness-portability`.
- Loop-level harness portability — Phase 8, `examples/03`.
- The polished `/examples` suite including `examples/05-workflow-hitl` — Phase 8.
- A heavyweight/durable workflow engine — permanently out of scope (§8.1, §13);
  reachable only via `OrchestrationProtocol`.
- Human task-management inbox or UI — out of scope (§8.2, §13).
- Mobile SDK, chat adapter, web UI — out of scope for v0 (§8.3).
- Supervision Quality — ruled out of v0 scope (D-IMPL-48).
