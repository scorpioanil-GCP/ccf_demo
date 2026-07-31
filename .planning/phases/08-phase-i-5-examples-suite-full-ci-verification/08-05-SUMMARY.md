---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 05
subsystem: examples
tags: [examples, quickstart, exam-01, banking, no-hardcoding]
requires: [08-01]
provides:
  - "examples/00-quickstart runnable end-to-end via make example-00 (EXAM-01)"
  - "Fresh meridian-bank artifacts: ontology, events, controlplane, halflife"
  - "README with invariant table, citations, D-09 rationale, change-first guidance"
affects: [08-06..08-11 — every later example builds on this shape, 08-12 CI examples job]
tech-stack:
  added: []
  patterns:
    - "Example = asserted program: run.py ends in explicit assertions, exit 0/nonzero"
    - "Expected results declared in controlplane.yaml `expected:` block, not in driver code"
key-files:
  created:
    - examples/00-quickstart/run.py
    - examples/00-quickstart/README.md
    - examples/00-quickstart/artifacts/ontology.yaml
    - examples/00-quickstart/artifacts/events.yaml
    - examples/00-quickstart/artifacts/controlplane.yaml
    - examples/00-quickstart/artifacts/halflife.yaml
  modified: []
decisions:
  - "Expected served-view contents (entity classes, relationship types, count) are deployment declarations in controlplane.yaml `expected:`, so run.py carries zero domain expectations (§6.4 applied to assertions, not just inputs)"
  - "halflife.yaml is load-bearing, not decorative: run.py parses it through parse_artifact (float refusal fires), registers table + profile in the Control Plane, and computes a freshness figure for a declared observation at the decision instant"
metrics:
  duration: "~12 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 05: examples/00-quickstart Summary

"Hello, Context Product" — fresh meridian-bank artifacts driving a thin
asserted run.py through L1→L6 (boot, ingest, four-operator chain, three
gates, five-dimension replay record, serve) with a λ_c freshness
demonstration; `make example-00` exits 0.

## What was built

- **Task 1 (150813f):** `examples/00-quickstart/artifacts/` authored fresh
  (banking per D-IMPL-52, distinct from `tests/fixtures/banking/` in every
  name and value: tenant `meridian-bank`, customer/account/mandate
  ontology, four-envelope stream with dual-source lineage accumulation, a
  similarity-ranked-out deposit account, and a restricted mandate the
  policy operator substitutes out). `run.py` mirrors the proto-quickstart
  pipeline: boot on SQLite in a tempdir, register resolution spec / policy
  bundle / λ_c table / debt profile / MAX_TTL in the Control Plane, ingest
  via L1, run Policy→Similarity→Temporal→Traversal, project, gate (assert
  `ServableProduct`), assert lineage strict equality and the declared
  `expected:` view, build the replay record, serve through `ReplayWriter`
  into a `FileArtifactStore`, assert content-address round trip and all
  five dimensions, then compute freshness of a declared observation. Exit
  0 on success; assertion failure exits nonzero.
- **Task 2 (369a4fa):** README with the invariant/what-would-fail table
  (proto-quickstart docstring style), both run commands, whitepaper
  (§5.2/§7.3/§7.4/§7.5/§7.6/§7.7/§7.10.1) and CLAUDE.md (§5/§6.4/§9/§10)
  citations, the D-09 banking rationale line, and "what to change first"
  pointing at `artifacts/` as the specialization surface.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `make example-00` exits 0 (prints tenant, product, entity count,
  operator count, replay content address, freshness figure)
- `make lint` exit 0 (CINV-01 covers the example code); `make typecheck`
  clean (156 files; examples excluded from mypy scope by design)
- Artifact-deletion test: moving `artifacts/` aside → run.py exits 1
  (FileNotFoundError); restored → green again (§6.4 demonstrated)
- `grep -rn "tests/fixtures" examples/00-quickstart/` → no matches
- README greps: `make example-00`, `banking`, `CLAUDE.md` all present

## Known Stubs

None — no placeholder values, no unwired data; every artifact field is
consumed by the driver.

## Self-Check: PASSED
