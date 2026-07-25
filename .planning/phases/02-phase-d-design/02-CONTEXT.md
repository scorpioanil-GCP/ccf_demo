# Phase 2: Phase D — Design - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce the SDK's architectural shape on paper: `docs/DESIGN.md` mapping all
126 SPEC_INVENTORY entries to design elements or explicit deferrals with every
named invariant preserved by construction; `docs/DECISIONS.md` with every open
`D-IMPL-NN` resolved (Dave's ruling recorded) or flagged as gating; and
`docs/diagrams/` with the complete set — one per Common Pillar (five), plus
the harness-adapter seam and ArtifactStore seam diagrams. No implementation
code (CLAUDE.md §3). Branch `phase-d`, model mandate Fable 5 "high" effort.
Ends with `/gsd-review --phase Phase D --all` → triage → Dave approval →
`D-GATE-D` → merge to `main` (CLAUDE.md §3.1).

</domain>

<decisions>
## Implementation Decisions

### D-IMPL resolution workflow
- **D-01:** The ~49 open `D-IMPL-NN` decisions are resolved through **batched
  interactive sessions** with Dave — decisions grouped by theme (e.g., fabric
  fundamentals, agent framework, cross-process/trust, artifact persistence,
  orchestration/HITL/experience), presented one decision at a time via
  AskUserQuestion, with the ruling logged in `docs/DECISIONS.md` immediately.
- **D-02:** Presentation is **recommendation-first**: each decision shows
  Claude's recommended resolution (grounded in whitepaper fidelity and the
  inventory analysis) first with rationale, followed by 2–3 alternatives with
  consequences, per the CLAUDE.md §15 discipline. Homecams data points may
  inform the rationale but are never defaults.
- **D-03 (Dave override of the interleaved recommendation):** **All decisions
  are resolved before any DESIGN.md drafting begins.** The decision marathon
  is a distinct plan/wave that completes first; drafting starts only against a
  fully-ruled (or provisionally-ruled) decision log.
- **D-04:** If Dave defers a ruling mid-session, Claude's recommendation is
  adopted as a **provisional resolution, clearly marked** in DECISIONS.md;
  DESIGN.md designs against it with the affected sections isolated/flagged,
  and the gate review presents all provisionals for Dave's final confirmation.

### DESIGN.md structure
- **D-05:** Top-level organization is **by Common Pillar** (CLAUDE.md §4),
  with the L1–L6 fabric detailed inside the Data and Context Layer pillar
  section, plus cross-cutting sections (Control/Data planes, invariant
  preservation, seams).
- **D-06:** Traceability is **inline citations + matrix appendix**: every
  design element cites the `INV-CHx-NN` entries it realizes inline, and an
  appendix table maps all 126 inventory entries → design section or
  `deferred: <reason>`, making DSGN-01 coverage mechanically checkable.
- **D-07:** Component altitude is **contract-level**: per component —
  responsibility, Protocol/type signatures (names, key methods, invariants
  enforced), seams, and the D-IMPL rulings it embodies. No method bodies, no
  file-level layout (that is Phase I territory).

### Diagram format & tooling
- **D-08:** Diagrams are **Mermaid source committed in-repo** under
  `docs/diagrams/` (GitHub-native rendering, consistent with the rebuilt
  whitepaper figures, diffable).
- **D-09:** Beyond the 7 required component diagrams, add **sequence diagrams
  for load-bearing runtime flows** where a static view cannot show the
  invariant — e.g., L2 single-writer write path, A2A admission verification,
  HITL suspend/resume, decision-replay resolution.

### Invariant proof format
- **D-10:** DESIGN.md carries a **dedicated "Invariant Preservation" chapter**:
  for each of the 7 named invariants (single-writer, composition-preservation,
  three validation gates, Algorithmic ⇄ Semantic Alternation,
  audit-by-construction, No-Hardcoding, zero harness imports in core) — a
  structural argument (which design construct makes violation impossible), the
  enforcement point, and the diagram/section that shows it — summarized in a
  table `/gsd-review` can check row-by-row. An invariant without a structural
  argument is a blocking finding (CLAUDE.md §3.1).
- **D-11:** The invariant chapter also **specifies the CI enforcement design**
  for Phase I (import-lint scopes, prompt-shaped-literal lint, `@algorithmic`
  lint, composition-preservation test harness shape, replay-by-construction
  checks) so Phase F's test strategy (FEAS-03) and Phase I implement against
  it rather than re-deriving.

### Claude's Discretion
- Decision-batch grouping and ordering within the marathon (gating-list
  decisions D-IMPL-01..05, 11, 14, 17, 20, 24, 26, 28 should be prominent).
- Diagram naming convention, C4 layering, and per-diagram detail depth.
- How DECISIONS.md entries are restructured when a ruling lands (status,
  date, ruling text format), consistent with the existing entry format.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project governance
- `CLAUDE.md` — canonical project definition (rev 4): §3 Phase D scope and
  out-of-scope, §3.1 review protocol and Phase D verification criteria, §4
  pillars, §12 decision log scaffolding + Phase I gating list, §15
  ambiguity discipline. Overrides everything else.

### Phase R deliverables (design inputs)
- `docs/SPEC_INVENTORY.md` — the 126-entry inventory Phase D designs
  against; includes governance D-NN catalog, load-bearing figures, named
  invariants, SDK extensions, pillar mapping, homecams-patterns appendix.
- `docs/DECISIONS.md` — D-IMPL-30..51 entries (with quoted ambiguous
  passages and proposed readings) plus status notes on D-IMPL-01..29;
  the document Phase D updates with rulings.
- `docs/CCF_Whitepaper_1-2.md` — canonical specification; cite sections
  from it, never the PDF (locked D-01 from Phase 1).

### Planning
- `.planning/ROADMAP.md` — Phase 2 goal and success criteria (DSGN-01..04).
- `.planning/REQUIREMENTS.md` — DSGN-01..04 definitions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/DESIGN.md` exists as a placeholder (initialized in Phase R setup) —
  Phase D replaces it with the real design.
- `docs/diagrams/` directory exists; whitepaper figures already render as
  Mermaid + repo-local PNGs — the Mermaid convention is established.
- `docs/DECISIONS.md` entry format (title, status, date, originating section,
  readings with consequences) is established — rulings should extend it, not
  restructure it wholesale.

### Established Patterns
- Phase R fragments/synthesis workflow under `.planning/phases/01-*` shows
  the multi-plan wave pattern the planner can reuse.
- No production code exists (correct — Phase D writes none).

### Integration Points
- Deliverables: `docs/DESIGN.md`, `docs/DECISIONS.md` (updated),
  `docs/diagrams/*.mmd`. Branch `phase-d` off `main` (post-D-GATE-R).

</code_context>

<specifics>
## Specific Ideas

- The decision marathon is the phase's first milestone and a hard
  prerequisite: no design prose until the log is fully ruled or provisional
  (Dave's explicit override of the interleaved default).
- The gate presentation must include a consolidated list of every
  provisional resolution for Dave's final confirmation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2 - Phase D — Design*
*Context gathered: 2026-07-25*
