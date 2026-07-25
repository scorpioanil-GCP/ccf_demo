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
- **Open question:** The element count is internally inconsistent in the `.md`. §6.3 prose opens "Nine elements jointly specify the contract" and the table lists nine (Assembly Mode included; §6.4 calls it "the §6.3 specification's ninth element"), yet the same §6.3 prose describes the §6.1 contract test as "the § 6.1 canonical 8-property table" and says "the 8-property test names what the contract carries; the 9-element specification names which contract surface each property maps to" — while CLAUDE.md §5 refers to "the eight-element specification per §6.3." Readings: (a) the contract has nine elements and the "eight" references (8-property test, CLAUDE.md) denote the external comparison test only — consequence: the SDK Context Product Contract base must carry all nine fields including Assembly Mode; (b) the contract has eight elements and Assembly Mode is a distinct per-product *configuration* property layered on the contract rather than a contract element — consequence: Assembly Mode lives in Control Plane product-class registration, not in the product schema; (c) the whitepaper drifted between revisions and the count is editorial — consequence: Dave rules which count is canonical and CLAUDE.md or the inventory annotates the discrepancy. The mapping from the 8 test properties to the 9 elements is asserted but never tabulated, so the property→element correspondence is also unspecified.

### INV-CH6-04 — Eight-step Context Product Lifecycle with closed-loop audit feedback

- **Section:** §6.4
- **Commitment:** A canonical eight-stage lifecycle: (1) Event/Data Ingestion — signals enter with source metadata preserved (origin system, emission timestamp, emitting principal, payload schema version) as the precondition for Lineage, Temporal Validation, and Replay; (2) Semantic Resolution — ontology mapping and entity resolution into the shared semantic frame; (3) Context Graph Mutation — append-plus-supersession discipline; "Mutation never overwrites; it layers, so temporal truth remains reconstructible"; (4) Temporal Validation — TTL assignment and validity assessment; refuses to assemble products that silently mix signals of asymmetric freshness; (5) Policy Binding — constraints applied during construction; impermissible reasoning paths foreclosed before serving; (6) Context Serving — via the addressable endpoint under the full contract; (7) Agent Consumption — the agent reasons only; no assembly work (no entity resolution, temporal stitching, policy filtering, re-interpretation); (8) Replay & Audit — action captured for replay; audit findings feed back as policy updates entering Step 1. "The lifecycle is a loop, not a pipeline." Products are inherently ephemeral; any change in signal, intent, policy, or entitlement requires reconstruction. The architectural heart is **trust-path purity** — deterministic source-of-record with optional probabilistic presentation: the algorithmic substrate is the artifact-of-record; renderings are presentation. Algorithmic and semantic stages alternate: Steps 1–6 algorithmic, Step 7 semantic, Step 8 algorithmic; "No semantic stage operates on raw signal, and no algorithmic stage performs semantic interpretation." Three consequences: replayable/auditable deterministic assembly; reduced hallucination surface (LLM sees dimensionally reduced, policy-enriched substrate); contained cost.
- **Type signature:** none given
- **Invariants:** Append-plus-supersession (no overwrite); assembly-vs-reasoning division of labor (Step 7 does no assembly); trust-path purity across all Assembly Modes (substrate is artifact-of-record; lineage recorded at substrate, not rendering; replay re-derives the substrate deterministically from the same graph state); Algorithmic ⇄ Semantic Alternation; the Step 8 → Step 1 feedback edge closes the loop.
- **Dependencies:** INV-CH6-03 (contract elements enforced through the lifecycle); Ch 7 §7.4 (Operators as the algorithmic-stage combination mechanism), §7.6 (Assembly Mode mechanism) — Ch 7 fragment.
- **Figures:** Fig-CH06-02 (eight-step lifecycle with dotted feedback edge)
- **Open question:** §6.4 Step 4 states "Temporal Validation assigns TTL to each mutation," while §6.3 defines TTL as a per-product contract element and §6.4's Counterparty thread gives per-product TTLs (four hours trading-desk, twenty-four hours committee) alongside per-signal TTLs ("an intraday trade-blotter entry carries a TTL of fifteen minutes"). Readings: (a) TTL exists at two granularities — per-mutation/per-signal validity in T and per-product validity in the contract — and the product TTL is derived from (e.g., min over) constituent signal validities; consequence: the SDK needs both a signal-level validity primitive and a product-level TTL with a defined derivation rule; (b) "TTL" in Step 4 loosely means the T-dimension validity envelope (half-life driven) and only the contract-level TTL is properly named TTL; consequence: naming must be disambiguated in the SDK type surface to avoid conflating half-life-derived validity with contract TTL; (c) product TTL is independently configured per product class and Step 4 only validates constituent signals against it; consequence: no derivation rule is required but a mixing-refusal rule (asymmetric-freshness refusal) still needs formal definition. The whitepaper does not specify the derivation or refusal rule; Ch 7 §7.7 may partially resolve this (Ch 7 fragment to cross-check).

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
- **Open question:** §6.6.3 specifies each leg's inputs ("Combines model scores, source reliability, and consensus…") and the conjunctive semantics, but no aggregation function, scale, or threshold mechanics for any leg or for aggregate Context Trust — "when all three legs hold, the recursion may terminate" leaves "hold" undefined. Readings: (a) the aggregation/thresholds are deliberately Control-Plane-configurable values (mechanism ships scoring interfaces; institutions supply thresholds) — consequence: the SDK defines a TrustScore Protocol with pluggable per-leg scorers and a conjunctive combinator, values in configuration per the mechanism-not-values rule; (b) a canonical formula is implied elsewhere (e.g., via Ch 7 §7.7 D_c mechanics) and the legs are derived quantities — consequence: cross-check the Ch 7 fragment before designing an independent trust primitive; (c) the triangle is advisory vocabulary, not a mechanism commitment — consequence: no SDK primitive required, only replay-record capture of whatever trust inputs the deployment computes. The choice gates whether v0 ships a trust-scoring surface.

---

## Open Questions (unnumbered)

*(Emitted unnumbered for synthesis pickup; plan 01-11 assigns D-IMPL-30+.)*

- *(from Ch 5 extraction)* None surfaced — Ch 5 is conceptual and defers all mechanism ambiguity to Ch 7, whose fragment carries those questions.
- *(from §6.3, INV-CH6-03)* Contract element count discrepancy — "Nine elements jointly specify the contract" vs the "canonical 8-property table" and CLAUDE.md §5's "eight-element specification per §6.3"; the 8-property→9-element mapping is asserted but never tabulated. Three readings with consequences recorded at INV-CH6-03.
- *(from §6.4, INV-CH6-04)* TTL granularity ambiguity — per-mutation/per-signal TTL (Step 4 "assigns TTL to each mutation") vs per-product contract TTL; no derivation rule or formal asymmetric-freshness refusal rule specified. Three readings with consequences recorded at INV-CH6-04; cross-check Ch 7 §7.7 fragment.
- *(from §6.6.3, INV-CH6-08)* Context Trust Triangle mechanics unspecified — no aggregation function, scale, or thresholds for the three legs or the aggregate; "when all three legs hold" leaves "hold" undefined. Three readings with consequences recorded at INV-CH6-08; gates whether v0 ships a trust-scoring surface.
