# 19-01 — one outcome shape, and the door states what it was asked

Phase 19 wave 1, plan `19-01`. Carries `D-IMPL-151` finding `B0` — the client
seam's two integrity checks cannot fail, on the exact transport where a crossed
question is physically possible — by giving those checks an operand the
consumer did not produce. The decisions of record are `C-01`, `C-02`, `C-04`,
`C-06`, `C-15`, `C-16` and `C-18` in
`.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-CONTEXT.md`.

## What did **not** change, stated first

- **`ccf.client.wire.__all__` is unchanged** — `["TransportAdapter",
  "WireOutcome", "WireRequest"]`. Every published import path resolves exactly
  as before; what moved is where the two names are *defined*.
- **The seam signature is untouched.** `TransportAdapter.ask(WireRequest) ->
  WireOutcome` still reads as it did. `C-05`/`C-08`'s retype to bytes is
  `19-02`'s work, deliberately not this plan's.
- **The clock did not move** (`C-15`, `C-13` governing). Both adapters still
  resolve `as_of=None` to `datetime.now(UTC)` client-side. `ccf.products.door`
  remains `__ccf_mode__ = "algorithmic"` and reads no clock.
- **The checks are still inert on the shipped path.** `mcp_stdio._decode` still
  overwrites the door's echo with its own argument. That is closed in `19-02`;
  this plan lands the shape so the retype can be one commit.

## ccf.products.door.WireRequest

- Surface: ccf.products.door.WireRequest
- Public surface: true
- Change type: added
- Before: defined in `ccf.client.wire`, and reachable only from there
- After: defined here, verbatim — the class docstring, both field validators
  (`_parameters_survive_the_wire`, `_temporal_boundary_survives_the_wire`) and
  the module-private `_unstable_parameter` moved unedited. `ccf.client.wire`
  re-exports it under the same name, so `from ccf.client.wire import
  WireRequest` is unchanged; `WireRequest.__module__` now reads
  `ccf.products.door`
- Why: the door has to *name* the type it echoes (`C-01`), and a producer-side
  shape module cannot import the client package without reversing the layering
  `ccf.products.door`'s own module docstring establishes — the shape is emitted
  from `runtime/` and decoded in `src/ccf/client`, and `src/` cannot import
  `runtime/`. `19-RESEARCH.md` §2.2 evaluated the alternative (`door.py`
  importing `ccf.client.wire`) and measured it cycle-free, and it is still
  rejected on layering grounds
- Migration: none for an importer. Code asserting on `WireRequest.__module__`
  or on a fully-qualified repr sees `ccf.products.door`

## ccf.products.door.DoorOutcome — two required members, five validator rules

- Surface: ccf.products.door.DoorOutcome
- Public surface: true
- Change type: behavior
- Before: three members — `product_json`, `replay_ref`, `refusal` — and a
  three-rule validator. `ccf.client.wire.WireOutcome` was a **separate class**
  with five members and a four-rule validator, and the two were kept in step by
  hand across a transcoding step in each adapter
- After: one class with exactly five members, in `WireOutcome`'s declaration
  order — `request`, `product_json`, `content_address`, `replay_ref`,
  `refusal`. `ccf.client.wire.WireOutcome` is an **alias**, so
  `ccf.client.wire.WireOutcome is ccf.products.door.DoorOutcome` is true. The
  merged `_exactly_one_half` carries **five** rules, not four: the two
  originals raised seven times between them and exactly two of those were the
  same rule in different words. The rule with no counterpart on the other side
  — *a refused outcome carrying a content address* — had no coverage anywhere
  in the tree and now has its own assertion
- Why: `C-06`. A door must emit precisely what a client decodes, because the
  transcoding step between two shapes is exactly where an adapter re-sources
  the echo from client state — which is what `B0` measured on both shipped
  adapters. `request` is required on **both** halves (`C-04`), so one
  comparison covers a served answer and a refusal: a crossed refusal is a
  governed "no" attributed to a question nobody asked, and must be as
  detectable as a crossed vessel
- Migration: a caller constructing a `DoorOutcome` directly must now supply
  `request` and `content_address`. In-tree there is no such caller left —
  `ccf_runtime.mcp.egress` constructs none. `DoorOutcome.model_validate_json`
  against bytes emitted by a pre-Phase-19 door fails, by design: the two new
  members are required, and an optional member with a reconstruction fallback
  is the bypass this phase exists to close

## ccf.products.door.door_question

- Surface: ccf.products.door.door_question
- Public surface: true
- Change type: added
- Before: absent
- After: `door_question(asked_json: str) -> WireRequest`. One
  `WireRequest.model_validate_json` call, re-raising `pydantic.ValidationError`
  as itself
- Why: `C-01` — the echo must be filled from what the door **parsed off its own
  wire**, never from an object it was handed. The parameter is text for exactly
  that reason: a door given an already-constructed `WireRequest` would be
  echoing the caller's own copy back to the caller
- Migration: none — a new name

## ccf.products.door.door_answer

- Surface: ccf.products.door.door_answer
- Public surface: true
- Change type: added
- Before: absent. Each door assembled its own `DoorOutcome` and serialized it
- After: `door_answer(resolved, *, echo, resolved_request, product_class,
  version) -> bytes` — the one emission site for the shape. `echo` is echoed
  verbatim; `resolved_request` is what the door answers against and what
  `door_refusal` names in a refusal's request identity. The two are
  deliberately **not** the same parameter: `WireRequest.temporal_boundary` may
  be `None` and `ProductRequest.asked_at` never is (`C-02`, `C-15`). The vessel
  is serialized exactly **once** and `content_address` is `sha256` of those
  same bytes, on the discipline
  `ccf_runtime.http_api.routes::canonical_response` records
- Why: `C-01` and `C-06`. A producer-computed address is what gives the
  consumer's recomputation something independent to disagree with; two
  serializations would be two chances to disagree
- Migration: none — a new name. Returns `bytes` because the caller puts them on
  a wire without a second rendering; the MCP tool decodes to UTF-8 at the seam,
  losslessly, because canonical bytes are UTF-8-decodable by construction

## ccf_runtime.mcp.egress — `request_context_product` gains a **required** argument

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Change type: behavior
- Before: eight tool arguments, seven required. The handler resolved parameters
  from the `parameters` argument and constructed `DoorOutcome` at two sites
- After: nine arguments, eight required. `request` carries the UTF-8 text of
  `canonical_bytes` over the caller's `WireRequest`; `door_question` parses it,
  and the outcome echoes **what was parsed** rather than the address arguments
  beside it. The handler then refuses a call that asks two things, by name, on
  every axis where a second copy of the fact exists: `product_class` against
  the encoded `product_id`, `parameters` against the encoded declared
  remainder, and — **guarded on `temporal_boundary is not None`** — `asked_at`
  against the encoded boundary. The answer resolves from the **decoded**
  request's parameters, so there is one source for what is answered and the
  echo is that same source. Both `DoorOutcome(` construction sites are replaced
  by one `door_answer` call
- Why: `C-16` and `C-18`. Required rather than optional on the tool
  docstring's own argument for the four §6.3 axes — required-together makes a
  partial address unrepresentable rather than merely refused — and because an
  optional argument with a reconstruction fallback is precisely the bypass this
  phase closes. The cross-check exists because two independent sources for one
  fact is the bypass one level up: a caller could encode question A, address
  question B, and have A echoed while B is answered. `C-18` extends that to the
  temporal axis because `C-15` keeps the clock client-side, so a **concrete**
  `as_of` crosses the pipe twice
  - **Known limit, stated rather than closed:** when the caller sent
  `as_of=None`, the client resolved the instant and there is **no second copy**
  to compare, so a transport altering `asked_at` alone is **undetected**. No
  fallback, tolerance window or reconstruction is added — a reconstructed
  operand is the bypass this phase exists to shut. The residual belongs in
  `C-10`'s named undetected list and in the phase's `D-IMPL` entry
- Migration: **a wire-compatibility break with no deprecation window** (`C-16`;
  pre-1.0). Any non-SDK consumer calling `request_context_product` must add
  `request`, carrying `canonical_bytes` of a `WireRequest` whose `product_id`
  and `parameters` agree with the address arguments beside it, and whose
  `temporal_boundary` is either `None` or exactly the `asked_at` being sent.
  The shipped `ccf.client.adapters.mcp_stdio` adapter sends it and is
  unaffected

## ccf.client.wire — the two shapes are re-exports now

- Surface: ccf.client.wire
- Public surface: true
- Change type: behavior
- Before: `WireRequest` and `WireOutcome` were defined here
- After: both are imported from `ccf.products.door`, and `WireOutcome` is a
  module-level alias rather than a subclass. `__all__` is unchanged, and the
  module docstring gains a section recording the collapse and its direction —
  appended, with every existing paragraph kept
- Why: `C-06`, plus the layering constraint above
- Migration: none for an importer. `isinstance` against either name admits the
  other, which is the point of an alias rather than a subclass

## The new controls

- Surface: tests/products/test_door_answer.py
- Public surface: false
- Change type: added
- Before: absent. **No test in the tree constructed a `DoorOutcome` at all**,
  and `test_codec.py::test_control_a_wire_outcome_with_both_halves_or_neither_is_refused`
  parametrized only two of the validator's rules — which is why rules 3, 4 and
  5 shipped uncovered
- After: 18 tests. The as-asked echo with its vacuity guard; the
  serialize-once address with a byte-level sabotage that also asserts the
  tampered vessel still validates as a `ContextProductContract`; the refusal
  carrying the echo, captured from the fixture deployment's own gates rather
  than synthesized; `door_question`'s round trip over every parameter and
  temporal shape the wire guard admits; and the five validator rules with one
  assertion each
- Why: `CLNT-12` / `D-22` — every gate carries a named sabotage control. The
  control on the shipped code was run in a scratch copy **outside** the tree
  (`door_answer` patched to echo `resolved_request.asked_at`) and observed
  red on all three echo assertions; no tracked source file was edited and
  reverted
- Migration: none — test-tree only

- Surface: tests/mcp/test_egress_parameters.py
- Public surface: false
- Change type: behavior
- Before: the shared case table drove both doors on the parameters axis alone
- After: the MCP leg carries a per-case encoded request derived from the same
  case values the HTTP leg uses, so `assert_same_verdicts` still compares two
  doors on one table. Five legs added for the address cross-check: the
  `product_class` crossing and the `parameters` crossing, each with its vacuity
  guard, and `C-18`'s three regions — a one-microsecond temporal disagreement
  refused by name, agreement answered, and an absent boundary answered rather
  than refused (the guard, and the leg that would go red if the comparison were
  written unguarded)
- Why: `C-16`, `C-18`
- Migration: none — test-tree only

- Surface: tests/crossproc/test_mcp_egress.py
- Public surface: false
- Change type: behavior
- Before: `REQUIRED_TOOL_ARGUMENTS` held seven names
- After: eight, with the constant's own prose amended rather than replaced. One
  leg added over the **real** cross-process path asserting that a question
  asked with `temporal_boundary=None` is echoed `None`, and that
  `content_address` equals `sha256` of the vessel text beside it
- Why: the unit proof cannot see a transport that re-labels what it carries,
  and this is the transport where a crossed question is physically possible
- Migration: none — test-tree only

## Amended by `19-07` — where the claim this shape enables is written down

Plan `19-07` (wave 5) changed **no** public surface and therefore files no
fragment of its own. It is recorded here instead, on the two fragments whose
`Before`/`After` entries describe the shapes its prose is about, so a reader
who arrives at either one is not left looking for a migration note that does
not exist.

What `19-07` did: it replaced `D-GATE-18`'s standing prose constraint — *the
SDK must not be described as detecting a transport that answered a different
question, or a vessel altered in transit* — with a **narrower true sentence**
in `ccf.client.codec`'s module docstring, amend-never-delete, keeping every
paragraph the constraint lived in. The claim names five conditions the checks
detect (corruption, truncation, mis-routing, a re-serializing intermediary,
producer/consumer canonicalization drift) and **four they do not**: an
adversary who can rewrite the envelope, a producer that mis-canonicalizes
consistently, two *identical* in-flight questions crossing, and — the residual
this fragment's *Known limit* block already names — a transport that alters
only the instant a question asked with `as_of=None` was answered against.

Signing stays out of scope and **no signature member is reserved on the wire**,
for the reason `C-10` gives: a member nothing sets and nothing reads is the
shape this phase exists to close.
