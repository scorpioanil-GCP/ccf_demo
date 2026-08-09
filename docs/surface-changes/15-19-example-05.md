# 15-19 — examples/05-workflow-hitl reshaped to typed artifact documents

Plan 15-19 adds **no** public Python surface: it touches `examples/`, `public/`
and `tests/` only. Every entry below is therefore `Public surface: false`, and
each `Surface` value is the repo-relative path of a changed artifact document or
of the example's own code. An artifact-document format change is real and an
adopter who copied this example's artifacts must act on it, but it can never
appear in the `__all__`-derived manifest diff.

The seven multi-artifact bundles this example shipped (`agent.yaml`,
`prompt.yaml`, `task.yaml`, `workflow.yaml`, `hitl.yaml`, `scope_mapping.yaml`,
`tokens.yaml`) are now nineteen typed, closed-world documents — thirteen
enumerated by one deployment manifest, four author-versioned and registered by
`run.py`, and two SDK-owned classes the manifest cannot address at all.

## The `_register_closure` ruling, and the evidence it rests on

The plan asked 15-19 to decide, from evidence, whether the 49-line
`_register_closure` should fold into the manifest. **It splits.** The five
documents it walked out of inline `referenced_artifacts:` blocks become manifest
entries; the four author-versioned definition classes and the two
non-manifest-addressable SDK classes stay in adopter code.

The decisive fact was verified in source rather than assumed:

- `_register_closure` used `ControlPlaneRegistry.register_versioned` for
  `AGENT_DEFINITION`, `TASK_DEFINITION` and `WORKFLOW_DEFINITION`. That method
  runs the D-05 bump check — the author's `artifact_version` claim held against
  content identity, with the four-outcome refusal table.
- `ccf.deployment.manifest.load_and_boot` registers every entry through
  `register_typed` (`src/ccf/deployment/manifest.py:299` — where it stood in the
  tree this fragment was written against; the call has moved since, and Phase
  15.1's ERGO-18 made the path conditional on each entry's declared
  `registration` mode), which does not run that check.

So a manifest entry for any of those three classes would have **silently
dropped governance**: routing, steps or an agent's axis bindings could be
re-authored under an unchanged `artifact_version` and nothing would refuse it.
CLAUDE.md §8.1 ("workflow definitions are Control Plane artifacts produced
through the Task Factory, not code") superficially reads the other way; it is
about where the *definition* lives, not about which registration path puts it in
force. Both readings agree that the definition is an artifact — and it is, at
`artifacts/workflow-definition.yaml`. Only the second says the SDK may skip the
check while putting it there.

`ccf.hitl-policy` and `ccf.scope-mapping` are excluded for a different reason,
already established by 15-17: they are SDK-owned but absent from
`SDK_ARTIFACT_CLASSES`, so a manifest entry naming one resolves to the open
`DeclaredArtifact` envelope and the transport and the authorizer — which read
their real contracts back off the Control Plane by key — would find the wrong
type there.

The ruling is not only documented, it is **tested**:
`test_the_author_versioned_definitions_kept_their_bump_check` asserts those keys
appear in the audit log under `register_versioned` and not under
`register_typed`, and that none of them is in the manifest's pin set. A future
edit that "tidied" them into the manifest flips the recorded action and the test
fails. Mutation-probed: swapping the workflow definition's registration to
`register_typed` fails that test and only that test.

## The two deferral markers 15-17 recorded are closed here

15-17's fragment records `hitl-policy.yaml` and `scope-mapping.yaml` carrying
`# ccf-schema: deferred(15-21) …` first lines, because `tools/dump_schemas.py`
emitted no schema for either class. The post-wave-11 `unaddressable_classes()`
fix closed that gap. Both documents in this example carry real
`$schema` headers pointing at `docs/schemas/ccf.hitl-policy.json` and
`docs/schemas/ccf.scope-mapping.json`. **No document under
`examples/05-workflow-hitl/artifacts/` carries a deferral marker or the
`# no-schema: DeclaredArtifact` escape hatch**; all nineteen name a committed
schema.

## The fabric this example suspends over is now real

Pre-rewrite, `run.py` had no fabric at all: it constructed a
`ControlPlaneRegistry` directly and hand-built a `GraphView(tenant_id=…,
as_of=…)` with no graph behind it for the replay record's dimension 1. Booting
through the manifest required a resolution spec and a policy bundle, so both are
now authored — and rather than leave them inert, the example ingests a
two-envelope loan batch and reads the record's graph view from
`booted.handle.reader.as_of`. Dimension 1 names a graph this example actually
wrote to.

What did **not** change: the projection stage is still fixture-shaped, declared
in `replay-values.yaml`. This example's subject is the Orchestration Layer and
the HITL primitives; `examples/00-quickstart` and `examples/06-decision-replay`
exercise the L1–L6 pipeline end to end, and a fourth full pipeline would teach
nothing new.

## Raw line count barely moved, and that is honest

858 lines to 866. The mechanical figure fell 28 → 4 and the relocatable figure
112 → 0, which are the two numbers D-11/D-12 report and never sum. What replaced
the 112 relocated assert/print lines is the typed result dataclass the test
module reads (≈100 lines) plus the docstrings that state the ruling above. The
driver's *work* did not shrink, because this example was never carrying much
marshalling — it is the suite's outlier at 3.3% mechanical density, which is
exactly why the plan scoped it as a relocation.

---

## examples/05-workflow-hitl/artifacts/manifest.yaml

- Surface: examples/05-workflow-hitl/artifacts/manifest.yaml
- Public surface: false
- Change type: reshaped
- Before: absent — `run.py` registered artifacts by hand, including a 49-line `_register_closure` that walked each definition's `referenced_artifacts` block
- After: a `ccf.deployment-manifest` naming thirteen documents by `path`, `key`, `class_id` and `role`, plus the tenant and the backend kind
- Why: the set of artifacts in force is replay dimension 2; a registration sequence no artifact records cannot be resolved back out of it
- Migration: write a manifest and call `load_and_boot`; keep author-versioned classes out of it and register them yourself

## examples/05-workflow-hitl/artifacts/resolution-spec.yaml

- Surface: examples/05-workflow-hitl/artifacts/resolution-spec.yaml
- Public surface: false
- Change type: added
- Before: absent — this example constructed a registry directly and booted no fabric
- After: a `ccf.resolution-spec` declaring loans, borrowers and the edge between them
- Why: `load_and_boot` boots a fabric, and a fabric needs a resolution spec; leaving it inert would have been an artifact added to satisfy a field, so the example ingests through it
- Migration: author your own entity and relationship rules

## examples/05-workflow-hitl/artifacts/events.yaml

- Surface: examples/05-workflow-hitl/artifacts/events.yaml
- Public surface: false
- Change type: added
- Before: absent — the replay record's graph view was a hand-built `GraphView` with no graph behind it
- After: a `ccf.signal-batch` of two envelopes asserting one loan from two sources, `role: load` (SDK-fixed under D-IMPL-80)
- Why: dimension 1 of a replay record should name a graph the deployment wrote to, not a constructed value
- Migration: author your own envelopes in the SDK's envelope vocabulary

## examples/05-workflow-hitl/artifacts/policy-bundle.yaml

- Surface: examples/05-workflow-hitl/artifacts/policy-bundle.yaml
- Public surface: false
- Change type: added
- Before: absent — the only policy artifact was the agent's regime, inline in `agent.yaml`
- After: a deployment-authored `DeclaredArtifact` under the short manifest key `policy-bundle`, stamped onto every claim at assembly
- Why: the FABRIC's bundle and the AGENT's regime govern different things; conflating them would make one bump read as the other
- Migration: author both, separately

## examples/05-workflow-hitl/artifacts/agent-policy-regime.yaml

- Surface: examples/05-workflow-hitl/artifacts/agent-policy-regime.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.policy_regime` block inside `agent.yaml`, registered by `_register_closure`'s loop
- After: its own `DeclaredArtifact`, `role: register`, under the key the agent definition's axis-4 ref resolves against
- Why: the ref and the registration become two independent statements of one fact, and the loop disappears
- Migration: lift each `referenced_artifacts` entry into its own document and give it a manifest entry keyed by the ref it answers

## examples/05-workflow-hitl/artifacts/agent-debt-profile.yaml

- Surface: examples/05-workflow-hitl/artifacts/agent-debt-profile.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.halflife_debt_profile` block inside `agent.yaml`
- After: its own `DeclaredArtifact`, `role: register`, under the axis-5 ref's key
- Why: as above
- Migration: as above

## examples/05-workflow-hitl/artifacts/task-skill.yaml

- Surface: examples/05-workflow-hitl/artifacts/task-skill.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.verify_loan_file_skill` block inside `task.yaml`
- After: its own `DeclaredArtifact`, `role: register`, under the key the task's first step ref names
- Why: what a workflow step may invoke is a standing statement of what the fabric may do
- Migration: as above

## examples/05-workflow-hitl/artifacts/exception-handler.yaml

- Surface: examples/05-workflow-hitl/artifacts/exception-handler.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.loan_file_exception_handler` block inside `workflow.yaml`
- After: its own `DeclaredArtifact`, `role: register`, under the key `exception_refs` names
- Why: an exception path is a first-class state transition (D-IMPL-61), so its destination is a registered artifact like any other routing value
- Migration: as above

## examples/05-workflow-hitl/artifacts/approval-policy.yaml

- Surface: examples/05-workflow-hitl/artifacts/approval-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `referenced_artifacts.disbursement_officer_policy` block inside `workflow.yaml`
- After: its own `DeclaredArtifact`, `role: register`, under the key `gate_policies` names
- Why: who may approve at a gate is precisely what the fabric was permitted to do — it is the answer a regulator asks for
- Migration: as above

## examples/05-workflow-hitl/artifacts/agent-definition.yaml

- Surface: examples/05-workflow-hitl/artifacts/agent-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `agent_definition:` block inside `agent.yaml`, alongside that file's `keys:` and `referenced_artifacts:` blocks
- After: a `ccf.agent-definition` whose document root IS the artifact, carrying a real `$schema` header and **not** in the manifest
- Why: the checker validates the whole document against the class its header names, so the root had to become the artifact; the class stays out of the manifest because `load_and_boot`'s `register_typed` does not run the D-05 bump check that `register_versioned` does
- Migration: split the file so the definition is the root; move its Control Plane key to a separate filing document

## examples/05-workflow-hitl/artifacts/prompt-artifact.yaml

- Surface: examples/05-workflow-hitl/artifacts/prompt-artifact.yaml
- Public surface: false
- Change type: reshaped
- Before: the `prompt_artifact:` block inside `prompt.yaml`
- After: a `ccf.prompt-artifact` at the document root, out of the manifest
- Why: as above
- Migration: as above

## examples/05-workflow-hitl/artifacts/task-definition.yaml

- Surface: examples/05-workflow-hitl/artifacts/task-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `task_definition:` block inside `task.yaml`
- After: a `ccf.task-definition` at the document root, author-versioned, out of the manifest
- Why: as above
- Migration: as above

## examples/05-workflow-hitl/artifacts/workflow-definition.yaml

- Surface: examples/05-workflow-hitl/artifacts/workflow-definition.yaml
- Public surface: false
- Change type: reshaped
- Before: the `workflow_definition:` block inside `workflow.yaml`, alongside that file's `keys:` and `referenced_artifacts:` blocks
- After: a `ccf.workflow-definition` at the document root, author-versioned, registered by `run.py`, out of the manifest
- Why: **this is the document the plan's ruling is about.** See the section above: routing re-authored under an unchanged `artifact_version` must be refused, and only `register_versioned` refuses it
- Migration: lift the block to the root; register it with `register_versioned`; bump `artifact_version` whenever you edit routing

## examples/05-workflow-hitl/artifacts/hitl-policy.yaml

- Surface: examples/05-workflow-hitl/artifacts/hitl-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `hitl_policy:` block inside `hitl.yaml`
- After: a `ccf.hitl-policy` at the document root, registered by `run.py`, carrying a **real** `$schema` header (15-17's deferral marker is closed)
- Why: one class, one document; the class is not manifest-addressable, so an entry naming it would resolve to the open envelope and leave the transport reading the wrong type back
- Migration: lift the block to the root and register it with `register_typed`; do not put it in a manifest

## examples/05-workflow-hitl/artifacts/scope-mapping.yaml

- Surface: examples/05-workflow-hitl/artifacts/scope-mapping.yaml
- Public surface: false
- Change type: reshaped
- Before: `scope_mapping.yaml`, carrying both a `keys:` block and a nested `scope_mapping:` block, under a hyphen-free filename
- After: `scope-mapping.yaml`, a `ccf.scope-mapping` at the document root with a real `$schema` header, registered by `run.py`
- Why: as above; the key moved to `agent-registration.yaml`, and the filename now matches the class id like every other document here
- Migration: rename the file, lift the block to the root, move the key out

## examples/05-workflow-hitl/artifacts/agent-registration.yaml

- Surface: examples/05-workflow-hitl/artifacts/agent-registration.yaml
- Public surface: false
- Change type: reshaped
- Before: the `keys:` blocks scattered across `agent.yaml`, `prompt.yaml`, `task.yaml`, `workflow.yaml`, `hitl.yaml` and `scope_mapping.yaml`
- After: one deployment-authored `DeclaredArtifact`, `role: load`, naming where each of the six driver-registered documents files, plus the signing key's name
- Why: a key is where a document is FILED, not part of what it says — and once each document's root must BE its artifact, there is nowhere else for the key to live. `role: load` because putting the filing scheme in force would content-hash it into replay dimension 2 alongside the artifacts it files
- Migration: gather the keys into one document and read them off `booted.artifacts`

## examples/05-workflow-hitl/artifacts/hitl-drive.yaml

- Surface: examples/05-workflow-hitl/artifacts/hitl-drive.yaml
- Public surface: false
- Change type: reshaped
- Before: the `approver:`, `drive:`, `node_outputs:`, `debt_factors:`, `clock:` and `review:` blocks inside `hitl.yaml`
- After: one deployment-authored `DeclaredArtifact`, `role: load`, with `clock.base` renamed `clock_base` at the declaration root and a new `drive.expected_exception_handler`
- Why: what one run's human actors did is not a standing statement of what the fabric was permitted to do — the POLICY governing them is, and that is registered separately. `expected_exception_handler` is new because the relocated assertion needs an authored expectation: reading the handler off the workflow definition the engine itself resolved would compare the engine's resolution against the document it resolved it from
- Migration: split the policy out, and author the exception handler your escalation assertion expects

## examples/05-workflow-hitl/artifacts/replay-values.yaml

- Surface: examples/05-workflow-hitl/artifacts/replay-values.yaml
- Public surface: false
- Change type: reshaped
- Before: the `replay:` block inside `hitl.yaml`
- After: one deployment-authored `DeclaredArtifact`, `role: load`
- Why: an envelope for one record is not a statement of what was permitted, and separating it makes the fixture-shaped projection stage visible rather than buried inside the HITL bundle
- Migration: lift the block into its own document

## examples/05-workflow-hitl/artifacts/tokens.yaml

- Surface: examples/05-workflow-hitl/artifacts/tokens.yaml
- Public surface: false
- Change type: reshaped
- Before: a bare `tokens:` list at the document root, re-read off disk by `ArtifactTokenSource` on every lookup
- After: a deployment-authored `DeclaredArtifact`, `role: load`, parsed once by `load_and_boot` and handed to the token source
- Why: one class, one document — and one parse, so there is no second read of the file to drift from the first
- Migration: wrap the list under `declaration:` and pass the parsed entries in rather than a path

## examples/05-workflow-hitl/run.py

- Surface: examples/05-workflow-hitl/run.py
- Public surface: false
- Change type: reshaped
- Before: 858 lines, 28 mechanical (a 49-line `_register_closure`, a 20-line registration cluster, the `_instant` timestamp helper, a `_load` YAML reader), 112 relocatable assert/print lines, and one `main()` whose assertions ran only under `make example-05`
- After: 866 lines, 4 mechanical, 0 asserts, 0 prints — one `run(*, root)` returning a typed result, with the guarantee relocated to `tests/examples/test_workflow_hitl_output.py`
- Why: `make examples` proves a spine runs; `pytest` proves it is correct (D-09). What stays in adopter code stays deliberately: the six explicit registrations (the ruling above), the `PolicyBinding` selection handed to `build_replay_record`, and the `submissions_after_refusals` capture taken between the refusals and the admission
- Migration: split `main()` from a `run()` that returns its state; move assertions to a test module; note that `run()` leaves the fabric handle OPEN

## tests/examples/test_workflow_hitl_output.py

- Surface: tests/examples/test_workflow_hitl_output.py
- Public surface: false
- Change type: added
- Before: absent
- After: 37 tests grouped by suspend, the hardened door, resume, the exception path, replay capture and the review queue, with a docstring table mapping every relocated assertion to its pre-rewrite line and stating audit-by-construction as the invariant at stake
- Why: an assertion lost in this move is not a missing test — it is a structural invariant losing the only place it is shown to hold (CLAUDE.md §8.2)
- Migration: n/a

## public/how-to/compose-a-workflow-with-hitl.md

- Surface: public/how-to/compose-a-workflow-with-hitl.md
- Public surface: false
- Change type: reshaped
- Before: eight includes, two of which named `artifacts/workflow.yaml` and `artifacts/hitl.yaml`, plus a "what to change first" section naming the old bundles
- After: eleven includes across the reshaped documents and two new spine markers (`boot`, `register-definitions`), plus new steps for the review queue and the exception path
- Why: `make docs-strict` catches an orphaned include but not a mis-pointed one; the "approval policy" paragraph pointed at a bundle that carried the policy, the identities, the drive values and the replay envelope all at once
- Migration: n/a

## public/tutorial/adopters-guide.md

- Surface: public/tutorial/adopters-guide.md
- Public surface: false
- Change type: reshaped
- Before: the "Compose a workflow with a human gate" section's eight includes, one naming `artifacts/workflow.yaml`
- After: the same section re-pointed, with a `register-definitions` include and a paragraph stating why four definition classes stay out of the manifest
- Why: the ruling is the interesting thing this example now teaches, and the guide is where an adopter meets it first
- Migration: n/a

## public/reference/artifacts/workflow-definitions.md

- Surface: public/reference/artifacts/workflow-definitions.md
- Public surface: false
- Change type: reshaped
- Before: the worked example included `examples/05-workflow-hitl/artifacts/workflow.yaml`, a bundle carrying `keys:`, `referenced_artifacts:` and the definition
- After: it includes `workflow-definition.yaml`, whose root IS the artifact the page documents
- Why: a reference page for a class should show a document of that class
- Migration: n/a

## public/reference/artifacts/task-definitions.md

- Surface: public/reference/artifacts/task-definitions.md
- Public surface: false
- Change type: reshaped
- Before: the worked example included `examples/05-workflow-hitl/artifacts/task.yaml`
- After: it includes `task-definition.yaml`
- Why: as above
- Migration: n/a
