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
