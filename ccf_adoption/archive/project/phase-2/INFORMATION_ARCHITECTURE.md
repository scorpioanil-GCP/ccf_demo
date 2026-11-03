# CCF Adoption Portal — Information Architecture

## Status

Phase 2A proposal. This document defines the user-facing information architecture for the CCF adoption portal. It does not dictate repository layout, site generator, or final visual design.

## Product principle

The portal should answer a visitor's next question, not expose the internal organization of the source repositories.

A useful evaluator journey is:

`What is CCF? → Why does it matter? → How do I use it? → How do I build one? → Show me a real financial-services implementation → How is it governed? → Can I run and operate it? → How do I adopt it?`

The portal therefore uses a deliberately small primary navigation with deeper task-oriented routes beneath it.

---

## Primary navigation

### 1. Start Here

Purpose: orient a technically sophisticated newcomer in minutes.

Includes:

- What CCF is
- Why CCF exists
- CCF in one architecture view
- NotebookLM overview video
- Whitepaper access
- Choose your learning path
- Key terminology
- Where CCF fits relative to data products, RAG, knowledge graphs, agent frameworks, and ordinary APIs

Primary audiences: evaluator, architect, technical leader, new developer.

### 2. Learn CCF

Purpose: explain the conceptual and architectural model without requiring SDK knowledge.

Includes:

- Systems of Cognition
- Context Products
- `G(E,R,T,P,Π,L)`
- Context Graph
- Context Projection
- Context Half-life
- Context Debt
- Decision Replay
- Control Plane / Data Plane
- L1–L6 architecture
- Layering, not replatforming
- Architecture & Patterns
- Whitepaper concepts and reusable diagrams

Primary audiences: architect, technical evaluator, controls/governance, senior developer.

### 3. Build with CCF

Purpose: task-oriented learning for people using the SDK.

Split immediately into two distinct routes:

#### Consume Context Products

- install / connect
- discover a product
- ask a product
- understand `Result`
- handle governed refusal
- debt / lineage / replay from the consumer view
- in-process consumption
- MCP consumption
- ADK / Claude Agent SDK / LangGraph harness examples
- advanced binding and adapter topics

#### Assemble Context Products

- restore and verify the demonstration data estate
- start from the business decision
- work with the SME
- design the Context Product
- author an implementation specification
- use AI to accelerate spec drafting without inventing terms
- bind sources
- acquire signals
- resolve graph state
- compose operators
- project for a principal
- bind policy, temporal semantics, provenance, Debt, and replay
- validate and expose the product
- debug / troubleshoot

Also includes:

- Specification Standard
- Spec-generation recipe
- Example-delivery recipe
- Small progressive tutorials
- Advanced SDK patterns

Primary audiences: consumer/agent developer, data engineer, Context Product assembler.

### 4. Reference

Purpose: answer precise implementation questions without tutorial narrative.

Includes:

- SDK Reference Manual
- Consumer API
- Product contracts / requests / results
- assembly interfaces
- graph / operators / projection
- freshness / Debt
- Control Plane
- replay
- deployment/configuration
- transports / runtime bindings
- specification references and templates
- glossary
- version / maturity markers

Every reference page must be pinned to an approved SDK evidence baseline. Reference content must distinguish `STABILIZED`, `VALIDATED-CURRENT`, `PROVISIONAL`, `INTERNAL`, and `DEPRECATED / SUPERSEDED` surfaces.

Primary audiences: developer, assembler, platform engineer.

### 5. Financial Services

Purpose: show why CCF matters by solving realistic financial-services problems end to end.

Each example begins with the business problem, not SDK code.

Includes:

- use-case catalog
- domain/family browsing
- CP-00 learning rung, clearly labeled as pre-Vault warm-up
- CP-01 onward as whitepaper/Vault-derived use cases where supported
- business decision and counterfactual failure
- personas, including controls/governance
- data reality and deliberate limitations
- Context Product specification
- assembly architecture
- control/governance view
- implementation walkthrough
- run / expected result
- proves / does not prove
- evidence lineage

Primary audiences: banker/SME, evaluator, data engineer, controls/governance, architect.

### 6. Govern & Operate

Purpose: bring enterprise controls, security, data-estate operation, and production concerns into one coherent destination.

Subsections:

#### Governance & Controls

- provenance / lineage
- entitlement / suppression
- policy binding
- temporal correctness
- Context Debt
- replay / reconstructibility
- information barriers
- classification / residency
- change control
- control ownership and second-line review

#### Data Environments

- Dataprep portable estate
- platform prerequisites
- restore
- verify
- reset
- troubleshooting
- per-example data dependencies

#### Security & Assurance

- security model
- threat model
- vulnerability-assessment methodology
- findings status
- remediation / retest
- secure deployment
- known limitations

Security claims apply only to named assessed SDK releases/commits.

#### Production Operations

- deployment
- configuration
- observability
- availability / degradation
- versioning and upgrades
- troubleshooting
- scaling / performance

Primary audiences: controls/governance, security, platform, operations, enterprise architect.

### 7. Adopt CCF

Purpose: help a team move from evaluation to a governed production program.

Includes:

- Is CCF appropriate for this problem?
- evaluation checklist
- first pilot
- 30-day path
- team roles and responsibilities
- SME + data engineer operating model
- AI-assisted specification workflow
- architecture decisions
- data readiness
- governance readiness
- production-readiness checklist
- evaluation → POC → pilot → production
- FAQ

Primary audiences: technology leaders, architects, program leads, governance partners.

---

## Why the primary navigation is smaller than the content model

The project contains distinct bodies of material such as the whitepaper, overview video, sample databases, Architecture & Patterns, Governance, Security, Operations, and the Adoption Guide. They remain distinct content types, but making each one a top-level navigation item would force a first-time visitor to understand our internal taxonomy before understanding CCF.

The seven primary destinations group those bodies around user intent:

- learn;
- build;
- look something up;
- see real use cases;
- govern/operate;
- adopt.

The whitepaper and overview video remain highly visible from Start Here and Learn CCF without becoming navigation dead ends.

---

## Persistent global elements

Every page should expose:

- global search;
- current documentation / SDK evidence baseline when technically relevant;
- breadcrumb;
- role / learning-path context when relevant;
- next recommended page;
- source / evidence link for authoritative claims;
- canonical / superseded status when relevant.

Technical pages should additionally expose maturity/status metadata without forcing casual readers to parse it.

---

## Cross-linking rules

1. Concept pages link to the smallest runnable tutorial that demonstrates the concept.
2. Tutorials link to the relevant reference entry rather than duplicating the API definition.
3. Financial Services pages link to the small SDK lessons for each mechanism they compose.
4. Financial Services pages link to their spec, Dataprep estate evidence, canonical example, tests/gates, and control evidence.
5. Reference pages link back to at least one explanatory tutorial or use case when one exists.
6. Governance pages link to real examples that exercise the control.
7. Data-environment pages list every example/tutorial that depends on that environment.
8. Superseded paths never appear as normal navigation targets; they are reachable only through historical/evidence context.

---

## Search model

Search should index by both technical term and user problem.

Examples:

- `Context Debt`, `D_c`, `incomplete context`
- `Decision Replay`, `reconstruct decision`
- `corporate family`, `ownership traversal`, `concentration`
- `MCP`, `LangGraph`, `Claude Agent SDK`, `ADK`
- `specification`, `SME`, `data engineer`
- `freshness`, `half-life`, `bitemporal`, `known_as_of`

Search results should visually distinguish:

- Concept
- Tutorial
- Reference
- Financial Services example
- Governance / control
- Data environment
- Adoption guidance

---

## Site-generator decision

Phase 2A does not lock the generator. MkDocs Material remains a strong candidate because the project is Markdown-heavy, search/navigation-intensive, Mermaid-friendly, and GitHub-native. The generator decision should be made during Phase 2C after the selected visual direction proves that the required page system and navigation can be implemented without fighting the framework.

---

## Phase 2A approval test

Approve this information architecture only if all of the following are true:

- a first-time evaluator can find the CCF story without understanding repo structure;
- a consumer developer can avoid assembler internals;
- an assembler can follow a decision/spec/data/assembly path;
- controls/governance has a first-class route and appears inside use cases;
- realistic Financial Services examples do not replace small SDK tutorials;
- whitepaper and video are prominent resources but not navigation dead ends;
- reference material remains versioned and separate from tutorials;
- data-estate setup is discoverable before tutorials that assume loaded data;
- security claims remain distinct from control-mechanism demonstrations.
