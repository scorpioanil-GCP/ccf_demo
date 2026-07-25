# Inventory Fragment — Chapter 7, §7.1–§7.4 (keys INV-CH7-01..39)

**Canonical authority:** `docs/CCF_Whitepaper_1-2.md` (the converted `.md` is authoritative; all citations reference its sections, never the PDF — locked D-01). Where this fragment and the whitepaper disagree, the whitepaper wins.

**Scope:** §7.1 Layered Architecture, §7.2 Architectural Decomposition, §7.3 Context Graph — System of State, §7.4 Context Operators — System of Computation. Key range owned: INV-CH7-01 through INV-CH7-39. Open questions are quoted and UNNUMBERED (numbering is the synthesis plan's job).

---

## §7.1 Layered Architecture (L1–L6)

### INV-CH7-01
- **Section:** §7.1
- **Commitment:** The fabric decomposes into six layers of responsibility (L1–L6), each owning a single responsibility, a single artifact, and a single handoff into the layer above. The layering is the architectural answer to the Chapter 4 §4.7 "missing layer" observation: traditional data architectures end at L3/L4; agentic reasoning requires L5 (typed role/intent-conditioned interpretation) and L6 (decision-ready delivery under contract), which do not exist in query-serving architectures.
- **Type signature:** Six-layer stack: L1 Signal → L2 Context Assembly → L3 Context Graph → L4 Context Operators → L5 Context Projection (Π) → L6 Context Products.
- **Invariants:** Layers are responsibility boundaries, not a sequential pipeline ("these layers are not a sequential pipeline; they are responsibility boundaries that ensure context is constructed correctly before it is consumed").
- **Dependencies:** INV-CH7-08 (four-concern decomposition), Chapter 4 §4.7 missing-layer claim.
- **Figures:** Fig-CH07-01 (fabric as persistent institutional memory / closed loop), Fig-CH07-02 (L1–L6 logical architecture; "Missing" annotation on L2, L3, L4; Perception/Expression bidirectional arrows).
- **Open question:** None.

### INV-CH7-02
- **Section:** §7.1
- **Commitment:** L1 — Signal Layer. Responsibility: ingestion and event normalization. Heterogeneous sources (transactions, operational events, documents, audio transcripts, external feeds) are expressed in a canonical event envelope with source identifiers and timestamps. L1 does not interpret; signals carry provenance and temporal markers but are not yet typed as entities/relationships. Handoff to L2: a stream of normalized signals, each tagged with source, ingestion timestamp, observed-time where known, and raw payload. Structured and unstructured streams arrive together — neither is privileged at the ingestion boundary.
- **Type signature:** Canonical event envelope: `{source, ingestion_timestamp, observed_time?, raw_payload}` (paraphrase of the prose enumeration; no formal schema given).
- **Invariants:** L1 does not interpret; no entity/relationship typing at L1; unstructured and structured co-equal at ingress.
- **Dependencies:** INV-CH7-03 (L2 consumes the normalized stream).
- **Figures:** Fig-CH07-02.
- **Open question:** "whatever raw payload the upstream system emitted" — the canonical event envelope's formal schema is not specified; a general-purpose SDK must commit to one. (unnumbered — see Open Questions)

### INV-CH7-03
- **Section:** §7.1
- **Commitment:** L2 — Context Assembly. Four concerns converge and define the layer: (1) semantic resolution (entity/relationship extraction from the signal stream); (2) temporal stitching (observed-time vs valid-time reconciliation producing as-of views without leaking future information into historical queries); (3) policy binding (principal scope, jurisdictional constraint, entitlement state attached to every resolved subgraph at assembly time — "the fabric does not resolve entities first and then ask who can see them"); (4) operator invocation (Context Operators actually run here, producing subgraph productions). L2 is the stage the Algorithmic ⇄ Semantic alternation actually crosses, since both algorithmic structure (traversal, temporal reconciliation) and semantic structure (entity extraction, relationship inference) are active in Assembly.
- **Type signature:** None given beyond the four-concern enumeration.
- **Invariants:** Scope/policy is bound at assembly time, not post-processed; no future-information leakage into historical (as-of) views.
- **Dependencies:** INV-CH7-02 (L1 handoff), INV-CH7-10 (graph state written), §7.6.6 alternation primitive.
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-04
- **Section:** §7.1
- **Commitment:** L3 — Context Graph (layered view). The graph is first-class persisted state — not a cache over a source system, not a denormalized lake view, but a computational primitive holding entities, typed relationship edges, temporal as-of versions, policy state, materialized projection state, and append-only lineage. Structure is "append-only-forward-with-supersession": new observations supersede rather than overwrite, both versions retained so as-of queries remain sound and supersession events themselves become analyzable state. Mechanism deferred to §7.3.
- **Type signature:** Six state classes per the G(E, R, T, P, Π, L) tuple (formalized at INV-CH7-10).
- **Invariants:** Append-only-forward-with-supersession; graph is persisted, typed, and the substrate all other layers compose against.
- **Dependencies:** INV-CH7-10..21 (§7.3 mechanism).
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-05
- **Section:** §7.1
- **Commitment:** L4 — Context Operators (layered view). Four canonical categories compose over the graph: Traversal (relationship walks from seed entities to a bounded subgraph), Temporal (as-of filters reconciling valid-time against observed-time), Policy (entitlement/jurisdiction/regulatory enforcement before downstream computation sees data), Similarity (surfacing non-obvious relevant context — analogs, cohorts, patterns). The layer owns composition: operators are not a fixed pipeline and are not exposed to agents as query primitives; they compose into Operator Plans — "typed expression trees the Assembly runtime can execute, memoize, and replay."
- **Type signature:** OperatorPlan = typed expression tree (formal algebra at INV-CH7-23).
- **Invariants:** Composition preservation (same operator plan + same graph state → same output) is the mechanical foundation of Decision Replay (§7.10); computation is typed composition under constraint, not ad hoc retrieval.
- **Dependencies:** INV-CH7-22..27 (§7.4 mechanism), §7.10 Decision Replay.
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-06
- **Section:** §7.1
- **Commitment:** L5 — Context Projection Π (layered view). Projection shapes subgraph productions into role-conditioned decision views: a typed transformation from graph substructure into principal-conditioned artifact, parameterized by the tuple (role, intent, temporal context, policy). It is not a post-hoc filter and not an RBAC overlay — the same subgraph is projected into different role-shaped structure per principal. Interpretation happens at L5 and nowhere else: "it does not leak into the agent, it does not leak into the delivery layer, and it does not leak back into the graph."
- **Type signature:** Π parameterized by `(role, intent, temporal context, policy)`.
- **Invariants:** Interpretation-isolation at L5 (no leakage to agent, delivery, or graph); projection-as-transformation-not-filter (load-bearing for Rebuttal #4).
- **Dependencies:** §7.5 mechanism (plan 01-07's key range), INV-CH7-05 (operator outputs).
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-07
- **Section:** §7.1
- **Commitment:** L6 — Context Products (layered view). The delivery surface: a Context Product is a typed, governed, decision-ready unit of meaning served under the eight-element contract Chapter 6 §6.3 specified (schema, freshness SLA, TTL, policy binding, lineage, semantic versioning, discovery, addressability). L6 inherits that contract by name and commits to the delivery mechanism enforcing it. A Context Product is a versioned artifact — TTL-bounded, semver-stamped, lineage-linked, served under freshness SLA — "not a query result, and … not a cache entry"; delivery is "a contracted decision-time artifact — not a shared queryable data model."
- **Type signature:** Eight-element contract inherited from §6.3 by name.
- **Invariants:** Delivery only via contracted artifact; contract enforcement, materialization policy, and SLO envelope specified in §7.6.
- **Dependencies:** Ch 6 §6.3 contract (Chapter 5–6 fragment's range), §7.6 mechanism (plan 01-07's key range).
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-08
- **Section:** §7.1
- **Commitment:** Two orthogonal planes cut across every layer. Control Plane (governance surface): Policy definitions binding L2/L4; operator behavior rules parameterizing L4; projection rules and entitlement definitions parameterizing L5; D_c thresholds driving debt-gated fail-closed decisions; λ_c calibration per observation type; materialization policy (pre-computed vs derived-on-demand products). "The Control Plane is where the fabric is declared — what it is allowed to do, how it is parameterized, and under what conditions it must refuse to act." Data Plane (continuous-execution surface): runs Assembly at L2, operator execution at L4, projection at L5, product serving at L6, within Control Plane constraints. The pattern is the canonical control-plane/data-plane separation of modern runtime architectures applied to a cognitive fabric.
- **Type signature:** None given (configuration surface enumerated; §7.8 commits the runtime separation mechanism).
- **Invariants:** Plane separation is maintained at runtime (mechanism in §7.8); every layer binds to one or both planes.
- **Dependencies:** §7.8 (plan 01-08's key range), §7.7 (D_c, λ_c).
- **Figures:** Fig-CH07-01, Fig-CH07-02.
- **Open question:** None.

---

## §7.2 Architectural Decomposition

### INV-CH7-09
- **Section:** §7.2
- **Commitment:** The fabric realizes as four concerns, each committed in mechanism detail by a later section: State (how the fabric holds what is true at a moment in time — §7.3), Computation (how subgraph productions are derived from state under Control Plane constraints — §7.4), Interpretation (how productions are shaped into principal-conditioned payloads — §7.5), Delivery (how interpretations are returned as versioned, governed, SLO-bounded artifacts — §7.6). The layered view (§7.1) answers *where*; the decomposition answers *what*.
- **Type signature:** State ↔ §7.3, Computation ↔ §7.4, Interpretation ↔ §7.5, Delivery ↔ §7.6.
- **Invariants:** The two readings (layers, concerns) are complementary views of one architecture.
- **Dependencies:** INV-CH7-01, and the four per-concern entries below.
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-10
- **Section:** §7.2 (concern: State) with §7.3 mechanism
- **Commitment:** State realizes as a typed, accumulating graph persisted behind a single-writer persistence tier. The single-writer invariant is "not a convention but an enforced architectural property: only the Assembly worker holds a write handle to the graph; every read-path service in the fabric is constructed without one, with the absence of a write handle enforced by dependency injection at boot time rather than by runtime discipline." Deterministic state transitions are a precondition for deterministic replay — if any read-path component could write, graph history would be contaminated by non-Assembly transitions Decision Replay could not reconstruct. Pattern grounding (reference implementation): typed graph with compound unique index on `(tenant_id, entity_uri)`, idempotent upsert with multi-source lineage accumulation, single-writer enforcement at boot time.
- **Type signature:** Compound unique index on `(tenant_id, entity_uri)`; write-handle absence expressed in constructor signatures (DI at boot).
- **Invariants:** **Single-writer enforcement at boot** (named architectural invariant); deterministic state transitions as replay precondition.
- **Dependencies:** INV-CH7-14, INV-CH7-15 (§7.3.2 mechanism), §7.10 replay.
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-11
- **Section:** §7.2 (concern: Computation)
- **Commitment:** Computation realizes as read-only-sync operator composition over projected subgraph. Operators never mutate graph state; they read, compose, and produce typed subgraph productions. Composition is via named, typed operators in expression trees evaluated deterministically. Composition preservation (formally at INV-CH7-23) is the foundation of deterministic Decision Replay. Pattern grounding: "operators compose via a typed expression tree with intermediate contexts replayable individually and lineage-complete end-to-end." Computation "is not an opaque large-language-model call against the graph."
- **Type signature:** Read-only-sync operator contract; typed expression tree.
- **Invariants:** **Operator read-only purity** (no graph mutation); intermediates individually replayable and lineage-complete.
- **Dependencies:** INV-CH7-22..27 (§7.4), §7.10.
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-12
- **Section:** §7.2 (concern: Interpretation)
- **Commitment:** Interpretation realizes as a Protocol-based projection engine with structural typing — a two-method contract: `required_operators()` declares which operators the projection depends on; `invoke()` executes the typed transformation. Dispatch is by structural typing at registration time rather than inheritance; new projections register by matching the Protocol shape; the engine resolves operator dependencies, runs them, and transforms the result into the role-conditioned payload. Pattern grounding: "structural interfaces with per-request operator resolution and a multi-stage execution engine with validation gates." Interpretation is not an RBAC filter on a shared query result.
- **Type signature:** `required_operators()` + `invoke()` (Protocol, structural typing).
- **Invariants:** Structural-typing dispatch, not inheritance; projection-as-typed-transformation.
- **Dependencies:** §7.5 mechanism (plan 01-07's key range), INV-CH7-06.
- **Figures:** Fig-CH07-02.
- **Open question:** None.

### INV-CH7-13
- **Section:** §7.2 (concern: Delivery)
- **Commitment:** Delivery realizes as a typed contract with semver, TTL, and lineage enforced at validation time. The typed base declares the eight §6.3 elements structurally; validation forbids additional fields at contract time (forbid-extra discipline) so a product cannot drift beyond its declared contract between versions; per-product subclasses add typed payloads. Pattern grounding: "typed bases with forbid-extra structural validation and per-product versioned payloads, with three sequential validation gates (empty-operator guard, lineage strict equality, TTL bounds) at assembly time."
- **Type signature:** Typed base with `extra=forbid`; per-product versioned payload subclasses.
- **Invariants:** **Three validation gates** (empty-operator guard, lineage strict equality, TTL bounds — named architectural invariant); forbid-extra at contract time.
- **Dependencies:** Ch 6 §6.3 (eight-element contract), §7.6 mechanism (plan 01-07's key range).
- **Figures:** Fig-CH07-02.
- **Open question:** None.

---

## §7.3 Context Graph — System of State

### INV-CH7-14
- **Section:** §7.3
- **Commitment:** The six-tuple G(E, R, T, P, Π, L) named conceptually at Ch 5 §5.2 becomes mechanism here. E: entities as URI-addressable nodes with identity persistent across source systems and time. R: typed relationships (ownership, guarantee, cross-default, covenant-of, defined-by, measured-by, …) as first-class persisted state, not derived joins. T: temporal state along two reconciled axes — valid-time (when a fact was true in the world) and observed-time (when the fabric learned of it). P: policy state — principal, jurisdiction, regulatory-regime binding traveling with every subgraph. Π: projection state — role-conditioned materialized views. L: lineage — append-only record of what signal chain produced every entity and edge, including passage-level anchors for unstructured content. The six axes are "orthogonal in concern but interdependent in use: no operator composes meaningfully against fewer than four of them at once, which is why collapsing them into flat tables breaks reasoning."
- **Type signature:** `G(E, R, T, P, Π, L)`; T bitemporal: (valid-time, observed-time).
- **Invariants:** Each axis persisted as a first-class surface; L append-only.
- **Dependencies:** Ch 5 §5.2 (formal introduction — Chapter 5–6 fragment's range), INV-CH7-15..21.
- **Figures:** Fig-CH07-03 (six-dimensional hexagon — every decision is the reconciled output of all six dimensions).
- **Open question:** None.

### INV-CH7-15
- **Section:** §7.3.1
- **Commitment:** The Context Graph is a first-class persisted computational primitive with its own invariants, write path, and lifecycle — not a cache, not a denormalized view, not an application abstraction. Two structural properties: (1) the graph accumulates enrichments across pipeline stages (an entity resolved by L2 persists; later enrichment passes attach rather than recompute from raw signals); (2) downstream stages append rather than reconstruct (L4/L5/L6 read current state, write their outputs back with lineage; they never rewrite entities the Assembly worker owns). The base ContextGraph type declares the six-tuple structure, single-writer write path, lineage-accumulation semantics, and supersession-not-deletion invariant; domain deployments extend the entity-class and relationship-type enumerations within that shape (banking/markets/treasury subclass examples are illustrative domain values, not SDK content). Reference-implementation grounding: physical representation maps to ~10 collections; single-writer enforced by dependency injection ("the absence is a structural property of the constructor signature, not a runtime check"). Inline decision box: the section text names "D-11's first-class persisted computational primitive commitment" (quoted at Fig-CH07-05 caption; D-NN catalog is plan 01-11's job).
- **Type signature:** Base `ContextGraph` type declaring six-tuple structure + subclass extension of entity-class and relationship-type enumerations; ~10-collection physical pattern.
- **Invariants:** **Single-writer** (DI-enforced at boot); supersession-not-deletion; append-not-reconstruct for downstream stages.
- **Dependencies:** INV-CH7-10, INV-CH7-14.
- **Figures:** Fig-CH07-04 (logical six-tuple ↔ physical collection pattern).
- **Open question:** "the physical representation maps to ~10 collections" — the exact collection decomposition is reference-implementation grounding, not a normative count; what the SDK's storage Protocol must require versus leave to backends is a design question. (unnumbered — see Open Questions)

### INV-CH7-16
- **Section:** §7.3.2
- **Commitment:** Persistence is keyed by a compound unique index on `(tenant_id, entity_uri)`. "Multi-tenancy is a structural property of identity, not a query-time filter: there is no code path in the fabric that resolves an entity without a tenant scope," and uniqueness is enforced at the persistence tier, not the application layer — making the tenant invariant a first-class correctness property (§7.8 forward-ref for invariant framing).
- **Type signature:** Compound unique index: `(tenant_id, entity_uri)`.
- **Invariants:** **Tenant invariant** — no entity resolution without tenant scope; persistence-tier uniqueness enforcement.
- **Dependencies:** INV-CH7-10, §7.8 architectural invariants (plan 01-08's key range).
- **Figures:** Fig-CH07-04.
- **Open question:** None.

### INV-CH7-17
- **Section:** §7.3.2
- **Commitment:** The write path is idempotent upsert: the same observation arriving twice (two source systems, or a retried ingestion worker) produces exactly one persisted entity record. Lineage, however, is NOT idempotent: multi-source lineage accumulates via set-union across every source that ever contributed evidence, with per-source timestamps and per-source passage-level anchors where the source is unstructured. Worked example: one counterparty identified by four different sources resolves to a single E node whose L carries set-union-accumulated evidence from all four.
- **Type signature:** Idempotent upsert on `(tenant_id, entity_uri)`; L accumulation = set-union with per-source `{timestamp, passage_anchor?}`.
- **Invariants:** **Idempotent upsert** (entity records); **set-union lineage accumulation** (never overwrite).
- **Dependencies:** INV-CH7-16, INV-CH7-14 (L axis).
- **Figures:** Fig-CH07-04, Fig-CH07-05 (Lineage Writer segment).
- **Open question:** None.

### INV-CH7-18
- **Section:** §7.3.2
- **Commitment:** Entity URIs are first-class addressable nodes with a naming convention the fabric reads against: `entity-class://<identity-hash>` for entities resolved by hash of identifying attributes, or `entity-class://<principal>-<discriminator>` for principal-scoped entities (examples given: `counterparty://lei-5493001RKR55V4X61F71`; `facility://<borrower-lei>-<facility-id>`). URI addressability means operators compose against stable identifiers surviving source-system changes; L preserves the URI → source-native-identifier mapping.
- **Type signature:** `entity-class://<identity-hash>` | `entity-class://<principal>-<discriminator>`.
- **Invariants:** URI stability across source-system change; source-identifier mapping preserved in L.
- **Dependencies:** INV-CH7-16, INV-CH7-17.
- **Figures:** None specific.
- **Open question:** None.

### INV-CH7-19
- **Section:** §7.3.3
- **Commitment:** Unstructured content is a first-class signal type: documents, audio transcripts, and semi-structured chat feed the graph as typed structure. The ingestion path "does not store raw text and return it at retrieval time; it performs entity/relationship extraction at ingestion time, producing typed nodes and typed edges that persist in E and R alongside" structured-feed output. "The Graph is built from unstructured content, not consulted from it" — the architectural distinction from RAG. Passage-level Lineage is the mechanism obligation carried from Ch 5 §5.6: an extracted edge carries an L record anchoring source document, page, paragraph, and offset span (or transcript identifier, timestamp, textual span) — not merely a document identifier. Passage-level anchoring is what makes §7.4 Composition (a) operationally possible and §7.10 replay forensically defensible: the Product→source-passage chain is traversable at any time without reconstructing it from unstructured indexes. The covenant cross-reference worked example (§14 covenant → defined-by → §1.5 definition → measured-by → §2.1 methodology) demonstrates graph-traversal resolution versus chunk-retrieval reconstruction.
- **Type signature:** Passage-level L anchor: `{document, page, paragraph, offset_span}` (documents) / `{transcript_id, timestamp, text_span}` (transcripts).
- **Invariants:** **Passage-level lineage** for unstructured content; extraction at ingestion time, not retrieval time.
- **Dependencies:** Ch 5 §5.6 (first naming), §7.4 Composition (a) (INV-CH7-30), §8.3 Pattern 5, §7.10.
- **Figures:** Fig-CH07-04.
- **Open question:** None.

### INV-CH7-20
- **Section:** §7.3.4
- **Commitment:** The Counterparty Credit Risk graph topology — entities (counterparty, parent group, material subsidiaries, exposure, facility, collateral), relationships (ownership with percentage on the edge, guarantee full/partial/keepwell, cross-default with carve-outs, set-off), temporal state (as-of filing date vs as-of intraday composed without flattening), policy state (Reg O, UK PRA 9/17, internal policies — attached at subgraph-resolution time, not post-processed), projection state (credit officer / compliance officer / credit-risk officer role lenses), lineage (10-K paragraph spans, trade blotter records, rating-agency feeds, credit-opinion memos, set-union). This topology is the substrate the §7.4 worked compositions (a) and (d) and the §7.5 three-role projection compose against. **Inventory note:** the topology is a *worked domain instantiation* (banking values), not SDK mechanism — the mechanism commitments it demonstrates are subclassing (INV-CH7-15), per-relationship-type lineage, materiality-as-thresholded-relationship, and policy-intersection-at-resolution-time. The text also cites inline decision "D-13 §7.3" (regulatory large-exposure regime binding).
- **Type signature:** None normative (domain illustration).
- **Invariants:** Each relationship type persisted in its own collection with its own lineage; materiality is a thresholded relationship, not a graph-wide flag; P attached at subgraph-resolution time.
- **Dependencies:** INV-CH7-14, INV-CH7-15; consumed by §7.4 compositions (a), (d) and §7.5 projections.
- **Figures:** None specific (topology described in prose + bullets).
- **Open question:** None.

### INV-CH7-21
- **Section:** §7.3.5
- **Commitment:** Two interaction mechanics are committed as sequences. (1) Supersession: supersession is logical, not physical — the prior claim remains in the graph with a `superseded_by` edge and a `superseded_at` timestamp; replay against T_prior re-renders prior state exactly because it was never discarded. The Temporal Operator reconciles observed-time vs valid-time structurally (not as a retention heuristic); the Lineage Writer accumulates set-union across all contributing sources. The sequence is "the runtime enactment of D-11's first-class persisted computational primitive commitment and D-33's supersession-as-Policy-event obligation" (inline D-NN references quoted; catalog is plan 01-11's job). (2) Entity resolution across disparate source systems: fragmented native identifiers (Markets, Treasury, ADR) converge to a single canonical E node via the Entity Resolver (correlation over shared attributes — LEI where present, registered address / authorized-signatory metadata otherwise) and Semantic Layer ontology disambiguation, under a tenant-scoped URI; unstructured claims (e.g., a covenant document's extracted entity reference — "XC-05's unstructured-as-first-class commitment") participate as first-class claims on par with structured identifiers; L accumulates set-union across all source classes.
- **Type signature:** Supersession record: prior claim + `superseded_by` edge + `superseded_at` timestamp.
- **Invariants:** **Append-only-forward-with-supersession** (overwrite-in-place prohibited — overwriting "would make Decision Replay at T+2 years structurally impossible"); canonical-E convergence regardless of querying line of business.
- **Dependencies:** INV-CH7-14 (T, L axes), INV-CH7-17, §7.7 supersession-as-Policy-event, §7.10 replay.
- **Figures:** Fig-CH07-05 (graph mutation on supersession sequence), Fig-CH07-06 (entity resolution sequence).
- **Open question:** The Entity Resolver's correlation mechanism ("shared attributes … where it does not") is described at pattern level; the SDK's resolver contract — pluggable strategy vs shipped mechanism — is a design question. (unnumbered — see Open Questions)

---

## §7.4 Context Operators — System of Computation

### INV-CH7-22
- **Section:** §7.4
- **Commitment:** Four canonical operator categories cover the space of operations the fabric performs: Traversal — bounded relationship walks parameterized by edge types, depth limits, and materiality thresholds; Temporal — valid-time and observed-time reconciliation against as-of alignments; Policy — principal, jurisdiction, and entitlement subgraph substitution applied before downstream operators see data; Similarity — corpus-scoped ranking with pinned index version, thresholded by contract, composed under policy pre-projection rather than as unconstrained retrieval. §7.4's threefold mechanism commitment: (1) operators compose algebraically; (2) composition is composition-preserving (intermediates individually replayable, cache-coherent under half-life-driven invalidation, lineage-complete); (3) operator plans are generated dynamically at runtime from agent intent by the Operator Plan DAG generator (text cites inline decision "D-15").
- **Type signature:** Category contracts per the parenthetical parameterizations above; each operator "typed in its inputs, in its outputs, and in its side-effect-free-read-only-sync contract against the graph" (Fig-CH07-07 caption).
- **Invariants:** **Operator purity** — side-effect-free, read-only-sync; every composition reads across multiple six-tuple axes simultaneously.
- **Dependencies:** INV-CH7-05, INV-CH7-14; category mechanism entries INV-CH7-24..27.
- **Figures:** Fig-CH07-07 (compositional algebra: four categories → Π → Context Product).
- **Open question:** None.

### INV-CH7-23
- **Section:** §7.4.1
- **Commitment:** The compositional form the fabric commits to is the operator algebra, with ∘ read right-to-left (Similarity first … Π last). A specific request need not exercise all five categories — three- and four-operator compositions are normal; the algebra defines the composition surface, a request picks its operators from it. The algebraic property the fabric reads against is composition-preservation — associativity of composition under the typed operator algebra — with three concrete consequences: (1) intermediate operator outputs are individually replayable (persistable, diffable, re-executable against same input state — the §7.10 replay mechanism); (2) intermediates are cache-coherent under λ_c-driven invalidation (supersession invalidates downstream intermediates predictably, no full recomputation); (3) every intermediate is lineage-complete (L carries forward operators invoked, parameters, and graph state read — each intermediate carries its own provenance sub-chain). Formal ancestry acknowledged (relational algebra, service-mesh filter composition, graph algebra); the novelty claim is the semantic-domain application plus typed contract plus closed-loop feedback, not the algebra itself. Inline decisions cited at Fig-CH07-08: "D-14 algebraic composition, D-17 determinism, and D-18's consolidated Rebuttal #11 + #13 answer."
- **Type signature:** `ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity`; composition-preservation: `(A ∘ B)(G) = A(B(G))`.
- **Invariants:** **Composition-preservation `(A∘B)(G) = A(B(G))`** — named invariant required for replay determinism; intermediates replayable / cache-coherent / lineage-complete.
- **Dependencies:** INV-CH7-11, §7.10 Decision Replay, §7.7 λ_c invalidation.
- **Figures:** Fig-CH07-07, Fig-CH07-08 (composition lifecycle: B(G) cached, A consumes intermediate, associativity preserved).
- **Open question:** None.

### INV-CH7-24
- **Section:** §7.4 (category: Traversal; walked in §7.4.6)
- **Commitment:** Traversal operators walk relationship edges from seed entities to a bounded subgraph — parameterized by `relationship-types` (e.g., structural-risk-carrying edges), `depth-limit`, and `materiality-threshold` (configurable floors). The traversal produces "a bounded-expansion-of-relevance rather than exhaustive-expansion-of-connection"; cost scales with projected subgraph, not full graph (composition (d): a naive Tier-1 walk could touch hundreds of thousands of nodes; the bounded, policy-projected, materiality-thresholded traversal resolves in tens to low hundreds). This is the mechanism answer to the PITFALLS Zone A3 derived-at-runtime cost objection.
- **Type signature:** `Traversal(relationship-types, depth-limit, materiality-threshold)`.
- **Invariants:** Bounded expansion; read-only purity (INV-CH7-22); thresholds/floors are Control Plane configuration, not code constants.
- **Dependencies:** INV-CH7-14 (R axis), INV-CH7-20 (worked topology), INV-CH7-23.
- **Figures:** Fig-CH07-07, Fig-CH07-09.
- **Open question:** None.

### INV-CH7-25
- **Section:** §7.4 (category: Temporal; walked in §7.4.4)
- **Commitment:** Temporal operators reconcile valid-time (when a fact is effective in the world) against observed-time (when the fabric learned of it) at the as-of boundary a decision requires. The reconciliation is a temporal correctness semantic, not a TTL filter: the fabric structurally expresses the difference between "we don't have this yet" and "this hasn't happened yet" (composition (b): executed-not-settled payment has future valid-time / present observed-time; cleared-not-posted has present valid-time / future observed-time — an as-of-now reconciliation resolves both without flattening). Half-life (λ_c, §7.7) sits ON TOP of this operator-layer temporal correctness — the answer to Rebuttal #5 ("Half-life is just TTL").
- **Type signature:** `Temporal(as-of-T)` over bitemporal (valid-time, observed-time) state.
- **Invariants:** Bitemporal reconciliation without flattening; no future-information leakage into as-of views (INV-CH7-03).
- **Dependencies:** INV-CH7-14 (T axis), §7.7 half-life (plan 01-08's key range).
- **Figures:** Fig-CH07-07, Fig-CH07-09.
- **Open question:** None.

### INV-CH7-26
- **Section:** §7.4 (category: Policy; walked in §7.4.5)
- **Commitment:** Policy operators enforce principal, jurisdiction, and entitlement by subgraph SUBSTITUTION at the Context Graph layer — "not a row-level filter on an index." Inadmissible content (e.g., MNPI-tagged documents outside the principal's wall-crossing context) "are not hidden by a visibility predicate appended to a retrieval query — they are structurally absent from the subgraph the principal's Policy-projected graph consists of." Jurisdictional constraints bake into the same projection. The ordering commitment is load-bearing: **the Policy Operator runs before the Similarity Operator, not after** — similarity ranks only over the principal-permissible subgraph; "no filter runs after retrieval because no retrieval of inadmissible content happened." This is the structural (not post-hoc) prevention of the wrong-chunk-through-wrong-principal failure class (Rebuttals #11, #13).
- **Type signature:** `Policy(principal, jurisdiction, entitlement)` → subgraph substitution.
- **Invariants:** **Policy-before-Similarity composition ordering**; structural absence, not post-retrieval filtering.
- **Dependencies:** INV-CH7-14 (P axis), INV-CH7-27, INV-CH7-23 (ordering within algebra).
- **Figures:** Fig-CH07-07 (ordering rendered), Fig-CH07-09.
- **Open question:** None.

### INV-CH7-27
- **Section:** §7.4 (category: Similarity; contract in §7.4.7)
- **Commitment:** Similarity operators surface non-obvious relevant context (analogs, cohorts, patterns) via corpus-scoped ranking. The determinism contract is structural: "given same corpus version, same embedding model version, same query, same threshold, same policy regime → same result." The index version is pinned in L (the output subgraph's L carries the embedding index identifier and version), so replay needs no external knowledge of which index was live; the threshold is part of the contract, not runtime-tuned; and composition with Policy runs before Similarity, so a different principal sees a different ranking because the input corpus is structurally different — not because ranking is nondeterministic. This contract-level determinism is the stated distinction from GraphRAG, whose intermediate pipeline outputs are not individually replayable and whose runtime-tunable parameters are not persisted in the decision record.
- **Type signature:** `Similarity(threshold)` with contract tuple `(corpus_version, embedding_model_version, query, threshold, policy_regime) → result`; index version pinned in L.
- **Invariants:** **Similarity determinism contract**; threshold carried through composition and re-invoked identically at replay; policy-pre-projection.
- **Dependencies:** INV-CH7-26 (ordering), INV-CH7-23, §7.10 replay.
- **Figures:** Fig-CH07-07, Fig-CH07-09.
- **Open question:** None.

### INV-CH7-28
- **Section:** §7.4.2
- **Commitment:** The Operator Plan DAG generator (Planner) is the runtime that selects which operators a specific request needs and orders them into a dependency-correct execution plan. Given an agent intent — "typically a tuple of role, decision class, and entity reference" — three stages: Stage 1 maps intent to required operators via operator-registry lookup; Stage 2 topologically orders them into the composition tree respecting dependencies ("Policy before Similarity; Temporal before Traversal where Traversal reads temporally-reconciled state"); Stage 3 hands the plan to the projection engine, which resolves intermediate contexts and reconciles them into the final Context Product. Pseudocode signature given in text (embedded in prose in the `.md` conversion).
- **Type signature:** `planOperators(agent_intent: {role, decision_class, entity_ref}, operator_registry: Registry) -> OperatorPlan`.
- **Invariants:** Topological ordering respects composition dependencies; plan generation is deterministic because the registry it reads is deterministic at runtime (INV-CH7-29).
- **Dependencies:** INV-CH7-22..27, INV-CH7-29, §7.5 projection engine (executes the plan).
- **Figures:** Fig-CH07-09 (Planner fan-out across the four worked compositions — design space, not one request's path).
- **Open question:** How the Planner schedules and materializes intermediates (caching policy, reuse decisions for replay invocations) is specified at property level (Fig-CH07-08's reuse note) but not at scheduling-mechanism level; Homecams shows one resolution — do NOT inherit it (CLAUDE.md §2.1). (unnumbered — see Open Questions)

### INV-CH7-29
- **Section:** §7.4.2
- **Commitment:** Two Planner mechanism commitments. (1) The Planner batch-resolves operator references via a DataLoader-style pattern — one query per operator type per call (N+1 avoidance): all Traversal references resolve in one batched call, all Temporal references in another. This amortizes per-operator cost and is how compositions stay within the §7.6 illustrative SLO envelope. (2) The operator registry is import-time / boot-time loaded, and duplicate registration fails fast: registering two operators under the same reference key is a boot-time failure that "prevents the fabric from serving any traffic until the duplicate is resolved" — not a runtime error during a request. The invariant is CI-tested (§7.8 Architectural Invariants carries the broader framing).
- **Type signature:** Registry: boot-time-loaded map of reference key → operator; duplicate key → boot failure.
- **Invariants:** **Boot-time registry with fail-fast duplicate registration** (CI-tested); batched (DataLoader-style) operator resolution.
- **Dependencies:** INV-CH7-28, §7.6 SLO envelope, §7.8 invariants (plan 01-08's key range).
- **Figures:** Fig-CH07-09.
- **Open question:** None.

### INV-CH7-30
- **Section:** §7.4.3–§7.4.6
- **Commitment:** Four worked compositions demonstrate the algebra's design space (each closes on the rebuttal/pitfall it architecturally answers): (a) Covenant cross-reference (unstructured-primary): `Traversal(covenant-of) ∘ Temporal(as-of-T) ∘ Similarity(threshold=0.85)` — Similarity returns passage-level graph anchors (not raw chunks), Temporal selects the active covenant version, Traversal walks covenant-of → defined-by → measured-by; the architectural claim is project-then-retrieve versus RAG's retrieve-then-filter (Rebuttal #11). (b) Intraday liquidity (Temporal-primary): `Temporal(as-of-now) ∘ Traversal(exposure) ∘ Policy(reg-limit)` — bitemporal reconciliation as correctness semantic (Rebuttal #5). (c) AML Policy-before-Similarity (four-operator): `Policy(MNPI + role-entitlement + jurisdiction) ∘ Similarity(threshold=0.75) ∘ Temporal(as-of-decision) ∘ Traversal(transaction-pattern)` — subgraph substitution enforced by Π, structural MNPI-leakage prevention (Rebuttal #13). (d) Credit-exposure traversal (Traversal-primary): `Traversal(relationship-types, depth-limit, materiality-threshold) ∘ Temporal(as-of-now) ∘ Policy(exposure-limit)` — bounded-expansion cost discipline (PITFALLS Zone A3). **Inventory note:** the compositions are domain-flavored worked examples (banking values — thresholds 0.85/0.75, Reg O, FinCEN, MNPI regimes are illustrative configuration, not SDK content); the mechanism commitments they carry are the algebraic forms and the ordering/threshold-as-contract disciplines already keyed at INV-CH7-23..27. Text cites inline decision "D-13 §7.3" in composition (d).
- **Type signature:** The four algebraic forms quoted above, verbatim.
- **Invariants:** As per INV-CH7-23..27; exactly one composition resolves per request (Fig-CH07-09 fan-out shows the design space, not an execution path).
- **Dependencies:** INV-CH7-19 (passage anchors), INV-CH7-20 (topology), INV-CH7-22..27.
- **Figures:** Fig-CH07-09.
- **Open question:** None.

### INV-CH7-31
- **Section:** §7.4.7
- **Commitment:** The determinism bar: "Given same graph state + Control Plane config + temporal boundary + execution plan, the operator composition produces the bit-for-bit same Context Product." A decision made under (G_yesterday, C_yesterday, T_yesterday, P_yesterday) is reconstructible today byte-for-byte. Precision commitment: **determinism is a property of the function, not the value.** The composition is function-deterministic (behaves as a mathematical function on its inputs; the function does not drift between invocations) while the returned value is legitimately time-varying because graph state is time-varying under bitemporal reconciliation and per-signal half-life — "identical inputs to the Temporal operator produce different liquidity snapshots minute-over-minute … and that legitimate value-variance is precisely what the function-deterministic composition is supposed to surface rather than smooth away." §7.7's decay `R(t) = R₀ × (1/2)^((t − t₀) / λ_c)` is the continuous instance of the same property; supersession-as-Policy-event is the discrete-event form. The §7.6 three-mode Assembly Mode model scopes function-determinism differently per mode (Mode 1 whole assembly; Mode 2 algorithmic substrate; Mode 3 orchestration layer) while value-variance handling is identical across modes.
- **Type signature:** Determinism tuple: `(graph_state, control_plane_config, temporal_boundary, execution_plan) → bit-for-bit identical ContextProduct`.
- **Invariants:** **Function-determinism** (with value-variance explicitly permitted and expected); replay reconstructibility.
- **Dependencies:** INV-CH7-23, INV-CH7-27, §7.6 modes and §7.7 half-life (plan 01-07/01-08 key ranges), §7.10.
- **Figures:** Fig-CH07-08.
- **Open question:** None.

### INV-CH7-32
- **Section:** §7.4.9
- **Commitment:** A Context Operator need not be a code-and-pipeline artifact; it may be realized as an agent swarm whose sole job is slot-filling a typed Context Product from the graph (detection, classification, reconciliation, policy-filtered emission) — "under the determinism guarantee that the output contract (the Context Product schema) holds even when the mechanism uses LLM-driven extraction internally." The algebra is the determinism surface; valid realizations include code-and-pipeline, SQL-backed, graph-traversal, and swarm operators — what matters at the typed boundary is that the product emerges with its schema, its λ_c, and its passage-level L intact. The downstream reasoning agent consumes the completed product plus seed context and does not re-assemble context de novo. The assembly/consumption boundary is typed and enforceable — this is what makes multi-agent architectures governable: auditors see two distinct replayable artifacts (assembler swarm's Context Product; reasoning agent's inference trace composed against it) interrogable independently, both bound to the §7.10 five-dimension envelope. Agent-swarm assembly is not retrieval: Policy is composed before Similarity at every step the swarm takes. Mode selection (when to choose swarm assembly per product) belongs to §7.6's Mode 3 — "§7.4 owns the operator-realization mechanism, §7.6 owns the per-product mode-selection decision."
- **Type signature:** Swarm-realized operator honors the same typed output contract (schema + λ_c + passage-level L) as any other realization.
- **Invariants:** Typed assembly/consumption boundary; Policy-before-Similarity holds inside swarm steps; output-contract determinism regardless of internal realization.
- **Dependencies:** INV-CH7-22, INV-CH7-26, §7.6 Mode 3, §7.10.
- **Figures:** None specific.
- **Open question:** None.

### INV-CH7-33
- **Section:** §7.4.10
- **Commitment:** The end-to-end interaction from agent intent to delivered Context Product is committed as a single sequence (counterparty credit exposure, Wholesale Banking worked case): Planner receives intent → resolves required operators against the import-time-loaded registry → fans out four typed operator invocations against the §7.3 topology → Traversal (bounded, materiality) → Temporal (bitemporal as-of-now reconciliation) → Policy before Similarity (canonical inversion) → Similarity (index version pinned in L) → composition-preservation checkpoint `(A ∘ B)(G) = A(B(G))` read by the Planner for intermediate-reuse decisions → Π projects for the role → Context Product Cache wraps the payload under the typed ContextProductContract and writes with TTL, so subsequent requests within the materialization window serve from cache without re-derivation. Fig-CH07-10's caption names the interaction "the operational realization of D-14 algebraic composition, D-15 Operator Plan DAG generator, D-17 determinism, and D-25 ContextProductContract population" (inline D-NN references quoted; catalog is plan 01-11's job).
- **Type signature:** Sequence: intent → OperatorPlan → 4-operator execution in dependency order → Π → contract-validated product → TTL cache write.
- **Invariants:** Composition-preservation observed as a runtime checkpoint; cache serves only contract-validated products within TTL.
- **Dependencies:** INV-CH7-20, INV-CH7-23, INV-CH7-28; §7.5 Π and §7.6 contract (plan 01-07's key range).
- **Figures:** Fig-CH07-10 (end-to-end assembly sequence — the §7.4 → §7.6 bridge).
- **Open question:** None.

---

## Open Questions (unnumbered)

- **Canonical event envelope schema (§7.1, L1).** "every signal tagged with its source, its ingestion timestamp, its observed-time where known, and whatever raw payload the upstream system emitted" — the whitepaper enumerates envelope fields in prose but gives no formal schema. The SDK must commit to a typed L1 envelope contract.
- **Physical collection decomposition (§7.3.1).** "the physical representation maps to ~10 collections" is reference-implementation grounding (Homecams-adjacent), not a normative count. What the SDK's graph-storage Protocol must require of a backend (indexes, supersession semantics, per-relationship-type lineage) versus what stays backend-internal is a design decision. Do NOT inherit the Homecams collection layout as the resolution.
- **Entity Resolver contract (§7.3.5).** Correlation via "shared attributes (the LEI where one exists, registered address and authorized-signatory metadata where it does not)" is a domain-flavored pattern. The SDK needs a general-purpose resolution Protocol; attribute-correlation strategies are user configuration.
- **Operator DAG planner intermediate scheduling (§7.4.2, Fig-CH07-08).** The whitepaper commits the contract — intermediates are persistable, cache-coherent under λ_c-driven invalidation, and reusable for replay ("the Planner reads against [associativity] when it decides whether an intermediate can be reused for a replay invocation") — but does not specify the scheduling/materialization mechanism (when intermediates are cached, eviction, reuse policy). Homecams shows one working resolution; per CLAUDE.md §2.1 it is one data point, not the canonical answer — do NOT inherit.
- **Operator registry population surface (§7.4.2).** "import-time / boot-time loaded" with fail-fast duplicates is committed, but how user-supplied operators register against the SDK's registry (entry points, explicit registration API, config-driven) is unspecified — a general-purpose SDK design choice.
- **Materiality/threshold configuration binding (§7.4.6, §7.4.3).** Thresholds ("configurable floor", `threshold=0.85` / `0.75`) are stated as contract-carried parameters; the whitepaper does not specify where they are declared (Control Plane bundle shape) or how they version. Interacts with the Control Plane configuration surface (§7.8) and the No-Hardcoding Rule (CLAUDE.md §6.4).
