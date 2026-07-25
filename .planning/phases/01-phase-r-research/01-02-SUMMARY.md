---
phase: 01-phase-r-research
plan: 02
subsystem: docs
tags: [whitepaper-conversion, figures, D-01, D-02, D-04]
requires: [01-01]
provides:
  - docs/figures/ (all 50 Fig-CHNN-MM images, chapters 1-8)
  - docs/CCF_Whitepaper_1-2.md (canonical .md, Ch 1-6 complete)
affects: [01-03, 01-04, 01-05, 01-06, 01-07, 01-08, 01-09]
tech-stack:
  added: []
  patterns: [hybrid pdftotext + visual PDF reconstruction, pdfimages page-mapped extraction]
key-files:
  created:
    - docs/figures/Fig-CH01-01.png … Fig-CH08-06.png (50 files)
    - docs/CCF_Whitepaper_1-2.md (Ch 1-6; Ch 7-8 appended by plans 01-05..01-08)
  modified: []
decisions:
  - "Notdef glyphs in the PDF's embedded font (invisible in the PDF itself) reconstructed per context: ∘ (operator composition), ⇄ (Search⇄Inference / Algorithmic⇄Semantic), → (BI→Agentic contrast pairs, §4.3/§5.1/§6.1 verdict arrows), λ_c (half-life)"
  - "Fig-CH02-01 (table-figure, no embedded raster) captured as a pdftoppm full-page render of PDF page 21"
  - "PDF caption on page 26 is misnumbered 'Fig-CH02-01'; prose confirms the diagram is Fig-CH02-02 — file named Fig-CH02-02.png, converter note added in the .md caption"
metrics:
  duration: "~2.5h"
  completed: "2026-07-25"
  tasks: 3
  commits: 3
---

# Phase 1 Plan 02: Figure Extraction + Whitepaper Ch 1–6 Conversion Summary

Canonical `docs/CCF_Whitepaper_1-2.md` (Ch 1–6, 16 linked figure placeholders, clean glyphs) plus all 50 whitepaper figures extracted and named in `docs/figures/`, executing locked decisions D-01/D-02/D-04.

## What Was Built

- **Task 1 (876418b):** All 50 figures in `docs/figures/` named `Fig-CHNN-MM.png`. 49 extracted as native-resolution embedded rasters via `pdfimages -all -p` with a caption-to-page / raster-to-page join (exact 1:1 after resolving CH02); Fig-CH02-01 is a vector/table figure with no raster and was rendered as a full page via `pdftoppm -r 150` (the fallback the plan sanctioned). Per-chapter counts match the verified inventory: CH01=3, CH02=2, CH03=4, CH04=2, CH05=2, CH06=3, CH07=28, CH08=6. No generic `fig-*` residue.
- **Task 2 (ecdce23):** Ch 1–4 converted. Front matter (What's New in v1.1, Forward, Executive Summary, Abstract), clean Contents list, `## N.` chapter / `### N.M` / `#### N.M.K` heading scheme, 11 figure placeholders, and three tables rebuilt as Markdown (§2.1 peer-bank benchmark, §3.6 failure-mode table, §4.5.1 five-row platform landscape). Conversion note at file top states the D-01 canonical-citation role and the glyph-reconstruction conventions.
- **Task 3 (8876ec6):** Ch 5–6 appended. Notation-heavy content reconstructed visually: `G(E, R, T, P, Π, L)` (display block in §5.2, 19 occurrences file-wide), `⇄` in the §6.6 heading and Search ⇄ Inference references, the nine-element Context Product specification (§6.3), and six tables (§5.1 six-tuple verdicts, §5.5 seven-architecture mapping, §6.1 eight-property contract test + six-row comparison, §6.3 nine elements, §6.5.1 MCP responsibility split). 5 figure placeholders (CH05 ×2, CH06 ×3).

## Verification

- `ls docs/figures/ | grep -c '^Fig-CH'` = 50; per-chapter counts exact.
- `grep -c '^### 5\.'` = 7; `grep -c '^### 6\.'` = 6; `Π` present (33 lines), `⇄` present (5 lines).
- `grep -Ec '^!\[Fig-CH0[1-6]-'` = 16 (3+2+4+2+2+3), all in `![Fig-CHNN-MM: caption](figures/Fig-CHNN-MM.png)` form.
- Zero U+FFFD (`�`) and zero `ﬀ/ﬁ/ﬂ` ligatures in the .md.

## Deviations from Plan

**1. [Rule 1 - Bug in source metadata] PDF caption typo on Fig-CH02-02**
- **Found during:** Task 1 page-mapping
- **Issue:** The PDF's page-26 diagram caption reads "Fig-CH02-01" but the surrounding prose ("Fig-CH02-02 makes the stack visible…") identifies it as Fig-CH02-02.
- **Fix:** Image named `Fig-CH02-02.png`; converter note embedded in the .md caption.
- **Commit:** 876418b / ecdce23

**2. [Rule 3 - Blocking] Missing-glyph reconstruction policy**
- **Found during:** Tasks 2–3
- **Issue:** Several math symbols are notdef in the PDF's embedded fonts — they are invisible in the rendered PDF, not merely corrupted by pdftotext. Affected: operator composition, ⇄, the §4.3/§5.1/§6.1 contrast-pair arrows, and λ.
- **Fix:** Context-based reconstruction (∘ / ⇄ / → / λ_c), documented in the file's conversion note so Phase R researchers know these are reconstructions. The §4.3 "X → Y" arrows are an interpretive choice matching the chapter's "BI → Agentic" framing; flag for Dave at the phase gate if fidelity review requires the original LaTeX source.
- **Commits:** ecdce23, 8876ec6

**3. Minor fidelity note (not a deviation rule):** pdftotext dehyphenation cannot distinguish line-break hyphens in compounds; a dictionary pass restored ~45 known compounds (agent-driven, role-conditioned, etc.). Residual paragraph-boundary merges at page breaks are possible in long prose sections; captions, headings, tables, and formal notation were verified visually per D-03 targets. The full D-03 section-by-section spot-check is plan 01-03's gate.

## Full-page-render fallbacks (per acceptance criteria)

- `Fig-CH02-01.png` — full-page render of PDF page 21 (table-figure, no embedded raster). All other 49 figures are native embedded rasters.

## Known Stubs

None — no code in this plan; the .md intentionally ends at Ch 6 (Ch 7–8 belong to plans 01-05…01-08 per the phase plan set).

## Threat Flags

None. No remote configured; scratch files stayed in the session scratchpad; only pre-installed poppler tools used (T-01-SC accepted disposition held — zero package installs).

## Commits

- 876418b — docs(01-02): extract 50 whitepaper figures to docs/figures per D-04
- ecdce23 — docs(01-02): convert whitepaper Ch 1-4 to canonical Markdown per D-01/D-02
- 8876ec6 — docs(01-02): convert whitepaper Ch 5-6 to canonical Markdown per D-01

## Self-Check: PASSED

- docs/CCF_Whitepaper_1-2.md exists (Ch 1-6, 16 placeholders, clean glyphs)
- docs/figures/ contains 50 Fig-CHNN-MM.png files
- Commits 876418b, ecdce23, 8876ec6 present in git log; working tree clean
