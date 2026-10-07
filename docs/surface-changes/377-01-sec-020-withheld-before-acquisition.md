# 377-01 — SEC-020: a withheld subject is rendered over the fabric as it stood before its question's acquisition

`D-IMPL-376` ruling (3), route A: one bounded corrective round on the leak the
`D-IMPL-371` close review measured on the paved road, built red-first. The
governed call's declared acquisition seam ingests the ASKED subject's evidence
BEFORE the plan runs. A subject that names nothing has nothing acquired for it,
so its walk reads the fabric as it stood before acquisition. The withheld
subject's request-seed-free re-execution (`370-20`) read the fabric AFTER its
own acquisition, so the plan's class seeds reached the evidence acquisition had
just put there. Measured on the paved fixture's class-seeded plan: under
`from_decision` the two products differed at `computed_empty`; under
`from_entity_freshness` the withheld subject was refused `ttl-refusal` and the
never-acquired one `ttl-anchor-refusal`. The exploit test is
`tests/products/test_withheld_is_indistinguishable_from_absent.py::test_the_paved_road_acquisition_seam_does_not_reveal_a_withheld_subject`.

**The rule.** When an acquisition seam is declared, the governed call reads the
fabric once, as an as-of read at the question's boundary, immediately before
the seam runs. When Π raises the withheld signal, the plan is re-executed
without the request seed over THAT state, answered by the reference semantics
(`ccf.graph.fallback.answer`). Nothing this request's acquisition ingested is
walked, and no record is masked. Replay dimension 1 keeps the real read.

**Scope, measured.** The rendering equals what a subject that names nothing
gets when that subject's question acquires nothing, which is what a source read
keyed on the subject returns for an identifier it does not hold. An acquisition
that ingests the same content whatever the subject (a population read) gives a
nonexistent subject that content too, and the withheld rendering does not walk
it. For that shape the two products differ at the same members as above, with
the roles reversed. Before this change that shape was indistinguishable and the
subject-keyed shape was not. No rendering built from the fabric before and
after acquisition can be exact for both shapes, because what an identifier that
names nothing would have acquired is the deployment's `acquire` to say.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: a subject Π withheld was rendered from the plan re-executed without the request seed over the fabric as it stood after the declared acquisition seam had ingested the asked subject's evidence. On a class-seeded plan its debt, empty finding and TTL anchor therefore reflected evidence that a never-acquired subject's fabric does not hold.
- After: when `acquisition` is declared, `__call__` reads the fabric (`reader.as_of` at `request.asked_at`) once, after every refusal that precedes the seam and immediately before the seam runs. A subject Π withholds is rendered from the plan re-executed without the request seed over that read. With no seam declared nothing is read in addition and the rendering is unchanged. Every refusal before the seam still reads nothing.
- Why: SEC-020, `D-IMPL-376` (3) route A. A withheld subject must be indistinguishable from a nonexistent one on the paved road, where acquisition populates each question's fabric before the plan runs.
- Migration: none for a product whose Π never withholds. A deployment with an acquisition seam makes one more as-of read of the tenant's graph per governed call (the call already makes one). A product whose Π withholds subjects should acquire by subject: see the scope above.

## ccf.projection.engine.ProjectionEngine

- Surface: ccf.projection.engine.ProjectionEngine
- Public surface: true
- Change type: reshaped
- Before: `execute_without_request_seed(*, executed, plan, perspective, tenant_id, temporal_boundary)` always read the store at `executed.store_snapshot_pin` where it could pin, so it walked whatever the store held at that pin.
- After: adds the keyword `before_acquisition: GraphView | None = None`. When given, every query of the re-execution is answered over that one as-of read by the reference semantics, carrying and enforcing the classification authority the read carried. A query at another tenant or instant, and the two history reads, are refused rather than answered from a state the reader does not hold. `None` keeps the previous behavior.
- Why: SEC-020, `D-IMPL-376` (3) route A. The fabric before this request's acquisition is the state a subject that names nothing walks.
- Migration: none. The keyword is additive and defaults to the previous behavior.
