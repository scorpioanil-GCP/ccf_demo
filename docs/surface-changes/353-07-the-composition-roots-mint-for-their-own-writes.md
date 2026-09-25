# 353-07 — the composition roots mint for their own writes; the callers of the handles take the capability

`D-IMPL-353` §1.2, §1.3, §1.6 and `D-IMPL-354` (PROPOSED), Lane J-SRC of the join.
Lane HANDLES made every registry write, artifact write and ledger write require
an `Authorized[<kind>]`; this fragment is what the **callers** of those handles
in `src/` became. Two shapes, and nothing else:

- **A composition root mints, through the recipe, for exactly what it writes.**
  `ccf.boot`, `ccf.deployment.manifest`, `ccf.products.resolver`,
  `ccf.products.product` and `ccf.client.adapters.inprocess` are the `src/`
  roots the §4 lint names (`COMPOSITION_MINT_SITES`). Each appends ONE
  `composition` event to the Control Plane's own audit log and mints with that
  event's content address as the capability's `decision_id`:

  ```python
  event = registry.audit_log.append(
      action="composition", key=<resource>, version=<Kind.action_id>,
      resolved=True, occurred_at=<the composition's clock>, actor=COMPOSITION_PRINCIPAL,
  )
  capability = mint_at_composition(<Kind>, tenant=<tenant>, principal=COMPOSITION_PRINCIPAL,
                                   resource=<resource>, decision_id=content_hash(event))
  ```

  `ReplayMint` on one evidence class for one tenant; `Register` on one Control
  Plane key, whose tenant is the key's own tenant segment, derived exactly as
  the registry's `CrossTenantKeyRefused` check derives it. No root mints a door
  kind (`mint_at_composition`'s overloads and runtime check refuse it).
- **A module that is not a root receives its capability at construction** —
  typed, required, no default — verifies it there, and holds it:
  `ControlPlaneInvalidationSink`, `PeeringAdmissionGate`,
  `QuestionBoundChildResolver`, `ReplayRefusalRecorder`. Nothing takes a
  tenant, a class or an actor from its caller any more; each is the
  capability's (§1.2, §1.3).

## What is recorded here that the design did not say (and is reported to the join)

- **`boot()` takes the tenants it composes for.** `ccf.boot.boot` had no tenant;
  the invalidation register it must mint `Register` for is per tenant, so the
  root has to be told. `tenant_ids: Sequence[str]`, required, non-empty. A
  manifest-driven boot passes its one resolved tenant.
- **Four SDK key builders were class-first; the registry's check reads the
  tenant as the FIRST segment.** `register_key`, `payload_ceiling_key`,
  `trust_policy_key` and `product_entitlement_key` rendered
  `{class}/{tenant}`; under §1.3 such a key could be registered only by a
  capability whose tenant was the class name. All four are now
  `{tenant}/{class}`. The strings changed; every reader that derives them
  through the builders is unaffected; a literal spelled elsewhere is not.
- **The paved road's derived manifest keys are BARE** (`product_class`,
  `agent`, `policy` — `ccf.deployment.config` derives a section's key from its
  label), and s1-01's manifest keys are bare too. A bare key has no tenant
  segment, so under §1.3 as landed **no capability can register it**; the
  manifest root refuses it before minting (`CrossTenantKeyRefused`). This
  fragment does NOT resolve that — it is a design gap between `D-IMPL-343`'s
  key derivation and §1.3's grammar, reported for ruling — and every
  config-derived deployment is red until it is ruled.
- **`open_product` no longer grants.** Its derived consumer chain requested one
  `skill.grant` per declared skill on the deployment's behalf. A grant requires
  `Authorized[SkillGrant]`, a door kind no composition root may mint; the road
  now reads which declared skills are bound and refuses, by name, when one is
  not (`GrantNotInForce`). Whether a declared grant is a third composition-time
  write is `D-IMPL-354`'s to rule.

## ccf.boot.boot

- Surface: ccf.boot.boot
- Public surface: true
- Change type: reshaped
- Before: `boot(*, backend, connection=None, secrets=None, registry, resolution_spec_key, resolution_spec_version, policy_bundle_key, policy_bundle_version)`
- After: `boot(*, backend, connection=None, secrets=None, registry, resolution_spec_key, resolution_spec_version, policy_bundle_key, policy_bundle_version, tenant_ids: Sequence[str])` — required, non-empty, distinct; for each tenant the root mints `Register` for `register_key(tenant)` through the recipe (one `composition` event per tenant on `registry.audit_log`) and hands the capabilities to the writer's `ControlPlaneInvalidationSink`
- Why: D-IMPL-354 — the sink is not a composition root and may hold only what its composer minted; the composer can mint only for tenants it knows
- Migration: pass the tenants the fabric ingests and supersedes under; `load_and_boot` passes its resolved tenant. A supersession under a tenant not named is refused by the sink (`InvalidationUnauthorized`), never filed under a fallback

## ccf.controlplane.invalidation.ControlPlaneInvalidationSink

- Surface: ccf.controlplane.invalidation.ControlPlaneInvalidationSink
- Public surface: true
- Change type: reshaped
- Before: `ControlPlaneInvalidationSink(*, registry)`; `record(...)` registered `register_key(tenant_id)` with no capability
- After: `ControlPlaneInvalidationSink(*, registry, authorities: tuple[Authorized[Register], ...])` — each verified at construction against exactly `register_key(authorized.tenant)`, one per tenant, at least one; `tenants` property; `record(...)` looks the capability up FIRST and raises `InvalidationUnauthorized` for a tenant it holds none for, then `register_typed(authorized, ...)`
- Why: D-IMPL-353 §1.2 (the handle requires the capability) and D-IMPL-354 (the sink mints nothing)
- Migration: construct through `boot()`; a test composing a sink by hand mints `Register` for `register_key(tenant)` through the recipe

## ccf.controlplane.invalidation.InvalidationUnauthorized

- Surface: ccf.controlplane.invalidation.InvalidationUnauthorized
- Public surface: true
- Change type: added
- Before: absent
- After: `PermissionError` raised by the sink at construction (duplicate or no capability) and at `record` (a tenant the fabric was not composed for)
- Why: a supersession the fabric has no authority to record is refused, typed, never skipped
- Migration: none

## ccf.controlplane.invalidation.register_key

- Surface: ccf.controlplane.invalidation.register_key
- Public surface: true
- Change type: behavior
- Before: returned `ccf.entity-invalidation/{tenant_id}` (class-first)
- After: returns `{tenant_id}/ccf.entity-invalidation` (tenant-first); `KEY_PREFIX` keeps its name and value
- Why: §1.3 — the registry reads the key's tenant as the text before the first `/`; a class-first key could be registered only by a capability whose tenant was the class name
- Migration: derive the key through the builder; nothing persisted carries the old string (the register is a Control Plane artifact re-registered per boot)

## ccf.controlplane.registry.ControlPlaneProtocol

- Surface: ccf.controlplane.registry.ControlPlaneProtocol
- Public surface: true
- Change type: behavior
- Before: the Protocol exposed `audit_events()` (a read) and no appendable log; only the in-process `ControlPlaneRegistry` had `audit_log`
- After: the Protocol declares the `audit_log` property (the append-only `AuditLog` the plane records into), as `ControlPlaneRegistry` already implemented it
- Why: D-IMPL-354 — a composition root records its `composition` decision on the plane's own log before minting; a plane with no appendable log cannot host a composition. On the surface for `register_versioned`'s reason: a remote plane cannot conform while quietly dropping it (FABR-07 obligation)
- Migration: a remote/alternative Control Plane implementation exposes its log as `audit_log`

## ccf.deployment.manifest.register_manifest_entries

- Surface: ccf.deployment.manifest.register_manifest_entries
- Public surface: true
- Change type: behavior
- Before: called `register_versioned(entry.key, ...)` / `register_typed(entry.key, ...)` with a bare key
- After: for each entry mints `Register` for exactly `entry.key` through the recipe (tenant = the key's own tenant segment; a key with no segment is refused with `CrossTenantKeyRefused` before minting) and passes the capability; one `composition` audit event per entry precedes each registration
- Why: D-IMPL-354 (composition-time registrations); §1.3 (the key's tenant is the capability's)
- Migration: none for tenant-prefixed keys; a deployment whose manifest keys are bare cannot register them until the bare-key question is ruled (reported)

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: booted with no tenant handed to `boot()`
- After: passes `tenant_ids=(resolved_tenant,)` — the one tenant the manifest resolves — so the fabric is composed for it and its invalidation register is mintable
- Why: `boot()` requires it (above)
- Migration: none

## ccf.peering.admission.PeeringAdmissionGate

- Surface: ccf.peering.admission.PeeringAdmissionGate
- Public surface: true
- Change type: reshaped
- Before: `PeeringAdmissionGate(*, identity, control_plane, audit_log, artifact_store, tenant_id, trust_policy_version, payload_ceiling_version, product_classes)`; persisted the admission record with `put(tenant_id=..., artifact_class=..., name=..., artifact=...)`
- After: `PeeringAdmissionGate(*, identity, control_plane, audit_log, artifact_store, authorized: Authorized[ReplayMint], trust_policy_version, payload_ceiling_version, product_classes)` — first statement `verify(authorized, kind=ReplayMint, resource=ADMISSION_RECORD.class_id)`; **the tenant the gate admits for IS `authorized.tenant`** (`tenant_id` deleted); the record is a `DerivedWrite` under the capability
- Why: §1.2 (the handle's caller holds the capability for its own evidence class), §1.3 (no second source for the tenant); the gate is not a composition root
- Migration: the deployment composing the gate mints `ReplayMint` for `ADMISSION_RECORD.class_id` under the admitting tenant (tests: `tests/composition.py::composition_replay_mint`) and declares that class on the store's `WriteKinds`

## ccf.peering.admission.payload_ceiling_key

- Surface: ccf.peering.admission.payload_ceiling_key
- Public surface: true
- Change type: behavior
- Before: `ccf.inbound-payload-ceiling/{tenant_id}`
- After: `{tenant_id}/ccf.inbound-payload-ceiling`
- Why: §1.3 (see `register_key`)
- Migration: derive through the builder

## ccf.peering.trust_policy.trust_policy_key

- Surface: ccf.peering.trust_policy.trust_policy_key
- Public surface: true
- Change type: behavior
- Before: `ccf.peering-trust-policy/{tenant_id}`
- After: `{tenant_id}/ccf.peering-trust-policy`
- Why: §1.3 (see `register_key`)
- Migration: derive through the builder

## ccf.products.entitlement.product_entitlement_key

- Surface: ccf.products.entitlement.product_entitlement_key
- Public surface: true
- Change type: behavior
- Before: `ccf.product-entitlement-policy/{tenant_id}`
- After: `{tenant_id}/ccf.product-entitlement-policy`
- Why: §1.3 (see `register_key`); the paved door registers this key at composition and must mint for the tenant, not the class name
- Migration: derive through the builder; a provenance identity that spelled the old string (one test did) is the new string

## ccf.products.child_resolver.QuestionBoundChildResolver

- Surface: ccf.products.child_resolver.QuestionBoundChildResolver
- Public surface: true
- Change type: reshaped
- Before: `QuestionBoundChildResolver(*, ledger, agent_definition_hash, gate, child_questions, callable_registry, artifact_store, mcp_skills=None, peering_skills=None, peering_gate=None, child_arguments=None)`; retained each question with `put(tenant_id=gate.tenant_id, artifact_class=CHILD_QUESTION_CLASS, ...)`
- After: adds `authorized: Authorized[ReplayMint]` (keyword, required): verified at construction against exactly `CHILD_QUESTION_CLASS`, its tenant held equal to `gate.tenant_id` once (`QuestionRetentionUnauthorized`); the question is a `DerivedWrite` under it
- Why: §1.2 / §2 P3 — the resolver is not a composition root and receives the evidence-class capability its composer minted
- Migration: `open_product` mints and passes it; a `build_children=` factory or a hand composition mints `ReplayMint` for `CHILD_QUESTION_CLASS` under the consumer tenant

## ccf.products.child_resolver.QuestionRetentionUnauthorized

- Surface: ccf.products.child_resolver.QuestionRetentionUnauthorized
- Public surface: true
- Change type: added
- Before: absent
- After: `PermissionError` raised at construction when the capability's tenant is not the gate's
- Why: §1.3 — one consumer tenant, compared once
- Migration: none

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: constructed `ReplayWriter(store=, artifact_class=)` / `QueryPinWriter(...)` per serve and filed admitted child contracts with `put(tenant_id=..., ...)`; registered `max_ttl_key` and `request_contract_key` with bare keys
- After: the constructor is unchanged (no new parameter; every construction site keeps working); `__post_init__` (1) refuses a store that does not declare `replay_record_class`, `query_pin_class` and `ADMITTED_CHILD_CONTRACT_CLASS` under `ReplayMint` (`UndeclaredMechanismClass` — fail closed at boot, never at the first write; a store exposing no `write_kinds` is refused the same way), (2) mints through the recipe three `ReplayMint` (one per class) and two `Register` (the declaration's `max_ttl_key`, the `request_contract_key`), audited with the process clock — never `admission_clock` — and holds them in one `init=False` value. Writers are built from the held capabilities; `_register` registers under them and refuses a declaration whose `max_ttl_key` differs from the minted one
- Why: D-IMPL-354 — the resolver's constructor and factories ARE its composition (this module is a `COMPOSITION_MINT_SITES` root). Authorities as constructor parameters were rejected because that makes every caller of a resolver a minter
- Migration: the store handed to a resolver declares the three classes under `ReplayMint` (`build_governed_resolver`, `open_product` and the in-process adapter declare them when they build the store)

## ccf.products.resolver.UndeclaredMechanismClass

- Surface: ccf.products.resolver.UndeclaredMechanismClass
- Public surface: true
- Change type: added
- Before: absent
- After: `TypeError` raised by `GovernedResolver.__post_init__` and `ReplayRefusalRecorder.__post_init__` when the store does not declare a class the resolver/recorder writes under `ReplayMint`
- Why: fail closed at construction rather than at the first governed write
- Migration: declare the class on the store's `WriteKinds`

## ccf.products.resolver.ReplayRefusalRecorder

- Surface: ccf.products.resolver.ReplayRefusalRecorder
- Public surface: true
- Change type: reshaped
- Before: `ReplayRefusalRecorder(*, artifact_store, replay_record_class, tenant_id, assembly_mode, policy_bundle_pin=None, disclosure_level_for=<factory>)`
- After: `ReplayRefusalRecorder(*, authorized: Authorized[ReplayMint], artifact_store, assembly_mode, policy_bundle_pin=None, disclosure_level_for=<factory>)` — `replay_record_class` and `tenant_id` are read-only properties of the capability (its resource, its tenant); verified at construction, and the store must declare the class (`UndeclaredMechanismClass`)
- Why: §1.2, §1.3 — no second source for the class or the tenant; the recorder holds the one capability its composition minted
- Migration: `declared_refusal_recorder` and `build_governed_resolver` mint it; a hand composition mints `ReplayMint` for the record class under the tenant

## ccf.products.resolver.declared_refusal_recorder

- Surface: ccf.products.resolver.declared_refusal_recorder
- Public surface: true
- Change type: behavior
- Before: built the recorder from `replay_record_class` and `tenant_id`
- After: same signature; mints `ReplayMint` for `replay_record_class` under `tenant_id` through the recipe on `control_plane.audit_log` and builds the recorder over it
- Why: this function is the recorder's composition
- Migration: none

## ccf.products.resolver.build_governed_resolver

- Surface: ccf.products.resolver.build_governed_resolver
- Public surface: true
- Change type: behavior
- Before: built a `FileArtifactStore(root=...)` from a declared `store_dirname`; built the SDK's recorder from class and tenant
- After: same signature; the store it builds declares `record_class`, `pin_class` and `ADMITTED_CHILD_CONTRACT_CLASS` under `ReplayMint`; the recorder it builds holds a recipe-minted `ReplayMint`; the resolver it returns has minted its own authorities (above)
- Why: D-IMPL-353 §1.2 (`write_kinds` has no default); D-IMPL-354
- Migration: a caller passing `artifact_store=` passes one that declares the three classes

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: built `FileArtifactStore(root=scratch/<store_dirname>)`; the derived consumer chain **requested one grant per declared skill** (`actor=agent.name`) and built the child resolver with no capability
- After: same signature; the store it builds declares the `replay:` binding's two classes plus `ADMITTED_CHILD_CONTRACT_CLASS` and `CHILD_QUESTION_CLASS` under `ReplayMint`; the derived chain registers the agent, skills and regime (composition-time `Register`), mints `ReplayMint` for `CHILD_QUESTION_CLASS` under the agent's tenant for the child resolver, reads which declared skills are bound to the agent, and **raises `GrantNotInForce`** for any that is not — it grants nothing
- Why: `GrantLedger.request` requires `Authorized[SkillGrant]`, a door kind a composition root may not mint (D-IMPL-353 §1.6; D-IMPL-354). A deployment that could grant itself skills at open was ambient authority
- Migration: grant the declared skills to the agent through a governed door as an authorized principal before opening; whether the paved road may make declared grants at composition is reported for ruling

## ccf.products.product.GrantNotInForce

- Surface: ccf.products.product.GrantNotInForce
- Public surface: true
- Change type: added
- Before: absent
- After: `PermissionError` raised by `open_product`'s derived chain naming the declared skills not granted to the composing agent on this Control Plane
- Why: above
- Migration: none

## ccf.skills.catalog.SkillCatalog

- Surface: ccf.skills.catalog.SkillCatalog
- Public surface: true
- Change type: reshaped
- Before: `register(entry, *, actor=None)` — the catalog derived the key and called `register_versioned(key, entry, SKILL_CATALOG_ENTRY, actor=actor)`
- After: `register(authorized: Authorized[SkillCatalogRegister] | Authorized[Register], entry)` — the catalog derives `skill_catalog_key(entry)` and binds the capability to it with `verify_any` BEFORE anything reaches the registry (wrong key, wrong kind, fabricated or retargeted all die there); `actor` is deleted (the audit actor is `authorized.principal`). `discover` and `resolve` are unchanged
- Why: §1.2 (the handle's caller holds the capability for its own action; the door kind is `skill.catalog.register`, the composition kind is `Register` for the entry's key), §1.5f
- Migration: the `skill.catalog.register` route passes its gate-minted capability; a deployment declaring entries at boot mints `Register` for `skill_catalog_key(entry)` (tests: `tests/composition.py::register_skill_entry`)

## ccf.client.adapters.inprocess.InProcessAdapter

- Surface: ccf.client.adapters.inprocess.InProcessAdapter
- Public surface: true
- Change type: behavior
- Before: booted the bound deployment over `FileArtifactStore(root=document.artifact_store)`
- After: the store declares the binding document's `replay_record_class` and `query_pin_class` plus `ADMITTED_CHILD_CONTRACT_CLASS` under `ReplayMint`; the resolver it builds mints its own authorities against that declaration and refuses at boot if a class it files is undeclared
- Why: D-IMPL-353 §1.2 — `write_kinds` has no default; the adapter is a composition site and states what its deployment's mechanism writes
- Migration: none for a binding document; a deployment on another substrate declares the same classes on its own store
