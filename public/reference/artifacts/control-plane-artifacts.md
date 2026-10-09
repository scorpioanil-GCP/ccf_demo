# Control Plane artifacts

The Control Plane says what the fabric is allowed to do, and it is also the audit plane. Every
artifact reaches it wrapped in a declared envelope carrying its own version lane, so replay can
resolve an exact version rather than "latest". Two calibration artifacts matter most to the
Data and Context Layer: the half-life table, which sets the decay rate per observation type,
and the debt profile, which sets the thresholds at which context shortfall forces an LLM path
or fails closed. The SDK supplies the formulas and refuses to supply the numbers — an
observation type with no declared half-life raises rather than decaying at a rate nobody chose.

::: ccf.controlplane.artifacts.DeclaredArtifact

::: ccf.controlplane.artifacts.HalfLifeTable

::: ccf.controlplane.artifacts.HalfLifeEntry

::: ccf.controlplane.artifacts.DebtProfile

## Worked examples

Each artifact class is its own document. A file is not an artifact: the two
calibrations below are separate classes with separate version lanes, so they
are separate documents, each validated closed-world against its own contract.

The half-life table:

```yaml
--8<-- "archive/examples/00-quickstart/artifacts/half-life-table.yaml"
```

The debt profile:

```yaml
--8<-- "archive/examples/00-quickstart/artifacts/debt-profile.yaml"
```

And a class the SDK does *not* own, carried in the open `DeclaredArtifact`
envelope. The SDK fixes `semver`, `class_id` and canonical serializability;
everything under `declaration:` is the deployment's own. The document's
`class_id` must name the class it is parsed or registered as — the class its
manifest entry names — or it is refused with
`ccf.controlplane.artifacts.ArtifactClassIdMismatch` before anything is
registered (`D-IMPL-378`):

```yaml
--8<-- "archive/examples/00-quickstart/artifacts/policy-bundle.yaml"
```

The `ccf.` class ids are the SDK's (`D-IMPL-84`), and no document, manifest
entry, config section or envelope files adopter content under one. The
manifest door, the single-file config door and the paved road refuse a `ccf.`
class id the SDK does not ship; `ccf.controlplane.artifacts.declared_artifact_class`
refuses every `ccf.` id; and a class built directly under a `ccf.` id refuses a
document that states its own class (the `DeclaredArtifact` envelope, or any
contract with a `class_id` field) when it is parsed, loaded or registered.
Each is refused as `ccf.controlplane.artifact_base.ReservedArtifactClassId`
before anything is registered or audited. Code is not refused: a program that
writes its own contract with no `class_id` field and builds
`ArtifactClass(class_id="ccf.<name>", contract=<that contract>)` over it
registers that contract's documents under the SDK's class name, with the key
bound to that id and the registration audited (`D-IMPL-378` OWED-RULINGS-3
item 3P1 (a): disclosed, not refused; measured by
`tests/controlplane/test_reserved_namespace_disclosed_residual.py::test_3p1_a_r3_a_ccf_class_built_over_an_adopter_contract_stating_no_class_id_registers`).
Register an SDK class with the SDK's own `ArtifactClass` constant, and give
your own classes ids in your own namespace.
