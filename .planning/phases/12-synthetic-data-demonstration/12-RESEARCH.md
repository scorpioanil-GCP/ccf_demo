# Phase 12: Synthetic-Data Demonstration - Research

**Researched:** 2026-08-01
**Domain:** CCF SDK end-to-end demo example (synthetic banking data store → L1→L2 → graph → products → agent)
**Confidence:** HIGH (nearly all findings verified directly in the codebase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Demo domain is **banking** — extends the quickstart/fixture banking scenario so Phase 14 docs tell one continuous story with realistic policy pressure.
- **D-02:** The reasoning problem is **entity-resolution fraud**: the same counterparty appears under different identifiers across sources; only L2 entity resolution links the aliases, revealing a **circular payment pattern** (fraud ring). L2 is the hero of the story.
- **D-03:** **Three source systems** feed L1 (e.g., core banking transactions, a payments/wire system, a counterparty/KYC registry).
- **D-04:** Dataset scale is **thousands of entities (~1k–5k)** with one planted fraud ring among plausible noise; CI-fast; walkthrough shows representative excerpts.
- **D-05:** The fake data store is produced by a **new purpose-built demo generator** — not an extension of `perf/synth/`. It borrows perf/synth's determinism discipline (fixed documented seed + checksum/shape assertions), never its ontology.
- **D-06:** Substrate is **SQLite databases** — one SQLite file (or table-set) per source system, generated deterministically at demo start.
- **D-07:** Planted pattern and noise rules live in a **versioned scenario definition artifact (YAML)**; the generator is a pure interpreter (No-Hardcoding §6.4). The walkthrough literal-includes the scenario file.
- **D-08:** Determinism pinned three ways: **fixed documented seed + checksum/shape assertions on the generated store + byte-compared expected final output**, matching the v0.1 examples' expected-output discipline.
- **D-09:** The demo agent is declared from the **`AnalyticsInsightsAgent` archetype**.
- **D-10:** Reasoning runs in **both modes**: deterministic skill-driven cycle detection over the resolved-entity payment graph in CI; optional `--live` flag adds LLM behavior locally.
- **D-11:** The headline claim is **executed, not asserted**: a **baseline contrast run** on raw per-source data (no entity resolution) finds nothing; the governed-context run finds the ring. CI pins **both** outcomes.
- **D-12:** `--live` mode is **narration-only** (citation-anchored investigation summary from the typed Context Product). Detection stays deterministic and identical in both modes; `--live` never runs in always-on CI.
- **D-13:** The demo lives at **`examples/08-e2e-demo`** (or similar numbered slug), inheriting the examples CI harness, expected-output discipline, and README convention.
- **D-14:** Narrated walkthrough is a **markdown doc under `docs/`** (e.g., `docs/demo-walkthrough.md`), mkdocs-compatible with literal-include directives (pymdownx.snippets-style paths) so Phase 14 mounts it unchanged.
- **D-15:** The one command is **`python examples/08-.../run.py`**, matching the per-example convention.
- **D-16:** Console output is **staged narration**: labeled banner per stage plus key facts — deterministic text, byte-compared in CI.

### Claude's Discretion
- Exact entity/transaction counts within the ~1k–5k band, ring size (~4–6 aliased counterparties), and noise parameters — provided D-08 determinism holds and CI stays fast.
- SQLite schema design per source system, and whether generation happens inside run.py's first stage or as a distinct step run.py invokes.
- Exact numbered slug and stage-banner wording.
- `--live` provider/configuration mechanics, provided it follows existing SDK LLM-access patterns and stays out of always-on CI.
- Walkthrough document structure and diagram choices.

### Deferred Ideas (OUT OF SCOPE)
- Wiring `--live` into an opt-in `workflow_dispatch` CI job (like live-legs.yml).
- `ccf demo` CLI subcommand as a front door — D-IMPL-22 territory.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEMO-01 | Synthetic fake data store — deterministic, multi-entity, domain values entirely in definition artifacts | Generator pattern verified in `perf/synth/generator.py` (seed discipline, artifact-interpreted ontology); SQLite via stdlib `sqlite3`; scenario YAML artifact per D-07 |
| DEMO-02 | End-to-end runnable example: L1→L2 ingest, graph fold, projection, typed Context Products, agent solves a problem unreachable from raw data | Full pipeline pattern verified in `examples/00-quickstart/run.py` (boot → ingest → operators → projection → gates → replay serve) and agent pattern in `examples/01-agent-basics/run.py` (AgentFactory + AnalyticsInsights archetype); skills dispatch in `src/ccf/skills/` |
| DEMO-03 | Narrated walkthrough doc literal-including code/artifacts; demo runs in CI like the v0.1 examples | Examples CI job in `.github/workflows/ci.yml` (`make examples`, always-on, D-10); Makefile per-example target pattern; pymdownx.snippets literal-include convention for Phase 14 mkdocs |
</phase_requirements>

## Summary

This phase adds a ninth numbered example (`examples/08-*`) that is a capstone composition of already-shipped mechanism — no new SDK surface is required. Every building block exists and was verified in the repo: the L1→L6 pipeline used by example 00, the AgentFactory/AnalyticsInsights pattern from example 01, the skills catalog/dispatch machinery (`src/ccf/skills/`), the `--mode live` opt-in pattern and `LLMClientProtocol` from example 03, the byte-compare/canonical-bytes discipline from example 06, and the seed+checksum determinism discipline from `perf/synth/generator.py`. The new work is: (1) a scenario-YAML-interpreting demo generator that writes three SQLite source-system files, (2) an L1 ingest path reading those SQLite files into `SignalEnvelope`s, (3) a deterministic cycle-detection skill run twice (raw baseline vs governed context) with both outcomes pinned, (4) staged console narration byte-compared in CI, and (5) `docs/demo-walkthrough.md` with snippets-style literal includes.

**Zero new dependencies.** `sqlite3` is stdlib; PyYAML is already in use; cycle detection over a ~1k–5k-node payment graph is a trivial DFS/Tarjan pass — do not add networkx. No Package Legitimacy Audit needed (no installs).

**Primary recommendation:** Build the demo as a strict composition of existing example patterns — copy the structural skeleton of example 00/01, add the generator + scenario artifact + skill artifacts, wire `make example-08` into the `examples` Makefile target, and keep every domain value (ring members, aliases, amounts, schemas' vocabulary, thresholds, banner-fact values) in `artifacts/*.yaml`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Synthetic store generation | Example code (thin interpreter) | Scenario artifact (YAML) | No-Hardcoding: generator is mechanism, scenario is values |
| Source-system persistence | SQLite files (one per source) | — | D-06; queryable with standard tools |
| Ingest / normalization | L1 (`ccf.signal.envelope`) | Example glue reading SQLite | L1 owns the envelope contract; example maps rows → envelopes |
| Entity resolution / alias linking | L2 (`ccf.assembly.worker`) | Ontology artifact rules | L2 is the single writer and the story's hero |
| Graph state | L3 (`ccf.graph`) | — | Existing mechanism |
| Cycle detection | Skill (governed callable, `ccf.skills`) | Agent (AnalyticsInsights) | D-10: deterministic, skill-driven, replay-captured |
| Baseline contrast run | Example code invoking the same skill logic on raw rows | — | D-11: same detection logic, no resolution — must find nothing |
| LLM narration (`--live`) | `LLMClientProtocol` adapter, opt-in | Prompt artifact | D-12; never in always-on CI |
| Walkthrough doc | `docs/demo-walkthrough.md` | Phase 14 mkdocs | D-14 |

## Standard Stack

### Core (all already in the repo — nothing to install)
| Component | Where | Purpose | Verified |
|-----------|-------|---------|----------|
| `sqlite3` (stdlib) | Python stdlib | Source-system store files | [VERIFIED: stdlib] |
| PyYAML | already a dependency (used by every example and `perf/synth`) | Artifact loading | [VERIFIED: codebase] |
| `random.Random(seed)` | stdlib | Deterministic generation (perf/synth pattern) | [VERIFIED: perf/synth/generator.py] |
| `ccf.boot.boot` / assembly / operators / projection / products / replay | `src/ccf/` | The L1→L6 pipeline | [VERIFIED: examples/00-quickstart/run.py] |
| `AgentFactory` + `analytics_insights` archetype | `src/ccf/agents/` | Demo agent construction | [VERIFIED: src/ccf/agents/archetypes.py:360, examples/01-agent-basics] |
| Skills catalog/grants/dispatch | `src/ccf/skills/` (callables.py, catalog.py, dispatch.py, grants.py) | Cycle-detection skill, replay-captured | [VERIFIED: codebase] |
| `LLMClientProtocol` | `src/ccf/llm/__init__.py` | `--live` narration seam | [VERIFIED: codebase] |
| `canonical_bytes` / `content_hash` | `ccf.contracts.canonical` | Byte-compare discipline | [VERIFIED: examples/06] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled DFS cycle detection | networkx | New dependency for a trivial algorithm on a governed typed payload — rejected; also this is exactly the "skill" the demo showcases |
| SQLite files | In-memory dicts / YAML event lists (example 00 style) | D-06 locks SQLite; the queryable "real system of record" feel is the point |
| New generator sharing perf/synth code | Import perf/synth | D-05 locks a new generator; borrow discipline only |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase. All dependencies are stdlib or already present in the repo. **Packages removed:** none. **Packages flagged:** none.

## Architecture Patterns

### System Architecture Diagram

```
scenario.yaml ──▶ [demo generator (pure interpreter, seeded RNG)]
                       │ writes 3 SQLite files
                       ▼
   core_banking.db   wires.db   kyc_registry.db      ◀── "raw" tier
        │                │            │
        │  (BASELINE CONTRAST: same cycle-detection logic
        │   over raw per-source rows → finds NOTHING; pinned)
        ▼                ▼            ▼
   [row → SignalEnvelope mapping]  ── L1
        ▼
   [L2 assembly: entity-resolution rules from ontology.yaml
    link counterparty aliases across sources]  ── single writer
        ▼
   [L3 Context Graph] ─▶ [L4 operator chain] ─▶ [L5 projection Π]
        ▼
   [L6 typed Context Product: resolved-entity payment graph]
        ▼
   [AnalyticsInsights agent (factory-built from agent.yaml)]
        ├── deterministic cycle-detection SKILL → ring found; pinned
        └── (--live only) LLM narration via prompt artifact
        ▼
   staged console banners (byte-compared) + replay record
```

### Recommended Project Structure
```
examples/08-e2e-demo/            # slug at Claude's discretion
├── run.py                       # thin: stages, assertions, banners
├── generator.py (optional split)# pure interpreter of scenario.yaml
├── README.md                    # short; links to docs/demo-walkthrough.md
└── artifacts/
    ├── scenario.yaml            # ring members, aliases, amounts, noise params, seed, expected checksums
    ├── ontology.yaml            # entity/relationship resolution rules (banking, extends quickstart vocabulary)
    ├── agent.yaml               # AnalyticsInsights agent definition
    ├── controlplane.yaml        # policy regime, thresholds, expected outputs
    ├── halflife.yaml            # half-life/debt profile refs
    ├── skills.yaml              # cycle-detection skill registration + expected output
    ├── prompt.yaml              # --live narration prompt artifact
    └── task.yaml / workflow.yaml (if the agent invocation follows example 01's task pattern)
docs/demo-walkthrough.md         # mkdocs-compatible, pymdownx.snippets includes
Makefile: example-08 target; add to `examples` aggregate target
.github/workflows/ci.yml: examples job already runs `make examples` — verify 08 is picked up
```

### Pattern 1: Deterministic generator as artifact interpreter
`perf/synth/generator.py` is the canonical in-repo model [VERIFIED: codebase]: module-level documented seed constant, single `random.Random(SEED)` threaded through everything, fixed `EPOCH` datetime (never a clock read), all vocabulary from `artifacts/*.yaml`, docstring citing D-numbers, and pinned shape/checksum tests that fire on drift. Mirror this exactly; do not import it. Store checksums (row counts, ring signature hash) belong in `scenario.yaml` or a sibling expected-values artifact so run.py asserts against artifact data, not code constants.

### Pattern 2: Example skeleton
Copy example 00/01 structure [VERIFIED]: module docstring stating what is demonstrated with §-citations; `ARTIFACTS = Path(__file__).parent / "artifacts"`; `_load()` helper; `_instant()` UTC normalization for YAML timestamps (PyYAML yields naive datetimes — canonical serializer rejects them, D-IMPL-38); `tempfile` working dir; exit 0 on all assertions; final `print` block of labeled facts. Run under `PYTHONPATH=src:runtime`.

### Pattern 3: Opt-in live mode
Example 03's `--mode live` pattern [VERIFIED]: argparse flag, live-only imports deferred inside the live branch so deterministic runs need no LLM package, assertions in live mode land on what CCF governs (the consumed product / replay record), never on model text. `LLMClientProtocol` in `src/ccf/llm/__init__.py` is the one place `anthropic` and peers may be imported. Live never appears in `make ci` (Phase-8 D-10 / D-IMPL-70).

### Pattern 4: Byte-compared staged narration
D-16 + D-08 require deterministic console text. Options: (a) capture run.py stdout in the Makefile/CI and diff against a committed expected file, or (b) example-06 style — assert `canonical_bytes` equality internally and print deterministic facts. The existing suite pins outcomes via in-run assertions against artifact `expected` blocks [VERIFIED: examples/00 run.py:352-359] rather than external stdout diffs; the lowest-infrastructure path satisfying "byte-compared expected final output" is an in-run assertion of the full rendered narration string (built once, printed once, compared against a committed expected-output artifact/file). Planner should pick one and state it; recommend committed `expected_output.txt` (or YAML block) compared in-run — zero Makefile/CI changes.

### Anti-Patterns to Avoid
- **Domain values in code:** ring aliases, amounts, thresholds, banner fact values, schema column vocabulary as Python constants — No-Hardcoding violation, CI lint rejects prompt-shaped literals.
- **Generator writing to the graph directly:** everything enters L3 only through L2 (single-writer, CLAUDE.md §10). The generator emits SQLite rows; ingest maps rows → envelopes → L2.
- **LLM anywhere in the detection path:** detection is algorithmic; Algorithmic ⇄ Semantic Alternation lint (`@algorithmic`) applies.
- **Asserting the contrast instead of executing it:** D-11 requires the raw-data pass to actually run and find nothing.
- **Clock reads or unordered iteration in generation/narration:** every timestamp derives from a fixed epoch; iterate sorted keys; SQLite row order must be made explicit (ORDER BY) before hashing/ingest.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pipeline stages (ingest, assembly, operators, projection, gates, replay) | Any new plumbing | Existing `ccf.*` mechanism as composed in example 00 | Already shipped and CI-proven |
| Agent construction | Direct `Agent(...)` | `AgentFactory.construct` from `agent.yaml` | Factory-only rule (§6.4); example 01 shows the path |
| Skill invocation/audit | Ad-hoc function call | Skills catalog + dispatch (`src/ccf/skills/`) | Skill-set-in-force must land in replay (§6.2) |
| Canonical hashing/serialization | New hashing | `ccf.contracts.canonical` | Byte-compare discipline already exists |
| Determinism testing | New harness | perf/synth-style pinned checksum assertions inside run.py + examples CI | Zero new infrastructure (D-13) |

**Key insight:** the entire phase is artifact authoring + thin composition code; any new mechanism appearing in `/src` should be treated as a scope smell (with one possible exception — see Open Questions #1).

## Common Pitfalls

### Pitfall 1: Naive datetimes from PyYAML
**What goes wrong:** canonical serializer refuses naive datetimes (D-IMPL-38). **Avoid:** normalize at the artifact/SQLite boundary like example 00's `_instant()`. SQLite has no datetime type — store ISO-8601 strings with explicit `Z`/offset and parse with UTC attachment.

### Pitfall 2: Nondeterministic SQLite bytes
**What goes wrong:** checksumming the raw `.db` file can drift (page layout, SQLite version). **Avoid:** checksum logical content (sorted row tuples / canonical serialization of query results), not file bytes; assert row counts + ring-signature hash per D-08.

### Pitfall 3: CI runtime blowout
**What goes wrong:** 1k–5k entities × multi-source transactions through L2 could be slow if assembly is per-envelope chatty. **Avoid:** pick counts at the low end first, measure locally (`make example-08` should stay in the same order as existing examples — seconds), and record the chosen counts in scenario.yaml. Phase 11 perf data (1k rung) suggests this scale is comfortably CI-fast [ASSUMED — verify with a local timing run during implementation].

### Pitfall 4: Baseline contrast accidentally succeeding
**What goes wrong:** if per-source identifiers are too similar (e.g., same string with different prefixes), naive cycle detection on raw data might still find the ring, destroying the headline claim. **Avoid:** scenario artifact must give each ring member genuinely disjoint identifiers per source system (account number vs wire BIC/name variant vs KYC registry id) so only the ontology's resolution rules can link them; add an explicit assertion that the baseline run finds zero cycles.

### Pitfall 5: Walkthrough include paths that Phase 14 can't mount
**What goes wrong:** relative snippet paths break when mkdocs mounts docs/. **Avoid:** use repo-root-relative paths in `--8<--` directives (pymdownx.snippets resolves against configured `base_path`; repo root is the safe convention) and note the assumption in the doc header for Phase 14. [ASSUMED — Phase 14 owns mkdocs config; coordinate via a comment in the doc.]

### Pitfall 6: `--live` leaking into always-on CI
**Avoid:** `make example-08` runs deterministic mode only; `--live` gets no Makefile CI wiring (deferred idea explicitly rejected a live CI job).

## Code Examples

### Seeded generator skeleton (mirrors perf/synth discipline)
```python
# Source: pattern from perf/synth/generator.py (verified in repo)
DEMO_SEED = 20260801  # documented; changing it invalidates pinned checksums
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)

def generate(scenario: dict, out_dir: Path) -> None:
    rng = random.Random(scenario["seed"])   # seed lives in scenario.yaml
    # interpret scenario["sources"], scenario["ring"], scenario["noise"] ...
    # write one sqlite3 file per source; all vocabulary from the artifact
```

### Expected-values assertion (example 00 style)
```python
# Source: examples/00-quickstart/run.py:352 (verified)
expected = control["expected"]
assert payload["entity_count"] == expected["entity_count"], payload
```

### Live-mode gating (example 03 style)
```python
# Source: examples/03-harness-portability/run.py (verified)
if args.live:
    # imports deferred here; narration only; no assertions on model text
```

## State of the Art

Not applicable in the ecosystem sense — this phase composes in-repo mechanism. The relevant "current state" facts: v0.1 shipped 2026-07-31 with examples 00–07 green in always-on CI (`make ci` = `ci-core` + `examples`); Phase 11 shipped perf/synth with seed 20260801; live legs are opt-in via `live-legs.yml`. All [VERIFIED: codebase].

## Project Constraints (from CLAUDE.md)

- No-Hardcoding Rule (§6.4): no inline prompts, agent definitions, thresholds, or routing values in code; factory-only agent construction; CI lint enforces.
- Single-writer (§10): only L2 writes L3; generator/example never touch the graph directly.
- Algorithmic ⇄ Semantic Alternation: no LLM imports in `@algorithmic` modules; detection path is purely algorithmic.
- Harness neutrality (§7.3): zero harness imports in `/src`; the demo agent runs via factory + existing mechanism, no harness needed for deterministic mode.
- Examples discipline (§9): runnable end-to-end on reference backends (SQLite graph store, file ArtifactStore), single documented command, README per example, code+artifacts side by side, runs in CI, D-IMPL-52 domain mix (banking for quickstart lineage — D-01 conforms).
- Docstrings cite whitepaper/CLAUDE.md sections; SDK extensions labeled as such.
- Commits at deliverable boundaries; whitepaper-silent gaps become D-IMPL entries, stop and ask Dave.
- Phase reviews via `/gsd-review` per §3.1 at phase end.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 1k–5k entities through L2 assembly completes in CI-acceptable seconds | Pitfall 3 | Reduce counts within the locked band; band floor (~1k) is safe per Phase 11's 1k rung |
| A2 | pymdownx.snippets with repo-root base_path is what Phase 14 will configure | Pitfall 5 | Path prefix edit in one doc when Phase 14 lands — trivial |
| A3 | The skills dispatch surface supports registering a new local callable skill purely via artifacts + example-local callable code (as example 06's `dispatch.expected_output` suggests) | Don't Hand-Roll | If callables must live in /src, the cycle-detection skill's *mechanism* home needs a decision — see Open Question 1 |

## Open Questions

1. **Where does the cycle-detection callable live?**
   - What we know: `src/ccf/skills/callables.py` exists; example 06 dispatches a skill and asserts against `skills.yaml`'s `expected_output`; example code may carry thin generic mechanism.
   - What's unclear: whether a graph-cycle-detection function counts as generic mechanism (fine in example code or even `/src`) or as demo-specific logic. It is domain-free (pure graph algorithm over a typed product), so example-local callable code registered through the catalog is the safest reading — parameters (which relationship type, thresholds) come from `skills.yaml`.
   - Recommendation: planner should read `src/ccf/skills/callables.py` and example 02/06's skill registration before writing the task; default to an example-local callable interpreted via artifact parameters.
2. **Baseline-contrast placement** — one run.py stage (recommended: "Stage 0: raw-data baseline") vs a separate script. Recommend one run.py per D-15's single command.
3. **Generation step shape** — Claude's discretion per CONTEXT; recommend generation as run.py's first stage (self-contained single command) writing into the tempfile working dir, with `generator.py` as a sibling module for walkthrough literal-inclusion.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python + PyYAML + ccf src/runtime | everything | ✓ | in-repo, CI-green | — |
| sqlite3 stdlib | data store | ✓ | stdlib | — |
| LLM provider (Anthropic/Ollama) | `--live` only | opt-in, keyed/local | — | `--live` is optional by design; no CI dependency |

No missing blocking dependencies.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing suite) + examples-as-tests (run.py exit code) |
| Config file | existing repo config; Makefile targets |
| Quick run command | `make example-08` (to be added) |
| Full suite command | `make ci` (= ci-core + examples) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEMO-01 | Store generates deterministically; checksums/shape pinned | in-example assertions (+ optional pytest determinism test mirroring `tests/perf_synth` pattern) | `make example-08` | ❌ Wave 0 |
| DEMO-02 | Baseline finds nothing; governed run finds ring; product/replay pinned | in-example assertions, byte-compare | `make example-08` | ❌ Wave 0 |
| DEMO-03 | Demo runs in always-on CI; walkthrough doc exists with valid include paths | `examples` CI job (existing); doc presence + path check | `make examples` / `make ci` | ❌ Wave 0 (Makefile wiring) |

### Sampling Rate
- **Per task commit:** `make example-08`
- **Per wave merge:** `make examples`
- **Phase gate:** `make ci` green before `/gsd:verify-work`; then `/gsd-review --phase Phase I --all` per CLAUDE.md §3.1 discipline for phase-end review.

### Wave 0 Gaps
- [ ] `examples/08-*/` directory + run.py + artifacts — DEMO-01/02
- [ ] Makefile `example-08` target added to `examples` aggregate — DEMO-03
- [ ] `docs/demo-walkthrough.md` — DEMO-03
- [ ] (optional) determinism pytest mirroring the perf-synth pin pattern

## Security Domain

Internal demo example, no network/auth surface, no user input, no installs.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | policy-regime artifacts exercise fabric-level policy, per existing mechanism |
| V5 Input Validation | yes | typed contracts at every boundary (Pydantic `extra=forbid`) — existing mechanism |
| V6 Cryptography | no | content hashing via existing `ccf.contracts.canonical` |

Threat note: SQLite queries in the ingest path should use parameterized queries as a hygiene habit even though all inputs are self-generated.

## Sources

### Primary (HIGH confidence — direct codebase inspection, 2026-08-01)
- `examples/00-quickstart/run.py`, `examples/01-agent-basics/run.py`, `examples/03-harness-portability/run.py`, `examples/06-decision-replay/run.py`
- `perf/synth/generator.py` + `perf/synth/artifacts/`
- `Makefile` (examples targets, `ci` aggregate), `.github/workflows/ci.yml`, `.github/workflows/live-legs.yml`
- `src/ccf/` module layout (agents, skills, llm, signal, assembly, contracts)
- `CLAUDE.md`, `.planning/REQUIREMENTS.md`, `12-CONTEXT.md`, `.planning/config.json`

### Secondary / Tertiary
- pymdownx.snippets include-path behavior: [ASSUMED] from training knowledge; low-risk (Phase 14 owns config).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — everything verified in-repo; zero installs
- Architecture: HIGH — direct composition of verified example patterns
- Pitfalls: HIGH/MEDIUM — determinism and No-Hardcoding pitfalls verified; CI-timing (A1) and snippets-path (A2) assumed

**Research date:** 2026-08-01
**Valid until:** stable — in-repo facts hold until Phase 13/14 modify the examples/docs surface
