# 378-26 — two manifest entries whose keys place to one key are refused at boot

`D-IMPL-378`, lane 378d-placement, remedied under CLAUDE.md §9's three-issue cap with the
lightweight process. Key placement (`D-IMPL-354`,
`src/ccf/deployment/manifest.py::manifest_under_tenant`) writes a bare key `k` as
`{tenant}/k` and leaves a key already written `{tenant}/k` unchanged. Two manifest entries
authored as `k` and `{tenant}/k` are different strings, so the manifest contract's own
key-uniqueness check (`DeploymentManifest._keys_are_unique`) admits them. Once placed they
are one Control Plane key.

What was measured before this change, each as a red test committed first:

- **One class: the deployment booted and one document was silently dropped.** Placement
  re-keyed the parsed documents into a mapping that holds one document per key (the later
  one in manifest order), and the register loop registered that survivor under both
  entries. The other document was never registered, never pinned and missing from
  `BootedFabric.artifacts`, with no error. Measured for two `ccf.half-life-table` entries
  through `load_and_boot` (a 3600-second half-life replaced by a 7-second one), and for two
  `ccf.operator-parameters.temporal` entries through `load_config_and_boot`
  (`require_valid_at_boundary: true` replaced by `false`).
- **Two classes: a late, unrelated refusal after a partial registration.** The survivor was
  registered under the earlier entry's class, and a `TypeError` stopped the boot only after
  the entries ahead of it were registered. With two adopter-owned bundle classes, the
  document registered as the policy bundle was the other bundle's.
- **A `role: load` entry ahead of a `register` one: the deployment booted** and the `load`
  document was missing from `BootedFabric.artifacts`.
- **The paved road** boots each question through `load_config_and_boot` and met the same
  late `TypeError` at its first question.

What holds now is in `tests/deployment/test_placed_key_collision.py`: the refusal by name,
naming both authored keys and the placed key, with nothing minted or registered, through
both boot doors, the paved road and the placement function itself. Two controls show that
entries at distinct placed keys, a bare key among them, still boot and both register.

**What this does NOT do.**
- **Placement itself is unchanged.** A bare key is still placed under the tenant and a key
  already under it is unchanged (`D-IMPL-354`); only a collision between two entries is
  refused.
- **One document under two keys that differ once placed is still admitted.** The contract
  permits a repeated `path` under different keys on purpose, and nothing here changes that.
- **The check reads the manifest's entries, not the caller's `parsed` mapping.** Every SDK
  caller passes a `parsed` mapping keyed by a subset of the entries' keys.
- **On the paved road the refusal arrives at the first question's boot,** from
  `OpenedProduct.answer`, because `open_product` boots nothing at open.

## ccf.deployment.manifest.ManifestKeysPlaceToOneKey

- Surface: ccf.deployment.manifest.ManifestKeysPlaceToOneKey
- Public surface: true
- Change type: added
- Before: absent. Two entries placing to one key either booted with one document silently dropped, or met an unrelated `TypeError` from the register loop after earlier entries were registered
- After: a `ValueError` subclass raised by `manifest_under_tenant` when two of the manifest's entries place to one key under the tenant, whatever their classes and roles, before anything is re-keyed, minted or registered. Its attributes are `authored_keys` (the two keys as the manifest wrote them, in manifest order), `placed_key` and `tenant`, and its message names all of them
- Why: `D-IMPL-378`, lane 378d-placement. One key holds one artifact in force, and a boot that keeps one of two documents for it loses a governance value with no record. Red tests: `tests/deployment/test_placed_key_collision.py::test_two_entries_of_one_class_placing_to_one_key_are_refused_at_boot`, `::test_two_adopter_classes_placing_to_one_key_are_refused_before_anything_is_registered`, `::test_a_load_entry_placing_onto_a_register_entry_is_refused_at_boot`, `::test_placement_itself_refuses_two_entries_placing_to_one_key_whatever_parsed_holds`
- Migration: none; additive

## ccf.deployment.ManifestKeysPlaceToOneKey

- Surface: ccf.deployment.ManifestKeysPlaceToOneKey
- Public surface: true
- Change type: added
- Before: absent
- After: the package-level spelling of `ccf.deployment.manifest.ManifestKeysPlaceToOneKey`
- Why: `D-IMPL-378`, lane 378d-placement; the refusal is raised through `ccf.deployment.load_and_boot` and `ccf.deployment.load_config_and_boot`, so it is named where they are
- Migration: none; additive

## ccf.deployment.manifest.manifest_under_tenant

- Surface: ccf.deployment.manifest.manifest_under_tenant
- Public surface: true
- Change type: behavior
- Before: same signature. Two entries placing to one key came back as two entries carrying one key, and a re-keyed `parsed` mapping holding one document for both
- After: same signature. Two entries placing to one key raise `ManifestKeysPlaceToOneKey` before anything is re-keyed. The check reads the manifest's entries, so a caller passing a partial `parsed` mapping (as the consumer chain `ccf.products.product.open_product` derives does) meets it too
- Why: `D-IMPL-378`, lane 378d-placement. Red test: `tests/deployment/test_placed_key_collision.py::test_placement_itself_refuses_two_entries_placing_to_one_key_whatever_parsed_holds`
- Migration: a manifest naming one artifact as both `k` and `{tenant}/k` keeps one of the two entries; two different artifacts need keys that differ once placed

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: same signature. A manifest whose entries placed to one key booted with one document silently dropped (same class), or raised an unrelated `TypeError` after a partial registration (different classes)
- After: same signature. It raises `ManifestKeysPlaceToOneKey` after every document is parsed and before anything is minted or registered
- Why: `D-IMPL-378`, lane 378d-placement. Red tests: `tests/deployment/test_placed_key_collision.py::test_two_entries_of_one_class_placing_to_one_key_are_refused_at_boot`, `::test_two_adopter_classes_placing_to_one_key_are_refused_before_anything_is_registered`, `::test_a_load_entry_placing_onto_a_register_entry_is_refused_at_boot`
- Migration: a deployment that booted with such a manifest boots no longer. Remove one of the two entries, or give the two keys that differ once placed

## ccf.deployment.load_and_boot

- Surface: ccf.deployment.load_and_boot
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.manifest.load_and_boot`
- After: as `ccf.deployment.manifest.load_and_boot`, which this name re-exports
- Why: `D-IMPL-378`, lane 378d-placement
- Migration: as `ccf.deployment.manifest.load_and_boot`

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: same signature. A `key:` override placing one section onto another section's placed key booted with one document silently dropped (two `operators:` entries of one category), or raised an unrelated `TypeError` after a partial registration (two sections of different classes). The paved road, which boots each question through this function, met the same `TypeError` at its first question
- After: same signature. It raises `ManifestKeysPlaceToOneKey` before anything is minted or registered, and the paved road raises it from `OpenedProduct.answer` at the first question's boot
- Why: `D-IMPL-378`, lane 378d-placement. Red tests: `tests/deployment/test_placed_key_collision.py::test_the_config_door_refuses_two_operator_entries_placing_to_one_key`, `::test_the_config_door_refuses_a_section_key_placing_onto_another_section`, `::test_the_paved_road_refuses_a_config_whose_sections_place_to_one_key`
- Migration: a `ccf_config.yaml` whose `key:` overrides place two sections onto one key boots no longer. Remove the override, or choose a key that differs from every other section's once placed

## ccf.deployment.load_config_and_boot

- Surface: ccf.deployment.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.config.load_config_and_boot`
- After: as `ccf.deployment.config.load_config_and_boot`, which this name re-exports
- Why: `D-IMPL-378`, lane 378d-placement
- Migration: as `ccf.deployment.config.load_config_and_boot`
