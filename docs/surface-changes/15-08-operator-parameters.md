# 15-08 — typed artifact classes for the four SDK-shipped operator categories

Plan 15-08 gives each canonical operator category a typed Control Plane artifact
class, so the operator-registry construction repeated by hand across the example
tree becomes an artifact read. Nine names are added — a marker base, four
contracts, four `ArtifactClass` constants — and the two `artifacts.py` docstring
sites that claimed operator parameter sets belong to the deployment are
qualified.

`ccf.operators.params` is **not edited**: three of the four contracts subclass
their existing `*Parameters` model, so every existing direct construction site —
tests, perf fixtures, adopter code — is untouched, and no second field vocabulary
exists to drift.

## ccf.controlplane.artifacts.OperatorParametersArtifact

- Surface: ccf.controlplane.artifacts.OperatorParametersArtifact
- Public surface: true
- Change type: added
- Before: absent — there was no shared type over operator-parameters artifacts
- After: an empty `VersionedArtifact` subclass carrying no fields, the marker
  base of all four category contracts
- Why: so the operator-registry builder can type its `parameters` mapping as
  `Mapping[str, OperatorParametersArtifact]` and accept all four categories *by
  type*. Without it the builder must `isinstance`-filter four unrelated classes,
  and that idiom, copied into adopter code to assemble the mapping, is exactly
  the new duplication class this surface exists to prevent
- Migration: none — new name

## ccf.controlplane.artifacts.TraversalNeighborhoodParametersArtifact

- Surface: ccf.controlplane.artifacts.TraversalNeighborhoodParametersArtifact
- Public surface: true
- Change type: added
- Before: absent — a deployment's traversal parameters were hand-marshalled into
  `TraversalNeighborhoodParameters(seed_entity_classes=..., relationship_types=...,
  depth_limit=...)` at each call site
- After: `class_id` `ccf.operator-parameters.traversal`; a contract subclassing
  `ccf.operators.params.TraversalNeighborhoodParameters` verbatim plus the
  `semver` lane
- Why: these parameter contracts are already `/src` code whose own module
  docstring calls them "Control Plane *values* that a deployment declares,
  versions, and replays against" — refusing to parse them declaratively was
  inconsistent rather than principled (D-01). Defined here rather than by adding
  `semver` to `params.py` because `ccf.operators` is L4 and importing the
  Control Plane's versioned base there would invert a layer
- Migration: replace the hand-built parameter block with
  `parse_artifact(document, OPERATOR_PARAMETERS_TRAVERSAL)`. A parsed artifact
  **is** a `TraversalNeighborhoodParameters` and passes straight to
  `TraversalNeighborhood(parameters=...)` with no unwrapping

## ccf.controlplane.artifacts.TemporalAsOfParametersArtifact

- Surface: ccf.controlplane.artifacts.TemporalAsOfParametersArtifact
- Public surface: true
- Change type: added
- Before: absent — `TemporalAsOfParameters(require_valid_at_boundary=...)` built
  by hand at each call site
- After: `class_id` `ccf.operator-parameters.temporal`; a contract subclassing
  `ccf.operators.params.TemporalAsOfParameters` verbatim plus the `semver` lane
- Why: same D-01 argument as the traversal class; the four categories move
  together or the surface is incoherent
- Migration: `parse_artifact(document, OPERATOR_PARAMETERS_TEMPORAL)`; the parsed
  artifact is accepted directly by `TemporalAsOf`

## ccf.controlplane.artifacts.SimilaritySelectParametersArtifact

- Surface: ccf.controlplane.artifacts.SimilaritySelectParametersArtifact
- Public surface: true
- Change type: added
- Before: absent — `SimilaritySelectParameters(query=..., minimum_score_percent=...,
  ranked_entity_classes=...)` built by hand, with the corpus attribute map read
  separately out of the ontology document
- After: `class_id` `ccf.operator-parameters.similarity`; a contract subclassing
  `ccf.operators.params.SimilaritySelectParameters` verbatim, **plus one
  artifact-only field**, `similarity_corpus_attribute_by_class: Mapping[str, str]`
- Why: same D-01 argument, with one deliberate asymmetry. The corpus map governs
  `TokenOverlapIndex` *construction*, not operator invocation, so it is read by
  the registry builder before the operator exists. Adding it to
  `SimilaritySelectParameters` would put a construction-time value on the
  per-invocation L4 invoke contract, so it lives on the artifact instead.
  **`SimilaritySelectParameters` itself is unchanged** and still declares exactly
  `query`, `minimum_score_percent`, `ranked_entity_classes`
- Migration: `parse_artifact(document, OPERATOR_PARAMETERS_SIMILARITY)`; the
  parsed artifact is accepted directly by `SimilaritySelect`, and its
  `similarity_corpus_attribute_by_class` is what the index construction reads —
  a deployment carrying that map in its ontology document moves it here

## ccf.controlplane.artifacts.PolicyFilterParametersArtifact

- Surface: ccf.controlplane.artifacts.PolicyFilterParametersArtifact
- Public surface: true
- Change type: added
- Before: absent — `PolicyFilterParameters(...)` built by hand, with
  `permitted_policy_bundle_versions=frozenset({policy_version})` where
  `policy_version` is the return value of `registry.register(...)`
- After: `class_id` `ccf.operator-parameters.policy`; a contract declaring
  exactly `semver`, `classification_attribute_by_class` and
  `permitted_classifications`. It is **not** a `PolicyFilterParameters` subclass
  and declares **no** `permitted_policy_bundle_versions`
- Why: per D-IMPL-76 the admitted policy-bundle version set is a content hash
  minted at registration, so no authored artifact can state it — the adopter
  passes the pin set to the operator-registry builder. Subclassing and leaving
  the field required means the artifact can never parse; subclassing and
  defaulting it to `frozenset()` means a parsed document satisfies
  `isinstance(x, PolicyFilterParameters)` and can be handed straight to
  `PolicyFilter` by anyone bypassing the builder, producing an operator that
  admits nothing while looking fully configured. A separate, deliberately
  incomplete contract makes the incompleteness structural
- Migration: `parse_artifact(document, OPERATOR_PARAMETERS_POLICY)`, and the
  document states **no** `permitted_policy_bundle_versions` key — the contract is
  closed-world, so including one is a parse failure. An adopter who expected to
  pass the parsed artifact straight to `PolicyFilter` needs
  `build_operator_registry` instead: it is what constructs the real
  `PolicyFilterParameters`, with the version set taken from the adopter-passed
  pins. The deployment still names which bundles it admits; the SDK only resolves
  the pin

## ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TRAVERSAL

- Surface: ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TRAVERSAL
- Public surface: true
- Change type: added
- Before: absent — no class-id addressed traversal parameters, so a D-05 manifest
  could not name them
- After: `ArtifactClass(class_id="ccf.operator-parameters.traversal", contract=TraversalNeighborhoodParametersArtifact)`,
  registered in `ccf.deployment.classes.SDK_ARTIFACT_CLASSES`
- Why: a class the SDK ships that a manifest cannot address is a class no adopter
  can register; the constant *is* the registration mechanism
- Migration: name `ccf.operator-parameters.traversal` in the manifest entry

## ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TEMPORAL

- Surface: ccf.controlplane.artifacts.OPERATOR_PARAMETERS_TEMPORAL
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.operator-parameters.temporal", contract=TemporalAsOfParametersArtifact)`,
  registered in `SDK_ARTIFACT_CLASSES`
- Why: same as the traversal constant — manifest addressability
- Migration: name `ccf.operator-parameters.temporal` in the manifest entry

## ccf.controlplane.artifacts.OPERATOR_PARAMETERS_POLICY

- Surface: ccf.controlplane.artifacts.OPERATOR_PARAMETERS_POLICY
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.operator-parameters.policy", contract=PolicyFilterParametersArtifact)`,
  registered in `SDK_ARTIFACT_CLASSES`
- Why: same as its siblings. Leaving the policy category on `DeclaredArtifact`
  while the other three gained typed classes was the rejected option (c) under
  D-IMPL-76 — the least consistent surface and the hardest to document
- Migration: name `ccf.operator-parameters.policy` in the manifest entry, and
  keep the policy-bundle pin in adopter code where D-06 already puts every other
  pin (D-IMPL-76)

## ccf.controlplane.artifacts.OPERATOR_PARAMETERS_SIMILARITY

- Surface: ccf.controlplane.artifacts.OPERATOR_PARAMETERS_SIMILARITY
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.operator-parameters.similarity", contract=SimilaritySelectParametersArtifact)`,
  registered in `SDK_ARTIFACT_CLASSES`
- Why: same as its siblings — manifest addressability for the fourth category
- Migration: name `ccf.operator-parameters.similarity` in the manifest entry; the
  document carries `similarity_corpus_attribute_by_class` alongside the
  operator's own three fields

## src/ccf/controlplane/artifacts.py

- Surface: src/ccf/controlplane/artifacts.py
- Public surface: false
- Change type: reshaped
- Before: the module docstring and the `DeclaredArtifact` class docstring both
  named "operator parameter sets" — unqualified — as a shape whose schema belongs
  to a deployment
- After: both say **deployment-authored** operator parameter sets, and both state
  the rule D-01 actually states: the SDK owns the schema of what it ships and
  never invents one for what it does not. The four categories the SDK ships have
  typed classes; everything else takes the open envelope
- Why: D-01. The unqualified claim was no longer true once this plan shipped the
  four typed classes, and amending only one of the two sites would leave the
  module contradicting itself. The policy-bundle rationale is kept intact — it
  was sound for policy bundles and remains the reason `DeclaredArtifact` exists;
  what changed is its scope, not its truth. mkdocstrings publishes both
  docstrings, so Phase 16's rendered reference changes with this edit, which is
  why it is a recorded surface change and not a comment tidy
- Migration: none — no name, signature or behavior changes; the docstrings are
  the deliverable
