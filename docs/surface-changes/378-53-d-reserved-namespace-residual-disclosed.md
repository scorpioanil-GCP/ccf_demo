# 378-53-d (OWED-RULINGS-3 3P1 (a)) — what the reserved `ccf.` namespace does not stop, disclosed and measured

`D-IMPL-378`, ruled by Dave on 2026-10-09 at 06:21 MST: *"3P1(a), 3P2(b)"*. Option 3P1 (a), from lane
`378f-k1b`'s proposal P1: *"Disclose and leave it. Writing a contract class and building an SDK-named class over
it is deliberate code. The reservation still holds for every document, manifest, config and envelope route."*
Built in lane `378i-small`. No behavior changes.

**R3**, measured by lane `378f-k1b` on `ae948439` and by this lane on `a539c215`:
`ArtifactClass(class_id="ccf.workflow-definition", contract=AdopterTyped)` and then `register_typed(...)`
registers, where `AdopterTyped` is a contract with a `semver` and a `body` and no `class_id`; the key is bound to
`ccf.workflow-definition` and the registration is audited under it. `ArtifactClass.validate` reads a document's
stated class, and such a document states none.

**What is written now.** The docstrings of `ArtifactClass` and `ReservedArtifactClassId` state R3 as not refused,
by ruling, and `public/reference/artifacts/control-plane-artifacts.md`, which had never described the `ccf.`
reservation, gains one paragraph: what is refused (a `ccf.` class id the SDK does not ship, at the manifest door,
the single-file config door and the paved road; every `ccf.` id at `declared_artifact_class`; a document stating
its own class under a `ccf.` class built directly, when it is parsed, loaded or registered), by which name
(`ReservedArtifactClassId`), and that deliberate code building an SDK-named class over its own contract is not.

**What measures it**, in `tests/controlplane/test_reserved_namespace_disclosed_residual.py`: R3 registers, as it
stands (a change that closes R3 turns this test red, and the disclosure must be revisited); each route the
paragraph says is refused is refused as `ReservedArtifactClassId` with nothing filed; and each of the three places
cites that test. The three citation checks failed before the disclosure was written. Severing the page's
paragraph reddened the page's check; a simulated closing of R3 reddened the R3 test.

## ccf.controlplane.artifact_base.ArtifactClass

- Surface: ccf.controlplane.artifact_base.ArtifactClass
- Public surface: true
- Change type: behavior
- Before: its docstring did not say what the reserved `ccf.` namespace does not stop.
- After: unchanged behavior; its docstring states R3: a class built directly under a `ccf.` id over a contract with no `class_id` field registers that contract's documents under the SDK's class name, key bound and audited, while the reservation holds on every document, manifest, config and envelope route.
- Why: `D-IMPL-378` OWED-RULINGS-3 item 3P1 (a). Measured by `tests/controlplane/test_reserved_namespace_disclosed_residual.py::test_3p1_a_r3_a_ccf_class_built_over_an_adopter_contract_stating_no_class_id_registers`.
- Migration: none. Register an SDK class with the SDK's own `ArtifactClass` constant, and give your own classes ids in your own namespace.

## ccf.controlplane.artifacts.ArtifactClass

- Surface: ccf.controlplane.artifacts.ArtifactClass
- Public surface: true
- Change type: behavior
- Before: as `ccf.controlplane.artifact_base.ArtifactClass`, which this name re-exports.
- After: the same docstring.
- Why: OWED-RULINGS-3 item 3P1 (a).
- Migration: none.

## ccf.controlplane.artifact_base.ReservedArtifactClassId

- Surface: ccf.controlplane.artifact_base.ReservedArtifactClassId
- Public surface: true
- Change type: behavior
- Before: its docstring listed where the reservation is refused and not what it leaves unrefused.
- After: unchanged behavior; its docstring states R3 as not refused, by ruling.
- Why: OWED-RULINGS-3 item 3P1 (a). Measured as for `ccf.controlplane.artifact_base.ArtifactClass`.
- Migration: none.

## ccf.controlplane.artifacts.ReservedArtifactClassId

- Surface: ccf.controlplane.artifacts.ReservedArtifactClassId
- Public surface: true
- Change type: behavior
- Before: as `ccf.controlplane.artifact_base.ReservedArtifactClassId`, which this name re-exports.
- After: the same docstring.
- Why: OWED-RULINGS-3 item 3P1 (a).
- Migration: none.
