# 350-05 — default-deny at every door, and a tenant that comes from the grant

Tier 1 of the security review of 2026-09-23: `SEC-002` (authorization reached
exactly one router), `SEC-004` (artifact `put` ungoverned), `SEC-012` (a
caller-typed audit actor), `SEC-018` (the MCP grant carried no tenant).

Measured before: **25 HTTP route handlers, 9 of them mutating, and only 1 of
those 9 authorized anything.** Under the No-Hardcoding Rule the artifacts those
routes write ARE the system's behavior, so write access was behavior
modification by any recognized bearer.

## What did NOT change, stated first

- **Authentication was already sound** and is not what this changes. The MCP
  HTTP transports already required the verifier/settings pair; the library's
  own middleware already engaged. What was missing was authorization.
- **No harness import enters `/src`**, and no policy value enters code. Action
  identifiers are mechanism; which principal may take which action against
  which resource is the deployment's registered scope mapping.
- **`D-IMPL-129` is not reopened.** What that ruling declined — deciding three
  Experience tools against `ProductEntitlementPolicy` — stays declined. Tenancy
  needed no new vocabulary.

## THE POSTURE CHANGES, BECAUSE THEY SURPRISE PEOPLE

- **`create_app` cannot build an unauthenticated app.** All five seams are
  required; `acknowledge_insecure_default` is deleted, and both `| None` arms
  are removed rather than re-defaulted. `D-IMPL-73` permitted shipping
  unauthenticated with a WARNING; that warning had never been escalated to an
  error anywhere in CI (**0 `filterwarnings` directives repo-wide, measured**),
  so it was an unread channel.
- **`/health`, `/docs` and `/openapi.json` now require a credential.** A
  path-keyed carve-out is an applicability switch — the defect class this
  remediation exists to close. A deployment opens liveness with one visible
  line in its scope mapping.
- **`--local` is suspended** (see `350-03`).

## ccf_runtime.authz.artifact.pattern_matches

- Surface: ccf_runtime.authz.artifact.pattern_matches
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.artifact.validate_patterns

- Surface: ccf_runtime.authz.artifact.validate_patterns
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.route_declaration.authorizes

- Surface: ccf_runtime.authz.route_declaration.authorizes
- Public surface: true
- Change type: added
- Before: absent
- After: the decorator a route declares its action and resource with, applied inside the routing decorator
- Why: the declaration lives at the route it governs, so the two cannot drift apart in separate files
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.route_declaration.ResourceBinding

- Surface: ccf_runtime.authz.route_declaration.ResourceBinding
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.route_declaration.ResourceSource

- Surface: ccf_runtime.authz.route_declaration.ResourceSource
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.route_declaration.route_authorization

- Surface: ccf_runtime.authz.route_declaration.route_authorization
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.route_declaration.RouteAuthorization

- Surface: ccf_runtime.authz.route_declaration.RouteAuthorization
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.route_declaration.ROUTE_AUTHORIZATION_ATTRIBUTE

- Surface: ccf_runtime.authz.route_declaration.ROUTE_AUTHORIZATION_ATTRIBUTE
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.route_declaration.TENANT_PATH_PARAM

- Surface: ccf_runtime.authz.route_declaration.TENANT_PATH_PARAM
- Public surface: true
- Change type: added
- Before: absent
- After: `"tenant"` — DERIVED, never declared: the gate enforces `path["tenant"] == grant.tenant` for any route whose template names it
- Why: derived rather than declared so it cannot be forgotten on a new route. The path may ASSERT the tenant; it may never SUPPLY it
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.tenancy.TenantedGrant

- Surface: ccf_runtime.authz.tenancy.TenantedGrant
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.tenancy.tenant_of_grant

- Surface: ccf_runtime.authz.tenancy.tenant_of_grant
- Public surface: true
- Change type: added
- Before: absent
- After: the one way a door obtains a tenant
- Why: `tenant := grant.tenant` and nothing else is a source; a declared 'tenant source' other than the grant would be a walk-around selector
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.tenancy.UntenantedGrantRefused

- Surface: ccf_runtime.authz.tenancy.UntenantedGrantRefused
- Public surface: true
- Change type: added
- Before: absent
- After: raised when a verified grant carries no tenant
- Why: fail-closed: an authenticated caller with no tenant is refused, never defaulted to one
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.errors.ERROR_REQUEST_UNAUTHORIZED

- Surface: ccf_runtime.http_api.errors.ERROR_REQUEST_UNAUTHORIZED
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.errors.ERROR_UNTENANTED_GRANT

- Surface: ccf_runtime.http_api.errors.ERROR_UNTENANTED_GRANT
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.gate.AuthorizationGate

- Surface: ccf_runtime.http_api.gate.AuthorizationGate
- Public surface: true
- Change type: added
- Before: absent
- After: pure-ASGI middleware; every request is identified, matched to its route, and decided before any handler runs
- Why: measured on this repo's fastapi 0.140.0 / starlette 1.3.1: an app-level `dependencies=[Depends(guard)]` gate does NOT run on a malformed body (422), on `GET /openapi.json` (200) or on `GET /docs` (200). A middleware runs on all of them. A gate the caller can skip by sending two bad bytes is the Tier-0 defect at framework scope
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.gate.build_route_table

- Surface: ccf_runtime.http_api.gate.build_route_table
- Public surface: true
- Change type: added
- Before: absent
- After: the route table the gate decides against, raising `UndeclaredRouteError` naming EVERY offender at once
- Why: built at boot so an undeclared route refuses the app rather than the request; a CI sweep is a backup, not the gate
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.gate.mounted_routes

- Surface: ccf_runtime.http_api.gate.mounted_routes
- Public surface: true
- Change type: added
- Before: absent
- After: walks fastapi 0.140's lazy `_IncludedRouter` and `_low_priority_routes`
- Why: `app.routes` sees 6 of the 30 real routes. A sweep written against `app.routes` would pass while leaving 24 routes unchecked — vacuous, the failure mode this remediation keeps finding
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.gate.RouteEntry

- Surface: ccf_runtime.http_api.gate.RouteEntry
- Public surface: true
- Change type: added
- Before: absent
- After: one row of that table: the route, its declared action, and where its resource comes from
- Why: the gate reads declarations, never guesses them
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.gate.UndeclaredRouteError

- Surface: ccf_runtime.http_api.gate.UndeclaredRouteError
- Public surface: true
- Change type: added
- Before: absent
- After: raised at construction when a mounted route declares no action
- Why: boot-time refusal; 'forgot to add the check' stops being a state the software can be in
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.grants.tenant_from_request

- Surface: ccf_runtime.http_api.grants.tenant_from_request
- Public surface: true
- Change type: added
- Before: absent
- After: the tenant the gate already decided, read back by a handler
- Why: a handler never re-derives a tenant; it reads the one that was authorized
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.artifact_server.ARTIFACT_BLOB_SURFACE

- Surface: ccf_runtime.mcp.artifact_server.ARTIFACT_BLOB_SURFACE
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.artifact_server.ARTIFACT_META_SURFACE

- Surface: ccf_runtime.mcp.artifact_server.ARTIFACT_META_SURFACE
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.auth.AMBIENT_STDIO_CLAIM

- Surface: ccf_runtime.mcp.auth.AMBIENT_STDIO_CLAIM
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.auth.granted_tenants

- Surface: ccf_runtime.mcp.auth.granted_tenants
- Public surface: true
- Change type: added
- Before: absent
- After: reads the verified tenants off `AccessToken.claims`
- Why: the library's own `claims` field carries them, so no library change was needed
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.auth.is_ambient_stdio

- Surface: ccf_runtime.mcp.auth.is_ambient_stdio
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.auth.TENANT_CLAIM

- Surface: ccf_runtime.mcp.auth.TENANT_CLAIM
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.auth.tenant_claims

- Surface: ccf_runtime.mcp.auth.tenant_claims
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.AmbientMutationRefused

- Surface: ccf_runtime.mcp.tenancy.AmbientMutationRefused
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.AMBIENT_STDIO_CLAIM

- Surface: ccf_runtime.mcp.tenancy.AMBIENT_STDIO_CLAIM
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.ambient_stdio_identity

- Surface: ccf_runtime.mcp.tenancy.ambient_stdio_identity
- Public surface: true
- Change type: added
- Before: absent
- After: scopes stdio's stated identity to the door's own tenant and marks it ambient; every `mutating` surface refuses it
- Why: stdio has no bearer, so the library's auth middleware cannot apply. An ambient identity may read within its own tenant and may not mutate
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.CrossTenantRefused

- Surface: ccf_runtime.mcp.tenancy.CrossTenantRefused
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.granted_tenants

- Surface: ccf_runtime.mcp.tenancy.granted_tenants
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.is_ambient_stdio

- Surface: ccf_runtime.mcp.tenancy.is_ambient_stdio
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.TENANT_CLAIM

- Surface: ccf_runtime.mcp.tenancy.TENANT_CLAIM
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.tenant_claims

- Surface: ccf_runtime.mcp.tenancy.tenant_claims
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.TenantGuardedServer

- Surface: ccf_runtime.mcp.tenancy.TenantGuardedServer
- Public surface: true
- Change type: added
- Before: absent
- After: one MANDATORY wrapper over all 15 MCP tool and resource bodies; `subject`/`mutating` are required keyword args
- Why: a tool body that must REMEMBER to check tenancy is the Tier-0 defect at tool scope — applicability decided by each implementation. A body cannot be registered without entitlement
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.TenantGuardViolation

- Surface: ccf_runtime.mcp.tenancy.TenantGuardViolation
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.TenantlessGrantRefused

- Surface: ccf_runtime.mcp.tenancy.TenantlessGrantRefused
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.TenantSubject

- Surface: ccf_runtime.mcp.tenancy.TenantSubject
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.unguarded_surfaces

- Surface: ccf_runtime.mcp.tenancy.unguarded_surfaces
- Public surface: true
- Change type: added
- Before: absent
- After: compares the wrapper's ledger against FastMCP's own registry
- Why: catches a body registered behind the wrapper's back — the check that makes the wrapper mandatory rather than merely available
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.untenanted_surfaces

- Surface: ccf_runtime.mcp.tenancy.untenanted_surfaces
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.mcp.tenancy.UnverifiedTenantCallerRefused

- Surface: ccf_runtime.mcp.tenancy.UnverifiedTenantCallerRefused
- Public surface: true
- Change type: added
- Before: absent
- After: added by the Tier-1 authorization work
- Why: part of the default-deny surface (`SEC-002`/`SEC-018`)
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## The 22 action identifiers

Each names one door-declared verb. Mechanism identifiers, not policy: a
deployment's scope mapping grants them by name, and the SDK enumerates no
grant. Listed individually because a policy file names them by value, so a
rename later is expensive and getting them right now is free.

## ccf_runtime.authz.refusals.ACTION_AGENT_DECLARE

- Surface: ccf_runtime.authz.refusals.ACTION_AGENT_DECLARE
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_AGENT_DECLARE` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_AGENT_LIST

- Surface: ccf_runtime.authz.refusals.ACTION_AGENT_LIST
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_AGENT_LIST` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_AGENT_READ

- Surface: ccf_runtime.authz.refusals.ACTION_AGENT_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_AGENT_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_AGENT_VERSIONS

- Surface: ccf_runtime.authz.refusals.ACTION_AGENT_VERSIONS
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_AGENT_VERSIONS` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_ARTIFACT_WRITE

- Surface: ccf_runtime.authz.refusals.ACTION_ARTIFACT_WRITE
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_ARTIFACT_WRITE` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_BACKENDS_READ

- Surface: ccf_runtime.authz.refusals.ACTION_BACKENDS_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_BACKENDS_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_CONFIG_KEYS_READ

- Surface: ccf_runtime.authz.refusals.ACTION_CONFIG_KEYS_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_CONFIG_KEYS_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_CONFIG_REGISTER

- Surface: ccf_runtime.authz.refusals.ACTION_CONFIG_REGISTER
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_CONFIG_REGISTER` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_CONFIG_RESOLVE

- Surface: ccf_runtime.authz.refusals.ACTION_CONFIG_RESOLVE
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_CONFIG_RESOLVE` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_CONFIG_VERSIONS_READ

- Surface: ccf_runtime.authz.refusals.ACTION_CONFIG_VERSIONS_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_CONFIG_VERSIONS_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_DOCS_READ

- Surface: ccf_runtime.authz.refusals.ACTION_DOCS_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_DOCS_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_HEALTH_READ

- Surface: ccf_runtime.authz.refusals.ACTION_HEALTH_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_HEALTH_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_OPENAPI_READ

- Surface: ccf_runtime.authz.refusals.ACTION_OPENAPI_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_OPENAPI_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_SCHEMA_LIST

- Surface: ccf_runtime.authz.refusals.ACTION_SCHEMA_LIST
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_SCHEMA_LIST` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_SCHEMA_READ

- Surface: ccf_runtime.authz.refusals.ACTION_SCHEMA_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_SCHEMA_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_READ

- Surface: ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_SKILL_CATALOG_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_REGISTER

- Surface: ccf_runtime.authz.refusals.ACTION_SKILL_CATALOG_REGISTER
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_SKILL_CATALOG_REGISTER` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_SKILL_GRANT

- Surface: ccf_runtime.authz.refusals.ACTION_SKILL_GRANT
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_SKILL_GRANT` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_SKILL_REVOKE

- Surface: ccf_runtime.authz.refusals.ACTION_SKILL_REVOKE
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_SKILL_REVOKE` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_WORKFLOW_INVOKE

- Surface: ccf_runtime.authz.refusals.ACTION_WORKFLOW_INVOKE
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_WORKFLOW_INVOKE` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_WORKFLOW_RESUME

- Surface: ccf_runtime.authz.refusals.ACTION_WORKFLOW_RESUME
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_WORKFLOW_RESUME` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.authz.refusals.ACTION_WORKFLOW_STATUS_READ

- Surface: ccf_runtime.authz.refusals.ACTION_WORKFLOW_STATUS_READ
- Public surface: true
- Change type: added
- Before: absent
- After: `ACTION_WORKFLOW_STATUS_READ` — one door-declared action id
- Why: a route that declares no action refuses the app at boot; these are the vocabulary those declarations use
- Migration: none for a caller; a deployment binds thefive seams `create_app` now requires

## ccf_runtime.http_api.app.CcfDeadEntitlementWarning

- Surface: ccf_runtime.http_api.app.CcfDeadEntitlementWarning
- Public surface: true
- Change type: removed
- Before: the warning `create_app` emitted when an entitlement source was
  bound with nothing to make it effective — the WR-05 dead-hook shape
- After: absent. There is no dead-hook state left to warn about: every seam
  is required, so a hook that could not run is unrepresentable rather than
  announced
- Why: the warning existed because the posture allowed an app to be built
  half-wired. `D-IMPL-73` is deleted and the half-wired app is gone with it.
  A warning channel this repo never escalated to an error (**0
  `filterwarnings` directives, measured**) is not a control, and keeping it
  would imply a state that can no longer occur
- Migration: none. Code catching or filtering this warning can drop the
  handler; the condition it named is now a construction-time refusal

## ccf_runtime.http_api.routes.skill.GrantRequest

- Surface: ccf_runtime.http_api.routes.skill.GrantRequest
- Public surface: true
- Change type: reshaped
- Before: carried a caller-typed `actor` field, written into the
  replay-relevant grant ledger
- After: no `actor`. The audit actor is derived from the verified grant
- Why: `SEC-012`. An audit actor a caller can type is not an audit actor.
  Deleting the field makes a caller-supplied actor unrepresentable rather
  than merely refused — the same move as deleting `tenant_id` from the
  artifact-put body
- Migration: stop sending `actor`; it is refused by `extra=forbid`. `ccf
  skill grant` / `revoke` dropped `--actor` in the same change

## ccf_runtime.http_api.routes.skill.GrantRevocationRequest

- Surface: ccf_runtime.http_api.routes.skill.GrantRevocationRequest
- Public surface: true
- Change type: reshaped
- Before: carried a caller-typed `actor` field
- After: no `actor`; derived from the verified grant
- Why: `SEC-012`, identically — a revocation's actor is an audit fact about
  who revoked, and a fact the subject supplies about itself is not one
- Migration: stop sending `actor`

## ccf_runtime.authz.artifact.tenant_pattern_matches

- Surface: ccf_runtime.authz.artifact.tenant_pattern_matches
- Public surface: true
- Change type: removed
- Before: the tenant-only matcher
- After: absent — superseded by `pattern_matches`, which takes the axis it is matching on
- Why: a matcher named for one axis cannot carry a second. Renaming rather than overloading keeps the resource axis from reading as an afterthought bolted onto tenancy
- Migration: call `pattern_matches(value, patterns)`; `validate_patterns(value, axis=...)` names which axis it is validating

## ccf_runtime.http_api.app.CcfDeadAuthorizerWarning

- Surface: ccf_runtime.http_api.app.CcfDeadAuthorizerWarning
- Public surface: true
- Change type: removed
- Before: the WR-05 warning for an authorizer bound with no auth hook, which could therefore never run
- After: absent. Both are required, so a dead authorizer is unrepresentable
- Why: the warning existed to announce a half-wired app. The half-wired app is gone, and a warning this repo never escalated to an error (**0 `filterwarnings`, measured**) was an unread channel announcing it
- Migration: none. Drop any handler; the condition is a construction-time refusal

## ccf_runtime.http_api.app.CcfInsecureDefaultWarning

- Surface: ccf_runtime.http_api.app.CcfInsecureDefaultWarning
- Public surface: true
- Change type: removed
- Before: the `D-IMPL-73` warning that an app was built with no authentication
- After: absent. `create_app` cannot build one
- Why: `SEC-002`. The posture it announced is deleted — nothing has shipped, so the correct change was available (`D-IMPL-293`). A warning is not a control, and this one was never read
- Migration: none for a caller. A deployment binds the five seams

## ccf_runtime.authz.artifact.ScopeEntry

- Surface: ccf_runtime.authz.artifact.ScopeEntry
- Public surface: true
- Change type: reshaped
- Before: `tenant_patterns` + `action_ids`
- After: adds `resource_patterns: tuple[str, ...]`, **required, no default**
- Why: a tenant-and-action axis changes WHO counts as recognized, not WHAT recognition permits. `SEC-002`'s stated harm — any recognized bearer rewriting an underwriting agent's prompt — survives a tenant-only fix as 'any bearer with `config.register` rewriting it'. Required rather than defaulted because a defaulted resource pattern would be a wildcard the SDK chose on the deployment's behalf
- Migration: every registered scope mapping declares `resource_patterns` per scope

## ccf_runtime.authz.protocol.AuthzDecision

- Surface: ccf_runtime.authz.protocol.AuthzDecision
- Public surface: true
- Change type: reshaped
- Before: carried the tenant and action of the decision
- After: adds `resource` and `matched_resource_pattern`
- Why: a decision that cannot say which resource it was about, and which pattern admitted it, is not auditable after the fact
- Migration: none for a caller; a custom authorizer populates both

## ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer

- Surface: ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer
- Public surface: true
- Change type: reshaped
- Before: resolved its scope mapping with `resolve_latest`
- After: takes `scope_mapping_version=` (**required**) and resolves at that exact version; `authorize` takes `resource=`
- Why: last-registered-wins on the authz path means a bearer who can register Control Plane artifacts may be able to re-issue the very policy that authorizes them — a guard whose rules are whatever the last writer wrote. Replay already bans `resolve_latest` for the same reason
- Migration: pin the version at construction

## ccf_runtime.cli.main.main

- Surface: ccf_runtime.cli.main.main
- Public surface: true
- Change type: reshaped
- Before: `main(argv, *, dependencies=None)`
- After: adds `authority=` and `credential=` for the in-process leg; `--local` is suspended
- Why: the gate is TOTAL, so an in-process request is a request and the absence of a network boundary entitles it to nothing. A LOCAL VARIABLE SHADOWING `credential` made the in-process leg send anonymously while type-checking clean — found at the join, visible from neither lane
- Migration: an embedder passes `authority=` and `credential=`; see `350-03`

## ccf_runtime.http_api.routes.artifact.ArtifactPutRequest

- Surface: ccf_runtime.http_api.routes.artifact.ArtifactPutRequest
- Public surface: true
- Change type: reshaped
- Before: carried `tenant_id` from the request body
- After: no `tenant_id`; the tenant comes from the verified grant
- Why: `SEC-004`. Deleting the field makes a caller-supplied tenant unrepresentable rather than merely refused. A path segment may ASSERT equality with the grant's tenant; it may never SUPPLY it
- Migration: stop sending `tenant_id`; `extra=forbid` refuses it

## ccf_runtime.http_api.routes.hitl.build_router

- Surface: ccf_runtime.http_api.routes.hitl.build_router
- Public surface: true
- Change type: reshaped
- Before: took an optional `authorizer=`, the one router that got one
- After: the authorizer reaches every router through the gate; the parameter's special status is gone
- Why: `SEC-002` in one line: authorization was an optional per-router decoration and it decorated exactly one router
- Migration: none — `create_app` wires it

## ccf_runtime.mcp.auth.TokenGrant

- Surface: ccf_runtime.mcp.auth.TokenGrant
- Public surface: true
- Change type: reshaped
- Before: `client_id` + `scopes`; no tenant of any kind
- After: adds `tenants: frozenset[str]`, carried into `AccessToken.claims`
- Why: `SEC-018`. A set rather than a scalar because the artifact store and HITL queue are deployment-wide surfaces one operator credential spans, and the only scalar encoding of that is a wildcard — a fail-open value the SDK would be holding on the deployment's behalf. **Empty means no tenant, never every tenant**, so a forgotten scope fails loudly. Declared `ccf_hash_transparent: True`: empty is exactly what was true of every grant minted before the field existed
- Migration: a token source supplies tenants; the dev `FileTokenSource` mints none, so every door refuses its grant

## Regression evidence

`tests/http_api/test_total_gate.py` — the gate is total, with an executable
NEGATIVE control that builds the app-level-dependency shape and asserts it
misses a malformed body, `/openapi.json` and `/docs`. That control caught its
own defect mid-flight: a function-local Pydantic body model does not resolve
under `from __future__ import annotations`, so it had been silently measuring a
route with no body validation at all.

`test_required_authority.py` measures the 0 `filterwarnings` directives that
justify deleting the warning rather than escalating it.
`test_route_declarations.py`, `test_no_caller_supplied_identity.py`,
`tests/mcp/test_tenant_guard.py` (the 15-surface wrapper), and
`tests/authz` cover the rest.

**Sabotage-verified: 13 severings on the HTTP lane, 13 reds, every anchor
resolving; 11 severings on the MCP lane, 11 reds.** Severed one at a time:
gate-not-installed, boot-refusal-removed, resource-axis-ignored,
untenanted-default, tenant-path-assertion-removed, pin→`resolve_latest`,
`auth` re-defaulted, impostor accepted, unreadable-body falls through,
duplicate query tolerated, catalog tenant unchecked, artifact-put body tenant,
authorizer decision ignored — and on MCP: claim dropped, comparison skipped,
empty-set read as permissive, middleware trusted, ledger blinded, ambient
mutation allowed, `put_artifact` reverted, a tool registered behind the
wrapper, a third untenanted surface, declared-subject defeated, a fifth
uncovered builder.

## Found at the JOIN, which is why the join exists

A **local variable in `ccf_runtime.cli.main.main` shadowed the `credential`
parameter**, so the CLI's in-process leg sent every request anonymously while
type-checking clean. Neither lane could see it: the parameter was added in one
tree and the shadow already lived in another.
