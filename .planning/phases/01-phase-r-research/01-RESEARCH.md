# Phase 1: Phase R — Research - Research

**Researched:** 2026-07-24
**Domain:** Specification extraction / documentation inventory (PDF → Markdown conversion, whitepaper commitment cataloging, reference-implementation pattern triangulation)
**Confidence:** HIGH (all load-bearing facts verified locally against the actual PDF, repo, and Homecams tree this session)

## Summary

Phase R is a documentation-extraction phase, not a code phase. The work is: (1) convert the 232-page whitepaper PDF to the canonical `docs/CCF_Whitepaper_1-2.md` with figures extracted, (2) extract every commitment in whitepaper §5–§8 into a component-keyed `docs/SPEC_INVENTORY.md` satisfying all CLAUDE.md §16 elements, (3) produce the `homecams-patterns` appendix from a read-only review of `/home/parkave/homecams_v2`, and (4) log every open question as `D-IMPL-NN` in `docs/DECISIONS.md`, then run the §3.1 review protocol.

I verified the actual shape of the source material. The PDF is real, unencrypted, LaTeX-via-pandoc produced, 232 letter pages, ~14.3 MB, with a full table of contents. Extraction targets: whitepaper Ch 5 (7 subsections), Ch 6 (6 subsections), Ch 7 (10 subsections — the mechanism core, pages 86–180, roughly 94 pages, by far the largest chapter), Ch 8 (13 subsections). There are exactly **50 load-bearing figures** (`Fig-CH01-01` through `Fig-CH08-06`; 28 in Ch 7 alone) and **41 unique inline governance decisions** (`D-NN`, numbered up to D-56, non-contiguous), plus a Ch 9 summary. All PDF tooling needed (pdftotext, pdfimages, pdfinfo, pandoc) is already installed. Homecams is accessible read-only with a 9-package `packages/si-*` monorepo, an 829-line CLAUDE.md, and a live MongoDB at `mongodb://192.168.4.76:27017/rtdetect` (port confirmed open, but no mongo client/pymongo installed locally).

**Primary recommendation:** Plan Phase R as (a) a small setup wave (repo prerequisites per CLAUDE.md §14, PDF→md conversion + figure extraction + spot-check gate), then (b) parallel per-chapter extraction waves — Ch 7 split into 2–3 tasks by subsection group given its ~94-page weight — then (c) cross-cutting inventory sections (invariants, D-NN catalog, figures, pillar mapping, SDK extensions), (d) the Homecams appendix as an independent parallel task, and (e) the review/approval gate. No external packages are needed except optionally pymongo/mongosh for the MongoDB metadata query.

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions
- **D-01:** The whitepaper exists only as `docs/CCF_Whitepaper_1-2.pdf`. Convert it to Markdown and commit as `docs/CCF_Whitepaper_1-2.md` — the path CLAUDE.md treats as canonical. All inventory citations reference the `.md` sections.
- **D-02:** Conversion is **Task 1 of the Phase R plan**, on the `phase-r` branch, committed at its own deliverable boundary. Research tasks depend on it.
- **D-03:** Verify conversion with a **section-by-section spot check** against the PDF: every section heading, every figure (Fig-CHNN-MM), tables, and formal type signatures must survive. Fix defects before any research task reads the `.md`.
- **D-04:** Figures: **extract each figure from the PDF as an image into `docs/figures/`**, with a linked placeholder (figure number + caption) at its location in the `.md`. The researcher reads the images directly when building the load-bearing-figures section of the inventory.

### Claude's Discretion
- **Repo prerequisites:** current branch is `master` (not `main`), no `origin` remote, no `phase-r` branch — CLAUDE.md §2.2/§14 expect `main`, origin `github.com/drcastillo/ccf_code` (private, created by Dave), and phase work on `phase-r`. Plan should sequence the §14 prerequisite checks/fixes sensibly; anything only Dave can do (creating the private GitHub repo) is a surfaced blocker, not silently skipped.
- **Inventory entry conventions:** component-key/ID scheme, entry granularity, and D-IMPL numbering for new open questions (CLAUDE.md §12 ends at D-IMPL-29; new ones start at D-IMPL-30).
- **Homecams review depth:** code read per §2.1 discipline; whether/how to run the read-only MongoDB metadata queries §2.1 mentions is Claude's call during planning (surface as a question if connection details are missing).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RSCH-01 | SPEC_INVENTORY.md catalogs every §5–§8 commitment with section, paraphrase, type signature, invariants, dependencies, figure refs, open-question field | Verified section map below gives the exact extraction targets (36 subsections across Ch 5–8); Ch 7 sizing (pages 86–180) drives the task-split recommendation |
| RSCH-02 | Dedicated sections: D-NN governance decisions, load-bearing figures, named invariants, SDK extensions, pillar mapping | Verified counts: 50 figures, 41 unique inline D-NN entries (format "D-15 Per-Mode Replay Footprint"); named invariants enumerated from CLAUDE.md §16; pillar map source is CLAUDE.md §4 |
| RSCH-03 | homecams-patterns appendix with inherit/do-not-inherit markers incl. MongoDB persistence | Homecams structure verified (9 si-* packages, mongo connection string found, port reachable); review-scope guidance below |
| RSCH-04 | Every open question gets D-IMPL-NN; review, triage, Dave approval, D-GATE-R | Numbering starts at D-IMPL-30; review protocol steps from CLAUDE.md §3.1 mapped to final plan tasks |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Phase R scope:** NO design choices, NO code, NO SDK diagrams. Deliverable is an inventory, not a summary — "If Phase R produces a summary instead of an inventory, redo it" (§16).
- **Whitepaper is canonical** (`docs/CCF_Whitepaper_1-2.md` once created); Homecams never overrides it; conflicts logged as informational.
- **Homecams discipline (§2.1):** pattern triangulation only, never port code; read `/home/parkave/homecams_v2/CLAUDE.md` exactly once, additive context only; domain values flagged "do not inherit"; MongoDB metadata via read-only query only.
- **Git discipline (§2.2):** phase work on `phase-r` branch; merge to `main` only at `D-GATE-R`; commits at deliverable boundaries with messages naming the CLAUDE.md section or D-IMPL served; no secrets in tree; `.gitignore` needed.
- **§3.1 review protocol is mandatory and ordered:** `/gsd-review --phase Phase R --all` → blocking/advisory triage → present to Dave → `D-GATE-R` entry in `docs/DECISIONS.md` → merge. Review passing is necessary, never sufficient.
- **§14 first-task items 1–5** (remote/branch confirmation, whitepaper presence, Homecams access, directory skeleton, placeholder docs) are pre-research setup and belong at the start of the Phase R plan.
- **Model mandate:** Anthropic Fable 5, "high" effort, for all Phase R work.
- **§15 discipline:** whitepaper-silent → D-IMPL entry and stop; whitepaper-ambiguous → quote passage, propose 2–3 readings.

## Architectural Responsibility Map

This is a documentation phase; "tiers" here are workstreams, not runtime tiers.

| Capability | Primary Owner | Secondary | Rationale |
|------------|--------------|-----------|-----------|
| Repo prerequisites (§14 items 1–5) | Setup task (Wave 0) | Dave (private repo creation — blocker) | Must precede all commits on `phase-r` |
| PDF → Markdown conversion + figures | Task 1 (locked D-02) | Spot-check gate (D-03) | All extraction cites the `.md`; fidelity gate before any reading |
| §5–§8 commitment extraction | Per-chapter extraction tasks | — | Content lives only in the converted whitepaper |
| Cross-cutting inventory sections (D-NN, figures, invariants, extensions, pillar map) | Synthesis task after chapter extraction | CLAUDE.md §4–§8 (for SDK-extension hooks) | Requires all chapter entries to exist first |
| homecams-patterns appendix | Independent parallel task | MongoDB read-only metadata query (optional) | Depends only on Homecams access, not on the whitepaper conversion |
| D-IMPL logging | Every extraction task (emit) + consolidation into docs/DECISIONS.md | — | Open questions surface during extraction; numbering from D-IMPL-30 |
| Review / approval / merge | Final gate task | Dave (approval authority) | §3.1 protocol, D-GATE-R |

## Verified Source Material Facts (all [VERIFIED: local inspection this session])

### Whitepaper PDF (`docs/CCF_Whitepaper_1-2.pdf`)
- 232 pages, letter, PDF 1.5, unencrypted, 14,284,363 bytes. Producer: LaTeX via pandoc / xdvipdfmx. Author: Dave Castillo, PhD. Title: "Cognitive Context Fabric". Created 2026-05-19.
- Plain-text extraction yields ~9,900 lines (pdftotext, layout intact enough that TOC, headings, and `Fig-CHNN-MM` references survive cleanly).
- **Chapter/section map for the extraction scope (§5–§8):**
  - **Ch 5 — Conceptual Model** (starts ~p. 60s): 5.1 Systems of Record→Cognition; 5.2 Context Graph G(E,R,T,P,Π,L); 5.3 Dynamic Context vs Content; 5.4 Core Thesis; 5.5 Mapping Data Systems to CCF; 5.6 Context Products — Derived not Stored; 5.7 CCF Architecture.
  - **Ch 6 — Context as a Product**: 6.1 Why Data Products Insufficient; 6.2 Definition; 6.3 Context Product Specification; 6.4 Lifecycle; 6.5 Key Principles; 6.6 Search ⇄ Inference Loop.
  - **Ch 7 — System Architecture** (pages 86–180, ~94 pages — the mechanism core): 7.1 Layered L1–L6 (p.86); 7.2 Architectural Decomposition (p.88); 7.3 Context Graph — System of State (p.91); 7.4 Context Operators (p.100); 7.5 Context Projection Π (p.112); 7.6 Context Products — Delivery (p.120); 7.7 Context Debt & Half-life (p.137); 7.8 Control Plane vs Data Plane (p.151); 7.9 Closed Loop Self-Learning (p.159); 7.10 Decision Replay (p.167).
  - **Ch 8 — Enterprise Integration** (p.180–218): 8.1–8.13, incl. 8.3 Non-Invasive Integration Patterns (p.182), 8.4 Alternating Derivation Pipeline (p.194), 8.10 Conversational Reporting Layer (out of SDK scope per CLAUDE.md §13).
  - Ch 9 — CCF Summary (context only; not an extraction target).
  - Ch 1–4 are motivation/context; not inventory targets but Ch 3 (agents) informs the SDK-extension hooks section.
- **Figures:** exactly 50 unique `Fig-CHNN-MM` references: CH01 ×3, CH02 ×2, CH03 ×4, CH04 ×2, CH05 ×2, CH06 ×3, CH07 ×28, CH08 ×6. `pdfimages -list` reports 51 embedded raster images — near 1:1 with figures, so D-04 extraction via `pdfimages` is feasible. Figure captions appear inline as e.g. `Fig-CH07-04: Context Graph — logical six-tuple and physical collection pattern`.
- **Governance decisions (D-NN):** 41 unique inline `D-NN` identifiers found, ranging D-05 to D-56 (non-contiguous: e.g., no D-01..04, D-08/09, D-12, D-24, D-26, D-29, D-32, D-36, D-43, D-49/50 in extracted text). Format is inline named decisions, e.g., "D-15 Per-Mode Replay Footprint", "D-16 Five Disciplines" — there is no single consolidated decision-list section detected, so the D-NN inventory section must be built by sweep-grep + context reading. Note: `D-05` also appears in a "Phase 12 D-05" project-history sense in at least one spot — extraction must disambiguate whitepaper governance decisions from incidental references.

### Repo state
- Branch `master` only; no remote; no `.gitignore`; untracked junk (`._CLAUDE.md`, `CLAUDE.md.orig`). `docs/` contains ONLY the PDF — `docs/SPEC_INVENTORY.md`, `docs/DECISIONS.md`, `docs/DESIGN.md`, `docs/diagrams/`, `/references`, `/src`, `/runtime`, `/tests`, `/examples` do NOT exist yet. §14 items 1–5 are genuinely outstanding.
- `.planning/config.json`: `branching_strategy: "none"` — but CLAUDE.md §2.2 mandates a `phase-r` branch and merge-to-main at the gate. CLAUDE.md wins; the plan must create/use `phase-r` explicitly rather than relying on GSD branching.
- Blocker only Dave can clear: private GitHub repo `github.com/drcastillo/ccf_code` + origin wiring (§2.2). Also: `main` doesn't exist (branch is `master`) — renaming/creating `main` is a Claude-discretion setup step, but the merge target at D-GATE-R must be `main`.

### Homecams reference implementation
- `/home/parkave/homecams_v2` accessible read-only. Top level: `packages/` with 9 packages (`si-app`, `si-conversation`, `si-framework`, `si-inference`, `si-ingest-server`, `si-models`, `si-observer`, `si-pool-safety`, `si-web-ui`), plus `scripts/`, `tests/`, `docs/`, `config/`, and start entrypoints incl. `start_ccf_agent.py`, `start_property_intelligence.py`.
- `/home/parkave/homecams_v2/CLAUDE.md` exists, 829 lines — read once per §2 discipline.
- MongoDB: connection string `mongodb://192.168.4.76:27017/rtdetect` found in `config/`; TCP port 27017 on 192.168.4.76 confirmed OPEN. Mongo-touching code concentrated in `si-pool-safety` (`services/mongo_data_service.py`, `service_container.py`, `cross_camera_assessment_service.py`, enrichment worker) and the `start_*.py` entrypoints.
- **No mongo client available locally**: neither `mongosh`/`mongo` CLI nor `pymongo` is installed. Running the §2.1 read-only metadata query requires installing one (see Package Legitimacy Audit) or reading collection names/shapes from Homecams source code instead — the source-code route is zero-install and likely sufficient for triangulation.

## Standard Stack

This phase produces Markdown documents; there is no library stack. The "stack" is local tooling.

### Core tooling (all pre-installed — verified)
| Tool | Location | Purpose | Status |
|------|----------|---------|--------|
| `pdftotext` (poppler) | /usr/bin | PDF → text for conversion base and verification greps | [VERIFIED: `command -v` + successful runs this session] |
| `pdfimages` (poppler) | /usr/bin | D-04 figure extraction to `docs/figures/` (51 embedded images) | [VERIFIED: `pdfimages -list` ran successfully] |
| `pdfinfo` (poppler) | /usr/bin | Page counts, metadata for spot-check | [VERIFIED] |
| `pandoc` | ~/.local/bin | Markdown normalization if needed (NOT a PDF reader — pandoc cannot ingest PDF) | [VERIFIED: installed] |
| Claude `Read` tool with `pages` param | built-in | Direct visual PDF reading, 20 pages/request — the highest-fidelity conversion path for headings/tables/type signatures | [VERIFIED: tool capability] |

### Conversion approach recommendation
Use a **hybrid**: `pdftotext` output as the mechanical skeleton + Claude reading the PDF in ≤20-page windows (232 pages ⇒ ~12 windows) to reconstruct faithful Markdown with headings, tables, and type signatures, and `pdfimages`/page-render extraction for the 50 figures. Pure `pdftotext` loses heading levels and table structure (this is a math-heavy LaTeX document — the extracted text already shows glyph issues like `Insuﬀicient` and `Search � Inference`); those defects are exactly what the D-03 spot-check gate exists to catch. Confidence: HIGH.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hybrid pdftotext + Read-tool conversion | `pymupdf4llm` / `marker-pdf` (PDF→md Python packages) | Better automation, but requires installing unverified packages and still needs the D-03 spot check; not worth the supply-chain surface for a one-time conversion [ASSUMED] |
| `pdfimages` raster extraction | Page-region rendering via `pdftoppm` (also poppler, verified installed with poppler-utils — confirm with `command -v pdftoppm` at plan time) | pdfimages extracts embedded rasters at native resolution (preferred); pdftoppm renders whole pages (fallback if a figure is vector-drawn) |
| pymongo install for Mongo metadata | Read collection names from Homecams source (`mongo_data_service.py` etc.) | Zero-install, satisfies §2.1 triangulation intent; live query only adds collection stats/index metadata |

## Package Legitimacy Audit

No package installs are required for the core phase work — all tooling is pre-installed system software. One optional install:

| Package | Registry | Purpose | slopcheck | Disposition |
|---------|----------|---------|-----------|-------------|
| `pymongo` | PyPI | Optional read-only Mongo metadata query (§2.1) | not run (slopcheck unavailable in this environment) | `[ASSUMED]` — pymongo is the long-standing official MongoDB Python driver, but per protocol without slopcheck it is tagged ASSUMED; planner should gate any install behind checkpoint:human-verify, or prefer the zero-install source-code route |

**Packages removed due to [SLOP]:** none. **Recommendation:** avoid the install entirely — derive Mongo persistence patterns from Homecams source code; run a live query only if Dave wants collection-level metadata (surface as a question).

## Architecture Patterns

### Workflow diagram

```
[Wave 0: Setup]
  repo prereqs (§14 1–5): .gitignore, skeleton dirs, placeholder docs,
  branch phase-r (from master; main creation/origin = Dave-dependent blocker surfaced)
        |
        v
[Task 1 (locked): PDF → docs/CCF_Whitepaper_1-2.md + docs/figures/ (50 figs)]
        |
        v
[D-03 spot-check gate: headings / figures / tables / type signatures vs PDF]
        |
        +--------------------+---------------------+
        v                    v                     v
[Ch 5 + Ch 6 extraction] [Ch 7 extraction        [Ch 8 extraction]      [Homecams review →
 (13 subsections)]        split 7.1–7.4 /          (13 subsections)]      homecams-patterns
                          7.5–7.7 / 7.8–7.10]                             appendix]  (parallel,
        |                    |                     |                      independent of conversion)
        +--------------------+---------------------+----------------------+
        v
[Synthesis: cross-cutting inventory sections — D-NN catalog (41 entries),
 load-bearing figures (50), named invariants, SDK extensions + hooks,
 pillar-by-pillar mapping; consolidate D-IMPL-30+ into docs/DECISIONS.md]
        |
        v
[§16 completeness self-audit → /gsd-review --phase "Phase R" --all → triage →
 fix blocking → present to Dave → D-GATE-R → merge phase-r → main]
```

### Pattern 1: Inventory entry template (define once, enforce everywhere)
Every entry needs the same seven fields (CLAUDE.md §16): whitepaper section, paraphrased commitment, type signature (where given), invariants, dependencies, figure refs, open-question field. Recommend a component-key scheme like `INV-<layer/area>-<NN>` (e.g., `INV-L3-01` for graph primitives, `INV-CP-xx` for Control Plane, `INV-OPS-xx` operators, `INV-PROD-xx` products) — planner discretion per CONTEXT.md, but the scheme must be fixed in the FIRST extraction task and reused by all, since parallel tasks writing one document need non-colliding keys. Simplest collision-avoidance: each chapter task writes its own section of SPEC_INVENTORY.md (or its own fragment file merged by the synthesis task) with a chapter-scoped key prefix.

### Pattern 2: Extraction tasks emit, synthesis task consolidates
Each chapter task appends candidate open questions (with quoted ambiguous passages per §15) to a working list; the synthesis task assigns final `D-IMPL-NN` numbers from D-IMPL-30 upward and writes `docs/DECISIONS.md`. This avoids number collisions across parallel tasks.

### Pattern 3: Completeness by enumeration, not by memory
The §16 gate is "no whitepaper section in §5–§8 lacks coverage." Build a checklist directly from the verified section map above (36 subsections) and mechanically tick it. Same for the 50 figures and 41 D-NN identifiers — grep the converted `.md` and diff against the verified lists.

### Anti-Patterns to Avoid
- **Summary drift:** prose summaries instead of field-structured entries → automatic redo per §16.
- **Design leakage:** any "the SDK should…" resolution inside the inventory is Phase D scope; it belongs in the open-question field / D-IMPL entry instead.
- **Homecams inheritance:** copying Homecams resolutions as defaults. Whitepaper-silent + Homecams-resolved = D-IMPL entry, per §2.1.
- **Citing the PDF:** all inventory citations must reference the `.md` sections (locked D-01).
- **Monolithic conversion task:** one task attempting all 232 pages in a single context will degrade fidelity in Ch 7's dense middle; window it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Figure extraction | screenshot-by-hand or ad-hoc scripts | `pdfimages -all` (+ `pdftoppm` fallback for vector figures) | Native-resolution embedded images, deterministic, already installed |
| Coverage verification | eyeballing | grep-diff of converted .md against the verified 36-subsection / 50-figure / 41-D-NN lists | Mechanical completeness proof for §16 |
| PDF → md conversion library install | pip-installing converters | pdftotext skeleton + Read-tool page windows | Zero supply-chain surface; the D-03 gate requires human-grade fidelity checking anyway |
| Mongo metadata | installing drivers by default | reading `si_pool_safety/services/mongo_data_service.py` and friends | Collection names, shapes, and persistence patterns are in code; §2.1 needs triangulation, not a live census |

## Common Pitfalls

### Pitfall 1: pdftotext glyph corruption in the canonical .md
**What goes wrong:** Ligatures (`ﬀ`), math symbols (`⇄` extracted as `�`, `λ_c`, `Π`, six-tuple notation) corrupt in plain-text extraction; the "formal type signatures must survive" D-03 requirement fails silently.
**How to avoid:** Reconstruct math/notation from the visually-read PDF pages, not from pdftotext output; spot-check specifically targets §5.2 (G six-tuple), §7.3–7.6 (signatures), §7.7 (λ_c, D_c formulas).
**Warning signs:** `�` characters, `ﬀ/ﬁ` ligatures, missing sub/superscripts in the .md.

### Pitfall 2: Context-budget blowout on Ch 7
**What goes wrong:** Ch 7 spans ~94 pages with 28 figures and most of the formal mechanism; one task cannot hold conversion + extraction + prior entries.
**How to avoid:** Split Ch 7 extraction into ~3 tasks along the natural seams (7.1–7.4 state/operators, 7.5–7.7 projection/products/debt, 7.8–7.10 planes/loop/replay); each task reads only its .md slice.

### Pitfall 3: D-NN false positives and gaps
**What goes wrong:** `D-NN` appears in non-governance contexts (e.g., "Phase 12 D-05" project history at line ~6082 of extracted text); conversely non-contiguous numbering (gaps at D-08/09, D-12, D-24, D-26, D-29, D-32, D-36, D-43, D-49/50 in text extraction) may mean some decisions live only in figures/tables that pdftotext dropped.
**How to avoid:** The D-NN inventory task greps the converted .md AND visually checks figure images and tables for decision boxes; disambiguate each hit by reading surrounding context; report the gap-numbers explicitly as "not found in whitepaper" rather than silently omitting.

### Pitfall 4: D-IMPL number collisions from parallel tasks
**How to avoid:** extraction tasks emit unnumbered open questions; synthesis task assigns D-IMPL-30+ sequentially (Pattern 2).

### Pitfall 5: Git prerequisites half-done
**What goes wrong:** Work committed on `master` with no `phase-r` branch, or the merge target `main` never created; D-GATE-R merge step then fails or violates §2.2.
**How to avoid:** Wave-0 task: create `main` from `master` (or rename), create `phase-r` from it, add `.gitignore` (junk files `._*`, `*.orig`), and surface the origin-remote/private-repo item as a Dave blocker in the plan (checkpoint), not a silent skip.

### Pitfall 6: `/gsd-review` treated as the gate
**How to avoid:** The plan's final tasks must model the full §3.1 sequence: self-review → triage (blocking fixed in-phase) → present to Dave (human checkpoint) → D-GATE-R logged in docs/DECISIONS.md → merge. Dave's approval is the gate; the review is a precondition.

## Runtime State Inventory

Not applicable — no rename/refactor/migration. (Docs-only greenfield phase.)

## Environment Availability

| Dependency | Required By | Available | Version/Notes | Fallback |
|------------|------------|-----------|---------------|----------|
| pdftotext / pdfinfo / pdfimages (poppler) | Conversion, spot-check, figure extraction | ✓ | /usr/bin | — |
| pandoc | md normalization (optional) | ✓ | ~/.local/bin | not needed |
| Claude Read tool PDF pages | High-fidelity conversion windows | ✓ | 20 pp/request, 232 pp ⇒ ~12 windows | — |
| git | branching, commits | ✓ | repo present | — |
| GitHub origin remote (private repo) | §2.2/§14 item 1 | ✗ | Dave must create repo | **Blocker to surface** — all other work proceeds locally |
| /home/parkave/homecams_v2 (read) | RSCH-03 | ✓ | 9 packages, CLAUDE.md 829 lines | — |
| MongoDB 192.168.4.76:27017 | optional §2.1 metadata query | ✓ port open | no local client (no mongosh, no pymongo) | Read persistence patterns from Homecams source (recommended) |
| `/gsd-review` command | RSCH-04 | assumed (GSD plugin present per project setup) | — | — |

**Missing with no fallback:** GitHub origin remote — Dave-only action; blocks the final push/merge visibility, not the phase work itself. Surface as checkpoint.

## Validation Architecture

Docs-only phase — no test framework applies; validation is structural.

| Req ID | Behavior | Validation Type | Check | Exists? |
|--------|----------|-----------------|-------|---------|
| RSCH-01 | Every §5–§8 subsection covered with all 7 entry fields | mechanical checklist | grep-diff inventory section refs against the verified 36-subsection list | build in synthesis task |
| RSCH-02 | 5 dedicated sections present | structural | section-heading check + counts (50 figures, 41 D-NN) vs verified lists | build in synthesis task |
| RSCH-03 | Appendix with markers | manual + structural | every appendix entry carries "candidate pattern" or "domain-specific — do not inherit" | in appendix task |
| RSCH-04 | D-IMPL entries + review protocol | procedural | every open-question field references a D-IMPL-NN; §3.1 steps executed in order | final gate tasks |
| D-03 | Conversion fidelity | manual spot-check | per-section heading/figure/table/signature comparison vs PDF | gate task after Task 1 |

- **Per task commit:** the task's own checklist green (e.g., chapter subsection list fully ticked).
- **Phase gate:** §16 element-by-element audit + `/gsd-review --phase "Phase R" --all` clean of blocking findings before presenting to Dave.
- **Wave 0 gaps:** none in the test-infrastructure sense; the "gap" is the placeholder docs and checklists themselves.

## Security Domain

Minimal for a docs phase, but two real items:
- **Secrets:** the Homecams Mongo connection string (`mongodb://192.168.4.76:27017/rtdetect`) is internal-network, apparently unauthenticated. Do NOT commit connection strings or any live query output containing data records into `ccf_code`; the appendix documents collection *names and shapes* only. Repo stays private (§2.2).
- **Supply chain:** no package installs recommended; if pymongo is installed anyway, gate behind human-verify (see audit).
- ASVS categories: not applicable (no code shipped this phase).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pymongo` on PyPI is the official MongoDB driver (only relevant if live query chosen) | Package Audit | Low — recommended route avoids the install entirely |
| A2 | `/gsd-review` accepts `--phase "Phase R" --all` as CLAUDE.md writes it | Validation | Low — syntax check at execution time; adjust invocation |
| A3 | The 51 embedded raster images map ~1:1 to the 50 figures (some figures could be vector-only) | Conversion | Medium — D-03 spot check catches misses; `pdftoppm` page render is the fallback |
| A4 | D-NN gaps (e.g., D-24, D-49) are genuinely absent from the whitepaper rather than lost in text extraction | RSCH-02 | Medium — figure/table visual sweep in the D-NN task mitigates |

## Open Questions

1. **MongoDB live query — run it or not?**
   - Known: port open, connection string found, no client installed; §2.1 says metadata query "will require a readonly query"; CONTEXT.md leaves depth to Claude.
   - Recommendation: source-code-derived collection inventory in the appendix; add one plan question/checkpoint asking Dave whether a live metadata query is wanted (and to approve the pymongo install if so).
2. **`main` branch creation.** Repo is on `master`; §2.2 assumes `main`. Recommendation: Wave-0 creates `main` from current `master` HEAD and branches `phase-r` from it; note in commit message. (Low risk; within setup discretion.)
3. **Origin remote timing.** Dave must create the private repo. Recommendation: surface as a checkpoint early (Wave 0) but do not block extraction work on it — only the final merge/push visibility depends on it.

## Sources

### Primary (HIGH confidence — direct local inspection, 2026-07-24)
- `docs/CCF_Whitepaper_1-2.pdf` — pdfinfo metadata, full pdftotext extraction, TOC parse, figure/D-NN greps, pdfimages listing
- Repo git state, `.planning/config.json`, `.planning/REQUIREMENTS.md`, `01-CONTEXT.md`
- `/home/parkave/homecams_v2` directory tree, mongo config grep, TCP probe to 192.168.4.76:27017
- `CLAUDE.md` (rev 4) — §2–§4, §12–§16

### Secondary / Tertiary
- None needed — no external web research was required for this phase.

## Metadata

**Confidence breakdown:**
- Source-material facts (section map, figure/D-NN counts, tooling, repo state): HIGH — directly verified this session
- Conversion-approach recommendation: HIGH — grounded in verified tool behavior and observed extraction defects
- Homecams appendix scoping: MEDIUM — structure verified, but code depth of the 9 packages not yet read (that reading IS the phase work)

**Research date:** 2026-07-24
**Valid until:** stable — sources are local, static files; re-verify only repo git state before planning
