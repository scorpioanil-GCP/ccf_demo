# Phase 14: Documentation Suite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-03
**Phase:** 14-Documentation Suite
**Areas discussed:** Site source layout + publish safety, Snippet include + drift mechanism, Schema + OpenAPI reference generation, Nav structure + doc placement

**Carried forward, not re-asked:** D-IMPL-71 (mkdocs-material + mkdocstrings; CI-artifact-only, nothing hosted), D-IMPL-72 (`make ci` gains `docs-strict`, effective at this phase's docs-target plan), REQUIREMENTS non-goal (no hand-written signatures, no pasted snippets).

---

## Site source layout + publish safety

### Q1 — Where should the mkdocs `docs_dir` point?

| Option | Description | Selected |
|--------|-------------|----------|
| New `docs/site/` tree | Default-deny by construction; internal deliverables stay in `docs/` and are unreachable | |
| Keep `docs_dir: docs/` with an exclude list | No file moves, but default-allow posture | |
| Move internal deliverables out to `.planning/` | Clean `docs/`, but relocates the canonical whitepaper path CLAUDE.md §2 names | |
| **Other (user)** | "Create a directory called 'public'" | ✓ |

**User's choice:** A `public/` directory as the docs source root.
**Notes:** Answered as free text rather than one of the presented options. A follow-up clarified root-level vs nested.

### Q1a — Would a repo directory called `client` make more sense?

**User's question; Claude advised against.** Rationale given: "client" is already load-bearing in this repo in two places — the MCP client role (CLAUDE.md §7.1, `src/ccf/mcp/`) and the `client_bare.py` / `client_anthropic.py` / `client_adk.py` consumer legs in `examples/external/`. A Markdown directory should borrow neither meaning. `public/` carries "published surface" natively from web-docroot convention.

### Q1b — Where should the publish-surface directory live?

| Option | Description | Selected |
|--------|-------------|----------|
| `public/` at repo root | Peer of `src/ runtime/ examples/ tests/ docs/`, one job, unambiguous boundary | ✓ |
| `docs/public/` nested | Tidier root, but the boundary sits inside the directory holding the whitepaper | |
| `client/` at repo root | User's original suggestion; advised against for the naming collision | |

**User's choice:** `public/` at repo root (recommended).

### Q2 — How is the "whitepaper is never published" guarantee proven?

| Option | Description | Selected |
|--------|-------------|----------|
| Post-build scan of the rendered site | Greps the built output for proprietary markers; proves it on the uploaded artifact | ✓ |
| Repo-structure lint only | Cheap, fits the CINV harness, but reasons about inputs — misses docstring/generated leaks | |
| Both — lint inputs, scan output | Belt and braces, two mechanisms to maintain | |

**User's choice:** Post-build scan of the rendered site (recommended).
**Notes:** Later sharpened by Q14 — the scan must key on quoted whitepaper *body text*, not bare `§` refs, or the cross-reference index trips its own gate.

### Q3 — How do the already-written publishable docs get into `public/`?

| Option | Description | Selected |
|--------|-------------|----------|
| Move them into `public/` | One home per file, no duplication, no include reaching into `docs/` | ✓ |
| Leave in `docs/`, include into `public/` | No file moves, but creates the exact escape path the boundary prevents | |
| Rewrite fresh in `public/`, retire originals | Cleanest result, most writing work | |

**User's choice:** Move them into `public/` (recommended).

### Q4 — How should the Mermaid diagrams appear?

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid rendered in-page | Native mkdocs-material support; `.mmd` stays the single artifact, no toolchain added | ✓ |
| Pre-render to SVG at build | Self-contained output, but adds Node/mermaid-cli to the always-on CI docs job | |
| You decide | Defer to planner | |

**User's choice:** Mermaid rendered in-page (recommended).

### Q5 — Posture for the CI-uploaded site artifact?

| Option | Description | Selected |
|--------|-------------|----------|
| Upload on every always-on CI run | How a private, non-hosted docs suite actually gets read | ✓ |
| Build strictly always, upload only on main / tags | Less churn, but no PR preview | |
| You decide | Defer to planner | |

**User's choice:** Upload on every always-on CI run (recommended).

### Q6 — Should `public/` carry its own README?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — short CONTRIBUTING-style note | Makes the invariant discoverable at the point of temptation, like the `examples/` charter README | ✓ |
| No — document it in CLAUDE.md and the lint | One less file to go stale | |

**User's choice:** Yes — a short CONTRIBUTING-style note (recommended).

**Area continuation:** User chose "More questions" once after Q3, then "Next area" after Q6.

---

## Snippet include + drift mechanism

### Q7 — How should include boundaries be marked?

| Option | Description | Selected |
|--------|-------------|----------|
| Named section markers in the example sources | `--8<-- "file.py:name"` + `[start:name]`/`[end:name]`; refactor-proof | ✓ |
| Whole-file includes only | Zero drift surface, but can't narrate step-by-step as DOCS-01 asks | |
| Line-range includes | No source changes, but line numbers rot silently — the exact drift failure the non-goal targets | |

**User's choice:** Named section markers in the example sources (recommended).

### Q8 — What happens when a referenced marker no longer exists?

| Option | Description | Selected |
|--------|-------------|----------|
| Fail the strict build | Breaks in the same commit; `make docs --strict` is already the always-on gate | ✓ |
| Separate marker-inventory lint | Better messages, fits CINV harness, but a second mechanism that can desync | |
| Both | Strict build for truth, lint for fast local feedback | |

**User's choice:** Fail the strict build (recommended).

### Q9 — Should definition artifacts be literal-included too?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — same marker mechanism, YAML/JSON from the artifact files | Artifacts are the adopter's primary authoring surface (§6.4); pasted YAML would drift | ✓ |
| Yes, but whole-file only for artifacts | Avoids the JSON-comment problem, longer inline blocks | |
| Code only — artifacts illustrated by hand | Reintroduces pasted content on the surface the SDK tells adopters to author in | |

**User's choice:** Yes — same marker mechanism (recommended).
**Notes:** JSON artifacts can't carry comment markers; flagged in CONTEXT.md as a planning detail (whole-file include or extraction step).

### Q10 — Which example families does the guide draw snippets from?

| Option | Description | Selected |
|--------|-------------|----------|
| The existing 00–07 suite + external legs | Guide becomes a narration layer over proven CI-run code; nothing new to keep green | ✓ |
| A new docs-only walkthrough example | Cleaner narrative, a ninth example to maintain | |
| You decide | Defer to researcher | |

**User's choice:** The existing 00–07 suite + external legs (recommended).

**Area continuation:** "Next area" after Q10.

---

## Schema + OpenAPI reference generation

### Q11 — How is the definition-artifact schema reference produced?

| Option | Description | Selected |
|--------|-------------|----------|
| Generated at docs build from the Pydantic models | Cannot drift by construction; generated pages aren't reviewable as a diff | ✓ |
| Committed JSON Schema + CI drift check | Reviewable diffs on an adopter-facing contract with its own semver lane, plus a regeneration ritual | |
| Both — committed schemas, rendered at build | Reviewable diffs and a generated site, one export mechanism | |

**User's choice:** Generated at docs build from the Pydantic models (recommended).

### Q12 — Where does the OpenAPI spec live?

| Option | Description | Selected |
|--------|-------------|----------|
| Committed `openapi.json` + CI drift check | "Drift check" presupposes a baseline; it's the contract integrators consume | ✓ |
| Generated at build only, never committed | Consistent with Q11, but there's then no drift check and no stable path | |
| You decide | Defer to researcher | |

**User's choice:** Committed `openapi.json` + CI drift check (recommended).
**Notes:** A deliberate exception to Q11's generate-at-build posture, for the two reasons above.

### Q13 — How much of the surface gets API reference pages?

| Option | Description | Selected |
|--------|-------------|----------|
| Protocols + public contracts, curated by hand | Signatures still generated; only the selection is curated | ✓ |
| Full auto-generated API tree | Nothing forgotten, but buries the six Protocols an integrator needs | |
| Curated pages + a complete auto tree behind it | Both, more nav and a larger publish-scan surface | |

**User's choice:** Protocols + public contracts, curated by hand (recommended).

### Q14 — What catches a renamed or removed referenced class?

| Option | Description | Selected |
|--------|-------------|----------|
| mkdocstrings' own strict-mode failure | Same single gate as snippet-marker drift; no extra tooling | ✓ |
| A coverage lint over the public surface | Also catches undocumented *additions*; a new lint to maintain | |
| Both | Removals and additions covered | |

**User's choice:** mkdocstrings' own strict-mode failure (recommended).

**Area continuation:** "Next area" after Q14.

---

## Nav structure + doc placement

### Q15 — How is top-level navigation organized?

| Option | Description | Selected |
|--------|-------------|----------|
| Diátaxis — Tutorial / How-to / Concepts / Reference | DOCS-01–04 already decompose this way; contributors know where a page belongs | ✓ |
| Pillar-first — nav mirrors the five Common Pillars | Conceptually coherent, but tutorials/reference/perf don't slot into a pillar | |
| Journey-first — Get started / Build / Operate / Reference | Reads well for day-1-to-production; awkward home for concepts | |

**User's choice:** Diátaxis (recommended).

### Q16 — Where do the five Common Pillars land?

| Option | Description | Selected |
|--------|-------------|----------|
| A Concepts section, one page per pillar | Phase D diagrams already exist one-per-pillar; mostly assembly | ✓ |
| One combined "Architecture" concepts page | Less nav sprawl, long page, less room per diagram | |
| You decide | Defer to planner | |

**User's choice:** A Concepts section, one page per pillar (recommended).

### Q17 — Where do PERFORMANCE.md, security notes, and the demo walkthrough sit?

| Option | Description | Selected |
|--------|-------------|----------|
| Reference / How-to / Tutorial respectively | Each lands where a reader would look for it | ✓ |
| A separate "Operations" top-level section | Clear audience split, a fifth non-Diátaxis category | |
| You decide | Defer to planner | |

**User's choice:** Reference / How-to / Tutorial respectively (recommended).

### Q18 — What does the whitepaper cross-reference index actually show?

| Option | Description | Selected |
|--------|-------------|----------|
| Section numbers + titles only, no quoted text | Useful to whitepaper holders, discloses nothing, keeps the scan satisfiable | ✓ |
| Section refs plus one-line paraphrases | More useful standalone, but paraphrase is still derived proprietary content | |
| Drop it from the site; keep it internal | Safest, but DOCS-04 names it as a deliverable — a scope reduction to log | |

**User's choice:** Section numbers + titles only, no quoted text (recommended).
**Notes:** Directly constrains the Q2 publish scan — it must key on quoted body text, not bare `§` references.

**Wrap-up:** User selected "I'm ready for context" — declined to open further gray areas.

---

## Claude's Discretion

None. Every question received an explicit ruling; no "You decide" option was taken, though one was offered on five of the eighteen questions.

## Deferred Ideas

- Hosting the site — a future D-IMPL under D-IMPL-71, revisit only if repo visibility changes.
- A public-surface docs-coverage lint (undocumented new Protocols) — considered at Q14, not adopted for v0.
- A separate marker-inventory lint for local feedback — considered at Q8, strict build covers correctness.
- Raised at wrap-up but not discussed: how-to guide inventory, docs as its own CI job vs folded in, whether top-level `README.md` becomes the site index.
