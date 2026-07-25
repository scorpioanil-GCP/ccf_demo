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
