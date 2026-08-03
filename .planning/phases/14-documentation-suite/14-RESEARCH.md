# Phase 14: Documentation Suite - Research

**Researched:** 2026-08-03
**Domain:** MkDocs documentation toolchain, drift-gated literal includes, generated API/schema reference, publish-safety scanning
**Confidence:** HIGH (every load-bearing mechanism claim below was verified empirically in a throwaway venv against the exact package versions, not read from docs)

## Summary

Every mechanism this phase depends on was probe-tested in a scratch venv with the current
releases (mkdocs 1.6.1, mkdocs-material 9.7.7, mkdocstrings 1.0.6, mkdocstrings-python 2.0.5,
pymdown-extensions 11.0.1, griffe-pydantic 1.3.1, pydantic 2.13.4 — the repo's exact pin).
The four drift gates D-07/D-08/D-11/D-14 all work, but **two of them do not work with default
settings** and the difference is silent: `pymdownx.snippets` swallows both a missing file *and*
a missing named section unless `check_paths: true` is set, and `mkdocs --strict` alone does not
turn that into an error because nothing is emitted at all. `check_paths: true` is not optional
in this repo — it is the entirety of D-08.

The publish-safety scan (D-02) was prototyped and validated against real repo content. A
10-word normalized-shingle set built from `docs/CCF_Whitepaper_1-2.md` (107,712 shingles, built
in 0.04 s) fires 60 hits on `docs/DESIGN.md` (positive control) and **zero** hits on both
`docs/security-notes.md` and `docs/demo-walkthrough.md` (the two files D-03 moves into
`public/`). It also uncovered the phase's most important latent finding: **13 existing
docstrings in `src/` and `runtime/` quote whitepaper body text verbatim at ≥10 words**, and
mkdocstrings will publish them. D-02's premise — that leaks arrive through docstrings, not
stray files — is empirically correct in this repo today.

Two items need Dave, not the planner. (1) `perf/baselines/` contains only `.gitkeep` and
`perf/results/` is gitignored, so **there are no committed measured numbers for PERFORMANCE.md
to publish** — and committing a baseline is a Dave-gated act under D-IMPL-70. (2) The 13
whitepaper-quoting docstrings must be reworded (recommended) or allowlisted (weakens the gate).

**Primary recommendation:** One root `mkdocs.yml` with `docs_dir: public`, `pymdownx.snippets`
at `base_path: ["."]` + `check_paths: true` + `dedent_subsections: true`, mkdocstrings with
`paths: ["src", "runtime"]` and the `griffe_pydantic` extension at `schema: true` (which
satisfies D-11 with zero custom hook code), explicit `validation:` levels raised to `warn` so
`--strict` catches links and anchors, a pytest-based `openapi.json` drift check reusing the
existing `tests/http_api/conftest.py::app` fixture, and a `tools/publish_scan.py` shingle
scanner run over `site/` in CI before artifact upload.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Site source layout + publish safety**

- **D-01: `docs_dir` is a new top-level `public/` directory.** The published surface is a repo-root peer of `src/ runtime/ examples/ tests/ docs/` with exactly one job. `docs/` stays the internal and canonical tree — `CCF_Whitepaper_1-2.md`, `DECISIONS.md`, `SPEC_INVENTORY.md`, `DESIGN.md`, `FEASIBILITY.md`, `ROADMAP.md`, `PHASE_I*_GATE.md`, `09-ruling-batch-minicycle.md` — and is structurally unreachable by the site build. The posture is default-deny: a file is published only by being deliberately placed in `public/`.
  - A `client/` directory was proposed and rejected: "client" is already load-bearing in this repo (the MCP client role per CLAUDE.md §7.1 and `src/ccf/mcp/`; the `client_bare.py` / `client_anthropic.py` / `client_adk.py` consumer legs in `examples/external/`). A Markdown directory must not borrow either meaning.
- **D-02: The never-publish guarantee is proven by a post-build content scan of the rendered site.** After `mkdocs build --strict`, a CI step scans the built output tree for proprietary markers and fails on any hit. The scan runs against the artifact that actually gets uploaded, so it catches leaks arriving through snippet includes, mkdocstrings docstrings, or symlinks — not only stray files.
  - **Scan definition constraint (from D-14):** the scan must key on quoted whitepaper **body text**, not on bare `§`/section references — otherwise the whitepaper cross-reference index trips its own gate.
- **D-03: Publishable files move out of `docs/` into `public/`.** `git mv` for `docs/demo-walkthrough.md`, `docs/security-notes.md`, and `docs/diagrams/`. One home per file; no duplication, no sync question, and no include directive reaching *into* `docs/` (which would be the exact escape path the boundary exists to prevent). Inbound references from READMEs and CLAUDE.md are fixed as part of the move.
- **D-04: Mermaid diagrams render in-page** via mkdocs-material's native support (`pymdownx.superfences`). The `.mmd` file stays the single artifact so diagrams cannot drift, light/dark theming is automatic, and no Node/mermaid-cli toolchain enters the always-on CI docs job.
- **D-05: The rendered site uploads as an Actions artifact on every always-on CI run**, default retention. Under D-IMPL-71's nothing-is-hosted posture this is how the docs actually get read; source is versioned, so retention expiry is harmless.
- **D-06: `public/README.md` states the publish boundary** — excluded from the site nav. Short, CONTRIBUTING-style: everything here is published; the whitepaper and internal deliverables live in `docs/` and must never be referenced from here; the post-build scan enforces it. Mirrors the `examples/` family-charter README pattern that carries the No-Hardcoding Rule.

**Snippet include + drift mechanism**

- **D-07: Named section markers in the example sources.** `pymdownx.snippets` with `--8<-- "examples/00-quickstart/run.py:assemble"` resolving `# --8<-- [start:assemble]` / `[end:assemble]` comments in the source. Refactor-proof — reordering or inserting lines never silently shifts a snippet. Marker comments in example sources are an accepted, intentional cost.
  - **Line-range includes are explicitly rejected**: line numbers rot on the first refactor and a strict build happily includes the wrong lines, which is precisely the drift failure DOCS-01's non-goal targets.
- **D-08: An unresolved marker or missing file fails the strict build** — never a silently-empty block. Because `make docs --strict` joins always-on CI per D-IMPL-72, a deleted marker breaks the build in the same commit that deletes it.
- **D-09: Definition artifacts are literal-included by the same mechanism.** The No-Hardcoding Rule (§6.4) makes artifacts the adopter's primary authoring surface; pasted YAML would drift from the artifacts CI actually runs, reintroducing the defect the code rule prevents. **Planning detail to resolve:** JSON artifacts cannot carry comment markers — those need whole-file include or an extraction step.
- **D-10: Snippets are sourced from the existing `examples/00`–`07` suite plus `examples/external/`.** The install → ontology → agent → workflow → replay arc maps onto `00-quickstart`, `01-agent-basics`, `02-skilling`, `05-workflow-hitl`, `06-decision-replay`, with `examples/external/` supplying the consumer view. No ninth example is built or kept green — the adopter's guide is a narration layer over already-proven CI-run code.

**Schema, API, and OpenAPI reference generation**

- **D-11: The definition-artifact schema reference is generated at docs build from the Pydantic models** (mkdocs hook / `gen-files` step emitting JSON Schema rendered into reference pages). Cannot drift by construction — the same argument that makes the API reference generated rather than hand-written. Prose commentary lives in a hand-written page beside the generated output.
- **D-12: `openapi.json` is committed, regenerated from `create_app()` in CI, and drift-checked.** DOCS-05 says "drift check," which presupposes a stored baseline; it is also the HTTP contract external integrators consume, so endpoint changes should surface as reviewable diffs. This is a deliberate exception to D-11's generate-at-build posture, for those two reasons.
- **D-13: The API reference is curated by hand to the Protocols and public contracts** — storage, similarity, harness adapter, artifact store, orchestration, HITL, plus the Context Product contract, the six archetypes, and the Agent & Task Factory. mkdocstrings still generates every signature and docstring; only the *selection* of surfaces is curated. A full auto-generated module tree was rejected as burying the handful of Protocols an integrator needs and publishing internal helpers alongside the adopter surface.
- **D-14: mkdocstrings' own strict-mode failure catches renames and removals.** An unresolvable `::: ccf.…` identifier errors under `mkdocs build --strict` — the same single gate that catches snippet-marker drift (D-08), no extra tooling. A public-surface coverage lint (catching *undocumented additions*) was considered and not adopted for v0.

**Nav structure + doc placement**

- **D-15: Diátaxis top-level nav — Tutorial / How-to / Concepts / Reference.**
- **D-16: The five Common Pillars are a Concepts section, one page per pillar** — each embedding its existing Phase D diagram from `public/diagrams/` and linking down to the Reference surfaces that realize it.
- **D-17: Placement of the carried-over documents** — PERFORMANCE.md → **Reference**; security & deployment notes → **How-to**; narrated demo walkthrough → **Tutorial**, beside the adopter's guide.
- **D-18: The whitepaper cross-reference index shows section numbers and titles only, no quoted body text.** A table mapping each SDK surface to the whitepaper section that specifies it (e.g. `ContextProduct` → §6.3, §7.6).

### Claude's Discretion

None — every question in this discussion received an explicit ruling. Two items are flagged
above as planning-level detail rather than open decisions: the JSON-artifact include mechanism
(D-09) and the exact marker-string set the publish scan keys on (D-02/D-18).

### Deferred Ideas (OUT OF SCOPE)

- **Hosting the site.** Future D-IMPL under D-IMPL-71. `mike` versioning already declined.
- **A public-surface docs-coverage lint** (fails when a newly exported Protocol has no reference page) — considered under D-14, not adopted for v0.
- **A separate marker-inventory lint** for fast local feedback on snippet markers.
- **Gray areas raised but not discussed:** how-to guide inventory, whether the docs build is its own CI job, whether the top-level `README.md` becomes the site index. All planner-level calls.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOCS-01 | Adopter's guide — day-1-to-production narrative (install → ontology → agent → workflow → replay) | Snippet mechanism §"Pattern 1"; marker inventory §"Runtime State Inventory"; all example artifacts are **YAML** so `#` markers work everywhere (Finding F-3) |
| DOCS-02 | Generated Protocol/API reference from citation-bearing docstrings, whitepaper never published | Curated Protocol inventory §"D-13 surface inventory"; mkdocstrings strict verified (Finding F-2); publish scan design §"Pattern 4" + Finding F-6 (13 leaking docstrings) |
| DOCS-03 | Definition-artifact schema reference — the adopter's primary authoring API | `griffe_pydantic` with `schema: true` verified against pydantic 2.13.4 (Finding F-4); authoring-surface model paths §"D-11 model inventory" |
| DOCS-04 | How-to guides + concepts pages (pillars, invariants, replay anatomy, whitepaper cross-reference index) | Diagram inventory (11 `.mmd` files); snippet-into-mermaid-fence verified (Finding F-5); D-18 scan-compatibility validated (§ refs are not shingles) |
| DOCS-05 | Security & deployment notes + OpenAPI polish with drift check | `create_app` located; existing `app` fixture reusable; deterministic dump recipe §"Pattern 3" |
| DOCS-06 | `make docs --strict` in always-on CI; PERFORMANCE.md publishes measured baselines with methodology | Makefile/CI attach points §"Integration Points"; **OPEN QUESTION 1 — no committed baselines exist** |

## Project Constraints (from CLAUDE.md)

| Directive | Section | Consequence for this phase |
|-----------|---------|---------------------------|
| No-Hardcoding Rule — no prompt/agent/task/threshold literals in `src/`, `runtime/`, `examples/` | §6.4, §11 | Adding `# --8<-- [start:x]` **comments** to example sources is compliant (comments, not literals). CINV-01 lint scope is `("src", "runtime", "examples")` — `public/` and `tools/` are outside it. |
| Whitepaper fidelity; every public class docstring cites its whitepaper section | §11 | This is the *substance* mkdocstrings renders — but citing is `§7.6`-style references, **not** quoting body text. Finding F-6 shows 13 docstrings crossed that line. |
| Harness neutrality: zero harness imports in `/src` | §7.3, §11 | Unaffected. Docs deps go in a new `docs` extra, never core. |
| Makefile mirrors ci.yml command-for-command | Phase-8 D-10 | The docs CI job must invoke `make docs-strict`, not a bespoke command string. |
| `PYTHON := .venv/bin/python`, `PYTHONPATH=src:runtime` | Makefile header | The docs target follows the same shape. mkdocstrings `paths:` config makes PYTHONPATH redundant for the handler, but keep the env prefix for consistency. |
| Private repo, proprietary IP — the whitepaper must never be published | §2.2 | The reason D-01/D-02 exist. |
| Surface gaps as `D-IMPL-NN`, do not pick a default | §11, §15 | Open Question 1 (perf baselines) is likely a `D-IMPL` for Dave, not a planner call. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Markdown source of published pages | `public/` (new docroot) | — | D-01: default-deny by existence |
| Code/artifact snippet resolution | `pymdownx.snippets` preprocessor | `examples/` sources | Runs before fence parsing; sources stay the single artifact |
| API signature + docstring rendering | `mkdocstrings` + `mkdocstrings-python` handler | `src/`, `runtime/` | Generated, never hand-written (DOCS-02 non-goal) |
| Definition-artifact JSON Schema | `griffe_pydantic` Griffe extension | `src/ccf/**/definitions.py`, `catalog.py`, `artifacts.py` | Build-time derivation from the models themselves (D-11) |
| HTTP contract | committed `openapi.json` | `create_app()` + pytest drift check | Reviewable diffs; D-12's deliberate exception |
| Diagram rendering | `pymdownx.superfences` custom fence + Material JS | `public/diagrams/*.mmd` | D-04: no Node toolchain in CI |
| Publish safety | `tools/publish_scan.py` over `site/` | `docs/CCF_Whitepaper_1-2.md` (shingle source) | Post-build, on the exact artifact that uploads (D-02) |
| CI orchestration | `Makefile` `docs` / `docs-strict` targets | `.github/workflows/ci.yml` docs job | D-IMPL-72; Makefile mirrors CI |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mkdocs` | 1.6.1 | Site builder, `--strict` gate | Ruled by D-IMPL-71 [CITED: docs/DECISIONS.md] |
| `mkdocs-material` | 9.7.7 | Theme, Mermaid support, search | Ruled by D-IMPL-71; native Mermaid satisfies D-04 |
| `mkdocstrings` | 1.0.6 | Handler framework, `:::` directive | Ruled by D-IMPL-71; strict failure is D-14's whole gate |
| `mkdocstrings-python` | 2.0.5 | Python handler (Griffe-backed) | The `[python]` extra of the ruled dependency |
| `pymdown-extensions` | 11.0.1 | `snippets` (D-07/D-08/D-09), `superfences` (D-04) | Ships with Material; the ruled include mechanism |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `griffe-pydantic` | 1.3.1 | Renders Pydantic model fields + JSON Schema in mkdocstrings output | **Recommended for D-11** — replaces a hand-written gen-files hook entirely |
| `mkdocs-gen-files` | 0.6.1 | Programmatic page generation at build | Only if D-11 is implemented as a custom hook instead of `griffe-pydantic`. Recommend **not** adding it. |
| `mkdocs-literate-nav` | 0.6.3 | Nav from a Markdown file | **Not needed** — D-15's nav is curated and small; keep nav in `mkdocs.yml` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `griffe-pydantic` for D-11 | `mkdocs-gen-files` hook calling `model_json_schema()` + a Markdown renderer we write | Full control over presentation; but it is code we own, test, and keep in sync with Pydantic. `griffe-pydantic` is the maintained mkdocstrings-org extension and gives fields + config + collapsible schema for one config block. |
| `griffe-pydantic` | `json-schema-for-humans` (1.5.1) rendering standalone HTML | Prettier standalone schema docs; but it lands outside the mkdocstrings page model, needs its own gen step, and duplicates the docstrings the models already carry. |
| Committed `openapi.json` | Generate the spec at docs build | Rejected by D-12 (locked): a stored baseline is what "drift check" presupposes, and integrators want reviewable diffs. |
| Material's Mermaid (CDN JS) | `mkdocs-mermaid2` or pre-rendering with mermaid-cli | Rejected by D-04 (locked): no Node in the always-on CI docs job. |

**Installation** (new `docs` extra in `pyproject.toml`):

```toml
docs = [
  "mkdocs==1.6.1",
  "mkdocs-material==9.7.7",
  "mkdocstrings[python]==1.0.6",
  "mkdocstrings-python==2.0.5",
  "pymdown-extensions==11.0.1",
  "griffe-pydantic==1.3.1",
]
```

`dev` should compose it (`"ccf[docs]"`) so the existing `pip install -e ".[dev]"` step in all
three CI jobs picks it up with no workflow change beyond the new job.

**Version verification:** all versions above confirmed via `pip index versions` on 2026-08-03
and installed together successfully in a probe venv on Python 3.12. `mkdocstrings-python` 2.0.5
pulls `griffelib` 2.1.0 (Griffe's renamed distribution); `griffe-pydantic` 1.3.1 is compatible
with it and with the repo's pinned `pydantic==2.13.4` — verified by building a probe site
against a `ConfigDict(extra="forbid")` model.

## Package Legitimacy Audit

`slopcheck install mkdocs-material mkdocstrings mkdocstrings-python pymdown-extensions griffe-pydantic mkdocs mkdocs-gen-files` — run 2026-08-03.

| Package | Registry | slopcheck | Disposition |
|---------|----------|-----------|-------------|
| `mkdocs` | PyPI | [OK] | Approved [VERIFIED: PyPI + D-IMPL-71 ruling] |
| `mkdocs-material` | PyPI | [OK] | Approved [VERIFIED: PyPI + D-IMPL-71 ruling] |
| `mkdocstrings` | PyPI | [OK] | Approved [VERIFIED: PyPI + D-IMPL-71 ruling] |
| `mkdocstrings-python` | PyPI | [OK] | Approved [VERIFIED: PyPI, mkdocstrings org] |
| `pymdown-extensions` | PyPI | [OK] | Approved [VERIFIED: PyPI, Material dependency] |
| `griffe-pydantic` | PyPI | [OK] | Approved [VERIFIED: mkdocstrings.github.io/griffe-pydantic, github.com/mkdocstrings/griffe-pydantic] |
| `mkdocs-gen-files` | PyPI | [OK] | Approved but **not recommended** — see Alternatives |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none. `scanned 7 packages / 7 OK`.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────┐
  authoring         │  public/**.md   (D-01 docroot, default-deny) │
  surface           │  public/diagrams/*.mmd                       │
                    └───────┬───────────────────┬─────────────────┘
                            │                   │
              --8<-- includes            ::: identifiers
                            │                   │
        ┌───────────────────▼──────┐   ┌────────▼───────────────────┐
        │ pymdownx.snippets        │   │ mkdocstrings + python      │
        │ base_path ["."]          │   │ paths ["src","runtime"]    │
        │ check_paths TRUE  ◄─D-08 │   │ griffe_pydantic schema:true│
        │ restrict_base_path TRUE  │   │       ◄─ D-11, D-13, D-14  │
        └───┬──────────────────┬───┘   └────────┬───────────────────┘
            │                  │                │
   examples/**/run.py   examples/**/artifacts/*.yaml   src/, runtime/ docstrings
   (marker comments)    (whole-file or marker)         (whitepaper §-citations)
            │                  │                │
            └──────────────────┴────────┬───────┘
                                        ▼
                          ┌──────────────────────────┐
                          │  mkdocs build --strict   │  ← ONE gate, 3 failure classes
                          │  validation.* = warn     │    (missing marker, dead ident,
                          └────────────┬─────────────┘     broken link/anchor)
                                       ▼
                            site/  (gitignored)
                                       │
              ┌────────────────────────┼─────────────────────────┐
              ▼                        ▼                         ▼
   tools/publish_scan.py     actions/upload-artifact     (nothing hosted — D-IMPL-71)
   shingles(whitepaper)             (D-05)
   ∩ text(site/**) == ∅
        │  FAIL on any hit  ◄── D-02
        ▼
   docs/CCF_Whitepaper_1-2.md   ← read ONLY by the scanner; never by mkdocs
```

Separately, outside the mkdocs graph:

```
runtime/ccf_runtime/http_api/app.py::create_app
        │
        ├─► tests/http_api/conftest.py::app fixture ──► app.openapi()
        │                                                    │
        │                          json.dumps(sort_keys, indent=2)
        │                                                    ▼
        └────────────────── compare ────────────────► openapi.json (committed)
                             FAIL on diff  ◄── D-12   (also included into a public/ page)
```

### Recommended Project Structure

```
public/                          # D-01 docroot — the ONLY tree mkdocs reads
├── README.md                    # D-06 publish-boundary charter (not in nav)
├── index.md                     # site landing page
├── tutorial/                    # D-15 Diátaxis
│   ├── adopters-guide.md        # DOCS-01 (install→ontology→agent→workflow→replay)
│   └── demo-walkthrough.md      # git mv from docs/ (D-03, D-17)
├── how-to/
│   ├── security-and-deployment.md   # git mv from docs/security-notes.md (D-03, D-17)
│   └── <task pages>             # DOCS-04
├── concepts/
│   ├── pillars/{data-context,orchestration,agent-types,hitl,experience}.md  # D-16
│   ├── invariants.md
│   ├── replay-anatomy.md
│   └── whitepaper-index.md      # D-18 — § numbers + titles ONLY
├── reference/
│   ├── protocols/*.md           # D-13 curated ::: pages
│   ├── artifacts/*.md           # D-11 (griffe_pydantic renders schema)
│   ├── http-api.md              # includes openapi.json
│   └── performance.md           # DOCS-06 (D-17)
└── diagrams/*.mmd               # git mv from docs/diagrams/ (D-03)
mkdocs.yml                       # repo root — cwd for base_path resolution
openapi.json                     # repo root, committed (D-12)
tools/publish_scan.py            # D-02 scanner (tools/ is outside CINV lint scope)
site/                            # build output — MUST be added to .gitignore
```

### Pattern 1: Marker-anchored snippet include (D-07/D-08)

**What:** A named region in an example source, included by name.
**When to use:** Every code snippet in every published page. No exceptions (DOCS-01 non-goal).

In `examples/00-quickstart/run.py`:
```python
    # --8<-- [start:assemble]
    handle.worker.ingest(events)
    view = handle.reader.view(boundary=boundary)
    # --8<-- [end:assemble]
```

In `public/tutorial/adopters-guide.md`:
````markdown
```python
--8<-- "examples/00-quickstart/run.py:assemble"
```
````

Verified behaviour (probe, pymdown-extensions 11.0.1):
- Marker comment lines are **omitted** from the output.
- With `dedent_subsections: true`, the common leading indentation is stripped — a region inside
  a function body renders flush-left. Without it, a 4-space-indented region renders indented
  inside the fence. **Set it.**
- Snippets is a *preprocessor*, so it runs before superfences parses the fence — the directive
  works inside ```` ```python ```` and ```` ```mermaid ```` fences alike (both verified).

### Pattern 2: mkdocstrings curated reference page (D-13/D-14)

```markdown
# Graph storage

::: ccf.graph.protocols.GraphReader
::: ccf.graph.protocols.GraphWriter
```

Handler config resolves the src-layout without PYTHONPATH:

```yaml
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: ["src", "runtime"]
          options:
            show_source: false
            members_order: source
            separate_signature: true
            show_signature_annotations: true
            extensions:
              - griffe_pydantic:
                  schema: true
```

`show_source: false` is a **publish-safety recommendation**, not just aesthetics: source
rendering would put whole module bodies (including comments, which the scan also reads) on the
published page, widening the leak surface well beyond docstrings.

### Pattern 3: Deterministic OpenAPI dump + drift check (D-12)

`create_app` is at `runtime/ccf_runtime/http_api/app.py:150` and takes a frozen kw-only
`ApiDependencies` dataclass (`runtime/ccf_runtime/http_api/dependencies.py:44`). Routers are
mounted unconditionally, so the emitted schema is **independent of the injected handles** —
but building a valid `ApiDependencies` is still simplest via the existing fixture.

`tests/http_api/conftest.py` already provides an `app` fixture (line 352) over a `fabric`
fixture, and `tests/http_api/test_openapi.py` already calls `app.openapi()`. Recommendation:

- **Regeneration:** a `tools/dump_openapi.py` (or a `make openapi` target) that constructs the
  app and writes `json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"`.
- **Drift check:** a new test in the existing `tests/http_api/test_openapi.py` asserting the
  committed file equals the freshly serialized spec, with the failure message naming the
  regeneration command. This puts the check in the **already-always-on `test` job** — no new
  CI wiring, and it fails on the same commit that changes an endpoint.
- **Determinism levers:** `sort_keys=True` removes dict-ordering sensitivity; `fastapi==0.140.0`
  and `pydantic==2.13.4` are already exact pins, so the `components.schemas` shapes are fixed.
  A FastAPI bump will move the spec — that is a *desirable*, reviewable diff, and the failure
  message should say so.
- **Publishing:** `public/reference/http-api.md` whole-file-includes `openapi.json` inside a
  ```` ```json ```` fence, so the published contract is the committed one by construction.

### Pattern 4: Publish-safety shingle scan (D-02)

Prototyped and validated on real repo content:

```python
# tools/publish_scan.py (sketch)
WP = Path("docs/CCF_Whitepaper_1-2.md")
N = 10
def norm(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
words = norm(re.sub(r"`[^`]*`", " ", WP.read_text()))     # strip code spans
shingles = {" ".join(words[i:i+N]) for i in range(len(words)-N)}
# for each file under site/: strip HTML tags -> norm -> slide window -> intersect
```

Measured on this repo, 2026-08-03:

| Input | 10-word shingle hits | Interpretation |
|-------|---------------------|----------------|
| `docs/CCF_Whitepaper_1-2.md` | (source) | 107,712 shingles, built in 0.04 s |
| `docs/DESIGN.md` | **60** | positive control — internal derived doc correctly trips |
| `docs/security-notes.md` | **0** | negative control — D-03 move is clean |
| `docs/demo-walkthrough.md` | **0** | negative control — D-03 move is clean |
| all `src/` + `runtime/` docstrings | **13 docstrings** | see Finding F-6 — real leak, must be fixed |

**Shingle-length sensitivity** (why N=10):

| N | docstrings tripping | `DESIGN.md` positive-control hits |
|---|--------------------|-----------------------------------|
| 8 | 22 | 146 |
| 10 | 13 | 60 |
| 14 | 8 | 7 |
| 20 | 2 | **0 — control fails** |

N=20 makes the gate useless (the positive control stops firing). N=8 is noisy. **N=10 is the
recommendation**: strong positive control, and its 13 hits are all genuine verbatim quotes.

**D-18 compatibility confirmed:** `§7.6`-style references are single tokens; the normalizer
drops `§` and a section number cannot form a 10-word body-text shingle. A cross-reference table
of section numbers and titles cannot trip the scan. (`D-IMPL-NN` identifiers likewise — but see
Open Question 3 on whether D-IMPL numbers should be published at all.)

Additional scan components beyond shingles:
- **Path/filename denylist** on the built tree: any occurrence of the literal strings
  `CCF_Whitepaper`, `SPEC_INVENTORY`, `PHASE_I`, `09-ruling-batch-minicycle`, `.planning/`,
  and any `Fig-CH\d\d-\d\d` figure name.
- **Symlink guard, pre-build:** fail if any path under `public/` is a symlink. mkdocs copies
  file *content*, so `public/x.md -> ../docs/CCF_Whitepaper_1-2.md` would publish the whitepaper
  outright. The shingle scan catches it post-hoc; the guard catches it earlier and more legibly.
- **Self-test:** run the scanner against the whitepaper itself and assert it fires. A scanner
  that silently stops matching (e.g. after a whitepaper re-format) is worse than no scanner.

### Anti-Patterns to Avoid

- **`check_paths` left at its default `False`.** This is the single most dangerous default in
  the phase. Verified: with `check_paths: false`, both a missing file *and* a missing named
  section build clean at exit 0 with an empty block. D-08 is `check_paths: true` and nothing else.
- **`base_path` pointing at the docroot with `../` traversal enabled.** `restrict_base_path`
  defaults to `True` and blocks `../` escapes (verified: `--8<-- "../secret/wp.md"` errored and
  produced no output). Do not turn it off.
- **Rendering source with `show_source: true`** in the API reference — publishes full module
  bodies, widening the D-02 surface.
- **Adding a symlink under `public/`** to avoid duplicating a file. That is precisely the escape
  path D-01/D-03 exist to close.
- **Line-range includes** — locked out by D-07.
- **Allowlisting the 13 leaking docstrings** instead of rewording them. That converts a
  structural gate into a maintained exception list, which is what D-02 was chosen over.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rendering Pydantic models as schema docs | A `gen-files` hook calling `model_json_schema()` + a Markdown emitter | `griffe_pydantic` extension, `schema: true` | Verified to emit collapsible JSON Schema + `Config: extra: forbid` + per-field types and descriptions, for one YAML block. A hand-rolled renderer is code to test and to keep in sync with Pydantic's schema output. |
| Checking snippet markers resolve | A marker-inventory lint | `pymdownx.snippets` `check_paths: true` under the strict build | Explicitly deferred in CONTEXT; the extension already raises `SnippetMissingError`. |
| Detecting renamed/removed Protocols | A public-surface diff lint | mkdocstrings' collection error | D-14 (locked). Verified: `ERROR - Could not collect 'mypkg.DoesNotExist'` → `Aborted with a BuildError!`, exit 1. |
| Broken internal links/anchors | A link checker | mkdocs `validation:` + `--strict` | Built in; just needs the levels raised (see Pitfall 3). |
| Rendering Mermaid to SVG | mermaid-cli / a Node step | Material's `superfences` custom fence | D-04 (locked); verified `<pre class="mermaid">` output and CDN JS load. |
| An OpenAPI dump harness | A standalone app-construction script duplicating fixture wiring | The existing `tests/http_api/conftest.py::app` fixture | It already exists and already runs in always-on CI. |

**Key insight:** this phase's entire value proposition is *"the tool fails instead of the human
noticing."* Every hand-rolled checker is a checker that can itself drift. The single strict build
plus one content scan is the whole enforcement story.

## Common Pitfalls

### Pitfall 1: `check_paths` default silently disables D-08

**What goes wrong:** Someone deletes a `[start:assemble]` marker; the docs build stays green;
the page ships an empty code fence.
**Why it happens:** `pymdownx.snippets` raises `SnippetMissingError` from `extract_section` only
under `if not found and self.check_paths:` (source line ~154), and from `parse_snippets` only
under `elif self.check_paths:` (line ~406). `--strict` cannot help — no warning is emitted.
**How to avoid:** `check_paths: true`. **Verify it in the plan** with a negative test (see
Validation Architecture).
**Warning signs:** an empty ```` ``` ```` block in the rendered HTML.

### Pitfall 2: `base_path` resolves against the process CWD, not `mkdocs.yml`

**What goes wrong:** Include paths that work locally break in CI, or vice versa.
**Why it happens:** verified in probe — running `mkdocs build -f site_src/mkdocs.yml` from
`/tmp/docsprobe` with `base_path: [".."]` resolved to `/tmp`, not to `site_src/..`.
**How to avoid:** `mkdocs.yml` at repo root, `base_path: ["."]`, and the Makefile target runs
from the repo root (which it does — `make` runs in the Makefile's directory). This also makes
the repo-root-relative paths already in `docs/demo-walkthrough.md`
(`--8<-- "examples/08-e2e-demo/artifacts/scenario.yaml"`) resolve unchanged after the D-03 move —
exactly what that file's HTML header comment anticipated.
**Warning signs:** `SnippetMissingError: Snippet at path 'examples/...' could not be found`.

### Pitfall 3: mkdocs link validation defaults are `info`, so `--strict` ignores them

**What goes wrong:** the "one strict build catches broken internal links" claim in CONTEXT
§specifics does not hold out of the box.
**Why it happens:** in `mkdocs/config/defaults.py`, `links.absolute_links`,
`links.unrecognized_links`, and `links.anchors` all default to `info`. `--strict` only promotes
**WARNING** to error.
**How to avoid:** set them explicitly:
```yaml
validation:
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn
  nav:
    omitted_files: warn
    not_found: warn
```
**Warning signs:** a build that passes with an obviously dead `[link](nope.md)`.

### Pitfall 4: `base_path: ["."]` leaves `docs/` reachable by snippets

**What goes wrong:** D-01 claims `docs/` is *structurally* unreachable; with `base_path: ["."]`
at repo root, `--8<-- "docs/CCF_Whitepaper_1-2.md"` resolves fine. `restrict_base_path` only
blocks escapes *above* the base path, not siblings *below* it.
**Why it happens:** the include paths this repo needs (`examples/...`, `perf/...`) force a
repo-root base path.
**How to avoid:** two options for the planner —
 (a) accept it and rely on the D-02 scan (the ruling's stated position: "the scan proves it on
 the artifact that ships"), or
 (b) narrow `base_path: ["examples", "public", "perf", "."]`-style to an explicit allowlist that
 omits `docs/` — but the trailing `"."` re-opens it, so a true structural block requires dropping
 `"."` and rewriting every include path to be relative to one of the listed roots (which would
 mean editing the existing `docs/demo-walkthrough.md` include paths).
**Recommendation:** (a) plus a `tools/publish_scan.py` pre-build check that no `.md` under
`public/` contains a `--8<--` directive whose path starts with `docs/` or `.planning/`. That is
three lines of regex and gives the structural claim without rewriting include paths.
**Warning signs:** none — this fails open by design.

### Pitfall 5: mermaid.js loads from a CDN at *view* time

**What goes wrong:** someone downloads the Actions artifact (D-05), opens it offline, and the
diagrams are blank.
**Why it happens:** verified — Material's JS bundle references
`https://unpkg.com/mermaid@11/dist/mermaid.min.js` and loads it lazily in the browser.
**Impact on CI:** none. The *build* is fully offline and deterministic, satisfying the always-on
CI determinism constraint. Only viewing needs network.
**How to avoid:** note it in `public/README.md`. Do not solve it (that would mean vendoring JS
or adding a Node step, both against D-04).

### Pitfall 6: `site/` is not gitignored

**What goes wrong:** a local `make docs` run commits a copy of the whole rendered site,
including anything the scan would have caught, straight into the repo.
**How to avoid:** add `site/` to `.gitignore` in the same plan that adds the `docs` target.
Verified absent from the current `.gitignore`.

### Pitfall 7: MkDocs 2.0 is announced as backward-incompatible

**What goes wrong:** an unpinned `mkdocs` resolves to 2.x and every plugin stops working.
**Why it happens:** mkdocs-material 9.7.7 prints a loud build-time banner:
*"MkDocs 2.0 … will introduce backward-incompatible changes … All plugins will stop working …
No migration path exists"* (squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/).
**How to avoid:** exact-pin `mkdocs==1.6.1` in the `docs` extra, consistent with this repo's
existing exact-pin discipline. Also expect this banner in every CI docs-job log — do not mistake
it for a build error (it is printed in red and the build exits 0).

## Code Examples

### Complete `mkdocs.yml` skeleton (repo root)

```yaml
site_name: CCF SDK
site_description: Cognitive Context Fabric SDK — governed, typed, replay-ready context
docs_dir: public
site_dir: site
strict: true          # belt-and-braces; `make docs-strict` also passes --strict

theme:
  name: material
  features:
    - navigation.sections
    - content.code.copy

validation:                     # Pitfall 3 — defaults are `info`, invisible to --strict
  omitted_files: warn
  absolute_links: warn
  unrecognized_links: warn
  anchors: warn
  nav:
    omitted_files: warn
    not_found: warn

plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: ["src", "runtime"]
          options:
            show_source: false
            separate_signature: true
            show_signature_annotations: true
            members_order: source
            extensions:
              - griffe_pydantic:
                  schema: true

markdown_extensions:
  - admonition
  - toc: {permalink: true}
  - pymdownx.snippets:
      base_path: ["."]          # resolves against CWD == repo root (Pitfall 2)
      check_paths: true         # D-08 — NOT optional (Pitfall 1)
      restrict_base_path: true  # default; blocks ../ escapes (verified)
      dedent_subsections: true  # flush-left regions from inside function bodies
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.highlight
  - pymdownx.inlinehilite

nav:
  - Home: index.md
  - Tutorial:
      - Adopter's guide: tutorial/adopters-guide.md
      - How data folds into context: tutorial/demo-walkthrough.md
  - How-to:
      - Security & deployment: how-to/security-and-deployment.md
  - Concepts:
      - Pillars: [concepts/pillars/*.md]
      - Invariants: concepts/invariants.md
      - Replay anatomy: concepts/replay-anatomy.md
      - Whitepaper cross-reference: concepts/whitepaper-index.md
  - Reference:
      - Protocols: [reference/protocols/*.md]
      - Definition artifacts: [reference/artifacts/*.md]
      - HTTP API: reference/http-api.md
      - Performance: reference/performance.md
```

Note: `public/README.md` is not in `nav`. With `validation.nav.omitted_files: warn` under
`--strict` that becomes an error, so it must be silenced with `not_in_nav: |` :

```yaml
not_in_nav: |
  README.md
```

### Diagram page (D-04 + D-16), verified working

````markdown
# The Data and Context Layer

```mermaid
--8<-- "public/diagrams/pillar-data-context.mmd"
```
````

Verified output: `<pre class="mermaid"><code>graph TD; …</code></pre>` — Material's JS picks it
up. The `.mmd` remains the single artifact (D-04).

### Makefile targets (D-IMPL-72 wiring)

```make
docs: ## Build the site into site/ (D-IMPL-71 — built, never hosted)
	$(ENV) $(PYTHON) -m mkdocs build

docs-strict: ## Strict build + publish-safety scan — the always-on gate (D-IMPL-72, D-02)
	$(ENV) $(PYTHON) -m mkdocs build --strict
	$(ENV) $(PYTHON) tools/publish_scan.py site

docs-serve: ## Local live-reload preview (never CI)
	$(ENV) $(PYTHON) -m mkdocs serve
```

and the D-IMPL-72 composition change, exactly as pre-authorized:

```make
ci: ci-core examples docs-strict ## Full local reproduction of the always-on pipeline (D-10, amended D-IMPL-72)
```

`.PHONY` must gain `docs docs-strict docs-serve`.

## D-13 surface inventory (real module paths, verified present)

Every path below was confirmed by grep on 2026-08-03. All are `Protocol` classes or public
contracts and all carry docstrings; spot-checks confirmed whitepaper/CLAUDE.md citations
(`ArtifactStoreProtocol` cites §7.4; `HarnessAdapterProtocol` cites §7.3).

**Storage / graph**
- `ccf.graph.protocols.GraphReader` (`src/ccf/graph/protocols.py:155`)
- `ccf.graph.protocols.GraphWriter` (`:191`) — the single-writer surface
- `ccf.controlplane.state.ControlPlaneStateStore` (`src/ccf/controlplane/state.py:136`)
- `ccf.controlplane.registry.ControlPlaneProtocol` (`src/ccf/controlplane/registry.py:154`)

**Similarity / embedding**
- `ccf.similarity.protocol.SimilarityIndexProtocol` (`src/ccf/similarity/protocol.py:87`)
- `ccf.similarity.protocol.MutableSimilarityIndexProtocol` (`:114`)
- `ccf.similarity.embedder.EmbedderProtocol` (`src/ccf/similarity/embedder.py:41`)

**Operators / projection**
- `ccf.operators.base.Operator` (`src/ccf/operators/base.py:119`)
- `ccf.projection.plan.ProjectionPlan` (`src/ccf/projection/plan.py:77`)
- `ccf.projection.acquisition.ContentAcquirer` (`:154`), `ContentAcquiringPlan` (`:182`)

**Context Product contract (DOCS-02 core)**
- `ccf.contracts.base.CCFContract` (`src/ccf/contracts/base.py:36`)
- `ccf.products.contract.ContextProductContract` (`src/ccf/products/contract.py:138`)
- `ccf.products.contract.ProductLineage` (`:118`), `RegisteredProductClass` (`:96`), `MaxTTL` (`:81`)
- `ccf.products.gates` — the three validation gates

**Harness adapter (§7.3 seam)**
- `ccf.harness.protocol.HarnessAdapterProtocol` (`src/ccf/harness/protocol.py:171`)

**Artifact store (§7.4 seam)**
- `ccf.artifacts.protocol.ArtifactStoreProtocol` (`src/ccf/artifacts/protocol.py:189`)
- reference impls: `ccf.artifacts.file_store.FileArtifactStore`, `ccf.artifacts.mcp_store`

**Orchestration**
- `ccf.orchestration.protocol.OrchestrationProtocol` (`src/ccf/orchestration/protocol.py:67`)
- `ccf.workflow.factory.WorkflowFactory`, `ccf.workflow.definitions.WorkflowDefinition`

**HITL**
- `ccf.hitl.transport.HITLTransportProtocol` (`src/ccf/hitl/transport.py:344`)
- `ccf.hitl.webhook.WebhookDeliveryProtocol` (`src/ccf/hitl/webhook.py:96`)
- `ccf.hitl.approval_gate`, `escalation`, `override`, `review_queue`, `principal`

**Agents: six archetypes + factory**
- `ccf.agents.archetypes` (`src/ccf/agents/archetypes.py`; `ArchetypeComponent` Protocol at `:96`)
- `ccf.agents.factory` — the Agent & Task Factory (§6.4)
- `ccf.agents.agent`, `ccf.agents.composition`, `ccf.agents.prompts`, `ccf.agents.errors`

**Peering / A2A**
- `ccf.peering.protocol.PeeringProtocol` (`src/ccf/peering/protocol.py:175`)
- `ccf.peering.identity.IdentityProvider` (`:314`), `SigningKeySource` (`:283`)

**Half-life / debt**
- `ccf.halflife.decay.Observation`, `effective_half_life`; `ccf.halflife.debt.context_debt`,
  `DebtFactors`, `DebtSignal`, `DebtFactorScorerProtocol` (`src/ccf/halflife/debt.py:170`)
  — **all of these are in the F-6 leak set; reword before publishing.**

**Runtime-side (Experience Layer, arguably in scope for D-13)**
- `ccf_runtime.mcp.experience.*Protocol` (six Protocols, `runtime/ccf_runtime/mcp/experience.py`)
- `ccf_runtime.http_api.auth.HttpAuthProtocol`, `ccf_runtime.authz.protocol.TenantAuthorizerProtocol`
- `ccf_runtime.workflow.engine.{SkillNodeBinding,AgentNodeBinding,DebtAssessmentBinding}`
- `ccf_runtime.adapters.{adk,claude_agent,langgraph}` — the three reference adapters

**Deliberately excluded** (private/internal — the reason D-13 curates): `ccf.boot._Backend`,
`ccf.graph._writer._Store`/`_Txn`, `ccf.graph.reader.Row`.

## D-11 model inventory (the adopter's authoring surface)

The definition-artifact surface, all subclasses of `CCFContract`
(`extra=forbid`) and therefore all rendered by `griffe_pydantic`:

| Artifact class | Module | Models |
|----------------|--------|--------|
| Agent definitions | `src/ccf/agents/definitions.py` | `AgentDefinition` (:200), `ContextContract` (:130), `ConsumedProduct` (:113), `PerspectiveBinding` (:151), `InstructionBinding` (:180), `VersionedRef` (:164) |
| Task definitions | `src/ccf/agents/definitions.py` | `TaskDefinition` (:288), `TaskStep` (:242) |
| Prompt artifacts | `src/ccf/agents/definitions.py` | `PromptArtifact` (:314) |
| Workflow definitions | `src/ccf/workflow/definitions.py` | `WorkflowDefinition` (:112), `WorkflowTransition` (:80) |
| Skill catalog | `src/ccf/skills/catalog.py` | `SkillCatalogEntry` (:281), `SkillRequirements` (:260), `SkillArgumentSchema` (:209), `SkillArgumentProperty` (:194), and the five binding types `LocalCallableBinding` (:109), `ToolBinding` (:128), `McpBinding` (:138), `PeeringBinding` (:149), `ProcedureBinding` (:165) |
| Skill grants | `src/ccf/skills/grants.py` | `SkillGrant` (:172), `PolicyRegimeGovernance` (:235), `GrantStateRecord` (:215) |
| Control Plane artifacts | `src/ccf/controlplane/artifacts.py` | `DeclaredArtifact` (:145), `HalfLifeTable` (:202), `HalfLifeEntry` (:169), `DebtProfile` (:216) |
| Product registration | `src/ccf/products/contract.py` | `RegisteredProductClass` (:96), `MaxTTL` (:81) |

Note the shared private base `_TwoLaneVersioned` appears in three modules (agents, workflow,
controlplane) — private, so keep it out of the reference and let `griffe_pydantic` inline the
inherited fields.

**Verified rendering** (probe, `pydantic==2.13.4`): for a `ConfigDict(extra="forbid")` model,
`griffe_pydantic` with `schema: true` emits a collapsible *"Show JSON schema"* block containing
the exact `model_json_schema()` output (`"additionalProperties": false`, per-field
`description`/`default`/`type`, `required`), plus a `Config: extra: forbid` line and a
per-field list with types and docstrings. That is DOCS-03's entire deliverable, generated.

## D-09 resolution: the JSON-artifact problem largely does not exist

**Finding F-3.** Every definition artifact in the example suite is **YAML**, not JSON:

```
examples/**/artifacts/*.yaml   : 65 files
examples/**/*.json             : 13 files — ALL of them non-artifact
```

The 13 JSON files are: 12 model-API replay fixtures under
`examples/external/00-hello-context/fixtures/` (captured Anthropic/Gemini wire traffic, EXAM-05)
and `examples/external/00-hello-context/.store/.artifact-names.json` (gitignored runtime output).
Neither is "the adopter's primary authoring surface" that D-09 is about. YAML carries `#`
comments, so the D-07 marker mechanism works unchanged on every real artifact.

**Recommendation for the planner:**
1. **Artifacts (YAML):** prefer **whole-file include** — `--8<-- "examples/01-agent-basics/artifacts/agent.yaml"`.
   An artifact is short and is meant to be read entire; a partial artifact teaches the wrong
   thing (an adopter needs to see every required key). This is also exactly what the existing
   `docs/demo-walkthrough.md` already does for all 8 of its artifact includes. Use named markers
   only where an artifact is long enough that a section is genuinely clearer.
2. **Example code (`run.py`, `client_*.py`):** named markers per D-07, since those files are
   long and narration wants specific stages.
3. **The one JSON file that *will* be included — `openapi.json`:** whole-file include (D-12
   makes it a committed baseline, and a partial API spec is meaningless).
4. **If a future JSON artifact needs a slice:** do *not* build a jq/gen-files extraction step.
   The precedent to set is "artifacts are included whole." Record this as the resolution of
   D-09's flagged planning detail.

## Runtime State Inventory

This phase includes a `git mv` (D-03), so the rename discipline applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified. The docs suite reads the repo tree and writes `site/`; no database, no collection names, no user_ids. | none |
| Live service config | None — verified. D-IMPL-71 rules nothing is hosted; there is no Pages site, no CDN, no external docs service holding a path. The only external reference is the runtime unpkg mermaid CDN URL, which is inside Material's bundle and carries no CCF identifier. | none |
| OS-registered state | None — verified. No scheduled task, service, or daemon references `docs/`. | none |
| Secrets/env vars | None — verified by grep. The docs build consumes no secret; `CCF_PERF_RUNNER_CLASS` is perf-only and untouched. | none |
| Build artifacts | `site/` is a NEW build output and is **not** in `.gitignore` — must be added. `ccf.egg-info/` already ignored. Adding a `docs` extra means every existing CI job's `pip install -e ".[dev]"` picks up the new deps only if `dev` composes `ccf[docs]`. | add `site/` to `.gitignore`; wire the extra |

**Inbound references to the three D-03-moved paths** (grep, excluding `.git/` and `.planning/`):

| Reference | File:line | Fix |
|-----------|-----------|-----|
| `docs/diagrams/` link | `README.md:85` | repoint to `public/diagrams/` |
| `docs/diagrams` (×8 rows in the pillar/seam mapping table + prose) | `docs/DESIGN.md:26–31, 37, 202` | repoint to `public/diagrams/` |
| `/docs/diagrams` in the skeleton listing and Phase D deliverable spec | `CLAUDE.md:162, 1227, 1248` | **CLAUDE.md edit — requires Dave.** See Open Question 2. |
| `docs/demo-walkthrough.md` link at the end of the example-08 README | `examples/08-e2e-demo/README.md` (per `13-RESEARCH.md:120`) | repoint to `public/tutorial/demo-walkthrough.md` |
| `docs/demo-walkthrough.md` in phase records | `.planning/**` (historical) | leave — historical record |

`docs/security-notes.md` has **no** inbound references outside `.planning/` — clean move.
`docs/figures/` (27 whitepaper figure PNGs) stays in `docs/` and must never move.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | everything | ✓ | 3.12 | — |
| pip / PyPI network | docs extra install | ✓ | — | — |
| `.venv` at repo root | every Makefile target | ✓ (Makefile assumes it; CI provisions it in the examples job) | — | the new docs CI job must provision `.venv` the same way (see Integration Points) |
| Node / mermaid-cli | — | ✗ | — | **not needed** — D-04 uses Material's browser-side rendering |
| `mkdocs` et al. | docs build | ✗ (not yet in `pyproject.toml`) | — | this phase adds the `docs` extra |
| `git` | D-03 `git mv` | ✓ | — | — |
| Internet at *view* time | Mermaid rendering in the downloaded artifact | n/a | — | none; document the caveat in `public/README.md` |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none blocking.

## Integration Points (verified against the real files)

**`Makefile`** — `PYTHON := .venv/bin/python`, `ENV := PYTHONPATH=src:runtime`. Add
`docs docs-strict docs-serve` to `.PHONY` (line ~19) and amend line
`ci: ci-core examples` → `ci: ci-core examples docs-strict` (D-IMPL-72; the comment block above
it should cross-reference the amendment, not edit the Phase-8 D-10 text).

**`.github/workflows/ci.yml`** — three existing jobs: `lint`, `test` (matrix + Postgres
service), `examples` (timeout 20 min). All three run `python -m pip install -e ".[dev]"`. The
`examples` job additionally provisions `.venv` explicitly (lines near the end) *because the
Makefile targets use `.venv/bin/python`* — the docs job must do the same:

```yaml
  docs:
    name: docs (strict build + publish scan)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12", cache: pip}
      - name: Install package with dev extras
        run: python -m pip install -e ".[dev]"
      - name: Provision .venv for the Makefile command surface
        run: python -m venv .venv && .venv/bin/pip install -e ".[dev]"
      - name: make docs-strict
        run: make docs-strict
      - uses: actions/upload-artifact@v4      # D-05
        with: {name: ccf-docs-site, path: site/}
```

Recommend a **separate job** (not folded into `lint`) — it is the CONTEXT "gray area", and a
separate job gives an independently readable red/green signal plus a clean artifact-upload
attach point. `perf.yml` and `live-legs.yml` are untouched.

**`pyproject.toml`** — add `[project.optional-dependencies] docs = [...]` and add `"ccf[docs]"`
to `dev`. `[tool.mypy] files = ["src", "runtime"]` is authoritative and **excludes `tools/`**,
so `tools/publish_scan.py` and `tools/dump_openapi.py` are not type-checked — consistent with
the existing `tools/lints/` package, which is also outside the mypy surface but *is* unit-tested
(`pytest tools/lints/tests -q` runs in the `lint` job). Mirror that: put tests for the scanner
under `tools/publish_scan_tests/` (or extend the lint job's step) so the gate itself is tested.

**`tools/lints/__main__.py`** — `LINTED_TREES = ("src", "runtime", "examples")`; `public/` is
outside all four rules. Adding marker comments to `examples/` sources touches the CINV-01
no-hardcoding tree, but comments are not string literals, so no lint impact expected. Confirm
in the plan by running `make lint` after the marker pass.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mkdocstrings` 0.x with a separate `griffe` distribution | `mkdocstrings` 1.0.6 + `mkdocstrings-python` 2.0.5 + `griffelib` 2.1.0 | 2026 (1.0 line) | The distribution rename to `griffelib` is the notable change; `griffe-pydantic` 1.3.1 is compatible — verified by building. |
| Hand-written Pydantic field tables | `griffe-pydantic` extension | matured 2024→2026 | Removes the D-11 hook entirely |
| MkDocs 1.x plugin ecosystem | MkDocs 2.0 announced as a breaking rewrite with **no migration path** | announced 2026-02-18 | Exact-pin `mkdocs==1.6.1`. Material prints this warning on every build. |

**Deprecated/outdated:** `mkdocs-mermaid2` — superseded by Material's native superfences
integration for the common case (and ruled out by D-04 anyway).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Every one of the 13 F-6 docstrings can be reworded without losing whitepaper-fidelity meaning (CLAUDE.md §11 requires citation, not quotation) | Finding F-6 | If rewording weakens fidelity, the alternative is a reviewed allowlist, which softens D-02 |
| A2 | `griffe-pydantic` renders every model in the D-11 inventory as cleanly as the probe model (which was a simple two-field `extra=forbid` model) | D-11 inventory | Complex models (discriminated unions in `SkillCatalogEntry`'s five binding types, `_TwoLaneVersioned` inheritance) may render awkwardly — verify on a real model in Wave 0 |
| A3 | The docs CI job's runtime stays well inside the always-on budget | Integration Points | Low risk: the probe builds completed in 0.04–0.23 s; a real build with ~40 mkdocstrings pages is seconds, not minutes |
| A4 | `openapi.json` is byte-stable across repeated runs on the same pins | Pattern 3 | If FastAPI introduces set-derived ordering anywhere, the drift test flakes; mitigate by asserting on the parsed dict, not the bytes, if it does |
| A5 | `not_in_nav: "README.md"` correctly silences the D-06 charter under strict validation | mkdocs.yml skeleton | Verify in Wave 0; the alternative is `exclude_docs` |

## Open Questions

1. **PERFORMANCE.md has no measured numbers to publish.** `git ls-files perf/baselines` returns
   only `.gitkeep`; `perf/results/` is gitignored (`.gitignore`: "Perf battery run outputs are
   never committed (Phase 11 D-02); baselines are"). `perf/README.md` §"Phase 14 pointer" says
   the curve artifacts "land in `perf/results/replay.curve.json`" — a gitignored path. The only
   committed measured numbers in the repo are the wall-time table in `perf/README.md` §"Budget
   (D-17 / D-25)" (measured 2026-08-02, runner class `local`).
   - What we know: DOCS-06 requires "PERFORMANCE.md publishes measured baselines with
     methodology and environment manifest." The methodology and the re-baseline ritual are fully
     written in `perf/README.md`. `perf/gate.py` writes a `sort_keys=True` results JSON.
   - What's unclear: **committing a baseline is a Dave-gated act under D-IMPL-70** ("re-baselining
     is a deliberate, Dave-approved act recorded in the decision/baselines log"). Phase 14 cannot
     unilaterally run `make perf` and commit `perf/baselines/local.json`.
   - Recommendation: surface to Dave as the phase's first gating item. Two viable shapes:
     (a) Dave approves a `local`-class baseline commit (and/or a `gh-ubuntu-24.04` one from a
     `workflow_dispatch` perf.yml run), and PERFORMANCE.md publishes it with the environment
     manifest; or (b) PERFORMANCE.md publishes methodology + the existing measured wall-time
     table + the re-baseline ritual, and explicitly states that per-benchmark baselines are not
     yet established. (b) is deliverable today; (a) is the stronger reading of DOCS-06.
     **This looks like a `D-IMPL-NN`, not a planner call** (CLAUDE.md §11: surface gaps, do not
     paper over them).

2. **CLAUDE.md edits for the D-03 move.** `CLAUDE.md:162`, `:1227`, `:1248` name
   `docs/diagrams/` as the Phase D deliverable location and as part of the canonical directory
   skeleton. D-03 says "inbound references from READMEs and CLAUDE.md are fixed as part of the
   move," which authorizes it — but CLAUDE.md is the canonical project document and `public/`
   is a new top-level tree the skeleton does not list.
   - Recommendation: the plan should propose the CLAUDE.md diff (add `public/` to the §14
     skeleton; repoint the three `docs/diagrams` references) and route it through Dave with the
     phase gate rather than editing silently.

3. **Should `D-IMPL-NN` identifiers appear on published pages?** Docstrings across `src/` and
   `runtime/` cite them heavily (e.g. `ArtifactStoreProtocol` cites D-IMPL-26); mkdocstrings will
   render them; `docs/DECISIONS.md` is on the never-publish list. D-18 rules that whitepaper
   `§` references are legal because they disclose no content — the same argument covers D-IMPL
   numbers (they are identifiers, not content). But the published surface then contains dangling
   references to a document adopters cannot read.
   - Recommendation: treat as legal (do not add `D-IMPL` to the scan denylist — it would trip on
     dozens of legitimate docstrings), and add one line to `public/README.md` or the index page
     explaining that `D-IMPL-NN` refers to the SDK's internal decision log. Confirm with Dave.

4. **How-to page inventory.** Explicitly listed in CONTEXT §deferred as a planner-level call. The
   available raw material: `security-notes.md` (moved), plus natural how-tos derivable from
   examples 02 (grant/revoke a skill), 04 (cross-process), 05 (workflow + HITL), 07 (swap the
   ArtifactStore), and the harness-adapter seam. Recommend 4–6 pages, each a narration layer over
   an existing green example (D-10's posture), not new prose about untested paths.

5. **Does the site index reuse `README.md`?** CONTEXT §deferred leaves it open. Recommendation:
   a distinct `public/index.md`. `README.md` currently links to `docs/CCF_Whitepaper_1-2.md`,
   `docs/DECISIONS.md`, and `docs/SPEC_INVENTORY.md` in its Documentation section — reusing it as
   the index would put three never-publish paths on the front page.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (`[tool.pytest.ini_options] testpaths = ["tests"]`) |
| Config file | `pyproject.toml`; secondary `perf/pytest.ini` for the perf battery |
| Quick run command | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests -q -m "not postgres and not chroma"` |
| Full suite command | `make test` (i.e. `CCF_REQUIRE_HARNESSES=1 pytest -q`) |
| Docs-gate command | `make docs-strict` |
| Lint-harness unit tests | `pytest tools/lints/tests -q` (run in the `lint` CI job) — the precedent for testing a gate |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOCS-01 | Every snippet marker referenced by a page resolves | integration | `make docs-strict` (fails via `SnippetMissingError`) | ❌ Wave 0 (mkdocs.yml) |
| DOCS-01 | A **deleted** marker fails the build | negative | `tools/docs_tests/test_snippet_gate.py` — temp-copy a source with the marker stripped, run `mkdocs build --strict`, assert nonzero | ❌ Wave 0 |
| DOCS-02 | Every curated `::: ccf.…` identifier resolves | integration | `make docs-strict` (fails via `Could not collect`) | ❌ Wave 0 |
| DOCS-02 | A **renamed** Protocol fails the build | negative | `tools/docs_tests/test_mkdocstrings_gate.py` — inject `::: ccf.does.not.Exist`, assert nonzero | ❌ Wave 0 |
| DOCS-02 | Whitepaper body text never reaches `site/` | unit + integration | `tools/publish_scan.py site` in `make docs-strict`; unit test feeds the whitepaper itself and asserts a hit (self-test), feeds `public/how-to/security-and-deployment.md` and asserts zero | ❌ Wave 0 |
| DOCS-02 | No symlinks under `public/` | unit | `tools/publish_scan.py --pre-build` | ❌ Wave 0 |
| DOCS-02 | No `--8<--` directive in `public/` reaches `docs/` or `.planning/` | unit | same scanner, pre-build mode | ❌ Wave 0 |
| DOCS-03 | Every model in the D-11 inventory renders with a JSON Schema block | integration | grep the built HTML for `Show JSON schema` once per artifact reference page | ❌ Wave 0 |
| DOCS-04 | Every `.mmd` in `public/diagrams/` is embedded by exactly one Concepts page | unit | small test globbing `public/diagrams/*.mmd` against include directives in `public/concepts/**` | ❌ Wave 0 |
| DOCS-04 | Internal links and anchors resolve | integration | `make docs-strict` with `validation.*: warn` | ❌ Wave 0 |
| DOCS-05 | `openapi.json` matches `create_app()` | unit | extend `tests/http_api/test_openapi.py` — assert committed file == `json.dumps(app.openapi(), indent=2, sort_keys=True)` | ✅ file exists, test to add |
| DOCS-05 | An endpoint change fails the drift check | negative | covered by the above (any route edit breaks it); add a docstring in the test naming `make openapi` as the fix | ✅ |
| DOCS-06 | `make docs-strict` is part of `make ci` | unit | grep the Makefile for `ci: ci-core examples docs-strict` | ❌ Wave 0 |
| DOCS-06 | The docs job runs in always-on CI and uploads the artifact | manual/CI | first green CI run on the branch | n/a |
| DOCS-06 | PERFORMANCE.md numbers trace to a committed source | manual | reviewer check — **blocked on Open Question 1** | n/a |

### Sampling Rate

- **Per task commit:** `make lint && make docs-strict` (seconds — probe builds ran in <0.25 s;
  a full site is still fast) plus `pytest tests/http_api -q` when the OpenAPI check is touched.
- **Per wave merge:** `make ci-core` + `make docs-strict`.
- **Phase gate:** `make ci` (now including `docs-strict` per D-IMPL-72) fully green, plus the
  four negative drift tests, plus a manual read of the uploaded artifact.

### Wave 0 Gaps

- [ ] `mkdocs.yml` at repo root — nothing can be validated before it exists
- [ ] `public/` tree with at least an index page
- [ ] `pyproject.toml` `docs` extra + `dev` composition
- [ ] `.gitignore` gains `site/`
- [ ] `tools/publish_scan.py` — covers DOCS-02's never-publish criterion
- [ ] `tools/docs_tests/` (or extend `tools/lints/tests` pattern) — the four negative drift tests
- [ ] `tools/dump_openapi.py` + `make openapi` — covers DOCS-05
- [ ] Rework of the 13 F-6 docstrings — **blocks the first green `docs-strict`**

## Security Domain

`security_enforcement` is not disabled in `.planning/config.json`; the section is included.
This phase ships no runtime surface, so the ASVS mapping is thin — but the phase's *defining*
risk is information disclosure, which is unusually high stakes here (proprietary IP, CLAUDE.md §2.2).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | no new authenticated surface; the docs describe `create_app`'s auth hook, it does not add one |
| V3 Session Management | no | static site, no sessions |
| V4 Access Control | **yes (indirectly)** | the "access control" here is the publish boundary: `public/` default-deny (D-01) + post-build scan (D-02) + Actions-artifact-only distribution (D-IMPL-71) |
| V5 Input Validation | no | no user input |
| V6 Cryptography | no | none introduced |
| V14 Configuration | **yes** | pinned dependency versions; `site/` gitignored; no secret consumed by the docs job |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Whitepaper body text published via an mkdocstrings-rendered docstring | Information Disclosure | D-02 shingle scan; **13 real instances found today (F-6)** — reword before the first green build |
| Whitepaper published via a symlink under `public/` | Information Disclosure | pre-build symlink guard + post-build scan (mkdocs copies content, so a symlink is a full leak) |
| Internal deliverable published via a `--8<--` directive reaching into `docs/` | Information Disclosure | pre-build include-path check (`docs/`, `.planning/` prefixes) + post-build scan; note `restrict_base_path` does **not** cover this (Pitfall 4) |
| `site/` committed to the repo with leaked content | Information Disclosure | `site/` in `.gitignore` |
| Actions artifact retention exposing the site | Information Disclosure | repo is private; artifacts inherit repo access. D-05 accepted default retention explicitly. |
| A new dependency in the docs extra executing a postinstall/build hook | Tampering | exact pins + slopcheck audit (all 7 [OK]); no `--yes`-style auto-download anywhere in the toolchain |
| Docs job reading a secret | Information Disclosure | the job needs none — do not add `secrets:` to it |
| A future whitepaper re-format silently breaking the scan | Repudiation | scanner self-test: assert the whitepaper itself trips the scan |

## Sources

### Primary (HIGH confidence)

- **Empirical probe** in a scratch venv (`/tmp/docsprobe`), 2026-08-03 — mkdocs 1.6.1,
  mkdocs-material 9.7.7, mkdocstrings 1.0.6, mkdocstrings-python 2.0.5, pymdown-extensions
  11.0.1, griffe-pydantic 1.3.1, griffelib 2.1.0, pydantic 2.13.4. Verified: snippet section
  extraction + dedent; `check_paths` behaviour on missing file and missing section (both
  polarities); `restrict_base_path` traversal block; `base_path` CWD resolution; mkdocstrings
  strict failure on an unresolvable identifier; `griffe_pydantic` schema rendering; mermaid
  custom fence; snippet-inside-mermaid-fence.
- **Package source read directly:** `pymdownx/snippets.py` lines ~154 and ~406 (the two
  `check_paths` guards); `mkdocs/config/defaults.py` lines 175–194 (validation defaults).
- **Repository inspection** (all paths and line numbers in this document verified by
  grep/`git ls-files` on 2026-08-03): `Makefile`, `.github/workflows/ci.yml`, `pyproject.toml`,
  `.gitignore`, `tools/lints/__main__.py`, `src/ccf/**`, `runtime/ccf_runtime/**`,
  `examples/**`, `perf/**`, `docs/**`.
- `docs/DECISIONS.md` — D-IMPL-70, D-IMPL-71, D-IMPL-72, D-IMPL-73 read in full.
- https://facelessuser.github.io/pymdown-extensions/extensions/snippets/ — option names,
  defaults, marker syntax.
- https://mkdocstrings.github.io/griffe-pydantic/ — extension configuration.

### Secondary (MEDIUM confidence)

- https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/ — the MkDocs 2.0
  breaking-change notice (surfaced by the build banner itself, which is HIGH; the article
  contents were not fetched).
- `slopcheck install` run 2026-08-03 — 7/7 [OK].

### Tertiary (LOW confidence)

- None relied upon. Every mechanism claim in this document was probe-verified or read from
  source; nothing rests on WebSearch alone.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — ruled by D-IMPL-71, versions verified on PyPI, installed and built together
- Drift-gate mechanisms (D-07/D-08/D-11/D-14): **HIGH** — every claim empirically probed, including the two silent-default traps
- Publish-scan design (D-02): **HIGH** — prototyped against real repo content with positive and negative controls and an N-sensitivity sweep
- Repo integration points: **HIGH** — every path, line number, and config value read from the file
- PERFORMANCE.md source material (DOCS-06): **LOW** — Open Question 1; the required inputs do not exist in the repo and creating them is Dave-gated

**Research date:** 2026-08-03
**Valid until:** 2026-09-02 (30 days) — but re-check `mkdocs` before any version bump; the
MkDocs 2.0 release is the one event that invalidates this stack wholesale.
