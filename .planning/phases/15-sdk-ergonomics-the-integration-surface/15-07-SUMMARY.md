---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 07
subsystem: controlplane
status: paused-at-checkpoint
tags: [artifacts, resolution-spec, semver, import-cycle, D-IMPL-77]
requires: ["15-05", "15-06"]
provides:
  - "ccf.controlplane.artifact_base (VersionedArtifact, ArtifactClass, validate_semver)"
  - "ccf.controlplane.artifacts.RESOLUTION_SPEC"
  - "EntityResolutionSpec as a versioned artifact reachable through parse_artifact"
  - "tests/controlplane/test_artifact_roundtrip.py — the general round-trip module 15-08/15-09 extend"
affects: ["15-08", "15-09", "15-10", "15-12", "15-21"]
key-files:
  created:
    - src/ccf/controlplane/artifact_base.py
    - tests/controlplane/test_artifact_roundtrip.py
    - docs/surface-changes/15-07-resolution-spec.md
  modified:
    - src/ccf/controlplane/artifacts.py
    - src/ccf/controlplane/registry.py
    - src/ccf/assembly/worker.py
    - src/ccf/deployment/classes.py
    - src/ccf/peering/admission.py
    - src/ccf/peering/trust_policy.py
    - src/ccf/hitl/transport.py
    - src/ccf/workflow/definitions.py
    - src/ccf/agents/definitions.py
    - src/ccf/skills/grants.py
    - src/ccf/skills/catalog.py
    - runtime/ccf_runtime/authz/artifact.py
    - tests/deployment/test_class_lookup.py
    - tests/agents/test_consumption_discipline.py
    - perf/conftest.py
    - "10 example run.py/serve.py modules + 5 test fixture modules (semver wiring)"
decisions: [D-IMPL-77]
---

# Phase 15 Plan 07: Resolution Spec as a First-Class Artifact Class — Summary

`EntityResolutionSpec` now carries its own semver lane and reaches adopters through
the same `parse_artifact` seam that already serves λ_c tables and debt profiles,
with the versioned-artifact primitives relocated to a cycle-free module.

**Status: PAUSED at Task 3, a `checkpoint:human-verify` gate.** Tasks 1, 2 and 4 are
complete and committed. Task 4 was executed *before* the checkpoint deliberately —
see "Deviations".

## The A1 ruling — root versioning (binding on 15-08, 15-09, 15-10)

**Ruling: neither. The root `schema_version` / `artifact_version` pair is file-level
decoration that never reaches `parse_artifact` at all. The artifact document is a
nested mapping.**

15-03's carry-forward posed this as a two-way choice — the class declares the two-field
root versioning, or the loader strips it. Both options are wrong, and they look
plausible only because the A1 spike passed the **whole ontology file** to
`model_validate`. That is not how any artifact class in this codebase is loaded.

The decisive evidence is the already-shipped precedent, `ccf.half-life-table`:

- `examples/00-quickstart/artifacts/halflife.yaml` carries root `schema_version` and
  `artifact_version`, **and** a nested `half_life_table:` mapping that carries its own
  `semver`.
- `examples/00-quickstart/run.py:208` calls
  `parse_artifact(halflife["half_life_table"], HALF_LIFE_TABLE)` — the *nested* mapping.
  The root keys are never handed to the contract, so `extra=forbid` never sees them.

So `ccf.resolution-spec` follows that precedent exactly and needs no new mechanism.
The consequences the three downstream plans inherit:

1. **Do not add `schema_version` / `artifact_version` fields to any artifact class in
   this closed world.** The single `semver` lane from `VersionedArtifact` is the whole
   versioning story for SDK artifact classes. The two-field D-IMPL-28 lane belongs to
   agent/prompt definition artifacts and stays on `_TwoLaneVersioned`, a separate base.
2. **Do not add a stripping step to the loader.** Stripping would make the closed-world
   guarantee conditional and would silently accept a document whose author put a
   *misspelled* key at the root.
3. **A file is not an artifact.** When an example YAML holds more than one artifact —
   as `halflife.yaml` holds both the table and the debt profile — each artifact is a
   nested mapping under its own key, and the root holds only decoration and
   deployment-level values like `tenant_id`. The rewrite plans that restructure
   `ontology.yaml` should introduce a nested `resolution_spec:` key holding `semver`
   plus the two rule lists, leaving `tenant_id` and the two D-03 operator maps at the
   root as sibling, non-artifact content.

This ruling was mine to make, not Dave's: it is not a design choice but a reading of an
existing, shipped, tested precedent. No `D-IMPL-NN` was raised.

## The `__all__` carry-forward from 15-06 — accepted

`HALF_LIFE_TABLE` and `DEBT_PROFILE` are now in `ccf.controlplane.artifacts.__all__`,
alongside the new `RESOLUTION_SPEC`. Adding the new constant while leaving its two
siblings out would have left the module's declared surface incoherent. All three are
claimed in the surface fragment under their fully-qualified dotted names.

15-06's anti-drift test still scans public module *attributes* rather than `__all__`.
That is deliberate and its docstring now says why: the attribute scan is a **superset**
of the `__all__` names, so it still catches a constant that is declared but never
exported — drift an `__all__`-only scan would now wave through.

## What was built

### Task 1 — `artifact_base.py`, and the cycle that was wider than the plan predicted

`src/ccf/controlplane/artifact_base.py` holds `validate_semver`, the now-public
`VersionedArtifact`, and `ArtifactClass`. It imports nothing from `ccf` except
`ccf.contracts.base`, and its module docstring states that constraint as the property
it exists to hold.

`ccf.controlplane.artifacts` re-exports all three and keeps `_VersionedArtifact` as a
module-level alias, so no existing import path or subclass needed editing.

**The plan predicted one cycle edge; there were two.** Re-pointing `registry.py` alone
was not sufficient. The actual closure was:

```
artifacts -> assembly.worker -> peering.admission -> peering.trust_policy -> artifacts
```

Both `admission.py` and `trust_policy.py` import exactly the two relocated primitives.
Rather than patch them one at a time as each new `ImportError` surfaced, every module
importing *only* `ArtifactClass` and `validate_semver` was re-pointed at `artifact_base`
— seven modules in total. This is behavior-identical (same objects, re-exported), and it
removes the latent hazard rather than the one instance of it.

`EntityResolutionSpec` now inherits `VersionedArtifact`. `boot()` is byte-identical
(`git diff src/ccf/boot.py` is empty), which is the point of D-IMPL-77's rejection of a
wrapper.

`RESOLUTION_SPEC` is registered in `SDK_ARTIFACT_CLASSES`;
`resolve_artifact_class("ccf.resolution-spec").contract is EntityResolutionSpec`.

**No custom validator was needed**, exactly as 15-03's A1 spike predicted. Pydantic
coerces the YAML lists and nested mappings to `tuple[EntityResolutionRule, ...]` and
`tuple[RelationshipResolutionRule, ...]` unaided.

### Task 2 — `tests/controlplane/test_artifact_roundtrip.py`

13 tests, parametrized over a module-level `CASES` list of
`(ArtifactClass, document, unknown_keys)` triples, covering all three SDK artifact
classes. Four guarantees per class — round-trip identity, content-hash stability across
independent parses, closed-world refusal, and refusal of a document stating no `semver`
— plus a vacuity guard asserting every id in `SDK_ARTIFACT_CLASSES` has a case.

The resolution-spec case injects the three D-03 key names verbatim (`tenant_id`,
`classification_attribute_by_class`, `similarity_corpus_attribute_by_class`), one at a
time, so a refusal is attributed to a specific key.

15-08 and 15-09 extend this by appending a `_Case`; the vacuity guard fails if they
don't.

### Task 4 — the surface fragment

`docs/surface-changes/15-07-resolution-spec.md`, eight entries, seven fields each.
`tools/dump_surface.py --report` shows `added (11)` / `removed (0)` / `reshaped (1)`;
seven of the eleven are this plan's and four are 15-06's, already claimed in its own
fragment. `ccf.controlplane.artifacts.ArtifactClass` does **not** appear under
`removed`, confirming the re-export holds.

`docs/surface/v0.2-surface.json` and the frozen baseline were not touched, and
`tests/deployment/test_class_lookup.py::test_this_plan_left_the_surface_manifests_alone`
passes.

## Deviations from Plan

**1. [Rule 3 — Blocking] The import cycle had a second edge the plan did not name.**
- Found during: Task 1, at the first cold-interpreter import check.
- Issue: `artifacts -> worker -> peering.admission -> peering.trust_policy -> artifacts`
  closes independently of the `registry` edge the plan documented.
- Fix: re-pointed all seven modules importing only the two relocated primitives at
  `artifact_base`, rather than patching each `ImportError` as it appeared.
- Commit: `6feba11`

**2. [Rule 3 — Blocking] 15-06's fragment-claims test could not survive a later wave.**
- Found during: Task 4.
- Issue: `test_this_plans_fragment_claims_exactly_what_it_added` scanned *only*
  `15-06-class-lookup.md` but compared against the manifest's *accumulated* `added` set.
  The manifest is frozen between 15-01 and 15-21, so that set grows with every merged
  plan — meaning 15-06's test went red the moment 15-07 added a name, a permanent false
  red saying nothing about either plan. 15-08, 15-09 and 15-10 would each have hit it.
- Fix: the scan now globs every fragment. Both assertion directions survive:
  `added <= claimed` still catches an entry a plan forgot to write (no other fragment
  claims a name its author never recorded), and `claimed <= added` still catches a
  fragment claiming a name the tree does not export. Renamed to
  `test_the_phases_fragments_claim_exactly_what_was_added`.
- Commit: `8b8dacb`

**3. [Rule 3 — Blocking] Two blast-radius sites outside the plan's file list.**
- `perf/conftest.py` built a spec with no lane; it now reads `artifact_version` from the
  perf battery's own ontology artifact, matching every example.
- `tests/agents/test_consumption_discipline.py`'s allow-list named
  `ccf.controlplane.artifacts` but not `artifact_base`. Admitting it **narrows** the
  consumption surface rather than widening it: `artifact_base` imports nothing from `ccf`
  except `ccf.contracts.base`, so it is strictly more constrained than the entry above it
  and reaches no fabric layer. The rationale is recorded inline at the allow-list entry.
- Commit: `90030c6`

**4. [Sequencing] Task 4 was executed before the Task 3 checkpoint.**
Task 3's own `how-to-verify` instructs the reviewer to run `make ci` and confirm green.
That is impossible while Task 4 is outstanding: 15-06's fragment-claims test fails until
this plan's fragment exists. Presenting Dave a checkpoint with a known-red suite would
have made the review unable to distinguish churn from defect — the exact confusion
D-IMPL-77 isolated this plan to prevent. Tasks 1, 2 and 4 are therefore all committed,
and the tree is green, before the gate.

**5. [Blast radius, expected] 16 further modules gained a `semver` argument.**
Ten example modules and five test-fixture modules construct an `EntityResolutionSpec`
and now state a lane. Examples read it from their own artifact
(`ontology["artifact_version"]`, or `federation["artifact_version"]` for
`04-cross-process/run.py`'s federation-derived spec) rather than inlining a literal, per
CLAUDE.md §6.4. Test fixtures use `semver="1.0.0"`, the established fixture convention.

## The regeneration finding — the substance of the Task 3 checkpoint

**Zero committed expected outputs required regeneration.** `make ci` exits 0 with no
file rewritten, and `git status` is clean after a full run.

The reason is structural rather than lucky: **every `resolution_spec_version` pin in the
tree is a runtime-computed variable, never a committed literal.** All 14 call sites pass
a `spec_version` obtained from `registry.register(...)`, which derives it from
`content_hash`. No golden file, fixture, or expected-output block anywhere in `examples/`,
`tests/` or `perf/` pins a resolution-spec hash as a literal string.

So the churn D-IMPL-77 anticipated is entirely real *semantically* — a re-registration of
identical resolution rules now mints a different pin than it did before this commit — but
it has no committed-file footprint. Nothing was regenerated because there was nothing to
regenerate. That is the claim the checkpoint asks Dave to confirm.

No replay record changed shape; only the values pins would take at runtime.

## Threat Flags

None. No new network endpoint, auth path, file access pattern, or trust-boundary schema
change. `T-15-07-05` (import-cycle DoS) is mitigated more strongly than planned — the
real closure had two edges and both are broken, verified by five separate cold-interpreter
import checks.

## Verification

- `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/controlplane/ tests/deployment/ tests/assembly/ -q` — pass
- `make typecheck` — `Success: no issues found in 164 source files`
- `make lint` — clean (No-Hardcoding lint now covers the new test module, per 15-04)
- `make ci-core` — `1628 passed, 2 skipped`
- `make ci` — exit 0, all example legs green, mkdocs `--strict` build clean
- Five cold-interpreter imports, each as the first `ccf` import in a fresh process:
  `ccf.controlplane.artifacts`, `ccf.assembly.worker`, `ccf.controlplane.registry`,
  `ccf.deployment.classes`, `ccf.controlplane.artifact_base` — all OK
- `git diff src/ccf/boot.py` — empty
- `grep -c "controlplane.artifacts" src/ccf/controlplane/registry.py` — 0
- `docs/surface/v0.2-surface.json` and `v0.2-surface-baseline.json` — untouched

## Commits

| Commit | Task | Subject |
|---|---|---|
| `6feba11` | 1 | make the resolution spec a versioned artifact class |
| `df80768` | 2 | round-trip and closed-world guarantees for SDK artifact classes |
| `8b8dacb` | 4 | record the resolution-spec surface changes |
| `90030c6` | 1/3 | absorb the semver blast radius in perf and the agents allow-list |

## Self-Check: PASSED

All three created files exist on disk; all four commit hashes resolve in `git log`.
