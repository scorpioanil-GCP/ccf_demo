---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 09
subsystem: examples
tags: [examples, exam-08, artifactstore, mcp, logistics, pluggability]
requires: [08-01, 08-05]
provides:
  - "examples/07-artifact-store-mcp runnable via make example-07 (EXAM-08)"
  - "Config-only file→MCP ArtifactStore swap with byte-equality proof (§7.4)"
  - "Fresh nordhaven-logistics artifacts + two store-config artifacts"
affects: [08-12 CI examples job]
tech-stack:
  added: []
  patterns:
    - "Store choice as a config artifact interpreted by a factory keyed on store.type — no backend branch around workload logic"
    - "One workload() called twice; only the store-config artifact name differs"
    - "MCP child reads the same store_mcp.yaml auth block the parent's client factory reads — credential cannot drift"
key-files:
  created:
    - examples/07-artifact-store-mcp/run.py
    - examples/07-artifact-store-mcp/mcp_store_child.py
    - examples/07-artifact-store-mcp/README.md
    - examples/07-artifact-store-mcp/artifacts/ontology.yaml
    - examples/07-artifact-store-mcp/artifacts/events.yaml
    - examples/07-artifact-store-mcp/artifacts/controlplane.yaml
    - examples/07-artifact-store-mcp/artifacts/store_file.yaml
    - examples/07-artifact-store-mcp/artifacts/store_mcp.yaml
  modified: []
decisions:
  - "File root and MCP endpoint are env-templated in the store-config artifacts (root_env/endpoint_env) so no absolute path or port is ever committed; the driver sets both per run"
  - "The MCP server child interprets store_mcp.yaml (token, scope, server name, issuer/resource identities) rather than carrying constants — stronger than the test-tree child it mirrors, per §6.4"
  - "Determinism across the two runs comes from declared decision instants; the equality assertions cover product bytes AND artifact refs (URI + content address), not bytes alone"
metrics:
  duration: "~10 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 09: examples/07-artifact-store-mcp Summary

§7.4 pluggability proven: one logistics fabric workload run twice — once on
`FileArtifactStore`, once on the authenticated MCP-backed reference store in
a real subprocess — with the served product byte-identical, the same
artifact classes at the same exact versions on both stores, and the store
choice living entirely in two config artifacts.

## What was built

- **Task 1 (1f92cf9):** `mcp_store_child.py` — the MCP artifact server on a
  file substrate, ephemeral port, `READY {port}` handshake, all deployment
  values (token, client id, scope, server name, issuer/resource URLs)
  interpreted from `artifacts/store_mcp.yaml`. Fresh logistics artifacts
  (tenant `nordhaven-logistics`: shipment/route/depot ontology, four-envelope
  stream with dual-source lineage accumulation, a similarity-ranked-out sea
  route, and a restricted bonded depot the policy operator substitutes out)
  plus `store_file.yaml` / `store_mcp.yaml` with distinct declared
  `store.type` values and env-templated root/endpoint.
- **Task 2 (723fb9f):** `run.py` — a `_STORE_FACTORIES` seam keyed by the
  config's declared type (the only place a backend is named), exactly one
  `workload()` (boot → ingest → four-operator chain → project → gate →
  replay record → persist product + replay record through the configured
  store), spawned child with `start_new_session=True` and captured stderr,
  5-attempt/1 s health-check loop against the store's presence surface
  before the MCP run, process-group SIGTERM→SIGKILL teardown in `finally`
  printing child stderr on failure. Assertions: product bytes byte-equal
  across runs; refs equal (URI and content address, pairwise); every MCP
  ref resolvable from a fresh client at its exact version with the exact
  bytes behind it. README with the invariant table, §7.4 / Pattern 3 / §6.4
  citations, D-09 logistics rationale, and change-first guidance.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `make example-07` exits 0 first try: 1061 byte-identical product bytes,
  two artifacts (`decision-replay-record`, `context-product`) at identical
  content addresses on both stores
- Child handshake check per plan's automated verify: `READY {port}` printed,
  clean terminate
- `grep -c "def workload"` → 1; `grep -q killpg` succeeds; health-check
  retry loop precedes the MCP workload run
- `make lint` exit 0 (CINV-01 covers the example); `make typecheck` clean
  (156 files; examples excluded from mypy scope by design)
- Threat register: T-08-21 mitigated by the byte-equality and
  exact-version-retrieval assertions; T-08-22 mitigated structurally — the
  workload reaches the store only through `serve()`/`store.put`, single-writer
  boot check in force, no `ccf.graph` import in either store

## Known Stubs

None — every artifact field is consumed by the driver or the child.

## Threat Flags

None — the MCP artifact-server boundary was already in the plan's threat
model; no new surface introduced.

## Self-Check: PASSED
