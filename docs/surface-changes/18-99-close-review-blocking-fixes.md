# 18-99 — Phase 18 close-review blocking fixes (`D-IMPL-151`)

The four findings the `CLAUDE.md` §3.1 close panel produced that close in-phase,
plus the in-phase claim correction for the one that does not. `B0` itself — the
inert client-seam integrity checks — is **deferred to its own follow-on phase as
an open blocking defect**, and is deliberately not repaired here.

## What did **not** change, stated first

- **No wire shape moved.** `ccf.products.door.DoorOutcome`,
  `ccf.client.wire.WireOutcome` and `ccf.client.wire.WireRequest`'s field set are
  byte-identical. `check_outcome` and `verify_content_address` behave exactly as
  they did; only their prose changed.
- **`tests/client/conformance/suite.py` is untouched** — `git diff` against the
  phase base is 0 lines, as `D-IMPL-148` requires and `D-IMPL-151` did not lift.
- **No door began validating.** `D-IMPL-121` still puts every request verdict at
  the resolver. `B2` is about what the MCP door *carries*, not what it *checks*.

## ccf.client.wire.WireRequest — `temporal_boundary` must be timezone-aware

- Surface: ccf.client.wire.WireRequest
- Public surface: true
- Change type: behavior
- Before: any `datetime` was accepted, naive included, and the failure surfaced
  differently on every transport. Measured on the two commands
  `examples/hw1-companies-over-revenue/README.md` documents, with the offset
  stripped off `--as-of`: `inprocess:` raised
  `ccf.contracts.canonical.CanonicalizationError` out of the SQLite graph
  backend, and `mcp+stdio:` raised `ccf.client.errors.TransportError` because the
  far door refused the naive `asked_at` by name and a *raised* door refusal
  reaches a client as a wire error
- After: a field validator refuses a naive instant at construction, so
  `ProductClient.ask` raises `pydantic.ValidationError` before any transport is
  reached and the failure is identical on every binding. `None` is unchanged and
  still means *defer to the server's decision instant* (`D-04`); any UTC offset
  is accepted, not only `+00:00` — `D-IMPL-38` refuses an *ambiguous* instant,
  not a non-UTC one
- Why: `D-IMPL-151` finding `B0b`. The `mcp+stdio` path reported a **transport
  failure for a caller's malformed argument**, which is `D-10`'s inversion: the
  natural response to a `TransportError` is a retry, and this question can never
  succeed. The guard for the hazard already existed one field over at
  `WireRequest._parameters_survive_the_wire`; `temporal_boundary` had no
  equivalent
- Migration: pass an aware instant — `datetime(..., tzinfo=UTC)`,
  `value.replace(tzinfo=UTC)`, or an ISO 8601 string carrying an offset. The
  refusal message names all three. A caller already passing an aware instant or
  `None` is unaffected; a caller passing a naive one was already failing, and now
  fails at the seam with a message that names the repair

## ccf_runtime.mcp.egress — the product tool refuses `"parameters": null`

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Change type: behavior
- Before: the tool argument was `parameters: dict[str, Any] | None = None` and
  the handler read `dict(parameters or {})`, so a supplied JSON `null` arrived as
  `None`, was defaulted to the empty mapping and reached the resolver — while the
  HTTP route refused the identical payload `400
  ERROR_PRODUCT_PARAMETERS_MALFORMED`
- After: the argument is `parameters: dict[str, Any] = EMPTY_PARAMETERS` and the
  handler reads `dict(parameters)`. The generated tool schema is `{"type":
  "object", "default": {}}`, so an **omitted** argument still arrives as the
  empty mapping and a supplied `null` is refused by the argument model before the
  handler runs — the same place a supplied array or string was already refused
- Why: `D-IMPL-151` finding `B2`. `or {}` was a default under a docstring
  stating the handler *"coerces nothing, defaults nothing and inspects
  nothing"*, and the result was a width difference `D-IMPL-133` forbids. The
  HTTP route's refusal is the correct half: the empty mapping is the *positive*
  statement `this question needs nothing beyond its four axes`, so reading a
  supplied `null` as that statement invents an assertion the caller never made
  — `D-08` — on the argument the resolver selects a plan from. Narrowing MCP
  satisfies "no wider than the other door" in the direction that does not add a
  silent default
- Migration: a client that omitted `parameters` is unaffected. A client that
  sent `"parameters": null` explicitly must omit the argument or send `{}`; both
  reproduce the previous behaviour exactly. The shipped
  `ccf.client.adapters.mcp_stdio` adapter always sends a mapping and is
  unaffected

## ccf_runtime.mcp.egress.EMPTY_PARAMETERS

- Surface: ccf_runtime.mcp.egress.EMPTY_PARAMETERS
- Public surface: false
- Change type: added
- Before: absent
- After: the product tool's `parameters` default, named so the argument model's
  schema, the handler and the reason for the non-nullable spelling live in one
  place. Pydantic copies a model's default on every validation, so no call
  receives this instance
- Why: a literal `{}` in the signature would carry the same schema and none of
  the reasoning, and a later reader would "fix" it back to `| None = None`
- Migration: none — a module-level constant, not exported

## ccf.client.codec — the integrity checks' claims corrected, not their behaviour

- Surface: ccf.client.codec
- Public surface: true
- Change type: behavior
- Before: the module docstring argued that the echo is *cross-checked, never
  reconstructed*, and both `verify_content_address` and `check_outcome`
  documented a `TransportError` for a transport that answered a different
  question or altered a vessel in transit
- After: the argument is kept whole and the measured state of the code is
  recorded beside it: `DoorOutcome` carries no request identity, so both shipped
  adapters fill `WireOutcome.request` from the request object the client also
  passes as `sent`, making `check_outcome`'s comparison an object against itself;
  and the "claimed" address is computed by the adapter from the same
  `product_json` it emits, making `verify_content_address` `sha256(x) !=
  sha256(x)`. Both `Raises:` blocks now say which failures are reachable from a
  shipped adapter and which are not. **No behaviour changed.** The same
  correction is carried on `WireOutcome.request` and `.content_address`, which
  point a reader at exactly this argument
- Why: `D-IMPL-151` finding `B0`, and Dave's instruction — *"Do not claim the
  current checks provide that protection."* The fix requires a wire-shape change
  across both doors, the adapter and the codec, and is deferred to its own phase;
  the false claim is not deferred with it
- Migration: **until that phase lands, this SDK must not be described as
  detecting a transport that answered a different question, or as detecting a
  vessel altered in transit.** No code change is required of an adopter; what
  changes is what may be claimed of the seam

## The two vacuous assertions, repaired

- Surface: tests/client/conformance/test_the_fixture_serves_a_replay_reference.py
- Public surface: false
- Change type: added
- Before: `assert_served_parity` compares every declared `Result` field,
  `replay_ref` among them — so two subjects both answering `None` agreed
  perfectly while carrying nothing, and **no conformance leg asserted that a
  served delivery carries a replay reference at all**. Plan `17-10` Task 2
  recorded the precondition in prose and nothing enforced it
- After: a per-subject precondition, run over both real transports, requiring a
  served delivery to carry a reference. It lives at the **binding** rather than
  in `suite.py` because both-`None` is a legitimate deployment shape —
  `served_answer()` returns `None` for the narrower `ServableProduct` and
  `door.py` records that as the honest report — so a suite demanding a reference
  would reject a legitimate deployment on grounds unrelated to the transport.
  What must be true is a fact about *this package's fixture*
- Why: `D-IMPL-151` finding `B1`, the vacuity class surviving inside
  `D-IMPL-148`'s own fix. `D-22`: three controls, including an adapter that
  blanks the reference on the way back, passed into the **real** assertion
- Migration: none — test-tree only

- Surface: tests/mcp/test_egress_parameters.py::assert_same_verdicts
- Public surface: false
- Change type: behavior
- Before: five cases, all well-formed JSON objects, and the two door callables
  **raised** when a door refused before the resolver — so a disagreement of the
  form *one door refuses this payload, the other serves it* was outside what the
  shared table could represent, which is why it could not see `B2`
- After: `REFUSED_AT_DOOR` is a verdict like any other and `EXPLICIT_NULL` is a
  case like any other, giving six. The non-vacuity guard is unchanged and still
  demands a **served** case rather than merely a non-empty table, so a pair of
  doors refusing everything is still refused
- Why: a disagreement the table cannot represent is the table's defect too
- Migration: none — test-tree only

- Surface: tests/contracts/test_canonical.py
- Public surface: false
- Change type: behavior
- Before: `set(carried) <= PERMITTED_CHILD_VARIABLES` — one-sided, so the
  `D-IMPL-150` `PYTHONPATH` repair going missing could not turn it red, while
  the module docstring claimed it *"holds the set closed"*
- After: `assert_child_environment_is_exactly` compares in both directions and
  names extra and missing separately, with two controls — the pre-`D-IMPL-150`
  environment (asserted to satisfy the old `<=`, so the control cannot silently
  stop being the control) and a leaked parent variable
- Why: `D-IMPL-151` finding `B3`, the same class as the leg `D-IMPL-149` split
- Migration: none — test-tree only
