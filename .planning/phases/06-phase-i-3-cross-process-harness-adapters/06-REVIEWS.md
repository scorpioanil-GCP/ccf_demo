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

## Disposition

Per §3.1, blocking findings are fixed **inside the current phase** before approval is
requested. B1 additionally requires a Dave ruling (it is a decision, not a fix).
**`D-GATE-I.3` is NOT logged and the phase is NOT marked gated.** Presented to Dave.
