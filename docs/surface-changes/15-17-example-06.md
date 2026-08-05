# 15-17 — examples/06-decision-replay reshaped to typed artifact documents

Plan 15-17 adds **no** public Python surface: it touches `examples/`, `public/`
and `tests/` only. Every entry below is therefore `Public surface: false`, and
each `Surface` value is the repo-relative path of a changed artifact document or
of the example's own code. An artifact-document format change is real and an
adopter who copied this example's artifacts must act on it, but it can never
appear in the `__all__`-derived manifest diff.

The nine multi-artifact bundles this example shipped (`ontology.yaml`,
`controlplane.yaml`, `agent.yaml`, `prompt.yaml`, `skills.yaml`, `task.yaml`,
`workflow.yaml`, `hitl.yaml`, `scope_mapping.yaml`) are now twenty-eight typed,
closed-world documents — twenty-one enumerated by one deployment manifest, five
author-versioned and registered by `run.py`, and two SDK-owned classes the
manifest cannot address at all.

## Two documents carry a deferral marker, and it is not decorative

`hitl-policy.yaml` and `scope-mapping.yaml` carry
`# ccf-schema: deferred(15-21) …` first lines instead of `$schema` headers. This
is recorded here because the plan requires it to be recorded here, on top of the
marker rather than in place of it.

The reason is a real gap in the schema-export surface, not an omission in this
example. `ccf.hitl-policy` and `ccf.scope-mapping` are **SDK-owned classes with
no committed schema**: they are absent from `SDK_ARTIFACT_CLASSES` (so a manifest
cannot name them) and absent from `author_versioned_classes()` (so
`tools/dump_schemas.py` emits nothing for them). There is therefore no honest
`$schema` target for either. The `DeclaredArtifact` envelope route is *not* an
escape hatch here: these documents genuinely ARE their SDK classes, and wrapping
them in an envelope would hide each class's own contract from the checker, which
is the anti-pattern in reverse.

`ccf.scope-mapping` additionally lives in `/runtime`, so emitting a schema for it
cannot follow the `/src`-rooted route the other classes use.

A future plan closing this would add a third schema-emission bucket — SDK-owned,
`register_typed`, not manifest-addressable — alongside 15-13's envelope and
15-14's author-versioned set. That is out of this plan's scope and out of a
concurrent wave's blast radius; 15-21 owns the tree-wide gate that will have to
rule on it.

## Nothing on disk was regenerated

There is no committed expected-output file, no pinned checksum manifest, and no
stored replay fixture under `examples/06-decision-replay/`. Every replay record,
content address and grant-set hash this example produces is written into a
per-run temporary directory and asserted against within the same run. The record
content addresses **did** move — the manifest's short unnamespaced
`policy-bundle` key replaces the long namespaced one, and the policy bundle is
now a `DeclaredArtifact` envelope document rather than a bare mapping — but no
committed file records the old values, so there is no `behavior`-class entry to
make and no fixture diff to review.

---

## examples/06-decision-replay/artifacts/manifest.yaml

- Surface: examples/06-decision-replay/artifacts/manifest.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — `run.py` registered artifacts by hand in a 41-line prologue, including a nested loop over each definition's `referenced_artifacts` block
- After: a `ccf.deployment-manifest` naming twenty-one documents by `path`, `key`, `class_id` and `role`, plus the tenant and the backend kind
- Why: the set of artifacts in force is replay dimension 2, and this is the example whose subject is that record — a registration sequence no artifact records could not be resolved back out of it
- Migration: write a manifest and call `load_and_boot`; the hand-written prologue plus `boot()` still works unchanged

## examples/06-decision-replay/artifacts/resolution-spec.yaml

- Surface: examples/06-decision-replay/artifacts/resolution-spec.yaml
- Public surface: false
- Change type: reshaped
- Before: `ontology.yaml`, carrying `schema_version`, `artifact_version`, `tenant_id`, `entity_rules`, `relationship_rules`, `classification_attribute_by_class` and `similarity_corpus_attribute_by_class`
- After: a `ccf.resolution-spec` carrying `semver`, `entity_rules` and `relationship_rules` and nothing else
- Why: D-03 makes the class closed-world over resolution rules only; the two attribute maps moved to the operator-parameters documents that consume them, and `tenant_id` to the manifest
- Migration: rename the file, replace both root version keys with a single `semver`, and move each displaced block to the document named below

## examples/06-decision-replay/artifacts/policy-bundle.yaml

- Surface: examples/06-decision-replay/artifacts/policy-bundle.yaml
- Public surface: false
- Change type: reshaped
- Before: the `policy_bundle:` block inside `controlplane.yaml`, registered as a bare mapping under the namespaced key `boreal-grid/policy-bundle/grid-operations`
- After: a deployment-authored `DeclaredArtifact` document under the short manifest key `policy-bundle`
- Why: one class, one document, one `$schema` header; the short key is this deployment's own vocabulary and matches every other rewritten example (15-13 R3, ruled at 15-16's checkpoint)
- Migration: lift the block under `declaration:`, add `semver` and `class_id`, and update any code naming the long key — including the `PolicyBinding(key=...)` the replay record carries

## examples/06-decision-replay/artifacts/operator-parameters-traversal.yaml

- Surface: examples/06-decision-replay/artifacts/operator-parameters-traversal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.traversal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.traversal` document
- Why: the SDK owns this parameter contract, so the document is validated against it rather than sitting inside an untyped bundle
- Migration: lift the block to a document root and add `semver`

## examples/06-decision-replay/artifacts/operator-parameters-temporal.yaml

- Surface: examples/06-decision-replay/artifacts/operator-parameters-temporal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.temporal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.temporal` document
- Why: as above
- Migration: lift the block to a document root and add `semver`

## examples/06-decision-replay/artifacts/operator-parameters-policy.yaml

- Surface: examples/06-decision-replay/artifacts/operator-parameters-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.policy:` block inside `controlplane.yaml`, plus `classification_attribute_by_class` from `ontology.yaml`
- After: a `ccf.operator-parameters.policy` document carrying both
- Why: one artifact, one consumer (D-03) — the classification map is read by this operator and by nothing else
- Migration: lift both blocks into one document root, add `semver`, and do not author `permitted_policy_bundle_versions` (D-IMPL-76 — `build_operator_registry` completes it from the adopter-passed pins)

## examples/06-decision-replay/artifacts/operator-parameters-similarity.yaml

- Surface: examples/06-decision-replay/artifacts/operator-parameters-similarity.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.similarity:` block inside `controlplane.yaml`, plus `similarity_corpus_attribute_by_class` from `ontology.yaml`
- After: a `ccf.operator-parameters.similarity` document carrying both, **without** `index_version`
- Why: the corpus's version identity is a property of graph state at a named boundary, not of these parameters (INV-CH7-27), so it moved to `product-governance.yaml` where the boundary is
- Migration: lift both blocks, add `semver`, and move `index_version` to wherever your deployment names its boundary

## examples/06-decision-replay/artifacts/perspective.yaml

- Surface: examples/06-decision-replay/artifacts/perspective.yaml
- Public surface: false
- Change type: reshaped
- Before: the `perspective:` block inside `controlplane.yaml`
- After: a `ccf.perspective` document
- Why: one class, one document
- Migration: lift the block to a document root and add `semver`

## examples/06-decision-replay/artifacts/product-class.yaml

- Surface: examples/06-decision-replay/artifacts/product-class.yaml
- Public surface: false
- Change type: reshaped
- Before: the `product_class:` block inside `controlplane.yaml` — carrying `plan_id` and `product_ttl_seconds` and carrying **no** `required_operator_keys`
- After: a `ccf.product-class` document carrying `required_operator_keys`, `max_ttl_key` and the schema lane
- Why: `required_operator_keys` is the AUTHORED declared side of Gate 2 (INV-CH7-47), and this example had the tautology at **two** sites — the record phase's plan and the replay environment's reconstruction of it both took `required` from the operator registry's own keys, so the gate compared a value against itself in the original decision *and* in its reproduction
- Migration: author `required_operator_keys` and pass it to your plan; never `operators.keys()`

## examples/06-decision-replay/artifacts/product-governance.yaml

- Surface: examples/06-decision-replay/artifacts/product-governance.yaml
- Public surface: false
- Change type: reshaped
- Before: `max_ttl_seconds`, `product_ttl_seconds`, `plan_id`, the similarity `index_version` and `artifacts.replay_record_class`, scattered across `controlplane.yaml`
- After: one deployment-authored `DeclaredArtifact` gathering the values the SDK declines to own
- Why: these are the deployment's numbers and identifiers, not an SDK contract; keeping them together and typed is what lets the rest of the directory be closed-world
- Migration: gather them under one `declaration:` and read them off `booted.artifacts`

## examples/06-decision-replay/artifacts/agent-policy-regime.yaml

- Surface: examples/06-decision-replay/artifacts/agent-policy-regime.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.policy_regime` block inside `agent.yaml`, registered by a loop in `run.py` over every definition's `referenced_artifacts`
- After: its own `DeclaredArtifact`, `role: register` in the manifest under the key the agent definition's axis-4 ref resolves against
- Why: the ref and the registration become two independent statements of one fact, and the registration loop disappears
- Migration: lift each `referenced_artifacts` entry into its own document and give it a manifest entry keyed by the ref it answers

## examples/06-decision-replay/artifacts/agent-debt-profile.yaml

- Surface: examples/06-decision-replay/artifacts/agent-debt-profile.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.halflife_debt_profile` block inside `agent.yaml`
- After: its own `DeclaredArtifact`, `role: register`, under the axis-5 ref's key
- Why: as above
- Migration: as above

## examples/06-decision-replay/artifacts/task-skill.yaml

- Surface: examples/06-decision-replay/artifacts/task-skill.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.collect_telemetry_skill` block inside `task.yaml`
- After: its own `DeclaredArtifact`, `role: register`, under the key the task's first step ref names
- Why: what a workflow step may invoke is a standing statement of what the fabric may do
- Migration: as above

## examples/06-decision-replay/artifacts/approval-policy.yaml

- Surface: examples/06-decision-replay/artifacts/approval-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.shift_supervisor_policy` block inside `workflow.yaml`
- After: its own `DeclaredArtifact`, `role: register`, under the key `gate_policies` names
- Why: who may approve at a gate is precisely what the fabric was permitted to do
- Migration: as above

## examples/06-decision-replay/artifacts/agent-definition.yaml

- Surface: examples/06-decision-replay/artifacts/agent-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `agent_definition:` block inside `agent.yaml`, alongside that file's `keys:` and `referenced_artifacts:` blocks
- After: a `ccf.agent-definition` whose document root IS the artifact, carrying a real `$schema` header (plan 15-14's author-versioned set) and **not** in the manifest
- Why: the checker validates the whole document against the class its header names, so the root had to become the artifact; the class stays out of the manifest because `load_and_boot`'s `register_typed` does not run the D-05 bump check that `register_versioned` does
- Migration: split the file so the definition is the root; move its Control Plane key to a separate filing document

## examples/06-decision-replay/artifacts/prompt-artifact.yaml

- Surface: examples/06-decision-replay/artifacts/prompt-artifact.yaml
- Public surface: false
- Change type: reshaped
- Before: the `prompt_artifact:` block inside `prompt.yaml`
- After: a `ccf.prompt-artifact` at the document root, author-versioned, out of the manifest
- Why: as above
- Migration: as above

## examples/06-decision-replay/artifacts/skill-catalog-entry.yaml

- Surface: examples/06-decision-replay/artifacts/skill-catalog-entry.yaml
- Public surface: false
- Change type: reshaped
- Before: the `skills.feeder_load_metrics:` block inside `skills.yaml`
- After: a `ccf.skill-catalog-entry` at the document root, author-versioned, out of the manifest
- Why: as above. Its Control Plane key is deliberately not authored anywhere — `SkillCatalog` derives it from the entry's own tenant and name
- Migration: as above

## examples/06-decision-replay/artifacts/task-definition.yaml

- Surface: examples/06-decision-replay/artifacts/task-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `task_definition:` block inside `task.yaml`
- After: a `ccf.task-definition` at the document root, author-versioned, out of the manifest
- Why: as above
- Migration: as above

## examples/06-decision-replay/artifacts/workflow-definition.yaml

- Surface: examples/06-decision-replay/artifacts/workflow-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `workflow_definition:` block inside `workflow.yaml`
- After: a `ccf.workflow-definition` at the document root, author-versioned, out of the manifest
- Why: as above
- Migration: as above

## examples/06-decision-replay/artifacts/hitl-policy.yaml

- Surface: examples/06-decision-replay/artifacts/hitl-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `hitl_policy:` block inside `hitl.yaml`
- After: a `ccf.hitl-policy` at the document root, registered by `run.py`, carrying a `# ccf-schema: deferred(15-21) …` first line
- Why: one class, one document; the deferral is because the class has no committed schema and no honest header exists — see the section above
- Migration: lift the block to the root and register it with `register_typed`; do not put it in a manifest, which would resolve it to the open envelope and leave the transport reading the wrong type back

## examples/06-decision-replay/artifacts/scope-mapping.yaml

- Surface: examples/06-decision-replay/artifacts/scope-mapping.yaml
- Public surface: false
- Change type: reshaped
- Before: `scope_mapping.yaml`, carrying both a `keys:` block and a nested `scope_mapping:` block
- After: a `ccf.scope-mapping` at the document root, registered by `run.py`, carrying a deferral marker for the same reason
- Why: as above; the key moved to `agent-registration.yaml`
- Migration: as above

## examples/06-decision-replay/artifacts/agent-registration.yaml

- Surface: examples/06-decision-replay/artifacts/agent-registration.yaml
- Public surface: false
- Change type: reshaped
- Before: the `keys:` blocks scattered across `agent.yaml`, `prompt.yaml`, `task.yaml`, `workflow.yaml`, `hitl.yaml` and `scope_mapping.yaml`
- After: one deployment-authored `DeclaredArtifact`, `role: load`, naming where each driver-registered document files
- Why: a key is where a document is FILED, not part of what it says — and once each document's root must BE its artifact, there is nowhere else for the key to live. `role: load` because putting the filing scheme in force would content-hash it into replay dimension 2 alongside the artifacts it files
- Migration: gather the keys into one document and read them off `booted.artifacts`

## examples/06-decision-replay/artifacts/skill-dispatch.yaml

- Surface: examples/06-decision-replay/artifacts/skill-dispatch.yaml
- Public surface: false
- Change type: reshaped
- Before: the `grant:`, `callable:`, `dispatch:` and `actors:` blocks inside `skills.yaml`
- After: one deployment-authored `DeclaredArtifact`, `role: load`, whose `grant_request` is the authorable half of a `ccf.skill-grant`
- Why: `SkillGrant` requires `agent_definition_hash`, which is derived identity computed at request time — a hash is never an artifact value, so a standalone `ccf.skill-grant` document cannot be authored even though that class has a committed schema. `role: load` because the ledger audits the grant independently when it admits it
- Migration: author the request, let `run.py` supply the hash

## examples/06-decision-replay/artifacts/hitl-drive.yaml

- Surface: examples/06-decision-replay/artifacts/hitl-drive.yaml
- Public surface: false
- Change type: reshaped
- Before: the `approver:`, `drive:`, `node_outputs:`, `debt_factors:`, `clock:` and `override:` blocks inside `hitl.yaml`
- After: one deployment-authored `DeclaredArtifact`, `role: load`, with `clock.base` moved to `decision.yaml`
- Why: what one run's human actors did is not a standing statement of what the fabric was permitted to do — the POLICY governing them is, and that is registered separately
- Migration: split the policy out, move the clock seed to your decision-inputs document, and read the rest off `booted.artifacts`

## examples/06-decision-replay/artifacts/tokens.yaml

- Surface: examples/06-decision-replay/artifacts/tokens.yaml
- Public surface: false
- Change type: reshaped
- Before: a bare `tokens:` list at the document root, re-read off disk by `ArtifactTokenSource` on every lookup
- After: a deployment-authored `DeclaredArtifact`, `role: load`, parsed once by `load_and_boot` and handed to the token source
- Why: one class, one document — and one parse, so there is no second read of the file to drift from the first
- Migration: wrap the list under `declaration:` and pass the parsed entries in rather than a path

## examples/06-decision-replay/artifacts/decision.yaml

- Surface: examples/06-decision-replay/artifacts/decision.yaml
- Public surface: false
- Change type: reshaped
- Before: the `decision:` block inside `controlplane.yaml`, plus `clock.base` from `hitl.yaml`
- After: a deployment-authored `DeclaredArtifact`, `role: load`, carrying the boundary, the decision instant and the clock seed
- Why: what instant one run asked about is not part of what the fabric was permitted to do; the clock seed joins them because it is the same kind of value and must be readable **before** the first registration
- Migration: gather the instants into one document; read it through `load_artifact` ahead of `load_and_boot` if your audit clock is artifact-seeded

## examples/06-decision-replay/artifacts/expected.yaml

- Surface: examples/06-decision-replay/artifacts/expected.yaml
- Public surface: false
- Change type: reshaped
- Before: the `expected:` block inside `controlplane.yaml`
- After: a deployment-authored `DeclaredArtifact`, `role: load`
- Why: an expectation is not a permission, and the relocated test module needs a source for its domain expectations other than itself
- Migration: lift the block into its own document

## examples/06-decision-replay/artifacts/replay-probes.yaml

- Surface: examples/06-decision-replay/artifacts/replay-probes.yaml
- Public surface: false
- Change type: reshaped
- Before: the `artifacts:` block inside `controlplane.yaml`
- After: a deployment-authored `DeclaredArtifact`, `role: load`, carrying the store's class names and the two negative probes' values; `replay_record_class` moved to `product-governance.yaml`
- Why: a probe is not a permission — putting it in force would say the fabric was permitted to resolve an unregistered version, which is the opposite of what the probe proves
- Migration: split governance values from probe values and read both off `booted.artifacts`

## examples/06-decision-replay/artifacts/events.yaml

- Surface: examples/06-decision-replay/artifacts/events.yaml
- Public surface: false
- Change type: reshaped
- Before: a flat shape (`source_system_id`, `payload`, `schema_version`/`artifact_version`) that `run.py` translated envelope by envelope in a 12-line helper
- After: a `ccf.signal-batch` in the SDK's own envelope vocabulary (`tenant_id`, `source: {system_id}`, `raw_payload`), ingested in one line
- Why: a translation removed is one that cannot drift. `role: load` is FIXED by the SDK here (D-IMPL-80)
- Migration: rename the payload keys to the envelope's own and delete the translation helper

## examples/06-decision-replay/run.py

- Surface: examples/06-decision-replay/run.py
- Public surface: false
- Change type: reshaped
- Before: 1,320 lines, 175 mechanical (five marshalling helpers, a 77-line operator-construction function, a 41-line registration prologue, an 8-line boot), 130 relocatable assert/print lines, and a `record()`/`replay_decision()` split whose assertions ran only under `make example-06`
- After: 1,075 lines, 12 mechanical, 0 asserts, 0 prints — one `run(*, root)` returning a typed result, with the guarantee relocated to `tests/examples/test_decision_replay_output.py`
- Why: `make examples` proves a spine runs; `pytest` proves it is correct (D-09). What stays in adopter code stays deliberately: the MaxTTL registration, `register_product_class`, the product's own lineage, `run_gates` with its independent `engine_resolved`, and — the one that matters most in this file — the explicit `pins.version_for` lookup behind every `PolicyBinding` handed to `build_replay_record`
- Migration: split `main()` from a `run()` that returns its state; move assertions to a test module; note that `run()` leaves the fabric handle OPEN because the replay leg reads through its reader

## tests/examples/test_decision_replay_output.py

- Surface: tests/examples/test_decision_replay_output.py
- Public surface: false
- Change type: added
- Before: absent
- After: 33 tests grouped by the replay dimension each covers, with a docstring table mapping every relocated assertion to its pre-rewrite line
- Why: the largest relocation in the suite, and the one whose subject is the five-dimension record — so the grouping is by dimension rather than by call order
- Migration: n/a

## public/tutorial/adopters-guide.md

- Surface: public/tutorial/adopters-guide.md
- Public surface: false
- Change type: reshaped
- Before: the "Replay the decision" section's three snippet includes, with prose asserting that the third block itself shows reproduction refusing
- After: the same three markers, re-pointed at the rewritten spine, with the prose corrected to say where the refusal is now asserted
- Why: `make docs-strict` catches an orphaned include but not a mis-pointed one, and the version-sensitivity block now prepares the probe rather than executing the refusal
- Migration: n/a
