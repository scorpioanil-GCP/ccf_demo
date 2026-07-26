# Phase 5: Phase I.2 — Agent Specialization Framework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-25
**Phase:** 5-Phase I.2 — Agent Specialization Framework
**Areas discussed:** Build sequencing & slice, Agent versioning mechanics, Skill catalog scope in I.2, Task Factory scope

---

## Build sequencing & slice

| Option | Description | Selected |
|--------|-------------|----------|
| Slice first (Recommended) | Thin artifact→factory→Agent path against the I.1 banking fabric, then widen | ✓ |
| Subsystem-by-subsystem | Dependency order, end-to-end proof late | |
| Two slices | Separate specialization and skilling slices | |

**User's choice:** Slice first.

| Option | Description | Selected |
|--------|-------------|----------|
| AnalyticsInsights (Recommended) | Precursor of examples/01-agent-basics | ✓ |
| ContextAssembly | Exercises write path but doesn't foreshadow example 01 | |
| MonitoringSurveillance | Pulls long-running semantics early | |

**User's choice:** AnalyticsInsights.

| Option | Description | Selected |
|--------|-------------|----------|
| Test-double harness (Recommended) | Deterministic driver in /tests fixtures only | ✓ |
| Construction-only slice | No execution until I.3 | |
| Minimal runtime host in ccf_runtime | Risks shipping a loop | |

**User's choice:** Test-double harness.

| Option | Description | Selected |
|--------|-------------|----------|
| By pillar concern (Recommended) | Archetypes+composition / factory+axes / skilling+governance / gate | ✓ |
| By archetype | Six small waves | |
| Planner's choice | Fully delegated | |

**User's choice:** By pillar concern.

---

## Agent versioning mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Hash-verified bump (Recommended) | Author bumps; Control Plane refuses drift via D-IMPL-26 hash | ✓ |
| Auto-derived versions | Content-hash versions; semver loses meaning | |
| Trust the author | No consistency check | |

**User's choice:** Hash-verified bump.

| Option | Description | Selected |
|--------|-------------|----------|
| Hash + URI + skill-set (Recommended) | Content hash, URI annotation, archetype list, grant-set by hash | ✓ |
| URI only | Violates D-IMPL-26 | |
| Full artifact inline | Bloats records | |

**User's choice:** Hash + URI + skill-set.

| Option | Description | Selected |
|--------|-------------|----------|
| Grant-set hash (Recommended) | Deterministic hash over ordered active grant hashes | ✓ |
| Skill-set epoch counter | Second version lane to govern | |
| No distinct identity | No comparable capability identifier | |

**User's choice:** Grant-set hash.

---

## Skill catalog scope in I.2

| Option | Description | Selected |
|--------|-------------|----------|
| Schema all, exercise 2 (Recommended) | All four types in schema; dispatch for local-callable + tool; MCP/A2A NotYetBound | ✓ |
| Only 2 types in schema | Forces I.3 schema bump | |
| All four with stub transports | Fake transports risk | |

**User's choice:** Schema all, exercise 2.

| Option | Description | Selected |
|--------|-------------|----------|
| Pending-until-approved (Recommended) | Full grant state machine + ApprovalSink Protocol; I.4 plugs in | ✓ |
| Tier 1 only in I.2 | I.4 reworks grant flow | |
| Inline approval hook | Weak audit story | |

**User's choice:** Pending-until-approved.

| Option | Description | Selected |
|--------|-------------|----------|
| With the skilling wave (Recommended) | Check activates in the wave landing grant/revoke + replay capture | ✓ |
| At the gate wave | Late discovery risk | |
| First commit of I.2 | Suite red most of the phase | |

**User's choice:** With the skilling wave.

---

## Task Factory scope

| Option | Description | Selected |
|--------|-------------|----------|
| Schema + factory, no engine (Recommended) | Task artifacts validated/constructed; I.4 consumes | ✓ |
| Defer tasks entirely to I.4 | Factory reopened later | |
| Tasks + minimal executor | Orchestration pulled forward | |

**User's choice:** Schema + factory, no engine.

| Option | Description | Selected |
|--------|-------------|----------|
| Lint + capability token (Recommended) | AST lint + unforgeable construction token | |
| Lint only | CINV-01 AST check alone; no runtime guard | ✓ |
| Module-private class | Convention, not enforcement | |

**User's choice:** Lint only — **explicit divergence from the recommendation.** `Agent` stays a normal public class; no construction token.

| Option | Description | Selected |
|--------|-------------|----------|
| Full validate, no render-to-LLM (Recommended) | Load + validate template params at construction; no rendering | ✓ |
| URI reference only | Defers a D-IMPL-28 commitment | |
| Include render path | Premature — I.3 seam | |

**User's choice:** Full validate, no render-to-LLM.

## Claude's Discretion

- Banking fixture artifact specifics (realism bar applies)
- Plan/wave counts within the by-pillar organization; module layout
- Archetype Protocol bundle obligation-declaration shape (within D-IMPL-19 rules)
- NotYetBound taxonomy placement; grant-set hash canonical serialization details

## Deferred Ideas

- MCP/A2A skill dispatch → I.3; prompt rendering + LLM invocation → I.3; real ApprovalGate sink → I.4; task execution → I.4
