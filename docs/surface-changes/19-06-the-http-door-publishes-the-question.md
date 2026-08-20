# 19-06 — the HTTP door publishes the question it was asked

Phase 19 wave 3, plan `19-06`. Gives the HTTP product door the sibling the
envelope-carrying doors gained in `19-01`, through the channel this one
actually has. The decision of record is `C-09` in
`.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-CONTEXT.md`.

## What did **not** change, stated first

- **`D-IMPL-126`'s four `ETag` reasons stand verbatim.** Not one line inside
  `canonical_response`'s ruling block moved — measured against `git diff`, the
  only change in that span is the signature line itself. The new constant's
  comment **defers to** those four reasons and does not restate them, exactly
  as `REPLAY_REF_HEADER`'s comment already does.
- **`C-09` extends the ruling rather than amending it.** *"Each surface
  publishes the same sibling values through whatever channel it actually
  has"* is the sentence this header hangs on, and it is unchanged.
- **The payload is still serialized exactly once.** `body` is one
  `canonical_bytes` call and the address is derived from those same bytes;
  `grep -c "canonical_bytes(payload)"` is 1. The echo is an independent
  serialization of a **different object**, which is what `REPLAY_REF_HEADER`
  already is.
- **No OpenAPI declaration, and the precedent was measured rather than
  assumed.** `grep -c "X-CCF" openapi.json` returns **0** both before and
  after: neither existing sibling header is declared, so declaring the third
  would make the committed schema inconsistent with itself. No `make openapi`
  run happened.
- **The four non-product `canonical_response` call sites are untouched** and
  pass nothing. The docstring's enumeration of five call sites was re-read and
  re-counted against the tree; it still reads correctly.
- **No HTTP client adapter was built, and none exists.** The echo is verified
  **producer-side only**. Nothing in this plan claims client-side coverage on
  this transport.

## ccf_runtime.http_api.routes.REQUEST_ECHO_HEADER

- Surface: ccf_runtime.http_api.routes.REQUEST_ECHO_HEADER
- Public surface: true
- Change type: added
- Before: absent. This door published two `X-CCF-*` siblings —
  `CONTENT_ADDRESS_HEADER` and `REPLAY_REF_HEADER` — and no statement of what
  it had been asked
- After: `Final[str] = "X-CCF-Request-Echo"`, carrying the caller's own
  `ccf.products.door.WireRequest`, canonically serialized and base64url-
  wrapped
- Why: `C-09`. *One shape* is scoped to doors that **have** an envelope; this
  door's body *is* the vessel, so the echo joins the siblings rather than
  displacing them. base64url rather than canonical JSON verbatim because a
  header value has to survive every intermediary and canonical JSON carries
  `"` and may carry non-ASCII — and because the second-rendering objection
  `ccf.client.wire` records is about the **vessel**, whose address is a
  function of its bytes, while nothing anywhere hashes this echo
- Migration: none — a new name, and a new header a consumer may ignore

## ccf_runtime.http_api.routes.canonical_response — a third sibling

- Surface: ccf_runtime.http_api.routes.canonical_response
- Public surface: true
- Change type: behavior
- Before: `canonical_response(payload, *, replay_ref=None)`
- After: a keyword-only `asked: WireRequest | None = None` after
  `replay_ref`, stamped under `REQUEST_ECHO_HEADER` when it is not `None`.
  `None` — the default — means **no question was posed**, and the header is
  then **absent rather than empty**, on exactly the reasoning `replay_ref`
  already carries: stamping an empty header would make *"no question was
  asked"* and *"the question is named by nothing"* the same observation
- Why: `C-09`. The docstring records the two facts a future HTTP adapter
  needs: that it reconstructs the echo by **decoding this header and never
  from its own state**, and the transport asymmetry — this door requires
  `asked_at` whenever any §6.3 axis is supplied, so an echo published here
  never carries a `None` `temporal_boundary`, whereas `mcp+stdio` carries
  `None` faithfully. It also records that `C-18`'s temporal cross-check has no
  subject on this door: the boundary is built **from** the one `asked_at` the
  route parsed, so a cross-check would compare a value with itself. That is a
  measurement, not an exemption
- Migration: none — additive and keyword-only with a default

## ccf_runtime.http_api.routes.product — the route states what it was asked

- Surface: ccf_runtime.http_api.routes.product.build_router
- Public surface: true
- Change type: behavior
- Before: `retrieve` called `canonical_response(answer.product,
  replay_ref=answer.replay_ref)`. The question it had assembled reached the
  resolver and went no further; a consumer had no producer-sourced statement
  of what had been answered
- After: `retrieve` builds the echo from `_asked`'s own return and the path
  segment it had already resolved, and passes it through as `asked=`. When
  `_asked` returns `None` — the positive assertion that the caller asked for
  the class's standing answer and posed no question of their own — it passes
  `None` and no header is stamped
- Why: `C-09`. Every field originates producer-side, which is the property a
  future HTTP adapter depends on
- Migration: none for a conforming caller

### Two behaviour breaks, both narrowings, both closing a measured divergence

- Surface: ccf_runtime.http_api.routes.product.build_router
- Public surface: true
- Change type: behavior
- Before: a `parameters` value that cannot survive a wire — a `float`, a
  `Decimal`, a `set` — was forwarded verbatim and the door served **200**.
  Measured against the tree: `?parameters={"x": 1.5}` reached the resolver as
  a Python `float`. Separately, an `asked_at` carrying no UTC offset was also
  served **200**
- After: both are refused with a `400`. A wire-unstable parameter carries
  `ERROR_PRODUCT_PARAMETERS_MALFORMED` and the guard's **own** message, which
  names the wire-stable spelling. A naive `asked_at` carries
  `ERROR_PRODUCT_REQUEST_INCOMPLETE` — an axis supplied without the part that
  makes it unambiguous, which is the *the door fills nothing in* that constant
  already records
- Why: `C-09` forces the question to be representable, and `C-10` forbids the
  alternative: publishing no header for a question that cannot be represented
  is a sibling that silently disappears for some questions, which is the exact
  pattern this phase exists to close. `D-08`'s posture — *the fabric never
  silently degrades a caller's value* — decides the direction. Both refusals
  move this door into **agreement** with the MCP product tool, which already
  refuses each of them at `WireRequest` construction; the shared width table
  in `tests/mcp/test_egress_parameters.py` contains no float case, so the
  divergence was real and invisible. This is the narrowing direction
  `D-IMPL-151` finding `B2` already chose for this pair of doors
- **The naive-`asked_at` refusal makes a shipped claim true.**
  `ccf.products.door.WireRequest`'s temporal guard states that *"both product
  doors refuse a naive `asked_at` by name"*. Measured before this change: this
  one did not
- Migration: **a break with no deprecation window** (pre-1.0). A caller
  sending a `float` renders it with `format(value, 'f')`; a caller sending a
  bare local instant attaches an explicit offset. Both spellings are named in
  the refusal message rather than left to be guessed
- **Deferred, and named rather than papered over:** a naive `asked_at` would
  read better under a dedicated `product-asked-at-naive` error code.
  `runtime/ccf_runtime/http_api/errors.py` is outside this plan's declared
  file set, so the existing constant whose recorded meaning covers *an axis
  the door refuses to fill in* is reused. `19-08` should rule on whether the
  dedicated code is owed

## The controls

- Surface: tests/http_api/test_content_address_header.py
- Public surface: false
- Change type: behavior
- Before: 5 tests, all about the content address
- After: 10. Five added, each named against `C-09`: the echo round trip
  (base64url-decode, `model_validate_json`, **total** equality against a
  `WireRequest` built from what the caller sent, never read back off the
  response); its **named sabotage control**, which hands that same assertion
  function a question differing in one parameter and requires it to fail; the
  two refusal legs; and a shared **vacuity guard** asserting the
  representable form of both still serves, without which both refusal legs
  pass against a door that refuses everything
- Why: `C-09`, `CLNT-12`, `D-22`
- Migration: none — test-tree only

- Surface: tests/http_api/test_routes.py
- Public surface: false
- Change type: behavior
- Before: 33 tests. The product door legs here run against the fixture's
  deliberately **ungoverned** app, which refuses and therefore never reaches
  `canonical_response`
- After: 35, plus a module-local governed app built for the same reason
  `test_content_address_header.py` and `test_product_entitlement.py` each
  build one. The absence leg asserts `header not in response.headers` —
  absence, never `== ""` — and its **named sabotage control** hands the same
  assertion a response to a request that *did* pose a question and requires it
  to fail. That control is the load-bearing half: on its own the absence
  assertion passes against a route that never stamps the header at all, which
  is precisely the vacuity this repository has shipped before
- Why: `C-09`, `CLNT-12`, `D-22`
- Migration: none — test-tree only
