# CCF SDK

## What This Is

A general-purpose software development kit implementing the Cognitive Context
Fabric (CCF) — a library, runtime, and reference components any team can adopt
to construct, govern, and serve decision-ready context to AI agents, and to
build, orchestrate, and operate specialized agents on top of that fabric. The
SDK is organized around five Common Pillars (Data and Context Layer,
Orchestration Layer, Core Agent Types, Human in the Loop and Control,
Experience Layer).

**Canonical project definition:** `/home/parkave/ccf_code/CLAUDE.md` (revision 4).
That document is authoritative for phases, review protocol, invariants, scope,
and the decision log. This PROJECT.md is a GSD-facing summary; where they
disagree, CLAUDE.md wins.

**Canonical specification:** `docs/CCF_Whitepaper_1-2.md` — single source of
truth for every CCF primitive, contract, invariant, and naming convention.

## Core Value

Fidelity to the whitepaper: every load-bearing primitive in
`docs/CCF_Whitepaper_1-2.md` realized in code with the contracts, invariants,
and composition properties the whitepaper commits to. Drift is a defect, not a
design choice.

Success conditions in priority order (CLAUDE.md §1): (1) whitepaper fidelity,
(2) general-purposeness — mechanism, never domain values, (3) harness
neutrality — CI-enforced, zero harness imports in core, (4) adoptability
through specialization — hours or days, not weeks.

## Requirements

### Validated

(None yet — ship to validate)

### Active

Phase deliverables under the CLAUDE.md §3 phase discipline:

- [ ] Phase R — `docs/SPEC_INVENTORY.md`: complete component-keyed catalog of
      every whitepaper commitment, per §16 success criteria, including the
      `homecams-patterns` appendix with inherit/do-not-inherit markers
- [ ] Phase D — `docs/DESIGN.md`, `docs/DECISIONS.md`, `docs/diagrams/`
      (one diagram per pillar + harness-adapter seam + ArtifactStore seam);
      every D-IMPL resolved by Dave or flagged as gating
- [ ] Phase F — `docs/FEASIBILITY.md`, `docs/ROADMAP.md`: per-component
      verdicts, v0.1 minimum viable surface, test strategy for every
      CI-enforced invariant
- [ ] Phase I — working library in `/src`, runtime in `/runtime`, tests in
      `/tests`, the eight-example v0 suite in `/examples` (§9), all CI
      invariant lints green, two-harness portability demonstrated

The detailed v0 in-scope surface is CLAUDE.md §13; REQUIREMENTS.md extracts it.

### Out of Scope

Per CLAUDE.md §13 (reasoning recorded there):

- An agent loop or harness of any kind — CCF layers onto harnesses; adapters only
- Pre-built domain ontologies, projections, policy bundles, skill catalogs,
  workflows, HITL policies — user configuration, shipped only as example artifacts
- Distributed multi-writer coordination within a tenant — single-writer v0 posture
- Heavyweight workflow engines (Temporal etc.) — reachable via OrchestrationProtocol
- Production observability stacks, mobile SDK, chat adapter, web UI,
  human task-management inbox — users build on exposed Protocols/HTTP API
- Conversational Reporting Layer (whitepaper §8.10)
- Homecams rebuild on the SDK — post-v0 validation exercise, explicitly not v0
- Domain calibrations and regulatory policy bundles — never the SDK's problem

## Context

- **Whitepaper:** `docs/CCF_Whitepaper_1-2.md` in-repo; every public class
  docstring cites its whitepaper section; SDK extensions cite CLAUDE.md and are
  labeled explicitly.
- **Reference implementation:** `/home/parkave/homecams_v2` — pattern
  triangulation only; never port code; whitepaper wins conflicts; its MongoDB
  persistence is a triangulation data point for the ArtifactStore design.
  `/home/parkave/homecams_v2/CLAUDE.md` is additive best-practices context only.
- **Decision authority:** Dave, via the `D-IMPL-NN` log in `docs/DECISIONS.md`.
  When the whitepaper is silent or ambiguous, log and stop — never pick a
  default and hope.
- **Repo:** `github.com/drcastillo/ccf_code`, private, monorepo (provisional
  D-IMPL-10). `main` is the approved-state branch; phase work on phase branches
  (`phase-r`, …); merges to `main` only at `D-GATE-<Phase>` entries; no
  force-push to `main`.
- **GSD ↔ CLAUDE.md mapping:** GSD phases map 1:1 to CLAUDE.md phases —
  Phase 1 = R, Phase 2 = D, Phase 3 = F, Phase 4+ = I sliced into
  implementation sub-phases. GSD's researcher/plan-checker/verifier agents are
  pre-flight rigor; the real gates remain `/gsd-review --phase <Phase> --all`
  self-review, blocking/advisory triage, and Dave's approval logged as
  `D-GATE-<Phase>` (CLAUDE.md §3.1).

## Constraints

- **Process**: Phase discipline (R → D → F → I) is sequential; no phase starts
  before the prior phase's deliverable is Dave-approved — CLAUDE.md §3.
- **Process**: No production code in Phase R; no redesign in Phase I (revisits
  are Phase D mini-cycles with their own review + D-GATE) — CLAUDE.md §3.
- **Models**: Phases R/D/F run on Fable 5 at high effort; Phase I on Opus 5
  (fallback Opus 4.8) at high effort — CLAUDE.md §3.
- **Structural invariants (CI-enforced)**: single-writer (only L2 writes L3),
  composition-preservation `(A∘B)(G)=A(B(G))`, three Context Product validation
  gates, Algorithmic ⇄ Semantic Alternation, audit-by-construction for
  HITL/workflow/skilling, No-Hardcoding Rule (no inline prompts, agents,
  task graphs, thresholds in code), zero harness imports in `/src`.
- **Typing**: Typed contracts at every boundary (Pydantic `extra=forbid` or
  equivalent); Protocols over inheritance; reference impl per Protocol.
- **Gating**: Phase I cannot start until D-IMPL-01..05, 11, 14, 17, 20, 24,
  26, 28 are at least provisionally resolved — CLAUDE.md §12.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLAUDE.md is canonical; PROJECT.md is a summary wrapper | Avoid dual sources of truth; CLAUDE.md predates and governs GSD setup | — Pending |
| GSD phases map 1:1 to R/D/F/I (I sliced into sub-phases) | Preserves phase discipline while gaining GSD planning/verification rigor | — Pending |
| All GSD rigor agents on (research, plan check, verifier), Interactive mode | Dave's approval gates require stopping; rigor layered under them | — Pending |
| Skip GSD generic domain research step | Phase R against the whitepaper IS the research; web sweep adds noise | — Pending |
| Monorepo at `github.com/drcastillo/ccf_code` | Provisional D-IMPL-10 per CLAUDE.md §2.2 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions (and `docs/DECISIONS.md` where they are D-IMPL/D-GATE class)
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-26 — Phase 5 (I.2 Agent Specialization Framework) complete: AGNT-01/02/03 verified 4/4; gap-closure plans 05-08..05-10 closed CR-01 and all WR/IN findings; 577 tests, lints and mypy --strict clean. D-GATE-I.2 package awaits Dave's approval.*
