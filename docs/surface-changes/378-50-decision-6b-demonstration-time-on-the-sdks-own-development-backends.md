# 378-50 (decision 6 (b)) — demonstration time only on the SDK's own approved development backends

`D-IMPL-378` decision 6, ruled (b) by Dave on 2026-10-09 (his 06:06 MST list, confirmed at 06:21 MST as "6b"):
*"(b). Restrict demonstration time to the SDK’s own approved development backends. Explicitly amend the broader
“declares itself” wording."* The option he ruled on reads: *"tighten the code to the SDK's own SQLite / in-memory
classes."* It amends C1 (b) (fragment `378-22`), under which a graph adapter whose own registration declared itself a
development reference was admitted. Built in lane 378i-devref.

The hole, found by the final panel (G-DEVREF): the guard
`src/ccf/products/demonstration_clock.py::_refuse_outside_development_substrates` admitted any graph adapter whose
`BackendRegistration.development_reference` was true, and a third-party registration can set that public field.
Measured on `a539c215` by the red test: a third-party adapter, resolved through the registry's real entry-point path,
that re-registers the SDK's own SQLite or in-memory store and declares the flag, composed a `DeclaredServeClock`; at the
in-process door its question was served at the declared instant.

What holds now (`tests/client/test_demonstration_serve_instant.py`):

- `src/ccf/graph/registry.py::is_sdk_development_reference` decides. It is true only for an adapter the SDK ships,
  found in the SDK's own adapter package directory and never through the `ccf.graph_backends` entry-point group,
  whose own SDK record declares `development_reference`. A third party cannot add a name to that directory, cannot
  claim one of its names through the group (`ReservedBackendName`), and `resolve` refuses a record that answers to a
  name it does not carry.
- A third-party registration's `development_reference` is never read. Red tests:
  `test_a_third_party_adapter_declaring_development_reference_is_refused_at_composition` (over both stores) and
  `test_a_third_party_adapter_declaring_development_reference_is_refused_at_the_in_process_door`.
- The SDK's own SQLite and in-memory adapters are still admitted:
  `test_the_sdks_own_development_backends_are_still_admitted_at_composition`.

**The choice made for the public field.** `BackendRegistration.development_reference` stays, with the same type and
default, and is read only on the SDK's own records. The alternatives were to refuse a third-party registration that
sets it, or to stop consulting it. Keeping it is the least surprising choice. Core may not name an adapter
(`D-IMPL-93` property (2), lint `cinv04-substrate-name`), so the SDK's own SQLite and in-memory records still need to
state the fact. Refusing a third-party registration that sets it would refuse every boot of that adapter, not only the
demonstration it asked for. `git grep -n development_reference -- src runtime` on this tree finds one reader,
`src/ccf/graph/registry.py::is_sdk_development_reference`, and two setters, the SDK's own SQLite and in-memory
records.

**What this does NOT do.**

- **It does not change the artifact-store half.** That half is still an `isinstance` test against `FileArtifactStore`,
  so a subclass of the SDK's store passes it. `test_a_subclass_of_the_sdks_file_store_passes_the_store_check`
  measures that, and SP §4.14 discloses it. The lane reports it for a ruling.
- **It does not verify which store a fabric booted.** The guard asks about the name on the booted handle's adapter pin,
  which `src/ccf/boot.py::boot` builds from the resolved record's own name. Deployment code that rewrites
  `FabricHandle.adapter`, or builds a `FabricHandle` directly, can name an SDK adapter over another store. That is
  deployment code inside the trusted-code assumption, not an adapter's declaration.
- **No refusal token, record or content address changes.** The refusal is the same class with the same reason token,
  `graph-substrate-not-development`; only its message is reworded.

## ccf.graph.registry.is_sdk_development_reference

- Surface: ccf.graph.registry.is_sdk_development_reference
- Public surface: true
- Change type: added
- Before: absent
- After: `is_sdk_development_reference(name: str) -> bool`. True only when `name` is an adapter the SDK ships (the built-in discovery source, the SDK's own adapter package directory) and the SDK's own registration record for it declares `development_reference`. False for every other name, including any third-party adapter, whatever its registration declares, and nothing is imported for such a name
- Why: `D-IMPL-378` decision 6 (b). Red test: `tests/client/test_demonstration_serve_instant.py::test_a_third_party_adapter_declaring_development_reference_is_refused_at_composition`
- Migration: none; additive

## ccf.graph.registry.BackendRegistration

- Surface: ccf.graph.registry.BackendRegistration
- Public surface: true
- Change type: behavior
- Before: same fields. `development_reference`, set to `True` by any registration, admitted a declared demonstration serve instant over that adapter; fragment `378-22`'s migration note invited a third-party development adapter to set it
- After: same fields, same default. `development_reference` is read only on the SDK's own registrations, through `is_sdk_development_reference`. On a third-party registration it is never read, so setting it no longer admits demonstration time
- Why: `D-IMPL-378` decision 6 (b), amending C1 (b)'s "declares itself"
- Migration: a third-party adapter that set `development_reference=True` boots as before, and a demonstration serve instant declared over it is now refused at composition (`DemonstrationServeInstantRefused`, reason `graph-substrate-not-development`). Demonstration time runs on the SDK's own SQLite or in-memory adapter

## ccf.products.demonstration_clock.compose_serve_clock

- Surface: ccf.products.demonstration_clock.compose_serve_clock
- Public surface: true
- Change type: behavior
- Before: same signature. Admitted a declaration over any graph adapter whose own registration declared `development_reference`, third-party adapters included
- After: same signature. Admits a declaration only over a graph adapter the SDK ships whose own registration is a development reference (`is_sdk_development_reference`), with an artifact store that is an instance of `FileArtifactStore` as before. `ccf.products.resolver.build_governed_resolver` and the in-process door call it, so both refuse the same way
- Why: `D-IMPL-378` decision 6 (b). Red tests: `tests/client/test_demonstration_serve_instant.py::test_a_third_party_adapter_declaring_development_reference_is_refused_at_composition` and `tests/client/test_demonstration_serve_instant.py::test_a_third_party_adapter_declaring_development_reference_is_refused_at_the_in_process_door`
- Migration: as `ccf.graph.registry.BackendRegistration`

## ccf.products.demonstration_clock.DemonstrationServeInstantRefused

- Surface: ccf.products.demonstration_clock.DemonstrationServeInstantRefused
- Public surface: true
- Change type: behavior
- Before: raised with reason `graph-substrate-not-development` when the graph adapter's own registration did not declare `development_reference`
- After: raised with the same reason when the graph adapter is not one of the SDK's own approved development backends, whatever its registration declares. The message says an adapter's declaration about itself does not count. The `artifact-store-not-development` reason, the `key` attribute and the `ValueError` base are unchanged
- Why: `D-IMPL-378` decision 6 (b)
- Migration: none for a caller that branches on the class or the reason token. A caller that matched the message text reads the new wording
