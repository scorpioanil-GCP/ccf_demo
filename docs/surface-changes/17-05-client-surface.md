# 17-05 — the client surface an adopter actually types

## What did **not** change, stated first

- **No shipped door changed, and no producer-side type moved.** This plan adds
  the consuming half only. Nothing under `ccf.products`, `ccf.replay`,
  `ccf.deployment` or `ccf_runtime` was touched.
- **`RefusalEnvelope` is unchanged, and is not copied.** `ccf.client.result.Refusal`
  *is* that class under the name the spec uses for it, not a client-side
  parallel shape. A copy would need a gate asserting the two agree, and the day
  it drifted a client's `refusal.kind` would name a vocabulary the fabric no
  longer speaks.
- **`decode_outcome`'s behaviour is unchanged.** Its three post-parse checks
  were lifted into `check_outcome`, which it now calls; every one of `17-04`'s
  34 codec tests passes untouched.
- **The package's public surface is exactly four names and no more.** Every
  other name below is a module-level export reached by importing that module
  directly — the adapter author's surface, not the client developer's.

## ccf.client.ProductClient

- Surface: ccf.client.ProductClient
- Public surface: true
- Change type: added
- Before: absent — `ccf.client.__all__` was empty, and there was no client role
  at all. A consumer reached a Context Product by importing the producer's own
  boot machinery, which is how the rejected Phase 16 example ended up holding a
  path to the producer's Control Plane config
- After: one of the four names `D-03` fixes the package surface at, re-exported
  from `ccf.client.client`
- Why: `D-01` puts the client abstraction and the result contract in the SDK, so
  transports become adapters *behind* a contract rather than each re-inventing
  one. Four names is the measurable form of `D-02`'s "the producer side stays
  invisible to the client", and `tests/client/test_surface.py` asserts the set
  by equality with controls that watch the assertion fail on a fifth name and on
  a missing one
- Migration: none — new surface. `from ccf.client import ProductClient` is the
  whole import a consumer needs

## ccf.client.Result

- Surface: ccf.client.Result
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported from `ccf.client.result`; the second of the four ruled names
- Why: `D-01` — a Context Product is valuable because of the contract it
  returns, so one result shape crosses every transport
- Migration: none — new surface

## ccf.client.TransportError

- Surface: ccf.client.TransportError
- Public surface: true
- Change type: added
- Before: declared in `ccf.client.errors` by `17-04` but not exported from the
  package, whose `__all__` was empty
- After: re-exported from the package; the third of the four ruled names
- Why: `D-10` reserves it for *the wire never spoke*, and a caller catching it
  should not have to know which submodule declared it
- Migration: none — `from ccf.client.errors import TransportError` still works

## ccf.client.BindingError

- Surface: ccf.client.BindingError
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported from the package; the fourth of the four ruled names
- Why: `D-05`/`D-10`. It subclasses `TransportError`, so `except TransportError`
  stays the one catch-all for every way the wire never spoke, while a caller who
  wants to distinguish a misconfiguration from an outage catches the narrower
  type first
- Migration: none — new surface

## ccf.client.result.Result

- Surface: ccf.client.result.Result
- Public surface: true
- Change type: added
- Before: absent — a served product crossed a door as bare canonical bytes and a
  refusal crossed no door at all, so there was no shape carrying "the answer or
  the governed no"
- After: a class carrying either half, with five pre-assembly properties
  (`refused`, `refusal`, `product_id`, `parameters`, `temporal_boundary`)
  readable on both, and six post-assembly properties that **raise** on a refused
  result. Exactly one of the two halves is enforced at construction
- Why: `D-07` makes a refusal a value rather than an exception — the gates ran
  and the governed answer was "no, and here is why", which is the fabric
  working. `D-09` keeps everything that existed *before* assembly readable, so
  the "no" stays auditable at the seam. Deliberately **not** a Pydantic
  contract, and that is a design consequence rather than an inconsistency: the
  guard requires attribute access to be a computation, while a declared field is
  a value that would be readable as `None` on a refused result before any code
  of this module ran — the exact defect `D-08` forbids. Validation is not
  deferred by that choice, because the boundary this type sits behind is
  `WireOutcome`, which is frozen and `extra=forbid`
- Migration: none — new type. Note for anyone extending it: a seventh public
  property must join `GUARDED_FIELDS` or `PRE_ASSEMBLY_FIELDS`, because
  `tests/client/test_result_guard.py` asserts the two partition the class's
  public properties exactly

## ccf.client.result.Refusal

- Surface: ccf.client.result.Refusal
- Public surface: true
- Change type: added
- Before: absent under this name. `ccf.products.refusal.RefusalEnvelope` shipped
  in `17-02` and is what a refusal has always been
- After: the client's name for that same class — an alias, not a copy and not a
  subclass
- Why: the spec's four names are `ProductClient`, `Result` (*with its*
  `Refusal`), `TransportError` and `BindingError` — so `Refusal` rides on
  `Result` rather than standing beside it, and is deliberately **not** a fifth
  package export. It is the same type because the envelope already *is* the
  client-facing reading: it promotes `reason`, `key` and `detail`, carries
  `kind` unflattened, and attaches the pre-assembly request identity and lineage
  `D-09` requires. A parallel shape with the same members would need a gate
  asserting a rename is still a rename
- Migration: none — `RefusalEnvelope` is unchanged and both names resolve to it

## ccf.client.result.GUARDED_FIELDS

- Surface: ccf.client.result.GUARDED_FIELDS
- Public surface: true
- Change type: added
- Before: absent — nothing named which members of a delivered product exist only
  after assembly
- After: the six names `D-08` guards: `payload`, `debt`, `content_address`,
  `replay_ref`, `lineage`, `expires_at`
- Why: exported rather than private because the guard's message enumerates it,
  the per-field tests parameterize over it, and `17-07`'s conformance suite
  reads it so the guard leg is written once for every adapter that ever ships.
  Three readers of one tuple cannot drift into disagreeing about what is
  guarded; three copies would
- Migration: none — new constant

## ccf.client.result.PRE_ASSEMBLY_FIELDS

- Surface: ccf.client.result.PRE_ASSEMBLY_FIELDS
- Public surface: true
- Change type: added
- Before: absent
- After: the five members readable on either half — `refused`, `refusal`,
  `product_id`, `parameters`, `temporal_boundary`
- Why: `D-09`'s assembly boundary is the rule that decides which fields survive
  a refusal, and a rule stated only in prose cannot be checked. Declaring both
  sides makes "every public property is on one side of the boundary" an
  assertion, so a seventh property cannot appear next year on neither
- Migration: none — new constant

## ccf.client.errors.BindingError

- Surface: ccf.client.errors.BindingError
- Public surface: true
- Change type: added
- Before: absent. `17-04` declared `TransportError` and recorded that the
  binding half would join it here
- After: a `TransportError` subclass raised when binding resolution produces
  nothing usable — no address at all, an address with no scheme prefix, or a
  scheme no adapter is registered for
- Why: `D-05`, `D-10`. A subclass rather than a sibling for the caller's sake:
  from where they stand, an address that would not resolve and a connection that
  would not open are the same event, so one `except` clause covers both
- Migration: none — new exception type

## ccf.client.errors.RefusedResultError

- Surface: ccf.client.errors.RefusedResultError
- Public surface: true
- Change type: added
- Before: absent — there was no result to read past, so there was nothing for
  caller negligence to mean
- After: a `RuntimeError` subclass raised when a post-assembly field is read off
  a refused `Result`
- Why: `D-08`'s inversion — the exception does not fire when the fabric says no,
  it fires when the caller ignores the fabric saying no. Deliberately **not** an
  `AttributeError`, and that is load-bearing rather than stylistic: the
  three-argument `getattr(result, "payload", None)` and `hasattr` both convert
  an `AttributeError` straight back into the silent `None` the guard exists to
  prevent. Deliberately **not** a `TransportError` either, because a retry loop
  wrapped around `except TransportError` would re-issue a question whose answer
  already arrived, forever. It is importable from this module but is not among
  the package's four names, because a caller reaching for it by name is writing
  `except` around a field read instead of branching on `result.refused`
- Migration: none — new exception type

## ccf.client.binding.BINDING_ENV_VAR

- Surface: ccf.client.binding.BINDING_ENV_VAR
- Public surface: true
- Change type: added
- Before: absent — no environment variable named where a client talks to
- After: the literal `"CCF_BINDING"`, as a named constant
- Why: `D-05` step 2. A constant rather than a repeated literal so the refusal
  message, the tests and any adapter's documentation all say the same string
- Migration: none — new constant

## ccf.client.binding.AdapterFactory

- Surface: ccf.client.binding.AdapterFactory
- Public surface: true
- Change type: added
- Before: absent
- After: `Callable[[str], TransportAdapter]` — the type of a registry value,
  receiving the address after the scheme prefix
- Why: `D-06`. Named so an adapter plan registering a scheme has a type to
  conform to rather than a shape to infer from an existing entry. The factory
  receives the remainder rather than the whole binding, so `inprocess:./deployment`
  hands `./deployment` and `http://host/path` hands `//host/path` — which is
  what a URL parser expects when it is handed a scheme separately
- Migration: none — new alias

## ccf.client.binding.SCHEME_REGISTRY

- Surface: ccf.client.binding.SCHEME_REGISTRY
- Public surface: true
- Change type: added
- Before: absent
- After: a plain `dict[str, AdapterFactory]`, **empty** on this plan
- Why: `D-06` — a plain dict inside `ccf.client`, mechanism rather than values:
  it holds no product identity, no threshold and no policy. Empty is the current
  truth rather than a placeholder, because the in-process adapter is a later
  plan in this phase and registers `inprocess` when it lands. That makes the
  empty case real today, which is why an unresolvable scheme refuses loudly
  rather than falling through to a default — a lookup that quietly does nothing
  when it can resolve nothing is a gate that goes silent exactly when a
  deployment is least configured. There is deliberately no entry-point lookup,
  no registration decorator and no metadata scan; each is a fourth resolution
  step wearing a different hat, and `tests/client/test_binding.py` asserts
  against the source that none is here
- Migration: none — new registry. An adapter registers its scheme at import
  time by assigning into this dict

## ccf.client.binding.resolve_binding

- Surface: ccf.client.binding.resolve_binding
- Public surface: true
- Change type: added
- Before: absent
- After: `resolve_binding(binding=None, *, environ=None) -> str` — the explicit
  kwarg, else `CCF_BINDING`, else `BindingError`
- Why: `D-05`. Three steps and no fourth: no bindings file, no per-product
  environment-variable naming, no discovery chain. The reason is measured rather
  than aesthetic — the example this phase exists to replace was 722 lines, and a
  resolution chain is how that happens. `environ` is a parameter so the second
  step is testable without mutating the process, and never a third source of
  truth
- Migration: none — new callable

## ccf.client.binding.split_binding

- Surface: ccf.client.binding.split_binding
- Public surface: true
- Change type: added
- Before: absent
- After: `split_binding(binding) -> tuple[str, str]`, splitting on the **first**
  colon only and refusing a missing scheme, an empty scheme or an empty address
- Why: `D-06` makes the scheme prefix the only place a transport is named, so
  the parse has one definition. Splitting on the first colon only is what keeps
  `http://host/path` intact and `mcp+stdio` one scheme name rather than two. A
  malformed binding is refused rather than half-resolved, because a client
  holding half an address fails later, further from what was actually wrong
- Migration: none — new callable

## ccf.client.binding.adapter_for_binding

- Surface: ccf.client.binding.adapter_for_binding
- Public surface: true
- Change type: added
- Before: absent
- After: `adapter_for_binding(binding=None, *, environ=None) -> TransportAdapter`
  — resolution and scheme dispatch in one call
- Why: one call so the client has one thing to do, and — the reason that
  mattered when writing the tests — so precedence between the kwarg and the
  environment is observable as *which adapter got built with which address*
  rather than as which string got stored. `17-RESEARCH.md` §7 names the
  distinction: a stored attribute proves storage, not dispatch
- Migration: none — new callable

## ccf.client.client.ProductClient

- Surface: ccf.client.client.ProductClient
- Public surface: true
- Change type: added
- Before: absent
- After: `for_product(product_id, binding=None)` and
  `ask(parameters, as_of=None) -> Result`, sync-only, holding the single
  `Result` decoder
- Why: `D-04` fixes the API at those two calls, and `D-24` fixes it at one
  synchronous `ask` — async would double the exported surface and the first
  audience for this package is a reader. `D-12` puts `Result` construction in
  exactly one place, here, which is what makes "every transport returns the same
  shape" a code path an adapter cannot avoid rather than a convention it is
  asked to follow; `tests/client/test_surface.py` asserts the one-site property
  with an AST scan over `src/`, `runtime/` and `examples/`, and its control
  passes the same scan a `tmp_path` root with two sites and watches it fail.
  `as_of=None` means *use the server's decision instant*, documented on `ask()`
  as `D-04` requires
- Migration: none — new class. `__init__` takes a `TransportAdapter` directly,
  for adapter authors and tests; `for_product` is the ordinary path

## ccf.client.codec.check_outcome

- Surface: ccf.client.codec.check_outcome
- Public surface: true
- Change type: added
- Before: absent — the three post-parse checks lived inside `decode_outcome`'s
  body, reachable only by handing it bytes
- After: `check_outcome(outcome, *, sent) -> ContextProductContract | None`,
  performing the echo cross-check, the address recomputation and the vessel
  parse, returning the parsed vessel or `None` on a refusal.
  `decode_outcome` now calls it and is otherwise unchanged
- Why: `D-11` types the adapter seam as returning a `WireOutcome` **object**
  rather than bytes, so an adapter that never went near this module can still
  hand the client a well-formed outcome that answers a different question or
  carries an address disagreeing with its own bytes. Extracting the checks lets
  `ProductClient` run *the same function* on everything it is handed, which
  turns `D-12`'s "a code path adapters cannot avoid" into a property of the
  checks as well as of `Result` construction. The alternative — the client
  re-encoding and re-decoding every outcome to force it through
  `decode_outcome` — buys the same guarantee at three times the serialization
  cost. The vessel is returned rather than discarded so the caller that needs it
  does not parse the same text twice
- Migration: none — new callable, and `decode_outcome`'s contract is unchanged.
  An adapter author who already holds a `WireOutcome` and wants the checks calls
  this instead of round-tripping through bytes
