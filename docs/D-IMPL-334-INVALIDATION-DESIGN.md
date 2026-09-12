# `D-IMPL-334` — the smallest design that lets supersession reach a served product

**Status: a design for Dave to rule on. No code has been written.**
Measured against `src/` and `runtime/` at `main`, 2026-09-12.

---

## 1 · The reframe, which is Dave's and is the whole design

> *"We do not necessarily need a traditional product cache. 'Invalidation' could
> mean marking an existing content-addressed artifact no longer eligible to
> serve."*

The obvious design says: invalidation needs something to invalidate → a product
cache → eviction → an event system to trigger it. That is a large build and it
is the one the article's language implies.

**The smaller reading asks what the fabric must REFUSE.** And the SDK already
refuses at serve time — on TTL, on debt, on attestation, on a declared product
gate. **Eligibility is a predicate, not a storage problem.**

Two measured facts make the small version work, and both were verified rather
than assumed:

- **The SDK stores no Context Product.** `ccf/replay/serve.py::deliver` builds a
  `ServedProduct` and hands it to the caller; the ArtifactStore holds replay
  records and Control Plane artifacts, never product instances. **So there is
  nothing to evict — which removes the need for a cache rather than creating
  one.**
- **The SDK already records what every served product depended on.**
  `ContextFabricSnapshot` carries `touched_entities`, `touched_relationships`,
  `temporal_boundary`, `store_snapshot_pin` and `store_watermark`; the same
  record carries `product_content_address`. **The reverse index nobody has is
  already in the data the SDK writes on every serve.**

---

## 2 · The five capabilities, each against what exists

### 2.1 A supersession / change event

**Exists, unemitted.** `ccf/graph/_writer.py::_restitch_chain` already computes
that a claim on entity `E` was superseded at instant `T`, and writes
`superseded_by` / `superseded_at`. It is inside L2, which is the single writer —
so it is the **only** place the event can originate without breaking the
single-writer invariant.

**The event is a triple**, and it needs no envelope, no schema negotiation and no
transport:

```
(tenant_id, entity_uri, invalidated_from)
```

**No bus.** The writer appends to a register in the same call that sets
`superseded_at`. A bus exists to decouple producers from an unknown set of
consumers; here there is exactly one consumer and it is a predicate.

### 2.2 Knowing which products depended on the changed entity

**Already recorded — no new write-time index.** Every replay record carries
`touched_entities` beside `product_content_address` and the snapshot the product
was built at. *"Which served products touched `E`"* is a query over artifacts the
SDK already writes.

**And for the gate it is not even needed.** The serve-time predicate (§2.4) asks
about the product **in hand**, whose touched entities it has directly. Scanning
historical records is only needed to answer *"what did I already serve that is
now ineligible?"* — a reporting question, not a correctness one.

> **This is the single biggest saving in the design.** The expensive-sounding
> capability turns out to be a read over existing data, and the correctness path
> does not use it at all.

### 2.3 Marking products stale — append-only, and nothing is deleted

A new Control Plane artifact class, the **invalidation register**:

| field | meaning |
|---|---|
| `tenant_id` | scope |
| `entity_uri` | the entity whose state changed |
| `invalidated_from` | the instant from which a product built on older state is ineligible |
| `cause` | what superseded it — the superseding claim's identity |

**Append-only, versioned and content-addressed like every other Control Plane
artifact.** Nothing is evicted, nothing is deleted, and
`ArtifactStoreProtocol`'s no-delete guarantee — *"what makes the tampering
threat structural rather than procedural"* — is untouched.

**Eligibility is computed, never stored:**

> A product is **ineligible** when any entity in its `touched_entities` carries a
> register entry whose `invalidated_from` is **later than** the product's
> `graph_snapshot_at`.

A product is not marked. A product is *evaluated*, against a register, at the
moment someone asks for it. That is why there is no cache and no eviction.

### 2.4 Proving the next consumer cannot receive the old product

**One new gate, in the shape the TTL gate already has.**
`ccf/products/gates.py::run_gates` receives `registry: ControlPlaneProtocol` and
already resolves `MAX_TTL` through it; the register resolves the same way.

It needs one thing the candidate does not carry — the touched-entity list —
threaded in **exactly as `source_attestation` was**: keyword-only, `None`
default, additive, every existing call site byte-for-byte unchanged. That
precedent is in the tree and its docstring states the posture. The value is
available at the call site already: `execution.touched_entities()`.

**The refusal is structural, not advisory.** `ServableProduct` is
metaclass-guarded and constructible only with the gate token, and `deliver()` is
the only path from a candidate to a `ServedProduct`. A product that fails this
gate **cannot be delivered**, in the same way an expired one cannot.

> **THE HONEST LIMIT, AND IT MUST BE IN THE RULING.** This refuses to **re-serve**
> an ineligible product. **It cannot reach a product a consumer already holds** —
> no SDK can. What it can add is a read-side `is_eligible(content_address)` so a
> holder may ask. Anything stronger would be claiming the fabric can reach into a
> consumer's memory, which is the kind of claim `EWS-G22` exists to prevent.

### 2.5 Replay and audit of *why*

The register is append-only, so the causal chain is intact by construction: the
superseding claim's identity is in the entry, and the entry's identity is in the
refusal.

The gate refusal is a `GateRefusal` value like every other, so it travels the
existing refusal path into the replay record with its lineage attached. *"Why was
this invalidated"* is answerable **from the record alone**, at the standard every
other refusal already meets. No new audit surface.

---

## 3 · The surface, counted

| # | Change | Size |
|---|---|---|
| 1 | One Control Plane artifact class — the register | a contract + registration |
| 2 | One append call in `_restitch_chain` | a few lines, inside the existing single writer |
| 3 | One gate in `run_gates` | the `_refuse_ttl` shape |
| 4 | One keyword-only argument threaded into `run_gates` | the `source_attestation` precedent, additive |
| 5 | One optional read-side `is_eligible(...)` | for a holder to ask |

**What this design does NOT add:** no product cache · no eviction · no delete ·
no event bus · no subscriber registry · no background process · no write-time
reverse index · no new transport · no change to `ArtifactStoreProtocol`.

**`D-IMPL-36` is the entry that deferred the invalidation story, and
`IntermediateCache` names it as the reason a longer-lived cache cannot exist.
This design does not come due against it** — it adds no cache, so it inherits no
invalidation problem. The deferral stands; this routes around it.

---

## 4 · What must be ruled before code

1. **Where the register lives** — the in-process Control Plane registry
   (versioned, append-only, already the audit plane) or the ArtifactStore.
   *Recommendation: the registry.* It is already the audit plane and already
   what `run_gates` resolves through.
2. **Granularity** — entities only, or relationships too? `touched_relationships`
   exists beside `touched_entities`. *Recommendation: entities only for v1.* A
   relationship change that matters usually supersedes a claim on an endpoint.
3. **Who appends** — the graph writer synchronously, which couples L2 to the
   Control Plane; or the deployment, which makes it skippable. *Recommendation:
   the writer.* A guarantee a deployment can forget is not a guarantee.
4. **Refuse, or serve with a finding?** A hard refusal is strong and may be too
   blunt — the debt path's precedent is `forced_llm` / `fail_closed` routing
   rather than a binary. *Recommendation: refuse for v1*, because the question
   this answers is *"may this be served"*, and add routing later if measurement
   demands it.
5. **Does invalidation cross the A2A boundary?** An inbound peer product carries
   its own lineage and snapshot. *Recommendation: out of scope for v1*, recorded
   rather than silently unhandled.

---

## 5 · What this unblocks, and what it does not

**It unblocks rung 11's step 7 honestly.** `CP-SPEC-011` could then demonstrate
the real thing: an Item 2.04 acceleration lands, the register gains an entry for
that obligor, and a re-request for the covenant product — which never mentions
early warning — **is refused because its snapshot predates the change**. That is
a cascade in the only sense that matters: *an event about one entity makes a
different product ineligible.*

**It does not deliver push notification**, and `CP-SPEC-011` §0.4 and `EWS-G22`
stay exactly as written. A consumer still learns by asking. The difference is
that asking now gets the right answer instead of a stale one.
