# Checkpoint 1A — CCF Concept, Diagram & Graphics Inventory

**Source:** `drcastillo/ccf`  
**Pinned source commit:** `ac81805d0e400da15f860eed8c39a132af3ce945`  
**Status:** READY FOR CHECKPOINT 1A REVIEW

## 1. Purpose

This inventory identifies the parts of the CCF whitepaper source repository that should be reused, adapted, or referenced when building the adoption portal. The published PDF remains the released whitepaper artifact, but the adoption work should use the structured Markdown, inline Mermaid, and source graphics wherever possible instead of extracting content from the PDF.

The adoption portal is not a second whitepaper. It should turn the whitepaper's architectural vocabulary into a task-oriented learning and implementation experience.

## 2. Source hierarchy inside `ccf`

The whitepaper repository already separates source, lineage, build machinery, and published artifact:

1. `whitepaper/CCF_*.md` — authoritative current chapter source.
2. Inline Mermaid fences in those chapter files — authoritative diagram source for most technical diagrams.
3. `whitepaper/figures/CH##/*.png` — selected static/polished figures; matching `_orig.png` files preserve originals.
4. `docs/CCF_Chapter_N_*.md` — historical/draft lineage only, not preferred source.
5. `CCF_Whitepaper_1-2.pdf` — published v1.2 distribution artifact.

For adoption content, prefer items 1–3. Use the PDF to validate the published presentation or to provide the released document itself.

## 3. Narrative sources and adoption role

| Source | Core contribution | Recommended adoption use | Reuse class |
|---|---|---|---|
| `CCF_00b_Executive_Summary.md` | Concise why-now / why-context / core primitives story | Landing page, Start Here, executive/architect path | **ADAPT** — retain architecture, neutralize institution-specific language |
| `CCF_Chapter_1_Banking_AI.md` | Banking problem, architectural accretion, Forensic Data Gap | Why CCF / problem framing | **ADAPT** |
| `CCF_Chapter_2_Banking_Agents.md` | Agentic systems in financial services and context gap | Agent developer learning path | **ADAPT** |
| `CCF_Chapter_3_Agent_Anatomy.md` | Agent anatomy, execution loop, context as operating environment, multidimensional context, context-starved failure modes | Start Here, developer mental model, governance story | **HIGH REUSE** |
| `CCF_Chapter_4_BI_Agents.md` | BI → agentic AI gap; why query/semantic layers alone do not construct decision context | Why CCF / architecture evaluator path | **ADAPT** |
| `CCF_Chapter_5_CCF.md` | Systems of Cognition, `G(E,R,T,P,Π,L)`, Dynamic Context vs Content, mapping existing data systems, derived-not-stored Context Products | Core CCF concepts and architecture overview | **PRIMARY SOURCE** |
| `CCF_Chapter_6_Context_Product.md` | Context Product category, contract, lifecycle, decision-scoped output | Using the SDK conceptual introduction; Context Product reference concepts | **PRIMARY SOURCE** |
| `CCF_Chapter_7_CCF_Architecture.md` | Mechanism-level architecture: L1–L6, graph, operators, projection, delivery, debt/half-life, planes, closed loop, replay | Architecture & Patterns; Using SDK advanced concepts; governance | **PRIMARY SOURCE** |
| `CCF_Chapter_8_CCF_Integration.md` | Layering-not-replatforming, five non-invasive patterns, enterprise integration, four financial-services archetypes | Architecture & Patterns; adoption/evaluation path; use-case framing | **PRIMARY SOURCE, ADAPT** |
| `CCF_Chapter_9_Summary.md` | Eight primitives, single-domain pilot, platform/domain split, adoption summary | Glossary, architecture quick reference, Adoption Guide | **HIGH REUSE** |

## 4. Canonical concepts to preserve

The following terms are architectural vocabulary and should remain consistent across the adoption site. They may be explained in simpler language, but their names and semantics should not drift.

### 4.1 Context as the operating environment

Chapter 3 establishes the key developer mental model: the model determines how reasoning is performed; context determines what reasoning is possible. Context is not merely another input or prompt payload. This is a strong candidate for the early learning path because it explains why CCF exists before a developer encounters any SDK API.

### 4.2 Systems of Record → Signal Generation → Cognition

Chapter 5 positions CCF as a new architectural responsibility above the existing data estate, not as a replacement for it. This is the conceptual bridge from enterprise data architecture to CCF.

### 4.3 Context Graph `G(E, R, T, P, Π, L)`

Canonical six dimensions:

- `E` — Entities
- `R` — Relationships
- `T` — temporal validity
- `P` — Policy
- `Π` — Perspective / typed projection
- `L` — Lineage

This formalism should be a persistent visual and conceptual anchor throughout the portal.

### 4.4 Dynamic Context vs Dynamic Content

Canonical rule: **Context informs content; content does not define context.** Useful for explaining where CCF sits relative to LLM generation, RAG, and agent output generation.

### 4.5 Context Products — derived, not stored

A Context Product is a typed, governed, decision-ready unit of meaning constructed for a specific decision frame. It should be presented as the primary consumer interface to CCF rather than as a query result or persisted dataset.

### 4.6 Data Products and Context Products are composition partners

The whitepaper repeatedly emphasizes layering rather than displacement. Data Products remain governed substrate; Context Products are decision-time outputs for agents. This distinction should be central to the adoption story because it lowers perceived migration risk.

### 4.7 L1–L6 layered architecture

Canonical layers from Chapter 7:

- L1 Signal Layer
- L2 Context Assembly
- L3 Context Graph
- L4 Context Operators
- L5 Context Projection (Π)
- L6 Context Products

The layers are responsibility boundaries, not a simple sequential pipeline.

### 4.8 Context Operators

Typed computation over the graph: traversal, temporal, policy, similarity and related compositions. For adoption purposes, Chapter 7 supplies the architectural meaning; `ccf_code` must later supply the authoritative SDK API/reference behavior.

### 4.9 Context Projection (Π)

Projection is typed role-conditioned transformation, **not RBAC filtering**. The same graph state can produce different Context Products for different principals without duplicating underlying state.

### 4.10 Context Debt and Context Half-life

Context Half-life models per-signal decay. Context Debt makes insufficiency, staleness, or uncertainty explicit and is designed to bias action conservatively rather than let agents silently reason over degraded context.

### 4.11 Control Plane vs Data Plane

The Control Plane declares what the fabric is allowed to do and how it is parameterized; the Data Plane executes continuously within those constraints. This belongs in both architecture and governance learning paths.

### 4.12 Decision Replay

Decision Replay is environment/evidence replay, not merely model trace. It reconstructs the decision substrate — graph state, policy version, lineage, operator composition, freshness — needed for forensic review.

### 4.13 Assembly Mode

Per-Context-Product configuration distinguishing pure algorithmic assembly, algorithmic assembly plus LLM packaging, and algorithmic orchestration with agent-swarm assembly. The adoption portal should introduce this only after the base Context Product model is understood.

### 4.14 Layering, not replatforming

Chapter 8's central enterprise-integration posture: CCF composes over warehouses, lakehouses, Data Mesh nodes, semantic layers, systems of record, streams, and document stores. Heterogeneity is treated as an operating condition, not a temporary defect that must be eliminated before adoption can begin.

## 5. High-value reusable Mermaid diagrams

Most diagrams are inline Mermaid in the chapter Markdown and therefore can be reused as source, adapted, themed, and kept diffable in `ccf_adoption` when we build the site.

### Chapter 3 — agent/context mental model

| Figure | Purpose | Adoption candidate |
|---|---|---|
| `Fig-CH03-01` | Anatomy of an Agent — Memory, Reasoning, Context, Tools, Feedback | Start Here / agent developer |
| `Fig-CH03-02` | Agent Execution Loop; Context Assembly as the inflection between intent and action | Start Here / Using SDK |
| `Fig-CH03-03` | Scalar BI context vs multidimensional agentic context | Why CCF |
| additional Ch. 3 Mermaid | Context-starved failure modes / surrounding mental models | Governance / Why CCF after review |

### Chapter 5 — conceptual model

| Figure | Purpose | Adoption candidate |
|---|---|---|
| `Fig-CH05-01` | Semantic-layer tuple vs Context Graph six-tuple; makes P / Π / L extension explicit | Core concepts / architecture evaluator |
| `Fig-CH05-02` | Systems of Record → Signal Generation → Cognition | Landing architecture / Why CCF |

### Chapter 6 — Context Products

| Figure | Purpose | Adoption candidate |
|---|---|---|
| `Fig-CH06-01` | Data Product lifecycle vs Context Product lifecycle | Using the SDK / evaluator path |
| other Ch. 6 Mermaid | Contract, lifecycle and trust concepts | Evaluate individually during Phase 2/3 |

### Chapter 7 — architecture mechanics

Chapter 7 contains numerous inline Mermaid diagrams in addition to the static figures below. Particularly valuable candidates include role-conditioned projection, runtime conditioning, operator composition, Conditional Assessment Routing, Debt cascade, control/data plane mechanics and other mechanism diagrams. We should copy Mermaid source selectively, not bulk-copy every whitepaper figure.

### Chapter 8 — enterprise integration

| Figure | Purpose | Adoption candidate |
|---|---|---|
| `Fig-CH08-01` | Non-invasive Tier-1 integration architecture: existing estate → CCF Perception → Comprehension → Reasoning/Action → Replay | Architecture & Patterns / Adoption Guide |
| additional Ch. 8 Mermaid | Five integration patterns and use-case/archetype integration views | Architecture & Patterns / Financial Services Use Cases |

## 6. Static/polished figures available for direct visual reuse

The repo stores selected polished PNGs plus `_orig.png` originals. The non-original rendered assets currently discovered are:

| Asset | Meaning | Likely portal use |
|---|---|---|
| `whitepaper/figures/CH03/Fig-CH03-04-debt-cascade.png` | Context Debt cascade | Governance / Context Debt |
| `whitepaper/figures/CH07/Fig-CH07-01-overall-architecture.png` | CCF as persistent institutional memory / closed-loop architecture | Landing architecture / Overview |
| `whitepaper/figures/CH07/Fig-CH07-02-layer-model.png` | L1–L6 logical architecture | Architecture / Reference |
| `whitepaper/figures/CH07/Fig-CH07-03-G-hexagon.png` | `G(E,R,T,P,Π,L)` six-dimension visual | Core concepts / recurring visual motif |
| `whitepaper/figures/CH07/Fig-CH07-13-product-lifecycle.png` | Eight-step Context Product lifecycle and contract sidebar | Using the SDK / Context Product overview |
| `whitepaper/figures/CH07/Fig-CH07-17-trust-triangle.png` | Confidence / Freshness / Lineage trust triangle | Governance / controls |
| `whitepaper/figures/CH07/Fig-CH07-26-replay.png` | Decision Replay | Governance / assurance / architecture |

Each has a matching `_orig.png` in the source repo. Before copying any rendered graphic into `ccf_adoption`, Phase 2 should decide whether to reuse the rendered version, the original, or recreate the concept using source-controlled Mermaid/D2 to fit the portal design system.

## 7. Concept-to-portal mapping

| Portal area | Preferred `ccf` sources |
|---|---|
| Start Here / What is CCF? | Executive Summary; Ch. 3 context mental model; Ch. 5 conceptual model; Ch. 7 overall architecture |
| Whitepaper | Published v1.2 snapshot + provenance only |
| CCF Overview / Video companion | Executive Summary; Ch. 5; selected Ch. 7 visuals |
| Using the SDK — consumer | Ch. 6 Context Product concept; Ch. 7 delivery surface; SDK details must come from `ccf_code` |
| Using the SDK — assembler | Ch. 5 graph model; Ch. 7 L1–L6, operators, projection, debt/half-life, planes; API behavior from `ccf_code` |
| Reference Manual | `ccf` for definitions/rationale; `ccf_code` for authoritative public API and runtime behavior |
| Architecture & Patterns | Ch. 5 mapping; Ch. 7 mechanism; Ch. 8 integration patterns |
| Financial Services Use Cases | Ch. 5/8 for framing only; detailed requirements should come from `obsidian-vault` and executable evidence from `ccf_code` |
| Governance & Controls | Ch. 5 P/Π/L/T; Ch. 7 debt, half-life, Control Plane, Decision Replay, Trust Triangle |
| Security & Assurance | Reuse architecture/trust-boundary concepts where relevant; vulnerability claims must come from the future assessment, not the whitepaper |
| Operations / Production | Ch. 7/8 architectural guidance; operational truth must be reconciled with SDK implementation and deployment examples |
| Adoption Guide | Ch. 8 layering-not-replatforming + Ch. 9 single-domain pilot and platform/domain ownership split |

## 8. Reuse classes

Every source fragment considered for publication should receive one of these dispositions:

### REUSE — canonical

Use with minimal or no semantic change. Examples: names of primitives, six-tuple dimensions, L1–L6 names, derived-not-stored, Control Plane/Data Plane, Decision Replay, Context Debt/Half-life.

### ADAPT — institution-neutral

Preserve the architectural claim but remove institution-specific strategy, migration, organization, or branding references. Much of the Executive Summary and Chapter 8 falls into this category.

### VISUAL REUSE

A diagram or figure is conceptually suitable for the portal. Preserve source provenance. During Phase 2, decide whether its existing styling fits the product design; if not, recreate from the same source semantics rather than editing the meaning.

### SOURCE ONLY

Use to understand or validate the architecture but do not republish directly without revalidation. Examples include time-sensitive vendor comparisons, external market claims, research citations, institution-specific implementation details, and numerical claims whose freshness matters.

## 9. Important boundary with `ccf_code`

The whitepaper is authoritative for architectural intent and terminology. It is **not automatically authoritative for current SDK method names, signatures, configuration fields, defaults, exceptions, or executable behavior**.

When the adoption site says *what CCF means*, `ccf` can be authoritative.

When the adoption site says *what the SDK currently does*, `ccf_code` must be authoritative and the statement should be traceable to implementation/tests/examples.

This boundary is essential to keep the adoption material accurate as the SDK evolves.

## 10. Checkpoint 1A recommendation

Approve the following source strategy for subsequent phases:

1. Treat `ccf@ac81805d` as the pinned whitepaper-source baseline for the initial adoption build.
2. Prefer structured Markdown and Mermaid over PDF extraction.
3. Reuse canonical architectural terminology without drift.
4. Adapt institution-specific prose to financial-services-neutral language.
5. Selectively reuse/recreate diagrams rather than copying the complete whitepaper figure set.
6. Preserve source provenance for every reused asset.
7. Defer SDK-behavior claims to Checkpoint 1B and `ccf_code`.
8. Defer detailed financial-services requirements/data lineage to Checkpoint 1C and the Vault/dataprep sources.

If approved, Phase 1B begins with an inventory of the public SDK surface and a mapping of capability → implementation → test → example → candidate documentation section.
