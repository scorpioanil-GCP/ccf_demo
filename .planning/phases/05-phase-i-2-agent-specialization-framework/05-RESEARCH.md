# Phase 5: Phase I.2 — Agent Specialization Framework - Research

**Researched:** 2026-07-26
**Domain:** Internal SDK extension — Agent/archetype/factory/skilling mechanism on the existing I.1 fabric (Python 3.12, Pydantic v2, YAML, Jinja2)
**Confidence:** HIGH (dominated by codebase inspection and Dave-resolved D-IMPL rulings, not external discovery)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Build sequencing & slice**
- **D-01:** Vertical slice first, repeating the I.1 pattern: one YAML agent definition → factory construction → single-archetype `Agent` → runs against the I.1 banking fabric, with replay dimension 4 capturing agent identity/version. Subsequent plans widen.
- **D-02:** The slice fixture agent declares the **AnalyticsInsights** archetype in the banking scenario — the deliberate precursor of `examples/01-agent-basics`, exactly as the I.1 slice preceded example 00. Same realism bar as I.1's D-02 ("would this slice catch a broken invariant?").
- **D-03:** "The slice agent runs" via a **test-double harness living in `/tests` fixtures only** — a minimal deterministic driver for the Agent's fabric seams (consume a Context Product, invoke a bound skill, emit output through effect capture). It never lives in `/src` or `/runtime` and never ships: CLAUDE.md §7.3's no-loop commitment holds.
- **D-04:** Widening waves organized **by pillar concern**, mirroring I.1's subsystem split: (a) all six archetypes + D-IMPL-19 composition rules, (b) factory hardening + no-bypass + six axes complete, (c) skill catalog + governance + replay capture, (d) gate wave.

**Agent versioning mechanics**
- **D-05:** Axis-change ⇒ new-version is enforced by **hash-verified bump**: authors bump `artifact_version` explicitly (semver intent stays human); the Control Plane refuses registration when content changed without a version bump **or** the version changed without content change — drift is mechanically detectable via the D-IMPL-26 content hash. Version discipline is enforced, never trusted.
- **D-06:** Replay dimension 4 records, per decision: the agent definition's **content hash** (canonical identity), its **versioned URI as annotation** (per D-IMPL-26's replay rule), the **composed archetype list** (D-IMPL-19), and the **in-force skill grant set by grant-artifact hash**. Everything resolvable to exact bytes.
- **D-07:** The in-force skill-set has its own identity: a **deterministic grant-set hash** over the ordered set of active grant-artifact hashes. No epoch counter; agent version stays stable across grants — the channel-1/channel-2 separation preserved mechanically.

**Skill catalog scope in I.2**
- **D-08:** The catalog-entry schema covers **all four D-IMPL-12 skill types from day one** (no schema_version bump needed in I.3), but only **local-callable and tool** skills get working reference dispatch and fixtures in I.2. MCP/A2A entries validate and register; dispatching them raises a **typed NotYetBound** error until I.3 binds the transports.
- **D-09:** Tier-2 governance (D-IMPL-29) ships as the **full grant state machine now** — requested → pending-approval → effective/refused — behind a typed **ApprovalSink Protocol**. I.2 tests approve via a test double; I.4's ApprovalGate becomes the real sink with zero state-machine change. Tier 1 (automatic policy-compatibility check) is always on and non-waivable.
- **D-10:** The deferred CINV-04 `skill-set-capture` check flips from skip to **active in the same plan/wave that lands grant/revoke + replay capture** — that wave is not done until the formerly-skipped check passes as an active behavioral check (suite goes 3 skips → 2 skips within I.2).

**Task Factory scope**
- **D-11:** I.2 ships the **task definition artifact schema + factory construction/validation only — no execution engine**. No-bypass and No-Hardcoding enforcement cover Task artifacts from day one; I.4's Workflow primitive consumes the already-stable Task artifact format.
- **D-12:** Factory no-bypass enforcement is **CINV-01 lint only** — the existing AST factory-bypass check is the mechanism of record. `Agent` stays a normal public class; **no runtime construction token** (deliberate divergence from I.1's capability-token pattern for delivery). Dave's explicit choice over the recommended lint+token option. Planner must NOT re-add a token.
- **D-13:** Prompt-artifact machinery (axis 6): **full construction-time validation, no render-to-LLM**. I.2 ships prompt artifact loading, Jinja2 template-parameter declaration validation at construction (per D-IMPL-28), and versioned-URI resolution. A bad instruction binding fails factory construction. Rendering into harness-ready strings is I.3 adapter work; no LLM invocation in I.2.

### Claude's Discretion
- Banking fixture specifics for the agent/task/skill/prompt artifacts — bounded by the D-02 realism bar; all values in fixture artifacts, never `/src` (No-Hardcoding applies to fixtures' code too).
- Exact plan/wave counts within the D-04 organization; internal module layout under `/src/ccf/agents` (or equivalent) per DESIGN.md.
- Shape of the archetype Protocol bundles' obligation declarations, within the D-IMPL-19 conflict rules (dedupe identical, declaration-order for defaults with factory warning, error on hard contradiction).
- NotYetBound error taxonomy placement and the grant-set hash's canonical serialization details (use `ccf.contracts.canonical` machinery from I.1).

### Deferred Ideas (OUT OF SCOPE)
- MCP/A2A skill dispatch binding → Phase 6 (I.3), per D-08.
- Prompt rendering into harness context + LLM invocation → Phase 6 (I.3) adapter seams, per D-13.
- Real ApprovalGate sink for tier-2 grants → Phase 7 (I.4), per D-09.
- Task execution semantics (Workflow primitive) → Phase 7 (I.4), per D-11.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGNT-01 | Unified Agent base + six archetypes (Workflow/Task, DocumentIntelligence, AnalyticsInsights, MonitoringSurveillance, ContentGeneration, ContextAssembly) as SDK mechanism (§6.1, §6.3) | DESIGN.md §3.1–§3.4 gives complete per-archetype contracts (responsibility/invariants/seams table, verbatim above under "Archetype contracts"); D-IMPL-11/19 rulings fix the shape: single concrete final `Agent` + `ArchetypeComponent` Protocol bundles, ordered composition with three explicit conflict rules |
| AGNT-02 | Agent & Task Factory + D-IMPL-28 definition-artifact schema; no factory bypass (§6.4) | D-IMPL-28 ruling (YAML + Pydantic v2 `extra=forbid` + exported JSON Schema + Jinja2 versioned-URI prompts + two-field versioning); existing typed-registration machinery in `src/ccf/controlplane/artifacts.py` (`ArtifactClass`, `load_artifact`, `parse_artifact`) is the pattern to extend; CINV-01c factory-bypass lint already scaffolded in `tools/lints/no_hardcoding.py` (`FACTORY_ONLY_NAMES = {"Agent","Task"}`, `FACTORY_PATH_MARKER = "factory"`) per D-12 |
| AGNT-03 | Skill catalog — registration, discovery, governance, runtime grant/revoke with policy-compatibility check and replay capture (§6.2) | D-IMPL-12 (four skill types, catalog entries as versioned Control Plane artifacts with typed requirements declaration; grants as separate versioned artifacts referencing entries by version) + D-IMPL-29 (two-tier governance) + D-06/D-07/D-09/D-10 constraints; `ControlPlaneRegistry` append-only versioning + `AuditLog` are the substrate; CINV-04 `skill-set-capture` check exists at `tests/invariants/test_replay_by_construction.py:127` waiting to activate |
</phase_requirements>

## Summary

This phase is almost entirely **internal design realization**, not external technology discovery. Every governing decision is already ruled (D-IMPL-11, 12, 19, 26, 28, 29 — all RESOLVED by Dave 2026-07-25) and DESIGN.md §3 specifies the component contracts at signature altitude. The I.1 fabric shipped every substrate this phase needs: canonical serialization + content hashing (`ccf.contracts.canonical`), the append-only versioned Control Plane registry with typed artifact classes and an audit log, the file-backed ArtifactStore with D-IMPL-26 hybrid addressing (`ccf-artifact://` URIs, `@latest` refused in replay), the five-dimension replay record with dimension 4 explicitly annotated as "extends in I.2", and the CINV lint framework with the factory-bypass rule (`cinv01c`) already scaffolded and dormant. The planner's job is composition, not invention.

The one genuinely new external dependency is **Jinja2** — required by D-IMPL-28 for prompt-artifact template-parameter validation (D-13: parse + validate declared parameters at construction time, no rendering to LLM). Jinja2 3.1.6 is current on PyPI, slopcheck-verified `[OK]`, and must be added to `pyproject.toml` pinned per the repo's exact-pin convention. The load-bearing Jinja2 API for this phase is `jinja2.Environment.parse()` + `jinja2.meta.find_undeclared_variables()` — parse-only introspection with no rendering, which keeps I.2 free of any LLM-adjacent surface and keeps the module algorithmic (CINV-03).

The main planning risks are not technical unknowns but invariant-preservation traps: (1) dimension 4 extension must remain a mechanical serialization of artifact-resolved state (hashes, not reconstructions) per D-05/D-06/D-07; (2) the `PerspectiveConditioning` contract in `src/ccf/replay/record.py` is frozen and canonically hashed — extending it changes replay-record content hashes, so the extension must be additive fields on the existing contract, done once, with tests updated in the same wave; (3) the factory-bypass lint currently keys on bare names `Agent`/`Task` constructed outside modules whose path contains `factory` — the new module layout must respect that convention or extend the lint deliberately; (4) fixtures carry all values (No-Hardcoding applies to test code too — I.1 established this and CINV-01 scans will cover the new fixture-loading code).

**Primary recommendation:** Plan four waves per D-04 with the D-01 vertical slice first; build every new schema as a `CCFContract` subclass registered through `ControlPlaneRegistry.register_typed`; treat `ccf.contracts.canonical.content_hash` as the sole identity primitive for agent versions, grant artifacts, and the grant-set hash; add `jinja2==3.1.6` to core dependencies.

## Architectural Responsibility Map

All tiers here are internal SDK layers (no browser/CDN — this is a library).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `Agent` class + `ArchetypeComponent` bundles | `/src/ccf/agents/` (new) | — | SDK mechanism per §6.1; final concrete class, no loop [CITED: DESIGN.md §3.1] |
| Agent/Task definition-artifact schemas | `/src/ccf/agents/` schemas (Pydantic v2) | Control Plane typed registration | D-IMPL-28; schemas are code, definitions are artifacts |
| Factory construction | `/src/ccf/agents/factory.py` (path must contain `factory` for CINV-01c) | ArtifactStore + Control Plane resolution | "Factory reads through Control Plane resolution, never raw storage" [CITED: DESIGN.md §3.5] |
| Hash-verified version bump (D-05) | `src/ccf/controlplane/registry.py` extension | — | Registration-time refusal is a Control Plane behavior per CONTEXT integration points |
| Skill catalog + grant state machine + tier-1 check | Control Plane (new module, e.g. `src/ccf/skills/` or under controlplane) | AuditLog for every action | D-IMPL-12/29: catalog entries and grants are Control Plane artifacts; grants audited |
| ApprovalSink Protocol (tier 2) | `/src` Protocol + `/tests` test-double sink | I.4 ApprovalGate later | D-09; conformance-suite pattern from `tests/conformance/` applies |
| Skill dispatch (local-callable, tool) | agents/skills mechanism | NotYetBound typed error for MCP/A2A | D-08 |
| Replay dimension 4 extension | `src/ccf/replay/record.py` (`PerspectiveConditioning`) | serve/replay engine plumbing | Record docstring already reserves this extension for I.2 [VERIFIED: codebase] |
| Prompt-artifact validation (axis 6) | new prompt-artifact module (algorithmic; Jinja2 parse-only) | ArtifactStore URI resolution | D-13; no rendering, no LLM |
| Test-double harness driver | `/tests` fixtures only | — | D-03; never `/src` or `/runtime` |
| No-bypass + prompt-literal enforcement | `tools/lints/no_hardcoding.py` | CI | D-12: lint is the mechanism of record; no token |

## Standard Stack

### Core (already pinned in pyproject.toml — do not re-litigate)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.13.4 (pinned) | Artifact schemas, `extra=forbid`, JSON Schema export | D-IMPL-28 ruling [VERIFIED: pyproject.toml + PyPI `pip index versions` shows 2.13.4 current] |
| pyyaml | 6.0.3 (pinned) | YAML definition artifacts | D-IMPL-28; already used by `load_artifact` in controlplane/artifacts.py [VERIFIED: codebase] |
| pytest / hypothesis / mypy | pinned in `dev` extra | TDD-on-invariants pattern | Carried from I.1 [VERIFIED: pyproject.toml] |

### New This Phase
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jinja2 | 3.1.6 | Prompt-artifact template parsing + parameter introspection (parse-only in I.2) | D-IMPL-28/D-13. Pin exactly, add to core `dependencies`. [VERIFIED: `pip index versions jinja2` → 3.1.6 current; slopcheck `[OK]` on PyPI] |

Key API (parse-only, no render — keeps the module clean of any generation surface):

```python
# Source: Jinja2 official API (jinja2.meta) — stable since 2.x. [ASSUMED: training knowledge of
# API surface; verify signature against installed 3.1.6 during the slice — see Assumptions A1]
from jinja2 import Environment
from jinja2.meta import find_undeclared_variables

env = Environment()               # no loader needed for parse-only validation
ast = env.parse(template_source)  # raises jinja2.TemplateSyntaxError on bad template
used = find_undeclared_variables(ast)  # set[str] of template parameters
# Validate: declared parameters in the referencing definition == used (or superset rule per plan)
```

**Installation:**
```bash
# add "jinja2==3.1.6" to [project].dependencies in pyproject.toml, then
pip install -e ".[dev]"
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 parse-only introspection | Regex over `{{ ... }}` | Hand-rolls a template parser; misses `{% for %}`/filters/nested access; violates Don't-Hand-Roll. Jinja2 is ruled by D-IMPL-28 anyway |
| Pydantic JSON Schema export (`model_json_schema()`) | Hand-written JSON Schema files | Drift between schema and validator; D-IMPL-28 says "exported JSON Schema" — generate from the Pydantic models |

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| jinja2 | PyPI | ~17 yrs (2.0 era 2008) | very high (Pallets) | github.com/pallets/jinja | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

(slopcheck ran successfully against PyPI: `jinja2 [OK]`, 2026-07-26. The trailing `pip install` failure was PEP-668 externally-managed-environment noise, irrelevant since the dependency enters via pyproject.toml. Note npm also has an unrelated `jinja2` package — the correct ecosystem is PyPI.)

## Architecture Patterns

### System Architecture Diagram

```
                         AUTHOR-TIME                                    RUN-TIME
  YAML agent/task/skill/prompt artifacts (fixtures / user)
        │
        ▼
  ArtifactStore (file store, D-IMPL-26 hybrid addressing)
        │  register_typed (Pydantic v2 schema validation, extra=forbid)
        ▼
  ControlPlaneRegistry ──── hash-verified bump check (D-05):
        │                    refuse content-change-without-bump AND
        │                    bump-without-content-change
        │  resolve(key, version)  — pinned, never @latest
        ▼
  AgentFactory.construct(definition_ref) ─────────────► Agent (single concrete class)
        │   1. resolve definition + referenced artifacts       │ identity = content hash
        │   2. validate six axes (Pydantic)                    │ + versioned URI annotation
        │   3. compose ArchetypeComponent bundles              │ + composed archetype list
        │      (ordered; dedupe / order-wins+warn / error)     │ + bound skill-set
        │   4. resolve instruction bindings (axis 6):          │
        │      load prompt artifact, Jinja2 parse,             ▼
        │      declared-params vs find_undeclared_variables    test-double harness (/tests only)
        │      → construction error on mismatch                │ consume product / invoke skill /
        ▼                                                      │ emit via effect capture
  Skill catalog (Control Plane artifacts, 4 types)             ▼
        │  grant request ──► tier 1 policy-compat check   serve()/replay path
        │  (non-waivable) ──► tier 2? ──► ApprovalSink    │
        │  state machine: requested → pending-approval    ▼
        │                → effective / refused        DecisionReplayRecord
        │  every transition → AuditLog                dimension 4 += agent content hash,
        ▼                                             URI annotation, archetype list,
  grant-set hash = content_hash(ordered active        grant-set hash (D-06/D-07)
  grant-artifact hashes) — D-07
```

### Recommended Project Structure (Claude's discretion per CONTEXT; suggested)
```
src/ccf/agents/
├── __init__.py
├── agent.py          # Agent (concrete, final), trust-leg surface, no loop
├── archetypes.py     # ArchetypeComponent Protocol + six bundles (or one module per archetype)
├── composition.py    # D-IMPL-19 ordered composition + conflict rules
├── definitions.py    # AgentDefinition / TaskDefinition Pydantic schemas (six axes)
├── factory.py        # AgentFactory / TaskFactory — path contains "factory" (CINV-01c)
├── prompts.py        # prompt-artifact loading + Jinja2 parse-only validation (D-13)
└── errors.py         # NotYetBound, composition/construction error taxonomy
src/ccf/skills/
├── catalog.py        # catalog entry schema (4 types + requirements declaration), registration/discovery
├── grants.py         # grant artifacts, state machine, tier-1 check, ApprovalSink Protocol
└── dispatch.py       # local-callable + tool dispatch; NotYetBound for mcp/a2a
```

### Pattern 1: Typed artifact class + factory interpreter (extend, don't invent)
**What:** New artifact schemas follow the exact I.1 pattern: `CCFContract` subclasses (frozen, `extra=forbid`, canonically serializable), declared `ArtifactClass`, registered via `ControlPlaneRegistry.register_typed`, loaded from YAML via the existing `load_artifact`/`parse_artifact` machinery in `src/ccf/controlplane/artifacts.py`.
**When to use:** every new artifact class — agent definition, task definition, skill catalog entry, skill grant, prompt artifact.
**Why:** version identity is already content identity in the registry (idempotent re-registration, append-only), which is exactly the substrate D-05's hash-verified bump needs. [VERIFIED: src/ccf/controlplane/registry.py docstring]

### Pattern 2: Structural `ArchetypeComponent` Protocol
**What:** Per DESIGN.md §3.1, archetypes conform structurally to a Protocol exposing `fabric_interaction_pattern()`, `replay_obligations()`, and `configuration_defaults()`. The factory attaches them in declaration order.
**Conflict rules (D-IMPL-19, verbatim):** identical obligations contributed twice → deduplicated; conflicting configuration defaults → declaration order wins with a **factory warning**; hard contradictions → **factory construction error**. These three rules are "explicit enough to unit-test directly" [CITED: FEASIBILITY.md §3.3 verdict]. The obligation-declaration shape is Claude's discretion — recommend making obligations `CCFContract` values so "identical" and "contradictory" are decidable via canonical bytes.

### Pattern 3: Grant state machine behind a Protocol sink (D-09)
**What:** requested → pending-approval → effective/refused, with tier 1 always evaluated first. `ApprovalSink` is a Protocol; I.2 ships a test-double sink in fixtures and a conformance test in `tests/conformance/` (established I.1 pattern for every new Protocol per CONTEXT "Reusable Assets").
**Replay/audit:** every transition emits an `AuditEvent` (grant, approval, effective-time per D-IMPL-29); the effective set feeds the D-07 grant-set hash.

### Pattern 4: Typed refusals as returned values, exceptions for broken deployments
**What:** Established I.1 discipline [VERIFIED: STATE.md accumulated decisions; gate refusals in `src/ccf/products/gates.py`]. Apply it here: a tier-1 refusal or a hash-verified-bump refusal is a *returned typed refusal* (a bad artifact, not a broken fabric); a missing Control Plane key stays `ControlPlaneMissing` (exception). NotYetBound for MCP/A2A dispatch is arguably a deployment-shape error — the planner should decide its side of the line explicitly and document it (see Open Questions Q2).

### Anti-Patterns to Avoid
- **Reconstruction in dimension 4:** never derive replay content from live objects; serialize the artifact-resolved record (hashes) captured at construction/grant time. "No reconstruction, no drift between what ran and what is recorded" [CITED: DESIGN.md §3.6].
- **Floats or naive datetimes anywhere near identity:** `ccf.contracts.canonical` rejects them outright; grant-set hashing and version comparison must stay on int/Decimal/aware-datetime. [VERIFIED: src/ccf/contracts/canonical.py]
- **An epoch counter or version bump on skill grant:** D-07 explicitly forbids it — agent version is stable across grants.
- **A construction token on `Agent`:** D-12 explicitly forbids re-adding it.
- **Prompt text or agent config inline in test code:** No-Hardcoding applies to fixtures' *code* too; values live in `tests/fixtures/banking/*.yaml` files.
- **Rendering a Jinja2 template in I.2:** parse-only. Any `template.render(...)` call is I.3 scope creep.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Template parameter discovery | regex over `{{ }}` | `jinja2.Environment.parse` + `jinja2.meta.find_undeclared_variables` | control structures, filters, nested attribute access all defeat regex |
| Content identity / grant-set hash | any new hashing scheme | `ccf.contracts.canonical.content_hash` | CONTEXT mandates it; the SDK permits exactly one canonical form [VERIFIED: canonical.py "Nothing else in the SDK may define its own canonical form"] |
| Artifact versioning/append-only storage | a new store | `ControlPlaneRegistry` + `ArtifactStore` file impl | D-05's refusal logic is a thin check on top of existing content-hash version identity |
| JSON Schema for non-Python tooling | hand-written schemas | Pydantic `model_json_schema()` | D-IMPL-28 "exported JSON Schema" |
| Protocol conformance tests | ad-hoc per-impl tests | `tests/conformance/` parametrized suite pattern | established I.1 pattern; applies to ApprovalSink and skill dispatch |
| Audit trail for grants | new log type | `ccf.controlplane.audit.AuditLog` / `AuditEvent` | append-only, time-injected, records failures — already the audit plane |

**Key insight:** I.1 deliberately built the substrates (canonical hashing, append-only registry, artifact store, audit log, lint framework, conformance suites) so that I.2 is schema + composition work over ruled formats. FEASIBILITY.md rates every agent-surface component "strong fit" on this basis.

## Common Pitfalls

### Pitfall 1: Extending `PerspectiveConditioning` breaks replay-record hashes mid-phase
**What goes wrong:** `DecisionReplayRecord` is a frozen `CCFContract`; adding dimension-4 fields changes canonical bytes and thus every record's content hash. If done piecemeal (agent identity in wave 1, grant-set hash in wave 3), tests asserting byte-exact replay churn twice.
**Why it happens:** D-01's slice needs agent identity in dimension 4 early, but the grant-set hash lands with wave (c).
**How to avoid:** design the full dimension-4 field set once (D-06 enumerates it exactly: definition content hash, versioned-URI annotation, composed archetype list, grant-set hash) in the slice, with the grant-set field carrying an explicit "no grants" value (a positive claim, mirroring the `MODE_1_MODEL_VERSION = "none"` precedent in record.py) until wave (c) populates it.
**Warning signs:** replay tests updated in more than one wave for the same field family.

### Pitfall 2: CINV-01c convention mismatch
**What goes wrong:** the dormant factory-bypass rule fires on `Agent(...)`/`Task(...)` constructed outside modules whose path contains `factory` [VERIFIED: tools/lints/no_hardcoding.py `FACTORY_ONLY_NAMES`, `FACTORY_PATH_MARKER = "factory"`]. If `Agent.__init__` is invoked internally from `agent.py` or `composition.py`, the lint flags SDK-internal construction — or worse, the team allowlists it away and hollows the check.
**How to avoid:** put the one legitimate `Agent(...)` call site inside `factory.py`; the factory composes and constructs. Tests construct via the factory from fixture artifacts (CLAUDE.md §6.4 requires this anyway). If the lint needs extension (e.g., name-alias detection, keyword construction via `type()`), extend `cinv01c` deliberately in the factory-hardening wave — CONTEXT says "extend factory-bypass rules rather than building new machinery."
**Warning signs:** new entries in `tools/lints/allowlist.yaml` for cinv01c.

### Pitfall 3: Grant-set hash nondeterminism
**What goes wrong:** D-07 requires a deterministic hash over the *ordered* set of active grant-artifact hashes. "Ordered" must be defined — grant time? hash sort? — or two processes disagree.
**How to avoid:** use canonical serialization's own rules: a `frozenset` of grant hashes canonicalizes as an array sorted by each element's canonical bytes [VERIFIED: canonical.py table]. Recommend: the grant-set is a set (sorted-by-hash canonical form), not an insertion-ordered list, unless the planner decides grant order is semantically meaningful (it should not be — revocation would then reorder history).
**Warning signs:** any list of hashes whose order depends on wall-clock arrival.

### Pitfall 4: Tier-1 check drifting into values
**What goes wrong:** the policy-compatibility check ("declared requirements exceed the agent's policy regime or context contract") tempts a hard-coded comparison vocabulary (scope names, egress categories) in `/src`.
**How to avoid:** the *requirements-declaration schema* is mechanism (typed block on the catalog entry per D-IMPL-29); the vocabulary values live in fixture policy-regime artifacts. The check compares declared sets structurally — subset/equality over opaque identifiers — never interpreting specific scope names. Mirror the D-IMPL-38 discipline (no silent defaults: an agent definition without a policy regime cannot be granted anything).
**Warning signs:** string literals naming scopes/egress classes in `/src`; CINV-01b may catch numeric forms but not string vocabularies — review manually.

### Pitfall 5: The test-double harness leaks toward mechanism
**What goes wrong:** the D-03 driver grows convenience features (retry, context assembly, tool routing) and becomes a de-facto loop, violating CLAUDE.md §7.3.
**How to avoid:** keep it a linear deterministic script in `tests/fixtures/` (or `tests/agents/harness_double.py` as a fixture module): one product consumption, one skill invocation, one effect emission, no branching on model output (there is no model in I.2 — D-13). CINV-02 (harness-import lint) does not fire on `/tests`, so this boundary is discipline + review, not lint.
**Warning signs:** the double imported from more than the agent test modules; any loop/while over agent turns.

### Pitfall 6: Hash-verified bump refuses legitimate no-op re-registration
**What goes wrong:** D-05 refuses "version changed without content change" AND "content changed without bump" — but the registry today treats byte-identical re-registration as idempotent (same version, no-op). The new check must preserve idempotency: re-registering identical content under the identical `artifact_version` is fine; identical content under a *new* version is the refusal case.
**How to avoid:** specify the three-outcome table explicitly in the plan (same-content/same-version → idempotent OK; same-content/new-version → refuse; new-content/same-version → refuse; new-content/new-version → append) and TDD it.

### Pitfall 7: pyproject pin vs installed environment drift
**What goes wrong:** pyproject pins `pydantic==2.13.4` but the ambient interpreter has 2.12.5 and Jinja2 3.1.2 [VERIFIED: `pip show`] — the repo evidently runs in a venv or the pins were bumped after last install. Schema behavior (JSON Schema output text) can differ across pydantic minors, breaking exported-schema snapshot tests.
**How to avoid:** the environment-setup task in the slice plan should reinstall `-e ".[dev]"` in the project venv and assert `pydantic.__version__ == "2.13.4"` before schema-export tests; pin `jinja2==3.1.6` (not the ambient 3.1.2).

## Code Examples

### Six-axis definition artifact (fixture shape, per D-IMPL-28 + DESIGN.md §3.6)
```yaml
# tests/fixtures/banking/agents/covenant_analytics.yaml — illustrative shape only;
# actual field names are the planner's schema decision. [ASSUMED: shape synthesized
# from D-IMPL-28 + DESIGN.md §3.6; no ruled field-name vocabulary exists yet]
schema_version: "1.0.0"        # per-artifact-class lane (D-IMPL-28)
artifact_version: "1.0.0"      # author-bumped; hash-verified (D-05)
name: covenant-analytics
tenant: fixture-bank
archetypes: [analytics_insights]          # axis 1 — ordered list (D-IMPL-19)
context_contract:                          # axis 2
  consumes: [{ product_class: "...", schema_version: "..." }]
perspective: { role: "...", selection_params: {} }   # axis 3 (D-IMPL-49 signature)
policy_regime: { ref: "ccf-artifact://fixture-bank/policy_bundle/...@1.0.0" }  # axis 4
halflife_debt_profile: { ref: "ccf-artifact://fixture-bank/debt_profile/...@1.0.0" }  # axis 5
instruction_bindings:                      # axis 6 — refs only, never inline (D-13)
  - prompt: "ccf-artifact://fixture-bank/prompt/...@1.0.0"
    parameters: [entity_name, as_of]       # validated against find_undeclared_variables
```

### Hash-verified bump outcome table (D-05)
```python
# Registration decision — pure function over (existing_versions, incoming). Refusals are
# typed returned values (I.1 discipline), not exceptions.
# content_hash(incoming) == hash bound to incoming.artifact_version?  → idempotent no-op
# content changed, artifact_version unchanged                          → RefuseUnbumpedChange
# content unchanged, artifact_version bumped                           → RefuseEmptyBump
# content changed, artifact_version bumped                             → append new version
```

### Grant-set hash (D-07, using I.1 canonical machinery)
```python
from ccf.contracts.canonical import canonical_bytes, content_hash
# active_grant_hashes: frozenset[str] of grant-artifact content hashes
# canonical form of a frozenset is an array sorted by element canonical bytes → deterministic
grant_set_hash = content_hash(frozenset(active_grant_hashes))  # exact call shape per canonical.py API
```

## Runtime State Inventory

Not applicable — greenfield feature phase, no rename/refactor/migration. (Section included to state the omission explicitly.)

## State of the Art

| Old Approach (I.1) | Current Approach (I.2) | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CINV-01c scaffolded, nothing to catch | Active against real `Agent`/`Task` classes | this phase | lint suite must go from vacuous to behavioral; add a fixture proving it fires |
| CINV-04 `skill-set-capture` skip (3 skips) | Active check (→ 2 skips) in wave (c) | this phase (D-10) | wave (c) exit criterion |
| `PerspectiveConditioning` = principal + role | + agent hash, URI annotation, archetype list, grant-set hash | this phase (D-06) | replay-record contract change, do once (Pitfall 1) |
| Capability-token pattern (I.1 serve/delivery) | NOT reused for factory no-bypass | ruled D-12 | deliberate divergence — planner must not re-add |

**Deprecated/outdated:** nothing external; no library migrations this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `jinja2.meta.find_undeclared_variables(env.parse(src))` is the correct/stable 3.1.6 API for parameter introspection | Standard Stack / Don't Hand-Roll | Low — API stable since 2.x; verify against installed 3.1.6 in the slice's first test |
| A2 | YAML fixture field names sketched in Code Examples | Code Examples | None — explicitly illustrative; schema naming is the planner's decision under D-IMPL-28 |
| A3 | CINV-02 harness-import lint does not scan `/tests` (so the D-03 double is lint-invisible and needs review discipline) | Pitfall 5 | Low — if it does scan tests, the double still imports no harness package, so no finding either way; confirm scan roots when planning the gate wave |

## Open Questions

1. **Where does the skill catalog module live — `src/ccf/skills/` vs `src/ccf/controlplane/`?**
   - What we know: D-IMPL-12 makes catalog entries and grants Control Plane artifacts; CONTEXT integration points name "skill catalog under Control Plane" but leave module layout to discretion.
   - Recommendation: separate `src/ccf/skills/` package holding schemas + state machine + dispatch, with registration flowing through the existing `ControlPlaneRegistry` — keeps `controlplane/` mechanism-generic.
2. **NotYetBound: exception or typed refusal?**
   - What we know: I.1 discipline — refusals returned, exceptions for broken deployments. Dispatching an MCP skill in I.2 is arguably a deployment misconfiguration (the transport doesn't exist yet), suggesting exception; but a granted-and-valid skill that merely isn't dispatchable yet resembles a refusal.
   - Recommendation: typed exception (subclass in the agents/skills error taxonomy) — nothing about the *artifact* is bad; the SDK build lacks the transport. Document the choice in the plan; it's Claude's discretion per CONTEXT.
3. **Dimension-4 delegation chain in I.2.** DESIGN.md §3.6 lists "delegation chain complete from originating principal to acting agent" in the dimension-4 serialization, but workflow calling chains are I.4. Recommendation: include a delegation-chain field with a single-element (originating principal → agent) value in I.2, extended by I.4 — avoids a second contract change (Pitfall 1 logic).
4. **Do task definition artifacts get their own dimension-4/5 capture in I.2?** D-11 ships schema + construction only; nothing executes a Task, so no replay capture should exist for tasks this phase. Verify the plan does not invent one.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | everything | ✓ | 3.12.3 (meets >=3.12) | — |
| pydantic | schemas | ✓ (ambient 2.12.5; pin says 2.13.4) | see Pitfall 7 | reinstall in venv |
| pyyaml | artifacts | ✓ | 6.0.1 ambient / 6.0.3 pinned | reinstall in venv |
| jinja2 | axis-6 validation | ✓ ambient 3.1.2; pin 3.1.6 | PyPI has 3.1.6 | add to pyproject + install |
| pytest/hypothesis/mypy | tests/lints/CI | ✓ (I.1 suite ran green: 383 passed / 3 skips) | pinned | — |
| Postgres/testcontainers | only if slice touches Postgres graph backend | marker-gated (`postgres`) | — | SQLite backend is the default fixture path |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** version-drift items above (reinstall editable with dev extra).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + hypothesis 6.161.5 + mypy 2.3.0 `--strict` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, testpaths=tests) |
| Quick run command | `pytest tests/agents tests/skills -x -q` (new dirs) or targeted file |
| Full suite command | `pytest -q && python -m tools.lints` (lints via `tools/lints/__main__.py`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGNT-01 | Agent base + six archetypes; composition conflict rules (dedupe/order-warn/error) | unit | `pytest tests/agents/test_archetypes.py tests/agents/test_composition.py -x` | ❌ Wave 0/slice |
| AGNT-01 | No path from Agent to L1–L5 (surface absence) | unit (negative) | `pytest tests/agents/test_consumption_discipline.py -x` | ❌ |
| AGNT-02 | Factory-only construction; six axes validated; bad instruction binding fails construction; hash-verified bump | unit + lint | `pytest tests/agents/test_factory.py -x && python -m tools.lints` (cinv01c behavioral fixture) | ❌ |
| AGNT-02 | JSON Schema export for artifact classes | unit | `pytest tests/agents/test_schema_export.py -x` | ❌ |
| AGNT-03 | Catalog registration/discovery, 4 types; tier-1 refusal; grant state machine via ApprovalSink double; NotYetBound on mcp/a2a dispatch | unit + conformance | `pytest tests/skills -x; pytest tests/conformance/test_approval_sink.py -x` | ❌ |
| AGNT-03 | Grant/revoke + skill-set in replay; CINV-04 skill-set-capture active | invariant | `pytest tests/invariants/test_replay_by_construction.py -rs -x` (assert 2 skips remaining, D-10) | ✅ exists, check currently skipped |
| AGNT-01..03 | Slice end-to-end: fixture agent runs against banking fabric, dimension 4 captured | integration | `pytest tests/integration/test_agent_slice.py -x` | ❌ |

### Sampling Rate
- **Per task commit:** targeted new-test files (`pytest <files> -x -q`) + `python -m tools.lints`
- **Per wave merge:** full `pytest -q` + lints + `mypy --strict`
- **Phase gate:** full suite green, skip count = 2 (D-10), lints exit 0, per-invariant gate checklist (I.1 D-17 pattern) before `/gsd-review`

### Wave 0 Gaps
- [ ] `tests/agents/` package + fixtures (`tests/fixtures/banking/agents/`, `.../skills/`, `.../prompts/`, `.../tasks/`) — covers AGNT-01/02
- [ ] `tests/skills/` package — covers AGNT-03
- [ ] `tests/conformance/test_approval_sink.py` — ApprovalSink Protocol conformance (I.1 pattern)
- [ ] Test-double harness fixture module (D-03) in `/tests`
- [ ] `jinja2==3.1.6` added to pyproject core dependencies + editable reinstall
- [ ] A behavioral lint fixture proving cinv01c fires on a bypassing construction (the rule is currently vacuous)

## Security Domain

`security_enforcement` is not set in `.planning/config.json`; treating as enabled. This phase is a library with no network/user-input surface, but governance mechanisms ARE its security surface.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (I.2) | approver identity binding is I.4/D-IMPL-21; ApprovalSink double records an approver id string only |
| V3 Session Management | no | — |
| V4 Access Control | **yes** | tier-1 policy-compatibility check (non-waivable) + tier-2 gate — this phase's core access-control mechanism; test refusal paths as first-class |
| V5 Input Validation | yes | Pydantic v2 `extra=forbid` on every artifact schema; YAML loaded via existing `load_artifact` (uses `yaml` safe path — verify `safe_load` is what artifacts.py uses when extending) |
| V6 Cryptography | yes (integrity) | sha256 content addressing via `ccf.contracts.canonical` only — never a second hash scheme; no signing in I.2 (D-IMPL-15 is I.3+) |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| YAML deserialization (arbitrary object construction) | Elevation | `yaml.safe_load` only — confirm when touching artifact loading; never `yaml.load` without SafeLoader |
| Jinja2 SSTI | Elevation | Parse-only in I.2 (no render, no user-controlled render context) — SSTI surface deferred to I.3; note this in the I.3 handoff |
| Artifact tampering | Tampering | content-addressed identity — tampered artifact fails its own address (D-IMPL-26, already structural) |
| Ungoverned capability sprawl | Elevation | tier-1 non-waivable check; refusal audited; grant-set hash in replay |
| Audit evasion (grant without record) | Repudiation | every state-machine transition through `AuditLog`; CINV-04 skill-set-capture check verifies by construction |

## Project Constraints (from CLAUDE.md)

- **No-Hardcoding Rule (§6.4):** no prompt/instruction literals, no agent/task definitions, no thresholds/skill grants as code constants — in `/src`, `/runtime`, `/examples`, and fixtures' code. CI: `tools/lints/no_hardcoding.py`.
- **Zero harness imports in `/src`** (§7.3, CINV-02); the D-03 test double lives in `/tests` and imports no harness.
- **No agent loop shipped or absorbed** (§7.3) — bounds the test double and the `Agent` class (no reasoning loop).
- **Archetypes in code, agents in artifacts** (§6.1) — an agent instance in `/src` is a defect.
- **Single-writer** (§10) — nothing in this phase acquires a graph write handle; ContextAssembly archetype emission goes through L2 (mechanism exists; I.2 declares the pattern, transport lands later).
- **Typed contracts at every boundary** — Pydantic `extra=forbid` (`CCFContract`).
- **Whitepaper/CLAUDE.md citations in public docstrings**; SDK-extension surfaces cite CLAUDE.md §6 and say so explicitly (I.1 modules model this style).
- **Algorithmic modules declare `__ccf_mode__ = "algorithmic"`; no LLM client imports** (CINV-03) — everything in I.2 is algorithmic (D-13: no LLM invocation).
- **Surface gaps as D-IMPL-NN and stop** — do not pick defaults on whitepaper-silent questions.
- **Phase discipline:** branch `phase-i2`; commits at deliverable boundaries naming the D-IMPL/section served; ends with `/gsd-review` → triage → Dave approval → `D-GATE-I.2`; merge to `main` only at the gate. Model mandate for Phase I work: Opus 5 (fallback Opus 4.8), high effort.
- **Tests construct agents through the factory from fixture artifacts** — never inline (§6.4).

## Sources

### Primary (HIGH confidence)
- Codebase inspection (2026-07-26): `src/ccf/controlplane/{registry,audit,artifacts}.py`, `src/ccf/replay/record.py`, `src/ccf/contracts/canonical.py`, `src/ccf/artifacts/protocol.py`, `tools/lints/no_hardcoding.py`, `tests/invariants/test_replay_by_construction.py`, `pyproject.toml`, `tests/fixtures/banking/`
- `docs/DESIGN.md` §3 (Core Agent Types, full component contracts §3.1–§3.8)
- `docs/DECISIONS.md` — D-IMPL-11, 12, 19, 26, 28, 29 (all RESOLVED, Dave, 2026-07-25)
- `docs/FEASIBILITY.md` — agent-surface verdicts (all "strong fit")
- `.planning/phases/05-.../05-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- PyPI registry via `pip index versions` (jinja2 3.1.6, pydantic 2.13.4); slopcheck `jinja2 [OK]`

### Secondary (MEDIUM confidence)
- Jinja2 `meta.find_undeclared_variables` API surface — training knowledge of a long-stable API, flagged A1 for in-slice verification

### Tertiary (LOW confidence)
- none

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — one new dep, registry- and slopcheck-verified; everything else pinned since I.1
- Architecture: HIGH — DESIGN.md §3 specifies signatures; all governing D-IMPLs resolved with zero provisionals
- Pitfalls: HIGH — derived from direct code reading of the contracts the phase must extend

**Research date:** 2026-07-26
**Valid until:** 2026-08-26 (stable internal domain; only Jinja2/pydantic pins could move)
