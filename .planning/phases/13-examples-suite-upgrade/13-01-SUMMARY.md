---
phase: 13-examples-suite-upgrade
plan: "01"
subsystem: docs
tags: [examples, readme-template, gloss, no-hardcoding]
requires: []
provides:
  - "Canonical seven-heading README skeleton (D-02) for examples 00-07"
  - "20-term CCF gloss table with verified whitepaper/CLAUDE.md cites (D-04)"
  - "[ADAPT]/[MECHANISM] artifact header-marker wording (D-11)"
  - "Per-example regeneration-warning phrasing, 00-07 vs 08 (D-10)"
affects: [13-02, 13-03, 13-04, 13-05]
tech-stack:
  added: []
  patterns: [verbatim-copy consistency contract for parallel wave execution]
key-files:
  created:
    - .planning/phases/13-examples-suite-upgrade/13-README-TEMPLATE.md
  modified: []
decisions:
  - "Gloss cites use verified whitepaper §N.N headings only — the whitepaper has no numbered subsections, so §7.7.4/§7.10.1-style cites from the plan action were normalized to §7.7 / §7.10 with named subsections"
metrics:
  duration: ~8 min
  tasks: 1
  files: 1
  completed: 2026-08-02
---

# Phase 13 Plan 01: Shared README Template Summary

One canonical planning-internal reference fixing the seven D-02 README
headings, a 20-term CCF gloss table with whitepaper-verified cites, the
exact [ADAPT]/[MECHANISM] marker wording, and per-example D-10
regeneration phrasing — so the eight parallel Wave-2 README rewrites
cannot drift.

## What was built

`.planning/phases/13-examples-suite-upgrade/13-README-TEMPLATE.md` (201
lines), four parts:

1. **Template skeleton** — title form `# examples/NN-name — <hook>` plus
   exactly seven `##` headings, verbatim, in D-02 order, with the
   explicit rule that `grep -c '^## '` must equal 7 per README (extra
   content goes under existing sections, never a new H2). Per-section
   guidance covers D-03 (path refs, excerpts of 8 lines or fewer, no
   include machinery), D-12 (Artifact-by-artifact table columns
   `Artifact | What it declares | Yours to edit vs mechanism`), D-11
   (What to change first = exact file + keys), and the examples/05
   `Invariant | What would fail here` table pattern.
2. **Gloss table** — 20 terms (Context Product, Context Graph, L1–L6,
   Operators, Π, λ_c, D_c, Decision Replay record, Control/Data Plane,
   MCP, A2A, archetype vs agent, specialization/skilling,
   No-Hardcoding, ApprovalGate, ExceptionEscalation, OverrideBoundary,
   ReviewQueue, ArtifactStore), each with a one-line gloss and a cite;
   CLAUDE.md-only concepts marked "SDK extension".
3. **Marker convention** — the two fixed comment lines
   `# [ADAPT] domain vocabulary — safe to change for your domain` and
   `# [MECHANISM] structural keys interpreted by the factory — do not rename`,
   YAML-comments-only, identical wording across all eight examples.
4. **Regeneration phrasing** — canonical 00–07 paragraph
   (run `make example-NN`, review assertions, deliberately edit the
   `expected:` block, land in the same commit) with a per-example table
   of which file(s) hold the `expected` blocks (05: hitl.yaml
   `expected_gate`; 02/06: also skills.yaml; 06: also hitl.yaml), a
   separate 08-only paragraph (checksum re-pin + expected_output.txt),
   and the explicit statement that no `make regen-*` targets exist or
   will be added.

## Verification

- `grep -c '^## '` = 11 (≥4 required) — PASS
- `What would fail`, `[ADAPT]`, `[MECHANISM]` present — PASS
- No `--8<--` string anywhere in the file — PASS (guidance reworded to
  "snippet-include directives" to satisfy the literal-string criterion)
- `make regen` appears only inside does-not-exist statements — PASS
- File ≥60 lines (201) — PASS
- Gloss table ≥16 terms (20) — PASS

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan-listed whitepaper subsection numbers do not exist**
- **Found during:** Task 1 (cite verification, as the plan itself mandates)
- **Issue:** The plan action listed cites like §7.7.4 and §7.10.1, but
  `docs/CCF_Whitepaper_1-2.md` numbers headings only at the §N.N level
  (verified by grep — §7.7 and §7.10 exist; their subsections are
  unnumbered named headings).
- **Fix:** Gloss cites use the verified §7.7 / §7.10 with the named
  subsection in parentheses; the template documents this normalization
  rule for downstream READMEs.
- **Files modified:** 13-README-TEMPLATE.md
- **Commit:** 58d834e

## Known Stubs

None — planning-internal Markdown only.

## Threat Flags

None — no new surface (matches the plan's threat model: planning-internal
Markdown, no runtime input, no dependency, no endpoint).

## Self-Check: PASSED
- FOUND: .planning/phases/13-examples-suite-upgrade/13-README-TEMPLATE.md
- FOUND: commit 58d834e
