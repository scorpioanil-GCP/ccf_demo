# Phase 7: Phase I.4 — Orchestration, HITL, Experience - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Multi-agent workflows with human gates execute, suspend, and resume — with
every human action and every execution trace replay-recorded by construction —
and the fabric becomes reachable through the three v0 front doors. Four
sub-domains:

1. **Orchestration (ORCH-01, ORCH-02)** — the in-SDK Workflow primitive per
   CLAUDE.md §8.1 and D-IMPL-17: skill / agent / HITL-gate nodes,
   state-machine semantics with explicit transitions and terminal conditions,
   first-class exception paths, suspend/resume on Control Plane state
   (D-IMPL-18), harness-neutral agent nodes resolved through the I.3 adapter
   bindings, and workflow definitions as Control Plane artifacts through the
   Task Factory. Plus `OrchestrationProtocol` as the seam to external
   orchestrators, with **identical replay obligations**.
2. **HITL (HITL-01)** — all four primitives (ApprovalGate,
   ExceptionEscalation, OverrideBoundary, ReviewQueue) per §8.2, on the
   `HITLTransportProtocol` typed queue (D-IMPL-20) with `HumanPrincipalBinding`
   identity (D-IMPL-21), writing to Decision Replay with **no path through the
   HITL surface producing an unrecorded human action**.
3. **Experience Layer (EXPR-01, EXPR-02, EXPR-03)** — MCP server egress
   exposing Context Products *and agents* (this includes the
   **Experience-surface MCP edge that D-GATE-I.3 explicitly deferred to
   Phase 7** — a named deferral, not a coverage claim); the `ccf` noun-verb CLI
   (D-IMPL-22) over the HTTP API with a `--local` direct-library mode; and the
   HTTP API skeleton with a valid OpenAPI spec (D-IMPL-23).
4. **Inherited, by ruling** — **D-IMPL-56 implementation**: `SkillCatalogEntry`
   gains a required `description` and a typed `SkillArgumentSchema`, one shared
   derivation renders all three harness tool surfaces (deleting the adapters'
   per-adapter `_tool_description` helpers), and a fifth `procedure` skill type
   carries Anthropic Agent Skills' SKILL.md through **seam 1** via
   `InstructionBinding` — never seam 2. Ruled 2026-07-27; implementation is
   this phase's scope by that ruling.

Success criteria per `.planning/ROADMAP.md` Phase 7 (four criteria). Branch
`phase-i4`; model mandate Opus 5 (fallback Opus 4.8) high effort; ends with
`/gsd-review` → triage → Dave approval → `D-GATE-I.4`.

**Also this phase, and it is a criterion not a nicety:** the two remaining
CINV-04 deferral skips — `hitl-action-capture` and `workflow-trace-capture` —
are activated. Their skip reasons each name Phase I.4 as the unblocking phase.
The suite's skip count goes to **zero**.

**Not in this phase:** the polished `/examples` suite including
`examples/05-workflow-hitl` and `examples/03-harness-portability` (Phase 8 /
I.5); advisory **A3** (the Claude adapter's hand-built `ResultMessage` seam-4
leg) which is explicitly Phase 8's obligation and is **not** discharged here;
any heavyweight/durable workflow engine (§8.1 — reinventing Temporal is out of
scope, reachable via `OrchestrationProtocol`); any human task-management inbox
or UI (§8.2, §13); mobile/chat/web front ends (§8.3).

</domain>

<decisions>
## Implementation Decisions

### Build sequencing & slice

- **D-01:** **Vertical slice first**, continuing the I.1/I.2/I.3 pattern. The
  slice is **a two-step workflow that suspends on one real ApprovalGate and
  resumes on approval**, with the human action and the step sequence both
  landing in the replay record. Chosen as the thinnest path that exercises
  everything structurally novel in this phase at once: the engine, the
  Control Plane state seam (and therefore the D-20 closure), a real HITL
  primitive replacing I.2's scripted test double, and **both** CINV-04 skips.
  A straight-line no-gate workflow was rejected deliberately — it would defer
  suspend/resume, which is the actual hard part, into wave 2.
- **D-02:** Waves widen **engine → HITL → front doors → orchestrators → gate**:
  (a) Workflow engine + the D-20 state-seam closure + D-IMPL-56 (see D-14);
  (b) the remaining three HITL primitives (ExceptionEscalation,
  OverrideBoundary, ReviewQueue) with their transports;
  (c) the three front doors (MCP egress incl. the Experience edge, HTTP+OpenAPI,
  CLI);
  (d) the three `OrchestrationProtocol` driver integrations;
  (e) gate wave.
  **Front doors deliberately precede the orchestrator legs** (Dave's ruling
  over the I.3-mirroring alternative): criterion 4 is banked before the phase's
  largest external unknown opens, and the orchestrator legs get a real HTTP
  surface to drive if that proves the cleanest integration path.
- **D-03:** **One phase, one gate.** ORCH + HITL + EXPR ship and gate together
  as `D-GATE-I.4`, matching the ROADMAP as written. Splitting into I.4a/I.4b
  and a mid-phase review checkpoint were both offered and declined. Planning
  should expect this to be the largest plan count yet (I.3 was 25).
- **D-04:** **Test fixtures in I.4, polished examples in I.5** — unchanged from
  I.3 D-06. Every wave builds its proof as a test fixture; `examples/05` and
  `examples/06` land in Phase 8.

### OrchestrationProtocol — all three SDKs, not only LangGraph

This is a **widening of D-IMPL-17**, which named only LangGraph in its two-seam
disambiguation. Dave raised it unprompted.

- **D-05:** **Three real driver integrations.** Google ADK, the Claude Agent
  SDK, and LangGraph each get a real `OrchestrationProtocol` integration in
  `/runtime` that drives a CCF workflow end-to-end through **that SDK's own
  topology surface**, all three exercised by one factory-parametrized
  conformance suite. The "one deep, then two against the suite" staging (I.3's
  D-07 pattern) was offered and **declined** — all three are real legs.
  Build *order within the wave* remains planner-level per the `D-GATE-F`
  precedent (intra-phase staging is sequencing, not a revision of a ruling);
  that does not reduce the leg count below three.
- **D-06:** **Structural enforcement of the two-seam distinction: separate
  module trees.** Orchestrator integrations live under
  `runtime/ccf_runtime/orchestration/<sdk>/` and **never** inside
  `runtime/ccf_runtime/adapters/<sdk>/`, with a lint or import test pinning
  that no orchestration module imports an adapter module and vice versa. This
  makes advisory **A7**'s failure mode — promoting the LangGraph adapter's
  private `_build_graph` topology into the SDK's engine — structurally
  unrepresentable rather than merely documented. It also means the CINV-02
  harness-import carve-out must be re-examined: `HARNESS_ADAPTER_MODULES`
  currently admits `ccf_runtime.adapters` only (I.3 D-24), so the new tree
  needs its own considered carve-out entry — **and D-24's negative test
  discipline applies**: a harness import in `ccf_runtime.peering` or
  `ccf_runtime.cdc` must still fail, or the carve-out is an unguarded prefix
  match.
- **D-07:** **Recorded as a new numbered entry, `D-IMPL-60`** (next free
  number; 59 is the current highest), as **Dave's own ruling**, with accepted
  consequences enumerated the way D-IMPL-24 enumerated its three adapter / three
  CI / three example legs. `D-IMPL-17` itself is **untouched** and is
  cross-referenced. Amending an approved `D-GATE-D` ruling in place was
  offered and declined — consistent with D-IMPL-55/57/58/59, all of which took
  new numbers rather than editing prior text.

### The D-20 state-seam closure (a prerequisite, not a follow-up)

`docs/PHASE_I3_GATE.md` §5 states this in as many words: *"Closing this … is a
prerequisite for the first I.4 plan that touches the seam, not a follow-up."*
`ControlPlaneStateStore.put` neither audits nor requires a token; the pairing in
`grants.py` is paired-call **convention**, and suspend/resume multiplies the
call sites (INV-CH7-71).

- **D-08:** **Both mechanisms.** An audit-bearing write path as the ergonomic
  surface (following the I.2 precedent — transitions audit through the one
  existing `AuditLog`, no parallel log type), **plus** a token the raw seam
  requires so `put()` cannot be reached without one. This is the only option
  under which the D-21-compliant claim can honestly read **"by construction"**
  rather than "lint-enforced in shipped surfaces" — and per D-21, the wording
  in docstrings and the gate document must track whichever it actually earns.
- **D-09:** **All 8 existing grant call sites are retrofitted in the same plan
  that closes the seam.** Exactly one way to write Control Plane state exists at
  every point in time. Migrating grants later was offered and declined: two
  coexisting write patterns is precisely the condition that let the convention
  drift unnoticed through the I.2 gate.
- **D-10:** **Counterfactual *plus* adversarial proof.** A test that goes red
  when the closure is reverted (output recorded in the gate document — the
  standard every I.3 closure was held to), **and** a test that actively
  attempts an unaudited write and asserts it cannot succeed. The 06-20
  precedent is the relevant one: neutering the adversarial `capture_effect`
  produced `DID NOT RAISE`, which is what an inspection-only finding cannot
  give you. Make both explicit `must_haves` on the closure plan.

### Workflow artifact shape and execution model

- **D-11:** **`TaskDefinition` keeps the step list; a new `WorkflowDefinition`
  wraps it.** `TaskDefinition`/`TaskStep` (`src/ccf/agents/definitions.py`)
  continue to declare the ordered steps they already declare — kinds
  `skill` / `agent` / `hitl-gate`, refs pinned by versioned URI — and
  `WorkflowDefinition` adds **only** what a state machine needs on top:
  explicit transitions, terminal conditions, and exception routing (§8.1).
  Neither artifact duplicates the other. Two alternatives were rejected:
  extending `TaskDefinition` in place (reopens a gated I.2 contract), and a
  standalone `WorkflowDefinition` beside it (leaves `TaskDefinition`
  interpreting nothing, and forces users to choose between overlapping types).
- **D-12 (consequence of D-11, and the intended reading):** the approval-policy
  binding for a gate lives on the **wrapper**, so I.2's
  `_ref_agrees_with_kind` validator — `hitl-gate` steps must not carry a ref,
  because *"binding an approval policy before anything can execute would be a
  claim the artifact cannot yet honor"* (`definitions.py:249`) — stays
  **byte-identical**. Planning must confirm this holds against the actual gate
  semantics rather than assume it; if a gate genuinely needs a step-level ref,
  that is a schema change to gated I.2 code and gets recorded as such, not
  slipped in.
- **D-13:** **Per-node exception refs**, not a workflow-level routing table.
  Each node declares its own exception-path target (typically a HITL gate) in
  the artifact — explicit and locally readable. Thresholds and routing values
  are artifact content, never code constants (CINV-01 / No-Hardcoding §6.4).
  **Residual for research (flagged, not decided):** what a node with **no**
  exception ref means — propagate to workflow terminal, or a validation error
  at artifact load. §8.1 requires exception paths be first-class state
  transitions rather than error handling glued on, so the absent case needs a
  defined meaning either way.
- **D-14:** **Async-first engine, per the existing D-IMPL-04 ruling**
  ("`ccf` + `ccf-runtime` packages, async-first runtime / sync core"). The
  engine sits on the runtime side of that line, consistent with the HTTP and
  MCP front doors and all three external orchestrators. Note the I.3 **B3**
  finding as a live hazard for any sync/async bridging that remains: the
  intuitive held-session `start_blocking_portal()` bridge **deadlocks**
  (verified at a 120 s timeout); the working shape was a dedicated background
  event-loop thread plus one session per call against `stateless_http=True`.

### D-IMPL-56 implementation

- **D-15:** **Wave-1 prerequisite.** The schema change (required `description`
  + typed `SkillArgumentSchema`), the one shared three-harness derivation, and
  the fifth `procedure` skill type all land **before the slice**, because
  workflow agent-nodes bind skills and the I.3 gate is explicit about the
  consequence of delay: *"every future adapter re-derives tool description and
  argument schema in `/runtime`, and the first one to derive them differently
  silently breaks the D-18 harness equivalence"*. The `ccf skill import <dir>`
  importer follows in the CLI wave as a thin front-end over the
  already-shipped schema.
- **D-16:** **`description` is required, and every existing fixture gains a
  real one in the same plan.** No optional phase, no default, no sentinel.
  With Pydantic `extra=forbid` plus a required field, an entry without a
  description cannot be constructed — which enforces rather than requests the
  ruling's premise that *what a skill is for is the deployment's statement*.
  A `NO_DESCRIPTION`-style positive sentinel (the `NO_HARNESS_TRACE` /
  `NO_GRANTS` doctrine) was offered and declined as a weaker forcing function.
  Constraint that does not move: no prose describing any particular skill may
  appear in `/src` or `/runtime` (CINV-01) — descriptions are artifact content.
- **D-17:** **Three-way tool-surface equality assertion.** One test asserts all
  three adapters' rendered tool surfaces agree on description and argument
  schema for the same catalog entry — making the D-18 portability equivalence
  explicit and giving it an intrinsic failure mode (it goes red if any adapter
  re-derives). The added revert-one-adapter counterfactual was offered and not
  taken; the equality assertion is itself falsifiable, which is the property
  that matters.
- **D-18:** Per the ruling, **SKILL.md is an authoring format, not a canonical
  artifact.** Import is one-way; frontmatter `name`/`description` map to the
  entry's fields, the body becomes a registered `ccf.prompt-artifact`, and
  `references/` become further pinned artifacts. `allowed-tools` is **not**
  auto-mapped onto `SkillRequirements` — a harness permission token is not a
  policy-regime identifier, and inferring one would be the SDK inventing the
  deployment's policy vocabulary (D-IMPL-29).

### Constraints inherited from `docs/PHASE_I3_GATE.md` §5 — prerequisites, not notes

- **D-19 (A7):** the Workflow primitive is built against **D-IMPL-17's
  boundary**, *not* by generalizing the LangGraph adapter's `_build_graph`. An
  adapter's private topology is harness-internal (§13), and promoting it would
  make the SDK ship the loop it commits to never shipping (§7.3). D-06 above is
  the structural expression of this.
- **D-20 (D-22 carried):** `tests/invariants/test_consumption_discipline.py`
  remains a **direct-import** check with no transitive closure. Any widening of
  `ALLOWED_CCF_PREFIXES` needs a transitive-closure argument, as I.2's
  `ccf.controlplane.resolution` widening received — **never a precedent
  argument**. Do not upgrade `src/ccf/harness/protocol.py`'s wording; the claim
  it has earned is "`Agent`'s own imports reach no fabric layer".
- **D-21 (D-IMPL-45):** `TraceCorrelationHook` attaches to the **existing**
  `harness_trace` slot on replay dimension 3 (delivered in I.3 as D-IMPL-55).
  The slot exists and is isolated from the governed fields; do not mint a new
  location.
- **D-22 (D-21 carried):** **scope every invariant claim to its actual
  enforcement.** Write "lint-enforced in shipped surfaces" or "audited by the
  current implementation" rather than "no path" / "by construction" unless the
  state is genuinely unrepresentable. This bears hardest on HITL-01's
  audit-by-construction criterion, which is exactly the kind of claim that
  degrades into convention.
- **D-23 (D-23 carried):** **any set-identity, admission decision, or replay
  claim computed over shared Control Plane state carries a multi-principal case
  in its plan's `must_haves`** — two tenants, two agents, two approvers. CR-01
  was a *planning* defect: no two-agent test was ever required, so none existed.
  Directly relevant to workflow state keyed per tenant and to
  `HumanPrincipalBinding`.
- **D-24 (process, from the D-GATE-I.3 planning-quality finding):** **five of
  six I.3 gap-closure plans carried a path, symbol, or criterion defect**,
  clustered into repeated wrong beliefs (a nonexistent `tests/products`; the
  same impossible `controlplane/artifacts.py` placement in three plans, against
  a real `products.contract → controlplane.registry → controlplane.artifacts`
  cycle; a nonexistent `BINDING_BY_TYPE` symbol; two `grep -c … == 0` criteria
  unsatisfiable against their own mandates). Every one was resolved by
  preserving the property and recording a deviation, never by bending code to
  satisfy a counter. **Tell executors to expect one per plan**, and verify
  every path and symbol a plan names before the plan is written.
- **D-25 (process, from Cursor via I.3):** draft gate-checklist rows from
  **tests that fail under the broken implementation**, not from plan intent.
  I.2's initial gate prose overclaimed and had to be rewritten.
- **D-26 (execution environment, from the I.3 handoff):** worktree agents fork
  off `main`, not the phase branch — keep the `EXPECTED_BASE` merge-base guard
  (it fired 7/7 times in I.3; without the `git reset --hard`, a merge silently
  reverts the phase). There is **no `.venv` in agent worktrees** and both `ccf`
  and `ccf_runtime` are editable-installed against the main repo, so executors
  must run `PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python` —
  `src` alone is not enough, and a bare run reports green against code never
  exercised. **The post-merge gate on `main` is the load-bearing check, not the
  executor's self-check.** The merge guard blocks deletions outside
  `.planning/` cumulatively against the `pre-peering` tag.

### Claude's Discretion

- **Front-door build order and HTTP framework choice.** Not selected for
  discussion; planner-level under D-IMPL-22 (thin client over HTTP with
  `--local`) and D-IMPL-23 (minimal skeleton mirroring the CLI noun set, no L1
  endpoint). Note `uvicorn==0.51.0` is already a core dependency while FastAPI
  is not — an added core dependency needs a stated reason.
- **HITL transport v0 scope.** Not selected; planner-level under D-IMPL-20
  (MCP endpoints primary, webhooks notify-only). Two sub-questions the planner
  owns: whether the webhook leg ships in v0 or defers, and whether the real
  `ApprovalGate` joins the parametrization in
  `tests/conformance/test_approval_sink.py` — whose docstring already reserves
  the slot ("I.4's `ApprovalGate` adds its own param here") — or gets its own
  suite. The reserved slot is the strong hint.
- **Replay dimension-5 extension shape.** Not selected; follows the
  established, thrice-used extension pattern documented at
  `src/ccf/replay/__init__.py:12` and specified in D-IMPL-55: a doctrine line
  naming which phase extends which dimension, a new field defaulted to a
  **positive sentinel** rather than `None` or absence, and an optional
  pre-serialized block recorded **verbatim** on `build_replay_record` (never
  reconstructed inside the builder — a record that re-observed anything would
  describe recording-time state rather than decision-time state). The five
  dimensions stay inviolate (INV-CH7-80); a sixth block is a fidelity defect,
  not an option.
- **How an orchestrator conformance leg behaves when an SDK is absent** — under
  one constraint carried from I.3: a skipped leg must be **visible and
  self-explaining**, naming which SDK and which extra enables it. CI installs
  `[dev]`, so all three legs run there regardless. Note the harness extras
  (`adk`, `claude-agent`, `langgraph`, aggregate `harnesses`) already exist from
  I.3 D-08 and its one-documented-command requirement still applies.
- Module tree details below the D-06 boundary.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Governing specification
- `CLAUDE.md` §8.1 — Orchestration Layer: the Workflow primitive's committed
  properties (agent nodes, state-machine semantics, replay integration,
  exception paths, harness-neutral nodes) **and** the explicit boundary —
  "Reinventing Temporal is out of scope."
- `CLAUDE.md` §8.2 — HITL: the four primitives, the audit-by-construction
  commitment ("no path through the HITL surface that produces an unrecorded
  human action"), and what the SDK does *not* provide (no workflow inbox).
- `CLAUDE.md` §8.3 — Experience Layer: the three v0 front doors and the
  deliberate exclusions (no mobile SDK, chat adapter, or web UI).
- `CLAUDE.md` §6.4 — the No-Hardcoding Rule: no task graph, routing table,
  threshold, approval rule, or skill grant as a code constant. Directly binds
  D-11/D-13/D-16.
- `CLAUDE.md` §10 — L1–L6 layering, the two planes, and the single-writer
  invariant (no path this phase adds may acquire a write handle to L3).
- `CLAUDE.md` §11 — working principles: Protocols over inheritance, reference
  impls alongside Protocols, typed contracts at every boundary, "Decision
  Replay is enforced at write time, not retrofitted."
- `CLAUDE.md` §13 — scope and non-scope, including harness-internal behavior
  (the basis for D-19/A7).
- `CLAUDE.md` §15 — what to do when unclear: a whitepaper-silent or
  document-ambiguous question is a `D-IMPL-NN` entry and a **stop**, never a
  chosen default.
- `docs/CCF_Whitepaper_1-2.md` §7.10.1 — the five-dimension Decision Replay
  record (INV-CH7-80, INV-CH7-83, INV-CH7-88): dimensions 4 and 5 are what
  workflow traces and HITL actions extend; the five dimensions themselves are
  inviolate.
- `docs/CCF_Whitepaper_1-2.md` §7.8.2 — the Control Plane as the audit plane
  (INV-CH7-71 is the invariant behind the D-08 state-seam closure).

### Rulings that constrain this phase
- `docs/DECISIONS.md` **D-IMPL-17** — in-SDK Workflow primitive +
  `OrchestrationProtocol`; the LangGraph two-seam disambiguation. **Widened by
  D-05/D-07 above via a new entry, `D-IMPL-60`; D-IMPL-17's own text is not
  edited.**
- `docs/DECISIONS.md` **D-IMPL-18** — suspended workflow state at the Control
  Plane boundary as typed versioned records on the native store; every
  transition appends to the execution trace; the trace writes through to the
  ArtifactStore at each suspend and at terminal. No separate workflow-store
  Protocol.
- `docs/DECISIONS.md` **D-IMPL-20** — `HITLTransportProtocol` typed queue; MCP
  endpoints primary, webhooks notify-only (notification and authority
  separated so audit-by-construction cannot be bypassed).
- `docs/DECISIONS.md` **D-IMPL-21** — `HumanPrincipalBinding`: approver
  identity, authentication context, action time, and the content hash of the
  Context Product the approver saw. No HITL action lands without a binding.
- `docs/DECISIONS.md` **D-IMPL-22** — `ccf <noun> <verb>`; thin client over
  HTTP with `--local`; `ccf agent declare` takes an artifact file, never inline
  definition flags; zero privileged CLI paths.
- `docs/DECISIONS.md` **D-IMPL-23** — the minimal v0 HTTP surface mirroring the
  CLI noun set; OpenAPI generated from the existing `extra=forbid` contracts;
  **L1 ingestion deliberately absent** (a generic write endpoint would invite a
  second writer).
- `docs/DECISIONS.md` **D-IMPL-27** — substrate split by mutability: suspended
  workflow state is mutable-until-terminal and therefore native, not
  ArtifactStore; the terminal trace lands in the ArtifactStore.
- `docs/DECISIONS.md` **D-IMPL-45** — `TraceCorrelationHook` +
  `ExternalTraceProviderProtocol`; attaches at the replay-hooks seam this
  phase, into the slot I.3 delivered.
- `docs/DECISIONS.md` **D-IMPL-55** — the `HarnessTrace` sub-structure on
  dimension 3 and, more importantly, **the canonical statement of the
  three-edit dimension-extension pattern** that workflow step sequences must
  follow.
- `docs/DECISIONS.md` **D-IMPL-56** — RESOLVED 2026-07-27, implemented here.
  Read the entry *and* the SKILL.md-is-an-authoring-format paragraph that
  follows it.
- `docs/DECISIONS.md` **D-IMPL-04** — async-first runtime / sync core (binds
  D-14).
- `docs/DECISIONS.md` **D-IMPL-24** — all three harnesses ship v0 reference
  adapters; the template for how D-IMPL-60 should enumerate its consequences.
- `docs/DECISIONS.md` **D-IMPL-29** — two-tier skilling governance; the SDK
  never interprets a requirement identifier (basis for D-18's
  `allowed-tools` non-mapping).
- `docs/DECISIONS.md` **D-GATE-F** — the note establishing that intra-phase
  staging is sequencing, not a revision of a ruling (basis for D-05's build-order
  carve-out).
- `docs/DECISIONS.md` **D-GATE-I.3** — the full approved scope of what this
  phase builds on, including every narrowing I.3 recorded rather than claimed
  away.

### Phase inputs and precedent
- `.planning/ROADMAP.md` §"Phase 7" — goal, dependencies, and the four success
  criteria. **Criterion 2 is the sharpest**: CI verifies there is no path
  through the HITL surface producing an unrecorded human action.
- `.planning/REQUIREMENTS.md` — ORCH-01, ORCH-02, HITL-01, EXPR-01, EXPR-02,
  EXPR-03.
- `docs/PHASE_I3_GATE.md` **§5 — required reading.** The handoff is written as
  prerequisites with named consequences, not notes. Source of D-19..D-22 above.
- `docs/PHASE_I3_GATE.md` §1 — the two remaining CINV-04 skips and what
  activating them means for the suite's skip count.
- `docs/PHASE_I3_GATE.md` §4.12 — the D-IMPL-56 surfacing, with the
  divergence-no-test-would-catch consequence stated.
- `.planning/phases/06-phase-i-3-cross-process-harness-adapters/06-CONTEXT.md`
  — the slice-first pattern, the Protocols-in-`/src`/impls-in-`/runtime`
  boundary (D-04), the harness-extras posture (D-08), the conformance-suite
  pattern (D-09), and the cross-process test topology rules (D-15/D-16 — real
  subprocesses, ephemeral ports, readiness handshake, **never a sleep**).
- `.planning/phases/05-phase-i-2-agent-specialization-framework/05-REVIEWS.md`
  — the retrospective whose A2 finding is this phase's D-08 prerequisite.
- `docs/DESIGN.md` — the Orchestration and HITL pillar diagrams in
  `docs/diagrams/`, plus the invariant-preservation arguments this phase must
  not break. **Note the I.3 precedent:** `docs/DESIGN.md:745` was found
  stale-assigning the adapters to I.4 and was corrected in-phase; expect and
  correct similar staleness rather than coding to it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ccf/controlplane/state.py` — `ControlPlaneStateStore` Protocol +
  `InMemoryStateStore`. Its module docstring **already names this phase's
  consumer**: "suspended workflow execution state when I.4 brings it." Records
  are deliberately **opaque** and the module holds no vocabulary of its own, so
  the workflow state record type is defined next to the machine that
  transitions it, never here (CINV-01).
- `src/ccf/agents/definitions.py` — `TaskDefinition` / `TaskStep`, with
  `TASK_STEP_KINDS` and the `_ref_agrees_with_kind` validator. Schema and
  validation only; `factory.py:340` and `:427` both state that execution
  semantics are I.4's Workflow primitive scope. This is the artifact D-11 wraps.
- `src/ccf/skills/grants.py` — the `ApprovalSink` seam and the `grant_*`
  `AuditAction` members. `:439` states outright that "the suspending
  ApprovalGate that I.4 brings inherits this seam rather than a re-opened
  question," and `:354` that I.2 conforms via a scripted double while I.4's
  `ApprovalGate` conforms with the real thing. `:337` defers the human
  principal to D-IMPL-21 — i.e. to this phase.
- `tests/conformance/test_approval_sink.py` — the factory-parametrized
  conformance pattern, with a slot **already reserved** for I.4's real
  `ApprovalGate` (`:5`, `:62`).
- `src/ccf/replay/record.py` — `:25` records the doctrine line ("workflow step
  sequences extend it in I.4"), `:159` reserves dimension 4 for HITL actions,
  `:184` names the `TraceCorrelationHook` seam, `:262` notes that I.4 workflow
  chains extend the single-element `delegation_chain`. Four separate reserved
  extension points, all this phase's.
- `src/ccf/mcp/` + `runtime/ccf_runtime/mcp/` — the shared MCP client library
  and the egress server from I.3. The Experience-surface MCP edge is an
  addition to existing machinery, not new machinery.
- `src/ccf/harness/protocol.py` — `HarnessAdapterProtocol`; how agent nodes
  resolve to an executing harness. Its wording is deliberately scoped (D-20
  above) — do not upgrade it.
- `runtime/ccf_runtime/adapters/{claude_agent,langgraph,adk}/` — the three
  adapters whose `_tool_description` helpers D-IMPL-56 deletes, and whose
  `_build_graph` (LangGraph) must **not** be generalized (A7 / D-19).
- Hypothesis is wired and carrying 73+ properties; a state-machine engine is
  strong `hypothesis.stateful` territory if the planner wants it.

### Established Patterns
- **Refusals are typed return values; broken wiring raises.** Gate refusals
  (`GateRefusal`, `GrantRefusal`, `RegistrationRefusal`, `AdmissionRefusal`)
  are returned and inspected. A rejected approval is an expected outcome — a
  returned refusal — while a workflow node referencing a nonexistent artifact
  is broken wiring and raises.
- **Constructor injection everywhere** — registry, catalog, audit log, sink,
  clock, state store. No service holds a wall clock or keys of its own. The
  workflow engine must take its clock injected, or suspend/resume timestamps
  become untestable.
- **Audit refusals with `resolved=False`** — the audit plane records what it
  turned away. A rejected approval and an escalation that timed out both land
  in the journal.
- **Positive sentinels over `None`/absence** — `NO_HARNESS_TRACE`, `NO_GRANTS`,
  `NO_AGENT_DEFINITION`. Absence must be an asserted claim, so that a dropped
  value and a genuinely-absent value are different artifacts.
- **Canonical serialization refuses lossy types** (`canonical.py` normalizes
  field-by-field rather than via `model_dump()`; integer-percent similarity
  scores). Anything a workflow trace contributes to a replay record goes
  through it.
- **CINV-01 and No-Hardcoding apply to `/runtime` and `/examples`, not just
  `/src`** — which includes the CLI and the HTTP layer.

### Integration Points
- **Workflow engine → `ControlPlaneStateStore`** — suspend/resume, through the
  D-08 audit-bearing path only.
- **Workflow engine → replay dimensions 4 and 5** — step sequences and HITL
  actions, via the verbatim pre-serialized-block pattern.
- **Agent nodes → `HarnessAdapterProtocol`** — the workflow never names a
  harness; the adapter binding resolves it (§8.1, "harness-neutral at every
  node").
- **HITL primitives → `HITLTransportProtocol` → MCP endpoints** — queues as
  Resources, actions as Tools, on the Experience-Layer surface.
- **CLI → HTTP API → the same factories and Control Plane actions every other
  client uses** — zero privileged paths (D-IMPL-22).
- **`OrchestrationProtocol` → the workflow engine**, from
  `runtime/ccf_runtime/orchestration/<sdk>/`, with no import path to
  `runtime/ccf_runtime/adapters/<sdk>/` (D-06).
- **Terminal workflow trace → ArtifactStore**; live suspended state stays
  native (D-IMPL-18 / D-IMPL-27).

</code_context>

<specifics>
## Specific Ideas

- **"Not only LangGraph but Anthropic Agent SDK and Google SDK"** — stated
  unprompted, and the origin of D-05/D-06/D-07 and the new `D-IMPL-60`. All
  three v0 SDKs must be provable as *orchestrators*, mirroring D-IMPL-24's own
  logic for adapters. Three real legs; the staged alternative was declined
  explicitly.
- **"By construction" must be earned, not asserted** — the reason D-08 takes
  *both* mechanisms rather than the cheaper wrapper alone.
- **Every closure proved by observed counterfactual** — break it, watch it go
  red, put the output in the gate document. Dave's standing standard across
  I.3, made an explicit `must_haves` requirement here (D-10).
- **One write pattern at a time** — the reason the 8 grant call sites migrate
  in the closure plan rather than later (D-09).

</specifics>

<deferred>
## Deferred Ideas

- **Gray areas raised but not selected** (available to research if it finds
  them load-bearing; each has a governing ruling already, so none is a gap):
  front-door build order and HTTP framework choice (D-IMPL-22/23); HITL
  transport v0 scope — the webhook leg and the `test_approval_sink.py`
  parametrization slot (D-IMPL-20); replay dimension-5 extension shape,
  sentinel, and `TraceCorrelationHook` placement (D-IMPL-45/55).
- **Absent per-node exception ref semantics** (D-13 residual) — propagate to
  terminal vs. validation error at load. A real open question, not a deferral;
  research should resolve it or surface it as a `D-IMPL-NN`.
- **Advisory A3 — the Claude adapter's hand-built `ResultMessage` seam-4 leg.**
  Explicitly **Phase 8**'s obligation, owned by whoever writes
  `examples/03-harness-portability`, where a real Claude Agent SDK execution is
  available. Not discharged by anything here; do not let a plan claim it.
- **Loop-level harness portability** — not claimed by I.3 and not this phase's
  to claim. `examples/03` in Phase 8.
- **Advisory A7's underlying tension** — LangGraph is a topology-owning harness
  and its adapter necessarily authors execution shape. Documented, bounded by
  D-06's module split, and **not** resolved by generalizing it.
- **A heavyweight/durable workflow engine** — permanently out of scope (§8.1,
  §13). Reachable only via `OrchestrationProtocol`.
- **A human task-management inbox or UI** — out of scope (§8.2, §13). HITL
  events are exposed through Protocols; consumption is the user's choice.
- **Mobile SDK, chat adapter, web UI** — out of scope for v0 (§8.3). Users
  build them on the HTTP API and its OpenAPI spec.
- **Supervision Quality** — ruled out of v0 scope (D-IMPL-48).

</deferred>

---

*Phase: 7-Phase I.4 — Orchestration, HITL, Experience*
*Context gathered: 2026-07-29*
