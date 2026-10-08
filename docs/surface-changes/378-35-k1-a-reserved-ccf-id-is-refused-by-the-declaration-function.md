# 378-35 (K1) — the public declaration function refuses a reserved `ccf.` class id

`D-IMPL-378` K1, ruled (b) by Dave on 2026-10-08 at 12:29 MST: *"Refuse reserved ccf. names through
the public declaration function; preserve legitimate SDK registration."* Built in lane 378e-small.

`D-IMPL-84` reserves the `ccf.` prefix for the SDK. Before this change the reservation lived only in
`src/ccf/deployment/classes.py::resolve_artifact_class`, the resolver the manifest, the single-file
config and the paved road share. `src/ccf/controlplane/artifacts.py::declared_artifact_class`, the
public function a program calls to build an adopter class over the open `DeclaredArtifact` envelope,
applied none of it. Lane 378d-classid measured the consequence: `declared_artifact_class(
"ccf.workflow-definition")` returned an envelope class, and a document stating that id registered through
`ControlPlaneRegistry.register_typed` with its key bound to `ccf.workflow-definition`.

What holds now is in `tests/deployment/test_declaration_function_reserved_namespace.py`. The function
refuses `ccf.workflow-definition`, `ccf.hitl-policy`, `ccf.made-up-class` and the bare prefix with
`ReservedArtifactClassId`, before any class exists, so the probe's squat registers and audits nothing.
Four controls hold that legitimate registration is preserved: adopter namespaces (including
`ccfx.policy-bundle` and `fixture.ccf.thing`) still take the envelope and register; every SDK class id
still resolves to the SDK's own contract; and `load_and_boot`, `load_config_and_boot` and the paved road
still register the SDK's own `ccf.` classes, with the declaration function never handed a `ccf.` id on
any of them.

**Why the SDK needed no internal path around the refusal.** The SDK builds every one of its `ccf.`
classes as a typed `ArtifactClass` constant over its own contract: importing every module of `ccf` and
`ccf_runtime` finds 39 distinct constants, every one in the `ccf.` namespace and none over the envelope.
The only construction over the envelope is inside `declared_artifact_class`, and its only SDK caller,
`resolve_artifact_class`, serves an SDK id from its
reviewed mappings and refuses any other `ccf.` id before it reaches the envelope. The boot-path controls
measure the same thing at run time.

**What this does NOT do.**

- **It does not refuse the public `ArtifactClass` constructor.** A program that writes
  `ArtifactClass(class_id="ccf.workflow-definition", contract=DeclaredArtifact)` itself can still register
  an envelope under that id. That route is option (c) of the K1 sheet (refusing inside the shared
  validation step), which was not the ruled option; it is reported by lane 378e-small for a ruling.
- **`resolve_artifact_class` is unchanged.** It refuses the same reservation first, with its own
  manifest-oriented message, as a plain `ValueError`. Its prefix is now read from the same private
  statement in `ccf.controlplane.artifacts`, so the two doors cannot disagree about the prefix.
- **No document, record or content address changes.** A scan of every tracked YAML and JSON document
  found no envelope-shaped document stating a `ccf.` id, and no call in the tree passes a `ccf.` literal
  to the function.

## ccf.controlplane.artifacts.ReservedArtifactClassId

- Surface: ccf.controlplane.artifacts.ReservedArtifactClassId
- Public surface: true
- Change type: added
- Before: absent. `declared_artifact_class` built an envelope class for an id in the SDK's reserved `ccf.` namespace
- After: a `ValueError` raised by `declared_artifact_class` for an id starting `ccf.`, before any class exists. Its attribute `class_id` is the refused id, and its message names the id and cites `D-IMPL-84`
- Why: `D-IMPL-378` K1 (b). A program could register a document of arbitrary content under an SDK class name, the squat `D-IMPL-84` refuses for a manifest, and the registry would bind the key to that name and pin it into Decision Replay dimension 2. Red tests: `tests/deployment/test_declaration_function_reserved_namespace.py::test_the_declaration_function_refuses_a_reserved_ccf_id_by_name`, `::test_the_programmatic_squat_registers_nothing`
- Migration: none; additive

## ccf.controlplane.artifacts.declared_artifact_class

- Surface: ccf.controlplane.artifacts.declared_artifact_class
- Public surface: true
- Change type: behavior
- Before: same signature. It returned an envelope class for any id, including `ccf.workflow-definition` and every other `ccf.` id
- After: same signature. An id starting `ccf.` raises `ReservedArtifactClassId`; every other id is unchanged
- Why: `D-IMPL-378` K1 (b), extending `D-IMPL-84` from the manifest resolver to the public declaration function. Red tests as for `ReservedArtifactClassId`
- Migration: a program that passed a `ccf.` id registers an SDK class with the SDK's own `ArtifactClass` constant (for example `ccf.workflow.definitions.WORKFLOW_DEFINITION`), or chooses an id in its own namespace
