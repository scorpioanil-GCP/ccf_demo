---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 08
subsystem: controlplane
tags: [artifacts, operator-parameters, D-01, D-IMPL-76, ERGO-08]
requires:
  - ccf.controlplane.artifact_base.VersionedArtifact (15-07)
  - ccf.deployment.classes.SDK_ARTIFACT_CLASSES (15-06)
  - ccf.operators.params.*Parameters
provides:
  - ccf.controlplane.artifacts.OperatorParametersArtifact
  - ccf.controlplane.artifacts.TraversalNeighborhoodParametersArtifact
  - ccf.controlplane.artifacts.TemporalAsOfParametersArtifact
  - ccf.controlplane.artifacts.SimilaritySelectParametersArtifact
  - ccf.controlplane.artifacts.PolicyFilterParametersArtifact
  - ccf.controlplane.artifacts.OPERATOR_PARAMETERS_{TRAVERSAL,TEMPORAL,POLICY,SIMILARITY}
affects:
  - 15-11 (the D-07 operator-registry builder consumes all five types)
  - 15-13..15-20 (example artifact documents adopt the four class ids)
tech-stack:
  added: []
  patterns: [15-PATTERNS §1 Parts A-E, "no default is a value nobody chose"]
key-files:
  created:
    - docs/surface-changes/15-08-operator-parameters.md
  modified:
    - src/ccf/controlplane/artifacts.py
    - src/ccf/deployment/classes.py
    - tests/controlplane/test_artifact_roundtrip.py
decisions:
  - "PolicyFilterParametersArtifact is not a PolicyFilterParameters subclass — the incompleteness D-IMPL-76 mandates is made structural rather than defaulted"
  - "similarity_corpus_attribute_by_class is an artifact-only field; SimilaritySelectParameters (the L4 invoke contract) is unchanged"
metrics:
  duration: ~35m
  completed: 2026-08-04
---

# Phase 15 Plan 08: Operator-Parameters Artifact Classes Summary

Each of the four SDK-shipped operator categories now has a typed, versioned
`ArtifactClass` — three inheriting their existing `*Parameters` contract verbatim,
and policy deliberately not — so operator-registry construction becomes an
artifact read without the SDK inventing a schema for anything it does not ship.

## What was built

**Task 1 — five new contracts and four constants** (`5b51381`).
`OperatorParametersArtifact` is an empty `VersionedArtifact` marker base; its
docstring states the reason it exists (the D-07 builder types its `parameters`
mapping by that type rather than `isinstance`-filtering four unrelated classes, an
idiom that would otherwise be copied into every adopter's assembly code).
`TraversalNeighborhoodParametersArtifact`, `TemporalAsOfParametersArtifact` and
`SimilaritySelectParametersArtifact` multiply inherit the marker base and their
existing `ccf.operators.params` contract, so a parsed artifact **is** the
parameter set and reaches the operator constructor unmapped.
`PolicyFilterParametersArtifact` inherits only the marker base and declares
exactly `classification_attribute_by_class` and `permitted_classifications`.
`git diff src/ccf/operators/params.py` is empty.

**Task 2 — both docstring sites amended** (`ff7e8d4`). The module docstring and
`DeclaredArtifact`'s docstring both claimed, unqualified, that operator parameter
sets are a deployment's schema. Both now say **deployment-authored** and both
state the narrower rule D-01 actually states. The policy-bundle rationale is
intact; its scope changed, not its truth.

**Task 3 — coverage and the surface record** (`75b798c`). Four cases added to the
round-trip parametrization (satisfying 15-07's vacuity guard), three
constructor-acceptance tests, and two policy-specific tests. The fragment records
this plan's nine additions plus the docstring reshape.

## Key decisions

**The policy artifact is not a `PolicyFilterParameters`.** Both alternatives were
written out in the class docstring because both look reasonable until they are:
subclassing with the field required means the artifact can never parse (the value
is a registration-time content hash, D-IMPL-76); subclassing with a `frozenset()`
default means a parsed document satisfies `isinstance` and can be handed straight
to `PolicyFilter`, producing an operator that admits nothing while looking fully
configured — a silent fail-*closed* that reads as configured, which is the mirror
image of the failure the SDK guards against.

**The corpus map is artifact-only.** `similarity_corpus_attribute_by_class`
governs `TokenOverlapIndex` construction, so putting it on
`SimilaritySelectParameters` would place a value no invocation reads onto the L4
invoke contract. A test pins its absence there.

## Deviations from Plan

**1. [Rule 1 — Test correctness] The policy bypass test asserts the dynamic
refusal, not a constructor `TypeError`.**
- Found during: Task 3.
- Issue: the plan's acceptance criterion said "constructing `PolicyFilter`
  directly from the parsed artifact fails". `PolicyFilter.__init__` is a bare
  assignment with no runtime validation, so it does not raise; and `mypy`'s
  `files` are `["src", "runtime"]`, so no test module can assert the static
  refusal either. An initial `pytest.raises(TypeError)` was a false claim that
  happened to fail loudly.
- Fix: the test asserts what is actually true and is the property that matters —
  `not isinstance(parsed, PolicyFilterParameters)`, the field's absence from
  `model_fields`, and that an operator built by bypassing the builder **raises
  `AttributeError` on its own admission set** rather than admitting nothing. The
  docstring states explicitly which half of the refusal is static (the annotation,
  outside this module's reach) and which is asserted here. The substance of the
  criterion — the artifact cannot be used as an operator parameter set —
  is met; only the mechanism named for it changed.
- Commit: `75b798c`

Nothing else deviated. The manifest and frozen baseline were not touched, `make
ci-core` is green (1659 passed, 2 skipped), `make typecheck`, `make docs-strict`
and `python -m tools.lints --all` all exit 0.

## Note for 15-09 — the `required_operator_keys` `min_length=1` question

The reviewer's concern (raised against 15-09, not this plan) is whether
`ProductClassDeclaration.required_operator_keys` with `min_length=1` overconstrains
deployments needing zero operators. This plan produced **no evidence either way**
about a legitimately-absent operator *category*, and deliberately did not act on
it. One observation that is adjacent but does not decide it: the four categories
are now independently addressable artifact classes, so a deployment declaring
three of the four is a coherent, parseable state — nothing in this plan requires
all four to be present. That says nothing about whether a *product class* can
legitimately require zero operators, which is a different question about the
empty-operator validation gate (§6.3) and remains 15-09's to rule on.

## Self-Check: PASSED

- `src/ccf/controlplane/artifacts.py` — FOUND (modified)
- `src/ccf/deployment/classes.py` — FOUND (modified)
- `tests/controlplane/test_artifact_roundtrip.py` — FOUND (modified)
- `docs/surface-changes/15-08-operator-parameters.md` — FOUND
- Commits `5b51381`, `ff7e8d4`, `75b798c` — all present in `git log`
- `docs/surface/v0.2-surface.json` and `v0.2-surface-baseline.json` — unmodified
