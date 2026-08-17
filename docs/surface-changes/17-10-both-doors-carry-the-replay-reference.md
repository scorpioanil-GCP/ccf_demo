# 17-10 — the MCP door emits the refusal envelope, and both doors name the replay record

`D-IMPL-148` (Dave, 2026-08-17) **as amended by Addendum A the same day**. Two
rulings, executed as one change because they need the same one:

- **The MCP tool's refusal is a return value, never a raise.** Measured against
  `mcp==1.28.1`, a FastMCP tool that raises reaches the client as
  `isError=True` carrying `ToolError: Error executing tool <name>: <message>` —
  so a client wanting the governed answer would have to strip a server's
  wording. String-parsing prose for an audited verdict is not a channel.
- **Both doors carry the replay reference.** `Result.replay_ref` is in
  `GUARDED_FIELDS` and `tests/client/conformance/suite.py::assert_served_parity`
  compares every declared field, so an adapter bound against a door emitting
  none would fail parity on it. The base entry scoped the fix to the MCP door
  and recorded the identical HTTP gap as *deferred*; Dave superseded that with
  *both, not one* — the principle `D-IMPL-133` applied to `parameters`.

Because the tool's return had to become a structure for the refusal, the
reference rides that same change rather than forcing a second one.

## What did **not** change, stated first

- **No door validates anything.** `refuse_request` is still the resolver's call
  and no door's (`D-IMPL-121`). This change widens what a door *carries*, never
  what it *checks*.
- **The resolver seam's declared type is unchanged.**
  `ProductResolverProtocol.__call__` still takes the same five keyword arguments
  and is still annotated `-> ServableProduct`. Widening it would reshape all
  three product doors and is a fourth door's worth of work nothing has ruled;
  `ccf.products.resolver` records the same divergence from its own side. What
  moved is the **tool handler's tolerance**: it now accepts `ServedProduct` and
  a refusal alongside the declared vessel, and raises `TypeError` on anything
  else rather than reporting a wiring defect as a governed "no".
- **The MCP resource is untouched.** Its body still *is* the vessel, byte for
  byte. It carries no request, so it has no question for a refusal envelope to
  name, and it has neither a header nor an envelope, so it has no sibling
  channel for a reference. Giving it one means making it a different resource.
- **The HTTP response body is untouched**, so `openapi.json` did not move —
  verified by regenerating it under the committed-drift gate and observing no
  diff. The reference travels as a response header, exactly as
  `X-CCF-Content-Address` does, and neither `X-CCF-*` header is declared in the
  OpenAPI document.
- **The served vessel is never re-serialized.** `DoorOutcome.product_json`
  carries the canonical **text** — the identical expression the resource
  returns — so `sha256` of it is still the producer's content address with no
  second rendering anywhere on the path.
- **A governance refusal still raises.** `ProductEntitlementRefused` is decided
  before the resolver is reached and is deliberately outside the envelope's
  vocabulary; entitlement at the client seam is on the v0 not-list.

## ccf.products.door.DoorOutcome

- Surface: ccf.products.door.DoorOutcome
- Public surface: true
- Change type: added
- Before: absent. A door had exactly one thing it could say — the vessel's
  canonical bytes — so a refusal had no wire shape and a replay reference had
  nowhere to ride. `WireOutcome.replay_ref` had already named that absence:
  *"No shipped door emits this today, which is a defect the client seam exists
  to fix rather than a feature request"*
- After: a frozen, `extra=forbid` contract carrying `product_json`,
  `replay_ref` and `refusal`, with a model validator refusing an outcome that is
  both halves or neither. The MCP tool returns its canonical JSON
- Why: `D-IMPL-148`. It lives in `src/` beside the types it carries, for the
  reason `ccf.products.refusal` gives for its own placement: it is emitted by a
  door in `runtime/` and decoded by a client in `src/ccf/client`, and `src/`
  cannot import `runtime/` — so the emission and the decode agree by
  construction rather than by two implementations being written to the same
  paragraph. The two halves are discriminated **structurally**: exclusive named
  members, and underneath them `RefusalEnvelope` and `ContextProductContract`
  are both `extra=forbid` with disjoint required fields, so neither can validate
  as the other
- Migration: a client reading the MCP product **tool** parses
  `DoorOutcome.model_validate_json(text)` and reads `product_json` where it
  previously read the whole return. The MCP **resource** is unchanged and needs
  no client change. There is no shipped adapter for this tool yet — the
  `mcp+stdio` adapter is plan `17-10` Task 3 — so no SDK consumer is affected

## ccf.products.door.ServedAnswer

- Surface: ccf.products.door.ServedAnswer
- Public surface: true
- Change type: added
- Before: absent. Each door read `.product` off whatever its resolver returned
  and discarded everything beside it
- After: a frozen dataclass carrying the vessel and the replay reference, or the
  reference's honest absence. Not a contract, deliberately: it never crosses a
  wire
- Why: two served shapes reach a door — the narrower `ServableProduct` the
  `runtime/` seams declare, and the `ServedProduct` that
  `ccf.products.resolver.GovernedResolver` returns — and only the second carries
  a reference. One function reading both is what stops three doors growing three
  `isinstance` ladders and then disagreeing about what "served" means
- Migration: none — a new type, reachable only from the new function below

## ccf.products.door.served_answer

- Surface: ccf.products.door.served_answer
- Public surface: true
- Change type: added
- Before: absent
- After: `served_answer(resolved) -> ServedAnswer`. Total over the two served
  shapes; raises `TypeError` naming the type on anything else
- Why: `replay_ref=None` must mean *this deployment's resolver produced no
  reference* — which is the honest report for the narrower vessel — and never
  *a reference was dropped at the door*. Concentrating that read in one place is
  what makes the distinction checkable
- Migration: none — additive

## ccf.products.door.door_refusal

- Surface: ccf.products.door.door_refusal
- Public surface: true
- Change type: added
- Before: absent. A refusal returned by a deployment's resolver reached
  `canonical_bytes(x.product)` and produced an `AttributeError` — an opaque 500
  on HTTP and an `isError` with pydantic's wording on MCP
- After: `door_refusal(resolved, *, asked, product_class, version) ->
  RefusalEnvelope | None`. A ready-made `RefusalEnvelope` passes through
  **untouched**, so the pre-assembly lineage a gate refusal genuinely had is
  preserved rather than re-enveloped away; a bare refusal value that
  `REFUSAL_KINDS` names is translated against the question the door carried;
  anything else returns `None`
- Why: `D-IMPL-148`, and the *"handle both"* the plan asks for. **No third
  channel exists, and that is a measurement rather than an omission**: every
  type in `REFUSAL_KINDS` is a `CCFContract` — a value — so none of them can be
  raised, and no shipped exception in the tree carries one. A door has nothing
  to catch and translate
- Migration: none — additive. A deployment whose resolver already returns
  `ServableProduct` sees no behavioural change at all

## ccf_runtime.http_api.routes.REPLAY_REF_HEADER

- Surface: ccf_runtime.http_api.routes.REPLAY_REF_HEADER
- Public surface: true
- Change type: added
- Before: absent — the HTTP product door discarded the replay reference exactly
  as the MCP door did. `grep replay_ref runtime/ccf_runtime/http_api/routes/product.py`
  returned nothing
- After: `"X-CCF-Replay-Ref"`, the header a served product publishes the
  versioned URI of its replay record under
- Why: `D-IMPL-148` Addendum A's *"both, not one"*. A **header** rather than a
  body member, on the identical argument `CONTENT_ADDRESS_HEADER` is one: the
  body *is* the product, so a reference carried inside it would change the bytes
  and therefore change the address they claim. The MCP tool publishes the same
  string in an envelope because it has no header channel — the asymmetry is a
  property of the transports, not a difference in what the doors carry
- Migration: none — a new response header. Existing clients ignore it. It is
  **absent rather than empty** when the resolver produced no reference, so that
  "no record was named" and "the record is named by nothing" stay distinguishable

## ccf_runtime.http_api.routes.canonical_response

- Surface: ccf_runtime.http_api.routes.canonical_response
- Public surface: true
- Change type: reshaped
- Before: `canonical_response(payload) -> Response` — the canonical body plus
  the content-address header, and nothing else
- After: `canonical_response(payload, *, replay_ref: str | None = None) ->
  Response`. One keyword-only parameter, defaulting to `None`, which publishes
  `REPLAY_REF_HEADER` when supplied and sets no header when not
- Why: the product door is the one call site with a replay reference to publish;
  the other four serve Control Plane and replay artifacts rather than a
  delivered Context Product and pass nothing. A sibling channel on the response
  is the only place the reference can go without changing the bytes the body
  claims an address for
- Migration: none. Additive and defaulted — all five existing call sites read
  identically and behave identically, and the response is byte-for-byte
  unchanged when the argument is omitted
