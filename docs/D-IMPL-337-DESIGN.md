# D-IMPL-337 — design package (OPEN, not ruled)

**Baseline: `main` @ `78a603bb5e556e844f3e4495b1e802749f67a5ee`.**
**Design only. No implementation, and none authorized.**

Reproduce every measurement here with
`.planning/censuses/guarded_type_census_v3.py`.

---

## 0 · The governing invariant, preserved exactly

> If a type derives authority or validity from a guarded construction path,
> every publicly reachable consumer that relies on that authority must
> positively verify the guarded runtime type before using it. Structural
> compatibility or duck typing is insufficient.

**`isinstance` is not canonized.** Whether it is the universal rule, one valid
mechanism under the invariant, or wrong for some guarded types, is what this
design must prove.

---

## 1 · Three conclusions locked before the mechanism panels returned

Ruled by Dave, 2026-09-14.

### 1.1 · The rule is NOT defined around annotations

The three censuses disagreed, and the disagreement is the proof:

| Instrument | Keyed on | Result |
| --- | --- | --- |
| v1 (preserved) | annotation + `isinstance(<arg>` as text | 15 sites, 14 unverified |
| v2 | `isinstance` anywhere alongside the type name | 43 sites, **3** unverified |
| **v3** | literal `isinstance(THAT arg, THAT type)` in the AST | 13 annotated, **6** exposed-unchecked |

Reading the disputed sites settled it. **v2 over-credited**:
`mount_product_source` isinstance-checks the payload shape and
`refuse_over_tolerance` checks a tolerance value — neither checks its guarded
parameter. **v1 under-counted** real verification.

**The decisive counterexample is `ccf.products.composite.compose_children`**:
exported, genuinely verifies `AdmittedChild`, and types its parameter `object`
**deliberately**, so mypy cannot prove the guard unreachable. The guarded check
is real *precisely because* the parameter is intentionally typed broadly. Any
annotation-keyed rule would report it as not a consumer.

### 1.2 · The unit of governance

> A publicly reachable entry point that can receive an externally supplied
> value whose authority depends on guarded construction must positively
> establish that guarded runtime authority before relying on it.

Materially narrower than *"every function mentioning a guarded type must
`isinstance` it."*

### 1.3 · "Module-private" is not an exemption category

The measured taxonomy, from the call graph:

| Category | Measured sites | Status |
| --- | --- | --- |
| **verified-before-entry** | `_rebinding_failure`, `_row_for_admitted` — only caller `compose_children` verifies | genuinely exempt |
| **reachable through an unchecked public path** | `_refuse`, `_validated_member` (via `mount_product_source`); `state._verify` (via `put`) | **governed at the public entry point** |
| **internally sourced** | `child_resolver._admit` — its caller does not verify, but the producer comes from `resolve_producing_grant` and cannot be externally supplied | potentially exempt, **because external substitution is impossible — not because the helper is private** |

---

## 2 · Refreshed census

**7 token-guarded types**, each with an `__init__` that raises unless handed a
module-private token:

| Type | Module | Refusal |
| --- | --- | --- |
| `AdmittedChild` | `ccf/products/composite.py` | `ChildAdmissionBypassError` |
| `AdmittedProduct` | `ccf/peering/admission.py` | `AdmissionBypassError` |
| `ChildInvocation` | `ccf/products/composite.py` | `ProvenanceForgeryError` |
| `DeliveryCapability` | `ccf/replay/serve.py` | `CapabilityForgeryError` |
| `ResolvedProducer` | `ccf/products/composite.py` | `ProvenanceForgeryError` |
| `ServableProduct` | `ccf/products/gates.py` | `GateBypassError` |
| `StateWriteToken` | `ccf/controlplane/state.py` | `StateWriteBypassError` |

**Population change from the merged `D-IMPL-336` surface: none.** The type
count and the exposed-site identities are unchanged from the preserved census.
336 added `ResolvedProducer` and `ChildInvocation` **with** their checks —
`invocation_from_dispatch` verifies, `compose_children` verifies — so it
enlarged the guarded population without enlarging the governed gap.

### 2.1 · The six exposed, unchecked entry points

| Type | Site | Reach | Consequence if bypassed |
| --- | --- | --- | --- |
| `ServableProduct` | `replay/serve.py::serve` | EXPORTED | **gate bypass** — the three validation gates never ran |
| `ServableProduct` | `replay/serve.py::deliver` | public name | **gate bypass** |
| `ServableProduct` | `products/gates.py::refuse_over_tolerance` | EXPORTED | **gate bypass** (tolerance held against an unvetted product) |
| `AdmittedProduct` | `graph/product_source.py::mount_product_source` | EXPORTED | **admission / L3 proof bypass** — an unverified federated product mounted as a queryable source |
| `AdmittedProduct` | `assembly/worker.py::ingest_admitted` | public name | **admission / L3 proof bypass**, against the single-writer invariant |
| `StateWriteToken` | `controlplane/state.py::put` | public name | **Control Plane mutation** on a structurally similar but unauthorized value |

**Not flattened into one severity.** Three distinct consequence classes.

### 2.2 · Verification without annotation — invisible to any annotation-keyed rule

| Site | Reach | Verifies | Subject |
| --- | --- | --- | --- |
| `composite.py::compose_children` | EXPORTED | `AdmittedChild` | `outcome` |
| `door.py::served_answer` | EXPORTED | `ServableProduct` | `resolved` |
| `resolver.py::__call__` | module-private | `ServableProduct` | `gated` |
| `child_resolver.py::_admit_peered` | module-private | `AdmittedProduct` | `outcome` |

### 2.3 · The proven exploit

Public imports only, no reflection, no private-name access: a duck-typed
`ServableProduct` reaches `DeliveryCapability.deliver`, which does
`ServedProduct(product=product.product, …)` with no type check, and returns a
`ServedProduct`. `isinstance(duck, ServableProduct)` is `False`. **The three
validation gates never ran.**

---

## 3 · The question that decides the mechanism

Dave, and it is not elegance:

> Which mechanism can distinguish a value that merely **looks** right from one
> whose authority came through the guarded construction path, **without forcing
> every internal helper to re-check it**.

Two panels are testing this. Results and the recommendation follow in §4–§8.

---

## 4 · Design alternatives · *pending panel results*
## 5 · Recommended mechanism · *pending*
## 6 · Test and lint strategy · *pending*
## 7 · Compatibility impact · *pending*
## 8 · Proposed wording for D-IMPL-337 · *pending*
