# 374-02 — SEC-017: within-tenant product entitlement declared on the token grant

`D-IMPL-374` (2), ruling (a), with the coordinator's option A on the measurement
that none of the three tools named a product. History: `D-IMPL-129` declined to
decide `list_agents`, `invoke_agent` and `get_replay_record` against
`ProductEntitlementPolicy`; `SEC-018` made them tenant-decided; `D-IMPL-370`
read `SEC-017`'s remedy as including within-tenant entitlement. The exploit
tests are `tests/mcp/test_product_roster.py`.

**Declaring the roster is the deployment's obligation.** A grant with no
`products` is tenant-wide, which is the behavior before this change. The SDK
ships no default roster. In a token file, `"products": null` (or no key) is
tenant-wide and `"products": []` reaches no product.

**Fix round 1 (one rule).** The roster is held on every surface where a
product class is known at the call, after the tenant check and before the
authorizer, so a refused call records no allow. MCP: the Experience door's
`context_product` resource, `get_context`, `get_lineage`, `invoke_agent`,
`get_replay_record` (and `list_agents`, filtered); the egress door's product
resource, product tool and addressed resource. HTTP: `GET /product/...` and
the two `/replay/...` routes. **Surfaces that cannot know a class at the
call, and so are not bound by the roster:** the MCP artifact server, the MCP
HITL server, and the HTTP `/artifact`, `/hitl`, `/agent`, `/skill`,
`/workflow`, `/config`, `/schema` and `/backends` routes.

## ccf_runtime.mcp.auth.TokenGrant

- Surface: ccf_runtime.mcp.auth.TokenGrant
- Public surface: true
- Change type: reshaped
- Before: `client_id`, `scopes`, `tenants`, `authentication`. Within a tenant, every verified principal reached every agent and the replay record on the Experience door.
- After: adds `products: frozenset[str] | None = None`, a roster of Context Product class names (schema names). It is hash-transparent at `None`. `None` (`null` or absent in a token file) declares no roster and stays tenant-wide. A set, including an empty one (`[]`), bounds reach to the classes on it on every surface listed above.
- Why: SEC-017. Within-tenant product entitlement, on the grant that already carries `tenants`.
- Migration: none for a grant that should stay tenant-wide. To restrict a principal, add `"products": [...]` to its grant in the token source.

## ccf_runtime.authz.product_entitlement.TokenGrant

- Surface: ccf_runtime.authz.product_entitlement.TokenGrant
- Public surface: true
- Change type: reshaped
- Before: re-export of `ccf_runtime.mcp.auth.TokenGrant` without `products`.
- After: the same re-export, now with `products`. `verified_grant()` carries the verified token's roster into the grant it returns.
- Why: SEC-017. If `verified_grant()` dropped the roster, every rostered caller would read as tenant-wide.
- Migration: none.

## ccf_runtime.mcp.auth.PRODUCT_CLAIM

- Surface: ccf_runtime.mcp.auth.PRODUCT_CLAIM
- Public surface: true
- Change type: added
- Before: absent.
- After: `"ccf.products"`. This is the `AccessToken.claims` key the verifier writes a declared roster under. It is absent when no roster is declared.
- Why: SEC-017. The roster travels the same way the tenants do (`TENANT_CLAIM`).
- Migration: none. A custom `TokenVerifier` that builds claims itself must write this claim to carry a roster.

## ccf_runtime.mcp.auth.product_claims

- Surface: ccf_runtime.mcp.auth.product_claims
- Public surface: true
- Change type: added
- Before: absent.
- After: renders a grant's roster for `AccessToken.claims`. It returns `{}` when the grant declares none, so "no roster" and "empty roster" stay two states.
- Why: SEC-017.
- Migration: none.

## ccf_runtime.mcp.auth.granted_products

- Surface: ccf_runtime.mcp.auth.granted_products
- Public surface: true
- Change type: added
- Before: absent.
- After: the single read of a verified token's roster. It returns `None` only when the claim is absent. A malformed claim yields the empty roster, never `None`.
- Why: SEC-017. Unparseable is not permissive.
- Migration: none.

## ccf_runtime.mcp.tenancy.ProductOutsideRosterRefused

- Surface: ccf_runtime.mcp.tenancy.ProductOutsideRosterRefused
- Public surface: true
- Change type: added
- Before: absent.
- After: a `TenantGuardViolation` raised by the MCP guard, before the authorizer, when a rostered caller reaches a class outside its roster. The message names the surface and the off-roster classes, each echoed at most 64 characters.
- Why: SEC-017. The refusal is by name.
- Migration: none. A door that catches `TenantGuardViolation` already catches it.

## ccf_runtime.mcp.experience.ExposedAgent

- Surface: ccf_runtime.mcp.experience.ExposedAgent
- Public surface: true
- Change type: reshaped
- Before: no product classes. Nothing on the door's path said which products an agent reaches.
- After: adds `product_classes: frozenset[str] | None = None`, hash-transparent at `None`. It is DERIVED, never declared: only `ccf_runtime.mcp.agent_directory.exposed_agent` sets it, from the definition's context contract (`consumes ∪ emits`). An entry that states `product_classes` any other way is refused at construction by name. With no derived classes, a rostered caller is refused the agent, and the agent is not listed for that caller.
- Why: SEC-017 fix round 1, IMPORTANT 3. A directory that declared a narrower set would widen every roster's reach.
- Migration: build directory entries with `ccf_runtime.mcp.agent_directory.exposed_agent`. Unrostered deployments need nothing.

## ccf_runtime.mcp.experience.build_experience_server

- Surface: ccf_runtime.mcp.experience.build_experience_server
- Public surface: true
- Change type: reshaped
- Before: no `replay_record_product_class`. `list_agents`, `invoke_agent` and `get_replay_record` were tenant-decided only.
- After: adds the optional keyword `replay_record_product_class` (no default value; refused when `get_replay_record` is not allowlisted). For a caller whose grant declares a roster, the guard refuses by name, before the authorizer: the `context_product` resource, `get_context` and `get_lineage` for a class off the roster; `invoke_agent` if the directory is missing, the agent is not exposed, carries no contract, or any of its classes is off the roster; `get_replay_record` unless `replay_record_product_class` is declared and on the roster. `list_agents` lists only agents that `invoke_agent` would dispatch for that caller. A caller with no roster is unchanged.
- Why: SEC-017.
- Migration: none for unrostered deployments. A deployment that issues rostered grants and exposes `get_replay_record` declares `replay_record_product_class`.

## ccf_runtime.mcp.auth.bounded_echo

- Surface: ccf_runtime.mcp.auth.bounded_echo
- Public surface: true
- Change type: added
- Before: absent.
- After: `repr` of at most 64 characters of a value. Every identifier a roster refusal names goes through it. The cap is the one `ccf.skills.wire_arguments` puts on echoed argument keys.
- Why: SEC-017 fix round 1. A refusal's text is bounded by the SDK, never by the caller.
- Migration: none.

## ccf_runtime.mcp.tenancy.ProductReach

- Surface: ccf_runtime.mcp.tenancy.ProductReach
- Public surface: true
- Change type: added
- Before: absent.
- After: which Context Product classes one guarded surface's call reaches. Built only through `TenantGuardedServer.products_from_argument`, `products_declared`, `products_resolved` and `products_unknown`.
- Why: SEC-017 fix round 1. Each surface states its product reading, and the guard holds a declared roster to it before the authorizer.
- Migration: see `ccf_runtime.mcp.tenancy.TenantGuardedServer`.

## ccf_runtime.mcp.tenancy.roster_refusal

- Surface: ccf_runtime.mcp.tenancy.roster_refusal
- Public surface: true
- Change type: added
- Before: absent.
- After: builds the by-name `ProductOutsideRosterRefused` for a surface and a reason.
- Why: SEC-017. One phrasing for every roster refusal.
- Migration: none.

## ccf_runtime.mcp.tenancy.GuardedSurface

- Surface: ccf_runtime.mcp.tenancy.GuardedSurface
- Public surface: true
- Change type: reshaped
- Before: `action`, `subject`, `resource`, `mutating`.
- After: adds `products: ProductReach`.
- Why: SEC-017 fix round 1. The ledger records each surface's product reading.
- Migration: none for a deployment.

## ccf_runtime.mcp.tenancy.TenantGuardedServer

- Surface: ccf_runtime.mcp.tenancy.TenantGuardedServer
- Public surface: true
- Change type: behavior
- Before: `tool()` and `resource()` took `action`, `subject`, `resource`, `mutating`. Nothing held a product roster.
- After: `tool()` and `resource()` also require `products: ProductReach` (keyword-only, no default), from four new static readers. After the tenant floor and before the authorizer, a grant's declared roster is held to it, and a call off the roster is refused with `ProductOutsideRosterRefused`: no allow is recorded and nothing is minted. The grant handed to the authorizer now carries `products`.
- Why: SEC-017 fix round 1, IMPORTANTS 1 and 2.
- Migration: a deployment registering its own surfaces on the guard adds `products=` to each: `door.products_unknown("<why>")` for a surface that knows no product class at the call.

## ccf_runtime.mcp.agent_directory.exposed_agent

- Surface: ccf_runtime.mcp.agent_directory.exposed_agent
- Public surface: true
- Change type: added
- Before: absent. Directories built `ExposedAgent` by hand.
- After: `exposed_agent(definition, *, definition_key, definition_version, skills)` reads name, artifact version, archetypes and the derived `product_classes` off an `AgentDefinition`. It is the only way an entry gets `product_classes`. It lives in its own module because the Experience server source holds no agents-package handle (T-07-20).
- Why: SEC-017 fix round 1, IMPORTANT 3.
- Migration: directories serving rostered principals build their entries with it.

## ccf_runtime.mcp.agent_directory.context_contract_classes

- Surface: ccf_runtime.mcp.agent_directory.context_contract_classes
- Public surface: true
- Change type: added
- Before: absent.
- After: `consumes ∪ emits` of a `ContextContract` as a set of class names. This is the one derivation of what an exposed agent reaches.
- Why: SEC-017 fix round 1, IMPORTANT 3.
- Migration: none.

## ccf_runtime.authz.route_declaration.ProductClassSource

- Surface: ccf_runtime.authz.route_declaration.ProductClassSource
- Public surface: true
- Change type: added
- Before: absent.
- After: `PATH` (a path parameter) or `REPLAY_DECLARED` (the app's declared `replay_record_product_class`).
- Why: SEC-017 fix round 1. This is where an HTTP route's product class comes from.
- Migration: none.

## ccf_runtime.authz.route_declaration.ProductClassBinding

- Surface: ccf_runtime.authz.route_declaration.ProductClassBinding
- Public surface: true
- Change type: added
- Before: absent.
- After: one route's product-class statement, `ProductClassBinding.path(name)` or `ProductClassBinding.replay_declared()`.
- Why: SEC-017 fix round 1.
- Migration: none.

## ccf_runtime.authz.route_declaration.RouteAuthorization

- Surface: ccf_runtime.authz.route_declaration.RouteAuthorization
- Public surface: true
- Change type: reshaped
- Before: `action_id`, `resource`.
- After: adds `products: ProductClassBinding | None = None`. `None` means the route knows no product class at the call.
- Why: SEC-017 fix round 1.
- Migration: none.

## ccf_runtime.authz.route_declaration.authorizes

- Surface: ccf_runtime.authz.route_declaration.authorizes
- Public surface: true
- Change type: reshaped
- Before: `authorizes(action_id, *, resource)`.
- After: `authorizes(action_id, *, resource, products=None)`. The product route declares `ProductClassBinding.path("product_class")`, and the two replay routes declare `ProductClassBinding.replay_declared()`.
- Why: SEC-017 fix round 1.
- Migration: none.

## ccf_runtime.http_api.errors.ERROR_PRODUCT_OUTSIDE_ROSTER

- Surface: ccf_runtime.http_api.errors.ERROR_PRODUCT_OUTSIDE_ROSTER
- Public surface: true
- Change type: added
- Before: absent.
- After: `"product-outside-roster"`. This is the 403 error code the HTTP gate returns when a rostered bearer reaches a class off its roster, or a replay record when no class is declared.
- Why: SEC-017 fix round 1.
- Migration: none.

## ccf_runtime.http_api.gate.AuthorizationGate

- Surface: ccf_runtime.http_api.gate.AuthorizationGate
- Public surface: true
- Change type: reshaped
- Before: `auth`, `authorizer`, `table`. Nothing held a product roster.
- After: adds the keyword `replay_record_product_class: str | None = None`. After the tenant and resource, and before the authorizer, the gate refuses with 403 `product-outside-roster` when a rostered bearer's route-declared class is off its roster. No allow is recorded for the refusal.
- Why: SEC-017 fix round 1, IMPORTANTS 1 and 2.
- Migration: none; `create_app` passes it.

## ccf_runtime.http_api.app.create_app

- Surface: ccf_runtime.http_api.app.create_app
- Public surface: true
- Change type: reshaped
- Before: no replay class.
- After: adds the keyword `replay_record_product_class: str | None = None`, with no SDK default value. Without it, a rostered bearer is refused every replay read.
- Why: SEC-017 fix round 1.
- Migration: a deployment that issues rostered grants and serves replay over HTTP declares it.
