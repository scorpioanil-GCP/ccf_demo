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

## 4 · THE FINDING THAT DECIDES IT: `isinstance` does not verify guarded construction

Measured by the orchestrator on `main` @ `78a603bb`, after two panels raised it:

```
ServableProduct   subclass, never gated  -> isinstance: True
                  object.__new__         -> isinstance: True
StateWriteToken   subclass               -> isinstance: True
```

And the subclass **reaches the exploit**: a `class Forged(ServableProduct)`
that never calls `super().__init__`, with a `product` property, passes
`isinstance` and flows through `DeliveryCapability.deliver` into a real
`ServedProduct`. **Strictly worse than the duck type**, because it inherits the
real attribute surface and satisfies any `isinstance`-shaped rule.

**`isinstance` measures the TYPE. The invariant names the PATH.** Those are
different properties, and the gap is reachable through supported interfaces —
no `object.__new__` required, no module patching, no private-name access.

### 4.1 · The project already settled this, at the one site where it was thought through

`src/ccf/controlplane/state.py` verifies the **mint**, not the type:

```python
__slots__ = ("_minted",)
def __init__(self, token: object) -> None:
    if token is not _STATE_WRITE_TOKEN: raise StateWriteBypassError(...)
    self._minted = _STATE_WRITE_TOKEN

def _verify(token: StateWriteToken) -> None:
    if getattr(token, "_minted", None) is not _STATE_WRITE_TOKEN:
        raise StateWriteBypassError(...)
```

It **refused both forgeries** in the probe. And it is already pinned by a
shipped test — `tests/invariants/test_state_seam_closure.py::test_a_token_subclass_skipping_init_cannot_succeed`,
whose docstring is:

> **"isinstance is not the gate — the mint is verified at the write."**

**Canonizing `isinstance` would have contradicted a shipped, tested invariant**
and would have had census v1 report the codebase's single correct
implementation as a violation, replacing it with a strictly weaker check.

---

## 5 · Recommended mechanism

**Verify the MINT at the boundary. Not the type, and not at every consumer.**

| Half of the distinguishing question | How the mint answers it |
| --- | --- |
| *distinguish authority from shape* | the marker is set **only** on the guarded construction path, so a subclass, a duck type and `object.__new__` all fail it; a type check fails only the duck type |
| *without forcing every internal helper to re-check* | the marker **travels with the value**, so a helper that received it from a verified boundary needs nothing; verification is placed, not repeated |

Three properties follow, and each is measured rather than argued:

1. **Placement is the entry point**, per the ruled unit of governance. 0 of the
   5 genuinely-internal helpers change.
2. **The predicate is the mint**, because the type is not the authority.
3. **The population must be DECLARED, not discovered** — see §6.

`type(x) is T` is a viable second-best: it excludes subclasses, and zero
subclasses of any guarded type exist in `src/`, `tests/`, `examples/` or
`runtime/` except an adversarial one in `test_state_seam_closure.py`. It still
admits `object.__new__`, so it is weaker than the mint and stronger than
`isinstance`.

---

## 6 · Test and lint strategy — and why the census cannot be the source of truth

**The census has now been wrong three times, in three different ways**, and
that is the argument:

- **v1** under-counted verification (missed `compose_children`);
- **v2** over-credited it (`mount_product_source` isinstance-checks the payload
  shape; `refuse_over_tolerance` checks a tolerance value);
- **v3** filed `ProductSource.__init__` as module-private **because the
  function name begins with an underscore** — while `ProductSource` is in
  `__all__` and the constructor is private *by convention only*. That is a
  **7th governed site**, found by review, not by the instrument.

Additionally, **the 7 guarded types are discovered by heuristic** — a class
whose `__init__` contains an `ast.If` whose test unparses to contain
`"token is not"`. All 7 happen to spell it identically, which is luck. A #8
minting through a classmethod factory, a `_minted` sentinel, or
`__init_subclass__` is invisible, and **nothing fails**.

So the strategy is three layers, none of them load-bearing alone:

1. **A DECLARED registry** of guarded types and of governed entry points. The
   rule keys on the declaration; the census only *finds candidates* and reports
   drift against it. A new guarded type that is not declared is a **lint
   failure at the type**, which is how #8 enters without a hand-maintained
   six-site list.
2. **Runtime negative controls**, one per governed entry point, each handing it
   a structurally compatible impostor **and a subclass that skips the guard**,
   asserting refusal. `test_state_seam_closure.py` is the shipped template.
3. **A drift lint** comparing the declared roster against the census, failing
   when a candidate boundary appears that the roster does not name.

**Close the subclass hole at the type as well**, with `__init_subclass__`
refusal, so the per-consumer check stops being load-bearing for 6 of 7 types.

---

## 7 · Compatibility impact

- **No Protocol in `src/ccf/` is outlawed.** Measured across all 50: exactly
  one carries a guarded type in a signature — `ControlPlaneStateStore.put`
  (`state.py:154`). Storage backends, operators, projections, MCP/A2A
  transports, harness adapters, artifact stores, orchestration and HITL routers
  name no guarded type and are untouched. Structural typing stays valid where
  no guarded authority is asserted, exactly as ruled.
- **One seam cannot be governed by any mechanism here.** The SDK invites a
  third-party `ControlPlaneStateStore` (`state.py:44-47`) and cannot compel a
  conforming implementation to check the token at all. That is a **stated
  residual**, not a hole this design closes.
- **Frozen example specimens are not touched.** The five shipped examples
  verify with `case ServableProduct() as gated:` — PEP 634 class patterns with
  isinstance semantics that an `isinstance`-literal signature does not credit.
  Forcing edits there is forbidden by CLAUDE.md §9 and `D-IMPL-261`. A
  mint-keyed rule at declared boundaries does not reach them.
- **Two guarded types have zero annotated consumers** — `DeliveryCapability`
  and `ChildInvocation`. An annotation-keyed rule would govern 5 of 7,
  omitting the capability at the centre of the proven exploit.

---

## 8 · Proposed wording for D-IMPL-337

The governing invariant is unchanged. What is added is the operative rule:

> **Invariant (unchanged).** If a type derives authority or validity from a
> guarded construction path, every publicly reachable consumer that relies on
> that authority must positively verify the guarded runtime authority before
> using it. Structural compatibility or duck typing is insufficient.
>
> **Operative rule.** A guarded type **declares** itself in the guarded-type
> registry and carries a mint marker set only on its guarded construction path.
> A **governed entry point** — a publicly reachable callable that can receive
> an externally supplied value of a declared guarded type — **declares itself**
> in the governed-boundary roster and establishes the mint before relying on
> the value. Internal callees inherit that establishment and do not re-check.
>
> **`isinstance` does not satisfy this rule.** It verifies the type, not the
> construction path: a subclass that skips the guard passes it and has been
> measured reaching a governed delivery. Where a type check is used it is
> `type(x) is T` at minimum, and the mint by preference.
>
> **Exemption.** A callable is exempt only where an externally supplied value
> cannot reach the guarded parameter — because every caller establishes the
> mint first, or because the value is sourced internally from a trusted
> constructor path. Being module-private is **not** an exemption.

### The eight recorded questions, answered

1. **Is `isinstance` universal?** **No — it is inappropriate**, for every
   guarded type, because it measures type rather than path. Measured.
2. **What does *publicly reachable consumer* mean operationally?** A callable
   nameable from outside its module **whose guarded parameter can be supplied
   by the caller**. Two axes, not one; `child_resolver._admit` is reachable and
   not suppliable.
3. **Are module-private consumers exempt?** Not as a category. Three measured
   classes: verified-before-entry (exempt), reachable-through-an-unchecked-public-path
   (governed at the entry), internally-sourced (exempt because substitution is
   impossible). `ProductSource.__init__` proves name-shape is not reachability.
4. **Where does enforcement belong?** At declared boundaries, with the mint
   travelling in the value so helpers inherit it — plus `__init_subclass__`
   refusal at the type so the boundary check is not solely load-bearing.
5. **Interaction with Protocols?** One Protocol touched of 50; structural
   typing elsewhere untouched. The third-party store seam is a stated residual.
6. **Do mutation sites need a stronger rule?** The three consequence classes —
   gate bypass, admission/L3 bypass, Control Plane mutation — are **not
   flattened**. The Control Plane mutation site already carries the strongest
   mechanism in the tree and is the template, which is evidence for *yes*.
7. **How is it tested mechanically?** Declared registry + drift lint + runtime
   negative controls including a **subclass** impostor. The census finds
   candidates; it is never the source of truth.
8. **How do future guarded types enter?** By declaration. An undeclared type
   whose construction is token-guarded is a lint failure **at the type**, not a
   missing row in a hand-written list.
