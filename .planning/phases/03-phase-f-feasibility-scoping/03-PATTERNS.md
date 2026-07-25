# Phase 3: Phase F — Feasibility & Scoping - Pattern Map

**Mapped:** 2026-07-25
**Files analyzed:** 4 (2 new docs, 2 in-place edits)
**Analogs found:** 4 / 4 (docs-only phase; all analogs are existing repo documents)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/FEASIBILITY.md` (new) | design/analysis doc | derivation from corpus | `docs/DESIGN.md` (component-entry style, §9 invariant table, Appendix A matrix, Appendix B advisory table, Appendix C index) | exact |
| `docs/ROADMAP.md` (new) | milestone doc | derivation from `.planning/ROADMAP.md` + DESIGN.md | `docs/DESIGN.md` preamble/table conventions + `.planning/ROADMAP.md` (I.1–I.5 sequencing truth) | role-match |
| `docs/DESIGN.md` (in-place wording fixes, D-11) | design doc edit | targeted edits (2) | itself — §9 expanded argument 1 ("Honest residual claim") and Appendix B F-1 (numerics) | exact |
| `docs/DECISIONS.md` (conditional D-02 additions + `D-GATE-F`) | decision log append | append-only | itself — D-IMPL-30..51 entry format; D-GATE-R/D-GATE-D gate-entry format | exact |

## Pattern Assignments

### `docs/FEASIBILITY.md` (new — FEAS-01/03, D-01..D-03, D-07..D-11)

**Analog:** `docs/DESIGN.md`

**Doc preamble pattern** (DESIGN.md style, cf. DECISIONS.md lines 1–3):
```markdown
# FEASIBILITY — CCF SDK v0

**Canonical authority:** `CLAUDE.md` (revision 4). ... Whitepaper citations
reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).
```

**Component-entry pattern** — the per-component verdict entries should mirror DESIGN.md's `#### Component:` bullet-block shape (lines 279–302). Concrete analog, `docs/DESIGN.md` lines 292–296:
```markdown
#### Component: SLO envelope, materialization, and cost discipline

- **Responsibility:** ... (INV-CH7-50). ...
- **Invariants enforced:** ... Materialization policy is Control Plane
  configuration under the D-IMPL-38 discipline; ...
- **D-IMPL rulings embodied:** D-IMPL-27, D-IMPL-36, D-IMPL-38.
```
Adapt for FEASIBILITY: per D-03 each entry = **Verdict** (strong fit / needs design choice / out of scope for v0) + 2–4 sentence rationale citing the DESIGN.md section (`§2B.3` style) and `D-IMPL-NN` rulings + **Risk:** low/med/high. No effort estimates (D-03). Component names come from DESIGN.md's `#### Component:` headings and named Protocols (48 `###` subsections; ~28 Protocols — see RESEARCH Key Finding 2 for the enumeration spine).

**Invariant-table pattern** for the D-07 test-strategy chapter — copy the column-table shape of `docs/DESIGN.md` §9 lines 751–759:
```markdown
| Invariant | Structural argument (design construct) | Enforcement point | Diagram/section ref |
|-----------|----------------------------------------|-------------------|---------------------|
| Single-writer enforcement (only L2/Assembly writes L3) | `GraphReader`/`GraphWriter` Protocol split (D-IMPL-34): ... | DI composition root at boot; strict mypy + writer-module import lint in CI; boot-time token mint | §2A.5.3; `docs/diagrams/seq-single-writer-write-path.mmd` |
```
D-07 columns: invariant | verification mechanism (lint / test harness / boot check) | CI job | pass criterion | DESIGN.md §9 ref. **Content is transposed, not re-derived, from DESIGN.md §9 lines 777–788** (CINV-01..04, composition-preservation harness, single-writer boot check, gate unit tests + MAX_TTL registration test). Add two new rows only: D-08 test class 2 (staged-execution equivalence: two-stage projection plan output == direct composition) and D-09 hash-verified re-hydration (ReHydrationRecipe replay reproduces pinned content hashes per D-IMPL-26/44).

**Canonical gate naming** (Pitfall 4 — Phase D's B2 finding). Always verbatim, per `docs/DESIGN.md` line 755:
```
empty-operator guard → lineage strict equality → TTL bounds
```

**Appendix matrix pattern** (D-01, 126 entries) — copy `docs/DESIGN.md` Appendix A, lines 792–798:
```markdown
## Appendix A — Traceability Matrix (126/126, D-06)

Every `INV-CHx-NN` inventory entry (`docs/SPEC_INVENTORY.md`) mapped to the design
section that realizes it, or explicitly deferred with the ruling that defers it.
Key set is exactly the inventory's 126-entry set (mechanically checkable:
unique-key diff against the inventory is empty).

| INV key | DESIGN.md section | Status |
|---------|-------------------|--------|
| INV-CH5-01 | §2A.0 | mapped |
```
FEASIBILITY's matrix adds an owning-component → verdict join: columns `INV key | DESIGN.md section | Owning component | Verdict`. Keep the "mechanically checkable: unique-key diff ... is empty" sentence — `/gsd-review` checks coverage this way. Note `see-also` composite refs exist (e.g., `§2B.1 (see-also §2A.1)`, line 820) and Appendix A contains "deferred" statuses (grep before building — Assumption A2).

**Advisory Disposition appendix pattern** (D-11) — copy `docs/DESIGN.md` Appendix B, lines 929–935:
```markdown
## Appendix B — Review Appendix (carried-forward findings)

Advisory findings carried forward from the Phase R Review Appendix (...), with
Phase D dispositions. Zero blocking findings were carried in.

| ID | Finding (Phase R, advisory) | Phase D disposition |
|----|------------------------------|---------------------|
| F-1 | Non-normativity of numeric examples ... | Honored throughout: ... (D-IMPL-38/39/40); ... |
```
The 7 items are enumerated at `.planning/phases/02-phase-d-design/02-REVIEWS.md` line 236: three-adapter sizing input, composition-preservation test definition, hash-verified re-hydration strategy, residual-risk wording, numerics disclaimer, deferral migration notes, dev IdentityProvider. Items 4–5 dispositions must cite the actual DESIGN.md fix commit hashes (Pitfall 6).

**Gate-list check table** (FEAS-03) — 12 rows in DECISIONS.md's status-note style, `docs/DECISIONS.md` line 9 pattern: `**D-IMPL-01 — Language target.** RESOLVED — Python 3.12+ ... 2026-07-25. Approver: Dave.` Columns: ID | ruling one-liner | RESOLVED | DECISIONS.md ref. **D-IMPL-10 wording must be copied verbatim from Appendix C** (Pitfall 1), `docs/DESIGN.md` line 945:
```
D-IMPL-10 (repo shape) is resolved for v0 as monorepo — the post-v0
adapter-split remainder is non-gating and tracked outside Phase D
```
(Note D-IMPL-10 is NOT one of the 12 gate IDs: the list is 01–05, 11, 14, 17, 20, 24, 26, 28. Census discipline: 49 marathon rulings / 50 cited / 51 entries, per DECISIONS.md line 40.)

---

### `docs/ROADMAP.md` (new — FEAS-02, D-04..D-06)

**Analog:** `docs/DESIGN.md` table/preamble conventions + `.planning/ROADMAP.md` sequencing (phases 4–8 = I.1–I.5: Fabric Core; Agent Specialization Framework; Cross-Process & Harness Adapters; Orchestration/HITL/Experience; Examples Suite & Full CI Verification).

**Preamble must state the two-roadmap relationship explicitly** (Pitfall 2): `.planning/ROADMAP.md` is the sequencing source of truth; `docs/ROADMAP.md` is the deliverable view, 1:1 aligned, each milestone gated by `D-GATE-I.n`.

**Milestone + v0.1 annotation:** the v0.1 minimum viable surface (D-04) is the subset of I.1–I.2 running examples 00–01: L1–L6 fabric core, Control Plane registry, Agent & Task Factory, `AnalyticsInsightsAgent` archetype only, SQLite graph store + sqlite-vec, file-backed ArtifactStore. Include the dev/mock IdentityProvider assessment as a v0.1-surface line item (D-11 advisory 7).

**Deferral register pattern** (D-06) — table shape mirroring Appendix B: columns `Item | Source (CLAUDE.md § / D-IMPL-NN) | Reason deferred | Earliest re-entry milestone`. Mandatory five rows: Homecams rebuild (CLAUDE.md §9), adapter package split (D-IMPL-10 residual), agent-swarm intent decomposition (D-IMPL-49, DESIGN.md §4 named post-v0 extension), Supervision Quality (D-IMPL-48, DESIGN.md §5 deferred disposition), Conversational Reporting Layer (whitepaper §8.10 / CLAUDE.md §13). Candidate extras: Chroma second SimilarityIndex impl (D-IMPL-03 "if budget allows"), Appendix A "deferred"-status entries.

---

### `docs/DESIGN.md` (in-place edits — D-11 advisory items 4 and 5)

**Analog:** itself. Two targeted edits, each its own commit (the Advisory Disposition appendix cites the hashes):

1. **Single-writer residual-risk framing** — strengthen/propagate the existing sentence at `docs/DESIGN.md` line 763 (§9 expanded argument 1):
```
**Honest residual claim (per the D-IMPL-41 ruling):** Python cannot make
determined-insider evasion impossible; the claim strength is *no unforced path
exists, and every forced path fails CI or fails at boot*.
```
2. **Numerics disclaimer** — extend the F-1 posture (Appendix B line 935: "every numeric value ... is illustrative, never an SDK default", designed as Control Plane configuration per D-IMPL-38/39/40) into an explicit disclaimer where §9/§2B cite illustrative numbers.

Do not restructure headings, renumber sections, or touch Appendix A/C keys.

---

### `docs/DECISIONS.md` (conditional appends — D-02 new gaps; mandatory `D-GATE-F`)

**Analog:** itself. "Extend it, never restructure it" (CONTEXT.md).

**New D-IMPL entry pattern** (if a D-02 gap fires) — next sequential number is **D-IMPL-52**. Copy the entry shape of `docs/DECISIONS.md` line 47 (D-IMPL-30): bold `**D-IMPL-NN — Title.**` + status (`Open — awaiting Dave` initially) + date + `Originates:` section ref + (for ambiguous passages) quoted passage with 2–3 readings and consequences per CLAUDE.md §15. Appended after D-IMPL-51, before the `---` / Pending gate actions.

**Gate entry pattern** — copy `docs/DECISIONS.md` line 101 (D-GATE-D) under `## Gate Log (D-GATE)`:
```markdown
**D-GATE-F** — Phase F (Feasibility & Scoping) approved. Date: YYYY-MM-DD.
Approver: Dave. Scope: ... Triage disposition: N blocking findings fixed
in-phase; M advisory recorded/carried. Deliverables: docs/FEASIBILITY.md (...),
docs/ROADMAP.md (...), DESIGN.md wording-fix commits (<hashes>), review +
triage evidence (03-REVIEWS.md ...). Phase I may begin.
```

## Shared Patterns

### Citation conventions (apply to both new docs)
- DESIGN.md sections cited as `§2B.3`, `§2A.5.3`; inventory keys as `INV-CHx-NN`; rulings as `D-IMPL-NN` with "per the **D-IMPL-NN ruling**" inline-bold style; diagrams as `docs/diagrams/<name>.mmd`.
- Whitepaper cited as `docs/CCF_Whitepaper_1-2.md` §sections, never the PDF (locked D-01, DECISIONS.md line 3).
- Bold inline emphasis for load-bearing phrases; em-dash-heavy declarative prose; `---` horizontal rules between major chapters/appendices.

### Mechanical checkability
Every coverage claim states its check, DESIGN.md Appendix A style: "mechanically checkable: unique-key diff against the inventory is empty." FEASIBILITY's matrix, the 12-row gate table, the ≥5-row deferral register, and the 7-row advisory appendix should each be grep-verifiable (see RESEARCH Validation Architecture).

### Do-not-drift wordings (copy verbatim, never paraphrase)
- Three gates: "empty-operator guard → lineage strict equality → TTL bounds" (DESIGN.md line 755).
- D-IMPL-10 status: Appendix C wording (DESIGN.md line 945).
- Census: "49 marathon rulings, 50 cited rulings, 51 total entries — consistent by construction" (DECISIONS.md line 40).
- CINV IDs: CINV-01..04 exactly as DESIGN.md lines 781–784 (IDs match `.planning/REQUIREMENTS.md`).

## No Analog Found

None. Every deliverable has a direct in-repo analog; no RESEARCH.md fallback patterns needed.

## Metadata

**Analog search scope:** `docs/` (DESIGN.md, DECISIONS.md, SPEC_INVENTORY.md), `.planning/phases/02-phase-d-design/`, `.planning/ROADMAP.md`
**Files scanned:** 4 read in targeted ranges (DESIGN.md 1011 lines via heading map + 3 non-overlapping section reads; DECISIONS.md full; 02-REVIEWS.md triage section)
**Pattern extraction date:** 2026-07-25
