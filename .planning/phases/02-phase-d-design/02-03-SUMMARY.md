---
phase: 02-phase-d-design
plan: 03
subsystem: decision-log
tags: [decision-log, decision-marathon]
requires:
  - 02-02 batch-1 rulings (D-IMPL-01 language target conditions every batch-2 signature-level recommendation)
provides:
  - 14 batch-2 rulings RESOLVED in docs/DECISIONS.md (D-IMPL-11,12,13,14,15,16,19,24,25,28,29,45,46,49)
  - fragments/marathon-batch-2.md — 14 recommendation-first briefs (Wave-5 design input)
  - Four Phase I gate items resolved (D-IMPL-11, 14, 24, 28)
  - DESIGN.md obligation recorded in D-IMPL-49 (swarm-level intent decomposition documented as orchestration-layer concern, named post-v0 extension)
affects: [Core Agent Types design sections, harness-adapter surface, cross-process/trust design, 02-04..02-11, Phase I gate list, example-03 scope]
tech-stack:
  added: []
  patterns: [recommendation-first ruling sessions (D-02); single Agent class + Protocol-typed archetype bundles; verify-everything at trust boundaries; LF A2A as default wire]
key-files:
  created:
    - .planning/phases/02-phase-d-design/fragments/marathon-batch-2.md
  modified:
    - docs/DECISIONS.md
decisions:
  - "D-IMPL-28: YAML artifacts + Pydantic v2 (extra=forbid) schemas w/ exported JSON Schema; Jinja2 prompt artifacts by versioned URI; schema_version + artifact_version semver lanes"
  - "D-IMPL-11: single concrete Agent runtime class; archetypes as Protocol-typed composable bundles; no user subclassing"
  - "D-IMPL-24: DAVE'S OWN RULING — all three harnesses (Google ADK + Claude Agent SDK + LangGraph) ship v0 reference adapters; third CI leg + example-03 variant accepted into scope"
  - "D-IMPL-14: LF A2A protocol as default WireProtocol impl; typed-HTTP fallback second reference"
  - "D-IMPL-12: dynamic Control Plane skill catalog; four skill types; requirements declaration on entries; versioned grant/revocation artifacts"
  - "D-IMPL-19: ordered archetype composition with explicit conflict rules (dedupe / declaration-order-wins-with-warning / hard-contradiction errors)"
  - "D-IMPL-25: three seams mandatory; skill exposure mandatory iff non-empty skill-set; effects:unsupported is conformance-verified absence"
  - "D-IMPL-29: two-tier skilling governance — automatic check always on; ApprovalGate-gated grants as Control Plane configuration"
  - "D-IMPL-13: one ccf MCP client library (L1 + L4–L5), one ccf-runtime egress server (L6 + Experience), separate ArtifactStore MCP contract"
  - "D-IMPL-15: IdentityProvider Protocol; mTLS/X.509 transport + detached JWS product signing; static-keypair dev + cert-backed prod impls"
  - "D-IMPL-16: verify every inbound A2A product, no fast path; trust tiers configure admissibility only; post-v0 relief via verification caching"
  - "D-IMPL-45: TraceCorrelationHook on replay dimension 5 at adapter replay-hooks seam; ExternalTraceProviderProtocol w/ no-op reference"
  - "D-IMPL-46: PassageCitationProvider Protocol defined by typed L-anchor output; Anthropic Citations adapter + deterministic span-matcher references"
  - "D-IMPL-49: refined ruling — deterministic (perspective, context_product_class, selection_params) signature; intent as declared parameter; DESIGN.md must document swarm intent decomposition as orchestration-layer, named post-v0 extension"
metrics:
  duration: ~1 session (briefs + interactive ruling session + logging)
  completed: 2026-07-25
---

# Phase 2 Plan 03: Decision Marathon Batch 2 Summary

**One-liner:** All 14 agent-framework, harness, and cross-process/trust decisions ruled by Dave (13 as recommended, D-IMPL-24 Dave's own three-harness ruling, D-IMPL-49 refined) and logged RESOLVED — zero provisionals, zero deferrals; gating members 11, 14, 24, 28 all resolved.

## What was done

### Task 1 — Recommendation briefs (commit 3dc8aca)
- `fragments/marathon-batch-2.md`: 14 recommendation-first briefs, gating decisions first (28, 11, 24, 14), all signature-level recommendations conditioned on the batch-1 D-IMPL-01 ruling; 12↔29 and 46↔09 interactions noted inline; Homecams observations phrased only as data points.

### Task 2 — Interactive ruling session + logging (commit 07d4570)
- Session held with Dave via the orchestrator checkpoint (Approver: Dave, 2026-07-25). Zero provisionals/deferrals.
- 13 decisions ruled AS RECOMMENDED per marathon-batch-2.md.
- **D-IMPL-24 is Dave's own ruling, differing from the recommendation:** all three harnesses — Google ADK + Claude Agent SDK (must-haves) + LangGraph — ship reference adapters in v0. Rationale: LangGraph installations (including Homecams) could benefit from CCF. Accepted consequences recorded in the entry: third adapter + CI leg + example-03 variant in v0 scope; LangGraph-vs-Workflow-primitive overlap handled in design (adapter binds agent-loop seams; orchestration overlap is D-IMPL-17 territory). D-IMPL-11 ruled after an extended discussion including a worked CreditMonitoringAgent/OverdraftMonitoringAgent scenario; D-IMPL-16 ruled after a performance/safety discussion (admission off the hot path).
- **D-IMPL-49 ruled as a refined recommendation** (after an agent-swarm context-assembly discussion): deterministic signature retained, plus a recorded DESIGN.md obligation — swarm-level intent decomposition documented as an orchestration-layer concern and a NAMED post-v0 extension candidate (intent compiles to concrete product requests carrying the signature; coordination stays above Π; replay stays deterministic). The obligation is in the ruling text so drafting plans pick it up.
- Format per batch-1 precedent: 11..29 as status-note bullets; 45/46/49 as appended RESOLVED tokens with original entry text retained ("Originally: Open — awaiting Dave"). The open-entries umbrella bullet updated to (17, 18, 20, 21, 22, 23, 26, 27).
- Phase I gate impact: 11, 14, 24, 28 now resolved; remaining gate items 17, 20, 26.

## Verification

- Plan's automated check passed: all 14 IDs carry `RESOLVED` in docs/DECISIONS.md, dated 2026-07-25, "Approver: Dave".
- Original D-IMPL-45/46/49 entry text retained.
- Rulings commit 07d4570 touches only docs/DECISIONS.md.

## Deviations from Plan

None - plan executed exactly as written (rulings transcribed from Dave's answers via the orchestrator checkpoint; D-IMPL-24 and D-IMPL-49 recorded as Dave's ruling/refinement, not as recommendation adoption).

## Known Stubs

None.

## Threat Flags

None — T-02-07 (every RESOLVED names Approver: Dave), T-02-08 (no provisionals to mark), T-02-09 (docs only, private repo) all satisfied.

## Self-Check: PASSED

- `.planning/phases/02-phase-d-design/fragments/marathon-batch-2.md` — FOUND
- 14/14 RESOLVED tokens in docs/DECISIONS.md — FOUND
- Commits 3dc8aca, 07d4570 on phase-d — FOUND
