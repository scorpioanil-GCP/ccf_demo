---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 04
subsystem: orchestration/docs
tags: [adk, deprecation, d-14, allowlist, key-management, d-impl-62]
requires: [08-01, 08-02]
provides:
  - "ADK driver on the non-deprecated google.adk.workflow.Workflow composition at 2.5.0 (no pin bump)"
  - "D-IMPL-62 one-line verb status note in docs/DECISIONS.md"
  - "docs/security-notes.md — key sourcing, rotation posture, CI-secrets discipline"
affects: [08-10 example 03 ADK leg, phase gate D-14 doc obligations]
tech-stack:
  added: []
  patterns:
    - "ADK Workflow via START->drive->gate edge chain; BaseAgent segments are BaseNodes at 2.5.0"
    - "D-08 allowlist as the sanctioned CINV-01 false-positive mechanism (first real use)"
key-files:
  created: [docs/security-notes.md]
  modified: [runtime/ccf_runtime/orchestration/adk/driver.py, tools/lints/allowlist.yaml, tools/lints/no_hardcoding.py, tools/lints/tests/test_no_hardcoding.py, docs/DECISIONS.md]
decisions:
  - "ADK migration taken (not suppression): Workflow is usable at 2.5.0 — BaseAgent is a BaseNode, so both driver segments plug into Workflow(edges=...) unchanged; Runner invoked via node="
  - "google.adk Workflow name collision with CCF's factory-only Workflow resolved via two reviewed cinv01c D-08 allowlist entries, not lint weakening"
  - "AllowlistEntry.matches suffix-anchors repo-relative entry paths (Rule 1 — absolute reported paths never matched the documented repo-relative form)"
metrics:
  duration: "~20 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 04: Hardening C — ADK SequentialAgent migration + D-14 doc notes Summary

ADK driver migrated off deprecated `SequentialAgent` onto
`google.adk.workflow.Workflow` at the existing 2.5.0 pin (conformance
40/40 unchanged), plus the D-IMPL-62 verb status note and the
key-management security note.

## What was built

- **Task 1 (96d355c):** `AdkWorkflowDriver` now composes
  `google.adk.workflow.Workflow` (aliased `AdkWorkflow` — CCF's own
  `Workflow` is already imported) with a `("START", drive, gate)` edge
  chain per run. The existing `_EngineSegment`/`_GatePark` `BaseAgent`
  subclasses plug in unchanged because `BaseAgent(BaseNode)` at 2.5.0;
  `Runner` is invoked via its `node=` parameter (the typed BaseNode root).
  A scratchpad probe confirmed zero deprecation warnings, correct
  ordering, and identical scalar session-state before touching the
  driver. `grep -c SequentialAgent driver.py` == 0; no suppression
  needed. Two reviewed `cinv01c` entries landed in
  `tools/lints/allowlist.yaml` (D-08 mechanism) for the harness-side
  `Workflow` name collision — the flagged calls author ADK topology, not
  CCF workflow handles, which still come only from `WorkflowFactory`.
- **Task 2 (d099904):** D-IMPL-62 entry in `docs/DECISIONS.md` carries
  the verb status note — v0 ships exactly one HITL decision verb,
  `submit`, cross-referencing D-15 and the 08-02 removal. New
  `docs/security-notes.md` (no prior security doc existed): signing-key
  sourcing for A2A identity (`SigningKeySource`/`IdentityProvider`
  Protocols, `FileBackedKeySource` as dev reference, keys never in the
  tree) and `SignedPrincipalBinding` (same D-IMPL-15 joserfc JWS
  machinery, requiredness governed by the `ccf.hitl-policy` artifact per
  D-16); rotation stated explicitly as out-of-v0 operator responsibility
  with the rotation-compatible seams named; CI-secrets discipline
  (`ANTHROPIC_API_KEY` as an Actions secret only; reviewer keys from the
  operator-local homecams `.env`, never committed).

## Deviations from Plan

**1. [Rule 3 - Blocking] D-08 allowlist entries for the ADK `Workflow` name collision**
- **Found during:** Task 1
- **Issue:** `cinv01c-factory-bypass` keys on the constructed name
  `Workflow` (alias-tracked), so `google.adk.workflow.Workflow` — a
  harness object, not CCF's — blocked `make lint`.
- **Fix:** two reviewed entries in `tools/lints/allowlist.yaml`, the
  allowlist header's ONLY sanctioned exemption path (fingerprint-exact,
  reasoned, reviewer-attributed). The lint itself is untouched in its
  name-based strictness.
- **Files modified:** tools/lints/allowlist.yaml
- **Commit:** 96d355c

**2. [Rule 1 - Bug] Allowlist path matching never worked for the documented form**
- **Found during:** Task 1 (first real exercise of the D-08 allowlist)
- **Issue:** findings report absolute paths (runner `--base` defaults to
  cwd) while the allowlist header mandates repo-relative paths "exactly
  as the lint reports it" — exact `==` matching could never fire.
- **Fix:** `AllowlistEntry.matches` accepts exact or
  path-segment-boundary suffix matches (same discipline as
  `_is_factory_module`); fingerprint matching stays exact.
- **Files modified:** tools/lints/no_hardcoding.py
- **Commit:** 96d355c

**3. [Rule 3 - Blocking] `test_shipped_allowlist_parses_and_is_empty` superseded**
- **Found during:** Task 1
- **Issue:** the shipped-allowlist test asserted the list is empty,
  contradicting the entries this plan legitimately adds.
- **Fix:** renamed to `..._entries_are_reviewed`; asserts every entry is
  CINV-01-scoped, reviewed, reasoned, with a 64-hex fingerprint.
- **Files modified:** tools/lints/tests/test_no_hardcoding.py
- **Commit:** 96d355c

**Scope note (not a deviation):** the plan's suggested
`-W error::DeprecationWarning` check is unusable as-is — ADK 2.5.0 trips
its *own* internal `BaseAgentConfig` DeprecationWarning at import time.
Warning provenance was verified instead via `pytest -W always`: the only
deprecation is ADK-internal at import; none originates from driver usage.

## Verification

- `CCF_REQUIRE_HARNESSES=1` conformance
  (`test_orchestration.py` + `test_harness_portability.py`) → 40 passed
  (25/25 orchestration bodies preserved across all four legs)
- `grep -c SequentialAgent runtime/ccf_runtime/orchestration/adk/driver.py` → 0
- `make lint` exit 0; `make typecheck` → clean, 156 files
- `pytest tools/lints/tests tests/lints -q` → 90 passed
- `make test` → **1337 passed / 0 failed** (`CCF_REQUIRE_HARNESSES=1`)
- Task 2 gate: `grep -q "submit" docs/DECISIONS.md`, `test -s
  docs/security-notes.md`, `grep -qi rotation docs/security-notes.md` → OK

## Known Stubs

None.

## Threat Flags

None — T-08-08 mitigated by the security note's keys-never-in-tree
discipline; T-08-09 gated by the unchanged 25/25 conformance bodies.

## Self-Check: PASSED
