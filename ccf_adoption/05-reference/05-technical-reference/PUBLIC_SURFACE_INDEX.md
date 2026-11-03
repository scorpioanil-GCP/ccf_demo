# Current Public Surface Index

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Generated mechanically from `docs/surface/v0.2-surface.json` on current SDK `main`.

The manifest contains **243 public modules**. The v1.0.1 manifest contained **217**.

This is an index, not a tutorial. A name appears here because the committed current-main surface manifest records it as public.

## Reading this page

- Prefer package-level exports where the SDK supplies them.
- For submodule-only public names, import from the module shown.
- Do not infer a public contract from implementation symbols absent from the manifest.
- This surface is the released `v1.0.2` tag; it matches the merged main runtime inspected on 18 October 2026.


## Consumer API

| Module | Current public names |
| --- | --- |
| `ccf.client` | `BindingError`, `ProductClient`, `Result`, `TransportError` |
| `ccf.client.adapters.binding_document` | `BINDING_DOCUMENT_NAME`, `BindingDocument`, `DATA_KEYS`, `DebtDeclaration`, `ErasureAuthorityDeclaration`, `OPTIONAL_KEYS`, `QuestionDeclaration`, `REFERENCE_KEYS`, `RULED_OUT_KEYS`, `conforming_plan_factory`, `load_binding_document`, `load_reference`, `looks_like_a_reference` |
| `ccf.client.adapters.inprocess` | `InProcessAdapter`, `SCHEME`, `reset_boot_cache` |
| `ccf.client.adapters.mcp_stdio` | `McpStdioAdapter`, `SCHEME` |
| `ccf.client.binding` | `AdapterFactory`, `BINDING_ENV_VAR`, `SCHEME_REGISTRY`, `adapter_for_binding`, `resolve_binding`, `split_binding` |
| `ccf.client.client` | `ProductClient` |
| `ccf.client.codec` | `DecodedOutcome`, `check_outcome`, `decode_outcome`, `encode_outcome`, `verify_content_address` |
| `ccf.client.errors` | `BindingError`, `RefusedResultError`, `TransportError` |
| `ccf.client.result` | `GUARDED_FIELDS`, `PRE_ASSEMBLY_FIELDS`, `Refusal`, `Result` |
| `ccf.client.wire` | `TransportAdapter`, `WireOutcome`, `WireRequest` |


## Context Products

| Module | Current public names |
| --- | --- |
| `ccf.products.bind` | `refuse_bound_payload`, `resolve_declared_payload_schema` |
| `ccf.products.child_resolver` | `ChildArguments`, `ChildQuestion`, `ChildQuestionReferenceMismatch`, `ChildQuestions`, `ChildRecordAltered`, `ChildRecordMismatch`, `GrantBoundChildResolver`, `MalformedDoorAnswer`, `QuestionBoundChildResolver`, `QuestionRetentionUnauthorized` |
| `ccf.products.composite` | `ADMITTED_CHILD_CONTRACT_CLASS`, `AdmittedChild`, `AgentConditionedChildResolverProtocol`, `AmbiguousProducerError`, `CHILD_QUESTION_CLASS`, `CHILD_REFUSAL_REASONS`, `ChildAcquisition`, `ChildAdmissionBypassError`, `ChildAdmissionRefusal`, `ChildCandidate`, `ChildContractView`, `ChildInvocation`, `ChildOutcomeResolution`, `ChildRefusalReason`, `CompositeAdmissionGate`, `CompositeChildResolverProtocol`, `CompositionOutcome`, `ELIGIBILITY_LOCAL_REGISTER`, `ELIGIBILITY_PRODUCER_ATTESTED`, `ELIGIBILITY_PROVIDER_CONTROLS`, `EligibilityEvidence`, `GATE_CHILD_ADMISSION`, `ProvenanceForgeryError`, `RequestAwareChildResolverProtocol`, `ResolvedProducer`, `child_contract_view`, `compose_children`, `invocation_from_dispatch`, `resolve_child_outcomes`, `resolve_producing_grant` |
| `ccf.products.composition` | `ConstituentValidity`, `EmptyCompositionError`, `ExpiryDerivation`, `MixingRefusal`, `compose_expiry`, `compose_lineage`, `refuse_mixing` |
| `ccf.products.constraints` | `CAPABILITY_TRAVERSAL_DEPTH`, `ConstraintEffectivityConflict`, `ConstraintRefusal`, `PinnedConstraint`, `PolicyConstraintResolver`, `PolicyResolutionConflict`, `REFERENCE_CONSTRAINT_RESOLVER_ID`, `REFERENCE_CONSTRAINT_RESOLVER_VERSION`, `ReferencePolicyConstraintResolver`, `ResolutionOutcome`, `TechnicalCapability`, `applicable`, `constraints_in_force`, `resolve_effective_request` |
| `ccf.products.contract` | `AssemblyMode`, `ChildRequirement`, `ComputedEmptyFinding`, `ConstituentValidityFloors`, `ContextProductContract`, `DeclaredProductGate`, `FreshnessSLA`, `MaxTTL`, `NOT_ADDRESSABLE`, `NOT_DISCOVERABLE`, `NO_PAYLOAD_SCHEMA`, `NO_PRODUCT_GATE`, `NO_REQUEST_CONTRACT`, `NO_SERVE_OBLIGATIONS`, `NO_VALIDITY_FLOORS`, `OptionalAbsenceTreatment`, `ProductAddress`, `ProductClassRegistrationError`, `ProductDiscovery`, `ProductLineage`, `RefusalCause`, `RegisteredProductClass`, `SUBJECT_WITHHOLDING_NEVER`, `SUBJECT_WITHHOLDING_POSSIBLE`, `SeamRefusalCause`, `ServeObligations`, `SubjectWithholding`, `TTLAnchor`, `UNMEASURED_FRESHNESS_SLA`, `register_product_class`, `requirements_declaration_is_coherent`, `version_satisfies_floor` |
| `ccf.products.debt_scorer` | `AssemblyDebtScorer`, `DECLARED_FACTOR_SCORER_ID`, `DECLARED_FACTOR_SCORER_VERSION`, `DeclaredFactor`, `EvidenceAwareFactorScorer`, `ExecutionEvidence`, `emptiness_of` |
| `ccf.products.demonstration_clock` | `DeclaredServeClock`, `DemonstrationServeInstantConflict`, `DemonstrationServeInstantRefused`, `compose_serve_clock` |
| `ccf.products.disclosure` | `DISCLOSURE_FULL`, `DISCLOSURE_LEVELS`, `DISCLOSURE_MINIMAL`, `DisclosureDecision`, `DisclosureLevel`, `EXTERNAL_STATEMENTS`, `INDISTINGUISHABLE_BELOW_FULL`, `PERMITTED_AT_MINIMAL`, `SUPPRESSED_BELOW_FULL`, `TRANSLATED_AT_MINIMAL`, `WITHHELD`, `disclose` |
| `ccf.products.door` | `AnsweredQuestion`, `DoorOutcome`, `PRODUCT_REQUEST_TOOL`, `ProducerAssertion`, `ServedAnswer`, `UngovernedResolverResult`, `WireRequest`, `door_answer`, `door_question`, `door_refusal`, `served_answer` |
| `ccf.products.entitlement` | `PRODUCT_ENTITLEMENT_POLICY`, `PrincipalNotEntitled`, `ProductEntitlementGrant`, `ProductEntitlementPolicy`, `ProductEntitlementViolation`, `product_entitlement_key` |
| `ccf.products.expiry` | `FROM_DECISION`, `FROM_ENTITY_FRESHNESS`, `TTLAnchorResolution`, `TTLAnchorUndeclared`, `refuse_undeclared_ttl_anchor`, `resolve_ttl_anchor`, `valid_from_rows` |
| `ccf.products.gates` | `AttestationRefusal`, `DEBT_TOLERANCE_PARAMETER`, `DeclaredObligationRefusal`, `EmptyOperatorRefusal`, `EvidenceAfterDecisionRefusal`, `GATE_DECLARED_OBLIGATIONS`, `GATE_EMPTY_OPERATOR`, `GATE_LINEAGE_ATTRIBUTABILITY`, `GATE_LINEAGE_EQUALITY`, `GATE_SOURCE_ATTESTATION`, `GATE_TTL_ANCHOR`, `GATE_TTL_BOUNDS`, `GateBypassError`, `GateRefusal`, `LineageAttributionRefusal`, `LineageMismatchRefusal`, `PYDANTIC_MODEL_FORMS`, `ProductInvariantRefusal`, `ServableProduct`, `ServableProductNotAModel`, `TTLAnchorRefusal`, `TTLRefusal`, `ToleranceExceededRefusal`, `refuse_attestation`, `refuse_dependency_invalidation`, `refuse_over_tolerance`, `run_federated_gates`, `run_gates`, `verify_gate_provenance` |
| `ccf.products.payload` | `PayloadSchemaViolation`, `PayloadViolationReason`, `ProductPayloadSchema`, `refuse_payload` |
| `ccf.products.producer` | `ProducerAssertion` |
| `ccf.products.product` | `AcquireProtocol`, `AcquisitionContext`, `AssessProtocol`, `AssessmentContext`, `ChildResolverFactory`, `ConsumerContext`, `DeclaredGrantRefused`, `GrantNotInForce`, `OpenedProduct`, `PopulationAcquireProtocol`, `PopulationAcquisitionContext`, `SourcesNotRead`, `open_product` |
| `ccf.products.provenance` | `AUTHORITIES`, `Authority`, `EffectiveParameter`, `EffectiveRequest`, `OverrideRecord`, `ParameterBound`, `ProvenanceSource` |
| `ccf.products.refusal` | `ErasedContentRefusal`, `GovernedRefusalRaised`, `NON_PRODUCT_REFUSALS`, `NON_VALUE_VIOLATIONS`, `NO_REPLAY_REFERENCE`, `REFUSAL_KINDS`, `RESOLVED_BY_THE_RESOLVER`, `RefusalEnvelope`, `RefusalEvidence`, `RequestIdentity`, `ResolvedByTheResolver`, `ResourceRequestIdentity`, `SourceUnavailableRefusal`, `SubjectUnavailableRefusal`, `TemporalBoundRefusal`, `envelope_for`, `refuse_temporal_bound` |
| `ccf.products.request` | `AnchorAmbiguityRefusal`, `ArgumentDomain`, `NO_REQUEST_CONTRACT`, `PARAMETER_VALUE_FLOOR_EXCLUSIONS`, `PARAMETER_VALUE_FLOOR_V1`, `PARAMETER_VALUE_FLOOR_VERSION`, `PRODUCT_REQUEST_CONTRACT`, `ProductRequest`, `ProductRequestContract`, `ProductRequestViolation`, `ProductRequestViolationReason`, `RelativeDefault`, `SUBJECT_FLOOR_V1`, `SUBJECT_FLOOR_VERSION`, `decode_declared_request`, `refuse_floor`, `refuse_intent`, `refuse_request`, `refuse_request_contract_pin`, `refuse_undeclared_class_default`, `request_seeds` |
| `ccf.products.request_schema` | `render_request_input_schema` |
| `ccf.products.resolver` | `AcquiredFabricReused`, `AcquisitionNeedsAQuestionFabric`, `AcquisitionOverUnverifiableStore`, `AcquisitionSeamProtocol`, `AssemblyDebtScorerProtocol`, `ChildAwareDebtScorerProtocol`, `CompositeNeedsAWithholdingStance`, `CompositeNeedsAnEarlyPolicy`, `CompositePlanFactoryProtocol`, `CompositeWithheldLate`, `DEBT_SCORER_INPUTS`, `EARLY_POLICY_ACQUISITION_REFUSAL`, `EarlyPolicyNeedsRequestAwareChildren`, `GovernedResolver`, `IncompatibleRefusalRecorder`, `InstantAwareDebtScorerProtocol`, `NeverWithholdingContradicted`, `NeverWithholdingNeedsAPositiveDeclaration`, `NeverWithholdingProjectionCanWithhold`, `NonWithholdingPlanFactoryProtocol`, `PackagingTraceProtocol`, `PopulationAcquisitionSeamProtocol`, `PopulationPhaseSharesAnOwner`, `PopulationQuestion`, `PopulationReadInSubjectKeyedPhase`, `ProductGateProtocol`, `ProductNotResolvable`, `ProjectionPlanFactoryProtocol`, `QuestionStoreReopened`, `RefusalRecorderProtocol`, `ReplayRefusalRecorder`, `ResolverOutcome`, `SHARED_OWNER_WALK_DEPTH`, `SHARED_OWNER_WALK_OBJECTS`, `ServedProductResolverProtocol`, `SharedOwnerWalkIncomplete`, `SubjectDisclosingPlanFactoryProtocol`, `UNHELD_SUBJECT_PROBE`, `UNHELD_SUBJECT_PROBE_REFUSAL`, `UndeclaredMechanismClass`, `UndisclosedSubjectAnswered`, `UndisclosedSubjectSubstituteIsHeld`, `UnheldSubjectProbeIsHeld`, `UnmarkedStoreNotPresumedFresh`, `UnsupportedComposition`, `WithholdingClassListedReadable`, `build_governed_resolver`, `declared_refusal_recorder`, `refuse_incompatible_refusal_recorder` |
| `ccf.products.subject_disclosure` | `SubjectDisclosurePolicy` |


## Fabric L1–L5

| Module | Current public names |
| --- | --- |
| `ccf.assembly.worker` | `AssemblyWorker`, `EntityResolutionRule`, `EntityResolutionSpec`, `EntityResolutionStrategy`, `FederatedIngestSpec`, `IdentityRefused`, `IngestResult`, `NO_RESOLVING_RULE`, `RefusedAssertion`, `RelationshipResolutionRule`, `ResolvedEntity`, `SpecDrivenEntityResolution` |
| `ccf.graph.backends.fluree` | `DEFAULT_PARTITION`, `FLUREE_SUBSTRATE`, `FlureeGraphReader`, `FlureeGraphStore`, `FlureePinAhead`, `MAX_DEPTH_CEILING`, `MAX_QUERY_BODY_BYTES` |
| `ccf.graph.backends.fluree_write` | `FlureeConnection`, `FlureeGraphWriter`, `REGISTRATION` |
| `ccf.graph.backends.memory` | `MemoryGraphReader`, `MemoryGraphStore` |
| `ccf.graph.backends.memory_write` | `MemoryConnection`, `MemoryGraphWriter`, `REGISTRATION` |
| `ccf.graph.backends.mongo` | `DEFAULT_DATABASE`, `DEFAULT_PARTITION`, `MongoGraphReader`, `MongoGraphStore` |
| `ccf.graph.backends.mongo_write` | `MongoConnection`, `MongoGraphWriter`, `REGISTRATION` |
| `ccf.graph.backends.neo4j` | `DEFAULT_PARTITION`, `MAX_DEPTH_CEILING`, `Neo4jGraphReader`, `Neo4jGraphStore` |
| `ccf.graph.backends.neo4j_write` | `Neo4jConnection`, `Neo4jGraphWriter`, `REGISTRATION` |
| `ccf.graph.backends.postgres` | `DEFAULT_SCHEMA`, `ENTITY_KIND`, `PostgresGraphReader`, `PostgresGraphStore`, `RELATIONSHIP_KIND` |
| `ccf.graph.backends.postgres_write` | `PostgresConnection`, `PostgresGraphWriter`, `REGISTRATION` |
| `ccf.graph.backends.sqlite` | `ENTITY_KIND`, `RELATIONSHIP_KIND`, `SqliteGraphReader`, `SqliteGraphStore` |
| `ccf.graph.backends.sqlite_write` | `REGISTRATION`, `SqliteConnection`, `SqliteGraphWriter` |
| `ccf.graph.fallback` | `answer` |
| `ccf.graph.governed_reader` | `governed_reader` |
| `ccf.graph.leases` | `AbsoluteLockDirectory`, `LOCK_DIRECTORY_SETTING`, `LOCK_FILE_SUFFIX`, `LockFileWriterLease`, `SDK_MANAGED_LOCK_DIRECTORY`, `declared_lock_directory_lease`, `lock_directory_writer_lease`, `lock_file_name`, `require_absolute_lock_directory`, `require_private_lock_directory`, `sdk_managed_lock_directory` |
| `ccf.graph.product_source` | `GATE_PRODUCT_MOUNT`, `ProductMountRefusal`, `ProductSource`, `mount_product_source` |
| `ccf.graph.protocols` | `ClassificationAuthority`, `ClassificationAuthorityMissing`, `ClassificationAuthorityNotMinted`, `EntityRecord`, `GraphQuery`, `GraphReader`, `GraphView`, `GraphWriter`, `LineageMode`, `NO_STORE_SNAPSHOT_PIN`, `PolicyBindingMode`, `ProcessScopedWriterLease`, `QueryFragment`, `RelationshipRecord`, `SnapshotPinnable`, `SourceAttestation`, `StoreSnapshotPin`, `TEMPORAL_AXES`, `TemporalAxis`, `TraversalDepthCapability`, `TraversalDirection`, `TraversalSpec`, `UngovernedClassificationAttribute`, `UpsertResult`, `WRITER_LEASE_SCOPES`, `WriterLease`, `WriterLeaseHeld`, `WriterLeaseRequired`, `WriterLeaseScope`, `WriterLeaseSource`, `acquire_declared_writer_lease`, `require_classification_authority`, `require_query_classification_authority` |
| `ccf.graph.reader` | `BaseGraphReader`, `ENTITY_KIND`, `RELATIONSHIP_KIND`, `Row`, `parse_timestamp` |
| `ccf.graph.registry` | `AdapterPin`, `BackendRegistration`, `BackendStore`, `DuplicateBackendName`, `InvalidBackendConfig`, `ReservedBackendName`, `ResolvedBackend`, `ResolvedSecret`, `UnknownBackend`, `declared_names`, `is_sdk_development_reference`, `resolve`, `validate_connection` |
| `ccf.operators.base` | `CATEGORY_ORDER`, `Operator`, `OperatorCategory`, `OperatorOutput`, `OperatorParameters`, `OperatorProvenance`, `PushableOperator`, `mint_provenance`, `read_intent_of` |
| `ccf.operators.categories` | `PolicyFilter`, `PolicyFilterParameters`, `SimilaritySelect`, `SimilaritySelectParameters`, `TemporalAsOf`, `TemporalAsOfParameters`, `TraversalDescendants`, `TraversalDescendantsParameters`, `TraversalNeighborhood`, `TraversalNeighborhoodParameters` |
| `ccf.operators.params` | `PolicyFilterParameters`, `SimilaritySelectParameters`, `TemporalAsOfParameters`, `TraversalDescendantsParameters`, `TraversalNeighborhoodParameters` |
| `ccf.operators.planner` | `ComposedOperator`, `IntermediateCache`, `OperatorPlan`, `PlannedStep`, `build_operator_plan`, `compose` |
| `ccf.operators.registry` | `DuplicateOperatorKey`, `OperatorRegistration`, `OperatorRegistry`, `UnregisteredOperator` |
| `ccf.projection.acquisition` | `AcquiredContent`, `AcquirerNotConfigured`, `AcquisitionError`, `ContentAcquirer`, `ContentAcquiringPlan`, `ContentRequest`, `ContentUnsatisfied`, `UndeclaredAcquisition`, `UnknownContentSource` |
| `ccf.projection.engine` | `AcquirerNotConfigured`, `ContentUnsatisfied`, `DuplicateOperatorKey`, `ExecutionResult`, `ExecutionStep`, `OperatorRegistry`, `ProjectionEngine`, `UndeclaredAcquisition`, `UnregisteredOperator` |
| `ccf.projection.plan` | `Perspective`, `ProjectionOutput`, `ProjectionPlan` |
| `ccf.projection.segmentation` | `FragmentFamilyConflict`, `InProcessSegment`, `PushableSegment`, `SegmentedPlan`, `compile_segment_query`, `segment_plan` |
| `ccf.signal` | `envelope`, `source` |
| `ccf.signal.acquisition` | `AcquisitionRecordError`, `FileRecordAcquisitionSource` |
| `ccf.signal.envelope` | `IngressTemporalBound`, `SignalEnvelope`, `SourceIdentity`, `TemporalWriteRefused`, `refuse_foreign_envelope` |
| `ccf.signal.mcp_envelope_map` | `BLOB_PAYLOAD_KEY`, `McpMappingError`, `ResourceContents`, `envelope_id_for`, `payload_of`, `source_metadata_of`, `to_envelope` |
| `ccf.signal.mcp_source` | `MCPSourceAdapter` |
| `ccf.signal.source` | `SignalSourceProtocol` |
| `ccf.similarity.chroma_index` | `COLLECTION_PREFIX`, `ChromaIndex` |
| `ccf.similarity.embedder` | `EmbedderProtocol` |
| `ccf.similarity.protocol` | `MutableSimilarityIndexProtocol`, `SimilarityHit`, `SimilarityIndexProtocol`, `TokenOverlapIndex`, `cosine_score_percent`, `order_hits` |
| `ccf.similarity.sqlite_vec_index` | `SqliteVecIndex` |


## Governance, Authorization, Control Plane and Deployment

| Module | Current public names |
| --- | --- |
| `ccf.artifacts.file_store` | `FileArtifactStore`, `InsecureArtifactStoreRoot` |
| `ccf.artifacts.mcp_store` | `McpArtifactStore` |
| `ccf.artifacts.protocol` | `ARTIFACT_URI_SCHEME`, `ArtifactName`, `ArtifactNotFound`, `ArtifactReadRefused`, `ArtifactRef`, `ArtifactResolutionRefused`, `ArtifactStoreError`, `ArtifactStoreProtocol`, `ArtifactStoreUnauthenticated`, `ArtifactUriUnresolvable`, `ArtifactWriteAuthority`, `ArtifactWriteRefused`, `CONTENT_ADDRESS_PATTERN`, `DerivedWrite`, `LATEST_VERSION_TOKEN`, `MalformedContentAddress`, `MovingTargetRefused`, `NAME_SEGMENT_SEPARATOR`, `WriteKinds`, `WriteKindsDeclarationError`, `WriteTarget`, `artifact_uri`, `authorized_write_target`, `held_content_address`, `parse_artifact_uri` |
| `ccf.authz.actions` | `ACTION_AGENT_DECLARE`, `ACTION_AGENT_LIST`, `ACTION_AGENT_READ`, `ACTION_AGENT_VERSIONS`, `ACTION_ARTIFACT_ERASE`, `ACTION_ARTIFACT_READ`, `ACTION_ARTIFACT_SUBJECT_MATCH`, `ACTION_ARTIFACT_WRITE`, `ACTION_BACKENDS_READ`, `ACTION_CONFIG_KEYS_READ`, `ACTION_CONFIG_REGISTER`, `ACTION_CONFIG_RESOLVE`, `ACTION_CONFIG_VERSIONS_READ`, `ACTION_DOCS_READ`, `ACTION_HEALTH_READ`, `ACTION_HITL_ACTION_SUBMIT`, `ACTION_HITL_QUEUE_READ`, `ACTION_OPENAPI_READ`, `ACTION_PRODUCT_RETRIEVE`, `ACTION_REPLAY_READ`, `ACTION_SCHEMA_LIST`, `ACTION_SCHEMA_READ`, `ACTION_SKILL_CATALOG_READ`, `ACTION_SKILL_CATALOG_REGISTER`, `ACTION_SKILL_GRANT`, `ACTION_SKILL_REVOKE`, `ACTION_WORKFLOW_INVOKE`, `ACTION_WORKFLOW_RESUME`, `ACTION_WORKFLOW_STATUS_READ` |
| `ccf.authz.capability` | `ActionKind`, `AgentDeclare`, `AgentList`, `AgentRead`, `AgentVersions`, `ArtifactErase`, `ArtifactRead`, `ArtifactSubjectMatch`, `ArtifactWrite`, `Authorized`, `BackendsRead`, `COMPOSITION_KINDS`, `COMPOSITION_PRINCIPAL`, `CapabilityBypassError`, `CompositionRegister`, `ConfigKeysRead`, `ConfigRegister`, `ConfigResolve`, `ConfigVersionsRead`, `DeclaredSkillGrant`, `DocsRead`, `Execute`, `GrantMutate`, `HealthRead`, `HitlQueueRead`, `HitlSubmit`, `InvalidationRecordRegister`, `OpenApiRead`, `ProductRetrieve`, `Register`, `ReplayMint`, `ReplayRead`, `Resume`, `SchemaList`, `SchemaRead`, `SkillCatalogRead`, `SkillCatalogRegister`, `SkillGrant`, `SkillRevoke`, `WorkflowStatusRead`, `kind_for_action`, `mint`, `mint_at_composition`, `verify`, `verify_any` |
| `ccf.authz.decision` | `AuthzDecision` |
| `ccf.boot` | `FabricHandle`, `READ_ONLY_LEASE_MECHANISM`, `READ_ONLY_LEASE_SCOPE`, `ReadOnlyFabricRefused`, `boot`, `compose_invalidation_sink` |
| `ccf.contracts` | `base`, `canonical`, `claims` |
| `ccf.contracts.base` | `CCFContract` |
| `ccf.contracts.canonical` | `CanonicalizationError`, `HASH_TRANSPARENT_KEY`, `canonical_bytes`, `canonical_timestamp`, `content_hash`, `generation_mismatch`, `hash_transparent_fields` |
| `ccf.contracts.claims` | `EntityClaim`, `LineageEntry`, `PassageAnchor`, `RelationshipClaim` |
| `ccf.contracts.guarded` | `GUARDED_TYPES`, `GuardedTypeDeclaration`, `declaration_for` |
| `ccf.controlplane` | `artifacts`, `audit`, `registry`, `resolution`, `state` |
| `ccf.controlplane.artifact_base` | `ArtifactClass`, `ArtifactClassIdMismatch`, `ReservedArtifactClassId`, `VersionedArtifact`, `validate_semver` |
| `ccf.controlplane.artifacts` | `ArtifactClass`, `ArtifactClassIdMismatch`, `ArtifactLoadError`, `ArtifactRole`, `CONSTRAINT_OPERATORS`, `ConstraintApplicability`, `ConstraintOperator`, `DEBT_PROFILE`, `DEMONSTRATION_SERVE_INSTANT`, `DEPLOYMENT_CONFIG`, `DEPLOYMENT_MANIFEST`, `DebtProfile`, `DecayMode`, `DeclaredArtifact`, `DeploymentConfig`, `DeploymentManifest`, `EGRESS_DOOR`, `EgressDoorBinding`, `HALF_LIFE_TABLE`, `HalfLifeEntry`, `HalfLifeTable`, `MCP_PRODUCER`, `ManifestEntry`, `McpProducerRegistration`, `OPERATOR_PARAMETERS_POLICY`, `OPERATOR_PARAMETERS_SIMILARITY`, `OPERATOR_PARAMETERS_TEMPORAL`, `OPERATOR_PARAMETERS_TRAVERSAL`, `OPERATOR_PARAMETERS_TRAVERSAL_DESCENDANTS`, `OperatorParametersArtifact`, `PERSPECTIVE`, `POLICY_CONSTRAINT`, `PRODUCT_CLASS`, `PROJECTION_REQUIREMENTS`, `PerspectiveArtifact`, `PolicyConstraint`, `PolicyFilterParametersArtifact`, `ProducerOfferDeclaration`, `ProductClassDeclaration`, `ProjectionRequirements`, `REPLAY_BINDING`, `RESOLUTION_SPEC`, `RegistrationMode`, `ReplayBinding`, `RequestBoundParameter`, `ReservedArtifactClassId`, `SIGNAL_BATCH`, `SeamRefusalBinding`, `SecretReference`, `SignalBatch`, `SimilaritySelectParametersArtifact`, `TEMPORAL_BOUNDARY_POLICY`, `TTL_BINDING`, `TemporalAsOfParametersArtifact`, `TraversalDescendantsParametersArtifact`, `TraversalNeighborhoodParametersArtifact`, `TtlBinding`, `VersionedArtifact`, `declared_artifact_class`, `load_artifact`, `parse_artifact`, `validate_semver` |
| `ccf.controlplane.audit` | `AttributeAssertionRefusedAuditEvent`, `AuditAction`, `AuditEvent`, `AuditLog`, `AuthzDecisionAuditEvent`, `AuthzFailingAxis`, `REGISTRATION_ACTIONS`, `WorkflowVerdictIntegrityAuditEvent`, `WorkflowVerdictIntegrityFailure` |
| `ccf.controlplane.demonstration_serve_instant` | `DEMONSTRATION_SERVE_INSTANT`, `DemonstrationServeInstant`, `DemonstrationServeInstantMisdeclared`, `DemonstrationServeInstantMisplaced`, `PinnedDemonstrationServeInstant`, `demonstration_serve_instant_key`, `refuse_misplaced_demonstration_serve_instants`, `resolve_demonstration_serve_instant` |
| `ccf.controlplane.registry` | `AmbiguousPinnedVersionError`, `ArtifactIsolationRefused`, `AuditEvent`, `ControlPlaneMissing`, `ControlPlaneProtocol`, `ControlPlaneRegistry`, `CrossTenantKeyRefused`, `DERIVED_REGISTER_KINDS`, `DerivedRegisterAuthority`, `INVALIDATION_RECORD_CLASS_ID`, `INVALIDATION_RECORD_PREFIX`, `REGISTER_KINDS`, `RefuseEmptyBump`, `RefuseUnbumpedChange`, `RegisterAuthority`, `RegistrationRefusal`, `RegistryIntegrityFailure`, `ReplayResolver`, `TypedRegisterAuthority`, `invalidation_record_key`, `namespaced_key` |
| `ccf.controlplane.resolution` | `ControlPlaneResolution`, `resolve_pinned` |
| `ccf.controlplane.state` | `AuditedStateWriter`, `ConditionalStateStore`, `ControlPlaneStateStore`, `InMemoryStateStore`, `STATE_KEY_SEPARATOR`, `STATE_STORE_IDENTITY_PATTERN`, `STATE_WRITE_KINDS`, `StateConflict`, `StateKeyError`, `StateStoreIdentityMissing`, `StateTenantMismatch`, `StateWriteAuthority`, `StateWriteBypassError`, `StateWriteToken`, `split_state_key`, `state_key`, `state_store_identity_of`, `verify_any` |
| `ccf.controlplane.temporal_boundary` | `PinnedTemporalBoundary`, `TEMPORAL_BOUNDARY_POLICY`, `TemporalBoundaryMisdeclared`, `TemporalBoundaryPolicy`, `TemporalBoundaryUndeclared`, `resolve_temporal_boundary`, `temporal_boundary_policy_key` |
| `ccf.deployment` | `ArtifactPin`, `BootedFabric`, `DeploymentManifest`, `DeploymentStoreNotEmpty`, `DeploymentStoreNotVerified`, `DerivedDeployment`, `EnvironmentDocument`, `ManifestEntry`, `ManifestKeysPlaceToOneKey`, `QuestionFabricNotExclusive`, `QuestionFabricNotFresh`, `QuestionStoreNotEmpty`, `ResolvedPins`, `SDK_ARTIFACT_CLASSES`, `SDK_ARTIFACT_ROLES`, `SDK_VERSIONED_ARTIFACT_CLASSES`, `SeamRefusalWidening`, `SimilarityCorpusAttributeError`, `UnpinnedArtifactError`, `build_operator_registry`, `derive_deployment`, `load_and_boot`, `load_config_and_boot`, `load_environment_document`, `refuse_operator_set_divergence`, `refuse_registration_the_sdk_fixes`, `refuse_role_the_sdk_fixes`, `refuse_seam_refusal_widening`, `register_manifest_entries`, `resolve_artifact_class` |
| `ccf.deployment.binder` | `refuse_operator_set_divergence`, `refuse_unpromisable_freshness_sla` |
| `ccf.deployment.classes` | `SDK_ARTIFACT_CLASSES`, `SDK_ARTIFACT_ROLES`, `SDK_VERSIONED_ARTIFACT_CLASSES`, `refuse_registration_the_sdk_fixes`, `refuse_role_the_sdk_fixes`, `resolve_artifact_class` |
| `ccf.deployment.config` | `DerivedDeployment`, `derive_deployment`, `load_config_and_boot` |
| `ccf.deployment.environment` | `DoorEnvironment`, `ENVIRONMENT_DOCUMENT_NAME`, `EnvironmentDocument`, `EnvironmentMissing`, `EnvironmentValue`, `RemoteSettings`, `SubstrateSettings`, `load_environment_document`, `resolve_value`, `resolve_values` |
| `ccf.deployment.keys` | `DeploymentKeys` |
| `ccf.deployment.manifest` | `BootedFabric`, `DeploymentStoreNotEmpty`, `DeploymentStoreNotVerified`, `ManifestKeysPlaceToOneKey`, `QuestionFabricNotExclusive`, `QuestionFabricNotFresh`, `QuestionStoreNotEmpty`, `UngovernedClassificationAttribute`, `keys_under_tenant`, `load_and_boot`, `manifest_under_tenant`, `register_manifest_entries` |
| `ccf.deployment.operators` | `SimilarityCorpusAttributeError`, `build_operator_registry` |
| `ccf.deployment.pins` | `ArtifactPin`, `ResolvedPins`, `UnpinnedArtifactError` |
| `ccf.erasure` | `APPROVING_VERDICT`, `ClassRetention`, `DOOR_NAMING_CLASS`, `DOOR_SIGNATURE_ASSERTION`, `DoorNamingAnswer`, `DoorNamingQuery`, `ERASURE_APPROVAL_CLASS`, `ERASURE_INDEX_FILENAME`, `ERASURE_RECORD_CLASS`, `ERASURE_SUBJECT_DECLARATION`, `ErasedAddress`, `ErasedContentRefused`, `ErasureApproval`, `ErasureApprovalInvalid`, `ErasureAuthority`, `ErasureCompositionRefused`, `ErasureConsultingStore`, `ErasureIndexCorrupt`, `ErasureIndexEntry`, `ErasureIndexEntryExists`, `ErasureIndexInsecure`, `ErasureIndexProtocol`, `ErasureIndexUnavailable`, `ErasureIndexWriteFailed`, `ErasureRecord`, `ErasureRecordInvalid`, `ErasureRequest`, `ErasureSubjectClass`, `ErasureSubjectDeclaration`, `ErasureSubjectLocator`, `ErasureTrust`, `FileErasureIndex`, `GENESIS`, `INDEX_CORRUPT`, `INDEX_UNSUPPORTED`, `LegalHold`, `PinnedPolicySource`, `REPLAY_INPUT_PATHS`, `RETENTION_HOLD_POLICY`, `RETENTION_REASON_CODES`, `RequestedAddress`, `RetentionDecision`, `RetentionHoldPolicy`, `RetentionReasonCode`, `SUBJECT_MATCH_CLASS`, `SubjectJudgment`, `SubjectMatchAnswer`, `SubjectMatchQuery`, `SubjectMatchSignatureInvalid`, `SubjectMatchVerdict`, `compose_erasure_consult`, `erasure_index_at`, `judge_retention`, `judge_subject`, `policy_head`, `reference_approval_verifier`, `require_append_authority`, `sign_door_naming_query`, `sign_erasure_record`, `sign_subject_match_query`, `subject_match_verdict`, `subject_ref_for`, `verify_door_naming_query`, `verify_door_signature`, `verify_erasure_approval`, `verify_erasure_entry`, `verify_subject_match_query` |
| `ccf.erasure.approval` | `APPROVING_VERDICT`, `ErasureApprovalInvalid`, `PinnedPolicySource`, `policy_head`, `reference_approval_verifier`, `verify_erasure_approval` |
| `ccf.erasure.contracts` | `ClassRetention`, `ERASURE_APPROVAL_CLASS`, `ERASURE_RECORD_CLASS`, `ERASURE_SUBJECT_DECLARATION`, `ErasedAddress`, `ErasureApproval`, `ErasureRecord`, `ErasureRequest`, `ErasureSubjectClass`, `ErasureSubjectDeclaration`, `ErasureSubjectLocator`, `LegalHold`, `REPLAY_INPUT_PATHS`, `RETENTION_HOLD_POLICY`, `RETENTION_REASON_CODES`, `RequestedAddress`, `RetentionDecision`, `RetentionHoldPolicy`, `RetentionReasonCode`, `judge_retention`, `subject_ref_for` |
| `ccf.erasure.errors` | `ErasedContentRefused`, `ErasureCompositionRefused`, `ErasureIndexCorrupt`, `ErasureIndexInsecure`, `ErasureIndexWriteFailed`, `INDEX_CORRUPT` |
| `ccf.erasure.index` | `ERASURE_INDEX_FILENAME`, `ErasureIndexEntry`, `ErasureIndexEntryExists`, `ErasureIndexProtocol`, `FileErasureIndex`, `GENESIS`, `erasure_index_at`, `require_append_authority` |
| `ccf.erasure.store` | `ErasedContentRefused`, `ErasureCompositionRefused`, `ErasureConsultingStore`, `ErasureIndexUnavailable`, `INDEX_UNSUPPORTED`, `compose_erasure_consult` |
| `ccf.erasure.subject_match` | `DOOR_NAMING_CLASS`, `DoorNamingAnswer`, `DoorNamingQuery`, `SUBJECT_MATCH_CLASS`, `SubjectJudgment`, `SubjectMatchAnswer`, `SubjectMatchQuery`, `SubjectMatchSignatureInvalid`, `SubjectMatchVerdict`, `judge_subject`, `sign_door_naming_query`, `sign_subject_match_query`, `subject_match_verdict`, `verify_door_naming_query`, `verify_subject_match_query` |
| `ccf.erasure.trust` | `DOOR_SIGNATURE_ASSERTION`, `ErasureAuthority`, `ErasureRecordInvalid`, `ErasureTrust`, `sign_erasure_record`, `verify_door_signature`, `verify_erasure_entry` |
| `ccf.halflife` | `debt`, `decay` |
| `ccf.halflife.assessment` | `DebtAssessment`, `DebtEvidence`, `DebtEvidencePointer`, `DebtFactorName`, `DebtFactors`, `DebtSignal`, `NO_DEBT_EVIDENCE`, `NO_OBLIGATION_IN_FORCE`, `NO_SCORER_PINS`, `NO_SIGNAL_OBLIGATIONS`, `NO_SOURCE_REFRESH_RECENCY`, `ObligationInForce`, `ScorerPin`, `SignalObligation`, `SignalObligations`, `SourceRefreshRecency`, `SourceRefreshWindow` |
| `ccf.halflife.debt` | `DebtAssessment`, `DebtEvidence`, `DebtEvidencePointer`, `DebtFactorName`, `DebtFactorScorerProtocol`, `DebtFactors`, `DebtSignal`, `EmptyFactorCompositionError`, `FreshnessScorer`, `NO_DEBT_EVIDENCE`, `NO_OBLIGATION_IN_FORCE`, `NO_SCORER_PINS`, `NO_SIGNAL_OBLIGATIONS`, `NO_SOURCE_REFRESH_RECENCY`, `ScorerPin`, `SignalObligation`, `SignalObligations`, `SourceRefreshRecency`, `SourceRefreshWindow`, `assess_debt`, `basic_debt`, `compose_debt_factors`, `context_debt` |
| `ccf.halflife.decay` | `HalfLifeEntry`, `HalfLifeTable`, `MissingDecayInstant`, `MissingHalfLife`, `NO_SUBJECT_IDENTITY`, `NoDecayCurve`, `Observation`, `TemporalOrderError`, `decay_basis_of`, `decay_mode_of`, `effective_half_life`, `freshness`, `freshness_over_of`, `half_life_of`, `leading_edge`, `relevance_ratio`, `series_key_attribute_of` |


## Agents and Integration Extensions

| Module | Current public names |
| --- | --- |
| `ccf.agents` | `ARCHETYPES`, `Agent`, `AgentFactory`, `AgentIdentity`, `ArchetypeComponent`, `AssemblyOutcome`, `ComposedArchetype`, `CompositionContradiction`, `ConfigurationDefault`, `ConsultationRecord`, `ContextAssemblerProtocol`, `ControlPlaneResolution`, `DETERMINISTIC_ASSEMBLER_ID`, `DETERMINISTIC_ASSEMBLER_VERSION`, `DefaultConflict`, `DeterministicAssembler`, `EmittedEffect`, `NO_CONSULTATIONS`, `ReplayObligation`, `Task`, `TaskFactory`, `TaskIdentity`, `analytics_insights`, `compose`, `content_generation`, `context_assembly`, `document_intelligence`, `monitoring_surveillance`, `workflow_task` |
| `ccf.agents.agent` | `Agent`, `AgentIdentity`, `EmittedEffect` |
| `ccf.agents.archetypes` | `ARCHETYPES`, `ArchetypeComponent`, `ConfigurationDefault`, `ReplayObligation`, `analytics_insights`, `content_generation`, `context_assembly`, `document_intelligence`, `monitoring_surveillance`, `workflow_task` |
| `ccf.agents.assembler` | `AssemblyOutcome`, `ConsultationRecord`, `ContextAssemblerProtocol`, `DETERMINISTIC_ASSEMBLER_ID`, `DETERMINISTIC_ASSEMBLER_VERSION`, `DeterministicAssembler`, `NO_CONSULTATIONS` |
| `ccf.agents.composition` | `ComposedArchetype`, `CompositionContradiction`, `DefaultConflict`, `compose` |
| `ccf.agents.definitions` | `AGENT_DEFINITION`, `ARCHETYPE_IDS`, `ASSEMBLY_ARCHETYPE_ID`, `AgentDefinition`, `ConsumedProduct`, `ContextContract`, `EMITS_NOTHING`, `EmittedProduct`, `InstructionBinding`, `PROMPT_ARTIFACT`, `PerspectiveBinding`, `PromptArtifact`, `TASK_DEFINITION`, `TASK_STEP_KINDS`, `TaskDefinition`, `TaskStep`, `VersionedRef` |
| `ccf.agents.errors` | `ASSEMBLY_REASON_TENANT_MISMATCH`, `ASSEMBLY_REASON_UNDECLARED_ROLE`, `AgentConstructionError`, `AgentDefinitionError`, `AssemblyRefusal`, `AssemblyRefused`, `ConsumptionRefused`, `FalseGrantClaimError`, `NotYetBound`, `PromptRenderRefused`, `PromptValidationError`, `SkillNotBound` |
| `ccf.agents.factory` | `AgentFactory`, `ControlPlaneResolution`, `Task`, `TaskFactory`, `TaskIdentity` |
| `ccf.agents.prompts` | `render_instruction`, `validate_instruction_binding`, `validate_prompt_artifact` |
| `ccf.harness` | `EffectCapability`, `EffectRefusal`, `HarnessAdapterProtocol`, `HarnessCapabilities` |
| `ccf.harness.protocol` | `EFFECT_CAPABILITIES`, `EffectCapability`, `EffectRefusal`, `HarnessAdapterProtocol`, `HarnessCapabilities` |
| `ccf.hitl` | `APPROVAL_GATE_EVENT_CLASS`, `APPROVAL_POLICY`, `AUTHENTICATION_CLAIM`, `ApprovalGate`, `ApprovalPolicy`, `ApprovalSinkAdapter`, `ApproverIdentity`, `ApproverNotEligible`, `AttestationInvalid`, `AuthenticationClaims`, `AuthenticationContext`, `ESCALATION_ACTIONS`, `EscalationActionError`, `EscalationActionRecord`, `EscalationHandOff`, `EscalationRefused`, `EscalationResolution`, `EscalationResolutionRefused`, `ExceptionEscalation`, `ExplicitEscalation`, `GATE_ACTIONS`, `GateActionError`, `GateResolution`, `GateResolutionRefused`, `HITLTransportProtocol`, `HITL_ACTIONS`, `HITL_ACTION_ARTIFACT_CLASS`, `HITL_EVENT_CLASSES`, `HitlActionClaims`, `HitlActionReceipt`, `HitlActionRecord`, `HitlActionRequest`, `HitlActionSubmission`, `HitlEventNotification`, `HitlEventRevalidationRefused`, `HumanPrincipalBinding`, `InMemoryHitlTransport`, `OverrideActionRecord`, `OverrideBoundary`, `OverrideResolution`, `OverrideResolutionRefused`, `PendingHitlEvent`, `PrincipalMismatchRefused`, `RecordingWebhookDeliverer`, `ReviewActionRecord`, `ReviewQueue`, `ReviewQueueItem`, `ReviewResolution`, `ReviewResolutionRefused`, `SignedHitlAction`, `UnboundDecisionError`, `UnknownEscalationEventError`, `UnknownGateEventError`, `UnknownOverrideEventError`, `UnknownReviewEventError`, `WebhookDeliveryOutcome`, `WebhookDeliveryProtocol`, `WebhookEndpoint`, `WebhookEndpointConflict`, `WebhookHitlNotifier`, `check_approver_eligibility`, `sign_hitl_action`, `verify_hitl_action` |
| `ccf.hitl.approval_gate` | `ApprovalGate`, `ApprovalSinkAdapter`, `GATE_ACTIONS`, `GATE_APPROVE`, `GATE_EVENT_CLASS`, `GateActionError`, `GateResolution`, `GateResolutionRefused`, `HITL_ACTION_ARTIFACT_CLASS`, `HitlActionRecord`, `UnboundDecisionError`, `UnknownGateEventError` |
| `ccf.hitl.approval_policy` | `APPROVAL_POLICY`, `ApprovalPolicy` |
| `ccf.hitl.escalation` | `ESCALATION_ACTIONS`, `ESCALATION_EVENT_CLASS`, `EscalationActionError`, `EscalationActionRecord`, `EscalationHandOff`, `EscalationRefused`, `EscalationResolution`, `EscalationResolutionRefused`, `ExceptionEscalation`, `ExplicitEscalation`, `UnknownEscalationEventError` |
| `ccf.hitl.identity_binding` | `AttestationInvalid`, `HitlActionClaims`, `SignedHitlAction`, `sign_hitl_action`, `verify_hitl_action` |
| `ccf.hitl.override` | `OverrideActionRecord`, `OverrideBoundary`, `OverrideResolution`, `OverrideResolutionRefused`, `UnknownOverrideEventError` |
| `ccf.hitl.principal` | `AUTHENTICATION_CLAIM`, `ApproverIdentity`, `AuthenticationClaims`, `AuthenticationContext`, `HumanPrincipalBinding`, `validate_content_hash` |
| `ccf.hitl.review_queue` | `ReviewActionRecord`, `ReviewQueue`, `ReviewQueueItem`, `ReviewResolution`, `ReviewResolutionRefused`, `UnknownReviewEventError` |
| `ccf.hitl.transport` | `APPROVAL_GATE_EVENT_CLASS`, `ApproverNotEligible`, `EventStateAtSubmit`, `GateAlreadyClosed`, `GateClosure`, `GateVerdictsChanged`, `HITLTransportProtocol`, `HITL_ACTIONS`, `HITL_EVENT_CLASSES`, `HITL_POLICY`, `HitlActionReceipt`, `HitlActionRequest`, `HitlActionSubmission`, `HitlEventRevalidationRefused`, `HitlGateClosed`, `HitlPolicy`, `InMemoryHitlTransport`, `PendingHitlEvent`, `PrincipalMismatchRefused`, `SignedBindingInvalidRefused`, `SignedBindingMismatchRefused`, `SignedBindingRequiredRefused`, `SignedBindingStaleRefused`, `check_approver_eligibility`, `enforce_attestation`, `resolve_hitl_policy`, `signed_binding_required` |
| `ccf.hitl.webhook` | `HitlEventNotification`, `RecordingWebhookDeliverer`, `WebhookDeliveryOutcome`, `WebhookDeliveryProtocol`, `WebhookEndpoint`, `WebhookEndpointConflict`, `WebhookHitlNotifier` |
| `ccf.llm` | `LLMClientProtocol` |
| `ccf.mcp.acquisition` | `McpContentAcquirer`, `TENANT_PLACEHOLDER` |
| `ccf.mcp.client` | `HttpClientFactory`, `McpResourceClient`, `SyncMcpBridge`, `bearer_client_factory`, `run_with_session` |
| `ccf.mcp.errors` | `McpClientError`, `McpResourceAbsent`, `McpServerUnreachable`, `McpTimeout`, `McpToolFailed` |
| `ccf.orchestration` | `OrchestrationProtocol` |
| `ccf.orchestration.protocol` | `OrchestrationProtocol` |
| `ccf.peering.admission` | `ADMISSION_RECORD`, `AdmissionBypassError`, `AdmissionNotRecorded`, `AdmissionRecord`, `AdmissionRecordReferenceMismatch`, `AdmissionRefusal`, `AdmittedProduct`, `ContractRefusal`, `GATE_CONTRACT`, `GATE_ISSUANCE`, `GATE_LINEAGE_CONTINUITY`, `GATE_PAYLOAD_CEILING`, `GATE_POLICY_BINDING`, `GATE_SIGNATURE`, `INBOUND_PAYLOAD_CEILING`, `InboundPayloadCeiling`, `IssuanceRefusal`, `LineageContinuityRefusal`, `PRODUCER_ASSERTION_HEADER`, `PayloadTooLargeRefusal`, `PeeringAdmissionGate`, `PolicyBindingRefusal`, `SignatureRefusal`, `payload_ceiling_key`, `union_lineage`, `verify_admission_provenance` |
| `ccf.peering.eligibility` | `ELIGIBILITY_ASSERTION_HEADER`, `ELIGIBILITY_ASSERTION_SCHEMA_VERSION`, `EligibilityAssertion`, `EligibilityAssertionMalformed`, `decode_eligibility_assertion`, `encode_eligibility_assertion`, `mint_eligibility_assertion` |
| `ccf.peering.identity` | `AlgorithmNotPermitted`, `DetachedJwsIdentityProvider`, `FileBackedKeySource`, `IdentityError`, `IdentityProvider`, `JsonWebKey`, `KeyUnavailable`, `PRODUCT_SIGNATURE_TYPE`, `SIGNING_ALGORITHM`, `SignatureInvalid`, `SignatureMalformed`, `SignedContextProduct`, `SigningKeySource`, `UnknownSigningKey`, `jwk_thumbprint`, `signed_product_address` |
| `ccf.peering.issuance` | `ISSUANCE_CLAIMS_HEADER`, `ISSUANCE_CLAIMS_SCHEMA_VERSION`, `InProcessSeenNonceSet`, `IssuanceClaims`, `IssuanceClaimsMalformed`, `IssuedAnswer`, `IssuedRequest`, `SeenNonceSetProtocol`, `decode_issuance_claims`, `encode_issuance_claims`, `issuance_staleness`, `mint_issuance_claims` |
| `ccf.peering.protocol` | `EmitReceipt`, `InboundProduct`, `PeerRef`, `PeeringProtocol` |
| `ccf.peering.trust_policy` | `PEERING_TRUST_POLICY`, `PeerNotTrusted`, `PeerTrustGrant`, `PeeringTrustPolicy`, `TrustPolicyViolation`, `trust_policy_key` |
| `ccf.skills` | `ApprovalOutcome`, `ApprovalRejected`, `ApprovalSink`, `BoundSkillView`, `GovernanceUndeclared`, `GrantCollisionError`, `GrantLedger`, `GrantRefusal`, `GrantTransitionError`, `LocalCallableBinding`, `McpBinding`, `PeeringBinding`, `PolicyRegimeGovernance`, `PolicyRegimeUnresolvable`, `RequirementsExceedRegime`, `SKILL_CATALOG_ENTRY`, `SKILL_GRANT`, `SKILL_TYPES`, `SkillCatalog`, `SkillCatalogEntry`, `SkillGrant`, `SkillNotInCatalog`, `SkillRequirements`, `SplitAuditPlaneError`, `TenantMismatch`, `ToolBinding`, `grant_set_hash`, `skill_catalog_key`, `skill_grant_key` |
| `ccf.skills.callables` | `CallableNotRegistered`, `CallableRegistry`, `DuplicateCallableKey`, `SkillCallable` |
| `ccf.skills.catalog` | `LocalCallableBinding`, `McpBinding`, `McpProductBinding`, `NO_PRODUCT_CLASS`, `PeeringBinding`, `ProcedureBinding`, `SKILL_CATALOG_ENTRY`, `SKILL_TYPES`, `SkillArgumentElement`, `SkillArgumentMember`, `SkillArgumentProperty`, `SkillArgumentSchema`, `SkillCatalog`, `SkillCatalogEntry`, `SkillNotInCatalog`, `SkillRequirements`, `ToolBinding`, `skill_catalog_key` |
| `ccf.skills.dispatch` | `ChildQuestionIdentity`, `McpInvocation`, `McpProductFailure`, `McpProductInvocation`, `McpProductProvenanceError`, `McpSkillRegistry`, `McpSkillUnregistered`, `PeeringInvocation`, `PeeringSkillRegistry`, `PeeringSkillUnregistered`, `ProducerDoesNotOffer`, `ProducerOffer`, `ProducerRegistration`, `ProductQuestion`, `SkillInvocation`, `TENANT_NOT_GRANTED_CODE`, `ToolInvocation`, `dispatch_skill`, `question_identity`, `verify_mcp_product_failure`, `verify_mcp_product_invocation` |
| `ccf.skills.grants` | `ApprovalOutcome`, `ApprovalRejected`, `ApprovalSink`, `BoundSkillView`, `GOVERNANCE_FIELD`, `GRANT_STATE`, `GovernanceUndeclared`, `GrantAuthorityMismatch`, `GrantCollisionError`, `GrantLedger`, `GrantRefusal`, `GrantState`, `GrantStateRecord`, `GrantTransitionError`, `PolicyRegimeGovernance`, `PolicyRegimeUnresolvable`, `RefusingApprovalSink`, `RequirementsExceedRegime`, `SKILL_GRANT`, `SkillGrant`, `SplitAuditPlaneError`, `TenantMismatch`, `grant_set_hash`, `skill_grant_key` |
| `ccf.skills.producers` | `ProducerEnvironmentMissing`, `producer_registration_from_artifact`, `register_declared_producer` |
| `ccf.skills.toolsurface` | `HARNESS_EXPOSABLE_SKILL_TYPES`, `ProcedureHasNoToolSurface`, `RenderedToolSurface`, `SkillHasNoToolSurface`, `render_tool_surface` |
| `ccf.skills.wire_arguments` | `ArgumentRefused`, `MissingArgumentRefused`, `MistypedArgumentRefused`, `UndeclaredArgumentRefused`, `refuse_unconforming_arguments`, `refuse_undeclared_arguments`, `undeclared_arguments` |
| `ccf.workflow` | `WORKFLOW_DEFINITION`, `WORKFLOW_FAILED_STATE`, `Workflow`, `WorkflowConstructionError`, `WorkflowDefinition`, `WorkflowFactory`, `WorkflowIdentity`, `WorkflowTenantMismatchError`, `WorkflowTransition` |
| `ccf.workflow.definitions` | `WORKFLOW_DEFINITION`, `WORKFLOW_FAILED_STATE`, `WorkflowDefinition`, `WorkflowTransition` |
| `ccf.workflow.factory` | `Workflow`, `WorkflowConstructionError`, `WorkflowFactory`, `WorkflowIdentity`, `WorkflowTenantMismatchError` |


## Decision Replay

| Module | Current public names |
| --- | --- |
| `ccf.replay.correlation` | `ExternalTraceProviderProtocol`, `NoOpTraceProvider`, `TraceCorrelation`, `TraceCorrelationHook` |
| `ccf.replay.engine` | `CompositeReplayEnvironment`, `ERASED_SITE_CHILD_CONTRACT`, `ERASED_SITE_DECISION_RECORD`, `ERASED_SITE_REPLAY_ARTIFACT`, `ERASED_SITE_RETAINED_CHILD_QUESTION`, `ErasedContent`, `ErasedReplayOutcome`, `RefusalReplayOutcome`, `ReplayDivergence`, `ReplayEnvironment`, `ReplayError`, `ReplayGenerationMismatch`, `ReplayOutcome`, `ReplayRecordKindMismatch`, `ReplayResolutionClaimMismatch`, `ReplayUnresolvable`, `replay`, `replay_refusal`, `resolve_artifact`, `resolve_artifact_at_uri`, `retained_child_question` |
| `ccf.replay.environment` | `RecordedEnvironment`, `RecordedEnvironmentUnbuildable` |
| `ccf.replay.evidence` | `EVIDENCE_SCHEMA_VERSION`, `EvidenceEntry`, `PendingEvidence`, `ReplayEvidenceAltered`, `ReplayEvidenceIndex`, `ReplayEvidenceUnavailable`, `file_sha256`, `require_record_address` |
| `ccf.replay.inspection` | `DecisionExplanation`, `ParameterOrigin`, `PolicyVersion`, `explain_decision` |
| `ccf.replay.provenance` | `RecordNotFiledByRecordWriter`, `UnattributableRecordStore`, `filed_by_record_writer`, `require_filed_by_record_writer` |
| `ccf.replay.record` | `CHILD_ADMITTED`, `CHILD_OUTCOME_STATUSES`, `ChildResolution`, `ContentGenerationPath`, `ContextFabricSnapshot`, `DecisionReplayRecord`, `FalseAssemblyRefusalClaimError`, `HarnessTrace`, `MODE_1_MODEL_VERSION`, `ModelVersionRecord`, `NO_ADAPTER`, `NO_AGENT_DEFINITION`, `NO_ASSEMBLER`, `NO_ASSEMBLY_REFUSAL`, `NO_DISCLOSURE_DECISION`, `NO_FABRIC_READ`, `NO_GRANTS_SET_HASH`, `NO_GRAPH_QUERIES`, `NO_HARNESS`, `NO_HARNESS_TRACE`, `NO_HITL_ACTIONS`, `NO_ISSUANCE`, `NO_PACKAGING`, `NO_PACKAGING_TRACE`, `NO_PRODUCT_ADDRESS`, `NO_REFUSAL_SEAM`, `NO_REQUEST_RESOLUTION`, `NO_ROLE_RESOLVED`, `NO_WORKFLOW_TRACE`, `PackagingTrace`, `PerspectiveConditioning`, `PolicyBinding`, `PolicyBindingsSnapshot`, `REFUSAL_SEAMS`, `ResolutionNotApplicable`, `ResolutionNotApplicableReason`, `UNSTATED_SUBJECT_WITHHOLDING`, `build_replay_record`, `mint_assembly_refusal`, `new_issuance` |
| `ccf.replay.serve` | `CapabilityForgeryError`, `DeliveryCapability`, `ProductRecordMismatch`, `QueryPinMismatch`, `QueryPinReferenceMismatch`, `QueryPinWriter`, `ReplayReferenceMismatch`, `ReplayTenantMismatch`, `ReplayWriter`, `ServedProduct`, `record_refusal`, `serve` |
| `ccf.replay.snapshots` | `SnapshotPinUnresolvable`, `SnapshotReader`, `SnapshotScopeViolation`, `snapshot_of_execution` |


## Runtime

| Module | Current public names |
| --- | --- |
| `ccf_runtime.adapters.adk` | `AGENT_HASH_STATE_KEY`, `AdkAdapter`, `AdkCarrier`, `ContextInjection`, `HARNESS_ID`, `MODEL_STATE_KEY`, `REFUSAL_RESPONSE_KEY`, `TRACE_METADATA_KEY`, `USAGE_STATE_KEY` |
| `ccf_runtime.adapters.adk.adapter` | `AGENT_HASH_STATE_KEY`, `AdkAdapter`, `AdkCarrier`, `ContextInjection`, `HARNESS_ID`, `MODEL_STATE_KEY`, `REFUSAL_RESPONSE_KEY`, `TRACE_METADATA_KEY`, `USAGE_STATE_KEY` |
| `ccf_runtime.adapters.claude_agent` | `ClaudeAgentAdapter`, `HARNESS_ID` |
| `ccf_runtime.adapters.claude_agent.adapter` | `AllowlistedEnvironmentTransport`, `ClaudeAgentAdapter`, `DEFAULT_CHILD_ENVIRONMENT`, `HARNESS_ID`, `PromptFileRefused` |
| `ccf_runtime.adapters.langgraph` | `AGENT_HASH_METADATA_KEY`, `HARNESS_ID`, `HarnessState`, `LangGraphAdapter`, `LangGraphCarrier`, `MODEL_METADATA_KEY`, `USAGE_METADATA_KEY` |
| `ccf_runtime.adapters.langgraph.adapter` | `AGENT_HASH_METADATA_KEY`, `HARNESS_ID`, `HarnessState`, `LangGraphAdapter`, `LangGraphCarrier`, `MODEL_METADATA_KEY`, `USAGE_METADATA_KEY` |
| `ccf_runtime.authz.artifact` | `SCOPE_MAPPING`, `ScopeEntry`, `ScopeMappingArtifact`, `pattern_matches`, `validate_patterns` |
| `ccf_runtime.authz.capability` | `ActionKind`, `AgentDeclare`, `AgentList`, `AgentRead`, `AgentVersions`, `ArtifactRead`, `ArtifactWrite`, `Authorized`, `BackendsRead`, `COMPOSITION_KINDS`, `COMPOSITION_PRINCIPAL`, `CapabilityBypassError`, `CompositionRegister`, `ConfigKeysRead`, `ConfigRegister`, `ConfigResolve`, `ConfigVersionsRead`, `DocsRead`, `Execute`, `GrantMutate`, `HealthRead`, `HitlQueueRead`, `HitlSubmit`, `OpenApiRead`, `ProductRetrieve`, `Register`, `ReplayMint`, `ReplayRead`, `Resume`, `SchemaList`, `SchemaRead`, `SkillCatalogRead`, `SkillCatalogRegister`, `SkillGrant`, `SkillRevoke`, `WorkflowStatusRead`, `kind_for_action`, `mint`, `mint_at_composition`, `verify`, `verify_any` |
| `ccf_runtime.authz.delivery_boundary` | `DEREFERENCE_PRODUCT_ID`, `DereferenceRequest`, `DereferencedEvidence`, `DisclosingRecorderProtocol`, `EVIDENCE_READ_KINDS`, `EVIDENCE_SURFACES`, `EvidenceReadAuthority`, `SURFACE_HTTP_ARTIFACT_READ`, `SURFACE_HTTP_REPLAY_READ`, `SURFACE_HTTP_ROUTE`, `SURFACE_MCP_RESOURCE`, `SURFACE_MCP_TOOL`, `UnattributableDeliveryBoundaryError`, `UnconsultedDeliveryBoundaryError`, `UnrecordableDeliveryBoundaryError`, `disclosing_boundary`, `govern_absence`, `govern_dereference`, `govern_entitlement`, `govern_erasure`, `govern_resolution`, `govern_scope_denial`, `recorded_boundary` |
| `ccf_runtime.authz.product_entitlement` | `ControlPlaneProductEntitlementSource`, `EvidenceReadabilitySourceProtocol`, `PerspectiveResolverProtocol`, `ProductEntitlementRefused`, `ProductEntitlementSourceProtocol`, `TokenGrant`, `UnverifiedProductCallerRefused`, `entitled_perspective`, `verified_grant` |
| `ccf_runtime.authz.protocol` | `AuthzDecision`, `ControlPlaneTenantAuthorizer`, `TenantAuthorizerProtocol` |
| `ccf_runtime.authz.refusals` | `ACTION_AGENT_DECLARE`, `ACTION_AGENT_LIST`, `ACTION_AGENT_READ`, `ACTION_AGENT_VERSIONS`, `ACTION_ARTIFACT_READ`, `ACTION_ARTIFACT_WRITE`, `ACTION_BACKENDS_READ`, `ACTION_CONFIG_KEYS_READ`, `ACTION_CONFIG_REGISTER`, `ACTION_CONFIG_RESOLVE`, `ACTION_CONFIG_VERSIONS_READ`, `ACTION_DOCS_READ`, `ACTION_HEALTH_READ`, `ACTION_HITL_ACTION_SUBMIT`, `ACTION_HITL_QUEUE_READ`, `ACTION_OPENAPI_READ`, `ACTION_PRODUCT_RETRIEVE`, `ACTION_REPLAY_READ`, `ACTION_SCHEMA_LIST`, `ACTION_SCHEMA_READ`, `ACTION_SKILL_CATALOG_READ`, `ACTION_SKILL_CATALOG_REGISTER`, `ACTION_SKILL_GRANT`, `ACTION_SKILL_REVOKE`, `ACTION_WORKFLOW_INVOKE`, `ACTION_WORKFLOW_RESUME`, `ACTION_WORKFLOW_STATUS_READ` |
| `ccf_runtime.authz.route_declaration` | `ProductClassBinding`, `ProductClassSource`, `ROUTE_AUTHORIZATION_ATTRIBUTE`, `ResourceBinding`, `ResourceSource`, `RouteAuthorization`, `TENANT_PATH_PARAM`, `authorizes`, `composed_fields`, `route_authorization` |
| `ccf_runtime.authz.tenancy` | `AmbiguousTenantRefused`, `TenantNotGrantedRefused`, `UntenantedGrantRefused`, `acting_tenant`, `tenants_of_grant` |
| `ccf_runtime.cdc` | `CDCMappingError`, `CDCSourceAdapter`, `ChangeEvent`, `ChangeSource`, `change_image`, `commit_time`, `envelope_id_for`, `parse_change_event`, `to_envelope` |
| `ccf_runtime.cdc.adapter` | `CDCSourceAdapter` |
| `ccf_runtime.cdc.envelope_map` | `CDCMappingError`, `ChangeEvent`, `ChangeSource`, `change_image`, `commit_time`, `envelope_id_for`, `parse_change_event`, `to_envelope` |
| `ccf_runtime.cli.commands` | `CommandRefused`, `RequestSpec`, `load_document` |
| `ccf_runtime.cli.commands.agent` | `register` |
| `ccf_runtime.cli.commands.artifact` | `register` |
| `ccf_runtime.cli.commands.backends` | `register` |
| `ccf_runtime.cli.commands.config` | `register` |
| `ccf_runtime.cli.commands.hitl` | `register` |
| `ccf_runtime.cli.commands.product` | `register` |
| `ccf_runtime.cli.commands.replay` | `register` |
| `ccf_runtime.cli.commands.schema` | `register` |
| `ccf_runtime.cli.commands.skill` | `register` |
| `ccf_runtime.cli.commands.skill_import` | `MAX_REFERENCES`, `MAX_REFERENCE_BYTES`, `register` |
| `ccf_runtime.cli.commands.workflow` | `register` |
| `ccf_runtime.cli.credential` | `CredentialUnresolved`, `authorization_headers`, `resolve_remote_credential` |
| `ccf_runtime.cli.evidence` | `VERBS`, `register`, `run` |
| `ccf_runtime.cli.local` | `build_local_dependencies` |
| `ccf_runtime.cli.main` | `build_parser`, `main` |
| `ccf_runtime.erasure` | `ErasureDoor`, `ErasureRefused`, `ErasureWorkflowUngated` |
| `ccf_runtime.erasure.door` | `ErasureDoor`, `ErasureRefused`, `ErasureWorkflowUngated` |
| `ccf_runtime.http_api.app` | `AUTH_POSTURE_SENTENCE`, `GovernedWiringError`, `HttpAuthority`, `create_app` |
| `ccf_runtime.http_api.auth` | `BearerTokenAuth`, `HttpAuthProtocol` |
| `ccf_runtime.http_api.dependencies` | `ApiDependencies` |
| `ccf_runtime.http_api.errors` | `ERROR_AMBIGUOUS_TENANT`, `ERROR_APPROVER_NOT_ELIGIBLE`, `ERROR_ARTIFACT_STORE_UNAUTHENTICATED`, `ERROR_DECISION_UNMINTABLE`, `ERROR_EVIDENCE_ABSENT`, `ERROR_EVIDENCE_CLASS_SEALED`, `ERROR_EVIDENCE_CLASS_UNRECOVERABLE`, `ERROR_EVIDENCE_DISCLOSURE_WITHHELD`, `ERROR_EVIDENCE_PRINCIPAL_MISMATCH`, `ERROR_EXECUTION_FENCED`, `ERROR_HITL_EVENT_REVALIDATION_REFUSED`, `ERROR_HITL_GATE_CLOSED`, `ERROR_INVALID_GRANT`, `ERROR_NO_CAPABILITY`, `ERROR_PRINCIPAL_NOT_ENTITLED`, `ERROR_PRODUCT_CLASS_UNENTITLED`, `ERROR_PRODUCT_DOOR_UNGOVERNED`, `ERROR_PRODUCT_OUTSIDE_ROSTER`, `ERROR_PRODUCT_PARAMETERS_MALFORMED`, `ERROR_PRODUCT_POLICY_ABSENT`, `ERROR_PRODUCT_REQUEST_INCOMPLETE`, `ERROR_PRODUCT_ROLE_UNGRANTED`, `ERROR_REQUEST_UNAUTHORIZED`, `ERROR_ROUTE_HANDLE_ABSENT`, `ERROR_SIGNED_BINDING_INVALID`, `ERROR_SIGNED_BINDING_MISMATCH`, `ERROR_SIGNED_BINDING_REQUIRED`, `ERROR_SIGNED_BINDING_STALE`, `ERROR_SUBJECT_CONFLICT`, `ERROR_TENANT_UNAUTHORIZED`, `ERROR_UNAUTHENTICATED`, `ERROR_UNTENANTED_GRANT`, `refusal_detail` |
| `ccf_runtime.http_api.gate` | `AuthorizationGate`, `RouteEntry`, `UndeclaredRouteError`, `build_route_table`, `mounted_routes` |
| `ccf_runtime.http_api.grants` | `GateDenial`, `absent`, `authorized_from_request`, `denial_from_request`, `grant_from_request`, `within_tenant` |
| `ccf_runtime.http_api.refusal_status` | `STATUS_BY_KIND`, `STATUS_FULFILLMENT_WITHHELD`, `STATUS_GONE`, `STATUS_REQUEST`, `STATUS_UNAVAILABLE`, `status_for` |
| `ccf_runtime.http_api.routes` | `CONTENT_ADDRESS_HEADER`, `REPLAY_REF_HEADER`, `REQUEST_ECHO_HEADER`, `canonical_response`, `governed_refusal_response`, `refusal_response` |
| `ccf_runtime.http_api.routes.agent` | `AgentDeclarationRequest`, `AgentDeclared`, `build_router` |
| `ccf_runtime.http_api.routes.artifact` | `ARTIFACT_WRITE_RESOURCE`, `ArtifactPutRequest`, `build_router` |
| `ccf_runtime.http_api.routes.backends` | `build_router` |
| `ccf_runtime.http_api.routes.config` | `ConfigRegistered`, `ConfigRegistrationRequest`, `build_router` |
| `ccf_runtime.http_api.routes.hitl` | `build_router` |
| `ccf_runtime.http_api.routes.product` | `build_router` |
| `ccf_runtime.http_api.routes.replay` | `build_router` |
| `ccf_runtime.http_api.routes.schema` | `build_router` |
| `ccf_runtime.http_api.routes.skill` | `CATALOG_REGISTER_RESOURCE`, `GrantIssued`, `GrantRequest`, `GrantRevocationRequest`, `build_router` |
| `ccf_runtime.http_api.routes.workflow` | `WorkflowInvocationRequest`, `WorkflowResumptionRequest`, `build_router` |
| `ccf_runtime.identity_binding` | `AuthenticationUnattested`, `ERROR_AUTHENTICATION_UNATTESTED`, `attested_authentication`, `authentication_of_grant`, `authentication_of_token`, `principal_from_authorized` |
| `ccf_runtime.mcp.agent_directory` | `context_contract_classes`, `exposed_agent` |
| `ccf_runtime.mcp.artifact_server` | `ARTIFACT_BLOB_URI_SCHEME`, `ARTIFACT_META_URI_SCHEME`, `ARTIFACT_NAMES_URI_SCHEME`, `ArtifactPresence`, `ArtifactResolution`, `ArtifactSubstrate`, `BLOB_URI_TEMPLATE`, `DOOR_NAMING_TOOL`, `META_URI_TEMPLATE`, `NAMES_URI_TEMPLATE`, `NAME_URI_TEMPLATE`, `NonCanonicalPayload`, `PUT_ARTIFACT_TOOL`, `SUBJECT_MATCH_REFUSED`, `SUBJECT_MATCH_TOOL`, `SubjectMatchRefused`, `artifact_blob_uri`, `artifact_meta_uri`, `build_artifact_server` |
| `ccf_runtime.mcp.auth` | `AMBIENT_STDIO_CLAIM`, `FileTokenSource`, `PRODUCT_CLAIM`, `SourceBackedTokenVerifier`, `StaticTokenSource`, `TENANT_CLAIM`, `TokenGrant`, `TokenSourceProtocol`, `authentication_claims`, `bounded_echo`, `granted_products`, `granted_tenants`, `is_ambient_stdio`, `product_claims`, `tenant_claims` |
| `ccf_runtime.mcp.composed_product` | `ComposedProduct`, `compose_for_door` |
| `ccf_runtime.mcp.egress` | `AddressedQuestion`, `CCF_FAILURE_PREFIX`, `MAX_ADDRESS_QUESTION_BYTES`, `NaiveAskedAtRefused`, `PRODUCT_ADDRESS_TEMPLATE`, `PRODUCT_REQUEST_TOOL`, `PRODUCT_URI_SCHEME`, `PRODUCT_URI_TEMPLATE`, `ProductNotServable`, `ProductResolverProtocol`, `build_egress_server`, `parse_product_address`, `product_address`, `product_uri` |
| `ccf_runtime.mcp.experience` | `AgentDirectoryProtocol`, `AgentInvokerProtocol`, `AgentToolCatalog`, `AgentToolListing`, `AgentToolSurface`, `ContextProviderProtocol`, `DEFAULT_INVOKE_AGENT_DESCRIPTION`, `DEFAULT_LIST_AGENTS_DESCRIPTION`, `DEFAULT_PRODUCT_RESOURCE_DESCRIPTION`, `EXPERIENCE_PRODUCT_URI_SCHEME`, `EXPERIENCE_PRODUCT_URI_TEMPLATE`, `EXPERIENCE_TOOLS`, `ExperienceProductNotServable`, `ExperienceProductResolverProtocol`, `ExperienceReplayReadRefused`, `ExposedAgent`, `GET_CONTEXT_TOOL`, `GET_LINEAGE_TOOL`, `GET_REPLAY_RECORD_TOOL`, `INVOKE_AGENT_TOOL`, `LIST_AGENTS_TOOL`, `LineageProviderProtocol`, `ReplayRecordReaderProtocol`, `agent_tool_listing`, `build_experience_server`, `experience_product_uri` |
| `ccf_runtime.mcp.hitl_server` | `HITL_QUEUE_URI_SCHEME`, `HITL_QUEUE_URI_TEMPLATE`, `HitlActionRouteProtocol`, `HitlQueueView`, `HitlQueueViewProtocol`, `SUBMIT_HITL_ACTION_TOOL`, `UnverifiedCallerRefused`, `build_hitl_server`, `hitl_queue_uri` |
| `ccf_runtime.mcp.product_door` | `ProductDoor`, `ServesProducts`, `StdioIdentityRequired`, `open_door`, `open_door_with_verifier`, `scope_mapping_key` |
| `ccf_runtime.mcp.review_door` | `ReviewActionRefused`, `ReviewDoor`, `open_review_door` |
| `ccf_runtime.mcp.tenancy` | `AMBIENT_STDIO_CLAIM`, `ActionUnauthorizedRefused`, `AmbientMutationRefused`, `AmbiguousTenantRefused`, `CrossTenantRefused`, `DecisionUnmintableRefused`, `GuardedSurface`, `ProductOutsideRosterRefused`, `ProductReach`, `READ_KINDS`, `ResourceSubject`, `ResourceUnreadableRefused`, `TENANT_CLAIM`, `TenantGuardViolation`, `TenantGuardedServer`, `TenantSubject`, `TenantlessGrantRefused`, `UnguardedSurfaceError`, `UnverifiedTenantCallerRefused`, `ambient_stdio_identity`, `granted_tenants`, `is_ambient_stdio`, `roster_refusal`, `tenant_claims`, `unguarded_surfaces` |
| `ccf_runtime.orchestration` | `DriverStateRetrievalError`, `SegmentNotExecutedError`, `WorkflowDriverError`, `run_coroutine_sync` |
| `ccf_runtime.orchestration.adk` | `AdkWorkflowDriver` |
| `ccf_runtime.orchestration.adk.driver` | `AdkWorkflowDriver` |
| `ccf_runtime.orchestration.claude_agent` | `ClaudeAgentWorkflowDriver` |
| `ccf_runtime.orchestration.claude_agent.driver` | `ClaudeAgentWorkflowDriver` |
| `ccf_runtime.orchestration.common` | `DriverStateRetrievalError`, `SegmentNotExecutedError`, `WorkflowDriverError`, `run_coroutine_sync` |
| `ccf_runtime.orchestration.langgraph` | `LangGraphWorkflowDriver` |
| `ccf_runtime.orchestration.langgraph.driver` | `LangGraphWorkflowDriver` |
| `ccf_runtime.orchestration.reference` | `WorkflowEngineOrchestrationAdapter` |
| `ccf_runtime.peering.lf_a2a` | `JSONRPC_BINDING`, `LfA2AWire`, `PEER_ID_METADATA`, `PEER_TENANT_METADATA`, `PeerCardResolver`, `SIGNED_PRODUCT_MEDIA_TYPE`, `UnsupportedCarriageOperation`, `build_agent_card` |
| `ccf_runtime.peering.typed_http` | `MalformedWireMessage`, `PEER_ID_HEADER`, `PEER_TENANT_HEADER`, `PeerEndpointResolver`, `PeerUnreachable`, `ReceiveQueueFull`, `SIGNED_PRODUCT_MEDIA_TYPE`, `TypedHttpWire`, `WIRE_MESSAGE_ID_HEADER`, `WireTransportError` |
| `ccf_runtime.workflow.engine` | `AgentNodeBinding`, `DebtAssessmentBinding`, `ExecutionFenced`, `ForeignStateRecordError`, `SkillNodeBinding`, `UnboundDebtAssessmentError`, `WORKFLOW_TRACE_ARTIFACT_CLASS`, `WorkflowCompleted`, `WorkflowEngine`, `WorkflowExceptionRouted`, `WorkflowExecutionTypeError`, `WorkflowOutcome`, `WorkflowResumeRefused`, `WorkflowSuspended`, `WorkflowTraceReferenceMismatch`, `WorkflowWiringError` |
| `ccf_runtime.workflow.state` | `TRACE_ENTRY_KINDS`, `TraceEntry`, `WORKFLOW_STATE`, `WORKFLOW_STATUSES`, `WorkflowStateRecord`, `suspension_left_by` |
