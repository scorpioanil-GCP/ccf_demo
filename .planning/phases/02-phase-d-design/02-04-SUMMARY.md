---
phase: 02-phase-d-design
plan: 04
subsystem: decision-log
tags: [decision-log, decision-marathon]
requires:
  - 02-02/02-03 batch-1/2 rulings (D-IMPL-28 addressing dependency, D-IMPL-24 LangGraph overlap routed to 17, D-IMPL-38 parameter discipline reused throughout batch 3)
provides:
  - 19 batch-3 rulings RESOLVED in docs/DECISIONS.md (D-IMPL-06,17,18,20,21,22,23,26,27,30,31,32,36,42,43,44,47,48,50)
  - Marathon closed — 49/49 census PASS; full 12-member Phase I gating list RESOLVED
  - fragments/marathon-batch-3.md — 19 recommendation-first briefs (Wave-5 design input)
  - fragments/provisional-register.md — consolidated register for D-GATE-D (zero provisionals, census evidence recorded)
affects: [all Wave-5 drafting plans (02-05..02-11), DESIGN.md obligations (D-IMPL-17 LangGraph seam doc, D-IMPL-30 drift annotation, D-IMPL-42 alias table, D-IMPL-48 reference-pattern sketch), Phase I gate — now clear]
tech-stack:
  added: []
  patterns: [hybrid content-hash + versioned-URI artifact addressing; logical snapshots + touched-substate manifests; mutability-based substrate split; typed queue HITL transport with notify-only webhooks; versioned pluggable scorer Protocols with replay-pinned versions]
key-files:
  created:
    - .planning/phases/02-phase-d-design/fragments/marathon-batch-3.md
    - .planning/phases/02-phase-d-design/fragments/provisional-register.md
  modified:
    - docs/DECISIONS.md
decisions:
  - "D-IMPL-26: hybrid addressing — content-hash canonical identity + versioned-URI naming via append-only Control Plane mapping; @latest never in replay/lineage"
  - "D-IMPL-06: logical snapshots (as-of reference + touched-substate manifest); full-fidelity tier materializes content-addressed artifacts; index versions pinned"
  - "D-IMPL-17: minimal in-SDK Workflow primitive + OrchestrationProtocol; LangGraph two-seam disambiguation documented in DESIGN.md"
  - "D-IMPL-20: HITLTransportProtocol typed queue core; MCP endpoints primary; webhooks notify-only; actions always return via typed queue"
  - "D-IMPL-27: substrate split by mutability — immutable/replay-relevant → ArtifactStore; hot mutable state → native Protocols"
  - "D-IMPL-36: deterministic intermediate cache keyed (tenant, operator_key, parameter_set_version, input_intermediate_keys, graph_snapshot_id); supersession-cascade invalidation, lazy re-derivation"
  - "D-IMPL-44: typed ReHydrationRecipe + ColdSourceArchiveProtocol; re-hydration re-runs L2 under pinned versions, verifies bit-for-bit or fails loudly"
  - "D-IMPL-50: SDK-shipped fidelity-lifecycle engine above the ArtifactStore Protocol; severity exemption in mechanism; windows/thresholds as values"
  - "D-IMPL-18: workflow state at Control Plane boundary; trace write-through to ArtifactStore at terminal and each suspend"
  - "D-IMPL-21: IdentityProvider Protocol family with distinct HumanPrincipalBinding incl. content hash of Context Product seen; OIDC/SAML path; JWS-signed reference impl"
  - "D-IMPL-22: noun-verb ccf CLI, thin client over HTTP API, --local dev mode"
  - "D-IMPL-23: minimal HTTP skeleton mirroring CLI nouns; OpenAPI from Pydantic contracts; deliberately no L1 ingestion endpoint"
  - "D-IMPL-43: closed-loop interpretation configurable per signal class, default human-gated (ApprovalGate); D-IMPL-29 two-tier pattern reused"
  - "D-IMPL-30: nine contract elements incl. Assembly Mode; 'eight' references (incl. CLAUDE.md §5) annotated as editorial drift in DESIGN.md — Dave's ruling authorizes the CLAUDE.md §5 annotation"
  - "D-IMPL-31: two TTL granularities — signal-level λ_c validity + per-class contract TTL with declared derivation rule and mixing-refusal floors"
  - "D-IMPL-32: TrustScorer Protocol, conjunctive combinator, per-leg per-class Control Plane thresholds; reference LegScorers from debt components"
  - "D-IMPL-42: prose taxonomy canonical — enum OUTCOME | CONTEXT_VALIDITY | AUDIT_LINEAGE; Fig-CH07-24 handler names as documented aliases"
  - "D-IMPL-47: REFINED RULING — DebtFactorScorer Protocol + reference F/C/S computations AS RECOMMENDED plus Dave's evolvability requirement: (scorer_id, scorer_version) identity with Control-Plane-updatable class bindings; per-class custom scorer override via the same Protocol seam; replay pins the scorer version in force"
  - "D-IMPL-48: Supervision Quality out of v0 SDK scope; documented reference pattern + build sketch in DESIGN.md; no SDK type"
metrics:
  duration: ~1 session (briefs + interactive ruling session + logging + census)
  completed: 2026-07-25
---

# Phase 2 Plan 04: Decision Marathon Batch 3 + Close-Out Summary

**One-liner:** Final 19 marathon rulings landed (artifact addressing/snapshots/replay lifecycle, orchestration/HITL/experience, whitepaper-ambiguity cluster) — 18 as recommended plus a refined D-IMPL-47 evolvability ruling — closing the marathon at 49/49 RESOLVED with zero provisionals and clearing the full Phase I gate list.

## What was done

- **Task 1 (commit 795b09c):** 19 recommendation-first briefs in `fragments/marathon-batch-3.md`, gating decisions (26, 06, 17, 20) first; ambiguity-cluster briefs quote the ambiguous whitepaper passages per CLAUDE.md §15.
- **Task 2 (checkpoint, commit 13a6b7e):** Interactive ruling session with Dave completed — all 19 decisions ruled, zero deferrals/provisionals. 18 AS RECOMMENDED; **D-IMPL-47 ruled as a refined recommendation** carrying Dave's explicit evolvability requirement (versioned scorers, Control-Plane-updatable bindings, per-class override, replay pins scorer version). All rulings logged in `docs/DECISIONS.md` dated 2026-07-25, Approver: Dave, with original ambiguous-passage text retained under "Originally:" per batch precedent.
- **Task 3 (commit 0490b7b):** 49/49 census PASS (every marathon ID RESOLVED); 12/12 gating IDs (01..05, 11, 14, 17, 20, 24, 26, 28) individually confirmed RESOLVED; `fragments/provisional-register.md` created recording **zero provisionals** with census evidence (`grep -c 'PROVISIONAL'` → 0). D-IMPL-10's CLAUDE.md §2.2 provisional (monorepo) noted as outside the marathon protocol.

## Deviations from Plan

None - plan executed exactly as written (Task 2 executed as a checkpoint continuation with rulings supplied by the orchestrator from Dave's session).

## Outcome

The decision marathon is over. D-03's precondition is cleared: Wave 5 drafting (02-05..02-11) may begin against a fully status-tokened decision log. DESIGN.md obligations accumulated for drafting: LangGraph two-seam boundary (17), nine-element drift annotation incl. CLAUDE.md §5 (30), learning-signal alias table (42), Supervision Quality build sketch (48), swarm intent decomposition note (49, from batch 2).

## Self-Check: PASSED

- fragments/marathon-batch-3.md — FOUND
- fragments/provisional-register.md — FOUND
- docs/DECISIONS.md 19 batch-3 IDs RESOLVED — verified (loop PASS)
- Commits 795b09c, 13a6b7e, 0490b7b — FOUND in git log
