# Security and Authorization

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

> This page describes SDK 1.0.2. Numbered-security disposition comes from the post-tag release register; deployment and delivered-build claims remain tied to their own evidence.

## Security model

CCF's runtime posture is built around one principle:

> **Unauthorized or ungoverned work should be unrepresentable at the protected seam, not merely detected because every caller remembered a check.**

That principle spans authorization capabilities, request shape, trusted time, product entitlement, human approval, artifact persistence, Replay provenance, erasure, peering, adapter isolation and supply-chain posture.

## Authorization capabilities and default deny

The action-bound capability model remains the base:

- authorization produces an `Authorized[action]` bound to one tenant, principal, action, resource and decision;
- protected handles verify the capability for their own action;
- HTTP route declarations and the runtime gate are default-deny;
- MCP wrappers mint the equivalent governed capability at registration/call boundaries;
- tenant resolution refuses ambiguous, ungranted or untenanted authority.

Composition-only authorities remain distinct from caller/door authorities. Current additions include `DeclaredSkillGrant`, `InvalidationRecordRegister`, and `ArtifactSubjectMatch`.

## Request and identity floors

`ProductRequestContract` includes `subject_domain`; `ArgumentDomain` supports patterns as well as numeric/member bounds.

`refuse_floor(...)` applies current SDK subject/parameter floors before downstream domain logic. Malformed input is a governed request refusal rather than an unchecked value reaching an adapter/query language.

`ccf.assembly.worker.IdentityRefused` remains the named refusal for unsafe entity identity minting; an empty identity declaration is not converted into a hash of `{}`.

## Trusted time

### Tenant temporal boundary

`TemporalBoundaryPolicy` declares:

- `max_past_seconds`;
- `permitted_clock_skew_seconds`.

Current writer/serve paths use the pinned policy and refuse out-of-window evidence/questions rather than inventing a default.

### Demonstration serve instant

Current main adds a separate development-only declaration:

- `ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstant`;
- `ccf.products.demonstration_clock.compose_serve_clock(...)`.

A paved deployment with a declared demonstration instant and **no custom clock** serves the dated demonstration at the declared instant and uses the same instant for ingress temporal judgment. A caller-composed clock beside the declaration is refused.

This mechanism is constrained to the SDK's ruled development posture; it is not a production clock override.

## Product entitlement and disclosure

### Declared multi-principal entitlement

`DeploymentConfig.product_entitlement` is the supported composition path for a product door serving multiple principals. `open_product` registers the declared policy; the standard door installs its one-principal default only when no declared policy is present.

The product roster carried on a verified token remains a separate transport constraint from `ProductEntitlementPolicy`.

### Unknown class vs unentitled caller

Current product HTTP/MCP paths can answer an undeclared product class with the same external `subject-unavailable` posture as an unentitled caller.

On HTTP, `RouteAuthorization.answers_denial`, `GateDenial`, `denial_from_request(...)`, and `govern_scope_denial(...)` let the product route preserve the internal authorizer denial in audit/Replay while returning the governed disclosure-shaped response.

Authentication, tenant selection, product roster and other gate failures remain separate.

## Human actions, eligibility and gate closure

Current signed-action surfaces remain:

- `HitlActionClaims`;
- `SignedHitlAction`;
- `sign_hitl_action(...)`;
- `verify_hitl_action(...)`;
- `enforce_attestation(...)`.

`ApprovalPolicy.eligible_principals` is the pinned statement of who may approve an approval gate.

A `WorkflowEngine` now binds its Control Plane into the transport's approver-eligibility judgment. The engine-composed reference transport refuses an ineligible `approve`/`reject`
before recording when the selected event is the gate's own approval-gate event
and names a policy. A third-party transport must expose the binding seam and
perform the judgment against every bound plane; construction checks the method's
presence, not that it enforces eligibility.

Late verdicts with no request for the exact pause and verdicts on a selected non-gate event
under the gate's key with the same pause fingerprint retain the conflict-hold gaps described in
[HITL](HITL.md#recorded-eligibility-exceptions). They do not let an ineligible
principal authorize passage. Do not describe eligibility checking as universal.

Current HITL gate state also includes:

- `GateClosure`;
- `GateAlreadyClosed`;
- `GateVerdictsChanged`;
- `HitlGateClosed`.

### Review door

`ccf_runtime.mcp.review_door.open_review_door(...)` composes an authenticated, event-target-bound authority path over `ReviewQueue`.

Review release/reject should flow through this door when the actor is an external authenticated principal; do not recreate a principal-string release path.

## Workflow resumption and fencing

Current main repairs a suspension whose approval request never reached the queue:

- the starter's retry or a resumption can restore the same missing request;
- no workflow step/effect is re-run;
- no approval is manufactured;
- a resumption performing restoration is first recorded as refused;
- competing recovery/state transitions can raise `ExecutionFenced`.

`WorkflowTraceReferenceMismatch` prevents a store-supplied trace reference from being handed out unless it is exactly the reference of the trace the engine wrote.

SDK 1.0.2 binds every state record and pause fingerprint to a permanent state-store identity. Independent stores cannot share one approval; foreign records refuse. Custom stores require identity and process-scoped leases, and custom transports require atomic per-pause enqueue/retire and exact-pause submission judgment. Legacy durable suspensions need rebind and fresh approval. See [migration requirements](MIGRATION_AND_LIMITATIONS.md). These controls do not create a distributed transaction over application effects.

## Artifact and Replay integrity

### Store roots and write authority

`FileArtifactStore` requires an explicit safe root and `write_kinds`; unsafe roots refuse through `InsecureArtifactStoreRoot`.

### Stored-byte integrity

A content-addressed path is not, by itself, proof that its current bytes still hash to the address.

Current integrity-sensitive readers re-hash before use, including:

- Replay/evidence reads;
- locally dispatched child-record reads;
- retained child-question reads;
- erasure-door reads;
- MCP artifact client-lane reads.

`ChildRecordAltered` is one named refusal on this boundary.

### Returned-reference integrity

Writers verify that a store's returned `ArtifactRef` is exactly the reference of what was written.

Current named failures include:

- `ReplayReferenceMismatch`;
- `QueryPinReferenceMismatch`;
- `ChildQuestionReferenceMismatch`;
- `AdmissionRecordReferenceMismatch`;
- `WorkflowTraceReferenceMismatch`.

### Governed record provenance

`ccf.replay.provenance` verifies filing by the governed record writer. A record-shaped client artifact does not become governed Replay evidence merely by matching the JSON shape.

### Control Plane read integrity

The registry keeps write-verified canonical bytes beside its protected reconstruction. Read doors parse those bytes and verify type/value/identity before returning a fresh object.

`RegistryIntegrityFailure` distinguishes corrupt/inconsistent existing registry state from a genuinely absent artifact.

## Per-entity invalidation records

Invalidation boundaries are now one `EntityInvalidationRecord` per `(tenant, entity)`.

`InvalidationRecordRegister` is a narrowly scoped composition authority for that tenant's `ccf.entity-invalidation-record` key range. It is not general Control Plane write authority.

`open_product` exposes the product's tenant-scoped invalidation sink; use that sink for external invalidation events.

## Erasure and subject matching

Current erasure is whole-artifact **read withholding**, not byte destruction.

Erasure trust/index/approval remain deployment-declared and fail closed.

Current main also adds `ccf.erasure.subject_match` and MCP subject-match/door-naming surfaces. These allow erasure paths to judge what a remote artifact names without turning the operation into a general artifact read.

Readers verify addressed bytes before subject judgment.

## SEC-020 subject-withholding controls

Current main contains substantially more than the Oct-9 pre-acquisition rendering change.

### Positive class declaration

`ProductClassDeclaration.subject_withholding` states `may-withhold` or `never`.

A class affirming `never` requires its plan factory to positively declare `withholds_no_subject() -> True`. Silence or a non-true declaration refuses at construction. A false positive declaration remains a measured limitation; the SDK cannot prove arbitrary deployment code truthful.

### Fresh-question / population controls

Current main also includes:

- the fixed unheld-subject probe, verified absent before it is used;
- refusal of a population-shaped read left in the subject-keyed phase;
- separate population-acquisition seams/contexts;
- question-fabric/question-store freshness and exclusivity checks;
- early-policy/request-aware-child requirements;
- stand-in/held-subject checks and constant-refusal paths;
- `executed_seeds`, `subject_withholding` and per-answer `issuance` evidence in Replay.

These are landed mechanisms. **They are not a blanket claim that every withheld subject is observationally identical to every nonexistent subject under arbitrary deployment code.**

Use the current SDK decision log for SEC-020 governance disposition.

## SQLite writer identity

Current main goes beyond the old path-only SQLite lease.

`SqliteConnection.writer_lease_lock_dir` can declare an absolute/private lock directory. With a declared lease, the SQLite writer lease keys an additional lock by the opened database file's device/inode so writers using different names for the same file converge on the same identity lock **when they declare the same lock directory**.

The SQLite store also refuses a regular database file with more than one name **at open, before setup**, including read-only opens.

Important limits remain:

- every writer must use the same declared lock directory for the identity lease to coordinate;
- no declaration retains the older limited posture;
- renaming a live SQLite database is not made safe and can strand WAL state;
- direct SQLite access outside the SDK is outside these controls.

Do not use hard-link backups of a live SDK-managed SQLite database.

## Peering replay and ingress bounds

Signed issuance/freshness remains required for peering admission.

Nonce identity is scoped by tenant and verified signing-key thumbprint. The default seen-set is shared by default gates within one process. Separate processes need a deployment-supplied shared/persistent/pruned implementation if cross-process replay rejection is required.

LF/A2A ingress requires `max_request_bytes` in addition to decoded message and pending-queue bounds. These are per-request/queue limits, not an aggregate process-memory guarantee.

## Stdio and harness isolation

Stdio remains a process-ownership, single-principal boundary. The standard ambient identity is tenant-scoped and read-only.

The Claude Agent SDK adapter remains isolated through its environment allowlist, owner-only prompt file, `tools=[]`, `setting_sources=[]`, `strict_mcp_config=True`, controlled cwd and fail-closed default transport. Remove prompt directories after dependent sessions complete.

Harness tool exposure remains limited to `tool`, `mcp`, and `local_callable`; `peering`, `mcp_product`, and `procedure` are not rendered as ordinary harness tools. Skill wire arguments are validated fail-closed before dispatch.

## Supply chain, version and license

Current main keeps:

- hash-pinned dependency lock/install path;
- read-only CI token posture and SHA-pinned actions;
- `setuptools_scm` dynamic version provenance;
- distribution name `ccf-sdk` while imports remain `ccf` / `ccf_runtime`.

Current SDK root `LICENSE.md` is the CCF SDK Software License. Its Schedule A fixes the delivered source at `01fc424d92f8d15856d5f277e9cf18ef59bc7883` and identifies the delivered wheel. This current-main technical reference does not alter that fixed delivery record.

## Assurance rule

A repaired mechanism is not automatically a closed numbered finding.

For assurance statements, use:

- the current SDK decision log;
- the controls register;
- the current implementation/source-change records;
- release/delivery evidence appropriate to the exact commit being deployed.

## Exact current surface

Use [Generated API Signatures](api/README.md), [Current Public Surface Index](PUBLIC_SURFACE_INDEX.md), [SDK Update Status](../../SDK_UPDATE_STATUS.md), and [Refresh Evidence](REFRESH_EVIDENCE.md).

## Delivery limits and migration

The controlled bank delivery qualifies MCP streamable HTTP on loopback, with a
SQLite graph store per instance and its identity lock. The bank product door constructs no workflow engine or approval queue. Other transports and
backends have suite evidence, not qualification under that exact configuration.
The shared service credential does not establish employee-specific authorization
or a narrow information-wall entitlement explanation.

**SEC-013, SEC-020 and SEC-027 remain open.** The release register reports SEC-009 closed; MCP-backed completion remains unsupported.
Erasure completion over the MCP-backed artifact store is unsupported; use an
in-process store for completion. Upgrade the MCP artifact server first or with
its clients, and keep mixed-version erasure requests disabled until the door
client is also upgraded.

See [Migration and Delivery Limits](MIGRATION_AND_LIMITATIONS.md) for the exact
HTTP status mappings, MCP upgrade requirements, HITL exceptions and pinned SDK
evidence. Green CI and a current API manifest do not close numbered findings.

## Current security disposition and exact delivery scope — 17 October 2026

The [post-tag register](https://github.com/drcastillo/ccf_code/blob/2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe/packaging/bank-controlled/OPEN-SECURITY-ITEMS.md) reports **27 of 30 findings closed; SEC-013, SEC-020 and SEC-027 open**. SEC-029 closed when `v1.0.2` was cut; the register inside the tag predates that closure. D-IMPL-392 explicitly permitted the release despite the remaining findings. Hosted release CI did not run; the licensor accepted the recorded local release check. These are source-attributed results, not a fresh security qualification by this documentation pass.

| Item | Released behavior | Boundary |
| --- | --- | --- |
| SEC-001 residual | Permanent state-store identity binds each approval to the store and exact pause; custom stores/queues must meet new contracts | Engine seam checks do not prove implementation persistence, uniqueness or atomicity; legacy paused runs require rebind and fresh approval |
| SEC-020 parts 1–3 | Scoped cp-06C acquisition and declared refusal for absent/out-of-request-scope facilities | Accepted for tested cp-06C only. SEC-020 remains open SDK-wide, with HIGH-rated parts; caller-chosen `borrower_scope` is not entitlement |
| SEC-030 | Opaque `ccf-runtime-failure:<id>` for unexpected ordinary exceptions in protected MCP acquisition/resolution/emission | Excludes preceding entitlement, HTTP, experience/agent tools, HITL and the standing `ccf-product://{tenant}/{class}/{version}` resource |
| SEC-029 | Wheel version is `1.0.2` from release tag | Does not establish a new bank delivery or a hosted CI result |

SEC-030 retains governed exception handling and correlates opaque IDs with operator-side exception types/frames without message text. Shutdown `BaseException` signals propagate. The bank door does not register the excluded standing resource; `build_egress_server` does by default.

| Build/source | Recorded status |
| --- | --- |
| `01fc424d92f8d15856d5f277e9cf18ef59bc7883`; `1.0.2.dev1564+g01fc424d9` | October 13 sealed bank delivery; lacks the later scoped SEC-020/030 and SEC-001 residual repairs |
| `5f85b389efe9e4b1de62e84a5af62ca4b2e12178`; `v1.0.2` | Released October 17; wheel `ccf_sdk-1.0.2-py3-none-any.whl`; source release notes record SHA-256 `1d18f600b121268aa58b6438507f682e7b877c78fedf3ea33b2e13e90be51a71`; not recorded as delivered to the bank |
| `2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe` | Merged main inspected October 18; runtime/examples/configuration identical to tag, with later handoff/release documentation |

Use the hash of the actual artifact supplied: a locally rebuilt wheel can have a different byte hash and must not be presented as the recorded wheel. Schedule A still names October 13; a later delivery needs the licensor's written grant/amendment.

Sources: [release notes](https://github.com/drcastillo/ccf_code/blob/2bd04d174a2acba8ec72cfeda3f9b8b22ccedcfe/packaging/bank-controlled/RELEASE-NOTES-1.0.2.md), [security guide](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/public/how-to/security-and-deployment.md), [MCP implementation](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/runtime/ccf_runtime/mcp/egress.py), [SEC-020 decomposition](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/packaging/bank-controlled/SEC-020-DECOMPOSITION.md).
