# 17-03 — the resolver seam that yields a gate-admitted product

## What did **not** change, stated first

A reader's first question about a change to the resolver story is whether the
seam they already implement moved. It did not.

- **Neither `runtime/` resolver seam was touched.** Both
  `ccf_runtime.mcp.egress.ProductResolverProtocol` and
  `ccf_runtime.mcp.experience.ExperienceProductResolverProtocol` keep the same
  five keyword-only arguments and the same return type. No entry is filed for
  either name below, and that absence is deliberate — a claim on a name that
  did not move fails the completeness gate in the other direction.
- **No shipped door changed.** Nothing under `runtime/` imports this module,
  and no door's serialization, entitlement check or URI template moved.
- **`run_gates`, `serve`, `refuse_request` and `build_replay_record` are
  unedited.** This plan composes them; it does not reshape any of them. The
  composition is new, the parts are not.
- **No new boundary was crossed.** No module under `src/` imports
  `ccf_runtime` before this change and none does after it — the property is
  now asserted by a standing test rather than left as a fact about the tree.

## ccf.products.resolver.ServedProductResolverProtocol

- Surface: ccf.products.resolver.ServedProductResolverProtocol
- Public surface: true
- Change type: added
- Before: absent — no `src/`-resident seam yielded a gate-admitted product.
  The nearest one, `ccf.agents.assembler.ContextAssemblerProtocol`, sits one
  level below the vessel: its outcome carries a payload and no contract, no
  gates and no replay record. The two seams that do yield a gated product both
  live in `runtime/`, so an in-process client had no implementable path
- After: a `@runtime_checkable` Protocol with one keyword-only `__call__`
  taking `tenant`, `product_class`, `version`, `perspective` and `request` —
  copied argument for argument from the egress seam — and returning
  `ResolverOutcome`
- Why: spec Amendment 1 §B (`D-29`) ruled the resolver Protocol is declared in
  `src/`, because the alternative shapes are both refused: importing the
  `runtime/` seam would be the first `src` → `runtime` edge in the tree, and
  having the client run the gates itself would put an SDK-owned verdict on the
  serve path that `D-IMPL-102` limb 3 declined
- Migration: none for existing door resolvers — the argument list is identical,
  so a deployment adapts one by widening its return type rather than reshaping
  its call

## ccf.products.resolver.ResolverOutcome

- Surface: ccf.products.resolver.ResolverOutcome
- Public surface: true
- Change type: added
- Before: absent — the shipped seams return a servable product and admit no
  refusal in their union, so a fabric refusal produced behind one had nowhere
  to go, and a replay reference could not reach a caller at all
- After: a named union alias, `ServedProduct | RefusalEnvelope`
- Why: the two widenings research measured to be missing. `ServedProduct`
  rather than `ServableProduct` carries `replay_ref`, which the ruled client
  result exposes and which no shipped door can reach today; the refusal half
  gives every fabric refusal a way across the seam, which is what
  `RefusalEnvelope` was defined in wave 1 to be. A named alias rather than an
  inline union because a `match` statement, a decoder and a docstring must all
  spell the same set
- Migration: none — nothing returned this type before

## ccf.products.resolver.ProductNotResolvable

- Surface: ccf.products.resolver.ProductNotResolvable
- Public surface: true
- Change type: added
- Before: absent from `src/`. The equivalent absence signal,
  `ccf_runtime.mcp.egress.ProductNotServable`, lives in `runtime/` and is
  unreachable from `src/`
- After: a `LookupError` subclass raised when a resolver holds no product at
  the address it was called with
- Why: a distinct type rather than an import, because importing the door's one
  would be exactly the `src` → `runtime` edge Amendment 1 §B ruled out. Raised
  rather than returned, on the split `ProductRequestViolation` already draws: a
  question the class does not answer is a bad question and comes back as a
  refusal value, while an address the resolver was never wired to serve is a
  broken deployment and comes back as an exception
- Migration: none — a deployment catching `ProductNotServable` at a door is
  unaffected; this type is raised only by an in-process resolver

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: added
- Before: absent. The SDK shipped every *part* of assemble → gate → record →
  serve and never the composition, so every deployment wrote it — which is why
  the rejected first example wrote it in front of a reader who wanted to ask
  one question
- After: a frozen, keyword-only dataclass conforming to
  `ServedProductResolverProtocol`, composing `refuse_request` → graph view at
  the boundary → `build_operator_registry` → `ProjectionEngine.execute` →
  `register_product_class` → `run_gates` → `build_replay_record` → `serve`
- Why: `D-29` ruled the reference implementation ships in `src/` beside the
  Protocol. The hard constraint attached to that ruling is that the
  composition is **pure mechanism**: thirteen constructor arguments, none with
  a default, four of them manifest keys read off the booted fabric's own
  artifacts — so every threshold, class name, policy key, TTL figure and
  artifact-class token stays a Control Plane artifact or a value the
  deployment authored
- Migration: none — a deployment keeps its own resolver if it has one. This is
  a reference implementation carrying no privileged status: the SDK invokes it
  never, and a deployment substituting its own loses no capability

## ccf.products.resolver.ProjectionPlanFactoryProtocol

- Surface: ccf.products.resolver.ProjectionPlanFactoryProtocol
- Public surface: true
- Change type: added
- Before: absent — a deployment composing assemble → gate → serve by hand
  constructed its plan inline, so there was no named seam for "how this
  deployment builds Π for one question"
- After: a `@runtime_checkable` Protocol with one keyword-only `__call__`
  taking `required` and `request` and returning a `ProjectionPlan`
- Why: a *factory* rather than a plan, because a plan that interprets a
  caller's parameters has to see them. Handing the resolver one long-lived
  plan would freeze the parameters at wiring time — the *configurable rather
  than callable* defect the request surface was built to correct — or force
  every plan to be mutable, which replay cannot tolerate
- Migration: none — new seam, no prior shape

## ccf.products.resolver.AssemblyDebtScorerProtocol

- Surface: ccf.products.resolver.AssemblyDebtScorerProtocol
- Public surface: true
- Change type: added
- Before: absent — debt was assessed by deployment code at whatever call site
  the deployment's own spine chose, with no named seam at the resolver
- After: a `@runtime_checkable` Protocol with one keyword-only `__call__`
  taking `view` and returning a `DebtAssessment`
- Why: the SDK ships the machinery for debt and never the values, and the
  choice this seam hides is larger than a threshold — measuring freshness over
  the rows a question *read* rather than over the rows that *survived being
  read* yields a different number, and which is right depends on what the
  product means. It takes the view rather than the payload because debt is
  measured against the assembly, not declared beside it
- Migration: none — new seam, no prior shape
