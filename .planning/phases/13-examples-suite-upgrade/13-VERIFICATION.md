---
phase: 13-examples-suite-upgrade
verified: 2026-08-02T00:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Read one example's README + artifacts cold (suggest examples/01-agent-basics) and identify which artifact/key to edit to adapt it to a new domain"
    expected: "The 'What to change first' section plus [ADAPT]/[MECHANISM] markers make the exact edit obvious without reading run.py"
    why_human: "SC4 is a pedagogical-quality judgment; structure is verified but teaching effectiveness is subjective"
---

# Phase 13: Examples Suite Upgrade Verification Report

**Phase Goal:** The v0.1 examples suite (00–07) teaches the SDK on its own — every example narrates what it demonstrates and why, and its artifacts exercise enough SDK surface that an adopter can adapt it directly
**Verified:** 2026-08-02
**Status:** human_needed (all automated checks pass)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Every example 00–07 has a detailed narrated README (what/artifact-by-artifact/sections exercised/what-to-change-first) | ✓ VERIFIED | All 9 READMEs (00–08) carry the exact seven D-02 headings (`What this demonstrates`, `Run it`, `The story`, `Artifact-by-artifact`, `Whitepaper / CLAUDE.md sections exercised`, `What to change first`, `What would fail`); heading count = 7 in each |
| 2 | Scenarios exercise materially more SDK surface via richer artifacts; code stays thin per No-Hardcoding | ✓ VERIFIED | 01 agent.yaml exercises all six channel-1 axes (axis comments at lines 54–81); 02 skills.yaml expected blocks; 05 drives ReviewQueue (run.py:79–82, 678); 06 drives OverrideBoundary (run.py:99–101) with both original and override in replay ("both values in the record" in run output); [ADAPT]/[MECHANISM] markers in every example's artifacts (08 untouched by design per 13-05 scope) |
| 3 | Suite runs green in CI with single documented command per example; expected-output changes are reviewed events | ✓ VERIFIED | All 9 examples executed here: exit 0 with documented commands (03 requires `--mode deterministic` exactly as its README documents; bare invocation exits 2 with usage — refusal, not silent skip). All 9 READMEs contain "reviewed" regeneration warnings. Conformance test tests/conformance/test_harness_portability.py: 15 passed |
| 4 | Adopter can identify the exact artifact to edit; code/artifact boundary visible | ✓ VERIFIED (structural) / human check for quality | Every README's "What to change first" names concrete artifact files (e.g., 00: controlplane/events/halflife/ontology.yaml); [ADAPT]/[MECHANISM] header markers present in artifacts of all enriched examples |

**Score:** 4/4 truths verified

### Required Artifacts

All 12 plan-declared artifacts verified via `gsd-sdk query verify.artifacts` — all `passed: true` across plans 13-01..13-05 (template, 9 READMEs, 01 agent.yaml, 05 hitl.yaml).

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| 13-README-TEMPLATE.md | examples/00..07/README.md | headings copied verbatim | ✓ WIRED (tool false-negative on glob target path; manually confirmed `## What this demonstrates` in template line 29 and all 9 READMEs at line 3) |
| 01 controlplane.yaml | 01 run.py | expected block asserted | ✓ WIRED |
| 02 skills.yaml | 02 run.py | expected block asserted | ✓ WIRED |
| 03 controlplane.yaml | tests/conformance/test_harness_portability.py | conformance consumes artifacts | ✓ WIRED (15 tests pass) |
| 05 hitl.yaml | src/ccf/hitl/review_queue.py | ReviewQueue driven from artifacts | ✓ WIRED |
| 06 hitl.yaml | src/ccf/hitl/override.py | OverrideBoundary driven from artifacts | ✓ WIRED |
| 07 store_mcp.yaml | 07 run.py | store swap from artifact config | ✓ WIRED |

### Behavioral Spot-Checks (all executed in this verification session)

| Example | Command | Exit | Status |
| --- | --- | --- | --- |
| 00–02, 04–07 | `PYTHONPATH=src:runtime .venv/bin/python examples/<ex>/run.py` | 0 | ✓ PASS |
| 03 | same + `--mode deterministic` (as documented) | 0 | ✓ PASS |
| Conformance | `pytest tests/conformance/test_harness_portability.py` | 15 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| --- | --- | --- | --- |
| EXAM-01 | 13-01..13-05 | ✓ SATISFIED | Seven-section narrated READMEs on all examples, gloss table (19 terms with cites) in template |
| EXAM-02 | 13-02..13-05 | ✓ SATISFIED | Six-axis 01, skilling depth 02, ReviewQueue 05, OverrideBoundary 06, store swap 07; artifacts-first |
| EXAM-03 | 13-02..13-05 | ✓ SATISFIED | All examples exit 0 with documented commands; regeneration-as-reviewed-event wording in all 9 READMEs |

No orphaned requirements: REQUIREMENTS.md maps exactly EXAM-01/02/03 to Phase 13; all claimed by plans.

### Anti-Patterns Found

None. No TBD/FIXME/XXX, no placeholder language in example code or READMEs.

### Human Verification Required

1. **Cold-read adaptability check** — Read examples/01-agent-basics README + artifacts without code; identify the artifact/key to edit for a new domain. Expected: obvious from "What to change first" + markers. Why human: pedagogical quality is subjective (SC4).

### Gaps Summary

No gaps. All four roadmap success criteria are evidenced in the codebase, all key links wired, all nine examples run green in this verifier's own process.

---

_Verified: 2026-08-02_
_Verifier: Claude (gsd-verifier)_
