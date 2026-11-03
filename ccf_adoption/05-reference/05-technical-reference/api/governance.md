# Governance / Authorization / Control Plane / Deployment — SDK 1.0.2 Signatures

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Exact public shapes for artifacts, authorization, Control Plane, deployment, erasure, contracts, and debt/half-life governance.

This page is generated from `docs/surface/v0.2-surface.json` at `v1.0.2`. It is a lookup appendix; use the focused reference pages for semantics and examples.

> SDK 1.0.2 is tagged. Release status, deployment verification and the prior bank delivery remain separate; see [migration requirements](../MIGRATION_AND_LIMITATIONS.md).

## `ccf.artifacts.file_store`

- `FileArtifactStore` — **class**
  - `(*, root: 'Path | str', write_kinds: 'WriteKinds') -> 'None'`
- `InsecureArtifactStoreRoot` — **class**
  - `(*, root: 'Path', mode: 'int', owner_uid: 'int', process_uid: 'int') -> 'None'`

## `ccf.artifacts.mcp_store`

- `McpArtifactStore` — **class**
  - `(*, url: 'str', bridge: 'SyncMcpBridge', write_kinds: 'WriteKinds', http_client_factory: 'HttpClientFactory | None' = None) -> 'None'`

## `ccf.artifacts.protocol`

- `ARTIFACT_URI_SCHEME` — **constant**
  - `str`
- `ArtifactName` — **contract**
  - `{"artifact_class":"<class 'str'>","artifact_version":"<class 'str'>","name":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ArtifactNotFound` — **class**
  - `type`
- `ArtifactReadRefused` — **class**
  - `(message: 'str', *, envelope: 'RefusalEnvelope') -> 'None'`
- `ArtifactRef` — **contract**
  - `{"artifact_class":"<class 'str'>","content_address":"<class 'str'>","name":"<class 'str'>","tenant_id":"<class 'str'>","uri":"<class 'str'>"}`
- `ArtifactResolutionRefused` — **class**
  - `(message: 'str', *, envelope: 'RefusalEnvelope') -> 'None'`
- `ArtifactStoreError` — **class**
  - `type`
- `ArtifactStoreProtocol` — **class**
  - `(*args, **kwargs)`
- `ArtifactStoreUnauthenticated` — **class**
  - `type`
- `ArtifactUriUnresolvable` — **class**
  - `type`
- `ArtifactWriteAuthority` — **function**
  - `typing.Union[ccf.authz.capability.Authorized[ccf.authz.capability.ArtifactWrite], ccf.authz.capability.Authorized[ccf.authz.capability.ReplayMint], ccf.authz.capability.Authorized[ccf.authz.capability.Execute], ccf.authz.capability.Authorized[ccf.authz.capability.Resume], ccf.authz.capability.Authorized[ccf.authz.capability.ArtifactErase]]`
- `ArtifactWriteRefused` — **class**
  - `type`
- `CONTENT_ADDRESS_PATTERN` — **constant**
  - `Pattern`
- `DerivedWrite` — **class**
  - `(*, artifact_class: 'str', name: 'str', artifact: 'object') -> 'None'`
- `LATEST_VERSION_TOKEN` — **constant**
  - `str`
- `MalformedContentAddress` — **class**
  - `type`
- `MovingTargetRefused` — **class**
  - `type`
- `NAME_SEGMENT_SEPARATOR` — **constant**
  - `str`
- `WriteKinds` — **class**
  - `(kinds_by_class: 'Mapping[str, tuple[type[ActionKind], ...]]') -> 'None'`
- `WriteKindsDeclarationError` — **class**
  - `type`
- `WriteTarget` — **contract**
  - `{"artifact_class":"<class 'str'>","name":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `artifact_uri` — **function**
  - `(*, tenant_id: 'str', artifact_class: 'str', name: 'str', artifact_version: 'str') -> 'str'`
- `authorized_write_target` — **function**
  - `(authorized: 'ArtifactWriteAuthority', artifact: 'object', *, write_kinds: 'WriteKinds') -> 'tuple[WriteTarget, object]'`
- `held_content_address` — **function**
  - `(content_address: 'str') -> 'str'`
- `parse_artifact_uri` — **function**
  - `(uri: 'str') -> 'ArtifactName'`

## `ccf.authz.actions`

- `ACTION_AGENT_DECLARE` — **constant**
  - `str`
- `ACTION_AGENT_LIST` — **constant**
  - `str`
- `ACTION_AGENT_READ` — **constant**
  - `str`
- `ACTION_AGENT_VERSIONS` — **constant**
  - `str`
- `ACTION_ARTIFACT_ERASE` — **constant**
  - `str`
- `ACTION_ARTIFACT_READ` — **constant**
  - `str`
- `ACTION_ARTIFACT_SUBJECT_MATCH` — **constant**
  - `str`
- `ACTION_ARTIFACT_WRITE` — **constant**
  - `str`
- `ACTION_BACKENDS_READ` — **constant**
  - `str`
- `ACTION_CONFIG_KEYS_READ` — **constant**
  - `str`
- `ACTION_CONFIG_REGISTER` — **constant**
  - `str`
- `ACTION_CONFIG_RESOLVE` — **constant**
  - `str`
- `ACTION_CONFIG_VERSIONS_READ` — **constant**
  - `str`
- `ACTION_DOCS_READ` — **constant**
  - `str`
- `ACTION_HEALTH_READ` — **constant**
  - `str`
- `ACTION_HITL_ACTION_SUBMIT` — **constant**
  - `str`
- `ACTION_HITL_QUEUE_READ` — **constant**
  - `str`
- `ACTION_OPENAPI_READ` — **constant**
  - `str`
- `ACTION_PRODUCT_RETRIEVE` — **constant**
  - `str`
- `ACTION_REPLAY_READ` — **constant**
  - `str`
- `ACTION_SCHEMA_LIST` — **constant**
  - `str`
- `ACTION_SCHEMA_READ` — **constant**
  - `str`
- `ACTION_SKILL_CATALOG_READ` — **constant**
  - `str`
- `ACTION_SKILL_CATALOG_REGISTER` — **constant**
  - `str`
- `ACTION_SKILL_GRANT` — **constant**
  - `str`
- `ACTION_SKILL_REVOKE` — **constant**
  - `str`
- `ACTION_WORKFLOW_INVOKE` — **constant**
  - `str`
- `ACTION_WORKFLOW_RESUME` — **constant**
  - `str`
- `ACTION_WORKFLOW_STATUS_READ` — **constant**
  - `str`

## `ccf.authz.capability`

- `ActionKind` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `AgentDeclare` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `AgentList` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `AgentRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `AgentVersions` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ArtifactErase` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ArtifactRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ArtifactSubjectMatch` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ArtifactWrite` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `Authorized` — **class**
  - `(sentinel: 'object', *, kind: 'type[A]', tenant: 'str', principal: 'str', resource: 'str', decision_id: 'str') -> 'None'`
- `BackendsRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `COMPOSITION_KINDS` — **constant**
  - `tuple`
- `COMPOSITION_PRINCIPAL` — **constant**
  - `str`
- `CapabilityBypassError` — **class**
  - `type`
- `CompositionRegister` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ConfigKeysRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ConfigRegister` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ConfigResolve` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ConfigVersionsRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `DeclaredSkillGrant` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `DocsRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `Execute` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `GrantMutate` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `HealthRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `HitlQueueRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `HitlSubmit` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `InvalidationRecordRegister` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `OpenApiRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ProductRetrieve` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `Register` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ReplayMint` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `ReplayRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `Resume` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `SchemaList` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `SchemaRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `SkillCatalogRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `SkillCatalogRegister` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `SkillGrant` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `SkillRevoke` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `WorkflowStatusRead` — **class**
  - `(*_: 'Any', **__: 'Any') -> "'ActionKind'"`
- `kind_for_action` — **function**
  - `(action_id: 'str') -> 'type[ActionKind]'`
- `mint` — **function**
  - `(kind: 'type[A]', *, decision: 'AuthzDecision', principal: 'str', decision_id: 'str') -> 'Authorized[A]'`
- `mint_at_composition` — **function**
  - `(kind: 'type[A]', *, tenant: 'str', principal: 'str', resource: 'str', decision_id: 'str') -> 'Authorized[A]'`
- `verify` — **function**
  - `(authorized: 'object', *, kind: 'type[ActionKind]', resource: 'str') -> 'None'`
- `verify_any` — **function**
  - `(authorized: 'object', *, kinds: 'tuple[type[ActionKind], ...]', resource: 'str') -> 'type[ActionKind]'`

## `ccf.authz.decision`

- `AuthzDecision` — **contract**
  - `{"action_id":"<class 'str'>","allowed":"<class 'bool'>","artifact_version":"<class 'str'>","decision_id":"str | None","matched_resource_pattern":"str | None","matched_scope_pattern":"str | None","resource":"<class 'str'>","tenant":"<class 'str'>"}`

## `ccf.boot`

- `FabricHandle` — **class**
  - `(*, reader: 'GraphReader', worker: 'AssemblyWorker', registry: 'ControlPlaneProtocol', adapter: 'AdapterPin', shutdown: 'Callable[[], None]', lease_scope: "WriterLeaseScope | Literal['read-only'] | None" = None, lease_mechanism: 'str | None' = None) -> 'None'`
- `READ_ONLY_LEASE_MECHANISM` — **constant**
  - `str`
- `READ_ONLY_LEASE_SCOPE` — **constant**
  - `str`
- `ReadOnlyFabricRefused` — **class**
  - `type`
- `boot` — **function**
  - `(*, backend: 'str', connection: 'Mapping[str, object] | None' = None, secrets: 'Mapping[str, ResolvedSecret] | None' = None, registry: 'ControlPlaneProtocol', resolution_spec_key: 'str', resolution_spec_version: 'str', policy_bundle_key: 'str', policy_bundle_version: 'str', tenant_ids: 'Sequence[str]', read_only: 'bool' = False) -> 'FabricHandle'`
- `compose_invalidation_sink` — **function**
  - `(registry: 'ControlPlaneProtocol', *, tenant_ids: 'Sequence[str]') -> 'ControlPlaneInvalidationSink'`

## `ccf.contracts`

- `base` — **constant**
  - `module`
- `canonical` — **constant**
  - `module`
- `claims` — **constant**
  - `module`

## `ccf.contracts.base`

- `CCFContract` — **contract**
  - `{}`

## `ccf.contracts.canonical`

- `CanonicalizationError` — **class**
  - `type`
- `HASH_TRANSPARENT_KEY` — **constant**
  - `str`
- `canonical_bytes` — **function**
  - `(obj: 'object') -> 'bytes'`
- `canonical_timestamp` — **function**
  - `(value: 'datetime') -> 'str'`
- `content_hash` — **function**
  - `(obj: 'object') -> 'str'`
- `generation_mismatch` — **function**
  - `(model_cls: 'type[BaseModel]', stored: 'Mapping[str, object]') -> 'tuple[str, ...]'`
- `hash_transparent_fields` — **function**
  - `(model_cls: 'type[BaseModel]') -> 'frozenset[str]'`

## `ccf.contracts.claims`

- `EntityClaim` — **contract**
  - `{"attributes":"collections.abc.Mapping[str, str]","entity_class":"<class 'str'>","entity_uri":"<class 'str'>","lineage":"frozenset[ccf.contracts.claims.LineageEntry]","observed_at":"<class 'datetime.datetime'>","tenant_id":"<class 'str'>","valid_from":"datetime.datetime | None","valid_to":"datetime.datetime | None"}`
- `LineageEntry` — **contract**
  - `{"envelope_id":"<class 'str'>","observed_at":"<class 'datetime.datetime'>","passage_anchor":"ccf.contracts.claims.PassageAnchor | None","source":"<class 'ccf.signal.envelope.SourceIdentity'>"}`
- `PassageAnchor` — **contract**
  - `{"kind":"<class 'str'>","locator":"<class 'str'>"}`
- `RelationshipClaim` — **contract**
  - `{"attributes":"collections.abc.Mapping[str, str]","lineage":"frozenset[ccf.contracts.claims.LineageEntry]","object_uri":"<class 'str'>","observed_at":"<class 'datetime.datetime'>","relationship_type":"<class 'str'>","subject_uri":"<class 'str'>","tenant_id":"<class 'str'>","valid_from":"datetime.datetime | None","valid_to":"datetime.datetime | None"}`

## `ccf.contracts.guarded`

- `GUARDED_TYPES` — **constant**
  - `tuple`
- `GuardedTypeDeclaration` — **class**
  - `(type_path: 'str', authority: 'str', mint: 'str', verifier: 'str | None', boundaries: 'tuple[str, ...]', propagation: 'str', residual: 'str | None' = None, verifier_aliases: 'tuple[str, ...]' = (), notes: 'tuple[str, ...]' = <factory>) -> None`
- `declaration_for` — **function**
  - `(type_path: 'str') -> 'GuardedTypeDeclaration | None'`

## `ccf.controlplane`

- `artifacts` — **constant**
  - `module`
- `audit` — **constant**
  - `module`
- `registry` — **constant**
  - `module`
- `resolution` — **constant**
  - `module`
- `state` — **constant**
  - `module`

## `ccf.controlplane.artifact_base`

- `ArtifactClass` — **class**
  - `(class_id: 'str', contract: 'type[CCFContract]') -> None`
- `ArtifactClassIdMismatch` — **class**
  - `(*, presented_class_id: 'str', document_class_id: 'object') -> 'None'`
- `ReservedArtifactClassId` — **class**
  - `(class_id: 'str') -> 'None'`
- `VersionedArtifact` — **contract**
  - `{"semver":"<class 'str'>"}`
- `validate_semver` — **function**
  - `(value: 'str') -> 'str'`

## `ccf.controlplane.artifacts`

- `ArtifactClass` — **class**
  - `(class_id: 'str', contract: 'type[CCFContract]') -> None`
- `ArtifactClassIdMismatch` — **class**
  - `(*, presented_class_id: 'str', document_class_id: 'object') -> 'None'`
- `ArtifactLoadError` — **class**
  - `type`
- `ArtifactRole` — **function**
  - `typing.Literal['register', 'load']`
- `CONSTRAINT_OPERATORS` — **constant**
  - `frozenset`
- `ConstraintApplicability` — **contract**
  - `{"intent":"str | None","perspective_role":"str | None","product_class":"str | None","tenant":"str | None"}`
- `ConstraintOperator` — **function**
  - `typing.Literal['maximum', 'minimum', 'allowed_set', 'required', 'preferred']`
- `DEBT_PROFILE` — **constant**
  - `ArtifactClass`
- `DEMONSTRATION_SERVE_INSTANT` — **constant**
  - `ArtifactClass`
- `DEPLOYMENT_CONFIG` — **constant**
  - `ArtifactClass`
- `DEPLOYMENT_MANIFEST` — **constant**
  - `ArtifactClass`
- `DebtProfile` — **contract**
  - `{"fail_closed_threshold":"<class 'decimal.Decimal'>","forced_llm_threshold":"<class 'decimal.Decimal'>","risk_sensitivity":"<class 'decimal.Decimal'>","semver":"<class 'str'>","signal_obligations":"tuple[ccf.halflife.assessment.SignalObligation, ...]"}`
- `DecayMode` — **function**
  - `typing.Literal['curve', 'supersede-only']`
- `DeclaredArtifact` — **contract**
  - `{"class_id":"<class 'str'>","declaration":"collections.abc.Mapping[str, typing.Any]","semver":"<class 'str'>"}`
- `DeploymentConfig` — **contract**
  - `{"agent":"collections.abc.Mapping[str, typing.Any] | None","backend":"<class 'str'>","backend_secrets":"tuple[ccf.controlplane.artifacts.SecretReference, ...]","debt_profile":"collections.abc.Mapping[str, typing.Any] | None","default_perspective":"collections.abc.Mapping[str, typing.Any] | None","demonstration_serve_instant":"collections.abc.Mapping[str, typing.Any] | None","door":"collections.abc.Mapping[str, typing.Any] | None","grants":"tuple[str, ...] | None","half_life":"collections.abc.Mapping[str, typing.Any] | None","operators":"collections.abc.Mapping[str, collections.abc.Mapping[str, typing.Any]] | None","policy":"collections.abc.Mapping[str, typing.Any] | None","policy_bundle_key":"str | None","policy_constraints":"collections.abc.Mapping[str, collections.abc.Mapping[str, typing.Any]] | None","producers":"collections.abc.Mapping[str, collections.abc.Mapping[str, typing.Any]] | None","product_class":"collections.abc.Mapping[str, typing.Any]","product_entitlement":"collections.abc.Mapping[str, typing.Any] | None","replay":"collections.abc.Mapping[str, typing.Any] | None","request_contract":"collections.abc.Mapping[str, typing.Any] | None","resolution":"collections.abc.Mapping[str, typing.Any] | None","resolution_spec_key":"str | None","semver":"<class 'str'>","skills":"collections.abc.Mapping[str, collections.abc.Mapping[str, typing.Any]] | None","store_creation_lock_wait_seconds":"int | None","survivor_cap":"int | None","temporal_boundary":"collections.abc.Mapping[str, typing.Any] | None","tenant_id":"str | None","ttl":"collections.abc.Mapping[str, typing.Any] | None"}`
- `DeploymentManifest` — **contract**
  - `{"artifacts":"tuple[ccf.controlplane.artifacts.ManifestEntry, ...]","backend":"<class 'str'>","backend_secrets":"tuple[ccf.controlplane.artifacts.SecretReference, ...]","policy_bundle_key":"<class 'str'>","resolution_spec_key":"<class 'str'>","semver":"<class 'str'>","store_creation_lock_wait_seconds":"int | None","survivor_cap":"int | None","tenant_id":"str | None"}`
- `EGRESS_DOOR` — **constant**
  - `ArtifactClass`
- `EgressDoorBinding` — **contract**
  - `{"producer_id":"<class 'str'>","producer_tenant":"<class 'str'>","required_scope":"<class 'str'>","semver":"<class 'str'>","tool_description":"<class 'str'>"}`
- `HALF_LIFE_TABLE` — **constant**
  - `ArtifactClass`
- `HalfLifeEntry` — **contract**
  - `{"decay":"typing.Literal['curve', 'supersede-only']","decay_basis":"typing.Literal['observed-at', 'valid-from']","decay_driver":"<class 'str'>","freshness_over":"typing.Literal['series-mean', 'leading-edge']","half_life_seconds":"int | None","series_key_attribute":"str | None","supersession_event":"<class 'str'>"}`
- `HalfLifeTable` — **contract**
  - `{"entries":"collections.abc.Mapping[str, ccf.controlplane.artifacts.HalfLifeEntry]","semver":"<class 'str'>"}`
- `MCP_PRODUCER` — **constant**
  - `ArtifactClass`
- `ManifestEntry` — **contract**
  - `{"class_id":"<class 'str'>","key":"<class 'str'>","path":"<class 'str'>","registration":"typing.Literal['typed', 'versioned']","role":"typing.Literal['register', 'load']"}`
- `McpProducerRegistration` — **contract**
  - `{"credential_from_env":"<class 'str'>","endpoint_from_env":"<class 'str'>","offers":"tuple[ccf.controlplane.artifacts.ProducerOfferDeclaration, ...]","producer_id":"<class 'str'>","producer_tenant":"<class 'str'>","semver":"<class 'str'>","server":"<class 'str'>"}`
- `OPERATOR_PARAMETERS_POLICY` — **constant**
  - `ArtifactClass`
- `OPERATOR_PARAMETERS_SIMILARITY` — **constant**
  - `ArtifactClass`
- `OPERATOR_PARAMETERS_TEMPORAL` — **constant**
  - `ArtifactClass`
- `OPERATOR_PARAMETERS_TRAVERSAL` — **constant**
  - `ArtifactClass`
- `OPERATOR_PARAMETERS_TRAVERSAL_DESCENDANTS` — **constant**
  - `ArtifactClass`
- `OperatorParametersArtifact` — **contract**
  - `{"semver":"<class 'str'>"}`
- `PERSPECTIVE` — **constant**
  - `ArtifactClass`
- `POLICY_CONSTRAINT` — **constant**
  - `ArtifactClass`
- `PRODUCT_CLASS` — **constant**
  - `ArtifactClass`
- `PROJECTION_REQUIREMENTS` — **constant**
  - `ArtifactClass`
- `PerspectiveArtifact` — **contract**
  - `{"principal_id":"<class 'str'>","role":"<class 'str'>","semver":"<class 'str'>"}`
- `PolicyConstraint` — **contract**
  - `{"applies_to":"<class 'ccf.controlplane.artifacts.ConstraintApplicability'>","effective_from":"<class 'datetime.datetime'>","effective_until":"datetime.datetime | None","operator":"typing.Literal['maximum', 'minimum', 'allowed_set', 'required', 'preferred']","overridable":"<class 'bool'>","parameter":"<class 'str'>","policy_id":"<class 'str'>","preferred_decimal":"<class 'bool'>","priority":"<class 'int'>","reason":"<class 'str'>","semver":"<class 'str'>","source_authority":"<class 'str'>","value":"decimal.Decimal | str | tuple[str, ...] | None"}`
- `PolicyFilterParametersArtifact` — **contract**
  - `{"classification_attribute_by_class":"collections.abc.Mapping[str, str]","permitted_classifications":"frozenset[str] | ccf.controlplane.artifacts.RequestBoundParameter","semver":"<class 'str'>"}`
- `ProducerOfferDeclaration` — **contract**
  - `{"product_class":"<class 'str'>","versions_from":"<class 'str'>"}`
- `ProductClassDeclaration` — **contract**
  - `{"accepted_lineage_modes":"frozenset[typing.Literal['graph-supplied', 'product-carried', 'none']]","accepted_policy_binding_modes":"frozenset[typing.Literal['assembly-stamped', 'admission-verified', 'none']]","addressability":"<class 'ccf.products.contract.ProductAddress'>","assembly_mode":"typing.Literal['algorithmic', 'llm_packaged', 'swarm_assembled']","constituent_validity_floors":"<class 'ccf.products.contract.ConstituentValidityFloors'>","decision_instant_parameter":"str | None","declared_product_gate":"<class 'ccf.products.contract.DeclaredProductGate'>","discovery":"<class 'ccf.products.contract.ProductDiscovery'>","freshness_sla":"<class 'ccf.products.contract.FreshnessSLA'>","max_ttl_key":"<class 'str'>","payload_schema_key":"<class 'str'>","request_contract_key":"<class 'str'>","required_operator_keys":"tuple[str, ...]","requires":"tuple[ccf.products.contract.ChildRequirement, ...]","schema_name":"<class 'str'>","schema_version":"<class 'str'>","seam_refusals":"tuple[ccf.controlplane.artifacts.SeamRefusalBinding, ...]","semver":"<class 'str'>","serve_obligations":"<class 'ccf.products.contract.ServeObligations'>","subject_withholding":"typing.Literal['may-withhold', 'never']","ttl_anchor":"typing.Literal['from_decision', 'from_entity_freshness']"}`
- `ProjectionRequirements` — **contract**
  - `{"plan_id":"<class 'str'>","required_operator_keys":"tuple[str, ...]","semver":"<class 'str'>"}`
- `REPLAY_BINDING` — **constant**
  - `ArtifactClass`
- `RESOLUTION_SPEC` — **constant**
  - `ArtifactClass`
- `RegistrationMode` — **function**
  - `typing.Literal['typed', 'versioned']`
- `ReplayBinding` — **contract**
  - `{"query_pin_class":"<class 'str'>","record_class":"<class 'str'>","semver":"<class 'str'>","store_dirname":"<class 'str'>"}`
- `RequestBoundParameter` — **contract**
  - `{"parameter":"<class 'str'>","source":"typing.Literal['effective_request']"}`
- `ReservedArtifactClassId` — **class**
  - `(class_id: 'str') -> 'None'`
- `SIGNAL_BATCH` — **constant**
  - `ArtifactClass`
- `SeamRefusalBinding` — **contract**
  - `{"cause":"typing.Union[typing.Literal['nonexistent', 'unauthorized', 'undisclosed'], typing.Literal['source-unavailable']]","error_code":"<class 'str'>","exception":"<class 'str'>"}`
- `SecretReference` — **contract**
  - `{"env_var":"<class 'str'>","field":"<class 'str'>"}`
- `SignalBatch` — **contract**
  - `{"envelopes":"tuple[ccf.signal.envelope.SignalEnvelope, ...]","semver":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `SimilaritySelectParametersArtifact` — **contract**
  - `{"index_version":"<class 'str'>","minimum_score_percent":"<class 'int'>","query":"<class 'str'>","ranked_entity_classes":"frozenset[str]","semver":"<class 'str'>","similarity_corpus_attribute_by_class":"collections.abc.Mapping[str, str]"}`
- `TEMPORAL_BOUNDARY_POLICY` — **constant**
  - `ArtifactClass`
- `TTL_BINDING` — **constant**
  - `ArtifactClass`
- `TemporalAsOfParametersArtifact` — **contract**
  - `{"require_valid_at_boundary":"<class 'bool'>","semver":"<class 'str'>"}`
- `TraversalDescendantsParametersArtifact` — **contract**
  - `{"admitted_entity_classes":"frozenset[str] | None","depth_limit":"<class 'int'>","relationship_types":"frozenset[str]","seed_entity_classes":"frozenset[str]","semver":"<class 'str'>"}`
- `TraversalNeighborhoodParametersArtifact` — **contract**
  - `{"admitted_entity_classes":"frozenset[str] | None","depth_limit":"<class 'int'>","relationship_types":"frozenset[str]","seed_entity_classes":"frozenset[str]","semver":"<class 'str'>"}`
- `TtlBinding` — **contract**
  - `{"max_ttl_seconds":"<class 'int'>","product_ttl_seconds":"<class 'int'>","semver":"<class 'str'>"}`
- `VersionedArtifact` — **contract**
  - `{"semver":"<class 'str'>"}`
- `declared_artifact_class` — **function**
  - `(class_id: 'str') -> 'ArtifactClass'`
- `load_artifact` — **function**
  - `(text: 'str', artifact_class: 'ArtifactClass') -> 'CCFContract'`
- `parse_artifact` — **function**
  - `(document: 'object', artifact_class: 'ArtifactClass') -> 'CCFContract'`
- `validate_semver` — **function**
  - `(value: 'str') -> 'str'`

## `ccf.controlplane.audit`

- `AttributeAssertionRefusedAuditEvent` — **contract**
  - `{"action":"typing.Literal['register', 'register_typed', 'register_versioned', 'resolve', 'resolve_latest', 'grant_requested', 'grant_pending_approval', 'grant_effective', 'grant_refused', 'grant_revoked', 'peering_admitted', 'peering_admission_refused', 'skill_invoked', 'state_written', 'workflow_started', 'workflow_transition', 'workflow_suspended', 'workflow_resumed', 'workflow_exception', 'workflow_completed', 'workflow_request_retired', 'hitl_action', 'authz_decision', 'composition', 'attribute_assertion_refused', 'governed_attribute_omitted', 'erasure_index_unsupported']","actor":"str | None","artifact_class":"str | None","key":"<class 'str'>","occurred_at":"<class 'datetime.datetime'>","refused_attribute":"str | None","refused_entity_class":"str | None","refused_envelope_id":"str | None","refused_source_system_id":"str | None","refused_value_present":"bool | None","resolved":"<class 'bool'>","sequence":"<class 'int'>","version":"<class 'str'>"}`
- `AuditAction` — **function**
  - `typing.Literal['register', 'register_typed', 'register_versioned', 'resolve', 'resolve_latest', 'grant_requested', 'grant_pending_approval', 'grant_effective', 'grant_refused', 'grant_revoked', 'peering_admitted', 'peering_admission_refused', 'skill_invoked', 'state_written', 'workflow_started', 'workflow_transition', 'workflow_suspended', 'workflow_resumed', 'workflow_exception', 'workflow_completed', 'workflow_request_retired', 'hitl_action', 'authz_decision', 'composition', 'attribute_assertion_refused', 'governed_attribute_omitted', 'erasure_index_unsupported']`
- `AuditEvent` — **contract**
  - `{"action":"typing.Literal['register', 'register_typed', 'register_versioned', 'resolve', 'resolve_latest', 'grant_requested', 'grant_pending_approval', 'grant_effective', 'grant_refused', 'grant_revoked', 'peering_admitted', 'peering_admission_refused', 'skill_invoked', 'state_written', 'workflow_started', 'workflow_transition', 'workflow_suspended', 'workflow_resumed', 'workflow_exception', 'workflow_completed', 'workflow_request_retired', 'hitl_action', 'authz_decision', 'composition', 'attribute_assertion_refused', 'governed_attribute_omitted', 'erasure_index_unsupported']","actor":"str | None","artifact_class":"str | None","key":"<class 'str'>","occurred_at":"<class 'datetime.datetime'>","resolved":"<class 'bool'>","sequence":"<class 'int'>","version":"<class 'str'>"}`
- `AuditLog` — **class**
  - `() -> 'None'`
- `AuthzDecisionAuditEvent` — **contract**
  - `{"action":"typing.Literal['register', 'register_typed', 'register_versioned', 'resolve', 'resolve_latest', 'grant_requested', 'grant_pending_approval', 'grant_effective', 'grant_refused', 'grant_revoked', 'peering_admitted', 'peering_admission_refused', 'skill_invoked', 'state_written', 'workflow_started', 'workflow_transition', 'workflow_suspended', 'workflow_resumed', 'workflow_exception', 'workflow_completed', 'workflow_request_retired', 'hitl_action', 'authz_decision', 'composition', 'attribute_assertion_refused', 'governed_attribute_omitted', 'erasure_index_unsupported']","actor":"str | None","artifact_class":"str | None","authz_action_id":"str | None","authz_failing_axis":"typing.Optional[typing.Literal['tenant', 'action', 'resource', 'mapping']]","authz_matched_pattern":"str | None","authz_matched_resource_pattern":"str | None","authz_resource":"str | None","key":"<class 'str'>","occurred_at":"<class 'datetime.datetime'>","resolved":"<class 'bool'>","sequence":"<class 'int'>","version":"<class 'str'>"}`
- `AuthzFailingAxis` — **function**
  - `typing.Literal['tenant', 'action', 'resource', 'mapping']`
- `REGISTRATION_ACTIONS` — **constant**
  - `frozenset`
- `WorkflowVerdictIntegrityAuditEvent` — **contract**
  - `{"action":"typing.Literal['register', 'register_typed', 'register_versioned', 'resolve', 'resolve_latest', 'grant_requested', 'grant_pending_approval', 'grant_effective', 'grant_refused', 'grant_revoked', 'peering_admitted', 'peering_admission_refused', 'skill_invoked', 'state_written', 'workflow_started', 'workflow_transition', 'workflow_suspended', 'workflow_resumed', 'workflow_exception', 'workflow_completed', 'workflow_request_retired', 'hitl_action', 'authz_decision', 'composition', 'attribute_assertion_refused', 'governed_attribute_omitted', 'erasure_index_unsupported']","actor":"str | None","artifact_class":"str | None","key":"<class 'str'>","occurred_at":"<class 'datetime.datetime'>","resolved":"<class 'bool'>","sequence":"<class 'int'>","version":"<class 'str'>","workflow_recorded_approver":"str | None","workflow_verdict_integrity":"typing.Optional[typing.Literal['route_disagreement', 'conflicting_verdicts']]"}`
- `WorkflowVerdictIntegrityFailure` — **function**
  - `typing.Literal['route_disagreement', 'conflicting_verdicts']`

## `ccf.controlplane.demonstration_serve_instant`

- `DEMONSTRATION_SERVE_INSTANT` — **constant**
  - `ArtifactClass`
- `DemonstrationServeInstant` — **contract**
  - `{"serve_instant":"<class 'datetime.datetime'>"}`
- `DemonstrationServeInstantMisdeclared` — **class**
  - `type`
- `DemonstrationServeInstantMisplaced` — **class**
  - `(message: 'str', *, reason: 'MisplacedReason', keys: 'tuple[str, ...]', expected: 'str') -> 'None'`
- `PinnedDemonstrationServeInstant` — **class**
  - `(key: 'str', version: 'str', declaration: 'DemonstrationServeInstant') -> None`
- `demonstration_serve_instant_key` — **function**
  - `(*, tenant_id: 'str') -> 'str'`
- `refuse_misplaced_demonstration_serve_instants` — **function**
  - `(*, keys: 'Sequence[str]', tenant_id: 'str') -> 'None'`
- `resolve_demonstration_serve_instant` — **function**
  - `(*, registry: 'ControlPlaneProtocol', tenant_id: 'str') -> 'PinnedDemonstrationServeInstant | None'`

## `ccf.controlplane.registry`

- `AmbiguousPinnedVersionError` — **class**
  - `(key: 'str', declared_version: 'str', content_hashes: 'Sequence[str]') -> 'None'`
- `ArtifactIsolationRefused` — **class**
  - `(*, artifact_type: 'str', door: 'str', reason: 'str') -> 'None'`
- `AuditEvent` — **contract**
  - `{"action":"typing.Literal['register', 'register_typed', 'register_versioned', 'resolve', 'resolve_latest', 'grant_requested', 'grant_pending_approval', 'grant_effective', 'grant_refused', 'grant_revoked', 'peering_admitted', 'peering_admission_refused', 'skill_invoked', 'state_written', 'workflow_started', 'workflow_transition', 'workflow_suspended', 'workflow_resumed', 'workflow_exception', 'workflow_completed', 'workflow_request_retired', 'hitl_action', 'authz_decision', 'composition', 'attribute_assertion_refused', 'governed_attribute_omitted', 'erasure_index_unsupported']","actor":"str | None","artifact_class":"str | None","key":"<class 'str'>","occurred_at":"<class 'datetime.datetime'>","resolved":"<class 'bool'>","sequence":"<class 'int'>","version":"<class 'str'>"}`
- `ControlPlaneMissing` — **class**
  - `type`
- `ControlPlaneProtocol` — **class**
  - `(*args, **kwargs)`
- `ControlPlaneRegistry` — **class**
  - `(*, clock: 'Callable[[], datetime] | None' = None, audit_log: 'AuditLog | None' = None, state_store: 'ControlPlaneStateStore | None' = None) -> 'None'`
- `CrossTenantKeyRefused` — **class**
  - `type`
- `DERIVED_REGISTER_KINDS` — **constant**
  - `tuple`
- `DerivedRegisterAuthority` — **function**
  - `typing.Union[ccf.authz.capability.Authorized[ccf.authz.capability.ConfigRegister], ccf.authz.capability.Authorized[ccf.authz.capability.CompositionRegister], ccf.authz.capability.Authorized[ccf.authz.capability.AgentDeclare], ccf.authz.capability.Authorized[ccf.authz.capability.SkillCatalogRegister], ccf.authz.capability.Authorized[ccf.authz.capability.SkillGrant], ccf.authz.capability.Authorized[ccf.authz.capability.DeclaredSkillGrant]]`
- `INVALIDATION_RECORD_CLASS_ID` — **constant**
  - `str`
- `INVALIDATION_RECORD_PREFIX` — **constant**
  - `str`
- `REGISTER_KINDS` — **constant**
  - `tuple`
- `RefuseEmptyBump` — **contract**
  - `{"artifact_version":"<class 'str'>","content_hash":"<class 'str'>","detail":"<class 'str'>","existing_version":"<class 'str'>","key":"<class 'str'>"}`
- `RefuseUnbumpedChange` — **contract**
  - `{"artifact_version":"<class 'str'>","detail":"<class 'str'>","existing_hash":"<class 'str'>","incoming_hash":"<class 'str'>","key":"<class 'str'>"}`
- `RegisterAuthority` — **function**
  - `typing.Union[ccf.authz.capability.Authorized[ccf.authz.capability.ConfigRegister], ccf.authz.capability.Authorized[ccf.authz.capability.CompositionRegister], ccf.authz.capability.Authorized[ccf.authz.capability.AgentDeclare], ccf.authz.capability.Authorized[ccf.authz.capability.SkillCatalogRegister]]`
- `RegistrationRefusal` — **contract**
  - `{"artifact_version":"<class 'str'>","detail":"<class 'str'>","key":"<class 'str'>"}`
- `RegistryIntegrityFailure` — **class**
  - `(*, key: 'str', version: 'str', door: 'str', reason: 'str') -> 'None'`
- `ReplayResolver` — **class**
  - `(control_plane: 'ControlPlaneProtocol') -> 'None'`
- `TypedRegisterAuthority` — **function**
  - `typing.Union[ccf.authz.capability.Authorized[ccf.authz.capability.ConfigRegister], ccf.authz.capability.Authorized[ccf.authz.capability.CompositionRegister], ccf.authz.capability.Authorized[ccf.authz.capability.AgentDeclare], ccf.authz.capability.Authorized[ccf.authz.capability.SkillCatalogRegister], ccf.authz.capability.Authorized[ccf.authz.capability.InvalidationRecordRegister]]`
- `invalidation_record_key` — **function**
  - `(*, tenant_id: 'str', entity_uri: 'str') -> 'str'`
- `namespaced_key` — **function**
  - `(*, tenant: 'str', key: 'str') -> 'str'`

## `ccf.controlplane.resolution`

- `ControlPlaneResolution` — **class**
  - `(*args, **kwargs)`
- `resolve_pinned` — **function**
  - `(control_plane: 'ControlPlaneResolution', uri: 'str') -> 'object | None'`

## `ccf.controlplane.state`

- `AuditedStateWriter` — **class**
  - `(*, store: 'ControlPlaneStateStore', audit: 'AuditLog') -> 'None'`
- `ConditionalStateStore` — **class**
  - `(*args, **kwargs)`
- `ControlPlaneStateStore` — **class**
  - `(*args, **kwargs)`
- `InMemoryStateStore` — **class**
  - `() -> 'None'`
- `STATE_KEY_SEPARATOR` — **constant**
  - `str`
- `STATE_STORE_IDENTITY_PATTERN` — **constant**
  - `Pattern`
- `STATE_WRITE_KINDS` — **constant**
  - `tuple`
- `StateConflict` — **class**
  - `type`
- `StateKeyError` — **class**
  - `type`
- `StateStoreIdentityMissing` — **class**
  - `type`
- `StateTenantMismatch` — **class**
  - `type`
- `StateWriteAuthority` — **function**
  - `typing.Union[ccf.authz.capability.Authorized[ccf.authz.capability.Execute], ccf.authz.capability.Authorized[ccf.authz.capability.Resume], ccf.authz.capability.Authorized[ccf.authz.capability.SkillGrant], ccf.authz.capability.Authorized[ccf.authz.capability.SkillRevoke], ccf.authz.capability.Authorized[ccf.authz.capability.DeclaredSkillGrant]]`
- `StateWriteBypassError` — **class**
  - `type`
- `StateWriteToken` — **class**
  - `(token: 'object') -> 'None'`
- `split_state_key` — **function**
  - `(key: 'str') -> 'tuple[str, str]'`
- `state_key` — **function**
  - `(*, tenant: 'str', record_id: 'str') -> 'str'`
- `state_store_identity_of` — **function**
  - `(store: 'object') -> 'str'`
- `verify_any` — **function**
  - `(authorized: 'object', *, kinds: 'tuple[type[ActionKind], ...]', resource: 'str') -> 'type[ActionKind]'`

## `ccf.controlplane.temporal_boundary`

- `PinnedTemporalBoundary` — **class**
  - `(key: 'str', version: 'str', policy: 'TemporalBoundaryPolicy') -> None`
- `TEMPORAL_BOUNDARY_POLICY` — **constant**
  - `ArtifactClass`
- `TemporalBoundaryMisdeclared` — **class**
  - `type`
- `TemporalBoundaryPolicy` — **contract**
  - `{"max_past_seconds":"<class 'int'>","permitted_clock_skew_seconds":"<class 'int'>"}`
- `TemporalBoundaryUndeclared` — **class**
  - `(key: 'str', required_class_id: 'str', reason: 'str', detail: 'str') -> None`
- `resolve_temporal_boundary` — **function**
  - `(*, registry: 'ControlPlaneProtocol', tenant_id: 'str') -> 'PinnedTemporalBoundary | TemporalBoundaryUndeclared'`
- `temporal_boundary_policy_key` — **function**
  - `(*, tenant_id: 'str') -> 'str'`

## `ccf.deployment`

- `ArtifactPin` — **contract**
  - `{"class_id":"<class 'str'>","key":"<class 'str'>","registration":"typing.Literal['typed', 'versioned']","version":"<class 'str'>"}`
- `BootedFabric` — **class**
  - `(handle: 'FabricHandle', pins: 'ResolvedPins', tenant_id: 'str', artifacts: 'Mapping[str, CCFContract]', survivor_cap: 'int | None', keys: 'DeploymentKeys | None' = None, for_question: 'bool' = False, question_store: 'bool' = False, store_creation: "Literal['verified', 'unmarked', 'unverifiable']" = 'unmarked') -> None`
- `DeploymentManifest` — **contract**
  - `{"artifacts":"tuple[ccf.controlplane.artifacts.ManifestEntry, ...]","backend":"<class 'str'>","backend_secrets":"tuple[ccf.controlplane.artifacts.SecretReference, ...]","policy_bundle_key":"<class 'str'>","resolution_spec_key":"<class 'str'>","semver":"<class 'str'>","store_creation_lock_wait_seconds":"int | None","survivor_cap":"int | None","tenant_id":"str | None"}`
- `DeploymentStoreNotEmpty` — **class**
  - `type`
- `DeploymentStoreNotVerified` — **class**
  - `(*, marker: 'Path', reason: "Literal['pending', 'unreadable', 'oversized', 'claimed', 'lock-unavailable', 'lock-held']", lock: 'Path | None' = None, detail: 'str | None' = None) -> 'None'`
- `DerivedDeployment` — **class**
  - `(manifest: 'DeploymentManifest', documents: 'Mapping[str, Mapping[str, Any]]', keys: 'DeploymentKeys') -> None`
- `EnvironmentDocument` — **contract**
  - `{"config":"<class 'str'>","door":"ccf.deployment.environment.DoorEnvironment | None","remote":"ccf.deployment.environment.RemoteSettings | None","sources":"collections.abc.Mapping[str, collections.abc.Mapping[str, ccf.deployment.environment.EnvironmentValue]]","substrate":"<class 'ccf.deployment.environment.SubstrateSettings'>"}`
- `ManifestEntry` — **contract**
  - `{"class_id":"<class 'str'>","key":"<class 'str'>","path":"<class 'str'>","registration":"typing.Literal['typed', 'versioned']","role":"typing.Literal['register', 'load']"}`
- `ManifestKeysPlaceToOneKey` — **class**
  - `(*, authored_keys: 'tuple[str, str]', placed_key: 'str', tenant: 'str') -> 'None'`
- `QuestionFabricNotExclusive` — **class**
  - `type`
- `QuestionFabricNotFresh` — **class**
  - `type`
- `QuestionStoreNotEmpty` — **class**
  - `type`
- `ResolvedPins` — **contract**
  - `{"entries":"tuple[ccf.deployment.pins.ArtifactPin, ...]"}`
- `SDK_ARTIFACT_CLASSES` — **constant**
  - `dict`
- `SDK_ARTIFACT_ROLES` — **constant**
  - `dict`
- `SDK_VERSIONED_ARTIFACT_CLASSES` — **constant**
  - `dict`
- `SeamRefusalWidening` — **class**
  - `type`
- `SimilarityCorpusAttributeError` — **class**
  - `type`
- `UnpinnedArtifactError` — **class**
  - `type`
- `build_operator_registry` — **function**
  - `(*, parameters: 'Mapping[str, OperatorParametersArtifact]', view: 'GraphView', pins: 'ResolvedPins', policy_bundle_key: 'str', deployment_operators: 'Sequence[Operator]' = ()) -> 'OperatorRegistry'`
- `derive_deployment` — **function**
  - `(config: 'DeploymentConfig', config_filename: 'str' = 'ccf_config.yaml') -> 'DerivedDeployment'`
- `load_and_boot` — **function**
  - `(manifest_path: 'str | Path', *, registry: 'ControlPlaneProtocol', connection: 'Mapping[str, object] | None' = None, tenant_id: 'str | None' = None, read_only: 'bool' = False, for_question: 'bool' = False) -> 'BootedFabric'`
- `load_config_and_boot` — **function**
  - `(config_path: 'str | Path', *, registry: 'ControlPlaneProtocol', connection: 'Mapping[str, object] | None' = None, tenant_id: 'str | None' = None, read_only: 'bool' = False, for_question: 'bool' = False) -> 'BootedFabric'`
- `load_environment_document` — **function**
  - `(config_root: 'Path') -> 'EnvironmentDocument'`
- `refuse_operator_set_divergence` — **function**
  - `(*, declared: 'ProductClassDeclaration', plan: 'ProjectionPlan') -> 'None'`
- `refuse_registration_the_sdk_fixes` — **function**
  - `(class_id: 'str', registration: 'RegistrationMode') -> 'None'`
- `refuse_role_the_sdk_fixes` — **function**
  - `(class_id: 'str', role: 'ArtifactRole') -> 'None'`
- `refuse_seam_refusal_widening` — **function**
  - `(*, declared: 'ProductClassDeclaration', deployment_exceptions: 'frozenset[str]') -> 'None'`
- `register_manifest_entries` — **function**
  - `(manifest: 'DeploymentManifest', parsed: 'Mapping[str, CCFContract]', *, registry: 'ControlPlaneProtocol', tenant: 'str', only: 'frozenset[str] | None' = None) -> 'tuple[ArtifactPin, ...]'`
- `resolve_artifact_class` — **function**
  - `(class_id: 'str') -> 'ArtifactClass'`

## `ccf.deployment.binder`

- `refuse_operator_set_divergence` — **function**
  - `(*, declared: 'ProductClassDeclaration', plan: 'ProjectionPlan') -> 'None'`
- `refuse_unpromisable_freshness_sla` — **function**
  - `(*, declared: 'ProductClassDeclaration', constituents: 'Sequence[ProductClassDeclaration]') -> 'None'`

## `ccf.deployment.classes`

- `SDK_ARTIFACT_CLASSES` — **constant**
  - `dict`
- `SDK_ARTIFACT_ROLES` — **constant**
  - `dict`
- `SDK_VERSIONED_ARTIFACT_CLASSES` — **constant**
  - `dict`
- `refuse_registration_the_sdk_fixes` — **function**
  - `(class_id: 'str', registration: 'RegistrationMode') -> 'None'`
- `refuse_role_the_sdk_fixes` — **function**
  - `(class_id: 'str', role: 'ArtifactRole') -> 'None'`
- `resolve_artifact_class` — **function**
  - `(class_id: 'str') -> 'ArtifactClass'`

## `ccf.deployment.config`

- `DerivedDeployment` — **class**
  - `(manifest: 'DeploymentManifest', documents: 'Mapping[str, Mapping[str, Any]]', keys: 'DeploymentKeys') -> None`
- `derive_deployment` — **function**
  - `(config: 'DeploymentConfig', config_filename: 'str' = 'ccf_config.yaml') -> 'DerivedDeployment'`
- `load_config_and_boot` — **function**
  - `(config_path: 'str | Path', *, registry: 'ControlPlaneProtocol', connection: 'Mapping[str, object] | None' = None, tenant_id: 'str | None' = None, read_only: 'bool' = False, for_question: 'bool' = False) -> 'BootedFabric'`

## `ccf.deployment.environment`

- `DoorEnvironment` — **contract**
  - `{"credential":"<class 'ccf.deployment.environment.EnvironmentValue'>","issuer_url":"ccf.deployment.environment.EnvironmentValue | None","resource_server_url":"ccf.deployment.environment.EnvironmentValue | None"}`
- `ENVIRONMENT_DOCUMENT_NAME` — **constant**
  - `str`
- `EnvironmentDocument` — **contract**
  - `{"config":"<class 'str'>","door":"ccf.deployment.environment.DoorEnvironment | None","remote":"ccf.deployment.environment.RemoteSettings | None","sources":"collections.abc.Mapping[str, collections.abc.Mapping[str, ccf.deployment.environment.EnvironmentValue]]","substrate":"<class 'ccf.deployment.environment.SubstrateSettings'>"}`
- `EnvironmentMissing` — **class**
  - `type`
- `EnvironmentValue` — **contract**
  - `{"from_env":"<class 'str'>","remedy":"<class 'str'>"}`
- `RemoteSettings` — **contract**
  - `{"call_timeout_seconds":"<class 'int'>"}`
- `SubstrateSettings` — **contract**
  - `{"prefix":"<class 'str'>","setting":"<class 'str'>","suffix":"<class 'str'>"}`
- `load_environment_document` — **function**
  - `(config_root: 'Path') -> 'EnvironmentDocument'`
- `resolve_value` — **function**
  - `(value: 'EnvironmentValue', environ: 'Mapping[str, str]') -> 'str'`
- `resolve_values` — **function**
  - `(sources: 'Mapping[str, Mapping[str, EnvironmentValue]]', environ: 'Mapping[str, str]') -> 'Mapping[str, Mapping[str, str]]'`

## `ccf.deployment.keys`

- `DeploymentKeys` — **class**
  - `(product_class: 'str', request_contract: 'str | None', policy_bundle: 'str', resolution_spec: 'str', half_life: 'str | None', debt_profile: 'str | None', default_perspective: 'str | None', replay: 'str | None', ttl: 'str | None', door: 'str | None', temporal_boundary: 'str | None', agent: 'str | None', operator_parameters: 'tuple[str, ...]', policy_constraints: 'tuple[str, ...]', producers: 'tuple[str, ...]', skills: 'tuple[str, ...]') -> None`

## `ccf.deployment.manifest`

- `BootedFabric` — **class**
  - `(handle: 'FabricHandle', pins: 'ResolvedPins', tenant_id: 'str', artifacts: 'Mapping[str, CCFContract]', survivor_cap: 'int | None', keys: 'DeploymentKeys | None' = None, for_question: 'bool' = False, question_store: 'bool' = False, store_creation: "Literal['verified', 'unmarked', 'unverifiable']" = 'unmarked') -> None`
- `DeploymentStoreNotEmpty` — **class**
  - `type`
- `DeploymentStoreNotVerified` — **class**
  - `(*, marker: 'Path', reason: "Literal['pending', 'unreadable', 'oversized', 'claimed', 'lock-unavailable', 'lock-held']", lock: 'Path | None' = None, detail: 'str | None' = None) -> 'None'`
- `ManifestKeysPlaceToOneKey` — **class**
  - `(*, authored_keys: 'tuple[str, str]', placed_key: 'str', tenant: 'str') -> 'None'`
- `QuestionFabricNotExclusive` — **class**
  - `type`
- `QuestionFabricNotFresh` — **class**
  - `type`
- `QuestionStoreNotEmpty` — **class**
  - `type`
- `UngovernedClassificationAttribute` — **class**
  - `(*, operator_key: 'str', entity_class: 'str', attribute: 'str') -> 'None'`
- `keys_under_tenant` — **function**
  - `(keys: 'DeploymentKeys', *, tenant: 'str') -> 'DeploymentKeys'`
- `load_and_boot` — **function**
  - `(manifest_path: 'str | Path', *, registry: 'ControlPlaneProtocol', connection: 'Mapping[str, object] | None' = None, tenant_id: 'str | None' = None, read_only: 'bool' = False, for_question: 'bool' = False) -> 'BootedFabric'`
- `manifest_under_tenant` — **function**
  - `(manifest: 'DeploymentManifest', parsed: 'Mapping[str, CCFContract]', keys: 'DeploymentKeys | None', *, tenant: 'str') -> 'tuple[DeploymentManifest, Mapping[str, CCFContract], DeploymentKeys | None]'`
- `register_manifest_entries` — **function**
  - `(manifest: 'DeploymentManifest', parsed: 'Mapping[str, CCFContract]', *, registry: 'ControlPlaneProtocol', tenant: 'str', only: 'frozenset[str] | None' = None) -> 'tuple[ArtifactPin, ...]'`

## `ccf.deployment.operators`

- `SimilarityCorpusAttributeError` — **class**
  - `type`
- `build_operator_registry` — **function**
  - `(*, parameters: 'Mapping[str, OperatorParametersArtifact]', view: 'GraphView', pins: 'ResolvedPins', policy_bundle_key: 'str', deployment_operators: 'Sequence[Operator]' = ()) -> 'OperatorRegistry'`

## `ccf.deployment.pins`

- `ArtifactPin` — **contract**
  - `{"class_id":"<class 'str'>","key":"<class 'str'>","registration":"typing.Literal['typed', 'versioned']","version":"<class 'str'>"}`
- `ResolvedPins` — **contract**
  - `{"entries":"tuple[ccf.deployment.pins.ArtifactPin, ...]"}`
- `UnpinnedArtifactError` — **class**
  - `type`

## `ccf.erasure`

- `APPROVING_VERDICT` — **constant**
  - `str`
- `ClassRetention` — **contract**
  - `{"erasable":"<class 'bool'>","holds":"tuple[ccf.erasure.contracts.LegalHold, ...]","minimum_age":"int | None","reasons":"tuple[str, ...]","severity_exempt":"<class 'bool'>"}`
- `DOOR_NAMING_CLASS` — **constant**
  - `str`
- `DOOR_SIGNATURE_ASSERTION` — **constant**
  - `str`
- `DoorNamingAnswer` — **contract**
  - `{"filed_by_record_writer":"<class 'bool'>","names":"tuple[ccf.artifacts.protocol.ArtifactName, ...]"}`
- `DoorNamingQuery` — **contract**
  - `{"content_address":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ERASURE_APPROVAL_CLASS` — **constant**
  - `str`
- `ERASURE_INDEX_FILENAME` — **constant**
  - `str`
- `ERASURE_RECORD_CLASS` — **constant**
  - `str`
- `ERASURE_SUBJECT_DECLARATION` — **constant**
  - `ArtifactClass`
- `ErasedAddress` — **contract**
  - `{"artifact_class":"<class 'str'>","content_address":"<class 'str'>","key_paths":"tuple[str, ...]","scope":"typing.Literal['whole']"}`
- `ErasedContentRefused` — **class**
  - `(*, content_address: 'str', erasure_record_address: 'str | None', reason: 'str | None', erased_at: 'datetime | None') -> 'None'`
- `ErasureApproval` — **contract**
  - `{"acted_at":"<class 'datetime.datetime'>","approver":"<class 'ccf.hitl.principal.ApproverIdentity'>","attestation":"<class 'ccf.hitl.identity_binding.SignedHitlAction'>","gate":"<class 'str'>","gate_state_hash":"<class 'str'>","hitl_policy_ref":"<class 'str'>","request_id":"<class 'str'>","submission_hash":"<class 'str'>","tenant_id":"<class 'str'>","verdict":"<class 'str'>","workflow_definition_hash":"<class 'str'>"}`
- `ErasureApprovalInvalid` — **class**
  - `(detail: 'str', *, reason_code: 'str') -> 'None'`
- `ErasureAuthority` — **contract**
  - `{"door_keys":"collections.abc.Mapping[str, collections.abc.Mapping[str, str]]","hitl_policy_key":"<class 'str'>","tenant_id":"<class 'str'>","workflow_definition_hash":"<class 'str'>"}`
- `ErasureCompositionRefused` — **class**
  - `type`
- `ErasureConsultingStore` — **class**
  - `(inner: 'ArtifactStoreProtocol', *, index: 'ErasureIndexProtocol', audit_log: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'PinnedPolicySource', erasure_trust: 'ErasureTrust', tenant_id: 'str | None', identity_provider: 'IdentityProvider | None' = None, _verdicts: '_Verdicts | None' = None) -> 'None'`
- `ErasureIndexCorrupt` — **class**
  - `(detail: 'str', *, content_address: 'str' = '') -> 'None'`
- `ErasureIndexEntry` — **contract**
  - `{"approval_ref":"<class 'str'>","content_address":"<class 'str'>","door_key_id":"<class 'str'>","door_signature":"<class 'str'>","erased_at":"<class 'datetime.datetime'>","erasure_record_address":"<class 'str'>","reason":"<class 'str'>","request_id":"<class 'str'>","subject_class":"<class 'str'>","subject_ref":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ErasureIndexEntryExists` — **class**
  - `type`
- `ErasureIndexInsecure` — **class**
  - `type`
- `ErasureIndexProtocol` — **class**
  - `(*args, **kwargs)`
- `ErasureIndexUnavailable` — **class**
  - `type`
- `ErasureIndexWriteFailed` — **class**
  - `type`
- `ErasureRecord` — **contract**
  - `{"actor":"<class 'ccf.hitl.principal.ApproverIdentity'>","addresses":"tuple[ccf.erasure.contracts.ErasedAddress, ...]","approval_ref":"<class 'str'>","authorizing_decision_id":"<class 'str'>","erased_at":"<class 'datetime.datetime'>","legal_basis":"<class 'str'>","reason":"<class 'str'>","record_id":"<class 'str'>","request_id":"<class 'str'>","requested_by":"<class 'str'>","retention_decision":"<class 'ccf.erasure.contracts.RetentionDecision'>","subject_class":"<class 'str'>","subject_ref":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ErasureRecordInvalid` — **class**
  - `(detail: 'str', *, reason_code: 'str') -> 'None'`
- `ErasureRequest` — **contract**
  - `{"addresses":"tuple[ccf.erasure.contracts.RequestedAddress, ...]","legal_basis":"<class 'str'>","reason":"<class 'str'>","retention_policy_ref":"<class 'str'>","subject_class":"<class 'str'>","subject_declaration_ref":"<class 'str'>","subject_ref":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ErasureSubjectClass` — **contract**
  - `{"artifact_classes":"tuple[str, ...]","class_id":"<class 'str'>","identifier_kind":"typing.Literal['opaque', 'principal']","key_paths":"tuple[str, ...]","subject_ref_salt":"<class 'str'>"}`
- `ErasureSubjectDeclaration` — **contract**
  - `{"semver":"<class 'str'>","subjects":"tuple[ccf.erasure.contracts.ErasureSubjectClass, ...]","tenant_id":"<class 'str'>"}`
- `ErasureSubjectLocator` — **class**
  - `(*args, **kwargs)`
- `ErasureTrust` — **contract**
  - `{"authorities":"collections.abc.Mapping[str, ccf.erasure.trust.ErasureAuthority]"}`
- `FileErasureIndex` — **class**
  - `(path: 'Path | str') -> 'None'`
- `GENESIS` — **constant**
  - `str`
- `INDEX_CORRUPT` — **constant**
  - `str`
- `INDEX_UNSUPPORTED` — **constant**
  - `str`
- `LegalHold` — **contract**
  - `{"addresses":"tuple[str, ...] | None","basis":"<class 'str'>","hold_id":"<class 'str'>","placed_at":"<class 'datetime.datetime'>","placed_by":"<class 'str'>","subject_refs":"tuple[str, ...] | None"}`
- `PinnedPolicySource` — **class**
  - `(*args, **kwargs)`
- `REPLAY_INPUT_PATHS` — **constant**
  - `tuple`
- `RETENTION_HOLD_POLICY` — **constant**
  - `ArtifactClass`
- `RETENTION_REASON_CODES` — **constant**
  - `frozenset`
- `RequestedAddress` — **contract**
  - `{"artifact_class":"<class 'str'>","content_address":"<class 'str'>","retained_since":"<class 'datetime.datetime'>"}`
- `RetentionDecision` — **contract**
  - `{"address":"str | None","hold_id":"str | None","policy_ref":"<class 'str'>","reason_code":"typing.Literal['admitted', 'class-absent', 'not-erasable', 'severity-exempt', 'legal-hold', 'reason-unknown', 'under-minimum-age', 'policy-unresolvable', 'replay-input']","verdict":"typing.Literal['admit', 'refuse']"}`
- `RetentionHoldPolicy` — **contract**
  - `{"classes":"collections.abc.Mapping[str, ccf.erasure.contracts.ClassRetention]","semver":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `RetentionReasonCode` — **function**
  - `typing.Literal['admitted', 'class-absent', 'not-erasable', 'severity-exempt', 'legal-hold', 'reason-unknown', 'under-minimum-age', 'policy-unresolvable', 'replay-input']`
- `SUBJECT_MATCH_CLASS` — **constant**
  - `str`
- `SubjectJudgment` — **function**
  - `typing.Literal['bytes-not-at-address', 'bytes-unparseable', 'subject-not-found', 'subject-in-replay-input', 'subject-found']`
- `SubjectMatchAnswer` — **contract**
  - `{"verdict":"typing.Literal['subject-unverifiable', 'subject-not-found', 'subject-in-replay-input', 'subject-found']"}`
- `SubjectMatchQuery` — **contract**
  - `{"content_address":"<class 'str'>","key_paths":"tuple[str, ...]","subject_ref":"<class 'str'>","subject_ref_salt":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `SubjectMatchSignatureInvalid` — **class**
  - `type`
- `SubjectMatchVerdict` — **function**
  - `typing.Literal['subject-unverifiable', 'subject-not-found', 'subject-in-replay-input', 'subject-found']`
- `compose_erasure_consult` — **function**
  - `(store: 'ArtifactStoreProtocol', *, index: 'ErasureIndexProtocol', audit_log: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'PinnedPolicySource', erasure_trust: 'ErasureTrust', tenant_id: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'ErasureConsultingStore'`
- `erasure_index_at` — **function**
  - `(store_root: 'Path | str') -> 'FileErasureIndex'`
- `judge_retention` — **function**
  - `(policy: 'RetentionHoldPolicy', *, policy_ref: 'str', request: 'ErasureRequest', now: 'datetime') -> 'RetentionDecision'`
- `judge_subject` — **function**
  - `(payload: 'bytes', query: 'SubjectMatchQuery') -> 'SubjectJudgment'`
- `policy_head` — **function**
  - `(control_plane: 'PinnedPolicySource') -> 'str'`
- `reference_approval_verifier` — **function**
  - `() -> 'IdentityProvider'`
- `require_append_authority` — **function**
  - `(authorized: 'Authorized[ArtifactErase]', entry: 'ErasureIndexEntry') -> 'None'`
- `sign_door_naming_query` — **function**
  - `(query: 'DoorNamingQuery', *, signer: 'IdentityProvider', key_id: 'str') -> 'str'`
- `sign_erasure_record` — **function**
  - `(record: 'ErasureRecord', *, signer: 'IdentityProvider', key_id: 'str') -> 'str'`
- `sign_subject_match_query` — **function**
  - `(query: 'SubjectMatchQuery', *, signer: 'IdentityProvider', key_id: 'str') -> 'str'`
- `subject_match_verdict` — **function**
  - `(judgment: 'SubjectJudgment') -> 'SubjectMatchVerdict'`
- `subject_ref_for` — **function**
  - `(declaration: 'ErasureSubjectDeclaration', subject_class: 'str', identifier: 'str') -> 'str'`
- `verify_door_naming_query` — **function**
  - `(query: 'DoorNamingQuery', *, door_signature: 'str', authority: 'ErasureAuthority', identity_provider: 'IdentityProvider') -> 'None'`
- `verify_door_signature` — **function**
  - `(payload: 'bytes', *, door_signature: 'str', door_key_id: 'str', authority: 'ErasureAuthority', identity_provider: 'IdentityProvider') -> 'None'`
- `verify_erasure_approval` — **function**
  - `(approval: 'ErasureApproval', *, tenant_id: 'str', request_id: 'str', approver: 'ApproverIdentity', requested_by: 'str', authority: 'ErasureAuthority', control_plane: 'PinnedPolicySource', identity_provider: 'IdentityProvider') -> 'HitlActionClaims'`
- `verify_erasure_entry` — **function**
  - `(entry: 'ErasureIndexEntry', payload: 'bytes', *, trust: 'ErasureTrust', identity_provider: 'IdentityProvider') -> 'tuple[ErasureRecord, ErasureAuthority]'`
- `verify_subject_match_query` — **function**
  - `(query: 'SubjectMatchQuery', *, door_signature: 'str', authority: 'ErasureAuthority', identity_provider: 'IdentityProvider') -> 'None'`

## `ccf.erasure.approval`

- `APPROVING_VERDICT` — **constant**
  - `str`
- `ErasureApprovalInvalid` — **class**
  - `(detail: 'str', *, reason_code: 'str') -> 'None'`
- `PinnedPolicySource` — **class**
  - `(*args, **kwargs)`
- `policy_head` — **function**
  - `(control_plane: 'PinnedPolicySource') -> 'str'`
- `reference_approval_verifier` — **function**
  - `() -> 'IdentityProvider'`
- `verify_erasure_approval` — **function**
  - `(approval: 'ErasureApproval', *, tenant_id: 'str', request_id: 'str', approver: 'ApproverIdentity', requested_by: 'str', authority: 'ErasureAuthority', control_plane: 'PinnedPolicySource', identity_provider: 'IdentityProvider') -> 'HitlActionClaims'`

## `ccf.erasure.contracts`

- `ClassRetention` — **contract**
  - `{"erasable":"<class 'bool'>","holds":"tuple[ccf.erasure.contracts.LegalHold, ...]","minimum_age":"int | None","reasons":"tuple[str, ...]","severity_exempt":"<class 'bool'>"}`
- `ERASURE_APPROVAL_CLASS` — **constant**
  - `str`
- `ERASURE_RECORD_CLASS` — **constant**
  - `str`
- `ERASURE_SUBJECT_DECLARATION` — **constant**
  - `ArtifactClass`
- `ErasedAddress` — **contract**
  - `{"artifact_class":"<class 'str'>","content_address":"<class 'str'>","key_paths":"tuple[str, ...]","scope":"typing.Literal['whole']"}`
- `ErasureApproval` — **contract**
  - `{"acted_at":"<class 'datetime.datetime'>","approver":"<class 'ccf.hitl.principal.ApproverIdentity'>","attestation":"<class 'ccf.hitl.identity_binding.SignedHitlAction'>","gate":"<class 'str'>","gate_state_hash":"<class 'str'>","hitl_policy_ref":"<class 'str'>","request_id":"<class 'str'>","submission_hash":"<class 'str'>","tenant_id":"<class 'str'>","verdict":"<class 'str'>","workflow_definition_hash":"<class 'str'>"}`
- `ErasureRecord` — **contract**
  - `{"actor":"<class 'ccf.hitl.principal.ApproverIdentity'>","addresses":"tuple[ccf.erasure.contracts.ErasedAddress, ...]","approval_ref":"<class 'str'>","authorizing_decision_id":"<class 'str'>","erased_at":"<class 'datetime.datetime'>","legal_basis":"<class 'str'>","reason":"<class 'str'>","record_id":"<class 'str'>","request_id":"<class 'str'>","requested_by":"<class 'str'>","retention_decision":"<class 'ccf.erasure.contracts.RetentionDecision'>","subject_class":"<class 'str'>","subject_ref":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ErasureRequest` — **contract**
  - `{"addresses":"tuple[ccf.erasure.contracts.RequestedAddress, ...]","legal_basis":"<class 'str'>","reason":"<class 'str'>","retention_policy_ref":"<class 'str'>","subject_class":"<class 'str'>","subject_declaration_ref":"<class 'str'>","subject_ref":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ErasureSubjectClass` — **contract**
  - `{"artifact_classes":"tuple[str, ...]","class_id":"<class 'str'>","identifier_kind":"typing.Literal['opaque', 'principal']","key_paths":"tuple[str, ...]","subject_ref_salt":"<class 'str'>"}`
- `ErasureSubjectDeclaration` — **contract**
  - `{"semver":"<class 'str'>","subjects":"tuple[ccf.erasure.contracts.ErasureSubjectClass, ...]","tenant_id":"<class 'str'>"}`
- `ErasureSubjectLocator` — **class**
  - `(*args, **kwargs)`
- `LegalHold` — **contract**
  - `{"addresses":"tuple[str, ...] | None","basis":"<class 'str'>","hold_id":"<class 'str'>","placed_at":"<class 'datetime.datetime'>","placed_by":"<class 'str'>","subject_refs":"tuple[str, ...] | None"}`
- `REPLAY_INPUT_PATHS` — **constant**
  - `tuple`
- `RETENTION_HOLD_POLICY` — **constant**
  - `ArtifactClass`
- `RETENTION_REASON_CODES` — **constant**
  - `frozenset`
- `RequestedAddress` — **contract**
  - `{"artifact_class":"<class 'str'>","content_address":"<class 'str'>","retained_since":"<class 'datetime.datetime'>"}`
- `RetentionDecision` — **contract**
  - `{"address":"str | None","hold_id":"str | None","policy_ref":"<class 'str'>","reason_code":"typing.Literal['admitted', 'class-absent', 'not-erasable', 'severity-exempt', 'legal-hold', 'reason-unknown', 'under-minimum-age', 'policy-unresolvable', 'replay-input']","verdict":"typing.Literal['admit', 'refuse']"}`
- `RetentionHoldPolicy` — **contract**
  - `{"classes":"collections.abc.Mapping[str, ccf.erasure.contracts.ClassRetention]","semver":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `RetentionReasonCode` — **function**
  - `typing.Literal['admitted', 'class-absent', 'not-erasable', 'severity-exempt', 'legal-hold', 'reason-unknown', 'under-minimum-age', 'policy-unresolvable', 'replay-input']`
- `judge_retention` — **function**
  - `(policy: 'RetentionHoldPolicy', *, policy_ref: 'str', request: 'ErasureRequest', now: 'datetime') -> 'RetentionDecision'`
- `subject_ref_for` — **function**
  - `(declaration: 'ErasureSubjectDeclaration', subject_class: 'str', identifier: 'str') -> 'str'`

## `ccf.erasure.errors`

- `ErasedContentRefused` — **class**
  - `(*, content_address: 'str', erasure_record_address: 'str | None', reason: 'str | None', erased_at: 'datetime | None') -> 'None'`
- `ErasureCompositionRefused` — **class**
  - `type`
- `ErasureIndexCorrupt` — **class**
  - `(detail: 'str', *, content_address: 'str' = '') -> 'None'`
- `ErasureIndexInsecure` — **class**
  - `type`
- `ErasureIndexWriteFailed` — **class**
  - `type`
- `INDEX_CORRUPT` — **constant**
  - `str`

## `ccf.erasure.index`

- `ERASURE_INDEX_FILENAME` — **constant**
  - `str`
- `ErasureIndexEntry` — **contract**
  - `{"approval_ref":"<class 'str'>","content_address":"<class 'str'>","door_key_id":"<class 'str'>","door_signature":"<class 'str'>","erased_at":"<class 'datetime.datetime'>","erasure_record_address":"<class 'str'>","reason":"<class 'str'>","request_id":"<class 'str'>","subject_class":"<class 'str'>","subject_ref":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ErasureIndexEntryExists` — **class**
  - `type`
- `ErasureIndexProtocol` — **class**
  - `(*args, **kwargs)`
- `FileErasureIndex` — **class**
  - `(path: 'Path | str') -> 'None'`
- `GENESIS` — **constant**
  - `str`
- `erasure_index_at` — **function**
  - `(store_root: 'Path | str') -> 'FileErasureIndex'`
- `require_append_authority` — **function**
  - `(authorized: 'Authorized[ArtifactErase]', entry: 'ErasureIndexEntry') -> 'None'`

## `ccf.erasure.store`

- `ErasedContentRefused` — **class**
  - `(*, content_address: 'str', erasure_record_address: 'str | None', reason: 'str | None', erased_at: 'datetime | None') -> 'None'`
- `ErasureCompositionRefused` — **class**
  - `type`
- `ErasureConsultingStore` — **class**
  - `(inner: 'ArtifactStoreProtocol', *, index: 'ErasureIndexProtocol', audit_log: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'PinnedPolicySource', erasure_trust: 'ErasureTrust', tenant_id: 'str | None', identity_provider: 'IdentityProvider | None' = None, _verdicts: '_Verdicts | None' = None) -> 'None'`
- `ErasureIndexUnavailable` — **class**
  - `type`
- `INDEX_UNSUPPORTED` — **constant**
  - `str`
- `compose_erasure_consult` — **function**
  - `(store: 'ArtifactStoreProtocol', *, index: 'ErasureIndexProtocol', audit_log: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'PinnedPolicySource', erasure_trust: 'ErasureTrust', tenant_id: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'ErasureConsultingStore'`

## `ccf.erasure.subject_match`

- `DOOR_NAMING_CLASS` — **constant**
  - `str`
- `DoorNamingAnswer` — **contract**
  - `{"filed_by_record_writer":"<class 'bool'>","names":"tuple[ccf.artifacts.protocol.ArtifactName, ...]"}`
- `DoorNamingQuery` — **contract**
  - `{"content_address":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `SUBJECT_MATCH_CLASS` — **constant**
  - `str`
- `SubjectJudgment` — **function**
  - `typing.Literal['bytes-not-at-address', 'bytes-unparseable', 'subject-not-found', 'subject-in-replay-input', 'subject-found']`
- `SubjectMatchAnswer` — **contract**
  - `{"verdict":"typing.Literal['subject-unverifiable', 'subject-not-found', 'subject-in-replay-input', 'subject-found']"}`
- `SubjectMatchQuery` — **contract**
  - `{"content_address":"<class 'str'>","key_paths":"tuple[str, ...]","subject_ref":"<class 'str'>","subject_ref_salt":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `SubjectMatchSignatureInvalid` — **class**
  - `type`
- `SubjectMatchVerdict` — **function**
  - `typing.Literal['subject-unverifiable', 'subject-not-found', 'subject-in-replay-input', 'subject-found']`
- `judge_subject` — **function**
  - `(payload: 'bytes', query: 'SubjectMatchQuery') -> 'SubjectJudgment'`
- `sign_door_naming_query` — **function**
  - `(query: 'DoorNamingQuery', *, signer: 'IdentityProvider', key_id: 'str') -> 'str'`
- `sign_subject_match_query` — **function**
  - `(query: 'SubjectMatchQuery', *, signer: 'IdentityProvider', key_id: 'str') -> 'str'`
- `subject_match_verdict` — **function**
  - `(judgment: 'SubjectJudgment') -> 'SubjectMatchVerdict'`
- `verify_door_naming_query` — **function**
  - `(query: 'DoorNamingQuery', *, door_signature: 'str', authority: 'ErasureAuthority', identity_provider: 'IdentityProvider') -> 'None'`
- `verify_subject_match_query` — **function**
  - `(query: 'SubjectMatchQuery', *, door_signature: 'str', authority: 'ErasureAuthority', identity_provider: 'IdentityProvider') -> 'None'`

## `ccf.erasure.trust`

- `DOOR_SIGNATURE_ASSERTION` — **constant**
  - `str`
- `ErasureAuthority` — **contract**
  - `{"door_keys":"collections.abc.Mapping[str, collections.abc.Mapping[str, str]]","hitl_policy_key":"<class 'str'>","tenant_id":"<class 'str'>","workflow_definition_hash":"<class 'str'>"}`
- `ErasureRecordInvalid` — **class**
  - `(detail: 'str', *, reason_code: 'str') -> 'None'`
- `ErasureTrust` — **contract**
  - `{"authorities":"collections.abc.Mapping[str, ccf.erasure.trust.ErasureAuthority]"}`
- `sign_erasure_record` — **function**
  - `(record: 'ErasureRecord', *, signer: 'IdentityProvider', key_id: 'str') -> 'str'`
- `verify_door_signature` — **function**
  - `(payload: 'bytes', *, door_signature: 'str', door_key_id: 'str', authority: 'ErasureAuthority', identity_provider: 'IdentityProvider') -> 'None'`
- `verify_erasure_entry` — **function**
  - `(entry: 'ErasureIndexEntry', payload: 'bytes', *, trust: 'ErasureTrust', identity_provider: 'IdentityProvider') -> 'tuple[ErasureRecord, ErasureAuthority]'`

## `ccf.halflife`

- `debt` — **constant**
  - `module`
- `decay` — **constant**
  - `module`

## `ccf.halflife.assessment`

- `DebtAssessment` — **contract**
  - `{"debt":"<class 'decimal.Decimal'>","factors":"<class 'ccf.halflife.assessment.DebtFactors'>","scorers":"tuple[ccf.halflife.assessment.ScorerPin, ...]","signal":"<enum 'DebtSignal'>"}`
- `DebtEvidence` — **function**
  - `typing.Annotated[tuple[ccf.halflife.assessment.DebtEvidencePointer, ...], AfterValidator(func=<function _pointers_are_unique_and_canonically_ordered>)]`
- `DebtEvidencePointer` — **contract**
  - `{"handle":"<class 'str'>"}`
- `DebtFactorName` — **function**
  - `typing.Literal['freshness', 'completeness', 'semantic_consistency']`
- `DebtFactors` — **contract**
  - `{"completeness":"<class 'decimal.Decimal'>","freshness":"<class 'decimal.Decimal'>","semantic_consistency":"<class 'decimal.Decimal'>"}`
- `DebtSignal` — **class**
  - `(*values)`
- `NO_DEBT_EVIDENCE` — **constant**
  - `tuple`
- `NO_OBLIGATION_IN_FORCE` — **constant**
  - `str`
- `NO_SCORER_PINS` — **constant**
  - `tuple`
- `NO_SIGNAL_OBLIGATIONS` — **constant**
  - `tuple`
- `NO_SOURCE_REFRESH_RECENCY` — **constant**
  - `NoneType`
- `ObligationInForce` — **function**
  - `typing.Annotated[str, AfterValidator(func=<function _the_obligation_carried_is_declared_or_is_the_sentinel>)]`
- `ScorerPin` — **contract**
  - `{"factor":"typing.Literal['freshness', 'completeness', 'semantic_consistency']","scorer_id":"<class 'str'>","scorer_version":"<class 'str'>"}`
- `SignalObligation` — **contract**
  - `{"obligation_ref":"<class 'str'>","signal":"<enum 'DebtSignal'>"}`
- `SignalObligations` — **function**
  - `typing.Annotated[tuple[ccf.halflife.assessment.SignalObligation, ...], AfterValidator(func=<function _obligations_are_one_per_signal_in_canonical_order>)]`
- `SourceRefreshRecency` — **constant**
  - `ccf.halflife.assessment.SourceRefreshWindow | None`
- `SourceRefreshWindow` — **contract**
  - `{"newest_source_refresh_at":"<class 'datetime.datetime'>","oldest_source_refresh_at":"<class 'datetime.datetime'>"}`

## `ccf.halflife.debt`

- `DebtAssessment` — **contract**
  - `{"debt":"<class 'decimal.Decimal'>","factors":"<class 'ccf.halflife.assessment.DebtFactors'>","scorers":"tuple[ccf.halflife.assessment.ScorerPin, ...]","signal":"<enum 'DebtSignal'>"}`
- `DebtEvidence` — **function**
  - `typing.Annotated[tuple[ccf.halflife.assessment.DebtEvidencePointer, ...], AfterValidator(func=<function _pointers_are_unique_and_canonically_ordered>)]`
- `DebtEvidencePointer` — **contract**
  - `{"handle":"<class 'str'>"}`
- `DebtFactorName` — **function**
  - `typing.Literal['freshness', 'completeness', 'semantic_consistency']`
- `DebtFactorScorerProtocol` — **class**
  - `(*args, **kwargs)`
- `DebtFactors` — **contract**
  - `{"completeness":"<class 'decimal.Decimal'>","freshness":"<class 'decimal.Decimal'>","semantic_consistency":"<class 'decimal.Decimal'>"}`
- `DebtSignal` — **class**
  - `(*values)`
- `EmptyFactorCompositionError` — **class**
  - `type`
- `FreshnessScorer` — **class**
  - `(table: 'HalfLifeTable', risk_sensitivity: 'Decimal') -> None`
- `NO_DEBT_EVIDENCE` — **constant**
  - `tuple`
- `NO_OBLIGATION_IN_FORCE` — **constant**
  - `str`
- `NO_SCORER_PINS` — **constant**
  - `tuple`
- `NO_SIGNAL_OBLIGATIONS` — **constant**
  - `tuple`
- `NO_SOURCE_REFRESH_RECENCY` — **constant**
  - `NoneType`
- `ScorerPin` — **contract**
  - `{"factor":"typing.Literal['freshness', 'completeness', 'semantic_consistency']","scorer_id":"<class 'str'>","scorer_version":"<class 'str'>"}`
- `SignalObligation` — **contract**
  - `{"obligation_ref":"<class 'str'>","signal":"<enum 'DebtSignal'>"}`
- `SignalObligations` — **function**
  - `typing.Annotated[tuple[ccf.halflife.assessment.SignalObligation, ...], AfterValidator(func=<function _obligations_are_one_per_signal_in_canonical_order>)]`
- `SourceRefreshRecency` — **constant**
  - `ccf.halflife.assessment.SourceRefreshWindow | None`
- `SourceRefreshWindow` — **contract**
  - `{"newest_source_refresh_at":"<class 'datetime.datetime'>","oldest_source_refresh_at":"<class 'datetime.datetime'>"}`
- `assess_debt` — **function**
  - `(factors: 'DebtFactors', *, profile: 'DebtProfile', scorers: 'tuple[ScorerPin, ...]' = ()) -> 'DebtAssessment'`
- `basic_debt` — **function**
  - `(*, available: 'int', required: 'int') -> 'Decimal'`
- `compose_debt_factors` — **function**
  - `(own: 'DebtFactors', children: 'Sequence[DebtFactors]') -> 'DebtFactors'`
- `context_debt` — **function**
  - `(factors: 'DebtFactors') -> 'Decimal'`

## `ccf.halflife.decay`

- `HalfLifeEntry` — **contract**
  - `{"decay":"typing.Literal['curve', 'supersede-only']","decay_basis":"typing.Literal['observed-at', 'valid-from']","decay_driver":"<class 'str'>","freshness_over":"typing.Literal['series-mean', 'leading-edge']","half_life_seconds":"int | None","series_key_attribute":"str | None","supersession_event":"<class 'str'>"}`
- `HalfLifeTable` — **contract**
  - `{"entries":"collections.abc.Mapping[str, ccf.controlplane.artifacts.HalfLifeEntry]","semver":"<class 'str'>"}`
- `MissingDecayInstant` — **class**
  - `type`
- `MissingHalfLife` — **class**
  - `type`
- `NO_SUBJECT_IDENTITY` — **constant**
  - `str`
- `NoDecayCurve` — **class**
  - `type`
- `Observation` — **contract**
  - `{"observation_type":"<class 'str'>","observed_at":"<class 'datetime.datetime'>","series":"str | None","subject":"<class 'str'>","valid_from":"datetime.datetime | None"}`
- `TemporalOrderError` — **class**
  - `type`
- `decay_basis_of` — **function**
  - `(table: 'HalfLifeTable', observation_type: 'str') -> 'DecayBasis'`
- `decay_mode_of` — **function**
  - `(table: 'HalfLifeTable', observation_type: 'str') -> 'DecayMode'`
- `effective_half_life` — **function**
  - `(half_life: 'timedelta', risk_sensitivity: 'Decimal') -> 'timedelta'`
- `freshness` — **function**
  - `(observation: 'Observation', *, now: 'datetime', table: 'HalfLifeTable', risk_sensitivity: 'Decimal') -> 'Decimal'`
- `freshness_over_of` — **function**
  - `(table: 'HalfLifeTable', observation_type: 'str') -> 'FreshnessAggregation'`
- `half_life_of` — **function**
  - `(table: 'HalfLifeTable', observation_type: 'str') -> 'timedelta'`
- `leading_edge` — **function**
  - `(observations: 'Sequence[Observation]', *, table: 'HalfLifeTable', now: 'datetime') -> 'tuple[Observation, ...]'`
- `relevance_ratio` — **function**
  - `(*, elapsed: 'timedelta', half_life: 'timedelta') -> 'Decimal'`
- `series_key_attribute_of` — **function**
  - `(table: 'HalfLifeTable', observation_type: 'str') -> 'str | None'`
