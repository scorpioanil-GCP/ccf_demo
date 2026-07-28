# Phase I.2 — Agent Specialization Framework: Gate Package

**Phase:** 5 (Phase I.2 — Agent Specialization Framework) · **Branch:** `phase-i2` · **Assembled:** 2026-07-26
**Protocol:** CLAUDE.md §3.1 (self-review → triage → present to Dave → `D-GATE-I.2` → merge)
**Gate bar:** D-17 pattern carried from I.1 — the per-invariant checklist green, each named
invariant mapping to a *named passing* test or lint. No numeric coverage gate.

> **Status: GATED AND MERGED.** `D-GATE-I.2` approved by Dave 2026-07-26
> (`docs/DECISIONS.md`); `phase-i2` merged to `main` `--no-ff` at `ba0088e`.
>
> This document was assembled as the plan 05-07 deliverable and originally read
> "AWAITING REVIEW" — accurate when written, stale once the gate closed. Two
> cross-AI reviewers (Codex, Cursor) independently caught the drift in the
> retrospective review; see `05-REVIEWS.md` finding A5.
>
> **Evidence-section counts below are point-in-time snapshots, not the final
> state.** §1 records 568 passed and §3 records 577 — the counts at those
> waves. The phase closed at **627 passed / 2 skipped**, mypy `--strict` clean
> across 80 files, `tools.lints` exit 0, verified independently on `main` after
> the merge. `05-VERIFICATION.md` is the authoritative outcome record.
>
> **Protocol note.** §3.1 step 1 calls for `/gsd-review --phase <Phase> --all`
> *before* presentation to Dave. Phase I.2's gate used `/gsd-code-review`
> instead; the cross-AI review was run retrospectively and is recorded in
> `05-REVIEWS.md`. Its findings are advisories carried into Phase I.3 — they
> did not and cannot alter this gate.

---

## 1. Verification Evidence — Execution Record

All legs executed on `phase-i2` in the project `.venv` (Python 3.12), 2026-07-26.

| Leg | Command | Result |
|-----|---------|--------|
| Full suite | `.venv/bin/pytest tests/ -q` | **568 passed, 2 skipped** (exit 0) |
| Invariant registry, skip detail | `.venv/bin/pytest tests/invariants/ -rs -q` | **15 passed, 2 skipped** — the only skips in the whole suite, both CINV-04 deferrals (below) |
| Strict typing | `.venv/bin/mypy --strict src` | **Success: no issues found in 63 source files** |
| Invariant lints (CINV-01a/b/c, CINV-02, CINV-03) | `.venv/bin/python -m tools.lints` | **exit 0, zero findings** |
| Allowlist discipline | `git log --oneline -- tools/lints/allowlist.yaml` | last touched `ab7b7eb` (Phase 4, plan 04-02) — **no cinv01c allowlisting occurred this phase** |

**The 2 skips are deliberate and load-bearing (D-10).** I.1 ended with 3 phase-tagged
CINV-04 skips; I.2 activated `skill-set-capture`, leaving exactly the two I.4 deferrals:

| Skipped check | Activating phase | Reason string emitted |
|---------------|------------------|------------------------|
| `hitl-action-capture` | **Phase I.4** | every HITL action lands in replay dimension 2 by construction (CLAUDE.md §8.2) |
| `workflow-trace-capture` | **Phase I.4** | every workflow execution trace lands in replay dimensions 4 and 5 by construction (CLAUDE.md §8.1) |

### RESEARCH Open Question 4 verification (RESOLVED as ruled)

D-11 ships the task **schema + construction only** — no task-execution replay capture is
invented in I.2. Verified two ways:

- `grep -rn "task" src/ccf/replay/record.py` → **empty** (no TaskDefinition or
  task-execution capture field exists in the replay record).
- `tests/agents/test_factory.py::test_no_replay_capture_is_invented_for_tasks` asserts it
  behaviorally, so the boundary cannot regress silently.

### Fixture-only boundary spot-checks (all must be, and are, empty)

| Spot check | Command | Result |
|------------|---------|--------|
| No domain values in the agent/skill mechanism | `grep -rin "covenant\|banking\|kyc" src/ccf/agents src/ccf/skills` | **empty** (exit 1) |
| No template rendering in I.2 (D-13: parse-only) | `grep -rn "\.render(" src/ccf` | **empty** (exit 1) |
| No harness imports anywhere in `/src` | `grep -rn "import adk\|langgraph\|claude_agent" src/` | **empty** (exit 1) — corroborating the CINV-02 lint's zero findings |

Every agent instance, prompt, threshold, half-life value, skill grant, and policy scope in
this phase lives under `tests/fixtures/banking/` (agents/, prompts/, tasks/, skills/) —
never in `/src`. Nothing was fixed silently to produce these results; every leg passed on
first run.

### D-04 wave-organization conformance

The executed wave order matches the ruled pillar-concern sequence exactly:
**(a)** archetypes + composition — plans 05-02/05-03 (foundations in 05-01);
**(b)** factory hardening — plan 05-04;
**(c)** skill catalog + governance + replay capture — plans 05-05/05-06;
**(d)** gate wave — plan 05-07 (this document).

---

## 2. Per-Invariant Checklist (D-17 pattern; invariants touched or activated in I.2)

| # | Invariant | Named verification mechanism | Result |
|---|-----------|------------------------------|--------|
| 1 | **No-Hardcoding — prompt-shaped literals** | Lint rule `cinv01a-prompt-shape` (`tools/lints/no_hardcoding.py`), run by `python -m tools.lints`. All prompts live in `tests/fixtures/banking/prompts/*.yaml`, referenced by versioned URI (axis 6, D-13 parse-only) | ✅ zero findings |
| 2 | **No-Hardcoding — numeric tables/thresholds** | Lint rule `cinv01b-numeric-table` (same module). Half-life/debt profiles, governance scopes, and task refs all live in fixture YAML | ✅ zero findings |
| 3 | **No-Hardcoding — factory bypass (CINV-01c, activated this phase per D-12)** | Lint rule `cinv01c-factory-bypass` + the behavioral fixture suite `tests/lints/test_cinv01c_behavioral.py` — `::test_agent_construction_outside_a_factory_fires_the_lint`, `::test_task_construction_outside_a_factory_fires_the_lint`, `::test_a_module_level_alias_of_a_factory_only_name_is_caught`, `::test_the_real_tree_yields_zero_factory_bypass_findings`. The lint is proven to *fire* on bypass, not merely to stay silent | ✅ zero findings on the real tree; positive-detection fixtures pass |
| 4 | **Zero harness imports in core (CINV-02)** | Lint rule `cinv02-harness` (`tools/lints/harness_imports.py`) over `/src`; corroborated by the §1 grep. The D-03 harness test double lives in `tests/agents/harness_double.py`, outside `/src` | ✅ zero findings |
| 5 | **Algorithmic ⇄ Semantic Alternation (CINV-03)** | Lint rule `cinv03-algorithmic` (`tools/lints/algorithmic.py`). Every I.2 module declares `__ccf_mode__ = "algorithmic"` (D-13: no LLM invocation anywhere in the phase); Jinja2 use is `Environment.parse` + `meta.find_undeclared_variables` only | ✅ zero findings |
| 6 | **Replay-by-construction — skill-set capture (CINV-04, ACTIVATED this phase per D-10)** | Registry entry `skill-set-capture` in `tests/invariants/test_replay_by_construction.py`, `status="active"`, owning test `tests/integration/test_agent_slice.py::test_a_granted_decision_captures_the_grant_set_hash_in_dimension_4`. Registry integrity check asserts the owning test exists; suite skips dropped 3 → 2. Mechanism after gap closure (CR-01/WR-01, plans 05-08/05-09): `grant_set_hash` is a **required** keyword argument to `Agent.perspective_conditioning` — no silent no-grants default — and a false `NO_GRANTS_SET_HASH` claim on an agent holding effective grants is refused with `FalseGrantClaimError`; the ledger's `grant_set_hash(agent_definition_hash)` is computed per-agent over exactly that agent's effective grants (D-07), so a grant to another agent sharing the ledger never moves it | ✅ active and passing |
| 7 | **Audit-by-construction for grants** | `tests/skills/test_grants.py::TestAudit::test_every_transition_lands_in_the_audit_log_with_the_injected_clock`, `::test_a_tier_1_refusal_is_audited_as_unresolved`, `::test_a_sink_rejection_is_audited_with_the_approver_as_actor` — every `GrantLedger` state transition, including refusals, writes a `grant_*` `AuditEvent`. Mechanism after gap closure (WR-07, plan 05-09): `ControlPlaneRegistry` accepts an injected `AuditLog` and composition sites hand the **same instance** to the `GrantLedger`, so registration and grant-lifecycle events share one log, one sequence, one clock (whitepaper §7.8.2 — the Control Plane is the audit plane, singular); a conforming `ApprovalSink` cannot drop the obligation (the ledger owns the write) | ✅ passing |
| 8 | **Tier-1 policy-compatibility check is non-waivable (D-IMPL-29)** | `tests/skills/test_grants.py::test_excess_scopes_are_refused_naming_the_excess_identifiers`, `::test_excess_context_products_are_refused_naming_the_excess`, `::test_a_missing_policy_regime_refuses_rather_than_defaults`, `::test_tier_1_refuses_before_tier_2_is_ever_consulted` | ✅ passing |
| 9 | **Single-writer across the agent boundary** | `tests/agents/test_consumption_discipline.py::test_agents_modules_import_only_the_consumption_surface` (import allowlist guard over `ccf.agents`), `::test_the_agent_public_surface_holds_no_write_surface_object`, `::test_agent_methods_accept_only_typed_context_products`. No module in this phase acquires a `GraphWriter`; the I.1 static gate `cinv02-graph-writer` remains green | ✅ passing; lint zero findings |
| 10 | **D-05 version discipline (hash-verified bump)** | `tests/controlplane/test_hash_verified_bump.py` — all seven cases (idempotent re-registration, changed-content-without-bump refused, bump-without-change refused, refusals as contract values, every outcome audited); plus the six-axis matrix, row 12 | ✅ passing |
| 11 | **D-07 grant-set determinism** | `tests/skills/test_grants.py::test_the_module_function_is_exactly_content_hash_over_the_frozenset`, `::test_the_hash_is_deterministic_across_arrival_orders`, `::test_revocation_restores_the_prior_hash`, `::test_the_agent_definition_hash_is_unchanged_across_grants` — `grant_set_hash = content_hash(frozenset(active grant hashes))`, order-free, identity-preserving | ✅ passing |
| 12 | **Six-axis versioning — any axis change is a new agent version visible in replay** | `tests/agents/test_factory.py::test_every_axis_mutation_produces_a_distinct_content_hash`, `::test_every_unbumped_axis_change_is_refused_at_registration`, `::test_a_bumped_axis_change_lands_in_dimension_four` — the full matrix over all six specialization axes | ✅ passing |
| 13 | **D-IMPL-19 archetype composition rules** | `tests/agents/test_composition.py` — dedupe (`::test_identical_obligations_appear_once`), declaration-order conflict resolution with a recorded fact (`::test_conflicting_defaults_resolve_by_declaration_order`, `::test_the_factory_warns_on_an_order_resolved_default_conflict`), typed hard-contradiction failure (`::test_a_hard_contradiction_is_a_typed_error`, `::test_a_contradiction_fails_factory_construction`), purity/order-sensitivity (`::test_composition_is_pure_and_order_sensitive`) | ✅ passing |
| 14 | **ApprovalSink Protocol conformance (D-09 — I.4's ApprovalGate joins unchanged)** | `tests/conformance/test_approval_sink.py` — factory-parametrized structural-conformance suite (typed outcome, rejection-as-value, auditable outcome) | ✅ passing |

**Every invariant touched or activated in I.2 has a row above, and every row names an
existing, passing test `file::function` or lint rule id.** The D-17 gate bar is met.

---

## 3. Success-Criteria Evidence Map (ROADMAP Phase 5 · requirements AGNT-01/02/03)

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | **Unified Agent base + all six archetypes in `/src` with no agent instances, prompts, or domain values in library code; composition per D-IMPL-11/19** (AGNT-01) | `src/ccf/agents/archetypes.py` (all six `ArchetypeComponent`s), `src/ccf/agents/agent.py`, `src/ccf/agents/composition.py`; `tests/agents/test_archetypes.py`, `test_composition.py` (row 13), `test_consumption_discipline.py` (row 9); the §1 domain grep over `src/ccf/agents` + `src/ccf/skills` is empty; CINV-01a/b zero findings (rows 1–2) |
| 2 | **Factory constructs agents/tasks only from D-IMPL-28 definition artifacts; no bypass path; lint rejects bypass and prompt literals** (AGNT-02) | `src/ccf/agents/factory.py` (AgentFactory + TaskFactory, D-11), `src/ccf/agents/definitions.py` (six-axis schema), `tests/agents/test_factory.py` (construction, refusal paths, determinism), `tests/agents/test_schema_export.py` (exported JSON Schema); the CINV-01c behavioral fixture suite (row 3) proves the lint fires on bypass; `tests/agents/test_factory.py` fixtures construct only through factories |
| 3 | **Skill catalog: registration, discovery, runtime grant/revoke; policy-compatibility refusal; every grant/revocation and the in-force skill-set in replay** (AGNT-03) | `src/ccf/skills/catalog.py` + `tests/skills/test_catalog.py` (D-IMPL-12 four-type entries, Control-Plane registration/discovery); `src/ccf/skills/grants.py` + rows 7–8, 11 (two-tier governance, refusals, audit); `src/ccf/skills/dispatch.py` + `tests/skills/test_dispatch.py` (local/tool dispatch, typed `NotYetBound` for mcp/a2a per D-08); CINV-04 `skill-set-capture` active with its owning slice test (row 6) |
| 4 | **All six specialization axes expressible in the definition artifact and versioned; any axis change is a new agent version visible in replay** (AGNT-01/02) | `src/ccf/agents/definitions.py` (all six axes in `AgentDefinition`); the six-axis version matrix (row 12); D-05 hash-verified bump (row 10); dimension-4 assertions in `tests/integration/test_agent_slice.py` (definition hash, prompt-artifact versions, grant-set hash all recorded verbatim) |

All three requirement ids — **AGNT-01, AGNT-02, AGNT-03** — are covered; ROADMAP marks each
complete after plans 05-03, 05-04, and 05-06 respectively.

### Gap-closure note (plans 05-08 · 05-09 · 05-10)

The phase code review (`05-REVIEW.md`, 2026-07-26) found 1 critical, 8 warning, and 8 info
findings. Plans **05-08**, **05-09**, and **05-10** closed the following before this gate is
presented: **CR-01** (per-agent D-07 grant-set hash), **WR-01** (required `grant_set_hash`
argument with `FalseGrantClaimError` refusal of false zero-grants claims), **WR-02**
(tenant-coherence refusal `TenantMismatch` on the grant path), **WR-03** (typed
`BoundSkillView` seam whose only producer is `GrantLedger.bound_view`), **WR-04**
(catalog-entry resolution before any ledger state mutation — no wedged `requested` grants),
**WR-05** (`GrantCollisionError` on same-name double-effective grants), **WR-06** (CINV-01c
import-alias tracking + explicit factory-path allowlist replacing the `"factory"` substring
exemption), **WR-07** (single shared `AuditLog` injected into registry and ledger), **WR-08**
(`AmbiguousPinnedVersionError` when one declared semver names two contents; unaudited probes
via `peek`), **IN-01** (this document's rows 6–7 corrected to describe the fixed mechanisms),
**IN-02** (stale harness-double pragma cleared), **IN-03** (`SkillCatalog.discover` derived
from registry state via `keys_of_class`, volatile per-instance index deleted), and **IN-08**
(`TaskFactory` refuses an `agent` step whose ref resolves to a non-`AgentDefinition` class).

**Advisory carry-forward (IN-07, per the review's fix suggestion):**
`tests/agents/test_agent.py` constructs `Agent` directly for constructor-validation unit
tests — a documented deviation from CLAUDE.md §6.4's "tests construct agents the same way,
from fixture artifacts." The scoping decision: the CINV-01c lint's mechanism-of-record scope
is `/src`, `/runtime`, `/examples`; constructor-refusal tests must exercise the constructor's
own guards and cannot do so through the factory. Recorded here as an advisory triage item
for the §3.1 review, not silently in a test docstring.

**Gap-closure re-verification sweep** (executed after plan 05-10, 2026-07-26):

| Leg | Command | Result |
|-----|---------|--------|
| Full suite | `.venv/bin/python -m pytest -q -m "not postgres"` | **577 passed, 2 skipped** (exit 0 — the 2 skips are exactly the declared I.4 CINV-04 deferrals, `hitl-action-capture` and `workflow-trace-capture`) |
| Invariant lints | `.venv/bin/python -m tools.lints` | **exit 0, zero findings** |
| Strict typing | `.venv/bin/python -m mypy --strict src tools` | **Success: no issues found in 74 source files** |

---

## 4. Discretionary Implementation Notes (Claude's-discretion items — NOT new D-IMPL entries)

These were in-phase implementation choices inside space the rulings left open. No genuine
whitepaper-silent gap surfaced mid-phase, so `docs/DECISIONS.md` gains no new entry; the
choices are recorded here for the reviewer.

1. **`NotYetBound` is a typed `RuntimeError`, not a returned refusal** (RESEARCH Open
   Question 2). A granted, valid mcp/a2a catalog entry whose transport this build lacks is
   a *deployment-shape fact*, not a bad artifact — refusal values are reserved for bad
   artifacts (the I.1 gate-refusal discipline). Documented on the class in
   `src/ccf/agents/errors.py`; asserted by
   `tests/skills/test_dispatch.py::test_not_yet_bound_is_a_typed_exception_not_a_refusal_value`.
2. **Exact-match prompt-parameter rule.** The parameters a prompt artifact declares must
   equal exactly the set Jinja2's `find_undeclared_variables` discovers — no unused
   declarations, no undeclared uses. Both directions fail factory construction
   (`tests/agents/test_factory.py::test_a_prompt_parameter_mismatch_fails_construction`).
   Strictness chosen so a drifted template can never silently ship.
3. **Grant-set as `frozenset`** (D-07 realization). The in-force grant set is hashed as
   `content_hash(frozenset(active_grant_hashes))` — arrival-order-free by type, with the
   positive `NO_GRANTS_SET_HASH` sentinel for the empty set so "no grants" is a recorded
   fact, not an absent field (row 11).

---

## 5. I.3 / I.4 Handoff Notes

**To Phase 6 (I.3 — Cross-Process & Harness Adapters):**

- **Jinja2 rendering and the SSTI surface.** I.2 is parse-only (D-13): no `.render()` call
  exists in `/src` (verified §1). Rendering into harness-ready strings lands in the I.3
  adapters, and the deferred security surface travels with it. RESEARCH threat-register
  note, verbatim: *"Jinja2 SSTI | Elevation | Parse-only in I.2 (no render, no
  user-controlled render context) — SSTI surface deferred to I.3; note this in the I.3
  handoff."* I.3 must treat render-context provenance and sandboxing as an explicit
  threat-model item before the first `render(...)` ships.
- **`local_callable` dispatch is artifact-driven arbitrary code execution (IN-06 —
  accepted risk, carried forward deliberately).** `src/ccf/skills/dispatch.py` resolves a
  catalog entry's `callable_ref` with `importlib.import_module` + `getattr`, which
  executes arbitrary module code at dispatch time. The T-05-18 trust posture that makes
  this acceptable in I.2 is narrow and *stated as a precondition, not a property*:
  `callable_ref`s arrive only from Control Plane artifacts registered inside the tenant
  trust boundary, which in I.2 means in-repo fixtures. **I.3 invalidates the precondition
  rather than inheriting it** — once artifacts can arrive via MCP artifact stores or A2A
  federation (CLAUDE.md §7.2/§7.4), a `callable_ref` becomes remote-influenced input and
  the posture no longer holds by construction. I.3 must therefore re-examine this as an
  explicit threat-model item alongside the Jinja2 SSTI note above, and decide the control
  before the first non-in-repo artifact source is admitted: an import allowlist, a
  registered-callable indirection that removes free-form module paths, or a Control Plane
  admission check on `callable_ref` provenance. **This is a deliberate deferral, not a
  gap to be closed inside I.2** — no dispatch semantics were changed for it.
  **RESOLVED in I.3 (2026-07-26) as D-IMPL-54:** candidate (b), the
  registered-callable indirection. `importlib` is gone from
  `src/ccf/skills/dispatch.py`; `callable_ref` is a key into a boot-registered
  `CallableRegistry` (`src/ccf/skills/callables.py`). This paragraph is left
  standing as the I.2 record of the deferral, not as a live claim.
- **MCP/A2A skill dispatch is `NotYetBound` by ruling (D-08).** `mcp` and `a2a` catalog
  entries validate, register, and grant today; only dispatch raises the typed exception
  naming the deferral. I.3 binds the transports; the dispatch seam in
  `src/ccf/skills/dispatch.py` is where they land, and
  `tests/skills/test_dispatch.py` marks the two entry types that flip.
- **Prompt rendering pipeline.** The factory already resolves and pins prompt artifacts by
  versioned URI and carries them on the constructed agent
  (`test_the_resolved_prompt_artifacts_travel_with_the_agent`); the I.3 adapter's context
  injection seam (CLAUDE.md §7.3 seam 1) consumes those pinned artifacts — it must never
  re-resolve them.
- **Advisory carry-forwards from the I.1 gate** still open: A-7 (`shipped_operators()` is
  hand-assembled — revisit if I.3 ships operators) and A-1 (class-level citation placement
  for auxiliary types, extend as modules are touched).

**To Phase 7 (I.4 — Orchestration & HITL):**

- **ApprovalSink real implementation (D-09).** I.2's sink decides synchronously; the
  suspending `ApprovalGate` is I.4 scope. It joins the `GrantLedger` state machine and the
  factory-parametrized conformance suite (`tests/conformance/test_approval_sink.py`)
  **with no test-body change** — that is the designed seam. Approver identity is an id
  string only; identity binding is D-IMPL-21 (T-05-19 accepted).
- **Grant state is on the Control Plane's mutable-state seam (WR-05 — closed in I.2, not
  deferred).** Grant *artifacts* are immutable and register append-only; grant *state* is
  mutable until terminal and lives on `ControlPlaneStateStore`
  (`src/ccf/controlplane/state.py`), per D-IMPL-27's mutability split and D-IMPL-18's
  ruling that such state sits on "the Control Plane's storage seam — pluggable there, no
  separate workflow-store Protocol." Both were resolved 2026-07-25; an earlier revision of
  this document and of the `GrantLedger` docstring described them as open and deferred the
  fix on that basis — that was wrong, and the deferral was withdrawn rather than inherited.
  Every ledger over one Control Plane now agrees on the effective set, the per-agent
  `grant_set_hash`, and the bound view, pinned by `TestGovernanceSeams` in
  `tests/skills/test_grants.py` (each verified to fail with the seam reverted).
  **I.4 inherits the seam, not the question:** the suspending `ApprovalGate` produces a
  `pending-approval` grant that must survive a restart, and it does so by the deployment
  supplying a durable `ControlPlaneStateStore` — the same store suspended workflow
  execution state uses — with no consumer change. The v0 default is in-process, matching
  the Control Plane it sits in (CLAUDE.md §13).
- **Task execution.** D-11 shipped `TaskDefinition` + `TaskFactory` as schema and
  construction only — no execution surface and no invented replay capture (verified §1).
  Workflow execution, its replay trace (`workflow-trace-capture`), and HITL capture
  (`hitl-action-capture`) are the two remaining CINV-04 deferrals, both phase-tagged I.4.

---

## 6. What Dave Is Asked To Decide (after `/gsd-review --phase "Phase I.2" --all`)

1. Read §1 (verification evidence), §2 (per-invariant checklist), §3 (success-criteria
   map), §4 (discretionary notes), §5 (handoff).
2. Optionally re-run: `.venv/bin/pytest tests -q && .venv/bin/mypy --strict src && .venv/bin/python -m tools.lints`
3. **Approve or reject the Phase I.2 gate.**

On approval — and only on approval — the executor appends the `D-GATE-I.2` entry to
`docs/DECISIONS.md`, merges `phase-i2` into `main` with a merge commit referencing
`D-GATE-I.2` (no force-push, CLAUDE.md §2.2), and updates `.planning/ROADMAP.md` and
`.planning/REQUIREMENTS.md`.
