---
phase: 13-examples-suite-upgrade
plan: 02
subsystem: examples
tags: [examples, readme, no-hardcoding, specialization-axes, half-life, debt]
requires: [13-01]
provides:
  - "examples/00-quickstart upgraded: D-02 template README, enriched banking scenario (branch entity, domiciled_at edge), ADAPT/MECHANISM markers"
  - "examples/01-agent-basics upgraded: all six channel-1 axes observably exercised (D-06), per-axis failure narration, new halflife.yaml with D_c forced-llm gating"
affects: [13-05, phase-14-docs]
tech-stack:
  added: []
  patterns:
    - "Debt profile parsed typed from agent.yaml axis-5 declaration via DebtProfile.model_fields selection (no field-name domain literals)"
    - "Reviewed expected_signal in halflife.yaml as the CAR-routing witness"
key-files:
  created:
    - examples/01-agent-basics/artifacts/halflife.yaml
  modified:
    - examples/00-quickstart/README.md
    - examples/00-quickstart/artifacts/{ontology,events,halflife,controlplane}.yaml
    - examples/01-agent-basics/README.md
    - examples/01-agent-basics/artifacts/{agent,controlplane,events,ontology,prompt,analysis_output}.yaml
    - examples/01-agent-basics/run.py
decisions:
  - "Example 00 enrichment: branch entity class + domiciled_at (account->branch) gives the depth-2 traversal a genuine second hop; expected 2->3 entities"
  - "Example 01 axis-5 gating: aged work-order-status observation (37 min vs 1h half-life x1.2 risk) yields D_c ~0.356, inside (0.30, 0.75] -> forced_llm; completeness set to 0.80 for margin over the band edge"
  - "Axis 3/4 witnesses live in expected: (role, excluded_entity_classes) so rebinding either axis fails an artifact-declared assertion"
metrics:
  duration: "~35 min"
  completed: 2026-08-02
---

# Phase 13 Plan 02: Examples 00 and 01 Upgrade Summary

**One-liner:** Examples 00 (banking quickstart) and 01 (field-service agent-basics) rewritten to the seven-heading D-02 template with artifacts-first enrichment — 00 gains a branch/domiciled_at second traversal hop, 01 makes all six specialization axes observable including a computed D_c of ~0.356 crossing the agent's forced_llm_threshold.

## Tasks Completed

| Task | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | Enrich and narrate example 00-quickstart | b834384 | README.md + 4 artifacts (run.py untouched) |
| 2 | Make example 01's six axes observably matter (D-06) | 788a1b5 | README.md + 7 artifacts (halflife.yaml new) + run.py interpreter additions |

## Expected-Output Deltas (D-09 reviewed events)

- **00:** `entity_count` 2→3, `entity_classes` +`branch`, `relationship_types` +`domiciled_at`. Cause: new branch entity rule, `domiciled_at` relationship rule, ev-104 branch-directory envelope, `domiciled_at` added to traversal types, `branch-directory-record` λ_c row. Zero run.py changes.
- **01:** `expected:` gains `role: dispatch-analyst` (axis 3) and `excluded_entity_classes: [site]` (axis 4); new `halflife.yaml` with reviewed `expected_signal: forced_llm` (axis 5, D_c ≈ 0.3555 > 0.30, ≤ 0.75). Run output prints computed debt and CAR signal.

## Per-Axis Observability (D-06)

1. Archetype binding — composition asserted against replay dim 4 and `agent.components`; printed.
2. Context contract — consumed product's schema name/version asserted equal to the contract's declared class.
3. Perspective — served payload `role` == `expected.role` == definition's Π role (chained assertion).
4. Policy regime — `site` asserted absent from the served view by name via `excluded_entity_classes`.
5. Half-life/debt — FreshnessScorer over declared observations + declared C/S factors; `assess_debt` signal asserted equal to reviewed `expected_signal`, plus band-position assertions.
6. Instruction bindings — resolved prompt artifact's `declared_parameters` == binding parameters (pre-existing, now narrated per-axis in README).

## Deviations from Plan

**1. [Rule 3 - Blocking] Worktree lacked a Python venv**
- **Found during:** Task 1 baseline run
- **Issue:** `make example-00` requires `.venv/bin/python`; venvs are not checked in and the worktree had none
- **Fix:** symlinked the main checkout's `.venv` into the worktree (`.venv` is gitignored; nothing committed)
- **Files modified:** none (untracked, ignored symlink)

**2. [Minor] `13-PATTERNS.md` referenced in plan context does not exist in the worktree base commit** (it is untracked in the main checkout). Proceeded with 13-README-TEMPLATE.md and 13-CONTEXT.md, which carry all decisions the plan cites.

**3. [Minor] Debt margin tuning:** first calibration produced D_c 0.3152 (0.015 over the band edge); completeness lowered "0.85"→"0.80" for a safer deterministic margin (D_c 0.3555) before commit.

## Verification

- `make example-00`, `make example-01`, `make lint`, `make typecheck` all green
- Both READMEs: exactly 7 `##` headings in D-02 order; regeneration warning names `controlplane.yaml`; no `--8<--`; excerpts ≤8 lines
- `[ADAPT]`/`[MECHANISM]` exact-wording markers in all 11 artifact files
- 01 README "What would fail" has 8 rows, one per axis plus two inherited invariants
- run.py diff (01 only): artifact-dict reads + assertions with per-axis comments; no domain value, threshold number or prompt text in code (No-Hardcoding lint green)
- Exactly one commit per example: b834384 (00), 788a1b5 (01)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary changes; all data synthetic (T-13-01 honored), `make lint` run before each commit (T-13-02).

## Self-Check: PASSED

- examples/01-agent-basics/artifacts/halflife.yaml — FOUND
- examples/00-quickstart/README.md (7 headings) — FOUND
- commits b834384, 788a1b5 — FOUND
