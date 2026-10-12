# 20261011-24 — an opened product records an invalidation boundary through the scoped writer

Dave, 2026-10-11 20:19 MST (the second bounded SDK round): *"Invalidation must use the existing scoped writer
capability."* Finding (round 3, cp-17 `MWE-G11`): an external event (a Reg FD disclosure) sets an invalidation
boundary the deployment must record, and the register is written only under `InvalidationRecordRegister`, which SDK
composition mints per composed tenant (`D-IMPL-354`, `D-IMPL-382`). A paved deployment could not reach it:
`ControlPlaneInvalidationSink(registry=...)` without the minted capability is refused.

What changed: the recipe `ccf.boot.boot` has always used for the graph writer's sink is a public function,
`ccf.boot.compose_invalidation_sink(registry, *, tenant_ids)`, and `boot` calls it. `open_product` — a composition
root — calls it once, at open, over the product's ONE Control Plane, for the product's own tenant only, and exposes
the sink as `OpenedProduct.invalidation_sink`. `record(...)` advances an entity's boundary as a new audited version of
its record; a tenant the product was not opened for is refused `InvalidationUnauthorized` before anything is read or
written. Measured in `tests/products/test_opened_product_invalidation.py`; cp-17 `MWE-G11` now records its boundary
through it.

## ccf.boot.compose_invalidation_sink

- Surface: ccf.boot.compose_invalidation_sink
- Public surface: true
- Change type: added
- Before: absent (the recipe was inline in `boot`)
- After: `compose_invalidation_sink(registry, *, tenant_ids) -> ControlPlaneInvalidationSink`, minting one `InvalidationRecordRegister` per validated tenant from a recorded composition event; `boot` uses it unchanged in behavior
- Why: round 5 item 4; Dave 2026-10-11 20:19 MST
- Migration: none

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: reshaped
- Before: no way for a paved deployment to record an invalidation boundary
- After: the constructor takes `invalidation_sink: ControlPlaneInvalidationSink | None = None` (set by `open_product`), and the `invalidation_sink` property returns it — the scoped writer for this product's tenant only
- Why: round 5 item 4. Red test: `tests/products/test_opened_product_invalidation.py::test_the_authorized_write_lands_as_an_audited_version`; refusal: `::test_an_out_of_scope_write_is_refused_and_nothing_lands`
- Migration: a deployment that built `ControlPlaneInvalidationSink(registry=opened.control_plane)` records through `opened.invalidation_sink`
