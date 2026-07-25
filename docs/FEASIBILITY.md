# FEASIBILITY — CCF SDK v0

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

## 1. Purpose, Method, and the Risk-Rating Rubric

This is the Phase F feasibility deliverable (FEAS-01): a per-component implementation verdict for every named design component in `docs/DESIGN.md`, per CLAUDE.md §3 (Phase F) and §3.1 (Phase F review criteria). Each component below carries exactly one **Verdict** — `strong fit`, `needs design choice`, or `out of scope for v0` — a 2–4 sentence rationale citing the DESIGN.md section that designs it and the `D-IMPL-NN` rulings it embodies, and a **Risk** note. Appendix A maps all 126 `INV-CHx-NN` inventory entries (`docs/SPEC_INVENTORY.md`) to their owning component's verdict, mirroring the DESIGN.md Appendix A traceability pattern so `/gsd-review` can check coverage mechanically.

**Decision-status baseline.** All 49 marathon rulings (D-IMPL-01..50 excluding D-IMPL-10 and D-IMPL-51 per the DECISIONS.md Decision Census note) are RESOLVED with Dave as approver (2026-07-25, D-GATE-D); D-IMPL-10 (repo shape) is resolved for v0 as monorepo — the post-v0 adapter-split remainder is non-gating. No verdict below re-litigates a ruling; where sizing pressure exists (the three-harness scope, D-IMPL-24), the analysis produces a recommendation for Dave at D-GATE-F, never a scope change.

**No per-component sizing numbers.** Per the Phase 3 locked decision D-03, component entries carry a risk/complexity note only — quantified per-component sizing on unbuilt code would be speculative. The risk ratings feed the `docs/ROADMAP.md` milestone breakdown.

**Risk-rating rubric (defined once; applied verbatim in every entry):**

| Rating | Definition |
|--------|------------|
| **low** | A single, well-precedented mechanism: the design commits to one Protocol or contract whose shape has direct precedent (in mainstream Python practice, in the reference-implementation ecosystem, or in the Homecams existence proof as triangulation), with no external-standard dependency. |
| **med** | A novel composition of ruled mechanisms: every constituent is individually precedented and ruled, but their composition (determinism guarantees, cross-layer invariants, conformance surfaces) is CCF-specific and must be verified empirically in Phase I. |
| **high** | An external-dependency or cross-process surface where the depended-on standard, SDK, or protocol is emergent or fast-moving (2026 state), so integration behavior can shift under the SDK during Phase I. |

**Verdict semantics.** `strong fit` — the design commits contracts, invariants, and seams sufficiently that Phase I can implement without a new design decision. `needs design choice` — feasibility analysis surfaced a genuinely new gap requiring a `D-IMPL-NN` ruling (per the Phase 3 D-02 discipline; none fired in this analysis — see §10). `out of scope for v0` — a ruled deferral appearing in the design as a named disposition, carried here so the component census is complete.

---

## 2. Data and Context Layer — Write Side (DESIGN.md §2A)

#### Component: Layered architecture frame and conceptual foundations

- **Verdict:** strong fit
- **Rationale:** §2A.0–§2A.1 fix the L1–L6 responsibility boundaries, the two-plane cut, and the ten Chapter-5 conceptual commitments as module boundaries plus the DI composition root — package structure per the **D-IMPL-01** and **D-IMPL-04** rulings (`ccf` library + `ccf-runtime`, sync operator path inside an async-first runtime). This is organizational commitment, not novel machinery; Phase I realizes it as package layout and boot wiring.
- **Risk:** low

#### Component: L1 Signal Layer — `SignalEnvelope` and `SignalSourceProtocol`

- **Verdict:** strong fit
- **Rationale:** §2A.2 commits a fully-shaped Pydantic v2 `extra=forbid` envelope per the **D-IMPL-33** ruling (whitepaper core plus `tenant_id`, `envelope_id`, `source_metadata`) and a single-obligation ingress Protocol; the no-interpretation invariant is realized structurally by opaque payload typing. Tenancy is structural per **D-IMPL-05**. Contract-first Pydantic modeling is thoroughly precedented.
- **Risk:** low

#### Component: L2 Context Assembly worker (four converging concerns, temporal stitching, supersession)

- **Verdict:** strong fit
- **Rationale:** §2A.3.1/§2A.3.3 design the sole `GraphWriter` holder with Protocol-seamed sub-stages: semantic resolution, bitemporal temporal stitching with logical supersession (`superseded_by`/`superseded_at` per the **D-IMPL-34** Protocol semantics), assembly-time policy binding, and operator invocation, with LLM access confined to semantic sub-stages via **D-IMPL-09**. The composition of bitemporal correctness with policy-at-assembly is CCF-specific and must be exercised hard by the per-dimension negative tests (§2A.0 obligation) — hence not low risk despite each constituent being ruled.
- **Risk:** med

#### Component: `EntityResolutionStrategy` Protocol and reference resolver

- **Verdict:** strong fit
- **Rationale:** §2A.3.2 ships mechanism only per the **D-IMPL-35** ruling: candidate correlation over user-declared identity attributes onto tenant-scoped `entity-class://` URIs with set-union lineage on merge; correlation values are user configuration, never SDK values. The reference deterministic attribute-correlation strategy is well-precedented; probabilistic matching is explicitly a user plugin.
- **Risk:** low

#### Component: Ingress pattern frame and CDC→G reference ingress (Pattern 1)

- **Verdict:** strong fit
- **Rationale:** §2A.4/§2A.4.1 commit the sidecar, non-invasive posture for all five co-deployed patterns and a `CDCSourceAdapter` normalizing Debezium-style change events into envelopes per **D-IMPL-33**, running async in `ccf-runtime` per **D-IMPL-04**(b). CDC consumption is mature infrastructure; the SDK's obligation is normalization, not transport.
- **Risk:** low

#### Component: MCP-client ingress adapter (`MCPSourceAdapter`)

- **Verdict:** strong fit
- **Rationale:** §2A.4.2 binds the shared `ccf` MCP client library to L1 per the **D-IMPL-13** five-edge role allocation, with acquisition results reaching L3 only via L2. The mechanism is a thin adapter over the client library; the risk it inherits is the MCP-ecosystem drift risk carried by the client library component (§8 below), not anything L1-specific.
- **Risk:** med

#### Component: Semantic-layer metadata import (Pattern 2)

- **Verdict:** strong fit
- **Rationale:** §2A.4.3 designs a `SemanticLayerImportAdapter` implementing `SignalSourceProtocol`, landing imported definitions as ontology-vocabulary entities the **D-IMPL-35** reference resolver correlates against; which semantic-layer product is bound is deployment configuration. Read-through import with no write-back keeps the surface small.
- **Risk:** low

#### Component: Pattern 5 unstructured ingestion pipeline (stage Protocols + reference pipeline)

- **Verdict:** strong fit
- **Rationale:** §2A.4.4 commits each of the six stages as a Protocol with one opinionated reference pipeline per the **D-IMPL-08** ruling, embedders via **D-IMPL-07**, citations via **D-IMPL-46**, and Policy-before-Similarity as retrieval-tier structure. The composition — ingestion-time extraction with passage-level L on every edge, Mode-1 purity under per-stage `@algorithmic` lint targets — is novel to CCF and spans several reference implementations, making this one of the larger fabric work items.
- **Risk:** med

#### Component: `ContextGraph` state primitive (six-tuple G)

- **Verdict:** strong fit
- **Rationale:** §2A.5.1 declares all six axes structurally on the base type with lineage accumulation and supersession-not-deletion semantics; deployments extend entity/relationship enumerations via configuration, never subclassed domain content. Rests on **D-IMPL-02** (backends) and **D-IMPL-05** (structural tenancy); Homecams provides the existence proof that the six-tuple persists tractably.
- **Risk:** med

#### Component: `GraphStore` Protocol and reference backends (Postgres + SQLite)

- **Verdict:** strong fit
- **Rationale:** §2A.5.2 requires exactly six invariant semantics of any backend per the **D-IMPL-34** ruling — compound `(tenant_id, entity_uri)` uniqueness, idempotent upsert with set-union lineage, logical supersession with as-of reads, append-only-forward, per-relationship-type edge lineage, bitemporal reads — verified by a Protocol conformance suite both **D-IMPL-02** reference implementations must pass. Bitemporal semantics on two substrates is the med driver; the conformance suite bounds it.
- **Risk:** med

#### Component: Single-writer enforcement stack (D-IMPL-41)

- **Verdict:** strong fit
- **Rationale:** §2A.5.3 realizes the four-layer stack per the **D-IMPL-41** ruling — reader/writer Protocol split (**D-IMPL-34**), one-writer DI at boot, mypy + import-lint static gate, boot-token runtime backstop — with the boundary-preserving rulings (**D-IMPL-16**, **D-IMPL-23**, **D-IMPL-25**, **D-IMPL-27**) closing every eroding path. Each layer is standard Python tooling; the honest residual claim ("no unforced path exists, and every forced path fails CI or fails at boot") is already recorded in DESIGN.md §9.
- **Risk:** low

---

## 3. Data and Context Layer — Read Side (DESIGN.md §2B)

#### Component: Operator algebra and the four canonical operator categories

- **Verdict:** strong fit
- **Rationale:** §2B.1 commits the algebra `ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity` with typed, read-only, sync operators (**D-IMPL-04**), parameterized exclusively through **D-IMPL-38** `OperatorParameterSet` artifacts. Composition-preservation `(A∘B)(G) = A(B(G))` and the function-determinism contract are properties Phase I must verify empirically for every shipped operator pair (§9 test-strategy rows, added in a later plan) — an empirical bar, not a design gap.
- **Risk:** med

#### Component: Operator Plan DAG generator (Planner), registry, and intermediate cache

- **Verdict:** strong fit
- **Rationale:** §2B.1 designs `planOperators` with dependency-correct ordering, boot-time fail-fast registration per **D-IMPL-37**, and the deterministic intermediate cache keyed on `(tenant, operator_key, parameter_set_version, input_intermediate_keys, graph_snapshot_id)` per **D-IMPL-36** — a cache hit is by construction the value replay would produce. Deterministic-DAG planning is well-precedented; the replay-coherent cache key discipline is the CCF-specific composition to verify.
- **Risk:** med

#### Component: `SimilarityIndex` Protocol and `EmbedderProtocol` (similarity substrate)

- **Verdict:** strong fit
- **Rationale:** §2B.1 commits vendor-neutral corpus/index versioning with version-pinned reads as Protocol obligations per **D-IMPL-03** (sqlite-vec dev default; Chroma second if budget allows) and `(model_id, model_version)` reporting per **D-IMPL-07**, with a local deterministic embedder as replay-test infrastructure. The INV-CH7-27 determinism tuple makes version pinning a contract, not a convention — the med driver is holding bit-for-bit determinism across index versions on real substrates.
- **Risk:** med

#### Component: Context Projection engine Π (`ProjectionPlan` structural typing)

- **Verdict:** strong fit
- **Rationale:** §2B.2 commits the structural-typing dispatch (`required_operators()` + `invoke()`), two-stage execution separating principal-agnostic operator plans from principal-conditioned projection plans, statelessness by invariant, and the deterministic selection signature `(perspective, context_product_class, selection_params)` per the **D-IMPL-49** ruling. Structural typing via Python Protocols is native to the **D-IMPL-01** substrate.
- **Risk:** med

#### Component: `ContextProductContract` and the three validation gates

- **Verdict:** strong fit
- **Rationale:** §2B.3 commits the nine-element specification per the **D-IMPL-30** ruling on the seven-field `extra=forbid` typed base, per-product independent semver lanes, the canonical gate sequence — empty-operator guard → lineage strict equality → TTL bounds — as the only construction path of a servable product, MAX_TTL as required per-class Control Plane configuration per **D-IMPL-39**, and two-granularity TTL derivation with the mixing-refusal rule per **D-IMPL-31**. Contract validation at a typed boundary is precedented; the gates are pure mechanism.
- **Risk:** low

#### Component: SLO envelope, materialization policy, and cache lifecycle

- **Verdict:** strong fit
- **Rationale:** §2B.3 designs the four-state cache lifecycle (Fresh → Near-Expiry → Invalidated/expiry → Re-Derived) with Control-Plane-owned materialization policy under **D-IMPL-38**, intermediate substrate on the hot side of the **D-IMPL-27** mutability split, and all SLO numerics as calibration envelopes, never shipped constants. Cache coherency under supersession-event invalidation is the med driver.
- **Risk:** med

#### Component: Algorithmic ⇄ Semantic Alternation, three Assembly Modes, and `LLMClientProtocol`

- **Verdict:** strong fit
- **Rationale:** §2B.3 pins the alternation invariant structurally — opaque L1 payloads plus a single crisp lint target via the **D-IMPL-09** `LLMClientProtocol` (Anthropic reference adapter with Citations capability) — and commits the three Assembly Modes with per-mode replay footprints as the ninth contract element per **D-IMPL-30**. Mode 2's four pinned primitives and Mode 3's orchestration-layer determinism are contract obligations Phase I implements mechanically.
- **Risk:** low

#### Component: Half-life λ_c machinery

- **Verdict:** strong fit
- **Rationale:** §2B.4 implements the committed decay form `R(t) = R₀ × (1/2)^((t − t₀) / λ_c)` with the sequential-window observer buffer, λ_c strictly as Control Plane configuration per observation type under the **D-IMPL-38** discipline, and supersession as a Policy event cascading through cache coherency. The math is fixed by the whitepaper; only calibration is user territory.
- **Risk:** low

#### Component: Debt machinery — `DebtFactorScorer`, `TrustScorer`, and CAR routing

- **Verdict:** strong fit
- **Rationale:** §2B.4 commits `D_c = 1 − (F·C·S)` verbatim with per-factor scorer Protocols, versioned `(scorer_id, scorer_version)` identity, and replay pinning per the **D-IMPL-47** ruling; Trust Triangle legs derive from the same components under the **D-IMPL-32** conjunctive combinator; CAR consumes user-declared threat scales and per-class thresholds per **D-IMPL-40**. Zero new measurement machinery is required — the med driver is the evolvability surface (class→scorer-version rebinding without code change) interacting correctly with replay.
- **Risk:** med

#### Component: Decision Replay record (five dimensions + SDK extensions)

- **Verdict:** strong fit
- **Rationale:** §2B.5 commits the five inviolate dimensions with the SDK extensions (HITL actions on dimension 2; agent version, skill-set, and workflow chain on dimension 4; workflow steps on dimension 5) enforced at write time across every pillar. The record format is mode-invariant per-mode-extended (INV-CH7-88), populated mechanically from artifacts already serialized under **D-IMPL-11**/**D-IMPL-28**. Cross-pillar capture completeness is the med driver — it is exactly what the CINV-04 checks exist to verify.
- **Risk:** med

#### Component: Snapshot strategy and artifact-version resolution

- **Verdict:** strong fit
- **Rationale:** §2B.5 rules out physical graph copies: logical snapshots by construction per **D-IMPL-06** (`graph_snapshot_id` = temporal boundary + tenant + watermark, plus the lineage-enumerated touched-substate manifest), hybrid content-hash + versioned-URI addressing per **D-IMPL-26** with `@latest` forbidden in replay records, and the **D-IMPL-27** mutability split. Resolution of exact versions by hash is deterministic mechanism; the med driver is watermark semantics across both graph backends.
- **Risk:** med

#### Component: Fidelity lifecycle engine and cold-archive re-hydration

- **Verdict:** strong fit
- **Rationale:** §2B.5 ships the three-tier compression lifecycle (Full / Compressed / Tombstoned) with the severity exemption and structural `retention-reason` per the **D-IMPL-50** ruling, executing above the ArtifactStore Protocol; every compressed record carries a typed `ReHydrationRecipe` whose replay re-runs L2 assembly under pinned versions and verifies bit-for-bit against the stored hash per **D-IMPL-44**, with `ColdSourceArchiveProtocol` as the pluggable archive seam. Bit-for-bit re-hydration is the strongest determinism claim in the SDK and is named as its own hash-verified test-strategy row (Phase 3 locked D-09).
- **Risk:** med

#### Component: Replay provider seams — `PassageCitationProvider` and `TraceCorrelationHook`

- **Verdict:** strong fit
- **Rationale:** §2B.5 defines both by typed output contract: passage anchors in the whitepaper's L-anchor forms with provider identity/version per the **D-IMPL-46** ruling (Anthropic Citations adapter + deterministic post-hoc span-matcher), and the external trace reference `{trace_provider, trace_id, trace_url?, capture_time}` via `ExternalTraceProviderProtocol` per **D-IMPL-45**. The vendor-facing adapter (Citations API) is the high-side ingredient, but the deterministic fallback keeps the SDK contract CI-testable without the vendor — netting med.
- **Risk:** med

#### Component: Closed-Loop Self-Learning

- **Verdict:** strong fit
- **Rationale:** §2B.6 commits the three-stage pattern (typed `OutcomeSignal` → gated Control Plane interpretation → versioned propagation) over the canonical enum taxonomy per **D-IMPL-42**, with interpretation defaulting to human-gated (ApprovalGate) per **D-IMPL-43** and exactly four Control-Plane-owned refinement targets. No gradient machinery exists anywhere in the loop; every constituent rides governance mechanism designed elsewhere in this document.
- **Risk:** low

---

## 4. Core Agent Types (DESIGN.md §3)

#### Component: `Agent` base and `ArchetypeComponent` Protocol

- **Verdict:** strong fit
- **Rationale:** §3.1 commits a single concrete final `Agent` class — the factory's only output type, carrying identity, version, composed archetypes, channel-1 record, and bound skill-set, with no reasoning loop — per the **D-IMPL-11** ruling, with archetypes as structurally-typed behavior bundles. The no-subclassing rule makes the archetype/agent separation structurally safe and dimension-4 replay capture a mechanical serialization.
- **Risk:** low

#### Component: The six archetypes (incl. swarm-realized operators and the alternating derivation pipeline)

- **Verdict:** strong fit
- **Rationale:** §3.2/§3.4 design each archetype as an `ArchetypeComponent` bundle — execution shape, fabric-interaction pattern, replay obligations, zero domain values — including the `ContextAssemblyAgent` realization of swarm-realized operators (INV-CH7-32) and the Document-Heavy Compositional binding of the alternation invariant (INV-CH8-12). Consumption discipline (no path from `Agent` to L1–L5) and trust-gated action via the **D-IMPL-32** legs are negative obligations enforced by surface absence.
- **Risk:** med

#### Component: Archetype composition

- **Verdict:** strong fit
- **Rationale:** §3.3 rules composition over mixins per **D-IMPL-19**: ordered archetype list in the artifact, dedup of identical obligations, declaration-order default resolution with factory warning, hard contradictions as construction errors. The conflict rules are explicit enough to unit-test directly.
- **Risk:** low

#### Component: Agent & Task Factory and the definition-artifact schema

- **Verdict:** strong fit
- **Rationale:** §3.5 makes the factory the only construction path (tests included, via fixture artifacts) interpreting YAML artifacts validated by Pydantic v2 with exported JSON Schema and Jinja2 prompt artifacts behind versioned URIs per the **D-IMPL-28** ruling, addressed per **D-IMPL-26**. Deterministic construction (identical definition + referenced-artifact versions → identical configuration) is what makes agent identity replayable; the No-Hardcoding Rule is realized structurally here and enforced by CINV-01.
- **Risk:** med

#### Component: Channel 1 — specialization record (six axes)

- **Verdict:** strong fit
- **Rationale:** §3.6 types all six axes as validated artifact fields (**D-IMPL-28**), with axis changes re-versioning the agent and dimension-4 capture serialized mechanically as `(agent_id, artifact_version, archetype list, six-axis record, skill-set snapshot, delegation chain)` per INV-CH7-84. This is schema work over ruled formats.
- **Risk:** low

#### Component: Channel 2 — skill catalog and skilling governance

- **Verdict:** strong fit
- **Rationale:** §3.7 commits the dynamic Control Plane catalog with four skill types per **D-IMPL-12**, two-tier governance per **D-IMPL-29** (tier-1 compatibility check always on and non-waivable; tier-2 ApprovalGate by policy), grants/revocations as separate versioned artifacts, and skill-set-in-force replay capture. The governance state machine touches the Control Plane, HITL, replay, and the adapter skill-exposure seam simultaneously — a genuinely cross-pillar composition.
- **Risk:** med

---

## 5. Orchestration Layer (DESIGN.md §4)

#### Component: Workflow primitive

- **Verdict:** strong fit
- **Rationale:** §4 designs a minimal state machine — skill/agent/HITL-gate nodes, first-class exception paths, suspend/resume on Control Plane state per **D-IMPL-18**, definitions as Task Factory artifacts per **D-IMPL-28**, debt cascade recomputed at every handoff boundary — per the **D-IMPL-17** scope ruling, explicitly not a Temporal-class engine. Replay-by-construction on every transition (dimensions 4/5) plus Mode 3 record primitives are the CCF-specific composition to verify.
- **Risk:** med

#### Component: `OrchestrationProtocol`

- **Verdict:** strong fit
- **Rationale:** §4 ships the seam to external orchestrators per **D-IMPL-17**, with identical replay obligations (a non-replay-complete engine is non-conforming, not degraded) and the LangGraph two-seam boundary stated explicitly per **D-IMPL-17**/**D-IMPL-24**. For v0 the SDK ships the Protocol and its in-SDK reference realization only — no external-engine integration is in scope, which caps the surface.
- **Risk:** low

#### Component: Swarm-level intent decomposition (named post-v0 extension)

- **Verdict:** out of scope for v0
- **Rationale:** Per the **D-IMPL-49** ruling and its explicit DESIGN.md obligation (§4), intent decomposition is an orchestration-layer concern and a NAMED post-v0 extension candidate: in v0, intent never reaches Π as free inference — it is a declared enum-valued selection parameter inside the deterministic selection signature. Nothing in the v0 Workflow primitive precludes the extension; it composes as a coordinator pattern over existing nodes. Carried in the ROADMAP.md deferral register.
- **Risk:** low

---

## 6. Human in the Loop and Control (DESIGN.md §5)

#### Component: The four HITL primitives (ApprovalGate, ExceptionEscalation, OverrideBoundary, ReviewQueue)

- **Verdict:** strong fit
- **Rationale:** §5 gives all four one structural contract — the only completion path is a typed action record carrying a `HumanPrincipalBinding` (**D-IMPL-21**) whose replay append precedes the state transition — with ExceptionEscalation realizing the fail-closed escalation pathway over **D-IMPL-40**/**D-IMPL-38** thresholds and ReviewQueue consuming the **D-IMPL-46** citation contract. Audit-by-construction is argued structurally in five steps and verified by CINV-04; no unrecorded-action path exists to close later.
- **Risk:** low

#### Component: `HITLTransportProtocol` (typed queue + reference transports)

- **Verdict:** strong fit
- **Rationale:** §5 commits the typed queue as the single ingress/egress per the **D-IMPL-20** ruling, with two reference transports: MCP endpoints (queues as Resources, actions as Tools — primary, serving example 05 and the `ccf hitl` CLI) and notify-only webhooks that structurally cannot carry authority. No inbox UI ships, per CLAUDE.md §8.2/§13.
- **Risk:** low

#### Component: HITL identity binding (`IdentityProvider` family, `HumanPrincipalBinding`)

- **Verdict:** strong fit
- **Rationale:** §5 rules the binding shape per **D-IMPL-21** — subject id + provider reference, authentication context, action time, content hash of the product seen (**D-IMPL-26**) — pluggable through the same `IdentityProvider` Protocol family as **D-IMPL-15**, with a dev authenticated-principal reference and a JWS-signed binding for non-repudiation. Enterprise OIDC/SAML integration is deployment configuration behind the Protocol, keeping the SDK-side surface bounded.
- **Risk:** med

#### Component: Supervision Quality (documented reference pattern)

- **Verdict:** out of scope for v0
- **Rationale:** Per the **D-IMPL-48** ruling, Supervision Quality ships as a documented reference pattern, not mechanism: the behavioral axes are domain values, the fusion function is calibration, and every needed primitive (L1 signals, **D-IMPL-37** user-registered operators, user-defined product class, **D-IMPL-38** thresholds, HITL escalation) already exists in this design. INV-CH8-19 maps to *deferred* in DESIGN.md Appendix A — a ruled disposition, not a coverage gap. Carried in the ROADMAP.md deferral register.
- **Risk:** low

---

## 7. Experience Layer (DESIGN.md §6)

#### Component: MCP egress server (Experience front door)

- **Verdict:** strong fit
- **Rationale:** §6.1 commits one `ccf-runtime` egress server with two resource families (L6 products; Experience access Tools, plus the **D-IMPL-20** HITL queues) per the **D-IMPL-13** role allocation, with the ArtifactStore server contract kept separate. MCP-server implementation in Python is well-supported in 2026, but the protocol surface is still evolving vendor-side — the shared MCP-ecosystem exposure nets med.
- **Risk:** med

#### Component: `ccf` CLI

- **Verdict:** strong fit
- **Rationale:** §6.2/§8.5 fix the noun-verb surface (`agent`, `skill`, `workflow`, `hitl`, `replay`, `artifact`, `product`, `config`) per the **D-IMPL-22** ruling as a thin client over the HTTP API with a `--local` dev mode; every mutating verb routes through the same factories and Control Plane actions (artifact files only, never inline definitions). Replay renderings reuse Π recursively per INV-CH7-91 rather than adding a rendering subsystem.
- **Risk:** low

#### Component: HTTP API skeleton

- **Verdict:** strong fit
- **Rationale:** §6.3 mirrors the CLI noun set with OpenAPI generated from the existing Pydantic `extra=forbid` contracts per the **D-IMPL-23** ruling — serialization, auth hooks, routing, no new semantics — and deliberately omits L1 ingestion to protect single-writer. Skeleton-scale REST over generated contracts is routine.
- **Risk:** low

#### Component: Conversational Reporting Layer (adjacency, not designed)

- **Verdict:** out of scope for v0
- **Rationale:** Per CLAUDE.md §13 and DESIGN.md §6.4, the Conversational Reporting Layer (whitepaper §8.10) is inventoried, not designed: INV-CH8-21 maps to *deferred* in DESIGN.md Appendix A. Its underlying primitives (Π, D_c gating, replay) are in scope individually; a future conversational surface is a user-built reference integration over the three front doors. Carried in the ROADMAP.md deferral register.
- **Risk:** low

---

## 8. Control Plane / Data Plane (DESIGN.md §7)

#### Component: Control Plane registry (versioned configuration + audit plane)

- **Verdict:** strong fit
- **Rationale:** §7 designs the in-process versioned registry (with remote extension point per CLAUDE.md §13) owning the six whitepaper configuration classes plus the SDK artifact classes, all under the **D-IMPL-38** declared-schema, no-silent-default discipline, with closed-loop updates entering through the **D-IMPL-43** gated path and the plane-boundary invariant register (INV-CH7-73) enforced by mechanism designed in §2A/§2B/§5. It is the audit plane by construction — every configuration change versioned and retained against the decisions made under it. As the artifact hub every other pillar depends on, sequencing pressure lands here first in Phase I.
- **Risk:** med

---

## 9. Cross-Process Seams (DESIGN.md §8)

#### Component: MCP client library (five-edge role allocation)

- **Verdict:** strong fit
- **Rationale:** §8.1 allocates MCP to exactly the five CLAUDE.md §7.1 edges per the **D-IMPL-13** ruling, with one client library serving L1 ingress and L4–L5 acquisition, packaged per **D-IMPL-04**, and client/server modules separated by trust posture. The MCP specification and Python SDK ecosystem are moving targets at 2026 state; the SDK's normalization boundary contains the drift but Phase I should pin SDK versions and wrap vendor types at the module boundary.
- **Risk:** high

#### Component: A2A federation (`WireProtocol`, `IdentityProvider` signing, admission verification)

- **Verdict:** strong fit
- **Rationale:** §8.2 commits the Linux Foundation A2A protocol as the v0 default `WireProtocol` with a plain typed-HTTP fallback per **D-IMPL-14**, two-layer identity (mTLS transport + detached-JWS product signing) per **D-IMPL-15**, and verify-every-admission at the consumer Control Plane per **D-IMPL-16**, with lineage set-union continuity across the boundary. The Context Product Contract is the stable layer and the wire is replaceable by design — but the A2A standard itself is emergent, which is precisely the high-rubric case; the fallback transport is the containment.
- **Risk:** high

#### Component: Harness adapter — Google ADK

- **Verdict:** strong fit
- **Rationale:** §8.3 binds the four `HarnessAdapterProtocol` seams to Google ADK per the **D-IMPL-24** ruling (must-have) under the **D-IMPL-25** seam-scope rules. ADK's tool interface and context surface map naturally onto skill exposure and context injection; the external-SDK dependency is the med-to-high driver. Per-harness sizing analysis: the ADK adapter is the middle of the three in expected integration complexity — a stable-enough public API, but effect-capture routing (governed emission, never a write handle) and replay-hook completeness (dimension 3/5 capture from ADK's execution trace) are integration work against a vendor SDK that revises quarterly.
- **Risk:** high

#### Component: Harness adapter — Claude Agent SDK

- **Verdict:** strong fit
- **Rationale:** §8.3 binds the same four seams to the Claude Agent SDK per **D-IMPL-24** (must-have) and **D-IMPL-25**. Per-harness sizing analysis: expected to be the most tractable of the three — the SDK's MCP-native posture means context injection and skill exposure can ride MCP surfaces the fabric already ships (a harness that speaks MCP needs no adapter for consumption; the adapter earns its keep on skill exposure, effect capture, and replay per CLAUDE.md §7.3), and the **D-IMPL-45** `TraceCorrelationHook` attaches cleanly at the replay-hooks seam. Residual exposure is vendor-SDK evolution, shared with the other two adapters.
- **Risk:** med

#### Component: Harness adapter — LangGraph

- **Verdict:** strong fit
- **Rationale:** §8.3 binds the four seams to LangGraph per Dave's own **D-IMPL-24** ruling (all three ship v0), with the **D-IMPL-17** two-seam disambiguation keeping the harness adapter strictly on the agent-loop seams and LangGraph-as-orchestrator as a distinct, optional `OrchestrationProtocol` integration. Per-harness sizing analysis: the highest-complexity adapter of the three — LangGraph's graph-of-nodes execution model has no single "agent loop" surface, so context injection and effect capture must be bound per-node-boundary, and disciplined enforcement of the two-seam boundary is itself integration work. **Recommendation for Dave at D-GATE-F (not a scope change; the ruling stands unless Dave revises it):** within milestone I.3, stage the LangGraph adapter after the ADK and Claude Agent SDK adapters have proven the conformance suite, so the hardest binding lands on a validated `HarnessAdapterProtocol` rather than co-evolving with it.
- **Risk:** high

#### Component: ArtifactStore (`ArtifactStoreProtocol` + file-backed and MCP-backed reference implementations)

- **Verdict:** strong fit
- **Rationale:** §8.4 commits the Protocol with the **D-IMPL-27** mutability split (immutable replay-relevant artifacts in; hot state out), **D-IMPL-26** hybrid addressing with append-only version→hash binding and `@latest` forbidden in replay records, never-a-second-writer trust posture, and the **D-IMPL-50** lifecycle engine executing above the Protocol so any conforming store inherits it. The file-backed dev store is straightforward; the MCP-backed reference server shares the MCP-ecosystem exposure noted for the client library.
- **Risk:** med

---

## 10. Cross-Cutting: CI Invariant Enforcement (DESIGN.md §9)

#### Component: CINV lint and check suite (CINV-01..04, composition-preservation harness, boot check)

- **Verdict:** strong fit
- **Rationale:** §9 designs all enforcement mechanically: CINV-01 prompt-shaped-literal + factory-bypass lints, CINV-02 zero-harness-imports lint hosting the single-writer static gate (**D-IMPL-41**), CINV-03 `@algorithmic` lint with the **D-IMPL-09** single import target, CINV-04 replay-by-construction assertions, plus the operator-pair property harness and the single-writer boot check. Each is standard AST/import-lint and property-test tooling; the prompt-shape heuristics of CINV-01 will need tuning against false positives, which is calibration inside a committed design, not a design gap.
- **Risk:** med

### D-02 gap check (result of this analysis)

No component analysis above surfaced a genuinely new design gap: every verdict is `strong fit` or a ruled `out of scope for v0` disposition. Accordingly, no `needs design choice` verdict was issued and no new `D-IMPL-52` entry is required from this plan. (Per the Phase 3 D-02 discipline, had a gap fired, the component would carry `needs design choice` and the entry would be appended to `docs/DECISIONS.md` in the plan that owns DECISIONS.md changes.)

### Verdict census

50 components: 47 `strong fit`, 0 `needs design choice`, 3 `out of scope for v0` (swarm-level intent decomposition per D-IMPL-49; Supervision Quality per D-IMPL-48; Conversational Reporting Layer per CLAUDE.md §13). Risk distribution: 19 low, 27 med, 4 high (MCP client library, A2A federation, Google ADK adapter, LangGraph adapter). The high ratings cluster exactly where the rubric predicts: external-dependency and cross-process surfaces with emergent 2026-state standards.

---

## Appendix A — Inventory Verdict Matrix (126/126, D-01)

Every `INV-CHx-NN` inventory entry (`docs/SPEC_INVENTORY.md`) mapped — via its DESIGN.md realizing section (per DESIGN.md Appendix A, including its see-also composite refs and the two ruled deferred statuses) — to the §2–§10 component that owns that section, carrying that component's verdict. Key set is exactly the inventory's 126-entry set (mechanically checkable: unique-key diff against the inventory is empty).

| INV key | DESIGN.md section | Owning component | Verdict |
|---------|-------------------|------------------|---------|
| INV-CH5-01 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-02 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-03 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-04 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-05 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-06 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-07 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-08 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-09 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH5-10 | §2A.0 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH6-01 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH6-02 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH6-03 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH6-04 | §2B.3 | Algorithmic ⇄ Semantic Alternation, Assembly Modes, LLMClientProtocol | strong fit |
| INV-CH6-05 | §3.1 | Agent base and ArchetypeComponent Protocol | strong fit |
| INV-CH6-06 | §6.1 | MCP egress server (Experience front door) | strong fit |
| INV-CH6-07 | §3.2 | The six archetypes | strong fit |
| INV-CH6-08 | §3.2 | The six archetypes | strong fit |
| INV-CH7-01 | §2A.1 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH7-02 | §2A.2.1 | L1 Signal Layer — SignalEnvelope and SignalSourceProtocol | strong fit |
| INV-CH7-03 | §2A.3.1 | L2 Context Assembly worker | strong fit |
| INV-CH7-04 | §2A.3.3 | L2 Context Assembly worker | strong fit |
| INV-CH7-05 | §2B.1 (see-also §2A.1) | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-06 | §2B.2 (see-also §2A.1) | Context Projection engine Π | strong fit |
| INV-CH7-07 | §2B.3 (see-also §2A.1) | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-08 | §2A.1 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH7-09 | §2A.1 | Layered architecture frame and conceptual foundations | strong fit |
| INV-CH7-10 | §2A.5.3 | Single-writer enforcement stack (D-IMPL-41) | strong fit |
| INV-CH7-11 | §2B.1 (see-also §2A.1) | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-12 | §2B.2 (see-also §2A.1) | Context Projection engine Π | strong fit |
| INV-CH7-13 | §2B.3 (see-also §2A.1) | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-14 | §2A.5.1 | ContextGraph state primitive | strong fit |
| INV-CH7-15 | §2A.5.1 | ContextGraph state primitive | strong fit |
| INV-CH7-16 | §2A.5.2 | GraphStore Protocol and reference backends | strong fit |
| INV-CH7-17 | §2A.5.2 | GraphStore Protocol and reference backends | strong fit |
| INV-CH7-18 | §2A.3.2 | EntityResolutionStrategy Protocol and reference resolver | strong fit |
| INV-CH7-19 | §2A.4.4 | Pattern 5 unstructured ingestion pipeline | strong fit |
| INV-CH7-20 | §2A.5.2 | GraphStore Protocol and reference backends | strong fit |
| INV-CH7-21 | §2A.3.2 | EntityResolutionStrategy Protocol and reference resolver | strong fit |
| INV-CH7-22 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-23 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-24 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-25 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-26 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-27 | §2B.1 | SimilarityIndex Protocol and EmbedderProtocol | strong fit |
| INV-CH7-28 | §2B.1 | Operator Plan DAG generator (Planner), registry, intermediate cache | strong fit |
| INV-CH7-29 | §2B.1 | Operator Plan DAG generator (Planner), registry, intermediate cache | strong fit |
| INV-CH7-30 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-31 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH7-32 | §3.4 | The six archetypes | strong fit |
| INV-CH7-33 | §2B.1 | Operator Plan DAG generator (Planner), registry, intermediate cache | strong fit |
| INV-CH7-40 | §2B.2 | Context Projection engine Π | strong fit |
| INV-CH7-41 | §2B.2 | Context Projection engine Π | strong fit |
| INV-CH7-42 | §2B.2 | Context Projection engine Π | strong fit |
| INV-CH7-43 | §2B.2 | Context Projection engine Π | strong fit |
| INV-CH7-44 | §2B.2 | Context Projection engine Π | strong fit |
| INV-CH7-45 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-46 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-47 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-48 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-49 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-50 | §2B.3 | SLO envelope, materialization policy, cache lifecycle | strong fit |
| INV-CH7-51 | §2B.3 | SLO envelope, materialization policy, cache lifecycle | strong fit |
| INV-CH7-52 | §2B.3 | ContextProductContract and the three validation gates | strong fit |
| INV-CH7-53 | §2B.3 | SLO envelope, materialization policy, cache lifecycle | strong fit |
| INV-CH7-54 | §2B.3 | Algorithmic ⇄ Semantic Alternation, Assembly Modes, LLMClientProtocol | strong fit |
| INV-CH7-55 | §4 | Workflow primitive | strong fit |
| INV-CH7-56 | §4 | Workflow primitive | strong fit |
| INV-CH7-57 | §2B.4 | Half-life λ_c machinery | strong fit |
| INV-CH7-58 | §2B.4 | Half-life λ_c machinery | strong fit |
| INV-CH7-59 | §2B.4 | Half-life λ_c machinery | strong fit |
| INV-CH7-60 | §2B.4 | Half-life λ_c machinery | strong fit |
| INV-CH7-61 | §2B.4 | Debt machinery — DebtFactorScorer, TrustScorer, CAR routing | strong fit |
| INV-CH7-62 | §2B.4 | Debt machinery — DebtFactorScorer, TrustScorer, CAR routing | strong fit |
| INV-CH7-63 | §2B.4 | Debt machinery — DebtFactorScorer, TrustScorer, CAR routing | strong fit |
| INV-CH7-64 | §2B.4 | Debt machinery — DebtFactorScorer, TrustScorer, CAR routing | strong fit |
| INV-CH7-65 | §5 | The four HITL primitives | strong fit |
| INV-CH7-66 | §2B.4 | Debt machinery — DebtFactorScorer, TrustScorer, CAR routing | strong fit |
| INV-CH7-67 | §5 | The four HITL primitives | strong fit |
| INV-CH7-68 | §4 | Workflow primitive | strong fit |
| INV-CH7-70 | §7 | Control Plane registry | strong fit |
| INV-CH7-71 | §7 | Control Plane registry | strong fit |
| INV-CH7-72 | §7 | Control Plane registry | strong fit |
| INV-CH7-73 | §7 | Control Plane registry | strong fit |
| INV-CH7-74 | §7 | Control Plane registry | strong fit |
| INV-CH7-75 | §2B.6 | Closed-Loop Self-Learning | strong fit |
| INV-CH7-76 | §2B.6 | Closed-Loop Self-Learning | strong fit |
| INV-CH7-77 | §2B.6 | Closed-Loop Self-Learning | strong fit |
| INV-CH7-78 | §2B.6 | Closed-Loop Self-Learning | strong fit |
| INV-CH7-79 | §2B.5 | Decision Replay record | strong fit |
| INV-CH7-80 | §2B.5 | Decision Replay record | strong fit |
| INV-CH7-81 | §2B.5 | Decision Replay record | strong fit |
| INV-CH7-82 | §5 | The four HITL primitives | strong fit |
| INV-CH7-83 | §2B.5 | Decision Replay record | strong fit |
| INV-CH7-84 | §3.6 | Channel 1 — specialization record (six axes) | strong fit |
| INV-CH7-85 | §2B.5 | Decision Replay record | strong fit |
| INV-CH7-86 | §2B.5 | Replay provider seams — PassageCitationProvider, TraceCorrelationHook | strong fit |
| INV-CH7-87 | §2B.5 | Replay provider seams — PassageCitationProvider, TraceCorrelationHook | strong fit |
| INV-CH7-88 | §4 | Workflow primitive | strong fit |
| INV-CH7-89 | §2B.5 | Fidelity lifecycle engine and cold-archive re-hydration | strong fit |
| INV-CH7-90 | §2B.5 | Decision Replay record | strong fit |
| INV-CH7-91 | §6.2 | ccf CLI | strong fit |
| INV-CH8-01 | §2A.4 | Ingress pattern frame and CDC→G reference ingress | strong fit |
| INV-CH8-02 | §2A.4 | Ingress pattern frame and CDC→G reference ingress | strong fit |
| INV-CH8-03 | §2A.4 | Ingress pattern frame and CDC→G reference ingress | strong fit |
| INV-CH8-04 | §2A.4 | Ingress pattern frame and CDC→G reference ingress | strong fit |
| INV-CH8-05 | §2A.4.1 | Ingress pattern frame and CDC→G reference ingress | strong fit |
| INV-CH8-06 | §2A.4.3 | Semantic-layer metadata import (Pattern 2) | strong fit |
| INV-CH8-07 | §6.1 | MCP egress server (Experience front door) | strong fit |
| INV-CH8-08 | §8.2 | A2A federation (WireProtocol, signing, admission) | strong fit |
| INV-CH8-09 | §2A.4.4 | Pattern 5 unstructured ingestion pipeline | strong fit |
| INV-CH8-10 | §2A.4.4 | Pattern 5 unstructured ingestion pipeline | strong fit |
| INV-CH8-11 | §2A.4 | Ingress pattern frame and CDC→G reference ingress | strong fit |
| INV-CH8-12 | §3.4 | The six archetypes | strong fit |
| INV-CH8-13 | §2A.5.1 | ContextGraph state primitive | strong fit |
| INV-CH8-14 | §2B.4 | Half-life λ_c machinery | strong fit |
| INV-CH8-15 | §2B.5 | Fidelity lifecycle engine and cold-archive re-hydration | strong fit |
| INV-CH8-16 | §5 | The four HITL primitives | strong fit |
| INV-CH8-17 | §2B.1 | Operator algebra and the four canonical categories | strong fit |
| INV-CH8-18 | §5 | The four HITL primitives | strong fit |
| INV-CH8-19 | §5 (deferred per D-IMPL-48) | Supervision Quality (documented reference pattern) | out of scope for v0 |
| INV-CH8-20 | §2B.5 | Fidelity lifecycle engine and cold-archive re-hydration | strong fit |
| INV-CH8-21 | §6.4 (deferred per CLAUDE.md §13) | Conversational Reporting Layer (adjacency, not designed) | out of scope for v0 |
| INV-CH8-22 | §3.8 | The six archetypes | strong fit |
| INV-CH8-23 | §5 | The four HITL primitives | strong fit |
| INV-CH8-24 | §6.4 | MCP egress server (Experience front door) | strong fit |

**Census:** 126 rows; 124 carry `strong fit` via their owning component; 2 carry `out of scope for v0` (INV-CH8-19 per D-IMPL-48; INV-CH8-21 per CLAUDE.md §13) — both are ruled deferral dispositions mirrored from DESIGN.md Appendix A, not coverage gaps.
