---
phase: 12-synthetic-data-demonstration
plan: 03
subsystem: docs
tags: [demo, ci, makefile, readme, walkthrough, mkdocs, pymdownx-snippets]
requires:
  - "12-02: examples/08-e2e-demo/run.py + artifacts + expected_output.txt"
provides:
  - "Makefile example-08 target wired into the examples aggregate (nine examples) — make ci includes the demo with zero workflow-file changes (D-13)"
  - "examples/08-e2e-demo/README.md — short §9-conformant README linking to the walkthrough"
  - "docs/demo-walkthrough.md — narrated 'how data folds into context' with 10 repo-root-relative --8<-- literal includes, ready for Phase 14 mkdocs mount"
  - "12-VALIDATION.md finalized: per-task map green for DEMO-01..03, nyquist_compliant: true"
affects: [phase-13-examples-upgrade, phase-14-docs-site]
tech-stack:
  added: []
  patterns:
    - "walkthrough excerpts are pymdownx.snippets whole-file includes by repo-root-relative path only (no line-range syntax) so the include-path existence check is exact and Phase 14 base_path mounting is trivial"
key-files:
  created:
    - examples/08-e2e-demo/README.md
    - docs/demo-walkthrough.md
  modified:
    - Makefile
    - .planning/phases/12-synthetic-data-demonstration/12-VALIDATION.md
decisions:
  - "Whole-file --8<-- includes only (scenario, ontology, skills, agent, controlplane, halflife, prompt, expected_output, run.py, generator.py) — no pymdownx section markers inside artifacts (would touch checksum-pinned files) and no line-range paths (would break the path-exists verification and be fragile under edits)"
  - "No live-variant Makefile target for example-08 (D-10/D-12: live never in always-on CI; deferred idea explicitly rejected by plan)"
metrics:
  duration: "~25 min"
  completed: 2026-08-02
---

# Phase 12 Plan 03: CI Wiring and Narrated Walkthrough Summary

The e2e demo is now the ninth example behind `make examples` / `make ci` with zero CI workflow changes, and docs/demo-walkthrough.md narrates the raw-data-to-context transformation stage by stage with every excerpt literal-included from the files that actually run in CI.

## What Was Built

- **Makefile**: `example-08` target (`$(ENV) $(PYTHON) examples/08-e2e-demo/run.py`, deterministic, no `--live` wiring), added to `.PHONY` and to the `examples` aggregate ("all nine examples"). `.github/workflows/ci.yml` untouched — it already runs `make examples` (D-13 verified).
- **examples/08-e2e-demo/README.md**: short per §9 — what it demonstrates (entity-resolution fraud ring unreachable from raw data; L2 as hero), the single command plus `make example-08`, the `--live` note, CLAUDE.md/whitepaper sections exercised, "what to change first: artifacts/scenario.yaml", link to the walkthrough.
- **docs/demo-walkthrough.md** (291 lines): Phase 14 HTML-comment header documenting the repo-root-relative `base_path` assumption; then the seven-part narration — the invisible ring, the scenario artifact as "change this to make your own demo" (D-07), the executed baseline finding nothing, L1→L2 convergence via `identity_keys` (tax ref + address), operators→projection→gated product, the factory-built agent's governed skill finding exactly the ring, and replay/determinism — closing with the expected transcript, run.py, and running-it-yourself (`--live` included). 10 `--8<--` includes, all paths verified to exist; no pasted code.
- **12-VALIDATION.md**: Per-Task Verification Map filled with real plan/task IDs and commands (pytest test_demo_generator for DEMO-01, `make example-08` for DEMO-02, `make examples` for DEMO-03), all rows green; frontmatter `nyquist_compliant: true`, `wave_0_complete: true`, Wave 0 items checked.

## Verification

- `make example-08` → exit 0 (byte-compared narration OK)
- `make examples` → all nine examples OK, exit 0
- Include check: 10 `--8<--` directives, all paths resolve
- Full sweep: `python -m tools.lints --all` exit 0; `PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 python -m pytest -q` → 1483 passed, 2 skipped; no expected-output changes to examples 00–07
- grep confirms: example-08 in .PHONY, target, and aggregate; no live variant target

## Deviations from Plan

None - plan executed exactly as written. (Environment note, not a code deviation: the worktree lacked the gitignored `.venv`; a local symlink to the main checkout's venv was created so `make` targets run — nothing committed.)

## Commits

| Commit | Description |
| --- | --- |
| 0f5196b | feat(12-03): wire example-08 into make examples and add §9 README |
| b1f1c08 | docs(12-03): narrated demo walkthrough with literal includes + finalize validation map |

## Known Stubs

None.

## Threat Flags

None — docs/Makefile surface only; walkthrough includes reference only `examples/08-e2e-demo/*` paths (T-12-07 mitigation honored: no whitepaper or .planning includes).

## Self-Check: PASSED

- Makefile example-08 wiring — FOUND
- examples/08-e2e-demo/README.md — FOUND
- docs/demo-walkthrough.md (291 lines, 10 resolving includes) — FOUND
- 12-VALIDATION.md nyquist_compliant: true — FOUND
- Commits 0f5196b, b1f1c08 — FOUND
