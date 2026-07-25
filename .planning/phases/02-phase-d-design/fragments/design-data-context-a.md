# Data and Context Layer — Part A: The Write Side (L1–L3, Ingress, Single-Writer)

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

**Scope of this fragment.** The fabric's write side: the L1 Signal Layer, the L2 Context Assembly layer, the L3 Context Graph, the ingress patterns that feed them (CDC→G, MCP-client ingress, semantic-layer metadata import, Unstructured Ingestion), and single-writer enforcement. Read-side mechanism (L4–L6, half-life/debt, replay, control/data plane runtime separation) is Part B (`design-data-context-b.md`). Coverage contract: every INV entry assigned to this fragment by `fragments/entry-ownership.md` is cited inline in a component section or listed under Deferred entries. Altitude is contract-level per locked D-07: responsibility, Protocol/type-signature names and key methods, invariants enforced, seams, and D-IMPL rulings embodied — no method bodies, no file layout.

**See-also cross-references honored here.** Two Part-B-owned entries name this fragment as their write-side anchor: INV-CH7-60 (the §7.8 append-only-with-logical-supersession invariant — its graph-side mechanism is §A.3.3/§A.5.2 of this fragment; its runtime-invariant framing is Part B's) and INV-CH7-73 (the §7.8.4 architectural-invariants enumeration whose clause (a), build-time single-writer prevention, is realized by the §A.5.3 enforcement stack; the remaining clauses are Part B's). One `design-experience-seams.md`-owned entry, INV-CH8-24 (coexistence/layering onto existing estates), anchors its ingress-side half in §A.4's non-invasive pattern designs.

---

## A.0 Conceptual Foundations (Chapter 5 commitments the write side realizes)

The write side is where the whitepaper's conceptual commitments become persisted mechanism. The Chapter 5 commitments governing every component below, each with its design consequence:

- **Three-tier enterprise architecture** (INV-CH5-01): the fabric occupies Tier 3 (Cognition) above Record and Signal Generation tiers. L1–L3 are the machinery by which Tier 3 represents state without absorbing Tiers 1–2.
  - *Design consequence:* no SDK component below opens a write path into a Tier 1/2 system; ingress adapters are strictly read/subscribe-side (§A.4).
- **Data-perspective vs context-perspective boundary** (INV-CH5-02): systems below the fabric answer data questions; the graph exists to answer context questions. The six-tuple verdicts against knowledge catalogs (E HIT / R HIT / T MISS / P MISS / Π MISS / L PARTIAL) define exactly what L2/L3 must add rather than duplicate.
  - *Design consequence:* the T/P/Π/L dimensions are where the SDK's write side spends its mechanism budget; E/R import leans on existing substrates via Pattern 2 (§A.4.3) and the four-tier composition (INV-CH8-11).
- **The six-tuple `G(E, R, T, P, Π, L)`** (INV-CH5-03) with **per-dimension semantics and necessity tests** (INV-CH5-04): all six dimensions are mandatory; removal of any one produces a named, testable failure mode.
  - *Design consequence:* the SDK's `ContextGraph` state primitive declares all six structurally (§A.5.1), and the Phase I test strategy must exercise the per-dimension failure modes as negative tests — a design obligation recorded for Phase F's test-strategy chapter.
- **Dynamic context vs dynamic content** (INV-CH5-05) and **derived-not-stored / project-then-retrieve** (INV-CH5-07): the graph persists context state; Context Products are projected at decision time, never stored as the system of record.
  - *Design consequence:* the write side persists *graph state*, and only graph state — product materialization is a read-side cache concern (Part B), never a second write path.
- **Core thesis — context, not data, is the unit of decision-making** (INV-CH5-06): the write side's job is to convert data-shaped signal into context-shaped state.
  - *Design consequence:* this is the design rationale for L1's non-interpretation rule (§A.2) and L2's four converging concerns (§A.3.1) — the conversion happens exactly once, at assembly, under policy.
- **Composition above, not replacement** (INV-CH5-08): the fabric composes over warehouses, lakehouses, mesh nodes, and operational systems.
  - *Design consequence:* every ingress pattern in §A.4 is sidecar by construction; no component acquires a write path into a source system; source migration changes ingestion bindings, never fabric architecture (INV-CH8-01).
- **Five-component fabric architecture** (INV-CH5-09): the named Cognitive Context Fabric decomposes into the layered stack this fragment and Part B jointly design.
  - *Design consequence:* the SDK package structure mirrors the decomposition (§A.1) so the whitepaper's architectural vocabulary is legible in the code layout.
- **Prior art and claimed novelty boundary** (INV-CH5-10): typed six-axis state + operator algebra + governed delivery is the claimed-novel composition.
  - *Design consequence:* each of those three surfaces stays a distinct SDK mechanism (graph primitive, operator algebra in Part B, product contract in Part B) rather than collapsing into a retrieval library — the novelty boundary is preserved by module boundary.

---

## A.1 Layered Architecture Frame (L1–L6, two planes)

- **Responsibility:** Fix the responsibility boundaries this fragment designs within. The fabric decomposes into six layers — L1 Signal → L2 Assembly → L3 Graph → L4 Operators → L5 Projection → L6 Products — each owning a single responsibility, artifact, and handoff (INV-CH7-01, Fig-CH07-02). The layers are responsibility boundaries, not a sequential pipeline. Orthogonally, the fabric realizes four concerns — State (§7.3), Computation (§7.4), Interpretation (§7.5), Delivery (§7.6) — as complementary views of one architecture (INV-CH7-09).
- **Protocol/type signatures:** The SDK package structure mirrors the layer stack (CLAUDE.md §10): `ccf.signal` (L1), `ccf.assembly` (L2), `ccf.graph` (L3), with L4–L6 modules designed in Part B. The layered view is realized as module boundaries plus the DI composition root (§A.5), not as a runtime pipeline object.
- **Invariants enforced:** Layer-boundary discipline — L4 operators are read-only (INV-CH7-11, mechanism in Part B), interpretation is isolated at L5 (INV-CH7-06), delivery happens only via the contracted artifact at L6 (INV-CH7-07, INV-CH7-13). This fragment's write side guarantees the complementary half: nothing above L2 writes graph state (§A.5). L4/L5/L6 layered-view commitments (INV-CH7-05, INV-CH7-06, INV-CH7-07) and the three per-concern mechanism entries for Computation/Interpretation/Delivery (INV-CH7-11, INV-CH7-12, INV-CH7-13) bind here at the boundary and are designed in mechanism detail in Part B (see-also per the ownership table).
- **Seams:** Control Plane and Data Plane cut across all six layers (INV-CH7-08): policy definitions binding L2, operator parameterization, λ_c calibration, D_c thresholds, and materialization policy are Control Plane configuration; L1 ingestion, L2 assembly, and L3 persistence execute on the Data Plane within those constraints. Runtime plane-separation mechanism is Part B (§7.8 entries); this fragment consumes the separation as a design constraint — every threshold or table named below is a Control Plane value, never SDK code (No-Hardcoding, CLAUDE.md §6.4).
- **D-IMPL rulings embodied:** D-IMPL-01 (Python 3.12+ sole target; typed contracts as Pydantic v2 `extra=forbid`; Protocol-based seams — every signature below assumes it); D-IMPL-04 (two packages, `ccf` library + `ccf-runtime`; fabric core stays sync on the operator path, ingestion adapters may be async in the runtime package).

### A.1.1 Layer handoff summary (write side)

| Layer | Responsibility | Handoff artifact | Owning section | Key entries |
|-------|----------------|------------------|----------------|-------------|
| L1 Signal | ingestion + normalization, no interpretation | `SignalEnvelope` stream | §A.2 | INV-CH7-02 |
| L2 Assembly | resolution, stitching, policy binding, operator invocation; sole writer | graph mutations via `GraphWriter` | §A.3, §A.5.3 | INV-CH7-03, INV-CH7-10 |
| L3 Graph | persisted six-tuple state | `GraphReader` views to L4+ | §A.5 | INV-CH7-04, INV-CH7-14..21 |
| L4 Operators | read-only typed composition | operator plans / subgraph productions | Part B | INV-CH7-05, INV-CH7-11 |
| L5 Projection | Π role-conditioned interpretation | principal-conditioned payloads | Part B | INV-CH7-06, INV-CH7-12 |
| L6 Products | contracted delivery | typed Context Products | Part B | INV-CH7-07, INV-CH7-13 |

---

## A.2 L1 — Signal Layer

### A.2.1 The `SignalEnvelope` contract

- **Responsibility:** Ingestion and event normalization (INV-CH7-02). Heterogeneous sources — transactions, operational events, documents, audio transcripts, external feeds — are expressed in one canonical event envelope. L1 does not interpret: signals carry provenance and temporal markers but no entity/relationship typing. Structured and unstructured streams are co-equal at the ingestion boundary.
- **Protocol/type signatures:** `SignalEnvelope` — a Pydantic v2 `extra=forbid` contract per the D-IMPL-33 ruling: `source` (structured source identity), `ingestion_timestamp`, `observed_time` (optional), `raw_payload` (typed opaque-to-L1), plus `tenant_id` (no untenanted path, INV-CH7-16), an SDK-assigned `envelope_id` (lineage anchoring against the L axis, INV-CH7-14), and an opaque `source_metadata` extension block. Source adapters implement a `SignalSourceProtocol` whose single obligation is emitting valid envelopes; the envelope is the L1→L2 handoff artifact.
- **Invariants enforced:** L1 does not interpret (opaque payload typing makes interpretation structurally unavailable, not merely discouraged); no entity/relationship typing at L1; unstructured and structured co-equal at ingress; every envelope tenant-scoped and lineage-addressable from birth.
- **Seams:** `SignalSourceProtocol` is the pluggable ingress seam — CDC adapters, MCP-source adapters, file/stream adapters, and the Pattern 5 pipeline all terminate in envelope emission (§A.4). Envelope ids are the terminus the D-IMPL-44 re-hydration recipe references (Part B).
- **D-IMPL rulings embodied:** D-IMPL-33 (envelope schema as ruled — the whitepaper-enumerated core plus `tenant_id`, `envelope_id`, `source_metadata`, `extra=forbid`); D-IMPL-05 (tenant first-class in the envelope; single-tenant is the degenerate one-fixed-tenant case, never a separate mode).

### A.2.2 `SignalSourceProtocol` (the ingress adapter seam)

- **Responsibility:** The single seam every ingress mechanism implements — CDC (§A.4.1), MCP-source (§A.4.2), semantic-layer import (§A.4.3), Pattern 5 persistence stage (§A.4.4), and user-supplied file/stream adapters. An adapter's whole contract is: connect to a source, emit valid `SignalEnvelope`s, report source identity. It carries no graph access of any kind.
- **Protocol/type signatures:** `SignalSourceProtocol` with envelope emission as the sole output surface; adapters run in `ccf-runtime` (async per D-IMPL-04(b)) while the envelope contract lives in the `ccf` library so both packages share one type.
- **Invariants enforced:** Adapter isolation — an ingress adapter cannot reach L3 (it holds neither `GraphReader` nor `GraphWriter`); source identity recorded per envelope so L records *identity, not location* (INV-CH8-01 source-neutrality); tenant scope required on every emission (INV-CH7-16).
- **Seams:** This is the primary user-extension point on the write side: adopting a new source class means implementing one Protocol, registering it in deployment configuration, and touching nothing else — the ingestion-binding-not-architecture consequence of INV-CH8-03.
- **D-IMPL rulings embodied:** D-IMPL-04 (runtime-package placement); D-IMPL-33 (envelope as the only output type); D-IMPL-05 (tenant-scoped emission).

---

## A.3 L2 — Context Assembly

### A.3.1 The four converging concerns

- **Responsibility:** Assembly is where four concerns converge (INV-CH7-03): (1) **semantic resolution** — entity/relationship extraction from the signal stream; (2) **temporal stitching** — observed-time vs valid-time reconciliation producing as-of views with no future-information leakage into historical queries; (3) **policy binding** — principal scope, jurisdiction, and entitlement state attached to every resolved subgraph *at assembly time* ("the fabric does not resolve entities first and then ask who can see them"); (4) **operator invocation** — Context Operators execute here, producing subgraph productions (operator mechanism itself is Part B). L2 is the stage the Algorithmic ⇄ Semantic Alternation actually crosses (INV-CH7-03): both algorithmic structure (traversal, temporal reconciliation) and semantic structure (entity extraction, relationship inference) are active, so L2's internal stages carry the `@algorithmic` lint tags where they are algorithmic (CLAUDE.md §11) — the semantic stages are the only ones permitted an `LLMClientProtocol` dependency (D-IMPL-09).
- **Protocol/type signatures:** An `AssemblyWorker` component in `ccf.assembly` is the sole holder of the `GraphWriter` handle (§A.5). Its sub-stages are Protocol seams, not subclasses: `EntityResolutionStrategy` (below), a temporal-stitching stage operating on the bitemporal T axis, a policy-binding stage that resolves the in-force policy bundle version from the Control Plane and stamps it onto every resolved subgraph, and the operator-invocation surface (Part B).
- **Invariants enforced:** Scope/policy bound at assembly time, never post-processed; no future-information leakage into as-of views; every graph mutation flows through this component and no other (single-writer, §A.5).
- **Seams:** Reads envelopes from L1; writes exclusively through `GraphWriter` (D-IMPL-34 interface split); consumes Control Plane policy bundles and λ_c tables as versioned configuration; A2A admissions enter here after consumer-side Control Plane verification (INV-CH8-08 — admission never bypasses L2; the A2A surface itself is designed in `design-experience-seams.md`).
- **D-IMPL rulings embodied:** D-IMPL-41 (Assembly is the one component constructed with a `GraphWriter`); D-IMPL-09 (semantic sub-stages reach LLMs only through `LLMClientProtocol`).

### A.3.2 Entity resolution

- **Responsibility:** Converge fragmented native identifiers from disparate source systems onto a single canonical E node under a tenant-scoped URI, with unstructured claims participating as first-class evidence on par with structured identifiers (INV-CH7-21, Fig-CH07-06).
- **Protocol/type signatures:** `EntityResolutionStrategy` Protocol per the D-IMPL-35 ruling: candidate correlation over *user-declared* identity attributes → canonical `entity-class://` URI (INV-CH7-18 naming forms: `entity-class://<identity-hash>` or `entity-class://<principal>-<discriminator>`), with set-union lineage accumulation on merge. The SDK ships a reference deterministic attribute-correlation strategy driven by user-declared ontology configuration; correlation attribute sets, precedence rules, and probabilistic matching are user configuration or plugins — never SDK values (the whitepaper's LEI/registered-address examples are domain illustration, INV-CH7-21).
- **Invariants enforced:** Canonical-E convergence regardless of querying line of business; URI stability across source-system change with the URI → source-native-identifier mapping preserved in L (INV-CH7-18); resolution is always tenant-scoped (INV-CH7-16).
- **Seams:** Strategy is pluggable per deployment; the Semantic Layer ontology import (Pattern 2, §A.4.3) supplies the disambiguation vocabulary the reference strategy correlates against.
- **D-IMPL rulings embodied:** D-IMPL-35 (mechanism shipped, correlation values user-supplied).

### A.3.3 Temporal stitching and supersession

- **Responsibility:** Reconcile observed-time against valid-time structurally (not as a retention heuristic), and enact supersession as a logical event: a superseding observation attaches a `superseded_by` edge and `superseded_at` timestamp to the prior claim, which remains in the graph (INV-CH7-21, Fig-CH07-05). Overwrite-in-place is prohibited — it "would make Decision Replay at T+2 years structurally impossible."
- **Protocol/type signatures:** Supersession record shape: prior claim + `superseded_by` edge + `superseded_at` timestamp, required of every `GraphStore` backend by the D-IMPL-34 Protocol surface (semantic 3). Bitemporal T axis: (valid-time, observed-time) per INV-CH7-14.
- **Invariants enforced:** Append-only-forward-with-supersession (INV-CH7-04, INV-CH7-21); as-of reads against T_prior re-render prior state exactly; supersession events are themselves analyzable state (they feed the Policy-event cascade Part B designs against λ_c invalidation).
- **Seams:** Supersession-as-Policy-event is consumed by Part B's half-life/debt machinery and D-IMPL-36 intermediate invalidation.
- **D-IMPL rulings embodied:** D-IMPL-34 (supersession + bitemporal reads are Protocol requirements, not backend conventions).

---

## A.4 Ingress Patterns (the non-invasive surface)

The five integration patterns are co-deployed, not alternatives, and every one is sidecar by posture and deployment (INV-CH8-04): the fabric references source-of-record data via L, never replaces sources, and blast radius is bounded by the sidecar boundary. This posture realizes the layering-not-replatforming principle (INV-CH8-03, Fig-CH08-01) against the structurally plural, mid-migration estate that is the operating state, not a transition state (INV-CH8-01). What the estate lacks — and the fabric produces alongside it — is the decision substrate that closes the Forensic Data Gap: policy version in force, supervisory context, freshness at action time, role-conditioned view (INV-CH8-02). Where the estate includes a productized knowledge-catalog substrate, the fabric composes over it per the four-tier pattern with six Tier-2 ⇄ Tier-3 integration mechanics — critically, catalog access-control signals are P *signal*, never P *enforcement*, which stays at Tier 3 (INV-CH8-11).

All ingress terminates in `SignalEnvelope` emission; nothing in this section acquires a write handle (§A.5).

### A.4.1 Pattern 1 — CDC→G reference ingress

- **Responsibility:** Preferred ingress for transactional systems of record: Debezium-style CDC streams committed transactions from the source's write-ahead log; Assembly normalizes each change into a typed entity/relationship upsert keyed on `(tenant_id, entity_uri)` (INV-CH8-05). The source is undisturbed — no query-path coupling, no schema coupling.
- **Protocol/type signatures:** A `CDCSourceAdapter` implementing `SignalSourceProtocol`, shipped as the v0 reference ingress (CLAUDE.md §13); change events map to envelopes with `observed_time` from the transaction commit and `source` identifying the source system, not its location (INV-CH8-01 source-neutrality).
- **Invariants enforced:** Non-invasiveness is architectural — CDC never touches the source's query path; all resulting writes enter the graph through Assembly only (INV-CH8-05, single-writer).
- **Seams:** Runtime-package concern (async ingestion loop per D-IMPL-04(b)); the specific CDC transport is deployment infrastructure, not SDK mechanism.
- **D-IMPL rulings embodied:** D-IMPL-33 (envelope as the normalization target); D-IMPL-04 (async ingestion in `ccf-runtime`).

### A.4.2 MCP-client ingress (SDK extension, CLAUDE.md §7.1)

- **Responsibility:** Query-based acquisition from content-rich systems (calendars, document repositories, communications archives) via MCP servers front-ending the sources — complementary to CDC (transactional capture). SDK-defined extension of Pattern 3, labeled as such (INV-CH8-07 records the whitepaper's export-only framing and the SDK's bidirectional extension).
- **Protocol/type signatures:** One `ccf` MCP client library serving both L1 ingress and L4–L5 content acquisition per the D-IMPL-13 ruling; at L1 an `MCPSourceAdapter` normalizes MCP resource reads into `SignalEnvelope`s. The client and the egress server live in different modules with different trust postures (INV-CH8-07).
- **Invariants enforced:** Acquisition results reach L3 only via L2 (D-IMPL-13 ruling text); the envelope discipline applies unchanged — MCP-acquired content receives no interpretation privilege at L1.
- **Seams:** The same client surface serves decision-time content acquisition at L4–L5 (Part B); egress and ArtifactStore MCP roles are designed in `design-experience-seams.md`.
- **D-IMPL rulings embodied:** D-IMPL-13 (five-edge MCP role allocation; single client library, two ingress roles).

### A.4.3 Pattern 2 — semantic-layer metadata import

- **Responsibility:** Read through existing semantic-layer investments (dbt, Cube, AtScale, proprietary): metric, dimension, and relationship definitions import as typed entity shapes in G, binding canonical dimensional vocabulary to the E and R registries; domain event streams carrying semantic-layer-shaped events import as metadata events via the same mechanism (INV-CH8-06). Existing semantic-layer consumers are unaffected — the fabric is an additional consumer.
- **Protocol/type signatures:** A `SemanticLayerImportAdapter` implementing `SignalSourceProtocol`; imported definitions land as ontology-vocabulary entities the `EntityResolutionStrategy` reference implementation correlates against (§A.3.2). Which semantic-layer product is bound is deployment configuration, not SDK mechanism.
- **Invariants enforced:** Reads-through, never replaces (INV-CH8-06); imported vocabulary is candidate structure typed at L2, consistent with the Tier-2-candidates / Tier-3-load-bearing rule (INV-CH8-11 mechanic 2).
- **Seams:** Feeds the user-declared ontology configuration surface that D-IMPL-35 resolution strategies consume.
- **D-IMPL rulings embodied:** D-IMPL-35 (ontology config as the correlation vocabulary's home).

### A.4.4 Pattern 5 — Unstructured Ingestion pipeline

- **Responsibility:** Make document-, audio-, and chat-shaped signal first-class citizens of the graph via the six-stage pipeline: parse → chunk → embed → Policy-before-Similarity retrieval → typed entity/relationship extraction with passage-level source references → graph-persist with passage-level L bound to every edge (INV-CH8-09, Fig-CH08-02/03). Extraction happens at ingestion time, not retrieval time: "the Graph is built from unstructured content, not consulted from it" (INV-CH7-19) — the architectural distinction from RAG.
- **Protocol/type signatures:** Per the D-IMPL-08 ruling, each stage is a Protocol with one opinionated reference pipeline wired from the reference implementations: parser, chunker, embedder (`EmbedderProtocol` per D-IMPL-07, with `(model_id, model_version)` reporting), retrieval (Policy Operator before Similarity Operator, structurally ordered), extraction (`PassageCitationProvider` per D-IMPL-46, designed in Part B's replay context), persistence (through L2/`GraphWriter` only). Passage-level L anchor shapes: `{document, page, paragraph, offset_span}` for documents, `{transcript_id, timestamp, text_span}` for transcripts (INV-CH7-19). The reference-stack vendor choices the whitepaper names (LlamaParse/Docling, voyage-finance-2/BGE-M3) are Control Plane substitution values, never SDK mechanism; what is architectural is the dispatch axis (cloud-agentic vs on-prem-sensitive, decided by data-classification policy), Policy-before-Similarity ordering, typed extraction, and passage-level L binding (INV-CH8-10).
- **Invariants enforced:** Policy-before-Similarity enforced in the retrieval tier as structure, not post-hoc filter (INV-CH8-09); passage-level L on every extracted edge (INV-CH7-19); Mode 1 purity — no LLM invocation in any assembly stage of the pipeline itself (INV-CH8-09; the `@algorithmic` lint's per-stage enforcement targets per the D-IMPL-08 ruling); the fabric never becomes record-of-record for regulated archives — it references WORM archives via L (INV-CH8-10).
- **Seams:** Stage Protocols express the mode variance of the Alternating Derivation Pipeline (INV-CH8-12 — owned by `design-agent-types.md`; the ingestion substrate is this pipeline); embedder and citation-provider Protocols are shared with Part B's similarity and replay machinery.
- **D-IMPL rulings embodied:** D-IMPL-08 (stage Protocols + opinionated reference pipeline); D-IMPL-07 (EmbedderProtocol with version identity); D-IMPL-46 (citation provider by reference).

---

## A.5 L3 — Context Graph and Single-Writer Enforcement

### A.5.1 The `ContextGraph` state primitive

- **Responsibility:** First-class persisted computational primitive — not a cache, not a denormalized view, not an application abstraction (INV-CH7-15, INV-CH7-04). Holds the six-tuple `G(E, R, T, P, Π, L)` in mechanism form (INV-CH7-14, Fig-CH07-03/04): E as URI-addressable nodes with identity persistent across sources and time; R as typed first-class persisted relationships, never derived joins; T bitemporal (valid-time, observed-time); P as policy state traveling with every subgraph; Π as role-conditioned materialized projection state; L as append-only lineage with passage-level anchors for unstructured content. The graph accumulates enrichments across pipeline stages — later passes attach rather than recompute; downstream stages append rather than reconstruct (INV-CH7-15). §8.5's domain lens confirms the primitive is archetype-invariant: different agentic-work archetypes weight the six dimensions differently while the graph primitive stays the same, and L records source identity, not source location — migration-proof by construction (INV-CH8-13, INV-CH8-01).
- **Protocol/type signatures:** Base `ContextGraph` type declaring the six-tuple structure, single-writer write path, lineage-accumulation semantics, and supersession-not-deletion invariant; deployments extend entity-class and relationship-type *enumerations* within that shape via configuration — the whitepaper's banking topology (counterparty/facility/guarantee graph, INV-CH7-20) is a worked domain instantiation demonstrating the mechanism commitments (subclassing shape, per-relationship-type lineage, materiality-as-thresholded-relationship, policy-intersection-at-resolution-time), never SDK content.
- **Invariants enforced:** All six axes persisted as first-class surfaces read simultaneously by every operator composition — not independent graphs stitched query-side (INV-CH8-13); L append-only (INV-CH7-14); append-only-forward-with-supersession (INV-CH7-04).
- **Seams:** Persistence via the `GraphStore` Protocol below; read access via `GraphReader` to L4+ (Part B); hot graph state stays on the graph store, never the ArtifactStore (D-IMPL-27 mutability rule, designed in Part B / `design-experience-seams.md`).
- **D-IMPL rulings embodied:** D-IMPL-02 (Protocol + Postgres reference + SQLite-for-dev); D-IMPL-05 (tenancy structural).

### A.5.2 The `GraphStore` Protocol (storage seam)

- **Responsibility:** Carry the invariant semantics substrate-neutrally; leave all physical layout backend-internal (the whitepaper's "~10 collections" is reference grounding, not a normative count — INV-CH7-15).
- **Protocol/type signatures:** Per the D-IMPL-34 ruling, the Protocol requires exactly six invariant semantics: (1) compound uniqueness on `(tenant_id, entity_uri)` at the persistence tier (INV-CH7-16); (2) idempotent upsert with set-union lineage accumulation (INV-CH7-17); (3) logical supersession with `superseded_by`/`superseded_at` and as-of reads (INV-CH7-21); (4) append-only-forward (INV-CH7-04); (5) per-relationship-type edge lineage (INV-CH7-20); (6) bitemporal read support (INV-CH7-14). Backend-internal: collection/table decomposition, indexing strategy, partitioning. The Protocol exposes **separate `GraphReader` and `GraphWriter` interfaces** — the seam D-IMPL-41 enforcement hangs on. A Protocol conformance test suite verifies all six semantics against both D-IMPL-02 reference implementations.
- **Invariants enforced:** **Tenant invariant** — no code path resolves an entity without tenant scope; uniqueness enforced at the persistence tier, not the application layer (INV-CH7-16). **Idempotent upsert** — the same observation arriving twice produces exactly one persisted entity record; **set-union lineage accumulation** — lineage is deliberately NOT idempotent: multi-source evidence accumulates with per-source timestamps and passage anchors, never overwritten (INV-CH7-17).
- **Seams:** Reference implementations: Postgres (production posture) and SQLite (dev — load-bearing for the §9 examples discipline, per the D-IMPL-02 rationale).
- **D-IMPL rulings embodied:** D-IMPL-34 (six-semantics requirement surface; reader/writer split); D-IMPL-02 (backends); D-IMPL-05 (compound-index tenancy).

### A.5.3 Single-writer enforcement (the D-IMPL-41 stack)

- **Responsibility:** Make "only the Assembly worker holds a write handle to the graph" an enforced architectural property, not a convention (INV-CH7-10): every read-path service is constructed without a write handle, the absence enforced by dependency injection at boot rather than runtime discipline. Deterministic state transitions are the precondition for deterministic replay — if any read-path component could write, graph history would be contaminated by non-Assembly transitions Decision Replay could not reconstruct.
- **Protocol/type signatures:** The four-layer enforcement stack per the D-IMPL-41 ruling: (1) **interface split** — separate `GraphReader`/`GraphWriter` Protocols (D-IMPL-34); read-path constructors accept only `GraphReader`, so write-handle absence is a structural property of the constructor signature (INV-CH7-15); (2) **DI-at-boot** — the composition root constructs exactly one `GraphWriter` and injects it into L2/Assembly only; (3) **static gate** — strict mypy in CI rejects non-L2 `GraphWriter` type references, plus an import lint (same machinery as the `@algorithmic` and harness lints) forbidding the writer module's import outside L2 and the composition root; CI failure is build failure — Python's honest equivalent of build-time prevention; (4) **runtime backstop** — the writer handle is constructed with a boot-time token only the composition root can mint. The residual-honesty note (Python cannot make determined-insider evasion impossible; the claim strength is "no unforced path exists and every forced path fails CI or fails at boot") lands in DESIGN.md's Invariant Preservation chapter per the ruling.
- **Invariants enforced:** **Single-writer enforcement at boot** — the named architectural invariant (INV-CH7-10, INV-CH7-15). The invariant holds across every boundary that might otherwise erode it: **A2A admission** — an inbound A2A Context Product is verified at the consumer's Control Plane and then enters L3 only through L2, never directly (INV-CH8-08; CLAUDE.md §10); **harness effect capture** — no harness ever acquires a write handle; adapter effect capture routes through governed emission or L2 write-back (CLAUDE.md §7.3 seam 3; D-IMPL-25's `effects: unsupported` declaration is a verified capability, not an unimplemented seam); **ArtifactStore** — the store is a persistence substrate behind mechanism, never a second writer (CLAUDE.md §7.4); **HTTP surface** — L1 ingestion is deliberately absent from the v0 HTTP API because a generic write endpoint would invite a second writer path (D-IMPL-23 ruling).
- **Seams:** The composition root is the one place `GraphWriter` is visible outside `ccf.assembly`; the write path is rendered in `docs/diagrams/seq-single-writer-write-path.mmd` (D-09 sequence diagram, this plan's Task 2).
- **D-IMPL rulings embodied:** D-IMPL-41 (the stack itself); D-IMPL-34 (the interface seam); D-IMPL-25 and D-IMPL-23 (boundary-preserving rulings cited above); D-IMPL-16 (verify-every-admission — no fast path that could weaken the L2-only entry).

---

### A.5.4 The write path, end to end

The complete write path — rendered as the D-09 sequence diagram in `docs/diagrams/seq-single-writer-write-path.mmd` — composes the components above into the one route by which anything becomes graph state:

1. **Signal arrives.** A source event reaches an ingress adapter: CDC change event (§A.4.1), MCP resource read (§A.4.2), semantic-layer definition (§A.4.3), or an unstructured document entering the Pattern 5 pipeline (§A.4.4).
2. **L1 normalizes.** The adapter emits a `SignalEnvelope` (D-IMPL-33): tenant-scoped, lineage-addressable, payload opaque. No interpretation has occurred (INV-CH7-02).
3. **L2 assembles.** The Assembly worker runs the four concerns in sequence for the affected substate: entity resolution via `EntityResolutionStrategy` (INV-CH7-21, D-IMPL-35), temporal stitching against the bitemporal T axis (INV-CH7-03), policy binding stamping the in-force Control Plane bundle version onto the resolved subgraph (INV-CH7-03), and — on the read side of assembly — operator invocation (Part B).
4. **L3 persists.** The single `GraphWriter` handle executes an idempotent upsert keyed on `(tenant_id, entity_uri)` (INV-CH7-16, INV-CH7-17); lineage accumulates by set-union; superseded claims receive `superseded_by`/`superseded_at` edges and remain (INV-CH7-21, INV-CH7-60).
5. **Refused paths.** Two boundary cases demonstrate the invariant rather than merely asserting it: an inbound A2A Context Product must pass consumer-side Control Plane verification (D-IMPL-16) and then enters the graph *through L2 as an admission*, never via a direct L3 write (INV-CH8-08); a harness attempting effect capture finds no write handle in existence outside the Assembly worker — its outputs route through governed emission or L2 write-back (D-IMPL-25), and a conforming read-only adapter declares `effects: unsupported` as a verified capability.

Every step is deterministic given the envelope stream and the in-force Control Plane versions — which is precisely what makes the write path replayable (INV-CH7-10) and the D-IMPL-44 re-hydration recipe (Part B) expressible as envelope ids + pinned versions.

---

## A.6 Design Constraints Carried Forward

Constraints this fragment's design imposes on sibling fragments, so synthesis (plan 02-10) can verify seam consistency:

- **Part B (L4–L6, replay):** `GraphReader` is the only graph access L4+ receives (§A.5.2/§A.5.3); operator purity (INV-CH7-11) is therefore structurally assisted — there is nothing to mutate through. Supersession events (§A.3.3) are the invalidation input for λ_c cascade and D-IMPL-36 intermediate caches. `envelope_id` (§A.2.1) is the terminus the D-IMPL-44 recipe references.
- **`design-agent-types.md`:** The Alternating Derivation Pipeline (INV-CH8-12) consumes the Pattern 5 stage Protocols (§A.4.4) as its Perception substrate; archetype fabric-interaction patterns never include a write handle.
- **`design-orch-hitl.md`:** Workflow and HITL state persist at the Control Plane boundary (D-IMPL-18), not in the graph — nothing in orchestration touches `GraphWriter`.
- **`design-experience-seams.md`:** The A2A admission seam terminates at L2 (§A.5.4 step 5); the MCP client library is shared between L1 ingress (this fragment) and L4–L5 acquisition plus Experience surfaces (that fragment) per D-IMPL-13; the ArtifactStore never holds live graph state (D-IMPL-27) and never becomes a second writer; the v0 HTTP API carries no ingestion endpoint (D-IMPL-23).

---

## A.7 Owned-Entry Coverage

All 41 entries assigned to this fragment by `fragments/entry-ownership.md` are cited above, plus the three see-also keys whose rows name this fragment (INV-CH7-60, INV-CH7-73, INV-CH8-24 — anchored in the scope note and §A.3.3/§A.5.3/§A.4 respectively): INV-CH5-01, INV-CH5-02, INV-CH5-03, INV-CH5-04, INV-CH5-05, INV-CH5-06, INV-CH5-07, INV-CH5-08, INV-CH5-09, INV-CH5-10 (§A.0); INV-CH7-01, INV-CH7-08, INV-CH7-09 (§A.1); INV-CH7-02 (§A.2); INV-CH7-03 (§A.3); INV-CH7-05, INV-CH7-06, INV-CH7-07, INV-CH7-11, INV-CH7-12, INV-CH7-13 (§A.1 — layered-view/concern commitments bound at the boundary; mechanism detail in Part B per the ownership see-also); INV-CH7-04, INV-CH7-10, INV-CH7-14, INV-CH7-15, INV-CH7-16, INV-CH7-17, INV-CH7-18, INV-CH7-19, INV-CH7-20, INV-CH7-21 (§A.3, §A.4.4, §A.5); INV-CH8-01, INV-CH8-02, INV-CH8-03, INV-CH8-04, INV-CH8-05, INV-CH8-06, INV-CH8-09, INV-CH8-10, INV-CH8-11, INV-CH8-13 (§A.4, §A.5). Deferred entries: none.

All D-IMPL rulings cited in this fragment (01, 02, 04, 05, 07, 08, 09, 13, 16, 23, 25, 27, 33, 34, 35, 41, 44, 46) are RESOLVED in `docs/DECISIONS.md`; no section of this fragment rests on a PROVISIONAL ruling.
