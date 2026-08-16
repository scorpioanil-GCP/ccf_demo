# 17-13 — the reference debt scorer becomes the default

## What did **not** change, stated first

- **`GovernedResolver` still has thirteen constructor arguments and not one
  default.** Its docstring's claim — *"Every value this composition needs that
  the SDK cannot know arrives from outside it, and nothing has a default"* — is
  intact and still under test at
  `tests/products/test_resolver_seam.py::test_no_constructor_argument_carries_a_default`,
  which reads `default` and `default_factory` off every dataclass field. **The
  default lives in a helper precisely so that assertion did not have to be
  weakened**, and weakening a shipped assertion to admit a feature is this
  phase's signature defect.
- **`AssemblyDebtScorerProtocol` and `AssemblyDebtScorer` are byte-identical in
  shape.** No signature, return type or export moved. This plan *selects* the
  reference; it reshapes nothing about it.
- **`binding.yaml` gained and lost no key.** Its `debt:` block survives intact —
  see `## binding.yaml (debt:)` below for why the default could not shrink it.
- **No `ProjectionPlanFactory` reference implementation, and no pass-through
  plan.** Amendment A.2 of the 2026-08-16 spec ruled one impossible as scoped
  and the pass-through was withdrawn during that exchange. The deployment's one
  Python module is still the projection, and still the only one.
- **`REFERENCE_KEYS` still has exactly one element.** No second
  `module:attribute` reference was added and neither of `17-12`'s two refusals
  was weakened.

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: added
- Before: absent. `GovernedResolver` took `debt_scorer` as a required argument
  with no default, so **every** deployment supplied one — and since the SDK
  shipped no implementation until `17-11`, every deployment also *wrote* one.
  `17-12` moved the composition into
  `ccf.client.adapters.inprocess::_boot`, where it was one transport's private
  wiring rather than a seam a second transport could reach
- After: a keyword-only function taking the three fabric objects, the ten data
  values and the single permitted `plan:` factory, and returning a
  `GovernedResolver`. When no `debt_scorer` is passed it composes
  `ccf.products.debt_scorer.AssemblyDebtScorer` from the two Control Plane keys
  the caller named plus the two declared factors, each wrapped in
  `DeclaredFactor` so it lands in the Decision Replay record under its own
  `ScorerPin` (`D-IMPL-47`). Passing an explicit scorer overrides the reference
  entirely. Supplying **both**, or **neither**, is refused with a `TypeError`
  naming what is missing
- Why: §6 of
  `docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md`
  requires that *"a deployment that provides only data never has to know the
  Protocols exist"*, and CLAUDE.md §11 requires a reference implementation
  beside every Protocol. Shipping `AssemblyDebtScorer` without selecting it
  satisfied neither: a deployment still had to name it. **The helper rather
  than the class** because the default is not a value but a *construction*
  needing four further inputs — defaulting on the class would have grown it
  from thirteen arguments to seventeen, four of them dead whenever an explicit
  scorer is supplied, in order to give one argument a default
- Migration: none — new name, no prior shape. A deployment that constructs
  `GovernedResolver` directly keeps working unchanged and keeps supplying its
  own scorer. A deployment that wants the SDK's reference switches its
  construction call to this function and supplies `half_life_key`,
  `debt_profile_key`, `declared_completeness` and `declared_semantic_consistency`
  instead of a scorer

## ccf.products.resolver.DEBT_SCORER_INPUTS

- Surface: ccf.products.resolver.DEBT_SCORER_INPUTS
- Public surface: true
- Change type: added
- Before: absent
- After: `("half_life_key", "debt_profile_key", "declared_completeness",
  "declared_semantic_consistency")` — the four values
  `build_governed_resolver` needs to construct the reference scorer
- Why: exported for the reason `ccf.client.result.GUARDED_FIELDS` is exported —
  the helper's two refusal messages enumerate it, and the tests parameterize
  over it, so a fifth input added to the reference scorer gets its own control
  on the day it is declared rather than the day somebody remembers. A
  hand-written list beside each of three call sites is three lists that rot
  independently
- Migration: none

## src/ccf/client/adapters/inprocess.py

- Surface: src/ccf/client/adapters/inprocess.py
- Public surface: false
- Change type: behavior
- Before: `_boot` constructed `GovernedResolver` itself, composing
  `AssemblyDebtScorer` inline from two `_artifact` lookups and two
  `DeclaredFactor` wraps. `17-12`'s own docstring named this *"the composition
  `17-13` is expected to lift into `build_governed_resolver(...)`"*
- After: `_boot` calls `build_governed_resolver` with the document's data and
  selects only the artifact **store** itself — `FileArtifactStore`, because
  `artifact_store:` declares a path and a path is what a file-backed store
  takes. `ProductNotResolvable` raised while resolving the two debt keys is
  translated into a `BindingError` naming `binding.yaml`, because at boot every
  key the helper could miss was written there; the original is chained, so
  nothing about the manifest is lost
- Why: a second transport must not grow a second copy of a thirteen-argument
  composition, and the *"never has to know the Protocol exists"* property
  belongs to the seam rather than to one adapter. Classified
  `Public surface: false` because no exported Python name changed shape — the
  adapter's exports are `SCHEME`, `InProcessAdapter` and `reset_boot_cache`,
  all untouched
- Migration: none. The refusal an adopter sees for a mistyped `debt:` key is
  still a `BindingError` and therefore still a `TransportError`, so one
  `except` clause covers it exactly as before

## binding.yaml (debt:)

- Surface: binding.yaml
- Public surface: false
- Change type: behavior
- Before: `17-12` added the `debt:` block — `half_life_key`,
  `debt_profile_key`, `completeness`, `semantic_consistency` — and flagged it
  as possibly relocatable once `17-13` shipped a default
- After: **unchanged, all four fields, and deliberately so.** What changed is
  what the deployment must *know*: the block declares `D_c`'s **inputs**, and
  the SDK now selects the **machinery** that consumes them. A deployment names
  no scorer, imports nothing from `ccf.products.debt_scorer`, and writes no
  `GraphView` → `DebtFactors` adapter
- Why: none of the four is something a default may supply. The two keys name
  **Control Plane artifacts**, and §6 of the ruling forbids *"new discovery or
  registration machinery in this change"* — a fabric holding two λ_c tables has
  no SDK-knowable right answer, and picking the only one present is a rule that
  silently changes behaviour the day a second is registered. The two factors
  have **no SDK measurement at all**: `DebtFactors` records that position in its
  own docstring, and `17-11` rejected each candidate default in turn (`C = 1` is
  a number the SDK chose inside a delivered product's content address; `C = 0`
  fail-closes every deployment; deriving `C` from the table's breadth couples
  completeness to how many observation types a deployment happens to calibrate)
- Migration: none — no key was added, removed or renamed
