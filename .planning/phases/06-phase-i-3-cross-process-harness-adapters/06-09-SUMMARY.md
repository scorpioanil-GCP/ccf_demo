---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 09
subsystem: a2a-typed-http-transport
tags: [a2a, wire-protocol, typed-http, crossproc, single-writer, d-imp-14, xprc-02]
requires:
  - "ccf.a2a.wire (06-08) — WireProtocol, PeerRef, EmitReceipt, InboundProduct"
  - "ccf.a2a.admission (06-08) — A2AAdmissionGate, AdmittedProduct, typed refusals"
  - "ccf.a2a.identity / trust_policy (06-07) — detached-JWS signing, peer grants"
  - "tests/crossproc/conftest.py (06-04) — the shared child-spawn fixture"
  - "crossproc/servers/mcp_egress_child.build_servable_product (06-04) — the assembled banking product"
provides:
  - "ccf_runtime.a2a.typed_http — WireProtocol implementation #1, independent of any wire standard"
  - "tests/crossproc/test_a2a_exchange.py — the real two-process signed exchange with consumer-side admission"
  - "tests/invariants/test_a2a_single_writer.py — the A2A leg of ROADMAP criterion 4"
  - "tests/fixtures/banking/a2a.yaml — peer identities, ceilings, endpoint path, federation ingress rule"
affects:
  - "06-10 — the LF A2A leg is now a substitution under a proven abstraction, not a redesign"
  - "06-10 — `a2a`/protobuf is STILL unexercised; that cost lands entirely there"
  - "06-10 — the AdmittedProduct-on-L2 binding is NOT closed here (see Open obligations)"
tech-stack:
  added: []
  patterns:
    - "the wire carries the SignedContextProduct as one canonical document, so the signed payload member crosses verbatim and the transport never touches base64url"
    - "the 06-04 fixture's roles inverted: the consumer is the parent and listens; the children emit before they announce, so `readline()` also gates the exchange"
    - "AST *identifier* scans rather than source-text greps, so a docstring documenting compliance cannot trip an invariant test"
key-files:
  created:
    - runtime/ccf_runtime/a2a/__init__.py
    - runtime/ccf_runtime/a2a/typed_http.py
    - tests/crossproc/servers/a2a_producer_child.py
    - tests/crossproc/test_a2a_exchange.py
    - tests/invariants/test_a2a_single_writer.py
    - tests/fixtures/banking/a2a.yaml
  modified: []
decisions:
  - "The envelope crosses as one canonical document rather than raw body + header metadata, so the transport does no base64url handling at all"
  - "The consumer mints its own entity URIs for federated claims rather than adopting the peer's"
  - "The graph digest covers the SQLite write-ahead log; a main-file-only digest reports 'unchanged' after a real write"
metrics:
  duration: ~95m
  completed: 2026-07-26
---

# Phase 06 Plan 09: Typed-HTTP A2A Transport and the Cross-Process Proof Summary

The first `WireProtocol` implementation — plain typed HTTP, deliberately bound
to no wire standard — carrying a signed banking Context Product across a real
OS process boundary into a consuming fabric's Control Plane gate, with the A2A
leg of ROADMAP criterion 4 pinned by three concrete observables and both
mutation experiments the plan asked for performed and restored.

## Task 1 — `ccf_runtime.a2a.typed_http`

`TypedHttpWire` is symmetric: one instance is the `httpx` client leg that
emits and the owner of the Starlette/ASGI endpoint that queues what arrives.
A deployment that only sends never hosts `asgi_app()`; one that only receives
never calls `emit`. Neither case needs a second type.

Three shape choices are load-bearing:

* **The envelope crosses as one canonical document.** The body is
  `canonical_bytes(signed)`, and `SignedContextProduct.payload` is already
  base64url text, so the product's own canonical bytes are never decoded,
  re-encoded, or round-tripped anywhere in this module — they cross as the same
  characters the producer signed. This is a **deviation from the plan's wording**
  ("detached JWS members carried alongside as transport metadata"), taken
  because the alternative — raw body plus header metadata — would have put the
  transport in the business of base64url encoding the payload member back into
  place, and 06-07's standing correction is that nothing hand-rolls base64url.
  `wire.py`'s own contract wording ("the payload member travels verbatim") is
  satisfied more strictly this way, not less.
* **No check of any kind above framing.** Four framing checks — media type,
  body size, the declared peer header, whether the body parses as a signed
  product — and nothing else. No signature verification, no trust-policy read,
  no entitlement decision (D-12). The module docstring says so, and it is the
  only place in the file that names the gate's module at all.
* **The body ceiling is defence in depth and says so.** Streamed and counted
  rather than `await request.body()`, so a peer that declares a small
  `content-length` and then sends more is cut off mid-stream. The authoritative
  ceiling remains the Control Plane's, applied by the gate before
  canonicalization (06-08). No default (D-IMPL-38); a non-positive value is
  refused at construction.

Endpoint, path, client, clock and ceiling are all caller-supplied. Tenancy is a
per-call argument on `PeerRef`, never a constructor field (CDC precedent); the
only constructor identity is `local_peer_id`, which is identity and not
location. `PeerEndpointResolver` is a seam rather than a field on `PeerRef`,
because a `PeerRef` deliberately is not an address.

## Task 2 — the real two-process exchange

`tests/crossproc/servers/a2a_producer_child.py` runs the whole L1→L6 banking
slice in its own heap (reusing 06-04's `build_servable_product` rather than
re-implementing it), signs the assembled product with its own peer key, and
emits **two** carriages over real loopback HTTP before announcing `READY`:

1. the genuine envelope;
2. the genuine protected header and signature spliced onto a *different*
   product's payload member. Both members are library-produced, so a real
   tampered envelope traverses a real socket rather than the parent mutating a
   value it already holds — and nothing slices bytes.

Because the child emits before it announces, the parent's blocking
`readline()` is also the gate on the exchange having happened. Nothing is
sleep-gated anywhere.

**The 06-04 fixture's roles are inverted, and the fixture is unchanged.** The
consumer is the parent and listens; the children connect. `_hosted()` reuses
the same mechanics for the same reasons — bind port 0 first, hand the bound
socket to uvicorn, gate on the server's own `started` flag — but it is the
parent hosting, so it could not be the fixture itself. `spawn_child_server` is
used verbatim for both children; configuration reaches them through the
inherited environment, which needed no fixture change at all.

Seven tests, 13 s. The two-peer case (D-23) is the default rather than an
addendum: both peers' genuine products are admitted against their *own*
entries, both tampered ones refused, and peer B's genuine, fully entitled
product presented under peer A's identity is refused with `declared_key_id`
naming B's key and `permitted_key_ids` naming only A's.

Lineage is asserted as an exact set-union on both set axes, with the
producer's `graph_snapshot_at` anchor and its policy version surviving.

**Mutation performed and the implementation restored** (`git status --porcelain`
clean afterwards): handing the received product straight to `worker.ingest`
before calling the gate makes `test_a_tampered_product_is_refused_and_leaves_l3_byte_identical`
fail on the graph digest.

## Task 3 — `tests/invariants/test_a2a_single_writer.py`

Nine tests implementing research's criterion-4 A2A row:

**(a) Assembly is the only mutation path.** With a producer in a separate OS
process, reaching a *verdict* changes nothing (asserted separately — the gate
guards L2's entrance and does not shorten the path through it), and only
`worker.ingest` moves L3. `test_a2a_exchange.py` additionally asserts by AST
that `_ingest_admitted` is the *only* function in the consumer that calls
`.ingest(...)`.

**(b) No transport module holds or names a write surface.** Modules are
**discovered** via `pkgutil` rather than listed — a hand-maintained list is one
a later transport can be added without joining — and a guard test asserts the
discovery found something, so the parametrized assertions cannot pass
vacuously. Three scans: imports reach neither `ccf.graph` nor `ccf.assembly`;
no AST *identifier* is in `WRITE_SURFACE_NAMES`; and a constructed instance
holds no attribute, **public or private**, whose type is one.
`WRITE_SURFACE_NAMES` is imported from `test_consumption_discipline.py`, not
redefined.

**(c) A refused product leaves L3 byte-identical**, write-ahead log included.

**Mutation performed and the implementation restored:** adding an
`AssemblyWorker`-typed attribute to `typed_http.py` fails both the import scan
and the identifier scan.

**D-22 held.** `ALLOWED_CCF_PREFIXES` is untouched (`git diff --quiet`
verified), and a test states *why* no widening was needed rather than leaving
it to a reviewer: `test_consumption_discipline.py` scans `src/ccf/agents` only,
and the transport is not in the agents package. No transitive-closure argument
is being offered here because none is required — nothing was widened.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 — Blocking] The graph digest had to cover the write-ahead log**

- **Found during:** Task 2, first run.
- **Issue:** `sha256(database_path.read_bytes())` — the technique
  `test_mcp_role_separation.py` uses — reported the consumer's graph as
  **unchanged** after a real, committed ingest. The SQLite backend runs
  `PRAGMA journal_mode = WAL` (`src/ccf/graph/backends/sqlite.py:149`), so the
  write landed in `<db>-wal` and the main file was byte-identical.
- **Why it matters beyond this plan:** an *unchanged*-assertion built on that
  digest passes for the wrong reason. It is exactly the false-observable class
  this suite exists to avoid.
- **Fix:** the digest covers the main file **and** `-wal`, excluding `-shm`
  (process coordination state, not durable content, and it churns on reads).
  The reasoning is in the method's docstring so the next reader does not
  rediscover it.
- **Files:** `tests/crossproc/test_a2a_exchange.py`. Commit `4716fbf`.
- The corresponding weakness in `test_mcp_role_separation.py` is **out of
  scope** and logged to `deferred-items.md` rather than fixed.

**2. [Rule 3 — Blocking] The A2A domain vocabulary had no fixture**

- **Found during:** Task 2.
- **Issue:** The plan requires every domain value to come from
  `tests/fixtures/banking/`, and nothing there declared peer identities, key
  identifiers, producer hashes, payload ceilings, the endpoint path, or how an
  admitted federated product becomes L1 signal on the consumer's side.
- **Fix:** added `tests/fixtures/banking/a2a.yaml`, outside the plan's
  `files_modified`. No key *material* is in it — keys are generated per test
  into a temp directory. No sibling wave-4 plan touches `tests/fixtures/`.
- **Files:** `tests/fixtures/banking/a2a.yaml`. Commit `4716fbf`.

### Plan criteria corrected

**Task 1 acceptance criterion 3 contradicts the task's own action text.** The
criterion asserts `'GraphWriter' not in inspect.getsource(m)`, while the action
instructs the module docstring to state that "the transport holds no
`GraphWriter`, no `GraphStore`, no assembly worker". Satisfying both literally
is impossible; satisfying the criterion by deleting the paragraph would be
strictly worse, and satisfying the action would fail the criterion. This is the
recurring defect the executor brief names — **a source-text grep standing in for
a structural property, unable to distinguish a violation from a mention of
one**.

Resolution: the docstring states the property in prose that is not a type name
("no graph write handle, no graph store, and no assembly worker"), so both
greps pass *and* the claim is made. The substantive property is then held by
Task 3's observable (b), which scans **AST identifiers, never source text** —
a docstring is `ast.Constant`, not an identifier, so it cannot trip the check,
while a genuine use of the type is an identifier and cannot escape it. The
mutation experiment confirms the check is load-bearing. The honest form of the
criterion is the identifier scan, not the grep.

**Task 1 acceptance criterion 4** (`grep -c 'admission'` is 0 outside the
docstring paragraph) is satisfied as written — the two matches are both inside
the module docstring — but it has the same weakness, and the property it is
reaching for is genuinely held by a different fact: the module **imports
nothing from `ccf.a2a.admission`**, which Task 3's import scan asserts.

**The `time.sleep` grep criterion was self-tripping.** The exchange module's
docstring originally said "There is no `time.sleep` anywhere", which made the
grep match a statement of compliance. Rephrased to "Nothing here is
sleep-gated"; the grep is now genuinely empty.

## Open obligations

**`AssemblyWorker` still does not require `AdmittedProduct` — NOT closed here,
and not covered.** 06-08 flagged this explicitly and assigned it to
06-09/06-10. It is **outside this plan's scope**: `src/ccf/assembly/worker.py`
is not in `files_modified`, and binding `AdmittedProduct` onto L2's entry point
changes a core `/src` signature that a concurrent wave-4 plan could also be
touching. It is therefore left cleanly for **06-10**, exactly as 06-08 left it
for this wave — reported as open, not as done.

What this plan *does* establish, stated at its real strength: the consumer path
demonstrably runs gate → `AdmittedProduct` → envelope → `worker.ingest`, this is
asserted by AST to be the only ingest call site in the consumer, and a bypass
makes the tamper test fail. That is an observed property of one deployment's
code, **not** a type-level constraint. Until `admit_entity_claim` (or an inbound
A2A counterpart) takes `AdmittedProduct`, "only an admitted product reaches L2"
remains a documented obligation rather than a type error.

**`a2a` / protobuf (research assumption A3) is STILL unexercised.** This
transport imports nothing from `a2a` — deliberately, since its whole purpose is
to prove the abstraction independent of any wire standard — and neither does
`/src`. **06-10 is the first plan that will import it; budget for type-stub
friction there.** The one data point this plan adds: the `WireProtocol`
boundary is genuinely sufficient. `TypedHttpWire` satisfies it structurally
(asserted at runtime), and everything transport-specific — framing, headers,
statuses, the ASGI app — sits strictly below the line, so the LF A2A leg is a
substitution rather than a redesign.

**No `AuditAction` member was added.** The wave-3 add/add conflict class does
not recur here: this plan reuses 06-08's `a2a_admitted` /
`a2a_admission_refused` unchanged and modified no `/src` file at all.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-06-46 through T-06-52 are each addressed:
T-06-46 by the three scans of observable (b) plus the byte-identity assertions;
T-06-47 by the verbatim-payload carriage (a re-serializing transport would
refuse the *genuine* product, which is what makes the admission test a real
check on it); T-06-48 by the absence of any check in the transport and the
absence of any import of the gate's module; T-06-49 by the two-peer and
cross-peer-key cases; T-06-50 by the absence of any address literal in
`/runtime` (grep-verified) and the fixture's explicit loopback bind; T-06-51 by
the streamed body limit; T-06-52 by the untouched allowlist.

## Verification

| Check | Result |
|---|---|
| `pytest tests/crossproc/test_a2a_exchange.py -q` | 7 passed in 13.0 s (criterion: < 60 s) |
| `pytest tests/crossproc/test_a2a_exchange.py -k 'peer'` | passes (D-23) |
| `pytest tests/crossproc/test_a2a_exchange.py -k 'tamper or refus'` | passes, asserts L3 unchanged |
| `pytest tests/crossproc -q` | 28 passed |
| `pytest tests/invariants/test_a2a_single_writer.py -q` | 9 passed (criterion: ≥ 3) |
| `pytest tests/invariants -q` | 33 passed, 2 skipped (incl. `test_single_writer_boot.py`) |
| `pytest -q -m "not postgres and not chroma"` | 817 passed, 2 skipped, **2 pre-existing failures** (see below) |
| same, excluding this plan's new files | 801 passed, 2 skipped, same 2 failures — so the failures are on the base |
| `python -m mypy` | Success: no issues found in 94 source files |
| `python -m tools.lints --all` | exit 0 |
| `git diff --quiet tests/agents/test_consumption_discipline.py` | clean (D-22) |
| `grep -c 'WRITE_SURFACE_NAMES' tests/invariants/test_a2a_single_writer.py` | 4, imported not redefined |
| `grep 'no path\|by construction'` in the invariant module | nothing (D-21) |
| `grep 'http://\|127\.0\.0\.1\|localhost'` in `typed_http.py` | nothing |
| `grep 'import a2a\|from a2a\|langgraph\|google.adk\|claude_agent_sdk'` in `typed_http.py` | nothing |
| `grep 'time.sleep'` in both new test files | nothing |
| Orphaned child processes after the run | none |
| `git status --porcelain` after both mutation experiments | clean |

**Baseline note.** The brief cited a 835-passed baseline; the measured base at
`d51f9af` under `-m "not postgres and not chroma"` is **801 passed / 2 skipped /
2 failed**, and this plan takes it to 817. The two failures
(`tests/conformance/test_harness_adapter.py`, absent-harness path asserted
against a harness that *is* installed) are pre-existing, environment-dependent,
and out of this plan's scope — logged to `deferred-items.md` for plan 06-13's
wave rather than fixed here.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `d170c55` | Typed-HTTP `WireProtocol`, the first transport under the abstraction |
| 2 | `4716fbf` | The real two-process signed exchange with consumer-side admission |
| 3 | `490675c` | The A2A leg of ROADMAP criterion 4 |

## Self-Check: PASSED

All six created files exist on disk; all three task commits are present in
`git log`. No `/src` file was modified. No shared orchestrator artifact
(`STATE.md`, `ROADMAP.md`) was touched.
