# 378-28 — a document that states one artifact class is refused as another

`D-IMPL-378`, lane 378d-classid, remedied under CLAUDE.md §9's three-issue cap with the
lightweight process. The open envelope, `src/ccf/controlplane/artifacts.py::DeclaredArtifact`
(`semver`, `class_id`, `declaration`), is the one Control Plane contract whose document states
the class it is, and `src/ccf/controlplane/artifacts.py::declared_artifact_class` builds an
`ArtifactClass` over that one contract for every adopter class id. A manifest entry or a
registering caller names the class the document is presented as. Before this change nothing
compared the two.

What was measured before this change, each as a red test committed first:

- **The parse door admitted it.** `parse_artifact` and `load_artifact` accepted a document
  stating `fixture.other-bundle` as `fixture.policy-bundle`, and a document stating the SDK's
  `ccf.workflow-definition` as an adopter's `acme.policy-bundle` (`D-IMPL-84` refuses that id as
  a manifest class; nothing read it inside the document).
- **The registry filed it.** `register_typed` bound the key to the presented class and audited
  that class, and the artifact resolved back stated the other one. `register_versioned` did the
  same for an adopter's own author-versioned contract that states its class.
- **The manifest door booted it.** `load_and_boot` registered and pinned the document as the
  entry's class (the pin is what Decision Replay dimension 2 carries) while
  `BootedFabric.artifacts` handed back a document stating another class. A `role: load` entry
  was handed back the same way.

What holds now is in `tests/controlplane/test_artifact_class_identity.py` and
`tests/deployment/test_document_class_identity.py`: the refusal by name, naming both classes,
with nothing registered, audited or booted, through `parse_artifact`, `load_artifact`,
`register_typed`, `register_versioned` and `load_and_boot` (both roles). Three controls show
that documents stating the class they are presented as still parse, register and boot.

**What this does NOT do.**

- **No SDK-owned typed class changes.** No SDK `ArtifactClass` constant, measured by importing
  every module of `ccf` and `ccf_runtime`, has a contract declaring a top-level `class_id`, and
  their contracts forbid extra fields, so a typed document cannot state a class at all. The check
  applies to a contract that declares the field: the open envelope, and an adopter's own contract
  that declares one.
- **The single-file config door and the paved road are unchanged in practice.** They build each
  adopter-owned section's document with the section's own `class_id`, so the two always agree;
  they run the same check at parse.
- **No content address and no replay record changes.** The check reads a document and adds
  nothing to it. A record served on the tree before this change, pinning an open-envelope policy
  bundle, replayed to its own address on the tree after it (lane measurement).
- **Replay reads are untouched.** `src/ccf/replay/engine.py::resolve_artifact` resolves by
  content address and contract, not through `ArtifactClass.validate`.

## ccf.controlplane.artifact_base.ArtifactClassIdMismatch

- Surface: ccf.controlplane.artifact_base.ArtifactClassIdMismatch
- Public surface: true
- Change type: added
- Before: absent. A document stating one class was parsed, registered, audited and pinned as another with no error
- After: a refusal that is both a `TypeError` and a `ValueError`, raised by `ArtifactClass.validate` when the artifact's contract declares a top-level `class_id` and the artifact states a class other than the `ArtifactClass`'s own. Its attributes are `presented_class_id` (the class it was parsed or registered as) and `document_class_id` (the class it states), and its message names both
- Why: `D-IMPL-378`, lane 378d-classid. A Control Plane document filed as a class it says it is not splits one fact across the audit plane, the pin and the artifact. Red tests: `tests/controlplane/test_artifact_class_identity.py::test_a_document_stating_another_class_is_refused_at_parse`, `::test_register_typed_refuses_an_artifact_stating_another_class_and_registers_nothing`, `::test_register_versioned_refuses_an_artifact_stating_another_class_and_registers_nothing`
- Migration: none; additive

## ccf.controlplane.artifacts.ArtifactClassIdMismatch

- Surface: ccf.controlplane.artifacts.ArtifactClassIdMismatch
- Public surface: true
- Change type: added
- Before: absent
- After: the same class as `ccf.controlplane.artifact_base.ArtifactClassIdMismatch`, re-exported beside `ArtifactClass` and `ArtifactLoadError`
- Why: `D-IMPL-378`, lane 378d-classid; the refusal is raised through `parse_artifact` and `load_artifact`, so it is named where they are
- Migration: none; additive

## ccf.controlplane.artifact_base.ArtifactClass

- Surface: ccf.controlplane.artifact_base.ArtifactClass
- Public surface: true
- Change type: behavior
- Before: same constructor. `validate` checked only that the artifact is an instance of the contract
- After: same constructor. `validate` also raises `ArtifactClassIdMismatch` when the artifact's contract declares a top-level `class_id` and the artifact states a class other than this one. The predicate is read from the artifact, so it holds however the `ArtifactClass` was built
- Why: `D-IMPL-378`, lane 378d-classid. Red tests: `tests/controlplane/test_artifact_class_identity.py::test_register_typed_refuses_an_artifact_stating_another_class_and_registers_nothing`, `::test_register_versioned_refuses_an_artifact_stating_another_class_and_registers_nothing`
- Migration: a caller that validated an open-envelope artifact against a class it does not state now meets the refusal. Present it as the class it states, or correct its `class_id`

## ccf.controlplane.artifacts.ArtifactClass

- Surface: ccf.controlplane.artifacts.ArtifactClass
- Public surface: true
- Change type: behavior
- Before: as `ccf.controlplane.artifact_base.ArtifactClass`
- After: as `ccf.controlplane.artifact_base.ArtifactClass`, which this name re-exports
- Why: `D-IMPL-378`, lane 378d-classid
- Migration: as `ccf.controlplane.artifact_base.ArtifactClass`

## ccf.controlplane.artifacts.parse_artifact

- Surface: ccf.controlplane.artifacts.parse_artifact
- Public surface: true
- Change type: behavior
- Before: same signature. A document stating a `class_id` other than the class it was parsed as was returned
- After: same signature. The validated document is held to the class by `ArtifactClass.validate`, so that document raises `ArtifactClassIdMismatch` (a `ValueError`) instead of being returned
- Why: `D-IMPL-378`, lane 378d-classid. Red test: `tests/controlplane/test_artifact_class_identity.py::test_a_document_stating_another_class_is_refused_at_parse`
- Migration: correct the document's `class_id`, or parse it as the class it states

## ccf.controlplane.artifacts.load_artifact

- Surface: ccf.controlplane.artifacts.load_artifact
- Public surface: true
- Change type: behavior
- Before: as `ccf.controlplane.artifacts.parse_artifact`, from YAML text
- After: as `ccf.controlplane.artifacts.parse_artifact`, which it calls
- Why: `D-IMPL-378`, lane 378d-classid. Red test: `tests/controlplane/test_artifact_class_identity.py::test_a_document_stating_another_class_is_refused_at_parse`
- Migration: as `ccf.controlplane.artifacts.parse_artifact`

## ccf.controlplane.artifacts.DeclaredArtifact

- Surface: ccf.controlplane.artifacts.DeclaredArtifact
- Public surface: true
- Change type: behavior
- Before: same fields. Its `class_id` was carried and never compared with the class it was parsed or registered as
- After: same fields. Its `class_id` is held to the class it is presented as by `ArtifactClass.validate`
- Why: `D-IMPL-378`, lane 378d-classid
- Migration: none for a document stating its own class

## ccf.controlplane.artifacts.declared_artifact_class

- Surface: ccf.controlplane.artifacts.declared_artifact_class
- Public surface: true
- Change type: behavior
- Before: same signature. The class it returned admitted an envelope stating any `class_id`
- After: same signature. The class it returns admits an envelope stating its own `class_id` only
- Why: `D-IMPL-378`, lane 378d-classid
- Migration: none for a document stating its own class

## ccf.controlplane.registry.ControlPlaneRegistry

- Surface: ccf.controlplane.registry.ControlPlaneRegistry
- Public surface: true
- Change type: behavior
- Before: same signatures. `register_typed` and `register_versioned` registered an artifact stating a `class_id` other than `artifact_class`'s, bound the key to `artifact_class` and audited it
- After: same signatures. Both raise `ArtifactClassIdMismatch` (a `TypeError`) from `artifact_class.validate`, before anything is stored or audited
- Why: `D-IMPL-378`, lane 378d-classid. Red tests: `tests/controlplane/test_artifact_class_identity.py::test_register_typed_refuses_an_artifact_stating_another_class_and_registers_nothing`, `::test_register_versioned_refuses_an_artifact_stating_another_class_and_registers_nothing`
- Migration: register an artifact under the class it states

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: behavior
- Before: same signature. An entry whose document stated a `class_id` other than the entry's class booted: the document was registered and pinned as the entry's class (`role: register`) or handed back under it (`role: load`)
- After: same signature. It raises `ArtifactClassIdMismatch` (a `ValueError`) while every document is parsed, before anything is minted or registered, whatever the entry's role
- Why: `D-IMPL-378`, lane 378d-classid. Red tests: `tests/deployment/test_document_class_identity.py::test_a_register_entry_whose_document_states_another_class_is_refused_at_boot`, `::test_a_load_entry_whose_document_states_another_class_is_refused_at_boot`
- Migration: a manifest whose entry names a class its document does not state boots no longer. Make the entry's `class_id` and the document's `class_id` the same class

## ccf.deployment.load_and_boot

- Surface: ccf.deployment.load_and_boot
- Public surface: true
- Change type: behavior
- Before: as `ccf.deployment.manifest.load_and_boot`
- After: as `ccf.deployment.manifest.load_and_boot`, which this name re-exports
- Why: `D-IMPL-378`, lane 378d-classid
- Migration: as `ccf.deployment.manifest.load_and_boot`
