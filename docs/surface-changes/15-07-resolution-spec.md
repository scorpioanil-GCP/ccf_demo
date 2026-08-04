# 15-07 — the resolution spec as a first-class artifact class

Plan 15-07 makes `EntityResolutionSpec` a versioned Control Plane artifact
reachable through the same `parse_artifact` seam that already serves λ_c tables
and debt profiles (D-IMPL-77), and absorbs the content-hash churn that follows
as one reviewed event.

Eight names change. Three are the versioned-artifact primitives relocating to a
module that breaks an import cycle; three are `ArtifactClass` constants entering
`ccf.controlplane.artifacts.__all__`; one is the re-export that keeps the
relocation invisible to existing callers; and one is the reshape that carries
the blast radius. All eight are claimed below.

`ccf.controlplane.artifacts.ArtifactClass` does **not** appear under `removed`
in `tools/dump_surface.py --report`: the re-export keeps it in that module's
`__all__`, so every existing import path still resolves.

## ccf.controlplane.artifact_base.VersionedArtifact

- Surface: ccf.controlplane.artifact_base.VersionedArtifact
- Public surface: true
- Change type: added
- Before: absent — the base existed as `ccf.controlplane.artifacts._VersionedArtifact`,
  module-private, with no module of its own
- After: a public `CCFContract` subclass declaring the single `semver` lane,
  validated through `validate_semver`, with no default
- Why: two reasons, and both are structural. **It had to move**, because
  D-IMPL-77 requires `EntityResolutionSpec` gain `semver` *in place*, so
  `ccf.controlplane.artifacts` must name a class from `ccf.assembly.worker` to
  declare `RESOLUTION_SPEC` — and `worker` reaches `ccf.controlplane.registry`,
  which needs `ArtifactClass`. Leaving these primitives in `artifacts` closed
  `artifacts -> worker -> registry -> artifacts` at **import** time, taking the
  package down rather than tripping a lint. The real closure proved wider than
  the registry edge alone: `worker -> peering.admission -> peering.trust_policy
  -> artifacts` closes it too, so every module importing only the relocated
  primitives now takes them from `artifact_base`. **It had to become public**,
  because L2's `EntityResolutionSpec` now inherits it, and an L2 contract
  inheriting a module-private Control Plane type is a relocation hazard the next
  refactor trips over
- Migration: none — `ccf.controlplane.artifacts` re-exports it, and
  `_VersionedArtifact` survives there as a module-level alias

## ccf.controlplane.artifact_base.ArtifactClass

- Surface: ccf.controlplane.artifact_base.ArtifactClass
- Public surface: true
- Change type: added
- Before: absent at this path — defined in `ccf.controlplane.artifacts`
- After: the same frozen dataclass (`class_id`, `contract`, `validate`),
  unchanged in behavior, defined here
- Why: it is the name `ccf.controlplane.registry` needed, and the one whose
  location closed the cycle. `artifact_base` imports nothing from `ccf` except
  `ccf.contracts.base`, and its module docstring states that constraint as the
  property it exists to hold — a future import into it would re-close the cycle
  silently
- Migration: none — `ccf.controlplane.artifacts.ArtifactClass` still resolves

## ccf.controlplane.artifact_base.validate_semver

- Surface: ccf.controlplane.artifact_base.validate_semver
- Public surface: true
- Change type: added
- Before: absent at this path — defined in `ccf.controlplane.artifacts`
- After: the same function and the same regex, defined here
- Why: it travels with the base that calls it. The semver grammar has exactly
  one home (E7); re-declaring the regex in a second module so the base could
  move would be the defect this relocation exists to avoid
- Migration: none — `ccf.controlplane.artifacts.validate_semver` still resolves

## ccf.controlplane.artifacts.VersionedArtifact

- Surface: ccf.controlplane.artifacts.VersionedArtifact
- Public surface: true
- Change type: added
- Before: absent from `__all__` — the module exposed only the private
  `_VersionedArtifact`
- After: re-exported from `ccf.controlplane.artifact_base` and listed in
  `__all__`
- Why: the re-export is what makes the relocation a non-event for adopters. The
  module's public surface does not shrink, and a caller who reached for the base
  through this module keeps working
- Migration: none

## ccf.controlplane.artifacts.RESOLUTION_SPEC

- Surface: ccf.controlplane.artifacts.RESOLUTION_SPEC
- Public surface: true
- Change type: added
- Before: absent — there was no artifact class for the L2 resolution
  vocabulary, so a deployment's ontology document could not reach
  `parse_artifact` at all
- After: `ArtifactClass(class_id="ccf.resolution-spec", contract=EntityResolutionSpec)`,
  also registered in `ccf.deployment.classes.SDK_ARTIFACT_CLASSES` so a D-05
  manifest can name it
- Why: this is the phase's highest-duplication target. The spec's field names
  already match the ontology YAML keys exactly, so the ~20-line hand-marshaller
  repeated across nine files was pure wiring — three things blocked its removal
  (no `semver`, the operator-facing attribute maps riding in the same document
  per D-03, and no registered class) and this plan removes all three. Closed-world
  validation comes free: `CCFContract` is frozen and `extra=forbid`, so an
  unknown key fails at parse with no new machinery
- Migration: deployments hand-marshalling an ontology document into an
  `EntityResolutionSpec` replace that code with
  `parse_artifact(document, RESOLUTION_SPEC)`. Note the document handed to
  `parse_artifact` is the **resolution-spec mapping**, not the whole ontology
  file: root-level `schema_version` / `artifact_version` keys are file-level
  decoration and are refused by the closed-world contract, exactly as they
  already are for `ccf.half-life-table`, whose document is the nested
  `half_life_table:` mapping

## ccf.controlplane.artifacts.HALF_LIFE_TABLE

- Surface: ccf.controlplane.artifacts.HALF_LIFE_TABLE
- Public surface: true
- Change type: added
- Before: defined as a module-level constant but absent from `__all__`
- After: listed in `__all__`
- Why: the constant was always importable and always intended as public — the
  omission was an oversight, and a measurable one. 15-06's anti-drift test had
  to scan public module *attributes* rather than `__all__` precisely because an
  `__all__`-only scan would have found zero `ArtifactClass` instances and passed
  while proving nothing. This plan owns `artifacts.py`, so it is the plan that
  can fix it
- Migration: none — the import path is unchanged; `from ccf.controlplane.artifacts
  import *` now yields it

## ccf.controlplane.artifacts.DEBT_PROFILE

- Surface: ccf.controlplane.artifacts.DEBT_PROFILE
- Public surface: true
- Change type: added
- Before: defined as a module-level constant but absent from `__all__`
- After: listed in `__all__`
- Why: same omission and same fix as `HALF_LIFE_TABLE` — with `RESOLUTION_SPEC`
  being added to `__all__` in this plan, leaving its two siblings out would have
  left the module's declared surface incoherent
- Migration: none — the import path is unchanged

## ccf.assembly.worker.EntityResolutionSpec

- Surface: ccf.assembly.worker.EntityResolutionSpec
- Public surface: true
- Change type: reshaped
- Before: a `CCFContract` with `entity_rules` and `relationship_rules` and no
  version field of any kind
- After: inherits `ccf.controlplane.artifact_base.VersionedArtifact`; `semver`
  is required and has **no default**
- Why: D-IMPL-77. The class's own docstring already called it "a Control Plane
  artifact, versioned like any other" — the field's absence made that sentence
  aspirational, and was one of exactly three things keeping the spec away from
  the `parse_artifact` seam. A **wrapper** holding `semver` beside the spec was
  rejected: `ccf.boot.boot` would then receive a wrapper where it expects a
  spec, changing `boot()`'s signature — the one contract D-05 committed to
  preserving. The wrapper trades a data change for a contract change, which is
  the more expensive of the two. No default, because a default lane is a version
  nobody chose and the registry's D-05 bump check would then compare content
  hashes against a lane the author never asserted
- Migration: **the content hash changes.** `semver` participates in
  `content_hash(spec)`, so every `resolution_spec_version` pin minted after this
  change differs from one minted before it, and every Decision Replay record
  carrying such a pin is pinned to a new value. Existing replay records remain
  valid against the artifact versions they name — nothing is invalidated and no
  record changes shape — but a re-registration of the *same* resolution rules
  now produces a different pin than it did before. Constructing an
  `EntityResolutionSpec` without `semver` is now a validation error: state the
  lane, and prefer reading it from the artifact rather than inlining one
  (CLAUDE.md §6.4)
