# 364-01 — the temporal write refusal converts at the acquisition seam

`D-IMPL-364` SEC-008 B2 (Dave's choice 1: *"Add `TemporalWriteRefused` to
`SDK_SEAM_REFUSALS` for governed serves."*). Measured before this entry: when the
fabric's second clock read at the seam (`ingress_at`) had moved past the first
(`served_at`) and the paved road's per-question stamp fell outside the tenant's
window, `TemporalWriteRefused` escaped `OpenedProduct.answer` as an untyped error
with no replay record. It now converts through the SDK-owned seam map into a
governed refusal with a record, the way `IdentityRefused` does.

**The public meaning, ruled (Dave, 2026-10-04): the 404 mapping stays.** The
refusal is a `SubjectUnavailableRefusal` (kind `subject-unavailable`) with cause
`nonexistent` — the fabric holds no admissible observation for this question at
this instant — and error code `temporal-write-refused`. The HTTP door maps the
kind to 404 at every disclosure level, by the rule that the status is taken from
the disclosed kind and never from the internal cause, so that no status tells a
principal whether a subject exists. The same window breach judged at the request
is a `TemporalBoundRefusal` (400); the two are different facts — a question
outside the window, and a write the fabric would not accept at the instant it
tried — and are deliberately not collapsed.

## ccf.products.resolver.SDK_SEAM_REFUSALS

- Surface: ccf.products.resolver.SDK_SEAM_REFUSALS
- Public surface: false
- Change type: behavior
- Before: one entry — `ccf.assembly.worker.IdentityRefused` → cause `nonexistent`, code `identity-refused`. A `ccf.signal.envelope.TemporalWriteRefused` raised inside the acquisition seam on a governed serve escaped `OpenedProduct.answer` as a traceback, and no replay record was written.
- After: two entries — `ccf.signal.envelope.TemporalWriteRefused` → cause `nonexistent`, code `temporal-write-refused`. On a governed serve the refusal is minted by the resolver as a `SubjectUnavailableRefusal` at seam `acquisition`, recorded on dimension 5 (`assembly_refusal` carries the cause, the code and the guard's own detail, which names the envelope id, the policy key, both instants and the tenant's declared reach), and delivered through the ordinary disclosure step. At `minimal` (the default) and `reasoned` the consumer sees kind `subject-unavailable`, detail "the requested subject is not available to this principal under this product", and `cause` / `error_code` withheld as `undisclosed`; at `full` the shell carries `nonexistent` / `temporal-write-refused` and the guard's detail. The HTTP door answers 404 at every level. The writer is never reached: zero writes, no restamp.
- Why: `D-IMPL-364` SEC-008 B2 — the seam's own write refusal on a governed serve is a recorded governed refusal, not an escaped exception; the record is where the true reason lives. Cause `nonexistent` is the closed `RefusalCause` reading `IdentityRefused` already carries and the map admits no other; the 404 is the kind's, chosen so that a timing refusal and an entitlement refusal are indistinguishable to a principal who is not entitled to know which. Ruled to stay (Dave, 2026-10-04).
- Migration: none for a caller — the type still exists. The writer itself raises no `TemporalWriteRefused` (it judges no instant); a low-road composition that composes `IngressTemporalBound` and invokes `refuse_outside_window` before its own `ingest` receives the raw exception from that call, and one that does not compose the guard receives nothing. A consumer of the product doors that keys on `cause` alone cannot distinguish this refusal from a missing subject below `full`; a consumer entitled to `full` reads `error_code` `temporal-write-refused`. An operator reads the replay record. A deployment whose serves take longer than the tenant's declared past reach between `asked_at` and the seam's `ingress_at` will see this refusal on otherwise-sound questions; the remedy is the tenant's `TemporalBoundaryPolicy`, not the question.
