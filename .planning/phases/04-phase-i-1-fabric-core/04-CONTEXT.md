# Phase 4: Phase I.1 — Fabric Core - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the L1–L6 Data and Context Layer end-to-end in-process against
reference backends, with CI invariant scaffolding running from the first
fabric commit. Deliverables per `.planning/ROADMAP.md` Phase 4: Context
Graph on SQLite + Postgres (D-IMPL-02) with idempotent upsert, lineage
accumulation, single-writer-at-boot; four operator categories with
composition-preservation tests; two-stage projection engine; Context
Product Contract (`extra=forbid`, three validation gates); λ_c/D_c from
Control Plane config only; five-dimension Decision Replay written at
serve time; ArtifactStore Protocol; CDC→G ingress; CINV-01..04 lints
green. Branch `phase-i1`; model mandate Opus ("Opus 5" if available else
"Opus 4.8") high effort per CLAUDE.md §3; ends with `/gsd-review --phase
Phase I.1 --all` → triage → Dave approval → `D-GATE-I.1`.

</domain>

<decisions>
## Implementation Decisions

### Build sequencing
- **D-01:** Vertical slice first — a thin L1→L6 path (minimal ingest →
  assembly → SQLite graph → operator chain → projection → typed Context
  Product with replay record) lands early; subsequent plans widen it.
- **D-02:** The slice's proof point is a **proto-quickstart**: a private
  test-fixture precursor of `examples/00-quickstart`, formalized as the
  real example in Phase 8. It must be **realistic, not hello-world** —
  real multi-type ontology, multi-source events exercising idempotent
  upsert and lineage accumulation, a genuine operator chain, products
  that actually trip the validation gates, full five-dimension replay
  record. Planner bar: "would this slice catch a broken invariant?"
- **D-03 (REVISES CLAUDE.md §9):** Dave changed the examples-domain
  policy: the v0 examples suite becomes a **horizontal mix of domains**,
  with **example 00 (and the I.1 slice fixtures) in a banking scenario**
  — not the single neutral field-service domain §9 currently mandates.
  Phase 4 must amend CLAUDE.md §9 accordingly and log the ruling in
  `docs/DECISIONS.md` (new D-IMPL-NN, Approver: Dave, 2026-07-25).
  Banking fixtures also give realistic policy/regulatory pressure on the
  fabric, serving D-02.
- **D-04:** Widening work is organized **by subsystem**, matching
  DESIGN.md component boundaries: operators+composition tests, projection
  engine, product contract+gates, λ_c/D_c, replay+ArtifactStore, Control
  Plane registry, CDC ingress, Postgres backend, Chroma index.
- **D-05:** Wave 1 = repo/packaging scaffold (`ccf` + `ccf-runtime`
  packages, pyproject, CI skeleton with lints) **plus only the typed
  contracts the slice needs**. Remaining contracts land with their
  subsystem plans — no speculative full contract layer up front.

### CI lint mechanics
- **D-06:** The No-Hardcoding, zero-harness-imports, and `@algorithmic`
  lints are **custom in-repo AST checkers** (a `tools/` or `tests/lints/`
  module, themselves unit-tested), run as CI steps. No ruff/flake8 plugin
  packaging.
- **D-07:** Lints **gate CI from the first fabric commit** — they land in
  the Wave 1 scaffold, blocking, never report-only.
- **D-08:** No-Hardcoding detection = heuristics (prompt-shaped
  multi-sentence strings, numeric-table/dict constants in `/src`,
  factory-bypass construction) **plus a reviewed, versioned allowlist
  file** for legitimate literals. Every exception is an explicit,
  reviewable allowlist entry.
- **D-09:** CI runs on **GitHub Actions** (private repo): lint job + test
  matrix; Postgres provided as a service container.

### Backend & infra logistics
- **D-10:** Local Postgres testing via **testcontainers-python**; CI uses
  the GitHub Actions postgres service container. Same test suite runs in
  both.
- **D-11:** Postgres reference GraphStore lands **after the slice, in a
  later wave within I.1**, implemented against the by-then-stable
  Protocol conformance suite. Slice and early subsystem plans run on
  SQLite.
- **D-12:** ArtifactStore in I.1 = **Protocol + file-backed dev impl
  only**; the MCP-backed reference impl moves to I.3 with the rest of the
  MCP machinery. ⚠ This amends Phase 4 success criterion 4 (which names
  the MCP-backed impl) — planner must record the scope amendment in
  `.planning/ROADMAP.md`/gate materials rather than silently miss it.
- **D-13:** **Chroma is IN for I.1** as the second SimilarityIndex
  reference impl (budget granted under D-IMPL-03's "if budget allows").
  Gets its own subsystem plan against the shared conformance suite.

### Test strategy depth
- **D-14:** Composition-preservation `(A∘B)(G) = A(B(G))` tested with
  **property-based generation (Hypothesis) for every shipped operator
  pair, plus curated banking fixture graphs** for known edge cases (empty
  results, policy-filtered nodes, temporal boundaries). Covers both
  FEASIBILITY.md D-08 test classes.
- **D-15:** Test discipline = **TDD on contracts and invariants**
  (tests-first for validation gates, single-writer, lineage strict
  equality, replay record shape, Protocol conformance); implementation-
  first permitted for plumbing/scaffolding.
- **D-16:** Backend parity via **one shared, parametrized Protocol
  conformance suite** run identically against SQLite/Postgres and
  sqlite-vec/Chroma; backend-specific tests only for substrate quirks.
- **D-17:** Gate bar = the FEAS-03 **per-invariant checklist green** (each
  named invariant maps to a passing named test/lint); line coverage
  reported informationally, **no numeric coverage gate**.

### Claude's Discretion
- Exact heuristic set and thresholds for the No-Hardcoding AST checker
  (bounded by D-08's allowlist mechanism).
- Slice contract subset selection (D-05), plan/wave counts, and internal
  module layout within `/src` per DESIGN.md.
- Banking fixture ontology specifics (entity/relationship types, event
  mix) — bounded by D-02's realism bar; keep values in fixture artifacts,
  never `/src` (No-Hardcoding Rule applies to fixtures' code too).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project governance
- `CLAUDE.md` — canonical (rev 4): §5 primitive quick-reference, §6.4
  No-Hardcoding Rule, §7.4 ArtifactStore constraints, §10 L1–L6 layering
  + single-writer invariant, §11 working principles, §3.1 Phase I review
  criteria. **§9 requires amendment per D-03 (banking example 00,
  horizontal domain mix).**
- `docs/CCF_Whitepaper_1-2.md` — canonical spec; §7.3 graph mechanism,
  §7.4 operators, §7.5 projection, §7.6 product contract/gates, §7.7
  λ_c/D_c, §7.8 Control/Data plane, §7.10 replay. Cite sections in every
  public-class docstring.

### Design & decisions (all Phase 4 work builds against these)
- `docs/DESIGN.md` — component boundaries for the D-04 subsystem plan
  split; Invariant Preservation chapter; Appendix A inventory→design
  matrix.
- `docs/DECISIONS.md` — 49 D-IMPL rulings (esp. D-IMPL-01..09, 26, 34,
  41, 44, 47); D-03 adds a new entry here.
- `docs/SPEC_INVENTORY.md` — 126 entries; INV-CH7-* invariants cited by
  the rulings.
- `docs/FEASIBILITY.md` — per-component verdicts + FEAS-03 per-invariant
  test-strategy table (the D-17 gate checklist) + D-08 two
  composition-test classes.
- `docs/ROADMAP.md` — Milestone I.1 scope and v0.1 surface table
  (Postgres-within-I.1, CI-from-first-commit language).

### Planning
- `.planning/ROADMAP.md` — Phase 4 goal, requirements FABR-01..09 +
  CINV-01..04, success criteria (criterion 4 amended per D-12).
- `.planning/REQUIREMENTS.md` — FABR/CINV requirement definitions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No production code exists yet — `/src`, `/runtime`, `/tests` are empty.
  Phase 4 writes the first fabric code.
- `docs/DESIGN.md` Appendix A/C and `docs/FEASIBILITY.md` appendix matrix
  give the planner a ready component list and risk ratings.
- `ccf/whitepaper/` canonical markdown chapters + `docs/figures/` for
  docstring citations.

### Established Patterns
- Multi-plan wave structure under `.planning/phases/0{1,2,3}-*` — Phase 4
  reuses it (Wave 1 scaffold+slice contracts → slice → subsystem waves →
  Postgres/Chroma → gate wave).
- Phase-branch discipline: work on `phase-i1`, merge to `main` only at
  `D-GATE-I.1` (CLAUDE.md §2.2).
- Review protocol §3.1 with cross-AI reviewers (CODEX_API_KEY /
  CURSOR_API_KEY per CLAUDE.md §3.1 credentials note).

### Integration Points
- New: `/src` (ccf library), `/runtime` (ccf-runtime package skeleton),
  `/tests` (conformance suites, lints), `.github/workflows/` (CI),
  `tools/` or `tests/lints/` (AST checkers + allowlist file).
- Doc edits: CLAUDE.md §9 amendment, `docs/DECISIONS.md` new ruling,
  `.planning/ROADMAP.md` criterion-4 amendment (D-12).

</code_context>

<specifics>
## Specific Ideas

- Dave's bar for the slice: "NOT a 'hello world' — realistic features
  that pressure-test the emerging SDK code."
- First example / slice domain is banking; the eventual suite is a
  horizontal mix of domains (D-03) — a deliberate reversal of the
  CLAUDE.md §9 single-neutral-domain rule, to be amended and logged.

</specifics>

<deferred>
## Deferred Ideas

- MCP-backed ArtifactStore reference impl → Phase 6 (I.3), per D-12.
- None other — discussion stayed within phase scope.

</deferred>

---

*Phase: 4 - Phase I.1 — Fabric Core*
*Context gathered: 2026-07-25*
