# Phase 3: Phase F — Feasibility & Scoping - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce `docs/FEASIBILITY.md` (per-component verdict: strong fit / needs
design choice / out of scope for v0), `docs/ROADMAP.md` (milestone breakdown,
explicit v0.1 minimum viable SDK surface, deferred items), and the FEAS-03
test strategy naming how each CI-enforced invariant is verified — plus a
check that the 12-member Phase I gate list (D-IMPL-01..05, 11, 14, 17, 20,
24, 26, 28) is resolved (it is: 49/49 rulings, zero provisionals, per
D-GATE-D). Branch `phase-f`, model mandate Fable 5 "high" effort. No
implementation code. Ends with `/gsd-review --phase Phase F --all` → triage →
Dave approval → `D-GATE-F` → merge to `main` (CLAUDE.md §3.1).

</domain>

<decisions>
## Implementation Decisions

### Component granularity (FEAS-01)
- **D-01:** A "component" = a named design component/Protocol in DESIGN.md
  (~30–50 units). Each carries one verdict. An appendix matrix maps all 126
  SPEC_INVENTORY entries to their owning component's verdict, mirroring the
  Phase 2 D-06 traceability pattern so `/gsd-review` can check coverage
  mechanically.
- **D-02:** If feasibility analysis surfaces a genuinely new design gap: log
  a new `D-IMPL-NN` in `docs/DECISIONS.md`, mark the component "needs design
  choice", and present at the D-GATE-F review (CLAUDE.md §15). Phase 4
  blocks only if the gap is on the gate-critical path. No inline
  re-litigation of ruled decisions.
- **D-03:** Each component entry carries: verdict + 2–4 sentence rationale
  citing its DESIGN.md section and the D-IMPL rulings it embodies + a
  risk/complexity note (low/med/high) that feeds the ROADMAP.md milestone
  breakdown. No per-component effort estimates (speculative on unbuilt code).

### v0.1 surface and docs/ROADMAP.md (FEAS-02)
- **D-04:** The v0.1 minimum viable surface is **example-driven**: exactly
  what is needed to run `examples/00-quickstart` and `examples/01-agent-basics`
  end-to-end on reference backends — fabric core L1–L6, Control Plane
  registry, Agent & Task Factory, one archetype (`AnalyticsInsightsAgent`),
  SQLite graph store, file-backed ArtifactStore.
- **D-05:** `docs/ROADMAP.md` milestones align **1:1 with GSD phases
  I.1–I.5** (Fabric Core; Agent Framework; Cross-Process & Harness; Orch +
  HITL + Experience; Examples + CI), each gated by its `D-GATE-I.n`. The
  v0.1 surface is annotated as the subset of milestones I.1–I.2 that runs
  examples 00–01. One source of sequencing truth with `.planning/ROADMAP.md`.
- **D-06:** Deferred items use a **named deferral register** table: item,
  source (CLAUDE.md § / D-IMPL-NN), reason deferred, earliest milestone it
  could re-enter. Must include at minimum: Homecams rebuild (post-v0),
  adapter package split (D-IMPL-10 residual), agent-swarm extension
  (D-IMPL-49), Supervision Quality (D-IMPL-48), Conversational Reporting
  Layer (§8.10). This register also closes the Ollama
  "deferral migration notes" advisory.

### Test strategy (FEAS-03)
- **D-07:** The test strategy is a **per-invariant spec table** chapter
  inside FEASIBILITY.md (no separate TEST_STRATEGY.md). One row per
  CI-enforced invariant: verification mechanism (lint rule / test harness /
  boot check), where it runs (CI job), pass criterion, and which DESIGN.md
  Invariant Preservation section it implements — building on the Phase 2
  D-11 CI enforcement design, not re-deriving it.
- **D-08:** Composition-preservation is specified as **two explicit test
  classes**: (1) algebraic operator-pair equality `(A∘B)(G) = A(B(G))` over
  fixture graphs for every shipped operator pair; (2) staged-execution
  equivalence — the two-stage projection plan's output equals direct
  composition. Closes the Codex/Cursor advisory.
- **D-09:** Hash-verified re-hydration is a named test-strategy row:
  replaying a ReHydrationRecipe must reproduce artifacts whose content
  hashes match the pinned hashes (leveraging D-IMPL-26 hybrid
  content-hash + versioned-URI addressing). A Phase I test class, not a CI
  lint. Closes the Gemini advisory.

### Advisory disposition (7 items carried from Phase D)
- **D-10:** Three-harness v0 scope (D-IMPL-24, Dave's own ruling): the
  adapter components get an **honest feasibility verdict with per-harness
  sizing/risk analysis, no re-litigation**. If risk is high, that lands as a
  recommendation for Dave at D-GATE-F (e.g., stage LangGraph later within
  I.3) — the ruling stands unless Dave revises it.
- **D-11:** FEASIBILITY.md carries an **"Advisory Disposition" appendix**:
  all 7 carried items, each with its disposition (where addressed / why no
  action), making D-GATE-F closure mechanically checkable. Wording fixes
  (Python single-writer residual-risk framing, numerics disclaimer) are
  applied to DESIGN.md in-place with the appendix pointing at the commits;
  the dev/mock IdentityProvider suggestion is assessed as a v0.1-surface
  feasibility line item.

### Claude's Discretion
- FEASIBILITY.md / ROADMAP.md internal chapter ordering and formatting.
- Exact component enumeration extracted from DESIGN.md (bounded by D-01).
- Risk-rating rubric (low/med/high definitions).
- How the Phase I gate-list check is presented (table expected).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project governance
- `CLAUDE.md` — canonical (rev 4): §3 Phase F deliverables, §3.1 Phase F
  review criteria, §9 examples suite (defines the v0.1 cut), §12 Phase I
  gate list, §13 v0 scope/non-scope (deferral register source), §15
  ambiguity discipline.

### Phase D deliverables (feasibility inputs)
- `docs/DESIGN.md` — the 1011-line design FEASIBILITY.md issues verdicts
  against; its Invariant Preservation chapter + CI enforcement design
  (Phase 2 D-11) is the direct input to the FEAS-03 test-strategy table.
- `docs/DECISIONS.md` — all 49 D-IMPL rulings + D-GATE entries; verdict
  rationales cite these; new gaps extend it per D-02.
- `docs/SPEC_INVENTORY.md` — 126 entries for the appendix matrix (D-01).
- `.planning/phases/02-phase-d-design/02-REVIEWS.md` — the 7 advisory
  findings carried to Phase F; source list for the Advisory Disposition
  appendix (D-11).
- `docs/CCF_Whitepaper_1-2.md` — canonical spec; cite sections, never the PDF.

### Planning
- `.planning/ROADMAP.md` — Phase 3 goal/success criteria (FEAS-01..04) and
  the I.1–I.5 phase structure docs/ROADMAP.md milestones align to (D-05).
- `.planning/REQUIREMENTS.md` — FEAS-01..04 definitions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/DESIGN.md` Appendix A (inventory→design matrix) and Appendix C
  (D-IMPL ruling index) — the FEAS-01 component list and appendix matrix
  derive directly from these.
- `docs/DECISIONS.md` entry format is established — new D-IMPL entries (if
  any) extend it, never restructure it.
- Phase 1/2 multi-plan wave pattern under `.planning/phases/0{1,2}-*` —
  reusable planning structure; Phase F is likely smaller (docs-only).

### Established Patterns
- Review appendix pattern (blocking/advisory triage per §3.1) established in
  Phase D — the Advisory Disposition appendix follows it.
- No production code exists (correct — Phase F writes none).

### Integration Points
- Deliverables: `docs/FEASIBILITY.md` (new), `docs/ROADMAP.md` (new — note:
  distinct from `.planning/ROADMAP.md`), small in-place DESIGN.md wording
  fixes (D-11), possible `docs/DECISIONS.md` additions (D-02). Branch
  `phase-f` off `main` (post-D-GATE-D).

</code_context>

<specifics>
## Specific Ideas

- The Phase I hard gate check (success criterion 3) should present the
  12-member gate list against DECISIONS.md status explicitly — all 12 are
  resolved per D-GATE-D, so this is a verification table, not new work.
- Sizing pressure on the three-harness ruling may produce a staging
  recommendation for Dave at the gate, never a unilateral scope change.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3 - Phase F — Feasibility & Scoping*
*Context gathered: 2026-07-25*
