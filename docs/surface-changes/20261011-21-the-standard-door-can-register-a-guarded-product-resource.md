# 20261011-21 — the standard door can register the product resource, guarded exactly as the tool

Dave, 2026-10-11 20:19 MST (the second bounded SDK round): *"Registering a product resource must not create an
unguarded retrieval path."* Finding (round 3, cp-04 `CFT-G13`, 3 tests): `ProductDoor.server` passed
`expose_product_resource=False` unconditionally, so a deployment whose ruled gate requires the parameterized product
resource to be registered and enumerable (and to refuse) could not keep it on the standard door — and
`build_egress_server`, which can, requires an authorizer no deployment can compose.

What changed: `open_door` and `open_door_with_verifier` take `expose_product_resource: bool = False`, held on the
`ProductDoor` and passed to `build_egress_server`. Off by default (tool-only, unchanged). When on, the resource
`ccf-product://{tenant}/{product_class}/{version}` is registered on the SAME `TenantGuardedServer` under the same
pinned authorizer, retrieve action and product-class resource as the tool, and its body entitles through the same
`govern_entitlement` step, refusal recorder and perspective resolver — no second, weaker path. Measured in
`tests/mcp/test_door_product_resource.py` over the real MCP door: default registers no resource; with the flag the
template is enumerable; an unentitled principal is refused on the resource exactly as on the tool
(`principal-not-entitled` on both records, no product); a declared principal passes the entitlement to the resolver;
an unknown credential is refused 401 on both surfaces.

## ccf_runtime.mcp.product_door.open_door

- Surface: ccf_runtime.mcp.product_door.open_door
- Public surface: true
- Change type: reshaped
- Before: no way to register the product resource; the door was always tool-only
- After: takes `expose_product_resource: bool = False`; `True` also registers the guarded product resource
- Why: round 5 item 2; Dave 2026-10-11 20:19 MST. Red test: `tests/mcp/test_door_product_resource.py::test_an_unentitled_principal_is_refused_on_the_resource_exactly_as_on_the_tool`
- Migration: none; a door that must keep the resource (cp-04 `CFT-G13`) passes `expose_product_resource=True`

## ccf_runtime.mcp.product_door.open_door_with_verifier

- Surface: ccf_runtime.mcp.product_door.open_door_with_verifier
- Public surface: true
- Change type: reshaped
- Before: no way to register the product resource
- After: takes `expose_product_resource: bool = False`, as `open_door`
- Why: round 5 item 2; Dave 2026-10-11 20:19 MST
- Migration: none

## ccf_runtime.mcp.product_door.ProductDoor

- Surface: ccf_runtime.mcp.product_door.ProductDoor
- Public surface: true
- Change type: behavior
- Before: `server()` built a tool-only door
- After: `server()` registers the product resource beside the tool when the door was opened with `expose_product_resource=True` (a new private field, defaulted, so construction through `open_door` is unchanged)
- Why: round 5 item 2
- Migration: none; construct through `open_door` / `open_door_with_verifier`
