# 15-18 — examples/04-cross-process reshaped to typed artifact documents

Plan 15-18 adds **no** public Python surface: it touches `examples/`, `public/`
and `tests/` only. Every entry below is therefore `Public surface: false` with
`Change type: reshaped`, and each `Surface` value is the repo-relative path of a
changed artifact document. An artifact-document format change is real and an
adopter who copied this example's artifacts must act on it, but it can never
appear in the `__all__`-derived manifest diff.

**A note on the vocabulary below.** Every `Before:` clause quotes the
pre-rewrite documents, which carried a property-intelligence vocabulary
(`larkfield-estates`, `SituationPlan`). A separate commit in this same plan
re-domains the example to syndicated lending (`harborline-syndications`,
`CovenantSlicePlan`) per D-10, so Phase 16 has a banking A2A/MCP worked
instance. That re-domaining is not a surface change and is not logged here; the
`Before:` names are left as they were so this fragment stays an accurate record
of what an adopter is migrating *from*.

The five multi-artifact bundles this example shipped (`ontology.yaml`,
`controlplane.yaml`, `a2a.yaml`, `agent.yaml`, `prompt.yaml`) are now
twenty-seven typed, closed-world, `$schema`-annotated documents.

**This example carries TWO deployment manifests, and that is the structural
change an adopter most needs to notice.** Producer and consumer are two
deployments in two OS processes with two Control Planes, two graphs and two
replay records. D-06 makes the artifact set in force answerable from one
document *per deployment*, so there are two: `producer-manifest.yaml` and
`consumer-manifest.yaml`. The pre-rewrite example read one `controlplane.yaml`
from both processes.

**Three consumer documents are content-identical to a producer document and are
still separate files.** `consumer-policy-bundle.yaml`,
`consumer-product-class.yaml` and the ceiling in
`consumer-product-governance.yaml` each state, on the consumer's own authority,
what it will admit. Held in one shared file the agreement would be
unfalsifiable — an edit would move both ends together and the admission check
would keep passing for a reason unrelated to what it verifies. Held in two,
editing either alone makes the inbound product's asserted regime fall outside
the consumer's entitlement and admission refuses. That refusal is the check.

**Every document in this directory carries a real `$schema` header.** There is
no `# no-schema: DeclaredArtifact` escape hatch and no
`# ccf-schema: deferred(…)` marker: SDK-owned classes point at their own
committed schema, and every deployment-authored class points at
`docs/schemas/ccf.declared-artifact.json` with its own `class_id`.
`agent-definition.yaml` and `prompt-artifact.yaml` point at plan 15-14's
author-versioned schemas and stay **out of the manifest**, because they register
through `register_versioned` (which holds the author's `artifact_version` claim
against content identity — the D-05 bump check) and `load_and_boot` registers
through `register_typed`, which does not.

`ccf.peering-trust-policy` deliberately does **not** appear as a header — see
`peering-trust.yaml` below: the class requires key material, which no authored
document can carry.

## examples/04-cross-process/artifacts/producer-manifest.yaml

- Surface: examples/04-cross-process/artifacts/producer-manifest.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — `producer_child.py` registered artifacts by hand in a 32-line prologue, including a loop that registered artifacts out of another artifact's body
- After: a `ccf.deployment-manifest` naming sixteen documents by `path`, `key`, `class_id` and `role`, plus the tenant and the backend kind
- Why: the set of artifacts in force is replay dimension 2, so it must be one enumerated, content-hashable document rather than a sequence of registration calls no artifact records
- Migration: write a manifest and call `load_and_boot`; the hand-written prologue plus `boot()` still works unchanged

## examples/04-cross-process/artifacts/consumer-manifest.yaml

- Surface: examples/04-cross-process/artifacts/consumer-manifest.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — `run.py` built the consumer's resolution spec from a nested `federation.entity_rule` block inside `a2a.yaml` and registered the rest by hand
- After: a second `ccf.deployment-manifest` naming eight documents, including the consumer's own resolution spec, policy bundle, admitted product class and peering entitlement
- Why: the consumer is a deployment in its own right; a shared manifest would assert that one artifact set was in force for both sides, which is exactly the thing the A2A trust boundary exists because it is not true
- Migration: give each process its own manifest rather than one bundle read twice

## examples/04-cross-process/artifacts/resolution-spec.yaml

- Surface: examples/04-cross-process/artifacts/resolution-spec.yaml
- Public surface: false
- Change type: reshaped
- Before: `ontology.yaml`, carrying `schema_version`, `artifact_version`, `tenant_id`, `entity_rules`, `relationship_rules`, `classification_attribute_by_class` and `similarity_corpus_attribute_by_class`
- After: a `ccf.resolution-spec` carrying `semver`, `entity_rules` and `relationship_rules` and nothing else
- Why: D-03 makes the class closed-world over resolution rules only; the two attribute maps moved to the operator-parameters documents that consume them, and `tenant_id` to the manifest
- Migration: rename the file, replace both root version keys with a single `semver`, and move each displaced block to the document named below

## examples/04-cross-process/artifacts/consumer-resolution-spec.yaml

- Surface: examples/04-cross-process/artifacts/consumer-resolution-spec.yaml
- Public surface: false
- Change type: reshaped
- Before: the `federation.entity_rule:` block nested inside `a2a.yaml`, translated by a bespoke `_consumer_resolution_spec` helper that read a differently-nested document
- After: a `ccf.resolution-spec` at the standard nesting, loaded by the consumer's manifest like any other
- Why: a resolution spec is a resolution spec whichever deployment authors it; the nesting variant existed only because the consumer had no manifest of its own, and it cost a 19-line translation helper
- Migration: lift the rule to a document root under `entity_rules:` and name it from your manifest

## examples/04-cross-process/artifacts/policy-bundle.yaml

- Surface: examples/04-cross-process/artifacts/policy-bundle.yaml
- Public surface: false
- Change type: reshaped
- Before: the `policy_bundle:` block inside `controlplane.yaml`, registered as a bare mapping under the long key `larkfield-estates/policy-bundle/situation-desk`
- After: a document in the open `DeclaredArtifact` envelope — `semver`, `class_id`, `declaration` — registered under the short manifest key `policy-bundle`
- Why: the SDK never invents a policy-bundle schema, but it owns the envelope, and the envelope is what gives a deployment-authored document a version lane and a checkable class identity
- Migration: wrap your bundle in `declaration:` and add `semver` and `class_id`. Both the content and the key change, so the pinned version changes

## examples/04-cross-process/artifacts/consumer-policy-bundle.yaml

- Surface: examples/04-cross-process/artifacts/consumer-policy-bundle.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — the consumer registered the *producer's* `policy_bundle` block from the same `controlplane.yaml` and separately recomputed its content hash as `producer_policy_version`
- After: the consumer's own envelope document, content-identical to the producer's and registered from the consumer's manifest
- Why: the pre-rewrite `assert policy_version == producer_policy_version` compared two reads of one file. As two documents the agreement is falsifiable, and it is exactly what the trust grant's `permitted_policy_regimes` entitles
- Migration: author the regime you entitle a peer to claim as your own document rather than reading the peer's

## examples/04-cross-process/artifacts/operator-parameters-traversal.yaml

- Surface: examples/04-cross-process/artifacts/operator-parameters-traversal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.traversal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.traversal` document
- Why: the SDK owns this parameter contract, so the document is validated against it rather than sitting inside an untyped bundle
- Migration: lift the block to a document root and add `semver`

## examples/04-cross-process/artifacts/operator-parameters-temporal.yaml

- Surface: examples/04-cross-process/artifacts/operator-parameters-temporal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.temporal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.temporal` document
- Why: as above
- Migration: lift the block to a document root and add `semver`

## examples/04-cross-process/artifacts/operator-parameters-policy.yaml

- Surface: examples/04-cross-process/artifacts/operator-parameters-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.policy:` block inside `controlplane.yaml`, with `classification_attribute_by_class` living in `ontology.yaml`
- After: a `ccf.operator-parameters.policy` document carrying both, and deliberately no `permitted_policy_bundle_versions`
- Why: one artifact, one consumer — the map is read by this operator and nothing else. The admitted-version set stays absent because it is a content hash minted at registration, which an adopter has no value to author (D-IMPL-76)
- Migration: move `classification_attribute_by_class` out of the ontology; pass the policy bundle key to `build_operator_registry`

## examples/04-cross-process/artifacts/operator-parameters-similarity.yaml

- Surface: examples/04-cross-process/artifacts/operator-parameters-similarity.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.similarity:` block inside `controlplane.yaml`, with `similarity_corpus_attribute_by_class` in `ontology.yaml` and `index_version` alongside the query
- After: a `ccf.operator-parameters.similarity` document carrying query, threshold, ranked classes and the corpus attribute map; the index version moves to the governance document
- Why: the corpus attribute map governs index *construction* and belongs with the artifact that declares it. The index version does not: it identifies a corpus state at a named boundary, not a parameter set
- Migration: move `similarity_corpus_attribute_by_class` out of the ontology; pass `similarity_index_version` to `build_operator_registry`

## examples/04-cross-process/artifacts/perspective.yaml

- Surface: examples/04-cross-process/artifacts/perspective.yaml
- Public surface: false
- Change type: reshaped
- Before: the `perspective:` block inside `controlplane.yaml`
- After: a `ccf.perspective` document
- Why: a parsed artifact of this class **is** a `Perspective` and passes straight into projection invocation with no field translation
- Migration: lift the block to a document root and add `semver`

## examples/04-cross-process/artifacts/product-class.yaml

- Surface: examples/04-cross-process/artifacts/product-class.yaml
- Public surface: false
- Change type: reshaped
- Before: the `product_class:` block inside `controlplane.yaml`, carrying `plan_id` and `product_ttl_seconds` and declaring no operator set
- After: a `ccf.product-class` document declaring `required_operator_keys` and `max_ttl_key`; `plan_id` and `product_ttl_seconds` move to the deployment's own governance document
- Why: `required_operator_keys` is the authored declared side of the lineage gate. Without it the projection returned the operator registry's own keys — `SituationPlan(required=operators.keys())` — and Gate 2 compared a value against itself
- Migration: add `required_operator_keys` naming the operator keys your projection depends on, and read it in your projection instead of the registry's keys

## examples/04-cross-process/artifacts/consumer-product-class.yaml

- Surface: examples/04-cross-process/artifacts/consumer-product-class.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — the consumer registered its admitted product class from the producer's `product_class:` block
- After: the consumer's own `ccf.product-class` document, naming the schema it will admit and its own TTL key
- Why: a consumer that read its admission criteria off the producer's declaration would be verifying a value against itself; `permitted_schema_names` in the trust grant is built from this
- Migration: author the classes you admit rather than inheriting the peer's

## examples/04-cross-process/artifacts/product-governance.yaml

- Surface: examples/04-cross-process/artifacts/product-governance.yaml
- Public surface: false
- Change type: reshaped
- Before: `max_ttl_seconds`, `product_ttl_seconds`, `index_version` and `plan_id` scattered through `controlplane.yaml`
- After: one deployment-authored document in the `DeclaredArtifact` envelope carrying all of them
- Why: these are values the SDK deliberately declines to own; the TTL ceiling and the product's own lifetime in particular stay two separately authored numbers, which is the whole reason Gate 3 is a check
- Migration: collect the equivalents from your Control Plane bundle into a declared document

## examples/04-cross-process/artifacts/consumer-product-governance.yaml

- Surface: examples/04-cross-process/artifacts/consumer-product-governance.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — the consumer registered `max_ttl_seconds` from the producer's bundle
- After: the consumer's own envelope document carrying its own ceiling
- Why: the ceiling a consumer enforces is the consumer's policy; a peer does not get to raise it by declaring a longer one
- Migration: author your own ceiling for every class you admit

## examples/04-cross-process/artifacts/producer-peering.yaml

- Surface: examples/04-cross-process/artifacts/producer-peering.yaml
- Public surface: false
- Change type: reshaped
- Before: the `producer:` block and parts of the `consumer:` block inside `a2a.yaml`, read by BOTH processes
- After: the producer's own envelope document, `role: register`, naming who it is on the wire, which key id it signs under, which producing agent it asserts, and where it emits
- Why: which identity a fabric emits under is a standing statement of what it was permitted to do. Split from the consumer's entitlement so the federation relationship is stated from both sides independently — one shared document would make the signature check pass for a reason unrelated to trust
- Migration: split your federation bundle along the trust boundary: what you assert goes in your Control Plane, what you entitle a peer to assert goes in theirs

## examples/04-cross-process/artifacts/peering-trust.yaml

- Surface: examples/04-cross-process/artifacts/peering-trust.yaml
- Public surface: false
- Change type: reshaped
- Before: the `consumer:` and `producer:` blocks inside `a2a.yaml`
- After: the consumer's own envelope document, `role: register`, carrying the trust-policy REQUEST — peer ids, the key identifier the peer may sign under, the producing agent it may assert, the ceilings, and the receive path
- Why: **this is deliberately not a `ccf.peering-trust-policy`, despite that class being real SDK mechanism.** `PeerTrustGrant` requires `signing_keys` — key MATERIAL, generated per run and never committed — so a standalone document of that class cannot be authored and a header naming it would be one its own class rejects. What is authorable is the request; `run.py` completes it with the run's public key. Same shape as `max_ttl_version`'s deliberate absence from a product-class document
- Migration: author the policy half of your trust entry and supply key material at registration time

## examples/04-cross-process/artifacts/federation-ingest.yaml

- Surface: examples/04-cross-process/artifacts/federation-ingest.yaml
- Public surface: false
- Change type: reshaped
- Before: the `federation:` block inside `a2a.yaml`, mixing the L1 mapping with the entity resolution rule
- After: a deployment-authored `role: register` document carrying the mapping only; the entity rule moved to `consumer-resolution-spec.yaml`
- Why: D-03 makes a resolution spec closed-world over resolution rules, so the rule and the mapping cannot share a document. What shape of peer claim a fabric turns into signal is a standing permission, hence `register`
- Migration: split the block: rules to your resolution spec, aliases and the source system id to a declared document

## examples/04-cross-process/artifacts/consumer-lineage.yaml

- Surface: examples/04-cross-process/artifacts/consumer-lineage.yaml
- Public surface: false
- Change type: reshaped
- Before: the `consumer.lineage:` block inside `a2a.yaml`
- After: a deployment-authored `role: load` document
- Why: the consumer's lineage at admission is a statement about its own state at one instant, not about what it was permitted to do. Its operators stay deliberately disjoint from the producer's, so the merged set proves union rather than replacement
- Migration: lift the block into a declared document and mark it `role: load`

## examples/04-cross-process/artifacts/decision.yaml

- Surface: examples/04-cross-process/artifacts/decision.yaml
- Public surface: false
- Change type: reshaped
- Before: the `decision:` block inside `controlplane.yaml`, with unquoted timestamps parsed by a bespoke `_instant` helper
- After: a deployment-authored `role: load` document with quoted instants
- Why: what instant one run asked about is not part of what the fabric was permitted to do. Quoting the timestamps removes the helper: the artifact loader suppresses PyYAML's timestamp resolver, so no zone-attaching translation is needed at the boundary
- Migration: quote your instants and mark the document `role: load`

## examples/04-cross-process/artifacts/consumer-decision.yaml

- Surface: examples/04-cross-process/artifacts/consumer-decision.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — the consumer read the producer's `decision.now`
- After: the consumer's own `role: load` document carrying its admission instant
- Why: a consumer reading the producer's clock would take freshness from the party whose freshness it is checking
- Migration: author your own admission instant

## examples/04-cross-process/artifacts/expected.yaml

- Surface: examples/04-cross-process/artifacts/expected.yaml
- Public surface: false
- Change type: reshaped
- Before: the `expected:` block inside `controlplane.yaml`, read by `producer_child.py`'s own `assert` statements
- After: a deployment-authored `role: load` document, read by `tests/examples/test_cross_process_output.py`; gains `role` and `excluded_entity_classes`
- Why: D-09 moves the example's assertions into `tests/`, and the expectations move with them; an expectation is not a permission, so it is never put in force
- Migration: move your `expected:` block into a declared document and read it from your relocated tests

## examples/04-cross-process/artifacts/events.yaml

- Surface: examples/04-cross-process/artifacts/events.yaml
- Public surface: false
- Change type: reshaped
- Before: a flat, bespoke shape — `source_system_id:` and `payload:` — translated into `SignalEnvelope` by a 12-line `_envelopes` helper that also had to attach UTC to naive timestamps
- After: a `ccf.signal-batch` adopting the SDK's own envelope vocabulary — `tenant_id`, `source: {system_id}`, `raw_payload` — parsed by `load_and_boot` and returned on `booted.artifacts`
- Why: a translation removed is one that cannot drift. `role: load` is FIXED by the SDK for this class: registering a batch would content-hash raw event data into replay dimension 2
- Migration: rename `source_system_id` to `source: {system_id}` and `payload` to `raw_payload`, add `tenant_id` per envelope, and delete your loader

## examples/04-cross-process/artifacts/agent-definition.yaml

- Surface: examples/04-cross-process/artifacts/agent-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `agent_definition:` block inside `agent.yaml`, alongside a `keys:` block and two inlined `referenced_artifacts`
- After: a `ccf.agent-definition` document whose **root is the artifact**, annotated with that class's committed schema, and absent from the manifest
- Why: the header checker validates the whole document against the class it names, so a file carrying both the artifact and its filing key cannot be annotated. It stays out of the manifest because `register_versioned`'s D-05 bump check would otherwise be silently dropped
- Migration: lift the definition to the document root, move the key into a deployment-authored document, and register it yourself

## examples/04-cross-process/artifacts/prompt-artifact.yaml

- Surface: examples/04-cross-process/artifacts/prompt-artifact.yaml
- Public surface: false
- Change type: reshaped
- Before: the `prompt_artifact:` block inside `prompt.yaml`, alongside a `keys:` block
- After: a `ccf.prompt-artifact` document whose root is the artifact, absent from the manifest for the same reason
- Why: one class, one document
- Migration: lift the prompt to the document root and register it with `register_versioned`

## examples/04-cross-process/artifacts/agent-policy-regime.yaml

- Surface: examples/04-cross-process/artifacts/agent-policy-regime.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.policy_regime:` block inlined inside `agent.yaml`
- After: its own envelope document, named by the manifest under the key the agent definition's versioned-URI ref resolves against
- Why: `agent.yaml` was three artifact classes in one file, and `producer_child.py` carried a loop that registered artifacts out of another artifact's body. The ref and the registration are now two independent statements of one key
- Migration: lift each `referenced_artifacts` entry into its own document and give the manifest an entry whose `key` is exactly the string the ref names

## examples/04-cross-process/artifacts/agent-debt-profile.yaml

- Surface: examples/04-cross-process/artifacts/agent-debt-profile.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.halflife_debt_profile:` block inlined inside `agent.yaml`
- After: its own envelope document, named by the manifest under the ref's key
- Why: as above. It stays on the open envelope rather than `ccf.debt-profile` because a versioned-URI ref names a deployment key rather than an SDK artifact class
- Migration: as above

## examples/04-cross-process/artifacts/agent-registration.yaml

- Surface: examples/04-cross-process/artifacts/agent-registration.yaml
- Public surface: false
- Change type: reshaped
- Before: the `keys:` blocks at the top of `agent.yaml` and `prompt.yaml`
- After: one deployment-authored `role: load` document naming all four Control Plane keys
- Why: a key is where a document is *filed*, not part of what it says, and the author-versioned documents' roots had to become their artifacts
- Migration: collect the keys your driver reads into a declared document
