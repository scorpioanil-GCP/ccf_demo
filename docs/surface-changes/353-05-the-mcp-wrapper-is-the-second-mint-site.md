# 353-05 — the MCP wrapper is the second mint site; bodies take `Authorized`

`D-IMPL-353` §1.1 names two producers of the capability and no third: the HTTP
`AuthorizationGate` and the MCP `TenantGuardedServer` wrapper. This fragment is
the MCP half. `runtime/ccf_runtime/mcp/tenancy.py::TenantGuardedServer` now
decides tenancy, asks the deployment's authorizer for the body's **declared**
action on its **declared** resource, and — on *allowed* and only then — mints
`Authorized[kind_for_action(action)]` and hands it to the body as its first
argument. A body registered through the wrapper has no `authorizer` parameter
and no `tenant` argument; it has `authorized`, or it has nothing to hand any
handle. Nothing is minted on any refusal.

## What did NOT change, stated first

- **Authentication is untouched.** The verifier/settings pair every builder
  already required is still what engages the library's bearer middleware; the
  wrapper decides on a verified identity and never establishes one.
- **The tenancy floor still runs first, and it runs before the authorizer is
  asked** (`tests/mcp/test_mint_site.py::test_the_tenancy_floor_runs_before_the_authorizer_is_asked`).
  A deployment's authorizer can never be what lets a cross-tenant call through.
- **`D-IMPL-129` is not reopened.** The three Experience tools are still not
  decided against `ProductEntitlementPolicy`; what they gained is a capability
  for a door-declared action, in the authorizer's own vocabulary.
- **The wire keeps its `tenant` argument** where it had one. It names *which*
  of a multi-tenant grant's tenants; the wrapper consumes it and the body reads
  `authorized.tenant`. FastMCP's input schema never carries `authorized`
  (`tests/mcp/test_mint_site.py::test_the_body_has_no_tenant_argument_and_the_wire_still_does`).

## THE POSTURE CHANGES, BECAUSE THEY SURPRISE PEOPLE

- **Every MCP builder takes a required `authorizer`.** `build_artifact_server`,
  `build_egress_server` and `build_experience_server` (and, at the join,
  `build_hitl_server`) cannot compose a door that decides nothing (§2 P4).
  A shipped example server that calls a builder bare does not build; that is a
  gap-ledger row for the join, not an example edit (`D-IMPL-261`).
- **`put_artifact` has no `tenant_id` argument.** The store files under
  `authorized.tenant`, and the class and name reach it as `authorized.resource`
  (`"<class>/<name>"`). A client still sending `tenant_id` is refused by the
  tool boundary.
- **The blob and presence resources go through the governed dereference**
  (§2 P5). There is no untenanted read of artifact bytes: their capability's
  tenant is the grant's **sole** tenant, and a grant spanning several is refused
  as ambiguous rather than picked for (§1.3). A consequence, stated rather than
  hidden: `govern_dereference` resolves its target as a Decision Replay record,
  so a stored artifact of any other class answers the `nonexistent` shell
  through the blob resource — the property the HTTP artifact GET has had since
  `D-IMPL-345`.
- **A mutating kind cannot be registered `mutating=False`**, so a stated stdio
  identity can be minted the kinds in `READ_KINDS` and never a mutating one.
- **Registration behind the wrapper is a boot failure** (§2 P9): the
  constructor refuses a `FastMCP` already carrying surfaces, `build()` is the
  only way to obtain the server and raises on any surface the ledger does not
  know, and the raw `.fastmcp` accessor is gone.
- **`open_door` no longer takes `token_verifier`.** An authority-typed
  parameter admitting `None` is what the §4 lint refuses; the paved road mints
  its own static credential as before, and a deployment with its own identity
  provider calls `open_door_with_verifier`, where the verifier is required.

## Joins this fragment names

- `store.put(authorized, artifact)` and `govern_dereference(authorized, ...)`
  are called in the design's §1.2 shapes ahead of Lanes HANDLES and CAP-GATE;
  `tests/mcp/test_artifact_server_authorized.py` carries their real-path
  controls as `xfail(strict=True)` and their contract controls green.
- `invoke_agent` is minted `workflow.invoke` (`Execute`) on `definition_key`
  until an `agent.invoke` action id and kind exist in `ccf.authz`
  (`runtime/ccf_runtime/mcp/experience.py::build_experience_server`).

## ccf_runtime.mcp.tenancy.TenantGuardedServer

- Surface: ccf_runtime.mcp.tenancy.TenantGuardedServer
- Public surface: true
- Change type: reshaped
- Before: `TenantGuardedServer(server)`; `.tool(*, name, subject, mutating)` and `.resource(uri, *, subject, mutating)` guarded tenancy and called the body with the caller's arguments; `.fastmcp` exposed the raw server; `.untenanted()` was a fourth subject reading
- After: `TenantGuardedServer(server, *, authorizer: TenantAuthorizerProtocol)` — refused for a server already carrying a surface; `.tool(*, name, action, subject, resource, mutating)` and `.resource(uri, *, action, subject, resource, mutating)` decide the declared action on the declared resource and call `body(authorized, **wire_arguments)`; `.build()` replaces `.fastmcp` and raises on a smuggled surface; `.from_grant()` replaces `.untenanted()`; four resource readers (`resource_argument`, `resource_declared`, `resource_route`, `resource_composed`); `.ledger` maps names to `GuardedSurface`
- Why: `D-IMPL-353` §1.1 — the wrapper is the MCP mint site; a body must receive a capability for exactly its action or nothing, and a raw registration must be a boot failure rather than a test failure (§2 P9)
- Migration: pass `authorizer=` at construction; declare `action=` and `resource=` at every registration; make the body's first parameter `authorized: Authorized[Kind]`, drop its `tenant` parameter and read `authorized.tenant`; return `door.build()` instead of `door.fastmcp`

## ccf_runtime.mcp.tenancy.TenantSubject

- Surface: ccf_runtime.mcp.tenancy.TenantSubject
- Public surface: true
- Change type: reshaped
- Before: fields `argument`, `declared`, `untenanted`
- After: fields `argument`, `declared`, `grant` — the third reading selects the grant's sole tenant and refuses a grant holding several as ambiguous
- Why: `D-IMPL-353` §1.3 — every capability names exactly one tenant, so no surface may be registered with none
- Migration: a surface that registered `untenanted()` registers `from_grant()`; a caller whose grant spans tenants names one on a surface that carries a tenant argument

## ccf_runtime.mcp.tenancy.ResourceSubject

- Surface: ccf_runtime.mcp.tenancy.ResourceSubject
- Public surface: true
- Change type: added
- Before: absent — the MCP doors decided on `(grant, tenant)` only, or passed the action id as the resource
- After: a closed reading of where the resource comes from — a wire argument, a declared value, the route itself, or a `str.format` template over the wire arguments
- Why: the fourth axis of the decision (`SEC-002`) has to be named per surface for the authorizer to decide it and the mint to bind it
- Migration: none for a caller; a registration states one of the four readers

## ccf_runtime.mcp.tenancy.GuardedSurface

- Surface: ccf_runtime.mcp.tenancy.GuardedSurface
- Public surface: true
- Change type: added
- Before: absent — the ledger held `TenantSubject` alone
- After: the ledger's value: `action`, `subject`, `resource`, `mutating` — everything a registration declared
- Why: an instrument reading the ledger must see the action a surface mints for, not only how it selects its tenant
- Migration: none

## ccf_runtime.mcp.tenancy.READ_KINDS

- Surface: ccf_runtime.mcp.tenancy.READ_KINDS
- Public surface: true
- Change type: added
- Before: absent — whether a surface mutated was a per-site boolean and nothing checked it against the action
- After: the kinds a stated (ambient stdio) identity may be minted; anything absent is mutating, and a registration whose kind is absent is refused as `mutating=False`
- Why: the per-site flag the ambient rule keys off must not be false for a mutating kind, or a stated identity could be minted a write
- Migration: none; a new kind is classified by `tests/mcp/test_mint_site.py::test_every_exported_kind_is_classified_read_or_mutating`

## ccf_runtime.mcp.tenancy.ActionUnauthorizedRefused

- Surface: ccf_runtime.mcp.tenancy.ActionUnauthorizedRefused
- Public surface: true
- Change type: added
- Before: absent — only the HITL door refused an authorizer's *no*, as a bare `ValueError`
- After: the typed refusal every wrapped surface raises when the authorizer denies; its message is the shared `ERROR_TENANT_UNAUTHORIZED` body rendered protocol-natively (D-08)
- Why: a denial at the mint site is one refusal class across every MCP surface, and nothing is minted on it
- Migration: a client parses the denial exactly as it parses the HTTP door's 403 body

## ccf_runtime.mcp.tenancy.AmbiguousTenantRefused

- Surface: ccf_runtime.mcp.tenancy.AmbiguousTenantRefused
- Public surface: true
- Change type: added
- Before: absent — a surface with no tenant on the wire compared nothing
- After: raised when a surface names no tenant and the verified grant holds more than one; the guard does not pick
- Why: `D-IMPL-353` §1.3 — a decision is about one tenant, selected from the grant, never chosen for it
- Migration: an operator credential spanning tenants uses a surface that carries a tenant argument, or a per-tenant credential

## ccf_runtime.mcp.tenancy.ResourceUnreadableRefused

- Surface: ccf_runtime.mcp.tenancy.ResourceUnreadableRefused
- Public surface: true
- Change type: added
- Before: absent
- After: raised when the declared resource argument is absent, empty or not a string — a deny, never a skip, before the authorizer is asked
- Why: the caller chooses what to send, and every choice must lead to the check running (the HTTP gate's rule, applied to arguments)
- Migration: none

## ccf_runtime.mcp.tenancy.UnguardedSurfaceError

- Surface: ccf_runtime.mcp.tenancy.UnguardedSurfaceError
- Public surface: true
- Change type: added
- Before: absent — a surface registered behind the wrapper was caught by `tests/mcp/test_tenant_guard.py` and by nothing at boot
- After: raised by the constructor for a server already carrying a surface and by `build()` for one registered after wrapping
- Why: `D-IMPL-353` §2 P9 — registration behind the wrapper is a boot failure, so a handler with no capability behind it never reaches the wire
- Migration: register every tool and resource through the wrapper

## ccf_runtime.mcp.tenancy.untenanted_surfaces

- Surface: ccf_runtime.mcp.tenancy.untenanted_surfaces
- Public surface: true
- Change type: removed
- Before: the pinned roster of surfaces registered with no tenant on the wire — two artifact resources
- After: absent; the reading it rostered no longer exists, and `tests/mcp/test_tenant_guard.py::test_every_surface_on_every_shipped_server_names_a_tenant_reading` asserts every ledger entry selects a tenant
- Why: every capability names one tenant (§1.3), so the roster is empty by construction rather than pinned
- Migration: none

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: reshaped
- Before: `build_artifact_server(*, server_name, store, token_verifier, auth_settings)`; `put_artifact(tenant_id, artifact_class, name, canonical_b64)`; the blob and presence resources read the store directly, untenanted
- After: `build_artifact_server(*, server_name, store, token_verifier, auth_settings, authorizer, entitlement_source, refusal_recorder, audit_log)`; `put_artifact(artifact_class, name, canonical_b64)` calls `store.put(authorized, artifact)` with `Authorized[ArtifactWrite]` for `"<class>/<name>"`; the blob and presence resources call `govern_dereference(authorized, ...)` with `Authorized[ArtifactRead]` for the address, and a refusal crosses as the shell's canonical bytes
- Why: `D-IMPL-353` §1.2 (the tenant is the capability's; `tenant_id` is deleted) and §2 P5 (no untenanted read of artifact bytes)
- Migration: compose the four new seams; a client stops sending `tenant_id` and expects a shell where it read `found: false`

## ccf_runtime.mcp.artifact_server.ARTIFACT_BLOB_SURFACE

- Surface: ccf_runtime.mcp.artifact_server.ARTIFACT_BLOB_SURFACE
- Public surface: true
- Change type: removed
- Before: the blob template's name, exported so the untenanted roster could pin it by identity
- After: absent; the resource is tenanted (from the grant) and no roster names it
- Why: the roster it existed for is gone (§1.3)
- Migration: use `BLOB_URI_TEMPLATE`

## ccf_runtime.mcp.artifact_server.ARTIFACT_META_SURFACE

- Surface: ccf_runtime.mcp.artifact_server.ARTIFACT_META_SURFACE
- Public surface: true
- Change type: removed
- Before: the presence template's name, exported for the untenanted roster
- After: absent
- Why: the roster it existed for is gone (§1.3)
- Migration: use `META_URI_TEMPLATE`

## ccf_runtime.mcp.egress.build_egress_server

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Change type: reshaped
- Before: no `authorizer`; the product resource, the request tool and the address resource took `tenant` as their first parameter
- After: `authorizer: TenantAuthorizerProtocol` is a required keyword; every body takes `authorized: Authorized[ProductRetrieve]` first and reads `authorized.tenant`; each surface is minted `product.retrieve` on `product_class`
- Why: `D-IMPL-353` §1.1 — the door's three surfaces run under a capability minted by the wrapper
- Migration: pass `authorizer=`; the wire is unchanged

## ccf_runtime.mcp.experience.build_experience_server

- Surface: ccf_runtime.mcp.experience.build_experience_server
- Public surface: true
- Change type: reshaped
- Before: no `authorizer`; bodies took `tenant` from the wire and asserted `verified_grant()`
- After: `authorizer: TenantAuthorizerProtocol` is a required keyword; every body takes `authorized` first — `product.retrieve` for the product resource, `get_context` and `get_lineage`; `agent.list` for `list_agents`; `replay.read` for `get_replay_record`; `workflow.invoke` (provisionally — see the joins above) on `definition_key` for `invoke_agent`
- Why: `D-IMPL-353` §1.1; the three tools `D-IMPL-129` left tenant-decided now carry a capability for a declared action
- Migration: pass `authorizer=`; the wire is unchanged

## ccf_runtime.mcp.product_door.open_door

- Surface: ccf_runtime.mcp.product_door.open_door
- Public surface: true
- Change type: reshaped
- Before: `open_door(product, *, environ=None, perspective_resolver=None, token_verifier=None, entitlement_source=None)` — `None` meant the paved road's static credential
- After: `open_door(product, *, environ=None, perspective_resolver=None, entitlement_source=None)`; the door also derives and registers a pinned scope mapping (`scope_mapping_key`) granting the declared scope `product.retrieve` on the declared class for the declared tenant, and builds the authorizer the egress builder now requires
- Why: `D-IMPL-353` §4 — an authority-typed parameter admitting `None` says an absent verifier is representable; the paved road keeps working without one
- Migration: a caller that passed `token_verifier=` calls `open_door_with_verifier`; every other call is unchanged

## ccf_runtime.mcp.product_door.open_door_with_verifier

- Surface: ccf_runtime.mcp.product_door.open_door_with_verifier
- Public surface: true
- Change type: added
- Before: absent — the deployment-verifier departure was `open_door(token_verifier=...)`
- After: `open_door_with_verifier(product, *, token_verifier, environ=None, perspective_resolver=None, entitlement_source=None)` — the same composition over a required verifier
- Why: two constructors rather than one `None`-typed authority parameter (§4)
- Migration: none for the paved road

## ccf_runtime.mcp.product_door.scope_mapping_key

- Surface: ccf_runtime.mcp.product_door.scope_mapping_key
- Public surface: true
- Change type: added
- Before: absent
- After: `scope_mapping_key(*, tenant_id)` — the Control Plane key one tenant's door scope mapping registers under, derived on the terms of `product_entitlement_key`
- Why: the door and its authorizer must not disagree about where a tenant's mapping lives, and the SDK holds no tenant
- Migration: none

## ccf_runtime.mcp.product_door.ProductDoor

- Surface: ccf_runtime.mcp.product_door.ProductDoor
- Public surface: true
- Change type: reshaped
- Before: fields ended `_token_verifier`, `_entitlement_source`, `_perspective_resolver`, `_environ`
- After: `_authorizer: TenantAuthorizerProtocol` sits between `_token_verifier` and `_entitlement_source`; `server()` passes it to `build_egress_server`
- Why: the door holds the authorizer `open_door` derived, as it holds the verifier
- Migration: none; the class is constructed by `open_door` and `open_door_with_verifier`
