---
phase: 13-examples-suite-upgrade
plan: 05
subsystem: examples
tags: [readme, artifact-store, mcp, phase-gate, d-02-template]
requires:
  - 13-02 (examples 00/01 D-02-conformant)
  - 13-03 (examples 02-04 D-02-conformant)
  - 13-04 (examples 05/06 D-02-conformant)
provides:
  - Example 07 enriched + template-conformant README
  - Example 08 README retrofitted to D-02 heading order
  - Suite-wide phase gate green (make ci)
affects: []
tech-stack:
  added: []
  patterns:
    - Store-swap equivalence widened to a third §7.4 artifact class
      (Control Plane policy bundle) through the same factory seam
key-files:
  created: []
  modified:
    - examples/07-artifact-store-mcp/README.md
    - examples/07-artifact-store-mcp/run.py
    - examples/07-artifact-store-mcp/artifacts/controlplane.yaml
    - examples/07-artifact-store-mcp/artifacts/events.yaml
    - examples/07-artifact-store-mcp/artifacts/ontology.yaml
    - examples/07-artifact-store-mcp/artifacts/store_file.yaml
    - examples/07-artifact-store-mcp/artifacts/store_mcp.yaml
    - examples/08-e2e-demo/README.md
decisions:
  - "Enrichment surface for 07: persist the Control Plane policy bundle
    as a third artifact class through the store seam — the pairwise
    URI/content-address assertions now cover a Control Plane bundle,
    not just decision outputs (§7.4 artifact-class list)"
  - "ev-504 (second shipment on the rail route) added so the product
    depends on real multi-entity traversal; expected entity_count 3 -> 4
    updated as a reviewed event in the same commit"
metrics:
  duration: ~15 minutes
  completed: 2026-08-02
---

# Phase 13 Plan 05: Example 07 upgrade, example 08 retrofit, phase gate Summary

Example 07 rewritten to the seven-heading D-02 template with a widened
store-pluggability proof (Control Plane bundle as a third asserted
artifact class), example 08's README retrofitted to the D-02 heading
order without touching its artifacts, and the full suite proven green
under `make ci`.

## What was done

**Task 1 — example 07 (commit 9266344):**
- README grown from 57 lines to full D-02 conformance: verbatim glosses
  (ArtifactStore, MCP integration, Context Product, Control Plane),
  reviewed-regeneration paragraph naming `controlplane.yaml`, an
  Artifact-by-artifact table with the `[ADAPT]`/`[MECHANISM]` split, an
  Adapt-it section naming `store_mcp.yaml`/`store_file.yaml` keys, and
  a What-would-fail table including the single-writer invariant across
  the store boundary.
- Artifacts-first enrichment (D-08): `controlplane.yaml` gained
  `policy_bundle_artifact_class`/`_name` keys; `events.yaml` gained
  ev-504 (second shipment); all five artifact files carry the verbatim
  `[ADAPT]`/`[MECHANISM]` header markers.
- `run.py` changed only to interpret the new keys: one additional
  `store.put` of the policy bundle and a third returned ref, which the
  existing pairwise and fresh-client assertions automatically cover —
  the additional asserted surface the plan required.
- `expected:` block `entity_count` 3 → 4, reviewed against the
  assertion output and landed in the same commit (D-10, EXAM-03).

**Task 2 — example 08 retrofit + phase gate (commit aa75c95):**
- Existing 08 prose reordered under the seven D-02 headings; only glue
  prose added (story summary, artifact table, what-would-fail table
  from the example's own documented assertions). Artifacts,
  `generator.py`, checksums, and `expected_output.txt` untouched —
  `git status` for the task shows only the README.
- Byte-compare regeneration workflow kept under "Run it" (08-specific
  D-10 phrasing); `docs/demo-walkthrough.md` link retained as a closing
  pointer.
- Phase gate: `make ci` exits 0 (ci-core + all nine examples). All nine
  READMEs show exactly seven `## ` headings. `git ls-files
  'examples/**/__pycache__/*'` is empty.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `make example-07` exits 0 with the enriched artifacts
- `make lint` clean
- `grep -c '^## '` = 7 for all nine example READMEs (00–08)
- `make ci` exits 0 (phase gate, EXAM-03 / Research Pitfall 2)
- No `__pycache__` tracked under examples/
- Exactly one commit touches examples/07, one touches examples/08

## Commits

| Task | Commit | Scope |
| --- | --- | --- |
| 1 | 9266344 | examples/07-artifact-store-mcp (README + 5 artifacts + run.py) |
| 2 | aa75c95 | examples/08-e2e-demo/README.md only |

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary surface;
the store credentials in `store_mcp.yaml` remain obviously synthetic
(T-13-01 mitigated), and 08's byte-compared artifacts were not touched
(T-13-06 mitigated).

## Self-Check: PASSED
