# Phase 1C — Financial Services lineage model

## Purpose

Phase 1C establishes the evidence chain behind every Financial Services example. The adoption portal must be able to explain not only how an example runs, but why it exists, what data reality supports it, what was deliberately engineered, what the SDK implementation proves, and what controls/governance reviewers should examine.

The evidence chain is:

`whitepaper concept / use case → Vault decision frame → Dataprep data reality → SDK implementation spec → SDK example/tests → adoption narrative`

No source in that chain replaces another. Each owns a different term.

## Authority by question

| Question | Primary authority | What it owns |
|---|---|---|
| Why does this product exist? | `obsidian-vault` | Business problem, decision, trigger, principals, counterfactual failure, implementation-independent scope and prerequisites |
| What data actually exists? | `ccf_dataprep` | Public sources, engineered elements, store placement, measured coverage, limitations, known issues, source and extraction caveats |
| How is this product built on the current SDK? | `ccf_code` implementation spec + example | Concrete source bindings, request surface, operator path, projection, debt/freshness, gates, replay, runtime behavior and current canonical implementation shape |
| What should an adopter learn and do? | `ccf_adoption` | Learning narrative, persona routing, traceability, reproduction guidance, controls/governance lens and explicit statement of what the example proves/does not prove |

## Spec-first operating model

The specification is a primary engineering artifact, not a documentation by-product.

1. The **SME and data engineer** agree the business decision and proposed assembly approach.
2. AI tooling may help structure, draft, cross-check and pressure-test the specification.
3. AI must not invent missing source systems, policy values, thresholds, scope boundaries, or business facts. Unknowns stay explicit.
4. The implementation specification is approved before engineering begins, except where a historical example is explicitly disclosed as retrospective.
5. If the build disproves an approved substantive term, that is a deviation to resolve, not permission to silently edit the approved design.

The adoption portal should teach AI as an accelerator of specification quality after human agreement on the problem and assembly approach—not as the authority that chooses the business problem.

## Required lineage record per Financial Services example

Every approved example lineage entry must contain these sections.

### 1. Identity and release state

- CP number and canonical example path
- Context Product registry name and version where applicable
- tier / assembly mode
- pinned source commits
- approved / current / work-in-progress status
- canonical vs historical/superseded paths

### 2. Business problem first

Before architecture or code:

- business problem
- decision being made
- trigger
- business/domain personas
- control/governance personas
- counterfactual: what ordinary retrieval/data-product logic gets wrong
- consequence of getting the frame wrong
- why this warrants a Context Product

The narrative should originate in the Vault/whitepaper lineage. Engineering follows the problem statement; it does not define it retroactively.

### 3. Specification lineage

- Vault implementation-independent specification
- SDK implementation specification
- applicable specification standard/template
- differences between the two specification levels
- Gate-1 / Gate-2 status where available
- known retrospective-spec disclosures
- unresolved `[TBC]` items or source disagreements

### 4. Data reality

Classify every material input or condition as:

- **public observed** — sourced from a public authoritative or documented source
- **derived** — deterministically computed from observed inputs
- **synthetic — internal** — invented to stand in for non-public institutional data
- **synthetic — engineered** — deliberately introduced to exercise a required condition or failure mode
- **synthetic — bridging** — identifier/entity/relationship needed to join public sources where the source does not provide a common key
- **unavailable / deferred** — required by the ideal product but absent from the public estate or intentionally not implemented

For each limitation record:

- why the limitation exists
- where it is documented
- whether it is a data limitation, extraction limitation, licensing boundary, or SDK limitation
- how it affects the example
- what the example still proves despite it
- what the example must not claim to prove

A deliberate public-data limitation must never be presented as an SDK defect unless evidence says it is one.

### 5. Assembly / implementation evidence

- concrete source/store bindings
- request surface
- assembly/operator path
- projection/perspective behavior
- freshness / half-life / Context Debt behavior
- product gates and example-specific tests
- replay / lineage behavior
- run command(s)
- canonical implementation path

### 6. Controls & governance lens

Controls/governance is a first-class persona, not an appendix. For each example identify which of the following actually apply:

- policy-at-construction / entitlement
- data classification / residency / information barriers
- source authority and provenance
- temporal correctness and stale-data behavior
- Context Debt / fail-closed or refusal behavior
- deterministic vs semantic stages
- model-risk controls for Assembly Mode 2/3
- Decision Replay and auditability
- change/version governance
- specification approval and deviation control
- read-only source-system posture / separation of duties

Do not fabricate a control just to fill a template. State `not applicable` or `not demonstrated` when evidence does not support it.

### 7. What the example proves / does not prove

Each example ends with two explicit lists:

**Proves** — mechanisms demonstrated by executable evidence.

**Does not prove** — limitations, missing production data, untested scale, vendor-specific assumptions, or other boundaries.

## Persona set for Financial Services examples

At minimum route content for:

- business/domain SME
- data engineer / Context Product assembler
- agent/application developer consuming the product
- controls / governance / second-line reviewer
- platform / operations engineer
- model-risk reviewer when a model is in the trust path

Not every persona needs equal depth on every page, but the controls/governance path must always be visible.

## Phase 1C internal checkpoints

### 1C.1 — Lineage contract + canonical exemplar

Define this model and prove it against one example end-to-end. Canonical CP-04 is the exemplar.

### 1C.2 — Approved ladder mapping

Apply the approved 1C.1 shape across CP-00 through CP-12. CP-04 always means `examples/cp-04-canonical-corporate-family-tree`.

### 1C.3 — Gap and controls review

Review the mapped set for:

- missing Vault → Dataprep → Spec → SDK links
- public vs engineered-data ambiguity
- unacknowledged limitations
- missing controls/governance persona treatment
- stale spec-standard references
- work-in-progress examples accidentally treated as released

Only after 1C.3 is approved does the Phase 1 evidence map become the basis for site architecture and use-case production.
