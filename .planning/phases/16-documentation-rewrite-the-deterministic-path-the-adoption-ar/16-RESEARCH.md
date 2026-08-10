# Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument - Research

**Researched:** 2026-08-09
**Domain:** Adopter-facing examples suite + published documentation tree, against the post-Phase-15.4 SDK surface
**Confidence:** HIGH for tree inventory and API surfaces (everything was read or executed against the tree at `84f4501`); MEDIUM for the LangGraph client leg and the DGX opt-in CI leg (no in-tree precedent exists for either)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

**These are LOCKED. Do not re-derive, re-litigate, or offer alternatives.** Where
this research finds a tension between a locked decision and the tree, it is filed
as a finding under `## Open Questions for the Planner`, not resolved.

### Locked Decisions

*Copied verbatim from `16-CONTEXT.md` `<decisions>`.*

**Structure and sequencing**

- **D-01: Four sections; Phase 16 ships 1–3, Phase 17 ships 4.** Verified at the
  code level that Modes 2/3 are **additive** and do not invalidate Sections 1–3:
  - `src/ccf/operators/base.py:120` — the `Operator` Protocol docstring already
    names swarm realization as permitted (INV-CH7-32): *"Realization is
    unconstrained: code, SQL-backed, or swarm — the algebra is the determinism
    surface, and conformance to this Protocol is the whole obligation."* The seam
    Sections 1–3 depend on does not change.
  - `apply()` requires *"no writes, no I/O **against the graph**, no clock
    reads"* — the line was drawn to permit a non-graph call, not forbid it.
  - `PushableOperator` (`base.py:162`) is the **shipped precedent** for the
    extension shape: Phase 15.2 added a whole capability as a *separate*
    Protocol so *"an existing third-party operator that never heard of pushdown
    still satisfies `Operator` unchanged."*
  - `ModelVersionRecord` (`src/ccf/replay/record.py:340`) already carries
    `assembly_mode` with a Mode-1 default and a docstring stating Mode 2 supplies
    the real version when packaging lands. `harness_trace` was added the same
    additive way in I.3.
  - Whitepaper §7.10: the same replay record format extends across all three
    modes *"without requiring a different replay infrastructure per mode."*
- **D-02: Rule the Mode 2 attachment point during Phase 16 planning.** One
  `D-IMPL-NN`, **no code**: confirm Mode 2 packaging attaches **above** `serve()`
  rather than within it. Evidence already points there — whitepaper §7.6 makes
  the LLM rendering *"a presentation layer over the substrate rather than the
  artifact a supervisor inspects"* — but Section 1 teaches `serve()` as one
  expression with no branch reaching delivery without a recorded decision (a
  Phase 04 decision), so the shape must be settled before that prose is written.
  This is the only fabric-adjacent act in Phase 16, and it produces a decision
  entry, not a diff.

**Use case and data**

- **D-03: KYC / UBO resolution and refresh is the use-case spine.**
- **D-04: FIBO stores are an enterprise source CCF reads at L1 — never loaded
  wholesale into CCF's graph.** Read side = L1 ingress adapters (CDC, MCP client,
  file/stream) plus `src/ccf/mcp/acquisition.py` for L4/L5 decision-time
  acquisition; **none of these are registry "backends."** Write side = CCF's own
  Context Graph (L3), which is what the six backends are. `boot()` takes
  `backend: str` — required, no default, **exactly one**. Read store and write
  store are independent. *Selective assembly*, never *wholesale replication*.
- **D-05: Temporal signal is authored as an L1 observation stream, as today.**

**Backends**

- **D-06: One parameterized runner, matrix-proven across all six.** One example
  body; backend selected by artifact or env. A CI matrix runs the suite across
  `sqlite`, `memory`, `postgres`, `neo4j`, `mongo`, `fluree` and asserts
  equivalent Context Products.
  - **CI split per D-10/D-11:** `sqlite` + `memory` in always-on CI
    (deterministic, offline); the four DGX databases as an **opt-in live-legs
    job**. Always-on CI must stay network-free.
  - **Connection settings** come from `compare_backends.py`: Fluree
    `192.168.4.76:8090` (ledger `fibo:main`), Mongo `192.168.4.76:27017`, Neo4j
    `bolt://192.168.4.76:7687`, Postgres `192.168.4.76:5432` (db `parkavedb`).
    All env-overridable; **no credential may enter the tree.**

**Examples suite**

- **D-07: Greenfield the examples; rewrite the docs.** Retire `examples/00`–`08`
  and build the sections fresh against the new seam. Those examples are the
  snippet source of record for the entire `public/` tree, so all published pages
  move in the same phase. There is no partial state.
- **D-08: Existing requirements re-home into the new suite.** DEMO-01..03 and
  EXAM-01..05 map onto whichever new examples cover them. Phase 16 additionally
  mints DOCS-07..NN.
- **D-09: All three harnesses stay in examples.** Claude Agent SDK, Google ADK,
  and LangGraph.

**Documentation**

- **D-10: The adoption argument gets its own page, naming alternatives.** RAG over
  a vector store, hand-rolled context assembly, a semantic layer plus prompt
  templates — and what breaks: no replay, no policy binding at assembly, no
  lineage to a passage, no staleness measure. The worked demonstration is the UBO
  question, "Who ultimately owns Acme?"
- **D-11: Snippet legibility is achieved by structural separation in the example
  sources.** Each example physically separates the **CCF call spine** from
  **deployment code** (the projection Π, domain artifacts, scenario setup) into
  distinct, separately-markered regions, visible to a repo reader. No new marker
  vocabulary beyond Phase 14's D-07 named markers.
- **D-12: G-01's framing defect is fixed by construction, not by editing.**
  Section 1 is deterministic and agent-free. Specifically retired: the Concepts
  data-context page opening on *"how does an agent get at first-party records"*,
  the buried line-133 acknowledgement that the SDK ships no agents, and the
  absence of any how-to for deterministic Context Product assembly.

### Claude's Discretion

- Section-to-example mapping (how many examples per section, and their
  boundaries) — planner-level, given the section definitions above.
- Whether the six-backend matrix is one CI job or several.
- How DEMO-01..03's fraud-ring scenario re-homes given the KYC/UBO spine.
- Nav structure within the four sections, inside Phase 14's Diátaxis frame
  (D-15..D-18), which stands unless a section demands otherwise.

### Deferred Ideas (OUT OF SCOPE)

- **A credit-memo example** — deferred by Dave to a later phase (2026-08-09).
- **Tier-3 raw external sources** — reading an enterprise estate at *operator
  time* without it ever landing in L3. Fabric work; its own roadmap entry.
- **Pattern 5 / `src/ccf/unstructured/`** — D-IMPL-08 RESOLVED 2026-07-25, never
  built.
- **Section 4 itself** — Mode 2 (`llm_packaged`) and Mode 3 (`swarm_assembled`).
  Phase 17.
- **A lint for mis-pointed snippet includes** (SURFACE-AUDIT A-5) — named as this
  phase's concern; may still land as its own follow-up.
- **`make ci` does not reach `tools/`** though CI does — three suites there fail
  pre-existing.
- **DI-15.4-05 / F2** — the public-vs-private adapter surface, and
  `substrate_vocabulary` deriving from in-tree adapters only. Awaiting Dave's
  ruling; touches the "write a graph backend adapter" how-to this phase rewrites.
</user_constraints>

---

## Project Constraints (from CLAUDE.md)

Directives extracted from `./CLAUDE.md` that bind this phase. The planner must
verify each plan against these; they carry the same authority as CONTEXT.md's
locked decisions.

| # | Directive | Source | How it binds Phase 16 |
|---|---|---|---|
| C-1 | **No-Hardcoding Rule.** No prompt or system-instruction string literal in code; no agent/task definition in code; no task graph, routing table, threshold, approval rule, or skill grant as a code constant. Applies to `/src`, `/runtime` **and `/examples`**. | §6.4, §11 | Every new example is code + artifacts side by side. CI-enforced by `cinv01a/b/c` over `RULE_TREE_SCOPE = ("src","runtime","examples","tests")`. **`tests/` is in scope** — the relocated assertion modules must not carry domain values either. |
| C-2 | **An example whose code would still run meaningfully with its artifacts deleted has violated the rule.** | §6.4, §9 | The greenfield examples must be *thinner* than today's, not richer. |
| C-3 | **Harness neutrality.** Zero harness imports in `/src`; adapters only under `/runtime/adapters/<harness>/`. | §1, §7.3, §11 | Section 2 and 3 harness legs live in `examples/`, and consume `/runtime/adapters/`. `cinv02-harness` guards `src`+`runtime` only — an example may import a harness SDK. |
| C-4 | **Every example declares a single documented run command**; a broken example is a broken build; examples run in CI. | §9 | Criterion 1's "runs end-to-end by a single documented command" is already the standing rule, realized as `make example-NN`. |
| C-5 | **README per example** stating what it demonstrates, which whitepaper and CLAUDE.md sections it exercises, and what to change first. | §9 | The shipped template is seven headings, asserted by `run.py` PASS 4 in `examples/external/00-hello-context` and by `test_ext00_serve_output.py::test_the_readme_keeps_its_seven_template_headings`. See §C-3 below. |
| C-6 | **Horizontal mix of domains across the suite** (D-IMPL-52). No example is a domain pack; everything domain-specific lives in definition artifacts. | §9 | D-03 makes KYC/UBO the *spine*, not the only domain. The planner must decide how many examples share the KYC domain without turning the suite into a domain pack — this is a real tension, see Risks R-6. |
| C-7 | **Whitepaper never published**; cite section numbers and titles only, never body text. | §11, Phase 14 D-18 | `tools/publish_scan.py` `pub01-whitepaper-shingle` (N=10 words) enforces it, no allowlist. |
| C-8 | **Surface gaps; do not paper over them.** Whitepaper-silent → `D-IMPL-NN` and stop. | §11, §15 | D-02 is exactly this shape and is the only such act sanctioned in this phase. |
| C-9 | **Phase review protocol** — cross-AI panel (`/gsd-review --all`) is unsubstitutable and runs on shipped code at close; single-agent review is additive; verify every finding; fix blocking in-phase; then present to Dave. | §3.1 | The phase's own close, not a plan deliverable — but the planner should not schedule the gate before the panel. |

---

## Summary

Phase 16 is a **coordinated retirement**: nine example directories plus one
external example are the snippet source of record for 15 of the 41 published
pages, via **102 snippet-include directives**, and the greenfield decision (D-07)
moves all of them at once. The single most load-bearing artifact this research
produces is the page→example dependency table in §A.2 — every row is a page that
goes red under `make docs-strict` the moment its source example is deleted,
because `pymdownx.snippets` runs with `check_paths: true` and `mkdocs.yml` sets
`strict: true`. There is no partial state, mechanically, not merely by policy.

The mechanism the phase builds on is in good shape. The Phase 15.4 backend
registry seam is real and executable: `ccf.graph.registry.declared_names()`
returns seven names in a dev checkout, `resolve(name)` hands back a typed
connection contract per adapter, `DeploymentManifest.backend` is a free lowercase
string checked against the registry at load, and `load_and_boot(...,
connection=...)` takes the per-adapter mapping keyed on that adapter's own config
fields. A parameterized runner is a lookup, exactly as D-06 asserts. The
precedent to mirror already exists and is not hypothetical:
`tests/conformance/test_graphstore.py::graph_backend` parametrizes seven backends
with per-backend pytest marks over `tests/conftest.py::fabric_boot`, whose
`location` mapping is keyed on each adapter's config-model field names. The
example runner should be its structural twin.

Three findings deserve the planner's attention before any plan is written.
**First, the FIBO dataset does not contain a multi-hop ownership chain.**
`ownershipPercent` is an attribute of the *Party entity*, not of the ownership
relationship, and every `hasOwnershipInterestIn` edge runs Party → Corporation in
one hop; no corporation owns another. The adoption argument's worked
demonstration — "traversing an ownership chain, aggregating percentages across
hops" — is not answerable from the data as it stands, so the phase owes a
deliberate data extension (Dave's own instruction allows it: *"or be provided
additional data to support"*). **Second, always-on CI already runs Postgres,
Neo4j, Mongo and Fluree as blocking service-container legs** in the `test` job,
with `CCF_REQUIRE_*=1` turning a skip into a failure — so "always-on CI is
network-free" is true in the sense of *no external network*, and localhost
containers are already the established pattern. D-06 locks sqlite+memory as the
always-on example matrix and the four DGX databases as opt-in; the planner should
know the container path exists as a *third* option it is not authorized to choose
without a ruling. **Third, `public/`'s Gate-2 prose is already correct** — plan
15.1-20 swept it — so criterion 8 is about not *reintroducing* the defect in
newly-written pages, plus retiring one stale heading in
`examples/06-decision-replay/README.md:189` ("Gate 2 independence") that dies with
the example anyway.

**Primary recommendation:** treat the page→example dependency table (§A.2) as the
phase's spine — decompose plans so that every wave leaves `make docs-strict`
green, which means an example and every page that includes from it move in the
same wave, and the nav entry, the page, and the example are one unit of work.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Deterministic Context Product assembly (Section 1) | **Deployment code in `examples/`** (L1→L6 call spine) | `src/ccf` fabric | The SDK ships mechanism; the spine is what an adopter writes. `run.py` *is* the teaching artifact. |
| Backend selection / parameterization | **`ccf.graph.registry` + `DeploymentManifest.backend`** | example `run.py` (`--backend`), `connection=` mapping | Selection is a name in a manifest (registry docstring, explicit ruling). The runner supplies only the connection mapping. |
| Zero-CCF-dependency client (Section 2) | **`examples/<sec2>/client_*.py`** — third-party MCP client only | `runtime/ccf_runtime/mcp/experience.py` server side | The claim is an *absence* in the client's import list; the server is CCF's. |
| Harness binding (Sections 2 & 3) | **`runtime/ccf_runtime/adapters/<harness>/`** | example legs | CLAUDE.md §7.3: adapters only, never core. |
| Agentic skills within CCF (Section 3) | **`ccf.skills` catalog/grants/dispatch + `ccf.agents` factory** | Control Plane artifacts | Agents are artifacts, not code (§6.1). |
| Snippet extraction | **`pymdownx.snippets` named markers in example sources** | `mkdocs.yml` | D-07: named markers, never line ranges. |
| Publication gate | **`tools/publish_scan.py` + `mkdocs build --strict`** | `make docs-strict`, `ci.yml docs` job | Default-deny by existence; exit code is the only signal. |
| CI matrix execution | **`.github/workflows/*.yml` + `Makefile`** | `pytest` marks in `pyproject.toml` | The Makefile mirrors CI command-for-command (D-10). |
| Adoption argument evidence | **`public/` prose citing shipped mechanism** | `ccf.replay`, `ccf.halflife`, `ccf.operators.categories.PolicyFilter`, `PassageAnchor` | The page must cite mechanism, not assert. |

---

## A. The Retirement Inventory

### A.1 The ten examples, as they stand

Every row verified by directory listing and by reading the module docstring. Test
modules verified present under `tests/examples/`.

| Example | Demonstrates | Run command | Artifacts | Test module(s) | `run.py` LoC | Markers |
|---|---|---|---|---|---|---|
| `examples/00-quickstart` | Smallest fabric end-to-end: manifest → L1 ingest → four-category operators → project → 3 gates → replay record → serve. "Hello, Context Product." | `make example-00` | 16 YAML | `test_quickstart_output.py` (322) | 398 | 7 |
| `examples/01-agent-basics` | Declare an agent from an archetype via artifact; Agent Factory; six specialization axes; `λ_c` half-life table + `D_c` debt evaluation | `make example-01` | 22 YAML | `test_agent_basics_output.py` (427) | 531 | 5 |
| `examples/02-skilling` | Channel-2 skilling: catalog, grant, exercise, refusal on an impermissible grant, revoke; all in replay | `make example-02` | 21 YAML | `test_skilling_output.py` (437) | 609 | 5 |
| `examples/03-harness-portability` | One agent definition under three harnesses (Claude Agent SDK, ADK, LangGraph); deterministic + opt-in live legs | `make example-03` (`--mode deterministic`) | 18 YAML + `agents/` | `test_harness_portability_output.py` (419) | 711 (+ `legs/{deterministic,live,ollama_client}.py`) | 9 (+1 in `legs/deterministic.py`) |
| `examples/04-cross-process` | `ContextAssemblyAgent` in a subprocess; one product over **MCP and A2A**; Control Plane admission; tampered-envelope refusal | `make example-04` | 28 YAML | `test_cross_process_output.py` (461) | 521 (+ `producer_child.py` 597) | 9 |
| `examples/05-workflow-hitl` | Workflow state machine, ApprovalGate suspend/resume, exception path, ReviewQueue, HITL in replay | `make example-05` | 19 YAML | `test_workflow_hitl_output.py` (846) | 875 | 11 |
| `examples/06-decision-replay` | Replay a prior decision: resolve snapshot, policy bundle, agent version, skill-set, prompt-artifact versions; version sensitivity | `make example-06` | 30 YAML | `test_decision_replay_output.py` (808) | 1179 | 5 |
| `examples/07-artifact-store-mcp` | Swap file-backed ArtifactStore for the MCP-backed reference store; nothing else changes | `make example-07` | 16 YAML | `test_artifact_store_output.py` (369) | 636 (+ `mcp_store_child.py`) | 4 |
| `examples/08-e2e-demo` | DEMO-01..03: synthetic generator, ingest → graph → product → agent, byte-compared narrated transcript | `make example-08` | 26 files (incl. `expected_output.txt`) | `test_e2e_demo_output.py` (589), `test_demo_generator.py` (136) | 1164 (+ `generator.py` 431) | 0 |
| `examples/external/00-hello-context` | EXAM-04/05: authenticated MCP front door; **four zero-CCF-import client legs** (bare MCP, Anthropic SDK, Google ADK, Claude Desktop `.mcp.json`); live-captured fixtures + replay server | `make example-ext-00` | 17 YAML + `fixtures/` | `test_ext00_serve_output.py` (465), `test_ext00_hardening.py` (850), `test_ext00_fixture_schemas.py` (186) | `run.py` 790, `serve.py` 743, `replay_server.py` 400, 3 client legs | 3 (in `client_bare.py`) |

Additional test modules under `tests/examples/` **not tied to a single example**
and which must be re-homed rather than retired:

| Module | LoC | What it holds | Disposition |
|---|---|---|---|
| `test_gate_two_divergence.py` | 279 | The E2 binder refusal exercised at every example site; asserts the two-authored-document comparison. Its docstring already carries the corrected assembly-path-integrity wording. | **Rewrite against the new suite.** This is criterion 8's positive evidence. |
| `test_artifact_schema_headers.py` | 174 | `$schema` header ↔ class agreement over example artifacts | Rewrite; auto-arms per directory. |
| `test_surface_audit.py` | 303 | ERGO-03's mechanical-line-count audit over `examples/` (`tools/measure_examples.py` before/after) | **Decide.** Its `before/` baseline is Phase 15's; a greenfield suite makes the comparison meaningless. See Open Question Q-4. |
| `test_demo_generator.py` | 136 | `08-e2e-demo/generator.py` | Retires with example 08 unless the generator re-homes. |

**Retirement totals:** 10 example directories, ~213 artifact documents,
~7,000 lines of `run.py`/driver code, and ~5,000 lines of `tests/examples/`
assertions.

### A.2 The page→example dependency table ⟵ *the load-bearing artifact*

Generated mechanically from `public/**/*.md` by matching `--8<-- "…"` directives
whose target starts with `examples/`. **102 include directives across 20
(page, example) pairs across 15 pages.**

| Published page | Sources from | Includes |
|---|---|---|
| `tutorial/adopters-guide.md` | `examples/00-quickstart` | 9 |
| `tutorial/adopters-guide.md` | `examples/01-agent-basics` | 5 |
| `tutorial/adopters-guide.md` | `examples/02-skilling` | 6 |
| `tutorial/adopters-guide.md` | `examples/05-workflow-hitl` | 9 |
| `tutorial/adopters-guide.md` | `examples/06-decision-replay` | 3 |
| `tutorial/adopters-guide.md` | `examples/external/00-hello-context` | 3 |
| `tutorial/demo-walkthrough.md` | `examples/08-e2e-demo` | 14 |
| `how-to/compose-a-workflow-with-hitl.md` | `examples/05-workflow-hitl` | 14 |
| `how-to/run-agents-cross-process.md` | `examples/04-cross-process` | 10 |
| `how-to/bind-a-harness-adapter.md` | `examples/03-harness-portability` | 6 |
| `how-to/grant-and-revoke-a-skill.md` | `examples/02-skilling` | 6 |
| `how-to/swap-the-artifact-store.md` | `examples/07-artifact-store-mcp` | 6 |
| `reference/artifacts/control-plane-artifacts.md` | `examples/00-quickstart` | 3 |
| `reference/artifacts/product-registration.md` | `examples/00-quickstart` | 2 |
| `reference/artifacts/agent-definitions.md` | `examples/01-agent-basics` | 1 |
| `reference/artifacts/prompt-artifacts.md` | `examples/01-agent-basics` | 1 |
| `reference/artifacts/skill-catalog.md` | `examples/02-skilling` | 1 |
| `reference/artifacts/skill-grants.md` | `examples/02-skilling` | 1 |
| `reference/artifacts/task-definitions.md` | `examples/05-workflow-hitl` | 1 |
| `reference/artifacts/workflow-definitions.md` | `examples/05-workflow-hitl` | 1 |

**Inverted — which pages die with each example:**

| Example | Pages that go red on its deletion |
|---|---|
| `00-quickstart` | `tutorial/adopters-guide.md`, `reference/artifacts/control-plane-artifacts.md`, `reference/artifacts/product-registration.md` |
| `01-agent-basics` | `tutorial/adopters-guide.md`, `reference/artifacts/agent-definitions.md`, `reference/artifacts/prompt-artifacts.md` |
| `02-skilling` | `tutorial/adopters-guide.md`, `how-to/grant-and-revoke-a-skill.md`, `reference/artifacts/skill-catalog.md`, `reference/artifacts/skill-grants.md` |
| `03-harness-portability` | `how-to/bind-a-harness-adapter.md` |
| `04-cross-process` | `how-to/run-agents-cross-process.md` |
| `05-workflow-hitl` | `tutorial/adopters-guide.md`, `how-to/compose-a-workflow-with-hitl.md`, `reference/artifacts/task-definitions.md`, `reference/artifacts/workflow-definitions.md` |
| `06-decision-replay` | `tutorial/adopters-guide.md` |
| `07-artifact-store-mcp` | `how-to/swap-the-artifact-store.md` |
| `08-e2e-demo` | `tutorial/demo-walkthrough.md` |
| `external/00-hello-context` | `tutorial/adopters-guide.md` |

**`tutorial/adopters-guide.md` alone depends on six of the ten examples (35
includes).** It cannot be moved incrementally. It is the phase's single hardest
scheduling constraint.

**Non-include references also needing re-cut** (prose naming a path, invisible to
`check_paths`, so they rot *silently* — this is exactly SURFACE-AUDIT A-5):

| Page | Prose-only refs | Targets |
|---|---|---|
| `tutorial/demo-walkthrough.md` | 6 | incl. `tests/examples/test_e2e_demo_output.py` |
| `tutorial/adopters-guide.md` | 3 | `tests/examples/test_{agent_basics,workflow_hitl,decision_replay}_output.py` |
| `how-to/swap-the-artifact-store.md` | 2 | `tests/examples/test_artifact_store_output.py` |
| `how-to/bind-a-harness-adapter.md` | 2 | `tests/examples/test_harness_portability_output.py` |
| `how-to/compose-a-workflow-with-hitl.md` | 2 | `tests/examples/test_workflow_hitl_output.py` |
| `how-to/grant-and-revoke-a-skill.md` | 1 | — |
| `how-to/run-agents-cross-process.md` | 1 | — |

**Pages with no example dependency (26 of 41)** — these do not break on
retirement, but most are still in scope for A-3 (stale pre-15 surface), G-01
(criterion 2), and criterion 9. They are: `index.md`, `charter.md`, the 5 pillar
pages, `concepts/{invariants,replay-anatomy,whitepaper-index}.md`, the 12
`reference/protocols/*.md`, `reference/{http-api,performance}.md`, and
`how-to/{security-and-deployment,write-a-graph-backend-adapter}.md`.

Diagrams: 11 `.mmd` under `public/diagrams/`, embedded by Concepts pages under a
**bijection asserted by `tools/docs_tests/test_diagram_coverage.py`** — every
`.mmd` has exactly one home page. Restructuring Concepts must preserve that
bijection or the test fails.

### A.3 The `required_operator_keys` vs `operators_invoked` sites (criterion 8 / A-4)

Nine sites in `tests/examples/`. These are the checks SURFACE-AUDIT A-4 says must
**not** be promoted as independence proofs.

| Module | Line | Shape |
|---|---|---|
| `test_quickstart_output.py` | 208 | `set(declared.required_operator_keys) == set(result.operators_invoked)` |
| `test_agent_basics_output.py` | 225 | same |
| `test_skilling_output.py` | 240 | same |
| `test_harness_portability_output.py` | 235 | same |
| `test_artifact_store_output.py` | 259 | same |
| `test_decision_replay_output.py` | 287 | same |
| `test_e2e_demo_output.py` | 333 | same |
| `test_cross_process_output.py` | 268 | consumer-side variant (**this one is a genuinely independent statement** per SURFACE-AUDIT 15-18) |
| `test_ext00_serve_output.py` | 275 | consumer-side variant |

The honest framing is already written into the tree and should be carried
forward verbatim in spirit —
`tests/examples/test_quickstart_output.py:196-204`:

> *"…the executed set traces to `projection-requirements.yaml` and the declared
> set to `product-class.yaml`, two documents an author can edit apart, held
> together by `refuse_operator_set_divergence`. **Still not proven here:** that
> the two were authored rather than copied. A deployment that reads one document
> into the other collapses the binder…"*

---

## B. The Parameterized Runner

### B.1 The Phase 15.4 backend registry seam — verified public API

Executed against the tree (`PYTHONPATH=src:runtime python -c …`), not read from
docs.

```python
from ccf.graph.registry import declared_names, resolve
declared_names()  # -> frozenset of adapter names, from disk + entry points
resolve(name)     # -> ResolvedBackend(registration, version, distribution)
```

`ccf.graph.registry.__all__` = `AdapterPin`, `BackendRegistration`,
`BackendStore`, `DuplicateBackendName`, `InvalidBackendConfig`,
`ReservedBackendName`, `ResolvedBackend`, `ResolvedSecret`, `UnknownBackend`,
`declared_names`, `resolve`, `validate_connection`.

**Observed output on this checkout** (seven names — the seventh is the
out-of-tree fixture `make install` installs, and it is *always-on* by ruling):

| Name | Config model | Config fields | Secret fields | Distribution |
|---|---|---|---|---|
| `sqlite` | `SqliteConnection` | `database_path` | — | `ccf` |
| `memory` | `MemoryConnection` | *(none)* | — | `ccf` |
| `postgres` | `PostgresConnection` | `dsn`, `schema_name` | — | `ccf` |
| `neo4j` | `Neo4jConnection` | `uri`, `partition` | — | `ccf` |
| `mongo` | `MongoConnection` | `uri`, `partition` | — | `ccf` |
| `fluree` | `FlureeConnection` | `url`, `partition` | **`bearer_token`** | `ccf` |
| `demo` | `DemoConnection` | `graph_name` | — | `ccf-demo-adapter` (out-of-tree) |

Two discovery sources: **built-ins by reading module stems off disk** inside
`src/ccf/graph/backends/` (a disk read, never an import), and **third parties via
the `ccf.graph_backends` entry-point group** (`BACKEND_ENTRY_POINT_GROUP`).
`resolve()` imports exactly one adapter. `declared_names()` is fail-closed on
duplicate / reserved / malformed names.

**`boot()`** — `src/ccf/boot.py:222`:

```python
def boot(*, backend: str, connection: Mapping[str, object] | None = None,
         secrets: Mapping[str, ResolvedSecret] | None = None,
         registry: ControlPlaneProtocol,
         resolution_spec_key: str, resolution_spec_version: str,
         policy_bundle_key: str, policy_bundle_version: str) -> FabricHandle
```
`backend` is required with no default and no inference — stated as a refusal in
the docstring.

**`load_and_boot()`** — `src/ccf/deployment/manifest.py:417`:

```python
def load_and_boot(manifest_path: str | Path, *, registry: ControlPlaneProtocol,
                  connection: Mapping[str, object] | None = None,
                  tenant_id: str | None = None) -> BootedFabric
```
Returns `BootedFabric(handle, pins, tenant_id, artifacts, survivor_cap)`.

**Manifest field** — `src/ccf/controlplane/artifacts.py:1044`:
`backend: str = Field(pattern=r"^[a-z][a-z0-9_]*$")` — a **shape** rule only.
Membership is checked at load against `declared_names()`. The six-name `Literal`
was removed by plan 15.4-06.
`backend_secrets: tuple[SecretReference, ...]` names *(adapter config field,
environment variable)* pairs — the value never appears in the document.

**`ccf backends list`** → `GET /backends` → `{"backends": [sorted names]}`.
`runtime/ccf_runtime/cli/commands/backends.py` deliberately holds **no local
generation path**: it returns a `RequestSpec` and travels the route like any
client, including under `--local`. `GET /backends` answers `503` on a packaging
conflict.

### B.2 What the runner binds to, and the precedent to mirror

**Three parameterization points, in order of authority:**

1. **`DeploymentManifest.backend`** — one string per manifest document. A
   manifest is content-hashable Control Plane state, so this value **cannot** be
   env-substituted inside the document without destroying the pin. The honest
   shapes are: (a) one thin manifest per backend in the same `artifacts/`
   directory (`manifest-<backend>.yaml`), all naming the same artifact documents;
   or (b) one manifest and a `--backend` flag that selects among (a). Both keep
   every manifest a true, hashable record of what that run put in force.
   *Constraint:* `load_and_boot` preflights that **every entry's document lies
   inside the deployment**, so the shared artifact set must be reachable by
   relative path from each manifest — co-location in one `artifacts/` directory
   satisfies this.
2. **`connection=` mapping** — keys are the *adapter's own config-model field
   names*, not `boot`'s. This is caller-supplied, therefore the natural home for
   env-derived values and the one place a DSN/URI legitimately lives.
3. **`backend_secrets`** — only `fluree` declares a secret field
   (`bearer_token`). Postgres/Neo4j/Mongo carry credentials inside the DSN/URI,
   which arrives through (2) and therefore never enters the tree.

**Existing precedent to mirror — this is not hypothetical:**

- `tests/conformance/test_graphstore.py::graph_backend` (line 47) —
  `@pytest.fixture(params=[sqlite, memory, demo, postgres(mark), neo4j(mark),
  mongo(mark), fluree(mark)])`. Its docstring states the property the example
  matrix wants: *"not one test body below changed, and no test body knows which
  substrate it is running on. That is what makes the suite evidence of parity
  rather than two suites that happen to agree."*
- `tests/conftest.py::fabric_boot` (line 294) — the per-backend `location`
  mapping built from each adapter's config field names, with `postgres` getting a
  fresh schema per boot, `neo4j`/`mongo`/`fluree` a fresh `partition`, `memory` an
  **empty mapping**, `sqlite` a tmp file. This is exactly the shape the example
  runner's connection resolver should take.
- `examples/03-harness-portability/artifacts/live.yaml` — the precedent for an
  **opt-in-leg configuration artifact deliberately kept out of the manifest**:
  *"Naming it in the manifest would make the CI leg parse and hand back
  configuration for a mode it never enters."* The DGX connection defaults belong
  in an artifact of this shape, env-overridable, no credentials.

**What equivalence can be asserted across backends, verified from the contracts:**

`ContextProductContract` fields are `schema_name`, `schema_version`, `plan_id`,
`tenant_id`, `temporal_boundary`, `expires_at`, `ttl_anchor`, `lineage`,
`payload`. `ProductLineage` is `operators_invoked`, `policy_bundle_versions`,
`graph_snapshot_at`. **No field is substrate-dependent**, and `expires_at` is
derived from an authored instant in `decision.yaml` rather than a wall clock. So
`content_hash(product)` byte-identity across all six backends is a defensible,
strong assertion.

⚠ **The replay record is NOT byte-identical across backends, by design.**
`PolicyBindingsSnapshot` carries `graph_adapter`, `graph_adapter_version` and
`graph_secret_refs` as of plan 15.4-08 (`src/ccf/replay/record.py:283-285`). The
matrix must assert equivalence on the **served Context Product**, and assert the
replay record's *non-adapter dimensions* separately. A plan that says "byte-
identical replay records across six backends" will fail, and would be wrong to
"fix" by dropping the adapter pin.

### B.3 CI split — what exists today

`make ci` = `ci-core` (`lint typecheck test`) + `examples` + `docs-strict`.
`make examples` = `example-00` … `example-08` + `example-ext-00` (ten targets).

**`.github/workflows/ci.yml` has four jobs**: `lint`, `test`, `examples`, `docs`.

| Job | Substrate access | Blocking |
|---|---|---|
| `lint` | none | yes — `pytest tools/lints/tests`, `python -m tools.lints --all`, `mypy` |
| `test` | **postgres:16, neo4j:5-community, mongo:7, fluree/server:4.1.4 as service containers**, each with `CCF_REQUIRE_*=1` so a skip is a failure | yes |
| `examples` | **none** — `make examples` only, plus `CCF_REQUIRE_HARNESSES=1` | yes |
| `docs` | none — `pytest tools/publish_scan_tests tools/docs_tests`, then `make docs-strict`, then artifact upload | yes |

**`.github/workflows/live-legs.yml`** is `workflow_dispatch` + one weekly `cron`.
Jobs: `examples-live-ollama` (dispatch-only guard), `examples-live-anthropic`
(dispatch-only, `secrets.ANTHROPIC_API_KEY` with fail-fast), `fluree-drift`
(floating `4.1` tag, answers both triggers). **This is the file a DGX opt-in job
belongs in**, and the two guarded jobs are the exact template: an `if:
github.event_name == 'workflow_dispatch'` guard plus a fail-fast secret
precondition step.

**Where credentials come from today, and what keeps them out of the tree:**
- CI service containers use *published test credentials in the workflow file*
  (`ccf_test_password`) — acceptable because the container is ephemeral and
  localhost-only. **This pattern must not be copied for the DGX**, whose
  credentials are real.
- Live legs use `${{ secrets.ANTHROPIC_API_KEY }}` with a fail-fast presence
  check and `::error::` guidance. This is the DGX pattern.
- In-fabric, `backend_secrets: [{field, env_var}]` + `ResolvedSecret` +
  `canonical_bytes` **refusing `SecretStr` outright** means a credential cannot be
  content-hashed into an artifact even by accident.
- Makefile pattern for a leg: `CCF_TEST_<X>_URI ?= <localhost default>` +
  `CCF_REQUIRE_<X>=1` + `-m <marker> -rs`. Registered markers in
  `pyproject.toml`: `postgres`, `chroma`, `neo4j`, `mongo`, `fluree`,
  `conformance`, `crossproc`, `harness`.

**Operational note carried in STATE.md:** the local mongo container is on **port
27019, not 27017** — the wrong port *hangs*; use `CCF_TEST_MONGO_URI`. And the
fluree leg is 37 tests, not 38.

### B.4 FIBO / KYC / UBO data — verified contents and the gap

`/home/parkave/fluree/examples/fibo/` (outside the repo):

| File | Shape |
|---|---|
| `mongo-entities.json` | **JSONL, 14 lines** (not a JSON array — `json.load` fails) |
| `mongo-relationships.json` | **JSONL, 11 lines** |
| `fibo-instances.json` | SPARQL results JSON — flat `{s,p,o}` triples |
| `compare_backends.py` | Connection settings + per-substrate query shapes |
| `load_{neo4j,postgres,mongo}.py`, `fluree_to_mongo.py` | Per-substrate loaders |

Entities (14): 6 `Corporation` (Acme Corporation, Beta Holdings LLC, Gamma Bank
AG, Delta Private Equity Fund LP, **Acme Global Trading Corporation**, **Beta
Investment Holdings**, Omega Securities Ltd — 7 by label, 6 by CONTEXT's count),
4 `Party` (John Smith, Jane Doe, Hans Müller, Sarah Chen), 3 `Address`.
Entity keys observed: `_id`, `id`, `types`, `source`, `label`, `legalName`,
`fullName`, `lei`, `jurisdiction`, `entityStatus`, `clientType`,
`onboardingDate`, `riskRating`, `kycStatus`, `nationality`, `dateOfBirth`,
`role`, `ownershipPercent`, `attrs`.

Relationships (11): `isRelatedTo` ×6, `hasOwnershipInterestIn` ×4,
`hasControllingInterestIn` ×1. **Edge keys are only `from`, `to`, `type`,
`source`, `_id`.**

⚠ **FINDING F-1 — `ownershipPercent` is an entity attribute, not an edge
attribute, and there is no multi-hop ownership chain.**

```
JohnSmith   (45.0%, role="Ultimate Beneficial Owner") --hasOwnershipInterestIn--> AcmeCorp
JohnSmith                                             --hasControllingInterestIn-> AcmeCorp
JaneDoe     (60.0%, role="Managing Member")           --hasOwnershipInterestIn--> BetaHoldings
HansMueller (no percent, role="Director")             --hasOwnershipInterestIn--> GammaBank
SarahChen   (25.0%, role="Limited Partner")           --hasOwnershipInterestIn--> DeltaFund
```

Every ownership edge is **Party → Corporation, exactly one hop**. No corporation
owns another corporation. The only corp→corp edges are untyped `isRelatedTo`.
A party carries **one** `ownershipPercent` regardless of how many entities it
holds an interest in, so percentages cannot even be attributed per-edge.

Consequences the planner must price:
- D-03's stated teaching property "**multi-hop ownership chains** are what a graph
  does and what chunk retrieval does badly" is **not demonstrable on this data**.
- D-10's worked demonstration — *"traversing an ownership chain, aggregating
  percentages across hops, and filtering by jurisdiction-specific thresholds"* —
  requires (a) corp→corp `hasOwnershipInterestIn` edges and (b) a per-edge
  percentage.
- Dave's own instruction covers this: *"Use the use case that the backend fibo
  based data stores can support today **or be provided additional data to
  support**"* (discussion log). **Extending the FIBO dataset is in scope and
  should be an explicit, named deliverable with a requirement ID.**

What *is* demonstrable on today's data without extension:
- Sarah Chen at exactly `25.0` — the FinCEN CDD beneficial-ownership threshold
  boundary case. ✅
- Four jurisdictions (`US-DE`, `US-NY`, `DE`, `GB` — verify GB; observed US-DE,
  US-NY, DE on the entities read) for `P`-axis divergence. ✅ *(partially
  verified — read three, CONTEXT claims four)*
- Two planted near-duplicates: "Acme Corporation" / "Acme Global Trading
  Corporation" and "Beta Holdings LLC" / "Beta Investment Holdings" for
  Similarity. ✅
- One-hop UBO with role and percentage. ✅
- Entity resolution across `label` vs `legalName` vs `fullName`. ✅

**What "Who ultimately owns Acme?" requires of `G(E, R, T, P, Π, L)`:**

| Axis | Requirement |
|---|---|
| `E` | Corporation + Party entity classes, resolved across `label`/`legalName`/`lei` (near-duplicate hazard) |
| `R` | `hasOwnershipInterestIn` / `hasControllingInterestIn` typed edges; **corp→corp edges needed for depth ≥ 2** |
| `T` | `onboardingDate` + an authored L1 observation stream (D-05) giving `λ_c` something to decay |
| `P` | Jurisdiction-conditioned threshold (FinCEN 25% for US-DE/US-NY vs EU/UK regimes) — the `PolicyFilter` operator |
| `Π` | The perspective that decides which of {direct owner, controlling owner, UBO} the reader's role sees |
| `L` | Which source system each ownership claim came from, with lineage accumulating across corroborating sources |

Operators: `TraversalNeighborhood` (depth ≥ 2 once the data supports it),
`TemporalAsOf`, `PolicyFilter`, `SimilaritySelect` (the near-duplicate names are
the reason Similarity is non-trivial here). All four categories are exercised
naturally — that is the strongest argument for the spine.

**DGX reachability verified 2026-08-09:** ports `8090`, `27017`, `7687`, `5432`
on `192.168.4.76` are all **OPEN** from this machine.

---

## C. The Three Documentation Sections

### C.1 Section 1 — "Hello CCF", agent-free deterministic assembly

**The minimal public API path today**, taken from `examples/00-quickstart/run.py`
(the tree's own shortest spine, 398 lines, 7 markers, 41 import lines):

1. `load_and_boot(MANIFEST, registry=…, connection=…)` → `BootedFabric`
2. `booted.handle.worker.ingest(envelope)` per envelope from the `role: load`
   `ccf.signal-batch`
3. `view = booted.handle.reader.as_of(tenant_id=…, at=boundary)`
4. `build_operator_registry(parameters=…, view=view, pins=…, policy_bundle_key=…,
   similarity_index_version=…)`
5. `plan = <DeploymentPlan>(plan_id=requirements.plan_id,
   required=requirements.required_operator_keys)` then
   `refuse_operator_set_divergence(declared=declared, plan=plan)` then
   `ProjectionEngine(reader=…, registry=…).execute(plan=…, perspective=…,
   tenant_id=…, temporal_boundary=…)`
6. `run_gates(candidate, engine_resolved=…, now=…, registry=…, product_class=…)`
   → `ServableProduct`
7. `build_replay_record(…)` → `serve(product=…, record=…, replay_writer=…)`

**A-1 verification — is `from ccf.deployment import …` the single preferred day-1
import? Partially, and the answer must be stated precisely.**

`ccf.deployment.__all__` (verified) is:
`SDK_ARTIFACT_CLASSES`, `SDK_ARTIFACT_ROLES`, `SDK_VERSIONED_ARTIFACT_CLASSES`,
`ArtifactPin`, `BootedFabric`, `DeploymentManifest`, `ManifestEntry`,
`ResolvedPins`, `SimilarityCorpusAttributeError`, `UnpinnedArtifactError`,
`build_operator_registry`, `load_and_boot`, `refuse_operator_set_divergence`,
`refuse_registration_the_sdk_fixes`, `refuse_role_the_sdk_fixes`,
`resolve_artifact_class`.

That is the **wiring** surface — steps 1, 4 and the binder. It is *not* the whole
day-1 path: steps 3, 5, 6, 7 need `ccf.graph.protocols`, `ccf.projection.{plan,
engine}`, `ccf.products.{contract,gates}`, `ccf.replay.{record,serve}`, plus
`ccf.controlplane.{artifacts,registry}` for the typed casts. A-1's actual
instruction (SURFACE-AUDIT §5.3) is narrower than it sounds: *"document
`from ccf.deployment import …` as the single preferred day-1 import and treat
**submodule FQNs** as implementation detail"* — i.e. never write
`from ccf.deployment.manifest import load_and_boot`, always
`from ccf.deployment import load_and_boot`. **A-1 is discharged by a documented
import convention plus consistent use across every new example, not by collapsing
the API.**

**The four Context Operator categories** — `src/ccf/operators/categories.py`:
`TraversalNeighborhood`, `TemporalAsOf`, `PolicyFilter`, `SimilaritySelect`, with
typed parameter contracts in `src/ccf/operators/params.py`
(`TraversalNeighborhoodParameters`, `TemporalAsOfParameters`,
`PolicyFilterParameters`, `SimilaritySelectParameters`), each authored as a
`ccf.operator-parameters.<category>` artifact. `OperatorPlan` / `PlannedStep` /
`ComposedOperator` / `IntermediateCache` live in `src/ccf/operators/planner.py`.

**How the six axes of `G` become visible to a beginner** — the tree has **no
existing page that teaches them**. `grep "six axes"` over `public/` returns three
hits and all three are about the *six specialization axes* of an agent, except
`concepts/whitepaper-index.md:19` which is a bare table row. This is genuinely
new content, and the mapping to observable surfaces is:

| Axis | Observable in |
|---|---|
| `E` Entities | `GraphView.entities: tuple[EntityRecord, ...]` |
| `R` Relationships | `GraphView.relationships: tuple[RelationshipRecord, ...]` |
| `T` Time | `GraphView.as_of: datetime`; `reader.as_of(at=…)`; `UpsertResult.superseded_claim_id` |
| `P` Policy | `PolicyFilter` operator + `ProductLineage.policy_bundle_versions` + `PolicyBinding` in replay dim 2 |
| `Π` Projection | the deployment's `ProjectionPlan` subclass + `PerspectiveArtifact` |
| `L` Lineage | `LineageEntry(source, envelope_id, observed_at, passage_anchor)`; `UpsertResult.lineage_added`; `ProductLineage` |

`GraphView` is a **frozen `CCFContract`**, deterministically ordered (entities by
`entity_uri`, relationships by `relationship_key`) — which is what makes the six
axes *inspectable* in a beginner example: you can print a view and it is stable.

### C.2 Section 2 — external agents over MCP, zero CCF dependency

**The MCP egress surface as it ships:**

| Module | Role |
|---|---|
| `runtime/ccf_runtime/mcp/egress.py` | `build_egress_server(...)`, `product_uri(tenant=…, product_class=…, version=…)`. **No auth parameters** — raw egress. |
| `runtime/ccf_runtime/mcp/experience.py` | `build_experience_server(...)` — the **Experience front door with the auth machinery** (D-12). Tools: `get_context`, `get_lineage`, `get_replay_record` (`GET_CONTEXT_TOOL` etc.), plus `list_agents` / `invoke_agent`. Takes a `tool_allowlist`; a tool absent from the allowlist is **never registered** (registration-time omission, D-05). Tool *prose* comes from artifacts, never code (§6.4). |
| `runtime/ccf_runtime/mcp/auth.py` | Bearer-token verification against a manifest-loaded token table; no anonymous mode. |
| `runtime/ccf_runtime/mcp/artifact_server.py` | The ArtifactStore MCP role — distinct from egress. |
| `runtime/ccf_runtime/mcp/hitl_server.py` | HITL queues/actions over MCP (D-IMPL-20). |

Transport: **Streamable HTTP** (`mcp.client.streamable_http.streamablehttp_client`
on the client side), bearer token in an `Authorization` header, served by uvicorn
on loopback with a `READY <port>` stdout handshake as the parent's readiness gate.
`mcp==1.28.1` is a core pin.

**Per-harness client-leg status:**

| Harness | Package (pinned) | What a client leg needs | Exists today | Missing |
|---|---|---|---|---|
| **Claude Agent SDK** | `claude-agent-sdk==0.2.128` (extra `claude-agent`) | An MCP server binding on the session | `runtime/…/adapters/claude_agent/adapter.py`; `examples/03` deterministic leg; `examples/external/…/client_anthropic.py` uses the **raw `anthropic` SDK + `mcp` client**, not the Agent SDK | A client leg driven by `claude-agent-sdk` itself over MCP. The Anthropic-SDK leg is a *near* precedent, not the same thing. |
| **Google ADK** | `google-adk==2.5.0` (extra `adk`) | `McpToolset` + `StreamableHTTPConnectionParams` | ✅ `examples/external/00-hello-context/client_adk.py` — imports only `google.adk.*` and `google.genai` | Nothing structural; rebuild against the new fabric. |
| **LangGraph** | `langgraph==1.2.9` (extra `langgraph`) | An MCP tool binding inside a graph node | ❌ **No LangGraph client leg exists anywhere in the tree**; `langchain-mcp-adapters` is **not installed** | The whole leg. |

⚠ **FINDING F-2 — criterion 3 requires three harness client legs and only one
exists.** Criterion 3: *"Every Section 2 client leg imports nothing from `ccf`
… across all three harnesses."* `examples/external/00-hello-context` ships
**bare-MCP, Anthropic-SDK, and ADK** legs. There is no LangGraph leg and no
Claude-Agent-SDK-as-client leg. Two new legs must be built.

For the LangGraph leg there are two paths:
- **Recommended (zero new dependency):** drive `mcp.ClientSession` +
  `streamablehttp_client` directly inside a LangGraph node, binding the
  discovered tools as LangChain tools by hand. `mcp` is already a core pin;
  `langchain-core==1.5.1` is already present transitively. Nothing new to audit,
  and the import list stays legibly free of `ccf`.
- **Alternative:** add `langchain-mcp-adapters` as a `langgraph`-extra
  dependency. `slopcheck install langchain-mcp-adapters` → **`[OK]`** *("Name
  starts with 'langchain-' — classic LLM naming pattern. Name looks like LLM bait
  but package is established.")*. **Tagged `[ASSUMED]`** — the name came from
  training data, not from official documentation or Context7, and registry
  existence alone does not confer verification. If the planner takes this path it
  owes a `checkpoint:human-verify` before install and a version pin with the same
  discipline as `neo4j==6.2.0` / `pymongo==4.17.0`.

**How "imports nothing from `ccf`" is asserted in CI today — a mechanism exists
and should be extended, not rebuilt.**

`examples/external/00-hello-context/run.py::_assert_zero_ccf_imports`:

```python
pattern = re.compile(r"^(import|from) (ccf|ccf_runtime)", re.MULTILINE)
offenders = [p.name for p in sorted(_EXAMPLE_ROOT.glob("client_*.py"))
             if pattern.search(p.read_text(encoding="utf-8"))]
```

Asserted from CI in `tests/examples/test_ext00_serve_output.py`:
- `test_the_committed_client_legs_import_no_ccf` — runs the real function over
  the shipped files.
- `test_the_zero_import_assertion_fails_when_a_leg_imports_ccf` — **the negative
  control**: copies the legs to `tmp_path`, injects `from ccf.boot import boot`
  and `import ccf_runtime` (both spellings, parametrized), repoints
  `_EXAMPLE_ROOT`, and asserts the guard *refuses*. This is the pattern to keep.
- Additionally `docs/SURFACE-AUDIT.md` §2.3 records that plan 15-20 asserted an
  **empty `git diff`** on all three client legs, because ERGO-15/EXAM-04 rest on
  them.

**Known blind spot the planner should close while rewriting:** the regex is
line-anchored and matches only `import ccf…` / `from ccf…` at line start. It does
not catch `importlib.import_module("ccf")`, an indented import inside a function,
or `__import__`. Given Phase 15.1's entire history of line-scoped greps
under-counting, **an AST-based version of this guard is the obvious upgrade** and
would also discharge part of the "a lint that can actually fail" discipline. It
belongs in `tools/lints/` if it is to run tree-wide.

### C.3 Section 3 — advanced CCF: embedding, and agentic skills

**"Embedding CCF in your own application" concretely means, against today's
surface:** an in-process `load_and_boot(...)` → `BootedFabric` inside the host
application's own process, then the seven-step spine, then either (a) return the
`ServedProduct` in-process, (b) stand up `build_experience_server` for external
consumers, or (c) emit over A2A/peering. The boundary is `serve()` — see §D.3.
`examples/04-cross-process` is the shipped material for (b)+(c) and
`examples/07-artifact-store-mcp` for swapping persistence underneath a running
deployment.

**The skill-catalog / grant / archetype surface a worked example would exercise:**

`ccf.skills.__all__` (verified, partial listing): `SKILL_CATALOG_ENTRY`,
`SKILL_GRANT`, `SKILL_TYPES`, `ApprovalOutcome`, `ApprovalRejected`,
`ApprovalSink`, `BoundSkillView`, `GovernanceUndeclared`, `GrantCollisionError`,
`GrantLedger`, `GrantRefusal`, `GrantTransitionError`, `LocalCallableBinding`,
`McpBinding`, `PeeringBinding`, `PolicyRegimeGovernance`,
`PolicyRegimeUnresolvable`, `RequirementsExceedRegime`, `SkillCatalog`,
`SkillCatalogEntry`, `SkillGrant`, `SkillNotInCatalog`, `SkillRequirements`,
`SplitAuditPlaneError`, `TenantMismatch`. Modules: `catalog.py`, `grants.py`,
`dispatch.py`, `callables.py`, `toolsurface.py`.

`ccf.agents.__all__`: `ARCHETYPES`, `Agent`, `AgentFactory`, `AgentIdentity`,
`ArchetypeComponent`, `ComposedArchetype`, `CompositionContradiction`,
`ConfigurationDefault`, `ControlPlaneResolution`, `DefaultConflict`,
`EmittedEffect`, `ReplayObligation`, `Task`, `TaskFactory`, `TaskIdentity`,
`analytics_insights`, `compose`, `content_generation`, `context_assembly`,
`document_intelligence`, `monitoring_surveillance`, `workflow_task`.

⚠ **The structural fact Section 3's prose must state, from the discussion log:**
every module under `src/ccf/agents/` carries `__ccf_mode__ = "algorithmic"`, and
CINV-03 bars a tagged module from importing `ccf.llm` or any vendor model SDK.
**The SDK's agent surface is structurally forbidden from calling a model.** Those
agents demonstrate *agents as governed identity*, not *agents as reasoners*.
Section 3 must say this plainly or it will read as a Mode-2 promise the fabric
does not keep until Phase 17.

`src/ccf/llm/` contains only `__init__.py` — the `LLMClientProtocol` seam, no
vendor adapter. This is consistent with D-01 and must not be presented as more.

---

## D. Constraints This Phase Must Not Violate

### D.1 The URGENT constraint — Gate 2 / INV-CH7-47

**Current wording is already correct across `src/`, `tests/` and `public/`** (plan
15.1-20's sweep). The eight sites carrying the corrected wording:

| File | Line | Wording |
|---|---|---|
| `src/ccf/deployment/__init__.py` | 72-79 | *"Lineage strict equality (whitepaper §7.6, INV-CH7-47) therefore verifies **assembly-path integrity** — that a served product matches the assembly path the deployment said produced it. It is *not* an independent witness … the engine builds `operators_invoked` and `steps` in one loop over the same operator plan … It is a faithful transcriber."* |
| `src/ccf/projection/plan.py` | 21-22 | *"…the strict-equality gate (INV-CH7-47) compares downstream is the transcribed claim against the engine's execution record — **assembly-path integrity**…"* |
| `src/ccf/products/gates.py` | 397 | *"That buys assembly-path integrity and no…"* |
| `src/ccf/controlplane/artifacts.py` | 528-529 | *"Gate 2 (lineage strict equality, INV-CH7-47) sits downstream of both, and what it verifies is **assembly-path integrity** — the claim as transcribed into the Contract…"* |
| `src/ccf/deployment/binder.py` | 37 | Gate 2 defined and the binder placed upstream of it |
| `src/ccf/deployment/manifest.py` | 35 | why a collapsed binder makes the gate compare a value against itself |
| `tests/examples/test_gate_two_divergence.py` | 8 | *"Gate 2 verifies **assembly-path integrity**: the claim transcribed into the…"* |
| `tests/lints/test_deployment_gates_ban.py` | 6 | *"…rather than independent witness: the engine builds…"* |

**Published pages (both already correct):**
- `public/tutorial/adopters-guide.md:116-127` — *"Comparing them establishes
  **assembly-path integrity** — the product served was assembled by the path the
  deployment claimed. It is not an independent check on the claim itself: the
  engine builds its invoked set and its execution steps in one loop over the same
  operator plan, so it transcribes that plan faithfully rather than witnessing it
  independently. Drift an author could introduce is caught earlier, at the binder
  above (`D-IMPL-86`)."*
- `public/reference/artifacts/product-registration.md:20-28` — same substance,
  naming `refuse_operator_set_divergence` as where authorable drift actually
  fails.

**Files needing a wording change:**

| File | Site | What is wrong | Disposition |
|---|---|---|---|
| `examples/06-decision-replay/README.md` | 189 | Table row headed **"Gate 2 independence (INV-CH7-47)"** — the exact framing criterion 8 forbids | Dies with the example under D-07; must not be reproduced. |
| `tests/products/test_gate_independence.py` | filename + module | The *name* still says "independence". Its content is the `run_gates` two-separately-sourced-arguments guard (ERGO-02), which is a real and different property from independence-of-authorship. | ⚠ **Leave the name; do not rename in this phase.** It is a `src/`-adjacent standing guard, out of scope, and a rename would stale citations across `tests/deployment/` and `tests/products/`. Instead: never *cite* it as evidence of Gate 2 independence in any published page. |
| **All newly-written Section 1–3 prose** | — | The risk is reintroduction, not correction | Every new page describing gates gets a plan-level acceptance check (see Validation Architecture V-8). |

### D.2 The four carried advisories this phase owns

| Adv. | Current state in the tree (verified) | What "discharged in the published tree" means |
|---|---|---|
| **A-1** | `ccf.deployment.__all__` has 16 names; every example already imports `from ccf.deployment import build_operator_registry, load_and_boot, refuse_operator_set_divergence`. **No published page states the convention.** `docs/SURFACE-CHANGES.md` lists both `ccf.deployment.X` and `ccf.deployment.manifest.X`, which is what made 52 additions read as 52 concepts. | A published page (Reference or Tutorial) that states: **import from `ccf.deployment`, never from its submodules; submodule FQNs are implementation detail.** Plus: every new example demonstrably follows it, and ideally a check that no `examples/` file imports `from ccf.deployment.<sub>`. |
| **A-2** | The surface toolchain is: `tools/dump_surface.py` (generated manifest at `docs/surface/v0.2-surface.json`), `make surface` (regenerate — run by exactly two plans per phase: phase-start and phase-close), `tools/assemble_surface_changes.py` + `make surface-changes` (assembles `docs/SURFACE-CHANGES.md` from `docs/surface-changes/*.md` fragments, refusing an entry missing one of seven fields), the drift assertion in `tests/test_surface_drift.py` (always-on `test` job), and `docs/surface-changes/README.md` (the only existing description — internal, not published). Adjacent: `tools/measure_examples.py` + `make measure-examples`, `tools/dump_schemas.py` + `make schemas`, `tools/check_schema_headers.py` + `make schema-headers`, `tools/dump_openapi.py` + `make openapi`. | **A maintainer-facing published page** describing the surface record: what the generated manifest is, why the baseline is immutable mid-phase, how fragments are written and assembled, and which drift assertions gate. Note `docs/surface-changes/README.md` names internal paths (`.planning/`) — check `pub02-internal-path` before any `git mv` into `public/`. |
| **A-3** | Measured: `public/` has **zero** occurrences of any substrate name (`sqlite`, `postgres`, `neo4j`, `mongo`, `fluree`); **six** occurrences of `load_and_boot`; **one** `boot(` (in `write-a-graph-backend-adapter.md`, about `make_writer` refusal). So the published tree does not describe the six-backend surface at all, does not mention the registry, `ccf backends list`, `GET /backends`, `backend_secrets`, `GraphQuery`/`docs/GRAPH_QUERY_SEMANTICS.md`, pushdown, `ProductSource`, or `SourceAttestation`. `how-to/write-a-graph-backend-adapter.md` (242 lines) is the page most likely to be materially wrong post-15.4 and is also the page DI-15.4-05/F2 touches. | Every page rewritten against the surface at HEAD, with the registry seam, the six adapters, and the CLI/HTTP `backends` noun documented. **Stale-page inventory below.** |
| **A-8** | `BootedFabric.artifacts` docstring (`src/ccf/deployment/manifest.py:118-138`) already states both halves precisely: *"`role` governs registration and pinning, never visibility. A `role: load` artifact appearing here is still absent from `pins`, still absent from the Control Plane registry, and still absent from replay dimension 2."* **No published page says either half.** | The reference page for Control Plane artifacts (and/or a manifest reference page) states **both**: `role: load` artifacts *are* reachable on `BootedFabric.artifacts`, *and* they are absent from the pin set / replay dimension 2. |

**A-3 stale-page inventory (highest risk first):**

1. `how-to/write-a-graph-backend-adapter.md` (242 lines) — predates the registry
   seam entirely; the adapter contract is now `BackendRegistration(name,
   config_model, secret_fields, open_store, make_writer)` declared as
   `REGISTRATION` in a `*_write.py` module, discovered by disk read or entry
   point. Also entangled with the open DI-15.4-05/F2 ruling.
2. `tutorial/adopters-guide.md` (447 lines) — six-example dependency; the
   canonical day-1 narrative.
3. `tutorial/demo-walkthrough.md` (329 lines) — DEMO-03's deliverable, tied to
   `08-e2e-demo`'s byte-compared transcript.
4. `concepts/pillars/data-context.md` (105 lines) — **the G-01 page**: opens on
   *"how does an agent get at first-party records"*; carries the buried line-133
   acknowledgement.
5. `reference/protocols/storage-and-graph.md` (14 lines) — thin, and now
   materially incomplete: no `GraphQuery`, no registry, no pushdown.
6. `how-to/security-and-deployment.md` (161 lines) — `backend_secrets` /
   `SecretReference` / `ResolvedSecret` did not exist when it was written.
7. The 12 `reference/protocols/*.md` pages are mkdocstrings-thin (9–42 lines);
   they will not be *wrong* so much as *silent* about 15.2–15.4 additions.

### D.3 Phase 14's D-07 marker vocabulary (criterion 6)

**Exact syntax in use.** Source side, a Python comment:

```python
    # --8<-- [start:boot]
    booted = load_and_boot(...)
    # --8<-- [end:boot]
```

Consumer side, in Markdown:

```
--8<-- "examples/00-quickstart/run.py:boot"
```

Whole-file include (used for every YAML artifact — **no YAML file in the tree
carries a marker**):

```
--8<-- "examples/00-quickstart/artifacts/manifest.yaml"
```

**Toolchain that consumes it:** `pymdownx.snippets` configured in `mkdocs.yml`
with `base_path: ["."]` (resolved against **process CWD**, which is why `make`
always runs at the repo root), `check_paths: true` (D-08 in its entirety — the
default `false` makes a missing file *and* a missing section build clean at exit
0 with an empty block), `restrict_base_path: true`, `dedent_subsections: true`.
Gated by `strict: true` in `mkdocs.yml` plus `--strict` on the command line, and
proven live by `tools/docs_tests/test_snippet_gate.py` (positive + two negative
controls). Line-range includes are **explicitly rejected** by D-07.

**Current marker inventory:** 7 (`00`), 5 (`01`), 5 (`02`), 9 (`03`), 9 (`04`),
11 (`05`), 5 (`06`), 4 (`07`), 0 (`08`), 1 (`03/legs/deterministic.py`),
3 (`external/…/client_bare.py`). Names in use: `boot`, `ingest`, `operators`,
`project`, `gate`, `record`, `serve`, `agent-artifacts`, `agent-factory`,
`specialization-axes`, `agent-replay`, `skill-catalog`, `skill-grant`,
`skill-exercise`, `skill-refusal`, `skill-revoke`, `harness-agent`,
`harness-replay-hook`, `harness-legs`, `harness-governed-fields`, `peer-*`,
`mcp-egress`, `store-*`, `workflow-*`, `hitl-*`, `replay-*`, `mcp-connect`,
`mcp-discover`, `mcp-resource`, `register-definitions`, `review-queue`,
`exception-path`.

**How a "CCF call spine" region is separated from "deployment code" legibly in
the repository** — D-11 forbids new marker vocabulary, so the separation must be
*structural*, and the tree already supplies three composable conventions the
planner can combine without inventing anything:

1. **File-level split.** The strongest and most legible: put the spine in one
   module and the deployment code in another —
   `examples/<name>/spine.py` (the CCF call spine, imports `ccf.*`, no domain
   vocabulary) beside `examples/<name>/deployment.py` (the projection `Π`
   subclass, the artifact-key vocabulary, scenario setup). Precedent:
   `examples/03-harness-portability/legs/` and
   `examples/04-cross-process/producer_child.py` are already separate modules
   with separate concerns. A repo reader sees the boundary in `ls`.
2. **Ordered, contiguous marker regions inside the spine** using the existing
   named-marker vocabulary — the seven `00-quickstart` names (`boot`, `ingest`,
   `operators`, `project`, `gate`, `record`, `serve`) already *are* the spine's
   canonical decomposition and should be the standard set every Section-1
   example uses.
3. **The `[ADAPT]` / `[MECHANISM]` header convention**, already present in every
   example artifact (`manifest.yaml`, `live.yaml`, `harnesses.yaml` all carry it)
   — a close cousin of D-11 that CONTEXT explicitly says "should inform it".
   Extending the same two-word vocabulary to the *code* file headers costs no new
   markers.

The acceptance test for criterion 6 should be exactly Dave's own sentence:
someone reading the repository — not the rendered site — can tell which code is
CCF and which is theirs.

### D.4 The fabric must not change (criterion 10)

Verified against the tree at HEAD:

| Thing criterion 10 forbids | Present? | Evidence |
|---|---|---|
| Mode 2 packaging stage | **No** | `AssemblyMode = Literal["algorithmic","llm_packaged","swarm_assembled"]` exists at `src/ccf/products/contract.py:71` as a **type only**; `ModelVersionRecord.assembly_mode` at `record.py:356`; no packaging code anywhere. |
| Mode 3 coordinator | **No** | No swarm module; `Operator` docstring merely permits swarm realization. |
| `src/ccf/unstructured/` | **No** | Directory does not exist. `src/ccf/llm/` contains only `__init__.py`. |
| Tier-3 external sources | **No** | Deferred in 15.2. |

**`serve()` and its boundary — for D-02's ruling text.**

`src/ccf/replay/serve.py`, `__all__` = `CapabilityForgeryError`,
`DeliveryCapability`, `QueryPinMismatch`, `QueryPinWriter`, `ReplayWriter`,
`ServedProduct`, `serve`.

```python
def serve(*, product: ServableProduct, record: DecisionReplayRecord,
          replay_writer: ReplayWriter,
          query_pin_writer: QueryPinWriter | None = None,
          executed_queries: tuple[GraphQuery, ...] = ()) -> ServedProduct
```

*"Record the decision, then deliver the product — in that order, always."*
Ordering is load-bearing (15.2-08 / D-11): query bytes persist **before** the
replay-record append, so a recorded pin never dangles; consistency is checked
before any store write, raising `QueryPinMismatch`.

The boundary, stated for the ruling: `serve()`'s **inputs** are an already-gated
`ServableProduct` (only `ccf.products.gates` can mint one) and a fully-built
`DecisionReplayRecord`. Its **outputs** are a `ServedProduct` carrying a
`DeliveryCapability`. It performs exactly two acts — persist the query pins, then
append the replay record — and returns. **It contains no rendering, no
transformation of the product payload, and no branch.** The Phase 04 decision
carried in STATE.md is the anchor: *"serve() is one expression because the replay
append returns the delivery capability — there is no branch that reaches delivery
without a recorded decision."*

That is the structural argument D-02 needs: **a packaging stage inside `serve()`
would introduce the branch that decision exists to forbid**, and would place an
LLM call inside the function that mints the audit record. Attaching *above*
`serve()` — consuming the `ServedProduct` — keeps the substrate the artifact a
supervisor inspects and makes the rendering a presentation layer over it
(whitepaper §7.6). The one open sub-question the ruling should answer explicitly:
whether `assembly_mode` on the *product class* then describes the substrate
(always `algorithmic` when packaging sits above) or the delivered artifact
(`llm_packaged`), because CONTEXT's `<specifics>` promises Section 1 will
introduce `assembly_mode: algorithmic` as *a real choice with two siblings
arriving later*.

---

## E. The Adoption Argument (criterion 7)

The page must **cite shipped mechanism**, not assert. Verified backing for each
of the four "what the alternatives lack" claims:

| Claim | Shipped CCF mechanism | Verified location | Confidence |
|---|---|---|---|
| **No replay** | Five-dimension `DecisionReplayRecord`; `build_replay_record(...)`; `serve()` records **before** delivering, with no branch to delivery without a record; dimension 2 pins policy bundles, HITL actions, survivor cap, **graph adapter + version + secret refs**; dimension 4 carries agent version and skill-set in force; `graph_query_sequence` pins the executed query hashes with canonical bytes in the ArtifactStore | `src/ccf/replay/{record,serve}.py`; `ContentGenerationPath.graph_query_sequence`; `PolicyBindingsSnapshot` | HIGH |
| **No policy binding at assembly** | `PolicyFilter` operator (one of the four categories, authored as `ccf.operator-parameters.policy`); `ProductLineage.policy_bundle_versions: frozenset[str]` — *"a set, because state assembled under two bundle versions has two bindings and collapsing them would lose the one that mattered"*; `boot()` requires `policy_bundle_key` + `policy_bundle_version` as an explicit pinned pair with no "latest"; `PolicyBinding` in replay dim 2; A2A admission verifies inbound policy bindings at the consumer's Control Plane before L3 | `src/ccf/operators/categories.py::PolicyFilter`; `src/ccf/products/contract.py::ProductLineage`; `src/ccf/boot.py::boot`; `src/ccf/peering/admission.py` | HIGH |
| **No lineage to a passage** | `PassageAnchor` is a shipped contract; `LineageEntry(source, envelope_id, observed_at, passage_anchor)`; lineage accumulates by set-union on idempotent re-arrival (`UpsertResult.lineage_added`, INV-CH7-17); `ReviewQueue` items carry the passage-level lineage view for reviewers | `src/ccf/contracts/claims.py:53,85`; `src/ccf/hitl/review_queue.py:98-102,257` | **MEDIUM — see caveat** |
| **No staleness measure** | `ccf.halflife.decay` (`Observation`, `freshness`, per-observation-type `λ_c` from a `ccf.half-life-table` artifact with `decay_driver` and `supersession_event` rows) and `ccf.halflife.debt` (`D_c` computed against a `ccf.debt-profile`, gating Forced-LLM / Fail-Closed routing); `TemporalAsOf` operator; `GraphView.as_of` guaranteeing no future-information leakage (INV-CH7-14) | `src/ccf/halflife/{decay,debt}.py`; `examples/01-agent-basics/artifacts/{half-life-table,debt-evaluation,agent-debt-profile}.yaml` | HIGH |

⚠ **Caveat the adoption page must carry (honesty > rhetoric).** The
`passage_anchor` *contract* ships and is populated on `LineageEntry`, but
**Pattern 5 / `src/ccf/unstructured/` was never built** (D-IMPL-08 RESOLVED
2026-07-25, no code), so there is no shipped ingestion pipeline that *produces*
passage anchors from documents. The page may honestly say "the lineage contract
anchors a claim to the passage it came from" and must not say "CCF extracts
passage anchors from your documents today." Overclaiming here is precisely the
defect class Phase 15.1 spent five review rounds on.

**The UBO demonstration, and what it needs.** "Who ultimately owns Acme?" is the
right question — the answer lives in the *relationships*, not in any passage, and
a vector store over chunked documents structurally cannot compose it. But see
FINDING F-1: **today's data answers it in one hop**, which weakens the
demonstration considerably (one hop is retrievable). The page's force depends on
the data extension. The planner should treat "extend the FIBO dataset with
corp→corp ownership edges carrying per-edge percentages" as a **prerequisite of
criterion 7**, not a nice-to-have.

**One more asset the page should use:** G-01's finding was that the entire
published surface returns **zero** hits for "why not just", "instead of
building", "rather than building", "compared to". That is a mechanical
before/after the phase can re-measure — see V-7.

---

## F. Publication Mechanics

**The build.** `docs_dir: public` in `mkdocs.yml` at the **repo root** (not inside
`public/`, because `pymdownx.snippets` `base_path` resolves against process CWD).
`site_dir: site`, gitignored. `strict: true` in the config *and* `--strict` on the
command line, so `make docs` and `make docs-strict` gate identically. The
`validation:` block promotes `omitted_files`, `absolute_links`,
`unrecognized_links`, `anchors`, `nav.omitted_files`, `nav.not_found` from
`info` to `warn`, and `--strict` promotes warn→error. Without that block a dead
`[link](nope.md)` builds clean at exit 0.

**The gate — `make docs-strict`, three ordered steps, no `|| true`, no `-`
prefix, no report-only flag:**

```make
docs-strict:
	PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py --pre-build
	PYTHONPATH=.:src:runtime .venv/bin/python -m mkdocs build --strict
	PYTHONPATH=.:src:runtime .venv/bin/python tools/publish_scan.py site
```

Wired into `make ci` (D-IMPL-72) and into the always-on `docs` job in `ci.yml`,
which first runs `pytest tools/publish_scan_tests tools/docs_tests -q` and then
uploads `site/` as artifact `ccf-docs-site`. **Nothing is hosted** (D-IMPL-71) —
the artifact is how adopters read it.

**Publish-safety rules (`tools/publish_scan.py`, no allowlist, exit code is the
only signal):**

| Rule | What it catches | Tuning |
|---|---|---|
| `pub01-whitepaper-shingle` | 10 consecutive normalized words from the whitepaper body in a published file; strips HTML and backtick code spans first | `SHINGLE_WORDS = 10`, measured (N=8 noisy, N=20 useless) |
| `pub02-internal-path` | A published path naming an internal deliverable (`INTERNAL_PATH_TOKENS`: `CCF_Whitepaper`, `SPEC_INVENTORY`, `PHASE_I`, …), or a `Fig-CHNN-NN` figure citation; boundary-anchored | — |
| `pub03-symlink` | A symlink under `public/` | pre-build only |
| `pub04-include-escape` | A snippet target outside `INCLUDE_ALLOWED_PREFIXES = ("examples/", "public/", "perf/baselines/")` plus a separate root-file list (`openapi.json`) | ⚠ **Positive allowlist — new example directories must live under `examples/`, or this constant needs an audited edit.** |

**Nav.** `mkdocs.yml`'s `nav:` enumerates every path explicitly, **no globs** — the
comment says it "lists 40 pages, and `charter.md` is the single `not_in_nav`
page, for the 41 markdown files under `public/`." With `validation.nav.
omitted_files: warn` under `--strict`, **a new page not added to nav fails the
build, and a nav entry whose file was deleted fails the build.** Nav restructuring
is therefore a first-class deliverable, not cleanup.

Current Diátaxis nav: Home / Tutorial (2) / How-to (7) / Concepts (Pillars 5 +
Invariants + Replay anatomy + Whitepaper cross-reference) / Reference (Protocols
12 + Definition artifacts 8 + HTTP API + Performance).

**Other gates that constrain the rewrite:**
- `tools/docs_tests/test_diagram_coverage.py` — **bijection**: every
  `public/diagrams/*.mmd` is included by exactly one page under
  `public/concepts/`. Both directions reported by name.
- `tools/docs_tests/test_mkdocstrings_gate.py` — runs the **real** site config
  against a **copy** of the real `public/` tree, asserting an impossible
  identifier fails, a near-miss *rename* of a genuinely documented identifier
  fails, and the unmodified copy builds clean. This is D-14's whole
  rename-and-removal gate.
- `tools/docs_tests/test_openapi_drift_control.py`, `test_snippet_gate.py`.
- `tools/lints/citations.py` (`cite01-resolves`, `cite02-anchor`,
  `cite03-node-id`) runs in `make lint` → `make ci-core` → `make ci`. **A new
  page citing `file.py:NNN` will be checked if it carries a backticked anchor.**
  Prefer `module.py::symbol` form. `docs/DECISIONS.md` is deliberately out of
  scope; `.planning/phases/` is exempt except `deferred-items.md`.

**"Runs end-to-end by a single documented command" for a published section**
means, concretely: a `make example-<name>` target exists, is composed into `make
examples`, is exercised by the `examples` job in `ci.yml`, and the section's own
page states that exact command string. The Makefile mirrors CI command-for-command
(D-10), and `.venv/bin/python` is the interpreter in every recipe (CI provisions a
`.venv` specifically so the command strings are identical).

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Selecting a backend in the example runner | A `if backend == …` cascade or a name→module dict | `ccf.graph.registry.declared_names()` / `resolve()`; `DeploymentManifest.backend`; `load_and_boot(connection=…)` | This is exactly what 15.4 un-forked. A cascade would re-fork it and `cinv04-substrate-name` guards `src/` only, so nothing would catch it in `examples/`. |
| Parametrizing tests across six backends | A new matrix harness | Mirror `tests/conformance/test_graphstore.py::graph_backend` + `tests/conftest.py::fabric_boot`, and reuse the registered pytest marks (`postgres`, `neo4j`, `mongo`, `fluree`) | Proven, and the marks already gate CI legs. |
| Asserting zero-CCF imports in client legs | A fresh grep | Extend `_assert_zero_ccf_imports` **and its negative-control test**; upgrade the matcher to AST | A guard without a proof that it refuses is a guard that can silently pass forever. The negative control already exists. |
| Including code in docs | Pasted snippets or line-range includes | `pymdownx.snippets` named markers (D-07) | Line numbers rot; a strict build happily includes the wrong lines. |
| Keeping schemas / OpenAPI / surface manifests in docs current | Hand-written tables | `make schemas`, `make openapi`, `make surface`, mkdocstrings `:::` directives | Every one has a committed baseline and an always-on drift assertion. |
| A whitepaper-leak check | A reviewer checklist | `tools/publish_scan.py` | No allowlist, no report-only mode, already wired into `ci`. |
| Secrets for the DGX legs | Any file in the tree | GitHub Actions secrets + `backend_secrets: [{field, env_var}]` + `ResolvedSecret`; `canonical_bytes` refuses `SecretStr` | The refusal is mechanism, not discipline. |
| Loading FIBO data into CCF's graph wholesale | A bulk importer | L1 ingress (`CDCSourceAdapter`, `McpResourceClient`, file/stream) + selective assembly; `McpContentAcquirer` for L4/L5 decision-time acquisition | D-04, and Dave's *"that would be a disaster."* |
| An assertion inside example code | `assert` in `run.py` | A parallel `tests/examples/test_*.py` module | ERGO-16 / D-09; ~85 assertion/print lines were inflating apparent integration cost, which is half the reason this phase exists. |

---

## Common Pitfalls

### P-1: Deleting an example before its pages are re-cut
**What goes wrong:** `make docs-strict` fails in the `docs` job and `make ci` goes
red, blocking every subsequent wave.
**Why:** `check_paths: true` + `strict: true` make a missing snippet file a hard
build error, by design (D-08).
**Avoid:** every wave moves an example *and* every page in its §A.2 row together.
**Warning sign:** a plan whose acceptance criteria mention only `make examples`.

### P-2: Line-scoped greps under-counting a sweep
**What goes wrong:** a "complete" sweep leaves sites standing.
**Why:** a wrapped Markdown sentence is invisible to a line-scoped grep. Phase
15.1 under-counted the same sweep **six times**; the fix that finally worked was
paragraph-scoping (join the file into one whitespace-normalized string, match
there, map the offset back to a line).
**Avoid:** every prose sweep in this phase is paragraph-scoped from the start.
**Warning sign:** any plan step spelled `grep -rn "<phrase>"`.

### P-3: Asserting byte-identical *replay records* across backends
**What goes wrong:** the matrix test fails and the "fix" deletes the adapter pin.
**Why:** `PolicyBindingsSnapshot.graph_adapter` / `graph_adapter_version` /
`graph_secret_refs` are dimension-2 facts as of 15.4-08.
**Avoid:** assert byte-identity on the **served `ContextProductContract`** (no
substrate-dependent field) and assert the replay record's non-adapter dimensions
separately.

### P-4: Reintroducing the Gate-2 independence framing in new prose
**What goes wrong:** criterion 8 fails on pages nobody swept, because the sweep
was of *old* pages.
**Avoid:** a plan-level acceptance check on every new page describing gates; and
copy the corrected sentence from `src/ccf/deployment/__init__.py:72-79` rather
than paraphrasing it fresh.

### P-5: Documenting a substrate name in `src/`
**What goes wrong:** `cinv04-substrate-name` / `-prose` fires and `make lint`
fails.
**Why:** the rule scopes `src/` only and derives its vocabulary from adapter
module stems on disk; the prose rule fires on a docstring naming ≥3 distinct
substrates. `examples/` and `public/` are **not** in scope, so documenting the six
backends in published pages is safe.
**Warning sign:** a plan that "documents the backends" by editing a `src/`
docstring.

### P-6: Adding an example outside `examples/`
**What goes wrong:** `pub04-include-escape` fires because
`INCLUDE_ALLOWED_PREFIXES` is a **positive** allowlist.
**Avoid:** keep every new example under `examples/`, or make the constant edit a
deliberate, reviewed act.

### P-7: A green `docs-strict` read as "the docs are current"
**What goes wrong:** exactly A-3. SURFACE-AUDIT says it outright: *"`make
docs-strict` green means the site builds, not that it is current."*
**Avoid:** criterion 9's discharge needs positive evidence per advisory, not a
green build.

### P-8: A "complete" claim in a SUMMARY that was reasoned to rather than measured
**Why it matters here:** R5-WR-02 is a carried residual specifically about this,
and its disposition is *"Phase 16, as a writing rule"*: **a record that claims
every figure was measured must either be scripted output or must scope the claim
to what was.**

### P-9: `make ci` green read as "CI would be green"
**Why:** `[tool.pytest] testpaths = ["tests"]`, so `pytest tools/lints/tests
tools/publish_scan_tests tools/docs_tests` is run by `ci.yml` and by **nothing a
developer runs locally**. Three of those tests **fail right now** (see Risks R-2).

---

## State of the Art (in this repo)

| Old approach (what the docs still describe) | Current approach | Changed in | Impact on Phase 16 |
|---|---|---|---|
| Hand-written registration prologue + `boot(database_path=…)` | `load_and_boot(manifest)` + `connection=` mapping keyed on the adapter's own config fields | Phase 15 (ERGO-10), 15.4 D-10 | Every published snippet region is wrong at the `boot` step |
| Per-database keyword arguments on `boot()` | `backend: str` required, `connection: Mapping[str, object]` | 15.4 | `how-to/write-a-graph-backend-adapter.md` is materially stale |
| Six-name `Literal` on `DeploymentManifest.backend` | Free lowercase string, membership checked at load against the registry; `ccf backends list` / `GET /backends` replaces the editor enum | 15.4-06, 15.4-09 (D-IMPL-22 amended) | New reference content owed |
| Two graph backends (sqlite, postgres) | **Six** in-tree + third-party via `ccf.graph_backends` entry points | 15.2, 15.3, 15.4 | The whole of criterion 4 |
| No query seam | `GraphQuery` + `GraphReader.query()` + `docs/GRAPH_QUERY_SEMANTICS.md` (35 `GQ-NN` clauses, semantics v1.0.1) + pushdown with `translated_answers`/`fallback_answers` telemetry | 15.2 | Nothing in `public/` mentions it |
| Gate 2 as "two independently produced sets" | Gate 2 as **assembly-path integrity**; authorable drift caught upstream at `refuse_operator_set_divergence` over two authored artifacts | D-IMPL-57 correction + D-IMPL-86, 2026-08-05 | Criterion 8 |
| `role` implied invisibility | `role` governs registration and pinning, **never visibility**; `role: load` artifacts return on `BootedFabric.artifacts` | D-IMPL-80 | A-8 |
| Manifest cannot name author-versioned classes | A manifest **may** name all six as `registration: versioned`; what is refused at preflight is `registration: typed` for such a class | 15.1-02 (D-IMPL-85 superseded) | The superseded-claim sweep is **still open for `examples/01`–`04`** — and those files retire, which closes that half for free |

**Deprecated / retired:** the `tools/gates/` D-IMPL-92 line-budget gate (retired
by 15.4-07, replaced by `cinv02-backend-import` and `cinv04-substrate-name`/
`-prose`); the `ccf hitl decide` verb (removed, `submit` is the one verb).

---

## Validation Architecture

Test framework and commands, verified by execution.

### Test Framework

| Property | Value |
|---|---|
| Framework | `pytest` (with `pytest-cov`, `pytest-benchmark` for `perf/` only) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]`, `testpaths = ["tests"]`, 8 registered markers |
| Quick run command | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests -q -m "not postgres and not chroma and not neo4j and not mongo and not fluree"` |
| Full suite command | `make ci` (= `lint typecheck test examples docs-strict`) |
| Gate-checker suites CI runs but `make ci` does not | `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q` — **453 passed / 3 failed at HEAD** |
| Substrate legs | `make legs` = `leg-postgres leg-neo4j leg-mongo leg-fluree` |

### The 10 ROADMAP success criteria → verification

| # | Criterion | Verification |
|---|---|---|
| **V-1** | Sections 1–3 published; each runs end-to-end by a single documented command; Section 4 absent and named as Phase 17's | `make docs-strict` exit 0 **and** `make examples` exit 0 **and** a test asserting every `make example-*` target named in a published page exists in the `Makefile` and is composed into `examples:` (new: `tools/docs_tests/test_documented_commands_exist.py`, parsing `Makefile` `.PHONY` + the `examples:` prerequisite list against a regex over `public/**/*.md`). Section 4 absence: `grep -c "llm_packaged\|swarm_assembled" public/` returns hits only in prose that names Phase 17. |
| **V-2** | Section 1 invokes no agent | AST assertion over the Section-1 example modules: no import of `ccf.agents`, `ccf.skills`, `ccf.workflow`, `ccf.hitl`, `ccf_runtime.adapters`. New test `tests/examples/test_section_one_is_agent_free.py`, with a **negative control** (inject `from ccf.agents import AgentFactory` into a copy, assert the guard refuses) — the `test_ext00_serve_output.py` pattern. |
| **V-3** | Every Section 2 client leg imports nothing from `ccf`, across all three harnesses | Extend `_assert_zero_ccf_imports` to an **AST** matcher (catches `importlib.import_module("ccf")`, indented imports, `__import__`) over `client_*.py`; assert in `tests/examples/test_<sec2>_output.py::test_the_committed_client_legs_import_no_ccf`; keep the parametrized negative control `test_the_zero_import_assertion_fails_when_a_leg_imports_ccf`. Plus a test asserting **exactly three** harness legs are present by name, so a dropped leg is a failure rather than a silence. |
| **V-4** | One parameterized runner; CI matrix asserts equivalent Context Products across six backends; sqlite+memory always-on and network-free; four DGX opt-in; no credential in the tree | (a) `pytest tests/examples/test_backend_matrix.py -q` — parametrized over `["sqlite","memory"]` always-on, `["postgres","neo4j","mongo","fluree"]` behind the existing marks; asserts `content_hash(product_sqlite) == content_hash(product_<b>)` for every `b`. (b) One-runner proof: an AST/source assertion that exactly one example driver module exists for the matrix and that it contains no substrate name literal. (c) Network-free proof: reuse example 03's socket-guard pattern (`T-08-25`) — install a guard that fails the run if anything opens a non-loopback socket during the always-on legs. (d) Credential proof: a `tools/lints` rule or test asserting no example artifact or `.py` contains a `dsn`/`uri`/`password`/`token` value for `192.168.4.76`; `git grep -c "192.168.4.76" -- examples/ public/ src/ runtime/` must be 0 **except** in an env-defaulted, value-free artifact. |
| **V-5** | `examples/00`–`08` retired; every page sourcing from them re-cut; no partial state | `make docs-strict` exit 0 is the **mechanical** proof for includes (`check_paths: true` makes a dangling include a build error). For prose-only refs (the silent half): a new checker `tools/docs_tests/test_no_stale_example_paths.py` that extracts every `examples/…` and `tests/examples/…` path token from `public/**/*.md` (paragraph-scoped) and asserts each resolves on disk. **This also discharges SURFACE-AUDIT A-5's mis-pointed-include gap for path targets.** Plus `test -d examples/00-quickstart` must fail. |
| **V-6** | Each example separates CCF call spine from deployment code into distinct markered regions, legible in the repo | A structural test: for each new example, assert (a) the spine module exists and imports no domain vocabulary artifact keys directly (or the file-split convention chosen), (b) the spine carries the canonical ordered marker set, (c) every marker opened is closed, (d) no marker region spans both modules. Runnable as `pytest tests/examples/test_spine_separation.py -q`. **Human check remains the real gate** — Dave's sentence — so the plan should carry a `checkpoint:human-verify`. |
| **V-7** | Adoption-argument page names the alternatives and what each lacks; worked demonstration is the UBO question | `pytest tools/docs_tests/test_adoption_argument.py -q` asserting the page exists in nav and contains, case-insensitively: at least one of {"why not just","instead of building","rather than building","compared to"}; the three named alternatives; the four named lacks; and the literal UBO question. This is the **exact inverse of G-01's measurement**, which found zero hits site-wide — so the before/after is mechanical, not editorial. |
| **V-8** | Gate 2 documented as assembly-path integrity and nowhere as two independently authored sets; the `test_*_output.py` comparisons not promoted as independence proofs | Two paragraph-scoped assertions over `public/**/*.md` in `tools/docs_tests/test_gate_two_wording.py`: (i) every paragraph mentioning `INV-CH7-47` or "lineage strict equality" also contains "assembly-path integrity" or an explicit negation; (ii) **zero** paragraphs assert independence *affirmatively* — i.e. a match for "independent"/"independently" adjacent to Gate 2 must also carry a negation ("not", "rather than", "never"). Mirrors the two-vocabulary sweep 15.1 ran, but as a standing gate rather than a one-off. |
| **V-9** | A-1, A-2, A-3, A-8 discharged in the published tree | **A-1:** `grep -rn "from ccf.deployment import" public/ examples/` non-empty **and** `grep -rn "from ccf\.deployment\.[a-z_]* import" examples/ public/` empty; plus the convention page present in nav. **A-2:** the maintainer page present in nav and naming `tools/dump_surface.py`, `make surface`, `tools/assemble_surface_changes.py`, and baseline immutability; `tools/publish_scan.py --pre-build` still exit 0 on it (`pub02-internal-path`). **A-3:** `grep -c` over `public/` for `load_and_boot`, `backend`, `ccf backends`, `GraphQuery`, `registry` all > 0; and no page describes a `boot()` signature that does not match `inspect.signature(ccf.boot.boot)` — assertable by a test that extracts fenced `boot(` signatures and compares parameter names. **A-8:** the reference page contains both halves — `BootedFabric.artifacts` reachability **and** absence from `pins`/replay dimension 2 — asserted by string presence in `tools/docs_tests/test_advisory_discharge.py`. |
| **V-10** | No fabric changed; D-02 is a ruling with no diff | `git diff --stat <phase-base>..HEAD -- src/ runtime/` shows **zero** lines changed (or only a ruled, enumerated exception list). Plus: `test ! -d src/ccf/unstructured`; `grep -rn "llm_packaged" src/ | wc -l` unchanged from base; `docs/DECISIONS.md` contains the new `D-IMPL-94` (next free id — highest at HEAD is **D-IMPL-93**) entry for D-02. A CI-runnable form: `make gate-16` in the spirit of the retired `make gate-15.3`, asserting the permitted-change path allowlist excludes `src/` and `runtime/`. |

### Sampling Rate

- **Per task commit:** `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples -q` + `make lint`
- **Per wave merge:** `make ci` (**must include `docs-strict`** — this is the wave gate that catches P-1) + `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q`
- **Phase gate:** `make ci` green, the three gate-checker suites green (requires fixing the 3 pre-existing failures), `make legs` green against containers, the DGX opt-in workflow dispatched once and green, then `/gsd-review --all` per CLAUDE.md §3.1

### Wave 0 Gaps

- [ ] **Fix the 3 pre-existing gate-checker failures** (they block any honest "green" claim):
  - `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` — `ProductClassDeclaration`'s docstring in `src/ccf/controlplane/artifacts.py` trips the shingle scan with **20 hits**. ⚠ **This one requires a `src/` docstring edit, which collides with criterion 10's "no fabric changed."** Needs an explicit carve-out in the D-02-adjacent ruling or a recorded exception. See Open Question Q-1.
  - `tools/docs_tests/test_snippet_gate.py::test_the_unmodified_source_builds_clean` and `::test_a_deleted_section_marker_fails_the_strict_build` — both expect an `[start:ontology]` marker in `examples/00-quickstart/run.py` that no longer exists (`SNIPPET_SOURCE`/`SECTION` constants at the top of the module). **The greenfield rewrite must repoint these two constants at a new example and marker.**
- [ ] Decide `make ci` composition: whether it gains the three gate-checker suites so the claim *"the full local reproduction of the always-on pipeline"* becomes true (deferred-items names this as Phase 16's, two separable items).
- [ ] `tests/examples/test_backend_matrix.py` — does not exist
- [ ] `tests/examples/test_section_one_is_agent_free.py` — does not exist
- [ ] `tests/examples/test_spine_separation.py` — does not exist
- [ ] `tools/docs_tests/test_no_stale_example_paths.py` — does not exist (A-5)
- [ ] `tools/docs_tests/test_gate_two_wording.py` — does not exist
- [ ] `tools/docs_tests/test_adoption_argument.py` — does not exist
- [ ] `tools/docs_tests/test_advisory_discharge.py` — does not exist
- [ ] `tools/docs_tests/test_documented_commands_exist.py` — does not exist
- [ ] The **LangGraph** and **Claude-Agent-SDK** client legs for Section 2 (F-2)
- [ ] The FIBO data extension: corp→corp `hasOwnershipInterestIn` edges with per-edge percentages (F-1)
- [ ] A DGX opt-in job in `.github/workflows/live-legs.yml` with secret-gated fail-fast preconditions
- [ ] Framework install: **none needed** — `pytest` and the whole toolchain are present

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python | everything | ✓ | 3.12 (`.venv`) | — |
| `pytest` / `mypy` / `mkdocs` / `mkdocs-material` / `mkdocstrings` / `griffe-pydantic` | test + docs gates | ✓ | installed in `.venv` | — |
| `mcp` | MCP client + server | ✓ | 1.28.1 (core pin) | — |
| `google-adk` | ADK legs | ✓ | 2.5.0 (extra `adk`) | — |
| `claude-agent-sdk` | Claude legs | ✓ | 0.2.128 (extra `claude-agent`) | — |
| `langgraph` | LangGraph legs | ✓ | 1.2.9 (extra `langgraph`) | — |
| `anthropic` | external client leg | ✓ | 0.120.2 (extra `anthropic`) | — |
| `langchain-core` | LangGraph MCP tool binding | ✓ | 1.5.1 (transitive) | — |
| `langchain-mcp-adapters` | *optional* LangGraph MCP binding | ✗ | — | **Use `mcp.ClientSession` directly inside a LangGraph node — zero new dependency (recommended)** |
| `neo4j` driver | neo4j leg | extra `neo4j` (`==6.2.0`), not in base `[dev]` | — | CI installs `.[dev,neo4j,mongo]` |
| `pymongo` | mongo leg | extra `mongo` (`==4.17.0`) | — | same |
| Fluree | fluree leg | **no Python extra** — `httpx` is a core pin | — | — |
| DGX Fluree `192.168.4.76:8090` | opt-in live leg | ✓ **port OPEN** | ledger `fibo:main` | localhost container `fluree/server:4.1.4` |
| DGX Mongo `192.168.4.76:27017` | opt-in live leg | ✓ **port OPEN** | — | localhost container `mongo:7` (**local dev container is on 27019**) |
| DGX Neo4j `192.168.4.76:7687` | opt-in live leg | ✓ **port OPEN** | — | localhost container `neo4j:5-community` |
| DGX Postgres `192.168.4.76:5432` | opt-in live leg | ✓ **port OPEN** | db `parkavedb` | localhost container `postgres:16` / testcontainer |
| `NEO4J_PASSWORD`, `PGPASSWORD` for the DGX | opt-in live leg | ✗ **not in this environment** | — | GitHub Actions secrets + fail-fast precondition step, per the `ANTHROPIC_API_KEY` pattern |
| `slopcheck` | package legitimacy gate | ✓ | 0.6.1 (user install; note: no `--json` flag in this version) | — |

**Missing with no fallback:** DGX credentials. The opt-in leg cannot be *proven*
green from this machine; it must be dispatched in Actions with secrets configured,
which is a Dave-facing prerequisite, not a code task.

**Missing with fallback:** `langchain-mcp-adapters` — the raw-`mcp`-in-a-node path
removes the need entirely.

---

## Package Legitimacy Audit

Phase 16 is examples + documentation and **should install nothing new**. One
candidate surfaced and is recommended *against*.

| Package | Registry | Age | Downloads | Source repo | slopcheck | Disposition |
|---|---|---|---|---|---|---|
| `langchain-mcp-adapters` | PyPI | established | — (not measured) | langchain-ai org (unverified in this session) | `[OK]` — *"Name looks like LLM bait but package is established"* | **NOT RECOMMENDED.** Tagged `[ASSUMED]`: the name came from training data, not from official docs or Context7, and registry existence alone does not confer verification. Use `mcp.ClientSession` directly (zero new dependency). If the planner takes this path anyway, gate it behind a `checkpoint:human-verify` and pin exactly, per the `neo4j==6.2.0` precedent. |

**Packages removed due to `[SLOP]`:** none.
**Packages flagged `[SUS]`:** none.

Every other package this phase touches is **already pinned in `pyproject.toml`**
and was audited in its originating phase (`neo4j==6.2.0` and `pymongo==4.17.0` in
15.2-RESEARCH; `google-adk==2.5.0`, `claude-agent-sdk==0.2.128`,
`langgraph==1.2.9` in 06-RESEARCH; `anthropic==0.120.2` in 13.1-RESEARCH).

---

## Risks and Landmines

Ranked by expected cost to the phase.

### R-1 (HIGHEST) — `tutorial/adopters-guide.md` is a six-example single point of coupling
447 lines, 35 includes, six of the ten examples. It cannot be moved incrementally
and it is the day-1 narrative every other page defers to. Any wave decomposition
that touches it before all six of its sources exist leaves `make docs-strict` red
across every parallel worktree. **Mitigation:** treat it as a terminal-wave
deliverable, and let the new Section-1/2/3 tutorial pages be *new files* in a new
nav position while the old guide is deleted in one commit at the end.

### R-2 (HIGH) — three gate-checker suites fail at HEAD and one of them needs a `src/` edit
`tools/publish_scan_tests/test_docstring_leaks.py` fails because
`ProductClassDeclaration`'s docstring in `src/ccf/controlplane/artifacts.py`
trips the whitepaper shingle scan with **20 hits**. Fixing it edits `src/`, which
criterion 10 forbids. Leaving it means CI's `docs` job is red on a step `make ci`
never runs — so the phase cannot honestly claim green. **This is a decision, not
a task.** See Q-1.

### R-3 (HIGH) — the FIBO data cannot answer the adoption argument's own question
F-1. Multi-hop ownership does not exist in the dataset; `ownershipPercent` is on
entities, not edges. Criterion 7's worked demonstration and D-03's stated teaching
property both depend on it. **Mitigation:** make the data extension an explicit,
requirement-bearing deliverable in an early wave, so downstream example and page
work is not written against data that does not exist.

### R-4 (HIGH) — two of the three Section-2 harness client legs do not exist
F-2. Criterion 3 says "all three harnesses"; the tree ships bare-MCP, Anthropic
SDK and ADK. LangGraph-as-MCP-client and Claude-Agent-SDK-as-MCP-client are both
new work, and the LangGraph one has no in-tree precedent at all. **Mitigation:**
spike the LangGraph leg early against the *existing* `examples/external` server
before the greenfield fabric exists, so a transport surprise surfaces in week one.

### R-5 (MEDIUM-HIGH) — "always-on CI stays network-free" vs. what CI already does
D-06 locks sqlite+memory always-on and the four DGX as opt-in. But `ci.yml`'s
`test` job **already runs all four other substrates always-on** as blocking
service containers with `CCF_REQUIRE_*=1`. A reviewer will ask why the example
matrix is weaker than the conformance matrix. The answer is defensible (the
`examples` job has no service containers, and DGX ≠ container), but the planner
should state it explicitly rather than let it read as an oversight. **Do not
resolve this by adding containers to the `examples` job without a ruling** — that
is a third option D-06 did not authorize.

### R-6 (MEDIUM) — the KYC/UBO spine vs. D-IMPL-52's horizontal domain mix
D-03 makes KYC/UBO *the* spine; D-IMPL-52 and CLAUDE.md §9 require a horizontal
mix of domains across the suite specifically because *"a suite that visibly
crosses domains demonstrates generality more convincingly than a single neutral
domain held constant."* A suite where every example is KYC contradicts the ruling
that governs the suite. **Mitigation:** the planner's discretion over
section-to-example mapping is the lever — e.g. Section 1 on KYC (where the data
lives), Sections 2–3 on other domains, with the UBO question reserved for the
adoption argument and Section 1's first justification of typed products. Flag as
Q-3.

### R-7 (MEDIUM) — the `docs-strict` gate is not the only thing that must stay green
Four *other* standing checks constrain the rewrite and are easy to forget:
the diagram **bijection** (`test_diagram_coverage.py`), the mkdocstrings
rename gate (`test_mkdocstrings_gate.py` — runs the real config over a copy of
the real tree), the citation lint (`cite01/02/03` in `make lint`), and the
`INCLUDE_ALLOWED_PREFIXES` positive allowlist. A nav restructure that orphans a
`.mmd`, or a new page citing `file.py:NNN` with a backticked anchor, fails a gate
in a job most people are not watching.

### R-8 (MEDIUM) — the superseded-claim sweep is still open in `examples/01`–`04`
deferred-items records it as **STILL OPEN**, with the note that *"the enumeration
below this entry is a subset"* and that it has under-counted six times. Those four
directories retire under D-07, which closes that half for free — **but the same
false claims may be copied forward into the new examples if anyone writes the new
artifacts by reference to the old ones.** The corrected wording to converge on is
in `examples/05-workflow-hitl/artifacts/manifest.yaml` and the three corrected
`public/` pages. `docs/surface-changes/` + `docs/SURFACE-CHANGES.md` (38 candidate
sites) remain open and are dated per-plan records — a judgment, not a mechanical
fix.

### R-9 (MEDIUM) — the four Gate-2 tripwire residuals inherit here
R4-WR-03 (loop-carried rebinding out of reach), R5-WR-01 (`_Binding.until` covers
the comprehension's outermost iterable — a **measured bidirectional regression**),
the augmented-assignment mutable-set opacity, and the attribute/subscript
`global`/`nonlocal` exception. deferred-items places all four in Phase 16. None is
a documentation task; each is a `tests/products/test_gate_two_call_shape.py`
change or a docstring-limits correction. **They are inherited, not scoped** — the
planner should decide explicitly whether to take them (and R5-WR-01 needs the
outermost-iterable **walrus** case measured, which no reviewer did) or carry them
again with Dave's word.

### R-10 (LOW-MEDIUM) — retiring `tests/examples/test_surface_audit.py`'s baseline
ERGO-03's before/after measurement is anchored on a `docs/surface/examples/before/`
baseline frozen at Phase 15's start. A greenfield suite makes the comparison
meaningless, and the tool's own comment says re-freezing mid-phase *destroys the
comparison*. Deleting the test silently would erase a shipped requirement's
evidence. Q-4.

### R-11 (LOW) — `make examples` scale
The `examples` job carries `timeout-minutes: 20` for ten examples, several of
which spawn subprocesses. A six-backend matrix run inside the examples job would
blow that budget. Keep the matrix in the `test` job (or its own job) and keep the
`examples` job a single-backend smoke run.

---

## Open Questions for the Planner

**D-01..D-12 in CONTEXT.md are LOCKED. Nothing below reopens one.** Where a
locked decision meets a tree fact awkwardly, it is filed as a finding for the
planner to surface, not resolved here.

### Q-1 — The `ProductClassDeclaration` docstring fails the publish scan, and fixing it edits `src/`
**Known:** `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_
reproduces_whitepaper_body_text` fails at HEAD with 20 shingle hits against
`src/ccf/controlplane/artifacts.py`. CI's `docs` job runs this suite.
**Unclear:** whether a docstring correction counts as "the fabric changed" under
criterion 10.
**Recommendation:** it does not — no behavior, no signature, no contract changes,
and mkdocstrings publishes that docstring, so it is squarely *documentation*. But
criterion 10 is Dave's wording. Surface it as a one-line scope clarification
alongside D-02's ruling rather than deciding it inside a plan.

### Q-2 — Does the D-02 ruling also settle what `assembly_mode` describes?
**Known:** `assembly_mode` is on the product class *and* on `ModelVersionRecord`.
CONTEXT `<specifics>` promises Section 1 introduces `assembly_mode: algorithmic`
as *a real choice with two siblings arriving later*.
**Unclear:** if Mode 2 packaging attaches *above* `serve()`, does the product
class's `assembly_mode` describe the substrate (always `algorithmic`) or the
delivered artifact (`llm_packaged`)? Section 1's prose cannot be written honestly
without the answer.
**Recommendation:** fold this sub-question into the D-02 entry rather than
minting a second ruling.

### Q-3 — How many examples share the KYC/UBO domain? (D-03 × D-IMPL-52)
**Known:** D-03 makes KYC/UBO the spine; D-IMPL-52 and CLAUDE.md §9 require a
horizontal domain mix; today's suite is deliberately mixed (banking, e-commerce
`atlas-commerce`, financial services `meridian-bank`).
**Unclear:** whether "spine" means every example, or the through-line the
adoption argument and Section 1 use.
**Recommendation:** the narrower reading. Section-to-example mapping is explicitly
Claude's discretion, so this is the planner's call — but it should be *made
visibly*, with the D-IMPL-52 tension named, not fallen into.

### Q-4 — What happens to ERGO-03's `test_surface_audit.py` baseline?
Three options: retire the test with a recorded rationale; re-baseline against the
greenfield suite (destroying the Phase 15 comparison the requirement's evidence
rests on); or freeze the current before/after as a historical record and stop
running it. **Recommendation:** freeze and retire the *running* test, with the
measured figures moved into the phase record — but this touches a Complete
requirement's evidence, so surface it rather than decide it.

### Q-5 — Does the phase take the four inherited Gate-2 tripwire residuals?
R-9. They are real, measured, and placed in Phase 16 by deferred-items, but none
is documentation work and R5-WR-01 needs a measurement no one has made.
**Recommendation:** carry them with an explicit ruling rather than absorbing them
silently; a phase that quietly takes on `tests/products/` mechanism work while
claiming "no fabric changed" invites exactly the criterion-10 argument Q-1 raises.

### Q-6 — Does `docs/SURFACE-CHANGES.md` publish into the site?
SURFACE-AUDIT §5.4 open editorial question, explicitly carried to Phase 16.
Interacts with A-2's maintainer page and with `pub02-internal-path` (the fragments
reference `.planning/` paths).

### Q-7 — Does DI-15.4-05 / F2 need to be ruled before `write-a-graph-backend-adapter.md` is rewritten?
The public-vs-private adapter surface, and `substrate_vocabulary` deriving from
in-tree adapters only, are awaiting Dave. That how-to page is the one this phase
must rewrite most substantially, and it would document exactly the surface under
question. **Recommendation:** either get the ruling in the same package as D-02,
or write the page to the surface that is settled and state the open question in
the phase record rather than in the published page.

### Q-8 — Should `make ci` compose the three gate-checker suites?
deferred-items names it as two separable Phase-16 items ("fix the three, and
decide whether `make ci` should compose the gate-checker suites so the claim it
makes becomes true"). Doing it makes `make ci` slower and truer.

---

## Suggested Plan Decomposition

**Advisory input to the planner, not a plan.** The organizing constraint is P-1:
**every wave must end with `make docs-strict` green**, which means an example and
every page in its §A.2 row move together. The suggested shape front-loads
everything that could invalidate later work.

### Wave 0 — Unblock and rule (serial, small, checkpointed)

| Plan | Scope | Why first |
|---|---|---|
| **16-01** | The ruling package: D-02 (`D-IMPL-94`, Mode 2 above `serve()`, incl. Q-2's sub-question), plus Q-1's criterion-10 clarification, plus a decision on Q-5 and Q-7. Mint DOCS-07..NN; re-home DEMO-01..03 and EXAM-01..05 in `REQUIREMENTS.md`. **No code.** | Every later plan's acceptance criteria depend on these. `checkpoint:human-verify`. |
| **16-02** | Fix the three gate-checker failures; repoint `test_snippet_gate.py`'s `SNIPPET_SOURCE`/`SECTION`; decide + implement Q-8. Establish the new test-module skeletons listed under Wave 0 Gaps as *failing-for-the-right-reason* stubs. | Nothing can claim green until these are green. |
| **16-03** | **FIBO data extension** (F-1): corp→corp `hasOwnershipInterestIn` edges with per-edge `ownershipPercent`, loaded to all four DGX stores via the existing `load_*.py` shape; plus in-repo fixtures derived from it. Document the extension. | Every KYC/UBO example and the adoption argument are written against this. |

### Wave 1 — The seam and the runner (parallel-safe)

| Plan | Scope | Depends on |
|---|---|---|
| **16-04** | The **parameterized runner**: one example body, `--backend`, per-backend thin manifests, connection resolver mirroring `tests/conftest.py::fabric_boot`, opt-in-leg config artifact on the `live.yaml` precedent. Plus `tests/examples/test_backend_matrix.py` (sqlite+memory always-on). | 16-01, 16-02 |
| **16-05** | **CI wiring**: `make example-*`/`make examples` recomposition, matrix job placement (Q/R-11), the DGX opt-in job in `live-legs.yml` with secret-gated fail-fast, socket guard for the network-free proof, the no-credential-in-tree check. | 16-04 |
| **16-06** | **The spine/deployment separation convention** (D-11): the file-split + canonical marker set + `[ADAPT]`/`[MECHANISM]` header extension, realized once as a reference and pinned by `tests/examples/test_spine_separation.py`. | 16-01 |

### Wave 2 — Section 1 (the deterministic path)

| Plan | Scope | Depends on |
|---|---|---|
| **16-07** | Section 1 example(s): agent-free deterministic assembly on KYC/UBO, six axes of `G` made inspectable, four operator categories, `assembly_mode` introduced as a choice. Plus `test_section_one_is_agent_free.py` with its negative control. | 16-03, 16-04, 16-06 |
| **16-08** | Section 1 published pages + nav; retire `concepts/pillars/data-context.md`'s agent-first framing (D-12); re-cut `reference/artifacts/{control-plane-artifacts,product-registration}.md`; A-8 discharge; A-1 convention page. **Retire `examples/00-quickstart`** in the same commit as its three dependent pages. | 16-07 |

### Wave 3 — Section 2 (external agents over MCP) — the riskiest wave

| Plan | Scope | Depends on |
|---|---|---|
| **16-09** | The MCP-egress fabric side for Section 2 + the **bare-MCP** and **ADK** client legs (rebuilds of proven patterns) + the AST-upgraded zero-import guard with its negative control. | 16-07 |
| **16-10** | The **LangGraph** and **Claude-Agent-SDK** client legs (F-2, new work). *Spike this against the existing `examples/external` server in Wave 1 if capacity allows.* | 16-09 |
| **16-11** | Section 2 published pages + nav; retire `examples/external/00-hello-context` and `examples/03-harness-portability`; re-cut `how-to/bind-a-harness-adapter.md`. | 16-09, 16-10 |

### Wave 4 — Section 3 (advanced CCF)

| Plan | Scope | Depends on |
|---|---|---|
| **16-12** | Embedding CCF in a host application + cross-process/A2A (absorbs `04-cross-process`) + ArtifactStore swap (absorbs `07`). | 16-09 |
| **16-13** | Agentic skills within CCF: archetype → agent artifact → factory → skill catalog/grant/revoke → workflow + HITL → replay (absorbs `01`, `02`, `05`, `06`). Must state the CINV-03 "agents as governed identity, not reasoners" fact plainly. | 16-12 |
| **16-14** | Section 3 published pages + nav; re-cut `how-to/{grant-and-revoke-a-skill,run-agents-cross-process,compose-a-workflow-with-hitl,swap-the-artifact-store}.md` and `reference/artifacts/{agent-definitions,prompt-artifacts,skill-catalog,skill-grants,task-definitions,workflow-definitions}.md`; retire `01`, `02`, `04`, `05`, `06`, `07`. | 16-12, 16-13 |

### Wave 5 — The argument, the stale surface, and the close

| Plan | Scope | Depends on |
|---|---|---|
| **16-15** | **The adoption-argument page** (D-10, criterion 7) + `test_adoption_argument.py`; the UBO worked demonstration; the passage-anchor honesty caveat. | 16-03, 16-07 |
| **16-16** | **A-3 sweep**: rewrite `how-to/write-a-graph-backend-adapter.md` against the registry seam (subject to Q-7), `how-to/security-and-deployment.md` for `backend_secrets`, `reference/protocols/storage-and-graph.md` for `GraphQuery`/pushdown; document `ccf backends list` / `GET /backends`. **A-2**: the surface-toolchain maintainer page (subject to Q-6). | 16-01 |
| **16-17** | **Terminal retirement**: delete `tutorial/adopters-guide.md` and `tutorial/demo-walkthrough.md`, retire `examples/08-e2e-demo`, final nav, `test_no_stale_example_paths.py` green, `test_gate_two_wording.py` green, `test_advisory_discharge.py` green, `test_documented_commands_exist.py` green. | all |
| **16-18** | Phase close: full `make ci` + gate-checker suites + `make legs` + one dispatched DGX run; `make gate-16` no-`src`-diff assertion; requirements table; **then** `/gsd-review --all` on shipped code per §3.1. `checkpoint:human-verify`. | all |

**Parallelism note.** Waves 2, 3 and 4 each end with a page-retirement plan that
must land atomically with its example deletions. Running 16-08, 16-11 and 16-14 in
parallel worktrees is safe *only* if `tutorial/adopters-guide.md` is untouched
until 16-17 — which is why it is deliberately terminal.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | `langchain-mcp-adapters` is the langchain-ai org's official MCP binding for LangGraph | C.2, Package Audit | Low — it is recommended *against*; the zero-dependency path avoids the question entirely. `[ASSUMED]` — name from training data, not from official docs or Context7; `slopcheck` `[OK]` does not confer verification. |
| A2 | The FIBO dataset contains **four** jurisdictions (`US-DE`, `US-NY`, `DE`, `GB`) as CONTEXT D-03 states | B.4 | Low. Three were directly observed (`US-DE`, `US-NY`, `DE`); `GB` was not read. If only three exist, D-03's "four jurisdictions" teaching claim needs a one-word correction. |
| A3 | The DGX stores currently hold the same 14/11 dataset as the JSONL files, unmodified | B.4 | Medium. Ports are open but no query was issued (no credentials in this environment). If the stores diverge from the files, the matrix's cross-store equivalence assertion is measuring the wrong thing. **The planner should have Wave 0 verify store contents against the files before writing examples against them.** |
| A4 | Editing a `src/` docstring does not constitute "the fabric changed" under criterion 10 | Q-1, Risks R-2 | Medium — it is a scope reading, and Dave's wording governs. Filed as Q-1 rather than assumed silently. |
| A5 | `content_hash(ContextProductContract)` is genuinely substrate-independent | B.2, V-4 | Medium-low. Derived from reading every field of `ContextProductContract` and `ProductLineage` — none is substrate-dependent, and `expires_at` derives from an authored instant. **Not executed across two backends.** A one-hour spike in Wave 1 would upgrade this to VERIFIED and de-risk criterion 4 entirely. |
| A6 | The seven-heading example README template is still the shipped contract | A.1, C-5 | Low. Verified present in `00-quickstart/README.md` and `external/00-hello-context/README.md`, and asserted by `run.py` PASS 4 + `test_ext00_serve_output.py::test_the_readme_keeps_its_seven_template_headings`. |
| A7 | `D-IMPL-94` is the next free decision id | V-10, 16-01 | Low. Highest observed in `docs/DECISIONS.md` is `D-IMPL-93`. Re-check at planning; the phase may also want `DI-16-NN` in-phase design-issue ids per the 15.2/15.4 precedent. |

---

## Sources

### Primary (HIGH confidence — read or executed against the tree at `84f4501`)
- `src/ccf/graph/registry.py`, `src/ccf/graph/backends/*_write.py` — adapter registration seam; enumerated by execution
- `src/ccf/boot.py`, `src/ccf/deployment/{__init__,manifest,binder}.py` — boot + wiring surface
- `src/ccf/controlplane/artifacts.py` — `DeploymentManifest`, `ManifestEntry`, `ProductClassDeclaration`
- `src/ccf/products/{contract,gates}.py`, `src/ccf/replay/{record,serve}.py`, `src/ccf/projection/{plan,engine}.py`, `src/ccf/operators/{categories,params,planner,registry}.py`, `src/ccf/graph/protocols.py`, `src/ccf/contracts/claims.py`, `src/ccf/halflife/`, `src/ccf/agents/__init__.py`, `src/ccf/skills/__init__.py`, `src/ccf/mcp/{client,acquisition}.py`
- `runtime/ccf_runtime/mcp/{egress,experience,auth}.py`, `runtime/ccf_runtime/cli/commands/backends.py`, `runtime/ccf_runtime/http_api/routes/backends.py`, `runtime/ccf_runtime/adapters/{adk,claude_agent,langgraph}/`
- `mkdocs.yml`, `Makefile`, `pyproject.toml`, `.github/workflows/{ci,live-legs}.yml`
- `tools/publish_scan.py`, `tools/lints/{__main__,no_hardcoding,harness_imports,substrate_names,citations}.py`, `tools/docs_tests/*`, `tools/publish_scan_tests/*`
- `public/**/*.md` (41 pages), `public/diagrams/*.mmd` (11)
- `examples/**` (10 directories), `tests/examples/*` (17 modules), `tests/conformance/test_graphstore.py`, `tests/conftest.py`
- **Executed:** `declared_names()`/`resolve()` enumeration; `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q` (453 passed / 3 failed); DGX TCP probe on 4 ports; `slopcheck install langchain-mcp-adapters`; the page→example table generator
- `/home/parkave/fluree/examples/fibo/{mongo-entities,mongo-relationships,fibo-instances}.json`, `compare_backends.py`

### Primary (HIGH confidence — project canon)
- `CLAUDE.md` (rev 4) — §1, §3.1, §6.4, §7.1, §7.3, §9, §10, §11, §13, §15
- `.planning/phases/16-…/16-CONTEXT.md` (D-01..D-12), `16-DISCUSSION-LOG.md`
- `.planning/ROADMAP.md` Phase 16 entry (10 success criteria), `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md` — the authoritative 11-residual inheritance list
- `docs/SURFACE-AUDIT.md` §2.3, §2.4, §3, §5.3 (A-1..A-8), §5.4, §6
- `docs/DECISIONS.md` — D-IMPL-08, D-IMPL-22 (twice amended), D-IMPL-24, D-IMPL-52, D-IMPL-57 (correction), D-IMPL-71, D-IMPL-72, D-IMPL-80, D-IMPL-84/85, D-IMPL-86, D-IMPL-93
- `.planning/phases/14-documentation-suite/14-CONTEXT.md` — D-07..D-20

### Secondary (MEDIUM confidence)
- `docs/surface-changes/README.md` — the only existing description of the surface toolchain (A-2's raw material)

### Tertiary (LOW confidence — flagged, not relied on)
- `langchain-mcp-adapters` as the LangGraph MCP binding — training data + `slopcheck [OK]` only; **recommended against** for exactly this reason

---

## Metadata

**Confidence breakdown:**
- Retirement inventory & page→example table: **HIGH** — generated mechanically from the tree, not transcribed
- Backend registry API & parameterization: **HIGH** — executed, not read
- CI / publication mechanics: **HIGH** — read in full from `Makefile`, `ci.yml`, `live-legs.yml`, `mkdocs.yml`, `publish_scan.py`
- Gate-2 wording sites (criterion 8): **HIGH** — every site opened and read
- Carried advisories A-1/A-2/A-3/A-8: **HIGH** for current state; **MEDIUM** for what "discharged" means (an editorial judgment)
- FIBO data contents: **HIGH** for the files; **MEDIUM** for the DGX stores (ports probed, contents not queried — A3)
- Section 2 harness legs: **MEDIUM** — the gap is verified; the LangGraph remedy is a design recommendation with no in-tree precedent
- Cross-backend product byte-identity: **MEDIUM** — derived from contract fields, not executed (A5)

**Research date:** 2026-08-09
**Valid until:** ~2026-09-08 for the tree inventory (30 days; but **invalid the moment any wave lands**, since the page→example table is a snapshot of a tree this phase deletes). Re-run the table generator at the start of each wave rather than trusting this copy.
