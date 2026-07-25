---
phase: 01-phase-r-research
plan: 10
subsystem: research
tags: [homecams, patterns, artifactstore, triangulation]
requires: [01-01]
provides:
  - homecams-patterns appendix fragment for SPEC_INVENTORY.md synthesis (plan 01-11)
affects: [01-11]
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - .planning/phases/01-phase-r-research/fragments/homecams-patterns.md
  modified: []
decisions:
  - "MongoDB triangulation derived from source code only (zero installs, no live query) per RESEARCH.md recommendation; live-query option deferred to Dave as an unnumbered open question"
  - "Homecams substrate mandate (MongoDB as single system-of-record) marked do-not-inherit; persistence pattern (typed repos, single writer, index-as-invariant) marked candidate pattern"
metrics:
  duration: ~15m
  completed: 2026-07-24
  tasks: 2
  files: 1
---

# Phase 01 Plan 10: Homecams Patterns Appendix Summary

Read-only survey of all nine homecams_v2 si-* packages producing a 30+-row
marker-disciplined pattern table plus a source-code-derived MongoDB persistence
triangulation for the ArtifactStore (§7.4) design.

## What Was Done

**Task 1 (commit 60a4da3):** Read `/home/parkave/homecams_v2/CLAUDE.md` exactly once
(additive context only, per CCF CLAUDE.md §2 discipline), then surveyed all 9 si-*
packages plus the start entrypoints. Produced the pattern table in
`fragments/homecams-patterns.md` — every row carries exactly one of the two markers
(`candidate pattern` / `domain-specific — do not inherit`), with source-path citations
per row (`packages/si-...`). si-framework, si-inference, si-observer, si-pool-safety,
si-conversation, si-web-ui, si-app all cited; si-models and si-ingest-server explicitly
noted as yielding no CCF-relevant patterns beyond deployment plumbing. Whitepaper-silent
resolutions (operator intermediates, projection-plan selection, replay compression,
sync/async split, definition-artifact format) recorded both as candidate patterns and
under `## Open Questions (unnumbered)`.

**Task 2 (commit 895a4f0):** MongoDB persistence documented as an ArtifactStore
triangulation data point from source code only — `mongo_data_service.py`,
`graph_entities_repository.py`, `context_edge_repository.py`,
`projection_cache_repository.py`, `fabric_activation_repository.py`,
`enrichment_worker/worker.py`. Collection names, document shapes, and index invariants
(compound unique `(tenant_id, entity_uri)`, unique natural-key edge index, TTL-governed
projection cache) captured; single-writer discipline and versioning observations mapped
to D-IMPL-26/27. Zero occurrences of `mongodb://` and zero IP addresses in the fragment
(verified by grep). No packages installed. The live-query question is in Open Questions
for Dave.

## Verification

- `| Marker |` header present: 1; `do not inherit`: 13+ rows; `candidate pattern`: 23+ occurrences — PASS
- `ArtifactStore` referenced 5 times in fragment — PASS
- `mongodb://` occurrences: 0; IP-address occurrences: 0 — PASS
- No pip/npm invocations in this plan — PASS

## Deviations from Plan

None - plan executed exactly as written. (Note: `01-PATTERNS.md` referenced in plan
context was untracked in the main repo and absent from this worktree; the table format
was reconstructed from the plan's explicit column spec: Pattern | Source | Marker | Notes.)

## Known Stubs

None.

## Threat Flags

None — T-01-03 and T-01-SC mitigations applied as planned (no connection string/IPs
committed; no package installs).

## Self-Check: PASSED

- fragments/homecams-patterns.md exists — FOUND
- 01-10-SUMMARY.md exists — FOUND
- Commits 60a4da3, 895a4f0 exist — FOUND
