# Fabric L1–L5 — SDK 1.0.2 Signatures

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Exact public shapes for Signal, Assembly, Graph, Operators, Projection, and Similarity.

This page is generated from `docs/surface/v0.2-surface.json` at `v1.0.2`. It is a lookup appendix; use the focused reference pages for semantics and examples.

> SDK 1.0.2 is tagged. Release status, deployment verification and the prior bank delivery remain separate; see [migration requirements](../MIGRATION_AND_LIMITATIONS.md).

## `ccf.assembly.worker`

- `AssemblyWorker` — **class**
  - `(*, writer: 'GraphWriter', resolution: 'EntityResolutionStrategy', registry: 'ControlPlaneProtocol', policy_bundle_key: 'str', policy_bundle_version: 'str') -> 'None'`
- `EntityResolutionRule` — **contract**
  - `{"attribute_authorities":"collections.abc.Mapping[str, frozenset[str]]","attribute_keys":"tuple[str, ...]","entity_class":"<class 'str'>","identity_keys":"tuple[str, ...]","identity_sources":"collections.abc.Mapping[str, str]","match_key":"<class 'str'>"}`
- `EntityResolutionSpec` — **contract**
  - `{"entity_rules":"tuple[ccf.assembly.worker.EntityResolutionRule, ...]","relationship_rules":"tuple[ccf.assembly.worker.RelationshipResolutionRule, ...]","semver":"<class 'str'>"}`
- `EntityResolutionStrategy` — **class**
  - `(*args, **kwargs)`
- `FederatedIngestSpec` — **contract**
  - `{"payload_records_key":"<class 'str'>","record_key_aliases":"collections.abc.Mapping[str, str]","source_system_id":"<class 'str'>"}`
- `IdentityRefused` — **class**
  - `(*, envelope_id: 'str', entity_class: 'str', reason: 'str', key: 'str | None' = None, field: 'str | None' = None) -> 'None'`
- `IngestResult` — **contract**
  - `{"entities":"tuple[ccf.graph.protocols.UpsertResult, ...]","envelope_id":"<class 'str'>","policy_bundle_version":"<class 'str'>","refused_assertions":"tuple[ccf.assembly.worker.RefusedAssertion, ...]","relationships":"tuple[ccf.graph.protocols.UpsertResult, ...]","tenant_id":"<class 'str'>"}`
- `NO_RESOLVING_RULE` — **constant**
  - `str`
- `RefusedAssertion` — **contract**
  - `{"attribute":"<class 'str'>","entity_class":"<class 'str'>","entity_uri":"<class 'str'>","envelope_id":"<class 'str'>","source_system_id":"<class 'str'>"}`
- `RelationshipResolutionRule` — **contract**
  - `{"object_entity_class":"<class 'str'>","object_rule":"str | None","predicate_key":"str | None","relationship_type":"<class 'str'>","subject_entity_class":"<class 'str'>","subject_rule":"str | None"}`
- `ResolvedEntity` — **contract**
  - `{"attributes":"dict[str, str]","entity_class":"<class 'str'>","entity_uri":"<class 'str'>","resolved_by":"<class 'str'>"}`
- `SpecDrivenEntityResolution` — **class**
  - `(*, spec: 'EntityResolutionSpec') -> 'None'`

## `ccf.graph.backends.fluree`

- `DEFAULT_PARTITION` — **constant**
  - `str`
- `FLUREE_SUBSTRATE` — **constant**
  - `str`
- `FlureeGraphReader` — **class**
  - `(store: 'FlureeGraphStore') -> 'None'`
- `FlureeGraphStore` — **class**
  - `(*, url: 'str', partition: 'str' = 'ccf', ledger: 'str' = 'ccf:main', bearer_token: 'str | None' = None, writer_lease: 'WriterLeaseSource | None' = None) -> 'None'`
- `FlureePinAhead` — **class**
  - `type`
- `MAX_DEPTH_CEILING` — **constant**
  - `int`
- `MAX_QUERY_BODY_BYTES` — **constant**
  - `int`

## `ccf.graph.backends.fluree_write`

- `FlureeConnection` — **contract**
  - `{"partition":"str | None","url":"<class 'str'>","writer_lease_lock_dir":"typing.Optional[typing.Annotated[str, AfterValidator(func=<function require_absolute_lock_directory>), AfterValidator(func=<function require_private_lock_directory>)]]"}`
- `FlureeGraphWriter` — **class**
  - `(*, store: 'FlureeGraphStore', token: 'BootToken') -> 'None'`
- `REGISTRATION` — **constant**
  - `BackendRegistration`

## `ccf.graph.backends.memory`

- `MemoryGraphReader` — **class**
  - `(store: 'MemoryGraphStore') -> 'None'`
- `MemoryGraphStore` — **class**
  - `() -> 'None'`

## `ccf.graph.backends.memory_write`

- `MemoryConnection` — **contract**
  - `{}`
- `MemoryGraphWriter` — **class**
  - `(*, store: 'MemoryGraphStore', token: 'BootToken') -> 'None'`
- `REGISTRATION` — **constant**
  - `BackendRegistration`

## `ccf.graph.backends.mongo`

- `DEFAULT_DATABASE` — **constant**
  - `str`
- `DEFAULT_PARTITION` — **constant**
  - `str`
- `MongoGraphReader` — **class**
  - `(store: 'MongoGraphStore') -> 'None'`
- `MongoGraphStore` — **class**
  - `(*, uri: 'str', partition: 'str' = 'ccf', database: 'str | None' = None, writer_lease: 'WriterLeaseSource | None' = None) -> 'None'`

## `ccf.graph.backends.mongo_write`

- `MongoConnection` — **contract**
  - `{"partition":"str | None","uri":"<class 'str'>","writer_lease_lock_dir":"typing.Optional[typing.Annotated[str, AfterValidator(func=<function require_absolute_lock_directory>), AfterValidator(func=<function require_private_lock_directory>)]]"}`
- `MongoGraphWriter` — **class**
  - `(*, store: 'MongoGraphStore', token: 'BootToken') -> 'None'`
- `REGISTRATION` — **constant**
  - `BackendRegistration`

## `ccf.graph.backends.neo4j`

- `DEFAULT_PARTITION` — **constant**
  - `str`
- `MAX_DEPTH_CEILING` — **constant**
  - `int`
- `Neo4jGraphReader` — **class**
  - `(store: 'Neo4jGraphStore') -> 'None'`
- `Neo4jGraphStore` — **class**
  - `(*, uri: 'str', partition: 'str' = 'ccf', database: 'str | None' = None, writer_lease: 'WriterLeaseSource | None' = None) -> 'None'`

## `ccf.graph.backends.neo4j_write`

- `Neo4jConnection` — **contract**
  - `{"partition":"str | None","uri":"<class 'str'>","writer_lease_lock_dir":"typing.Optional[typing.Annotated[str, AfterValidator(func=<function require_absolute_lock_directory>), AfterValidator(func=<function require_private_lock_directory>)]]"}`
- `Neo4jGraphWriter` — **class**
  - `(*, store: 'Neo4jGraphStore', token: 'BootToken') -> 'None'`
- `REGISTRATION` — **constant**
  - `BackendRegistration`

## `ccf.graph.backends.postgres`

- `DEFAULT_SCHEMA` — **constant**
  - `str`
- `ENTITY_KIND` — **constant**
  - `str`
- `PostgresGraphReader` — **class**
  - `(connection: 'psycopg.Connection[dict[str, Any]]') -> 'None'`
- `PostgresGraphStore` — **class**
  - `(*, dsn: 'str', schema: 'str' = 'ccf') -> 'None'`
- `RELATIONSHIP_KIND` — **constant**
  - `str`

## `ccf.graph.backends.postgres_write`

- `PostgresConnection` — **contract**
  - `{"dsn":"<class 'str'>","schema_name":"<class 'str'>"}`
- `PostgresGraphWriter` — **class**
  - `(*, store: 'PostgresGraphStore', token: 'BootToken') -> 'None'`
- `REGISTRATION` — **constant**
  - `BackendRegistration`

## `ccf.graph.backends.sqlite`

- `ENTITY_KIND` — **constant**
  - `str`
- `RELATIONSHIP_KIND` — **constant**
  - `str`
- `SqliteGraphReader` — **class**
  - `(connection: 'sqlite3.Connection') -> 'None'`
- `SqliteGraphStore` — **class**
  - `(*, database_path: 'Path | str', writer_lease: 'WriterLeaseSource | None' = None) -> 'None'`

## `ccf.graph.backends.sqlite_write`

- `REGISTRATION` — **constant**
  - `BackendRegistration`
- `SqliteConnection` — **contract**
  - `{"database_path":"<class 'pathlib.Path'>","writer_lease_lock_dir":"typing.Optional[typing.Annotated[str, AfterValidator(func=<function require_absolute_lock_directory>), AfterValidator(func=<function require_private_lock_directory>)]]"}`
- `SqliteGraphWriter` — **class**
  - `(*, store: 'SqliteGraphStore', token: 'BootToken') -> 'None'`

## `ccf.graph.fallback`

- `answer` — **function**
  - `(entities: 'Sequence[EntityRecord]', relationships: 'Sequence[RelationshipRecord]', *, query: 'GraphQuery') -> 'tuple[tuple[EntityRecord, ...], tuple[RelationshipRecord, ...]]'`

## `ccf.graph.governed_reader`

- `governed_reader` — **function**
  - `(inner: 'GraphReader', authority: 'ClassificationAuthority') -> 'GraphReader'`

## `ccf.graph.leases`

- `AbsoluteLockDirectory` — **function**
  - `typing.Annotated[str, AfterValidator(func=<function require_absolute_lock_directory>), AfterValidator(func=<function require_private_lock_directory>)]`
- `LOCK_DIRECTORY_SETTING` — **constant**
  - `str`
- `LOCK_FILE_SUFFIX` — **constant**
  - `str`
- `LockFileWriterLease` — **class**
  - `(*, path: 'Path') -> 'None'`
- `SDK_MANAGED_LOCK_DIRECTORY` — **constant**
  - `str`
- `declared_lock_directory_lease` — **function**
  - `(lock_dir: 'str | None') -> 'WriterLeaseSource | None'`
- `lock_directory_writer_lease` — **function**
  - `(lock_dir: 'str | Path') -> 'WriterLeaseSource'`
- `lock_file_name` — **function**
  - `(graph_identity: 'str') -> 'str'`
- `require_absolute_lock_directory` — **function**
  - `(value: 'str') -> 'str'`
- `require_private_lock_directory` — **function**
  - `(value: 'str') -> 'str'`
- `sdk_managed_lock_directory` — **function**
  - `(base: 'str | Path') -> 'str'`

## `ccf.graph.product_source`

- `GATE_PRODUCT_MOUNT` — **constant**
  - `str`
- `ProductMountRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>","reason":"<class 'str'>","schema_name":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ProductSource` — **class**
  - `(*, admitted: 'AdmittedProduct', entities: 'tuple[EntityRecord, ...]', relationships: 'tuple[RelationshipRecord, ...]') -> 'None'`
- `mount_product_source` — **function**
  - `(*, admitted: 'AdmittedProduct') -> 'ProductSource | ProductMountRefusal'`

## `ccf.graph.protocols`

- `ClassificationAuthority` — **contract**
  - `{"governed":"collections.abc.Mapping[str, collections.abc.Mapping[str, frozenset[str]]]","spec_address":"<class 'str'>","written":"collections.abc.Mapping[str, frozenset[str]]"}`
- `ClassificationAuthorityMissing` — **class**
  - `(*, consumer: 'str') -> 'None'`
- `ClassificationAuthorityNotMinted` — **class**
  - `(*, consumer: 'str') -> 'None'`
- `EntityRecord` — **contract**
  - `{"claim":"<class 'ccf.contracts.claims.EntityClaim'>","claim_id":"<class 'str'>","policy_bundle_version":"<class 'str'>","superseded_at":"datetime.datetime | None","superseded_by":"str | None"}`
- `GraphQuery` — **contract**
  - `{"allowed_entities":"frozenset[str] | None","as_of":"<class 'datetime.datetime'>","classification_attribute_by_class":"collections.abc.Mapping[str, str] | None","permitted_classifications":"frozenset[str] | None","permitted_policy_bundle_versions":"frozenset[str] | None","require_valid_at_boundary":"bool | None","seeds":"frozenset[str] | None","tenant_id":"<class 'str'>","traverse":"ccf.graph.protocols.TraversalSpec | None"}`
- `GraphReader` — **class**
  - `(*args, **kwargs)`
- `GraphView` — **contract**
  - `{"as_of":"<class 'datetime.datetime'>","entities":"tuple[ccf.graph.protocols.EntityRecord, ...]","relationships":"tuple[ccf.graph.protocols.RelationshipRecord, ...]","tenant_id":"<class 'str'>"}`
- `GraphWriter` — **class**
  - `(*args, **kwargs)`
- `LineageMode` — **function**
  - `typing.Literal['graph-supplied', 'product-carried', 'none']`
- `NO_STORE_SNAPSHOT_PIN` — **constant**
  - `StoreSnapshotPin`
- `PolicyBindingMode` — **function**
  - `typing.Literal['assembly-stamped', 'admission-verified', 'none']`
- `ProcessScopedWriterLease` — **class**
  - `(*, substrate: 'str') -> 'None'`
- `QueryFragment` — **contract**
  - `{"classification_attribute_by_class":"collections.abc.Mapping[str, str] | None","permitted_classifications":"frozenset[str] | None","permitted_policy_bundle_versions":"frozenset[str] | None","require_valid_at_boundary":"bool | None","traverse":"ccf.graph.protocols.TraversalSpec | None"}`
- `RelationshipRecord` — **contract**
  - `{"claim":"<class 'ccf.contracts.claims.RelationshipClaim'>","claim_id":"<class 'str'>","policy_bundle_version":"<class 'str'>","relationship_key":"<class 'str'>","superseded_at":"datetime.datetime | None","superseded_by":"str | None"}`
- `SnapshotPinnable` — **class**
  - `(*args, **kwargs)`
- `SourceAttestation` — **contract**
  - `{"lineage":"typing.Literal['graph-supplied', 'product-carried', 'none']","peer":"ccf.peering.protocol.PeerRef | None","policy_binding":"typing.Literal['assembly-stamped', 'admission-verified', 'none']"}`
- `StoreSnapshotPin` — **contract**
  - `{"pin":"<class 'str'>","substrate":"<class 'str'>"}`
- `TEMPORAL_AXES` — **constant**
  - `tuple`
- `TemporalAxis` — **function**
  - `typing.Literal['event-time', 'transaction-time', 'as-of']`
- `TraversalDepthCapability` — **class**
  - `(*args, **kwargs)`
- `TraversalDirection` — **function**
  - `typing.Literal['undirected', 'forward']`
- `TraversalSpec` — **contract**
  - `{"admitted_entity_classes":"frozenset[str] | None","depth_limit":"<class 'int'>","direction":"typing.Literal['undirected', 'forward']","relationship_types":"frozenset[str]","seed_entity_classes":"frozenset[str]"}`
- `UngovernedClassificationAttribute` — **class**
  - `(*, operator_key: 'str', entity_class: 'str', attribute: 'str') -> 'None'`
- `UpsertResult` — **contract**
  - `{"claim_created":"<class 'bool'>","claim_id":"<class 'str'>","lineage_added":"<class 'int'>","node_key":"<class 'str'>","superseded_claim_id":"str | None"}`
- `WRITER_LEASE_SCOPES` — **constant**
  - `tuple`
- `WriterLease` — **class**
  - `(*args, **kwargs)`
- `WriterLeaseHeld` — **class**
  - `type`
- `WriterLeaseRequired` — **class**
  - `type`
- `WriterLeaseScope` — **function**
  - `typing.Literal['cross-process', 'process']`
- `WriterLeaseSource` — **function**
  - `collections.abc.Callable[[str], ccf.graph.protocols.WriterLease]`
- `acquire_declared_writer_lease` — **function**
  - `(source: 'WriterLeaseSource | None', *, substrate: 'str', graph_identity: 'str') -> 'WriterLease'`
- `require_classification_authority` — **function**
  - `(view: "'GraphView'", by_class: 'Mapping[str, str] | None', *, consumer: 'str') -> 'None'`
- `require_query_classification_authority` — **function**
  - `(q: "'GraphQuery'") -> 'None'`

## `ccf.graph.reader`

- `BaseGraphReader` — **class**
  - `()`
- `ENTITY_KIND` — **constant**
  - `str`
- `RELATIONSHIP_KIND` — **constant**
  - `str`
- `Row` — **class**
  - `(*args, **kwargs)`
- `parse_timestamp` — **function**
  - `(value: 'str | None') -> 'datetime | None'`

## `ccf.graph.registry`

- `AdapterPin` — **contract**
  - `{"name":"<class 'str'>","secret_refs":"tuple[str, ...]","version":"<class 'str'>"}`
- `BackendRegistration` — **class**
  - `(name: 'str', config_model: 'type[CCFContract]', secret_fields: 'frozenset[str]', open_store: 'Callable[[CCFContract, Mapping[str, SecretStr]], BackendStore]', make_writer: 'Callable[[BackendStore, BootToken], BaseGraphWriter]', development_reference: 'bool' = False) -> None`
- `BackendStore` — **class**
  - `(*args, **kwargs)`
- `DuplicateBackendName` — **class**
  - `type`
- `InvalidBackendConfig` — **class**
  - `type`
- `ReservedBackendName` — **class**
  - `type`
- `ResolvedBackend` — **class**
  - `(registration: 'BackendRegistration', version: 'str', distribution: 'str') -> None`
- `ResolvedSecret` — **contract**
  - `{"field":"<class 'str'>","ref_name":"<class 'str'>","value":"<class 'pydantic.types.SecretStr'>"}`
- `UnknownBackend` — **class**
  - `type`
- `declared_names` — **function**
  - `() -> 'frozenset[str]'`
- `is_sdk_development_reference` — **function**
  - `(name: 'str') -> 'bool'`
- `resolve` — **function**
  - `(name: 'str') -> 'ResolvedBackend'`
- `validate_connection` — **function**
  - `(registration: 'BackendRegistration', connection: 'Mapping[str, object]') -> 'CCFContract'`

## `ccf.operators.base`

- `CATEGORY_ORDER` — **constant**
  - `tuple`
- `Operator` — **class**
  - `(*args, **kwargs)`
- `OperatorCategory` — **function**
  - `typing.Literal['policy', 'similarity', 'temporal', 'traversal']`
- `OperatorOutput` — **contract**
  - `{"provenance":"<class 'ccf.operators.base.OperatorProvenance'>","view":"<class 'ccf.graph.protocols.GraphView'>"}`
- `OperatorParameters` — **contract**
  - `{}`
- `OperatorProvenance` — **contract**
  - `{"category":"typing.Literal['policy', 'similarity', 'temporal', 'traversal']","index_version":"str | None","operator_key":"<class 'str'>","parameter_hash":"<class 'str'>","upstream":"tuple[ccf.operators.base.OperatorProvenance, ...]"}`
- `PushableOperator` — **class**
  - `(*args, **kwargs)`
- `mint_provenance` — **function**
  - `(operator: 'Operator', *, upstream: 'tuple[OperatorProvenance, ...]', index_version: 'str | None' = None) -> 'OperatorProvenance'`
- `read_intent_of` — **function**
  - `(operator: 'Operator') -> 'QueryFragment | None'`

## `ccf.operators.categories`

- `PolicyFilter` — **class**
  - `(*, parameters: 'PolicyFilterParameters') -> 'None'`
- `PolicyFilterParameters` — **contract**
  - `{"classification_attribute_by_class":"collections.abc.Mapping[str, str]","permitted_classifications":"frozenset[str]","permitted_policy_bundle_versions":"frozenset[str]"}`
- `SimilaritySelect` — **class**
  - `(*, parameters: 'SimilaritySelectParameters', index: 'SimilarityIndexProtocol') -> 'None'`
- `SimilaritySelectParameters` — **contract**
  - `{"minimum_score_percent":"<class 'int'>","query":"<class 'str'>","ranked_entity_classes":"frozenset[str]"}`
- `TemporalAsOf` — **class**
  - `(*, parameters: 'TemporalAsOfParameters') -> 'None'`
- `TemporalAsOfParameters` — **contract**
  - `{"require_valid_at_boundary":"<class 'bool'>"}`
- `TraversalDescendants` — **class**
  - `(*, parameters: 'TraversalDescendantsParameters') -> 'None'`
- `TraversalDescendantsParameters` — **contract**
  - `{"admitted_entity_classes":"frozenset[str] | None","depth_limit":"<class 'int'>","relationship_types":"frozenset[str]","seed_entity_classes":"frozenset[str]"}`
- `TraversalNeighborhood` — **class**
  - `(*, parameters: 'TraversalNeighborhoodParameters') -> 'None'`
- `TraversalNeighborhoodParameters` — **contract**
  - `{"admitted_entity_classes":"frozenset[str] | None","depth_limit":"<class 'int'>","relationship_types":"frozenset[str]","seed_entity_classes":"frozenset[str]"}`

## `ccf.operators.params`

- `PolicyFilterParameters` — **contract**
  - `{"classification_attribute_by_class":"collections.abc.Mapping[str, str]","permitted_classifications":"frozenset[str]","permitted_policy_bundle_versions":"frozenset[str]"}`
- `SimilaritySelectParameters` — **contract**
  - `{"minimum_score_percent":"<class 'int'>","query":"<class 'str'>","ranked_entity_classes":"frozenset[str]"}`
- `TemporalAsOfParameters` — **contract**
  - `{"require_valid_at_boundary":"<class 'bool'>"}`
- `TraversalDescendantsParameters` — **contract**
  - `{"admitted_entity_classes":"frozenset[str] | None","depth_limit":"<class 'int'>","relationship_types":"frozenset[str]","seed_entity_classes":"frozenset[str]"}`
- `TraversalNeighborhoodParameters` — **contract**
  - `{"admitted_entity_classes":"frozenset[str] | None","depth_limit":"<class 'int'>","relationship_types":"frozenset[str]","seed_entity_classes":"frozenset[str]"}`

## `ccf.operators.planner`

- `ComposedOperator` — **class**
  - `(*, outer: 'Operator', inner: 'Operator', cache: 'IntermediateCache | None' = None) -> 'None'`
- `IntermediateCache` — **class**
  - `() -> 'None'`
- `OperatorPlan` — **class**
  - `(operators: 'tuple[Operator, ...]') -> None`
- `PlannedStep` — **contract**
  - `{"category":"typing.Literal['policy', 'similarity', 'temporal', 'traversal']","operator_key":"<class 'str'>","parameter_hash":"<class 'str'>","position":"<class 'int'>"}`
- `build_operator_plan` — **function**
  - `(*, registry: 'OperatorRegistry', required_operators: 'Sequence[str]') -> 'OperatorPlan'`
- `compose` — **function**
  - `(outer: 'Operator', inner: 'Operator', *, cache: 'IntermediateCache | None' = None) -> 'ComposedOperator'`

## `ccf.operators.registry`

- `DuplicateOperatorKey` — **class**
  - `type`
- `OperatorRegistration` — **class**
  - `(key: 'str', category: 'OperatorCategory', parameters_schema: 'type[OperatorParameters]', version: 'str | None', operator: 'Operator') -> None`
- `OperatorRegistry` — **class**
  - `() -> 'None'`
- `UnregisteredOperator` — **class**
  - `type`

## `ccf.projection.acquisition`

- `AcquiredContent` — **contract**
  - `{"content":"<class 'str'>","content_hash":"<class 'str'>","request":"<class 'ccf.projection.acquisition.ContentRequest'>"}`
- `AcquirerNotConfigured` — **class**
  - `type`
- `AcquisitionError` — **class**
  - `type`
- `ContentAcquirer` — **class**
  - `(*args, **kwargs)`
- `ContentAcquiringPlan` — **class**
  - `(*args, **kwargs)`
- `ContentRequest` — **contract**
  - `{"request_key":"<class 'str'>","selector":"<class 'str'>","source_key":"<class 'str'>"}`
- `ContentUnsatisfied` — **class**
  - `type`
- `UndeclaredAcquisition` — **class**
  - `type`
- `UnknownContentSource` — **class**
  - `type`

## `ccf.projection.engine`

- `AcquirerNotConfigured` — **class**
  - `type`
- `ContentUnsatisfied` — **class**
  - `type`
- `DuplicateOperatorKey` — **class**
  - `type`
- `ExecutionResult` — **contract**
  - `{"acquisitions":"tuple[ccf.projection.acquisition.AcquiredContent, ...]","empty_results":"frozenset[str]","executed_queries":"tuple[ccf.graph.protocols.GraphQuery, ...]","operators_invoked":"frozenset[str]","plan_id":"<class 'str'>","projection":"<class 'ccf.projection.plan.ProjectionOutput'>","provenance":"ccf.operators.base.OperatorProvenance | None","seeds":"frozenset[str] | None","source_attestation":"ccf.graph.protocols.SourceAttestation | None","steps":"tuple[ccf.projection.engine.ExecutionStep, ...]","store_snapshot_pin":"<class 'ccf.graph.protocols.StoreSnapshotPin'>","survivor_cap":"int | None","view":"<class 'ccf.graph.protocols.GraphView'>"}`
- `ExecutionStep` — **contract**
  - `{"category":"<class 'str'>","operator_key":"<class 'str'>","parameter_hash":"<class 'str'>"}`
- `OperatorRegistry` — **class**
  - `() -> 'None'`
- `ProjectionEngine` — **class**
  - `(*, reader: 'GraphReader', registry: 'OperatorRegistry', acquirer: 'ContentAcquirer | None' = None, survivor_cap: 'int | None' = None) -> 'None'`
- `UndeclaredAcquisition` — **class**
  - `type`
- `UnregisteredOperator` — **class**
  - `type`

## `ccf.projection.plan`

- `Perspective` — **contract**
  - `{"principal_id":"<class 'str'>","role":"<class 'str'>"}`
- `ProjectionOutput` — **contract**
  - `{"payload":"collections.abc.Mapping[str, typing.Any]","plan_id":"<class 'str'>","withheld":"<class 'bool'>"}`
- `ProjectionPlan` — **class**
  - `(*args, **kwargs)`

## `ccf.projection.segmentation`

- `FragmentFamilyConflict` — **class**
  - `type`
- `InProcessSegment` — **class**
  - `(operator_keys: 'tuple[str, ...]') -> None`
- `PushableSegment` — **class**
  - `(operator_keys: 'tuple[str, ...]', fragments: 'tuple[QueryFragment, ...]') -> None`
- `SegmentedPlan` — **class**
  - `(segments: 'tuple[PushableSegment | InProcessSegment, ...]') -> None`
- `compile_segment_query` — **function**
  - `(segment: 'PushableSegment', *, tenant_id: 'str', as_of: 'datetime', seeds: 'frozenset[str] | None', allowed_entities: 'frozenset[str] | None') -> 'GraphQuery'`
- `segment_plan` — **function**
  - `(operators: 'Sequence[Operator]') -> 'SegmentedPlan'`

## `ccf.signal`

- `envelope` — **constant**
  - `module`
- `source` — **constant**
  - `module`

## `ccf.signal.acquisition`

- `AcquisitionRecordError` — **class**
  - `type`
- `FileRecordAcquisitionSource` — **class**
  - `(*, path: 'Path', source: 'SourceIdentity', selectors: 'Mapping[str, Any] | None' = None, clock: 'Callable[[], datetime] | None' = None) -> 'None'`

## `ccf.signal.envelope`

- `IngressTemporalBound` — **class**
  - `(pinned: 'Mapping[str, object]') -> None`
- `SignalEnvelope` — **contract**
  - `{"envelope_id":"<class 'str'>","ingestion_timestamp":"<class 'datetime.datetime'>","observed_time":"datetime.datetime | None","raw_payload":"collections.abc.Mapping[str, typing.Any]","source":"<class 'ccf.signal.envelope.SourceIdentity'>","source_metadata":"collections.abc.Mapping[str, typing.Any]","tenant_id":"<class 'str'>"}`
- `SourceIdentity` — **contract**
  - `{"system_id":"<class 'str'>"}`
- `TemporalWriteRefused` — **class**
  - `(*, envelope_id: 'str', tenant_id: 'str', instant: 'datetime', policy_key: 'str', reason: 'str', detail: 'str') -> 'None'`
- `refuse_foreign_envelope` — **function**
  - `(envelope: 'SignalEnvelope', *, tenant_id: 'str', asked_at: 'datetime') -> 'None'`

## `ccf.signal.mcp_envelope_map`

- `BLOB_PAYLOAD_KEY` — **constant**
  - `str`
- `McpMappingError` — **class**
  - `type`
- `ResourceContents` — **constant**
  - `mcp.types.TextResourceContents | mcp.types.BlobResourceContents`
- `envelope_id_for` — **function**
  - `(*, system_id: 'str', resource_name: 'str', contents: 'ResourceContents') -> 'str'`
- `payload_of` — **function**
  - `(contents: 'ResourceContents') -> 'Mapping[str, Any]'`
- `source_metadata_of` — **function**
  - `(contents: 'ResourceContents', *, resource_name: 'str') -> 'Mapping[str, Any]'`
- `to_envelope` — **function**
  - `(contents: 'ResourceContents', *, tenant_id: 'str', system_id: 'str', resource_name: 'str', ingestion_timestamp: 'datetime') -> 'SignalEnvelope'`

## `ccf.signal.mcp_source`

- `MCPSourceAdapter` — **class**
  - `(*, system_id: 'str', client: 'McpResourceClient', resources: 'Mapping[str, str]', clock: 'Callable[[], datetime] | None' = None) -> 'None'`

## `ccf.signal.source`

- `SignalSourceProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf.similarity.chroma_index`

- `COLLECTION_PREFIX` — **constant**
  - `str`
- `ChromaIndex` — **class**
  - `(*, embedder: 'EmbedderProtocol', index_version: 'str', path: 'Path | None' = None) -> 'None'`

## `ccf.similarity.embedder`

- `EmbedderProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf.similarity.protocol`

- `MutableSimilarityIndexProtocol` — **class**
  - `(*args, **kwargs)`
- `SimilarityHit` — **contract**
  - `{"entity_uri":"<class 'str'>","score_percent":"<class 'int'>"}`
- `SimilarityIndexProtocol` — **class**
  - `(*args, **kwargs)`
- `TokenOverlapIndex` — **class**
  - `(*, index_version: 'str', corpus: 'Mapping[tuple[str, str], str] | None' = None) -> 'None'`
- `cosine_score_percent` — **function**
  - `(distance: 'float') -> 'int'`
- `order_hits` — **function**
  - `(hits: 'list[SimilarityHit]') -> 'tuple[SimilarityHit, ...]'`

## `ccf.similarity.sqlite_vec_index`

- `SqliteVecIndex` — **class**
  - `(*, connection: 'sqlite3.Connection', embedder: 'EmbedderProtocol', index_version: 'str', table: 'str' = 'ccf_similarity_vectors') -> 'None'`
