# Phased Execution Plan

Every phase ends in an explicit human-in-the-loop checkpoint. Complex phases include internal checkpoints so work cannot run far past an unvalidated assumption.

## Phase 0 — Project Constitution & Source Model

**Purpose:** establish mission, audiences, repository boundaries, source hierarchy, quality bar, and checkpoint discipline.

**Outputs:**

- project charter;
- source model and provenance rules;
- phased plan;
- checkpoint protocol.

**Checkpoint 0:** Project Constitution Approval.

---

## Phase 1 — Evidence & Asset Inventory

**Purpose:** map the four read-only source repositories before writing authoritative adoption content.

### 1A — CCF / whitepaper inventory

Inventory structured whitepaper Markdown, Mermaid diagrams, static graphics, conceptual vocabulary, architecture material, and reusable assets.

**Internal checkpoint 1A:** approve the CCF concept/asset inventory and reuse candidates.

### 1B — SDK inventory

Inventory public SDK surface, configuration, docs, tests, and examples. Separate consumer-facing from assembler-facing capabilities.

**Internal checkpoint 1B:** approve the SDK capability map.

### 1C — Use-case and data lineage

Map Vault use cases to `ccf_dataprep` datasets/relationships and `ccf_code` executable examples.

**Internal checkpoint 1C:** approve the Vault → Dataprep → SDK example lineage.

**Checkpoint 1:** Evidence Map Approval.

---

## Phase 2 — Information Architecture & Product UX

**Purpose:** define the adoption portal as a product before scaling content.

### 2A — Information architecture

Define site map, learning paths, hierarchy, search/navigation behavior, cross-linking, and page types.

**Internal checkpoint 2A:** approve information architecture and learning paths.

### 2B — Visual directions

In ChatGPT Work, use Product Design to create three materially different visual directions for the portal.

**Internal checkpoint 2B:** select one visual direction.

### 2C — Prototype

Prototype enough of the selected direction to demonstrate the landing page, navigation, article/reference page, SDK tutorial, and financial-services use case.

**Internal checkpoint 2C:** approve the prototype and reusable page system.

**Checkpoint 2:** Experience Approval.

---

## Phase 3 — Start Here / CCF Story

**Purpose:** build the front door into CCF.

**Scope:** CCF introduction, NotebookLM video, whitepaper, executive explanation, architecture overview, why CCF, where CCF fits, and routing into the learning paths.

Reuse `ccf` Markdown, Mermaid, figures, and graphics where appropriate.

**Checkpoint 3:** CCF Story Approval — a technically sophisticated newcomer should understand what CCF is, why it exists, and where to go next.

---

## Phase 4 — Using the SDK

**Purpose:** teach SDK skills with intentionally simple examples before introducing financial-services complexity.

### 4A — Consumer path

Install, discover, request, interpret, refuse, and consume Context Products through supported consumption surfaces.

**Internal checkpoint 4A:** consumer can succeed without learning assembly.

### 4B — Assembler path

Define, source, resolve, relate, govern, apply temporal semantics/provenance/Context Debt, publish, and test a Context Product.

**Internal checkpoint 4B:** assembly mental model and progression approved.

### 4C — Progressive tutorial

Build one small Context Product end to end using minimal domain complexity.

**Internal checkpoint 4C:** a new engineer can follow and reproduce the tutorial.

### 4D — Advanced SDK concepts

Multiple backends, orchestration, lifecycle, debugging, and advanced patterns.

**Checkpoint 4:** Using-the-SDK Release Candidate.

---

## Phase 5 — SDK Reference Manual

**Purpose:** create authoritative reference material grounded in `ccf_code` implementation and tests.

### 5A — Core models and contracts
### 5B — Context Product assembly
### 5C — Resolution, graph, and temporal semantics
### 5D — Policy, provenance, and Context Debt
### 5E — Consumption and transports
### 5F — Configuration and operations

Each internal checkpoint includes a coverage matrix for public surfaces, documentation, tests, and examples.

**Checkpoint 5:** Reference Manual Approval.

---

## Phase 6 — Financial Services Use Cases

**Purpose:** demonstrate composition of SDK capabilities in realistic financial-services scenarios.

Each use case should cover: business problem; decision supported; why conventional retrieval is insufficient; required context; data estate; Context Product design; SDK capabilities; architecture; how to run; expected result; what it proves; governance/controls; source lineage.

### 6A — Flagship use case

Take one use case completely through the final pattern.

**Internal checkpoint 6A:** approve template, evidence depth, and UX.

### 6B — First use-case family

Scale the approved pattern across one coherent domain family.

**Internal checkpoint 6B:** approve family-level organization.

### 6C — Remaining use cases

Scale the proven pattern.

**Checkpoint 6:** Financial Services Portfolio Approval.

---

## Phase 7 — Sample Data Environments

**Purpose:** make the example estates reproducible.

For each relevant technology: prerequisites, installation, configuration, load, validation, reset, troubleshooting, and consuming examples.

### 7A — One complete database environment

**Internal checkpoint 7A:** zero-to-validated setup reproduced.

### 7B — One multi-database example estate

**Internal checkpoint 7B:** cross-store example setup reproduced.

**Checkpoint 7:** Reproducibility Approval.

---

## Phase 8 — Governance, Security & Production

### 8A — Governance & Controls

Provenance, entitlements, temporal correctness, replay, auditability, Context Debt, policy.

### 8B — Security model

Threat model, trust boundaries, secure configuration, credentials/secrets posture, attack surfaces.

### 8C — Vulnerability assessment

Reserve the publication structure before assessment begins. When completed, publish the approved scope, methodology, SDK version, severity summary, remediation/retest status, and residual-risk statement. Do not publish unsafe exploit detail for unresolved vulnerabilities.

### 8D — Production operations

Deployment, observability, scaling, troubleshooting, upgrades, operational patterns.

**Checkpoint 8:** Enterprise Readiness Review.

---

## Phase 9 — Adoption & Release

**Purpose:** turn the material into a credible institutional adoption path and validate the complete product.

### 9A — Adoption path

Evaluation → proof of concept → pilot → production readiness; team roles, skills, decision points, FAQs, glossary.

### 9B — Content freeze

Resolve known content gaps and freeze substantive release content.

### 9C — UX / Product Design audit

Review navigation, comprehension, accessibility, responsive behavior, and product cohesion.

### 9D — Technical verification

Validate links, search, code/commands, diagram rendering, asset integrity, source traceability, whitepaper/SDK alignment, and example/data lineage.

**Checkpoint 9:** Release Approval.
