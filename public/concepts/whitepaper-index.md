# Whitepaper cross-reference

The CCF whitepaper is proprietary and is not published with this
documentation. This page is for readers who already hold a copy: it maps each
SDK surface to the section number and title that specifies it, so that a
question about fidelity can be taken straight to the governing section.

Nothing on this page reproduces or summarizes what those sections say. If you
do not hold the whitepaper, the [Concepts pages][invariants] and the
[Reference][storage] section are self-contained; this table adds nothing for
you.

Titles are given in short form where the full heading is long; the section
number is the authoritative key. Sections beginning `5.` are chapter 5, `6.` chapter 6, `7.` chapter 7 and `8.`
chapter 8.

| SDK surface | Section | Section title |
| --- | --- | --- |
| Context Graph, six axes | 5.2 | Context Graph Definition |
| Products are derived, not stored | 5.6 | Context Products — Derived not Stored |
| Overall fabric architecture | 5.7 | The Cognitive Context Fabric Architecture |
| Why a data product is not enough | 6.1 | Why Data Products Are Insufficient |
| Context Product definition | 6.2 | Definition of Context Product |
| Context Product Contract | 6.3 | Context Product Specification |
| Product cache states | 6.4 | Context Product Lifecycle |
| Product design principles | 6.5 | Context Product Key Principles |
| Late-binding content acquisition | 6.6 | Search ↔ Inference Loop |
| Layer packages L1–L6 | 7.1 | Layered Architecture (L1–L6) |
| Component decomposition | 7.2 | Architectural Decomposition |
| Graph store and the single writer | 7.3 | Context Graph — System of State |
| Operator algebra and planning | 7.4 | Context Operators — System of Computation |
| Projection engine (Π) | 7.5 | Context Projection (Π) — System of Interpretation |
| Delivery layer and validation gates | 7.6 | Context Products — System of Delivery |
| Half-life and debt computation | 7.7 | Context Debt and Context Half-life |
| Control Plane and Data Plane split | 7.8 | Control Plane vs Data Plane |
| Outcome feedback to configuration | 7.9 | Closed Loop with Self-Learning |
| Five-dimension replay record | 7.10 | Decision Replay |
| Layering posture over existing systems | 8.2 | Layering, Not Replatforming — The Central Design Principle |
| Ingress patterns, MCP and A2A | 8.3 | Non-Invasive Integration Patterns |
| Unstructured ingestion stack | 8.3.1 | Pattern 5 Reference Stack |
| Algorithmic ⇄ Semantic alternation | 8.4 | The Alternating Derivation Pipeline |
| Temporal abstraction across batch and stream | 8.6 | The Temporal Abstraction Layer |
| Quantitative governance primitives | 8.7 | Governing Agentic Risk — Quantitative Primitives |
| Half-life and debt as governance | 8.7.1 | Half-life and Debt as Governance Primitives |
| Policy-before-similarity ordering | 8.7.2 | MNPI Governance via Policy-before-Similarity |
| Fail-closed behaviour | 8.7.3 | Fail-Closed Under Degraded Sources |
| Replay retention and compression | 8.9 | Auditability at Scale — Replayability and Compression |
| Adoption sequencing | 8.11 | Incremental Adoption and Organizational Implications |

## Surfaces the whitepaper does not specify

Several parts of the SDK are extensions rather than realizations. They are
marked as SDK-defined wherever they appear, and they cite the project charter
rather than a whitepaper section: the agent specialization framework and the
agent and task factory, bidirectional MCP, federation as a v0 commitment, the
harness adapter surface, artifact persistence, the orchestration primitive, the
HITL primitives, and the Experience Layer front doors.

The [pillar pages][datactx] say which of the five pillars each extension
serves.

[invariants]: invariants.md
[storage]: ../reference/protocols/storage-and-graph.md
[datactx]: pillars/data-context.md
