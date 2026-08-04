# Phase 15: SDK Ergonomics — The Integration Surface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-03
**Phase:** 15-sdk-ergonomics-the-integration-surface
**Areas discussed:** Artifact class ownership, The wiring entry point, Example rewrite scope, Where helpers live

---

## Artifact class ownership

### Operator parameters — SDK-owned schema or open envelope?

| Option | Description | Selected |
|--------|-------------|----------|
| Typed per shipped category | Each SDK-shipped operator category gets a registered `ArtifactClass` whose contract is its existing `*Parameters` model; custom operators keep `DeclaredArtifact` | ✓ |
| One open envelope, dispatched | Single `ccf.operator-parameters` class keyed by operator id, loader dispatches to whichever `Parameters` contract that id resolves to | |
| Stay DeclaredArtifact | No new typed classes; a loader helper marshals from an open declaration | |

**User's choice:** Requested discussion rather than selecting; agreed with the analysis afterward ("Agree with your read").
**Notes:** The argument that moved it — `PolicyFilterParameters` et al. are already `/src` code, so the SDK already fully owns those schemas; the quickstart's lines 231–295 are hand-translating YAML into a schema the SDK wrote, not a deployment declaring its own shape. The `artifacts.py` docstring's policy-bundle argument is sound for policy bundles and over-generalized when it swept operator parameter sets in beside them. Confirmed during discussion that this touches no governance boundary: operator parameters have no second independent source the fabric checks them against, unlike the `run_gates` lineage case, so D-15A does not bind.

### Naive-timestamp handling vs D-IMPL-38

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse naive, require offset | Loader raises `ArtifactLoadError` on any naive timestamp, mirroring `_reject_floats` | |
| Attach UTC at the boundary | Loader does what `_instant()` does now — naive means UTC | |
| Declared default in the artifact | Artifact declares its own timezone at document level; loader applies it | |
| String-load + `fromisoformat` *(added mid-discussion)* | Suppress PyYAML's timestamp resolver, parse via `datetime.fromisoformat` | ✓ |

**User's choice:** Requested discussion; selected the fourth option after it was introduced ("Yes agreed with string").
**Notes:** The original three options were framed on a false premise, exposed by measurement. `2026-08-03T12:00:00Z` is not an implicit timezone — `Z` is the ISO-8601 UTC designator and the author stated UTC; PyYAML's resolver drops it. So the naive datetime is a parser defect, not an authoring defect, and "refuse naive" would have rejected 100 timestamps whose authors already said what they meant. Measured evidence: 100 `Z` timestamps across 20 example YAML files, 12 already using explicit offsets (suite already inconsistent), tz-attaching helper duplicated across 13 Python files including `perf/suites/common.py` and `perf/synth/generator.py`. Accepted cost: `load_artifact`'s YAML behavior changes for existing callers.

### Fate of `ontology.yaml`'s non-fabric fields

| Option | Description | Selected |
|--------|-------------|----------|
| Split by consumer | `ccf.resolution-spec` closed-world over rules only; attribute maps move into the operator-parameters artifacts that consume them | ✓ |
| Keep one ontology artifact | Single SDK-owned `ccf.ontology` class with a named section for deployment attribute maps | |
| You decide at planning | Lock the typed resolution spec, defer the rest to research | |

**User's choice:** Split by consumer.
**Notes:** The quickstart's `ontology.yaml` mixes L2-consumed resolution rules with fields only the example's own operator wiring reads, with nothing in the artifact distinguishing them. Splitting makes closed-world validation possible for both halves.

### JSON Schema emission

| Option | Description | Selected |
|--------|-------------|----------|
| Emit + wire the examples | `ccf schema export` CLI command; example artifacts carry `$schema` headers; CI freshness gate | ✓ |
| Emit, don't wire | Ship the command, no headers in examples | |
| Docs reference only | Artifact classes appear in the Phase 14 D-11 generated schema reference and nowhere else | |

**User's choice:** Emit + wire the examples.
**Notes:** Follows Phase 14 D-12's committed-and-drift-checked OpenAPI pattern. Gives adopters validation at authoring time and Phase 16 a shipped instance to literal-include.

---

## The wiring entry point

### Entry-point shape

| Option | Description | Selected |
|--------|-------------|----------|
| Manifest → boot, one call | A `ccf.deployment-manifest` enumerates artifacts; one call loads, validates, registers, and boots, returning the handle plus resolved pins | ✓ |
| Manifest → registry, boot stays | Manifest populates the registry and returns pins; adopter writes the `boot()` call | |
| Per-shape loaders, no manifest | Loaders per artifact class the adopter composes explicitly | |

**User's choice:** Manifest → boot, one call.
**Notes:** `boot()`'s pinned `(key, version)` contract is unchanged underneath — the manifest produces the pins rather than hand-written code producing them. The friction was never `boot()`; it was the eleven lines before it.

### How the manifest names what it registers

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit enumeration only | Every artifact named with path, key, class; no globs; manifest is content-hashable; typed pin set returned | ✓ |
| Enumeration with glob sections | Explicit entries plus globbed groups for repetitive shapes | |
| Explicit, plus a manifest hash on the record | Enumeration only, and the manifest's content hash additionally recorded on the replay record | |

**User's choice:** Explicit enumeration only.
**Notes:** Load-bearing because the set of Control Plane artifacts in force is dimension 2 of the five-dimension replay record; a glob would make it a function of directory contents at boot time. The third option's idea was deferred rather than rejected — it touches whitepaper §7.10.1 and warrants its own decision.

### Operator-registry construction ordering

| Option | Description | Selected |
|--------|-------------|----------|
| Two-phase, view-aware builder | Builder takes artifacts plus a `GraphView`; ordering constraint expressed in the signature | ✓ |
| Deferred index binding | Index-backed operators bind lazily at first invocation, pulling the view from the engine | |
| Builder + explicit index handoff | Builder does parameter-only operators; adopter constructs and hands in index-backed ones | |

**User's choice:** Two-phase, view-aware builder.
**Notes:** `SimilaritySelect`'s `TokenOverlapIndex` is built from a corpus read out of the live graph at the temporal boundary (`run.py:249-256`), after boot and after ingest — so the registry cannot be a pure artifact read. Lazy binding was rejected: it would build the index inside the algorithmic path during projection execution, over a corpus determined by invocation timing rather than by a boundary the deployment named.

### Substrate declaration without a secret in the tree

| Option | Description | Selected |
|--------|-------------|----------|
| Manifest names kind, caller supplies connection | Manifest declares `backend: postgres`/`sqlite`; DSN or path passed as a call argument | ✓ |
| Manifest names kind + env var reference | Manifest names the env var holding the DSN; loader reads it | |
| Substrate stays entirely out of the manifest | Backend selection remains a `boot()` argument | |

**User's choice:** Manifest names kind, caller supplies connection.
**Notes:** `boot()` refuses to infer the substrate, so the manifest cannot stay silent; `postgres_dsn` is never persisted, so the manifest cannot carry it. Declaring the kind satisfies both. A manifest declaring `postgres` with no connection supplied must fail loudly, never fall back to SQLite.

---

## Example rewrite scope

### Where the ~85 lines of CI assertions and prints go

| Option | Description | Selected |
|--------|-------------|----------|
| Move to `tests/` | Examples become pure demonstration; a parallel test module asserts against each example's output | ✓ |
| Shared example harness | Assertions stay in the example directory behind a small shared checker | |
| Stay, markers exclude them | Leave them; Phase 16's re-cut markers fence them out of published snippets | |

**User's choice:** Move to `tests/`.
**Notes:** Also largely dissolves Phase 16's marker problem — little is left in the file that isn't the call spine. Accepted cost: "the example asserts its own behavior" stops being visible teaching material.

### Banking re-domaining scope

| Option | Description | Selected |
|--------|-------------|----------|
| 04 only, mix preserved | Re-domain example 04 to banking; leave every other example's domain alone | ✓ |
| Re-domain the Phase 16 set | Re-domain whatever the guide literal-includes (00, 04, likely 05/06) | |
| All to banking | One banking scenario across the suite | |

**User's choice:** 04 only, mix preserved.
**Notes:** Honors D-IMPL-52 (Dave, 2026-07-25), which deliberately replaced the earlier "one coherent neutral domain" rule. Anything broader would reverse that ruling and need a superseding decision rather than a phase-level choice.

### Timing and form of the criterion-1 surface audit

| Option | Description | Selected |
|--------|-------------|----------|
| Front-loaded, gates the plan set | Audit is the phase's first plan; findings determine which helpers get built | |
| Report at phase close | Build from existing evidence, write the audit as the closing record | ✓ |
| Both ends, one document | Short front-loaded inventory extended into the full audit at close | |

**User's choice:** Report at phase close.
**Notes:** Raised as a cost at the time: the helper set is then chosen without a front-loaded evidence sweep, and the quickstart is the only file this discussion measured. Mitigation carried into CONTEXT.md as an explicit research directive — the research and pattern-mapping pass must sweep all nine examples plus `examples/external/` before the helper set is fixed.

### Line-count target

| Option | Description | Selected |
|--------|-------------|----------|
| No numeric target | "Demonstrably smaller" stands; the audit reports the honest number | ✓ |
| Target the call spine (~55 lines) | Aim for roughly 100 lines — nothing but spine and Π | |

**User's choice:** No numeric target.
**Notes:** A target risks being hit by relocating lines rather than removing work — live, since the assertion decision already moves ~85 lines to `tests/`.

---

## Where helpers live

### Package location vs the algorithmic-purity constraint

| Option | Description | Selected |
|--------|-------------|----------|
| New `ccf.deployment` in `/src` | One package holding the manifest class, loaders, and builders; algorithmic-tagged, doing file I/O as `boot.py` already does | ✓ |
| Split pure/impure | Parsing/building in `/src`, path resolution and file reading in a thin `/runtime` layer | |
| Classmethods on existing types | `OperatorRegistry.from_artifacts(...)` etc., each beside the type it constructs | |

**User's choice:** New `ccf.deployment` in `/src`.
**Notes:** The stated cost was checked immediately rather than deferred: `tools/lints/algorithmic.py` enforces CINV-03 purely as "no LLM client import in an algorithmic-tagged module" and says nothing about filesystem I/O, and `boot.py` is already algorithmic-tagged while opening SQLite files. No lint change needed; the only work is documenting the reading so the next contributor doesn't re-derive it.

### Additive vs replacing

| Option | Description | Selected |
|--------|-------------|----------|
| Additive — constructors stay public | Direct constructors remain; helpers are a faster path over them | ✓ |
| Helpers become the supported path | Constructors stay importable but the documented/exampled/tested path is the helper surface | |
| Replace aggressively | Remove or privatize whatever the helpers subsume | |

**User's choice:** Additive — constructors stay public.
**Notes:** Preserves the escape hatch for exotic deployments, consistent with CLAUDE.md §11's Protocol-first posture. Flagged afterward that "nothing v0.2 breaks" is not quite absolute — the timestamp decision changes `load_artifact`'s behavior even though no surface is removed, and that belongs in the surface-change log as a behavior entry.

### Form of the surface-change record

| Option | Description | Selected |
|--------|-------------|----------|
| A phase-scoped surface-change log | One document listing added/reshaped/removed surfaces with before/after and reason | |
| Generated API diff | Diff the rendered public surface between phase start and end commits | |
| Both — generated diff, curated log | Diff guarantees completeness; log carries rationale and migration guidance | ✓ |

**User's choice:** Both — generated diff, curated log.
**Notes:** The log is written incrementally as plans land, so it can't be reconstructed wrongly at the end, and it doubles as the migration note D-15B says v0.1/v0.2 adopters get.

---

## Claude's Discretion

Every question received an explicit ruling or explicit carry. Left as planning-level detail:

- Return-type shape of the one-call entry point (what the pin-set object is named and carries), its error messages, and whether the manifest carries `tenant_id`
- Whether `ccf.deployment` is one module or several, and individual loader naming
- What `examples/external/` becomes under the helper surface — follows mechanically from the entry-point and location decisions
- Whether the CLI grows commands beyond `ccf schema export`
- `Perspective` and the product-class declaration getting typed artifact classes — carried by the same test that settled operator parameters, with Dave given the chance to object and none raised

## Deferred Ideas

- **Recording the deployment-manifest content hash on the Decision Replay record** — the strongest audit position for the manifest question, deferred because it touches whitepaper §7.10.1 replay-record shape and warrants its own decision rather than riding in on an ergonomics phase
- **Re-domaining the published example set or the whole suite to banking** — would reverse D-IMPL-52 and needs a superseding decision; only example 04 moves
- **Whether the Agent & Task Factory definition-artifact paths carry comparable marshalling burden** — surfaced at the close and not explored; in scope for this phase if the research sweep finds it in examples 01–03, but a new factory surface is not
