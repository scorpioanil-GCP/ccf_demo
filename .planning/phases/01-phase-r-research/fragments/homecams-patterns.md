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
