# Phase 14: Documentation Suite - Context

**Gathered:** 2026-08-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the built SDK into a documentation site an outside engineering team can adopt from — adopter's guide, generated Protocol/API reference, definition-artifact schema reference, how-to and concepts pages, security & deployment notes with a drift-checked OpenAPI spec, PERFORMANCE.md publishing the Phase 11 measured baselines, and the narrated demo walkthrough — with `make docs --strict` joining always-on CI.

Every API signature is generated, every number is measured, and every snippet is literal-included from CI-run code. Hand-written signatures and pasted snippets are the phase's explicit non-goal.

**Not in this phase:** hosting or publishing the site (ruled CI-artifact-only by D-IMPL-71), new SDK surface, new examples, changes to the fabric.

</domain>

<decisions>
## Implementation Decisions

### Site source layout + publish safety

- **D-01: `docs_dir` is a new top-level `public/` directory.** The published surface is a repo-root peer of `src/ runtime/ examples/ tests/ docs/` with exactly one job. `docs/` stays the internal and canonical tree — `CCF_Whitepaper_1-2.md`, `DECISIONS.md`, `SPEC_INVENTORY.md`, `DESIGN.md`, `FEASIBILITY.md`, `ROADMAP.md`, `PHASE_I*_GATE.md`, `09-ruling-batch-minicycle.md` — and is structurally unreachable by the site build. The posture is default-deny: a file is published only by being deliberately placed in `public/`.
  - A `client/` directory was proposed and rejected: "client" is already load-bearing in this repo (the MCP client role per CLAUDE.md §7.1 and `src/ccf/mcp/`; the `client_bare.py` / `client_anthropic.py` / `client_adk.py` consumer legs in `examples/external/`). A Markdown directory must not borrow either meaning.
- **D-02: The never-publish guarantee is proven by a post-build content scan of the rendered site.** After `mkdocs build --strict`, a CI step scans the built output tree for proprietary markers and fails on any hit. The scan runs against the artifact that actually gets uploaded, so it catches leaks arriving through snippet includes, mkdocstrings docstrings, or symlinks — not only stray files.
  - **Scan definition constraint (from D-14):** the scan must key on quoted whitepaper **body text**, not on bare `§`/section references — otherwise the whitepaper cross-reference index trips its own gate.
- **D-03: Publishable files move out of `docs/` into `public/`.** `git mv` for `docs/demo-walkthrough.md`, `docs/security-notes.md`, and `docs/diagrams/`. One home per file; no duplication, no sync question, and no include directive reaching *into* `docs/` (which would be the exact escape path the boundary exists to prevent). Inbound references from READMEs and CLAUDE.md are fixed as part of the move.
- **D-04: Mermaid diagrams render in-page** via mkdocs-material's native support (`pymdownx.superfences`). The `.mmd` file stays the single artifact so diagrams cannot drift, light/dark theming is automatic, and no Node/mermaid-cli toolchain enters the always-on CI docs job.
- **D-05: The rendered site uploads as an Actions artifact on every always-on CI run**, default retention. Under D-IMPL-71's nothing-is-hosted posture this is how the docs actually get read; source is versioned, so retention expiry is harmless.
- **D-06: `public/README.md` states the publish boundary** — excluded from the site nav. Short, CONTRIBUTING-style: everything here is published; the whitepaper and internal deliverables live in `docs/` and must never be referenced from here; the post-build scan enforces it. Mirrors the `examples/` family-charter README pattern that carries the No-Hardcoding Rule.

### Snippet include + drift mechanism

- **D-07: Named section markers in the example sources.** `pymdownx.snippets` with `--8<-- "examples/00-quickstart/run.py:assemble"` resolving `# --8<-- [start:assemble]` / `[end:assemble]` comments in the source. Refactor-proof — reordering or inserting lines never silently shifts a snippet. Marker comments in example sources are an accepted, intentional cost.
  - **Line-range includes are explicitly rejected**: line numbers rot on the first refactor and a strict build happily includes the wrong lines, which is precisely the drift failure DOCS-01's non-goal targets.
- **D-08: An unresolved marker or missing file fails the strict build** — never a silently-empty block. Because `make docs --strict` joins always-on CI per D-IMPL-72, a deleted marker breaks the build in the same commit that deletes it.
- **D-09: Definition artifacts are literal-included by the same mechanism.** The No-Hardcoding Rule (§6.4) makes artifacts the adopter's primary authoring surface; pasted YAML would drift from the artifacts CI actually runs, reintroducing the defect the code rule prevents. **Planning detail to resolve:** JSON artifacts cannot carry comment markers — those need whole-file include or an extraction step.
- **D-10: Snippets are sourced from the existing `examples/00`–`07` suite plus `examples/external/`.** The install → ontology → agent → workflow → replay arc maps onto `00-quickstart`, `01-agent-basics`, `02-skilling`, `05-workflow-hitl`, `06-decision-replay`, with `examples/external/` supplying the consumer view. No ninth example is built or kept green — the adopter's guide is a narration layer over already-proven CI-run code.

### Schema, API, and OpenAPI reference generation

- **D-11: The definition-artifact schema reference is generated at docs build from the Pydantic models** (mkdocs hook / `gen-files` step emitting JSON Schema rendered into reference pages). Cannot drift by construction — the same argument that makes the API reference generated rather than hand-written. Prose commentary lives in a hand-written page beside the generated output.
- **D-12: `openapi.json` is committed, regenerated from `create_app()` in CI, and drift-checked.** DOCS-05 says "drift check," which presupposes a stored baseline; it is also the HTTP contract external integrators consume, so endpoint changes should surface as reviewable diffs. This is a deliberate exception to D-11's generate-at-build posture, for those two reasons.
- **D-13: The API reference is curated by hand to the Protocols and public contracts** — storage, similarity, harness adapter, artifact store, orchestration, HITL, plus the Context Product contract, the six archetypes, and the Agent & Task Factory. mkdocstrings still generates every signature and docstring; only the *selection* of surfaces is curated. A full auto-generated module tree was rejected as burying the handful of Protocols an integrator needs and publishing internal helpers alongside the adopter surface.
- **D-14: mkdocstrings' own strict-mode failure catches renames and removals.** An unresolvable `::: ccf.…` identifier errors under `mkdocs build --strict` — the same single gate that catches snippet-marker drift (D-08), no extra tooling. A public-surface coverage lint (catching *undocumented additions*) was considered and not adopted for v0.

### Nav structure + doc placement

- **D-15: Diátaxis top-level nav — Tutorial / How-to / Concepts / Reference.** DOCS-01–04 already decompose along exactly these lines, and the convention means contributors know where a new page belongs without asking.
- **D-16: The five Common Pillars are a Concepts section, one page per pillar** — each embedding its existing Phase D diagram from `public/diagrams/` and linking down to the Reference surfaces that realize it. The one-per-pillar diagrams already exist, so the section is largely assembly.
- **D-17: Placement of the carried-over documents** — PERFORMANCE.md → **Reference** (measured fact with methodology and environment manifest); security & deployment notes → **How-to** (operator standing it up safely); narrated demo walkthrough → **Tutorial**, beside the adopter's guide.
- **D-18: The whitepaper cross-reference index shows section numbers and titles only, no quoted body text.** A table mapping each SDK surface to the whitepaper section that specifies it (e.g. `ContextProduct` → §6.3, §7.6). Useful to anyone holding the whitepaper, discloses no proprietary content, and keeps the publish-safety scan satisfiable. Paraphrasing the commitments was rejected as still-derived content that muddies the scan definition.

### Post-research rulings (Dave, 2026-08-03)

Added after `14-RESEARCH.md` surfaced four items the discussion could not have anticipated.

- **D-19: DOCS-06 ships with real measured numbers — the baseline is run and committed inside Phase 14.** Research found `perf/baselines/` holds only `.gitkeep` and `perf/results/` is gitignored, so there was nothing measured to publish. Dave approves running the Phase 11 battery on a named runner class and committing the resulting baseline under D-IMPL-70's Dave-gated re-baseline ritual, logged as **D-IMPL-75**. Consequence: Phase 14 carries a measurement plan, not only a documentation plan, and the baseline commit is a gated act requiring Dave's sign-off on the produced numbers before PERFORMANCE.md cites them.
- **D-20: The 13 whitepaper-quoting docstrings are rewritten to paraphrase + `§` citation.** Research found verbatim body-text quotes at ≥10 words in `src/ccf/halflife/{debt,decay}.py`, `src/ccf/peering/__init__.py`, `src/ccf/projection/__init__.py`, `src/ccf/controlplane/artifacts.py`, `src/ccf/operators/{planner,categories}.py`, and `runtime/ccf_runtime/cdc/adapter.py` — all of which mkdocstrings would publish. Each is reworked to a paraphrased commitment plus its section citation, per CLAUDE.md §11 ("cite the section in the docstring of every public class"). **No allowlist**: the publish-safety scan stays purely default-deny with zero exceptions, and narrowing the D-13 reference selection to hide the modules was rejected as fragile — it would silently re-expose the text the first time a Protocol page is added. Wave 0 work; blocks the first green publish scan.
- **D-21: `README.md` does not become the site index.** The site gets a purpose-written `public/index.md`. README currently links three never-publish paths (the whitepaper and internal phase deliverables); a README obliged to stay scan-clean is a standing trap for every future contributor.
- **D-22: `D-IMPL-NN` identifiers may appear on published pages.** Bare decision-ID references (e.g. "ruled under D-IMPL-71") disclose no proprietary content and keep the published docs traceable to the decision log. Carried-over documents do not need them stripped.

### Claude's Discretion

Every question in this discussion received an explicit ruling. Two items remain planning-level detail rather than open decisions: the JSON-artifact include mechanism (D-09 — research finds this largely moot, as all 65 example definition artifacts are YAML and the 13 JSON files are replay fixtures and gitignored output, not an authoring surface) and the exact marker-string set the publish scan keys on (D-02/D-18 — research recommends 10-word normalized shingles, validated with positive and negative controls).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rulings that bind this phase
- `docs/DECISIONS.md` — **D-IMPL-71** (docs toolchain and publishing posture: mkdocs-material + mkdocstrings; `make docs --strict` builds in CI and the rendered site uploads as an Actions artifact; **nothing is hosted**; private-Pages unavailable on this plan; hosting stays a future D-IMPL). **D-IMPL-72** (amendment of Phase-8 D-10: `make ci` becomes `ci-core examples docs-strict` and ci.yml gains the corresponding job, **effective at the Phase 14 plan that creates the docs build target**). **D-IMPL-70** (perf governance — bounds what PERFORMANCE.md may claim and how baselines are re-based). **D-IMPL-28** (definition artifact format — the surface DOCS-03 documents).
- `docs/09-ruling-batch-minicycle.md` — items 3, 4, 5: the surfacing context behind D-IMPL-70/71/72.

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 14 entry: goal, dependencies (Phases 9, 11, 12, 13), five success criteria.
- `.planning/REQUIREMENTS.md` — DOCS-01 … DOCS-06, plus the non-goal "Hand-written API signatures or pasted snippets in docs — generated reference and literal-includes only (drift prevention)"; DEMO-03 (narrated walkthrough in the docs site, literal-including the example's code and artifacts).
- `CLAUDE.md` §2.2 (private repo, proprietary IP — the reason for the publish boundary), §4 (the five Common Pillars, the Concepts section's subject), §6.4 (No-Hardcoding Rule — why artifacts are literal-included), §10 (L1–L6 + the two planes), §11 (docstrings cite the whitepaper section — the substance mkdocstrings renders).

### Content sources to be moved or included
- `docs/demo-walkthrough.md` — moves to `public/`, becomes the Tutorial-section walkthrough (DEMO-03).
- `docs/security-notes.md` — moves to `public/`, becomes the How-to security & deployment notes (DOCS-05).
- `docs/diagrams/*.mmd` — moves to `public/diagrams/`; five pillar diagrams plus `seam-artifact-store`, `seam-harness-adapter`, and the sequence diagrams. Rendered in-page as Mermaid.
- `examples/` (`00-quickstart` … `07-artifact-store-mcp`) and `examples/external/` — the snippet source of record; get `--8<-- [start:…]` markers.
- `docs/SPEC_INVENTORY.md` — the existing SDK-surface → whitepaper-section mapping the cross-reference index (D-18) derives from. **Stays internal; never published.**

### Must NOT be published (the scan's targets)
- `docs/CCF_Whitepaper_1-2.md`, `docs/CCF_Whitepaper_1-2.pdf`, `docs/DECISIONS.md`, `docs/SPEC_INVENTORY.md`, `docs/DESIGN.md`, `docs/FEASIBILITY.md`, `docs/ROADMAP.md`, `docs/PHASE_I*_GATE.md`, `docs/09-ruling-batch-minicycle.md`, and everything under `.planning/`.

### Toolchain and CI surfaces to modify
- `Makefile` — gains `docs` / `docs-strict`; `ci: ci-core examples` becomes `ci: ci-core examples docs-strict` per D-IMPL-72. The Makefile mirrors `ci.yml` command-for-command (D-10) and uses `PYTHON := .venv/bin/python` with `PYTHONPATH=src:runtime`.
- `.github/workflows/ci.yml` — gains the docs job plus artifact upload. (`perf.yml` and `live-legs.yml` stay opt-in per D-IMPL-70 / D-11 and are not touched.)
- `pyproject.toml` — docs dependencies (mkdocs-material, mkdocstrings[python], pymdown-extensions) as an extra; `[tool.mypy] files` is authoritative for the typecheck surface.
- `tools/lints/` — the existing CINV lint harness, the pattern any new docs-side check follows. (Corrected 2026-08-03: this was written as `src/ccf/lints/`, which does not exist. `14-RESEARCH.md` and `14-PATTERNS.md` have the correct path.)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The eight-example suite + `examples/external/`** — already run green in always-on CI (`make examples`, `CCF_REQUIRE_HARNESSES=1`). Becomes the snippet source of record; the guide narrates rather than reimplements.
- **`docs/diagrams/*.mmd`** — one diagram per pillar plus the two seam diagrams and three sequence diagrams, authored in Phase D. The Concepts section is mostly assembly over these.
- **`docs/security-notes.md` and `docs/demo-walkthrough.md`** — Phase 9–10 and Phase 12 content already written; they move rather than get rewritten (their snippet blocks convert to literal-includes).
- **Citation-bearing docstrings across `src/`** — CLAUDE.md §11 requires every public class to cite its whitepaper section, so the API reference's substance already exists; mkdocstrings surfaces it.
- **`tools.lints` harness** — the established pattern for a repo-wide invariant check, if the publish scan or any docs check wants a local-feedback sibling.

### Established Patterns
- **Makefile mirrors CI command-for-command (D-10).** Any docs target must be runnable identically locally and in Actions; the docs job cannot use a command that has no Makefile equivalent.
- **`PYTHONPATH=src:runtime` with the venv interpreter explicitly**, never relying on a fresh editable install.
- **Charter README beside a governed directory** (`examples/external/README.md`, the family charter) — the precedent D-06's `public/README.md` follows.
- **Always-on CI is deterministic-only** (D-10/D-11 split); anything network-or-key-dependent is opt-in. The docs build must be fully deterministic and offline to join always-on CI.

### Integration Points
- **New `public/` tree** at repo root — the only directory mkdocs reads.
- **`make ci` composition** — D-IMPL-72 pre-authorized the change; this phase performs the wiring, and the plan that creates the docs target is the one that makes the edit (no dead target lands earlier).
- **`create_app()`** in the runtime HTTP surface — the source of the committed `openapi.json` and its drift check.
- **Definition-artifact Pydantic models** (per D-IMPL-28) — the source of the generated schema reference.

</code_context>

<specifics>
## Specific Ideas

- The publish boundary is the phase's defining safety property, and it is deliberately *structural* rather than procedural: `public/` is default-deny by existence, `docs/` is unreachable, and the post-build scan proves it on the artifact that ships. Reviewers should be able to answer "could the whitepaper leak?" by looking at the directory layout, not by trusting an exclude list.
- Directory naming in this repo carries invariant weight (`/src` vs `/runtime` is the harness-neutrality lint boundary; `/examples` is the No-Hardcoding boundary). `public/` was chosen to name the *published surface* using web-docroot convention, and `client/` was rejected for colliding with two existing architectural meanings of "client."
- One strict build is the single drift gate for three distinct failure classes: unresolved snippet markers (D-08), unresolvable mkdocstrings identifiers (D-14), and broken internal links. Preferring that one mechanism over bespoke lints was a repeated choice through this discussion.

</specifics>

<deferred>
## Deferred Ideas

- **Hosting the site.** Explicitly a future D-IMPL under D-IMPL-71 — revisit only if the repo's visibility posture changes. mkdocs output is host-agnostic, so a later ruling starts from the same build. `mike` versioning was already declined.
- **A public-surface docs-coverage lint** (fails when a newly exported Protocol has no reference page) — considered under D-14, not adopted for v0. Worth revisiting if the Protocol surface grows post-v0.
- **A separate marker-inventory lint** for fast local feedback on snippet markers — the strict build covers correctness; this would only improve error messages.
- **Gray areas raised but not discussed** (the user was ready for context): the how-to guide inventory (which tasks earn their own page), whether the docs build is its own CI job or folds into an existing one, and whether the top-level `README.md` becomes the site index or stays distinct. All are planner-level calls within the decisions above.

</deferred>

---

*Phase: 14-Documentation Suite*
*Context gathered: 2026-08-03*
