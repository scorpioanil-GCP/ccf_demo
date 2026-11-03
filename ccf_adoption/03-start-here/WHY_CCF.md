# Why CCF

## The missing responsibility is context construction

Enterprise data platforms were built to capture, govern, organize, and serve data. They do that well.

What they historically leave to the human consumer is the **interpretive work required at decision time**:

- which entities and relationships matter for this decision;
- which signals are still valid;
- which policy regime applies;
- what the current role is allowed to see or act upon;
- how the same underlying state should be interpreted for a different principal;
- which evidence supports each claim;
- what was missing, stale, or uncertain when the decision was made.

When the consumer is a human analyst, that work can happen outside the architecture. The human reads across systems, reconstructs relationships, judges recency, applies policy, and writes the final answer.

When the consumer is an agent operating at machine cadence, that assumption breaks. The system itself must construct the decision environment before reasoning begins.

CCF makes that responsibility architectural.

---

## Agents are not simply faster human workflows

Agents differ from human-centric processes in several important ways.

### They compose at runtime

An agent may combine sources that were never joined when the underlying systems were designed. The decision frame cannot always be pre-modeled as one table, report, or materialized view.

### They operate at machine cadence

A signal that was acceptable for a human workflow measured in days may be unusable for a decision made in seconds or minutes. Freshness must therefore be carried at the signal/claim level, not assumed globally.

### They ask questions schemas did not anticipate

The question being asked today may not have existed when the warehouse, semantic model, or Data Product was designed. The architecture has to compose meaning without requiring the underlying estate to be redesigned for every new agent question.

### They may carry decision authority

When an intelligent system participates in regulated workflows, evidence, policy, lineage, and reconstruction cannot be optional logging conveniences. They are part of the decision substrate.

---

## Context is the operating environment

A useful way to understand the problem is to separate the model from the environment in which the model reasons.

An agent combines:

- Memory
- Reasoning
- **Context**
- Tools
- Feedback

The model drives reasoning, but reasoning is bounded by the context supplied to it.

**The model determines how reasoning is performed; context determines what reasoning is possible.**

A more capable model does not repair a stale, policy-empty, role-flat, incomplete decision frame. CCF focuses on the environment the agent reasons against.

---

## Why ordinary retrieval is not enough

Retrieval answers *what can I fetch?*

Decision context must also answer:

- **What is true?**
- **What is still true?**
- **What is relevant to this intent?**
- **What may this principal reason over?**
- **How should the state be projected for this role?**
- **Where did each claim come from?**
- **What is missing or stale?**

That is why CCF is not defined as another RAG layer, search system, semantic layer, or graph database. Those can all be valuable inputs. CCF adds the architectural responsibility of constructing governed decision context from them.

---

## Why existing data architecture remains essential

CCF is not an argument that warehouses, lakehouses, Data Mesh, Data Products, semantic layers, knowledge graphs, streams, or document stores are obsolete.

The opposite is true: CCF depends on them as governed signal sources.

The enterprise problem is not that those systems are wrong. They were optimized for different responsibilities:

- **Systems of Record** preserve authoritative operational facts.
- **Signal-generation systems** refine, govern, publish, and expose usable enterprise data.
- **Systems of Cognition** construct decision-ready meaning from those signals at the moment it is needed.

CCF occupies the third responsibility.

---

## Layering, not replatforming

The enterprise integration posture is simple:

**CCF layers over the existing estate; it does not require the estate to be replaced first.**

A bank or other large enterprise may be simultaneously operating relational warehouses, cloud lakehouses, domain Data Products, operational systems, graphs, streaming platforms, document archives, and active migration programs. CCF treats that heterogeneity as the operating condition.

A source-system change should be an ingestion/binding concern, not a reason to re-architect the cognition layer.

This allows teams to pilot CCF against the estate they have now rather than waiting for a hypothetical fully consolidated future state.

---

## The failure modes CCF is designed to make visible

Context problems are often silent because the resulting answer can still look plausible.

Common failure classes include:

- **Context Starved** — necessary signals or relationships never entered the decision frame.
- **Latency Poisoned / temporally incoherent** — stale or differently timed signals were treated as equally current.
- **Policy Blind** — the frame was constructed without the governing policy state.
- **Perspective Flat** — one role's interpretation was treated as universal.
- **Lineage-poor / unreplayable** — the decision cannot be reconstructed from the evidence that actually produced it.

CCF is designed to surface those conditions before or alongside reasoning rather than leave them hidden behind a fluent answer.

---

## What CCF changes

CCF adds a set of first-class architectural primitives:

- a Context Graph that carries entities, relationships, time, policy, perspective, and lineage;
- Context Operators that compute over the graph under typed constraints;
- Context Projection that shapes the graph for a principal and intent;
- Context Products as the governed delivery interface;
- Context Half-life and Context Debt to make decay and insufficiency explicit;
- a Control Plane that declares what the fabric may do;
- Decision Replay that reconstructs the evidence environment behind an action.

Together, those primitives move interpretation from an implicit human activity into an explicit, governed system responsibility.

---

## The shortest version

**CCF exists because agents need more than access to data. They need a governed representation of what matters, right now, for this decision, for this principal, under this policy — with evidence.**

---

## Next

- [Architecture at a Glance](ARCHITECTURE_AT_A_GLANCE.md)
- [Context Products](CONTEXT_PRODUCTS.md)
- [Start Here](START_HERE.md)

## Source provenance

Adapted from `drcastillo/ccf@ac81805d0e400da15f860eed8c39a132af3ce945`, especially Chapter 3 §3.2–3.6, Chapter 5 §5.1–5.2, Chapter 6 §6.1, and Chapter 8 §8.1–8.3. Institution-specific examples and vendor-comparison detail are intentionally omitted from this front-door explanation.
