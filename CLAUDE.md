# CCF SDK — Project Orientation for Claude Code

> This file is the entry point for Claude Code. Read it in full at the start of
> every session before touching code, design docs, or the whitepaper.

## 1. Mission

Build a **general-purpose implementation of the Cognitive Context Fabric (CCF)
as a software development kit**. The deliverable is a library, a runtime, and
supporting reference components that any team can adopt to construct, govern,
and serve decision-ready context to AI agents — and to build, orchestrate, and
operate specialized agents *on top of* that fabric.

The SDK is organized around **five Common Pillars** (§4) that match how users
actually build agentic systems. Each pillar is realized by SDK mechanism; each
is specialized by user configuration.

The work has four success conditions, in priority order:

1. **Fidelity to the whitepaper.** Every load-bearing primitive specified in
   `docs/CCF_Whitepaper_1-2.md` is realized in code with the contracts,
   invariants, and composition properties the whitepaper commits to. Drift
   from the whitepaper is a defect, not a design choice.
2. **General-purposeness.** The SDK encodes *mechanism*, not *domain values*.
   Banking-specific, property-intelligence-specific, or any other
   domain-specific configurations (half-life tables, ontologies, projection
   roles, policy bundles, skills, workflows, approval policies) live in
   user-supplied config, not in the library.
3. **Harness neutrality.** The SDK works with any agent harness — Google ADK,
   the Claude Agent SDK, LangGraph, a bespoke loop — because **CCF layers
   onto the harness as the trust-and-control plane; it never absorbs the
   agent loop and it does not ship one.** No module in the SDK core imports
   a harness. Harness bindings are adapters (§7.3), and the seams between
   fabric and harness are the typed Context Product Contract, MCP, and A2A —
   nothing harness-shaped. Harness neutrality is an invariant with CI
   enforcement, not an aspiration.
4. **Adoptability through specialization.** Users will always specialize the
   SDK for their specific use case. A competent engineering team should be
   able to read the docs, install the SDK, register a domain ontology plus a
   projection plus a policy bundle plus a specialized agent, orchestrate a
   multi-agent workflow with HITL checkpoints, and have agents consume (or
   produce) typed `ContextProduct`s over the wire — in hours or days, not
   weeks or months.

If any of these come into conflict, fidelity to the whitepaper wins.
Harness neutrality and general-purposeness are two faces of the same
commitment — the SDK never encodes anyone else's loop, values, or vendor.
Where the SDK extends *beyond* what the whitepaper commits to (the Agent
Specialization Framework, the Agent & Task Factory, the Orchestration Layer,
HITL primitives, the Harness Adapter surface, the ArtifactStore, the
Experience Layer adapters), the extension is explicit and labeled as
SDK-defined, not whitepaper-derived.

## 2. Canonical Inputs

| Source                                  | Role                                             |
| --------------------------------------- | ------------------------------------------------ |
| `/home/parkave/ccf_code/docs/CCF_Whitepaper_1-2.md` (repo copy: `./docs/CCF_Whitepaper_1-2.md`) | **Canonical specification.** Single source of truth for every primitive, contract, invariant, and naming convention defined by CCF itself. |
| `/home/parkave/homecams_v2`             | **Reference implementation for pattern triangulation.** A working CCF realization for home property situational intelligence. Read for patterns; do not port code. See §2.1 for the discipline. |
| `/home/parkave/homecams_v2/CLAUDE.md`   | **Best-practices reference only.** Read once, early, for conventions, workflow framing, session discipline, and orientation patterns that proved out in a real build. It is *additive context and framing only* — nothing in it overrides anything specified in this document. Where the two disagree, this document wins silently; no decision-log entry required. |
| Author conversations (Dave)             | **Decision authority** on every open question in the decision log (§12). |

### 2.1 How to use Homecams

`/home/parkave/homecams_v2` is a real, running CCF implementation. It is
useful for four things and four things only:

- **Pattern triangulation.** Where the whitepaper specifies a contract but
  not a specific resolution (e.g., how the operator DAG planner schedules
  intermediates), Homecams shows *one* working resolution. That resolution
  is one data point, never the canonical answer.
- **Existence proof.** Confirming that the whitepaper's primitives compose
  into a working system. Useful when reviewing the inventory in Phase R.
- **Cautionary contrast.** Where Homecams encodes domain-specific values
  (property-intelligence half-lives, camera/sensor signal types, person/pet
  ontology), it shows the boundary between SDK mechanism and user
  specialization. The SDK must keep these on opposite sides of that line.
- **MongoDB Collections.** Its code references mongodb collections where
  aspects of the CCF are persisted. It will require a readonly query to
  secure the appropriate meta-data from mongodb.

**Do not port code from Homecams into the SDK.** Homecams is a
domain-specialized realization; the SDK is general-purpose machinery. Any
code that looks copy-able is almost certainly mixing mechanism with domain
values. If a pattern in Homecams is genuinely worth reproducing, the SDK
re-implements it cleanly against the whitepaper contract, with the
domain-specific parts factored out as user configuration.

Persistence of CCF artifacts is a first-class SDK surface in revision 4:
the ArtifactStore Protocol with an MCP-backed reference implementation
(§7.4), so that users are free to use their own persistent store and
decision-playback data store. Homecams's MongoDB persistence is a
triangulation data point for that design, not a substrate to inherit.

When the whitepaper and Homecams disagree, **the whitepaper wins**. When the
whitepaper is silent and Homecams has a resolution, the resolution becomes
an *open question for the decision log* (§12), not a default to inherit.

**Important Note** Although Homecams validates the CCF claims and
capabilities, the implementation did not leverage a CCF SDK pattern or
framework. Although there is some code that has been labeled application
independent, CCF features and capabilities are implemented throughout the
Homecams application. A rebuild of Homecams *on* the CCF SDK is a planned
post-v0 validation exercise (§9); it is explicitly not part of the initial
release.

### 2.2 Repository

The project's home is `github.com/drcastillo/ccf_code` — a **private**
repository, and it stays private: the canonical whitepaper lives in
`docs/` and CCF is proprietary IP. Dave creates the repository; Claude
Code does everything after — remote wiring, `.gitignore` (build
artifacts, environments, credentials; never a secret in the tree), and
all commits.

Discipline:

- **`main` is the approved-state branch.** What is on `main` reflects
  the last Dave-approved phase gate. Phase work happens on a phase
  branch (`phase-r`, `phase-d`, and so on); the merge to `main` happens
  at the `D-GATE-<Phase>` entry (§3.1), and the merge commit references
  it. No force-push to `main`, ever.
- **Commit at deliverable boundaries, not keystroke boundaries.** A
  commit corresponds to a coherent unit — an inventory section, a
  resolved decision, a passing example — with a message that names the
  section of this document or the `D-IMPL-NN` it serves.
- **This establishes `ccf_code` as a single repository for v0** —
  library, runtime, adapters, examples, and docs together — which
  provisionally resolves D-IMPL-10 as *monorepo*. Whether adapters
  split out post-v0 remains open under that entry; log the provisional
  resolution.
- The whitepaper, this document, and all definition artifacts (§6.4)
  are versioned in the repo — the No-Hardcoding Rule only works if the
  artifacts have the same version-control gravity as the code.

## 3. Phase Discipline (Use `/gsd` plugin)

This project is built under the `/gsd` plugin's phase-disciplined workflow. The
phases are sequential. Do not collapse them, and do not start a phase before
the prior phase's deliverable is approved by Dave.

### Phase R — Research (`gsd-phase-researcher`)
**Deliverable:** `docs/SPEC_INVENTORY.md`
**Purpose:** Extract every commitment in the whitepaper into a structured,
component-keyed catalog. For each entry: the whitepaper section, the
commitment in author's own paraphrase, the formal type/signature where one is
given, the invariants that must hold, the figures it depends on, and any
open questions or under-specifications.
**Model:** Use the Anthropic Fable 5 model with "high" effort for Phase R.
**Review:** utilize "/gsd-review --phase Phase R --all" at the conclusion of Phase R, per the protocol in §3.1.

Phase R also reviews Homecams once — to inventory which patterns exist
there that might inform SDK design, and which domain-specific commitments
exist there that the SDK must *not* inherit. Output: a `homecams-patterns`
appendix to the inventory. Phase R also reads
`/home/parkave/homecams_v2/CLAUDE.md` once, per the §2 discipline.

**Out of scope for Phase R:** design choices, code, diagrams of the SDK's
own architecture (the whitepaper's diagrams are inventoried, not redrawn).

### Phase D — Design (`gsd-planner`)
**Deliverable:** `docs/DESIGN.md`, `docs/DECISIONS.md`, `public/diagrams/`
**Purpose:** Produce the SDK's architectural shape against the inventory.
Surface every design decision Dave has to rule on. Produce architecture
diagrams (component, sequence, layered, deployment) for the SDK itself,
distinct from the whitepaper's domain figures. The diagrams must include
**one per pillar** (§4) showing how that pillar is realized in SDK mechanism,
plus one diagram for the harness-adapter seam (§7.3) and one for the
ArtifactStore seam (§7.4).
**Model:** Use the Anthropic Fable 5 model with "high" effort for Phase D.
**Review:** utilize "/gsd-review --phase Phase D --all" at the conclusion of Phase D, per the protocol in §3.1.

**Out of scope for Phase D:** writing implementation code.

### Phase F — Feasibility & Scoping (`gsd-planner` continued)
**Deliverable:** `docs/FEASIBILITY.md`, `docs/ROADMAP.md`
**Purpose:** Per-component implementation verdict (strong fit / needs design
choice / out of scope for v0). Milestone breakdown. Test strategy. Define
v0.1 minimum viable SDK surface and what gets deferred.
**Model:** Use the Anthropic Fable 5 model with "high" effort for Phase F.
**Review:** utilize "/gsd-review --phase Phase F --all" at the conclusion of Phase F, per the protocol in §3.1.

### Phase I — Implementation
**Deliverable:** working library and runtime in `/src` and `/runtime`,
tests in `/tests`, the v0 examples suite in `/examples` per §9.
**Purpose:** Build the SDK module by module against the inventory, the design,
and the decision log.
**Model:** Use the Anthropic "Opus 5" if available otherwise use "Opus 4.8" with "high" effort for Phase I.
**Review:** utilize "/gsd-review --phase Phase I --all" at the conclusion of Phase I, per the protocol in §3.1.

### Phase boundaries are real
Do not write production code during Phase R. Do not redesign during Phase I.
If a decision needs to be revisited, that is a new Phase D mini-cycle with
its own decision log entry, not in-line scope creep.

### 3.1 Phase Review and Approval Protocol

Every phase ends the same way, in the same order. The sequence is not
optional and its steps do not merge:

1. **Self-review.** Run `/gsd-review --phase <Phase> --all` against the
   phase's deliverables. The review runs *before* anything is presented
   to Dave — a review report is a precondition of requesting approval,
   not a substitute for it.

   **This step is the cross-AI panel, and nothing else satisfies it.**
   `/gsd-review --all` invokes every available external reviewer; a
   single-agent code review (`/gsd:code-review`, the `gsd-code-reviewer`
   agent, or any in-session review by the executing model) is **additive,
   never a substitute**. Running the single-agent review and presenting on
   its findings does not discharge this step. Both run: the panel because
   independent models catch different blind spots, the single-agent pass
   because it reads at a depth a panel prompt cannot carry.

   **What the panel IS, definitionally (D-GATE-21, Dave, 2026-08-22).**
   The panel is *the set of available external AI reviewers, with the
   executing model excluded for independence*. It is not a particular
   command invocation. `/gsd-review --all` is the mechanism that gathers
   them, and the reviewer set, credentials and model selection come from
   that workflow — but the panel is discharged by the reviewers having
   read the right subject, not by the command having been typed.

   **When execution has already happened, the panel reviews the *shipped
   code*, not the plans.** A phase whose plans were reviewed before
   execution does not get a second plan review at close — those decisions
   are already executed. Write the close-time panel to a distinct file
   (`<phase>-CLOSE-REVIEWS.md`) so the pre-execution plan review survives.

   **The close-time payload is the committed tree, however the panel is
   invoked.** `$HOME/.claude/get-shit-done/workflows/review.md` gathers
   `*-PLAN.md`, `*-CONTEXT.md` and `*-RESEARCH.md` and asks for a *plan*
   review — correct before execution, wrong at close. At close, either
   `/gsd-review --all` gathers the shipped subjects (the changed source,
   the artifacts the phase produced, the diff against the phase base), or
   the payload is assembled by hand from those subjects and the three
   reviewer invocations otherwise follow the workflow exactly. **Plans stay
   the pre-execution review target; shipped code is the close-time target.**
   A hand-assembled close-time payload is conforming, not a deviation —
   but say so in the phase record, and name every subject that was left
   out of it.

   **Inline the source rather than pointing reviewers at paths.** On this
   host, codex's sandbox (`bwrap`) fails in a way that lets it exit 0
   having read nothing. Inlining the subject makes a silent sandbox failure
   unable to empty the review. Before counting any reviewer as having
   reviewed, check that the symbols and line numbers in its output actually
   resolve against the tree — and record any reviewer that failed that test
   as failed, rather than as a reviewer.

   **Give the panel the findings already known and tell it not to re-derive
   them** — its budget is better spent on what is *adjacent* to each known
   defect, and on what each suggests about where the same defect class
   lives. Phase 15.4's close-time panel found a harness-neutrality lint hole
   that predated the phase entirely, purely because it was pointed at the
   neighbourhood of a fixed blocker rather than at the blocker.

   **Verify every finding against the tree before recording or acting on
   it, and record the ones you reject as rejected.** Reviewers in this
   project have produced confident, well-formatted, false findings — one
   was rejected outright in Phase 15.1 for fabricated citations, and Phase
   15.4 received a finding asserting that two lint checkers had no tests
   when 41 test functions existed. An unverified finding acted on is worse
   than no review.

   **Ordering, explicitly:** `/gsd:execute-phase` completing is not the end
   of a phase. Execution → cross-AI panel (`--all`) → single-agent code
   review → verify every finding → fix all blocking findings in-phase →
   *then* present to Dave. A phase is not closed until Dave's ruling and
   the `D-GATE-<Phase>` entry, and no defect known at that point should be
   carried into the next phase without an explicit ruling to carry it.
2. **Triage findings.** Classify every finding as **blocking** (a
   violated invariant, a whitepaper-fidelity defect, a missing
   deliverable element, an unsurfaced decision) or **advisory** (style,
   sequencing, deferred-scope observations). Blocking findings are fixed
   inside the current phase before proceeding; advisory findings are
   recorded in the phase deliverable's review appendix and carried
   forward.
3. **Present to Dave.** Deliverables plus the review report plus the
   triage. Dave's approval is the phase gate. `/gsd-review` passing is
   necessary, never sufficient — approval authority is Dave's alone
   (§2), and Dave can reject a deliverable the review passed.
4. **Log and advance.** Approval date recorded in `docs/DECISIONS.md`
   under a `D-GATE-<Phase>` entry. Only then does the next phase begin.

If a blocking finding cannot be fixed without a decision Dave hasn't
made, that is a `D-IMPL-NN` entry and a stop — the phase does not
complete around it.

**Cross-AI reviewer credentials.** When `/gsd-review` invokes external
CLIs, Codex and Cursor authenticate via environment variables sourced
from `/home/parkave/homecams_v2/.env` (never committed to this repo):

- **Codex** — use `CODEX_API_KEY` (not `OPENAI_API_KEY`; that key's
  project lacks API credit). Authenticate with
  `printenv CODEX_API_KEY | codex login --with-api-key` before
  `codex exec`. The ChatGPT-account login is unreliable (revoked
  refresh tokens); prefer API-key auth.
- **Cursor** — export `CURSOR_API_KEY` into the environment before
  `cursor agent -p --mode ask` (the `--trust` flag does not exist in
  the installed version; omit it).

**What each phase's review verifies, minimally:**

- **Phase R** — the inventory satisfies every element of §16, entry by
  entry; no whitepaper section in §5–§8 of the whitepaper lacks
  coverage; the `homecams-patterns` appendix exists with inherit /
  do-not-inherit markers; every open question carries a `D-IMPL-NN`.
- **Phase D** — every inventory entry maps to a design element or an
  explicit deferral; every open `D-IMPL-NN` is either resolved (with
  Dave's ruling recorded) or flagged as gating; the diagram set is
  complete (one per pillar, plus the harness-adapter and ArtifactStore
  seam diagrams); the design preserves every named invariant
  (single-writer, composition-preservation, three validation gates,
  Algorithmic ⇄ Semantic Alternation, audit-by-construction,
  No-Hardcoding, zero harness imports in core) *by construction, on
  paper* — an invariant the design cannot show structurally is a
  blocking finding.
- **Phase F** — every design component carries a verdict (strong fit /
  needs design choice / out of scope for v0); the v0.1 surface is
  explicit; the Phase I gate list (§12) is checked against actual
  resolution status; the test strategy names how each CI-enforced
  invariant will be verified.
- **Phase I** — all CI invariants green: No-Hardcoding lint, harness
  import lint, `@algorithmic` lint, composition-preservation tests for
  every shipped operator pair, replay-by-construction checks (HITL,
  workflow, skill-set capture), and the full §9 examples suite passing
  end-to-end including the two-harness portability assertion in
  example 03. Plus a whitepaper-fidelity spot check: for a sample of
  public classes, the cited whitepaper section actually specifies the
  implemented contract.

**Mini-cycles review too.** A Phase D mini-cycle triggered from Phase I
runs the same protocol scoped to the revisited decision: review, triage,
Dave's approval, `D-GATE` entry. No silent redesign.

## 4. The Common Pillars — User-Facing Architecture

The CCF SDK is organized around five Common Pillars that match how users
actually build agentic systems. The pillars are the **user-facing
architecture**; the L1–L6 fabric layers (§10), the Agent Specialization
Framework (§6), Cross-Process and Harness plumbing (§7), and the
Orchestration/HITL/Experience components (§8) are the **internal mechanism**
that realizes them.

### The five pillars

| Pillar | Purpose | SDK realization |
| --- | --- | --- |
| **Data and Context Layer** | Access to 1st-party data, 3rd-party data, and content produced by other agents. Where Context Assembly agents, the Context Graph, and Systems of Record live. | L1–L5 of the fabric (§10), bidirectional MCP surface (§7.1), ArtifactStore persistence (§7.4), `ContextAssemblyAgent` archetype (§6) |
| **Orchestration Layer** | Method for managing agents and subagents through a workflow. Where multi-agent compositions execute. | Workflow primitive with agent-node and HITL-gate support (§8.1), Protocol for integrating external orchestrators |
| **Core Agent Types** | Six functional archetypes (SDK mechanism) from which *agents* (declared, versioned Control Plane artifacts) are produced by the Agent Factory and specialized through two channels: configuration and skilling. | Agent Specialization Framework (§6) — archetype/agent separation, Agent & Task Factory, dual-channel specialization, harness-neutral agent definitions |
| **Human in the Loop and Control** | Approval, exception handling, override paths, escalation. Every HITL action is replay-integrated. | HITL primitives (§8.2) with audit integration into the five-dimension Decision Replay record |
| **Experience Layer** | The front door — UX, chat, mobile, API. | v0: MCP server (egress), CLI, HTTP API skeleton (§8.3). UX/mobile/chat are reference integrations users build, not SDK components |

### Discipline notes

- **The pillars are how users *think about* building with the SDK.** The
  fabric (L1–L6) is how the SDK *produces* context. The Agent Framework +
  Orchestration + HITL + Experience adapters are how the SDK *delivers* the
  fabric to user applications. All five pillars are mechanism; everything
  domain-specific is values.
- **Specialization spans the pillars and travels through two channels,
  never through subclassing.** A user specializes by (channel 1) declaring
  agents from archetypes with bound context contracts, perspectives, policy
  regimes, and half-life/debt profiles, and by (channel 2) skilling those
  agents from a governed skill catalog. Users also bind workflows to agent
  compositions, approval policies to HITL gates, and experience adapters to
  delivery surfaces. None of this requires the user to fork the SDK — or to
  write an agent in code at all (§6.4).
- **The pillars are not strict layers.** Agents in Core Agent Types read
  from the Data and Context Layer, run inside the Orchestration Layer,
  yield to the HITL pillar at gates, and are reached through the
  Experience Layer. The pillars are organizing categories, not a stack.
- **Every pillar contributes to Decision Replay.** Context state (Data and
  Context), agent identity, version, configuration, and skill-set in force
  (Core Agent Types), workflow trace (Orchestration), human actions (HITL),
  and the calling surface (Experience) all land in the five-dimension
  replay record. The replay story is end-to-end, not fabric-only.

## 5. CCF Primitives — Quick Reference (Data and Context Layer)

These are the primitives the whitepaper commits to in mechanism detail. They
realize the Data and Context Layer pillar. The whitepaper sections are
authoritative; this is orientation, not specification.

- **Context Graph `G(E, R, T, P, Π, L)`** — typed graph state across six axes
  (Entities, Relationships, Time, Policy, Projection, Lineage). Specified in
  §5.2 conceptually and §7.3 in mechanism detail (compound unique index on
  `(tenant_id, entity_uri)`, idempotent upsert with multi-source lineage
  accumulation, single-writer enforcement at boot, append-only with logical
  supersession).
- **Context Operators** — four canonical categories (Traversal, Temporal,
  Policy, Similarity) composing under the algebra
  `ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity`.
  Composition-preservation `(A∘B)(G) = A(B(G))` is required for replay
  determinism. Specified in §7.4.
- **Context Projection `Π`** — Protocol-based projection engine with
  structural typing: `required_operators()` + `invoke()`. Two-stage
  execution (operator plan → projection plan). Specified in §7.5.
- **Context Product Contract** — typed base with `extra=forbid`, the
  eight-element specification per §6.3. Three validation gates:
  empty-operator guard, lineage strict equality, TTL bounds. Per-product
  semver lanes are independent. Specified in §6.3 and §7.6.
- **Context Half-life `λ_c`** — per-observation-type decay rate. Lives in
  Control Plane configuration, not code. Specified in §7.7.1–§7.7.2.
- **Context Debt `D_c`** — quantified shortfall when freshness or
  completeness drops below threshold; gates Forced LLM and Fail-Closed
  behavior. Specified in §7.7.4–§7.7.8.
- **Decision Replay Record** — five dimensions: Context Fabric Snapshot,
  Policy Bindings Snapshot, Model Version Record, Perspective Conditioning,
  Content Generation Path. Specified in §7.10.1. **HITL actions and
  orchestration traces extend dimensions (2) and (4)** — see §8.2. **Agent
  version and skill-set in force extend dimension (4)** — see §6.2.
- **Control Plane vs Data Plane** — Control Plane defines what the fabric
  is allowed to do; Data Plane executes within those constraints. Control
  Plane is also the audit plane (§7.8.2). Specified in §7.8. In the SDK,
  agent definitions, task definitions, prompt artifacts, and skill grants
  are Control Plane artifacts (§6.4).
- **Closed-Loop Self-Learning** — outcomes propagate to Control Plane
  updates (operator parameters, projection weights, policy thresholds,
  half-life adjustments), *not* to model retraining. "The loop is in the
  graph, not the model." Specified in §7.9.
- **Algorithmic ⇄ Semantic Alternation** — algorithmic stages and semantic
  stages alternate. LLMs never see raw signal. Specified in §7.6.6 and is a
  structural invariant CI must enforce.
- **Integration Patterns** — CDC→G (Pattern 1), semantic-layer metadata
  import (Pattern 2), MCP integration (Pattern 3, **bidirectional in the
  SDK — see §7.1**), A2A federation (Pattern 4, **first-class in v0 — see
  §7.2**), Unstructured Ingestion (Pattern 5). Specified in §8.3 with SDK
  extensions noted.

## 6. Agent Specialization Framework (Core Agent Types Pillar)

This section commits the SDK to an extension beyond the whitepaper. Chapter 3
describes agents as consumers of the fabric; it does not specify a framework
for *building specialized agents*. The SDK provides one — labeled clearly as
SDK-defined — because users will always specialize for their specific use
case, and an ad-hoc specialization story produces inconsistent adoption.

Revision 4 makes two structural commitments revision 3 blurred: **archetypes
and agents are different things** (§6.1), and **specialization travels
through two deliberately separated channels — specialization and skilling**
(§6.2).

### 6.1 Archetypes and agents are different things

- **An archetype is a functional template the SDK ships.** It is a named
  bundle of mechanism-level patterns — execution shape, fabric interaction
  pattern, replay obligations — with no identity, no prompts, no skills, no
  policy bindings, and no domain values. Archetypes are SDK code, live in
  `/src`, and are never instantiated directly. An archetype describes *the
  patterns the fabric requires of a class of agent*; it does not describe
  any particular agent, and it does not implement a reasoning loop — the
  loop belongs to the harness (§6.5, §7.3).
- **An agent is a declared, versioned artifact.** It is a named unit of
  decisioning produced by the Agent Factory (§6.4) from an archetype (or a
  composition of archetypes) plus a specialization record plus skill
  bindings. Agents are Control Plane artifacts — data, not code. They carry
  identity, version, and audit lineage. Two deployments running identical
  SDK versions can operate entirely different agent populations without a
  line of diverging code.

Consequences of the separation:

- The SDK's `/src` contains archetypes. It never contains agents. Any agent
  found in library code is a defect of the same severity as a hard-coded
  half-life table.
- Agent identity and versioning hang off the definition artifact and land
  in the Decision Replay record: *which agent, which version, which
  configuration, which skill-set* made this decision is answerable from
  replay alone.
- Because an agent is an artifact rather than code, it is harness-neutral
  by construction (§6.5) and portable across storage substrates via the
  ArtifactStore (§7.4).

### 6.2 Two channels of specialization: specialization and skilling

An agent's behavior is specialized through two distinct channels. The
separation is load-bearing; do not collapse it in design or implementation.

**Channel 1 — Specialization (the identity-and-constraint channel).**
Fixed in the agent's definition artifact and versioned with it. Changing
any axis produces a *new agent version*. Six axes:

1. **Archetype binding** — which archetype(s) supply the agent's execution
   and fabric-interaction patterns, and how they compose (D-IMPL-11,
   D-IMPL-19).
2. **Context contract** — which Context Product schemas the agent reads,
   and/or which projection it emits to.
3. **Perspective** — the Π role-conditioning that shapes the agent's view
   of the graph and the products it consumes.
4. **Policy regime** — the Control Plane bundle in force for this agent
   (entitlements, jurisdictional bindings, regulatory regime, HITL policy,
   and the envelope of skills the agent is *permitted* to bind).
5. **Half-life and debt profile** — what staleness the agent tolerates,
   what `D_c` threshold triggers Forced LLM or Fail-Closed.
6. **Instruction bindings** — references (never inline text — §6.4) to
   versioned prompt/instruction artifacts.

**Channel 2 — Skilling (the capability channel).** Skills are typed,
governed capabilities registered in the skill catalog: tools, MCP
resources, A2A endpoints exposing remote Context Products, or local
callables. Skills bind to agents *by reference* and can be attached,
upgraded, or revoked over the agent's life through the Control Plane
**without re-declaring the agent** — subject to governance:

- The policy regime (channel 1) defines which skills an agent *may* bind;
  skilling defines which it *does* bind. The Control Plane refuses a skill
  bind whose declared requirements exceed the agent's policy regime or
  context contract. This compatibility check is mechanism, shipped with
  the SDK.
- A skill grant or revocation is itself an audited Control Plane action.
  The skill-set in force at decision time is part of the Decision Replay
  record — a decision replays against the skills the agent actually had,
  not the skills it has now.

**Why two channels.** Specialization changes *who the agent is*; skilling
changes *what the agent can currently do*. Conflating them forces a full
agent redefinition for every capability change, or — worse — ungoverned
capability sprawl inside a nominally fixed agent. Keeping them separate
yields: (a) stable agent identity for audit and replay; (b) capability
agility under explicit governance; (c) a clean seam for harness adapters,
which expose exactly the currently-bound skill-set as the harness's tools
(§7.3) — no more, no less.

### 6.3 The six core archetypes

The SDK ships a unified `Agent` base plus six archetypes. Declaring an
agent from an archetype is the accelerated path, not a requirement — a
user can declare against the base directly — but the archetypes encode
patterns common to each functional category and accelerate adoption.

- **`WorkflowAgent` / `TaskAgent`** — procedural, multi-step. Patterns:
  state-machine execution, deterministic step ordering, skill orchestration
  against a defined task graph, structured idempotency. Examples: KYC,
  credit checks, onboarding, routing, fulfillment. Heavy interaction with
  the Orchestration Layer (§8.1).
- **`DocumentIntelligenceAgent`** — focused on document operations.
  Patterns: ingest, metadata extraction, analysis, generation, with
  passage-level lineage (§7.10.3) baked into outputs. Heavy use of the
  unstructured pipeline (Pattern 5). Examples: document analysis pipelines,
  document drafting agents, content-search agents.
- **`AnalyticsInsightsAgent`** — computation over Context Products.
  Patterns: temporal analysis against the T dimension, threshold detection,
  comparative analysis across entities, signal aggregation. Examples:
  financial analysis, covenant monitoring, client intelligence,
  performance analysis.
- **`MonitoringSurveillanceAgent`** — long-running, trigger-driven.
  Patterns: event subscription against L1 streams, threshold-based
  activation, continuous freshness with `λ_c`-driven re-evaluation. Examples:
  deal monitoring, market signal detection, client triggers, anomaly watch.
- **`ContentGenerationAgent`** — structured LLM output. Patterns:
  template binding, citation-aware generation (§7.10.3 — every claim
  passage-anchored), draft-and-review HITL integration (§8.2). Examples:
  credit memos, research notes, pitch decks, narrative reports.
- **`ContextAssemblyAgent`** — assembler agent producing Context Products
  for consumption by other agents. The recursive context enrichment case
  §6.6 names. Produces Context Products on the wire, transported via
  in-process call, MCP server, or A2A federation.

**Archetypes are functional categories, not exclusive categories.** A
single agent can compose archetypes: a `MonitoringSurveillanceAgent` can
produce Context Products (assembler behavior) for downstream
`AnalyticsInsightsAgent`s; a `ContentGenerationAgent` can also be a
`ContextAssemblyAgent` if its output is itself a typed Context Product.
The archetypes are templates of common patterns, not a class hierarchy
users must navigate. The SDK exposes archetype composition as
mixins-or-composition (see D-IMPL-11 and D-IMPL-19 — open) rather than as
a deep hierarchy.

### 6.4 The Agent & Task Factory and the No-Hardcoding Rule

The SDK constructs agents and tasks **exclusively through factories** that
interpret declarative definition artifacts. There is no supported path to
an agent or task that bypasses the factory.

**The No-Hardcoding Rule (structural invariant).** Absolutely no inline
prompts and no hardcoded system logic inside code files — in `/src`,
`/runtime`, or `/examples`. Concretely:

- **No prompt or system-instruction string literal in code.** Prompts and
  instructions are versioned artifacts referenced by URI from agent and
  task definitions (specialization axis 6).
- **No agent definition in code.** Agents come from the Agent Factory
  reading definition artifacts. Tests construct agents the same way, from
  fixture artifacts.
- **No task graph, routing table, threshold, approval rule, or skill grant
  expressed as code constants.** These are Control Plane artifacts
  interpreted by mechanism.
- **Code contains interpreters and factories, never the things
  interpreted.**

Enforcement is CI, in the same spirit as the Algorithmic ⇄ Semantic lint
(§11): a lint pass rejects prompt-shaped string literals in code modules
and rejects agent or task construction that bypasses the factory.
Definition artifacts live under version control and/or the ArtifactStore
(§7.4) with their own semver lanes. The definition artifact format —
schema language, prompt templating, versioning — is D-IMPL-28 (open).

This rule is why the examples suite (§9) is structured as *code and
artifacts side by side*: the code is thin and generic; the artifacts carry
everything specific. An example whose code would still run meaningfully
with its artifacts deleted has violated the rule.

### 6.5 Agents are harness-neutral by construction

Because an agent is an artifact, nothing in its definition names a
harness. The same agent definition runs under Google ADK, the Claude Agent
SDK, or a bespoke loop, bound at runtime by a Harness Adapter (§7.3)
which maps: the agent's currently-bound skills onto the harness's tool
interface; the agent's context contract onto typed Context Product
consumption; the harness's outputs back through governed effect capture;
and the harness's execution trace into the five-dimension replay record.
Archetypes describe patterns the *fabric* requires — replay obligations,
fabric interaction shape — not a loop implementation. The loop belongs to
the harness; the trust, the context, and the audit belong to CCF.

## 7. Cross-Process and Harness-Neutral by Default

The SDK assumes from v0 that **agents will not all run in the same
process**, and that **agents will not all run under the same harness**.
Both are deliberate scoping decisions and they shape the rest of the
design.

### 7.1 MCP as a bidirectional integration surface

The whitepaper's Pattern 3 (§8.3) frames MCP as "Context Product export."
The SDK extends this: MCP is a bidirectional surface used at multiple
points in the fabric.

- **MCP as ingress (L1).** MCP servers front-end source data stores
  feeding the Signal Layer. The SDK ships an MCP client that consumes
  external MCP servers — calendar systems, document repositories,
  transactional stores, communications archives — and normalizes their
  outputs into the L1 event envelope. CDC and MCP-ingress are
  complementary: CDC for transactional capture, MCP for query-based
  acquisition of content-rich systems.
- **MCP as ingress for content acquisition (L4–L5).** When operators or
  projections need to acquire content at decision time, the same MCP
  client surface serves the acquisition. This is where the
  search-inference recursion of §6.6 lives.
- **MCP as egress (L6).** The fabric exposes Context Products as MCP
  Resources, per Pattern 3 unchanged. Any MCP-capable agent runtime
  consumes them without knowing anything about the fabric's internals.
- **MCP as the Experience Layer access surface.** External agent runtimes
  (Anthropic's Claude products, third-party agent frameworks) reach the
  SDK's Context Products through the same MCP egress used by internal
  consumers. The Experience Layer (§8.3) treats the MCP server as one of
  three v0 front doors.
- **MCP as the artifact persistence transport.** The ArtifactStore's
  reference implementation is an MCP server (§7.4).

Implication: the SDK is both an MCP client and an MCP server, in more
than one role each. The SDK-as-MCP-client and SDK-as-MCP-server live in
different modules; their contracts and trust postures differ, and the
artifact-persistence role (§7.4) is distinct from the egress role.

### 7.2 A2A federation is first-class in v0

Agent-to-Agent context exchange across process or organizational
boundaries is a v0 commitment, not a v1 deferral.

What A2A means for the SDK:

- **Transport for cross-process Context Product exchange.** When an
  assembler agent in one process emits a Context Product consumed by a
  decisioning agent in another, A2A is the wire format. The Context
  Product Contract travels intact across the boundary.
- **Trust boundary verification.** Per §8.3 Pattern 4, A2A trust
  boundaries are resolved via Policy bindings carried in the exchanged
  Context Product and **verified at the consumer's Control Plane before
  admission into the consuming fabric's graph**. The SDK enforces this as
  a structural commitment: an inbound A2A Context Product is not
  admissible to L3 until the consuming Control Plane validates its Policy
  bindings.
- **Identity and attestation.** Agent identity, signing of emitted
  products, verification of inbound signatures.
- **Lineage continuity.** Inbound L extends, not replaces, the consumer's
  L via set-union; producer's operator plan, graph snapshot, and policy
  version are all preserved.

Industry A2A standards at 2026 state are emergent. SDK posture: a
`WireProtocol` abstraction with the most production-credible primitive as
the v0 default. **The Context Product Contract is the stable layer; the
wire is replaceable.**

### 7.3 Harness neutrality and the Harness Adapter Protocol

This is of paramount importance and is load-bearing for CCF's entire
positioning: **CCF layers onto any agent harness as the trust-and-control
plane. It does not absorb the agent loop, and it does not ship one.** The
reasoning loop, the tool-calling loop, planning behavior, sub-agent
spawning semantics — those belong to the harness, whether that is Google
ADK, the Claude Agent SDK, LangGraph, or a bespoke loop. CCF's job is
what no harness provides: governed, typed, replay-ready context in;
policy-verified, lineage-preserving effects out.

Commitments:

- **Zero harness imports in core.** No module in `/src` imports any
  harness package. CI enforces this via an import lint using the same
  machinery as the `@algorithmic` lint (§11). A harness import in `/src`
  is a defect of the same class as an LLM client in an algorithmic module.
- **`HarnessAdapterProtocol`.** Harness bindings live in
  `/runtime/adapters/<harness>/` as Protocol implementations. A conforming
  adapter binds four seams:
  1. **Context injection** — typed Context Products into the harness's
     context/memory/prompt-assembly surface, without the harness ever
     touching L3 or raw signal.
  2. **Skill exposure** — the agent's *currently-bound* skill-set (§6.2)
     surfaced as the harness's tools. Skills the agent has not been
     granted do not exist from the harness's point of view.
  3. **Effect capture** — harness outputs routed back through governed
     emission (typed Context Product) or L2 write-back. A harness never
     acquires a write handle to the graph; the single-writer invariant
     (§10) holds across the adapter boundary.
  4. **Replay hooks** — model version, prompt-artifact version, and
     execution trace captured into the five-dimension Decision Replay
     record.
- **The neutral seams are the stable layer.** Typed Context Product
  Contract + MCP + A2A. A harness that already speaks MCP needs no
  adapter for *consumption*; the adapter earns its keep on skill
  exposure, effect capture, and replay.
- **Reference adapters ship with v0.** Which harnesses get reference
  adapters is D-IMPL-24 (open; Google ADK and the Claude Agent SDK are the
  presumptive pair). The mandatory-vs-optional status of the four seams
  for a conforming adapter is D-IMPL-25 (open).
- **Portability is demonstrated, not asserted.** The examples suite (§9)
  must show one agent definition running unmodified under at least two
  harnesses, producing equivalent Context Product consumption and
  replay records.

### 7.4 MCP Artifact Persistence — the ArtifactStore

The SDK persists CCF artifacts through an `ArtifactStoreProtocol` with an
**MCP-backed reference implementation**, so users are free to use their
own persistent store and decision-playback data store by standing up (or
pointing at) an MCP server that implements the artifact resource
contract. A file-backed implementation ships for development.

Artifact classes in scope:

- Graph snapshots and similarity-index snapshots (what makes §7.10 replay
  tractable at year-scale — D-IMPL-06).
- Context Products at rest.
- Decision Replay records, all five dimensions including the HITL and
  workflow extensions (§8.1, §8.2).
- Control Plane bundles: policy bundles, `λ_c` tables, workflow
  definitions, HITL policies, A2A trust policy.
- The No-Hardcoding artifacts (§6.4): agent definitions, task
  definitions, prompt/instruction artifacts, skill catalog entries and
  grants.

Constraints — structural, not advisory:

- **Single-writer preserved.** The ArtifactStore is a persistence
  substrate reached *through* L2 and Control Plane mechanism. An MCP
  artifact server never becomes a second writer to L3; nothing enters the
  graph except through L2, including artifacts retrieved from the store.
- **Replay determinism.** Artifacts are immutable and versioned —
  content-addressed or versioned-URI, the addressing scheme is D-IMPL-26
  (open). Replay resolves *exact* artifact versions, never "latest."
- **Trust posture.** The artifact MCP server sits inside the tenant trust
  boundary but is authenticated. Artifacts arriving from *outside* the
  boundary are A2A's problem (§7.2) — admission via Control Plane
  verification — never the store's.
- **Hot state vs artifacts may split substrates.** The live Context Graph
  remains on the graph storage Protocol (Postgres/SQLite reference impls,
  D-IMPL-02); the ArtifactStore holds versioned artifacts. Which artifact
  classes route through the ArtifactStore in v0 versus native storage
  Protocols is D-IMPL-27 (open).

## 8. Orchestration, HITL, and Experience (Three Remaining Pillars)

These are SDK extensions beyond the whitepaper. The whitepaper assumes a
control plane and a delivery surface but does not specify multi-agent
workflow primitives, human-in-the-loop mechanics, or front-door integration.
The SDK provides these because they are what users actually need to put
specialized agents into production.

### 8.1 Orchestration Layer

**What the SDK provides.** A minimal Workflow primitive — sufficient to
compose multi-agent and multi-step workflows with HITL gates — plus a
Protocol for integrating external orchestrators when users need more
heavyweight workflow infrastructure.

The Workflow primitive has these properties:

- **Agent nodes.** Each step in a workflow is either a skill invocation,
  an agent invocation, or a HITL gate. Agent invocations carry the
  context contract the called agent expects. Consistent with the
  No-Hardcoding Rule (§6.4), workflow definitions are Control Plane
  artifacts produced through the Task Factory, not code.
- **State machine semantics.** Workflows are state machines with explicit
  states, transitions, and terminal conditions. State is persisted at
  the Control Plane boundary so a workflow can suspend on a HITL gate or
  a long-running monitoring trigger and resume later.
- **Replay integration.** Workflow execution traces extend the Decision
  Replay record's Perspective Conditioning dimension (the calling agent
  chain) and Content Generation Path dimension (the step sequence). A
  workflow re-replays exactly under the same inputs and Control Plane
  state.
- **Exception paths.** Every workflow node can yield to an exception path
  (typically a HITL gate). Exception paths are first-class state
  transitions, not error handling glued on after the fact.
- **Harness-neutral at every node.** An agent node invokes an agent
  *definition*; which harness executes it is resolved through the
  adapter binding (§7.3), not through the workflow.

**What the SDK does *not* provide.** A heavyweight workflow engine. If
users need durable execution at Temporal/Step-Functions scale, they
implement an `OrchestrationProtocol` adapter to the external engine. The
SDK's Workflow primitive is for in-fabric coordination, not for
enterprise-grade durable orchestration.

This boundary is intentional. Reinventing Temporal is out of scope.

### 8.2 Human in the Loop and Control

**What the SDK provides.** HITL primitives that any orchestration layer
(in-SDK or external) can compose, with audit integration into the
five-dimension Decision Replay record by construction.

The HITL primitives are:

- **ApprovalGate** — a workflow step that suspends until a human
  approves or rejects. The approval action lands in the replay record
  with the approver's identity, the time of approval, the Context
  Product the approver saw, and any annotations.
- **ExceptionEscalation** — a routing primitive that hands a workflow
  state to a designated human role when a condition (typically `D_c`
  threshold breach or an agent's explicit escalation) is met.
- **OverrideBoundary** — a typed boundary at which a human can substitute
  a value the agent would otherwise have produced. Overrides are
  audited; the original agent output and the override are both in the
  replay record.
- **ReviewQueue** — a primitive for asynchronous human review of
  ContentGenerationAgent outputs (credit memos, narratives) before
  release. Integrates with passage-level lineage so reviewers can see
  what each claim is anchored to.

**The audit-by-construction commitment.** Every HITL primitive writes to
the Decision Replay record as a structural invariant, not as an opt-in
hook. There is no path through the HITL surface that produces an
unrecorded human action. CI verifies the invariant.

**What the SDK does *not* provide.** A human task management UI. The
SDK exposes HITL events through Protocols (queue interfaces, webhook
hooks, MCP server endpoints) so users can wire them to their existing
human-task systems. The SDK does not ship a workflow inbox.

### 8.3 Experience Layer

**What the SDK provides for v0.** Three front-door surfaces:

- **MCP server** — Context Products and agents exposed as MCP Resources
  and MCP Tools (per §7.1). The primary surface for external agent
  runtimes consuming the fabric.
- **CLI** — `ccf` command-line tool for interactive use, workflow
  invocation, HITL queue inspection, replay queries, and Control Plane
  configuration — including agent declaration, skill grant/revoke, and
  artifact inspection against the ArtifactStore.
- **HTTP API skeleton** — REST endpoints over the fabric. The primary
  surface for service integration and for custom UX layers users build.

**What the SDK does *not* provide for v0.** No mobile SDK, no chat
adapter, no web UI. These are reference integrations users build on top
of the HTTP API. The SDK provides example HTTP clients and an OpenAPI
spec so building these is straightforward; it does not ship them.

This boundary preserves the "Experience Layer is the user's UX" framing
while still giving users a working front door from day one.

## 9. SDK Usage Examples — the v0 Examples Suite

The examples are the adoption contract: they are how a competent
engineering team gets from `pip install` to a governed, replayable,
multi-agent deployment in hours, and they are how the SDK's claims —
general-purposeness, harness neutrality, No-Hardcoding, audit by
construction — are *demonstrated* rather than asserted.

**The Homecams rebuild on the CCF SDK is a planned post-v0 validation
exercise. It is explicitly not part of the initial release.** The initial
release ships practical, runnable, domain-neutral examples instead.

### Discipline for every example

- **Runnable end-to-end** against the reference backends (SQLite-for-dev
  graph store, file-backed ArtifactStore), with a single documented
  command. Examples run in CI; a broken example is a broken build.
- **Code and artifacts side by side.** Per the No-Hardcoding Rule (§6.4),
  each example's directory contains thin generic code plus the definition
  artifacts (agent definitions, prompt artifacts, policy bundles, workflow
  definitions, skill registrations) that carry everything specific. The
  artifacts are the teaching material as much as the code.
- **A README per example** stating what it demonstrates, which whitepaper
  sections and which sections of this document it exercises, and what the
  user should change first to adapt it.
- **A horizontal mix of domains across the suite** (D-IMPL-52, Dave,
  2026-07-25 — this *replaces* the former "one coherent neutral domain"
  rule). Examples deliberately span unrelated domains, because a suite
  that visibly crosses domains demonstrates generality more convincingly
  than a single neutral domain held constant. **`examples/00-quickstart`
  — and the Phase I.1 vertical-slice fixtures that precede it — are a
  banking scenario**, which also puts realistic policy and regulatory
  pressure on the fabric. What does not change: no example is a domain
  pack, and everything domain-specific lives in definition artifacts,
  never in example code (the No-Hardcoding Rule, §6.4).

### The v0 suite

1. **`examples/00-quickstart`** — the smallest possible fabric. Register a
   minimal ontology, ingest a handful of events through L1, assemble, and
   serve one typed Context Product in-process. "Hello, Context Product."
2. **`examples/01-agent-basics`** — declare an agent from the
   `AnalyticsInsightsAgent` archetype via a definition artifact, construct
   it through the Agent Factory, run it against the quickstart fabric.
   Demonstrates the archetype/agent separation (§6.1) and all six
   specialization axes (§6.2, channel 1).
3. **`examples/02-skilling`** — grant a new skill to the running agent
   through the Control Plane, exercise it, revoke it. Demonstrates channel
   2: the agent definition never changes; the governance compatibility
   check fires on an impermissible grant; every grant and revocation
   appears in the replay record.
4. **`examples/03-harness-portability`** — one agent definition executed
   unmodified under two harnesses via their adapters (per D-IMPL-24), with
   an assertion that Context Product consumption and the replay records
   are equivalent. This is the harness-neutrality proof (§7.3).
5. **`examples/04-cross-process`** — an assembler agent
   (`ContextAssemblyAgent`) in one process, a consumer agent in another,
   exchanging a Context Product over MCP egress and over A2A, with
   Control Plane admission verification demonstrated on the consumer side.
6. **`examples/05-workflow-hitl`** — a multi-step workflow with an
   ApprovalGate and an ExceptionEscalation path; suspend on the gate,
   resume on approval; the human action lands in the replay record.
7. **`examples/06-decision-replay`** — replay a prior decision:
   resolve the graph snapshot, policy bundle version, agent version,
   skill-set, and prompt-artifact versions from the ArtifactStore and
   reproduce the Context Product exactly.
8. **`examples/07-artifact-store-mcp`** — swap the file-backed
   ArtifactStore for the MCP-backed reference store. Nothing else in the
   deployment changes. Demonstrates §7.4 pluggability.

Examples 04 + 05 together supersede the former "one full end-to-end
deployment" scope bullet; the composed pair *is* that deployment.

### What the examples are not

They are not domain packs, starter kits, or product templates. They
demonstrate mechanism. Anything in an example that a user would ship
unmodified to production belongs in the SDK; anything a user must replace
belongs in artifacts — and the examples make that boundary visible.

## 10. Architectural Layers (L1–L6) — Fabric Internals

The SDK's package structure for the fabric reflects the layered
architecture (§7.1 of the whitepaper):

- **L1 Signal Layer** — ingestion + event normalization. Includes CDC
  ingress, MCP client ingress (§7.1), file/stream adapters.
- **L2 Context Assembly** — entity resolution, temporal stitching, policy
  binding, operator invocation. **Only writer** to the graph.
- **L3 Context Graph** — typed persisted graph (§7.3 whitepaper).
- **L4 Context Operators** — typed composable read-only operators (§7.4).
  May invoke MCP clients for content acquisition.
- **L5 Context Projection** — Π as typed transformation (§7.5). May
  invoke MCP clients for late-binding content acquisition.
- **L6 Context Products** — delivery contract with SLO envelope (§7.6).
  Served via in-process call, MCP server, or A2A endpoint.

Above L6 sit the SDK extensions: the Agent Specialization Framework and
Agent & Task Factory (§6), the Harness Adapter surface (§7.3), the
Orchestration Layer (§8.1), the HITL primitives (§8.2), and the
Experience Layer surfaces (§8.3).

Two orthogonal planes cut across all six fabric layers and the SDK
extensions:

- **Control Plane** — versioned configuration, policy registry, λ_c
  tables, approval workflows, agent and task definition artifacts, prompt
  artifacts, skill catalog and grants, A2A trust policy, workflow
  definitions, HITL policy. Audit plane.
- **Data Plane** — runtime execution against Control Plane configuration.

The single-writer invariant (only L2 holds a write handle to L3) is
**architectural, not advisory.** Enforce via dependency injection at boot.
This holds for A2A admissions (an inbound A2A Context Product enters L3
only through L2, after Control Plane verification), for harness effect
capture (§7.3 — no harness ever acquires a write handle), and for the
ArtifactStore (§7.4 — the store is a substrate behind mechanism, never a
second writer).

## 11. Working Principles

These principles override Claude Code's general defaults for this project:

**Whitepaper fidelity over speed.** When in doubt, re-read the relevant
whitepaper section before writing code. Cite the section in the docstring
of every public class. Where the SDK extends beyond the whitepaper (the
Agent Specialization Framework, the Agent & Task Factory, bidirectional
MCP, A2A as first-class, the Harness Adapter surface, the ArtifactStore,
the Orchestration Layer, HITL primitives, the Experience Layer),
docstrings cite *this* document and mark the extension explicitly.

**Surface gaps; do not paper over them.** When the whitepaper is silent
or ambiguous on a point a general-purpose implementation has to commit on,
log the gap as a `D-IMPL-NN` decision in `docs/DECISIONS.md` and stop.
Do not pick a default and hope. Do not pattern-match to "what Homecams
probably did." Wait for Dave.

**Mechanism, not values.** The SDK provides the machinery for half-life,
policy, projection, ontology, skills, agent specialization, workflows,
HITL policies, and experience surfaces — never bakes in domain values.
If a hard-coded table, threshold, skill catalog, projection role, workflow
definition, or approval policy appears in `/src`, that is a defect.

**No hardcoded prompts or system logic — anywhere.** The No-Hardcoding
Rule (§6.4) applies to `/src`, `/runtime`, and `/examples` alike. Prompts,
instructions, agent definitions, task definitions, and routing values are
versioned artifacts constructed through the Agent & Task Factory. Code is
interpreters and factories. CI lint enforces it.

**Harness neutrality is an invariant, not an aspiration.** Zero harness
imports in `/src`, enforced by CI import lint. Harness-specific code lives
only in `/runtime/adapters/<harness>/` behind `HarnessAdapterProtocol`.
The agent loop is never absorbed and never shipped.

**Typed contracts at every boundary.** Every public surface uses typed
contracts (Pydantic models with `extra=forbid` in Python, equivalents in
other languages if scoped). Validation is at the boundary, never deferred.

**Composition-preservation is a property, not a hope.** Every operator is
a pure function over typed inputs. Tests verify `(A∘B)(G) = A(B(G))`
empirically for every operator pair the SDK ships.

**Decision Replay is enforced at write time, not retrofitted.** Every
ContextProduct that the delivery layer serves is replay-ready by
construction. **Every HITL action is replay-recorded by construction**
(§8.2). **Every workflow trace lands in replay by construction** (§8.1).
**Every skill grant, revocation, and the skill-set in force at decision
time lands in replay by construction** (§6.2). Lineage strict equality is
a validation gate, not a debug feature.

**No hidden model calls in the algorithmic path.** The Algorithmic ⇄
Semantic Alternation is a structural invariant. A CI lint rule rejects any
import of an LLM client in modules tagged `@algorithmic`.

**Prefer Protocols over inheritance.** Storage backends, vector indices,
operator implementations, projections, MCP transports, A2A transports,
harness adapters, artifact stores, agent skills, agent archetypes,
orchestration backends, HITL routers, and experience adapters are all
Protocol-based.

**Reference implementations ship alongside Protocols.** For every
pluggable substrate, the SDK ships a working reference impl. Users plug in
alternatives by implementing the Protocol.

## 12. Open Decisions Awaiting Dave (Decision Log Scaffolding)

These are surfaced now because Phase D cannot complete without resolutions.
Each `D-IMPL-NN` gets its resolution, its date, and a reference to the
whitepaper section or to this document's section where the question
originates.

**Fabric and core (Data and Context Layer):**
- **D-IMPL-01 — Language target.** Python (default), TypeScript, both, or
  language-agnostic protocol + reference impl?
- **D-IMPL-02 — Graph storage substrate.** Storage Protocol + reference
  Postgres impl + SQLite-for-dev impl (recommended), or single backend?
- **D-IMPL-03 — Vector substrate.** SimilarityIndex Protocol + reference
  impl on sqlite-vec / Chroma, or single vendor?
- **D-IMPL-04 — Runtime topology for v0.** Confirmed: library **and**
  runtime. Sub-decisions: (a) one binary or library+runtime as separate
  packages; (b) sync, async, or both for the agent host loop.
- **D-IMPL-05 — Tenancy model.** Single-tenant per process, multi-tenant
  with `tenant_id` first-class, or both via configuration?
- **D-IMPL-06 — Snapshot management for replay.** Storage strategy for
  graph snapshots and similarity-index snapshots making §7.10 replay
  tractable at year-scale. Interacts with the ArtifactStore (§7.4,
  D-IMPL-26/27).
- **D-IMPL-07 — Embedding model abstraction.** EmbedderProtocol with
  reference adapters, or one model?
- **D-IMPL-08 — Unstructured pipeline (Pattern 5) pluggability.** Each
  stage as a Protocol, or one opinionated pipeline?
- **D-IMPL-09 — LLM access for semantic stages.** Direct Anthropic SDK
  (with §7.10.3 Citations API), or LLMClientProtocol with multi-vendor
  adapters?
- **D-IMPL-10 — Repo shape.** Provisionally resolved as **monorepo**
  at `github.com/drcastillo/ccf_code` — core + runtime + adapters +
  examples + docs together — per §2.2. Remaining open under this
  entry: whether adapters split into separate packages or repos
  post-v0.

**Cross-process and trust:**
- **D-IMPL-13 — MCP role allocation.** Which integration edges use MCP
  (per §7.1), and what's the SDK's API per role?
- **D-IMPL-14 — A2A wire protocol.** Which transport for v0? MCP-over-A2A
  extensions, custom typed RPC over HTTP/2+mTLS, or other? WireProtocol
  abstraction committed; v0 default needs ruling.
- **D-IMPL-15 — Agent identity and signing.** PKI primitives for A2A
  (X.509, JWT, SPIFFE/SPIRE, custom)?
- **D-IMPL-16 — Control Plane scope at A2A boundary.** Verify every
  inbound A2A Context Product, or fast-path admissions for high-trust
  peers?

**Agent Specialization Framework (Core Agent Types):**
- **D-IMPL-11 — Agent base shape.** Class hierarchy, pure Protocol with
  composable mixins, or single configurable class with role resolved at
  runtime? Originates in §6. Interacts with the archetype/agent
  separation (§6.1): whatever the shape, archetypes stay in code and
  agents stay in artifacts.
- **D-IMPL-12 — Skill catalog model.** Static registry at boot? Dynamic
  registration via Control Plane? MCP-Resources-as-skills as the unified
  mechanism? Originates in §6. Interacts with D-IMPL-29 (skilling
  governance).
- **D-IMPL-19 — Agent archetype expression.** Mixins, composition, or
  templates? How do users combine archetypes (e.g., a monitoring agent
  that is also an assembler)? Originates in §6.3.
- **D-IMPL-28 — Definition artifact format.** Schema language for agent
  and task definition artifacts (YAML/JSON validated by exported JSON
  Schema, Pydantic-native, or other), prompt-artifact templating
  approach, and semver lane structure. Originates in §6.4. Gates the
  Agent & Task Factory and therefore most of the agent surface.
- **D-IMPL-29 — Skilling governance depth.** Does a runtime skill grant
  require only the automatic policy-compatibility check, or can policy
  regimes require an approval workflow (HITL gate) on grant? Skill
  requirement-declaration schema. Originates in §6.2.

**Harness neutrality:**
- **D-IMPL-24 — Harness adapter targets for v0.** Google ADK and the
  Claude Agent SDK are the presumptive reference pair. Confirm, and rule
  whether a third (e.g., LangGraph) makes v0 or waits. Originates in
  §7.3. The examples suite (§9, example 03) depends on this.
- **D-IMPL-25 — HarnessAdapterProtocol seam scope.** Are all four seams
  (context injection, skill exposure, effect capture, replay hooks)
  mandatory for a conforming adapter, or is effect capture optional for
  read-only consumers? Originates in §7.3.

**Artifact persistence:**
- **D-IMPL-26 — Artifact addressing and versioning.** Content-addressed
  vs versioned-URI addressing; the MCP resource contract shape for the
  reference artifact server. Originates in §7.4. Interacts with
  D-IMPL-06.
- **D-IMPL-27 — Substrate split.** Which artifact classes route through
  the ArtifactStore in v0 versus remaining on native storage Protocols
  (live graph state on the graph store, etc.)? Originates in §7.4.

**Orchestration:**
- **D-IMPL-17 — Orchestration primitive scope.** Minimal in-SDK Workflow
  primitive + Protocol for external orchestrators (recommended), or
  Protocol only with no reference impl? Originates in §8.1.
- **D-IMPL-18 — Workflow state persistence.** Where does suspended
  workflow state live? Control Plane (recommended), separate workflow
  store, or pluggable Protocol? Originates in §8.1. Interacts with
  D-IMPL-27.

**HITL:**
- **D-IMPL-20 — HITL transport.** How are HITL events delivered to
  humans for v0? Queue interface only (let users wire to their own
  systems), webhook hooks, or MCP server endpoints exposing HITL queues?
  Originates in §8.2.
- **D-IMPL-21 — HITL identity binding.** How is the approver's identity
  bound to the audit record? Same PKI as A2A (D-IMPL-15), separate, or
  pluggable? Originates in §8.2.

**Experience Layer:**
- **D-IMPL-22 — CLI shape.** Subcommand structure for the v0 CLI,
  including agent declaration, skilling, and artifact inspection
  commands. Originates in §8.3.
- **D-IMPL-23 — HTTP API surface.** Which endpoints in v0? Originates in
  §8.3.

**Gating discipline.** Do not start Phase I until at least these are
provisionally resolved:
- D-IMPL-01 through D-IMPL-05 (fabric and runtime fundamentals)
- D-IMPL-11 (agent base shape)
- D-IMPL-14 (A2A wire protocol)
- D-IMPL-17 (orchestration primitive scope)
- D-IMPL-20 (HITL transport)
- D-IMPL-24 (harness adapter targets — example 03 and the adapter
  surface cannot be built without it)
- D-IMPL-26 (artifact addressing — replay and the factory both depend
  on it)
- D-IMPL-28 (definition artifact format — the Agent & Task Factory
  cannot be built without it)

The remainder can resolve in parallel with early Phase I work on the core.

## 13. Scope and Non-Scope

### In scope for the SDK (v0)

**Data and Context Layer:**
- Context Graph state primitive with reference Postgres + SQLite backends.
- Operator algebra with the four canonical operator categories.
- Projection engine with structural typing.
- Context Product Contract base + the three validation gates.
- Half-life and Debt computation.
- Five-dimension Decision Replay record + replay engine, extended to
  cover HITL actions, workflow traces, agent versions, and skill-sets in
  force.
- Control Plane as an in-process versioned registry, with extension
  point for remote control planes.
- ArtifactStore Protocol with MCP-backed reference implementation and
  file-backed dev implementation (§7.4).
- CDC→G ingress reference (Pattern 1).
- Algorithmic ⇄ Semantic Alternation enforced as CI invariant.

**Core Agent Types:**
- Unified Agent base + six archetypes (`WorkflowAgent`,
  `DocumentIntelligenceAgent`, `AnalyticsInsightsAgent`,
  `MonitoringSurveillanceAgent`, `ContentGenerationAgent`,
  `ContextAssemblyAgent`) as SDK mechanism per §6.1.
- Agent & Task Factory + the declarative definition-artifact schema
  (per D-IMPL-28), with the No-Hardcoding Rule enforced in CI.
- Skill catalog primitives: registration, discovery, governance,
  runtime grant/revoke with policy-compatibility check and replay
  capture (§6.2).

**Cross-Process and Harness:**
- Bidirectional MCP (client at L1/L4/L5/Experience, server at L6 and at
  the ArtifactStore).
- A2A federation with WireProtocol abstraction, identity/signing
  primitives, and Control Plane admission verification.
- `HarnessAdapterProtocol` + reference adapters for the harnesses ruled
  in D-IMPL-24, with the zero-harness-imports-in-core CI lint.

**Orchestration Layer:**
- Workflow primitive with agent nodes and HITL gates, suspendable on
  Control Plane state; workflow definitions as Control Plane artifacts.
- OrchestrationProtocol for external orchestrator integration.

**Human in the Loop:**
- HITL primitives (ApprovalGate, ExceptionEscalation, OverrideBoundary,
  ReviewQueue) with audit-by-construction integration into Decision
  Replay.

**Experience Layer:**
- MCP server (egress).
- CLI (`ccf`) for interactive use, workflow invocation, HITL inspection,
  replay queries, Control Plane configuration, agent declaration,
  skilling, and artifact inspection.
- HTTP API skeleton with OpenAPI spec.

**Examples and demonstrability:**
- The eight-example v0 suite specified in §9, in a single coherent
  neutral domain, run in CI. Examples 04 + 05 together constitute the
  full end-to-end cross-process + HITL deployment; example 03
  demonstrates harness portability.

### Out of scope for the SDK (v0)
- **An agent loop or harness of any kind.** The SDK never ships or
  absorbs a reasoning/tool-calling loop; harness integration is adapters
  only (§7.3).
- Pre-built domain ontologies, projections, policy bundles, skill
  catalogs, workflows, or HITL routing policies. These are *example
  configurations* under `/examples/`, not library code.
- Distributed multi-writer coordination within a single tenant.
  Single-writer per tenant is the v0 posture; A2A handles cross-tenant.
- Heavyweight workflow engines (Temporal, Step Functions, Airflow).
  Reachable via OrchestrationProtocol.
- Production-grade observability stacks. Logging hooks are exposed; the
  observability *infra* is the deployment's problem.
- Mobile SDK, chat adapter, web UI. Users build these on the HTTP API.
- Human task management inbox / UI. SDK exposes HITL events;
  consumption is the user's choice.
- The Conversational Reporting Layer (§8.10 of the whitepaper).

### Not the SDK's problem at all
- Domain-specific calibrations (`λ_c` values, similarity thresholds,
  skill catalogs, workflow specifications, approval policies).
- Regulatory policy bundles (SR 11-7, FinCEN, HIPAA, etc.).
- Production deployment topology (k8s, service mesh, etc.).
- Harness-internal behavior (planning strategies, sub-agent semantics,
  context-window management inside the loop). CCF governs what crosses
  the seams, not what happens inside the harness.

## 14. First Task for Claude Code

When this `CLAUDE.md` is approved by Dave:

1. Confirm the `origin` remote is `github.com/drcastillo/ccf_code`, the
   repository is private, and the working branch for Phase R is
   `phase-r`, per §2.2.
2. Confirm `./docs/CCF_Whitepaper_1-2.md` is present in the repo (source:
   `/home/parkave/ccf_code/docs/CCF_Whitepaper_1-2.md`).
3. Confirm `/home/parkave/homecams_v2` is accessible (read-only), and
   read `/home/parkave/homecams_v2/CLAUDE.md` once per the §2 discipline.
4. Create the directory skeleton:
   ```
   /docs                  # Phase R, D, F deliverables
   /public                # D-01: the published surface — the only tree mkdocs
                          #   reads; publication is default-deny by existence
   /public/diagrams       # SDK architecture diagrams (Phase D)
   /references            # Whitepaper + reference material
   /src                   # Phase I only (library — fabric, archetypes, ops)
   /runtime               # Phase I only (agent host, harness adapters, MCP, A2A, HTTP, CLI)
   /tests                 # Phase I only
   /examples              # Phase I only (v0 suite per §9)
   ```
5. Initialize empty `docs/SPEC_INVENTORY.md`, `docs/DECISIONS.md`, and
   `docs/DESIGN.md` with placeholder headers.
6. Run **Phase R — Research** by invoking `gsd-phase-researcher` against
   the whitepaper. Output: `docs/SPEC_INVENTORY.md`. Include the
   `homecams-patterns` appendix described in §3.
7. Run `/gsd-review --phase Phase R --all` and triage findings per §3.1.
   Fix blocking findings before proceeding.
8. **Stop and present to Dave for approval** — inventory, review report,
   and triage together, per §3.1. Do not proceed to Phase D until Dave
   approves, the `D-GATE-R` entry is logged, and `phase-r` is merged to
   `main` per §2.2.

After Dave approves the inventory, run `gsd-planner` for Phases D and F.
Phase D must produce **one architecture diagram per pillar** in
`public/diagrams/`, showing how each pillar (§4) maps onto SDK mechanism,
plus the harness-adapter seam diagram and the ArtifactStore seam diagram
(§3).

## 15. What to Do When Things Are Unclear

- **Whitepaper-silent question:** add a `D-IMPL-NN` entry, stop, ask Dave.
- **Whitepaper-ambiguous question:** quote the ambiguous passage in the
  decision log, propose 2–3 readings with consequences, ask Dave.
- **SDK extension question (agents, archetypes, factory, skilling,
  harness adapters, artifact persistence, orchestration, HITL,
  experience, MCP role, A2A):** the relevant section of this document is
  the canonical surface; if it's ambiguous, same discipline — add a
  `D-IMPL-NN` entry and ask.
- **Homecams-conflicts-with-whitepaper situation:** whitepaper wins. Log
  the conflict as informational in the inventory.
- **Homecams-CLAUDE.md-conflicts-with-this-document situation:** this
  document wins, silently. No decision-log entry required (§2).
- **Homecams-encodes-domain-values-the-SDK-might-inherit situation:**
  add it to the `homecams-patterns` appendix with a "do not inherit"
  marker.
- **Temptation-to-inline-a-prompt-or-definition situation:** stop. That
  is the No-Hardcoding Rule (§6.4) firing. Put it in an artifact,
  reference it from the definition, and if the artifact schema is the
  blocker, that is D-IMPL-28 — ask Dave.
- **Harness-specific-behavior question:** if it is inside the loop, it
  is the harness's problem (§13); if it crosses a seam, it is adapter
  scope (§7.3) — and if the adapter contract is ambiguous, D-IMPL-25.
- **Performance-tradeoff question:** Phase I problem. Defer.
- **Domain-specific question:** out of scope. Note as an
  example-configuration concern, not an SDK concern.

## 16. What Success Looks Like for Phase R

The `docs/SPEC_INVENTORY.md` Dave approves at the end of Phase R has:

- One entry per primitive named in §5 through §8 of the whitepaper.
- For each entry: whitepaper section, paraphrased commitment, type
  signature where given, invariants, dependencies on other primitives,
  figure references, and an "open question for design" field if
  applicable.
- A separate section listing every governance decision (D-NN) the
  whitepaper makes that the SDK must honor.
- A separate section listing every load-bearing figure (Fig-CHNN-MM)
  and what mechanism it commits to.
- A separate section listing every named architectural invariant
  (single-writer enforcement, composition-preservation, three
  validation gates, Algorithmic ⇄ Semantic Alternation,
  audit-by-construction for HITL, the No-Hardcoding Rule, zero harness
  imports in core).
- A separate section listing every SDK extension this document commits
  to (Agent Specialization Framework with the archetype/agent
  separation, Six Archetypes, Agent & Task Factory, dual-channel
  specialization incl. skilling, bidirectional MCP, A2A as first-class,
  Harness Adapter surface, ArtifactStore, Orchestration Layer, HITL
  primitives, Experience Layer) and what whitepaper hooks each attaches
  to.
- A **pillar-by-pillar mapping**: for each of the five Common Pillars
  (§4), the inventory entries that contribute to it. This is the
  primary cross-reference Phase D will work against.
- A `homecams-patterns` appendix: patterns observed in
  `/home/parkave/homecams_v2` marked as "candidate pattern" or
  "domain-specific — do not inherit," including its MongoDB persistence
  approach as a triangulation data point for the ArtifactStore design
  (§7.4).
- A separate section listing every open question Phase D will have to
  resolve, including the `D-IMPL-NN` numbers from §12 plus any new
  ones Phase R surfaces.

If Phase R produces a summary instead of an inventory, redo it.

## 17. Interactions with Dave

Keep the dialog with Dave as concise as required to communicate the
response and options. Minimize technical jargon and speak to Dave in
plain English. Avoid verbose explanations filled with technical jargon —
just get to the point.

---

*Last revised: revision 4 — separated agent archetypes (SDK mechanism)
from agents (declared, versioned Control Plane artifacts) and introduced
the dual-channel specialization model (specialization + skilling) with
governance and replay capture (§6.1–§6.2); added the Agent & Task Factory
and the No-Hardcoding Rule as a CI-enforced structural invariant (§6.4);
elevated harness neutrality to a mission-level success condition with the
`HarnessAdapterProtocol` and zero-harness-imports-in-core lint (§1, §7.3);
added MCP-backed artifact persistence via the ArtifactStore Protocol
(§7.4); added the v0 examples suite as the adoption contract, with the
Homecams-on-SDK rebuild deferred to post-v0 validation (§9); normalized
the whitepaper reference to `docs/CCF_Whitepaper_1-2.md`; added
`/home/parkave/homecams_v2/CLAUDE.md` as an additive best-practices
reference; added D-IMPL-24 through D-IMPL-29 and extended the Phase I
gate accordingly; added the Phase Review and Approval Protocol (§3.1)
with per-phase verification criteria, blocking/advisory triage,
`D-GATE-<Phase>` approval logging, and a Phase R review step;
renumbered §9–§15 of revision 3 to §10–§16.*
