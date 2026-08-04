# 15-06 — class-id → `ArtifactClass` resolution

Plan 15-06 gives `ccf.deployment` its first real exports: the lookup a D-05
manifest needs to turn its `class` string into the contract that validates the
document it names.

This fragment discharges the debt 15-02 recorded explicitly. That plan created
`ccf.deployment` as an empty shell whose `__all__` was `[]`, and
`tools/dump_surface.py` skips any module with a falsy `__all__` — so the package
never entered the manifest and 15-02's entry was correctly `Public surface:
false`, with the note that *"the first export this package gains is a genuine
public-surface addition and is claimed as `Public surface: true` by whichever
plan adds it, under its own fully-qualified name."* That is this plan.

Four names appear in `tools/dump_surface.py --report`, not two: each object is
reachable both at its defining module and re-exported from the package root, and
the manifest records module-qualified names, so both spellings are real manifest
entries. All four are claimed below.

## ccf.deployment.classes.resolve_artifact_class

- Surface: ccf.deployment.classes.resolve_artifact_class
- Public surface: true
- Change type: added
- Before: absent — `ccf.controlplane.artifacts` has no registry of artifact
  classes. Its `ArtifactClass` values are module-level constants that callers
  import by name, which is the right shape for a caller who knows statically
  which class it wants and the wrong shape for a manifest, whose whole point is
  that it does not
- After: `resolve_artifact_class(class_id: str) -> ArtifactClass`, returning the
  SDK's own constant for an id the SDK owns and
  `declared_artifact_class(class_id)` for every other id
- Why: the manifest declares each artifact by `path, key, class`, where `class`
  is a string. Nothing in the tree turned that string into a contract. The
  fallthrough is the D-01 line made operational: the SDK owns the schema of what
  it ships and never invents one for what it does not, so an unrecognized id is a
  deployment-authored schema and gets the open `DeclaredArtifact` envelope — by
  design, not by failure. SDK ids resolve from the reviewed mapping *first*, so a
  manifest cannot shadow an SDK class into the permissive envelope
- Migration: none — new function. Callers who import an `ArtifactClass` constant
  by name may keep doing so; this is the additional string-keyed direction, not a
  replacement

## ccf.deployment.classes.SDK_ARTIFACT_CLASSES

- Surface: ccf.deployment.classes.SDK_ARTIFACT_CLASSES
- Public surface: true
- Change type: added
- Before: absent — there was no enumeration of the artifact classes the SDK owns
- After: `dict[str, ArtifactClass]` keyed by `class_id`, today
  `ccf.half-life-table` and `ccf.debt-profile`
- Why: exported rather than private because "which artifact classes does this SDK
  ship?" is a question an adopter writing a manifest actually asks, and answering
  it by reading source is worse than answering it by import. It is hand-written
  by name rather than scanned out of `globals()` so a new SDK class is a
  deliberate reviewed addition rather than something that appears by import
  accident, and `tests/deployment/test_class_lookup.py` holds it to the artifacts
  module so the hand-maintenance cannot silently fall behind
- Migration: none — new constant. Treat it as read-only; mutating it changes
  resolution globally for the process

## ccf.deployment.resolve_artifact_class

- Surface: ccf.deployment.resolve_artifact_class
- Public surface: true
- Change type: added
- Before: absent — `ccf.deployment.__all__` was `[]` and the package exported
  nothing at all
- After: re-exported from the package root, so the adopter-facing import is
  `from ccf.deployment import resolve_artifact_class`
- Why: the package root is the adopter's entry point to the wiring surface; a
  helper reachable only at its defining module makes the submodule layout part of
  the public contract
- Migration: none

## ccf.deployment.SDK_ARTIFACT_CLASSES

- Surface: ccf.deployment.SDK_ARTIFACT_CLASSES
- Public surface: true
- Change type: added
- Before: absent — the package exported nothing
- After: re-exported from the package root alongside `resolve_artifact_class`
- Why: same reason as the function — the two are read together, and splitting
  them across import paths would be an arbitrary seam
- Migration: none

## Manifest ownership

This plan did **not** regenerate `docs/surface/v0.2-surface.json` and did not
touch `docs/surface/v0.2-surface-baseline.json`, per the single-owner rule in
this directory's README: 15-01 writes the live manifest at phase start, 15-21 at
phase close, and eleven concurrent worktrees each regenerating a whole-tree file
would each pass `--check` pre-merge and leave the tree stale after the second
merge. `tools/dump_surface.py --report` was run instead and reports exactly the
four names claimed above, zero removed and zero reshaped;
`tests/deployment/test_class_lookup.py::test_this_plans_fragment_claims_exactly_what_it_added`
asserts that correspondence in both directions at this plan's own wave rather
than deferring it to 15-21.
