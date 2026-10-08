# 378-07 — the temporal-boundary migration note, the boot result's placed keys, and two diagnostics

`D-IMPL-378`: the four documentation and diagnostic items Dave ordered after the
`D-IMPL-377` close-out (its §7e; Dave, 14:27 MST: *"docs/diagnostic items go to a
follow-up batch after this close-out"*). Two are code changes, each built red
first with one executed severing. The rest correct documentation the estate run
showed to be wrong.

**The migration this fragment exists to record.** Since `3976cbc1` (`D-IMPL-358`
step 5) every governed serve resolves the tenant's temporal boundary before
anything is acquired, and a tenant with none declared is refused with reason
`temporal-boundary-undeclared`. No fragment recorded that change when it landed:
`358-05` anticipated it (*"once enforcement lands … will refuse"*) and `358-08`
recorded only the write guard. The adopter documentation is section 4.14 of
`public/how-to/security-and-deployment.md`. The bare-key half is the false
*"Migration: none"* in `353-09`, struck there in place with a dated correction;
`public/reference/artifacts/deployment-manifest.md` now states the placed keys.

## ccf.products.resolver.GovernedResolver

- Surface: ccf.products.resolver.GovernedResolver
- Public surface: true
- Change type: behavior
- Before: until `3976cbc1` a governed serve applied no temporal bound, so a question asked as of any instant, however far before or after the serve instant, was assembled
- After: same signature. Every serve resolves the tenant's `TemporalBoundaryPolicy` at `{tenant}/ccf.temporal-boundary-policy` (`ccf.controlplane.temporal_boundary.resolve_temporal_boundary`) and judges the question's `asked_at`, and separately the decision instant the class derives, against the trusted serve instant before anything is acquired (`ccf.products.refusal.refuse_temporal_bound`). Undeclared: a `temporal-bound-refusal` with reason `temporal-boundary-undeclared`, recorded in Decision Replay with the key that was required and no policy binding; at `minimal` the caller sees *"this tenant does not answer for the instant this question names"*, and the HTTP status is 400. Declared: an instant outside the window is refused `asked-at-outside-temporal-bound` or `decision-instant-outside-temporal-bound`, and the policy's exact version is pinned on the record of the served decision or of the refusal its window caused. The paved road also holds each acquired envelope to the same window (`358-08`)
- Why: `D-IMPL-358` step 5 with ruling 11. The SDK holds no duration (`D-IMPL-38`), so absence refuses rather than defaulting. This is the migration note step 5 left unwritten (the `D-IMPL-377` close-out, §7e item 1 and restriction 21; estate families A and A')
- Migration: **required.** A deployment upgraded from before `3976cbc1` boots normally and then serves no governed question until it declares a temporal boundary for each tenant it serves. Every tag so far, `v0.1.0`, `v1.0.0` and `v1.0.1`, predates `3976cbc1` (measured with `git merge-base --is-ancestor`), so this applies to an upgrade from any tagged release. Declare it as a `temporal_boundary:` section in `ccf_config.yaml` holding `max_past_seconds` and `permitted_clock_skew_seconds` (the config needs a top-level `tenant_id`), or as a manifest entry with `key: ccf.temporal-boundary-policy`, `class_id: ccf.temporal-boundary-policy`, `role: register` and `registration: typed`, as `examples/s1-01-hello-context-product/artifacts/manifest.yaml` does. A composition root serving several tenants registers one policy per tenant at `temporal_boundary_policy_key(tenant_id=...)`. Both values are policy decisions: `0` is the strictest bound, no value means unbounded, and a negative value is refused. Section 4.14 of the security how-to describes the refusal and how to choose the values

## ccf.controlplane.temporal_boundary.TemporalBoundaryPolicy

- Surface: ccf.controlplane.temporal_boundary.TemporalBoundaryPolicy
- Public surface: true
- Change type: behavior
- Before: the class docstring said "the comparison itself is **not implemented at this step**", and the module docstring said "It does *not* enforce anything", with the resolver work still to come. Both were written at step 3 and have been stale since `3976cbc1`
- After: documentation only; no code path changed. The class docstring names `ccf.products.refusal.refuse_temporal_bound` as the comparison, live on every governed serve. The module docstring adds that enforcement has landed in the callers (`GovernedResolver`, `IngressTemporalBound`) and that an undeclared tenant is refused, while the module itself still reads no clock
- Why: the temporal-boundary item (the `D-IMPL-377` close-out, §7e item 1). The SDK's own reference text told a reader the boundary was not enforced
- Migration: none

## ccf.controlplane.temporal_boundary.PinnedTemporalBoundary

- Surface: ccf.controlplane.temporal_boundary.PinnedTemporalBoundary
- Public surface: true
- Change type: behavior
- Before: the `binding` property's docstring said *"Nothing appends this yet"*
- After: documentation only. The resolver carries exactly this binding on the record of a served decision and on the record of a refusal the declared window caused, and carries none when the policy is undeclared
- Why: as for `TemporalBoundaryPolicy`
- Migration: none

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: behavior
- Before: the docstring said `artifacts` is *"keyed by manifest key"* and showed `{key: booted.artifacts[key] for key in (...)}` *"naming its own manifest keys"*; `pins` said nothing about its keys. Both have been wrong for a bare authored key since `D-IMPL-354` placed every key under the tenant (`353-09`)
- After: documentation only. `pins` and `artifacts` are documented as keyed by the manifest key as placed under the deployment's tenant: `{tenant}/policy` for an authored `policy`, and a key already under the tenant unchanged. The docstring names the lookups that work (`booted.keys.<section>`, or `namespaced_key(tenant=booted.tenant_id, key=...)`) and what a bare key gets (`KeyError`, `None` from `.get`, `UnpinnedArtifactError`). `keys` is documented as placed too
- Why: the `D-IMPL-377` close-out, §7e item 2 (estate family R): example code followed the docstring and read its artifacts and pins by bare keys
- Migration: none; read the boot result by the placed key, as the corrected `353-09` entry for `namespaced_key` now says

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: the docstring's day-1 paragraph told the adopter to read `booted.artifacts[<signal-batch-key>]` and to name its own manifest keys against `booted.artifacts`, without saying those keys come back placed under the tenant
- After: documentation only. The paragraph says every key there is placed under the tenant and points to `BootedFabric.artifacts`
- Why: as for `BootedFabric`
- Migration: none

## ccf.deployment.operators.build_operator_registry

- Surface: ccf.deployment.operators.build_operator_registry
- Public surface: true
- Change type: behavior
- Before: the `parameters` docstring showed `{key: booted.artifacts[key] for key in (...)}` as *"naming its own manifest keys"*
- After: documentation only. It says the manifest keys are named as placed under the tenant, which is how `BootedFabric.artifacts` holds them
- Why: as for `BootedFabric`
- Migration: none

## ccf.deployment.pins.ArtifactPin

- Surface: ccf.deployment.pins.ArtifactPin
- Public surface: true
- Change type: behavior
- Before: `key` was documented as *"taken verbatim from the manifest entry"*, which reads as the key the author wrote and is wrong for a bare one
- After: documentation only. `key` is the key the entry was registered under; for a pin a loader produced, the manifest key as placed under the tenant
- Why: as for `BootedFabric`
- Migration: none

## ccf.deployment.pins.ResolvedPins

- Surface: ccf.deployment.pins.ResolvedPins
- Public surface: true
- Change type: behavior
- Before: `version_for("policy")`, against a pin recorded under `{tenant}/policy`, raised `UnpinnedArtifactError` saying *"the manifest either does not name it or names it with role 'load'"*. Both causes are false in that case (measured on a `load_config_and_boot` fabric)
- After: same signature, same exception type, and the same exact lookup; nothing is re-derived or chosen. When the missed key is the bare form of a recorded key (the text after its tenant segment), the message names the recorded key and the cause: a loader records each pin under its manifest key as placed under the deployment's tenant (`manifest_under_tenant`, `D-IMPL-354`). It also names the remedy (`BootedFabric.keys`, `namespaced_key`). Every other miss keeps the `D-IMPL-80` message. `ResolvedPins` still has exactly one public method, and `UnpinnedArtifactError`'s docstring names the third situation
- Why: the `D-IMPL-377` close-out, §7e item 3. Red: `tests/deployment/test_pins_tenant_key_diagnosis.py::test_a_bare_key_names_the_placed_key_its_pin_is_recorded_under`, `::test_a_bare_key_holding_a_separator_is_diagnosed_the_same_way` and `::test_a_booted_fabrics_pins_name_the_placed_key_for_a_bare_lookup`. One severing, the diagnosis branch disabled, reddens all three
- Migration: none. The exception type is unchanged; a caller that matched the old message text on a bare-key miss reads the new one

## ccf.products.request.ProductRequestContract

- Surface: ccf.products.request.ProductRequestContract
- Public surface: true
- Change type: behavior
- Before: `from_declared(None)` raised `AttributeError: 'NoneType' object has no attribute 'declaration'`, and a raw mapping raised the same for `dict`: the interpreter's error, not a refusal. `None` is what `booted.artifacts.get("request_contract")` returns, since the boot result holds that artifact under `{tenant}/request_contract`
- After: same signature. An argument carrying no `declaration` mapping is refused first, in the method's existing convention: a `ValueError` naming the guard (*"… was handed None, which is not a declared artifact …"*). For `None` the message names the placed keys of `BootedFabric.artifacts` and the remedy. A `DeclaredArtifact` reads exactly as before
- Why: the `D-IMPL-377` close-out, §7e item 4. Red: `tests/products/test_from_declared_refuses_a_non_artifact.py::test_none_is_refused_by_name_rather_than_raising_attribute_error` and `::test_a_raw_mapping_is_refused_by_the_same_guard`. One severing, the original dereference restored with the refusal disabled, reddens both
- Migration: a caller that caught `AttributeError` here catches `ValueError`, which the method's `Raises` section already named for every malformed declaration
