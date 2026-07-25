# Inventory Fragment — Whitepaper Ch 5 (Conceptual Model) and Ch 6 (Context as a Product)

**Canonical authority:** `docs/CCF_Whitepaper_1-2.md`. All section citations reference the `.md`, never the PDF (locked D-01). Spot-check gate: `fragments/spotcheck-report.md` records `VERDICT: PASS`.

Keys are chapter-scoped: `INV-CH5-NN` / `INV-CH6-NN`. Every entry carries the seven mandatory fields per CLAUDE.md §16. Open questions are emitted **unnumbered**; the synthesis plan (01-11) assigns D-IMPL-30+ numbers.

---

## Chapter 5 — The Cognitive Context Fabric: Conceptual Model

### INV-CH5-01 — Three-tier enterprise architecture: Record → Signal Generation → Cognition

- **Section:** §5.1
- **Commitment:** Enterprise information architecture is a three-tier stack. Tier 1, Systems of Record, answers "what happened" (ledgers, customer systems, event streams). Tier 2, Systems of Signal Generation, is the governed substrate (medallion, mesh, MDM, knowledge graphs, semantic layers, feature stores, document stores) delivering governed signal at particular grains and cadences — none of which produces decisions. Tier 3, Systems of Cognition, is the interpretive layer whose sole responsibility is constructing meaning at decision time; historically externalized into human analysts, the agentic shift relocates it into the architecture. The cognition tier composes above the lower tiers; it does not replace them ("a layering of responsibilities").
- **Type signature:** none given
- **Invariants:** The cognition tier never replaces Tier 1/Tier 2; it composes above them. Interpretation is internalized by the architecture, not delegated to the consumer.
- **Dependencies:** INV-CH5-03 (the Context Graph formalism through which Tier 3 represents state); Ch 4 gap diagnosis (context antecedent).
- **Figures:** Fig-CH05-02 (three-tier model, placed at §5.6)
- **Open question:** none

### INV-CH5-02 — Data-perspective vs context-perspective boundary (Knowledge Catalog six-tuple verdicts)

- **Section:** §5.1
- **Commitment:** The boundary between Tier 2 and Tier 3 is named explicitly as data-perspective vs context-perspective. The data-perspective productizes entities, relationships, and lineage ("these objects exist, these connect to those, this came from that") — Google Cloud Knowledge Catalog is the canonical adversarial reference. The context-perspective begins where it ends: time as bitemporal validity-as-state (T) rather than refresh cadence; policy as graph-state element shaping composition (P) rather than post-hoc access control; role as typed reshape per principal (Π) rather than RBAC over one canonical schema. The six-tuple verdict table records: E HIT, R HIT (substrate-tier productization the CCF inherits), T MISS, P MISS, Π MISS (the cognition-tier additions), L PARTIAL (catalog-level lineage exists; per-claim lineage is the cognition-tier extension). The CCF explicitly does not duplicate the Tier-2 productization toolchain.
- **Type signature:** none given
- **Invariants:** T + P + Π are cognition-tier primitives the substrate does not assume; L extends from catalog-level (Tier 2) to per-claim (Tier 3). The verdict table is the canonical authoritative reference (Ch 4 §4.5.2 cross-cites it).
- **Dependencies:** INV-CH5-03 (six-tuple); INV-CH5-08 (composition-above posture per architecture family).
- **Figures:** none
- **Open question:** none

### INV-CH5-03 — Context Graph six-tuple definition G(E, R, T, P, Π, L)

- **Section:** §5.2
- **Commitment:** The Context Graph is the formal structure through which the cognitive layer represents state, defined as the six-tuple `G(E, R, T, P, Π, L)` — the minimum set of dimensions required for decision-time reasoning to be valid. "Each dimension is necessary. None are optional." The distinguishing claim vs knowledge graphs: "A knowledge graph tells you the relationship exists. A context graph tells you whether that relationship was active, relevant, and authoritative at decision time" — T, P, Π, L are what separate the two. The six-tuple strictly extends the semantic-layer four-tuple (M, D, T, J) with Policy, Perspective, and Lineage as first-class dimensions of the formalism (not metadata on query results).
- **Type signature:** `G(E, R, T, P, Π, L)`
- **Invariants:** All six dimensions mandatory; removal of any one produces a named, testable failure mode (see INV-CH5-04). The six-tuple is a strict superset of (M, D, T, J).
- **Dependencies:** INV-CH5-04 (per-dimension semantics); Ch 7 §7.3 (mechanism-level graph specification — inventoried by the Ch 7 fragment).
- **Figures:** Fig-CH05-01 (six-tuple vs four-tuple extension)
- **Open question:** none

### INV-CH5-04 — Per-dimension semantics and necessity tests (E, R, T, P, Π, L)

- **Section:** §5.2
- **Commitment:** Each dimension carries defined semantics: **E** — entities as semantic anchors (not records); ambiguous anchoring makes everything attached unreliable. **R** — typed relationships capturing exposure, influence, dependency, interaction ("not just joins"). **T** — temporal validity ("whether it remains relevant"), signals discounted by context half-life. **P** — constraints (regulatory, governance, thresholds, entitlements, jurisdictional residency) that shape context *before* reasoning, determining valid inputs and permissible outputs. **Π** — role-based interpretation as a dimension of context itself, not a presentation layer. **L** — construction record (signals used, relationships traversed, policies applied, transformations, model versions) enabling explanation, validation, and replay; extends to passage-level for unstructured sources. Necessity is demonstrated by six banking vignettes, each mapping a removed dimension onto a named failure mode (Context Starved, relational Context Starved, Content Static, Policy Blind, Perspective Flat, and the lineage/auditability extension), using Ch 3 §3.6 vocabulary.
- **Type signature:** none given
- **Invariants:** Policy shapes context before reasoning, not after. Perspective is intrinsic to context, not presentation. Lineage must support decision replay and examiner re-tracing.
- **Dependencies:** INV-CH5-03; Ch 3 §3.6 failure-mode vocabulary; Ch 7 §7.7 (half-life formalism), §7.10 (replay/passage-level lineage) — Ch 7 fragment.
- **Figures:** Fig-CH05-01
- **Open question:** none

### INV-CH5-05 — Dynamic context vs dynamic content separation

- **Section:** §5.3
- **Commitment:** Dynamic context (situational intelligence — what is true now and why it matters) and dynamic content (expressive intelligence — outputs that communicate/justify/act) are distinct capabilities with a strict directional relationship: "Context informs content. Content does not define context." The cognitive layer constructs dynamic context only; it does not generate content — it is the foundation content-generating systems operate on. Content-first pipelines (stored retrieval artifacts reassembled at query time) are named as the blurred anti-pattern: they produce dynamic content from fundamentally static retrieval, whereas the fabric continuously reconstructs graph state at decision time.
- **Type signature:** none given
- **Invariants:** The context-constructing layer never generates content; the informing relationship is unidirectional (context → content).
- **Dependencies:** INV-CH5-07 (derived-not-stored); INV-CH5-03.
- **Figures:** none
- **Open question:** none

### INV-CH5-06 — Core thesis: context, not data, is the unit of decision-making

- **Section:** §5.4
- **Commitment:** "Context (not data) is the unit of decision-making." Data is an input; context is an interpretation. Four derived requirements: (1) context must be constructed dynamically at runtime — it cannot be precomputed, because relevance depends on the specific decision; (2) it must integrate multiple dimensions simultaneously; (3) it must be validated before use — completeness, consistency, policy compliance, temporal validity; (4) it must be traceable — every decision explainable via a record of how context was constructed. Context becomes an explicit, engineered first-class system capability.
- **Type signature:** none given
- **Invariants:** No precomputation of context; validation precedes use; traceability of construction is mandatory.
- **Dependencies:** INV-CH5-03; INV-CH5-07; INV-CH6-03 (contract that operationalizes validation/traceability).
- **Figures:** none
- **Open question:** none

### INV-CH5-07 — Context Products are derived, not stored (project-then-retrieve)

- **Section:** §5.6
- **Commitment:** Context Products are the operational output of the cognitive layer: dynamically constructed projections of the Context Graph shaped by the decision's intent, the role's perspective, the temporal validity required, and the policy in force. The same signals yield different products under different conditions. "Derived not stored": assembled at request time from current graph state, never pre-materialized. Passage-level Lineage records the page-and-paragraph span each claim rests on (surfaceable to a reviewer in under five seconds); Anthropic's Citations API is named as the component primitive (specified Ch 7). The contract carries Assembly Mode as a per-product property naming one of three modes (pure algorithmic; algorithmic with LLM packaging; algorithmic orchestration with agent-swarm assembly). The structural distinction vs the GraphRAG pipeline family is **retrieve-then-filter vs project-then-retrieve**; the structural rejection of context-as-weights (test-time training) is that a weight delta cannot encode T, P, Π, L and is not replayable.
- **Type signature:** none given
- **Invariants:** No pre-materialization; policy shapes the candidate space before retrieval runs; every claim from unstructured sources carries passage-level lineage; the fabric owns the substrate for any decision class where replay or policy binding is load-bearing.
- **Dependencies:** INV-CH5-03; INV-CH6-02/03 (full contract in Ch 6); Ch 7 §7.4 (Policy-before-Similarity composition), §7.6 (Assembly Mode mechanism), §7.10 (Citations/replay) — Ch 7 fragment.
- **Figures:** Fig-CH05-02
- **Open question:** none

### INV-CH5-08 — Mapping data systems to CCF: composition above, not replacement

- **Section:** §5.5
- **Commitment:** Seven architecture families are repositioned, not replaced, each with a named contribution, gap, and composition rule: Medallion (Gold is one signal source for Operators); Data Mesh (Context Products are the consumer-side composition partner of Data Products); MDM (golden records are the authoritative E source; CCF composes R/T/P/Π/L above); Knowledge Graphs (KG storage is substrate for E and R; CCF adds T/P/Π/L inside the formalism); Semantic Layers (G-tuple is strictly richer algebra than (M, D, T, J)); Feature Stores (Context Products subsume feature views; Π adds role-differentiation); Document/Search/Vector stores (referenced as L1 signal sources; parse → chunk → embed → policy-shape → similarity-rank → graph-edge pipeline lands unstructured content in G). The posture is formally named "layering, not replatforming" (Ch 8 §8.2).
- **Type signature:** none given
- **Invariants:** Every family is a composition partner; existing investments are preserved. MDM identity is inherited, never duplicated. Unstructured stores are L1 sources, not context stores.
- **Dependencies:** INV-CH5-01 (tier model); INV-CH5-02; Ch 8 §8.2/§8.3 integration patterns — Ch 8 fragment.
- **Figures:** Fig-CH05-02
- **Open question:** none

### INV-CH5-09 — Five-component fabric architecture (named: Cognitive Context Fabric)

- **Section:** §5.7
- **Commitment:** The cognitive layer is formally named the Cognitive Context Fabric, comprising five components with specific responsibilities: (1) Context Graph — structural substrate of state per the six-tuple; (2) Context Operators — computational machinery for traversal, temporal evaluation, policy shaping, similarity analysis, and perspective projection; (3) Context Assembly Layer — integrates Operator outputs into coherent runtime projections ("where meaning is produced"); (4) Context Products — Assembly outputs delivered through the uniform contract; (5) control plane — governs the interaction of the other four, enforces policy, records lineage for decision replay. Each component exists because it addresses a requirement the six dimensions impose.
- **Type signature:** none given
- **Invariants:** Five components, each with a single named responsibility; the control plane is the governance and lineage-recording locus.
- **Dependencies:** INV-CH5-03; full mechanism specification Ch 7 (Ch 7 fragment).
- **Figures:** none
- **Open question:** none

### INV-CH5-10 — Prior art acknowledgment and claimed novelty boundary

- **Section:** §5.7.1
- **Commitment:** The fabric is "a synthesis, not an invention," and acknowledgment is part of the specification. Named precedents and the exact extension claimed over each: Zep/Graphiti bitemporal knowledge graph (T builds on it; CCF adds per-claim context half-life and supersession-as-Policy-event); Palantir Foundry Ontology (closest full-stack analog; gaps closed are explicit Π as typed function and a formal Half-Life primitive); OPA (policy machinery inherits externalized-decision semantics; CCF extends from boundary enforcement to composition — policy shapes the candidate subgraph before retrieval); semantic layers ((M, D, T, J) → strictly richer G-tuple). Claimed contribution: the unified six-tuple with explicit P, Π, L as first-class citizens, operated on by deterministic Context Operators, emitted as Context Products derived at request time. "The composition is novel; the ingredients are not."
- **Type signature:** none given
- **Invariants:** Supersession is a Policy event; Context Operators are deterministic; policy-before-retrieval composition.
- **Dependencies:** INV-CH5-03; INV-CH5-07; Ch 7 operator/half-life mechanisms — Ch 7 fragment.
- **Figures:** none
- **Open question:** none

---

## Open Questions (unnumbered)

*(Populated across both tasks; synthesis assigns D-IMPL-30+.)*

- *(from Ch 5 extraction)* None surfaced — Ch 5 is conceptual and defers all mechanism ambiguity to Ch 7, whose fragment carries those questions.
