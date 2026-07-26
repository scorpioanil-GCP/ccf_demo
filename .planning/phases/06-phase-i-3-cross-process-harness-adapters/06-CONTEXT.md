# Phase 6: Phase I.3 — Cross-Process & Harness Adapters - Context

**Gathered:** 2026-07-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Context Products travel governed across process and harness boundaries.
Three sub-domains plus one inherited deliverable:

1. **Bidirectional MCP (XPRC-01)** — client ingress at L1/L4/L5/Experience
   normalizing to the L1 envelope; server egress at L6 exposing Context
   Products as MCP Resources; the ArtifactStore MCP role kept in a module
   distinct from egress (§7.1).
2. **A2A federation (XPRC-02)** — typed Context Products across processes
   behind the `WireProtocol` abstraction (D-IMPL-14), with identity/signing
   (D-IMPL-15) and inbound products admitted to L3 only through L2 after
   Control Plane policy-binding verification (D-IMPL-16), lineage extended
   by set-union.
3. **Harness adapters (XPRC-03)** — `HarnessAdapterProtocol` plus reference
   adapters for all three D-IMPL-24 harnesses (Google ADK, Claude Agent SDK,
   LangGraph), binding the seams per D-IMPL-25, with the
   zero-harness-imports-in-`/src` lint staying green.
4. **Inherited (D-12 amendment)** — the MCP-backed ArtifactStore reference
   implementation, passing the same shared conformance suite as the
   file-backed dev impl with no other deployment change required to swap.

Success criteria per `.planning/ROADMAP.md` Phase 6, including criterion 4:
single-writer demonstrably holds across the A2A boundary, the adapter
boundary, and the ArtifactStore. Branch `phase-i3`; model mandate Opus 5
(fallback Opus 4.8) high effort; ends with `/gsd-review` → triage → Dave
approval → `D-GATE-I.3`.

**Not in this phase:** workflow/orchestration execution, HITL primitives,
and the Experience Layer front doors (all Phase 7 / I.4); the polished
`/examples` suite (Phase 8 / I.5).

</domain>

<decisions>
## Implementation Decisions

### Build sequencing & slice

- **D-01:** **Vertical slice first**, continuing the I.1 and I.2 pattern.
  The slice is **MCP egress at L6**: serve one existing banking Context
  Product as an MCP Resource, consumed by an MCP client in a test. Chosen
  as the smallest honest cross-process proof — it exercises the L6 delivery
  contract that already exists, requires no harness and no identity/signing,
  and produces the client library plus server scaffolding that A2A and the
  ArtifactStore both reuse.
- **D-02:** Waves widen **transport → trust → harness**:
  (a) MCP client ingress at L1/L4/L5 + the MCP-backed ArtifactStore;
  (b) A2A wire + identity/signing + Control Plane admission;
  (c) `HarnessAdapterProtocol` + the three reference adapters;
  (d) gate wave.
  Each wave depends only on what precedes it, and the three external harness
  SDKs — the phase's largest unknown — land last, when the fabric-side seams
  are already proven.
- **D-03:** **One shared MCP client library** (per D-IMPL-13) plus **three
  role modules**: L6 egress, ArtifactStore, and ingress normalization. §7.1
  requires the ArtifactStore role live in a module distinct from egress
  (Phase 6 criterion 1 states this explicitly); separate modules make the
  differing trust postures structural rather than conventional.
- **D-04:** **Protocols in `/src`, implementations in `/runtime`.**
  `HarnessAdapterProtocol`, `WireProtocol`, and `IdentityProvider` are
  Protocol declarations in `/src/ccf/` (harness-free and lintable); every
  concrete adapter and transport lives under
  `/runtime/ccf_runtime/adapters/<harness>/` and `/runtime/ccf_runtime/a2a/`,
  matching CLAUDE.md §7.3 and the existing `runtime/ccf_runtime/cdc/`
  precedent. `/src` skill dispatch types against the Protocols, so the
  declarations cannot move to `/runtime` without inverting the dependency.
- **D-05:** **Remote skill dispatch ships with its transport wave** — `mcp`
  dispatch in the MCP wave, `a2a` dispatch in the A2A wave, each arriving
  with its governance and audit capture. The catalog already declares both
  skill types with typed bindings (`catalog.py:63-131`) while `dispatch.py`
  executes only `local_callable`; closing that gap per-wave keeps every wave
  end-to-end and means the harness skill-exposure seam sees all four skill
  types working.
- **D-06:** **Test fixtures in I.3, polished examples in I.5.** Each wave
  builds its proof as a test fixture (cross-process exchange, adapter
  portability, ArtifactStore swap); the `/examples` directories with READMEs
  land in Phase 8. Follows the I.1→example-00 and I.2→example-01 precursor
  precedent, and avoids a domain/style mismatch with the other five examples.
- **D-07:** Within the harness wave, **one adapter deep, then two against
  the suite**: build the Claude Agent SDK adapter end-to-end to discover what
  the Protocol actually needs, harden `HarnessAdapterProtocol` and the
  conformance suite against it, then bring ADK and LangGraph up against that
  fixed suite. Matches the D-10 LangGraph intra-I.3 staging recommendation
  carried from Phase F. Ordering only — D-IMPL-24 made all three equally v0.

### Harness dependency & test posture

- **D-08:** **Composable optional extras, never core dependencies.** Three
  per-harness extras (`adk`, `claude-agent`, `langgraph`), an aggregate
  `harnesses` extra installing all three in one command, and `dev` including
  `harnesses` so CI and contributors get everything from
  `pip install -e .[dev]`. Follows the `chroma` precedent ("NEVER a core
  dependency"), but for a stronger reason than weight: harness neutrality is
  an install-time property as well as an import-time one. A LangGraph
  deployment must not be made to install Google's SDK. **Requirement: one
  documented command installs and runs all three.**
- **D-09:** **One shared conformance suite, run against the real SDKs.** A
  factory-parametrized `HarnessAdapterProtocol` conformance suite — the
  pattern `tests/conformance/test_approval_sink.py` already establishes —
  executed against all three real harnesses in CI, **with no LLM calls**.
  Adapters are seam bindings, so the suite drives context injection, skill
  exposure, and effect capture without the harness ever reaching a model.
  Doubles were rejected deliberately: a double written to the Protocol we
  designed can pass while the real SDK's surface disagrees, which is exactly
  the failure this phase exists to prevent (§7.3 — portability demonstrated,
  not asserted).
- **D-10:** **`effects: unsupported` must be declared *and* proven inert.**
  An adapter claiming it declares so in typed metadata *and* the suite drives
  an effect-producing path asserting nothing reached the graph and no write
  handle was obtainable. This is what makes D-IMPL-25's "conformance-verified
  absence" different from an opt-out.

### A2A wire and trust

- **D-11:** **Typed-HTTP fallback first, then LF A2A.** Build the fallback
  to prove the `WireProtocol` abstraction and get Context Products crossing a
  real process boundary with admission verification working, then implement
  LF A2A against that same abstraction. **This is sequencing within
  D-IMPL-14, not a revision of it** — LF A2A remains the ruled v0 default
  (same framing as the D-10 staging note recorded at `D-GATE-F`). Rationale:
  LF A2A is an emergent 2026 standard, and §7.2 states the Contract is the
  stable layer while the wire is replaceable, so building in that order means
  a disappointing LF A2A surface does not stall XPRC-02, admission
  verification, identity/signing, and the example-04 fixture behind it.
- **D-12:** **Admission is a Control Plane gate ahead of L2.** Every inbound
  A2A Context Product passes a typed admission gate before it can reach L2;
  since only L2 writes to L3, single-writer carries the guarantee
  structurally. Wire implementations hand products to the gate and never hold
  a path to L2. Placing the check inside each `WireProtocol` implementation
  was rejected — it duplicates the rule per transport and lets a future
  transport omit it, the same drift IN-01 found in the pinned-resolution
  logic.
- **D-13:** **Real detached-JWS signing, dev-grade key custody.** Genuine
  signing and verification of emitted and inbound products, with a
  file-backed dev key source behind the `IdentityProvider` Protocol.
  Signature verification is load-bearing for admission, so a stubbed signer
  would make the admission gate untestable; PKI/HSM custody is deployment
  infrastructure and stays out (§13). Full mTLS channel security is
  deployment topology, not v0 SDK scope.
- **D-14:** **Lineage set-union pinned by a Hypothesis property.** Assert the
  law over generated lineage pairs — producer entries always survive,
  consumer entries always survive, order never matters, re-admission is
  idempotent — rather than fixture round-trips that pin chosen examples.
  Extends existing machinery: the I.1 suite already runs Hypothesis, and
  lineage strict equality is an existing validation gate. Replacement instead
  of union must fail loudly.

### Cross-process test topology

- **D-15:** **Real subprocesses over loopback.** Spawn genuine producer and
  consumer processes exchanging over real HTTP on loopback. The only topology
  where "two processes" is literally true — an in-process double shares a
  Python heap and therefore cannot prove the consumer lacks a write handle to
  the producer's graph, which is exactly what criterion 4 asserts.
- **D-16:** **Ephemeral ports plus a readiness handshake.** Bind port 0 so
  the OS assigns a free port, have the child report its address, and gate on
  an explicit readiness probe — **never a sleep** — with a pytest fixture
  guaranteeing teardown on failure. Removes the three classic flake sources:
  port collisions, racing a not-yet-listening server, and orphaned processes
  poisoning later tests.
- **D-17:** **One shared cross-process fixture, built during the slice.** The
  same harness serves MCP egress, the MCP ArtifactStore, and A2A. The slice
  therefore delivers infrastructure the whole phase depends on, and the
  ephemeral-port/readiness discipline is written once. Example 07's
  ArtifactStore swap is a deployment-level claim and is weaker if the store
  never leaves the process.
- **D-18:** **Replay-record equivalence for portability = equal on governed
  fields, harness-specific fields isolated.** Assert exact equality on
  everything CCF governs — Context Product consumed, grant-set hash, agent
  definition hash, policy bundle version, lineage — while harness-attributable
  fields (model version, trace shape, token counts) are confined to a named
  sub-structure excluded from comparison. Full byte equality across three
  different SDKs would either fail always or force those fields out of the
  record entirely.

### Inherited constraints from the Phase I.2 retrospective review

Source: `.planning/phases/05-phase-i-2-agent-specialization-framework/05-REVIEWS.md`
(gemini, codex, cursor, ollama — run after `D-GATE-I.2`, so all findings are
advisory to I.2 and **binding as planning constraints here**). The reviewers'
shared theme: several I.2 properties documented as "by construction" are in fact
enforced by lint scope, paired-call discipline, or docstring convention. I.3
removes the two conditions that made that tolerable — in-repo artifacts and a
single process.

- **D-19 (from A1, unanimous HIGH):** the `local_callable` dispatch control is a
  **blocking checklist item in the A2A/MCP wave**, not a follow-up. No wave may
  admit a non-fixture catalog source until one of — registered-callable table,
  Control-Plane admission allowlist, or provenance/signature check — is selected
  and implemented. Ollama's concrete case: a third-party catalog entry naming
  `os.system`. This upgrades the §5 handoff note from "carry forward" to "gate".
- **D-20 (from A2, 3/4 + verifier ADV-02):** `ControlPlaneStateStore.put` neither
  audits nor requires a token; the audit pairing in `grants.py` is convention.
  **I.3 must not add a second consumer of that seam without an audit-bearing write
  path**, because I.4's workflow suspend/resume multiplies the call sites and one
  missed pair is silent state with no audit record (INV-CH7-71). If a wave here
  needs the state seam, closing this comes first.
- **D-21 (from A3, 4/4):** **scope invariant claims to their actual enforcement.**
  Write "lint-enforced in shipped surfaces" or "audited by the current
  implementation" rather than "no path" / "by construction", unless the state is
  genuinely unrepresentable. Applies to `HarnessAdapterProtocol` seam claims and
  the D-10 `effects: unsupported` verification wording especially — a
  conformance-verified absence is exactly the kind of claim that degrades into
  convention.
- **D-22 (from A6, codex + verifier ADV-03):** `test_consumption_discipline.py`
  is a **direct-import** check with no transitive closure, while the AGNT-01
  claim it encodes is "no path from Agent to L1–L5". Adapter modules enter that
  import graph this phase. Any widening of `ALLOWED_CCF_PREFIXES` requires a
  transitive-closure argument, as the I.2 `ccf.controlplane.resolution` widening
  received — never a precedent argument.
- **D-23 (from Cursor's divergent finding):** CR-01 was a **planning** defect, not
  an implementation bug — plan 05-06's must-haves specified
  `content_hash(frozenset(...))` with no per-agent filter, so no two-agent test
  was ever required. Constraint for this phase: **any set-identity, admission
  decision, or replay claim computed over shared Control Plane state must carry a
  multi-principal case in its plan's `must_haves`** — two tenants, two agents, two
  peers — not just the happy single-principal path. Directly relevant to A2A
  admission (D-12) and lineage set-union (D-14).
- **Process (from Cursor):** draft gate-checklist rows from *tests that fail under
  the broken implementation*, not from plan intent. I.2's initial gate prose
  overclaimed and had to be rewritten in 05-10.

### Claude's Discretion

- **Harness skip mechanism** (D-09 corollary): how a conformance leg behaves
  when a harness SDK is absent is planning's call, under one constraint — a
  skipped harness leg must always be **visible and self-explaining**, naming
  which harness and which extra enables it. The I.1 precedent is the three
  CINV-04 deferral skips, each naming its activating phase. CI installs
  `[dev]`, so all three legs run there regardless.
- Module tree details below the D-03/D-04 boundaries.
- Exact extra names and composition mechanics, subject to D-08's one-command
  requirement.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Governing specification
- `CLAUDE.md` §7.1 — bidirectional MCP: the five edges and their distinct
  trust postures; the artifact-persistence role as separate from egress.
- `CLAUDE.md` §7.2 — A2A as first-class in v0: trust-boundary verification,
  identity/attestation, lineage continuity by set-union, `WireProtocol`
  posture ("the Contract is the stable layer; the wire is replaceable").
- `CLAUDE.md` §7.3 — harness neutrality: zero harness imports in core,
  `HarnessAdapterProtocol`'s four seams, "portability is demonstrated, not
  asserted".
- `CLAUDE.md` §7.4 — ArtifactStore: the MCP-backed reference impl, the
  single-writer constraint, replay determinism, trust posture.
- `CLAUDE.md` §10 — L1–L6 layering and the single-writer invariant across
  the A2A, adapter, and ArtifactStore boundaries.
- `CLAUDE.md` §11 — working principles (Protocols over inheritance,
  reference impls alongside Protocols, typed contracts at every boundary).
- `CLAUDE.md` §13 — scope and non-scope; what is explicitly not the SDK's
  problem (harness-internal behavior, deployment topology).
- `docs/CCF_Whitepaper_1-2.md` §8.3 — Integration Patterns 3 (MCP) and
  4 (A2A federation), including the trust-boundary resolution this phase
  implements.

### Rulings that constrain this phase
- `docs/DECISIONS.md` **D-IMPL-13** — five MCP edges via one client lib,
  egress server, separate ArtifactStore contract.
- `docs/DECISIONS.md` **D-IMPL-14** — LF A2A default `WireProtocol`,
  typed-HTTP fallback. (See D-11 above: build order differs; the ruling does
  not.)
- `docs/DECISIONS.md` **D-IMPL-15** — `IdentityProvider` Protocol, mTLS +
  detached JWS.
- `docs/DECISIONS.md` **D-IMPL-16** — verify every inbound A2A product; no
  fast path for high-trust peers.
- `docs/DECISIONS.md` **D-IMPL-24** — Dave's own ruling: **all three**
  harnesses ship v0 reference adapters (ADK + Claude Agent SDK + LangGraph),
  with three CI legs and three example-03 variants as accepted consequences.
- `docs/DECISIONS.md` **D-IMPL-25** — three seams mandatory;
  `effects: unsupported` is a conformance-verified absence.
- `docs/DECISIONS.md` **D-IMPL-17** — the LangGraph two-seam disambiguation:
  the LangGraph *harness adapter* binds only the §7.3 agent-loop seams;
  LangGraph *as an orchestrator* is a distinct optional
  `OrchestrationProtocol` integration (Phase 7). **One tool, two seams,
  never conflated.**
- `docs/DECISIONS.md` **D-IMPL-26** — hybrid content-hash + versioned-URI
  addressing; governs the ArtifactStore MCP resource contract.
- `docs/DECISIONS.md` **D-IMPL-27** — substrate split by mutability.
- `docs/DECISIONS.md` **D-GATE-F** — the D-10 note establishing that
  intra-phase staging is sequencing, not a revision of a ruling.

### Phase inputs and precedent
- `.planning/ROADMAP.md` §"Phase 6" — the five success criteria, including
  criterion 5 (MCP ArtifactStore, inherited via the D-12 amendment).
- `.planning/REQUIREMENTS.md` — XPRC-01, XPRC-02, XPRC-03.
- `docs/DESIGN.md` — the harness-adapter seam diagram and the ArtifactStore
  seam diagram (`docs/diagrams/`), plus the invariant-preservation arguments
  this phase must not break.
- `docs/PHASE_I2_GATE.md` §5 — the I.2→I.3 handoff, including the **IN-06
  threat-model item**: `local_callable` dispatch is artifact-driven code
  execution whose T-05-18 trust posture is a *precondition on the input*
  that **I.3 invalidates**, because MCP/A2A artifact sources make
  `callable_ref` remote-influenced. Three candidate controls are named
  there. **This is required reading for the A2A wave.**
- `.planning/phases/05-phase-i-2-agent-specialization-framework/05-CONTEXT.md`
  — the slice-first pattern (D-01) and the test-double-harness boundary
  (D-03: harness doubles live in `/tests` only, never `/src` or `/runtime`).
- `.planning/phases/05-phase-i-2-agent-specialization-framework/05-REVIEWS.md`
  — **required reading.** Four-reviewer retrospective on I.2, run after the gate.
  Its "Agreed Concerns" and "Disposition" sections are the source of D-19..D-23
  above. Read the Disposition table for the routing of each finding into this
  phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ccf/artifacts/protocol.py` + `file_store.py` — `ArtifactStoreProtocol`
  and its file-backed reference impl. The MCP-backed store must pass the
  **same** conformance suite; `file_store.py` is the behavioral target.
- `src/ccf/skills/catalog.py:63-131` — `SkillType` already includes `mcp` and
  `a2a` with typed `McpBinding` / `A2ABinding` descriptors. The declaration
  side exists; only dispatch is missing.
- `tests/conformance/test_approval_sink.py` — the factory-parametrized
  conformance-suite pattern D-09 reuses for `HarnessAdapterProtocol`.
- `runtime/ccf_runtime/cdc/` — the only existing `/runtime` module; the
  precedent for adapter placement under D-04.
- Hypothesis is already wired (73 properties on the ci profile in I.1) —
  D-14's set-union property extends it rather than introducing a tool.
- `src/ccf/controlplane/state.py` — the `ControlPlaneStateStore` seam added
  in I.2. Not needed by I.3, but it is the pattern for a pluggable
  Control-Plane-adjacent substrate.

### Established Patterns
- **Refusals are typed values; misuse is an exception.** Gate refusals
  (`GateRefusal`, `GrantRefusal`, `RegistrationRefusal`) are returned and
  inspected, never raised. The A2A admission gate (D-12) should follow this.
- **Constructor injection everywhere** — registry, catalog, audit log, sink,
  clock are all injected; no service holds a wall clock or keys of its own.
- **Audit refusals with `resolved=False`** — the audit plane records what it
  turned away (T-05-16). Inbound A2A refusals must land in the journal.
- **CINV-01 mechanism-not-values** and the No-Hardcoding Rule apply to
  `/runtime` and `/examples`, not just `/src`.

### Integration Points
- **L6 → MCP egress**: the existing Context Product delivery contract is what
  the slice serves; no new product machinery.
- **L1 envelope ← MCP ingress**: MCP client responses normalize into
  `SignalEnvelope` (the I.1 superset per D-IMPL-33).
- **L2 ← A2A admission**: the only path inbound products may take to L3.
- **`Agent` ← harness adapters**: `src/ccf/agents/agent.py:14-15` states the
  `Agent` is "the fabric-side representation a harness adapter binds";
  `prompts.py:19` explicitly defers harness-ready rendering to I.3.
- **Skill dispatch → transports**: `src/ccf/skills/dispatch.py` gains `mcp`
  and `a2a` execution paths per D-05.

</code_context>

<specifics>
## Specific Ideas

- **"Easy to install and run all three harnesses"** — stated directly during
  discussion and elevated to a requirement in D-08. One documented command
  must install and exercise all three. This drove the composable-extras
  shape rather than a single dev bundle.
- **No sleeps for readiness** (D-16) — an explicit prohibition, not a
  preference.
- **No LLM calls in the adapter conformance suite** (D-09) — adapters are
  seam bindings; the loop is the harness's business (§13).

</specifics>

<deferred>
## Deferred Ideas

- **Gray areas raised but not explored** (available to research if it finds
  them load-bearing): MCP client ingress normalization detail — how
  source-specific MCP responses become `SignalEnvelope`s; the ArtifactStore
  MCP resource contract shape under D-IMPL-26 addressing; A2A trust-policy
  artifact declaration in the Control Plane. None are blocked; they were
  judged researcher territory rather than user decisions.
- **Full mTLS channel security** — D-IMPL-15 names it, but D-13 scopes v0 to
  detached JWS. mTLS is deployment topology (§13); revisit if a deployment
  requires it.
- **PKI/HSM key custody** — behind the `IdentityProvider` Protocol from day
  one, so a real custody backend is an implementation, not a redesign.
- **LangGraph as an orchestrator** (as opposed to as a harness) — explicitly
  a distinct `OrchestrationProtocol` integration under D-IMPL-17, and
  Phase 7 (I.4) scope. Do not conflate with the LangGraph adapter built here.

</deferred>

---

*Phase: 6-Phase I.3 — Cross-Process & Harness Adapters*
*Context gathered: 2026-07-26*
