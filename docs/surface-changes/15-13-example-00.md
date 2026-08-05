# 15-13 — examples/00-quickstart reshaped to typed artifact documents

Plan 15-13 adds **no** public Python surface: `tools/dump_surface.py --report`
shows nothing added by this plan (the accumulated set it prints belongs to
15-01 through 15-12). Every entry below is therefore `Public surface: false`.

The four multi-artifact bundles the quickstart shipped are now fourteen typed,
closed-world, `$schema`-annotated documents enumerated by one deployment
manifest. An adopter who copied the quickstart's artifacts needs the mapping,
which is what this fragment is for.

## examples/00-quickstart/artifacts/manifest.yaml

- Surface: examples/00-quickstart/artifacts/manifest.yaml
- Public surface: false
- Change type: added
- Before: absent — `run.py` registered artifacts by hand in a fourteen-line prologue
- After: a `ccf.deployment-manifest` naming every document by `path`, `key`, `class_id` and `role`, plus the tenant and the backend kind
- Why: the set of artifacts in force is replay dimension 2, so it must be one enumerated, content-hashable document rather than a sequence of registration calls no artifact records
- Migration: write a manifest and call `load_and_boot`; the hand-written prologue plus `boot()` still works unchanged

## examples/00-quickstart/artifacts/resolution-spec.yaml

- Surface: examples/00-quickstart/artifacts/resolution-spec.yaml
- Public surface: false
- Change type: reshaped
- Before: `ontology.yaml`, carrying `schema_version`, `artifact_version`, `tenant_id`, `entity_rules`, `relationship_rules`, `classification_attribute_by_class` and `similarity_corpus_attribute_by_class`
- After: `ccf.resolution-spec` carrying `semver`, `entity_rules` and `relationship_rules` and nothing else
- Why: D-03 makes the class closed-world over resolution rules only; the two attribute maps moved to the operator-parameters documents that consume them, and `tenant_id` to the manifest
- Migration: rename the file, replace both root version keys with a single `semver`, move `tenant_id` to the manifest, and move each attribute map to its operator's parameters document

## examples/00-quickstart/artifacts/events.yaml

- Surface: examples/00-quickstart/artifacts/events.yaml
- Public surface: false
- Change type: reshaped
- Before: flat envelopes with `source_system_id:` and `payload:`, and no `tenant_id` (read from the ontology)
- After: a `ccf.signal-batch` with `semver`, `tenant_id`, and envelopes using nested `source: {system_id: ...}` and `raw_payload:`
- Why: the document adopts the SDK's own envelope vocabulary, so the loader has no translation to perform and none to drift; the batch carries its tenant because every event in a batch belongs to one, and it disagrees loudly rather than being repaired
- Migration: nest `source_system_id` under `source: {system_id: ...}`, rename `payload:` to `raw_payload:`, add `tenant_id` at batch level and on each envelope

## examples/00-quickstart/artifacts/half-life-table.yaml

- Surface: examples/00-quickstart/artifacts/half-life-table.yaml
- Public surface: false
- Change type: reshaped
- Before: the `half_life_table:` block nested inside `halflife.yaml`
- After: its own `ccf.half-life-table` document
- Why: one artifact class, one document — two classes in one file cannot both carry an honest `$schema` header, because each annotates the other's keys as errors
- Migration: lift the nested mapping to the document root

## examples/00-quickstart/artifacts/debt-profile.yaml

- Surface: examples/00-quickstart/artifacts/debt-profile.yaml
- Public surface: false
- Change type: reshaped
- Before: the `debt_profile:` block nested inside `halflife.yaml`
- After: its own `ccf.debt-profile` document
- Why: same as the half-life table — one class, one document, one version lane
- Migration: lift the nested mapping to the document root

## examples/00-quickstart/artifacts/operator-parameters-traversal.yaml

- Surface: examples/00-quickstart/artifacts/operator-parameters-traversal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.traversal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.traversal` document
- Why: the SDK owns this parameter contract, so the document is validated against it rather than sitting inside an untyped bundle
- Migration: lift the block to a document root and add `semver`

## examples/00-quickstart/artifacts/operator-parameters-temporal.yaml

- Surface: examples/00-quickstart/artifacts/operator-parameters-temporal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.temporal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.temporal` document
- Why: as above
- Migration: lift the block to a document root and add `semver`

## examples/00-quickstart/artifacts/operator-parameters-policy.yaml

- Surface: examples/00-quickstart/artifacts/operator-parameters-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.policy:` block inside `controlplane.yaml`, with `classification_attribute_by_class` living in `ontology.yaml`
- After: a `ccf.operator-parameters.policy` document carrying both, and deliberately no `permitted_policy_bundle_versions`
- Why: one artifact, one consumer — the map is read by this operator and nothing else. The admitted-version set stays absent because it is a content hash minted at registration, which an adopter has no value to author (D-IMPL-76)
- Migration: move `classification_attribute_by_class` out of the ontology into this document; pass the policy bundle key to `build_operator_registry`

## examples/00-quickstart/artifacts/operator-parameters-similarity.yaml

- Surface: examples/00-quickstart/artifacts/operator-parameters-similarity.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.similarity:` block inside `controlplane.yaml`, with `similarity_corpus_attribute_by_class` in `ontology.yaml` and `index_version` alongside the query
- After: a `ccf.operator-parameters.similarity` document carrying query, threshold, ranked classes and the corpus attribute map; the index version moves out
- Why: the corpus attribute map governs index *construction* and belongs with the artifact that declares it. The index version does not: it identifies a corpus state at a named boundary, not a parameter set, so it is supplied to the builder per run
- Migration: move `similarity_corpus_attribute_by_class` out of the ontology; pass `similarity_index_version` to `build_operator_registry`

## examples/00-quickstart/artifacts/perspective.yaml

- Surface: examples/00-quickstart/artifacts/perspective.yaml
- Public surface: false
- Change type: reshaped
- Before: the `perspective:` block inside `controlplane.yaml`
- After: a `ccf.perspective` document
- Why: a parsed artifact of this class **is** a `Perspective` and passes straight into projection invocation with no field translation
- Migration: lift the block to a document root and add `semver`

## examples/00-quickstart/artifacts/product-class.yaml

- Surface: examples/00-quickstart/artifacts/product-class.yaml
- Public surface: false
- Change type: reshaped
- Before: the `product_class:` block inside `controlplane.yaml`, carrying `plan_id` and `product_ttl_seconds` and declaring no operator set
- After: a `ccf.product-class` document declaring `required_operator_keys` and `max_ttl_key`; `plan_id` and `product_ttl_seconds` move to the deployment's own governance document
- Why: `required_operator_keys` is the authored declared side of the lineage gate. Without it the projection returned the operator registry's own keys and Gate 2 compared a value against itself. `max_ttl_version` stays absent because registering the ceiling mints it
- Migration: add `required_operator_keys` naming the operator keys your projection depends on, and read it in your projection instead of the registry's keys

## examples/00-quickstart/artifacts/product-governance.yaml

- Surface: examples/00-quickstart/artifacts/product-governance.yaml
- Public surface: false
- Change type: added
- Before: `max_ttl_seconds`, `product_ttl_seconds`, `index_version` and `artifacts.replay_record_class` scattered through `controlplane.yaml`
- After: one deployment-authored document in the `DeclaredArtifact` envelope carrying all of them plus `plan_id`
- Why: these are values the SDK deliberately declines to own; the TTL ceiling and the product's own lifetime in particular stay two separately authored numbers, which is the whole reason Gate 3 is a check
- Migration: collect the equivalents from your Control Plane bundle into a declared document

## examples/00-quickstart/artifacts/policy-bundle.yaml

- Surface: examples/00-quickstart/artifacts/policy-bundle.yaml
- Public surface: false
- Change type: reshaped
- Before: the `policy_bundle:` block inside `controlplane.yaml`, registered as a bare mapping
- After: a document in the open `DeclaredArtifact` envelope — `semver`, `class_id`, `declaration`
- Why: the SDK never invents a policy-bundle schema, but it does own the envelope, and the envelope is what gives a deployment-authored document a version lane and a checkable class identity
- Migration: wrap your bundle in `declaration:` and add `semver` and `class_id`

## examples/00-quickstart/artifacts/decision.yaml

- Surface: examples/00-quickstart/artifacts/decision.yaml
- Public surface: false
- Change type: reshaped
- Before: the `decision:` block inside `controlplane.yaml`, plus `demonstration:` inside `halflife.yaml`
- After: one deployment-authored `role: load` document carrying both instants and the freshness demonstration
- Why: what instant one run asked about is not part of what the fabric was permitted to do, so it is parsed and returned rather than registered into replay dimension 2
- Migration: move your decision instants into a declared document and mark it `role: load`

## examples/00-quickstart/artifacts/expected.yaml

- Surface: examples/00-quickstart/artifacts/expected.yaml
- Public surface: false
- Change type: reshaped
- Before: the `expected:` block inside `controlplane.yaml`, read by `run.py`
- After: a deployment-authored `role: load` document, read by `tests/examples/test_quickstart_output.py`
- Why: D-09 moves the example's assertions into `tests/`, and the expectations have to move with them; an expectation is not a permission, so it is never put in force
- Migration: move your `expected:` block into a declared document and read it from your relocated tests

## docs/schemas/ccf.declared-artifact.json

- Surface: docs/schemas/ccf.declared-artifact.json
- Public surface: false
- Change type: added
- Before: absent — deployment-authored classes had no `$schema` target at all, so their documents could only pass `make schema-headers` with a deferral marker naming no real closing plan
- After: the committed JSON Schema of the open `DeclaredArtifact` envelope, emitted by `tools/dump_schemas.py` **without** joining `SDK_ARTIFACT_CLASSES`
- Why: the SDK does not own a deployment's schema, but it does own the envelope — `semver`, `class_id`, and an open `declaration` — and that is exactly what such a document can honestly be annotated with. Keeping it out of `SDK_ARTIFACT_CLASSES` means no manifest can name it as a class and the "unknown class id resolves to the envelope" design is untouched
- Migration: point deployment-authored documents at `docs/schemas/ccf.declared-artifact.json` and give each one a `class_id` field

## tools/check_schema_headers.py

- Surface: tools/check_schema_headers.py
- Public surface: false
- Change type: behavior
- Before: a header naming anything outside `SDK_ARTIFACT_CLASSES` was rejected, so deployment-authored documents were unannotatable
- After: a header naming `ccf.declared-artifact` is accepted when the envelope contract accepts the document, the document declares a `class_id`, and that class is not one the SDK owns; the manifest cross-check then compares the entry's `class_id` against the *document's* field rather than the header
- Why: the indirection must not become an escape hatch. An SDK-owned class pointed at the open envelope would silence every constraint it declares, so that is refused, and the two-independent-statements property the cross-check exists for is preserved rather than dropped
- Migration: none — existing headers are unaffected
