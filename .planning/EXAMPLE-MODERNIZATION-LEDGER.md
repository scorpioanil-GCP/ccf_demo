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

---

## `MOD-04` — BLOCKING. The s1-01 migration is mechanically complete and was REVERTED: two already-known, still-open SDK findings stop it preserving domain behavior.

**Status:** **RULED and REPAIRED — `D-IMPL-308`, 2026-09-09.** Both findings were
reopened narrowly and closed: the resolver now reads a class-declared decision
instant and carries a declared refresh window. Rerunning the unchanged adapter
took the five failures to two. The two that remain are a different cause and
are `MOD-05` below.

**The migration was built and run before it was classified**, so what follows is
measured against a working canonical s1-01 rather than predicted. `spine.py`
went **634 → 390 lines**, `assemble_and_serve` from 379 lines carrying seven
hand-composed regions to a ~60-line adapter opening `boot` / `acquire` /
`govern`; `refuse_operator_set_divergence`, `run_gates`, `build_replay_record`,
`serve`, `ProjectionEngine` and `refuse_request` all left the example.
`tests/examples/test_s1_01_governed_resolver_adoption.py` stayed **3 passed, 2
xfailed**, and `tests/examples/test_s1_01_output.py` went to **34 passed, 5
failed**. The five are one cause.

**The measurement, from a real run of the migrated example:**

| what | the deployment declares | the canonical path produced |
| --- | --- | --- |
| graph boundary (`asked_at`) | `00:00` | `00:00` |
| decision instant (`scenario.now`) | `00:05` | — no seam |
| `record.recorded_at` | `00:05` | **`00:00`** |
| `product.expires_at` | `00:15` (`now` + 600s) | **`00:10`** (`asked_at` + 600s) |
| `product.source_refresh_recency` | the declared window | **`None`** |

**`GovernedResolver` collapses the decision instant onto the graph boundary.**
s1-01 declares them five minutes apart on purpose —
`tests/examples/test_s1_01_output.py::test_the_recorded_boundary_is_data_and_not_a_clock_read`
asserts `temporal_boundary < now < expires_at`, which is how the example proves
no clock is read anywhere in the path. On the canonical path both the record's
`recorded_at` and the product's TTL run from `asked_at`, so **the content
address and every graph pin move**, which is what the other three failures are.

**Neither finding is new, and that is the difficulty.** Both were already
recorded and carried:

* **`F-09`** — *"a decision instant distinct from the graph boundary"*, carried
  by name in `D-GATE-24.11`.
* **`24.10-F-08`** — `source_refresh_recency` has no seam in the resolver's
  candidate construction; it is a live `xfail(strict=True)` in
  `tests/examples/test_s1_01_governed_resolver_adoption.py`, so the day the seam
  lands it XPASSes loudly.

**Why the migration was reverted rather than landed with five reds.**
`D-IMPL-305`'s method requires the migration to *preserve domain behavior* and
*keep existing business assertions unchanged*. Landing it would move the
example's published content address and drop a field the deployment declares —
a regressed example, not a modernized one. `D-IMPL-261` keeps evidence
executable, and the evidence here is this row plus the two findings that were
already executable; it is not served by shipping an s1-01 that answers with the
wrong TTL.

**What is NOT the repair.** Adjusting s1-01's artifacts so its decision instant
equals its graph boundary would delete the property the example exists to prove
and make `test_the_recorded_boundary_is_data_and_not_a_clock_read` vacuous.
Weakening or deleting the five assertions is the same move. Repairing
`GovernedResolver` is SDK work, and the fence forbids it
(`D-IMPL-305`, `D-IMPL-307`).

**Options, none taken:**

1. **Rule `F-09` and `24.10-F-08` in scope for a small SDK repair**, then land
   the migration. This is the only option that ends with s1-01 canonical AND
   behavior-preserving. It reopens SDK work the fence closed, so it needs an
   explicit ruling rather than an executor's judgment.
2. **Migrate `s1-00` first and leave s1-01 pending the seam. MEASURED, and
   `s1-00` is CLEAR of both findings.** Its
   `examples/s1-00-companies-over-revenue/deployment.py` returns
   `self.request.asked_at` from both `now` and `temporal_boundary`, so its
   decision instant and its graph boundary are the same instant and `F-09`
   cannot bite; and its own `produce.py` records in its docstring that this
   product carries **no** `source_refresh_recency` and **no**
   `obligation_in_force`, so `24.10-F-08` has nothing to take away. This
   inverts Dave's stated order (`s1-01` then `s1-00`) and is therefore a
   ruling rather than an executor's call — recorded, not taken.
3. **Land s1-01 canonical and accept the moved address**, re-pinning the
   example's expectations. Rejected on its face here because it changes an
   example's answer to make the SDK look adopted, which is what `D-IMPL-261`
   forbids — recorded so the option is on the record as considered.

**The migration is not lost.** It is reproducible from this row: the adapter
shape is `tests/examples/test_s1_01_governed_resolver_adoption.py::_wire`, and
the two wiring details that cost time are worth carrying — `Scenario` needs the
manifest artifact key for the request contract (`request-contract`), which is
**not** the Control Plane pin `product-governance.yaml` declares under
`request_contract_key`; and the record is read back from the store through
`ServedProduct.replay_ref` rather than kept from a step the deployment no longer
performs.



---

## `MOD-05` — BLOCKING. The canonical path seals the graph store's moving head inside the content address, so the same question no longer seals to the same address.

**Status:** OPEN. Blocks s1-01. Outside `D-IMPL-308`'s fence. Needs a ruling.

**Measured by diffing two runs of the identical question**, same subject, same
instants, two whole runs against two graphs. Every product field byte-identical
except one:

```
DIFFER store_snapshot_pin
   run1: {'substrate': 'fluree', 'pin': '74342'}
   run2: {'substrate': 'fluree', 'pin': '74409'}
```

`GovernedResolver` sets `store_snapshot_pin=execution.store_snapshot_pin` inside
`ProductLineage`, which is inside the sealed product and therefore inside the
content address. **s1-01's hand-composed spine set none**, which is why
`tests/examples/test_s1_01_output.py::test_the_products_address_survives_a_different_graph_identity`
passed before the migration and fails after it. Its own words: *"The content
address is byte-identical, which is what makes replay a property of the question
and the Control Plane rather than of where the bytes happened to be stored."*
`test_the_record_carries_all_five_dimensions` fails for the same reason.

**Why this is not `D-IMPL-308`'s to fix.** That ruling authorized four things —
graph boundary, distinct decision instant, TTL from the proper anchor, declared
source-refresh recency — and said in terms: *"Do not redesign temporal semantics
generally."* A store head is none of the four.

**Why it is a real question and not obviously a defect.** `24.5-L-02` put the
pin there as *"the head the engine read once before its first query, beside the
temporal anchor and never inside it"*, and replay plausibly wants to know which
store state was read. Against that: a ledger head advances on its own, so two
callers asking the same question of the same logical state get different
addresses, and the ladder's central claim is *same question → same answer*.
cp-05's reproducibility claim is already bounded to *"a quiescent ledger for that
run"* — which is this issue, priced in rather than resolved. The question to
answer first is the one `24.11-C-01` framed: **what does the identifier claim to
identify?**

**Options, none taken:**

1. **Move the pin out of the sealed lineage** and carry it as evidence beside
   the address, where the replay reference already lives. The two s1-01 failures
   resolve and the migration lands unchanged. Changes what every existing
   product's address is a function of, so digests move — `D-IMPL-293` says
   nothing has shipped and digests are consequences to regenerate.
2. **Keep it sealed and rule the address a function of the store state.** Then
   `test_the_products_address_survives_a_different_graph_identity` is asserting
   something the SDK no longer claims, and it is the test that must be
   re-authored — with a ruling, never quietly.
3. **Leave s1-01 reverted and migrate `s1-00` first.** `s1-00` is clear of
   `MOD-04`'s two findings (measured); whether it is clear of this one is
   **unmeasured**, and it will not be until an adapter is built for it, because
   the pin is only populated on the canonical path.
