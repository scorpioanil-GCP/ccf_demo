# Inventory Fragment — Whitepaper Ch 7 (§7.5–§7.7)

**Canonical authority:** `docs/CCF_Whitepaper_1-2.md`. All citations reference `.md` sections, never the PDF (locked D-01). Key block: INV-CH7-40 through INV-CH7-69 (plan 01-06 owns 01–39; plan 01-08 starts at 70). Extraction gate: `fragments/spotcheck-report.md` records `VERDICT: PASS`.

---

## §7.5 — Context Projection (Π), System of Interpretation

### INV-CH7-40 — Π performs subgraph substitution, not subgraph filtering

**Section:** §7.5 (incl. §7.5.6)
**Commitment:** Π is a typed transformation, not an RBAC filter: its output is itself a valid Context Graph for the principal — a substructure, not a filtered result set. The fabric commits to "construct once, interpret many": one underlying Context Graph is the shared representation of truth; many projections produce role-shaped views at decision time. Four distinctions from RBAC are committed: (i) enforcement at the graph formalism itself (inadmissible parts are not in the projected Graph's scope, nothing downstream to filter); (ii) safe composition with operators (no leak-by-absence — operators compose against Π's output as if it were the full Graph, because for that principal it IS the full Graph); (iii) decision-time parameterization by the tuple (principal, time, policy regime, jurisdiction), not principal-only; (iv) auditability — every Context Product carries its Projection as first-class Lineage metadata (plan_id, operators_invoked, policy_version, graph_snapshot_at), producing a trail of how meaning was constructed, not just who touched data. §7.5.6 sharpens the same commitment against the Knowledge Catalog "Perspectives" foil: Perspectives filters a single canonical view; Π constructs different typed graphs per principal, and the typed structure determines which operators can compose over it.
**Type signature:** none given (mechanism carried by ProjectionPlan, INV-CH7-41)
**Invariants:** Output of Π is a valid Context Graph composable with the operator algebra; no data hidden across role views — meaning is constructed by substitution, never by removal; every projection's lineage lands in the Contract.
**Dependencies:** Context Graph (§7.3 entries, plan 01-06), operator algebra (§7.4 entries, plan 01-06), Context Product Contract (INV-CH7-45)
**Figures:** Fig-CH07-11, Fig-CH07-12
**Open question:** none

### INV-CH7-41 — ProjectionPlan as two-method structural interface

**Section:** §7.5.1
**Commitment:** Π is realized by the ProjectionPlan — a language-neutral structural interface dispatched via structural typing, never class inheritance. Any type exposing the two declared methods qualifies: `required_operators()` declares which operators the projection depends on before invocation; `invoke()` executes the typed transformation against the operator-composed subgraph and returns the typed Context Product. The engine resolves `required_operators()` first (batch-resolving via the §7.4 Operator Plan DAG generator), then invokes with resolved operator outputs bound in. Registration is import-time structural introspection; runtime dispatch is a keyed lookup. Rationale committed: projections share no useful common base behavior (narrative vs temporal-correlation vs branching-rule styles), so the shape is the contract; testability improves because a plain structural match substitutes in tests with no mocking framework.
**Type signature:** `required_operators()` + `invoke()`; every registered projection returns a typed ContextProductContract subclass
**Invariants:** Structural typing, not inheritance — no base class, no runtime-registered inheritance chain, no type-name resolution; every projection's return value is wrapped under the Contract the Control Plane maintains for that projection.
**Dependencies:** Operator Plan DAG generator (§7.4, plan 01-06), ContextProductContract (INV-CH7-45)
**Figures:** Fig-CH07-12
**Open question:** none

### INV-CH7-42 — Two-stage execution model: Operator Plan then Projection Plan

**Section:** §7.5.2
**Commitment:** Projection layers on operator execution as a second-stage plan: the Operator Plan answers "what is true"; the Projection Plan answers "what that truth means in this decision context." Separation is structural — operators are principal-agnostic (same computation regardless of requester, enabling memoization of intermediates); projections are principal-conditioned (shaped by role, intent, temporal context, policy regime) and know nothing about how the graph was traversed. Coupling is tight in execution via operator-produced metadata: the operator plan carries which traversal paths were walked, which temporal constraints applied, which policy filters enforced, which similarity expansions occurred (threshold + index version), and the Projection Plan reads this metadata during invocation. Combining the concerns is named a failure: operators-as-projections yields rigid precomputed views; projections-as-operators pushes interpretation into agent code, fragmenting auditability.
**Type signature:** none given
**Invariants:** Neither concern leaks into the other; operator memoization guarantee (same operators + same state → same output) depends on principal-agnosticism.
**Dependencies:** INV-CH7-41; §7.4 operator plan metadata (plan 01-06)
**Figures:** none
**Open question:** none

### INV-CH7-43 — Role-shaped views and runtime conditioning

**Section:** §7.5.3–§7.5.4
**Commitment:** The same underlying resolved context projected under different Π yields structurally different Context Products with zero duplication of state (three-principal credit-memo example: credit-officer, compliance-officer, credit-risk-officer views differ in which axes are primary/subordinated/expanded/compressed — no data hidden, meaning constructed differently; the operator chain executes once and all projections dispatch against the same memoized intermediate). Projection runs dynamically at runtime, conditioned by the tuple (role, intent, temporal context, policy). Runtime conditioning is committed as the mechanism avoiding two named failure modes: precompute-everything (combinatorial explosion of role × decision-class × time-horizon × policy-regime views) and resolve-at-read-time (interpretation leaks into agent code, audit fragments per-agent).
**Type signature:** none given
**Invariants:** Projection resolved at request time against current graph state and current Control Plane config; no interpretive logic in agent code; cost bounded by memoizable operator intermediates.
**Dependencies:** INV-CH7-41, INV-CH7-42; Entitlement Service / role-to-intent-to-plan lookup (Fig-CH07-12)
**Figures:** Fig-CH07-12
**Open question:** none

### INV-CH7-44 — Context Product Contract as output stability layer

**Section:** §7.5.5
**Commitment:** Π produces a Context Product Contract as its output surface. The Contract decouples agent consumers from internal evolution: an operator can be re-implemented, a graph class extended, a policy versioned — and the Contract's surface to the agent stays stable, because the Contract declares the output shape in typed terms the agent binds to while the evolution lives behind the Contract boundary. §7.5 names Π as the producer of Contracts; §7.6 commits the Contract mechanism itself.
**Type signature:** none given (base committed at INV-CH7-45)
**Invariants:** Contract surface stability across operator/graph/policy evolution.
**Dependencies:** INV-CH7-45 (Contract base), §6.3 eight-element specification (plan 01-05, INV-CH6 entries)
**Figures:** none
**Open question:** none

---

## §7.6 — Context Products, System of Delivery

### INV-CH7-45 — ContextProductContract base specification with extra=forbid

**Section:** §7.6.1
**Commitment:** The fabric commits to a typed base every projection returns, carrying seven contract fields (matching the Fig-CH07-13 Context Product Spec sidebar): `schema_name` (class-level constant, stable per product — downstream discovery/subscription indexes against it, hence a classvar not an instance field), `schema_version` (semver of the Contract schema: MAJOR breaking / MINOR additive / PATCH clarification), `plan_id` (identifies the ProjectionPlan — including its version — that produced the product, connecting the Contract to the exact projection for forensic reconstruction), `expires_at` (datetime TTL boundary; Contracts past it must not be served from cache without re-derivation, enforced at read time), `ttl_anchor` (enum `from_decision` | `from_entity_freshness` — the two anchors carry different semantics and getting the anchor wrong breaks cache coherency in either direction), `lineage` (`operators_invoked` as typed operator references, `policy_version` at composition time, `graph_snapshot_at` — together the audit trail replay requires to reproduce the product bit-for-bit), and `payload` (per-product typed; each subclass declares its own payload schema). The base has `extra=forbid` as a structural-validation discipline blocking Contract drift; CI enforces `extra=forbid` as a build-time invariant.
**Type signature:** `extra=forbid` typed base; fields: schema_name (classvar), schema_version (semver), plan_id, expires_at (datetime), ttl_anchor ∈ {from_decision, from_entity_freshness}, lineage {operators_invoked, policy_version, graph_snapshot_at}, payload (per-product typed)
**Invariants:** `extra=forbid` on the base and at the cache-write boundary; per-product subclasses extend payload without contaminating the base; cross-cutting invariants validated once on the base, applied everywhere; CI fails a PR introducing a drifted Contract.
**Dependencies:** §6.3 eight-element specification (plan 01-05); INV-CH7-41 (plan_id ↔ ProjectionPlan identity); §7.10 replay (plan 01-08)
**Figures:** Fig-CH07-13
**Open question:** none

### INV-CH7-46 — Validation gate 1: empty-operator guard

**Section:** §7.6.1, §7.6.4
**Commitment:** The first of three sequential validation gates in the projection execution engine. The empty-operator guard rejects a Contract whose `operators_invoked` is empty — a projection must have resolved at least one operator to have meaningfully read the graph; an empty set indicates a misconfigured projection, not a trivially-successful one. In the Fig-CH07-16 gate sequence this concern is checked by the Schema Validator layer alongside base-field presence.
**Type signature:** none given
**Invariants:** Gate condition: `operators_invoked ≠ ∅`; refusal is a structured rejection returned to the agent, never silent acceptance; no invalid product reaches an agent, enters the cache, or contaminates the Decision Replay record.
**Dependencies:** INV-CH7-45; INV-CH7-52 (gate sequence)
**Figures:** Fig-CH07-16
**Open question:** none

### INV-CH7-47 — Validation gate 2: lineage strict equality

**Section:** §7.6.1, §7.6.4
**Commitment:** The second validation gate. Lineage strict equality rejects a Contract whose declared `operators_invoked` does not match the set of operators the engine actually resolved — forgery, omission, or accidental drift all fail at the gate. The Fig-CH07-16 Lineage Completeness Checker additionally verifies that passage-level anchors exist for every claim derived from unstructured sources.
**Type signature:** none given
**Invariants:** Gate condition: declared `operators_invoked` set == engine-resolved operator set (strict equality); passage-level anchors present for every unstructured-derived claim.
**Dependencies:** INV-CH7-45; §7.4 operator plan (plan 01-06); passage-level lineage (§7.10.3, plan 01-08)
**Figures:** Fig-CH07-16
**Open question:** none

### INV-CH7-48 — Validation gate 3: TTL bounds

**Section:** §7.6.1, §7.6.4
**Commitment:** The third validation gate. TTL bounds rejects a Contract whose `expires_at` is in the past or beyond a MAX_TTL envelope — expired-on-arrival and impossibly-long-lived Contracts are both invariant violations. The cache write re-verifies `extra=forbid` and TTL bounds within MAX_TTL at the cache boundary after all three gates pass.
**Type signature:** none given
**Invariants:** Gate condition: `now < expires_at ≤ now + MAX_TTL`; re-verified at cache-write time.
**Dependencies:** INV-CH7-45 (expires_at, ttl_anchor); INV-CH7-51 (cache coherency)
**Figures:** Fig-CH07-16
**Open question:** "TTL bounds rejects a Contract whose expires_at is in the past or beyond a MAX_TTL envelope" — the whitepaper never specifies where MAX_TTL is configured or its default. Readings: (a) MAX_TTL is a Control Plane configuration per Context Product class (consistent with §7.8's configuration posture; consequence: SDK ships mechanism, users supply values); (b) MAX_TTL is a single fabric-wide constant (simpler, but a hard-coded threshold would collide with the mechanism/values boundary); (c) MAX_TTL derives from the product's λ_c band (elegant but nowhere stated). Left unnumbered for synthesis.

### INV-CH7-49 — Per-product independent semver lanes

**Section:** §7.6.1
**Commitment:** Per-product semver evolution independence: a version bump on one product's Contract (e.g., CounterpartyCreditRiskContract v2.1.0 → v2.2.0 adding a payload field) does not touch any other product's Contract — each product class evolves on its own cadence with no cross-product blast radius. This is the stability property making Contract evolution tractable across an enterprise with dozens of product classes.
**Type signature:** semver per Contract subclass (MAJOR/MINOR/PATCH per standard discipline)
**Invariants:** Version lanes are independent per product class.
**Dependencies:** INV-CH7-45
**Figures:** none
**Open question:** none

### INV-CH7-50 — Illustrative SLO envelope

**Section:** §7.6.2
**Commitment:** The fabric commits to an illustrative SLO envelope — explicitly envelope, not vendor benchmarks; production calibration against decision-class workload patterns is required. Five targets: (1) p99 300ms for interactive Context Products; (2) 2s for asynchronous Context Products; (3) 10K Context Products per second per cluster steady-state throughput, scaling horizontally across clusters; (4) materialization budget band ≤ N% of cluster compute capacity; (5) cache-hit target band ≥ M% at steady state within the λ_c window. The envelope is the mechanism-level answer to Rebuttal #3 ("derived-at-runtime is expensive"): cost is not free but bounded by a specific envelope.
**Type signature:** none given (numeric targets as above)
**Invariants:** The numbers are illustrative calibration targets, never shipped as constants — production must reconcile against observed workload.
**Dependencies:** INV-CH7-51 (materialization policy consumes bands 4–5); λ_c (INV-CH7-57)
**Figures:** none
**Open question:** none

### INV-CH7-51 — Materialization policy and cache coherency state machine

**Section:** §7.6.3
**Commitment:** The Control Plane maintains a materialization policy per Context Product class deciding which Contracts are pre-computed and which derive on demand, driven by three signals: (1) Half-life × access frequency (materialize when pre-computing once per λ_c window amortizes across many reads); (2) derivation cost envelope (per-class cost bands, INV-CH7-53); (3) regulatory supersession triggers (source-entity state changes cascade invalidation across the dependency chain — a superseded entity invalidates every Context Product whose operators_invoked touched it, not only Contracts named for it directly). Cache coherency semantics: materialized products within their λ_c window are reused without re-derivation with the cache-hit recorded in request lineage; supersession events evict; invalidation cascades downstream. Fig-CH07-14 commits the four-state lifecycle: Fresh → Near-Expiry → (InvalidatedBySupersession | expiry) → Re-Derived → Fresh; every materialized product occupies exactly one state at any time.
**Type signature:** none given
**Invariants:** No serving from cache past λ_c window or after supersession without re-derivation; supersession transitions are Policy events from the Control Plane, not time-decay events; cache hits are recorded in lineage.
**Dependencies:** λ_c (INV-CH7-57), supersession-as-Policy-event (INV-CH7-60), Control Plane (§7.8, plan 01-08)
**Figures:** Fig-CH07-14
**Open question:** none

### INV-CH7-52 — Derivation paths and three-gate validation sequence

**Section:** §7.6.4
**Commitment:** Two runtime interaction commitments. (1) Derivation paths: on every request the Product Cache performs a keyed lookup against the composite identity making a product instance unique — tenant, schema name, ProjectionPlan identifier, graph snapshot identifier, principal binding. Cache-hit: serve within the λ_c window, record hit in lineage, resolve inside the p99 300ms envelope. Cache-miss: Materialization Engine invokes the operator composition, reads the graph under policy projection, applies Π, populates the Contract; a conditional cache write follows only if the three-signal materialization decision justifies it (one-off products are not necessarily cached). (2) Contract validation: three sequential gates before any product is written to cache or delivered — Schema Validator (seven base fields present, extra=forbid not violated), Policy Gate (the policy binding recorded in the Contract matches the Control Plane's active policy at assembly time; a mismatched policy version is structurally inadmissible), Lineage Completeness Checker (strict equality of operators_invoked plus passage-level anchor verification). Three refusal branches return structured rejections; cache write occurs only if all three gates pass.
**Type signature:** composite cache key: (tenant, schema_name, plan_id, graph_snapshot_id, principal binding)
**Invariants:** No invalid Context Product reaches an agent, enters the cache, or contaminates the Decision Replay record; gates fail fast, keeping assembly cost bounded per-class; conditional-write discipline keeps the cache free of never-re-requested products.
**Dependencies:** INV-CH7-45..48, INV-CH7-51; Fig-CH07-10 end-to-end trace (§7.4, plan 01-06)
**Figures:** Fig-CH07-15, Fig-CH07-16
**Open question:** none

### INV-CH7-53 — Per-Context-Product-class cost envelope

**Section:** §7.6.5
**Commitment:** Four illustrative cost multiple bands relative to baseline (absolute dollars vary per deployment): materialized-structured-only × 1 baseline; materialized-unstructured-heavy × 3–5 (embedding-index maintenance + retrieval-against-index overhead); derived-on-demand-structured × 2–4 (bounded low by operator memoization, high by worst-case composition depth against cold caches); derived-on-demand-unstructured × 8–15 (the most expensive quadrant, most aggressively targeted for pre-computation by the materialization policy). The bands are a calibration tool: the Control Plane decides materialization per class by where the class lives in the matrix; the CAR routing pattern (§7.7) bounds which cache-miss requests exercise the expensive LLM path.
**Type signature:** cost bands: ×1 / ×3–5 / ×2–4 / ×8–15 (illustrative)
**Invariants:** Bands are illustrative multiples, never absolute constants in code.
**Dependencies:** INV-CH7-51 (signal 2), INV-CH7-65 (CAR)
**Figures:** none
**Open question:** none

### INV-CH7-54 — Algorithmic ⇄ Semantic Alternation as architectural primitive

**Section:** §7.6.6
**Commitment:** Every Context Product composition respects strict alternation of algorithmic and semantic stages. Algorithmic stages perform deterministic computation without LLM inference (graph traversal, temporal reconciliation, policy subgraph substitution, similarity-over-pinned-index ranking, contract-shaped structuring); semantic stages (assessment, reasoning, narrative production) receive as sole input the output of the immediately preceding algorithmic stage. Two invariants flow from the alternation: (1) no semantic stage operates on raw signals — every LLM invocation receives the pre-resolved typed substrate an algorithmic stage produced, never unprocessed feed; (2) no algorithmic stage performs semantic interpretation. Every pipeline transition crosses the algorithmic/semantic boundary exactly once — strict alternation, not undisciplined interleave. Stage pattern verbatim: Signals → Algorithmic-Assembly → LLM-Assessment → Algorithmic-Structuring → LLM-Reasoning → Algorithmic-Action-Structuring → Agent Action. Consequences committed: replay determinism (§7.10 rests on it — algorithmic stages replay bit-for-bit, semantic stages receive identical structured inputs) and cost boundedness (the expensive LLM invocation runs on reduced substrate only). Reference-implementation grounding: the discipline is a structural invariant the CI suite validates against attempted bypasses, not a code-review convention.
**Type signature:** stage sequence as quoted above
**Invariants:** No LLM sees raw signal; no algorithmic stage constructs meaning; strict alternation; CI-enforced structural invariant.
**Dependencies:** §6.4 lifecycle-pattern introduction (plan 01-05); §7.10 replay determinism and §7.9 closed-loop write-back (plan 01-08); SDK enforcement hook: CLAUDE.md §11 commits a CI lint rejecting any LLM-client import in modules tagged `@algorithmic` — the SDK realization of this whitepaper invariant
**Figures:** none (pseudocode block in-text)
**Open question:** none

### INV-CH7-55 — Three Assembly Modes: cost vs quality vs determinism

**Section:** §7.6.7
**Commitment:** Three Assembly Modes exhaust the delivery-layer choice space, selected per Context Product via the ninth contract element (§6.3): Mode 1 pure algorithmic assembly (no LLM anywhere; lowest cost, highest determinism, lowest narrative quality; exemplar: AML alert triage routing); Mode 2 algorithmic assembly with LLM packaging (LLM at the presentation layer only over the dimensionally-reduced algorithmic substrate; substrate stays artifact-of-record and bit-for-bit replayable; presentation is replay-deterministic under pinned model version, pinned temperature, logged prompt; exemplar: credit-memo narrative packaging); Mode 3 algorithmic orchestration with agent-swarm assembly (coordinator dispatches agents across federated trust boundaries; each emits typed contributions against contracts the coordinator verifies and reconciles; highest cost — ~15× single-agent baseline, industry-reported; exemplar: syndicated-lending covenant cross-reference over A2A/Pattern 4). Trust-path purity holds across modes: the algorithmic substrate, never the probabilistic presentation, is what the Decision Replay record commits to. Determinism discipline: "Determinism is a property of the function, not the value."
**Type signature:** Mode ∈ {1: pure-algorithmic, 2: algorithmic+LLM-packaging, 3: algorithmic-orchestration+agent-swarm}; per-product configuration at product-class registration
**Invariants:** Trust-path purity invariant under mode selection; mode selection is a registration-time configuration decision, not an emergent runtime property.
**Dependencies:** INV-CH7-54 (alternation primitive the modes select against); §6.3 ninth element (plan 01-05); A2A federation Pattern 4 (§8.3, plan 01-09)
**Figures:** none
**Open question:** none

### INV-CH7-56 — Per-mode replay footprint and five mixed-mode disciplines

**Section:** §7.6.8–§7.6.9
**Commitment:** Each mode commits a replay footprint the §7.10 record must carry. Mode 1: trivial — the typed product is exactly the algorithmic substrate; model version dimension is "none"/"N/A". Mode 2: derivative-view discipline — substrate bit-for-bit replayable; the LLM presentation replays only under four pinned primitives (model version pinned, temperature pinned, full prompt logged or hashed, LLM-output hash captured for bitwise verification). Mode 3: determinism boundary moves to the orchestration layer — mode selection, typed contributions, and reconciliation are replay-deterministic; the record adds orchestration plan ID, per-agent-version manifest, and per-agent contribution boundary markers, with per-agent contributions recursively replayed by their own modes. Five disciplines govern mixed-mode assembly: (1) artifact-of-record (examiner re-traces against the substrate hash, never the LLM narrative); (2) model-version + temperature + full-prompt pinning (forced by e.g. the 31 CFR §1020.320 five-year SAR retention obligation); (3) smoothing-failure-mode watchpoint (LLMs may reconcile conflicts the substrate deliberately surfaced — formally defended at §7.7.5); (4) cost economics internalized at registration time; (5) failure-mode inventory consulted at mode-selection registration and model-validation audit.
**Type signature:** Mode 2 replay primitives: {model_version, temperature, prompt (logged|hashed), output_hash}; Mode 3 additions: {orchestration_plan_id, per_agent_version_manifest, contribution_boundary_markers}
**Invariants:** Artifact-of-record is always the algorithmic substrate; every HITL-relevant/examiner-facing reconstruction anchors on substrate hash; no unpinned Mode 2 narrative counts as replayable.
**Dependencies:** INV-CH7-55; §7.10 "Replay Across Assembly Modes" (plan 01-08); INV-CH7-63 (multiplicative-conjunctive defense of discipline 3)
**Figures:** none
**Open question:** none

---

## §7.7 — Context Debt and Context Half-life

### INV-CH7-57 — Context Half-life λ_c formal decay model

**Section:** §7.7.1
**Commitment:** Context decays because the world it describes changes; the fabric commits to a formal decay model: a piece of context observed at t₀ with initial decision-relevance R₀ has decision-relevance R(t) at time t given by the formula below, where λ_c is the Context Half-life — the duration over which decision-relevance halves. The formula deliberately mirrors radioactive decay, including composition under re-observation (a new observation at t₁ resets the decay clock). Consequence: the fabric reasons about context-age probabilistically rather than as a binary fresh-or-expired TTL check. A product assembled at decision time t_d from observations at t₀¹, t₀², ..., t₀ⁿ has a per-observation freshness distribution; the Freshness Budget for a decision class is the composition of per-observation decay curves against a decision-class-specific λ_c × Risk Sensitivity bound (high-risk classes consume freshness budget faster). Discrete implementation committed: a sequential-window observer-buffer pattern — a sliding window of decay-weighted samples per observation type; decision-time queries return a freshness-weighted composite, not the most-recent-observation-only answer (Patent Claim 2).
**Type signature:** `R(t) = R₀ × (1/2)^((t − t₀) / λ_c)`
**Invariants:** λ_c is not a TTL — a TTL is a hard purge/invalidate cutoff; λ_c is a continuous decay curve for confidence reasoning. Data past its λ_c remains accessible for historical reconstruction (Decision Replay depends on this) but does not count as current for decision purposes — physical retention is separated from logical decision-relevance.
**Dependencies:** Freshness Budget / Trust Triangle (§6.6 via plan 01-05; INV-CH7-66); Decision Replay (§7.10, plan 01-08)
**Figures:** Fig-CH07-17
**Open question:** none

### INV-CH7-58 — λ_c as Control Plane configuration, never code

**Section:** §7.7.1–§7.7.2
**Commitment:** λ_c is domain-specific and observation-type-specific (a 10-K has λ_c in months; a Bloomberg IB chat has λ_c of 1 hour for trading and 5 years for compliance retention; a sanctions-screening match has λ_c in minutes at most). The fabric stores λ_c as a Control Plane configuration per observation type, not as a per-document attribute, so a policy change propagates consistently across every instance of that observation type without rewriting graph state. The λ_c values are illustrative calibrations, not universal constants — "These values are illustrative, not empirical — production calibration against observed decision-reversal data and regulatory expectations is required."
**Type signature:** per-observation-type λ_c configuration entry (band, dominant decay driver, supersession event)
**Invariants:** Mechanism/values boundary: the architecture "does not dictate the numbers; it dictates that the numbers be named per observation type, stored on the Control Plane, and auditable as first-class Policy configuration." λ_c values live in Control Plane config, never in code — the SDK ships the machinery, users supply the calibrations (CLAUDE.md §11 "Mechanism, not values" enforces this as the SDK realization).
**Dependencies:** Control Plane (§7.8, plan 01-08); INV-CH7-57
**Figures:** Fig-CH07-17
**Open question:** none

### INV-CH7-59 — λ_c configuration surface shape (illustrative document-type table)

**Section:** §7.7.2
**Commitment:** A seventeen-row illustrative table of wholesale-banking observation types commits the shape of the λ_c configuration surface, not the numbers: every observation type gets its own bounded band (not a single number), a named dominant decay driver (so the choice of λ_c is auditable back to the phenomenon it models), and a named supersession event (so the fabric knows when continuous decay is cut short by a discrete event). Example rows: 10-K, 12 months, quarterly/annual supersession, new 10-K filing; KYC sanctions match, hours, real-time sanctions feed, new match or clearance; Bloomberg IB chat, dual retention (1 hour markets / 5 years compliance). The table is explicitly non-exhaustive; production deployments extend it.
**Type signature:** table row: (document type, illustrative λ_c band, dominant decay driver, supersession event)
**Invariants:** The three-column-plus-type shape is the commitment; the numbers are domain values out of SDK scope.
**Dependencies:** INV-CH7-58; INV-CH7-60 (supersession event column)
**Figures:** Fig-CH07-17
**Open question:** none

### INV-CH7-60 — Supersession as a Policy event with logical (not physical) supersession

**Section:** §7.7.3
**Commitment:** Supersession is a Policy event, not just time decay: a new 10-K collapses λ_c on the old 10-K for current-value queries the moment it is filed, regardless of remaining continuous-decay budget. The fabric must listen for supersession events, not only clock ticks. Two committed properties: (1) logical supersession, not physical deletion — the superseded observation remains in the graph with a `superseded_by` edge to the new observation and a `superseded_at` timestamp; the assembly engine filters superseded observations out of current-value queries by default but retains them for temporal queries bound to pre-supersession windows (foundation for SR 11-7 / OCC re-tracing years later; resolved in full by §7.10). (2) Supersession propagates through the Control Plane as a versioned Policy event that (i) marks the old filing superseded in the graph, (ii) publishes an invalidation cascading through Data Plane cache coherency, (iii) triggers lazy re-derivation on next request — never eager re-materialization (avoiding the thundering-herd cost spike on quarterly earnings cycles). Every invalidation is a versioned Policy event with its own audit lineage in the Policy Store, never a silent runtime side-effect (contrast with direct-wire cache-eviction).
**Type signature:** `superseded_by` edge + `superseded_at` timestamp on the superseded observation
**Invariants:** Logical supersession only (append-only with supersession, consistent with §7.3); invalidation always travels through the Control Plane; re-derivation is lazy; historical reconstruction sees the superseded observation.
**Dependencies:** INV-CH7-51 (InvalidatedBySupersession state), §7.3 append-only graph (plan 01-06), §7.8 Policy Store (plan 01-08), §7.10 replay (plan 01-08)
**Figures:** Fig-CH07-14, Fig-CH07-18
**Open question:** none

### INV-CH7-61 — Context Debt D_c basic formula

**Section:** §7.7.4
**Commitment:** Context Debt is the fabric's structural measurement of how far short assembled context falls from the coverage the current decision requires, computed at assembly time and consumed by the agent as a first-class decision input, not a log line. C_available is the aggregate contextual coverage the fabric can actually assemble at decision time; C_required is the coverage the decision class nominally requires. D_c = 0 means full coverage; D_c = 1 means nothing relevant assembled. The basic form captures quantity-of-coverage only (missing statements, missing certificate, broken connection each lift D_c), not quality-of-coverage.
**Type signature:** `D_c = 1 − (C_available / C_required)`, `D_c ∈ [0, 1]`
**Invariants:** D_c ∈ [0, 1]; a runtime signal consumed as a decision input before the decision is taken, never post-hoc audit metadata.
**Dependencies:** INV-CH7-62 (extended form), INV-CH7-65 (CAR consumes D_c)
**Figures:** none
**Open question:** none

### INV-CH7-62 — Context Debt D_c extended multiplicative formula

**Section:** §7.7.4
**Commitment:** The extended form incorporates three independent multiplicative factors for dimensions along which coverage degrades even when all required sources are nominally present: F is freshness (composition of per-observation decay curves against the decision-class λ_c × Risk Sensitivity bound), C is completeness (fraction of required fields actually populated across assembled sources), S is semantic consistency (fraction of assembled sources whose structured assertions agree on the entities, relationships, and magnitudes the decision cares about). The factors compose multiplicatively because they are gating: any one factor at zero drives D_c to 1.
**Type signature:** `D_c = 1 − (F · C · S)`, `D_c ∈ [0, 1]`, F, C, S ∈ [0, 1]
**Invariants:** Multiplicative (conjunctive) composition; any single factor at zero drives D_c to 1; codomain [0, 1] by construction.
**Dependencies:** INV-CH7-57 (F derives from λ_c decay curves), INV-CH7-63 (defense of the form), INV-CH7-64 (runtime components), INV-CH7-66 (Trust Triangle algebra)
**Figures:** none
**Open question:** none

### INV-CH7-63 — Why multiplicative-conjunctive, not weighted-additive

**Section:** §7.7.5
**Commitment:** The multiplicative form is a defended choice against the named alternative `D_c_alt = 1 − (w_F · F + w_C · C + w_S · S)` (weights summing to 1, each ≥ 0). Rejection rationale: any-factor-near-zero-collapses-whole — the multiplicative form refuses to average a near-zero quality dimension against strong values from the others, forcing the decision into Conditional Assessment Routing; the weighted-additive form masks a collapsed factor (near-zero factor × small weight leaves the sum low-debt). Worked example: guarantor-share disagreement (50% vs 100% across two sources) yields S = 0.05 with F = C = 0.95; multiplicative gives D_c ≈ 0.955 → Forced LLM with the inconsistency surfaced; weighted-additive (w_F = w_C = 0.4, w_S = 0.2) gives D_c_alt = 0.23 → Standard LLM with the inconsistency masked and unflagged. The multiplicative-conjunctive commitment is what makes the D_c signal regulator-defensible (fail-closed under an adversarial SR 11-7 reading) and is the formal defense of the §7.6.9 smoothing-failure-mode watchpoint.
**Type signature:** rejected alternative: `D_c_alt = 1 − (w_F · F + w_C · C + w_S · S)`
**Invariants:** The SDK must implement the multiplicative-conjunctive form; the weighted-additive form is architecturally rejected, not a tuning preference.
**Dependencies:** INV-CH7-62; INV-CH7-56 (discipline 3 cross-cite); INV-CH7-65 (routing consequence)
**Figures:** none
**Open question:** none

### INV-CH7-64 — Three debt components with runtime signals

**Section:** §7.7.6
**Commitment:** The fabric instantiates the extended formula at runtime through three named debt components, each rolling up into F, C, or S, each with a concrete assembly-engine signal: (1) data-source-availability-debt — a required source was attempted and failed; the engine records the attempt, failure mode, and expected source in the product's lineage and lifts D_c; a mature deployment distinguishes "source returned nothing" (zero-length response is information) from "source failed to return" (silence is not information — biases toward caution). (2) as-of-time-staleness-debt — temporal staleness beyond the decision class's λ_c × Risk Sensitivity budget, with explicit disambiguation between "no activity" (low-debt: the world is quiet) and "source failure" (high-debt: the fabric does not know what the world is doing). (3) entity-resolution-confidence-debt — the fabric's own confidence in entity resolution / extraction / schema-matching of unstructured sources below the decision class's semantic-consistency floor (e.g., UBO chain resolution at 0.72 vs a 0.90 floor); must surface as first-class signal, not buried extraction metadata.
**Type signature:** none given (components roll up to F / C / S factors)
**Invariants:** Failed-retrieval attempts recorded in lineage; the no-activity vs source-failure disambiguation is architecturally required; confidence debt is first-class agent-visible signal.
**Dependencies:** INV-CH7-62; INV-CH7-66 (leg mapping)
**Figures:** none
**Open question:** none

### INV-CH7-65 — Conditional Assessment Routing (CAR): Skip / Conditional / Standard LLM / Forced LLM

**Section:** §7.7.7
**Commitment:** CAR is a routing matrix consuming D_c, decision-class threat level, and relevant-signal count to select one of four states. Routing logic verbatim: IF total_relevant_signals == 0 → Skip (decision resolves algorithmically); ELIF threat_level ≤ LOW → Conditional (route to LLM only if context changed significantly since the last cached assessment); ELIF D_c above the class-specific threshold → Forced LLM (context is partial or stale; the LLM must be invoked with explicit awareness of the debt and must reason conservatively against it); ELSE → Standard LLM. In the reference pattern this routing empirically skips LLM for 75–85% of cycles — the mechanism-level answer to "derived-at-runtime is expensive": a naive all-LLM deployment at ×8–15 baseline collapses to full LLM cost on roughly a sixth of cycles. Forced LLM is the distinct behavior in which the prompt includes explicit debt-awareness and reconciliation reasoning is required (e.g., a missing covenant-compliance certificate drives one of 500 credits into Forced; the memo surfaces the gap rather than reasoning around it).
**Type signature:** routing predicate chain as quoted; states ∈ {Skip, Conditional, Standard LLM, Forced LLM}
**Invariants:** D_c thresholds are class-specific configuration (Control Plane, not code); Forced LLM reasons with the gap visible, never around it; the routing is the economic engine bounding LLM cost.
**Dependencies:** INV-CH7-61/62 (D_c inputs), INV-CH7-53 (cost bands), Control Plane thresholds (§7.8, plan 01-08)
**Figures:** Fig-CH07-19
**Open question:** "threat_level ≤ LOW" and "class-specific threshold" — the whitepaper does not specify the threat-level scale, its source, or how the class-specific D_c threshold is set. Readings: (a) both are Control Plane configuration per decision class (consistent with §7.8 posture; SDK ships the routing mechanism only); (b) threat level is computed by the fabric from signal characteristics (would require a specified computation the paper never gives). Left unnumbered for synthesis.

### INV-CH7-66 — Trust Triangle debt-mapping (Ch 6 forward-ref resolution)

**Section:** §7.7.8
**Commitment:** The mapping from the three debt components to the Chapter 6 §6.6 Trust Triangle legs is structural, not metaphorical: confidence-debt (entity-resolution-confidence-debt) → Confidence leg; freshness-debt (as-of-time-staleness-debt) → Freshness leg; lineage-integrity-debt (data-source-availability-debt and provenance breaks) → Lineage leg. The triangle is conjunctive — weak legs degrade the whole; a Context Product with any weak leg fails the triangle regardless of the other two. A product arriving at an agent carries the composite D_c, the three component debt scores, and the three leg strengths derived from them, so the agent's decision policy reasons against explicit signals, never an opaque "trust" label. The multiplicative D_c = 1 − (F · C · S) is the algebraic statement of the triangle's conjunctive gating.
**Type signature:** per-product signal set: composite D_c + three component debt scores + three leg strengths
**Invariants:** Conjunctive gating (weak leg fails the whole); the three-signal decomposition is runtime, measurable, and agent-visible at assembly time.
**Dependencies:** §6.6 Trust Triangle (plan 01-05), INV-CH7-62, INV-CH7-64
**Figures:** Fig-CH07-17
**Open question:** none

### INV-CH7-67 — Conservative bias and Fail-Closed under elevated D_c

**Section:** §7.7.9
**Commitment:** Elevated D_c biases urgency upward, not downward: debt is a risk amplifier, not a risk mitigator. The architectural posture is fail-closed by default — the absence of strong evidence against a suspicion is an argument for caution, not for clearing it. The fabric explicitly rejects two nearby postures: cache-first (missing data as a latency/availability problem) and permissive LLM-first (the model fills the gap from general knowledge) — both minimize apparent uncertainty, which a regulated-enterprise decision agent must not do. Instead the fabric makes uncertainty visible and routes upward into human-escalation, additional-source-fetch, or decision-decline paths preserving accountability (Patent Claim 7). This is the mechanism-level resolution of the upstream-source-break objection (Rebuttal #10): an upstream break produces elevated D_c and Forced-LLM/human-escalation routing — a bounded outage with auditable degradation, not a silent correctness failure.
**Type signature:** none given
**Invariants:** Fail-closed by default under elevated D_c; uncertainty is surfaced and routed, never smoothed; decision-reversal exposure bounded to decisions actually dependent on the broken source.
**Dependencies:** INV-CH7-65 (Forced LLM / escalation routing), HITL escalation surface (SDK extension, CLAUDE.md §8.2 ExceptionEscalation hooks on D_c threshold breach)
**Figures:** none
**Open question:** none

### INV-CH7-68 — Debt cascade across multi-agent handoff

**Section:** §7.7.10–§7.7.11
**Commitment:** In multi-agent workflows (intake → escalation → resolution), the debt a downstream agent consumes is the cumulative debt of upstream agents' context carried forward, not a per-agent metric: each handoff inherits the upstream context plus interim observations, with D_c recomputed against aged observations (inherited staleness plus elapsed λ_c decay); the composition F · C · S degrades across handoffs until a class-threshold breach triggers fail-closed routing (the resolution agent declines to act and routes to human escalation). "Debt compounds at agent speed, not human speed." The credit-memo worked example (§7.7.11) additionally commits per-claim debt decomposition: with inputs (a)–(d) present and (e) overdue, D_c is non-zero for the compliance-status claim specifically while other claims remain at D_c = 0; CAR routes to Forced LLM, which surfaces the absence in the memo output ("compliance status cannot be affirmed…") as a first-class input to the next-action recommendation — the gap shapes the decision before it is taken.
**Type signature:** none given (per-claim D_c decomposition within one Context Product)
**Invariants:** D_c is recomputed at every handoff boundary against inherited plus new observations; threshold breach at any handoff triggers fail-closed routing; gaps are decision inputs, not log lines.
**Dependencies:** INV-CH7-62, INV-CH7-65, INV-CH7-67; workflow/orchestration surface (SDK extension, CLAUDE.md §8.1)
**Figures:** Fig-CH07-20 (companion: Fig-CH03-04)
**Open question:** none

---

## Open Questions (unnumbered)

- (INV-CH7-48, §7.6.1/§7.6.4) "TTL bounds rejects a Contract whose expires_at is in the past or beyond a MAX_TTL envelope" — where is MAX_TTL configured and what governs its value? Readings: (a) Control Plane configuration per Context Product class; (b) fabric-wide constant (collides with the mechanism/values boundary); (c) derived from the product's λ_c band. Consequences per reading noted in the entry.
- (INV-CH7-65, §7.7.7) "ELIF threat_level ≤ LOW → Conditional … ELIF D_c above the class-specific threshold → Forced LLM" — the threat-level scale, its source, and how class-specific D_c thresholds are set are unspecified. Readings: (a) both are Control Plane configuration per decision class; (b) threat level is fabric-computed from signal characteristics (no computation given). Consequences per reading noted in the entry.
