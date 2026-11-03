# Agents and Integration Extensions — SDK 1.0.2 Signatures

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Exact public shapes for agents, skills, workflows, harnesses, HITL, orchestration, peering, MCP, and related extension seams.

This page is generated from `docs/surface/v0.2-surface.json` at `v1.0.2`. It is a lookup appendix; use the focused reference pages for semantics and examples.

> SDK 1.0.2 is tagged. Release status, deployment verification and the prior bank delivery remain separate; see [migration requirements](../MIGRATION_AND_LIMITATIONS.md).

## `ccf.agents`

- `ARCHETYPES` — **constant**
  - `dict`
- `Agent` — **class**
  - `(*, definition: 'AgentDefinition', identity: 'AgentIdentity', components: 'tuple[ArchetypeComponent, ...]', instruction_artifacts: 'Mapping[str, PromptArtifact]', bound_skills: 'BoundSkillView | None', callable_registry: 'CallableRegistry | None' = None, mcp_skills: 'McpSkillRegistry | None' = None, peering_skills: 'PeeringSkillRegistry | None' = None) -> 'None'`
- `AgentFactory` — **class**
  - `(*, control_plane: 'ControlPlaneResolution', callable_registry: 'CallableRegistry | None' = None, mcp_skills: 'McpSkillRegistry | None' = None, peering_skills: 'PeeringSkillRegistry | None' = None, product_classes: 'Mapping[str, RegisteredProductClass] | None' = None) -> 'None'`
- `AgentIdentity` — **contract**
  - `{"archetype_composition":"tuple[str, ...]","definition_hash":"<class 'str'>","definition_uri":"<class 'str'>"}`
- `ArchetypeComponent` — **class**
  - `(*args, **kwargs)`
- `AssemblyOutcome` — **contract**
  - `{"acquisitions":"tuple[ccf.projection.acquisition.AcquiredContent, ...]","assembler_id":"<class 'str'>","assembler_version":"<class 'str'>","consultations":"<class 'ccf.agents.assembler.ConsultationRecord'>","halflife_debt_profile":"<class 'str'>","payload":"collections.abc.Mapping[str, typing.Any]","skill_set_in_force":"tuple[str, ...]"}`
- `ComposedArchetype` — **contract**
  - `{"archetype_ids":"tuple[str, ...]","conflicts":"tuple[ccf.agents.composition.DefaultConflict, ...]","defaults":"tuple[ccf.agents.archetypes.ConfigurationDefault, ...]","obligations":"tuple[ccf.agents.archetypes.ReplayObligation, ...]"}`
- `CompositionContradiction` — **class**
  - `type`
- `ConfigurationDefault` — **contract**
  - `{"name":"<class 'str'>","value":"<class 'str'>"}`
- `ConsultationRecord` — **contract**
  - `{"permitted":"tuple[str, ...]","refused":"tuple[str, ...]"}`
- `ContextAssemblerProtocol` — **class**
  - `(*args, **kwargs)`
- `ControlPlaneResolution` — **class**
  - `(*args, **kwargs)`
- `DETERMINISTIC_ASSEMBLER_ID` — **constant**
  - `str`
- `DETERMINISTIC_ASSEMBLER_VERSION` — **constant**
  - `str`
- `DefaultConflict` — **contract**
  - `{"key":"<class 'str'>","losing_archetype":"<class 'str'>","losing_value":"<class 'str'>","winning_archetype":"<class 'str'>","winning_value":"<class 'str'>"}`
- `DeterministicAssembler` — **class**
  - `(agent: 'Agent', projection: 'ProjectionOutput', acquisitions: 'tuple[AcquiredContent, ...]' = (), request_contract: 'ProductRequestContract | None' = None) -> None`
- `EmittedEffect` — **contract**
  - `{"agent_definition_hash":"<class 'str'>","payload":"collections.abc.Mapping[str, typing.Any]"}`
- `NO_CONSULTATIONS` — **constant**
  - `ConsultationRecord`
- `ReplayObligation` — **contract**
  - `{"name":"<class 'str'>","obligation":"<class 'str'>"}`
- `Task` — **class**
  - `(*, definition: 'TaskDefinition', identity: 'TaskIdentity', resolved_refs: 'Mapping[str, object]', instruction_artifacts: 'Mapping[str, PromptArtifact]') -> 'None'`
- `TaskFactory` — **class**
  - `(*, control_plane: 'ControlPlaneResolution') -> 'None'`
- `TaskIdentity` — **contract**
  - `{"definition_hash":"<class 'str'>","definition_uri":"<class 'str'>"}`
- `analytics_insights` — **constant**
  - `_AnalyticsInsightsComponent`
- `compose` — **function**
  - `(components: 'Sequence[ArchetypeComponent]') -> 'ComposedArchetype'`
- `content_generation` — **constant**
  - `_ContentGenerationComponent`
- `context_assembly` — **constant**
  - `_ContextAssemblyComponent`
- `document_intelligence` — **constant**
  - `_DocumentIntelligenceComponent`
- `monitoring_surveillance` — **constant**
  - `_MonitoringSurveillanceComponent`
- `workflow_task` — **constant**
  - `_WorkflowTaskComponent`

## `ccf.agents.agent`

- `Agent` — **class**
  - `(*, definition: 'AgentDefinition', identity: 'AgentIdentity', components: 'tuple[ArchetypeComponent, ...]', instruction_artifacts: 'Mapping[str, PromptArtifact]', bound_skills: 'BoundSkillView | None', callable_registry: 'CallableRegistry | None' = None, mcp_skills: 'McpSkillRegistry | None' = None, peering_skills: 'PeeringSkillRegistry | None' = None) -> 'None'`
- `AgentIdentity` — **contract**
  - `{"archetype_composition":"tuple[str, ...]","definition_hash":"<class 'str'>","definition_uri":"<class 'str'>"}`
- `EmittedEffect` — **contract**
  - `{"agent_definition_hash":"<class 'str'>","payload":"collections.abc.Mapping[str, typing.Any]"}`

## `ccf.agents.archetypes`

- `ARCHETYPES` — **constant**
  - `dict`
- `ArchetypeComponent` — **class**
  - `(*args, **kwargs)`
- `ConfigurationDefault` — **contract**
  - `{"name":"<class 'str'>","value":"<class 'str'>"}`
- `ReplayObligation` — **contract**
  - `{"name":"<class 'str'>","obligation":"<class 'str'>"}`
- `analytics_insights` — **constant**
  - `_AnalyticsInsightsComponent`
- `content_generation` — **constant**
  - `_ContentGenerationComponent`
- `context_assembly` — **constant**
  - `_ContextAssemblyComponent`
- `document_intelligence` — **constant**
  - `_DocumentIntelligenceComponent`
- `monitoring_surveillance` — **constant**
  - `_MonitoringSurveillanceComponent`
- `workflow_task` — **constant**
  - `_WorkflowTaskComponent`

## `ccf.agents.assembler`

- `AssemblyOutcome` — **contract**
  - `{"acquisitions":"tuple[ccf.projection.acquisition.AcquiredContent, ...]","assembler_id":"<class 'str'>","assembler_version":"<class 'str'>","consultations":"<class 'ccf.agents.assembler.ConsultationRecord'>","halflife_debt_profile":"<class 'str'>","payload":"collections.abc.Mapping[str, typing.Any]","skill_set_in_force":"tuple[str, ...]"}`
- `ConsultationRecord` — **contract**
  - `{"permitted":"tuple[str, ...]","refused":"tuple[str, ...]"}`
- `ContextAssemblerProtocol` — **class**
  - `(*args, **kwargs)`
- `DETERMINISTIC_ASSEMBLER_ID` — **constant**
  - `str`
- `DETERMINISTIC_ASSEMBLER_VERSION` — **constant**
  - `str`
- `DeterministicAssembler` — **class**
  - `(agent: 'Agent', projection: 'ProjectionOutput', acquisitions: 'tuple[AcquiredContent, ...]' = (), request_contract: 'ProductRequestContract | None' = None) -> None`
- `NO_CONSULTATIONS` — **constant**
  - `ConsultationRecord`

## `ccf.agents.composition`

- `ComposedArchetype` — **contract**
  - `{"archetype_ids":"tuple[str, ...]","conflicts":"tuple[ccf.agents.composition.DefaultConflict, ...]","defaults":"tuple[ccf.agents.archetypes.ConfigurationDefault, ...]","obligations":"tuple[ccf.agents.archetypes.ReplayObligation, ...]"}`
- `CompositionContradiction` — **class**
  - `type`
- `DefaultConflict` — **contract**
  - `{"key":"<class 'str'>","losing_archetype":"<class 'str'>","losing_value":"<class 'str'>","winning_archetype":"<class 'str'>","winning_value":"<class 'str'>"}`
- `compose` — **function**
  - `(components: 'Sequence[ArchetypeComponent]') -> 'ComposedArchetype'`

## `ccf.agents.definitions`

- `AGENT_DEFINITION` — **constant**
  - `ArtifactClass`
- `ARCHETYPE_IDS` — **constant**
  - `frozenset`
- `ASSEMBLY_ARCHETYPE_ID` — **constant**
  - `str`
- `AgentDefinition` — **contract**
  - `{"archetypes":"tuple[str, ...]","artifact_version":"<class 'str'>","context_contract":"<class 'ccf.agents.definitions.ContextContract'>","halflife_debt_profile":"<class 'ccf.agents.definitions.VersionedRef'>","instruction_bindings":"tuple[ccf.agents.definitions.InstructionBinding, ...]","name":"<class 'str'>","perspective":"<class 'ccf.agents.definitions.PerspectiveBinding'>","policy_regime":"<class 'ccf.agents.definitions.VersionedRef'>","schema_version":"<class 'str'>","tenant":"<class 'str'>"}`
- `ConsumedProduct` — **contract**
  - `{"product_class":"<class 'str'>","schema_version":"<class 'str'>"}`
- `ContextContract` — **contract**
  - `{"consumes":"tuple[ccf.agents.definitions.ConsumedProduct, ...]","emits":"tuple[ccf.agents.definitions.EmittedProduct, ...]"}`
- `EMITS_NOTHING` — **constant**
  - `tuple`
- `EmittedProduct` — **contract**
  - `{"product_class":"<class 'str'>","schema_version":"<class 'str'>"}`
- `InstructionBinding` — **contract**
  - `{"parameters":"tuple[str, ...]","prompt":"<class 'str'>"}`
- `PROMPT_ARTIFACT` — **constant**
  - `ArtifactClass`
- `PerspectiveBinding` — **contract**
  - `{"role":"<class 'str'>","selection_params":"collections.abc.Mapping[str, str]"}`
- `PromptArtifact` — **contract**
  - `{"artifact_version":"<class 'str'>","declared_parameters":"tuple[str, ...]","name":"<class 'str'>","schema_version":"<class 'str'>","template":"<class 'str'>","tenant":"<class 'str'>"}`
- `TASK_DEFINITION` — **constant**
  - `ArtifactClass`
- `TASK_STEP_KINDS` — **constant**
  - `frozenset`
- `TaskDefinition` — **contract**
  - `{"artifact_version":"<class 'str'>","instruction_bindings":"tuple[ccf.agents.definitions.InstructionBinding, ...]","name":"<class 'str'>","schema_version":"<class 'str'>","steps":"tuple[ccf.agents.definitions.TaskStep, ...]","tenant":"<class 'str'>"}`
- `TaskStep` — **contract**
  - `{"kind":"<class 'str'>","name":"<class 'str'>","ref":"str | None"}`
- `VersionedRef` — **contract**
  - `{"ref":"<class 'str'>"}`

## `ccf.agents.errors`

- `ASSEMBLY_REASON_TENANT_MISMATCH` — **constant**
  - `str`
- `ASSEMBLY_REASON_UNDECLARED_ROLE` — **constant**
  - `str`
- `AgentConstructionError` — **class**
  - `type`
- `AgentDefinitionError` — **class**
  - `type`
- `AssemblyRefusal` — **contract**
  - `{"detail":"<class 'str'>","reason":"<class 'str'>"}`
- `AssemblyRefused` — **class**
  - `type`
- `ConsumptionRefused` — **class**
  - `type`
- `FalseGrantClaimError` — **class**
  - `type`
- `NotYetBound` — **class**
  - `type`
- `PromptRenderRefused` — **class**
  - `type`
- `PromptValidationError` — **class**
  - `type`
- `SkillNotBound` — **class**
  - `type`

## `ccf.agents.factory`

- `AgentFactory` — **class**
  - `(*, control_plane: 'ControlPlaneResolution', callable_registry: 'CallableRegistry | None' = None, mcp_skills: 'McpSkillRegistry | None' = None, peering_skills: 'PeeringSkillRegistry | None' = None, product_classes: 'Mapping[str, RegisteredProductClass] | None' = None) -> 'None'`
- `ControlPlaneResolution` — **class**
  - `(*args, **kwargs)`
- `Task` — **class**
  - `(*, definition: 'TaskDefinition', identity: 'TaskIdentity', resolved_refs: 'Mapping[str, object]', instruction_artifacts: 'Mapping[str, PromptArtifact]') -> 'None'`
- `TaskFactory` — **class**
  - `(*, control_plane: 'ControlPlaneResolution') -> 'None'`
- `TaskIdentity` — **contract**
  - `{"definition_hash":"<class 'str'>","definition_uri":"<class 'str'>"}`

## `ccf.agents.prompts`

- `render_instruction` — **function**
  - `(*, binding: 'InstructionBinding', artifact: 'PromptArtifact', parameter_values: 'Mapping[str, str]') -> 'str'`
- `validate_instruction_binding` — **function**
  - `(binding: 'InstructionBinding', artifact: 'PromptArtifact') -> 'None'`
- `validate_prompt_artifact` — **function**
  - `(artifact: 'PromptArtifact') -> 'None'`

## `ccf.harness`

- `EffectCapability` — **function**
  - `typing.Literal['governed', 'unsupported']`
- `EffectRefusal` — **contract**
  - `{"agent_definition_hash":"<class 'str'>","harness_id":"<class 'str'>","reason":"<class 'str'>"}`
- `HarnessAdapterProtocol` — **class**
  - `(*args, **kwargs)`
- `HarnessCapabilities` — **contract**
  - `{"effects":"typing.Literal['governed', 'unsupported']","harness_id":"<class 'str'>"}`

## `ccf.harness.protocol`

- `EFFECT_CAPABILITIES` — **constant**
  - `frozenset`
- `EffectCapability` — **function**
  - `typing.Literal['governed', 'unsupported']`
- `EffectRefusal` — **contract**
  - `{"agent_definition_hash":"<class 'str'>","harness_id":"<class 'str'>","reason":"<class 'str'>"}`
- `HarnessAdapterProtocol` — **class**
  - `(*args, **kwargs)`
- `HarnessCapabilities` — **contract**
  - `{"effects":"typing.Literal['governed', 'unsupported']","harness_id":"<class 'str'>"}`

## `ccf.hitl`

- `APPROVAL_GATE_EVENT_CLASS` — **constant**
  - `str`
- `APPROVAL_POLICY` — **constant**
  - `ArtifactClass`
- `AUTHENTICATION_CLAIM` — **constant**
  - `str`
- `ApprovalGate` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ApprovalPolicy` — **contract**
  - `{"eligible_principals":"frozenset[str]","semver":"<class 'str'>"}`
- `ApprovalSinkAdapter` — **class**
  - `(*, resolution: 'GateResolution | None' = None) -> 'None'`
- `ApproverIdentity` — **contract**
  - `{"identity_provider_ref":"<class 'str'>","subject_id":"<class 'str'>"}`
- `ApproverNotEligible` — **class**
  - `type`
- `AttestationInvalid` — **class**
  - `type`
- `AuthenticationClaims` — **contract**
  - `{"assurance_level":"<class 'str'>","identity_provider_ref":"<class 'str'>","method":"<class 'str'>","session_ref":"<class 'str'>"}`
- `AuthenticationContext` — **contract**
  - `{"assurance_level":"<class 'str'>","method":"<class 'str'>","session_ref":"<class 'str'>"}`
- `ESCALATION_ACTIONS` — **constant**
  - `frozenset`
- `EscalationActionError` — **class**
  - `type`
- `EscalationActionRecord` — **contract**
  - `{"accepted":"<class 'bool'>","event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>","trigger":"ccf.hitl.escalation.ExplicitEscalation | ccf.halflife.assessment.DebtAssessment"}`
- `EscalationHandOff` — **contract**
  - `{"event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","trigger":"ccf.hitl.escalation.ExplicitEscalation | ccf.halflife.assessment.DebtAssessment"}`
- `EscalationRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `EscalationResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","record":"<class 'ccf.hitl.escalation.EscalationActionRecord'>"}`
- `EscalationResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `ExceptionEscalation` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ExplicitEscalation` — **contract**
  - `{"reason":"<class 'str'>"}`
- `GATE_ACTIONS` — **constant**
  - `frozenset`
- `GateActionError` — **class**
  - `type`
- `GateResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","outcome":"<class 'ccf.skills.grants.ApprovalOutcome'>","record":"<class 'ccf.hitl.approval_gate.HitlActionRecord'>"}`
- `GateResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `HITLTransportProtocol` — **class**
  - `(*args, **kwargs)`
- `HITL_ACTIONS` — **constant**
  - `frozenset`
- `HITL_ACTION_ARTIFACT_CLASS` — **constant**
  - `str`
- `HITL_EVENT_CLASSES` — **constant**
  - `frozenset`
- `HitlActionClaims` — **contract**
  - `{"action":"<class 'str'>","event_key":"<class 'str'>","issued_at":"<class 'datetime.datetime'>","nonce":"<class 'str'>","product_content_hash":"<class 'str'>","subject_id":"<class 'str'>","tenant":"<class 'str'>"}`
- `HitlActionReceipt` — **contract**
  - `{"event_pending":"<class 'bool'>","status":"typing.Literal['submitted']","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>","submissions_for_event":"<class 'int'>"}`
- `HitlActionRecord` — **contract**
  - `{"approved":"<class 'bool'>","event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>"}`
- `HitlActionRequest` — **contract**
  - `{"action":"<class 'str'>","annotation":"str | None","attestation":"ccf.hitl.identity_binding.SignedHitlAction | None","event_key":"<class 'str'>","product_content_hash":"<class 'str'>"}`
- `HitlActionSubmission` — **contract**
  - `{"action":"<class 'str'>","annotation":"str | None","answered_event_class":"str | None","answered_workflow_state_ref":"str | None","approval_policy_ref":"str | None","attestation":"ccf.hitl.identity_binding.SignedHitlAction | None","authorizing_decision_id":"str | None","event_key":"<class 'str'>","event_state_at_submit":"typing.Optional[typing.Literal['claimed', 'pending', 'missing']]","hitl_policy_ref":"str | None","principal":"<class 'ccf.hitl.principal.HumanPrincipalBinding'>","requested_by":"str | None"}`
- `HitlEventNotification` — **contract**
  - `{"endpoint_key":"<class 'str'>","event":"<class 'ccf.hitl.transport.PendingHitlEvent'>"}`
- `HitlEventRevalidationRefused` — **class**
  - `type`
- `HumanPrincipalBinding` — **contract**
  - `{"action_time":"<class 'datetime.datetime'>","approver":"<class 'ccf.hitl.principal.ApproverIdentity'>","authentication":"<class 'ccf.hitl.principal.AuthenticationContext'>","product_content_hash":"<class 'str'>","verdict":"<class 'str'>"}`
- `InMemoryHitlTransport` — **class**
  - `(*, control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `OverrideActionRecord` — **contract**
  - `{"event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","final":"~ProductT","original":"~ProductT","overridden":"<class 'bool'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>"}`
- `OverrideBoundary` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `OverrideResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","record":"<class 'ccf.hitl.override.OverrideActionRecord'>"}`
- `OverrideResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `PendingHitlEvent` — **contract**
  - `{"event_class":"<class 'str'>","event_key":"<class 'str'>","policy_ref":"str | None","product_content_hash":"<class 'str'>","requested_by":"str | None","tenant":"<class 'str'>","workflow_state_ref":"<class 'str'>"}`
- `PrincipalMismatchRefused` — **class**
  - `type`
- `RecordingWebhookDeliverer` — **class**
  - `() -> 'None'`
- `ReviewActionRecord` — **contract**
  - `{"event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","item":"<class 'ccf.hitl.review_queue.ReviewQueueItem'>","released":"<class 'bool'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>"}`
- `ReviewQueue` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ReviewQueueItem` — **contract**
  - `{"lineage":"tuple[ccf.contracts.claims.LineageEntry, ...]","output_ref":"<class 'str'>"}`
- `ReviewResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","record":"<class 'ccf.hitl.review_queue.ReviewActionRecord'>"}`
- `ReviewResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `SignedHitlAction` — **contract**
  - `{"claims":"<class 'ccf.hitl.identity_binding.HitlActionClaims'>","key_id":"<class 'str'>","signature":"<class 'str'>"}`
- `UnboundDecisionError` — **class**
  - `type`
- `UnknownEscalationEventError` — **class**
  - `type`
- `UnknownGateEventError` — **class**
  - `type`
- `UnknownOverrideEventError` — **class**
  - `type`
- `UnknownReviewEventError` — **class**
  - `type`
- `WebhookDeliveryOutcome` — **contract**
  - `{"delivered":"<class 'bool'>","endpoint_key":"<class 'str'>","error":"str | None"}`
- `WebhookDeliveryProtocol` — **class**
  - `(*args, **kwargs)`
- `WebhookEndpoint` — **contract**
  - `{"endpoint_key":"<class 'str'>","tenant":"<class 'str'>","url":"<class 'str'>"}`
- `WebhookEndpointConflict` — **class**
  - `type`
- `WebhookHitlNotifier` — **class**
  - `(*, deliverer: 'WebhookDeliveryProtocol', endpoints: 'tuple[WebhookEndpoint, ...]') -> 'None'`
- `check_approver_eligibility` — **function**
  - `(*, policy_ref: 'str | None', requested_by: 'str | None', subject_id: 'str', control_plane: 'object | None') -> 'None'`
- `sign_hitl_action` — **function**
  - `(claims: 'HitlActionClaims', *, provider: 'IdentityProvider', key_id: 'str') -> 'SignedHitlAction'`
- `verify_hitl_action` — **function**
  - `(signed: 'SignedHitlAction', *, provider: 'IdentityProvider', public_keys: 'Mapping[str, JsonWebKey]') -> 'HitlActionClaims'`

## `ccf.hitl.approval_gate`

- `ApprovalGate` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ApprovalSinkAdapter` — **class**
  - `(*, resolution: 'GateResolution | None' = None) -> 'None'`
- `GATE_ACTIONS` — **constant**
  - `frozenset`
- `GATE_APPROVE` — **constant**
  - `str`
- `GATE_EVENT_CLASS` — **constant**
  - `str`
- `GateActionError` — **class**
  - `type`
- `GateResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","outcome":"<class 'ccf.skills.grants.ApprovalOutcome'>","record":"<class 'ccf.hitl.approval_gate.HitlActionRecord'>"}`
- `GateResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `HITL_ACTION_ARTIFACT_CLASS` — **constant**
  - `str`
- `HitlActionRecord` — **contract**
  - `{"approved":"<class 'bool'>","event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>"}`
- `UnboundDecisionError` — **class**
  - `type`
- `UnknownGateEventError` — **class**
  - `type`

## `ccf.hitl.approval_policy`

- `APPROVAL_POLICY` — **constant**
  - `ArtifactClass`
- `ApprovalPolicy` — **contract**
  - `{"eligible_principals":"frozenset[str]","semver":"<class 'str'>"}`

## `ccf.hitl.escalation`

- `ESCALATION_ACTIONS` — **constant**
  - `frozenset`
- `ESCALATION_EVENT_CLASS` — **constant**
  - `str`
- `EscalationActionError` — **class**
  - `type`
- `EscalationActionRecord` — **contract**
  - `{"accepted":"<class 'bool'>","event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>","trigger":"ccf.hitl.escalation.ExplicitEscalation | ccf.halflife.assessment.DebtAssessment"}`
- `EscalationHandOff` — **contract**
  - `{"event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","trigger":"ccf.hitl.escalation.ExplicitEscalation | ccf.halflife.assessment.DebtAssessment"}`
- `EscalationRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `EscalationResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","record":"<class 'ccf.hitl.escalation.EscalationActionRecord'>"}`
- `EscalationResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `ExceptionEscalation` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ExplicitEscalation` — **contract**
  - `{"reason":"<class 'str'>"}`
- `UnknownEscalationEventError` — **class**
  - `type`

## `ccf.hitl.identity_binding`

- `AttestationInvalid` — **class**
  - `type`
- `HitlActionClaims` — **contract**
  - `{"action":"<class 'str'>","event_key":"<class 'str'>","issued_at":"<class 'datetime.datetime'>","nonce":"<class 'str'>","product_content_hash":"<class 'str'>","subject_id":"<class 'str'>","tenant":"<class 'str'>"}`
- `SignedHitlAction` — **contract**
  - `{"claims":"<class 'ccf.hitl.identity_binding.HitlActionClaims'>","key_id":"<class 'str'>","signature":"<class 'str'>"}`
- `sign_hitl_action` — **function**
  - `(claims: 'HitlActionClaims', *, provider: 'IdentityProvider', key_id: 'str') -> 'SignedHitlAction'`
- `verify_hitl_action` — **function**
  - `(signed: 'SignedHitlAction', *, provider: 'IdentityProvider', public_keys: 'Mapping[str, JsonWebKey]') -> 'HitlActionClaims'`

## `ccf.hitl.override`

- `OverrideActionRecord` — **contract**
  - `{"event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","final":"~ProductT","original":"~ProductT","overridden":"<class 'bool'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>"}`
- `OverrideBoundary` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `OverrideResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","record":"<class 'ccf.hitl.override.OverrideActionRecord'>"}`
- `OverrideResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `UnknownOverrideEventError` — **class**
  - `type`

## `ccf.hitl.principal`

- `AUTHENTICATION_CLAIM` — **constant**
  - `str`
- `ApproverIdentity` — **contract**
  - `{"identity_provider_ref":"<class 'str'>","subject_id":"<class 'str'>"}`
- `AuthenticationClaims` — **contract**
  - `{"assurance_level":"<class 'str'>","identity_provider_ref":"<class 'str'>","method":"<class 'str'>","session_ref":"<class 'str'>"}`
- `AuthenticationContext` — **contract**
  - `{"assurance_level":"<class 'str'>","method":"<class 'str'>","session_ref":"<class 'str'>"}`
- `HumanPrincipalBinding` — **contract**
  - `{"action_time":"<class 'datetime.datetime'>","approver":"<class 'ccf.hitl.principal.ApproverIdentity'>","authentication":"<class 'ccf.hitl.principal.AuthenticationContext'>","product_content_hash":"<class 'str'>","verdict":"<class 'str'>"}`
- `validate_content_hash` — **function**
  - `(value: 'str') -> 'str'`

## `ccf.hitl.review_queue`

- `ReviewActionRecord` — **contract**
  - `{"event":"<class 'ccf.hitl.transport.PendingHitlEvent'>","item":"<class 'ccf.hitl.review_queue.ReviewQueueItem'>","released":"<class 'bool'>","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>"}`
- `ReviewQueue` — **class**
  - `(*, transport: 'HITLTransportProtocol', audit: 'AuditLog', clock: 'Callable[[], datetime]', control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ReviewQueueItem` — **contract**
  - `{"lineage":"tuple[ccf.contracts.claims.LineageEntry, ...]","output_ref":"<class 'str'>"}`
- `ReviewResolution` — **contract**
  - `{"hitl_actions_block":"<class 'str'>","record":"<class 'ccf.hitl.review_queue.ReviewActionRecord'>"}`
- `ReviewResolutionRefused` — **contract**
  - `{"event_key":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `UnknownReviewEventError` — **class**
  - `type`

## `ccf.hitl.transport`

- `APPROVAL_GATE_EVENT_CLASS` — **constant**
  - `str`
- `ApproverNotEligible` — **class**
  - `type`
- `EventStateAtSubmit` — **function**
  - `typing.Literal['claimed', 'pending', 'missing']`
- `GateAlreadyClosed` — **class**
  - `type`
- `GateClosure` — **contract**
  - `{"authorizing_decision_id":"<class 'str'>","decided_action":"<class 'str'>","decided_by":"<class 'str'>","event_key":"<class 'str'>","observed_submissions":"<class 'int'>","passage":"<class 'str'>","product_content_hash":"<class 'str'>","tenant":"<class 'str'>"}`
- `GateVerdictsChanged` — **class**
  - `type`
- `HITLTransportProtocol` — **class**
  - `(*args, **kwargs)`
- `HITL_ACTIONS` — **constant**
  - `frozenset`
- `HITL_EVENT_CLASSES` — **constant**
  - `frozenset`
- `HITL_POLICY` — **constant**
  - `ArtifactClass`
- `HitlActionReceipt` — **contract**
  - `{"event_pending":"<class 'bool'>","status":"typing.Literal['submitted']","submission":"<class 'ccf.hitl.transport.HitlActionSubmission'>","submissions_for_event":"<class 'int'>"}`
- `HitlActionRequest` — **contract**
  - `{"action":"<class 'str'>","annotation":"str | None","attestation":"ccf.hitl.identity_binding.SignedHitlAction | None","event_key":"<class 'str'>","product_content_hash":"<class 'str'>"}`
- `HitlActionSubmission` — **contract**
  - `{"action":"<class 'str'>","annotation":"str | None","answered_event_class":"str | None","answered_workflow_state_ref":"str | None","approval_policy_ref":"str | None","attestation":"ccf.hitl.identity_binding.SignedHitlAction | None","authorizing_decision_id":"str | None","event_key":"<class 'str'>","event_state_at_submit":"typing.Optional[typing.Literal['claimed', 'pending', 'missing']]","hitl_policy_ref":"str | None","principal":"<class 'ccf.hitl.principal.HumanPrincipalBinding'>","requested_by":"str | None"}`
- `HitlEventRevalidationRefused` — **class**
  - `type`
- `HitlGateClosed` — **class**
  - `type`
- `HitlPolicy` — **contract**
  - `{"permitted_clock_skew_seconds":"int | None","semver":"<class 'str'>","signature_max_age_seconds":"int | None","signed_binding_required":"<class 'bool'>","trusted_keys":"collections.abc.Mapping[str, collections.abc.Mapping[str, collections.abc.Mapping[str, str]]] | None"}`
- `InMemoryHitlTransport` — **class**
  - `(*, control_plane: 'ControlPlaneProtocol | None' = None, hitl_policy_key: 'str | None' = None, identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `PendingHitlEvent` — **contract**
  - `{"event_class":"<class 'str'>","event_key":"<class 'str'>","policy_ref":"str | None","product_content_hash":"<class 'str'>","requested_by":"str | None","tenant":"<class 'str'>","workflow_state_ref":"<class 'str'>"}`
- `PrincipalMismatchRefused` — **class**
  - `type`
- `SignedBindingInvalidRefused` — **class**
  - `type`
- `SignedBindingMismatchRefused` — **class**
  - `type`
- `SignedBindingRequiredRefused` — **class**
  - `type`
- `SignedBindingStaleRefused` — **class**
  - `type`
- `check_approver_eligibility` — **function**
  - `(*, policy_ref: 'str | None', requested_by: 'str | None', subject_id: 'str', control_plane: 'object | None') -> 'None'`
- `enforce_attestation` — **function**
  - `(authorized: 'Authorized[HitlSubmit]', submission: 'HitlActionSubmission', *, identity_provider: 'IdentityProvider | None', policy: 'HitlPolicy') -> 'HitlActionClaims'`
- `resolve_hitl_policy` — **function**
  - `(*, control_plane: 'ControlPlaneProtocol | None', hitl_policy_key: 'str | None') -> 'tuple[str, HitlPolicy] | None'`
- `signed_binding_required` — **function**
  - `(*, control_plane: 'ControlPlaneProtocol | None', hitl_policy_key: 'str | None') -> 'bool'`

## `ccf.hitl.webhook`

- `HitlEventNotification` — **contract**
  - `{"endpoint_key":"<class 'str'>","event":"<class 'ccf.hitl.transport.PendingHitlEvent'>"}`
- `RecordingWebhookDeliverer` — **class**
  - `() -> 'None'`
- `WebhookDeliveryOutcome` — **contract**
  - `{"delivered":"<class 'bool'>","endpoint_key":"<class 'str'>","error":"str | None"}`
- `WebhookDeliveryProtocol` — **class**
  - `(*args, **kwargs)`
- `WebhookEndpoint` — **contract**
  - `{"endpoint_key":"<class 'str'>","tenant":"<class 'str'>","url":"<class 'str'>"}`
- `WebhookEndpointConflict` — **class**
  - `type`
- `WebhookHitlNotifier` — **class**
  - `(*, deliverer: 'WebhookDeliveryProtocol', endpoints: 'tuple[WebhookEndpoint, ...]') -> 'None'`

## `ccf.llm`

- `LLMClientProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf.mcp.acquisition`

- `McpContentAcquirer` — **class**
  - `(*, sources: 'Mapping[str, McpResourceClient]') -> 'None'`
- `TENANT_PLACEHOLDER` — **constant**
  - `str`

## `ccf.mcp.client`

- `HttpClientFactory` — **function**
  - `collections.abc.Callable[[], httpx.AsyncClient]`
- `McpResourceClient` — **class**
  - `(*, url: 'str', bridge: 'SyncMcpBridge | None' = None, http_client_factory: 'HttpClientFactory | None' = None) -> 'None'`
- `SyncMcpBridge` — **class**
  - `(*, call_timeout_seconds: 'float') -> 'None'`
- `bearer_client_factory` — **function**
  - `(credential: 'str', *, timeout_seconds: 'float') -> 'HttpClientFactory'`
- `run_with_session` — **function**
  - `(*, url: 'str', operation: 'SessionOperation[T]', http_client_factory: 'HttpClientFactory | None' = None) -> 'T'`

## `ccf.mcp.errors`

- `McpClientError` — **class**
  - `type`
- `McpResourceAbsent` — **class**
  - `type`
- `McpServerUnreachable` — **class**
  - `type`
- `McpTimeout` — **class**
  - `type`
- `McpToolFailed` — **class**
  - `(tool: 'str', text: 'str') -> 'None'`

## `ccf.orchestration`

- `OrchestrationProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf.orchestration.protocol`

- `OrchestrationProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf.peering.admission`

- `ADMISSION_RECORD` — **constant**
  - `ArtifactClass`
- `AdmissionBypassError` — **class**
  - `type`
- `AdmissionNotRecorded` — **class**
  - `type`
- `AdmissionRecord` — **contract**
  - `{"admitted_at":"<class 'datetime.datetime'>","consumer_lineage":"<class 'ccf.products.contract.ProductLineage'>","issuance":"<class 'ccf.peering.issuance.IssuanceClaims'>","merged_lineage":"<class 'ccf.products.contract.ProductLineage'>","peer_id":"<class 'str'>","producer_lineage":"<class 'ccf.products.contract.ProductLineage'>","product_content_address":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `AdmissionRecordReferenceMismatch` — **class**
  - `(*, fields: 'tuple[str, ...]') -> 'None'`
- `AdmissionRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>","peer_id":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `AdmittedProduct` — **class**
  - `(product: 'ContextProductContract', lineage: 'ProductLineage', peer: 'PeerRef', token: 'object', protected_header: 'Mapping[str, object] | None' = None, content_address: 'str | None' = None, issuance: 'IssuanceClaims | None' = None) -> 'None'`
- `ContractRefusal` — **contract**
  - `{"detail":"<class 'str'>","gate":"<class 'str'>","peer_id":"<class 'str'>","schema_name":"str | None","tenant_id":"<class 'str'>","violation":"<class 'str'>"}`
- `GATE_CONTRACT` — **constant**
  - `str`
- `GATE_ISSUANCE` — **constant**
  - `str`
- `GATE_LINEAGE_CONTINUITY` — **constant**
  - `str`
- `GATE_PAYLOAD_CEILING` — **constant**
  - `str`
- `GATE_POLICY_BINDING` — **constant**
  - `str`
- `GATE_SIGNATURE` — **constant**
  - `str`
- `INBOUND_PAYLOAD_CEILING` — **constant**
  - `ArtifactClass`
- `InboundPayloadCeiling` — **contract**
  - `{"max_payload_bytes":"<class 'int'>","semver":"<class 'str'>"}`
- `IssuanceRefusal` — **contract**
  - `{"detail":"<class 'str'>","failure":"typing.Literal['claims-missing', 'stale-issuance', 'replayed']","gate":"<class 'str'>","issued_at":"datetime.datetime | None","max_age_seconds":"<class 'int'>","peer_id":"<class 'str'>","skew_seconds":"<class 'int'>","tenant_id":"<class 'str'>"}`
- `LineageContinuityRefusal` — **contract**
  - `{"consumer":"frozenset[str]","detail":"<class 'str'>","gate":"<class 'str'>","merged":"frozenset[str]","peer_id":"<class 'str'>","producer":"frozenset[str]","tenant_id":"<class 'str'>"}`
- `PRODUCER_ASSERTION_HEADER` — **constant**
  - `str`
- `PayloadTooLargeRefusal` — **contract**
  - `{"ceiling_bytes":"<class 'int'>","detail":"<class 'str'>","gate":"<class 'str'>","observed_bytes":"<class 'int'>","peer_id":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `PeeringAdmissionGate` — **class**
  - `(*, identity: 'IdentityProvider', control_plane: 'ControlPlaneProtocol', audit_log: 'AuditLog', artifact_store: 'ArtifactStoreProtocol', authorized: 'Authorized[ReplayMint]', trust_policy_version: 'str', payload_ceiling_version: 'str', product_classes: 'Mapping[str, RegisteredProductClass]', seen: 'SeenNonceSetProtocol | None' = None) -> 'None'`
- `PolicyBindingRefusal` — **contract**
  - `{"asserted":"frozenset[str]","assertion":"<class 'str'>","detail":"<class 'str'>","gate":"<class 'str'>","peer_id":"<class 'str'>","permitted":"frozenset[str]","tenant_id":"<class 'str'>"}`
- `SignatureRefusal` — **contract**
  - `{"declared_key_id":"str | None","detail":"<class 'str'>","failure":"<class 'str'>","gate":"<class 'str'>","peer_id":"<class 'str'>","permitted_key_ids":"frozenset[str]","tenant_id":"<class 'str'>"}`
- `payload_ceiling_key` — **function**
  - `(*, tenant_id: 'str') -> 'str'`
- `union_lineage` — **function**
  - `(*, producer: 'ProductLineage', consumer: 'ProductLineage') -> 'ProductLineage'`
- `verify_admission_provenance` — **function**
  - `(admitted: 'object') -> "'AdmittedProduct'"`

## `ccf.peering.eligibility`

- `ELIGIBILITY_ASSERTION_HEADER` — **constant**
  - `str`
- `ELIGIBILITY_ASSERTION_SCHEMA_VERSION` — **constant**
  - `str`
- `EligibilityAssertion` — **contract**
  - `{"checked_at":"<class 'datetime.datetime'>","child_content_address":"<class 'str'>","composition_invocation":"<class 'str'>","consumer_scope":"<class 'str'>","eligible":"<class 'bool'>","producer":"<class 'str'>","requested_as_of":"<class 'datetime.datetime'>","schema_version":"<class 'str'>"}`
- `EligibilityAssertionMalformed` — **class**
  - `type`
- `decode_eligibility_assertion` — **function**
  - `(claim: 'object') -> 'EligibilityAssertion'`
- `encode_eligibility_assertion` — **function**
  - `(assertion: 'EligibilityAssertion') -> 'str'`
- `mint_eligibility_assertion` — **function**
  - `(*, child_content_address: 'str', requested_as_of: 'datetime', producer: 'str', consumer_scope: 'str', checked_at: 'datetime', composition_invocation: 'str', eligible: 'bool') -> 'EligibilityAssertion'`

## `ccf.peering.identity`

- `AlgorithmNotPermitted` — **class**
  - `type`
- `DetachedJwsIdentityProvider` — **class**
  - `(*, key_source: 'SigningKeySource', algorithm: 'str' = 'ES256') -> 'None'`
- `FileBackedKeySource` — **class**
  - `(*, directory: 'pathlib.Path') -> 'None'`
- `IdentityError` — **class**
  - `type`
- `IdentityProvider` — **class**
  - `(*args, **kwargs)`
- `JsonWebKey` — **function**
  - `collections.abc.Mapping[str, str]`
- `KeyUnavailable` — **class**
  - `type`
- `PRODUCT_SIGNATURE_TYPE` — **constant**
  - `str`
- `SIGNING_ALGORITHM` — **constant**
  - `str`
- `SignatureInvalid` — **class**
  - `type`
- `SignatureMalformed` — **class**
  - `type`
- `SignedContextProduct` — **contract**
  - `{"payload":"<class 'str'>","protected":"<class 'str'>","signature":"<class 'str'>"}`
- `SigningKeySource` — **class**
  - `(*args, **kwargs)`
- `UnknownSigningKey` — **class**
  - `type`
- `jwk_thumbprint` — **function**
  - `(public_key: 'JsonWebKey') -> 'str'`
- `signed_product_address` — **function**
  - `(product: 'object') -> 'str'`

## `ccf.peering.issuance`

- `ISSUANCE_CLAIMS_HEADER` — **constant**
  - `str`
- `ISSUANCE_CLAIMS_SCHEMA_VERSION` — **constant**
  - `str`
- `InProcessSeenNonceSet` — **class**
  - `() -> 'None'`
- `IssuanceClaims` — **contract**
  - `{"answered":"<class 'ccf.peering.issuance.IssuedAnswer'>","echo":"<class 'ccf.peering.issuance.IssuedRequest'>","issued_at":"<class 'datetime.datetime'>","nonce":"<class 'str'>","schema_version":"<class 'str'>"}`
- `IssuanceClaimsMalformed` — **class**
  - `type`
- `IssuedAnswer` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","freshness":"<class 'str'>","intent":"<class 'str'>","subject":"<class 'str'>"}`
- `IssuedRequest` — **contract**
  - `{"parameters":"collections.abc.Mapping[str, typing.Any]","product_id":"<class 'str'>","temporal_boundary":"datetime.datetime | None"}`
- `SeenNonceSetProtocol` — **class**
  - `(*args, **kwargs)`
- `decode_issuance_claims` — **function**
  - `(claim: 'object') -> 'IssuanceClaims'`
- `encode_issuance_claims` — **function**
  - `(claims: 'IssuanceClaims') -> 'str'`
- `issuance_staleness` — **function**
  - `(*, issued_at: 'datetime', now: 'datetime', max_age_seconds: 'int', skew_seconds: 'int') -> "Literal['post-dated', 'expired'] | None"`
- `mint_issuance_claims` — **function**
  - `(*, issued_at: 'datetime', nonce: 'str', answered: 'IssuedAnswer', echo: 'IssuedRequest') -> 'IssuanceClaims'`

## `ccf.peering.protocol`

- `EmitReceipt` — **contract**
  - `{"content_address":"<class 'str'>","peer":"<class 'ccf.peering.protocol.PeerRef'>","wire_message_id":"<class 'str'>"}`
- `InboundProduct` — **contract**
  - `{"observed_peer":"<class 'ccf.peering.protocol.PeerRef'>","signed":"<class 'ccf.peering.identity.SignedContextProduct'>"}`
- `PeerRef` — **contract**
  - `{"peer_id":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `PeeringProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf.peering.trust_policy`

- `PEERING_TRUST_POLICY` — **constant**
  - `ArtifactClass`
- `PeerNotTrusted` — **class**
  - `type`
- `PeerTrustGrant` — **contract**
  - `{"permitted_clock_skew_seconds":"<class 'int'>","permitted_policy_regimes":"frozenset[str]","permitted_producer_hashes":"frozenset[str]","permitted_schema_names":"frozenset[str]","signature_max_age_seconds":"<class 'int'>","signing_keys":"collections.abc.Mapping[str, collections.abc.Mapping[str, str]]"}`
- `PeeringTrustPolicy` — **contract**
  - `{"peers":"collections.abc.Mapping[str, ccf.peering.trust_policy.PeerTrustGrant]","semver":"<class 'str'>","tenant_id":"<class 'str'>"}`
- `TrustPolicyViolation` — **class**
  - `type`
- `trust_policy_key` — **function**
  - `(*, tenant_id: 'str') -> 'str'`

## `ccf.skills`

- `ApprovalOutcome` — **contract**
  - `{"approved":"<class 'bool'>","approver_id":"<class 'str'>"}`
- `ApprovalRejected` — **contract**
  - `{"approver_id":"<class 'str'>","check":"<class 'str'>","detail":"<class 'str'>"}`
- `ApprovalSink` — **class**
  - `(*args, **kwargs)`
- `BoundSkillView` — **class**
  - `(ledger: "'GrantLedger'", agent_definition_hash: 'str') -> 'None'`
- `GovernanceUndeclared` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>","ref":"<class 'str'>"}`
- `GrantCollisionError` — **class**
  - `(skill_name: 'str', first_hash: 'str', second_hash: 'str') -> 'None'`
- `GrantLedger` — **class**
  - `(*, control_plane: 'ControlPlaneRegistry', catalog: 'SkillCatalog', sink: 'ApprovalSink', clock: 'Callable[[], datetime]', audit: 'AuditLog | None' = None) -> 'None'`
- `GrantRefusal` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>"}`
- `GrantTransitionError` — **class**
  - `type`
- `LocalCallableBinding` — **contract**
  - `{"callable_ref":"<class 'str'>"}`
- `McpBinding` — **contract**
  - `{"resource":"<class 'str'>","server":"<class 'str'>"}`
- `PeeringBinding` — **contract**
  - `{"endpoint":"<class 'str'>"}`
- `PolicyRegimeGovernance` — **contract**
  - `{"grant_requires_approval":"<class 'bool'>","permitted_scopes":"frozenset[str]"}`
- `PolicyRegimeUnresolvable` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>","ref":"<class 'str'>"}`
- `RequirementsExceedRegime` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>","excess_context_products":"frozenset[str]","excess_scopes":"frozenset[str]"}`
- `SKILL_CATALOG_ENTRY` — **constant**
  - `ArtifactClass`
- `SKILL_GRANT` — **constant**
  - `ArtifactClass`
- `SKILL_TYPES` — **constant**
  - `frozenset`
- `SkillCatalog` — **class**
  - `(control_plane: 'ControlPlaneRegistry') -> 'None'`
- `SkillCatalogEntry` — **contract**
  - `{"argument_schema":"<class 'ccf.skills.catalog.SkillArgumentSchema'>","artifact_version":"<class 'str'>","binding":"ccf.skills.catalog.LocalCallableBinding | ccf.skills.catalog.ToolBinding | ccf.skills.catalog.McpBinding | ccf.skills.catalog.McpProductBinding | ccf.skills.catalog.PeeringBinding | ccf.skills.catalog.ProcedureBinding","description":"<class 'str'>","name":"<class 'str'>","produces":"<class 'str'>","requirements":"<class 'ccf.skills.catalog.SkillRequirements'>","schema_version":"<class 'str'>","skill_type":"typing.Literal['local_callable', 'tool', 'mcp', 'mcp_product', 'peering', 'procedure']","tenant":"<class 'str'>"}`
- `SkillGrant` — **contract**
  - `{"agent_definition_hash":"<class 'str'>","artifact_version":"<class 'str'>","name":"<class 'str'>","schema_version":"<class 'str'>","skill_name":"<class 'str'>","skill_version":"<class 'str'>","tenant":"<class 'str'>"}`
- `SkillNotInCatalog` — **class**
  - `type`
- `SkillRequirements` — **contract**
  - `{"required_context_products":"frozenset[str]","required_scopes":"frozenset[str]"}`
- `SplitAuditPlaneError` — **class**
  - `type`
- `TenantMismatch` — **contract**
  - `{"check":"<class 'str'>","definition_tenant":"<class 'str'>","detail":"<class 'str'>","entry_tenant":"<class 'str'>","grant_tenant":"<class 'str'>"}`
- `ToolBinding` — **contract**
  - `{"command":"<class 'str'>"}`
- `grant_set_hash` — **function**
  - `(active_grant_hashes: 'frozenset[str]') -> 'str'`
- `skill_catalog_key` — **function**
  - `(entry: 'SkillCatalogEntry') -> 'str'`
- `skill_grant_key` — **function**
  - `(grant: 'SkillGrant') -> 'str'`

## `ccf.skills.callables`

- `CallableNotRegistered` — **class**
  - `type`
- `CallableRegistry` — **class**
  - `() -> 'None'`
- `DuplicateCallableKey` — **class**
  - `type`
- `SkillCallable` — **function**
  - `collections.abc.Callable[[collections.abc.Mapping[str, str]], collections.abc.Mapping[str, str]]`

## `ccf.skills.catalog`

- `LocalCallableBinding` — **contract**
  - `{"callable_ref":"<class 'str'>"}`
- `McpBinding` — **contract**
  - `{"resource":"<class 'str'>","server":"<class 'str'>"}`
- `McpProductBinding` — **contract**
  - `{"product_class":"<class 'str'>","product_version":"<class 'str'>","server":"<class 'str'>"}`
- `NO_PRODUCT_CLASS` — **constant**
  - `str`
- `PeeringBinding` — **contract**
  - `{"endpoint":"<class 'str'>"}`
- `ProcedureBinding` — **contract**
  - `{"instruction":"<class 'ccf.agents.definitions.InstructionBinding'>"}`
- `SKILL_CATALOG_ENTRY` — **constant**
  - `ArtifactClass`
- `SKILL_TYPES` — **constant**
  - `frozenset`
- `SkillArgumentElement` — **contract**
  - `{"description":"<class 'str'>","properties":"collections.abc.Mapping[str, ccf.skills.catalog.SkillArgumentMember] | None","required":"tuple[str, ...]","type":"typing.Literal['string', 'number', 'integer', 'boolean', 'array', 'object']"}`
- `SkillArgumentMember` — **contract**
  - `{"description":"<class 'str'>","type":"typing.Literal['string', 'number', 'integer', 'boolean', 'array', 'object']"}`
- `SkillArgumentProperty` — **contract**
  - `{"description":"<class 'str'>","items":"ccf.skills.catalog.SkillArgumentElement | None","properties":"collections.abc.Mapping[str, ccf.skills.catalog.SkillArgumentMember] | None","required":"tuple[str, ...]","type":"typing.Literal['string', 'number', 'integer', 'boolean', 'array', 'object']"}`
- `SkillArgumentSchema` — **contract**
  - `{"properties":"collections.abc.Mapping[str, ccf.skills.catalog.SkillArgumentProperty]","required":"tuple[str, ...]"}`
- `SkillCatalog` — **class**
  - `(control_plane: 'ControlPlaneRegistry') -> 'None'`
- `SkillCatalogEntry` — **contract**
  - `{"argument_schema":"<class 'ccf.skills.catalog.SkillArgumentSchema'>","artifact_version":"<class 'str'>","binding":"ccf.skills.catalog.LocalCallableBinding | ccf.skills.catalog.ToolBinding | ccf.skills.catalog.McpBinding | ccf.skills.catalog.McpProductBinding | ccf.skills.catalog.PeeringBinding | ccf.skills.catalog.ProcedureBinding","description":"<class 'str'>","name":"<class 'str'>","produces":"<class 'str'>","requirements":"<class 'ccf.skills.catalog.SkillRequirements'>","schema_version":"<class 'str'>","skill_type":"typing.Literal['local_callable', 'tool', 'mcp', 'mcp_product', 'peering', 'procedure']","tenant":"<class 'str'>"}`
- `SkillNotInCatalog` — **class**
  - `type`
- `SkillRequirements` — **contract**
  - `{"required_context_products":"frozenset[str]","required_scopes":"frozenset[str]"}`
- `ToolBinding` — **contract**
  - `{"command":"<class 'str'>"}`
- `skill_catalog_key` — **function**
  - `(entry: 'SkillCatalogEntry') -> 'str'`

## `ccf.skills.dispatch`

- `ChildQuestionIdentity` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","freshness":"<class 'str'>","intent":"<class 'str'>","request":"<class 'str'>","subject":"<class 'str'>"}`
- `McpInvocation` — **contract**
  - `{"arguments":"collections.abc.Mapping[str, str]","contents":"<class 'str'>","resource":"<class 'str'>","server":"<class 'str'>","skill_name":"<class 'str'>","skill_type":"<class 'str'>"}`
- `McpProductFailure` — **class**
  - `(*, skill_name: 'str', skill_type: 'str', server: 'str', producer_id: 'str', producer_tenant: 'str', producer_registration_address: 'str', product_class: 'str', product_version: 'str', question_address: 'str', failure: 'McpProductFailureKind', detail: 'str', token: 'object') -> 'None'`
- `McpProductInvocation` — **class**
  - `(*, skill_name: 'str', skill_type: 'str', server: 'str', producer_id: 'str', producer_tenant: 'str', producer_registration_address: 'str', product_class: 'str', product_version: 'str', question_address: 'str', request_json: 'str', contents: 'str', arguments: 'Mapping[str, str]', token: 'object') -> 'None'`
- `McpProductProvenanceError` — **class**
  - `type`
- `McpSkillRegistry` — **class**
  - `(*, audit_log: 'AuditLog', clock: 'Callable[[], datetime]') -> 'None'`
- `McpSkillUnregistered` — **class**
  - `type`
- `PeeringInvocation` — **contract**
  - `{"arguments":"collections.abc.Mapping[str, str]","endpoint":"<class 'str'>","products":"tuple[ccf.peering.protocol.InboundProduct, ...]","skill_name":"<class 'str'>","skill_type":"<class 'str'>"}`
- `PeeringSkillRegistry` — **class**
  - `(*, audit_log: 'AuditLog', clock: 'Callable[[], datetime]') -> 'None'`
- `PeeringSkillUnregistered` — **class**
  - `type`
- `ProducerDoesNotOffer` — **class**
  - `type`
- `ProducerOffer` — **contract**
  - `{"product_class":"<class 'str'>","versions_from":"<class 'str'>"}`
- `ProducerRegistration` — **contract**
  - `{"artifact_address":"<class 'str'>","offers":"tuple[ccf.skills.dispatch.ProducerOffer, ...]","producer_id":"<class 'str'>","producer_tenant":"<class 'str'>","server":"<class 'str'>"}`
- `ProductQuestion` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","freshness":"<class 'str'>","intent":"<class 'str'>","parameters":"collections.abc.Mapping[str, typing.Any]","request_json":"<class 'str'>","subject":"<class 'str'>"}`
- `SkillInvocation` — **contract**
  - `{"output":"collections.abc.Mapping[str, str]","skill_name":"<class 'str'>","skill_type":"<class 'str'>"}`
- `TENANT_NOT_GRANTED_CODE` — **constant**
  - `str`
- `ToolInvocation` — **contract**
  - `{"arguments":"collections.abc.Mapping[str, str]","command":"<class 'str'>","skill_name":"<class 'str'>"}`
- `dispatch_skill` — **function**
  - `(entry: 'SkillCatalogEntry', *, arguments: 'Mapping[str, str]', callable_registry: 'CallableRegistry', mcp_skills: 'McpSkillRegistry | None' = None, peering_skills: 'PeeringSkillRegistry | None' = None, question: 'ProductQuestion | None' = None) -> 'SkillInvocation | ToolInvocation | McpInvocation | PeeringInvocation | McpProductInvocation | McpProductFailure'`
- `question_identity` — **function**
  - `(*, request_json: 'str', subject: 'str', intent: 'str', freshness: 'str', asked_at: 'datetime') -> 'str'`
- `verify_mcp_product_failure` — **function**
  - `(value: 'object') -> 'McpProductFailure'`
- `verify_mcp_product_invocation` — **function**
  - `(value: 'object') -> 'McpProductInvocation'`

## `ccf.skills.grants`

- `ApprovalOutcome` — **contract**
  - `{"approved":"<class 'bool'>","approver_id":"<class 'str'>"}`
- `ApprovalRejected` — **contract**
  - `{"approver_id":"<class 'str'>","check":"<class 'str'>","detail":"<class 'str'>"}`
- `ApprovalSink` — **class**
  - `(*args, **kwargs)`
- `BoundSkillView` — **class**
  - `(ledger: "'GrantLedger'", agent_definition_hash: 'str') -> 'None'`
- `GOVERNANCE_FIELD` — **constant**
  - `str`
- `GRANT_STATE` — **constant**
  - `str`
- `GovernanceUndeclared` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>","ref":"<class 'str'>"}`
- `GrantAuthorityMismatch` — **class**
  - `type`
- `GrantCollisionError` — **class**
  - `(skill_name: 'str', first_hash: 'str', second_hash: 'str') -> 'None'`
- `GrantLedger` — **class**
  - `(*, control_plane: 'ControlPlaneRegistry', catalog: 'SkillCatalog', sink: 'ApprovalSink', clock: 'Callable[[], datetime]', audit: 'AuditLog | None' = None) -> 'None'`
- `GrantRefusal` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>"}`
- `GrantState` — **function**
  - `typing.Literal['requested', 'pending-approval', 'effective', 'refused', 'revoked']`
- `GrantStateRecord` — **contract**
  - `{"grant":"<class 'ccf.skills.grants.SkillGrant'>","state":"typing.Literal['requested', 'pending-approval', 'effective', 'refused', 'revoked']"}`
- `GrantTransitionError` — **class**
  - `type`
- `PolicyRegimeGovernance` — **contract**
  - `{"grant_requires_approval":"<class 'bool'>","permitted_scopes":"frozenset[str]"}`
- `PolicyRegimeUnresolvable` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>","ref":"<class 'str'>"}`
- `RefusingApprovalSink` — **class**
  - `()`
- `RequirementsExceedRegime` — **contract**
  - `{"check":"<class 'str'>","detail":"<class 'str'>","excess_context_products":"frozenset[str]","excess_scopes":"frozenset[str]"}`
- `SKILL_GRANT` — **constant**
  - `ArtifactClass`
- `SkillGrant` — **contract**
  - `{"agent_definition_hash":"<class 'str'>","artifact_version":"<class 'str'>","name":"<class 'str'>","schema_version":"<class 'str'>","skill_name":"<class 'str'>","skill_version":"<class 'str'>","tenant":"<class 'str'>"}`
- `SplitAuditPlaneError` — **class**
  - `type`
- `TenantMismatch` — **contract**
  - `{"check":"<class 'str'>","definition_tenant":"<class 'str'>","detail":"<class 'str'>","entry_tenant":"<class 'str'>","grant_tenant":"<class 'str'>"}`
- `grant_set_hash` — **function**
  - `(active_grant_hashes: 'frozenset[str]') -> 'str'`
- `skill_grant_key` — **function**
  - `(grant: 'SkillGrant') -> 'str'`

## `ccf.skills.producers`

- `ProducerEnvironmentMissing` — **class**
  - `type`
- `producer_registration_from_artifact` — **function**
  - `(artifact: 'McpProducerRegistration') -> 'ProducerRegistration'`
- `register_declared_producer` — **function**
  - `(registry: 'McpSkillRegistry', *, artifact: 'McpProducerRegistration', environ: 'Mapping[str, str]', bridge: 'SyncMcpBridge', credential_factory: 'CredentialFactory | None' = None) -> 'ProducerRegistration'`

## `ccf.skills.toolsurface`

- `HARNESS_EXPOSABLE_SKILL_TYPES` — **constant**
  - `frozenset`
- `ProcedureHasNoToolSurface` — **class**
  - `type`
- `RenderedToolSurface` — **class**
  - `(description: 'str', input_schema: 'dict[str, Any]') -> None`
- `SkillHasNoToolSurface` — **class**
  - `type`
- `render_tool_surface` — **function**
  - `(entry: 'SkillCatalogEntry') -> 'RenderedToolSurface'`

## `ccf.skills.wire_arguments`

- `ArgumentRefused` — **class**
  - `(*, surface: 'str', undeclared: 'tuple[str, ...]' = (), missing: 'tuple[str, ...]' = (), mistyped: 'tuple[str, ...]' = ()) -> 'None'`
- `MissingArgumentRefused` — **class**
  - `(*, surface: 'str', undeclared: 'tuple[str, ...]' = (), missing: 'tuple[str, ...]' = (), mistyped: 'tuple[str, ...]' = ()) -> 'None'`
- `MistypedArgumentRefused` — **class**
  - `(*, surface: 'str', undeclared: 'tuple[str, ...]' = (), missing: 'tuple[str, ...]' = (), mistyped: 'tuple[str, ...]' = ()) -> 'None'`
- `UndeclaredArgumentRefused` — **class**
  - `(*, surface: 'str', undeclared: 'tuple[str, ...]' = (), missing: 'tuple[str, ...]' = (), mistyped: 'tuple[str, ...]' = ()) -> 'None'`
- `refuse_unconforming_arguments` — **function**
  - `(arguments: 'Mapping[str, object]', *, schema: 'SkillArgumentSchema', surface: 'str') -> 'None'`
- `refuse_undeclared_arguments` — **function**
  - `(arguments: 'Mapping[str, object]', *, declared: 'Iterable[str]', surface: 'str') -> 'None'`
- `undeclared_arguments` — **function**
  - `(arguments: 'Mapping[str, object]', *, declared: 'Iterable[str]') -> 'tuple[str, ...]'`

## `ccf.workflow`

- `WORKFLOW_DEFINITION` — **constant**
  - `ArtifactClass`
- `WORKFLOW_FAILED_STATE` — **constant**
  - `str`
- `Workflow` — **class**
  - `(*, definition: 'WorkflowDefinition', task_definition: 'TaskDefinition', identity: 'WorkflowIdentity', definition_key: 'str') -> 'None'`
- `WorkflowConstructionError` — **class**
  - `type`
- `WorkflowDefinition` — **contract**
  - `{"artifact_version":"<class 'str'>","exception_refs":"collections.abc.Mapping[str, str]","gate_policies":"collections.abc.Mapping[str, str]","gate_routes":"collections.abc.Mapping[str, collections.abc.Mapping[str, str]]","name":"<class 'str'>","schema_version":"<class 'str'>","start":"<class 'str'>","task_definition_ref":"<class 'str'>","tenant":"<class 'str'>","terminal_states":"tuple[str, ...]","transitions":"tuple[ccf.workflow.definitions.WorkflowTransition, ...]"}`
- `WorkflowFactory` — **class**
  - `(*, control_plane: 'ControlPlaneResolution') -> 'None'`
- `WorkflowIdentity` — **contract**
  - `{"definition_hash":"<class 'str'>","definition_uri":"<class 'str'>","task_definition_hash":"<class 'str'>","task_definition_uri":"<class 'str'>"}`
- `WorkflowTenantMismatchError` — **class**
  - `type`
- `WorkflowTransition` — **contract**
  - `{"source":"<class 'str'>","target":"<class 'str'>"}`

## `ccf.workflow.definitions`

- `WORKFLOW_DEFINITION` — **constant**
  - `ArtifactClass`
- `WORKFLOW_FAILED_STATE` — **constant**
  - `str`
- `WorkflowDefinition` — **contract**
  - `{"artifact_version":"<class 'str'>","exception_refs":"collections.abc.Mapping[str, str]","gate_policies":"collections.abc.Mapping[str, str]","gate_routes":"collections.abc.Mapping[str, collections.abc.Mapping[str, str]]","name":"<class 'str'>","schema_version":"<class 'str'>","start":"<class 'str'>","task_definition_ref":"<class 'str'>","tenant":"<class 'str'>","terminal_states":"tuple[str, ...]","transitions":"tuple[ccf.workflow.definitions.WorkflowTransition, ...]"}`
- `WorkflowTransition` — **contract**
  - `{"source":"<class 'str'>","target":"<class 'str'>"}`

## `ccf.workflow.factory`

- `Workflow` — **class**
  - `(*, definition: 'WorkflowDefinition', task_definition: 'TaskDefinition', identity: 'WorkflowIdentity', definition_key: 'str') -> 'None'`
- `WorkflowConstructionError` — **class**
  - `type`
- `WorkflowFactory` — **class**
  - `(*, control_plane: 'ControlPlaneResolution') -> 'None'`
- `WorkflowIdentity` — **contract**
  - `{"definition_hash":"<class 'str'>","definition_uri":"<class 'str'>","task_definition_hash":"<class 'str'>","task_definition_uri":"<class 'str'>"}`
- `WorkflowTenantMismatchError` — **class**
  - `type`
