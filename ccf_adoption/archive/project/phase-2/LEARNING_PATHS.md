# CCF Adoption Portal — Learning Paths

## Purpose

The portal should route people by the job they are trying to do. These paths are not personas for marketing; they are ordered learning journeys with clear exit criteria.

---

## Path A — Evaluate CCF

**Who:** technology executive, architect, innovation leader, product leader, technical evaluator.

**Question:** Is CCF relevant to the problems my organization has, and is it materially different from ordinary retrieval, data products, knowledge graphs, or agent frameworks?

**Route:**

1. Start Here — What is CCF?
2. Why Context Fails at Decision Time
3. Context Products
4. CCF Architecture in One View
5. Financial Services — one flagship use case
6. Governance & Controls — what is governed
7. Adopt CCF — evaluation checklist
8. Whitepaper / deeper architecture as desired

**Exit criteria:** the evaluator can explain the problem CCF solves, the role of a Context Product, why a heterogeneous governed context layer is different from a query/RAG call, and what a credible pilot would require.

---

## Path B — Consume a Context Product

**Who:** agent developer, application developer, workflow developer.

**Question:** How do I ask an existing Context Product for governed context without learning how it was assembled?

**Route:**

1. Context Product in five minutes
2. Consumer prerequisites / connection
3. `ProductClient`
4. Ask a product
5. Understand `Result`
6. Governed refusal vs transport error
7. Read Debt / lineage / replay metadata
8. Consume through MCP
9. Use from ADK / Claude Agent SDK / LangGraph
10. Reference entries as needed

**Avoid by default:** graph construction, source binding, operator composition, Control Plane authoring, assembler internals.

**Exit criteria:** a developer can call a product, interpret success/refusal, integrate it through the supported client/transport boundary, and know where to look when the contract or binding fails.

---

## Path C — Assemble a Context Product

**Who:** data engineer, Context Product assembler, applied AI/data platform engineer.

**Question:** How do I turn a real decision problem into a governed Context Product over a heterogeneous estate?

**Route:**

1. Start from the business decision
2. Work with the SME
3. Do we need a Context Product?
4. Restore and verify the Dataprep demonstration estate
5. Specification Standard
6. From business problem to approved spec
7. Bind data sources and measured reality
8. Build acquisition / graph / operator / projection stages
9. Apply temporal semantics, policy, provenance, and Debt
10. Bind request / payload / product contracts
11. Run gates / sabotage tests / replay
12. Expose through a supported door
13. Validate the example
14. Compare with a realistic Financial Services implementation

**AI role:** AI may draft, reconcile, check, and accelerate the specification after the SME and data engineer settle the intended assembly. AI does not invent missing business rules, sources, thresholds, control requirements, or data availability.

**Exit criteria:** the assembler can move from decision frame to approved spec to reproducible implementation without collapsing business authority, data authority, and SDK authority into one document.

---

## Path D — Architect CCF

**Who:** enterprise architect, data architect, AI platform architect, solution architect.

**Question:** Where does CCF sit in the enterprise, what does it own, and what does it deliberately not own?

**Route:**

1. Systems of Cognition
2. `G(E,R,T,P,Π,L)`
3. L1–L6 architecture
4. Control Plane / Data Plane
5. Layering, not replatforming
6. Consumer vs assembler boundary
7. Graph / operator / projection / product responsibilities
8. Deployment/configuration model
9. MCP / A2A / HTTP as transport bindings, not semantics
10. Data Environments
11. Governance & Controls
12. Production Operations
13. Reference Manual for exact surfaces

**Exit criteria:** the architect can place CCF alongside existing systems of record, lakehouse/data products, graphs, IAM/policy systems, agent frameworks, and runtime transports without assigning CCF responsibilities it does not own.

---

## Path E — Review Controls & Governance

**Who:** data governance, model governance, operational risk, compliance, second line, audit, control partner.

**Question:** What is governed, what evidence exists, where are the control boundaries, and what is not yet proven?

**Route:**

1. What a Context Product claims
2. Provenance / lineage
3. Temporal correctness / freshness
4. Entitlement / suppression / policy binding
5. Context Debt and incomplete context
6. Decision Replay / reconstructibility
7. Change and specification governance
8. Financial Services example — controls view
9. Data Reality & Deliberate Limitations
10. Security & Assurance boundary
11. Known limitations / deferred controls

**Explicit boundary:** the CP-00–12 ladder demonstrates control mechanisms but does not certify enterprise IAM integration, full MNPI-wall behavior, Mode 2/3 model-risk controls, security posture, or production resilience.

**Exit criteria:** the reviewer can identify the evidence required to reconstruct a decision, distinguish demonstrated mechanisms from institution-specific integrations, and identify the controls that must be assessed separately before production.

---

## Path F — Operate CCF

**Who:** platform engineer, SRE, infrastructure engineer, application operations.

**Question:** How do I stand up, configure, observe, troubleshoot, upgrade, and operate the environment?

**Route:**

1. Runtime / deployment model
2. Dataprep portable estate
3. Restore and verify
4. Configuration and secrets posture
5. Backends
6. Runtime doors / MCP / HTTP / peering
7. Observability
8. Failure / refusal / degradation semantics
9. Versioning / upgrade posture
10. Troubleshooting
11. Secure deployment
12. Production-readiness checklist

**Exit criteria:** the operator can distinguish source-estate health, CCF assembly/runtime health, governed refusal, transport failure, and unsupported configuration.

---

## Path G — Adopt CCF as a Team

**Who:** program lead, engineering manager, product owner, domain lead, architecture/governance leadership.

**Question:** How do we evaluate CCF responsibly and move from one use case to a repeatable operating model?

**Route:**

1. Evaluation checklist
2. Select one real decision problem
3. Identify SME, data engineer, consumer, controls partner, platform owner
4. Data readiness
5. Specification workflow
6. Build / validate one Context Product
7. Define evidence and control gates
8. Pilot
9. Production-readiness assessment
10. Operating model and ownership
11. Scale to a portfolio of products

**Exit criteria:** the team has a defined pilot, accountable roles, an evidence baseline, a spec-first workflow, data/control readiness, and explicit production gates.

---

## Learning-path routing rules

- A visitor may change paths without losing context; paths are views over shared content, not duplicated documents.
- Pages may belong to multiple paths, but have one canonical content location.
- A page should state `Recommended for` and `Prerequisites` when sequencing matters.
- Financial Services pages should offer persona tabs/sections rather than duplicate whole pages for SME, assembler, consumer, and controls readers.
- Search bypasses the learning path when the visitor already knows the term or API they need.
