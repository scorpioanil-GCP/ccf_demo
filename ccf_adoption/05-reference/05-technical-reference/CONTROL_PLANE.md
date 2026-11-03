# Control Plane

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

The Control Plane defines what the fabric may do and preserves the versioned governance state needed to explain a determination later.

## Core rule

A YAML/JSON document is not authority merely because it exists. Current main uses typed artifact classes, versioned registration and composition-scoped capabilities to decide what may be registered or mutated.

Reserved SDK class identifiers are protected. `ReservedArtifactClassId` / `ArtifactClassIdMismatch` refuse documents or declarations that attempt to state a conflicting SDK class identity.

## Current declarations

Current deployment/Control Plane declarations include the established product, request, operator, policy, half-life/debt, perspective, Replay and TTL artifacts plus:

### Temporal boundary policy

`ccf.controlplane.temporal_boundary.TemporalBoundaryPolicy`

declares the accepted historical window and clock skew. No SDK default is invented when a governed path requires the policy.

### Demonstration serve instant

`ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstant`

is a development-only declared serve instant. It is placement-checked and resolved as a pinned Control Plane artifact; the paved product path honors it only under the ruled development conditions.

### Product entitlement

`DeploymentConfig.product_entitlement` is an optional tenant-scoped `ccf.product-entitlement-policy` declaration. This is the supported path for a standard product door serving multiple declared principals.

### Declared grants

`DeploymentConfig.grants` names declared skill labels. Composition requests them through `GrantLedger` with `DeclaredSkillGrant`; deployment code does not mint ordinary door grant authority.

### Subject-withholding stance

`ProductClassDeclaration.subject_withholding` declares `may-withhold` or `never`. A `never` declaration requires the corresponding plan factory's positive non-withholding declaration.

## Registry integrity

Current `ControlPlaneRegistry` retains verified canonical bytes with each registered reconstruction and checks them on read.

Important current failures include:

- `RegistryIntegrityFailure` — existing registry state is internally inconsistent/missing verified bytes;
- `ArtifactIsolationRefused` — parsing/reconstruction did not prove isolation/equality;
- `ArtifactClassIdMismatch` / `ReservedArtifactClassId` — class identity is not acceptable.

Read doors return fresh reconstructions rather than a mutable object held inside the registry.

## Per-entity invalidation records

Current main uses **one invalidation record per `(tenant, entity)`** rather than a whole-tenant invalidation register.

Public surfaces include:

- `InvalidationRecordRegister`;
- `invalidation_record_key(...)`;
- `INVALIDATION_RECORD_PREFIX`;
- `INVALIDATION_RECORD_CLASS_ID`;
- `compose_invalidation_sink(...)`.

The invalidation capability is confined to its own tenant's `ccf.entity-invalidation-record` keys. It is not general registry-write authority.

## State and workflow integrity

`ConditionalStateStore` now requires a permanent `identity`, validated by `state_store_identity_of` against `STATE_STORE_IDENTITY_PATTERN`; malformed or missing identity raises `StateStoreIdentityMissing` (engine composition reports `WorkflowWiringError`). A copied durable store must refuse to open. Process-scoped path-backed stores must hold an exclusive writer lease throughout their lifetime.

`WorkflowStateRecord.state_store_identity` binds the suspension hash to its store. Legacy `None` remains hash-transparent for old records but cannot authorize resumption: rebind and obtain fresh approval. Retirement is audited as `workflow_request_retired`. See [migration requirements](MIGRATION_AND_LIMITATIONS.md).

Workflow and approval code uses stronger reference/fencing checks on current main; see [HITL](HITL.md) and the runtime API appendix.

## Mechanism vs values

The SDK supplies interpretation mechanism. Deployments supply governed values such as:

- policy thresholds;
- temporal windows;
- trust grants;
- approval eligibility;
- request domains;
- demonstration instant (development only);
- product entitlement;
- declared grants.

Connection strings, credentials and host-local settings remain environment/runtime values, not content-hashed governance.

## Exact current shapes

Use [Governance API signatures](api/governance.md).

## Declared Context Skill authority

The policy envelope, catalog entry and effective grant have distinct roles. SDK composition requests deployment-declared grants using `DeclaredSkillGrant`; application examples should not mint that capability. SK-01 records grant events in the in-memory Control Plane. Its replay record identifies the granted set by hash, not members or requirements. See [Context Skills](CONTEXT_SKILLS.md).
