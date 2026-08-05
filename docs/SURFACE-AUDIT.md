# Phase 15 surface audit

The phase-close answer to ROADMAP Phase 15 Success Criteria 1, 4, 5 and 6. Every
number here is **generated from an executable measurement**, not transcribed
from a plan or estimated from a diff — the tools that produced them are named
under each section so any figure can be reproduced.

| Section | Answers |
| --- | --- |
| 1 | Criterion 6 — the generated public-surface diff and its cross-check against the curated log |
| 2 | Criterion 1 — the measured before/after of the adopter-facing surface, relocation and removal separately |
| 3 | Criterion 4 — per shipped helper, "what does this hide from the replay record?" |
| 4 | The two governance items the phase surfaced, and their disposition |

---

## 1. The generated public-surface diff (Criterion 6)

**Sources.** `docs/surface/v0.2-surface-baseline.json` (frozen at phase start by
plan 15-01, byte-unchanged since — see the immutability assertion below) diffed
against the live surface via
`tools.dump_surface.diff_surfaces(baseline, build_surface())`. The tables below
are emitted from that call, not transcribed.

The live manifest `docs/surface/v0.2-surface.json` was regenerated **in place,
exactly once, by this plan**. That is the single-owner rule
(`docs/surface-changes/README.md`): 15-01 writes it at phase start, 15-21 writes
it at phase close, and the nineteen plans in between run
`tools/dump_surface.py --report` and claim their drift with a fragment. Nothing
was re-pointed here — no `SURFACE_PATH` change and no test edited to read a
different file — because the live manifest never moved. `--check` now exits 0
for the first time since 15-01, so the documented-drift gate has degenerated to
plain bytes-equality with nothing left unclaimed.

### 1.1 What moved

#### Added (52)

| Fully-qualified name | Claimed by |
| --- | --- |
| `ccf.controlplane.artifact_base.ArtifactClass` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifact_base.VersionedArtifact` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifact_base.validate_semver` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.ArtifactRole` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.DEBT_PROFILE` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.DEPLOYMENT_MANIFEST` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.DeploymentManifest` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.HALF_LIFE_TABLE` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.ManifestEntry` | `15-10-manifest.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_POLICY` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_SIMILARITY` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TEMPORAL` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TRAVERSAL` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.OperatorParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.PERSPECTIVE` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.PRODUCT_CLASS` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.PerspectiveArtifact` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.PolicyFilterParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.ProductClassDeclaration` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.RESOLUTION_SPEC` | `15-07-resolution-spec.md` |
| `ccf.controlplane.artifacts.SIGNAL_BATCH` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.SignalBatch` | `15-09-signal-perspective-productclass.md` |
| `ccf.controlplane.artifacts.SimilaritySelectParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.TemporalAsOfParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.TraversalNeighborhoodParametersArtifact` | `15-08-operator-parameters.md` |
| `ccf.controlplane.artifacts.VersionedArtifact` | `15-07-resolution-spec.md` |
| `ccf.deployment.ArtifactPin` | `15-10-manifest.md` |
| `ccf.deployment.BootedFabric` | `15-10-manifest.md` |
| `ccf.deployment.DeploymentManifest` | `15-10-manifest.md` |
| `ccf.deployment.ManifestEntry` | `15-10-manifest.md` |
| `ccf.deployment.ResolvedPins` | `15-10-manifest.md` |
| `ccf.deployment.SDK_ARTIFACT_CLASSES` | `15-06-class-lookup.md` |
| `ccf.deployment.SDK_ARTIFACT_ROLES` | `15-10-manifest.md` |
| `ccf.deployment.SimilarityCorpusAttributeError` | `15-11-operator-builder.md` |
| `ccf.deployment.UnpinnedArtifactError` | `15-10-manifest.md` |
| `ccf.deployment.build_operator_registry` | `15-11-operator-builder.md` |
| `ccf.deployment.classes.SDK_ARTIFACT_CLASSES` | `15-06-class-lookup.md` |
| `ccf.deployment.classes.SDK_ARTIFACT_ROLES` | `15-10-manifest.md` |
| `ccf.deployment.classes.refuse_role_the_sdk_fixes` | `15-10-manifest.md` |
| `ccf.deployment.classes.resolve_artifact_class` | `15-06-class-lookup.md` |
| `ccf.deployment.load_and_boot` | `15-10-manifest.md` |
| `ccf.deployment.manifest.BootedFabric` | `15-10-manifest.md` |
| `ccf.deployment.manifest.load_and_boot` | `15-10-manifest.md` |
| `ccf.deployment.operators.SimilarityCorpusAttributeError` | `15-11-operator-builder.md` |
| `ccf.deployment.operators.build_operator_registry` | `15-11-operator-builder.md` |
| `ccf.deployment.pins.ArtifactPin` | `15-10-manifest.md` |
| `ccf.deployment.pins.ResolvedPins` | `15-10-manifest.md` |
| `ccf.deployment.pins.UnpinnedArtifactError` | `15-10-manifest.md` |
| `ccf.deployment.refuse_role_the_sdk_fixes` | `15-10-manifest.md` |
| `ccf.deployment.resolve_artifact_class` | `15-06-class-lookup.md` |
| `ccf_runtime.cli.commands.schema.register` | `15-12-schema-export.md` |
| `ccf_runtime.http_api.routes.schema.build_router` | `15-12-schema-export.md` |

#### Removed (0)

*None.* This is a finding, not an omission. D-15B granted free rein on the
public API pre-1.0 and the phase used none of it in the removing direction:
every helper Phase 15 shipped is **additive**, and every path that worked at
phase start still works. Section 3's D-14 row and
`tests/deployment/test_direct_construction.py` assert that positively rather
than inferring it from an empty list.

#### Reshaped (1)

| Fully-qualified name | Claimed by |
| --- | --- |
| `ccf.assembly.worker.EntityResolutionSpec` | `15-07-resolution-spec.md` |

`semver` became a required field with no default (D-IMPL-77). It participates in
`content_hash(spec)`, so every `resolution_spec_version` pin minted after the
change differs from one minted before it. Existing Decision Replay records stay
valid against the artifact versions they name — nothing is invalidated and no
record changes shape.

#### Behavior — exempt from diff agreement (1 public)

| Fully-qualified name | Claimed by |
| --- | --- |
| `ccf.controlplane.artifacts.load_artifact` | `15-05-timestamps.md` |

D-02. `load_artifact`'s signature did not move; what it returns for a
timestamp-shaped scalar did. A generated signature diff is **structurally
incapable** of seeing this, which is the whole reason D-15 asks for a curated
log alongside the manifest rather than instead of it.

### 1.2 The cross-check, and what makes it a check

`docs/SURFACE-CHANGES.md` carries **267 entries** — 54 naming a public Python
surface, 213 naming something real that is not Python API (lint scope, tooling,
committed schemas, and artifact *document* formats).

`tests/test_surface_completeness.py` asserts six properties against that log,
reading it through `assemble_surface_changes.parse_entries()` — the same parser
that assembles the document, so "what the log says" has exactly one definition:

| # | Property | Falsification, run once and reverted |
| --- | --- | --- |
| 1 | The diff is non-empty and **both** classification partitions are non-empty | an empty diff would make every assertion below vacuously true |
| 2 | Every diff line has a matching **public** entry with an agreeing `Change type` | deleting the `ccf.deployment.load_and_boot` entry → fails naming that exact name, `NO ENTRY` |
| 3 | Every public non-`behavior` entry has a matching diff line | adding an entry for `ccf.deployment.does_not_exist` → fails naming it |
| 4 | No `Public surface: false` entry names anything in the diff | flipping `load_and_boot` to `false` → fails with `WRONG CLASSIFICATION`, **not** `NO ENTRY` |
| 5 | `ccf.controlplane.artifacts.load_artifact` carries a `behavior` entry | retyping it `reshaped` → fails naming that surface |
| 6 | The frozen baseline is byte-identical to what 15-01 committed | pinned by SHA-256 **and** by commit provenance |

Changing one entry's `Change type` from `added` to `removed` fails **both**
directions with distinct messages — `WRONG CHANGE TYPE. Found ['removed']; the
manifest shows 'added'` from the diff→log side and `claims 'removed' … but the
manifest shows it under ['added'] instead` from the log→diff side. A mismatched
direction and a misclassification are never reported as a missing entry, because
each needs a different fix.

**Assertions 2 and 4 together close the classification in both directions.**
That is why `Public surface` is a *checked field* rather than an annotation: an
executor who mislabels a real public-API change to duck assertion 3 fails
assertion 2 instead.

**The two gates are a designed pair.** `tests/test_surface_drift.py` is
module-granular and direction-blind on purpose — cheap, always-on, survivable
across fourteen parallel waves. This module is exact and runs at phase close and
thereafter. Weakening either without the other is a regression, and both
docstrings say so.

### 1.3 Baseline immutability, verified

`docs/surface/v0.2-surface-baseline.json` is byte-identical to what 15-01
committed:

```
sha256  cef0d469db249947f8392331a50bc94bf92d46a4266e4945e2b59944dac043cc
```

`git log --oneline -- docs/surface/v0.2-surface-baseline.json` shows **two**
commits, `6e6d3f5 feat(15-01)` and `c4e7ca4 fix(15-01)` — both plan 15-01's, the
second being 15-01's own in-plan correction making the manifest import-order
independent. The rule the plan text states as "exactly one commit" is written
once **by 15-01** and never again by any other plan; that is what
`test_the_frozen_baseline_was_written_only_by_plan_15_01` asserts, and it is
what holds. The bytes at `c4e7ca4` hash to the digest above.
