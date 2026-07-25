# SPEC_INVENTORY — CCF SDK v0

**Canonical authority:** `docs/CCF_Whitepaper_1-2.md` — the converted whitepaper `.md` is authoritative; every citation in this inventory references its sections, never the PDF (locked D-01). Where the whitepaper and any other source disagree, the whitepaper wins. Where an entry notes an **SDK-defined** extension, the citation is to `CLAUDE.md` (revision 4) and the extension is explicitly labeled per CLAUDE.md §1.

**Produced in Phase R** (deliverable per CLAUDE.md §3 and §16). Extraction gated on `fragments/spotcheck-report.md` `VERDICT: PASS` (locked D-03).

## Structure and Key Scheme

- **Keys are chapter-scoped:** `INV-CH5-NN`, `INV-CH6-NN`, `INV-CH7-NN`, `INV-CH8-NN`. Chapter 7's key space is partitioned by extraction slice (01–39 for §7.1–§7.4; 40–69 for §7.5–§7.7; 70+ for §7.8–§7.10) to prevent collisions; keys are stable identifiers, not sequence numbers.
- **Every entry carries the seven mandatory fields** per CLAUDE.md §16: whitepaper section, paraphrased commitment, type signature (where given), invariants, dependencies, figure references, and an open-question field.
- **Open questions** carry `D-IMPL-NN` cross-references into `docs/DECISIONS.md` (numbers from D-IMPL-30 assigned at synthesis; D-IMPL-01..29 originate in CLAUDE.md §12).
- **Chapter sections** cover whitepaper Chapters 5–8; the five cross-cutting §16 sections (governance D-NN catalog, load-bearing figures, named invariants, SDK extensions with hooks, pillar mapping) and the subsection coverage proof follow the chapter sections. The `homecams-patterns` appendix closes the document.

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

## Chapter 6 — Context as a Product

### INV-CH6-01 — Data products are insufficient outputs; category change, not variant

- **Section:** §6.1
- **Commitment:** Three data-product assumptions break under agentic consumption: interpretation occurs outside the system; context is reconstructed by the consumer; decisions are made downstream of data access. "Data products are necessary inputs. They are insufficient outputs." The gap is a category mismatch, not a quality issue — Data Products and Context Products are different contracts serving different consumers under different temporal disciplines, and are composition partners, not competitors. The persistent-vs-ephemeral posture distinction is structural: Data Products are refresh-scheduled stored artifacts; Context Products exist only for the decision moment plus TTL window. The canonical 8-property contract test against Google Data Product records three HITs (Schema-ish; Refresh-as-Freshness; Discovery/Addressability via MCP toolbox) and five MISSes as the category-change set (Runtime-assembled; TTL-with-recompute; Π typed reshape; Policy-at-construction; Entitlement-formative). A six-row table names the differences in kind (persisted vs runtime-constructed; human interpretation vs machine-consumable meaning; periodic freshness vs TTL-bound validity; schema-centric vs G-tuple-centric; post-retrieval access governance vs policy-embedded by construction; reusable inputs vs decision-scoped outputs) — the first three axes (runtime construction, principal-scoped policy embedding, TTL-bound validity) are the minimum differentiators. The RAG objection is answered architecturally: retrieve-then-filter vs project-then-retrieve, enabled by Policy-before-Similarity composition (Ch 7 §7.4).
- **Type signature:** none given
- **Invariants:** The two postures are structurally incompatible at the policy layer; composable only if CCF sits above the catalog. Policy shapes the candidate space before retrieval runs.
- **Dependencies:** INV-CH5-07 (derived-not-stored); INV-CH6-03 (contract elements); Ch 7 §7.4 (composition mechanism) — Ch 7 fragment; Ch 8 §8.2 ("layering, not replatforming").
- **Figures:** Fig-CH06-01 (Context Product vs Data Product lifecycle, incl. closing replay edge)
- **Open question:** none

### INV-CH6-02 — Definition of Context Product and the four shaping forces

- **Section:** §6.2
- **Commitment:** A Context Product is "a typed, governed, decision-ready unit of meaning, constructed dynamically at runtime to reflect the current state of the world as it relates to a specific intent." Four interdependent forces shape any Context Product at construction: **Intent** (the decision driving the request — same graph, different context shapes per intent); **Perspective (Π)** (role of the consuming agent, as a first-class dimension, not display-layer transformation); **Time (T)** (temporal validity per signal, with explicit decay asymmetry — a nine-month-old 10-K vs a fifteen-minute-old blotter entry); **Policy (P)** (shapes which signals may be composed, which actions recommended, which entities mentioned — never a post-construction filter). Construction jointly answers five questions: what is relevant now; what remains valid; how are elements connected; what actions are permitted; why is this the case.
- **Type signature:** none given
- **Invariants:** The four forces are interdependent dimensions of a single construct, not separable properties. Policy is formative, never a post-hoc filter.
- **Dependencies:** INV-CH5-03 (six-tuple); INV-CH6-03 (contract).
- **Figures:** none
- **Open question:** none

### INV-CH6-03 — Context Product Specification: the contract elements

- **Section:** §6.3
- **Commitment:** The contract is the guarantee making the product a reliable interface. The specification table enumerates the elements: (1) **Schema** — context-aware typed structure of entities/relationships/attributes, aligned to G(E, R, T, P, Π, L); the projection shape is the product's identity; (2) **Freshness SLA** — how current underlying signals must be (seconds for fraud, minutes for liquidity, hours/days for credit); expectation of currency, sibling of TTL, varying by signal and decision; (3) **TTL** — bounded validity after which the product is invalid and must be recomputed against current graph state; (4) **Policy Binding** — regulatory/institutional constraints encoded in the product; "agents do not 'check policy' after the fact"; construction refuses the impermissible; (5) **Lineage** — sources, transformations, applied policies, model versions; passage-level for unstructured claims; substrate for auditability, replay, trust; (6) **Semantic Versioning** — controlled evolution; agents pin versions with preserved migration paths; (7) **Discovery** — registry locating products by intent, domain, capability; (8) **Addressability** — well-defined interfaces for structured queries carrying intent, role, and freshness parameters (address pattern `/context-products/credit-risk/counterparty/{counterparty-id}?intent=lending-decision&freshness=...`); (9) **Assembly Mode** — per-product configuration property under trust-path purity naming one of three modes (pure algorithmic assembly; algorithmic assembly with LLM packaging; algorithmic orchestration with agent-swarm assembly), committing the cost/quality/determinism tradeoff at product-class registration time (mechanism Ch 7 §7.6). The §6.1 8-property contract test maps onto these elements; §6.3 cross-cites it as canonical.
- **Type signature:** address pattern `/context-products/{domain}/{product}/{id}?intent=...&freshness=...` (illustrative, given in §6.3)
- **Invariants:** Three validation gates attach to this contract at mechanism level (empty-operator guard, lineage strict equality, TTL bounds — Ch 7 §7.6, Ch 7 fragment). Policy Binding is enforced at construction. Assembly Mode is a documented governance-time decision, not an emergent runtime property. Trust-path purity holds invariant across all three modes.
- **Dependencies:** INV-CH6-01 (8-property test); INV-CH6-04 (lifecycle integration); Ch 7 §7.6 (validation gates + Assembly Mode mechanism) — Ch 7 fragment.
- **Figures:** none
- **Open question (D-IMPL-30):** The element count is internally inconsistent in the `.md`. §6.3 prose opens "Nine elements jointly specify the contract" and the table lists nine (Assembly Mode included; §6.4 calls it "the §6.3 specification's ninth element"), yet the same §6.3 prose describes the §6.1 contract test as "the § 6.1 canonical 8-property table" and says "the 8-property test names what the contract carries; the 9-element specification names which contract surface each property maps to" — while CLAUDE.md §5 refers to "the eight-element specification per §6.3." Readings: (a) the contract has nine elements and the "eight" references (8-property test, CLAUDE.md) denote the external comparison test only — consequence: the SDK Context Product Contract base must carry all nine fields including Assembly Mode; (b) the contract has eight elements and Assembly Mode is a distinct per-product *configuration* property layered on the contract rather than a contract element — consequence: Assembly Mode lives in Control Plane product-class registration, not in the product schema; (c) the whitepaper drifted between revisions and the count is editorial — consequence: Dave rules which count is canonical and CLAUDE.md or the inventory annotates the discrepancy. The mapping from the 8 test properties to the 9 elements is asserted but never tabulated, so the property→element correspondence is also unspecified.

### INV-CH6-04 — Eight-step Context Product Lifecycle with closed-loop audit feedback

- **Section:** §6.4
- **Commitment:** A canonical eight-stage lifecycle: (1) Event/Data Ingestion — signals enter with source metadata preserved (origin system, emission timestamp, emitting principal, payload schema version) as the precondition for Lineage, Temporal Validation, and Replay; (2) Semantic Resolution — ontology mapping and entity resolution into the shared semantic frame; (3) Context Graph Mutation — append-plus-supersession discipline; "Mutation never overwrites; it layers, so temporal truth remains reconstructible"; (4) Temporal Validation — TTL assignment and validity assessment; refuses to assemble products that silently mix signals of asymmetric freshness; (5) Policy Binding — constraints applied during construction; impermissible reasoning paths foreclosed before serving; (6) Context Serving — via the addressable endpoint under the full contract; (7) Agent Consumption — the agent reasons only; no assembly work (no entity resolution, temporal stitching, policy filtering, re-interpretation); (8) Replay & Audit — action captured for replay; audit findings feed back as policy updates entering Step 1. "The lifecycle is a loop, not a pipeline." Products are inherently ephemeral; any change in signal, intent, policy, or entitlement requires reconstruction. The architectural heart is **trust-path purity** — deterministic source-of-record with optional probabilistic presentation: the algorithmic substrate is the artifact-of-record; renderings are presentation. Algorithmic and semantic stages alternate: Steps 1–6 algorithmic, Step 7 semantic, Step 8 algorithmic; "No semantic stage operates on raw signal, and no algorithmic stage performs semantic interpretation." Three consequences: replayable/auditable deterministic assembly; reduced hallucination surface (LLM sees dimensionally reduced, policy-enriched substrate); contained cost.
- **Type signature:** none given
- **Invariants:** Append-plus-supersession (no overwrite); assembly-vs-reasoning division of labor (Step 7 does no assembly); trust-path purity across all Assembly Modes (substrate is artifact-of-record; lineage recorded at substrate, not rendering; replay re-derives the substrate deterministically from the same graph state); Algorithmic ⇄ Semantic Alternation; the Step 8 → Step 1 feedback edge closes the loop.
- **Dependencies:** INV-CH6-03 (contract elements enforced through the lifecycle); Ch 7 §7.4 (Operators as the algorithmic-stage combination mechanism), §7.6 (Assembly Mode mechanism) — Ch 7 fragment.
- **Figures:** Fig-CH06-02 (eight-step lifecycle with dotted feedback edge)
- **Open question (D-IMPL-31):** §6.4 Step 4 states "Temporal Validation assigns TTL to each mutation," while §6.3 defines TTL as a per-product contract element and §6.4's Counterparty thread gives per-product TTLs (four hours trading-desk, twenty-four hours committee) alongside per-signal TTLs ("an intraday trade-blotter entry carries a TTL of fifteen minutes"). Readings: (a) TTL exists at two granularities — per-mutation/per-signal validity in T and per-product validity in the contract — and the product TTL is derived from (e.g., min over) constituent signal validities; consequence: the SDK needs both a signal-level validity primitive and a product-level TTL with a defined derivation rule; (b) "TTL" in Step 4 loosely means the T-dimension validity envelope (half-life driven) and only the contract-level TTL is properly named TTL; consequence: naming must be disambiguated in the SDK type surface to avoid conflating half-life-derived validity with contract TTL; (c) product TTL is independently configured per product class and Step 4 only validates constituent signals against it; consequence: no derivation rule is required but a mixing-refusal rule (asymmetric-freshness refusal) still needs formal definition. The whitepaper does not specify the derivation or refusal rule; Ch 7 §7.7 may partially resolve this (Ch 7 fragment to cross-check).

### INV-CH6-05 — Seven Context Product key principles

- **Section:** §6.5
- **Commitment:** "Agents do not consume data directly. They consume context." Seven principles the product must uphold: (1) **Runtime Construction** — never persisted-and-retrieved; a requirement, not an optimization; (2) **Time-bound (TTL)** — implicit or explicit TTL enforcing continuous recomputation; an expired product "is not merely stale; it is invalid under the contract"; (3) **Policy-embedded** — construction forecloses impermissible compositions; compliant by construction; (4) **Entitlement-aware** — entitlements are formative constraints, with three implications: agents only see context they may reason over (correctness, not just security); sensitive relationships never materialize for unauthorized consumers (syndicate participation, MNPI boundaries, advisor-client confidentiality); policy and access unify into a single construct — two agents on the same signals may receive different products; (5) **Discoverable** — registry by intent/domain/capability; runtime name-to-endpoint resolution; (6) **Traceable (Lineage)** — full construction lineage for supervisors, auditors, internal control; (7) **Interoperable** — integrates with MCP (agent-to-tool discovery/invocation) and A2A (cross-agent federation) so a product specified once is consumable across frameworks.
- **Type signature:** none given
- **Invariants:** TTL expiry ⇒ contract invalidity (not degradation). Entitlements shape the product, never a view on top of it. Unauthorized edges never materialize.
- **Dependencies:** INV-CH6-03 (contract elements the principles govern); INV-CH6-06 (MCP boundary); Ch 8 §8.3 Pattern 3/4 (MCP/A2A integration patterns) — Ch 8 fragment.
- **Figures:** none
- **Open question:** none

### INV-CH6-06 — MCP as the access layer; CCF as the construction layer

- **Section:** §6.5.1
- **Commitment:** MCP is the access layer through which agents request Context Products; CCF is the construction layer producing them. Conflating them is "the most common misreading." The responsibility boundary: CCF constructs context (signal integration, validation, transformation into meaning) and owns state management, temporal logic, and policy application; MCP provides discovery, request, and standardized invocation — it bridges agents to the Context Assembly Runtime and nothing more. Canonical request path: `Agent → MCP Interface → Context Assembly Runtime → Context Graph → Context Product → Agent`. Two architectural advantages: construction stays centralized/governed/consistent (one construction layer, one invariant set, one audit substrate regardless of agent frameworks above); interoperability becomes a property of the interface. A2A extends interoperability to cross-agent federation (Ch 8 §8.3).
- **Type signature:** request path `Agent → MCP Interface → Context Assembly Runtime → Context Graph → Context Product → Agent`
- **Invariants:** MCP never manages state, enforces temporal logic, applies policy, or constructs context. One construction layer / one audit substrate regardless of consuming frameworks.
- **Dependencies:** INV-CH6-05 (Interoperable principle); Ch 8 §8.3 Pattern 3 (MCP) and Pattern 4 (A2A) — Ch 8 fragment. SDK-extension hook: CLAUDE.md §7.1 extends Pattern-3 egress to a bidirectional MCP surface (ingress at L1/L4–L5, egress at L6, Experience access, artifact persistence) — an explicit SDK extension beyond this whitepaper commitment.
- **Figures:** none
- **Open question:** none

### INV-CH6-07 — Search ⇄ Inference loop engineered as a Context Product abstraction

- **Section:** §6.6 (§6.6.1, §6.6.2, §6.6.4)
- **Commitment:** Agentic reasoning is a recursive interplay: `inference → drives search; search → enriches context; enriched context → improves inference`, running until sufficient confidence is reached to act or the agent escalates, defers, or refuses. Each line is a commitment; what makes the recursion tractable rather than unbounded is that each iteration is grounded in a Context Product request with a defined contract — the agent never queries raw stores, never assembles its own temporal/policy envelope, never reconstructs entity identities. "Assembly stays in the architecture; reasoning stays with the agent." The three-turn Counterparty worked example (§6.6.2) shows each turn invoking a different Operator composition without the agent specifying operators directly, with Π reshaping per turn. §6.6.4 resolves Ch 3 §3.10's forward reference: the loop is engineered as the Context Product abstraction — one contract, one lifecycle, one principle set, one trust framework, one access layer — replacing per-agent ad-hoc retrieval pipelines.
- **Type signature:** `inference → drives search; search → enriches context; enriched context → improves inference` (three-line loop vocabulary, verbatim)
- **Invariants:** Every loop iteration is a contracted Context Product request; agents never self-assemble context; operator composition is resolved by the Runtime from the request, not specified by the agent.
- **Dependencies:** INV-CH6-03 (contract); INV-CH6-08 (stopping criterion); Ch 7 §7.4 (operator composition invariants) — Ch 7 fragment. SDK-extension hook: CLAUDE.md §7.1 places the search-inference recursion's decision-time content acquisition on the MCP client surface at L4–L5.
- **Figures:** none
- **Open question:** none

### INV-CH6-08 — Context Trust Triangle: conjunctive quality gate and stopping criterion

- **Section:** §6.6.3
- **Commitment:** The recursion's stopping criterion is trust-based, made tractable by the Context Trust Triangle's three legs: **Context Confidence** (is it reliable? — model scores, source reliability, cross-signal consensus); **Context Freshness** (is it current? — TTL, context half-life decay of underlying signals, recency of the most recent bearing event); **Context Lineage Integrity** (is it traceable? — provenance-chain integrity, transformation-audit completeness, L-dimension resolution against source substrate). "The triangle is conjunctive, not disjunctive. Weak legs degrade the whole." An agent facing aggregate-low trust must not act — it escalates, requests a different product, or surfaces the weakness. The triangle also anchors the hallucination answer: four compounding mechanisms (evidence pinning; machine-auditable passage-level Lineage; graph persistence removing per-query re-inference; policy projection constraining the retrieval surface before similarity ranking), plus Context Debt as explicit decision input (Ch 7 §7.7), "reduce the failure surface by changing what the model infers on, not the model itself."
- **Type signature:** none given
- **Invariants:** Conjunctive semantics — weakness in any leg degrades aggregate trust regardless of the other two; low aggregate trust forbids action (escalate/re-request/surface).
- **Dependencies:** INV-CH6-07 (loop it gates); INV-CH6-03 (TTL, Lineage elements the legs consume); Ch 7 §7.7 (half-life, Context Debt) and §7.10 (lineage/replay) — Ch 7 fragment.
- **Figures:** Fig-CH06-03 (Trust Triangle, conjunctive edges)
- **Open question (D-IMPL-32):** §6.6.3 specifies each leg's inputs ("Combines model scores, source reliability, and consensus…") and the conjunctive semantics, but no aggregation function, scale, or threshold mechanics for any leg or for aggregate Context Trust — "when all three legs hold, the recursion may terminate" leaves "hold" undefined. Readings: (a) the aggregation/thresholds are deliberately Control-Plane-configurable values (mechanism ships scoring interfaces; institutions supply thresholds) — consequence: the SDK defines a TrustScore Protocol with pluggable per-leg scorers and a conjunctive combinator, values in configuration per the mechanism-not-values rule; (b) a canonical formula is implied elsewhere (e.g., via Ch 7 §7.7 D_c mechanics) and the legs are derived quantities — consequence: cross-check the Ch 7 fragment before designing an independent trust primitive; (c) the triangle is advisory vocabulary, not a mechanism commitment — consequence: no SDK primitive required, only replay-record capture of whatever trust inputs the deployment computes. The choice gates whether v0 ships a trust-scoring surface.

---


---

## Chapter 7 — The Architecture of Cognition (Mechanism)

Chapter 7 is inventoried in three key blocks: INV-CH7-01..39 (§7.1–§7.4), INV-CH7-40..69 (§7.5–§7.7), INV-CH7-70+ (§7.8–§7.10).

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
- **Open question (D-IMPL-33):** "whatever raw payload the upstream system emitted" — the canonical event envelope's formal schema is not specified; a general-purpose SDK must commit to one.

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
- **Open question (D-IMPL-34):** "the physical representation maps to ~10 collections" — the exact collection decomposition is reference-implementation grounding, not a normative count; what the SDK's storage Protocol must require versus leave to backends is a design question.

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
- **Open question (D-IMPL-35):** The Entity Resolver's correlation mechanism ("shared attributes … where it does not") is described at pattern level; the SDK's resolver contract — pluggable strategy vs shipped mechanism — is a design question.

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
- **Open question:** Threshold declaration/versioning schema is open — see D-IMPL-38.

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
- **Open question (D-IMPL-36):** How the Planner schedules and materializes intermediates (caching policy, reuse decisions for replay invocations) is specified at property level (Fig-CH07-08's reuse note) but not at scheduling-mechanism level; Homecams shows one resolution — do NOT inherit it (CLAUDE.md §2.1).

### INV-CH7-29
- **Section:** §7.4.2
- **Commitment:** Two Planner mechanism commitments. (1) The Planner batch-resolves operator references via a DataLoader-style pattern — one query per operator type per call (N+1 avoidance): all Traversal references resolve in one batched call, all Temporal references in another. This amortizes per-operator cost and is how compositions stay within the §7.6 illustrative SLO envelope. (2) The operator registry is import-time / boot-time loaded, and duplicate registration fails fast: registering two operators under the same reference key is a boot-time failure that "prevents the fabric from serving any traffic until the duplicate is resolved" — not a runtime error during a request. The invariant is CI-tested (§7.8 Architectural Invariants carries the broader framing).
- **Type signature:** Registry: boot-time-loaded map of reference key → operator; duplicate key → boot failure.
- **Invariants:** **Boot-time registry with fail-fast duplicate registration** (CI-tested); batched (DataLoader-style) operator resolution.
- **Dependencies:** INV-CH7-28, §7.6 SLO envelope, §7.8 invariants (plan 01-08's key range).
- **Figures:** Fig-CH07-09.
- **Open question:** Registry population surface for user-supplied operators is open — see D-IMPL-37.

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
**Open question (D-IMPL-39):** "TTL bounds rejects a Contract whose expires_at is in the past or beyond a MAX_TTL envelope" — the whitepaper never specifies where MAX_TTL is configured or its default. Readings: (a) MAX_TTL is a Control Plane configuration per Context Product class (consistent with §7.8's configuration posture; consequence: SDK ships mechanism, users supply values); (b) MAX_TTL is a single fabric-wide constant (simpler, but a hard-coded threshold would collide with the mechanism/values boundary); (c) MAX_TTL derives from the product's λ_c band (elegant but nowhere stated). Left unnumbered for synthesis.

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
**Open question (D-IMPL-40):** "threat_level ≤ LOW" and "class-specific threshold" — the whitepaper does not specify the threat-level scale, its source, or how the class-specific D_c threshold is set. Readings: (a) both are Control Plane configuration per decision class (consistent with §7.8 posture; SDK ships the routing mechanism only); (b) threat level is computed by the fabric from signal characteristics (would require a specified computation the paper never gives). Left unnumbered for synthesis.

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


### INV-CH7-70 — Control Plane / Data Plane separation as first-class primitives

- **Whitepaper section:** §7.8, §7.8.1
- **Commitment (paraphrase):** The fabric commits to a structural separation
  between the Control Plane — the plane that defines what the fabric is
  allowed to do at runtime (policies, operator behavior parameters,
  projection rules, entitlements, D_c thresholds, λ_c values,
  materialization rules) — and the Data Plane — the plane that executes
  against those definitions (assembly engines, operator runtimes, projection
  computations, context-product serving, decision-replay record writers).
  The pattern is adopted from the service-mesh ancestry (Istio/Envoy); CCF
  claims novelty only in the cargo: the Control Plane carries Policy
  definitions, Operator behavior rules, Projection rules and Entitlements,
  per-decision-class D_c thresholds, per-observation-type λ_c, and
  Materialization policy; the Data Plane carries the assembly runtime,
  operator execution engine, projection computation engine, product serving
  tier, and replay-record writers.
- **Type signature:** none given (architectural separation; cargo classes
  enumerated in prose).
- **Invariants:** Control Plane holds definitional authority; Data Plane
  engines execute against Control Plane definitions without owning them.
  Configuration propagates to the Data Plane "under controlled handoff
  protocols."
- **Dependencies:** λ_c table (§7.7, slice B entries), D_c thresholds
  (§7.7), operator behavior (§7.4), projection rules (§7.5),
  materialization/cache tier (§7.6). Governance D-40 (service-mesh
  ancestor).
- **Figure refs:** Fig-CH07-21 (planes with CCF-specific cargo; named
  load-bearing — §7.8 refers back to it for the audit-plane property, the
  configuration surface, and the invariant-enforcement boundary).
- **Open question:** none.

### INV-CH7-71 — The Control Plane is also the audit plane

- **Whitepaper section:** §7.8.2
- **Commitment (paraphrase):** "The control plane is also the audit plane."
  Every Operator invocation, Projection computation, and Context Product
  assembly is observable from the Control Plane for replay — as a
  first-class architectural property of the Control Plane itself, not a
  sidecar observability concern. Every configuration change the Control
  Plane applies (policy version, operator-parameter adjustment,
  projection-rule refinement) is versioned, timestamped, and retained
  against the decisions made under the version in force at the time. The
  audit question — what did the agent know, under what policies, with what
  perspective conditioning, producing what content — is answered by
  reconstructing Control Plane state at decision time and replaying Data
  Plane execution under it (resolved in full by the §7.10 five-dimension
  record).
- **Type signature:** none given.
- **Invariants:** Every runtime decision auditable against the exact
  rule-state in force at decision time; every policy update is a versioned
  event with its own audit entry, and Data Plane invalidation flows as a
  published event, not a direct side-effect on cache state (Fig-CH07-22);
  every policy update traverses that sequence exactly once.
- **Dependencies:** INV-CH7-70 (plane separation); §7.10 replay record
  (INV-CH7-81); §7.6 cache state machine (Fig-CH07-14
  InvalidatedBySupersession). Governance D-41 (control-plane-is-audit-plane).
  Regulatory anchors named: SR 11-7, OCC consent-order re-tracing, EU AI Act.
- **Figure refs:** Fig-CH07-22 (Control Plane ⇄ Data Plane message exchange
  sequence; load-bearing — renders versioned-audit-entry and event-published
  invalidation; named as runtime enactment of D-40, D-41, D-42, D-44).
- **Open question:** none.

### INV-CH7-72 — Control Plane configuration surface enumeration

- **Whitepaper section:** §7.8.3
- **Commitment (paraphrase):** A production Control Plane carries, at
  minimum, six versioned, auditable, controlled-handoff configuration
  classes: (1) Policy definitions (regulatory constraints, internal risk
  thresholds, jurisdictional applicability rules); (2) Operator behavior
  rules (traversal-depth limits, materiality thresholds, temporal-boundary
  rules, similarity-threshold contracts); (3) Projection logic
  (role-to-intent-to-plan lookup tables, projection rules, entitlement
  matrices); (4) D_c thresholds per decision class; (5) λ_c per observation
  type (the §7.7 table, stored as Control Plane configuration so calibration
  updates propagate consistently); (6) Materialization policy per
  Context-Product class. Worked example: a regulatory exposure-limit change
  flows as a single Control Plane update — no graph state, engine code, or
  agent logic changes — the "instant-and-consistent adaptation" property.
- **Type signature:** none given (configuration classes enumerated; the
  specific values are domain calibrations, not SDK content).
- **Invariants:** All six classes versioned and auditable; a calibration
  update propagates consistently across every consumer of the configuration
  without rewriting graph state.
- **Dependencies:** INV-CH7-70/71; operator entries (§7.4), projection
  entries (§7.5), λ_c/D_c entries (§7.7). Governance D-42 (config surface
  enumeration). SDK note (CLAUDE.md §5, §10 — SDK-defined mapping): in the
  SDK, agent definitions, task definitions, prompt artifacts, and skill
  grants are additional Control Plane artifact classes — an SDK extension,
  not a whitepaper commitment.
- **Figure refs:** Fig-CH07-22 (policy-update sequence).
- **Open question:** none.

### INV-CH7-73 — Five architectural invariants, CI-tested at the plane boundary

- **Whitepaper section:** §7.8.4
- **Commitment (paraphrase):** Architectural invariants are "CI-tested, not
  conventional" — the bypass structurally does not exist. Five invariants
  are committed at the Control Plane / Data Plane boundary: (a)
  Single-writer for graph state — only the Assembly worker writes to
  enrichment-surface collections; read-path services receive no
  write-capable handles, enforced by dependency injection at boot and the
  type system at build time; (b) Projection stateless by invariant — the
  Projection engine holds no write locks and no in-process cache;
  materialization lives in a separately gated tier under explicit policy;
  (c) Lineage strict equality — `operators_invoked` must equal the set of
  operators actually resolved during assembly, validated at the stage-3a
  gate, else the product is not served; (d) TTL bounds — every product has
  `expires_at ∈ (now, now + MAX_TTL]` validated at stage-3b, CI-tested at
  both boundaries; (e) Tenant-scoped by kw-only argument — every `execute()`
  call on the assembly engine requires `tenant_id` as a keyword-only
  argument. All five are CI-tested in a reference implementation; conscious
  disablement is a governance event the audit trail captures.
- **Type signature:** partial — `operators_invoked` set equality;
  `expires_at ∈ (now, now + MAX_TTL]`; `execute(*, tenant_id=...)` kw-only.
- **Invariants:** This entry IS the invariant register for the plane
  boundary: single-writer, stateless projection, lineage strict equality,
  TTL bounds, tenant scoping — each enforced structurally (DI, type system,
  function signature, CI gate), never by convention.
- **Dependencies:** §7.3 single-writer graph mechanism; §7.5 projection
  purity; §7.6 validation gates (stage-3a/3b) — cross-links to slice A/B
  entries. Governance D-43 (invariants as first-class commitments).
- **Figure refs:** Fig-CH07-21 (invariant-enforcement boundary).
- **Open question (D-IMPL-41):** "The invariant is enforced by
  dependency injection at boot time — the read-path services' DI containers
  simply do not receive write-capable handles… and the compilation of those
  services against write-capable interfaces is prevented by the type system
  at build time." — The whitepaper assumes a compiled/typed enforcement
  substrate; how the SDK realizes build-time prevention in the target
  language(s) depends on D-IMPL-01 (language target) and is a design
  question for Phase D.

### INV-CH7-74 — Data Plane determinism

- **Whitepaper section:** §7.8.5
- **Commitment (paraphrase):** Given the same graph state, the same Control
  Plane configuration, and the same temporal boundary, the Data Plane
  produces a bit-for-bit identical Context Product on every execution — the
  §7.4 operator-composition determinism claim restated at the plane level
  across assembly, operator execution, projection computation, and
  materialization. No sampling, no temperature-based variation in
  structural-reasoning stages, no hidden randomness in retrieval or
  extraction paths; any admitted randomness (e.g., embedding
  non-determinism under GPU parallelism) is isolated to boundaries the
  replay record can reproduce exactly (same model, same seed, same batch
  shape). This determinism is the architectural foundation that makes
  Decision Replay evidentiary rather than best-effort.
- **Type signature:** none given (determinism property over fixed inputs).
- **Invariants:** Bit-for-bit output identity under fixed (graph state,
  Control Plane config, temporal boundary); randomness isolation at
  reproducible boundaries.
- **Dependencies:** §7.4 composition-preservation (slice B);
  INV-CH7-81 (five-dimension record consumes this property).
  Governance D-44 (Data Plane determinism).
- **Figure refs:** none directly (referenced by Fig-CH07-27's
  bit-for-bit reassembly note).
- **Open question:** none.

### INV-CH7-75 — Closed loop: graph write-back through the Control Plane

- **Whitepaper section:** §7.9, §7.9.1
- **Commitment (paraphrase):** Closed-loop learning flows exclusively
  through the Control Plane as graph write-back — never as direct runtime
  modification of operators, projection, or policy, and never as model
  retraining. The three-stage pattern: (1) outcome observation becomes a
  typed OutcomeSignal carrying Provenance, `observed_at`, and its own λ_c
  (outcome signals are first-class context entities whose evidential weight
  decays); (2) the Control Plane interprets the signal and, where
  warranted, issues a versioned update (operator definition change, policy
  calibration, projection logic refinement, or half-life adjustment) — the
  interpretation step is where business judgment, statistical significance,
  and regulatory calibration constraints enter; (3) Data Plane propagation
  is downstream of the versioned update, with `projection_plan_id` +
  `contract_version` attribution in replay records so historical decisions
  remain re-traceable against the version in force when made. Graph
  write-back is logical, not destructive: outcome evidence appends typed
  outcome edges with their own lineage and temporal binding; prior state
  remains available for replay.
- **Type signature:** pseudocode given —
  `processOutcomeSignal(outcome: TypedOutcome, provenance: Provenance,
  half_life_lambda_c: Duration) -> ControlPlaneUpdate`, with
  `OutcomeSignal(outcome, provenance, observed_at, lambda_c)` and
  `versioned(update)` return.
- **Invariants:** No silent behavioral change: every change to agent-visible
  behavior is a versioned, auditable Control Plane event; write-back is
  append-only/logical; next-agent invocation reads refined graph state, not
  retrained weights.
- **Dependencies:** INV-CH7-70/71 (governance planes); §7.10 record
  (evidence persisted per decision); §7.3 append-only graph (slice A).
  Governance D-45 (write-back pseudocode), D-47 (loop-is-in-the-graph).
- **Figure refs:** Fig-CH07-23 (closed-loop graph write-back sequence;
  load-bearing — renders "the loop is in the graph" operationally).
- **Open question:** none.

### INV-CH7-76 — Three categories of learning signal

- **Whitepaper section:** §7.9.2
- **Commitment (paraphrase):** The Control Plane distinguishes three
  learning-signal categories, each with distinct interpretation logic and
  write-back target: (i) Outcome signals — direct ground truth (repaid /
  defaulted, fraud confirmed / cleared, SAR substantiated / closed), driving
  policy-calibration updates because they measure false-positive/negative
  rates; (ii) Context validity signals — λ_c feedback (was context within
  effective half-life at decision time), driving λ_c adjustments and
  freshness-budget recalibration; (iii) Audit/lineage signals — meta-signals
  separating context failure (incomplete/stale/inconsistent context →
  graph-level updates) from model failure (correct context, poor reasoning →
  model-level intervention outside Control Plane scope). Exactly one
  handler processes any given evidence event; each handler's graph-write
  target is structurally distinct (outcome edge with decision-class
  attribution; correction edge with pre/post-decision state; metadata
  refinement to P and Π dimensions). Every category writes to graph state,
  never to weights.
- **Type signature:** none given (routing semantics rendered in
  Fig-CH07-24's alt/else branches).
- **Invariants:** One-event-one-handler routing; graph-write targets
  structurally distinct per category; no gradient descent, no model
  parameter update, no retrained checkpoint in the CCF loop.
- **Dependencies:** INV-CH7-75 (write-back channel); λ_c entries (§7.7).
  Governance D-46 (three categories). Note: Fig-CH07-24 names the handlers
  Outcome / Correction / Metadata while §7.9.2 prose names the categories
  outcome / context-validity / audit-lineage — informational naming
  divergence within the whitepaper itself.
- **Figure refs:** Fig-CH07-24 (signal categorization; load-bearing —
  three-category routing as graph-level, not gradient-descent, operation).
- **Open question (D-IMPL-42):** The categorization mechanism's
  naming differs between prose ("Outcome signals… Context validity
  signals… Audit/lineage signals") and figure caption ("Outcome Signal
  Handler… Correction Signal Handler… Metadata Signal Handler") — the SDK
  must pick one canonical taxonomy for the learning-signal type; synthesis
  should log this for design.

### INV-CH7-77 — Four refinement targets; "the loop is in the graph, not the model"

- **Whitepaper section:** §7.9.3
- **Commitment (paraphrase):** The three signal categories drive updates to
  exactly four Control-Plane-owned refinement targets: (1) Operator
  refinement (traversal depth, similarity thresholds, temporal boundaries);
  (2) Projection optimization (which signals are primary, subordinated,
  emphasized, compressed per principal view); (3) Policy calibration
  (detection thresholds, exposure limits, D_c class thresholds, entitlement
  boundaries); (4) Half-life adjustment (λ_c and freshness budgets per
  observation type). Canonical statement captured verbatim: "Agents appear
  to improve in production without retraining because the context they
  consume is improving." And: "The loop is in the graph, not the model."
  The model-retraining and prompt-refinement paradigms are explicitly
  orthogonal — the fabric does not prevent or replace them; the CCF's own
  loop operates at the graph and policy layer, so improvements compound
  across decision classes, are auditable at the Control Plane, and do not
  couple governance to any model's lifecycle.
- **Type signature:** none given (four target classes enumerated).
- **Invariants:** Refinement operates only on the four Control-Plane-owned
  targets; improvement lives in the context substrate, never in weights or
  prompts within the CCF loop.
- **Dependencies:** INV-CH7-75/76; operator parameters (§7.4), projection
  weighting (§7.5), policy/D_c thresholds (§7.7/§7.8.3), λ_c (§7.7).
  Governance D-47. External validation cited: Agentic Context Engineering
  (arXiv:2510.04618) — cited by the whitepaper as convergent evidence, with
  the CCF's distinction being the governed Control Plane surface.
- **Figure refs:** none directly (Fig-CH07-25 renders the full cycle —
  see INV-CH7-78).
- **Open question:** none.

### INV-CH7-78 — Learning as governance, not around it

- **Whitepaper section:** §7.9.4, §7.9.5
- **Commitment (paraphrase):** Learning strengthens governance rather than
  bypassing it: every closed-loop Control Plane update is versioned and
  auditable under the same discipline as any policy definition, and the
  improvement history is itself part of the audit trail. Three committed
  consequences: (1) consistency — an update propagates to every decision
  class consuming the configuration surface (Control Plane as single source
  of truth; asymmetry only by explicit commitment); (2) versioned
  auditability — "why was this threshold set at this value on the day of
  the decision" is answerable with update version, outcome-signal analysis,
  and approval workflow; (3) controlled evolution — approval workflows,
  staged propagation, and rollback apply to closed-loop updates exactly as
  to initial definitions. §7.9.5's fraud-detection worked example
  instantiates the full cycle (replay reconstruction → three contributing
  factors → three versioned Control Plane updates: λ_c 60→20 min,
  projection signal elevation, TTL 30→5 min), and notes the mechanism is
  invariant across decision classes — only the outcome signal's own λ_c and
  the statistical-significance threshold differ.
- **Type signature:** none given.
- **Invariants:** Closed-loop updates run through the same governance regime
  (versioning, approval, staged propagation, rollback) as initial
  configuration; no separate learning regime exists.
- **Dependencies:** INV-CH7-71 (audit plane), INV-CH7-75..77; §7.10 replay
  (reconstruction step of the cycle). Governance D-48
  (learning-as-governance).
- **Figure refs:** Fig-CH07-25 (closed-loop feedback cycle; supplementary —
  mechanism fully specified in prose per the whitepaper's own note).
- **Open question:** none.

### INV-CH7-79 — Decision Replay: forensic reconstruction as first-class commitment

- **Whitepaper section:** §7.10 (intro)
- **Commitment (paraphrase):** Every decision the fabric participates in is
  forensically reconstructible, years after the fact, against the exact
  state of the fabric at the moment of the decision — enforced at the
  moment of assembly, at the boundary of every Context Product, and at the
  Control Plane / Data Plane interface, not bolted on as post-hoc
  observability. §7.10 commits: the five-dimension record, environment
  replay (distinct from model trace), Anthropic Citations as the
  passage-level lineage component primitive, the Evidence Chain
  (Fig-CH07-28), three-tier compression with severity exemption, the AML
  SAR triage worked example, and three-audiences/three-renderings.
- **Type signature:** none given (chapter-level commitment; mechanism in
  the entries below).
- **Invariants:** Replay-readiness enforced at write time (assembly), not
  retrofitted.
- **Dependencies:** INV-CH7-74 (Data Plane determinism is the foundation);
  INV-CH7-71 (audit plane); lineage strict equality (INV-CH7-73(c)).
- **Figure refs:** Fig-CH07-26, Fig-CH07-27, Fig-CH07-28 (detailed in the
  entries below).
- **Open question:** none.

### INV-CH7-80 — The five-dimension replay record (enumeration)

- **Whitepaper section:** §7.10.1
- **Commitment (paraphrase):** A decision is reconstructible only if five
  dimensions of state at decision time t can each be reproduced exactly —
  "drop any one and a class of audit question becomes unanswerable." The
  five dimensions, by name: (1) **Context Fabric Snapshot**; (2) **Policy
  Bindings Snapshot**; (3) **Model Version Record**; (4) **Perspective
  Conditioning**; (5) **Content Generation Path**. The dimensions are
  orthogonal (each answers a different audit-question class) and
  collectively exhaustive for decision reconstruction. All five are
  captured, versioned, and retained together, indexed by the decision's
  temporal boundary and decision class, and available through the replay
  interface at any future audit time. Retention is subject to three-tier
  compression (INV-CH7-88), "but the five-dimension structure itself is
  inviolate." Patent Claim 13 covers the record as reduced-to-practice.
- **Type signature:** none given (record structure enumerated; field-level
  contracts per dimension in INV-CH7-81..85).
- **Invariants:** Five-dimension structure inviolate; captured/versioned/
  retained together; indexed by temporal boundary + decision class.
- **Dependencies:** INV-CH7-74 (determinism), INV-CH7-71 (audit plane).
  Governance D-51 (five-dimension record). SDK-defined extensions
  (CLAUDE.md, not whitepaper commitments): HITL actions and workflow
  traces extend dimensions (2) and (4) per CLAUDE.md §8.2/§8.1; agent
  version, configuration, and skill-set in force extend dimension (4) per
  CLAUDE.md §6.2.
- **Figure refs:** Fig-CH07-26 (five input nodes → single indexed
  replay-record node → five audit-question classes; canonical visual for
  §7.10); Fig-CH07-27 (examiner re-trace sequence: five parallel reads
  reconciled into deterministic reproduction).
- **Open question (D-IMPL-44):** "made available through the
  replay interface at any future time the audit obligation requires" —
  snapshot storage strategy that makes replay tractable at year-scale is
  under-specified; interacts with D-IMPL-06 (snapshot management) and
  D-IMPL-26 (artifact addressing/versioning).

### INV-CH7-81 — Dimension 1: Context Fabric Snapshot

- **Whitepaper section:** §7.10.1 item (1)
- **Commitment (paraphrase):** The complete `G(E, R, T, P, Π, L)` at
  decision time — every entity the decision touched, every relation, the
  temporal binding active at t, the policy regime in force, the projection
  applied, and the lineage for every assertion. Answers "what did the agent
  know?" — the first examiner re-tracing question; dropping it breaks
  SR 11-7 model validation.
- **Type signature:** `G(E, R, T, P, Π, L)` substate at t.
- **Invariants:** Completeness over the decision's touched substate;
  snapshot immutable once written.
- **Dependencies:** Context Graph six-tuple (§7.3, slice A entries);
  INV-CH7-74 (deterministic re-read).
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Context Graph historical read).
- **Open question (D-IMPL-44):** Full-fidelity graph substate per
  decision at "millions of decisions each day" scale — the whitepaper
  defers cost to compression (§7.10.5) but leaves the snapshot substrate
  open; interacts with D-IMPL-06.

### INV-CH7-82 — Dimension 2: Policy Bindings Snapshot

- **Whitepaper section:** §7.10.1 item (2)
- **Commitment (paraphrase):** The version identifier and serialized
  parameters of all active policies at decision time: the regulatory policy
  bundle governing the decision, internal risk-threshold policies above
  regulatory floors, operator-behavior policies in force, and the
  projection and entitlement policies that shaped the Context Product.
  Answers "what rules applied?" — establishes governance compliance;
  dropping it breaks FinCEN examiner review.
- **Type signature:** version identifier + serialized parameters (shape not
  further formalized).
- **Invariants:** Snapshot binds the exact policy versions in force at t.
- **Dependencies:** INV-CH7-71/72 (Control Plane versioning is the source).
  SDK-defined extension (CLAUDE.md §8.2, not a whitepaper commitment):
  HITL actions (approver identity, time, Context Product seen, annotations)
  extend this dimension.
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Policy Store historical read).
- **Open question:** none.

### INV-CH7-83 — Dimension 3: Model Version Record

- **Whitepaper section:** §7.10.1 item (3)
- **Commitment (paraphrase):** Identifiers of every model the decision
  pipeline invoked: detection models producing risk signals, classification
  models producing typology matches, embedding models producing similarity
  scores, and the LLM model and version that reasoned over the assembled
  Context Product. Answers "what software reasoned?" — separates model
  failure from context failure; indispensable for SR 11-7 model-validation
  review; "none"/"N/A" for pure-algorithmic Mode 1 (§7.10.4).
- **Type signature:** model identifiers per pipeline stage; Mode 2 record
  refines to `model_version_string`
  (vendor + family + version + revision pin) per §7.10.4.
- **Invariants:** Every invoked model captured; version pinning sufficient
  for re-invocation at replay.
- **Dependencies:** INV-CH7-74 (randomness isolation: same model, same
  seed, same batch shape); INV-CH7-87 (per-mode record contents).
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Model Registry read).
- **Open question:** none.

### INV-CH7-84 — Dimension 4: Perspective Conditioning

- **Whitepaper section:** §7.10.1 item (4)
- **Commitment (paraphrase):** The agent identity, the role definition the
  agent executed under, the tools the agent had available, and the
  delegation chain that led to the agent being invoked for this decision.
  Answers "for whom, with what authority?" — establishes that the right
  principal acted under the right delegation.
- **Type signature:** none given (agent identity, role, tool inventory,
  delegation chain).
- **Invariants:** Delegation chain complete from originating principal to
  acting agent.
- **Dependencies:** Projection/perspective conditioning (§7.5, slice B).
  SDK-defined extensions (not whitepaper commitments): workflow execution
  traces (calling agent chain) extend this dimension per CLAUDE.md §8.1;
  agent version and skill-set in force extend it per CLAUDE.md §6.2.
- **Figure refs:** Fig-CH07-26; Fig-CH07-27 (Projection stage applies
  Dim 4).
- **Open question:** none.

### INV-CH7-85 — Dimension 5: Content Generation Path

- **Whitepaper section:** §7.10.1 item (5)
- **Commitment (paraphrase):** The input-data identifiers for every source
  that contributed, the reasoning trace the agent produced (for
  deterministic algorithmic decisions the trace is the operator/projection
  trace, not an LLM rationale), and the structured output produced.
  Answers "how did it get from input to output?" — source-to-conclusion
  traceability; dropping it breaks BCBS 239 data-lineage requirements.
- **Type signature:** none given (input identifiers + reasoning trace +
  structured output).
- **Invariants:** Trace covers input→output end to end; algorithmic-mode
  trace is the operator/projection trace by definition.
- **Dependencies:** Lineage strict equality (INV-CH7-73(c)); passage-level
  lineage (INV-CH7-86). SDK-defined extension (CLAUDE.md §8.1): workflow
  step sequences extend this dimension.
- **Figure refs:** Fig-CH07-26; Fig-CH07-27.
- **Open question:** none.

### INV-CH7-86 — Environment replay, not model trace

- **Whitepaper section:** §7.10.2
- **Commitment (paraphrase):** "LLM observability captures the model's
  trace; CCF reconstructs the decision environment." The model trace
  (LangSmith / W&B Weave: prompt, intermediate reasoning, token outputs,
  tool invocations, latency) is silent on the fabric's side — the exact
  Context Product consumed, entitlement boundaries, temporal binding,
  policy bindings, λ_c configuration, projection applied. Given the
  environment (CCF) plus the model's own trace (captured by a separate
  tool), reconstruction is deterministic, bit-for-bit, on the Data Plane
  determinism foundation. The two layers are complementary; the model
  trace is necessary but not sufficient; the environment replay is the
  sufficient condition the CCF contributes. Named regulatory obligations
  satisfied by the composition: SR 11-7 post-hoc independent validation,
  OCC model-risk-management reconstruction, FinCEN examiner re-tracing.
- **Type signature:** none given.
- **Invariants:** Environment reconstruction deterministic (bit-for-bit)
  from the five-dimension record; model trace explicitly out of CCF scope.
- **Dependencies:** INV-CH7-74, INV-CH7-80. Governance D-52 (environment
  replay vs model trace).
- **Figure refs:** Fig-CH07-27 (bit-for-bit reassembly Note-over).
- **Open question:** none.

### INV-CH7-87 — Passage-level Lineage via the Anthropic Citations API

- **Whitepaper section:** §7.10.3
- **Commitment (paraphrase):** The L dimension must extend to the passage
  level for unstructured content: an unstructured claim must be traceable
  to the specific passage (document, passage, and where applicable
  page/bounding-box), not the document as a whole. The CCF builds on the
  Anthropic Citations API (GA January 2025) as "the canonical component
  primitive on which CCF's passage-level Lineage L for unstructured content
  builds": passage-level references produced at inference time as part of
  generation are persisted as Lineage entries attached to each claim in the
  Context Product. The Evidence Chain — Context Product claim →
  passage-level Lineage → Citations source reference → specific
  passage/page/bounding-box in the WORM/durable source — is the forward
  chain; the audit direction re-traces it in reverse. Explicitly
  decoupled: "Anthropic Citations is a component primitive the CCF uses,
  not a feature the CCF is" — the architectural commitment is that
  passage-level Lineage is a first-class L field populated by whatever
  component primitive the deployment selects and persisted in the replay
  record.
- **Type signature:** citation reference = (source document, passage,
  page/bounding-box where applicable).
- **Invariants:** Every unstructured-derived claim carries passage-level
  Lineage; Evidence Chain reconstructible at audit time; primitive is
  pluggable (not Anthropic-coupled).
- **Dependencies:** L dimension (§7.3); INV-CH7-85 (Dim 5); XC-05
  unstructured-as-first-class commitment (§7.3/§7.4, slices A/B).
  Governance D-53 (Citations API as component primitive). Interacts with
  D-IMPL-09 (LLM access for semantic stages / Citations API).
- **Figure refs:** Fig-CH07-28 (Evidence Chain; load-bearing — the XC-05
  commitment carried through to the audit surface).
- **Open question:** none.

### INV-CH7-88 — Replay across assembly modes (Modes 1/2/3 record contents)

- **Whitepaper section:** §7.10.4
- **Commitment (paraphrase):** The five-dimension record is the canonical
  Mode 1 artifact and the baseline Modes 2 and 3 extend without modifying.
  Mode 1: the five dimensions exactly, model version "none"/"N/A", content
  path = operator/projection trace. Mode 2 adds four LLM-rendering
  primitives: `model_version_string`, `temperature_float`,
  `full_prompt_text_or_hash` (inline or content-addressed hash with body in
  the WORM tier), `llm_output_hash`; the algorithmic substrate hash anchors
  the artifact-of-record. Mode 3 adds three orchestration primitives:
  `orchestration_plan_id` (content-addressed), `per_agent_version_manifest`
  (agent identity, framework version, prompt version, tool inventory), and
  `per_agent_contribution_boundary_markers`; per-agent contributions are
  themselves Mode 1/2/3 records (recursive composition). Compression and
  severity exemption operate on every per-mode record without distinction —
  replay is mode-invariant on one record format.
- **Type signature:** the Mode 2/3 field names above are given verbatim in
  the whitepaper.
- **Invariants:** Modes extend, never modify, the five-dimension baseline;
  recursive composition of per-agent records; mode-invariant replay
  infrastructure.
- **Dependencies:** §7.6 assembly modes and D-15/D-16 (slice B);
  INV-CH7-80, INV-CH7-89.
- **Figure refs:** none specific to this H3.
- **Open question:** none.

### INV-CH7-89 — Three-tier compression with severity exemption

- **Whitepaper section:** §7.10.5
- **Commitment (paraphrase):** Retention cost over year/decade horizons is
  bounded by three tiers: Full fidelity (all fields of all five dimensions;
  configurable per-decision-class window, typically weeks–months);
  Compressed (essential metrics only — threat level, entity counts/ids,
  composite D_c, coverage percentage, summary statistics — with the graph
  substate reduced to a deterministic hash re-hydratable from the cold
  source archive); Tombstoned (metadata only — timestamp, threat level,
  cycle id, decision class; applied per regulatory retention minima). The
  severity exemption: instances at or above a configurable,
  decision-class-specific severity threshold are never compressed or
  tombstoned — "Significant decisions retain full fidelity permanently."
  Every compressed/tombstoned record carries a structural
  `retention-reason` field. In a reference implementation the compression
  is an architectural invariant: deterministic algorithm, CI-tested
  severity exemption, structural retention-reason — bypassing is not
  silent on either the cost or the audit side. Patent Claim 14 covers the
  primitive.
- **Type signature:** partial — tier field lists and `retention-reason`
  field named.
- **Invariants:** Severity exemption never compressible/tombstonable;
  deterministic compression; retention-reason structural; five-dimension
  structure inviolate under compression (INV-CH7-80).
- **Dependencies:** INV-CH7-80; D_c (§7.7). Governance D-54 (implied by
  sequence D-51..D-56; three-tier compression). Severity thresholds and
  retention windows are Control Plane configuration (domain values, not
  SDK content).
- **Figure refs:** none.
- **Open question (D-IMPL-44):** "The graph substate itself is
  reduced to a deterministic hash of the five-dimension record, so that
  the exact substate can be re-hydrated if ever needed from a
  source-record archive" — the cold-archive substrate and re-hydration
  contract are unspecified; interacts with D-IMPL-06 and D-IMPL-27
  (substrate split).

### INV-CH7-90 — AML SAR triage worked example (replay end-to-end)

- **Whitepaper section:** §7.10.6
- **Commitment (paraphrase):** The canonical worked example composing the
  five-dimension record, Evidence Chain, and compression policy: an
  investigator's SAR filing decision captures all five dimensions
  (including passage-level Lineage for Bloomberg IB chat, wire narrative,
  and adverse-media passages via Anthropic Citations); years later an OCC
  examiner re-traces the Evidence Chain of Fig-CH07-28 in reverse for
  every narrative claim. The SAR filing is severity-exempt (Full fidelity
  permanently); routine non-filing typology-match cycles take the
  compressed/tombstoned tiers. Resolves the §7.6 D-30 anticipation via
  D-55; anchor example for the XC-05 load-bearing commitment.
- **Type signature:** none (worked example).
- **Invariants:** Defensibility is exactly coextensive with every claim
  having a traceable Evidence Chain.
- **Dependencies:** INV-CH7-80..89; §7.6 D-30 (slice B); Chapter 8 §8.9
  carries the regulatory payoff. Governance D-55.
- **Figure refs:** Fig-CH07-27 (re-trace sequence), Fig-CH07-28 (Evidence
  Chain).
- **Open question:** none.

### INV-CH7-91 — Three audiences, three renderings

- **Whitepaper section:** §7.10.7
- **Commitment (paraphrase):** The same underlying replay record serves
  three audiences through three renderings that are "three Projections of
  the same record," not three separate records: auditors/examiners get the
  Full-fidelity five-dimension trace with passage-level Evidence Chain;
  risk-and-compliance get a policy-adherence rendering emphasizing the
  Policy Bindings Snapshot, D_c/severity summaries, and Perspective
  Conditioning; management gets an executive pattern-detection summary
  aggregated over the record corpus. Mechanism: the recursive application
  of the §7.5 Projection primitive Π at the replay layer — audit-time
  consumption inherits the same principal-conditioning, entitlement, and
  role-shaped semantics as runtime consumption. "One primitive,
  recursively applied, serves every consumption surface."
- **Type signature:** none given (Π applied to the replay record).
- **Invariants:** One record, three projections — never three records;
  replay rendering reuses the Projection primitive, no separate mechanism.
- **Dependencies:** Projection Π (§7.5, slice B); INV-CH7-80.
  Governance D-56 (three audiences / three renderings).
- **Figure refs:** Fig-CH07-27 (alt/else audience branches).
- **Open question:** none.

---


---

## Chapter 8 — Enterprise Integration

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
- **Open question (D-IMPL-38):** "Where the whitepaper specifies the deduplication confidence threshold as Control-Plane-governed but gives no threshold schema or defaulting rule, the SDK must decide the Control Plane parameter shape for operator thresholds." (unnumbered; synthesis task assigns any D-IMPL number).

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
- **Open question (D-IMPL-47):** "The extended form D_c = 1 − (F · C · S) is given without specification of how F, C, and S are individually computed or weighted; the SDK must commit a computable definition per factor." (unnumbered; synthesis assigns numbering).

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
- **Open question (D-IMPL-48):** "The composite scoring function combining the five behavioral axes with VLM/LLM reasoning outputs is not specified — axis weights, fusion function, and score semantics are open for design." (unnumbered; synthesis assigns numbering).

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


---

## Governance Decisions (D-NN)

Every governance decision (D-NN) the whitepaper makes that the SDK must honor, per CLAUDE.md §16. Sweep method: exhaustive `D-[0-9]` grep of `docs/CCF_Whitepaper_1-2.md` with per-hit context reads, plus visual inspection of extracted figure images (`docs/figures/`) for decision boxes/tables the text extraction might have dropped (Fig-CH05-01, Fig-CH06-01, Fig-CH07-04, Fig-CH07-13, Fig-CH07-21, Fig-CH07-26, Fig-CH08-01 checked; no D-NN content appears in figures).

**41 unique D-NN entries found. Verified range D-05..D-56, non-contiguous.**

| D-NN | Name | Whitepaper section | Committed mechanism |
|------|------|--------------------|---------------------|
| D-05 | Mode 1 replay exemplar (AML alert triage) | §7.10.4 (cited as "Phase 12 D-05") | Pure-algorithmic product's replay record: five dimensions exactly, model version "N/A" (INV-CH7-88) |
| D-06 | Mode 2 replay exemplar (credit-memo narrative packaging) | §7.10.4 (cited as "Phase 12 D-06") | Algorithmic substrate as artifact-of-record + four pinned LLM-rendering primitives (INV-CH7-88) |
| D-07 | Mode 3 replay exemplar (syndicated covenant cross-reference) | §7.10.4 (cited as "Phase 12 D-07") | Orchestration-layer determinism boundary; recursive per-agent records (INV-CH7-88) |
| D-10 | Bitemporal validity-as-state as a contract-element-level commitment | §6.1 contract-test table (cited as "Phase 12 D-10") | T carried at the §6.3-element level, not as substrate refresh cadence (INV-CH6-01/03) |
| D-11 | Context Graph as first-class persisted computational primitive | §7.3.1, §7.3.5 | Persisted typed graph with its own invariants/write path/lifecycle (INV-CH7-15, INV-CH7-21) |
| D-13 | Regulatory large-exposure regime binding in policy scope | §7.3.4, §7.4.6 | P carries applicable regulatory regime bindings at subgraph resolution (INV-CH7-20, INV-CH7-30(d)) |
| D-14 | Algebraic operator composition | §7.4 | `ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity` (INV-CH7-23) |
| D-15 | Operator Plan DAG generator — AND (second use) Per-Mode Replay Footprint | §7.4.2; §7.6.8 (via §7.10.4) | Runtime intent→operator-plan generation (INV-CH7-28); per-mode replay footprint (INV-CH7-56). **Informational: the whitepaper reuses D-15 for two distinct commitments — an internal numbering collision, recorded here, both commitments inventoried.** |
| D-16 | Five Disciplines for Mixed-Mode Assembly | §7.6.9 (via §7.10.4) | Artifact-of-record, pinning, smoothing watchpoint, cost internalization, failure-mode inventory (INV-CH7-56) |
| D-17 | Operator composition determinism | §7.4.7 | Function-determinism with permitted value-variance; bit-for-bit reconstruction tuple (INV-CH7-31) |
| D-18 | Consolidated Rebuttal #11 + #13 answer | §7.4 | Policy-before-Similarity structural prevention; project-then-retrieve (INV-CH7-26) |
| D-19 | Π performs subgraph substitution, not subgraph filter | §7.5 | Projection output is a valid Context Graph for the principal (INV-CH7-40) |
| D-20 | ProjectionPlan Protocol as two-method structural interface | §7.5.1 | `required_operators()` + `invoke()`, structural typing dispatch (INV-CH7-41) |
| D-21 | Lineage source-neutrality | §8.5 (referenced from §8.1) | L records source identity, not source location — migration-proof (INV-CH8-01, INV-CH8-13) |
| D-22 | Role-shaped views from one shared graph | §7.5.3 (extended §8.9) | Same resolved context, structurally different products per Π, zero state duplication (INV-CH7-43, INV-CH8-20) |
| D-23 | Runtime conditioning | §7.5.4 | Projection resolved at request time by (role, intent, temporal context, policy); avoids precompute-everything (INV-CH7-43) |
| D-25 | ContextProductContract base with extra=forbid | §7.6.1 | Seven-field typed base; forbid-extra CI invariant (INV-CH7-45, INV-CH7-33) |
| D-27 | Materialization policy with conditional write | §7.6.3 | Three-signal per-class materialization decision; cache coherency state machine (INV-CH7-51) |
| D-28 | Per-class cost envelope | §7.6.5 | Four illustrative cost multiple bands ×1/×3–5/×2–4/×8–15 (INV-CH7-53) |
| D-30 | SAR-triage replay anticipation | §7.6 (anticipation; resolved by D-55 at §7.10.6) | Worked replay example anticipated at delivery layer, resolved at replay layer (INV-CH7-90) |
| D-31 | λ_c formula as configuration | §7.7.1–§7.7.2 | `R(t) = R₀ × (1/2)^((t − t₀) / λ_c)`; per-observation-type values in Control Plane config (INV-CH7-57/58) |
| D-33 | Supersession as Policy event | §7.7.3 | Logical supersession (`superseded_by` + `superseded_at`); Control-Plane-versioned invalidation; lazy re-derivation (INV-CH7-60, INV-CH7-21) |
| D-34 | D_c formulas | §7.7.4 | Basic `D_c = 1 − (C_available / C_required)`; extended `D_c = 1 − (F · C · S)` (INV-CH7-61/62) |
| D-35 | Three debt components | §7.7.6 | Source-availability, as-of-staleness, entity-resolution-confidence debt with runtime signals (INV-CH7-64) |
| D-37 | Trust Triangle debt-mapping | §7.7.8 | Structural mapping of the three debt components onto the §6.6 Trust Triangle legs (INV-CH7-66) |
| D-38 | Conservative fail-closed bias | §7.7.9 | Elevated D_c biases urgency upward; fail-closed default; uncertainty routed, never smoothed (INV-CH7-67) |
| D-39 | Debt cascade across agent handoff | §7.7.10–§7.7.11 | D_c recomputed at every handoff; per-claim debt decomposition (INV-CH7-68) |
| D-40 | Service-mesh Control/Data Plane ancestry | §7.8 | Istio/Envoy-pattern plane separation with CCF-specific cargo (INV-CH7-70) |
| D-41 | Control-plane-is-audit-plane | §7.8.2 | Every runtime decision auditable against exact rule-state in force; versioned policy events (INV-CH7-71) |
| D-42 | Configuration surface enumeration | §7.8.3 | Six versioned configuration classes (policy, operator rules, projection logic, D_c, λ_c, materialization) (INV-CH7-72) |
| D-44 | Data Plane determinism | §7.8.5 | Bit-for-bit identical product under fixed (graph state, config, temporal boundary) (INV-CH7-74) |
| D-45 | Closed-loop write-back pseudocode | §7.9.1 | `processOutcomeSignal(...) -> ControlPlaneUpdate`; typed OutcomeSignal with own λ_c (INV-CH7-75) |
| D-46 | Three learning-signal categories | §7.9.2 | Outcome / context-validity / audit-lineage signals, one-event-one-handler (INV-CH7-76) |
| D-47 | Loop-is-in-the-graph | §7.9.3 | Four Control-Plane-owned refinement targets; no model retraining in the CCF loop (INV-CH7-77) |
| D-48 | Learning-as-governance | §7.9.4–§7.9.5 | Closed-loop updates under the same versioning/approval/rollback regime as initial config (INV-CH7-78) |
| D-51 | Five-dimension replay record | §7.10.1 | Fabric Snapshot, Policy Bindings, Model Version, Perspective Conditioning, Content Generation Path — structure inviolate (INV-CH7-80) |
| D-52 | Environment replay vs model trace | §7.10.2 | CCF reconstructs the decision environment; model trace explicitly out of scope (INV-CH7-86) |
| D-53 | Anthropic Citations API as passage-level L component primitive | §7.10.3 | Passage-level Lineage populated by a pluggable citation primitive; Evidence Chain (INV-CH7-87) |
| D-54 | Three-tier compression with severity exemption | §7.10.5 | Full fidelity / Compressed / Tombstoned; severity-exempt decisions retained permanently (INV-CH7-89) |
| D-55 | AML SAR triage worked replay example | §7.10.6 | End-to-end composition of record + Evidence Chain + compression policy (INV-CH7-90) |
| D-56 | Three audiences, three renderings | §7.10.7 | One record, three Π-projections; recursive application of the §7.5 primitive (INV-CH7-91) |

**Gap numbers — not found in whitepaper** (verified against text sweep and visual figure check): D-01, D-02, D-03, D-04, D-08, D-09, D-12, D-24, D-26, D-29, D-32, D-36, D-43, D-49, D-50.

Disambiguated false positives: "locked D-01"/"D-02/D-03"/"D-04" in the converter preamble are this project's *conversion* decisions (Phase R history), not whitepaper governance decisions; "Phase 12 D-05/06/07/10" is the whitepaper's own project-history phrasing but each points at a genuine inventoried commitment (rows above); "D1–D5" in Fig-CH07-26 are timeline day markers, not decision identifiers.

---

## Load-Bearing Figures

All 50 figures (`Fig-CHNN-MM`), per CLAUDE.md §16, with the mechanism each commits. Captions abbreviated from the `.md` placeholders (visually reconstructed at conversion per locked D-04); mechanisms cross-checked against the inventory entries citing each figure.

| Figure | Caption (abbreviated) | Mechanism committed |
|--------|----------------------|---------------------|
| Fig-CH01-01 | Structural Fragmentation — LoB footprint vs disparate system categories | Motivating condition: estate heterogeneity as the operating state (grounds INV-CH8-01) |
| Fig-CH01-02 | The Forensic Data Gap | Evidence-trail / as-of / role-view / passage reconstruction as the missing capability (grounds INV-CH8-02) |
| Fig-CH01-03 | Client 360 — snapshot vs dynamic assembly | Aggregate-vs-assemble distinction; decision-time assembly posture |
| Fig-CH02-01 | Peer-Bank Agent Adoption Benchmark | Existence proof of agentic scale; no mechanism |
| Fig-CH02-02 | The Enterprise Agent Stack — five tiers | The fabric tier as the unnamed tier between document-understanding and the data estate; MCP/A2A as the open wire protocols |
| Fig-CH03-01 | Anatomy of an Agent — five capabilities | Context as one of five composing agent capabilities |
| Fig-CH03-02 | The Agent Execution Loop — eight stages | Context assembly as the critical inflection of the loop |
| Fig-CH03-03 | Multidimensional vs scalar context | Multi-dimension convergence per decision, each with freshness/policy/perspective annotations |
| Fig-CH03-04 | Context Debt Cascade | Compounding degradation across agent invocations (companion to Fig-CH07-20) |
| Fig-CH04-01 | Three Structural Choices of BI | HITL/snapshot/role-as-dashboard patterns breaking under agentic load |
| Fig-CH04-02 | The Structural Discontinuity | The missing context-construction layer between data representation and machine reasoning |
| Fig-CH05-01 | Six-tuple strictly extends (M, D, T, J) | P, Π, L as first-class formalism dimensions (INV-CH5-03/04) |
| Fig-CH05-02 | Three-tier architectural model | Cognition tier composed above Record and Signal tiers (INV-CH5-01/07/08) |
| Fig-CH06-01 | Context Product vs Data Product lifecycle | Persistent-vs-ephemeral posture; closing replay edge (INV-CH6-01) |
| Fig-CH06-02 | Eight-Step Context Product Lifecycle | Lifecycle loop with Step 8 → Step 1 feedback edge (INV-CH6-04) |
| Fig-CH06-03 | Context Trust Triangle | Conjunctive quality gate over Confidence/Freshness/Lineage-integrity legs (INV-CH6-08) |
| Fig-CH07-01 | Fabric as Persistent Institutional Memory | Closed-loop fabric posture; plane separation context (INV-CH7-01/08) |
| Fig-CH07-02 | L1–L6 Logical Architecture | Six responsibility layers; "Missing" annotation on L2/L3/L4 (INV-CH7-01..08) |
| Fig-CH07-03 | Six-Dimensional Decision Architecture | Every decision as the reconciled output of all six dimensions (INV-CH7-14) |
| Fig-CH07-04 | Logical six-tuple ↔ physical collection pattern | Per-dimension persistence surfaces; L resolved to Decision Replay records (INV-CH7-15..19) |
| Fig-CH07-05 | Graph mutation on supersession | Supersession sequence: prior claim retained, edge written, lineage accumulates, invalidation emitted (INV-CH7-21) |
| Fig-CH07-06 | Entity resolution across source systems | Fragmented identifiers converge to one canonical E node (INV-CH7-21) |
| Fig-CH07-07 | Context Operators — compositional algebra | Four categories composing into Π and the Context Product; typed read-only contracts (INV-CH7-22/23) |
| Fig-CH07-08 | Operator composition lifecycle | Intermediate caching, associativity preservation, replay reuse (INV-CH7-23, INV-CH7-31) |
| Fig-CH07-09 | Operator Plan DAG generator fan-out | Intent → four example compositions (design space, not one path) (INV-CH7-28..30) |
| Fig-CH07-10 | End-to-end assembly sequence | Intent → plan → four operators → Π → contract-validated cached product (INV-CH7-33; runtime enactment of D-14/D-15/D-17/D-25) |
| Fig-CH07-11 | Π — typed subgraph substitution vs RBAC filter | Substitution-not-filtering projection semantics (INV-CH7-40) |
| Fig-CH07-12 | Π runtime conditioning — three principals | Role-shaped products from one shared graph read (INV-CH7-40..43) |
| Fig-CH07-13 | Anatomy of a Context Product | Contract spec sidebar + eight-step assembly path; "agents never directly query lake tables" (INV-CH7-45) |
| Fig-CH07-14 | Cache coherency state machine | Fresh → Near-Expiry → Invalidated/expiry → Re-Derived lifecycle under λ_c and supersession (INV-CH7-51) |
| Fig-CH07-15 | Derivation paths (cache hit vs miss) | Keyed lookup, conditional cache write, p99 envelope (INV-CH7-52) |
| Fig-CH07-16 | Three sequential validation gates | Empty-operator guard, policy gate, lineage completeness — refusal before cache/delivery (INV-CH7-46..48, 52) |
| Fig-CH07-17 | Trust Triangle with Half-Life and Freshness Budget | λ_c decay composition against decision-class budgets (INV-CH7-57..59, 66) |
| Fig-CH07-18 | Supersession as a Policy event | Control Plane → Policy Store → λ_c Calibrator → Data Plane invalidation propagation (INV-CH7-60) |
| Fig-CH07-19 | Conditional Assessment Routing matrix | Skip / Conditional / Standard LLM / Forced LLM decision tree (INV-CH7-65) |
| Fig-CH07-20 | Debt cascade across agent handoff | D_c accumulation and fail-closed breach across A→B→C workflow (INV-CH7-68) |
| Fig-CH07-21 | Control Plane and Data Plane | Plane separation with CCF-specific cargo; invariant-enforcement boundary (INV-CH7-70/73) |
| Fig-CH07-22 | Control ⇄ Data Plane message exchange | Versioned audit entry; event-published invalidation (runtime enactment of D-40/41/42/44) (INV-CH7-71/72) |
| Fig-CH07-23 | Closed-loop graph write-back | Decision captured → evidence persisted → graph refined → next invocation reads improved state (INV-CH7-75) |
| Fig-CH07-24 | Learning signal categorization | One evidence event → one of three handlers → distinct graph-level refinement target (INV-CH7-76) |
| Fig-CH07-25 | Closed-loop feedback cycle | Outcome signals propagate as Control Plane updates (supplementary) (INV-CH7-78) |
| Fig-CH07-26 | Decision Replayability Architecture | Five input dimensions → single indexed record → audience renderings; "what did the agent know at 2:14 PM last Tuesday" test (INV-CH7-80) |
| Fig-CH07-27 | Decision Replay re-trace | Examiner query; five parallel reads reassembled bit-for-bit under audience projection (INV-CH7-80/86/90/91) |
| Fig-CH07-28 | Evidence Chain for Decision Replay | Claim → passage-level L → Citations reference → WORM source passage; XC-05 carried to audit surface (INV-CH7-87) |
| Fig-CH08-01 | Non-Invasive Integration Reference Architecture | Layering posture: legacy/mesh tiers unchanged; Patterns 1–5 as Perception ingress; algorithmic/semantic firewall; replay closes the loop (INV-CH8-03/04) |
| Fig-CH08-02 | Pattern 5 ingestion path (tiers 1–4) | Parser dispatch by data classification, chunking, embedding (INV-CH8-09/10) |
| Fig-CH08-03 | Pattern 5 retrieval/extraction/persistence path (tiers 5–7) | Policy-before-Similarity retrieval, typed extraction, passage-level L persistence (INV-CH8-09/10) |
| Fig-CH08-04 | Alternating Derivation Pipeline | Four-stage algorithmic ⇄ semantic alternation with distance-weighted deduplication and persist-into-G feedback (INV-CH8-12) |
| Fig-CH08-05 | 6D Context Graph — Wholesale Banking rendering | Illustrative domain lens; T/P/Π/L as projections over one E-R subgraph (supplementary) (INV-CH8-13) |
| Fig-CH08-06 | Conditional Assessment Routing decision tree | Bypass / Conditional / Forced Escalation governance rendering (supplementary) (INV-CH8-16) |

50/50 figures cataloged (CH01: 3, CH02: 2, CH03: 4, CH04: 2, CH05: 2, CH06: 3, CH07: 28, CH08: 6).

---

## Named Architectural Invariants

Per CLAUDE.md §16 — every named architectural invariant, with origin and the inventory entries realizing it.

| Invariant | Origin | Realizing inventory entries |
|-----------|--------|-----------------------------|
| Single-writer enforcement (only L2/Assembly writes L3; DI at boot) | Whitepaper §7.2, §7.3.1, §7.8.4(a); CLAUDE.md §10 (extends across A2A admission, harness effect capture, ArtifactStore) | INV-CH7-10, INV-CH7-15, INV-CH7-73; INV-CH8-05 (CDC writes only via Assembly) |
| Composition-preservation `(A∘B)(G) = A(B(G))` | Whitepaper §7.4.1, §7.2; CLAUDE.md §11 (tested per shipped operator pair) | INV-CH7-11, INV-CH7-23, INV-CH7-31, INV-CH7-33 |
| Three validation gates (empty-operator guard, lineage strict equality, TTL bounds) | Whitepaper §7.6.1, §7.6.4, §7.8.4(c)(d); CLAUDE.md §5 | INV-CH7-13, INV-CH7-46, INV-CH7-47, INV-CH7-48, INV-CH7-52 |
| Algorithmic ⇄ Semantic Alternation (LLMs never see raw signal) | Whitepaper §6.4, §7.6.6; CLAUDE.md §11 (`@algorithmic` CI lint) | INV-CH6-04, INV-CH7-54, INV-CH8-12 |
| Audit-by-construction (every HITL action, workflow trace, and skill event replay-recorded) | Whitepaper §7.8.2, §7.10 (record enforced at write time); CLAUDE.md §8.1, §8.2, §6.2 (HITL/workflow/skilling extensions — SDK-defined) | INV-CH7-71, INV-CH7-79, INV-CH7-80..85 |
| No-Hardcoding Rule (no inline prompts/definitions/values in code) | CLAUDE.md §6.4 (SDK-defined structural invariant); whitepaper hooks: λ_c/thresholds as Control Plane config (§7.7.2, §7.8.3) | INV-CH7-58, INV-CH7-59, INV-CH7-72 (config-surface posture); homecams-patterns appendix (CI-guard precedent row) |
| Zero harness imports in core | CLAUDE.md §1, §7.3, §11 (SDK-defined; CI import lint) | No whitepaper counterpart (the whitepaper does not ship an agent loop); attaches to the Ch 3 agents-as-consumers posture and INV-CH6-06 (MCP as access layer, fabric internals opaque to consumers) |

Additional whitepaper-named structural invariants inventoried (subsidiary to the seven above): tenant invariant / kw-only tenant scoping (INV-CH7-16, INV-CH7-73(e)); operator read-only purity (INV-CH7-11, INV-CH7-22); Policy-before-Similarity ordering (INV-CH7-26, INV-CH8-17); append-only-forward-with-supersession (INV-CH7-04, INV-CH7-21, INV-CH7-60); Similarity determinism contract (INV-CH7-27); boot-time registry fail-fast (INV-CH7-29); stateless projection (INV-CH7-73(b)); five-dimension record inviolate (INV-CH7-80); severity exemption (INV-CH7-89).

---

## SDK Extensions and Whitepaper Hooks

Every SDK extension CLAUDE.md commits to (per §16), labeled SDK-defined, with the whitepaper hook each attaches to.

| SDK extension (CLAUDE.md) | CLAUDE.md section | Whitepaper hook |
|---------------------------|-------------------|-----------------|
| Agent Specialization Framework with archetype/agent separation | §6, §6.1 | Ch 3 agents-as-consumers of the fabric; §6.5/§6.6 agent consumption discipline (INV-CH6-05/07: agents never self-assemble context) |
| Six Archetypes (`WorkflowAgent`/`TaskAgent`, `DocumentIntelligenceAgent`, `AnalyticsInsightsAgent`, `MonitoringSurveillanceAgent`, `ContentGenerationAgent`, `ContextAssemblyAgent`) | §6.3 | §7.4.9 swarm-realized operators and §6.6 recursive enrichment (ContextAssembly); §7.10.3 passage-anchored generation (ContentGeneration/DocumentIntelligence); §7.7 λ_c-driven re-evaluation (Monitoring); T-dimension analysis (Analytics) |
| Agent & Task Factory + No-Hardcoding Rule | §6.4 | §7.8.3 Control Plane configuration surface (INV-CH7-72 — agent/task/prompt/skill artifacts as additional Control Plane classes, SDK-defined) |
| Dual-channel specialization (specialization + skilling) with governance and replay capture | §6.2 | §7.10.1 dimension 4 Perspective Conditioning (INV-CH7-84 — agent version and skill-set in force extend it); §7.8.2 audit plane |
| Bidirectional MCP (client at L1/L4–L5/Experience; server at L6 and ArtifactStore) | §7.1 | §8.3 Pattern 3 export (INV-CH8-07 — whitepaper commits egress only); §6.5.1 MCP as access layer (INV-CH6-06); §6.6 search-inference content acquisition (INV-CH6-07) |
| A2A federation first-class in v0 (WireProtocol, identity/signing, admission verification) | §7.2 | §8.3 Pattern 4 (INV-CH8-08 — whitepaper commits the architectural surface; consumer-side Control Plane verification); §7.6.7 Mode 3 cross-organizational assembly (INV-CH7-55) |
| Harness Adapter surface (`HarnessAdapterProtocol`, four seams, zero-harness-imports lint) | §7.3 | Ch 2 §2.5 / Ch 3 (harness ecosystem exists outside the fabric); §6.5.1 access-layer boundary (INV-CH6-06); §7.10.1 replay hooks into dimensions 3–5 |
| ArtifactStore Protocol with MCP-backed reference implementation | §7.4 | §7.10.1/§7.10.5 replay record retention and snapshot tractability (INV-CH7-80, INV-CH7-89); §7.8.3 Control Plane bundle persistence (INV-CH7-72) |
| Orchestration Layer (Workflow primitive + OrchestrationProtocol) | §8.1 | §7.7.10 multi-agent handoff topology (INV-CH7-68); §7.10.1 dimensions 4/5 (workflow traces extend Perspective Conditioning and Content Generation Path) |
| HITL primitives (ApprovalGate, ExceptionEscalation, OverrideBoundary, ReviewQueue) with audit-by-construction | §8.2 | §7.7.9 fail-closed escalation routing (INV-CH7-67); §8.8 Supervision Quality complement (INV-CH8-19); §7.10.1 dimension 2 (HITL actions extend Policy Bindings Snapshot) |
| Experience Layer (MCP server, `ccf` CLI, HTTP API skeleton) | §8.3 | §6.5.1 MCP access surface (INV-CH6-06); §8.3 Pattern 3 (INV-CH8-07); Conversational Reporting Layer §8.10 explicitly out of v0 scope (INV-CH8-21) |

---

## Pillar-by-Pillar Mapping

For each of the five Common Pillars (CLAUDE.md §4), the inventory entries that contribute to it — the primary cross-reference for Phase D.

| Pillar | Contributing inventory entries |
|--------|-------------------------------|
| **Data and Context Layer** | Ch 5 all (INV-CH5-01..10); Ch 6 all (INV-CH6-01..08); Ch 7 fabric mechanism: INV-CH7-01..33 (layers, decomposition, graph, operators), INV-CH7-40..56 (projection, delivery), INV-CH7-57..68 (half-life, debt), INV-CH7-70..78 (planes, closed loop), INV-CH7-79..91 (replay); Ch 8 integration: INV-CH8-01..11 (patterns), INV-CH8-13/14 (graph lens, temporal layer), INV-CH8-20 (auditability at scale) |
| **Orchestration Layer** | INV-CH7-32 (swarm-realized operators), INV-CH7-55/56 (Mode 3 orchestration + replay footprint), INV-CH7-68 (debt cascade across handoff), INV-CH7-88 (Mode 3 record: orchestration plan ID, agent manifest); INV-CH8-08 (A2A federation as cross-org orchestration ingress). SDK-defined mechanism (Workflow primitive, OrchestrationProtocol) per CLAUDE.md §8.1 |
| **Core Agent Types** | INV-CH6-05 (agents consume context, not data), INV-CH6-07 (search-inference loop; assembly stays in architecture), INV-CH6-08 (trust-gated action), INV-CH7-32 (assembler-swarm archetype grounding), INV-CH7-84 (agent identity/role/tools/delegation in replay), INV-CH8-12/14/20/21 (the four archetypes of agentic work as functional templates). SDK-defined mechanism (archetypes, factory, skilling) per CLAUDE.md §6 |
| **Human in the Loop and Control** | INV-CH7-65 (Forced LLM / escalation routing), INV-CH7-67 (fail-closed, human-escalation paths), INV-CH7-68 (threshold-breach fail-closed routing), INV-CH7-71 (audit plane), INV-CH7-82 (HITL extension of Policy Bindings Snapshot), INV-CH8-16 (forced-escalation pathway), INV-CH8-18 (escalate-or-refuse), INV-CH8-19 (Supervision Quality). SDK-defined primitives per CLAUDE.md §8.2 |
| **Experience Layer** | INV-CH6-05 (Discoverable/Interoperable principles), INV-CH6-06 (MCP as the access layer; request path), INV-CH8-07 (MCP export surface), INV-CH7-91 (three audiences / three renderings as consumption surfaces), INV-CH8-21 (Conversational Reporting Layer — inventoried, out of v0 scope). SDK-defined surfaces (MCP server, CLI, HTTP API) per CLAUDE.md §8.3 |

---

## Subsection Coverage

All 36 target subsections of whitepaper Chapters 5–8 covered (Ch 5: 7, Ch 6: 6, Ch 7: 10, Ch 8: 13). Coverage proven by enumeration:

| Subsection | Covered by | ✓ |
|------------|-----------|---|
| §5.1 | INV-CH5-01, INV-CH5-02 | ✓ |
| §5.2 | INV-CH5-03, INV-CH5-04 | ✓ |
| §5.3 | INV-CH5-05 | ✓ |
| §5.4 | INV-CH5-06 | ✓ |
| §5.5 | INV-CH5-08 | ✓ |
| §5.6 | INV-CH5-07 | ✓ |
| §5.7 (incl. §5.7.1) | INV-CH5-09, INV-CH5-10 | ✓ |
| §6.1 | INV-CH6-01 | ✓ |
| §6.2 | INV-CH6-02 | ✓ |
| §6.3 | INV-CH6-03 | ✓ |
| §6.4 | INV-CH6-04 | ✓ |
| §6.5 (incl. §6.5.1) | INV-CH6-05, INV-CH6-06 | ✓ |
| §6.6 (incl. §6.6.1–§6.6.4) | INV-CH6-07, INV-CH6-08 | ✓ |
| §7.1 | INV-CH7-01..08 | ✓ |
| §7.2 | INV-CH7-09..13 | ✓ |
| §7.3 | INV-CH7-14..21 | ✓ |
| §7.4 | INV-CH7-22..33 | ✓ |
| §7.5 | INV-CH7-40..44 | ✓ |
| §7.6 | INV-CH7-45..56 | ✓ |
| §7.7 | INV-CH7-57..68 | ✓ |
| §7.8 | INV-CH7-70..74 | ✓ |
| §7.9 | INV-CH7-75..78 | ✓ |
| §7.10 | INV-CH7-79..91 | ✓ |
| §8.1 | INV-CH8-01, INV-CH8-02 | ✓ |
| §8.2 | INV-CH8-03 | ✓ |
| §8.3 (incl. §8.3.1, §8.3.2) | INV-CH8-04..11 | ✓ |
| §8.4 | INV-CH8-12 | ✓ |
| §8.5 | INV-CH8-13 | ✓ |
| §8.6 | INV-CH8-14 | ✓ |
| §8.7 (incl. §8.7.1–§8.7.3) | INV-CH8-15..18 | ✓ |
| §8.8 | INV-CH8-19 | ✓ |
| §8.9 | INV-CH8-20 | ✓ |
| §8.10 | INV-CH8-21 | ✓ |
| §8.11 | INV-CH8-22 | ✓ |
| §8.12 | INV-CH8-23 | ✓ |
| §8.13 | INV-CH8-24 | ✓ |

36/36 subsections covered.

---

## Open Questions for Phase D

Every open question Phase D must resolve, per CLAUDE.md §16. Full entries live in `docs/DECISIONS.md`; inventory entries cross-reference them in their Open-question fields.

- **From CLAUDE.md §12 (pre-existing scaffolding):** D-IMPL-01 through D-IMPL-29 — canonical home is CLAUDE.md §12; D-IMPL-10 provisionally resolved (monorepo). The §12 Phase I gate list (D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28) stands.
- **New from Phase R extraction (assigned at synthesis, 2026-07-25):**
  - D-IMPL-30 — Contract element count, eight vs nine (§6.3; INV-CH6-03)
  - D-IMPL-31 — TTL granularity, per-signal vs per-product (§6.4; INV-CH6-04)
  - D-IMPL-32 — Trust Triangle scoring mechanics (§6.6.3; INV-CH6-08)
  - D-IMPL-33 — Canonical L1 event envelope schema (§7.1; INV-CH7-02)
  - D-IMPL-34 — Graph-storage Protocol requirement surface (§7.3.1; INV-CH7-15)
  - D-IMPL-35 — Entity Resolver contract (§7.3.5; INV-CH7-21)
  - D-IMPL-36 — Operator-plan intermediate scheduling/materialization (§7.4.2; INV-CH7-28)
  - D-IMPL-37 — Operator registry population surface (§7.4.2; INV-CH7-29)
  - D-IMPL-38 — Control Plane parameter schema for operator thresholds (§7.4.3/§7.4.6/§8.4; INV-CH7-24, INV-CH8-12)
  - D-IMPL-39 — MAX_TTL configuration locus (§7.6.1/§7.6.4; INV-CH7-48)
  - D-IMPL-40 — CAR threat-level scale and class D_c thresholds (§7.7.7; INV-CH7-65)
  - D-IMPL-41 — Build-time single-writer enforcement substrate (§7.8.4; INV-CH7-73)
  - D-IMPL-42 — Learning-signal taxonomy naming (§7.9.2; INV-CH7-76)
  - D-IMPL-43 — Closed-loop interpretation step, automated vs human-gated (§7.9.1; INV-CH7-75)
  - D-IMPL-44 — Cold-archive re-hydration contract (§7.10.1/§7.10.5; INV-CH7-80/81/89)
  - D-IMPL-45 — Model-trace composition seam (§7.10.2; INV-CH7-86)
  - D-IMPL-46 — Passage-citation provider Protocol (§7.10.3; INV-CH7-87)
  - D-IMPL-47 — Computable F/C/S debt-factor definitions (§7.7.4/§8.7.1; INV-CH7-62, INV-CH8-16)
  - D-IMPL-48 — Supervision Quality scoring and SDK-scope disposition (§8.8; INV-CH8-19)
  - D-IMPL-49 — Projection-plan selection signature (§7.5 silence; homecams-patterns)
  - D-IMPL-50 — Replay fidelity-lifecycle: SDK-shipped or ArtifactStore-delegated (§7.10.5; homecams-patterns)
  - D-IMPL-51 — Live MongoDB metadata query approval (CLAUDE.md §2.1; homecams-patterns)
- **Stated non-commitment (not a gap):** per-domain λ_c calibration methodology is explicitly withheld by the whitepaper as trade-secret (INV-CH8-11).

---

## Appendix: homecams-patterns

Read-only pattern review of `/home/parkave/homecams_v2` per CCF CLAUDE.md §2.1 discipline.
Every pattern is a **triangulation data point, never a canonical answer**. Where the
whitepaper and Homecams disagree, the whitepaper wins. No code is ported; rows cite
source paths only.

Marker vocabulary (exactly two values): `candidate pattern` | `domain-specific — do not inherit`.

Homecams `/home/parkave/homecams_v2/CLAUDE.md` (829 lines) was read exactly once, as
additive best-practices context only, per CCF CLAUDE.md §2 — nothing from it overrides
this project's own CLAUDE.md.

## Pattern Table

| Pattern | Source (Homecams path) | Marker | Notes |
|---------|------------------------|--------|-------|
| Framework/domain package split — domain-agnostic primitives in one package, domain subclasses in another | `packages/si-framework/` vs `packages/si-pool-safety/` | candidate pattern | Homecams' `si-framework`/`si-pool-safety` line is the same boundary CCF SDK draws between `/src` mechanism and user configuration; Homecams enforces it by package, the SDK will enforce it by artifact (§6.4). |
| Context Graph as persisted typed model, enrich-only (downstream stages enrich, never rebuild) | `packages/si-framework/src/si_framework/models/context_graph.py` (`ContextGraphNode`); domain subclass `packages/si-pool-safety/src/si_pool_safety/models/pool_context_graph.py` | candidate pattern | Matches whitepaper append-only-with-supersession posture; Homecams realizes "accumulate, never reconstruct" as an architectural constraint. |
| Operator vs Projection separation — operators construct truth + load-bearing metadata; projections interpret truth for a consumer | `packages/si-framework/src/si_framework/services/operator_resolver.py`, `projection_engine.py`, `contracts/projection.py` | candidate pattern | Homecams' formalized v5.0 split (operators → resolved context + metadata → ProjectionExecutionEngine) is one working resolution of whitepaper §7.4/§7.5 two-stage execution. |
| Projection contract shape: `ProjectionPlan` Protocol + `ContextProductContract` + `ProjectionLineage` + `OperatorRef` | `packages/si-framework/src/si_framework/contracts/projection.py` | candidate pattern | Protocol-based structural typing consistent with whitepaper §7.5 `required_operators()`/`invoke()`; concrete shape is a data point for SDK design. |
| Projection derived from (agent role, decision intent, product contract) triple | `packages/si-framework/src/si_framework/services/projection_engine.py`, projection registry `projection_registry.py` | candidate pattern | A resolution of how Π role-conditioning selects a projection plan; whitepaper specifies Π mechanism, not the plan-selection inputs. |
| Context Products as terminal delivery interface — agents never query the graph, never run operators | `packages/si-framework/src/si_framework/models/context_product.py` (`ContextProductBundle`); call site `packages/si-pool-safety/src/si_pool_safety/tools/guardian_tools.py` | candidate pattern | Directly validates whitepaper §6.3/§7.6 delivery posture (existence proof). |
| Materialized projection-output cache with TTL index, distinct from graph state | `packages/si-framework/src/si_framework/repositories/projection_cache_repository.py` | candidate pattern | TTL-governed cache of projection outputs (whitepaper is silent on materialization/caching of intermediates) — data point for operator-DAG intermediate handling; see Open Questions. |
| Context Half-Life as first-class state + service | `packages/si-framework/src/si_framework/models/context_primitives.py` (`ContextHalfLifeState`), `services/context_half_life_service.py` | candidate pattern | Mechanism shape (per-observation-type decay state + service) is inheritable; the λ_c *values* are not (see below). |
| Property-intelligence λ_c values and per-observation-type half-life tables | `config/policy.yaml` (`ContextHalfLifePolicy` in `si_framework/models/policy.py`) | domain-specific — do not inherit | Domain calibration; CCF CLAUDE.md §13 "not the SDK's problem at all". |
| Context Debt as decomposed components with conservative bias (debt biases urgency upward) | `packages/si-framework/src/si_framework/models/context_primitives.py` (`ContextDebt`, `CoverageDebtComponent`), `services/context_debt_service.py` | candidate pattern | Component decomposition and the incomplete-information-as-risk-amplifier stance are data points for whitepaper §7.7.4–§7.7.8 D_c gating (Forced LLM / Fail-Closed). |
| Camera/temporal/identity debt component taxonomy | `si_framework/models/context_primitives.py` (camera coverage, temporal coverage, identity resolution debt) | domain-specific — do not inherit | Sensor-domain component taxonomy; the SDK ships debt *mechanism*, users define components. |
| Decision Replay record with five dimensions persisted per significant decision | `packages/si-framework/src/si_framework/models/context_primitives.py` (`DecisionReplayRecord`), `reporting/replay_service.py` | candidate pattern | Existence proof of whitepaper §7.10.1 five-dimension record persisted at write time, not retrofitted. |
| Context compression / three-tier fidelity lifecycle (full → compressed → tombstoned; high-threat never compressed) | `si_framework/models/context_primitives.py` (`CompressedContextSnapshot`); `pool_context_graph.py` `compress()` | candidate pattern | One resolution of year-scale replay tractability the whitepaper leaves open (D-IMPL-06) — data point, not a default; policy of *what* is never compressed is domain-specific. |
| Policy as first-class config loaded into typed models (`SystemPolicy` hierarchy) | `packages/si-framework/src/si_framework/models/policy.py`, `services/policy_service.py`, `config/policy.yaml` + `config/zone_policies.yaml` | candidate pattern | Control-Plane-as-typed-config pattern; the policy *content* (age brackets, supervision ratios, escalation rules) is do-not-inherit (next row). |
| Age classification, supervision ratios, threat/urgency ladders, escalation rules | `config/policy.yaml`, `config/zone_policies.yaml`, `si_framework/models/policy.py` value semantics | domain-specific — do not inherit | Pure domain values (child safety domain); cautionary-contrast example of the mechanism/values line. |
| No-Hardcoding rule enforced by CI grep guard; YAML agent/task definitions + Jinja2 prompt templates with versioned policy/prompt/toolchain per invocation | `config/agent_descriptions/`, `config/task_descriptions/`, `config/prompts/`, CI guard `packages/si-pool-safety/tests/ci_guards/test_no_inline_prompts.py` | candidate pattern | Direct precedent for CCF CLAUDE.md §6.4 No-Hardcoding Rule and its CI lint; YAML+Jinja2 is one data point for D-IMPL-28 (format is open — do not inherit the format by default). |
| Single-writer enforcement: one process (EnrichmentWorker) is sole writer of graph-state collections; hot-path agent writes only its own ingest collections | `packages/si-pool-safety/src/si_pool_safety/enrichment_worker/worker.py`; ADR in Homecams CLAUDE.md §3.2/§5.8 | candidate pattern | Working realization of the whitepaper single-writer invariant (only L2 writes L3), enforced by process topology + repository ownership. |
| Sync/async boundary as process split (synchronous hot path, out-of-process async enrichment worker) — "when sync and async natures collide, split into two processes" | `packages/si-pool-safety/src/si_pool_safety/services/ccf_agent.py` (sync router) + `enrichment_worker/` (async, spawned by `start_property_intelligence.py`) | candidate pattern | Operationally-proven resolution relevant to D-IMPL-04(b) (sync/async runtime posture) — data point only. |
| Idempotent upsert with lineage accumulation and unique natural-key indexes | `packages/si-pool-safety/src/si_pool_safety/repositories/graph_entities_repository.py` (`graph_entities`), `si_framework/repositories/context_edge_repository.py` (`context_edges`, in-batch dedup + unique natural key) | candidate pattern | Matches whitepaper §7.3 idempotent-upsert/multi-source-lineage mechanism (existence proof). |
| Tenant-scoped repository base class; `tenant_id` filter on reference collections | `packages/si-framework/src/si_framework/repositories/tenant_scoped.py` | candidate pattern | Data point for D-IMPL-05 (tenancy model): tenant_id first-class at the repository layer. |
| Zone/camera topology, adjacency, coverage percentages, zone SAA registry | `packages/si-pool-safety/src/si_pool_safety/models/infrastructure.py` (`CameraTopology`, `AdjacentCamera`), `config/zone_policies.yaml` | domain-specific — do not inherit | Camera/sensor spatial ontology is domain values; equivalent SDK concept is user-supplied ontology config. |
| Person/pet/vehicle entity ontology, sentinel labels, known-person registry | `packages/si-pool-safety/src/si_pool_safety/models/` (perception/comprehension models), `persons` registry, `si_framework/models/vehicle_events.py` gallery design | domain-specific — do not inherit | Named in CCF CLAUDE.md §2.1 as the canonical do-not-inherit example. |
| LangGraph 7-node zone agent orchestration | `packages/si-pool-safety/src/si_pool_safety/situational_awareness/`, Homecams CLAUDE.md §3.1 | domain-specific — do not inherit | Homecams hard-binds a specific harness (LangGraph); CCF SDK is harness-neutral by invariant (§7.3) — cautionary contrast, and evidence the loop can live outside SDK mechanism. |
| MQTT topic-namespace event fan-out (`si/{tid}/...`) as the L1/L2 transport | `packages/si-observer/src/si_observer/transport/`, `si_pool_safety/services/ccf_agent.py` | domain-specific — do not inherit | Transport choice bound to the deployment; SDK L1 ingress is Protocol-based (CDC, MCP client, file/stream adapters). The *normalized-event-envelope* idea (`si_framework/models/enrichable_observer_event.py`, dual adapters for two edge shapes) is separately inheritable as a candidate pattern (next row). |
| Normalized enrichable-event contract with per-source adapters at ingress | `packages/si-framework/src/si_framework/models/enrichable_observer_event.py` | candidate pattern | One resolution of L1 event-envelope normalization across heterogeneous sources. |
| Provider-agnostic LLM access via LiteLLM with per-zone provider overrides in config | `config/zone_policies.yaml` LLM/VLM provider blocks; `si_framework/services/llm_service.py` | candidate pattern | Data point for D-IMPL-09 (LLMClientProtocol vs direct vendor SDK). |
| Pluggable classifier/encoder behind a Protocol with factory registration (swappable without code changes) | `packages/si-framework/src/si_framework/models/vehicle_classifier.py` (`VehicleClassifierABC`), `packages/si-inference/src/si_inference/vehicle_classifier.py`, `si_framework/services/vehicle_classifier_factory.py` | candidate pattern | Protocol + factory + registry shape matches CCF "prefer Protocols, ship reference impls" principle (§11); relevant to D-IMPL-07. |
| Scoring/inference as separate HTTP services (scoring farm) | `packages/si-inference/src/si_inference/` (`classifier_server.py`, `multisource_server.py`) | domain-specific — do not inherit | CV-scoring deployment topology; not an SDK concern (production topology is out of scope, CCF CLAUDE.md §13). |
| Conversation layer: intent-classified queries over the fabric with deterministic path for safety-critical intents and context-debt warnings prepended to every answer | `packages/si-conversation/src/si_conversation/`, `packages/si-pool-safety/src/si_pool_safety/conversation/` | domain-specific — do not inherit | The Conversational Reporting Layer is explicitly out of SDK v0 scope (CCF CLAUDE.md §13); debt-warning-on-serve is noted as an interesting D_c surfacing idea for the Experience Layer, but inherits nothing. |
| Web UI / dashboard / Alexa surfaces | `packages/si-web-ui/`, `packages/si-conversation/` (Alexa), `packages/si-app/` (frontend/deploy app shell) | domain-specific — do not inherit | UX surfaces are user-built reference integrations per CCF CLAUDE.md §8.3; no CCF-relevant mechanism beyond what other rows already capture. |
| Prompt-injection mitigation: delimiting untrusted narrative inputs with explicit BEGIN/END markers before LLM consolidation | `si_framework/processors/` (LLMConsolidationProcessor; documented in Homecams CLAUDE.md §6) | candidate pattern | Semantic-stage input-hygiene data point for the Algorithmic ⇄ Semantic boundary. |
| Conservative floor rule: consolidated assessment never below max per-input severity | LLMConsolidationProcessor (`packages/si-framework/src/si_framework/processors/`) | domain-specific — do not inherit | A safety-domain policy value (bias direction), not mechanism; the *mechanism* of policy-constrained consolidation is covered by the policy rows. |

Package coverage note: `si-models` (`packages/si-models/` — binary/identity model weights and
metadata) and `si-ingest-server` (`packages/si-ingest-server/` — edge ingest HTTP service)
yielded no CCF-relevant patterns beyond deployment plumbing already covered above;
`si-app` is covered by the UX-surfaces row. All nine `si-*` packages plus
`start_ccf_agent.py` / `start_property_intelligence.py` were surveyed.

## MongoDB Persistence — ArtifactStore (§7.4) Triangulation Data Point

Derived entirely from Homecams source code (no client install, no live query, per the
RESEARCH.md zero-install route). Collection names and document shapes only — no
connection details and no data records appear here. Overall marker for the persistence
*pattern*: `candidate pattern` (a single system-of-record with typed repositories, a
declared single writer per collection family, and index-as-invariant discipline);
the specific collection inventory and all field values are
`domain-specific — do not inherit`.

**Connection management (mechanism):** a single `MongoDataService`
(`packages/si-pool-safety/src/si_pool_safety/services/mongo_data_service.py`) owns the
pymongo client lifecycle (lazy creation, connection pooling, health check); repositories
receive the database handle from it via the `ServiceContainer`
(`services/service_container.py`). `candidate pattern` — substrate-handle injection is
the same shape as the SDK's storage-Protocol + DI-at-boot posture.

**Repository layer (mechanism):** typed repositories per collection, with a shared
`TenantScopedRepository` base (`packages/si-framework/src/si_framework/repositories/tenant_scoped.py`)
making tenant filtering structural rather than conventional. `candidate pattern`
(D-IMPL-05 data point).

**CCF artifact classes persisted, by collection family** (names/shapes as written in
repository code and Homecams CLAUDE.md §5; counts omitted — live data is out of scope):

| CCF artifact class | Collection(s) | Shape / indexing (from source) | Marker |
|---|---|---|---|
| Context Graph state per cycle | `context_graphs` | Per-cycle G(E,R,T,P,Π,L) documents with `fidelity_level` (full/compressed/tombstoned) — `si_framework/repositories/context_graph_repository.py` | candidate pattern (fidelity field); collection inventory domain-specific — do not inherit |
| Entity/edge registry | `graph_entities` | Idempotent upsert keyed on compound unique index `(tenant_id, entity_uri)` (`graph_entities_tid_uri`); repeat hits `$addToSet`-append to `lineage[]` and advance `last_seen_at`; index absence raises at boot (fail-fast index-as-invariant) — `si_pool_safety/repositories/graph_entities_repository.py` | candidate pattern — directly mirrors whitepaper §7.3 compound-index + multi-source lineage accumulation |
| Relationship/policy edges | `context_edges` | Triple-shaped docs `(tenant_id, subject_id, predicate, object_id, timestamp)`; forward/reverse/predicate-window traversal indexes plus a unique natural-key index (`uniq_edge`); idempotent bulk insert with in-batch dedup — `si_framework/repositories/context_edge_repository.py` | candidate pattern |
| Materialized projection outputs | `projection_cache` | TTL index governs lifecycle (docs expire at explicit expiration timestamp); pure-`$set` upsert keyed on `product_id`; deliberately NO lineage index — lineage queries hit `graph_entities` only (architectural boundary between graph state and projection cache) — `si_framework/repositories/projection_cache_repository.py` | candidate pattern |
| Discriminator quarantine | `context_products_unclassified` | Quarantine for documents that fail the graph-state vs projection-output discriminator during the v5.0 collection split | candidate pattern (migration-safety idea); do-not-inherit as a permanent surface |
| Assembled fabric instances | `cognitive_context_fabrics` | `activated_product_uris` written by the enrichment worker — `si_framework/repositories/fabric_activation_repository.py` | domain-specific — do not inherit (fabric persistence shape is bound to Homecams' MQTT pipeline) |
| Decision Replay records | `decision_replay_records` | Full five-dimension decision state persisted per significant decision; alerts additionally embed full dynamic context for self-contained replay — `si_framework/reporting/replay_service.py` | candidate pattern — key ArtifactStore triangulation row: replay records as immutable persisted artifacts |
| Half-life state | `context_half_life_states` | Per-observation-type decay tracking — `si_framework/services/context_half_life_service.py` | candidate pattern (mechanism); observation types domain-specific — do not inherit |
| Perception/intelligence time series | `observer_states`, `model_scores`, `monitor_summaries`, `states`, `alerts`, `alert_dispatches` | Timeseries collections (append-only) with a separate mutable regular collection (`alert_dispatches`) for lifecycle state, because timeseries collections cannot mutate | candidate pattern (append-only-vs-mutable split); collections domain-specific — do not inherit |
| Reference/config data | `cameras`, `camera_topology`, `persons`, `zones`, `vehicles`, `vehicle_embeddings`, `models` | Tenant-scoped (`tenant_id`) reference registries | domain-specific — do not inherit |

**Single-writer discipline over the store:** the enrichment worker is the declared sole
writer of `graph_entities` / `projection_cache` / `context_products_unclassified` /
`context_edges` / `cognitive_context_fabrics.activated_product_uris`
(`si_pool_safety/enrichment_worker/worker.py`; ADR in Homecams CLAUDE.md §3.2/§5.8);
the hot-path agent writes only its own ingest collections. `candidate pattern` — a
process-topology realization of "the store is a substrate behind mechanism, never a
second writer" (CCF CLAUDE.md §7.4).

**Versioning/immutability observations relevant to D-IMPL-26:** Homecams versions by
embedded fields (model version, prompt template version, policy version inside replay
records) rather than content-addressing or versioned URIs; artifacts are effectively
immutable by append-only timeseries semantics plus the compression/tombstone lifecycle.
This is one data point for the ArtifactStore addressing decision, not a default.

**Cautionary contrast:** Homecams treats MongoDB as the mandated single system-of-record
("MongoDB is the single system-of-record" — Homecams CLAUDE.md §1.4). The SDK must NOT
inherit a mandated substrate: persistence goes behind `ArtifactStoreProtocol` and the
graph-storage Protocol (D-IMPL-02/26/27), with MongoDB merely one possible user-supplied
backend. Marker for substrate mandate: `domain-specific — do not inherit`.

