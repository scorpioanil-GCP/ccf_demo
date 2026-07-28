# Phase I.3 — Cross-AI Gate Review (§3.1 step 1)

Date: 2026-07-27. Run by the orchestrator BEFORE presenting to Dave, per CLAUDE.md §3.1
("a review report is a precondition of requesting approval, not a substitute for it").

## Reviewers invoked

| Reviewer | Outcome | Usable |
|---|---|---|
| **cursor** (`cursor agent -p --mode ask`) | 4 BLOCKING + 8 ADVISORY, all with file:line | **YES** — grounded, verified |
| **codex** (`codex exec --sandbox read-only`) | Could not read the tree: `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` | No — **refused to fabricate**, correctly |
| **gemini** (`gemini -p`) | 3 BLOCKING claims, all FALSE | No — **discarded**, see below |
| claude | Skipped — self, for independence (`CLAUDE_CODE_ENTRYPOINT=cli`) | n/a |

### Gemini discarded — its findings were fabricated

Its tool calls were blocked (`Unauthorized tool call: 'read_file'`) and it fell back to a
sub-agent that invented file contents. All three BLOCKING claims were checked and are false:

| Gemini claim | Verified reality |
|---|---|
| `test_harness_portability.py` uses a `MockAdapter` | Zero occurrences of "mock"; obtains real adapters via `leg.adapter(...)`, asserts 3 distinct `harness_id`s, and Google ADK's own `BaseAgentConfig` deprecation warning appears in the run |
| `src/ccf/harness/` violates harness neutrality | Contains only `__init__.py` + `protocol.py`; `grep` for all four harness SDKs returns **nothing** |
| A2A admission writes directly to L3 | `admission.py` routes to `AssemblyWorker.ingest_admitted`; no graph handle |

Recorded because a review that invents findings is worse than no review — it would have sent
the phase chasing three non-defects while the real ones (below) shipped.

## Orchestrator triage

Every finding below was **independently verified against the code** before triage. Cursor's
full report is in `06-REVIEWS-cursor.md`.

### BLOCKING

**B1 — INV-CH7-47 is read down for federated products, with no decision entry.**
`src/ccf/a2a/admission.py::_run_contract_gates` passes
`engine_resolved=product.lineage.operators_invoked` — the *producer's own* claim — as the
witness for lineage strict equality, and the docstring itself says the gate is
"**structurally vacuous** here". `grep -c INV-CH7-47 docs/DECISIONS.md` = **0**.
CLAUDE.md §3.1 names "an unsurfaced decision" as blocking, and §15 requires a `D-IMPL-NN`
entry and a STOP when the whitepaper is silent or being narrowed. A validation gate the
whitepaper commits to is being reinterpreted at the trust boundary by implementation
docstring rather than by Dave's ruling.

**B2 — "lineage extended by set-union" is true only of a transient object.**
`A2AAdmissionGate.admit` computes `merged` into `AdmittedProduct.lineage`, but
`AssemblyWorker.ingest_admitted` never reads it (verified: no `lineage` reference in the
method body), and no `/src` consumer of `admitted.lineage` exists — L2 strips payload
records into `SignalEnvelope`s and the merged `ProductLineage` is discarded. ROADMAP
criterion 2 and gate row 14 claim lineage continuity as a *fabric* property (§7.2, whitepaper
L-axis). It is currently a property of a wrapper that is thrown away.

**B3 — the portability claim is broader than its evidence.**
Verified: `_drive` calls the seams directly — `inject_context` → `capture_effect(output=
dict(product.payload))` → `replay_trace(execution=leg.execution())`. No harness loop runs.
And all three adapters' governed `capture_effect` is literally `return agent.emit_effect(
output)`, so feeding the same payload three times **must** hash-equal: the emission-equality
assertion cannot detect harness-specific corruption.
**Important qualification, in fairness to 06-15:** the *consumption* axis IS real and has
teeth — the product is recovered out of each harness-native carrier, and mutating ADK to
rewrite delivered bytes turns the suite red. The defect is scope, not fraud: what is proven
is "three adapters translate one artifact into their own carriers equivalently", not
"one agent definition executed under three harnesses". ROADMAP criterion 3 and §7.3's
"portability is demonstrated, not asserted" claim the latter.

### ADVISORY (recorded, carried forward)

- **A1** — single-writer *instance* scan constructs only `TypedHttpWire`; `lf_a2a`, the
  D-IMPL-14 **default**, is covered by source scan but never instance-scanned.
  (`tests/invariants/test_a2a_single_writer.py`)
- **A2** — `_ADMISSION_TOKEN` is importable (verified: `from ccf.a2a.admission import
  _ADMISSION_TOKEN` succeeds), so `AdmittedProduct` is forgeable. Gate row 6's "type error,
  not a discipline" overclaims relative to Python's import model.
- **A3** — Claude's seam-4 `execution()` is a hand-built `ResultMessage` seeded from
  fixtures; ADK and LangGraph push values through real harness machinery. One of three legs
  is a fixture echo.
- **A4** — gate row 1 cites `tests/lints/` for the CINV-02 carve-out tests; they live in
  `tools/lints/tests/test_harness_imports.py`. The directory exists but holds different
  tests, so the citation is wrong in the same class as the mypy-evidence defects this phase
  already recorded.
- **A5** — ROADMAP/06-CONTEXT criterion 1 still names the Experience MCP edge; I.3 delivers
  none. The gate defers it honestly; the criterion text was not amended to match.
- **A6** — `D-IMPL-56` correctly open; adapters currently derive tool description/schema in
  `/runtime`. Accrues divergence risk until ruled.
- **A7** — the LangGraph adapter ships a three-node topology (`_build_graph`). Documented and
  necessary for a topology-owning harness, but it is the one place the SDK authors execution
  shape. Keep explicit so I.4 cannot inherit it as a workflow engine.

## Disposition table (added 06-22)

One row per finding. A finding is either **closed** — with the plan that closed it and the
evidence a reviewer can run — or **carried**, with a target phase *and the consequence of
leaving it open*. A carried advisory with no stated consequence is an unowned bullet, which
CLAUDE.md §3.1's "recorded in the phase deliverable's review appendix and carried forward"
does not license.

The evidence column deliberately spans the **whole** gap-closure wave, 06-18 through 06-25.
D-IMPL-59 named the structural cause behind B1, B2 and A2 — a *category* named after its
first instance — so **06-24 and 06-25 carry closure evidence for findings whose symptom an
earlier plan fixed**: B1's contract is now stated at seam level, B2's record is located at the
Peering boundary, and A2's scoped claim was carried verbatim across the rename. A disposition
table that stopped at 06-22 would omit the plans that closed the cause rather than the symptom.

| # | Class | Disposition | Closed by / carried to | Evidence, or consequence if carried |
|---|-------|-------------|------------------------|--------------------------------------|
| **B1** | blocking | **CLOSED** in-phase, on Dave's `D-IMPL-57` ruling (reading (a)) | **06-18**, contract stated at seam level by **06-24**; claims narrowed by **06-22** | `ccf.products.gates.run_federated_gates` with `GATE_LINEAGE_ATTRIBUTABILITY` replaces the vacuous strict-equality invocation; `tests/gates/test_federated_gates.py` (10 cases) and `tests/peering/test_admission_attributability.py` (6), the end-to-end case driven **through `admit`** with signature verification asserted to have *succeeded* first. Counterfactual measured: restoring the old wiring fails 3 of 6. Gate row 21 and ROADMAP criterion 2 now state the narrowed reading **with Dave's accepted consequence carried across verbatim** |
| **B2** | blocking | **CLOSED** in-phase, on Dave's `D-IMPL-58` ruling (reading (d)) | **06-19**; record located at the Peering boundary by **06-24**; claims narrowed by **06-22** (closure item 6) | `AdmissionRecord` / `ADMISSION_RECORD` (`class_id` `ccf.admission-record`) in `src/ccf/peering/admission.py`, persisted **before** `AdmittedProduct` is constructed; audit append carries the reference triple; `ccf.replay.engine.resolve_artifact` resolves it at an exact version. `tests/peering/test_admission_record.py::test_the_union_is_observed_in_persisted_state_through_the_replay_path` observes the union in **persisted state**, never on the wrapper. `src/ccf/contracts/claims.py` unchanged, asserted. Counterfactual: reverting the store write fails 5 of 14 |
| **B3** | blocking | **CLOSED as to scope** — the evidence was raised *and* the wording narrowed. Note the residual below | **06-20**; documented by **06-22** (§3.3.1, ROADMAP criterion 3) | Four adversarial cases give seam-3 and seam-4 observed failure modes, driven through the same `_drive` the honest legs use; counterfactual measured (`DID NOT RAISE`). **Residual, stated in the gate rather than only here:** all three shipped adapters' `capture_effect` remain delegations to `Agent.emit_effect`, so the honest emission equality is structurally guaranteed; and no harness loop runs. Loop-level execution is handed to `examples/03-harness-portability` in Phase 8, not dropped |
| **A1** | advisory | **CLOSED** — structurally, so a third transport joins by being discovered | **06-21**; inherited intact through **06-24**'s rename; row 3 strengthened by **06-22** | `tests/invariants/test_peering_single_writer.py` discovers `PeeringProtocol`-shaped classes structurally and keys `TRANSPORT_BUILDERS` by class; legs `[TypedHttpWire]`, `[LfA2AWire]`. `::test_every_discovered_transport_is_actually_constructed` is the count guard, its failure message naming both counts and both name-lists |
| **A2** | advisory | **CLOSED** by bounding the claim, not deleting it (D-21) | **06-21**; wording carried **verbatim** across **06-24**'s rename; row 6 amended by **06-22** | `::test_the_unforgeability_claim_is_scoped_to_the_unforced_path` asserts **both** edges — token withheld → `AdmissionBypassError`; private token imported → construction succeeds — so the wording cannot be re-strengthened without a red suite. `grep -c "unforgeable"` = 0 in the test module. `T-06-91` (forging via `_ADMISSION_TOKEN`) remains **accepted**, now pinned by a test rather than asserted in prose |
| **A3** | advisory | **CARRIED — not closed, and not claimed closed** | **Phase 8, `examples/03-harness-portability`** (where a real Claude Agent SDK execution is available) | The Claude leg's seam-4 `execution()` is a hand-built `ResultMessage` seeded from fixtures, while ADK and LangGraph push values through real harness machinery. **Consequence:** one of three seam-4 legs is a fixture echo, so the trace-equivalence evidence is **two-legged in substance**. 06-20 reduced the exposure — the corrupted-trace and dropped-trace cases give the axis a failure mode independent of how any single leg's `execution()` is built, and the trace assertion now checks attribution against each leg's own declared values — but did **not** close it. In `PHASE_I3_GATE.md` §3.3.1 and §5 |
| **A4** | advisory | **CLOSED** | **06-22** | Row 1 now cites `tools/lints/tests/test_harness_imports.py` and its four boundary tests, verified by running them (`pytest tools/lints/tests -q` → 49 passed). Recorded in §1.1 as the phase's **third** gate-evidence integrity finding — the count was raised rather than the instance absorbed — and generalized into the §4.13 citation sweep (47 paths, 63 `file::function` citations, zero unresolved) |
| **A5** | advisory | **CLOSED** | **06-22** | ROADMAP criterion 1 now names the edges I.3 delivers (L1 ingress, L4/L5 acquisition, L6 egress, distinct ArtifactStore role) and records the Experience MCP edge as **Phase 7** scope, matching `06-CONTEXT.md`'s locked deferral and the gate's own §3.1 note — which itself said the criterion "stands as written and is not amended", and has been amended to match |
| **A6** | advisory | **CARRIED** — as an open decision for Dave, which is its correct home | **`D-IMPL-56`**, ruled by Dave; relevant from **Phase 7 (I.4)** onward | Adapters derive tool description and argument schema in `/runtime` because `SkillCatalogEntry` declares neither. **Consequence:** every future adapter re-derives the same two fields, and the first to derive them differently **silently breaks harness equivalence** — the D-18 property 06-15 proves. Already surfaced in `PHASE_I3_GATE.md` §4.12 and §6 item 3 as a decision Dave is asked to rule; **cross-referenced here rather than restated**, since a second statement of an open decision is a second place for it to drift |
| **A7** | advisory | **CARRIED** — as an explicit I.4 boundary, not a note | **Phase 7 (I.4)**, against `D-IMPL-17`'s scope boundary | The LangGraph adapter ships a three-node topology in `_build_graph`. Documented and necessary for a topology-owning harness. **Consequence:** it is the one place in the SDK that authors execution *shape*, and I.4 **must not inherit it as a workflow engine** — D-IMPL-17 scopes the in-SDK Workflow primitive to in-fabric coordination and puts durable orchestration behind `OrchestrationProtocol`. Added to `PHASE_I3_GATE.md` §5 under the "prerequisites — not notes" framing |

**Counts:** 3 blocking, all closed in-phase. 7 advisory: 4 closed (A1, A2, A4, A5), 3 carried
with consequences (A3, A6, A7).

## Disposition

Per §3.1, blocking findings are fixed **inside the current phase** before approval is
requested. B1 additionally required a Dave ruling (it is a decision, not a fix), as did B2 —
both were ruled on 2026-07-27 as `D-IMPL-57` reading (a) and `D-IMPL-58` reading (d).

**All three blocking findings were closed in-phase by plans 06-18 through 06-25.** The wave
**grew** after this review was written: `D-IMPL-58` and `D-IMPL-59` landed mid-flight, and two
closures — the Peering re-description of the **seam** (06-24) and of the **skill surface**
(06-25) — sit in plans that did not exist when the findings were triaged. They belong to the
disposition because D-IMPL-59 identified the structural cause that B1, B2 and A2 were symptoms
of; closing the symptom without the cause would have left the next federation transport to
re-open all three.

**`D-GATE-I.3` remains unlogged and the phase is NOT marked gated.** No plan in this wave logs
it — asserted, not assumed: `grep -c "D-GATE-I.3" docs/DECISIONS.md` = 0. The phase is
**re-presented to Dave by 06-23**, which re-verifies the checklist row by row after these
closures. Approval authority is Dave's alone (CLAUDE.md §3.1, §2), and `/gsd-review` passing
is necessary but never sufficient.
