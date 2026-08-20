---
phase: 19
kind: close-review
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-08-20T05:45:00Z
reviewed: shipped code at 920c171..e734b7a (NOT the plans — those were reviewed pre-execution)
prompt_bytes: 202061
---

# Cross-AI CLOSE Review — Phase 19

Per CLAUDE.md §3.1, this panel reviewed the **shipped code**, not the plans. The plans
had two pre-execution plan-checker rounds; that review stands and is recorded separately.
Written to a distinct file so the pre-execution review survives.

`claude` was skipped for independence (the review ran from Claude Code). The prompt
inlined 202KB of line-numbered source — `wire.py`, `codec.py`, `client.py`, both
adapters and `door.py` in full, plus the MCP cross-check region, the HTTP echo region,
and the single-transport control file — because Codex's sandbox cannot create user
namespaces on this host and would otherwise review nothing at exit 0.

The panel was given the five already-known findings and told **not** to re-derive them.

## Verification verdicts (orchestrator, against the tree)

Every finding below was checked against the tree before being recorded. Findings naming
symbols that do not exist are marked REJECTED — FABRICATION.

| # | Finding | Reviewers | Verdict |
|---|---------|-----------|---------|
| **A** | `wire.py::TransportAdapter.ask` docstring claims an adapter "cannot construct the outcome" — it can; relabeling the echo defeats **both** checks | codex, cursor, ollama (3/4) | **CONFIRMED — demonstrated empirically** |
| **B** | `codec.py` "the residual is the `None` path and only the `None` path" generalizes from the MCP door; in-process has no equivalent cross-check or measurement statement | cursor | **CONFIRMED (prose scope)** |
| **C** | `codec.py::decode_outcome` docstring still says the client "runs again" — stale post-`C-05` | cursor | **CONFIRMED** |
| D | HTTP `_echo` violates `C-02` / breaks `as_of=None` | gemini | **REJECTED as stated** — forward-looking note only |
| E | `check_outcome` refusal early-return skips the address guard | ollama | **REJECTED** — validator forbids the shape |
| F | Hash recomputed on decoded text not canonical bytes | ollama | **ADVISORY** — hypothetical, not a current defect |
| G | `check_outcome` / `verify_content_address` error messages omit received values | gemini | **ADVISORY** — diagnostics quality |
| H | `_McpMovesTheDoorsInstant` staticmethod forwarding | ollama | **REJECTED — FABRICATION** (cited file does not exist) |
| I | `_alter_the_vessel` brace-index fragility | ollama | **REJECTED — FABRICATION** (cited file does not exist) |

## Finding A — the consensus finding, demonstrated

Three of four reviewers converged independently. `src/ccf/client/wire.py::TransportAdapter.ask`
states:

> an adapter that cannot construct the outcome cannot fill the echo from the request it
> was handed, so `check_outcome`'s comparison has an operand the client did not supply.

**The antecedent is false.** `WireOutcome is DoorOutcome` is public (`wire.py`), and
`encode_outcome` is public and in `codec.__all__`. An adapter can parse the producer's
bytes, `model_copy(update={"request": sent})`, re-encode, and return bytes — satisfying
`ask(WireRequest) -> bytes` exactly.

**Measured out-of-tree, nothing tracked edited** (`scratchpad/probe/relabel3.py`), with
two deliberately DIFFERENT vessels so a pass is attributable:

```
A. forward B's bytes unchanged, client asked A  -> TransportError raised   (check is live)
B. relabel B's echo to A, vessel stays B's,
   address left honest for B                    -> *** NO RAISE ***        (both checks pass)
C. honest A, client asked A                     -> no raise                (control)
```

Leg B serves **B's vessel under A's identity** with no error. Leg A proves the check is
not simply dead. A first version of this probe was VACUOUS — legs B and C produced
byte-identical outcomes — and was discarded and rebuilt; that vacuity is recorded here
because it is the same defect class the phase is about, occurring in the verification
code written to test it.

**Scope, stated precisely.** `19-05`'s AST gate (`C-17`) covers `src/ccf/client/adapters/`,
so an **in-tree** adapter doing this goes red. The gate's narrowness was Dave's explicit
ruling and is not in question. What is in question is that the **docstring's claim is
unscoped** — it asserts an inability that does not hold for the out-of-tree adapters the
Protocol exists to admit.

**Why this matters more than its severity suggests:** this is a false claim about an
integrity check, in shipped source, in the phase whose entire subject is claims matching
what the code does. It is the same species as the sentence this phase corrected.

## Finding B — the residual's scope

`codec.py` says a concrete `as_of` "crosses twice … and the MCP door cross-checks the two
and refuses a disagreement by name", then concludes "The residual is the `None` path and
only the `None` path."

Verified: `runtime/ccf_runtime/mcp/egress.py` does cross-check. `src/ccf/client/adapters/inprocess.py`
computes `asked_at = request.temporal_boundary or datetime.now(UTC)` and passes it to
`_door` as a separate argument; `_door` never compares the two. On the **shipped**
in-process adapter they cannot disagree (one is derived from the other), so this is not
an exploitable hole on the shipped path — but the prose generalizes a property established
for one door to both.

The honest form already exists elsewhere in this phase: the HTTP door's `_echo` says the
cross-check "has no subject here … a cross-check would compare a value with itself. Its
absence is a measurement, not an exemption." In-process lacks the equivalent sentence.

## Finding C — a stale docstring

`codec.py::decode_outcome` says the last three checks "are `check_outcome`, which the
client runs **again** on whatever an adapter returns." Verified: `client.py` contains no
call to `check_outcome` — only `decode_outcome`, once. `client.py` handles the same
amendment correctly, keeping the superseded paragraph and marking it amended; `codec.py`
does not.

## Rejected findings, and why

- **D (gemini, HIGH).** `_echo` does set `temporal_boundary=asked.asked_at`, so the
  citation is real — but the failing scenario is not established: the route's `asked_at`
  is `datetime | None = None`, no HTTP **client adapter** ships, and nothing consumes the
  header through `check_outcome` today. Recorded as a forward-looking constraint on
  whoever writes that adapter, not as a present defect.
- **E (ollama).** `door.py` validator rejects `content_address is not None` on a refusal,
  and `codec.py` marks the follow-on guard `# pragma: no cover - validator forbids`. The
  scenario ("`decode_outcome` succeeds") is impossible — `model_validate` raises first.
- **H, I (ollama).** Both cite `test_a_crossed_question_is_caught_over_the_mcp_transport.py`
  and `test_a_crossed_question_is_caught.py`. **Neither file exists.** The real file is
  `test_a_crossed_question_is_caught_on_one_transport.py`. Fabricated citations.

## Reviewer reliability, this run

- **codex** — grounded, one finding, correct, and the sharpest statement of it. The
  inlined-source workaround held.
- **cursor** — strongest on breadth: three findings, all three confirmed, plus a long
  and accurate "checked and NOT defects" section that correctly declined to re-derive
  the known items.
- **gemini** — grounded this time (a change from Phase 18, where 4 of 5 findings were
  fabrications), but its one HIGH is overstated.
- **ollama** — mixed: converged on Finding A correctly, then produced two findings citing
  files that do not exist. Consistent with prior runs: verify everything.

---

# Raw reviews

## Codex Review

## Summary
Phase 19 does make the two checks capable of failing on the shipped `inprocess` and `mcp+stdio` paths: `ProductClient.ask` decodes adapter-returned bytes through `decode_outcome`, `check_outcome` compares the parsed echo to `sent`, and `verify_content_address` hashes received `product_json` against the producer’s claimed address. The main residual I see is not in those shipped adapters, but in the “unbypassable seam” claim: the Python surface still permits a new adapter to synthesize canonical `DoorOutcome` bytes from the caller’s request, recreating the Phase 18 vacuity while satisfying `ask(...) -> bytes`.

## Findings

### 1. Public bytes seam still allows adapter-side outcome reconstruction — MEDIUM
**Where:** `src/ccf/client/wire.py:133` `TransportAdapter.ask`; `src/ccf/client/client.py:100` `ProductClient.__init__`; `src/ccf/products/door.py:292` `DoorOutcome`; `src/ccf/client/codec.py:203` `encode_outcome`

**Why it is wrong:** The prose says an adapter “cannot construct the outcome” because the seam returns `bytes`, but the shipped API still exposes everything needed for an adapter to construct `DoorOutcome` and encode it. `ProductClient` accepts any structural adapter at line 100, and the only formal requirement is `ask(self, request: WireRequest) -> bytes` at line 133. Since `DoorOutcome` is public at line 292 and `encode_outcome` is public at line 203, a new adapter can build a valid outcome object from the `request` it was handed, encode it, and return bytes. That satisfies the typed seam while recreating the original “object compared with itself” failure mode.

**Failing scenario:** A future HTTP adapter receives `request`, calls a server or local helper for only `product_json`, computes `sha256(product_json)`, constructs `DoorOutcome(request=request, product_json=..., content_address=..., ...)`, and returns `encode_outcome(...)`. `ProductClient.ask` then calls `decode_outcome(..., sent=request)` at `src/ccf/client/client.py:228-230`; `check_outcome` at `src/ccf/client/codec.py:358` compares the adapter-filled echo to the same request object, and `verify_content_address` at `src/ccf/client/codec.py:267-275` compares a digest the adapter computed from the same bytes. Both checks are green for the wrong reason. The existing single-transport controls subclass or wrap shipped adapters, but nothing in the inlined source would catch this new adapter pattern.

## Checked and NOT defects
- `check_outcome` runs the request echo comparison before returning on refusal at `src/ccf/client/codec.py:358-368`; a crossed refusal is still caught rather than silently accepted.
- The altered-vessel tests include a discrimination guard at `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py:497-529`, so those controls do not merely prove malformed JSON or contract validation fires.
- The declared `as_of=None` residual is preserved in prose and in a live test at `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py:342-378`.
- The MCP concrete temporal-boundary check compares the encoded request’s boundary to the separate `asked_at` argument at `runtime/ccf_runtime/mcp/egress.py:852-864`, so that path is not just relying on the client echo check.
- `door_answer` uses one vessel serialization for both `product_json` and `content_address` at `src/ccf/products/door.py:656-662`; I do not see a second producer-side rendering there.

## Risk Assessment
MEDIUM — the shipped adapters and the named controls appear to exercise live checks, but the seam is not structurally unbypassable for future adapters. The phase fixed the current implementations; it did not make reconstruction impossible at the public Python API boundary.

---

## Cursor Review

## Summary

Phase 19 does make `check_outcome` and `verify_content_address` capable of failing on the shipped path: adapters return producer `bytes`, `decode_outcome` parses producer-minted `request` / `content_address`, and the single-transport controls exercise real `ProductClient` refusals with discriminating wording. The phase is not a full structural lock against reconstruction, though — a new adapter can still rewrite the echo from the `WireRequest` it was handed, and in-process still lacks the concrete-`as_of` door cross-check that MCP has, so the “residual is `as_of=None` only” claim is too strong.

`★ Insight ─────────────────────────────────────`
Typed `ask(...) -> bytes` removes the *convenient* B0 path (adapters no longer return a built outcome), but it does not make echo identity a cryptographic or CI-enforced property — only an opaque pass-through convention.
`─────────────────────────────────────────────────`

## Findings

### 1. Echo reconstruction is still expressible on the bytes seam — HIGH
**Where:** `src/ccf/client/wire.py:133` `TransportAdapter.ask` · `src/ccf/client/codec.py:358` `check_outcome` · `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py:104` `_InProcessAnswersAnotherQuestion.ask`

**Why it is wrong:** The Protocol only constrains the return type to `bytes`. An adapter may still parse those bytes, set `request` from the argument it was handed, and re-`encode_outcome`. Then `outcome.request != sent` compares two values the adapter aligned on purpose, so the echo check cannot fail — the same defect class as B0, one layer later. `wire.py:136-138` overclaims that “an adapter that cannot construct the outcome cannot fill the echo”; construction is still possible via `DoorOutcome` / `model_copy` / `encode_outcome`. The shipped crossed-question controls only change what is **asked of the door** (`super().ask(request.model_copy(...))`), so the producer’s echo honestly says B; they never sabotage by **relabeling** a B outcome’s echo back to A.

**Failing scenario:** Adapter asks the door with `OTHER_PARAMETERS`, receives a well-formed served outcome, then `model_copy(update={"request": request})` with the client’s original `WireRequest` before returning bytes. `ProductClient.ask` serves the B vessel under A’s identity; no `TransportError`. Nothing in the inlined conformance module catches this. (Envelope rewrite is named as undetectable in `codec.py:131-134`, but that paragraph describes rewriting echo **and** address to match a substitute; echo-only relabel keeps a matching address and is exactly the adapter-author reconstruction Phase 19 set out to end.)

### 2. Concrete `as_of` temporal disagreement is unprotected on in-process; “None-only residual” overclaims — MEDIUM
**Where:** `src/ccf/client/adapters/inprocess.py:402-406` / `456-483` `InProcessAdapter.ask` / `_door` · `src/ccf/client/codec.py:143-152` (C-18 residual prose) · contrast `runtime/ccf_runtime/mcp/egress.py:852-864` · `tests/.../test_a_crossed_question_is_caught_on_one_transport.py:125` `_McpMovesTheDoorsInstant`

**Why it is wrong:** On MCP, a concrete boundary crosses twice and the door refuses mismatch by name. On in-process, the encoded question and the separate `asked_at` argument are also two copies (`ask` at 402-406), but `_door` never compares `asked_wire.temporal_boundary` to `asked_at`. The client only sees the echo (`None` or the encoded boundary). Prose that the residual is “the `None` path and only the `None` path” (`codec.py:150-152`) is false for in-process: a concrete-boundary `asked_at`-only move is also silent. The live C-18 control exists only for MCP.

**Failing scenario:** Subclass `InProcessAdapter`, override `ask` to `canonical_bytes(request)` unchanged but pass `asked_at = request.temporal_boundary + timedelta(microseconds=1)` into `_door` (with a concrete `as_of`). Echo matches `sent`; client serves; answer is computed at the moved instant. No `TransportError`.

### 3. `decode_outcome` still claims the client re-runs `check_outcome` — LOW
**Where:** `src/ccf/client/codec.py:424-425` `decode_outcome`

**Why it is wrong:** After `C-05`, `ProductClient.ask` (`client.py:228-229`) calls `decode_outcome` once and does not call `check_outcome` again (`client.py:47-49`). The docstring still says the client “runs again on whatever an adapter returns,” which is the pre-amendment D-11 story. That mis-states where load-bearing checks run and can send a reader hunting for a second call site that does not exist.

**Failing scenario:** Documentation / review failure mode only — a reader treats dual-path checking as current mechanism and underestimates dependence on the single `decode_outcome` call.

## Checked and NOT defects

- **Shipped happy path:** `ProductClient.ask` → `adapter.ask` → `decode_outcome(..., sent=request)` → `check_outcome` with producer-parsed echo and producer-claimed address (`client.py:223-230`, `codec.py:458-468`, `door.py:656-661`).
- **`door_answer` single vessel serialization:** `content_address` is `sha256` of the same `vessel` bytes that become `product_json` (`door.py:656-661`); consumer recompute via `product_json.encode("utf-8")` (`codec.py:267`) is identity for that UTF-8 text.
- **Check ordering:** echo before refusal short-circuit before address before contract (`codec.py:358-377`); refusal returns after echo check and skips address (`367-368`) — correct.
- **Altered-vessel control:** edits `product_json` only, re-encodes without fixing the claim (`test_...py:386-413`); discrimination guard requires vessel still JSON+contract-valid (`497-529`) so the raise is attributable to `verify_content_address`, not the parser/contract limb; D-22 honest-in-hostile-slot controls exist for both P1 and P2.
- **Crossed-question controls:** single transport, discriminating match strings, exact `TransportError` (not `BindingError`), vacuity via honest serve — not a two-subject parity diff.
- **C-18 residual measurement:** `test_an_absent_boundary_leaves_the_moved_instant_undetectable` correctly asserts serve + echo `None` + lineage at the sabotaged instant (`342-378`) — does not overclaim detection on that path.
- **MCP dual-arg cross-checks** for `product_class` / `parameters` / concrete `temporal_boundary` (`egress.py:834-864`) are real door-side refusals, not client self-comparisons.
- **`WireOutcome is DoorOutcome`** alias (`wire.py:103`) and in-process question text round-trip via `door_question` (`inprocess.py:404`, `456-479`) are sound for the non-relabel threat model.
- **Known items not re-derived:** unused `_result_from(..., sent=)`, HTTP naive-`asked_at` error-code reuse, ROADMAP / key-links / citation-lint holes.

## Risk Assessment

**MEDIUM** — For the two shipped adapters and the non-relabel sabotage the phase actually tests, both integrity checks can fail and are watched failing on one transport at a time. Residual risk is concentrated in (1) any new/custom adapter that rewrites `DoorOutcome.request` from client state before returning bytes, and (2) in-process concrete-`as_of` `asked_at` drift, which prose currently folds incorrectly into a None-only residual.

---

## Gemini Review

## Summary

Phase 19 successfully transitions the CCF SDK from a state where integrity checks were "green by construction" (comparing objects to themselves) to a state where they are load-bearing and empirically verified. The retyping of the `TransportAdapter` seam to `bytes` effectively removes the ability for adapters to "help" the client by reconstructing the echo from local state. The introduction of `door_question` and `door_answer` ensures that the producer side maintains a single source of truth for both the answer and its echoed question. The conformance suite now includes high-fidelity sabotage controls that prove a single-transport client detects both crossed questions and altered vessels.

## Findings

### 1. HTTP door `_echo` violates `C-02` and breaks `as_of=None` — HIGH
**Where:** `runtime/ccf_runtime/http_api/routes/product.py`:273 `_echo`
**Why it is wrong:** The `_echo` helper reconstructs the `WireRequest` from the `ProductRequest` object (`asked`). However, `ProductRequest.asked_at` is always a concrete `datetime` (resolved by the door or client), whereas the original `WireRequest` may have had a `None` temporal boundary. This violates mandate `C-02` (recorded in `door.py` line 607 and `client.py` line 173), which requires that `as_of=None` be echoed verbatim as `None`.
**Failing scenario:** A future HTTP adapter calls the door with `as_of=None`. The door resolves the clock to `T1` and serves the answer. The `REQUEST_ECHO_HEADER` contains a `WireRequest` where `temporal_boundary` is `T1`. The client compares `sent.temporal_boundary (None)` with `outcome.request.temporal_boundary (T1)`. The check `outcome.request != sent` fails, raising a `TransportError` on a perfectly healthy wire.

### 2. `check_outcome` error message obscures the defect — MEDIUM
**Where:** `src/ccf/client/codec.py`:361 `check_outcome`
**Why it is wrong:** When an echo mismatch occurs, the error message prints the `product_id` of both `sent` and `received`. However, if the `product_id` matches (e.g., a transport crosses two questions for the *same* product class), the user is told `sent 'A' and received 'A'`, followed by a generic statement that parameters or temporal boundaries differ. It does not print the actual values that disagreed.
**Failing scenario:** A multiplexing transport swaps two concurrent requests for `hw1.companies-over-revenue`. The client raises `TransportError: the outcome echoes a different question than the one that was asked — sent 'hw1.companies-over-revenue' and received 'hw1.companies-over-revenue', or their parameters ... differ.` The developer has no signal as to *which* parameters were received, making it impossible to determine which other request's answer was leaked.

### 3. `verify_content_address` diagnosis is incomplete — LOW
**Where:** `src/ccf/client/codec.py`:272 `verify_content_address`
**Why it is wrong:** The error message attributes the failure to altered bytes or canonicalization drift. It omits the case where the bytes are correct but the `content_address` claim itself was tampered with (the "inverse" corruption). While the limitation regarding adversaries rewriting the envelope is documented at line 131, the error message prose reinforces the idea that the bytes are the only culprit.
**Failing scenario:** A malicious intermediary leaves `product_json` untouched but replaces `content_address` with a random string. The client reports "The bytes were altered in transit", which is technically false (the claim was altered).

## Checked and NOT defects

- **In-process degenerate wire:** Confirmed that `InProcessAdapter` now serializes the request to text and the door re-parses it (`adapters/inprocess.py`:404, 456). This correctly closes the `B0` reconstruction hole for the most common dev transport.
- **Ordering of checks:** `decode_outcome` correctly runs the envelope validation, then the echo check, then the content address check, and finally the contract schema validation. This ensures the most informative failure (e.g., "altered vessel") masks the subsequent schema failure.
- **`as_of=None` Residual (`C-18`):** Confirmed that the `as_of=None` residual is accurately described and that the MCP door's cross-check correctly skips the comparison when the echo is `None` (`egress.py`:853).
- **Single-Serialization Discipline:** `door_answer` correctly serializes the vessel exactly once and derives both the JSON text and the hash from that single byte-string (`door.py`:656-661), preventing drift between the payload and the claim.

## Risk Assessment

**LOW** — The core integrity defect `B0` is resolved for the primary transports (MCP and In-Process). The identified HIGH finding in the HTTP door affects a path for which no shipped adapter yet exists, and its fix is a straightforward alignment with the logic already proven in the MCP door. The structural integrity of the "single point of parity" in `codec.py` is now a fact of the type system.

---

## Ollama Review

**## Summary**
Phase 19 rewrote the transport seam so that adapters return the *producer’s canonical bytes* instead of a `WireOutcome`.  
`decode_outcome` now parses those bytes, extracts the `request` that the *door* itself echoed, and `check_outcome` verifies that this request equals the one the client sent and that the vessel’s SHA‑256 matches the emitted `content_address`.  
Because the request and address now come from the wire, the two integrity checks can actually fail – the conformance tests in `tests/client/...` demonstrate that a crossed question or a tampered vessel raises a `TransportError`.  

The checks are therefore functional, but they rely on the *honesty of the adapter*: nothing in the type system or runtime prevents a malicious adapter from parsing the bytes, mutating the echoed request or the address claim, recomputing a matching hash, re‑serialising and returning the forged bytes. In that situation the client would see a perfectly‑passing outcome. This is the only remaining way the “cannot fail” defect could re‑appear.

---

## Findings
| # | Title | Severity | Where | Why it is wrong | Failing scenario |
|---|-------|----------|-------|----------------|-------------------|
| 1 | **Adapter can re‑construct a forged outcome** | HIGH | `src/ccf/client/wire.py` lines 133‑136 (the `TransportAdapter.ask` protocol) – the protocol only requires returning `bytes`. Nothing prevents an adapter from doing `out = WireOutcome.model_validate_json(bytes); out = out.model_copy(update={request: …}); forged = encode_outcome(out)`. | The integrity checks compare `outcome.request` with the client‑sent `WireRequest` and recompute the hash from `outcome.product_json`. If an adapter rewrites both fields *and* recomputes the matching SHA‑256, the checks succeed even though the answer is for a different question (or a tampered vessel). The SDK’s security model assumes trustworthy adapters; the code does not enforce it. | A malicious `FakeAdapter` that does: <br>```python<br>def ask(self, req):<br>    raw = real_adapter.ask(req)               # honest bytes<br>    out = WireOutcome.model_validate_json(raw)<br>    out = out.model_copy(update={<br>        "request": req.model_copy(update={"parameters": {"evil":1}}),<br>        "product_json": out.product_json,  # unchanged<br>        "content_address": hashlib.sha256(out.product_json.encode()).hexdigest()<br>    })<br>    return encode_outcome(out)<br>```<br>When the client runs `ask`, the check sees the forged request and matching address and returns a `Result` instead of raising. |
| 2 | **`check_outcome` skips verification that a *refusal* carries no address** | LOW | `src/ccf/client/codec.py` line 358‑367 (the early `if outcome.product_json is None: return None`). The function returns before the `if outcome.content_address is None:` guard that raises on a stray address. | The `DoorOutcome` model validator already rejects such a shape, but the early return means the explicit runtime guard is never exercised for refusals. If a future change relaxed the validator, a malformed refusal could slip through. | Construct a byte payload where `product_json` is `null` and `content_address` is a non‑null string. `decode_outcome` succeeds, `check_outcome` returns `None`, and the client’s `Result` contains `content_address` even though the answer was a refusal. |
| 3 | **`verify_content_address` recomputes the hash on the *client‑side* string, not on the exact bytes the producer hashed** | MEDIUM | `src/ccf/client/codec.py` line 267 (`hashlib.sha256(product_json.encode("utf-8")).hexdigest()`). The producer’s address is the SHA‑256 of the *canonical bytes* of the vessel; the client recomputes on the decoded UTF‑8 text. If the canonical serializer ever produced a byte sequence that is not a simple UTF‑8 round‑trip (e.g. it normalises Unicode to NFC), the two digests could diverge even for an honest kit. | The current serializer is defined to be a pure UTF‑8 round‑trip, but the design does not enforce it at the type level. A future change to `canonical_bytes` that adds a BOM or normalises line endings would cause false negatives. | Change `canonical_bytes` to prepend `b'\xef\xbb\xbf'` (a UTF‑8 BOM). The door would emit an address of the *bytes with BOM*, while the client would hash the text **without** the BOM, causing a mismatch and an unexpected `TransportError`. |
| 4 | **Doc‑string over‑claim about “every transport detects a crossed question”** | LOW | `src/ccf/client/client.py` lines 151‑166: the prose states that the client “answers against its own clock” after the fix, but the residual `C‑18` (as_of=None) is still open. The comment correctly mentions the residual, but elsewhere (e.g., `src/ccf/client/codec.py` line 96‑104) the description *“the client detects a crossed question and an altered vessel”* is presented without an immediate qualifier, which can be read as a universal claim. | Readers could infer that the SDK guarantees detection of a crossed question **even when `as_of=None`**, contradicting the explicit residual in the spec. | Run the test `test_an_absent_boundary_leaves_the_moved_instant_undetectable` – the client does **not** raise, proving the over‑claim. |
| 5 | **`_McpMovesTheDoorsInstant._call` uses a staticmethod but calls `McpStdioAdapter._call` via the class name** | MEDIUM | `tests/client/conformance/test_a_crossed_question_is_caught_over_the_mcp_transport.py` lines 168‑176. The staticmethod overrides the original, but it forwards to `McpStdioAdapter._call` (the *base* class) instead of the overridden method on the subclass, which could bypass any future overrides in `McpStdioAdapter`. | If a downstream version of `McpStdioAdapter` added its own logic to `_call`, this test harness would skip it, potentially hiding bugs. | Subclass `McpStdioAdapter` adds a logging side‑effect in its own `_call`; the test harness’s staticmethod would not invoke that logging, making the test’s coverage incomplete. |
| 6 | **`_alter_the_vessel` mutates `product_json` but does not preserve the original `content_address` length** | LOW | `tests/client/conformance/test_a_crossed_question_is_caught.py` lines 386‑413. The function recomputes `encode_outcome` after inserting a space, which changes the UTF‑8 length of the vessel but leaves the original `content_address` unchanged (as intended). However, the comment “one space … inside the vessel text’s opening brace” assumes the brace is at index 0; if the JSON were minified differently (e.g., whitespace before `{`) the insertion could land elsewhere, potentially corrupting JSON structure. | The edit is fragile to formatting changes, but the current door always emits compact JSON, so the test passes. Future changes to the serializer that add whitespace before the opening brace would cause the edit to break JSON, making the test fail for the wrong reason. | Change `canonical_bytes` to emit pretty‑printed JSON (`indent=2`). The edit would insert a space *after* the newline, breaking JSON and causing the `assert_an_altered_vessel_is_caught` test to pass for the wrong reason (parser error instead of address mismatch). |

---

## Checked and **NOT** defects
- `src/ccf/client/wire.py` – the alias `WireOutcome = DoorOutcome` correctly guarantees a single shape.
- `src/ccf/client/codec.py` – the order of checks in `check_outcome` (request ↔ sent, then vessel presence, then address) is sound; no short‑circuit hides a later failure.
- `src/ccf/client/codec.py` – `decode_outcome` correctly turns malformed JSON into a `TransportError`.
- `src/ccf/client/client.py` – the `ask` method builds a proper `WireRequest` and forwards the bytes to `decode_outcome`; the `Result` construction reads only from the validated outcome.
- `src/ccf/client/adapters/inprocess.py` – the question is encoded and decoded, guaranteeing that the echo comes from the door’s parsed request.
- `src/ccf/client/adapters/mcp_stdio.py` – the MCP adapter passes the canonical JSON request unchanged; the `_declared` guard ordering is intentional and correct.
- `src/ccf/products/door.py` – the `DoorOutcome` model validator enforces “exactly one half” and the refusal/vessel invariants.
- All tests under `tests/client/conformance/` pass, confirming that the intended failure modes (crossed question, altered vessel, temporal mismatch) are caught on each transport.

---

## Risk Assessment
**MEDIUM** – The core integrity checks are now live and the conformance suite demonstrates they fail when the wire is tampered. However, the security guarantee depends on **trusting the adapter** to forward the producer’s bytes unchanged. Because the SDK’s type system cannot prevent a malicious adapter from parsing, mutating, and re‑serialising the outcome (finding 1), an attacker with control of the adapter could subvert the checks completely. If the threat model expands to include untrusted adapters, a cryptographic binding (e.g., a signature over the outcome) would be required to raise the risk to LOW. Until such a mechanism is added, the remaining risk is **MEDIUM**.

---

