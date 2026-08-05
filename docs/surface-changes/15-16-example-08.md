# 15-16 — examples/08-e2e-demo reshaped to typed artifact documents

Plan 15-16 adds **no** public Python surface: it touches `examples/`, `public/`
and `tests/` only. Every entry below is therefore `Public surface: false` with
`Change type: reshaped`, and each `Surface` value is the repo-relative path of a
changed artifact document. An artifact-document format change is real and an
adopter who copied this demo's artifacts must act on it, but it can never appear
in the `__all__`-derived manifest diff.

The six multi-artifact bundles the demo shipped (`ontology.yaml`,
`controlplane.yaml`, `halflife.yaml`, `agent.yaml`, `skills.yaml`,
`prompt.yaml`) are now twenty-one typed, closed-world, `$schema`-annotated
documents — eighteen of them enumerated by one deployment manifest, three
author-versioned and registered by `run.py` itself.

**Exactly one document in this directory is NOT annotated.** `scenario.yaml`
carries a `# ccf-schema: deferred(15-21) …` first line, and that deferral is
permanent rather than debt: it is not a CCF artifact class at all — it is
`generator.py`'s input, describing the synthetic world that exists before any
fabric does — and it carries YAML floats (the noise amount bands) that the
artifact loader refuses by design. No envelope can accept it without changing
the data and every pinned checksum with it.

**Every other document carries a real `$schema` header, including the three
author-versioned ones.** `agent-definition.yaml`, `prompt-artifact.yaml` and
`skill-catalog-entry.yaml` point at `docs/schemas/ccf.agent-definition.json`,
`ccf.prompt-artifact.json` and `ccf.skill-catalog-entry.json` — plan 15-14's
author-versioned schema set, committed *without* making those classes
manifest-addressable. That distinction is the whole point and is worth stating
plainly for adopters:

> A class can have a committed schema and still be absent from
> `SDK_ARTIFACT_CLASSES`. `ccf.agent-definition`, `ccf.prompt-artifact` and
> `ccf.skill-catalog-entry` carry the author's own `artifact_version` and
> register through `register_versioned`, which holds that claim against the
> document's content identity — the D-05 bump check. `load_and_boot` registers
> through `register_typed`, which does not run it. So naming one of these in a
> manifest would parse perfectly and silently drop the governance the class
> exists to carry. They are authored by hand and therefore get schemas; they are
> not manifest-addressable and therefore stay out of the manifest.

`ccf.skill-grant` has a committed schema too, and this example still does not
use it as a header — see `skill-dispatch.yaml` below for why (the class requires
a derived hash that no authored document can carry).

## examples/08-e2e-demo/artifacts/manifest.yaml

- Surface: examples/08-e2e-demo/artifacts/manifest.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — `run.py` registered artifacts by hand in a 41-line prologue, and registered two more out of another artifact's body
- After: a `ccf.deployment-manifest` naming fifteen documents by `path`, `key`, `class_id` and `role`, plus the tenant and the backend kind
- Why: the set of artifacts in force is replay dimension 2, so it must be one enumerated, content-hashable document rather than a sequence of registration calls no artifact records
- Migration: write a manifest and call `load_and_boot`; the hand-written prologue plus `boot()` still works unchanged

## examples/08-e2e-demo/artifacts/resolution-spec.yaml

- Surface: examples/08-e2e-demo/artifacts/resolution-spec.yaml
- Public surface: false
- Change type: reshaped
- Before: `ontology.yaml`, carrying `schema_version`, `artifact_version`, `tenant_id`, `entity_rules`, `relationship_rules`, `classification_attribute_by_class`, `similarity_corpus_attribute_by_class` and the whole `ingest:` block
- After: a `ccf.resolution-spec` carrying `semver`, `entity_rules` and `relationship_rules` and nothing else
- Why: D-03 makes the class closed-world over resolution rules only; the two attribute maps moved to the operator-parameters documents that consume them, `tenant_id` to the manifest, and the L1 mapping to its own document
- Migration: rename the file, replace both root version keys with a single `semver`, and move each displaced block to the document named below

## examples/08-e2e-demo/artifacts/ingest-spec.yaml

- Surface: examples/08-e2e-demo/artifacts/ingest-spec.yaml
- Public surface: false
- Change type: reshaped
- Before: the `ingest:` block inside `ontology.yaml`
- After: a deployment-authored `DeclaredArtifact` document, `role: register`
- Why: this example ingests from three live SQLite source systems rather than from a `ccf.signal-batch`, so there is no static batch document to name — but the *mapping* is declarable and it is a standing statement of what the fabric admits, which the D-IMPL-80 test resolves as `register`
- Migration: lift the block into a declared document and read it off `booted.artifacts`

## examples/08-e2e-demo/artifacts/half-life-table.yaml

- Surface: examples/08-e2e-demo/artifacts/half-life-table.yaml
- Public surface: false
- Change type: reshaped
- Before: the `half_life_table:` block nested inside `halflife.yaml`
- After: its own `ccf.half-life-table` document
- Why: one artifact class, one document — two classes in one file cannot both carry an honest `$schema` header, because each annotates the other's keys as errors
- Migration: lift the nested mapping to the document root

## examples/08-e2e-demo/artifacts/debt-profile.yaml

- Surface: examples/08-e2e-demo/artifacts/debt-profile.yaml
- Public surface: false
- Change type: reshaped
- Before: the `debt_profile:` block nested inside `halflife.yaml`
- After: its own `ccf.debt-profile` document
- Why: same as the half-life table — one class, one document, one version lane
- Migration: lift the nested mapping to the document root

## examples/08-e2e-demo/artifacts/operator-parameters-traversal.yaml

- Surface: examples/08-e2e-demo/artifacts/operator-parameters-traversal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.traversal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.traversal` document
- Why: the SDK owns this parameter contract, so the document is validated against it rather than sitting inside an untyped bundle
- Migration: lift the block to a document root and add `semver`

## examples/08-e2e-demo/artifacts/operator-parameters-temporal.yaml

- Surface: examples/08-e2e-demo/artifacts/operator-parameters-temporal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.temporal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.temporal` document
- Why: as above
- Migration: lift the block to a document root and add `semver`

## examples/08-e2e-demo/artifacts/operator-parameters-policy.yaml

- Surface: examples/08-e2e-demo/artifacts/operator-parameters-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.policy:` block inside `controlplane.yaml`, with `classification_attribute_by_class` living in `ontology.yaml`
- After: a `ccf.operator-parameters.policy` document carrying both, and deliberately no `permitted_policy_bundle_versions`
- Why: one artifact, one consumer — the map is read by this operator and nothing else. The admitted-version set stays absent because it is a content hash minted at registration, which an adopter has no value to author (D-IMPL-76)
- Migration: move `classification_attribute_by_class` out of the ontology into this document; pass the policy bundle key to `build_operator_registry`

## examples/08-e2e-demo/artifacts/operator-parameters-similarity.yaml

- Surface: examples/08-e2e-demo/artifacts/operator-parameters-similarity.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.similarity:` block inside `controlplane.yaml`, with `similarity_corpus_attribute_by_class` in `ontology.yaml` and `index_version` alongside the query
- After: a `ccf.operator-parameters.similarity` document carrying query, threshold, ranked classes and the corpus attribute map; the index version moves out
- Why: the corpus attribute map governs index *construction* and belongs with the artifact that declares it. The index version does not: it identifies a corpus state at a named boundary, not a parameter set
- Migration: move `similarity_corpus_attribute_by_class` out of the ontology; pass `similarity_index_version` to `build_operator_registry`

## examples/08-e2e-demo/artifacts/perspective.yaml

- Surface: examples/08-e2e-demo/artifacts/perspective.yaml
- Public surface: false
- Change type: reshaped
- Before: the `perspective:` block inside `controlplane.yaml`
- After: a `ccf.perspective` document
- Why: a parsed artifact of this class **is** a `Perspective` and passes straight into projection invocation with no field translation
- Migration: lift the block to a document root and add `semver`

## examples/08-e2e-demo/artifacts/product-class.yaml

- Surface: examples/08-e2e-demo/artifacts/product-class.yaml
- Public surface: false
- Change type: reshaped
- Before: the `product_class:` block inside `controlplane.yaml`, carrying `plan_id` and `product_ttl_seconds` and declaring no operator set
- After: a `ccf.product-class` document declaring `required_operator_keys` and `max_ttl_key`; `plan_id` and `product_ttl_seconds` move to the deployment's own governance document
- Why: `required_operator_keys` is the authored declared side of the lineage gate. Without it the projection returned the operator registry's own keys — `PaymentNetworkPlan(required=operators.keys())` — and Gate 2 compared a value against itself
- Migration: add `required_operator_keys` naming the operator keys your projection depends on, and read it in your projection instead of the registry's keys

## examples/08-e2e-demo/artifacts/product-governance.yaml

- Surface: examples/08-e2e-demo/artifacts/product-governance.yaml
- Public surface: false
- Change type: reshaped
- Before: `max_ttl_seconds`, `product_ttl_seconds`, `index_version`, `plan_id` and `artifacts.replay_record_class` scattered through `controlplane.yaml`
- After: one deployment-authored document in the `DeclaredArtifact` envelope carrying all of them
- Why: these are values the SDK deliberately declines to own; the TTL ceiling and the product's own lifetime in particular stay two separately authored numbers, which is the whole reason Gate 3 is a check
- Migration: collect the equivalents from your Control Plane bundle into a declared document

## examples/08-e2e-demo/artifacts/policy-bundle.yaml

- Surface: examples/08-e2e-demo/artifacts/policy-bundle.yaml
- Public surface: false
- Change type: reshaped
- Before: the `policy_bundle:` block inside `controlplane.yaml`, registered as a bare mapping under the key `meridian-bank/policy-bundle/financial-crime-analyst`
- After: a document in the open `DeclaredArtifact` envelope — `semver`, `class_id`, `declaration` — registered under the short manifest key `policy-bundle`
- Why: the SDK never invents a policy-bundle schema, but it does own the envelope, and the envelope is what gives a deployment-authored document a version lane and a checkable class identity
- Migration: wrap your bundle in `declaration:` and add `semver` and `class_id`. **Note that both the content and the Control Plane key change, so the pinned version changes and any recorded replay reference over this bundle is regenerated** — see the narration note below

## examples/08-e2e-demo/artifacts/agent-policy-regime.yaml

- Surface: examples/08-e2e-demo/artifacts/agent-policy-regime.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.policy_regime:` block inlined inside `agent.yaml`
- After: its own envelope document, named by the manifest under the key the agent definition's versioned-URI ref resolves against
- Why: `agent.yaml` was three artifact classes in one file, and `run.py` carried a loop that registered artifacts out of another artifact's body. The ref and the registration are now two independent statements of one fact
- Migration: lift each `referenced_artifacts` entry into its own document and give the manifest an entry whose `key` is exactly the string the ref names

## examples/08-e2e-demo/artifacts/agent-debt-profile.yaml

- Surface: examples/08-e2e-demo/artifacts/agent-debt-profile.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.halflife_debt_profile:` block inlined inside `agent.yaml`
- After: its own envelope document, named by the manifest under the ref's key
- Why: as above. It stays distinct from the fabric's `ccf.debt-profile`: what staleness the fabric tolerates and what staleness one agent tolerates are two statements
- Migration: as above

## examples/08-e2e-demo/artifacts/decision.yaml

- Surface: examples/08-e2e-demo/artifacts/decision.yaml
- Public surface: false
- Change type: reshaped
- Before: the `decision:` block inside `controlplane.yaml`, plus `demonstration:` inside `halflife.yaml`
- After: one deployment-authored `role: load` document carrying all four instants and the freshness demonstration
- Why: what instant one run asked about is not part of what the fabric was permitted to do, so it is parsed and returned rather than registered into replay dimension 2
- Migration: move your decision instants into a declared document and mark it `role: load`

## examples/08-e2e-demo/artifacts/expected.yaml

- Surface: examples/08-e2e-demo/artifacts/expected.yaml
- Public surface: false
- Change type: reshaped
- Before: the `expected:` block inside `controlplane.yaml`, read by `run.py`'s `_require` calls
- After: a deployment-authored `role: load` document, read by `tests/examples/test_e2e_demo_output.py`
- Why: D-09 moves the example's assertions into `tests/`, and the expectations have to move with them; an expectation is not a permission, so it is never put in force
- Migration: move your `expected:` block into a declared document and read it from your relocated tests

## examples/08-e2e-demo/artifacts/expected_output.txt

- Surface: examples/08-e2e-demo/artifacts/expected_output.txt
- Public surface: false
- Change type: reshaped
- Before: 49 lines of committed transcript, byte-compared by `run.py` itself
- After: byte-compared by `tests/examples/test_e2e_demo_output.py`; **one line regenerated** — the Stage 6 `replay record` content address
- Why: the reshape changed the policy bundle's content (it now carries the envelope's `semver`/`class_id`/`declaration`) and its Control Plane key (`policy-bundle` rather than the long namespaced one). Both land in the replay record's dimension-2 binding, so the record's own content hash moves. No other line of the transcript changes, and the regeneration is a reviewed event under this plan's blocking checkpoint
- Migration: none for adopters; if your own transcript pins a replay address, expect to regenerate it when any registered artifact's content or key changes


## examples/08-e2e-demo/artifacts/agent-definition.yaml

- Surface: examples/08-e2e-demo/artifacts/agent-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `agent_definition:` block inside `agent.yaml`, alongside a `keys:` block and two inlined `referenced_artifacts`
- After: a `ccf.agent-definition` document whose **root is the artifact**, annotated with that class's committed schema
- Why: the header checker validates the whole document against the class it names, so a file carrying both the artifact and its filing key cannot be annotated. The key moved to `agent-registration.yaml`
- Migration: lift the definition to the document root and move the Control Plane key into a deployment-authored document

## examples/08-e2e-demo/artifacts/prompt-artifact.yaml

- Surface: examples/08-e2e-demo/artifacts/prompt-artifact.yaml
- Public surface: false
- Change type: reshaped
- Before: the `prompt_artifact:` block inside `prompt.yaml`, alongside `keys:` and the `--live` provider configuration
- After: a `ccf.prompt-artifact` document whose root is the artifact
- Why: one class, one document. The template is what the model is asked; the endpoint and timeouts are which model is asked — never the same artifact
- Migration: lift the prompt to the document root; move provider configuration to its own document

## examples/08-e2e-demo/artifacts/skill-catalog-entry.yaml

- Surface: examples/08-e2e-demo/artifacts/skill-catalog-entry.yaml
- Public surface: false
- Change type: reshaped
- Before: the single entry under `skills:` inside `skills.yaml`, alongside the grant, the actors and the dispatch
- After: a `ccf.skill-catalog-entry` document whose root is the artifact
- Why: `skills.yaml` was three things in one file and could carry no honest header for any of them
- Migration: lift the entry to the document root

## examples/08-e2e-demo/artifacts/skill-dispatch.yaml

- Surface: examples/08-e2e-demo/artifacts/skill-dispatch.yaml
- Public surface: false
- Change type: reshaped
- Before: the `grant:`, `actors:` and `dispatch:` blocks inside `skills.yaml`
- After: one deployment-authored `role: load` document in the `DeclaredArtifact` envelope, carrying `grant_request`, `requesting_actor` and `dispatch`
- Why: **this is deliberately not a `ccf.skill-grant`, despite that class having a committed schema.** `SkillGrant` requires `agent_definition_hash`, which is derived identity computed by mechanism at request time — a hash is never an artifact value, so a standalone document of that class cannot be authored and a `ccf.skill-grant` header would be one its own class rejects. What *is* authorable is the grant request, and `run.py` completes it by supplying the hash
- Migration: rename your `grant:` block to `grant_request:` inside a declared document, and leave the derived hash out

## examples/08-e2e-demo/artifacts/agent-registration.yaml

- Surface: examples/08-e2e-demo/artifacts/agent-registration.yaml
- Public surface: false
- Change type: reshaped
- Before: the `keys:` blocks at the top of `agent.yaml` and `prompt.yaml`
- After: one deployment-authored `role: load` document naming both Control Plane keys
- Why: a key is where a document is *filed*, not part of what it says, and the author-versioned documents' roots had to become their artifacts. The skill catalog entry's key is deliberately absent — `SkillCatalog` derives it from the entry's own tenant and name, so authoring one would be a second, drifting statement of a value mechanism already owns
- Migration: collect the keys your driver reads into a declared document

## examples/08-e2e-demo/artifacts/live-narration.yaml

- Surface: examples/08-e2e-demo/artifacts/live-narration.yaml
- Public surface: false
- Change type: reshaped
- Before: the `live:` block inside `prompt.yaml`
- After: one deployment-authored `role: load` document carrying the provider defaults and runner limits
- Why: one class, one document; and an endpoint is deployment *environment*, which is why the environment variables still override these recorded defaults
- Migration: lift the block into a declared document
