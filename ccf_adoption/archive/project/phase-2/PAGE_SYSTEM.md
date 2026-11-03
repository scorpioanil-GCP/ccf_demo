# CCF Adoption Portal — Page System

## Purpose

This document defines the minimum reusable page types and evidence components the portal needs. Phase 2B may change the visual treatment, but it should not erase these information requirements.

---

## 1. Start / landing page

Purpose: explain CCF quickly and route visitors by intent.

Required modules:

- concise CCF value proposition;
- architecture/hero visual;
- `Choose your path` routing;
- overview video;
- whitepaper access;
- flagship Financial Services example;
- core concepts;
- SDK quick entry;
- governance / enterprise-readiness entry;
- current release / documentation baseline indicator.

Do not make the home page a chronological news feed or a repository index.

---

## 2. Concept page

Purpose: explain one CCF concept without requiring code.

Examples: Context Product, Context Debt, Context Half-life, Decision Replay, Projection, L1–L6 architecture.

Required shape:

1. concept in one sentence;
2. problem it solves;
3. conceptual model / diagram;
4. important distinctions / non-goals;
5. small example;
6. where it appears in the SDK;
7. related Financial Services examples;
8. source evidence / whitepaper lineage;
9. next recommended page.

---

## 3. Tutorial page

Purpose: teach a task with minimal conceptual overhead.

Required metadata:

- audience;
- estimated setup level (`none`, `client only`, `portable estate`, `advanced runtime`);
- prerequisites;
- SDK evidence baseline;
- capability maturity where relevant;
- expected result.

Required shape:

1. what you will accomplish;
2. prerequisites;
3. setup;
4. code/config steps;
5. expected output;
6. what just happened;
7. common failure modes;
8. cleanup / next step;
9. links to reference entries.

Tutorials should not duplicate API reference tables.

---

## 4. Reference page

Purpose: provide exact, version-pinned implementation facts.

Required metadata:

- source repository / path;
- evidence commit;
- maturity classification;
- public / advanced / internal status;
- first known supporting examples/tests;
- supersession status if applicable.

Required shape:

1. purpose;
2. public surface / signature / schema;
3. parameters / fields;
4. return / result semantics;
5. errors / governed refusal behavior;
6. lifecycle / invariants;
7. configuration;
8. concise example;
9. tests/examples that prove behavior;
10. related tutorial/concept links.

Do not present `INTERNAL` surfaces as ordinary adopter APIs.

---

## 5. Financial Services use-case page

Purpose: explain a real decision problem and then show how CCF solves it.

This page type is deliberately business-first.

Required top metadata:

- use-case title;
- domain;
- business decision;
- tier / assembly mode;
- canonical example;
- required data estate;
- SDK evidence baseline;
- difficulty;
- personas;
- control domains exercised.

Required narrative order:

1. **Business Problem**
2. **Decision & Personas**
3. **Why Conventional Retrieval / Data Products Are Insufficient**
4. **Business / Risk / Control Consequence**
5. **Context Required**
6. **How This Example Was Formed** — Whitepaper → Vault → Dataprep → SDK spec/example
7. **Data Reality & Deliberate Limitations**
8. **Context Product Specification**
9. **Assembly Architecture**
10. **Control & Governance View**
11. **Implementation Walkthrough**
12. **Run It / Expected Result**
13. **What the Example Proves**
14. **What It Does Not Prove**
15. **Evidence & Lineage**

Required reusable callouts:

- `Business decision`
- `Counterfactual failure`
- `Data reality`
- `Control demonstrated`
- `Boundary / not proven`
- `Known limitation`
- `Canonical implementation`
- `Evidence baseline`

These callouts must remain visually distinguishable from ordinary prose.

---

## 6. Governance / control page

Purpose: explain one control domain and show where it is evidenced.

Examples: provenance, entitlement/suppression, temporal correctness, Context Debt, Decision Replay, invalidation.

Required shape:

1. control objective;
2. failure being prevented;
3. CCF mechanism;
4. evidence produced;
5. where enforced;
6. example(s) that demonstrate it;
7. control boundary / what is not proven;
8. institution-specific integration responsibilities;
9. assurance/testing considerations.

A control page must distinguish mechanism evidence from enterprise certification.

---

## 7. Data-environment page

Purpose: make a reproducible environment available to tutorials/examples.

Required shape:

1. what this environment contains;
2. why it exists;
3. provenance / public vs engineered content;
4. prerequisites;
5. install;
6. restore;
7. verify;
8. reset;
9. troubleshooting;
10. examples that depend on it;
11. version / snapshot identity.

The Dataprep portable estate is the canonical full assembler environment.

---

## 8. Adoption-guide page

Purpose: help a team make a decision or execute a stage of adoption.

Examples: evaluation checklist, select a pilot, team roles, spec workflow, production readiness.

Required shape:

1. objective;
2. entry criteria;
3. people involved;
4. activities;
5. artifacts/evidence produced;
6. decision gate;
7. exit criteria;
8. next stage.

---

## 9. Security / assurance page

Purpose: make security claims precise and release-specific.

Required metadata:

- assessed SDK release/commit;
- assessment date;
- scope;
- methodology/version;
- status.

Required shape varies by security-model, threat-model, methodology, findings-summary, remediation, secure-deployment, or known-limitations page, but no security page may imply that CP-ladder control evidence is itself a vulnerability assessment.

---

## Global evidence components

### Evidence Baseline

Shows the exact source commit/release supporting technical claims.

### Maturity Badge

One of:

- STABILIZED
- VALIDATED-CURRENT
- PROVISIONAL
- INTERNAL
- DEPRECATED / SUPERSEDED

### Canonical / Historical

Used where multiple paths exist. CP-04 must show canonical-only navigation.

### Data Reality

Four standard labels:

- Public
- Synthetic — internal
- Synthetic — engineered
- Derived

### Control Demonstrated

States the mechanism actually exercised.

### Boundary / Not Proven

States the adjacent claim the evidence does not support.

### Source Trail

Links the adoption claim back to the authoritative evidence chain.

---

## Responsive / accessibility requirements for Phase 2B/2C

The design direction must accommodate:

- dense technical pages without relying on tiny text;
- keyboard-accessible navigation;
- code blocks that remain readable on small screens;
- diagrams with textual explanations / accessible alternatives;
- callouts that do not depend on color alone;
- tables that degrade gracefully on narrow screens;
- persistent but non-intrusive evidence metadata;
- clear distinction among tutorial steps, evidence, warnings, and business narrative.

---

## Content duplication rule

One fact should have one canonical explanatory home whenever possible.

- Concepts explain meaning.
- Tutorials explain how to do a task.
- Reference explains exact interfaces.
- Financial Services examples show composition in a real problem.
- Governance pages explain control intent and evidence.
- Data Environment pages explain reproducibility.

Other pages link back instead of copying entire sections.
