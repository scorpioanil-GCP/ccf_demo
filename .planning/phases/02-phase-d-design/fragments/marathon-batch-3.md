# Decision Marathon — Batch 3 Briefs (Artifact Persistence & Replay, Orchestration/HITL/Experience, Ambiguity Cluster)

**Canonical authority:** `CLAUDE.md` (revision 4). CLAUDE.md wins on any disagreement. Whitepaper citations reference `docs/CCF_Whitepaper_1-2.md` sections, never the PDF (locked D-01).

Scope: artifact persistence and replay — D-IMPL-26, 06, 27, 36, 44, 50; orchestration/HITL/experience — D-IMPL-17, 18, 20, 21, 22, 23, 43; whitepaper-ambiguity cluster — D-IMPL-30, 31, 32, 42, 47, 48. Nineteen decisions; four on the Phase I gating list (06, 17, 20, 26). Presentation per locked D-02: recommendation first with rationale, then alternatives with consequences. Dave is the sole decision authority (CLAUDE.md §2); nothing here is a ruling. Homecams observations are triangulation data points, never defaults (CLAUDE.md §2.1).

**Prior-ruling conditioning.** These briefs assume the batch-1/2 rulings now RESOLVED in docs/DECISIONS.md — above all **D-IMPL-28** (YAML artifacts + Pydantic v2 schemas + Jinja2 prompt URIs; `schema_version` + `artifact_version` with independent per-class semver lanes — D-IMPL-26 must supply the addressing those lanes hang off), **D-IMPL-24** (Dave's three-harness ruling incl. LangGraph — its orchestration-overlap consequence is explicitly "D-IMPL-17 territory"), **D-IMPL-13** (separate ArtifactStore MCP contract, never merged with egress), **D-IMPL-14** (LF A2A default wire), **D-IMPL-15** (IdentityProvider Protocol, mTLS + detached JWS — D-IMPL-21 layers on it), **D-IMPL-38/39/40** (typed versioned Control Plane parameter artifacts, no silent defaults — the mechanism-not-values resolution shape reused throughout batch 3), **D-IMPL-29** (two-tier skilling governance — the tier-2 pattern D-IMPL-43 reuses), and **D-IMPL-04/05** (ccf + ccf-runtime, multi-tenant first-class).

Ordering rationale: gating decisions first — **D-IMPL-26** (artifact addressing; interacts with 06, and both replay and the factory depend on it), **06** (snapshot management), **17** (orchestration primitive scope), **20** (HITL transport) — then 27, 36, 44, 50, 18, 21, 22, 23, 43, 30, 31, 32, 42, 47, 48. Interactions noted inline: 36/44/50 with 06/26/27 (the intermediate-cache, re-hydration, and fidelity-lifecycle mechanisms all sit on the snapshot/addressing/substrate triangle); 18 with 27 (suspended workflow state is hot-mutable, not artifact-shaped).

---

## D-IMPL-26 — Artifact addressing and versioning (GATING)

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.4. Interacts with D-IMPL-06 (snapshots are an artifact class) and D-IMPL-28 (the semver lanes need an addressing scheme to resolve against). Replay and the Agent & Task Factory both depend on it.

**Recommendation: hybrid addressing — content-addressed canonical identity plus versioned-URI naming, resolved through the Control Plane.** Concretely:

- **Canonical identity is a content hash.** Every artifact (definition artifact, prompt artifact, policy bundle, Context Product at rest, replay record, snapshot) has as its immutable identity `sha256(canonical_serialization)`. Immutability and replay determinism become verifiable properties, not conventions: replay resolves *exact* artifact versions by hash, and a tampered artifact fails its own address (CLAUDE.md §7.4 — "Replay resolves exact artifact versions, never 'latest'").
- **Human/system-facing addressing is a versioned URI**, `ccf-artifact://{tenant}/{artifact_class}/{name}@{artifact_version}` (per the D-IMPL-28 two-field version discipline), maintained as a Control Plane mapping `versioned-URI → content hash`. The mapping is append-only: a version, once bound to a hash, is never rebound. `@latest` is permitted only at authoring/Control Plane surfaces, never in a replay record or lineage entry — those store the hash (with the URI carried as annotation).
- **The MCP resource contract** for the reference artifact server (per the D-IMPL-13 separate ArtifactStore contract): artifacts exposed as MCP Resources addressable by both forms — the versioned URI for browsing/tooling, the content hash for replay resolution — with a typed metadata resource per artifact (class, schema_version, artifact_version, hash, created_at, retention-reason where applicable).

Rationale:
- Replay dimension resolution (INV-CH7-80/81) and the Mode 2/3 record fields (`full_prompt_text_or_hash` content-addressed, `orchestration_plan_id` content-addressed — INV-CH7-88, §7.10.4 verbatim field names) already presuppose content addressing in the whitepaper's own record format; the SDK aligning artifact identity with it is fidelity, not invention.
- D-IMPL-28's semver lanes need a stable naming scheme; pure content addressing has no version ordering and would break the lanes. The hybrid gives semver its home (the URI) and replay its guarantee (the hash).
- Homecams' embedded-field versioning of replay artifacts is a data point recorded against this entry at Phase R — a data point only; the hybrid scheme supersedes rather than inherits it.

**Alternative A — versioned-URI only (no content addressing).** Consequence: simplest and most readable; but immutability becomes a store-side promise the SDK cannot verify — a mutated artifact under an unchanged URI silently corrupts replay, exactly the Repudiation threat the ArtifactStore constraints (§7.4 "artifacts are immutable and versioned") exist to kill.

**Alternative B — content-addressed only (no naming layer).** Consequence: maximal integrity; but no semver lanes (D-IMPL-28 breaks), unreadable references throughout DECISIONS/DESIGN/examples, and every "give me the current policy bundle" operation needs an out-of-band index anyway — which is the naming layer, reinvented ad hoc.

---

## D-IMPL-06 — Snapshot management for replay (GATING)

**Origin:** CLAUDE.md §12; originates in whitepaper §7.10 (INV-CH7-80/81). Interacts with D-IMPL-26/27 (snapshots as artifacts) and D-IMPL-44 (re-hydration is the compressed-tier counterpart).

**Recommendation: logical snapshots by construction — a snapshot is an immutable as-of reference plus a touched-substate manifest, not a physical graph copy; materialization into the ArtifactStore happens per the fidelity tier.** Concretely:

- **The append-only graph is the snapshot substrate.** Because L3 is append-only with logical supersession and bitemporal reads (INV-CH7-04/21, the D-IMPL-34 six-semantics Protocol), the graph at time t is always reconstructible from the live store by an as-of read. Dimension 1 (Context Fabric Snapshot, INV-CH7-81) is therefore captured as `graph_snapshot_id` = (temporal boundary t, tenant, store-state watermark) plus a **touched-substate manifest** (the entity URIs, relationship ids, and lineage entries the decision actually read — already enumerated in L by lineage strict equality).
- **Full-fidelity tier materializes; later tiers reference.** Within the per-decision-class full-fidelity window (INV-CH7-89), the touched substate is additionally materialized as a content-addressed artifact in the ArtifactStore (per D-IMPL-26) so replay in that window never depends on live-store retention. At compression, the materialized substate is reduced to the deterministic hash + re-hydration recipe (D-IMPL-44's contract).
- **Similarity-index snapshots:** the index version pinned in L (INV-CH7-27) is the reference; the SDK requires the SimilarityIndex Protocol (D-IMPL-03) to support version-pinned reads, and periodic full-index snapshots are ArtifactStore artifacts on a Control-Plane-configured cadence (values, not SDK policy).

Rationale:
- "Millions of decisions each day" (INV-CH7-81 open question) makes per-decision physical graph copies economically absurd; the whitepaper's own answer is compression (§7.10.5), which only works if the snapshot is logical-first.
- The as-of read is exactly what the D-IMPL-34 Protocol already requires of every backend (bitemporal read support, supersession filtering) — the snapshot mechanism reuses committed mechanism instead of adding a parallel store.
- Materialize-then-compress matches the three-tier lifecycle (INV-CH7-89) one-for-one: full fidelity = materialized artifact; compressed = hash + recipe; tombstoned = metadata only.

**Alternative A — physical per-decision snapshots (copy the touched substate at every decision, always).** Consequence: simplest replay path (no as-of machinery on the audit path); but storage cost scales with decision volume × substate size from day one, and the whitepaper's compression tiers become damage control instead of design.

**Alternative B — periodic whole-graph snapshots only (no per-decision manifest).** Consequence: cheap and operationally familiar; but "what did the agent know?" (the first examiner question, INV-CH7-81) becomes unanswerable per decision — a whole-graph image at midnight cannot isolate the decision's touched substate, breaking SR 11-7 re-tracing as the whitepaper frames it.

---

## D-IMPL-17 — Orchestration primitive scope (GATING)

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §8.1. The D-IMPL-24 ruling explicitly routes the LangGraph-vs-Workflow-primitive overlap here.

**Recommendation: minimal in-SDK Workflow primitive plus `OrchestrationProtocol` for external orchestrators — the CLAUDE.md §12 recommended option — with the D-IMPL-24 LangGraph overlap resolved by seam discipline.** Concretely:

- **The Workflow primitive ships** with exactly the §8.1 committed properties: nodes are skill invocations, agent invocations, or HITL gates; state-machine semantics with explicit states/transitions/terminals; suspend/resume on Control Plane state (persistence locus per D-IMPL-18); exception paths as first-class transitions; harness-neutral agent nodes (definition invoked, harness resolved via adapter); workflow definitions as Control Plane artifacts through the Task Factory (No-Hardcoding, §6.4). Traces land in replay dimensions 4 and 5 by construction.
- **`OrchestrationProtocol`** is the seam to external engines (Temporal-class durable execution — CLAUDE.md §8.1/§13 explicitly out of scope to reinvent): an external orchestrator drives agent invocation, HITL gating, and trace capture through the same typed surfaces the in-SDK primitive uses, so replay obligations hold identically.
- **LangGraph disambiguation (per the D-IMPL-24 ruling's recorded consequence):** the LangGraph *harness adapter* binds only the agent-loop seams of §7.3 — what happens inside a LangGraph graph is harness-internal (CLAUDE.md §13 "not the SDK's problem"). LangGraph *as an orchestrator of CCF agents* is a distinct, optional `OrchestrationProtocol` integration. One tool, two seams, never conflated — DESIGN.md documents the boundary explicitly.

Rationale: example 05 (workflow + HITL suspend/resume) requires a working in-SDK primitive; CLAUDE.md §8.1 commits both the primitive and the Protocol; the boundary "in-fabric coordination, not enterprise-grade durable orchestration" is already drawn and this recommendation simply keeps it.

**Alternative A — Protocol only, no reference primitive.** Consequence: no reinvention risk at all; but example 05 cannot run without shipping a third-party engine dependency in the quickstart path, the HITL primitives lose their reference composition surface, and CLAUDE.md §11's "reference implementations ship alongside Protocols" is violated.

**Alternative B — fuller workflow engine (durable timers, retries policy engine, distributed execution).** Consequence: more production-usable out of the box; but it is precisely the "reinventing Temporal" CLAUDE.md §8.1 rules out of scope, and it deepens the LangGraph overlap the D-IMPL-24 ruling asks this decision to contain.

---

## D-IMPL-20 — HITL transport (GATING)

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §8.2 ("The SDK exposes HITL events through Protocols — queue interfaces, webhook hooks, MCP server endpoints").

**Recommendation: a `HITLTransportProtocol` (typed queue interface) as the core mechanism, with two reference transports — MCP server endpoints exposing HITL queues (primary, serving example 05 and the CLI) and webhook delivery (secondary).** Concretely:

- **The core is a typed queue contract:** pending HITL events (ApprovalGate, ExceptionEscalation, OverrideBoundary, ReviewQueue items) are typed records — event class, workflow state reference, the Context Product the human must see, deadline/escalation policy reference — enqueued by the HITL primitives and consumed/acted through the Protocol. Actions (approve/reject/override/annotate) return through the same surface and land in the replay record by construction (§8.2 audit-by-construction; there is no transport path that bypasses capture).
- **Reference transport 1 — MCP endpoints:** HITL queues exposed as MCP Resources and actions as MCP Tools on the Experience-Layer surface (consistent with the D-IMPL-13 edge allocation), which is what the `ccf hitl` CLI subcommands (D-IMPL-22) and example 05 consume.
- **Reference transport 2 — webhooks:** outbound event notification for wiring to existing human-task systems (the CLAUDE.md §8.2 "users wire to their existing systems" posture); the webhook notifies, the action still flows back through the typed queue surface — notification and authority are separated so audit capture cannot be bypassed.
- No inbox UI, no task-management system — out of scope per CLAUDE.md §8.2/§13.

Rationale: queue-only would leave example 05 with no operable front door; MCP is already the Experience Layer's primary surface and adds no new protocol dependency; separating notification (webhook) from action (typed queue) keeps audit-by-construction structural.

**Alternative A — queue interface only (users build all delivery).** Consequence: smallest surface; but the v0 examples and CLI would each need bespoke plumbing, and "working front door from day one" (CLAUDE.md §8.3 framing, applied to HITL) fails.

**Alternative B — webhook-first (push model as the primary mechanism).** Consequence: integrates naturally with enterprise task systems; but push-only makes the acting surface live outside the SDK's typed boundary — approvals arriving as arbitrary HTTP callbacks weaken the identity binding (D-IMPL-21) and make audit-by-construction contingent on the receiver's discipline.

---

## D-IMPL-27 — Substrate split: ArtifactStore vs native storage Protocols

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §7.4. Interacts with D-IMPL-06 (snapshot artifacts), D-IMPL-18 (workflow state), D-IMPL-26 (addressing).

**Recommendation: split by mutability — immutable, versioned, replay-relevant artifacts route through the ArtifactStore; hot mutable state stays on native Protocols.** Concretely, through the ArtifactStore in v0: Decision Replay records (all five dimensions + extensions), materialized graph-substate and similarity-index snapshots (per D-IMPL-06), Context Products at rest, Control Plane bundles (policy bundles, λ_c tables, workflow definitions, HITL policies, A2A trust policy, OperatorParameterSets), and all No-Hardcoding artifacts (agent/task definitions, prompt artifacts, skill catalog entries and grants) — i.e., the full CLAUDE.md §7.4 artifact-class list. On native Protocols: the live Context Graph (GraphStore, D-IMPL-02), the live similarity index (D-IMPL-03), operator-plan intermediate caches (D-IMPL-36 — coherence-managed, evictable, not artifacts), and suspended workflow execution state (D-IMPL-18 — mutable until terminal; the terminal trace then lands in the ArtifactStore as part of replay).

Rationale: the ArtifactStore's constraints (§7.4 — immutable, versioned, replay resolves exact versions) define what belongs in it; anything mutable or evictable placed there either violates the constraints or forces an exception regime. The mutability criterion is a single structural rule instead of a per-class negotiation, and it preserves single-writer trivially (the store never holds live graph state, so it can never become a second writer).

**Alternative A — everything through the ArtifactStore, including hot state.** Consequence: one substrate, simplest mental model; but the live graph behind an MCP artifact server destroys the p99 300ms envelope (INV-CH7-52 territory) and puts an immutability-contracted store in the mutation path — a category error.

**Alternative B — minimal ArtifactStore (replay records only; everything else native).** Consequence: smallest v0 store surface; but Control Plane bundles and definition artifacts then have no versioned, immutable home, and example 07 (swap file-backed store for MCP-backed, nothing else changes) loses most of its demonstration value.

---

## D-IMPL-36 — Operator-plan intermediate scheduling and materialization

**Origin:** docs/DECISIONS.md D-IMPL-36; originates in whitepaper §7.4.2, Fig-CH07-08 (INV-CH7-28). Interacts with D-IMPL-06/27 (intermediates are cache state, not artifacts).

**Recommendation: a deterministic intermediate cache with Control-Plane-configured materialization policy — the SDK ships the coherence mechanism; when-to-cache is values.** Concretely: intermediates are keyed on `(tenant, operator_key, parameter_set_version, input_intermediate_keys, graph_snapshot_id)` — a deterministic key, so a cache hit is by construction the same value replay would produce (INV-CH7-28's contract: persistable, cache-coherent, reusable for replay). Invalidation rides the committed supersession Policy-event cascade (λ_c collapse and supersession invalidate downstream intermediates predictably; lazy re-derivation, never eager — INV-CH7-51 territory). Whether a given operator/product class materializes intermediates at all, retention window, and eviction budget are per-class Control Plane configuration under the D-IMPL-38 parameter discipline (no SDK-side default values). The Planner's intermediate-reuse decision at the composition-preservation checkpoint (Fig-CH07-10) reads this cache. Homecams' TTL-indexed `projection_cache` separate from graph state is a data point confirming the separate-cache shape works in production; the SDK's deterministic keying is designed against the whitepaper contract, not inherited.

**Alternative A — always materialize every intermediate.** Consequence: maximal reuse and trivially replay-complete; but storage/compute cost is unbounded for deep compositions at volume, and the whitepaper deliberately leaves the decision to policy ("cache-coherent" is required; "always cached" is not).

**Alternative B — never materialize (recompute every composition end-to-end).** Consequence: zero coherence machinery; but the §7.6.4 derived-on-demand cost bands (×8–15 worst quadrant) are exactly the economics materialization exists to bound, and the Fig-CH07-10 intermediate-reuse checkpoint becomes dead mechanism.

---

## D-IMPL-44 — Cold-archive re-hydration contract for compressed replay records

**Origin:** docs/DECISIONS.md D-IMPL-44; originates in whitepaper §7.10.1/§7.10.5 (INV-CH7-80/81/89). This entry owns the re-hydration contract specifically; 06 owns snapshots, 26 addressing, 27 substrate.

**Recommendation: a typed `ReHydrationRecipe` carried by every compressed record, plus a `ColdSourceArchiveProtocol` — the SDK ships the deterministic re-hydration mechanism; the archive substrate is pluggable.** Concretely: at compression (tier 2 of INV-CH7-89), the graph substate is reduced to (a) the deterministic content hash of the materialized substate artifact and (b) a typed recipe — the L1 envelope ids / source references, entity URIs, temporal boundary, and the operator-plan + parameter-set + policy-bundle version references needed to re-derive the substate. Re-hydration re-runs L2 assembly against the archived source signals under the pinned Control Plane versions and **verifies the result against the stored hash** — bit-for-bit or the re-hydration fails loudly (never a silent approximation). The `ColdSourceArchiveProtocol` is the seam to WORM/durable source archives (the whitepaper's own Evidence Chain terminus, INV-CH7-87); reference impl file-backed for dev. Recipes and hashes are ArtifactStore artifacts addressed per D-IMPL-26.

**Alternative A — retain full-fidelity substates permanently (no re-hydration needed).** Consequence: simplest audit story; but it abolishes the compressed tier the whitepaper commits (INV-CH7-89) and re-imports the year-scale cost problem compression exists to solve.

**Alternative B — leave re-hydration to deployments (SDK stores hash only, mechanism unspecified).** Consequence: least SDK surface; but "re-hydratable from the cold source archive" (§7.10.5) becomes an unverifiable claim — a hash without a recipe is a checksum of something no one can rebuild, and the audit obligation the tier exists to satisfy fails at exactly the moment it is invoked.

---

## D-IMPL-50 — Replay fidelity-lifecycle mechanism: SDK-shipped or ArtifactStore-delegated

**Origin:** docs/DECISIONS.md D-IMPL-50; originates in whitepaper §7.10.5 (INV-CH7-89). Interacts with D-IMPL-06/27/44; distinct in that it allocates the *mechanism*, not the substrate.

**Recommendation: SDK-shipped mechanism, executing above the ArtifactStore Protocol.** The three-tier compression, the severity exemption, and the structural `retention-reason` field are committed whitepaper mechanism, not deployment options: "deterministic algorithm, CI-tested severity exemption, structural retention-reason — bypassing is not silent" (INV-CH7-89, which the whitepaper frames as an architectural invariant of a reference implementation, and Patent Claim 14 covers). The SDK therefore ships the lifecycle engine: deterministic compression function per record class, the never-compress/never-tombstone severity exemption enforced in mechanism, retention-reason written structurally on every transition — operating on artifacts *through* the ArtifactStore Protocol, so any conforming store gets the lifecycle for free. What is values: retention windows per decision class, the severity threshold per decision class, tombstone minima — all Control Plane configuration under the D-IMPL-38 discipline. Homecams' working retention lifecycle is a data point that a lifecycle-above-store split operates in production; the SDK's design follows the whitepaper contract, not that resolution.

**Alternative A — ArtifactStore-delegated (retention is entirely the store's policy).** Consequence: thinner SDK; but the severity exemption and deterministic-compression invariants become per-store promises the CI suite cannot verify uniformly, and a store that quietly tombstones a severity-exempt SAR-class record breaks the exact regulatory commitment (§7.10.5 "Significant decisions retain full fidelity permanently") the tier system exists for.

**Alternative B — hybrid: SDK defines the tier/exemption contract as Protocol obligations; each store implements compression natively.** Consequence: stores can optimize compression physically; but N stores × 1 deterministic algorithm is N chances to diverge, and replay of a compressed record would depend on which store compressed it — mode-invariant replay (INV-CH7-88) argues for one shipped algorithm.

---

## D-IMPL-18 — Workflow state persistence

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §8.1. Interacts with D-IMPL-27 (suspended state is hot-mutable, not artifact-shaped).

**Recommendation: Control Plane persistence (the CLAUDE.md §12 recommended option) — suspended workflow execution state lives at the Control Plane boundary as typed, versioned state records on the Control Plane's native store; terminal traces land in the ArtifactStore as replay artifacts.** Concretely: §8.1 already commits "state is persisted at the Control Plane boundary so a workflow can suspend on a HITL gate or a long-running monitoring trigger and resume later" — this ruling confirms that locus. Execution state (current node, variable bindings, pending-gate references) is mutable until the workflow terminates and therefore stays off the ArtifactStore per the D-IMPL-27 mutability rule; every state *transition* is appended to the execution trace, and at terminal (or at each suspend, for long-horizon audit) the trace is written through to the ArtifactStore as part of the replay record (dimensions 4/5 extensions, CLAUDE.md §8.1). The persistence substrate is the Control Plane's storage seam — pluggable at that level, not a separate workflow-store Protocol.

**Alternative A — separate dedicated workflow store.** Consequence: a purpose-shaped store for workflow scale; but it adds a fourth substrate (graph, artifacts, control plane, workflows) for v0's "in-fabric coordination, not Temporal-scale" primitive — infrastructure disproportionate to the committed scope, and durable-execution scale is `OrchestrationProtocol` territory anyway (D-IMPL-17).

**Alternative B — pluggable `WorkflowStateProtocol` with no committed locus.** Consequence: maximal flexibility; but §8.1 has already committed the Control Plane boundary in prose, and an uncommitted locus forces every deployment to make a decision the SDK should have made — an adoptability failure for a v0 primitive.

---

## D-IMPL-21 — HITL identity binding

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §8.2. Interacts with D-IMPL-15 (A2A identity) and D-IMPL-20 (transport).

**Recommendation: pluggable via the same `IdentityProvider` Protocol family as D-IMPL-15, with a distinct human-principal binding shape — not the same PKI mandated, not a separate bespoke system.** Concretely: every HITL action record carries a typed `HumanPrincipalBinding` — approver identity (subject id + identity-provider reference), authentication context (method, assurance level, session reference), action time, and the content hash of the Context Product the approver saw (per D-IMPL-26 addressing — "the Context Product the approver saw" is a §8.2 commitment, and a hash makes it exact). The binding is produced by an `IdentityProvider` implementation at the HITL action surface; deployments plug their IdP (OIDC/SAML enterprise providers being the realistic case for human principals, vs. mTLS+JWS for workloads per D-IMPL-15). Reference impls: authenticated-principal record from the HTTP/MCP auth context (dev), and a JWS-signed binding reusing the D-IMPL-15 signing machinery for deployments wanting cryptographic non-repudiation. Audit-by-construction holds regardless of provider: no HITL action can land without a binding.

**Alternative A — same PKI as A2A, mandatory (humans get X.509/JWS identities).** Consequence: one identity substrate, strong non-repudiation; but human principals in enterprises live in OIDC/SAML directories, not workload PKI — mandating certificate-backed human identity is an adoption wall for a v0 with no shipped inbox UI.

**Alternative B — separate bespoke HITL identity system.** Consequence: purpose-built; but two identity frameworks in one SDK is surface without benefit when the Protocol seam already generalizes, and replay would carry two incompatible identity shapes.

---

## D-IMPL-22 — CLI shape

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §8.3.

**Recommendation: noun-verb subcommand structure — `ccf <noun> <verb>` — covering exactly the §8.3 enumerated surfaces, as a thin client over the HTTP API with a direct-library mode for dev.** Concretely, the v0 noun set: `ccf agent` (declare | list | show | versions), `ccf skill` (catalog | grant | revoke | show), `ccf workflow` (run | status | resume | list), `ccf hitl` (queue | show | approve | reject | override), `ccf replay` (query | resolve | verify), `ccf artifact` (list | get | put | verify), `ccf product` (get | list), `ccf config` (Control Plane bundles: show | apply | versions). Every mutating verb routes through the same factories/Control Plane actions as any other client (No-Hardcoding: `ccf agent declare` takes an artifact file, never inline definition flags), so the CLI adds zero privileged paths. Thin-client-over-HTTP keeps one authorization/audit surface; `--local` direct-library mode serves the SQLite/file-backed quickstart where no server runs (examples 00–02).

**Alternative A — flat command set (`ccf declare-agent`, `ccf grant-skill`, ...).** Consequence: fewer keystrokes for the top commands; but the §8.3 surface is already ~8 domains and growing — flat namespaces stop scaling immediately, and the noun-verb form is the ecosystem-legible default (git/kubectl/gh).

**Alternative B — CLI as a first-class runtime peer (own direct fabric bindings, richer than the API).** Consequence: powerful operator tool; but any CLI capability the HTTP API lacks becomes an undocumented second surface with its own auth/audit posture — the Experience Layer's three front doors should expose one capability set.

---

## D-IMPL-23 — HTTP API surface

**Origin:** CLAUDE.md §12; originates in CLAUDE.md §8.3 ("HTTP API skeleton — REST endpoints over the fabric").

**Recommendation: a minimal v0 skeleton mirroring the CLI noun set, with OpenAPI generated from the Pydantic contracts.** Concretely, v0 endpoint families: `GET /products/{class}` + `GET /products/{class}/{id}` (Context Product retrieval — the primary integration surface); `POST /agents` (declare from artifact) + `GET /agents`, `/agents/{id}`, `/agents/{id}/versions`; `POST /skills/grants` + `DELETE /skills/grants/{id}` + `GET /skills/catalog`; `POST /workflows/{id}/invocations` + `GET /workflows/invocations/{id}` + `POST /workflows/invocations/{id}/resume`; `GET /hitl/queues/{queue}` + `POST /hitl/events/{id}/actions`; `GET /replay/decisions/{id}` + `POST /replay/decisions/{id}/resolve`; `GET/PUT /artifacts/...`; `GET /health`, `GET /openapi.json`. All request/response bodies are the same Pydantic `extra=forbid` contracts the SDK already defines (typed contracts at every boundary, CLAUDE.md §11) — the API adds serialization, auth hooks, and routing, no new semantics. Ingestion (L1) is deliberately *not* on the v0 HTTP surface: ingress is CDC/MCP-adapter territory (D-IMPL-13/33), and a generic write endpoint would invite a second writer path.

**Alternative A — products-only read API.** Consequence: tiny, safe; but the CLI (thin client, D-IMPL-22) then cannot exist over HTTP, and "the primary surface for service integration and for custom UX layers" (§8.3) fails for every operation except read.

**Alternative B — full CRUD over every fabric object incl. graph entities.** Consequence: maximal integratability; but entity-level write endpoints bypass L2 — a single-writer violation by API design — and v0 "skeleton" (§8.3's own word) argues for the minimal governed set.

---

## D-IMPL-43 — Closed-loop interpretation step: automated vs human-gated

**Origin:** docs/DECISIONS.md D-IMPL-43; originates in whitepaper §7.9.1 (INV-CH7-75). Interacts with CLAUDE.md §8.2 (HITL) and D-IMPL-29 (whose two-tier pattern this reuses).

**Recommendation: configurable per learning-signal class, defaulting to human-gated — the D-IMPL-29 two-tier shape applied to the closed loop.** The ambiguous passage (§7.9.1): *"The interpretation step is where business judgment, statistical significance, and regulatory calibration constraints enter the loop"* — the whitepaper names human-flavored inputs without specifying the actor. Concretely: every closed-loop Control Plane update (operator parameters, projection weights, policy thresholds, half-life adjustments — §7.9's committed update classes) flows through an interpretation stage that is a workflow with an ApprovalGate **by default**; Control Plane policy may configure specific signal classes × parameter classes × bounded deltas as auto-applied (tier-1: always-on validation against declared parameter bounds per D-IMPL-38; tier-2: ApprovalGate unless explicitly waived for that class). Every update — gated or auto — is a versioned Control Plane action in the audit plane; "the loop is in the graph, not the model" stays intact either way. Default-gated is the fidelity-conservative reading: "business judgment... regulatory calibration" are human vocabulary, and SR 11-7-flavored deployments cannot accept silent auto-calibration.

**Alternative A — always human-gated, no auto path.** Consequence: maximally conservative; but high-frequency low-stakes calibrations (e.g., cache-window tuning from hit-rate signals) would drown a review queue, and the whitepaper's continuous-learning framing implies some automated flow.

**Alternative B — automated by default, human-gated on exception.** Consequence: the loop runs at machine tempo; but the whitepaper's own wording puts judgment *inside* the interpretation step, and auto-default means a mis-specified learning signal rewrites policy thresholds before any human sees it — the exact governance inversion the Control Plane exists to prevent.

---

## D-IMPL-30 — Context Product Contract element count (eight vs nine)

**Origin:** docs/DECISIONS.md D-IMPL-30; originates in whitepaper §6.3 (INV-CH6-03). Ambiguous passage (§6.3): the prose opens *"Nine elements jointly specify the contract"* and the table lists nine (Assembly Mode included; §6.4 calls it *"the §6.3 specification's ninth element"*), yet the same §6.3 prose describes *"the § 6.1 canonical 8-property table"* and CLAUDE.md §5 refers to "the eight-element specification per §6.3."

**Recommendation: reading (a) with the (c) annotation — the contract has nine elements; the "eight" references are annotated as editorial drift.** Concretely: the SDK Contract base carries all nine elements including Assembly Mode; §6.4's explicit "ninth element" language plus the nine-row table is the strongest internal evidence of authorial intent, and Assembly Mode is load-bearing mechanism elsewhere (the §7.6 three-mode model and the per-mode replay footprints of INV-CH7-88 hang off it — a contract without the mode cannot say which replay footprint applies). The eight-count references (including CLAUDE.md §5's) are recorded in DESIGN.md as an annotated discrepancy, and — since CLAUDE.md wins on disagreement as a governance matter — Dave's ruling here doubles as authorization to treat CLAUDE.md §5's "eight" as tracking the same drift rather than overriding the whitepaper table. Note also the Fig-CH07-13 seven-field *typed base* (INV-CH7-45) is a different artifact — base contract fields vs. specification elements — and DESIGN.md will state the mapping explicitly to stop the counts colliding again.

**Alternative — reading (b): eight elements; Assembly Mode is per-product-class configuration in Control Plane registration, not a contract element.** Consequence: cleaner contract/config separation and consistency with the "eight" references; but the replay record then has to fetch the mode from registration state instead of the product itself, weakening the self-describing property replay leans on, and it contradicts §6.4's "ninth element" wording head-on.

**Alternative — reading (c) alone: treat the count as editorial, rule nothing structural.** Consequence: no design commitment; but the SDK must declare the base schema in Phase I regardless — deferring the count just moves the same decision to a worse moment.

---

## D-IMPL-31 — TTL granularity: per-signal vs per-product

**Origin:** docs/DECISIONS.md D-IMPL-31; originates in whitepaper §6.4 Step 4 vs §6.3 (INV-CH6-04). Ambiguous passage: §6.4 Step 4 states *"Temporal Validation assigns TTL to each mutation,"* while §6.3 defines TTL as a per-product contract element, and §6.4's worked thread gives both per-product TTLs (4h/24h) and per-signal TTLs (15 min blotter entry).

**Recommendation: reading (a) — two granularities with a declared derivation rule.** Concretely: the SDK ships (i) a **signal-level validity primitive** — each observation carries a validity envelope derived from its type's λ_c (the §7.7 machinery, so this is a naming of existing mechanism, not a new decay system); and (ii) the **product-level contract TTL** (`expires_at` + `ttl_anchor` per INV-CH7-45), whose derivation is declared per product class in the Control Plane: `expires_at = min(class-configured ceiling per D-IMPL-39 MAX_TTL, derivation over constituent signal validities)` with the derivation function (min is the reference default shape; the choice per class is configuration) declared under the D-IMPL-38 parameter discipline. This makes the worked thread's both-granularities usage literal rather than loose, and it gives the asymmetric-freshness mixing-refusal rule a formal footing: a product class may declare constituent-validity floors whose breach refuses assembly rather than emitting a product fresher-labeled than its stalest load-bearing constituent.

**Alternative — reading (b): only contract-level TTL is properly TTL; Step 4's "TTL" means the T-dimension validity envelope.** Consequence: one TTL concept, simpler vocabulary; but the SDK still needs the signal-validity type either way (the 15-min blotter entry is real mechanism), so this is reading (a) with less honest naming.

**Alternative — reading (c): product TTL independently configured per class; Step 4 only validates constituents; no derivation rule.** Consequence: simplest configuration story; but a 24h-TTL product assembled from a 15-min signal is then structurally expressible with no gate refusing it — the freshness-misrepresentation failure mode §6.4's thread exists to dramatize.

---

## D-IMPL-32 — Context Trust Triangle scoring mechanics

**Origin:** docs/DECISIONS.md D-IMPL-32; originates in whitepaper §6.6.3 (INV-CH6-08). Ambiguous passage (§6.6.3): *"when all three legs hold, the recursion may terminate"* — no aggregation function, scale, or threshold mechanics are specified for any leg or the aggregate.

**Recommendation: reading (a) with (b) folded in as the reference implementation — a `TrustScorer` Protocol with pluggable per-leg scorers and a conjunctive combinator; the shipped reference scorer derives leg strengths from the §7.7 debt components.** Concretely: the SDK defines the mechanism — three typed legs, each scored in [0,1] by a `LegScorer` Protocol; termination is conjunctive ("all three legs hold" is the whitepaper's own combinator: each leg ≥ its threshold), with per-leg thresholds as Control Plane values per decision class (D-IMPL-38 discipline, no SDK defaults). The reference `LegScorer` set computes legs from the D_c components (the §7.7.8 debt-mapping the entry itself notes partially supports this: leg strengths derive from the three debt components — F, C, S per D-IMPL-47), so v0 ships a working trust surface with zero new measurement machinery, while deployments with independent trust signals plug their own scorers. Every computed leg score, threshold version, and termination verdict lands in the replay record.

**Alternative — reading (b) alone: legs are purely derived D_c quantities; no independent trust primitive.** Consequence: no new Protocol; but deployments whose trust inputs are not debt-shaped (e.g., source-reputation systems) have no seam, and the triangle's termination role in the §6.6 recursion gets hard-wired to one derivation.

**Alternative — reading (c): the triangle is advisory vocabulary; no SDK primitive, replay captures inputs only.** Consequence: zero mechanism cost; but "the recursion may terminate" is a control-flow commitment — something must decide termination, and an unspecified something is exactly what CLAUDE.md §15 says not to paper over.

---

## D-IMPL-42 — Learning-signal taxonomy naming

**Origin:** docs/DECISIONS.md D-IMPL-42; originates in whitepaper §7.9.2 vs Fig-CH07-24 (INV-CH7-76). Ambiguous passage: the §7.9.2 prose categories (*outcome / context-validity / audit-lineage*) diverge from the Fig-CH07-24 handler names (*Outcome / Correction / Metadata*) — an informational naming divergence inside the whitepaper.

**Recommendation: adopt the prose taxonomy as canonical — typed enum `OUTCOME | CONTEXT_VALIDITY | AUDIT_LINEAGE` — with the Fig-CH07-24 handler names documented as the dispatch-side aliases.** Rationale: the prose names describe *what the signal is about* (the semantic category the enum must carry through the Control Plane and replay record), whereas the figure names describe *what the handler does with it* — "Correction" and "Metadata" are handler roles, not signal semantics, and an enum named for handler behavior couples the taxonomy to one processing topology. Prose-over-figure also matches the inventory's own reading (INV-CH7-76 flags the divergence as informational, with the prose carrying the commitment). DESIGN.md records the alias table (context-validity ↔ Correction handler; audit-lineage ↔ Metadata handler) so the figure remains legible against the code.

**Alternative A — adopt the figure's handler names as the enum.** Consequence: code matches the diagram people will look at; but `Metadata` as a signal category is near-meaningless at the type level, and future handler restructuring (two handlers for one category) would strand the names.

**Alternative B — invent a third, cleaner taxonomy.** Consequence: best names win; but inventing vocabulary the whitepaper doesn't use is a fidelity cost with zero mechanism benefit — the discipline is pick-one-of-theirs and annotate.

---

## D-IMPL-47 — Computable definitions for the F, C, S debt factors

**Origin:** docs/DECISIONS.md D-IMPL-47; originates in whitepaper §7.7.4/§8.7.1 (INV-CH7-62, INV-CH8-16). Ambiguous passage: the extended form *"D_c = 1 − (F · C · S)"* is given without specifying how F (freshness), C (completeness), and S (semantic consistency) are individually computed; §7.7.6 names the runtime signals per component but not the factor computations.

**Recommendation: a per-factor `DebtFactorScorer` Protocol with SDK reference computations built from the runtime signals §7.7.6 itself names — mechanism shipped, calibration as values.** Concretely, the reference scorers: **F** = an aggregation over constituent signal freshness ratios `R(t)/R₀` from the committed decay form `R(t) = R₀ × (1/2)^((t−t₀)/λ_c)` (reference aggregation: weighted minimum over load-bearing constituents; weights/aggregation choice per product class); **C** = declared-slot coverage — the fraction of the product class's required contract slots populated by admissible observations (the coverage-percentage signal §7.7.6/INV-CH7-89 already name); **S** = 1 − (detected-contradiction rate over the assembled substrate: conflicting values for the same (entity, attribute, as-of) under supersession rules — the conflict signals the assembly engine already surfaces). Each factor ∈ [0,1]; `D_c = 1 − (F·C·S)` verbatim (the multiplicative-conjunctive form is committed — INV-CH7-63 defends it). All weights, thresholds, and aggregation selections are per-class Control Plane parameters under D-IMPL-38; deployments with richer semantics plug their own scorers. Factor values + scorer identity/version land in the replay record (composite D_c is already a compressed-tier field, INV-CH7-89).

**Alternative A — fixed SDK formulas, no Protocol.** Consequence: simplest, fully deterministic across deployments; but S in particular is domain-sensitive (what counts as a contradiction), and hard-wiring it violates mechanism-not-values at exactly the point §7.7.6 left open.

**Alternative B — fully user-supplied (SDK defines only the interface and the combination form).** Consequence: zero SDK opinion; but v0 then ships debt gating (CAR routing, Forced LLM, Fail-Closed — all committed mechanism) that cannot run until every adopter writes three scorers — an adoptability failure for the quickstart.

---

## D-IMPL-48 — Supervision Quality: scoring function and SDK-scope disposition

**Origin:** docs/DECISIONS.md D-IMPL-48; originates in whitepaper §8.8 (INV-CH8-19). Ambiguous passage: the §8.8 composite scoring function combining the five behavioral axes with VLM/LLM reasoning outputs is unspecified — axis weights, fusion function, and score semantics are all open; also open is whether Supervision Quality is SDK mechanism at all.

**Recommendation: out of v0 SDK scope — Supervision Quality ships as a documented reference pattern, not mechanism.** Rationale: CLAUDE.md §13's v0 scope list does not include it, and the honest reading of §8.8 is that it is a *domain application* of committed primitives rather than a new primitive: the five behavioral axes are domain values (the property-intelligence flavor is visible in the axis set), the fusion function is calibration, and the VLM/LLM reasoning stage is ordinary semantic-stage mechanism under the Alternation invariant. Everything a deployment needs to build it already exists in the fabric: signals through L1, axis computations as user-registered operators (D-IMPL-37), the composite as a user-defined Context Product class, thresholds via D-IMPL-38, and escalation via the HITL primitives. DESIGN.md records the disposition with a short "how you would build it" sketch (candidate future example, not v0 suite); no SDK type is named `SupervisionQuality`.

**Alternative A — ship a `CompositeScorer` Protocol (generic multi-axis fusion mechanism, Supervision Quality as its motivating case).** Consequence: a reusable scoring primitive with §8.8 as documentation; but no other inventory entry demands generic score fusion, so the Protocol would be speculative surface — and speculative mechanism is scope creep with a maintenance tail.

**Alternative B — defer entirely (no disposition, revisit post-v0).** Consequence: zero Phase D cost; but the census requires a disposition, and an undisposed §8.8 invites Phase I to improvise — the exact silent-scope failure the marathon exists to prevent.

---

*End of batch 3 briefs. 19 decisions: 26, 06, 17, 20 (gating) + 27, 36, 44, 50, 18, 21, 22, 23, 43 + 30, 31, 32, 42, 47, 48. Awaiting Dave's rulings per the plan's Task 2 checkpoint.*
