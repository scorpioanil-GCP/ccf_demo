# SDK Quick Reference

**Current SDK reference baseline:** `v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

## Current governed declarations

- Request shape: `ProductRequestContract.subject_domain`, `ArgumentDomain.pattern`
- Temporal boundary: `TemporalBoundaryPolicy`
- Development demo time: `DemonstrationServeInstant`
- Product entitlement: `DeploymentConfig.product_entitlement`
- Declared skills in force: `DeploymentConfig.grants`
- Subject withholding: `ProductClassDeclaration.subject_withholding`
- Human approval: `ApprovalPolicy`, `SignedHitlAction`
- Peering replay defense: `IssuanceClaims`, `SeenNonceSetProtocol`
- Evidence store: `FileArtifactStore(root=..., write_kinds=...)`

## Paved road

Use `open_product(...)` as the composition root. Current paved-road behavior can also compose:

- declared entitlement;
- declared grants;
- demonstration serve instant;
- invalidation sink;
- erasure-consulting store;
- request-scoped child factory over a complete declared chain.

Do not hand-recreate the resolver/gate/replay spine.

## Product doors

- Standard: `open_door(...)`
- Custom verifier: `open_door_with_verifier(...)`
- Optional resource: `expose_product_resource=True`
- Hand-composed governed product: `compose_for_door(...)`
- Human review queue: `open_review_door(...)`

## Refusal/integrity types worth knowing

- `TemporalBoundRefusal`
- `EvidenceAfterDecisionRefusal`
- `ChildRecordAltered`
- `ChildQuestionReferenceMismatch`
- `ReplayReferenceMismatch`
- `QueryPinReferenceMismatch`
- `AdmissionRecordReferenceMismatch`
- `WorkflowTraceReferenceMismatch`
- `ExecutionFenced`
- `RegistryIntegrityFailure`

## Store/graph migration seams

- Network-store writer lease: declare shared writer lease
- SQLite: optional `writer_lease_lock_dir`; same file + same directory coordinates by file identity
- SQLite multi-name file: refused at open, readers included
- Store creation: two-phase verified marker and bounded/zero-wait creation lock
- `store_creation_lock_wait_seconds`: absent = refuse immediately if held; present = bounded wait
- Read-only fabric: `boot(..., read_only=True)`
- Classification: boot-minted authority / governed reader
- Invalidation: one record per `(tenant, entity)`, through `opened.invalidation_sink`

## Replay/withholding

Current Replay records can carry `executed_seeds`, `issuance` and `subject_withholding`.

A class declaring `subject_withholding: never` must have a plan factory that positively declares `withholds_no_subject() -> True`.

SEC-020 defenses include the unheld-subject probe, question-store/fabric freshness rules, population-phase separation and stand-in checks. Do not translate those mechanisms into a universal closure claim.

## HITL/workflow

- Engine binds approver eligibility into the transport
- Gate closure is explicit
- ReviewQueue external release/reject goes through the review door
- Missing approval requests can be restored without rerunning workflow effects
- Concurrent/stale transitions can be `ExecutionFenced`

## Peering

- nonce key: tenant + verified key thumbprint + nonce
- default seen-set: process-wide, not cross-process persistent
- LF ingress: declare request-body and decoded-message limits

## Rules worth remembering

- refusal is data;
- authorization and Context Product policy are distinct;
- exact-version pins matter for Replay;
- content address and returned reference must both be held to what was written/read;
- stdio is single-principal;
- secrets/DSNs do not belong in governed config;
- demonstration time is development-only;
- current-main reference is not release qualification.

See [Generated API Signatures](api/README.md) for exact shapes.

## Current operational additions

- [Context Skills](CONTEXT_SKILLS.md): declare catalog/policy/producer/agent/grants; use [SK-01](../02-context-product-producer/examples/SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md).
- [Replay](DECISION_REPLAY.md): `evidence_root=`, `read_sources=False`, `OpenedProduct.replay_decision`.
- [Evidence CLI](CLI_HTTP_OPERATIONS.md#retained-evidence-commands): launcher `decisions`, `why`, `replay`.
- [Fluree](GRAPH_AND_STORAGE.md#current-fluree-pin-and-retained-graphs): 4.2.4.
- [Security](SECURITY_AND_AUTHORIZATION.md#current-security-disposition-and-exact-delivery-scope--17-october-2026): scoped SEC-020/030 fixes and separate delivered/candidate/current-main status.
