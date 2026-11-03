# Context Products — SDK 1.0.2 Signatures

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Exact public shapes for Context Product contracts, requests, resolvers, composition, disclosure, gates, and related product surfaces.

This page is generated from `docs/surface/v0.2-surface.json` at `v1.0.2`. It is a lookup appendix; use the focused reference pages for semantics and examples.

> SDK 1.0.2 is tagged. Release status, deployment verification and the prior bank delivery remain separate; see [migration requirements](../MIGRATION_AND_LIMITATIONS.md).

## `ccf.products.bind`

- `refuse_bound_payload` — **function**
  - `(*, payload: 'Mapping[str, Any]', product_class: 'RegisteredProductClass', registry: 'ControlPlaneProtocol') -> 'PayloadSchemaViolation | None'`
- `resolve_declared_payload_schema` — **function**
  - `(*, product_class: 'RegisteredProductClass', registry: 'ControlPlaneProtocol') -> 'ProductPayloadSchema | None'`

## `ccf.products.child_resolver`

- `ChildArguments` — **function**
  - `collections.abc.Callable[[ccf.products.contract.ChildRequirement, ccf.products.request.ProductRequest], collections.abc.Mapping[str, str]]`
- `ChildQuestion` — **contract**
  - `{"freshness":"<class 'str'>","intent":"<class 'str'>","parameters":"collections.abc.Mapping[str, typing.Any]","subject":"<class 'str'>"}`
- `ChildQuestionReferenceMismatch` — **class**
  - `(*, fields: 'tuple[str, ...]') -> 'None'`
- `ChildQuestions` — **function**
  - `collections.abc.Callable[[ccf.products.contract.ChildRequirement, ccf.products.request.ProductRequest], ccf.products.child_resolver.ChildQuestion]`
- `ChildRecordAltered` — **class**
  - `type`
- `ChildRecordMismatch` — **class**
  - `type`
- `GrantBoundChildResolver` — **class**
  - `(*, ledger: 'GrantLedger', agent_definition_hash: 'str', gate: 'CompositeAdmissionGate', child_arguments: 'ChildArguments', callable_registry: 'CallableRegistry', artifact_store: 'ArtifactStoreProtocol', mcp_skills: 'McpSkillRegistry | None' = None, peering_skills: 'PeeringSkillRegistry | None' = None, peering_gate: 'PeeringAdmissionGate | None' = None, child_questions: 'ChildQuestions | None' = None, agent: 'AgentDefinition | None' = None) -> 'None'`
- `MalformedDoorAnswer` — **class**
  - `type`
- `QuestionBoundChildResolver` — **class**
  - `(*, ledger: 'GrantLedger', agent_definition_hash: 'str', gate: 'CompositeAdmissionGate', authorized: 'Authorized[ReplayMint]', child_questions: 'ChildQuestions', callable_registry: 'CallableRegistry', artifact_store: 'ArtifactStoreProtocol', mcp_skills: 'McpSkillRegistry | None' = None, peering_skills: 'PeeringSkillRegistry | None' = None, peering_gate: 'PeeringAdmissionGate | None' = None, child_arguments: 'ChildArguments | None' = None, agent: 'AgentDefinition | None' = None) -> 'None'`
- `QuestionRetentionUnauthorized` — **class**
  - `type`

## `ccf.products.composite`

- `ADMITTED_CHILD_CONTRACT_CLASS` — **constant**
  - `str`
- `AdmittedChild` — **class**
  - `(candidate: 'ChildCandidate', eligibility_basis: 'str', factors: 'DebtFactors', asked_at: 'datetime', composition_invocation: 'str', verified_address: 'str', evidence: "'EligibilityEvidence | None'", admitted_at: 'datetime', token: 'object') -> 'None'`
- `AgentConditionedChildResolverProtocol` — **class**
  - `(*args, **kwargs)`
- `AmbiguousProducerError` — **class**
  - `type`
- `CHILD_QUESTION_CLASS` — **constant**
  - `str`
- `CHILD_REFUSAL_REASONS` — **constant**
  - `frozenset`
- `ChildAcquisition` — **function**
  - `typing.Literal['local-dispatch', 'mcp', 'mcp-product', 'peered']`
- `ChildAdmissionBypassError` — **class**
  - `type`
- `ChildAdmissionRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>","producer_id":"str | None","producer_refusal_key":"str | None","producer_refusal_kind":"str | None","producer_refusal_reason":"str | None","producer_registration_address":"str | None","producer_replay_ref":"str | None","producer_server":"str | None","producer_tenant":"str | None","product_class":"<class 'str'>","question_address":"str | None","question_ref":"str | None","reason":"typing.Literal['class-mismatch', 'version-incompatible', 'as-of-mismatch', 'address-mismatch', 'debt-unassessable', 'ineligible', 'eligibility-evidence-missing', 'eligibility-evidence-mismatch', 'eligibility-evidence-stale', 'eligibility-bound-undeclared', 'composition-unwired', 'tenant-mismatch', 'provenance-unverified', 'no-producing-skill', 'ambiguous-producer', 'unauthorized', 'requirement-mismatch', 'undeclared-outcome', 'unsupported-outcome', 'mixing-refused', 'producer-tenant-mismatch', 'producer-mismatch', 'producer-unasserted', 'question-mismatch', 'producer-unavailable']","reported_content_address":"str | None","verified_content_address":"str | None"}`
- `ChildCandidate` — **class**
  - `(requirement: 'ChildRequirement', contract: 'ContextProductContract', content_address: 'str', invocation: "'ChildInvocation'", admission: 'AdmittedProduct | None' = None, producer_assertion: 'ProducerAssertion | None' = None, question_echo: "'WireRequest | None'" = None, answered_question: "'AnsweredQuestion | None'" = None, child_replay_ref: 'str | None' = None, asked_question: "'ChildQuestion | None'" = None) -> None`
- `ChildContractView` — **class**
  - `(contracts: 'Mapping[str, ContextProductContract]') -> 'None'`
- `ChildInvocation` — **class**
  - `(*, skill_name: 'str', entry_version: 'str', grant_hash: 'str', acquisition: 'ChildAcquisition', touched_entities: 'tuple[str, ...] | None', token: 'object', producer_id: 'str | None' = None, producer_tenant: 'str | None' = None, producer_registration_address: 'str | None' = None, producer_server: 'str | None' = None, question_address: 'str | None' = None, question_ref: 'str | None' = None) -> 'None'`
- `ChildOutcomeResolution` — **class**
  - `(rows: 'tuple[ChildResolution, ...]', admitted: 'tuple[AdmittedChild, ...]', admitted_factors: 'tuple[DebtFactors, ...]', refusal: 'ChildAdmissionRefusal | None') -> None`
- `ChildRefusalReason` — **function**
  - `typing.Literal['class-mismatch', 'version-incompatible', 'as-of-mismatch', 'address-mismatch', 'debt-unassessable', 'ineligible', 'eligibility-evidence-missing', 'eligibility-evidence-mismatch', 'eligibility-evidence-stale', 'eligibility-bound-undeclared', 'composition-unwired', 'tenant-mismatch', 'provenance-unverified', 'no-producing-skill', 'ambiguous-producer', 'unauthorized', 'requirement-mismatch', 'undeclared-outcome', 'unsupported-outcome', 'mixing-refused', 'producer-tenant-mismatch', 'producer-mismatch', 'producer-unasserted', 'question-mismatch', 'producer-unavailable']`
- `CompositeAdmissionGate` — **class**
  - `(*, tenant_id: 'str', consumer_scope: 'str', registry: 'ControlPlaneProtocol') -> 'None'`
- `CompositeChildResolverProtocol` — **class**
  - `(*, requirements: 'Sequence[ChildRequirement]', asked_at: 'datetime', admitted_at: 'datetime', composition_invocation: 'str', consumer_lineage: 'ProductLineage') -> 'Mapping[str, object]'`
- `CompositionOutcome` — **class**
  - `(factors: 'DebtFactors | None', resolutions: 'tuple[ChildResolution, ...]', refusal: 'ChildAdmissionRefusal | None', lineage: 'ProductLineage | None' = None, expires_at: 'datetime | None' = None, admitted_operators: 'frozenset[str]' = frozenset()) -> None`
- `ELIGIBILITY_LOCAL_REGISTER` — **constant**
  - `str`
- `ELIGIBILITY_PRODUCER_ATTESTED` — **constant**
  - `str`
- `ELIGIBILITY_PROVIDER_CONTROLS` — **constant**
  - `str`
- `EligibilityEvidence` — **class**
  - `(checked_at: 'datetime', assertion_address: 'str', producer: 'str') -> None`
- `GATE_CHILD_ADMISSION` — **constant**
  - `str`
- `ProvenanceForgeryError` — **class**
  - `type`
- `RequestAwareChildResolverProtocol` — **class**
  - `(*args, **kwargs)`
- `ResolvedProducer` — **class**
  - `(*, entry: 'SkillCatalogEntry', grant_hash: 'str', token: 'object') -> 'None'`
- `child_contract_view` — **function**
  - `(resolved: 'ChildOutcomeResolution') -> 'ChildContractView'`
- `compose_children` — **function**
  - `(*, own_factors: 'DebtFactors', requirements: 'Sequence[ChildRequirement]', outcomes: 'Mapping[str, object]', asked_at: 'datetime', composition_invocation: 'str', own_lineage: 'ProductLineage', max_ttl: 'MaxTTL', ttl_anchor_at: 'datetime', evaluated_at: 'datetime', validity_floors: 'ConstituentValidityFloors') -> 'CompositionOutcome'`
- `invocation_from_dispatch` — **function**
  - `(producer: 'ResolvedProducer', dispatched: 'object', *, touched_entities: 'tuple[str, ...] | None' = None, question_ref: 'str | None' = None) -> 'ChildInvocation'`
- `resolve_child_outcomes` — **function**
  - `(*, requirements: 'Sequence[ChildRequirement]', outcomes: 'Mapping[str, object]', asked_at: 'datetime', composition_invocation: 'str') -> 'ChildOutcomeResolution'`
- `resolve_producing_grant` — **function**
  - `(requirement: 'ChildRequirement', bound_skills: 'BoundSkillView') -> 'ResolvedProducer | None'`

## `ccf.products.composition`

- `ConstituentValidity` — **contract**
  - `{"constituent_id":"<class 'str'>","expires_at":"<class 'datetime.datetime'>","signal_type":"<class 'str'>"}`
- `EmptyCompositionError` — **class**
  - `type`
- `ExpiryDerivation` — **function**
  - `collections.abc.Callable[[collections.abc.Sequence[datetime.datetime]], datetime.datetime]`
- `MixingRefusal` — **contract**
  - `{"constituent_expires_at":"<class 'datetime.datetime'>","constituent_id":"<class 'str'>","detail":"<class 'str'>","evaluated_at":"<class 'datetime.datetime'>","floor_seconds":"<class 'int'>","signal_type":"<class 'str'>"}`
- `compose_expiry` — **function**
  - `(*, constituent_validities: 'Sequence[datetime]', max_ttl: 'MaxTTL', ttl_anchor_at: 'datetime', derivation: 'ExpiryDerivation' = <built-in function min>) -> 'datetime'`
- `compose_lineage` — **function**
  - `(lineages: 'Sequence[ProductLineage]') -> 'ProductLineage'`
- `refuse_mixing` — **function**
  - `(*, constituents: 'Sequence[ConstituentValidity]', floors: 'ConstituentValidityFloors', evaluated_at: 'datetime') -> 'MixingRefusal | None'`

## `ccf.products.constraints`

- `CAPABILITY_TRAVERSAL_DEPTH` — **constant**
  - `str`
- `ConstraintEffectivityConflict` — **class**
  - `type`
- `ConstraintRefusal` — **contract**
  - `{"bound":"<class 'ccf.products.provenance.ParameterBound'>","detail":"<class 'str'>","key":"<class 'str'>","overrides":"tuple[ccf.products.provenance.OverrideRecord, ...]","reason":"typing.Literal['bound-exceeded', 'not-in-allowed-set', 'required-absent']","requested":"typing.Any"}`
- `PinnedConstraint` — **contract**
  - `{"constraint":"<class 'ccf.controlplane.artifacts.PolicyConstraint'>","key":"<class 'str'>","version":"<class 'str'>"}`
- `PolicyConstraintResolver` — **class**
  - `(*args, **kwargs)`
- `PolicyResolutionConflict` — **contract**
  - `{"conflicting":"tuple[ccf.products.provenance.ProvenanceSource, ...]","detail":"<class 'str'>","key":"<class 'str'>","overrides":"tuple[ccf.products.provenance.OverrideRecord, ...]","reason":"typing.Literal['policy-resolution-conflict']"}`
- `REFERENCE_CONSTRAINT_RESOLVER_ID` — **constant**
  - `str`
- `REFERENCE_CONSTRAINT_RESOLVER_VERSION` — **constant**
  - `str`
- `ReferencePolicyConstraintResolver` — **class**
  - `(control_plane: '_ConstraintSource', entitlement_key: 'str | None') -> None`
- `ResolutionOutcome` — **contract**
  - `{"evidence":"<class 'ccf.products.provenance.EffectiveRequest'>","refusal":"ccf.products.constraints.ConstraintRefusal | ccf.products.constraints.PolicyResolutionConflict | ccf.products.request.ProductRequestViolation | None"}`
- `TechnicalCapability` — **contract**
  - `{"capability":"<class 'str'>","identity":"<class 'str'>","maximum":"<class 'decimal.Decimal'>"}`
- `applicable` — **function**
  - `(constraint: 'PolicyConstraint', *, product_class: 'str', tenant: 'str', perspective_role: 'str', intent: 'str', served_at: 'datetime') -> 'bool'`
- `constraints_in_force` — **function**
  - `(control_plane: '_ConstraintSource', *, served_at: 'datetime') -> 'tuple[PinnedConstraint, ...]'`
- `resolve_effective_request` — **function**
  - `(*, request: 'ProductRequest', declared: 'ProductRequestContract', declared_source: 'ProvenanceSource', constraints: 'tuple[PinnedConstraint, ...]', capabilities: 'tuple[TechnicalCapability, ...]', capability_bindings: 'Mapping[str, str]', verified_overrides: 'tuple[OverrideRecord, ...]', perspective: 'Perspective', tenant: 'str', served_at: 'datetime', class_defaults: 'Mapping[str, Any] | None' = None, class_source: 'ProvenanceSource | None' = None) -> 'ResolutionOutcome'`

## `ccf.products.contract`

- `AssemblyMode` — **function**
  - `typing.Literal['algorithmic', 'llm_packaged', 'swarm_assembled']`
- `ChildRequirement` — **contract**
  - `{"absence_treatment":"ccf.products.contract.OptionalAbsenceTreatment | None","compatible_from":"<class 'str'>","product_class":"<class 'str'>","required":"<class 'bool'>"}`
- `ComputedEmptyFinding` — **contract**
  - `{"emptiness":"typing.Literal['attested', 'unattested']","operators_invoked":"frozenset[str]","operators_returned_empty":"frozenset[str]","plan_id":"<class 'str'>"}`
- `ConstituentValidityFloors` — **contract**
  - `{"min_validity_seconds_by_signal":"collections.abc.Mapping[str, int]"}`
- `ContextProductContract` — **contract**
  - `{"computed_empty":"ccf.products.contract.ComputedEmptyFinding | None","debt":"ccf.halflife.assessment.DebtAssessment | None","debt_evidence":"tuple[ccf.halflife.assessment.DebtEvidencePointer, ...]","expires_at":"<class 'datetime.datetime'>","lineage":"<class 'ccf.products.contract.ProductLineage'>","obligation_in_force":"<class 'str'>","payload":"collections.abc.Mapping[str, typing.Any]","plan_id":"<class 'str'>","schema_name":"<class 'str'>","schema_version":"<class 'str'>","source_refresh_recency":"ccf.halflife.assessment.SourceRefreshWindow | None","temporal_boundary":"<class 'datetime.datetime'>","tenant_id":"<class 'str'>","ttl_anchor":"typing.Literal['from_decision', 'from_entity_freshness']","ttl_anchor_at":"datetime.datetime | None"}`
- `DeclaredProductGate` — **contract**
  - `{"gate_id":"<class 'str'>","gate_version":"<class 'str'>"}`
- `FreshnessSLA` — **contract**
  - `{"max_age_seconds_by_signal":"collections.abc.Mapping[str, int]"}`
- `MaxTTL` — **contract**
  - `{"seconds":"<class 'int'>"}`
- `NOT_ADDRESSABLE` — **constant**
  - `ProductAddress`
- `NOT_DISCOVERABLE` — **constant**
  - `ProductDiscovery`
- `NO_PAYLOAD_SCHEMA` — **constant**
  - `str`
- `NO_PRODUCT_GATE` — **constant**
  - `DeclaredProductGate`
- `NO_REQUEST_CONTRACT` — **constant**
  - `str`
- `NO_SERVE_OBLIGATIONS` — **constant**
  - `ServeObligations`
- `NO_VALIDITY_FLOORS` — **constant**
  - `ConstituentValidityFloors`
- `OptionalAbsenceTreatment` — **contract**
  - `{"completeness_when_absent":"<class 'decimal.Decimal'>","omissible_outcomes":"frozenset[str]"}`
- `ProductAddress` — **contract**
  - `{"address_template":"<class 'str'>"}`
- `ProductClassRegistrationError` — **class**
  - `type`
- `ProductDiscovery` — **contract**
  - `{"audiences":"frozenset[str]","capabilities":"frozenset[str]","domain":"<class 'str'>","intents":"frozenset[str]"}`
- `ProductLineage` — **contract**
  - `{"graph_snapshot_at":"<class 'datetime.datetime'>","operators_invoked":"frozenset[str]","policy_bundle_versions":"frozenset[str]"}`
- `RefusalCause` — **function**
  - `typing.Literal['nonexistent', 'unauthorized', 'undisclosed']`
- `RegisteredProductClass` — **contract**
  - `{"accepted_lineage_modes":"frozenset[typing.Literal['graph-supplied', 'product-carried', 'none']]","accepted_policy_binding_modes":"frozenset[typing.Literal['assembly-stamped', 'admission-verified', 'none']]","addressability":"<class 'ccf.products.contract.ProductAddress'>","assembly_mode":"typing.Literal['algorithmic', 'llm_packaged', 'swarm_assembled']","constituent_validity_floors":"<class 'ccf.products.contract.ConstituentValidityFloors'>","discovery":"<class 'ccf.products.contract.ProductDiscovery'>","freshness_sla":"<class 'ccf.products.contract.FreshnessSLA'>","max_ttl_key":"<class 'str'>","max_ttl_version":"<class 'str'>","payload_schema_key":"<class 'str'>","payload_schema_version":"<class 'str'>","request_contract_key":"<class 'str'>","request_contract_version":"<class 'str'>","requires":"tuple[ccf.products.contract.ChildRequirement, ...]","schema_name":"<class 'str'>","schema_version":"<class 'str'>","serve_obligations":"<class 'ccf.products.contract.ServeObligations'>","ttl_anchor":"typing.Literal['from_decision', 'from_entity_freshness']"}`
- `SUBJECT_WITHHOLDING_NEVER` — **constant**
  - `str`
- `SUBJECT_WITHHOLDING_POSSIBLE` — **constant**
  - `str`
- `SeamRefusalCause` — **function**
  - `typing.Union[typing.Literal['nonexistent', 'unauthorized', 'undisclosed'], typing.Literal['source-unavailable']]`
- `ServeObligations` — **contract**
  - `{"default_debt_tolerance":"decimal.Decimal | None","lineage_inputs_at":"frozenset[str]"}`
- `SubjectWithholding` — **function**
  - `typing.Literal['may-withhold', 'never']`
- `TTLAnchor` — **function**
  - `typing.Literal['from_decision', 'from_entity_freshness']`
- `UNMEASURED_FRESHNESS_SLA` — **constant**
  - `FreshnessSLA`
- `register_product_class` — **function**
  - `(*, registry: 'ControlPlaneProtocol', schema_name: 'str', schema_version: 'str', ttl_anchor: 'TTLAnchor', assembly_mode: 'AssemblyMode', max_ttl_key: 'str', max_ttl_version: 'str', accepted_policy_binding_modes: 'frozenset[PolicyBindingMode]' = frozenset({'assembly-stamped'}), accepted_lineage_modes: 'frozenset[LineageMode]' = frozenset({'graph-supplied'}), freshness_sla: 'FreshnessSLA' = FreshnessSLA(max_age_seconds_by_signal={}), discovery: 'ProductDiscovery' = ProductDiscovery(domain='not-discoverable', intents=frozenset(), capabilities=frozenset(), audiences=frozenset()), addressability: 'ProductAddress' = ProductAddress(address_template='not-addressable'), constituent_validity_floors: 'ConstituentValidityFloors' = ConstituentValidityFloors(min_validity_seconds_by_signal={}), payload_schema_key: 'str' = 'no-payload-schema', payload_schema_version: 'str' = 'no-payload-schema', request_contract_key: 'str' = 'no-request-contract', request_contract_version: 'str' = 'no-request-contract', requires: 'tuple[ChildRequirement, ...]' = (), serve_obligations: 'ServeObligations' = ServeObligations(default_debt_tolerance=None, lineage_inputs_at=frozenset())) -> 'RegisteredProductClass'`
- `requirements_declaration_is_coherent` — **function**
  - `(requires: 'tuple[ChildRequirement, ...]') -> 'None'`
- `version_satisfies_floor` — **function**
  - `(*, floor: 'str', version: 'str') -> 'bool'`

## `ccf.products.debt_scorer`

- `AssemblyDebtScorer` — **class**
  - `(*, table: 'HalfLifeTable', profile: 'DebtProfile', completeness: 'DebtFactorScorerProtocol', semantic_consistency: 'DebtFactorScorerProtocol') -> None`
- `DECLARED_FACTOR_SCORER_ID` — **constant**
  - `str`
- `DECLARED_FACTOR_SCORER_VERSION` — **constant**
  - `str`
- `DeclaredFactor` — **class**
  - `(value: 'Decimal') -> None`
- `EvidenceAwareFactorScorer` — **class**
  - `(*args, **kwargs)`
- `ExecutionEvidence` — **contract**
  - `{"operators_invoked":"frozenset[str]","operators_returned_empty":"frozenset[str]","queries_executed":"<class 'int'>","source_attestation":"ccf.graph.protocols.SourceAttestation | None","store_snapshot_pin":"<class 'ccf.graph.protocols.StoreSnapshotPin'>"}`
- `emptiness_of` — **function**
  - `(evidence: 'ExecutionEvidence') -> "Literal['attested', 'unattested']"`

## `ccf.products.demonstration_clock`

- `DeclaredServeClock` — **class**
  - `(pinned: 'PinnedDemonstrationServeInstant') -> None`
- `DemonstrationServeInstantConflict` — **class**
  - `(message: 'str', *, key: 'str') -> 'None'`
- `DemonstrationServeInstantRefused` — **class**
  - `(message: 'str', *, reason: 'RefusalReason', key: 'str') -> 'None'`
- `compose_serve_clock` — **function**
  - `(*, control_plane: 'ControlPlaneProtocol', fabric: 'BootedFabric', artifact_store: 'ArtifactStoreProtocol', admission_clock: 'Callable[[], datetime]', sdk_clock: 'Callable[[], datetime]') -> 'Callable[[], datetime]'`

## `ccf.products.disclosure`

- `DISCLOSURE_FULL` — **constant**
  - `str`
- `DISCLOSURE_LEVELS` — **constant**
  - `frozenset`
- `DISCLOSURE_MINIMAL` — **constant**
  - `str`
- `DisclosureDecision` — **contract**
  - `{"external_kind":"<class 'str'>","internal_kind":"<class 'str'>","level":"typing.Literal['minimal', 'reasoned', 'full']","policy":"ccf.products.provenance.ProvenanceSource | None","withheld":"tuple[str, ...]"}`
- `DisclosureLevel` — **function**
  - `typing.Literal['minimal', 'reasoned', 'full']`
- `EXTERNAL_STATEMENTS` — **constant**
  - `dict`
- `INDISTINGUISHABLE_BELOW_FULL` — **constant**
  - `dict`
- `PERMITTED_AT_MINIMAL` — **constant**
  - `dict`
- `SUPPRESSED_BELOW_FULL` — **constant**
  - `dict`
- `TRANSLATED_AT_MINIMAL` — **constant**
  - `dict`
- `WITHHELD` — **constant**
  - `str`
- `disclose` — **function**
  - `(envelope: 'RefusalEnvelope', *, level: 'DisclosureLevel', policy: 'ProvenanceSource | None') -> 'tuple[RefusalEnvelope, DisclosureDecision]'`

## `ccf.products.door`

- `AnsweredQuestion` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","freshness":"<class 'str'>","intent":"<class 'str'>","subject":"<class 'str'>"}`
- `DoorOutcome` — **contract**
  - `{"answered":"ccf.products.door.AnsweredQuestion | None","content_address":"str | None","producer":"ccf.products.producer.ProducerAssertion | None","product_json":"str | None","refusal":"ccf.products.refusal.RefusalEnvelope | None","replay_ref":"str | None","request":"<class 'ccf.products.door.WireRequest'>"}`
- `PRODUCT_REQUEST_TOOL` — **constant**
  - `str`
- `ProducerAssertion` — **contract**
  - `{"producer_id":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `ServedAnswer` — **class**
  - `(product: 'ContextProductContract', replay_ref: 'str') -> None`
- `UngovernedResolverResult` — **class**
  - `type`
- `WireRequest` — **contract**
  - `{"parameters":"collections.abc.Mapping[str, typing.Any]","product_id":"<class 'str'>","temporal_boundary":"datetime.datetime | None"}`
- `door_answer` — **function**
  - `(resolved: 'object', *, echo: 'WireRequest', resolved_request: 'ProductRequest', producer: 'ProducerAssertion | None' = None) -> 'bytes'`
- `door_question` — **function**
  - `(asked_json: 'str') -> 'WireRequest'`
- `door_refusal` — **function**
  - `(resolved: 'object') -> 'RefusalEnvelope | None'`
- `served_answer` — **function**
  - `(resolved: 'object') -> 'ServedAnswer'`

## `ccf.products.entitlement`

- `PRODUCT_ENTITLEMENT_POLICY` — **constant**
  - `ArtifactClass`
- `PrincipalNotEntitled` — **class**
  - `type`
- `ProductEntitlementGrant` — **contract**
  - `{"disclosure_level":"typing.Optional[typing.Literal['minimal', 'reasoned', 'full']]","overridable_policies":"frozenset[str]","permitted_roles":"frozenset[str]","permitted_schema_names":"frozenset[str]"}`
- `ProductEntitlementPolicy` — **contract**
  - `{"disclosure_level":"typing.Literal['minimal', 'reasoned', 'full']","evidence_readable_classes":"frozenset[str]","policy_version":"<class 'str'>","principals":"collections.abc.Mapping[str, ccf.products.entitlement.ProductEntitlementGrant]","tenant_id":"<class 'str'>"}`
- `ProductEntitlementViolation` — **class**
  - `type`
- `product_entitlement_key` — **function**
  - `(*, tenant_id: 'str') -> 'str'`

## `ccf.products.expiry`

- `FROM_DECISION` — **constant**
  - `str`
- `FROM_ENTITY_FRESHNESS` — **constant**
  - `str`
- `TTLAnchorResolution` — **contract**
  - `{"anchor_at":"<class 'datetime.datetime'>","basis":"typing.Literal['from_decision', 'from_entity_freshness']","contributing_types":"tuple[str, ...]"}`
- `TTLAnchorUndeclared` — **class**
  - `type`
- `refuse_undeclared_ttl_anchor` — **function**
  - `(*, ttl_anchor: 'str', entries: 'Mapping[str, object] | None', product_class: 'str') -> 'None'`
- `resolve_ttl_anchor` — **function**
  - `(*, ttl_anchor: 'TTLAnchor', view: 'GraphView | None', table: 'HalfLifeTable | None', decided_at: 'datetime', product_class: 'str') -> 'TTLAnchorResolution | TTLAnchorRefusal'`
- `valid_from_rows` — **function**
  - `(entries: 'Mapping[str, object] | None') -> 'tuple[str, ...]'`

## `ccf.products.gates`

- `AttestationRefusal` — **contract**
  - `{"accepted_modes":"frozenset[str]","detail":"<class 'str'>","failing_dimension":"typing.Literal['policy_binding', 'lineage']","gate":"<class 'str'>","source_mode":"<class 'str'>"}`
- `DEBT_TOLERANCE_PARAMETER` — **constant**
  - `str`
- `DeclaredObligationRefusal` — **contract**
  - `{"declared":"<class 'str'>","detail":"<class 'str'>","gate":"<class 'str'>","obligation":"typing.Literal['lineage-inputs']","observed":"<class 'str'>"}`
- `EmptyOperatorRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>"}`
- `EvidenceAfterDecisionRefusal` — **contract**
  - `{"decided_at":"<class 'datetime.datetime'>","detail":"<class 'str'>","reason":"typing.Literal['evidence-after-decision']"}`
- `GATE_DECLARED_OBLIGATIONS` — **constant**
  - `str`
- `GATE_EMPTY_OPERATOR` — **constant**
  - `str`
- `GATE_LINEAGE_ATTRIBUTABILITY` — **constant**
  - `str`
- `GATE_LINEAGE_EQUALITY` — **constant**
  - `str`
- `GATE_SOURCE_ATTESTATION` — **constant**
  - `str`
- `GATE_TTL_ANCHOR` — **constant**
  - `str`
- `GATE_TTL_BOUNDS` — **constant**
  - `str`
- `GateBypassError` — **class**
  - `type`
- `GateRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>"}`
- `LineageAttributionRefusal` — **contract**
  - `{"attested_address":"<class 'str'>","candidate_address":"<class 'str'>","declared":"frozenset[str]","detail":"<class 'str'>","gate":"<class 'str'>"}`
- `LineageMismatchRefusal` — **contract**
  - `{"declared":"frozenset[str]","detail":"<class 'str'>","gate":"<class 'str'>","resolved":"frozenset[str]"}`
- `PYDANTIC_MODEL_FORMS` — **constant**
  - `frozenset`
- `ProductInvariantRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>","gate_version":"<class 'str'>"}`
- `ServableProduct` — **class**
  - `(product: 'ContextProductContract', token: 'object') -> 'None'`
- `ServableProductNotAModel` — **class**
  - `type`
- `TTLAnchorRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>","now":"<class 'datetime.datetime'>","observation_types":"tuple[str, ...]","ttl_anchor":"<class 'str'>","valid_from_rows":"tuple[str, ...]"}`
- `TTLRefusal` — **contract**
  - `{"detail":"<class 'str'>","expires_at":"<class 'datetime.datetime'>","gate":"<class 'str'>","max_ttl_seconds":"<class 'int'>","now":"<class 'datetime.datetime'>"}`
- `ToleranceExceededRefusal` — **contract**
  - `{"authority":"typing.Literal['default', 'caller', 'policy', 'technical']","breakdown":"ccf.halflife.assessment.DebtAssessment | None","detail":"<class 'str'>","observed":"decimal.Decimal | None","source":"<class 'ccf.products.provenance.ProvenanceSource'>","tolerance":"<class 'decimal.Decimal'>"}`
- `refuse_attestation` — **function**
  - `(*, attestation: 'SourceAttestation | None', product_class: 'RegisteredProductClass') -> 'AttestationRefusal | None'`
- `refuse_dependency_invalidation` — **function**
  - `(candidate: 'ContextProductContract', *, touched_entities: 'tuple[str, ...] | None', registry: 'ControlPlaneProtocol') -> 'DependencyInvalidationRefusal | None'`
- `refuse_over_tolerance` — **function**
  - `(product: 'ServableProduct', *, tolerance: 'EffectiveParameter | None', policy_bound: 'ParameterBound | None') -> 'ToleranceExceededRefusal | ConstraintRefusal | None'`
- `run_federated_gates` — **function**
  - `(candidate: 'ContextProductContract', *, attested_address: 'str', now: 'datetime', registry: 'ControlPlaneProtocol', product_class: 'RegisteredProductClass') -> 'ServableProduct | GateRefusal'`
- `run_gates` — **function**
  - `(candidate: 'ContextProductContract', *, engine_resolved: 'frozenset[str]', now: 'datetime', registry: 'ControlPlaneProtocol', product_class: 'RegisteredProductClass', source_attestation: 'SourceAttestation | None' = None, touched_entities: 'tuple[str, ...] | None' = None) -> 'ServableProduct | GateRefusal'`
- `verify_gate_provenance` — **function**
  - `(product: 'object') -> "'ServableProduct'"`

## `ccf.products.payload`

- `PayloadSchemaViolation` — **contract**
  - `{"declared_keys":"frozenset[str]","declared_type":"str | None","detail":"<class 'str'>","key":"<class 'str'>","presented_keys":"frozenset[str]","presented_type":"str | None","reason":"typing.Literal['undeclared-key', 'missing-required-key', 'type-mismatch']"}`
- `PayloadViolationReason` — **function**
  - `typing.Literal['undeclared-key', 'missing-required-key', 'type-mismatch']`
- `ProductPayloadSchema` — **contract**
  - `{"properties":"collections.abc.Mapping[str, ccf.skills.catalog.SkillArgumentProperty]","required":"tuple[str, ...]"}`
- `refuse_payload` — **function**
  - `(*, payload: 'Mapping[str, Any]', declared: 'ProductPayloadSchema') -> 'PayloadSchemaViolation | None'`

## `ccf.products.producer`

- `ProducerAssertion` — **contract**
  - `{"producer_id":"<class 'str'>","tenant_id":"<class 'str'>"}`

## `ccf.products.product`

- `AcquireProtocol` — **class**
  - `(context: 'AcquisitionContext') -> 'Iterable[SignalEnvelope]'`
- `AcquisitionContext` — **class**
  - `(request: 'ProductRequest', perspective: 'Perspective', tenant_id: 'str', sources: 'Mapping[str, Mapping[str, str]]', instant: 'datetime') -> None`
- `AssessProtocol` — **class**
  - `(context: 'AssessmentContext') -> 'DebtAssessment'`
- `AssessmentContext` — **class**
  - `(view: 'GraphView', evidence: 'ExecutionEvidence | None', decided_at: 'datetime', half_life: 'HalfLifeTable | None', profile: 'DebtProfile | None', children: 'ChildContractView | None') -> None`
- `ChildResolverFactory` — **function**
  - `collections.abc.Callable[[ccf.products.product.ConsumerContext], ccf.products.composite.CompositeChildResolverProtocol | ccf.products.composite.RequestAwareChildResolverProtocol]`
- `ConsumerContext` — **class**
  - `(tenant_id: 'str', control_plane: 'ControlPlaneRegistry', artifact_store: 'ArtifactStoreProtocol', mcp_skills: 'McpSkillRegistry | None', clock: 'Callable[[], datetime]', derived_children: 'QuestionBoundChildResolver | None' = None, agent: 'AgentDefinition | None' = None) -> None`
- `DeclaredGrantRefused` — **class**
  - `(message: 'str', *, skill: 'str', refusal: 'object | None') -> 'None'`
- `GrantNotInForce` — **class**
  - `type`
- `OpenedProduct` — **class**
  - `(*, config_root: 'Path', config_path: 'Path', scratch: 'Path', evidence_root: 'Path', config: 'DeploymentConfig', environment: 'EnvironmentDocument', keys: 'DeploymentKeys', tenant_id: 'str', declaration: 'ProductClassDeclaration', replay: 'ReplayBinding', ttl: 'TtlBinding', door: 'EgressDoorBinding | None', default_perspective: 'PerspectiveArtifact', sources: 'Mapping[str, Mapping[str, str]] | None', control_plane: 'ControlPlaneRegistry', artifact_store: 'ArtifactStoreProtocol', erasure_index: 'ErasureIndexProtocol', erasure_trust: 'ErasureTrust', refusal_recorder: 'ReplayRefusalRecorder', acquire: 'AcquireProtocol', project: 'ProjectionPlanFactoryProtocol', assess: 'AssessProtocol', gate: 'ProductGateProtocol | None', clock: 'Callable[[], datetime]', constraint_resolver: 'PolicyConstraintResolver | None', capabilities: 'tuple[TechnicalCapability, ...] | None', children: 'CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None', packaging_trace: 'PackagingTraceProtocol | None' = None, mcp_skills: 'McpSkillRegistry | None' = None, bridge: 'SyncMcpBridge | None' = None, agent: 'AgentDefinition | None' = None, population: 'PopulationAcquireProtocol | None' = None, honors_demonstration_serve_instant: 'bool' = False, invalidation_sink: 'ControlPlaneInvalidationSink | None' = None) -> 'None'`
- `PopulationAcquireProtocol` — **class**
  - `(context: 'PopulationAcquisitionContext') -> 'Iterable[SignalEnvelope]'`
- `PopulationAcquisitionContext` — **class**
  - `(question: 'PopulationQuestion', perspective: 'Perspective', tenant_id: 'str', sources: 'Mapping[str, Mapping[str, str]]', instant: 'datetime') -> None`
- `SourcesNotRead` — **class**
  - `(what: 'str') -> 'None'`
- `open_product` — **function**
  - `(*, config_root: 'Path | str', scratch: 'Path | str', evidence_root: 'Path | str | None' = None, acquire: 'AcquireProtocol', project: 'ProjectionPlanFactoryProtocol', assess: 'AssessProtocol', gate: 'ProductGateProtocol | None' = None, questions: 'ChildQuestions | None' = None, clock: 'Callable[[], datetime]' = <function _utc_now>, environ: 'Mapping[str, str] | None' = None, read_sources: 'bool' = True, control_plane: 'ControlPlaneRegistry', erasure_trust: 'ErasureTrust', artifact_store: 'ArtifactStoreProtocol | None' = None, constraint_resolver: 'PolicyConstraintResolver | None' = None, capabilities: 'tuple[TechnicalCapability, ...] | None' = None, approval_sink: 'ApprovalSink | None' = None, children: 'CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None' = None, build_children: 'ChildResolverFactory | None' = None, packaging_trace: 'PackagingTraceProtocol | None' = None, erasure_index: 'ErasureIndexProtocol | None' = None, population: 'PopulationAcquireProtocol | None' = None) -> 'OpenedProduct'`

## `ccf.products.provenance`

- `AUTHORITIES` — **constant**
  - `frozenset`
- `Authority` — **function**
  - `typing.Literal['default', 'caller', 'policy', 'technical']`
- `EffectiveParameter` — **contract**
  - `{"authority":"typing.Literal['default', 'caller', 'policy', 'technical']","bound":"ccf.products.provenance.ParameterBound | None","name":"<class 'str'>","source":"<class 'ccf.products.provenance.ProvenanceSource'>","value":"typing.Any"}`
- `EffectiveRequest` — **contract**
  - `{"applied":"tuple[ccf.products.provenance.ProvenanceSource, ...]","asked_at":"<class 'datetime.datetime'>","guidance":"tuple[ccf.products.provenance.ParameterBound, ...]","overrides":"tuple[ccf.products.provenance.OverrideRecord, ...]","parameters":"tuple[ccf.products.provenance.EffectiveParameter, ...]"}`
- `OverrideRecord` — **contract**
  - `{"entitled":"<class 'bool'>","grant_source":"ccf.products.provenance.ProvenanceSource | None","honored":"<class 'bool'>","policy_id":"<class 'str'>","policy_version":"<class 'str'>","principal_id":"<class 'str'>"}`
- `ParameterBound` — **contract**
  - `{"authority":"typing.Literal['default', 'caller', 'policy', 'technical']","operator":"<class 'str'>","policy_id":"str | None","reason":"str | None","source":"<class 'ccf.products.provenance.ProvenanceSource'>","value":"typing.Any"}`
- `ProvenanceSource` — **contract**
  - `{"identity":"<class 'str'>","kind":"typing.Literal['artifact', 'request', 'capability']","version":"str | None"}`

## `ccf.products.refusal`

- `ErasedContentRefusal` — **contract**
  - `{"detail":"<class 'str'>","erased_at":"datetime.datetime | None","erasure_reason":"str | None","erasure_record_address":"str | None"}`
- `GovernedRefusalRaised` — **class**
  - `(refusal: 'object', *, resolution: 'object', request: 'RequestIdentity | None' = None) -> 'None'`
- `NON_PRODUCT_REFUSALS` — **constant**
  - `frozenset`
- `NON_VALUE_VIOLATIONS` — **constant**
  - `frozenset`
- `NO_REPLAY_REFERENCE` — **constant**
  - `str`
- `REFUSAL_KINDS` — **constant**
  - `dict`
- `RESOLVED_BY_THE_RESOLVER` — **constant**
  - `ResolvedByTheResolver`
- `RefusalEnvelope` — **contract**
  - `{"detail":"<class 'str'>","disclosure":"str | None","evidence":"ccf.products.refusal.RefusalEvidence | None","fields":"collections.abc.Mapping[str, str]","key":"str | None","kind":"<class 'str'>","policy_bindings":"tuple[ccf.products.provenance.ProvenanceSource, ...]","pre_assembly_lineage":"ccf.products.contract.ProductLineage | None","provenance":"ccf.products.provenance.EffectiveRequest | None","reason":"<class 'str'>","replay_reference":"<class 'str'>","request":"<class 'ccf.products.refusal.RequestIdentity'>","resource":"ccf.products.refusal.ResourceRequestIdentity | None"}`
- `RefusalEvidence` — **contract**
  - `{"computed_empty":"ccf.products.contract.ComputedEmptyFinding | None","debt":"ccf.halflife.assessment.DebtAssessment | None","operators_invoked":"frozenset[str]","plan_id":"<class 'str'>"}`
- `RequestIdentity` — **contract**
  - `{"parameters":"collections.abc.Mapping[str, typing.Any]","product_id":"<class 'str'>","product_version":"str | None","temporal_boundary":"datetime.datetime | None"}`
- `ResolvedByTheResolver` — **class**
  - `()`
- `ResourceRequestIdentity` — **contract**
  - `{"address":"<class 'str'>","determined_at":"<class 'datetime.datetime'>","surface":"<class 'str'>","tenant_from":"typing.Optional[typing.Literal['capability']]","tenant_id":"<class 'str'>"}`
- `SourceUnavailableRefusal` — **contract**
  - `{"detail":"<class 'str'>","error_code":"<class 'str'>"}`
- `SubjectUnavailableRefusal` — **contract**
  - `{"cause":"typing.Literal['nonexistent', 'unauthorized', 'undisclosed']","detail":"<class 'str'>","error_code":"str | None"}`
- `TemporalBoundRefusal` — **contract**
  - `{"detail":"<class 'str'>","max_past_seconds":"int | None","permitted_clock_skew_seconds":"int | None","policy_key":"<class 'str'>","presented_at":"datetime.datetime | None","reason":"typing.Literal['temporal-boundary-undeclared', 'asked-at-outside-temporal-bound', 'decision-instant-outside-temporal-bound']","served_at":"<class 'datetime.datetime'>"}`
- `envelope_for` — **function**
  - `(refusal: 'object', *, request: 'RequestIdentity', pre_assembly_lineage: 'ProductLineage | None' = None, policy_bindings: 'tuple[ProvenanceSource, ...]' = (), evidence: 'RefusalEvidence | None' = None, provenance: 'EffectiveRequest | None' = None, resource: 'ResourceRequestIdentity | None' = None) -> 'RefusalEnvelope'`
- `refuse_temporal_bound` — **function**
  - `(*, pinned: 'PinnedTemporalBoundary | TemporalBoundaryUndeclared', served_at: 'datetime', asked_at: 'datetime', decision_instant: 'datetime') -> 'TemporalBoundRefusal | None'`

## `ccf.products.request`

- `AnchorAmbiguityRefusal` — **contract**
  - `{"anchor":"<class 'str'>","candidates":"frozenset[str]","detail":"<class 'str'>"}`
- `ArgumentDomain` — **contract**
  - `{"maximum":"decimal.Decimal | None","members":"tuple[str | int | bool | decimal.Decimal, ...] | None","minimum":"decimal.Decimal | None","pattern":"str | None"}`
- `NO_REQUEST_CONTRACT` — **constant**
  - `str`
- `PARAMETER_VALUE_FLOOR_EXCLUSIONS` — **constant**
  - `mappingproxy`
- `PARAMETER_VALUE_FLOOR_V1` — **constant**
  - `Pattern`
- `PARAMETER_VALUE_FLOOR_VERSION` — **constant**
  - `str`
- `PRODUCT_REQUEST_CONTRACT` — **constant**
  - `ArtifactClass`
- `ProductRequest` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","freshness":"<class 'str'>","intent":"<class 'str'>","parameters":"collections.abc.Mapping[str, typing.Any]","policy_overrides":"tuple[str, ...]","schema_name":"<class 'str'>","schema_version":"<class 'str'>","subject":"<class 'str'>"}`
- `ProductRequestContract` — **contract**
  - `{"argument_domains":"collections.abc.Mapping[str, ccf.products.request.ArgumentDomain]","arguments":"<class 'ccf.skills.catalog.SkillArgumentSchema'>","capability_bindings":"collections.abc.Mapping[str, str]","defaults":"collections.abc.Mapping[str, typing.Any]","relative_defaults":"collections.abc.Mapping[str, ccf.products.request.RelativeDefault]","schema_name":"<class 'str'>","schema_version":"<class 'str'>","semver":"<class 'str'>","subject_domain":"ccf.products.request.ArgumentDomain | None","unsupported_arguments":"collections.abc.Mapping[str, str]"}`
- `ProductRequestViolation` — **contract**
  - `{"declared_keys":"frozenset[str]","declared_type":"str | None","detail":"<class 'str'>","key":"<class 'str'>","overrides":"tuple[ccf.products.provenance.OverrideRecord, ...]","presented_keys":"frozenset[str]","presented_type":"str | None","reason":"typing.Literal['undeclared-parameter', 'missing-required-parameter', 'type-mismatch', 'class-mismatch', 'not-supported-at-tier', 'not-a-proportion', 'below-minimum', 'above-maximum', 'not-in-domain', 'malformed-value']"}`
- `ProductRequestViolationReason` — **function**
  - `typing.Literal['undeclared-parameter', 'missing-required-parameter', 'type-mismatch', 'class-mismatch', 'not-supported-at-tier', 'not-a-proportion', 'below-minimum', 'above-maximum', 'not-in-domain', 'malformed-value']`
- `RelativeDefault` — **contract**
  - `{"offset_seconds":"<class 'int'>","render":"typing.Literal['date', 'timestamp']"}`
- `SUBJECT_FLOOR_V1` — **constant**
  - `Pattern`
- `SUBJECT_FLOOR_VERSION` — **constant**
  - `str`
- `decode_declared_request` — **function**
  - `(request: 'ProductRequest', declared: 'ProductRequestContract') -> 'ProductRequest'`
- `refuse_floor` — **function**
  - `(*, request: 'ProductRequest', declared: 'ProductRequestContract') -> 'ProductRequestViolation | None'`
- `refuse_intent` — **function**
  - `(*, request: 'ProductRequest', discovery: 'ProductDiscovery') -> 'ProductRequestViolation | None'`
- `refuse_request` — **function**
  - `(*, request: 'ProductRequest', declared: 'ProductRequestContract') -> 'ProductRequestViolation | None'`
- `refuse_request_contract_pin` — **function**
  - `(*, registry: 'ControlPlaneProtocol', schema_name: 'str', schema_version: 'str', request_contract_key: 'str', request_contract_version: 'str') -> 'ProductRequestContract | None'`
- `refuse_undeclared_class_default` — **function**
  - `(*, schema_name: 'str', schema_version: 'str', serve_obligations: 'ServeObligations', declared: 'ProductRequestContract | None') -> 'None'`
- `request_seeds` — **function**
  - `(request: 'ProductRequest | None') -> 'frozenset[str] | None'`

## `ccf.products.request_schema`

- `render_request_input_schema` — **function**
  - `(contract: 'ProductRequestContract') -> 'dict[str, Any]'`

## `ccf.products.resolver`

- `AcquiredFabricReused` — **class**
  - `type`
- `AcquisitionNeedsAQuestionFabric` — **class**
  - `type`
- `AcquisitionOverUnverifiableStore` — **class**
  - `type`
- `AcquisitionSeamProtocol` — **class**
  - `(*, request: 'ProductRequest', perspective: 'Perspective') -> 'None'`
- `AssemblyDebtScorerProtocol` — **class**
  - `(*, view: 'GraphView', evidence: 'ExecutionEvidence | None' = None) -> 'DebtAssessment'`
- `ChildAwareDebtScorerProtocol` — **class**
  - `(*args, **kwargs)`
- `CompositeNeedsAWithholdingStance` — **class**
  - `type`
- `CompositeNeedsAnEarlyPolicy` — **class**
  - `type`
- `CompositePlanFactoryProtocol` — **class**
  - `(*args, **kwargs)`
- `CompositeWithheldLate` — **class**
  - `type`
- `DEBT_SCORER_INPUTS` — **constant**
  - `tuple`
- `EARLY_POLICY_ACQUISITION_REFUSAL` — **constant**
  - `SubjectUnavailableRefusal`
- `EarlyPolicyNeedsRequestAwareChildren` — **class**
  - `type`
- `GovernedResolver` — **class**
  - `(*, fabric: 'BootedFabric', control_plane: 'ControlPlaneProtocol', product_class_key: 'str', request_contract_key: 'str', operator_parameter_keys: 'tuple[str, ...]', policy_bundle_key: 'str', debt_profile_key: 'str | None', plan_factory: 'ProjectionPlanFactoryProtocol', debt_scorer: 'AssemblyDebtScorerProtocol', product_gate: 'ProductGateProtocol | None', constraint_resolver: 'PolicyConstraintResolver', capabilities: 'tuple[TechnicalCapability, ...]', refusal_recorder: 'RefusalRecorderProtocol', artifact_store: 'ArtifactStoreProtocol', replay_record_class: 'str', query_pin_class: 'str', max_ttl_seconds: 'int', product_ttl_seconds: 'int', packaging_trace: 'PackagingTraceProtocol | None', composite_children: 'CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None', admission_clock: 'Callable[[], datetime]', decision_instant_parameter: 'str | None', source_refresh_recency: 'SourceRefreshRecency', acquisition: 'AcquisitionSeamProtocol | None', population_acquisition: 'PopulationAcquisitionSeamProtocol | None', half_life_key: 'str | None') -> None`
- `IncompatibleRefusalRecorder` — **class**
  - `type`
- `InstantAwareDebtScorerProtocol` — **class**
  - `(*args, **kwargs)`
- `NeverWithholdingContradicted` — **class**
  - `type`
- `NeverWithholdingNeedsAPositiveDeclaration` — **class**
  - `type`
- `NeverWithholdingProjectionCanWithhold` — **class**
  - `type`
- `NonWithholdingPlanFactoryProtocol` — **class**
  - `(*args, **kwargs)`
- `PackagingTraceProtocol` — **class**
  - `(*, product: 'ContextProductContract') -> 'PackagingTrace'`
- `PopulationAcquisitionSeamProtocol` — **class**
  - `(*, question: 'PopulationQuestion', perspective: 'Perspective') -> 'None'`
- `PopulationPhaseSharesAnOwner` — **class**
  - `type`
- `PopulationQuestion` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","freshness":"<class 'str'>","intent":"<class 'str'>","parameters":"collections.abc.Mapping[str, typing.Any]","schema_name":"<class 'str'>","schema_version":"<class 'str'>"}`
- `PopulationReadInSubjectKeyedPhase` — **class**
  - `type`
- `ProductGateProtocol` — **class**
  - `(*, candidate: 'ContextProductContract', evidence: 'ExecutionEvidence | None' = None) -> 'str | None'`
- `ProductNotResolvable` — **class**
  - `type`
- `ProjectionPlanFactoryProtocol` — **class**
  - `(*, required: 'tuple[str, ...]', request: 'ProductRequest') -> 'ProjectionPlan'`
- `QuestionStoreReopened` — **class**
  - `type`
- `RefusalRecorderProtocol` — **class**
  - `(*args, **kwargs)`
- `ReplayRefusalRecorder` — **class**
  - `(*, authorized: 'Authorized[ReplayMint]', artifact_store: 'ArtifactStoreProtocol', assembly_mode: 'AssemblyMode', policy_bundle_pin: 'PolicyBinding | None' = None, disclosure_level_for: 'Callable[..., tuple[DisclosureLevel, ProvenanceSource | None]]' = <factory>) -> None`
- `ResolverOutcome` — **constant**
  - `ccf.replay.serve.ServedProduct | ccf.products.refusal.RefusalEnvelope`
- `SHARED_OWNER_WALK_DEPTH` — **constant**
  - `int`
- `SHARED_OWNER_WALK_OBJECTS` — **constant**
  - `int`
- `ServedProductResolverProtocol` — **class**
  - `(*, tenant: 'str', product_class: 'str', version: 'str', perspective: 'Perspective', request: 'ProductRequest | None') -> 'ResolverOutcome'`
- `SharedOwnerWalkIncomplete` — **class**
  - `type`
- `SubjectDisclosingPlanFactoryProtocol` — **class**
  - `(*args, **kwargs)`
- `UNHELD_SUBJECT_PROBE` — **constant**
  - `str`
- `UNHELD_SUBJECT_PROBE_REFUSAL` — **constant**
  - `SubjectUnavailableRefusal`
- `UndeclaredMechanismClass` — **class**
  - `type`
- `UndisclosedSubjectAnswered` — **class**
  - `type`
- `UndisclosedSubjectSubstituteIsHeld` — **class**
  - `type`
- `UnheldSubjectProbeIsHeld` — **class**
  - `type`
- `UnmarkedStoreNotPresumedFresh` — **class**
  - `type`
- `UnsupportedComposition` — **class**
  - `type`
- `WithholdingClassListedReadable` — **class**
  - `type`
- `build_governed_resolver` — **function**
  - `(*, fabric: 'BootedFabric', control_plane: 'ControlPlaneProtocol', product_class_key: 'str', request_contract_key: 'str', operator_parameter_keys: 'tuple[str, ...]', policy_bundle_key: 'str', plan_factory: 'ProjectionPlanFactoryProtocol', erasure_index: 'ErasureIndexProtocol', erasure_trust: 'ErasureTrust', max_ttl_seconds: 'int | None' = None, product_ttl_seconds: 'int | None' = None, decision_instant_parameter: 'str | None' = None, source_refresh_recency: 'SourceRefreshRecency' = None, composite_children: 'CompositeChildResolverProtocol | RequestAwareChildResolverProtocol | None' = None, admission_clock: 'Callable[[], datetime]' = <function _utc_now>, artifact_store: 'ArtifactStoreProtocol | None' = None, replay_record_class: 'str | None' = None, query_pin_class: 'str | None' = None, artifact_store_root: 'Path | None' = None, half_life_key: 'str | None' = None, debt_profile_key: 'str | None' = None, declared_completeness: 'Decimal | None' = None, evidence_clock_key: 'str | None' = None, declared_semantic_consistency: 'Decimal | None' = None, debt_scorer: 'AssemblyDebtScorerProtocol | None' = None, product_gate: 'ProductGateProtocol | None' = None, constraint_resolver: 'PolicyConstraintResolver | None' = None, capabilities: 'tuple[TechnicalCapability, ...] | None' = None, refusal_recorder: 'RefusalRecorderProtocol | None' = None, acquisition: 'AcquisitionSeamProtocol | None' = None, packaging_trace: 'PackagingTraceProtocol | None' = None, population_acquisition: 'PopulationAcquisitionSeamProtocol | None' = None) -> 'GovernedResolver'`
- `declared_refusal_recorder` — **function**
  - `(*, control_plane: 'ControlPlaneProtocol', artifact_store: 'ArtifactStoreProtocol', replay_record_class: 'str', tenant_id: 'str', assembly_mode: 'AssemblyMode', policy_bundle_pin: 'PolicyBinding') -> 'ReplayRefusalRecorder'`
- `refuse_incompatible_refusal_recorder` — **function**
  - `(recorder: 'object', *, builder: 'str', keyword: 'str' = 'subject_withholding') -> 'None'`

## `ccf.products.subject_disclosure`

- `SubjectDisclosurePolicy` — **contract**
  - `{"by_principal":"collections.abc.Mapping[str, frozenset[str]]","by_role":"collections.abc.Mapping[str, frozenset[str]]","undisclosed_subject":"<class 'str'>"}`
