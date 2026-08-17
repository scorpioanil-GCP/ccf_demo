# 17-06 — the in-process leg: a binding document, and the degenerate wire

## What did **not** change, stated first

- **`ccf.client`'s package surface is still exactly four names.** `D-03` fixes
  it at `ProductClient`, `Result`, `TransportError` and `BindingError`, and
  **nothing below is re-exported from the package** —
  `tests/client/test_surface.py` still asserts that set by equality. Every name
  below is public Python API all the same, and is logged here as such: it is a
  module-level export an *adapter author* reaches by importing the module
  directly. The two facts are not in tension and the distinction is worth
  keeping straight — "public" for this log means *the surface manifest tracks
  it*, which is a wider set than *a client developer types it*.
- **No producer-side type moved, and no shipped door changed.**
  `ccf.products.resolver`, `ccf.replay.serve`, `ccf.deployment` and every module
  under `ccf_runtime` are untouched. This plan *consumes* the resolver seam
  `17-03` declared; it does not widen it.
- **`SCHEME_REGISTRY` is unchanged as a type and as a mechanism.** `17-05`
  shipped it deliberately empty, and this plan populates the `inprocess` key at
  import of the adapter module — which is exactly the "a scheme reaches the
  registry by its adapter module being imported" rule `D-05` already states. No
  plugin lookup and no discovery chain was added.
- **`ccf.client.adapters` itself exports nothing.** Its `__all__` is empty and
  stays empty: importing a name from the package would be a fifth binding
  resolution step in a design that has exactly three.

## A surface that is **PROPOSED, not ruled**

Everything under `ccf.client.adapters.binding_document` interprets the
`binding.yaml` document `D-IMPL-141` proposes. **That decision is recorded as
`PROPOSED — awaiting Dave's ruling at the Phase 17 gate`**, and this fragment
does not assert otherwise. The surface is confined to one module precisely so a
different ruling rewrites that file and the adapter's call site rather than the
adapter.

## ccf.client.adapters.binding_document.BINDING_DOCUMENT_NAME

- Surface: ccf.client.adapters.binding_document.BINDING_DOCUMENT_NAME
- Public surface: true
- Change type: added
- Before: absent — a deployment root had no way to tell a client anything, and
  an in-process binding address named a directory nothing could interpret
- After: the constant `"binding.yaml"`, referenced by every refusal the loader
  raises so a rename is one edit rather than a search
- Why: `D-IMPL-141` (PROPOSED). `ccf_config.yaml` is a closed-world contract —
  `ccf/deployment/config.py::_RESERVED_SECTIONS` fixes seven sections plus
  `operators`, and the module already refuses a `signal_batch` section by
  explicit decision — so a deployment that must contribute Python needs some
  other document to say where it is
- Migration: none — new surface, and inert unless a deployment authors the file

## ccf.client.adapters.binding_document.REQUIRED_KEYS

- Surface: ccf.client.adapters.binding_document.REQUIRED_KEYS
- Public surface: true
- Change type: added
- Before: absent
- After: `("config", "resolver", "question")` — the keys a binding document must
  state
- Why: exported so the tests parameterize over the real tuple rather than a
  copy of it. A fourth required key therefore cannot arrive without a test for
  its absence, which is the drift a hand-maintained duplicate would allow
- Migration: none — new surface

## ccf.client.adapters.binding_document.OPTIONAL_KEYS

- Surface: ccf.client.adapters.binding_document.OPTIONAL_KEYS
- Public surface: true
- Change type: added
- Before: absent
- After: `("connection",)` — a deployment whose backend needs no connection
  settings omits it, and omission is a positive statement rather than a missing
  value
- Why: the unknown-key refusal enumerates both tuples by name, so a reader told
  their key is not a key is also told what the keys are
- Migration: none — new surface

## ccf.client.adapters.binding_document.BindingDocument

- Surface: ccf.client.adapters.binding_document.BindingDocument
- Public surface: true
- Change type: added
- Before: absent
- After: a frozen dataclass carrying one deployment root's wiring, with **every
  path already resolved and already contained** — so a consumer never re-checks
  and never holds a second, weaker copy of the containment rule
- Why: `root` is the value the in-process boot cache keys on. Resolving it here
  rather than in the adapter is what makes `./deployment` and its absolute
  spelling one cache entry, which is `D-30`'s actual failure mode: a second
  `load_config_and_boot` against one graph raises `SingleWriterViolation`
- Migration: none — new surface

## ccf.client.adapters.binding_document.ResolverCall

- Surface: ccf.client.adapters.binding_document.ResolverCall
- Public surface: true
- Change type: added
- Before: absent
- After: the two things a deployment supplies that the SDK cannot invent — a
  typed `ProductRequest` and the `Perspective` it is answered under
- Why: `ServedProductResolverProtocol` takes five arguments and a `WireRequest`
  carries three fields. Three of the five the SDK holds already — `tenant` off
  the booted fabric, `product_class` and `version` off the request's own
  `schema_name`/`schema_version`, so a deployment is never asked to state its
  class address twice. The remaining two it cannot invent: `subject`, `intent`
  and `freshness` are domain vocabulary, `asked_at` is the producer's answer to
  `D-04`'s "`as_of=None` means the server's decision instant", and the client
  surface exposes no principal in v0 (`D-IMPL-129`). The SDK inventing either
  would be a half-life table in library code under another name
- Migration: none — new surface

## ccf.client.adapters.binding_document.QuestionFactoryProtocol

- Surface: ccf.client.adapters.binding_document.QuestionFactoryProtocol
- Public surface: true
- Change type: added
- Before: absent
- After: a `@runtime_checkable` Protocol for the factory a deployment names
  under `question:` — the shape
  `examples/s1-00-companies-over-revenue/deployment.py::request` already has,
  widened by the perspective
- Why: a Protocol rather than a base class (CLAUDE.md §11) — a deployment
  conforms by being callable this way. The decorator verifies only the presence
  of `__call__`, which every function has, so the loader checks the factory's
  **return value** against `ResolverCall` as well; that check is real, and the
  Protocol alone would be a tautology
- Migration: none — new surface

## ccf.client.adapters.binding_document.load_binding_document

- Surface: ccf.client.adapters.binding_document.load_binding_document
- Public surface: true
- Change type: added
- Before: absent
- After: reads and validates the document at a deployment root, refusing an
  unknown top-level key **by name** in the `DeploymentConfig` posture
- Why: deployment wiring that silently selected a default would be a deployment
  running configuration nobody authored, and it would surface as a wrong answer
  rather than as a failed boot. Containment is enforced rather than trusted: a
  path is refused both as written (absolute, or carrying `..`) and as resolved
  (a plain name that is a symlink out), which is the two-check rule
  `ManifestEntry` already holds a manifest to. `T-17-19` accepts that loading a
  reference runs the deployment's Python — the root is its own trust boundary —
  but not that a document reaches outside the deployment it describes
- Migration: none — new surface

## ccf.client.adapters.binding_document.load_reference

- Surface: ccf.client.adapters.binding_document.load_reference
- Public surface: true
- Change type: added
- Before: absent
- After: resolves a `<module-path>:<attribute>` reference against a deployment
  root, loading the module under a name derived from the **resolved root**
- Why: a bare module name would be a real collision rather than a theoretical
  one — the conformance suite boots more than one deployment in a process and
  `sys.modules` is process-wide, so a second root carrying its own `resolver.py`
  would silently get the first root's code. The root goes on `sys.path` only for
  the duration of the load, so a deployment module can import its own siblings
- Migration: none — new surface

## ccf.client.adapters.binding_document.conforming_resolver

- Surface: ccf.client.adapters.binding_document.conforming_resolver
- Public surface: true
- Change type: added
- Before: absent
- After: refuses a resolver factory whose product does not satisfy
  `ServedProductResolverProtocol`
- Why: the Protocol is `@runtime_checkable`, which is the whole reason it
  carries the decorator — this is a real structural check at the boundary a
  surface is handed a resolver, rather than a shape mismatch discovered inside
  a call that has already been accepted
- Migration: none — new surface

## ccf.client.adapters.inprocess.SCHEME

- Surface: ccf.client.adapters.inprocess.SCHEME
- Public surface: true
- Change type: added
- Before: absent — `SCHEME_REGISTRY` shipped empty in `17-05`, deliberately, so
  every lookup refused and a client with no transport installed said so loudly
- After: the constant `"inprocess"`, and the key this module registers itself
  under at import
- Why: written once so the registry entry, the refusal messages and the tests
  all say the same string. `D-05` — a scheme reaches the registry by its
  adapter module being imported, and there is still no plugin lookup and no
  discovery chain behind it
- Migration: none — new surface. `CCF_BINDING="inprocess:<root>"` is the whole
  configuration change a deployment makes

## ccf.client.adapters.inprocess.InProcessAdapter

- Surface: ccf.client.adapters.inprocess.InProcessAdapter
- Public surface: true
- Change type: added
- Before: absent — no `TransportAdapter` existed, so `ProductClient` had a seam
  and nothing to put behind it
- After: the first transport. Boots the deployment its address names **lazily**
  on the first `ask()`, caches the booted fabric on the **resolved absolute**
  root, calls the deployment's resolver, and encodes the answer through the
  canonical serializer
- Why: three rulings at once. `D-16` — the boot is invisible, so a developer
  types one command and nothing about a manifest or an artifact key reaches
  them. `D-13` — the adapter holds a live product and serializes it **anyway**,
  with no fast path, which makes in-process a true degenerate wire, gives a
  parity bug exactly one place to live, and *physically* prevents a live
  producer-side object from crossing the seam. `D-30` — the cache is not an
  optimization: a second `load_config_and_boot` against one graph raises
  `SingleWriterViolation`, measured, so caching is what makes a second `ask()`
  and a second client legal at all, and keying on the resolved root is what
  keeps `./deployment` and its absolute spelling one entry
- Migration: none — new surface. Nothing in `ccf.client`'s four-name package
  surface changed, and a client developer never names this class

## ccf.client.adapters.inprocess.reset_boot_cache

- Surface: ccf.client.adapters.inprocess.reset_boot_cache
- Public surface: true
- Change type: added
- Before: absent
- After: closes every cached fabric and empties the cache. **For tests only**,
  and deliberately not re-exported from `ccf.client`
- Why: `D-03` fixes that package's surface at four names, and a fifth for a test
  affordance would put a lifecycle control in a client developer's namespace to
  buy a test something the test can reach directly. It **closes** rather than
  clearing, and that is the whole reason it is a function: a cleared cache whose
  handles were never closed leaves the writers live, so the next boot against
  the same graph raises `SingleWriterViolation` — a helper that made the next
  test fail for a reason belonging to the previous one
- Migration: none — new surface, and no `close()` was added to `ProductClient`
  (`D-30`): two clients on one binding **share** the cached fabric, so a
  per-client close would retire a handle the other is still using
