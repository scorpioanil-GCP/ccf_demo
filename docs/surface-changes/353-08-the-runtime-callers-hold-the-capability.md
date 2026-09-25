# 353-08 — the runtime callers hold the capability; the join's reading of the seams

`D-IMPL-353` (design accepted 2026-09-24; `docs/D-IMPL-353-DESIGN.md`) and
`D-IMPL-354` (composition authority, PROPOSED at the join). Lane J-RUNTIME:
every HTTP route, MCP body, engine write and CLI composition under `runtime/`
now hands the §1.2 handles the capability the gate or the wrapper minted, or —
at a composition root — one minted through the D-IMPL-354 recipe. This
fragment records the runtime callers' migration and the three places the join
had to make a reading the lane texts left open: the governed dereference's
resource bind, the MCP artifact server's split, and the wrapper's decision id.

## What did NOT change, stated first

- **No action id changed value and no handle signature changed here.** The
  §1.2 handle signatures are Lane HANDLES' (`353-03`); this fragment records
  the callers reaching them and the three runtime seams that changed shape to
  do so.
- **The HTTP wire is unchanged for every route but one.** `ArtifactPutRequest`
  still carries `artifact_class`, `name` and `artifact`; what changed is the
  string the gate decides on (below). The catalog-register route's body is
  unchanged; what changed is likewise the decided resource.
- **`govern_absence`, `govern_entitlement` and `govern_raised_refusal` are
  untouched.** They still take `grant=`; only the evidence read moved to the
  capability.

## THE POSTURE CHANGES, BECAUSE THEY SURPRISE PEOPLE

- **The MCP artifact server round-trips every artifact class again (§7.4).**
  Lane MCP routed every blob and presence read through the governed
  dereference, which resolves its target as a Decision Replay record, so the
  §7.4 persistence transport could round-trip replay records only; the lane
  flagged it. The join implements THE SPLIT
  (`runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server`,
  module docstring): a hash-addressed read (1) verifies the capability against
  the address, (2) reads what the address IS from the substrate's reverse
  naming index, (3) routes any class the substrate's `WriteKinds` declares
  under `ReplayMint` through `govern_dereference`, and (4) serves every other
  class filed under the capability's tenant as the exact stored bytes, with one
  `authz_decision` audit event; an address filed under no name of the
  capability's tenant — another tenant's, or nothing — takes the governed
  branch too and answers the `nonexistent` shell byte-for-byte (up to the
  reference asked and the record produced) as a missing address does.
  Evidence: `tests/mcp/test_artifact_server_authorized.py` (the split's five
  controls) and `tests/conformance/test_artifactstore.py[mcp]`.
- **The governed dereference binds the capability to the REFERENCE, not to
  the door's `address`.** The lane brief said *verify against `address`*; on
  HTTP `address` is the route template (`/artifact/{content_address}`) and on
  MCP it is the blob URI, while the resource the gate or wrapper decided on is
  the content address or URI the caller asked for — `reference.reference`.
  `govern_dereference` therefore runs
  `verify_any(authorized, kinds=EVIDENCE_READ_KINDS, resource=reference.reference)`
  as its first statement. The faithful reading, stated rather than hidden.
- **The MCP wrapper refuses an allow it cannot mint from** (`decision-unmintable`,
  typed as `DecisionUnmintableRefused`, the HTTP gate's mirror) and mints
  `decision_id=decision.decision_id` — the authorizer's own audit event —
  instead of a content hash of the decision tuple, which named no record.
- **`create_app` refuses at boot** a refusal recorder whose store has not
  declared the recorder's record class under `ReplayMint`, or exposes no
  `WriteKinds` declaration at all (*don't know* is not *pass*). The
  `GovernedRecordClasses` / `GovernedWriteHandle` half Lane CAP-GATE wrote is
  retired with those names; `governed_wiring` reads `write_kinds` instead.
- **The HTTP artifact write is decided on `"<class>/<name>"`**, the store's
  own target — a new `ResourceBinding.body_composed` reading spells it from
  the two body fields, the HTTP counterpart of the MCP wrapper's
  `resource_composed`. A body that cannot spell the resource is a deny at the
  gate, never a skip. The catalog-register route is decided on the entry's
  own Control Plane key the same way.
- **The workflow engine's trace is a derived write the deployment must
  declare.** A store whose `WriteKinds` does not name
  `WORKFLOW_TRACE_ARTIFACT_CLASS` under `(Execute, Resume)` makes the first
  trace write fail closed; `cli.local` declares it, and every workflow fixture
  does.

## Joins this fragment names — files touched outside this lane's list

- `src/ccf/products/resolver.py::ReplayRefusalRecorder` — at the join base
  `record()` still built `ReplayWriter(store=, artifact_class=)`, whose
  constructor is now `(authorized, store)`, so every governed refusal raised
  `TypeError`. Bridged minimally: the recorder takes `authorized:
  Authorized[ReplayMint]`, verifies it at construction, and derives
  `tenant_id` and `replay_record_class` from it. J-SRC owns the final shape;
  the entry below is this bridge's.
- `src/ccf/skills/catalog.py::SkillCatalog.register` — called
  `register_versioned(key, ..., actor=)`; bridged to `(authorized, entry)`.
- `src/ccf/artifacts/file_store.py::FileArtifactStore.names_at` — the reverse
  naming index the split needs (a bare content address says nothing about
  class or tenant). Additive.
- `runtime/ccf_runtime/http_api/gate.py::AuthorizationGate` — the one method
  that extracts a `BODY_COMPOSED` resource; the gate is Lane CAP-GATE's.
- `runtime/ccf_runtime/http_api/routes/skill.py` — not on the lane's list;
  four whole-tree mypy errors at the join base, migrated with the other routes.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: reshaped
- Before: `govern_dereference(*, grant: TokenGrant, reference, store, entitlement_source, refusal_recorder, audit_log, surface, address)` — the principal was `grant.client_id`, the audited action was chosen by `reference.wants_bytes`
- After: `govern_dereference(authorized: Authorized[ArtifactRead] | Authorized[ReplayRead], *, reference, store, entitlement_source, refusal_recorder, audit_log, surface, address)` — `verify_any(authorized, kinds=EVIDENCE_READ_KINDS, resource=reference.reference)` is the first statement; the principal is `authorized.principal`; the audited action is the verified kind's; hold 2's entitlement seam is handed a grant carrying the capability's principal and tenant and nothing else
- Why: `D-IMPL-353` §1.2 — the governed evidence read takes the capability for its own action and has no grant or tenant parameter; the resource bind is the reference the door's declaration named, which is what the gate or wrapper decided on
- Migration: pass the capability from `authorized_from_request(request, kind=ArtifactRead|ReplayRead)` or the wrapper's first argument; drop `grant=`

## ccf_runtime.authz.delivery_boundary.EVIDENCE_READ_KINDS

- Surface: ccf_runtime.authz.delivery_boundary.EVIDENCE_READ_KINDS
- Public surface: true
- Change type: added
- Before: absent
- After: `(ArtifactRead, ReplayRead)` — the two kinds a governed evidence read is verified against, by identity
- Why: one roster for `verify_any`, beside the surfaces roster, so the dereference's kinds are a fact stated once
- Migration: none

## ccf_runtime.authz.delivery_boundary.EvidenceReadAuthority

- Surface: ccf_runtime.authz.delivery_boundary.EvidenceReadAuthority
- Public surface: true
- Change type: added
- Before: absent
- After: the alias `Authorized[ArtifactRead] | Authorized[ReplayRead]`, the static type of `govern_dereference`'s first parameter
- Why: a handler holding any other kind is a `mypy --strict` error at the call (§1.5b); `tests/authz/test_dereference_static.py` is the committed negative control
- Migration: none

## ccf_runtime.authz.delivery_boundary.EVIDENCE_SURFACES

- Surface: ccf_runtime.authz.delivery_boundary.EVIDENCE_SURFACES
- Public surface: true
- Change type: behavior
- Before: `{SURFACE_HTTP_REPLAY_READ, SURFACE_HTTP_ARTIFACT_READ}`
- After: adds `SURFACE_MCP_RESOURCE`, so a read-refusal record minted at the MCP blob or presence resource is recognized by `_is_read_refusal`
- Why: Lane MCP measured that an MCP-minted read refusal was withheld from its own principal at hold 2 as a record with no recoverable class
- Migration: none

## ccf_runtime.authz.delivery_boundary.DisclosingRecorderProtocol

- Surface: ccf_runtime.authz.delivery_boundary.DisclosingRecorderProtocol
- Public surface: true
- Change type: behavior
- Before: `tenant_id: str` declared as a settable data member
- After: `tenant_id` declared as a read-only property, so a recorder that derives its tenant from a composition-minted capability conforms
- Why: the SDK's recorder reads its tenant off `Authorized[ReplayMint]` (§1.3) and exposes it as a property
- Migration: none for conformers carrying a field; a conformer carrying a settable attribute still conforms

## ccf_runtime.authz.route_declaration.ResourceSource

- Surface: ccf_runtime.authz.route_declaration.ResourceSource
- Public surface: true
- Change type: behavior
- Before: four members — `PATH`, `QUERY`, `BODY`, `ROUTE`
- After: five — adds `BODY_COMPOSED`, a `str.format` template over named top-level body fields
- Why: the artifact store takes class and name from the capability's resource, so the gate must decide on exactly `"<class>/<name>"` spelled from two body fields (`D-IMPL-353` §1.2)
- Migration: none; a route that needs it declares `ResourceBinding.body_composed(template)`

## ccf_runtime.authz.route_declaration.ResourceBinding

- Surface: ccf_runtime.authz.route_declaration.ResourceBinding
- Public surface: true
- Change type: behavior
- Before: constructors `path`, `query`, `body`, `route`
- After: adds `body_composed(template)`; a template naming no usable field is refused at declaration
- Why: as `ResourceSource.BODY_COMPOSED`
- Migration: none

## ccf_runtime.authz.route_declaration.composed_fields

- Surface: ccf_runtime.authz.route_declaration.composed_fields
- Public surface: true
- Change type: added
- Before: absent
- After: `composed_fields(template) -> tuple[str, ...]` — the body fields a composed template names, in order; empty for a template naming nothing usable (positional, indexed, attribute or non-identifier fields)
- Why: the gate formats the template over exactly these names and nothing else, so a field the declaration did not name cannot reach the resource (`SEC-002`)
- Migration: none

## ccf_runtime.http_api.gate.AuthorizationGate

- Surface: ccf_runtime.http_api.gate.AuthorizationGate
- Public surface: true
- Change type: behavior
- Before: a `BODY`-sourced resource was one top-level string field
- After: a `BODY_COMPOSED`-sourced resource is the template formatted over its named fields; any named field absent, empty or not a string is a deny
- Why: the composed reading (above) has to be extracted by the gate, and the caller chooses what to send, so every choice leads to the check running
- Migration: none

## ccf_runtime.http_api.routes.artifact.ARTIFACT_WRITE_RESOURCE

- Surface: ccf_runtime.http_api.routes.artifact.ARTIFACT_WRITE_RESOURCE
- Public surface: true
- Change type: added
- Before: absent — the write was decided on the body's `name` alone
- After: `"{artifact_class}/{name}"`, the template the artifact PUT route declares through `ResourceBinding.body_composed`
- Why: one vocabulary for artifact resources at the HTTP door and the MCP tool, the store's own target
- Migration: a scope mapping that granted `artifact.write` on a name pattern now names `"<class>/<name>"` patterns

## ccf_runtime.http_api.routes.artifact.build_router

- Surface: ccf_runtime.http_api.routes.artifact.build_router
- Public surface: true
- Change type: behavior
- Before: PUT called `store.put(tenant_id=authorized.tenant, artifact_class=body.artifact_class, name=body.name, artifact=body.artifact)`; GET called `govern_dereference(grant=grant_from_request(request), ...)` with a 503 arm for a missing grant
- After: PUT calls `store.put(authorized_from_request(request, kind=ArtifactWrite), body.artifact)`; GET calls `govern_dereference(authorized_from_request(request, kind=ArtifactRead), ...)`; the 503 arm is gone with the grant
- Why: `D-IMPL-353` §1.2 — the handles take the capability; the tenant, class and name are the capability's
- Migration: none on the wire

## ccf_runtime.http_api.routes.replay.build_router

- Surface: ccf_runtime.http_api.routes.replay.build_router
- Public surface: true
- Change type: behavior
- Before: both reads called `govern_dereference(grant=grant_from_request(request), ...)` with a 503 arm for a missing grant
- After: both reads call `govern_dereference(authorized_from_request(request, kind=ReplayRead), ...)`; the module asserts `kind_for_action(ACTION_REPLAY_READ) is ReplayRead`
- Why: as the artifact route
- Migration: none on the wire

## ccf_runtime.http_api.routes.agent.build_router

- Surface: ccf_runtime.http_api.routes.agent.build_router
- Public surface: true
- Change type: behavior
- Before: `register_versioned(body.key, body.definition, AGENT_DEFINITION)` behind an `assert authorized.resource == body.key`
- After: `register_versioned(authorized, body.definition, AGENT_DEFINITION)` — the key is the capability's resource, the actor its principal; the response echoes `authorized.resource`
- Why: `D-IMPL-353` §1.2
- Migration: none on the wire

## ccf_runtime.http_api.routes.config.build_router

- Surface: ccf_runtime.http_api.routes.config.build_router
- Public surface: true
- Change type: behavior
- Before: `register_versioned(body.key, artifact, artifact_class)`
- After: `register_versioned(authorized, artifact, artifact_class)`
- Why: `D-IMPL-353` §1.2
- Migration: none on the wire

## ccf_runtime.http_api.routes.skill.CATALOG_REGISTER_RESOURCE

- Surface: ccf_runtime.http_api.routes.skill.CATALOG_REGISTER_RESOURCE
- Public surface: true
- Change type: added
- Before: absent — the catalog register route was decided on the entry's `name`
- After: `"{tenant}/ccf.skill-catalog-entry/{name}"`, the entry's own Control Plane key as `skill_catalog_key` derives it, declared through `ResourceBinding.body_composed`
- Why: the registry files under the capability's resource, so the gate must decide on exactly that key
- Migration: a scope mapping that granted `skill.catalog.register` on a name now names the key

## ccf_runtime.http_api.routes.skill.build_router

- Surface: ccf_runtime.http_api.routes.skill.build_router
- Public surface: true
- Change type: behavior
- Before: `catalog.register(entry)`; `ledger.request(body.grant, definition=..., actor=authorized.principal)`; `ledger.revoke(body.grant_hash, actor=authorized.principal)`
- After: `catalog.register(authorized, entry)`; `ledger.request(authorized, body.grant, definition=...)`; `ledger.revoke(authorized)` — the actor is the capability's principal, the grant hash its resource
- Why: `D-IMPL-353` §1.2
- Migration: none on the wire

## ccf_runtime.http_api.app.create_app

- Surface: ccf_runtime.http_api.app.create_app
- Public surface: true
- Change type: behavior
- Before: refused at boot a recorder over a store declaring its class governed (`GovernedRecordClasses`) without a `GovernedWriteHandle`
- After: refuses at boot a recorder whose store's `WriteKinds` does not name the recorder's class under `ReplayMint`, or exposes no `write_kinds` declaration
- Why: `D-IMPL-353` §3 read over the per-class write kinds Lane HANDLES put on the store; the retired names are gone
- Migration: declare the replay record class under `ReplayMint` on the store the doors serve from

## ccf_runtime.http_api.app.GovernedWiringError

- Surface: ccf_runtime.http_api.app.GovernedWiringError
- Public surface: true
- Change type: behavior
- Before: raised for a governed class with no minting handle
- After: raised for an undeclared class or an undeclaring store; the message names the class and the store's declaration
- Why: as `create_app`
- Migration: none

## ccf_runtime.mcp.tenancy.TenantGuardedServer

- Surface: ccf_runtime.mcp.tenancy.TenantGuardedServer
- Public surface: true
- Change type: behavior
- Before: minted `decision_id=content_hash(decision)`
- After: refuses, typed, an allow with no `decision_id` or one deciding about another tenant, action or resource, and mints `decision_id=decision.decision_id`
- Why: `D-IMPL-353` §1.5a — the capability names the audit event it is evidence of; a hash of the decision tuple named no record
- Migration: a deployment's own authorizer must populate `AuthzDecision.decision_id`; the SDK's does

## ccf_runtime.mcp.tenancy.DecisionUnmintableRefused

- Surface: ccf_runtime.mcp.tenancy.DecisionUnmintableRefused
- Public surface: true
- Change type: added
- Before: absent
- After: the `TenantGuardViolation` raised when the authorizer answered allowed with a decision the wrapper cannot mint from; its message is the shared `decision-unmintable` refusal body rendered protocol-natively
- Why: the HTTP gate's `ERROR_DECISION_UNMINTABLE`, mirrored at the MCP mint site
- Migration: none

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: reshaped
- Before: `store: ArtifactStoreProtocol`; the blob and presence resources dereferenced every address as a Decision Replay record
- After: `store: ArtifactSubstrate`; the blob and presence resources take THE SPLIT (posture changes above)
- Why: §7.4 — the persistence transport must round-trip every artifact class; the split needs the substrate's `write_kinds` and reverse index
- Migration: pass a store carrying `write_kinds` and `names_at` (the shipped `FileArtifactStore` does)

## ccf_runtime.mcp.artifact_server.ArtifactSubstrate

- Surface: ccf_runtime.mcp.artifact_server.ArtifactSubstrate
- Public surface: true
- Change type: added
- Before: absent
- After: a structural Protocol — `ArtifactStoreProtocol` plus `write_kinds` and `names_at(*, content_address)`
- Why: what the split needs of its substrate beyond the four Protocol methods
- Migration: none for `FileArtifactStore`; a deployment's own substrate carries the two members

## ccf_runtime.mcp.product_door.open_door

- Surface: ccf_runtime.mcp.product_door.open_door
- Public surface: true
- Change type: behavior
- Before: registered the entitlement policy and the scope mapping with bare keys
- After: registers each under a `Register` minted through the D-IMPL-354 recipe — a `composition` audit event on the product's Control Plane naming the key, then `mint_at_composition(Register, ...)` for exactly that key
- Why: `D-IMPL-354` — the door is a composition root and its own registrations are the deployment's act on its fabric
- Migration: none

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: `_persist` wrote `(WORKFLOW_STATE, key, record)` through the audited writer without the capability; `_write_trace` called `put(tenant_id=, artifact_class=, name=, artifact=)`; `_key` was an f-string
- After: `_persist` calls `write(authorized, WORKFLOW_STATE, record, record_id=execution_id, event=...)`; `_write_trace` calls `put(authorized, DerivedWrite(artifact_class=WORKFLOW_TRACE_ARTIFACT_CLASS, name=execution_id, artifact=trace))`; `_key` is `state_key(tenant=, record_id=)`
- Why: `D-IMPL-353` §1.2 derived writes — the deployment must declare the trace class under `(Execute, Resume)` or the first trace write fails closed
- Migration: declare `WORKFLOW_TRACE_ARTIFACT_CLASS: (Execute, Resume)` in the store's `WriteKinds`

## ccf_runtime.cli.local.build_local_dependencies

- Surface: ccf_runtime.cli.local.build_local_dependencies
- Public surface: true
- Change type: behavior
- Before: `FileArtifactStore(root=root / "artifacts")`
- After: the store declares `WORKFLOW_TRACE_ARTIFACT_CLASS` under `(Execute, Resume)` and nothing else
- Why: the local fabric composes an engine and no resolver; it declares what it writes and no lane it holds no capability for
- Migration: none

## ccf.products.resolver.ReplayRefusalRecorder

- Surface: ccf.products.resolver.ReplayRefusalRecorder
- Public surface: true
- Change type: reshaped
- Before: `ReplayRefusalRecorder(*, artifact_store, replay_record_class, tenant_id, assembly_mode, policy_bundle_pin=None, disclosure_level_for=...)`; `record()` built `ReplayWriter(store=, artifact_class=)` — red at the join base
- After: `ReplayRefusalRecorder(*, authorized: Authorized[ReplayMint], artifact_store, assembly_mode, policy_bundle_pin=None, disclosure_level_for=...)`; verifies the capability at construction; `replay_record_class` and `tenant_id` are read-only properties off it; `record()` builds `ReplayWriter(authorized=, store=)`
- Why: `D-IMPL-353` §1.2, §1.3, §2 P3 — the fabric's own writer is handed a `ReplayMint` at composition and there is no second source for the tenant or the class; the join's bridge, J-SRC owns the final shape
- Migration: mint `ReplayMint` for the record class at composition and pass `authorized=`; drop `replay_record_class=` and `tenant_id=`

## ccf.skills.catalog.SkillCatalog

- Surface: ccf.skills.catalog.SkillCatalog
- Public surface: true
- Change type: behavior
- Before: `register(entry, *, actor=None)` calling `register_versioned(key, entry, ..., actor=actor)` — red at the join base
- After: `register(authorized: Authorized[SkillCatalogRegister] | Authorized[Register], entry)`; the entry's derived key must equal the capability's resource or the call is refused before the registry is touched
- Why: `D-IMPL-353` §1.2 — the join's bridge for the catalog route and the fixtures; J-SRC owns the final shape
- Migration: pass the door's capability, or a composition-minted `Register` for `skill_catalog_key(entry)`

## ccf.artifacts.file_store.FileArtifactStore

- Surface: ccf.artifacts.file_store.FileArtifactStore
- Public surface: true
- Change type: reshaped
- Before: no reverse lookup over the naming index
- After: adds `names_at(*, content_address) -> tuple[ArtifactName, ...]` — every `(tenant, class, name)` an address was filed under; empty for an address nothing was filed under and for a string that is not an address
- Why: the artifact server's split has to know what an address IS before deciding how to read it
- Migration: none

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: `put` sent `tenant_id` on the wire; `get` returned whatever bytes the blob resource answered; `exists` raised `McpServerUnreachable` on a refusal shell
- After: `put` sends exactly `artifact_class`, `name`, `canonical_b64`; `get` verifies `sha256(bytes)` against the address and raises `ArtifactNotFound` for a shell; `exists` reads a shell as `False`
- Why: the tenant travels in the credential, never the wire (§1.3); a governed refusal is a shell, and this store reads it as absence rather than as the artifact or an outage
- Migration: none
