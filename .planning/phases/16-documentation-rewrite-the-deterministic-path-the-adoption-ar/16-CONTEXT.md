# Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument - Context

**Gathered:** 2026-08-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Rebuild the adopter-facing **examples suite and published documentation** against
the post-Phase-15 surface, organized as four sections that teach CCF in
increasing depth. Phase 16 delivers **Sections 1–3**, all against mechanism the
SDK demonstrably ships today. **Section 4 is Phase 17's**, arriving with the
fabric that enables it.

- **Section 1 — "Hello CCF."** Deterministic assembly only, no agents. A
  beginner's path through Context Products, Context Operators, and the six axes
  of `G(E, R, T, P, Π, L)`. Simple examples.
- **Section 2 — External agents over MCP.** Client agents reach CCF with **zero
  CCF dependency**. Deterministic only; no CCF-internal agents. Claude Agent SDK
  and Google ADK legs (ADK is what the bank runs), plus LangGraph per D-IMPL-24.
- **Section 3 — Advanced CCF.** Embedding CCF in your own application, and
  developing agentic skills within CCF against a real use case. Claude Agent SDK
  and Google ADK. The section most likely to be used for real problems.
- **Section 4 — LLM packaging and agent swarms.** *Phase 17.* Assembly Mode 2
  (`llm_packaged`) and Mode 3 (`swarm_assembled`).

**⚠ SCOPE EXPANSION — needs a ROADMAP.md update before planning.** The roadmap's
Phase 16 entry reads "one document, two sections … re-cut snippet markers." This
discussion expanded it, on Dave's authority (2026-08-09), to a **greenfield
rewrite of the examples suite** plus a four-section documentation rewrite plus a
six-backend CI matrix. Every original success criterion is absorbed; nothing is
dropped. The ROADMAP entry must be updated through `gsd-sdk query roadmap.*`
(never a direct edit — universal anti-pattern #15) before `/gsd:plan-phase 16`.

**Not in this phase:** any fabric change. No Mode 2 packaging stage, no Mode 3
swarm coordinator, no Pattern 5 / `src/ccf/unstructured/`, no tier-3 external
sources. Phase 16 is examples and documentation only — with one exception, a
paper ruling (D-01 below) that writes no code.

</domain>

<decisions>
## Implementation Decisions

### Structure and sequencing

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

### Use case and data

- **D-03: KYC / UBO resolution and refresh is the use-case spine.** Chosen
  because it is what the FIBO data on the DGX *natively is*. Verified contents of
  `mongo-entities.json` / `mongo-relationships.json`: 14 entities (6
  Corporations, 4 Parties, 3 Addresses), 11 relationships
  (`hasOwnershipInterestIn` ×4, `hasControllingInterestIn` ×1, `isRelatedTo` ×6),
  carrying `kycStatus`, `riskRating`, `onboardingDate`, `clientType`, `lei`,
  `jurisdiction`, `ownershipPercent`, `role: "Ultimate Beneficial Owner"`,
  `nationality`, `dateOfBirth`.

  What makes it a good CCF teaching case, specifically:
  - **Traversal is the point.** Multi-hop ownership chains are what a graph does
    and what chunk retrieval does badly.
  - **Policy is non-trivial.** Four jurisdictions (US-DE, US-NY, DE, GB) means
    real regulatory-regime divergence in the `P` axis, not a placeholder.
  - **Similarity is non-trivial.** Two planted near-duplicates ("Acme Global
    Trading Corporation" vs "Acme Corporation Inc.") give name-matching something
    to get wrong.
  - **A real boundary case exists.** Sarah Chen sits at exactly 25.0% ownership —
    the FinCEN CDD beneficial-ownership threshold.
  - **It extends to Section 4 cleanly.** Mode 2 packages a KYC review narrative;
    Mode 3 reconciles UBO across correspondent banks that genuinely cannot share
    customer data.
- **D-04: FIBO stores are an enterprise source CCF reads at L1 — never loaded
  wholesale into CCF's graph.** The two-sided model, confirmed with Dave:
  - **Read side (enterprise estates).** Data marts, KGs, databases, lakes — all
    fair game as sources for a Context Product. Reached through L1 ingress
    adapters: CDC (`runtime/ccf_runtime/cdc/adapter.py`), MCP client
    (`src/ccf/mcp/client.py`), file/stream. Plus `src/ccf/mcp/acquisition.py` for
    L4/L5 decision-time acquisition. **None of these are registry "backends."**
  - **Write side (CCF's own Context Graph, L3).** This is what the six backends
    are. `boot()` takes `backend: str` — required, no default, **exactly one** —
    because the boot token is minted once per graph and single-writer keys on
    graph identity. CCF's own KG never splits read and write across stores.
  - **Read store and write store are independent.** In the examples they may be
    different databases on the same DGX server.
  - **The distinction that matters:** *selective assembly* (CCF reads what a
    specific Context Product needs, resolves entities, binds policy, records
    lineage) versus *wholesale replication* (mirroring the estate into CCF's
    graph). The second is explicitly rejected — Dave: *"The CCF was never in the
    business of creating KGs from enterprise data … that would be a disaster."*
- **D-05: Temporal signal is authored as an L1 observation stream, as today.**
  Investigated and confirmed a non-issue: the current suite already exercises
  half-life and Context Debt fully — `examples/01-agent-basics` ships
  `half-life-table.yaml` (per-observation-type `λ_c` with `decay_driver` and
  `supersession_event` rows) and `debt-evaluation.yaml`, whose dated observations
  produce an assessed `D_c` landing in a CAR routing state. Signal arrives via
  `events.yaml`. The FIBO stores holding static entity state is **not** a gap:
  L1 is signal, L3 is state.

### Backends

- **D-06: One parameterized runner, matrix-proven across all six.** One example
  body; backend selected by artifact or env. A CI matrix runs the suite across
  `sqlite`, `memory`, `postgres`, `neo4j`, `mongo`, `fluree` and asserts
  equivalent Context Products. This proves substrate-neutrality as a **property**
  rather than by repetition, and is precisely what the Phase 15.4 backend
  registry seam was built for — six literal per-backend variants would re-fork
  the code that phase just un-forked.
  - **CI split per D-10/D-11:** `sqlite` + `memory` in always-on CI
    (deterministic, offline); the four DGX databases as an **opt-in live-legs
    job**. Always-on CI must stay network-free.
  - **Connection settings** come from `compare_backends.py`: Fluree
    `192.168.4.76:8090` (ledger `fibo:main`), Mongo `192.168.4.76:27017`, Neo4j
    `bolt://192.168.4.76:7687`, Postgres `192.168.4.76:5432` (db `parkavedb`).
    All env-overridable; **no credential may enter the tree.**
  - Greenfield makes this *cheaper*, not dearer: every current example hardcodes
    `backend: sqlite` in its artifacts, so parameterization is a design premise
    rather than a nine-example migration.

### Examples suite

- **D-07: Greenfield the examples; rewrite the docs.** Retire `examples/00`–`08`
  and build the sections fresh against the new seam. **Coupling the planner must
  respect:** those examples are the snippet source of record for the entire
  `public/` tree (Phase 14 D-07/D-10), so all ~50 published pages move in the
  same phase. There is no partial state.
- **D-08: Existing requirements re-home into the new suite.** DEMO-01..03 (the
  banking fraud-ring demo, currently `examples/08-e2e-demo`) and EXAM-01..05 map
  onto whichever new examples cover them, rather than being retired. Coverage
  stays traceable without minting duplicates. Phase 16 additionally mints
  DOCS-07..NN for the documentation work itself.
- **D-09: All three harnesses stay in examples.** Claude Agent SDK, Google ADK,
  and LangGraph. Harness neutrality is mission success condition 3 (CLAUDE.md
  §1), D-IMPL-24 ruled all three ship v0 reference adapters, and a three-way
  byte-identical assertion is a materially stronger claim than a two-way one.
  Costs a third leg in every agent-bearing example across Sections 2 and 3.

### Documentation

- **D-10: The adoption argument gets its own page, naming alternatives.** Closes
  the second half of UAT gap G-01, which found **zero** hits across the entire
  published surface for comparative rationale ("why not just", "instead of
  building", "rather than building", "compared to"). The page names what teams
  build instead — RAG over a vector store, hand-rolled context assembly, a
  semantic layer plus prompt templates — and states what breaks: no replay, no
  policy binding at assembly, no lineage to a passage, no staleness measure.
  - **The worked demonstration is the UBO question.** "Who ultimately owns Acme?"
    requires traversing an ownership chain, aggregating percentages across hops,
    and filtering by jurisdiction-specific thresholds. A vector store over
    chunked documents structurally cannot answer it, because the answer lives in
    the *relationships*, not in any passage.
  - Accepted cost: the docs now owe a defence of these comparisons as the
    alternatives evolve.
- **D-11: Snippet legibility is achieved by structural separation in the example
  sources.** Each example physically separates the **CCF call spine** from
  **deployment code** (the projection Π, domain artifacts, scenario setup) into
  distinct, separately-markered regions. The boundary is visible to anyone
  reading the repo — not only in rendered docs — which is where the original
  complaint came from: *"I can't tell from looking at the code which code is
  example code and which code is required by the CCF."* No new marker vocabulary
  beyond Phase 14's D-07 named markers.
- **D-12: G-01's framing defect is fixed by construction, not by editing.**
  Section 1 is deterministic and agent-free, so the agent-first mental model the
  UAT condemned cannot survive the new structure. Specifically retired: the
  Concepts data-context page opening on *"how does an agent get at first-party
  records"*, the buried line-133 acknowledgement that the SDK ships no agents,
  and the absence of any how-to for deterministic Context Product assembly.

### Claude's Discretion

- Section-to-example mapping (how many examples per section, and their
  boundaries) — planner-level, given the section definitions above.
- Whether the six-backend matrix is one CI job or several.
- How DEMO-01..03's fraud-ring scenario re-homes given the KYC/UBO spine — the
  two are compatible (both are counterparty-network problems) but the mapping is
  a planning call.
- Nav structure within the four sections, inside Phase 14's Diátaxis frame
  (D-15..D-18), which stands unless a section demands otherwise.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and inheritance
- `.planning/ROADMAP.md` — Phase 16 entry (goal, what it inherits, the eleven
  15.1 residuals, the two process findings). **Note the scope expansion flagged
  in `<domain>` above; the entry needs updating before planning.**
- `.planning/phases/14.1-documentation-the-deterministic-path-the-adoption-argument-i/14.1-SUPERSEDED.md`
  — Dave's seven rulings of 2026-08-03, including the two-section structure
  (ruling 5), banking domain from the whitepaper's own scenarios (ruling 6), and
  the snippet re-cut (ruling 7). Also the three findings that survive: A2A is
  already demonstrated in `04-cross-process`; criterion 5's external example
  exists; and the `run_gates()` two-independent-sources invariant that bounds
  abstraction.
- `.planning/phases/14-documentation-suite/14-HUMAN-UAT.md` — **G-01** (the
  agent-first framing defect, with per-page evidence) and **G-02** (the two
  undemonstrated Assembly Modes, and Dave's build-before-documenting ruling).

### Rulings that bind this phase
- `docs/DECISIONS.md` — **D-IMPL-24** (all three harnesses ship v0 adapters —
  binds D-09); **D-IMPL-52** (examples are a horizontal mix of domains; example
  00 and the I.1 slice fixtures are banking); **D-IMPL-71** (docs toolchain and
  publishing posture; nothing is hosted); **D-IMPL-72** (`make ci` includes
  `docs-strict`); **D-IMPL-86** (design E2 — the projection-requirements
  artifact and the boot binder; **what Gate 2 actually verifies**);
  **D-IMPL-28** (definition artifact format); **D-IMPL-08** (Pattern 5 stage
  Protocols — RESOLVED 2026-07-25 but never built, which is why Section 4 waits).
- `.planning/phases/14-documentation-suite/14-CONTEXT.md` — Phase 14's D-01..D-22
  stand unless superseded here: `public/` as the published tree (default-deny by
  existence), the post-build publish-safety scan, named snippet markers, generated
  schema and API reference, Diátaxis nav, and the whitepaper cross-reference
  discipline (section numbers and titles only, never body text).

### The URGENT constraint
- **Phase 16 must not document a self-satisfying gate.** Gate 2 (INV-CH7-47) is
  **assembly-path integrity** — the claim transcribed into the Contract equalling
  the engine's execution of the plan — **not** a comparison of two independently
  authored sets. `docs/DECISIONS.md` D-IMPL-86 carries the full derivation and
  the established fact that *"the engine is a faithful transcriber of the plan,
  not an independent witness."*
- Related, from `docs/SURFACE-AUDIT.md` §5.3 **A-4**: several
  `tests/examples/test_*_output.py` checks compare `required_operator_keys`
  against `operators_invoked` and document that editing the artifact moves both
  ends. **Phase 16 must not promote these as independence proofs.** The
  independent statements are the consumer-side ones and the artifact-vs-engine
  comparison.

### Carried advisories this phase owns
- `docs/SURFACE-AUDIT.md` §5.3 — **A-1** (document `from ccf.deployment import …`
  as the single preferred day-1 import; submodule FQNs are implementation
  detail); **A-2** (a maintainer-facing page for the surface toolchain —
  `tools/dump_surface.py`, `make surface`, baseline immutability); **A-3** (the
  published docs describe the pre-15 surface — this phase's core defect);
  **A-5** (no automated check exists for a mis-pointed snippet include; building
  one is this phase's concern); **A-8** (D-IMPL-80's *"role governs registration
  and pinning, never visibility"* needs explicit documentation — `role: load`
  artifacts are reachable on `BootedFabric.artifacts` and absent from the replay
  pin set, and the reference pages must say both).
- `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md` — **the
  authoritative inheritance list** for the eleven 15.1 residuals. Explicitly
  **not** `docs/SURFACE-AUDIT.md` §6.4, which predates the last four remediation
  rounds.
- `docs/SURFACE-AUDIT.md` §5.4 — the open editorial question of whether
  `docs/SURFACE-CHANGES.md` publishes into the site.

### Whitepaper — the specification
- `docs/CCF_Whitepaper_1-2.md` **§7.4** (Context Operators; the "Agent Swarms as
  Operator Realization" H3 that makes Section 4 additive; the counterparty
  worked composition), **§7.6** (Context Products, delivery, and the three
  Assembly Modes with their cost/quality/determinism tradeoffs), **§7.10**
  (Decision Replay, and the mode-invariance commitment), **§6.3** (the contract's
  nine elements), **§7.7** (Context Debt and half-life).

### The data and the substrates
- `/home/parkave/fluree/examples/fibo/compare_backends.py` — connection settings
  for the four DGX databases and the working per-substrate query shapes.
- `/home/parkave/fluree/examples/fibo/mongo-entities.json`,
  `mongo-relationships.json`, `fibo-instances.json` — the FIBO KYC/UBO dataset
  the use case is drawn from.
- `/home/parkave/fluree/examples/fibo/load_neo4j.py`, `load_postgres.py`,
  `load_mongo.py`, `fluree_to_mongo.py` — how the same logical data is shaped per
  substrate.

### Project canon
- `CLAUDE.md` — **§6.4** (No-Hardcoding Rule — why examples are code and
  artifacts side by side), **§7.1** (bidirectional MCP; the L1 ingress role that
  D-04 rests on), **§7.3** (harness neutrality; binds D-09), **§9** (the examples
  suite as the adoption contract, and the per-example discipline), **§10** (L1–L6
  and the two planes), **§11** (working principles), **§3.1** (the phase review
  protocol — the cross-AI panel is unsubstitutable).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The backend registry seam** (`src/ccf/graph/registry.py`, Phase 15.4) — six
  adapters declare themselves; core looks up rather than branching. This is what
  makes D-06's parameterized runner a lookup rather than a fork.
- **`examples/external/00-hello-context`** — already a banking credit-context
  fabric with **four zero-CCF-import consumer legs** (bare MCP, Anthropic SDK,
  Google ADK, Claude Desktop via `.mcp.json`), CI-asserted. Section 2's proven
  pattern even under greenfield; the *pattern* survives even though the code is
  rebuilt.
- **`examples/04-cross-process`** — runs a `ContextAssemblyAgent` in its own
  subprocess, serves one product over **MCP *and* A2A**, verifies Control Plane
  admission, and exercises a tampered-envelope refusal. Section 3's cross-process
  material.
- **`examples/01-agent-basics` artifacts** — `half-life-table.yaml`,
  `debt-evaluation.yaml`, `agent-debt-profile.yaml`: the working shape for
  teaching `λ_c` and `D_c`, reusable as a template for the KYC observation
  stream.
- **Phase 14's docs toolchain** — `public/` tree, `mkdocs.yml` nav, publish-safety
  scan, named snippet markers, mkdocstrings-generated reference. The machinery
  stands; the content is rewritten.

### Established Patterns
- **Code and artifacts side by side (§6.4).** An example whose code would still
  run meaningfully with its artifacts deleted has violated the No-Hardcoding Rule.
- **Artifacts carry `[ADAPT]` / `[MECHANISM]` markers** distinguishing
  deployment-tunable values from structural keys the factory interprets. This
  convention is a close cousin of D-11's structural separation and should inform it.
- **Always-on CI is deterministic and offline** (D-10/D-11 split). Anything
  network- or key-dependent is opt-in — which is why the four DGX databases
  cannot join the always-on job.
- **The Makefile mirrors CI command-for-command** (D-10). A docs or matrix target
  must be runnable identically locally and in Actions.
- **Every example declares `assembly_mode: algorithmic`** — verified across all
  nine. Vestigial today; becomes a real governance choice when Section 4 lands.

### Integration Points
- **`boot(backend=...)`** — the single parameterization point for D-06.
- **L1 ingress** (`runtime/ccf_runtime/cdc/adapter.py`, `src/ccf/mcp/client.py`) —
  where FIBO data enters as signal under D-04.
- **`public/` + `mkdocs.yml` nav** — the four sections must map onto (or
  deliberately restructure) the existing Diátaxis frame.
- **`tests/examples/test_*_output.py`** — greenfield retires these alongside the
  examples; the new suite needs equivalent CI assertions, kept **outside** the
  published snippets per the 14.1 finding that ~85 assertion/print lines were
  inflating apparent integration cost.

</code_context>

<specifics>
## Specific Ideas

- **"I can't tell from looking at the code which code is example code and which
  code is required by the CCF."** Dave's original complaint, 2026-08-03, is the
  phase's north star and the reason D-11 chose *structural* separation over a
  docs-layer legend. The test is whether someone reading the repo — not the
  rendered site — can see the boundary.
- **Section 1 is deliberately small.** "Hello CCF" generates one Context Product
  and teaches Context Products, Context Operators, and the six axes. It does not
  reach for agents, and its being agent-free is the structural fix for G-01
  rather than a stylistic choice.
- **Section 2's constraint is the demonstration.** The client has *no CCF
  dependency*. That is the primary adoption path — an external agent consuming
  governed context over MCP — and it must be visible in the client code's import
  list, which is exactly what `examples/external/` already proves.
- **The UBO question is the adoption argument.** "Who ultimately owns Acme?"
  demonstrates in one sentence why relationships-plus-policy beats
  retrieve-then-filter. It should appear in the adoption-argument page and again
  wherever Section 1 first justifies typed Context Products.
- **Section 4 makes Section 1's artifacts retroactively meaningful.** The
  `assembly_mode: algorithmic` line sitting in every artifact stops being
  boilerplate and becomes a governance decision a product owner defends. Section
  1 should introduce it as a real choice with two siblings arriving later, not as
  a constant.

</specifics>

<deferred>
## Deferred Ideas

- **A credit-memo example.** Explicitly deferred by Dave to a later phase
  (2026-08-09). It is the whitepaper's canonical Mode 2 exemplar (§7.6) and
  wants facilities, limits, exposure amounts and covenants loaded into the FIBO
  stores, plus Pattern 5 for passage-level lineage to a 10-K.
- **Tier-3 raw external sources** — reading an enterprise estate at *operator
  time* without it ever landing in L3. Deferred in Phase 15.2, explicitly
  designed-for (*"must not require a refactor to add"*). This is the fully
  structural version of "never load the estate," versus today's selective-ingest
  discipline. **Fabric work; belongs on the roadmap as its own entry.**
- **Pattern 5 / `src/ccf/unstructured/`** — D-IMPL-08 RESOLVED 2026-07-25, never
  built. Needed for document ingestion and passage-level lineage. Phase 17 or
  later; decide against Section 4's actual example design.
- **Section 4 itself** — Mode 2 (`llm_packaged`) and Mode 3 (`swarm_assembled`).
  Phase 17: the packaging stage with the whitepaper's four pinning primitives
  (model version, temperature, full prompt, output hash), and the swarm
  coordinator. Open design question for that phase: how a swarm-realized operator
  is admitted to the composition-preservation suite, given it is deterministic at
  the typed boundary but not value-deterministic.
- **A lint for mis-pointed snippet includes** (SURFACE-AUDIT A-5) — `docs-strict`
  catches an *orphaned* include, not a *mis-pointed* one. Named as this phase's
  concern; may still land as its own follow-up.
- **`make ci` does not reach `tools/`** though CI does — three suites there fail
  pre-existing. A process finding carried from the 15.1 close; not this phase's
  goal but adjacent to its CI work.
- **DI-15.4-05 / F2** — the public-vs-private adapter surface, and
  `substrate_vocabulary` deriving from in-tree adapters only. Awaiting Dave's
  ruling; touches the "write a graph backend adapter" how-to this phase rewrites.

</deferred>

---

*Phase: 16-Documentation Rewrite — The Deterministic Path & The Adoption Argument*
*Context gathered: 2026-08-09*
