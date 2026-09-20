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
`examples/s1-01-hello-context-product/spine.py::assemble_and_serve`,
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
`src/ccf/products/resolver.py::GovernedResolver.__call__` calls
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
`examples/s1-01-hello-context-product/spine.py::assemble_and_serve`,
`refuse_request(request=scenario.request, declared=scenario.request_contract)`.

**It is not uniquely load-bearing.** Measured across the shipped trees,
`ccf.products.request::refuse_request` has **8** call sites — cp-00, cp-01,
cp-02, cp-03, cp-04, cp-05's MCP door, s1-00 and s1-01. No floor constant counts
them. Deleting s1-01's leaves seven.

**But two SDK docstrings name s1-01 specifically:**

* `src/ccf/products/request.py::refuse_request` — *"`examples/s1-01-hello-context-product/spine.py::assemble_and_serve`
  is the shipped worked example."* Migration makes this false, because the
  function would no longer make the call.
* `src/ccf/products/bind.py` — *"Each has one shipped call site to read …
  and `examples/s1-01-hello-context-product/spine.py::assemble_and_serve` for
  the request refusal."* **This is already stale on today's tree**, before any
  migration: there are eight, not one. Measured, not read off the prose.

`src/ccf/products/resolver.py::GovernedResolver` and `:2466` also cite s1-01's spine, but as
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

**Status:** **RULED — `D-IMPL-309`, 2026-09-09.** Neither option 1 nor 2 as
written: the head is **removed from the sealed models**, not moved beside the
address and not left sealed. Dave: *"Logical determination identity is
addressed. Physical store furniture is recorded."*

**A third option the three below did not contain, and the measurement that
produced it.** Option 1 was first implemented as a fourth
`ccf_hash_transparent` posture — *ambient*: never rendered at any value — and
**backed out**, because `canonical_bytes` is at once the address input, the
stored form and the wire form:

```
original pin : substrate='fluree' pin='74342'
roundtripped : substrate='none'   pin='no-store-snapshot-pin'
```

A field omitted from that form is not excluded from identity, it is **erased**
and read back as its sentinel — a positive claim that the substrate exposes no
head. So the field is removed outright: `ProductLineage`,
`ComputedEmptyFinding` and `RefusalEvidence` no longer declare it, and because
they are `extra=forbid` a deployment that still passes it is refused by name
rather than silently losing the value. `ContextFabricSnapshot`,
`ExecutionResult` and `replay()`'s pin comparison are untouched — the stop
condition (*does replay retain and compare the head independently of the
product?*) was measured **before** any edit and satisfied.

Two sabotages, both RED: reintroducing the field into sealed identity, and
stopping the recording of the head. The full ruling, the withdrawn claim and
the carried reds are in `docs/DECISIONS.md` under `D-IMPL-309`.

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

---

## `MOD-06` — BLOCKING for s1-01's last test. The canonical path pins the request contract into replay dimension 2; the hand-composed spine pinned only the policy bundle, and s1-01's test asserts dimension 2 equals the product's single lineage version.

**Status:** **RULED — `D-IMPL-310`, 2026-09-09.** A stale example assertion, not
an SDK defect: the canonical path is more complete, and
`product lineage policy bundles ⊆ replay dimension-2 bindings` was never an
equality. **No SDK code changed.** The test was made *more* precise — both
limbs checked against sources independent of the record — and sabotage-proven
four ways. Not a value disagreement and **not** the store pin: the two sides
agree about every version they share.

**Measured on a real canonical run** (`tests/examples/test_s1_01_output.py::
test_the_record_carries_all_five_dimensions`):

```
LINEAGE (product.lineage.policy_bundle_versions):
   5520f88f7b9ee813008800e52e097cea128479d58162b785aa48e23dbec3eff8

RECORD (record.policy_bindings.bindings):
   key='policy-bundle'     version='5520f88f…e23dbec3eff8'   <- same value
   key='request-contract'  version='bdc2343d…0938ccd8b1956f86'  <- the extra one
```

The canonical path records **one binding more**. `GovernedResolver` reads the
policy version once (`src/ccf/products/resolver.py::GovernedResolver.__call__`) and uses it for both
the lineage and the record, so those cannot diverge; what it *additionally*
pins is the version of the **request contract** artifact that governed the
question. The hand-composed spine built dimension 2 with exactly one
`PolicyBinding`, so the test's equality held trivially.

**The test, unchanged:**

```python
assert [binding.version for binding in restored.policy_bindings.bindings] == [
    _the_one_policy_version(result)
]
```

`_the_one_policy_version` reads `result.product.lineage.policy_bundle_versions`
and asserts it has exactly one member.

**Why this is a question and not obviously either answer.** Dimension 2 is the
*Policy Bindings Snapshot* — whitepaper §7.10.1 — and a request contract is a
Control Plane artifact whose version genuinely governed the decision, so
pinning it is arguably what the dimension is for and the canonical path is
**more** complete. Against that: the product's lineage carries
`policy_bundle_versions`, and if dimension 2 is to be a superset of it then the
example's assertion is comparing two sets that were never the same set, and it
happened to pass only because one spine populated both from one value.

**What was NOT done.** The test is untouched (`D-IMPL-261`: an example's
assertion is not rewritten to accommodate an SDK surface it just met). The
failure is left executable and visible.

**Options, none taken:**

1. **Rule dimension 2 a superset and re-author the assertion** to hold the
   product's lineage version to *membership* in the record's bindings rather
   than to equality with the whole list. The example then asserts what it
   actually cares about — the version that produced the answer is the version
   the record names — and stops asserting how many other bindings exist.
2. **Rule the request-contract pin misplaced** and move it out of dimension 2.
   It would need somewhere to go; dimension 5 already pins the request itself.
3. **Rule both correct and the assertion simply stale**, re-authored with a
   ruling recorded, on the `D-IMPL-306` precedent for a test-model correction
   caused by SDK evolution.

**Everything else s1-01 was asked to preserve is green** — see the migration
note below.

---

## s1-01 migration — LANDED, one red

`spine.py` is canonical: **634 → 426 lines**, the seven `D-07` regions replaced
by `boot` / `acquire` / `govern`, and
`tests/examples/test_spine_separation.py::shape_of` classifies the directory
**`canonical`** (not half-migrated) from the AST — 60 passed.

Preserved, measured, with no re-pin and no expectation weakened:

| required | result |
| --- | --- |
| graph boundary `00:00`, decision instant `00:05`, expiry `00:15` | green |
| source refresh recency | green |
| stable address across unrelated ledger movement | green — `test_the_products_address_survives_a_different_graph_identity`, the `MOD-05` casualty |
| store snapshot pin in replay, not on the product | green (`D-IMPL-309`) |
| no local binder | the site is **gone**; `MOD-01` discharged as `D-IMPL-307` ruled — resolved floor `12 → 11` and delegated `1 → 2` in one commit |
| canonical shape, not half-migrated | green |

`tests/examples/test_s1_01_output.py`: **39 passed** — `MOD-06` ruled and its
test corrected under `D-IMPL-310`. **s1-01 is fully modernized.**

---

## `MOD-07` — RULED (`D-IMPL-311`). BLOCKING for one s1-00 test. The canonical path returns a governed `RefusalEnvelope` where the hand-composed producer returned a bare `ProductRequestViolation`. Same reason, same key, plus a replay reference — but a different type on the CONSUMER surface.

**Status:** **RULED — `D-IMPL-311`, 2026-09-09.** Option 1: the envelope is the
canonical consumer-facing refusal; the violation is the internal representation.
Three sites re-authored, the three semantic assertions kept verbatim, and
`replay_reference` newly asserted. No SDK change. Two sabotages, both RED.

**Measured**, on `test_a_missing_threshold_is_refused_not_defaulted`:

```
RefusalEnvelope(kind='product-request-violation',
                reason='missing-required-parameter',
                key='revenue_threshold',
                detail=…, replay_reference='…a8eb6e31', …)
```

The three things the test actually asserts about the refusal all still hold —
`reason`, `key`, and that nothing was assembled (`not hasattr(outcome,
"product")`; neither type has a `product` member). What fails is the fourth:

```python
assert isinstance(outcome, ProductRequestViolation)
```

**What each carrier holds:**

| | fields |
| --- | --- |
| `ProductRequestViolation` | `reason` `key` `detail` + `declared_keys` `declared_type` `presented_keys` `presented_type` `overrides` |
| `RefusalEnvelope` | `reason` `key` `detail` + `kind` **`replay_reference`** `policy_bindings` `disclosure` `request` `pre_assembly_lineage` `evidence` `provenance` `resource` `fields` |

**Why this is a question and not obviously either answer.** The envelope is
strictly better governance evidence — the refusal is *recorded*, and a consumer
holding it can name the decision record that authorized the refusal, which a
bare violation value cannot. That is the `D-IMPL-251` shape (*refusal of
fulfillment, not of response*) and the `D-IMPL-310` shape (the canonical path
carries more). Against that: **this is the consumer surface**, which is s1-00's
whole teaching point. `examples/s1-00-companies-over-revenue/consume.py::main`
branches on `isinstance(outcome, ProductRequestViolation)`, and
`produce.py::assemble_and_serve` declares `-> Assembled | ProductRequestViolation`
in its signature and argues for it in its docstring: *"A refusal is not an
exception: a bad question is a bad question, not a broken deployment, and a
verdict returned as a value cannot be swallowed by a bare `except`."* That
argument survives the change intact — an envelope is still a value — but the
type in it does not.

**Options, none taken:**

1. **Rule the envelope the canonical refusal carrier** and re-author the three
   sites (`produce.py`'s signature and docstring, `consume.py`'s branch, the
   test's `isinstance`) to say `RefusalEnvelope`, with the ruling recorded. The
   example then teaches the governed refusal, including that a refusal has a
   replay reference — which is arguably a better lesson than the one it teaches
   now.
2. **Rule that a canonical producer may narrow the envelope back to the
   violation** at its own boundary, keeping the consumer contract fixed. Costs
   the replay reference at the consumer surface unless it is passed separately.
3. **Rule the SDK should return the violation** for a request-contract failure
   and reserve the envelope for post-assembly refusals. This is an SDK change
   and would touch every canonical consumer, so it is the widest of the three.

---

## `MOD-08` — RULED (`D-IMPL-311`). BLOCKING for four gate tests. s1-00 changed ARCHITECTURAL CATEGORY, and both rosters that record such a category require a human ruling by construction.

**Status:** **RULED — `D-IMPL-311`, 2026-09-09.** The paired roster edit, in one
commit. **And the roster edit alone was not enough:** `sdk_supplied` is measured
from the tree and the predicate could not read a *lambda* `plan_factory`. Fixed
by matching cp-05's named-`def` shape — not by widening the predicate, and not
by editing the roster around an instrument that could not see the tree. Two
row-B controls that used s1-00 as their specimen were re-pointed at cp-00.

Before the migration s1-00 authored its own operator set from one document and
claimed `D-IMPL-137`'s **one-document exemption**
(`RULED_ONE_DOCUMENT_DEPLOYMENTS`, `tests/products/test_gate_two_call_shape.py::RULED_ONE_DOCUMENT_DEPLOYMENTS`).
After it, `plan_factory` consumes the resolver's `required` and s1-00 authors
none — which is the **SDK-supplied** category
(`RULED_SDK_SUPPLIED_DEPLOYMENTS`). It is currently in the first roster and
absent from the second, so the detector reports it as `D-IMPL-137` **row C** —
*a second operator set authored where the Control Plane cannot see it* — which
is the one thing it is now provably not.

Four tests are red on this: `test_the_premise_detector_reads_the_shipped_tree_correctly`,
`test_the_one_document_exemption_has_not_spread`,
`test_hw1_claims_the_exemption_for_the_stated_reason`,
`test_a_second_operator_set_outside_the_control_plane_is_refused`.

**Why this is not an executor's edit.** The roster's own comment: *"an unruled
claimant is red, and a human rules on it."* The two rosters are deliberately
separate so that *"one shared population would let either grow into the other's
room while both read green"*. cp-05 made this exact move under `D-IMPL-301`, and
Dave's words are recorded beside its entry: *"a classification update, not an
exemption swap."*

**The edit a ruling would authorize** is the same paired one cp-05 got: remove
`examples/s1-00-companies-over-revenue` from `RULED_ONE_DOCUMENT_DEPLOYMENTS`
and add it to `RULED_SDK_SUPPLIED_DEPLOYMENTS`, in one commit, with the removal
site carrying a dated comment naming the migration — exactly as the cp-05
removal site does.

---

## s1-00 migration — BUILT, two classified misses

`produce.py` is canonical: **411 → 336 lines**, the seven `D-07` regions
replaced by `boot` / `acquire` / `govern`, and `shape_of` classifies the
directory **`canonical`**.

**Eight quarantined tests were un-quarantined and pass unchanged.** All eight
carried one reason — *"frozen s1-00 produce.py calls `build_replay_record` with
no resolution state — quarantined evidence … un-quarantine and rerun unchanged
after `D-GATE-24.7`"*. `D-GATE-24.7` has passed and the migration removes the
call that caused the quarantine, so all eight `XPASS(strict)`-ed. The markers
were removed and **no test body was touched**; that is the ruled un-quarantine,
not a re-pin.

Preserved, and deliberately NOT added to:

| required | result |
| --- | --- |
| producer shape `boot` / `acquire` / `govern` | green |
| `build_governed_resolver`, no local binder, no manual gate/record/serve | green — s1-00 never had a binder call (`MOD-03` measured zero) |
| temporal semantics unchanged | **no `decision_instant_parameter` passed** — s1-00 reads the graph and stamps the decision at the same instant, and says so by naming none. The `00:00`/`00:05` distinction s1-01 needed was NOT manufactured |
| no `source_refresh_recency` added | **not passed** — s1-00 never declared one; the SDK's empty window is the positive statement |
| no F-09 declaration fields added | none passed |
| store pin is replay evidence, not identity | holds by `D-IMPL-309` |
| `shape_of` reports canonical | green |

`tests/examples/test_s1_00_output.py` + `test_s1_00_config_equivalence.py`:
**11 passed**. `tests/products/test_gate_two_call_shape.py`: **130 passed**.
**s1-00 is fully modernized.**

---

## cp-05 post-`D-IMPL-309` — the renderer corrected, the live rerun NOT run

`run.py:218` read `lineage.store_snapshot_pin`, a field `D-IMPL-309` removed.
Corrected as ruled: the head now comes from **replay**, never restored to
`ProductLineage`, and no old product semantics were republished to keep the
prior renderer shape.

**One thing the fix had to work around, and it is worth recording.** The
renderer could not resolve the record itself: `produce_governed` roots the
artifact store under a `TemporaryDirectory` that its own `finally` cleans up
before returning, so by the time `render` runs the record is gone unless the
caller passed `--replay-root`. The record is therefore read **while the store is
still alive** (`produce.py::_replay_record`, called before `fabric_root.cleanup()`)
and returned as a third element. Four call sites unpack it; `produce()` is
unaffected because it already took `[0]`.

The transcript now says the true thing in the true place: the LINEAGE block no
longer claims a store pin, and DECISION REPLAY prints it beside the record's
address with a sentence naming why it is not on the product.

**NOT DONE, and it is owed:** the live cp-05 rerun and any artifact
republication. The example needs `CCF_CP_05_FLUREE_URL`,
`CCF_CP_05_FLUREE_LEDGER`, `CCF_CP_05_POSTGRES_DSN` and
`CCF_CP_05_POSTGRES_SCHEMA`, and the values reconstructed from
`ccf_dataprep/.env` are **wrong** — the anchor `5493000Q1S5TJIDIQH89` resolves
in `ccf_v2.legal_entity` but carries no node in ledger `fibo:main`, so every
run refuses on a store disagreement. **Measured that this is not the change:**
the failure set under that environment is **identical** at the branch base and
at HEAD once correlation ids are normalized — 15 failures, all estate, none
from this edit. Without the estate the tests skip (14 skipped, unchanged).

---

## The pass CLOSES here (`D-IMPL-312`)

`s1-01` and `s1-00` are modernized and canonical; cp-05's renderer is corrected.
**cp-04 is NOT modernized in place and will not be.** It stays the `D-IMPL-261`
frozen rung-4 specimen — seven-region spine, row-B architecture, historical
published address and docs, no `GovernedResolver`.

Its modern replacement is a **new tree** (`examples/cp-04-canonical-*`, or
`cp-06`), a **new sitting** with fresh scope. The principle, which is the part
that will matter again: *historical specimens preserve evidence; canonical
successors teach current SDK usage, and one tree cannot serve both once those
roles diverge.*

**Owed, and explicitly not part of the successor work:** cp-05's live rerun and
artifact republication, blocked on the four `CCF_CP_05_*` estate values.
