---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 10
subsystem: a2a-lf-transport-and-skill-dispatch
tags: [a2a, lf-a2a, wire-protocol, protobuf, skills, dispatch, d-imp-14, xprc-02]
requires:
  - "ccf.a2a.wire (06-08) — WireProtocol, PeerRef, EmitReceipt, InboundProduct"
  - "ccf.a2a.admission (06-08) — A2AAdmissionGate, AdmittedProduct"
  - "ccf.a2a.identity (06-07) — detached-JWS signing over canonical bytes"
  - "ccf_runtime.a2a.typed_http (06-09) — WireProtocol implementation #1 and its transport error hierarchy"
  - "tests/crossproc/servers/a2a_producer_child.py (06-09) — the producer shape, env vocabulary and tamper construction, reused verbatim"
  - "tests/crossproc/conftest.py (06-04) — the shared child-spawn fixture, unchanged"
provides:
  - "ccf_runtime.a2a.lf_a2a — WireProtocol implementation #2, the D-IMPL-14 default, on a2a-sdk 1.1.2"
  - "ccf.skills.dispatch.A2ASkillRegistry / A2AInvocation — the fourth and last skill transport (D-05, D-08)"
  - "tests/crossproc/test_a2a_exchange.py parametrized over both wires, with a standing byte-equality guard for assumption A2"
  - "tests/fixtures/banking/skills/remote_products_a2a.yaml — the a2a skill vocabulary"
affects:
  - "06-16 — the AdmittedProduct-on-L2 obligation is STILL OPEN and is escalated here, not closed"
  - "wave (c) harness adapters — the skill catalog is now complete; skill exposure sees four dispatchable types"
tech-stack:
  added: []
  patterns:
    - "assumption resolved by measurement before implementation, with the losing candidate's failure mode recorded in the module docstring"
    - "a params fixture over transports, with not one pre-existing assertion edited — the substitution claim made checkable rather than asserted"
    - "AST import scans over source-text greps, because a docstring that names what a module does not import is an ast.Constant, not an ast.Import"
key-files:
  created:
    - runtime/ccf_runtime/a2a/lf_a2a.py
    - tests/crossproc/servers/lf_a2a_producer_child.py
    - tests/fixtures/banking/skills/remote_products_a2a.yaml
  modified:
    - src/ccf/skills/dispatch.py
    - src/ccf/agents/agent.py
    - tests/crossproc/test_a2a_exchange.py
    - tests/skills/test_dispatch.py
    - tests/invariants/test_a2a_single_writer.py
    - tests/fixtures/banking/a2a.yaml
decisions:
  - "Part.raw carries the whole detached-JWS envelope as one canonical document, not the raw product bytes plus metadata members — so nothing hand-rolls base64url"
  - "Part.data is refused outright at the frame rather than coerced, because Struct's JSON value model does not preserve the bytes a signature was made over"
  - "an a2a skill dispatch returns unadmitted InboundProducts; dispatch cannot construct an AdmittedProduct, so an invocation cannot become an admission"
metrics:
  duration: ~100m
  completed: 2026-07-26
---

# Phase 06 Plan 10: LF A2A Transport and the Fourth Skill Type Summary

The D-IMPL-14 default wire lands as a **substitution under a proven
abstraction**: `LfA2AWire` satisfies the same `WireProtocol` as
`TypedHttpWire`, and the cross-process exchange's seven assertions pass over
both legs with **not one assertion edited**. Skill dispatch's last
`NotYetBound` transport branch is replaced, so all four skill types dispatch.

## Assumption A2 — resolved by measurement, before any code was written

`a2a-sdk` version **re-verified as 1.1.2**, exactly what research pinned, so the
shortened ~14-day validity window did not bite. The `Part` field list
(`text, raw, url, data, metadata, filename, media_type`) and the `Artifact`
field list (`artifact_id, name, description, parts, metadata, extensions`) both
hold as research recorded them. `Part`'s content oneof is named **`content`**,
not `part` — the one field-level detail research did not state, and the first
thing that broke.

The prototype ran a **real assembled and signed banking Context Product** (the
1618-byte detached-JWS envelope from `build_servable_product`) through both
candidate placements, over `MessageToJson` → `Parse`, which is what the JSON-RPC
binding actually does:

| Candidate | Byte-equal after round trip | Signature re-verifies |
|---|---|---|
| `Part.raw` (protobuf `bytes`) | **True** | **True** |
| `Part.data` (`google.protobuf.Value`) | **False** | n/a — the bytes moved |

`Part.data`'s divergence is visible in the first 80 bytes: Struct's JSON model
re-renders `{"payload":"…"` as `{"payload": "…"` — a space after the colon.
Canonical bytes do not survive it, so neither would the signature. Research's
recommendation is therefore **confirmed by measurement, not adopted on
authority**, and the failure mode is recorded in the module docstring so a later
contributor does not "simplify" `raw` into `data`.

A second end-to-end prototype stood up the real JSON-RPC server and client and
confirmed a byte-identical payload across an actual loopback carriage before the
module was written.

## Task 1 — `ccf_runtime.a2a.lf_a2a`

`LfA2AWire` is symmetric like its sibling: one instance is the client leg that
emits and the owner of the routes that queue what arrives.

**LF A2A's machinery does LF A2A's job.** `DefaultRequestHandler`,
`InMemoryTaskStore`, `create_jsonrpc_routes`, `create_agent_card_routes`,
`A2ACardResolver` and `ClientFactory` are used as given; the module composes
them and re-implements none of them. What CCF supplies is an `AgentExecutor`
whose entire body is *frame, queue, acknowledge* — there is no agent loop here
and nothing for one to do (CLAUDE.md §7.3).

Three shape choices are load-bearing:

* **Protobuf stops at the module edge.** Every generated type is constructed and
  consumed inside `/runtime` and converted to and from the CCF contracts
  `ccf.a2a.wire` declares. `grep -rn 'from a2a\.\|import a2a' src/` returns
  nothing. The docstring states *why* in the terms C4 requires: a protobuf
  message silently preserves unknown fields rather than refusing them, so
  "the product validated" could be true of a message that had been quietly
  extended.
* **Framing checks only, four of them**, mirroring `typed_http`: exactly one
  part, the `raw` alternative, the declared media type, the size ceiling, plus
  the peer metadata and whether the bytes parse. No signature check, no trust
  policy read, no entitlement decision (D-12). A `data` part is refused
  *outright* rather than coerced — the A2 finding turned into a frame rule.
* **Both halves of the sync↔async seam**, on the `McpResourceClient` precedent.
  `emit` is a facade over `emit_async` that owns its loop and **refuses to run
  inside a running one** rather than nesting and deadlocking a host.

Agent Cards are documented as **discovery, never trust** (T-06-55): a spoofed
card can misdirect a carriage and cannot make an unentitled product admissible,
because the gate resolves the signing key from the consuming tenant's
trust-policy artifact by the JWS `kid`.

`build_agent_card` exists so a deployment can stand a peer up without importing
`a2a`'s generated types — which keeps the protobuf surface inside this module
for ordinary callers as well as for `/src`. No address, port, scheme, card
identity or default ceiling is in the file (CINV-01, D-IMPL-38).

## Task 2 — one set of assertions, two wires

`tests/crossproc/servers/lf_a2a_producer_child.py` is **deliberately thin, and
that is the finding**: it imports the typed-HTTP child's env vocabulary,
`_required` and `_tampered` rather than restating them, reuses
`build_servable_product` and the emit-then-announce ordering unchanged, and
differs only in the four lines that build the transport and the app. Had it
needed to do more, the `WireProtocol` boundary would not have been the stable
layer §7.2 claims.

`test_a2a_exchange.py` now parametrizes over `["typed-http", "lf-a2a"]` in the
house form (one branch per param, `yield`/`return`, `raise
NotImplementedError(request.param)` tail). **16 tests, both params, 30 s.**
`git diff` on the module removes **zero assertion lines** — verified
mechanically, not by reading. The same admission, the same lineage set-union,
the same tamper refusal, the same two-peer D-23 case and the same
L3-unchanged-on-refusal check all pass over both wires.

One new case, `test_the_carried_payload_is_byte_equal_and_still_verifies`, is
the standing A2 guard. It makes three observations rather than one, because the
first two are each individually satisfiable by a broken transport: the signature
verifies **over the bytes as carried** (which is the strongest available
statement of byte-identity with what the producer emitted — verification
succeeds only over exactly the signed bytes); the verified payload *is* the
carried payload rather than a reconstruction; and re-serializing the parsed
product reproduces the carried bytes exactly. It runs on **both** legs: it could
not be expressed in the shared body (it needs the peer's public key and the raw
envelope), but withholding it from the typed-HTTP leg would forfeit exactly the
comparison that would make a divergence visible.

Two docstring invariant rows added: wire replaceability, and A2A serialization
preserving the payload — each phrased as *what would fail here*.

## Task 3 — the fourth skill type

`A2ASkillRegistry` maps a **logical endpoint name** to a `WireProtocol` the
composition root wired. Dispatch types against the *Protocol*, never a concrete
transport, so `/src` acquires no transport, `httpx` or protobuf dependency and
either shipped wire — or a third — binds at the composition root.

**What comes back is inert.** `A2AInvocation.products` are
`InboundProduct`s — unadmitted. L2 does not accept one, and this module cannot
construct the `AdmittedProduct` L2 would accept, so a skill invocation cannot
become an admission however the calling agent behaves (D-12). The dispatch does
not filter what it drained by peer, because a filter would silently discard
another peer's product on its way past and each product already carries the peer
the transport observed.

The SSRF posture (T-06-57) is asserted with a fixture whose *unregistered*
endpoint is written as a real-looking URL on purpose: it is matched as a name,
resolves to nothing, and a recording transport's call count proves nothing was
dialled on the way to finding out.

**The `NotYetBound` tail is narrowed, not deleted**, and two tests hold it: one
constructs a fifth-type entry via `model_construct` (documented as bypassing
validation *because* no artifact can reach the branch today, which is precisely
why deleting the tail would otherwise look free), and one asserts the tail's
message names neither MCP nor A2A as outstanding — a false error message is how
a reader concludes a working path is unimplemented.

**Mutations performed and the implementation restored** (`git status
--porcelain` clean afterwards): adding `import httpx` to `dispatch.py` fails the
AST import scan, and restoring "A2A is outstanding" to the tail message fails
the message test. Both checks are load-bearing rather than decorative.

## Deviations from Plan

### Plan criteria corrected

**1. Task 3's `grep -rn 'ccf_runtime\|httpx\|import a2a\|from a2a'
src/ccf/skills/dispatch.py` criterion was self-tripping.** The docstring names
both shipped wires in the course of explaining that dispatch depends on
*neither*, and `:mod:` cross-references to `ccf_runtime.a2a.typed_http` and
`ccf_runtime.a2a.lf_a2a` made the grep match a statement of compliance. This is
the recurring phase defect exactly: **a source-text grep cannot distinguish a
violation from a mention of one.**

Resolution, both halves: the docstring now names the wires in prose that is not
a module path ("either shipped wire — typed HTTP or LF A2A"), so the grep is
genuinely empty *and* the claim is still made; and the substantive property is
held by `test_dispatch_imports_no_transport_no_runtime_and_no_protobuf`, an
**AST import scan** — an import is an `ast.Import`, a mention is an
`ast.Constant`, so a docstring cannot trip it while a real import cannot escape
it. The scan asserts it found imports at all, so it cannot pass vacuously, and
the mutation experiment confirms it fires.

**2. Task 1's `inspect.getsource` criterion is honoured, with 06-09's
resolution.** The docstring states the property in prose that is not a type name
("no graph write handle, no graph store, and no assembly worker"), so
`'GraphWriter'`/`'ccf.graph'`/`'AssemblyWorker'` are all absent and the claim is
still made. The structural property is held by
`tests/invariants/test_a2a_single_writer.py`'s AST identifier and attribute
scans, which discover modules via `pkgutil` and therefore covered this new
module the moment it existed — no test edit was needed for that.

### Auto-fixed issues

**1. [Rule 3 — Blocking] `Agent.invoke_skill`'s return type and docstring were
falsified by binding `a2a`.**

- **Found during:** Task 3, first mypy run.
- **Issue:** `dispatch_skill` gained `A2AInvocation` in its return union, which
  `src/ccf/agents/agent.py` does not declare; and its `Raises` block asserted
  "the bound entry is `a2a` and this build lacks the transport", which had just
  become false.
- **Fix:** widened the union, added the `TYPE_CHECKING` import, and rewrote the
  `Raises` entries so `NotYetBound` describes a *fifth* type and
  `A2ASkillUnregistered` describes the (still-unthreaded) agent-level wiring —
  the same standing gap `mcp` already documents.
- **Files:** `src/ccf/agents/agent.py` (outside `files_modified`). Commit
  `45841d4`.

**2. [Rule 3 — Blocking] `tests/invariants/test_a2a_single_writer.py` re-registers
the exchange module's fixtures and broke on the new one.**

- **Found during:** Task 2 verification.
- **Issue:** It imports `consumer` from `test_a2a_exchange`; `consumer` now
  depends on `transport`, which was not re-registered, so two tests errored on a
  missing fixture.
- **Fix:** one added name in the existing import list. Its L3 assertions now run
  **once per wire**, which is strictly stronger than before.
- **Files:** `tests/invariants/test_a2a_single_writer.py` (outside
  `files_modified`). Commit `a72c692`.

**3. [Rule 3 — Blocking] The LF A2A leg had no fixture vocabulary, and its
Agent Card cannot carry a relative URL.**

- **Found during:** Task 2, first run — the child resolved the consumer's card
  and then failed with "Request URL is missing an 'http://' or 'https://'
  protocol", because the card built at fixture time carried only the RPC path.
- **Why it matters:** LF A2A publishes *where this peer answers*, so the port
  must be bound before the transport exists. `_hosted` now takes a **builder**
  rather than an application and hands it the base URL. It already bound the
  port first, for the reason 06-04 established; that same ordering is what makes
  the card constructible. The typed-HTTP leg does not care and did not change.
- **Files:** `tests/crossproc/test_a2a_exchange.py`, plus an additive `lf_a2a`
  block in `tests/fixtures/banking/a2a.yaml` (outside `files_modified`; 06-09
  created that file under the same discipline, and no sibling touches it).
  Commit `a72c692`.

### Deliberate departure from the plan's wording

**`Part.raw` carries the whole envelope, not the raw product bytes plus
detached-JWS members in `Part.metadata`.** The plan's `raw`-over-`data` ruling
is honoured exactly and was independently measured; what differs is *which*
document goes in `raw`. Splitting the envelope would oblige the transport to
base64url-encode the payload member back into place on receipt, and 06-07's
standing correction is that nothing in this codebase hand-rolls base64url —
that is where verification bugs hide. Carried whole, the product's canonical
bytes are never decoded, re-encoded or round-tripped anywhere in the module.
The A2 property is unaffected and is asserted directly rather than inferred.
`Part.metadata` carries the peer claim, the LF A2A analogue of typed HTTP's
headers. Recorded in the module docstring as well as here.

## Assumption A3 — the protobuf cost, paid and recorded in full

**The bill was smaller than budgeted, and this is the last plan that could have
paid it.** Recorded precisely so the phase gate has the real number:

* **No `types-protobuf` was needed.** `a2a-sdk` 1.1.2 **ships `py.typed`**, so
  the existing `[[tool.mypy.overrides]] module = ["a2a.*"]
  ignore_missing_imports = true` entry is a no-op for it — mypy type-checks
  against the real generated types. `python -m mypy` was **clean on the first
  run** over the new module, and stayed clean when the `_send` client parameter
  was tightened from `Any` to `a2a.client.Client`.
* **No stub friction, no `# type: ignore`, no new dependency, no pyproject
  change.** The generated `a2a_pb2` module is top-level and is *not* covered by
  the `a2a.*` override, which turned out not to matter: nothing imports it
  directly, because everything is reached through `a2a.types`.
* **The real cost was API discovery, not typing.** Three findings, none of which
  research had: `Part`'s content oneof is named **`content`**, not `part`;
  `SendMessageRequest`'s field is **`message`**, not `request`; and the server
  routes are FastAPI-shaped (`add_a2a_routes_to_fastapi`,
  `create_jsonrpc_routes`), so the LF A2A leg mounts routes on a `FastAPI` app
  rather than returning a Starlette app the way `typed_http` does.
* **One cosmetic residue:** `a2a/utils/proto_utils.py` emits
  `DeprecationWarning: label() is deprecated` on every message validation (100
  warnings across the exchange run). Vendor-internal, out of scope, not
  suppressed.

## OPEN OBLIGATION — `AdmittedProduct` on L2 is **NOT CLOSED**, and is escalated to 06-16

**This must not be read as covered.** 06-08 left it, 06-09 left it, and this
plan leaves it too — with a reason, and with a concrete proposal so the fourth
wave is not a repeat.

`src/ccf/assembly/worker.py` is **not in this plan's `files_modified`**, and
that boundary is substantive rather than bureaucratic: `AssemblyWorker.ingest`
takes a `SignalEnvelope` and is the entry point for *every* L1 source — CDC,
MCP ingress, file adapters — of which an admitted A2A product is one. Binding
`AdmittedProduct` onto that signature is therefore not a narrowing; it would
break every other ingestion path. Closing the obligation properly means adding a
**second, federated entry point** that takes `AdmittedProduct` and nothing else,
and that is a change to L2's declared surface — a design decision, not an
executor's auto-fix (CLAUDE.md §3: no redesign during Phase I).

The honest current strength, unchanged from 06-09 and restated rather than
upgraded: the consumer path is **observed** to run gate → `AdmittedProduct` →
envelope → `worker.ingest`, this is asserted by AST to be the only ingest call
site in the consumer, and a bypass makes the tamper test fail. That is a
property of one deployment's code, **not** a type-level constraint. Until an
inbound-A2A entry point takes `AdmittedProduct`, "only an admitted product
reaches L2" remains a documented obligation rather than a type error.

**Concrete proposal for 06-16 to rule on:** add
`AssemblyWorker.ingest_admitted(admitted: AdmittedProduct) -> tuple[...]`
alongside `ingest`, deriving the envelopes internally (the derivation currently
lives in `test_a2a_exchange._ingest_admitted`), so an unadmitted product has no
callable path into L2 at all. Everything needed to do it exists; only the ruling
does not.

## Shared-venv report

**This plan installed nothing.** `a2a-sdk==1.1.2` was already present and
pinned in `pyproject.toml`; `fastapi` 0.140.0 and `protobuf` 6.33.6 arrived as
its transitive dependencies. No `pip install` was run, so no sibling's baseline
was disturbed by this agent.

Observed as shared-venv state during the run, for the record: `google-adk`
**2.5.0 is now installed** (sibling 06-14 landed it mid-flight) and `langgraph`
1.2.9 remains from wave 4. Neither affected this plan's suite — the full run was
green with both present.

## `AuditAction` note

**No `AuditAction` member was added.** The wave-3 add/add conflict class does
not recur here: `a2a` dispatch records on the existing `skill_invoked` action,
deliberately on the *same* action and the same log as `mcp` rather than a
parallel one, so "which skills did this agent invoke" stays answerable from one
query (CLAUDE.md §6.2). `src/ccf/controlplane/audit.py` is untouched.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-06-53 through T-06-59 are each addressed:
T-06-53 by the protobuf confinement plus the `/src` import scan (AST, not grep);
T-06-54 by the A2 prototype before implementation and the standing byte-equality
plus signature-reverification test; T-06-55 by the card being read for discovery
only, stated in the docstring, with trust resolved from the JWS `kid` against
the trust-policy artifact; T-06-56 by `test_a2a_single_writer.py`'s `pkgutil`
discovery, which covered this module the moment it existed; T-06-57 by the
logical-endpoint registry, the URL-shaped unregistered fixture value and the
call-count assertion; T-06-58 by the real grant machinery refusing before the
transport is touched, with `wire.calls == 0`; T-06-59 by the audit assertions on
both the success and failure paths.

## Verification

| Check | Result |
|---|---|
| `pytest -q` (full suite) | **888 passed, 2 skipped**, zero failures (baseline: 866 passed / 2 skipped) |
| `pytest tests/crossproc/test_a2a_exchange.py -q` | 16 passed in 29.6 s, both params |
| `--collect-only` shows `typed-http` and `lf-a2a` | yes, 8 cases × 2 |
| `pytest tests/crossproc/test_a2a_exchange.py -k 'byte_equal or canonical'` | passes, both params |
| `pytest tests/crossproc tests/invariants -q` | 74 passed, 2 skipped |
| `pytest tests/skills -q` | 85 passed |
| `python -m mypy` | Success: no issues found in **97** source files |
| `python -m tools.lints --all` | exit 0 |
| `grep -rn 'from a2a\.\|import a2a' src/` | nothing |
| `grep -rn 'ccf_runtime\|httpx\|import a2a\|from a2a' src/ccf/skills/dispatch.py` | nothing |
| `inspect.getsource` scan of `lf_a2a` for `GraphWriter`/`ccf.graph`/`AssemblyWorker` | clean |
| `grep -c 'NotYetBound' src/ccf/skills/dispatch.py` | 4; its message names neither MCP nor A2A |
| harness-import lint spot-check (`import langgraph` injected into `lf_a2a.py`) | **fails** with `cinv02-harness`, restored, lints back to 0 |
| dispatch mutation (`import httpx`) | AST import scan **fails**; restored |
| dispatch mutation (tail message names A2A) | message test **fails**; restored |
| `grep -n 'time.sleep' tests/crossproc/servers/lf_a2a_producer_child.py` | nothing |
| Orphaned child processes after the run | none |
| `git status --porcelain` after every mutation experiment | clean |
| `STATE.md` / `ROADMAP.md` modified | no |

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `c97fb21` | LF A2A transport, the D-IMPL-14 default `WireProtocol` |
| 2 | `a72c692` | The exchange parametrized over both transports |
| 3 | `45841d4` | The `a2a` skill dispatch path (D-05, D-08) |

## Self-Check: PASSED

All three created files and the six modified files exist on disk with the
recorded content; all three task commits are present in `git log`. No shared
orchestrator artifact (`STATE.md`, `ROADMAP.md`) was touched.
