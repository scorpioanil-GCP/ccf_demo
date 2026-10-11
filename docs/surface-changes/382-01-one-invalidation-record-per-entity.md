# 382-01 (D-IMPL-382 option A, 2026-10-11 07:32) — one invalidation record per (tenant, entity), written under a capability confined to its own tenant's records of one class

`D-IMPL-382`, Dave, 2026-10-11 07:32 MST, adopting Grok's ruling: *"Implement option A after recording the
ruling. The authorization amendment covers only entity-invalidation records belonging to the capability's
tenant. It must not authorize another tenant, another artifact class, or general registry writes."*
*"State that the whole-register address disappears and each entity has its own version history. Verify that
updating or reading one entity no longer processes unrelated entities."* Built in lane `382-entity-records`,
red tests first. **SEC-020 stays OPEN**; no SEC row closes.

**What changed, and what disappears.** A tenant's invalidation boundaries were one
`EntityInvalidationRegister` artifact under `{tenant}/ccf.entity-invalidation`, re-registered whole on every
supersession and read whole on every serve. They are now one `EntityInvalidationRecord` per entity under
`{tenant}/ccf.entity-invalidation/{sha256(entity_uri)}`. **The whole-register content address no longer
exists**; each entity's record has its own address and **its own version history**. A supersession reads and
writes one entity's record; the serve-time dependency gate reads one record per touched entity;
`invalidation_history` reconstructs a tenant's history as the set of its entity chains. The advance rule is
unchanged: only a strictly later instant moves a boundary, and a write that does not move it registers nothing.

**What the tests measure.** `tests/controlplane/test_invalidation_per_entity.py` (3 cases, red at `d5a3f142`):
one supersession and one serve-time read stay under 4 KB of rendered or parsed bytes with 200 unrelated
entities on record (29,892 bytes before), and no key's history mixes entities.
`tests/controlplane/test_invalidation_record_authority.py` (11 cases): no door can obtain the kind; another
tenant, any other prefix, another artifact class, `register` and `register_versioned`, and every fabrication
are refused with nothing registered; a record read is a fresh object a mutation cannot reach.

## ccf.authz.capability.InvalidationRecordRegister

- Surface: ccf.authz.capability.InvalidationRecordRegister
- Public surface: true
- Change type: added
- Before: the invalidation sink held `Authorized[CompositionRegister]` for exactly one key per tenant.
- After: a composition-only kind (`action_id` `composition.invalidation-record.register`), in `COMPOSITION_KINDS`, minted only by `mint_at_composition`; `kind_for_action` refuses it by name. Its resource is the tenant's invalidation prefix.
- Why: `D-IMPL-382` option A — the one amendment to the one-key-per-capability rule of `D-IMPL-353` §1.2 / `D-IMPL-354`, confined by the registry to its own tenant's records of one class.
- Migration: a composition root that built a `ControlPlaneInvalidationSink` mints this kind for `register_key(tenant)` instead of `CompositionRegister`; `ccf.boot` does so.

## ccf.controlplane.registry.ControlPlaneRegistry

- Surface: ccf.controlplane.registry.ControlPlaneRegistry
- Public surface: true
- Change type: behavior
- Before: `register_typed` accepted the door kinds only and registered under the capability's resource.
- After: `register_typed` also accepts `InvalidationRecordRegister`, and only for the `ccf.entity-invalidation-record` class, only when the capability was minted for exactly its own tenant's `ccf.entity-invalidation` prefix, and only for a record naming that tenant; the key is derived by `invalidation_record_key`, never supplied. `register` and `register_versioned` refuse the kind. Every record passes through the same write and read doors as any artifact (`D-IMPL-380`).
- Why: `D-IMPL-382`, above.
- Migration: none for existing callers.

## ccf.controlplane.registry.invalidation_record_key

- Surface: ccf.controlplane.registry.invalidation_record_key
- Public surface: true
- Change type: added
- Before: no such function.
- After: `invalidation_record_key(*, tenant_id, entity_uri) -> str`, the derived key `{tenant}/ccf.entity-invalidation/{sha256(entity_uri)}`.
- Why: `D-IMPL-382`, above.
- Migration: none.

## ccf.controlplane.registry.INVALIDATION_RECORD_PREFIX

- Surface: ccf.controlplane.registry.INVALIDATION_RECORD_PREFIX
- Public surface: true
- Change type: added
- Before: the prefix lived only in `ccf.controlplane.invalidation.KEY_PREFIX`.
- After: `"ccf.entity-invalidation"`, the one class segment the invalidation-record capability may write under; `KEY_PREFIX` now names it.
- Why: the registry confines the capability to its tenant's prefix, so the registry owns the prefix (`D-IMPL-382`).
- Migration: none.

## ccf.controlplane.registry.INVALIDATION_RECORD_CLASS_ID

- Surface: ccf.controlplane.registry.INVALIDATION_RECORD_CLASS_ID
- Public surface: true
- Change type: added
- Before: no such constant; the register's class id was `ccf.entity-invalidation-register`.
- After: `"ccf.entity-invalidation-record"`, the one artifact class the invalidation-record capability may register; `ENTITY_INVALIDATION_RECORD` uses it. The class `ccf.entity-invalidation-register` no longer exists.
- Why: *"It must not authorize … another artifact class"* (`D-IMPL-382`).
- Migration: none; nothing shipped under the old class.

## ccf.controlplane.registry.TypedRegisterAuthority

- Surface: ccf.controlplane.registry.TypedRegisterAuthority
- Public surface: true
- Change type: added
- Before: `register_typed` was annotated `RegisterAuthority`.
- After: `RegisterAuthority | Authorized[InvalidationRecordRegister]`, the static type of `register_typed`'s first parameter on the registry and on `ControlPlaneProtocol`.
- Why: `D-IMPL-382`, above.
- Migration: none.
