# ROADMAP — CCF SDK v0 (Phase F Deliverable)

**Canonical authority:** `CLAUDE.md` (revision 4). This document is the Phase F
deliverable roadmap (FEAS-02): the milestone breakdown for Phase I, the explicit
v0.1 minimum viable SDK surface, and the named deferral register.

**Two-roadmap relationship (stated explicitly).** `.planning/ROADMAP.md` is the
**sequencing source of truth** — its phases 4–8 define the Phase I sub-phase
order, dependencies, requirement IDs, and success criteria. This file,
`docs/ROADMAP.md`, is the **deliverable view**, aligned **1:1** with those
phases: milestone I.n below corresponds exactly to `.planning/ROADMAP.md` phase
`n+3`, and each milestone closes only at its `D-GATE-I.n` entry in
`docs/DECISIONS.md` per the CLAUDE.md §3.1 protocol. Where the two documents
could ever disagree on sequencing, `.planning/ROADMAP.md` wins; where either
disagrees with CLAUDE.md, CLAUDE.md wins.

Risk highlights per milestone are drawn from the per-component Risk notes in
`docs/FEASIBILITY.md` (FEAS-01, D-03 discipline: risk ratings feed this
breakdown; no per-component effort estimates exist by design). Decision status
is quoted per the locked wording: D-IMPL-10 (repo shape) is resolved for v0 as
monorepo — the post-v0 adapter-split remainder is non-gating and tracked
outside Phase D.

---

## 1. Milestone Breakdown (D-05: 1:1 with GSD phases I.1–I.5)

### Milestone I.1 — Fabric Core

- **Mirrors:** `.planning/ROADMAP.md` Phase 4. **Gate:** `D-GATE-I.1`.
- **Scope:** L1–L6 Data and Context Layer end-to-end in-process against
  reference backends (Postgres + SQLite per **D-IMPL-02**, sqlite-vec per
  **D-IMPL-03**), Context Product Contract with the three validation gates,
  `λ_c`/`D_c` computation from Control Plane configuration, five-dimension
  Decision Replay written at serve time, ArtifactStore Protocol (file-backed
  and MCP-backed reference impls), CDC→G ingress, and the CI invariant
  scaffolding (CINV-01..04) running from day one.
- **Requirements:** FABR-01..09, CINV-01..04.
- **Risk highlights (FEASIBILITY.md §§2–3, §8, §10):** predominantly low/med.
  Med-risk concentrations: entity resolution and temporal stitching in L2,
  operator algebra composition-preservation harness, replay snapshot mechanics
  (D-IMPL-06 logical snapshots), and the Control Plane registry — the artifact
  hub every other pillar depends on, so sequencing pressure lands here first.
  CINV-01 prompt-shape lint heuristics need false-positive tuning (calibration,
  not a design gap). No high-risk component lives in I.1.

### Milestone I.2 — Agent Specialization Framework

- **Mirrors:** `.planning/ROADMAP.md` Phase 5. **Gate:** `D-GATE-I.2`.
- **Scope:** Unified Agent base + six archetypes as SDK mechanism (§6.1
  archetype/agent separation), Agent & Task Factory constructing agents only
  from definition artifacts (**D-IMPL-28** schema), all six specialization
  axes, skill catalog with registration/discovery/grant/revoke, the
  policy-compatibility check, and replay capture of skill-sets in force.
- **Requirements:** AGNT-01..03.
- **Risk highlights (FEASIBILITY.md §4):** low/med throughout. Med-risk
  drivers: the factory + No-Hardcoding lint interplay (CINV-01 must reject
  factory bypass) and archetype composition per the D-IMPL-11/19 rulings.
- **v0.1 note:** the v0.1 surface (§2 below) is the subset of I.1–I.2 that
  runs `examples/00-quickstart` and `examples/01-agent-basics`.

### Milestone I.3 — Cross-Process & Harness Adapters

- **Mirrors:** `.planning/ROADMAP.md` Phase 6. **Gate:** `D-GATE-I.3`.
- **Scope:** Bidirectional MCP (client ingress at L1/L4/L5/Experience, server
  egress at L6, distinct ArtifactStore MCP role), A2A federation behind the
  `WireProtocol` abstraction (**D-IMPL-14**) with identity/signing
  (**D-IMPL-15**) and verify-every-admission (**D-IMPL-16**),
  `HarnessAdapterProtocol` + all three reference adapters per the
  **D-IMPL-24** ruling (Google ADK, Claude Agent SDK, LangGraph — all three
  ship v0), zero-harness-imports lint green.
- **Requirements:** XPRC-01..03.
- **Risk highlights (FEASIBILITY.md §9):** **the high-risk components of the
  whole design concentrate here** — MCP client library (high: MCP spec/SDK
  ecosystem is a moving target at 2026 state), A2A federation (high: the A2A
  standard is emergent; the typed-HTTP fallback is the containment), the
  Google ADK adapter (high: vendor SDK revising quarterly), and the LangGraph
  adapter (high: no single agent-loop surface; per-node-boundary binding).
  The Claude Agent SDK adapter is med (MCP-native posture). Per the D-10
  per-harness sizing analysis, FEASIBILITY.md carries a **recommendation for
  Dave at D-GATE-F — not a scope change; the D-IMPL-24 ruling stands unless
  Dave revises it:** within I.3, stage the LangGraph adapter after the ADK and
  Claude Agent SDK adapters have proven the conformance suite, so the hardest
  binding lands on a validated `HarnessAdapterProtocol` rather than
  co-evolving with it.

### Milestone I.4 — Orchestration, HITL, Experience

- **Mirrors:** `.planning/ROADMAP.md` Phase 7. **Gate:** `D-GATE-I.4`.
- **Scope:** Workflow primitive (agent/skill/HITL-gate nodes, suspend/resume
  at the Control Plane boundary per **D-IMPL-18**), all four HITL primitives
  with audit-by-construction into Decision Replay, `OrchestrationProtocol`
  for external engines (**D-IMPL-17**), and the three front doors: MCP server
  egress, the `ccf` CLI (**D-IMPL-22**), HTTP API skeleton + OpenAPI
  (**D-IMPL-23**).
- **Requirements:** ORCH-01..02, HITL-01, EXPR-01..03.
- **Risk highlights (FEASIBILITY.md §§5–7):** low/med. Med-risk drivers:
  workflow suspend/resume state persistence and the CI verification that no
  HITL path produces an unrecorded human action.

### Milestone I.5 — Examples Suite & Full CI Verification

- **Mirrors:** `.planning/ROADMAP.md` Phase 8. **Gate:** `D-GATE-I.5`
  (the Phase I gate, `D-GATE-I`).
- **Scope:** The eight-example v0 suite (`examples/00`–`07`) end-to-end in CI
  in one coherent neutral domain; example 03's two-harness portability
  assertion; examples 04+05 as the composed cross-process + HITL deployment;
  example 06 exact replay from ArtifactStore-resolved versions; all CI
  invariants green across `/src`, `/runtime`, `/examples`; whitepaper-fidelity
  spot check.
- **Requirements:** EXAM-01..09.
- **Risk highlights:** med — the risk here is integrative (every prior
  milestone's surface exercised together), not novel mechanism; per
  FEASIBILITY.md, no I.5-owned component rates high on its own.

---

## 2. v0.1 Minimum Viable SDK Surface (D-04 — example-driven)

The v0.1 surface is defined **by example, not by component list ambition**: it
is exactly the subset of milestones **I.1–I.2** required to run
`examples/00-quickstart` and `examples/01-agent-basics` end-to-end on the
reference backends. Concretely:

| v0.1 component | Milestone | Notes |
|---|---|---|
| Fabric core L1–L6 (in-process) | I.1 | Signal ingress → assembly → graph → operators → projection → Context Product, single-writer enforced at boot |
| Context Product Contract + three validation gates | I.1 | empty-operator guard → lineage strict equality → TTL bounds |
| Control Plane registry (in-process, versioned) | I.1 | Audit plane; all configuration values, zero hard-coded tables |
| Decision Replay record (write-time) | I.1 | Five dimensions; replay-ready by construction |
| SQLite graph store (dev reference, D-IMPL-02) | I.1 | Postgres reference impl completes within I.1 but is not required to run examples 00–01 |
| sqlite-vec SimilarityIndex (D-IMPL-03) | I.1 | Zero-infra quickstart pairing |
| File-backed ArtifactStore | I.1 | MCP-backed reference store completes within I.1/I.3; examples 00–01 need only the file-backed impl |
| Agent & Task Factory + definition-artifact schema (D-IMPL-28) | I.2 | No-Hardcoding Rule enforced; agents from artifacts only |
| One archetype: `AnalyticsInsightsAgent` | I.2 | The other five archetypes complete I.2 but are outside the v0.1 cut |
| CI invariant scaffolding (CINV-01..04) | I.1 | Runs from the first fabric commit |
| **Dev/mock IdentityProvider — assessed: NOT required for v0.1** | I.3 entry | See assessment below |

**Dev/mock IdentityProvider assessment (D-11 advisory item 7).** v0.1 does
**not** need an IdentityProvider, dev/mock or otherwise: examples 00–01 are
entirely in-process — no A2A boundary is crossed, no Context Product is signed
or admission-verified, and the D-IMPL-15 two-layer identity design (mTLS
transport + detached-JWS product signing) is exercised first at milestone I.3.
A dev/mock `IdentityProvider` implementation **is** warranted as the first
deliverable of I.3's A2A work, so `examples/04-cross-process` and the adapter
conformance suite can run without real PKI provisioning; it enters the surface
there, not in v0.1.

Everything in milestones I.3–I.5, plus the non-v0.1 remainder of I.1–I.2
(Postgres reference impl, the other five archetypes, MCP surfaces, A2A, HITL,
Experience front doors, examples 02–07), is v0 scope but outside the v0.1 cut.

---

## 3. Deferral Register (D-06)

Named register of everything deliberately deferred out of v0, with source,
reason, and earliest re-entry point. This register also closes the Phase D
"deferral migration notes" advisory.

| Item | Source (CLAUDE.md § / D-IMPL-NN) | Reason deferred | Earliest re-entry milestone |
|---|---|---|---|
| Homecams rebuild on the CCF SDK | CLAUDE.md §9 | Planned post-v0 validation exercise, explicitly not part of the initial release; the domain-neutral examples suite is the v0 adoption contract instead | Post-v0 (after `D-GATE-I`) |
| Adapter package split (separate packages/repos) | D-IMPL-10 residual | D-IMPL-10 (repo shape) is resolved for v0 as monorepo — the post-v0 adapter-split remainder is non-gating and tracked outside Phase D | Post-v0 (after `D-GATE-I`) |
| Agent-swarm intent decomposition | D-IMPL-49 | Free intent inference is out of v0 scope; intent is a declared enum-valued selection parameter in v0. Swarm-level decomposition is documented in DESIGN.md §4 as an orchestration-layer concern and a named post-v0 extension candidate | Post-v0 (builds on I.4 orchestration) |
| Supervision Quality (INV-CH8-19) | D-IMPL-48 | Ships as a documented reference pattern, not SDK mechanism: behavioral axes are domain values, fusion is calibration; every needed primitive exists in the v0 fabric. Candidate future example, not v0 suite | Post-v0 (candidate example over I.1–I.4 primitives) |
| Conversational Reporting Layer (INV-CH8-21) | Whitepaper §8.10 / CLAUDE.md §13 | Explicitly out of v0 scope; a future conversational surface is a user-built reference integration over the three front doors, whose underlying primitives (Π, D_c gating, replay) ship individually | Post-v0 (over I.4 Experience surfaces) |
| Chroma second `SimilarityIndex` reference impl | D-IMPL-03 | Ruled "if budget allows"; sqlite-vec is the committed dev-default reference impl and satisfies the Protocol-plus-reference-impl discipline on its own | I.1 (budget-permitting) or post-v0 |
| Remote Control Plane implementation | CLAUDE.md §13 | v0 ships the in-process versioned registry with an extension point for remote control planes; the remote implementation itself is user/post-v0 scope | Post-v0 (extension point lands in I.1) |

**Not deferred — explicitly:** no harness adapter is deferred out of v0. Per
Dave's **D-IMPL-24** ruling, all three reference adapters (Google ADK, Claude
Agent SDK, LangGraph) ship in milestone I.3. The LangGraph staging note in §1
is intra-I.3 sequencing advice for Dave at D-GATE-F, not a deferral.

---

## 4. Cross-References

- Verdicts and risk ratings: `docs/FEASIBILITY.md` (FEAS-01; Appendix A maps
  all 126 inventory entries to owning-component verdicts).
- Sequencing source of truth: `.planning/ROADMAP.md` phases 4–8.
- Decision log and gate entries: `docs/DECISIONS.md` (`D-GATE-I.n` entries
  land there as each milestone closes per CLAUDE.md §3.1).
- Test strategy (FEAS-03): the per-invariant spec table chapter in
  `docs/FEASIBILITY.md` §11.
