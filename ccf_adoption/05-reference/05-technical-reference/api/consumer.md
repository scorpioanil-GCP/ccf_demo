# Consumer API — SDK 1.0.2 Signatures

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Exact public shapes for `ccf.client` and its current submodules.

This page is generated from `docs/surface/v0.2-surface.json` at `v1.0.2`. It is a lookup appendix; use the focused reference pages for semantics and examples.

> SDK 1.0.2 is tagged. Release status, deployment verification and the prior bank delivery remain separate; see [migration requirements](../MIGRATION_AND_LIMITATIONS.md).

## `ccf.client`

- `BindingError` — **class**
  - `type`
- `ProductClient` — **class**
  - `(*, product_id: 'str', adapter: 'TransportAdapter') -> 'None'`
- `Result` — **class**
  - `(*, product_id: 'str', parameters: 'Mapping[str, Any]', temporal_boundary: 'datetime | None', vessel: 'ContextProductContract | None', content_address: 'str | None', replay_ref: 'str | None', refusal: 'Refusal | None') -> 'None'`
- `TransportError` — **class**
  - `type`

## `ccf.client.adapters.binding_document`

- `BINDING_DOCUMENT_NAME` — **constant**
  - `str`
- `BindingDocument` — **class**
  - `(*, root: 'Path', config: 'Path', plan: 'str', question: 'QuestionDeclaration', perspective: 'Perspective', product_class_key: 'str', request_contract_key: 'str', operator_parameter_keys: 'tuple[str, ...]', policy_bundle_key: 'str', replay_record_class: 'str', query_pin_class: 'str', max_ttl_seconds: 'int', product_ttl_seconds: 'int', artifact_store: 'Path', debt: 'DebtDeclaration', erasure_authority: 'ErasureAuthorityDeclaration | None', connection: 'Mapping[str, object] | None', server: 'Path | None') -> None`
- `DATA_KEYS` — **constant**
  - `tuple`
- `DebtDeclaration` — **class**
  - `(*, half_life_key: 'str', debt_profile_key: 'str', completeness: 'Decimal', semantic_consistency: 'Decimal') -> None`
- `ErasureAuthorityDeclaration` — **class**
  - `(*, hitl_policy_key: 'str', workflow_definition_hash: 'str', door_keys: 'Mapping[str, Mapping[str, str]]') -> None`
- `OPTIONAL_KEYS` — **constant**
  - `tuple`
- `QuestionDeclaration` — **class**
  - `(*, subject: 'str', intent: 'str', freshness: 'str', asked_at: 'datetime | None') -> None`
- `REFERENCE_KEYS` — **constant**
  - `tuple`
- `RULED_OUT_KEYS` — **constant**
  - `dict`
- `conforming_plan_factory` — **function**
  - `(candidate: 'Any', *, reference: 'str', root: 'Path') -> 'ProjectionPlanFactoryProtocol'`
- `load_binding_document` — **function**
  - `(root: 'str | Path') -> 'BindingDocument'`
- `load_reference` — **function**
  - `(reference: 'str', *, root: 'Path', key: 'str') -> 'Any'`
- `looks_like_a_reference` — **function**
  - `(value: 'object') -> 'bool'`

## `ccf.client.adapters.inprocess`

- `InProcessAdapter` — **class**
  - `(address: 'str', *, clock: 'Callable[[], datetime]' = <function _utc_now>) -> 'None'`
- `SCHEME` — **constant**
  - `str`
- `reset_boot_cache` — **function**
  - `() -> 'None'`

## `ccf.client.adapters.mcp_stdio`

- `McpStdioAdapter` — **class**
  - `(address: 'str', *, clock: 'Callable[[], datetime]' = <function _utc_now>) -> 'None'`
- `SCHEME` — **constant**
  - `str`

## `ccf.client.binding`

- `AdapterFactory` — **function**
  - `collections.abc.Callable[[str], ccf.client.wire.TransportAdapter]`
- `BINDING_ENV_VAR` — **constant**
  - `str`
- `SCHEME_REGISTRY` — **constant**
  - `dict`
- `adapter_for_binding` — **function**
  - `(binding: 'str | None' = None, *, environ: 'Mapping[str, str] | None' = None) -> 'TransportAdapter'`
- `resolve_binding` — **function**
  - `(binding: 'str | None' = None, *, environ: 'Mapping[str, str] | None' = None) -> 'str'`
- `split_binding` — **function**
  - `(binding: 'str') -> 'tuple[str, str]'`

## `ccf.client.client`

- `ProductClient` — **class**
  - `(*, product_id: 'str', adapter: 'TransportAdapter') -> 'None'`

## `ccf.client.codec`

- `DecodedOutcome` — **class**
  - `(outcome: 'WireOutcome', vessel: 'ContextProductContract | None') -> None`
- `check_outcome` — **function**
  - `(outcome: 'WireOutcome', *, sent: 'WireRequest') -> 'ContextProductContract | None'`
- `decode_outcome` — **function**
  - `(raw: 'bytes', *, sent: 'WireRequest') -> 'DecodedOutcome'`
- `encode_outcome` — **function**
  - `(outcome: 'WireOutcome') -> 'bytes'`
- `verify_content_address` — **function**
  - `(product_json: 'str', claimed: 'str') -> 'str'`

## `ccf.client.errors`

- `BindingError` — **class**
  - `type`
- `RefusedResultError` — **class**
  - `type`
- `TransportError` — **class**
  - `type`

## `ccf.client.result`

- `GUARDED_FIELDS` — **constant**
  - `tuple`
- `PRE_ASSEMBLY_FIELDS` — **constant**
  - `tuple`
- `Refusal` — **contract**
  - `{"detail":"<class 'str'>","disclosure":"str | None","evidence":"ccf.products.refusal.RefusalEvidence | None","fields":"collections.abc.Mapping[str, str]","key":"str | None","kind":"<class 'str'>","policy_bindings":"tuple[ccf.products.provenance.ProvenanceSource, ...]","pre_assembly_lineage":"ccf.products.contract.ProductLineage | None","provenance":"ccf.products.provenance.EffectiveRequest | None","reason":"<class 'str'>","replay_reference":"<class 'str'>","request":"<class 'ccf.products.refusal.RequestIdentity'>","resource":"ccf.products.refusal.ResourceRequestIdentity | None"}`
- `Result` — **class**
  - `(*, product_id: 'str', parameters: 'Mapping[str, Any]', temporal_boundary: 'datetime | None', vessel: 'ContextProductContract | None', content_address: 'str | None', replay_ref: 'str | None', refusal: 'Refusal | None') -> 'None'`

## `ccf.client.wire`

- `TransportAdapter` — **class**
  - `(*args, **kwargs)`
- `WireOutcome` — **contract**
  - `{"answered":"ccf.products.door.AnsweredQuestion | None","content_address":"str | None","producer":"ccf.products.producer.ProducerAssertion | None","product_json":"str | None","refusal":"ccf.products.refusal.RefusalEnvelope | None","replay_ref":"str | None","request":"<class 'ccf.products.door.WireRequest'>"}`
- `WireRequest` — **contract**
  - `{"parameters":"collections.abc.Mapping[str, typing.Any]","product_id":"<class 'str'>","temporal_boundary":"datetime.datetime | None"}`
