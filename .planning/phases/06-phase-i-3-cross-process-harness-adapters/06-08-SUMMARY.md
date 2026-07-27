---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 08
subsystem: a2a-wire-and-admission
tags: [a2a, wire-protocol, admission, control-plane, lineage, d-imp-14, d-imp-16, xprc-02]
requires:
  - "ccf.a2a.identity (06-07) — IdentityProvider, SignedContextProduct"
  - "ccf.a2a.trust_policy (06-07) — A2ATrustPolicy, PeerTrustGrant"
  - "ccf.products.gates.run_gates — the TTL gate, wired in not reimplemented"
  - "ccf.controlplane.registry / audit — pinned resolution and the one audit log"
provides:
  - "ccf.a2a.wire — WireProtocol + PeerRef / EmitReceipt / InboundProduct"
  - "ccf.a2a.admission — A2AAdmissionGate, AdmittedProduct, five typed refusals"
  - "ccf.a2a.admission.union_lineage — the D-14 set-union law as one callable"
  - "ccf.a2a.admission.InboundPayloadCeiling — the Control Plane size ceiling artifact"
  - "ccf.a2a.admission.PRODUCER_ASSERTION_HEADER — the signed producer claim"
affects:
  - "06-09 / 06-10 — both transports implement WireProtocol and route through the gate"
  - "06-16 — the gate sweep asserts /src imports nothing from a2a"
  - "identity.sign gained an optional `assertions` kwarg; emitters must populate it"
tech-stack:
  added: []
  patterns:
    - "the admission refusal base *is* GateRefusal, so a caller reads an A2A refusal exactly as it reads a TTL refusal"
    - "governance claims travel in the JWS protected header, which is signed, rather than beside it"
    - "the size ceiling is the one check above canonicalization, and a test instruments the decoder to prove it"
key-files:
  created:
    - src/ccf/a2a/wire.py
    - src/ccf/a2a/admission.py
    - tests/a2a/test_admission.py
    - tests/properties/test_lineage_union.py
  modified:
    - src/ccf/a2a/identity.py
    - src/ccf/controlplane/audit.py
decisions:
  - "AdmittedProduct keeps the construction token; the module argues in writing why the Agent counter-precedent does not transfer (untrusted remote origin vs SDK-controlled factory)"
  - "The lineage-equality gate is structurally vacuous across a trust boundary and says so, rather than passing silently"
  - "graph_snapshot_at is preserved from the producer, and order-independence is stated over the two set axes only"
metrics:
  duration: ~75m
  completed: 2026-07-26
---

# Phase 06 Plan 08: WireProtocol and the A2A Admission Gate Summary

One Control Plane gate, above every transport, that verifies size, signature,
contract, policy bindings, TTL and lineage before an inbound A2A Context
Product can be offered to L2 — with typed audited refusals and the lineage
set-union law pinned by a Hypothesis property that fails loudly under
replacement.

## Task 1 — `WireProtocol`

`src/ccf/a2a/wire.py`. Three CCF contracts (`PeerRef`, `EmitReceipt`,
`InboundProduct`) plus a `runtime_checkable` Protocol with `emit` and
`receive`. Nothing on the surface names an L2, assembly or graph type, and
`/src` imports nothing from `a2a` at all.

Three shape choices are load-bearing:

* **`PeerRef` is not an address.** It carries `(tenant_id, peer_id)` — the
  identifiers the trust-policy artifact keys on. A reference embedding an
  endpoint would make trust a property of where a message arrived from, which
  is the property an attacker most easily controls.
* **`EmitReceipt` is transport acknowledgement only.** Whether the far side
  *admitted* the product is the far side's Control Plane decision, reached
  after the receipt exists; a separate type stops an emitter reading
  "delivered" as "accepted".
* **`InboundProduct.observed_peer` is a claim**, documented as such: it selects
  which trust-policy entry the gate reads and proves nothing. What binds the
  product to a principal is the signature.

`InboundProduct.declared_payload_size()` measures the base64url payload member
without decoding it, which is what lets check 1 run above canonicalization.

## Task 2 — the admission gate

`src/ccf/a2a/admission.py`. Six checks in a documented order: size ceiling
(pre-canonicalization) → signature → contract → policy bindings → TTL →
lineage. Refusals are returned values whose base is
`ccf.products.gates.GateRefusal` itself, so an A2A refusal is read exactly like
a TTL refusal rather than through a parallel shape; each subclass carries both
sides of its mismatch. Every verdict is appended to the injected Control Plane
audit log — refusals with `resolved=False`.

**Two things the module says out loud rather than leaving implicit.**

1. **The token argument.** `AdmittedProduct` keeps a module-private
   construction token. The docstring names the I.2 D-12 counter-precedent
   (Dave removed exactly this token from `Agent` in favour of a lint) and
   argues the difference: an `Agent` is built by an in-process factory the SDK
   controls, so a lint over the SDK's own code can make the statement; an
   `AdmittedProduct` describes something from an untrusted remote peer, and a
   lint cannot make a statement about code the SDK does not ship — a
   deployment's own transport, or a third-party wire implementation.
2. **The lineage-equality gate is vacuous across the boundary.** `run_gates`
   is wired in rather than reimplemented, which buys the empty-operator guard
   and the TTL bound genuinely. It does *not* buy INV-CH7-47: that gate compares
   the producer's declaration against the *engine's independent record*, and the
   consumer ran no engine. The declared set is passed as its own witness, and
   `_run_contract_gates` states in its docstring that this makes the comparison
   trivially true, so a reader cannot mistake a passing gate for a verified
   claim. What substitutes is the signature — the producer is accountable for
   the declaration even where the consumer cannot recompute it.

D-20 holds: no `ControlPlaneStateStore` consumer is added. The trust policy and
the ceiling are versioned artifacts resolved by pinned `(key, version)`.

## Task 3 — proofs

22 admission tests and 6 Hypothesis properties; 714 passed / 2 skipped overall
(baseline 686 + 28, the deselected 32 unchanged).

D-23 is the default case, not an addendum. Two peers with different keys and
different entitlements: peer B's key does not admit a product as peer A; peer A
asserting a producer only peer B may assert is refused with both sets on the
refusal; the same envelope is admitted as peer A and refused as peer B. Two
tenants register policies naming the *same* peer with different permitted
producers, and one tenant's grant does not admit that peer for the other.

**Every mutation the plan asked for was performed and the implementation
restored** (`git status --porcelain` clean afterwards):

| Mutation | Result |
|---|---|
| `union_lineage` replaced by `return producer` | 3 of 6 properties fail: consumer-survives, order-independence, strict-growth guard |
| size check disabled | `test_an_oversized_payload_is_refused_before_canonicalization` fails |
| TTL refusal branch disabled | `test_a_validly_signed_but_expired_product_is_refused_by_the_ttl_gate` fails |

The oversize test also **instruments `SignedContextProduct.canonical_payload`**
and asserts it was never called, so the ordering claim is observed rather than
asserted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] The producer assertion had no signed carrier**

- **Found during:** Task 2, check 4.
- **Issue:** The plan requires refusing a peer that asserts a producer
  agent-definition hash outside its entitlements. No such field exists on
  `ContextProductContract`, and `InboundProduct` cannot carry it usefully —
  an unsigned assertion is rewritable in flight, and a governance check against
  a rewritable claim checks nothing.
- **Fix:** `IdentityProvider.sign` gained an optional keyword-only
  `assertions: Mapping[str, str] | None`, merged into the **protected** header
  (which is part of the JWS signing input) and refused if it would overwrite
  `alg` / `kid` / `typ`. The gate reads the claim from the header only *after*
  verification succeeds, so it is authenticated. Additive and backward
  compatible: `sign()` without assertions behaves byte-identically, and all 36
  of 06-07's tests still pass.
- **Files modified:** `src/ccf/a2a/identity.py` (outside the plan's
  `files_modified`; no sibling wave-3 plan touches it).
- **Commit:** `5717494` / `4b3eafa`.

**2. [Rule 3 — Blocking] `joserfc` refuses undeclared protected-header members**

- **Found during:** Task 3, first run — 19 failures.
- **Issue:** `jws.serialize_json` and `deserialize_json` call
  `check_supported_header`, which raises `UnsupportedHeaderError` for any member
  outside `JWS_HEADER_REGISTRY`. `strict_check_header=False` would have fixed
  it and would also have admitted whatever *else* an envelope carried — the
  exact shape the parameter exists to prevent.
- **Fix:** `_registry_declaring()` builds a `JWSRegistry` from
  `joserfc.registry.JWS_HEADER_REGISTRY` plus the members actually present,
  each typed `"str"`, with strict checking left **on**. CCF's assertions are
  declared, not smuggled. Applied symmetrically on sign and verify.
- **Files modified:** `src/ccf/a2a/identity.py`.
- **Commit:** `4b3eafa`.

**3. [Rule 2 — Missing critical functionality] `AuditAction` had no A2A member**

- **Found during:** Task 2.
- **Issue:** `AuditAction` is a closed `Literal`. The gate must audit its
  verdicts, and CLAUDE.md §7.8.2 / WR-07 make the Control Plane's log the one
  audit plane — a private admission journal would fragment it.
- **Fix:** Added `"a2a_admitted"` and `"a2a_admission_refused"`, with the
  rationale in the existing comment block. Purely additive; nothing matches
  exhaustively on `AuditAction` (verified by grep — only `registry.py` and
  `grants.py` reference the type, both as a parameter annotation).
- **Files modified:** `src/ccf/controlplane/audit.py` (outside
  `files_modified`; no sibling wave-3 plan touches it).
- **Commit:** `5717494`.

### Plan criteria corrected

**`grep -c 'state_store\|ControlPlaneStateStore' src/ccf/a2a/admission.py` is 0
— false as written.** The count is 1, and the single match is the module
docstring paragraph *stating* that this gate adds no `ControlPlaneStateStore`
consumer (D-20). The substantive property the criterion is testing holds
absolutely: there is no such consumer in the code, no `state_store` attribute,
and no import of `ccf.controlplane.state`. Satisfying the criterion literally
would have meant deleting the paragraph that records D-20 compliance, which is
strictly worse. Reported rather than silently worked around; the honest check is
`! grep -q 'state_store' <code lines>`.

### Design choices worth flagging for review

**`graph_snapshot_at` is not unioned.** It is single-valued and cannot be. The
producer's anchor is preserved (CLAUDE.md §7.2 says the producer's graph
snapshot *is* preserved), the consumer's stays on the consumer's own products,
and the order-independence law is therefore stated over the two set axes only —
the property suite says so rather than pretending an instant commutes.

## Notes for plans 06-09, 06-10, and 06-16

* **`a2a` / protobuf (research assumption A3) is STILL unexercised.** Nothing in
  this plan imports `a2a`; `/src` deliberately must not (the module docstring
  says so and 06-16 asserts it). The `a2a.*` mypy override remains proven only
  to the extent that it parses. **06-10 is the first plan that will actually
  import it — budget for type-stub friction there.** The one relevant
  data point this plan can offer: the wire boundary is already entirely above
  protobuf, so the friction is contained to `runtime/ccf_runtime/a2a/lf_a2a.py`
  and cannot leak into `/src`.
* **`joserfc` header-registry friction is now answered** (deviation 2). Any
  emitter adding a signed claim must go through `sign(assertions=...)`; a
  hand-built header will be refused by the library.
* **An emitter that does not populate `PRODUCER_ASSERTION_HEADER` produces a
  product no gate will admit** — by design (a peer that will not say what
  produced a product cannot be held to what it may produce). Both transports'
  emit paths must set it. `DetachedJwsIdentityProvider.sign` still defaults to
  no assertions, so this is a caller obligation, not an automatic one.
* **Seams the transports want:** `A2AAdmissionGate.admit(inbound=...,
  consumer_lineage=..., now=...)` returns `AdmittedProduct | GateRefusal`. A
  transport constructs an `InboundProduct` and hands it over; it cannot
  construct an `AdmittedProduct`, and `AdmittedProduct` is what L2's inbound
  path is to require.
* **Not yet bound: `AssemblyWorker` does not yet take `AdmittedProduct`.**
  `admit_entity_claim` still takes an `EntityClaim`, so today "only an admitted
  product may be handed to L2" is a type fact about what the gate *produces*
  and a documented obligation, not yet an enforced signature on L2. Binding it
  is 06-09/06-10 scope (`src/ccf/assembly/worker.py` is outside this plan's
  `files_modified`). Flagging it explicitly so nobody inherits it as done.

## Known Stubs

None. The two transports the gate sits above are 06-09 and 06-10 by design.

## Threat Flags

None beyond the plan's register. T-06-37 through T-06-45 are each addressed and
tested; T-06-41's ordering claim is proven by instrumentation rather than
asserted, and T-06-45 is proven by the absence of a `ControlPlaneStateStore`
consumer.

## Verification

| Check | Result |
|---|---|
| `pytest tests/a2a tests/properties/test_lineage_union.py -q` | 64 passed |
| `pytest tests/a2a/test_admission.py -q` | 22 passed (criterion: ≥10) |
| `pytest tests/properties/test_lineage_union.py -q` | 6 properties (criterion: ≥4) |
| `pytest tests/a2a/test_admission.py -k 'peer_a or peer_b or two_peer'` | 3 passed (D-23) |
| `pytest tests/a2a/test_admission.py -k tenant` | 2 passed (D-23) |
| `pytest -q -m "not postgres and not chroma"` | 714 passed, 2 skipped (baseline 686 + 28) |
| `python -m mypy` | Success: no issues found in 82 source files |
| `python -m tools.lints --all` | exit 0 |
| `grep -rn 'from a2a\.' src/` | nothing |
| `grep -c 'resolved=False' src/ccf/a2a/admission.py` | 2 |
| `git status --porcelain` after all three mutation experiments | clean |

`raise` appears in `admission.py` only for broken-deployment conditions — a
wrongly-typed pinned artifact — and for the construction-token bypass. Every
governance verdict is a returned value.

## Commits

| Task | Commit | Description |
|---|---|---|
| 1 | `639e626` | `WireProtocol` with nothing transport-shaped above the line |
| 2 | `5717494` | The Control Plane admission gate ahead of L2 |
| 3 | `4b3eafa` | Two-peer / two-tenant admission proofs and the lineage union law |

## Self-Check: PASSED

All four created files exist on disk, both modified files carry their changes,
and all three task commits are present in `git log`. No shared orchestrator
artifact (`STATE.md`, `ROADMAP.md`) was modified.
