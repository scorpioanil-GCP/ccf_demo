---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 08
subsystem: hitl
tags: [hitl, escalation, override, review-queue, replay, HITL-01]
requires:
  - 07-04 (HITLTransportProtocol, HumanPrincipalBinding, replay dim-2 seam)
  - 07-07 (ApprovalGate shape, HITL_ACTION_ARTIFACT_CLASS, TOCTOU doctrine)
provides:
  - ExceptionEscalation (src/ccf/hitl/escalation.py)
  - OverrideBoundary (src/ccf/hitl/override.py)
  - ReviewQueue (src/ccf/hitl/review_queue.py)
affects: [07-09 (D-GATE cites this SUMMARY for the webhook disposition), examples 05/06]
tech-stack:
  added: []
  patterns:
    - constructor injection (transport/audit/clock) uniform across all four primitives
    - pre-serialized dim-2 hitl_actions blocks (07-05 verbatim keyword discipline)
    - typed refusals audited resolved=False; broken wiring raises (I.1 line)
key-files:
  created:
    - src/ccf/hitl/escalation.py
    - src/ccf/hitl/override.py
    - src/ccf/hitl/review_queue.py
    - tests/hitl/test_escalation.py
    - tests/hitl/test_override.py
    - tests/hitl/test_review_queue.py
    - tests/workflow/test_exception_paths.py
  modified:
    - src/ccf/hitl/__init__.py
    - tests/fixtures/banking/hitl.yaml
decisions:
  - "Webhook notify-only leg: DEFERRED from v0 (owned here — see below)"
  - "Escalation D_c condition source: DebtAssessment from assess_debt against the DebtProfile artifact; OK-signal hand-offs are typed refusals"
  - "Workflow→escalation wiring is composition-root data flow (WorkflowExceptionRouted fields), never a src→runtime import"
metrics:
  duration: "~30 min"
  completed: 2026-07-30
---

# Phase 7 Plan 08: ExceptionEscalation, OverrideBoundary, ReviewQueue Summary

Completed HITL-01's four-primitive surface: three new primitives mirroring the ApprovalGate's injection/refusal/TOCTOU/dim-2 discipline, with workflow exception paths routed into escalation end-to-end.

## What was built

- **`ExceptionEscalation`** — routing primitive. Triggers: `ExplicitEscalation(reason)` or a `DebtAssessment` produced by `ccf.halflife.debt.assess_debt` against the Control-Plane `DebtProfile` artifact (the D_c condition surface *does* exist — no discrepancy to record; thresholds never appear in code). An OK-signal assessment is a typed `EscalationRefused`, audited `resolved=False`. Hand-offs surface as `exception-escalation` events with the pinned routing artifact as `policy_ref`; resolution requires a `HumanPrincipalBinding` by type and yields the pre-serialized dim-2 block carrying the trigger.
- **Workflow exception-path integration** — `tests/workflow/test_exception_paths.py` proves the covenant workflow's failing node routes to its artifact-declared handler ref (first-class recorded transition), the deployment hands the routed state to the escalation on the shared transport, resolution lands on dim 2, and after resume/gate/terminal the exception transition appears verbatim in the dim-5 `step_sequence_block`. The seam is the `WorkflowExceptionRouted` outcome's *data* — `/src` never imports `/runtime`, so no engine change was needed.
- **`OverrideBoundary`** — generic over the overridden `CCFContract` type (`OverrideBoundary[ProductT]`, mypy `--strict` clean). `propose(original)` binds the original's content hash; `resolve(principal, override|None)` records **both** original and final values verbatim in the dim-2 block (byte-asserted, T-07-16). Confirm path (`override=None`) is a recorded `approve` action, never an absence.
- **`ReviewQueue`** — asynchronous pre-release review. `ReviewQueueItem` requires ≥1 `LineageEntry` (real §7.10.3 passage-lineage types — see symbol note below); `items(tenant)` pairs pending events with lineage views; `release`/`reject` are bound actions (rejection audited `resolved=False`); two-tenant isolation tested (D-23, T-07-18). No inbox/UI — Protocol surfaces only (§8.2 boundary).

## Passage-lineage symbols used (recorded per plan)

Grep of `src/ccf` found the I.2 citation/lineage surface in `ccf.contracts.claims`: **`PassageAnchor`** (`kind`, `locator`) and **`LineageEntry`** (`source: SourceIdentity`, `envelope_id`, `observed_at`, `passage_anchor`). `ReviewQueueItem.lineage` is typed `tuple[LineageEntry, ...]`, asserted in tests against `PassageAnchor` instances, never strings.

## Webhook notify-only leg — v0 disposition (single owner: this plan)

**DEFERRED from v0.** Rationale, per D-IMPL-20's notification/authority separation: authority never flowed through the webhook leg either way — every human action returns through the typed `HITLTransportProtocol` queue, which is what makes audit-by-construction unbypassable from a notification channel. The v0 delivery surfaces are the transport Protocol (deployments wire their own task systems) and the MCP server endpoints on the Experience Layer (D-IMPL-20's primary). A notify-only webhook emitter is a pure observer of pending events, implementable by any deployment against `HITLTransportProtocol` with zero SDK change; shipping one in v0 would encode a notification-infrastructure choice (retry semantics, signing, endpoint registry) the SDK has no business making. `transport.py`'s docstring and 07-09 both point here as the single source; nothing else re-litigates this.

## D-22 scope discipline

Every primitive's module docstring states its claims in the two named legs — **type-unrepresentable** (unbound actions cannot be constructed: `HitlActionSubmission` requires `HumanPrincipalBinding` by type) and **lint/CI-covered** (capture completeness demonstrated by the owning tests) — never an absolute "no path" claim.

## Deviations from Plan

None - plan executed exactly as written. The Cursor-flagged risk (no Control-Plane-sourced D_c condition surface) did not materialize: `assess_debt` + `DebtProfile` is exactly that surface.

## Commits

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 RED | 086f179 | failing escalation + exception-path tests, fixture material for all three tasks |
| 1 GREEN | ffbacef | ExceptionEscalation + workflow integration |
| 2 RED | 6df4a09 | failing OverrideBoundary tests |
| 2 GREEN | ae39597 | OverrideBoundary |
| 3 RED | 6c7e907 | failing ReviewQueue tests |
| 3 GREEN | d79ef19 | ReviewQueue |

## Verification

- `tests/hitl` 49 passed; `tests/workflow` (incl. new exception-path e2e) green
- Full suite: **1141 passed, 0 skipped, 0 failed**
- `tools.lints --all` exit 0 (no role/threshold/routing constant in code)
- `mypy --strict` clean on all three new modules (generic OverrideBoundary included)

## Known Stubs

None.

## Threat Flags

None — no new surface beyond the plan's threat model; T-07-16/17/18 mitigations implemented and tested as registered.

## TDD Gate Compliance

RED→GREEN commit pairs exist for all three tasks (see table); no refactor commits needed.

## Self-Check: PASSED

All 6 task commits present on the worktree branch; all 7 created files exist; full suite 1141 passed / 0 skipped; lints exit 0.
