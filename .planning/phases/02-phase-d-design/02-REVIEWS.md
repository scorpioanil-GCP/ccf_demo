---
phase: 2
reviewers: [gemini, ollama, codex]
reviewers_failed: [cursor (not logged in), claude (skipped — self)]
codex_note: initial runs failed (revoked ChatGPT auth, then quota); succeeded 2026-07-25 after CODEX_API_KEY re-login + billing fix
reviewed_at: 2026-07-25T17:52:13Z
scope: Phase D deliverables (docs/DESIGN.md, docs/DECISIONS.md, docs/diagrams/*.mmd) reviewed against CLAUDE.md §3.1 Phase D verification criteria
---

# Cross-AI Review — Phase 2 (Phase D — Design)

## Gemini Review

I will start by verifying that the design deliverables mentioned in the request exist in the workspace and match the provided content.

I will read `docs/SPEC_INVENTORY.md` to verify that the 126 entries mentioned in the traceability matrix match the actual requirements and check for any gaps in the design.

I will read `docs/SPEC_INVENTORY.md` to verify the inventory entries and ensure the design's traceability matrix is comprehensive.

The CCF SDK Phase 2 (Design) deliverables—comprising `docs/DESIGN.md`, `docs/DECISIONS.md`, and 11 architectural diagrams—represent an exceptionally rigorous, high-fidelity translation of the Cognitive Context Fabric whitepaper into a viable software architecture. The design effectively navigates the "mechanism vs. values" discipline, ensuring that domain-specific logic, thresholds, and prompts are externalized to the Control Plane.

### Summary
The design deliverables are **complete and highly compliant** with the Phase D verification criteria. Every one of the 126 inventory entries is accounted for through mapping or explicit deferral, and all 50 `D-IMPL` decisions are resolved. The design is maintained strictly at the contract altitude, focusing on protocols, type signatures, and seams without leaking implementation code. The structural arguments for the seven named invariants are particularly robust, providing multi-layered enforcement strategies (Protocol splits, DI, and CI lints) that compensate for target-language limitations.

### Strengths
- **Robust Invariant Preservation:** The "Single-Writer" enforcement stack (D-IMPL-41) is a standout design element, combining interface splits, DI-at-boot, and CI-enforced import lints to ensure graph integrity.
- **High-Fidelity Traceability:** The 126-row traceability matrix and the granular citation of `D-IMPL` rulings in every section create a transparent and audit-ready architecture.
- **Clean Seam Architecture:** The `HarnessAdapterProtocol` (4 mandatory/conditional seams) and the ArtifactStore/GraphStore split (based on mutability) provide a highly decoupled framework that ensures harness neutrality and single-writer safety.
- **Forensic-Grade Replay:** The five-dimension Decision Replay design—incorporating bitemporal T-axis support, content-addressed snapshots, and `HumanPrincipalBinding` for HITL—is architecturally sound and preserves whitepaper fidelity.

### Concerns
- **Replay Re-hydration Fragility (MEDIUM):** The strategy for cold-archive re-hydration (D-IMPL-44) relies on bit-for-bit reconstruction from archived source signals. Even minor perturbations in upstream signal formats or L2 ingestion logic could render compressed records non-reproducible.
- **Control Plane Centralization (LOW):** The v0 design places extreme weight on the "in-process versioned registry" for the Control Plane. While appropriate for v0, this centralization creates a potential bottleneck for multi-tenant production scaling.
- **Lint Dependency (LOW):** The integrity of core invariants (No-Hardcoding, Alternation, Zero-Harness-Imports) depends heavily on the implementation of custom CI lints (CINV-01..04). Any failure or bypass of these lints could erode the architectural guarantees.

### Suggestions
- **Re-hydration Validation Strategy:** In Phase F (Feasibility), include a specific test strategy for verifying the re-hydration of compressed records against their content hashes to detect signal or logic drift early.
- **Standardized Error Handling in CAR:** For the Conditional Assessment Routing (CAR), specify a standardized "Debt-Breach" exception schema to ensure that Fail-Closed events carry consistent diagnostic metadata for HITL actors.
- **Developer Identity Provider:** Explicitly specify a "Dev/Mock" implementation of the `IdentityProvider` (D-IMPL-15/21) to simplify the implementation of the Example-00 through Example-02 dev-mode suite.

### Risk Assessment: LOW
The design is structurally sound and adheres strictly to the whitepaper’s primitive set and naming conventions. The use of structural typing and Protocol-based seams ensures the SDK remains general-purpose and harness-neutral. The high level of detail in invariant enforcement significantly reduces the risk of architectural drift during the Implementation phase.

**Verdict: Approved. Phase D is complete.**

---

## Ollama Review (gpt-oss:120b-cloud)

**Review of Phase D – DESIGN Deliverables (CCF SDK v0)**  

### 1. Summary  
The DESIGN document presents a complete, contract‑level architecture for the CCF SDK that maps every one of the 126 inventory entries, resolves all 49 open D‑IMPL decisions, and supplies the required seven diagrams (five pillar diagrams plus the two seam diagrams) together with supporting sequence diagrams.  All seven named architectural invariants are argued structurally, linked to explicit enforcement points (CI lints, DI/boot checks, replay‑by‑construction, Control‑Plane validation, etc.).  The design stays strictly at the level of responsibilities, protocol signatures, invariants and seams – no implementation code appears – and no domain‑specific numeric values are baked into the SDK (they are all declared as Control‑Plane configuration).  Overall the deliverable meets the Phase D verification criteria, with the only notable open‑question being the provisional status of D‑IMPL‑10.

---

### 2. Strengths  

- **Complete traceability** – Appendix A lists all 126 inventory entries, with only two legitimate deferrals (Supervision Quality & Conversational Reporting) that are explicitly documented.  
- **Decision resolution** – All D‑IMPL‑01 … ‑29 decisions are marked **RESOLVED** (approved by Dave, 2026‑07‑25). The only “provisional” entry (D‑IMPL‑10) is noted with its reasoning, and the decision‑log cross‑references are consistent.  
- **Diagram coverage** – The required five pillar diagrams plus the Harness‑Adapter and ArtifactStore seam diagrams are present, and the auxiliary sequence diagrams illustrate the critical runtime flows (single‑writer write path, A2A admission, HITL suspend/resume, replay reconstruction).  
- **Invariant‑by‑construction arguments** – Each of the seven invariants has a dedicated structural argument, an enforcement point, and a diagram reference.  For example, single‑writer enforcement is guaranteed by the `GraphReader`/`GraphWriter` split, DI‑at‑boot injection, a mypy import‑lint, and a runtime token back‑stop.  
- **Mechanism‑vs‑Values discipline** – All thresholds, TTLs, λ₍c₎, D₍c₎, etc., are declared as Control‑Plane artifacts (via D‑IMPL‑38, ‑39, ‑40, ‑47) with no SDK‑side defaults.  Illustrative numbers are explicitly marked as examples.  
- **No‑hard‑coding and zero‑harness‑imports** – The design includes CI lints (`@algorithmic`, `zero‑harness‑import`) and a clear seam‑boundary (harness adapters live under `/runtime/adapters/`).  
- **Extensibility zones** – The SDK‑defined extensions (Agent Specialisation Framework, Orchestration primitive, HITL primitives, Experience Layer) are cleanly separated from the white‑paper primitives and are labelled as such throughout.  

---

### 3. Concerns  

| # | Concern | Severity | Why it matters |
|---|----------|----------|----------------|
| **C‑1** | **D‑IMPL‑10 remains “provisionally resolved”** (monorepo shape) rather than a final resolution. | **HIGH** | Phase D verification requires *every* open D‑IMPL‑NN decision to be **resolved** (or explicitly flagged as gating). A provisional ruling does not satisfy the criterion and leaves the repo‑layout decision unsettled for downstream phases. |
| **C‑2** | **Reliance on Python‑type‑system for single‑writer enforcement** (D‑IMPL‑41). The document notes a “honest residual claim” that Python cannot guarantee impossible evasion. | **MEDIUM** | The invariant *Single‑writer* is a core architectural guarantee. While the structural argument (split interfaces, DI, import‑lint) is sound, the lack of a language‑level enforcement could be considered a weakness if the governance board expects a provably impossible violation. |
| **C‑3** | **Three‑validation‑gate enforcement** relies on runtime checks (TTL vs MAX_TTL, lineage equality) but no static/compile‑time guarantee is provided. | **LOW** | The invariant is still enforced at the product‑creation boundary, but the design does not include a structural static guarantee (e.g., type‑level constraint) – acceptable but worth noting. |
| **C‑4** | **Illustrative numeric examples** (e.g., thresholds 0.85/0.75, TTL 300 ms) appear in the text. Although flagged as examples, they could be mistaken for SDK defaults. | **LOW** | Potential for misinterpretation by downstream implementers; a brief note in the design header could reinforce that these numbers are *not* SDK values. |
| **C‑5** | **Deferral of Supervision Quality (INV‑CH8‑19) and Conversational Reporting (INV‑CH8‑21)** – while permitted, the design does not provide a concrete migration path. | **LOW** | Not a verification failure, but future phases will need a clear plan to incorporate these high‑value features. |

---

### 4. Suggestions  

- **Resolve D‑IMPL‑10** (or convert it to a gating decision) before the Phase D sign‑off so the verification criterion is fully satisfied.  
- **Add a short “Residual risk” paragraph** to the Single‑Writer invariant section, explaining why the Python‑based enforcement is considered sufficient (CI lint, boot‑token, no export of `GraphWriter`), and possibly sketch a future static‑analysis safeguard.  
- **Create a “Values vs Mechanism” checklist** near the top of the document to remind readers that all numeric examples are illustrative only; this will avoid accidental hard‑coding.  
- **Consider adding a static type‑level sentinel** (e.g., `WriteAllowed = Literal[False]` in all non‑L2 modules) to make the import‑lint rule self‑documenting.  
- **Provide a migration note** for the two deferred inventory entries, outlining the intended architectural hook points (e.g., where Supervision Quality would plug into the existing operator pipeline).  

---

### 5. Risk Assessment  

**Overall risk: MEDIUM**  

*Justification*: The design largely fulfills all Phase D verification criteria; the only blocker is the provisional status of D‑IMPL‑10, which is a high‑severity concern because the repository layout influences the entire build pipeline. The single‑writer invariant is well‑argued but rests on Python‑level guarantees, introducing a moderate residual risk. All other concerns are low‑severity and pertain mainly to documentation clarity rather than architectural integrity. Resolving D‑IMPL‑10 and reinforcing the single‑writer argument will bring the risk down to **LOW**.

---

## Codex Review

## Summary

The Phase D deliverables are substantially complete and generally strong: the design is at contract altitude, the required diagram set is present, the 126 inventory entries are explicitly mapped or deferred, and the named invariants mostly have structural enforcement arguments rather than assertions. The main blocking issue is decision-log consistency: `D-IMPL-10` is still described as provisionally resolved with an open post-v0 question, while `DESIGN.md` claims zero provisionals and all decisions resolved. That directly conflicts with the Phase D criterion for open D-IMPL decisions.

## Strengths

- **Traceability is strong:** Appendix A maps all 126 inventory entries, with two explicit deferrals tied to scope/rulings.
- **Invariant chapter is useful and concrete:** the single-writer, audit-by-construction, no-hardcoding, and zero-harness-imports invariants have clear structural mechanisms plus CI/boot enforcement.
- **Mechanism/values separation is consistently defended:** thresholds, TTL ceilings, λ_c tables, D_c thresholds, trust scoring thresholds, prompts, skills, policies, and domain ontologies are pushed into Control Plane artifacts.
- **Seams are well-separated:** MCP roles, A2A admission, harness adapters, and ArtifactStore each have distinct trust postures and do not create alternate graph-write paths.
- **Replay design is especially mature:** exact artifact versions, no `@latest` in replay, logical snapshots, re-hydration recipes, and five-dimension record extensions are coherently tied together.
- **Diagram coverage exceeds the minimum:** five pillar diagrams, harness seam, ArtifactStore seam, plus four sequence diagrams for critical flows.

## Concerns

- **HIGH — D-IMPL resolution status is internally inconsistent.**  
  `DESIGN.md` says all 49 open decisions are resolved and that there are zero provisionals, but `DECISIONS.md` says `D-IMPL-10` is “Provisionally resolved” with a remaining open question about adapter/package/repo split post-v0. The Phase D criterion requires every open D-IMPL decision to be resolved or flagged as gating. This needs reconciliation: either mark `D-IMPL-10` fully resolved for v0 with the remainder explicitly post-v0/non-gating, or flag it as gating.

- **MEDIUM — Decision census is confusing.**  
  The review request says 49 decision rulings; `DESIGN.md` says 49 open decisions resolved; Appendix C says 50 distinct rulings cited; `DECISIONS.md` includes `D-IMPL-51`. This may be explainable because `D-IMPL-51` is Phase R triangulation metadata and `D-IMPL-10` is non-load-bearing, but the documents do not make that accounting clean.

- **MEDIUM — The “three validation gates” wording drifts.**  
  The named invariant is empty-operator guard, lineage strict equality, and TTL bounds. Some text instead names the sequence as “Schema Validator → Policy Gate → Lineage Completeness Checker,” which does not visibly include the empty-operator guard or TTL bounds. The mechanism is present elsewhere, but the gate naming should be normalized.

- **MEDIUM — Composition-preservation argument could be sharper.**  
  The design sometimes describes `(A∘B)(G) = A(B(G))` as if it were a semantic property, but that equation is definitional composition. The real invariant appears to be deterministic, lineage-preserving, cache-coherent staged composition. The test plan should define valid operator pair domains and expected equivalence more precisely.

- **LOW — Some traceability rows point to boundary sections rather than full mechanism sections.**  
  For example, several L4/L5/L6 entries map to §2A.1 as boundary commitments even though their mechanism lives in §2B. This is probably acceptable because the prose cross-references Part B, but it weakens mechanical auditability.

- **LOW — Some diagrams are dense enough that they function more as concept maps than verification diagrams.**  
  They still satisfy the criteria, but future reviewers may need clearer visual emphasis on enforcement points, especially validation gates and Control Plane/Data Plane handoffs.

## Suggestions

- Resolve the `D-IMPL-10` status explicitly:
  - “Resolved for v0: monorepo; post-v0 adapter package split tracked outside Phase D; non-gating.”
  - Or mark it gating if it truly affects Phase I.
- Add a short “Decision Census” note explaining which D-IMPL entries count toward Phase D and why `D-IMPL-51` is or is not included.
- Rename the L6 validation sequence consistently to the actual three gates: empty-operator guard, lineage strict equality, TTL bounds.
- Rephrase the composition invariant around replay-equivalent staged execution, deterministic cache keys, typed operator compatibility, and lineage preservation.
- In Appendix A, consider mapping see-also entries to both the boundary section and the mechanism section, e.g. `§2A.1 / §2B.1`.

## Risk Assessment

**Overall risk: MEDIUM.** The design substance is strong and appears to meet most Phase D criteria, but the unresolved/provisional decision inconsistency is a formal gate risk. Once the D-IMPL census and `D-IMPL-10` status are cleaned up, the residual risk drops to LOW.

---

## Consensus Summary (3 reviewers: Gemini, Ollama gpt-oss:120b, Codex gpt-5)

### Agreed Strengths (all three)
- Complete 126/126 traceability with only the two documented, ruled deferrals
- Structural invariant arguments robust — single-writer (D-IMPL-41 four-layer stack), audit-by-construction, No-Hardcoding, zero-harness-imports all mechanism-backed
- Mechanism/values discipline held throughout — thresholds/TTLs/λ_c/prompts all Control Plane artifacts
- Diagram set exceeds the minimum (5 pillar + 2 seam + 4 sequence); seams cleanly decoupled with distinct trust postures
- Replay design mature (exact versions, no @latest, logical snapshots, re-hydration recipes)

### Agreed Concerns (2+ reviewers)
- **D-IMPL-10 provisional status / decision-census consistency** (Ollama HIGH; Codex HIGH; Gemini not flagged). Codex sharpened the real defect: DESIGN.md claims "zero provisionals / all resolved" while DECISIONS.md carries D-IMPL-10 as "provisionally resolved" with a post-v0 sub-question — an internal inconsistency, not merely a strict criterion reading. Fix at the gate: reconcile the census (state D-IMPL-10 as "Resolved for v0: monorepo; post-v0 adapter split tracked outside Phase D; non-gating" or flag it gating), and add a Decision Census note covering why D-IMPL-51 counts differently. **TRIAGE: BLOCKING (doc-consistency fix, small).**
- **Python single-writer residual** (Ollama C-2 MEDIUM; Gemini lint-dependency LOW): both accept the four-layer stack and honest-residual framing; reinforce the residual-risk narrative. TRIAGE: ADVISORY (already present per D-IMPL-41 ruling; strengthen wording).

### Codex-unique items (for triage)
- MEDIUM — "Three validation gates" naming drift: some text names "Schema Validator → Policy Gate → Lineage Completeness Checker" instead of the canonical empty-operator guard / lineage strict equality / TTL bounds. TRIAGE: BLOCKING (naming normalization — invariant identity must be unambiguous for the row-by-row gate check).
- MEDIUM — Composition-preservation argument should be rephrased around deterministic, lineage-preserving, cache-coherent staged execution (the equation alone is definitional). TRIAGE: ADVISORY → fold into Phase F test strategy.
- LOW — Some traceability rows map to boundary sections (§2A.1) where mechanism lives in §2B; consider dual mapping. TRIAGE: ADVISORY.
- LOW — Dense diagrams function as concept maps; emphasize enforcement points visually. TRIAGE: ADVISORY.

### Reviewer-unique items (Gemini / Ollama, carried from 2-reviewer pass)
- Gemini MEDIUM: re-hydration fragility (D-IMPL-44) — Phase F test strategy for hash-verified re-hydration. ADVISORY → Phase F.
- Gemini LOW: Control Plane centralization at scale (v0-appropriate). ADVISORY.
- Gemini suggestion: dev/mock IdentityProvider for examples 00–02. ADVISORY → Phase F/I.
- Ollama LOW: C-3 gates runtime-only; C-4 illustrative numerics disclaimer; C-5 migration notes for the two deferrals. ADVISORY.

### Overall
- Gemini: LOW risk — "Approved. Phase D is complete."
- Ollama: MEDIUM (drops to LOW once D-IMPL-10 status reconciled).
- Codex: MEDIUM (same driver: "once the D-IMPL census and D-IMPL-10 status are cleaned up, the residual risk drops to LOW").
- **Net triage: 2 BLOCKING doc-consistency fixes (D-IMPL-10 census reconciliation; validation-gate naming normalization) + advisory items carried to the gate appendix and Phase F. No blocking findings against the design substance.**
