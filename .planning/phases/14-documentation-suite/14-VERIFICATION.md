---
phase: 14-documentation-suite
verified: 2026-08-03T19:10:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
human_verification:
  - test: "Read public/tutorial/adopters-guide.md end to end as an adopter who has never seen CCF. Follow it literally from `pip install -e \".[dev]\"` through the replay section."
    expected: "Each section's prose explains WHY before the included snippet shows HOW; no step assumes knowledge introduced only in a later section; the reader can reach a governed, replayable deployment without consulting docs/ or the source tree."
    why_human: "Structural arc, include provenance and build health are machine-verified. Pedagogical adequacy — the actual content of the phase goal, 'a competent engineering team can go from install to production using the docs alone' — is a judgment about prose quality that no grep or build can make."
  - test: "Open the built site (`make docs-serve`) and page through Concepts → Pillars. Confirm each of the five pillar diagrams renders as a Mermaid graph, not as a raw code block or an empty figure."
    expected: "All five pillar diagrams plus the seam and sequence diagrams render visually; labels are legible and edges resolve."
    why_human: "Mermaid renders client-side in the browser. The build embeds the .mmd source into a fence; whether the JS renderer draws a correct, readable diagram cannot be verified from the built HTML."
---

# Phase 14: Documentation Suite Verification Report

**Phase Goal:** A competent engineering team can go from install to a governed, replayable deployment using the docs alone — with every API signature generated, every number measured, and every snippet literal-included from CI-run code
**Verified:** 2026-08-03
**Status:** human_needed (all automated must-haves verified; two content-quality items need a human)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Adopter's guide walks day-1 to production, every snippet literal-included from CI-run examples | ✓ VERIFIED | `public/tutorial/adopters-guide.md` (390 lines) headings trace Install → ontology/first Context Product → Declare an agent → Grant/revoke a skill → Workflow with human gate → Replay the decision → Consume from outside. 34 of 36 code blocks are `--8<--` includes drawn from 10 distinct CI-run sources across examples 00, 01, 02, 05, 06 and `examples/external/00-hello-context`. The 2 non-include blocks are shell invocations (`pip install -e ".[dev]"`, `make ci`), not pasted code or signatures. |
| 2 | Protocol/API reference generated via mkdocs-material + mkdocstrings; build provably never publishes whitepaper or internal deliverables | ✓ VERIFIED | 98 `:::` mkdocstrings identifiers across `public/reference/`; `show_source: false` set as a publish-safety measure. Never-publish gate proven by four live leak injections — see "Adversarial Gate Testing" below. All four failed the build with exit 2. |
| 3 | Definition-artifact schema reference covers the authoring surface; how-to + concepts pages exist | ✓ VERIFIED | 8 artifact reference pages carrying 29 generated identifiers total (agent-definitions 6, skill-catalog 9, control-plane-artifacts 4, skill-grants 3, task-definitions 2, workflow-definitions 2, product-registration 2, prompt-artifacts 1) with `griffe_pydantic: schema: true` rendering JSON Schema. 6 how-to pages, 5 pillar concept pages, plus `invariants.md`, `replay-anatomy.md`, `whitepaper-index.md` all present and in nav. |
| 4 | Security & deployment notes document Phase 9–10 postures; OpenAPI regenerated from `create_app()` with CI drift check | ✓ VERIFIED | `public/how-to/security-and-deployment.md` present and leads the How-to nav section (D-17). `tests/http_api/test_openapi.py` — 8 passed, in the always-on `test` job. `make openapi` re-run produced a **byte-identical** `openapi.json`. `public/reference/http-api.md:14` literal-includes `openapi.json`, so the published contract is the committed one by construction. |
| 5 | `make docs --strict` passes in always-on CI (logged D-10 amendment); PERFORMANCE.md publishes measured baselines with methodology + environment manifest | ✓ VERIFIED | `make docs-strict` run locally: **exit 0**. `Makefile:63` — `ci: ci-core examples docs-strict`. `.github/workflows/ci.yml` `docs` job on `push: branches: ["**"]` + `pull_request`, not `continue-on-error` (the only three matches are comments stating it is deliberately NOT used), uploads `site/`, and runs the docs-gate unit tests *before* the gate. D-10 amendment logged as **D-IMPL-72**; baseline authorization as **D-IMPL-75**. `perf/baselines/local.json` carries `metadata.runner_class: "local"` and `metadata.approved: "Dave, 2026-08-03, phase-14 wave-2 gate"`, whole-file-included at `public/reference/performance.md:20` alongside "What the suites measure", "Environment manifest", "What these numbers do and do not claim", and "How these numbers change — the re-baseline ritual". |

**Score:** 5/5 truths verified

### Adversarial Gate Testing (Criterion 2, second clause)

Per the standing instruction not to accept "the scan exits 0" as proof, I injected four real leaks into the working tree and ran the full `make docs-strict` gate against each. The tree was restored after every test (`git status --porcelain` clean at close).

| # | Injected leak | Channel | Result | Rule fired |
| --- | --- | --- | --- | --- |
| A | 15-word verbatim whitepaper body run appended to `public/index.md` | Markdown page | ✗ **exit 2** (12 findings) | `pub01-whitepaper-shingle` |
| B | Same run as a `%%` comment in `public/diagrams/pillar-hitl.mmd` | Mermaid diagram source — the channel the *old* scanner never read | ✗ **exit 2** | `pub01` at `site/concepts/pillars/hitl/index.html` |
| C | `public/leak.md -> ../docs/CCF_Whitepaper_1-2.md` symlink | Pre-build symlink (mkdocs copies content) | ✗ **exit 2** | `pub03-symlink` |
| D | `--8<-- "./docs/DECISIONS.md"` appended to `public/index.md` | Include escape using the `./` form that defeats a denylist | ✗ **exit 2** | `pub04-include-escape` |

The gate is genuinely default-deny, not merely quiet:

- **No allowlist, no escape hatch.** `tools/publish_scan.py` has no `--exit-zero`, no report-only mode, and no allowlist file — deliberately unlike `tools/lints/allowlist.yaml` (D-20). The 13 leaking docstrings found when the gate was written were *reworked*, not excepted.
- **Fails closed on a tree it did not read.** `require_populated()` hard-exits when the scan root is missing or empty (CR-03 fix), closing the case where a partially-failed build left `site/` empty and the scan reported clean.
- **Positive allowlist on includes** over a *normalized* target, so `./docs/x` and `public/../docs/x` are judged as the `docs/x` they resolve to.
- **Self-test.** `self_test_fires()` asserts the shingle machinery still matches its own source, so a whitepaper reformat cannot silently produce a scan that passes everything.
- **No suffix allowlist in `scan_tree`** — `.mmd` sources copied verbatim into `site/` are scanned as a publication channel, which is precisely what made test B fail.

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `mkdocs.yml` | Site config with silent-default traps closed | ✓ VERIFIED | `check_paths: true`, `restrict_base_path: true`, `strict: true`, full `validation:` block promoting `unrecognized_links`/`anchors`/`nav` to `warn` (hence fatal). `docs_dir: public`, `site_dir: site`. |
| `public/charter.md` | D-06 never-publish charter, published but out of nav (AMENDED) | ✓ VERIFIED | `public/README.md` does **not** exist. `public/charter.md` builds to `site/charter/index.html`; `not_in_nav: charter.md`; zero nav references in `site/index.html`. Amendment correctly applied. |
| `tools/publish_scan.py` | The D-02 never-publish gate | ✓ VERIFIED | 454 lines. Four rules, no allowlist. Proven live (above). |
| `openapi.json` | Committed HTTP contract baseline | ✓ VERIFIED | Regeneration byte-identical; drift test green. |
| `perf/baselines/local.json` | First committed measured baseline in D-12 schema | ✓ VERIFIED | `metadata` + `benchmarks`; runner class and Dave approval recorded. |
| `public/reference/**` | 20 reference pages | ✓ VERIFIED | 12 protocol + 8 artifact pages + http-api + performance, all in nav, all resolving. |
| `public/concepts/**` | 8 concept pages | ✓ VERIFIED | 5 pillars + invariants + replay-anatomy + whitepaper-index. |
| `public/how-to/**` | 6 how-to pages | ✓ VERIFIED | Security & deployment leads the section per D-17. |
| `Makefile` | docs-strict gate + D-IMPL-72 ci composition | ✓ VERIFIED | `ci: ci-core examples docs-strict`; `docs-strict` = pre-build scan → strict build → site scan, no `-` prefix, no `\|\| true`. |
| `.github/workflows/ci.yml` | Always-on docs job with artifact upload | ✓ VERIFIED | `run: make docs-strict`, upload of `site/`, not continue-on-error. |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| `Makefile` | `mkdocs` / `tools/publish_scan.py` | `docs-strict` three-step recipe | ✓ WIRED |
| `.github/workflows/ci.yml` | `Makefile` | `run: make docs-strict` | ✓ WIRED |
| `public/reference/http-api.md` | `openapi.json` | whole-file `--8<--` include | ✓ WIRED |
| `public/reference/performance.md` | `perf/baselines/local.json` | whole-file `--8<--` include | ✓ WIRED |
| `public/tutorial/adopters-guide.md` | 6 example run.py + 4 artifact files | marker-anchored includes | ✓ WIRED |
| `public/concepts/pillars/*.md` | `public/diagrams/*.mmd` | include inside mermaid fence | ✓ WIRED — `test_diagram_coverage.py` pins exactly-one-embed |
| `mkdocs.yml` | `ccf.*` / `ccf_runtime.*` | mkdocstrings `paths: ["src","runtime"]` | ✓ WIRED — 98 identifiers all collect under `strict` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Docs gate passes clean | `make docs-strict` | exit 0, built in 1.94 s | ✓ PASS |
| Docs-gate checkers self-test | `pytest tools/publish_scan_tests tools/docs_tests -q` | 56 passed | ✓ PASS |
| OpenAPI drift assertion | `pytest tests/http_api/test_openapi.py -q` | 8 passed | ✓ PASS |
| OpenAPI regeneration determinism | `make openapi && diff` | byte-identical | ✓ PASS |
| Leak injection × 4 | see Adversarial Gate Testing | all exit 2 | ✓ PASS |
| No `docs/diagrams` reference left in CLAUDE.md | `git grep -q 'docs/diagrams' CLAUDE.md` | exit 1 (no match) | ✓ PASS |
| `public/README.md` absent (amendment) | `ls public/README.md` | No such file | ✓ PASS |

The `tools/docs_tests` negative controls are real, not nominal: `test_mkdocstrings_gate.py` runs the **real** `mkdocs.yml` against a **copy** of the real `public/` tree, applies both an impossible-identifier mutation and a near-miss *rename* of a genuinely documented Protocol, and asserts both fail while the unmutated copy builds clean — so the failures are attributable to the mutation rather than a broken fixture.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
| --- | --- | --- | --- |
| DOCS-01 | Adopter's guide day-1-to-production narrative | ✓ SATISFIED | Criterion 1 (plan 14-07) |
| DOCS-02 | Generated Protocol/API reference; whitepaper never published | ✓ SATISFIED | Criterion 2 (plans 14-01, 14-02, 14-06) |
| DOCS-03 | Definition-artifact schema reference | ✓ SATISFIED | Criterion 3 (plan 14-06) |
| DOCS-04 | How-to guides + concepts pages | ✓ SATISFIED | Criterion 3 (plans 14-04, 14-05, 14-08) |
| DOCS-05 | Security & deployment notes + OpenAPI drift check | ✓ SATISFIED | Criterion 4 (plans 14-03, 14-04, 14-08) |
| DOCS-06 | `make docs --strict` in always-on CI + PERFORMANCE.md | ✓ SATISFIED | Criterion 5 (plans 14-01, 14-09, 14-10) |

No orphaned requirements: all six IDs mapped to Phase 14 in REQUIREMENTS.md are claimed by at least one plan's `requirements` frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `.planning/REQUIREMENTS.md` | 26–31, 83–88 | DOCS-01..06 still `- [ ]` unchecked and `Pending` in the traceability matrix | ℹ️ Info | Tracking-doc staleness only. The implementation is verified present; the checkbox is normally flipped at phase close by the orchestrator. |
| `public/tutorial/demo-walkthrough.md` | 101, 162, 210 | 3 blocks of pasted program *output* (`entities served 4458`, `ring size 5`, etc.) rather than literal includes | ⚠️ Warning | Values were cross-checked and **match `examples/08-e2e-demo/artifacts/expected_output.txt` exactly** today. But no gate ties them to that file, so a future change to the example's output would leave the walkthrough silently stale. Criterion 1's "no pasted snippets" clause is about *code*, which is fully satisfied; this is narrated output in a different page. Recorded as a hardening opportunity, not a goal gap. |
| `.github/workflows/ci.yml` | 4–7 | Stale header NOTE claiming the lint job "fails by design" until plan 04-02 | ℹ️ Info | Already recorded as open review item WR-11. Comment-only; no behavioral effect. |
| `public/charter.md` | 13–14 | Names `CCF_Whitepaper_1-2.md` / `SPEC_INVENTORY.md` as filenames | ℹ️ Info | Intentional and benign — the charter's purpose is to state what is never published. `pub02` matches *path* segments, not prose; no whitepaper content is disclosed. |

### Carried-Forward Review Items (not gaps)

`14-REVIEW.md` recorded 3 blockers + 12 warnings. All 3 blockers (CR-01/02/03) and 5 warnings (WR-02/04/05/06) were fixed with regression tests — CR-03's fail-closed fix is directly confirmed by `require_populated()` in the shipped scanner. **Nine warnings remain deliberately OPEN by Dave's scoping ruling** and are carried forward, not counted as gaps:

WR-01 (whitepaper figures / `references/` tree outside every token list), WR-03 (`normalize()` does no unicode or HTML-entity normalization), WR-07 (`--suite` never cross-checked against ids that ran), WR-08 (empty perf results set gates nothing and exits 0), WR-09 (`assemble` snippet region spans an unbalanced `try:`), WR-10 (a real leak emits one finding line per matching shingle — confirmed live in test A, which produced 12 lines for one injected quote), WR-11 (stale ci.yml header NOTE), WR-12 (`_rules()` parses findings positionally, breaks on paths containing a space).

WR-03 is the most substantive of these for the security core: the shingle normalizer strips HTML tags and code spans but does not normalize unicode look-alikes or HTML entities, so a determined adversary could evade `pub01`. This is an evasion-hardening gap against a *deliberate* actor, not a leak-detection gap against the accidental copy-paste the gate exists to catch — and `pub02`/`pub03`/`pub04` remain unaffected. Appropriate to carry forward.

### Deviations from Plan Frontmatter (both authorized)

- **14-01 must_have** said "`public/README.md` is published but absent from the nav." Verified against the **amended** form: MkDocs 1.6 aliases `README.md` to `index.md`, emitting a warning that is fatal under `strict: true` and that `not_in_nav` cannot silence. Dave's wave-1 ruling renamed it to `public/charter.md`. Confirmed: `public/README.md` absent, `site/charter/index.html` built, zero nav entries. The rationale is documented in `mkdocs.yml` lines 42–57 rather than buried in a summary.
- **14-09 `files_modified`** omitted `perf/gate.py`, where a drift-scoping fix was authorized mid-phase. In scope, not drift.

### Gaps Summary

No gaps. All five ROADMAP success criteria are verified against the codebase, all six requirement IDs are satisfied, and the phase's security core — the never-publish gate — was proven by adversarial injection across all four leak channels rather than accepted on a passing exit code.

Status is `human_needed` rather than `passed` solely because two items are irreducibly human: the pedagogical adequacy of the adopter's guide (which is the literal substance of the phase goal and cannot be established by grep or build) and the browser-side rendering of the eleven Mermaid diagrams.

---

_Verified: 2026-08-03_
_Verifier: Claude (gsd-verifier)_
