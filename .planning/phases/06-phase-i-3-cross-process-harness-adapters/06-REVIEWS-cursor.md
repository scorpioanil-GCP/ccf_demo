## Verdict

The phase’s own gate prose is unusually self-aware about vacuity. The failures that remain are mostly **claims that look strong because a nearby, weaker property is well tested**.

---

### BLOCKING

**1. Portability is seam translation, not “executed under three harnesses”**
- **Where:** `tests/conformance/test_harness_portability.py` `_drive` (≈245–286); Claude `execution()` in `tests/conformance/test_harness_adapter.py` (≈450–473)
- **What:** The proof calls `inject_context` → `capture_effect(output=dict(product.payload))` → `replay_trace(execution=leg.execution())`. It never drives a harness loop that consumes the agent definition and produces an effect. Claude’s “execution” is a hand-built `ResultMessage` filled from fixtures. ADK/LangGraph runs are empty vehicles with fixture-seeded model/token fields.
- **Why:** CLAUDE.md §7.3 — *“portability is demonstrated, not asserted”* — and phase claim 5. This is the XPRC-01 failure mode applied to XPRC-03.
- **Change:** Drive one real (no-model) harness execution per adapter that (a) sees the injected product, (b) exercises a bound skill through the harness tool surface, (c) produces an effect the harness handed back, (d) yields a trace the harness actually produced — then compare. Do not accept a synthetic `ResultMessage` for Claude.

**2. Cross-harness emission equality is tautological**
- **Where:** `test_the_governed_emission_is_identical_across_the_three_harnesses`; all three `capture_effect` → `agent.emit_effect(output)`; `Agent.emit_effect` (`src/ccf/agents/agent.py` ≈405–415)
- **What:** Under `governed`, every adapter is `return agent.emit_effect(output)`. `emit_effect` only wraps the mapping. Feeding the same `product.payload` three times must hash-equal.
- **Why:** Criterion “equivalent… under all three harnesses” with teeth — this assertion cannot detect harness-specific emission corruption.
- **Change:** Recover the effect from a harness-owned path (LangGraph effect node / ADK tool callback / Claude permission+tool path) and compare those recovered values.

**3. A2A lineage set-union is computed, tested, then thrown away**
- **Where:** `A2AAdmissionGate.admit` builds `merged` → `AdmittedProduct.lineage`; `AssemblyWorker.ingest_admitted` (`src/ccf/assembly/worker.py` ≈391–489) never reads `admitted.lineage`; only tests touch it (`tests/crossproc/test_a2a_exchange.py` ≈747–775)
- **What:** Gate row 14 / XPRC-02 claim “lineage extends by set-union” is true of a transient object. L2 strips payload records into `SignalEnvelope`s and drops the merged `ProductLineage`. No `/src` production consumer of `admitted.lineage` exists.
- **Why:** CLAUDE.md §7.2 / whitepaper L-axis — continuity must hold in fabric state, not on a discarded admission wrapper. Classic asserted-not-demonstrated.
- **Change:** Make `ingest_admitted` (or the subsequent product path) persist/propagate the merged lineage into consumer graph/product lineage, and assert union on **post-ingest** state — not on `AdmittedProduct` alone.

**4. INV-CH7-47 is self-witnessed on the A2A path — and never decided**
- **Where:** `A2AAdmissionGate._run_contract_gates` (`src/ccf/a2a/admission.py` ≈847–883), especially `engine_resolved=product.lineage.operators_invoked`
- **What:** The gate docstring admits lineage strict equality is “structurally vacuous” across the trust boundary. Signature accountability is offered as substitute. No `D-IMPL-*` entry records Dave accepting that substitution.
- **Why:** Whitepaper fidelity + “surface gaps; do not paper over them.” A silent reading of INV-CH7-47 for federated products is an unsurfaced decision.
- **Change:** Open a `D-IMPL` (or close one): either (a) require an independent consumer-side witness, (b) formally narrow INV-CH7-47 for A2A with Dave’s ruling, or (c) refuse to call `run_gates` with a self-witness and gate differently.

---

### ADVISORY (but sharp)

**5. Criterion-4 instance scan is typed-HTTP-only; LF A2A is the ruled default**
- **Where:** `tests/invariants/test_a2a_single_writer.py` `test_a_constructed_transport_holds_no_fabric_write_surface` (≈193–221); discovery guard asserts `typed_http` only (≈150–153)
- **What:** Import/identifier scans cover `lf_a2a` via discovery; the live constructed-instance half only builds `TypedHttpWire`. D-IMPL-14’s default wire is not instance-scanned.
- **Why:** Invariant held asymmetrically — discipline for the default transport.
- **Change:** Construct `LfA2AWire` the same way; require `lf_a2a` in the discovery guard.

**6. `AdmittedProduct` “unforgeable” is privacy convention, not construction**
- **Where:** `_ADMISSION_TOKEN` in `src/ccf/a2a/admission.py` (≈333–373); tests only pass a wrong `object()` token
- **What:** `from ccf.a2a.admission import _ADMISSION_TOKEN` forges an admitted product. Gate row 6’s “type error, not a discipline” overclaims relative to Python’s import model.
- **Why:** Same class as D-21 overclaiming — strong wording, weaker mechanism.
- **Change:** Scope the claim to “SDK call sites + annotation,” or harden (e.g. gate-only factory module, no importable token).

**7. Claude seam-4 “harness carried” evidence is fixture echo**
- **Where:** `build_harness_leg` Claude `execution()` (≈450–473); `test_seam_4_reads_what_the_harness_carried_not_what_the_adapter_held` (≈1031–1056)
- **What:** For Claude, the test constructs `ResultMessage` with `reported_model` / `session_id`, then asserts those strings appear in the execution and in the trace. ADK/LangGraph at least push values through harness machinery; Claude does not.
- **Why:** Vacuous for one of three legs of a three-harness claim.
- **Change:** Same as finding 1 — Claude needs a real SDK execution artifact, or the Claude leg must be explicitly scoped weaker in the gate (not claimed equivalent).

**8. Governed replay equality is mostly shared inputs to `build_replay_record`**
- **Where:** `_drive` passes `execution=_execution(definition)` (same for all legs), same agent conditioning, same bindings; only `product=recovered` and `harness_trace` vary
- **What:** Product recovery from carriers is real (ADK brace hazard). Everything else in the governed set is equal because the test fed the same fabric-side arguments three times.
- **Why:** Finding D in the brief — equality by construction of the record builder, not of harness behavior.
- **Change:** Derive more governed fields from harness-visible outcomes (or stop claiming “equivalent replay records from three harness runs”).

**9. ROADMAP/CONTEXT still name Experience MCP; I.3 delivers none**
- **Where:** `docs/ROADMAP.md` I.3 scope; `06-CONTEXT.md` criterion 1; gate §3.1 deferral
- **What:** Honest deferral in the gate; criterion text still lists Experience. Not in your abbreviated claim list, but it is a named Phase 6 success-criterion leg with zero evidence.
- **Change:** Amend ROADMAP/CONTEXT criterion 1 to match the deferral, or deliver a thin Experience-client edge.

**10. `D-IMPL-56` correctly open — adapters invent tool surface**
- **Where:** `_tool_description` ×3 in adapters; `SKILL_ARGUMENT_SCHEMA` in Claude adapter; `docs/DECISIONS.md` D-IMPL-56
- **What:** Not prompt prose, but Control Plane schema workarounds in `/runtime`. Gate logs it; still accrues divergence risk for example 03.
- **Change:** Dave rules schema fields on `SkillCatalogEntry` before I.4 skill-binding at workflow nodes.

**11. Gate row 1 mis-cites evidence location**
- **Where:** `docs/PHASE_I3_GATE.md` row 1 claims `tests/lints/`; actual tests are `tools/lints/tests/test_harness_imports.py` (four carve-out cases ≈90–113)
- **What:** Evidence exists; the gate cites the wrong tree — same class as the mypy evidence defects they already recorded.
- **Change:** Fix the citation.

**12. LangGraph adapter ships a three-node topology**
- **Where:** `LangGraphAdapter._build_graph` (`runtime/ccf_runtime/adapters/langgraph/adapter.py` ≈366–403)
- **What:** Tension with “CCF never ships a loop.” Mitigated by D-IMPL-24 + documented necessity; still the one place the SDK authors harness execution shape rather than only translating.
- **Change:** Keep the boundary explicit in DESIGN/docs so I.4 orchestration cannot inherit this graph as a workflow engine (already noted; enforce in I.4 planning).

---

### What I did *not* find (on the axes you cared about)

- No domain half-lives, prompts, or agent definitions in `/src` from this pass.
- CINV-02 carve-out boundary tests are real (wrong path in the gate, not missing).
- ArtifactStore WAL-inclusive digest + sensitivity guard look load-bearing, not decorative.
- `effects: unsupported` has a non-declaration half in conformance.
- MCP L1 / L4–L5 / L6 / ArtifactStore role split has executable edges; Experience is the explicit hole.

---

### Bottom line for Dave

Do not treat the 940-pass / lint-green surface as the gate. The three claims that fail the phase’s own “what would fail if broken” standard are:

1. **harness portability as execution under three harnesses**,
2. **A2A lineage continuity as a fabric property**,
3. **INV-CH7-47 meaning under federation**.

Everything else is either honestly deferred, correctly logged as open (`D-IMPL-56`), or a narrower scan hole. I would **reject `D-GATE-I.3`** until at least findings **1** and **3** are fixed or formally re-scoped with a decision entry; finding **4** should not ship as silent doctrine.
