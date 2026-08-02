---
phase: 12-synthetic-data-demonstration
verified: 2026-08-02T00:00:00Z
status: human_needed
score: 12/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Read docs/demo-walkthrough.md and examples/08-e2e-demo/README.md as a newcomer, then run `make example-08` and read the staged console narration"
    expected: "The narration and walkthrough make the raw-data → governed-context transformation legible to someone new to CCF; the 'change scenario.yaml to make your own demo' framing is clear"
    why_human: "Teaching quality and newcomer legibility are subjective; grep verifies structure, not pedagogy"
---

# Phase 12: Synthetic Data Demonstration — Verification Report

**Phase Goal:** A newcomer can run one command and watch raw synthetic data become governed context that lets an agent solve a problem it could not solve from the raw data alone
**Verified:** 2026-08-02
**Status:** human_needed (all automated checks passed; one subjective legibility check remains)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (plan) | Status | Evidence |
|---|-------|--------|----------|
| 1 | Generator is deterministic; pinned checksums match (D-05, D-08) | ✓ VERIFIED | `pytest tests/examples/test_demo_generator.py -q` → 4 passed (determinism, pin match, planted ring, plain-sqlite visibility) |
| 2 | Every domain value in scenario.yaml; generator is a pure interpreter (D-07) | ✓ VERIFIED | grep for ring aliases (`Harrow Point Consulting`, `HRPTSGS1XXX`, `ACCT-31-8046-1127`) across all `.py` in examples/src/runtime → zero hits; generator.py takes a scenario dict, holds no vocabulary; `tools.lints --all` exit 0 |
| 3 | Newcomer can open the three .db files with sqlite3 and see plausible rows (D-01/D-03/D-06) | ✓ VERIFIED | `test_row_counts_visible_via_plain_sqlite` passes; scenario.yaml declares core_banking/wires/kyc_registry sources |
| 4 | ~1k–5k entities, one planted ring among noise, CI-fast (D-04) | ✓ VERIFIED | scenario.yaml noise block (~1200 counterparties), 5-member ring; generator tests complete in 0.8s |
| 5 | One command runs generation → baseline → L1→L2 → graph → operators → projection → gated product → agent skill → replay, exit 0 (D-15) | ✓ VERIFIED | `make example-08` exit 0; run.py stages present (worker.ingest L680, run_gates L813, AgentFactory L917, build_replay_record L974) |
| 6 | Reasoning problem is entity-resolution fraud only L2 resolution can solve (D-02, D-09) | ✓ VERIFIED | Ring members carry genuinely disjoint per-source identifiers in scenario.yaml; ontology.yaml resolution rules link them; agent.yaml archetype analytics_insights |
| 7 | Baseline EXECUTES same detection over raw rows, finds 0; governed run finds exactly the planted ring — both asserted (D-10, D-11) | ✓ VERIFIED | Run output: Stage 2 BASELINE "structured cycles found 0"; governed stage "structured cycles found 1, ring size 5, ring members ..."; assertions at run.py L640 and L943 against artifact expected blocks |
| 8 | Full staged narration byte-compared against committed expected file (D-12/D-16) | ✓ VERIFIED | In-run assertion vs artifacts/expected_output.txt (run.py L1026-1030) passes; two consecutive runs produce byte-identical stdout (diff → identical) |
| 9 | --live adds LLM narration only; never required (D-16) | ✓ VERIFIED | argparse --live flag (L1068); LLM imports deferred inside live branch only (no top-level anthropic/llm import); deterministic run passed without LLM package |
| 10 | make example-08 runs deterministically; make examples includes it; zero CI workflow changes (D-13) | ✓ VERIFIED | Makefile: example-08 target (L75), in .PHONY (L23), in examples aggregate "all nine examples" (L78); `make example-08` exit 0; no live variant target |
| 11 | Walkthrough narrates step-by-step with literal includes by repo-root-relative paths (D-14) | ✓ VERIFIED | docs/demo-walkthrough.md 291 lines, 10 `--8<--` includes, all paths resolve (programmatic check) |
| 12 | README is short, states the single command, links to walkthrough | ✓ VERIFIED | README.md 54 lines; contains run command and link to docs/demo-walkthrough.md |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| examples/08-e2e-demo/artifacts/scenario.yaml | Versioned scenario: seed, 3 sources, ring, noise, expected pins | ✓ VERIFIED | 280 lines; seed 20260812, fixed epoch, disjoint ring identifiers, expected checksum block |
| examples/08-e2e-demo/generator.py | Pure interpreter, min 100 lines | ✓ VERIFIED | 415 lines; generate()/source_checksum(); no perf.synth import, no vocabulary |
| tests/examples/test_demo_generator.py | Determinism pin tests | ✓ VERIFIED | 133 lines, 4 tests, all pass |
| examples/08-e2e-demo/run.py | Staged composition, min 250 lines | ✓ VERIFIED | 1076 lines; six labeled stages + narration byte-compare + --live |
| artifacts/{ontology,agent,controlplane,halflife,skills,prompt}.yaml | Fabric + agent + skill + prompt definitions | ✓ VERIFIED | All present, parse; agent archetypes [analytics_insights]; controlplane expected baseline_cycles: 0 |
| artifacts/expected_output.txt | Committed byte-compared narration | ✓ VERIFIED | 48 lines; in-run equality assertion passes |
| Makefile | example-08 wired into examples aggregate + .PHONY | ✓ VERIFIED | Target, .PHONY, aggregate all present |
| examples/08-e2e-demo/README.md | §9-conformant short README | ✓ VERIFIED | Command + walkthrough link present |
| docs/demo-walkthrough.md | mkdocs walkthrough, min 150 lines, snippets | ✓ VERIFIED | 291 lines, 10 resolving includes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| generator.py | scenario.yaml | pure interpretation | ✓ WIRED | Caller (run.py L139 / tests L43) yaml.safe_load's the artifact and passes the dict to generate(); generator holds zero vocabulary. Pattern location differs from plan (safe_load in caller, not generator) — intent satisfied, arguably stronger separation |
| test_demo_generator.py | generator.py | regenerate + checksum compare | ✓ WIRED | checksum comparisons at test L60, L72 |
| run.py | generator.py | Stage 1 generate() | ✓ WIRED | generate() invoked into tempfile working dir; returned checksums asserted vs pins |
| run.py | handle.worker.ingest | single-writer ingest | ✓ WIRED | L680; no other graph write path in example |
| run.py | AgentFactory | factory-only construction | ✓ WIRED | L917, constructed from agent.yaml definition |
| run.py | expected_output.txt | narration equality assertion | ✓ WIRED | L1026-1030, passing |
| Makefile | run.py | example-08 target | ✓ WIRED | `$(ENV) $(PYTHON) examples/08-e2e-demo/run.py` |
| demo-walkthrough.md | scenario.yaml | --8<-- include | ✓ WIRED | Include present; all 10 include paths resolve |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Generator determinism + pins | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples/test_demo_generator.py -q` | 4 passed in 0.80s | ✓ PASS |
| One-command demo | `make example-08` | exit 0 | ✓ PASS |
| Byte-stable stdout | run.py twice, diff | BYTE-IDENTICAL | ✓ PASS |
| Baseline vs governed contrast | run output inspection | baseline: 0 cycles; governed: 1 cycle, 5 members | ✓ PASS |
| CI invariant lints | `.venv/bin/python -m tools.lints --all` | exit 0 | ✓ PASS |
| Walkthrough includes resolve | inline python re/pathlib check | 10 includes, missing: [] | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEMO-01 | 12-01 | Deterministic synthetic data store, domain values in artifacts | ✓ SATISFIED | Truths 1-4 |
| DEMO-02 | 12-02 | End-to-end runnable example, agent solves problem unreachable from raw data | ✓ SATISFIED | Truths 5-9 |
| DEMO-03 | 12-03 | Narrated walkthrough with literal includes; demo runs in CI | ✓ SATISFIED | Truths 10-12 |

No orphaned requirements: REQUIREMENTS.md maps exactly DEMO-01/02/03 to Phase 12, all claimed by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | none (no TODO/FIXME/XXX/HACK/placeholder in phase files) | — | — |

Note: run.py stdout includes lines beyond expected_output.txt content (e.g. --live summary hooks print outside the narration buffer by design, D-16); the byte-compare contract is the internal narration-buffer assertion plus byte-identical stdout across runs — both hold.

### Human Verification Required

### 1. Newcomer legibility of the demonstration

**Test:** As a newcomer, read examples/08-e2e-demo/README.md and docs/demo-walkthrough.md, run `make example-08`, and read the staged narration.
**Expected:** The transformation from raw per-source rows to governed context — and why the baseline fails while the governed agent succeeds — is understandable without prior CCF knowledge; the "change scenario.yaml" adaptation path is clear.
**Why human:** Pedagogical quality is not grep-verifiable.

### Gaps Summary

None. All 12 must-have truths verified against the codebase with executed evidence (tests, demo run, lints), not SUMMARY claims. Single remaining item is a subjective newcomer-legibility review.

---

_Verified: 2026-08-02_
_Verifier: Claude (gsd-verifier)_
