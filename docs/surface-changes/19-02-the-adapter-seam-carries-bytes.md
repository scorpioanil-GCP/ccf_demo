# 19-02 — the adapter seam carries bytes, and no adapter builds an answer

Phase 19 wave 2, plan `19-02`. Closes the mechanism half of `D-IMPL-151`
finding `B0`: an adapter that cannot construct the outcome cannot fill the
echo from the request it was handed, so `check_outcome`'s two comparisons stop
comparing a value with itself. The decisions of record are `C-05`, `C-06`,
`C-07`, `C-08` and `C-14` in
`.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-CONTEXT.md`.
`19-01` landed the shape this plan carries.

## What did **not** change, stated first

- **`ccf.client.wire.__all__` is unchanged** — `["TransportAdapter",
  "WireOutcome", "WireRequest"]`. What moved is what `TransportAdapter.ask`
  returns, not what the module publishes.
- **`Result` is still constructed in exactly one place** (`D-12`), and
  `check_outcome`'s echo comparison still precedes its refusal branch (`C-04`)
  — measured by line number, not assumed.
- **The clock did not move** (`C-15`, `C-13` governing). Both adapters still
  resolve `as_of=None` to `datetime.now(UTC)` client-side, in the same method,
  with the ruling comment intact. The encoded `WireRequest` carries
  `temporal_boundary=None` to the door and the door echoes `None`.
- **No signature member and no shim were added.** There is no `ask` overload
  taking either bytes or an outcome — a fallback that reconstructs the echo is
  precisely the bypass this phase closes (`C-10`, Pitfall 2).
- **`tests/client/conformance/suite.py` is untouched.** The `C-12` tamper legs
  are `19-03`/`19-04`'s work.

## ccf.client.wire.TransportAdapter — the seam returns bytes

- Surface: ccf.client.wire.TransportAdapter
- Public surface: true
- Change type: behavior
- Before: `def ask(self, request: WireRequest) -> WireOutcome` — an adapter
  constructed the outcome object the client then re-checked. `D-11` permitted
  it, and that permission is what let both shipped adapters set
  `outcome.request` from the request they were handed while
  `ProductClient.ask` passed that same object as `sent`, making
  `outcome.request != sent` an object compared with itself
- After: `def ask(self, request: WireRequest) -> bytes`. The request stays
  typed because an adapter genuinely needs its fields to build a tool call or
  a URL; only the answer becomes bytes
- Why: `C-05`, `C-08`. The object return is removed **by type change** rather
  than by convention, so an adapter has nothing to construct and therefore no
  way to source the echo from client state. `mypy --strict` binds this over
  `src` and `runtime`; an out-of-tree adapter is reached by `19-05`'s AST gate
  (`C-17`), because a type change is invisible to code the type checker never
  reads
- Migration: **a source break with no deprecation window** (pre-1.0). An
  out-of-tree adapter — which can only exist by a third party assigning into
  `SCHEME_REGISTRY`, since `D-05` forbids plugin discovery — returns
  `encode_outcome(outcome)` where it returned `outcome`, or hands the
  producer's bytes through unexamined, which is the better shape. The two
  shipped adapters are updated in this plan

## ccf.client.codec.DecodedOutcome

- Surface: ccf.client.codec.DecodedOutcome
- Public surface: true
- Change type: added
- Before: absent
- After: a frozen dataclass with two attributes — `outcome: WireOutcome` and
  `vessel: ContextProductContract | None` — returned by `decode_outcome`
- Why: `check_outcome` **already parses** the served vessel in order to
  validate it, and until now `decode_outcome` discarded that return while
  `ProductClient._result_from` sourced the vessel from its own second
  `check_outcome` call. With the checks moved onto the one decode path, a
  caller that re-parsed `product_json` to get its own copy would be running a
  second contract validation on a second decode path — the defect `D-12`
  exists to prevent, one field over. A frozen dataclass rather than a bare
  tuple, on the precedent `ccf.products.door.ServedAnswer` already sets for *a
  value and the thing that authorized it*: a positional pair at a published
  surface reads as an accident at the first call site that unpacks it wrong
- Migration: none — a new name

## ccf.client.codec.decode_outcome — returns the pair

- Surface: ccf.client.codec.decode_outcome
- Public surface: true
- Change type: reshaped
- Before: `decode_outcome(raw: bytes, *, sent: WireRequest) -> WireOutcome`,
  with **no shipped call site** — both adapters built the outcome directly,
  so the one path that parses `request` and `content_address` out of
  sender-produced bytes was reached only by this package's own tests
- After: `decode_outcome(raw: bytes, *, sent: WireRequest) -> DecodedOutcome`.
  The body is otherwise unchanged: the parse, the malformed-bytes raise and
  the check order are exactly as they were. `ProductClient.ask` now calls it
  on what the adapter returned, so `CLNT-08` stops being a claim about an
  unshipped function
- Why: `C-05`. See `DecodedOutcome` above for why the vessel has to travel out
  with the outcome rather than be re-parsed by the caller
- Migration: a caller reading an outcome field off the return now reads it off
  `.outcome`; the vessel it would otherwise re-parse is `.vessel`. Every
  in-tree call site is updated in this plan

## ccf.client.adapters.mcp_stdio.McpStdioAdapter — `_decode` is gone

- Surface: ccf.client.adapters.mcp_stdio.McpStdioAdapter
- Public surface: true
- Change type: behavior
- Before: `ask` returned the door's text through a private `_decode` that
  parsed the `DoorOutcome`, re-built a `WireOutcome` with `request=request`
  from its own argument, and recomputed the content address from the very
  text it passed on
- After: `ask` returns
  `asyncio.run(self._call(...)).encode("utf-8")`. `_decode` is deleted
  entirely, along with the module's now-unused `hashlib`, `ValidationError`,
  `WireOutcome` and `DoorOutcome` imports. `_call` is unchanged
- Why: `C-06`. The point is the **absence of a transcoding step** — a
  transcoding step is exactly where an adapter can re-source the echo from
  client state. The wire between the MCP door and this adapter stays text
  because raw bytes cannot be an MCP tool result without base64, and a base64
  envelope would be the second rendering of the vessel that `ccf.client.wire`
  rejects by ruling; encoding text this adapter never inspects is a
  pass-through, not a transcoding
- **Diagnostic narrowing, accepted rather than papered over:** `_decode`
  raised a `TransportError` naming the scheme and the program for malformed
  bytes. `decode_outcome` raises the same diagnosis in the same words without
  that context, and the generic message is taken. A thin adapter-level
  well-formedness check would parse and discard — not a transcoding step, but
  a place a future adapter grows one
- Migration: none for a caller. `_decode` was private

## ccf.client.adapters.inprocess.InProcessAdapter — a wire in both directions

- Surface: ccf.client.adapters.inprocess.InProcessAdapter
- Public surface: true
- Change type: behavior
- Before: `ask` built a `ProductRequest` from the `WireRequest` **object** it
  was handed, called the resolver, and passed the result to a private
  `_encode` that built a `WireOutcome` with `request=request` — the same
  object. The answer half was a degenerate wire (`D-13`); the question half
  was not one at all
- After: `ask` is the **client** half: it boots, reads the clock exactly where
  it read it before, encodes the question with
  `canonical_bytes(request).decode("utf-8")`, and hands *text* to a new
  private `_door`. `_door` is the **producer** half: it parses that text with
  `ccf.products.door.door_question`, builds the `ProductRequest` from what it
  parsed, calls the resolver, and emits through `ccf.products.door.door_answer`
  — the one emission site, which serializes the vessel once and derives the
  content address from those same bytes. `_encode` is deleted
- Why: `C-07`. Without it the fix would be cosmetic on the transport every
  quickstart, fixture and dev path uses: two halves sharing one object make
  the echo cross-check an object compared with itself, which is `B0` surviving
  in-process while being closed over the wire. The door half takes **text and
  never a `WireRequest`**, for the reason `door_question` already states
- **The cost, ruled and not benchmarked:** two extra serializations per `ask`,
  accepted with no benchmark owed (`C-14`). `D-13` already accepted *"a
  microsecond of serialization"* on the answer half, and the question is far
  smaller than the answer
- Migration: none for a caller. Both `_encode` and `_door` are private.
  `TransportError` is no longer imported: `_encode`'s wrong-shape raise is
  gone, and `served_answer` inside `door_answer` raises `TypeError` for a
  resolver answering with neither shape — the same diagnosis in the right
  place. No in-tree test asserted the old wording

## ccf.client.client.ProductClient — one decode, no second check

- Surface: ccf.client.client.ProductClient
- Public surface: true
- Change type: behavior
- Before: `ask` returned `self._result_from(self._adapter.ask(request),
  sent=request)`, and `_result_from` ran `check_outcome` on the object an
  adapter had built
- After: `ask` returns
  `self._result_from(decode_outcome(self._adapter.ask(request), sent=request),
  sent=request)`. `_result_from` takes a `DecodedOutcome`, reads the six
  echo/address/replay fields off `.outcome` and the vessel off `.vessel`, and
  keeps its **one** `Result` construction. Its `check_outcome` call and the
  module's `check_outcome` import are both gone — running the checks twice
  would hash the vessel twice and validate the contract twice
- Why: `C-05`. The paragraph explaining why the request identity is read off
  the **echo** rather than off `sent` is unchanged and is now amended with one
  sentence recording where the comparison runs; both `:func:` cross-references
  to `check_outcome` in this module's prose are preserved for `19-07` to amend
- Migration: none — `_result_from` is private and `ask`'s signature and return
  are unchanged

## The repaired and new controls

- Surface: tests/client/test_client.py
- Public surface: false
- Change type: behavior
- Before: five stub adapters and two helpers returned `WireOutcome`; the module
  docstring described the seam as returning an object
- After: every stub returns bytes through the **shipped** `encode_outcome`; the
  object-returning helpers are kept and gain encoding siblings, so a test
  needing the object still has one. No test hand-rolls a wire encoding. The
  docstring is re-aimed at the bytes seam, keeping its reasoning about the two
  lying transports and recording where the lie is now caught. No assertion was
  weakened, retargeted or dropped, and the collected count is unchanged at 16
- Why: `C-05`
- Migration: none — test-tree only

- Surface: tests/client/test_codec.py
- Public surface: false
- Change type: behavior
- Before: `SwallowingAdapter.ask` returned an outcome, and four sites read an
  outcome field directly off `decode_outcome`'s return
- After: the stub encodes; the four sites bind `.outcome`. The three
  `decode_outcome` calls inside `pytest.raises` discard the return and are
  genuinely unaffected. Nothing any of them asserts changed; 34 collected,
  unchanged
- Why: `C-05`
- Migration: none — test-tree only

- Surface: tests/client/test_inprocess_adapter.py
- Public surface: false
- Change type: behavior
- Before: 17 tests. The direct `adapter.ask(request)` asserted the **answer**
  half is a degenerate wire; nothing asserted the question half, because there
  was nothing to assert
- After: 19. The existing leg decodes the bytes and holds its `product_json`
  assertion unchanged. Two added: `C-07`'s question-half round trip — the echo
  equals the question sent **and** is not the same object, over a question
  carrying a nested mapping parameter, observed on a **refused** outcome so
  the echo's outcome-level placement (`C-04`) is what carries it — and
  `C-02`/`C-15`'s pair, `None` in and `None` out while the served vessel names
  a concrete decision instant
- Why: `C-07`, `C-02`, `C-14`. The round trip's vacuity guard was run in a
  scratch script outside the tree: the same assertion against a request
  differing in one parameter fails, so the equality is doing work
- Migration: none — test-tree only

- Surface: tests/client/conformance/test_the_suite_fires.py
- Public surface: false
- Change type: behavior
- Before: `Mutation = Callable[[WireOutcome], WireOutcome]`; `_Swallowing`
  synthesized a refusal outcome around a captured envelope
- After: `Mutation = Callable[[bytes], bytes]`, and every mutation is parse →
  edit → encode. Each records, in prose, that it parses with
  `WireOutcome.model_validate_json` and **not** with `decode_outcome`, and
  why: the decoder runs the client's own checks, so a control that parsed
  through it would attribute an observed failure to the decoder rather than to
  the leg under test. `_Swallowing` now replays the producer's captured
  **bytes verbatim**, and the leg is handed the refusing question as its
  broken-transport question so the captured echo is the echo of the question
  asked. That makes the control **stronger**: the forged refusal survives every
  codec check there is, so the leg has to catch it on `D-10` grounds alone. 44
  collected, unchanged
- Why: `C-05`, `C-08`
- Migration: none — test-tree only

- Surface: tests/client/conformance/test_the_mcp_binding_fires.py
- Public surface: false
- Change type: behavior
- Before: both wrappers edited the outcome object `super().ask` returned
- After: both parse the wire, edit, and re-encode.
  `_AnswersAnotherQuestion`'s re-label survives as a `model_copy` and is
  marked as the line `19-03` deletes to produce the phase's single-transport
  control. It is worth noticing rather than passing over that the re-label is
  **not** a construction, so no construction counter can see it — a limit
  `19-05`'s AST gate has to state in its own docstring rather than imply
- Why: `C-05`
- Migration: none — test-tree only

- Surface: tests/client/conformance/test_the_fixture_serves_a_replay_reference.py
- Public surface: false
- Change type: behavior
- Before: `_DropsTheReplayReference.ask` rebuilt the outcome object
- After: it parses the wire, blanks the reference, and re-encodes — carrying
  `request` through from **`outcome.request`**, the producer's echo, and never
  re-labelling it from the method's own argument
- Why: `C-05`
- Migration: none — test-tree only

- Surface: tests/client/test_wire.py
- Public surface: false
- Change type: behavior
- Before: two annotation-only stubs typed `-> WireOutcome`
- After: `-> bytes`. Neither stub ever speaks; the repair is for the reader and
  for `runtime_checkable` conformance, since `mypy` does not read `tests/`
- Why: `C-08`
- Migration: none — test-tree only

- Surface: tests/client/test_binding.py
- Public surface: false
- Change type: behavior
- Before: a `# pragma: no cover` stub typed `-> WireOutcome`
- After: `-> bytes`, on the same terms as above
- Why: `C-08`
- Migration: none — test-tree only
