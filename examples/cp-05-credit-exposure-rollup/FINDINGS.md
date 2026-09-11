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

## `CP05-F-03` — three artifacts fail the schema-header gate, and none of them fails as a HEADER

**Status: OPEN. Diagnosed and STOPPED at the 2026-09-11 hygiene sitting, on
Dave's own boundary for it: *"schema-headers on cp-05 artifacts is the same
sitting if it is actually a header, not a product change. If it needs new
criteria, stop and record."* It needs a ruling on all three.**

`make schema-headers` is red on exactly three documents, and it has been red on
`main` for as long as the measurement goes back. The gate names them precisely,
and each is a different problem wearing one error message.

| document | what the gate says | what it actually is |
|---|---|---|
| `artifacts/expected.yaml` | `declaration.measures.adjusted_differs_from_gross_by_pct` is a float | a **value-type change to a comparison fixture** |
| `artifacts/question.yaml` | `declaration.parameters.materiality` is a float | the same class, on the request side |
| `artifacts/scenarios.yaml` | `declaration` is a list where `DeclaredArtifact` requires a mapping | **structural** — the document is not a declared artifact at all |

### Why the first two are not header work

The rule the gate enforces is real and is the SDK's: *"float values are not
admissible in a Control Plane artifact (not bit-stable across platforms); quote
the value so it parses as text and is validated as a decimal."* The repair is to
quote `7.90` and the materiality value.

But `expected.yaml` is **the declaration cp-05's tests compare the served payload
against** — `test_the_measures_are_what_the_declaration_says` and
`test_the_naive_answer_understates_by_the_declared_factor` read it, and
`CER-G01` and `CER-G02` are declared against those tests. Changing a value's
TYPE there changes what four assertions compare, and one of them already does
`Decimal(served) / Decimal(naive[...])`. That is a product change with gate
consequences, not a header edit, and it is exactly what the boundary excludes.

### Why the third is a different question entirely

`scenarios.yaml` carries a **list** under `declaration`. `DeclaredArtifact`
requires a mapping, so this document cannot be that class no matter what header
it names. The available moves are a different artifact class, a wrapping key, or
the `# ccf-schema: deferred(<plan>) <reason>` marker the gate itself offers —
and choosing among them is a decision about what the document IS.

### What was NOT done

No value was quoted, no document reshaped, no `deferred` marker added. A
`deferred` marker in particular would turn a red into a green while changing
nothing about the document, which is the shape this project refuses everywhere
else.
