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
