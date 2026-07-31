# Phase I.5 — Examples Suite & Full CI Verification: Gate Package (the Phase I gate)

**Phase:** 8 (Phase I.5) · **Branch:** `phase-i5` · **Assembled:** 2026-07-31
**Protocol:** CLAUDE.md §3.1 (self-review → triage → present to Dave → `D-GATE-I` → merge → tag)
**This is the Phase I gate — the v0 declaration.** Per D-17 (08-CONTEXT): approval →
`D-GATE-I` entry → merge `phase-i5` to `main --no-ff` → tag `v0.1.0` on the merge commit
on `main` — in that order, never before approval (08-RESEARCH Pitfall 6). No PyPI publish;
the repository stays private.

> **Status: AWAITING DAVE'S GATE APPROVAL.** `/gsd-review` passing is necessary, never
> sufficient — approval authority is Dave's alone (CLAUDE.md §3.1, §2). `D-GATE-I` is
> deliberately unwritten; the merge and the `v0.1.0` tag do not exist until it is.

---

## 1. Verification Evidence — Execution Record

Executed 2026-07-31 on the `phase-i5` branch head, repository root
`/home/parkave/ccf_code`, interpreter `.venv/bin/python` (Python 3.12),
`PYTHONPATH=src:runtime`. The command is `make ci` — finalized in 08-12 as
`ci-core + examples`, command-identical to the always-on GitHub Actions pipeline
(`.github/workflows/ci.yml`, D-10).

| Leg | Command | Result |
|-----|---------|--------|
| Invariant lints | `python -m tools.lints --all` | exit 0, zero findings |
| Strict typing | `python -m mypy` (`--strict` via config, `src` + `runtime`) | Success: no issues in 156 source files |
| Full suite, harnesses mandatory | `CCF_REQUIRE_HARNESSES=1 python -m pytest -q` | **1339 passed, 0 skipped, 0 failed** (phase baseline was 1315/0/0 on `main`) |
| Examples suite | `make examples` | all eight exit 0 (00–07, incl. example 03's deterministic three-harness leg) |

Version: `pyproject.toml` reads `version = "0.1.0"` (bumped from `0.1.0.dev0` in this
plan; `make ci` re-run green after the bump — the run recorded above).

**Actions evidence caveat (unchanged from 08-12):** `phase-i5` and `main` are ahead of
`origin`; Dave has not authorized a push, so the new `examples` job and `live-legs.yml`
have not yet run *in Actions*. The local sweep above is command-identical to the
pipeline (D-10) and stands in as the EXAM-09 evidence until push authorization —
see §6 item (b).

---

## 2. Per-Invariant Checklist — the CLAUDE.md §3.1 Phase I list

Every row names the enforcing mechanism and what would fail if the implementation were
broken (the D-17/D-25 gate-row discipline carried from I.1–I.4).

| # | §3.1 Phase I item | Enforcing mechanism | What would fail if broken |
|---|-------------------|---------------------|---------------------------|
| 1 | **No-Hardcoding lint (CINV-01a/b/c)** green over `/src`, `/runtime`, **and `/examples`** | `tools/lints/no_hardcoding.py` via `tools.lints --all` (exit 0); the 08-01 `RULE_TREE_SCOPE` posture puts CINV-01 in force over `/examples` (with its three-test posture suite in `tests/lints/`); prompt-shaped literals, numeric policy tables, and factory-bypass construction all refuse | An inline prompt or agent definition in any example's `run.py`; a threshold constant in `/src`; an agent constructed outside `AgentFactory` — each is a lint finding and `make ci` is red |
| 2 | **Harness-import lint (CINV-02)** — zero harness imports in `/src` | `tools/lints/harness_imports.py` via `tools.lints --all`; harness SDKs importable only under `runtime/ccf_runtime/adapters/` and the D-IMPL-60 orchestration driver tree (`tools/lints/orchestration_imports.py` enforces the split bidirectionally) | A `google.adk`/`claude_agent_sdk`/`langgraph` import in `/src` — a defect of the same class as an LLM client in an algorithmic module (CLAUDE.md §7.3) |
| 3 | **`@algorithmic` lint (CINV-03)** — no LLM client in algorithmic modules | `tools/lints/algorithmic.py` via `tools.lints --all`; modules declaring `__ccf_mode__ = "algorithmic"` refuse LLM-client imports | A hidden model call in the algorithmic path — the Algorithmic ⇄ Semantic Alternation (whitepaper §7.6.6) broken structurally, not stylistically |
| 4 | **Composition-preservation for every shipped operator pair** | `tests/properties/test_composition.py` — `itertools.product` over the operator registry (n², self-pairs included, grows automatically when an operator ships); `(A∘B)(G) = A(B(G))` asserted on `canonical_bytes`, bit for bit; composite from production `ccf.operators.planner.compose()` run through the intermediate cache; Hypothesis-generated states plus curated edge graphs (empty result, fully policy-filtered, temporal boundary) | Any pair whose composite diverges from its sequence — two content addresses for one plan, a replay that disagrees with itself; a hand-listed pair set someone forgot to extend (impossible: the parametrization is the registry) |
| 5 | **Replay-by-construction checks** — HITL actions, workflow traces, skill-set capture | `tests/invariants/test_replay_by_construction.py` (active-only registry, zero deferral skips since 07-07); `hitl-action-capture` and `workflow-trace-capture` both active with recorded-red counterfactuals (PHASE_I4_GATE §2.2 verbatim); grant-set-in-force capture per I.2 (`tests/replay/` dimension-4 drives); end-to-end `build_replay_record` drives for all four HITL primitives (D-GATE-I.4.1 item c) | A human action, a workflow transition, or a skill grant that reached delivery without landing in the five-dimension record — each owning test observed red under a severed pass-through |
| 6 | **Full §9 examples suite passing end-to-end** | `make examples` — eight asserted programs, exit 0 = every invariant held; run in CI as an always-on job with `CCF_REQUIRE_HARNESSES=1` (a skipped harness leg is a failure) and `timeout-minutes: 20`, never `continue-on-error` (D-10); D-09 README/artifacts contract check 8/8 PASS (non-empty `artifacts/`, documented command, whitepaper + CLAUDE.md citations, domain-rationale line) | A broken example is a broken build — CLAUDE.md §9's own words; an example whose code still ran meaningfully with its artifacts deleted would violate the No-Hardcoding Rule (and row 1 catches the inline forms) |
| 7 | **Example 03's portability assertion** (the two-harness §3.1 floor, shipped at three) | `examples/03-harness-portability` deterministic leg: **one** agent definition (`artifacts/agents/order_insights.yaml`, loaded once) executed under real `ClaudeSDKClient`, ADK `Runner`, and LangGraph loop machinery — product bytes identical ×3, 7 governed replay fields equal ×3, 3 distinct harness traces; `legs/deterministic.py` imports all three harness SDKs unconditionally (a missing harness is a failure, not a skip). Live legs (Ollama keyless default; Anthropic key-gated) assert D-04 structural equivalence | A harness whose consumption or replay record diverged from the other two; portability asserted rather than demonstrated (CLAUDE.md §7.3) |

**Single-writer enforcement** (the remaining named architectural invariant, verified since
I.1 and unchanged): `tests/invariants/test_single_writer_boot.py`,
`test_adapter_single_writer.py`, `test_peering_single_writer.py` — one writer per graph
keyed on graph identity, held across the harness-adapter, A2A-admission, and
ArtifactStore boundaries. **Three L6 validation gates**: empty-operator guard, lineage
strict equality, TTL bounds — exercised by the L6 test tree and demonstrated live in
example 00.

---

## 3. Whitepaper-Fidelity Spot Check (§3.1 Phase I requirement)

Sample of six public classes/surfaces; for each, the docstring's cited whitepaper section
was read against the implemented contract. **Recorded sample and findings:**

| # | Public surface | Cited section | Does the section specify the implemented contract? |
|---|----------------|---------------|-----------------------------------------------------|
| 1 | `ccf.contracts.base.CCFContract` (typed base, `extra=forbid`, boundary validation) | Whitepaper §6.3 | **Yes.** §6.3 "Context Product Specification" specifies the contract as the nine-element guarantee surface (Schema, Freshness SLA, TTL, Policy Binding, Lineage, Semver, Discovery, Addressability, Assembly Mode); the typed-base/`extra=forbid` discipline realizes "supports variability while preserving semantic consistency" at the boundary. Note: CLAUDE.md §5 says "eight-element" — recorded drift, annotated per D-IMPL-30's ruling (nine elements canonical) |
| 2 | `ccf.graph.protocols` (GraphView/as-of reads, typed relationships, supersession) | Whitepaper §7.3 | **Yes.** §7.3 "Context Graph — System of State" specifies the graph as first-class persisted state across the six axes; INV-CH7-14 (as-of re-render) and INV-CH7-20 (typed first-class relationships) are cited per-class and present in the section |
| 3 | `ccf.operators.base` / `ccf.operators.categories` (four categories, pure read-only operators, planner dependency order) | Whitepaper §7.4 | **Yes.** §7.4 names exactly the four canonical categories (Traversal, Temporal, Policy, Similarity), the Policy-before-Similarity ordering (Fig-CH07-07), the algebraic composition, and composition-preservation as the foundation of deterministic replay — each cited invariant (INV-CH7-22/24/25/27/28) traceable in the section |
| 4 | `ccf.projection.engine.ProjectionEngine` (two-stage execution, read-only handle, optional MCP acquisition) | Whitepaper §7.4–§7.5, §6.6 | **Yes.** §7.5 specifies Π as the system of interpretation over the operator-composed subgraph; the engine's operator-plan → projection-plan split matches §7.4's "plans handed to the projection engine for execution"; the acquisition seam cites §6.6's search-inference recursion |
| 5 | `ccf.replay.record` (five-dimension Decision Replay record) | Whitepaper §7.10.1 | **Yes.** §7.10 specifies replay as environment replay across exactly the five dimensions (INV-CH7-80 "inviolate"); the SDK's extensions (HITL block on dim 2, workflow step sequence on dim 5, agent version/skill-set on dim 4) are docstring-marked as CLAUDE.md §8.1/§8.2/§6.2 extensions, not whitepaper claims — the extension-labeling discipline of CLAUDE.md §11 |
| 6 | `ccf.halflife.decay` (λ_c per observation type, Freshness Budget = λ_c × Risk Sensitivity) | Whitepaper §7.7 | **Yes.** §7.7 specifies λ_c as Control Plane configuration per observation type and the Freshness Budget product form; the module quotes the section's own sentence and keeps both values in Control Plane artifacts (no table in code — row 1) |

No fidelity defect found in the sample: every cited section specifies the implemented
contract, and every SDK-defined extension encountered was explicitly labeled as such.

---

## 4. Phase 8 Named Obligations — Status

| Obligation | Source | Status |
|------------|--------|--------|
| **D-14** hardening wave (R1 was-called assertions; fail-closed `isinstance(grant, TokenGrant)`; typed refusal `error_code` constants; ADK `SequentialAgent` migration; D-IMPL-62 verb status note; key-management note; examples-bind-auth absorbed into 05/06) | 08-CONTEXT D-14; D-GATE-I.4.1 carried list | **Discharged** — 08-02 (verb removal + fail-closed branch + `http_api/errors.py`), 08-03 (D-16 + R1), 08-04 (ADK migration onto `google.adk.workflow.Workflow` at the 2.5.0 pin + both doc notes), 08-08 (examples 05/06 bind `auth=BearerTokenAuth(...)` and demonstrate the hardened surface end-to-end) |
| **D-15** `ccf hitl decide` removed; one verb (`submit`) | 08-CONTEXT D-15 | **Discharged** — 08-02, tree-wide removal with an absence test; DECISIONS.md entry dated 2026-07-30 |
| **D-16** signed-binding requiredness composed at the authority path | 08-CONTEXT D-16 (accelerating N5/R2) | **Discharged** — 08-03: `signed_binding_required` is a schema-validated Control Plane value (`ccf.hitl-policy` artifact) enforced at the HITL transport with two typed refusals mapped to shared `ERROR_SIGNED_BINDING_*` constants at both HTTP and MCP doors; demonstrated live in examples 05 and 06 |
| **D-17** v0 packaging: tag + version bump + top-level README + `D-GATE-I` | 08-CONTEXT D-17 | **Staged** — README.md authored (install, quickstart, eight-example table, no PyPI); pyproject `0.1.0`; tag and `D-GATE-I` await approval (§6) |
| **A3** — Claude adapter's hand-built `ResultMessage` seam-4 leg | I.3 gate → I.4 gate §5 | **Discharged** — 08-10: zero adapter change; the discharge test and example 03's Claude leg drive a genuinely SDK-parsed `ResultMessage` through seam 4, the session running over the adapter's own seam-1 carrier |
| **R1** was-called derivation assertions | 07-REVIEWS rounds 2–3 | **Discharged** — 08-03 |
| **R2/N5** non-repudiation residual (signed-binding composition) | 07-REVIEWS rounds 2–3 | **Discharged** via D-16 (row above); the D-IMPL-63 identity-binding reference impls themselves shipped in 7.1 (D-GATE-I.4.1) |
| Loop-level harness portability (§7.3 proof) | I.3/I.4 gate handoffs | **Discharged** — 08-10 (deterministic, three harnesses) + 08-11 (live legs, D-04 structural equivalence) |
| EXAM-09 CI wiring | ROADMAP Phase 8 | **Discharged at the wiring level** — 08-12; Actions runs pend push authorization (§1 caveat) |

**Deferred (unchanged, post-v0):** Homecams-on-SDK rebuild; PyPI publishing; perf
baselines; replay-explorer / workflow-graph-export CLI ideas; mobile/chat/web UX.
**Standing residuals:** T-07-24 (unauthenticated *default* HTTP posture — the optional
`BearerTokenAuth` hook shipped in 7.1 and the examples bind it; the default posture
sentence stands as ruled); unaudited Control Plane state *reads* (07-02 observation);
google-adk deprecation watch moves to the next pin bump (migration done at 2.5.0).

---

## 5. Success-Criteria Evidence Map (ROADMAP Phase 8)

| Criterion | Evidence |
|-----------|----------|
| 1. Eight examples, code + artifacts side by side, horizontal domain mix (as amended by D-IMPL-52; ≥4 domains, D-06) | Domains shipped: banking (00, 05), field-service (01), clinical-trials ops (02), e-commerce (03), property-intelligence (04, per D-08 — zero Homecams code), energy/grid ops (06), logistics (07) — seven distinct domains; D-09 rationale line present 8/8 |
| 2. Single documented command per example; suite runs in CI | `make example-NN` per README; `make examples` in the always-on `examples` job (§2 row 6) |
| 3. Example 03 portability | §2 row 7 |
| 4. CI invariants verified across `/src`, `/runtime`, `/examples` | §2 rows 1–5; §1 sweep |
| 5. Phase I gate per §3.1 | This document; review appendix §7; Dave's ruling §6 |

Requirements EXAM-01..09 are ticked in `.planning/REQUIREMENTS.md` against plans
08-05..08-12; EXAM-09's Actions-observed leg carries the §1 caveat.

---

## 6. What Dave Is Asked To Decide

1. Read §1 (the sweep), §2 (the seven §3.1 rows), §3 (the fidelity sample), §4
   (obligations), §7 (review + triage). Optionally re-run `make ci`, or spot-run
   `make example-00`, `make example-03`, `make example-05`.
2. **(a) Approve or reject the Phase I gate.** On approval — and only then — the
   `D-GATE-I` entry is appended to `docs/DECISIONS.md`, `phase-i5` merges to `main
   --no-ff` referencing it, and `v0.1.0` is tagged on the merge commit on `main`.
3. **(b) Push authorization.** `phase-i5`/`main` are ahead of `origin`; until a push,
   the Actions pipeline (always-on `examples` job, `live-legs.yml`) cannot run for
   real. Authorizing the push converts §1's local-sweep evidence into observed Actions
   evidence. This is a separate yes/no from (a).

---

## 7. Review Appendix — §3.1 Cross-AI Review and Triage

*(Populated by the Phase I review task; see the disposition table below.)*
