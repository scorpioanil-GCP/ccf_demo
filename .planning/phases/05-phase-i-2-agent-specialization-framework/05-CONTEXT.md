# Phase 5: Phase I.2 — Agent Specialization Framework - Context

**Gathered:** 2026-07-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Core Agent Types pillar as SDK mechanism: the unified `Agent`
base plus all six archetypes (Protocol-typed component bundles per
D-IMPL-11/19) in `/src` with zero agent instances, prompts, or domain
values; the Agent & Task Factory constructing agents and tasks
exclusively from D-IMPL-28 YAML definition artifacts; the skill catalog
with registration, discovery, runtime grant/revoke, the two-tier
D-IMPL-29 governance check, and replay capture of every grant/revocation
and the in-force skill-set; all six specialization axes expressible and
versioned in the definition artifact, with any axis change producing a
new agent version visible in replay dimension 4. Requirements AGNT-01..03
per `.planning/ROADMAP.md` Phase 5. Branch `phase-i2`; model mandate
Opus 5 (fallback Opus 4.8) high effort; ends with `/gsd-review` → triage
→ Dave approval → `D-GATE-I.2`.

</domain>

<decisions>
## Implementation Decisions

### Build sequencing & slice
- **D-01:** Vertical slice first, repeating the I.1 pattern: one YAML
  agent definition → factory construction → single-archetype `Agent` →
  runs against the I.1 banking fabric, with replay dimension 4 capturing
  agent identity/version. Subsequent plans widen.
- **D-02:** The slice fixture agent declares the **AnalyticsInsights**
  archetype in the banking scenario — the deliberate precursor of
  `examples/01-agent-basics`, exactly as the I.1 slice preceded
  example 00. Same realism bar as I.1's D-02 ("would this slice catch a
  broken invariant?").
- **D-03:** "The slice agent runs" via a **test-double harness living in
  `/tests` fixtures only** — a minimal deterministic driver for the
  Agent's fabric seams (consume a Context Product, invoke a bound skill,
  emit output through effect capture). It never lives in `/src` or
  `/runtime` and never ships: CLAUDE.md §7.3's no-loop commitment holds.
- **D-04:** Widening waves organized **by pillar concern**, mirroring
  I.1's subsystem split: (a) all six archetypes + D-IMPL-19 composition
  rules, (b) factory hardening + no-bypass + six axes complete,
  (c) skill catalog + governance + replay capture, (d) gate wave.

### Agent versioning mechanics
- **D-05:** Axis-change ⇒ new-version is enforced by **hash-verified
  bump**: authors bump `artifact_version` explicitly (semver intent stays
  human); the Control Plane refuses registration when content changed
  without a version bump **or** the version changed without content
  change — drift is mechanically detectable via the D-IMPL-26 content
  hash. Version discipline is enforced, never trusted.
- **D-06:** Replay dimension 4 records, per decision: the agent
  definition's **content hash** (canonical identity), its **versioned URI
  as annotation** (per D-IMPL-26's replay rule), the **composed archetype
  list** (D-IMPL-19), and the **in-force skill grant set by
  grant-artifact hash**. Everything resolvable to exact bytes.
- **D-07:** The in-force skill-set has its own identity: a
  **deterministic grant-set hash** over the ordered set of active
  grant-artifact hashes. No epoch counter; agent version stays stable
  across grants — the channel-1/channel-2 separation preserved
  mechanically.

### Skill catalog scope in I.2
- **D-08:** The catalog-entry schema covers **all four D-IMPL-12 skill
  types from day one** (no schema_version bump needed in I.3), but only
  **local-callable and tool** skills get working reference dispatch and
  fixtures in I.2. MCP/A2A entries validate and register; dispatching
  them raises a **typed NotYetBound** error until I.3 binds the
  transports.
- **D-09:** Tier-2 governance (D-IMPL-29) ships as the **full grant
  state machine now** — requested → pending-approval → effective/refused
  — behind a typed **ApprovalSink Protocol**. I.2 tests approve via a
  test double; I.4's ApprovalGate becomes the real sink with zero
  state-machine change. Tier 1 (automatic policy-compatibility check) is
  always on and non-waivable.
- **D-10:** The deferred CINV-04 `skill-set-capture` check flips from
  skip to **active in the same plan/wave that lands grant/revoke +
  replay capture** — that wave is not done until the formerly-skipped
  check passes as an active behavioral check (suite goes 3 skips →
  2 skips within I.2).

### Task Factory scope
- **D-11:** I.2 ships the **task definition artifact schema + factory
  construction/validation only — no execution engine**. No-bypass and
  No-Hardcoding enforcement cover Task artifacts from day one; I.4's
  Workflow primitive consumes the already-stable Task artifact format.
- **D-12:** Factory no-bypass enforcement is **CINV-01 lint only** —
  the existing AST factory-bypass check is the mechanism of record.
  `Agent` stays a normal public class; **no runtime construction token**
  (deliberate divergence from I.1's capability-token pattern for
  delivery). Dave's explicit choice over the recommended lint+token
  option.
- **D-13:** Prompt-artifact machinery (axis 6): **full
  construction-time validation, no render-to-LLM**. I.2 ships prompt
  artifact loading, Jinja2 template-parameter declaration validation at
  construction (per D-IMPL-28), and versioned-URI resolution. A bad
  instruction binding fails factory construction. Rendering into
  harness-ready strings is I.3 adapter work; no LLM invocation in I.2.

### Claude's Discretion
- Banking fixture specifics for the agent/task/skill/prompt artifacts —
  bounded by the D-02 realism bar; all values in fixture artifacts,
  never `/src` (No-Hardcoding applies to fixtures' code too).
- Exact plan/wave counts within the D-04 organization; internal module
  layout under `/src/ccf/agents` (or equivalent) per DESIGN.md.
- Shape of the archetype Protocol bundles' obligation declarations,
  within the D-IMPL-19 conflict rules (dedupe identical, declaration-
  order for defaults with factory warning, error on hard contradiction).
- NotYetBound error taxonomy placement and the grant-set hash's
  canonical serialization details (use `ccf.contracts.canonical`
  machinery from I.1).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project governance
- `CLAUDE.md` — canonical (rev 4): §6 Agent Specialization Framework in
  full (§6.1 archetype/agent separation, §6.2 two channels, §6.3 six
  archetypes, §6.4 Factory + No-Hardcoding Rule, §6.5 harness
  neutrality); §7.3 no-loop commitment (bounds the test-double harness);
  §11 working principles.
- `docs/CCF_Whitepaper_1-2.md` — canonical spec; Chapter 3 (agents as
  fabric consumers), §7.10 replay dimensions. Cite sections in public
  docstrings; SDK-extension surfaces cite CLAUDE.md §6 and say so.

### Design & decisions
- `docs/DECISIONS.md` — esp. D-IMPL-11 (single Agent class + Protocol
  archetype bundles), D-IMPL-12 (four skill types, catalog as Control
  Plane artifacts), D-IMPL-19 (ordered composition + conflict rules),
  D-IMPL-26 (hybrid addressing; replay stores hash, URI as annotation),
  D-IMPL-28 (YAML + Pydantic v2 + Jinja2 + two-field versioning),
  D-IMPL-29 (two-tier skilling governance).
- `docs/DESIGN.md` — Core Agent Types pillar section + component
  boundaries; Invariant Preservation chapter.
- `docs/FEASIBILITY.md` — per-component verdicts for the agent surface;
  per-invariant test-strategy table (the D-17 gate-checklist pattern
  carries over from I.1).
- `docs/SPEC_INVENTORY.md` — INV-CH7-84 (replay dimension 4), INV-CH8-22
  (archetypes as functional categories).

### Planning
- `.planning/ROADMAP.md` — Phase 5 goal, AGNT-01..03, four success
  criteria.
- `.planning/REQUIREMENTS.md` — AGNT requirement definitions.
- `.planning/phases/04-phase-i-1-fabric-core/04-CONTEXT.md` — carried
  decisions (banking fixtures, TDD-on-invariants, conformance-suite
  pattern, per-invariant gate bar).

### Phase I.1 code to build on
- `src/ccf/contracts/` — `CCFContract` (`extra=forbid`) base + canonical
  serialization (grant-set hash must use it).
- `src/ccf/controlplane/` — versioned registry, audit log, artifact
  registration (hash-verified bump lands here).
- `src/ccf/artifacts/` — ArtifactStore Protocol + file store (definition
  artifacts persist through it).
- `src/ccf/replay/` — five-dimension record; dimension 4 extension
  point.
- `tools/lints/` — CINV-01 no-hardcoding + factory-bypass checker
  (D-12's mechanism of record); CINV-04 registry in
  `tests/invariants/test_replay_by_construction.py` (skill-set-capture
  skip to activate per D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Full I.1 fabric: graph (SQLite/Postgres), operators, projection,
  products + gates, λ_c/D_c, replay engine, Control Plane registry,
  file ArtifactStore, banking fixtures under `tests/fixtures/banking/`.
- `ccf.contracts.canonical` — field-by-field canonical serializer
  (deterministic hashing substrate for D-05/D-06/D-07).
- Conformance-suite pattern (`tests/conformance/`) — reuse for any new
  Protocol (ApprovalSink, skill dispatch).
- CINV lint framework (`tools/lints/` + versioned allowlist) — extend
  factory-bypass rules rather than building new machinery.

### Established Patterns
- Slice-first waves; TDD on contracts/invariants; typed refusals as
  returned values, exceptions for broken deployments; per-invariant gate
  checklist (D-17); phase branch `phase-i2`, merge at `D-GATE-I.2`.
- CINV-04 deferral discipline: checks skip with activating-phase reason
  strings, never silently absent.

### Integration Points
- New: `/src/ccf/agents/` (or per DESIGN.md) — Agent class, archetype
  bundles, factory; skill catalog under Control Plane; task artifact
  schema; replay dimension-4 extension.
- Extended: `src/ccf/controlplane/registry.py` (hash-verified bump,
  grant state machine, audit actions), `src/ccf/replay/record.py`
  (dimension 4 fields), `tools/lints/no_hardcoding.py` (factory-bypass
  coverage for Agent/Task), CINV-04 registry (skill-set-capture
  activation).

</code_context>

<specifics>
## Specific Ideas

- The I.2 slice fixture is the deliberate precursor of
  `examples/01-agent-basics`, as the I.1 slice was for example 00 —
  banking AnalyticsInsights agent, formalized in Phase 8.
- D-12 is a deliberate divergence: Dave chose lint-only no-bypass over
  the recommended lint + construction-token, accepting that dynamic
  construction is not runtime-guarded. Planner should not re-add a
  token.

</specifics>

<deferred>
## Deferred Ideas

- MCP/A2A skill dispatch binding → Phase 6 (I.3), per D-08.
- Prompt rendering into harness context + LLM invocation → Phase 6
  (I.3) adapter seams, per D-13.
- Real ApprovalGate sink for tier-2 grants → Phase 7 (I.4), per D-09.
- Task execution semantics (Workflow primitive) → Phase 7 (I.4), per
  D-11.

</deferred>

---

*Phase: 5 - Phase I.2 — Agent Specialization Framework*
*Context gathered: 2026-07-25*
