# Runtime — SDK 1.0.2 Signatures

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Exact public shapes under `ccf_runtime`, including authorization, adapters, CLI, HTTP, MCP, erasure, orchestration, peering, workflow, and Replay.

This page is generated from `docs/surface/v0.2-surface.json` at `v1.0.2`. It is a lookup appendix; use the focused reference pages for semantics and examples.

> SDK 1.0.2 is tagged. Release status, deployment verification and the prior bank delivery remain separate; see [migration requirements](../MIGRATION_AND_LIMITATIONS.md).

## `ccf_runtime.adapters.adk`

- `AGENT_HASH_STATE_KEY` — **constant**
  - `str`
- `AdkAdapter` — **class**
  - `(*, model: 'str', agent_name: 'str', session_id: 'str', effects: 'EffectCapability') -> 'None'`
- `AdkCarrier` — **class**
  - `(llm_agent: 'LlmAgent', runnable: 'BaseAgent', injection: 'ContextInjection', skills: 'tuple[str, ...]' = (), session_state: 'dict[str, Any]' = <factory>) -> None`
- `ContextInjection` — **class**
  - `(instructions: 'tuple[str, ...]' = (), products: 'tuple[str, ...]' = ()) -> None`
- `HARNESS_ID` — **constant**
  - `str`
- `MODEL_STATE_KEY` — **constant**
  - `str`
- `REFUSAL_RESPONSE_KEY` — **constant**
  - `str`
- `TRACE_METADATA_KEY` — **constant**
  - `str`
- `USAGE_STATE_KEY` — **constant**
  - `str`

## `ccf_runtime.adapters.adk.adapter`

- `AGENT_HASH_STATE_KEY` — **constant**
  - `str`
- `AdkAdapter` — **class**
  - `(*, model: 'str', agent_name: 'str', session_id: 'str', effects: 'EffectCapability') -> 'None'`
- `AdkCarrier` — **class**
  - `(llm_agent: 'LlmAgent', runnable: 'BaseAgent', injection: 'ContextInjection', skills: 'tuple[str, ...]' = (), session_state: 'dict[str, Any]' = <factory>) -> None`
- `ContextInjection` — **class**
  - `(instructions: 'tuple[str, ...]' = (), products: 'tuple[str, ...]' = ()) -> None`
- `HARNESS_ID` — **constant**
  - `str`
- `MODEL_STATE_KEY` — **constant**
  - `str`
- `REFUSAL_RESPONSE_KEY` — **constant**
  - `str`
- `TRACE_METADATA_KEY` — **constant**
  - `str`
- `USAGE_STATE_KEY` — **constant**
  - `str`

## `ccf_runtime.adapters.claude_agent`

- `ClaudeAgentAdapter` — **class**
  - `(*, model: 'str', mcp_server_name: 'str', mcp_server_version: 'str', effects: 'EffectCapability', child_environment: 'Mapping[str, str] | None' = None, cwd: 'str | Path | None' = None, max_turns: 'int | None' = None) -> 'None'`
- `HARNESS_ID` — **constant**
  - `str`

## `ccf_runtime.adapters.claude_agent.adapter`

- `AllowlistedEnvironmentTransport` — **class**
  - `(prompt: str | collections.abc.AsyncIterable[dict[str, typing.Any]], options: claude_agent_sdk.types.ClaudeAgentOptions)`
- `ClaudeAgentAdapter` — **class**
  - `(*, model: 'str', mcp_server_name: 'str', mcp_server_version: 'str', effects: 'EffectCapability', child_environment: 'Mapping[str, str] | None' = None, cwd: 'str | Path | None' = None, max_turns: 'int | None' = None) -> 'None'`
- `DEFAULT_CHILD_ENVIRONMENT` — **constant**
  - `tuple`
- `HARNESS_ID` — **constant**
  - `str`
- `PromptFileRefused` — **class**
  - `type`

## `ccf_runtime.adapters.langgraph`

- `AGENT_HASH_METADATA_KEY` — **constant**
  - `str`
- `HARNESS_ID` — **constant**
  - `str`
- `HarnessState` — **class**
  - `_TypedDictMeta`
- `LangGraphAdapter` — **class**
  - `(*, model: 'str', thread_id: 'str', run_tags: 'tuple[str, ...]' = (), effects: 'EffectCapability') -> 'None'`
- `LangGraphCarrier` — **class**
  - `(graph: 'Any', state: 'HarnessState', config: 'RunnableConfig', tools: 'ToolNode') -> None`
- `MODEL_METADATA_KEY` — **constant**
  - `str`
- `USAGE_METADATA_KEY` — **constant**
  - `str`

## `ccf_runtime.adapters.langgraph.adapter`

- `AGENT_HASH_METADATA_KEY` — **constant**
  - `str`
- `HARNESS_ID` — **constant**
  - `str`
- `HarnessState` — **class**
  - `_TypedDictMeta`
- `LangGraphAdapter` — **class**
  - `(*, model: 'str', thread_id: 'str', run_tags: 'tuple[str, ...]' = (), effects: 'EffectCapability') -> 'None'`
- `LangGraphCarrier` — **class**
  - `(graph: 'Any', state: 'HarnessState', config: 'RunnableConfig', tools: 'ToolNode') -> None`
- `MODEL_METADATA_KEY` — **constant**
  - `str`
- `USAGE_METADATA_KEY` — **constant**
  - `str`

## `ccf_runtime.authz.artifact`

- `SCOPE_MAPPING` — **constant**
  - `ArtifactClass`
- `ScopeEntry` — **contract**
  - `{"action_ids":"tuple[str, ...]","resource_patterns":"tuple[str, ...]","tenant_patterns":"tuple[str, ...]"}`
- `ScopeMappingArtifact` — **contract**
  - `{"scopes":"collections.abc.Mapping[str, ccf_runtime.authz.artifact.ScopeEntry]","semver":"<class 'str'>"}`
- `pattern_matches` — **function**
  - `(pattern: 'str', value: 'str') -> 'bool'`
- `validate_patterns` — **function**
  - `(value: 'tuple[str, ...]', *, axis: 'str') -> 'tuple[str, ...]'`

## `ccf_runtime.authz.capability`

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
- `ArtifactRead` — **class**
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

## `ccf_runtime.authz.delivery_boundary`

- `DEREFERENCE_PRODUCT_ID` — **constant**
  - `str`
- `DereferenceRequest` — **class**
  - `(*, reference: 'str', by_uri: 'bool', wants_bytes: 'bool') -> None`
- `DereferencedEvidence` — **class**
  - `(*, content_address: 'str', record: 'DecisionReplayRecord', payload: 'bytes | None' = None) -> None`
- `DisclosingRecorderProtocol` — **class**
  - `(*args, **kwargs)`
- `EVIDENCE_READ_KINDS` — **constant**
  - `tuple`
- `EVIDENCE_SURFACES` — **constant**
  - `frozenset`
- `EvidenceReadAuthority` — **function**
  - `typing.Union[ccf.authz.capability.Authorized[ccf.authz.capability.ArtifactRead], ccf.authz.capability.Authorized[ccf.authz.capability.ReplayRead]]`
- `SURFACE_HTTP_ARTIFACT_READ` — **constant**
  - `str`
- `SURFACE_HTTP_REPLAY_READ` — **constant**
  - `str`
- `SURFACE_HTTP_ROUTE` — **constant**
  - `str`
- `SURFACE_MCP_RESOURCE` — **constant**
  - `str`
- `SURFACE_MCP_TOOL` — **constant**
  - `str`
- `UnattributableDeliveryBoundaryError` — **class**
  - `type`
- `UnconsultedDeliveryBoundaryError` — **class**
  - `type`
- `UnrecordableDeliveryBoundaryError` — **class**
  - `type`
- `disclosing_boundary` — **function**
  - `(*, refusal_recorder: 'object | None', builder: 'str') -> 'DisclosingRecorderProtocol'`
- `govern_absence` — **function**
  - `(*, grant: 'TokenGrant', tenant: 'str', product_class: 'str', product_version: 'str | None', parameters: 'Mapping[str, Any]', asked_at: 'datetime | None', surface: 'str', address: 'str', perspective: 'Perspective', absent: 'LookupError', entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'RefusalRecorderProtocol') -> 'RefusalEnvelope'`
- `govern_dereference` — **function**
  - `(authorized: 'EvidenceReadAuthority', *, reference: 'DereferenceRequest', store: 'ArtifactStoreProtocol', entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'DisclosingRecorderProtocol', audit_log: 'AuditLog', surface: 'str', address: 'str', erased_client_read: 'ErasedContentRefused | None' = None) -> 'DereferencedEvidence | RefusalEnvelope'`
- `govern_entitlement` — **function**
  - `(*, grant: 'TokenGrant', tenant: 'str', product_class: 'str', product_version: 'str | None', requested_role: 'str | None', parameters: 'Mapping[str, Any]', asked_at: 'datetime | None', surface: 'str', address: 'str', entitlement_source: 'ProductEntitlementSourceProtocol', perspective_resolver: 'PerspectiveResolverProtocol', refusal_recorder: 'RefusalRecorderProtocol') -> 'Perspective | RefusalEnvelope'`
- `govern_erasure` — **function**
  - `(*, grant: 'TokenGrant', tenant: 'str', product_class: 'str', product_version: 'str | None', parameters: 'Mapping[str, Any]', asked_at: 'datetime | None', surface: 'str', address: 'str', perspective: 'Perspective', erased: 'ErasedContentRefused', entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'RefusalRecorderProtocol') -> 'RefusalEnvelope'`
- `govern_resolution` — **function**
  - `(authorized: 'Authorized[ArtifactRead]', *, artifact_class: 'str', name: 'str', artifact_version: 'str', store: 'ArtifactStoreProtocol', entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'DisclosingRecorderProtocol', audit_log: 'AuditLog', surface: 'str', address: 'str') -> 'DereferencedEvidence | RefusalEnvelope'`
- `govern_scope_denial` — **function**
  - `(*, grant: 'TokenGrant', tenant: 'str', product_class: 'str', product_version: 'str | None', parameters: 'Mapping[str, Any]', asked_at: 'datetime | None', surface: 'str', address: 'str', denial: 'str', entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'RefusalRecorderProtocol') -> 'RefusalEnvelope'`
- `recorded_boundary` — **function**
  - `(*, refusal_recorder: 'object | None', builder: 'str') -> 'RefusalRecorderProtocol'`

## `ccf_runtime.authz.product_entitlement`

- `ControlPlaneProductEntitlementSource` — **class**
  - `(*, control_plane: 'ControlPlaneRegistry', clock: 'Callable[[], datetime]') -> 'None'`
- `EvidenceReadabilitySourceProtocol` — **class**
  - `(*args, **kwargs)`
- `PerspectiveResolverProtocol` — **class**
  - `(*, grant: 'TokenGrant', tenant: 'str', requested_role: 'str | None') -> 'Perspective'`
- `ProductEntitlementRefused` — **class**
  - `(*, error_code: 'str', message: 'str', policy: 'ProvenanceSource | None' = None, role: 'str | None' = None) -> 'None'`
- `ProductEntitlementSourceProtocol` — **class**
  - `(*args, **kwargs)`
- `TokenGrant` — **contract**
  - `{"authentication":"ccf.hitl.principal.AuthenticationClaims | None","client_id":"<class 'str'>","products":"frozenset[str] | None","scopes":"tuple[str, ...]","tenants":"frozenset[str]"}`
- `UnverifiedProductCallerRefused` — **class**
  - `type`
- `entitled_perspective` — **function**
  - `(*, grant: 'TokenGrant', tenant: 'str', product_class: 'str', requested_role: 'str | None', entitlement_source: 'ProductEntitlementSourceProtocol', perspective_resolver: 'PerspectiveResolverProtocol') -> 'Perspective'`
- `verified_grant` — **function**
  - `() -> 'TokenGrant'`

## `ccf_runtime.authz.protocol`

- `AuthzDecision` — **contract**
  - `{"action_id":"<class 'str'>","allowed":"<class 'bool'>","artifact_version":"<class 'str'>","decision_id":"str | None","matched_resource_pattern":"str | None","matched_scope_pattern":"str | None","resource":"<class 'str'>","tenant":"<class 'str'>"}`
- `ControlPlaneTenantAuthorizer` — **class**
  - `(*, control_plane: 'ControlPlaneRegistry', scope_mapping_key: 'str', scope_mapping_version: 'str', clock: 'Callable[[], datetime]') -> 'None'`
- `TenantAuthorizerProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf_runtime.authz.refusals`

- `ACTION_AGENT_DECLARE` — **constant**
  - `str`
- `ACTION_AGENT_LIST` — **constant**
  - `str`
- `ACTION_AGENT_READ` — **constant**
  - `str`
- `ACTION_AGENT_VERSIONS` — **constant**
  - `str`
- `ACTION_ARTIFACT_READ` — **constant**
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

## `ccf_runtime.authz.route_declaration`

- `ProductClassBinding` — **class**
  - `(*, source: 'ProductClassSource', name: 'str' = '') -> None`
- `ProductClassSource` — **class**
  - `(*values)`
- `ROUTE_AUTHORIZATION_ATTRIBUTE` — **constant**
  - `str`
- `ResourceBinding` — **class**
  - `(*, source: 'ResourceSource', name: 'str') -> None`
- `ResourceSource` — **class**
  - `(*values)`
- `RouteAuthorization` — **class**
  - `(*, action_id: 'str', resource: 'ResourceBinding', products: 'ProductClassBinding | None' = None, answers_denial: 'bool' = False) -> None`
- `TENANT_PATH_PARAM` — **constant**
  - `str`
- `authorizes` — **function**
  - `(action_id: 'str', *, resource: 'ResourceBinding', products: 'ProductClassBinding | None' = None, answers_denial: 'bool' = False) -> 'Callable[[_Endpoint], _Endpoint]'`
- `composed_fields` — **function**
  - `(template: 'str') -> 'tuple[str, ...]'`
- `route_authorization` — **function**
  - `(endpoint: 'object') -> 'RouteAuthorization | None'`

## `ccf_runtime.authz.tenancy`

- `AmbiguousTenantRefused` — **class**
  - `type`
- `TenantNotGrantedRefused` — **class**
  - `type`
- `UntenantedGrantRefused` — **class**
  - `type`
- `acting_tenant` — **function**
  - `(*, tenants: 'frozenset[str]', named: 'str | None') -> 'str'`
- `tenants_of_grant` — **function**
  - `(grant: 'object') -> 'frozenset[str]'`

## `ccf_runtime.cdc`

- `CDCMappingError` — **class**
  - `type`
- `CDCSourceAdapter` — **class**
  - `(*, system_id: 'str', change_op_key: 'str', source_path: 'Path | str | None' = None, lines: 'Sequence[str] | None' = None, clock: 'Callable[[], datetime] | None' = None) -> 'None'`
- `ChangeEvent` — **contract**
  - `{"after":"collections.abc.Mapping[str, typing.Any] | None","before":"collections.abc.Mapping[str, typing.Any] | None","op":"typing.Literal['c', 'u', 'd']","source":"<class 'ccf_runtime.cdc.envelope_map.ChangeSource'>","ts_ms":"<class 'int'>"}`
- `ChangeSource` — **contract**
  - `{"connector":"<class 'str'>","db":"<class 'str'>","table":"<class 'str'>"}`
- `change_image` — **function**
  - `(event: 'ChangeEvent') -> 'Mapping[str, Any]'`
- `commit_time` — **function**
  - `(event: 'ChangeEvent') -> 'datetime'`
- `envelope_id_for` — **function**
  - `(*, system_id: 'str', event: 'ChangeEvent') -> 'str'`
- `parse_change_event` — **function**
  - `(raw: 'object') -> 'ChangeEvent'`
- `to_envelope` — **function**
  - `(raw: 'object', *, tenant_id: 'str', system_id: 'str', change_op_key: 'str', ingestion_timestamp: 'datetime') -> 'SignalEnvelope'`

## `ccf_runtime.cdc.adapter`

- `CDCSourceAdapter` — **class**
  - `(*, system_id: 'str', change_op_key: 'str', source_path: 'Path | str | None' = None, lines: 'Sequence[str] | None' = None, clock: 'Callable[[], datetime] | None' = None) -> 'None'`

## `ccf_runtime.cdc.envelope_map`

- `CDCMappingError` — **class**
  - `type`
- `ChangeEvent` — **contract**
  - `{"after":"collections.abc.Mapping[str, typing.Any] | None","before":"collections.abc.Mapping[str, typing.Any] | None","op":"typing.Literal['c', 'u', 'd']","source":"<class 'ccf_runtime.cdc.envelope_map.ChangeSource'>","ts_ms":"<class 'int'>"}`
- `ChangeSource` — **contract**
  - `{"connector":"<class 'str'>","db":"<class 'str'>","table":"<class 'str'>"}`
- `change_image` — **function**
  - `(event: 'ChangeEvent') -> 'Mapping[str, Any]'`
- `commit_time` — **function**
  - `(event: 'ChangeEvent') -> 'datetime'`
- `envelope_id_for` — **function**
  - `(*, system_id: 'str', event: 'ChangeEvent') -> 'str'`
- `parse_change_event` — **function**
  - `(raw: 'object') -> 'ChangeEvent'`
- `to_envelope` — **function**
  - `(raw: 'object', *, tenant_id: 'str', system_id: 'str', change_op_key: 'str', ingestion_timestamp: 'datetime') -> 'SignalEnvelope'`

## `ccf_runtime.cli.commands`

- `CommandRefused` — **class**
  - `type`
- `RequestSpec` — **class**
  - `(method: 'str', path: 'str', params: 'Mapping[str, str]' = <factory>, json: 'object | None' = None, tolerate_empty_bump: 'bool' = False) -> None`
- `load_document` — **function**
  - `(path: 'str') -> 'dict[str, Any]'`

## `ccf_runtime.cli.commands.agent`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.artifact`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.backends`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.config`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.hitl`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.product`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.replay`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.schema`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.skill`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.skill_import`

- `MAX_REFERENCES` — **constant**
  - `int`
- `MAX_REFERENCE_BYTES` — **constant**
  - `int`
- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.commands.workflow`

- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`

## `ccf_runtime.cli.credential`

- `CredentialUnresolved` — **class**
  - `type`
- `authorization_headers` — **function**
  - `(credential: 'SecretStr') -> 'dict[str, str]'`
- `resolve_remote_credential` — **function**
  - `(*, token_env: 'str | None', token_file: 'str | None', environ: 'Mapping[str, str]') -> 'SecretStr'`

## `ccf_runtime.cli.evidence`

- `VERBS` — **constant**
  - `tuple`
- `register` — **function**
  - `(subparsers: "'argparse._SubParsersAction[argparse.ArgumentParser]'") -> 'None'`
- `run` — **function**
  - `(args: 'argparse.Namespace', opened: 'OpenedProduct', *, out: 'TextIO') -> 'int'`

## `ccf_runtime.cli.local`

- `build_local_dependencies` — **function**
  - `(*, root: 'Path', hitl_policy_key: 'str', erasure_trust: 'ErasureTrust') -> 'ApiDependencies'`

## `ccf_runtime.cli.main`

- `build_parser` — **function**
  - `() -> 'argparse.ArgumentParser'`
- `main` — **function**
  - `(argv: 'Sequence[str] | None' = None, *, dependencies: 'ApiDependencies | None' = None, authority: 'HttpAuthority | None' = None, credential: 'SecretStr | None' = None) -> 'int'`

## `ccf_runtime.erasure`

- `ErasureDoor` — **class**
  - `(*, engine: 'WorkflowEngine', factory: 'WorkflowFactory', control_plane: 'ControlPlaneRegistry', transport: 'HITLTransportProtocol', authority: 'ErasureAuthority', door_signer: 'IdentityProvider', door_key_id: 'str', store: 'ArtifactStoreProtocol', clock: 'Callable[[], datetime]', index: 'ErasureIndexProtocol', identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ErasureRefused` — **class**
  - `(message: 'str', *, reason_code: 'str', decision: 'RetentionDecision | None' = None) -> 'None'`
- `ErasureWorkflowUngated` — **class**
  - `type`

## `ccf_runtime.erasure.door`

- `ErasureDoor` — **class**
  - `(*, engine: 'WorkflowEngine', factory: 'WorkflowFactory', control_plane: 'ControlPlaneRegistry', transport: 'HITLTransportProtocol', authority: 'ErasureAuthority', door_signer: 'IdentityProvider', door_key_id: 'str', store: 'ArtifactStoreProtocol', clock: 'Callable[[], datetime]', index: 'ErasureIndexProtocol', identity_provider: 'IdentityProvider | None' = None) -> 'None'`
- `ErasureRefused` — **class**
  - `(message: 'str', *, reason_code: 'str', decision: 'RetentionDecision | None' = None) -> 'None'`
- `ErasureWorkflowUngated` — **class**
  - `type`

## `ccf_runtime.http_api.app`

- `AUTH_POSTURE_SENTENCE` — **constant**
  - `str`
- `GovernedWiringError` — **class**
  - `type`
- `HttpAuthority` — **class**
  - `_TypedDictMeta`
- `create_app` — **function**
  - `(deps: 'ApiDependencies', *, auth: 'HttpAuthProtocol', authorizer: 'TenantAuthorizerProtocol', product_entitlement: 'ProductEntitlementSourceProtocol', perspective_resolver: 'PerspectiveResolverProtocol', refusal_recorder: 'RefusalRecorderProtocol', replay_record_product_class: 'str | None') -> 'FastAPI'`

## `ccf_runtime.http_api.auth`

- `BearerTokenAuth` — **class**
  - `(*, token_source: 'TokenSourceProtocol') -> 'None'`
- `HttpAuthProtocol` — **class**
  - `(*args, **kwargs)`

## `ccf_runtime.http_api.dependencies`

- `ApiDependencies` — **class**
  - `(*, control_plane: 'ControlPlaneRegistry', artifact_store: 'ArtifactStoreProtocol', erasure_index: 'ErasureIndexProtocol', erasure_trust: 'ErasureTrust', product_resolver: 'ProductResolverProtocol', workflow_factory: 'WorkflowFactory | None' = None, workflow_engine: 'WorkflowEngine | None' = None, hitl_transport: 'HITLTransportProtocol | None' = None, skill_catalog: 'SkillCatalog | None' = None, grant_ledger: 'GrantLedger | None' = None, clock: 'Callable[[], datetime] | None' = None) -> None`

## `ccf_runtime.http_api.errors`

- `ERROR_AMBIGUOUS_TENANT` — **constant**
  - `str`
- `ERROR_APPROVER_NOT_ELIGIBLE` — **constant**
  - `str`
- `ERROR_ARTIFACT_STORE_UNAUTHENTICATED` — **constant**
  - `str`
- `ERROR_DECISION_UNMINTABLE` — **constant**
  - `str`
- `ERROR_EVIDENCE_ABSENT` — **constant**
  - `str`
- `ERROR_EVIDENCE_CLASS_SEALED` — **constant**
  - `str`
- `ERROR_EVIDENCE_CLASS_UNRECOVERABLE` — **constant**
  - `str`
- `ERROR_EVIDENCE_DISCLOSURE_WITHHELD` — **constant**
  - `str`
- `ERROR_EVIDENCE_PRINCIPAL_MISMATCH` — **constant**
  - `str`
- `ERROR_EXECUTION_FENCED` — **constant**
  - `str`
- `ERROR_HITL_EVENT_REVALIDATION_REFUSED` — **constant**
  - `str`
- `ERROR_HITL_GATE_CLOSED` — **constant**
  - `str`
- `ERROR_INVALID_GRANT` — **constant**
  - `str`
- `ERROR_NO_CAPABILITY` — **constant**
  - `str`
- `ERROR_PRINCIPAL_NOT_ENTITLED` — **constant**
  - `str`
- `ERROR_PRODUCT_CLASS_UNENTITLED` — **constant**
  - `str`
- `ERROR_PRODUCT_DOOR_UNGOVERNED` — **constant**
  - `str`
- `ERROR_PRODUCT_OUTSIDE_ROSTER` — **constant**
  - `str`
- `ERROR_PRODUCT_PARAMETERS_MALFORMED` — **constant**
  - `str`
- `ERROR_PRODUCT_POLICY_ABSENT` — **constant**
  - `str`
- `ERROR_PRODUCT_REQUEST_INCOMPLETE` — **constant**
  - `str`
- `ERROR_PRODUCT_ROLE_UNGRANTED` — **constant**
  - `str`
- `ERROR_REQUEST_UNAUTHORIZED` — **constant**
  - `str`
- `ERROR_ROUTE_HANDLE_ABSENT` — **constant**
  - `str`
- `ERROR_SIGNED_BINDING_INVALID` — **constant**
  - `str`
- `ERROR_SIGNED_BINDING_MISMATCH` — **constant**
  - `str`
- `ERROR_SIGNED_BINDING_REQUIRED` — **constant**
  - `str`
- `ERROR_SIGNED_BINDING_STALE` — **constant**
  - `str`
- `ERROR_SUBJECT_CONFLICT` — **constant**
  - `str`
- `ERROR_TENANT_UNAUTHORIZED` — **constant**
  - `str`
- `ERROR_UNAUTHENTICATED` — **constant**
  - `str`
- `ERROR_UNTENANTED_GRANT` — **constant**
  - `str`
- `refusal_detail` — **function**
  - `(*, error_code: 'str', message: 'str') -> 'dict[str, str]'`

## `ccf_runtime.http_api.gate`

- `AuthorizationGate` — **class**
  - `(app: '_ASGIApp', *, auth: 'HttpAuthProtocol', authorizer: 'TenantAuthorizerProtocol', table: 'tuple[RouteEntry, ...]', replay_record_product_class: 'str | None' = None) -> 'None'`
- `RouteEntry` — **class**
  - `(*, template: 'str', methods: 'frozenset[str]', declaration: 'RouteAuthorization', matcher: 're.Pattern[str]', parameters: 'frozenset[str]') -> None`
- `UndeclaredRouteError` — **class**
  - `type`
- `build_route_table` — **function**
  - `(app: 'object') -> 'tuple[RouteEntry, ...]'`
- `mounted_routes` — **function**
  - `(app: 'object') -> 'Iterator[tuple[str, object]]'`

## `ccf_runtime.http_api.grants`

- `GateDenial` — **class**
  - `(*, grant: 'TokenGrant', tenant: 'str', statement: 'str') -> None`
- `absent` — **function**
  - `(key: 'str', version: 'str') -> 'HTTPException'`
- `authorized_from_request` — **function**
  - `(request: 'Request', *, kind: 'type[A]') -> 'Authorized[A]'`
- `denial_from_request` — **function**
  - `(request: 'Request') -> 'GateDenial | None'`
- `grant_from_request` — **function**
  - `(request: 'Request') -> 'TokenGrant | None'`
- `within_tenant` — **function**
  - `(*, tenant: 'str', key: 'str') -> 'bool'`

## `ccf_runtime.http_api.refusal_status`

- `STATUS_BY_KIND` — **constant**
  - `mappingproxy`
- `STATUS_FULFILLMENT_WITHHELD` — **constant**
  - `int`
- `STATUS_GONE` — **constant**
  - `int`
- `STATUS_REQUEST` — **constant**
  - `int`
- `STATUS_UNAVAILABLE` — **constant**
  - `int`
- `status_for` — **function**
  - `(kind: 'str') -> 'int'`

## `ccf_runtime.http_api.routes`

- `CONTENT_ADDRESS_HEADER` — **constant**
  - `str`
- `REPLAY_REF_HEADER` — **constant**
  - `str`
- `REQUEST_ECHO_HEADER` — **constant**
  - `str`
- `canonical_response` — **function**
  - `(payload: 'object', *, replay_ref: 'str | None' = None, asked: 'WireRequest | None' = None) -> 'Response'`
- `governed_refusal_response` — **function**
  - `(envelope: 'RefusalEnvelope') -> 'JSONResponse'`
- `refusal_response` — **function**
  - `(refusal: 'CCFContract', *, status_code: 'int') -> 'JSONResponse'`

## `ccf_runtime.http_api.routes.agent`

- `AgentDeclarationRequest` — **contract**
  - `{"definition":"<class 'ccf.agents.definitions.AgentDefinition'>","key":"<class 'str'>"}`
- `AgentDeclared` — **contract**
  - `{"key":"<class 'str'>","version":"<class 'str'>"}`
- `build_router` — **function**
  - `(deps: 'ApiDependencies') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.artifact`

- `ARTIFACT_WRITE_RESOURCE` — **constant**
  - `str`
- `ArtifactPutRequest` — **contract**
  - `{"artifact":"dict[str, object]","artifact_class":"<class 'str'>","name":"<class 'str'>"}`
- `build_router` — **function**
  - `(deps: 'ApiDependencies', *, entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'DisclosingRecorderProtocol') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.backends`

- `build_router` — **function**
  - `(deps: 'ApiDependencies') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.config`

- `ConfigRegistered` — **contract**
  - `{"key":"<class 'str'>","version":"<class 'str'>"}`
- `ConfigRegistrationRequest` — **contract**
  - `{"artifact":"dict[str, typing.Any]","class_id":"<class 'str'>","key":"<class 'str'>"}`
- `build_router` — **function**
  - `(deps: 'ApiDependencies') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.hitl`

- `build_router` — **function**
  - `(deps: 'ApiDependencies') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.product`

- `build_router` — **function**
  - `(deps: 'ApiDependencies', *, entitlement_source: 'ProductEntitlementSourceProtocol', perspective_resolver: 'PerspectiveResolverProtocol', refusal_recorder: 'RefusalRecorderProtocol') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.replay`

- `build_router` — **function**
  - `(deps: 'ApiDependencies', *, entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'DisclosingRecorderProtocol') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.schema`

- `build_router` — **function**
  - `(deps: 'ApiDependencies') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.skill`

- `CATALOG_REGISTER_RESOURCE` — **constant**
  - `str`
- `GrantIssued` — **contract**
  - `{"grant_hash":"<class 'str'>"}`
- `GrantRequest` — **contract**
  - `{"definition_key":"<class 'str'>","definition_version":"<class 'str'>","grant":"<class 'ccf.skills.grants.SkillGrant'>"}`
- `GrantRevocationRequest` — **contract**
  - `{"grant_hash":"<class 'str'>"}`
- `build_router` — **function**
  - `(deps: 'ApiDependencies') -> 'APIRouter'`

## `ccf_runtime.http_api.routes.workflow`

- `WorkflowInvocationRequest` — **contract**
  - `{"definition_key":"<class 'str'>","definition_version":"<class 'str'>","execution_id":"<class 'str'>"}`
- `WorkflowResumptionRequest` — **contract**
  - `{"decision":"<class 'str'>","definition_key":"<class 'str'>","definition_version":"<class 'str'>","execution_id":"<class 'str'>"}`
- `build_router` — **function**
  - `(deps: 'ApiDependencies') -> 'APIRouter'`

## `ccf_runtime.identity_binding`

- `AuthenticationUnattested` — **class**
  - `type`
- `ERROR_AUTHENTICATION_UNATTESTED` — **constant**
  - `str`
- `attested_authentication` — **function**
  - `(claims: 'AuthenticationClaims | None') -> 'AuthenticationClaims'`
- `authentication_of_grant` — **function**
  - `(grant: 'TokenGrant') -> 'AuthenticationClaims | None'`
- `authentication_of_token` — **function**
  - `(token: 'AccessToken') -> 'AuthenticationClaims | None'`
- `principal_from_authorized` — **function**
  - `(authorized: 'Authorized[HitlSubmit]', *, authentication: 'AuthenticationClaims', action_time: 'datetime', product_content_hash: 'str', action: 'str') -> 'HumanPrincipalBinding'`

## `ccf_runtime.mcp.agent_directory`

- `context_contract_classes` — **function**
  - `(contract: 'ContextContract') -> 'frozenset[str]'`
- `exposed_agent` — **function**
  - `(definition: 'AgentDefinition', *, definition_key: 'str', definition_version: 'str', skills: 'tuple[SkillCatalogEntry, ...]') -> 'ExposedAgent'`

## `ccf_runtime.mcp.artifact_server`

- `ARTIFACT_BLOB_URI_SCHEME` — **constant**
  - `str`
- `ARTIFACT_META_URI_SCHEME` — **constant**
  - `str`
- `ARTIFACT_NAMES_URI_SCHEME` — **constant**
  - `str`
- `ArtifactPresence` — **contract**
  - `{"found":"<class 'bool'>"}`
- `ArtifactResolution` — **contract**
  - `{"content_address":"str | None","found":"<class 'bool'>"}`
- `ArtifactSubstrate` — **class**
  - `(*args, **kwargs)`
- `BLOB_URI_TEMPLATE` — **constant**
  - `str`
- `DOOR_NAMING_TOOL` — **constant**
  - `str`
- `META_URI_TEMPLATE` — **constant**
  - `str`
- `NAMES_URI_TEMPLATE` — **constant**
  - `str`
- `NAME_URI_TEMPLATE` — **constant**
  - `str`
- `NonCanonicalPayload` — **class**
  - `type`
- `PUT_ARTIFACT_TOOL` — **constant**
  - `str`
- `SUBJECT_MATCH_REFUSED` — **constant**
  - `str`
- `SUBJECT_MATCH_TOOL` — **constant**
  - `str`
- `SubjectMatchRefused` — **class**
  - `type`
- `artifact_blob_uri` — **function**
  - `(*, content_address: 'str') -> 'str'`
- `artifact_meta_uri` — **function**
  - `(*, content_address: 'str') -> 'str'`
- `build_artifact_server` — **function**
  - `(*, server_name: 'str', store: 'ArtifactSubstrate', token_verifier: 'TokenVerifier', auth_settings: 'AuthSettings', authorizer: 'TenantAuthorizerProtocol', entitlement_source: 'ProductEntitlementSourceProtocol', refusal_recorder: 'DisclosingRecorderProtocol', audit_log: 'AuditLog', erasure_index: 'ErasureIndexProtocol', control_plane: 'PinnedPolicySource', erasure_trust: 'ErasureTrust') -> 'FastMCP'`

## `ccf_runtime.mcp.auth`

- `AMBIENT_STDIO_CLAIM` — **constant**
  - `str`
- `FileTokenSource` — **class**
  - `(*, path: 'Path | str') -> 'None'`
- `PRODUCT_CLAIM` — **constant**
  - `str`
- `SourceBackedTokenVerifier` — **class**
  - `(*, source: 'TokenSourceProtocol') -> 'None'`
- `StaticTokenSource` — **class**
  - `(*, grants: 'Mapping[str, TokenGrant]') -> 'None'`
- `TENANT_CLAIM` — **constant**
  - `str`
- `TokenGrant` — **contract**
  - `{"authentication":"ccf.hitl.principal.AuthenticationClaims | None","client_id":"<class 'str'>","products":"frozenset[str] | None","scopes":"tuple[str, ...]","tenants":"frozenset[str]"}`
- `TokenSourceProtocol` — **class**
  - `(*args, **kwargs)`
- `authentication_claims` — **function**
  - `(grant: 'TokenGrant') -> 'Mapping[str, Any]'`
- `bounded_echo` — **function**
  - `(value: 'object') -> 'str'`
- `granted_products` — **function**
  - `(token: 'AccessToken') -> 'frozenset[str] | None'`
- `granted_tenants` — **function**
  - `(token: 'AccessToken') -> 'frozenset[str]'`
- `is_ambient_stdio` — **function**
  - `(token: 'AccessToken') -> 'bool'`
- `product_claims` — **function**
  - `(grant: 'TokenGrant') -> 'Mapping[str, Any]'`
- `tenant_claims` — **function**
  - `(grant: 'TokenGrant') -> 'Mapping[str, Any]'`

## `ccf_runtime.mcp.composed_product`

- `ComposedProduct` — **class**
  - `(tenant_id: 'str', declaration: 'ProductClassDeclaration', default_perspective: 'Perspective', control_plane: 'ControlPlaneRegistry', refusal_recorder: 'RefusalRecorderProtocol', door: 'EgressDoorBinding', environment: 'EnvironmentDocument', policy_bundle_pin: 'PolicyBinding', replay_store: 'ArtifactStoreProtocol', resolve: 'ProductResolverProtocol') -> None`
- `compose_for_door` — **function**
  - `(config_path: 'Path', *, boot_connection: 'Mapping[str, object]', environment_root: 'Path', door: 'EgressDoorBinding | None', replay_store: 'ArtifactStoreProtocol', replay_record_class: 'str', resolver: 'ProductResolverProtocol | None' = None, build_resolver: 'ResolverFactory | None' = None, default_perspective: 'Perspective | None' = None) -> 'ComposedProduct'`

## `ccf_runtime.mcp.egress`

- `AddressedQuestion` — **contract**
  - `{"asked_at":"<class 'datetime.datetime'>","freshness":"<class 'str'>","intent":"<class 'str'>","request":"<class 'str'>","subject":"<class 'str'>"}`
- `CCF_FAILURE_PREFIX` — **constant**
  - `str`
- `MAX_ADDRESS_QUESTION_BYTES` — **constant**
  - `int`
- `NaiveAskedAtRefused` — **class**
  - `type`
- `PRODUCT_ADDRESS_TEMPLATE` — **constant**
  - `str`
- `PRODUCT_REQUEST_TOOL` — **constant**
  - `str`
- `PRODUCT_URI_SCHEME` — **constant**
  - `str`
- `PRODUCT_URI_TEMPLATE` — **constant**
  - `str`
- `ProductNotServable` — **class**
  - `type`
- `ProductResolverProtocol` — **class**
  - `(*, tenant: 'str', product_class: 'str', version: 'str', perspective: 'Perspective', request: 'ProductRequest | None') -> 'ServedProduct | RefusalEnvelope'`
- `build_egress_server` — **function**
  - `(*, server_name: 'str', resolver: 'ProductResolverProtocol', token_verifier: 'TokenVerifier', auth_settings: 'AuthSettings', authorizer: 'TenantAuthorizerProtocol', entitlement_source: 'ProductEntitlementSourceProtocol', perspective_resolver: 'PerspectiveResolverProtocol', refusal_recorder: 'RefusalRecorderProtocol | None' = None, expose_product_resource: 'bool' = True, expose_product_tool: 'bool' = False, product_tool_description: 'str | None' = None, producer_id: 'str | None' = None, producer_tenant: 'str | None' = None) -> 'FastMCP'`
- `parse_product_address` — **function**
  - `(uri: 'str') -> 'tuple[str, str, str, AddressedQuestion]'`
- `product_address` — **function**
  - `(*, tenant: 'str', product_class: 'str', version: 'str', question: 'WireRequest', subject: 'str', intent: 'str', freshness: 'str', asked_at: 'datetime') -> 'str'`
- `product_uri` — **function**
  - `(*, tenant: 'str', product_class: 'str', version: 'str') -> 'str'`

## `ccf_runtime.mcp.experience`

- `AgentDirectoryProtocol` — **class**
  - `(*, tenant: 'str') -> 'tuple[ExposedAgent, ...]'`
- `AgentInvokerProtocol` — **class**
  - `(*, tenant: 'str', definition_key: 'str', definition_version: 'str', skill: 'str', arguments: 'Mapping[str, str]') -> 'str'`
- `AgentToolCatalog` — **contract**
  - `{"agents":"tuple[ccf_runtime.mcp.experience.AgentToolListing, ...]","tenant":"<class 'str'>"}`
- `AgentToolListing` — **contract**
  - `{"archetypes":"tuple[str, ...]","artifact_version":"<class 'str'>","definition_key":"<class 'str'>","definition_version":"<class 'str'>","description":"<class 'str'>","name":"<class 'str'>","tools":"tuple[ccf_runtime.mcp.experience.AgentToolSurface, ...]"}`
- `AgentToolSurface` — **contract**
  - `{"description":"<class 'str'>","input_schema":"dict[str, typing.Any]","skill":"<class 'str'>"}`
- `ContextProviderProtocol` — **class**
  - `(*, tenant: 'str', entity: 'str', perspective: 'Perspective') -> 'str'`
- `DEFAULT_INVOKE_AGENT_DESCRIPTION` — **constant**
  - `str`
- `DEFAULT_LIST_AGENTS_DESCRIPTION` — **constant**
  - `str`
- `DEFAULT_PRODUCT_RESOURCE_DESCRIPTION` — **constant**
  - `str`
- `EXPERIENCE_PRODUCT_URI_SCHEME` — **constant**
  - `str`
- `EXPERIENCE_PRODUCT_URI_TEMPLATE` — **constant**
  - `str`
- `EXPERIENCE_TOOLS` — **constant**
  - `frozenset`
- `ExperienceProductNotServable` — **class**
  - `type`
- `ExperienceProductResolverProtocol` — **class**
  - `(*, tenant: 'str', product_class: 'str', version: 'str', perspective: 'Perspective', request: 'ProductRequest | None') -> 'ServedProduct | RefusalEnvelope'`
- `ExperienceReplayReadRefused` — **class**
  - `type`
- `ExposedAgent` — **contract**
  - `{"archetypes":"tuple[str, ...]","artifact_version":"<class 'str'>","definition_key":"<class 'str'>","definition_version":"<class 'str'>","name":"<class 'str'>","product_classes":"frozenset[str] | None","skills":"tuple[ccf.skills.catalog.SkillCatalogEntry, ...]"}`
- `GET_CONTEXT_TOOL` — **constant**
  - `str`
- `GET_LINEAGE_TOOL` — **constant**
  - `str`
- `GET_REPLAY_RECORD_TOOL` — **constant**
  - `str`
- `INVOKE_AGENT_TOOL` — **constant**
  - `str`
- `LIST_AGENTS_TOOL` — **constant**
  - `str`
- `LineageProviderProtocol` — **class**
  - `() -> 'str'`
- `ReplayRecordReaderProtocol` — **class**
  - `() -> 'str'`
- `agent_tool_listing` — **function**
  - `(agent: 'ExposedAgent') -> 'AgentToolListing'`
- `build_experience_server` — **function**
  - `(*, server_name: 'str', product_resolver: 'ExperienceProductResolverProtocol', agent_directory: 'AgentDirectoryProtocol | None' = None, agent_invoker: 'AgentInvokerProtocol | None' = None, context_provider: 'ContextProviderProtocol | None' = None, lineage_provider: 'LineageProviderProtocol | None' = None, replay_record_reader: 'ReplayRecordReaderProtocol | None' = None, get_context_description: 'str | None' = None, get_lineage_description: 'str | None' = None, get_replay_record_description: 'str | None' = None, list_agents_description: 'str | None' = None, invoke_agent_description: 'str | None' = None, product_resource_description: 'str | None' = None, token_verifier: 'TokenVerifier', auth_settings: 'AuthSettings', authorizer: 'TenantAuthorizerProtocol', entitlement_source: 'ProductEntitlementSourceProtocol', perspective_resolver: 'PerspectiveResolverProtocol', refusal_recorder: 'RefusalRecorderProtocol | None' = None, entitled_product_class: 'str | None' = None, lineage_tenant: 'str | None' = None, replay_record_tenant: 'str | None' = None, replay_record_product_class: 'str | None' = None, tool_allowlist: 'frozenset[str] | None' = None) -> 'FastMCP'`
- `experience_product_uri` — **function**
  - `(*, tenant: 'str', product_class: 'str', version: 'str') -> 'str'`

## `ccf_runtime.mcp.hitl_server`

- `HITL_QUEUE_URI_SCHEME` — **constant**
  - `str`
- `HITL_QUEUE_URI_TEMPLATE` — **constant**
  - `str`
- `HitlActionRouteProtocol` — **class**
  - `(authorized: 'Authorized[HitlSubmit]', *, submission: 'HitlActionSubmission') -> 'str'`
- `HitlQueueView` — **contract**
  - `{"events":"tuple[ccf.hitl.transport.PendingHitlEvent, ...]","tenant":"<class 'str'>"}`
- `HitlQueueViewProtocol` — **class**
  - `(authorized: 'Authorized[HitlQueueRead]') -> 'tuple[PendingHitlEvent, ...]'`
- `SUBMIT_HITL_ACTION_TOOL` — **constant**
  - `str`
- `UnverifiedCallerRefused` — **class**
  - `type`
- `build_hitl_server` — **function**
  - `(*, server_name: 'str', queue_view: 'HitlQueueViewProtocol', action_route: 'HitlActionRouteProtocol', token_verifier: 'TokenVerifier', auth_settings: 'AuthSettings', authorizer: 'TenantAuthorizerProtocol', clock: 'Callable[[], datetime]') -> 'FastMCP'`
- `hitl_queue_uri` — **function**
  - `(*, tenant: 'str') -> 'str'`

## `ccf_runtime.mcp.product_door`

- `ProductDoor` — **class**
  - `(product: 'ServesProducts', credential: 'str', principal_id: 'str', role: 'str', scope: 'str', tenant_id: 'str', producer_id: 'str', _token_verifier: 'TokenVerifier', _authorizer: 'TenantAuthorizerProtocol', _entitlement_source: 'ProductEntitlementSourceProtocol', _perspective_resolver: 'PerspectiveResolverProtocol', _environ: 'Mapping[str, str]', _expose_product_resource: 'bool' = False) -> None`
- `ServesProducts` — **class**
  - `(*args, **kwargs)`
- `StdioIdentityRequired` — **class**
  - `type`
- `open_door` — **function**
  - `(product: 'ServesProducts', *, environ: 'Mapping[str, str] | None' = None, perspective_resolver: 'PerspectiveResolverProtocol | None' = None, entitlement_source: 'ProductEntitlementSourceProtocol | None' = None, expose_product_resource: 'bool' = False) -> 'ProductDoor'`
- `open_door_with_verifier` — **function**
  - `(product: 'ServesProducts', *, token_verifier: 'TokenVerifier', environ: 'Mapping[str, str] | None' = None, perspective_resolver: 'PerspectiveResolverProtocol | None' = None, entitlement_source: 'ProductEntitlementSourceProtocol | None' = None, expose_product_resource: 'bool' = False) -> 'ProductDoor'`
- `scope_mapping_key` — **function**
  - `(*, tenant_id: 'str') -> 'str'`

## `ccf_runtime.mcp.review_door`

- `ReviewActionRefused` — **class**
  - `type`
- `ReviewDoor` — **class**
  - `(queue: 'ReviewQueue', tenant_id: 'str', control_plane: 'ControlPlaneRegistry', scope_mapping_version: 'str', required_scopes: 'tuple[str, ...]', _token_verifier: 'TokenVerifier', _authorizer: 'ControlPlaneTenantAuthorizer', _clock: 'Callable[[], datetime]') -> None`
- `open_review_door` — **function**
  - `(queue: 'ReviewQueue', *, tenant_id: 'str', token_verifier: 'TokenVerifier', reviewer_scopes: 'Mapping[str, Sequence[str]]', clock: 'Callable[[], datetime]') -> 'ReviewDoor'`

## `ccf_runtime.mcp.tenancy`

- `AMBIENT_STDIO_CLAIM` — **constant**
  - `str`
- `ActionUnauthorizedRefused` — **class**
  - `type`
- `AmbientMutationRefused` — **class**
  - `type`
- `AmbiguousTenantRefused` — **class**
  - `type`
- `CrossTenantRefused` — **class**
  - `type`
- `DecisionUnmintableRefused` — **class**
  - `type`
- `GuardedSurface` — **class**
  - `(action: 'str', subject: 'TenantSubject', resource: 'ResourceSubject', mutating: 'bool', products: 'ProductReach') -> None`
- `ProductOutsideRosterRefused` — **class**
  - `type`
- `ProductReach` — **class**
  - `(argument: 'str | None' = None, declared: 'frozenset[str] | None' = None, undeclared: 'str | None' = None, resolve: 'ProductResolver | None' = None, unknown: 'str | None' = None) -> None`
- `READ_KINDS` — **constant**
  - `frozenset`
- `ResourceSubject` — **class**
  - `(argument: 'str | None' = None, declared: 'str | None' = None, route: 'bool' = False, template: 'str | None' = None) -> None`
- `ResourceUnreadableRefused` — **class**
  - `type`
- `TENANT_CLAIM` — **constant**
  - `str`
- `TenantGuardViolation` — **class**
  - `type`
- `TenantGuardedServer` — **class**
  - `(server: 'FastMCP', *, authorizer: 'TenantAuthorizerProtocol') -> 'None'`
- `TenantSubject` — **class**
  - `(argument: 'str | None' = None, declared: 'str | None' = None, grant: 'bool' = False) -> None`
- `TenantlessGrantRefused` — **class**
  - `type`
- `UnguardedSurfaceError` — **class**
  - `type`
- `UnverifiedTenantCallerRefused` — **class**
  - `type`
- `ambient_stdio_identity` — **function**
  - `(*, credential: 'str', principal_id: 'str', scope: 'str', tenant: 'str') -> 'AccessToken'`
- `granted_tenants` — **function**
  - `(token: 'AccessToken') -> 'frozenset[str]'`
- `is_ambient_stdio` — **function**
  - `(token: 'AccessToken') -> 'bool'`
- `roster_refusal` — **function**
  - `(surface: 'str', reason: 'str') -> 'ProductOutsideRosterRefused'`
- `tenant_claims` — **function**
  - `(grant: 'TokenGrant') -> 'Mapping[str, Any]'`
- `unguarded_surfaces` — **function**
  - `(server: 'FastMCP') -> 'frozenset[str]'`

## `ccf_runtime.orchestration`

- `DriverStateRetrievalError` — **class**
  - `type`
- `SegmentNotExecutedError` — **class**
  - `type`
- `WorkflowDriverError` — **class**
  - `type`
- `run_coroutine_sync` — **function**
  - `(coro: 'Coroutine[object, object, _T]', *, timeout: 'float | None' = None) -> '_T'`

## `ccf_runtime.orchestration.adk`

- `AdkWorkflowDriver` — **class**
  - `(*, engine: 'WorkflowEngine') -> 'None'`

## `ccf_runtime.orchestration.adk.driver`

- `AdkWorkflowDriver` — **class**
  - `(*, engine: 'WorkflowEngine') -> 'None'`

## `ccf_runtime.orchestration.claude_agent`

- `ClaudeAgentWorkflowDriver` — **class**
  - `(*, engine: 'WorkflowEngine') -> 'None'`

## `ccf_runtime.orchestration.claude_agent.driver`

- `ClaudeAgentWorkflowDriver` — **class**
  - `(*, engine: 'WorkflowEngine') -> 'None'`

## `ccf_runtime.orchestration.common`

- `DriverStateRetrievalError` — **class**
  - `type`
- `SegmentNotExecutedError` — **class**
  - `type`
- `WorkflowDriverError` — **class**
  - `type`
- `run_coroutine_sync` — **function**
  - `(coro: 'Coroutine[object, object, _T]', *, timeout: 'float | None' = None) -> '_T'`

## `ccf_runtime.orchestration.langgraph`

- `LangGraphWorkflowDriver` — **class**
  - `(*, engine: 'WorkflowEngine') -> 'None'`

## `ccf_runtime.orchestration.langgraph.driver`

- `LangGraphWorkflowDriver` — **class**
  - `(*, engine: 'WorkflowEngine') -> 'None'`

## `ccf_runtime.orchestration.reference`

- `WorkflowEngineOrchestrationAdapter` — **class**
  - `(*, engine: 'WorkflowEngine') -> 'None'`

## `ccf_runtime.peering.lf_a2a`

- `JSONRPC_BINDING` — **constant**
  - `str`
- `LfA2AWire` — **class**
  - `(*, local_peer_id: 'str', agent_card: 'AgentCard', cards: 'PeerCardResolver', http_client_factory: 'Callable[[], httpx.AsyncClient]', clock: 'Callable[[], datetime]', rpc_path: 'str', max_request_bytes: 'int', max_message_bytes: 'int', max_pending: 'int') -> 'None'`
- `PEER_ID_METADATA` — **constant**
  - `str`
- `PEER_TENANT_METADATA` — **constant**
  - `str`
- `PeerCardResolver` — **class**
  - `(*, peer: 'PeerRef') -> 'str'`
- `SIGNED_PRODUCT_MEDIA_TYPE` — **constant**
  - `str`
- `UnsupportedCarriageOperation` — **class**
  - `type`
- `build_agent_card` — **function**
  - `(*, name: 'str', version: 'str', description: 'str', rpc_url: 'str') -> 'AgentCard'`

## `ccf_runtime.peering.typed_http`

- `MalformedWireMessage` — **class**
  - `type`
- `PEER_ID_HEADER` — **constant**
  - `str`
- `PEER_TENANT_HEADER` — **constant**
  - `str`
- `PeerEndpointResolver` — **class**
  - `(*, peer: 'PeerRef') -> 'str'`
- `PeerUnreachable` — **class**
  - `type`
- `ReceiveQueueFull` — **class**
  - `type`
- `SIGNED_PRODUCT_MEDIA_TYPE` — **constant**
  - `str`
- `TypedHttpWire` — **class**
  - `(*, local_peer_id: 'str', endpoints: 'PeerEndpointResolver', http_client: 'httpx.Client', clock: 'Callable[[], datetime]', receive_path: 'str', max_request_bytes: 'int', max_pending: 'int') -> 'None'`
- `WIRE_MESSAGE_ID_HEADER` — **constant**
  - `str`
- `WireTransportError` — **class**
  - `type`

## `ccf_runtime.workflow.engine`

- `AgentNodeBinding` — **class**
  - `(*args, **kwargs)`
- `DebtAssessmentBinding` — **class**
  - `(*args, **kwargs)`
- `ExecutionFenced` — **class**
  - `type`
- `ForeignStateRecordError` — **class**
  - `type`
- `SkillNodeBinding` — **class**
  - `(*args, **kwargs)`
- `UnboundDebtAssessmentError` — **class**
  - `type`
- `WORKFLOW_TRACE_ARTIFACT_CLASS` — **constant**
  - `str`
- `WorkflowCompleted` — **contract**
  - `{"delegation_chain":"tuple[str, ...]","execution_id":"<class 'str'>","step_sequence_block":"<class 'str'>","tenant":"<class 'str'>","terminal_state":"<class 'str'>","trace_artifact":"<class 'ccf.artifacts.protocol.ArtifactRef'>"}`
- `WorkflowEngine` — **class**
  - `(*, control_plane: 'ControlPlaneRegistry', artifact_store: 'ArtifactStoreProtocol', hitl_transport: 'HITLTransportProtocol', skill_binding: 'SkillNodeBinding', agent_binding: 'AgentNodeBinding', clock: 'Callable[[], datetime]', audit: 'AuditLog | None' = None, debt_binding: 'DebtAssessmentBinding | None' = None) -> 'None'`
- `WorkflowExceptionRouted` — **contract**
  - `{"execution_id":"<class 'str'>","handler_ref":"<class 'str'>","node":"<class 'str'>","tenant":"<class 'str'>","trace_artifact":"<class 'ccf.artifacts.protocol.ArtifactRef'>"}`
- `WorkflowExecutionTypeError` — **class**
  - `type`
- `WorkflowOutcome` — **function**
  - `typing.Union[ccf_runtime.workflow.engine.WorkflowSuspended, ccf_runtime.workflow.engine.WorkflowCompleted, ccf_runtime.workflow.engine.WorkflowExceptionRouted, ccf_runtime.workflow.engine.WorkflowResumeRefused]`
- `WorkflowResumeRefused` — **contract**
  - `{"execution_id":"<class 'str'>","reason":"<class 'str'>","tenant":"<class 'str'>"}`
- `WorkflowSuspended` — **contract**
  - `{"event_key":"<class 'str'>","execution_id":"<class 'str'>","gate":"<class 'str'>","tenant":"<class 'str'>","trace_artifact":"<class 'ccf.artifacts.protocol.ArtifactRef'>"}`
- `WorkflowTraceReferenceMismatch` — **class**
  - `(*, fields: 'tuple[str, ...]') -> 'None'`
- `WorkflowWiringError` — **class**
  - `type`

## `ccf_runtime.workflow.state`

- `TRACE_ENTRY_KINDS` — **constant**
  - `frozenset`
- `TraceEntry` — **contract**
  - `{"kind":"<class 'str'>","occurred_at":"<class 'datetime.datetime'>","sequence":"<class 'int'>","source":"<class 'str'>","target":"<class 'str'>"}`
- `WORKFLOW_STATE` — **constant**
  - `str`
- `WORKFLOW_STATUSES` — **constant**
  - `frozenset`
- `WorkflowStateRecord` — **contract**
  - `{"current_state":"<class 'str'>","execution_id":"<class 'str'>","started_by":"str | None","state_store_identity":"str | None","status":"<class 'str'>","tenant":"<class 'str'>","trace":"tuple[ccf_runtime.workflow.state.TraceEntry, ...]","workflow_definition_hash":"<class 'str'>","workflow_definition_uri":"<class 'str'>"}`
- `suspension_left_by` — **function**
  - `(record: 'WorkflowStateRecord') -> 'WorkflowStateRecord | None'`
