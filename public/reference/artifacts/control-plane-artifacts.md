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
everything under `declaration:` is the deployment's own:

```yaml
--8<-- "archive/examples/00-quickstart/artifacts/policy-bundle.yaml"
```
