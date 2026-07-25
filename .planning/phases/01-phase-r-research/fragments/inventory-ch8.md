# Inventory Fragment — Whitepaper Chapter 8 (Enterprise Integration)

**Canonical authority:** `docs/CCF_Whitepaper_1-2.md` (the converted `.md` is authoritative; all citations reference its sections, never the PDF — locked D-01). Where CLAUDE.md commits SDK extensions beyond the whitepaper, those notes are labeled **SDK-defined** and cite CLAUDE.md sections.

**Scope:** §8.1–§8.13 (13 subsections), all five integration patterns individually cataloged. Keys: `INV-CH8-NN`. Extraction per D-03 gate (`spotcheck-report.md` VERDICT: PASS).

---

### INV-CH8-01 — Architectural reality: heterogeneity is the operating state

- **Whitepaper section:** §8.1
- **Commitment (paraphrase):** A Tier-1 bank's estate is structurally plural — warehouses, medallion lakehouses, Data Mesh nodes, cloud lakes, operational systems of record, communications-compliance archives, WORM legal-hold systems — and mid-migration. Heterogeneity is not a transition state; it is *the* state. Any architecture that requires estate consolidation as a precondition is misaligned. The fabric must read from pre-migration, post-migration, and both-during-transition sources without re-architecture; the graph's dimensions are source-neutral by design.
- **Type signature:** None given (posture commitment, not mechanism).
- **Invariants:** Source-neutrality of graph dimensions (a source migration changes ingestion bindings, never fabric architecture); L records source identity, not source location.
- **Dependencies:** §8.5 Lineage paragraph (D-21) makes source-neutrality visible at graph level; §1.2 Forensic Data Gap; §8.2 posture.
- **Figure refs:** None.
- **Open question:** None.

### INV-CH8-02 — The Forensic Data Gap as the capability the estate lacks

- **Whitepaper section:** §8.1
- **Commitment (paraphrase):** Existing systems of record capture decision *outcomes* well but not the situational substrate of decisions (policy version in force, supervisory context, signal freshness/staleness at action time, missing signals, role-conditioned view). Closing the Forensic Data Gap is a capability existing systems structurally do not carry; the fabric produces it alongside them without replatforming.
- **Type signature:** None given.
- **Invariants:** The "why" must be bound to policy, time, perspective, and lineage with the mathematical discipline of Ch 7 — agents cannot reason reliably on outcome-only records.
- **Dependencies:** Ch 1 §1.2 (names the gap); Ch 7 mechanism chapters; §8.2 layering posture.
- **Figure refs:** None.
- **Open question:** None.

### INV-CH8-03 — Layering, not replatforming (central design principle)

- **Whitepaper section:** §8.2
- **Commitment (paraphrase):** The fabric does not replace the warehouse, lakehouse, Data Mesh, semantic layer, or feature store; it composes over them and produces the decision-substrate properties (policy binding, temporal reasoning, perspective conditioning, passage-level lineage) they were not designed to produce. It does not demand these properties from below; it produces them on top. Source changes propagate through ingestion updates, never through re-architecting the fabric. Four archetypes of agentic work (Document-Heavy Compositional, Temporal Reconciliation, Forensic-Defensibility, Conversational Synthesis) organize the chapter; the posture holds across all four.
- **Type signature:** None given.
- **Invariants:** Coexistence over replacement is a constraint on every architectural choice (what the fabric reads, writes back, replaces, leaves untouched); the moving estate is an ingestion-layer concern, not an architectural one.
- **Dependencies:** §8.1 (the reality being layered over); §8.3 integration patterns (the composition mechanism); §8.4/§8.6/§8.9/§8.10 (archetype walkthroughs); Fig-CH08-01.
- **Figure refs:** Fig-CH08-01 (layering posture: legacy tier and Data Mesh tier structurally unchanged; Perception layer = Pattern 1–5 ingress; Comprehension/Reasoning boundary = the §7.6 algorithmic/semantic firewall; Decision Replay closes the loop).
- **Open question:** None.

### INV-CH8-04 — Five non-invasive integration patterns (co-deployed surface)

- **Whitepaper section:** §8.3
- **Commitment (paraphrase):** Five patterns — CDC→G, semantic-layer metadata import, MCP Context Product export, A2A federation, Unstructured Ingestion — together form the non-invasive surface by which the fabric composes over the estate. Each is sidecar by posture and by deployment: the fabric references source-of-record data via L, never replaces source systems, and fabric-side blast radius is bounded by the sidecar boundary. The patterns are *co-deployed*, not alternatives — one decision typically requires structured state, streaming behavior, governed data products, cross-organizational context, and unstructured evidence composed into the same Context Product.
- **Type signature:** None given (the five patterns are the enumeration).
- **Invariants:** Sidecar posture per pattern; L-reference (not replacement) of sources.
- **Dependencies:** Ch 7 §7.3 (unstructured content as first-class signal type); Fig-CH08-01 (the reference architecture the patterns bind to). **SDK-defined:** the SDK realizes these as Pillar 1 / L1 ingress mechanism per CLAUDE.md §5 "Integration Patterns" and §13 (CDC→G ingress reference in v0 scope).
- **Figure refs:** Fig-CH08-01.
- **Open question:** None.

### INV-CH8-05 — Pattern 1: CDC→G

- **Whitepaper section:** §8.3 (Pattern 1)
- **Commitment (paraphrase):** Change-data-capture is the preferred ingress for transactional systems of record where direct querying imposes operational cost. Debezium-style CDC streams committed transactions from the source's write-ahead log into the ingest surface; Assembly normalizes each change into a typed entity/relationship upsert keyed on the compound index of Ch 7 §7.3. The source is undisturbed — no query-path coupling, no schema coupling; CDC ingress is sidecar to the source, not in-path.
- **Type signature:** Upserts keyed on the Ch 7 §7.3 compound unique index `(tenant_id, entity_uri)` (by reference; not restated in §8.3).
- **Invariants:** Non-invasive commitment is architectural — CDC never touches the source's query path; all writes enter the graph through Assembly (single-writer, Ch 7 §7.3).
- **Dependencies:** Ch 7 §7.3 (compound index, idempotent upsert); L2 Context Assembly as the only writer. **SDK-defined:** CDC→G ingress reference implementation is in v0 scope per CLAUDE.md §13.
- **Figure refs:** Fig-CH08-01 (Perception-layer ingress).
- **Open question:** None.

### INV-CH8-06 — Pattern 2: semantic-layer metadata import

- **Whitepaper section:** §8.3 (Pattern 2)
- **Commitment (paraphrase):** The fabric reads through existing semantic-layer investments (dbt, Cube, AtScale, proprietary stacks) rather than replacing them: metric, dimension, and relationship definitions import as typed entity shapes in G, binding the canonical dimensional vocabulary to the E and R registries. Existing semantic-layer consumers are unaffected — the fabric becomes an additional consumer. Pattern 2 also absorbs the streaming concern: domain event streams carrying semantic-layer-shaped events (metric computation, materialized dimension change, data-product version bump) import as metadata events into G via the same mechanism.
- **Type signature:** None given (typed entity shapes in G; no schema stated).
- **Invariants:** Reads-through, never replaces; the semantic layer's own consumers continue undisturbed.
- **Dependencies:** Ch 4 §4.1 (semantic-layer landscape), Ch 5 §5.5 (Mapping) establish the inheritance; E and R registries (Ch 7 §7.3); §8.3.2 mechanic 3 (catalog semantic-layer productization → canonical semantic substrate).
- **Figure refs:** Fig-CH08-01.
- **Open question:** None.

### INV-CH8-07 — Pattern 3: MCP Context Product export

- **Whitepaper section:** §8.3 (Pattern 3)
- **Commitment (paraphrase):** The fabric exposes Context Products as MCP Resources so any MCP-capable agent runtime consumes the typed, policy-bound, role-projected payload without knowing the fabric's internals. Design constraint (from Ch 2 §2.5): MCP is a transport/protocol layer, not a context-semantics layer — the fabric is *served via* MCP, not *defined by* MCP. The Context Product carries its semantic contract (Ch 6 §6.3 ContextProductContract) at the application layer, independent of transport (MCP, direct API, message bus, inline library import). MCP is one of several protocol-layer choices at the Control Plane; the Contract's stability holds across all of them.
- **Type signature:** Context Products as MCP Resources; contract per Ch 6 §6.3 `ContextProductContract`.
- **Invariants:** Transport-independence of the Context Product contract; consumers need not adopt MCP.
- **Dependencies:** Ch 2 §2.5 (MCP positioning), Ch 6 §6.3 (contract), Ch 6 §6.5 (MCP as access-layer surface). **SDK-defined (bidirectional MCP):** the whitepaper frames Pattern 3 as export only; CLAUDE.md §7.1 extends MCP to a bidirectional surface — MCP client ingress at L1, content acquisition at L4–L5, egress at L6 (Pattern 3 unchanged), Experience Layer access surface, and ArtifactStore persistence transport (§7.4). SDK-as-client and SDK-as-server live in different modules with different trust postures. This extension is SDK-defined, labeled per CLAUDE.md §1.
- **Figure refs:** Fig-CH08-01.
- **Open question:** "MCP role allocation — which integration edges use MCP (per §7.1), and what's the SDK's API per role?" (existing D-IMPL-13; quoted from CLAUDE.md §12, not re-numbered here).

### INV-CH8-08 — Pattern 4: A2A federation

- **Whitepaper section:** §8.3 (Pattern 4)
- **Commitment (paraphrase):** A2A protocols let one organization's agent consume a Context Product produced by another organization's fabric under negotiated contract, entitlement, and Lineage terms (syndicated lending, correspondent banking exemplars). Trust boundaries (entitlement, jurisdiction, data-residency, liability) are resolved at the A2A layer via Policy bindings carried in the exchanged Context Product and **verified at the consumer's Control Plane before admission into the consuming fabric's graph**. Whitepaper posture: Pattern 4 is an architectural proposition — A2A standards are industry-emergent at 2026 state; the claim is to the architectural surface, not to production federation networks. A2A is optional per use case in the whitepaper (Patterns 1–3 and 5 suffice intra-organization). Pattern 4 is the cross-organizational ingress that Ch 7 §7.6 Mode 3 assembly consumes — the syndicated-covenant Mode 3 exemplar walks typed contributions across participants with passage-level L preserved on every reconciled relationship.
- **Type signature:** Typed Context Product on the wire (e.g., `SyndicatedCovenantContext`); no wire schema given.
- **Invariants:** Consumer-side Control Plane verification precedes graph admission; passage-level L preserved across the trust boundary; Mode 3 is structurally cross-organizational (not subsumable by a larger Mode 2 context window).
- **Dependencies:** Ch 7 §7.6 Mode 3 (assembly-mode commitment), Ch 7 §7.4 (algorithmic verification discipline), Ch 7 §7.10 (passage-level L). **SDK-defined (A2A first-class in v0):** per CLAUDE.md §7.2, A2A is a v0 commitment, not a v1 deferral — `WireProtocol` abstraction with a v0 default transport; identity/attestation and signing primitives; inbound A2A products enter L3 only through L2 after Control Plane validation of Policy bindings (structural, per CLAUDE.md §10); lineage continuity via set-union (inbound L *extends*, never replaces, consumer L, preserving producer operator plan, graph snapshot, and policy version).
- **Figure refs:** Fig-CH08-01.
- **Open questions:** "Which transport for v0? MCP-over-A2A extensions, custom typed RPC over HTTP/2+mTLS, or other?" (existing D-IMPL-14); "PKI primitives for A2A (X.509, JWT, SPIFFE/SPIRE, custom)?" (existing D-IMPL-15); "Verify every inbound A2A Context Product, or fast-path admissions for high-trust peers?" (existing D-IMPL-16). Quoted from CLAUDE.md §12; not re-numbered here.

### INV-CH8-09 — Pattern 5: Unstructured Ingestion (six-stage pipeline)

- **Whitepaper section:** §8.3 (Pattern 5)
- **Commitment (paraphrase):** The signals that matter most for the target decisions are document-, audio-, and chat-shaped; Pattern 5 makes them first-class citizens of the Context Graph. Ingress is a six-stage pipeline: (1) parse into structured spans; (2) chunk with late-chunking and Contextual Retrieval discipline; (3) embed with a corpus-calibrated model; (4) apply the Policy Operator **before** the Similarity Operator (per Ch 7 §7.4 composition (c)), then run similarity retrieval against the policy-scoped index; (5) extract typed entities and typed relationships with the Anthropic Citations API returning passage-level source references; (6) graph-persist into G(E, R, T, P, Π, L) with passage-level Lineage (page, paragraph, bounding box, chunk identifier, embedding version, WORM archive reference) bound to every edge. Pattern 5 is the canonical Mode 1 ingestion mechanism — pure algorithmic assembly, no LLM invocation at any stage of the assembly itself.
- **Type signature:** parse → chunk → embed → Policy-before-Similarity retrieval → typed entity-and-relationship extraction → graph-persist with passage-level L.
- **Invariants:** Policy-before-Similarity ordering enforced in the retrieval tier (structural, not post-hoc filter); passage-level L on every extracted edge; Mode 1 purity (no LLM in assembly).
- **Dependencies:** Ch 7 §7.3 (unstructured as first-class signal), Ch 7 §7.4 composition (c), Ch 7 §7.6 (Mode 1 commitment), Ch 7 §7.10 (Citations/passage-level L); §8.3.1 reference stack; §8.4 Alternating Derivation Pipeline as downstream Mode 2 consumer.
- **Figure refs:** Fig-CH08-02, Fig-CH08-03.
- **Open question:** "Unstructured pipeline (Pattern 5) pluggability — each stage as a Protocol, or one opinionated pipeline?" (existing D-IMPL-08; quoted from CLAUDE.md §12).

### INV-CH8-10 — Pattern 5 reference stack (2026 vendor snapshot)

- **Whitepaper section:** §8.3.1
- **Commitment (paraphrase):** The engineering reference stack for Pattern 5. Parser dispatch axis is cloud-agentic vs on-prem-sensitive, decided by data-classification and residency policy, *not* model capability (LlamaParse Agentic / IBM Docling as 2026 exemplars). Embedding: finance-calibrated cloud model vs self-hosted alternative (voyage-finance-2 / BGE-M3 as 2026 exemplars), decision boundary again the data-classification policy at the Control Plane. Retrieval: Policy Operator projects a principal-permissible subgraph at the entitlement gate; Similarity applies distance-weighted ranking only over that subgraph; hybrid BM25 + dense + ColBERT rerank produces candidates. Extraction: typed NER + typed relationships with Citations passage references. Persistence: passage-level L pinning (page, bounding box, chunk id, embedding version, WORM reference, valid-time, policy regime). Durable vs replaceable is explicit: the dispatch axis, Policy-before-Similarity ordering, typed extraction, and passage-level L binding are architectural; specific vendors are Control Plane substitutions requiring no re-architecture.
- **Type signature:** Seven-tier pipeline: source → parser dispatch → chunking → embedding (tiers 1–4, Fig-CH08-02); retrieval → extraction → persistence (tiers 5–7, Fig-CH08-03).
- **Invariants:** Vendor substitution is a Control Plane operation; Policy-before-Similarity is a structural property of the pipeline; the fabric never becomes the record of record for regulated archives (references them via L).
- **Dependencies:** Ch 7 §7.10 D-53 (Anthropic Citations as the canonical passage-level L component); Fig-CH07-07 Evidence Chain. Note for SDK: specific vendors (LlamaParse, Docling, voyage-finance-2, BGE-M3) are domain/deployment values, not SDK mechanism — the SDK ships the pipeline Protocols per CLAUDE.md working principle "Mechanism, not values" (relates to D-IMPL-07, D-IMPL-08).
- **Figure refs:** Fig-CH08-02, Fig-CH08-03, Fig-CH07-07 (by reference).
- **Open question:** "EmbedderProtocol with reference adapters, or one model?" (existing D-IMPL-07; quoted from CLAUDE.md §12).

### INV-CH8-11 — Four-tier composition pattern over knowledge-catalog substrates

- **Whitepaper section:** §8.3.2
- **Commitment (paraphrase):** Where the fabric sits relative to a productized knowledge-catalog substrate: Tier 1 systems of record and signal (unmodified; Patterns 1–5 handle ingress); Tier 2 productized knowledge-catalog / data-product substrate (vendor-agnostic class; not duplicated, not replatformed); Tier 3 the CCF as cognition layer (adds bitemporal T, policy-at-construction P, typed Π per principal, per-claim L, D_c, λ_c, decision replay — primitives no catalog substrate assumes); Tier 4 agent consumption via MCP or equivalent APIs under the Ch 6 §6.3 contract. Six integration mechanics bind Tier 2 ⇄ Tier 3: (1) catalog data products → CCF signal inputs; (2) catalog enrichment → entity-extraction pre-processor for E and R (Tier-2-extracted entities are *candidates*; Tier-3 typing makes them load-bearing); (3) catalog semantic-layer productization → canonical semantic substrate for E + R registries; (4) access-control-aware search → P *signal*, never P *enforcement* (the fabric never delegates P-enforcement to Tier 2 — two stacked policy layers); (5) MCP composes vertically across tiers without collapsing the tier distinction; (6) catalog measurable context evaluation → one λ_c calibration input among many. Tier-2 and Tier-4 vendor selections are decoupled; composition, not substitution.
- **Type signature:** None given (four tiers + six mechanics enumeration).
- **Invariants:** P-enforcement stays at Tier 3 regardless of Tier-2 vendor; fabric assembles Context Products ephemerally at decision time (does not adopt Tier-2 persistence model); tier decoupling preserved across substrate and agent vendor choices.
- **Dependencies:** Ch 4 §4.5.2 (four-tier compressed statement; six-tuple verdict E HIT / R HIT / T MISS / P MISS / Π MISS / L PARTIAL boundary), Ch 5 §5.1, Ch 7 §7.4–§7.10 (cognition-tier disciplines), Ch 7 §7.6 (per-product Assembly Mode against Tier-2 substrate), §8.3 Patterns 1–5.
- **Figure refs:** None in §8.3.2.
- **Open question:** None (per-domain λ_c calibration methodology is explicitly withheld by the whitepaper as trade-secret — inventoried as a stated non-commitment, not a gap).

### INV-CH8-12 — The Alternating Derivation Pipeline (Document-Heavy Compositional archetype)

- **Whitepaper section:** §8.4
- **Commitment (paraphrase):** The Document-Heavy Compositional archetype (credit-memo exemplar) runs a four-stage alternation: **Algorithmic Perception** (Pattern 5 pipeline; deterministic NER and relationship extraction; no LLM inference; structured graph writes with passage-level L) → **Semantic Comprehension** (LLM reads chunks in context, proposes cross-document candidate relationships the span-local stage cannot infer) → **Algorithmic Verification** (Policy Operator first at the entitlement gate; Similarity Operator applies distance-weighted deduplication to LLM-proposed relationships at a Control-Plane-governed confidence threshold — below threshold, candidates remain separate and ambiguity is carried forward, never silently collapsed; Temporal Operator aligns as-of times; Traversal Operator expands the entity network per Ch 7 §7.4 composition (a)) → **Semantic Synthesis** (LLM drafts narrative over the verified, Π-projected subgraph with Citations pinning every claim to a source passage). Output is a typed Context Product honoring the Ch 6 §6.3 contract, feeding the Ch 7 §7.10 five-dimension replay. This is the canonical Mode 2 illustration (algorithmic assembly + LLM packaging); Mode 1 omits the semantic stages; Mode 3 expands Perception into cross-organizational contribution gathering. LLM inference runs exactly twice (Comprehension, Synthesis), bounded by the surrounding algorithmic stages. A persist-into-G feedback loop accumulates extracted entities, verified relationships, and anchors so subsequent invocations do not recompute from raw signal.
- **Type signature:** Algorithmic Perception → Semantic Comprehension → Algorithmic Verification → Semantic Synthesis, each handing off under a typed contract; output e.g. `CreditMemoContext`.
- **Invariants:** Algorithmic ⇄ Semantic Alternation (Ch 7 §7.6 architectural primitive — LLMs never see raw signal; algorithmic stages never perform semantic interpretation); Policy-before-Similarity within Verification; below-threshold candidate edges carried forward as distinct; project-then-retrieve, not retrieve-then-filter; every claim in synthesis output passage-anchored.
- **Dependencies:** **Links to the §7.6.6 alternation invariant** — Ch 7 §7.6 committed the alternation as a primitive the delivery layer respects; §8.4 walks the same primitive end to end (CI-enforced structural invariant in the SDK per CLAUDE.md §5, §11 `@algorithmic` lint). Also: §8.3/§8.3.1 Pattern 5 (Perception substrate), Ch 7 §7.4 compositions (a) and (c), Ch 7 §7.5 (Π projection), Ch 7 §7.7 (D_c trigger on missing/stale inputs), Ch 6 §6.3 (contract fields), Ch 7 §7.10 (replay).
- **Figure refs:** Fig-CH08-04 (renders the four stages, boundary crossings, distance-weighted deduplication, and the persist-into-G feedback arrow).
- **Open question:** "Where the whitepaper specifies the deduplication confidence threshold as Control-Plane-governed but gives no threshold schema or defaulting rule, the SDK must decide the Control Plane parameter shape for operator thresholds." (unnumbered; synthesis task assigns any D-IMPL number).

### INV-CH8-13 — Six-dimensional graph, domain lens (weight patterns)

- **Whitepaper section:** §8.5
- **Commitment (paraphrase):** §8.5 does not re-specify G(E, R, T, P, Π, L); it renders each dimension in Wholesale Banking vocabulary and commits the *weight-pattern* observation: different archetypes weight the six dimensions differently while the graph primitive stays the same. E: typed URI-addressable entities whose identity persists across sources and time; ingestion never overwrites a resolved entity — it appends enrichments. R: typed, directed relationships as first-class persisted state, not derived query-side joins. T: layered, not scalar — each source class carries its own λ_c and the layers reconcile through explicit windows rather than silent averaging. P: a frozen policy-version identifier plus serialized parameters bound at construction time; policy projection runs before any similarity or traversal operator sees graph state. Π: a typed transformation from graph substructure to principal-conditioned payload — not an RBAC filter; two agents on the same graph state legitimately receive different Context Products. L: records source identity, not source location (migration-proof); pins to page/paragraph/bounding-box, transaction records, WORM archive locations. Archetype weightings: Document-Heavy Compositional E-R-L heavy; Temporal Reconciliation T-dominant; Forensic-Defensibility P-L-Π heavy; Conversational Synthesis Π-heavy and D_c-aware.
- **Type signature:** `G(E, R, T, P, Π, L)` (by reference to Ch 5 §5.2, Ch 7 §7.3).
- **Invariants:** T/P/Π/L are typed dimensions of the same persisted state read simultaneously by every operator composition — not independent graphs stitched query-side; append-only entity enrichment (single-writer discipline per Ch 7 §7.3); L source-neutrality.
- **Dependencies:** Ch 5 §5.2 (six-tuple), Ch 7 §7.3 (persisted state), Ch 7 §7.4 compositions (a)/(c)/(d), Ch 7 §7.5 (Π), Ch 7 §7.7 (λ_c 17-row illustrative table), Ch 7 §7.10 (passage-level L), Ch 1 §1.4 (Client 360 five-traversal challenge resolved against this substrate). Domain vocabulary (Reg O, PRA 9/17, MiFID II, borrower/guarantor ontology) is illustrative — for the SDK these are user-supplied configuration values, never mechanism (CLAUDE.md §1, §13).
- **Figure refs:** Fig-CH08-05 (supplementary: E-R plane with T/P/Π/L as dotted projections over the same subgraph; illustrative client).
- **Open question:** None.

### INV-CH8-14 — Temporal Abstraction Layer (Temporal Reconciliation archetype)

- **Whitepaper section:** §8.6
- **Commitment (paraphrase):** The CCF is a temporal abstraction layer over the data ecosystem: it decouples the timing of data production from the timing of decision consumption by distinguishing valid-time (when a fact was true) from observed-time (when the fabric learned of it) — a bitemporal discipline **enforced at the graph mutation boundary**, not reconstructed downstream by agents. "Real time" is a property of assembly and interpretation at moment of use, not of the data. The layer reconciles 6–10 source systems with unaligned cadences to a single as-of time, generating explicit valid-time-vs-observed-time disambiguation where they diverge (e.g., "signed-but-not-yet-settled-as-of-now," not "failed-to-settle"). The mechanism is neutral to structured vs unstructured and batch vs streaming sources — batch-overnight ASR transcripts and streaming chat reconcile to the same as-of time via the same layer. When a reconciliation gap surfaces, D_c fires on the freshness axis and routes conservatively (escalation, secondary verification, or a flagged narrative naming the gap) rather than answering with silent missing-data confidence.
- **Type signature:** Output is a typed Context Product (e.g., `FXPostTradeContext`) honoring the Ch 6 §6.3 contract with per-component freshness SLA and TTL bounds.
- **Invariants:** Bitemporal enforcement at the mutation boundary; single as-of binding per reconciliation; divergence surfaced explicitly, never averaged; conservative-bias routing under debt (Ch 7 §7.7).
- **Dependencies:** Ch 7 §7.4 composition (b) (Temporal Operator mechanism — not re-specified in §8.6); Ch 7 §7.7 (λ_c per source class, D_c firing); Ch 7 §7.5 (Π rendering per role); Ch 7 §7.10 (replay makes supervisory review tractable); §8.5 T-dominant weighting.
- **Figure refs:** None in §8.6.
- **Open question:** None.

### INV-CH8-15 — Regulatory regime → artifact mapping

- **Whitepaper section:** §8.7
- **Commitment (paraphrase):** The fabric's primitives produce, as first-class outputs, the artifact classes ten regulatory regimes require (tabulated: SR 26-2, ECOA/CFPB 2023-03, EU AI Act Annex III, BCBS 239, DORA, OCC Interagency TPRM, GDPR Art 22, NIST AI 600-1, NYDFS AI letter, FS AI RMF). Each obligation is discharged by a named fabric primitive: reconstructability by the five-dimension Decision Replay record + frozen policy binding; reason-specificity by passage-level L + Π reasoning trace; operational resilience by D_c fail-closed posture; etc. The regulatory landscape is a first-class design input, not a post-hoc compliance layer.
- **Type signature:** None (regime→artifact table).
- **Invariants:** Artifacts are composed at decision time by the same mechanism that makes decisioning work, never reconstructed at examination time.
- **Dependencies:** Ch 7 §7.10 (replay), Ch 7 §7.7 (λ_c/D_c), §8.7.1–§8.7.3, §8.8 (supervision quality), §8.12 (the "how"). For the SDK: specific regime bundles are user-supplied policy configuration, explicitly "Not the SDK's problem" per CLAUDE.md §13 — the SDK ships the artifact-producing mechanism only.
- **Figure refs:** None (table in text).
- **Open question:** None.

### INV-CH8-16 — λ_c and D_c as governance primitives; Conditional Assessment Routing

- **Whitepaper section:** §8.7.1
- **Commitment (paraphrase):** λ_c and D_c are first-class fields on the graph, persisted into the Decision Replay record, becoming regulatory artifacts at audit time. Domain-decay form: `R(t) = R_0 × (1/2)^((t − t_0) / λ_c)`, calibrated per source class; all published λ_c values carry the illustrative qualifier (deployment teams calibrate against their own corpus). Basic debt form: `D_c = 1 − (C_available / C_required)`; extended form `D_c = 1 − (F · C · S)` (freshness, completeness, semantic consistency) decomposes the scalar so governance can identify which axis produces the debt — the three factors are not substitutes, and the extended form makes routing auditable. D_c drives Conditional Assessment Routing with three architecturally distinct pathways: **bypass** (no relevant entities/threats — skip LLM inference entirely), **conditional** (low debt, routine — standard LLM assessment), **forced escalation** (high debt — incomplete information treated as a risk amplifier; human-in-the-loop or multi-modal verification). High debt is detected at the Comprehension boundary *before* the semantic stage sees the context, making the overconfident-sparse-context LLM failure mode structurally impossible for routed workflows; the routing decision itself lands in the replay record.
- **Type signature:** `R(t) = R_0 × (1/2)^((t − t_0) / λ_c)`; `D_c = 1 − (C_available / C_required)`; extended `D_c = 1 − (F · C · S)`.
- **Invariants:** λ_c/D_c persisted into replay; routing decision captured as a regulatory artifact; debt computed algorithmically before semantic invocation; λ_c values are calibration outputs, never fixed constants (for the SDK: λ_c tables live in Control Plane configuration, not code — CLAUDE.md §5).
- **Dependencies:** Ch 7 §7.7 (mechanism owner — §8.7.1 applies it to governance); Ch 6 §6.3 (D_c as declarative contract field); Ch 7 §7.10 (replay capture).
- **Figure refs:** Fig-CH08-06 (Conditional Assessment Routing decision tree; supplementary, not load-bearing per the text).
- **Open question:** "The extended form D_c = 1 − (F · C · S) is given without specification of how F, C, and S are individually computed or weighted; the SDK must commit a computable definition per factor." (unnumbered; synthesis assigns numbering).

### INV-CH8-17 — MNPI governance via Policy-before-Similarity (subgraph substitution)

- **Whitepaper section:** §8.7.2
- **Commitment (paraphrase):** The Policy Operator runs before the Similarity Operator, not after — similarity-first-filter-later systems allow restricted signal to influence ranking, scoring, and candidate neighborhoods before any entitlement check. At the graph layer, restricted-information enforcement is **subgraph substitution enforced by Π**, not a row-level index filter: Π projects a different subgraph per principal clearance, and the entire downstream composition runs against the principal-specific subgraph from the first operator onward. Leakage is structurally prevented, not post-hoc mitigated (a 99%-effective post-hoc filter leaks 1%, which is where the exposure sits; post-hoc filters cannot be replay-verified as reliably blocking).
- **Type signature:** None (ordering + substitution commitment).
- **Invariants:** Policy-before-Similarity operator ordering (Ch 7 §7.4 composition (c)); subgraph substitution as a typed transformation auditable under Π's stability-layer contract; structural prevention is the only posture that withstands reconstructability expectations.
- **Dependencies:** Ch 7 §7.4 composition (c) (mechanism), Ch 7 §7.5 (Π stability contract — mechanism side lives there, governance side here); §8.3.1 retrieval tier (enforcement point); §8.7 regime table (artifacts produced).
- **Figure refs:** None.
- **Open question:** None.

### INV-CH8-18 — Fail-closed under degraded sources

- **Whitepaper section:** §8.7.3
- **Commitment (paraphrase):** The fabric cannot prevent upstream degradation; its posture when degradation occurs is a three-step fail-closed mechanism inherited from Ch 7 §7.7: (1) Context Debt detects degradation (D_c computation at the Comprehension boundary before the Context Product is issued); (2) the Context Product inherits the Debt (every Context Product carries assembly-time D_c as a declarative field per Ch 6 §6.3); (3) the agent escalates or refuses (Conditional Assessment Routing). A silently-high-Debt Context Product is architecturally precluded from being the substrate of a consequential decision. Bias direction: elevated D_c biases urgency **upward**, not downward — inverting both cache-first (missing data = cache miss, return what you have) and permissive-LLM-first (missing data = reason from general knowledge) postures. Uncertainty is made visible and routed into escalation, additional-source-fetch, or decision-decline paths; the routing is captured in replay.
- **Type signature:** Detect (D_c) → inherit (contract field) → escalate/refuse (routing).
- **Invariants:** Each step is architectural, not advisory; no decision path exists on a silently-high-Debt product; conservative bias under debt.
- **Dependencies:** Ch 7 §7.7 (mechanism side), Ch 6 §6.3 (contract inheritance), §8.7.1 (routing), Ch 7 §7.10 (routing captured in replay). SDK hook: gates Forced LLM / Fail-Closed behavior per half-life-and-debt profile, specialization axis 5 (CLAUDE.md §6.2 — SDK-defined).
- **Figure refs:** None.
- **Open question:** None.

### INV-CH8-19 — Supervision Quality Assessment (presence → engagement)

- **Whitepaper section:** §8.8
- **Commitment (paraphrase):** The fabric evaluates *depth of engagement* rather than the fact of sign-off. Five behavioral-signal axes (time-on-case; cross-system query logs; historical precedent vs the reviewer's own comparable-case pattern and the institutional average; supporting-documents opened; relevant queries checked) fuse with VLM/LLM reasoning over case artifacts (does the disposition narrative substantively address flagged conditions, or is it boilerplate). The signals combine into a composite supervision quality score bounded in [0, 1], persisted alongside the decision in the Decision Replay record; below a policy-defined, Control-Plane-governed threshold, the fabric identifies a rubber-stamp approval and triggers escalation to secondary review. Supervision Quality is the complement of Context Debt: D_c measures completeness of what the agent saw; Supervision Quality measures how the human engaged with what the agent produced — the two are independent, jointly-required empirical controls.
- **Type signature:** Composite score ∈ [0, 1], persisted in the replay record.
- **Invariants:** Score persisted with the decision; threshold is policy-bound (Control Plane), never hard-coded; the two controls (D_c, Supervision Quality) are non-substitutable.
- **Dependencies:** Ch 7 §7.10 (replay persistence), §8.7.1 (D_c complement), Control Plane thresholds (Ch 7 §7.8). Whitepaper notes reduction-to-practice in a property-intelligence reference implementation (Homecams triangulation data point — see homecams-patterns appendix; the scoring calibration is domain-specific, do not inherit values). SDK hook: complements HITL primitives per CLAUDE.md §8.2 (SDK-defined).
- **Figure refs:** None.
- **Open question:** "The composite scoring function combining the five behavioral axes with VLM/LLM reasoning outputs is not specified — axis weights, fusion function, and score semantics are open for design." (unnumbered; synthesis assigns numbering).

### INV-CH8-20 — Auditability at scale: replay binding and the three-tier compression lifecycle

- **Whitepaper section:** §8.9
- **Commitment (paraphrase):** The Forensic-Defensibility archetype binds Decision Replay, Π projection, and passage-level L to the evidentiary chain a filed report rests on: every narrative claim traces narrative claim → passage → source → Decision Replay record, with citations produced at extraction, persisted as passage-level Lineage in L, and retained when the decision is recorded. Reconstruction is Ch 7 §7.10 Decision Replay queried by temporal boundary and decision identifier at T+2/T+5 years. The compression regime is the three-tier lifecycle (Ch 7 §7.10 D-54, referenced by name): **Full-Fidelity** (retained indefinitely for decisions exceeding severity thresholds — the severity exemption is the mechanism by which decisions that matter most for review outlive any otherwise-applicable retention limit); **Compressed** (routine cycles reduced to essential aggregated metrics — composite D_c, entity counts, outcome, decision class — sufficient for longitudinal analysis, not full replay); **Tombstoned** (minimal metadata: timestamps, decision IDs, outcome class — audit adjacency preserved, storage recovered). Compression is Control-Plane-governed; severity thresholds are policy-bound, not hard-coded. Π renders the same record as three distinct role-shaped views (auditor / investigator / compliance-officer) from one underlying record with no state duplication. The fabric never becomes the record of record for WORM-regulated archives; it references them via L.
- **Type signature:** Three-tier lifecycle: Full-Fidelity | Compressed | Tombstoned.
- **Invariants:** Every claim carries both a passage-level L anchor and a replay anchor; severity asymmetry (routine reduced aggressively, high-severity preserved indefinitely); thresholds policy-bound; one record, N Π-projections; WORM archives remain records of record.
- **Dependencies:** Ch 7 §7.10 (replay mechanism, D-53 Citations, D-54 lifecycle), Ch 7 §7.5 D-22 (three-view precedent), §8.8 (Supervision Quality as complementary reviewer-side control), Fig-CH07-07 Evidence Chain (load-bearing rendering, by reference). SDK hook: interacts with snapshot management and ArtifactStore (CLAUDE.md §7.4; D-IMPL-06, D-IMPL-26/27).
- **Figure refs:** Fig-CH07-07 (by reference); none new in §8.9.
- **Open question:** "Snapshot management for replay — storage strategy for graph snapshots and similarity-index snapshots making §7.10 replay tractable at year-scale." (existing D-IMPL-06; quoted from CLAUDE.md §12 — the three-tier lifecycle constrains but does not resolve it).

### INV-CH8-21 — Conversational Reporting Layer (Conversational Synthesis archetype)

- **Whitepaper section:** §8.10
- **Commitment (paraphrase):** A conversational surface over the same Context Graph the other archetypes operate on — not a chatbot over a warehouse. Three stages: (1) **intent classification** routes a natural-language request into an archetype category (advisory synthesis, transactional lookup, attestation reconstruction, benchmark comparison), each selecting a different Π projection; (2) **Π projection over Decision Replay records and passage-level Lineage** composes the response against a specific substrate, not a free-form retrieval corpus (the "what changed" pattern is a Π projection over replay records since the last review plus incremental graph mutation since that horizon); (3) the **Context Debt Awareness Mechanism** gates the response against substrate freshness — if D_c is elevated on any dimension the answer depends on, the gap is surfaced as a first-class signal rather than masked by fluent prose ("fluent prose is the most dangerous surface on which to carry a freshness hole"). Every claim cites its source passage via the Ch 7 §7.10 D-53 Citations mechanism.
- **Type signature:** intent classification → Π projection → D_c-aware gating; output honoring the Ch 6 §6.3 contract.
- **Invariants:** The response may never sound more confident than the context warrants; missing feeds produce named gaps and deferred claims, never fabrication; same substrate underwrites the conversational answer as underwrites §8.4/§8.9 outputs.
- **Dependencies:** §8.5 Π-heavy/D_c-aware weighting, §8.6 temporal mechanism, §8.7.1 (D_c), Ch 7 §7.5 (Π), Ch 7 §7.10 (replay + Citations). **Scope note: the Conversational Reporting Layer is out of SDK v0 scope per CLAUDE.md §13** ("The Conversational Reporting Layer (§8.10 of the whitepaper)" is on the explicit out-of-scope list) — inventoried here for completeness, not designed; its underlying primitives (Π, D_c gating, replay) are in scope individually.
- **Figure refs:** None.
- **Open question:** None (out-of-scope disposition is a settled CLAUDE.md §13 ruling, not an open design question).

### INV-CH8-22 — Archetype mapping framework, pilot criteria, and platform/domain split

- **Whitepaper section:** §8.11
- **Commitment (paraphrase):** A diagnostic framework places any use case on the four-archetype typology by which binding work dominates (extraction/evidence chains; multi-system as-of reconciliation; adversarial-examination reconstruction; role-conditioned projection under a freshness gate); hybrid cases compose archetypes (Client 360 exercises all four). Seven narrative pilot-selection criteria: domain readiness, regulatory pressure, data-access maturity, executive sponsorship, time-to-value, accumulation, risk appetite — prioritization itself is deliberately left to leadership. Organizational commitment: a platform-versus-domain split — the platform team owns fabric primitives (Graph, Operators, Control Plane, Replay Storage); domain teams own domain-specific Operators and domain Context Products, analogous to Data Mesh domain ownership extended to context products. Pilots do not wait on data modernization: source re-binding is an ingestion-layer operation, not pilot-level rework. The first archetype delivers reusable components (entity reconciliation logic, policy binding templates, replay storage, passage-L pinning harness, λ_c calibration methodology) that accelerate every subsequent archetype — accumulation is the enterprise-capability mechanism.
- **Type signature:** None (framework + criteria enumeration).
- **Invariants:** The framework is illustrative, not exhaustive or prescriptive; the architecture deliberately does not preempt prioritization.
- **Dependencies:** §8.4/§8.6/§8.9/§8.10 (the four archetypes), §8.5 (weight patterns), Ch 1 §1.4 (Client 360 arc closed at the framework level). For the SDK: the platform/domain split maps directly onto the mechanism-vs-values boundary — platform-team assets are SDK mechanism; domain Operators/Products are user configuration (CLAUDE.md §1, §13).
- **Figure refs:** None.
- **Open question:** None.

### INV-CH8-23 — Governance and SDLC alignment

- **Whitepaper section:** §8.12
- **Commitment (paraphrase):** Governance becomes measurable because the primitives are measurable: regulatory artifacts are a first-class output of the same mechanism that performs decisioning, composed at decision time rather than reconstructed at examination time. Three governance primitives unify the surface — λ_c makes freshness regulatorily legible, D_c makes completeness legible (traceable against the routing traversed), Supervision Quality makes review engagement legible — supporting threshold-setting per decision class, replay-record sampling audits, and score-distribution review. SDLC alignment: Context Operator definitions, Π projection logic, policy bindings, replay storage, and compression tiers are versioned, tested, and approved through the same SDLC gates that govern models and applications; the Ch 7 §7.8 Control Plane / Data Plane separation is the architectural boundary that lets SDLC gates map 1:1 to control-plane deployments without disrupting the data-plane assembly path.
- **Type signature:** None.
- **Invariants:** Governance artifacts produced by mechanism, not by a separate governance track; operator/policy changes move through the same gates as model changes; Control Plane vs Data Plane boundary (Ch 7 §7.8) is what makes SDLC tractable.
- **Dependencies:** §8.7 (regime table — the "what"; §8.12 is the "how"), §8.7.1–§8.7.3, §8.8, Ch 7 §7.8 (plane separation — the audit plane). SDK hook: Control Plane as versioned in-process registry with audit obligations (CLAUDE.md §5, §13).
- **Figure refs:** None.
- **Open question:** None.

### INV-CH8-24 — Chapter conclusion: coexistence as the single architectural commitment

- **Whitepaper section:** §8.13
- **Commitment (paraphrase):** The chapter's elements — four archetypes, five integration patterns, the domain graph rendering, the regulatory taxonomy, supervision quality, the auditability regime, the conversational surface, the adoption framework, the governance posture — are one architectural commitment: coexistence rather than replacement, enabling the System-of-Record → System-of-Cognition path as layered composition. The fluid-ecosystem posture is restated as a design condition: pilots launch mid-migration; source moves re-bind via ingestion updates, not rework; heterogeneity is the condition the architecture was designed for, not retrofitted to.
- **Type signature:** None (conclusion; no new mechanism).
- **Invariants:** None new (restates §8.1–§8.2 commitments).
- **Dependencies:** §8.1–§8.12 (summarized), Ch 9 (hand-off).
- **Figure refs:** None.
- **Open question:** None.

---

## Open Questions (unnumbered)

Quoted for the synthesis task; numbering (new D-IMPL-NN from D-IMPL-30 onward) is assigned only at synthesis. Existing CLAUDE.md §12 numbers are referenced where the question already exists.

- "Where the whitepaper specifies the deduplication confidence threshold as Control-Plane-governed but gives no threshold schema or defaulting rule, the SDK must decide the Control Plane parameter shape for operator thresholds." (from §8.4 Algorithmic Verification — INV-CH8-12)
- "The extended form D_c = 1 − (F · C · S) is given without specification of how F, C, and S are individually computed or weighted; the SDK must commit a computable definition per factor." (from §8.7.1 — INV-CH8-16)
- "The composite scoring function combining the five behavioral axes with VLM/LLM reasoning outputs is not specified — axis weights, fusion function, and score semantics are open for design." (from §8.8 Supervision Quality — INV-CH8-19; also raises whether Supervision Quality is SDK mechanism at all or a reference pattern users implement — CLAUDE.md §13 does not list it in v0 scope)
- Existing-number cross-references surfaced by Ch 8 (not new): D-IMPL-06 (snapshot management vs §8.9 compression tiers), D-IMPL-07 (embedder abstraction, §8.3.1), D-IMPL-08 (Pattern 5 stage pluggability), D-IMPL-13 (MCP role allocation), D-IMPL-14/15/16 (A2A transport, identity, admission scope, §8.3 Pattern 4).

