# 378-22 — a deployment-declared demonstration serve instant (`D-IMPL-378` C1)

`D-IMPL-378` CI ruling C1 (a), Dave: *"an SDK way for a deployment to declare a fixed
demonstration serve instant, honored by both transports, never usable in production
(security review required), so hw1's pinned question stops expiring without weakening an
assertion."* **SDK-defined** (CLAUDE.md §11). **A candidate:** how "never usable in
production" is enforced is a proposal Dave rules on; this fragment records option (b) — the
declaration is refused outside the SDK's development substrates, and every record made under
it pins it in Decision Replay dimension 2. The measurements are in
`tests/client/test_demonstration_serve_instant.py`.

What changes for a deployment that declares nothing: nothing. Its config derives the same
manifest, its resolver serves on the clock it was composed with, and its records are
byte-identical to the ones written before this change (the pin is appended only under a
declaration).

## ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstant

- Surface: ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstant
- Public surface: true
- Change type: added
- Before: absent — a deployment pinned to a past instant had no governed way to say which instant it serves at; `examples/s1-01-hello-context-product/spine.py` composed one in example code through `admission_clock`
- After: a typed Control Plane contract with one member, `serve_instant`, a zone-bearing instant (a zone-less one is refused, `D-IMPL-38`)
- Why: since `D-IMPL-358` a governed serve is judged at `served_at`; a demonstration whose question is pinned to a past date is refused as expired by today's clock, correctly, unless the deployment declares the instant it serves at
- Migration: none; a deployment that wants a demonstration instant declares it (see `DeploymentConfig`)

## ccf.controlplane.demonstration_serve_instant.DEMONSTRATION_SERVE_INSTANT

- Surface: ccf.controlplane.demonstration_serve_instant.DEMONSTRATION_SERVE_INSTANT
- Public surface: true
- Change type: added
- Before: absent
- After: the artifact class `ccf.demonstration-serve-instant`, typed-registerable (in `ccf.deployment.classes.SDK_ARTIFACT_CLASSES`), with no author lanes
- Why: a declaration must be a pinned Control Plane artifact so the record it governs can name its exact version, which replay's exact-version binding check can resolve
- Migration: none

## ccf.controlplane.artifacts.DEMONSTRATION_SERVE_INSTANT

- Surface: ccf.controlplane.artifacts.DEMONSTRATION_SERVE_INSTANT
- Public surface: true
- Change type: added
- Before: absent
- After: the same class constant re-exposed from the module that exposes the SDK's artifact-class catalog, on `TEMPORAL_BOUNDARY_POLICY`'s precedent
- Why: `tests/deployment/test_class_lookup.py` holds every typed-registerable class to the object this module exposes
- Migration: none

## ccf.controlplane.demonstration_serve_instant.demonstration_serve_instant_key

- Surface: ccf.controlplane.demonstration_serve_instant.demonstration_serve_instant_key
- Public surface: true
- Change type: added
- Before: absent
- After: `{tenant}/ccf.demonstration-serve-instant`, derived per tenant and never from a section name
- Why: two tenants cannot share one declaration, and the registry's tenant check reads the segment before the first `/` (`D-IMPL-353` §1.3)
- Migration: none

## ccf.controlplane.demonstration_serve_instant.PinnedDemonstrationServeInstant

- Surface: ccf.controlplane.demonstration_serve_instant.PinnedDemonstrationServeInstant
- Public surface: true
- Change type: added
- Before: absent
- After: a resolved declaration with its key and exact registered version; `binding` is the `PolicyBinding` every record made under it carries
- Why: the version a record pins is the one resolved, never one rebuilt later (`PinnedTemporalBoundary`'s rule)
- Migration: none

## ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstantMisdeclared

- Surface: ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstantMisdeclared
- Public surface: true
- Change type: added
- Before: absent
- After: raised when something other than a `DemonstrationServeInstant` is registered at the key
- Why: a wrong artifact is a configuration error, not an absent declaration; reading it as absent would serve on the real clock a deployment that believed it had declared one
- Migration: none

## ccf.controlplane.demonstration_serve_instant.resolve_demonstration_serve_instant

- Surface: ccf.controlplane.demonstration_serve_instant.resolve_demonstration_serve_instant
- Public surface: true
- Change type: added
- Before: absent
- After: resolves one tenant's declaration with its version, or `None` when the tenant declares none; reads no clock and enforces nothing
- Why: the Control Plane half of the mechanism, kept apart from the composition that honors it
- Migration: none

## ccf.products.demonstration_clock.compose_serve_clock

- Surface: ccf.products.demonstration_clock.compose_serve_clock
- Public surface: true
- Change type: added
- Before: absent
- After: the one composition step that turns a declaration into the resolver's serve clock, called once by `ccf.products.resolver.build_governed_resolver`. With no declaration it returns the clock the caller composed. With one, it refuses a caller-composed clock (`DemonstrationServeInstantConflict`), refuses a graph adapter whose registration does not declare `development_reference` or an artifact store that is not the SDK's `FileArtifactStore` (`DemonstrationServeInstantRefused`), and otherwise returns a `DeclaredServeClock`. A Control Plane offering the unaudited pinned-read surface is probed with `versions` first, so a deployment that declares nothing gains no audit event
- Why: C1's "never usable in production", option (b) candidate: a fixed serve clock keeps expired answers servable and judges policy effectivity and composite admission at a stale instant, so it is refused on any substrate a production deployment runs on
- Migration: none

## ccf.products.demonstration_clock.DeclaredServeClock

- Surface: ccf.products.demonstration_clock.DeclaredServeClock
- Public surface: true
- Change type: added
- Before: absent
- After: a callable returning the declared instant, carrying the declaration's exact pin as `binding`
- Why: audit by construction — whatever reads `served_at` from it can also say which declaration set it
- Migration: none

## ccf.products.demonstration_clock.DemonstrationServeInstantConflict

- Surface: ccf.products.demonstration_clock.DemonstrationServeInstantConflict
- Public surface: true
- Change type: added
- Before: absent
- After: raised when a composition supplies its own clock (`admission_clock`, or an adapter's `clock`) while the deployment declares an instant
- Why: one serve instant has one authority; a silent winner would be two authorities that can drift apart
- Migration: none

## ccf.products.demonstration_clock.DemonstrationServeInstantRefused

- Surface: ccf.products.demonstration_clock.DemonstrationServeInstantRefused
- Public surface: true
- Change type: added
- Before: absent
- After: the option (b) production guard, raised at composition with `reason` `graph-substrate-not-development` or `artifact-store-not-development` and the declaration's `key`
- Why: C1 requires the declaration be never usable in production
- Migration: none

## ccf.graph.registry.BackendRegistration

- Surface: ccf.graph.registry.BackendRegistration
- Public surface: true
- Change type: reshaped
- Before: five fields — `name`, `config_model`, `secret_fields`, `open_store`, `make_writer`
- After: a sixth, `development_reference: bool = False`. The SDK's SQLite and in-memory adapters set it; every other adapter, including any third-party adapter written before this field, defaults to `False`
- Why: the option (b) production guard needs to know whether the booted graph adapter is a development reference, and core may neither import nor name an adapter (`D-IMPL-93` properties (1) and (2), lints `cinv02-backend-import` and `cinv04-substrate-name`). The adapter states the fact about itself and `compose_serve_clock` asks it through `ccf.graph.registry.resolve`. Measured first the other way: a name list in core was refused by `cinv04-substrate-name`, and the existing `secret_fields` cannot stand in for the flag because the Postgres, MongoDB and Neo4j adapters also declare none
- Migration: none; a third-party adapter that is a development reference may set `development_reference=True`, and one that says nothing keeps every declared demonstration serve instant refused over it

## ccf.products.refusal.NON_VALUE_VIOLATIONS

- Surface: ccf.products.refusal.NON_VALUE_VIOLATIONS
- Public surface: true
- Change type: behavior
- Before: eight exception names the closed refusal vocabulary places outside the envelope
- After: nine; `DemonstrationServeInstantConflict` joins, with its reason stated beside the constant
- Why: the structural walk over the `…Conflict` name family found the new class (`tests/products/test_refusal_envelope.py::test_the_refusal_vocabulary_is_closed_by_set_equality`). It is a composition-time configuration contradiction, refused before any question exists, so it is an exception and never a governed shell (`D-IMPL-253` Q15)
- Migration: none

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: reshaped
- Before: no `demonstration_serve_instant` section; the key was refused as unrecognised
- After: an optional `demonstration_serve_instant:` section, hash-transparent at `None`, derived like `temporal_boundary:` — body verbatim, no `semver` injected, the bookkeeping keys refused by name, a top-level `tenant_id` required, key `{tenant}/ccf.demonstration-serve-instant`
- Why: the single-file authoring surface for the declaration, so a config-driven deployment can state it where its other declarations are
- Migration: none; absence means the real clock

## ccf.deployment.config.derive_deployment

- Surface: ccf.deployment.config.derive_deployment
- Public surface: true
- Change type: behavior
- Before: one bare typed section, `temporal_boundary:`
- After: also derives `demonstration_serve_instant:`, appended after the temporal boundary so a config without it derives byte-for-byte what it did; a zone-less instant is refused at derivation
- Why: as for `DeploymentConfig`
- Migration: none

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: behavior
- Before: the resolver served on `admission_clock` as passed
- After: same signature. When the tenant declares a demonstration serve instant, the resolver serves at it (`served_at`, Gate 3's comparand, the temporal window's evaluation instant, constraint effectivity and composite admission), resolved once at construction so a later registration does not reach a built resolver. Refused by name beside a supplied `admission_clock`, and outside the development substrates. The erasure consult keeps `admission_clock`, so no audit stamp carries a declared instant; Context Debt keeps the decision instant (`D-IMPL-358` ruling 6)
- Why: C1; one composition function every composition root already calls, so the in-process adapter and a door's product honor the declaration with no transport code
- Migration: none for a deployment that declares nothing. A deployment that declares an instant must not also pass `admission_clock`

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: no record named the instant's source
- After: same fields. A resolver whose serve clock is a `DeclaredServeClock` appends the declaration's exact `(key, version)` to dimension 2 of every record it writes, served and refused; on any other clock it appends nothing
- Why: audit by construction — an examiner can tell a demonstration record from a real one from the record alone, and the pin resolves at its recorded version through the Control Plane's exact-version read, the check replay makes for every binding (`tests/client/test_demonstration_serve_instant.py::test_the_records_pin_resolves_at_its_recorded_version`)
- Migration: none

## ccf.client.adapters.inprocess.InProcessAdapter

- Surface: ccf.client.adapters.inprocess.InProcessAdapter
- Public surface: true
- Change type: behavior
- Before: `as_of=None` resolved to the adapter's clock
- After: when the deployment declares a demonstration serve instant, `as_of=None` resolves to it (one composition, one now), and a `clock` passed to the adapter beside the declaration is refused at boot with `DemonstrationServeInstantConflict`
- Why: C1, "honored by both transports"
- Migration: none

## ccf.client.adapters.mcp_stdio.McpStdioAdapter

- Surface: ccf.client.adapters.mcp_stdio.McpStdioAdapter
- Public surface: true
- Change type: behavior
- Before: `as_of=None` resolved to the adapter's clock
- After: the client reads the declaration from the deployment's `ccf_config.yaml` (which it already reads for the tenant and lane) and resolves `as_of=None` to it; a `clock` passed beside it is refused with `DemonstrationServeInstantConflict` before anything is spawned. The server child serves at the same declaration through `build_governed_resolver`
- Why: without it, `as_of=None` would ask at today's date and be served at the declared instant, and the two transports would disagree (`D-IMPL-150`)
- Migration: none

## ccf.demonstration-serve-instant

- Surface: ccf.demonstration-serve-instant
- Public surface: false
- Change type: added
- Before: absent
- After: a new artifact document format, `serve_instant` only, with its committed JSON Schema at `docs/schemas/ccf.demonstration-serve-instant.json`; the `ccf.deployment-config` schema gains the optional section
- Why: as for `DemonstrationServeInstant`
- Migration: none
