---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 07
subsystem: examples
tags: [examples, cross-process, exam-05, mcp-egress, a2a, admission, property-intelligence]
requires: [08-01, 08-05]
provides:
  - "examples/04-cross-process runnable end-to-end via make example-04 (EXAM-05)"
  - "Fresh larkfield-estates property-intelligence artifacts (D-07 zero-porting, D-08 domain lock)"
  - "Two-process exchange over MCP egress AND A2A with consumer-side admission verification + refusal path"
affects: [08-08 workflow-hitl (composes into the full deployment), 08-12 CI examples job]
tech-stack:
  added: []
  patterns:
    - "Child serves two surfaces (MCP egress + own A2A endpoint) on ephemeral ports, announces READY {mcp_port} {a2a_port} only after both servers started and both emissions accepted"
    - "Subprocess hygiene: start_new_session=True, stderr to file, finally-block os.killpg SIGTERM→grace→SIGKILL, stderr printed on any failure"
    - "One product, two front doors: MCP-received bytes asserted byte-equal to the A2A-signed canonical payload"
key-files:
  created:
    - examples/04-cross-process/run.py
    - examples/04-cross-process/producer_child.py
    - examples/04-cross-process/README.md
    - examples/04-cross-process/artifacts/ontology.yaml
    - examples/04-cross-process/artifacts/events.yaml
    - examples/04-cross-process/artifacts/controlplane.yaml
    - examples/04-cross-process/artifacts/a2a.yaml
    - examples/04-cross-process/artifacts/agent.yaml
    - examples/04-cross-process/artifacts/prompt.yaml
  modified: []
decisions:
  - "producer_child.py runs standalone (no env) with a throwaway per-run key and no emission, or orchestrated (run.py sets CCF_EXAMPLE04_CONSUMER_URL + CCF_EXAMPLE04_KEY_DIR) with emit-before-announce — one child serves both the plan's standalone verify and the exchange"
  - "AdmissionRecord exact-version assertion goes through the audit verdict: peering_admitted event's version is the record's content address; store.exists + get + content_hash(record)==address closes the immutability loop"
  - "Consumer's own lineage at admission is a deployment declaration in a2a.yaml (consumer.lineage), not driver constants — §6.4 applied to the union's consumer side"
  - "README names Homecams once, deliberately: Task 2 requires the explicit D-07/D-09 zero-porting statement, which supersedes Task 1's no-'homecams'-anywhere grep for README.md only; code and artifacts stay grep-clean"
metrics:
  duration: "~18 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 07: examples/04-cross-process Summary

Assembler ↔ consumer across two real OS processes in a fresh
`larkfield-estates` property-intelligence deployment: one typed Context
Product served over MCP egress and A2A, admitted on the consumer side only
after signature + policy-binding verification with an exact-version
`AdmissionRecord` and set-union lineage, and a tampered envelope refused
with L3 byte-identical; `make example-04` exits 0.

## What was built

- **Task 1 (f767e91):** `artifacts/` authored 100% fresh (property
  intelligence per D-08; `/home/parkave/homecams_v2` never opened, D-07):
  properties/zones/sensors/occupancy-signals ontology with a dual-source
  property, a similarity-ranked-out humidity sensor, and a restricted
  occupancy signal the policy operator substitutes out; Control Plane
  bundle with declared `expected:` view; A2A federation values (consumer
  identity, producer entitlements, ceilings, federated-ingest vocabulary,
  consumer's own lineage); `context_assembly` agent definition + prompt
  artifact. `producer_child.py` runs L1→L6, factory-constructs the
  assembler agent and validates the gated product against its contract,
  signs (detached JWS with the declared producer-hash assertion), emits
  genuine + spliced-tampered envelopes when a consumer URL is supplied,
  then serves MCP egress and its own A2A endpoint on ephemeral ports and
  prints `READY {mcp_port} {a2a_port}` only after both started.
- **Task 2 (906f4e5):** `run.py` — consumer fabric booted from the same
  artifacts set (federation entity rule, trust policy, ceiling, product
  class), hosts its A2A endpoint port-bound-first, spawns the child with
  `start_new_session=True` and captured stderr, blocking READY handshake,
  then: (1) MCP read validates the typed contract and is byte-equal to the
  A2A-signed payload; (2) admission asserts `AdmittedProduct`, the audited
  `AdmissionRecord` at its exact content address
  (`content_hash(record) == address`), merged lineage `== producer ∪
  consumer` on both axes, and L3 movement only through the typed
  `ingest_admitted` door; (3) the tampered envelope is refused
  (`SignatureRefusal`), the refusal audited, graph digest (db + WAL)
  unchanged. `finally` reaps the whole process group via `os.killpg`
  (SIGTERM → grace → SIGKILL); any failure prints the child's stderr and
  exits nonzero. README carries the invariant table, citations (whitepaper
  §8.3 Patterns 3–4; CLAUDE.md §7.1/§7.2/§6.1/§6.4/§10), the D-09
  property-intelligence rationale and the explicit D-07 zero-porting
  statement, and `make example-04`.

## Deviations from Plan

None blocking — plan executed as written. One reading recorded: Task 1's
acceptance grep (`grep -rn "homecams"` returns nothing) and Task 2's
requirement to state the zero-porting claim explicitly in the README
conflict; the Task 2 requirement governs `README.md`, and code + artifacts
remain grep-clean.

## Verification

- `make example-04` exits 0, including the negative admission case
  (prints tenant, peer, product, MCP byte count, admission-record address,
  merged lineage operators, refusal type)
- Task 1 standalone verify: bare `python producer_child.py` prints
  `READY {mcp_port} {a2a_port}` and terminates cleanly
- `make lint` exit 0 (CINV-01 covers the example); `make typecheck` clean
  (156 files; examples excluded from mypy scope by design)
- `grep -q start_new_session run.py` and `grep -q killpg run.py` both hit
- `grep -rn homecams` over code + artifacts → no matches (README carries
  the required explicit statement only)

## Known Stubs

None — every artifact field is consumed by a driver; no placeholder values.

## Self-Check: PASSED
