---
phase: 02-phase-d-design
reviewed: 2026-07-25T19:05:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - docs/DESIGN.md
  - docs/DECISIONS.md
  - docs/diagrams/pillar-agent-types.mmd
  - docs/diagrams/pillar-data-context.mmd
  - docs/diagrams/pillar-experience.mmd
  - docs/diagrams/pillar-hitl.mmd
  - docs/diagrams/pillar-orchestration.mmd
  - docs/diagrams/seam-artifact-store.mmd
  - docs/diagrams/seam-harness-adapter.mmd
  - docs/diagrams/seq-a2a-admission.mmd
  - docs/diagrams/seq-hitl-suspend-resume.mmd
  - docs/diagrams/seq-replay-resolution.mmd
  - docs/diagrams/seq-single-writer-write-path.mmd
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues
---

# Phase 2: Code Review Report (Mechanical/Consistency Pass)

**Reviewed:** 2026-07-25T19:05:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found (warnings only — no Critical findings)

## Summary

This is the mechanical/consistency layer on the FINAL post-fix state (after B1–B5 fix commits eeb4f4d/796febd), deliberately scoped to not duplicate the four cross-AI content reviews in 02-REVIEWS.md. Checks performed: traceability-matrix key diff against the inventory, D-IMPL citation cross-referencing, figure-citation resolution, intra-document section-reference validation, Mermaid source inspection for all 11 diagrams, markdown table column integrity, and verification that each of the five blocking fixes (B1–B5) actually landed.

**Verified clean (mechanical evidence):**

- **Traceability matrix (Appendix A):** exactly 126 `| INV-` rows, zero duplicate keys, and a unique-key diff against `docs/SPEC_INVENTORY.md` entry headers is empty in both directions. The matrix's own "mechanically checkable" claim (DESIGN.md:794) holds.
- **D-IMPL cross-reference:** the set of D-IMPL IDs cited in DESIGN.md (01–51) is identical to the set defined in DECISIONS.md — no dangling and no orphaned decisions.
- **Figure citations:** every `Fig-CHnn-mm` cited in DESIGN.md resolves against the whitepaper/inventory; none dangle.
- **Diagram references:** all 11 `docs/diagrams/*.mmd` filenames cited in DESIGN.md exist on disk; all 11 files on disk are cited.
- **Table integrity:** pipe counts across all markdown tables cluster cleanly by table shape (4/5/6/7 columns); no ragged rows in the 126-row matrix, the 52-row Appendix C index, the invariant table, or the layer-handoff table.
- **B1–B5 fix verification:** B1 census note present (DECISIONS.md:40) and §1 wording softened (DESIGN.md:18–20); B2 zero residue of "Schema Validator / Policy Gate / Lineage Completeness Checker" naming — canonical three-gate names used at DESIGN.md:755/767; B3 the six L4–L6 entries (INV-CH7-05/06/07/11/12/13) retargeted to §2B primary with §2A.1 see-also (DESIGN.md:820–828); B4 zero "Both pillars" residue; B5 `pillar-orchestration.mmd` edge relabeled `trace write-through at suspend/terminal (not execution state — D-IMPL-18/27)` and the duplicate §8.6/§8.6a numbering is gone.
- No TODO/FIXME/TBD markers; D-GATE-D's "1011 lines" claim matches `wc -l docs/DESIGN.md`.

Residual findings below are wording/formatting consistency items; none is a design-substance or gate-integrity defect.

## Warnings

### WR-01: Appendix C intro contradicts the B1-reconciled D-IMPL-10 status wording

**File:** `docs/DESIGN.md:945`
**Issue:** Appendix C states "D-IMPL-10 (repo shape) **remains provisionally resolved** and is cited only for orientation." This is pre-B1 phrasing. The B1 fix established the canonical wording everywhere else: DESIGN.md:18 ("resolved for v0 as monorepo ... non-gating deferred scope"), DESIGN.md:20 ("provisional monorepo *orientation* ... not a design basis"), and DECISIONS.md:18 (the label "is a CLAUDE.md-governed orientation, not a Phase D `PROVISIONAL` status token"). A reader auditing Appendix C alone re-encounters exactly the "provisionally resolved" ambiguity B1 was meant to eliminate (Codex/Ollama HIGH in 02-REVIEWS.md).
**Fix:** Align line 945 with the census language, e.g.: "...D-IMPL-10 (repo shape) is resolved for v0 as monorepo per CLAUDE.md §2.2 (post-v0 adapter-split remainder non-gating) and is cited only for orientation."

### WR-02: Overloaded §n.n notation — whitepaper vs DESIGN-internal sections are indistinguishable

**File:** `docs/DESIGN.md:16` (convention) vs e.g. `docs/DESIGN.md:743`, `docs/DESIGN.md:599`
**Issue:** The §1 citation convention declares "whitepaper sections as `§n.n`", but the document also uses the same notation for its own sections. Line 743 ("Phase I.3 ... implements against §8.1–§8.2 and §8.4 ... §6 and §8.3") means DESIGN-internal §8.x/§6, while lines 490/599/637 ("§8.11", "§8.12", "§8.10", "§8.13") mean whitepaper §8.x, and lines 367/375/615 ("§6.5", "§6.6", "§6.5.1") mean whitepaper Chapter 6 — all in a document that also has its own §6.1–§6.4 and §8.1–§8.9. Both target sets exist, so a mechanical cross-reference audit cannot disambiguate, and Phase F/I implementers reading hand-off statements like line 743 must infer the referent. This is the same class of auditability weakness Cursor flagged for the matrix, but in the prose reference system.
**Fix:** Adopt a distinguishing form for internal references (e.g., "DESIGN §8.3" or "§8.3 of this document") in the §1 convention block and normalize the internal references — the Phase I hand-off (§8.9) and the Appendix C "Cited in sections" column are the highest-value spots.

## Info

### IN-01: Appendix C structural placement and formatting defects

**File:** `docs/DESIGN.md:1000-1001`
**Issue:** The census line (`**Census:** 50 distinct rulings...`) abuts the `### Replay contributions by pillar` heading with no blank line, and that subsection — a CLAUDE.md §4 cross-check table belonging to the design body — is nested inside Appendix C (the D-IMPL Ruling Index), after the appendix's closing census. Also a stray double blank line at 741–742 after the §8.9 heading.
**Fix:** Insert a blank line and `---` separator before the heading; consider relocating "Replay contributions by pillar" to §9 or its own appendix.

### IN-02: Appendix C "Every D-IMPL-NN ruling" claim excludes cited D-IMPL-51

**File:** `docs/DESIGN.md:945-999`
**Issue:** The intro claims the index covers "Every `D-IMPL-NN` ruling embodied in this design," and the table lists exactly D-IMPL-01..50 — but D-IMPL-51 is cited in the design body (§1, line 18). The DECISIONS.md:40 census note explains the exclusion (Phase R metadata, not a design decision), so the accounting is defensible, but Appendix C itself does not state it.
**Fix:** Add one line: "D-IMPL-51 (Phase R triangulation metadata) is referenced in §1 for census accounting only and is not an embodied ruling — see the Decision Census note in `docs/DECISIONS.md`."

### IN-03: Inconsistent participant-alias quoting across sequence diagrams

**File:** `docs/diagrams/seq-single-writer-write-path.mmd:2-8`
**Issue:** This diagram quotes participant aliases (`participant SRC as "Source (CDC / MCP ingress)"`) while the other three sequence diagrams use unquoted aliases. Quoted actor aliases are only supported in newer Mermaid releases; older renderers display the quote characters literally. Not a syntax error, but a rendering-consistency risk across toolchains.
**Fix:** Drop the quotes (parentheses and slashes are legal in unquoted aliases) to match the other three sequence diagrams.

### IN-04: Mermaid compile verification not possible in this environment

**File:** `docs/diagrams/*.mmd`
**Issue:** `mmdc` is installed but its puppeteer chrome-headless-shell binary is corrupted/wrong-architecture (`linux_arm` binary failing with exec errors), so all 11 diagrams failed to compile for environmental reasons only. Validation was performed by manual syntax inspection instead: all 11 diagrams use well-formed `flowchart`/`sequenceDiagram` grammar (subgraphs, edge-label forms `-->|"..."|`, `-. text .->`, `== text ==>`, `alt/else/end`, `Note over` all correctly formed); no defects found.
**Fix:** Reinstall the puppeteer browser (`npx puppeteer browsers install chrome-headless-shell`) or add a CI render step so diagram compilation is machine-verified before D-GATE artifacts ship.

---

_Reviewed: 2026-07-25T19:05:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
