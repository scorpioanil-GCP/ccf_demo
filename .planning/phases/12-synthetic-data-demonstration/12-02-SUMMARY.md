---
phase: 12-synthetic-data-demonstration
plan: 02
subsystem: examples
tags: [demo, e2e, entity-resolution, fraud-ring, agent, skills, replay, no-hardcoding]
requires:
  - "12-01: examples/08-e2e-demo/generator.py + artifacts/scenario.yaml"
provides:
  - "examples/08-e2e-demo/run.py — one-command staged demo: generate -> executed baseline -> L1->L2 ingest -> operators -> projection -> gated product -> agent skill detection -> replay serve"
  - "examples/08-e2e-demo/artifacts/{ontology,controlplane,halflife,agent,prompt,skills}.yaml — all domain values as versioned definition artifacts"
  - "examples/08-e2e-demo/artifacts/expected_output.txt — committed byte-compared staged narration"
affects: [12-03]
tech-stack:
  added: []
  patterns:
    - "role-keyed L1 envelope mapping: ontology.yaml `ingest` spec selects scenario sources/tables/columns by mechanism role, so run.py holds zero source vocabulary"
    - "one detection mechanism, two passes (D-11): the identical structured-cycle function runs over raw per-source rows (finds 0) and as the agent's granted skill over the typed Context Product (finds the ring)"
    - "skill callable fully artifact-parameterized: every entity class, edge type, attribute name, and threshold arrives in skills.yaml dispatch.arguments"
key-files:
  created:
    - examples/08-e2e-demo/run.py
    - examples/08-e2e-demo/artifacts/ontology.yaml
    - examples/08-e2e-demo/artifacts/controlplane.yaml
    - examples/08-e2e-demo/artifacts/halflife.yaml
    - examples/08-e2e-demo/artifacts/agent.yaml
    - examples/08-e2e-demo/artifacts/prompt.yaml
    - examples/08-e2e-demo/artifacts/skills.yaml
    - examples/08-e2e-demo/artifacts/expected_output.txt
  modified: []
decisions:
  - "Detection is structured-cycle detection (min length + consecutive-amount tolerance + strictly increasing timestamps + span window), not bare topology: the noise wire graph contains topological SCCs, so topology alone would not separate ring from noise; the structural constraints do, verified empirically (baseline 0, governed exactly 1)"
  - "Entity model: counterparty (identity: tax ref), site (identity: address), account, transfer, movement; wire aliases resolve to canonical counterparties through the typed-edge chain transfer -delivered_at-> site <-registered_at- counterparty, walked by the skill over the product payload"
  - "Payment edges live as transfer ENTITIES carrying amount/timestamp/party-name attributes (RelationshipClaim edges carry no attributes on the L2 co-occurrence path); typed edges carry the linking evidence"
  - "Ambiguous resolution (a display name or alias mapping to two canonicals) resolves to nothing rather than to a guess — deterministic and honest in both passes"
  - "--live provider config lives in prompt.yaml's `live` block (ollama-style endpoint, env overrides), httpx imported only inside the branch"
metrics:
  duration: "~50 min"
  completed: 2026-08-02
---

# Phase 12 Plan 02: End-to-End Demonstration Summary

One command (`PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py`) runs 6,870 raw SQLite rows through an executed baseline that finds nothing, then through L1→L2 entity resolution, the four-operator chain, a gated typed Context Product, and a factory-built AnalyticsInsights agent whose granted cycle-detection skill finds exactly the planted 5-member fraud ring — with the full staged narration byte-compared against a committed expected file.

## What Was Built

- **Six definition artifacts** carrying every domain value. `ontology.yaml` is the hero: entity rules converge the ledger account and KYC entry on one `counterparty` node (shared tax reference) and the wire transfer and KYC entry on one `site` node (shared registered address) — the two links no single source contains. Its `ingest` block maps raw rows to envelope payloads purely by mechanism roles.
- **run.py** (~1,080 lines, thin loading/mapping/asserting): six labeled stages, each printing a `_banner` that appends to the narration buffer. Stage 2 executes the same detection function over raw per-source rows (identifiers as-is) and asserts 0 cycles; Stage 5 asserts the governed skill output equals the dispatch pin (the ring, sorted legal names). All graph writes go through `handle.worker.ingest` only; agent construction is factory-only with `bound_skills` from the GrantLedger; grant admission runs the tier-1 governance check against the regime's `skill_governance` envelope.
- **expected_output.txt**: committed from the first green run; the in-run equality assertion passes and two consecutive full runs are byte-identical on stdout.
- **--live** (opt-in, never CI): renders the prompt artifact via `render_instruction` against the deterministic detection outcome and prints an Ollama-style model's summary; nothing about model text asserted; `httpx` import deferred inside the branch.

## Verification

- `PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py` → exit 0 (~40 s wall, dominated by 6,870 SQLite ingests); two consecutive runs byte-identical
- Baseline cycles = 0 and governed cycles = 1 (the pinned ring) both asserted against `controlplane.yaml expected` / `skills.yaml dispatch.expected_output`
- `pytest tests/examples/ -x -q` → 4 passed; `python -m tools.lints --all` → exit 0 (No-Hardcoding, @algorithmic, writer lints)
- Spot greps: no ring alias, source/table name, or banking literal in run.py; `worker.ingest` is the only write path; no top-level LLM imports; `--help` shows `--live`
- Detection premise verified empirically before build: noise wires DO contain topological SCCs (13/89-node), so the structural constraints (3% consecutive-amount tolerance, increasing timestamps, 30-day span, min length 3 — all artifact values) are load-bearing, and they separate ring from noise exactly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Detection defined as structured cycles, not bare topology**
- **Found during:** Task 1 design verification
- **Issue:** The raw wire log alone contains the ring as a name-level directed cycle, and the noise graph contains large SCCs — bare cycle detection would make the baseline find cycles (breaking `baseline_cycles: 0`) or the governed pass find many
- **Fix:** Detection requires amount-tolerance chaining + strictly increasing timestamps + span window + known-party attribution (all parameters in skills.yaml); baseline drops the ring edges because the aliases match no known counterparty — verified 0/1 empirically before authoring the pins
- **Files modified:** artifacts/skills.yaml, artifacts/controlplane.yaml, run.py
- **Commit:** fe7a9f5

**2. [Rule 1 - Bug] Renamed expected-block key colliding with a source table name**
- **Found during:** Task 2 acceptance greps
- **Issue:** `expected.resolved_counterparties` put the registry table name in run.py via the lookup key
- **Fix:** renamed to `resolved_seed_entities` in artifact and driver
- **Commit:** 522d866

## Commits

| Commit | Description |
| --- | --- |
| fe7a9f5 | feat(12-02): author fabric, agent, skill, and prompt definition artifacts |
| 522d866 | feat(12-02): run.py stages 1-4 — generation, executed baseline, ingest, gated product |
| 1b33826 | feat(12-02): agent skill detection, replay serve, byte-compared narration, --live |

## Known Stubs

None — every expected value is a real pinned outcome from the deterministic run.

## Notes for 12-03

- The demo is not yet wired into the Makefile `examples` CI target and has no README — deliberately left to plan 12-03's walkthrough/CI scope (not in this plan's `files_modified`).
- Full run wall time ~40 s (per-ingest SQLite commits); acceptable for CI but worth noting in the walkthrough.

## Self-Check: PASSED

- examples/08-e2e-demo/run.py — FOUND
- examples/08-e2e-demo/artifacts/{ontology,controlplane,halflife,agent,prompt,skills}.yaml — FOUND
- examples/08-e2e-demo/artifacts/expected_output.txt — FOUND
- Commits fe7a9f5, 522d866, 1b33826 — FOUND
