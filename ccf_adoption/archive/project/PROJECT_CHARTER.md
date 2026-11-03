# Project Charter — CCF Adoption

## Mission

Build `ccf_adoption` into the authoritative learning, implementation, assurance, and adoption environment for the Cognitive Context Fabric SDK, focused on financial-services use cases.

The outcome must be more than documentation. It should allow a technically sophisticated evaluator, developer, architect, control partner, or security reviewer to understand CCF, trust the evidence behind it, learn the SDK, reproduce examples, and form a credible path from evaluation to production adoption.

## Primary objectives

1. Explain what CCF is, why it exists, and where it fits in a modern financial-services architecture.
2. Teach developers how to consume Context Products without requiring them to understand how Context Products are assembled.
3. Teach assemblers how to construct Context Products over realistic multi-system data estates.
4. Provide an authoritative SDK reference grounded in executable implementation and tests.
5. Demonstrate CCF through realistic financial-services use cases with traceable lineage from business problem to data estate to executable example.
6. Make sample data environments reproducible by a third party.
7. Present governance, provenance, temporal correctness, entitlements, replay, Context Debt, security, and operational readiness as first-class adoption concerns.
8. Incorporate the planned CCF SDK vulnerability assessment and its remediation status into the assurance story.
9. Deliver a coherent, compelling product experience rather than a collection of unrelated files.

## Primary audiences

- **CCF evaluator** — wants to understand the problem, architecture, value proposition, and evidence quickly.
- **Context Product consumer** — an agent/application developer who wants to discover and consume a Context Product through in-memory, MCP, A2A, LangGraph, HTTP, or another supported surface.
- **Context Product assembler** — a developer/data engineer who integrates databases, lakehouses, graphs, streams, data products, policies, temporal semantics, provenance, and controls.
- **Enterprise / platform architect** — evaluates fit with the existing data and AI estate, integration model, deployment posture, and architectural boundaries.
- **Governance / risk / control reviewer** — evaluates provenance, policy enforcement, replay, auditability, temporal correctness, and controlled consumption.
- **Security reviewer** — evaluates trust boundaries, attack surface, secure deployment, vulnerability findings, remediation, and residual risk.
- **Adoption leader** — wants a credible path from evaluation to proof of concept, pilot, and production.

## Core product principles

### 1. Learn by task, reference by need

The primary learning experience is task-oriented. The Reference Manual is authoritative support, not the only way to learn.

### 2. Consumers and assemblers are different personas

A consumer should be able to use a Context Product without learning its construction. Assembly is a separate and more advanced skill path.

### 3. Simple SDK examples teach primitives; financial-services examples prove composition

`Using the SDK` uses deliberately small examples to teach individual capabilities. `Financial Services Use Cases` composes those capabilities into realistic solutions. Code should not be duplicated merely to satisfy both sections; the use cases should link back to the relevant SDK lessons.

### 4. Evidence beats assertion

Important adoption claims should trace to one or more authoritative sources: whitepaper source, use-case specification, engineered dataset, SDK implementation, tests, or executable example.

### 5. Reuse authoritative artifacts before recreating them

Where the `ccf` repository already contains appropriate Markdown, Mermaid diagrams, figures, graphics, or conceptual content, reuse or adapt those assets rather than extracting equivalent content from the PDF or redrawing it unnecessarily.

### 6. Architecture diagrams remain maintainable

Prefer source-controlled Mermaid, D2, Graphviz, or similarly maintainable diagrams for technical architecture. Generated imagery may be used selectively for conceptual or editorial presentation, but it must not replace auditable technical diagrams.

### 7. Financial-services credibility is first-class

Examples should explain the business decision, why conventional retrieval is insufficient, what context is required, how the data estate represents reality, what the SDK does, and what the example proves.

### 8. Security and assurance are part of adoption, not an appendix

The portal will reserve a first-class home for the security model, threat model, secure deployment guidance, vulnerability-assessment methodology, findings summary, remediation status, and residual risks.

## Hard repository boundary

The following repositories are **read-only evidence sources** for this project:

- `drcastillo/ccf`
- `drcastillo/obsidian-vault`
- `drcastillo/ccf_dataprep`
- `drcastillo/ccf_code`

ChatGPT Work must never create branches, commits, edits, merges, tags, releases, or pushes in those repositories.

`drcastillo/ccf_adoption` is the **only writable repository** for this project.

This rule applies even if the underlying GitHub connection exposes broader technical permissions.

## Non-goals

- Reimplementing or refactoring the SDK as part of the adoption project.
- Treating `ccf_adoption` as a new source of truth for SDK semantics.
- Rewriting the whitepaper in the adoption repo.
- Duplicating large amounts of example code merely to create documentation.
- Silently resolving contradictions between source repositories.
- Publishing unresolved vulnerability exploit detail that would materially increase risk.

## Definition of a compelling outcome

A successful release should allow a new technical user to answer, with evidence:

1. What is CCF and what problem does it solve?
2. How does it fit into an existing financial-services data and AI estate?
3. How do I consume a Context Product?
4. How do I assemble one?
5. What does the SDK actually expose and guarantee?
6. Can I run a realistic example myself?
7. Where did the example data and relationships come from?
8. How are provenance, policy, time, replay, and Context Debt governed?
9. How has the SDK been assessed for security and vulnerabilities?
10. What would it take to move from evaluation to production?

## Quality bar

Before release, the site should have:

- coherent navigation and learning paths;
- no knowingly broken internal links;
- runnable or explicitly qualified commands/examples;
- source traceability for substantive technical claims;
- aligned SDK and whitepaper versions;
- maintainable technical diagrams;
- reproducible sample-data setup where promised;
- documented security/assurance status;
- accessibility and responsive-layout review;
- a final Product Design / UX audit;
- an explicit release checkpoint approved by the architecture owner.
