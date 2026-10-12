# 20261011-22 — the shared door adapter: the standard door over a hand-composed product

Dave, 2026-10-11 20:19 MST (the second bounded SDK round), scope item "the shared door adapter". Finding (round 3,
§E repetition threshold): a deployment that composes its product by hand (its own assembler, its own per-question
fabric — not `open_product`) can reach an MCP door after `D-IMPL-353` only through the standard door over a
`ServesProducts` conformer, and cp-07, cp-04 and door-cp-05 each wrote the same ~60-line conformer: a fresh Control
Plane, one throwaway SDK boot of `ccf_config.yaml` (so the declared `product_entitlement:` is registered by the SDK's
composition recipe), the `policy` pin read off it, the SDK's `declared_refusal_recorder`, the declaration, perspective,
door binding and environment document, and `resolve` delegated to the deployment's governed path. Frozen cp-06's door
could not be composed at all (`register_typed` refused `CapabilityBypassError`; `build_egress_server` requires an
authorizer over a scope mapping only SDK composition registers).

What changed: `ccf_runtime.mcp.composed_product.compose_for_door` is that conformer, once. It decides nothing and
registers nothing of its own (the registrations are the SDK boot's and the standard door's; the recorder is the SDK's)
and mints no capability. The caller opens `open_door` / `open_door_with_verifier` over the `ComposedProduct`, which
derives the scope mapping and the pinned authorizer exactly as for a paved product. cp-07, cp-04, door-cp-05 and
cp-06 now use it. Measured in `tests/mcp/test_composed_product_door.py` over the real MCP door: the scope mapping and
pinned authorizer derived as for a paved product; the declared entitlement in force with no door default over it;
each declared principal served under its own role; an undeclared principal refused `principal-not-entitled` with the
deployment's resolver never called; an unknown token refused 401.

## ccf_runtime.mcp.composed_product.compose_for_door

- Surface: ccf_runtime.mcp.composed_product.compose_for_door
- Public surface: true
- Change type: added
- Before: absent — each hand-composed door wrote its own `ServesProducts` conformer
- After: `compose_for_door(config_path, *, boot_connection, environment_root, door, replay_store, replay_record_class, resolver=None, build_resolver=None, default_perspective=None) -> ComposedProduct`; exactly one of `resolver=` / `build_resolver=` (a factory handed the one recorder)
- Why: round 5 item 1; Dave 2026-10-11 20:19 MST. Red test: `tests/mcp/test_composed_product_door.py::test_each_declared_principal_is_served_under_its_own_permissions`
- Migration: a hand-composed door replaces its conformer class with this call and opens the standard door over the result

## ccf_runtime.mcp.composed_product.ComposedProduct

- Surface: ccf_runtime.mcp.composed_product.ComposedProduct
- Public surface: true
- Change type: added
- Before: absent
- After: a frozen dataclass conforming to `ServesProducts` (`tenant_id`, `declaration`, `default_perspective`, `control_plane`, `refusal_recorder`, `door`, `environment`, `resolve`) plus `policy_bundle_pin` and `replay_store`; `resolve` is a field holding the deployment's governed path, which the standard door calls after its authorizer and entitlement step; built only by `compose_for_door`
- Why: round 5 item 1
- Migration: none
