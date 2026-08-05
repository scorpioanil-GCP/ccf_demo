# 15-11 — the two-phase, view-aware operator-registry builder

Plan 15-11 replaces the 64-line operator-registry construction block repeated
across nine example sites with one call. The block is worth showing in full,
because what the `after` deliberately keeps is as load-bearing as what it drops.

```python
# before — examples/00-quickstart/run.py:232-295, repeated across nine sites
params = control["operator_parameters"]
operators = OperatorRegistry()
operators.register(
    PolicyFilter(
        parameters=PolicyFilterParameters(
            permitted_policy_bundle_versions=frozenset({policy_version}),
            classification_attribute_by_class=dict(
                ontology["classification_attribute_by_class"]
            ),
            permitted_classifications=frozenset(
                params["policy"]["permitted_classifications"]
            ),
        )
    )
)
corpus_attribute = ontology["similarity_corpus_attribute_by_class"]
view = handle.reader.as_of(tenant_id=tenant_id, at=boundary)
corpus = {
    (tenant_id, record.claim.entity_uri): record.claim.attributes[
        corpus_attribute[record.claim.entity_class]
    ]
    for record in view.entities
    if record.claim.entity_class in corpus_attribute
}
operators.register(
    SimilaritySelect(
        parameters=SimilaritySelectParameters(
            query=params["similarity"]["query"],
            minimum_score_percent=params["similarity"]["minimum_score_percent"],
            ranked_entity_classes=frozenset(
                params["similarity"]["ranked_entity_classes"]
            ),
        ),
        index=TokenOverlapIndex(
            corpus=corpus, index_version=params["similarity"]["index_version"]
        ),
    )
)
operators.register(TemporalAsOf(parameters=TemporalAsOfParameters(...)))
operators.register(TraversalNeighborhood(parameters=TraversalNeighborhoodParameters(...)))

# after
view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=boundary)
operators = build_operator_registry(
    parameters={key: booted.artifacts[key] for key in operator_parameter_keys},
    view=view,
    pins=booted.pins,
    policy_bundle_key=manifest_policy_bundle_key,
    similarity_index_version=declared_index_version,
)
```

**`OperatorRegistry` and every operator constructor remain directly usable
(D-14).** `git diff src/ccf/operators/` is empty for this plan. A deployment that
wants to register one operator by hand, or to inject a `SimilarityIndexProtocol`
implementation other than `TokenOverlapIndex`, still does exactly what it did
before. This is an additive wiring surface, not a replacement of the algebra.

**`parameters` takes the *artifact* classes from 15-08, not the operator
parameter classes.** An adopter passing a bare `PolicyFilterParameters` is not on
the supported path, and the refusal is structural rather than a check: the whole
point of the policy conversion is that `permitted_policy_bundle_versions` arrives
from the adopter-passed pins (D-IMPL-76), so a caller who already holds a
complete `PolicyFilterParameters` has assembled the admitted-bundle set somewhere
the audit plane cannot see. An unrecognized artifact class is refused with a
message naming the manifest key.

**This builder does not answer Gate 2.** The returned registry's `keys()` is what
the fabric *resolved*; the declared side of the empty-operator gate is
`ProductClassDeclaration.required_operator_keys`, authored in the product-class
artifact (15-09). Passing this registry's keys to both sides of that comparison
makes the gate compare a value against itself. The builder deliberately exposes
no "required keys" convenience that would make the tautology easier to write than
to avoid.

## ccf.deployment.operators.build_operator_registry

- Surface: ccf.deployment.operators.build_operator_registry
- Public surface: true
- Change type: added
- Before: absent — every deployment hand-wrote a ~64-line block constructing four
  operators, converting the policy artifact's fields into a
  `PolicyFilterParameters`, and building the similarity corpus with an inline
  dict comprehension over a live view
- After: `build_operator_registry(*, parameters, view, pins, policy_bundle_key,
  similarity_index_version=None) -> OperatorRegistry`
- Why: four properties, each of which the hand-written block could lose silently.
  **The view is in the signature.** This could not be a pure artifact read:
  `SimilaritySelect` ranks against an injected index built from a corpus read out
  of the live graph at a named temporal boundary, after boot and after ingest.
  Lazy binding — handing the operator a callable that built the index at first
  invocation — was considered and rejected: it would build the index inside the
  projection engine's execution, in the algorithmic path, over a corpus
  determined by *when the engine happened to invoke the operator* rather than by
  a boundary the deployment named. INV-CH7-27 fixes the similarity determinism
  contract as `(corpus_version, embedding_model_version, query, threshold,
  policy_regime) -> same result`, and a corpus that is a function of invocation
  timing is not one that contract can name. `view` is therefore keyword-only with
  no default, so the ordering constraint is structural rather than documented,
  and a test asserts `Parameter.empty` rather than merely asserting that omitting
  it raises (T-15-11-03).
  **The admitted policy-bundle version arrives from the adopter.** Per D-IMPL-76
  the pin set is passed *in*, never discovered: there is no `resolve_latest` in
  the module, and a builder that asked the Control Plane what to admit would be
  the fabric deciding its own admission set. The `PolicyFilterParameters` is
  constructed explicitly rather than by `model_copy(update=...)` — the artifact
  is not a `PolicyFilterParameters`, so there is nothing to copy from, and the
  explicit construction is the single visible place where the admitted-bundle set
  is assembled (T-15-11-01).
  **No caller-declared category.** Registration goes through `register(operator)`
  with no `category=` keyword; the registry reads category and parameter schema
  off the operator. A builder that re-introduced a caller-declared category would
  let the planner order an operator into a position it does not belong in — the
  Policy-after-Similarity failure INV-CH7-26 forbids. An AST test asserts zero
  `category=` keywords across every `register` call in the module, because a
  behavioral test would pass if a future edit declared each operator's *own*
  category explicitly, which reads harmlessly and reopens the failure anyway
  (T-15-11-02).
  **Which operators exist stays per-deployment policy.** Expressed by which
  artifacts `parameters` contains — `examples/02-skilling` registers three, not
  four — so the module holds no fixed set of four keys, no operator key literal
  and no entity class literal (CINV-01). `DuplicateOperatorKey` stays fatal and
  uncaught (T-15-11-04)
- Migration: replace the inline block with the call. Assemble `parameters` by
  naming your own manifest keys against `booted.artifacts` — no `isinstance`
  filtering, which is what the `OperatorParametersArtifact` marker base from
  15-08 exists to make unnecessary. Take the view *at the boundary the decision
  is being made against*, before calling. Pass `booted.pins` and the manifest's
  `policy_bundle_key`. Supply `similarity_index_version` exactly when
  `parameters` carries a similarity artifact: it is required then and refused
  otherwise. **The builder does not mint one** — a version derived from the
  parameters artifact's own pin would be identical across two different
  boundaries, which is precisely the corpus identity INV-CH7-27 needs to
  distinguish, and `TokenOverlapIndex` already documents `index_version` as a
  value the deployment assigns

## ccf.deployment.build_operator_registry

- Surface: ccf.deployment.build_operator_registry
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: the package root is the import an adopter reaches for, as with
  `load_and_boot` beside it
- Migration: none — both import paths resolve

## ccf.deployment.operators.SimilarityCorpusAttributeError

- Surface: ccf.deployment.operators.SimilarityCorpusAttributeError
- Public surface: true
- Change type: added
- Before: absent — the inline corpus comprehension raised a bare `KeyError` from
  a dict subscript, with no message naming which artifact and which entity
  disagreed, and nine sites were free to "fix" it nine different ways
- After: a `ValueError` raised at registry-build time when an entity of a class
  the corpus map *names* carries no such attribute, or carries a non-string value
  under it
- Why: **this is the corpus-extraction ruling, and it is stated because nine
  deployments will follow it.** Two things can go wrong reading a corpus through
  `similarity_corpus_attribute_by_class`, and they get opposite answers.
  *An entity class absent from the map contributes no corpus entry* — silent, and
  correct. The map is the deployment's statement of which classes are rankable, so
  a class it does not name is a class the deployment chose to leave out, exactly
  as `SimilaritySelectParametersArtifact` already records. There is nothing to
  repair and nothing to report.
  *An entity of a named class carrying no such attribute is refused.* The
  declaration and the graph contradict each other, and every repair is worse than
  the refusal: skipping the entity drops it from the corpus, `TokenOverlapIndex.rank`
  then silently passes over it, and the similarity operator excludes it from the
  view — a governed omission produced by no rule anyone wrote down. Substituting
  an empty string is the same omission with a scoring story attached. **Refuse,
  never repair.** A non-string corpus value is refused by the same rule: coercing
  it would move the failure into ranking, at invocation time, far from the
  artifact that declared it. Both halves are asserted, not left to the docstring
- Migration: none for a correct deployment. If a build now raises this, the
  similarity artifact's `similarity_corpus_attribute_by_class` names an attribute
  the resolution spec does not carry onto that entity class — fix whichever of
  the two documents is wrong. Removing the class from the map is the supported
  way to say "this class is not rankable"

## ccf.deployment.SimilarityCorpusAttributeError

- Surface: ccf.deployment.SimilarityCorpusAttributeError
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: raised by `build_operator_registry`, so an adopter catching it imports it
  from the same place it imported the builder
- Migration: none — both import paths resolve
