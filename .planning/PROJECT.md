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

## Current State

**Shipped: v0.1.0 (2026-07-31, D-GATE-I).** Whitepaper-faithful v0 SDK on `main`:
fabric L1–L6, six archetypes + Agent & Task Factory + governed skilling,
bidirectional MCP + A2A/Peering + three harness adapters (Claude Agent SDK,
Google ADK, LangGraph), Workflow/HITL primitives with signed-binding auth,
MCP/CLI/HTTP front doors, eight-example suite in CI (1339 tests, mypy strict,
all invariant lints green). Milestone audit: tech_debt, no blockers
(.planning/v0.1-MILESTONE-AUDIT.md).

**Phase 9 complete (2026-08-01):** Hardening — WR-02 thread-safe
`InMemoryHitlTransport` (plain `threading.Lock`, D-16 verification outside the
lock), WR-03 loop-safe driver dispatch (`run_coroutine_sync` + typed
driver-error hierarchy across all three adapters), and the six-item ruling
batch D-IMPL-68..73 resolved by Dave with zero deferrals (1353 tests green).

## Current Milestone: v0.2 Performance, Documentation & Demonstration

**Goal:** Make the v0.1 SDK production-credible and adoptable — measured
performance with regression gates, adopter-grade documentation with detailed
usage examples, a synthetic-data end-to-end demonstration of
data→context→agentic reasoning, and closure of the security/robustness debt
from the v0.1 audit.

**Target features:**
- Detailed examples + usage documentation: adopter's guide, Protocol
  reference, definition-artifact schema reference, how-to guides, generated
  API reference, OpenAPI polish, security/deployment notes
- Fake data store demonstration: a synthetic, deterministic data store
  (domain values in artifacts per No-Hardcoding) ingested through L1→L2,
  folded into the Context Graph, projected into Context Products, and
  consumed by an agent solving a concrete reasoning problem end-to-end
- Performance & scalability test battery: micro-benchmarks, fabric load/scale
  curves, cross-process latency, replay-at-scale, committed baselines,
  `make perf`, opt-in CI job with relative regression thresholds
- Hardening intake: WR-01 HITL door authorization, WR-02 transport
  synchronization, WR-03 ADK driver robustness, ApprovalGate.resolve x D-16
  composition, create_app auth-default warning

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
*Last updated: 2026-08-01
