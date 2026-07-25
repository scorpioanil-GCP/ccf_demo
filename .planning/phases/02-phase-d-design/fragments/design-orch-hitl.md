# Design Fragment — Orchestration Layer + Human in the Loop and Control Pillars

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

Both pillars are **SDK-defined extensions** — they cite CLAUDE.md §8.1 and §8.2 as their canonical surface, not the whitepaper. The whitepaper hooks they attach to are cited per inventory entry (INV-CHx-NN). Contract altitude per locked D-07: responsibilities, Protocol/type signatures, invariants, seams — no implementation code.

Owned entries (per `fragments/entry-ownership.md`): INV-CH7-55, INV-CH7-56, INV-CH7-65, INV-CH7-67, INV-CH7-68, INV-CH7-82, INV-CH7-88, INV-CH8-16, INV-CH8-18, INV-CH8-19, INV-CH8-23. See-also entries touched here with primary ownership elsewhere: INV-CH6-08, INV-CH7-32, INV-CH7-71, INV-CH7-75, INV-CH8-08.

---

## Pillar: Orchestration Layer

SDK-defined, cites CLAUDE.md §8.1. The whitepaper assumes a control plane and multi-agent workflows (INV-CH7-32 swarm-realized operators; INV-CH7-68 multi-agent handoff; INV-CH8-08 cross-org A2A ingress) but specifies no workflow primitive; the SDK provides one, minimal by design.

### Component: Workflow primitive

- **Responsibility:** Compose multi-agent and multi-step work as an explicit state machine with three node types — skill invocation, agent invocation, HITL gate — suspendable at the Control Plane boundary and resumable later. In-fabric coordination only; explicitly NOT a Temporal-scale durable-execution engine (CLAUDE.md §8.1 non-goal — "Reinventing Temporal is out of scope").
- **Protocol/type signatures:** `WorkflowDefinition` — a versioned Control Plane artifact (YAML per D-IMPL-28, `extra=forbid` validated) produced exclusively through the Task Factory, never expressed in code (No-Hardcoding, CLAUDE.md §6.4). Shape: named states, typed transitions, terminal conditions, per-node exception-path binding. `WorkflowNode ::= SkillNode(skill_ref@version) | AgentNode(agent_ref@version, context_contract_ref) | HITLGateNode(gate_class, hitl_policy_ref)`. `WorkflowExecutionState` — typed, versioned record: `{workflow_ref@version, current_node, variable_bindings, pending_gate_refs, trace_ref}`.
- **Invariants enforced:**
  - **State machine semantics** — explicit states, transitions, terminal conditions; no implicit control flow (CLAUDE.md §8.1).
  - **Exception paths are first-class transitions** — every node declares an exception path (typically a HITL gate: ExceptionEscalation); exceptions are state transitions, never glued-on error handling (CLAUDE.md §8.1).
  - **Harness-neutral at every node** — an AgentNode invokes an agent *definition*; the executing harness resolves through the adapter binding (CLAUDE.md §7.3, D-IMPL-24/25), never through the workflow.
  - **Replay by construction** — every state transition appends to the execution trace; traces extend replay dimension 4 (Perspective Conditioning: the calling agent chain) and dimension 5 (Content Generation Path: the step sequence). A workflow re-replays exactly under the same inputs and Control Plane state (CLAUDE.md §8.1, §11).
  - **Debt cascade honored across handoffs** — INV-CH7-68: at every AgentNode handoff boundary the downstream agent's D_c is recomputed against inherited plus interim observations (inherited staleness plus elapsed λ_c decay); a class-threshold breach at any handoff triggers fail-closed routing into the node's exception path (typically ExceptionEscalation). "Debt compounds at agent speed, not human speed" is a workflow-boundary obligation, not an agent courtesy.
- **State persistence (D-IMPL-18, RESOLVED):** Suspended `WorkflowExecutionState` lives at the Control Plane boundary as typed, versioned state records on the Control Plane's native store — mutable until terminal, therefore off the ArtifactStore per the D-IMPL-27 mutability rule. The execution trace is written through to the ArtifactStore as part of the replay record at terminal and at each suspend (long-horizon audit). Persistence substrate is the Control Plane's storage seam — pluggable there; no separate workflow-store Protocol.
- **Seams:** Task Factory (definition artifacts in); Control Plane (state persistence, suspension/resume); HITL primitives (gate nodes); Harness Adapter binding (AgentNode execution); ArtifactStore (terminal/suspend trace write-through, D-IMPL-27); replay record (dimensions 4/5).
- **D-IMPL rulings embodied:** D-IMPL-17 (minimal Workflow primitive + `OrchestrationProtocol`), D-IMPL-18 (Control Plane state persistence), D-IMPL-28 (definition artifact format), D-IMPL-24 (harness-neutral node resolution across all three v0 adapters).

### Component: OrchestrationProtocol

- **Responsibility:** The seam to external, Temporal-class orchestrators (D-IMPL-17, RESOLVED). Users who need enterprise-grade durable execution implement `OrchestrationProtocol` against their engine; the SDK ships the Protocol plus the in-SDK Workflow primitive as its reference realization.
- **Protocol/type signatures:** `OrchestrationProtocol` — Protocol-based (CLAUDE.md §11 "Prefer Protocols over inheritance"): execute a `WorkflowDefinition`, surface suspension/resume events, and deliver execution traces satisfying the identical replay obligations as the in-SDK primitive. An external engine that cannot deliver replay-complete traces is a non-conforming implementation, not a degraded mode.
- **Invariants enforced:** Identical replay obligations — traces land in dimensions 4/5 regardless of engine; HITL gates encountered under an external orchestrator still route through the SDK's HITL primitives (audit-by-construction is not delegable to the engine).
- **The LangGraph two-seam boundary (D-IMPL-17 + D-IMPL-24, explicit per the rulings):** LangGraph is one tool with two distinct, never-conflated seams. (1) The LangGraph *harness adapter* (`/runtime/adapters/langgraph/`) binds only the §7.3 agent-loop seams — context injection, skill exposure, effect capture, replay hooks — for an agent whose reasoning loop runs under LangGraph. (2) LangGraph *as an orchestrator of CCF agents* is a distinct, optional `OrchestrationProtocol` integration, subject to the same replay obligations as any external engine. An agent running under the LangGraph harness inside a workflow executed by the in-SDK Workflow primitive is the normal composition; LangGraph orchestrating that workflow is a separate, explicit integration choice.
- **Seams:** external engine (behind the Protocol); Workflow definitions (shared artifact format); HITL primitives (gates non-bypassable); replay record.
- **D-IMPL rulings embodied:** D-IMPL-17 (scope and the LangGraph disambiguation), D-IMPL-24 (adapter-vs-orchestrator separation).

### Orchestration and the assembly modes (Mode 3)

- **Responsibility mapping:** INV-CH7-55 — Mode 3 (algorithmic orchestration with agent-swarm assembly) is the assembly mode in which a coordinator dispatches agents (including across federated trust boundaries via A2A, INV-CH8-08) and verifies/reconciles their typed contributions. The Orchestration Layer is where Mode 3's coordinator lives; the Data and Context Layer owns the per-product mode-selection registration (§7.6 owns mode selection; §7.4 owns operator realization — INV-CH7-32).
- **Invariants enforced:** INV-CH7-56 / INV-CH7-88 — Mode 3 moves the determinism boundary to the orchestration layer: mode selection, typed contributions, and reconciliation are replay-deterministic; the replay record adds the three Mode 3 primitives verbatim — `orchestration_plan_id` (content-addressed per D-IMPL-26), `per_agent_version_manifest` (agent identity, framework version, prompt version, tool inventory — populated mechanically from the D-IMPL-11 agent artifacts and D-IMPL-19 composed archetype lists), and `per_agent_contribution_boundary_markers`. Per-agent contributions are recursively their own Mode 1/2/3 records; modes extend, never modify, the five-dimension baseline (INV-CH7-88). Trust-path purity holds: the algorithmic substrate, never any probabilistic presentation, is what replay commits to (INV-CH7-55).
- **Swarm-realized operators (INV-CH7-32, see-also from design-agent-types.md):** an operator realized as an agent swarm honors the same typed output contract (schema + λ_c + passage-level L) as any code-and-pipeline realization; Policy-before-Similarity holds inside swarm steps; the workflow that realizes the swarm is an ordinary `WorkflowDefinition` whose trace satisfies the Mode 3 replay footprint.
- **Cross-org ingress (INV-CH8-08, see-also from design-experience-seams.md):** A2A is the cross-organizational orchestration ingress Mode 3 consumes. The Orchestration Layer treats a remote contribution as an AgentNode result arriving over the wire; admission (consumer-side Control Plane verification before L3 entry, D-IMPL-16) belongs to the A2A seam, not to the workflow.

### Swarm-level intent decomposition — named post-v0 extension (D-IMPL-49 DESIGN.md obligation)

Per the D-IMPL-49 ruling, this is recorded explicitly: **swarm-level intent decomposition is an orchestration-layer concern and a NAMED post-v0 extension candidate.** In v0, intent never reaches Π as free inference — where plan selection varies by intent, intent is a declared enum-valued selection parameter inside the canonical deterministic projection-selection signature `(perspective, context_product_class, selection_params)`. The post-v0 extension shape: an intent-decomposition stage in the Orchestration Layer compiles a high-level intent down to concrete Context Product requests each carrying that signature; coordination stays above Π; replay stays deterministic because every compiled request is fully determined by its signature plus plan version. Nothing in v0's Workflow primitive precludes this — it composes as a coordinator pattern over existing nodes.

---

## Pillar: Human in the Loop and Control

SDK-defined, cites CLAUDE.md §8.2. Whitepaper hooks: escalation/fail-closed routing (INV-CH7-65, INV-CH7-67, INV-CH8-16, INV-CH8-18), the audit plane (INV-CH7-71), the closed-loop interpretation gate (INV-CH7-75, D-IMPL-43), and replay dimension 2 extension (INV-CH7-82).

### The four HITL primitives

All four share one structural contract: each primitive's **only completion path** is a typed action record that carries a `HumanPrincipalBinding` (D-IMPL-21) and lands in the Decision Replay record. There is no alternate return path.

- **ApprovalGate**
  - **Responsibility:** A workflow step that suspends until a human approves or rejects (CLAUDE.md §8.2).
  - **Protocol/type signatures:** Pending record: `{gate_id, workflow_state_ref, context_product_ref (content hash per D-IMPL-26), deadline/escalation_policy_ref}`. Action record: `{approve|reject, HumanPrincipalBinding, action_time, context_product_hash_seen, annotations}`.
  - **Invariants enforced:** The replay record captures the approver's identity, the time of approval, the Context Product the approver saw (by content hash — the approver's view is pinned, not "latest"), and any annotations. Suspension persists workflow state per D-IMPL-18 before the gate blocks; resume is a state transition, never a re-execution.
- **ExceptionEscalation**
  - **Responsibility:** Routes a workflow state to a designated human role when a condition is met — canonically a `D_c` threshold breach or an agent's explicit escalation (CLAUDE.md §8.2).
  - **Invariants enforced:** This primitive is the SDK realization of the whitepaper's fail-closed escalation pathway: INV-CH7-67 (elevated D_c biases urgency upward; uncertainty is surfaced and routed into human-escalation, additional-source-fetch, or decision-decline paths — never smoothed); INV-CH8-18 (detect → inherit → escalate/refuse is architectural, not advisory; no decision path exists on a silently-high-Debt product); INV-CH8-16 / INV-CH7-65 (the CAR forced-escalation state hands off here — the routing decision itself lands in the replay record as a regulatory artifact). Trigger sources are typed: `DcThresholdBreach(class_threshold_ref)` | `ExplicitEscalation(agent_ref, reason)`. Thresholds are per-class Control Plane values (D-IMPL-40, D-IMPL-38) — never SDK constants.
- **OverrideBoundary**
  - **Responsibility:** A typed boundary at which a human substitutes a value the agent would otherwise have produced (CLAUDE.md §8.2).
  - **Invariants enforced:** Both the original agent output and the override land in the replay record — the override never erases what it overrode. The override record is typed against the value's contract (`extra=forbid`); an override that does not validate against the contract is refused, not coerced.
- **ReviewQueue**
  - **Responsibility:** Asynchronous human review of ContentGenerationAgent outputs before release (CLAUDE.md §8.2).
  - **Invariants enforced:** Integrates passage-level lineage so reviewers see what each claim is anchored to — consuming the `PassageCitationProvider` output contract (D-IMPL-46), never a vendor API. Release/reject actions carry the full binding + annotation contract of ApprovalGate actions.
  - **Trust Triangle hook (INV-CH6-08, see-also):** an agent facing aggregate-low trust "must not act — it escalates, requests a different product, or surfaces the weakness"; the conjunctive trust gate's escalation branch (per-leg thresholds via the D-IMPL-32 `TrustScorer`) routes into ExceptionEscalation/ReviewQueue, with every computed leg score and verdict in the replay record.

### Audit-by-construction — the structural argument

The claim (CLAUDE.md §8.2): no path through the HITL surface produces an unrecorded human action. The design shows this **structurally**, not aspirationally:

1. **Single ingress/egress construct.** All four primitives enqueue and dequeue exclusively through the `HITLTransportProtocol` typed queue (D-IMPL-20). Pending events are typed records; actions return through the same surface. There is no primitive method that accepts a human action outside the queue contract.
2. **The action record is the completion token.** A suspended gate transitions state only when the Workflow primitive receives a validated action record — and the action record's schema (`extra=forbid`) makes `HumanPrincipalBinding` a required field (D-IMPL-21: subject id + identity-provider reference, authentication context, action time, content hash of the product seen). An unbound action is a validation failure at the boundary, not a recorded-but-anonymous action.
3. **Replay write precedes state transition.** The transition function is defined as: validate action → append action record to the replay record (extending dimension 2, Policy Bindings Snapshot, per INV-CH7-82's SDK extension) → transition workflow state. The replay append is a precondition of the transition, in the same construction-order sense that lineage strict equality is a validation gate at L6 — enforced at write time, not retrofitted (CLAUDE.md §11).
4. **Webhooks cannot bypass it.** The secondary webhook transport is notify-only (D-IMPL-20): the webhook notifies; the action always flows back through the typed queue. Notification and authority are separated by construction.
5. **Audit-plane grounding (INV-CH7-71, see-also):** the Control Plane is also the audit plane — HITL action records are Control Plane audit events versioned and retained against the decisions made under them, which is what makes the replay extension queryable years later.

CI verifies the invariant (Phase I obligation, CLAUDE.md §8.2/§3.1): replay-by-construction checks assert that every HITL completion path emits the replay write.

### Transport (D-IMPL-20, RESOLVED)

`HITLTransportProtocol` — a typed queue interface as the core mechanism. Pending HITL events (all four primitive classes) are typed records: event class, workflow state reference, the Context Product the human must see, deadline/escalation policy reference. Two reference transports ship: (1) **MCP server endpoints** exposing HITL queues as Resources and actions as Tools on the Experience-Layer surface — primary; serves example 05 and the `ccf hitl` CLI (D-IMPL-22); (2) **webhooks** — secondary, notify-only, per the structural argument above. Non-goal (CLAUDE.md §8.2, §13): no human task-management UI, no workflow inbox — users wire the queue to their existing human-task systems.

### Identity binding (D-IMPL-21, RESOLVED)

Pluggable via the same `IdentityProvider` Protocol family as D-IMPL-15, with a distinct human-principal binding shape: every HITL action record carries a typed `HumanPrincipalBinding` — approver identity (subject id + identity-provider reference), authentication context (method, assurance level, session reference), action time, and the content hash (D-IMPL-26) of the Context Product the approver saw. OIDC/SAML enterprise providers are the expected human-principal path (vs. mTLS+JWS for workloads). Reference impls: authenticated-principal record from the HTTP/MCP auth context (dev) and a JWS-signed binding reusing the D-IMPL-15 signing machinery for cryptographic non-repudiation. Audit-by-construction holds regardless of provider: no HITL action lands without a binding.

### HITL in the closed loop (D-IMPL-43; INV-CH7-75 see-also)

The closed-loop interpretation step (INV-CH7-75: outcome signal → Control Plane interpretation → versioned update) is human-gated by default per the D-IMPL-43 ruling: every closed-loop Control Plane update flows through a workflow with an ApprovalGate; Control Plane policy may configure specific signal classes × parameter classes × bounded deltas as auto-applied (tier 1 bounds validation per D-IMPL-38 always on; tier 2 ApprovalGate unless explicitly waived per class). Gated or auto, every update is a versioned Control Plane action in the audit plane — "the loop is in the graph, not the model" holds either way. This makes the HITL pillar a structural participant in Closed-Loop Self-Learning, not an adjacent feature.

### Supervision Quality (INV-CH8-19) — deferred disposition

Per the D-IMPL-48 ruling, Supervision Quality is **out of v0 SDK scope** — a documented reference pattern, not mechanism. §8.8 is a domain application of committed primitives: behavioral-signal axes are domain values; the fusion function is calibration; the VLM/LLM reasoning stage is ordinary semantic-stage mechanism under the Alternation invariant. Everything a deployment needs already exists in this design: signals via L1, axis computations as user-registered operators (D-IMPL-37), the composite as a user-defined Context Product class, thresholds via D-IMPL-38, and rubber-stamp escalation via ExceptionEscalation/ReviewQueue. DESIGN.md's synthesis records the "how you would build it" sketch; no SDK type is named `SupervisionQuality`. This deferral is a ruled disposition, not a coverage gap: INV-CH8-19 maps to *deferred* in Appendix A with D-IMPL-48 as the reason.

### Governance and SDLC alignment (INV-CH8-23)

Both pillars produce the governance legibility §8.12 commits to: workflow definitions, HITL policies, approval rules, and escalation thresholds are versioned Control Plane artifacts moving through the same SDLC gates as models and applications; the Control Plane / Data Plane boundary (INV-CH7-70/71, owned by design-data-context-b.md) is what lets a HITL-policy change deploy as a control-plane action without disrupting data-plane assembly. The three governance primitives (λ_c, D_c, Supervision Quality where a deployment builds it) remain measurable because the routing they drive (INV-CH8-16) and the human actions they trigger land in replay by construction.

---

## Coverage map (owned entries → section)

| INV key | Disposition | Section |
|---------|-------------|---------|
| INV-CH7-55 | mapped | Orchestration and the assembly modes (Mode 3 coordinator locus) |
| INV-CH7-56 | mapped | Orchestration and the assembly modes (Mode 3 replay footprint) |
| INV-CH7-65 | mapped | ExceptionEscalation (CAR forced-escalation handoff) |
| INV-CH7-67 | mapped | ExceptionEscalation (fail-closed, conservative bias) |
| INV-CH7-68 | mapped | Workflow primitive invariants (debt cascade across handoffs) |
| INV-CH7-82 | mapped | Audit-by-construction step 3 (dimension 2 HITL extension) |
| INV-CH7-88 | mapped | Orchestration and the assembly modes (Mode 3 record primitives) |
| INV-CH8-16 | mapped | ExceptionEscalation (routing as regulatory artifact) |
| INV-CH8-18 | mapped | ExceptionEscalation (detect → inherit → escalate/refuse) |
| INV-CH8-19 | deferred (D-IMPL-48) | Supervision Quality — deferred disposition |
| INV-CH8-23 | mapped | Governance and SDLC alignment |

See-also entries (owned elsewhere, touched here): INV-CH6-08 (ReviewQueue trust hook), INV-CH7-32 (swarm-realized operators), INV-CH7-71 (audit-plane grounding), INV-CH7-75 (closed-loop gate), INV-CH8-08 (cross-org ingress).

## Provisional flags

None of the rulings embodied in this fragment (D-IMPL-17, 18, 20, 21, 24, 25, 26, 28, 29, 32, 40, 43, 46, 48, 49) are provisional — all carry `RESOLVED` status with Dave as approver in `docs/DECISIONS.md`. D-IMPL-10 (repo shape) remains provisionally resolved but is not load-bearing for either pillar.
