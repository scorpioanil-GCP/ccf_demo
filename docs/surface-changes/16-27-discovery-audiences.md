# 16-27 — `ProductDiscovery` gains a fourth axis, `audiences`

## What did **not** change, stated first

A reader's first question about a change to a shipped §6.3 element is whether
their document moved.

- `domain`, `intents` and `capabilities` are the same three fields at the same
  types.
- `NOT_DISCOVERABLE` is the same positive assertion — *this class is reached
  by direct reference and is not offered for intent-, domain- or
  capability-based lookup* — restated to also state the fourth axis
  explicitly (`audiences=frozenset()`) rather than inheriting it from the
  field default.
- `ProductClassDeclaration` and `RegisteredProductClass` are **unedited** and
  reach the axis through the `ProductDiscovery` type they already name.
  Neither's own recorded shape moves: both are `contract`-kind exports, and a
  `contract`-kind shape is the field-annotation type map
  (`{name: str(field.annotation) ...}`), not a rendering of default values —
  `discovery`'s annotation is `ProductDiscovery` before and after, unchanged.
- `register_product_class`'s **parameter list** is unchanged — the same
  fourteen keyword-only parameters, at the same types, in the same order,
  with the same required/optional split. What moved about it is a rendering
  detail, described below.
- `ccf.projection.plan.Perspective` is untouched, which is the distinction
  `D-IMPL-135` exists to draw: `Perspective` conditions Π's view of the graph
  under a caller's grant at run time; `audiences` advertises an intended
  readership to a registry and conditions nothing.

## ccf.products.contract.ProductDiscovery

- Surface: ccf.products.contract.ProductDiscovery
- Public surface: true
- Change type: reshaped
- Before: three axes — `domain: str`, `intents: frozenset[str]`,
  `capabilities: frozenset[str]`
- After: a fourth axis — `audiences: frozenset[str] = frozenset()` — on the
  same footing as the other three: opaque, deployment-declared, uninterpreted
- Why: `D-IMPL-135` (Dave, 2026-08-14) — a product's intended audience
  (`analyst`, `investment_banker`) maps onto none of the existing three axes;
  calling a role an *intent* or a *capability* corrupts both meanings, and
  the two come apart the moment one role serves several intents
- Migration: none. Every existing `ProductDiscovery` construction, every
  committed `ccf.product-class` document, and `NOT_DISCOVERABLE` itself keep
  working unedited. A deployment that wants an audience declares
  `audiences=frozenset({...})`, or an `audiences:` list on its
  `ccf.product-class` document's `discovery:` block

## ccf.products.contract.register_product_class

- Surface: ccf.products.contract.register_product_class
- Public surface: true
- Change type: reshaped
- Before: `discovery: ProductDiscovery = NOT_DISCOVERABLE`, a keyword-only
  parameter defaulting to the three-axis
  `ProductDiscovery(domain='not-discoverable', intents=frozenset(),
  capabilities=frozenset())`
- After: the same keyword-only parameter, at the same type, with the same
  default name `NOT_DISCOVERABLE` — but the sentinel's own printed
  representation now carries `audiences=frozenset()`, so the function's
  captured shape moves even though no parameter was added, removed,
  retyped, or reordered
- Why: `ProductDiscovery` is a `contract`-kind export, and
  `tests/test_surface_shape_capture.py`'s committed-manifest disturbance
  check (`test_no_committed_plain_class_or_function_shape_is_disturbed`)
  only walks `class`- and `function`-kind entries — so `ProductDiscovery`'s
  own shape move is structurally invisible to that check. Measured rather
  than assumed, per `D-IMPL-138`(c): `pytest -k surface` is the arbiter, and
  it caught the move **here**, not on `ProductDiscovery`.
  `register_product_class` is a `function`-kind entry whose keyword-only
  `discovery` parameter defaults to `NOT_DISCOVERABLE`, and a
  `function`-kind entry's captured shape is `str(inspect.signature(obj))`,
  which renders a default argument's own `repr()` inline — so the fourth
  axis's move surfaces transitively, on the one function that carries the
  sentinel as a default, rather than on `ProductDiscovery` directly
- Migration: none. Every call site that does not pass `discovery=` continues
  to receive `NOT_DISCOVERABLE`, whose *value* is unchanged (still the class
  not offered for lookup on any axis) — only the sentinel's own printed
  representation grew a field

## The `_SHAPE_MOVED_BY_FRAGMENT` question, answered by measurement

`D-IMPL-135` anticipated a `_SHAPE_MOVED_BY_FRAGMENT` claim for
`ccf.products.contract.ProductDiscovery`, reasoning that adding a field moves
the class's shape. `D-IMPL-138`(c) ruled: measure, do not pre-decide.
Measured: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/ -q -k
surface` fails one test —
`test_no_committed_plain_class_or_function_shape_is_disturbed` — and the name
it reports as newly, unclaimably differing is
`ccf.products.contract.register_product_class`, **not**
`ccf.products.contract.ProductDiscovery`. `ProductDiscovery` itself never
appears in that test's `differing` set, because it is `contract`-kind and the
test's own loop skips every entry whose `kind` is not `class` or `function`
(`tests/test_surface_shape_capture.py:506`). The allowance entered into
`_SHAPE_MOVED_BY_FRAGMENT` is therefore keyed to
`ccf.products.contract.register_product_class`, citing this fragment.
