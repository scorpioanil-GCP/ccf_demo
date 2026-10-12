# 20261011-02 — a deployment declares several principals' entitlements; the standard door composes over them

Dave, 2026-10-11 16:23 MST, ruling 4 (the bounded SDK round). Finding G4-F-04 (also cp-07's door, SEC353-G-05):
since `D-IMPL-353` a deployment cannot register its own `ProductEntitlementPolicy` (the registry takes a capability
only SDK composition code mints), and the standard door registers a ONE-principal policy, so a door serving several
principals had no supported path. cp-15..24's `server/serve.py::entitle` registered one by hand and is now refused
`CapabilityBypassError`.

The supported path: the deployment DECLARES the policy as Control Plane data in `ccf_config.yaml`:

```yaml
product_entitlement:
  tenant_id: <the deployment's tenant_id — held equal>
  policy_version: "1.0.0"
  principals:
    PRIN-A: {permitted_schema_names: [<this product's class>], permitted_roles: [<A's role>]}
    PRIN-B: {permitted_schema_names: [<this product's class>], permitted_roles: [<B's role>]}
```

`open_product` registers it at open under the composition recipe (an audited `composition` event and a
`CompositionRegister` minted for exactly the tenant's entitlement key), every boot re-registers the same content, and
`open_door` / `open_door_with_verifier` register their one-principal default only where the key holds nothing. Refused
by name at open: a body whose `tenant_id` is not the deployment's; a grant naming a class this deployment does not
serve. Each principal's credential, scope and role resolution stay the deployment's verifier and perspective resolver,
as before; the scope every credential carries is the door's `required_scope`. Measured in
`tests/mcp/test_door_declared_principals.py` over the real MCP door: each declared principal served under its own
role; a declared principal asking under a role it was not granted refused (`product-role-ungranted`); a credential
whose principal is not declared refused (`principal-not-entitled`); an unknown credential refused at the verifier;
with no declaration only the door's default principal is entitled.

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: reshaped
- Before: no `product_entitlement` section; a config naming one was refused as an unrecognized section
- After: an optional, hash-transparent `product_entitlement: Mapping[str, Any] | None` section, derived as a bare typed `ccf.product-entitlement-policy` entry at `product_entitlement_key(tenant_id)`; a config that does not name it hashes and derives exactly as before
- Why: G4-F-04; Dave 2026-10-11 16:23 MST ruling 4. Red test: `tests/mcp/test_door_declared_principals.py::test_each_declared_principal_is_served_under_its_own_role`
- Migration: a deployment whose code registered a `ProductEntitlementPolicy` by hand moves the policy body into `product_entitlement:` and deletes the registration

## ccf.deployment.classes.SDK_ARTIFACT_CLASSES

- Surface: ccf.deployment.classes.SDK_ARTIFACT_CLASSES
- Public surface: true
- Change type: behavior
- Before: `ccf.product-entitlement-policy` was not manifest-addressable ("entitles a principal registers that policy programmatically")
- After: it is manifest-addressable (typed registration), so the `product_entitlement:` section and a manifest entry can name it
- Why: G4-F-04; programmatic registration is no longer available to a deployment (D-IMPL-353)
- Migration: none

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: registered nothing about entitlement at open
- After: registers the declared `product_entitlement:` policy at open, under an audited composition decision, after refusing a grant that names a class this deployment does not serve
- Why: G4-F-04; the door decides entitlement before any question boots. Red test: `tests/mcp/test_door_declared_principals.py::test_a_declaration_granting_a_class_this_deployment_does_not_serve_is_refused_at_open`
- Migration: none

## ccf_runtime.mcp.product_door.open_door

- Surface: ccf_runtime.mcp.product_door.open_door
- Public surface: true
- Change type: behavior
- Before: always registered its one-principal entitlement policy, replacing nothing but superseding any earlier version as latest
- After: registers its one-principal default only when the tenant's entitlement key holds no version; a declared policy is composed over, never replaced. `open_door_with_verifier` shares the composition
- Why: G4-F-04. Severing proof: forcing the default registration reddens `::test_each_declared_principal_is_served_under_its_own_role` and `::test_a_declared_principal_asking_under_a_role_it_was_not_granted_is_refused`
- Migration: none
