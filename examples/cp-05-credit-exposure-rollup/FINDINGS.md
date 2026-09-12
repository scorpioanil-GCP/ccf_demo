# Findings — cp-05 credit exposure rollup


---

## `CP05-F-01` — four of §G.2's eight acceptance criteria had no test that asserted them

**Status: FIXED, 2026-09-11.** All four now have an executing test and are
declared. `artifacts/gates.yaml` carries **8 of 8**.

| id | what was written |
|---|---|
| `CER-G04` | two limit regimes, same anchor. `group-limit-test` counts guarantees and deducts; `internal-appetite` counts none and adjusted stays level with gross. Asserted as a relationship, never a figure. |
| `CER-G05` | the reconciliation guard **observed firing** on a rollup made to double-subtract, after the real determination is confirmed to pass. The positive half runs first, so a guard that refused everything could not satisfy it. |
| `CER-G06` | two regimes must not hash to one content address, or replay cannot tell which authorized the answer. |
| `CER-G07` | one traversal operator carries all four relationship types, so the family is walked once. |

**Two of the four corrected their own criterion when measured.**

`CER-G04` — I first asserted that the regime counting NEITHER guarantees nor
undrawn would return the SMALLER adjusted figure. The estate said otherwise, and
it is right: `counts_guarantees=False` means the guarantee **deduction** is not
applied, so adjusted stays level with gross at $10.125B while the broad regime
falls to $9.325B. Counting fewer things toward an adjustment removes less, not
more. The test now asserts the relationship that actually holds.

`CER-G06` — §G.2 words this as *"a replay at a different `policy_version`
produces a different one"*. Measured, both regimes record the **same**
policy-bundle version, and that is correct: the limit definition is a versioned
row in `ccf_v2.limit_definition`, read as estate data, not a Control Plane
bundle. The test asserts the property the criterion exists to protect — the two
answers must not share a content address — and asserts the bundle version
*stays* equal, so mistaking estate data for a bundle version would go red.

`CER-G07` — §G.2 asks for *"a single ledger `t` in lineage"* as the evidence.
That evidence does not exist here: cp-05's lineage carries `graph_snapshot_at`,
the decision instant. The property is asserted instead against
`operators_invoked`. Note that `assembler.acquire_edges` **does** loop per
predicate — and its own docstring says why that is a different thing:
acquisition reads someone else's graph to populate L3, and the traversal that
answers the product's question runs over L3 afterwards. Only the second is the
product's claim.

## `CP05-F-02` — every output test was COLLECTED and none of them EXECUTED

**Status: FIXED in this sitting (`D-IMPL-327`). The two-line cause is repaired,
the eight assertions are unchanged, and the reason it went unnoticed is the part
worth keeping.**

### What was measured

`produce.produce_governed` returns **three** values — `payload, governed,
record`. The `matrix` fixture in `tests/examples/test_cp_05_output.py` unpacked
**two**. Every test in the module therefore raised
`ValueError: too many values to unpack (expected 2)` during fixture setup:

```
8 passed  →  became  →  0 passed, 8 errors
```

Measured at the branch base as well as on the branch, so this predates the gate
work. **cp-05 has had no output-level test coverage**, and nothing said so.

### Why nobody noticed, which is the finding

**An erroring test is still a COLLECTED test.** `pytest --collect-only` lists
all eight node ids; the failure happens later, at fixture setup. Any instrument
that asks *"did pytest collect this node id?"* — which is exactly what
`tools/check_product_gates.py` asks, by design and for good reasons — reports
the module present and healthy.

So the gate roster built in `D-IMPL-327` would have declared four gates against
three tests that could not run, and the checker would have called cp-05 green.
**The gate wiring is what surfaced this**: mapping a declared obligation onto a
named test is what made someone run that test directly and look at the result.

Dave's ruling on the limitation, verbatim: *"Do not redesign the gate checker in
this sitting. Its collection-only limitation is now known; direct pytest
execution proves these four gates here."*

### The repair, and what it deliberately is not

```python
payload, governed, _record = produce.produce_governed(...)
```

Named `_record` rather than `*rest`, so a fourth return value fails here loudly
instead of being swallowed by the same silence that hid this one.

**No assertion was added, removed or weakened.** The eight tests' bodies are
byte-identical to what they were; only the fixture's unpack moved. This is the
`D-IMPL-261` allowed case — *"the SDK surface it legitimately consumes was
deliberately changed"* — applied to the example's own producer, whose signature
gained a third return value while its test was not updated. It is an
objectively stale test, not a change made to get a product to pass.

All eight now execute and pass against the curated estate.


---

## `CP05-F-03` — three artifacts failed the schema-header gate, and none of them failed as a HEADER

**Status: FIXED, 2026-09-11. Not an SDK issue.** The rule the gate enforces is
the SDK's and is correct; these three documents violated it. The caution
recorded when this was first diagnosed — that quoting the values would change
what four assertions compare — **was measured and did not hold.**

| document | what the gate said | what was done |
|---|---|---|
| `artifacts/expected.yaml` | four float values | quoted — 4 floats, 0 remain |
| `artifacts/question.yaml` | `materiality` is a float | quoted |
| `artifacts/scenarios.yaml` | `declaration` is a list where `DeclaredArtifact` requires a mapping | the list moved under a named key, `consumers` |

**Why the feared blast radius was not real.** The one assertion that consumes a
quoted value already wrote `Decimal(str(naive["understates_gross_family_by_factor"]))`
— the `str()` makes a quoted value and a float identical to it. The other
changed fields are read by no test at all. Measured after the change: **cp-05's
8 output tests pass, unchanged**, and `CER-G01`/`CER-G02` are unaffected.

**`scenarios.yaml` needed a shape decision, and it is the smallest honest one.**
The document IS a declaration of a set of consumers, so the eight entries now
sit under `declaration.consumers` and `run.py` follows the key. No entry, value
or parameter changed; `run.py --scenarios` prints the same eight consumers.

**No `deferred` marker was used.** The gate offers
`# ccf-schema: deferred(<plan>) <reason>`, which would have turned red to green
while changing nothing about the documents — the move this project refuses
everywhere else, and the reason this finding stayed open rather than being
silenced when it was first diagnosed.

