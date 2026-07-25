# Phase 1: Phase R — Research - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-24
**Phase:** 1-Phase R — Research
**Areas discussed:** Whitepaper source format

---

## Whitepaper source format

### Q1 — How should Phase R consume the spec (only the PDF exists)?

| Option | Description | Selected |
|--------|-------------|----------|
| Convert to Markdown first | One-time PDF→Markdown, committed as docs/CCF_Whitepaper_1-2.md before research; matches CLAUDE.md's canonical path, stable citation anchors | ✓ |
| Work from the PDF directly | Researcher reads PDF pages; citations reference PDF pages; .md path stays dangling | |
| Convert but keep PDF canonical | .md as working copy, PDF authoritative for any doubt | |

### Q2 — How is conversion accuracy verified?

| Option | Description | Selected |
|--------|-------------|----------|
| Section-by-section spot check | Verify every heading, figure, table, formal signature survived; fix before research reads it | ✓ |
| Full page-by-page diff review | Exhaustive comparison; highest confidence, slowest | |
| Convert and trust the tooling | Sanity-scan and start; fix garbling as found | |

### Q3 — How are figures handled (won't survive PDF→Markdown as text)?

| Option | Description | Selected |
|--------|-------------|----------|
| Extract images + placeholders | Figures extracted to docs/figures/, linked placeholders with number/caption in the .md | ✓ |
| Placeholders only, read PDF for figures | .md marks locations; researcher opens PDF when needed | |
| Transcribe figures to text/mermaid | Greppable but transcription risks fidelity drift | |

### Q4 — Where does conversion work belong?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase R plan, first task | Task 1 on phase-r branch, own deliverable-boundary commit | ✓ |
| Pre-phase setup, before planning | Do immediately alongside §14 skeleton checks | |
| You decide | Claude picks during planning | |

**Notes:** None beyond selections.

---

## Claude's Discretion

- Repo prerequisites (branch `master`→`main`, missing origin remote, `phase-r` branch, §14 skeleton) — sequencing left to planning; Dave-only actions surfaced as blockers.
- Inventory entry conventions (ID scheme, granularity, D-IMPL-30+ numbering).
- Homecams review depth (incl. whether to run read-only MongoDB metadata queries).

## Deferred Ideas

None — discussion stayed within phase scope.
