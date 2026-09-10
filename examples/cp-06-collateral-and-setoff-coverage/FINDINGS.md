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
