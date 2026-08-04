# Phase 15: SDK Ergonomics — The Integration Surface - Context

**Gathered:** 2026-08-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Absorb into the SDK the mechanical YAML→typed-object marshalling and boot/registry/operator
wiring that every deployment currently writes for itself, so the day-1 integration is a
fraction of today's 451-line `examples/00-quickstart/run.py` — without hiding one governance
decision from the adopter or one dimension from the replay record. Then rewrite the
eight-example suite and `examples/external/` to the streamlined surface and record every
public-surface change so Phase 16 documents the surface that exists.

**Not in this phase:** new fabric capability; Assembly Modes 2 or 3 (v0.3); the documentation
rewrite itself (Phase 16). Simplification that costs an invariant is a fidelity defect, not
simplification (CLAUDE.md §1 ranks fidelity first).

**Rulings carried in and binding (Dave, 2026-08-03, recorded in ROADMAP.md):**

- **D-15A — the abstraction line is marshalling and wiring only.** Helpers may absorb
  YAML→typed-object loading, registry population, boot wiring, and operator construction from
  artifacts. Every point where a deployment *asserts something the fabric then verifies* stays
  explicit in adopter code. The worked case: `run_gates()` takes the engine's resolved
  operators separately from the product's own lineage claim so lineage strict equality has two
  independent sources; a helper computing both from one input would make the gate tautological.
  Cases requiring a governance boundary to move are surfaced as decisions, not resolved by the
  phase.
- **D-15B — free rein on the public API, pre-1.0.** The phase may reshape, rename, collapse, or
  remove any public surface; examples and docs are rewritten to match. `v0.1.0` stays tagged as
  the historical artifact.

**The reusable discriminator, derived during this discussion:** for each candidate helper, ask
whether the thing it would compute has a *second independent source the fabric checks it
against*. If yes (lineage), the helper must not collapse them. If no (operator parameters,
resolution rules, manifest pins), it is pure marshalling and D-15A permits it.

</domain>

<decisions>
## Implementation Decisions

### Artifact class ownership

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

### The wiring entry point

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

### Example rewrite scope

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

### Where helpers live

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

### Claude's Discretion

Every question in this discussion received an explicit ruling or an explicit carry. Planning-level
detail deliberately left open:

- The exact return-type shape of the D-05 one-call entry point (what the pin set object is called
  and carries), its error messages, and whether the manifest carries `tenant_id`.
- Whether the `ccf.deployment` surface is one module or several, and the naming of individual
  loaders.
- What `examples/external/` becomes under the helper surface — follows mechanically from D-05/D-13.
- Whether the CLI grows commands beyond `ccf schema export`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and binding rulings
- `.planning/ROADMAP.md` — Phase 15 entry: goal, the measured evidence (451 lines decomposed into
  ~85 CI assertions / ~105 marshalling / ~45 projection Π / ~55 call spine), six success criteria,
  and the **D-15A** and **D-15B** rulings quoted in `<domain>` above. Also the Phase 16 entry, whose
  criteria 5 and 6 depend on this phase's output.
- `CLAUDE.md` §1 (fidelity-first priority order — simplification that costs an invariant is a
  fidelity defect), §6.4 (the No-Hardcoding Rule — code contains interpreters and factories, never
  the things interpreted; this phase's whole thesis), §9 (examples-suite discipline and the
  horizontal domain mix behind D-10), §10 (L1–L6 and the two planes), §11 (working principles —
  Protocol-first, typed contracts at every boundary, no hidden model calls).
- `docs/DECISIONS.md` — **D-IMPL-38** (no floats, no implicit timezone in artifacts — the rule D-02
  reinterprets correctly), **D-IMPL-52** (horizontal domain mix, Dave 2026-07-25 — binds D-10),
  **D-IMPL-28** (definition artifact format), **D-IMPL-26** (artifact addressing), **D-IMPL-02**
  (graph storage substrate — the SQLite/Postgres choice D-08 declares), **D-IMPL-03** (SimilarityIndex
  Protocol — `TokenOverlapIndex` is only the reference impl, relevant to D-07).

### The surfaces being reshaped
- `src/ccf/controlplane/artifacts.py` — the `ArtifactClass` / `parse_artifact` / `load_artifact`
  seam, the `DeclaredArtifact` envelope, `_reject_floats`, and the module docstring **D-01 amends**.
- `src/ccf/operators/categories.py` — the four shipped `*Parameters` contracts D-01 makes
  declaratively parseable.
- `src/ccf/boot.py` — the composition root; its pinned-pair contract is preserved unchanged under
  D-05, and its `postgres_dsn` handling is the constraint behind D-08. Also the precedent that an
  algorithmic-tagged module may do file I/O (D-13).
- `src/ccf/projection/engine.py` — `OperatorRegistry`, the target of D-07's builder.
- `src/ccf/products/gates.py` — `run_gates`, the worked case D-15A is defined against. Do not let
  any helper compute both `engine_resolved` and the product's lineage claim from one input.
- `src/ccf/assembly/worker.py` — `EntityResolutionSpec`, `EntityResolutionRule`,
  `RelationshipResolutionRule`: the shapes D-03 makes a closed-world artifact class.
- `examples/00-quickstart/run.py` — the 451-line measured baseline; lines 99–135 are the
  hand-marshalling D-01/D-02 remove, 231–295 the operator block D-07 replaces, 249–256 the corpus
  comprehension that forces the two-phase shape.
- `tools/lints/algorithmic.py` — checked during discussion; enforces CINV-03 as LLM-import-only, so
  D-13 needs no lint change. `tools/lints/no_hardcoding.py` still binds every new loader.

### Downstream and adjacent
- `.planning/phases/14-documentation-suite/14-CONTEXT.md` — **D-07/D-08** (snippet markers and the
  strict-build gate that Phase 16 re-cuts), **D-11** (generated schema reference from Pydantic
  models — D-04's artifact classes land there for free), **D-12** (committed-and-drift-checked
  OpenAPI — the exact pattern D-04's freshness gate follows).
- `.planning/phases/14-documentation-suite/14-HUMAN-UAT.md` — G-01/G-02, the gaps Phase 16 closes
  against this phase's surface.

</canonical_refs>

<code_context>
## Existing Code Insights

### Research directive (consequence of D-11)

Because the surface audit is a phase-close report rather than a front-loaded gate, **the research
and pattern-mapping pass must sweep all nine examples (`00`–`08`) plus `examples/external/` for
hand-marshalling patterns before the helper set is fixed.** The quickstart is the only file this
discussion measured. A marshalling pattern that appears in six examples but not the quickstart would
otherwise be missed entirely, and the phase would ship a helper set fitted to one example.

### Reusable assets

- **`ArtifactClass` / `parse_artifact` / `load_artifact`** (`controlplane/artifacts.py`) — the seam
  criterion 2 names explicitly. Every new artifact class reaches adopters through it; nothing new is
  invented alongside it.
- **`DeclaredArtifact`** — stays as the open envelope for deployment-authored schemas
  (custom operators, policy bundles). D-01 narrows *when* it applies, not whether.
- **`_reject_floats`** — the precedent D-02's timestamp handling is modeled on: refuse at parse
  rather than silently repair, because a repaired value has already lost the property that made it
  admissible.
- **`boot()`'s pinned `(key, version)` contract** — preserved verbatim; D-05 changes what produces
  the pins, never what `boot` requires of them.
- **`FabricHandle`** — has no writer attribute, not even private. The manifest entry point returns
  this same handle; it must not grow a write path.
- **Phase 14's drift-gate pattern** (committed artifact + CI regeneration + diff) — D-04 reuses it
  wholesale for exported JSON Schema.

### Established patterns that constrain this phase

- **Single-writer (CLAUDE.md §10, DESIGN.md §2A.5.3).** `ccf.graph._writer` is imported by `boot.py`
  and `ccf.assembly` alone, enforced by the CINV-02 import lint. No helper may widen that.
- **No-Hardcoding (§6.4).** The new loaders are interpreters — they may hold no domain value, no
  key name, no threshold. `tools/lints/no_hardcoding.py` binds them.
- **CINV-03 algorithmic tagging.** Confirmed to mean no LLM client import, not no I/O (D-13).
- **Closed-world contracts.** `CCFContract` is frozen and `extra=forbid`; D-03's split exists
  precisely so closed-world validation becomes possible where it currently cannot be.

### Integration points

- `ccf.deployment` (new) → `controlplane.artifacts` (parse), `controlplane.registry` (register),
  `boot` (compose), `projection.engine.OperatorRegistry` (build), `operators.categories` (contracts).
- `ccf schema export` → the CLI (`runtime/`, Experience Layer per §8.3) and the Phase 14 docs build.
- Examples `00`–`08` and `examples/external/` → rewritten consumers of the above; assertions relocate
  to `tests/` per D-09.

</code_context>

<specifics>
## Specific Ideas

- **The `run_gates` case is the canonical illustration of D-15A** and should be named explicitly
  wherever the abstraction line is documented: the gate takes `engine_resolved` separately from the
  product's own lineage claim so lineage strict equality has two independent sources. A helper
  computing both from one input would make the gate tautological and silently delete a whitepaper
  invariant. Use it as the worked example in the `ccf.deployment` package docstring.
- **The D-02 reframing is worth preserving in the code comment**, not just the decision log: `Z` is
  an explicit UTC designator and PyYAML's resolver drops it. Without that sentence, a future
  contributor reading "we refuse naive timestamps but accept `Z`" will read it as an inconsistency
  and try to "fix" it.
- **Amending the `artifacts.py` docstring (D-01) is itself a recorded surface change** for the D-15
  log — mkdocstrings publishes it, so Phase 16's rendered reference changes with it.

</specifics>

<deferred>
## Deferred Ideas

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
  sweep (see `<code_context>`) finds hand-marshalling in the agent/skill artifact paths of examples
  01–03, that is in scope for this phase; a *new* factory surface is not.

</deferred>

---

*Phase: 15-sdk-ergonomics-the-integration-surface*
*Context gathered: 2026-08-03*
