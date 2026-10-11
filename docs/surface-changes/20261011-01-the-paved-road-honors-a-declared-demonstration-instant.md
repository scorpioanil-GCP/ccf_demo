# 20261011-01 — the paved road honors a declared demonstration serve instant when the caller composes no clock

Dave, 2026-10-11 16:23 MST, ruling 4 (the bounded SDK round) and the clock fix ruling 1 depends on. Finding
G1-SDK-01: `open_product` defaulted its clock to `product.py`'s own `_utc_now`, and `compose_serve_clock` tests
"the caller composed no clock" by identity against the resolver's `_utc_now`. The two were different function
objects, so every paved deployment that declared `demonstration_serve_instant:` and composed no clock was refused
with `DemonstrationServeInstantConflict` ("this composition supplies its own clock"), which was not true.

What changed:

- `open_product` takes the startup snapshot at open: when the deployment's `ccf_config.yaml` declares
  `demonstration_serve_instant:` and the caller passes no `clock=`, every question's resolver is handed the SDK's
  own default clock, so `compose_serve_clock` serves at the declaration with all of its checks. The ingress
  temporal write guard on the paved road judges envelopes at that same declared instant (one instant per
  question).
- `compose_serve_clock`'s exact-type store check (decision 4 (a)) looks through the SDK's own
  `ErasureConsultingStore` wrapper, matched by exact type, to the store it decorates. The paved road hands the
  resolver its store already wrapped, so without this the SDK's own file store was refused on the paved road.

Kept, measured in `tests/products/test_paved_road_demonstration_instant.py`: a caller-composed clock beside a
declaration is refused (`DemonstrationServeInstantConflict`); several declarations are refused
(`DemonstrationServeInstantMisplaced`); a store that is not the SDK's own is refused inside the wrapper
(`artifact-store-not-development`); a question outside the window around the declared instant is refused
`asked-at-outside-temporal-bound`; without the declaration the dated question is refused on the real clock; a
declaration registered after open is refused at the next question
(`tests/client/test_demonstration_serve_instant.py::test_the_paved_road_refuses_a_declaration_registered_after_open_at_the_next_question`).
The instant remains a development instant: refused outside the SDK's own development backends, pinned in
dimension 2 of every record.

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: same signature. A deployment whose `ccf_config.yaml` declared `demonstration_serve_instant:` was refused with `DemonstrationServeInstantConflict` at its first question, whether or not the caller passed `clock=`
- After: same signature. With no `clock=`, the declaration present at open is honored: the resolver serves at the declared instant, the ingress guard judges at it, and every record pins it. With `clock=` beside a declaration, unchanged (refused by name)
- Why: G1-SDK-01; Dave 2026-10-11 16:23 MST ruling 4. Red test: `tests/products/test_paved_road_demonstration_instant.py::test_a_paved_deployment_with_no_composed_clock_serves_at_its_declared_instant`
- Migration: a paved deployment with a dated demonstration question adds `demonstration_serve_instant: {serve_instant: "<ISO instant>"}` and a `temporal_boundary:` to its `ccf_config.yaml`, passes no `clock=` to `open_product`, and runs on the SDK's SQLite or in-memory adapter with the default artifact store

## ccf.products.demonstration_clock.compose_serve_clock

- Surface: ccf.products.demonstration_clock.compose_serve_clock
- Public surface: true
- Change type: behavior
- Before: same signature. The store check was `type(artifact_store) is FileArtifactStore` on the store as handed in, so the SDK's own file store wrapped in the SDK's own `ErasureConsultingStore` was refused `artifact-store-not-development`
- After: same signature. The SDK's own `ErasureConsultingStore` (exact type, not a subclass) is looked through to the store it decorates, and the exact-type test is made there. A subclass of `FileArtifactStore` inside the wrapper is still refused
- Why: G1-SDK-01; the paved road's store is always wrapped. Red test: `tests/products/test_paved_road_demonstration_instant.py::test_a_paved_deployment_with_no_composed_clock_serves_at_its_declared_instant`; the refusal kept: `::test_a_store_that_is_not_the_sdks_own_is_still_refused`
- Migration: none

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: reshaped
- Before: the constructor took no statement of the demonstration snapshot
- After: the constructor takes `honors_demonstration_serve_instant: bool = False`, which `open_product` sets from its startup snapshot (the document declares an instant and no `clock=` was passed). It selects the admission clock handed to the resolver and the ingress guard's clock; it grants nothing — `compose_serve_clock` still makes every check
- Why: G1-SDK-01; Dave 2026-10-11 16:23 MST ruling 4
- Migration: none; construct through `open_product`
