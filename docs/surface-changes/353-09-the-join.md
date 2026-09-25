# 353-09 — the join: one key derivation, and the names the join itself changed

`D-IMPL-353`'s seven lanes and three join lanes were merged on `security-tier-0`
on 2026-09-24. This fragment records the public names the JOIN changed while
reconciling them — nothing a lane claimed in `353-01` … `353-08`.

## What did NOT change, stated first

- **No door signature and no handle signature changed here.** Those are the
  lanes' (`353-02` … `353-07`).
- **No action id changed value.**

## ccf.controlplane.registry.namespaced_key

- Surface: ccf.controlplane.registry.namespaced_key
- Public surface: true
- Change type: added
- Before: absent — the config loader derived bare section keys (`product_class`, `policy`, `half_life`, `policy_constraints.<label>`) and the binding document named them the same way; under the `{tenant}/{class}[/{name}]` grammar the registry enforces (§1.3) a bare key belongs to nobody and, once every registration required a capability, could not be registered at all
- After: `namespaced_key(*, tenant, key)` — the one derivation that CONFINES a deployment's key to its resolved tenant: a key already under `{tenant}/` is returned unchanged; every other key, bare or prefixed, is placed under it (`{tenant}/{key}`). Applied through `src/ccf/deployment/manifest.py::manifest_under_tenant` (manifest entries, the two boot keys, the parsed-artifact mapping, the resolver's `DeploymentKeys`) by the loader (`src/ccf/deployment/manifest.py::_register_and_boot`) and by the consumer chain `open_product` derives (`src/ccf/products/product.py::_derive_consumer_chain`), and in `src/ccf/client/adapters/inprocess.py::_boot` for the binding document's keys. Confinement rather than refusal because a section label may legitimately contain `/` (a policy constraint named by a path), so a leading segment is not evidence of an author's tenant claim; a deployment composed through the loader can never register outside its own tenant, and the audit log shows the confined key
- Why: `D-IMPL-354`: the loader is SDK mechanism, not an example; the grammar is the security invariant, so the loader adapts to it rather than the registry admitting tenant-less keys (which would let two tenants collide on one bare name). Direct callers of `register_manifest_entries` place their keys with `manifest_under_tenant` first; the register loop and the door handles keep the registry's own tenant-segment check
- Migration: none for a deployment that names bare keys — they are placed under its tenant; a deployment that authored keys under another prefix finds them under `{tenant}/{prefix}/…`, never under the other prefix

## ccf.deployment.manifest.manifest_under_tenant

- Surface: ccf.deployment.manifest.manifest_under_tenant
- Public surface: true
- Change type: added
- Before: absent — `register_manifest_entries` was handed a derived manifest whose keys were the bare section names, and the registry (before §1.3) admitted them
- After: `manifest_under_tenant(manifest, parsed, keys, *, tenant) -> (manifest, parsed, keys)` — applies `namespaced_key` to a derived manifest's entries and its two boot keys, to the parsed-artifact mapping keyed by those entries, and to the resolver's `DeploymentKeys` (`None` passes through), so the key an artifact is registered under and the key the resolver later reads are the same string by construction. Called by `src/ccf/deployment/manifest.py::_register_and_boot` and `src/ccf/products/product.py::_derive_consumer_chain`; a direct caller of `register_manifest_entries` (a test standing in for a deployment; `examples/cp-20-syndicated-lending-co-lender/deployment.py`, frozen under `D-IMPL-261` and recorded in its gap ledger) calls it before the loop, because the loop admits only keys already under a tenant
- Why: `D-IMPL-354`: one placement, applied at every composition root that hands a derived manifest to the register loop, rather than the loop guessing a tenant from a key segment
- Migration: a caller holding a `DerivedDeployment` and a resolved tenant calls `manifest_under_tenant(derived.manifest, parsed, derived.keys, tenant=<tenant>)` and registers the returned manifest and mapping; the returned `DeploymentKeys` are the strings to resolve by

## ccf.deployment.manifest.keys_under_tenant

- Surface: ccf.deployment.manifest.keys_under_tenant
- Public surface: true
- Change type: added
- Before: absent — a `DeploymentKeys` record held the bare section names the derivation produced, and every consumer of it read the Control Plane by those strings
- After: `keys_under_tenant(keys, *, tenant) -> DeploymentKeys` — every `str` field and every member of every `tuple` field through `namespaced_key`, `None` kept; idempotent for keys already under the tenant. `manifest_under_tenant` applies it to the keys it returns; `src/ccf/products/product.py::open_product` computes it once and exposes the result as `OpenedProduct.keys`
- Why: `D-IMPL-354`: the keys a product exposes, pins and resolves by must be the strings the loader registered — one derivation, applied where the record is handed out rather than re-derived by every reader
- Migration: a caller holding derived `DeploymentKeys` and a resolved tenant calls `keys_under_tenant(keys, tenant=<tenant>)` before reading the Control Plane by them

## ccf.products.product.OpenedProduct

- Surface: ccf.products.product.OpenedProduct
- Public surface: true
- Change type: behavior
- Before: `OpenedProduct.keys` was the derivation's `DeploymentKeys` — the bare section names (`product_class`, `policy`, `half_life`) — while every per-question boot registered the same artifacts under `{tenant}/…`; the refusal recorder's policy-bundle pin was recorded under the bare key
- After: same signature; `OpenedProduct.keys` is `keys_under_tenant(derived.keys, tenant=config.tenant_id)` — the placed strings the booted fabric holds and a served record's bindings carry — and the refusal recorder's `policy_bundle_pin` names the placed key, the same string the resolver's own records pin
- Why: `D-IMPL-354`: a public record naming a key the Control Plane does not hold under that string is a lie a replay reader would act on; found by `tests/products/test_d_impl_341_ttl_anchor.py::test_c1_an_evidence_anchored_class_expires_from_the_source_instant_not_the_decision`, whose record carried `{tenant}/half_life` while `opened.keys.half_life` read `half_life`
- Migration: none for a reader of `opened.keys` that compares against what the product served; a reader that compared against the bare section names now compares against the placed ones

## ccf.mcp.client.run_with_session

- Surface: ccf.mcp.client.run_with_session
- Public surface: true
- Change type: behavior
- Before: every exception the operation raised inside the session was re-raised as `McpServerUnreachable` — including `McpToolFailed` (a tool that reported an error) and `McpTimeout` — so `dispatch_skill`'s `tool-error` and `timeout` arms could never fire and a producer door refusing at its tenancy floor (`SEC-018`) reached the consumer's row as unreachability
- After: same signature; an error that is already a `McpClientError` — bare, or the member of the single-member exception group the transport's task group wraps it in — propagates as itself (`raise named from error`); only an error the client cannot classify becomes `McpServerUnreachable`, as before. Found at the join by `tests/products/test_d_impl_342_producer_refusal_evidence.py::test_c_a4a_a_door_refusal_whose_claims_fail_carries_no_producer_refusal`, whose door started refusing by error under `SEC-018`; the wrap predates the phase (`SEC353-J-02`)
- Why: `D-IMPL-353` §1.1 made doors refuse a tenant the grant does not carry; a refusal reported as an outage is the wrong fact in an audit row, and it hid two dead classification arms. The row vocabulary still has no reason for a producer that REFUSED by error rather than answered (`producer-unavailable` is what the slot reads) — reported for ruling
- Migration: a caller that caught `McpServerUnreachable` to mean "any failure" now sees `McpToolFailed` and `McpTimeout` by their own types; `McpTimeout` remains a subclass of `McpServerUnreachable`, so an `except McpServerUnreachable` still catches a timeout and no longer catches a tool error

## ccf.replay.serve.QueryPinWriter

- Surface: ccf.replay.serve.QueryPinWriter
- Public surface: true
- Change type: reshaped
- Before: `QueryPinWriter(*, store, artifact_class)`; `write_query_bytes(*, tenant_id, queries)` took the tenant from the caller
- After: `QueryPinWriter(*, authorized: Authorized[ReplayMint], store)` — the capability is verified at construction (kind, mint, resource = the pin class) and supplies the tenant and the class; `tenant_id` is a property read off it. The twin of `ReplayWriter` in `353-03`, whose entry Lane HANDLES wrote; this one was left unclaimed there and is recorded at the join on that lane's behalf (the shape gate `tests/test_surface_shape_capture.py::test_no_committed_plain_class_or_function_shape_is_disturbed` found it)
- Why: `D-IMPL-353` §1.2 — a writer of a governed evidence class holds the composition-minted capability for it; the tenant a pin is filed under is the capability's, never an argument
- Migration: `QueryPinWriter(authorized=mint_at_composition(ReplayMint, tenant=…, principal=COMPOSITION_PRINCIPAL, resource=<pin class>, decision_id=…), store=store)`; callers of `write_query_bytes` drop `tenant_id=`

## ccf.authz.capability.verify

- Surface: ccf.authz.capability.verify
- Public surface: true
- Change type: behavior
- Before: the mint record `(sentinel, kind, tenant, principal, resource, decision_id)` lived on every instance as `_minted`, and `verify` accepted ANY object whose `_minted` began with the module's sentinel and whose fields matched — so a holder of one genuine capability could read the sentinel off it and forge a capability for any kind, tenant or resource (`SimpleNamespace` or `Authorized.__new__` + `object.__setattr__`), and every handle honored it
- After: same signature; the mint record is held by the module in a private identity-keyed table (`_ISSUED`, a `WeakKeyDictionary`), never on the object; `verify` reads the record through `_issued(candidate)` — exact type `Authorized`, then identity membership — and only then compares the fields. A stand-in, an instance built around `__init__`, a copy, a pickle round-trip or an object carrying a stolen mint tuple is not a key and confers nothing; nothing a holder can read off a capability names the table or the sentinel
- Why: panel finding F-FORGE-01 at the join (codex, cursor and gemini independently; reproduced against the tree before the fix) — a CRITICAL under the brief's own threat model, fixed in-phase per `D-IMPL-352`; `tests/authz/test_capability.py::TestFabrication::test_a_forgery_carrying_the_real_sentinel_dies_at_use` and `test_a_copy_or_a_pickle_of_a_capability_is_not_the_capability` hold it; severings M4 and M25 (S-FORGE) redden them
- Migration: none for a holder that uses a capability; code that read `_minted` off a capability (nothing in `src/` or `runtime/` did; four test fixtures built forgeries through it) has no slot to read

## ccf.authz.capability.Authorized

- Surface: ccf.authz.capability.Authorized
- Public surface: true
- Change type: behavior
- Before: `__slots__` carried `_minted`; a capability could be `copy.copy`'d, `deepcopy`'d or pickled into an object `verify` then honored
- After: same constructor signature (the sentinel first, five keyword fields); `__slots__` carries `__weakref__` instead of `_minted`; `__reduce__` refuses copy and pickle by name (`CapabilityBypassError`: a capability is re-decided, never duplicated, §1.5g); `__setattr__`/`__delattr__` unchanged
- Why: F-FORGE-01 (above) — the record off the object, and no duplication path that would yield an object outside the table
- Migration: none; a capability is passed by reference and never copied

## ccf.deployment.manifest.register_manifest_entries

- Surface: ccf.deployment.manifest.register_manifest_entries
- Public surface: true
- Change type: reshaped
- Before: `register_manifest_entries(manifest, parsed, *, registry, only=None)` — the loop minted `Register` for the tenant it READ off each key (`_tenant_of_key`), so the registry's tenant-segment check compared the key's segment with itself
- After: `register_manifest_entries(manifest, parsed, *, registry, tenant, only=None)` — `tenant` is the tenant the composition root composes for; a key under any other tenant is refused by name (`CrossTenantKeyRefused`) BEFORE anything is appended or minted, and the loop mints for `tenant` and no other. The loader passes its resolved tenant; the consumer chain passes its deployment's; a direct caller says whose fabric it composes
- Why: panel (codex HIGH, cursor) at the join: a tenant derived from the key and then checked against the key is no check; `D-IMPL-354`'s composition authority must be a statement by the root, not a reading of the data. `tests/products/test_paved_road_grants.py::test_the_register_loop_mints_for_the_tenant_it_is_given_and_refuses_a_key_under_another` holds it; severing M28 reddens it
- Migration: add `tenant=<the deployment's resolved tenant>` (the frozen `examples/cp-20-syndicated-lending-co-lender/deployment.py` call now raises `TypeError`, recorded in the gap ledger under `SEC353-G-05`/`G-07`)

## ccf.deployment.register_manifest_entries

- Surface: ccf.deployment.register_manifest_entries
- Public surface: true
- Change type: reshaped
- Before: the package re-export of `ccf.deployment.manifest.register_manifest_entries` — `(manifest, parsed, *, registry, only=None)`
- After: the same re-export, now `(manifest, parsed, *, registry, tenant, only=None)`; see the entry for `ccf.deployment.manifest.register_manifest_entries`
- Why: one function, two names on the surface manifest
- Migration: as for `ccf.deployment.manifest.register_manifest_entries`

## ccf_runtime.http_api.grants.within_tenant

- Surface: ccf_runtime.http_api.grants.within_tenant
- Public surface: true
- Change type: added
- Before: absent — the read routes listed every tenant's keys (`keys_of_class`, `SkillCatalog.discover`) and resolved any key the caller named, checking only that the gate had allowed the read action
- After: `within_tenant(*, tenant, key) -> bool` — whether `key` is under `tenant` (the first segment of the Control Plane grammar); the agent, config and skill read routes apply it with the CAPABILITY's tenant: a list is the capability's tenant's keys/entries and no other tenant's; a keyed read (`resolution`, `declaration`) of another tenant's key reads as absent; `versions` of another tenant's key is `[]`, exactly as for an absent key
- Why: panel finding F-READ-01..04 (cursor, HIGH) at the join — a hostile authenticated tenant whose mapping allowed the read actions had cross-tenant reconnaissance after the allow; `D-IMPL-353` §1.3 puts the tenant on the capability for writes, and a read that names data must read the same tenant. `tests/http_api/test_join_routes_under_the_capability.py::test_a_read_after_an_allow_sees_only_the_capabilitys_tenant` holds it; severings M26 and M27 redden it
- Migration: a caller listing or reading its own tenant's artifacts sees no change; one that read another tenant's key sees the absent response

## ccf_runtime.http_api.grants.absent

- Surface: ccf_runtime.http_api.grants.absent
- Public surface: true
- Change type: added
- Before: absent — each read route raised its own 404 from `ControlPlaneMissing`
- After: `absent(key, version) -> HTTPException` — the 404 an absent registration gets, spelled once, so a key under another tenant is refused with a response byte-identical to the one a key that does not exist gets (no existence oracle across tenants; the same reasoning as `WorkflowTenantMismatchError` → 404). The door's test holds the two bodies equal
- Why: F-READ-04 (above)
- Migration: none

## ccf_runtime.http_api.routes.agent.build_router

- Surface: ccf_runtime.http_api.routes.agent.build_router
- Public surface: true
- Change type: behavior
- Before: `declarations` listed every tenant's agent keys; `declaration` and `versions` served any key the caller named after the gate's allow
- After: same signature; `declarations` lists the capability's tenant's keys; `declaration` of another tenant's key is the absent 404 (`absent`); `versions` of another tenant's key is `[]`
- Why: F-READ-01/-04 (see `within_tenant`)
- Migration: none for a caller reading its own tenant

## ccf_runtime.http_api.routes.config.build_router

- Surface: ccf_runtime.http_api.routes.config.build_router
- Public surface: true
- Change type: behavior
- Before: `keys` listed every tenant's keys in a class; `resolution` and `versions` served any key the caller named after the gate's allow
- After: same signature; `keys` lists the capability's tenant's; `resolution` of another tenant's key is the absent 404 (`absent`); `versions` of another tenant's key is `[]`
- Why: F-READ-03/-04 (see `within_tenant`)
- Migration: none for a caller reading its own tenant

## ccf_runtime.http_api.routes.skill.build_router

- Surface: ccf_runtime.http_api.routes.skill.build_router
- Public surface: true
- Change type: behavior
- Before: `catalog` returned every tenant's catalog entries after the gate's allow
- After: same signature; `catalog` returns the entries whose `tenant` is the capability's
- Why: F-READ-02 (see `within_tenant`)
- Migration: none for a caller reading its own tenant

## ccf_runtime.http_api.grants.tenant_from_request

- Surface: ccf_runtime.http_api.grants.tenant_from_request
- Public surface: true
- Change type: removed
- Before: the tenant read off the verified grant, kept by Lane CAP-GATE as `authorized_from_request(request).tenant` only for `routes/hitl.py` until Lane HITL-DOOR migrated
- After: deleted at the join; every route reads its tenant from the capability (`authorized_from_request(request, kind=…).tenant`) and nothing reads a tenant off a grant
- Why: `D-IMPL-353` §1.3 — the tenant on every write is the capability's; a second reader was a second source
- Migration: `authorized_from_request(request, kind=<the route's kind>).tenant`

## ccf_runtime.mcp.product_door.scope_mapping_key

- Surface: ccf_runtime.mcp.product_door.scope_mapping_key
- Public surface: true
- Change type: behavior
- Before: derived `{class}/{tenant}` — class first — so under the registry's tenant-segment rule the door's own scope mapping could only be registered by minting for the class id as if it were a tenant
- After: derives `{tenant}/{class}`, the grammar the registry reads the tenant from; the door mints `Register` for the tenant it composes for and the registry's check is a real check. Its sibling `product_entitlement_key` was flipped by Lane J-SRC (`353-07`)
- Why: `D-IMPL-353` §1.3; a capability whose tenant is a class id is a false statement in the audit log
- Migration: none for callers (the function derives); a deployment that persisted the old key string re-registers its mapping under the new one
