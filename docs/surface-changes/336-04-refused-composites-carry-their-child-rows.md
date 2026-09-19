# D-IMPL-336 CMP-R-01 — a refused composite records which children it tried

Applied 2026-09-13 under `D-IMPL-336` Amendment 5 §5, which completes
**CMP-R-01**. Amendment 4 authorized the protocol change and required the
surface to be **recorded before it is implemented**; this fragment is that
record, and it lands in its own commit ahead of the code.

## The gap

`compose_children` builds a `ChildResolution` row for **every** requirement,
refused or not — deliberately, because *"a requirement that produced nothing
and left no row would be indistinguishable from one that was never declared"*.
Those rows reach the persisted record on the **served** path only.

A refused composite records through `RefusalRecorderProtocol.record`, which has
no parameter for them. So the one case where a reader most needs to know which
child failed — the composite refused — is the case where the record does not
say.

## Why it was not simply added earlier

It was added once and **backed out**. `RefusalRecorderProtocol` is a public
seam with three callers, and shipping a parameter that the protocol accepted
and the implementations ignored would have been the exact defect class this
work exists to repair. Closing it properly is a protocol change, and a protocol
change gets recorded before it gets written.

## What changes

- **`ccf.products.resolver.RefusalRecorderProtocol.record`** gains
  `child_resolutions: tuple[ChildResolution, ...] = ()`. Defaulted, because
  every existing caller refuses something that is not a composite and `()` is
  the true statement for them — *this refusal concerned no declared children* —
  rather than a filler value.
- **`ccf.products.resolver.ReplayRefusalRecorder.record`** forwards it to
  `build_replay_record`, which already accepts `child_resolutions` and writes
  it to `ContentGenerationPath`.
- **`GovernedResolver._record_refusal`** passes the rows a refused composition
  produced.

## What does not change

The ordering invariant (`D-IMPL-256`) is untouched: the record is appended
first and the returned shell is the one the append addressed. Nothing about
which module may mint replay moves. `ChildResolution` and
`ContentGenerationPath.child_resolutions` already exist and are already
hash-transparent at `()`, so **no content address moves** — a non-composite
refusal records exactly the bytes it recorded before.

## Surface entries

## ccf.products.resolver.RefusalRecorderProtocol.record

- Surface: ccf.products.resolver.RefusalRecorderProtocol.record
- Public surface: true
- Change type: behavior
- Before: no parameter for child resolutions, so a refused composite's persisted record could not name the children it tried
- After: accepts `child_resolutions`, defaulted to `()` (D-IMPL-336 CMP-R-01)
- Why: the case where a reader most needs to know which child failed is the case the record was silent about The manifest records exports, not attributes or methods, so this change has no diff line; the entry's type was corrected from `reshaped` to `behavior` at the `f0656746` qualification (2026-09-19).
- Migration: none required — the parameter is defaulted and `()` is the true claim for every non-composite refusal; a deployment substituting its own recorder may accept and forward it

## ccf.products.resolver.ReplayRefusalRecorder.record

- Surface: ccf.products.resolver.ReplayRefusalRecorder.record
- Public surface: true
- Change type: behavior
- Before: forwarded no child resolutions to `build_replay_record`
- After: forwards them, so a refused composite's persisted record carries one row per declared requirement (D-IMPL-336 CMP-R-01)
- Why: the reference implementation must actually satisfy the widened seam, or the parameter would be accepted and ignored — the defect class this phase repairs The manifest records exports, not attributes or methods, so this change has no diff line; the entry's type was corrected from `reshaped` to `behavior` at the `f0656746` qualification (2026-09-19).
- Migration: none required
