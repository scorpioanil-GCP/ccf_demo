# 377-01 — SEC-020: a withheld subject is rendered over the fabric as it stood before its question's acquisition

`D-IMPL-376` ruling (3), route A: one bounded corrective round on the leak the
`D-IMPL-371` close review measured on the paved road, built red-first.
**SEC-020 stays OPEN.** The round removes one measured difference; the channels
listed below still tell a withheld subject from a nonexistent one.

**The difference this round removes.** The governed call's declared acquisition
seam ingests the ASKED subject's evidence BEFORE the plan runs. The withheld
subject's request-seed-free re-execution (`370-20`) read the fabric AFTER that
acquisition, so the plan's class seeds reached the evidence acquisition had
just put there. A subject that names nothing, asked of a source keyed on the
subject, has nothing acquired for it and walks the fabric as it stood before.
Measured on the paved fixture's class-seeded plan: under `from_decision` the
two products differed at `computed_empty`; under `from_entity_freshness` the
withheld subject was refused `ttl-refusal` and the never-acquired one
`ttl-anchor-refusal`. The exploit test is
`tests/products/test_withheld_is_indistinguishable_from_absent.py::test_the_paved_road_acquisition_seam_does_not_reveal_a_withheld_subject`.

**The rule.** When an acquisition seam is declared, the governed call reads the
fabric once, as an as-of read at the question's boundary, immediately before
the seam runs. When Π raises the withheld signal, the plan is re-executed
without the request seed over THAT state, answered by the reference semantics
(`ccf.graph.fallback.answer`). The walk reads none of the records this
request's acquisition ingested, and no record is masked. The operator registry
is not rebuilt: the re-execution reuses the one built from the view read after
acquisition (see the similarity channel below). Replay dimension 1 keeps the
real read.

**What this makes equal, as measured.** On the paved road's test fixture, a
withheld subject's served product, every member of it, and its refusal shell,
every member except `replay_reference`, matched a nonexistent subject's on both
TTL anchors. That is a measurement, not a proof. The fixture meets four
conditions, and the list below includes a measured break of each: the
acquisition is keyed on the subject; the fabric is booted for the question; no
composite child is about the subject; and no similarity operator scores an
entity the acquisition refreshed.

**What still tells them apart.** Each was measured on test fixtures; the
security how-to, section 4.12, states the same list for deployers.

- **The answer's replay reference.** `src/ccf/replay/serve.py::ReplayWriter`
  files each record under its graph snapshot id, a hash of what the plan
  actually read together with the tenant and the question's instant, and that
  name travels in `ServedProduct.replay_ref`, the MCP egress door's
  `replay_ref`, the HTTP product route's `X-CCF-Replay-Ref` header and a
  refusal's `replay_reference`. On the class-seeded paved plan, both anchors,
  the withheld answer's record name differed from the one two nonexistent
  subjects' answers shared, while the vessels' content addresses matched.
- **The record.** Dimension 1 keeps the real read, the acquired subject
  included, and an owner at full disclosure reads its own record through the
  `D-IMPL-345` dereference. Each half was measured on its own; the end-to-end
  dereference of a withheld decision's record was not run.
- **Composite child legs.** Children are resolved for the asked subject before
  the plan; the composed factors replace the debt, the composed expiry and
  lineage stand in the product, and none of it is re-rendered. A required
  child asked about the composite's own subject from a source keyed on it made
  the products differ at `debt.debt` and `debt.factors.freshness`; a child
  asked about a fixed subject did not.
- **Similarity over an entity the acquisition refreshed.** On a fabric that
  already held the subject, an acquisition that changed its similarity
  attribute made the products differ at `computed_empty`, `debt.debt`,
  `debt.factors.freshness` and `debt.scorers`. With no similarity operator,
  with the attribute unchanged, or with the registry built from the view read
  before acquisition, they did not.
- **A fabric that outlives the question.** The withheld subject's acquisition
  stays in the fabric: after one question about a withheld subject the source
  holds, a later answer about an identifier that names nothing moved at
  `debt.debt` and `debt.factors.freshness`, and it did not when the source
  held nothing. The paved road boots a fabric for each question.
- **An acquisition not keyed on the subject** (a population read). The mirror
  image of the removed difference: `computed_empty` under `from_decision`, and
  `ttl-refusal` against `ttl-anchor-refusal` under `from_entity_freshness`.
  Before this change that shape was indistinguishable and the subject-keyed
  shape was not. Reasoned, not measured: no rendering built from the fabric
  before and after acquisition can be exact for both shapes, because what an
  identifier that names nothing would have acquired is the deployment's
  `acquire` to say.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: a subject Π withheld was rendered from the plan re-executed without the request seed over the fabric as it stood after the declared acquisition seam had ingested the asked subject's evidence. On a class-seeded plan its debt, empty finding and TTL anchor therefore reflected evidence that a never-acquired subject's fabric does not hold.
- After: when `acquisition` is declared, `__call__` reads the fabric (`reader.as_of` at `request.asked_at`) once, after every refusal that precedes the seam and immediately before the seam runs. A subject Π withholds is rendered from the plan re-executed without the request seed over that read. With no seam declared nothing is read in addition and the rendering is unchanged. Every refusal before the seam still reads nothing.
- Why: SEC-020, `D-IMPL-376` (3) route A. On the paved road acquisition populates each question's fabric before the plan runs, and this removes the difference that made in the served product. SEC-020 stays OPEN: see the channels above.
- Migration: none for a product whose Π never withholds. A deployment with an acquisition seam makes one more as-of read of the tenant's graph per governed call (the call already makes one). Before relying on Π's withheld signal, read the channels above that still tell a withheld subject from a nonexistent one.

## ccf.projection.engine.ProjectionEngine

- Surface: ccf.projection.engine.ProjectionEngine
- Public surface: true
- Change type: reshaped
- Before: `execute_without_request_seed(*, executed, plan, perspective, tenant_id, temporal_boundary)` always read the store at `executed.store_snapshot_pin` where it could pin, so it walked whatever the store held at that pin.
- After: adds the keyword `before_acquisition: GraphView | None = None`. When given, every query of the re-execution is answered over that one as-of read by the reference semantics, carrying and enforcing the classification authority the read carried. A query at another tenant or instant, and the two history reads, are refused rather than answered from a state the reader does not hold. `None` keeps the previous behavior.
- Why: SEC-020, `D-IMPL-376` (3) route A. The fabric before this request's acquisition is the state the walk of a subject that names nothing reads, when the acquisition is keyed on the subject and the fabric is booted for the question.
- Migration: none. The keyword is additive and defaults to the previous behavior.
