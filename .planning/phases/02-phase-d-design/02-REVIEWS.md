---
phase: 2
reviewers: [gemini, ollama, codex, cursor]
reviewers_failed: [claude (skipped — self)]
cursor_note: initial run failed (no login); succeeded 2026-07-25 via CURSOR_API_KEY
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

## Cursor Review

# Cross-AI Review — Phase D (Design)

## 1. Summary

Phase D deliverables meet the §3.1 verification bar: a 126-row traceability matrix with two ruled deferrals, D-IMPL-01..51 closed (Phase I gating set fully RESOLVED; D-IMPL-10 provisional monorepo only), the required seven architecture diagrams plus four load-bearing sequences, and a §9 invariant chapter that argues each of the seven named invariants structurally rather than by assertion. Contract altitude holds; domain values are consistently pushed to Control Plane configuration. Residual issues are documentation accuracy and Phase F scope pressure (three harness adapters), not missing design or unsupported invariants.

## 2. Strengths

- **Traceability is first-class.** Appendix A claims 126/126 with census; matrix row count matches inventory entry headers (126). Deferrals (INV-CH8-19, INV-CH8-21) cite D-IMPL-48 / CLAUDE.md §13 as ruled dispositions, not silent gaps.
- **Invariant preservation is structural.** §9 + D-IMPL-41 (reader/writer split, DI, CI lint, boot token), L6 gate-as-sole-construction-path, HITL action-as-completion-token, factory-as-sole-construction-path, and harness-only-in-`/runtime` are real design constructs, not aspiration.
- **Seam discipline is clear.** MCP five-edge allocation, A2A verify-every-admission → L2-only write, ArtifactStore never second writer, LangGraph harness-vs-orchestrator split, and HTTP deliberately without L1 ingestion all protect single-writer.
- **Mechanism/values boundary is enforced in design.** λ_c, MAX_TTL, CAR thresholds, operator parameters, and illustrative 0.85/0.75 figures are Control Plane / illustrative, with D-IMPL-38/39/40 as the schema discipline.
- **Decision log quality is high.** Ambiguous whitepaper passages (D-IMPL-30/31/32/39/40/etc.) quote the text, offer readings, and record Dave’s ruling with date/approver. Phase I gate list is explicitly marked RESOLVED.
- **Diagram set is complete and useful.** Five pillar diagrams, two mandated seams, plus sequences for write path, HITL suspend/resume, A2A admission, and replay resolution — the sequences actually demonstrate refused paths, not only happy paths.
- **SDK extensions are labeled.** Agent framework, HITL, orchestration, harness adapters, ArtifactStore, and bidirectional MCP cite CLAUDE.md and whitepaper hooks without pretending they are whitepaper-native.

## 3. Concerns

- **MEDIUM — Traceability primary-section drift for L4–L6 layer entries.** INV-CH7-05/06/07/11/12/13 map to §2A.1, which only binds them at the layer boundary and says mechanism lives in Part B. The design *exists* in §2B, so this is not a coverage miss, but the matrix understates the real home and weakens mechanical “unique-key → design element” audit.
- **MEDIUM — §4/§5 ownership paste residue.** §4 opens with “Both pillars…” and lists owned entries that Appendix A assigns to §5 (e.g. INV-CH7-65/67/82, INV-CH8-16/18/19/23). Design content is present; ownership metadata is inconsistent and will confuse Phase F/I implementers.
- **MEDIUM — `pillar-orchestration.mmd` edge ambiguity.** `WFState --> ArtifactStore` sits next to “trace write-through,” but D-IMPL-18/27 put *mutable* suspended execution state on the Control Plane store, not the ArtifactStore. A reader can infer state persistence in the ArtifactStore, which would violate the mutability split.
- **MEDIUM — Three-harness v0 scope (D-IMPL-24) as Phase F pressure.** Design correctly records Dave’s ruling (ADK + Claude Agent SDK + LangGraph). That does not fail Phase D criteria, but it expands example 03, CI legs, and adapter conformance — Phase F must size this explicitly or the design becomes an unvalidated schedule risk.
- **LOW — “Zero provisionals” wording vs D-IMPL-10.** DESIGN §1 says the marathon closed with zero provisionals; D-IMPL-10 remains provisionally resolved (post-v0 adapter-split remainder open). Not load-bearing for components here, but the claim is slightly overstated.
- **LOW — Duplicate §8.6 / §8.6a numbering.** Minor navigation defect in an otherwise careful document.
- **LOW — Composition-preservation leans on purity + empirical CI.** The structural story (pure `GraphReader` operators, deterministic intermediate keys) is adequate for Phase D; Phase F still needs to nail intermediate-type equality and non-commutativity traps so “bit-for-bit” tests are well-defined.

No **HIGH** findings against the stated Phase D verification criteria (no missing inventory mapping, no unresolved gating decision, no missing required diagram, no assertion-only invariant, no implementation code bodies, no domain values baked into mechanism).

## 4. Suggestions

- Retarget Appendix A primary sections for INV-CH7-05/06/07/11/12/13 to §2B.1–§2B.3 (keep §2A.1 as see-also).
- Split the §4 owned-entry list to match Appendix A; remove the “Both pillars…” leftover from the §4/§5 merge.
- In `pillar-orchestration.mmd`, replace `WFState --> ArtifactStore` with something like `Replay --> ArtifactStore` only, or label the edge `trace write-through (not execution state)`.
- Add a one-line Phase F note under D-IMPL-24: adapter/conformance/example-03 cost as an explicit feasibility input.
- Soften §1 “zero provisionals” to “zero provisional *design-basis* flags; D-IMPL-10 remains provisional monorepo orientation.”
- Before Dave’s D-GATE-D, run a mechanical unique-key diff of inventory headers vs Appendix A (claimed empty; worth proving in the review report).

## 5. Risk Assessment

**Overall: LOW** for Phase D gate readiness.

Justification: every verification criterion is satisfied on the evidence reviewed — inventory coverage with ruled deferrals, decisions resolved (gating set complete), diagram set complete, invariants argued structurally with CI designs named (CINV-01..04), contract altitude preserved, and mechanism/values discipline held. Remaining issues are editorial consistency and forward-looking feasibility load from the three-adapter ruling; they should be cleaned or recorded before presentation to Dave, but they do not block a Phase D pass under §3.1.

---

## Consensus Summary (4 reviewers: Gemini, Ollama gpt-oss:120b, Codex gpt-5, Cursor)

### Agreed Strengths (all four)
- Complete 126/126 traceability with two ruled deferrals; decision log quality high (quoted ambiguities, readings, dated rulings with approver)
- Structural invariant arguments, not assertions — single-writer four-layer stack, gate-as-sole-construction-path, factory-as-sole-path, harness-only-in-/runtime
- Mechanism/values discipline held; illustrative numerics correctly non-normative
- Diagram set exceeds minimum; sequences demonstrate refused paths, not just happy paths
- Seam discipline protects single-writer at every boundary (MCP, A2A, ArtifactStore, HTTP-no-ingestion)

### Agreed Concerns (2+ reviewers) — triage
1. **D-IMPL-10 "zero provisionals" wording inconsistency** (Codex HIGH; Ollama HIGH; Cursor LOW as wording; Gemini not flagged). DESIGN.md §1 overstates "zero provisionals" while DECISIONS.md keeps D-IMPL-10 provisional (post-v0 adapter split). Fix: reconcile census — "Resolved for v0: monorepo; post-v0 adapter split non-gating" + Decision Census note (incl. D-IMPL-51 accounting). **BLOCKING (small doc fix).**
2. **Traceability primary-section drift for L4–L6 entries** (Codex LOW; Cursor MEDIUM): INV-CH7-05/06/07/11/12/13 map to §2A.1 boundary rather than §2B mechanism sections. Fix: retarget primary to §2B.1–§2B.3, keep §2A.1 see-also. **BLOCKING-lite (mechanical edit, do at gate).**
3. **Python single-writer residual** (Ollama MEDIUM; Gemini LOW): accepted with honest-residual framing; strengthen wording. ADVISORY.

### Single-reviewer items — triage
- Codex MEDIUM — validation-gate naming drift ("Schema Validator → Policy Gate → Lineage Completeness Checker" vs canonical empty-operator guard / lineage strict equality / TTL bounds). **BLOCKING (naming normalization).**
- Cursor MEDIUM — §4/§5 ownership paste residue ("Both pillars…" + misassigned owned-entry lists). **BLOCKING-lite (editorial fix at gate).**
- Cursor MEDIUM — pillar-orchestration.mmd `WFState --> ArtifactStore` edge implies mutable state in ArtifactStore, contradicting D-IMPL-18/27. **BLOCKING-lite (relabel edge "trace write-through (not execution state)").**
- Cursor MEDIUM — three-harness v0 scope is Phase F sizing pressure. ADVISORY → explicit Phase F feasibility input under D-IMPL-24.
- Codex MEDIUM — composition-preservation phrasing (definitional equation vs staged-execution invariant); Cursor LOW concurs re Phase F test definition. ADVISORY → Phase F test strategy.
- Cursor LOW — duplicate §8.6/§8.6a numbering. Fix at gate.
- Gemini MEDIUM — re-hydration fragility → Phase F hash-verified re-hydration test strategy. ADVISORY.
- Gemini LOW — Control Plane centralization at scale; dev/mock IdentityProvider suggestion. ADVISORY.
- Ollama LOW — gates runtime-only note; numerics disclaimer; deferral migration notes. ADVISORY.

### Overall verdicts
- Gemini: LOW — "Approved. Phase D is complete."
- Cursor: LOW — "does not block a Phase D pass under §3.1"; explicitly zero HIGH findings against the criteria.
- Ollama: MEDIUM → LOW once D-IMPL-10 reconciled.
- Codex: MEDIUM → LOW once census + gate naming cleaned.

### Net triage for the 02-11 gate
**Blocking (all doc-consistency, no design-substance defects):**
B1. D-IMPL-10 census reconciliation + Decision Census note (D-IMPL-51 accounting) + soften §1 wording.
B2. Validation-gate naming normalization to the canonical three gates.
B3. Appendix A primary-section retarget for the six L4–L6 entries (§2B primary, §2A.1 see-also).
B4. §4/§5 ownership-list residue cleanup.
B5. pillar-orchestration.mmd edge relabel (trace write-through, not execution state) + fix §8.6/§8.6a numbering.
**Advisory (record in gate appendix, carry to Phase F):** three-adapter sizing input, composition-preservation test definition, hash-verified re-hydration strategy, residual-risk wording, numerics disclaimer, deferral migration notes, dev IdentityProvider.
