# 16-29 — `derive_deployment`, the single-file derivation and its five refusals

## What did **not** change

- `ManifestEntry`'s five fields are the same five, all still required with
  no default — `path`, `key`, `class_id`, `role`, `registration`. This plan
  narrows nothing about `role`/`registration`'s no-default posture on the
  contract itself; `D-IMPL-134`'s narrowing is expressed entirely in the
  new loader, never by relaxing the field.
- `DeploymentManifest`'s three `model_validator(mode="after")` methods
  (`_secret_fields_are_unique`, `_keys_are_unique`,
  `_boot_pins_name_registered_entries`) are unchanged. `derive_deployment`
  constructs a `DeploymentManifest` exactly as the multi-file loader does
  and is held to the same three validators — `_keys_are_unique` is what R4
  delegates to rather than re-implementing.
- `load_and_boot` is unchanged. `git diff --stat $BASE..HEAD --
  src/ccf/deployment/manifest.py` is empty — an acceptance criterion, not
  an incidental fact — because `16-30` reuses that entry point unmodified
  over a derived manifest.
- `refuse_role_the_sdk_fixes` and `refuse_registration_the_sdk_fixes` are
  unchanged and are **called** by the new derivation on every entry,
  derived value and override alike — the same class-wide posture
  `load_and_boot` already holds every authored entry to, never bypassed.
- `src/ccf/deployment/binder.py::refuse_operator_set_divergence` is
  unchanged. R2 is a **parse-time** refusal over one document's own two
  fields (`product_class.required_operator_keys` against `operators:`),
  not a call into the binder, which compares a different pair of documents
  at a different moment (projection-plan-build time). `git diff --stat
  $BASE..HEAD -- src/ccf/deployment/binder.py` is empty.
- The multi-file form stays supported indefinitely under Dave's dual-model
  ruling of 2026-08-14 (`D-IMPL-136`, amended 2026-08-15). No conversion
  sweep is planned or performed here; HW-1
  (`examples/s1-00-companies-over-revenue`) is read-only reference
  material and is not edited — `git diff --stat $BASE..HEAD -- examples/`
  is empty.
- No artifact class is added by this plan (`derive_deployment` produces
  `DeploymentManifest` instances and plain-mapping documents, never a new
  contract), so no schema moves: `git diff --stat $BASE..HEAD --
  docs/schemas/` is empty.

## ccf.deployment.config.derive_deployment

- Surface: ccf.deployment.config.derive_deployment
- Public surface: true
- Change type: added
- Before: did not exist
- After: `derive_deployment(config: DeploymentConfig, config_filename: str =
  "ccf_config.yaml") -> DerivedDeployment`. A pure function: turns one parsed
  `DeploymentConfig` into a `DeploymentManifest` plus one materialised
  document per section, applying design spec §6's derivation table and the
  five refusals design spec §6.1, §11.1 and §11.2 demand. Reads no file,
  reads no environment variable, and produces equal results across two calls
  on an equal input
- Why: `D-IMPL-134` (the narrowing) and `D-IMPL-136` (the single-file form)
  — the loader that turns `ccf_config.yaml`'s sections into the same typed
  contracts the multi-file form authors by hand. `16-30` is what registers
  and boots from this function's output; this function derives only
- Migration: none. New surface; every existing multi-file deployment keeps
  working unchanged

## ccf.deployment.config.DerivedDeployment

- Surface: ccf.deployment.config.DerivedDeployment
- Public surface: true
- Change type: added
- Before: did not exist
- After: a frozen `dataclass` — not a `CCFContract` — carrying `manifest:
  DeploymentManifest` and `documents: Mapping[str, Mapping[str, Any]]`.
  Not a `CCFContract` for the reason `BootedFabric` gives for itself: it is
  a derivation result handed to a caller, not a content-hashable artifact —
  the `manifest` field is the content-hashable thing
- Why: the return type `derive_deployment` needs — a manifest plus its
  documents, in one value, with no artifact class of its own to invent
- Migration: none. New surface

## ccf.deployment.derive_deployment

- Surface: ccf.deployment.derive_deployment
- Public surface: true
- Change type: added
- Before: did not exist
- After: re-export of `ccf.deployment.config.derive_deployment` from
  `ccf.deployment.__init__`'s `__all__`, exactly as every other
  `ccf.deployment.*` submodule's public names are re-exported at the
  package
- Why: package-level ergonomics — an adopter imports `from ccf.deployment
  import derive_deployment` alongside `load_and_boot`, `build_operator_registry`
  and the rest of the wiring surface, rather than reaching into the
  submodule
- Migration: none. New surface

## ccf.deployment.DerivedDeployment

- Surface: ccf.deployment.DerivedDeployment
- Public surface: true
- Change type: added
- Before: did not exist
- After: re-export of `ccf.deployment.config.DerivedDeployment`, same
  reasoning as the function's re-export above
- Why: same as `ccf.deployment.derive_deployment`
- Migration: none. New surface

## The one collision the shipped SDK classes hit, for the record

Design spec §6.2 names the general hazard the override syntax runs: a
section whose own schema legitimately declares a field named `role`,
`key`, `class_id` or `registration` cannot express both meanings under one
shared YAML key. Measured against every class this loader materialises at
the document's top level, exactly one hits it —
`~ccf.projection.plan.Perspective`'s own `role` (the Π role-conditioning
value, e.g. `analyst`), which collides with `ManifestEntry.role`
(`register`/`load`) on the `default_perspective` section design spec
§8.1's own worked example uses. Left unresolved, that worked example could
not be authored at all: `'analyst'` is not a valid `ManifestEntry.role`,
and no single-file `default_perspective` section could supply
`Perspective.role` while letting `ManifestEntry.role` derive silently.
`derive_deployment` resolves this with a targeted, measured precedence
rule rather than a hardcoded exception: a reserved name the *target
class's own contract* already declares is content, not bookkeeping, so
content wins and the bookkeeping field falls back to its silent
derivation. This is not a new public surface — no name, type or signature
changes — and is recorded here because it is a substantive behaviour a
reader of the derivation table alone would not predict.
