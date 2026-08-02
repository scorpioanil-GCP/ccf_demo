---
phase: 13-examples-suite-upgrade
plan: "03"
subsystem: examples
tags: [examples, skilling, harness-portability, cross-process, a2a, readme-template]
requires:
  - 13-01 (shared README template, gloss table, marker convention)
provides:
  - examples/02-skilling upgraded to the Phase-13 bar (D-02 template, enriched catalog)
  - examples/03-harness-portability upgraded (D-02 template, shipment enrichment, deterministic leg only)
  - examples/04-cross-process upgraded (D-02 template, multi-sensor payload, two-sided lineage union)
affects: []
tech-stack:
  added: []
  patterns:
    - "[ADAPT]/[MECHANISM] header markers in every enriched artifact"
    - "reviewed-event expected-block regeneration workflow in each README"
key-files:
  created: []
  modified:
    - examples/02-skilling/README.md
    - examples/02-skilling/artifacts/{agent,controlplane,events,ontology,skills}.yaml
    - examples/03-harness-portability/README.md
    - examples/03-harness-portability/artifacts/{agents/order_insights,controlplane,events,ontology,prompt}.yaml
    - examples/04-cross-process/README.md
    - examples/04-cross-process/artifacts/{a2a,agent,controlplane,events,ontology,prompt}.yaml
decisions:
  - "02 enrichment: a third catalog entry (site-status-feed, mcp type) permitted but never granted — registration-vs-capability made visible with zero run.py changes"
  - "03 enrichment: shipment entity + shipped_via edge widens the byte-identical three-harness equivalence to three entity classes; live legs untouched"
  - "04 enrichment: second kept sensor (multi-sensor exchanged payload) + a consumer-side lineage operator disjoint from the producer's plan, making the asserted merged lineage two-sided evidence of set-union"
metrics:
  duration: "~35 minutes"
  completed: "2026-08-02"
  tasks: 3
  files: 19
---

# Phase 13 Plan 03: Upgrade Examples 02–04 Summary

Examples 02 (skilling), 03 (harness-portability), and 04 (cross-process)
rewritten to the seven-heading D-02 README template with verbatim glosses and
markers, each with an artifacts-first enrichment deepening its own story —
skilling governance, portability equivalence surface, A2A admission — one
atomic commit per example.

## Commits

| Task | Example | Commit | Output delta |
| --- | --- | --- | --- |
| 1 | 02-skilling | 5af9d76 | none — new catalog entry registers but binds nothing; expected blocks unchanged |
| 2 | 03-harness-portability | c302c93 | entity_count 2→3, +shipment class, +shipped_via edge; product bytes 1048 identical ×3 |
| 3 | 04-cross-process | 95d3745 | entity_count 3→4 (second kept sensor); merged lineage now includes consumer's own operator |

## What was done

- **Example 02** — added `site-status-feed` (mcp type, requirements inside
  the envelope, never granted): the catalog is now wider than the agent's
  bound set, and the existing `bound_skill_names == (permitted,)` assertions
  cover the new entry with no code change (D-08). Refusal path narration
  deepened in the README naming `expected_excess.scopes` and the
  `skill_governance.permitted_scopes` key that triggers it. Regeneration
  warning names both `controlplane.yaml` and `skills.yaml`.
- **Example 03** — deterministic leg only: a stalled shipment (ev-104)
  attaches behind the delayed order via a new `shipped_via` edge, so the
  byte-level three-harness equivalence covers three entity classes and a
  second surviving typed edge. `expected:` updated deliberately after a
  reviewed run. Live legs (`live.yaml`, live make targets) untouched;
  README documents them as opt-in/never-CI. Conformance test
  `tests/conformance/test_harness_portability.py` run before commit: 15
  passed (it consumes `tests/fixtures/banking`, not example artifacts —
  Pitfall 2 verified rather than assumed).
- **Example 04** — a second perimeter-relevant sensor makes the exchanged
  payload multi-entity, and `policy.consumer-desk-filter` added to the
  consumer's own lineage makes the asserted `producer ∪ consumer` union
  two-sided — set-union continuity observable, not vacuous. A rejected
  admission narration was NOT forced: the tampered-envelope refusal path
  already exists and is asserted; the README elevates it as the Pattern-4
  teaching moment. All identity/trust values noted as obviously synthetic.

All three READMEs: exactly seven `##` headings in the D-02 order, verbatim
glosses from 13-README-TEMPLATE.md Part 2, Artifact-by-artifact tables
mirroring the `[ADAPT]`/`[MECHANISM]` header markers now present in every
artifact file, D-10 regeneration warnings, and concrete Adapt-it sections
naming files and keys.

## Verification

- `make example-02`, `make example-03`, `make example-04` — all exit 0
- `pytest tests/conformance/test_harness_portability.py` — 15 passed
- `make lint` — green (No-Hardcoding, harness-import, @algorithmic lints)
- `grep -c '^## '` — 7 for each of the three READMEs
- No `__pycache__`, no live-leg files, no deletions in any commit
- Exactly one commit per example directory

## Deviations from Plan

None of substance. One clarification: the plan's key_link claimed the
conformance test consumes example-03 artifacts (Pitfall 2); it actually
consumes `tests/fixtures/banking`. The test was still run before commit as
instructed and passed — the coupling concern is moot but was verified.

Note: `make` targets require the repo venv; in this worktree the main
checkout's interpreter was passed via `make PYTHON=...` (no files changed).

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes; T-13-01
(synthetic identity values) and T-13-03 (admission verification preserved
and still asserted) both honored.

## Self-Check: PASSED

- examples/02-skilling/README.md — FOUND
- examples/03-harness-portability/README.md — FOUND
- examples/04-cross-process/README.md — FOUND
- Commits 5af9d76, c302c93, 95d3745 — FOUND in git log
