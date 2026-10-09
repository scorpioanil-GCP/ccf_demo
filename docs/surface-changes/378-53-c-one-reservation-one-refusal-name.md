# 378-53-c (OWED-RULINGS-3 3P2 (b)) — the manifest door's `ccf.` reservation refusal is `ReservedArtifactClassId`

`D-IMPL-378`, ruled by Dave on 2026-10-09 at 06:21 MST: *"3P1(a), 3P2(b)"*. Option 3P2 (b), from lane
`378f-k1b`'s proposal P2: *"Have `resolve_artifact_class` raise `ReservedArtifactClassId` too, so that one rule
has one name. It is a `ValueError` subclass, so existing callers keep catching it, but its message would
change."* Built in lane `378i-small`.

**What changed.** `D-IMPL-84` reserves the `ccf.` prefix for the SDK. `declared_artifact_class` and
`ArtifactClass.validate` refused it as `ReservedArtifactClassId`; `resolve_artifact_class` (the resolver the
manifest door, the single-file config door and the paved road share) refused the same reservation as a plain
`ValueError`. It now raises `ReservedArtifactClassId(class_id)`. Measured in
`tests/deployment/test_resolve_artifact_class_names_the_reservation.py` (an SDK id no manifest addresses, an
invented id and the bare prefix: refused as exactly that type, carrying the id, raised in
`resolve_artifact_class`; still a `ValueError` whose text names the id and cites `D-IMPL-84`) and, through the
doors, by the four shapes in `tests/deployment/test_reserved_class_id_in_validate.py` that pinned this
refusal's name as `ValueError` and now pin `ReservedArtifactClassId` (the manifest door; the config door and the
paved road). 9 tests failed before the change; severing (a plain `ValueError` restored) reddened the same 9.

**What a caller sees.** The type is a `ValueError` subclass, so a caller catching `ValueError` keeps catching
it. Its message is `ReservedArtifactClassId`'s: it still names the id and cites `D-IMPL-84`, and no longer says
"is not a class the SDK ships" or "correct the spelling of the SDK class you meant". Measured by `git grep`:
that text appeared only in `src/ccf/deployment/classes.py`, and every test that matched this refusal's text
matched `D-IMPL-84`. The empty-id refusal is a different rule and keeps its plain `ValueError`.

## ccf.deployment.classes.resolve_artifact_class

- Surface: ccf.deployment.classes.resolve_artifact_class
- Public surface: true
- Change type: behavior
- Before: a `ccf.` id the SDK does not ship raised a plain `ValueError` saying it is not a class the SDK ships.
- After: it raises `ccf.controlplane.artifact_base.ReservedArtifactClassId` (a `ValueError`) carrying `class_id`, with that class's message; an empty id still raises a plain `ValueError`.
- Why: `D-IMPL-378` OWED-RULINGS-3 item 3P2 (b): one rule, one name. Red test: `tests/deployment/test_resolve_artifact_class_names_the_reservation.py::test_3p2_b_the_resolver_refuses_a_reserved_id_as_reserved_artifact_class_id`.
- Migration: none for a caller catching `ValueError`; a caller matching the old message text reads the new one, or catches `ReservedArtifactClassId` by name.

## ccf.deployment.resolve_artifact_class

- Surface: ccf.deployment.resolve_artifact_class
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.classes.resolve_artifact_class`.
- After: the package-level spelling of the same change.
- Why: OWED-RULINGS-3 item 3P2 (b).
- Migration: as `ccf.deployment.classes.resolve_artifact_class`.

## ccf.controlplane.artifact_base.ReservedArtifactClassId

- Surface: ccf.controlplane.artifact_base.ReservedArtifactClassId
- Public surface: true
- Change type: behavior
- Before: raised by `declared_artifact_class` and `ArtifactClass.validate`.
- After: also raised by `resolve_artifact_class`, for a `ccf.` id the SDK does not ship, before the open envelope is reached. Unchanged class, attribute and message.
- Why: OWED-RULINGS-3 item 3P2 (b).
- Migration: none.

## ccf.controlplane.artifacts.ReservedArtifactClassId

- Surface: ccf.controlplane.artifacts.ReservedArtifactClassId
- Public surface: true
- Change type: behavior
- Before: as `ccf.controlplane.artifact_base.ReservedArtifactClassId`, which this name re-exports.
- After: the same change.
- Why: OWED-RULINGS-3 item 3P2 (b).
- Migration: none.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: an entry naming a `ccf.` class id the SDK does not ship raised a plain `ValueError`.
- After: it raises `ReservedArtifactClassId` (a `ValueError`), before anything is registered or audited, as before.
- Why: OWED-RULINGS-3 item 3P2 (b). Red test: `tests/deployment/test_reserved_class_id_in_validate.py::test_control_the_manifest_door_refuses_an_envelope_stating_a_reserved_id_by_its_own_mechanism`.
- Migration: none for a caller catching `ValueError`.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: behavior
- Before: a section naming a `ccf.` class id the SDK does not ship raised a plain `ValueError`.
- After: it raises `ReservedArtifactClassId` (a `ValueError`); the paved road (`ccf.products.product.open_product`) refuses the same section the same way.
- Why: OWED-RULINGS-3 item 3P2 (b). Red test: `tests/deployment/test_reserved_class_id_in_validate.py::test_control_the_config_door_and_the_paved_road_refuse_a_reserved_policy_class_by_their_own_mechanism`.
- Migration: none for a caller catching `ValueError`.
