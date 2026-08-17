# 17-10 — both parameterised product doors carry client-supplied `parameters`

`D-IMPL-133` (Dave, 2026-08-14) implemented: *"Ruled: both doors carry
`parameters`. The MCP tool and the HTTP route both accept a client-supplied
mapping and pass it through unvalidated to the resolver. **Both**, not one."*

## What did **not** change, stated first

- **No door validates a parameter.** `refuse_request` is still called by the
  deployment's own resolver and by no door (`D-IMPL-121`), because a door never
  holds the `RegisteredProductClass` the comparison needs. Both doors carry the
  mapping **verbatim** — no coercion, no defaulting, no inspection of what is
  inside it. This is why the repair is two lines and not a seam widening.
- **The resolver seam is byte-identical in shape.**
  `ProductResolverProtocol.__call__` still takes the same five keyword
  arguments and still returns `ServableProduct`. Nothing about `ProductRequest`
  moved either; `parameters` was already a required field of it.
- **The MCP resource is untouched.** It still passes `request=None`, because
  `ccf-product://` still has three path segments and no query surface. The
  tool's served body is still byte-identical to the resource's for the same
  question, asserted at
  `tests/mcp/test_egress_parameters.py::test_the_tool_body_is_byte_identical_to_the_resources`.
- **Neither door gained an address-claiming argument.** No `role`, no
  caller-supplied `schema_name`, no caller-supplied `schema_version`. A request
  addressed to another class stays unrepresentable on both surfaces rather than
  merely refused.
- **The tool is still opt-in.** `expose_product_tool` still defaults to `False`,
  so a deployment that upgrades and changes nothing gains no new door and no
  new argument.

## ccf_runtime.mcp.egress — the `request_context_product` tool

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Change type: behavior
- Before: the handler took seven arguments — three address segments plus
  whitepaper §6.3's four axes — and hard-wired `parameters={}` at
  `mcp/egress.py::build_egress_server`. The measured consequence, recorded in
  the handler's own
  docstring: *a product class whose request contract declares **any** required
  parameter is not reachable through this tool*, and a resolver discharging its
  `refuse_request` obligation refused every such call
  `missing-required-parameter`
- After: an eighth argument, `parameters: dict[str, Any] | None = None`,
  forwarded verbatim to `ProductRequest.parameters`. **Optional, not required** —
  the seven above are the *address* and stay required together so a partial
  address remains unrepresentable, while the declared remainder is not part of
  the address. Omitting it is the empty mapping, which says *this question needs
  nothing beyond its four axes*
- Why: `D-IMPL-133`. The half of the recorded objection that said a *"flat
  tool-argument map cannot carry `D-IMPL-103`'s declared nested types without
  the door guessing at coercions"* is **false as measured** — an MCP tool
  argument map is JSON, not flat text, so a presented `3` arrives an `int`, a
  presented `"3"` arrives a `str`, and one level of declared nesting crosses
  intact. Nothing is left to guess at. The half that said a declared-parameter
  surface *"would make this tool wider than the HTTP door"* is still binding and
  is honoured by repairing **both** doors, not neither
- Migration: none. The argument is optional and omitting it reproduces the
  previous behaviour exactly. A deployment whose product class declares no
  required parameter is unaffected; one whose class declares a required
  parameter becomes reachable through this tool for the first time

## GET /product/{tenant}/{product_class}/{version} — `?parameters=`

- Surface: ccf_runtime.http_api.routes.product.build_router
- Public surface: true
- Change type: behavior
- Before: the route took `role`, `subject`, `intent`, `freshness` and
  `asked_at`, and hard-wired `parameters={}` in
  `http_api/routes/product.py::build_router` for the
  identical recorded reason. Those two sites were the **only** two in `runtime/`
  constructing a `ProductRequest` for a door
- After: an optional `parameters` query parameter carrying **one JSON object**.
  The door parses it and carries what it found; it inspects nothing inside it.
  Text that is not JSON, or JSON that is not an object, is refused 400 with the
  new `ERROR_PRODUCT_PARAMETERS_MALFORMED` code. Supplying `parameters` with
  none of the four §6.3 axes is refused 400 with the existing
  `ERROR_PRODUCT_REQUEST_INCOMPLETE`: the declared remainder qualifies a
  question, and there is no question to qualify
- Why: `D-IMPL-133`'s *"both, not one"*. **JSON text in one parameter rather
  than flattened query keys**, and that shape is the whole of how the recorded
  objection is honoured rather than overridden: a flat, string-valued query
  genuinely cannot carry declared types or nesting without the door guessing at
  a coercion, whereas JSON is self-describing and carries both. It is also what
  makes the two doors exactly as wide as each other, which is the property
  `D-IMPL-133` gives as the reason for repairing both
- Migration: none — a new optional query parameter. Existing callers are
  byte-identical in behaviour. `openapi.json` regains one parameter entry and
  is regenerated under the committed-drift gate

## ccf_runtime.http_api.errors.ERROR_PRODUCT_PARAMETERS_MALFORMED

- Surface: ccf_runtime.http_api.errors.ERROR_PRODUCT_PARAMETERS_MALFORMED
- Public surface: true
- Change type: added
- Before: absent
- After: `"product-parameters-malformed"` — the typed code the product route
  refuses a non-JSON-object `?parameters=` with
- Why: `D-08`, one vocabulary and two renderings: the code is the contract and
  the prose is human context, so no client parses refusal text. Refusal rather
  than a fallback to the empty mapping, because a door that quietly read
  malformed text as *no parameters* would answer a question the caller did not
  ask while reporting success
- Migration: none — a new constant, reachable only from a call that supplies the
  new parameter

## The width ceiling, mechanized

- Surface: tests/mcp/test_egress_parameters.py::assert_same_verdicts
- Public surface: false
- Change type: added
- Before: nothing held the two doors' parameter surfaces to each other. They
  drifted into identical hard-wirings independently and were repaired
  independently in plan `16-23` and `D-IMPL-108`
- After: `assert_same_verdicts(cases, ask_mcp, ask_http)` runs **one shared
  case table** against both real doors and requires identical verdicts, where a
  verdict is what `refuse_request` says about the request the door actually
  carried. Five cases: served, served-with-optional, empty, undeclared, and
  wrong-typed. The assertion **refuses a table in which no case is served** —
  without that guard the table would have passed against the two unrepaired
  doors, which carried `{}` and therefore agreed perfectly while carrying
  nothing
- Why: a per-door table lets the two drift, which is how the doors got here.
  `D-22`: the two controls pass a deliberately-wider fake door and a coercing
  fake door into the **real** assertions rather than into copies of them
- Migration: none
