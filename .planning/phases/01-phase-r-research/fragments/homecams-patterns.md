# Appendix: homecams-patterns

Read-only pattern review of `/home/parkave/homecams_v2` per CCF CLAUDE.md §2.1 discipline.
Every pattern is a **triangulation data point, never a canonical answer**. Where the
whitepaper and Homecams disagree, the whitepaper wins. No code is ported; rows cite
source paths only.

Marker vocabulary (exactly two values): `candidate pattern` | `domain-specific — do not inherit`.

Homecams `/home/parkave/homecams_v2/CLAUDE.md` (829 lines) was read exactly once, as
additive best-practices context only, per CCF CLAUDE.md §2 — nothing from it overrides
this project's own CLAUDE.md.

## Pattern Table

| Pattern | Source (Homecams path) | Marker | Notes |
|---------|------------------------|--------|-------|
| Framework/domain package split — domain-agnostic primitives in one package, domain subclasses in another | `packages/si-framework/` vs `packages/si-pool-safety/` | candidate pattern | Homecams' `si-framework`/`si-pool-safety` line is the same boundary CCF SDK draws between `/src` mechanism and user configuration; Homecams enforces it by package, the SDK will enforce it by artifact (§6.4). |
| Context Graph as persisted typed model, enrich-only (downstream stages enrich, never rebuild) | `packages/si-framework/src/si_framework/models/context_graph.py` (`ContextGraphNode`); domain subclass `packages/si-pool-safety/src/si_pool_safety/models/pool_context_graph.py` | candidate pattern | Matches whitepaper append-only-with-supersession posture; Homecams realizes "accumulate, never reconstruct" as an architectural constraint. |
| Operator vs Projection separation — operators construct truth + load-bearing metadata; projections interpret truth for a consumer | `packages/si-framework/src/si_framework/services/operator_resolver.py`, `projection_engine.py`, `contracts/projection.py` | candidate pattern | Homecams' formalized v5.0 split (operators → resolved context + metadata → ProjectionExecutionEngine) is one working resolution of whitepaper §7.4/§7.5 two-stage execution. |
| Projection contract shape: `ProjectionPlan` Protocol + `ContextProductContract` + `ProjectionLineage` + `OperatorRef` | `packages/si-framework/src/si_framework/contracts/projection.py` | candidate pattern | Protocol-based structural typing consistent with whitepaper §7.5 `required_operators()`/`invoke()`; concrete shape is a data point for SDK design. |
| Projection derived from (agent role, decision intent, product contract) triple | `packages/si-framework/src/si_framework/services/projection_engine.py`, projection registry `projection_registry.py` | candidate pattern | A resolution of how Π role-conditioning selects a projection plan; whitepaper specifies Π mechanism, not the plan-selection inputs. |
| Context Products as terminal delivery interface — agents never query the graph, never run operators | `packages/si-framework/src/si_framework/models/context_product.py` (`ContextProductBundle`); call site `packages/si-pool-safety/src/si_pool_safety/tools/guardian_tools.py` | candidate pattern | Directly validates whitepaper §6.3/§7.6 delivery posture (existence proof). |
| Materialized projection-output cache with TTL index, distinct from graph state | `packages/si-framework/src/si_framework/repositories/projection_cache_repository.py` | candidate pattern | TTL-governed cache of projection outputs (whitepaper is silent on materialization/caching of intermediates) — data point for operator-DAG intermediate handling; see Open Questions. |
| Context Half-Life as first-class state + service | `packages/si-framework/src/si_framework/models/context_primitives.py` (`ContextHalfLifeState`), `services/context_half_life_service.py` | candidate pattern | Mechanism shape (per-observation-type decay state + service) is inheritable; the λ_c *values* are not (see below). |
| Property-intelligence λ_c values and per-observation-type half-life tables | `config/policy.yaml` (`ContextHalfLifePolicy` in `si_framework/models/policy.py`) | domain-specific — do not inherit | Domain calibration; CCF CLAUDE.md §13 "not the SDK's problem at all". |
| Context Debt as decomposed components with conservative bias (debt biases urgency upward) | `packages/si-framework/src/si_framework/models/context_primitives.py` (`ContextDebt`, `CoverageDebtComponent`), `services/context_debt_service.py` | candidate pattern | Component decomposition and the incomplete-information-as-risk-amplifier stance are data points for whitepaper §7.7.4–§7.7.8 D_c gating (Forced LLM / Fail-Closed). |
| Camera/temporal/identity debt component taxonomy | `si_framework/models/context_primitives.py` (camera coverage, temporal coverage, identity resolution debt) | domain-specific — do not inherit | Sensor-domain component taxonomy; the SDK ships debt *mechanism*, users define components. |
| Decision Replay record with five dimensions persisted per significant decision | `packages/si-framework/src/si_framework/models/context_primitives.py` (`DecisionReplayRecord`), `reporting/replay_service.py` | candidate pattern | Existence proof of whitepaper §7.10.1 five-dimension record persisted at write time, not retrofitted. |
| Context compression / three-tier fidelity lifecycle (full → compressed → tombstoned; high-threat never compressed) | `si_framework/models/context_primitives.py` (`CompressedContextSnapshot`); `pool_context_graph.py` `compress()` | candidate pattern | One resolution of year-scale replay tractability the whitepaper leaves open (D-IMPL-06) — data point, not a default; policy of *what* is never compressed is domain-specific. |
| Policy as first-class config loaded into typed models (`SystemPolicy` hierarchy) | `packages/si-framework/src/si_framework/models/policy.py`, `services/policy_service.py`, `config/policy.yaml` + `config/zone_policies.yaml` | candidate pattern | Control-Plane-as-typed-config pattern; the policy *content* (age brackets, supervision ratios, escalation rules) is do-not-inherit (next row). |
| Age classification, supervision ratios, threat/urgency ladders, escalation rules | `config/policy.yaml`, `config/zone_policies.yaml`, `si_framework/models/policy.py` value semantics | domain-specific — do not inherit | Pure domain values (child safety domain); cautionary-contrast example of the mechanism/values line. |
| No-Hardcoding rule enforced by CI grep guard; YAML agent/task definitions + Jinja2 prompt templates with versioned policy/prompt/toolchain per invocation | `config/agent_descriptions/`, `config/task_descriptions/`, `config/prompts/`, CI guard `packages/si-pool-safety/tests/ci_guards/test_no_inline_prompts.py` | candidate pattern | Direct precedent for CCF CLAUDE.md §6.4 No-Hardcoding Rule and its CI lint; YAML+Jinja2 is one data point for D-IMPL-28 (format is open — do not inherit the format by default). |
| Single-writer enforcement: one process (EnrichmentWorker) is sole writer of graph-state collections; hot-path agent writes only its own ingest collections | `packages/si-pool-safety/src/si_pool_safety/enrichment_worker/worker.py`; ADR in Homecams CLAUDE.md §3.2/§5.8 | candidate pattern | Working realization of the whitepaper single-writer invariant (only L2 writes L3), enforced by process topology + repository ownership. |
| Sync/async boundary as process split (synchronous hot path, out-of-process async enrichment worker) — "when sync and async natures collide, split into two processes" | `packages/si-pool-safety/src/si_pool_safety/services/ccf_agent.py` (sync router) + `enrichment_worker/` (async, spawned by `start_property_intelligence.py`) | candidate pattern | Operationally-proven resolution relevant to D-IMPL-04(b) (sync/async runtime posture) — data point only. |
| Idempotent upsert with lineage accumulation and unique natural-key indexes | `packages/si-pool-safety/src/si_pool_safety/repositories/graph_entities_repository.py` (`graph_entities`), `si_framework/repositories/context_edge_repository.py` (`context_edges`, in-batch dedup + unique natural key) | candidate pattern | Matches whitepaper §7.3 idempotent-upsert/multi-source-lineage mechanism (existence proof). |
| Tenant-scoped repository base class; `tenant_id` filter on reference collections | `packages/si-framework/src/si_framework/repositories/tenant_scoped.py` | candidate pattern | Data point for D-IMPL-05 (tenancy model): tenant_id first-class at the repository layer. |
| Zone/camera topology, adjacency, coverage percentages, zone SAA registry | `packages/si-pool-safety/src/si_pool_safety/models/infrastructure.py` (`CameraTopology`, `AdjacentCamera`), `config/zone_policies.yaml` | domain-specific — do not inherit | Camera/sensor spatial ontology is domain values; equivalent SDK concept is user-supplied ontology config. |
| Person/pet/vehicle entity ontology, sentinel labels, known-person registry | `packages/si-pool-safety/src/si_pool_safety/models/` (perception/comprehension models), `persons` registry, `si_framework/models/vehicle_events.py` gallery design | domain-specific — do not inherit | Named in CCF CLAUDE.md §2.1 as the canonical do-not-inherit example. |
| LangGraph 7-node zone agent orchestration | `packages/si-pool-safety/src/si_pool_safety/situational_awareness/`, Homecams CLAUDE.md §3.1 | domain-specific — do not inherit | Homecams hard-binds a specific harness (LangGraph); CCF SDK is harness-neutral by invariant (§7.3) — cautionary contrast, and evidence the loop can live outside SDK mechanism. |
| MQTT topic-namespace event fan-out (`si/{tid}/...`) as the L1/L2 transport | `packages/si-observer/src/si_observer/transport/`, `si_pool_safety/services/ccf_agent.py` | domain-specific — do not inherit | Transport choice bound to the deployment; SDK L1 ingress is Protocol-based (CDC, MCP client, file/stream adapters). The *normalized-event-envelope* idea (`si_framework/models/enrichable_observer_event.py`, dual adapters for two edge shapes) is separately inheritable as a candidate pattern (next row). |
| Normalized enrichable-event contract with per-source adapters at ingress | `packages/si-framework/src/si_framework/models/enrichable_observer_event.py` | candidate pattern | One resolution of L1 event-envelope normalization across heterogeneous sources. |
| Provider-agnostic LLM access via LiteLLM with per-zone provider overrides in config | `config/zone_policies.yaml` LLM/VLM provider blocks; `si_framework/services/llm_service.py` | candidate pattern | Data point for D-IMPL-09 (LLMClientProtocol vs direct vendor SDK). |
| Pluggable classifier/encoder behind a Protocol with factory registration (swappable without code changes) | `packages/si-framework/src/si_framework/models/vehicle_classifier.py` (`VehicleClassifierABC`), `packages/si-inference/src/si_inference/vehicle_classifier.py`, `si_framework/services/vehicle_classifier_factory.py` | candidate pattern | Protocol + factory + registry shape matches CCF "prefer Protocols, ship reference impls" principle (§11); relevant to D-IMPL-07. |
| Scoring/inference as separate HTTP services (scoring farm) | `packages/si-inference/src/si_inference/` (`classifier_server.py`, `multisource_server.py`) | domain-specific — do not inherit | CV-scoring deployment topology; not an SDK concern (production topology is out of scope, CCF CLAUDE.md §13). |
| Conversation layer: intent-classified queries over the fabric with deterministic path for safety-critical intents and context-debt warnings prepended to every answer | `packages/si-conversation/src/si_conversation/`, `packages/si-pool-safety/src/si_pool_safety/conversation/` | domain-specific — do not inherit | The Conversational Reporting Layer is explicitly out of SDK v0 scope (CCF CLAUDE.md §13); debt-warning-on-serve is noted as an interesting D_c surfacing idea for the Experience Layer, but inherits nothing. |
| Web UI / dashboard / Alexa surfaces | `packages/si-web-ui/`, `packages/si-conversation/` (Alexa), `packages/si-app/` (frontend/deploy app shell) | domain-specific — do not inherit | UX surfaces are user-built reference integrations per CCF CLAUDE.md §8.3; no CCF-relevant mechanism beyond what other rows already capture. |
| Prompt-injection mitigation: delimiting untrusted narrative inputs with explicit BEGIN/END markers before LLM consolidation | `si_framework/processors/` (LLMConsolidationProcessor; documented in Homecams CLAUDE.md §6) | candidate pattern | Semantic-stage input-hygiene data point for the Algorithmic ⇄ Semantic boundary. |
| Conservative floor rule: consolidated assessment never below max per-input severity | LLMConsolidationProcessor (`packages/si-framework/src/si_framework/processors/`) | domain-specific — do not inherit | A safety-domain policy value (bias direction), not mechanism; the *mechanism* of policy-constrained consolidation is covered by the policy rows. |

Package coverage note: `si-models` (`packages/si-models/` — binary/identity model weights and
metadata) and `si-ingest-server` (`packages/si-ingest-server/` — edge ingest HTTP service)
yielded no CCF-relevant patterns beyond deployment plumbing already covered above;
`si-app` is covered by the UX-surfaces row. All nine `si-*` packages plus
`start_ccf_agent.py` / `start_property_intelligence.py` were surveyed.

## MongoDB Persistence — ArtifactStore (§7.4) Triangulation Data Point

Derived entirely from Homecams source code (no client install, no live query, per the
RESEARCH.md zero-install route). Collection names and document shapes only — no
connection details and no data records appear here. Overall marker for the persistence
*pattern*: `candidate pattern` (a single system-of-record with typed repositories, a
declared single writer per collection family, and index-as-invariant discipline);
the specific collection inventory and all field values are
`domain-specific — do not inherit`.

**Connection management (mechanism):** a single `MongoDataService`
(`packages/si-pool-safety/src/si_pool_safety/services/mongo_data_service.py`) owns the
pymongo client lifecycle (lazy creation, connection pooling, health check); repositories
receive the database handle from it via the `ServiceContainer`
(`services/service_container.py`). `candidate pattern` — substrate-handle injection is
the same shape as the SDK's storage-Protocol + DI-at-boot posture.

**Repository layer (mechanism):** typed repositories per collection, with a shared
`TenantScopedRepository` base (`packages/si-framework/src/si_framework/repositories/tenant_scoped.py`)
making tenant filtering structural rather than conventional. `candidate pattern`
(D-IMPL-05 data point).

**CCF artifact classes persisted, by collection family** (names/shapes as written in
repository code and Homecams CLAUDE.md §5; counts omitted — live data is out of scope):

| CCF artifact class | Collection(s) | Shape / indexing (from source) | Marker |
|---|---|---|---|
| Context Graph state per cycle | `context_graphs` | Per-cycle G(E,R,T,P,Π,L) documents with `fidelity_level` (full/compressed/tombstoned) — `si_framework/repositories/context_graph_repository.py` | candidate pattern (fidelity field); collection inventory domain-specific — do not inherit |
| Entity/edge registry | `graph_entities` | Idempotent upsert keyed on compound unique index `(tenant_id, entity_uri)` (`graph_entities_tid_uri`); repeat hits `$addToSet`-append to `lineage[]` and advance `last_seen_at`; index absence raises at boot (fail-fast index-as-invariant) — `si_pool_safety/repositories/graph_entities_repository.py` | candidate pattern — directly mirrors whitepaper §7.3 compound-index + multi-source lineage accumulation |
| Relationship/policy edges | `context_edges` | Triple-shaped docs `(tenant_id, subject_id, predicate, object_id, timestamp)`; forward/reverse/predicate-window traversal indexes plus a unique natural-key index (`uniq_edge`); idempotent bulk insert with in-batch dedup — `si_framework/repositories/context_edge_repository.py` | candidate pattern |
| Materialized projection outputs | `projection_cache` | TTL index governs lifecycle (docs expire at explicit expiration timestamp); pure-`$set` upsert keyed on `product_id`; deliberately NO lineage index — lineage queries hit `graph_entities` only (architectural boundary between graph state and projection cache) — `si_framework/repositories/projection_cache_repository.py` | candidate pattern |
| Discriminator quarantine | `context_products_unclassified` | Quarantine for documents that fail the graph-state vs projection-output discriminator during the v5.0 collection split | candidate pattern (migration-safety idea); do-not-inherit as a permanent surface |
| Assembled fabric instances | `cognitive_context_fabrics` | `activated_product_uris` written by the enrichment worker — `si_framework/repositories/fabric_activation_repository.py` | domain-specific — do not inherit (fabric persistence shape is bound to Homecams' MQTT pipeline) |
| Decision Replay records | `decision_replay_records` | Full five-dimension decision state persisted per significant decision; alerts additionally embed full dynamic context for self-contained replay — `si_framework/reporting/replay_service.py` | candidate pattern — key ArtifactStore triangulation row: replay records as immutable persisted artifacts |
| Half-life state | `context_half_life_states` | Per-observation-type decay tracking — `si_framework/services/context_half_life_service.py` | candidate pattern (mechanism); observation types domain-specific — do not inherit |
| Perception/intelligence time series | `observer_states`, `model_scores`, `monitor_summaries`, `states`, `alerts`, `alert_dispatches` | Timeseries collections (append-only) with a separate mutable regular collection (`alert_dispatches`) for lifecycle state, because timeseries collections cannot mutate | candidate pattern (append-only-vs-mutable split); collections domain-specific — do not inherit |
| Reference/config data | `cameras`, `camera_topology`, `persons`, `zones`, `vehicles`, `vehicle_embeddings`, `models` | Tenant-scoped (`tenant_id`) reference registries | domain-specific — do not inherit |

**Single-writer discipline over the store:** the enrichment worker is the declared sole
writer of `graph_entities` / `projection_cache` / `context_products_unclassified` /
`context_edges` / `cognitive_context_fabrics.activated_product_uris`
(`si_pool_safety/enrichment_worker/worker.py`; ADR in Homecams CLAUDE.md §3.2/§5.8);
the hot-path agent writes only its own ingest collections. `candidate pattern` — a
process-topology realization of "the store is a substrate behind mechanism, never a
second writer" (CCF CLAUDE.md §7.4).

**Versioning/immutability observations relevant to D-IMPL-26:** Homecams versions by
embedded fields (model version, prompt template version, policy version inside replay
records) rather than content-addressing or versioned URIs; artifacts are effectively
immutable by append-only timeseries semantics plus the compression/tombstone lifecycle.
This is one data point for the ArtifactStore addressing decision, not a default.

**Cautionary contrast:** Homecams treats MongoDB as the mandated single system-of-record
("MongoDB is the single system-of-record" — Homecams CLAUDE.md §1.4). The SDK must NOT
inherit a mandated substrate: persistence goes behind `ArtifactStoreProtocol` and the
graph-storage Protocol (D-IMPL-02/26/27), with MongoDB merely one possible user-supplied
backend. Marker for substrate mandate: `domain-specific — do not inherit`.

## Open Questions (unnumbered)

These record places where the whitepaper is silent and Homecams shows one working
resolution. Per CCF CLAUDE.md §2.1, each is a data point requiring a decision — never a
default to inherit. The synthesis plan should fold these into the D-IMPL log.

- **Operator intermediate materialization:** Homecams caches materialized projection
  outputs in a TTL-indexed `projection_cache` collection separate from graph state
  (`si_framework/repositories/projection_cache_repository.py`). Should the SDK's operator
  DAG planner support materialized intermediates, and where do they persist (interacts
  with D-IMPL-06/D-IMPL-27)?
- **Projection-plan selection inputs:** Homecams derives a projection plan from the
  (agent role, decision intent, product contract) triple. Is this triple the SDK's
  canonical projection-selection signature, or is intent modeling out of scope?
- **Replay-record compression lifecycle:** Homecams' three-tier fidelity
  (full/compressed/tombstoned with never-compress exceptions) is one resolution of
  year-scale replay storage (D-IMPL-06). Does the SDK ship a fidelity-lifecycle
  mechanism, or leave retention entirely to the ArtifactStore implementation?
- **Sync/async runtime split:** Homecams' operationally-proven pattern is a purely
  synchronous hot path plus an out-of-process async enrichment worker. Does this inform
  D-IMPL-04(b) (sync/async posture of the SDK runtime)?
- **Definition-artifact format precedent:** Homecams uses YAML agent/task definitions +
  Jinja2 prompt templates with a CI grep guard. Is this the D-IMPL-28 starting point, or
  does the SDK adopt a schema-validated format instead?
- **Live MongoDB metadata query:** Is a live read-only MongoDB metadata query wanted
  (would require approving a pymongo install)? The source-code route above satisfied the
  §2.1 triangulation intent with zero installs; a live query would only add
  collection-level stats/index metadata. For Dave via the synthesis plan.

---

## Live MongoDB Metadata Query (D-IMPL-51 — resolved, executed 2026-07-25)

Dave approved a live read-only metadata query at the Phase R gate. Executed via the Homecams venv's existing pymongo (no install) against the Homecams instance with `readPreference=secondaryPreferred`; listing operations only (server_info, list_database_names, list_collection_names, estimated_document_count, list_indexes). No document reads, no writes, no credentials recorded. Server: MongoDB 8.0.19, database `rtdetect`, 55 collections.

### CCF-relevant collections (triangulation for ArtifactStore §7.4, D-IMPL-26/27)

| Collection | ~Docs | Key indexes | CCF mapping |
|---|---|---|---|
| `context_edges` | 319,226 | `uniq_edge (tenant_id, subject_id, predicate, object_id, timestamp) UNIQUE`; `forward_traverse`/`reverse_traverse`/`predicate_window` all tenant-prefixed with `timestamp: -1` | L3 graph R-dimension; confirms tenant-first compound-unique upsert identity and bidirectional traversal indexing (INV-CH7 graph entries) |
| `graph_entities` | 51,256 | `_id` | L3 E-dimension |
| `context_graphs` | 66,658 | `_id` | Graph snapshots / assembled state |
| `cognitive_context_fabrics` | 91,129 | `_id` | Assembled fabric state records |
| `zone_context_fabrics` | 138,639 | `_id` | Domain-scoped fabric partitions (domain-specific — do not inherit the zone partitioning) |
| `context_products_retired_20260524` | 20,866 | `uniq_product_id UNIQUE`; `tenant_type_observed (tenant_id, product_type, observed_at -1)`; `tenant_lineage (tenant_id, lineage_graph)` | L6 Context Products at rest; suffix-dated retirement = logical supersession via collection rotation (candidate pattern: versioned retirement; the date-suffix mechanics are domain ops, do not inherit) |
| `projection_cache` | 122,821 | `uniq_product_id UNIQUE`; TTL-style `projection_cache_ttl_expires (expires_at)`; `tenant_perspective_cam_type_observed (tenant_id, perspective.cam_id, product_type, observed_at -1)` | L5 Π output caching with perspective-conditioned index — live confirmation that perspective is a first-class query axis |
| `decision_replay_records` | 70,667 | `_id` | §7.10 five-dimension replay store — replay at scale is real (70k records) |
| `classification_lineages` | 10,626 | `_id` | L-dimension lineage records |
| `context_half_life_states` | 19,277 | `_id` | §7.7 λ_c decay state materialized per observation |
| `context_debt` | 11 | `_id` | §7.7 D_c records (small: debt is computed, sparsely persisted) |
| `dynamic_context_assessments` | 7,411 | `_id` | CAR/debt assessment outputs |
| `tenants` | 1 | `_id` | Single-tenant deployment; `tenant_id` still first in every compound index — live confirmation of the multi-tenant-ready single-tenant posture (D-IMPL-05 data point) |

### Live-query observations for Phase D

1. **`tenant_id` leads every governance-bearing compound index** even in a one-tenant deployment — supports the `tenant_id`-first-class reading of D-IMPL-05.
2. **Uniqueness discipline matches the whitepaper §7.3 commitment**: unique compound identity on edges (`uniq_edge`) and products (`uniq_product_id`), with append-only + supersession realized via collection rotation (`*_retired_YYYYMMDD`) rather than in-place deletes.
3. **TTL enforcement is index-level** (`expires_at` on `projection_cache`, `chat_sessions` 30d TTL) — a data point for D-IMPL-31 (TTL locus).
4. **Quarantine collection exists** (`context_products_unclassified` with tenant/observed index) — admission-gating pattern consistent with Control-Plane-verified admission (candidate pattern).
5. High-volume operational collections (`heartbeats` 1.5M, `model_scores` 768k, `observer_states` 612k, `zone_processor_results` 563k) are domain telemetry — do not inherit.
