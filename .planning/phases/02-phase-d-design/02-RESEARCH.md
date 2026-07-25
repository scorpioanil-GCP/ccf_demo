# Phase 2: Phase D — Design - Research

**Researched:** 2026-07-25
**Domain:** Architecture-design documentation phase (docs-only; no code, no packages)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-IMPL resolution workflow**
- **D-01:** The ~49 open `D-IMPL-NN` decisions are resolved through **batched interactive sessions** with Dave — decisions grouped by theme (e.g., fabric fundamentals, agent framework, cross-process/trust, artifact persistence, orchestration/HITL/experience), presented one decision at a time via AskUserQuestion, with the ruling logged in `docs/DECISIONS.md` immediately.
- **D-02:** Presentation is **recommendation-first**: each decision shows Claude's recommended resolution (grounded in whitepaper fidelity and the inventory analysis) first with rationale, followed by 2–3 alternatives with consequences, per the CLAUDE.md §15 discipline. Homecams data points may inform the rationale but are never defaults.
- **D-03 (Dave override of the interleaved recommendation):** **All decisions are resolved before any DESIGN.md drafting begins.** The decision marathon is a distinct plan/wave that completes first; drafting starts only against a fully-ruled (or provisionally-ruled) decision log.
- **D-04:** If Dave defers a ruling mid-session, Claude's recommendation is adopted as a **provisional resolution, clearly marked** in DECISIONS.md; DESIGN.md designs against it with the affected sections isolated/flagged, and the gate review presents all provisionals for Dave's final confirmation.

**DESIGN.md structure**
- **D-05:** Top-level organization is **by Common Pillar** (CLAUDE.md §4), with the L1–L6 fabric detailed inside the Data and Context Layer pillar section, plus cross-cutting sections (Control/Data planes, invariant preservation, seams).
- **D-06:** Traceability is **inline citations + matrix appendix**: every design element cites the `INV-CHx-NN` entries it realizes inline, and an appendix table maps all 126 inventory entries → design section or `deferred: <reason>`, making DSGN-01 coverage mechanically checkable.
- **D-07:** Component altitude is **contract-level**: per component — responsibility, Protocol/type signatures (names, key methods, invariants enforced), seams, and the D-IMPL rulings it embodies. No method bodies, no file-level layout (that is Phase I territory).

**Diagram format & tooling**
- **D-08:** Diagrams are **Mermaid source committed in-repo** under `docs/diagrams/` (GitHub-native rendering, consistent with the rebuilt whitepaper figures, diffable).
- **D-09:** Beyond the 7 required component diagrams, add **sequence diagrams for load-bearing runtime flows** where a static view cannot show the invariant — e.g., L2 single-writer write path, A2A admission verification, HITL suspend/resume, decision-replay resolution.

**Invariant proof format**
- **D-10:** DESIGN.md carries a **dedicated "Invariant Preservation" chapter**: for each of the 7 named invariants — a structural argument (which design construct makes violation impossible), the enforcement point, and the diagram/section that shows it — summarized in a table `/gsd-review` can check row-by-row. An invariant without a structural argument is a blocking finding (CLAUDE.md §3.1).
- **D-11:** The invariant chapter also **specifies the CI enforcement design** for Phase I (import-lint scopes, prompt-shaped-literal lint, `@algorithmic` lint, composition-preservation test harness shape, replay-by-construction checks) so Phase F's test strategy (FEAS-03) and Phase I implement against it rather than re-deriving.

### Claude's Discretion
- Decision-batch grouping and ordering within the marathon (gating-list decisions D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28 should be prominent).
- Diagram naming convention, C4 layering, and per-diagram detail depth.
- How DECISIONS.md entries are restructured when a ruling lands (status, date, ruling text format), consistent with the existing entry format.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DSGN-01 | `docs/DESIGN.md` maps every inventory entry to a design element or explicit deferral, preserving every named invariant by construction on paper | Inventory verified at exactly 126 `### INV-` entries (grep-confirmed); pillar-by-pillar mapping section (SPEC_INVENTORY.md line 1853) is the pre-built cross-reference for the D-05 pillar organization; the D-06 matrix appendix is mechanically checkable against the 126-entry census |
| DSGN-02 | `docs/DECISIONS.md` — every open `D-IMPL-NN` resolved with Dave's ruling or flagged as gating | Full open-decision census below: 28 open of D-IMPL-01..29 (canonical home CLAUDE.md §12; D-IMPL-10 provisional) + 21 open of D-IMPL-30..50 (D-IMPL-51 RESOLVED) = **49 open decisions**, matching CONTEXT's "~49". Entry format for rulings established (title, status, date, originating section) |
| DSGN-03 | `docs/diagrams/` — one diagram per pillar (5), plus harness-adapter seam and ArtifactStore seam diagrams | `docs/diagrams/` exists and is empty; Mermaid convention established by rebuilt whitepaper figures; `mmdc` available locally for render-verification |
| DSGN-04 | Phase D reviewed, triaged, Dave-approved, `D-GATE-D` logged, phase branch merged to `main` | §3.1 protocol steps and Phase D verification criteria enumerated below; Phase R gate provides the executed precedent (01-REVIEWS.md, review-triage fragment, D-GATE-R entry format) |
</phase_requirements>

## Summary

This is a pure documentation/design phase — no libraries to select, no packages to install, no runtime dependencies. The research questions that matter are all *internal*: the exact state of the decision log, the shape of the inventory Phase D must trace against, the review criteria the deliverables will be judged by, and process mechanics (branching, gate protocol, Mermaid conventions). All were verified directly against the repo. [VERIFIED: repo inspection]

Three facts dominate planning. First, D-GATE-R is logged (docs/DECISIONS.md, approved 2026-07-25) and `phase-r` is merged to `main` (commit 1891b40) — the phase dependency is satisfied, but the working tree currently sits on `phase-r`; Phase D must branch `phase-d` off `main`. Second, the decision marathon (locked D-03) is a hard-sequenced first milestone: 49 open D-IMPL decisions, of which the 12-item Phase I gating list (D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28) is most prominent — this wave is human-interactive (AskUserQuestion) and therefore inherently serial and un-parallelizable. Third, DESIGN.md drafting *after* the marathon is highly parallelizable by pillar (five pillar sections + cross-cutting chapters + diagrams), because SPEC_INVENTORY.md already partitions all 126 entries by pillar.

**Primary recommendation:** Plan three sequential milestones — (1) decision marathon in themed batches with immediate DECISIONS.md logging, (2) parallel pillar-by-pillar DESIGN.md + diagram drafting against the ruled log with a final traceability-matrix + Invariant Preservation synthesis pass, (3) gate wave (`/gsd-review --phase "Phase D" --all` → triage → Dave presentation with consolidated provisional list → D-GATE-D → merge).

## Architectural Responsibility Map

Not applicable in the software-tier sense (no runtime). Deliverable-ownership map instead:

| Capability | Owner artifact | Secondary | Rationale |
|------------|---------------|-----------|-----------|
| Decision rulings | `docs/DECISIONS.md` | CLAUDE.md §12 (canonical home for 01–29 text) | Log is append/extend, established entry format |
| Component contracts, invariant proofs, traceability matrix | `docs/DESIGN.md` | — | Locked D-05/D-06/D-07/D-10/D-11 |
| Structural/sequence diagrams | `docs/diagrams/*.mmd` | referenced from DESIGN.md sections | Locked D-08/D-09 |
| Gate evidence | `.planning/phases/02-*/02-REVIEWS.md` + fragments | D-GATE-D entry in DECISIONS.md | Phase R precedent (01-REVIEWS.md, fragments/review-triage.md) |

## Standard Stack

No external packages. Tooling in play:

| Tool | Status | Purpose |
|------|--------|---------|
| Mermaid (GitHub-native rendering) | n/a — markup, not a dependency | Diagram source per locked D-08 [VERIFIED: docs/figures uses same convention] |
| `mmdc` (mermaid-cli) | Installed at `~/.nvm/.../bin/mmdc` | Optional local render-verification of `.mmd` files before commit [VERIFIED: command -v] |
| git / gh | Installed | `phase-d` branch, merge at gate [VERIFIED] |

## Package Legitimacy Audit

Not applicable — this phase installs no packages. **Packages removed:** none. **Packages flagged:** none.

## Key Facts for Planning (verified repo state)

### Decision census (drives the marathon plan)

[VERIFIED: docs/DECISIONS.md + SPEC_INVENTORY.md "Open Questions for Phase D" section, line 1914]

- **D-IMPL-01..29** — scaffolded in CLAUDE.md §12 (canonical home; DECISIONS.md references, does not duplicate). D-IMPL-10 provisionally resolved (monorepo; adapter-split remainder still open). All others open.
- **D-IMPL-30..50** — full entries in docs/DECISIONS.md with quoted ambiguous passages and proposed readings (Phase R synthesis, 2026-07-25). All open.
- **D-IMPL-51** — RESOLVED (live MongoDB query executed at Phase R gate). Not part of the marathon.
- **Total open: 49.** Phase I gating list (must be at least provisionally resolved before Phase 4): D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28.
- Homecams triangulation data points are already recorded against D-IMPL-04(b), 05, 07, 09, 26, 28, 33, 36, 49, 50 — usable in recommendation rationales, never as defaults (CLAUDE.md §2.1).
- Known cross-decision dependencies (order batches accordingly): D-IMPL-41 depends on D-IMPL-01 (language target); D-IMPL-34 interacts with 02; D-IMPL-36/44/50 interact with 06/26/27; D-IMPL-12 interacts with 29; D-IMPL-46 with 09; D-IMPL-18 with 27. **Resolve D-IMPL-01 first** — many downstream signatures depend on the language target.
- Suggested theme batches (Claude's discretion, honoring gating prominence): (1) fabric & runtime fundamentals 01–09 + 33–41 subset, (2) agent framework 11, 12, 19, 28, 29 + 49, (3) cross-process/trust 13–16 + 45, 46, (4) artifact persistence & replay 26, 27, 06 + 36, 44, 50, (5) orchestration/HITL/experience 17, 18, 20–23 + 43, (6) harness 24, 25, (7) whitepaper-ambiguity cluster 30, 31, 32, 42, 47, 48.

### Inventory shape (drives DESIGN.md traceability)

[VERIFIED: docs/SPEC_INVENTORY.md, 2071 lines]

- Exactly **126 `### INV-` entries**: CH5 ×10, CH6 ×8, CH7 ×84, CH8 ×24. Key scheme `INV-CHx-NN`.
- Pre-built sections Phase D consumes directly: Named Architectural Invariants table (line 1815 — all 7 invariants with realizing entries, plus subsidiary invariants list), SDK Extensions and Whitepaper Hooks (line 1833 — 11 extensions), **Pillar-by-Pillar Mapping (line 1853 — the primary Phase D cross-reference, partitioning entries by pillar)**, Governance Decisions D-NN (line 1698), Load-Bearing Figures (line 1754, 50 figures), Review Appendix with carried-forward advisory findings (line 2063 — read and address/carry these).
- The D-06 matrix appendix is mechanically checkable: `grep -c "### INV-"` = 126 rows expected.

### Gate protocol facts (drive the closing wave)

[VERIFIED: CLAUDE.md §3.1 + Phase 1 precedent files]

- Phase D review verifies, minimally: every inventory entry mapped or explicitly deferred; every open D-IMPL resolved (ruling recorded) or flagged gating; diagram set complete (5 pillars + 2 seams); all 7 named invariants preserved *by construction, on paper* — a missing structural argument is a **blocking** finding.
- Sequence is fixed: self-review → blocking/advisory triage → present to Dave (deliverables + review report + triage + **consolidated provisional-resolution list** per CONTEXT specifics) → D-GATE-D entry → merge `phase-d` to `main`, merge commit referencing the gate.
- Phase R precedent artifacts to mirror: `01-REVIEWS.md`, `fragments/review-triage.md`, D-GATE-R entry format (approver, date, scope, deliverables list).

### Housekeeping items found

- **Branch state:** repo currently on `phase-r`; `main` contains the merged Phase R deliverables. First task: `git checkout main && git checkout -b phase-d`. [VERIFIED: git branch]
- **DECISIONS.md hygiene:** Phase 1 VERIFICATION flagged a cosmetic cleanup (stale pending-gate text / duplicated heading) recommended "early in Phase D" — cheap one-line fix to fold into the first plan. [CITED: .planning/phases/01-phase-r-research/01-VERIFICATION.md]
- `docs/DESIGN.md` is a 5-line placeholder to be replaced wholesale. `docs/diagrams/` exists, empty. [VERIFIED]

## Architecture Patterns

### Recommended DESIGN.md skeleton (per locked D-05/D-06/D-07/D-10/D-11)

```
docs/DESIGN.md
├── 1. Overview + reading guide (pillar map, decision-log linkage)
├── 2. Pillar: Data and Context Layer  (L1–L6 detailed here; largest section — ~102 of 126 entries)
├── 3. Pillar: Core Agent Types        (archetype/agent separation, factory, skilling)
├── 4. Pillar: Orchestration Layer
├── 5. Pillar: Human in the Loop and Control
├── 6. Pillar: Experience Layer
├── 7. Cross-cutting: Control Plane / Data Plane
├── 8. Cross-cutting: Seams (harness adapter, ArtifactStore, MCP roles, A2A)
├── 9. Invariant Preservation chapter  (7 rows: structural argument, enforcement point, diagram ref
│                                       + CI enforcement design per D-11)
└── Appendix A. Traceability matrix    (126 rows: INV-CHx-NN → §section | deferred: <reason>)
    Appendix B. Review appendix        (advisory findings carried forward, per §3.1)
```

Per-component template (contract altitude, D-07): responsibility · Protocol/type signature names + key methods · invariants enforced · seams touched · D-IMPL rulings embodied · inline INV citations.

### Diagram set (per DSGN-03 + locked D-09)

Required 7 component diagrams: `pillar-data-context.mmd`, `pillar-agent-types.mmd`, `pillar-orchestration.mmd`, `pillar-hitl.mmd`, `pillar-experience.mmd`, `seam-harness-adapter.mmd`, `seam-artifact-store.mmd`. Plus D-09 sequence diagrams (minimum set named in CONTEXT): `seq-single-writer-write-path.mmd`, `seq-a2a-admission.mmd`, `seq-hitl-suspend-resume.mmd`, `seq-replay-resolution.mmd`. Naming convention is Claude's discretion — the `pillar-*/seam-*/seq-*` prefix scheme above is recommended for review checkability. Verify each renders with `mmdc -i <f>.mmd -o /dev/null` (or scratchpad output) before commit.

### Pattern: decision-marathon wave shape

Each batch = one interactive session block: for each decision, present recommendation-first (rationale citing INV entries and whitepaper sections) + 2–3 alternatives with consequences via AskUserQuestion → write ruling to DECISIONS.md **immediately** (D-01) → commit at batch boundary. Deferred rulings become clearly-marked provisionals (D-04) accumulated into a "Provisional Resolutions" list for the gate presentation. Recommended DECISIONS.md ruling format (Claude's discretion, consistent with existing entries): keep the original entry text, append `**RESOLVED** — <ruling>. Date. Approver: Dave.` or `**PROVISIONAL** — <adopted recommendation>. Date. Pending Dave confirmation at D-GATE-D.`

### Anti-patterns to avoid

- **Writing any implementation code** — Phase boundary violation (CLAUDE.md §3). Signatures in prose/diagrams only; no `/src` files.
- **Drafting design prose before the marathon completes** — explicit Dave override (locked D-03).
- **Treating Homecams resolutions as defaults** — data points in rationale only (§2.1).
- **File-level layout in DESIGN.md** — that is Phase I territory (locked D-07).
- **Silently absorbing an unresolved decision into the design** — must be a ruling, a marked provisional, or a gating flag; nothing else.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Traceability coverage check | Manual eyeballing of 126 rows | `grep`-based census: 126 `### INV-` keys in inventory vs 126 matrix rows in DESIGN.md appendix | Mechanically checkable per locked D-06; review can rerun it |
| Decision inventory | Re-deriving open decisions | SPEC_INVENTORY.md "Open Questions for Phase D" section + DECISIONS.md | Already complete and cross-referenced |
| Pillar partitioning of entries | Fresh entry-by-entry sort | SPEC_INVENTORY.md Pillar-by-Pillar Mapping table | Phase R built it as "the primary cross-reference for Phase D" |
| Diagram rendering pipeline | Custom render scripts | Committed `.mmd` + GitHub-native rendering; `mmdc` for spot checks | Locked D-08; convention already established by whitepaper figures |

## Common Pitfalls

### Pitfall 1: Marathon stalls block everything
**What goes wrong:** 49 interactive decisions is long; if Dave is unavailable mid-batch, the whole phase halts (D-03 forbids drafting ahead).
**How to avoid:** D-04 is the pressure valve — a deferral converts to a marked provisional and the marathon continues. Plan batches so the 12 gating-list decisions land earliest; order D-IMPL-01 first (language target gates many signature-level recommendations).
**Warning signs:** A batch session ends with decisions neither ruled nor provisionally adopted.

### Pitfall 2: Invariant chapter asserts instead of argues
**What goes wrong:** "The design preserves single-writer" without naming the construct that makes violation impossible → blocking finding at review (§3.1).
**How to avoid:** For each of the 7 invariants use the D-10 triple: structural argument + enforcement point + diagram/section reference, in a row-checkable table. Cross-check against the inventory's Named Architectural Invariants table (line 1815) which lists the realizing INV entries per invariant.

### Pitfall 3: Traceability drift during parallel drafting
**What goes wrong:** Pillar sections drafted in parallel each cite INV entries inline, but the appendix matrix is assembled last and misses or double-books entries (some INV entries plausibly touch two pillars).
**How to avoid:** Assign each of the 126 entries to exactly one owning section up front (from the pillar mapping; cross-pillar entries get a primary owner + "see also"); synthesis task builds the matrix from that assignment and greps DESIGN.md to confirm every key appears.

### Pitfall 4: Provisionals lost at the gate
**What goes wrong:** D-04 provisionals scattered through DECISIONS.md; gate presentation forgets one; Dave approves without confirming it.
**How to avoid:** Maintain a running "Provisional Resolutions pending D-GATE-D confirmation" list (CONTEXT specifics require the consolidated list at the gate); review checks it against a grep for `PROVISIONAL` in DECISIONS.md.

### Pitfall 5: Diagrams that don't render on GitHub
**What goes wrong:** Mermaid features/syntax that mmdc accepts but GitHub's renderer rejects (or vice versa), discovered at review.
**How to avoid:** Stick to core flowchart/sequenceDiagram syntax; spot-check each `.mmd` with local `mmdc` and visually confirm at least one representative diagram on the pushed branch. [ASSUMED — GitHub/mmdc feature parity not verified this session; low risk with core syntax]

### Pitfall 6: Wrong branch base
**What goes wrong:** Branching `phase-d` off the current `phase-r` HEAD instead of `main` (they should be identical post-merge, but `main` is the approved-state base per §2.2).
**How to avoid:** `git checkout main && git pull && git checkout -b phase-d` as the phase's first action; push with upstream.

## Runtime State Inventory

Not applicable — not a rename/refactor/migration phase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git + origin remote | branch/merge/gate | ✓ | wired to github.com/drcastillo/ccf_code (SSH) | — |
| mmdc (mermaid-cli) | diagram render checks | ✓ | ~/.nvm node v24.13.1 bin | GitHub-native rendering only |
| AskUserQuestion (interactive mode) | decision marathon | ✓ (`mode: interactive` in .planning/config.json) | — | — |

No missing dependencies.

## Validation Architecture

No test framework exists or is needed (docs-only phase; no code permitted). Validation is mechanical doc checks:

### Phase Requirements → Check Map
| Req ID | Behavior | Check Type | Automated Command | Exists? |
|--------|----------|-----------|-------------------|---------|
| DSGN-01 | 126/126 entries mapped; 7 invariant rows with structural arguments | grep census | `grep -c 'INV-CH' docs/DESIGN.md` appendix rows = 126; invariant table rows = 7 | ✅ (grep) |
| DSGN-02 | 49 open decisions each RESOLVED / PROVISIONAL / flagged gating | grep census | `grep -cE 'RESOLVED|PROVISIONAL|GATING' docs/DECISIONS.md` vs open-decision list | ✅ (grep) |
| DSGN-03 | 7 required diagrams (+D-09 sequences) present and rendering | file check + render | `ls docs/diagrams/*.mmd`; `for f in docs/diagrams/*.mmd; do mmdc -i "$f" -o <scratch>/out.svg; done` | ✅ (mmdc verified) |
| DSGN-04 | Review run, triaged, D-GATE-D logged, merged | manual + grep | `/gsd-review --phase "Phase D" --all`; `grep 'D-GATE-D' docs/DECISIONS.md`; merge commit on main | manual gate (Dave) |

- **Per task commit:** relevant grep check above
- **Phase gate:** full DSGN-01..04 checklist + `/gsd-review` before Dave presentation
- **Wave 0 gaps:** none — no test infrastructure applies

## Security Domain

Not materially applicable — no code, no inputs, no packages this phase. The *design content* must, however, specify security-relevant mechanism (A2A identity/signing D-IMPL-15, admission verification D-IMPL-16, HITL identity binding D-IMPL-21, trust posture of the ArtifactStore) because the inventory commits to them; these are design sections, not phase-execution security controls.

## Project Constraints (from CLAUDE.md)

- Phase boundary: **no implementation code** in Phase D (§3); redesign-during-I requires a mini-cycle.
- Whitepaper fidelity wins over everything; cite `docs/CCF_Whitepaper_1-2.md` sections (never the PDF — locked Phase 1 decision).
- Surface gaps as `D-IMPL-NN` and stop; never pick a default silently (§15). Homecams = data points only (§2.1).
- All 7 named invariants must be shown preserved *by construction on paper* — a structural gap is a blocking review finding (§3.1 Phase D criteria).
- Diagram set: one per pillar + harness-adapter seam + ArtifactStore seam (§3, §14).
- Branch discipline: work on `phase-d`; merge to `main` only at D-GATE-D; merge commit references the gate; no force-push to `main` (§2.2). Commit at deliverable boundaries with messages naming the section or D-IMPL served.
- Model mandate: Fable 5, "high" effort for Phase D (§3).
- `/gsd-review` passing is necessary, never sufficient — Dave's approval is the gate (§3.1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | GitHub-native Mermaid rendering accepts the same core syntax mmdc renders | Pitfall 5 | Cosmetic; fix diagrams after push |

## Open Questions (RESOLVED)

1. **Does `/gsd-review --phase "Phase D" --all` expect specific artifact filenames beyond the deliverables?** RESOLVED — recommendation adopted: mirror the Phase 1 evidence-file pattern. Plan 02-11 produces `02-REVIEWS.md` + `fragments/review-triage.md` exactly as in the Phase R precedent.
2. **How many D-09 sequence diagrams beyond the named four?** RESOLVED — recommendation adopted: exactly the four sequence diagrams named in CONTEXT (no additions were found where a static diagram could not show an invariant); realized across plans 02-05..02-09.

## Sources

### Primary (HIGH confidence — direct repo inspection, 2026-07-25)
- `docs/SPEC_INVENTORY.md` (2071 lines; entry census, invariants table, pillar mapping, open-questions section, review appendix)
- `docs/DECISIONS.md` (D-IMPL-30..51 full text; D-GATE-R entry; ruling format)
- `CLAUDE.md` rev 4 (§2.2, §3, §3.1, §4, §12, §15, §16)
- `.planning/phases/02-phase-d-design/02-CONTEXT.md`; `.planning/REQUIREMENTS.md`; `.planning/config.json`
- `.planning/phases/01-phase-r-research/01-VERIFICATION.md`, `01-PATTERNS.md` (gate precedent, doc-phase pattern)
- Local environment probes (git branches, mmdc/node availability)

## Metadata

**Confidence breakdown:**
- Decision census & repo state: HIGH — grep/read-verified this session
- Process/gate mechanics: HIGH — verbatim from CLAUDE.md §3.1 + executed Phase R precedent
- Mermaid rendering parity: MEDIUM — one [ASSUMED] item, low impact

**Research date:** 2026-07-25
**Valid until:** stable while repo unchanged; re-verify decision census if DECISIONS.md is edited before planning
