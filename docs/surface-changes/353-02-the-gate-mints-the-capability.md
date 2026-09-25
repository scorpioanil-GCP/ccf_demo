# 353-02 — the gate mints the capability; one tenant reader, and the gate does not pick

D-IMPL-353 §1.1, §1.3, §1.4 and §3, Lane CAP-GATE. The HTTP
`AuthorizationGate` no longer only *decides*: after the authorizer returns
*allowed* it **mints** an `Authorized` capability for exactly that decision
(`src/ccf/authz/capability.py::mint`) and parks it on
`request.state.authorized`; every handler obtains it through
`runtime/ccf_runtime/http_api/grants.py::authorized_from_request` and acts
under `authorized.tenant` / `authorized.principal`. On every refusal nothing
is minted.

## What did NOT change, stated first

- **Authentication** is untouched: `HttpAuthProtocol`, `BearerTokenAuth` and
  the token sources are as `350-05` left them.
- **The route declarations** (`@authorizes`, `ResourceBinding`) and the
  action-id vocabulary are unchanged. Every route still declares its action
  and its resource at its own definition.
- **`create_app`'s signature** is unchanged: the same five required seams,
  no default on any of them. What changed is one more refusal at
  construction (`GovernedWiringError`, below).
- **The OpenAPI document is byte-identical** — body parameters were renamed
  from `request` to `body` where a live `Request` was added, and a single
  un-embedded body parameter's name does not reach the document
  (`tests/http_api/test_openapi.py` holds the committed `openapi.json` equal
  to what `create_app()` emits).
- **`tenant_from_request` survives under its old name and shape** — it is now
  `authorized_from_request(request).tenant` and reads no grant — for the one
  caller another lane owns (`runtime/ccf_runtime/http_api/routes/hitl.py`);
  it is deleted at the join once that door migrates.

## THE POSTURE CHANGES, BECAUSE THEY SURPRISE PEOPLE

- **A credential spanning several tenants is refused on a route that names
  none.** `TokenGrant.tenants` is a set; a decision is about one tenant. The
  gate selects the one the route's path names (it must be a member), or the
  only one the grant holds. Several held and none named is a `403
  ambiguous-tenant`: **the gate does not pick.** An operator credential
  reaches tenant-less routes by presenting a credential scoped to one tenant.
- **A path segment naming a tenant the grant does not hold is the constant
  denial** (`request-unauthorized`), not `ambiguous-tenant`: which tenants a
  credential is near is not a caller's to learn from a refusal.
- **An allow the gate cannot mint from is a `503 decision-unmintable`**: a
  deployment's own authorizer returning *allowed* with no `decision_id`, or
  for a tenant, action or resource other than the one asked. The SDK's
  authorizer can never produce this.
- **`TenantedTokenGrant` is gone from the test fixtures** — the subclass that
  carried a `tenant` scalar no token source ever minted, and the reason the
  whole `tests/http_api` suite stayed green while the door refused every real
  credential (P1). Every fixture now mints the base `TokenGrant` through the
  real `StaticTokenSource` / `FileTokenSource`, and
  `tests/http_api/test_capability_gate.py` opens the door with a real token
  file.
- **A deny on the audit log says what it denied**: the resource, the resource
  pattern that matched, and the axis that refused. The allow's content
  address is the `decision_id` every capability carries.
  `src/ccf/controlplane/audit.py::AuditLog` — `append` — accepts the three
  new keywords (`authz_resource`, `authz_matched_resource_pattern`,
  `authz_failing_axis`, all default `None`); additive, so every pre-existing
  call appends exactly what it appended. The manifest does not capture
  method keywords, so this is recorded here rather than as an entry.

## ccf_runtime.authz.tenancy.tenants_of_grant

- Surface: ccf_runtime.authz.tenancy.tenants_of_grant
- Public surface: true
- Change type: added
- Before: absent; `tenant_of_grant` read a `.tenant` scalar the shipped contract does not carry
- After: `tenants_of_grant(grant: object) -> frozenset[str]` — the ONE reader, over the ONE field `TokenGrant.tenants`; refuses a non-`TokenGrant`, an empty set, and an empty-string member (whole)
- Why: D-IMPL-353 §1.3 / `SEC-002`: one reader over one field means no fixture can mint a shape production cannot (P1)
- Migration: a door or wrapper that read `tenant_of_grant(grant)` reads `tenants_of_grant(grant)` and selects with `acting_tenant`; credentials must carry `tenants`

## ccf_runtime.authz.tenancy.acting_tenant

- Surface: ccf_runtime.authz.tenancy.acting_tenant
- Public surface: true
- Change type: added
- Before: absent; the tenant was a scalar and nothing selected
- After: `acting_tenant(*, tenants: frozenset[str], named: str | None) -> str` — a named member, or the only member, else `AmbiguousTenantRefused`; a named non-member is `TenantNotGrantedRefused`; an empty set is `UntenantedGrantRefused`
- Why: D-IMPL-353 §1.3: a decision is about one tenant, selected from the grant's set; the gate does not pick
- Migration: the MCP `TenantGuardedServer` wrapper selects through the same function so both mint sites share one rule

## ccf_runtime.authz.tenancy.AmbiguousTenantRefused

- Surface: ccf_runtime.authz.tenancy.AmbiguousTenantRefused
- Public surface: true
- Change type: added
- Before: absent
- After: `RuntimeError` raised by `acting_tenant` when the grant spans several tenants and the route named none; rendered by the gate as `403 ambiguous-tenant`
- Why: D-IMPL-353 §1.3 — refusing is the alternative to the gate writing half of the decision itself
- Migration: none for a single-tenant credential; a multi-tenant credential addresses a route that names the tenant, or is re-scoped

## ccf_runtime.authz.tenancy.TenantNotGrantedRefused

- Surface: ccf_runtime.authz.tenancy.TenantNotGrantedRefused
- Public surface: true
- Change type: added
- Before: absent; the gate compared the path segment to the scalar inline
- After: `RuntimeError` raised by `acting_tenant` when the route names a tenant the grant does not hold; rendered by the gate as the constant `request-unauthorized` denial
- Why: a path segment may agree with the credential and may never supply a tenant it lacks (`SEC-002`)
- Migration: none

## ccf_runtime.authz.tenancy.tenant_of_grant

- Surface: ccf_runtime.authz.tenancy.tenant_of_grant
- Public surface: true
- Change type: removed
- Before: `tenant_of_grant(grant: object) -> str`, reading a `.tenant` attribute
- After: deleted; `tenants_of_grant` + `acting_tenant` replace it
- Why: the shipped `TokenGrant` has no `.tenant` — the reader was satisfiable only by a test-only subclass, so every real credential was refused `untenanted-grant` (P1, D-IMPL-353 §2)
- Migration: `tenant = acting_tenant(tenants=tenants_of_grant(grant), named=<path tenant or None>)`

## ccf_runtime.authz.tenancy.TenantedGrant

- Surface: ccf_runtime.authz.tenancy.TenantedGrant
- Public surface: true
- Change type: removed
- Before: a `runtime_checkable` Protocol with a single `tenant: str` attribute
- After: deleted; there is no Protocol a subclass can satisfy by adding a scalar
- Why: the Protocol was the shape the P1 fixture satisfied; the only credential shape is `TokenGrant` with its `tenants` set
- Migration: type against `TokenGrant`

## ccf_runtime.http_api.grants.authorized_from_request

- Surface: ccf_runtime.http_api.grants.authorized_from_request
- Public surface: true
- Change type: added
- Before: absent; handlers read a grant and derived a tenant from it
- After: `authorized_from_request(request) -> Authorized[ActionKind]` and `authorized_from_request(request, *, kind=K) -> Authorized[K]` — verifies the mint and every field against the minted tuple, holds the kind to the route's declared action (read from the resolved endpoint) and to `kind=`; refuses `403 no-capability` for absent, fabricated, retargeted or wrong-action objects
- Why: D-IMPL-353 §1.4 — a handler holds the capability the gate minted or it holds nothing
- Migration: every route body calls it and passes `authorized` to the handles it calls; `authorized.tenant` and `authorized.principal` replace every tenant and actor derivation

## ccf_runtime.http_api.gate.AuthorizationGate

- Surface: ccf_runtime.http_api.gate.AuthorizationGate
- Public surface: true
- Change type: reshaped
- Before: decided `(grant, tenant, action, resource)` with `tenant := grant.tenant`, held a path tenant equal to it, and stashed `token_grant`
- After: reads `tenants_of_grant`, selects with `acting_tenant` (403 `ambiguous-tenant` / constant denial), decides once, refuses `503 decision-unmintable` unless the allow carries a `decision_id` and answers the question asked, then mints `Authorized[kind_for_action(action_id)]` and stashes it as `request.state.authorized` beside `token_grant`
- Why: D-IMPL-353 §1.1 (the gate is one of two mint sites) and §1.3 (the tenant is selected, never picked)
- Migration: deployments whose credentials span tenants scope them or address tenant-naming routes; custom authorizers must return `decision_id` and decide about the tuple asked

## ccf_runtime.http_api.gate.build_route_table

- Surface: ccf_runtime.http_api.gate.build_route_table
- Public surface: true
- Change type: reshaped
- Before: refused a route with no declaration or a path-sourced resource its template lacks
- After: additionally refuses a route whose declared action id no capability kind exists for (`src/ccf/authz/capability.py::kind_for_action`), naming it in `UndeclaredRouteError`
- Why: the gate mints for the route's action after an allow; an action with no kind is an allow the gate could not mint from, decided at boot rather than on the first allowed request
- Migration: a new route's action id must be one `kind_for_action` resolves

## ccf_runtime.http_api.app.GovernedWiringError

- Surface: ccf_runtime.http_api.app.GovernedWiringError
- Public surface: true
- Change type: added
- Before: absent; a recorder filing a governed class through a store that governs it, with no minting authority, built cleanly and failed at its first denial
- After: `ValueError` raised by `create_app` at construction in that configuration
- Why: D-IMPL-353 §3 / `D-IMPL-256` (2): a door that cannot record what it decides is not a valid governed door, and that is decided at boot, not when a denial happens
- Migration: hand the recorder `GovernedWriteHandle(store)` or do not declare the class governed on the store the doors serve from; the second direction (a store declaring a write kind no door can mint) lands with the per-class write-kind mapping

## ccf_runtime.http_api.errors.ERROR_AMBIGUOUS_TENANT

- Surface: ccf_runtime.http_api.errors.ERROR_AMBIGUOUS_TENANT
- Public surface: true
- Change type: added
- Before: absent
- After: `"ambiguous-tenant"` — 403 when the grant spans several tenants and the route names none
- Why: its own code on the `ERROR_UNTENANTED_GRANT` reasoning: the answer is a function of the credential and the template, which a caller cannot vary, so distinguishing it discloses nothing and an operator reads the cause
- Migration: none

## ccf_runtime.http_api.errors.ERROR_NO_CAPABILITY

- Surface: ccf_runtime.http_api.errors.ERROR_NO_CAPABILITY
- Public surface: true
- Change type: added
- Before: absent
- After: `"no-capability"` — 403 from `authorized_from_request` for an absent, fabricated, retargeted or wrong-action object; unreachable behind the gate
- Why: one code for all four — there is nothing useful for a caller to learn from which
- Migration: none

## ccf_runtime.http_api.errors.ERROR_DECISION_UNMINTABLE

- Surface: ccf_runtime.http_api.errors.ERROR_DECISION_UNMINTABLE
- Public surface: true
- Change type: added
- Before: absent
- After: `"decision-unmintable"` — 503 when the bound authorizer's allow carries no `decision_id` or answers a different question
- Why: a deployment fault, not the caller's; the gate refuses rather than minting an authority traceable to nothing
- Migration: a custom `TenantAuthorizerProtocol` implementation populates `decision_id` and decides about the tuple it was asked

## ccf.controlplane.audit.AuthzDecisionAuditEvent

- Surface: ccf.controlplane.audit.AuthzDecisionAuditEvent
- Public surface: true
- Change type: reshaped
- Before: `authz_action_id`, `authz_matched_pattern`
- After: adds `authz_resource: str | None`, `authz_matched_resource_pattern: str | None`, `authz_failing_axis: AuthzFailingAxis | None`, all hash-transparent at the sentinel (`D-IMPL-243`), so events appended before the fields existed and events appended now with them at `None` canonicalize identically
- Why: D-IMPL-353 §3 — every refusal says what it refused; the A2 byte-pin on plain events is untouched
- Migration: none for readers; an examiner filtering denies reads `authz_failing_axis`

## ccf.controlplane.audit.AuthzFailingAxis

- Surface: ccf.controlplane.audit.AuthzFailingAxis
- Public surface: true
- Change type: added
- Before: absent
- After: `Literal["tenant", "action", "resource", "mapping"]` — the deepest axis a held scope entry reached before failing, or `mapping` when no scope mapping decided (nothing at the pinned version, or a near-miss artifact)
- Why: three states, not two — refused on an axis, refused because nothing could decide, and (on an allow) no axis refused; recording a mapping-less deny as an axis would name a rule that never ran
- Migration: none

## ccf.authz.decision.AuthzDecision

- Surface: ccf.authz.decision.AuthzDecision
- Public surface: true
- Change type: added
- Before: `ccf_runtime.authz.protocol.AuthzDecision` with `allowed`, `matched_scope_pattern`, `matched_resource_pattern`, `artifact_version`, `action_id`, `tenant`, `resource` — the relocation itself is `353-01`'s
- After: the relocated contract with one more field, this lane's: `decision_id: str | None = None` (hash-transparent at the sentinel) — the content address of the `authz_decision` event recording the decision; the SDK's authorizer always supplies it and the gate mints no capability from an allow without one
- Why: D-IMPL-353 §1.5(a): a capability is evidence of exactly one audit record
- Migration: a custom authorizer returns `decision_id`; a decision constructed with none is refused by the gate as `decision-unmintable`

## ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer

- Surface: ccf_runtime.authz.protocol.ControlPlaneTenantAuthorizer
- Public surface: true
- Change type: reshaped
- Before: `authorize(...)` returned a decision with no record id and audited tenant pattern and action only
- After: `authorize(...)` returns `AuthzDecision` with `decision_id = content_hash(event)`; the appended event carries the resource, the matched resource pattern and, on a deny, the failing axis (`action` when no held entry names the action, `tenant`, `resource`, or `mapping` when nothing resolved at the pin)
- Why: D-IMPL-353 §1.5(a) and §3
- Migration: none; the constructor is unchanged
