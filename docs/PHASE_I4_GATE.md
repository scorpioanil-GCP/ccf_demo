# Phase I.4 — Orchestration, HITL, Experience: Gate Package

STATUS: gated and merged — see §8 post-merge addendum (D-GATE-I.4, 2026-07-30).

**Phase:** 7 (Phase I.4) · **Branch:** `phase-i4` · **Assembled:** 2026-07-30
**Protocol:** CLAUDE.md §3.1 (self-review → triage → present to Dave → `D-GATE-I.4` → merge)
**Gate bar:** the D-17 checklist carried from I.1–I.3 — every row names a passing test or lint
**and what would fail if the implementation were broken** (D-25: rows are drafted from tests
that fail under the broken implementation, never from plan intent). No numeric coverage gate.

> **Status: RULED AND FIXED — AWAITING DAVE'S FINAL GATE APPROVAL.** The §3.1 cross-AI
> review ran (Codex + Cursor, 2026-07-30; §7); findings were triaged blocking/advisory; the
> evidence-and-wording findings were **fixed in-phase** (§7.2). The four findings that
> required rulings were logged as **D-IMPL-62..65** and **Dave ruled on all four on
> 2026-07-30** (recorded in `docs/DECISIONS.md`): D-IMPL-62 — submit-only with
> honest-contract hardening (hardening **implemented in-phase**, §2.3); D-IMPL-63 —
> identity-binding reference impls deferred to explicit follow-up-phase scope; D-IMPL-64 —
> deferral **rejected**, the notify-only webhook transport **implemented in-phase** (§2.3);
> D-IMPL-65 — composition-root wiring closes this gate, with a NAMED next-phase engine
> commitment. The post-ruling sweep is green (§1). `D-GATE-I.4` is **deliberately
> unwritten**; approval authority is Dave's alone (CLAUDE.md §3.1, §2). Per D-03: one
> phase, one gate — ORCH + HITL + EXPR ship and gate together; there is no I.4a/I.4b split.

> **How to read the criterion-2 rows (D-22 wording template, mandatory).** Every row that
> speaks to "unrecorded action" states **which paths are type-unrepresentable, naming the
> type or contract that makes them so**, and **which paths are lint/CI-covered, naming the
> owning test observed red under breakage**. No row in this document makes an absolute
> unscoped claim of impossibility. The one place the absolute wording appears is as a marked
> quotation: CLAUDE.md §8.2 commits that "no path through the HITL surface produces an
> unrecorded human action" — *quotation, not a claim this document asserts at that strength;
> the strength actually enforced is stated row by row below.*

---

## 1. Verification Evidence — Execution Record

**What ran, and where.** Executed 2026-07-30 on the `phase-i4` branch head (`5d9f843` plus
this plan's DESIGN/REQUIREMENTS corrections), repository root
`/home/parkave/ccf_code`, interpreter `/home/parkave/ccf_code/.venv/bin/python`
(Python 3.12), `PYTHONPATH=src:runtime`. Per D-26 the *load-bearing* check is the post-merge
run on `main`; this sweep is the merged-phase-branch-head run that precedes it.

| Leg | Command | Result |
|-----|---------|--------|
| Full suite, harnesses mandatory | `CCF_REQUIRE_HARNESSES=1 python -m pytest -q` | **1280 passed, 0 skipped, 0 failed**, exit 0 (post-ruling re-run, 2026-07-30; pre-ruling sweep was 1268/0/0) |
| Strict typing | `python -m mypy` | **Success: no issues found in 152 source files** (`src` + `runtime` per `[tool.mypy] files`; 151 pre-ruling, +1 for `ccf.hitl.webhook`) |
| Invariant lints (CINV-01a/b/c, CINV-02 incl. both carve-outs, CINV-03, d06-orchestration-split) | `python -m tools.lints --all` | **exit 0, zero findings** |

**The skip count is zero — and that is the phase's own deliverable, not an accident.** I.3
ended with exactly two deliberate skips, both naming Phase I.4 as their activating phase:
`hitl-action-capture` and `workflow-trace-capture` (CINV-04 deferrals). Plan 07-07 flipped
both, with an observed red counterfactual for each (§2.2 below, verbatim), and removed the
deferral machinery entirely rather than emptying it — an empty `parametrize` over a deferral
set would itself emit a skip. `grep -c "not-yet-applicable"
tests/invariants/test_replay_by_construction.py` → 0.

**Pass-count trajectory across the phase, no deletions:** 987 (phase baseline, 07-01) →
1002 (07-02) → 1081 (07-04) → 1096 (07-06) → 1120/0-skips (07-07) → 1141 (07-08) →
1161 (07-09) → 1232 (07-11) → 1257 (07-12) → 1268 (07-13) → **1280 (07-14, post-ruling
fixes: D-IMPL-62 hardening + D-IMPL-64 webhook transport — this sweep)**. Every plan's
SUMMARY records its own count; no test module was deleted in the phase (each plan's
self-check asserts no unexpected deletions; 07-09's role-separation diff explicitly shows
zero removed lines).

### 1.1 D-04: every wave's proof is a test fixture; `examples/` untouched

Per D-04, examples/05 (workflow-HITL) and examples/06 (decision-replay) are **Phase 8's
deliverables, not this phase's** — nothing was created under `examples/`. Every proof in
this document is a test against fixtures under `tests/fixtures/banking/` (payment-release,
covenant-review, certificate-refresh workflow/task artifacts; two-approver `hitl.yaml`;
SKILL.md import fixture under `tests/fixtures/skillmd/`).

### 1.2 Supply chain and secrets

- Two direct dependency pins were added this phase (07-01): `fastapi==0.140.0`,
  `httpx==0.28.1`, both pre-audited in the 07-RESEARCH Package Legitimacy Audit (T-07-01:
  exact-version pins, slopcheck OK, mature PyPI repos). CLI is stdlib argparse — no
  click/typer.
- No key material entered the tree; cross-AI review credentials are sourced from
  `/home/parkave/homecams_v2/.env` at runtime only (T-07-36), never committed.

---

## 2. Per-Criterion Checklist (D-17/D-25 pattern)

Every row: the claim **scoped to its actual enforcement (D-22)**, the named test or lint,
and what fails under breakage. Rows are grouped under the four ROADMAP Phase 7 success
criteria. Every row was drafted from a test that fails under the broken implementation —
the recorded reds are in §2.2 and in the cited plan SUMMARYs.

### Criterion 1 — Workflow primitive (state machine, artifacts via factory, D-IMPL-18 suspend/resume, dims 4/5)

| # | Claim, at the strength it is enforced | Named mechanism | What would fail if broken |
|---|----------------------------------------|-----------------|---------------------------|
| 1 | **Workflow definitions are Control Plane artifacts constructed only through the factory path** — construction outside `WorkflowFactory` is lint-refused (CINV-01c `FACTORY_ONLY_NAMES` includes `Workflow`), and semantic validation (step-name agreement against the *resolved* task, gate-policy kind agreement, exception-ref resolvability) runs at factory time | `tests/workflow/test_definitions.py` (28 contract cases incl. `@latest` refusal, reachability, terminal declaration), `tests/workflow/test_factory.py`; `tests/lints/test_cinv01c_behavioral.py` — bypass fires, alias bypass fires, allowlisted `ccf.workflow.factory` exempt | A `Workflow(...)` call outside the factory module fires the lint; an unpinned or unresolvable ref refuses at construction; a definition whose gate policy names a non-gate node refuses at factory time, not at first execution |
| 2 | **The engine executes factory-built handles only** — a hand-built object is a typed `WorkflowExecutionTypeError`, so the artifact path is the only path into execution | `tests/workflow/test_engine.py` (14 behavior cases); `runtime/ccf_runtime/workflow/engine.py` execute-boundary check | Handing the engine anything but the factory's frozen `Workflow` handle raises; without the check, an inline dict-shaped workflow would execute and CINV-01's artifact discipline would be decoration |
| 3 | **Suspended state persists at the Control Plane boundary through the audited, token-gated seam — never a raw `put`** (D-IMPL-18; D-20 closed by 07-02). The write path is type-unrepresentable without a `StateWriteToken`, whose sole minting path is `AuditedStateWriter`; the subclass-skipping-`__init__` and forged-kwarg paths are CI-covered by the adversarial tests, observed red under the reverted seam (§2.2) | `tests/invariants/test_state_seam_closure.py` (7 cases: direct call, forged kwarg, token construction, subclass skipping `__init__`, both-signature token, sole-minting-path, two-tenant); engine's only state writes go through `AuditedStateWriter` (07-06 acceptance grep: the only `put(` in the engine is the ArtifactStore trace write) | Reverting the closure makes the invariant module fail at *collection* (`ImportError: cannot import name 'AuditedStateWriter'` — §2.2 verbatim); a workflow suspend that wrote state without its domain event would be silent Control Plane state with no audit record (INV-CH7-71), which is exactly the multiplied-call-site risk the I.3 handoff named |
| 4 | **Suspend/resume round-trips correctly, including under interleaving** — resume decisions must name a transition the artifact declared (routing is the artifact's statement; no decision→state constant exists in code); undeclared decisions are typed refusals audited `resolved=False` | `tests/workflow/test_engine.py` round-trip cases; `tests/workflow/test_engine_stateful.py` — `hypothesis.stateful` `RuleBasedStateMachine` over two tenants × two workflow shapes with four invariants (incl. trace completeness) | A resume that re-executed instead of transitioning, a cross-tenant state leak, or a trace missing a transition — the stateful suite drives interleavings a straight-line test never reaches |
| 5 | **Execution traces land in replay dimensions 4 and 5 verbatim** — the engine serializes the dim-5 step-sequence block and dim-4 delegation chain once; `build_replay_record` records them byte-for-byte (07-05 keyword discipline). CINV-04 `workflow-trace-capture` is **active** with its owning test proven red under a severed pass-through (§2.2) | `tests/workflow/test_slice.py::test_the_step_sequence_lands_on_dimension_5_verbatim`; `tests/replay/test_dimension_extensions.py` (five-dimension structural assertion INV-CH7-80, byte-equality, round-trip, two-tenant); `tests/invariants/test_replay_by_construction.py` (active-only registry) | Severing the dim-5 pass-through: `assert ... == outcome.step_sequence_block` fails against the `no-workflow-trace` sentinel — measured, verbatim in §2.2. A sixth dimension block is an INV-CH7-80 fidelity defect the structural assertion catches |
| 6 | **D-IMPL-61 (option-a) exception semantics: an absent per-node exception ref is a defined, audited transition to the reserved terminal `failed` state, recorded in the trace as a first-class transition; a bound ref routes to its artifact-declared handler as a recorded transition** | `tests/workflow/test_definitions.py` (`WORKFLOW_FAILED_STATE` reserved: valid target, never a source, never the start); `tests/workflow/test_engine.py` exception cases; `tests/workflow/test_exception_paths.py` — end-to-end: failing node → artifact-declared handler ref → escalation on the shared transport → a bound resolution producing its `hitl_actions_block` *(narrowed — closes review finding X-4: the test asserts the block is produced, and the **dim-5** exception transition verbatim through the replay path; it does not drive this block through `build_replay_record` — dim-2 landing of an arbitrary block is the builder guarantee cited in row 7)* → exception transition verbatim in the dim-5 block | An exception that fell through unrecorded, or a propagate-to-terminal that did not appear in the trace — the accepted consequence of option-a (an author can omit a handler) is mitigated exactly here: the trace makes the omission observable at first exercise |

### Criterion 2 — HITL primitives write to Decision Replay (D-22-scoped rows)

The ROADMAP criterion's own sentence ("CI verifies there is no path through the HITL surface
producing an unrecorded human action") is a quotation of CLAUDE.md §8.2. What is enforced,
stated in the mandatory template:

| # | Claim, in the D-22 template | Named mechanism | What would fail if broken |
|---|------------------------------|-----------------|---------------------------|
| 7 | **An unbound human action is type-unrepresentable via `HitlActionSubmission`**, whose `principal: HumanPrincipalBinding` is a required field on an `extra=forbid` contract (all four D-IMPL-21 fields required: approver identity + IdP ref, authentication context, injected `action_time`, sha256-shape `product_content_hash`); **capture completeness is CI-covered at this scope, stated precisely** *(narrowed — closes review findings X-3/C-4)*: the CINV-04 owning test `tests/workflow/test_slice.py::test_the_human_action_lands_on_dimension_2_verbatim` drives the **ApprovalGate** end to end through `build_replay_record` and was observed red under the severed capture (§2.2 verbatim); the other three primitives are covered **compositionally** — per-primitive byte-equality of the produced `hitl_actions_block` against the canonical action record (`tests/hitl/test_{escalation,override,review_queue}.py`) composed with the builder's verbatim-landing guarantee (`tests/replay/test_dimension_extensions.py::test_a_supplied_hitl_block_lands_on_dimension_2_verbatim`) — **not** by a per-primitive end-to-end replay drive. The CINV-04 registry's "every … by construction" sentences are marked CLAUDE.md quotations, not suite claims at that strength | `src/ccf/hitl/principal.py`, `src/ccf/hitl/transport.py`; `tests/hitl/test_principal.py`, `tests/hitl/test_transport.py`; `tests/invariants/test_replay_by_construction.py` `hitl-action-capture` (active, with adversarial-case table) | Constructing a submission with no binding is a Pydantic validation error, not an anonymous record; severing the dim-2 pass-through turns the owning test red against the `no-hitl-actions` sentinel — measured, §2.2 |
| 8 | **ApprovalGate: rejection and TOCTOU refusal are recorded outcomes, not exceptions or absences** — both audit `resolved=False` under the `hitl_action` action; the approver's view is pinned by suspend-time `product_content_hash`, and a hash mismatch is a returned `GateResolutionRefused` with the event left pending (T-07-39). The sync `ApprovalSink` face is satisfied by composition (`ApprovalSinkAdapter` wrapping a completed bound `GateResolution`); `decide()` with nothing bound raises typed `UnboundDecisionError` — the adapter is type-unable to fabricate a verdict | `tests/hitl/test_approval_gate.py`; `tests/conformance/test_approval_sink.py` (the `approval-gate-adapter` param joined with **zero test-body changes** — diff-asserted); `tests/workflow/test_slice.py` TOCTOU mutate-between and two-approver (D-23) cases | A gate that resolved against a product the human did not see; a rejection that vanished instead of auditing `resolved=False`; a sink that produced a verdict no human made |
| 9 | **ExceptionEscalation's D_c trigger reads Control-Plane values only** — `assess_debt` against the `DebtProfile` artifact; an OK-signal hand-off is a typed `EscalationRefused` audited `resolved=False`; no threshold exists in code (CINV-01b) | `tests/hitl/test_escalation.py`; `tools.lints --all` (cinv01b-numeric-table) | A threshold constant in `/src` fires the lint; an escalation on an OK signal would make the routing artifact's statement false |
| 10 | **OverrideBoundary records both the original and the final value verbatim** (byte-asserted, T-07-16); the confirm path (`override=None`) is a recorded `approve` action, never an absence. **ReviewQueue items require ≥1 real `LineageEntry`** (§7.10.3 passage-lineage types, `PassageAnchor` instances — never strings); release/reject are bound actions; two-tenant isolation held (D-23, T-07-18) | `tests/hitl/test_override.py` (generic `OverrideBoundary[ProductT]`, mypy `--strict` clean); `tests/hitl/test_review_queue.py` | An override that erased what it overrode; a confirm that left no record; a review item with fabricated string lineage |

### Criterion 3 — OrchestrationProtocol: external orchestrators drive workflows without touching SDK internals

| # | Claim | Named mechanism | What would fail if broken |
|---|-------|-----------------|---------------------------|
| 11 | **The Protocol is in `/src` with the driver-implements doctrine, and the bare engine structurally fails the isinstance check** — verbs are `start_execution`/`resume_execution`, deliberately not the engine's names; the doctrine sentence ("…not a third peer harness") is verbatim in the module docstring; zero harness imports; `__ccf_mode__ = "algorithmic"` | `src/ccf/orchestration/protocol.py`; `tests/conformance/test_orchestration.py::test_the_bare_engine_is_not_the_isinstance_target` | Renaming the Protocol verbs to the engine's would make every object with an engine surface "conform" — the doctrine made structural, not just written |
| 12 | **D-IMPL-60 complete: four legs (in-sdk, langgraph, adk, claude-agent) pass one factory-parametrized conformance suite with zero shared-body edits between 07-12 and 07-13** — each leg drives the same payment-release workflow end-to-end (skill step → real ApprovalGate suspension → bound approval → `released` terminal) with **byte-identical replay obligations** (canonical-bytes-equal step-sequence block, delegation chain, trace content address vs the reference leg; D-23 two-tenant keying through the driver seam) | `tests/conformance/test_orchestration.py` — 25/25 (5 bodies × 4 legs + 5 suite-mechanism tests); `CCF_REQUIRE_HARNESSES=1` turns absent-SDK skips into failures (the I.3 row-12 pattern, inherited not reinvented) | A leg whose replay bytes diverge from the reference leg's; a driver reaching the engine's internals rather than its public surface; a shared-body edit smuggling per-leg accommodation (diff-asserted at each 07-13 RED commit) |
| 13 | **Orchestrators hold position only; typed CCF outcomes never enter an orchestrator's persistence** (T-07-30/T-07-33) — LangGraph checkpointer values, ADK session state, and the Claude session transcript are all asserted scalar (`str|bool|int`), never a `CCFContract`; suspended authority lives in `WorkflowStateRecord` on the Control Plane store. **The orchestration/adapters module split is lint-enforced bidirectionally** (d06-orchestration-split), with D-24-discipline negative tests in both directions plus the lookalike-sibling case | per-leg introspection seams (`checkpointed_values()`, `persisted_state()`, `session_transcript()`) driven by the shared T-07-33 body; `tools/lints/orchestration_imports.py`; `tests/lints/test_orchestration_imports.py` (orchestration→adapters fails, adapters→orchestration fails, `ccf_runtime.peering`/`cdc` harness imports still fail, `ccf_runtime.orchestration_evil` lookalike flagged) | An orchestrator's checkpoint becoming a second source of workflow truth; a driver importing an adapter (loop absorption — advisory A7's failure mode, now structurally unrepresentable rather than documented) |

### Criterion 4 — Three front doors

| # | Claim | Named mechanism | What would fail if broken |
|---|-------|-----------------|---------------------------|
| 14 | **MCP front door (EXPR-01), discharging the D-GATE-I.3 named Experience-edge deferral**: products (`ccf-experience-product://`) and agents (list/invoke Tools rendering every bound skill through the D-IMPL-56 shared derivation) on a role-separated authenticated server; **plus the D-IMPL-20 primary HITL authority channel** (`ccf-hitl-queue://` Resources; `submit_hitl_action` whose input schema *is* the D-IMPL-21 field set, so an unbound call is a tool-level refusal before a submission can exist). Both proven cross-process with dim-4/dim-2 landings independently recomputed by the parent process | `tests/crossproc/test_experience_edge.py`, `tests/crossproc/test_hitl_mcp.py`; `tests/invariants/test_mcp_role_separation.py` (+6 rows, additions only: module/import separation, scheme ownership, no-graph-import scans for both new roles cross-checked against egress, artifact, and each other) | A front-door address confused with an egress or artifact address in a replay record (the T-06-16 split extended to roles 3 and 4); a privileged path in the experience module (it imports no factory, no Control Plane, no agents, no graph package — source-grep-asserted by the test); a pending HITL event consumed by a refused submission |
| 15 | **HTTP API skeleton (EXPR-03): the D-IMPL-22/23 ruled noun set exactly, OpenAPI 3.1.0 generated from the existing `extra=forbid` contracts, no ingest/L1/write path, product read-only** — the noun-set assertion is parsed from the D-IMPL-22 ruling text in `docs/DECISIONS.md`, so drift between ruling and surface is a red test, not a review catch | `tests/http_api/test_routes.py` (with `test_openapi.py`, 34 tests: set-equality, forbidden paths, contract round-trips, typed-4xx-vs-opaque-5xx refusal line, OpenAPI validity + exact auth-posture string equality, and the two D-IMPL-62 receipt cases of row 17) | A route outside the ruled noun set; a write door onto L1 (the single-writer invariant's front-door leg); an OpenAPI document that stopped carrying the posture sentence verbatim |
| 16 | **`ccf` CLI (EXPR-02): thin client, zero privileged paths** — every verb is a pure argv→request translation to the same routes; `--local` constructs the **identical** `ApiDependencies` bundle `create_app` consumes (type-asserted: `type(bundle) is ApiDependencies`); HTTP-vs-injected equivalence proven byte-identical against a real uvicorn server; `agent declare` has no inline-definition flag to parse (T-07-29); no URL literal in the package (test-scanned). `ccf skill import` is one-way (byte-level directory snapshot equal before/after) and never maps `allowed-tools` onto requirements (D-IMPL-29, T-07-28) | `tests/cli/test_cli.py` (40 CLI tests with `test_skill_import.py`, incl. exit-code discipline 0/1/2 and the D-IMPL-62 receipt-output case of row 17) | A CLI-only ledger path (T-07-27 — this is why `/skill/revocations` was added as a route rather than a CLI shortcut, §4.3); an importer that turned a SKILL.md's `allowed-tools` into granted requirements |

### 2.1 Row-by-row basis

Every module named above ran inside the §1 whole-tree sweep (1280 passed, harnesses
mandatory), and rows 3, 5 and 7 additionally cite **measured** counterfactuals (§2.2) rather
than reasoning — the I.2 process defect (gate prose drafted from plan intent) that D-25
exists to prevent. Lint-carried rows (9, 13, and the CINV-01c leg of row 1) are covered by
`tools.lints --all` exit 0.

### 2.2 Recorded counterfactual outputs (verbatim)

**Row 3 — D-20 state-seam closure reverted** (07-02: `src/ccf/controlplane/state.py`
reverted to base `2d62b01`, then `pytest tests/invariants/test_state_seam_closure.py -q`;
file restored after, 7/7 pass on the closed seam):

```
==================================== ERRORS ====================================
_________ ERROR collecting tests/invariants/test_state_seam_closure.py _________
ImportError while importing test module '.../tests/invariants/test_state_seam_closure.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/invariants/test_state_seam_closure.py:27: in <module>
    from ccf.controlplane.state import (
E   ImportError: cannot import name 'AuditedStateWriter' from 'ccf.controlplane.state'
=========================== short test summary info ============================
ERROR tests/invariants/test_state_seam_closure.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.11s
```

**Row 7 — CINV-04 `hitl-action-capture`** (07-07: dim-2 pass-through in
`build_replay_record` replaced with the sentinel; owning test red; sever restored,
`src/ccf/replay/record.py` verified byte-identical to pre-task state):

```
_____________ test_the_human_action_lands_on_dimension_2_verbatim ______________
        block = replay.policy_bindings.hitl_actions
>       assert block == resolution.hitl_actions_block
E       assert 'no-hitl-actions' == '{"approved":..."acme-bank"}}'
E         - {"approved":true,"event":{"event_class":"approval-gate","event_key":"acme-bank/exec-1/treasury-approval",...,"product_content_hash":"547ebaff5ca906456d72083e19e5b39a8d8a3c05cdd3c83b11e11bc1ee8c57f5",...},"submission":{"action":"approve",...,"principal":{...,"approver":{"identity_provider_ref":"acme-bank/idp/okta","subject_id":"credit-officer-11"},...
FAILED tests/workflow/test_slice.py::test_the_human_action_lands_on_dimension_2_verbatim
1 failed in 0.15s
```

**Row 5 — CINV-04 `workflow-trace-capture`** (same procedure, dim-5 pass-through severed):

```
_____________ test_the_step_sequence_lands_on_dimension_5_verbatim _____________
>       assert (
            replay.content_generation_path.workflow_step_sequence
            == outcome.step_sequence_block
        )
E         - [{"kind":"transition",...,"source":"verify-payment","target":"treasury-approval"},{"kind":"suspend",...},{"kind":"resume",...,"target":"released"}]
E         + no-workflow-trace
FAILED tests/workflow/test_slice.py::test_the_step_sequence_lands_on_dimension_5_verbatim
1 failed in 0.14s
```

These are this phase's recorded-red form: assert-diff and collection-error reds, the same
evidentiary class as I.3's `DID NOT RAISE` measurements — a red observed on the broken
implementation, restored immediately, cited by the row that rests on it.

### 2.3 Post-ruling evidence rows (D-IMPL-62 hardening, D-IMPL-64 webhook — built 07-14)

Both fixes followed the same TDD discipline as every other wave: failing tests committed
first, observed red, then the implementation. The reds here are pre-implementation reds
(RED commits `b754a90` and `e107f01`), the D-25 species for new mechanism.

| # | Claim, at the strength it is enforced | Named mechanism | What would fail if broken |
|---|----------------------------------------|-----------------|---------------------------|
| 17 | **The HTTP/CLI HITL action door is submit-only and says so honestly (D-IMPL-62)** — the response is `HitlActionReceipt`, whose `status` field is **type-closed to the literal `"submitted"`** (it cannot state or imply `resolved`), whose field set is closed (`extra=forbid`: status, submission echo, `event_pending`, `submissions_for_event`), and whose disposition fields carry **real queue state**, not an echo: immediately after a submit the event is still pending, because the submit alone effects no state transition — resolution is the owning primitive's act | `src/ccf/hitl/transport.py::HitlActionReceipt`; `runtime/ccf_runtime/http_api/routes/hitl.py`; `tests/http_api/test_routes.py::test_hitl_action_receipt_states_submitted_with_honest_disposition` (+ the unqueued-event case: `event_pending` is real queue state); `tests/cli/test_cli.py::test_hitl_decide_output_states_submitted_with_disposition` | Pre-implementation red observed: `KeyError: 'status'` on the old submission-echo response. A response that implied resolution, a receipt field claiming a transition that did not occur, or disposition fields computed from the request rather than the queue |
| 18 | **The notify-only webhook transport (D-IMPL-64) carries no authority surface, by construction** — `HitlEventNotification`'s field set is exactly `{endpoint_key, event}` (no action, no principal; test-asserted); the module never imports the submission contract and the notifier exposes no `submit` (source-scanned); delivery is an **injected** `WebhookDeliveryProtocol` with `RecordingWebhookDeliverer` as the §11 reference impl; a failing endpoint is a **recorded** `WebhookDeliveryOutcome(delivered=False, error=…)` — never an exception into the authority path — and other endpoints still deliver; tenant isolation holds (D-23); duplicate endpoint keys are a typed `WebhookEndpointConflict`; endpoint registrations are typed caller-supplied values, never constants (CINV-01) | `src/ccf/hitl/webhook.py`; `tests/hitl/test_webhook.py` (9 cases: delivery + tenant isolation, failure recording, typed refusals, extra-field refusal, the three notify-only-by-construction scans, Protocol conformance) | Pre-implementation red observed: collection `ImportError` (module absent). A notification payload that grew an action or principal field; a notifier with a submit path (a notification channel becoming an authority channel — exactly what D-IMPL-20's separation forbids); a failed delivery raising into a workflow's execution path |

---

## 3. Requirement and Success-Criteria Evidence Map

| Requirement | Delivered by | Gate rows |
|-------------|--------------|-----------|
| ORCH-01 (Workflow primitive) | 07-04 (contracts + factory), 07-06 (engine), 07-07 (slice) | 1–6 |
| ORCH-02 (OrchestrationProtocol) | 07-12, 07-13 | 11–13 |
| HITL-01 (four primitives, audit-by-construction) | 07-04 (contract layer), 07-07 (ApprovalGate + CINV-04), 07-08 (remaining three) | 7–10 |
| EXPR-01 (MCP front door) | 07-09 | 14 |
| EXPR-02 (`ccf` CLI) | 07-11 | 16 |
| EXPR-03 (HTTP API + OpenAPI) | 07-10 | 15 |

All six are ticked in `.planning/REQUIREMENTS.md` with gate-row citations. The four ROADMAP
Phase 7 success criteria map: criterion 1 → rows 1–6; criterion 2 → rows 7–10 (in the D-22
template); criterion 3 → rows 11–13; criterion 4 → rows 14–16.

**Prerequisites inherited from the I.3 gate (§5 there), both discharged:**

- **D-20 (`ControlPlaneStateStore.put` audit closure)** — closed by 07-02 *before* any plan
  multiplied the call sites, exactly as the handoff required. Row 3.
- **D-IMPL-45 (`TraceCorrelationHook` onto the `harness_trace` slot)** — delivered by 07-05:
  `ccf.replay.correlation` ships `ExternalTraceProviderProtocol`, `TraceCorrelation`,
  `NoOpTraceProvider`, and `TraceCorrelationHook`, composing a provider's
  `{trace_provider, trace_id}` payload into the existing dimension-3 `HarnessTrace` fields
  **before** `build_replay_record` — no new field, dimension, or sentinel (T-07-10), no-op
  byte-identity proven (`tests/replay/test_trace_correlation.py`). One wording drift
  recorded rather than papered over: the D-IMPL-45 DECISIONS entry says "dimension 5"; the
  later D-IMPL-55 ruling and the I.3 gate §5 both place the slot at dimension 3, and the
  implementation follows them (07-05 SUMMARY, informational deviation).

**The 07-13 Claude feasibility probe — the phase's largest external risk — returned GO**, so
the escalation artifact the plan pre-defined was never filed. All three load-bearing
surfaces were expressible: SDK-MCP tool routing for node advancement, the hook surface
(`CanUseTool` + `PostToolUse`) intercepting the hitl-gate with the engine's own suspend
handle obtainable driver-side, and same-session resume to the `released` terminal. The one
honest caveat, carried in the SUMMARY's own words: the driver runs the real
`ClaudeSDKClient` session machinery over the SDK's **public, exported** custom `Transport`
seam with a scripted in-process wire — no model, no network, no CLI (the D-09 discipline,
same species as the harness conformance suite's choice for all three SDKs). The scripted
side plays only the wire's role; tool timing for a deterministic workflow drive is not a
model decision, because replay equivalence would forbid one.

---

## 4. Discretionary In-Phase Choices, Residual Risks, and the Deviations Register

### 4.1 Residual risk — the v0 HTTP surface is unauthenticated (T-07-24, accepted)

Stated verbatim, as served in the OpenAPI `info.description` and string-equality-asserted
by test:

> "This API performs no authentication or authorization in v0: every request acts with the
> full authority of the injected fabric handles, it must be deployed inside the tenant trust
> boundary, and any future authentication is a new contract, not a configuration of this
> one."

**This is recorded as a residual deployment risk, not a closed item** (Codex finding,
07-10). HITL actions and workflow invocation are authority-bearing surfaces; the acceptance
rests entirely on the in-trust-boundary deployment assumption. Contrast: the two MCP-role
servers this phase added (experience, HITL) **are** authenticated with the required D-26
verifier+settings pair — the asymmetry is deliberate and visible, not an oversight: the
MCP surfaces are the D-IMPL-20 *primary* authority channel; the HTTP skeleton is the
D-IMPL-23 minimal service-integration surface whose auth hooks are a future contract.

### 4.2 Webhook notify-only leg — deferral REJECTED by D-IMPL-64; shipped in-phase

The 07-08 deferral (single-owner rationale in its SUMMARY: authority never flowed through
the webhook leg in any design revision — every human action returns through the typed
`HITLTransportProtocol` queue; a notify-only emitter is a pure observer) was surfaced as
D-IMPL-64 by the gate review, and **Dave rejected the deferral (2026-07-30): the ruled
notify-only webhook transport ships in v0, this phase.** It was built in 07-14
(`src/ccf/hitl/webhook.py`; row 18, §2.3) preserving exactly the properties the 07-08
rationale named: authority never flows through the webhook — the notification payload has
no authority surface by construction, and the notification-infrastructure choices the SDK
has no business making (HTTP client, retries, signing, endpoint registry) stay outside the
SDK behind the injected `WebhookDeliveryProtocol` seam, with endpoint registrations as
typed caller-supplied values. `DESIGN.md` §5's 07-14 deferral correction is superseded by
the ruling; the shipped surface now matches D-IMPL-20's original "two reference
transports" text.

### 4.3 Other discretionary choices (in-phase judgment, not new D-IMPL entries)

1. **FastAPI pin vs google-adk constraint (Cursor note).** `fastapi==0.140.0` is a direct
   pin (stated reason: D-IMPL-23 OpenAPI generated from the existing `extra=forbid`
   contracts) and sits inside google-adk 2.5.0's declared `fastapi>=0.133` range —
   compatible today, but the exact pin means a future google-adk floor bump surfaces as a
   resolver conflict rather than a silent upgrade. That is the intended failure mode
   (stated-reason pins over ranges); recorded so the conflict, when it comes, is read as
   the pin doing its job.
2. **Module tree.** Orchestration drivers under `runtime/ccf_runtime/orchestration/<sdk>/`
   (D-IMPL-60's ruled placement, never under `adapters/`); the workflow engine and its
   state record in `runtime/ccf_runtime/workflow/` (Open Question 2 resolved in module
   docstrings: contracts sync in `/src` per 07-04, engine and record `/runtime` per D-14
   and record-next-to-the-machine); HITL primitives in `src/ccf/hitl/`; the two new MCP
   roles as separate modules with their own URI schemes (`experience.py`,
   `hitl_server.py`); HTTP API under `runtime/ccf_runtime/http_api/` with
   closure-based per-noun routers; CLI under `runtime/ccf_runtime/cli/`.
3. **ApprovalGate / ApprovalSinkAdapter composition rationale (07-07).** The async gate
   owns transport, suspension, and binding; a thin adapter wraps an already-completed bound
   `GateResolution` for the sync `ApprovalSink` seam — because one object honestly doing
   both faces would have to lie when no human has acted (`decide()` can neither block on a
   pending human nor fabricate a verdict; unbound it raises typed `UnboundDecisionError`).
   The `GrantLedger` state machine is byte-untouched and still owns every transition —
   "joins with zero state-machine change" honored as property-preserving composition.
4. **Engine node bindings are injected Protocols** (`SkillNodeBinding`,
   `AgentNodeBinding`), not direct imports of skill dispatch or a harness adapter — the
   composition root binds both seams; the engine names neither, so harness-neutrality at
   agent nodes is structural (07-06).
5. **CLI verbs mirror HTTP routes exactly; missing routes were added rather than a CLI-only
   path invented** (07-11 Rule-2 additions: `/skill/revocations`, POST `/skill/catalog`,
   `/config/registrations`) — the thin-client posture (T-07-27) preserved by widening the
   wire surface, never the client.
6. **D-IMPL-56 executed as ruled** (07-03): required `description` + typed
   `SkillArgumentSchema` with no default and no sentinel; the fifth `procedure` type is
   seam-1-only, enforced at the shared derivation (`ProcedureHasNoToolSurface`), not left
   to adapter discipline; all three adapters consume one `render_tool_surface`, pinned by
   a three-way equality test over real harness tool objects.

### 4.4 Deviations register (D-24: expect ~one per plan; all recorded in plan SUMMARYs)

| Plan | Deviation | Class |
|------|-----------|-------|
| 07-01 | Stale transitive-dependency comment corrected when httpx became a direct pin | Rule 1 (untrue-comment class) |
| 07-02 | **D-09 "8 grant call sites" count**: `grants.py` has exactly **one** textual `_state_store.put` site; eight *logical* transitions flow through it — all eight `_put_state` call sites updated to carry their domain event, the single textual writer retrofitted (pre-flagged; the gate carries this row per Ollama C3). Also: `AuditEvent.sequence` is assigned by the log per the log's own stated contract — the writer appends the caller's event verbatim in every other field | D-24 stale-belief; Rule-1-adjacent |
| 07-03 | Task 3's fixture sweep executed inside Task 1's GREEN commit (required fields break fixture loading immediately); schema-lane-only version bump with recorded rationale | Rule 3; versioning discipline |
| 07-04 | None — two in-flight test-authoring fixes inside the TDD loop only | — |
| 07-05 | Byte-identity test's strip set extended for the new sentinel fields (the must_have explicitly allows it); **D-IMPL-45 wording drift** recorded: the DECISIONS entry says "dimension 5", the D-IMPL-55 ruling and I.3 gate place the slot at dimension 3 — implemented against dim 3 per the plan and handoff, drift recorded rather than silently resolved | Rule 3; informational |
| 07-06 | Milestone-2 surface landed with milestone 1 (investigated per fail-fast); node bindings as injected Protocols; two fixture artifacts added beyond the file list (No-Hardcoding forbids inline definitions) | task-structure; design resolution; Rule 2 |
| 07-07 | `hitl_action` AuditAction member added (recording a human verdict under `workflow_*`/`grant_*` would make the log lie); CINV-04 deferral machinery removed rather than emptied (an empty parametrize itself emits a skip) | Rule 2; Rule 3 |
| 07-08 | None — the Cursor-flagged risk (no D_c condition surface) did not materialize | — |
| 07-09 | None — test plumbing note only (`run_with_session` in place of a client lacking `http_client_factory`) | — |
| 07-10 | Route walk via `app.openapi()` paths — FastAPI 0.140 keeps included routers lazy (`_IncludedRouter`), so `app.routes` can never enumerate noun routes | Rule 3 |
| 07-11 | Three Rule-2 route additions (§4.3 item 5); `RefuseEmptyBump` tolerance on unchanged reference re-imports (typed discriminant, not prose matching); editable reinstall deferred to post-merge (shared venv) | Rule 2; Rule 1; deferred |
| 07-12 | Worktree base drift corrected at startup; two minor placements within plan intent | Rule 3; minor |
| 07-13 | Worktree base drift corrected; **google-adk 2.5.0 deprecates `SequentialAgent`** (used per the plan's verified-interface ruling; warnings only; logged to `deferred-items.md` for the next pin bump — migration is mechanical); package docstrings reworded to keep a literal acceptance grep at zero | Rule 3; note; minor |

### 4.5 Rejected review suggestions (recorded with rationale, not silently dropped)

| Suggestion | Disposition |
|------------|-------------|
| Ollama S7 — forbid policy-flavored words ("policy", "threshold", "risk") in CLI `help=` strings | **Rejected.** Those words are *mechanism vocabulary* in this SDK's surface (`gate_policies`, D_c thresholds, policy regimes are Control Plane concepts the CLI must name to be usable); a word ban would forbid accurate help text while catching no actual CINV-01 violation — the lint's AST checks already catch real hardcoded values |
| Ollama S8 — add a light performance benchmark (`timeit` the engine on a 10-step workflow) | **Deferred**, per CLAUDE.md §15: "Performance-tradeoff question: Phase I problem. Defer." A rough non-asserted figure in CI is either flaky (asserted) or dead weight (not); adoptability evidence is the Phase 8 examples suite's job |

### 4.6 DESIGN.md staleness corrections (made in this plan, recorded here)

Checked §4 (Orchestration) and §5 (HITL) against what shipped; four corrections, each
marked inline as a Phase I.4 correction:

1. **Workflow signatures**: the pre-implementation `WorkflowNode ::= …` /
   `WorkflowExecutionState{…variable_bindings…}` sketch annotated with the as-shipped shape
   (wrapper over a pinned TaskDefinition; `WorkflowFactory`; `WorkflowStateRecord` in
   `/runtime`; no `variable_bindings` in v0).
2. **Exception-path invariant**: "every node declares an exception path" corrected to the
   D-IMPL-61 ruling (absent ref = audited propagate-to-terminal; let-it-fail expressible).
3. **OrchestrationProtocol signatures**: annotated with the as-shipped verbs, the
   factory-handle boundary, and the D-IMPL-60 four-leg reality.
4. **Webhook transport**: "two reference transports ship" corrected — the notify-only
   webhook emitter is deferred from v0 per 07-08 (§4.2); the structural argument's item 4
   annotated accordingly.

### 4.7 D-22 phrase sweep over this document

Every criterion-2 row uses the template (grep this document for "type-unrepresentable" —
present in rows 3 and 7 and the header). The absolute CLAUDE.md §8.2 sentence appears
exactly twice, both as marked quotations (the header note and criterion 2's preamble);
no row asserts it at that strength.

---

## 5. Handoff to Phase I.5 (Phase 8)

- **Advisory A3 is Phase 8's, named as such since the I.3 gate**: the Claude *harness
  adapter's* seam-4 `execution()` remains a hand-built `ResultMessage`; whoever writes
  `examples/03-harness-portability` owns replacing it with a real SDK-driven execution.
  Nothing in I.4 changed its status. (The I.4 *orchestration* Claude leg is a different
  surface and runs real `ClaudeSDKClient` session machinery — §3 — but that does not
  discharge A3, which lives on the adapter seam.)
- **Loop-level harness portability** (§7.3's "one agent definition running unmodified under
  at least two harnesses") remains `examples/03`'s obligation — outstanding, per the I.3
  gate §3.3.1, unchanged by this phase.
- **Examples 05 and 06 are Phase 8 deliverables** (D-04): the mechanism they exercise —
  workflow + ApprovalGate suspend/resume with a replay-recorded human action (05), and
  full replay resolution from the ArtifactStore (06) — is delivered and test-proven here
  (rows 5–8; the crossproc fixtures already drive replay records through `ReplayWriter`
  over a `FileArtifactStore`); the examples are packaging + demonstration, not new
  mechanism.
- **`SequentialAgent` deprecation** (google-adk 2.5.0, `deferred-items.md`): revisit at the
  next google-adk pin bump; migration is mechanical (the driver's sub-agents are plain
  `BaseAgent` subclasses).
- **Post-merge `pip install -e .`** materializes `.venv/bin/ccf` (07-11 deferred it from a
  shared-venv worktree); until then the entry point is exercised as
  `python -m ccf_runtime.cli.main`.
- **Unaudited state *reads*** (07-02 open observation): `ControlPlaneStateStore.items`
  allows unaudited enumeration of current state (not history); this does not undermine the
  write-closure claim — nothing can *change* without a record — and widening to read
  auditing would be a new ruling, not a follow-up.
- **T-07-24** (§4.1) travels forward as an accepted residual until an auth contract is
  ruled for the HTTP surface. Per the D-IMPL-62 ruling, no new auth surface was forked —
  the honest-contract hardening changed what the response *says*, not who may say it.
- **D-IMPL-63 (ruled deferral, named follow-up scope):** the two D-IMPL-21 reference
  identity-binding implementations (auth-context-derived principal; JWS-signed binding
  reusing D-IMPL-15) are **explicit follow-up-phase scope**. Caller-supplied principal
  fields are the recorded v0 posture, consistent with the unauthenticated v0 HTTP surface.
- **D-IMPL-65 (named next-phase engine commitment):** the engine will refuse an
  agent-node handoff with no bound debt assessment. Scheduled scope, not an indefinite
  posture; the v0 gate closes on composition-root debt-cascade wiring.

---

## 6. What Dave Is Asked To Decide

The four OPEN rulings this section previously asked for were **ruled on 2026-07-30**
(recorded in `docs/DECISIONS.md`): D-IMPL-62 — submit-only with honest-contract hardening
(implemented, row 17); D-IMPL-63 — identity-binding reference impls deferred to named
follow-up scope; D-IMPL-64 — deferral rejected, webhook transport implemented (row 18);
D-IMPL-65 — composition-root now, engine commitment next phase. What remains is the gate
itself:

1. Read §1 (the post-ruling sweep — **1280/0/0** with harnesses mandatory, mypy 152
   files, lints clean, and the zero-skip milestone that closes CINV-04), §2 (eighteen rows
   across the four criteria — for any row that reads as a claim rather than evidence, run
   the test it names), §2.2–§2.3 (the measured counterfactuals and the two post-ruling
   TDD reds), §3 (requirements map, the two discharged I.3 prerequisites, the GO probe),
   §4 (residual risks — **the unauthenticated HTTP surface first** — the deviations
   register, the two rejected suggestions, the DESIGN.md corrections, and §4.2's
   ruling-superseded webhook disposition), §5 (the Phase 8 handoff, now carrying the
   D-IMPL-63 deferral and the D-IMPL-65 engine commitment as named scope), §7 (the review
   report, triage, and ruling outcomes).
2. Optionally re-run, from the repository root with the project interpreter:
   `CCF_REQUIRE_HARNESSES=1 PYTHONPATH=src:runtime .venv/bin/python -m pytest -q &&
   .venv/bin/python -m mypy && PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all`
   (expect **1280 passed, 0 skipped**; mypy 152 files; lints exit 0).
3. Confirm the four ROADMAP Phase 7 criteria against their rows (§3's mapping).
4. **Approve or reject the Phase I.4 gate.** Approval authority is Dave's alone; the
   review passing is necessary, never sufficient.

On approval — and only on approval — the `D-GATE-I.4` entry is appended to
`docs/DECISIONS.md` with the date, and `phase-i4` is merged into `main` with `--no-ff`, the
merge commit referencing the gate entry (CLAUDE.md §2.2, §3.1 step 4). Phase 8 begins after
both, and not before.

---

## 7. Review Appendix — §3.1 Cross-AI Review and Triage (2026-07-30)

Reviewers: **Codex** (API-key auth, `codex exec`, read-only instruction) and **Cursor**
(`cursor agent -p --mode ask`), both run against the phase deliverables (this gate document
plus the shipped `workflow`/`hitl`/`orchestration`/front-door trees) with the sweep facts
supplied. Findings below are numbered `C-n` (Codex) and `X-n` (Cursor). Every finding was
**verified against the code before triage** — none was accepted or dismissed on the
reviewer's say-so alone.

### 7.1 Disposition table

*(Rows marked "(OPEN), stop" record the triage as it stood at the checkpoint; all four
entries were ruled 2026-07-30 — see §7.4 for the rulings and their in-phase consequences.)*

| Finding | Substance | Class | Disposition |
|---------|-----------|-------|-------------|
| X-1 / C-2 (partial) | `POST /hitl/actions` + `ccf hitl decide` submit to the transport without a primitive `resolve` or dim-2 landing; the MCP HITL child, by contrast, drives gate resolve + replay write | **Blocking — ruling required** | Verified true (`routes/hitl.py` calls `submit` only; a submit alone effects no state transition and no authority action — the action becomes effective, and recorded, at primitive resolution). Whether the v0 door is submit-only by design or must compose a per-event-class resolve is a design ruling → **D-IMPL-62 (OPEN), stop** |
| X-2, X-5 | `WorkflowEngine.resume` takes a bare decision; DESIGN §5 structural args 2–3 stated engine-side enforcement that is composition-root responsibility as shipped | **Blocking — fixed in-phase (docs) + folded into D-IMPL-62** | DESIGN §5 args 2 and 3 corrected to as-shipped scoped statements; the engine-enforced-precondition question recorded under D-IMPL-62 |
| X-3 / C-4 | Row 7 / CINV-04 overclaimed per-primitive replay coverage: only the ApprovalGate slice drives `build_replay_record`; escalation/override/review are covered compositionally | **Blocking — fixed in-phase** | Row 7 narrowed to state the composition precisely (primitive-side byte-equality ∘ builder verbatim-landing guarantee); CINV-04 registry gained an explicit D-22 quotation-marking and scope comment |
| X-4 | Row 6 claimed exception-path "resolution on dim 2"; the named test asserts block production and the dim-5 landing, not a dim-2 drive | **Blocking — fixed in-phase** | Row 6 narrowed to what the test asserts |
| X-6 / C-1 | Webhook notify-only transport is a ruled D-IMPL-20 deliverable deferred without a decision-log entry | **Blocking — ruling required** | Verified true against D-IMPL-20's text → **D-IMPL-64 (OPEN), stop** (ratification ask; the 07-08 rationale carried intact) |
| C-2 | D-IMPL-23 rules the API "adds … auth hooks"; shipped surface performs no auth (T-07-24) | **Blocking — ruling required** | Verified true → folded into **D-IMPL-62 (OPEN)** with the posture sentence and residual-risk row (§4.1) unchanged |
| C-3 | D-IMPL-21's two reference identity-binding impls (auth-context-derived principal; JWS-signed binding) did not ship; principal fields are caller-supplied | **Blocking — ruling required** | Verified true (row 7's type-unrepresentable leg holds; the *binding-to-authenticated-context* leg does not exist) → **D-IMPL-63 (OPEN), stop** |
| C-5 | D-22 absolute wording in load-bearing artifacts outside marked quotations: `src/ccf/hitl/__init__.py` docstring; CINV-04 registry "every … by construction" strings | **Blocking — fixed in-phase** | Docstring rewritten as marked quotation + scoped statement; registry strings marked as CLAUDE.md quotations with the enforcement scope stated in an adjacent comment (the strings themselves are unedited quotations, per the I.3 §4.9 rule against rewriting quotations) |
| X-7 | DESIGN §4 lists INV-CH7-68 per-handoff debt cascade as an enforced Workflow invariant; the engine performs no per-handoff recomputation | **Blocking — ruling required** | Verified true (`assess_debt`/`DebtProfile` exist and drive ExceptionEscalation; no engine handoff check) → DESIGN §4 corrected + **D-IMPL-65 (OPEN), stop** |
| X-8 | Absolute "unbypassable" in §4.2 outside a quotation | Advisory (fixed anyway) | Reworded, scoped to rows 7–8 |
| X-9 | REQUIREMENTS evidence-row mis-citations (ORCH-01, HITL-01) | Advisory (fixed) | Corrected to rows 1–6 / 7–10 |
| C-6 | REQUIREMENTS CINV-04 row still "Pending" despite the deferrals being discharged | Advisory (fixed) | CINV-04 ticked with evidence; the remaining stale Phase-4 "Pending" traceability rows predate this phase and are **carried forward** as planning-doc staleness, not silently rewritten at gate wave |
| X-10 | D-IMPL-18's `variable_bindings` member absent from the shipped `WorkflowStateRecord`, noted openly but without a DECISIONS amendment | Advisory — carried | Recorded here; the record shape is the D-IMPL-18-consistent minimal set (state, status, trace, pinned URI); if Dave reads it as a ruled-member omission it joins the D-IMPL-62 ruling batch |
| X-11 | DESIGN Transport blurb said MCP "serves … the `ccf hitl` CLI"; the shipped CLI is an HTTP thin client | Advisory (fixed) | DESIGN corrected; the D-IMPL-20 ruled-text tension recorded under D-IMPL-62 |
| X-12 | ROADMAP criterion-4 "MCP server egress" vocabulary vs the shipped Experience-role server | Advisory — carried | Functionally aligned per the I.3 A5 amendment pattern; wording drift noted, not amended (ROADMAP criterion text is presented to Dave as-is) |
| X-13 | Accepted residuals already disclosed (T-07-24, unaudited state reads, `SequentialAgent` deprecation, examples 05/06 per D-04) | Advisory — carried | Already in §§4–5 |
| C — non-findings | Cursor's "what holds" list: harness neutrality in the new `/src` trees, no HTTP write door onto L1, factory path + CINV-01c, four-leg conformance surface | — | Recorded as corroboration |

*(Codex's first run could not access the repository — its sandbox network shim
(`bwrap`) is unavailable in this environment — and returned no findings; it was re-run
without the sandbox under an explicit read-only instruction. Recorded per the §1.1-class
discipline from I.3: a review that could not see the tree is not a passing review.)*

### 7.2 What was fixed in-phase (this plan, post-review)

Row 6 and row 7 narrowed; §4.2 reworded; `src/ccf/hitl/__init__.py` docstring rewritten to
the quotation + D-22 scope form; CINV-04 registry quotation-marking comment added
(comment-only — no test logic touched; suite re-verified green after, §7.3);
DESIGN.md §4 (debt cascade) and §5 (structural args 2–3, transport blurb) corrected;
REQUIREMENTS citations and CINV-04 status fixed. All recorded per-file in this plan's
commits.

### 7.3 Post-fix verification

The full sweep was re-run after the in-phase fixes (the only non-doc edits are docstring/
comment changes in `src/ccf/hitl/__init__.py` and
`tests/invariants/test_replay_by_construction.py`): **1268 passed, 0 skipped**, mypy clean
(151 files), `tools.lints --all` exit 0.

### 7.4 The §3.1 stop — and its resolution

Four blocking findings could not be fixed without rulings Dave had not made. Per §3.1 they
were logged as **D-IMPL-62..65 (OPEN)** and the phase **stopped** at the gate checkpoint.
**Dave ruled on all four on 2026-07-30** (full rulings in `docs/DECISIONS.md`):

| Entry | Ruling | In-phase consequence |
|-------|--------|----------------------|
| D-IMPL-62 | Submit-only with honest-contract hardening; MCP resolve-wiring is a ruled asymmetry; auth stays on T-07-24's residual entry | `HitlActionReceipt` implemented, TDD (row 17, §2.3) |
| D-IMPL-63 | Deferred — identity-binding reference impls are explicit follow-up-phase scope; caller-supplied principal fields are the v0 posture | Handoff entry, §5 |
| D-IMPL-64 | Deferral **rejected** — notify-only webhook transport ships in v0, this phase | `ccf.hitl.webhook` implemented, TDD (row 18, §2.3) |
| D-IMPL-65 | Composition-root wiring closes this gate; engine refusal of an unbound-debt agent-node handoff is a named next-phase commitment | DESIGN §4 note updated; handoff entry, §5 |

The full sweep was re-run after both implementations: **1280 passed, 0 skipped**, mypy
clean (152 files), `tools.lints --all` exit 0. `D-GATE-I.4` remains unwritten until Dave
approves the gate itself (§6).

---

## 8. Post-merge status addendum (Phase 7.1, D-IMPL-66(e))

**D-GATE-I.4 was approved on 2026-07-30 by Dave** and is logged in
`docs/DECISIONS.md` under the `D-GATE-I.4` entry. Per CLAUDE.md §2.2/§3.1 step 4,
`phase-i4` was merged into `main` with `--no-ff`, the merge commit referencing that
entry: `60f5192 chore: merge phase-i4 to main — Phase I.4 approved (D-GATE-I.4)`.

The load-bearing D-26 post-merge sweep, run on `main` after the merge:

| Leg | Result |
|-----|--------|
| `CCF_REQUIRE_HARNESSES=1 python -m pytest -q` | **1280 passed / 0 skipped / 0 failed** |
| `python -m mypy --strict` | clean over **152 source files** |
| `python -m tools.lints --all` | exit 0, zero findings |

§7.4's closing sentence ("`D-GATE-I.4` remains unwritten until Dave approves the gate
itself (§6)") describes the pre-approval state as it stood at the §3.1 checkpoint and is
**superseded by this addendum**; the historical text of §1–§7 is deliberately unedited —
this section is append-only.
