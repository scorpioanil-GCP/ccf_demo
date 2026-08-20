# Phase 19: The Client-Seam Integrity Checks Must Be Able to Fail - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the two client-seam integrity checks — `check_outcome`'s request-echo
comparison and `verify_content_address` — **capable of failing** when a
transport answers a different question or delivers a vessel that does not match
the address its producer computed. They cannot fail today on either shipped
adapter, on the exact transport where a crossed-question wire is physically
possible.

This carries Phase 18's `B0`, deferred by `D-IMPL-151` as an **open blocking
defect** and explicitly reserved out of `D-GATE-18`. It is not accepted risk.

**In scope:** the wire form carries request identity; the content address is
claimed by the producer and recomputed by the consumer; the seam is made
unbypassable so the next adapter cannot re-introduce the reconstruction; and
the failure is demonstrated by a **single-transport** client rather than only by
a cross-adapter parity diff (parity is blind by construction to a check broken
identically on both subjects — which is exactly how this survived Phase 18).

**Not in scope:** cryptographic signing of outcomes; adversarial tamper
detection against an actor with envelope write access; closing `A5` (stdio auth
is impersonation, carried forward unclosed from Phase 18); any sweep of the
defect class beyond `B0`.

</domain>

<decisions>
## Implementation Decisions

> **Numbering.** `C-NN` are decisions from *this discussion* and are a distinct
> namespace from the client design spec's `D-NN` (`D-11`, `D-12`, `D-13`,
> `D-15`, `D-22`, `D-28` are cited below and are **not** these) and from the
> project decision log's `D-IMPL-NN`. On ratification these become `D-IMPL-NN`
> entries in `docs/DECISIONS.md`.

### What identity travels
- **C-01:** The producer's echo is **the question the door re-states**, filled
  from the request the door itself resolved and answered — never passed through
  from client state. Rejected: a canonical digest (loses the diagnosis), a
  client-minted correlation token (proves the call, not the content), and both
  together.
- **C-02:** On the temporal axis the echo is **as asked**: a client that sent
  `as_of=None` gets `None` back. The comparison stays a total three-axis
  equality with no wildcard on the default path. The instant actually used is
  already reported on the served vessel, so nothing is lost. Rejected: echoing
  the resolved instant, which forces sent-`None` to match anything and
  reintroduces the vacuity one field over.
- **C-03:** The echo is a **`WireRequest`, compared by total equality** — no
  projection, no field-selection logic, and nothing on the wire that no check
  reads. Rejected: reusing `RequestIdentity` on both halves (its
  `product_version` has no client-side referent without a second assertion).
- **C-04:** The echo sits at **outcome level**, so one comparison covers a
  served answer and a refusal identically — a crossed refusal is a governed "no"
  attributed to a question nobody asked, and is as detectable as a crossed
  vessel. `RefusalEnvelope.request` is untouched and stays what `D-28` ruled it:
  the refusal's own audit record, not a transport control.

### Closing the D-11 bypass
- **C-05:** The adapter seam is **retyped to return bytes** — the adapter no
  longer constructs a `WireOutcome`, and `ProductClient` calls `decode_outcome`.
  This puts `decode_outcome` — which parses every field out of sender-produced
  bytes and today has no shipped call site — onto the shipped path, which is
  where the codec's entire argument already assumed it was. **Amends `D-11`;
  requires its own `D-IMPL` entry.**
- **C-06:** **One shape** for envelope-carrying doors: the door emits exactly
  what the client decodes, so the MCP adapter's `_decode` reduces to passing the
  door's bytes through. The point is the absence of a transcoding step — a
  transcoding step is precisely where an adapter can re-source the echo from
  client state.
- **C-07:** **Symmetric serialization.** The request is encoded too, and a
  producer-side door entry decodes it and echoes **what it parsed**. Over
  `mcp+stdio` this independence already exists (tool arguments genuinely cross a
  pipe); this decision is what makes the check live **in-process**, the
  transport every quickstart, fixture and dev path uses. Without it the fix
  would be cosmetic on the most-used transport. In-process becomes a true
  degenerate wire in both directions, which is the client spec's `D-13` argument
  applied to the question half.
- **C-08:** Seam signature is **`ask(WireRequest) -> bytes`**. The request stays
  typed because an adapter genuinely needs its fields to build a tool call or a
  URL; only the answer becomes bytes. The object return is gone by type change.
  **Amends `CLNT-05`.**

### The producer-claimed address
- **C-09:** "One shape" is scoped to doors that **have** an envelope (the MCP
  product tool, in-process). The **HTTP door is reconciled, not converted**: its
  body stays the vessel and the request echo joins the `X-CCF-*` siblings beside
  the content address it already publishes. `D-IMPL-126` and
  `canonical_response`'s ruling stand verbatim — *"each surface publishes the
  same sibling values through whatever channel it actually has."* No HTTP client
  adapter exists today; a future one assembles from body+headers, and must be
  written knowing every field still originates producer-side.
- **C-10:** The restored claim is **non-adversarial integrity, stated
  precisely**: the client detects an answer to a different question, and a
  vessel that does not match the address its producer computed — against
  corruption, truncation, mis-routing, a re-serializing intermediary and
  producer/consumer canonicalization drift. It does **not** detect an adversary
  who can rewrite the envelope, because the claim rides in the envelope.
  Signing is **out of scope**, and **no signature member is reserved on the
  wire** — a member nothing sets and nothing reads is the pattern this phase
  exists to close. `D-GATE-18`'s standing prose constraint is **replaced by a
  narrower true sentence, not lifted**, and `codec.py` says so in the same
  amend-never-delete style it already uses.

### How failure is proven
- **C-11:** The controls are a **hostile in-repo adapter** (answers question B
  when asked question A; returns a vessel whose bytes no longer match the
  claimed address) driven through the real `ProductClient`, plus **codec-level
  byte sabotage** handing `decode_outcome` tampered bytes. Both are
  **single-transport**, so they falsify the check itself rather than a
  divergence between subjects. A real crossing proxy on the stdio pipes was
  considered and rejected as concurrency/timing risk proving the same
  proposition.
- **C-12:** Tamper legs become a **conformance obligation**. The suite wraps
  each registered adapter in a byte-corrupting decorator — generic, and possible
  only because `C-05` made the seam bytes — and asserts the client raises: one
  leg for a crossed echo, one for an altered vessel. "Official adapter" comes to
  mean "its integrity checks are demonstrably live." This is the direct answer
  to the ROADMAP's *"a fix that leaves the seam bypassable re-opens the defect
  for the next adapter."* Adding legs to `suite.py` is **not** in tension with
  `D-GATE-18`'s zero-diff claim, which was about binding a new *adapter* without
  touching the suite, not about never adding a new *property*.
- **C-13:** **Stay narrow on `B0`.** No sweep of the defect class, no
  general obligations gate. `D-IMPL-151`'s recorded lesson — *parity is blind to
  a check broken identically on both subjects* — does the generalizing.
  `D-IMPL-146`'s accretion principle governs.
- **C-14:** The in-process path's two extra serializations per `ask` are
  **accepted with no benchmark owed**. The client spec's `D-13` already accepted "a microsecond of
  serialization" on the answer half; the question is far smaller than the answer.
  Record the reasoning in the decision entry.

### Rulings taken at planning (Dave, 2026-08-19)

> These three were surfaced by `19-RESEARCH.md` (§ *Conflicts With Locked
> Decisions*, § *Open Questions*), which recommended each be put to the user
> rather than taken by an agent. They are decisions of the same standing as
> `C-01`..`C-14` and become `D-IMPL-NN` entries on ratification.

- **C-15:** **Stay narrow on the clock; correct the prose only.** Both adapters
  resolve `as_of=None` → `datetime.now(UTC)` **client-side** today
  (`mcp_stdio.py:218-220`, `inprocess.py:377`), which makes
  `ProductClient.ask`'s promise that *"the producing deployment answers against
  its own clock"* (`client.py:139-141`) **false on both transports**. `C-13`
  governs: the clock read **does not move** in this phase. The encoded
  `WireRequest` carries `temporal_boundary=None` to the door, the door echoes
  `None` faithfully (which is what `C-02` requires and what the already-green
  `assert_decision_instant_is_auditable` leg pins), and the door's own
  `asked_at` remains the resolved instant it answers at. The false sentence is
  **amended to a true one** — amend-never-delete, the same discipline
  `codec.py`'s `B0` block already uses — and the underlying defect is recorded
  as its own `D-IMPL` entry for a later phase rather than fixed here. Rejected:
  moving the clock to the door (scope beyond `B0`, and a clock read cannot live
  in the `__ccf_mode__ = "algorithmic"` `door.py` entry); and saying nothing,
  which would leave a knowingly false claim in the shipped surface across the
  one phase whose subject is claims matching what the code does (`C-10`).

- **C-16:** **Break cleanly at the MCP tool; rule both breaks in one `D-IMPL`
  entry.** `PRODUCT_REQUEST_TOOL` gains the encoded request as a **required**
  argument — consistent with the tool docstring's own argument
  (`egress.py:672-676`) that required-together is strictly stronger than
  optional, so *"a partial address is unrepresentable rather than merely
  refused."* This is a wire-compatibility break for any non-SDK consumer of the
  tool; pre-1.0, there is **no deprecation window**. The same `D-IMPL` entry
  rules the `C-08` out-of-tree adapter break that CONTEXT.md already left to
  planning, stating the reasoning either way. Rejected: an optional argument
  with a reconstruction fallback — a fallback that reconstructs the echo is
  *precisely* the bypass this phase exists to close, and a member nothing sets
  is the pattern `C-10` names; and reshaping the tool's four §6.3 axis
  arguments wholesale, a larger break that discards the docstring's argument
  for why the axes are separately required.

- **C-17:** **A narrow AST gate proves no adapter constructs the outcome.**
  Scoped to `src/ccf/client/adapters/` only, mirroring `CLNT-06`'s existing and
  already-controlled `count_result_construction_sites` pattern in
  `test_surface.py`. This is what discharges the ROADMAP's explicit *"a fix
  that leaves the seam bypassable re-opens the defect for the next adapter"*
  with a **red check rather than a convention** — a type change binds `mypy`
  over `src`/`runtime` only and is invisible to an out-of-tree adapter. It
  carries its own named sabotage control per `CLNT-12` / `D-22`. This is not
  the "general obligations gate" `C-13` rejected: it is one assertion over one
  directory, not a framework.

- **C-18:** **Cross-check the temporal axis where it is checkable; declare the
  residual where it is not.** Found by the plan-checker against the shipped tree
  (`egress.py:542`, `:760`): because `C-15` keeps the clock client-side,
  `asked_at` stays a separate tool argument, so a **concrete** `as_of` crosses
  the `mcp+stdio` pipe **twice** — once inside the encoded `WireRequest` that
  becomes the echo, and once as the `asked_at` argument the door actually
  answers against. A transport that alters only `asked_at` produces a perfectly
  matching echo for an answer computed at a different instant. That is `B0`'s
  own failure mode surviving on the third axis of a comparison `C-03` defines as
  **total**.

  Therefore: when `temporal_boundary is not None`, the door **cross-checks it
  against `asked_at` and refuses a disagreement by name** — the same mechanism
  already built for `product_class` and `parameters`, extended rather than
  invented. When `temporal_boundary is None` the check is impossible, because
  the client resolved the clock (`C-15`); that residual is **named explicitly**
  in `C-10`'s undetected list, in the `D-IMPL` entry, and in `T-19-01`'s
  mitigation text, which currently claims the opposite. Rejected: declaring the
  whole temporal axis unprotected (ships a comparison called total that is inert
  on one of three axes), and dropping `asked_at` to single-source the instant
  (structurally strongest, but contradicts `C-16`'s ruling against reshaping the
  four §6.3 axes and discards the tool docstring's argument for why they are
  separately required).

### Claude's Discretion
Two residuals the user explicitly left to planning:
- Whether out-of-tree adapters get a deprecation window or simply break at the
  `C-08` type change. Pre-1.0 argues for breaking cleanly; state it in the
  `D-IMPL` entry either way.
- Where the new producer-side door entry lives. `src/ccf/products/door.py` is
  the obvious home — it already owns what a door puts on a wire, and the
  emitting side is in `runtime/` while the shape is in `src/`.

Also at planning's discretion: how the `C-05`/`C-08` change is staged into waves
(single merge to `main` at the gate either way), and the exact naming of the
echo member and the HTTP echo header.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The defect and its ruling
- `docs/DECISIONS.md` — `D-IMPL-151` (the `B0` deferral, the measured defect,
  and the instruction that it is **not** accepted risk) and `D-GATE-18` (the
  reservation, and the standing prose constraint in force until this lands)
- `.planning/phases/18-mcp-transport-the-second-door-and-the-portability-proof/18-CLOSE-REVIEWS.md`
  — `B0` as recorded, plus the ten carried advisories including `A5`
- `.planning/ROADMAP.md` — the Phase 19 detail section (scope "at least" list)

### The client design being amended
- `docs/superpowers/specs/2026-08-15-ccf-client-design.md` — `D-10` (exception
  taxonomy), **`D-11` (the adapter seam this phase amends)**, `D-12` (one
  `Result` construction), `D-13` (in-process as degenerate wire), `D-15`
  (conformance suite), `D-22` (named sabotage controls), `D-28` (refusal
  envelope and `RequestIdentity`)
- `.planning/REQUIREMENTS.md` — `CLNT-05` (amended by `C-08`), `CLNT-06`,
  `CLNT-08`, `CLNT-11`, **`CLNT-12` (every gate carries a named sabotage
  control — this phase is that requirement pointed at itself)**

### The code at the seam
- `src/ccf/client/codec.py` — `check_outcome`, `verify_content_address`,
  `decode_outcome`/`encode_outcome`; its docstring already carries the corrected
  claim and must be **amended, never deleted**
- `src/ccf/client/wire.py` — `WireRequest`, `WireOutcome`, and
  `_parameters_survive_the_wire` (the guard that makes an echo cross-check sound
  rather than a source of false wire failures)
- `src/ccf/products/door.py` — `DoorOutcome`, `served_answer`, `door_refusal`,
  `PRODUCT_REQUEST_TOOL`
- `src/ccf/client/client.py` — `ProductClient.ask` and `_result_from` (the one
  `Result` construction site; reads identity off the echo, safe only because the
  comparison ran)
- `src/ccf/client/adapters/inprocess.py` — `_encode`
- `src/ccf/client/adapters/mcp_stdio.py` — `_decode`, and the `stdio_client`
  spawn
- `runtime/ccf_runtime/mcp/egress.py` — the product tool that emits
  `DoorOutcome`; `build_egress_server`
- `runtime/ccf_runtime/http_api/routes/__init__.py` — `canonical_response`,
  `CONTENT_ADDRESS_HEADER`, `REPLAY_REF_HEADER` and the `X-CCF-*`-over-`ETag`
  ruling (`D-IMPL-126`) that `C-09` preserves
- `runtime/ccf_runtime/http_api/routes/product.py` — the HTTP product door

### Tests and gates
- `tests/client/conformance/suite.py` — the adapter-agnostic suite that gains
  the `C-12` tamper legs
- `tests/client/conformance/test_inprocess_conformance.py`,
  `test_mcp_conformance.py` — the two bound subjects
- `tests/client/test_codec.py` — where the codec's own controls live today
- `examples/hw1-companies-over-revenue/` — `consume.py` (the one unmodified
  consumer across two transports) and `server/serve.py` (the deployment's MCP
  server program)

### Project law
- `CLAUDE.md` §3.1 (the close protocol: cross-AI panel **and** a single-agent
  depth pass, every finding verified against the tree), §6.4 (No-Hardcoding),
  §7.3 (harness neutrality), §11 (working principles)

</canonical_refs>

<code_context>
## Existing Code Insights

### Measured state of the defect (verified in-tree during discussion, not read off the decision entry)
- `DoorOutcome` has three fields — `product_json`, `replay_ref`, `refusal`. **No
  request identity** (`door.py:139-141`).
- `mcp_stdio._decode` sets `request=request` from its own argument
  (`mcp_stdio.py:397,404`); `inprocess._encode` does the same
  (`inprocess.py:426,437`); `client.py:186` passes that same object as `sent`.
  `outcome.request != sent` is therefore an object compared with itself.
- Both adapters compute `content_address` as `sha256` of the very `product_json`
  they pass on (`mcp_stdio.py:406-408`, `inprocess.py:441`), so the check is
  `sha256(x) != sha256(x)`.
- `decode_outcome` — the one path reading both off sender-produced bytes — has
  **no shipped call site**; both adapters build `WireOutcome` directly, which
  `D-11` permits.

### Reusable assets
- `RefusalEnvelope.request: RequestIdentity` (`refusal.py:117-142`) is already
  producer-supplied and already crosses every wire — evidence the producer *can*
  state what it was asked, and the shape to keep consistent with (though `C-03`
  chose `WireRequest` for the echo).
- `canonical_bytes` / `ContextProductContract.model_validate_json` — the one
  serializer both halves of the round trip already share.
- `WireRequest._parameters_survive_the_wire` — the existing guard that stops a
  type-lossy parameter from producing a **false** echo failure. It becomes
  load-bearing the moment the echo can actually fail; `B0b`'s temporal twin
  landed in Phase 18.
- The HTTP door already publishes a producer-computed address header
  (`X-CCF-Content-Address`), serialized exactly once — the pattern `C-09`
  extends to the echo.
- `tools/docs_tests/test_resolver_seam_obligations.py` — an existing
  obligations-gate shape, if the rejected `C-13` alternative is ever revisited.

### Established patterns that constrain this phase
- **Amend, never delete.** `codec.py`'s docstring, `WireOutcome`'s attribute
  docs and `D-IMPL-146`'s banner all keep the reasoning and correct the claim.
  The same discipline applies to every prose correction this phase makes.
- **Enforced by construction over enforced by lint.** `WireOutcome`'s
  `_exactly_one_half` validator is the model: a shape a caller cannot construct
  their way around. `C-05` is the same instinct applied to the seam.
- **Serialize once.** `canonical_response` derives body and digest from one
  `canonical_bytes` call because two serializations are two chances to disagree.
- **A gate nobody is looking at protects nothing** (`CLNT-14`, the Phase 16
  lesson) — and its sharper successor, **a gate that cannot fail protects
  nothing**, which is this phase.

### Integration points
- Both doors (`ccf_runtime.mcp.egress`, `ccf_runtime.http_api.routes.product`),
  both adapters, the codec, `ProductClient`, `WireOutcome`/`DoorOutcome`, and
  the conformance suite. `src/` cannot import `runtime/` — the shape stays in
  `src/ccf/products/door.py` and the emitting sides import it, as they do today.

</code_context>

<specifics>
## Specific Ideas

- The phase's own success sentence, in the ROADMAP's words: *"A control that
  answers a different question must be caught by a **single-transport** client,
  not only by the cross-adapter parity diff."* Any proof that requires two
  subjects has not discharged this.
- `D-IMPL-151`'s process lesson, which generalizes past this fix: the defect was
  found by reading the codec's stated intent against the adapter's construction
   — a depth-pass activity no panel prompt elicited; all three external panelists
  missed it.
- The standing constraint until this lands: the SDK must not be described — in
  documentation, release notes, examples or conversation — as detecting a
  transport that answered a different question, or a vessel altered in transit.

</specifics>

<deferred>
## Deferred Ideas

- **An SDK composition helper for binding-document → governed resolver.**
  `examples/hw1-companies-over-revenue/server/serve.py` is 292 lines, of which
  ~180 are composing deployment values (boot the fabric, 21 named arguments to
  `build_governed_resolver`, register the entitlement policy, mint a token
  table) and only ~35 are the MCP server itself. That cost is deliberate — §6.4
  and CINV-01 mean the SDK ships no server entry point and no governance
  defaults — but whether a *data-driven* composition helper could carry it
  without becoming a values-bearing default is a real question. Its own phase.
- **Signing outcomes for adversarial tamper detection** (`C-10` puts it out of
  scope). Interacts with `D-IMPL-15` and with `A5`.
- **`A5` — stdio auth is impersonation rather than verification.** Carried
  forward unclosed from Phase 18; explicitly not this phase's work.

</deferred>

---

*Phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail*
*Context gathered: 2026-08-17*
