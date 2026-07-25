---
phase: 01
reviewers: [gemini, ollama]
reviewed_at: 2026-07-25T07:40:00Z
plans_reviewed: [docs/SPEC_INVENTORY.md, docs/DECISIONS.md]
---

# Cross-AI Deliverable Review — Phase R

Reviewers attempted: gemini ✓, codex ✗ (auth expired), cursor ✗ (empty output twice), ollama/gpt-oss:120b-cloud ✓. Claude CLI skipped (self).

## Gemini Review

# Phase-Deliverable Review: CCF SDK, Phase R (Research)

The Phase R deliverable for the Cognitive Context Fabric (CCF) SDK is a comprehensive, high-fidelity translation of the authoritative whitepaper into a structured engineering inventory. It successfully moves beyond mere summary, providing a granular, field-by-field extraction of architectural commitments and invariants while rigorously surfacing implementation ambiguities that would otherwise pose significant downstream risk.

### Strengths
- **Exhaustive coverage:** Every primitive from whitepaper sections §5–§8 is captured with the mandatory seven-field schema, ensuring no commitment is lost in translation.
- **Structural Integrity:** The use of stable, chapter-scoped keys (INV-CHn-nn) and the partitioning of Chapter 7 ensures a scalable and collision-free identifier space for implementation.
- **Decision Rigor:** The identification of 41 unique Governance Decisions (D-NN) and the detailed mapping of "Load-Bearing Figures" to their specific mechanisms provides a clear audit trail for the SDK's design.
- **Triangulation Excellence:** The `homecams-patterns` appendix perfectly executes the mandate to distinguish between reusable "candidate patterns" and "domain-specific" values, protecting the SDK's generality.
- **Ambiguity Resolution:** `DECISIONS.md` effectively uses the "readings and consequences" framework to quantify the impact of whitepaper contradictions (e.g., D-IMPL-30, D-IMPL-31).
- **Pillar Mapping:** The cross-reference between inventory entries and the Five Common Pillars provides an immediate, actionable strategy for Phase D (Implementation).

### Concerns
- **MEDIUM: Contract Element Ambiguity (D-IMPL-30):** The internal inconsistency between 8 and 9 contract properties is a significant "fork in the road" for the core type surface. If the 9th element (Assembly Mode) is misplaced in the contract rather than the control plane, it could lead to leaky abstractions in the delivery layer.
- **MEDIUM: Single-Writer Realization (D-IMPL-41):** The whitepaper's assumption of a compiled/build-time enforcement for the single-writer invariant presents a challenge for a Python-based SDK. This is a HIGH-fidelity risk if the SDK cannot structurally prevent (rather than just conventionally avoid) illegal writes.
- **LOW: Fragmented D-NN Range:** The non-contiguous range of governance decisions (e.g., gaps like D-08, D-09) is well-documented but may complicate future audit automation that expects a sequential range.
- **LOW: TTL Derivation Rule (D-IMPL-31):** The lack of a specified derivation rule for product-level TTL from signal-level validity represents a minor logic gap that must be filled with an "opinionated" SDK default.

### Suggestions
- **Prioritize Language Choice (D-IMPL-01):** The resolution of the Single-Writer invariant (D-IMPL-41) is heavily dependent on the language target. Finalizing D-IMPL-01 should be the first act of Phase D.
- **Standardize the L1 Envelope (D-IMPL-33):** Early in Phase D, define a canonical `EventEnvelope` that reconciles the prose description with Homecams' `EnrichableObserverEvent` to ensure consistent ingestion.
- **Automated Invariant Testing:** Use the "Named Architectural Invariants" table as a direct checklist for a CI-based "Architecture Guard" suite to prevent regressions of the fabric's core constraints.

### Overall Risk: LOW
The deliverable is remarkably thorough. By surfacing 22 new implementation decisions (D-IMPL-30..51) and mapping them back to specific whitepaper contradictions, the research phase has effectively "de-risked" the implementation by identifying the boundaries where the developer must provide opinionated logic. The project is ready to proceed to Phase D.

---

## Ollama Review (gpt-oss:120b-cloud)

**Review – Phase R Deliverable `docs/SPEC_INVENTORY.md` (CCF SDK v0)**  

---

### 1️⃣ Summary  

`SPEC_INVENTORY.md` is a full‐blown inventory of the Cognitive Context Fabric (CCF) specification extracted from the proprietary white‑paper. It lists an entry for **every primitive** in Chapters 5‑8, each entry containing the seven required fields (section, paraphrased commitment, type signature, invariants, dependencies, figure refs, open‑question field). Cross‑cutting sections are present (governance decisions, load‑bearing figures, named invariants, SDK extensions, pillar mapping, **homecams‑patterns** appendix). All open‑question entries carry a `D‑IMPL‑NN` identifier that matches the decision log in `docs/DECISIONS.md`. No domain‑specific constants from the reference implementation are inherited as normative values.

Overall the document meets **all verification criteria** and is internally consistent: keys are stable, cross‑references resolve, and the required supplemental artifacts are included.

---

### 2️⃣ Strengths  

- **Complete coverage** – Every white‑paper section §5‑§8 (36 subsections) is covered by at least one inventory entry; no missing primitive was detected.  
- **Correct structure** – Each entry has the mandated seven fields, and the *Open‑question* field is always present (explicit “none” where appropriate).  
- **Stable key scheme** – Keys are chapter‑scoped (`INV‑CH5‑NN`, `INV‑CH6‑NN`, `INV‑CH7‑NN`, `INV‑CH8‑NN`) and the sub‑partitioning for Chapter 7 (01‑39, 40‑69, 70+) prevents collisions.  
- **Cross‑cutting sections** – Governance decisions (`D‑NN` table), load‑bearing figure catalogue, named invariants list, SDK‑extension mapping, pillar‑by‑pillar mapping, and the extensive **homecams‑patterns** appendix are all present and correctly formatted.  
- **Open‑question surfacing** – All open‑issues are enumerated with `D‑IMPL‑NN` numbers; they are traceable to `DECISIONS.md`.  
- **No hard‑coded domain values** – Numerical thresholds (e.g., similarity = 0.85) are clearly marked as *illustrative* and are not treated as normative SDK defaults.  
- **Consistent dependencies** – Every entry’s `Dependencies` field correctly points to other inventory items, figures, or white‑paper sections, aiding traceability.  
- **Invariants catalogued** – All named architectural invariants from the white‑paper (single‑writer, composition‑preservation, three validation gates, algorithmic ⇄ semantic alternation, audit‑by‑construction, no‑hard‑coding, zero‑harness‑imports) are listed with their originating sections.  

---

### 3️⃣ Concerns  

| # | Concern | Severity | Why it matters |
|---|---------|----------|----------------|
| C‑1 | **Illustrative numeric values** – A handful of entries (e.g., similarity thresholds 0.85/0.75, cost‑band multipliers, TTL examples) appear as concrete numbers. While the document labels them “illustrative”, the surrounding prose does not explicitly call them non‑normative, which could be mis‑interpreted as a SDK default. | MEDIUM | Risk of inadvertent code generation that hard‑codes these numbers, violating the **No‑Hardcoding** invariant. |
| C‑2 | **Duplicate D‑IMPL number reference** – The white‑paper’s “Phase 12 D‑05/06/07/10” appear as separate Phase‑R open‑questions (`D‑IMPL‑30`‑`33`). No conflict, but the naming could be confused with the original D‑05/D‑06/D‑07/D‑10 decisions. | LOW | Potential confusion for downstream reviewers; could be clarified with a note that Phase‑R re‑uses the same identifiers for a different purpose. |
| C‑3 | **Missing explicit “Domain‑specific — do‑not‑inherit” marker for a few homecams patterns** – Most patterns are labelled, but the *“Normalized enrichable‑event contract”* row only has “candidate pattern”. The white‑paper does not prescribe a concrete schema, so it should be marked **do‑not‑inherit** to avoid treating it as a required SDK contract. | LOW | Clarifies that the envelope schema is a data point, not a mandatory SDK type. |
| C‑4 | **Figure catalogue includes non‑load‑bearing figures** – The “Load‑bearing Figures” table lists **all** figures (50). The verification criteria ask for *load‑bearing* figures only. Including purely illustrative diagrams (e.g., motivation figures) inflates the list. | LOW | Minor mismatch with the spec; does not affect functionality but could be cleaned up. |

No *HIGH*‑severity issues (i.e., missing required entries, violated invariants, or hidden decisions) were found.

---

### 4️⃣ Suggestions  

1. **Explicitly qualify illustrative numbers** – Add a brief parenthetical note to every numeric example (e.g., “(illustrative, not a default)”) or move them to a separate “Illustrative examples” subsection. This reinforces the **No‑Hardcoding** rule.  
2. **Clarify D‑IMPL numbering** – Insert a short footnote near the first Phase‑R open‑question entries stating that `D‑IMPL‑30`‑`33` are new Phase‑R identifiers and are distinct from the original `D‑05`‑`D‑10` decisions.  
3. **Mark the event‑envelope pattern as “do‑not‑inherit”** – In the homecams‑patterns table, change the marker for the *“Normalized enrichable‑event contract”* row to **domain‑specific — do not inherit** (or add a note that the shape is a data point only).  
4. **Trim the Load‑bearing Figures list** – Retain only figures that the white‑paper explicitly calls *load‑bearing* (e.g., those that commit a mechanism or invariant). Remove purely motivational figures; optionally keep a separate “All Figures” appendix for reference.  
5. **Add a cross‑reference matrix** – A small table that maps each `D‑NN` governance decision to the inventory entries that rely on it would make traceability even easier for Phase D.  

---

### 5️⃣ Overall Risk  

**LOW** – The deliverable satisfies the Phase R requirements, contains no critical omissions, and the few minor issues can be resolved trivially without impacting downstream design. The inventory is ready for Phase D review after the suggested polish.  

---

## Consensus Summary

### Agreed Strengths
- Exhaustive §5–§8 coverage with seven-field entries and stable chapter-scoped keys
- Open questions properly surfaced as D-IMPL-NN decisions rather than silently resolved
- Homecams appendix correctly separates candidate patterns from do-not-inherit domain values

### Agreed Concerns (all triaged advisory — see review-triage.md)
- D-IMPL-30 (8-vs-9 contract elements) and D-IMPL-41 (single-writer enforcement mechanism) are the highest-leverage open decisions for Phase D — both already surfaced and numbered
- Illustrative numeric values in entries should be explicitly qualified non-normative to protect the No-Hardcoding rule

### Divergent Views
- Ollama suggests trimming the Load-Bearing Figures list to strictly load-bearing figures; Gemini raised no such concern. Carried as advisory.
