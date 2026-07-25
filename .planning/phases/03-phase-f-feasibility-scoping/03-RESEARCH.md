# Phase 3: Phase F — Feasibility & Scoping - Research

**Researched:** 2026-07-25
**Domain:** Documentation/analysis phase — feasibility verdicts, roadmap, and test strategy derived from the internal corpus (DESIGN.md, DECISIONS.md, SPEC_INVENTORY.md). No web research required; no code written.
**Confidence:** HIGH (all findings verified directly against repo documents in this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Component granularity (FEAS-01)**
- **D-01:** A "component" = a named design component/Protocol in DESIGN.md (~30–50 units). Each carries one verdict. An appendix matrix maps all 126 SPEC_INVENTORY entries to their owning component's verdict, mirroring the Phase 2 D-06 traceability pattern so `/gsd-review` can check coverage mechanically.
- **D-02:** If feasibility analysis surfaces a genuinely new design gap: log a new `D-IMPL-NN` in `docs/DECISIONS.md`, mark the component "needs design choice", and present at the D-GATE-F review (CLAUDE.md §15). Phase 4 blocks only if the gap is on the gate-critical path. No inline re-litigation of ruled decisions.
- **D-03:** Each component entry carries: verdict + 2–4 sentence rationale citing its DESIGN.md section and the D-IMPL rulings it embodies + a risk/complexity note (low/med/high) that feeds the ROADMAP.md milestone breakdown. No per-component effort estimates (speculative on unbuilt code).

**v0.1 surface and docs/ROADMAP.md (FEAS-02)**
- **D-04:** The v0.1 minimum viable surface is **example-driven**: exactly what is needed to run `examples/00-quickstart` and `examples/01-agent-basics` end-to-end on reference backends — fabric core L1–L6, Control Plane registry, Agent & Task Factory, one archetype (`AnalyticsInsightsAgent`), SQLite graph store, file-backed ArtifactStore.
- **D-05:** `docs/ROADMAP.md` milestones align **1:1 with GSD phases I.1–I.5** (Fabric Core; Agent Framework; Cross-Process & Harness; Orch + HITL + Experience; Examples + CI), each gated by its `D-GATE-I.n`. The v0.1 surface is annotated as the subset of milestones I.1–I.2 that runs examples 00–01. One source of sequencing truth with `.planning/ROADMAP.md`.
- **D-06:** Deferred items use a **named deferral register** table: item, source (CLAUDE.md § / D-IMPL-NN), reason deferred, earliest milestone it could re-enter. Must include at minimum: Homecams rebuild (post-v0), adapter package split (D-IMPL-10 residual), agent-swarm extension (D-IMPL-49), Supervision Quality (D-IMPL-48), Conversational Reporting Layer (§8.10). This register also closes the Ollama "deferral migration notes" advisory.

**Test strategy (FEAS-03)**
- **D-07:** The test strategy is a **per-invariant spec table** chapter inside FEASIBILITY.md (no separate TEST_STRATEGY.md). One row per CI-enforced invariant: verification mechanism (lint rule / test harness / boot check), where it runs (CI job), pass criterion, and which DESIGN.md Invariant Preservation section it implements — building on the Phase 2 D-11 CI enforcement design, not re-deriving it.
- **D-08:** Composition-preservation is specified as **two explicit test classes**: (1) algebraic operator-pair equality `(A∘B)(G) = A(B(G))` over fixture graphs for every shipped operator pair; (2) staged-execution equivalence — the two-stage projection plan's output equals direct composition. Closes the Codex/Cursor advisory.
- **D-09:** Hash-verified re-hydration is a named test-strategy row: replaying a ReHydrationRecipe must reproduce artifacts whose content hashes match the pinned hashes (leveraging D-IMPL-26 hybrid content-hash + versioned-URI addressing). A Phase I test class, not a CI lint. Closes the Gemini advisory.

**Advisory disposition (7 items carried from Phase D)**
- **D-10:** Three-harness v0 scope (D-IMPL-24, Dave's own ruling): the adapter components get an **honest feasibility verdict with per-harness sizing/risk analysis, no re-litigation**. If risk is high, that lands as a recommendation for Dave at D-GATE-F (e.g., stage LangGraph later within I.3) — the ruling stands unless Dave revises it.
- **D-11:** FEASIBILITY.md carries an **"Advisory Disposition" appendix**: all 7 carried items, each with its disposition (where addressed / why no action), making D-GATE-F closure mechanically checkable. Wording fixes (Python single-writer residual-risk framing, numerics disclaimer) are applied to DESIGN.md in-place with the appendix pointing at the commits; the dev/mock IdentityProvider suggestion is assessed as a v0.1-surface feasibility line item.

### Claude's Discretion
- FEASIBILITY.md / ROADMAP.md internal chapter ordering and formatting.
- Exact component enumeration extracted from DESIGN.md (bounded by D-01).
- Risk-rating rubric (low/med/high definitions).
- How the Phase I gate-list check is presented (table expected).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FEAS-01 | `docs/FEASIBILITY.md` — per-component verdict (strong fit / needs design choice / out of scope for v0) | Component enumeration source verified: DESIGN.md has 48 `###` subsections and ~28 named Protocols/classes; Appendix A (126/126 matrix at lines 792+) and Appendix C (50-ruling D-IMPL index) give the mechanical inputs for D-01's appendix matrix. See "Component Enumeration" below. |
| FEAS-02 | `docs/ROADMAP.md` — milestones, explicit v0.1 surface, deferred items | `.planning/ROADMAP.md` I.1–I.5 phase structure verified (Phases 4–8, one D-GATE-I.n each); v0.1 cut components identified from D-04 against DESIGN.md sections; deferral register minimum-five items all located in corpus. |
| FEAS-03 | Test strategy per CI-enforced invariant; Phase I gate list checked against resolution status | DESIGN.md §9 "CI enforcement design (D-11) — CINV-01..04" is the direct input — verbatim content captured below. Gate list status verified: all 12 gating D-IMPL IDs RESOLVED per DECISIONS.md/STATE.md (D-GATE-D, zero provisionals, 49/49 rulings). |
| FEAS-04 | Phase F reviewed, triaged, Dave-approved, `D-GATE-F` logged, merged to `main` | §3.1 protocol + Phase 2's 02-REVIEWS.md consensus pattern (4 reviewers) is the established template; cross-AI credentials discipline documented in CLAUDE.md §3.1 and MEMORY.md. |
</phase_requirements>

## Summary

Phase F is a pure documentation/analysis phase: produce `docs/FEASIBILITY.md` and `docs/ROADMAP.md` from the completed Phase D corpus, apply two small in-place DESIGN.md wording fixes, and run the gate protocol. Every input the phase needs already exists in the repo and was verified this session: DESIGN.md (1011 lines, 48 subsections, Appendix A 126/126 traceability, Appendix C ruling index, §9 CI enforcement design), DECISIONS.md (49/49 D-IMPL rulings resolved, zero provisionals), SPEC_INVENTORY.md (126 entries), and 02-REVIEWS.md (the 7 advisory items with exact wording in its "Net triage" section, line 236).

The critical planner insight: this is a **derivation exercise, not an invention exercise**. FEAS-03's test-strategy table transposes DESIGN.md §9's already-designed CINV-01..04 + composition-preservation harness + single-writer boot check + gate unit tests into the D-07 table format, adding the D-08 second test class and the D-09 re-hydration row. The Phase I gate check is a verification table over already-resolved decisions. The only genuinely analytical work is the per-component verdicts and risk ratings (FEAS-01) and the per-harness sizing analysis (D-10).

**Primary recommendation:** Plan Phase F as 3–4 small doc-authoring plans on branch `phase-f`: (1) component enumeration + FEASIBILITY.md verdicts + appendix matrix; (2) ROADMAP.md + deferral register; (3) test-strategy chapter + gate-list table + advisory dispositions + DESIGN.md wording fixes; (4) review/gate plan (`/gsd-review --phase Phase F --all` → triage → Dave → D-GATE-F → merge). No packages installed, no external tools needed beyond git and the cross-AI review CLIs.

## Project Constraints (from CLAUDE.md)

- **Phase boundaries are real** — no implementation code in Phase F (§3); deliverables are `docs/FEASIBILITY.md`, `docs/ROADMAP.md` only, plus D-11's small DESIGN.md wording fixes and possible DECISIONS.md additions (D-02).
- **Model mandate:** Fable 5, "high" effort (§3, Phase F).
- **Branch discipline (§2.2):** work on `phase-f` off `main` (post-D-GATE-D); merge to `main` only at the `D-GATE-F` entry, `--no-ff` (Phase 2 precedent: 4873f40). No force-push to `main`. Commit at deliverable boundaries with messages naming the CLAUDE.md section or D-IMPL-NN served. Note: `.planning/config.json` has `branching_strategy: "none"` — CLAUDE.md §2.2 overrides; Phase 2 used a real `phase-d` branch.
- **Gate protocol (§3.1), in order:** self-review via `/gsd-review --phase Phase F --all` → blocking/advisory triage → present to Dave → log `D-GATE-F` in docs/DECISIONS.md → merge. Review passing is necessary, never sufficient.
- **§3.1 Phase F verification criteria (what the review checks):** every design component carries a verdict; v0.1 surface is explicit; Phase I gate list checked against actual resolution status; test strategy names how each CI-enforced invariant is verified.
- **Cross-AI credentials:** Codex via `printenv CODEX_API_KEY | codex login --with-api-key` (not OPENAI_API_KEY); Cursor via `CURSOR_API_KEY` exported, `cursor agent -p --mode ask` (no `--trust` flag). Keys from `/home/parkave/homecams_v2/.env`, never committed. [VERIFIED: CLAUDE.md §3.1 + MEMORY.md]
- **Ambiguity discipline (§15):** new gaps become `D-IMPL-NN` entries + stop; no defaults picked silently. D-02 operationalizes this for Phase F.
- **No re-litigation of ruled decisions** — Dave's 49 rulings stand; sizing pressure produces recommendations at the gate, never unilateral scope changes (D-10, CONTEXT.md Specifics).
- **Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF** (DECISIONS.md locked D-01).

## Architectural Responsibility Map

Not applicable in the multi-tier sense — docs-only phase. The "tiers" here are document ownership:

| Capability | Owning Artifact | Secondary | Rationale |
|------------|----------------|-----------|-----------|
| Per-component verdicts + appendix matrix + risk notes | `docs/FEASIBILITY.md` (new) | — | FEAS-01, D-01/D-03 |
| Test-strategy per-invariant table | `docs/FEASIBILITY.md` chapter | DESIGN.md §9 (source, unchanged) | D-07: chapter inside FEASIBILITY.md, no separate file |
| Advisory Disposition appendix | `docs/FEASIBILITY.md` appendix | 02-REVIEWS.md (source list) | D-11 |
| Milestones, v0.1 surface, deferral register | `docs/ROADMAP.md` (new — distinct from `.planning/ROADMAP.md`) | `.planning/ROADMAP.md` (sequencing truth to align 1:1) | FEAS-02, D-05/D-06 |
| Wording fixes (single-writer residual framing, numerics disclaimer) | `docs/DESIGN.md` (in-place edits) | Advisory appendix points at the commits | D-11 |
| New design gaps (if any) | `docs/DECISIONS.md` (append, established format) | — | D-02 |
| Gate record `D-GATE-F` | `docs/DECISIONS.md` | `.planning/STATE.md` update | FEAS-04 |

## Standard Stack

No libraries, packages, or runtimes are installed in this phase. Tooling is: Write/Edit for markdown, `git` for branch/commit/merge, `grep`/`diff` for mechanical matrix checks, and the cross-AI review CLIs (`codex`, `cursor`, plus Gemini/Ollama per the Phase 2 four-reviewer pattern) already installed and used in Phase 2. [VERIFIED: 02-REVIEWS.md shows all four reviewers ran successfully]

## Package Legitimacy Audit

Not applicable — no packages installed in this phase.

## Key Findings from the Internal Corpus

### 1. Phase I gate list — already fully resolved (FEAS-03 check is a verification table)

All 12 gate-list IDs (D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28) are RESOLVED with Dave as approver, dated 2026-07-25, zero provisionals; STATE.md explicitly records the blocker as CLEARED. [VERIFIED: docs/DECISIONS.md; .planning/STATE.md lines 53–55, 67] The planner should specify the gate-check as a 12-row table: ID | ruling one-liner | status RESOLVED | DECISIONS.md ref. One nuance to state precisely: **D-IMPL-10 is "resolved for v0 as monorepo; post-v0 adapter-split remainder non-gating"** — Phase 2's B1 blocking fix normalized this wording; FEASIBILITY.md must not reintroduce "zero provisionals including D-IMPL-10" ambiguity (this was Codex/Ollama's top Phase D finding).

### 2. Component enumeration source (D-01: ~30–50 units)

DESIGN.md provides two mechanical anchors: 48 `###` subsections and ~28 named Protocol/class identifiers (`GraphStore`, `SimilarityIndex`, `EmbedderProtocol`, `LLMClientProtocol`, `ArtifactStoreProtocol`, `ColdSourceArchiveProtocol`, `HarnessAdapterProtocol`, `WireProtocol`, `IdentityProvider`, `HITLTransportProtocol`, `OrchestrationProtocol`, `SignalSourceProtocol`, `TrustScorer`, `DebtFactorScorer`, `PassageCitationProvider`, `TraceCorrelationHook`, `ReHydrationRecipe`, `HumanPrincipalBinding`, `AgentFactory`, `TaskFactory`, the six archetypes, etc.). [VERIFIED: grep over docs/DESIGN.md] A component list built as "named Protocol or designed subsystem per DESIGN.md section" naturally lands in the 30–50 band. Recommended enumeration spine (per DESIGN.md structure):
- §2A: L1 Signal Layer, L2 Assembly, L3 GraphStore + single-writer stack, ingress patterns (CDC, MCP-ingress, Pattern 5 pipeline stages)
- §2B: L4 operator algebra (four categories), L5 projection engine, L6 Context Product Contract + three gates, λ_c/D_c (DebtFactorScorer), Decision Replay engine, closed loop
- §3: Agent base, six archetypes, archetype composition, Agent & Task Factory + artifact schema, specialization channel, skilling/skill catalog
- §4: Workflow primitive, OrchestrationProtocol
- §5: four HITL primitives, HITLTransportProtocol, HumanPrincipalBinding/IdentityProvider
- §6: MCP egress server, `ccf` CLI, HTTP API skeleton
- §7: Control Plane registry
- §8: MCP client lib (five edges), A2A (WireProtocol, identity/signing, admission), three harness adapters (per-harness rows per D-10), ArtifactStore (file + MCP impls)
- Cross-cutting: CINV lint suite, EmbedderProtocol, SimilarityIndex, LLMClientProtocol, snapshot/ReHydrationRecipe machinery

The appendix matrix (D-01) is a mechanical join: Appendix A already maps each of the 126 INV keys to a DESIGN.md section; add a "owning component → verdict" column keyed by section. Make it diff-checkable exactly as Appendix A is ("unique-key diff against the inventory is empty").

### 3. FEAS-03 test-strategy source material (D-07) — already designed in DESIGN.md §9

DESIGN.md §9 "CI enforcement design (D-11)" specifies, per CINV: [VERIFIED: docs/DESIGN.md lines 777–790]
- **CINV-01** No-Hardcoding: prompt-shaped-literal lint (heuristics: multi-sentence imperative prose, role-preamble patterns, template-brace density; pragma allow-list) + factory-bypass lint (AST check on `Agent`/`Task` instantiation sites, tests included).
- **CINV-02** Zero-harness-imports lint over `/src` (deny-list: ADK, Claude Agent SDK, LangGraph) + hosts the single-writer static gate (`GraphWriter` importable only by `ccf.assembly` + composition root; strict mypy).
- **CINV-03** `@algorithmic` lint — no `LLMClientProtocol`/vendor SDK import in tagged modules; per-stage in the Pattern 5 pipeline.
- **CINV-04** Replay-by-construction test-harness assertions (HITL action record precedes transition; workflow trace on every transition; skill-set serialized into dimension 4).
- Plus: composition-preservation property harness over every shipped operator pair (bit-for-bit, fixed `(graph_state, control_plane_config, temporal_boundary)` + Similarity determinism tuple); single-writer boot check (exactly one `GraphWriter`, held by Assembly worker); three-validation-gates covered by contract-level unit tests + MAX_TTL registration test — runtime mechanism, not lint.

The D-07 table therefore has ~9–10 rows: 7 named invariants (per §9's invariant table) expanded where an invariant has multiple mechanisms, plus D-08's second test class (staged-execution equivalence: two-stage projection plan output == direct composition — this is the *new* content Phase F adds; §9 covers only the algebraic class) and D-09's hash-verified re-hydration row (ReHydrationRecipe replay reproduces artifacts matching pinned content hashes per D-IMPL-26/44). Columns per D-07: invariant | mechanism (lint/harness/boot check) | CI job | pass criterion | DESIGN.md §9 ref.

### 4. The 7 carried advisories (D-11 appendix) — exact list

From 02-REVIEWS.md line 236 [VERIFIED]: (1) three-adapter sizing input (Cursor MEDIUM → D-10 per-harness analysis); (2) composition-preservation test definition (Codex MEDIUM/Cursor LOW → closed by D-08); (3) hash-verified re-hydration strategy (Gemini MEDIUM → closed by D-09); (4) Python single-writer residual-risk wording (Ollama MEDIUM/Gemini LOW → in-place DESIGN.md strengthening; note DESIGN.md §9 expanded-argument 1 already carries an "Honest residual claim" sentence — the fix is to strengthen/propagate that framing, cite the commit); (5) numerics disclaimer (Ollama LOW → in-place DESIGN.md fix, cite commit); (6) deferral migration notes (Ollama LOW → closed by the D-06 deferral register); (7) dev/mock IdentityProvider (Gemini LOW → assessed as a v0.1-surface feasibility line item). Each gets a disposition row: where addressed / why no action.

### 5. v0.1 surface and ROADMAP.md structure

`.planning/ROADMAP.md` phases 4–8 = I.1–I.5 with names verified: Fabric Core; Agent Specialization Framework; Cross-Process & Harness Adapters; Orchestration/HITL/Experience; Examples Suite & Full CI Verification. [VERIFIED] `docs/ROADMAP.md` mirrors these 1:1 (D-05), each gated by `D-GATE-I.n`, and annotates the v0.1 cut = subset of I.1–I.2 running examples 00–01: L1–L6 fabric core, Control Plane registry, Agent & Task Factory, `AnalyticsInsightsAgent` archetype only, SQLite graph store + sqlite-vec, file-backed ArtifactStore (D-04). Feasibility line item per D-11: whether v0.1 needs a dev/mock IdentityProvider. Cross-reference discipline: `docs/ROADMAP.md` must not fork sequencing from `.planning/ROADMAP.md` — state explicitly that `.planning/ROADMAP.md` is the sequencing source and `docs/ROADMAP.md` is the deliverable view.

### 6. Deferral register minimum set — all sourced

| Item | Source | Verified location |
|------|--------|-------------------|
| Homecams rebuild on SDK | CLAUDE.md §9 | [VERIFIED] |
| Adapter package split | D-IMPL-10 residual | DECISIONS.md / Appendix C wording [VERIFIED] |
| Agent-swarm intent decomposition | D-IMPL-49 | DESIGN.md §4 "named post-v0 extension" [VERIFIED] |
| Supervision Quality (INV-CH8-19) | D-IMPL-48 | DESIGN.md §5 "deferred disposition" [VERIFIED] |
| Conversational Reporting Layer | whitepaper §8.10, CLAUDE.md §13 | [VERIFIED] |

Also candidates from REQUIREMENTS.md v2 list: third-harness deferral does NOT apply (D-IMPL-24 ruled all three ship v0); Chroma second SimilarityIndex impl "if budget allows" (D-IMPL-03) is a plausible additional register row. The two ruled deferrals in Appendix A's 126-entry matrix (status "deferred") should also be checked and included — grep Appendix A for non-"mapped" statuses during planning.

### 7. Verdict distribution expectation

Given 49/49 rulings resolved and the design passing review with zero design-substance defects, most components should honestly land "strong fit." "Needs design choice" applies only if D-02 fires (new gap). "Out of scope for v0" applies to the deferral-register items that appear as design-named components (swarm decomposition, Supervision Quality). The three harness adapters get individually-sized verdicts (D-10): expect ADK/Claude-SDK medium, LangGraph flagged with the two-seam disambiguation (D-IMPL-17) complexity and a possible stage-later-within-I.3 recommendation for Dave.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Component/inventory coverage checking | Manual eyeballing of 126 rows | Mechanical key-diff (grep unique INV keys in FEASIBILITY appendix vs SPEC_INVENTORY), as Appendix A does | Phase 2 precedent; `/gsd-review` checks this mechanically per D-01 |
| Test strategy content | Fresh derivation of CI enforcement | Transpose DESIGN.md §9 D-11 designs verbatim into the D-07 table | D-07 mandates "building on Phase 2 D-11, not re-deriving" |
| Deferral list | Ad-hoc prose | D-06 named register table with the five mandatory rows | Locked decision; closes Ollama advisory |
| Decision-log entries | New format | Existing DECISIONS.md entry format | CONTEXT.md code-context: "extend it, never restructure it" |

## Common Pitfalls

### Pitfall 1: D-IMPL-10 census wording regression
**What goes wrong:** FEASIBILITY.md or ROADMAP.md restates "zero provisionals / all resolved" without the "resolved for v0; post-v0 adapter split non-gating" qualifier, reintroducing the exact inconsistency that was Phase D's top blocking finding (B1).
**How to avoid:** Copy the normalized Appendix C wording verbatim wherever decision status is summarized.

### Pitfall 2: Two ROADMAPs drifting
**What goes wrong:** `docs/ROADMAP.md` (deliverable) and `.planning/ROADMAP.md` (GSD) diverge on milestone content or sequencing.
**How to avoid:** D-05 — 1:1 alignment, one sequencing source of truth; state the relationship explicitly in docs/ROADMAP.md's preamble. Do not edit `.planning/ROADMAP.md` content beyond normal GSD tracking.

### Pitfall 3: Re-litigating ruled decisions under sizing pressure
**What goes wrong:** The three-harness analysis morphs into "recommend dropping LangGraph from v0."
**How to avoid:** D-10 — honest verdict + per-harness sizing/risk; a staging recommendation *within I.3* for Dave at the gate is the ceiling; the ruling stands unless Dave revises it.

### Pitfall 4: Canonical gate naming drift
**What goes wrong:** Test-strategy rows use non-canonical names for the three validation gates (Phase D's B2 finding: "Schema Validator → Policy Gate → Lineage Completeness Checker" drift).
**How to avoid:** Always: empty-operator guard → lineage strict equality → TTL bounds.

### Pitfall 5: Adding effort estimates
**What goes wrong:** Per-component effort estimates creep into verdict entries.
**How to avoid:** D-03 explicitly forbids them — risk/complexity note (low/med/high) only, with the rubric defined once (Claude's discretion).

### Pitfall 6: Forgetting the in-place DESIGN.md fixes are part of this phase
**What goes wrong:** Advisory items 4 and 5 (residual-risk wording, numerics disclaimer) are marked "disposed" in the appendix without the actual DESIGN.md commits existing.
**How to avoid:** Make the wording fixes their own task with commits; the appendix cites the commit hashes (D-11).

### Pitfall 7: Review sequencing
**What goes wrong:** Presenting to Dave before `/gsd-review` runs, or merging before D-GATE-F is logged.
**How to avoid:** §3.1 order is fixed: review → triage → Dave → log D-GATE-F in DECISIONS.md → merge `--no-ff` to main. Codex auth via `CODEX_API_KEY` (not OPENAI_API_KEY).

## Runtime State Inventory

Not applicable — no rename/refactor/migration; docs-only additions.

## State of the Art

Not applicable — internal-corpus phase; no external technology decisions are made here (all 49 D-IMPL rulings already fixed the stack: Python 3.12+, Pydantic v2, YAML+Jinja2 artifacts, Postgres/SQLite, sqlite-vec, LF A2A, three harness adapters).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The component list lands naturally in D-01's 30–50 band using "named Protocol or designed subsystem per DESIGN.md section" | Key Finding 2 | Low — if enumeration over/undershoots, adjust grouping granularity within Claude's discretion; D-01 bounds it |
| A2 | Appendix A contains exactly two "deferred"-status entries (per Cursor's review: "two ruled deferrals") | Key Finding 6 | Low — planner should grep Appendix A statuses during execution to confirm exact rows |

All other claims verified directly against repo files this session.

## Open Questions

1. **Exact component count and grouping** — Claude's discretion per CONTEXT.md; recommend the planner fix the enumeration in the first FEASIBILITY plan and freeze it before the appendix matrix is built (matrix keys depend on it).
2. **Risk-rating rubric definitions** — Claude's discretion; recommend defining low/med/high once in FEASIBILITY.md §1 (e.g., low = single well-precedented mechanism; med = novel composition of ruled mechanisms; high = external-dependency or cross-process surface with emergent standards) so ratings are auditable.
3. **Whether any D-02 gap actually fires** — cannot be known until verdict analysis runs; the plan should include the D-02 branch (new D-IMPL-NN + "needs design choice" + gate presentation) as a conditional path, not assume zero gaps.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | branch/commit/merge discipline | ✓ | (repo active) | — |
| `/gsd-review` + cross-AI CLIs (codex, cursor, gemini, ollama) | FEAS-04 gate | ✓ (all four ran in Phase 2) | — | Per §3.1; credentials from homecams .env |
| DESIGN.md / DECISIONS.md / SPEC_INVENTORY.md / 02-REVIEWS.md | All FEAS requirements | ✓ | current on main | — |

No missing dependencies.

## Validation Architecture

No code test framework applies (docs-only phase). Verification is mechanical document checking:

### Phase Requirements → Verification Map
| Req ID | Behavior | Verification | Automated Check |
|--------|----------|--------------|-----------------|
| FEAS-01 | Every component carries a verdict; 126-entry appendix matrix complete | Key-diff appendix matrix INV keys vs SPEC_INVENTORY (must be empty diff); grep verdict column for empty cells | `grep`-based, < 30s |
| FEAS-02 | ROADMAP milestones 1:1 with I.1–I.5; v0.1 surface explicit; deferral register ≥ 5 named rows | Cross-check milestone names against `.planning/ROADMAP.md` phases 4–8; grep register for the 5 mandatory items | `grep`/`diff`-based |
| FEAS-03 | Per-invariant test-strategy table complete; 12-row gate table all RESOLVED | Row count vs the 7 named invariants + D-08/D-09 rows; grep gate table for 12 D-IMPL IDs each marked RESOLVED with DECISIONS.md refs | `grep`-based |
| FEAS-04 | Review run, triaged, D-GATE-F logged, merged | `/gsd-review --phase Phase F --all` output exists; `grep D-GATE-F docs/DECISIONS.md`; `git log main` shows --no-ff merge | manual + grep |

### Wave 0 Gaps
None — no test infrastructure needed.

## Security Domain

Docs-only phase: no code, no packages, no network surfaces added. Applicable concerns:
- **Secrets:** Cross-AI credentials sourced from `/home/parkave/homecams_v2/.env` must never be committed (CLAUDE.md §3.1 / §2.2). The repo stays private (whitepaper is proprietary IP).
- No ASVS categories apply beyond secret handling; standard threat patterns not applicable.

## Sources

### Primary (HIGH confidence — all read/verified this session)
- `/home/parkave/ccf_code/CLAUDE.md` — §2.2, §3, §3.1, §9, §12, §13, §15
- `/home/parkave/ccf_code/docs/DESIGN.md` — §9 invariant/CI chapter (lines 747–790), Appendices A/B/C, section structure
- `/home/parkave/ccf_code/docs/DECISIONS.md` — D-IMPL resolution statuses
- `/home/parkave/ccf_code/docs/SPEC_INVENTORY.md` — 126-entry count (2071 lines)
- `/home/parkave/ccf_code/.planning/phases/02-phase-d-design/02-REVIEWS.md` — consensus triage, 7 advisories (line 236)
- `/home/parkave/ccf_code/.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- `.planning/phases/03-phase-f-feasibility-scoping/03-CONTEXT.md` — locked decisions D-01..D-11

## Metadata

**Confidence breakdown:**
- Corpus inputs and gate-list status: HIGH — verified by direct reads/greps this session
- Component enumeration approach: HIGH (bounded by D-01) with A1 noted
- Advisory list and dispositions: HIGH — exact source line located
- Pitfalls: HIGH — derived from Phase 2's actual blocking findings

**Research date:** 2026-07-25
**Valid until:** stable while `main` is unchanged post-D-GATE-D; re-verify if DESIGN.md/DECISIONS.md change before planning executes
