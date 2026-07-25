# Phase 1: Phase R — Research - Pattern Map

**Mapped:** 2026-07-24
**Files analyzed:** 8 new/modified files
**Analogs found:** 4 / 8 (docs-only greenfield phase; several deliverables have no in-repo analog by design)

## File Classification

This is a documentation-extraction phase. Roles are document types, not code roles; data flow is "transform" (PDF/whitepaper/Homecams source → structured Markdown).

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/CCF_Whitepaper_1-2.md` | canonical spec document (converted) | transform (PDF → md) | none | no analog (fidelity governed by D-01..D-04, not by any repo pattern) |
| `docs/figures/` (≈50 images) | figure assets | file-I/O (pdfimages extraction) | none | no analog |
| `docs/SPEC_INVENTORY.md` | structured inventory / catalog | transform (whitepaper → keyed entries) | `.planning/REQUIREMENTS.md` | role-match |
| `docs/SPEC_INVENTORY.md` — homecams-patterns appendix | catalog appendix with markers | transform (Homecams source → pattern list) | `.planning/REQUIREMENTS.md` traceability table | partial |
| `docs/DECISIONS.md` | decision log | append-only record | `CLAUDE.md` §12 (D-IMPL scaffolding) | exact (the format is prescribed there) |
| `docs/DESIGN.md` (placeholder) | placeholder doc | n/a | `.planning/ROADMAP.md` header style | partial |
| `.gitignore` | config | n/a | none in repo | no analog (standard content; §2.2 + RESEARCH.md name the entries) |
| Directory skeleton (`/references`, `/src`, `/runtime`, `/tests`, `/examples`, `docs/diagrams/`) | scaffolding | n/a | none | no analog (CLAUDE.md §14 item 4 is the spec) |

## Pattern Assignments

### `docs/SPEC_INVENTORY.md` (inventory, transform)

**Analog:** `/home/parkave/ccf_code/.planning/REQUIREMENTS.md`

**Keyed-entry ID pattern** (lines 11–22) — stable prefixed IDs, bold key, checkbox, section citation in parentheses:

```markdown
- [ ] **RSCH-01**: `docs/SPEC_INVENTORY.md` catalogs every commitment in
      whitepaper §5–§8: section, paraphrased commitment, type signature where
      given, invariants, dependencies, figure refs, open-question field (§16)
```

Apply the same scheme to inventory keys — RESEARCH.md Pattern 1 recommends `INV-<area>-<NN>` (e.g., `INV-L3-01`, `INV-OPS-03`), fixed in the first extraction task and chapter-scoped to avoid collisions between parallel tasks. Every entry must carry the seven §16 fields (whitepaper `.md` section, paraphrase, type signature, invariants, dependencies, figure refs, open-question field) — checkboxes are optional; the field structure is mandatory ("a summary instead of an inventory" is a redo per CLAUDE.md §16).

**Document header pattern** (lines 1–5) — state the canonical authority and precedence rule up front:

```markdown
# REQUIREMENTS — CCF SDK v0

Extracted from `CLAUDE.md` (canonical, revision 4) §3 phase deliverables and
§13 v0 scope. CLAUDE.md wins on any disagreement.
```

For SPEC_INVENTORY.md: authority is `docs/CCF_Whitepaper_1-2.md`; all citations reference `.md` sections, never the PDF (locked D-01).

**Completeness/traceability table pattern** (lines 151–160) — mechanical enumeration, one row per item, used to prove coverage:

```markdown
## Traceability

All 46 v1 requirements mapped (46/46).

| Requirement | Phase | Status |
|-------------|-------|--------|
| RSCH-01 | Phase 1 | Pending |
```

Reuse for the §16 dedicated sections: 36-subsection coverage checklist, 50-figure table (`Fig-CHNN-MM` | caption | mechanism committed), 41-entry D-NN governance table (report gap numbers explicitly as "not found"), named-invariants list, SDK-extensions-with-hooks table, pillar-by-pillar mapping.

---

### homecams-patterns appendix (inside `docs/SPEC_INVENTORY.md`)

**Analog:** `.planning/REQUIREMENTS.md` traceability table (partial) — same table-with-status-column discipline.

Each row needs an explicit marker column with exactly two values, per CLAUDE.md §16 and RSCH-03:

```markdown
| Pattern | Source (Homecams path) | Marker | Notes |
|---------|------------------------|--------|-------|
| MongoDB artifact persistence | packages/si-pool-safety/services/mongo_data_service.py | candidate pattern | ArtifactStore triangulation data point (§7.4) |
| Property-intelligence half-life values | ... | domain-specific — do not inherit | ... |
```

Do not commit the Mongo connection string or live data records (RESEARCH.md Security Domain) — collection names and shapes only.

---

### `docs/DECISIONS.md` (decision log, append-only)

**Analog:** `/home/parkave/ccf_code/CLAUDE.md` §12 — the format is prescribed there, not inferred:

```markdown
- **D-IMPL-10 — Repo shape.** Provisionally resolved as **monorepo**
  at `github.com/drcastillo/ccf_code` ... Remaining open under this
  entry: whether adapters split into separate packages or repos
  post-v0.
```

Entry contract per CLAUDE.md §12: each `D-IMPL-NN` carries a short bold title, its resolution (or "open — awaiting Dave"), its date, and a reference to the whitepaper section or CLAUDE.md section where the question originates. Ambiguous-whitepaper entries additionally quote the ambiguous passage and propose 2–3 readings with consequences (§15). New numbers start at **D-IMPL-30** and are assigned only by the synthesis task (RESEARCH.md Pattern 2 — extraction tasks emit unnumbered questions to avoid collisions). The file also hosts `D-GATE-R` at phase end (approval date + approver).

---

### `docs/DESIGN.md` placeholder + `docs/SPEC_INVENTORY.md` initial header

**Analog:** `.planning/ROADMAP.md` header style (lines 1–9) — title, canonical-authority pointer, one-line status:

```markdown
# ROADMAP — CCF SDK v0

**Canonical authority:** `/home/parkave/ccf_code/CLAUDE.md` (revision 4).
```

Placeholders per CLAUDE.md §14 item 5 need only a title, the authority pointer, and "Populated in Phase D/R" — nothing more.

---

### `docs/CCF_Whitepaper_1-2.md` + `docs/figures/`

**No analog exists.** Governing patterns come from CONTEXT.md D-01..D-04 and RESEARCH.md instead:

- Figure placeholder convention at each figure's location in the `.md`:
  `![Fig-CH07-04: Context Graph — logical six-tuple and physical collection pattern](figures/Fig-CH07-04.png)`
- Conversion is hybrid: pdftotext skeleton + Read-tool ≤20-page windows; math/notation (`G(E,R,T,P,Π,L)`, `λ_c`, `D_c`, `⇄`) reconstructed visually, never from pdftotext (glyph corruption pitfall).
- D-03 spot-check gate targets §5.2, §7.3–7.6, §7.7 specifically.

### `.gitignore` and directory skeleton

**No analog.** Content specified directly: `.gitignore` excludes `._*`, `*.orig`, build artifacts, environments, credentials (CLAUDE.md §2.2 + RESEARCH.md Pitfall 5). Skeleton is the exact §14 item 4 list.

## Shared Patterns

### Canonical-authority header
**Source:** `.planning/ROADMAP.md` lines 1–9 / `.planning/REQUIREMENTS.md` lines 1–5
**Apply to:** every new docs/ file
Open with the canonical source and the precedence rule ("CLAUDE.md wins" / "the whitepaper `.md` is authoritative; citations reference its sections").

### Section-citation discipline
**Source:** CLAUDE.md throughout (e.g., "(§16)", "(§2.1, §16)")
**Apply to:** every inventory entry, appendix row, and D-IMPL entry
Every claim cites a section — whitepaper `.md` sections for inventory content, CLAUDE.md sections for SDK-extension hooks. Never cite the PDF (locked D-01).

### Completeness-by-enumeration tables
**Source:** `.planning/REQUIREMENTS.md` traceability table
**Apply to:** subsection coverage (36), figures (50), D-NN (41), invariants, pillar mapping
Coverage is proven by grep-diff against the verified lists in RESEARCH.md, not asserted.

### Commit-at-deliverable-boundary messages
**Source:** repo git log (e.g., `docs(01): capture phase context`, `docs: create roadmap (8 phases)`)
**Apply to:** all Phase R commits
Conventional-commit style `docs:` prefix; message names the CLAUDE.md section or D-IMPL served (§2.2).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `docs/CCF_Whitepaper_1-2.md` | converted spec | PDF → md transform | First document of its kind; fidelity governed by D-01..D-04 gates, not repo precedent |
| `docs/figures/*` | figure assets | pdfimages extraction | No prior assets in repo |
| `.gitignore` | config | n/a | None exists; standard content named in RESEARCH.md |
| directory skeleton | scaffolding | n/a | Specified verbatim in CLAUDE.md §14 item 4 |

Planner should use RESEARCH.md ("Standard Stack", "Architecture Patterns", "Common Pitfalls") for these — it already contains the concrete tooling commands and conventions.

## Metadata

**Analog search scope:** `/home/parkave/ccf_code` (docs/, .planning/, CLAUDE.md, git log). `/src`, `/runtime`, `/tests`, `/examples` do not exist yet — no code analogs possible or expected for a Phase R docs-only phase. `/home/parkave/homecams_v2` was deliberately NOT mined for document patterns (§2.1: triangulation only, and its review IS the phase work).
**Files scanned:** 5 read in full (CONTEXT.md, RESEARCH.md, REQUIREMENTS.md, ROADMAP.md partial, CLAUDE.md via project context)
**Pattern extraction date:** 2026-07-24
