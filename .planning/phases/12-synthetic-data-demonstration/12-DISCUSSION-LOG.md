# Phase 12: Synthetic-Data Demonstration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-01
**Phase:** 12-synthetic-data-demonstration
**Areas discussed:** Demo domain & story, Data store & generator, Agent & 'unreachable' proof, Placement & walkthrough

---

## Demo domain & story

| Option | Description | Selected |
|--------|-------------|----------|
| Banking | Extends quickstart banking scenario; continuous docs story | ✓ |
| New neutral domain | Fresh domain (logistics etc.) for visible generality | |
| IoT/sensor ops | Device fleet telemetry; temporal/half-life story | |

**User's choice:** Banking (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Covenant breach risk | Cross-entity temporal synthesis reveals emerging breach | |
| Entity-resolution fraud | Aliased counterparties; L2 resolution reveals circular payments | ✓ |
| Stale-context hazard | Half-life decay changes the answer | |

**User's choice:** Entity-resolution fraud

| Option | Description | Selected |
|--------|-------------|----------|
| 3 sources | Transactions + payments/wire + counterparty/KYC registry | ✓ |
| 2 sources | Minimal scatter | |
| 4-5 sources | Includes unstructured docs; Pattern 5 scope risk | |

**User's choice:** 3 sources (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Hundreds of entities | ~200–500; readable + credible | |
| Tens of entities | Fully inspectable, weak claim | |
| Thousands of entities | ~1k–5k; maximally credible needle-in-haystack | ✓ |

**User's choice:** Thousands of entities
**Notes:** Walkthrough shows representative excerpts; CI speed must hold.

---

## Data store & generator

| Option | Description | Selected |
|--------|-------------|----------|
| New demo generator | Purpose-built; borrows perf/synth determinism discipline only | ✓ |
| Extend perf/synth | Parameterize with real ontology; couples trees | |
| Copy then diverge | Copy skeleton, rewrite freely | |

**User's choice:** New demo generator (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite databases | One per source system, deterministic, queryable | ✓ |
| Flat files (JSONL/CSV) | Simplest, fixture-like | |
| MCP server sources | Pattern 3 ingress showcase; process management cost | |

**User's choice:** SQLite databases (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Scenario artifact | YAML declares ring + noise; generator is pure interpreter | ✓ |
| Seed + code-shaped rules | Ring structure in code — No-Hardcoding conflict | |
| Pre-generated committed data | Committed outputs; opaque provenance | |

**User's choice:** Scenario artifact (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Seed + checksums + expected output | Full v0.1 examples discipline | ✓ |
| Seed + checksums only | Structural output assertions | |
| Expected output only | Intermediate data unverified | |

**User's choice:** Seed + checksums + expected output (recommended)

---

## Agent & 'unreachable' proof

| Option | Description | Selected |
|--------|-------------|----------|
| AnalyticsInsights | Familiar from example 01; fits fraud-ring analysis | ✓ |
| Assembly + Analytics pair | Agent composition showcase; longer walkthrough | |
| MonitoringSurveillance | Trigger-driven; long-running semantics complicate CI | |

**User's choice:** AnalyticsInsights (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic skills | Skill-driven cycle detection, no LLM, byte-exact CI | |
| LLM with recorded replay | Real LLM + replay fixtures | |
| Both modes | Deterministic in CI, optional --live locally | ✓ |

**User's choice:** Both modes

| Option | Description | Selected |
|--------|-------------|----------|
| Baseline contrast run | Raw-data pass finds nothing; governed context finds ring; both pinned | ✓ |
| Narrated-only contrast | Claim told, not shown | |
| Raw-data query appendix | Failing SQL scripts as appendix | |

**User's choice:** Baseline contrast run (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| LLM narrates findings | Detection deterministic in both modes; LLM writes citation-anchored summary | ✓ |
| LLM does the reasoning | Modes could diverge in outcome | |
| Live mode in opt-in CI | workflow_dispatch job for --live | |

**User's choice:** LLM narrates findings (recommended)
**Notes:** Opt-in live CI job noted as deferred idea.

---

## Placement & walkthrough

| Option | Description | Selected |
|--------|-------------|----------|
| examples/08-e2e-demo | Capstone of numbered suite; inherits CI harness | ✓ |
| demo/ top-level tree | Showcase signal; new CI wiring | |
| examples/demo (unnumbered) | Shares harness, awkward naming | |

**User's choice:** examples/08-e2e-demo (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| docs/walkthrough | mkdocs-compatible doc under docs/ with literal-includes | ✓ |
| Example README as walkthrough | One place, fights README conventions | |
| Both, generated | Build step emitting both; extra tooling | |

**User's choice:** docs/walkthrough (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| make demo | Top-level Makefile showcase target | |
| python examples/08.../run.py | Matches existing per-example convention | ✓ |
| ccf demo CLI subcommand | Dogfoods Experience Layer; D-IMPL-22 territory | |

**User's choice:** python examples/08.../run.py

| Option | Description | Selected |
|--------|-------------|----------|
| Staged narration | Labeled stage banners + key facts, byte-compared | ✓ |
| Quiet + summary | One final summary block | |
| Verbose trace | Per-record trace; brittle at scale | |

**User's choice:** Staged narration (recommended)

---

## Claude's Discretion

- Exact entity/transaction counts (~1k–5k band), ring size, noise parameters
- SQLite schema design; generation inside run.py vs distinct invoked step
- Exact numbered slug and stage-banner wording
- `--live` provider/configuration mechanics (existing SDK LLM-access patterns)
- Walkthrough document structure and diagrams

## Deferred Ideas

- Opt-in `workflow_dispatch` CI job exercising `--live` (live-legs.yml pattern)
- `ccf demo` CLI subcommand (D-IMPL-22 territory)
