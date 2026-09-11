# Findings — cp-06 collateral & set-off coverage

Adjudicated under `D-IMPL-315`: *"canonical path is richer"* is a finding to
adjudicate, never a licence to edit the example. Each entry states whether the
defect is the SDK's, this example's, another example's, or the estate's.

---

## `CP06-F-01` — cp-04-canonical reports `unreported` for the store watermark against the curated estate

**Status: OPEN. Defect in ANOTHER example (`examples/cp-04-canonical-corporate-family-tree`),
already merged to `main`. Found while writing cp-06's own graph leg, which
inherited the same code shape. NOT fixed on this branch — that would mix two
claims behind one review.**

### The defect

Both examples read the ledger's transaction index by matching the server's
listing on **name and branch**, which Fluree keys separately:

```python
name, _, branch = self._ledger.partition(":")
```

A ledger named `ccf:cp04-<uuid>` partitions correctly. A ledger named
**`fibo-v2`** — the curated estate, and the value cp-04-canonical's own README
tells the reader to export — partitions to `name="fibo-v2"`, `branch=""`, which
matches no entry in the listing. The function then returns its honest fallback,
`"unreported"`.

Measured 2026-09-10, same process, same estate:

| example | ledger | watermark |
|---|---|---|
| cp-06 (before fix) | `fibo-v2` | `unreported` |
| cp-06 (after fix) | `fibo-v2` | **`5545`** |
| **cp-04-canonical (shipped)** | `fibo-v2` | **`unreported`** |

### Why it was invisible

cp-04-canonical's tests and my development runs used a *seeded* ledger, whose
name carries an explicit `name:branch`. The bug only appears against a bare
ledger name — which is exactly the curated estate, and exactly what shipped.
The fallback is well-behaved and says `unreported` rather than raising, so
nothing failed; a provenance field is simply empty where it should carry `5545`.

### Severity

**Not a wrong answer, but a missing one.** The watermark is execution
provenance recorded in replay (`D-IMPL-309`); it does not enter the product's
content address, so no determination is wrong and no address moves. What is
lost is the ability to say which store state a decision read — for every run
against the estate the example documents.

### Fixed here, not there

cp-06's `acquisition.py` defaults the branch to `main` when the ledger name
carries no `:`. The identical two-line change applies to cp-04-canonical.
It is **not** applied on this branch: cp-04-canonical is not frozen
(`D-IMPL-313` — the successor is explicitly not under `D-IMPL-261`), so the fix
needs no ruling, but mixing it into a rung-6 branch would put two unrelated
claims behind one review, which is the separation `D-IMPL-317` was written to
preserve.

**Recommended:** a one-commit branch off `main` carrying the two-line fix and a
regression that asserts a bare ledger name resolves a watermark.


---

## `CP06-F-02` / `CP06-F-03` — the MCP door had never been booted, and both defects were in it

**Status: FIXED, 2026-09-10, after `D-GATE-cp-06`. Found from OUTSIDE this
example — by building cp-07's door, which inherited the same code shape, and
driving it. Recorded here under cp-07's identifiers (`CP07-F-08`, `CP07-F-09`)
because that is where the measurement was taken.**

### The root cause of both: nothing ever opened the door

This example shipped `server/door.yaml`, `server/serve.py`, and one test —
`test_the_door_declares_its_entrypoint_rather_than_a_script_path` — which reads
the YAML and asserts an entry point is **declared**. It is a correct test of a
real property and it cannot see either defect below, because **a door that has
never been opened passes every test written about its declaration.**

`tests/examples/test_cp_06_mcp_door.py` now boots the shipped door and drives it
with the shipped cp-04 MCP driver. That is the guard; the two fixes are its
consequences.

### `CP06-F-02` (`CP07-F-08`) — the first call answered `unable to open database file`

```python
resolver=build_resolver(root=root / "assembly"),
```

`root / "assembly"` was never created. `deployment.connection` then handed
SQLite a path inside it, and SQLite does not create a missing parent. Measured
against the curated estate:

```
cp-06 door isError: True | Error executing tool request_context_product:
                           unable to open database file
```

It arrives as an **MCP transport error**, which from a consumer's side is
indistinguishable from a producer that never started. Fixed by creating the
directory where it is named.

### `CP06-F-03` (`CP07-F-09`) — a governed "no" arrived as a runtime failure

```python
if not facility or not scope:
    return RefusalEnvelope(
        reason="missing-required-argument", key=..., detail=...)
```

`RefusalEnvelope` declares none of those fields. It requires `kind` — from the
SDK's own `REFUSAL_KINDS` vocabulary — plus `fields`, `request` and
`pre_assembly_lineage`. The constructor raised a `ValidationError`, the egress
layer caught it as a runtime failure, and the caller received
`ccf-runtime-failure:<id>`, which the SDK's own docstring reserves for *"CCF or
its runtime failed"* and explicitly promises a governed determination never
arrives as.

**Fixed by DELETING the check, not repairing it.** `facility_id` and
`borrower_scope` are `required` in the request contract, so the Control Plane
already refuses a question missing either — and does it properly:

```
kind      : product-request-violation
detail    : the question does not conform to the contract it addresses
replay_ref: present
isError   : false          # a governed refusal is a SUCCESSFUL response
```

This is `D-IMPL-289`: code that reconstructs what should have been declared dies
with the declaration. Two smaller compensating paths went with it —
`deployment.request` now builds the question **as asked** rather than validating
an anchor the Control Plane owns, and `acquire_for` no longer reads either source
store when governance has refused (`acquisition.nothing_acquired`).

### Sabotage-verified, both

Re-introducing each defect reds exactly the test that names it: removing the
`mkdir` returns `unable to open database file` on the first call, and restoring
the hand-rolled envelope returns `ccf-runtime-failure:<id>`. The in-process path
is untouched — `make example-cp-06` still serves `COVERAGE 1.0890` at
`D_c 0.376895431605010680`.
