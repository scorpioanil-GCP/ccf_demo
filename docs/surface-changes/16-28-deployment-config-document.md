# 16-28 — `DeploymentConfig`, the single-file authoring document (parse layer)

## What did **not** change, stated first

- `DeploymentManifest`, `ManifestEntry` and `load_and_boot` are untouched.
  Both are byte-identical to BASE (`inspect.getsource` character counts:
  `DeploymentManifest` 10561, `ManifestEntry` 7336, unchanged), and
  `src/ccf/deployment/manifest.py` carries no diff against BASE at all.
- `role` and `registration` remain required with no default on
  `ManifestEntry`, exactly as `D-IMPL-80` and `D-IMPL-85` specify. This
  plan narrows nothing about that pair — the narrowing for `ccf.*` classes
  is `D-IMPL-134`'s ruling and `16-29`'s loader, not this contract.
- The multi-file form is unaffected and, per Dave's dual-model ruling of
  2026-08-14 (and its 2026-08-15 amendment, `D-IMPL-136`), stays supported
  indefinitely. No conversion sweep is planned or performed here; HW-1
  (`examples/s1-00-companies-over-revenue`) is read-only reference material
  for this plan and is not edited.
- `resolve_artifact_class`, `SDK_ARTIFACT_ROLES` and
  `SDK_VERSIONED_ARTIFACT_CLASSES` are unchanged in shape — `DEPLOYMENT_CONFIG`
  joins `SDK_ARTIFACT_CLASSES` only, per `git diff --stat` on
  `src/ccf/deployment/classes.py` showing a single mapping-entry addition
  (plus its one import).
- `docs/surface/` is untouched — this fragment is reconciled against
  `tools/dump_surface.py --report`'s **live** measurement, per the
  single-owner rule (`docs/surface-changes/README.md`: only `15-01` and
  `15-21` write the committed manifests).

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: added
- Before: did not exist
- After: `VersionedArtifact` subclass — fifteen fields: the inherited
  `semver` (no default); the six deployment-level fields mirroring
  `DeploymentManifest`'s fields of the same name (`tenant_id`, `backend`,
  `backend_secrets`, `survivor_cap`, `resolution_spec_key`,
  `policy_bundle_key`); and the eight reserved sections (`product_class`
  required; `operators`, `request_contract`, `resolution`, `half_life`,
  `debt_profile`, `policy`, `default_perspective` optional, defaulting to
  `None`). A `model_validator(mode="before")` refuses every unreserved
  top-level key by name, listing every reserved name, built from
  `cls.model_fields` rather than a second hand-maintained list
- Why: `D-IMPL-136` (Dave, 2026-08-14) — the single-file `ccf_config.yaml`
  authoring form. This is the document half only: parsing, closed-world
  refusal, and holding adopter-owned section bodies uninterpreted.
  Deriving each section into the SDK artifact it names, registering, and
  booting are `16-29`'s and `16-30`'s scope, not this class's
- Migration: none. New surface; the multi-file `DeploymentManifest` form is
  unaffected and stays supported indefinitely (`D-IMPL-136`)

## ccf.controlplane.artifacts.DEPLOYMENT_CONFIG

- Surface: ccf.controlplane.artifacts.DEPLOYMENT_CONFIG
- Public surface: true
- Change type: added
- Before: did not exist
- After: `ArtifactClass(class_id="ccf.deployment-config", contract=DeploymentConfig)`,
  registered in `src/ccf/deployment/classes.py::SDK_ARTIFACT_CLASSES` so
  `resolve_artifact_class("ccf.deployment-config")` returns this constant
  by identity, and enumerated by `tools/dump_schemas.py` into the committed
  `docs/schemas/ccf.deployment-config.json` (fifteen properties,
  `additionalProperties: false`)
- Why: `D-IMPL-136` — the class identity a manifest, `resolve_artifact_class`,
  and the schema exporter all address by the same `class_id`, exactly as
  every other SDK artifact class is
- Migration: none. New surface

## The unregistered-then-registered sequence, for the record

`tests/deployment/test_class_lookup.py::test_every_exported_artifact_class_is_manifest_addressable`
failed the moment `DeploymentConfig`/`DEPLOYMENT_CONFIG` existed and before
`DEPLOYMENT_CONFIG.class_id` joined `SDK_ARTIFACT_CLASSES` — *"ccf.controlplane.artifacts
exports ArtifactClass constants that no manifest can address: {'DEPLOYMENT_CONFIG':
'ccf.deployment-config'} ... add it to ccf/deployment/classes.py"* — and passed
immediately once the one mapping entry was added. That is the anti-drift
mechanism `D-IMPL-136` inherits from `15-06` working as designed, not a
defect this plan fixed around.
