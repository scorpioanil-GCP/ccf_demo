---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 11
subsystem: deployment
tags: [operators, registry, similarity, corpus, D-07, D-IMPL-76, INV-CH7-27]
requires:
  - ccf.operators.registry.OperatorRegistry
  - ccf.operators.categories
  - ccf.controlplane.artifacts.OperatorParametersArtifact (15-08)
  - ccf.deployment.pins.ResolvedPins (15-10)
  - ccf.graph.protocols.GraphView
  - ccf.similarity.protocol.TokenOverlapIndex
provides:
  - ccf.deployment.operators.build_operator_registry
  - ccf.deployment.build_operator_registry
  - ccf.deployment.operators.SimilarityCorpusAttributeError
  - ccf.deployment.SimilarityCorpusAttributeError
affects:
  - the nine example sites that hand-build an OperatorRegistry (15-13 onward)
tech-stack:
  added: []
  patterns:
    - "ordering constraint encoded in a keyword-only parameter with no default"
    - "refuse-never-repair at a declaration/state contradiction"
    - "adopter passes the pin set; the builder never resolves it (D-IMPL-76)"
key-files:
  created:
    - src/ccf/deployment/operators.py
    - tests/deployment/test_operator_builder.py
    - docs/surface-changes/15-11-operator-builder.md
  modified:
    - src/ccf/deployment/__init__.py
decisions:
  - "Corpus ruling: a class absent from similarity_corpus_attribute_by_class is skipped silently; an entity of a named class missing that attribute is refused."
  - "similarity_index_version is an explicit adopter-supplied keyword; the builder does not mint one."
metrics:
  duration: ~55m
  completed: 2026-08-04
---

# Phase 15 Plan 11: The Operator-Registry Builder Summary

`build_operator_registry` turns operator-parameters artifacts plus a `GraphView`
into a populated `OperatorRegistry` in one call, with the two properties that
made a naive helper dangerous — index-at-a-named-boundary and adopter-held policy
pins — enforced by the signature and by tests rather than by prose.

## What was built

**Task 1 — `src/ccf/deployment/operators.py`** (commit `30f0ac4`). A two-phase
builder. Phase 1 constructs the parameter-only operators (traversal, temporal)
directly from their parsed artifacts, which *are* their `*Parameters` models, and
performs the module's one conversion: a real `PolicyFilterParameters` built
explicitly with `permitted_policy_bundle_versions=frozenset({pins.version_for(
policy_bundle_key)})`. Phase 2 reads the corpus out of the passed view using the
similarity artifact's own `similarity_corpus_attribute_by_class`, builds a
`TokenOverlapIndex`, and injects it into `SimilaritySelect`.

`view` is keyword-only with no default — the ordering constraint lives in the
signature. No `resolve_latest` in the module. No `category=` on any `register`
call. No operator-key or entity-class literal (CINV-01). Iteration is over
`sorted(parameters.items())`, so registration order is a function of the manifest
keys rather than of mapping iteration order.

**Task 2 — `tests/deployment/test_operator_builder.py`** (commit `1d4c7ab`), 13
tests, plus `docs/surface-changes/15-11-operator-builder.md` claiming all four
added names.

## The two review findings I owned

**cursor (MEDIUM) — corpus extraction underspecified.** Correct, and the more
consequential of the two: nine examples will follow whatever this module does, so
an unstated rule becomes nine divergent readings. Ruled explicitly, stated in the
module docstring and in the fragment, and asserted in both halves:

- *A class absent from the map contributes no corpus entry* — silent skip, and
  correct. The map is the deployment's statement of which classes are rankable;
  a class it does not name is one the deployment chose to leave out. This matches
  what `SimilaritySelectParametersArtifact` (15-08) already records.
- *An entity of a named class carrying no such attribute is refused* —
  `SimilarityCorpusAttributeError`, at build time. The declaration and the graph
  contradict each other. Every repair is worse: skipping drops the entity from
  the corpus, `rank` then passes over it, and the similarity operator excludes it
  from the view — a governed omission produced by no rule anyone wrote down.
  Substituting an empty string is the same omission with a scoring story
  attached. A non-string corpus value is refused by the same rule.

The prior inline comprehension raised a bare `KeyError` from a dict subscript for
the second case, with no message naming which artifact and which entity
disagreed. So the behavior is preserved in direction and made legible.

**codex (MEDIUM) — the "indices differ" test may be brittle.** Correct as a
warning about the test I would otherwise have written. Two changes:

1. The assertion is on **observable corpus membership**, never identity.
   `TokenOverlapIndex.rank` skips a candidate with no corpus entry, so the
   returned URI set *is* the corpus membership among those candidates. Both
   registries are ranked against the *same* candidate set (the later view), so
   the difference cannot come from what each index was asked about.
2. **Both ingests happen before either registry is built.** My first draft built
   the early registry while the graph still held one entity — under which an
   implementation that ignored `view` entirely and read the live graph would have
   produced the same one-entity corpus and passed. Building both registries
   against a two-entity graph means only the boundary carried by `view` can
   account for the 1-vs-2 difference. The test asserts the early corpus is a
   strict subset of the later one, with explicit lengths.

## Deviations from Plan

### 1. [Rule 2 — missing critical functionality] Added `similarity_index_version`

**Found during:** Task 1.
**Issue:** The plan's four-keyword signature has no source for
`TokenOverlapIndex(index_version=...)`, which is required with no default.
`SimilaritySelectParametersArtifact` (15-08) declares no such field, and the
artifact is not in this plan's `files_modified`.

Deriving it inside the builder was considered and rejected. The obvious
derivation — the similarity artifact's own pin — is **wrong**, not merely
inelegant: pin identity is content identity of the *parameters document*, so two
registries built at two different temporal boundaries from one artifact would
carry the same `index_version` while holding different corpora. INV-CH7-27 fixes
the determinism contract as `(corpus_version, embedding_model_version, query,
threshold, policy_regime) -> same result`; a corpus_version that cannot
distinguish two corpora is not one that contract can use. `TokenOverlapIndex`
already documents `index_version` as "version identity **the deployment**
assigns."

**Fix:** `similarity_index_version: str | None = None`, required exactly when
`parameters` carries a similarity artifact and refused when it does not — the
symmetric refuse-to-guess posture `_preflight_backend` (15-10) already
established. Documented in the docstring and the fragment.
**Files:** `src/ccf/deployment/operators.py`. **Commit:** `30f0ac4`.

### 2. [binding ruling #4] Did not write the plan-scoped `--report` subset test

The plan's Task 2 acceptance criteria ask for a test asserting
`set(report.added)` is a subset of this fragment's `Public surface: true`
entries. The binding rulings in my brief forbid exactly this, and they are right:
`--report` returns the **accumulated** 46 names since 15-01, not mine, so a
plan-scoped copy is the accumulation trap in its purest form. The assertion
already exists phase-wide as
`tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added`.

That existing test earned its keep here: it failed on my first fragment draft and
named the one entry I had omitted
(`ccf.deployment.SimilarityCorpusAttributeError`, the package-root re-export). A
second copy would have found the same thing twice.

### 3. [Rule 2] Unrecognized artifact classes are refused

The plan does not say what to do with a `parameters` entry belonging to no
canonical category. Silently ignoring it would let a deployment believe an
operator was registered when it was not, and the failure would surface as a
planner `UnregisteredOperator` far from the manifest key that caused it. The
builder raises `ValueError` naming the manifest key.

## Non-entrenchment of the Gate 2 tautology

The builder returns a bare `OperatorRegistry` and nothing else. It exposes no
"required keys" accessor, no bundled declared/resolved pair, and no convenience
that would make `required=registry.keys()` easier to write than to avoid. The
module docstring and the fragment both state where the *declared* side actually
lives — `ProductClassDeclaration.required_operator_keys` (15-09) — so 15-13 has an
authored source named at the point where it will be reached for, and 15-21's AST
guard has something clean to point at.

## Threat Model Dispositions

| Threat | Disposition |
|--------|-------------|
| T-15-11-01 policy admission widened by the builder | Mitigated. Pin passed in; parameterized test over two pins proves admission changes with it; a second test proves the artifact declares no version set at all. No `resolve_latest` in the module. |
| T-15-11-06 corpus map drifting into the L4 invoke contract | Mitigated. Test asserts the field is present on the artifact and absent from `SimilaritySelectParameters.model_fields`. |
| T-15-11-02 ordering via a caller-declared category | Mitigated. AST test finds zero `category=` keywords across every `register` call, with a non-vacuity assertion that calls were found at all. |
| T-15-11-03 corpus determined by invocation timing | Mitigated. `view` keyword-only with `Parameter.empty`; the two-boundary test is built to fail a live-graph-reading implementation. |
| T-15-11-04 duplicate operator key | Mitigated. `DuplicateOperatorKey` uncaught; test asserts it. |
| T-15-11-05 builder growing into gate execution | Mitigated. `ccf.products.gates` not imported; the 15-02 `cinv02-deployment-gates` lint passes. |
| T-15-11-SC package installs | N/A. No installs. |

## Verification

- `pytest tests/deployment/ tests/operators/ tests/products/ tests/test_surface_drift.py -q` — 85 passed
- `make lint` (`tools.lints --all`) — exit 0
- `make typecheck` — no issues in 167 source files
- `make test` — **1727 passed, 2 skipped**. These three are the `ci-core` legs;
  run separately because the aggregate target exceeds the 2-minute shell timeout.
- `git status --short docs/surface/` — empty. The live manifest and the frozen
  baseline are untouched; `make surface` was not run.

## Known Stubs

None.

## Self-Check: PASSED

- `src/ccf/deployment/operators.py` — FOUND
- `tests/deployment/test_operator_builder.py` — FOUND
- `docs/surface-changes/15-11-operator-builder.md` — FOUND
- commit `30f0ac4` — FOUND
- commit `1d4c7ab` — FOUND
