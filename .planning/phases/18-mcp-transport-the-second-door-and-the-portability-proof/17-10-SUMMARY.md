---
phase: 18-mcp-transport-the-second-door-and-the-portability-proof
plan: 10
subsystem: mcp-egress-door
status: complete
tags: [mcp, http-api, product-request, refusal-envelope, replay-ref, mcp-stdio, conformance, portability, d-impl-133, d-impl-148]
requires:
  - D-IMPL-133 (both doors carry parameters — the ruling Task 1 implements)
  - D-IMPL-148 + Addendum A (the refusal envelope, and both doors carry the replay reference)
  - D-IMPL-121 (validation stays at the resolver, never at a door)
  - D-IMPL-103 (one level of declared nested types)
  - D-IMPL-126 (the content-address header whose argument the replay-ref header reuses)
  - D-IMPL-141 Amendment A.3 (a deployment root holds exactly one Python module)
provides:
  - the MCP egress tool's `parameters` argument
  - the HTTP product route's `?parameters=` JSON-object query surface
  - ERROR_PRODUCT_PARAMETERS_MALFORMED
  - assert_same_verdicts / assert_type_mismatch_refused (the width ceiling, mechanized)
  - ccf.products.door — DoorOutcome, ServedAnswer, served_answer, door_refusal, PRODUCT_REQUEST_TOOL
  - the MCP tool's canonical refusal envelope, as a return value
  - X-CCF-Replay-Ref on the HTTP product door
  - assert_refusals_identical / assert_governance_stays_a_raise / assert_both_doors_carry_the_replay_ref
  - ccf.client.adapters.mcp_stdio — the second official transport adapter
  - the `mcp+stdio` scheme in SCHEME_REGISTRY
  - the MCP leg of the client conformance suite
affects:
  - src/ccf/products/door.py
  - src/ccf/client/adapters/mcp_stdio.py
  - src/ccf/client/binding.py
  - runtime/ccf_runtime/mcp/egress.py
  - runtime/ccf_runtime/http_api/routes/product.py
  - runtime/ccf_runtime/http_api/routes/__init__.py
  - runtime/ccf_runtime/http_api/errors.py
  - openapi.json
tech-stack:
  added: []
  patterns:
    - "verdict-over-door-callables: both doors compared as `Callable[[Mapping], Verdict]` so a control substitutes a divergent door into the real assertion"
    - "non-vacuity guard: an assertion refuses a table, or a pair of answers, that cannot fail for the reason it exists"
    - "reflection-over-transcription: field comparison derived from the contract's `model_fields`, never a written-down list"
    - "sibling-channel-per-transport: outcome-level values ride a header on HTTP and an envelope on MCP; the vessel's bytes are never touched"
    - "wire-vocabulary-in-src: a name both a runtime door and a src client must agree on is bound in src, and the door re-exports it"
    - "divergent-subject-into-the-real-leg: a control passes a deliberately-wrong adapter into the shipped suite assertion rather than re-implementing it"
    - "child-inherits-the-caller's-environment: a spawned deployment program must resolve the same SDK the client is running, and a filtered environment fails silently"
key-files:
  created:
    - src/ccf/products/door.py
    - src/ccf/client/adapters/mcp_stdio.py
    - tests/mcp/test_egress_parameters.py
    - tests/mcp/test_egress_refusal_envelope.py
    - tests/client/test_mcp_stdio_adapter.py
    - tests/client/fixtures/__init__.py
    - tests/client/fixtures/stdio_server.py
    - tests/client/conformance/test_mcp_conformance.py
    - tests/client/conformance/test_the_mcp_binding_fires.py
    - docs/surface-changes/17-10-both-doors-carry-parameters.md
    - docs/surface-changes/17-10-both-doors-carry-the-replay-reference.md
    - docs/surface-changes/17-10-the-mcp-stdio-adapter.md
  modified:
    - runtime/ccf_runtime/mcp/egress.py
    - runtime/ccf_runtime/http_api/routes/product.py
    - runtime/ccf_runtime/http_api/routes/__init__.py
    - runtime/ccf_runtime/http_api/errors.py
    - src/ccf/client/binding.py
    - tests/crossproc/test_mcp_egress.py
    - tests/test_surface_shape_capture.py
    - docs/DECISIONS.md
    - docs/SURFACE-CHANGES.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
    - openapi.json
decisions:
  - "D-IMPL-133 Addendum A — the recorded `parameters={}` objection is half false, half honoured"
  - "D-IMPL-148 Addendum A — both doors carry the replay reference; Task 4 is gated on both"
  - "the `mcp+stdio` address is TWO tokens — the server program and the deployment root — because a deployment root holds one Python module and the SDK ships no server"
  - "`PRODUCT_REQUEST_TOOL` moves to `ccf.products.door`; `egress.py` re-exports it, because `src/` cannot import `runtime/`"
metrics:
  tasks_completed: 4
  tasks_total: 4
  duration: ~3 sessions
  completed: 2026-08-17
---

# Phase 18 Plan 17-10: MCP Transport — Summary

All four tasks shipped. **Both parameterised product doors carry a client's
parameters; the MCP door refuses in the canonical envelope rather than in a
raised exception; both doors name the replay record that authorized a delivery;
and `mcp+stdio` is now a second official adapter that passed the conformance
suite without the suite moving to let it.**

The phase's claim is discharged rather than asserted. One question, one pinned
instant, two genuinely different transports — one in-process, one across a real
process boundary with a spawned child and real pipes:

| Transport | Content address |
| --- | --- |
| `inprocess` | `4113d988a3836a0c7a75ecb933c95b09fc9a7a263ed3477a65d325f31eccec50` |
| `mcp+stdio` | `4113d988a3836a0c7a75ecb933c95b09fc9a7a263ed3477a65d325f31eccec50` |

…and the identical replay reference on both:

```
ccf-artifact://tenant-client-fixture/fixture.replay-record/5b1bce07965497083f11d1d2340cd2d56996041652783da8d3aad265f0edb5ad@7001225c0a052e9d7477bdc426e5af3f149b6f55ea5bc6ddd13b98ce7ae3fefb
```

`replay_ref` was neither exempted nor special-cased anywhere, which was Dave's
explicit condition.

## Status: 4 of 4 tasks

| Task | Name | Status | Commit |
| --- | --- | --- | --- |
| 1 | The egress tool carries a client's parameters | **complete** | `74a4224` |
| 2 | The MCP door emits the canonical refusal envelope (+ both doors carry the replay ref) | **complete** | `36c78fb` |
| 3 | The `mcp+stdio` adapter, sync at the surface | **complete** | `f0d7670` |
| 4 | Bind MCP into the conformance suite | **complete** | `671835f` |

---

# Task 1 — what shipped

`D-IMPL-133` (Dave, 2026-08-14) had already ruled *"both doors carry
`parameters`. Both, not one."* It was unimplemented. It is implemented now.

- **MCP egress tool** takes an optional eighth argument,
  `parameters: dict[str, Any] | None = None`, forwarded **verbatim** to
  `ProductRequest.parameters` — no coercion, no defaulting, no inspection.
- **HTTP product route** takes an optional `?parameters=` carrying **one JSON
  object**, parsed and carried on identical terms.
- **`ERROR_PRODUCT_PARAMETERS_MALFORMED`** refuses text that is not a JSON
  object rather than falling back to the empty mapping — a fallback would
  answer a question the caller did not ask while reporting success.
- Supplying `parameters` with none of the four §6.3 axes is refused
  `ERROR_PRODUCT_REQUEST_INCOMPLETE`: the declared remainder qualifies a
  question and there is none to qualify.
- Neither door validates. `refuse_request` is still the resolver's call
  (`D-IMPL-121`), so this is a two-line repair rather than a seam widening.

## The parameter case table, and its size

**Five cases**, in `PARAMETER_CASES`, run against **both real doors** with
identical verdicts required:

| Case | Verdict (both doors) |
| --- | --- |
| `{minimum_score: 11}` | `served` |
| `{minimum_score: 11, region: "north"}` | `served` |
| `{}` | `missing-required-parameter` |
| `{minimum_score: 11, not_declared_by_this_class: "smuggled"}` | `undeclared-parameter` |
| `{minimum_score: "11"}` | `type-mismatch` |

Plus **two** `COERCION_CASES` for the type-mismatch sibling assertion.

A verdict is what `refuse_request` says about the request the door **actually
carried** — which under `D-IMPL-133` is exactly the half a door is responsible
for, and the only definition under which the two doors are comparable at all.

## The non-vacuity guard is the part that matters

`assert_same_verdicts` **refuses a table in which no case is served.** Without
that guard the table passes against the two *unrepaired* doors: both carried
`{}`, so every case reached the resolver as the same empty mapping and the two
agreed perfectly while carrying nothing. This was not theoretical — it was
observed during the RED run, where the wider-door control tripped the vacuity
guard instead of the width assertion because the HTTP door still carried
nothing.

## Sabotage controls (D-22) — three, all shipped tests, all observed firing

| Control | Divergent subject passed into the **real** assertion | Observed |
| --- | --- | --- |
| `test_the_width_assertion_fires_on_a_wider_mcp_door` | a fake `ask_mcp` that admits the undeclared parameter | raises, matches `wider` |
| `test_the_width_assertion_fires_on_a_table_that_never_serves` | two doors that never serve | raises, matches `no served case` |
| `test_the_coercion_assertion_fires_on_a_coercing_door` | a door that reads `"11"` as `11` and serves | raises, matches `type-mismatch` |

No control edits `runtime/` and reverts. **`git status --porcelain runtime/`
was empty after running them** (verified). Each is a test that runs on every CI
run forever, not an edit that leaves nothing in the tree.

## The `16-26` absorption, as written into `docs/DECISIONS.md`

Recorded as **`D-IMPL-133` Addendum A**. Its measured justification, in short:
`16-26` was filed *"neighboring, not gating"* and is gating, because the
conformance fixture class declares `minimum_score` **required**
(`tests/client/fixtures/deployment/ccf_config.yaml:46`). With `parameters={}`
hard-wired, an MCP adapter could not ask the phase's own question, could not
pass `D-15(a)` served parity, and could not carry `D-23` — every call would
have refused `missing-required-parameter` identically, so the parity legs would
have compared two refusals and reported green while proving nothing.

## The recorded reason was amended, never deleted — and its two halves differed

- **The coercion half is FALSE as measured.** It claimed *"a flat tool-argument
  map cannot carry `D-IMPL-103`'s declared nested types without the door
  guessing at coercions."* An MCP tool-argument map is **not flat and not
  string-valued — it is JSON.** Probed against `mcp==1.28.1`: a presented `3`
  arrived `int`, `"3"` arrived `str`, `true` arrived `bool`, and
  `{"a":[1,2]}` arrived a nested `dict`. Nothing is left to guess at.
- **The width half is TRUE and still binding.** The HTTP door hard-wired the
  identical `parameters={}` for the identical reason, and those two were the
  only two `ProductRequest` construction sites for a door in `runtime/`.
  Honoured by repairing **both** — which is what `D-IMPL-133` ruled.

---

# Task 2 — what shipped

Task 2's original content was *the MCP door emits the canonical refusal
envelope*. **Dave widened it the same day**, and the amendment is the reason
this task is larger than the plan wrote it.

## The ruling that widened the task

`D-IMPL-148` (Dave, 2026-08-17) had scoped the replay-reference fix to the MCP
door and recorded the HTTP door's identical gap as **deferred, not fixed**,
explicitly *"stated as an assumption rather than a ruling, because Dave was
offered the sub-question and did not annotate it."* Dave annotated it:

1. **Both doors carry the reference** — `egress.py` **and** `routes/product.py`.
2. **Only after both emit it** may the MCP adapter be bound into the
   conformance suite. That ordering is why this executor's scope stopped
   before Task 3.
3. **Do not special-case MCP, do not drop `replay_ref` from the parity
   comparison, do not weaken the parity suite.** Making a second adapter
   official while it and the HTTP door silently omit a compared field *"would
   make the conformance suite lie."*

Recorded as **`D-IMPL-148` Addendum A**, appended at the end of
`docs/DECISIONS.md` so no line-anchored citation shifts. The base entry's scope
paragraph is **amended and marked superseded, never deleted** — the paragraph
stands as the record of what was assumed, and the addendum carries the
behaviour.

## Why one change and not two

A refusal **cannot be raised** at this door. Measured against `mcp==1.28.1`,
FastMCP wraps a raised tool exception as
`ToolError: Error executing tool <name>: <message>` and delivers it
`isError=True` with that prose prefix — so a client wanting the governed answer
would have to strip a server's wording. String-parsing prose for an audited
verdict is not a channel.

So the refusal had to become the tool's **return value**, the return therefore
became a structure, and **the replay reference rides that same shape change
instead of forcing a second one.** That is the whole reason the two rulings
landed as one commit.

## What was built

**`src/ccf/products/door.py`** — new, and in `src/` for the reason
`ccf.products.refusal` gives for its own placement: the shape is emitted by a
door in `runtime/` and decoded by a client in `src/ccf/client`, and `src/`
cannot import `runtime/`.

| Name | What it is |
| --- | --- |
| `DoorOutcome` | The wire shape: `product_json`, `replay_ref`, `refusal`, with a model validator enforcing exactly one half |
| `ServedAnswer` | A frozen dataclass — the vessel and its reference. Not a contract; it never crosses a wire |
| `served_answer(resolved)` | Reads both served shapes; `TypeError` naming the type on anything else |
| `door_refusal(resolved, *, asked, product_class, version)` | Passes a `RefusalEnvelope` through untouched; translates a bare refusal value; `None` when it is not a refusal at all |

**The MCP tool** returns `canonical_bytes(DoorOutcome(...)).decode("utf-8")`.
**The HTTP route** publishes the same string under the new
`REPLAY_REF_HEADER` (`X-CCF-Replay-Ref`), via one keyword-only, defaulted
`replay_ref` parameter on `canonical_response`.

## The asymmetry is the transports, not the doors

Both doors carry the same values; each uses the sibling channel it actually
has. The argument is not new — it is `canonical_response`'s own, recorded for
the content address and reused verbatim: **the body *is* the product, so
anything carried inside it changes the bytes and therefore changes the address
they claim.** HTTP has a header, so the reference goes in a header and the body
is untouched. The MCP tool has an envelope, so it goes in the envelope and the
vessel rides as text inside it.

**The MCP resource is deliberately excluded, and that boundary is stated
rather than left to be inferred.** It carries no request, so it has no question
a refusal envelope could name; it has neither a header nor an envelope, so it
has no sibling channel. Giving it one means making it a different resource, and
the `mcp+stdio` adapter calls the **tool** (it must, to carry `parameters`), so
conformance is unaffected.

## Task 1's byte-identity assertion: restated, and why that is not weaker

**This is the item the ruling told me to face honestly rather than delete.**

Task 1 shipped `assert tool_text == resource_text` — the tool's *whole return*
was the vessel, byte for byte. Two shipped assertions rested on it:

| Assertion | Before | After |
| --- | --- | --- |
| `tests/mcp/test_egress_parameters.py::test_the_tool_carries_the_resources_bytes_without_re_serializing_them` (renamed from `..._the_tool_body_is_byte_identical_to_the_resources`) | `tool_text == resource_text` | `DoorOutcome.model_validate_json(tool_text).product_json == resource_text` |
| `tests/crossproc/test_mcp_egress.py::test_the_tool_is_never_the_weaker_path` | `tool_text == expected` | `DoorOutcome.model_validate_json(tool_text).product_json == expected` |

**The claim these assertions exist to make is *the parameterised surface is not
a second serialization of the product*** — a re-encode there would silently
change the content address of the resource beside it. That claim is asserted at
full strength, on raw text, unchanged. What is **no longer** claimed is that
the tool's return has *no frame around* those bytes — which is exactly and only
what the ruling changed.

It is also **stronger** in one respect it was not before: the text must now
validate as a `DoorOutcome`, so a door emitting an ad-hoc shape fails here
rather than being read as a vessel.

A third assertion got strictly stronger as a side effect.
`tests/crossproc/test_mcp_egress.py::test_two_questions_reach_two_content_addresses`
hashed *whatever the tool returned*; it now hashes the vessel the envelope
carries, which is the product's **actual** content address. The test's name was
already making that claim and only now measures it.

## Served vs refused: discriminated structurally, never by sniffing

Three mechanisms, and the conjunction is the claim:

1. `DoorOutcome`'s halves are **exclusive named members** under a model
   validator — a caller cannot construct their way to "both" or "neither".
2. `RefusalEnvelope` and `ContextProductContract` are both frozen and
   `extra=forbid` with **disjoint required fields**, so neither validates as
   the other.
3. The bare vessel is **not** a `DoorOutcome`, so a door emitting one is caught
   rather than read as an outcome with missing halves.

All three are asserted in
`test_the_served_and_refused_shapes_cannot_validate_as_each_other`. Nothing in
the module branches on the presence of a key.

## The governance boundary, drawn rather than missed

**A `ProductEntitlementRefused` still RAISES.** It is decided *before* the
resolver is reached, and contract-level entitlement at the client seam is on
the v0 not-list (`D-IMPL-129`). Enveloping it would report *"the fabric
answered no"* about a caller the fabric never answered at all — an audit record
of a decision that was not made.

Asserted on **both** halves, because neither implies the other:

- on the wire, an unentitled caller gets the protocol-native error and **no**
  `DoorOutcome` at all (`pytest.raises(ValidationError)` on the returned text);
- in the translation, the shipped `door_refusal` produces **no** envelope for
  the type — asserted through `assert_governance_stays_a_raise`, which takes
  the renderer as its subject.

A door could get the first right by accident and still acquire a translation
later. That is why both are checked.

## Nine behaviours

| # | Behaviour | Test |
| --- | --- | --- |
| 1 | A request the class does not answer returns an envelope; `kind` names the violation | `test_a_request_the_class_does_not_answer_returns_an_envelope` |
| 2 | A gate refusal carries its own typed fields, unflattened | `test_a_gate_refusal_carries_its_own_typed_fields` |
| 3 | The envelope carries the pre-assembly request identity, `parameters` included | `test_the_envelope_carries_the_pre_assembly_request_identity` |
| 4 | A governance refusal still raises and is not enveloped | `test_a_governance_refusal_still_raises_and_is_not_enveloped` |
| 5 | The MCP refusal is **field-identical** to the in-process one | `test_the_mcp_refusal_is_field_identical_to_the_in_process_one` |
| 6 | The MCP door carries the replay reference, and the vessel is byte-identical | `test_the_mcp_door_carries_the_replay_reference` |
| 7 | **Both** doors carry the **same** reference for the same product | `test_both_doors_carry_the_same_replay_reference` |
| 8 | A resolver carrying no reference has its absence reported, by omission | `test_a_resolver_that_carries_no_reference_reports_its_absence` |
| 9 | Served and refused cannot validate as each other | `test_the_served_and_refused_shapes_cannot_validate_as_each_other` |

Behaviours 1–5 are the plan's five. Behaviours 6–8 are the ruling's widening.
Behaviour 9 is the ruling's *"structurally, not by sniffing"* made executable.

Behaviour 5 is the leg **D-15(b) will consume in Task 4**, and its construction
is what makes it worth leaning on: **one resolver, driven two ways.** In process
a caller holds the envelope the resolver returned; over MCP the *same* envelope
is canonically serialized, carried, and re-validated. Field-identity is
therefore a statement about the **crossing** rather than about two
implementations happening to agree.

## Sabotage controls (D-22) — three more, all observed firing

| Control | Divergent subject passed into the **real** assertion | Observed |
| --- | --- | --- |
| `test_the_identity_assertion_fires_on_a_dropped_kind` | a refusal pair with `kind` changed on one | raises, matches `kind` |
| `test_the_boundary_assertion_fires_on_a_renderer_that_envelopes_governance` | a renderer that turns a governance refusal into a well-formed envelope | raises, matches `governance refusal` |
| `test_the_replay_ref_assertion_fires_on_a_door_that_drops_it` | (a) a door emitting `None`; (b) two doors emitting *different* references | raises, matches `no replay reference` / `property of the decision` |

No control edits `runtime/` and reverts — `git status --short` after the run
shows only the intended, committed files.

**`assert_both_doors_carry_the_replay_ref` checks absence before equality, and
that ordering is the guard.** Two doors both emitting `None` would agree
perfectly while carrying nothing — the vacuous pass this repository ships
repeatedly, and the exact state `D-IMPL-148` was raised about. So a `None` from
either side is refused **by name** rather than compared.

**`assert_refusals_identical` derives its field list from
`RefusalEnvelope.model_fields`, never from a written-down list** — the
discipline `result_fields()` already uses in the conformance suite. A member
added to the envelope next year is compared here without an edit, which is what
stops the assertion narrowing as the contract widens.

## Deviations from Plan (Task 2)

### 1. `[Rule 2 — missing critical functionality]` the HTTP door was repaired, and the plan's Task 2 `files_modified` did not list it

`D-IMPL-148` **Addendum A** is Dave's explicit ruling on exactly this, and it
supersedes the base entry's deferral. Commit `36c78fb`.

### 2. `[Rule 1 — bug]` the plan's *"the door translates a raised refusal"* is not implementable, and the reason is a measurement

The plan's `<action>` says the door should catch *"what its resolver raises or
returns"*. **Nothing raises a refusal.** Every type in `REFUSAL_KINDS` is a
`CCFContract` — a *value* — so none of them can be raised, and no shipped
exception in the tree carries one. `door_refusal` therefore handles the two
**returned** shapes (a ready-made `RefusalEnvelope`, and a bare refusal value)
and says in its own docstring that no third channel exists and why. This is
recorded rather than silently narrowed, because "handle both" was an
acceptance criterion.

### 3. `[Rule 3 — blocking]` the `_serializes_the_whole_vessel` invariant constrained the refactor's shape

`tests/invariants/test_replay_by_construction.py::test_no_enumerated_door_can_drop_the_debt_the_vessel_carries`
walks each door module's **source** for a call `canonical_bytes(<x>.product)`
or `canonical_response(<x>.product)`. Moving the serialization into
`ccf.products.door` would have made every door fail that check while behaving
identically — a false red, but a red the refactor had to respect. So the helper
returns the **vessel and the reference** and each door still serializes
`answer.product` in its own source. This is why `ServedAnswer` exists as a type
rather than the door helper simply returning bytes.

### 4. `[Rule 3 — blocking]` three surface gates went red and were repaired

Caught only because exit codes were branched on rather than echoed.
`tests/test_surface_drift.py`, `tests/test_surface_completeness.py` and
`tests/test_surface_shape_capture.py` all failed on the new public names.
Repairs: a new fragment
`docs/surface-changes/17-10-both-doors-carry-the-replay-reference.md` with six
seven-field entries; `canonical_response` registered in
`_SHAPE_MOVED_BY_FRAGMENT` with its reason; `docs/SURFACE-CHANGES.md`
reassembled via `make surface-changes`.

**`docs/surface/v0.2-surface.json` was NOT regenerated** — single-owner rule,
only `15-01` and `15-21` write it. `git status` confirms it is untouched.

### 5. `[Rule 1 — bug]` a stale citation in Task 1's own fragment was repaired

`docs/surface-changes/17-10-both-doors-carry-parameters.md` cited
`test_the_tool_body_is_byte_identical_to_the_resources` by `path::Symbol`
(`D-IMPL-114`). Renaming the test would have left a citation resolving to
nothing. Updated, with a pointer to the restatement and its reason.

---

# Task 3 — what shipped

`src/ccf/client/adapters/mcp_stdio.py` (415 lines), registered by **one dict
entry** at the bottom of its own module, exactly as `inprocess.py` ends.
`SCHEME_REGISTRY` now holds `['inprocess', 'mcp+stdio']`.

## What was missing, as the plan asked to be told

`src/ccf/mcp/client.py` **speaks streamable HTTP only and reads resources
only** — it has no stdio transport and no tool-call surface. Both were built
here. What *was* reused is its recorded reasoning rather than its code: the
**session-per-call** rule, which exists because a held `ClientSession` driven
from a blocking bridge was measured to deadlock.

`SyncMcpBridge` was deliberately **not** reused, and the reason is a value the
SDK may not choose. It requires `call_timeout_seconds` with no default
(`D-IMPL-38`), and an `AdapterFactory` receives one string with no deadline in
it. The plan's own threat register dispositions `T-17-41` (a stdio server that
never responds) as **accept** for v0 — no timeout, no retry, no backoff — so the
adapter invents none and runs one `asyncio.run` per call instead.

## The address form, and why it is two tokens

**`mcp+stdio:<program> <root>`**, `shlex`-split so either half can be quoted.

The one-token form — *the deployment is the program's own directory* — was
written first, and **a shipped gate caught it**. `D-IMPL-141` Amendment A.3
grants a deployment root exactly **one** Python module, its projection, and
`tests/client/test_data_only_deployment.py` refuses a second by name. Nine tests
went red on a `server.py` placed in the fixture root. The gate is right; the
address form changed.

So both halves are named because neither is inferable from the other:

- **the program** — because the SDK ships no server entry point and cannot.
  `build_egress_server` requires a server name, a token verifier, auth settings,
  an entitlement source and a perspective resolver: five deployment values in
  their entirety (CINV-01);
- **the root** — because the deployment cannot hold the program, and because
  stdio means *the client launches the server*, so a client that starts a
  deployment necessarily already knows where it is.

`ccf.client.binding` and `ccf.client.client` have spelled this scheme
`mcp+stdio:./server.py` since `D-06`; the program still leads the address.

## Where the tool's eight arguments come from

`PRODUCT_REQUEST_TOOL` takes eight and a `WireRequest` carries three. That gap
is the `D-04` boundary showing through, not something to paper over: the
client's question is *what class, which parameters, as of when*, and the rest is
the deployment's vocabulary — read from the **same two documents the in-process
adapter reads**. `tenant` and `version` come from `ccf_config.yaml`;
`subject`/`intent`/`freshness` from `binding.yaml`. `version` is emphatically
**not** the caller's: `WireRequest` carries none by ruling, because a client
pinning a schema version is a client maintaining a copy of the deployment's
registry.

## `PRODUCT_REQUEST_TOOL` moved to `src/`, and `egress.py` re-exports it

The adapter must name the tool it calls, and `src/` cannot import `runtime/`.
The constant is now bound in `ccf.products.door` — which exists for precisely
this reason, in its own words, *"the shape is emitted by a door in `runtime/`
and decoded by a client in `src/ccf/client`… so the emission and the decode
agree by construction rather than by two implementations being written to the
same paragraph."* A tool **name** spelled on both sides of that boundary is the
same hazard. `egress.py` imports it and keeps it in `__all__`, so every existing
`ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL` import and citation resolves
unchanged.

The alternative considered and rejected was **discovering** the tool by calling
`list_tools()` and requiring exactly one. It needs no surface change, and it
buys that by making the adapter unable to say which door it is calling — it
would break the moment a deployment mounted a second tool on the same server.

## The environment hazard, measured rather than imagined

**`mcp.client.stdio.get_default_environment()` hands a child six variables** —
`HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, `USER` — and `PYTHONPATH` is not
among them. A child launched with that default resolves `ccf` through the
interpreter's editable install, which **in this worktree is the main checkout**.

This was not theoretical. The first end-to-end smoke run passed with identical
content addresses and identical replay references *while the server process was
running a different checkout's code*. It reported a perfect result about
software the client under test was not running — the exact defect class this
repository's own hazard notes warn about, reproduced from the inside.

The adapter now passes `env=dict(os.environ)` explicitly, with the reasoning in
its docstring: MCP's filtered default is right for a server you did not write,
and a deployment's own program is not one of those.
`test_the_child_resolves_the_same_ccf_this_client_is_running` asserts the child's
`ccf.__file__` equals the parent's, and **was observed failing** with the
inheritance removed — reporting
`/home/parkave/ccf_code/src/ccf/__init__.py` against the worktree's path.

## Transport failures — four modes, four places

Every one raises `TransportError` and produces **no** `Result`:

| Leg | Where it fails |
| --- | --- |
| `test_an_address_naming_no_program_raises_before_anything_is_launched` | before launch — `BindingError`, a `TransportError` by inheritance |
| `test_a_server_that_exits_at_once_raises_rather_than_refusing` | at the pipe — the child dies mid-handshake |
| `test_a_door_that_raises_arrives_as_a_broken_wire_and_not_as_a_no` | at the door — `isError` with the server's prose in front of it |
| `test_a_server_answering_something_other_than_an_outcome_raises` | in the bytes — not a `DoorOutcome` |

Plus `test_a_one_token_address_is_refused_rather_than_half_resolved`, and the
**non-vacuity leg**: a question the real deployment refuses comes back as a
*value* — a refused `Result`, no exception. Without it, "everything raises"
would have passed all four above.

**A governance refusal arrives on this wire as `isError`, and is reported as a
broken wire rather than as a "no".** That is not a narrowing:
`ccf.client.errors` already places *an authentication failure* under *the wire
never spoke*, because from where the caller stands no governed answer arrived.
String-parsing FastMCP's `ToolError: Error executing tool …` prefix for an
audited verdict is not a channel — the same measurement Task 2 made.

## `git diff src/ccf/client/binding.py` — no new mechanism

Seven insertions, five deletions, **all inside one comment block**: the note
saying the registry is empty *"until"* the adapters land now names both adapters
and says each registers in one statement. No code changed in that module.

---

# Task 4 — what shipped

**`git diff tests/client/conformance/suite.py` is EMPTY.** A factory, a break
hook, and one call per property were the whole of the binding.

**And this time that is not the trivial truth.** Task 1's executor was careful
to say an empty diff proved nothing while Tasks 3 and 4 had not run. It is
evidence now, and the specific thing it is evidence of is this: binding a real
second transport — a different process, a different lifecycle, a different
failure vocabulary, a question assembled from different sources — required
**adding a subject and nothing else**. What made it possible is that `suite.py`
reaches every transport through `AdapterSubject` (a name, a way to connect, a
way to break) and derives its compared fields from `Result` rather than writing
them down.

## What is now compared, and against what

Six legs take **both** subjects, so the cross-adapter comparisons stop
degenerating to self-comparisons:

| Leg | What it now proves across two transports |
| --- | --- |
| `assert_served_parity` | every declared `Result` field identical — `payload`, `content_address`, `replay_ref`, `lineage`, `debt`, the request identity |
| `assert_one_question_is_one_address` | one question, one content address, whichever transport carried it |
| `assert_refusal_parity` | the same governed no — reason, key, unflattened kind, request identity |
| `assert_guard_parity` | the fail-closed guard holds per **field**, on both |
| `assert_wire_failure_parity` | a killed transport raises on both; a refusal through the healthy one does not |
| `assert_two_parameters_are_two_addresses` | `D-23` on the new path — the caller's number is in the address |

The break hook is transport-specific and genuinely damages the substrate: it
writes a program that exits immediately **beside** the deployment root (never
inside it — Amendment A.3 again) and points the binding at it, so the pipe
closes on the client. The hook raises nothing itself, and returns the same class
the healthy factory returns, so `suite.py`'s own same-type check is satisfied
rather than worked around.

## The deployment's server program

`tests/client/fixtures/stdio_server.py`, beside the deployment and not in it.
It **boots through `ccf.client.adapters.inprocess::_boot`** — the same function
the in-process adapter boots through — and that is load-bearing rather than
tidy: if it composed its own resolver, a passing parity leg would only show that
two *compositions* happened to agree. This is also how the `GovernedResolver`
precondition Task 2 recorded is satisfied by construction rather than by
inspection, and it was checked **before** the server was written, as instructed.

**One thing the deployment had to state that no shipped code could state for
it.** MCP stdio carries no authentication channel — FastMCP installs its bearer
middleware on the HTTP app, and there is no HTTP app — so `get_access_token()`
inside the door's handler finds nothing and the door refuses every caller as
unverified. The transport's own boundary is process ownership. The fixture
deployment therefore establishes its stdio caller's identity once, in **its own
program**, which is the only place such a decision may be written (CINV-01).
This is recorded as FINDING 6 below, because it is a real gap in the shipped
door's governance story and not merely a fixture detail.

## D-22 controls — a binding that could not fail would prove nothing

`test_the_suite_fires.py` proves the suite's *assertions* fire. It cannot prove
that **this binding** puts a real second transport where those assertions can
see it: a factory returning an adapter that agreed with in-process by
construction would pass every leg while comparing nothing. So two controls pass
a **divergent `mcp+stdio` subject** into the **real** `assert_served_parity`,
alongside the **real** in-process subject. Both still spawn a real child over
real pipes; each diverges in exactly one way, downstream of the transport.

| Control | Divergence | Observed |
| --- | --- | --- |
| `test_served_parity_fires_on_an_mcp_door_that_drops_the_replay_reference` | `replay_ref` discarded on the way back | raises — *"`replay_ref`: inprocess answered 'ccf-artifact://…' and mcp+stdio answered None"* |
| `test_served_parity_fires_on_an_mcp_transport_answering_another_question` | asks one question, echoes another | raises — *"`payload`: … `count`: 2 vs 1 …; `content_address`: …"* |

The first is the one this plan exists for. `replay_ref` is compared through
`result_fields()`, which **derives** its list from `Result` — so nobody can see
that comparison by reading the suite. The control makes it visible, which is
what turns *"both doors carry the reference"* from a claim into a measurement.

Neither control edits `src/` or `runtime/`, and neither re-implements an
assertion.

## Which pipeline runs the MCP conformance leg, and why

**The always-on one.** `make conformance` runs `tests/client/conformance`, and
`make test` already collects that directory, so the MCP leg runs on every
`ci-core` with no opt-in. It is entitled to be there: it is **network-free and
credential-free** — a child process on the same host, a file-backed store, a
SQLite graph composed from a path — so it passes with every substrate
environment variable unset. `D-32`'s opt-in discipline applies to a deployment
pointed at stores outside the repository, and this is not one.

Cost measured: `make conformance` 54 passed in **13.9 s** (was 47 tests); the
MCP legs spawn roughly a dozen short-lived children.

## The binding file is 131 lines, not 80 — and where they went

The plan budgeted 80 and said an overage means *"the suite is carrying
adapter-specific weight and the SUMMARY says where."* Measured, by AST:

| | `test_mcp_conformance.py` | `test_inprocess_conformance.py` (the model) |
| --- | --- | --- |
| total | 131 | 188 |
| blank | 32 | 38 |
| comment | 4 | 41 |
| docstring | 47 | 48 |
| **code** | **48** | **61** |

**None of the overage is adapter-specific weight.** The adapter-specific part is
two functions — `connect_over_stdio` and `break_over_stdio` — totalling four
statements. The rest is 20 lines of imports, seven one-line delegations to
`suite.py`, and prose. The module carries *less* code than the single-subject
module it mirrors, for one more subject and the same seven legs. Seven legs with
a docstring each cannot fit in 80 lines, and cutting legs to reach a line count
would have traded coverage for a number.

---

## Findings — verified against the tree, not asserted

### FINDING 1 (was blocking for Task 4): **CLOSED.** Served parity's `replay_ref` leg can now pass

The previous summary recorded that `assert_served_parity` compares `replay_ref`
and that no shipped door emitted one, so an `mcp+stdio` adapter would produce
`replay_ref=None` and the parity leg would report a disagreement. **Both doors
now emit it**, and the field was neither exempted nor dropped from the
comparison — which was Dave's explicit condition. `tests/client/conformance/`
is untouched: `git diff` against it is empty.

The remaining Task 4 dependency is Task 3, not this.

### FINDING 2 (design input for Task 2): **CONSUMED.** A refusal is the tool's return value

Recorded in full above and in `D-IMPL-148` Addendum A. `mcp==1.28.1` was
re-confirmed as the installed version.

### FINDING 3 (advisory): **CONSUMED.** The plan's Task 3 verification command names a symbol that does not exist

The plan's automated check is `from ccf.client.binding import SCHEMES`. The
registry is named **`SCHEME_REGISTRY`**. Task 3 ran the corrected command:

```
$ PYTHONPATH=src:runtime .venv/bin/python -c "…; print(sorted(SCHEME_REGISTRY))"
['inprocess', 'mcp+stdio']
```

### FINDING 4 (new, advisory): the HTTP door still has no refusal channel

DIV-4 is unclosed on HTTP and this is **deliberately** so, recorded in
`routes/product.py`'s module docstring and in Addendum A. A resolver answering
with a `RefusalEnvelope` there reaches `served_answer` and raises a `TypeError`
**naming the shape** — an opaque 500, exactly as the pre-existing
`AttributeError` produced, but now saying what went wrong. Rendering a fabric
refusal over HTTP is a status-code and body-shape decision nobody has ruled,
and inventing one on a shipped door would put an unruled contract in front of
adopters.

### FINDING 5 (new, operational): `make` targets need a `.venv` inside a worktree

`Makefile:10` is `PYTHON := .venv/bin/python` — a **relative** path — and a
fresh Claude Code worktree has no `.venv`, so every `make` target fails with
`No such file or directory` before running anything. A gitignored symlink to
the main checkout's `.venv` fixes it. `ENV := PYTHONPATH=src:runtime` is also
relative and therefore resolves to the **worktree's** `src` and `runtime`,
which is correct — but a bare `.venv/bin/python` invocation without that
`PYTHONPATH` would grade the **main checkout's** code, because the venv's
editable install points there. Verified at this commit:
`PYTHONPATH=<worktree>/src:<worktree>/runtime` resolves `ccf` to the worktree.

**Tasks 3 and 4 found the sharper half of this.** The `PYTHONPATH` that fixes
the *parent* does not reach a **child process** launched over MCP stdio, because
`mcp.client.stdio` filters the environment down to six variables. The child then
resolves `ccf` through the venv's editable install — the main checkout — and
answers correctly from code nobody is testing. See Task 3 above; the adapter now
passes the environment explicitly and a test holds it there.

---

## Findings raised by Tasks 3 and 4

### FINDING 6 (new, blocking-for-nobody-yet, but real): `assert_decision_instant_is_auditable` cannot take two subjects

**A defect in plan `17-07`'s suite, reported rather than worked around.**

The leg refuses a question that names its own instant — correctly, since handed
one it would recover the value it was given. It then compares the recovered
`served.lineage.graph_snapshot_at` **across subjects** via `_assert_views_agree`.
But with `as_of=None` each subject resolves the instant by reading a clock, so
any two subjects recover two different instants. Measured with two *in-process*
deployments: `2026-08-17 17:35:45.603222+00:00` against
`2026-08-17 17:35:45.719308+00:00` — 116 ms apart.

So the leg is unsatisfiable for **any** two subjects, and this is **not
MCP-specific**: two in-process subjects would fail it identically. It is
vacuously green today only because one subject is bound.

**Three things were not done about it**, per Dave's ruling that the suite is not
weakened to admit an adapter: `replay_ref` was not dropped, MCP was not
special-cased, and `suite.py` was not edited. The MCP binding calls this leg with
**the MCP subject alone**, which is a per-module argument choice and not a suite
change; its per-subject property — *a caller can recover the instant that
answered, and prove it by re-asking pinned to it* — is real and is asserted for
this transport.

The fix, when someone rules on it, is a suite change: either split the leg into a
per-subject property and a separate cross-subject one over a *pinned* question,
or compare only the per-subject re-ask invariant. Both are `17-07`'s to make.

### FINDING 7 (new, advisory): the shipped egress door has no identity story over stdio

`build_egress_server` requires `token_verifier` and `auth_settings` together
(`D-03`), and FastMCP installs that middleware **only on the HTTP app**. Over
stdio there is no HTTP app, so `verified_grant()` finds no access token and the
door refuses every caller `UnverifiedProductCallerRefused` — before any
deployment gets a say.

MCP stdio has no authentication channel by design; its boundary is process
ownership, and the server is a child of the client that spawned it. So a
deployment serving over stdio must establish its caller's identity itself, and
the fixture deployment does exactly that in its own program — which is the right
place (CINV-01: an identity provider is never the SDK's to choose).

What is **not** settled is whether the SDK should offer a supported seam for it,
or say in `build_egress_server`'s docstring that the auth pair is inert over
stdio and identity is the deployment's to establish. Today a deployment
discovers this by having every call refused. Worth a `D-IMPL` entry; not raised
as one here because Tasks 3 and 4 were not chartered to change that door, and
the fixture's own program is a legitimate resolution for the conformance leg.

### FINDING 8 (new, advisory): `D-24`'s revisit trigger fired and the answer did not change

`docs/superpowers/specs/2026-08-15-ccf-client-design.md` §9 names *this adapter*
as the trigger for revisiting the sync-only client surface. It was built and the
ruling holds unchanged: `ask` is synchronous, the async client is bridged inside
it with one `asyncio.run` per call, and no asynchronous twin was added. Recorded
because a named trigger that fires silently is a decision nobody knows was made.

---

## Requirements

`CLNT-15` is **satisfied**: its parameters clause (Task 1), its
refusal-envelope clause (Task 2) and its conformance clause (Task 4) are all
discharged. `CLNT-12` is **satisfied** by Task 3 — a second registered transport
adapter exists, builds no `Result`, and is sync at the surface.

Requirement IDs are **not** marked complete here: the orchestrator owns
`STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md` for this plan, and neither was
touched.

## Verification

Every run set `PYTHONPATH` to the worktree's `src:runtime`, and every exit code
was **captured and branched on** rather than echoed. `make ci-core` was run
**detached** with a `REAL_EXIT` sentinel, because it takes ~10 minutes and a
foregrounded run is killed mid-sweep — a truncated log is not a pass.

| Command | Exit | Result |
| --- | --- | --- |
| `make ci-core` (first run) | **2** | `make test` **3816 passed, 118 skipped, 0 failed**; `lint` 0; `typecheck` 0; **`gate-tools` red** on one stale generated report — see below |
| `make ci-core` (confirming re-run) | **0** | `3816 passed, 118 skipped, 0 failed`; `gate-tools` `400 passed` + `154 passed` |
| `make lint` | 0 | clean |
| `make typecheck` | 0 | `Success: no issues found in 210 source files` |
| `pytest tests/mcp/test_egress_refusal_envelope.py` | 0 | 12 passed |
| `pytest tests/mcp tests/crossproc/test_mcp_egress.py tests/http_api` | 0 | 174 passed |
| `pytest tests/crossproc tests/http_api tests/mcp tests/invariants` | 0 | 445 passed |
| surface gates (drift, completeness, shape capture, citation coverage) | 0 | 44 passed |
| `make gate-tools` | 0 | `400 passed`, `154 passed` |
| `make openapi` | 0 | **no diff** — the HTTP response *body* did not move |

Baseline for comparison was **3804 passed, 118 skipped** at Task 1's merge. The
delta is **+12**, which is this task's twelve new tests, and **no test was
removed** to get there.

### The first `ci-core` run went red, and reporting it is the point

`REAL_EXIT=2`. It was branched on rather than echoed, which is the only reason
it was seen: the failure is a **single** stale generated report
(`docs/surface/examples/RETIREMENT-COUPLINGS.md`), two lines of line-number
drift caused by the docstring paragraphs added to `egress.py`. It was
regenerated and the gate went green.

**One measurement worth carrying forward, because it cost a cycle.** The
retirement sweep scans **every file in the repository**, including untracked
scratch files. Regenerating the report while transcript logs sat in the
worktree root produced a report claiming `234 rows across 74 files`; with those
files deleted the true figure is `232 rows across 73 files`, and the committed
report was then stale in the *opposite* direction. **A regenerated report is
only correct if the working tree is clean of scratch files when it is
regenerated.** Every log this task produced was written outside the repository
after that was discovered.

`make conformance` and `make docs-strict` were **not** run at Task 2 — they
belong to Tasks 3 and 4. Both are run and green below.

### Tasks 3 and 4 — the phase's final sweep

Same discipline: `PYTHONPATH=src:runtime` on every invocation, every log written
**outside** the repository, `ci-core` and `docs-strict` run **detached** with a
`REAL_EXIT` sentinel and branched on rather than echoed.

| Command | Exit | Result |
| --- | --- | --- |
| `make ci-core` | **`REAL_EXIT=0`** | **3832 passed, 118 skipped, 0 failed** in 573.96 s; `lint` 0; `typecheck` `Success: no issues found in 211 source files`; `gate-tools` `400 passed` + `154 passed` |
| `make conformance` | 0 | **54 passed** in 13.89 s (was 47 — the seven MCP legs) |
| `make docs-strict` | **`REAL_EXIT=0`** | strict mkdocs build + publish scan clean |
| `make gate-tools` (first run) | **2** | one stale generated report — see below |
| `make gate-tools` (after regeneration) | 0 | `400 passed`, `154 passed` |
| `make lint` | 0 | clean |
| `make typecheck` | 0 | `Success: no issues found in 211 source files` |
| surface gates (drift, completeness, shape capture) | 0 | 39 passed |
| `pytest tests/client/test_mcp_stdio_adapter.py` | 0 | 7 passed |
| `pytest tests/client/conformance/test_mcp_conformance.py` | 0 | 7 passed |
| `pytest tests/client/conformance/test_the_mcp_binding_fires.py` | 0 | 2 passed |

**The pass count moved 3816 → 3832: exactly +16**, which is 7 adapter tests + 7
conformance legs + 2 controls. **No test was removed to get there**, and the
skip count is unchanged at 118 — nothing was quietly turned off.

**`gate-tools` went red first, and reporting it is again the point.** The same
failure class Task 2 hit: `docs/surface/examples/RETIREMENT-COUPLINGS.md` stale
by two lines of line-number drift, from docstring paragraphs added to
`egress.py` and `binding.py`. Regenerated with the working tree clean of scratch
files, and the sweep reported **`232 coupling rows across 73 files`** — the same
figure Task 2 established as the true one, which is the check that no scratch
file inflated it. It was re-swept again after this SUMMARY was written, because
the sweep reads the planning tree including this file.

### Three surface names were added, and the gates caught all three

`ccf.products.door.PRODUCT_REQUEST_TOOL`,
`ccf.client.adapters.mcp_stdio.McpStdioAdapter` and
`ccf.client.adapters.mcp_stdio.SCHEME` each failed
`test_surface_completeness.py` with *"NO ENTRY"* until
`docs/surface-changes/17-10-the-mcp-stdio-adapter.md` claimed them.
`docs/SURFACE-CHANGES.md` was reassembled with `make surface-changes`.

**`docs/surface/v0.2-surface.json` was NOT regenerated** — single-owner rule,
only `15-01` and `15-21` write it. `git status` confirms it untouched.
`openapi.json` was likewise not touched: Tasks 3 and 4 added no HTTP surface.

### `openapi.json` — measured, not assumed

The success criterion was *"regenerated if the HTTP response surface moved."*
It did not move: the change is a **response header**, and FastAPI declares
neither `X-CCF-Replay-Ref` nor the pre-existing `X-CCF-Content-Address` in the
OpenAPI document. `make openapi` was run and `git status` showed `openapi.json`
unmodified. The precedent is `D-IMPL-126`'s content-address header, which is
likewise absent from the document.

## Deviations from Plan (Tasks 3 and 4)

### 1. `[Rule 3 — blocking]` the address form is two tokens, not one

The plan says *"the address form is `mcp+stdio:<command>` — decide the exact
spelling by reading how the existing MCP tooling in the tree spells a stdio
server command."* **There is no existing stdio tooling in the tree** — measured;
`grep -rn stdio` over `src/`, `runtime/`, `tests/` and `examples/` returned eight
hits before this plan, every one of them prose about the scheme name (five in
`binding.py`, one in `client.py`) or the one `split_binding` test asserting
`mcp+stdio:./server.py` splits into two. No transport, no command, no launcher.
So the spelling was decided against
the constraints instead, and the one-token form was blocked by a shipped gate
(`D-IMPL-141` Amendment A.3). Recorded in full under Task 3.

### 2. `[Rule 3 — blocking]` `PRODUCT_REQUEST_TOOL` moved from `runtime/` to `src/`

Not in the plan's Task 3 `<files>`. It is forced: the adapter must name the tool
it calls and `src/` cannot import `runtime/`. `egress.py` re-exports the name, so
nothing that cited it moves. Surface fragment written; gates green.

### 3. `[Rule 2 — missing critical functionality]` the child inherits the caller's environment

Not in the plan. Without it the spawned server resolves a **different checkout's**
`ccf` and reports correct-looking answers about untested code — observed, not
theorised. A test now asserts the child's `ccf.__file__` matches the parent's and
was observed failing without the fix.

### 4. `[Rule 2]` the D-22 controls are new tests, not a plan requirement

Tasks 3 and 4 carry no `<acceptance_criteria>` sabotage clause of their own.
Two were written anyway, because a conformance *binding* that could not fail
proves nothing about the transport it binds — the same argument Tasks 1 and 2
made about their assertions.

### 5. `[Rule 1 — bug]` `tests/client/fixtures/` gained an `__init__.py`

Needed so both the adapter tests and the conformance binding import one
`STDIO_SERVER` constant rather than each spelling the path. Note the contrast
with `tests/mcp/`, which must **not** gain one: `tests/` is on `sys.path`, so an
`__init__.py` there would shadow the `mcp` distribution. `tests/client/fixtures`
shadows nothing, and `make ci-core` confirms collection is unaffected.

## Not done, and what it would take

- **FINDING 6** — `assert_decision_instant_is_auditable`'s cross-subject
  comparison. A `17-07` suite change, deliberately not made here.
- **FINDING 7** — a supported identity seam (or at minimum a docstring) for the
  egress door over stdio. Worth a `D-IMPL` entry; out of charter for this plan.
- **`ccf.mcp.client` was not refactored.** The `mcp+stdio` adapter carries its
  own stdio transport and tool call rather than growing them onto
  `McpResourceClient`, whose surface is *resources over streamable HTTP*. If a
  second stdio consumer ever appears, that is the moment to lift the transport
  into the shared module — one consumer is not yet evidence of a shared concern.

**`tests/client/conformance/suite.py` was not touched, and this time that
means something.** `git diff` against it is empty *with a real second adapter
bound and passing all seven legs* — which is the claim plan `17-07` wrote itself
to make and could not test. What it took: an eight-line factory pair and seven
one-line delegations. What it did **not** take: an assertion added, an assertion
narrowed, a field exempted, or MCP named anywhere inside the suite.

## Self-Check: PASSED

Every file this plan claims to have created exists on disk, and every commit
hash it cites resolves in `git log`:

- `src/ccf/client/adapters/mcp_stdio.py`, `src/ccf/products/door.py`
- `tests/client/test_mcp_stdio_adapter.py`, `tests/client/fixtures/__init__.py`,
  `tests/client/fixtures/stdio_server.py`
- `tests/client/conformance/test_mcp_conformance.py`,
  `tests/client/conformance/test_the_mcp_binding_fires.py`
- `docs/surface-changes/17-10-the-mcp-stdio-adapter.md`
- commits `74a4224`, `36c78fb`, `f0d7670`, `671835f`

`.planning/STATE.md`, `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` are
**unmodified** — the orchestrator owns them for this plan.
