# 374-02 — SEC-017: within-tenant product entitlement declared on the token grant

`D-IMPL-374` (2), ruling (a), with the coordinator's option A on the measurement
that none of the three tools named a product. History: `D-IMPL-129` declined to
decide `list_agents`, `invoke_agent` and `get_replay_record` against
`ProductEntitlementPolicy`; `SEC-018` made them tenant-decided; `D-IMPL-370`
read `SEC-017`'s remedy as including within-tenant entitlement. The exploit
tests are `tests/mcp/test_product_roster.py`.

**Declaring the roster is the deployment's obligation.** A grant with no
`products` is tenant-wide, which is the behavior before this change. The SDK
ships no default roster.

## ccf_runtime.mcp.auth.TokenGrant

- Surface: ccf_runtime.mcp.auth.TokenGrant
- Public surface: true
- Change type: reshaped
- Before: `client_id`, `scopes`, `tenants`, `authentication`. Within a tenant, every verified principal reached every agent and the replay record on the Experience door.
- After: adds `products: frozenset[str] | None = None`, a roster of Context Product class names (schema names). It is hash-transparent at `None`. `None` declares no roster and stays tenant-wide. A set, including an empty one, bounds reach on the Experience door's agent and replay tools to the classes on it.
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
- After: a `TenantGuardViolation` raised by the Experience door's agent and replay tools when a rostered caller reaches a class outside its roster. The message names the tool and the off-roster classes.
- Why: SEC-017. The refusal is by name.
- Migration: none. A door that catches `TenantGuardViolation` already catches it.

## ccf_runtime.mcp.experience.ExposedAgent

- Surface: ccf_runtime.mcp.experience.ExposedAgent
- Public surface: true
- Change type: reshaped
- Before: no product classes. Nothing on the door's path said which products an agent reaches.
- After: adds `product_classes: frozenset[str] | None = None`, the agent's context contract `consumes ∪ emits`, read by the deployment's directory. `None` means undeclared. A rostered caller is refused such an agent, and the agent is not listed for that caller.
- Why: SEC-017. This is what a roster is compared to on `invoke_agent` and `list_agents`.
- Migration: a deployment that issues rostered grants must have its `AgentDirectoryProtocol` fill `product_classes` from each exposed definition's `context_contract`. Otherwise rostered callers reach no agent. Unrostered deployments need nothing.

## ccf_runtime.mcp.experience.build_experience_server

- Surface: ccf_runtime.mcp.experience.build_experience_server
- Public surface: true
- Change type: reshaped
- Before: no `replay_record_product_class`. `list_agents`, `invoke_agent` and `get_replay_record` were tenant-decided only.
- After: adds the optional keyword `replay_record_product_class` (no default value; refused when `get_replay_record` is not allowlisted). For a caller whose grant declares a roster: `invoke_agent` looks the agent up in the directory and refuses by name if the directory is missing, the agent is not exposed, or any of its classes is off the roster. `list_agents` lists only agents that `invoke_agent` would dispatch for that caller. `get_replay_record` refuses unless `replay_record_product_class` is declared and on the roster. A caller with no roster is unchanged.
- Why: SEC-017.
- Migration: none for unrostered deployments. A deployment that issues rostered grants and exposes `get_replay_record` declares `replay_record_product_class`.
