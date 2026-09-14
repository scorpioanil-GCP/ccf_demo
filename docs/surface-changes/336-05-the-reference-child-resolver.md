# D-IMPL-336 Amendment 5 — the SDK ships a reference child resolver

Applied 2026-09-13 under `D-IMPL-336` Amendment 5 §1: *"Ship
`GrantBoundChildResolver` in `src/`. Deployment code binds the resolver; it
does not construct a chain of provenance objects."*

**This fragment was missing and the D-15 drift gate caught it** — reported by
the close panel's independent deep read, which observed that
`tests/test_surface_drift.py` was RED on this branch and GREEN on `main`, and
that the only unclaimed names were the branch's own headline deliverable. The
earlier fragments (`336-01`…`336-04`) name `ccf.products.composite` and
`ccf.peering.eligibility`; nothing named the new module.

## Why a reference implementation, when the Protocol said there would be none

`ccf.products.composite.CompositeChildResolverProtocol` used to state that the
SDK ships the Protocol *"and never an implementation, because resolving a
requirement to a granted skill, dispatching it and delivering the child is
agent orchestration — the harness's"*. That reading of CLAUDE.md §7.3/§8.1 is
superseded.

Dave's Amendment 5: resolving a requirement to a granted skill and dispatching
it **once** is not an agent loop, and *"the skill that the composite agent has
knows how to acquire the atomic context product and roll it in."* CLAUDE.md §11
governs instead — *"Reference implementations ship alongside Protocols."* What
stays out of `src/` is the scheduler, the swarm loop, and any new identity axis.

The measured reason it matters: acquiring one child went from **45 lines of
deployment code and five hand-constructed evidence objects to 16 lines and
none**.

## Surface entries

## ccf.products.child_resolver.GrantBoundChildResolver

- Surface: ccf.products.child_resolver.GrantBoundChildResolver
- Public surface: true
- Change type: added
- Before: absent — a deployment implemented `CompositeChildResolverProtocol` itself and hand-built the evidence chain
- After: the reference implementation, binding effective grant → actual dispatch → the child's governed delivery → fit checks → compose (D-IMPL-336 Amendment 5 §1)
- Why: the Protocol's own docstring told adopters to mint provenance objects that no longer exist, and every deployment would have written the same 45 lines
- Migration: construct one and pass it as `GovernedResolver(composite_children=...)`; a deployment substituting its own conforming resolver loses no capability

## ccf.products.child_resolver.ChildArguments

- Surface: ccf.products.child_resolver.ChildArguments
- Public surface: true
- Change type: added
- Before: absent
- After: the callable type turning one declared `ChildRequirement` into the typed arguments its producing skill takes (D-IMPL-336 Amendment 5)
- Why: what a child needs to be asked is deployment configuration, and the SDK holds no domain value (D-IMPL-38)
- Migration: none required — supply a callable when constructing `GrantBoundChildResolver`

## ccf.products.composite.CompositeChildResolverProtocol

- Surface: ccf.products.composite.CompositeChildResolverProtocol
- Public surface: true
- Change type: reshaped
- Before: `__call__(requirements, asked_at, admitted_at, composition_invocation)`
- After: also takes `consumer_lineage`, the composing product's own L axis (D-IMPL-336 Amendment 5)
- Why: `PeeringAdmissionGate.admit` extends lineage by set-union at the boundary and requires it, so a resolver acquiring a peered child could not verify one without it — and inventing a lineage on the consumer's behalf would make the union a fiction
- Migration: conforming resolvers accept the new keyword; `GovernedResolver` passes the composite's own pre-assembly lineage

## ccf.products.child_resolver.ChildRecordMismatch

- Surface: ccf.products.child_resolver.ChildRecordMismatch
- Public surface: true
- Change type: added
- Before: absent — `_touched_entities` read whatever record the producing skill named, never checking it described the product being admitted
- After: raised when the named record's `product_content_address` is not the address of the child in hand (D-IMPL-336 Amendment 5 §3, final review)
- Why: `F3` closed the ABSENT-evidence case on this leg; this is the MISATTRIBUTED-evidence case, which reads as present and passes the register check on the wrong product's reads
- Migration: none required — a producer naming its own record is unaffected; raised rather than refused, because evidence about another product is not a fact about this child's eligibility
