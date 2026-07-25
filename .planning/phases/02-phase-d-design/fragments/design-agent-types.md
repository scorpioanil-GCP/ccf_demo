# Design Fragment — Core Agent Types Pillar

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

**Pillar:** Core Agent Types (CLAUDE.md §4). **Fragment scope per `entry-ownership.md`:** owned entries INV-CH6-05, INV-CH6-07, INV-CH6-08, INV-CH7-32, INV-CH7-84, INV-CH8-12, INV-CH8-22; see-also cross-references to INV-CH6-04, INV-CH6-06, INV-CH7-72, INV-CH8-13, INV-CH8-14, INV-CH8-20, INV-CH8-21 (owned elsewhere; touched here only where the agent framework consumes them).

**Extension status:** The entire Agent Specialization Framework is **SDK-defined, cites CLAUDE.md §6** — the whitepaper's Chapter 3 describes agents as consumers of the fabric; it does not specify a framework for building specialized agents. Every component below is labeled with its CLAUDE.md anchor and its whitepaper hook (per the SPEC_INVENTORY "SDK Extensions and Whitepaper Hooks" table).

**Provisional flagging:** all five governing rulings (D-IMPL-11, D-IMPL-12, D-IMPL-19, D-IMPL-28, D-IMPL-29) are RESOLVED by Dave (2026-07-25) — none provisional; no D-04 blockquote flags are required in this fragment (cross-checked against `fragments/provisional-register.md`: zero provisionals).

**Phase discipline:** contract altitude only. No implementation code in this fragment; type surfaces are named signatures, not bodies.

---

## 1. The unified `Agent` base and the archetype shape

*SDK-defined, cites CLAUDE.md §6.1, §6.3. Whitepaper hook: Ch 3 agents-as-consumers; §6.5/§6.6 consumption discipline (INV-CH6-05, INV-CH6-07).*

- **Responsibility:** A single concrete runtime class, `Agent`, is the factory's only output type. It carries the agent's identity, version, composed archetype list, channel-1 specialization record, and currently-bound skill-set. It implements **no reasoning loop** — the loop belongs to the harness (CLAUDE.md §6.5, §7.3); `Agent` is the fabric-side representation the harness adapter binds against.
- **Protocol/type signatures:** `Agent` (concrete, final — no user subclassing); `ArchetypeComponent` (Protocol) — a typed behavior bundle exposing `fabric_interaction_pattern()`, `replay_obligations()`, and `configuration_defaults()`; archetypes conform structurally, never nominally.
- **Invariants enforced:** archetype/agent separation is structurally safe precisely because there is nothing to subclass (D-IMPL-11 rationale). `/src` contains archetypes and the `Agent` class; it never contains an agent instance or definition — an agent found in library code is a defect of the same severity as a hard-coded half-life table (CLAUDE.md §6.1). Everything distinguishing one agent from another is serialized in its definition artifact, which is what makes replay dimension 4 capture mechanical (INV-CH7-84).
- **Seams:** code-level extension happens only via Protocol seams — skills (§7 below), harness adapters (design-experience-seams.md), and `ArchetypeComponent` implementations. Agents reach the fabric through the MCP access layer, never by direct graph access (INV-CH6-06, owned by design-experience-seams.md).
- **D-IMPL rulings embodied:** **D-IMPL-11** (RESOLVED — single concrete `Agent` class specialized entirely by artifact; archetypes as Protocol-typed composable behavior bundles; no class hierarchy).

The consumption discipline the base enforces is the whitepaper's (INV-CH6-05, §6.5): *"Agents do not consume data directly. They consume context."* The `Agent` base exposes exactly one fabric-read surface — contracted Context Product requests — and no raw-store query surface. The seven Context Product key principles (Runtime Construction, TTL, Policy-embedded, Entitlement-aware, Discoverable, Traceable, Interoperable) are properties of the products the agent consumes, upheld on the fabric side (design-data-context-b.md); the agent framework's obligation is the negative one: **no path from `Agent` to L1–L5 exists** — TTL-expired products are contract-invalid, not stale, so the base refuses them rather than degrading (INV-CH6-05 invariant).

## 2. The six archetypes

*SDK-defined, cites CLAUDE.md §6.3. Whitepaper hooks per the SDK Extensions table: §7.4.9 swarm operators + §6.6 recursive enrichment (ContextAssembly); §7.10.3 passage-anchored generation (ContentGeneration, DocumentIntelligence); §7.7 λ_c re-evaluation (Monitoring); T-dimension analysis (Analytics).*

Each archetype is an `ArchetypeComponent` bundle: an execution shape, a fabric-interaction pattern, and replay obligations — no identity, no prompts, no skills, no policy bindings, no domain values (CLAUDE.md §6.1). Archetype weighting of the six graph dimensions varies while the graph primitive stays constant (INV-CH8-13, owned by design-data-context-a.md — the graph lens on agentic work).

| Archetype | Fabric-interaction pattern | Replay obligations |
|---|---|---|
| **WorkflowAgent / TaskAgent** | State-machine execution against a task graph declared as a Control Plane artifact; deterministic step ordering; structured idempotency; heavy Orchestration Layer interaction (design-orch-hitl.md, §8.1) | Step sequence lands in replay dimension 5; calling chain in dimension 4 |
| **DocumentIntelligenceAgent** | Ingest/extract/analyze/generate over the Pattern 5 unstructured pipeline; passage-level lineage (§7.10.3) baked into every output | Passage anchors in the L dimension of emitted products; document-derivation trace in dimension 5 |
| **AnalyticsInsightsAgent** | Computation over Context Products: temporal analysis against the T dimension (INV-CH8-14, owned by design-data-context-b.md), threshold detection, cross-entity comparison, signal aggregation | Product versions and as-of times consumed land in dimension 1 references |
| **MonitoringSurveillanceAgent** | Long-running, trigger-driven: event subscription against L1 streams, threshold activation, λ_c-driven continuous re-evaluation | Trigger condition, threshold version, and activation timestamp per invocation |
| **ContentGenerationAgent** | Template binding + citation-aware generation — every claim passage-anchored (§7.10.3); draft-and-review HITL integration via ReviewQueue (design-orch-hitl.md, §8.2) | Prompt-artifact versions in dimension 3/5; ReviewQueue actions extend dimension 2 |
| **ContextAssemblyAgent** | Assembler producing typed Context Products for other agents — the §6.6 recursive-enrichment case and the §7.4.9 swarm-realized operator case (INV-CH7-32, §4 below); transport via in-process call, MCP egress, or A2A | The emitted product is itself a replayable artifact bound to the five-dimension envelope, distinct from any consumer's inference trace |

Per-archetype contract detail, in the standard field template:

**`WorkflowAgent` / `TaskAgent`**
- **Responsibility:** procedural, multi-step decisioning against a task graph declared through the Task Factory (never code); examples per CLAUDE.md §6.3: KYC, credit checks, onboarding, routing, fulfillment.
- **Invariants enforced:** deterministic step ordering; structured idempotency (re-invocation with identical inputs and Control Plane state is a no-op or an identical result); every node can yield to a first-class exception path (design-orch-hitl.md).
- **Seams:** Workflow primitive agent-nodes (D-IMPL-17); suspended state persists at the Control Plane boundary (D-IMPL-18).

**`DocumentIntelligenceAgent`**
- **Responsibility:** document ingest, metadata extraction, analysis, generation over the Pattern 5 pipeline.
- **Invariants enforced:** passage-level lineage (§7.10.3) in every output; the §4 alternation discipline when composed with generation.
- **Seams:** unstructured pipeline stages (D-IMPL-08, design-data-context-a.md); Citations-capable LLM access per D-IMPL-09 (semantic stages only).

**`AnalyticsInsightsAgent`**
- **Responsibility:** computation over Context Products — temporal analysis, threshold detection, comparative analysis, signal aggregation.
- **Invariants enforced:** consumes only contract-validated products; thresholds are Control Plane parameters (D-IMPL-38 discipline), never code constants.
- **Seams:** T-dimension mechanics owned by the fabric (INV-CH8-14, design-data-context-b.md).

**`MonitoringSurveillanceAgent`**
- **Responsibility:** long-running, trigger-driven watch: event subscription against L1 streams, threshold-based activation, λ_c-driven continuous re-evaluation.
- **Invariants enforced:** activation conditions and thresholds are versioned Control Plane values; each activation is an independently replayable invocation.
- **Seams:** L1 stream subscription surface (design-data-context-a.md); escalation via ExceptionEscalation on D_c breach (design-orch-hitl.md).

**`ContentGenerationAgent`**
- **Responsibility:** structured LLM output under template binding — credit memos, research notes, narrative reports.
- **Invariants enforced:** citation-aware generation — every claim passage-anchored (§7.10.3); templates are versioned prompt artifacts (axis 6), never inline.
- **Seams:** ReviewQueue draft-and-review integration (design-orch-hitl.md, §8.2).

**`ContextAssemblyAgent`**
- **Responsibility:** assembler producing typed Context Products for other agents — the recursive-enrichment and swarm-operator case (§4).
- **Invariants enforced:** emitted products honor the full contract (schema + λ_c + passage-level L); Policy-before-Similarity inside every assembly step; emission reaches L3 only through L2 (single-writer, CLAUDE.md §10).
- **Seams:** transport via in-process call, MCP egress, or A2A (design-experience-seams.md).

The archetypes encode the search ⇄ inference loop discipline (INV-CH6-07, §6.6): every loop iteration is a contracted Context Product request; the agent never self-assembles context, never queries raw stores, never reconstructs entity identity — *"assembly stays in the architecture; reasoning stays with the agent."* The loop itself (inference → drives search; search → enriches context; enriched context → improves inference) executes inside the harness; the fabric-side pattern the archetypes contribute is that each turn's operator composition is resolved by the Runtime from the request, not specified by the agent (INV-CH6-07 invariant). Decision-time content acquisition inside the loop rides the MCP client surface at L4–L5 (CLAUDE.md §7.1, cross-ref design-data-context-b.md).

**Trust-gated action (INV-CH6-08, §6.6.3).** The loop's stopping criterion is the Context Trust Triangle — Context Confidence, Context Freshness, Context Lineage Integrity — with **conjunctive** semantics: weakness in any leg degrades aggregate trust regardless of the other two. The agent framework's design obligation: the `Agent` base surfaces the trust legs of every consumed product to the harness adapter as typed inputs, and encodes the low-trust behavior as a first-class outcome set — **escalate** (ExceptionEscalation, design-orch-hitl.md), **re-request** (a different product), or **surface the weakness** — never silent action under aggregate-low trust. Per the D-IMPL-32 ruling's disposition (recorded in `docs/DECISIONS.md`), trust aggregation mechanics are a Control-Plane-configurable scoring surface: mechanism ships the interfaces, institutions supply thresholds — values, never SDK constants.

## 3. Archetype composition

*SDK-defined, cites CLAUDE.md §6.3. Whitepaper hook: archetypes are functional categories, not exclusive categories.*

- **Responsibility:** Multi-archetype agents (a monitoring agent that is also an assembler; a content generator whose output is a typed Context Product) are declared as an **ordered archetype list** in the definition artifact. The factory attaches the corresponding `ArchetypeComponent` bundles to the single `Agent` instance in declaration order.
- **Protocol/type signatures:** artifact field `archetypes: ordered list of archetype identifiers` (channel-1 axis 1); composition performed by the Agent Factory, never by the artifact author writing code.
- **Invariants enforced:** explicit conflict rules per **D-IMPL-19** (RESOLVED): identical obligations contributed twice are **deduplicated**; conflicting configuration defaults resolve by **declaration order with a factory warning**; hard contradictions are a **factory construction error**. The composed archetype list is channel-1 identity and lands in replay dimension 4 (INV-CH7-84).
- **Seams:** composition over mixins — no class hierarchy exists to entangle (D-IMPL-11); users combine archetypes by declaration only.
- **D-IMPL rulings embodied:** **D-IMPL-19**; **D-IMPL-11** (composition target is the single `Agent` class).

## 4. Swarm-realized operators and the assembly/consumption boundary — INV-CH7-32

*Whitepaper commitment (§7.4.9), realized here through the `ContextAssemblyAgent` archetype.*

- **Responsibility:** A Context Operator may be realized as an agent swarm whose sole job is slot-filling a typed Context Product (detection, classification, reconciliation, policy-filtered emission). The archetype framework is where the SDK houses this realization: an assembler swarm is a composition of `ContextAssemblyAgent`-archetype agents orchestrated per design-orch-hitl.md.
- **Invariants enforced (verbatim from INV-CH7-32):** output-contract determinism — the product emerges with its schema, its λ_c, and its passage-level L intact regardless of internal LLM-driven extraction; **Policy is composed before Similarity at every step the swarm takes**; the assembly/consumption boundary is typed and enforceable — the downstream reasoning agent consumes the completed product plus seed context and does not re-assemble context de novo. Auditors see two distinct replayable artifacts — the assembler swarm's Context Product and the reasoning agent's inference trace — interrogable independently, both bound to the §7.10 five-dimension envelope.
- **Seams:** operator-realization mechanism is §7.4's (L4, design-data-context-b.md); per-product mode selection (when to choose swarm assembly) is §7.6 Mode 3 territory (design-data-context-b.md). Swarm-level **intent decomposition** is an orchestration-layer concern and a named post-v0 extension candidate per the D-IMPL-49 ruling — intent compiles down to concrete product requests carrying the deterministic `(perspective, context_product_class, selection_params)` selection signature; coordination stays above Π (documented in design-orch-hitl.md; noted here because the swarm is archetype-realized).
- **D-IMPL rulings embodied:** **D-IMPL-49** (selection-signature determinism at the swarm's product requests); alternation invariant per §5 below.

**Alternating derivation inside archetype pipelines (INV-CH8-12, §8.4).** The Document-Heavy Compositional pattern — Algorithmic Perception → Semantic Comprehension → Algorithmic Verification → Semantic Synthesis — is the canonical shape the `DocumentIntelligenceAgent` and `ContentGenerationAgent` archetypes bind to when composed over the fabric. The design carries its invariants into the archetype contracts: the Algorithmic ⇄ Semantic Alternation is structural (LLMs never see raw signal; algorithmic stages never perform semantic interpretation — INV-CH6-04, owned by design-data-context-b.md, whose CI `@algorithmic` lint design lives in the Invariant Preservation chapter); LLM inference runs exactly twice, bounded by algorithmic stages; Policy-before-Similarity holds inside Verification; below-threshold candidate relationships are carried forward as distinct, never silently collapsed (threshold schema per the D-IMPL-38 parameter discipline — Control Plane values, not code); every synthesis claim is passage-anchored. The persist-into-G feedback loop is an L2 write path — the archetype never acquires a write handle (single-writer, CLAUDE.md §10). Auditability of agentic work at scale (INV-CH8-20, owned by design-data-context-b.md) is the payoff: archetype pipelines produce governance artifacts by mechanism, not by a separate track.

## 5. The Agent & Task Factory and the definition-artifact schema

*SDK-defined, cites CLAUDE.md §6.4. Whitepaper hook: §7.8.3 Control Plane configuration surface — agent/task/prompt/skill artifacts are additional Control Plane classes (INV-CH7-72, owned by design-data-context-b.md).*

- **Responsibility:** The factory is the **only** construction path for agents and tasks. It interprets declarative definition artifacts, validates them, composes archetype components, resolves instruction bindings, and emits `Agent` instances. There is no supported path that bypasses it — including in tests, which construct agents from fixture artifacts, never inline (CLAUDE.md §6.4).
- **Protocol/type signatures:** `AgentFactory.construct(definition_ref) -> Agent`; `TaskFactory.construct(definition_ref) -> Task`. Definition artifacts per **D-IMPL-28** (RESOLVED): **YAML validated by Pydantic v2 (`extra=forbid`) schemas with exported JSON Schema** for non-Python tooling; **Jinja2-templated prompt artifacts referenced by versioned URI — never inline text** — with template parameters declared in the referencing definition and validated at construction time.
- **Invariants enforced:** every artifact carries `schema_version` and `artifact_version` with **independent per-artifact-class semver lanes** (D-IMPL-28); artifact addressing is the D-IMPL-26 hybrid (content-addressed canonical identity + versioned URI, `@latest` forbidden in replay/lineage) — storage seam owned by design-experience-seams.md (ArtifactStore). Construction is deterministic: identical definition version + identical referenced-artifact versions produce an identical `Agent` configuration, which is what makes agent identity replayable.
- **Seams:** artifacts persist via the ArtifactStore Protocol (CLAUDE.md §7.4) and/or version control; the factory reads through Control Plane resolution, never raw storage.
- **D-IMPL rulings embodied:** **D-IMPL-28**; D-IMPL-26 (addressing, by reference).

**The No-Hardcoding Rule as structural design.** The rule (CLAUDE.md §6.4) is realized structurally, not aspirationally: (a) no prompt or system-instruction string literal in code — instruction text exists only in versioned prompt artifacts reached via axis-6 references; (b) no agent or task definition in code — the factory is the sole interpreter; (c) no task graph, routing table, threshold, approval rule, or skill grant as code constants — all are Control Plane artifacts interpreted by mechanism; (d) code contains interpreters and factories, never the things interpreted. The CI lint design (prompt-shaped-literal rejection; factory-bypass rejection) is specified in the Invariant Preservation chapter of DESIGN.md — this fragment cross-references it rather than duplicating it. The rule is what makes the archetype/agent boundary the same boundary as mechanism/values: two deployments on identical SDK versions run entirely different agent populations with zero diverging code (CLAUDE.md §6.1).

## 6. Channel 1 — Specialization (identity and constraint)

*SDK-defined, cites CLAUDE.md §6.2. Whitepaper hook: §7.10.1 dimension 4 (INV-CH7-84).*

Fixed in the definition artifact and versioned with it; changing any axis produces a **new agent version**. The six axes, each a typed artifact field validated per D-IMPL-28:

1. **Archetype binding** — ordered archetype list and composition per D-IMPL-11/D-IMPL-19 (§3 above).
2. **Context contract** — which Context Product schemas the agent reads, and/or which projection it emits to (contract bases per design-data-context-b.md).
3. **Perspective** — the Π role-conditioning bound into projection-plan selection via the D-IMPL-49 signature `(perspective, context_product_class, selection_params)`.
4. **Policy regime** — the Control Plane bundle in force: entitlements, jurisdictional bindings, regulatory regime, HITL policy, and the **envelope of skills the agent is permitted to bind** (feeds §7 tier-1 governance).
5. **Half-life and debt profile** — staleness tolerance and the `D_c` threshold triggering Forced LLM or Fail-Closed (mechanics owned by design-data-context-b.md; escalation routing by design-orch-hitl.md).
6. **Instruction bindings** — versioned-URI references to prompt/instruction artifacts, never inline text (D-IMPL-28).

**Replay capture (INV-CH7-84).** Dimension 4 — Perspective Conditioning — answers *"for whom, with what authority?"*: agent identity, role, tool inventory, delegation chain complete from originating principal to acting agent. The SDK-defined extensions land here by construction: **agent version and skill-set in force** (CLAUDE.md §6.2) and **workflow calling chain** (CLAUDE.md §8.1, design-orch-hitl.md) extend dimension 4. Because every distinguishing property is artifact-serialized (D-IMPL-11), dimension 4 capture is a mechanical serialization of `(agent_id, artifact_version, composed archetype list, six-axis record, skill-set snapshot, delegation chain)` — no reconstruction, no drift between what ran and what is recorded.

## 7. Channel 2 — Skilling (capability under governance)

*SDK-defined, cites CLAUDE.md §6.2. Whitepaper hook: §7.8.2 audit plane; §7.10.1 dimension 4.*

- **Responsibility:** Skills are typed, governed capabilities in a **dynamic Control Plane skill catalog** (D-IMPL-12): registered as typed, versioned Control Plane artifacts (D-IMPL-28 format) at boot or at runtime through an audited Control Plane action. **Four skill types:** local callable | MCP resource/tool | A2A endpoint (exposing remote Context Products) | tool — MCP-Resources-as-skills is one type, not the unified mechanism (D-IMPL-12, RESOLVED).
- **Protocol/type signatures:** catalog entries carry a typed **requirements declaration** (policy scope, context-contract access, egress) validated per D-IMPL-28; grants and revocations are **separate versioned artifacts referencing catalog entries by version** (D-IMPL-12).
- **Invariants enforced — two-tier governance (D-IMPL-29, RESOLVED):** **Tier 1** — the automatic policy-compatibility check, **always on and non-waivable**: the Control Plane refuses any bind whose declared requirements exceed the agent's policy regime (axis 4) or context contract (axis 2). **Tier 2** — policy regimes may declare that grants (all, or matching declared criteria) additionally require an **ApprovalGate** before taking effect (gate primitive per design-orch-hitl.md); whether tier 2 is engaged is Control Plane configuration — values, not SDK policy. Grant, approval, and effective-time all land in the audit record; the skill-set in force at decision time is part of the replay record — **a decision replays against the skills the agent actually had, not the skills it has now** (CLAUDE.md §6.2; dimension 4 per §6 above).
- **Seams:** the harness adapter's skill-exposure seam surfaces exactly the currently-bound skill-set as the harness's tools — no more, no less (CLAUDE.md §7.3 seam 2; adapter design in design-experience-seams.md, across all three D-IMPL-24 harnesses: Google ADK, Claude Agent SDK, LangGraph).
- **D-IMPL rulings embodied:** **D-IMPL-12**; **D-IMPL-29**; D-IMPL-24/25 (by reference at the adapter seam).

**Why two channels stay separate (design commitment).** Specialization changes *who the agent is*; skilling changes *what it can currently do*. The design keeps them structurally distinct: axis changes re-version the agent artifact; skill grants/revocations version the grant artifacts and never re-declare the agent. Collapsing them would force full redefinition per capability change or invite ungoverned capability sprawl — the separation buys stable identity for audit, capability agility under explicit governance, and the clean adapter seam (CLAUDE.md §6.2).

## 8. Adoption framing — INV-CH8-22

The whitepaper's archetype mapping framework (§8.11) commits a **platform-versus-domain split**: platform teams own fabric primitives; domain teams own domain-specific operators and Context Products. For the SDK this maps directly onto the mechanism-vs-values boundary the agent framework enforces: the six archetypes, the `Agent` base, the factory, and the skill-catalog mechanism are platform/SDK assets in `/src`; agent definitions, task definitions, prompt artifacts, skill catalogs, and grants are domain/user artifacts. The four whitepaper decisioning archetypes (Document-Heavy Compositional, Temporal Reconciliation, Forensic-Defensibility, Conversational Synthesis) are *use-case diagnostic categories* users realize by declaring agents from the six SDK archetypes — the SDK ships no domain archetype and no prioritization opinion (the framework is illustrative, not prescriptive — INV-CH8-22 invariant). The Conversational Reporting Layer adjacency (INV-CH8-21, owned by design-experience-seams.md) remains explicitly out of v0 scope; nothing in the archetype set pre-builds it.

## 9. Coverage

| INV key | Ownership | Covered in |
|---|---|---|
| INV-CH6-05 | owned | §1 (consumption discipline; seven principles as fabric-side properties the base respects) |
| INV-CH6-07 | owned | §2 (loop discipline in the archetype contracts) |
| INV-CH6-08 | owned | §2 (trust-gated action; conjunctive stopping criterion) |
| INV-CH7-32 | owned | §4 (swarm-realized operators via ContextAssemblyAgent) |
| INV-CH7-84 | owned | §6 (dimension 4 capture, mechanical by construction) |
| INV-CH8-12 | owned | §4 (alternating derivation bound into archetype pipelines) |
| INV-CH8-22 | owned | §8 (platform/domain split as mechanism/values boundary) |
| INV-CH6-04, INV-CH6-06, INV-CH7-72, INV-CH8-13, INV-CH8-14, INV-CH8-20, INV-CH8-21 | see-also | cross-referenced in §1, §2, §4, §5, §8 at the touchpoints named in `entry-ownership.md`; owned by their assigned fragments |
