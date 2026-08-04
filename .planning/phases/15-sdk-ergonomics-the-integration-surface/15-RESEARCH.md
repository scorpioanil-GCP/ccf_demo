# Phase 15: SDK Ergonomics — The Integration Surface - Research

**Researched:** 2026-08-03
**Domain:** The CCF SDK's own adopter-facing integration surface (internal archaeology, not external-library research)
**Confidence:** HIGH — every quantitative claim below is derived from AST measurement of the repository at commit `0cfc10c`, reproducible with the scripts described in §Method. No web research was needed or performed.

## Summary

The phase's thesis is confirmed and is *larger* than the ROADMAP's estimate. Across the nine
examples plus `examples/external/`, **1,435 lines of 11,988 (12.0%) are mechanical
marshalling/wiring the SDK could supply**, concentrated in four repeating shapes that are
copy-pasted almost verbatim: `_resolution_spec` (9 sites, 180 lines, byte-identical body in 8
of 9), `_envelopes` (9 sites, 116 lines), the inline operator-registry block (9 sites, 579
lines), and `_instant`/`_load` (11 sites each, 94 lines combined). A tenth pattern —
`registry.register` / `parse_artifact` / `MaxTTL` / `Perspective` / `register_product_class`
call clusters — adds 350 lines.

The single most consequential finding: **`EntityResolutionSpec`, `EntityResolutionRule`,
`RelationshipResolutionRule` are already `CCFContract` subclasses whose field names match the
YAML keys exactly** (`worker.py:71-114` vs `00-quickstart/artifacts/ontology.yaml:29-70`). The
20-line `_resolution_spec` marshaller in nine files does nothing a `parse_artifact` call could
not do today, once the artifact carries a `semver` field and the two operator-facing attribute
maps are split out per D-03. This is the cheapest, highest-duplication win in the phase and
should land first.

The governance line holds cleanly for every helper the phase needs. The one place D-15A's
discriminator bites is `PolicyFilterParameters.permitted_policy_bundle_versions`, which is *not*
in any artifact today — it is the runtime return value of `registry.register` (`run.py:205`,
`run.py:241`). A typed `PolicyFilterParameters` artifact class therefore cannot be fully
declarative, and how the builder supplies that field is the one genuine open design question
this research surfaces (see §Open Questions Q1 / D-IMPL-76 candidate).

**Primary recommendation:** Build the loaders in duplication order — resolution spec, signal
envelopes, operator parameters, then the manifest/boot entry point — and gate every one against
a round-trip test plus the standing `run_gates` two-input regression. Do not touch
`examples/external/` until the `ccf.deployment` surface is frozen; it is the only tree whose
consumers must keep zero CCF imports on the client side.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| YAML → typed artifact parse | Control Plane (`ccf.controlplane.artifacts`) | — | Criterion 2 names `parse_artifact` as the mandated seam; nothing new is invented beside it |
| Path resolution + file read | New `ccf.deployment` (D-13) | — | `artifacts.py:312-327` deliberately takes text, not a path — "reading the file is the caller's concern" |
| Registry population from a manifest | `ccf.deployment` → `ControlPlaneRegistry.register` | Control Plane | Registration is Control Plane mechanism; the manifest is the input |
| Boot composition | `ccf.deployment` → `ccf.boot.boot()` | L2/L3 | `boot()`'s pinned `(key, version)` contract preserved verbatim (D-05) |
| Operator construction from artifacts | `ccf.deployment` (two-phase, view-aware, D-07) | L4 | `SimilaritySelect`'s index needs a live `GraphView` corpus (`run.py:249-256`), so it cannot be a pure artifact read |
| Gate execution (`run_gates`) | L6 (`ccf.products.gates`) — **stays in adopter code** | — | D-15A worked case: two independent inputs must remain two independent inputs |
| Projection Π | Deployment code — **not a target** | — | Whitepaper §7.5; `QuickstartPlan` (`run.py:138-182`) is what a user writes |
| Schema export (`ccf schema export`) | Experience Layer (`runtime/ccf_runtime/cli/`) | — | §8.3; joins the existing eight-noun CLI |

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Artifact class ownership**

- **D-01: A typed `ArtifactClass` per SDK-shipped operator category**, whose contract is that
  category's existing `*Parameters` model in `src/ccf/operators/categories.py`. Deployment-authored
  operators keep `DeclaredArtifact` as the documented path. **The `artifacts.py` module docstring
  is amended** to state what it actually means: the SDK owns the schema of what it ships and never
  invents one for what it doesn't.
  - Rationale: `PolicyFilterParameters` et al. are already `/src` code, so refusing to parse them
    declaratively was inconsistent rather than principled. The docstring's policy-bundle argument
    — sound for policy bundles — over-generalized when it swept operator parameter sets in beside
    them.
  - No D-15A exposure: operator parameters are an input the deployment supplies and the fabric
    consumes, with no second independent source for a gate to check them against.
- **D-02: Timestamp-shaped scalars load as strings and parse through `datetime.fromisoformat`.**
  PyYAML's timestamp resolver is suppressed in the artifact load path. `...Z` and `...+00:00` both
  yield aware datetimes; a designator-less timestamp is refused with a message naming D-IMPL-38.
  - Reframing that drove it: `2026-08-03T12:00:00Z` is **not** an implicit timezone — `Z` is the
    ISO-8601 UTC designator and the author stated UTC explicitly. PyYAML's resolver drops it. The
    naive datetime is a *parser* defect, not an authoring defect, so refusing it would punish
    authors for a rule they did not break.
  - Measured: **100** `...Z` timestamps across **20** example YAML files, **12** already written
    with explicit offsets (the suite is already inconsistent), and the timezone-attaching helper
    duplicated across **13** Python files including `perf/suites/common.py` and
    `perf/synth/generator.py`. Zero artifact churn; 13 helpers delete.
  - This sits beside `_reject_floats` as the same class of thing: both are places where YAML's own
    type resolution loses information the canonical serializer requires, fixed once in `/src`
    rather than in every deployment.
  - **Behavior change** for existing `load_artifact` callers relying on PyYAML handing back a
    `datetime`. Belongs in the D-15 surface-change log as a behavior entry even though nothing was
    removed.
- **D-03: The resolution spec artifact is split by consumer.** `ccf.resolution-spec` is
  closed-world over entity and relationship rules only — an unknown key fails at parse. The
  operator-facing attribute maps (`classification_attribute_by_class`,
  `similarity_corpus_attribute_by_class`) move into the operator-parameters artifacts that
  actually consume them, where D-01's typed per-category classes validate them.
  - The quickstart's `ontology.yaml` today does two unrelated jobs — L2-consumed resolution rules
    and fields the fabric never reads — with nothing in the artifact saying which is which. One
    artifact, one consumer makes closed-world validation possible for both.
- **D-04: `ccf schema export` emits JSON Schema per artifact class**, example artifacts carry
  `# yaml-language-server: $schema=...` headers, and a CI freshness gate guards drift — the same
  shape as Phase 14's committed-and-drift-checked OpenAPI (14-CONTEXT D-12).
  - An adopter gets completion and validation while *authoring*, which is where marshalling errors
    are cheapest to fix. Phase 16 gets a shipped instance to literal-include.
- **Carried without separate ruling:** `Perspective` and the product-class declaration get typed
  artifact classes, by the same D-01 test — both are already SDK contracts in `/src`.

**The wiring entry point**

- **D-05: A `ccf.deployment-manifest` artifact, and one call that loads, validates, registers, and
  boots** — returning the `FabricHandle` plus the resolved pins. `boot()`'s pinned `(key, version)`
  contract is unchanged underneath; the manifest produces the pins instead of hand-written code
  producing them.
  - `boot()` is already well-shaped (no defaults, no "latest", because a fabric whose config drifts
    between boots cannot be replayed). The friction is the eleven lines *before* it.
- **D-06: The manifest enumerates every artifact explicitly — path, key, class. No globs, no
  directory sweeps.** The manifest is itself content-hashable, so "what was in force" is answerable
  from one document, and the call returns a typed pin set the adopter reads and passes to
  `build_replay_record`.
  - Load-bearing because the set of Control Plane artifacts in force is dimension 2 of the
    five-dimension replay record. A glob would make that set a function of directory contents at
    boot time — a file dropped in the directory would silently change what was in force with no
    artifact recording that it did.
- **D-07: A two-phase, view-aware operator-registry builder.** It takes the artifacts plus a
  `GraphView` and builds everything in one call: parameter-only operators directly, index-backed
  ones from the view. The ordering constraint lives in the signature — the registry cannot be built
  without a view.
  - Why it can't be a pure artifact read: `SimilaritySelect`'s `TokenOverlapIndex` is built from a
    corpus read out of the live graph at the temporal boundary (`run.py:249-256`), after boot and
    after ingest. Lazy binding at first invocation was rejected: it would build the index during
    projection execution, inside the algorithmic path, over a corpus determined by when the engine
    happened to invoke it rather than by a boundary the deployment named.
  - Corpus-extraction rules (which attribute per entity class) come from the operator-parameters
    artifact per D-03.
- **D-08: The manifest declares the backend *kind*; the DSN or database path is a call argument
  from the environment.** A manifest declaring `postgres` with no connection supplied fails loudly
  rather than falling back to SQLite.
  - `boot()` refuses to *infer* the substrate, so the manifest cannot stay silent; but
    `postgres_dsn` "comes from the deployment's environment; it is never persisted," so the manifest
    cannot carry it either. Declaring the kind satisfies both.

**Example rewrite scope**

- **D-09: CI assertions and print summaries move to `tests/`.** Examples become pure demonstration
  — `run.py` is what an adopter would actually write, nothing more. A parallel test module imports
  and asserts against each example's output, keeping CI's guarantee intact.
  - Also largely dissolves Phase 16's snippet-marker problem: little is left in the file that isn't
    the call spine.
- **D-10: Re-domain example 04 to banking only; the horizontal domain mix is preserved everywhere
  else.** Gives Phase 16 the banking A2A/MCP worked instance its criterion 5 names, while honoring
  D-IMPL-52 (Dave, 2026-07-25 — a suite that visibly crosses domains demonstrates generality more
  convincingly than a single domain held constant). Re-domaining the whole suite would reverse
  D-IMPL-52 and would need a superseding decision, not a phase-level choice.
- **D-11: The criterion-1 surface audit is a phase-close report** with before/after line counts,
  not a front-loaded gate.
  - **Consequence the planner must absorb:** the helper set is therefore *not* derived from a
    front-loaded evidence sweep. See the research directive in `<code_context>` — the research and
    pattern-mapping pass must sweep all nine examples plus `examples/external/` for marshalling
    patterns, because the quickstart is the only file this discussion measured, and a pattern
    appearing in six examples but not the quickstart would otherwise be missed.
- **D-12: No numeric line-count target;** criterion 5's "demonstrably smaller" stands as written and
  the audit reports the honest number. A target invites being hit by moving lines rather than
  removing work — a live risk given D-09 already relocates ~85 lines to `tests/`.

**Where helpers live**

- **D-13: A new `ccf.deployment` package in `/src`**, algorithmic-tagged, holding the manifest
  artifact class, the loaders, and the boot/registry/operator builders. One obvious import home for
  adopters.
  - **The purity concern was checked and is resolved:** `tools/lints/algorithmic.py` enforces CINV-03
    purely as "no LLM client import in a module tagged `__ccf_mode__ = 'algorithmic'`" — it says
    nothing about filesystem I/O, and `boot.py` is already algorithmic-tagged while opening SQLite
    files. No lint change needed. **Write the reading down** (in the package docstring) so the next
    contributor does not re-derive it: "algorithmic" means no model call in the path, not no I/O.
  - Note the tension this resolves: `artifacts.py` deliberately takes text rather than a path
    ("reading the file is the caller's concern"). That module keeps its discipline; `ccf.deployment`
    is where path resolution and file reading live.
- **D-14: Additive — the direct constructors stay public.** `EntityResolutionSpec`,
  `SignalEnvelope`, the `*Parameters` classes and `boot()` all remain directly constructible; the
  helpers are a faster path over them. A deployment with an exotic need can still drop to the
  primitives, which matters because the manifest path is opinionated by design and CLAUDE.md §11's
  Protocol-first posture assumes users substitute their own implementations at these seams.
  - Docs must name the recommended path without making the other look deprecated.
  - **Not absolute:** D-02 is a behavior change to `load_artifact` even though no surface is removed.
    Record it as such.
- **D-15: Both a generated API diff and a curated surface-change log.** The diff (over the
  mkdocstrings-rendered public surface or an exported signature manifest, phase start vs end)
  guarantees completeness; the hand-written log carries rationale and migration guidance, is written
  incrementally as plans land, and is handed to Phase 16 as a direct input — doubling as the
  migration note D-15B says v0.1/v0.2 adopters get.

**Carried in from ROADMAP.md (Dave, 2026-08-03) and binding:**

- **D-15A — the abstraction line is marshalling and wiring only.** Helpers may absorb
  YAML→typed-object loading, registry population, boot wiring, and operator construction from
  artifacts. Every point where a deployment *asserts something the fabric then verifies* stays
  explicit in adopter code. The worked case: `run_gates()` takes the engine's resolved operators
  separately from the product's own lineage claim precisely so lineage strict equality has two
  independent sources; a helper computing both from one input would make the gate tautological and
  silently delete a whitepaper invariant. Dave reserves the right to revisit surface by surface
  where an ergonomic win requires touching a governance boundary — such cases are surfaced as
  decisions, not resolved by the phase.
- **D-15B — free rein on the public API, pre-1.0.** The phase may reshape, rename, collapse, or
  remove any public surface in the way; examples and docs are rewritten to match. `v0.1.0` stays
  tagged as the historical artifact. Anyone building against v0.1/v0.2 today has a migration, and
  that is accepted.

**The reusable discriminator (derived during discussion):** for each candidate helper, ask whether
the thing it would compute has a *second independent source the fabric checks it against*. If yes
(lineage), the helper must not collapse them. If no (operator parameters, resolution rules,
manifest pins), it is pure marshalling and D-15A permits it.

### Claude's Discretion

Every question in this discussion received an explicit ruling or an explicit carry. Planning-level
detail deliberately left open:

- The exact return-type shape of the D-05 one-call entry point (what the pin set object is called
  and carries), its error messages, and whether the manifest carries `tenant_id`.
- Whether the `ccf.deployment` surface is one module or several, and the naming of individual
  loaders.
- What `examples/external/` becomes under the helper surface — follows mechanically from D-05/D-13.
- Whether the CLI grows commands beyond `ccf schema export`.

### Deferred Ideas (OUT OF SCOPE)

- **Recording the deployment-manifest content hash on the Decision Replay record.** Raised as the
  strongest audit position for D-06 — it would let a replay prove *which manifest* produced the pin
  set, not merely which pins resulted. Deferred because it touches whitepaper §7.10.1 replay-record
  shape, which warrants its own decision rather than riding in on an ergonomics phase. Candidate
  `D-IMPL-NN` for a Phase D mini-cycle.
- **Re-domaining the published example set (or the whole suite) to banking.** Considered under D-10
  and rejected for this phase: it would reverse D-IMPL-52 (Dave, 2026-07-25) and needs a superseding
  decision. Only example 04 moves.
- **Whether the Agent & Task Factory definition-artifact paths carry comparable marshalling burden.**
  Surfaced as a candidate gray area at the close of discussion and not explored. If the research
  sweep finds hand-marshalling in the agent/skill artifact paths of examples 01–03, that is in scope
  for this phase; a *new* factory surface is not. **Research finding: it does not.** See §3.6.
</user_constraints>

## Project Constraints (from CLAUDE.md)

Directives the planner must verify compliance against. All are load-bearing for this phase.

| # | Directive | Source | Bearing on Phase 15 |
|---|-----------|--------|---------------------|
| C-1 | **Fidelity to the whitepaper ranks above every other success condition.** Simplification that costs an invariant is a fidelity defect. | §1 | The phase's governing tiebreak. Any helper that weakens a gate is rejected, not traded off. |
| C-2 | **Mechanism, not values.** No hard-coded table, threshold, skill catalog, projection role, workflow definition, or approval policy in `/src`. | §11 | `ccf.deployment` loaders may hold **no** key name, no domain value, no threshold. |
| C-3 | **No-Hardcoding Rule — code contains interpreters and factories, never the things interpreted.** Applies to `/src`, `/runtime`, `/examples` alike. CI-enforced. | §6.4 | This phase's whole thesis: move interpreters from `/examples` into `/src`. |
| C-4 | **Zero harness imports in `/src`.** CI import lint. | §7.3, §11 | `ccf.deployment` imports no harness. Trivially satisfied; verify in CI. |
| C-5 | **Single-writer invariant is architectural, not advisory.** Only L2 holds a write handle to L3; enforced via DI at boot. | §10 | The D-05 entry point returns the same `FabricHandle`, which has no writer attribute. It must not grow one. |
| C-6 | **Algorithmic ⇄ Semantic Alternation.** No LLM client import in `@algorithmic` modules. | §11 | `ccf.deployment` is algorithmic-tagged (D-13); confirmed compatible — see §7.1. |
| C-7 | **Typed contracts at every boundary.** Pydantic with `extra=forbid`; validation at the boundary, never deferred. | §11 | Every new artifact class is a `CCFContract` (frozen, closed-world). D-03's split exists to make closed-world validation possible. |
| C-8 | **Prefer Protocols over inheritance**; reference implementations ship alongside Protocols. | §11 | D-14's "direct constructors stay public" is the same posture — the helper path must not become the only path. |
| C-9 | **Decision Replay enforced at write time, not retrofitted.** Every product served is replay-ready by construction. | §11 | Criterion 4's test: "what does this hide from the replay record?" answer must be "nothing." |
| C-10 | **Surface gaps; do not paper over them.** Whitepaper-silent → log `D-IMPL-NN` and stop. Never pick a default and hope. | §11, §15 | Q1 (`permitted_policy_bundle_versions`) is exactly this situation. |
| C-11 | **Cite the whitepaper section in the docstring of every public class**; SDK extensions cite CLAUDE.md and are marked explicitly. | §11 | `ccf.deployment` is an SDK extension — its docstrings cite CLAUDE.md §6.4/§10, not the whitepaper, and say so. |
| C-12 | **Phase boundaries are real.** No redesign during implementation; a revisited decision is a Phase D mini-cycle with its own log entry. | §3 | Q1 and Q2 must be ruled *before* the affected plans execute, not resolved inline. |

**Project skills:** `.claude/skills/` and `.agents/skills/` — neither directory exists in this
repository (verified). No project-skill patterns constrain this phase.

<phase_requirements>
## Phase Requirements

`ERGO-01..ERGO-NN` are **not yet minted**. The proposed set is in §10 below, one requirement per
coherent ergonomic target, each mapped to the ROADMAP success criterion it serves.
</phase_requirements>

---

## 1. The Measured Baseline (Success Criterion 1)

### Method

All numbers below come from AST analysis, not `grep`. Three passes, reproducible:

1. **Composition pass** — per file: raw line count; `ast.Assert` node spans; `print(...)`
   expression-statement spans; docstring `Expr` spans; import spans; blank and comment lines.
2. **Duplication pass** — spans of every `FunctionDef` named `_load`, `_instant`,
   `_resolution_spec`, `_envelopes`, `_operators`, `_registry`, `_consumer_resolution_spec`,
   `_register_closure`.
3. **Block pass** — span from the `OperatorRegistry()` call to the last `operators.register(...)`
   call in each file; `boot(...)` call spans; `registry.register(...)` / `parse_artifact(...)` /
   `register_product_class(...)` / `MaxTTL(...)` / `Perspective(...)` call spans.

`[VERIFIED: AST measurement of the repository at HEAD]` for every figure in this section.

### 1.1 Correcting the ROADMAP's quickstart breakdown

The ROADMAP cites `examples/00-quickstart/run.py` (451 lines) as "~85 CI assertions / ~105
marshalling / ~45 projection Π / ~55 call spine." Measured against the actual file:

| ROADMAP claim | Measured | Delta | Evidence |
|---|---|---|---|
| ~85 lines CI assertions + prints | **40** (30 assert-node lines + 10 print-node lines) | −45 | 11 `assert` statements at `run.py:210,211,353,357-360,366,367-369,370-372,402-404,405,406-408,409,410,411-414,415,416-418,419,433`; 6 `print` calls at `run.py:435-444` |
| ~105 lines marshalling | **144** | +39 | see 1.2 breakdown |
| ~45 lines projection Π | **45** | 0 | `QuickstartPlan`, `run.py:138-182` |
| ~55 lines call spine | ~52 residual | ≈0 | `boot`+`ingest`+`execute`+`run_gates`+`build_replay_record`+`serve` |

The ROADMAP over-counted assertions (probably by including the surrounding comments and blank
lines) and under-counted marshalling (it did not include the `registry.register` / `parse_artifact`
/ `MaxTTL` / `Perspective` / `register_product_class` cluster, 27 lines, nor `_load`/`_instant`,
13 lines). **The corrected story is stronger for the phase, not weaker:** more of the file is
mechanical than the ROADMAP claimed, and less of it is assertion noise that D-09 merely relocates.

> **Planner note:** D-12 forbids a numeric line-count target, and D-12's stated risk — "a target
> invites being hit by moving lines rather than removing work" — is now quantified: D-09's
> relocation moves **40** lines out of the quickstart, not 85. The audit must report relocation
> and removal separately.

### 1.2 Quickstart, line by line

| Category | Lines | Location |
|---|---|---|
| `_load` (YAML file read) | 2 | `run.py:81-82` |
| `_instant` (timezone attach) | 11 | `run.py:85-95` |
| `_resolution_spec` (ontology → `EntityResolutionSpec`) | 20 | `run.py:99-118` |
| `_envelopes` (events → `SignalEnvelope`) | 12 | `run.py:123-134` |
| Registry population + `parse_artifact` + `MaxTTL` + `Perspective` + `register_product_class` | 27 | `run.py:201-213`, `run.py:299-329` |
| `boot(...)` call | 8 | `run.py:216-223` |
| Operator-registry block | 64 | `run.py:232-295` |
| **Mechanical subtotal** | **144** | |
| Assertions + prints (D-09 relocation) | 40 | scattered |
| Projection Π (`QuickstartPlan`) — **not a target** | 45 | `run.py:138-182` |
| Imports | 54 | `run.py:20-76` |
| Docstrings / comments / blanks | ~116 | |
| Genuine call spine + control flow | ~52 | |
| **Total** | **451** | |

Note the imports: **54 lines of import statements**, 27 distinct SDK names. Consolidating the
common path into `ccf.deployment` should collapse most of that — a second, unmeasured ergonomic
win the audit should report.

### 1.3 The whole tree

Per-file mechanical accounting. `helpers` = `_load`+`_instant`+`_resolution_spec`+`_envelopes`+
`_consumer_resolution_spec`+`_registry`; `opblk` = operator-registry construction (inline block or
`_operators` function); `boot` = `boot(...)` call span; `reg` = Control Plane registration cluster;
`mech` = their sum; `a+p` = assertion + print lines (D-09 relocation candidates).

| File | raw | helpers | opblk | boot | reg | **mech** | mech % | a+p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `00-quickstart/run.py` | 451 | 45 | 64 | 8 | 27 | **144** | 31.9% | 40 |
| `01-agent-basics/run.py` | 619 | 41 | 64 | 8 | 47 | **160** | 25.8% | 85 |
| `02-skilling/run.py` | 571 | 40 | 38 | 8 | 33 | **119** | 20.8% | 68 |
| `03-harness-portability/run.py` | 720 | 41 | 64 | 8 | 33 | **146** | 20.3% | 98 |
| `03/legs/deterministic.py` | 507 | 0 | 0 | 0 | 0 | 0 | — | 11 |
| `03/legs/live.py` | 641 | 0 | 0 | 0 | 0 | 0 | — | 23 |
| `03/legs/ollama_client.py` | 147 | 0 | 0 | 0 | 0 | 0 | — | 0 |
| `04-cross-process/run.py` | 533 | 25 | 0 | 8 | 21 | **54** | 10.1% | 68 |
| `04-cross-process/producer_child.py` | 630 | 41 | 62 | 8 | 33 | **144** | 22.9% | 14 |
| `05-workflow-hitl/run.py` | 858 | 8 | 0 | 0 | 20 | **28** | 3.3% | 112 |
| `06-decision-replay/run.py` | 1320 | 49 | 77 | 8 | 42 | **176** | 13.3% | 130 |
| `07-artifact-store-mcp/run.py` | 587 | 38 | 64 | 8 | 23 | **133** | 22.7% | 27 |
| `07/mcp_store_child.py` | 135 | 0 | 0 | 0 | 0 | 0 | — | 1 |
| `08-e2e-demo/run.py` | 1141 | 49 | 63 | 8 | 42 | **162** | 14.2% | 6 |
| `08-e2e-demo/generator.py` | 431 | 0 | 0 | 0 | 0 | 0 | — | 0 |
| `external/00/serve.py` | 773 | 41 | 61 | 8 | 23 | **133** | 17.2% | 1 |
| `external/00/run.py` | 766 | 0 | 22 | 8 | 6 | **36** | 4.7% | 22 |
| `external/00/replay_server.py` | 400 | 0 | 0 | 0 | 0 | 0 | — | 9 |
| `external/00/client_bare.py` | 77 | 0 | 0 | 0 | 0 | 0 | — | 5 |
| `external/00/client_anthropic.py` | 97 | 0 | 0 | 0 | 0 | 0 | — | 2 |
| `external/00/client_adk.py` | 75 | 0 | 0 | 0 | 0 | 0 | — | 1 |
| `external/00/fixtures/capture_proxy.py` | 415 | 0 | 0 | 0 | 0 | 0 | — | 7 |
| `external/00/fixtures/diff_fixtures.py` | 93 | 0 | 0 | 0 | 0 | 0 | — | 7 |
| **TOTALS** | **11,988** | **418** | **579** | **88** | **350** | **1,435** | **12.0%** | **~519 asserts + 218 prints** |

**Reading the table:**

- The **highest-density targets** are the fabric-construction files: quickstart (31.9%),
  `01-agent-basics` (25.8%), `producer_child.py` (22.9%), `07` (22.7%), `02` (20.8%),
  `03` (20.3%). All six construct a full fabric from artifacts.
- The **three client legs** in `examples/external/` are already near-zero mechanical (they have
  zero CCF imports by design, EXAM-04). They will not shrink from this phase, and nothing here
  should touch them.
- `05-workflow-hitl` is the outlier at 3.3% — it does not build an operator registry at all. Its
  own duplication is `_register_closure` (49 lines, `run.py:266-314`), a one-off.
- `08-e2e-demo/generator.py` and `external/.../capture_proxy.py` are pure demonstration substrate
  with no fabric wiring. Not targets.

### 1.4 The eight-example success criterion 5 target set

Files where a rewrite is expected to produce a measurable reduction, in descending mechanical
line count: `06-decision-replay/run.py` (176), `08-e2e-demo/run.py` (162),
`01-agent-basics/run.py` (160), `03-harness-portability/run.py` (146), `00-quickstart/run.py`
(144), `04-cross-process/producer_child.py` (144), `07-artifact-store-mcp/run.py` (133),
`external/00/serve.py` (133), `02-skilling/run.py` (119), `04-cross-process/run.py` (54),
`external/00/run.py` (36), `05-workflow-hitl/run.py` (28).

**Twelve files. 1,435 mechanical lines.** Plus ~737 assertion/print lines relocating to `tests/`
under D-09.

---

## 2. The Existing Declarative Seam (Success Criterion 2)

`src/ccf/controlplane/artifacts.py` — 327 lines, read end to end. `[VERIFIED: file read]`

### 2.1 The contract, precisely

**`ArtifactClass`** (`artifacts.py:100-131`) — a frozen `@dataclass` (deliberately *not* a
`CCFContract`, because "it carries a Python type, which has no canonical serialization and never
belongs in a content hash," `artifacts.py:103-106`). Two fields:

- `class_id: str` — stable identifier recorded on audit events.
- `contract: type[CCFContract]` — the contract instances must satisfy.

One method: `validate(artifact) -> CCFContract` (`artifacts.py:118-131`), raising `TypeError` on
a non-instance. Note its comment: "A near-miss mapping with the right keys is still a rejection —
structural luck is not a contract."

**Registration mechanism.** There is **no registry of artifact classes**. `ArtifactClass`
instances are module-level constants:

```python
HALF_LIFE_TABLE = ArtifactClass(class_id="ccf.half-life-table", contract=HalfLifeTable)  # :268
DEBT_PROFILE   = ArtifactClass(class_id="ccf.debt-profile",   contract=DebtProfile)      # :270
```

Callers import the constant and pass it to `parse_artifact`. `[VERIFIED: artifacts.py:267-270; no
registry structure exists in the module]`

> **Planner consequence:** D-06's manifest declares an artifact's *class* by name in YAML
> (`path, key, class`). Resolving a string class-id to an `ArtifactClass` object therefore needs a
> **class-id → `ArtifactClass` lookup that does not exist today**. Building it is in scope
> (mechanism, not values) but it is a genuinely new structure, not "reaching through the existing
> seam" — the planner must not assume it is free. The natural home is `ccf.deployment`, populated
> from the SDK-shipped constants plus `declared_artifact_class(class_id)` for anything the manifest
> names as deployment-declared.

**The two registered classes** and their contracts:

| class_id | contract | shape | source |
|---|---|---|---|
| `ccf.half-life-table` | `HalfLifeTable` | `semver: str`, `entries: Mapping[str, HalfLifeEntry]` with `min_length=1` | `artifacts.py:202-213` |
| `ccf.debt-profile` | `DebtProfile` | `semver: str`, `risk_sensitivity: Decimal`, `forced_llm_threshold: Decimal`, `fail_closed_threshold: Decimal` | `artifacts.py:216-264` |

Both derive from **`_VersionedArtifact`** (`artifacts.py:134-142`), which contributes exactly one
field — `semver: str`, validated by `validate_semver` (`artifacts.py:73-87`) against
`_SEMVER_RE` (`artifacts.py:65-67`, `MAJOR.MINOR.PATCH` with optional pre-release/build).
**`semver` has no default**, so an artifact that never states its lane cannot be registered
(`artifacts.py:13-17`).

**`DeclaredArtifact`** (`artifacts.py:145-161`) — the open envelope: `semver` (inherited) +
`class_id: str` + `declaration: Mapping[str, Any]`. Constructed via
`declared_artifact_class(class_id)` (`artifacts.py:164-166`), which returns a fresh
`ArtifactClass` bound to `DeclaredArtifact`. Its docstring is the exact text **D-01 amends**:
"Policy bundles, **operator parameter sets**, ontology declarations… The SDK does not get to
invent a policy-bundle schema on a user's behalf" (`artifacts.py:145-158`).

### 2.2 The validation path, step by step

```
load_artifact(text, artifact_class)        # :312-327
  └─ yaml.safe_load(text)                  # :324  ← D-02's intervention point
     └─ yaml.YAMLError → ArtifactLoadError # :325-326
  └─ parse_artifact(document, klass)       # :296-309
     ├─ _reject_floats(document, "")       # :303 → recursive over Mapping/list/tuple, :273-293
     │    └─ float anywhere → ArtifactLoadError with a dotted path
     └─ klass.contract.model_validate(doc) # :305
          └─ ValueError → ArtifactLoadError(f"document is not a valid {class_id}: {error}")
```

`ArtifactLoadError` is a `ValueError` subclass (`artifacts.py:90-97`).

**Every extension point, enumerated:**

| # | Extension point | Location | How Phase 15 uses it |
|---|---|---|---|
| E1 | New `ArtifactClass` module constant | `artifacts.py:267-270` pattern | D-01: one per shipped operator category; plus resolution-spec, perspective, product-class, signal-batch, deployment-manifest |
| E2 | New `_VersionedArtifact` subclass | `artifacts.py:134-142` | Every new SDK-owned class must inherit it to get the `semver` lane |
| E3 | `declared_artifact_class(class_id)` | `artifacts.py:164-166` | Deployment-authored operators / policy bundles keep this path (D-01) |
| E4 | `parse_artifact(document, klass)` | `artifacts.py:296-309` | The mandated criterion-2 seam. Every new loader calls it. |
| E5 | `load_artifact(text, klass)` | `artifacts.py:312-327` | D-02 changes the YAML loader used at `:324` |
| E6 | `_reject_floats` | `artifacts.py:273-293` | D-02's stated precedent; a timestamp check joins it as a sibling |
| E7 | `validate_semver` | `artifacts.py:73-87` | Shared grammar — must not be re-declared in `ccf.deployment` |
| E8 | `__all__` | `artifacts.py:49-60` | New public names go here; also the D-15 diff's tracking surface |

**Points that are NOT extension points and must not be treated as such:**

- There is **no** class-id registry (see 2.1). Building one is new work.
- `load_artifact` takes **text, not a path** (`artifacts.py:319-321`: "Deliberately takes text
  rather than a path: reading the file is the caller's concern, and keeping I/O out of this module
  keeps it algorithmic"). D-13 respects this — path resolution lives in `ccf.deployment`.
- `ArtifactClass.validate` is *instance* checking of an already-typed object, distinct from
  `parse_artifact`'s document validation. Two different jobs; do not conflate.

### 2.3 The `semver` field mismatch — a concrete blocker

Every example YAML file carries `schema_version: "1.0.0"` and `artifact_version: "1.0.0"` at the
document root (`00-quickstart/artifacts/ontology.yaml:21-22`,
`controlplane.yaml:21-22`, `events.yaml:28-29`, `halflife.yaml:20-21`). The SDK's
`_VersionedArtifact` requires the field to be named **`semver`**, and the half-life table's
*nested* block does carry `semver: "1.0.0"` (`halflife.yaml:26`).

So today the examples have two version conventions in one file: `artifact_version` at the root
(read by nobody) and `semver` inside the sub-document that `parse_artifact` actually validates.
Since new artifact classes are closed-world (`CCFContract` is `extra=forbid` — confirmed at
`artifacts.py:5-6` "frozen, closed-world"), **every example YAML that becomes a typed artifact
must be reshaped**: root `schema_version`/`artifact_version` either renamed to `semver` or
removed. This is 65 YAML files' worth of potential churn. D-15B permits it; the planner must
budget for it and it belongs in the D-15 surface-change log as an artifact-format change.

---

## 3. The Hand-Marshalling Inventory (Success Criterion 2)

Ordered by total duplicated lines — the strongest signal for build order.

### 3.1 `_resolution_spec` — 9 sites, 180 lines. **Build first.**

| File | Lines | Span |
|---|---|---|
| `00-quickstart/run.py` | 20 | 99-118 |
| `01-agent-basics/run.py` | 20 | 117-136 |
| `02-skilling/run.py` | 20 | 109-128 |
| `03-harness-portability/run.py` | 20 | 113-132 |
| `04-cross-process/producer_child.py` | 20 | 144-163 |
| `06-decision-replay/run.py` | 20 | 201-220 |
| `07-artifact-store-mcp/run.py` | 20 | 110-129 |
| `08-e2e-demo/run.py` | 20 | 182-201 |
| `external/00-hello-context/serve.py` | 20 | 324-343 |
| *(variant)* `04-cross-process/run.py::_consumer_resolution_spec` | 19 | 132-150 |

**The finding that matters:** the target types already match the YAML keys exactly.

| YAML key (`ontology.yaml`) | SDK field | SDK class | Source |
|---|---|---|---|
| `entity_rules[].match_key` | `match_key: str` | `EntityResolutionRule` | `assembly/worker.py:85` |
| `entity_rules[].entity_class` | `entity_class: str` | `EntityResolutionRule` | `assembly/worker.py:86` |
| `entity_rules[].identity_keys` | `identity_keys: tuple[str, ...]` | `EntityResolutionRule` | `assembly/worker.py:87` |
| `entity_rules[].attribute_keys` | `attribute_keys: tuple[str, ...] = ()` | `EntityResolutionRule` | `assembly/worker.py:88` |
| `relationship_rules[].relationship_type` | `relationship_type: str` | `RelationshipResolutionRule` | `assembly/worker.py:100` |
| `relationship_rules[].subject_entity_class` | `subject_entity_class: str` | `RelationshipResolutionRule` | `assembly/worker.py:101` |
| `relationship_rules[].object_entity_class` | `object_entity_class: str` | `RelationshipResolutionRule` | `assembly/worker.py:102` |
| `entity_rules` | `entity_rules: tuple[EntityResolutionRule, ...]` | `EntityResolutionSpec` | `assembly/worker.py:113` |
| `relationship_rules` | `relationship_rules: tuple[...] = ()` | `EntityResolutionSpec` | `assembly/worker.py:114` |

`EntityResolutionSpec` is a `CCFContract` (`assembly/worker.py:105`) whose docstring already
calls it "A Control Plane artifact, versioned like any other" (`worker.py:108-111`). Pydantic
coerces YAML lists to tuples and nested dicts to models. **The 20-line marshaller is dead
weight** — `parse_artifact(document, RESOLUTION_SPEC)` produces the identical object.

Three things stand between here and that:

1. `EntityResolutionSpec` does not inherit `_VersionedArtifact`, so it has no `semver` field.
   Either add the field (a change to an L2 contract — content-hash-affecting, so a
   surface-change-log entry) or wrap it. **The planner must pick one and record it.**
2. `ontology.yaml` carries `tenant_id`, `classification_attribute_by_class`, and
   `similarity_corpus_attribute_by_class` at the same level as `entity_rules` — closed-world
   validation would reject them. **This is exactly why D-03 exists.**
3. `_consumer_resolution_spec` (`04-cross-process/run.py:132-150`) reads a differently-nested
   document (`federation`). Check whether D-10's re-domaining also normalizes its shape.

**Verdict: pure marshalling. D-15A permits it. Hides nothing from replay** — the spec's registered
content version is `content_hash(spec)` either way (`registry.py:296`).

### 3.2 Operator-registry construction — 9 sites, 579 lines. **Biggest single win.**

| File | Lines | Span | Shape |
|---|---|---|---|
| `00-quickstart/run.py` | 64 | 232-295 | inline, 4 operators |
| `01-agent-basics/run.py` | 64 | 289-352 | inline, 4 operators |
| `03-harness-portability/run.py` | 64 | 283-346 | inline, 4 operators |
| `07-artifact-store-mcp/run.py` | 64 | 277-340 | inline, 4 operators |
| `08-e2e-demo/run.py` | 63 | 742-804 | inline, 4 operators |
| `04-cross-process/producer_child.py` | 62 | 322-383 | inline, 4 operators |
| `06-decision-replay/run.py` | 77 | 292-368 | `_operators()` function |
| `external/00-hello-context/serve.py` | 61 | 360-420 | `_operators()` function |
| `02-skilling/run.py` | 38 | 271-308 | inline, 3 operators (no similarity) |
| `external/00-hello-context/run.py` | 22 | 155-176 | `_operators()` method |

Per-parameter-class marshalling totals across the tree:

| Class | Sites | Lines | Target |
|---|---|---|---|
| `PolicyFilterParameters` | 9 | 93 | `ccf.operator-parameters.policy` (D-01) |
| `TraversalNeighborhoodParameters` | 9 | 81 | `ccf.operator-parameters.traversal` |
| `SimilaritySelectParameters` | 8 | 72 | `ccf.operator-parameters.similarity` |
| `TemporalAsOfParameters` | 9 | 45 | `ccf.operator-parameters.temporal` |
| `TokenOverlapIndex` | 8 | 32 | built by the D-07 two-phase builder from the view |

The `*Parameters` classes are `OperatorParameters` subclasses in `src/ccf/operators/params.py`
(**not** `categories.py` — CONTEXT.md D-01's file reference is slightly off; the classes live at
`params.py:41,64,83,98` and are re-exported through `categories.py`'s import surface). Their
module docstring already asserts they are "Control Plane *values* that a deployment declares,
versions, and replays against" (`params.py:5-12`) — which is D-01's argument, already written
down in `/src`.

**The D-07 two-phase constraint, verified.** `run.py:249-256` reads a live corpus:

```python
corpus_attribute = ontology["similarity_corpus_attribute_by_class"]   # :248
view = handle.reader.as_of(tenant_id=tenant_id, at=boundary)          # :249
corpus = { (tenant_id, record.claim.entity_uri):
           record.claim.attributes[corpus_attribute[record.claim.entity_class]]
           for record in view.entities
           if record.claim.entity_class in corpus_attribute }         # :250-256
```

This runs *after* boot and *after* ingest, over a `GraphView` at the named temporal boundary.
`SimilaritySelect.__init__` takes the index injected — "the operator never constructs one, because
which index a deployment ranks against is deployment configuration"
(`categories.py`, `SimilaritySelect` docstring). D-07's view-in-the-signature shape is correct and
required.

**Verdict: pure marshalling, with one exception.** See Q1 below —
`permitted_policy_bundle_versions` is not in any artifact.

### 3.3 `_envelopes` — 9 sites, 116 lines

| File | Lines | Span |
|---|---|---|
| `00-quickstart`, `01`, `02`, `03`, `04/producer_child`, `06`, `07`, `external/serve` | 12 each | see §Method dup pass |
| `08-e2e-demo/run.py` | 20 | 259-278 |

Unlike the resolution spec, this one is a **genuine translation**, not a pass-through. The YAML
uses flat keys the contract does not:

| YAML key (`events.yaml`) | `SignalEnvelope` field | Source |
|---|---|---|
| `envelope_id` | `envelope_id: str` | `signal/envelope.py:68` |
| `source_system_id` | `source: SourceIdentity(system_id=...)` — **nested** | `signal/envelope.py:69` |
| `ingestion_timestamp` | `ingestion_timestamp: datetime` — **needs `_instant`** | `signal/envelope.py:70` |
| `observed_time` | `observed_time: datetime \| None = None` — **needs `_instant`** | `signal/envelope.py:71` |
| `payload` | `raw_payload: Mapping[str, Any]` — **renamed** | `signal/envelope.py:72` |
| *(from `ontology["tenant_id"]`)* | `tenant_id: str` — **cross-document** | `signal/envelope.py:67` |
| *(absent)* | `source_metadata: Mapping = {}` | `signal/envelope.py:73` |

Two options, both D-15B-permitted:

- **(a) Reshape the artifacts** so `events.yaml` nests `source: {system_id: ...}` and uses
  `raw_payload:`. Then a `ccf.signal-batch` artifact class parses directly. Requires touching all
  20 event YAML files, and requires the loader to inject `tenant_id` (which lives in a *different*
  document) — so either the batch artifact carries its own `tenant_id`, or the loader takes it as
  an argument.
- **(b) A typed batch artifact class with the current flat field names** and a `model_validator`
  that assembles `SourceIdentity`. Zero artifact churn, but the SDK then owns a second field
  vocabulary for the same concept, which is exactly the kind of drift `_VersionedArtifact` exists
  to prevent.

**Recommendation: (a).** It removes the translation rather than relocating it, and the phase's
thesis is removal. Note `raw_payload` is documented as "opaque to L1. Its keys are the source's
vocabulary, never the fabric's" (`envelope.py:62-63`) — renaming the *container* key does not
touch that.

**Verdict: marshalling. Hides nothing** — envelope content is unchanged, `envelope_id` is still
authored, and lineage addresses signals by that id (`envelope.py:55-57`).

### 3.4 `_instant` — 11 sites, 72 lines (+ `_load`, 11 sites, 22 lines)

| File | Span | Lines |
|---|---|---|
| `00-quickstart/run.py` | 85-95 | 11 |
| `01-agent-basics/run.py` | 108-114 | 7 |
| `02-skilling/run.py` | 101-106 | 6 |
| `03-harness-portability/run.py` | 104-110 | 7 |
| `04-cross-process/producer_child.py` | 135-141 | 7 |
| `04-cross-process/run.py` | 117-120 | 4 |
| `05-workflow-hitl/run.py` | 144-149 | 6 |
| `06-decision-replay/run.py` | 183-188 | 6 |
| `07-artifact-store-mcp/run.py` | 104-107 | 4 |
| `08-e2e-demo/run.py` | 153-159 | 7 |
| `external/00-hello-context/serve.py` | 213-219 | 7 |

Note the **six distinct implementations** across eleven sites (spans of 4, 6, 7, and 11 lines) —
the helper has already drifted, which is the strongest argument for D-02 moving it into `/src`.

`_load` is 2 lines in every one of its 11 sites (`yaml.safe_load((ARTIFACTS / name).read_text(...))`).

**D-02's measurements re-verified independently:**

| D-02 claim | Measured | Match |
|---|---|---|
| 100 `...Z` timestamps in example YAML | **100** (`grep -rhoE "[0-9]{2}:[0-9]{2}:[0-9]{2}Z" examples --include=*.yaml \| wc -l`) | ✅ exact |
| across 20 example YAML files | **20** files | ✅ exact |
| timezone-attaching helper in 13 Python files | **11 in `examples/`** + `perf/suites/common.py` + `tests/perf_synth/test_determinism.py`, `tests/properties/strategies.py`, `tests/properties/test_lineage_union.py`, `src/ccf/graph/reader.py` | close — 12 outside `tests/`; the exact count depends on which pattern is matched. `perf/synth/generator.py` did **not** match my pattern; the planner should re-verify before asserting "13 helpers delete." |

**Verdict: pure marshalling. Hides nothing.** The instants remain data in artifacts
(`controlplane.yaml:83-85` — "Explicit inputs, never clock reads: the example is replayable
precisely because these are data"). D-02 makes the parse correct, not implicit.

### 3.5 Control Plane registration cluster — 350 lines across 36+37+10+10+10 call sites

| Call | Sites | Lines |
|---|---:|---:|
| `registry.register(...)` | 36 | 102 |
| `parse_artifact(...)` | 37 | 108 |
| `register_product_class(...)` | 10 | 90 |
| `Perspective(...)` | 10 | 40 |
| `MaxTTL(...)` | 10 | 10 |

`register_product_class` (10 sites, 90 lines) is the largest of these. In quickstart it is
`run.py:321-329`, taking `schema_name`, `schema_version`, `ttl_anchor`, `assembly_mode`,
`max_ttl_key`, `max_ttl_version` — all sourced from `control["product_class"]`
(`controlplane.yaml:66-72`) plus the MaxTTL pin minted three lines earlier. CONTEXT.md's carried
ruling gives the product-class declaration a typed artifact class. **The `max_ttl_version` pin is
minted at runtime** (`run.py:318-320`), the same shape as Q1 — the artifact declares the *key*,
the builder resolves the version.

`Perspective(...)` is 4 lines in every site, reading `control["perspective"]["principal_id"]` and
`["role"]`. A typed `ccf.perspective` class makes it one `parse_artifact`.

**`registry.register`** is where the manifest (D-05/D-06) lands. Note the quickstart pattern:
`spec_version = registry.register(...)` — the *return value* is the pin, and every pin then flows
into `boot()` (`run.py:216-223`), `PolicyFilterParameters` (`:241`), `ProductLineage` (`:341`), and
`PolicyBinding` (`:381-383`). **D-06's "returns a typed pin set the adopter reads and passes to
`build_replay_record`" is exactly right and non-negotiable** — those four downstream consumers must
keep receiving explicit pins.

### 3.6 The agent / skill / factory paths — swept, and clean

CONTEXT.md's deferred item asked whether the Agent & Task Factory definition-artifact paths carry
comparable marshalling burden. **They do not.** `[VERIFIED: AST call-site sweep across examples/]`

The factory surfaces already consume artifacts declaratively — CINV-01c
(`tools/lints/no_hardcoding.py:88-96`) *forces* `Agent`/`Task`/`Workflow` construction through an
explicit factory-module allowlist (`src/ccf/agents/factory.py`, `src/ccf/workflow/factory.py`),
so no example can hand-marshal an agent even if it wanted to. The only agent-adjacent duplication
found is `catalog.register` (3 sites, 3 lines) and `callables.register` (3 sites, 14 lines) —
negligible.

**Conclusion: the deferred item resolves to "out of scope, nothing found."** The planner should
record this so it is not re-litigated. The 2026 examples suite's marshalling burden is entirely in
the *fabric* path (L1–L6 + Control Plane), not the agent path — which is itself a datum: the
No-Hardcoding Rule's factory discipline worked where it was applied, and this phase is applying it
where it was not.

### 3.7 One-off patterns (not helper targets)

- `05-workflow-hitl/run.py::_register_closure` — 49 lines, `run.py:266-314`. Single site. Workflow
  definition registration. Not a duplication signal; leave it, or fold it into the manifest if the
  manifest grows a workflow-definition class.
- `06-decision-replay/run.py::_registry` — 9 lines, `run.py:488-496`. Single site.
- `external/00-hello-context/replay_server.py::_load_fixtures` — fixture machinery, not CCF wiring.

---

## 4. Boot / Registry / Operator-Registry Wiring (Success Criterion 3)

### 4.1 `boot()` today

`src/ccf/boot.py`, algorithmic-tagged (`boot.py:55`). Signature (`boot.py:143-153`):

```python
def boot(*, database_path=None, postgres_dsn=None, postgres_schema=DEFAULT_SCHEMA,
         registry: ControlPlaneProtocol,
         resolution_spec_key: str, resolution_spec_version: str,
         policy_bundle_key: str, policy_bundle_version: str) -> FabricHandle
```

Properties the phase must preserve:

- **No defaults, no "latest"** — "a fabric whose configuration could drift between boots is a
  fabric whose decisions cannot be replayed (D-IMPL-38, whitepaper §7.10)" (`boot.py:158-161`).
  D-05 explicitly preserves this: the manifest *produces* the pins, `boot` still *requires* them.
- **Substrate is never inferred** — `_open_backend` (`boot.py:113-141`) raises unless exactly one
  of `database_path`/`postgres_dsn` is given: "a fabric that guessed its own substrate could
  silently boot against a development SQLite file in production and would still pass every test"
  (`boot.py:120-126`). **This is the load-bearing constraint behind D-08.**
- **`postgres_dsn` is never persisted** (`boot.py:167-170`) — hence D-08's "manifest declares the
  kind, the connection is a call argument."
- **`FabricHandle` has no writer attribute, not even private** (`boot.py:60-97`). The D-05 entry
  point returns this same object. **It must not grow one** (C-5).
- **The boot token is minted once per graph** (`boot.py:14-18`); a second boot raises before any
  write.

`boot(...)` costs exactly **8 lines** at every one of its 11 call sites — the *call* is not the
friction. As CONTEXT.md D-05 says, "the friction is the eleven lines *before* it." Verified:
quickstart `run.py:201-214` is 14 lines of registration producing four pins, all consumed by the
8-line boot call.

### 4.2 `ControlPlaneRegistry`

`src/ccf/controlplane/registry.py`. `register(key, artifact, *, actor=None) -> str`
(`registry.py:282-304`):

- Version is `content_hash(artifact)` (`registry.py:296`) — content-addressed, so re-registering
  byte-identical content is idempotent and returns the same version (`registry.py:289-290`).
- Refuses anything not canonically serializable — floats, naive datetimes (`registry.py:284-287`).
  **This is the second enforcement point D-02's timestamp handling must satisfy**: a naive
  datetime reaching `register` raises `CanonicalizationError`, which is why the `_instant` helper
  exists at all.
- `register_typed(key, artifact, artifact_class)` exists on the Protocol (`registry.py:170-174`)
  — validates against an `ArtifactClass` before appending. **Underused in examples** (0 call sites
  found). The manifest loader should use `register_typed`, not `register`: it is the existing
  mechanism for exactly this job.
- `resolve_latest` exists (`registry.py:180-182`) but the manifest path must **never** use it —
  that is the "latest" `boot` refuses.
- The audit log is injectable so registry and grant ledger share one sequence (`registry.py:204-210`).
  The manifest loader must not construct a second `ControlPlaneRegistry` behind the adopter's back.

### 4.3 `OperatorRegistry`

`src/ccf/operators/registry.py:85-138` (**not** `projection/engine.py` — CONTEXT.md's
canonical-refs entry is off by a module; the planner should use `src/ccf/operators/registry.py`).

`register(operator, *, version=None)`:

- Reads category and parameter schema **off the operator**, never from the caller
  (`registry.py:94-99`): "a registration that could declare a category different from the one the
  operator reports would let the planner order an operator into a position it does not belong in,
  which is precisely the Policy-after-Similarity failure INV-CH7-26 forbids." **A builder must
  not re-introduce a caller-declared category.**
- `DuplicateOperatorKey` is fatal (`registry.py:100-109`).
- Category must be one of the four canonical (`registry.py:110-115`).

The D-07 builder wraps this; it does not replace it.

### 4.4 Per-deployment policy vs. copy-paste — the classification

| Thing | Classification | Evidence |
|---|---|---|
| Which artifacts exist and under which keys | **Per-deployment policy** — stays explicit (D-06: no globs) | `controlplane.yaml:25-30` is deployment vocabulary; `registry.py` never enumerates keys |
| The order/mechanics of registering them | **Copy-paste** — absorb | identical 14-line prologue in 9 files |
| Backend kind (SQLite vs Postgres) | **Per-deployment policy** — manifest declares it (D-08) | `boot.py:120-126` |
| DSN / database path | **Per-deployment environment** — call argument (D-08) | `boot.py:167-170` |
| The `(key, version)` pins passed to `boot` | **Derived** — manifest produces, adopter still reads (D-06) | `run.py:216-223` |
| Which four operators to register | **Per-deployment policy** — the artifact set declares it | `02-skilling` registers 3, not 4 (`run.py:271-308`) |
| Constructing each operator from its parameters | **Copy-paste** — absorb (D-01/D-07) | 579 lines across 9 sites |
| Corpus extraction rules | **Per-deployment policy**, but declared in the operator-parameters artifact (D-03) | `ontology.yaml:84-86` |
| The temporal boundary the corpus is read at | **Per-deployment policy** — stays a caller argument | `run.py:249`; D-07 rejects lazy binding for exactly this reason |
| Projection Π (`plan_id`, `required_operators`, `invoke`) | **Deployment code** — not a target | `run.py:138-182`; whitepaper §7.5 |
| The product's lineage claim | **Deployment assertion** — stays explicit (D-15A) | `run.py:339-343` |

---

## 5. The Governance Line, Surface by Surface (Success Criterion 4)

For each candidate helper: *what does this hide from the replay record?*

### 5.1 The invariant register, and where each is touched

| Invariant | Where enforced | Touched by this phase? | Verdict |
|---|---|---|---|
| **Gate 1 — empty-operator guard** | `gates.py:205-207` `_refuse_empty_operators` | No helper produces `lineage.operators_invoked` | Untouched |
| **Gate 2 — lineage strict equality** | `gates.py:203,209-217` | `run_gates(candidate, engine_resolved=execution.operators_invoked, ...)` — two inputs from two sources | **MUST STAY EXPLICIT.** See 5.2 |
| **Gate 3 — TTL bounds** | `gates.py:187-201` — MaxTTL resolved from the registry via the pin on `product_class` | A product-class artifact class declares the `max_ttl_key`; the *version* pin is minted at registration | Safe if the pin stays explicit — see 5.4 |
| **Single-writer** | `boot.py` composition root; CINV-02 import lint over `ccf.graph._writer` | `ccf.deployment` imports `ccf.boot`, never `ccf.graph._writer` | Safe; **CI-verify** |
| **Algorithmic ⇄ Semantic Alternation** | `tools/lints/algorithmic.py`, CINV-03 | `ccf.deployment` tagged algorithmic, imports no LLM client | Safe; verified in 7.1 |
| **Five-dimension replay record** | `replay/record.py::build_replay_record` | Pin set flows *into* it from the manifest loader | Safe if pins are explicit args — see 5.3 |
| **Skill-grant compatibility check** | `ccf.skills` grant path | Not touched — §3.6 found no marshalling in the agent path | Untouched |
| **Composition-preservation `(A∘B)(G)=A(B(G))`** | operator pair tests | Operators are constructed differently, not changed | Untouched; regression-test anyway |
| **No-Hardcoding (CINV-01)** | `tools/lints/no_hardcoding.py` | New loaders are interpreters; must hold no key name | Safe by construction; **see 7.2 for a trap** |

### 5.2 `run_gates` — the line, stated precisely

`src/ccf/products/gates.py:172-217`:

```python
def run_gates(candidate: ContextProductContract, *, engine_resolved: frozenset[str],
              now: datetime, registry, product_class) -> ServableProduct | GateRefusal:
    declared = candidate.lineage.operators_invoked       # :203  ← source A: the product's CLAIM
    ...
    if declared != engine_resolved:                      # :209  ← source B: what the ENGINE observed
        return LineageMismatchRefusal(...)               # :210-217
```

`engine_resolved` is documented as "The operator set the projection engine observed itself
running" (`gates.py:184-185`); `declared` is what the producer wrote into `ProductLineage`. In
quickstart both are typed by hand at `run.py:339-343` and `run.py:346-352`.

**The prohibition, in operational terms — the planner must encode this as a hard rule for every
plan that touches L6:**

> No shipped helper may accept a single input and emit *both* `ProductLineage.operators_invoked`
> and the `engine_resolved` argument. No helper may construct a `ContextProductContract` whose
> `lineage.operators_invoked` is read from a `ProjectionExecution`. No helper may wrap `run_gates`
> in a signature that takes only the execution.

`QuickstartPlan.required_operators()` returning `operators.keys()` (`run.py:301`) is *already*
uncomfortably close to this — the plan declares it requires whatever happens to be registered. It
is not a violation (the plan's *declaration* and the engine's *resolution* are still separate
mechanisms, and the projection docstring at `run.py:141-145` says so: "it does not run them and
cannot tell the engine what ran — which is what leaves the L6 lineage gate something real to
check"). But a helper that made this the *only* pattern would harden a shortcut into the SDK.
**Recommendation: the rewritten quickstart should declare `required` from the artifact, not from
`operators.keys()`,** so the demonstrated pattern is the safe one. This is a D-15A-motivated
change, not a mechanical one — flag it for Dave's awareness in the surface-change log.

### 5.3 The pin set and replay dimension 2

`build_replay_record(..., policy_bindings=(PolicyBinding(key=..., version=...),), ...)`
(`run.py:376-387`). The manifest loader (D-05/D-06) becomes the source of those keys and versions.

**What it must not do:** construct the `PolicyBinding` tuple itself and pass it to
`build_replay_record` internally. D-06 already rules this correctly — "the call returns a typed
pin set the adopter reads and passes to `build_replay_record`." The adopter's line stays.

**Residual risk the planner must watch:** if the pin-set object grows a convenience method like
`pins.policy_bindings()`, the adopter's line becomes `policy_bindings=pins.policy_bindings()` and
the *selection* of which bindings are in force becomes implicit. That is a governance-boundary
move. **Recommendation: the pin set is a plain typed record of `(key, version)` pairs with no
projection helpers.** Record as a design constraint.

### 5.4 The MaxTTL pin (Gate 3)

`run.py:318-320` mints `max_ttl_version = registry.register(keys["max_ttl"], MaxTTL(seconds=...))`,
then `register_product_class(..., max_ttl_key=..., max_ttl_version=max_ttl_version)`
(`run.py:321-329`). `run_gates` resolves the pin from the registry at gate time
(`gates.py:196-201`, raising `ControlPlaneMissing` rather than refusing — "that is a broken
deployment, not a bad product, and the two must not be reported the same way").

A product-class artifact class can declare `schema_name`, `schema_version`, `ttl_anchor`,
`assembly_mode`, and `max_ttl_key`. It **cannot** declare `max_ttl_version` — that is minted by
registration. Same shape as Q1.

**Verdict: safe.** The MaxTTL *value* stays in an artifact and the *pin* is derived from
registering it; nothing about Gate 3's independence changes. The TTL ceiling and the product's
own `expires_at` (`run.py:336-337`, from `declared["product_ttl_seconds"]`) remain two separately
authored numbers, which is the independence Gate 3 checks.

### 5.5 Candidates that would require a governance boundary to move — **DECISIONS, not tasks**

Two, both surfaced as decisions per D-15A's "such cases are surfaced as decisions, not resolved
by the phase":

- **G-A: `permitted_policy_bundle_versions` sourcing.** See Q1 / §9.2.
- **G-B: `QuickstartPlan.required_operators() == operators.keys()`.** See 5.2. Not a defect today;
  becomes one if a helper canonizes it.

Everything else in §3 clears D-15A's discriminator: no second independent source exists that the
fabric checks the value against.

### 5.6 A governance-adjacent risk of D-09 the planner must handle

`tools/lints/__main__.py:36-51` scopes CINV-01 (No-Hardcoding) to `("src", "runtime", "examples")`
— **`tests/` is not a linted tree.** D-09 moves assertions and print summaries into `tests/`.
Those assertions carry domain expectations (`controlplane.yaml:92-99`'s `expected:` block is read
at `run.py:364-372`).

**Risk:** if the relocated assertions inline the expected values instead of continuing to read
them from the artifact, domain values silently escape CINV-01's reach. That would be a real,
CI-invisible weakening of the No-Hardcoding Rule.

**Mitigation the planner must task:** the relocated test modules read the same `expected:` artifact
blocks the examples read today, and one of:
(a) add `tests` to `RULE_TREE_SCOPE["no-hardcoding"]` — a lint-scope change, therefore a recorded
decision, or (b) a permanent guard test asserting the relocated modules contain no domain literals.
**Recommend (a); it is one line of config and it closes the hole structurally.** Either way, record
it.

---

## 6. Public-Surface Change Inventory (Success Criterion 6)

### 6.1 Likely reshaped / removed, by confidence

**Certain (implied directly by locked decisions):**

| Surface | Change | Driver | Type |
|---|---|---|---|
| `ccf.controlplane.artifacts` module docstring | Amended — the operator-parameter-set sentence at `artifacts.py:145-158` | D-01 | Doc (mkdocstrings-published; Phase 16 rendered reference changes) |
| `load_artifact` | **Behavior change** — PyYAML timestamp resolver suppressed; returns `str` where it returned `datetime` | D-02 | Behavior |
| `ccf.controlplane.artifacts.__all__` | Grows — new `ArtifactClass` constants and contracts | D-01 | Addition |
| `ccf.deployment` (new package) | Added: manifest class, loaders, boot/registry/operator builders | D-13 | Addition |
| `ccf.operator-parameters.*` artifact classes ×4 | Added | D-01 | Addition |
| `ccf.resolution-spec` artifact class | Added; closed-world | D-03 | Addition |
| `ccf.perspective`, product-class artifact classes | Added | carried ruling | Addition |
| `ccf.deployment-manifest` artifact class | Added | D-05 | Addition |
| `ccf schema export` CLI command | Added (ninth noun alongside agent/skill/config/replay/product/workflow/artifact/hitl) | D-04 | Addition |

**Likely (follows from the evidence, needs a plan-level ruling):**

| Surface | Change | Driver |
|---|---|---|
| `EntityResolutionSpec` | Gains a `semver` field (inherit `_VersionedArtifact`) — **content-hash-affecting**, so every registered spec's version changes | §2.3, §3.1 |
| Example YAML root keys | `schema_version`/`artifact_version` → `semver`, across up to 65 files | §2.3 |
| `events.yaml` shape | `source_system_id` → `source.system_id`; `payload` → `raw_payload` | §3.3 option (a) |
| `ontology.yaml` shape | Split per D-03 | D-03 |
| `tools/lints/__main__.py::RULE_TREE_SCOPE` | `tests` added to `no-hardcoding` | §5.6 |

**Not changing (state explicitly — D-14 is additive):** `boot()` signature, `FabricHandle`,
`run_gates` signature, `ControlPlaneRegistry.register`, `OperatorRegistry.register`,
`EntityResolutionRule`, `RelationshipResolutionRule`, `SignalEnvelope`, the four `*Parameters`
classes, `parse_artifact`, `ArtifactClass`, `DeclaredArtifact`, `register_product_class`,
`build_replay_record`, `serve`.

### 6.2 Proposed shape of the D-15 record

Two artifacts, per D-15.

**(a) Generated signature manifest + diff — completeness guarantee.**

- **Where:** `docs/surface/v0.2-surface.json` (phase-start baseline, committed) and a
  `make surface` regenerator, mirroring Phase 14's committed-and-drift-checked `openapi.json`
  exactly (`Makefile:168-169` → `tools/dump_openapi.py`; drift asserted in
  `tests/http_api/test_openapi.py`). `[VERIFIED: Makefile:168-169; tests/http_api/test_openapi.py exists]`
- **Format:** JSON — for each public module, its `__all__` and for each exported name its kind and
  signature (`inspect.signature` for callables, field names+annotations for `CCFContract`
  subclasses). JSON because the drift check is a diff and JSON diffs are reviewable.
- **Generator:** `tools/dump_surface.py`, sibling to `tools/dump_openapi.py`. Same pattern, no new
  toolchain.
- **CI:** a test asserting the committed manifest matches the live surface, so a surface change
  that forgets the log is a red build, not a discovery in Phase 16.
- **Phase-close deliverable:** the diff of `v0.2-surface.json` (start) vs end.

**(b) Curated surface-change log — rationale and migration.**

- **Where:** `docs/SURFACE-CHANGES.md`, written incrementally as plans land.
- **Why `docs/` and not `public/`:** Phase 14 established `public/` as the published tree with
  default-deny-by-existence publication (`tools/publish_scan.py`). A migration note **should** be
  published for adopters — but publishing it is Phase 16's editorial call, not this phase's.
  Writing it in `docs/` and letting Phase 16 `git mv` it into `public/` matches the Phase 14
  precedent for the walkthrough and diagrams (plan 14-04). **Flag for the planner: confirm with
  Dave whether the migration note ships in v0.2's published site or waits for Phase 16.**
- **Entry shape:** one section per change — `Surface` / `Change type` (added / reshaped / removed /
  **behavior**) / `Before` / `After` / `Why` / `Migration`. The **behavior** type exists because
  D-14 explicitly notes D-02 is "a behavior change to `load_artifact` even though no surface is
  removed" — a pure signature diff will not catch it, which is precisely why both artifacts are
  needed.
- **Handoff:** named as a direct input in the Phase 16 entry.

---

## 7. CI Invariants and Blast Radius

### 7.1 The lint suite

`tools/lints/` — four checkers, driven by `python -m tools.lints --all` (`Makefile:43-44`).
`[VERIFIED: file read]`

| Rule | Module | Trees scoped | Allowlist? |
|---|---|---|---|
| `cinv01a-prompt-shape` | `no_hardcoding.py` | `src`, `runtime`, `examples` | Yes — `tools/lints/allowlist.yaml`, keyed `{file, rule, fingerprint}` |
| `cinv01b-numeric-table` | `no_hardcoding.py` | same | same |
| `cinv01c-factory-bypass` | `no_hardcoding.py` | same | same + `FACTORY_MODULE_ALLOWLIST` |
| `cinv02` harness imports | `harness_imports.py` | `src`, `runtime` (**not** `examples`) | No |
| `cinv03` algorithmic | `algorithmic.py` | `src`, `runtime` | No — "an exempted algorithmic module is simply a semantic module and should drop the tag" (`algorithmic.py:16-18`) |
| `cinv04` orchestration split | `orchestration_imports.py` | `src`, `runtime` | No |

**D-13's purity claim, independently verified.** `algorithmic.py:33-50`: the check is
`__ccf_mode__ == "algorithmic"` ⇒ no import of `ccf.llm`, `anthropic`, `openai`, `cohere`,
`litellm`, `google.generativeai`, `mistralai` — "at module scope or deferred inside a function."
**Nothing about filesystem I/O.** `boot.py:55` carries the tag while opening SQLite files
(`boot.py:137-140`). `artifacts.py:47` carries it while importing `yaml`. **D-13 needs no lint
change.** Confirmed.

### 7.2 Two lint traps for the new loaders

**Trap 1 — CINV-01a on error messages.** `no_hardcoding.py:64-75`: a string ≥40 chars scoring ≥2
of four signals is flagged. Signals include ≥3 sentences, ≥200 chars of prose, and role-openers
(`"you are"`, `"always"`, `"never"`, `"respond"`). Error messages in `ccf.deployment` will be long
and explanatory (D-02's must "name D-IMPL-38"; the existing precedent at `artifacts.py:283-287` is
a 3-line message opening with a clause containing "not"). Docstrings are excluded **by position**
(first `Expr` of a body), never by content — an error string is not in that position.
**Mitigation:** keep messages under 200 chars and under 3 sentences, or budget allowlist entries
with reviewer sign-off. The planner should assume at least a couple of allowlist entries and task
them explicitly rather than discovering them in CI.

**Trap 2 — CINV-01b on parameter-schema modules.** `no_hardcoding.py:87` scopes the
no-numeric-defaults rule to modules whose path matches `PARAM_SCHEMA_MARKERS = ("params",
"parameters", "thresholds")`. If any `ccf.deployment` module is named `*parameters*` (a natural
choice for the operator-parameters loader), it inherits that rule. That is *desirable* — but the
planner should name it deliberately rather than trip it accidentally.

**Trap 3 — D-09 moves domain values out of CINV-01 scope.** See §5.6.

### 7.3 Test suites and the baseline

- **Baseline: 1,548 tests collected** (`PYTHONPATH=src:runtime .venv/bin/python -m pytest
  --collect-only -q`). The brief's "~1531" is close; the delta is post-Phase-14 additions.
  `[VERIFIED: pytest collection at HEAD]`
- **Note for the planner:** collection **fails** (52–98 errors) unless run through the repo venv
  with `PYTHONPATH=src:runtime`. Use `make test` / `make ci-core`, never a bare `pytest`.
- `make ci-core` = `lint typecheck test` (`Makefile:52`). `make ci` = `ci-core examples
  docs-strict` (`Makefile:63`).
- `make typecheck` = `mypy --strict` over `src` + `runtime` (`Makefile:46-47`). **The new
  `ccf.deployment` package is `--strict`-typed from its first line.**
- **`make ci` includes `docs-strict`.** Reshaping public surface breaks mkdocstrings-rendered
  reference pages under `public/reference/protocols/` and `public/reference/artifacts/`
  (8 pages, `mkdocs.yml:152-159`) and the snippet markers literal-included from examples.
  **Every example rewrite is simultaneously a docs-build change.**
- **Snippet markers:** 92 `--8<--` markers across 9 example files (`00`:16, `04`:16, `05`:14,
  `02`:10, `01`:8, `03`:8, `07`:8, `06`:6, `external/client_bare`:6). Rewriting the examples
  invalidates marker line ranges; `make docs-strict` will catch it, and Phase 16 re-cuts them
  (criterion 6). **This phase must keep the markers valid, not perfect** — perfecting them is
  Phase 16's job. Task it as "markers survive the rewrite; re-cutting is Phase 16."
- **Publish-safety scan:** `tools/publish_scan.py`, never-publish gate with no allowlist
  (plan 14-02). New docs under `docs/` are not published; new pages under `public/` are.
- **Byte-identity discipline:** the Phase 9/13 precedent is that expected-output regeneration is a
  **reviewed, deliberate event** (ROADMAP Phase 9 criterion 4, Phase 13 criterion 3). Example
  rewrites will change expected outputs. Every regeneration needs an explicit checkpoint.

### 7.4 Blast radius summary

| Tree | Files touched (est.) | Gate |
|---|---|---|
| `src/ccf/deployment/` (new) | ~5-8 modules | `mypy --strict`, CINV-01/03, unit tests |
| `src/ccf/controlplane/artifacts.py` | 1 (docstring + classes + loader) | existing artifact tests + new round-trip tests |
| `src/ccf/assembly/worker.py` | 1 (if `EntityResolutionSpec` gains `semver`) | content-hash change ⇒ every registered spec version changes ⇒ **expected-output regeneration across the suite** |
| `runtime/ccf_runtime/cli/` | +1 command module + `main.py` wiring | CLI tests |
| `examples/` (12 py files, ≤65 yaml) | rewrite | `make examples`, byte-identity checkpoints |
| `tests/` | +1 assertion module per example (D-09) | `make test` |
| `public/` | reference pages regenerate | `make docs-strict` |
| `tools/` | +`dump_surface.py`, maybe `lints/__main__.py` scope | drift tests |
| `perf/` | `perf/suites/common.py` timestamp helper (D-02) | `make perf` bitrot smoke test |

**The `EntityResolutionSpec` semver change is the single largest blast-radius item in the phase.**
It changes `content_hash(spec)` for every deployment, therefore every `resolution_spec_version`
pin, therefore every replay record that carries one. It is safe (nothing is *lost*), but it will
regenerate expected outputs across the suite in one go. **Sequence it early, in its own plan, with
its own regeneration checkpoint** — do not let it land in the middle of the example rewrites where
its regeneration blast is indistinguishable from a rewrite defect.

---

## 8. Validation Architecture

> `workflow.nyquist_validation` was not found as an explicit `false` in `.planning/config.json`;
> treated as enabled.

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (repo venv at `.venv/bin/python`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.mypy]`) |
| Quick run command | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/<area> -x -q` |
| Full suite command | `make test` (= `CCF_REQUIRE_HARNESSES=1 pytest -q`) |
| Phase gate command | `make ci` (= `lint typecheck test examples docs-strict`) |
| Collected baseline | **1,548** tests |

### Per-target validation

| Target | Validation type | Automated command | Exists? |
|---|---|---|---|
| **Round-trip** — every new artifact class | `parse_artifact(yaml.safe_load(text), K)` → `content_hash` → re-serialize → re-parse → identical object; and `content_hash` stable across two parses | `pytest tests/controlplane/test_artifact_roundtrip.py -q` | ❌ Wave 0 |
| **Closed-world** — D-03's whole point | An unknown key in `ccf.resolution-spec` raises `ArtifactLoadError` | same module | ❌ Wave 0 |
| **D-02 timestamps** | `...Z` → aware UTC; `...+00:00` → aware; naive (no designator) → `ArtifactLoadError` naming D-IMPL-38; PyYAML resolver provably suppressed (a bare timestamp scalar arrives as `str`) | `pytest tests/controlplane/test_timestamps.py -q` | ❌ Wave 0 |
| **Float rejection unchanged** | existing `_reject_floats` tests still pass after the loader change | existing | ✅ |
| **Gate-tautology regression** — the D-15A guard | Two tests: (1) a `run_gates` call where `engine_resolved` is deliberately perturbed **must** produce `LineageMismatchRefusal`; (2) an AST guard over `src/ccf/deployment/` asserting no function returns or constructs both a `ProductLineage` and an `engine_resolved`-shaped value from one parameter | `pytest tests/products/test_gate_independence.py -q` | ❌ Wave 0 — **highest-value new test in the phase** |
| **Single-writer preserved** | `FabricHandle` returned by the D-05 entry point has no writer attribute (`not any('writ' in a for a in dir(handle))`); `ccf.deployment` does not import `ccf.graph._writer` | CINV-02 lint + `pytest tests/boot/ -q` | partial ✅ |
| **Manifest determinism (D-06)** | Same manifest ⇒ same pin set, byte-for-byte, across two loads; manifest is content-hashable | `pytest tests/deployment/test_manifest.py -q` | ❌ Wave 0 |
| **Manifest has no globs** | A manifest with a glob-shaped path is refused; adding an unlisted file to the artifacts directory does not change the pin set | same module | ❌ Wave 0 |
| **D-08 backend kind** | manifest `postgres` + no DSN ⇒ loud failure, never a SQLite fallback | same module | ❌ Wave 0 |
| **D-07 ordering constraint** | The operator-registry builder cannot be called without a `GraphView` (type-level, asserted by a mypy-fail fixture or a runtime `TypeError`); the corpus is read at the caller's named boundary | `pytest tests/deployment/test_operator_builder.py -q` | ❌ Wave 0 |
| **Composition-preservation unaffected** | existing operator-pair tests green after construction changes | existing suite | ✅ |
| **Line-count assertion (Criterion 1/5)** | An executable check asserting each rewritten example's mechanical line count is at or below the recorded post-value, and reporting the before/after delta. **Per D-12 there is no target number** — the test pins the *achieved* number so it cannot silently regress | `pytest tests/examples/test_surface_audit.py -q` | ❌ Wave 0 |
| **Surface manifest drift (D-15)** | Committed `docs/surface/*.json` matches the live surface | `pytest tests/test_surface_drift.py -q` | ❌ Wave 0 |
| **JSON Schema freshness (D-04)** | `ccf schema export` output matches the committed schemas | `pytest tests/cli/test_schema_export.py -q` | ❌ Wave 0 |
| **Eight-example suite green** | all nine examples + external run and exit 0 | `make examples` | ✅ |
| **D-09 relocated assertions** | Each example has a parallel test module asserting against its output; no example loses an assertion in the move (count comparison against the pre-phase baseline in §1.3) | `pytest tests/examples/ -q` | ❌ Wave 0 |
| **Docs build** | mkdocs strict + publish scan after every surface change | `make docs-strict` | ✅ |

### Sampling rate

- **Per task commit:** `make lint typecheck` + the touched area's `pytest -x -q`. Sub-30s.
- **Per wave merge:** `make ci-core` (lint + typecheck + full 1,548-test suite).
- **Per example rewrite:** `make example-NN` for the rewritten example + `make docs-strict`.
- **Phase gate:** `make ci` fully green, then `/gsd-review --phase "Phase 15" --all` per CLAUDE.md
  §3.1, then STOP and present to Dave.

### Wave 0 gaps

- [ ] `tests/deployment/` — new package; `conftest.py` with shared manifest/artifact fixtures
- [ ] `tests/controlplane/test_artifact_roundtrip.py` — round-trip + content-hash stability
- [ ] `tests/controlplane/test_timestamps.py` — D-02
- [ ] `tests/products/test_gate_independence.py` — **the D-15A guard; write it first, before any
      helper exists, so it is a standing constraint rather than a retrofit**
- [ ] `tests/examples/test_surface_audit.py` — the criterion-1 measurement, as an executable check
- [ ] `tests/test_surface_drift.py` + `tools/dump_surface.py` — D-15 baseline captured **at phase
      start**, before the first surface change
- [ ] `tests/examples/test_*_output.py` ×9 — D-09 relocated assertions
- [ ] Framework install: none needed — pytest, mypy, and the lints are all present

---

## 9. Sequencing and Risk

### 9.1 Proposed implementation order

**Wave 0 — instrumentation and standing guards (nothing else may start first).**
1. `tools/dump_surface.py` + committed phase-start baseline + drift test. *If this is not captured
   before the first surface change, criterion 6 cannot be satisfied honestly.*
2. `tests/products/test_gate_independence.py` — the D-15A guard, as a standing constraint.
3. `tests/examples/test_surface_audit.py` — record the §1.3 before-numbers as the audit baseline.
4. `docs/SURFACE-CHANGES.md` skeleton.

**Wave 1 — the artifact classes (no wiring yet, no example changes).**
5. `ccf.deployment` package skeleton, algorithmic-tagged, with the D-13 docstring writing down the
   "algorithmic means no model call, not no I/O" reading and the `run_gates` worked example.
6. The class-id → `ArtifactClass` lookup (§2.1 — new structure).
7. D-02 timestamp handling in `load_artifact` + the `ccf.deployment` file-reading loaders.
   *Independent of everything else; unblocks the 11 `_instant` deletions.*
8. `ccf.resolution-spec` (D-03 split) + `EntityResolutionSpec` semver decision.
   **Own plan, own regeneration checkpoint** (§7.4).
9. The four `ccf.operator-parameters.*` classes (D-01) — **blocked on Q1's ruling**.
10. `ccf.perspective`, product-class, signal-batch classes.
11. `artifacts.py` docstring amendment (D-01) — a recorded surface change.

**Wave 2 — wiring.**
12. `ccf.deployment-manifest` class + the D-05/D-06/D-08 one-call entry point + pin set.
13. The D-07 two-phase view-aware operator-registry builder.

**Wave 3 — CLI and authoring ergonomics.**
14. `ccf schema export` + committed JSON Schemas + freshness gate (D-04).
15. `# yaml-language-server: $schema=` headers on example artifacts.

**Wave 4 — example rewrites, in ascending risk.**
16. `00-quickstart` first — it is the day-1 example, the measured baseline, and the smallest full
    fabric. It proves the whole surface before eight more files depend on it.
17. `01`, `02`, `03`, `07` — the four other full-fabric single-process examples.
18. `08-e2e-demo` — largest, but zero assertions (its verification is byte-compared narration), so
    D-09 does not apply and the risk is contained.
19. `06-decision-replay` — highest mechanical count (176) *and* the replay example, so it is where
    a pin-set mistake is most consequential. Do it after the pattern is proven five times.
20. `04-cross-process` (`run.py` + `producer_child.py`) — **also carries D-10's re-domaining to
    banking.** Two changes in one file set; keep them as separate commits.
21. `05-workflow-hitl` — lowest mechanical density (3.3%), mostly a D-09 relocation.
22. **`examples/external/` last.** See 9.3.

**Wave 5 — close.**
23. The criterion-1 audit report with before/after (D-11).
24. Surface diff + curated log finalized and handed to Phase 16.

### 9.2 Decisions that must be ruled before their plans execute

Per CLAUDE.md §15 and C-10/C-12. Next free number is **D-IMPL-76** (`docs/DECISIONS.md` currently
runs to D-IMPL-75; entries are `D-IMPL-NN` inline, not `###` headings — the planner should match
the file's existing formatting rather than assume a heading style).

- **D-IMPL-76 (candidate) — how the operator-parameters artifact supplies
  `permitted_policy_bundle_versions`.** Blocks Wave 1 item 9. See Q1.
- **D-IMPL-77 (candidate) — whether `EntityResolutionSpec` gains `semver` in place or is wrapped.**
  Content-hash-affecting; blocks Wave 1 item 8. See Q2.
- **D-IMPL-78 (candidate) — CINV-01 lint scope over `tests/`.** Blocks D-09 relocation. See §5.6.
- **Confirm with Dave:** whether `docs/SURFACE-CHANGES.md` publishes in v0.2 or waits for Phase 16
  (§6.2b).

None of these is whitepaper-ambiguous; all three are SDK-extension questions where CLAUDE.md §15
directs a `D-IMPL-NN` entry rather than a picked default.

### 9.3 Where the phase is most likely to accidentally collapse a governance boundary

Ranked by likelihood × severity:

1. **The one-call entry point growing past wiring.** D-05's call "loads, validates, registers, and
   boots." The next obvious convenience — *and also runs the operators, and also projects* — is
   one refactor away, and it would swallow `engine_resolved`. **Guard: `test_gate_independence.py`
   from Wave 0, plus a hard rule that nothing in `ccf.deployment` imports `ccf.products.gates`.**
   That import ban is cheap, mechanical, and should be added to the lint config.
2. **The pin set growing projection helpers.** §5.3. A `pins.policy_bindings()` convenience makes
   the *selection* of bindings in force implicit. **Guard: the pin set is a plain typed record.**
3. **D-09 relocating domain values out of CINV-01's reach.** §5.6. **Guard: D-IMPL-78.**
4. **`required_operators()` canonized as `operators.keys()`.** §5.2 / G-B. **Guard: the rewritten
   quickstart declares `required` from the artifact.**
5. **The D-07 builder drifting toward lazy binding** because the two-phase signature is awkward.
   D-07 explicitly rejected lazy binding — it would build the index inside the algorithmic path
   over a corpus determined by invocation timing. **Guard: `test_operator_builder.py` asserts the
   builder cannot be called without a view.**
6. **`examples/external/` losing its zero-CCF-imports property.** The client legs
   (`client_bare.py`, `client_anthropic.py`, `client_adk.py`) demonstrate EXAM-04's core claim and
   are already near-zero mechanical (§1.3). The fabric side (`serve.py`, 133 mechanical lines) is a
   legitimate target; **the client legs are not.** `run.py:` already carries a zero-CCF-import grep
   assertion (plan 13.1-04). Touch `serve.py` only, and only after the pattern is proven on
   examples 00–08 — this is why it sequences last.

### 9.4 What unblocks what

```
Wave 0 (surface baseline + gate guard)  →  everything
D-02 timestamps                         →  11 _instant deletions (independent of all else)
class-id lookup                         →  manifest (D-05)
ccf.resolution-spec (D-03)              →  9 _resolution_spec deletions; also gates the semver
                                            regeneration (do it early, alone)
operator-parameters classes (D-01, Q1)  →  D-07 builder  →  9 operator-block deletions
manifest (D-05/06/08)                   →  boot/registry deletions in 11 files
all of the above                        →  example rewrites (00 first, external last)
example rewrites                        →  criterion-1 audit, D-15 diff, Phase 16 handoff
```

---

## 10. Proposed Requirement Set

One requirement per coherent ergonomic target, ready for the planner to mint. `SC` = ROADMAP
success criterion served.

| ID | Requirement | SC | Size | Notes |
|---|---|---|---|---|
| **ERGO-01** | A committed public-surface signature manifest + `make surface` regenerator + CI drift assertion, baselined at phase start | 6 | S | Wave 0. Must land before any surface change |
| **ERGO-02** | A standing gate-independence guard: `run_gates` keeps two independent inputs, enforced by regression test **and** by a ban on `ccf.deployment` importing `ccf.products.gates` | 4 | S | Wave 0. The D-15A enforcement mechanism |
| **ERGO-03** | The criterion-1 surface audit is an executable check recording per-example mechanical line counts before and after | 1, 5 | S | Wave 0 baseline; Wave 5 report. D-11/D-12 |
| **ERGO-04** | `ccf.deployment` package exists in `/src`, algorithmic-tagged, `mypy --strict`-clean, with a docstring recording the CINV-03 reading and the `run_gates` worked example | 3 | S | D-13 |
| **ERGO-05** | A class-id → `ArtifactClass` lookup, covering SDK-shipped classes and `declared_artifact_class` fallthrough | 2 | S | New structure — §2.1 |
| **ERGO-06** | Timestamp-shaped scalars load as strings and parse via `datetime.fromisoformat`; PyYAML's resolver is suppressed in the artifact path; naive timestamps refused naming D-IMPL-38; the duplicated helper is deleted from every site | 2 | M | D-02. Independent; can run parallel |
| **ERGO-07** | `ccf.resolution-spec` — a closed-world typed artifact class over entity and relationship rules, reached through `parse_artifact`, with the operator-facing attribute maps split out | 2 | M | D-03. Highest duplication (180 lines / 9 sites). Own regeneration checkpoint |
| **ERGO-08** | A typed `ArtifactClass` per SDK-shipped operator category, contracted by the existing `*Parameters` models; `DeclaredArtifact` remains the documented path for deployment-authored operators; the `artifacts.py` docstring is amended | 2 | M | D-01. **Blocked on D-IMPL-76 / Q1** |
| **ERGO-09** | Typed artifact classes for the signal batch, perspective, and product-class declaration | 2 | M | Carried ruling + §3.3 |
| **ERGO-10** | A `ccf.deployment-manifest` artifact class enumerating every artifact explicitly (path, key, class), and one call that loads, validates, registers, and boots — returning the `FabricHandle` plus a plain typed pin set; backend kind declared in the manifest, connection supplied by the caller | 3 | L | D-05/D-06/D-08 |
| **ERGO-11** | A two-phase, view-aware operator-registry builder taking artifacts plus a `GraphView`, building parameter-only and index-backed operators in one call, with the ordering constraint in the signature | 3 | M | D-07 |
| **ERGO-12** | `ccf schema export` emits JSON Schema per artifact class; schemas are committed; example artifacts carry `$schema` headers; a CI freshness gate guards drift | 2 | M | D-04. Follows Phase 14's OpenAPI pattern |
| **ERGO-13** | Examples 00–03, 07, 08 are rewritten to the streamlined surface and stay CI-green | 5 | L | Split per-example at planning |
| **ERGO-14** | Examples 04 (both files, including D-10's re-domaining to banking), 05, and 06 are rewritten and stay CI-green | 5 | L | 06 is highest-risk; 04 carries two changes |
| **ERGO-15** | `examples/external/00-hello-context/serve.py` is rewritten to the streamlined surface; the client legs keep zero CCF imports | 5 | M | Last. §9.3 item 6 |
| **ERGO-16** | Every example's CI assertions and print summaries relocate to a parallel `tests/` module with no loss of assertion coverage, and the No-Hardcoding Rule still reaches the relocated domain values | 5 | L | D-09. **Blocked on D-IMPL-78 / §5.6** |
| **ERGO-17** | A curated surface-change log with rationale and migration guidance, written incrementally, covering additions, reshapes, removals **and behavior changes**, handed to Phase 16 | 6 | M | D-15. The behavior-change class exists for D-02 |

**Coverage check against the six ROADMAP success criteria:**
SC1 → ERGO-03. SC2 → ERGO-05..09, ERGO-12. SC3 → ERGO-04, 10, 11. SC4 → ERGO-02 (with §5 as the
per-surface argument). SC5 → ERGO-13..16. SC6 → ERGO-01, ERGO-17. All six covered; no requirement
serves zero criteria.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Pydantic will coerce YAML lists→tuples and nested dicts→`CCFContract` submodels for `EntityResolutionSpec` without a custom validator | §3.1 | ERGO-07 is larger than estimated. **Cheap to falsify — the planner should spike this in one line before sizing the plan.** |
| A2 | `perf/synth/generator.py` contains a timestamp helper (CONTEXT.md D-02 asserts it; my grep pattern did not match it) | §3.4 | D-02's "13 helpers delete" count is off by one or two. Immaterial to the design; re-verify before asserting the number in the audit |
| A3 | The 65 example YAML files' root `schema_version`/`artifact_version` keys are read by nobody and can be renamed or removed | §2.3 | Artifact churn is larger, or something reads them. Verify with a grep before ERGO-07 executes |
| A4 | Publishing `SURFACE-CHANGES.md` is Phase 16's editorial call, not this phase's | §6.2b | A published migration note lands a phase late. Low severity; confirm with Dave |
| A5 | Relocating assertions to `tests/` preserves CI's guarantee in kind, not merely in count | §5.6, ERGO-16 | An example could pass while its behavior regressed. Mitigated by ERGO-16's no-loss-of-coverage clause |
| A6 | Adding `tests` to `RULE_TREE_SCOPE["no-hardcoding"]` will not produce a large volume of pre-existing findings across the current 1,548-test suite | §5.6 | D-IMPL-78's recommended resolution becomes expensive; fallback (b), a targeted guard test, applies. **Cheap to falsify — run the lint with the scope widened before ruling** |

---

## Open Questions

### Q1 — `PolicyFilterParameters.permitted_policy_bundle_versions` (candidate **D-IMPL-76**). **Blocks ERGO-08.**

**What we know.** `PolicyFilterParameters` has three fields (`params.py:59-61`):
`permitted_policy_bundle_versions: frozenset[str]`, `classification_attribute_by_class`,
`permitted_classifications`. D-03 moves `classification_attribute_by_class` into this artifact
(today at `ontology.yaml:78-82`), and `permitted_classifications` is already in
`controlplane.yaml:50-52`. But `permitted_policy_bundle_versions` is **in no artifact anywhere** —
it is `frozenset({policy_version})` at `run.py:238-240`, where `policy_version` is the return value
of `registry.register(keys["policy_bundle"], control["policy_bundle"])` at `run.py:205-207`. It is
a content hash minted at registration time.

**What's unclear.** A typed `ccf.operator-parameters.policy` artifact class cannot declare it.
Three readings, with consequences:

- **(a) The artifact declares `permitted_policy_bundle_keys` (keys, not versions); the D-07 builder
  resolves each key's registered version and constructs the frozenset.** Most ergonomic. The
  deployment still names *which bundles* it admits — the policy decision — and the SDK resolves
  the pin, which is mechanical. Risk: the builder is now resolving *from the registry*, one step
  closer to "the fabric decides what it admits." Needs a check that resolution is by explicit
  key, never `resolve_latest`.
- **(b) The builder takes the pin set (ERGO-10's return value) as an argument and the adopter
  passes it.** Most conservative; keeps the pin visible in adopter code, matching D-06's posture
  for `build_replay_record`. Costs one adopter line.
- **(c) The artifact stays a `DeclaredArtifact` for the policy category only**, the other three get
  typed classes. Least consistent; hardest to explain in Phase 16's docs.

**D-15A analysis.** Is there a second independent source the fabric checks this against? **Close
but no.** `PolicyFilter._admits` compares `record.policy_bundle_version` (stamped at assembly)
against `params.permitted_policy_bundle_versions` — two sources, but that is an *operator
predicate*, not a validation gate, and the operator's whole job is to compare them. It is not the
`run_gates` situation, where a gate exists specifically to catch a producer misdeclaring. So D-15A
permits (a). But the check is close enough to a governance boundary that CLAUDE.md §15 directs a
ruling rather than a default.

**Recommendation: (b), with (a) available as an opt-in.** (b) is strictly safer, costs one line,
and keeps the pin in the adopter's hand exactly where D-06 already put every other pin — which
makes it the consistent answer rather than a special case. **Ask Dave.**

### Q2 — `EntityResolutionSpec` semver placement (candidate **D-IMPL-77**). **Blocks ERGO-07.**

**What we know.** `EntityResolutionSpec` is a `CCFContract` (`worker.py:105`) with no `semver`
field. SDK-owned artifact classes get their semver lane from `_VersionedArtifact`
(`artifacts.py:134-142`), where `semver` has no default. `registry.register` versions by
`content_hash` (`registry.py:296`).

**What's unclear.** Adding `semver` to `EntityResolutionSpec` changes its content hash, therefore
every `resolution_spec_version` pin, therefore every replay record that carries one. The
alternative — a wrapper class holding `semver` + the spec — means `boot()` receives a wrapper where
it expects a spec (`boot.py`'s `TypeError: the resolution-spec artifact is not an
EntityResolutionSpec`), so `boot`'s contract would change, which D-05 says it must not.

**Recommendation: add `semver` in place, in its own plan, with its own regeneration checkpoint**
(§7.4). The wrapper alternative pushes the change into `boot()`, which is the one contract the
phase committed to preserving. But it is a content-hash change to an L2 contract and CLAUDE.md
§15 says surface it. **Ask Dave.**

### Q3 — Does the D-05 manifest carry `tenant_id`?

Explicitly left to Claude's discretion in CONTEXT.md. Evidence for carrying it: `tenant_id` lives
in `ontology.yaml:24` today, is read at `run.py:191`, and flows into `_envelopes` (`run.py:126`),
`handle.reader.as_of` (`run.py:249`), and `ContextProductContract` (`run.py:334`) — five consumers
of one value that currently rides in an artifact the manifest is splitting apart (D-03 makes
`ccf.resolution-spec` closed-world over rules only, so `tenant_id` has to go *somewhere*).
Evidence against: D-IMPL-05 makes tenancy a first-class runtime axis, and a manifest-pinned
tenant would prevent one manifest serving a multi-tenant deployment.

**Recommendation: the manifest carries an optional `tenant_id`; when absent, the caller supplies
it.** This is a planning-level detail, correctly inside Claude's discretion — no ruling needed —
but the planner should decide it explicitly rather than by omission, because the D-03 split
forces the question.

### Q4 — Does `examples/03-harness-portability`'s live leg constrain the rewrite?

`legs/live.py` (641 lines) and `legs/ollama_client.py` (147 lines) have **zero** mechanical
wiring (§1.3) and are excluded from `make ci` (live legs are opt-in per `Makefile` comments at
`:56-57`, `live-legs.yml`, D-11). So the rewrite touches only `03/run.py` (146 mechanical lines)
and `legs/deterministic.py` (0). **No constraint.** Recorded so the planner does not size for it.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python venv (`.venv/bin/python`) | everything | ✓ | repo-local | none needed |
| pytest | full suite (1,548 tests) | ✓ | via venv | — |
| mypy (`--strict`) | `make typecheck` | ✓ | via venv, `[tool.mypy]` authoritative | — |
| PyYAML | `artifacts.py:42`, all loaders | ✓ | — | — |
| Pydantic | every `CCFContract` | ✓ | v2 (`field_validator`, `model_validator(mode="after")`) | — |
| mkdocs + mkdocstrings | `make docs-strict` (in `make ci`) | ✓ | `docs` extra | — |
| `tools/lints` | `make lint` | ✓ | in-repo | — |
| SQLite | reference graph backend | ✓ | stdlib | — |
| Postgres | D-08's non-default path | not probed | — | SQLite is the default backend for all examples; D-08's Postgres path needs unit-level coverage only |
| Ollama / harness SDKs | `03/legs/live.py` | not probed | — | Live legs are opt-in and outside `make ci` (Q4) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none material — no external package is added by this phase.

## Package Legitimacy Audit

**Not applicable.** This phase installs no external packages. Every dependency it uses is already
in the repository's dependency set (PyYAML, Pydantic, pytest, mypy, mkdocs). `slopcheck` was not
run because there is nothing to check. If a plan later proposes a new dependency, the Package
Legitimacy Gate applies to it at that point.

## State of the Art

Not applicable in the usual sense — this is internal-surface archaeology. The one "old vs current"
axis worth recording:

| Old approach (v0.1/v0.2) | Current approach (post-Phase 15) | When changed | Impact |
|---|---|---|---|
| Two registered artifact classes; every other shape hand-marshalled in `/examples` | Typed artifact class per SDK-owned shape, reached through the same `parse_artifact` seam | Phase 15 | ~1,435 mechanical lines removed from the examples tree |
| Interpreters for SDK-owned shapes live in adopter code | Interpreters live in `/src`, per CLAUDE.md §6.4 as originally written | Phase 15 | The No-Hardcoding Rule applied to its second half |
| `load_artifact` returns whatever PyYAML resolves, including naive datetimes | Timestamps are strings parsed by the SDK; naive refused | Phase 15 (D-02) | **Behavior change** — belongs in the surface-change log |

## Sources

### Primary (HIGH confidence — direct file reads and AST measurement at HEAD `0cfc10c`)

- `src/ccf/controlplane/artifacts.py` (327 lines, read end to end) — the seam, §2
- `src/ccf/boot.py` (lines 1-200 read) — composition root, §4.1
- `src/ccf/operators/params.py` (114 lines, read end to end) — the four `*Parameters` contracts
- `src/ccf/operators/categories.py` (operator classes, `__init__` signatures) — §3.2
- `src/ccf/operators/registry.py:85-138` — `OperatorRegistry`, §4.3
- `src/ccf/products/gates.py:172-217` — `run_gates`, §5.2
- `src/ccf/assembly/worker.py:71-135` — resolution-spec contracts, §3.1
- `src/ccf/signal/envelope.py:46-73` — `SignalEnvelope`, §3.3
- `src/ccf/controlplane/registry.py:166-305` — register/resolve, §4.2
- `examples/00-quickstart/run.py` (451 lines, read end to end) — §1.2
- `examples/00-quickstart/artifacts/{ontology,controlplane,halflife,events}.yaml` — §2.3, §3
- `tools/lints/__main__.py`, `algorithmic.py`, `no_hardcoding.py` — §7.1, §7.2
- `Makefile` — targets, §7.3
- `mkdocs.yml` — reference page inventory, §7.3
- `.planning/phases/15-.../15-CONTEXT.md`, `.planning/ROADMAP.md`, `CLAUDE.md`, `docs/DECISIONS.md`

### Measurement scripts (reproducible)

Four AST scripts written to the session scratchpad: composition pass, duplication pass, block
pass, per-file aggregation. Methods described in §1 Method; results in §1.3 and §3. Any planner
task disputing a number should re-run rather than re-estimate.

### Secondary / Tertiary

None. No WebSearch, Context7, or external documentation was needed or used — the domain is this
repository.

## Metadata

**Confidence breakdown:**

- **Measured baseline (§1): HIGH** — AST measurement, reproducible, method stated. The one caveat
  is category boundaries (what counts as "mechanical"), which are defined explicitly in §Method
  so a re-measurement is comparable.
- **The declarative seam (§2): HIGH** — file read end to end; the "no class-id registry exists"
  finding is a verified negative (I looked for the structure and it is not in the module).
- **Marshalling inventory (§3): HIGH** — AST call-site enumeration with file:line for every entry.
  A1 (Pydantic coercion) is the one assumption inside it.
- **Wiring (§4): HIGH** — every claim carries a file:line and most carry the source's own
  docstring rationale.
- **Governance line (§5): HIGH for the analysis, MEDIUM for completeness** — I enumerated the
  invariants CLAUDE.md names and checked each. A CI-invariant I did not think to check would not
  appear here; the §7.1 lint enumeration is the mitigation.
- **Surface inventory (§6): MEDIUM** — "certain" rows follow from locked decisions; "likely" rows
  are my inference and are marked as such.
- **CI blast radius (§7): HIGH** — lints, Makefile, and test collection all verified by execution.
- **Sequencing (§9): MEDIUM** — a judgment informed by the measurements, not a measurement.
- **Requirement set (§10): MEDIUM** — a proposal; sizes are estimates the planner should revise.

**Research date:** 2026-08-03
**Valid until:** until the next commit touching `src/ccf/controlplane/`, `src/ccf/boot.py`,
`src/ccf/operators/`, or `examples/`. Every number here is a measurement of a specific tree state
and goes stale the moment that tree changes.
