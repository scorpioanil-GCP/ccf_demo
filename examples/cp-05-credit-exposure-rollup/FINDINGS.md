# Findings — cp-05 credit exposure rollup


---

## `CP05-F-01` — four of §G.2's eight acceptance criteria have no test that asserts them

**Status: OPEN. Recorded at the sitting that gave §G.2 stable ids
(`D-IMPL-327`), rather than declared against tests that do not prove them.**

`CP-SPEC-005` §G.2 declares eight acceptance criteria. `artifacts/gates.yaml`
declares **four**. The other four are named here with what each would need.

| id | criterion | why it is not declared |
|---|---|---|
| `CER-G04` | the same anchor under `internal-appetite` vs `group-limit-test` returns a different adjusted figure | neither regime name appears anywhere in the test tree; proving it needs two policy regimes wired and a comparison across them |
| `CER-G05` | all four validation gates pass, **and the reconciliation guard is observed firing** on a deliberately double-subtracting variant | see below — this is the one that looked covered and is not |
| `CER-G06` | replay from recorded lineage reproduces the payload hash, and a replay at a different `policy_version` produces a different one | `policy_version` appears in no test; needs a replay harness that can vary it |
| `CER-G07` | the traversal issues **one** walk, not one per predicate — evidenced by a single ledger `t` in lineage | needs ledger-`t` instrumentation on the lineage record |

### `CER-G05` is the instructive one: token presence is not token force

The first measurement of this roster probed each criterion by searching the test
tree for its distinguishing term. `reconciliation` **is** present in
`test_cp_05_output.py`, so the criterion was first read as covered. It is not.
What that test asserts is:

```python
assert payload["reconciliation"] is not None
```

— that the member is **present**. The criterion requires the guard to be
**observed firing** on a deliberately double-subtracting variant. Those are
different claims, and only one of them is held against a run.

Declaring `CER-G05` against that test would have been the `L-18` defect the
gate checker exists to catch: a declaration pointing at a test that does not
prove its statement. The roster is smaller and honest instead.

### What was NOT done

**No new instrumentation** (`D-IMPL-327`, Dave: *"Do not create new
instrumentation in this sitting ... New tests for those belong in a separate
sitting if we decide they are worth funding."*) And **no criterion was
reworded, renumbered or removed** to make the roster look complete — §G.2 says
exactly what it said, plus an id per criterion.


---

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

