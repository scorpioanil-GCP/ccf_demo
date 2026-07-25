# Data and Context Layer — Part B (L4–L6, Half-life/Debt, Replay, Closed Loop, Planes)

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

Fragment scope: the read side of the fabric pillar — L4 Context Operators, L5 Context Projection, L6 Context Products — plus Context Half-life λ_c and Context Debt D_c, the five-dimension Decision Replay record and replay engine, Closed-Loop Self-Learning, and the cross-cutting Control Plane / Data Plane separation. Companion fragment `design-data-context-a.md` owns L1–L3, ingestion, the graph, and single-writer scope. Contract altitude throughout — no implementation code (locked D-05/D-06/D-07). Owned-entry coverage contract: `fragments/entry-ownership.md`.

---

## L4 — Context Operators (System of Computation)

### Component: Operator algebra and the four canonical categories

- **Responsibility:** Typed, composable, read-only computation over the Context Graph. Four canonical categories cover the operation space (INV-CH7-22): **Traversal** — bounded relationship walks `Traversal(relationship-types, depth-limit, materiality-threshold)` producing bounded-expansion-of-relevance, never exhaustive expansion (INV-CH7-24); **Temporal** — bitemporal valid-time/observed-time reconciliation `Temporal(as-of-T)` as a correctness semantic, not a TTL filter (INV-CH7-25); **Policy** — principal/jurisdiction/entitlement subgraph **substitution** at the graph layer, never a row-level filter (INV-CH7-26); **Similarity** — corpus-scoped ranking `Similarity(threshold)` with the index version pinned in L and the determinism contract tuple `(corpus_version, embedding_model_version, query, threshold, policy_regime) → same result` (INV-CH7-27).
- **Protocol/type signatures (contract altitude):** `ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity` with ∘ read right-to-left; three- and four-operator compositions are normal — the algebra defines the composition surface, a request picks from it (INV-CH7-23). Each operator is typed in inputs, outputs, and its side-effect-free read-only-**sync** contract against the graph (INV-CH7-22); per the D-IMPL-04 ruling the operator/projection path stays sync inside the async-first runtime.
- **Invariants enforced:**
  - **Composition-preservation `(A∘B)(G) = A(B(G))`** is a design property verified empirically for every shipped operator pair (CLAUDE.md §11): intermediates are individually replayable, cache-coherent under λ_c-driven invalidation, and lineage-complete — each intermediate carries its own provenance sub-chain (INV-CH7-23). The layer-boundary discipline of INV-CH7-06 and the operator-purity commitment of INV-CH7-11 carry forward here: L4 reads L3, never writes it.
  - **Policy-before-Similarity ordering** — similarity ranks only over the principal-permissible subgraph; "no filter runs after retrieval because no retrieval of inadmissible content happened" (INV-CH7-26). The governance-side restatement (MNPI leakage structurally prevented, not post-hoc mitigated) is INV-CH8-17.
  - **Function-determinism** — "determinism is a property of the function, not the value": `(graph_state, control_plane_config, temporal_boundary, execution_plan) → bit-for-bit identical ContextProduct`, with legitimate value-variance from bitemporal state and decay explicitly expected (INV-CH7-31).
  - The four worked compositions (covenant cross-reference, intraday liquidity, AML Policy-before-Similarity, credit-exposure traversal — INV-CH7-30) are design-space demonstrations; their thresholds (0.85/0.75) and regimes are illustrative domain values, never SDK constants.
- **Seams:** `SimilarityIndex` Protocol per the D-IMPL-03 ruling — reference implementation on sqlite-vec (dev default), Chroma second if budget allows; vendor-neutral corpus/index versioning with version-pinned reads is a Protocol obligation (required by the INV-CH7-27 determinism contract and by D-IMPL-06 similarity-index snapshotting). Embeddings via `EmbedderProtocol` per the D-IMPL-07 ruling with `(model_id, model_version)` reporting as a contract obligation. Operator parameters (materiality floors, thresholds, temporal-boundary rules) are typed, versioned `OperatorParameterSet` Control Plane artifacts per the D-IMPL-38 ruling — declared schemas, no SDK-side domain defaults, in-force version captured in L per invocation.
- **D-IMPL rulings embodied:** D-IMPL-03, D-IMPL-04, D-IMPL-07, D-IMPL-38.

### Component: Operator Plan DAG generator (Planner) and registry

- **Responsibility:** Given agent intent (role, decision class, entity reference), select required operators from the registry, topologically order them into a dependency-correct plan (Policy before Similarity; Temporal before Traversal where Traversal reads temporally-reconciled state), and hand the plan to the projection engine (INV-CH7-28). Batch-resolve operator references DataLoader-style — one query per operator type per call (INV-CH7-29).
- **Protocol/type signatures:** `planOperators(agent_intent: {role, decision_class, entity_ref}, operator_registry) -> OperatorPlan` (INV-CH7-28).
- **Invariants enforced:** Boot-time-loaded registry with fail-fast duplicate registration — duplicate key is a boot failure, never a runtime request error (INV-CH7-29). Plan generation is deterministic because the registry is deterministic at runtime.
- **Seams:** Registry population is an explicit boot-time `register(operator_key, operator)` API at the composition root per the D-IMPL-37 ruling — no entry-point or import-side-effect registration in v0; the Control Plane declares which registered operators are permitted/parameterized, but code registers them. Intermediate materialization is a deterministic cache keyed on `(tenant, operator_key, parameter_set_version, input_intermediate_keys, graph_snapshot_id)` per the D-IMPL-36 ruling: a cache hit is by construction the value replay would produce; invalidation rides the supersession/Policy-event cascade lazily; when-to-cache, retention, and eviction budget are per-class Control Plane values under D-IMPL-38. The Planner's intermediate-reuse decision at the composition-preservation checkpoint (Fig-CH07-10) reads this cache (INV-CH7-33 end-to-end sequence: intent → OperatorPlan → four-operator execution in dependency order → Π → contract-validated product → TTL cache write).
- **D-IMPL rulings embodied:** D-IMPL-36, D-IMPL-37, D-IMPL-38.

### Component: Operator realization neutrality (swarm-realized operators)

- **Responsibility:** The algebra is the determinism surface; valid operator realizations include code-and-pipeline, SQL-backed, graph-traversal, and agent-swarm operators, provided the typed output contract (schema + λ_c + passage-level L) holds regardless of internal realization (INV-CH7-32, see also the Core Agent Types fragment which owns this entry's agent-side design). Policy-before-Similarity holds inside every swarm step; per-product mode selection belongs to §7.6 Mode 3 (INV-CH7-55). Decision-time content acquisition by operators uses the MCP client surface per the D-IMPL-13 ruling — the same client library as L1 ingress, serving L4–L5 acquisition; acquisition results reach L3 only via L2, so single-writer is unaffected. The search ⇄ inference recursion of INV-CH6-07 is engineered here: every loop iteration is a contracted Context Product request; agents never self-assemble context.
- **D-IMPL rulings embodied:** D-IMPL-13.

---

## L5 — Context Projection (Π, System of Interpretation)

- **Responsibility:** Π is a typed transformation performing subgraph **substitution**, not filtering: its output is itself a valid Context Graph for the principal — construct once, interpret many (INV-CH7-40). Role-shaped views condition at runtime on the tuple (role, intent, temporal context, policy regime), avoiding both precompute-everything and resolve-at-read-time failure modes (INV-CH7-43).
- **Protocol/type signatures:** The `ProjectionPlan` structural interface — any type exposing `required_operators()` + `invoke()` qualifies; dispatch is structural typing, never inheritance; every registered projection returns a typed `ContextProductContract` subclass (INV-CH7-41). Two-stage execution: the Operator Plan answers "what is true" (principal-agnostic, memoizable); the Projection Plan answers "what that truth means in this decision context" (principal-conditioned), reading operator-produced metadata during invocation — neither concern leaks into the other (INV-CH7-42).
- **Invariants enforced:** Output of Π composes with the operator algebra as if it were the full graph — no leak-by-absence (INV-CH7-40). Projection is stateless by invariant — no write locks, no in-process cache; materialization lives in a separately gated tier (INV-CH7-73(b)). Every projection's lineage (plan_id, operators_invoked, policy_version, graph_snapshot_at) lands in the Contract. The Contract is the output stability layer: operator re-implementation, graph-class extension, and policy versioning all evolve behind the Contract boundary (INV-CH7-44).
- **Seams:** Plan selection uses the canonical deterministic signature `(perspective, context_product_class, selection_params)` per the D-IMPL-49 ruling — perspective is channel-1 axis 3; `selection_params` is an optional typed block declared per product class under the D-IMPL-38 discipline; free intent inference is out of v0 scope (intent, where needed, is a declared enum-valued selection parameter). `(perspective, product_class, selection_params, plan_version)` fully determines the selected plan, preserving replay determinism. **DESIGN.md obligation carried per the D-IMPL-49 ruling:** swarm-level intent decomposition is an orchestration-layer concern and a NAMED post-v0 extension candidate — intent compiles down to concrete product requests carrying this signature; coordination stays above Π; replay stays deterministic (cross-reference: Orchestration pillar fragment).
- **D-IMPL rulings embodied:** D-IMPL-49, D-IMPL-38, D-IMPL-07 (embedder identity feeds projection-time similarity acquisition).

---

## L6 — Context Products (System of Delivery)

### Component: ContextProductContract

- **Responsibility:** The typed delivery contract every projection returns. Per the **D-IMPL-30 ruling the specification has nine elements including Assembly Mode** (INV-CH6-03): Schema, Freshness SLA, TTL, Policy Binding, Lineage, Semantic Versioning, Discovery, Addressability, Assembly Mode. The "eight-element" references (including CLAUDE.md §5's) are recorded as an annotated editorial-drift discrepancy per that ruling; the Fig-CH07-13 seven-field typed base (INV-CH7-45) is a different artifact — base contract *fields* vs. specification *elements* — and the mapping is: `schema_name`/`schema_version` realize Schema and Semantic Versioning; `expires_at` + `ttl_anchor` realize TTL; `lineage {operators_invoked, policy_version, graph_snapshot_at}` realizes Lineage and carries the Policy Binding version; `plan_id` binds the product to its projection (Π identity); `payload` is per-product typed; Freshness SLA, Discovery, Addressability, and Assembly Mode are class-level registration properties maintained by the Control Plane at product-class registration, surfaced through the registry and egress surfaces rather than as instance fields. A Context Product is a typed, governed, decision-ready unit of meaning shaped jointly by Intent, Perspective, Time, and Policy (INV-CH6-02) — the category-change answer to data products: runtime-assembled, TTL-bound, policy-formative, entitlement-formative (INV-CH6-01).
- **Protocol/type signatures:** `extra=forbid` typed base (Pydantic v2 per the D-IMPL-01 ruling); fields: `schema_name` (classvar), `schema_version` (semver), `plan_id`, `expires_at`, `ttl_anchor ∈ {from_decision, from_entity_freshness}`, `lineage`, `payload` (INV-CH7-45). Per-product independent semver lanes — a version bump on one product class never touches another (INV-CH7-49).
- **Invariants enforced — the three validation gates (verbatim):**
  1. **empty-operator guard** — rejects a Contract whose `operators_invoked` is empty; refusal is a structured rejection, never silent acceptance (INV-CH7-46).
  2. **lineage strict equality** — declared `operators_invoked` set must equal the engine-resolved operator set; forgery, omission, and drift all fail; passage-level anchors verified for every unstructured-derived claim (INV-CH7-47; restated at the plane boundary as INV-CH7-73(c); L6-gate placement per INV-CH7-13).
  3. **TTL bounds** — `now < expires_at ≤ now + MAX_TTL`, re-verified at cache-write time (INV-CH7-48). Per the **D-IMPL-39 ruling** MAX_TTL is required Control Plane configuration per product class — no SDK default; an unregistered MAX_TTL fails Control Plane validation at product-class registration; the in-force MAX_TTL version lands in the policy-bindings replay dimension.
  No invalid product reaches an agent, enters the cache, or contaminates the replay record; the three-gate sequence (Schema Validator, Policy Gate, Lineage Completeness Checker) runs before any cache write or delivery, and the cache lookup key is the composite `(tenant, schema_name, plan_id, graph_snapshot_id, principal binding)` (INV-CH7-52) — tenant-first per the D-IMPL-05 ruling.
  TTL granularity follows the **D-IMPL-31 ruling**: two granularities with a declared per-class derivation rule — signal-level validity envelopes derived from type λ_c, and product-level `expires_at = min(class MAX_TTL ceiling, derivation over constituent signal validities)`, with constituent-validity floors whose breach refuses assembly (the mixing-refusal rule) rather than emitting a product fresher-labeled than its stalest load-bearing constituent (INV-CH6-04 Step 4).
- **Seams:** Egress via in-process call, the MCP egress server (L6 Context Products as Resources, permitted agent invocations as Tools, per the D-IMPL-13 ruling — one server, two resource families; INV-CH8-07 Pattern 3), or A2A endpoint (Experience/seams fragment owns the transport design). MCP remains the access layer, CCF the construction layer — MCP never manages state, enforces temporal logic, applies policy, or constructs context (INV-CH6-06, owned by the Experience fragment; noted here as the L6 boundary).
- **D-IMPL rulings embodied:** D-IMPL-30, D-IMPL-31, D-IMPL-39, D-IMPL-01, D-IMPL-05, D-IMPL-13.

### Component: SLO envelope, materialization, and cost discipline

- **Responsibility:** The illustrative SLO envelope (p99 300ms interactive; 2s async; 10K products/s/cluster; materialization ≤ N% compute; cache-hit ≥ M% within the λ_c window) is a calibration envelope, never shipped constants (INV-CH7-50). The Control Plane maintains a per-class materialization policy driven by half-life × access frequency, derivation cost envelope, and regulatory supersession triggers; the four-state cache lifecycle Fresh → Near-Expiry → (InvalidatedBySupersession | expiry) → Re-Derived is the coherency state machine (INV-CH7-51). Per-class cost bands (×1 / ×3–5 / ×2–4 / ×8–15) are illustrative calibration multiples (INV-CH7-53).
- **Invariants enforced:** No serving from cache past the λ_c window or after supersession without re-derivation; supersession transitions are Policy events from the Control Plane; cache hits are recorded in lineage (INV-CH7-51). Materialization policy is Control Plane configuration under the D-IMPL-38 discipline; the intermediate cache substrate is native (hot, mutable) per the D-IMPL-27 mutability split.
- **D-IMPL rulings embodied:** D-IMPL-27, D-IMPL-36, D-IMPL-38.

### Component: Algorithmic ⇄ Semantic Alternation and the three Assembly Modes

- **Responsibility:** Strict alternation of algorithmic and semantic stages: no semantic stage operates on raw signal; no algorithmic stage performs semantic interpretation; every pipeline transition crosses the boundary exactly once (INV-CH7-54; lifecycle-level statement INV-CH6-04; agent-side application in the Alternating Derivation Pipeline, INV-CH8-12, owned by the Core Agent Types fragment). CI enforcement: the `@algorithmic` import lint rejecting any LLM-client import in algorithmic modules (CLAUDE.md §11), with `LLMClientProtocol` per the D-IMPL-09 ruling as the single crisp import target.
- **Assembly Modes:** Mode 1 pure algorithmic; Mode 2 algorithmic assembly with LLM packaging (four pinned primitives: model version, temperature, prompt logged/hashed, output hash); Mode 3 algorithmic orchestration with agent-swarm assembly (INV-CH7-55, ninth contract element per D-IMPL-30). Trust-path purity holds across modes — the algorithmic substrate, never the probabilistic presentation, is the artifact-of-record; per-mode replay footprints and the five mixed-mode disciplines are carried into the replay design below (INV-CH7-56). Mode 3 cross-org assembly egresses at L6 over A2A (transport design in the Experience/seams fragment).
- **D-IMPL rulings embodied:** D-IMPL-09, D-IMPL-30.

---

## Context Half-life λ_c and Context Debt D_c

### Component: Half-life machinery

- **Responsibility:** Formal decay model `R(t) = R₀ × (1/2)^((t − t₀) / λ_c)` — probabilistic decision-relevance decay, not a binary fresh/expired check; re-observation resets the clock; discrete implementation as the sequential-window observer-buffer returning freshness-weighted composites (INV-CH7-57). λ_c is **Control Plane configuration per observation type, never code** (INV-CH7-58); the configuration surface shape is the (type, band, dominant decay driver, supersession event) row — the shape is the commitment, the numbers are domain values out of SDK scope (INV-CH7-59). λ_c is not a TTL: data past its λ_c remains accessible for historical reconstruction (replay depends on this) while not counting as current (INV-CH7-57).
- **Supersession:** a Policy event, not just time decay — logical supersession via `superseded_by`/`superseded_at`, versioned Control Plane invalidation events cascading through Data Plane cache coherency, lazy re-derivation, never eager (INV-CH7-60; graph-side append-only supersession is owned by `design-data-context-a.md`). Bitemporal enforcement at the mutation boundary makes the fabric a temporal abstraction layer over unaligned source cadences (INV-CH8-14): "real time" is a property of assembly at moment of use, not of the data.
- **D-IMPL rulings embodied:** D-IMPL-38 (λ_c tables as versioned parameter artifacts follow the same declared-schema, no-silent-default discipline).

### Component: Debt machinery and Conditional Assessment Routing

- **Responsibility:** `D_c = 1 − (C_available / C_required)` basic form (INV-CH7-61); extended multiplicative form `D_c = 1 − (F · C · S)` with freshness, completeness, and semantic-consistency factors composing conjunctively — any factor at zero drives D_c to 1 (INV-CH7-62). The multiplicative-conjunctive form is a defended architectural choice; the weighted-additive alternative is **rejected, not a tuning preference** (INV-CH7-63). Three runtime debt components roll up into F/C/S: data-source-availability-debt, as-of-time-staleness-debt, entity-resolution-confidence-debt — with failed-retrieval attempts recorded in lineage and the no-activity vs source-failure disambiguation architecturally required (INV-CH7-64).
- **Protocol/type signatures:** Per the **D-IMPL-47 ruling**, per-factor `DebtFactorScorer` Protocols with SDK reference computations (F from decay-ratio aggregation; C from declared-slot coverage; S from detected-contradiction rate), versioned `(scorer_id, scorer_version)` identity, class→scorer-version binding updatable via the Control Plane, per-class custom-scorer override through the same seam, and replay pinning of the scorer version in force. Trust Triangle leg strengths derive from the same three components (INV-CH7-66 debt-mapping), and the `TrustScorer`/`LegScorer` Protocol surface with conjunctive combinator per the D-IMPL-32 ruling ships with reference leg scorers derived from F/C/S — zero new measurement machinery.
- **Routing:** CAR consumes D_c, decision-class threat level, and relevant-signal count into the verbatim four-state predicate chain Skip / Conditional / Standard LLM / Forced LLM (INV-CH7-65 — owned by the Orchestration/HITL fragment for the escalation pathway; the D_c drive mechanism is designed here). Per the **D-IMPL-40 ruling** the threat-level scale (ordered enum with designated LOW-or-below band) and class-specific D_c thresholds in [0,1] are Control Plane configuration per decision class; the SDK ships only the routing mechanism. Governance-side restatement: bypass/conditional/forced-escalation pathways with the routing decision itself landing in the replay record (INV-CH8-16). Conservative bias and Fail-Closed under elevated D_c: debt is a risk amplifier; uncertainty is surfaced and routed into escalation, additional-source-fetch, or decision-decline, never smoothed (INV-CH7-67 — HITL wiring owned by the Orchestration/HITL fragment). Debt cascades across multi-agent handoffs with D_c recomputed at every handoff boundary against inherited plus new observations (INV-CH7-68 — handoff design owned by the Orchestration/HITL fragment). Agent-level fail-closed thresholds are specialization axis 5 (half-life and debt profile) per CLAUDE.md §6.2.
- **D-IMPL rulings embodied:** D-IMPL-32, D-IMPL-40, D-IMPL-47, D-IMPL-38.

---

## Decision Replay (Five Dimensions + SDK Extensions)

### Component: The replay record

- **Responsibility:** Every decision is forensically reconstructible years later against the exact fabric state at decision time — enforced at assembly time, at every Context Product boundary, and at the plane interface, never bolted on (INV-CH7-79). The five dimensions are inviolate (INV-CH7-80): (1) **Context Fabric Snapshot** — the touched `G(E, R, T, P, Π, L)` substate at t (INV-CH7-81); (2) **Policy Bindings Snapshot** — version identifiers + serialized parameters of all active policies (INV-CH7-82; HITL actions extend this dimension per CLAUDE.md §8.2 — HITL record design owned by the Orchestration/HITL fragment); (3) **Model Version Record** — every invoked model, "none"/"N/A" for Mode 1 (INV-CH7-83); (4) **Perspective Conditioning** — agent identity, role, tools, delegation chain (INV-CH7-84 — owned by the Core Agent Types fragment for the agent-version/skill-set extensions; the dimension contract is designed here); (5) **Content Generation Path** — input identifiers, reasoning trace, structured output (INV-CH7-85; workflow step sequences extend it per CLAUDE.md §8.1).
- **Environment replay, not model trace:** CCF reconstructs the decision environment; the model's internal trace belongs to external tooling. The composition seam is the `TraceCorrelationHook` on dimension 5 at the harness adapter's replay-hooks seam, storing a typed external trace reference per LLM invocation, per the D-IMPL-45 ruling (INV-CH7-86 — seam design owned by the Experience/seams fragment).
- **Passage-level lineage:** every unstructured-derived claim carries passage-level L anchors; the Evidence Chain (claim → passage-level L → citation reference → WORM source passage) is reconstructible in reverse at audit time; the provider is pluggable via the `PassageCitationProvider` Protocol per the D-IMPL-46 ruling — Anthropic Citations adapter plus deterministic post-hoc span-matcher as reference impls (INV-CH7-87).
- **Per-mode footprints:** Modes extend, never modify, the five-dimension baseline; Mode 2 adds the four pinned LLM-rendering primitives; Mode 3 adds orchestration plan id, per-agent version manifest, and contribution boundary markers with recursive per-agent records; replay is mode-invariant on one record format (INV-CH7-88 — Mode 3 record composition shared with the Orchestration/HITL fragment). The AML SAR triage worked example is the canonical end-to-end composition (INV-CH7-90). Replay renderings for three audiences are three Π projections of one record — the §7.5 primitive recursively applied, never three records (INV-CH7-91 — rendering surface owned by the Experience fragment).

### Component: Snapshot strategy and artifact resolution — exact versions, never "latest"

- **Responsibility:** Per the **D-IMPL-06 ruling**, snapshots are **logical by construction**: `graph_snapshot_id` = temporal boundary + tenant + store-state watermark, plus the touched-substate manifest already enumerated by lineage strict equality — never a physical graph copy. The full-fidelity tier additionally materializes the touched substate as a content-addressed ArtifactStore artifact; similarity-index snapshots are the version pinned in L with version-pinned reads a `SimilarityIndex` Protocol obligation (D-IMPL-03).
- **Addressing:** per the **D-IMPL-26 ruling**, hybrid: content-addressed canonical identity `sha256(canonical_serialization)` plus versioned-URI naming `ccf-artifact://{tenant}/{artifact_class}/{name}@{artifact_version}` through an append-only Control Plane mapping. **`@latest` is permitted only at authoring surfaces — a replay record or lineage entry never stores "latest"; it stores the hash** (URI carried as annotation). Replay resolution therefore resolves exact artifact versions by hash: graph snapshot, policy bundle version, agent version, skill-set, prompt-artifact versions — the seq-replay-resolution diagram renders this sequence.
- **Substrate split:** per the **D-IMPL-27 ruling**, immutable replay-relevant artifacts route through the ArtifactStore; hot mutable state stays on native Protocols. **Determinism-obligation note (INV-CH7-80/89 dependency):** the ArtifactStore seam design (owned by the Experience/seams fragment) must preserve replay determinism per D-IMPL-26.
- **Lifecycle:** per the **D-IMPL-50 ruling** the SDK ships the fidelity-lifecycle engine above the ArtifactStore Protocol: three-tier compression (Full fidelity / Compressed / Tombstoned), the never-compress/never-tombstone severity exemption enforced in mechanism, and the structural `retention-reason` field on every transition (INV-CH7-89); retention windows, severity thresholds, and tombstone minima are Control Plane values. Governance-side statement of the same lifecycle with the WORM-archives-remain-records-of-record constraint: INV-CH8-20 (replay-anchor retention lifecycle at scale). Regulatory regime → artifact mapping is discharged by these primitives; specific regime bundles are user policy configuration, not SDK content (INV-CH8-15).
- **Cold-archive re-hydration:** per the **D-IMPL-44 ruling**, every compressed record carries a typed `ReHydrationRecipe`; re-hydration re-runs L2 assembly against archived source signals under pinned Control Plane versions and verifies bit-for-bit against the stored hash — or fails loudly; `ColdSourceArchiveProtocol` is the pluggable archive seam with a file-backed dev impl.
- **D-IMPL rulings embodied:** D-IMPL-06, D-IMPL-26, D-IMPL-27, D-IMPL-44, D-IMPL-50, D-IMPL-03.

---

## Closed-Loop Self-Learning

- **Responsibility:** "The loop is in the graph, not the model." Closed-loop learning flows exclusively through the Control Plane as logical graph write-back — never direct runtime modification of operators/projection/policy, never model retraining (INV-CH7-75). Three-stage pattern: typed `OutcomeSignal` (with provenance, `observed_at`, its own λ_c) → Control Plane interpretation → versioned update → Data Plane propagation with `projection_plan_id` + `contract_version` attribution so historical decisions re-trace against the version in force when made.
- **Signal taxonomy:** per the **D-IMPL-42 ruling** the prose taxonomy is canonical — typed enum `OUTCOME | CONTEXT_VALIDITY | AUDIT_LINEAGE` — with the Fig-CH07-24 handler names (Outcome/Correction/Metadata) documented as dispatch-side aliases in an alias table (INV-CH7-76). One-event-one-handler routing; structurally distinct graph-write targets per category; no gradient descent, no weight update.
- **Refinement targets:** exactly four Control-Plane-owned targets — operator refinement, projection optimization, policy calibration, half-life adjustment (INV-CH7-77). Agents appear to improve because the context they consume improves.
- **Governance:** per the **D-IMPL-43 ruling** the interpretation step is configurable per learning-signal class, **defaulting to human-gated** (workflow with an ApprovalGate; Control Plane policy may configure specific signal-class × parameter-class × bounded-delta combinations as auto-applied under tier-1 bounds validation per D-IMPL-38). Every update — gated or auto — is a versioned Control Plane action in the audit plane; learning runs through the same governance regime (versioning, approval, staged propagation, rollback) as initial configuration — no separate learning regime (INV-CH7-78). ApprovalGate mechanics are owned by the Orchestration/HITL fragment.
- **D-IMPL rulings embodied:** D-IMPL-42, D-IMPL-43, D-IMPL-38.

---

## Cross-Cutting: Control Plane / Data Plane

- **Responsibility:** Structural separation: the Control Plane defines what the fabric may do (policies, operator parameters, projection rules and entitlements, per-class D_c thresholds, per-type λ_c, materialization policy); the Data Plane executes against those definitions under controlled handoff (INV-CH7-70). **The Control Plane is also the audit plane**: every operator invocation, projection computation, and product assembly is observable for replay as a first-class property; every configuration change is versioned, timestamped, and retained against the decisions made under it; invalidation flows as published events, never direct side-effects (INV-CH7-71 — this audit plane is also what backs HITL audit-by-construction, designed in the Orchestration/HITL fragment).
- **Configuration surface:** the six whitepaper classes — policy definitions, operator behavior rules, projection logic, D_c thresholds, λ_c tables, materialization policy (INV-CH7-72) — **plus the SDK-defined artifact classes**: agent definitions, task definitions, prompt artifacts, skill catalog entries and grants, workflow definitions, HITL policies, A2A trust policy (CLAUDE.md §7.4/§10; formats per the D-IMPL-28 ruling, marked as SDK extensions). In the v0 design the Control Plane is an in-process versioned registry with a remote extension point (CLAUDE.md §13); all parameter classes follow the D-IMPL-38 declared-schema, versioned, no-silent-default discipline; closed-loop updates enter through the D-IMPL-43 gated interpretation path.
- **Invariants enforced (plane-boundary register, INV-CH7-73):** (a) single-writer for graph state — realized by the D-IMPL-41 four-layer enforcement stack (reader/writer Protocol split per D-IMPL-34, DI at boot, mypy + import lint CI gate, boot-token runtime backstop), with the honest residual claim ("no unforced path exists and every forced path fails CI or fails at boot") recorded for the Invariant Preservation chapter — full write-path design owned by `design-data-context-a.md`; (b) projection stateless; (c) lineage strict equality at the stage-3a gate; (d) TTL bounds at stage-3b with MAX_TTL per D-IMPL-39; (e) tenant-scoped kw-only `tenant_id` on every execute call per the D-IMPL-05 ruling. Data Plane determinism — bit-for-bit identity under fixed (graph state, config, temporal boundary), randomness isolated at reproducible boundaries — is the foundation replay stands on (INV-CH7-74). Auditability-at-scale for agentic work rests on the same plane properties (INV-CH8-20).
- **D-IMPL rulings embodied:** D-IMPL-05, D-IMPL-28, D-IMPL-34, D-IMPL-38, D-IMPL-41, D-IMPL-43.

---

## Coverage Notes

**Deferred entries:** none. Every entry owned by this fragment is designed above; entries where this fragment is See-also (INV-CH6-07, INV-CH7-32, INV-CH7-55/56 mode-3 orchestration side, INV-CH7-65/67/68 escalation side, INV-CH7-71 HITL audit backing, INV-CH7-72 agent-artifact classes, INV-CH7-75 human-gated interpretation, INV-CH7-80/82/84/86/88/89/91 extension-owning fragments, INV-CH8-07/12/16 and INV-CH7-06/11/13 boundary restatements) are cross-referenced at their design point above with the owning fragment named.

**PROVISIONAL bases:** none — every D-IMPL ruling embodied in this fragment is RESOLVED with Dave as approver (docs/DECISIONS.md, 2026-07-25). D-IMPL-10 (provisionally resolved, repo shape) is not load-bearing for this fragment.

**Phase-boundary note:** contract altitude only; no implementation code appears in this fragment. Type signatures quoted are the whitepaper's/rulings' committed contracts, not implementations.

### Owned-entry → design-section index

Input for synthesis (plan 02-10, Appendix A). One row per owned entry; See-also entries indexed separately above.

| INV key | Designed in section | Disposition |
|---------|---------------------|-------------|
| INV-CH6-01 | L6 — ContextProductContract | mapped |
| INV-CH6-02 | L6 — ContextProductContract | mapped |
| INV-CH6-03 | L6 — ContextProductContract (nine elements per D-IMPL-30) | mapped |
| INV-CH6-04 | L6 — Alternation component; TTL derivation per D-IMPL-31 | mapped |
| INV-CH7-22 | L4 — Operator algebra | mapped |
| INV-CH7-23 | L4 — Operator algebra (composition-preservation) | mapped |
| INV-CH7-24 | L4 — Operator algebra (Traversal) | mapped |
| INV-CH7-25 | L4 — Operator algebra (Temporal) | mapped |
| INV-CH7-26 | L4 — Operator algebra (Policy-before-Similarity) | mapped |
| INV-CH7-27 | L4 — Operator algebra (Similarity determinism contract) | mapped |
| INV-CH7-28 | L4 — Planner and registry | mapped |
| INV-CH7-29 | L4 — Planner and registry (fail-fast boot registry) | mapped |
| INV-CH7-30 | L4 — Operator algebra (worked compositions, values illustrative) | mapped |
| INV-CH7-31 | L4 — Operator algebra (function-determinism) | mapped |
| INV-CH7-33 | L4 — Planner and registry (end-to-end sequence) | mapped |
| INV-CH7-40 | L5 — Projection (substitution, not filtering) | mapped |
| INV-CH7-41 | L5 — Projection (`required_operators()` + `invoke()`) | mapped |
| INV-CH7-42 | L5 — Projection (two-stage execution) | mapped |
| INV-CH7-43 | L5 — Projection (runtime conditioning) | mapped |
| INV-CH7-44 | L5 — Projection (Contract as stability layer) | mapped |
| INV-CH7-45 | L6 — ContextProductContract (seven-field `extra=forbid` base) | mapped |
| INV-CH7-46 | L6 — validation gate 1: empty-operator guard | mapped |
| INV-CH7-47 | L6 — validation gate 2: lineage strict equality | mapped |
| INV-CH7-48 | L6 — validation gate 3: TTL bounds (MAX_TTL per D-IMPL-39) | mapped |
| INV-CH7-49 | L6 — ContextProductContract (independent semver lanes) | mapped |
| INV-CH7-50 | L6 — SLO envelope (illustrative, never constants) | mapped |
| INV-CH7-51 | L6 — materialization and cache coherency state machine | mapped |
| INV-CH7-52 | L6 — derivation paths and three-gate sequence | mapped |
| INV-CH7-53 | L6 — cost bands (illustrative multiples) | mapped |
| INV-CH7-54 | L6 — Algorithmic ⇄ Semantic Alternation | mapped |
| INV-CH7-57 | Half-life machinery (decay model) | mapped |
| INV-CH7-58 | Half-life machinery (λ_c Control Plane config, never code) | mapped |
| INV-CH7-59 | Half-life machinery (config surface shape) | mapped |
| INV-CH7-60 | Half-life machinery (supersession as Policy event) | mapped |
| INV-CH7-61 | Debt machinery (basic D_c form) | mapped |
| INV-CH7-62 | Debt machinery (extended multiplicative form) | mapped |
| INV-CH7-63 | Debt machinery (multiplicative-conjunctive, additive rejected) | mapped |
| INV-CH7-64 | Debt machinery (three runtime components) | mapped |
| INV-CH7-66 | Debt machinery (Trust Triangle debt-mapping, D-IMPL-32) | mapped |
| INV-CH7-70 | Control Plane / Data Plane (separation) | mapped |
| INV-CH7-71 | Control Plane / Data Plane (control plane is audit plane) | mapped |
| INV-CH7-72 | Control Plane / Data Plane (config surface + SDK classes) | mapped |
| INV-CH7-73 | Control Plane / Data Plane (five-invariant register, D-IMPL-41) | mapped |
| INV-CH7-74 | Control Plane / Data Plane (Data Plane determinism) | mapped |
| INV-CH7-75 | Closed-Loop Self-Learning (write-back through Control Plane) | mapped |
| INV-CH7-76 | Closed-Loop Self-Learning (signal taxonomy per D-IMPL-42) | mapped |
| INV-CH7-77 | Closed-Loop Self-Learning (four refinement targets) | mapped |
| INV-CH7-78 | Closed-Loop Self-Learning (learning as governance) | mapped |
| INV-CH7-79 | Decision Replay (first-class commitment) | mapped |
| INV-CH7-80 | Decision Replay (five-dimension record) | mapped |
| INV-CH7-81 | Decision Replay (dimension 1, logical snapshots per D-IMPL-06) | mapped |
| INV-CH7-83 | Decision Replay (dimension 3) | mapped |
| INV-CH7-85 | Decision Replay (dimension 5) | mapped |
| INV-CH7-87 | Decision Replay (passage-level lineage, D-IMPL-46) | mapped |
| INV-CH7-89 | Decision Replay (three-tier compression, D-IMPL-50/44) | mapped |
| INV-CH7-90 | Decision Replay (AML SAR worked example, composition anchor) | mapped |
| INV-CH8-14 | Half-life machinery (temporal abstraction layer) | mapped |
| INV-CH8-15 | Decision Replay (regime → artifact mapping; bundles are values) | mapped |
| INV-CH8-17 | L4 — Operator algebra (Policy-before-Similarity, governance side) | mapped |
| INV-CH8-20 | Decision Replay (auditability at scale, lifecycle) | mapped |

61 owned rows — matches the entry-ownership census for `design-data-context-b.md`.
