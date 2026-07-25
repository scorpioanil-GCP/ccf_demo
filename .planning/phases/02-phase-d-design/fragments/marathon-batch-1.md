# Decision Marathon — Batch 1 Briefs (Fabric and Runtime Fundamentals)

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

Scope: D-IMPL-01, 02, 03, 04, 05, 07, 08, 09 (CLAUDE.md §12 canonical text) plus fabric-related ambiguity entries D-IMPL-33, 34, 35, 37, 38, 39, 40, 41 (docs/DECISIONS.md canonical text). Presentation per locked D-02: recommendation first with rationale, then alternatives with consequences. Dave is the sole decision authority (CLAUDE.md §2); nothing here is a ruling. Homecams observations are triangulation data points, never defaults (CLAUDE.md §2.1).

Cross-dependency map (ordering rationale): **D-IMPL-01 is ruled first** — 02, 03, 07, 09, and especially 41 depend on the language target. D-IMPL-34 interacts with 02 (graph-storage Protocol requirement surface presumes the Protocol posture 02 sets). D-IMPL-38/39/40 share one recurring resolution shape (mechanism in SDK, values in Control Plane) and are grouped late in the batch.

---

## D-IMPL-01 — Language target

**Origin:** CLAUDE.md §12 (fabric and core). Gates: D-IMPL-41 (build-time single-writer enforcement substrate), all signature-level recommendations downstream, and the entire Phase D contract-level design (locked D-07 requires Protocol/type signatures).

**Recommendation: Python 3.12+ as the sole v0 target, with typed contracts (Pydantic v2 `extra=forbid`) and Protocol-based seams; no TypeScript port in v0.**

Rationale:
- The whitepaper's mechanism commitments are already expressed in Python-native idioms: structural-typing Protocol dispatch for Π — `required_operators()` + `invoke()` (INV-CH7-12, §7.2/§7.5); `extra=forbid` typed bases with per-product versioned payload subclasses (INV-CH7-13, §7.2; CLAUDE.md §5 names "Pydantic models with `extra=forbid`" explicitly in §11); tenant scoping via keyword-only `execute(*, tenant_id=...)` (INV-CH7-73, §7.8.4(e)) — a Python-specific signature form the whitepaper itself uses.
- CLAUDE.md §11 ("Typed contracts at every boundary") already presumes "Pydantic models … in Python, equivalents in other languages *if scoped*" — Python is the document's own default posture.
- The agent-harness ecosystem the SDK must adapt to (Google ADK, Claude Agent SDK, LangGraph — CLAUDE.md §7.3, D-IMPL-24) is Python-first; reference adapters and example 03 are cheapest and most credible in Python.
- Single-language v0 keeps the eight-example suite (§9), CI invariant lints (No-Hardcoding, `@algorithmic`, harness-import) and the composition-preservation test harness (INV-CH7-23) to one toolchain.
- Consequence to accept openly: Python cannot deliver literal compile-time prevention for single-writer (INV-CH7-73's "prevented by the type system at build time") — see D-IMPL-41 for the compensating enforcement stack.

**Alternative A — Python + TypeScript dual target.** Consequence: every typed contract, validation gate, and CI lint is authored and proven twice; v0 surface roughly doubles with no additional whitepaper fidelity; example suite and replay determinism must be proven per language. Defensible post-v0 if a TS consumer demand materializes; the MCP/A2A seams already give non-Python consumers wire-level access without a port.

**Alternative B — Language-agnostic protocol spec + one reference impl.** Consequence: elevates the wire contracts (Context Product schema, A2A, MCP resources) to the primary deliverable with Python as "merely" reference. Attractive for the §7.2 federation story, but v0 effort shifts from working SDK to spec authoring, and the whitepaper's in-process contracts (operator algebra, DI-at-boot single-writer) do not reduce to wire specs. Higher risk to the §9 adoption contract.

**Alternative C — TypeScript-first.** Consequence: stronger structural build-time typing helps D-IMPL-41, but abandons the Python-native idioms the whitepaper itself commits (kw-only tenant argument, Pydantic-style forbid-extra) and the Python-first harness ecosystem; §11's stated posture would need amendment.

---

## D-IMPL-02 — Graph storage substrate

**Origin:** CLAUDE.md §12. Interacts with D-IMPL-34 (Protocol requirement surface — what the Protocol demands of a backend is 34's question; whether there is a Protocol at all is this one's).

**Recommendation: GraphStore Protocol + reference Postgres implementation + SQLite-for-dev implementation** (the option CLAUDE.md §12 itself marks "recommended", and the posture §13 already lists in scope: "reference Postgres + SQLite backends").

Rationale:
- CLAUDE.md §11 ("Prefer Protocols over inheritance"; "Reference implementations ship alongside Protocols") makes a storage Protocol the structurally consistent choice.
- The whitepaper's storage commitments are substrate-neutral properties, not vendor features: compound unique index on `(tenant_id, entity_uri)` with persistence-tier uniqueness (INV-CH7-16, §7.3.2); idempotent upsert with set-union lineage accumulation (INV-CH7-17, §7.3.2); logical supersession with `superseded_by`/`superseded_at` (INV-CH7-21, §7.3.5); append-only-forward (INV-CH7-04, §7.1). Postgres and SQLite can both honor all four; the Protocol carries them as required semantics (see D-IMPL-34).
- SQLite-for-dev is load-bearing for the §9 examples discipline ("runnable end-to-end against the reference backends (SQLite-for-dev graph store …)") — the examples suite as specified assumes it.
- A single mandated backend is the cautionary contrast the inventory's persistence appendix flags: a mandated system-of-record is marked do-not-inherit — a data point (not a default) against single-backend postures generally.

**Alternative A — Postgres only.** Consequence: simpler v0 (one dialect, one migration story) but breaks the §9 zero-infra quickstart, contradicts §13's stated scope line, and hard-binds the fabric to one substrate in exactly the way the SDK's own Protocol principle prohibits.

**Alternative B — Protocol + SQLite only (defer Postgres).** Consequence: fastest v0; but no production-credible reference backend at launch weakens adoptability (success condition 4) and postpones proving that the Protocol's required semantics (§7.3.2 uniqueness at the persistence tier) hold under a concurrent server-grade store.

---

## D-IMPL-03 — Vector substrate

**Origin:** CLAUDE.md §12.

**Recommendation: SimilarityIndex Protocol + reference implementation on sqlite-vec (dev default) with Chroma as a second reference impl if budget allows** — the CLAUDE.md §12 "recommended" option.

Rationale:
- The Similarity operator's determinism contract is what the substrate must serve: "same corpus version, same embedding model version, same query, same threshold, same policy regime → same result", with the index version pinned in L (INV-CH7-27, §7.4.7). That contract requires the Protocol to expose corpus/index versioning and version pinning as first-class — vendor-neutral requirements, so a Protocol is the natural carrier.
- Policy-before-Similarity ordering (INV-CH7-26, §7.4.5) means the index is always queried over a policy-projected corpus; the Protocol must support corpus scoping. Again substrate-neutral.
- sqlite-vec pairs with the SQLite-for-dev graph store (D-IMPL-02) to keep the §9 quickstart at zero infrastructure.

**Alternative A — Single vendor (e.g., Chroma only).** Consequence: less v0 work, but adds a required service to the quickstart and binds the determinism contract's proof to one vendor's versioning semantics.

**Alternative B — Protocol only, no reference impl in v0.** Consequence: violates CLAUDE.md §11 ("Reference implementations ship alongside Protocols") and leaves the Similarity operator category — one of the four canonical categories (INV-CH7-22) — undemonstrable in the examples suite.

---

## D-IMPL-04 — Runtime topology for v0

**Origin:** CLAUDE.md §12. Topology itself is confirmed ("library **and** runtime"); two sub-decisions remain: (a) packaging, (b) sync/async posture for the agent host loop.

**Recommendation: (a) single distribution with two packages (`ccf` library + `ccf-runtime`) in the monorepo, installable separately; (b) async-first runtime with sync facades on the library's read/serve paths.**

Rationale:
- (a) The seam is already architectural: `/src` (fabric, archetypes, operators — zero harness imports, CI-enforced) vs `/runtime` (agent host, adapters, MCP, A2A, HTTP, CLI) per CLAUDE.md §7.3/§14. Publishing the two roots as two packages makes the harness-neutrality lint boundary a packaging boundary too — the import lint (INV-CH7-73-style CI posture; CLAUDE.md §11) gains a structural backstop. Monorepo (D-IMPL-10, provisionally resolved) already accommodates this.
- (b) The runtime's obligations are inherently concurrent: MCP server + client roles (CLAUDE.md §7.1), A2A endpoints (§7.2), suspended workflows and HITL gates (§8.1–8.2), long-running monitoring triggers (INV-CH8 monitoring archetype). Async-first is the only posture that serves those without thread-pool contortion. The library's operator/projection path is read-only-sync by whitepaper contract ("side-effect-free-read-only-sync", INV-CH7-22, §7.4) — so the fabric core stays sync-callable, and the async posture lives where the concurrency lives. A sync/async split at a process or component boundary is also a Homecams data point (not a default) for D-IMPL-04(b).

**Alternative A — one package, one binary.** Consequence: simplest install; but the library/runtime seam becomes convention-only, and a fabric-only consumer (e.g., embedding L1–L6 in an existing service) drags in MCP/A2A/HTTP dependencies.

**Alternative B — sync-only v0.** Consequence: simpler mental model; but suspendable workflows (§8.1 "suspend on a HITL gate … and resume later") and the bidirectional MCP surface become blocking or thread-based, an architecture v0 would then have to unwind.

**Alternative C — fully async including library surface.** Consequence: uniform, but forces async onto the operator algebra whose whitepaper contract is read-only-*sync* (INV-CH7-22), and complicates the composition-preservation test harness for no fidelity gain.

---

## D-IMPL-05 — Tenancy model

**Origin:** CLAUDE.md §12.

**Recommendation: multi-tenant with `tenant_id` first-class throughout — single-tenant is the degenerate case (one fixed tenant id), not a separate mode.**

Rationale:
- The whitepaper makes tenancy structural, not optional: compound unique index on `(tenant_id, entity_uri)` with "no code path in the fabric that resolves an entity without a tenant scope" (INV-CH7-16, §7.3.2), and tenant scoping as one of the five CI-tested plane-boundary invariants via kw-only `tenant_id` on `execute()` (INV-CH7-73, §7.8.4(e)). A "single-tenant mode" that drops tenant_id would fork every one of those signatures and create the exact conditional code path §7.3.2 prohibits.
- The product cache key includes tenant (INV-CH7-52, §7.6.4: composite identity "tenant, schema name, ProjectionPlan identifier, graph snapshot identifier, principal binding") — tenancy is load-bearing in delivery, not just storage.
- A tenant-scoped repository/base layer making tenant filtering structural rather than conventional is a Homecams data point (not a default) for D-IMPL-05, consistent with this posture.
- Single-tenant deployments configure one tenant and never think about it again; the mechanism cost of always-on tenancy is one required argument.

**Alternative A — single-tenant per process.** Consequence: simpler signatures, but violates INV-CH7-16's no-untenanted-path invariant the moment a second tenant appears, and multi-tenancy becomes a breaking retrofit across every persistence key and cache key.

**Alternative B — both modes via configuration.** Consequence: doubles the signature surface and creates the conditional resolution path the whitepaper structurally excludes; the "both" option is strictly dominated by first-class tenancy with a default tenant.

---

## D-IMPL-07 — Embedding model abstraction

**Origin:** CLAUDE.md §12.

**Recommendation: `EmbedderProtocol` with reference adapters (one API-based, one local/deterministic for tests), model identity + version exposed as part of the Protocol contract.**

Rationale:
- The Similarity determinism contract pins "same embedding model version" as a determinism input and requires the index version in L (INV-CH7-27, §7.4.7). Whatever embeds must therefore report a stable `(model_id, model_version)` identity — that is a Protocol obligation, not a vendor feature, so the abstraction earns its keep on fidelity grounds, not just pluggability.
- Replay (INV-CH7-31, §7.4.7 determinism tuple; §7.10) needs a deterministic embedder available in CI to make similarity-including compositions bit-for-bit reproducible in the test harness — a second (local) reference impl is thus test-strategy infrastructure, not gold-plating.
- A Protocol + factory registration shape for pluggable inference components is a Homecams data point (not a default) for D-IMPL-07.

**Alternative A — one hosted model, no abstraction.** Consequence: less code; but bakes a vendor into the fabric core (against CLAUDE.md §11) and makes CI replay tests network-dependent and nondeterministic across vendor model updates.

**Alternative B — defer embeddings entirely (Similarity optional in v0).** Consequence: shrinks v0; but Similarity is one of the four canonical operator categories (INV-CH7-22) and §13 lists the full operator algebra in scope — deferral is a whitepaper-fidelity defect, not a scope choice.

---

## D-IMPL-08 — Unstructured pipeline (Pattern 5) pluggability

**Origin:** CLAUDE.md §12.

**Recommendation: each stage as a Protocol (chunking/extraction/anchoring as pluggable stages) with one opinionated reference pipeline wired from the reference implementations.**

Rationale:
- The non-negotiable mechanism is the output contract, not the pipeline internals: extraction at ingestion time (not retrieval time), typed nodes/edges into E and R, and passage-level L anchors `{document, page, paragraph, offset_span}` / `{transcript_id, timestamp, text_span}` (INV-CH7-19, §7.3.3). Stage Protocols let users substitute extractors while the SDK enforces the contract every stage output must satisfy.
- The Alternating Derivation Pipeline (INV-CH8-12, §8.4) shows the same stages recombined per archetype (Mode 1 omits semantic stages; Mode 3 expands Perception) — a fixed monolithic pipeline could not express the mode variance the whitepaper itself walks.
- The Algorithmic ⇄ Semantic Alternation invariant (§7.6.6; CLAUDE.md §11 `@algorithmic` lint) is enforceable per stage when stages are typed units: perception stages tag `@algorithmic`, comprehension/synthesis stages are the sanctioned LLM touchpoints.
- Reference pipeline included per CLAUDE.md §11 (Protocols ship with reference impls) so example suites and Pattern 5 ingress work out of the box.

**Alternative A — one opinionated pipeline, no stage Protocols.** Consequence: simpler v0 and easier to test; but users with existing document-AI investments must fork rather than plug, and mode variance (INV-CH8-12) gets expressed as flags inside a monolith.

**Alternative B — Protocols only, no reference pipeline.** Consequence: violates the reference-impl principle; Pattern 5 and examples involving documents become non-runnable.

---

## D-IMPL-09 — LLM access for semantic stages

**Origin:** CLAUDE.md §12.

**Recommendation: `LLMClientProtocol` with a first-class Anthropic reference adapter that carries the §7.10.3 Citations capability; the Protocol requires model-version reporting and supports citation-bearing responses as an optional capability surface.**

Rationale:
- Replay dimension 3 (Model Version Record, §7.10.1; CLAUDE.md §5) makes model identity/version capture at call time a structural obligation — that belongs in the client contract regardless of vendor, which argues for a Protocol whose contract includes version reporting.
- Passage-anchored citation generation (§7.10.3; INV-CH8-12's Synthesis stage "Citations pinning every claim to a source passage") is best served today by the Anthropic Citations API — hence the Anthropic adapter is the reference and the capability is modeled in the Protocol (capability-flagged, since other vendors lack it; D-IMPL-46 will later own the passage-citation provider Protocol shape specifically).
- The `@algorithmic` lint (CLAUDE.md §11) needs a single import surface to police: one Protocol module gives the lint a crisp target ("no import of the LLM client Protocol or adapters in `@algorithmic` modules").
- A provider-agnostic LLM access layer with per-context provider overrides is a Homecams data point (not a default) for D-IMPL-09.

**Alternative A — direct Anthropic SDK, no Protocol.** Consequence: simplest and gets Citations natively; but hard-binds a vendor into semantic stages, contradicting the Protocol posture, and makes CI semantic-stage tests require Anthropic access.

**Alternative B — adopt an existing multi-vendor router library as the abstraction.** Consequence: broad vendor coverage for free; but imports a large third-party dependency into the semantic path, its abstraction (not ours) then defines what the replay record can capture, and citation support is lowest-common-denominator.

---

## D-IMPL-33 — Canonical L1 event envelope schema

**Origin:** docs/DECISIONS.md; whitepaper §7.1 (INV-CH7-02).

**Recommendation: commit a typed `SignalEnvelope` contract with exactly the whitepaper-enumerated core — `source` (structured source identity, not a bare string), `ingestion_timestamp`, `observed_time: optional`, `raw_payload` (typed as opaque-to-L1) — plus `tenant_id`, an SDK-assigned `envelope_id`, and an open `source_metadata` extension carried opaquely; `extra=forbid` on the envelope itself.**

Rationale:
- The whitepaper enumerates the fields in prose but gives no schema (INV-CH7-02, §7.1: `{source, ingestion_timestamp, observed_time?, raw_payload}`); the SDK must commit one, and the minimal-superset above adds only what other invariants force: `tenant_id` because no fabric path is untenanted (INV-CH7-16), and a stable envelope id because L must trace products back to contributing signals (INV-CH7-14 L axis; §7.10).
- "L1 does not interpret" (INV-CH7-02 invariant) is honored by typing `raw_payload` as opaque at L1 — typing of content happens at L2, preserving the layer boundary. Structured and unstructured payloads ride the same envelope ("neither is privileged at the ingestion boundary").
- Per-source adapters normalizing heterogeneous sources into one envelope contract is a Homecams data point (not a default) for D-IMPL-33.

**Alternative A — envelope as Protocol (duck-typed), not a concrete schema.** Consequence: maximal source flexibility, but L1→L2 handoff loses the single validated contract, and the bidirectional MCP ingress (CLAUDE.md §7.1) has no fixed shape to normalize into.

**Alternative B — minimal four-field envelope exactly as the prose enumerates, nothing more.** Consequence: purest fidelity reading; but tenancy and signal identity then get bolted on at L2, weakening lineage anchoring (a product's L could not name its contributing envelope without an id) and re-opening the untenanted-path issue.

---

## D-IMPL-34 — Graph-storage Protocol requirement surface

**Origin:** docs/DECISIONS.md; whitepaper §7.3.1 (INV-CH7-15). Interacts with D-IMPL-02 (assumes the Protocol posture recommended there). The reference collection layout is explicitly not inherited.

**Recommendation: the Protocol requires the whitepaper's invariant semantics and leaves all physical layout backend-internal. Required of every backend: (1) compound uniqueness on `(tenant_id, entity_uri)` enforced at the persistence tier (INV-CH7-16); (2) idempotent entity upsert with set-union lineage accumulation carrying per-source `{timestamp, passage_anchor?}` (INV-CH7-17); (3) logical supersession — prior claim retained with `superseded_by`/`superseded_at`, as-of reads over both (INV-CH7-21); (4) append-only-forward discipline / no physical overwrite of superseded state (INV-CH7-04); (5) per-relationship-type lineage on edges (INV-CH7-20 mechanism note); (6) bitemporal read support (valid-time vs observed-time as-of queries, INV-CH7-14 T axis). Backend-internal: collection/table decomposition ("~10 collections" is reference grounding, not normative — INV-CH7-15), index implementation strategy, physical partitioning.**

Rationale:
- This is exactly the mechanism/values line applied to storage: the six requirements are each a named whitepaper invariant that would break replay or lineage if a backend skipped them; everything else is substrate freedom. A backend that satisfies the six is conformant by construction — testable via a Protocol conformance test suite both reference impls (D-IMPL-02) must pass.
- Write-handle asymmetry (only L2 obtains a writer — INV-CH7-10, §7.2) is enforced at the DI/composition layer above the Protocol, not inside it; the Protocol exposes separate read and write interfaces so D-IMPL-41's enforcement stack has a seam to grip.

**Alternative A — thicker Protocol that also standardizes the logical collection model (entities/edges/lineage/supersession as named stores).** Consequence: easier to write backends by recipe, harder to map onto genuinely different substrates (a native graph DB would fight the imposed relational shape).

**Alternative B — thinner Protocol (CRUD + uniqueness only), invariants enforced in SDK code above the storage layer.** Consequence: simplest backend authoring; but persistence-tier uniqueness (INV-CH7-16 explicitly places enforcement at the persistence tier, "not the application layer") and durable supersession semantics cannot be guaranteed from above — a fidelity defect.

---

## D-IMPL-35 — Entity Resolver contract

**Origin:** docs/DECISIONS.md; whitepaper §7.3.5 (INV-CH7-21).

**Recommendation: SDK ships the resolution *mechanism* — an `EntityResolutionStrategy` Protocol (candidate correlation over declared identity attributes → canonical tenant-scoped URI per INV-CH7-18's `entity-class://` convention, with set-union lineage accumulation on merge) plus a reference deterministic attribute-correlation strategy driven by user-declared ontology config (which attributes identify which entity class, with precedence). Correlation attribute sets, precedence rules, and any probabilistic matching are user configuration/plugins, never SDK values.**

Rationale:
- The whitepaper's worked mechanics are domain-flavored ("the LEI where one exists, registered address … where it does not" — INV-CH7-21, §7.3.5); the general-purpose commitment is the *shape*: fragmented native identifiers converge to one canonical E node under a tenant-scoped URI, with unstructured claims participating as first-class and L accumulating set-union across source classes. That shape is mechanism the SDK must own; the attribute lists are exactly the kind of values §13 puts out of SDK scope.
- A pluggable strategy Protocol keeps the door open for ML/probabilistic resolvers without the SDK shipping one (semantic resolution beyond deterministic correlation would also cross the Algorithmic ⇄ Semantic boundary and needs the sanctioned semantic-stage path, not the L2 algorithmic path).
- Reference impl included per CLAUDE.md §11.

**Alternative A — Protocol only, no reference strategy.** Consequence: no example can ingest multi-source entities out of the box; violates the reference-impl principle.

**Alternative B — shipped opinionated resolver with built-in common identifier handling (LEI, email, etc.).** Consequence: convenient, but ships domain identifier knowledge in `/src` — mechanism/values violation of the kind CLAUDE.md §1 names a defect.

---

## D-IMPL-37 — Operator registry population surface

**Origin:** docs/DECISIONS.md; whitepaper §7.4.2 (INV-CH7-29).

**Recommendation: explicit boot-time registration API as the single mechanism — a `register(operator_key, operator)` surface invoked during fabric construction (composition root), with fail-fast duplicate-key error at boot exactly per INV-CH7-29; Control Plane configuration declares *which* registered operators are permitted/parameterized, but code registers them. No import-time side-effect registration, no entry-point magic in v0.**

Rationale:
- INV-CH7-29 (§7.4.2) commits "import-time / boot-time loaded" with duplicate registration as a boot failure that "prevents the fabric from serving any traffic". An explicit registration call at the composition root gives that invariant a single enforcement point, keeps registration deterministic and testable (the Planner's determinism at INV-CH7-28 leans on a deterministic registry), and avoids import-order-dependent side effects that make boot failures irreproducible.
- Operators are code (mechanism), so registration-in-code does not violate the No-Hardcoding Rule; which operators a deployment *enables* and their thresholds are Control Plane artifacts (D-IMPL-38) — the same code/config split as the rest of the fabric.
- Python entry points (given D-IMPL-01 recommendation) remain a possible post-v0 convenience layered on the same API.

**Alternative A — packaging entry points (auto-discovery).** Consequence: plugin-style UX; but registration becomes environment-dependent (what's installed) rather than declared, and duplicate detection depends on import order — weaker fail-fast semantics.

**Alternative B — config-driven registration (Control Plane names dotted paths to load).** Consequence: attractive symmetry with the No-Hardcoding Rule, but it puts code loading under data control (an artifact that causes arbitrary import/execution), a trust-posture problem at the A2A/artifact boundary; better to keep code registration in code and permissioning in config.

---

## D-IMPL-38 — Control Plane parameter schema for operator thresholds

**Origin:** docs/DECISIONS.md; whitepaper §7.4.3/§7.4.6, §8.4 (INV-CH7-24, INV-CH8-12).

**Recommendation: a typed, versioned `OperatorParameterSet` Control Plane artifact class: each operator declares its parameter schema (names, types, bounds, required/optional — no SDK-side default *values* for domain thresholds); the Control Plane stores per-deployment parameter bundles validated against those declared schemas, semver-versioned like other Control Plane artifacts, with the in-force version captured in L per invocation. Missing required parameter = boot/validation failure, never a silent default.**

Rationale:
- The whitepaper repeatedly states thresholds are Control-Plane-governed contract parameters (materiality floors — INV-CH7-24 §7.4.6 "configurable floors … Control Plane configuration, not code constants"; similarity thresholds part of the contract, not runtime-tuned — INV-CH7-27; deduplication confidence threshold Control-Plane-governed — INV-CH8-12 §8.4) but gives no schema. "Operator declares schema, Control Plane supplies values" is the minimal structure that satisfies the No-Hardcoding Rule (CLAUDE.md §6.4) while keeping validation typed at the boundary (CLAUDE.md §11).
- No-silent-defaults follows from the Review Appendix finding that every numeric in the whitepaper (0.85/0.75 etc.) is illustrative, never an SDK default — a defaulting rule that baked those in would be a fidelity defect.
- Version capture in L is what makes replay resolve the exact thresholds in force (INV-CH7-27 replay contract; §7.10 dimension 2).

**Alternative A — free-form config maps (dict-shaped), validated by each operator at runtime.** Consequence: least machinery; but validation scatters, drift between operators is invisible, and the replay record captures blobs rather than typed versioned artifacts.

**Alternative B — global threshold registry with SDK-shipped defaults marked "illustrative".** Consequence: friendlier onboarding, but shipped defaults *will* run in production unexamined — precisely the mechanism/values breach the No-Hardcoding Rule exists to prevent.

---

## D-IMPL-39 — MAX_TTL configuration locus

**Origin:** docs/DECISIONS.md; whitepaper §7.6.1/§7.6.4 (INV-CH7-48).

**Recommendation: reading (a) — MAX_TTL is Control Plane configuration per Context Product class, required (no SDK default), validated at gate 3 (`now < expires_at ≤ now + MAX_TTL`, INV-CH7-48) and re-verified at cache-write time; the MAX_TTL version in force is part of the policy-bindings replay dimension.**

Rationale:
- Per-class configuration is the only reading consistent with §7.8's configuration posture (INV-CH7-48's own entry says as much) and with the materialization machinery, which is already per-product-class (materialization policy per class — INV-CH7-51 §7.6.3; per-class cost bands — INV-CH7-52). A fabric-wide constant would force one envelope across products whose freshness regimes differ by orders of magnitude, and a hard-coded value collides with the mechanism/values boundary.
- Requiring the value (no default) follows the D-IMPL-38 no-silent-defaults posture; a product class without a declared MAX_TTL fails Control Plane validation at registration, not at serve time.

**Alternative A (reading b) — single fabric-wide constant.** Consequence: trivial to implement; violates No-Hardcoding and per-product independence (INV-CH7-49's independent evolution lanes imply per-class envelopes).

**Alternative B (reading c) — derive MAX_TTL from the product's λ_c band.** Consequence: elegant coupling of TTL to decay physics, but nowhere stated in the whitepaper — adopting it would be invention; at most a *validation lint* (warn when MAX_TTL wildly exceeds the λ_c window) could encode the intuition without making derivation normative.

---

## D-IMPL-40 — CAR threat-level scale and class-specific D_c thresholds

**Origin:** docs/DECISIONS.md; whitepaper §7.7.7 (INV-CH7-65).

**Recommendation: reading (a) — both the threat-level scale and the class-specific D_c thresholds are Control Plane configuration per decision class; the SDK ships only the routing mechanism: the four-state CAR predicate chain verbatim (Skip / Conditional / Standard LLM / Forced LLM, INV-CH7-65) over a user-declared ordered threat-level enum and per-class threshold values, all versioned Control Plane artifacts captured in replay. The SDK defines the *shape* (an ordered scale with a designated LOW-or-below band; a `D_c` threshold in [0,1] per class) but no values and no scale membership.**

Rationale:
- INV-CH7-65's own invariant line states "D_c thresholds are class-specific configuration (Control Plane, not code)"; extending the same treatment to the threat-level scale is the uniform mechanism/values split, and reading (b) — fabric-computed threat level — "would require a computation the paper never gives" (the entry's own consequence note): adopting it would be invention against §15 discipline.
- The routing mechanism itself is pure and testable: given (signal count, threat level, D_c, thresholds) the state is deterministic — it slots into the composition-preservation/replay test harness directly, and Forced-LLM's debt-aware prompting obligation (reason with the gap visible, INV-CH7-65/67) is mechanism the SDK owns.
- This resolution shape matches D-IMPL-38/39: parameters declared by mechanism, valued by Control Plane, versioned, replay-captured.

**Alternative A (reading b) — fabric-computed threat level from signal characteristics.** Consequence: removes a configuration burden but requires the SDK to invent an unspecified computation — a whitepaper-fidelity risk and a values-in-mechanism breach (what makes a signal "threatening" is domain judgment).

**Alternative B — SDK ships a default LOW/MEDIUM/HIGH/CRITICAL scale (values configurable).** Consequence: friendlier onboarding and arguably scale *names* are near-mechanism; but the band semantics ("≤ LOW skips to Conditional") become SDK-shipped policy — safer to ship the enum machinery and let users declare members, with the example suite demonstrating a scale in artifacts.

---

## D-IMPL-41 — Build-time single-writer enforcement substrate

**Origin:** docs/DECISIONS.md; whitepaper §7.8.4 (INV-CH7-73). **Depends on D-IMPL-01** — this recommendation assumes the Python ruling recommended there; if D-IMPL-01 resolves differently, this brief must be re-derived.

**Recommendation: a four-layer enforcement stack that reaches the strongest guarantee Python offers, with the residual gap explicitly documented: (1) *interface split* — `GraphReader` and `GraphWriter` are separate Protocols (per D-IMPL-34); read-path components' constructors accept only `GraphReader`; (2) *DI-at-boot* — the composition root constructs exactly one `GraphWriter` and injects it into L2/Assembly only ("the absence is a structural property of the constructor signature", INV-CH7-15/§7.8.4(a)); (3) *static gate as the build-time substrate* — strict mypy in CI rejects any non-L2 module referencing `GraphWriter` in a type position, plus an import-lint (same machinery as the `@algorithmic` and harness lints, CLAUDE.md §11) forbidding the writer module's import outside L2 and the composition root — CI failure = build failure, which is Python's honest equivalent of "prevented by the type system at build time"; (4) *runtime backstop* — the writer handle is constructed with a boot-time token only the composition root can mint, so an evasion of (1)–(3) still fails fast at runtime.**

Rationale:
- INV-CH7-73(a) (§7.8.4) commits DI-at-boot *and* type-system build-time prevention. In Python, structural typing + DI "approximates but does not equal build-time prevention" (the entry's own framing); the stack above converts the type-system claim into a CI-enforced static-analysis claim — consistent with the whitepaper's own posture that invariants are "CI-tested, not conventional" (INV-CH7-73 preamble) and with CLAUDE.md §11's structural-invariant-as-CI-lint pattern already used for three other invariants.
- The residual honesty note belongs in DESIGN.md's Invariant Preservation chapter (locked D-10): Python cannot make a determined insider's `object.__setattr__`-grade evasion impossible; the design claim is "no unforced path exists and every forced path fails CI or fails at boot" — the same claim strength the whitepaper's reference implementation actually demonstrates (DI + CI tests).
- A single sole-writer process topology is a Homecams data point (not a default) confirming the enforcement is achievable operationally; the SDK's version is in-process structural rather than process-topological, with process split remaining available to deployments via D-IMPL-04's packaging.

**Alternative A — runtime-only enforcement (DI + runtime token, no static gate).** Consequence: simpler CI; but abandons the whitepaper's build-time language entirely rather than approximating it — a weaker fidelity posture when a static gate is cheap.

**Alternative B — process-level enforcement (writer lives in a separate process; read paths physically lack the dependency).** Consequence: the strongest isolation, but forces a multi-process topology onto every deployment including the §9 SQLite quickstart — a deployment-topology mandate §13 puts out of SDK scope. Available as a deployment pattern, not the v0 mechanism.

**Alternative C — compiled extension or capability-object scheme for the writer.** Consequence: closest literal reading of "type system at build time", but adds a native-build toolchain to a pure-Python v0 for one invariant already covered by (1)–(4); disproportionate.

---

*End of batch 1 briefs. 16 decisions. Ruling session (Task 2) presents these one at a time, D-IMPL-01 first; every ruling logs to docs/DECISIONS.md immediately per locked D-01/D-04.*
