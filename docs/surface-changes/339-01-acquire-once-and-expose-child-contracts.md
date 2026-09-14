# D-IMPL-339 — acquire once, and expose the admitted child contracts to the parent's computation

Applied 2026-09-14 under `D-IMPL-339`, the ruling recorded at `57d045c9`.
Its own SDK phase, baselined on `main`, independent of `D-IMPL-338` and of the
CP-14 example.

## The gap

A composite's children contributed governance only — per-factor debt, the
lineage union, the expiry floor, Gate 2's widened operand, one replay row each
— and could not contribute **content**: the parent's plan was built and
executed before any child was dispatched, and the `AdmittedChild` values were
dropped the moment `compose_children` returned. No existing interface carried
them to the parent's computation.

## What changes — the approved split

```
existing child-independent request / policy / declaration checks
    -> acquire and admit children ONCE
    -> the read-only child-contract view
    -> construct and execute the parent's plan
    -> assess the parent's own evidence
    -> compose using the SAME acquired outcomes
    -> existing gates, tolerance, delivery / refusal, replay
```

Only the **acquisition** half of the composite block moves above the plan.
`compose_children` runs where it always did, after the assessment it needs,
over exactly the `outcomes` the one acquisition produced. The
declaration-versus-plan binder stays between plan construction and execution.

## Surface entries

## ccf.products.composite.resolve_child_outcomes

- Surface: ccf.products.composite.resolve_child_outcomes
- Public surface: true
- Change type: added
- Before: the per-requirement walk — provenance, slot/instant/invocation re-binding, the refusal branches and the honest absence — lived only inside `compose_children`
- After: factored out, returning a `ChildOutcomeResolution`; `compose_children` calls it and applies the four laws to what it returns, unchanged in behavior
- Why: the walk must run BEFORE the parent's plan so the view is derived only from children that passed it, and so a known blocking outcome refuses before any child-dependent computation
- Migration: none — `compose_children`'s signature and behavior are unchanged

## ccf.products.composite.ChildOutcomeResolution

- Surface: ccf.products.composite.ChildOutcomeResolution
- Public surface: true
- Change type: added
- Before: absent
- After: the walk's result — rows, admitted children, admitted factors, and the first refusal; `blocking` is `refusal is not None`
- Why: one value that both the view and the composition are derived from
- Migration: none

## ccf.products.composite.ChildContractView

- Surface: ccf.products.composite.ChildContractView
- Public surface: true
- Change type: added
- Before: absent
- After: a read-only `Mapping[str, ContextProductContract]` keyed by the declared requirement's `product_class` — contracts, not admission machinery
- Why: what the plan receives; no invented graph view, no `ProductSource` expansion, no `GraphReader`
- Migration: none

## ccf.products.composite.child_contract_view

- Surface: ccf.products.composite.child_contract_view
- Public surface: true
- Change type: added
- Before: absent
- After: derives a `ChildContractView` from a resolution that reached no refusal; raises `ValueError` over a blocked one
- Why: the view is derived only after provenance and request/slot bindings are established, and never over a composition already known not to compose
- Migration: none

## ccf.products.composite.ADMITTED_CHILD_CONTRACT_CLASS

- Surface: ccf.products.composite.ADMITTED_CHILD_CONTRACT_CLASS
- Public surface: true
- Change type: added
- Before: absent — nothing retained a served product's bytes
- After: the artifact class under which the consuming fabric files each admitted child's contract by content address at decision time
- Why: replay rebuilds the parent's view from what was CONSUMED, never from a provider call, a latest-version lookup or a live closure; the row's `child_content_address` now resolves to bytes
- Migration: none — a mechanism token, not a domain value; filed idempotently on the fabric's own store

## ccf.products.resolver.CompositePlanFactoryProtocol

- Surface: ccf.products.resolver.CompositePlanFactoryProtocol
- Public surface: true
- Change type: added
- Before: `ProjectionPlanFactoryProtocol.__call__(required=, request=)` was the only way a plan was built
- After: an optional companion Protocol, `build_with_children(required=, request=, children=)`; a composite-capable factory declares support by implementing it, and the resolver chooses the call **structurally**
- Why: adding a defaulted parameter to a Protocol does not make existing implementations accept it; no `TypeError`-and-retry
- Migration: none — a factory implementing only `__call__` is called exactly as before, for composites and non-composites alike

## ccf.products.resolver.ChildAwareDebtScorerProtocol

- Surface: ccf.products.resolver.ChildAwareDebtScorerProtocol
- Public surface: true
- Change type: added
- Before: a deployment scorer received the view and the execution evidence; the parent's own child-dependent `C`/`S` had no per-request input path
- After: an optional companion Protocol, `score_with_children(view=, evidence=, children=)`; the resolver asks it when the scorer implements it
- Why: the parent's child-dependent measurements must reach its assessment per request from the same admitted products the plan read
- Migration: none — a scorer implementing only `__call__` is asked exactly as before

## ccf.products.resolver.GovernedResolver.__call__

- Surface: ccf.products.resolver.GovernedResolver.__call__
- Public surface: true
- Change type: behavior
- Before: children acquired and composed AFTER the projection; a known blocking child outcome still ran the plan; a composition refusal carried the execution that ran
- After: children acquired once BEFORE the plan; a known blocking outcome (required child absent, invoked child refused or rejected at admission, no resolver wired) refuses before any child-dependent computation, recorded like a pre-assembly refusal with `execution=None` and every child row; admitted contracts are retained by address
- Why: `D-IMPL-339` Q2 — do not run child-dependent computation on a set already known not to compose; a payload computed before a later refusal is provisional and is never served
- Migration: none for non-composites (byte-identical path); none for composites with a legacy factory (served as before, governance only)

## ccf.replay.engine.CompositeReplayEnvironment

- Surface: ccf.replay.engine.CompositeReplayEnvironment
- Public surface: true
- Change type: added
- Before: `ReplayEnvironment.resolve_plan(plan_id=)` was the only plan seam, so a child-dependent plan could not be rebuilt on replay
- After: an optional companion Protocol, `resolve_composite_plan(plan_id=, children=)`; `replay()` rebuilds the view from the retained contracts BEFORE calling it, and refuses by name an environment that lacks it for a record that composed admitted children
- Why: the child-input reconstruction must be connected and proven, with no provider calls
- Migration: none for records that composed no admitted child; a composite's environment implements the method
