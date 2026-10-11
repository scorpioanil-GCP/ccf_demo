# 378-41 (K1 follow-up) — a reserved `ccf.` class built directly refuses a document that states it

`D-IMPL-378` K1 follow-up, ruled (b) by Dave on 2026-10-08 at 16:40 MST: *"Close the direct-construction
bypass while preserving legitimate SDK classes."* The option he ruled on reads: *"Also refuse an envelope
stating a `ccf.` id inside `ArtifactClass.validate`, where the class-identity guard already reads the stated
id — one check that closes every route."* Built in lane 378f-k1b.

K1 (b) (fragment `378-35-k1`) made `src/ccf/controlplane/artifacts.py::declared_artifact_class` refuse an id
in the SDK's reserved `ccf.` namespace (`D-IMPL-84`). The public constructor still built the same class.
Measured on `6942dadc`: `ArtifactClass(class_id="ccf.workflow-definition", contract=DeclaredArtifact)` admitted
an envelope stating that id through `ArtifactClass.validate`, `parse_artifact`, `load_artifact` and
`ControlPlaneRegistry.register_typed`, and the registry bound the key to `ccf.workflow-definition` and
audited it.

What holds now is in `tests/deployment/test_reserved_class_id_in_validate.py`.
`src/ccf/controlplane/artifact_base.py::ArtifactClass.validate` refuses a document whose contract declares a
top-level `class_id`, once the class-identity check has held that stated id equal to the class's own, when the
id starts with `ccf.`. The refusal is `ReservedArtifactClassId`, raised before anything is registered or
audited. The red test runs eight routes for four reserved ids (an SDK id a manifest addresses, one no manifest
addresses, an invented one, and the bare prefix): `validate`, `parse_artifact`, `load_artifact`,
`register_typed`, `register_versioned` over an envelope carrying an author lane, `register_versioned` over an
adopter's own contract that declares `class_id`, a third-party Control Plane that validates as K2 obliges, and
a class id built as a `str` subclass that answers `startswith` for itself. The check reads the base
`str.startswith`, so that last one is refused too.

**Why the SDK's own classes are untouched.** The check reads only a document whose contract declares a
top-level `class_id`, and no SDK class does. Importing every module of `ccf` and `ccf_runtime` finds 39
`ArtifactClass` constants, each over its own typed contract, none declaring `class_id`. The controls in the same
module measure all 39, not a sample:

- each parses to its own contract, validates, and registers through the method its contract requires;
- the manifest door boots one manifest naming every manifest-addressable SDK class: all are validated, and
  every class whose role is `register` is pinned and bound;
- the config door and the paved road refuse nothing an SDK class presents.

**What this does NOT do.**

- **It does not refuse a `ccf.` class built directly over an adopter's own contract that states no class
  id.** `ArtifactClass(class_id="ccf.workflow-definition", contract=<an adopter's typed contract>)` still
  registers, and the key is bound to `ccf.workflow-definition`. The check reads a stated id, and such a
  document states none. The lane reports this residual for a ruling.
- **Untyped `register()` is unchanged.** It stores an envelope stating a `ccf.` id without binding any class,
  as before, and calls no `ArtifactClass`.
- **The boot doors are unchanged.** No door builds a reserved class over the envelope, so each still refuses an
  envelope stating a `ccf.` id by its own mechanism, before anything is audited. Measured on the manifest
  door, the single-file config door and the paved road:
  - `resolve_artifact_class` refuses a `ccf.` id the SDK does not ship or no manifest addresses, still as a
    plain `ValueError`;
  - an adopter entry whose document states a `ccf.` id is `ArtifactClassIdMismatch`;
  - an envelope under an SDK entry fails the SDK's typed contract (`ArtifactLoadError`);
  - an author-versioned SDK class declared `typed` is refused by `refuse_registration_the_sdk_fixes`.
- **One shape that used to register is now refused, and nothing in the tree uses it.** That shape is a subclass
  of an SDK contract that adds a `class_id` field, presented as the SDK's own constant while stating that
  constant's id. A scan of every tracked Python file finds no such subclass.
- **No document, record or content address changes.** The check reads a document and adds nothing to it. Three
  scans found nothing in the tree that relies on a document stating a `ccf.` id being admitted:
  - every tracked YAML and JSON document: no envelope-shaped document states a `ccf.` id;
  - every tracked Python file: the only `ArtifactClass` calls with a `ccf.` literal are the SDK's 39 constants;
  - every `ArtifactClass.validate` call the local suite makes: the only such calls come from the new test
    module.

## ccf.controlplane.artifact_base.ReservedArtifactClassId

- Surface: ccf.controlplane.artifact_base.ReservedArtifactClassId
- Public surface: true
- Change type: added
- Before: absent from this module. The class was defined in `ccf.controlplane.artifacts` and raised only by `declared_artifact_class`
- After: the same `ValueError`, carrying `class_id`, defined here beside `ArtifactClass.validate`, which now raises it, because `ccf.controlplane.registry` reaches it through `ArtifactClass` and must not import `ccf.controlplane.artifacts`. Its message names the id, cites `D-IMPL-84`, and says a document that states its own class is refused under a reserved id
- Why: `D-IMPL-378` K1 follow-up (b). Red test: `tests/deployment/test_reserved_class_id_in_validate.py::test_a_directly_built_reserved_class_refuses_a_document_stating_it_by_name`
- Migration: none; additive. `ccf.controlplane.artifacts.ReservedArtifactClassId` is the same class

## ccf.controlplane.artifacts.ReservedArtifactClassId

- Surface: ccf.controlplane.artifacts.ReservedArtifactClassId
- Public surface: true
- Change type: behavior
- Before: defined in this module and raised only by `declared_artifact_class`
- After: the same class, now defined in `ccf.controlplane.artifact_base` and re-exported here, and also raised by `ArtifactClass.validate`. Its message is reworded to cover both places it is raised; its attribute `class_id` and its `ValueError` base are unchanged
- Why: `D-IMPL-378` K1 follow-up (b), as for `ccf.controlplane.artifact_base.ReservedArtifactClassId`
- Migration: none for a caller that catches it by name or as `ValueError`. A caller that matched its message text reads the new wording

## ccf.controlplane.artifact_base.ArtifactClass

- Surface: ccf.controlplane.artifact_base.ArtifactClass
- Public surface: true
- Change type: behavior
- Before: same constructor. `validate` held a self-stating document to the class's own id and admitted it whatever that id was, so a class built directly under a `ccf.` id registered the open envelope under an SDK class name
- After: same constructor. `validate` raises `ReservedArtifactClassId` when the artifact's contract declares a top-level `class_id`, the artifact states this class's id, and that id starts with `ccf.`. It is checked after the class-identity check, so a document stating another class is still `ArtifactClassIdMismatch`
- Why: `D-IMPL-378` K1 follow-up (b). Red test: `tests/deployment/test_reserved_class_id_in_validate.py::test_a_directly_built_reserved_class_refuses_a_document_stating_it_by_name`
- Migration: code that built a `ccf.` class over the envelope registers an SDK class with the SDK's own `ArtifactClass` constant, or chooses a class id in its own namespace

## ccf.controlplane.artifacts.ArtifactClass

- Surface: ccf.controlplane.artifacts.ArtifactClass
- Public surface: true
- Change type: behavior
- Before: as `ccf.controlplane.artifact_base.ArtifactClass`
- After: as `ccf.controlplane.artifact_base.ArtifactClass`, which this name re-exports
- Why: `D-IMPL-378` K1 follow-up (b)
- Migration: as `ccf.controlplane.artifact_base.ArtifactClass`

## ccf.controlplane.artifacts.parse_artifact

- Surface: ccf.controlplane.artifacts.parse_artifact
- Public surface: true
- Change type: behavior
- Before: same signature. A self-stating document parsed as a class built directly under the `ccf.` id it states was returned
- After: same signature. That document raises `ReservedArtifactClassId` (a `ValueError`) from `ArtifactClass.validate`
- Why: `D-IMPL-378` K1 follow-up (b). Red test as for `ccf.controlplane.artifact_base.ArtifactClass`
- Migration: as `ccf.controlplane.artifact_base.ArtifactClass`

## ccf.controlplane.artifacts.load_artifact

- Surface: ccf.controlplane.artifacts.load_artifact
- Public surface: true
- Change type: behavior
- Before: as `ccf.controlplane.artifacts.parse_artifact`, from YAML text
- After: as `ccf.controlplane.artifacts.parse_artifact`, which it calls
- Why: `D-IMPL-378` K1 follow-up (b)
- Migration: as `ccf.controlplane.artifacts.parse_artifact`

## ccf.controlplane.artifacts.DeclaredArtifact

- Surface: ccf.controlplane.artifacts.DeclaredArtifact
- Public surface: true
- Change type: behavior
- Before: same fields. Its `class_id` was held to the class it was presented as, and the class could be built under a `ccf.` id
- After: same fields. It is also refused under a class id starting `ccf.`, however that class was built, as `ReservedArtifactClassId`
- Why: `D-IMPL-378` K1 follow-up (b)
- Migration: none for a document in an adopter's own namespace

## ccf.controlplane.registry.ControlPlaneRegistry

- Surface: ccf.controlplane.registry.ControlPlaneRegistry
- Public surface: true
- Change type: behavior
- Before: same methods. `register_typed` and `register_versioned` filed a self-stating document under a class built directly with the `ccf.` id it states, bound the key to that id and audited it
- After: same methods. Both raise `ReservedArtifactClassId` from `artifact_class.validate` for that document, before anything is stored or audited. A third-party plane that validates as `D-IMPL-378` K2 obliges refuses it the same way
- Why: `D-IMPL-378` K1 follow-up (b). Red test as for `ccf.controlplane.artifact_base.ArtifactClass`
- Migration: as `ccf.controlplane.artifact_base.ArtifactClass`
