# Entry Ownership Assignment — Phase D Drafting (DSGN-01)

**Invariant: every INV key appears in exactly one Owning-fragment cell; synthesis (plan 02-10) builds Appendix A from this table.**

Derived from `docs/SPEC_INVENTORY.md` — Pillar-by-Pillar Mapping (line ~1853) and Named Architectural Invariants (line ~1815). The pillar sort is not re-derived here; where an entry contributes to two pillars, the pillar mapping's primary listing decides the owner and the secondary pillar lands in See-also. Owning fragments are the five Wave-5 drafting fragments:

- `design-data-context-a.md` — L1–L3, ingestion, graph, single-writer scope
- `design-data-context-b.md` — L4–L6, half-life/debt, replay, closed loop, control/data planes
- `design-agent-types.md` — Core Agent Types pillar (archetypes, factory, skilling)
- `design-orch-hitl.md` — Orchestration Layer + Human in the Loop and Control pillars
- `design-experience-seams.md` — Experience pillar + MCP roles, A2A, harness-adapter seam, ArtifactStore seam

126 rows. One owner per key — never two.

| INV key | Owning fragment | See-also |
|---------|-----------------|----------|
| INV-CH5-01 | design-data-context-a.md | — |
| INV-CH5-02 | design-data-context-a.md | — |
| INV-CH5-03 | design-data-context-a.md | — |
| INV-CH5-04 | design-data-context-a.md | — |
| INV-CH5-05 | design-data-context-a.md | — |
| INV-CH5-06 | design-data-context-a.md | — |
| INV-CH5-07 | design-data-context-a.md | — |
| INV-CH5-08 | design-data-context-a.md | — |
| INV-CH5-09 | design-data-context-a.md | — |
| INV-CH5-10 | design-data-context-a.md | — |
| INV-CH6-01 | design-data-context-b.md | — |
| INV-CH6-02 | design-data-context-b.md | — |
| INV-CH6-03 | design-data-context-b.md | — |
| INV-CH6-04 | design-data-context-b.md | design-agent-types.md (alternation touches agent consumption) |
| INV-CH6-05 | design-agent-types.md | design-experience-seams.md (Discoverable/Interoperable principles) |
| INV-CH6-06 | design-experience-seams.md | design-agent-types.md (agents reach fabric via MCP access layer) |
| INV-CH6-07 | design-agent-types.md | design-data-context-b.md (search-inference content acquisition at L4–L5) |
| INV-CH6-08 | design-agent-types.md | design-orch-hitl.md (trust-gated action / escalation) |
| INV-CH7-01 | design-data-context-a.md | — |
| INV-CH7-02 | design-data-context-a.md | — |
| INV-CH7-03 | design-data-context-a.md | — |
| INV-CH7-04 | design-data-context-a.md | — |
| INV-CH7-05 | design-data-context-a.md | — |
| INV-CH7-06 | design-data-context-a.md | design-data-context-b.md (layer boundaries touch L4–L6) |
| INV-CH7-07 | design-data-context-a.md | — |
| INV-CH7-08 | design-data-context-a.md | — |
| INV-CH7-09 | design-data-context-a.md | — |
| INV-CH7-10 | design-data-context-a.md | — |
| INV-CH7-11 | design-data-context-a.md | design-data-context-b.md (operator purity / composition) |
| INV-CH7-12 | design-data-context-a.md | — |
| INV-CH7-13 | design-data-context-a.md | design-data-context-b.md (validation gates at L6) |
| INV-CH7-14 | design-data-context-a.md | — |
| INV-CH7-15 | design-data-context-a.md | — |
| INV-CH7-16 | design-data-context-a.md | — |
| INV-CH7-17 | design-data-context-a.md | — |
| INV-CH7-18 | design-data-context-a.md | — |
| INV-CH7-19 | design-data-context-a.md | — |
| INV-CH7-20 | design-data-context-a.md | — |
| INV-CH7-21 | design-data-context-a.md | — |
| INV-CH7-22 | design-data-context-b.md | — |
| INV-CH7-23 | design-data-context-b.md | — |
| INV-CH7-24 | design-data-context-b.md | — |
| INV-CH7-25 | design-data-context-b.md | — |
| INV-CH7-26 | design-data-context-b.md | — |
| INV-CH7-27 | design-data-context-b.md | — |
| INV-CH7-28 | design-data-context-b.md | — |
| INV-CH7-29 | design-data-context-b.md | — |
| INV-CH7-30 | design-data-context-b.md | — |
| INV-CH7-31 | design-data-context-b.md | — |
| INV-CH7-32 | design-agent-types.md | design-orch-hitl.md (swarm-realized operators); design-data-context-b.md (L4 operator mechanism) |
| INV-CH7-33 | design-data-context-b.md | — |
| INV-CH7-40 | design-data-context-b.md | — |
| INV-CH7-41 | design-data-context-b.md | — |
| INV-CH7-42 | design-data-context-b.md | — |
| INV-CH7-43 | design-data-context-b.md | — |
| INV-CH7-44 | design-data-context-b.md | — |
| INV-CH7-45 | design-data-context-b.md | — |
| INV-CH7-46 | design-data-context-b.md | — |
| INV-CH7-47 | design-data-context-b.md | — |
| INV-CH7-48 | design-data-context-b.md | — |
| INV-CH7-49 | design-data-context-b.md | — |
| INV-CH7-50 | design-data-context-b.md | — |
| INV-CH7-51 | design-data-context-b.md | — |
| INV-CH7-52 | design-data-context-b.md | — |
| INV-CH7-53 | design-data-context-b.md | — |
| INV-CH7-54 | design-data-context-b.md | — |
| INV-CH7-55 | design-orch-hitl.md | design-data-context-b.md (Mode 3 cross-org assembly at L6); design-experience-seams.md (A2A) |
| INV-CH7-56 | design-orch-hitl.md | design-data-context-b.md (Mode 3 replay footprint) |
| INV-CH7-57 | design-data-context-b.md | — |
| INV-CH7-58 | design-data-context-b.md | — |
| INV-CH7-59 | design-data-context-b.md | — |
| INV-CH7-60 | design-data-context-b.md | design-data-context-a.md (append-only supersession in graph) |
| INV-CH7-61 | design-data-context-b.md | — |
| INV-CH7-62 | design-data-context-b.md | — |
| INV-CH7-63 | design-data-context-b.md | — |
| INV-CH7-64 | design-data-context-b.md | — |
| INV-CH7-65 | design-orch-hitl.md | design-data-context-b.md (CAR routing driven by D_c) |
| INV-CH7-66 | design-data-context-b.md | — |
| INV-CH7-67 | design-orch-hitl.md | design-data-context-b.md (fail-closed as debt behavior) |
| INV-CH7-68 | design-orch-hitl.md | design-data-context-b.md (debt cascade across handoff) |
| INV-CH7-70 | design-data-context-b.md | — |
| INV-CH7-71 | design-data-context-b.md | design-orch-hitl.md (audit plane backs HITL audit-by-construction) |
| INV-CH7-72 | design-data-context-b.md | design-agent-types.md (agent/task/prompt/skill artifact classes) |
| INV-CH7-73 | design-data-context-b.md | design-data-context-a.md (single-writer enforcement) |
| INV-CH7-74 | design-data-context-b.md | — |
| INV-CH7-75 | design-data-context-b.md | design-orch-hitl.md (interpretation step may be human-gated, D-IMPL-43) |
| INV-CH7-76 | design-data-context-b.md | — |
| INV-CH7-77 | design-data-context-b.md | — |
| INV-CH7-78 | design-data-context-b.md | — |
| INV-CH7-79 | design-data-context-b.md | — |
| INV-CH7-80 | design-data-context-b.md | design-experience-seams.md (ArtifactStore retention) |
| INV-CH7-81 | design-data-context-b.md | — |
| INV-CH7-82 | design-orch-hitl.md | design-data-context-b.md (dimension 2 Policy Bindings Snapshot) |
| INV-CH7-83 | design-data-context-b.md | — |
| INV-CH7-84 | design-agent-types.md | design-data-context-b.md (dimension 4 Perspective Conditioning) |
| INV-CH7-85 | design-data-context-b.md | — |
| INV-CH7-86 | design-data-context-b.md | design-experience-seams.md (model-trace composition seam, D-IMPL-45) |
| INV-CH7-87 | design-data-context-b.md | — |
| INV-CH7-88 | design-orch-hitl.md | design-data-context-b.md (Mode 3 replay record) |
| INV-CH7-89 | design-data-context-b.md | design-experience-seams.md (ArtifactStore lifecycle, D-IMPL-50) |
| INV-CH7-90 | design-data-context-b.md | — |
| INV-CH7-91 | design-experience-seams.md | design-data-context-b.md (replay renderings) |
| INV-CH8-01 | design-data-context-a.md | — |
| INV-CH8-02 | design-data-context-a.md | — |
| INV-CH8-03 | design-data-context-a.md | — |
| INV-CH8-04 | design-data-context-a.md | — |
| INV-CH8-05 | design-data-context-a.md | — |
| INV-CH8-06 | design-data-context-a.md | — |
| INV-CH8-07 | design-experience-seams.md | design-data-context-b.md (L6 egress of Context Products) |
| INV-CH8-08 | design-experience-seams.md | design-orch-hitl.md (A2A as cross-org orchestration ingress) |
| INV-CH8-09 | design-data-context-a.md | — |
| INV-CH8-10 | design-data-context-a.md | — |
| INV-CH8-11 | design-data-context-a.md | — |
| INV-CH8-12 | design-agent-types.md | design-data-context-b.md (Algorithmic ⇄ Semantic Alternation; Control Plane thresholds) |
| INV-CH8-13 | design-data-context-a.md | design-agent-types.md (graph lens on agentic work) |
| INV-CH8-14 | design-data-context-b.md | design-agent-types.md (temporal layer for agentic work) |
| INV-CH8-15 | design-data-context-b.md | — |
| INV-CH8-16 | design-orch-hitl.md | design-data-context-b.md (forced-escalation pathway driven by D_c) |
| INV-CH8-17 | design-data-context-b.md | — |
| INV-CH8-18 | design-orch-hitl.md | — |
| INV-CH8-19 | design-orch-hitl.md | — |
| INV-CH8-20 | design-data-context-b.md | design-agent-types.md (auditability of agentic work at scale) |
| INV-CH8-21 | design-experience-seams.md | design-agent-types.md (out-of-v0-scope archetype adjacency) |
| INV-CH8-22 | design-agent-types.md | — |
| INV-CH8-23 | design-orch-hitl.md | — |
| INV-CH8-24 | design-experience-seams.md | design-data-context-a.md (coexistence / layering onto estates) |

## Census check

Per 02-RESEARCH.md entry census: CH5 ×10, CH6 ×8, CH7 ×84, CH8 ×24 = 126. Ownership totals: design-data-context-a.md 41, design-data-context-b.md 61, design-agent-types.md 7, design-orch-hitl.md 11, design-experience-seams.md 6 — total 126.
