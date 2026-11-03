# Peering, MCP, and Runtime Surfaces

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

Do not collapse consumer transport, MCP product serving, review/HITL doors and fabric peering into one idea.

## Standard product door

Current product-door surfaces include:

- `ProductDoor`;
- `ServesProducts`;
- `open_door(...)`;
- `open_door_with_verifier(...)`;
- `StdioIdentityRequired`.

### Governed product resource

`open_door` / `open_door_with_verifier` now accept `expose_product_resource=False`.

Set it true when the deployment intentionally exposes the governed product resource in addition to the tool surface. The same product authorization/entitlement boundaries still apply.

### Multi-principal entitlement

The door composes over a deployment-declared `product_entitlement` policy when present. It only installs its one-principal default when no policy is already declared for the tenant.

## Hand-composed products

Use:

- `ccf_runtime.mcp.composed_product.ComposedProduct`;
- `compose_for_door(...)`.

This is the shared adapter for a governed product assembled outside `open_product`. It boots/holds the standard policy/refusal composition and gives the normal product door a `ServesProducts` conformer.

Do not copy an example-specific conformer.

## Stdio boundary

Stdio is process ownership, not a multi-principal authentication channel.

The standard ambient identity is tenant-scoped and read-only. A mutating surface refuses it before authorization.

Use loopback/HTTP or your own authenticated transport when callers must have distinct identities or mutating authority.

## Guarded MCP arguments

`TenantGuardedServer.tool` treats the tool's wire schema as closed world. Undeclared raw wire arguments refuse rather than being silently dropped by FastMCP.

Skill-level argument validation is a separate fabric seam and remains fail-closed.

## Product disclosure for unknown classes

Current product MCP/HTTP behavior avoids using "unknown class" as an existence oracle.

Where the product surface's scope/entitlement path denies an undeclared class, the external response can use the same governed `subject-unavailable` posture as an unentitled caller, while audit/Replay preserves the internal denial.

## Review door

`ccf_runtime.mcp.review_door.open_review_door(...)` is a HITL/review authority surface, not a product door.

It binds reviewer scopes to review-event key patterns and releases/rejects `ReviewQueue` entries through the standard authorized HITL path.

## Peering admission

Peering independently checks identity, trust, contract, payload bounds, lineage, and signed issuance/replay state.

Current issuance surfaces include `IssuanceClaims`, `SeenNonceSetProtocol`, and `InProcessSeenNonceSet`.

Nonce scope is tenant + verified signing-key thumbprint + nonce. Default gates share one seen-set within a process. Separate processes require a deployment-supplied shared/persistent/pruned implementation if cross-process replay rejection is required.

Admission-record writers also verify the returned `ArtifactRef`; a mismatch raises `AdmissionRecordReferenceMismatch`.

## Child question/record integrity

Composite child handling retains the exact asked question and verifies retained evidence:

- `ChildCandidate.asked_question`;
- `ChildQuestionReferenceMismatch`;
- `ChildRecordAltered`.

Do not reconstruct a child's question from its answer.

## Ingress bounds

`TypedHttpWire` requires `max_pending`.

LF/A2A ingress additionally requires positive `max_request_bytes` and the decoded `max_message_bytes`. Framing/base64 overhead means they are different limits.

These controls do not claim an aggregate process-memory bound.

## Claude Agent SDK adapter

The current adapter continues to isolate the child through:

- child-environment allowlist;
- owner-only prompt file/directory;
- controlled cwd;
- `tools=[]`;
- `setting_sources=[]`;
- `strict_mcp_config=True`;
- fail-closed vendor-default transport;
- explicit `max_turns`.

Call `adapter.remove_prompt_directories()` after dependent sessions end.

## Exact current shapes

Use the [Runtime API](api/runtime.md), [Extensions API](api/extensions.md), and [Security and Authorization](SECURITY_AND_AUTHORIZATION.md).
