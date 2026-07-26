# Phase I.1 — Fabric Core: Gate Package

**Phase:** 4 (Phase I.1 — Fabric Core) · **Branch:** `phase-i1` · **Assembled:** 2026-07-25
**Protocol:** CLAUDE.md §3.1 (self-review → triage → present to Dave → `D-GATE-I.1` → merge)
**Gate bar:** 04-CONTEXT.md **D-17** — the FEASIBILITY.md §11 per-invariant checklist green,
each named invariant mapping to a *named passing* test or lint. Line coverage is reported
informationally; there is **no numeric coverage gate**.

> **Status: APPROVED.** Dave approved this gate package on 2026-07-25 (CLAUDE.md §3.1
> step 3). The `D-GATE-I.1` entry is logged in docs/DECISIONS.md and `phase-i1` is merged
> to `main` with a merge commit referencing D-GATE-I.1.

---

## 1. Verification Matrix — Execution Record

All legs executed on `phase-i1` (64 commits ahead of `main`) in the project `.venv`
(Python 3.12, dev + chroma extras, Docker available for the Postgres leg).

| Leg | Command | Result |
|-----|---------|--------|
| Full suite (all markers) | `.venv/bin/pytest tests -q` | **383 passed, 3 skipped** (exit 0) |
| Postgres leg, mandatory | `CCF_REQUIRE_POSTGRES=1 .venv/bin/pytest tests -q -m postgres` | **12 passed** — the env var turns a silent skip into a failure, so this proves a real `postgres:16` container ran |
| Chroma leg | `.venv/bin/pytest tests -q -m chroma` | **20 passed** |
| Property suite, CI profile | `HYPOTHESIS_PROFILE=ci .venv/bin/pytest tests/properties -q` | **73 passed** |
| Invariant lints (CINV-01/02/03) | `.venv/bin/python -m tools.lints --all` | **exit 0, zero findings** |
| Lint checkers' own unit tests | `.venv/bin/pytest tools/lints/tests -q` | **45 passed** |
| Strict typing | `.venv/bin/mypy --strict src runtime` | **Success: no issues found in 55 source files** |
| Coverage (informational, D-17 — no gate) | `.venv/bin/pytest tests --cov=src/ccf --cov=runtime/ccf_runtime` | **97%** (1950 statements, 61 uncovered) |

**The 3 skips are deliberate and load-bearing.** They are the CINV-04 checks that are
*not yet applicable* in I.1, emitted as skips carrying their activating phase rather than
silently omitted, so "suite green" cannot be misread as "invariant holds":

| Skipped check | Activating phase | Reason string emitted |
|---------------|------------------|------------------------|
| `hitl-action-capture` | **Phase I.4** | every HITL action lands in replay dimension 2 by construction (CLAUDE.md §8.2) |
| `workflow-trace-capture` | **Phase I.4** | every workflow execution trace lands in replay dimensions 4 and 5 by construction (CLAUDE.md §8.1) |
| `skill-set-capture` | **Phase I.2** | every skill grant/revocation and the in-force skill-set land in replay dimension 4 by construction (CLAUDE.md §6.2) |

---

## 2. Per-Invariant Checklist (D-17 gate bar; rows transpose FEASIBILITY.md §11)

| # | Invariant | Named verification mechanism | Result |
|---|-----------|------------------------------|--------|
| 1 | **Single-writer enforcement — static gate** | `tools/lints/harness_imports.py` rule `cinv02-graph-writer` — the `ccf.graph._writer` module restriction, `WRITER_OK_MODULES = {ccf.assembly, ccf.boot}`, run by `python -m tools.lints --all`. In practice only `ccf.boot` imports it today. **Scope note (review finding R-1):** `mypy --strict` is a *supporting* build step (it types the reader/writer Protocol split), **not** an enforcer of "no non-L2 `GraphWriter` reference" — no mypy plugin implements that restriction. The load-bearing static gate is the CINV-02 lint alone. | ✅ zero findings; mypy clean. Mutation-probed: see §6.2 |
| 2 | **Single-writer enforcement — runtime backstop** | `tests/invariants/test_single_writer_boot.py` — boot-check assertion that exactly one `GraphWriter` is constructed per graph identity; a second-writer fixture fails boot (`BootToken`, `SingleWriterViolation`) | ✅ passing |
| 3 | **Composition-preservation `(A∘B)(G) = A(B(G))`** | `tests/properties/test_composition.py` — Hypothesis property harness parametrized over **every shipped operator pair** enumerated from the `OperatorRegistry` via `itertools.product`, asserting bit-for-bit equality on `canonical_bytes`; plus curated banking edge graphs (D-14) | ✅ passing, `ci` profile |
| 4 | **Staged-execution equivalence** (FEASIBILITY §11 D-08 test class 2) | `tests/properties/test_staged_vs_direct.py` — two-stage projection plan output == direct composition output under fixed `(graph_state, control_plane_config, temporal_boundary)` | ✅ passing |
| 5 | **Three validation gates** — empty-operator guard → lineage strict equality → TTL bounds | `tests/gates/test_product_gates.py` — the three rejection paths (`EmptyOperatorRefusal`, `LineageMismatchRefusal`, `TTLRefusal`), the `GateBypassError` construction guard, and the Control-Plane registration test that an unregistered `MAX_TTL` fails product-class registration (D-IMPL-39) | ✅ passing |
| 6 | **Algorithmic ⇄ Semantic Alternation** | **CINV-03** — `tools/lints/algorithmic.py`, keyed on `__ccf_mode__ = "algorithmic"`, rejecting any import of `ccf.llm.LLMClientProtocol` or an LLM vendor SDK; own tests in `tools/lints/tests/test_algorithmic.py` | ✅ zero findings; 45 checker tests pass |
| 7 | **Audit-by-construction / replay-by-construction (CINV-04)** | Two distinct layers, separated here per review finding R-2. **(a) The behavioral assertions** — the load-bearing tests: `tests/replay/test_serve_writes_replay.py::test_a_failing_store_yields_no_delivery` (a failing replay append yields *no* delivery), `::test_serve_writes_the_record_then_delivers` (ordering), `::test_the_delivery_capability_cannot_be_constructed_directly` (`CapabilityForgeryError` closes the forged path), `tests/invariants/test_single_writer_boot.py::test_booting_the_same_graph_twice_raises`, and `tests/replay/test_engine_rehydration.py::test_the_product_replays_exactly_after_the_graph_has_moved_on`. **(b) The status registry** — `tests/invariants/test_replay_by_construction.py` holds the CINV-04 check registry and asserts its *integrity* (every active check names an owning test that exists; every deferred check names its activating phase). It does not itself prove the behavioral invariants; it prevents the gate report going stale when a named test is renamed or deleted. Deferrals: HITL + workflow → **I.4**, skill-set → **I.2** | ✅ 3 active behavioral checks pass; registry integrity passes; 3 deferrals explicitly not-yet-applicable, never silently absent |
| 8 | **No-Hardcoding Rule** | **CINV-01** — `tools/lints/no_hardcoding.py`: prompt-shaped-literal heuristics + numeric-table/dict constant detection + factory-bypass AST check over `/src`, `/runtime`, `/examples`, with the versioned reviewed allowlist `tools/lints/allowlist.yaml` (D-08; findings carry `[fp=<sha256>]` so entries key on the literal, not the line) | ✅ zero findings |
| 9 | **Zero harness imports in core** | **CINV-02** — `tools/lints/harness_imports.py` import lint over `/src` against the configured harness deny-list (Google ADK, Claude Agent SDK, LangGraph) | ✅ zero findings |
| 10 | **Hash-verified re-hydration** (FEASIBILITY §11 D-09 test class) | `tests/replay/test_engine_rehydration.py` — replaying a recorded decision reproduces artifacts whose content hashes match the pinned hashes; divergence **raises**, never returns as a value | ✅ passing |
| 11 | **Backend parity** (D-16) | One parametrized conformance suite run identically on both substrates: `tests/conformance/test_graphstore.py` (SQLite + Postgres), `tests/conformance/test_similarity_index.py` (token-overlap + sqlite-vec + Chroma), `tests/conformance/test_artifactstore.py` (file store; the I.3 MCP store implements against the same suite) | ✅ passing on every parametrization |

**Every named invariant in CLAUDE.md §3.1's Phase I review list has a row above, and every
row names an existing, passing test or lint path.** The D-17 gate bar is met.

---

## 3. Requirement Coverage

### FABR — fabric core

| Req | Commitment | Evidence |
|-----|------------|----------|
| **FABR-01** | Context Graph primitive, Postgres + SQLite reference backends (D-IMPL-02), idempotent upsert, multi-source lineage set-union, single-writer at boot | `src/ccf/graph/` (Protocols, `_writer.py`, `backends/sqlite.py`, `backends/postgres.py`, shared `reader.py`), `src/ccf/assembly/worker.py`, `src/ccf/boot.py`; six-semantics conformance suite green on **both** substrates (plan 04-04, 04-10) |
| **FABR-02** | Operator algebra, four canonical categories, composition-preservation for every shipped pair | `src/ccf/operators/` (`base.py`, `categories.py`, `params.py`, `registry.py`, `planner.py`, `compose`); checklist rows 3–4 (plans 04-05, 04-06) |
| **FABR-03** | Projection engine Π with structural typing, two-stage execution | `src/ccf/projection/plan.py` (structural `ProjectionPlan` Protocol: `required_operators()` + `invoke()`), `src/ccf/projection/engine.py`; checklist row 4 (plan 04-05) |
| **FABR-04** | Context Product Contract base `extra=forbid` + the three validation gates | `src/ccf/contracts/base.py` (`CCFContract`, frozen + `extra=forbid`), `src/ccf/products/contract.py`, `src/ccf/products/gates.py`; checklist row 5 (plan 04-05) |
| **FABR-05** | λ_c / D_c computation, every value from Control Plane config, zero hard-coded tables in `/src` | `src/ccf/halflife/decay.py`, `src/ccf/halflife/debt.py` (basic + extended forms, CAR routing signals, `DebtFactorScorerProtocol` with `(scorer_id, scorer_version)` replay pinning per D-IMPL-47); rates live in `tests/fixtures/banking/halflife.yaml`, never `/src` — enforced by CINV-01 (plan 04-07) |
| **FABR-06** | Five-dimension Decision Replay record + replay engine | `src/ccf/replay/record.py` (all five dimensions per whitepaper §7.10.1), `src/ccf/replay/serve.py`, `src/ccf/replay/engine.py`, `src/ccf/replay/snapshots.py` (D-IMPL-06 logical snapshot); checklist rows 7, 10 (plans 04-05, 04-08) |
| **FABR-07** | Control Plane as in-process versioned registry, remote extension point | `src/ccf/controlplane/registry.py` (append-only, content-hash-as-version-id, no silent defaults, `ControlPlaneMissing`, `ReplayResolver`, actor attribution), `artifacts.py`, `audit.py` (append-only `AuditLog` — the audit plane per whitepaper §7.8.2), `ControlPlaneProtocol` as the remote seam (plans 04-03, 04-07) |
| **FABR-08** | ArtifactStore Protocol + file-backed dev impl | `src/ccf/artifacts/protocol.py` (hybrid content-hash + versioned-URI addressing per D-IMPL-26; `MovingTargetRefused` closes `@latest`), `src/ccf/artifacts/file_store.py`; conformance suite `tests/conformance/test_artifactstore.py`. **⚠ Scope-amended — see §4** (plans 04-05, 04-08) |
| **FABR-09** | CDC→G ingress reference (Pattern 1) | `runtime/ccf_runtime/cdc/adapter.py` + `envelope_map.py` (async, deterministic `envelope_id`, typed rejection, **no graph handle**); `tests/integration/test_cdc_slice.py` (plan 04-09) |

### CINV — CI invariants

| Req | Evidence |
|-----|----------|
| **CINV-01** No-Hardcoding lint | checklist row 8 — `tools/lints/no_hardcoding.py` + `allowlist.yaml`, blocking in CI from the first fabric commit (D-07) |
| **CINV-02** Zero-harness-imports lint | checklist row 9 — `tools/lints/harness_imports.py` (also hosts the single-writer static gate, row 1) |
| **CINV-03** `@algorithmic` lint | checklist row 6 — `tools/lints/algorithmic.py` |
| **CINV-04** Replay-by-construction checks | checklist rows 2, 7 — active checks pass; three deferrals explicit with phase pointers |

### ROADMAP Phase 4 success criteria

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | Graph on both backends, idempotent upsert, lineage accumulation, single-writer at boot; only L2 holds a write handle | ✅ FABR-01 + rows 1–2 |
| 2 | Four operator categories, composition-preservation for every pair; two-stage projection via structural typing | ✅ FABR-02/03 + rows 3–4 |
| 3 | `extra=forbid` + three gates; λ_c/D_c entirely from Control Plane config, zero hard-coded tables in `/src` | ✅ FABR-04/05 + rows 5, 8 |
| 4 | Five-dimension replay written at serve time by construction; ArtifactStore Protocol against the **file-backed dev impl**; CDC→G ingress | ✅ **as amended** — see §4 |
| 5 | CI invariant scaffolding green (CINV-01..04) | ✅ CINV table above |

---

## 4. Recorded Scope Amendments

Two amendments are in force for this gate. Both were ruled by Dave during phase context
(04-CONTEXT.md, 2026-07-25) and are already recorded in the tree — they are surfaced here so
the gate review verifies the *amended* criteria, not the originals.

**D-03 → logged as `D-IMPL-52` (Dave, 2026-07-25).** The v0 examples suite becomes a
**horizontal mix of domains**, with example 00 and the I.1 slice fixtures in a **banking**
scenario — replacing CLAUDE.md §9's single-neutral-domain rule. CLAUDE.md §9 was amended and
`docs/DECISIONS.md` carries the ruling (plan 04-01). The I.1 fixtures under
`tests/fixtures/banking/` are the realization; banking also supplies the realistic
policy/regulatory pressure the slice-realism bar (D-02) demanded.

**D-12 — ArtifactStore scope narrowed for I.1.** Phase 4 criterion 4 previously required the
ArtifactStore Protocol to work against "both the file-backed dev impl **and the MCP-backed
reference impl**." I.1 scope is now **Protocol + file-backed dev impl only**; the MCP-backed
reference implementation is **deferred to Phase 6 (I.3)**, where it lands with the rest of the
MCP machinery. The deferral has a receiving deliverable: it was added as **criterion 5 of
Phase 6** in `.planning/ROADMAP.md`, and Phase 8 criterion 3 (example 07's file-backed →
MCP-backed swap) depends on it. The ArtifactStore conformance suite is written
factory-parametrized precisely so the I.3 store adds a fixture param and changes no test body.

**FABR-08 is therefore partially delivered by design, not by omission.** Its requirement text
still names the MCP-backed impl; the I.1 portion (Protocol + file-backed impl + conformance
suite) is complete, and the MCP-backed portion is carried to Phase 6.

---

## 5. Whitepaper-Fidelity Spot Check (CLAUDE.md §3.1, Phase I criterion)

Method: sample public classes across L1–L6 and the SDK-extension surfaces, read each
docstring's cited section, and verify the cited section **actually specifies the implemented
contract** (rather than merely being topically adjacent). 12 classes sampled — all layers
represented.

| # | Class | Cited section | Does the cited section specify the implemented contract? |
|---|-------|---------------|-----------------------------------------------------------|
| 1 | `ccf.contracts.base.CCFContract` | Whitepaper §6.3 | ✅ §6.3 specifies the Context Product Contract; §7.6 commits the typed **base** the per-product subclasses inherit and where "cross-cutting invariants live on the base where they can be validated once." Frozen + `extra=forbid` is that closed-world base. |
| 2 | `ccf.signal.envelope.SignalEnvelope` | Whitepaper §7.1 | ✅ §7.1 commits L1 as the Signal Layer with a normalized event envelope as the L1→L2 handoff; the superset shape is D-IMPL-33. |
| 3 | `ccf.assembly.worker.AssemblyWorker` | Whitepaper §7.1, §7.3 | ✅ §7.3 states verbatim: "only the Assembly worker writes to the enrichment surface — enforced by dependency injection, not convention," and "every read-path service … is constructed without a write handle." The worker is the sole `GraphWriter` holder. |
| 4 | `ccf.graph.protocols.GraphView` | Whitepaper §7.3, §7.4 | ✅ §7.3 commits the six-tuple `G(E,R,T,P,Π,L)` with valid-time/observed-time reconciliation; §7.4 requires operators be read-only over graph state. An immutable as-of view is exactly that read surface. |
| 5 | `ccf.graph.protocols.GraphWriter` | INV-CH7-10 / DESIGN.md §2A.5.3 (whitepaper §7.3) | ✅ §7.3's compound unique index on `(tenant_id, entity_uri)`, idempotent upsert, and set-union lineage accumulation are each implemented on the writer path; supersession-not-deletion is the §7.3 base-graph invariant. |
| 6 | `ccf.operators.base.ContextOperator` | Whitepaper §7.4 | ✅ §7.4 commits the four canonical categories, `(A∘B)(G) = A(B(G))`, "side-effect-free-read-only-sync contract against the graph," and per-intermediate lineage provenance sub-chains. The pure view→view signature with an explicit `temporal_boundary` and a provenance sub-chain realizes all three. |
| 7 | `ccf.projection.plan.ProjectionPlan` | DESIGN.md §2B.2 (whitepaper §7.5) | ✅ §7.5 commits `ProjectionPlan` as a **structural-interface pattern** and formalizes the two-stage execution model. The Protocol is structural (`required_operators()` + `invoke()`), not nominal. |
| 8 | `ccf.projection.engine.ProjectionEngine` | DESIGN.md §2B.1 (whitepaper §7.5) | ✅ §7.5's two-stage model — operator plan then Π — is the engine's execution order; §7.5's "subgraph substitution, not filtering" is preserved because Π receives a composed `GraphView` and returns a projected structure. |
| 9 | `ccf.products.contract.ContextProductContract` | Whitepaper §6.3, §7.6 | ✅ §7.6 commits the Contract base with the declared fields the delivery layer requires before serving; the three-gate sequence is the SDK's enforcement of those declarations (INV-CH7-46/47/48). |
| 10 | `ccf.halflife.decay.Observation` / `debt.DebtFactors` | Whitepaper §7.7 | ✅ §7.7 commits the formal decay formula keyed to **observation type** (not claim), the basic and extended `D_c` forms, and Conditional Assessment Routing as the `D_c`→invocation-policy translation. `DebtSignal` is the CAR routing state. |
| 11 | `ccf.replay.record.DecisionReplayRecord` | Whitepaper §7.10 (INV-CH7-79/80) | ✅ §7.10 enumerates exactly the five dimensions the record carries — Context Fabric Snapshot, Policy Bindings Snapshot, Model Version Record, Perspective Conditioning, Content Generation Path — and states the record is enforced "at the moment of assembly," which is why `serve()` writes it rather than a post-hoc hook. |
| 12 | `ccf.artifacts.protocol.ArtifactStoreProtocol` | **CLAUDE.md §7.4** (SDK extension, correctly labeled) | ✅ §7.4 requires immutable, versioned artifacts, content-addressed **or** versioned-URI addressing (D-IMPL-26 rules *hybrid*), replay resolving exact versions and **never `@latest`** (`MovingTargetRefused`), and the store never becoming a second writer to L3. |

**Result: 12/12 verified, zero failures.** No sampled class cites a section that does not
specify its contract, and every SDK-extension class cites *CLAUDE.md* with the extension
labeled — never a whitepaper section it could not be derived from.

**Citation-coverage census (secondary observation).** 130 public top-level classes across
`/src` and `/runtime`. 82 carry a spec citation in the class docstring; 48 do not — these are
exception types, parameter/DTO value records, and backend implementation classes. **Every one
of the 48 lives in a module whose module-level docstring carries the citation** (verified
mechanically across all 20 owning modules). Recorded as advisory finding A-1 in §7.

---

## 6. Self-Review (§3.1 step 1)

`/gsd-review --phase "Phase I.1" --all` was run against the phase deliverables. Reviewer
availability and outcome:

| Reviewer | Status | Outcome |
|----------|--------|---------|
| In-repo verification matrix (§1) | ✅ ran | Authoritative leg — all eight commands green |
| Structural self-audit against §3.1 Phase I criteria | ✅ ran | Per-criterion results in the table below |
| Whitepaper-fidelity spot check (§5) | ✅ ran | 12/12 |
| Lint mutation probe (§6.2) | ✅ ran | CINV-02 proven to be a real gate, not a no-op |
| **Codex** (gpt-5.5) | ✅ ran (2nd attempt) | 2 findings raised as blocking — **1 upheld** (R-2), **1 refuted** by the code (see §6.1) |
| **Cursor** | ✅ ran (2nd attempt) | **NO BLOCKING FINDINGS**; 7 advisories, **3 upheld as gate-doc accuracy defects** (R-1, R-3, R-4) |
| **Gemini** | ✅ ran | **NO BLOCKING FINDINGS**; 5 advisories, all corroborating |

### §3.1 Phase I criteria, checked one by one

| §3.1 Phase I requirement | Result |
|---------------------------|--------|
| No-Hardcoding lint green | ✅ CINV-01, zero findings |
| Harness import lint green | ✅ CINV-02, zero findings |
| `@algorithmic` lint green | ✅ CINV-03, zero findings |
| Composition-preservation tests for **every shipped operator pair** | ✅ all 4 shipped operators, all 16 ordered pairs. **Precise claim (review finding R-3):** pairs are `itertools.product` over the `shipped_operators()` registry built in `tests/properties/strategies.py`, so *pair* coverage is n² automatically — but that registry is assembled by hand, not discovered from `/src`. A newly shipped operator must be added to `shipped_operators()`; adding it then earns its 2n new pairs for free. Coverage is complete today; the residual maintenance obligation is recorded as advisory A-7. |
| Replay-by-construction checks (HITL, workflow, skill-set capture) | ⚠️ **partially applicable in I.1 by design** — the three checks belong to surfaces I.1 does not ship (HITL/workflow → I.4, skilling → I.2). They exist in the registry and emit phase-tagged skips. The I.1-applicable leg (serve-path replay capture) is active and green. |
| Full §9 examples suite passing end-to-end, incl. the two-harness assertion | ⚠️ **not in I.1 scope** — the §9 examples suite is Phase 8 and the harness adapters are Phase 6 (I.3). I.1's analogue is the **proto-quickstart** (`tests/integration/test_proto_quickstart.py`, D-02), the private fixture precursor of `examples/00-quickstart`. |
| Whitepaper-fidelity spot check | ✅ §5, 12/12 |

The two ⚠️ rows are **milestone-scope facts, not defects**: CLAUDE.md §3.1's Phase I criteria
are written for Phase I as a whole, and Phase I is sliced into I.1–I.5 (Phases 4–8). Each ⚠️
item has a named receiving phase. They are recorded as advisory findings A-2 and A-3 so the
carry-forward is explicit rather than assumed.

### 6.1 Cross-AI review — execution record and finding dispositions

Per CLAUDE.md §3.1, Codex authenticates with `CODEX_API_KEY` (not `OPENAI_API_KEY`) and
Cursor with an exported `CURSOR_API_KEY`, both sourced from `/home/parkave/homecams_v2/.env`
— **never committed to this repo**.

**Environment problems encountered and worked around (recorded per §3.1 rather than hidden):**

- **Codex, attempt 1 — failed.** Login succeeded (`printenv CODEX_API_KEY | codex login
  --with-api-key`), but the Linux sandbox could not start: `bwrap: loopback: Failed
  RTM_NEWADDR: Operation not permitted`. Codex correctly refused to review files it could not
  read and returned "I cannot honestly say NO BLOCKING FINDINGS without access to the files."
- **Codex, attempt 2 — succeeded.** Re-run with the review material piped inline on stdin, so
  no repo file access was required. This produced a substantive review.
- **Cursor, attempt 1 — failed.** Workspace-trust prompt refused the non-interactive run.
  (Note for CLAUDE.md §3.1: the installed Cursor version *does* accept `--trust` / `--yolo` /
  `-f`, contradicting the standing note that "`--trust` does not exist"; `-f` worked.)
- **Cursor, attempt 2 — succeeded** with `cursor agent -p -f --mode ask`.
- **Gemini — succeeded** first attempt, added as a third reviewer.

**Finding dispositions.** Four findings had a real kernel and were **fixed in this document
before presentation** (§3.1 step 2 — blocking findings are fixed inside the phase). All four
were gate-document accuracy defects; **none was a code defect**, and no code changed.

| ID | Raised by | Finding | Disposition |
|----|-----------|---------|-------------|
| **R-1** | Cursor | Checklist row 1 claimed `mypy --strict` "rejects non-L2 `GraphWriter` type references". There is no mypy plugin implementing that restriction; the real static gate is the CINV-02 lint. | **Upheld — row 1 rewritten.** mypy is now described as a supporting build step, not an enforcer. The invariant is still enforced; only the doc's account of *what* enforces it was wrong. |
| **R-2** | Codex | Checklist row 7 pointed at `tests/invariants/test_replay_by_construction.py` as if it proved the serve-path invariant. That module is a status **registry** plus an integrity check; the behavioral proof lives in `tests/replay/test_serve_writes_replay.py`. As written the row could read as a tautological green. | **Upheld — row 7 rewritten** to separate (a) the named behavioral tests from (b) registry integrity. Gemini independently flagged the same module as a *strength* (it prevents stale gate reports); both readings are correct and the row now states both. |
| **R-3** | Cursor | §6 claimed "a new operator cannot escape composition coverage by list omission". Pairs are enumerated from a hand-built `shipped_operators()` fixture, so the *pair* expansion is automatic but registry membership is not. | **Upheld — claim narrowed** and the residual maintenance obligation recorded as advisory A-7. Today's coverage (4 operators, 16 ordered pairs) is complete. |
| **R-4** | Cursor | §7 stated both amendments are recorded in `docs/DECISIONS.md`. Only D-03/`D-IMPL-52` is; **D-12 lives on `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and 04-CONTEXT.md**, not in `DECISIONS.md`. | **Upheld — §7 corrected** to state each amendment's actual location. Verified: `grep "D-12" docs/DECISIONS.md` returns nothing. |
| **R-5** | Codex | Claimed the single-writer allowlist is inconsistent — doc says `ccf.assembly` + `ccf.boot`, but a test asserts the only importer is `ccf/boot.py`. | **Refuted by the code.** `tools/lints/harness_imports.py` defines `WRITER_OK_MODULES = frozenset({"ccf.assembly", "ccf.boot"})` — exactly what the doc claims. The test asserts the *current factual* importer set (only `boot.py` imports it today), which is narrower than the permitted set by circumstance, not by contradiction. Row 1 now states both facts explicitly so the distinction cannot be misread again. |

Codex's two remaining points (CINV-04 row wording; inability to judge lint strength from the
inline excerpt) are absorbed by the R-2 fix and by the mutation probe in §6.2 respectively.
Cursor's advisories 5–7 and Gemini's five advisories required no change; the substantive ones
are carried into §7.

### 6.2 Lint mutation probe

A gate that reports "zero lint findings" proves nothing unless the lint can fail. CINV-02 was
mutation-probed: `import langgraph` was appended to `src/ccf/operators/base.py`, and
`python -m tools.lints --all` was re-run.

```
1 CCF invariant violation(s).
src/ccf/operators/base.py:179 cinv02-harness harness import 'langgraph' is forbidden in
  core (CLAUDE.md §7.3); bind harnesses in runtime/adapters/<harness>/ instead
EXIT=1
```

The probe was reverted and the lint returned to exit 0 (`git status` clean). **The zero-finding
result in §1 is a real green, not a lint that never fires.** The checkers additionally carry 45
of their own unit tests covering positive-detection cases.

**Threat T-04-27 check (credential disclosure):** the diff for this plan touches only
`docs/PHASE_I1_GATE.md` and `.gitignore`; no key-shaped material enters the tree. Keys were
sourced into the process environment only, never written to a file in the repo.

---

## 7. Finding Triage (§3.1 step 2)

Classification per §3.1: **blocking** = violated invariant, whitepaper-fidelity defect,
missing deliverable element, or unsurfaced decision. **advisory** = style, sequencing, or
deferred-scope observation.

### Blocking findings

**None outstanding.** Four findings with a real kernel (R-1 … R-4, §6.1) were raised by the
cross-AI reviewers and **fixed in this document before presentation**, per §3.1 step 2. All
four were accuracy defects in the gate document's account of its own evidence; **no code
defect was found by any reviewer, and no source file changed as a result of the review.**

After those fixes: every named invariant maps to a named passing test or lint (§2); the
fidelity spot check is 12/12 (§5); no deliverable element of Phase 4 is missing against the
amended criteria (§3, §4); and no decision is unsurfaced.

**Amendment recording — precise locations** (corrected per R-4):

| Amendment | Where it is recorded |
|-----------|----------------------|
| **D-03** → `D-IMPL-52` | `docs/DECISIONS.md` (the ruling, approver Dave, 2026-07-25); CLAUDE.md §9 amended in place; 04-CONTEXT.md |
| **D-12** (MCP ArtifactStore → I.3) | `.planning/ROADMAP.md` (Phase 4 criterion 4 amendment note **and** Phase 6 criterion 5, the receiving deliverable); `.planning/REQUIREMENTS.md` (FABR-08); 04-CONTEXT.md. **Not in `docs/DECISIONS.md`** — it is a phase-scope amendment carried on the roadmap, not a `D-IMPL-NN` ruling. Flagged for Dave in §8 in case he wants it mirrored into the decision log. |

### Advisory findings (carried forward per §3.1)

| ID | Finding | Disposition |
|----|---------|-------------|
| **A-1** | 48 of 130 public classes carry their spec citation at **module** level rather than in the class docstring (CLAUDE.md §11 says "cite the section in the docstring of every public class"). All 48 are exception types, DTO/parameter records, or backend impl classes; all 48 modules are cited. | Advisory. No primitive-bearing class is uncited, and no citation is *wrong* — the gap is placement, not fidelity. Carried to I.2: extend the citation convention to auxiliary types as those modules are next touched. |
| **A-2** | The §3.1 CINV-04 criterion (HITL / workflow / skill-set replay capture) is only partially exercisable in I.1. | Advisory — milestone scope. Receiving phases named in-code: skill-set → **I.2**, HITL + workflow → **I.4**. The deferrals are structurally visible as phase-tagged skips, so they cannot be lost. |
| **A-3** | The §3.1 examples-suite and two-harness-portability criteria are not exercisable in I.1. | Advisory — milestone scope. Examples suite → **Phase 8**; harness adapters → **Phase 6 (I.3)**. I.1's proof point is the proto-quickstart per D-02. |
| **A-4** | FABR-08 is partially delivered (Protocol + file-backed impl; MCP-backed impl deferred). | Advisory — this is the **D-12 amendment**, ruled by Dave, with a receiving deliverable already written into Phase 6 criterion 5. Recorded so the requirements ledger is not marked complete on a half-delivery without the reader seeing why. |
| **A-5** | `src/ccf/llm/__init__.py` shows 0% coverage. | Advisory and *expected*: the module exists solely as the single crisp import target CINV-03 lints against (D-IMPL-09). It declares a Protocol with no implementation in `/src` by design. Coverage is informational under D-17 in any case. |
| **A-6** | The Postgres leg skips silently on a machine without Docker. | Advisory, already mitigated: `CCF_REQUIRE_POSTGRES=1` converts the skip to a failure, and CI sets it via the postgres service container. Verified in §1 — the mandatory run passes 12/12. |
| **A-7** | *(from R-3, Cursor)* `shipped_operators()` in `tests/properties/strategies.py` is assembled by hand, so a newly shipped operator must be added there to enter the n² pair expansion. | Advisory. All 4 shipped operators are present and all 16 ordered pairs are green today. Carried to I.2/I.3 as an operator-onboarding checklist item; a registry-discovery variant would remove the obligation entirely and is worth considering when the operator set next grows. |
| **A-8** | *(Cursor)* CINV-01's factory-bypass leg (CINV-01c) is scaffold-only until I.2, since no `Agent`/`Task` factory exists yet; `allowlist.yaml` is correspondingly empty. | Advisory and expected — the factory surface lands in **I.2**. The lint's own docstring already states this. The prompt-literal and numeric-table legs of CINV-01 are fully active today. |
| **A-9** | *(Cursor)* `test_a_retired_writer_refuses_further_writes` proves re-boot succeeds after `close()`; it does not assert that a post-`close()` write fails (the implementation does set `_closed`). | Advisory — a test-strength gap, not an invariant hole; the single-writer invariant itself is covered by the boot-refusal tests. Carried to I.2 as a one-line assertion to add. |
| **A-10** | Cross-AI reviewer CLIs both needed a second attempt for environment reasons (Codex sandbox `bwrap`, Cursor workspace trust), and CLAUDE.md §3.1's note that Cursor's `--trust` flag "does not exist" is now out of date — `-f` works. | Advisory. Recorded in §6.1. Worth a small CLAUDE.md §3.1 correction at Dave's discretion so the next phase gate does not re-derive the workaround. |

---

## 8. What Dave Is Asked To Decide

1. Read this document — §2 (per-invariant checklist), §3 (requirement coverage), §4 (the two
   amendments), §5 (fidelity spot check), §7 (triage).
2. Optionally re-run: `.venv/bin/pytest tests -q && .venv/bin/python -m tools.lints --all`
3. Note the two recorded amendments: **D-03/D-IMPL-52** (banking example 00, horizontal domain
   mix, CLAUDE.md §9 amended) and **D-12** (MCP-backed ArtifactStore deferred to I.3, with
   Phase 6 criterion 5 as the receiving deliverable).
4. Note two small items surfaced by the review that are **yours to rule on, not the
   executor's** (neither blocks the gate):
   - **D-12 placement** — the ArtifactStore scope amendment lives on the roadmap and
     requirements, not in `docs/DECISIONS.md`. Mirror it into the decision log as a
     `D-IMPL-NN`, or leave it as roadmap-carried scope?
   - **CLAUDE.md §3.1 credential note** — the standing note says Cursor's `--trust` flag does
     not exist; the installed version accepts `-f` / `--trust` / `--yolo`, and Codex needs
     stdin-inlined input because its bubblewrap sandbox cannot start here. Worth correcting
     for the next gate (advisory A-10).
5. **Approve or reject the Phase I.1 gate.**

On approval — and only on approval — the executor appends the `D-GATE-I.1` entry to
`docs/DECISIONS.md` (mirroring the `D-GATE-F` format), merges `phase-i1` into `main` with a
merge commit referencing `D-GATE-I.1` (no force-push, CLAUDE.md §2.2), and updates
`.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md`.
