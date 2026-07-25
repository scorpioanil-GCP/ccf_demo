# DESIGN — CCF SDK v0

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

## 1. Overview and Reading Guide

This is the Phase D design deliverable (DSGN-01): the CCF SDK's architectural shape against the 126-entry specification inventory (`docs/SPEC_INVENTORY.md`), organized by the five Common Pillars (CLAUDE.md §4, locked D-05). Altitude is contract-level throughout (locked D-07): responsibilities, Protocol/type-signature names and key methods, invariants enforced, seams, and the D-IMPL rulings each component embodies — no method bodies, no file-level layout (Phase I territory).

**How to read this document.**

- **Sections 2–6** are the five pillar chapters. The Data and Context Layer (§2) is split into a write side (§2A: L1–L3, ingress, single-writer) and a read side (§2B: L4–L6, half-life/debt, replay, closed loop) — internal references to "Part A"/"Part B" mean §2A/§2B.
- **Sections 7–8** are cross-cutting: the Control Plane / Data Plane separation (§7) and the cross-process seams — MCP role allocation, A2A federation, the Harness Adapter, the ArtifactStore (§8).
- **Section 9** is the Invariant Preservation chapter (locked D-10/D-11): a structural argument, enforcement point, and diagram/section reference for each of the seven named architectural invariants, plus the CI enforcement design Phase F's test strategy (FEAS-03) and Phase I implement against.
- **The two appendices** close the document: the 126-row traceability matrix mapping every `INV-CHx-NN` inventory entry to its design section (locked D-06), and the carried-forward review findings.

**Citation conventions.** Inventory entries are cited inline as `INV-CHx-NN`; decisions as `D-IMPL-NN`; figures as `Fig-CHnn-mm`; whitepaper sections as `§n.n`; CLAUDE.md sections as `CLAUDE.md §n`. Where the SDK extends beyond the whitepaper (the Agent Specialization Framework, the Agent & Task Factory, bidirectional MCP, A2A as first-class, the Harness Adapter surface, the ArtifactStore, the Orchestration Layer, HITL primitives, the Experience Layer), the extension is explicitly labeled **SDK-defined** with its CLAUDE.md anchor and its whitepaper hook.

**Decision-log linkage.** Every design commitment below cites the `D-IMPL-NN` ruling it embodies. All 49 open decisions are RESOLVED with Dave as approver (`docs/DECISIONS.md`, 2026-07-25; see the Decision Census note there for the 49/50/51 accounting, including D-IMPL-51). D-IMPL-10 (repo shape) is resolved for v0 as monorepo per CLAUDE.md §2.2 — the post-v0 adapter-split remainder is tracked outside Phase D as non-gating deferred scope — and is not load-bearing for any component in this document.

**Provisional-flag legend (locked D-04).** A design element resting on a provisional ruling carries a `> PROVISIONAL basis: D-IMPL-NN` blockquote flag. Because the decision marathon closed with zero provisional *design-basis* flags, **this document contains no provisional flags** — every component rests on RESOLVED rulings. (D-IMPL-10 remains a provisional monorepo *orientation* per CLAUDE.md §2.2; it is not a design basis for any component here and carries no flag.)

**Pillar map and diagram index.** One architecture diagram per pillar, one per mandated seam, and four D-09 sequence diagrams for load-bearing runtime flows:

| Section | Pillar / concern | Diagram(s) |
|---------|------------------|------------|
| §2 (§2A + §2B) | Data and Context Layer | `docs/diagrams/pillar-data-context.mmd`; `docs/diagrams/seq-single-writer-write-path.mmd`; `docs/diagrams/seq-replay-resolution.mmd` |
| §3 | Core Agent Types | `docs/diagrams/pillar-agent-types.mmd` |
| §4 | Orchestration Layer | `docs/diagrams/pillar-orchestration.mmd` |
| §5 | Human in the Loop and Control | `docs/diagrams/pillar-hitl.mmd`; `docs/diagrams/seq-hitl-suspend-resume.mmd` |
| §6 | Experience Layer | `docs/diagrams/pillar-experience.mmd` |
| §8 | Seams | `docs/diagrams/seam-harness-adapter.mmd`; `docs/diagrams/seam-artifact-store.mmd`; `docs/diagrams/seq-a2a-admission.mmd` |

---

## 2. Pillar: Data and Context Layer

The fabric itself — L1–L6 plus half-life/debt, replay, and the closed loop. Component diagram: `docs/diagrams/pillar-data-context.mmd`. Write-path sequence: `docs/diagrams/seq-single-writer-write-path.mmd`.

## 2A. The Write Side (L1–L3, Ingress, Single-Writer)

**Scope of §2A.** The fabric's write side: the L1 Signal Layer, the L2 Context Assembly layer, the L3 Context Graph, the ingress patterns that feed them (CDC→G, MCP-client ingress, semantic-layer metadata import, Unstructured Ingestion), and single-writer enforcement. Read-side mechanism (L4–L6, half-life/debt, replay, control/data plane runtime separation) is Part B (§2B). Coverage contract: every INV entry assigned to this chapter by the traceability matrix at the end of this document is cited inline in a component section or listed under Deferred entries. Altitude is contract-level per locked D-07: responsibility, Protocol/type-signature names and key methods, invariants enforced, seams, and D-IMPL rulings embodied — no method bodies, no file layout.

**See-also cross-references honored here.** Two Part-B-owned entries name this chapter as their write-side anchor: INV-CH7-60 (the §7.8 append-only-with-logical-supersession invariant — its graph-side mechanism is §2A.3.3/§2A.5.2 of this chapter; its runtime-invariant framing is Part B's) and INV-CH7-73 (the §7.8.4 architectural-invariants enumeration whose clause (a), build-time single-writer prevention, is realized by the §2A.5.3 enforcement stack; the remaining clauses are Part B's). One §6/§8-owned entry, INV-CH8-24 (coexistence/layering onto existing estates), anchors its ingress-side half in §2A.4's non-invasive pattern designs.

---

### 2A.0 Conceptual Foundations (Chapter 5 commitments the write side realizes)

The write side is where the whitepaper's conceptual commitments become persisted mechanism. The Chapter 5 commitments governing every component below, each with its design consequence:

- **Three-tier enterprise architecture** (INV-CH5-01): the fabric occupies Tier 3 (Cognition) above Record and Signal Generation tiers. L1–L3 are the machinery by which Tier 3 represents state without absorbing Tiers 1–2.
  - *Design consequence:* no SDK component below opens a write path into a Tier 1/2 system; ingress adapters are strictly read/subscribe-side (§2A.4).
- **Data-perspective vs context-perspective boundary** (INV-CH5-02): systems below the fabric answer data questions; the graph exists to answer context questions. The six-tuple verdicts against knowledge catalogs (E HIT / R HIT / T MISS / P MISS / Π MISS / L PARTIAL) define exactly what L2/L3 must add rather than duplicate.
  - *Design consequence:* the T/P/Π/L dimensions are where the SDK's write side spends its mechanism budget; E/R import leans on existing substrates via Pattern 2 (§2A.4.3) and the four-tier composition (INV-CH8-11).
- **The six-tuple `G(E, R, T, P, Π, L)`** (INV-CH5-03) with **per-dimension semantics and necessity tests** (INV-CH5-04): all six dimensions are mandatory; removal of any one produces a named, testable failure mode.
  - *Design consequence:* the SDK's `ContextGraph` state primitive declares all six structurally (§2A.5.1), and the Phase I test strategy must exercise the per-dimension failure modes as negative tests — a design obligation recorded for Phase F's test-strategy chapter.
- **Dynamic context vs dynamic content** (INV-CH5-05) and **derived-not-stored / project-then-retrieve** (INV-CH5-07): the graph persists context state; Context Products are projected at decision time, never stored as the system of record.
  - *Design consequence:* the write side persists *graph state*, and only graph state — product materialization is a read-side cache concern (Part B), never a second write path.
- **Core thesis — context, not data, is the unit of decision-making** (INV-CH5-06): the write side's job is to convert data-shaped signal into context-shaped state.
  - *Design consequence:* this is the design rationale for L1's non-interpretation rule (§2A.2) and L2's four converging concerns (§2A.3.1) — the conversion happens exactly once, at assembly, under policy.
- **Composition above, not replacement** (INV-CH5-08): the fabric composes over warehouses, lakehouses, mesh nodes, and operational systems.
  - *Design consequence:* every ingress pattern in §2A.4 is sidecar by construction; no component acquires a write path into a source system; source migration changes ingestion bindings, never fabric architecture (INV-CH8-01).
- **Five-component fabric architecture** (INV-CH5-09): the named Cognitive Context Fabric decomposes into the layered stack this chapter and Part B jointly design.
  - *Design consequence:* the SDK package structure mirrors the decomposition (§2A.1) so the whitepaper's architectural vocabulary is legible in the code layout.
- **Prior art and claimed novelty boundary** (INV-CH5-10): typed six-axis state + operator algebra + governed delivery is the claimed-novel composition.
  - *Design consequence:* each of those three surfaces stays a distinct SDK mechanism (graph primitive, operator algebra in Part B, product contract in Part B) rather than collapsing into a retrieval library — the novelty boundary is preserved by module boundary.

---

### 2A.1 Layered Architecture Frame (L1–L6, two planes)

- **Responsibility:** Fix the responsibility boundaries this chapter designs within. The fabric decomposes into six layers — L1 Signal → L2 Assembly → L3 Graph → L4 Operators → L5 Projection → L6 Products — each owning a single responsibility, artifact, and handoff (INV-CH7-01, Fig-CH07-02). The layers are responsibility boundaries, not a sequential pipeline. Orthogonally, the fabric realizes four concerns — State (§7.3), Computation (§7.4), Interpretation (§7.5), Delivery (§7.6) — as complementary views of one architecture (INV-CH7-09).
- **Protocol/type signatures:** The SDK package structure mirrors the layer stack (CLAUDE.md §10): `ccf.signal` (L1), `ccf.assembly` (L2), `ccf.graph` (L3), with L4–L6 modules designed in Part B. The layered view is realized as module boundaries plus the DI composition root (§2A.5), not as a runtime pipeline object.
- **Invariants enforced:** Layer-boundary discipline — L4 operators are read-only (INV-CH7-11, mechanism in Part B), interpretation is isolated at L5 (INV-CH7-06), delivery happens only via the contracted artifact at L6 (INV-CH7-07, INV-CH7-13). This chapter's write side guarantees the complementary half: nothing above L2 writes graph state (§2A.5). L4/L5/L6 layered-view commitments (INV-CH7-05, INV-CH7-06, INV-CH7-07) and the three per-concern mechanism entries for Computation/Interpretation/Delivery (INV-CH7-11, INV-CH7-12, INV-CH7-13) bind here at the boundary; their primary mechanism design lives in Part B (§2B.1–§2B.3, primary per the traceability matrix), with this section as see-also.
- **Seams:** Control Plane and Data Plane cut across all six layers (INV-CH7-08): policy definitions binding L2, operator parameterization, λ_c calibration, D_c thresholds, and materialization policy are Control Plane configuration; L1 ingestion, L2 assembly, and L3 persistence execute on the Data Plane within those constraints. Runtime plane-separation mechanism is Part B (§7.8 entries); this chapter consumes the separation as a design constraint — every threshold or table named below is a Control Plane value, never SDK code (No-Hardcoding, CLAUDE.md §6.4).
- **D-IMPL rulings embodied:** D-IMPL-01 (Python 3.12+ sole target; typed contracts as Pydantic v2 `extra=forbid`; Protocol-based seams — every signature below assumes it); D-IMPL-04 (two packages, `ccf` library + `ccf-runtime`; fabric core stays sync on the operator path, ingestion adapters may be async in the runtime package).

#### 2A.1.1 Layer handoff summary (write side)

| Layer | Responsibility | Handoff artifact | Owning section | Key entries |
|-------|----------------|------------------|----------------|-------------|
| L1 Signal | ingestion + normalization, no interpretation | `SignalEnvelope` stream | §2A.2 | INV-CH7-02 |
| L2 Assembly | resolution, stitching, policy binding, operator invocation; sole writer | graph mutations via `GraphWriter` | §2A.3, §2A.5.3 | INV-CH7-03, INV-CH7-10 |
| L3 Graph | persisted six-tuple state | `GraphReader` views to L4+ | §2A.5 | INV-CH7-04, INV-CH7-14..21 |
| L4 Operators | read-only typed composition | operator plans / subgraph productions | Part B | INV-CH7-05, INV-CH7-11 |
| L5 Projection | Π role-conditioned interpretation | principal-conditioned payloads | Part B | INV-CH7-06, INV-CH7-12 |
| L6 Products | contracted delivery | typed Context Products | Part B | INV-CH7-07, INV-CH7-13 |

---

### 2A.2 L1 — Signal Layer

#### 2A.2.1 The `SignalEnvelope` contract

- **Responsibility:** Ingestion and event normalization (INV-CH7-02). Heterogeneous sources — transactions, operational events, documents, audio transcripts, external feeds — are expressed in one canonical event envelope. L1 does not interpret: signals carry provenance and temporal markers but no entity/relationship typing. Structured and unstructured streams are co-equal at the ingestion boundary.
- **Protocol/type signatures:** `SignalEnvelope` — a Pydantic v2 `extra=forbid` contract per the D-IMPL-33 ruling: `source` (structured source identity), `ingestion_timestamp`, `observed_time` (optional), `raw_payload` (typed opaque-to-L1), plus `tenant_id` (no untenanted path, INV-CH7-16), an SDK-assigned `envelope_id` (lineage anchoring against the L axis, INV-CH7-14), and an opaque `source_metadata` extension block. Source adapters implement a `SignalSourceProtocol` whose single obligation is emitting valid envelopes; the envelope is the L1→L2 handoff artifact.
- **Invariants enforced:** L1 does not interpret (opaque payload typing makes interpretation structurally unavailable, not merely discouraged); no entity/relationship typing at L1; unstructured and structured co-equal at ingress; every envelope tenant-scoped and lineage-addressable from birth.
- **Seams:** `SignalSourceProtocol` is the pluggable ingress seam — CDC adapters, MCP-source adapters, file/stream adapters, and the Pattern 5 pipeline all terminate in envelope emission (§2A.4). Envelope ids are the terminus the D-IMPL-44 re-hydration recipe references (Part B).
- **D-IMPL rulings embodied:** D-IMPL-33 (envelope schema as ruled — the whitepaper-enumerated core plus `tenant_id`, `envelope_id`, `source_metadata`, `extra=forbid`); D-IMPL-05 (tenant first-class in the envelope; single-tenant is the degenerate one-fixed-tenant case, never a separate mode).

#### 2A.2.2 `SignalSourceProtocol` (the ingress adapter seam)

- **Responsibility:** The single seam every ingress mechanism implements — CDC (§2A.4.1), MCP-source (§2A.4.2), semantic-layer import (§2A.4.3), Pattern 5 persistence stage (§2A.4.4), and user-supplied file/stream adapters. An adapter's whole contract is: connect to a source, emit valid `SignalEnvelope`s, report source identity. It carries no graph access of any kind.
- **Protocol/type signatures:** `SignalSourceProtocol` with envelope emission as the sole output surface; adapters run in `ccf-runtime` (async per D-IMPL-04(b)) while the envelope contract lives in the `ccf` library so both packages share one type.
- **Invariants enforced:** Adapter isolation — an ingress adapter cannot reach L3 (it holds neither `GraphReader` nor `GraphWriter`); source identity recorded per envelope so L records *identity, not location* (INV-CH8-01 source-neutrality); tenant scope required on every emission (INV-CH7-16).
- **Seams:** This is the primary user-extension point on the write side: adopting a new source class means implementing one Protocol, registering it in deployment configuration, and touching nothing else — the ingestion-binding-not-architecture consequence of INV-CH8-03.
- **D-IMPL rulings embodied:** D-IMPL-04 (runtime-package placement); D-IMPL-33 (envelope as the only output type); D-IMPL-05 (tenant-scoped emission).

---

### 2A.3 L2 — Context Assembly

#### 2A.3.1 The four converging concerns

- **Responsibility:** Assembly is where four concerns converge (INV-CH7-03): (1) **semantic resolution** — entity/relationship extraction from the signal stream; (2) **temporal stitching** — observed-time vs valid-time reconciliation producing as-of views with no future-information leakage into historical queries; (3) **policy binding** — principal scope, jurisdiction, and entitlement state attached to every resolved subgraph *at assembly time* ("the fabric does not resolve entities first and then ask who can see them"); (4) **operator invocation** — Context Operators execute here, producing subgraph productions (operator mechanism itself is Part B). L2 is the stage the Algorithmic ⇄ Semantic Alternation actually crosses (INV-CH7-03): both algorithmic structure (traversal, temporal reconciliation) and semantic structure (entity extraction, relationship inference) are active, so L2's internal stages carry the `@algorithmic` lint tags where they are algorithmic (CLAUDE.md §11) — the semantic stages are the only ones permitted an `LLMClientProtocol` dependency (D-IMPL-09).
- **Protocol/type signatures:** An `AssemblyWorker` component in `ccf.assembly` is the sole holder of the `GraphWriter` handle (§2A.5). Its sub-stages are Protocol seams, not subclasses: `EntityResolutionStrategy` (below), a temporal-stitching stage operating on the bitemporal T axis, a policy-binding stage that resolves the in-force policy bundle version from the Control Plane and stamps it onto every resolved subgraph, and the operator-invocation surface (Part B).
- **Invariants enforced:** Scope/policy bound at assembly time, never post-processed; no future-information leakage into as-of views; every graph mutation flows through this component and no other (single-writer, §2A.5).
- **Seams:** Reads envelopes from L1; writes exclusively through `GraphWriter` (D-IMPL-34 interface split); consumes Control Plane policy bundles and λ_c tables as versioned configuration; A2A admissions enter here after consumer-side Control Plane verification (INV-CH8-08 — admission never bypasses L2; the A2A surface itself is designed in §6/§8).
- **D-IMPL rulings embodied:** D-IMPL-41 (Assembly is the one component constructed with a `GraphWriter`); D-IMPL-09 (semantic sub-stages reach LLMs only through `LLMClientProtocol`).

#### 2A.3.2 Entity resolution

- **Responsibility:** Converge fragmented native identifiers from disparate source systems onto a single canonical E node under a tenant-scoped URI, with unstructured claims participating as first-class evidence on par with structured identifiers (INV-CH7-21, Fig-CH07-06).
- **Protocol/type signatures:** `EntityResolutionStrategy` Protocol per the D-IMPL-35 ruling: candidate correlation over *user-declared* identity attributes → canonical `entity-class://` URI (INV-CH7-18 naming forms: `entity-class://<identity-hash>` or `entity-class://<principal>-<discriminator>`), with set-union lineage accumulation on merge. The SDK ships a reference deterministic attribute-correlation strategy driven by user-declared ontology configuration; correlation attribute sets, precedence rules, and probabilistic matching are user configuration or plugins — never SDK values (the whitepaper's LEI/registered-address examples are domain illustration, INV-CH7-21).
- **Invariants enforced:** Canonical-E convergence regardless of querying line of business; URI stability across source-system change with the URI → source-native-identifier mapping preserved in L (INV-CH7-18); resolution is always tenant-scoped (INV-CH7-16).
- **Seams:** Strategy is pluggable per deployment; the Semantic Layer ontology import (Pattern 2, §2A.4.3) supplies the disambiguation vocabulary the reference strategy correlates against.
- **D-IMPL rulings embodied:** D-IMPL-35 (mechanism shipped, correlation values user-supplied).

#### 2A.3.3 Temporal stitching and supersession

- **Responsibility:** Reconcile observed-time against valid-time structurally (not as a retention heuristic), and enact supersession as a logical event: a superseding observation attaches a `superseded_by` edge and `superseded_at` timestamp to the prior claim, which remains in the graph (INV-CH7-21, Fig-CH07-05). Overwrite-in-place is prohibited — it "would make Decision Replay at T+2 years structurally impossible."
- **Protocol/type signatures:** Supersession record shape: prior claim + `superseded_by` edge + `superseded_at` timestamp, required of every `GraphStore` backend by the D-IMPL-34 Protocol surface (semantic 3). Bitemporal T axis: (valid-time, observed-time) per INV-CH7-14.
- **Invariants enforced:** Append-only-forward-with-supersession (INV-CH7-04, INV-CH7-21); as-of reads against T_prior re-render prior state exactly; supersession events are themselves analyzable state (they feed the Policy-event cascade Part B designs against λ_c invalidation).
- **Seams:** Supersession-as-Policy-event is consumed by Part B's half-life/debt machinery and D-IMPL-36 intermediate invalidation.
- **D-IMPL rulings embodied:** D-IMPL-34 (supersession + bitemporal reads are Protocol requirements, not backend conventions).

---

### 2A.4 Ingress Patterns (the non-invasive surface)

The five integration patterns are co-deployed, not alternatives, and every one is sidecar by posture and deployment (INV-CH8-04): the fabric references source-of-record data via L, never replaces sources, and blast radius is bounded by the sidecar boundary. This posture realizes the layering-not-replatforming principle (INV-CH8-03, Fig-CH08-01) against the structurally plural, mid-migration estate that is the operating state, not a transition state (INV-CH8-01). What the estate lacks — and the fabric produces alongside it — is the decision substrate that closes the Forensic Data Gap: policy version in force, supervisory context, freshness at action time, role-conditioned view (INV-CH8-02). Where the estate includes a productized knowledge-catalog substrate, the fabric composes over it per the four-tier pattern with six Tier-2 ⇄ Tier-3 integration mechanics — critically, catalog access-control signals are P *signal*, never P *enforcement*, which stays at Tier 3 (INV-CH8-11).

All ingress terminates in `SignalEnvelope` emission; nothing in this section acquires a write handle (§2A.5).

#### 2A.4.1 Pattern 1 — CDC→G reference ingress

- **Responsibility:** Preferred ingress for transactional systems of record: Debezium-style CDC streams committed transactions from the source's write-ahead log; Assembly normalizes each change into a typed entity/relationship upsert keyed on `(tenant_id, entity_uri)` (INV-CH8-05). The source is undisturbed — no query-path coupling, no schema coupling.
- **Protocol/type signatures:** A `CDCSourceAdapter` implementing `SignalSourceProtocol`, shipped as the v0 reference ingress (CLAUDE.md §13); change events map to envelopes with `observed_time` from the transaction commit and `source` identifying the source system, not its location (INV-CH8-01 source-neutrality).
- **Invariants enforced:** Non-invasiveness is architectural — CDC never touches the source's query path; all resulting writes enter the graph through Assembly only (INV-CH8-05, single-writer).
- **Seams:** Runtime-package concern (async ingestion loop per D-IMPL-04(b)); the specific CDC transport is deployment infrastructure, not SDK mechanism.
- **D-IMPL rulings embodied:** D-IMPL-33 (envelope as the normalization target); D-IMPL-04 (async ingestion in `ccf-runtime`).

#### 2A.4.2 MCP-client ingress (SDK extension, CLAUDE.md §7.1)

- **Responsibility:** Query-based acquisition from content-rich systems (calendars, document repositories, communications archives) via MCP servers front-ending the sources — complementary to CDC (transactional capture). SDK-defined extension of Pattern 3, labeled as such (INV-CH8-07 records the whitepaper's export-only framing and the SDK's bidirectional extension).
- **Protocol/type signatures:** One `ccf` MCP client library serving both L1 ingress and L4–L5 content acquisition per the D-IMPL-13 ruling; at L1 an `MCPSourceAdapter` normalizes MCP resource reads into `SignalEnvelope`s. The client and the egress server live in different modules with different trust postures (INV-CH8-07).
- **Invariants enforced:** Acquisition results reach L3 only via L2 (D-IMPL-13 ruling text); the envelope discipline applies unchanged — MCP-acquired content receives no interpretation privilege at L1.
- **Seams:** The same client surface serves decision-time content acquisition at L4–L5 (Part B); egress and ArtifactStore MCP roles are designed in §6/§8.
- **D-IMPL rulings embodied:** D-IMPL-13 (five-edge MCP role allocation; single client library, two ingress roles).

#### 2A.4.3 Pattern 2 — semantic-layer metadata import

- **Responsibility:** Read through existing semantic-layer investments (dbt, Cube, AtScale, proprietary): metric, dimension, and relationship definitions import as typed entity shapes in G, binding canonical dimensional vocabulary to the E and R registries; domain event streams carrying semantic-layer-shaped events import as metadata events via the same mechanism (INV-CH8-06). Existing semantic-layer consumers are unaffected — the fabric is an additional consumer.
- **Protocol/type signatures:** A `SemanticLayerImportAdapter` implementing `SignalSourceProtocol`; imported definitions land as ontology-vocabulary entities the `EntityResolutionStrategy` reference implementation correlates against (§2A.3.2). Which semantic-layer product is bound is deployment configuration, not SDK mechanism.
- **Invariants enforced:** Reads-through, never replaces (INV-CH8-06); imported vocabulary is candidate structure typed at L2, consistent with the Tier-2-candidates / Tier-3-load-bearing rule (INV-CH8-11 mechanic 2).
- **Seams:** Feeds the user-declared ontology configuration surface that D-IMPL-35 resolution strategies consume.
- **D-IMPL rulings embodied:** D-IMPL-35 (ontology config as the correlation vocabulary's home).

#### 2A.4.4 Pattern 5 — Unstructured Ingestion pipeline

- **Responsibility:** Make document-, audio-, and chat-shaped signal first-class citizens of the graph via the six-stage pipeline: parse → chunk → embed → Policy-before-Similarity retrieval → typed entity/relationship extraction with passage-level source references → graph-persist with passage-level L bound to every edge (INV-CH8-09, Fig-CH08-02/03). Extraction happens at ingestion time, not retrieval time: "the Graph is built from unstructured content, not consulted from it" (INV-CH7-19) — the architectural distinction from RAG.
- **Protocol/type signatures:** Per the D-IMPL-08 ruling, each stage is a Protocol with one opinionated reference pipeline wired from the reference implementations: parser, chunker, embedder (`EmbedderProtocol` per D-IMPL-07, with `(model_id, model_version)` reporting), retrieval (Policy Operator before Similarity Operator, structurally ordered), extraction (`PassageCitationProvider` per D-IMPL-46, designed in Part B's replay context), persistence (through L2/`GraphWriter` only). Passage-level L anchor shapes: `{document, page, paragraph, offset_span}` for documents, `{transcript_id, timestamp, text_span}` for transcripts (INV-CH7-19). The reference-stack vendor choices the whitepaper names (LlamaParse/Docling, voyage-finance-2/BGE-M3) are Control Plane substitution values, never SDK mechanism; what is architectural is the dispatch axis (cloud-agentic vs on-prem-sensitive, decided by data-classification policy), Policy-before-Similarity ordering, typed extraction, and passage-level L binding (INV-CH8-10).
- **Invariants enforced:** Policy-before-Similarity enforced in the retrieval tier as structure, not post-hoc filter (INV-CH8-09); passage-level L on every extracted edge (INV-CH7-19); Mode 1 purity — no LLM invocation in any assembly stage of the pipeline itself (INV-CH8-09; the `@algorithmic` lint's per-stage enforcement targets per the D-IMPL-08 ruling); the fabric never becomes record-of-record for regulated archives — it references WORM archives via L (INV-CH8-10).
- **Seams:** Stage Protocols express the mode variance of the Alternating Derivation Pipeline (INV-CH8-12 — owned by §3; the ingestion substrate is this pipeline); embedder and citation-provider Protocols are shared with Part B's similarity and replay machinery.
- **D-IMPL rulings embodied:** D-IMPL-08 (stage Protocols + opinionated reference pipeline); D-IMPL-07 (EmbedderProtocol with version identity); D-IMPL-46 (citation provider by reference).

---

### 2A.5 L3 — Context Graph and Single-Writer Enforcement

#### 2A.5.1 The `ContextGraph` state primitive

- **Responsibility:** First-class persisted computational primitive — not a cache, not a denormalized view, not an application abstraction (INV-CH7-15, INV-CH7-04). Holds the six-tuple `G(E, R, T, P, Π, L)` in mechanism form (INV-CH7-14, Fig-CH07-03/04): E as URI-addressable nodes with identity persistent across sources and time; R as typed first-class persisted relationships, never derived joins; T bitemporal (valid-time, observed-time); P as policy state traveling with every subgraph; Π as role-conditioned materialized projection state; L as append-only lineage with passage-level anchors for unstructured content. The graph accumulates enrichments across pipeline stages — later passes attach rather than recompute; downstream stages append rather than reconstruct (INV-CH7-15). §8.5's domain lens confirms the primitive is archetype-invariant: different agentic-work archetypes weight the six dimensions differently while the graph primitive stays the same, and L records source identity, not source location — migration-proof by construction (INV-CH8-13, INV-CH8-01).
- **Protocol/type signatures:** Base `ContextGraph` type declaring the six-tuple structure, single-writer write path, lineage-accumulation semantics, and supersession-not-deletion invariant; deployments extend entity-class and relationship-type *enumerations* within that shape via configuration — the whitepaper's banking topology (counterparty/facility/guarantee graph, INV-CH7-20) is a worked domain instantiation demonstrating the mechanism commitments (subclassing shape, per-relationship-type lineage, materiality-as-thresholded-relationship, policy-intersection-at-resolution-time), never SDK content.
- **Invariants enforced:** All six axes persisted as first-class surfaces read simultaneously by every operator composition — not independent graphs stitched query-side (INV-CH8-13); L append-only (INV-CH7-14); append-only-forward-with-supersession (INV-CH7-04).
- **Seams:** Persistence via the `GraphStore` Protocol below; read access via `GraphReader` to L4+ (Part B); hot graph state stays on the graph store, never the ArtifactStore (D-IMPL-27 mutability rule, designed in Part B / §6/§8).
- **D-IMPL rulings embodied:** D-IMPL-02 (Protocol + Postgres reference + SQLite-for-dev); D-IMPL-05 (tenancy structural).

#### 2A.5.2 The `GraphStore` Protocol (storage seam)

- **Responsibility:** Carry the invariant semantics substrate-neutrally; leave all physical layout backend-internal (the whitepaper's "~10 collections" is reference grounding, not a normative count — INV-CH7-15).
- **Protocol/type signatures:** Per the D-IMPL-34 ruling, the Protocol requires exactly six invariant semantics: (1) compound uniqueness on `(tenant_id, entity_uri)` at the persistence tier (INV-CH7-16); (2) idempotent upsert with set-union lineage accumulation (INV-CH7-17); (3) logical supersession with `superseded_by`/`superseded_at` and as-of reads (INV-CH7-21); (4) append-only-forward (INV-CH7-04); (5) per-relationship-type edge lineage (INV-CH7-20); (6) bitemporal read support (INV-CH7-14). Backend-internal: collection/table decomposition, indexing strategy, partitioning. The Protocol exposes **separate `GraphReader` and `GraphWriter` interfaces** — the seam D-IMPL-41 enforcement hangs on. A Protocol conformance test suite verifies all six semantics against both D-IMPL-02 reference implementations.
- **Invariants enforced:** **Tenant invariant** — no code path resolves an entity without tenant scope; uniqueness enforced at the persistence tier, not the application layer (INV-CH7-16). **Idempotent upsert** — the same observation arriving twice produces exactly one persisted entity record; **set-union lineage accumulation** — lineage is deliberately NOT idempotent: multi-source evidence accumulates with per-source timestamps and passage anchors, never overwritten (INV-CH7-17).
- **Seams:** Reference implementations: Postgres (production posture) and SQLite (dev — load-bearing for the §9 examples discipline, per the D-IMPL-02 rationale).
- **D-IMPL rulings embodied:** D-IMPL-34 (six-semantics requirement surface; reader/writer split); D-IMPL-02 (backends); D-IMPL-05 (compound-index tenancy).

#### 2A.5.3 Single-writer enforcement (the D-IMPL-41 stack)

- **Responsibility:** Make "only the Assembly worker holds a write handle to the graph" an enforced architectural property, not a convention (INV-CH7-10): every read-path service is constructed without a write handle, the absence enforced by dependency injection at boot rather than runtime discipline. Deterministic state transitions are the precondition for deterministic replay — if any read-path component could write, graph history would be contaminated by non-Assembly transitions Decision Replay could not reconstruct.
- **Protocol/type signatures:** The four-layer enforcement stack per the D-IMPL-41 ruling: (1) **interface split** — separate `GraphReader`/`GraphWriter` Protocols (D-IMPL-34); read-path constructors accept only `GraphReader`, so write-handle absence is a structural property of the constructor signature (INV-CH7-15); (2) **DI-at-boot** — the composition root constructs exactly one `GraphWriter` and injects it into L2/Assembly only; (3) **static gate** — strict mypy in CI rejects non-L2 `GraphWriter` type references, plus an import lint (same machinery as the `@algorithmic` and harness lints) forbidding the writer module's import outside L2 and the composition root; CI failure is build failure — Python's honest equivalent of build-time prevention; (4) **runtime backstop** — the writer handle is constructed with a boot-time token only the composition root can mint. The residual-honesty note (Python cannot make determined-insider evasion impossible; the claim strength is "no unforced path exists and every forced path fails CI or fails at boot") lands in DESIGN.md's Invariant Preservation chapter per the ruling.
- **Invariants enforced:** **Single-writer enforcement at boot** — the named architectural invariant (INV-CH7-10, INV-CH7-15). The invariant holds across every boundary that might otherwise erode it: **A2A admission** — an inbound A2A Context Product is verified at the consumer's Control Plane and then enters L3 only through L2, never directly (INV-CH8-08; CLAUDE.md §10); **harness effect capture** — no harness ever acquires a write handle; adapter effect capture routes through governed emission or L2 write-back (CLAUDE.md §7.3 seam 3; D-IMPL-25's `effects: unsupported` declaration is a verified capability, not an unimplemented seam); **ArtifactStore** — the store is a persistence substrate behind mechanism, never a second writer (CLAUDE.md §7.4); **HTTP surface** — L1 ingestion is deliberately absent from the v0 HTTP API because a generic write endpoint would invite a second writer path (D-IMPL-23 ruling).
- **Seams:** The composition root is the one place `GraphWriter` is visible outside `ccf.assembly`; the write path is rendered in `docs/diagrams/seq-single-writer-write-path.mmd` (D-09 sequence diagram).
- **D-IMPL rulings embodied:** D-IMPL-41 (the stack itself); D-IMPL-34 (the interface seam); D-IMPL-25 and D-IMPL-23 (boundary-preserving rulings cited above); D-IMPL-16 (verify-every-admission — no fast path that could weaken the L2-only entry).

---

#### 2A.5.4 The write path, end to end

The complete write path — rendered as the D-09 sequence diagram in `docs/diagrams/seq-single-writer-write-path.mmd` — composes the components above into the one route by which anything becomes graph state:

1. **Signal arrives.** A source event reaches an ingress adapter: CDC change event (§2A.4.1), MCP resource read (§2A.4.2), semantic-layer definition (§2A.4.3), or an unstructured document entering the Pattern 5 pipeline (§2A.4.4).
2. **L1 normalizes.** The adapter emits a `SignalEnvelope` (D-IMPL-33): tenant-scoped, lineage-addressable, payload opaque. No interpretation has occurred (INV-CH7-02).
3. **L2 assembles.** The Assembly worker runs the four concerns in sequence for the affected substate: entity resolution via `EntityResolutionStrategy` (INV-CH7-21, D-IMPL-35), temporal stitching against the bitemporal T axis (INV-CH7-03), policy binding stamping the in-force Control Plane bundle version onto the resolved subgraph (INV-CH7-03), and — on the read side of assembly — operator invocation (Part B).
4. **L3 persists.** The single `GraphWriter` handle executes an idempotent upsert keyed on `(tenant_id, entity_uri)` (INV-CH7-16, INV-CH7-17); lineage accumulates by set-union; superseded claims receive `superseded_by`/`superseded_at` edges and remain (INV-CH7-21, INV-CH7-60).
5. **Refused paths.** Two boundary cases demonstrate the invariant rather than merely asserting it: an inbound A2A Context Product must pass consumer-side Control Plane verification (D-IMPL-16) and then enters the graph *through L2 as an admission*, never via a direct L3 write (INV-CH8-08); a harness attempting effect capture finds no write handle in existence outside the Assembly worker — its outputs route through governed emission or L2 write-back (D-IMPL-25), and a conforming read-only adapter declares `effects: unsupported` as a verified capability.

Every step is deterministic given the envelope stream and the in-force Control Plane versions — which is precisely what makes the write path replayable (INV-CH7-10) and the D-IMPL-44 re-hydration recipe (Part B) expressible as envelope ids + pinned versions.

---

### 2A.6 Design Constraints Carried Forward

Constraints §2A's design imposes on the sibling chapters, verified at synthesis for seam consistency:

- **Part B (L4–L6, replay):** `GraphReader` is the only graph access L4+ receives (§2A.5.2/§2A.5.3); operator purity (INV-CH7-11) is therefore structurally assisted — there is nothing to mutate through. Supersession events (§2A.3.3) are the invalidation input for λ_c cascade and D-IMPL-36 intermediate caches. `envelope_id` (§2A.2.1) is the terminus the D-IMPL-44 recipe references.
- **§3:** The Alternating Derivation Pipeline (INV-CH8-12) consumes the Pattern 5 stage Protocols (§2A.4.4) as its Perception substrate; archetype fabric-interaction patterns never include a write handle.
- **§4/§5:** Workflow and HITL state persist at the Control Plane boundary (D-IMPL-18), not in the graph — nothing in orchestration touches `GraphWriter`.
- **§6/§8:** The A2A admission seam terminates at L2 (§2A.5.4 step 5); the MCP client library is shared between L1 ingress (this chapter) and L4–L5 acquisition plus Experience surfaces (§6/§8) per D-IMPL-13; the ArtifactStore never holds live graph state (D-IMPL-27) and never becomes a second writer; the v0 HTTP API carries no ingestion endpoint (D-IMPL-23).

---

## 2B. The Read Side (L4–L6, Half-life/Debt, Replay, Closed Loop)

Scope of §2B: the read side of the fabric pillar — L4 Context Operators, L5 Context Projection, L6 Context Products — plus Context Half-life λ_c and Context Debt D_c, the five-dimension Decision Replay record and replay engine, Closed-Loop Self-Learning, and the cross-cutting Control Plane / Data Plane separation. §2A owns L1–L3, ingestion, the graph, and single-writer scope. Contract altitude throughout — no implementation code (locked D-05/D-06/D-07). Owned-entry coverage contract: the traceability matrix at the end of this document.

---

### 2B.1 L4 — Context Operators (System of Computation)

#### Component: Operator algebra and the four canonical categories

- **Responsibility:** Typed, composable, read-only computation over the Context Graph. Four canonical categories cover the operation space (INV-CH7-22): **Traversal** — bounded relationship walks `Traversal(relationship-types, depth-limit, materiality-threshold)` producing bounded-expansion-of-relevance, never exhaustive expansion (INV-CH7-24); **Temporal** — bitemporal valid-time/observed-time reconciliation `Temporal(as-of-T)` as a correctness semantic, not a TTL filter (INV-CH7-25); **Policy** — principal/jurisdiction/entitlement subgraph **substitution** at the graph layer, never a row-level filter (INV-CH7-26); **Similarity** — corpus-scoped ranking `Similarity(threshold)` with the index version pinned in L and the determinism contract tuple `(corpus_version, embedding_model_version, query, threshold, policy_regime) → same result` (INV-CH7-27).
- **Protocol/type signatures (contract altitude):** `ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity` with ∘ read right-to-left; three- and four-operator compositions are normal — the algebra defines the composition surface, a request picks from it (INV-CH7-23). Each operator is typed in inputs, outputs, and its side-effect-free read-only-**sync** contract against the graph (INV-CH7-22); per the D-IMPL-04 ruling the operator/projection path stays sync inside the async-first runtime.
- **Invariants enforced:**
  - **Composition-preservation `(A∘B)(G) = A(B(G))`** is a design property verified empirically for every shipped operator pair (CLAUDE.md §11): intermediates are individually replayable, cache-coherent under λ_c-driven invalidation, and lineage-complete — each intermediate carries its own provenance sub-chain (INV-CH7-23). The layer-boundary discipline of INV-CH7-06 and the operator-purity commitment of INV-CH7-11 carry forward here: L4 reads L3, never writes it.
  - **Policy-before-Similarity ordering** — similarity ranks only over the principal-permissible subgraph; "no filter runs after retrieval because no retrieval of inadmissible content happened" (INV-CH7-26). The governance-side restatement (MNPI leakage structurally prevented, not post-hoc mitigated) is INV-CH8-17.
  - **Function-determinism** — "determinism is a property of the function, not the value": `(graph_state, control_plane_config, temporal_boundary, execution_plan) → bit-for-bit identical ContextProduct`, with legitimate value-variance from bitemporal state and decay explicitly expected (INV-CH7-31).
  - The four worked compositions (covenant cross-reference, intraday liquidity, AML Policy-before-Similarity, credit-exposure traversal — INV-CH7-30) are design-space demonstrations; their thresholds (0.85/0.75) and regimes are illustrative domain values, never SDK constants.
- **Seams:** `SimilarityIndex` Protocol per the D-IMPL-03 ruling — reference implementation on sqlite-vec (dev default), Chroma second if budget allows; vendor-neutral corpus/index versioning with version-pinned reads is a Protocol obligation (required by the INV-CH7-27 determinism contract and by D-IMPL-06 similarity-index snapshotting). Embeddings via `EmbedderProtocol` per the D-IMPL-07 ruling with `(model_id, model_version)` reporting as a contract obligation. Operator parameters (materiality floors, thresholds, temporal-boundary rules) are typed, versioned `OperatorParameterSet` Control Plane artifacts per the D-IMPL-38 ruling — declared schemas, no SDK-side domain defaults, in-force version captured in L per invocation.
- **D-IMPL rulings embodied:** D-IMPL-03, D-IMPL-04, D-IMPL-07, D-IMPL-38.

#### Component: Operator Plan DAG generator (Planner) and registry

- **Responsibility:** Given agent intent (role, decision class, entity reference), select required operators from the registry, topologically order them into a dependency-correct plan (Policy before Similarity; Temporal before Traversal where Traversal reads temporally-reconciled state), and hand the plan to the projection engine (INV-CH7-28). Batch-resolve operator references DataLoader-style — one query per operator type per call (INV-CH7-29).
- **Protocol/type signatures:** `planOperators(agent_intent: {role, decision_class, entity_ref}, operator_registry) -> OperatorPlan` (INV-CH7-28).
- **Invariants enforced:** Boot-time-loaded registry with fail-fast duplicate registration — duplicate key is a boot failure, never a runtime request error (INV-CH7-29). Plan generation is deterministic because the registry is deterministic at runtime.
- **Seams:** Registry population is an explicit boot-time `register(operator_key, operator)` API at the composition root per the D-IMPL-37 ruling — no entry-point or import-side-effect registration in v0; the Control Plane declares which registered operators are permitted/parameterized, but code registers them. Intermediate materialization is a deterministic cache keyed on `(tenant, operator_key, parameter_set_version, input_intermediate_keys, graph_snapshot_id)` per the D-IMPL-36 ruling: a cache hit is by construction the value replay would produce; invalidation rides the supersession/Policy-event cascade lazily; when-to-cache, retention, and eviction budget are per-class Control Plane values under D-IMPL-38. The Planner's intermediate-reuse decision at the composition-preservation checkpoint (Fig-CH07-10) reads this cache (INV-CH7-33 end-to-end sequence: intent → OperatorPlan → four-operator execution in dependency order → Π → contract-validated product → TTL cache write).
- **D-IMPL rulings embodied:** D-IMPL-36, D-IMPL-37, D-IMPL-38.

#### Component: Operator realization neutrality (swarm-realized operators)

- **Responsibility:** The algebra is the determinism surface; valid operator realizations include code-and-pipeline, SQL-backed, graph-traversal, and agent-swarm operators, provided the typed output contract (schema + λ_c + passage-level L) holds regardless of internal realization (INV-CH7-32, see also §3 which owns this entry's agent-side design). Policy-before-Similarity holds inside every swarm step; per-product mode selection belongs to §7.6 Mode 3 (INV-CH7-55). Decision-time content acquisition by operators uses the MCP client surface per the D-IMPL-13 ruling — the same client library as L1 ingress, serving L4–L5 acquisition; acquisition results reach L3 only via L2, so single-writer is unaffected. The search ⇄ inference recursion of INV-CH6-07 is engineered here: every loop iteration is a contracted Context Product request; agents never self-assemble context.
- **D-IMPL rulings embodied:** D-IMPL-13.

---

### 2B.2 L5 — Context Projection (Π, System of Interpretation)

- **Responsibility:** Π is a typed transformation performing subgraph **substitution**, not filtering: its output is itself a valid Context Graph for the principal — construct once, interpret many (INV-CH7-40). Role-shaped views condition at runtime on the tuple (role, intent, temporal context, policy regime), avoiding both precompute-everything and resolve-at-read-time failure modes (INV-CH7-43).
- **Protocol/type signatures:** The `ProjectionPlan` structural interface — any type exposing `required_operators()` + `invoke()` qualifies; dispatch is structural typing, never inheritance; every registered projection returns a typed `ContextProductContract` subclass (INV-CH7-41). Two-stage execution: the Operator Plan answers "what is true" (principal-agnostic, memoizable); the Projection Plan answers "what that truth means in this decision context" (principal-conditioned), reading operator-produced metadata during invocation — neither concern leaks into the other (INV-CH7-42).
- **Invariants enforced:** Output of Π composes with the operator algebra as if it were the full graph — no leak-by-absence (INV-CH7-40). Projection is stateless by invariant — no write locks, no in-process cache; materialization lives in a separately gated tier (INV-CH7-73(b)). Every projection's lineage (plan_id, operators_invoked, policy_version, graph_snapshot_at) lands in the Contract. The Contract is the output stability layer: operator re-implementation, graph-class extension, and policy versioning all evolve behind the Contract boundary (INV-CH7-44).
- **Seams:** Plan selection uses the canonical deterministic signature `(perspective, context_product_class, selection_params)` per the D-IMPL-49 ruling — perspective is channel-1 axis 3; `selection_params` is an optional typed block declared per product class under the D-IMPL-38 discipline; free intent inference is out of v0 scope (intent, where needed, is a declared enum-valued selection parameter). `(perspective, product_class, selection_params, plan_version)` fully determines the selected plan, preserving replay determinism. **DESIGN.md obligation carried per the D-IMPL-49 ruling:** swarm-level intent decomposition is an orchestration-layer concern and a NAMED post-v0 extension candidate — intent compiles down to concrete product requests carrying this signature; coordination stays above Π; replay stays deterministic (cross-reference: §4).
- **D-IMPL rulings embodied:** D-IMPL-49, D-IMPL-38, D-IMPL-07 (embedder identity feeds projection-time similarity acquisition).

---

### 2B.3 L6 — Context Products (System of Delivery)

#### Component: ContextProductContract

- **Responsibility:** The typed delivery contract every projection returns. Per the **D-IMPL-30 ruling the specification has nine elements including Assembly Mode** (INV-CH6-03): Schema, Freshness SLA, TTL, Policy Binding, Lineage, Semantic Versioning, Discovery, Addressability, Assembly Mode. The "eight-element" references (including CLAUDE.md §5's) are recorded as an annotated editorial-drift discrepancy per that ruling; the Fig-CH07-13 seven-field typed base (INV-CH7-45) is a different artifact — base contract *fields* vs. specification *elements* — and the mapping is: `schema_name`/`schema_version` realize Schema and Semantic Versioning; `expires_at` + `ttl_anchor` realize TTL; `lineage {operators_invoked, policy_version, graph_snapshot_at}` realizes Lineage and carries the Policy Binding version; `plan_id` binds the product to its projection (Π identity); `payload` is per-product typed; Freshness SLA, Discovery, Addressability, and Assembly Mode are class-level registration properties maintained by the Control Plane at product-class registration, surfaced through the registry and egress surfaces rather than as instance fields. A Context Product is a typed, governed, decision-ready unit of meaning shaped jointly by Intent, Perspective, Time, and Policy (INV-CH6-02) — the category-change answer to data products: runtime-assembled, TTL-bound, policy-formative, entitlement-formative (INV-CH6-01).
- **Protocol/type signatures:** `extra=forbid` typed base (Pydantic v2 per the D-IMPL-01 ruling); fields: `schema_name` (classvar), `schema_version` (semver), `plan_id`, `expires_at`, `ttl_anchor ∈ {from_decision, from_entity_freshness}`, `lineage`, `payload` (INV-CH7-45). Per-product independent semver lanes — a version bump on one product class never touches another (INV-CH7-49).
- **Invariants enforced — the three validation gates (verbatim):**
  1. **empty-operator guard** — rejects a Contract whose `operators_invoked` is empty; refusal is a structured rejection, never silent acceptance (INV-CH7-46).
  2. **lineage strict equality** — declared `operators_invoked` set must equal the engine-resolved operator set; forgery, omission, and drift all fail; passage-level anchors verified for every unstructured-derived claim (INV-CH7-47; restated at the plane boundary as INV-CH7-73(c); L6-gate placement per INV-CH7-13).
  3. **TTL bounds** — `now < expires_at ≤ now + MAX_TTL`, re-verified at cache-write time (INV-CH7-48). Per the **D-IMPL-39 ruling** MAX_TTL is required Control Plane configuration per product class — no SDK default; an unregistered MAX_TTL fails Control Plane validation at product-class registration; the in-force MAX_TTL version lands in the policy-bindings replay dimension.
  No invalid product reaches an agent, enters the cache, or contaminates the replay record; the canonical three-gate sequence — empty-operator guard, lineage strict equality, TTL bounds — runs before any cache write or delivery, and the cache lookup key is the composite `(tenant, schema_name, plan_id, graph_snapshot_id, principal binding)` (INV-CH7-52) — tenant-first per the D-IMPL-05 ruling.
  TTL granularity follows the **D-IMPL-31 ruling**: two granularities with a declared per-class derivation rule — signal-level validity envelopes derived from type λ_c, and product-level `expires_at = min(class MAX_TTL ceiling, derivation over constituent signal validities)`, with constituent-validity floors whose breach refuses assembly (the mixing-refusal rule) rather than emitting a product fresher-labeled than its stalest load-bearing constituent (INV-CH6-04 Step 4).
- **Seams:** Egress via in-process call, the MCP egress server (L6 Context Products as Resources, permitted agent invocations as Tools, per the D-IMPL-13 ruling — one server, two resource families; INV-CH8-07 Pattern 3), or A2A endpoint (§8 owns the transport design). MCP remains the access layer, CCF the construction layer — MCP never manages state, enforces temporal logic, applies policy, or constructs context (INV-CH6-06, owned by §6/§8; noted here as the L6 boundary).
- **D-IMPL rulings embodied:** D-IMPL-30, D-IMPL-31, D-IMPL-39, D-IMPL-01, D-IMPL-05, D-IMPL-13.

#### Component: SLO envelope, materialization, and cost discipline

- **Responsibility:** The illustrative SLO envelope (p99 300ms interactive; 2s async; 10K products/s/cluster; materialization ≤ N% compute; cache-hit ≥ M% within the λ_c window) is a calibration envelope, never shipped constants (INV-CH7-50). The Control Plane maintains a per-class materialization policy driven by half-life × access frequency, derivation cost envelope, and regulatory supersession triggers; the four-state cache lifecycle Fresh → Near-Expiry → (InvalidatedBySupersession | expiry) → Re-Derived is the coherency state machine (INV-CH7-51). Per-class cost bands (×1 / ×3–5 / ×2–4 / ×8–15) are illustrative calibration multiples (INV-CH7-53).
- **Invariants enforced:** No serving from cache past the λ_c window or after supersession without re-derivation; supersession transitions are Policy events from the Control Plane; cache hits are recorded in lineage (INV-CH7-51). Materialization policy is Control Plane configuration under the D-IMPL-38 discipline; the intermediate cache substrate is native (hot, mutable) per the D-IMPL-27 mutability split.
- **D-IMPL rulings embodied:** D-IMPL-27, D-IMPL-36, D-IMPL-38.

#### Component: Algorithmic ⇄ Semantic Alternation and the three Assembly Modes

- **Responsibility:** Strict alternation of algorithmic and semantic stages: no semantic stage operates on raw signal; no algorithmic stage performs semantic interpretation; every pipeline transition crosses the boundary exactly once (INV-CH7-54; lifecycle-level statement INV-CH6-04; agent-side application in the Alternating Derivation Pipeline, INV-CH8-12, owned by §3). CI enforcement: the `@algorithmic` import lint rejecting any LLM-client import in algorithmic modules (CLAUDE.md §11), with `LLMClientProtocol` per the D-IMPL-09 ruling as the single crisp import target.
- **Assembly Modes:** Mode 1 pure algorithmic; Mode 2 algorithmic assembly with LLM packaging (four pinned primitives: model version, temperature, prompt logged/hashed, output hash); Mode 3 algorithmic orchestration with agent-swarm assembly (INV-CH7-55, ninth contract element per D-IMPL-30). Trust-path purity holds across modes — the algorithmic substrate, never the probabilistic presentation, is the artifact-of-record; per-mode replay footprints and the five mixed-mode disciplines are carried into the replay design below (INV-CH7-56). Mode 3 cross-org assembly egresses at L6 over A2A (transport design in §6/§8).
- **D-IMPL rulings embodied:** D-IMPL-09, D-IMPL-30.

---

### 2B.4 Context Half-life λ_c and Context Debt D_c

#### Component: Half-life machinery

- **Responsibility:** Formal decay model `R(t) = R₀ × (1/2)^((t − t₀) / λ_c)` — probabilistic decision-relevance decay, not a binary fresh/expired check; re-observation resets the clock; discrete implementation as the sequential-window observer-buffer returning freshness-weighted composites (INV-CH7-57). λ_c is **Control Plane configuration per observation type, never code** (INV-CH7-58); the configuration surface shape is the (type, band, dominant decay driver, supersession event) row — the shape is the commitment, the numbers are domain values out of SDK scope (INV-CH7-59). λ_c is not a TTL: data past its λ_c remains accessible for historical reconstruction (replay depends on this) while not counting as current (INV-CH7-57).
- **Supersession:** a Policy event, not just time decay — logical supersession via `superseded_by`/`superseded_at`, versioned Control Plane invalidation events cascading through Data Plane cache coherency, lazy re-derivation, never eager (INV-CH7-60; graph-side append-only supersession is owned by §2A). Bitemporal enforcement at the mutation boundary makes the fabric a temporal abstraction layer over unaligned source cadences (INV-CH8-14): "real time" is a property of assembly at moment of use, not of the data.
- **D-IMPL rulings embodied:** D-IMPL-38 (λ_c tables as versioned parameter artifacts follow the same declared-schema, no-silent-default discipline).

#### Component: Debt machinery and Conditional Assessment Routing

- **Responsibility:** `D_c = 1 − (C_available / C_required)` basic form (INV-CH7-61); extended multiplicative form `D_c = 1 − (F · C · S)` with freshness, completeness, and semantic-consistency factors composing conjunctively — any factor at zero drives D_c to 1 (INV-CH7-62). The multiplicative-conjunctive form is a defended architectural choice; the weighted-additive alternative is **rejected, not a tuning preference** (INV-CH7-63). Three runtime debt components roll up into F/C/S: data-source-availability-debt, as-of-time-staleness-debt, entity-resolution-confidence-debt — with failed-retrieval attempts recorded in lineage and the no-activity vs source-failure disambiguation architecturally required (INV-CH7-64).
- **Protocol/type signatures:** Per the **D-IMPL-47 ruling**, per-factor `DebtFactorScorer` Protocols with SDK reference computations (F from decay-ratio aggregation; C from declared-slot coverage; S from detected-contradiction rate), versioned `(scorer_id, scorer_version)` identity, class→scorer-version binding updatable via the Control Plane, per-class custom-scorer override through the same seam, and replay pinning of the scorer version in force. Trust Triangle leg strengths derive from the same three components (INV-CH7-66 debt-mapping), and the `TrustScorer`/`LegScorer` Protocol surface with conjunctive combinator per the D-IMPL-32 ruling ships with reference leg scorers derived from F/C/S — zero new measurement machinery.
- **Routing:** CAR consumes D_c, decision-class threat level, and relevant-signal count into the verbatim four-state predicate chain Skip / Conditional / Standard LLM / Forced LLM (INV-CH7-65 — owned by §4/§5 for the escalation pathway; the D_c drive mechanism is designed here). Per the **D-IMPL-40 ruling** the threat-level scale (ordered enum with designated LOW-or-below band) and class-specific D_c thresholds in [0,1] are Control Plane configuration per decision class; the SDK ships only the routing mechanism. Governance-side restatement: bypass/conditional/forced-escalation pathways with the routing decision itself landing in the replay record (INV-CH8-16). Conservative bias and Fail-Closed under elevated D_c: debt is a risk amplifier; uncertainty is surfaced and routed into escalation, additional-source-fetch, or decision-decline, never smoothed (INV-CH7-67 — HITL wiring owned by §4/§5). Debt cascades across multi-agent handoffs with D_c recomputed at every handoff boundary against inherited plus new observations (INV-CH7-68 — handoff design owned by §4/§5). Agent-level fail-closed thresholds are specialization axis 5 (half-life and debt profile) per CLAUDE.md §6.2.
- **D-IMPL rulings embodied:** D-IMPL-32, D-IMPL-40, D-IMPL-47, D-IMPL-38.

---

### 2B.5 Decision Replay (Five Dimensions + SDK Extensions)

#### Component: The replay record

- **Responsibility:** Every decision is forensically reconstructible years later against the exact fabric state at decision time — enforced at assembly time, at every Context Product boundary, and at the plane interface, never bolted on (INV-CH7-79). The five dimensions are inviolate (INV-CH7-80): (1) **Context Fabric Snapshot** — the touched `G(E, R, T, P, Π, L)` substate at t (INV-CH7-81); (2) **Policy Bindings Snapshot** — version identifiers + serialized parameters of all active policies (INV-CH7-82; HITL actions extend this dimension per CLAUDE.md §8.2 — HITL record design owned by §4/§5); (3) **Model Version Record** — every invoked model, "none"/"N/A" for Mode 1 (INV-CH7-83); (4) **Perspective Conditioning** — agent identity, role, tools, delegation chain (INV-CH7-84 — owned by §3 for the agent-version/skill-set extensions; the dimension contract is designed here); (5) **Content Generation Path** — input identifiers, reasoning trace, structured output (INV-CH7-85; workflow step sequences extend it per CLAUDE.md §8.1).
- **Environment replay, not model trace:** CCF reconstructs the decision environment; the model's internal trace belongs to external tooling. The composition seam is the `TraceCorrelationHook` on dimension 5 at the harness adapter's replay-hooks seam, storing a typed external trace reference per LLM invocation, per the D-IMPL-45 ruling (INV-CH7-86 — seam design owned by §6/§8).
- **Passage-level lineage:** every unstructured-derived claim carries passage-level L anchors; the Evidence Chain (claim → passage-level L → citation reference → WORM source passage) is reconstructible in reverse at audit time; the provider is pluggable via the `PassageCitationProvider` Protocol per the D-IMPL-46 ruling — Anthropic Citations adapter plus deterministic post-hoc span-matcher as reference impls (INV-CH7-87).
- **Per-mode footprints:** Modes extend, never modify, the five-dimension baseline; Mode 2 adds the four pinned LLM-rendering primitives; Mode 3 adds orchestration plan id, per-agent version manifest, and contribution boundary markers with recursive per-agent records; replay is mode-invariant on one record format (INV-CH7-88 — Mode 3 record composition shared with §4/§5). The AML SAR triage worked example is the canonical end-to-end composition (INV-CH7-90). Replay renderings for three audiences are three Π projections of one record — the §7.5 primitive recursively applied, never three records (INV-CH7-91 — rendering surface owned by §6/§8).

#### Component: Snapshot strategy and artifact resolution — exact versions, never "latest"

- **Responsibility:** Per the **D-IMPL-06 ruling**, snapshots are **logical by construction**: `graph_snapshot_id` = temporal boundary + tenant + store-state watermark, plus the touched-substate manifest already enumerated by lineage strict equality — never a physical graph copy. The full-fidelity tier additionally materializes the touched substate as a content-addressed ArtifactStore artifact; similarity-index snapshots are the version pinned in L with version-pinned reads a `SimilarityIndex` Protocol obligation (D-IMPL-03).
- **Addressing:** per the **D-IMPL-26 ruling**, hybrid: content-addressed canonical identity `sha256(canonical_serialization)` plus versioned-URI naming `ccf-artifact://{tenant}/{artifact_class}/{name}@{artifact_version}` through an append-only Control Plane mapping. **`@latest` is permitted only at authoring surfaces — a replay record or lineage entry never stores "latest"; it stores the hash** (URI carried as annotation). Replay resolution therefore resolves exact artifact versions by hash: graph snapshot, policy bundle version, agent version, skill-set, prompt-artifact versions — `docs/diagrams/seq-replay-resolution.mmd` renders this sequence.
- **Substrate split:** per the **D-IMPL-27 ruling**, immutable replay-relevant artifacts route through the ArtifactStore; hot mutable state stays on native Protocols. **Determinism-obligation note (INV-CH7-80/89 dependency):** the ArtifactStore seam design (owned by §6/§8) must preserve replay determinism per D-IMPL-26.
- **Lifecycle:** per the **D-IMPL-50 ruling** the SDK ships the fidelity-lifecycle engine above the ArtifactStore Protocol: three-tier compression (Full fidelity / Compressed / Tombstoned), the never-compress/never-tombstone severity exemption enforced in mechanism, and the structural `retention-reason` field on every transition (INV-CH7-89); retention windows, severity thresholds, and tombstone minima are Control Plane values. Governance-side statement of the same lifecycle with the WORM-archives-remain-records-of-record constraint: INV-CH8-20 (replay-anchor retention lifecycle at scale). Regulatory regime → artifact mapping is discharged by these primitives; specific regime bundles are user policy configuration, not SDK content (INV-CH8-15).
- **Cold-archive re-hydration:** per the **D-IMPL-44 ruling**, every compressed record carries a typed `ReHydrationRecipe`; re-hydration re-runs L2 assembly against archived source signals under pinned Control Plane versions and verifies bit-for-bit against the stored hash — or fails loudly; `ColdSourceArchiveProtocol` is the pluggable archive seam with a file-backed dev impl.
- **D-IMPL rulings embodied:** D-IMPL-06, D-IMPL-26, D-IMPL-27, D-IMPL-44, D-IMPL-50, D-IMPL-03.

---

### 2B.6 Closed-Loop Self-Learning

- **Responsibility:** "The loop is in the graph, not the model." Closed-loop learning flows exclusively through the Control Plane as logical graph write-back — never direct runtime modification of operators/projection/policy, never model retraining (INV-CH7-75). Three-stage pattern: typed `OutcomeSignal` (with provenance, `observed_at`, its own λ_c) → Control Plane interpretation → versioned update → Data Plane propagation with `projection_plan_id` + `contract_version` attribution so historical decisions re-trace against the version in force when made.
- **Signal taxonomy:** per the **D-IMPL-42 ruling** the prose taxonomy is canonical — typed enum `OUTCOME | CONTEXT_VALIDITY | AUDIT_LINEAGE` — with the Fig-CH07-24 handler names (Outcome/Correction/Metadata) documented as dispatch-side aliases in an alias table (INV-CH7-76). One-event-one-handler routing; structurally distinct graph-write targets per category; no gradient descent, no weight update.
- **Refinement targets:** exactly four Control-Plane-owned targets — operator refinement, projection optimization, policy calibration, half-life adjustment (INV-CH7-77). Agents appear to improve because the context they consume improves.
- **Governance:** per the **D-IMPL-43 ruling** the interpretation step is configurable per learning-signal class, **defaulting to human-gated** (workflow with an ApprovalGate; Control Plane policy may configure specific signal-class × parameter-class × bounded-delta combinations as auto-applied under tier-1 bounds validation per D-IMPL-38). Every update — gated or auto — is a versioned Control Plane action in the audit plane; learning runs through the same governance regime (versioning, approval, staged propagation, rollback) as initial configuration — no separate learning regime (INV-CH7-78). ApprovalGate mechanics are owned by §4/§5.
- **D-IMPL rulings embodied:** D-IMPL-42, D-IMPL-43, D-IMPL-38.

---

## 3. Pillar: Core Agent Types

Component diagram: `docs/diagrams/pillar-agent-types.mmd`.

**Extension status:** The entire Agent Specialization Framework is **SDK-defined, cites CLAUDE.md §6** — the whitepaper's Chapter 3 describes agents as consumers of the fabric; it does not specify a framework for building specialized agents. Every component below is labeled with its CLAUDE.md anchor and its whitepaper hook (per the SPEC_INVENTORY "SDK Extensions and Whitepaper Hooks" table).

**Provisional flagging:** all five governing rulings (D-IMPL-11, D-IMPL-12, D-IMPL-19, D-IMPL-28, D-IMPL-29) are RESOLVED by Dave (2026-07-25) — none provisional; no D-04 blockquote flags are required in this chapter (cross-checked against the Phase D provisional register: zero provisionals).

**Phase discipline:** contract altitude only. No implementation code in this chapter; type surfaces are named signatures, not bodies.

---

### 3.1 The unified `Agent` base and the archetype shape

*SDK-defined, cites CLAUDE.md §6.1, §6.3. Whitepaper hook: Ch 3 agents-as-consumers; §6.5/§6.6 consumption discipline (INV-CH6-05, INV-CH6-07).*

- **Responsibility:** A single concrete runtime class, `Agent`, is the factory's only output type. It carries the agent's identity, version, composed archetype list, channel-1 specialization record, and currently-bound skill-set. It implements **no reasoning loop** — the loop belongs to the harness (CLAUDE.md §6.5, §7.3); `Agent` is the fabric-side representation the harness adapter binds against.
- **Protocol/type signatures:** `Agent` (concrete, final — no user subclassing); `ArchetypeComponent` (Protocol) — a typed behavior bundle exposing `fabric_interaction_pattern()`, `replay_obligations()`, and `configuration_defaults()`; archetypes conform structurally, never nominally.
- **Invariants enforced:** archetype/agent separation is structurally safe precisely because there is nothing to subclass (D-IMPL-11 rationale). `/src` contains archetypes and the `Agent` class; it never contains an agent instance or definition — an agent found in library code is a defect of the same severity as a hard-coded half-life table (CLAUDE.md §6.1). Everything distinguishing one agent from another is serialized in its definition artifact, which is what makes replay dimension 4 capture mechanical (INV-CH7-84).
- **Seams:** code-level extension happens only via Protocol seams — skills (§3.7 below), harness adapters (§6/§8), and `ArchetypeComponent` implementations. Agents reach the fabric through the MCP access layer, never by direct graph access (INV-CH6-06, owned by §6/§8).
- **D-IMPL rulings embodied:** **D-IMPL-11** (RESOLVED — single concrete `Agent` class specialized entirely by artifact; archetypes as Protocol-typed composable behavior bundles; no class hierarchy).

The consumption discipline the base enforces is the whitepaper's (INV-CH6-05, §6.5): *"Agents do not consume data directly. They consume context."* The `Agent` base exposes exactly one fabric-read surface — contracted Context Product requests — and no raw-store query surface. The seven Context Product key principles (Runtime Construction, TTL, Policy-embedded, Entitlement-aware, Discoverable, Traceable, Interoperable) are properties of the products the agent consumes, upheld on the fabric side (§2B); the agent framework's obligation is the negative one: **no path from `Agent` to L1–L5 exists** — TTL-expired products are contract-invalid, not stale, so the base refuses them rather than degrading (INV-CH6-05 invariant).

### 3.2 The six archetypes

*SDK-defined, cites CLAUDE.md §6.3. Whitepaper hooks per the SDK Extensions table: §7.4.9 swarm operators + §6.6 recursive enrichment (ContextAssembly); §7.10.3 passage-anchored generation (ContentGeneration, DocumentIntelligence); §7.7 λ_c re-evaluation (Monitoring); T-dimension analysis (Analytics).*

Each archetype is an `ArchetypeComponent` bundle: an execution shape, a fabric-interaction pattern, and replay obligations — no identity, no prompts, no skills, no policy bindings, no domain values (CLAUDE.md §6.1). Archetype weighting of the six graph dimensions varies while the graph primitive stays constant (INV-CH8-13, owned by §2A — the graph lens on agentic work).

| Archetype | Fabric-interaction pattern | Replay obligations |
|---|---|---|
| **WorkflowAgent / TaskAgent** | State-machine execution against a task graph declared as a Control Plane artifact; deterministic step ordering; structured idempotency; heavy Orchestration Layer interaction (§4 of this document (CLAUDE.md §8.1)) | Step sequence lands in replay dimension 5; calling chain in dimension 4 |
| **DocumentIntelligenceAgent** | Ingest/extract/analyze/generate over the Pattern 5 unstructured pipeline; passage-level lineage (§7.10.3) baked into every output | Passage anchors in the L dimension of emitted products; document-derivation trace in dimension 5 |
| **AnalyticsInsightsAgent** | Computation over Context Products: temporal analysis against the T dimension (INV-CH8-14, owned by §2B), threshold detection, cross-entity comparison, signal aggregation | Product versions and as-of times consumed land in dimension 1 references |
| **MonitoringSurveillanceAgent** | Long-running, trigger-driven: event subscription against L1 streams, threshold activation, λ_c-driven continuous re-evaluation | Trigger condition, threshold version, and activation timestamp per invocation |
| **ContentGenerationAgent** | Template binding + citation-aware generation — every claim passage-anchored (§7.10.3); draft-and-review HITL integration via ReviewQueue (§5 of this document (CLAUDE.md §8.2)) | Prompt-artifact versions in dimension 3/5; ReviewQueue actions extend dimension 2 |
| **ContextAssemblyAgent** | Assembler producing typed Context Products for other agents — the §6.6 recursive-enrichment case and the §7.4.9 swarm-realized operator case (INV-CH7-32, §3.4 below); transport via in-process call, MCP egress, or A2A | The emitted product is itself a replayable artifact bound to the five-dimension envelope, distinct from any consumer's inference trace |

Per-archetype contract detail, in the standard field template:

**`WorkflowAgent` / `TaskAgent`**
- **Responsibility:** procedural, multi-step decisioning against a task graph declared through the Task Factory (never code); examples per CLAUDE.md §6.3: KYC, credit checks, onboarding, routing, fulfillment.
- **Invariants enforced:** deterministic step ordering; structured idempotency (re-invocation with identical inputs and Control Plane state is a no-op or an identical result); every node can yield to a first-class exception path (§4/§5).
- **Seams:** Workflow primitive agent-nodes (D-IMPL-17); suspended state persists at the Control Plane boundary (D-IMPL-18).

**`DocumentIntelligenceAgent`**
- **Responsibility:** document ingest, metadata extraction, analysis, generation over the Pattern 5 pipeline.
- **Invariants enforced:** passage-level lineage (§7.10.3) in every output; the §3.4 alternation discipline when composed with generation.
- **Seams:** unstructured pipeline stages (D-IMPL-08, §2A); Citations-capable LLM access per D-IMPL-09 (semantic stages only).

**`AnalyticsInsightsAgent`**
- **Responsibility:** computation over Context Products — temporal analysis, threshold detection, comparative analysis, signal aggregation.
- **Invariants enforced:** consumes only contract-validated products; thresholds are Control Plane parameters (D-IMPL-38 discipline), never code constants.
- **Seams:** T-dimension mechanics owned by the fabric (INV-CH8-14, §2B).

**`MonitoringSurveillanceAgent`**
- **Responsibility:** long-running, trigger-driven watch: event subscription against L1 streams, threshold-based activation, λ_c-driven continuous re-evaluation.
- **Invariants enforced:** activation conditions and thresholds are versioned Control Plane values; each activation is an independently replayable invocation.
- **Seams:** L1 stream subscription surface (§2A); escalation via ExceptionEscalation on D_c breach (§4/§5).

**`ContentGenerationAgent`**
- **Responsibility:** structured LLM output under template binding — credit memos, research notes, narrative reports.
- **Invariants enforced:** citation-aware generation — every claim passage-anchored (§7.10.3); templates are versioned prompt artifacts (axis 6), never inline.
- **Seams:** ReviewQueue draft-and-review integration (§5 of this document (CLAUDE.md §8.2)).

**`ContextAssemblyAgent`**
- **Responsibility:** assembler producing typed Context Products for other agents — the recursive-enrichment and swarm-operator case (§3.4).
- **Invariants enforced:** emitted products honor the full contract (schema + λ_c + passage-level L); Policy-before-Similarity inside every assembly step; emission reaches L3 only through L2 (single-writer, CLAUDE.md §10).
- **Seams:** transport via in-process call, MCP egress, or A2A (§6/§8).

The archetypes encode the search ⇄ inference loop discipline (INV-CH6-07, §6.6): every loop iteration is a contracted Context Product request; the agent never self-assembles context, never queries raw stores, never reconstructs entity identity — *"assembly stays in the architecture; reasoning stays with the agent."* The loop itself (inference → drives search; search → enriches context; enriched context → improves inference) executes inside the harness; the fabric-side pattern the archetypes contribute is that each turn's operator composition is resolved by the Runtime from the request, not specified by the agent (INV-CH6-07 invariant). Decision-time content acquisition inside the loop rides the MCP client surface at L4–L5 (CLAUDE.md §7.1, cross-ref §2B).

**Trust-gated action (INV-CH6-08, §6.6.3).** The loop's stopping criterion is the Context Trust Triangle — Context Confidence, Context Freshness, Context Lineage Integrity — with **conjunctive** semantics: weakness in any leg degrades aggregate trust regardless of the other two. The agent framework's design obligation: the `Agent` base surfaces the trust legs of every consumed product to the harness adapter as typed inputs, and encodes the low-trust behavior as a first-class outcome set — **escalate** (ExceptionEscalation, §4/§5), **re-request** (a different product), or **surface the weakness** — never silent action under aggregate-low trust. Per the D-IMPL-32 ruling's disposition (recorded in `docs/DECISIONS.md`), trust aggregation mechanics are a Control-Plane-configurable scoring surface: mechanism ships the interfaces, institutions supply thresholds — values, never SDK constants.

### 3.3 Archetype composition

*SDK-defined, cites CLAUDE.md §6.3. Whitepaper hook: archetypes are functional categories, not exclusive categories.*

- **Responsibility:** Multi-archetype agents (a monitoring agent that is also an assembler; a content generator whose output is a typed Context Product) are declared as an **ordered archetype list** in the definition artifact. The factory attaches the corresponding `ArchetypeComponent` bundles to the single `Agent` instance in declaration order.
- **Protocol/type signatures:** artifact field `archetypes: ordered list of archetype identifiers` (channel-1 axis 1); composition performed by the Agent Factory, never by the artifact author writing code.
- **Invariants enforced:** explicit conflict rules per **D-IMPL-19** (RESOLVED): identical obligations contributed twice are **deduplicated**; conflicting configuration defaults resolve by **declaration order with a factory warning**; hard contradictions are a **factory construction error**. The composed archetype list is channel-1 identity and lands in replay dimension 4 (INV-CH7-84).
- **Seams:** composition over mixins — no class hierarchy exists to entangle (D-IMPL-11); users combine archetypes by declaration only.
- **D-IMPL rulings embodied:** **D-IMPL-19**; **D-IMPL-11** (composition target is the single `Agent` class).

### 3.4 Swarm-realized operators and the assembly/consumption boundary — INV-CH7-32

*Whitepaper commitment (§7.4.9), realized here through the `ContextAssemblyAgent` archetype.*

- **Responsibility:** A Context Operator may be realized as an agent swarm whose sole job is slot-filling a typed Context Product (detection, classification, reconciliation, policy-filtered emission). The archetype framework is where the SDK houses this realization: an assembler swarm is a composition of `ContextAssemblyAgent`-archetype agents orchestrated per §4/§5.
- **Invariants enforced (verbatim from INV-CH7-32):** output-contract determinism — the product emerges with its schema, its λ_c, and its passage-level L intact regardless of internal LLM-driven extraction; **Policy is composed before Similarity at every step the swarm takes**; the assembly/consumption boundary is typed and enforceable — the downstream reasoning agent consumes the completed product plus seed context and does not re-assemble context de novo. Auditors see two distinct replayable artifacts — the assembler swarm's Context Product and the reasoning agent's inference trace — interrogable independently, both bound to the §7.10 five-dimension envelope.
- **Seams:** operator-realization mechanism is §7.4's (L4, §2B); per-product mode selection (when to choose swarm assembly) is §7.6 Mode 3 territory (§2B). Swarm-level **intent decomposition** is an orchestration-layer concern and a named post-v0 extension candidate per the D-IMPL-49 ruling — intent compiles down to concrete product requests carrying the deterministic `(perspective, context_product_class, selection_params)` selection signature; coordination stays above Π (documented in §4/§5; noted here because the swarm is archetype-realized).
- **D-IMPL rulings embodied:** **D-IMPL-49** (selection-signature determinism at the swarm's product requests); alternation invariant per §3.5 below.

**Alternating derivation inside archetype pipelines (INV-CH8-12, §8.4).** The Document-Heavy Compositional pattern — Algorithmic Perception → Semantic Comprehension → Algorithmic Verification → Semantic Synthesis — is the canonical shape the `DocumentIntelligenceAgent` and `ContentGenerationAgent` archetypes bind to when composed over the fabric. The design carries its invariants into the archetype contracts: the Algorithmic ⇄ Semantic Alternation is structural (LLMs never see raw signal; algorithmic stages never perform semantic interpretation — INV-CH6-04, owned by §2B, whose CI `@algorithmic` lint design lives in the Invariant Preservation chapter); LLM inference runs exactly twice, bounded by algorithmic stages; Policy-before-Similarity holds inside Verification; below-threshold candidate relationships are carried forward as distinct, never silently collapsed (threshold schema per the D-IMPL-38 parameter discipline — Control Plane values, not code); every synthesis claim is passage-anchored. The persist-into-G feedback loop is an L2 write path — the archetype never acquires a write handle (single-writer, CLAUDE.md §10). Auditability of agentic work at scale (INV-CH8-20, owned by §2B) is the payoff: archetype pipelines produce governance artifacts by mechanism, not by a separate track.

### 3.5 The Agent & Task Factory and the definition-artifact schema

*SDK-defined, cites CLAUDE.md §6.4. Whitepaper hook: §7.8.3 Control Plane configuration surface — agent/task/prompt/skill artifacts are additional Control Plane classes (INV-CH7-72, owned by §2B).*

- **Responsibility:** The factory is the **only** construction path for agents and tasks. It interprets declarative definition artifacts, validates them, composes archetype components, resolves instruction bindings, and emits `Agent` instances. There is no supported path that bypasses it — including in tests, which construct agents from fixture artifacts, never inline (CLAUDE.md §6.4).
- **Protocol/type signatures:** `AgentFactory.construct(definition_ref) -> Agent`; `TaskFactory.construct(definition_ref) -> Task`. Definition artifacts per **D-IMPL-28** (RESOLVED): **YAML validated by Pydantic v2 (`extra=forbid`) schemas with exported JSON Schema** for non-Python tooling; **Jinja2-templated prompt artifacts referenced by versioned URI — never inline text** — with template parameters declared in the referencing definition and validated at construction time.
- **Invariants enforced:** every artifact carries `schema_version` and `artifact_version` with **independent per-artifact-class semver lanes** (D-IMPL-28); artifact addressing is the D-IMPL-26 hybrid (content-addressed canonical identity + versioned URI, `@latest` forbidden in replay/lineage) — storage seam owned by §6/§8 (ArtifactStore). Construction is deterministic: identical definition version + identical referenced-artifact versions produce an identical `Agent` configuration, which is what makes agent identity replayable.
- **Seams:** artifacts persist via the ArtifactStore Protocol (CLAUDE.md §7.4) and/or version control; the factory reads through Control Plane resolution, never raw storage.
- **D-IMPL rulings embodied:** **D-IMPL-28**; D-IMPL-26 (addressing, by reference).

**The No-Hardcoding Rule as structural design.** The rule (CLAUDE.md §6.4) is realized structurally, not aspirationally: (a) no prompt or system-instruction string literal in code — instruction text exists only in versioned prompt artifacts reached via axis-6 references; (b) no agent or task definition in code — the factory is the sole interpreter; (c) no task graph, routing table, threshold, approval rule, or skill grant as code constants — all are Control Plane artifacts interpreted by mechanism; (d) code contains interpreters and factories, never the things interpreted. The CI lint design (prompt-shaped-literal rejection; factory-bypass rejection) is specified in the Invariant Preservation chapter of DESIGN.md — this chapter cross-references it rather than duplicating it. The rule is what makes the archetype/agent boundary the same boundary as mechanism/values: two deployments on identical SDK versions run entirely different agent populations with zero diverging code (CLAUDE.md §6.1).

### 3.6 Channel 1 — Specialization (identity and constraint)

*SDK-defined, cites CLAUDE.md §6.2. Whitepaper hook: §7.10.1 dimension 4 (INV-CH7-84).*

Fixed in the definition artifact and versioned with it; changing any axis produces a **new agent version**. The six axes, each a typed artifact field validated per D-IMPL-28:

1. **Archetype binding** — ordered archetype list and composition per D-IMPL-11/D-IMPL-19 (§3.3 above).
2. **Context contract** — which Context Product schemas the agent reads, and/or which projection it emits to (contract bases per §2B).
3. **Perspective** — the Π role-conditioning bound into projection-plan selection via the D-IMPL-49 signature `(perspective, context_product_class, selection_params)`.
4. **Policy regime** — the Control Plane bundle in force: entitlements, jurisdictional bindings, regulatory regime, HITL policy, and the **envelope of skills the agent is permitted to bind** (feeds §7 tier-1 governance).
5. **Half-life and debt profile** — staleness tolerance and the `D_c` threshold triggering Forced LLM or Fail-Closed (mechanics owned by §2B; escalation routing by §4/§5).
6. **Instruction bindings** — versioned-URI references to prompt/instruction artifacts, never inline text (D-IMPL-28).

**Replay capture (INV-CH7-84).** Dimension 4 — Perspective Conditioning — answers *"for whom, with what authority?"*: agent identity, role, tool inventory, delegation chain complete from originating principal to acting agent. The SDK-defined extensions land here by construction: **agent version and skill-set in force** (CLAUDE.md §6.2) and **workflow calling chain** (CLAUDE.md §8.1, §4/§5) extend dimension 4. Because every distinguishing property is artifact-serialized (D-IMPL-11), dimension 4 capture is a mechanical serialization of `(agent_id, artifact_version, composed archetype list, six-axis record, skill-set snapshot, delegation chain)` — no reconstruction, no drift between what ran and what is recorded.

### 3.7 Channel 2 — Skilling (capability under governance)

*SDK-defined, cites CLAUDE.md §6.2. Whitepaper hook: §7.8.2 audit plane; §7.10.1 dimension 4.*

- **Responsibility:** Skills are typed, governed capabilities in a **dynamic Control Plane skill catalog** (D-IMPL-12): registered as typed, versioned Control Plane artifacts (D-IMPL-28 format) at boot or at runtime through an audited Control Plane action. **Four skill types:** local callable | MCP resource/tool | A2A endpoint (exposing remote Context Products) | tool — MCP-Resources-as-skills is one type, not the unified mechanism (D-IMPL-12, RESOLVED).
- **Protocol/type signatures:** catalog entries carry a typed **requirements declaration** (policy scope, context-contract access, egress) validated per D-IMPL-28; grants and revocations are **separate versioned artifacts referencing catalog entries by version** (D-IMPL-12).
- **Invariants enforced — two-tier governance (D-IMPL-29, RESOLVED):** **Tier 1** — the automatic policy-compatibility check, **always on and non-waivable**: the Control Plane refuses any bind whose declared requirements exceed the agent's policy regime (axis 4) or context contract (axis 2). **Tier 2** — policy regimes may declare that grants (all, or matching declared criteria) additionally require an **ApprovalGate** before taking effect (gate primitive per §4/§5); whether tier 2 is engaged is Control Plane configuration — values, not SDK policy. Grant, approval, and effective-time all land in the audit record; the skill-set in force at decision time is part of the replay record — **a decision replays against the skills the agent actually had, not the skills it has now** (CLAUDE.md §6.2; dimension 4 per §3.6 above).
- **Seams:** the harness adapter's skill-exposure seam surfaces exactly the currently-bound skill-set as the harness's tools — no more, no less (CLAUDE.md §7.3 seam 2; adapter design in §6/§8, across all three D-IMPL-24 harnesses: Google ADK, Claude Agent SDK, LangGraph).
- **D-IMPL rulings embodied:** **D-IMPL-12**; **D-IMPL-29**; D-IMPL-24/25 (by reference at the adapter seam).

**Why two channels stay separate (design commitment).** Specialization changes *who the agent is*; skilling changes *what it can currently do*. The design keeps them structurally distinct: axis changes re-version the agent artifact; skill grants/revocations version the grant artifacts and never re-declare the agent. Collapsing them would force full redefinition per capability change or invite ungoverned capability sprawl — the separation buys stable identity for audit, capability agility under explicit governance, and the clean adapter seam (CLAUDE.md §6.2).

### 3.8 Adoption framing — INV-CH8-22

The whitepaper's archetype mapping framework (§8.11) commits a **platform-versus-domain split**: platform teams own fabric primitives; domain teams own domain-specific operators and Context Products. For the SDK this maps directly onto the mechanism-vs-values boundary the agent framework enforces: the six archetypes, the `Agent` base, the factory, and the skill-catalog mechanism are platform/SDK assets in `/src`; agent definitions, task definitions, prompt artifacts, skill catalogs, and grants are domain/user artifacts. The four whitepaper decisioning archetypes (Document-Heavy Compositional, Temporal Reconciliation, Forensic-Defensibility, Conversational Synthesis) are *use-case diagnostic categories* users realize by declaring agents from the six SDK archetypes — the SDK ships no domain archetype and no prioritization opinion (the framework is illustrative, not prescriptive — INV-CH8-22 invariant). The Conversational Reporting Layer adjacency (INV-CH8-21, owned by §6/§8) remains explicitly out of v0 scope; nothing in the archetype set pre-builds it.

---

## 4. Pillar: Orchestration Layer

Component diagram: `docs/diagrams/pillar-orchestration.mmd`.

This pillar is an **SDK-defined extension** — it cites CLAUDE.md §8.1 as its canonical surface, not the whitepaper. The whitepaper hooks it attaches to are cited per inventory entry (INV-CHx-NN). Contract altitude per locked D-07: responsibilities, Protocol/type signatures, invariants, seams — no implementation code.

Owned entries (per the traceability matrix at the end of this document): INV-CH7-55, INV-CH7-56, INV-CH7-68, INV-CH7-88. See-also entries touched here with primary ownership elsewhere: INV-CH7-32, INV-CH8-08.

---

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
- **Swarm-realized operators (INV-CH7-32, see-also from §3):** an operator realized as an agent swarm honors the same typed output contract (schema + λ_c + passage-level L) as any code-and-pipeline realization; Policy-before-Similarity holds inside swarm steps; the workflow that realizes the swarm is an ordinary `WorkflowDefinition` whose trace satisfies the Mode 3 replay footprint.
- **Cross-org ingress (INV-CH8-08, see-also from §6/§8):** A2A is the cross-organizational orchestration ingress Mode 3 consumes. The Orchestration Layer treats a remote contribution as an AgentNode result arriving over the wire; admission (consumer-side Control Plane verification before L3 entry, D-IMPL-16) belongs to the A2A seam, not to the workflow.

### Swarm-level intent decomposition — named post-v0 extension (D-IMPL-49 DESIGN.md obligation)

Per the D-IMPL-49 ruling, this is recorded explicitly: **swarm-level intent decomposition is an orchestration-layer concern and a NAMED post-v0 extension candidate.** In v0, intent never reaches Π as free inference — where plan selection varies by intent, intent is a declared enum-valued selection parameter inside the canonical deterministic projection-selection signature `(perspective, context_product_class, selection_params)`. The post-v0 extension shape: an intent-decomposition stage in the Orchestration Layer compiles a high-level intent down to concrete Context Product requests each carrying that signature; coordination stays above Π; replay stays deterministic because every compiled request is fully determined by its signature plus plan version. Nothing in v0's Workflow primitive precludes this — it composes as a coordinator pattern over existing nodes.

---

## 5. Pillar: Human in the Loop and Control

Component diagram: `docs/diagrams/pillar-hitl.mmd`. Gate suspend/resume sequence: `docs/diagrams/seq-hitl-suspend-resume.mmd`.

This pillar is an **SDK-defined extension** — it cites CLAUDE.md §8.2 as its canonical surface, not the whitepaper. Whitepaper hooks: escalation/fail-closed routing (INV-CH7-65, INV-CH7-67, INV-CH8-16, INV-CH8-18), the audit plane (INV-CH7-71), the closed-loop interpretation gate (INV-CH7-75, D-IMPL-43), and replay dimension 2 extension (INV-CH7-82).

Owned entries (per the traceability matrix at the end of this document): INV-CH7-65, INV-CH7-67, INV-CH7-82, INV-CH8-16, INV-CH8-18, INV-CH8-19 (deferred per D-IMPL-48), INV-CH8-23. See-also entries touched here with primary ownership elsewhere: INV-CH6-08, INV-CH7-71, INV-CH7-75.

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

The Orchestration (§4) and HITL (§5) pillars together produce the governance legibility §8.12 commits to: workflow definitions, HITL policies, approval rules, and escalation thresholds are versioned Control Plane artifacts moving through the same SDLC gates as models and applications; the Control Plane / Data Plane boundary (INV-CH7-70/71, owned by §2B) is what lets a HITL-policy change deploy as a control-plane action without disrupting data-plane assembly. The three governance primitives (λ_c, D_c, Supervision Quality where a deployment builds it) remain measurable because the routing they drive (INV-CH8-16) and the human actions they trigger land in replay by construction.

---

**SDK-extension labeling:** the Experience Layer, bidirectional MCP, A2A-as-first-class, the HarnessAdapterProtocol, and the ArtifactStore are SDK-defined extensions per CLAUDE.md §1, §7.1–§7.4, §8.3 — not whitepaper-derived, and labeled as such throughout.

---

## 6. Pillar: Experience Layer (SDK-defined, CLAUDE.md §8.3)

The Experience Layer is the front door: three v0 surfaces, nothing more. It adds delivery, authentication hooks, and serialization over the fabric — never new semantics, never a second write path. Diagram: `docs/diagrams/pillar-experience.mmd`.

### 6.1 MCP server (egress front door)

- **Responsibility:** Expose L6 Context Products as MCP Resources and permitted agent invocations as MCP Tools. This is the whitepaper's Pattern 3 unchanged (INV-CH8-07, §8.3): the fabric is *served via* MCP, not *defined by* MCP — the Context Product carries its semantic contract (§6.3) at the application layer, transport-independent.
- **Protocol/type signatures:** One `ccf-runtime` MCP egress server, two resource families — Context Products (L6 egress) and Experience access (agent invocation Tools) — per the D-IMPL-13 ruling. L6 egress and Experience access are one server, two resource families; the ArtifactStore MCP contract is a *separate* server, never merged with egress (D-IMPL-13).
- **Invariants enforced:** MCP never manages state, enforces temporal logic, applies policy, or constructs context (INV-CH6-06, §6.5.1): MCP is the access layer, CCF is the construction layer. Canonical request path: Agent → MCP Interface → Context Assembly Runtime → Context Graph → Context Product → Agent. One construction layer, one invariant set, one audit substrate regardless of the consuming framework.
- **Seams:** External agent runtimes (Claude products, third-party frameworks) reach Context Products through the same egress used by internal consumers (CLAUDE.md §7.1); the D-IMPL-20 HITL reference transport also rides this server — HITL queues as Resources, actions as Tools.
- **D-IMPL rulings embodied:** D-IMPL-13 (role allocation), D-IMPL-23 (the HTTP surface mirrors, never bypasses, the same factories/Control Plane actions).

### 6.2 `ccf` CLI (per D-IMPL-22 ruling)

- **Responsibility:** Interactive front door: noun-verb subcommand structure `ccf <noun> <verb>` over exactly the §8.3 enumerated surfaces, with the ruled noun set: `agent`, `skill`, `workflow`, `hitl`, `replay`, `artifact`, `product`, `config`.
- **Protocol/type signatures:** Thin client over the HTTP API (D-IMPL-23), plus a `--local` direct-library mode for the SQLite/file-backed dev quickstart (examples 00–02, CLAUDE.md §9).
- **Invariants enforced:** Every mutating verb routes through the same factories and Control Plane actions as any other client — `ccf agent declare` takes an artifact file, never inline definition flags (No-Hardcoding Rule, CLAUDE.md §6.4). The CLI adds zero privileged paths: one authorization surface, one audit surface (D-IMPL-22).
- **Seams:** `ccf replay` verbs consume the three-rendering surface of INV-CH7-91 (§7.10.7): auditors, risk/compliance, and management renderings are three Π projections of the *same* replay record, never three records — the CLI selects a rendering by requesting a Π role-conditioning, reusing the §7.5 Projection primitive recursively at the replay layer. `ccf artifact` verbs resolve both D-IMPL-26 address forms (content hash and versioned URI).
- **D-IMPL rulings embodied:** D-IMPL-22, D-IMPL-23, D-IMPL-26.

### 6.3 HTTP API skeleton (per D-IMPL-23 ruling)

- **Responsibility:** Minimal v0 REST skeleton mirroring the CLI noun set: product retrieval; agent declare/list/show/versions; skill grants/catalog; workflow invocations/status/resume; HITL queues/actions; replay decisions/resolve; artifact get/put; health + OpenAPI.
- **Protocol/type signatures:** OpenAPI generated from the Pydantic `extra=forbid` contracts the SDK already defines — the API adds serialization, auth hooks, and routing; no new semantics (D-IMPL-23).
- **Invariants enforced:** **L1 ingestion is deliberately NOT on the v0 HTTP surface.** Ingress is CDC/MCP-adapter territory (D-IMPL-13, D-IMPL-33); a generic write endpoint would invite a second writer path, violating the single-writer invariant (CLAUDE.md §10).
- **Seams:** The primary surface for service integration and user-built UX layers.
- **D-IMPL rulings embodied:** D-IMPL-23, D-IMPL-22 (CLI-over-HTTP layering).

### 6.4 Non-goals (v0)

Per CLAUDE.md §8.3/§13: no mobile SDK, no chat adapter, no web UI, no human-task inbox — users build these on the HTTP API against the shipped OpenAPI spec. The **Conversational Reporting Layer is out of v0 SDK scope** (INV-CH8-21, §8.10; CLAUDE.md §13 explicit out-of-scope list): it is inventoried, not designed — its underlying primitives (Π, D_c gating, replay) are in scope individually, and a future conversational surface is a user-built reference integration over the same three front doors. This boundary is the design condition INV-CH8-24 (§8.13) restates: **coexistence, not replacement** — the Experience Layer layers onto whatever estate exists; heterogeneity is the condition the architecture was designed for, and source moves re-bind at the ingestion layer, never as front-door rework.

---

## 7. Cross-Cutting: Control Plane / Data Plane

*The two orthogonal planes cut across all six fabric layers and every SDK extension (CLAUDE.md §10). Rendered inside `docs/diagrams/pillar-data-context.mmd` as the Control Plane subgraph governing the Data Plane fabric.*
- **Responsibility:** Structural separation: the Control Plane defines what the fabric may do (policies, operator parameters, projection rules and entitlements, per-class D_c thresholds, per-type λ_c, materialization policy); the Data Plane executes against those definitions under controlled handoff (INV-CH7-70). **The Control Plane is also the audit plane**: every operator invocation, projection computation, and product assembly is observable for replay as a first-class property; every configuration change is versioned, timestamped, and retained against the decisions made under it; invalidation flows as published events, never direct side-effects (INV-CH7-71 — this audit plane is also what backs HITL audit-by-construction, designed in §5).
- **Configuration surface:** the six whitepaper classes — policy definitions, operator behavior rules, projection logic, D_c thresholds, λ_c tables, materialization policy (INV-CH7-72) — **plus the SDK-defined artifact classes**: agent definitions, task definitions, prompt artifacts, skill catalog entries and grants, workflow definitions, HITL policies, A2A trust policy (CLAUDE.md §7.4/§10; formats per the D-IMPL-28 ruling, marked as SDK extensions). In the v0 design the Control Plane is an in-process versioned registry with a remote extension point (CLAUDE.md §13); all parameter classes follow the D-IMPL-38 declared-schema, versioned, no-silent-default discipline; closed-loop updates enter through the D-IMPL-43 gated interpretation path.
- **Invariants enforced (plane-boundary register, INV-CH7-73):** (a) single-writer for graph state — realized by the D-IMPL-41 four-layer enforcement stack (reader/writer Protocol split per D-IMPL-34, DI at boot, mypy + import lint CI gate, boot-token runtime backstop), with the honest residual claim ("no unforced path exists and every forced path fails CI or fails at boot") recorded for the Invariant Preservation chapter — full write-path design owned by §2A; (b) projection stateless; (c) lineage strict equality at the stage-3a gate; (d) TTL bounds at stage-3b with MAX_TTL per D-IMPL-39; (e) tenant-scoped kw-only `tenant_id` on every execute call per the D-IMPL-05 ruling. Data Plane determinism — bit-for-bit identity under fixed (graph state, config, temporal boundary), randomness isolated at reproducible boundaries — is the foundation replay stands on (INV-CH7-74). Auditability-at-scale for agentic work rests on the same plane properties (INV-CH8-20).
- **D-IMPL rulings embodied:** D-IMPL-05, D-IMPL-28, D-IMPL-34, D-IMPL-38, D-IMPL-41, D-IMPL-43.

---

## 8. Cross-Cutting: Seams — Cross-Process Surfaces

The four seams below are where trust postures change. Each is a distinct module with a distinct trust posture; none creates a second writer to L3.

### 8.1 MCP role allocation (per D-IMPL-13 ruling)

MCP is allocated to exactly the five CLAUDE.md §7.1 edges — an SDK-defined extension of the whitepaper's export-only Pattern 3 (INV-CH8-07):

| Role | Direction | Layer | Module | Trust posture |
|------|-----------|-------|--------|---------------|
| Signal ingress | client | L1 | `ccf` MCP client library via `MCPSourceAdapter` → D-IMPL-33 `SignalEnvelope` | Outbound to source systems; results are untrusted signal, normalized at L1, interpreted at L2 |
| Content acquisition | client | L4–L5 | same `ccf` MCP client library | Decision-time acquisition (§6.6 search-inference recursion); results reach L3 only via L2 |
| Product egress | server | L6 | `ccf-runtime` MCP egress server (resource family 1) | Serves policy-bound, role-projected products; consumers untrusted, entitlement enforced by Π/Policy |
| Experience access | server | above L6 | same egress server (resource family 2: agent Tools, HITL queues per D-IMPL-20) | Authenticated front door; zero privileged paths |
| Artifact persistence | server | Control Plane substrate | separate ArtifactStore MCP server contract (§7.4) | Inside tenant trust boundary, authenticated; never merged with egress |

- **Invariants enforced:** SDK-as-MCP-client and SDK-as-MCP-server live in different modules (CLAUDE.md §7.1); single-writer unaffected — acquisition results reach L3 only via L2 (D-IMPL-13). MCP provides discovery, request, and standardized invocation and nothing more (INV-CH6-06).
- **Packaging:** follows D-IMPL-04 (client library in `ccf`, servers in `ccf-runtime`).

### 8.2 A2A federation (per D-IMPL-14/15/16 rulings)

SDK-defined elevation of Pattern 4 (INV-CH8-08, §8.3) to a v0 commitment per CLAUDE.md §7.2. Diagram: `docs/diagrams/seq-a2a-admission.mmd`.

- **Responsibility:** Cross-process, cross-organization Context Product exchange. The Context Product Contract is the stable layer; the wire is replaceable.
- **Protocol/type signatures:** `WireProtocol` abstraction with the Linux Foundation A2A protocol (JSON-RPC over HTTPS, Agent Card discovery, task/artifact model) as the v0 default implementation, carrying the typed Context Product as the artifact payload; mTLS via deployment configuration; a plain typed-HTTP fallback transport as the second reference implementation (D-IMPL-14).
- **Identity and signing (D-IMPL-15):** `IdentityProvider` Protocol, two-layer model — workload/transport identity via mTLS (X.509) as deployment configuration; product-level signing via detached JWS over the canonical serialized Context Product (producer agent identity + version + key id), verified at the consumer's Control Plane during admission. Reference implementations: static-keypair JWS (dev) and certificate-backed keys (production posture). SPIFFE/SPIRE is a conforming implementation, not required.
- **Admission verification (D-IMPL-16):** Verify **every** inbound A2A Context Product — full Control Plane verification (signature, Policy bindings, contract validation, lineage integrity) on every admission, no fast path in v0. Peer trust tiers configure only *what* is admissible (producers, product classes, policy regimes a peer may assert), never verification skips. Post-v0 relief via verification caching memoized on immutable artifact identity, preserving verify-everything semantics.
- **Invariants enforced (structural, INV-CH8-08 + CLAUDE.md §10):** An inbound A2A Context Product is **not admissible to L3 until the consuming Control Plane validates its Policy bindings; admission then flows only through L2** — the single-writer invariant holds across the federation boundary. **Lineage continuity via set-union:** inbound L *extends*, never replaces, the consumer's L — the producer's operator plan, graph snapshot reference, and policy version are all preserved across the boundary, with passage-level L preserved (Mode 3 assembly, §7.6). Rejection is a first-class outcome: a failed verification produces an audited rejection record, never a partial admission.
- **D-IMPL rulings embodied:** D-IMPL-14, D-IMPL-15, D-IMPL-16 (and D-IMPL-13 for the transport-role boundary with MCP).

### 8.3 HarnessAdapterProtocol (per D-IMPL-24/25 rulings)

The load-bearing neutrality seam (CLAUDE.md §7.3): CCF layers onto any harness as the trust-and-control plane; it never absorbs the agent loop and does not ship one. Diagram: `docs/diagrams/seam-harness-adapter.mmd`.

- **Responsibility:** Bind an agent definition (a Control Plane artifact, §6.1) to a concrete harness at runtime across exactly four seams:
  1. **Context injection** — typed Context Products into the harness's context/memory/prompt-assembly surface; the harness never touches L3 or raw signal.
  2. **Skill exposure** — exactly the agent's *currently-bound* skill-set (§6.2 channel 2) surfaced as the harness's tools; ungranted skills do not exist from the harness's point of view (threat T-02-27 mitigation: no over-exposure by construction).
  3. **Effect capture** — harness outputs routed back through governed emission (typed Context Product) or L2 write-back; a harness never acquires a write handle to the graph — the single-writer invariant holds across the adapter boundary.
  4. **Replay hooks** — model version, prompt-artifact version, and execution trace captured into the five-dimension Decision Replay record; the D-IMPL-45 `TraceCorrelationHook` attaches here.
- **Seam scope (D-IMPL-25):** Three seams mandatory for every conforming adapter — context injection, replay hooks, and effect capture *as governed refusal*; skill exposure conditionally mandatory (required iff the bound agent has a non-empty skill-set). A read-only consumer adapter may declare `effects: unsupported`, in which case the absence of any write-back path is a *declared capability verified by the conformance suite* — never a merely-unimplemented seam.
- **Reference targets (D-IMPL-24, Dave's own ruling):** ALL THREE harnesses ship reference adapters in v0 — Google ADK + Claude Agent SDK (must-haves) + LangGraph. Accepted consequences recorded in the ruling: a third adapter, third CI leg, and third example-03 variant enter v0 scope. The LangGraph two-seam disambiguation (per D-IMPL-17): the LangGraph *harness adapter* binds only the §7.3 agent-loop seams; LangGraph *as an orchestrator* of CCF agents is a distinct, optional OrchestrationProtocol integration — one tool, two seams, never conflated.
- **Invariants enforced:** **Zero harness imports in core** — no module in `/src` imports any harness package; adapters live in `/runtime/adapters/<harness>/`; CI import lint enforces (same machinery as the `@algorithmic` lint). Shown structurally in the seam diagram: the CCF-core subgraph contains no harness node, and the only edges crossing the boundary are the four typed seams. Cross-reference: §9 Invariant Preservation, zero-harness-imports row.
- **D-IMPL rulings embodied:** D-IMPL-24, D-IMPL-25 (plus D-IMPL-45 at the replay-hooks seam).

### 8.4 ArtifactStore seam (per D-IMPL-26/27 rulings)

SDK-defined persistence surface (CLAUDE.md §7.4). Diagram: `docs/diagrams/seam-artifact-store.mmd`.

- **Responsibility:** Persist CCF artifacts through an `ArtifactStoreProtocol` with an MCP-backed reference implementation (the separate D-IMPL-13 artifact server contract) and a file-backed dev implementation, so users point at their own persistent store by implementing the Protocol or standing up a conforming MCP server.
- **Artifact classes in scope (per the D-IMPL-27 mutability split):** Immutable, versioned, replay-relevant artifacts route through the store — Decision Replay records with all extensions (HITL, workflow, skill-set, agent-version), materialized graph-substate and similarity-index snapshots (D-IMPL-06), Context Products at rest, Control Plane bundles (policy bundles, λ_c tables, workflow definitions, HITL policies, A2A trust policy), and all No-Hardcoding artifacts (agent/task definitions, prompt artifacts, skill catalog entries and grants). Hot mutable state stays on native Protocols: live Context Graph on GraphStore (D-IMPL-02), live similarity index (D-IMPL-03), operator-plan intermediate caches (D-IMPL-36), suspended workflow execution state (D-IMPL-18) — mutable until terminal, whose terminal trace then lands in the store. The mutability criterion is a single structural rule.
- **Addressing (D-IMPL-26):** Hybrid — content-addressed canonical identity (`sha256` of canonical serialization; tampering fails the artifact's own address) plus versioned-URI naming (`ccf-artifact://{tenant}/{artifact_class}/{name}@{artifact_version}`) resolved through an append-only Control Plane mapping (a version once bound to a hash is never rebound). `@latest` is permitted only at authoring/Control Plane surfaces — never in a replay record or lineage entry, which store the hash. The reference artifact MCP server exposes both address forms with a typed metadata resource per artifact. Replay resolves *exact* versions, never "latest."
- **Invariants enforced:** **Never a second writer** (threat T-02-26): the ArtifactStore is a persistence substrate reached *through* L2 and Control Plane mechanism; nothing enters the graph except through L2, including artifacts retrieved from the store — the seam diagram shows no store→L3 edge. Trust posture: inside the tenant boundary but authenticated; artifacts arriving from *outside* the boundary are A2A's problem (§8.2 above), never the store's. The D-IMPL-50 fidelity-lifecycle engine (compression tiers, severity exemption, retention-reason) executes *above* the Protocol, so any conforming store gets the lifecycle for free (see-also INV-CH7-89, owned by §2B).
- **D-IMPL rulings embodied:** D-IMPL-26, D-IMPL-27 (with D-IMPL-06, D-IMPL-18, D-IMPL-50 interactions noted).

---

### 8.5 CLI noun-verb surface (contract altitude, per D-IMPL-22)

| Noun | Representative verbs | Backing surface |
|------|----------------------|-----------------|
| `agent` | declare (artifact file), list, show, versions | Agent Factory / Control Plane (§6.4) |
| `skill` | register, grant, revoke, catalog | D-IMPL-12 catalog + D-IMPL-29 governance |
| `workflow` | invoke, status, resume, list | Workflow primitive (D-IMPL-17), state per D-IMPL-18 |
| `hitl` | queues, approve, reject, override, annotate | D-IMPL-20 typed queue transport |
| `replay` | show, resolve, render (audience Π per INV-CH7-91) | Replay engine + ArtifactStore resolution |
| `artifact` | get, put, inspect, resolve (hash ↔ URI per D-IMPL-26) | ArtifactStoreProtocol |
| `product` | get, list, classes | L6 delivery contract |
| `config` | show, set, bundle operations | Control Plane registry |

Every mutating verb is a Control Plane action; every action is audited; no verb accepts inline definitions (No-Hardcoding, CLAUDE.md §6.4). The verb inventory is illustrative at contract altitude — the exact flag surface is Phase I detail; the noun set and the artifact-file-only rule are the design commitments.

### 8.6 Replay contributions of the Experience pillar

Per CLAUDE.md §4, every pillar contributes to Decision Replay. The Experience Layer's contribution is the **calling surface**: which front door (MCP egress, CLI, HTTP), which authenticated principal, and which rendering (for replay-record consumption per INV-CH7-91) are captured on the relevant replay dimensions. HITL actions arriving through the MCP HITL surface (D-IMPL-20) carry the D-IMPL-21 `HumanPrincipalBinding` regardless of front door — notification and authority are separated so audit-by-construction cannot be bypassed from any Experience surface.

### 8.7 Seam-to-seam boundary notes

Three boundaries between the seams themselves are worth stating so Phase I does not blur them:

- **MCP egress vs A2A.** Both can carry a Context Product across a process boundary. The design rule: MCP egress serves consumers *inside* the trust boundary (or authenticated externals consuming read-only, entitlement-enforced by Π/Policy); A2A serves *cross-organizational* exchange where the product must be admitted into another fabric's graph — which is why admission verification (D-IMPL-16) exists on the A2A path and not on the egress path. A product read over MCP egress never enters another fabric's L3 through that read alone.
- **ArtifactStore MCP server vs egress MCP server.** Distinct server contracts, never merged (D-IMPL-13): egress serves live products and Experience access to consumers; the artifact server serves versioned artifacts to the fabric's own mechanism (and to replay tooling). Merging them would put replay substrate and consumer delivery on one trust surface.
- **Harness adapter vs OrchestrationProtocol.** Ruled under D-IMPL-17/D-IMPL-24: a harness adapter binds the agent-loop seams for one agent execution; an OrchestrationProtocol integration coordinates *many* agent executions. LangGraph appears on both lists as two separate integrations — the DESIGN.md synthesis carries the explicit boundary statement the D-IMPL-17 ruling requires.

### 8.8 Threat dispositions carried by this design (from the plan threat model)

- **T-02-25 (Spoofing, A2A producer identity) — mitigated by design:** detached-JWS product signing + consumer-side Control Plane verification per D-IMPL-15/D-IMPL-16; shown as the verification step and reject branch in `seq-a2a-admission.mmd`.
- **T-02-26 (Tampering, second writer via store or harness) — mitigated by design:** no store→L3 edge (§8.4) and no harness write handle (§8.3 seam 3); both constraints are visually enforced in the two seam diagrams and structurally enforced by the D-IMPL-41 stack.
- **T-02-27 (Elevation of privilege, harness skill over-exposure) — mitigated by design:** skill exposure is *exactly* the currently-bound skill-set (§8.3 seam 2); the D-IMPL-29 tier-1 compatibility check bounds what can ever be bound.

### 8.9 Phase I hand-off


Phase I.3 (cross-process) implements against §8.1–§8.2 and §8.4: the MCP client library and both server contracts, the WireProtocol default + fallback transports, the IdentityProvider reference implementations, and the ArtifactStoreProtocol with both reference stores. Phase I.4 (harness + experience) implements against §6 and §8.3: the three reference adapters and their conformance suite (including the `effects: unsupported` declared-capability check), the CLI, and the HTTP skeleton with generated OpenAPI. Every implementation module cites the D-IMPL ruling and the whitepaper or CLAUDE.md section it realizes, per CLAUDE.md §11 docstring discipline.

---

## 9. Invariant Preservation (D-10 / D-11)

Per locked D-10, this chapter argues each of the seven named architectural invariants (CLAUDE.md §16; `docs/SPEC_INVENTORY.md` Named Architectural Invariants table — same invariants, same order) **structurally**: the design construct that makes violation impossible (or forces it through a CI/boot failure), the enforcement point, and the diagram or section that shows it. An assertion-only row would be a blocking defect; none appears below.

| Invariant | Structural argument (design construct) | Enforcement point | Diagram/section ref |
|-----------|----------------------------------------|-------------------|---------------------|
| Single-writer enforcement (only L2/Assembly writes L3) | `GraphReader`/`GraphWriter` Protocol split (D-IMPL-34): read-path constructors accept only `GraphReader`, so write-handle absence is a constructor-signature property; the composition root constructs exactly one `GraphWriter` at boot and injects it into L2 only; boot-token backstop (D-IMPL-41 four-layer stack) | DI composition root at boot; strict mypy + writer-module import lint in CI; boot-time token mint | §2A.5.3; `docs/diagrams/seq-single-writer-write-path.mmd` |
| Composition-preservation `(A∘B)(G) = A(B(G))` | Operators are pure, read-only, sync functions over `GraphReader` views (INV-CH7-22) — no mutation path exists to break commutation with state; every intermediate carries its own provenance sub-chain and is cached on a deterministic key (D-IMPL-36), so a cache hit is by construction the value replay would produce | CI property-test harness over every shipped operator pair (CINV-adjacent test design below) | §2B.1; `docs/diagrams/pillar-data-context.mmd` |
| Three validation gates (empty-operator guard, lineage strict equality, TTL bounds) | The canonical gate sequence — empty-operator guard → lineage strict equality → TTL bounds — is the **only** construction path of a servable `ContextProductContract` — it runs before any cache write or delivery (INV-CH7-52), and the contract base is `extra=forbid`, so an unvalidated or forged product is a type/validation failure, not a served product | L6 delivery boundary, pre-cache and pre-delivery; MAX_TTL registration validation at the Control Plane (D-IMPL-39) | §2B.3; `docs/diagrams/pillar-data-context.mmd` |
| Algorithmic ⇄ Semantic Alternation (LLMs never see raw signal) | L1's opaque payload typing makes interpretation structurally unavailable below L2 (§2A.2); LLM access exists only through `LLMClientProtocol` (D-IMPL-09), giving the lint a single crisp import target; algorithmic modules carry the `@algorithmic` tag and cannot import it | CI `@algorithmic` import lint (CINV-03); per-stage lint targets in the Pattern 5 pipeline (D-IMPL-08) | §2B.3 (Alternation component); §2A.2; §2A.4.4 |
| Audit-by-construction (every HITL action, workflow trace, and skill event replay-recorded) | The typed action record is the **completion token**: a suspended gate transitions only on a validated action record whose `extra=forbid` schema requires `HumanPrincipalBinding` (D-IMPL-21), and the replay append is a defined precondition of the state transition; all ingress/egress rides one `HITLTransportProtocol` queue — webhooks are notify-only (D-IMPL-20); skill grants/revocations are versioned Control Plane artifacts landing in replay dimension 4 | Workflow transition function (replay write precedes transition); Control Plane audit plane (INV-CH7-71); replay-by-construction CI checks (CINV-04) | §5 (Audit-by-construction); `docs/diagrams/seq-hitl-suspend-resume.mmd` |
| No-Hardcoding Rule (no inline prompts/definitions/values in code) | The Agent & Task Factory is the **only** construction path for agents and tasks — code contains interpreters and factories, never the things interpreted; prompts exist only as Jinja2 artifacts behind versioned URIs (D-IMPL-28); thresholds, tables, and routing values are typed Control Plane parameter artifacts with no SDK-side defaults (D-IMPL-38/39/40) | CI prompt-shaped-literal lint + factory-bypass lint (CINV-01); Control Plane registration validation | §3.5; §7; `docs/diagrams/pillar-agent-types.mmd` |
| Zero harness imports in core | No module in `/src` imports a harness; harness bindings live only in `/runtime/adapters/<harness>/` behind `HarnessAdapterProtocol`, and the only edges crossing the core/harness boundary are the four typed seams — shown structurally in the seam diagram, whose CCF-core subgraph contains no harness node | CI import lint on `/src` (CINV-02), same machinery as the `@algorithmic` lint | §8.3; `docs/diagrams/seam-harness-adapter.mmd` |

### Per-invariant structural arguments (expanded)

**1. Single-writer enforcement.** The full D-IMPL-41 four-layer stack (§2A.5.3): (1) interface split — separate `GraphReader`/`GraphWriter` Protocols, so a read-path component's constructor signature cannot even name a write handle; (2) DI-at-boot — one `GraphWriter` exists, held by the Assembly worker; (3) static gate — strict mypy rejects non-L2 `GraphWriter` type references and an import lint forbids the writer module outside L2 and the composition root; (4) runtime backstop — the writer handle requires a boot-time token only the composition root can mint. The invariant holds across every eroding boundary: A2A admissions enter L3 only through L2 after Control Plane verification (D-IMPL-16, INV-CH8-08); harness effect capture routes through governed emission or L2 write-back — no adapter ever holds a write handle (D-IMPL-25); the ArtifactStore is substrate behind mechanism, never a second writer (D-IMPL-27); the v0 HTTP API deliberately carries no ingestion endpoint (D-IMPL-23). **Honest residual claim (per the D-IMPL-41 ruling):** Python cannot make determined-insider evasion impossible; the claim strength is *no unforced path exists, and every forced path fails CI or fails at boot*.

**2. Composition-preservation.** The algebra `ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity` (INV-CH7-23) commutes with staged application because operators are side-effect-free reads of the same graph state: there is nothing an inner application can mutate that would change an outer application's input. Determinism is anchored by the function-determinism contract `(graph_state, control_plane_config, temporal_boundary, execution_plan) → bit-for-bit identical product` (INV-CH7-31) and by the Similarity determinism tuple with version-pinned index reads (INV-CH7-27, D-IMPL-03). The property is verified empirically, per CLAUDE.md §11, for every shipped operator pair.

**3. Three validation gates.** Gate 1 (empty-operator guard, INV-CH7-46), gate 2 (lineage strict equality — declared `operators_invoked` must equal the engine-resolved set, INV-CH7-47), gate 3 (TTL bounds `now < expires_at ≤ now + MAX_TTL`, re-verified at cache-write, INV-CH7-48) sit on the one path a product takes to an agent, the cache, or the replay record. Refusal is a structured rejection, never silent acceptance. Because MAX_TTL is required per-class Control Plane configuration (D-IMPL-39), a product class without a registered bound fails at registration — the gate cannot be configured away.

**4. Algorithmic ⇄ Semantic Alternation.** The boundary is crossed exactly once per pipeline transition (INV-CH7-54): raw signal is typed opaque at L1, so no semantic stage can reach it; algorithmic stages carry the `@algorithmic` tag and the lint rejects any `LLMClientProtocol` import there. Mode 2's four pinned primitives and Mode 3's orchestration-layer determinism keep trust-path purity across assembly modes (INV-CH7-55/56); the Alternating Derivation Pipeline binds the same discipline into archetype pipelines (INV-CH8-12, §3.4).

**5. Audit-by-construction.** The five-step structural argument of §5 applies to all four HITL primitives: single typed queue ingress/egress; action record as completion token with required `HumanPrincipalBinding`; replay append as transition precondition; notify-only webhooks; audit-plane grounding. Workflow traces extend replay dimensions 4/5 on every transition (§4), and skill grants/revocations are versioned Control Plane artifacts whose in-force set is serialized into dimension 4 (§3.7) — a decision replays against the skills the agent actually had.

**6. No-Hardcoding Rule.** Realized structurally in §3.5: (a) no prompt/system-instruction string literal in code; (b) no agent/task definition in code — the factory is the sole interpreter, including in tests (fixture artifacts); (c) no task graph, routing table, threshold, approval rule, or skill grant as code constants — all are Control Plane artifacts under the D-IMPL-38 declared-schema discipline; (d) code contains interpreters and factories, never the things interpreted. Applies to `/src`, `/runtime`, and `/examples` alike (CLAUDE.md §6.4, §11).

**7. Zero harness imports in core.** The adapter seam (§8.3) is the only surface where harness-specific code exists; `HarnessAdapterProtocol`'s four seams (context injection, skill exposure, effect capture, replay hooks) are the only crossings; all three D-IMPL-24 reference adapters (Google ADK, Claude Agent SDK, LangGraph) live in `/runtime/adapters/<harness>/`. The LangGraph two-seam boundary (D-IMPL-17) keeps orchestration integration from becoming a covert harness import path.

### CI enforcement design (D-11) — CINV-01..04

Phase F's test strategy (FEAS-03) and Phase I implement against the following designs rather than re-deriving them. IDs match `.planning/REQUIREMENTS.md`.

- **CINV-01 — No-Hardcoding lint.** Two passes over `/src`, `/runtime`, `/examples`: (a) **prompt-shaped-literal lint** — rejects string literals exhibiting instruction shape (heuristics: multi-sentence imperative prose, role-preamble patterns, template-brace density) outside the artifact directories; allow-list for error messages and log strings via explicit pragma; (b) **factory-bypass lint** — rejects any construction of `Agent`/`Task` types outside `AgentFactory`/`TaskFactory` modules (AST check on instantiation sites), including in tests, which must construct from fixture artifacts. Enforces the §3.5 rule and invariant row 6.
- **CINV-02 — Zero-harness-imports lint.** Import lint over `/src`: any import of a harness package (Google ADK, Claude Agent SDK, LangGraph, or any package on the configured harness deny-list) is a build failure. The same machinery hosts the **single-writer static gate**: the `GraphWriter` module may be imported only by `ccf.assembly` and the composition root; strict mypy rejects non-L2 `GraphWriter` type references. Enforces invariant rows 1 and 7.
- **CINV-03 — `@algorithmic` lint.** Modules tagged `@algorithmic` may not import `LLMClientProtocol` or any LLM vendor SDK (D-IMPL-09 gives the single crisp target). Applied per-stage in the Pattern 5 pipeline per the D-IMPL-08 ruling (assembly stages Mode-1 pure). Enforces invariant row 4.
- **CINV-04 — Replay-by-construction checks.** Test-harness assertions that every completion path emits its replay write before state transition: (a) **HITL** — each of the four primitives' action paths appends a bound action record (with `HumanPrincipalBinding`) to the replay record as a transition precondition; (b) **workflow** — every state transition appends to the execution trace, and suspend/terminal states write through to the ArtifactStore; (c) **skill-set capture** — grant/revoke actions version the grant artifacts and the in-force skill-set serializes into dimension 4 at decision time. Enforces invariant row 5.
- **Composition-preservation test harness** (feeds FEAS-03 alongside the CINV set): a property test parameterized over **every shipped operator pair** `(A, B)` asserting `(A∘B)(G) = A(B(G))` bit-for-bit on generated graph fixtures, under fixed `(graph_state, control_plane_config, temporal_boundary)`; plus the Similarity determinism tuple asserted against version-pinned index reads. Enforces invariant row 2.
- **Single-writer boot check** (runtime complement to CINV-02's static gate): a boot-sequence assertion that exactly one `GraphWriter` was constructed and its holder is the Assembly worker; construction of a second writer or a writer outside the composition root fails boot. Enforces invariant row 1's runtime backstop.

The three validation gates (invariant row 3) are enforced by mechanism at runtime rather than by lint; their CI coverage is contract-level: gate unit tests (rejection paths for empty-operator, lineage inequality, TTL violation) plus the Control Plane registration test that an unregistered MAX_TTL fails product-class registration (D-IMPL-39).

---

## Appendix A — Traceability Matrix (126/126, D-06)

Every `INV-CHx-NN` inventory entry (`docs/SPEC_INVENTORY.md`) mapped to the design section that realizes it, or explicitly deferred with the ruling that defers it. Key set is exactly the inventory's 126-entry set (mechanically checkable: unique-key diff against the inventory is empty).

| INV key | DESIGN.md section | Status |
|---------|-------------------|--------|
| INV-CH5-01 | §2A.0 | mapped |
| INV-CH5-02 | §2A.0 | mapped |
| INV-CH5-03 | §2A.0 | mapped |
| INV-CH5-04 | §2A.0 | mapped |
| INV-CH5-05 | §2A.0 | mapped |
| INV-CH5-06 | §2A.0 | mapped |
| INV-CH5-07 | §2A.0 | mapped |
| INV-CH5-08 | §2A.0 | mapped |
| INV-CH5-09 | §2A.0 | mapped |
| INV-CH5-10 | §2A.0 | mapped |
| INV-CH6-01 | §2B.3 | mapped |
| INV-CH6-02 | §2B.3 | mapped |
| INV-CH6-03 | §2B.3 | mapped |
| INV-CH6-04 | §2B.3 | mapped |
| INV-CH6-05 | §3.1 | mapped |
| INV-CH6-06 | §6.1 | mapped |
| INV-CH6-07 | §3.2 | mapped |
| INV-CH6-08 | §3.2 | mapped |
| INV-CH7-01 | §2A.1 | mapped |
| INV-CH7-02 | §2A.2.1 | mapped |
| INV-CH7-03 | §2A.3.1 | mapped |
| INV-CH7-04 | §2A.3.3 | mapped |
| INV-CH7-05 | §2B.1 (see-also §2A.1) | mapped |
| INV-CH7-06 | §2B.2 (see-also §2A.1) | mapped |
| INV-CH7-07 | §2B.3 (see-also §2A.1) | mapped |
| INV-CH7-08 | §2A.1 | mapped |
| INV-CH7-09 | §2A.1 | mapped |
| INV-CH7-10 | §2A.5.3 | mapped |
| INV-CH7-11 | §2B.1 (see-also §2A.1) | mapped |
| INV-CH7-12 | §2B.2 (see-also §2A.1) | mapped |
| INV-CH7-13 | §2B.3 (see-also §2A.1) | mapped |
| INV-CH7-14 | §2A.5.1 | mapped |
| INV-CH7-15 | §2A.5.1 | mapped |
| INV-CH7-16 | §2A.5.2 | mapped |
| INV-CH7-17 | §2A.5.2 | mapped |
| INV-CH7-18 | §2A.3.2 | mapped |
| INV-CH7-19 | §2A.4.4 | mapped |
| INV-CH7-20 | §2A.5.2 | mapped |
| INV-CH7-21 | §2A.3.2 | mapped |
| INV-CH7-22 | §2B.1 | mapped |
| INV-CH7-23 | §2B.1 | mapped |
| INV-CH7-24 | §2B.1 | mapped |
| INV-CH7-25 | §2B.1 | mapped |
| INV-CH7-26 | §2B.1 | mapped |
| INV-CH7-27 | §2B.1 | mapped |
| INV-CH7-28 | §2B.1 | mapped |
| INV-CH7-29 | §2B.1 | mapped |
| INV-CH7-30 | §2B.1 | mapped |
| INV-CH7-31 | §2B.1 | mapped |
| INV-CH7-32 | §3.4 | mapped |
| INV-CH7-33 | §2B.1 | mapped |
| INV-CH7-40 | §2B.2 | mapped |
| INV-CH7-41 | §2B.2 | mapped |
| INV-CH7-42 | §2B.2 | mapped |
| INV-CH7-43 | §2B.2 | mapped |
| INV-CH7-44 | §2B.2 | mapped |
| INV-CH7-45 | §2B.3 | mapped |
| INV-CH7-46 | §2B.3 | mapped |
| INV-CH7-47 | §2B.3 | mapped |
| INV-CH7-48 | §2B.3 | mapped |
| INV-CH7-49 | §2B.3 | mapped |
| INV-CH7-50 | §2B.3 | mapped |
| INV-CH7-51 | §2B.3 | mapped |
| INV-CH7-52 | §2B.3 | mapped |
| INV-CH7-53 | §2B.3 | mapped |
| INV-CH7-54 | §2B.3 | mapped |
| INV-CH7-55 | §4 | mapped |
| INV-CH7-56 | §4 | mapped |
| INV-CH7-57 | §2B.4 | mapped |
| INV-CH7-58 | §2B.4 | mapped |
| INV-CH7-59 | §2B.4 | mapped |
| INV-CH7-60 | §2B.4 | mapped |
| INV-CH7-61 | §2B.4 | mapped |
| INV-CH7-62 | §2B.4 | mapped |
| INV-CH7-63 | §2B.4 | mapped |
| INV-CH7-64 | §2B.4 | mapped |
| INV-CH7-65 | §5 | mapped |
| INV-CH7-66 | §2B.4 | mapped |
| INV-CH7-67 | §5 | mapped |
| INV-CH7-68 | §4 | mapped |
| INV-CH7-70 | §7 | mapped |
| INV-CH7-71 | §7 | mapped |
| INV-CH7-72 | §7 | mapped |
| INV-CH7-73 | §7 | mapped |
| INV-CH7-74 | §7 | mapped |
| INV-CH7-75 | §2B.6 | mapped |
| INV-CH7-76 | §2B.6 | mapped |
| INV-CH7-77 | §2B.6 | mapped |
| INV-CH7-78 | §2B.6 | mapped |
| INV-CH7-79 | §2B.5 | mapped |
| INV-CH7-80 | §2B.5 | mapped |
| INV-CH7-81 | §2B.5 | mapped |
| INV-CH7-82 | §5 | mapped |
| INV-CH7-83 | §2B.5 | mapped |
| INV-CH7-84 | §3.6 | mapped |
| INV-CH7-85 | §2B.5 | mapped |
| INV-CH7-86 | §2B.5 | mapped |
| INV-CH7-87 | §2B.5 | mapped |
| INV-CH7-88 | §4 | mapped |
| INV-CH7-89 | §2B.5 | mapped |
| INV-CH7-90 | §2B.5 | mapped |
| INV-CH7-91 | §6.2 | mapped |
| INV-CH8-01 | §2A.4 | mapped |
| INV-CH8-02 | §2A.4 | mapped |
| INV-CH8-03 | §2A.4 | mapped |
| INV-CH8-04 | §2A.4 | mapped |
| INV-CH8-05 | §2A.4.1 | mapped |
| INV-CH8-06 | §2A.4.3 | mapped |
| INV-CH8-07 | §6.1 | mapped |
| INV-CH8-08 | §8.2 | mapped |
| INV-CH8-09 | §2A.4.4 | mapped |
| INV-CH8-10 | §2A.4.4 | mapped |
| INV-CH8-11 | §2A.4 | mapped |
| INV-CH8-12 | §3.4 | mapped |
| INV-CH8-13 | §2A.5.1 | mapped |
| INV-CH8-14 | §2B.4 | mapped |
| INV-CH8-15 | §2B.5 | mapped |
| INV-CH8-16 | §5 | mapped |
| INV-CH8-17 | §2B.1 | mapped |
| INV-CH8-18 | §5 | mapped |
| INV-CH8-19 | §5 | deferred: Supervision Quality out of v0 SDK scope per D-IMPL-48 — documented reference pattern (§5), not mechanism |
| INV-CH8-20 | §2B.5 | mapped |
| INV-CH8-21 | §6.4 | deferred: Conversational Reporting Layer out of v0 scope per CLAUDE.md §13 (§6.4); underlying primitives (Π, D_c gating, replay) in scope individually |
| INV-CH8-22 | §3.8 | mapped |
| INV-CH8-23 | §5 | mapped |
| INV-CH8-24 | §6.4 | mapped |

**Census:** 126 rows; 124 mapped, 2 deferred (both deferrals are ruled dispositions, not coverage gaps).

---

## Appendix B — Review Appendix (carried-forward findings)

Advisory findings carried forward from the Phase R Review Appendix (`docs/SPEC_INVENTORY.md`), with Phase D dispositions. Zero blocking findings were carried in.

| ID | Finding (Phase R, advisory) | Phase D disposition |
|----|------------------------------|---------------------|
| F-1 | Non-normativity of numeric examples — every numeric value in inventory entries (0.85/0.75 thresholds, TTL examples, cost-band multipliers) is illustrative, never an SDK default | Honored throughout: all such values designed as Control Plane configuration (D-IMPL-38/39/40); §2B.1/§2B.3 state the illustrative status inline (INV-CH7-30/50/53) |
| F-2 | Phase D sequencing guidance — resolve D-IMPL-01 before D-IMPL-41; D-IMPL-30 gates the contract type surface | Followed: D-IMPL-01 ruled in batch 1 before the D-IMPL-41 stack design; D-IMPL-30 (nine elements) ruled before the §2B.3 contract design; the eight-element drift annotation (incl. CLAUDE.md §5) is carried in §2B.3 per the ruling |
| F-3 | D-NN range intentionally non-contiguous — audit tooling must not assume a sequential range | Carried forward as a constraint on the CINV lint/audit tooling design (§9); no design element assumes contiguity |
| F-4 | Load-Bearing Figures list is a superset; strictly-load-bearing trimming left to Phase D discretion | Phase D cited figures where load-bearing (Fig-CH07-02/03/04/05/06/10/13, Fig-CH07-24, Fig-CH08-01/02/03); no trimming of the inventory list performed — deferred to Phase F if needed |
| F-5 | Format drift in §7.8–§7.10 inventory entries (bullet-style labels) — cosmetic | No action needed; keys and content complete; this document's Appendix A keys resolved against the inventory without ambiguity |

---

## Appendix C — D-IMPL Ruling Index

Every `D-IMPL-NN` ruling embodied in this design, with the sections that cite it. All rulings are RESOLVED (`docs/DECISIONS.md`, approver: Dave, 2026-07-25); D-IMPL-10 (repo shape) remains provisionally resolved and is cited only for orientation. The D-NN/D-IMPL-NN range is intentionally non-contiguous (Appendix B, F-3).

| Ruling | Cited in sections |
|--------|-------------------|
| D-IMPL-01 | §2A, §2B |
| D-IMPL-02 | §2A, §8 |
| D-IMPL-03 | §2B, §8, §9 |
| D-IMPL-04 | §2A, §2B, §8 |
| D-IMPL-05 | §2A, §2B, §7 |
| D-IMPL-06 | §2B, §8 |
| D-IMPL-07 | §2A, §2B |
| D-IMPL-08 | §2A, §3, §9 |
| D-IMPL-09 | §2A, §2B, §3, §9 |
| D-IMPL-10 | §1 |
| D-IMPL-11 | §3, §4 |
| D-IMPL-12 | §3, §8 |
| D-IMPL-13 | §2A, §2B, §6, §8 |
| D-IMPL-14 | §8 |
| D-IMPL-15 | §5, §8 |
| D-IMPL-16 | §2A, §4, §8, §9 |
| D-IMPL-17 | §3, §4, §8, §9 |
| D-IMPL-18 | §2A, §3, §4, §5, §8 |
| D-IMPL-19 | §3, §4 |
| D-IMPL-20 | §5, §6, §8, §9 |
| D-IMPL-21 | §5, §8, §9 |
| D-IMPL-22 | §5, §6, §8 |
| D-IMPL-23 | §2A, §6, §9 |
| D-IMPL-24 | §3, §4, §8, §9 |
| D-IMPL-25 | §2A, §8, §9 |
| D-IMPL-26 | §2B, §3, §4, §5, §6, §8 |
| D-IMPL-27 | §2A, §2B, §4, §8, §9 |
| D-IMPL-28 | §3, §4, §7, §9 |
| D-IMPL-29 | §3, §8 |
| D-IMPL-30 | §2B |
| D-IMPL-31 | §2B |
| D-IMPL-32 | §2B, §3, §5 |
| D-IMPL-33 | §2A, §6, §8 |
| D-IMPL-34 | §2A, §7, §9 |
| D-IMPL-35 | §2A |
| D-IMPL-36 | §2A, §2B, §8, §9 |
| D-IMPL-37 | §2B, §5 |
| D-IMPL-38 | §2B, §3, §5, §7, §9 |
| D-IMPL-39 | §2B, §7, §9 |
| D-IMPL-40 | §2B, §5 |
| D-IMPL-41 | §2A, §7, §8, §9 |
| D-IMPL-42 | §2B |
| D-IMPL-43 | §2B, §5, §7 |
| D-IMPL-44 | §2A, §2B |
| D-IMPL-45 | §2B, §8 |
| D-IMPL-46 | §2A, §2B, §5 |
| D-IMPL-47 | §2B |
| D-IMPL-48 | §5 |
| D-IMPL-49 | §2B, §3, §4 |
| D-IMPL-50 | §2B, §8 |

**Census:** 50 distinct rulings cited across the design body (§1–§9).
### Replay contributions by pillar (CLAUDE.md §4 cross-check)

Every pillar contributes to the five-dimension Decision Replay record; the design realizes each contribution as follows:

| Pillar | Replay contribution | Designed in |
|--------|--------------------|-------------|
| Data and Context Layer | Context fabric snapshot, policy bindings, model versions, content generation path (dimensions 1–3, 5) | §2B.5 |
| Core Agent Types | Agent identity, version, configuration, and skill-set in force (dimension 4) | §3.6, §3.7 |
| Orchestration Layer | Workflow trace and calling chain (dimensions 4–5); Mode 3 record primitives | §4 |
| Human in the Loop and Control | Human actions with `HumanPrincipalBinding` (dimension 2 extension) | §5 |
| Experience Layer | Calling surface, authenticated principal, rendering selection | §8.6 |
