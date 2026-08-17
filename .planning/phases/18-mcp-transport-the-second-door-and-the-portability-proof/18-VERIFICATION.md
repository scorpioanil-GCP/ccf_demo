---
phase: 18-mcp-transport-the-second-door-and-the-portability-proof
verified: 2026-08-17T18:51:23Z
status: gaps_found
score: 6/7 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
gaps:
  - truth: "D-15: the MCP adapter ships on passing the conformance suite, not on demoing — it is bound into the existing suite and changes nothing in it"
    status: partial
    reason: >-
      Six of the seven conformance legs are called with BOTH subjects and pass
      non-vacuously (independently sabotage-tested during this verification).
      The seventh — `assert_decision_instant_is_auditable` — is called with the
      MCP subject ALONE, so the adapter never faced that leg's cross-adapter
      comparison. `D-IMPL-149` was RESOLVED by Dave on 2026-08-17 at HEAD
      (commit 8826b12) with ruling (b) SPLIT THE LEG, and the entry states
      "Implementation is in-phase ... this ruling is the authorization for
      `17-10`'s otherwise-standing prohibition on editing `suite.py` to be
      lifted, and only for this leg." The tree does not contain that
      implementation. `.planning/STATE.md` itself lists the split as owed
      before the gate.
    artifacts:
      - path: "tests/client/conformance/suite.py"
        issue: >-
          Line 759 still carries `_assert_views_agree(recovered, leg="decision
          instant")` — the unsatisfiable cross-subject demand under
          `as_of=None` that ruling (b) part (3) orders removed. Parts (1) and
          (2) of the ruling are likewise absent: there is no clock-independent
          cross-adapter assertion gated on the test pinning the same `as_of`
          for every subject.
      - path: "tests/client/conformance/test_mcp_conformance.py"
        issue: >-
          Line 126-131 calls the leg with `(MCP,)` alone. Correct as a
          stop-and-report while D-IMPL-149 was open; stale now that it is
          ruled. Under the ruling this call site must take both subjects for
          the per-subject half and the new pinned cross-adapter assertion.
    missing:
      - "suite.py: remove the trailing `_assert_views_agree` from `assert_decision_instant_is_auditable` (ruling (b) part 3)"
      - "suite.py: add a clock-independent cross-adapter assertion that runs only when the caller pins the same `as_of` for every subject (ruling (b) part 2)"
      - "test_mcp_conformance.py: call the repaired per-subject leg with both subjects, and call the new pinned cross-adapter leg"
      - "A sabotage control (D-22) for the new cross-adapter assertion, passing a divergent subject into the real function"
  - truth: "CLAUDE.md §3.1 — the phase-close protocol is discharged before the phase is presented as complete"
    status: failed
    reason: >-
      The phase is submitted as complete but the §3.1 sequence has not run.
      There is no `18-CLOSE-REVIEWS.md` (the mandatory cross-AI panel on the
      SHIPPED CODE), no single-agent code review, no blocking/advisory triage,
      and no `D-GATE-18`. `.planning/STATE.md` at HEAD states all of these as
      owed. The ROADMAP row reads `1/1 — Complete`, which is accurate about
      plans and is not a gate.
    artifacts:
      - path: ".planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/"
        issue: "Contains only 17-10-PLAN.md and 17-10-SUMMARY.md; no CLOSE-REVIEWS artifact."
    missing:
      - "`/gsd-review --phase 18 --all` against the shipped code, written to 18-CLOSE-REVIEWS.md"
      - "Single-agent code review, additive to the panel"
      - "Every finding verified against the tree before it is recorded or acted on"
      - "Blocking findings fixed in-phase; advisory findings recorded"
      - "Dave's ruling and a `D-GATE-18` entry in docs/DECISIONS.md"
deferred:
  - truth: "REQUIREMENTS.md traceability Status for CLNT-15 reads Satisfied rather than Pending"
    addressed_in: "A Dave scope decision, recorded"
    evidence: >-
      D-IMPL-147 Addendum A: "Mass-updating seventeen statuses is a scope
      decision for Dave rather than a side effect of opening Phase 18, so only
      the one row whose correctness the lift actually changed was touched."
      All 22 CLNT rows read Pending, including the 14 that D-GATE-17 closed.
human_verification:
  - test: "Rule on whether the `mcp+stdio` portability claim must be reachable from `examples/hw1-companies-over-revenue/consume.py`"
    expected: >-
      The plan's stated Output is `CCF_BINDING=\"mcp+stdio:…\"` runs the same
      consume.py and returns an identical Result. In the tree consume.py
      imports only `ccf.client.adapters.inprocess`, and the example deployment
      ships no MCP server program, so that command raises BindingError. Either
      the example is wired for the second transport, or the Output line is
      recorded as discharged by the conformance suite instead.
    why_human: >-
      Scope decision. The Output line is in the plan's objective, not in
      must_haves, and the conformance suite is the ruled acceptance mechanism
      (D-15, §6 "an adapter is official when it passes"). Whether the adoption
      contract in §9 additionally requires the example to run over the second
      transport is Dave's call, not a grep's.
  - test: "Rule on whether an adopter has a supported path to write an mcp+stdio server program"
    expected: >-
      The only server program in the tree is `tests/client/fixtures/stdio_server.py`,
      and it composes its resolver by importing the PRIVATE
      `ccf.client.adapters.inprocess._boot`. There is no public composition
      helper and no documented recipe outside a test fixture.
    why_human: >-
      Adoptability judgement against CLAUDE.md §1 success condition 4. The
      private import is arguably correct for a fixture (it makes the parity
      legs a claim about transports rather than about two compositions) and
      arguably a missing public surface for adopters.
---

# Phase 18: MCP Transport — The Second Door and the Portability Proof — Verification Report

**Phase Goal:** Turn "transport-agnostic" from a design property into a demonstrated one — the MCP egress tool stops hard-wiring `parameters={}`, the MCP door emits the canonical refusal envelope while a governance refusal still raises, and `mcp+stdio` ships as the second official adapter on passing the conformance suite **without `suite.py` moving**. Discharge: the same question at the same instant yielding the same content address in-process and over MCP.

**Verified:** 2026-08-17T18:51:23Z
**Status:** gaps_found
**Re-verification:** No — initial verification
**HEAD at verification:** `8826b12` (moved from `ebeaa17` mid-verification; see Finding A)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | **D-28 rollout:** the MCP door produces the canonical refusal envelope | ✓ VERIFIED | `egress.py:729-745` calls `door_refusal(...)` and returns `canonical_bytes(DoorOutcome(product_json=None, replay_ref=None, refusal=refusal))`. `src/ccf/products/door.py::door_refusal` handles both a ready-made `RefusalEnvelope` (passed through untouched, lineage preserved) and a bare `REFUSAL_KINDS` value (translated against the carried request). Governance boundary held on **both** halves — `test_a_governance_refusal_still_raises_and_is_not_enveloped` asserts `isError=True` with no decodable `DoorOutcome` on the wire AND that the shipped renderer returns `None` for `ProductEntitlementRefused`. **Independently sabotaged:** mangling `refusal.key` on the MCP decode path made the real `assert_refusal_parity` leg fail. 30 tests in `tests/mcp/test_egress_refusal_envelope.py` + `test_egress_parameters.py` green (59 passed with crossproc). |
| 2 | **D-IMPL-133 / 16-26:** the MCP product door carries client-supplied parameters | ✓ VERIFIED | `grep "parameters={}" runtime/ccf_runtime/mcp/egress.py` → nothing. `egress.py:520` adds `parameters: dict[str, Any] \| None = None`; `:731` forwards `dict(parameters or {})` verbatim with no coercion. The docstring's recorded reason is **amended, not deleted** (`:584-660`), and its two halves are resolved separately with the width half still binding. The HTTP door was repaired symmetrically (`routes/product.py`, one JSON object in one query parameter). Width ceiling is a **shared** 5-case table (`PARAMETER_CASES`) run against both real doors through `assert_same_verdicts`, which carries a named non-vacuity guard refusing a table with no served case. End-to-end: the conformance fixture class declares a required parameter and is served over MCP. |
| 3 | **D-15:** the MCP adapter ships on passing the conformance suite, bound in, changing nothing in it | ✗ **PARTIAL — see gap 1** | `git diff c90d84b..HEAD -- tests/client/conformance/suite.py` = **0 lines**; same against `main`. `make conformance` exit **0**, **56 passed** (re-measured independently). But `test_mcp_conformance.py:126` calls `assert_decision_instant_is_auditable((MCP,), …)` — the MCP subject **alone**. `D-IMPL-149` is **RESOLVED at HEAD** with ruling (b) and an explicit in-phase implementation mandate that is absent from the tree. |
| 4 | **D-23:** two thresholds are two content addresses over MCP too | ✓ VERIFIED | `test_two_thresholds_are_two_content_addresses` calls `assert_two_parameters_are_two_addresses(SUBJECTS, …)` with both subjects; the leg checks address-first-then-payload with the ordering reasoning recorded. **Independently sabotaged:** patching the MCP adapter to ignore the caller's parameters made the leg fail. |
| 5 | **D-24:** sync at the client surface, async bridged internally | ✓ VERIFIED | `grep -c "async def ask\|await self.ask" src/ccf/client/adapters/mcp_stdio.py` → **0**. `ask()` is sync; one `asyncio.run(self._call(...))` per call; the whole session lifetime is one coroutine's `async with` stack (session-per-call). `ccf.client.__all__` == `['BindingError','ProductClient','Result','TransportError']` — the four ruled names, unchanged. `SyncMcpBridge` deliberately not reused, with the reason recorded (it requires `call_timeout_seconds` with no default, and T-17-41 dispositions timeouts as *accept* for v0). |
| 6 | **D-12:** the adapter constructs no `Result`; it returns a `WireOutcome` | ✓ VERIFIED | `grep -c "Result(" src/ccf/client/adapters/mcp_stdio.py` → **0**. `_decode` returns `WireOutcome`. The single construction site is `ProductClient._result_from` (`client.py:202`), which runs `codec.check_outcome` on whatever any adapter returned. `mypy --strict`: 211 files, no issues. |
| 7 | **D-22:** every control passes its broken subject INTO the shipped assertion as a parameter | ✓ VERIFIED | All five shipped assertions are functions over their subjects: `assert_same_verdicts(cases, ask_mcp, ask_http)`, `assert_type_mismatch_refused(cases, ask)`, `assert_refusals_identical(a, b)`, `assert_governance_stays_a_raise(render)`, `assert_both_doors_carry_the_replay_ref(ask_mcp, ask_http)`. Six controls pass divergent **callables** into those same functions. `test_the_mcp_binding_fires.py` subclasses the real `McpStdioAdapter` (still spawning a real child over real pipes) and passes it into the real `suite.assert_served_parity`. **No control copies a module to `tmp_path`** — the defect class the plan named is absent. Independently confirmed: my own sabotages fired the same shipped legs. |

**Score:** 6/7 truths verified

### The phase's central discharge — measured, not read

The claim *"the same question at the same instant yielding the same content address in-process and over MCP"* is **VERIFIED by independent measurement**, and the SUMMARY's pasted values are corroborated rather than trusted:

| Subject | content address (`hw`-fixture question, `as_of` pinned 2026-03-02T12:00Z) |
|---------|---------------------------------------------------------------------------|
| `inprocess` | `4113d988a3836a0c7a75ecb933c95b09fc9a7a263ed3477a65d325f31eccec50` |
| `mcp+stdio` | `4113d988a3836a0c7a75ecb933c95b09fc9a7a263ed3477a65d325f31eccec50` |

That first value fell out of my own sabotage run's failure message, not out of the SUMMARY. The equality is over a **real** process boundary (the child announces `CallToolRequest` on stderr through FastMCP's stdio server), and `assert_served_parity` compares **eleven** derived `Result` fields, `replay_ref` and `content_address` among them — with a non-`None` replay reference on **both** sides:
`ccf-artifact://tenant-client-fixture/fixture.replay-record/5b1bce07…@7001225c…`

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | `CLNT-15` traceability Status still reads `Pending` | A recorded Dave scope decision | `D-IMPL-147` Addendum A: mass-updating 17 stale statuses is Dave's scope call; only the row the lift changed was touched. All 22 CLNT rows are stale, including 14 that `D-GATE-17` closed. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ccf/client/adapters/mcp_stdio.py` | The second official adapter, registered under `mcp+stdio` (min 140 L) | ✓ VERIFIED | 415 L. Exists, substantive, wired (`SCHEME_REGISTRY[SCHEME] = McpStdioAdapter` at `:415`; imported by the conformance binding and its controls), and **data flows** — a real child process, real pipes, real bytes, verified by sabotage. |
| `tests/client/conformance/test_mcp_conformance.py` | The MCP adapter bound into the shared suite (max 80 L) | ⚠️ OVER BUDGET, recorded | **131 L vs 80.** The plan's own escape clause admits an overage if the SUMMARY says where; it does, with an AST breakdown (48 code lines vs the in-process model's 61; the adapter-specific part is two functions and four statements). Not adapter-specific weight. Accepted as a WARNING, not a blocker. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/ccf/client/adapters/mcp_stdio.py` | `src/ccf/client/codec.py` | the one decode path — the adapter builds no `Result` (pattern: `WireOutcome`) | ✓ WIRED (indirect, by design) | The adapter returns `WireOutcome` and builds no `Result`; `ProductClient._result_from` runs `codec.check_outcome` on it, which is `D-11`'s typed-seam posture stated in `codec.py`'s own docstring (*"the client calls it on whatever an adapter returned"*). **Note:** the adapter does not import `codec`; it spells `hashlib.sha256(...).hexdigest()` inline at `:407`, a second spelling of `codec.verify_content_address`'s formula at `:115`. Fails closed (the client recomputes and refuses a disagreement) and matches the pre-existing `inprocess.py:439` pattern. Informational, not a gap. |
| `runtime/ccf_runtime/mcp/egress.py` | `src/ccf/products/refusal.py` | the door emits the canonical refusal envelope (pattern: `RefusalEnvelope`) | ✓ WIRED | Via `ccf.products.door` (`envelope_for`, `REFUSAL_KINDS`, `RequestIdentity`). Egress imports `door_refusal`/`served_answer`/`DoorOutcome` at `:122-127`. |

### Data-Flow Trace (Level 4)

| Artifact | Data variable | Source | Produces real data | Status |
|----------|---------------|--------|--------------------|--------|
| `McpStdioAdapter` | `WireOutcome.product_json` | `session.call_tool(PRODUCT_REQUEST_TOOL, …)` over a spawned `sys.executable` child | Yes — non-empty canonical vessel; content address equals in-process | ✓ FLOWING |
| `McpStdioAdapter` | `WireOutcome.replay_ref` | `DoorOutcome.replay_ref` ← `served_answer(resolved).replay_ref` | Yes — a live `ccf-artifact://…` URI, proven by sabotage (nulling it turned the parity leg red) | ✓ FLOWING |
| `McpStdioAdapter` | `WireOutcome.refusal` | `DoorOutcome.refusal` ← `door_refusal(...)` | Yes — reason, key, kind and request identity all populated and field-identical to in-process | ✓ FLOWING |
| MCP egress tool | `ProductRequest.parameters` | the tool's new `parameters` argument, forwarded verbatim | Yes — `test_a_supplied_parameter_reaches_the_resolver` asserts on the **carried value**, not on served status | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| The conformance gate is green with both adapters | `make conformance` | exit 0, **56 passed** in 15.85 s | ✓ PASS |
| `suite.py` did not move | `git diff c90d84b..HEAD -- tests/client/conformance/suite.py \| wc -l` | **0** (also 0 vs `main`) | ✓ PASS |
| Both schemes registered | `python -c "…SCHEME_REGISTRY…"` / source read | `inprocess.py:445`, `mcp_stdio.py:415` — one dict entry each | ✓ PASS |
| The client surface stayed at four names | `python -c "import ccf.client; print(ccf.client.__all__)"` | `['BindingError','ProductClient','Result','TransportError']` | ✓ PASS |
| All CCF invariant lints | `make lint` | exit 0 | ✓ PASS |
| Harness-import lint is live (not vacuous) | injected `import google.adk` into a copy of the adapter and ran `harness_imports.check` | fired: `cinv02-harness harness import 'google.adk' is forbidden in core` | ✓ PASS |
| `mcp` is permitted in `src/` | `HARNESS_DENY` frozenset read; four pre-existing `src/` MCP imports | MCP is CCF's own integration surface (§7.1), not a harness | ✓ PASS |
| `src/` does not import `runtime/` | `pytest tests/invariants/test_src_does_not_import_runtime.py tests/invariants/test_mcp_role_separation.py` | 51 passed | ✓ PASS |
| `mypy --strict` | `make typecheck` | Success, 211 source files | ✓ PASS |
| MCP door tests | `pytest tests/mcp/test_egress_parameters.py tests/mcp/test_egress_refusal_envelope.py tests/crossproc/test_mcp_egress.py` | 59 passed | ✓ PASS |
| The D-22 controls run | `pytest tests/client/conformance/test_the_mcp_binding_fires.py tests/client/test_mcp_stdio_adapter.py` | 9 passed | ✓ PASS |
| The MCP leg runs in the always-on pipeline | `testpaths=["tests"]`, no default `-m` deselection, `ci-core → test` | Yes — `make conformance` is a name, not a second collection path | ✓ PASS |

### Independent Sabotage Probes (run by this verifier, outside the repository)

The recurring defect this project names is *machinery that reports green while verifying the wrong thing*. Four probes, each monkeypatching the **shipped** `McpStdioAdapter` from a plugin outside the tree and re-running the **shipped** conformance module:

| Probe | Expected to fire | Result |
|-------|------------------|--------|
| Null `replay_ref` on the MCP decode path | `assert_served_parity` | ✓ FIRED — named `replay_ref` and both values |
| Perturb the vessel bytes (address moves, internally consistent) | `assert_served_parity` + `assert_one_question_is_one_address` | ✓ FIRED — both legs, named `content_address` |
| Mangle `refusal.key` | `assert_refusal_parity` | ✓ FIRED |
| Make the adapter ignore the caller's `parameters` | `assert_two_parameters_are_two_addresses` (+ others) | ✓ FIRED |

**Adjacent question asked and answered (per the brief):** *are there OTHER `_assert_views_agree` call sites whose cross-subject comparison is vacuous?* There are exactly four. Three — `assert_served_parity`, `assert_one_question_is_one_address`, `assert_refusal_parity` — are proven non-vacuous above with two real subjects bound. The fourth is `assert_decision_instant_is_auditable`, which is `D-IMPL-149` and is gap 1. No fifth exists. `assert_guard_parity`, `assert_wire_failure_parity` and `assert_two_parameters_are_two_addresses` are per-subject by construction and need no cross-subject comparison.

### Requirements Coverage

| Requirement | Source plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| **CLNT-15** | `17-10` (Phase 18) | The MCP product door carries client-supplied parameters and emits the canonical refusal envelope, and the MCP adapter ships on passing the same conformance suite as in-process rather than on demoing (`D-15`, `D-28`, `D-IMPL-133`) | ⚠️ **SATISFIED IN SUBSTANCE, ONE CLAUSE PARTIAL** | Clause 1 (parameters) ✓ truth 2. Clause 2 (refusal envelope) ✓ truth 1. Clause 3 (ships on passing the suite) — passes as run (56/56, `suite.py` unmoved), but one leg was narrowed to a single subject, and `D-IMPL-149`'s ruled repair is unimplemented. The row in `.planning/REQUIREMENTS.md:355` correctly reads `Phase 18` per `D-IMPL-147` Addendum A; its Status column still reads `Pending` (deferred, above). |
| **CLNT-12** | `17-10` (mapped to Phase 17) | Every parity, guard and example gate this phase adds carries a named sabotage control demonstrating the check fails when its property is deliberately broken, written in the same plan as the assertion rather than deferred (`D-22`) | ✓ SATISFIED for this phase's additions | Six controls for five new shipped assertions plus the conformance binding; all pass a divergent subject into the real function. `.planning/REQUIREMENTS.md:352` correctly keeps the row on Phase 17 (eight Phase 17 plans claim it, two SUMMARYs record satisfying it) — `D-IMPL-147` Addendum A states the reasoning. Phase 18 re-asserts it for its own gates rather than owning it. |

**Orphan check:** `grep "Phase 18" .planning/REQUIREMENTS.md` returns only the `CLNT-15` row. No requirement is mapped to Phase 18 that no plan claimed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD` / `FIXME` / `XXX` in files this phase modified | — | **None found.** The debt-marker gate is clean across all 26 changed files. |
| `src/ccf/client/adapters/mcp_stdio.py` | 264 | `# pragma: no cover - typed` on a `BindingError` branch | ℹ️ Info | One narrow typed-impossible branch; consistent with the tree's existing convention. Not the `_parse`-swallows-`SyntaxError` pattern carried from `D-GATE-17`. |
| `src/ccf/client/adapters/mcp_stdio.py` | 407 | Second inline spelling of the content-address formula | ℹ️ Info | Fails closed (`codec.verify_content_address` recomputes and refuses). Matches `inprocess.py:439`. |
| `tests/contracts/test_canonical.py` | 117 | Child spawned with `env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"}` — **no `PYTHONPATH`** | ⚠️ Warning | **Adjacent to known finding 3, same defect class, unfixed.** Under an executor worktree this child imports the editable-install checkout's `ccf` (verified: the `.pth` finder resolves to `/home/parkave/ccf_code/src`) rather than the worktree under test, exactly the failure the phase fixed in the adapter. Benign in the main checkout; silent, not loud, in a worktree. Every other subprocess site checked (`test_cold_import.py`, `test_boot_seam.py`, `test_adapter_config.py`, `test_smoke.py`, `test_ext00_hardening.py`, `crossproc/conftest.py`, the example runners) either sets `PYTHONPATH` explicitly or inherits the full environment. One instance, named. |
| `examples/hw1-companies-over-revenue/consume.py` | 24 | Imports only `ccf.client.adapters.inprocess` | ⚠️ Warning | `CCF_BINDING="mcp+stdio:…" … consume.py` raises `BindingError` — the scheme reaches the registry only by its adapter module being imported, and no MCP server program ships for that deployment. The plan's stated **Output** is not achieved in the tree. Routed to human verification. |
| `tests/client/fixtures/stdio_server.py` | 63 | `from ccf.client.adapters.inprocess import _boot` (private) | ⚠️ Warning | The only server program in the tree reaches a private SDK symbol. Defensible for a fixture (it makes the parity legs a claim about transports, not about two compositions — the module docstring argues exactly this), but it means an adopter has no public composition path. Routed to human verification. |

### SUMMARY claims that did not survive checking

Recorded because the brief asks for disagreement to be flagged, not because either is load-bearing:

- **"`make conformance` 54 passed in 13.9 s"** — re-measured **56 passed** in 15.85 s. The SUMMARY's figure was taken before `test_the_mcp_binding_fires.py`'s two controls were added.
- **"`tests/client/conformance/` is untouched: `git diff` against it is empty."** — false as written; the phase added two files there. The claim is true, and is the one that matters, only of `suite.py`, which I re-measured at **0 lines** changed against both `c90d84b` and `main`.

### Findings

**FINDING A — the tree moved under verification, and the movement is the blocker.**
Verification began at `ebeaa17`, whose commit message and `DECISIONS.md` text both read `D-IMPL-149 — **OPEN — awaiting Dave**`. At 11:43 local, mid-verification, `8826b12` landed and rewrote that entry to **RESOLVED**, ruling **(b) SPLIT THE LEG**, with: *"Implementation is in-phase, per `CLAUDE.md` §3.1's requirement that blocking findings are fixed inside the current phase; this ruling is the authorization for `17-10`'s otherwise-standing prohibition on editing `suite.py` to be lifted, and only for this leg."*

This converts the orchestrator's brief-supplied premise (*"D-IMPL-149 (OPEN, awaiting Dave)"*) into a **closed ruling with unimplemented in-phase work**. It is the difference between a stop-and-report that is correct and a stop-and-report that is stale. The same commit added to `.planning/STATE.md` the explicit statement that Phase 18 is **NOT GATED** and that the suite split, the cross-AI panel, the single-agent review, triage and Dave's ruling are all still owed. My verdict agrees with the project's own state record.

**FINDING B — what `17-10` did about `D-IMPL-149` was right at the time, and is right in the record.**
The executor did not narrow the assertion, did not exempt the field, did not touch `suite.py`, and documented the reason at module and function level in the shipped test. That is the correct behaviour under `D-IMPL-148` and it is what made the defect visible at all. Nothing here is a finding against `17-10`; the finding is that the ruling that followed has not been executed.

### Gaps Summary

The phase's substantive engineering is done and it is **real**, not asserted. The MCP door carries parameters and refusals; the adapter is registered by one dict entry, builds no `Result`, is sync at the surface with the async client bridged internally, and raises on every wire failure; `suite.py` did not move by a single line; and the portability claim — one question, one instant, one content address across a genuine process boundary — reproduces under my own hands and survives four independent sabotages. Six of seven must-have truths are verified with adversarial evidence rather than with a green test.

Two things stop the phase closing.

The first is `D-IMPL-149`. When the executor stopped and reported, that was correct. Dave has since ruled, the ruling explicitly lifts the `suite.py` prohibition **for this leg only**, and it names three required parts — keep the per-subject property, add a clock-independent cross-adapter assertion gated on a pinned `as_of`, remove the unsatisfiable demand. None of the three is in the tree. Until they are, the cross-adapter half of `DEF-17-07` is asserted nowhere, `suite.py:759` still carries an assertion that has never been able to hold, and the MCP adapter has passed six of seven legs rather than seven. That is `D-15`'s *"an adapter is official when it passes"* met at six-sevenths.

The second is `CLAUDE.md` §3.1. The phase is being presented as complete without the cross-AI panel on the shipped code, without the single-agent review, without triage, and without a `D-GATE-18`. The project's own `STATE.md` says so at HEAD. §3.1 is explicit that `/gsd:execute-phase` completing is not the end of a phase, and this repository has a recorded history of the last commit being the least-reviewed one.

Neither gap is a defect in what was built. Both are work the phase's own governing documents say is owed before it closes.

---

_Verified: 2026-08-17T18:51:23Z_
_Verifier: Claude (gsd-verifier)_
