---
phase: 04-phase-i-1-fabric-core
plan: 02
subsystem: invariant-lints
tags: [ci, governance, ast, no-hardcoding, harness-neutrality]
requires:
  - 04-01 scaffold (pyproject, .github/workflows/ci.yml lint job, src/ccf package)
provides:
  - "python -m tools.lints --all — the blocking CI gate for CINV-01/02/03 (D-07)"
  - "CINV-01 No-Hardcoding checker + versioned allowlist mechanism (D-08)"
  - "CINV-02 harness-import checker incl. the GraphWriter module restriction"
  - "CINV-03 Algorithmic-Semantic checker keyed on __ccf_mode__"
  - "ccf.llm.LLMClientProtocol — the single crisp CINV-03 import target"
affects:
  - "every subsequent Phase 4 plan is linted from its first commit; CINV-01 false positives are resolved by allowlist entry, never by code exception"
  - "L2 writer plans must place the concrete writer at ccf.graph._writer and import it only from ccf.assembly / ccf.boot"
  - "algorithmic modules must carry __ccf_mode__ = \"algorithmic\" for CINV-03 to bind"
tech-stack:
  added:
    - "stdlib ast + hashlib (hand-rolled checkers per D-06 — no plugin framework)"
    - "pyyaml (already pinned in 04-01) for allowlist parsing"
  patterns:
    - "uniform checker surface: check_source(source, path, module_name) / check(path, module_name) -> list[str]"
    - "finding format 'path:line rule message', rule as the second field"
    - "CINV-01 findings carry [fp=<sha256>] so allowlist entries key on the literal, not the line"
key-files:
  created:
    - tools/__init__.py
    - tools/lints/__init__.py
    - tools/lints/__main__.py
    - tools/lints/no_hardcoding.py
    - tools/lints/harness_imports.py
    - tools/lints/algorithmic.py
    - tools/lints/allowlist.yaml
    - tools/lints/tests/__init__.py
    - tools/lints/tests/test_no_hardcoding.py
    - tools/lints/tests/test_harness_imports.py
    - tools/lints/tests/test_algorithmic.py
    - tools/lints/tests/test_runner.py
    - src/ccf/llm/__init__.py
  modified:
    - .github/workflows/ci.yml
decisions:
  - "Import rules (CINV-02/03) take no allowlist at all — an import restriction with exceptions is not an invariant; only CINV-01 is allowlistable (D-08)"
  - "Allowlist fingerprint = sha256 of the offending literal, matched exactly with file+rule; an exception expires the moment the literal drifts"
  - "Module tag is the dunder __ccf_mode__ = \"algorithmic\" (not a docstring marker) — trivially AST-detectable and survives docstring edits"
  - "CINV-03 covers deferred imports inside functions: a lazily-imported model client is still a model call in the algorithmic path"
  - "Dot-bounded module matching everywhere, so `langgraphql` never matches the `langgraph` deny entry"
  - "`anthropic` is deny-listed outside ccf.llm / ccf_runtime.llm rather than globally allowed (D-IMPL-09 seam)"
metrics:
  duration: ~20 min
  completed: 2026-07-25
  tasks: 3
  commits: 4
---

# Phase 4 Plan 02: CINV Invariant Lints Summary

Three hand-rolled stdlib-`ast` checkers plus a blocking runner, so the
No-Hardcoding Rule, zero-harness-imports, and Algorithmic⇄Semantic Alternation
gate the tree from before the first fabric commit — turning the knowingly-red
04-01 CI lint step green.

## What Was Built

**Task 1 — CINV-02 + CINV-03 import checkers** (`796e199`). `tools/lints/`
carries three shared helpers (`format_finding`, `imported_module_names`,
`matches_module`) so all checkers emit one format and match module names with
dot boundaries. `harness_imports.py` implements two rules in one walk:
`cinv02-harness` denies `google.adk` / `langgraph` / `claude_agent_sdk`
outright and `anthropic` everywhere except the LLM adapter path
(`ccf.llm`, `ccf_runtime.llm` — the D-IMPL-09 seam); `cinv02-graph-writer`
restricts `ccf.graph._writer` to `ccf.assembly` and `ccf.boot`, which is layer
2 of the single-writer defence (threat T-04-04) — even with a writer on disk,
no other module can name it. `algorithmic.py` keys on the module-level dunder
`__ccf_mode__ = "algorithmic"` and rejects `ccf.llm` plus six vendor SDKs,
including imports deferred inside functions. `src/ccf/llm/__init__.py` ships
the `LLMClientProtocol` stub that gives CINV-03 its single crisp target.

**Task 2 — CINV-01 No-Hardcoding checker + allowlist** (`ab7b7eb`).
Prompt-shape scores four signals (≥3 sentences, role-preamble opener, ≥3
template braces, >200 chars) and flags at ≥2, behind a prose prefilter that
drops SQL openers, URIs, and whitespace-free tokens, and with docstrings
excluded by AST *position* (first `Expr`-of-`Constant` in a module/class/def
body) rather than by content. Numeric-table flags module-level
predominantly-numeric collections and numeric defaults on declared parameter
fields in parameter-schema modules (D-IMPL-38, no silent defaults).
Factory-bypass flags `Agent(` / `Task(` outside factory modules — scaffolded
now, it fires nothing until I.2. `allowlist.yaml` ships with zero entries and a
header documenting the five required fields; loading rejects an entry missing
`reason` or `reviewer`, which is the repudiation risk (T-04-03) the allowlist
exists to close.

**Task 3 — the runner** (`e20406e`). `tools/lints/__main__.py` walks `src/`,
`runtime/`, and `examples/` (absent trees skipped), derives dotted module names
from each tree root, runs the selected checkers, applies the allowlist to
CINV-01 findings only, prints survivors, and exits 1 if any remain. `--all`
plus `--no-hardcoding` / `--harness-imports` / `--algorithmic`, and a `--base`
flag so tests can point it at a fixture tree. There is no report-only or
`--exit-zero` mode: exit code is the only gate signal (D-07).

## Key Implementation Details

- **CINV-01 findings carry `[fp=<sha256>]`.** The allowlist matches
  file+rule+fingerprint exactly, so a reviewer signs off on *that text*, not on
  a line number, and an exception stops applying the moment the literal drifts.
- **Import rules deliberately take no allowlist.** Documented in both checker
  docstrings and `allowlist.yaml`, because the obvious "improvement" a later
  reader will reach for is exactly the one that voids the invariant.
- **Dot-bounded matching** throughout (`langgraphql` ≠ `langgraph`), asserted by
  a dedicated test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Lint checker tests never ran in CI**
- **Found during:** Task 3 verification
- **Issue:** `pyproject.toml` sets `testpaths = ["tests"]` and `ci.yml` runs
  `pytest tests` explicitly, so `tools/lints/tests` — the tests for the
  enforcement mechanism of three named invariants — would never have executed
  on the gate. A silently-broken checker passes a green lint step.
- **Fix:** Added a `pytest tools/lints/tests -q` step to the lint job, ahead of
  the gate it verifies, plus `tools/lints/tests/__init__.py` so the repo root is
  the import root regardless of how pytest is invoked.
- **Files modified:** `.github/workflows/ci.yml`, `tools/lints/tests/__init__.py`
- **Commit:** `4808960`

**2. [Scope addition] Numeric defaults on parameter-schema fields**
The plan's `<interfaces>` block specifies "numeric defaults on Pydantic fields
in parameter-schema modules" under CINV-01b, but the `<behavior>` list and
acceptance criteria did not name it. Implemented and covered by two tests
(hit inside a `params`-marked module, miss outside one) rather than shipped
untested or silently dropped.

## Verification

| Check | Result |
|---|---|
| `python -m tools.lints --all` on the clean tree | exit 0 |
| `pytest tools/lints/tests -q` | 45 passed |
| RED before GREEN, both TDD tasks | confirmed (`ModuleNotFoundError` on first run of each) |
| `from ccf.llm import LLMClientProtocol` | exit 0 |
| Violating fixture (`import langgraph` under a temp `src/`) | runner exits 1 (unit test) |
| Real-repo subprocess run of the exact `ci.yml` invocation | exit 0 (unit test) |
| `ci.yml` parses; lint job steps in order | ok |
| GraphWriter restriction both directions | tested (allow `ccf.assembly`/`ccf.boot`, reject others) |
| `allowlist.yaml` parses, zero active entries | ok |
| Fingerprint == sha256 of the literal | asserted against a known digest |
| Post-commit deletion check, all 4 commits | no deletions |

## Known Stubs

`src/ccf/llm/__init__.py` — `LLMClientProtocol` exposes only `model_version`.
Intentional and documented in its docstring: at I.1 the Protocol exists so the
alternation invariant has something to name. The generation surface (messages,
whitepaper §7.10.3 citations, model-version capture for Decision Replay
dimension 3) is filled in by the plan that ships the first semantic stage.
`cinv01c-factory-bypass` is likewise scaffolded-but-inert until I.2 ships the
archetypes — this is the plan's stated intent, not an omission.

## Threat Flags

None. No new network, auth, file-access, or schema surface; the lints read
repo-local source and never execute it.

## Self-Check: PASSED

All 13 created files and the 1 modified file exist on disk; all four commit
hashes (`796e199`, `ab7b7eb`, `e20406e`, `4808960`) are present in `git log`.
