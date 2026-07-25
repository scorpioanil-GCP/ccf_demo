# Phase 1: Phase R — Research - Context

**Gathered:** 2026-07-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract every commitment in the CCF whitepaper into `docs/SPEC_INVENTORY.md` —
a structured, component-keyed catalog per CLAUDE.md §16 — plus the
`homecams-patterns` appendix (inherit / do-not-inherit markers) and a
`D-IMPL-NN` entry in `docs/DECISIONS.md` for every open question. No design
choices, no code, no SDK diagrams (CLAUDE.md §3, Phase R). Phase ends with
`/gsd-review --phase Phase R --all` → triage → Dave approval → `D-GATE-R` →
merge `phase-r` to `main`.

</domain>

<decisions>
## Implementation Decisions

### Whitepaper source format
- **D-01:** The whitepaper exists only as `docs/CCF_Whitepaper_1-2.pdf`. Convert
  it to Markdown and commit as `docs/CCF_Whitepaper_1-2.md` — the path CLAUDE.md
  treats as canonical. All inventory citations reference the `.md` sections.
- **D-02:** Conversion is **Task 1 of the Phase R plan**, on the `phase-r`
  branch, committed at its own deliverable boundary. Research tasks depend on it.
- **D-03:** Verify conversion with a **section-by-section spot check** against
  the PDF: every section heading, every figure (Fig-CHNN-MM), tables, and formal
  type signatures must survive. Fix defects before any research task reads the
  `.md`.
- **D-04:** Figures: **extract each figure from the PDF as an image into
  `docs/figures/`**, with a linked placeholder (figure number + caption) at its
  location in the `.md`. The researcher reads the images directly when building
  the load-bearing-figures section of the inventory.

### Claude's Discretion
User explicitly left these to Claude during planning:
- **Repo prerequisites:** current branch is `master` (not `main`), no `origin`
  remote, no `phase-r` branch — CLAUDE.md §2.2/§14 expect `main`, origin
  `github.com/drcastillo/ccf_code` (private, created by Dave), and phase work on
  `phase-r`. Plan should sequence the §14 prerequisite checks/fixes sensibly;
  anything only Dave can do (creating the private GitHub repo) is a surfaced
  blocker, not silently skipped.
- **Inventory entry conventions:** component-key/ID scheme, entry granularity,
  and D-IMPL numbering for new open questions (CLAUDE.md §12 ends at D-IMPL-29;
  new ones start at D-IMPL-30).
- **Homecams review depth:** code read per §2.1 discipline; whether/how to run
  the read-only MongoDB metadata queries §2.1 mentions is Claude's call during
  planning (surface as a question if connection details are missing).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project governance
- `CLAUDE.md` — canonical project definition (rev 4): §3 phase discipline,
  §3.1 review protocol, §16 Phase R success criteria, §2.1 Homecams discipline,
  §12 decision log scaffolding. Overrides everything else.

### Specification
- `docs/CCF_Whitepaper_1-2.pdf` — the only extant copy of the canonical spec
  (PDF). Source for the D-01 conversion.
- `docs/CCF_Whitepaper_1-2.md` — does not exist yet; produced by Task 1
  (D-01..D-04). Becomes the citation target for every inventory entry.

### Reference implementation
- `/home/parkave/homecams_v2` — read-only pattern triangulation (never port
  code); source for the `homecams-patterns` appendix.
- `/home/parkave/homecams_v2/CLAUDE.md` — read once, additive best-practices
  context only.

### Planning
- `.planning/REQUIREMENTS.md` — RSCH-01..04 for this phase.
- `.planning/ROADMAP.md` — Phase 1 success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Repo state (scouted 2026-07-24)
- Repo contains only `CLAUDE.md`, `docs/CCF_Whitepaper_1-2.pdf`, `.planning/`,
  and stray files (`._CLAUDE.md`, `CLAUDE.md.orig` — untracked; a `.gitignore`
  per §2.2 should exclude junk files).
- Git: branch `master`, no remote, no `.gitignore`. §14 skeleton directories
  (`/references`, `/src`, `/runtime`, `/tests`, `/examples`, `docs/diagrams`)
  not yet created — §14 items 1–5 are pre-research setup work.
- No production code exists (correct for Phase R).

### Integration Points
- Deliverables land in `docs/SPEC_INVENTORY.md` and `docs/DECISIONS.md`
  (initialize with placeholder headers per §14 item 5).
- Model mandate for all Phase R work: Anthropic Fable 5, "high" effort.

</code_context>

<specifics>
## Specific Ideas

- Fidelity is success condition #1: the converted `.md` must be verifiably
  faithful before the inventory cites it — hence the spot-check gate (D-03).
- If Phase R produces a summary instead of an inventory, redo it (CLAUDE.md §16).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1 - Phase R — Research*
*Context gathered: 2026-07-24*
