# Phase 12: Synthetic-Data Demonstration - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship the milestone's showcase: a deterministic, multi-entity synthetic fake
data store (every domain value in definition artifacts per No-Hardcoding) plus
one runnable end-to-end example in which raw data flows L1→L2, folds into the
Context Graph, projects into typed Context Products, and an agent solves a
concrete reasoning problem it could not solve from the raw data alone. The demo
runs in CI alongside the v0.1 examples with a single documented command,
deterministically, and a narrated step-by-step walkthrough document
("how data folds into context") literal-includes the example's code and
artifacts, ready for the Phase 14 docs site. Requirements: DEMO-01, DEMO-02,
DEMO-03.

</domain>

<decisions>
## Implementation Decisions

### Demo domain & story
- **D-01:** Demo domain is **banking** — extends the quickstart/fixture
  banking scenario so Phase 14 docs tell one continuous story with realistic
  policy pressure.
- **D-02:** The reasoning problem is **entity-resolution fraud**: the same
  counterparty appears under different identifiers across sources; only L2
  entity resolution links the aliases, revealing a **circular payment
  pattern** (fraud ring). L2 — the layer raw data literally lacks — is the
  hero of the story.
- **D-03:** **Three source systems** feed L1 (e.g., core banking
  transactions, a payments/wire system, a counterparty/KYC registry) —
  enough scatter that no single source reveals the ring, still tractable to
  narrate step-by-step.
- **D-04:** Dataset scale is **thousands of entities (~1k–5k)** with one
  planted fraud ring among plausible noise — a maximally credible
  needle-in-haystack. Generation and the demo run must still be CI-fast;
  the walkthrough shows representative excerpts, not the whole store.

### Data store & generator
- **D-05:** The fake data store is produced by a **new purpose-built demo
  generator** — not an extension of `perf/synth/`. It borrows perf/synth's
  determinism discipline (fixed documented seed + checksum/shape
  assertions), never its deliberately meaningless ontology. Perf stresses
  shape; the demo tells a story.
- **D-06:** Substrate is **SQLite databases** — one SQLite file (or
  table-set) per source system, generated deterministically at demo start.
  Feels like real systems of record; a curious newcomer can query them with
  standard tools; exercises a realistic ingest shape.
- **D-07:** The fraud-ring **planted pattern and noise-generation rules live
  in a versioned scenario definition artifact (YAML)**; the generator is a
  pure interpreter (No-Hardcoding §6.4). The walkthrough literal-includes
  the scenario file — "change this to make your own demo."
- **D-08:** Determinism pinned three ways: **fixed documented seed +
  checksum/shape assertions on the generated store** (row counts, ring
  signature) **+ byte-compared expected final output**, matching the v0.1
  examples' expected-output discipline (any regeneration is a reviewed,
  deliberate event).

### Agent & the "unreachable from raw data" proof
- **D-09:** The demo agent is declared from the **`AnalyticsInsightsAgent`
  archetype** — familiar from example 01, now doing something dramatically
  bigger over Context Products.
- **D-10:** Reasoning runs in **both modes**: detection is **deterministic
  skill-driven** (cycle detection over the resolved-entity payment graph
  in typed Context Products) in CI; an **optional `--live` flag** adds LLM
  behavior locally.
- **D-11:** The headline claim is **executed, not asserted**: a **baseline
  contrast run** first applies the same detection logic to the raw
  per-source data (no entity resolution, no graph) and finds nothing; then
  runs against governed context and finds the ring. CI pins **both**
  outcomes.
- **D-12:** `--live` mode is **narration-only**: the LLM writes a
  citation-anchored investigation summary from the typed Context Product
  (ContentGeneration-style step). Detection stays deterministic and
  **identical in both modes**; `--live` never runs in always-on CI.

### Placement & walkthrough
- **D-13:** The demo lives at **`examples/08-e2e-demo`** (or similar
  numbered slug) — capstone of the numbered suite, inheriting the examples
  CI harness, expected-output discipline, and README convention with zero
  new infrastructure. Phase 13's upgrade pass covers it naturally.
- **D-14:** The narrated walkthrough is a **markdown doc under `docs/`**
  (e.g., `docs/demo-walkthrough.md`), written now in mkdocs-compatible form
  with literal-include directives (pymdownx.snippets-style paths) so
  Phase 14 mounts it unchanged. The example README stays short and links
  to it.
- **D-15:** The one command is **`python examples/08-.../run.py`** —
  matching the existing per-example invocation convention exactly.
- **D-16:** Console output is **staged narration**: each stage prints a
  labeled banner plus a few key facts (events ingested, entities resolved,
  ring detected) so "watching raw data become context" happens live in the
  terminal — deterministic text, byte-compared in CI.

### Claude's Discretion
- Exact entity/transaction counts within the ~1k–5k band, ring size
  (~4–6 aliased counterparties), and noise parameters — provided D-08
  determinism holds and CI stays fast.
- SQLite schema design per source system, and whether generation happens
  inside run.py's first stage or as a distinct step run.py invokes.
- Exact numbered slug and stage-banner wording.
- `--live` provider/configuration mechanics, provided it follows existing
  SDK LLM-access patterns and stays out of always-on CI.
- Walkthrough document structure and diagram choices.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope
- `.planning/REQUIREMENTS.md` — DEMO-01..03 texts
- `.planning/ROADMAP.md` — Phase 12 goal and four success criteria

### Project invariants & rulings
- `CLAUDE.md` §6.4 (No-Hardcoding — scenario/domain values in definition
  artifacts, example code thin and generic), §9 (examples discipline:
  runnable end-to-end, code and artifacts side by side, README per
  example, D-IMPL-52 horizontal domain mix — quickstart is banking),
  §10 (L1→L6 flow, single-writer)
- `docs/DECISIONS.md` — D-IMPL-52 (banking quickstart/domain mix),
  Phase-8 D-10 / D-IMPL-70 lineage (always-on CI is deterministic-only;
  anything live/timing-dependent is opt-in)

### Prior phase carry-forward
- `.planning/phases/11-performance-battery/11-CONTEXT.md` — D-06 (perf/synth
  packaged importable; Phase 12 chose a NEW generator instead, borrowing
  only the determinism discipline), D-08 (seed + checksum pattern), D-09
  (why the perf ontology is unusable for a story demo)

### Code surfaces / patterns
- `examples/00-quickstart/` — the banking scenario this demo extends;
  run.py + artifacts/ layout convention (agent.yaml, ontology.yaml,
  controlplane.yaml, prompt.yaml, task.yaml, workflow.yaml)
- `examples/01-agent-basics/` — AnalyticsInsightsAgent declaration pattern
  the demo agent follows
- `perf/synth/generator.py` + `perf/synth/artifacts/` — determinism
  discipline (seed, checksum/shape assertions) to mirror, not import
- Examples CI harness + expected-output byte-compare discipline (Makefile
  `ci: ci-core examples`; regeneration is a reviewed event)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Examples CI harness and expected-output byte-compare machinery — the demo
  joins it as another numbered example, zero new CI infrastructure.
- `examples/00-quickstart` banking ontology/artifacts — the domain seed the
  demo scenario extends.
- Agent & Task Factory + definition-artifact schema (D-IMPL-28) — the demo
  agent, task, skills, and scenario are all artifacts.
- `perf/synth` determinism pattern (fixed seed + checksum assertions) as a
  design reference.

### Established Patterns
- No-Hardcoding: generator code is a pure interpreter; the scenario YAML
  carries the ring, aliases, amounts, and noise parameters.
- Always-on CI deterministic-only; `--live` LLM behavior documented but
  never in `make ci`.
- Per-example `run.py` invocation + short README linking out.

### Integration Points
- `examples/08-*` slot in the numbered suite + Makefile examples target.
- `docs/demo-walkthrough.md` → Phase 14 mkdocs site (literal-includes must
  use paths Phase 14 can mount unchanged).
- Phase 13 (Examples Upgrade) will sweep the new example's README.

</code_context>

<specifics>
## Specific Ideas

- The contrast must be executed, not asserted: raw-data pass fails, governed
  context pass succeeds, both pinned in CI.
- The scenario artifact is the teaching centerpiece — the walkthrough should
  frame it as "change this to make your own demo."
- Staged console banners make the L1→L2→graph→product→agent transformation
  visible live in the terminal.

</specifics>

<deferred>
## Deferred Ideas

- Wiring `--live` into an opt-in `workflow_dispatch` CI job (like
  live-legs.yml) — considered, not chosen for this phase; a future option
  if the live path needs exercising on demand.
- `ccf demo` CLI subcommand as a front door — D-IMPL-22 territory, out of
  this phase's scope.

</deferred>

---

*Phase: 12-synthetic-data-demonstration*
*Context gathered: 2026-08-01*
