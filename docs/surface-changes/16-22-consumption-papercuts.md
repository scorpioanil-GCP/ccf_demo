# 16-22 — the four consumption papercuts `D-IMPL-126` ruled

## What this fragment is, and why it exists before the examples do

`D-IMPL-126` (Dave, 2026-08-13) ruled four defects fixed **before** Phase 16's
Hello World examples are written, not after. The reason is not sequencing
convenience: an example written against an unfixed papercut teaches the
workaround, and the workaround then ships as documentation.

None of the four is in the line count the Phase 16 adoption spike measured —
consuming a Context Product is 9 lines over MCP and 10 over HTTP with zero
`ccf` imports, and producing one is 91 lines of developer Python, and those
figures are unchanged by this plan. The four are in the **error messages and
missing affordances** an adopter hits on the way to those lines, and each one
sent a reader into SDK source to recover.

**This fragment is also the first `16-*` fragment either surface gate can
see.** See the last prose section.

## The `ETag` ruling — recorded because it was a real choice

`X-CCF-Content-Address` was taken. `ETag` was rejected and **both** were not
shipped. The reasoning lives in `canonical_response`'s own docstring, where a
reader who reaches for `ETag` will find it; in brief:

1. **A CCF content address is an identity, not a cache validator.** It is the
   `D-IMPL-26` primitive the ArtifactStore resolves and replay pins against.
   RFC 9110 permits an intermediary to weaken a strong `ETag` to `W/"..."` or
   rewrite it across a content-coding transformation. An identity a proxy may
   legally alter is not an identity.
2. **`ETag` advertises cacheability on an entitlement-scoped body.** These
   responses are per-principal and per-perspective — `entitled_perspective`
   decides before the resolver runs. An `ETag` invites an intermediary to hold
   and re-serve a governed product; an `X-CCF-*` header carries no HTTP caching
   semantics and issues no such invitation. That is *also* why no
   `Cache-Control` change is owed: the hazard is avoided by the header choice
   rather than papered over with a second header.
3. **`ETag` is per-representation; the address is per-object.** The moment this
   door gains content negotiation or compression the two must diverge, and an
   `ETag` set to the content address would be lying.
4. Implementing `ETag` honestly means `If-None-Match` and a 304 path — real
   behaviour on a shipped door, outside what `D-IMPL-126` ruled.

Shipping both would be two headers carrying the same hex string, one of which a
proxy may rewrite: a guarantee that fails silently.

**The MCP doors are deliberately untouched.** They have no header channel and
their bodies *are* the product, so carrying the address inside the body would
change the body and therefore change the address it claims. The asymmetry is a
property of the transports, not an oversight.

## `ProductRequestContract.from_declared` — a new public method the manifest cannot see

`ProductRequestContract` gains a `from_declared(artifact)` classmethod: one
named call from the `DeclaredArtifact` a manifest returns to the typed
contract, replacing the four-field hand-build at
`examples/s1-01-hello-context-product/deployment.py::read`. It reads the
document's own `semver` lane plus the three declaration keys, and refuses a
declaration missing any of them by naming **all** the missing keys in one
message — an adopter fixing three keys one `KeyError` at a time is the papercut
restated.

**No entry is filed for it below, and that is a limitation of the manifest
rather than a gap in this record.** `tools/dump_surface.py` captures a class's
`__init__`/`__call__` signature and its Pydantic field set; it reaches no
ordinary method. `D-IMPL-122` declined to widen that on a measured cost — 65
new `reshaped` diff lines against 11 — and Dave took the smaller fix knowingly.
The consequence, stated here rather than left for a later gate to cite this
manifest for more than it proves: **the generated manifest is not evidence of
surface stability for a class's method set.** Adding `from_declared` produces
no diff line. This is the same honesty
`15.6-13-source-refresh-window.md` practised about its two withdrawn entries.

Two shapes were offered and neither was taken; both are recorded in the
method's own docstring so a later reader does not re-propose them as
oversights. A `*.request-contract` **suffix branch** in the manifest loader
would have the SDK claim a name across every adopter namespace, where
`D-IMPL-84` draws the line at exactly one prefix (`ccf.`), and it would be a
silent behavioural break with no version lane — a committed manifest naming
`acme.request-contract` resolves to a `DeclaredArtifact` today and would
resolve to the typed class tomorrow, changing what registers, what pins, and
what enters replay dimension 2. Registering `PRODUCT_REQUEST_CONTRACT` in
`SDK_VERSIONED_ARTIFACT_CLASSES` remains **available to a later ruling** for
the reasons already committed at that constant's definition.

`from_declared` is a **constructor, not a validator**. It performs no pin check
and claims none: `refuse_request_contract_pin` and `register_product_class`
remain the comparisons that catch a contract pinned onto the wrong class or
lane, exactly as they were for the hand-build it replaces.

## `hasattr(ServableProduct, "model_construct")` changes what it returns

Before this plan it returned `False` by accident — the attribute simply did not
exist. It still returns `False`, now on purpose, and the route it takes there is
worth recording because a naive version of this fix would have broken it.

`ServableProduct` now refuses every spelling in the new `PYDANTIC_MODEL_FORMS`
frozenset on **both** attribute channels — a metaclass `__getattr__` for
`ServableProduct.model_construct(...)` and a `__getattr__` on the class itself
for `servable.model_copy()`. Two channels because a metaclass covers only the
first, and `model_copy`, `model_dump` and `parse_obj` are *instance* methods in
pydantic: they are what a reader holding a returned object reaches for.

`GateBypassError` subclasses `TypeError` and nothing else. A refusal deriving
from it alone would make `hasattr(...)` **raise** instead of returning `False`,
and `getattr(x, "model_copy", None)` raise instead of defaulting — a hazard
created by this fix. `ServableProductNotAModel` therefore derives from **both**
`GateBypassError` and `AttributeError`, so a duck-type probe degrades while
`except GateBypassError` still catches and the message is unchanged.

Any name outside the frozenset still raises a plain `AttributeError` on both
channels. The scoping is the point: a refusal that swallowed a typo would
replace one confusing error with a more confident one.

## `ApiDependencies` moves its wiring check from boot to first call

**This is a posture change and it is not free.** Before, a deployment that
forgot a handle failed at *boot* with a `TypeError` from the frozen dataclass;
after, five of the eight handles default to `None` and the failure moves to
*first call* as a typed 503 carrying `ERROR_ROUTE_HANDLE_ABSENT`.

What keeps the diagnostic from being lost is that the 503 names the exact
absent field and the exact argument to supply. What an adopter should do about
it is below.

**Migration.** Nothing is required: `kw_only=True` means no field reordering,
and all seventeen shipped construction sites pass eight keyword arguments and
are byte-for-byte unaffected. **But a deployment that was relying on the boot
`TypeError` as its wiring check no longer has one** — assert your bundle
explicitly at your composition root instead, or drive one route from each family
you intend to expose in a smoke test. If you wire all eight, nothing about your
deployment changes.

## The surface-change machinery is no longer anchored to Phase 15

Recorded so a later phase does not rediscover this the hard way.

`tests/test_surface_drift.py:_fragment_text()` and
`tools/assemble_surface_changes.py:fragment_paths()` both globbed `15*-*.md`,
and `_PLAN_NUMBER` was anchored `^15`. Sixty of the sixty-one files in
`docs/surface-changes/` begin with `15`. **Every `16-*` fragment was therefore
invisible to both gates**: a Phase 16 plan could file one and still fail
`test_surface_drift` as an *undocumented* change, because the fragment's text
was never read, and a plan that filed nothing looked identical.

Both gates were green at that HEAD **while blind**, which is why the fix is not
asserted by a green build. `test_a_phase_16_fragment_is_actually_read` asserts
the read positively, in both directions: that `fragment_paths()` contains this
file's name, and that `_fragment_text()` contains a `Surface:` line quoted from
inside this file. `test_the_fragment_globs_are_not_phase_anchored` refuses a
future re-anchoring of either glob.

The glob and the regex widened **together**, as
`assemble_surface_changes.py`'s own docstring warns they must: `major` is now
read from the filename rather than hardcoded to `15`, so `16-*` fragments sort
*after* `15.6-*` instead of falling through to the unmatched branch and sorting
ahead of everything. This widens what the gates **read**, never what they
**permit** — every entry still passes the same seven-field refusal and every
claim is still matched by literal substring.

A third reader, `tests/deployment/test_class_lookup.py::_fragment_public_added`,
already globbed `*.md` and needed no change. It is named here so a later
contributor auditing this seam finds all three at once.

## ccf.products.gates.PYDANTIC_MODEL_FORMS

- Surface: ccf.products.gates.PYDANTIC_MODEL_FORMS
- Public surface: true
- Before: absent
- After: a `frozenset[str]` naming every pydantic model spelling
  `ServableProduct` deliberately does not have — both the v1 and v2 forms, and
  both the construction and the dump halves: `construct`, `from_orm`,
  `model_construct`, `model_copy`, `model_dump`, `model_dump_json`,
  `model_json_schema`, `model_validate`, `model_validate_json`,
  `model_validate_strings`, `parse_file`, `parse_obj`, `parse_raw`
- Change type: added
- Why: `D-IMPL-126` item (2). Enumerated **once**, exhaustively, on the
  `CONTAINER_FORMS` precedent from Phase 15.6 — a language's forms listed in one
  place rather than discovered one instance at a time, so a v1 spelling and a v2
  spelling cannot be closed on different days. Public rather than private
  because it is the machine-readable statement of what the type is not, and
  because a test parametrized over it is non-vacuous in a way a hand-listed test
  is not: adding a spelling here adds the refusal on both attribute channels at
  once
- Migration: none — new name. If you were duck-typing `ServableProduct` for a
  pydantic surface, this set is the authoritative list of what will now refuse

## ccf.products.gates.ServableProductNotAModel

- Surface: ccf.products.gates.ServableProductNotAModel
- Public surface: true
- Before: absent
- After: an exception deriving from **both** `GateBypassError` and
  `AttributeError`, raised when a name in `PYDANTIC_MODEL_FORMS` is reached for
  on `ServableProduct` — on the class channel or the instance channel. Its
  message states three things in order: the type is deliberately
  unconstructible; the only construction path is `ccf.products.gates.run_gates`,
  because holding one *is* the evidence the three gates ran; and this is
  INV-CH7-52 (whitepaper §7.6) working, not a pydantic version problem
- Change type: added
- Why: `D-IMPL-126` item (2). The dual inheritance is the whole of its reason
  and is not decorative — `GateBypassError` subclasses `TypeError`, so a refusal
  deriving from it alone makes `hasattr` raise instead of returning `False` and
  `getattr(..., None)` raise instead of defaulting. That hazard is created by
  this fix, so it is closed by it
- Migration: none for correct code. Code that caught the bare `AttributeError`
  these lookups used to raise still catches, because this **is** an
  `AttributeError`; code writing `except GateBypassError` around the gate path
  now catches these too, which is the intent

## ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT

- Surface: ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT
- Public surface: true
- Before: absent
- After: `Final[str] = "route-handle-absent"`, the typed `error_code` on the 503
  a route returns when the `ApiDependencies` handle it needs was not wired. The
  refusal body is the one `refusal_detail` shape (D-08) and its message names
  the absent field and the argument to supply
- Change type: added
- Why: `D-IMPL-126` item (3). A 503 and not a 500 for the
  `ERROR_PRODUCT_DOOR_UNGOVERNED` reason — the fault is the deployment's, not
  the caller's, and an opaque 500 would say nothing about which of eight handles
  is absent. A 503 and not a 404 because the route *exists*: it is mounted, it
  is in the OpenAPI document, and it answers the moment the handle is supplied.
  Narrowing at `build_router` time instead would make the route **vanish**
  rather than refuse, which is a different and unruled behaviour
- Migration: none required. A client that switches on `error_code` gains one
  value it may see from the workflow, skill and hitl routers when the serving
  deployment did not wire them

## ccf_runtime.http_api.routes.CONTENT_ADDRESS_HEADER

- Surface: ccf_runtime.http_api.routes.CONTENT_ADDRESS_HEADER
- Public surface: true
- Before: absent
- After: `Final[str] = "X-CCF-Content-Address"`, the response header every body
  `canonical_response` produces now carries, set to `sha256` of the exact bytes
  on the wire. All five call sites — `agent.py:74`, `config.py:98`,
  `replay.py:47`, `replay.py:65`, `product.py:154` — serve canonical bytes, so
  the claim is uniformly true at every one. `refusal_response` sets no such
  header
- Change type: added
- Why: `D-IMPL-126` item (4). `canonical_response` already claimed that a
  consumer hashing what it received gets the address the producer would — and
  the claim was **unverifiable from outside**, because checking it required
  already owning a CCF canonicalizer, which is exactly what a consumer reaching
  for an HTTP door does not have. A zero-`ccf` client now verifies it with
  `hashlib.sha256(response.content).hexdigest() ==
  response.headers["X-CCF-Content-Address"]`. The body and the digest are
  derived from **one** `canonical_bytes` call: two serializations of the same
  object are two chances to disagree, and the whole value of the header is that
  they cannot
- Migration: none — a new response header, additive on every existing route.
  Nothing is required to keep consuming. If you were re-canonicalizing a
  received body to check its address, you can stop

## ccf_runtime.http_api.dependencies.ApiDependencies

- Surface: ccf_runtime.http_api.dependencies.ApiDependencies
- Public surface: true
- Before: a frozen keyword-only dataclass with **eight required** fields
- After: the same eight fields, with `workflow_factory`, `workflow_engine`,
  `hitl_transport`, `skill_catalog` and `grant_ledger` typed `X | None` and
  defaulting to `None`. `control_plane`, `artifact_store` and `product_resolver`
  stay required — measured, they are read by four routers, two and one, and no
  useful app omits them. The class docstring now names, for each of the eight,
  the routes that handle gates
- Change type: reshaped
- Why: `D-IMPL-126` item (3). The spike measured a first-time adopter serving a
  single Context Product and finding the bundle demanded a workflow factory, a
  workflow engine, a HITL transport, a skill catalog and a grant ledger before
  `GET /product/...` would answer — five fabricated stubs to expose one noun. On
  the five, `None` is the positive assertion *this deployment exposes no such
  route*, and the route refuses with a typed 503 rather than serving
  half-wired. `kw_only=True` means the defaults required no field reordering
- Migration: **nothing is required.** All seventeen shipped construction sites
  pass eight keyword arguments and are unaffected; a deployment that wires all
  eight sees no change on any route. What *did* change is the posture: a
  deployment that forgot a handle used to fail at boot with a `TypeError` and
  now fails at first call with a typed 503. If you were relying on that boot
  failure as your wiring check, assert your bundle explicitly at your
  composition root, or smoke-test one route from each family you intend to
  expose
