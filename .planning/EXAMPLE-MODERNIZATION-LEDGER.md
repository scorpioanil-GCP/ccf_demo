# Example modernization — findings ledger

Chartered by `D-IMPL-305` and unblocked by `D-IMPL-306`. Order: `s1-01`, then
`s1-00`, then `cp-04` (held under `D-IMPL-261`).

**The standing method, per example:** measure hand-composed governance code;
migrate only responsibilities the SDK now owns; preserve domain behavior; keep
existing business assertions unchanged; update docs; **stop if a new SDK
deficiency appears**. Fence: no SDK work, no new generalized harness, no
raising a floor because a predicate is incomplete.

A finding here is **classified and preserved, never repaired in flight**
(`D-IMPL-261`, `D-IMPL-297`, `D-IMPL-305`).

---

## `MOD-01` — BLOCKING. s1-01 holds the only binder call site in the live `examples/` tree, against a floor with deliberately zero headroom.

**Status:** **RULED — `D-IMPL-307`, 2026-09-09.** Option 2 (split the floor). The evidence now splits by architectural ownership: `_resolved_binder_sites` counts deployments that bind for themselves, `_delegated_binder_sites` counts those whose binder call is the SDK's, and a migration decrements one while incrementing the other in the same commit. The delegated credit is contingent on `_canonical_binder_ownership` reading the SDK's own call, and that limb asserts ORDER against execution rather than presence. s1-01 is unblocked and **must not** keep its binder call to hold a number.

**Measured, not inferred.** `tests/products/test_gate_two_call_shape.py::_resolved_binder_sites`
returns **12** readable binder call sites against
`tests/products/test_gate_two_call_shape.py::MINIMUM_RESOLVED_BINDER_SITES` = **12**.
Headroom: **0**.

Eleven of the twelve are under `archive/examples/`. The twelfth —
`examples/s1-01-hello-context-product/spine.py:387`,
`refuse_operator_set_divergence(declared=scenario.product_class, plan=plan)` —
is **the only binder call site in the live `examples/` tree**.

Migrating s1-01 onto `GovernedResolver` deletes it and takes the count to
**11 < 12**, which is RED.

**Why lowering the floor is not the repair, in the constant's own words.** The
floor sits at the observed count *on purpose*:
`tests/products/test_gate_two_call_shape.py::test_the_binder_scan_is_not_vacuous`
records that *"headroom is not slack, it is a licence: a floor of 9 against 11
bodies lets two projecting bodies stop being scanned with nothing failing to
say so."* Moving the number to accommodate a migration is exactly the licence
that reasoning refuses, and it is what the fence forbids.

**Why this is the same class of defect `D-IMPL-306` just fixed, and why it is
NOT the same fix.** `D-IMPL-300` moved the binder INTO the canonical path:
`src/ccf/products/resolver.py:1761` calls
`refuse_operator_set_divergence(declared=declaration, plan=plan)` at the ruled
pre-execution point. So a canonical example legitimately does not call the
binder — the SDK does, on its behalf. But
`tests/products/test_gate_two_call_shape.py::_projecting_scopes` scans
`tests/products/test_gate_two_call_shape.py::BINDER_SCANNED_TREES`, which is the
examples trees and **not** `src/`, so the scan cannot see the SDK's own call.
The floor therefore counts *adopter* binder call sites as the evidence the seam
is reachable — an evidence model that predates the seam moving.

The seven-region contract had the same shape of fault and was repaired by
teaching the contract a second valid shape. **That repair is not available here
without touching the SDK-facing scan**, and the scan's universe, its floor and
what counts as a readable binder site are all decisions with rulings behind
them. Hence: stop.

**Options, none taken:**

1. **Widen `BINDER_SCANNED_TREES` to include the SDK's own call site.** The
   evidence becomes "the binder is called on the governed path", which is what
   `D-IMPL-300` actually established. Changes a test's universe, so the floor
   must be re-measured rather than adjusted — and the count would then include
   `src/`, which changes what the floor means.
2. **Split the floor.** Keep an adopter-call floor for hand-composed examples
   and add a separate assertion that the canonical path calls the binder.
   Preserves both evidences and both can fail independently.
3. **Migrate s1-00 first instead.** Measured below (`MOD-03`): s1-00's binder
   contribution is **zero**, so its migration does not touch this floor. This
   reorders Dave's stated order and does not resolve `MOD-01`; it only defers it
   to cp-04, which is held anyway.

---

## `MOD-02` — NON-BLOCKING, but two SDK docstrings would be falsified. One is already stale today.

**Status:** OPEN, and its handling is ruled by `D-IMPL-307`: *"A consumer example should not remain fat because an SDK test needs a producer witness."* If a still-valid producer-evidence test needs a shipped witness, measure whether an existing producer example already supplies it; if not, relocate deliberately. Never preserve it in s1-01, never weaken the gate silently.

s1-01's other legacy witness is
`examples/s1-01-hello-context-product/spine.py:324`,
`refuse_request(request=scenario.request, declared=scenario.request_contract)`.

**It is not uniquely load-bearing.** Measured across the shipped trees,
`ccf.products.request::refuse_request` has **8** call sites — cp-00, cp-01,
cp-02, cp-03, cp-04, cp-05's MCP door, s1-00 and s1-01. No floor constant counts
them. Deleting s1-01's leaves seven.

**But two SDK docstrings name s1-01 specifically:**

* `src/ccf/products/request.py:1691` — *"`examples/s1-01-hello-context-product/spine.py::assemble_and_serve`
  is the shipped worked example."* Migration makes this false, because the
  function would no longer make the call.
* `src/ccf/products/bind.py:76` — *"Each has one shipped call site to read …
  and `examples/s1-01-hello-context-product/spine.py::assemble_and_serve` for
  the request refusal."* **This is already stale on today's tree**, before any
  migration: there are eight, not one. Measured, not read off the prose.

`src/ccf/products/resolver.py:1244` and `:2466` also cite s1-01's spine, but as
the subject of the `24.10-F-06`..`F-09` seam measurement — a dated finding about
what the example *could not* adopt. Those citations describe history and are not
falsified by the migration; if anything the migration is their conclusion.

**No docstring was edited.** Re-pointing them is SDK work and the fence forbids
it. If the s1-01 migration proceeds, the docstring correction has to be
authorized with it — publishing a present-tense false SDK statement is the
defect class `D-IMPL-249` was raised for.

---

## `MOD-03` — INFORMATIONAL. The two non-blocking floors have headroom; s1-00 touches neither blocking one.

**Status:** measured, no action.

| floor | value | found | headroom | s1-01 contributes | s1-00 contributes |
| --- | --- | --- | --- | --- | --- |
| `MINIMUM_GATE_CALL_SITES` | 12 | 17 | 5 | 1 | 1 |
| `MINIMUM_PROJECTING_BODIES` | 14 | 20 | 6 | 1 | 1 |
| `MINIMUM_RESOLVED_BINDER_SITES` | 12 | 12 | **0** | **1** | **0** |

Migrating s1-01 takes the first to 16 and the second to 19 — both still above
their floors. Only the third refuses, and it refuses for `MOD-01`'s reason.
