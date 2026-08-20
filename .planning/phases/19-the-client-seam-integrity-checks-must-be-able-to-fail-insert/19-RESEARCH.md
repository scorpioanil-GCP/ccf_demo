# Phase 19: The Client-Seam Integrity Checks Must Be Able to Fail — Research

**Researched:** 2026-08-19
**Domain:** Python SDK — client transport seam, wire shapes, producer-side door entry, conformance-suite mechanics
**Confidence:** HIGH (every claim below is measured against the tree at HEAD `192c79d`; nothing is restated from `19-CONTEXT.md` without re-verification)
**Tree state at research:** `make lint --all` exit 0; `pytest --collect-only` = **4027 collected** (matches `D-GATE-18.1`'s 3909 passed + 118 skipped)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> **Numbering.** `C-NN` are decisions from *this discussion* and are a distinct
> namespace from the client design spec's `D-NN` (`D-11`, `D-12`, `D-13`,
> `D-15`, `D-22`, `D-28` are cited below and are **not** these) and from the
> project decision log's `D-IMPL-NN`. On ratification these become `D-IMPL-NN`
> entries in `docs/DECISIONS.md`.

**What identity travels**
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

**Closing the D-11 bypass**
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

**The producer-claimed address**
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

**How failure is proven**
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

### Deferred Ideas (OUT OF SCOPE)

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
</user_constraints>

---

## Phase Requirements

**No new REQ-IDs.** The ROADMAP's `Requirements:` line for Phase 19 is prose
(*"carries Phase 18's `B0`"*). This phase **amends `CLNT-05`** (`.planning/REQUIREMENTS.md:201`)
rather than minting a requirement. The coverage contract is the `C-01`…`C-14`
decision set. `.planning/REQUIREMENTS.md`'s traceability table (lines 341–362) has
no Phase 19 rows and needs none.

Requirements re-exercised (not re-minted) by this phase:

| ID | Line | How this phase touches it |
|----|------|---------------------------|
| `CLNT-05` | `.planning/REQUIREMENTS.md:201` | **Amended by `C-08`.** Text still reads `ask(WireRequest) -> WireOutcome`; must become `-> bytes`, with the old text kept per amend-never-delete. |
| `CLNT-06` | `:202` | One `Result` construction site must survive the seam retype — `tests/client/test_surface.py::count_result_construction_sites` (AST walk over `src/`, `runtime/`, `examples/`) is the gate. |
| `CLNT-08` | `:204` | `decode(encode(x)) == x` — `decode_outcome` moves from test-only onto the shipped path, so this requirement stops being a claim about an unshipped function. |
| `CLNT-11` | `:207` | The conformance suite gains two legs (`C-12`) without gaining a transport name. |
| `CLNT-12` | `:208` | **This phase is that requirement pointed at itself.** Every new gate carries a named sabotage control in the same plan. |
| `CLNT-14` | `:210` | `consume.py`'s AST-purity and budget gates must stay green; `consume.py` uses only `ProductClient` and is unaffected by the seam retype (verified — see §1.4). |
| `CLNT-15` | `:211` | The MCP adapter must still pass the suite, now including the two new legs. |

---

## Summary

The defect is exactly as `D-IMPL-151` measured it, and it still holds at HEAD.
The fix is a **wire-shape change plus a seam retype**, and the two are
inseparable: retyping the seam to bytes (`C-05`/`C-08`) is what makes the
producer-minted echo unforgeable by an adapter, and carrying request identity on
the wire (`C-01`…`C-04`) is what gives the retyped seam something true to carry.

The blast radius is **narrower than it looks**. `mypy` covers only `src` +
`runtime` (`pyproject.toml:158-162`), so test annotations naming `WireOutcome`
do not fail `make typecheck`. Of 4027 collected tests, the seam retype
mechanically breaks roughly **60–95** — concentrated in five test modules — and
`examples/` is untouched because `consume.py` speaks only `ProductClient.ask`.

Two findings from reading intent against construction (the `D-IMPL-151`
posture) that the planner must resolve before writing tasks:

1. **`C-02` collides with the tool's required `asked_at` on `mcp+stdio`, and
   with a pre-existing defect underneath it.** Today *both* adapters resolve
   `as_of=None` to `datetime.now(UTC)` **client-side**
   (`mcp_stdio.py:218-220`, `inprocess.py:377`) — so `ProductClient.ask`'s own
   promise that *"the producing deployment answers against its own clock"* is
   false on both transports. If the door echoes what it parsed from the tool
   arguments, it will echo a concrete instant where the client sent `None`, and
   **every default-path ask over MCP becomes a false `TransportError`**. `C-07`'s
   literal wording — *the request is encoded too, and the door decodes it* —
   resolves this cleanly (§2.3). The planner must choose deliberately; this is
   not a re-litigation of `C-02` but the mechanism `C-02` requires.
2. **The single-transport control C-11 asks for is one deleted line away.**
   `tests/client/conformance/test_the_mcp_binding_fires.py::_AnswersAnotherQuestion`
   already asks the real door question B while the client asked A — then
   re-labels the echo (`answered.model_copy(update={"request": request})`,
   line 69). Under a bytes seam that re-labelling is *impossible*, and the same
   class becomes a single-transport control with no new machinery (§8.1).

**Primary recommendation:** define **one** outcome shape and **one** request
shape in `src/ccf/products/door.py`, have `ccf.client.wire` re-export them, add a
shared producer-side door entry in `door.py` that both the MCP door and a new
in-process door call, and retype the seam to bytes in a single wave — then add
the two conformance tamper legs and the single-transport controls in the wave
after. Do **not** put `from ccf.client.wire import WireRequest` in `door.py`
(it works — verified — but reverses the established layering).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Minting the request echo | **Producer / door** (`src/ccf/products/door.py` entry, called from `runtime/` and from the in-process adapter) | — | `C-01`: the echo must be filled from what the *door* parsed, or it is a reconstruction. |
| Computing the claimed content address | **Producer / door** | — | `C-10`: the claim must be checkable, so it must originate where the bytes originate. |
| Serializing the outcome envelope | **Producer / door** | — | `C-06`: one shape, no transcoding step. |
| Carrying bytes | **Transport adapter** (`src/ccf/client/adapters/*`) | — | `C-05`/`C-08`: an adapter that can construct the outcome can forge the echo. |
| Decoding + all three checks | **Client codec** (`src/ccf/client/codec.py`) | `ProductClient._result_from` | `D-12`: one decode, one `Result` construction, a code path an adapter cannot avoid. |
| Publishing siblings without an envelope | **HTTP door** (`runtime/ccf_runtime/http_api/routes/`) | — | `C-09` + `D-IMPL-126`: each surface publishes the same sibling values through whatever channel it actually has. |
| Proving the checks can fail | **Tests** — conformance suite (generic) + named controls (per-subject) | — | `C-11`/`C-12`, `CLNT-12`, `D-22`. |
| Entitlement / perspective resolution | **`runtime/` doors only** | — | Unchanged by this phase; the shared `src/` door entry must take an already-resolved perspective, exactly as `served_answer`/`door_refusal` do today. |

---

## Project Constraints (from CLAUDE.md)

| Directive | Where it bites in this phase |
|-----------|------------------------------|
| §6.4 No-Hardcoding — enforced over `src`, `runtime`, `examples` **and `tests`** (`tools/lints/__main__.py:124`) | New conformance tamper legs and hostile-adapter controls must read the product id / parameter names from the deployment's own documents, exactly as `test_inprocess_conformance.py:41-55` does. A spelled product id in a new test is a red lint. |
| §7.3 zero harness imports in `src/` | Not touched — no harness anywhere near this seam. Lint scope `("src", "runtime")`. |
| `src/` cannot import `runtime/` | `tests/invariants/test_src_does_not_import_runtime.py`. The shared door entry lives in `src/`; both doors call *into* it. Never the reverse. |
| Amend, never delete | `codec.py`'s `B0` correction block (lines 44–84) and both `Raises:` blocks are **amended**, not removed. `D-GATE-18`'s standing constraint is **replaced by a narrower true sentence** (`C-10`), which means new prose beside the old, not a deletion. |
| Typed contracts, `extra=forbid` | Every wire shape is a `CCFContract`. Adding required members to `DoorOutcome` is a breaking wire change — see §10 for who parses it. |
| Composition-preservation / algorithmic (`CINV-03`) | `codec.py`, `wire.py`, `door.py` all carry `__ccf_mode__ = "algorithmic"`; the new door entry must too, and must take no clock. **This is a live constraint:** resolving `as_of=None` to *now* is a clock read, so it cannot live in the algorithmic `door.py` entry — it must stay in the caller (the adapter or the `runtime/` door). See §2.3. |
| §3.1 close protocol | Cross-AI panel against **shipped code**, written to `19-CLOSE-REVIEWS.md`; then a single-agent depth pass; every finding verified against the tree. |
| §2.2 branch discipline | Phase branch `phase-19`; single merge to `main` at `D-GATE-19`. |

Project skills: `/home/parkave/ccf_code/.claude/` contains only `settings.local.json` and `worktrees/` — **no `skills/` directory exists**. Nothing to load.

---

## 1. Blast radius of the `C-05`/`C-08` seam retype

### 1.1 `src/` — the definition sites (all must change)

| File:line | What it is |
|-----------|-----------|
| `src/ccf/client/wire.py:336-343` | `TransportAdapter.ask(self, request: WireRequest) -> WireOutcome` — **the Protocol itself** |
| `src/ccf/client/wire.py:72` | `__all__ = ["TransportAdapter", "WireOutcome", "WireRequest"]` |
| `src/ccf/client/wire.py:232-317` | `WireOutcome` — 5 members + `_exactly_one_half` validator |
| `src/ccf/client/client.py:186` | `return self._result_from(self._adapter.ask(request), sent=request)` — the site that passes `sent` and the adapter's own object into one comparison |
| `src/ccf/client/client.py:188-224` | `_result_from(outcome: WireOutcome, *, sent: WireRequest) -> Result` |
| `src/ccf/client/client.py:63,65` | imports `check_outcome`, `WireOutcome` |
| `src/ccf/client/adapters/inprocess.py:334-387` | `InProcessAdapter.ask(...) -> WireOutcome` |
| `src/ccf/client/adapters/inprocess.py:406-442` | `_encode(...) -> WireOutcome`; `request=request` at **422** and **437**; `content_address=hashlib.sha256(vessel).hexdigest()` at **439** |
| `src/ccf/client/adapters/mcp_stdio.py:188-232` | `McpStdioAdapter.ask(...) -> WireOutcome`; `request=request` at **231** |
| `src/ccf/client/adapters/mcp_stdio.py:443-490` | `_decode(text, *, request) -> WireOutcome`; `request=request` at **476** and **483**; `sha256(...)` at **485-487** |
| `src/ccf/client/binding.py:74,170` | `AdapterFactory = Callable[[str], TransportAdapter]`, `adapter_for_binding(...) -> TransportAdapter` — signature unchanged, but the docstrings name the seam |
| `src/ccf/products/door.py:114-173` | `DoorOutcome` — 3 members (`product_json:139`, `replay_ref:140`, `refusal:141`), **no request identity** (confirmed at HEAD) |
| `src/ccf/client/codec.py:119-304` | `encode_outcome`, `verify_content_address`, `check_outcome`, `decode_outcome`; the echo comparison is `codec.py:236` |

### 1.2 `runtime/` (must change)

| File:line | What it is |
|-----------|-----------|
| `runtime/ccf_runtime/mcp/egress.py:788-799` | the only two `DoorOutcome(` constructions in the tree |
| `runtime/ccf_runtime/mcp/egress.py:532-802` | `request_context_product` tool — 8 arguments, returns `str` |
| `runtime/ccf_runtime/http_api/routes/__init__.py:48,67,210-213` | `CONTENT_ADDRESS_HEADER`, `REPLAY_REF_HEADER`, `canonical_response`'s header dict |
| `runtime/ccf_runtime/http_api/routes/product.py:168-192` | `retrieve` → `_asked(...)` → `canonical_response(answer.product, replay_ref=...)` |

`runtime/` imports **nothing** from `ccf.client` today (verified: `grep -rn "from ccf.client" runtime/` is empty). Introducing `runtime/ → ccf.client` would be a new dependency direction — see §2.2 for the recommended alternative.

### 1.3 `tests/` (must change) — with collected counts

| File | Collected | Seam dependency | Est. tests broken |
|------|-----------|-----------------|-------------------|
| `tests/client/test_client.py` | 16 | 5 stub adapters returning `WireOutcome` (`:112,:120,:127,:270,:293`); helpers `served_outcome_for:68`, `refused_outcome_for:79`; module docstring `:11` is *about* the object seam | **~16 (all)** |
| `tests/client/conformance/test_the_suite_fires.py` | 44 | `_Divergent:94-99`, `_Swallowing:359-374`, inline adapters `:434,:467`; `Mutation = Callable[[WireOutcome], WireOutcome]:83`; `_remint:111`, `_move_the_expiry:178`, `_move_only_the_address:199`, `_drop_the_refusal_key:237`, `_misreport_the_anchor:593` | **~25–35** |
| `tests/client/test_codec.py` | 34 | `SwallowingAdapter.ask:366`; the rest call `decode_outcome`/`encode_outcome` directly and survive | **~1–3** |
| `tests/client/test_inprocess_adapter.py` | 17 | one direct `adapter.ask(request)` at `:310` asserting `outcome.product_json:331` | **~1–2** |
| `tests/client/conformance/test_the_mcp_binding_fires.py` | 3 | `_DropsTheReplayReference:52-54`, `_AnswersAnotherQuestion:65-70` both `model_copy` a returned `WireOutcome` | **3 (all)** |
| `tests/client/conformance/test_the_fixture_serves_a_replay_reference.py` | (in 69) | `_DropsTheReplayReference.ask:150-158` builds a `WireOutcome` | **~1–2** |
| `tests/client/test_wire.py` | 13 | `_NeverReached.ask:86` annotation only — never returns | **0 runtime; 1 annotation** |
| `tests/client/test_binding.py` | 25 | one `# pragma: no cover` stub at `:55` | **0 runtime; 1 annotation** |
| `tests/client/test_surface.py` | 19 | `"WireOutcome"`/`"TransportAdapter"` in a *forbidden-names* set (`:137-138`) — unaffected unless names change | **0** |
| `tests/mcp/test_egress_refusal_envelope.py` | 12 | parses tool text via `DoorOutcome.model_validate_json:534` | **0–4** (parses, does not construct; new required members arrive from the door) |
| `tests/mcp/test_egress_parameters.py` | 11 | `DoorOutcome.model_validate_json:948` | **0–2** |
| `tests/crossproc/test_mcp_egress.py` | 38 | `DoorOutcome.model_validate_json:1142,1501,1502` | **0–3** |
| `tests/client/test_mcp_stdio_adapter.py` | 17 | stub server bodies at `:261` (`'return "{}"'`) and `:302` — neither builds a valid outcome; all asks go through `ProductClient` | **0–2** |
| `tests/client/conformance/test_inprocess_conformance.py` / `test_mcp_conformance.py` | 8 + 8 | all through `ProductClient` | **0** |
| `tests/client/test_data_only_deployment.py` | — | all through `ProductClient` | **0** |
| `tests/http_api/test_content_address_header.py` | 5 | asserts `canonical_response`'s single-serialization equivalence; `C-09` adds a header | **0–2** |

**Total estimate: 50–95 tests of 4027 (1.2–2.4%).** The concentration in
`test_client.py` and `test_the_suite_fires.py` is the wave-planning signal:
those two modules are ~50 of the ~85.

### 1.4 `examples/` and `tools/` — **no change required**

- `examples/hw1-companies-over-revenue/consume.py` imports `ProductClient` and
  the two adapter modules (for scheme registration) only — verified by reading
  all 80 lines. **`CLNT-14`'s purity and budget gates are unaffected.**
- `examples/hw1-companies-over-revenue/server/serve.py` and `server/compose.py`
  import `ccf.client.adapters.binding_document` (the document loader), never the
  seam.
- No `tools/` module names `WireOutcome`, `TransportAdapter`, or `DoorOutcome`.

### 1.5 Out-of-tree adapters (the discretion item)

`SCHEME_REGISTRY` at import of both adapter modules is `['inprocess', 'mcp+stdio']`
(measured). There is no plugin discovery, no entry-point mechanism, and
`D-05` explicitly forbids one — so an out-of-tree adapter can only exist by a
third party importing `ccf.client.binding.SCHEME_REGISTRY` and assigning to it.

**Recommendation: break cleanly, no deprecation window.** Reasons, all
verifiable: (a) the package is pre-1.0 and `docs/surface/v0.2-surface.json` is a
*v0.2* baseline; (b) a compatibility shim that accepted **either** a
`WireOutcome` or bytes would re-open exactly the bypass `C-05` closes — an
adapter taking the object branch reconstructs the echo again, and the gate would
be green; (c) `D-11`'s permission is what admitted the defect, so a window is a
window on the defect. State the ruling in the `D-IMPL` entry either way, per the
discretion note. `[VERIFIED: SCHEME_REGISTRY measured; D-05 read at spec §3]`

---

## 2. Where request identity attaches, and what the producer-side door entry looks like

### 2.1 The measured starting point (re-verified at HEAD)

| CONTEXT.md claim | Status at HEAD | Actual |
|---|---|---|
| `DoorOutcome` has three fields, no request identity — `door.py:139-141` | ✅ **holds, line numbers exact** | `product_json:139`, `replay_ref:140`, `refusal:141` |
| `mcp_stdio._decode` sets `request=request` — `mcp_stdio.py:397,404` | ✅ holds, **lines drifted** | `:476` and `:483` (plus `:231` in `ask`) |
| `inprocess._encode` does the same — `inprocess.py:426,437` | ✅ holds, **one line drifted** | `:422` and `:437` |
| `client.py:186` passes the same object as `sent` | ✅ **holds, exact** | `client.py:186` |
| Adapters `sha256` the bytes they pass on — `mcp_stdio.py:406-408`, `inprocess.py:441` | ✅ holds, **lines drifted** | `mcp_stdio.py:485-487`, `inprocess.py:439` |
| `decode_outcome` has no shipped call site | ✅ **holds** | Only `tests/client/test_codec.py` (7 call sites) |

The planner should cite the **HEAD** numbers, not CONTEXT.md's.

### 2.2 Where the shapes should live — recommendation, with the evidence

`door.py:11-16` already states the placement rule for exactly this problem:

> *This module lives in `src/` for the reason `ccf.products.refusal` gives for
> its own placement: the shape is emitted by a door in `runtime/` and decoded by
> a client in `src/ccf/client`, and `src/` cannot import `runtime/`. Putting it
> beside the types it carries is what lets the emission and the decode agree
> **by construction** rather than by two implementations being written to the
> same paragraph.*

That argument is now doubly true, because `C-06` makes emission and decode the
*same shape*. Three placements were evaluated:

| Option | Import edges introduced | Verdict |
|---|---|---|
| **A.** `door.py` imports `WireRequest` from `ccf.client.wire`; `DoorOutcome` grows `request` + `content_address`; `ccf.client.wire.WireOutcome` becomes an alias | `ccf.products → ccf.client` (**new, reversed**) | Works — **experimentally verified, no import cycle** (see below) — but reverses the established direction. `ccf.client.wire` already imports `ccf.products.refusal`; `ccf.client.adapters.mcp_stdio` already imports `ccf.products.door`. |
| **B. (recommended)** `WireRequest` **and** the one outcome shape are *defined* in `src/ccf/products/door.py`; `ccf.client.wire` re-exports both under their existing names | none — `ccf.client → ccf.products` (existing), `runtime → ccf.products` (existing) | No new edge in either direction. `ccf.client.wire.WireRequest` and `.WireOutcome` stay importable at their published names, so `__all__` is unchanged and the surface manifest keeps its entries. |
| **C.** `runtime/` doors import `WireOutcome` from `ccf.client.wire` | `runtime → ccf.client` (**new**) | A *door* importing the *client* package is the wrong sentence. `runtime/` imports nothing from `ccf.client` today (measured). |

**Import-cycle experiment (option A, the risky one), run and reverted:**
`from ccf.client.wire import WireRequest` was inserted into `src/ccf/products/door.py`,
then each of `ccf.products.door`, `ccf.client.wire`, `ccf.client`,
`ccf.client.adapters.mcp_stdio`, `ccf.client.adapters.inprocess` and
`ccf_runtime.mcp.egress` was imported **first** in a fresh subprocess. All six
imported cleanly; the file was restored byte-identically. So option A is safe
*today* — but it is safe only because `ccf/client/__init__.py:80-82` imports
nothing that reaches `door.py`, and `tests/invariants/test_cold_import.py`
exists precisely because that kind of accident is invisible in a warm
interpreter. `[VERIFIED: subprocess cold-import probe, this session]`

**Under option B the surface manifest still drifts** — `docs/surface/v0.2-surface.json:1060`
records `WireOutcome.request` as `"<class 'ccf.client.wire.WireRequest'>"`, which
becomes `ccf.products.door.WireRequest`. That is fine and expected: this phase
must file a `docs/surface-changes/19-*.md` fragment regardless (§9.4).

### 2.3 The shared door entry — the minimal shape, and the `C-02` mechanism

`door.py` already ships two producer-side helpers with exactly the right
posture: `served_answer(resolved)` (`:197-234`) and
`door_refusal(resolved, *, asked, product_class, version)` (`:237-319`). Both
take *what the resolver returned* plus *what the door already resolved*, and
neither touches a clock, an entitlement or a transport. The new entry belongs
beside them.

**Minimal shape (recommended):**

```python
# src/ccf/products/door.py  — algorithmic (CINV-03), no clock, no I/O
def door_answer(
    resolved: object,
    *,
    asked: WireRequest,        # what the door PARSED off its own wire
    request: ProductRequest,   # the typed question it actually resolved
    product_class: str,
    version: str,
) -> bytes:
    """The canonical bytes a door puts on an envelope-carrying wire."""
```

It returns `canonical_bytes(DoorOutcome(request=asked, product_json=…,
content_address=…, replay_ref=…, refusal=…))`, calling the existing
`door_refusal` and `served_answer` internally, and computing
`content_address` from **the same `canonical_bytes(...)` call** that produced
`product_json` — the "serialize once" discipline `canonical_response` records
(`routes/__init__.py:145-160`) and `inprocess._encode:435-440` already
implements.

**Why `asked` is a separate parameter from `request`.** This is the `C-02`
mechanism. `ProductRequest.asked_at` is a **required, non-null** `datetime`; a
`WireRequest.temporal_boundary` may be `None`, and `C-02` requires `None` to be
echoed as `None`. The two are different facts and must not be derived from each
other. The door resolves the answer against `request.asked_at`; it echoes
`asked` verbatim.

**Where `asked` comes from, per transport:**

- **`mcp+stdio`** — `C-07` says *"the request is encoded too, and a producer-side
  door entry decodes it."* The recommended reading: the client encodes its
  `WireRequest` with `canonical_bytes` and passes it as **one additional tool
  argument** (a JSON string, or the object — see §3.3), and the door
  `WireRequest.model_validate_json`s it. The door then derives `product_class`
  and `parameters` **from the decoded request**, so there is exactly one source
  for those and no second rendering that nothing reads (`C-03`'s concern).
  `asked_at` stays a separate required argument — it is the *resolved* instant
  the door answers at, which is a different fact from the as-asked boundary.
- **`inprocess`** — the adapter encodes the `WireRequest` to bytes and hands
  those bytes to the in-process door, which decodes them. This is `C-07`'s whole
  point and `C-14`'s accepted cost. Round-trip fidelity is **verified**: see §6.
- **HTTP** — see §4.

**Who reads the clock.** `door.py` is `__ccf_mode__ = "algorithmic"` and must
stay so, so `as_of=None → now` cannot move into it. It stays in the caller
(`mcp_stdio.py:218-220`, `inprocess.py:377`) or moves into the `runtime/` MCP
door. Moving it to the door would *also* make `ProductClient.ask`'s existing
promise — *"the producing deployment answers against its own clock"* — true for
the first time; that is an attractive adjacent fix but is **`C-13` scope
pressure**, and the planner should note it and not take it unless it falls out
for free.

### 2.4 What existing conformance legs already pin about `C-02`

`tests/client/conformance/suite.py::assert_decision_instant_is_auditable`
asserts, for a question asked with `as_of=None`:

```
if served.temporal_boundary is not None:
    raise AssertionError(f"`{subject.name}` echoed a temporal boundary for a
        question that named none — `Result.temporal_boundary` is the echo of
        the question, and a transport filling it in has answered a question
        the caller did not ask")
```

`Result.temporal_boundary` comes from `outcome.request.temporal_boundary`
(`client.py:219`). **So `C-02` is already enforced by a currently-green
conformance leg over both real transports.** A design that had the door echo the
resolved instant would turn that leg red. This is strong, existing, mechanical
support for the §2.3 recommendation. `[VERIFIED: suite.py read; ci-core green at HEAD]`

Separately, and not to be conflated: `RefusalEnvelope.request.temporal_boundary`
is filled from `asked.asked_at` (`door.py:317`) — the **resolved** instant — and
the same leg *requires* it to be non-`None` on a refusal. `C-04` leaves
`RefusalEnvelope.request` untouched, which is exactly right, but a plan that
"unified" the two identities would break this leg.

---

## 3. The one-shape constraint (`C-06`) against the MCP door

### 3.1 What is emitted today

`runtime/ccf_runtime/mcp/egress.py:788-799`:

```python
if refusal is not None:
    return canonical_bytes(
        DoorOutcome(product_json=None, replay_ref=None, refusal=refusal)
    ).decode("utf-8")
answer = served_answer(resolved)
return canonical_bytes(
    DoorOutcome(
        product_json=canonical_bytes(answer.product).decode("utf-8"),
        replay_ref=answer.replay_ref,
        refusal=None,
    )
).decode("utf-8")
```

The tool's declared return type is `str`; FastMCP delivers it as a single
`TextContent` block.

### 3.2 What `_decode` does to it today, and what must go

`mcp_stdio.py:443-490` — the transcoding step, in full:

1. `DoorOutcome.model_validate_json(text)` (`:466`)
2. build a **new** `WireOutcome` with `request=request` from its own argument
   (`:476`, `:483`) — **the defect**
3. compute `content_address=sha256(outcome.product_json.encode("utf-8"))`
   (`:485-487`) — **the second defect**

Under `C-05`+`C-06` the whole method **disappears**. `ask` becomes:

```python
return asyncio.run(self._call(...)).encode("utf-8")
```

…and `_call` (`:368-441`) is unchanged: it already returns exactly one piece of
text and already raises `TransportError` for `isError`, for a dead pipe, and for
`len(spoken) != 1` (`:425-440`). Note `_call`'s existing check *"a door emits
exactly one — the canonical bytes of its outcome, and never a second rendering
beside them"* is already written for this world.

The malformed-bytes `TransportError` currently raised at `_decode:468-473` moves
to `decode_outcome`'s equivalent (`codec.py:296-301`), which says the same thing
in the same words. That is a **narrowing** of the message (it loses the
`{SCHEME}` and `{program}` context) — the planner should decide whether to keep
a thin adapter-level well-formedness check for the diagnostic, or accept the
generic message. Keeping one is *not* a transcoding step (it parses and discards)
but it is a place a future adapter could grow one; recommend accepting the
generic message.

### 3.3 MCP-protocol constraints — measured against `mcp==1.28.1` (installed)

| Concern | Finding |
|---|---|
| Text vs binary | The tool returns `str` → `TextContent`. **Raw bytes cannot be returned** as a tool result without base64, which `wire.py:50-53` explicitly rejects (*"a base64 or nested-JSON envelope … would put a second rendering of the vessel on the wire"*). **The wire stays text; the adapter does `.encode("utf-8")` at the seam.** This is not a "bytes pass-through" in the literal sense — it is a *text* pass-through that the adapter encodes without inspecting. That still satisfies `C-06`: there is no transcoding of the *shape*. |
| Byte fidelity of `str` → JSON-RPC → `str` → `.encode("utf-8")` | Safe. `canonical_bytes` uses `ensure_ascii=False` (`canonical.py:189`), so non-ASCII rides raw; JSON-RPC escapes and unescapes it losslessly. Canonical bytes are UTF-8-decodable by construction. |
| Nested escaping | `product_json` is a JSON *string member* inside the envelope, so the vessel is escaped once by the envelope's `json.dumps` and unescaped once on parse. `tests/crossproc/test_mcp_egress.py:1142` already asserts the recovered `product_json` equals the producer's bytes exactly. The address recompute is over the **inner** text, so the outer envelope's byte-identity is irrelevant. |
| Size limits | None imposed by stdio framing in `mcp==1.28.1`. The envelope grows by one `WireRequest` (three small members) and a 64-char hex address. Negligible. |
| Structured content | FastMCP would also accept a Pydantic return type and emit `structuredContent`. **Do not.** That is a second rendering and `_call:434-440` already refuses more than one text block. |
| `isError` | Unchanged. A raised governance refusal still arrives as `isError` and still becomes a `TransportError` (`mcp_stdio.py:425-433`), per the boundary `D-IMPL-148` Addendum A drew and `tests/mcp/test_egress_refusal_envelope.py` asserts. |

### 3.4 The new tool argument

Adding one argument to `PRODUCT_REQUEST_TOOL` is a **wire-compatibility break**
for any client that is not this adapter. The tool's own docstring
(`egress.py:672-676`) argues all four §6.3 axes are required *"which makes a
partial address unrepresentable rather than refused"* — that reasoning applies
to the encoded request too: make it **required**, not optional. A deployment
that adopted the tool pre-Phase-19 breaks; state that in the `D-IMPL` entry
alongside the out-of-tree-adapter ruling.

---

## 4. The HTTP reconciliation (`C-09`)

### 4.1 The exact serialization path

`runtime/ccf_runtime/http_api/routes/__init__.py:209-213`:

```python
body = canonical_bytes(payload)
headers = {CONTENT_ADDRESS_HEADER: hashlib.sha256(body).hexdigest()}
if replay_ref is not None:
    headers[REPLAY_REF_HEADER] = replay_ref
return Response(content=body, media_type=_JSON, headers=headers)
```

One `canonical_bytes` call, one digest derived from it. `canonical_response` has
**five** call sites (`agent.py:74`, `config.py:98`, `replay.py:47`,
`replay.py:65`, `product.py:192`) — the docstring enumerates them at `:189-192`.
Only the product route has a request to echo.

### 4.2 How the echo header is added without breaking "serialize once"

The echo is **not derived from `body`**, so it introduces no second
serialization of the payload. It is a second, independent serialization of a
*different* object (the `WireRequest`), which is exactly what `REPLAY_REF_HEADER`
already is (a string that came from elsewhere). Recommended signature:

```python
def canonical_response(
    payload: object,
    *,
    replay_ref: str | None = None,
    asked: WireRequest | None = None,   # new, keyword-only, defaulting to None
) -> Response:
```

with `headers[REQUEST_ECHO_HEADER] = canonical_bytes(asked).decode("utf-8")`
when `asked is not None`. The four non-product call sites pass nothing and are
untouched — the same pattern and the same justification `:198-207` already gives
for `replay_ref`'s default (*"means there is no reference to publish, and the
header is then absent rather than empty"*).

**Header value form.** Canonical JSON in an HTTP header is legal (header values
are opaque octets in practice) but contains `"` and may contain non-ASCII, which
RFC 9110 discourages in field values. Two options for the planner:

| Form | Pro | Con |
|---|---|---|
| Canonical JSON verbatim | one rendering; a future adapter does `WireRequest.model_validate_json(header)` | non-ASCII / control chars in a header value; some proxies mangle |
| base64url of the canonical bytes | header-safe on every intermediary | a second rendering, which `wire.py:50-53` rejected for the *vessel* — but the argument there was about the **content address becoming a function of the envelope**, which does not apply to a request echo (nothing hashes it) |

**Recommendation: base64url**, with the reasoning recorded, because the vessel
argument does not transfer and header-safety is a real property. Either way, a
future HTTP adapter reconstructs the echo by decoding the header — never from
its own state, which is the `C-09` sentence the planner must write down.

### 4.3 Header name

Existing constants: `CONTENT_ADDRESS_HEADER = "X-CCF-Content-Address"` (`:48`),
`REPLAY_REF_HEADER = "X-CCF-Replay-Ref"` (`:67`). The convention is
`X-CCF-<Title-Cased-Hyphenated>`. Candidates consistent with it:
**`X-CCF-Request-Echo`** (recommended — names what it *is*, matches `check_outcome`'s
vocabulary of "the echo"), `X-CCF-Asked`, `X-CCF-Request`. Declare it as a
`Final[str]` constant beside the other two, with the same
`#:`-comment discipline (`:41-67`) and the same note that the four reasons for
choosing `X-CCF-*` over a standard header apply unchanged and are not restated.

### 4.4 The case the planner must rule on

`_asked(...)` (`product.py:283-419`) returns **`None`** when a caller supplies
none of the four axes — *"the positive assertion this caller asked for the
class's standing answer and posed no question of their own."* There is then no
question to echo, and the header must be **absent**, on exactly the
`REPLAY_REF_HEADER` reasoning (*"Stamping an empty header would make 'no record
was named' and 'the record is named by nothing' the same observation"*,
`:64-66`). Say so in the constant's comment.

Also note: the HTTP door's `asked_at` is **required whenever any axis is
supplied**, so the HTTP echo's `temporal_boundary` is never `None` when it
exists. That is self-consistent with `C-02` (the HTTP surface has no way to
express *defer to the server*), and a future HTTP adapter must send an explicit
instant. Worth one sentence in the docstring so the asymmetry with `mcp+stdio`
is recorded rather than discovered.

---

## 5. Producer-claimed content address

### 5.1 Where it must be computed

Today both adapters hash the bytes they are about to pass on:
`inprocess.py:439` and `mcp_stdio.py:485-487`. Both must be **deleted** and the
computation must move producer-side, into the shared `door.py` entry (§2.3),
derived from the *same* `canonical_bytes(answer.product)` call that produces
`product_json`.

`inprocess._encode:435-440` is already exactly the right code in exactly the
wrong place:

```python
vessel = canonical_bytes(outcome.product)
… product_json=vessel.decode("utf-8"),
  content_address=hashlib.sha256(vessel).hexdigest(),
```

Move that pair verbatim into `door.py`. This is a transplant, not a design.

### 5.2 `canonical_bytes` is the single shared serializer — confirmed

- `src/ccf/contracts/canonical.py::canonical_bytes` (`:194`) is the only
  serializer; `content_hash` (`:229`) is `sha256(canonical_bytes(obj))`.
- `canonical_response` deliberately does **not** call `content_hash`, to avoid a
  second serialization (`routes/__init__.py:149-155`), and the equivalence is
  asserted in `tests/http_api/test_content_address_header.py` (5 tests).
- `tests/client/test_codec.py::test_the_recomputed_address_is_the_vessels_own_content_hash`
  asserts `sha256(product_json.encode("utf-8")) == content_hash(vessel)`.

### 5.3 What producer/consumer canonicalization drift actually looks like

The consumer **never re-canonicalizes** — it hashes the received *text*. So the
comparison detects:

- ✅ corruption or truncation of `product_json` in transit
- ✅ a re-serializing intermediary (any re-render changes the bytes, not the claim)
- ✅ mis-routing that swaps a vessel for another producer's
- ✅ a producer whose stated address disagrees with its own bytes (its own bug)
- ✅ producer/consumer **contract** drift — separately, via the third check
  (`ContextProductContract.model_validate_json`, `codec.py:254-261`), which
  `codec.py:81-84` already correctly records as unaffected by `B0`
- ❌ a producer that *consistently* mis-canonicalizes (it would state a matching
  address for its own wrong bytes). That case is caught by cross-adapter parity
  and by the contract check, not by this comparison.
- ❌ an adversary with envelope write access — `C-10`, explicitly out of scope.

The narrower-true-sentence `C-10` demands must say exactly this, and no more.

---

## 6. `_parameters_survive_the_wire` becomes load-bearing — measured, and it holds

`src/ccf/client/wire.py:142-177` (validator) + `:75-107` (`_unstable_parameter`).
Admissible set: `None`, `bool`, `int`, `str`, `Mapping` with `str` keys, `list` —
recursively. Everything else is refused **at construction**, with a message
naming the wire-stable spelling.

**Empirical round-trip probe run this session**
(`WireRequest → canonical_bytes → model_validate_json → ==`):

| Value | Result |
|---|---|
| `{"a": 1}` | admitted, **equal** |
| nested `{"a": {"b": [1, "x", True, None]}}` | admitted, **equal** |
| `{}` (empty) | admitted, **equal** |
| `2**70` (big int) | admitted, **equal** |
| `MappingProxyType({...})` | admitted (pydantic coerces to `dict` at construction), **equal** |
| `IntEnum` / `StrEnum` member | admitted, **equal** (decodes to base type; `IntEnum(5) == 5`) |
| `temporal_boundary` with microseconds | **equal** (`_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"` preserves all 6 digits, `canonical.py:72`) |
| `temporal_boundary` with a non-UTC offset | **equal** (normalized to UTC; `datetime` equality is instant-based) |
| `temporal_boundary=None` | **equal** (`None` stays `None`) |
| `float`, `Decimal`, `datetime`-in-parameters, `set`, `tuple`, `bytes`, non-`str` dict key (incl. nested) | **refused at construction** |

**Conclusion: there is no gap.** Every value the guard admits round-trips to a
value equal to itself, so no admissible question can produce a false echo
failure. The four candidate gaps named in the research brief are all closed:
float and `Decimal` are refused; `datetime` in `parameters` is refused;
`set`/`tuple` are refused; nested dict **key ordering** is irrelevant because
Python `dict` equality is order-independent and `sort_keys=True` normalizes the
rendering anyway. `[VERIFIED: probe script, this session]`

**Two things the planner must nonetheless do:**

1. **Add a control that the guard is what prevents the false failure.** Today
   `tests/client/test_wire.py` (13 tests) proves the guard *refuses* bad values.
   Nothing proves that admitting one would produce a `TransportError` on a
   healthy wire — which is the guard's stated reason for existing
   (`wire.py:147-162`). With the echo live, that is now demonstrable: construct
   an outcome whose echo carries a `Decimal`-rendered-as-text parameter and show
   `check_outcome` raises. `CLNT-12` requires it.
2. **`consume.py:32-35` already carries the guard's reasoning in a comment**
   (`"int, not float: WireRequest refuses a float because canonical JSON renders
   it as text, so the decoded echo would differ from what was sent and the
   cross-check would report a healthy wire as failed"`). That comment becomes
   *true of the shipped path* for the first time in this phase — a one-word
   prose amendment (it currently describes a hypothetical), not a rewrite.

---

## 7. Conformance-suite mechanics for `C-12`

### 7.1 How adapters are registered

`tests/client/conformance/suite.py:111-128`:

```python
@dataclass(frozen=True, kw_only=True)
class AdapterSubject:
    name: str
    connect: AdapterFactory          # Callable[[Path], TransportAdapter]
    break_transport: AdapterFactory
```

Subjects are module-level tuples: `test_inprocess_conformance.py:76-82` defines
`SUBJECTS`; `test_mcp_conformance.py:85-90` defines `MCP` and
`SUBJECTS = (*IN_PROCESS, MCP)`. Every leg takes `Sequence[AdapterSubject]`,
`provision: Provision`, and a `Question`. The `provision` fixture
(`conformance/conftest.py:31-…`) hands out one fresh deployment root per call,
counter-first, with the stdio server copied into the root's **parent**.

`suite.py` **names no transport** and this is asserted:
`test_the_suite_fires.py:933-953` walks `suite.py`'s AST for any string constant
that is a key of `SCHEME_REGISTRY`. **The new tamper legs must not name a
transport, a product id, or a parameter** — the latter two also because
`no-hardcoding` lints `tests` (`tools/lints/__main__.py:124`).

### 7.2 The byte-corrupting decorator, given a bytes seam

Because the seam returns bytes, the decorator is **fully generic and transport-blind** —
which is precisely `C-12`'s argument. Recommended shape, living in `suite.py`:

```python
class _Tampering:
    """A transport that answers correctly and then edits the bytes."""
    def __init__(self, inner: TransportAdapter, edit: Callable[[bytes], bytes]) -> None:
        self._inner, self._edit = inner, edit
    def ask(self, request: WireRequest) -> bytes:
        return self._edit(self._inner.ask(request))
```

Two edits, both of which keep the bytes **well-formed** so the failure is
attributable to the integrity check rather than to the parser — the same
discipline `test_codec.py::_encode_dropping_replay_ref` already states
(*"a saboteur producing undecodable bytes would prove the parser fires, not the
comparison"*):

- **crossed echo:** `decode → model_copy(request=<a different WireRequest>) → encode_outcome`.
  The "different question" must be derived, not spelled — e.g. flip one admitted
  parameter value read off the deployment's own request contract, or replace
  `product_id` with `product_id + "-crossed"`. Deriving keeps `no-hardcoding` green.
- **altered vessel:** `decode → model_copy(product_json=<edited text>) → encode_outcome`,
  leaving `content_address` at the producer's value. The edit must change the
  bytes without changing JSON validity — appending a space inside the JSON text
  is sufficient and is *not* a contract violation, so the failure lands on the
  address check rather than on the third check.

Note the decorator uses `encode_outcome` — the shipped encoder — rather than a
private copy, matching `test_codec.py`'s stated rule that *"a control that
re-implements the comparison proves only that the copy fires."*

### 7.3 Asserting the two legs generically

```python
def assert_a_crossed_echo_is_caught(subjects, *, provision, question) -> None: ...
def assert_an_altered_vessel_is_caught(subjects, *, provision, question) -> None: ...
```

Each leg must do **three** things per subject, mirroring
`assert_wire_failure_parity`'s three-part structure (`suite.py:575-641`):

1. the tampered subject raises `TransportError` and produces **no** `Result`
   (refused or otherwise);
2. the tampering adapter is of the **same type** as the healthy one *or* wraps
   it — `assert_wire_failure_parity` enforces `type(broken) is type(healthy)`;
   the wrapper form cannot satisfy that, so state the weaker check explicitly
   (the wrapper's `_inner` is the subject's own `connect(root)`) rather than
   silently dropping it;
3. the **untampered** subject on the same question does **not** raise — without
   which "everything raises" passes the leg. This is the vacuity guard, and it
   is the project's single most-repeated lesson.

Additionally assert the exception **message discriminates**: `match="different question"`
for the echo leg and `match="content address"` for the vessel leg, so the two
legs cannot pass on each other's failure. Both strings already exist in
`codec.py:238` and `:172`.

### 7.4 Is it additive? Yes, and the precedent is on record

`D-GATE-18`'s zero-diff claim was *"binding a new **adapter** changes nothing in
`suite.py`"* — a claim about adapters, not about properties. `C-12` states this
explicitly. The existing subjects are untouched: both new legs take the same
`SUBJECTS` tuples and the same `provision` fixture, and neither leg changes an
existing one. `test_inprocess_conformance.py` and `test_mcp_conformance.py` each
gain **two** call lines (8 → 10 collected each).

**The controls on the controls** belong in `test_the_suite_fires.py`, which
already runs each leg over a deliberately divergent subject and asserts it
fails. Add: hand each new leg an **honest** subject (no tampering) and assert it
raises `AssertionError` — i.e. the leg notices that the tamper was *not* caught.
That is what makes the leg itself non-vacuous.

---

## 8. The single-transport falsification requirement (`C-11`)

### 8.1 The hostile adapter — it already almost exists

`tests/client/conformance/test_the_mcp_binding_fires.py:57-70`:

```python
class _AnswersAnotherQuestion(McpStdioAdapter):
    def ask(self, request: WireRequest) -> WireOutcome:
        answered = super().ask(
            request.model_copy(update={"parameters": OTHER_PARAMETERS})
        )
        return answered.model_copy(update={"request": request})   # ← line 69
```

This is a **genuine crossed-question wire**: a real child process, real pipes,
the real door, question B asked while the client asked A. Line 69 is the
re-label that makes the client's echo check pass — and under a bytes seam that
line is **unwritable**. Delete it and the control becomes:

```python
class _AnswersAnotherQuestion(McpStdioAdapter):
    def ask(self, request: WireRequest) -> bytes:
        return super().ask(request.model_copy(update={"parameters": OTHER_PARAMETERS}))
```

…driven through the real `ProductClient`, asserting `TransportError` with
`match="different question"`. **One transport, one client, no parity diff.**
That is the phase's success sentence, discharged.

The same class applied to `InProcessAdapter` gives the second single-transport
subject, and the in-process one is the important one — it is the transport
`C-07` exists to make live and the one every quickstart uses.

For the **altered-vessel** half, the hostile adapter edits the returned bytes
(the vessel text) without restating the address. Same wrapper, different edit.

### 8.2 Where these live

**Not** in `src/ccf/client/adapters/` — a module there registers a scheme at
import (`SCHEME_REGISTRY[SCHEME] = …`, `inprocess.py:445`, `mcp_stdio.py:493`)
and would become a shipped adapter, and would also drift the public-surface
manifest.

**Recommended:** beside the existing controls, in
`tests/client/conformance/` — a new module named for what it proves, e.g.
`test_a_crossed_question_is_caught_on_one_transport.py`. The existing files
`test_the_suite_fires.py`, `test_the_mcp_binding_fires.py`,
`test_the_fixture_serves_a_replay_reference.py` establish the naming convention
(*a sentence about the property*), and their module docstrings establish the
required framing: *"Nothing in `src/` or `runtime/` is edited and reverted, and
nothing here re-implements an assertion."*

Both subjects (in-process and `mcp+stdio`) should be exercised, but the
assertion is **per subject** — each raises on its own, so neither leg needs the
other and the proof is not a comparison.

### 8.3 The codec-level byte-sabotage leg

`tests/client/test_codec.py` already has the *model-level* versions:

- `test_an_echo_naming_a_different_question_is_a_transport_failure` (`:206-217`)
- `test_the_decoder_recomputes_the_address_and_refuses_a_wire_that_disagrees` (`:182-188`)

Both `model_copy` **then** `encode_outcome`, so the bytes are internally
consistent except for the one deliberately-wrong member. `C-11` asks for
something strictly stronger: **hand `decode_outcome` bytes that were tampered
with after encoding.**

```python
raw = encode_outcome(a_served_outcome())
tampered = raw.replace(b'"companies"', b'"compan1es"')   # inside product_json
with pytest.raises(TransportError, match="content address"):
    decode_outcome(tampered, sent=a_request())
```

That is a true post-encoding byte edit, it leaves the envelope well-formed, and
it fires the address check rather than the parser. Add the echo twin the same
way. Both are pure functions with no fixtures — cheap, deterministic,
single-transport by construction (there is no transport at all).

`test_codec.py:238-244` already parametrizes five malformed-wire cases including
a truncation — those prove the *parser* fires and are the right neighbours for
the new legs.

---

## 9. Prose obligations — every file, with line numbers

### 9.1 `src/` — amend, never delete

| File | Lines | What must change |
|------|-------|------------------|
| `src/ccf/client/codec.py` | **44–84** | The whole *"…and the shipped adapters reconstruct"* block. **Keep it**; append the dated correction that the follow-on landed, what the checks now detect, and what they still do not (`C-10`'s narrower true sentence). |
| | **62–69** | The standing constraint paragraph (*"until the follow-on phase lands, this SDK must not be described as…"*) — **replaced by the narrower true sentence, not deleted**. |
| | **71–79** | *"No shipped adapter calls it"* — now false. Amend with the measurement that it is the shipped path. |
| | **30–42** | The original *"cross-checked, not reconstructed"* argument — **unchanged**, and say so. |
| | **145–151, 160–167** | `verify_content_address` — the `B0` paragraph and the `Raises:` caveat *"Not reachable from any shipped adapter today"*. |
| | **189–199, 204–214, 226–234** | `check_outcome` — the `D-11` reference at `:192`, the *"Two of the three checks are inert"* block, and the `Raises:` *"Only the last of the three is reachable"*. |
| | **283–292** | `decode_outcome`'s `Raises:` — the pointer at the follow-on phase. |
| `src/ccf/client/wire.py` | **1–57** | Module docstring — *"the whole of what a transport must implement"* under a new signature. |
| | **235–254** | `WireOutcome` class docstring, incl. the `D-11` framing at `:235` and the content-address sibling argument at `:244-254` (which stays true and gains the producer-mints-it fact). |
| | **256–274** | `request` and `content_address` attribute docs — both carry the `B0` correction verbatim and both must be amended. |
| | **320–343** | `TransportAdapter` Protocol docstring + `ask` signature and `Raises:`. |
| | **147–162** | `_parameters_survive_the_wire` — the guard's stated reason becomes live (§6). |
| `src/ccf/client/client.py` | **36–42** | *"`D-11` types the adapter seam as returning a `WireOutcome` object rather than bytes"* — the sentence this phase falsifies. |
| | **176–179** | `ask`'s `Raises:` for `TransportError` — the wording is already correct and becomes true. |
| | **188–214** | `_result_from` docstring, esp. `:196-201` (*"only safe because `check_outcome` has just proven the two equal"*) — now genuinely load-bearing. |
| `src/ccf/client/adapters/inprocess.py` | **15–36** | The `D-13` *"it serializes live objects anyway"* section — extend to the question half (`C-07`, `C-14`). |
| | **406–419** | `_encode` docstring — the address claim moves producer-side. |
| `src/ccf/client/adapters/mcp_stdio.py` | **98–101** | *"It returns a `WireOutcome`…"* |
| | **443–464** | `_decode` docstring — the method goes away. |
| | **45–69** | The tool-argument table — gains a row for the encoded request. |
| `src/ccf/products/door.py` | **1–64** | Module docstring, esp. **37–47** (the vessel-as-text argument, which stays) and **49–60** (the sibling argument, which now covers two siblings). |
| | **114–141** | `DoorOutcome` class docstring + members. |
| `src/ccf/client/__init__.py` | **46, 66** | The `D-11` / adapter-author-surface paragraphs. |
| `src/ccf/client/adapters/__init__.py` | **1, 4** | Names the `TransportAdapter` Protocol and `D-11`. |

### 9.2 `runtime/`

| File | Lines | What must change |
|------|-------|------------------|
| `runtime/ccf_runtime/mcp/egress.py` | **673–701** | *"What this tool returns is a `DoorOutcome` and no longer the bare vessel"* — extend, do not rewrite. |
| | **702–711** | *"The vessel is still not re-serialized, and that claim is now stated at the level it is true"* — must stay true and must now also cover the producer-minted address. |
| | **655–671** | The `parameters` argument prose — a second source of `product_class`/`parameters` (the encoded request) must be reconciled here. |
| `runtime/ccf_runtime/http_api/routes/__init__.py` | **131–208** | `canonical_response` — **`D-IMPL-126`'s four `ETag` reasons stand verbatim** (`C-09`); the *"each surface publishes the same sibling values through whatever channel it actually has"* sentence at `:186-192` is the hook the echo header hangs on; `:189-192` enumerates five call sites and must be re-counted if a signature changes. |
| | **41–67** | The two `#:` constant comments — the new one follows their form exactly. |
| `runtime/ccf_runtime/http_api/routes/product.py` | **60–70** | The sibling-asymmetry paragraph. |
| | **283–419** | `_asked` — the `None` case now also means *no echo header* (§4.4). |

### 9.3 `docs/` and `.planning/`

| File | Lines | What must change |
|------|-------|------------------|
| `docs/superpowers/specs/2026-08-15-ccf-client-design.md` | **121–160** (§5, `D-11`), **270–290** (§12 item 4), **401** (Amendment 1 effect table) | Needs an **Amendment 2** in Amendment 1's style (a dated, ruled block appended at the end), not an edit of §5. Amendment 1 sets the precedent at `:290+`. |
| `.planning/REQUIREMENTS.md` | **201** | `CLNT-05` — the seam signature. Amend the text, keep the `D-11` citation, add the amending decision id. |
| `.planning/ROADMAP.md` | **1644** | Cites `client.py:172`; the true line is **`client.py:186`**. Stale already. (`client.py` is an ambiguous basename — `src/ccf/client/client.py` and `src/ccf/mcp/client.py` — so the citation lint *drops* it as unchecked; it is stale prose, not a red gate.) |
| | **44**, **1651–1673** | The Phase 19 bullet and detail section carry the whole defect statement; the ROADMAP's Progress table needs a Phase 19 row on close. |
| `docs/DECISIONS.md` | append | **Next free id is `D-IMPL-156`** (155 is the highest; `D-GATE-18.1` is the last entry, line 470). Append-only — the file is `HISTORICAL_RECORDS`-exempt from the citation lint (`tools/lints/citations.py:172-178`) precisely because entries are never edited. Expect at least: the `C-01`…`C-14` ratification, the `D-11` amendment, the `CLNT-05` amendment, the out-of-tree-adapter ruling, and `D-GATE-19`. |
| `.planning/phases/18-…/18-CLOSE-REVIEWS.md` | **56–82** | `B0`'s `⚠ STATUS: DEFERRED` block. Per §3.1 it *"stays visible as deferred rather than closed"* until this phase lands; on close it should be marked closed **by appending**, with `A5` (`:195-205`) explicitly left open. |
| `examples/hw1-companies-over-revenue/README.md` | — | **Makes no tamper claim today** (checked: every `address` mention is about *reproducibility*, `:78-81`, `:134`, `:184`). Nothing must be deleted. Optionally add the narrower true sentence. |
| `examples/hw1-companies-over-revenue/consume.py` | **32–35** | The `int`-not-`float` comment describes a hypothetical that becomes real (§6). One-word amendment; watch the **80-line budget gate** (`CLNT-14`) — the file is currently 80 lines including the shebang-less docstring, so **do not add a line**. Verify against `tools/` budget gate before editing. |

### 9.4 Gates that will fire on prose/surface changes

| Gate | Command | Why it fires |
|------|---------|--------------|
| Public-surface drift | `tests/test_surface_drift.py` (inside `make test`) | `docs/surface/v0.2-surface.json` records `ccf.client.wire`'s `__all__` and each export's *shape* string (`:1042-1060`). A retyped `TransportAdapter.ask`, a moved `WireRequest`, or a new `door.py` export drifts it. **Remedy: a `docs/surface-changes/19-*.md` fragment naming every moved module** — the gate accepts documented drift. |
| Surface-changes assembly | `make surface-changes` → `tools/assemble_surface_changes.py` | Fragments must carry all seven fields (`Surface`, `Public surface`, `Change type`, `Before`, `After`, `Why`, `Migration`). **`D-IMPL-155`: a misnamed fragment is silently dropped** — name it `19-NN-<slug>.md`, numeric prefix first. |
| Citation drift | `make lint` → `tools/lints/citations.py` | Gated trees include `.planning` (excluding `.planning/phases/*`), `docs` (excluding `DECISIONS.md`, `PHASE_*.md`, the whitepaper), `src`, `runtime`, `tests`, `examples`, `public`. **Currently exit 0.** Risk is `cite02-anchor`: an anchored citation whose named symbol moves. `codec.py`, `wire.py`, `door.py` are unique basenames and therefore *checked*; `client.py` and `product.py` are ambiguous and therefore *dropped*. Re-run `make lint` after every prose wave. |
| `no-hardcoding` over `tests` | `make lint` | New controls must derive product ids and parameter names from deployment documents. |
| `mypy --strict` | `make typecheck` | `files = ["src", "runtime"]` only — **test annotations are not checked**, so a stale `-> WireOutcome` in a test does not fail the gate. Do not rely on mypy to find test breakage. |
| OpenAPI drift | `tests/http_api/test_openapi.py` | A new response *header* does not appear in the OpenAPI schema unless declared; if the plan declares it, regenerate with `make openapi`. |

---

## 10. Regression surface — measured

**Baseline at HEAD:** `pytest --collect-only -q` → **4027 collected**
(`D-GATE-18.1` recorded 3909 passed / 118 skipped at `04cccc2`; the tree is
unchanged since).

Per-module collected counts, measured this session:

```
tests/client                                   374
tests/client/conformance                        69
  test_the_suite_fires.py                       44
  test_inprocess_conformance.py                  8
  test_mcp_conformance.py                        8
  test_the_mcp_binding_fires.py                  3
  (+ the two other control modules)
tests/client/test_codec.py                      34
tests/client/test_binding.py                    25
tests/client/test_surface.py                    19
tests/client/test_inprocess_adapter.py          17
tests/client/test_mcp_stdio_adapter.py          17
tests/client/test_client.py                     16
tests/client/test_wire.py                       13
tests/mcp/test_egress_refusal_envelope.py       12
tests/mcp/test_egress_parameters.py             11
tests/crossproc/test_mcp_egress.py              38
tests/http_api/test_content_address_header.py    5
```

**Direct breakage estimate: 50–95 tests**, i.e. **1.2–2.4% of the suite**,
concentrated as follows:

- `test_client.py` — **all 16**. Its module docstring at `:11` is *about* the
  object seam; five stub adapters and two helper constructors must be rewritten.
- `test_the_suite_fires.py` — **~25–35 of 44**. Every `Mutation` (`:83`) becomes
  a bytes edit; `_remint` (`:111`), `_move_the_expiry` (`:178`),
  `_move_only_the_address` (`:199`), `_drop_the_refusal_key` (`:237`),
  `_misreport_the_anchor` (`:593`) all `model_copy` a `WireOutcome`.
  `_Swallowing` (`:359-374`) must synthesize a refusal **as bytes**, which is
  slightly harder and is worth its own task.
- `test_the_mcp_binding_fires.py` — **all 3**, and two of them become the phase's
  own controls (§8.1).
- Everything else — **≤ 10 combined**.

**Counts that should MOVE UP** and must be accounted for in the close-gate
arithmetic (the project's discipline is *every increment traces to a specific
finding*): two conformance legs × two bound subjects = **+4**; the
single-transport controls = **+2 to +6**; the codec byte-sabotage legs = **+2 to
+4**; the `_parameters_survive_the_wire` liveness control = **+1**; the
controls-on-the-controls in `test_the_suite_fires.py` = **+2**. Expect the suite
to finish around **4038–4048**.

**Cheap verification commands for the planner's tasks:**

```bash
.venv/bin/python -m pytest tests/client -q                    # 374, the fast inner loop
.venv/bin/python -m pytest tests/client/conformance -q        # == `make conformance`, 69
.venv/bin/python -m pytest tests/mcp tests/crossproc tests/http_api -q
make ci-core                                                  # lint + typecheck + test + gate-tools
```

---

## Validation Architecture

> Test framework detected: **pytest**, config in `pyproject.toml:141-152`
> (`testpaths = ["tests"]`, markers include `conformance` and `crossproc`).
> Runner: `.venv/bin/python` with `PYTHONPATH=src:runtime` (`Makefile:10-11`).
> **Never `python` bare — it does not exist on this host.**

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (+ `pytest-benchmark` for the perf extra, not used here) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`:141`) |
| Quick run command | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client -q` (374 tests, seconds) |
| Wave-merge command | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client tests/mcp tests/crossproc tests/http_api -q` |
| Full suite command | `make ci-core` (= `lint typecheck test gate-tools`) |
| Phase gate | `make ci` exit 0 (`ci-core` + `examples` + `docs-strict` + `gate-tools`) |

### The phase's deliverable **is** that a check can fail — so the properties are the checks

**Property 1 — a transport that answered a different question is detected, by a single-transport client.**

| | |
|---|---|
| **Property** | `ProductClient.ask` raises when the outcome's producer-minted echo does not equal the `WireRequest` that was sent. |
| **Sabotage** (`CLNT-12`, `D-22`) | A hostile in-repo adapter subclassing the **shipped** adapter, which asks the **real** door question B while the client asked A, and returns the door's bytes **unmodified** (§8.1). Written in the same plan as the assertion. |
| **Observation** | `pytest.raises(ccf.client.errors.TransportError, match="different question")` and **no `Result` produced at all** — refused or otherwise. `TransportError` is the `D-10` taxonomy's *"the wire never spoke"*; it must not be `BindingError` (a subclass — assert the exact type where the distinction matters) and must never be a refusal value. |
| **Single-transport?** | ✅ One `ProductClient`, one adapter, one deployment. No second subject exists in the assertion, so the phase's success sentence is discharged without the parity diff. Run for **both** subjects independently — two single-transport proofs, never one two-subject proof. |
| **Vacuity guard** | The same subject, untampered, on the same question, must **not** raise. Without it, "everything raises" passes. |
| **Control on the control** | Hand the assertion an honest adapter and assert it fails (`test_the_suite_fires.py` discipline). |

**Property 2 — a vessel that does not match the address its producer computed is detected, by a single-transport client.**

| | |
|---|---|
| **Property** | `ProductClient.ask` raises when `sha256(product_json)` ≠ the address the producer stated in the envelope. |
| **Sabotage** | (a) a hostile adapter that edits the vessel text in the returned bytes and leaves the claimed address alone; (b) codec-level: `decode_outcome(tampered_bytes, sent=…)` where the tamper is a **post-encoding byte edit** inside `product_json` (§8.3). |
| **Observation** | `pytest.raises(TransportError, match="content address")`. The message names both the claimed and the recomputed digest (`codec.py:171-176`), so assert on `match="content address"` and not on a digest value. |
| **Single-transport?** | ✅ (a) is one client, one adapter. (b) has no transport at all — it is a pure function over bytes. |
| **Vacuity guard** | Untampered bytes through the same path must decode cleanly and return a served `Result`. |
| **Discrimination guard** | The tampered bytes must stay **well-formed and contract-valid**, so the failure is attributable to the address check and not to the parser (`codec.py:296`) or the contract check (`codec.py:254`). Appending whitespace inside the vessel's JSON text achieves this. |

**Property 3 — the seam cannot be bypassed by the next adapter (`C-12`).**

| | |
|---|---|
| **Property** | Every subject registered in the conformance suite has demonstrably live integrity checks. |
| **Sabotage** | The generic byte-corrupting decorator in `suite.py` (§7.2), applied to each registered `AdapterSubject`. Generic because the seam is bytes — an adapter author writes nothing and cannot opt out. |
| **Observation** | Per subject: `TransportError` from the client, with the discriminating message; **and** the honest subject not raising. |
| **Single-transport?** | ✅ Each leg iterates subjects and asserts **per subject**; no cross-subject comparison anywhere in either leg. |
| **Neutrality guard** | `test_the_suite_fires.py:933-953` must stay green — the new legs may not contain any string that is a `SCHEME_REGISTRY` key, nor (per `no-hardcoding` over `tests`) a spelled product id or parameter name. |

**Property 4 — the guard that prevents *false* failures is what is preventing them (§6).**

| | |
|---|---|
| **Property** | `WireRequest._parameters_survive_the_wire` is why a healthy wire is not reported as broken. |
| **Sabotage** | Construct an outcome whose echo carries a parameter the guard refuses (e.g. a `Decimal` rendered as text) and show the shipped `check_outcome` raises on a wire that worked. |
| **Observation** | `TransportError` with `match="different question"` on a *healthy* exchange — which is the exact false-positive the guard's docstring (`wire.py:147-162`) says it exists to prevent. |
| **Single-transport?** | ✅ pure codec-level. |

**Property 5 — `C-02`'s as-asked temporal echo (regression, already pinned).**

`suite.assert_decision_instant_is_auditable` already asserts
`served.temporal_boundary is None` for a question asked with `as_of=None`, over
**both** real transports. This leg is the existing, currently-green mechanical
guard on `C-02` and **must stay green** — it is the tripwire on the §2.3 design
choice. No new test needed; name it in the plan's must-haves so a red is
attributed correctly.

### Requirements → Test Map

| Decision | Behavior | Test type | Automated command | Exists? |
|---|---|---|---|---|
| `C-01`,`C-03`,`C-04` | producer mints the echo; total `WireRequest` equality; one comparison covers served **and** refused | unit | `pytest tests/client/test_codec.py -q` | ⚠️ partial — refused-half echo leg is new |
| `C-02` | `as_of=None` echoes `None` | conformance | `pytest tests/client/conformance -q -k decision_instant` | ✅ exists, must stay green |
| `C-05`,`C-08` | seam returns bytes; `decode_outcome` on the shipped path | unit + type | `pytest tests/client -q`; `make typecheck` | ❌ Wave 0 — the retype itself |
| `C-06` | `_decode` has no transcoding step | source assertion | AST/source check that the adapter builds no outcome object | ❌ new — recommend an AST gate mirroring `test_surface.py::count_result_construction_sites` |
| `C-07` | in-process is a degenerate wire in **both** directions | unit | `pytest tests/client/test_inprocess_adapter.py -q` | ⚠️ `:295-336` asserts the answer half; the question half is new |
| `C-09` | HTTP publishes the echo as an `X-CCF-*` sibling; absent when no question was posed | unit | `pytest tests/http_api/test_content_address_header.py tests/http_api/test_routes.py -q` | ❌ new |
| `C-10` | the claim in prose matches what the code detects | docs/lint | `make lint` (citations), human read at close | ❌ new prose |
| `C-11` | single-transport falsification | conformance control | `pytest tests/client/conformance -q -k crossed` | ❌ new (one deleted line from existing) |
| `C-12` | tamper legs on every registered adapter | conformance | `make conformance` | ❌ new |
| `CLNT-06` | one `Result` construction site survives | AST gate | `pytest tests/client/test_surface.py -q` | ✅ exists |
| `CLNT-14` | `consume.py` purity + budget | AST gate | `make ci` examples job | ✅ exists, must stay green |

### Sampling Rate

- **Per task commit:** `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client -q`
- **Per wave merge:** `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client tests/mcp tests/crossproc tests/http_api -q` **and** `make lint`
- **Phase gate:** `make ci` exit 0, with the test count reconciled against the
  4027 baseline and **every increment traced to a named finding** (the
  `D-GATE-18` / `D-GATE-18.1` discipline).

### Coverage claim — stated precisely

| Axis | Covered |
|---|---|
| Transports | `inprocess` **and** `mcp+stdio` — both as conformance subjects (generic legs) and as single-transport controls. HTTP has **no client adapter**, so the `C-09` header is verified producer-side only; state that limit rather than implying client-side coverage. |
| Door types | Served **and** refused, by one comparison — `C-04` puts the echo at outcome level, and `check_outcome:236` runs the comparison **before** the `product_json is None` branch at `:245`, so a refusal is covered by construction with no second assertion. **Verify this ordering survives the refactor** — moving the echo check below the branch would silently uncover the refusal half. |
| `WireRequest` equality axes | All three — `product_id`, `parameters`, `temporal_boundary` — by total model equality (`C-03`). No projection, no field selection. |
| `temporal_boundary` | `None` stays `None` (`C-02`), pinned by an existing conformance leg; aware instants round-trip across offsets and microseconds (verified, §6). |
| `parameters` | Every admissible type round-trips equal (verified, §6); every inadmissible type is refused at construction, so no admissible question can produce a false failure. |
| **Not covered, and said so** | An adversary with envelope write access (`C-10`, out of scope); two *identical* in-flight questions crossing (accepted knowingly at discussion Q1); a producer that consistently mis-canonicalizes (§5.3). |

---

## Conflicts With Locked Decisions

**None that make a locked decision technically impossible.** One decision has a
mechanism dependency that the planner must resolve deliberately, and it is
flagged here at full volume because getting it wrong ships a false
`TransportError` on the most common call in the SDK:

### ⚠ `C-02` × `C-07` × the MCP tool's required `asked_at`

- `C-02` requires: client sends `as_of=None` → echo carries `temporal_boundary=None`.
- `C-01` requires: the echo is filled from what the **door** resolved and answered.
- Today, **both adapters resolve `None` → `datetime.now(UTC)` client-side**
  (`mcp_stdio.py:218-220`, `inprocess.py:377`), so the door never learns that
  `None` was sent.
- The MCP tool's `asked_at` is a **required** argument and its docstring argues
  at length (`egress.py:672-676`) that all four §6.3 axes are required so *"a
  partial address is unrepresentable rather than merely refused."*

**A door that echoes only what it parsed from today's tool arguments would echo
a concrete instant, and every `as_of=None` ask would raise a false
`TransportError`** — the exact false-failure class `_parameters_survive_the_wire`
exists to prevent, one field over. The existing conformance leg
`assert_decision_instant_is_auditable` would go red, correctly.

**`C-07`'s own wording resolves it** — *"the request is encoded too, and a
producer-side door entry decodes it and echoes what it parsed."* If the encoded
`WireRequest` crosses as its own argument, the door parses `temporal_boundary=None`
and echoes it faithfully, while `asked_at` stays the resolved instant the door
answers at. No locked decision moves. This is the recommended reading (§2.3).

**Two adjacent facts worth a checkpoint, not a ruling:**

1. `ProductClient.ask`'s docstring (`client.py:139-141`) says *"the producing
   deployment answers against its own clock."* **That is false today on both
   transports** — the *client* reads the clock. This phase does not have to fix
   it, and `C-13` says stay narrow. But the phase's own prose must not restate
   the false sentence, and if the encoded request carries `None` to the door,
   moving the clock read to the door falls out nearly for free. **Surface it to
   the user; do not take it unilaterally.**
2. The `mcp+stdio` tool gaining a required argument is a **wire-compatibility
   break** for any non-SDK consumer of `PRODUCT_REQUEST_TOOL`. Same class of
   ruling as the out-of-tree-adapter question already at planning's discretion;
   recommend ruling both in one `D-IMPL` entry.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Serializing the outcome envelope | a second `json.dumps` in the door | `ccf.contracts.canonical.canonical_bytes` | The one canonical form. `wire.py:17-53` records at length why a second rendering is the one thing to prevent. |
| Computing the content address | `content_hash(product)` inside the door | `hashlib.sha256(vessel).hexdigest()` over the **same** `canonical_bytes` call that produced `product_json` | `canonical_response:149-155` — `content_hash` serializes *and* hashes, so calling it is the second serialization. |
| Comparing the echo | a field-by-field comparison | `outcome.request != sent` (`codec.py:236`) | `C-03`: total equality, no projection. A projection is how a field stops being compared without going red. |
| Refusing an unstable parameter | a new validator | `WireRequest._parameters_survive_the_wire` (`wire.py:142-177`) | Already correct and now load-bearing (§6). |
| Building a hostile adapter | a from-scratch fake transport | subclass or wrap the **shipped** adapter | `test_the_mcp_binding_fires.py:9-16` and `test_codec.py:7-12` both state the rule: a control that tests a copy proves the copy fires. |
| Corrupting bytes | hand-rolled JSON string surgery for the *model-level* legs | `decode → model_copy → encode_outcome` | Keeps the bytes well-formed so the failure is attributable. (The *post-encoding* byte edit in §8.3 is deliberately different and is the stronger leg.) |
| A refusal shape for the swallowing control | a synthesized `RefusalEnvelope` | capture a real one from the deployment | `test_the_suite_fires.py:376-393` — *"a synthesized `kind` would name a refusal vocabulary the fabric does not speak."* |
| Test vocabulary | spelled product ids / parameter names | read them from the deployment's own documents | `no-hardcoding` lints `tests` (`tools/lints/__main__.py:124`); `test_inprocess_conformance.py:41-55` is the pattern. |

---

## Common Pitfalls

### Pitfall 1: the echo check moves below the refusal branch
`check_outcome:236` runs the echo comparison **before** `if outcome.product_json is None: return None` at `:245`. That ordering is the entire mechanism by which `C-04` covers a refusal with one comparison. A refactor that reorders it uncovers the refusal half silently — no test goes red today, because no refusal-echo control exists yet. **Add that control in the same plan.**

### Pitfall 2: a compatibility shim re-opens the bypass
Any `ask` that accepts *either* bytes or a `WireOutcome` restores `D-11`'s permission, and an adapter taking the object branch reconstructs the echo again with every gate green. This is the failure mode `C-05` exists to prevent. Break cleanly.

### Pitfall 3: the tamper decorator corrupts bytes into unparseability
An edit that breaks JSON validity fires `decode_outcome`'s parser (`codec.py:296-301`), not the integrity check — the control then proves the parser fires. `test_codec.py:270-274` already names this trap. Assert on the discriminating message.

### Pitfall 4: "everything raises" passes the new legs
`assert_wire_failure_parity:634-641` already carries the antidote (a healthy refusal must **not** raise). Every new leg needs the same third assertion.

### Pitfall 5: parity is asked to do the single-transport job
Adding the crossed-question control to a parity leg satisfies nothing — parity is blind by construction to a check broken identically on both subjects, which is how `B0` survived Phase 18. The assertion must be `pytest.raises(TransportError)` from **one** `ProductClient`, not `pytest.raises(AssertionError)` from a suite leg.

### Pitfall 6: the surface manifest goes stale silently
`tests/test_surface_drift.py` is **module-granular and direction-blind** — once any fragment names `ccf.client.wire`, later drift in that module is claimed for the rest of the phase, *including a removed export*. Name every moved module in the fragment, and regenerate `docs/surface/v0.2-surface.json` with `make surface` at the phase's last wave.

### Pitfall 7: a misnamed surface fragment is dropped with no red gate
`D-IMPL-154` / `D-IMPL-155`, both minted at `D-GATE-18.1`. `tools/retirement_sweep.py --report` **rewrites a tracked file** despite the flag name, and a fragment whose filename does not match `[0-9]*-*.md` is silently excluded from the assembled document. Name fragments `19-NN-<slug>.md` and `git diff` after every tooling run.

### Pitfall 8: parallel agents on one working tree
`MEMORY.md` and the Phase 18.1 orchestrator note: sabotage-running agents dispatched in parallel onto one tree observe each other's mutations and read them as tampering. This phase is **all sabotage**. Run controls serially, or in isolated trees that do not edit `.planning/`.

### Pitfall 9: the ROADMAP / STATE writers corrupt their files
`MEMORY.md`: every `state.*` and `roadmap.*` SDK writer drops fields whether it reports success or failure. **Hand-edit `.planning/` files.**

---

## Code Examples

### The producer-side entry (recommended shape)

```python
# src/ccf/products/door.py  — algorithmic (CINV-03)
def door_answer(
    resolved: object,
    *,
    asked: WireRequest,        # decoded from the wire, echoed verbatim (C-01, C-02)
    request: ProductRequest,   # the typed question this door resolved
    product_class: str,
    version: str,
) -> bytes:
    refusal = door_refusal(
        resolved, asked=request, product_class=product_class, version=version
    )
    if refusal is not None:
        return canonical_bytes(
            DoorOutcome(request=asked, product_json=None,
                        content_address=None, replay_ref=None, refusal=refusal)
        )
    answer = served_answer(resolved)
    vessel = canonical_bytes(answer.product)          # serialized ONCE
    return canonical_bytes(
        DoorOutcome(
            request=asked,
            product_json=vessel.decode("utf-8"),
            content_address=hashlib.sha256(vessel).hexdigest(),
            replay_ref=answer.replay_ref,
            refusal=None,
        )
    )
```
*Transplanted from `inprocess.py:435-440` (the serialize-once pair) and
`egress.py:788-799` (the two-branch structure). Source: both files, read at HEAD.*

### The seam, after `C-08`

```python
# src/ccf/client/wire.py
class TransportAdapter(Protocol):
    def ask(self, request: WireRequest) -> bytes: ...

# src/ccf/client/client.py
def ask(self, parameters, as_of=None) -> Result:
    request = WireRequest(product_id=self._product_id,
                          parameters=parameters, temporal_boundary=as_of)
    return self._result_from(
        decode_outcome(self._adapter.ask(request), sent=request), sent=request
    )
```
*`decode_outcome` already calls `check_outcome` internally (`codec.py:303`), so
the three checks run exactly once and `Result` is still constructed in exactly
one place — `CLNT-06`'s AST gate stays green.*

### The MCP adapter, after `C-06`

```python
# src/ccf/client/adapters/mcp_stdio.py — _decode is DELETED
def ask(self, request: WireRequest) -> bytes:
    declared = self._declared()
    arguments = { ... , "request": canonical_bytes(request).decode("utf-8")}
    return asyncio.run(
        self._call(declared.program, declared.document.root, arguments)
    ).encode("utf-8")
```
*`_call` (`:368-441`) is unchanged and already refuses `isError`, a dead pipe,
and more than one text block.*

### The single-transport control (`C-11`), from one deleted line

```python
class _AnswersAnotherQuestion(McpStdioAdapter):
    def ask(self, request: WireRequest) -> bytes:
        return super().ask(request.model_copy(update={"parameters": OTHER_PARAMETERS}))

def test_a_crossed_question_is_caught_by_one_client(provision):
    client = ProductClient(product_id=QUESTION.product_id,
                           adapter=_AnswersAnotherQuestion(str(provision("crossed"))))
    with pytest.raises(TransportError, match="different question"):
        client.ask(parameters=QUESTION.parameters, as_of=QUESTION.as_of)
    # vacuity guard — the honest adapter on the same question does NOT raise
    honest = ProductClient(product_id=QUESTION.product_id,
                           adapter=McpStdioAdapter(str(provision("honest"))))
    assert not honest.ask(parameters=QUESTION.parameters, as_of=QUESTION.as_of).refused
```
*Derived from `test_the_mcp_binding_fires.py:57-70` with line 69 removed.*

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python venv | everything | ✅ | `.venv/bin/python` (3.12) | none — bare `python` does not exist on this host |
| pytest | all tests | ✅ | via `dev` extra | — |
| mypy | `make typecheck` | ✅ | `files = ["src","runtime"]` | — |
| `mcp` | `mcp+stdio` adapter + egress | ✅ | **1.28.1** (matches the version the door's prose cites) | — |
| pydantic v2 | every contract | ✅ | — | — |
| `tools/lints` | `make lint` | ✅ | exit **0** at HEAD | — |
| `gh` / CI token | reading CI status | ❌ | — | `MEMORY.md`: Dave runs `~/ci_diag2.py` and pastes output |
| Cross-AI panel CLIs (`codex`, `cursor`, `gemini`) | §3.1 close | ⚠️ unverified this session | — | `MEMORY.md`: codex reviews nothing at exit 0 when bwrap fails; gemini fabricates symbols; inline the source for codex |
| External substrate servers (Postgres/Neo4j/Mongo/Fluree) | not needed | n/a | — | this phase touches none |

**No missing dependency blocks execution.**

---

## State of the Art

| Old | Current | When changed | Impact |
|---|---|---|---|
| Adapter builds `WireOutcome` (`D-11`) | Adapter returns bytes (`C-05`/`C-08`) | This phase | `decode_outcome` moves onto the shipped path; the echo becomes unforgeable by an adapter. |
| `DoorOutcome` (3 members) ≠ `WireOutcome` (5 members), adapter transcodes | One shape (`C-06`) | This phase | The transcoding step — the site of the defect — is deleted, not policed. |
| Client resolves `as_of=None → now` | *(unresolved — see Conflicts)* | — | `ProductClient.ask`'s clock sentence is currently false on both transports. |
| MCP tool: 8 arguments | 9, incl. the encoded request | This phase | Wire-compatibility break for non-SDK tool consumers. |
| HTTP: 2 `X-CCF-*` siblings | 3 (`C-09`) | This phase | `D-IMPL-126`'s ruling extended, not amended. |

**Deprecated by this phase:** `McpStdioAdapter._decode`, `InProcessAdapter._encode`,
and `D-11`'s permission for an adapter to construct the outcome object.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Option B (define both shapes in `door.py`, re-export from `ccf.client.wire`) is the right placement | §2.2 | A different placement is workable; option A was experimentally proven cycle-free. Low risk — this is a recommendation, not a measurement. |
| A2 | base64url is the right HTTP echo header encoding | §4.2 | Cosmetic; either form works. The planner may rule the other way. |
| A3 | The tamper decorator should live in `suite.py` rather than in each binding module | §7.2 | `C-12` says *"the suite wraps each registered adapter"*, which is explicit. Low risk. |
| A4 | Breaking out-of-tree adapters cleanly (no shim) | §1.5 | Explicitly a discretion item; the reasoning is recorded so the user can rule otherwise. |
| A5 | 50–95 tests break — the upper bound on `test_the_suite_fires.py` (~25–35 of 44) is estimated from reading, not from running a mutated tree | §10 | The number could be higher. The *files* are enumerated exactly; only the per-file split is estimated. |
| A6 | FastMCP's stdio framing imposes no practical size limit on the enlarged envelope | §3.3 | Not measured against a large vessel. The envelope grows by ~200 bytes, so risk is negligible, but a plan that also ships a large-payload example should measure it. |

---

## Open Questions

1. **Does the clock read move to the door?**
   - Known: both adapters read the clock today; `ProductClient.ask`'s docstring says the deployment does; the encoded-request design makes moving it nearly free.
   - Unclear: whether that is `C-13` scope creep.
   - Recommendation: **checkpoint for the user.** Do not take it unilaterally; do not restate the false sentence either way.

2. **Does `PRODUCT_REQUEST_TOOL` gain an argument or change shape?**
   - Known: adding a required argument breaks non-SDK consumers; the tool's own docstring argues required-together is strictly stronger than optional.
   - Recommendation: add it required, rule it in the same `D-IMPL` entry as the adapter break.

3. **Is `check_outcome` still separately exported once `decode_outcome` is the only path?**
   - Known: it is in `codec.__all__:112` and in the surface manifest; the conformance controls and `test_codec.py` reach it directly.
   - Recommendation: keep it exported — removing it would drift the surface for no gain and would take a control's handle away.

4. **Does the phase add an AST gate proving no adapter constructs the outcome (`C-06`'s "no transcoding step")?**
   - Known: `CLNT-06`'s `count_result_construction_sites` is the exact pattern, already written and controlled.
   - Recommendation: yes — a type change is enforced by mypy over `src`/`runtime` only, and an out-of-tree adapter is invisible to both. An AST gate over `src/ccf/client/adapters/` is cheap and closes the "next adapter" clause of the ROADMAP's scope list.

---

## Sources

### Primary (HIGH confidence — read at HEAD `192c79d`, this session)
- `src/ccf/client/codec.py`, `wire.py`, `client.py`, `adapters/inprocess.py`, `adapters/mcp_stdio.py`, `binding.py`, `__init__.py`
- `src/ccf/products/door.py`, `refusal.py` (`RequestIdentity`), `src/ccf/contracts/canonical.py`
- `runtime/ccf_runtime/mcp/egress.py`, `runtime/ccf_runtime/http_api/routes/__init__.py`, `routes/product.py`
- `tests/client/conformance/suite.py`, `conftest.py`, `test_inprocess_conformance.py`, `test_mcp_conformance.py`, `test_the_suite_fires.py`, `test_the_mcp_binding_fires.py`, `test_the_fixture_serves_a_replay_reference.py`
- `tests/client/test_codec.py`, `test_client.py`, `test_wire.py`, `test_surface.py`, `test_inprocess_adapter.py`, `test_mcp_stdio_adapter.py`
- `tools/lints/citations.py`, `tools/lints/__main__.py`, `tools/dump_surface.py`, `tools/assemble_surface_changes.py`, `tests/test_surface_drift.py`, `tests/invariants/test_cold_import.py`
- `docs/DECISIONS.md` (`D-IMPL-151` at `:458`, `D-GATE-18` at `:460`, `D-GATE-18.1` at `:470`)
- `docs/superpowers/specs/2026-08-15-ccf-client-design.md` §5, §6, §7.1, §8, §12, Amendment 1
- `.planning/phases/18-…/18-CLOSE-REVIEWS.md` (`B0` at `:56-82`, `A5` at `:195-205`)
- `.planning/ROADMAP.md` (`:44`, `:1629-1673`), `.planning/REQUIREMENTS.md` (`:197-218`, `:341-362`), `.planning/STATE.md`
- `CLAUDE.md` §2.2, §3.1, §6.4, §7.1, §7.3, §11
- `pyproject.toml` `[tool.pytest.ini_options]`, `[tool.mypy]`; `Makefile`

### Measurements taken this session (HIGH)
- `pytest --collect-only -q` → 4027 collected; 12 per-module counts
- `python -m tools.lints --all` → **exit 0**
- `WireRequest` round-trip probe over 19 parameter/boundary shapes → no admissible value drifts
- Cold-import probe with `door.py → ccf.client.wire` inserted and reverted → 6/6 modules import first, no cycle
- `SCHEME_REGISTRY` → `['inprocess', 'mcp+stdio']`
- `pip show mcp` → 1.28.1
- `grep -rn "from ccf.client" runtime/` → empty (no `runtime → ccf.client` edge today)

### Not consulted, deliberately
- Context7 / WebSearch / external package registries. **This phase installs no
  packages and adds no dependency**, so the Package Legitimacy Gate does not
  apply. Every fact needed is in the tree.

---

## Metadata

**Confidence breakdown:**
- Blast radius (§1): **HIGH** — enumerated by `grep` over the whole tree, counts measured with `--collect-only`.
- Wire/door design (§2–§5): **HIGH** on the constraints and the measured state; **MEDIUM** on the specific placement recommendation (option B), which is a judgement over three workable options.
- `_parameters_survive_the_wire` (§6): **HIGH** — empirically probed, no gap.
- Conformance mechanics (§7–§8): **HIGH** — the machinery was read in full and the control is one deleted line from existing code.
- Prose obligations (§9): **HIGH** on the file/line enumeration; **MEDIUM** on which gates fire (citation lint behaviour on ambiguous basenames is derived from reading the checker, not from a mutation run).
- Regression estimate (§10): **MEDIUM** — files exact, per-file split estimated (A5).

**Research date:** 2026-08-19
**Valid until:** until any of `codec.py`, `wire.py`, `door.py`, `client.py`, the two adapters, `egress.py`, `routes/__init__.py` or `tests/client/conformance/` changes. All line numbers are HEAD `192c79d`.
