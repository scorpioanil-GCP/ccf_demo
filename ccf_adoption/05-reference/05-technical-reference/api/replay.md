# Decision Replay — SDK 1.0.2 Signatures

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Exact public shapes for Decision Replay, record provenance, reconstruction, and replay lookup surfaces.

This page is generated from `docs/surface/v0.2-surface.json` at `v1.0.2`. It is a lookup appendix; use the focused reference pages for semantics and examples.

> SDK 1.0.2 is tagged. Release status, deployment verification and the prior bank delivery remain separate; see [migration requirements](../MIGRATION_AND_LIMITATIONS.md).

## `ccf.replay.correlation`

- `ExternalTraceProviderProtocol` — **class**
  - `(*args, **kwargs)`
- `NoOpTraceProvider` — **class**
  - `()`
- `TraceCorrelation` — **contract**
  - `{"trace_id":"<class 'str'>","trace_provider":"<class 'str'>"}`
- `TraceCorrelationHook` — **class**
  - `(*, provider: 'ExternalTraceProviderProtocol') -> 'None'`

## `ccf.replay.engine`

- `CompositeReplayEnvironment` — **class**
  - `(*args, **kwargs)`
- `ERASED_SITE_CHILD_CONTRACT` — **constant**
  - `str`
- `ERASED_SITE_DECISION_RECORD` — **constant**
  - `str`
- `ERASED_SITE_REPLAY_ARTIFACT` — **constant**
  - `str`
- `ERASED_SITE_RETAINED_CHILD_QUESTION` — **constant**
  - `str`
- `ErasedContent` — **contract**
  - `{"content_address":"<class 'str'>","erased_at":"datetime.datetime | None","erasure_record_address":"str | None","reason":"str | None","site":"<class 'str'>"}`
- `ErasedReplayOutcome` — **contract**
  - `{"erased_content":"tuple[ccf.replay.engine.ErasedContent, ...]","record":"ccf.replay.record.DecisionReplayRecord | None","record_content_address":"<class 'str'>"}`
- `RefusalReplayOutcome` — **contract**
  - `{"assembly_refusal":"<class 'str'>","child_contract_addresses":"tuple[str, ...]","erased_content":"tuple[ccf.replay.engine.ErasedContent, ...]","graph_snapshot_id":"<class 'str'>","record":"<class 'ccf.replay.record.DecisionReplayRecord'>","record_content_address":"<class 'str'>"}`
- `ReplayDivergence` — **class**
  - `type`
- `ReplayEnvironment` — **class**
  - `(*args, **kwargs)`
- `ReplayError` — **class**
  - `type`
- `ReplayGenerationMismatch` — **class**
  - `(*, contract: 'type[CCFContract]', fields: 'tuple[str, ...]', content_address: 'str') -> 'None'`
- `ReplayOutcome` — **contract**
  - `{"erased_content":"tuple[ccf.replay.engine.ErasedContent, ...]","graph_snapshot_id":"<class 'str'>","product":"<class 'ccf.products.contract.ContextProductContract'>","product_content_address":"<class 'str'>","record":"<class 'ccf.replay.record.DecisionReplayRecord'>","record_content_address":"<class 'str'>"}`
- `ReplayRecordKindMismatch` — **class**
  - `type`
- `ReplayResolutionClaimMismatch` — **class**
  - `(*, content_address: 'str', claimed_reason: 'str', pinned: 'tuple[tuple[str, str, str], ...]') -> 'None'`
- `ReplayUnresolvable` — **class**
  - `type`
- `replay` — **function**
  - `(*, record_address: 'str', store: 'ArtifactStoreProtocol', reader: 'GraphReader', control_plane: 'ControlPlaneProtocol', environment: 'ReplayEnvironment') -> 'ReplayOutcome | ErasedReplayOutcome'`
- `replay_refusal` — **function**
  - `(*, record_address: 'str', store: 'ArtifactStoreProtocol', reader: 'GraphReader', control_plane: 'ControlPlaneProtocol', environment: 'ReplayEnvironment') -> 'RefusalReplayOutcome | ErasedReplayOutcome'`
- `resolve_artifact` — **function**
  - `(*, store: 'ArtifactStoreProtocol', content_address: 'str', contract: 'type[_ArtifactT]') -> '_ArtifactT'`
- `resolve_artifact_at_uri` — **function**
  - `(*, store: 'ArtifactStoreProtocol', uri: 'str', contract: 'type[_ArtifactT]') -> '_ArtifactT'`
- `retained_child_question` — **function**
  - `(*, store: 'ArtifactStoreProtocol', row: 'ChildResolution') -> 'ChildQuestionIdentity'`

## `ccf.replay.environment`

- `RecordedEnvironment` — **class**
  - `(*, record: 'DecisionReplayRecord', opened: 'OpenedProduct', fabric: 'BootedFabric') -> 'None'`
- `RecordedEnvironmentUnbuildable` — **class**
  - `type`

## `ccf.replay.evidence`

- `EVIDENCE_SCHEMA_VERSION` — **constant**
  - `int`
- `EvidenceEntry` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","decided_at":"<class 'datetime.datetime'>","graph":"str | None","graph_required":"<class 'bool'>","graph_sha256":"str | None","outcome":"typing.Literal['served', 'refused']","parameters":"dict[str, JsonValue]","product_class":"<class 'str'>","product_version":"<class 'str'>","record_address":"<class 'str'>","refusal_reason":"str | None","schema_version":"typing.Literal[1]","subject":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `PendingEvidence` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","graph":"<class 'str'>","parameters":"dict[str, JsonValue]","product_class":"<class 'str'>","product_version":"<class 'str'>","schema_version":"typing.Literal[1]","started_at":"<class 'datetime.datetime'>","subject":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ReplayEvidenceAltered` — **class**
  - `(*, record_address: 'str', path: 'str', expected_sha256: 'str', found_sha256: 'str') -> 'None'`
- `ReplayEvidenceIndex` — **class**
  - `(*, evidence_root: 'Path', index_root: 'Path', tenant_id: 'str') -> 'None'`
- `ReplayEvidenceUnavailable` — **class**
  - `(*, record_address: 'str', detail: 'str', path: 'str | None' = None) -> 'None'`
- `file_sha256` — **function**
  - `(path: 'Path') -> 'str'`
- `require_record_address` — **function**
  - `(record_address: 'str') -> 'str'`

## `ccf.replay.inspection`

- `DecisionExplanation` — **contract**
  - `{"as_of":"datetime.datetime | None","asked_at":"<class 'datetime.datetime'>","debt":"str | None","debt_signal":"str | None","decided_at":"<class 'datetime.datetime'>","entities_touched":"int | None","graph_snapshot_id":"str | None","operators":"tuple[str, ...]","outcome":"typing.Literal['served', 'refused']","parameters":"tuple[ccf.replay.inspection.ParameterOrigin, ...]","policies":"tuple[ccf.replay.inspection.PolicyVersion, ...]","principal_id":"<class 'str'>","product_class":"<class 'str'>","product_version":"<class 'str'>","read_graph":"<class 'bool'>","record_address":"<class 'str'>","refusal_detail":"str | None","refusal_kind":"str | None","refusal_reason":"str | None","relationships_touched":"int | None","role":"<class 'str'>","subject":"<class 'str'>"}`
- `ParameterOrigin` — **contract**
  - `{"authority":"<class 'str'>","name":"<class 'str'>","source":"<class 'str'>","source_version":"str | None","value":"JsonValue"}`
- `PolicyVersion` — **contract**
  - `{"key":"<class 'str'>","version":"<class 'str'>"}`
- `explain_decision` — **function**
  - `(*, store: 'ArtifactStoreProtocol', evidence: 'ReplayEvidenceIndex', record_address: 'str') -> 'DecisionExplanation'`

## `ccf.replay.provenance`

- `RecordNotFiledByRecordWriter` — **class**
  - `type`
- `UnattributableRecordStore` — **class**
  - `type`
- `filed_by_record_writer` — **function**
  - `(store: 'object', *, content_address: 'str', tenant_id: 'str') -> 'bool'`
- `require_filed_by_record_writer` — **function**
  - `(store: 'object', *, content_address: 'str', tenant_id: 'str') -> 'None'`

## `ccf.replay.record`

- `CHILD_ADMITTED` — **constant**
  - `str`
- `CHILD_OUTCOME_STATUSES` — **constant**
  - `frozenset`
- `ChildResolution` — **contract**
  - `{"child_admitted_at":"datetime.datetime | None","child_asked_at":"datetime.datetime | None","child_content_address":"str | None","child_debt":"decimal.Decimal | None","child_debt_factors":"ccf.halflife.assessment.DebtFactors | None","child_eligibility_assertion_address":"str | None","child_eligibility_checked_at":"datetime.datetime | None","child_expires_at":"datetime.datetime | None","child_graph_snapshot_at":"datetime.datetime | None","child_lineage_ref":"str | None","child_operators_invoked":"frozenset[str] | None","child_policy_bundle_versions":"frozenset[str] | None","child_question_address":"str | None","child_question_ref":"str | None","child_replay_ref":"str | None","child_reported_address":"str | None","child_schema_name":"str | None","child_schema_version":"str | None","child_ttl_anchor":"str | None","child_ttl_anchor_at":"datetime.datetime | None","eligibility_basis":"str | None","grant_hash":"str | None","outcome_status":"<class 'str'>","producer_id":"str | None","producer_refusal_key":"str | None","producer_refusal_kind":"str | None","producer_refusal_reason":"str | None","producer_registration_address":"str | None","producer_server":"str | None","producer_tenant":"str | None","producing_fabric":"str | None","producing_skill_name":"str | None","producing_skill_version":"str | None","refusal_ref":"str | None","required":"<class 'bool'>","required_product_class":"<class 'str'>"}`
- `ContentGenerationPath` — **contract**
  - `{"assembly_refusal":"<class 'str'>","child_resolutions":"tuple[ccf.replay.record.ChildResolution, ...]","computed_empty":"ccf.products.contract.ComputedEmptyFinding | None","debt":"ccf.halflife.assessment.DebtAssessment | None","debt_evidence":"tuple[ccf.halflife.assessment.DebtEvidencePointer, ...]","disclosure_decision":"<class 'str'>","executed_seeds":"tuple[str, ...] | None","graph_query_sequence":"tuple[str, ...]","issuance":"<class 'str'>","obligation_in_force":"<class 'str'>","operator_plan":"tuple[str, ...]","plan_id":"<class 'str'>","product_content_address":"<class 'str'>","refusal_seam":"<class 'str'>","request":"ccf.products.request.ProductRequest | None","served_at":"datetime.datetime | None","source_refresh_recency":"ccf.halflife.assessment.SourceRefreshWindow | None","steps":"tuple[ccf.projection.engine.ExecutionStep, ...]","subject_withholding":"<class 'str'>","ttl_anchor_at":"datetime.datetime | None","workflow_step_sequence":"<class 'str'>"}`
- `ContextFabricSnapshot` — **contract**
  - `{"graph_snapshot_id":"<class 'str'>","source_attestation":"ccf.graph.protocols.SourceAttestation | None","store_snapshot_pin":"<class 'ccf.graph.protocols.StoreSnapshotPin'>","store_watermark":"<class 'str'>","temporal_boundary":"<class 'datetime.datetime'>","tenant_id":"<class 'str'>","touched_entities":"tuple[str, ...]","touched_relationships":"tuple[str, ...]"}`
- `DecisionReplayRecord` — **contract**
  - `{"content_generation_path":"<class 'ccf.replay.record.ContentGenerationPath'>","context_fabric_snapshot":"<class 'ccf.replay.record.ContextFabricSnapshot'>","model_version":"<class 'ccf.replay.record.ModelVersionRecord'>","perspective_conditioning":"<class 'ccf.replay.record.PerspectiveConditioning'>","policy_bindings":"<class 'ccf.replay.record.PolicyBindingsSnapshot'>","recorded_at":"<class 'datetime.datetime'>","tenant_id":"<class 'str'>"}`
- `FalseAssemblyRefusalClaimError` — **class**
  - `type`
- `HarnessTrace` — **contract**
  - `{"harness_id":"<class 'str'>","input_tokens":"<class 'int'>","model_version":"<class 'str'>","output_tokens":"<class 'int'>","trace_id":"<class 'str'>","trace_provider":"<class 'str'>"}`
- `MODE_1_MODEL_VERSION` — **constant**
  - `str`
- `ModelVersionRecord` — **contract**
  - `{"assembly_mode":"typing.Literal['algorithmic', 'llm_packaged', 'swarm_assembled']","harness_trace":"<class 'ccf.replay.record.HarnessTrace'>","model_version":"<class 'str'>","packaging_trace":"<class 'ccf.replay.record.PackagingTrace'>"}`
- `NO_ADAPTER` — **constant**
  - `str`
- `NO_AGENT_DEFINITION` — **constant**
  - `str`
- `NO_ASSEMBLER` — **constant**
  - `str`
- `NO_ASSEMBLY_REFUSAL` — **constant**
  - `str`
- `NO_DISCLOSURE_DECISION` — **constant**
  - `str`
- `NO_FABRIC_READ` — **constant**
  - `str`
- `NO_GRANTS_SET_HASH` — **constant**
  - `str`
- `NO_GRAPH_QUERIES` — **constant**
  - `tuple`
- `NO_HARNESS` — **constant**
  - `str`
- `NO_HARNESS_TRACE` — **constant**
  - `HarnessTrace`
- `NO_HITL_ACTIONS` — **constant**
  - `str`
- `NO_ISSUANCE` — **constant**
  - `str`
- `NO_PACKAGING` — **constant**
  - `str`
- `NO_PACKAGING_TRACE` — **constant**
  - `PackagingTrace`
- `NO_PRODUCT_ADDRESS` — **constant**
  - `str`
- `NO_REFUSAL_SEAM` — **constant**
  - `str`
- `NO_REQUEST_RESOLUTION` — **constant**
  - `str`
- `NO_ROLE_RESOLVED` — **constant**
  - `str`
- `NO_WORKFLOW_TRACE` — **constant**
  - `str`
- `PackagingTrace` — **contract**
  - `{"model_version":"<class 'str'>","output_hash":"<class 'str'>","prompt_artifact_hash":"<class 'str'>","prompt_artifact_uri":"<class 'str'>","temperature":"<class 'str'>"}`
- `PerspectiveConditioning` — **contract**
  - `{"agent_definition_hash":"<class 'str'>","agent_definition_uri":"<class 'str'>","archetype_composition":"tuple[str, ...]","assembler_id":"<class 'str'>","assembler_version":"<class 'str'>","delegation_chain":"tuple[str, ...]","grant_set_hash":"<class 'str'>","principal_id":"<class 'str'>","role":"<class 'str'>"}`
- `PolicyBinding` — **contract**
  - `{"key":"<class 'str'>","version":"<class 'str'>"}`
- `PolicyBindingsSnapshot` — **contract**
  - `{"bindings":"tuple[ccf.replay.record.PolicyBinding, ...]","graph_adapter":"<class 'str'>","graph_adapter_version":"<class 'str'>","graph_secret_refs":"tuple[str, ...]","hitl_actions":"<class 'str'>","request_resolution":"<class 'str'>","survivor_cap":"int | None"}`
- `REFUSAL_SEAMS` — **constant**
  - `frozenset`
- `ResolutionNotApplicable` — **contract**
  - `{"reason":"typing.Literal['no-resolution-step', 'refused-before-resolution']"}`
- `ResolutionNotApplicableReason` — **function**
  - `typing.Literal['no-resolution-step', 'refused-before-resolution']`
- `UNSTATED_SUBJECT_WITHHOLDING` — **constant**
  - `str`
- `build_replay_record` — **function**
  - `(*, execution: 'ExecutionResult | None', product: 'ContextProductContract | None', perspective: 'Perspective', policy_bindings: 'tuple[PolicyBinding, ...]', assembly_mode: 'AssemblyMode', recorded_at: 'datetime', resolution: "'EffectiveRequest | ResolutionNotApplicable'", refusal: "'RefusalEnvelope | None'" = None, tenant_id: 'str | None' = None, assembler_id: 'str | None' = None, assembler_version: 'str | None' = None, disclosure: 'str | None' = None, agent_conditioning: 'PerspectiveConditioning | None' = None, harness_trace: 'HarnessTrace | None' = None, packaging_trace: 'PackagingTrace | None' = None, served_at: 'datetime | None' = None, hitl_actions: 'str | None' = None, workflow_step_sequence: 'str | None' = None, assembly_refusal: 'str | None' = None, refusal_seam: 'str' = 'not-seam-held', adapter: 'AdapterPin | None' = None, request: 'ProductRequest | None' = None, child_resolutions: 'tuple[ChildResolution, ...]' = (), issuance: 'str | None' = None, subject_withholding: 'str | None' = None) -> 'DecisionReplayRecord'`
- `mint_assembly_refusal` — **function**
  - `(outcome: "'AssemblyOutcome | ProductRequestViolation | RefusalEnvelope | CCFContract'", *, claimed: 'str | None' = None) -> 'str'`
- `new_issuance` — **function**
  - `() -> 'str'`

## `ccf.replay.serve`

- `CapabilityForgeryError` — **class**
  - `type`
- `DeliveryCapability` — **class**
  - `(replay_ref: 'ArtifactRef', token: 'object') -> 'None'`
- `ProductRecordMismatch` — **class**
  - `type`
- `QueryPinMismatch` — **class**
  - `type`
- `QueryPinReferenceMismatch` — **class**
  - `(*, fields: 'tuple[str, ...]') -> 'None'`
- `QueryPinWriter` — **class**
  - `(*, authorized: 'Authorized[ReplayMint]', store: 'ArtifactStoreProtocol') -> 'None'`
- `ReplayReferenceMismatch` — **class**
  - `(*, fields: 'tuple[str, ...]') -> 'None'`
- `ReplayTenantMismatch` — **class**
  - `type`
- `ReplayWriter` — **class**
  - `(*, authorized: 'Authorized[ReplayMint]', store: 'ArtifactStoreProtocol') -> 'None'`
- `ServedProduct` — **contract**
  - `{"product":"<class 'ccf.products.contract.ContextProductContract'>","replay_ref":"<class 'ccf.artifacts.protocol.ArtifactRef'>"}`
- `record_refusal` — **function**
  - `(*, record: 'DecisionReplayRecord', replay_writer: 'ReplayWriter') -> 'ArtifactRef'`
- `serve` — **function**
  - `(*, product: 'ServableProduct', record: 'DecisionReplayRecord', replay_writer: 'ReplayWriter', query_pin_writer: 'QueryPinWriter | None' = None, executed_queries: 'tuple[GraphQuery, ...]' = ()) -> 'ServedProduct'`

## `ccf.replay.snapshots`

- `SnapshotPinUnresolvable` — **class**
  - `type`
- `SnapshotReader` — **class**
  - `(*, reader: 'GraphReader', snapshot: 'ContextFabricSnapshot') -> 'None'`
- `SnapshotScopeViolation` — **class**
  - `type`
- `snapshot_of_execution` — **function**
  - `(*, execution: 'ExecutionResult', tenant_id: 'str', temporal_boundary: 'datetime') -> 'ContextFabricSnapshot'`
