# D-IMPL-338 — a composite's child evidence survives every downstream refusal

Applied 2026-09-14 under `D-IMPL-338`, the ruling recorded at `57d045c9`.
Exclusively scoped to `CP14-F-09`.

## The gap

`D-IMPL-336` `CMP-R-01` widened `RefusalRecorderProtocol.record` with
`child_resolutions` and threaded the rows through **two** of the exits a
composite can take after its children were acquired: the served path and the
*composition* refusal. It left the other three — the universal-gate refusal,
the declared-product-gate refusal and the **tolerance** refusal — calling
`_record_refusal` without them. A composite refused for excess *inherited*
debt therefore wrote a record that did not say which children it inherited it
from. Measured at `CP-SPEC-014` Gate 1 (`resolver.py` 2224 / 2260 / 2300 at
`bff2ff17`).

## What changes

- **`GovernedResolver.__call__`** binds the rows **once**, immediately after
  the composite block — `child_rows = composed.resolutions if composed is not
  None else ()` — and every exit below it reads that one binding: the served
  record and all four post-acquisition refusals. The two refusals *above* the
  composite block are untouched and pass nothing: no child was considered
  there, and `()` is the true claim rather than an invented outcome.
- **No protocol changes.** The recorder seam already accepted the parameter;
  `build_replay_record` already wrote it to dimension 5.

## What does not change

`ChildResolution`'s shape, `compose_children`, the four composition laws, the
gates, the tolerance comparison, the disclosure layer and the ordering
invariant (`D-IMPL-256`) are untouched. The rows are record content and are
never part of the disclosed shell. Every non-composite refusal still records
`()`, which is hash-transparent, so **no existing record's content address
moves**.

## Surface entries

## ccf.products.resolver.GovernedResolver.__call__

- Surface: ccf.products.resolver.GovernedResolver.__call__
- Public surface: true
- Change type: behavior
- Before: a composite refused by the universal gates, the declared product gate or the tolerance comparison recorded no `child_resolutions`, although its children had been acquired and composed
- After: every refusal reached after child acquisition records the same child rows the served path records; refusals reached before acquisition record `()`
- Why: a tolerance refusal is the case that most needs its children named — the debt it refused on is inherited — and it was the case the record was silent about
- Migration: none — no signature or record shape changes; a deployment substituting its own `RefusalRecorderProtocol` already receives `child_resolutions` and should forward it
