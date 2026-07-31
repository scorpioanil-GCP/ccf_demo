---
phase: 07-phase-i-4-orchestration-hitl-experience
plan: 14
subsystem: gate
tags: [gate, review, d-impl-62, d-impl-63, d-impl-64, d-impl-65, hitl, webhook]
requirements: [ORCH-01, ORCH-02, HITL-01, EXPR-01, EXPR-02, EXPR-03]
dependency-graph:
  requires:
    - "07-01..07-13: everything Phase I.4 shipped — the gate package covers it all"
  provides:
    - "docs/PHASE_I4_GATE.md — full gate package: sweep, 18 evidence rows, counterfactuals, deviations, residual risks, review triage, ruling outcomes, I.5 handoff"
    - "D-IMPL-62..65 resolved with Dave's rulings (2026-07-30) in docs/DECISIONS.md"
    - "HitlActionReceipt (D-IMPL-62 hardening): HTTP/CLI HITL action door states 'submitted' with honest queue disposition"
    - "ccf.hitl.webhook (D-IMPL-64): notify-only webhook HITL transport with injected delivery Protocol"
  affects:
    - "Phase 8: D-IMPL-63 named deferral (identity-binding reference impls), D-IMPL-65 engine handoff-refusal commitment, examples 03/05/06, advisory A3"
tech-stack:
  added: []
  patterns:
    - "Honest submit-only receipt: status type-closed to the one true word (Literal['submitted']); disposition fields computed from real queue state, never echoed"
    - "Notify-only by construction: notification contract carries no authority surface; delivery seam injected; failure recorded as typed outcome, never raised into the authority path"
key-files:
  created:
    - src/ccf/hitl/webhook.py
    - tests/hitl/test_webhook.py
  modified:
    - docs/DECISIONS.md          # D-IMPL-62..65 OPEN -> RESOLVED (Dave, 2026-07-30)
    - docs/PHASE_I4_GATE.md      # ruled state, rows 17-18, sweep 1280/0/0, §7.4 rulings table
    - docs/DESIGN.md             # inline corrections updated to ruled dispositions
    - src/ccf/hitl/transport.py  # HitlActionReceipt; stale 07-08-deferral docstrings corrected
    - src/ccf/hitl/__init__.py   # receipt + webhook exports
    - runtime/ccf_runtime/http_api/routes/hitl.py   # POST /hitl/actions returns the receipt
    - runtime/ccf_runtime/cli/commands/hitl.py      # submit-only semantics documented
    - tests/http_api/test_routes.py                 # 2 receipt tests (TDD RED first)
    - tests/cli/test_cli.py                         # 1 receipt-output test (TDD RED first)
decisions:
  - "D-IMPL-62 RESOLVED (Dave, 2026-07-30): submit-only with honest-contract hardening — HTTP/CLI HITL channels keep submit-to-transport semantics; response states 'submitted', never implies resolved, with disposition state; auth stays on T-07-24's residual entry, no new auth surface"
  - "D-IMPL-63 RESOLVED (Dave, 2026-07-30): identity-binding reference impls deferred to explicit follow-up-phase scope; caller-supplied principal fields are the v0 posture"
  - "D-IMPL-64 RESOLVED (Dave, 2026-07-30): deferral REJECTED — notify-only webhook transport ships in v0, built this phase with the same discipline as the other transports"
  - "D-IMPL-65 RESOLVED (Dave, 2026-07-30): composition-root debt-cascade wiring closes the gate; NAMED next-phase commitment: the engine will refuse an agent-node handoff with no bound debt assessment"
metrics:
  duration: "two sessions (checkpoint at the §3.1 stop, resumed on Dave's rulings)"
  completed: 2026-07-30
  tasks: 3
  tests: "1280 passed / 0 skipped / 0 failed under CCF_REQUIRE_HARNESSES=1 (pre-ruling 1268 + 12 new); mypy --strict clean (152 files); tools.lints --all exit 0"
---

# Phase 7 Plan 14: Gate Wave — Sweep, Review, Rulings, Approval Checkpoint Summary

Full §3.1 gate sequence for Phase I.4: sweep (1280/0/0, zero skips), 18-row evidence
gate package with recorded counterfactuals, cross-AI review triaged, the four
ruling-required findings stopped per §3.1, ruled by Dave 2026-07-30, and both ruled
in-phase fixes (D-IMPL-62 honest-contract hardening, D-IMPL-64 notify-only webhook
transport) built TDD — awaiting Dave's final gate approval; D-GATE-I.4 unwritten, no
merge to main.

## What was done

**Task 1 (commit 131746d):** Full sweep + `docs/PHASE_I4_GATE.md` in the I.3 format —
16 per-criterion rows drafted from tests observed red under breakage (D-25), the
mandatory D-22 criterion-2 wording template, three verbatim counterfactuals, the
deviations register, residual risks (T-07-24 first), DESIGN.md staleness corrections,
REQUIREMENTS ticks.

**Task 2 (commit 386422e):** `/gsd-review` cross-AI review (Codex + Cursor). 14 findings
triaged; evidence-and-wording findings fixed in-phase; four findings requiring rulings
logged as D-IMPL-62..65 (OPEN) with a §3.1 stop.

**Checkpoint resume (this session):** Dave ruled on all four (2026-07-30).

- **Rulings recorded** (commit bd44a9b): D-IMPL-62..65 flipped OPEN → RESOLVED in
  `docs/DECISIONS.md` with the rulings verbatim in substance.
- **D-IMPL-62 hardening** (commits b754a90 test / 4ae7402 feat): `HitlActionReceipt` in
  `ccf.hitl.transport` — `status: Literal["submitted"]` (type-closed; cannot imply
  resolution), submission echo, `event_pending` and `submissions_for_event` computed
  from real transport queue state. `POST /hitl/actions` returns it; the CLI (a thin
  client) prints it. RED observed: `KeyError: 'status'` against the old echo response.
- **D-IMPL-64 webhook** (commits e107f01 test / 0130e35 feat): `ccf.hitl.webhook` —
  `WebhookEndpoint` (typed, caller-supplied registrations), `HitlEventNotification`
  (field set exactly `{endpoint_key, event}` — no authority surface, test-asserted),
  injected `WebhookDeliveryProtocol` with `RecordingWebhookDeliverer` reference impl,
  `WebhookHitlNotifier` with tenant isolation (D-23), typed `WebhookEndpointConflict`
  refusal, and delivery failures recorded as `WebhookDeliveryOutcome(delivered=False)`
  rather than raised into the authority path. RED observed: collection ImportError.
- **Gate + DESIGN updated** (commit acb5835): status block, sweep numbers (1280/0/0,
  mypy 152), pass-count trajectory, new §2.3 rows 17–18, §4.2 superseded-deferral
  rewrite, §5 handoff entries for the D-IMPL-63 deferral and D-IMPL-65 engine
  commitment, §6 reduced to the final approval ask, §7.4 rulings table; DESIGN.md
  inline Phase I.4 corrections updated to the ruled dispositions.

## Verification (post-ruling sweep)

- `CCF_REQUIRE_HARNESSES=1 PYTHONPATH=src:runtime .venv/bin/python -m pytest -q` —
  **1280 passed, 0 skipped, 0 failed**
- `.venv/bin/python -m mypy` — clean, 152 source files
- `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all` — exit 0

## Deviations from Plan

**1. [Rule 1 - stale docstrings] Transport docstrings still named the 07-08 webhook
deferral** after D-IMPL-64 rejected it — corrected in `src/ccf/hitl/transport.py`
alongside the webhook feat commit (0130e35).

Otherwise the continuation executed the resume instructions exactly as written.

## Known Stubs

None. Both new surfaces are complete mechanism with reference implementations.

## Threat Flags

None — no new surface outside the plan's threat model. The webhook transport is
notify-only by construction (no authority path; T-07-35-class honesty preserved by the
row-18 evidence discipline), and the D-IMPL-62 receipt changes what the response says,
not who may call it (auth remains T-07-24's accepted residual, per the ruling).

## Outstanding (deliberate)

- **D-GATE-I.4 is NOT written; phase-i4 is NOT merged to main.** Final gate approval is
  Dave's, pending at the checkpoint this plan ends on.
- Phase 8 carries: D-IMPL-63 identity-binding reference impls (named deferral),
  D-IMPL-65 engine handoff refusal (named commitment), examples 03/05/06, advisory A3,
  `SequentialAgent` deprecation at the next google-adk pin bump, post-merge
  `pip install -e .`.

## Self-Check: PASSED

Created files exist (`src/ccf/hitl/webhook.py`, `tests/hitl/test_webhook.py`); all
cited commits present (`bd44a9b`, `b754a90`, `4ae7402`, `e107f01`, `0130e35`,
`acb5835`); post-ruling sweep re-verified green.
