# 15-20 — examples/external/00-hello-context reshaped to typed artifact documents

Plan 15-20 adds **no** public Python surface: it touches `examples/` and
`tests/` only. Every entry below is therefore `Public surface: false`, and each
`Surface` value is the repo-relative path of a changed artifact document or of
the example's own code. An artifact-document format change is real and an
adopter who copied this example's artifacts must act on it, but it can never
appear in the `__all__`-derived manifest diff.

The four multi-class bundles this example shipped (`ontology.yaml`,
`controlplane.yaml`, `product.yaml`, plus root-shaped `events.yaml`,
`experience.yaml` and `tokens.yaml`) are now sixteen typed, closed-world
documents — fifteen enumerated by one deployment manifest, which is the
sixteenth. **Every one carries a real `$schema` header**: no
`# ccf-schema: deferred(…)` marker and no `# no-schema: DeclaredArtifact`
escape hatch appears anywhere under
`examples/external/00-hello-context/artifacts/`.

## The tree that had to be protected, and how that was verified

This example is the suite's only one whose *consumers* must keep **zero CCF
imports**. `client_bare.py`, `client_anthropic.py` and `client_adk.py`
demonstrate EXAM-04's core claim — an external agent consuming typed Context
Products, lineage and the five-dimension replay record over MCP without
importing the SDK — so only the fabric side was a rewrite target.

`git diff` is empty for all three client legs, for `replay_server.py`, and for
`fixtures/`. That is a necessary check and not a sufficient one, so the claim
was verified the other way as well: the phase's running finding is "a check
that passes for a reason unrelated to what it claims to verify", and a static
grep that matched nothing would be green forever. `run.py`'s
`_assert_zero_ccf_imports` is now **mutation-proved** by
`test_the_zero_import_assertion_fails_when_a_leg_imports_ccf`, which copies the
three legs to a temp directory, injects `from ccf.boot import boot` into one
(and, as a second case, `import ccf_runtime`), repoints `_EXAMPLE_ROOT` at the
copies and requires the real function to raise. The assertion in `run.py` is
byte-unchanged; what changed is that it is now known to refuse.

## What the two rewritten files actually gained

| File | raw | mechanical | relocatable |
| --- | ---: | ---: | ---: |
| `serve.py` before | 773 | 132 | 1 |
| `serve.py` after | 699 | 13 | 1 |
| `run.py` before | 766 | 36 | 22 |
| `run.py` after | 781 | 0 | 22 |

Removal and relocation are reported separately and never summed (D-12).

**`run.py`'s raw count rose and its relocatable count did not move. Both are
stated plainly rather than smoothed over.**

The raw rise is +15 lines: the process-lifecycle block gained a nesting level
so the booted replica's handle can be closed in an outer `finally`, and the
artifact reads that used to be four one-line `fabric._load(...)` calls are now
typed reads off `booted.artifacts` with their casts. What disappeared is the
work: a 22-line hand-built operator registry inside the replay environment and
an 8-line `boot` call with its registration prologue, both replaced by
`load_and_boot` and `build_operator_registry`.

The relocatable count did not move because **it cannot**.
`tests/examples/test_ext00_hardening.py::test_the_d15_fallback_works_with_every_client_leg_deselected`
runs `run.py --legs ""` as a subprocess and asserts that each of `PASS 1:`
through `PASS 8:` appears in its output. That module is out of scope for this
plan and is unmodified, so eight of `run.py`'s ten `print` calls are pinned by
a test this plan may not touch. The narration therefore stays where it is, and
the *claims* behind it are asserted in the new test module instead — which is
what makes `tests/` own the correctness even though the console output did not
move. `serve.py`'s single `print` is the `READY <port>` handshake: process
protocol, not narration, and the parent's blocking `readline()` is the
readiness gate.

## Two Gate 2 tautologies fixed, not one

`serve.py` built its projection plan with `required=operators.keys()` — the
operator registry's own keys on both sides of the lineage strict-equality gate
(INV-CH7-47). `required_operator_keys` in `product-class.yaml` is now the
authored declared side.

The same tautology existed a second time, in `run.py`'s
`HelloReplayEnvironment.resolve_plan`, which built the replay-time plan with
`required=self._operators().keys()`. Left alone it would have reproduced the
original decision's tautology inside the replay that exists to prove that
decision — the same shape 15-17 found in the replay example. It now reads
`required_operator_keys` off the artifact too.

## What the new test module adds beyond relocation

The plan asked for one assertion this family should have and now can: that the
served product's lineage and replay record reach the client leg unchanged.
Three tests carry it, and the module states plainly which of the three is a
real independent statement:

* `test_the_client_leg_read_the_product_the_deployment_declared` is an
  **independent expectation**. `expected.yaml` is read by nothing in the
  serving path, so the assertion closes the loop from an authored document
  through L1–L6, through the authenticated MCP surface, to an agent holding
  only a URL and a token — and either end changing alone fails it.
  Mutation-probed by editing `entity_count`.
* `test_the_served_lineage_reaches_the_client_leg_unchanged` and its
  replay-record sibling are **wire-fidelity checks**, and the module says so
  rather than implying an independence they do not have: both ends resolve
  from the same artifacts, so an artifact edit moves both. What they catch is
  a transport fault — re-serialization, truncation, or a block belonging to a
  different product than the one the surface assembled. The two values are
  computed in two different processes. Mutation-probed by pointing
  `lineage_provider` at a different object.
* `test_the_client_leg_received_all_five_replay_dimensions` replaces a
  substring grep. `run.py` PASS 5 checks that the text
  `content_generation_path` appears somewhere in the leg's output, which a
  document carrying one dimension and four empty keys would also satisfy.

---

## examples/external/00-hello-context/artifacts/manifest.yaml

- Surface: examples/external/00-hello-context/artifacts/manifest.yaml
- Public surface: false
- Change type: added
- Before: absent — `serve.py` and `run.py` each registered artifacts by hand from a `keys:` block inside `controlplane.yaml`
- After: a `ccf.deployment-manifest` naming fifteen documents by `path`, `key`, `class_id` and `role`, plus the tenant and the backend kind
- Why: the set of artifacts in force is replay dimension 2; a registration sequence no artifact records cannot be resolved back out of it
- Migration: write a manifest and call `load_and_boot`; keep the backend's connection string out of it

## examples/external/00-hello-context/artifacts/resolution-spec.yaml

- Surface: examples/external/00-hello-context/artifacts/resolution-spec.yaml
- Public surface: false
- Change type: reshaped
- Before: `ontology.yaml`, carrying the tenant id, the resolution rules, and two operator attribute maps in one document
- After: a `ccf.resolution-spec` closed-world over resolution rules only (D-03), with the tenant on the manifest and each attribute map moved to the operator document that reads it
- Why: one artifact, one consumer — and a document carrying three classes cannot carry an honest `$schema` header for any of them
- Migration: split the bundle; move `tenant_id` to the manifest and each attribute map to its operator's parameters document

## examples/external/00-hello-context/artifacts/events.yaml

- Surface: examples/external/00-hello-context/artifacts/events.yaml
- Public surface: false
- Change type: reshaped
- Before: a flat envelope shape (`source_system_id:`, `payload:`) that `serve.py` translated into `SignalEnvelope` in a `_envelopes` helper, with the tenant read from `ontology.yaml`
- After: a `ccf.signal-batch` in the SDK's own envelope vocabulary (`source: {system_id}`, `raw_payload:`), carrying its own `tenant_id`, `role: load`
- Why: a translation removed is one that cannot drift; `role: load` is FIXED by the SDK under D-IMPL-80 because registering raw events would content-hash them into replay dimension 2
- Migration: adopt the SDK's envelope field names and delete the translating helper

## examples/external/00-hello-context/artifacts/policy-bundle.yaml

- Surface: examples/external/00-hello-context/artifacts/policy-bundle.yaml
- Public surface: false
- Change type: reshaped
- Before: the `policy_bundle:` block inside `controlplane.yaml`
- After: a deployment-authored `DeclaredArtifact` under the short manifest key `policy-bundle`, headed by the committed envelope schema
- Why: the SDK owns the schema of what it ships and never invents one for a regulatory regime that is not its own, so a deployment class points at the envelope and declares its own `class_id`
- Migration: lift the block into its own document, wrap it under `declaration:`, and name the class

## examples/external/00-hello-context/artifacts/operator-parameters-traversal.yaml

- Surface: examples/external/00-hello-context/artifacts/operator-parameters-traversal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.traversal:` block inside `controlplane.yaml`, marshalled into `TraversalNeighborhoodParameters` by hand
- After: a `ccf.operator-parameters.traversal` that `build_operator_registry` reads directly
- Why: the marshalling was 61 lines of the same shape repeated four times; the artifact class is the shape
- Migration: one document per category, then pass the four to `build_operator_registry`

## examples/external/00-hello-context/artifacts/operator-parameters-temporal.yaml

- Surface: examples/external/00-hello-context/artifacts/operator-parameters-temporal.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.temporal:` block inside `controlplane.yaml`
- After: a `ccf.operator-parameters.temporal`
- Why: as above
- Migration: as above

## examples/external/00-hello-context/artifacts/operator-parameters-policy.yaml

- Surface: examples/external/00-hello-context/artifacts/operator-parameters-policy.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.policy:` block inside `controlplane.yaml`, plus `classification_attribute_by_class` from `ontology.yaml`, plus a `permitted_policy_bundle_versions` set `serve.py` assembled from the registration it had just performed
- After: a `ccf.operator-parameters.policy` carrying the classification map and the permitted classifications, and declaring NO admitted-version set — `build_operator_registry` completes that from the adopter-passed pins (D-IMPL-76)
- Why: the admitted-version set is a content hash minted at registration, so there is no value for an adopter to author; the classification map belongs with its one consumer
- Migration: move the map here and delete the hand-assembled version set

## examples/external/00-hello-context/artifacts/operator-parameters-similarity.yaml

- Surface: examples/external/00-hello-context/artifacts/operator-parameters-similarity.yaml
- Public surface: false
- Change type: reshaped
- Before: the `operator_parameters.similarity:` block inside `controlplane.yaml`, plus `similarity_corpus_attribute_by_class` from `ontology.yaml`, plus a corpus dict-comprehension repeated in both `serve.py` and `run.py`
- After: a `ccf.operator-parameters.similarity` carrying the corpus map; the corpus itself is read out of the graph view by `build_operator_registry`, which refuses (never repairs) an entity whose declared corpus attribute is missing
- Why: the duplicated comprehension silently skipped such an entity in both files — a governed omission produced by no rule anyone wrote down
- Migration: move the map here and delete both comprehensions

## examples/external/00-hello-context/artifacts/perspective.yaml

- Surface: examples/external/00-hello-context/artifacts/perspective.yaml
- Public surface: false
- Change type: reshaped
- Before: the `perspective:` block inside `controlplane.yaml`, constructed into a `Perspective` in `serve.py`
- After: a `ccf.perspective` passed straight to the projection engine
- Why: one class, one document; the construction was marshalling
- Migration: lift the block and drop the constructor call

## examples/external/00-hello-context/artifacts/product-class.yaml

- Surface: examples/external/00-hello-context/artifacts/product-class.yaml
- Public surface: false
- Change type: reshaped
- Before: the `product_class:` block inside `product.yaml`, alongside that file's `focus:` and `expected:` blocks — and with no `required_operator_keys` at all, because `serve.py` passed the operator registry's own keys
- After: a `ccf.product-class` whose document root IS the artifact, carrying `required_operator_keys` as the authored declared side of Gate 2
- Why: **this is the document the Gate 2 fix rests on.** A plan that returns the registry's keys makes lineage strict equality compare a value against itself
- Migration: author the operator keys your projection depends on and pass them to your plan; never `operators.keys()`

## examples/external/00-hello-context/artifacts/product-governance.yaml

- Surface: examples/external/00-hello-context/artifacts/product-governance.yaml
- Public surface: false
- Change type: reshaped
- Before: `max_ttl_seconds` and the `artifacts:` class names in `controlplane.yaml`, `product_ttl_seconds` and `plan_id` in `product.yaml`, and `index_version` inside the similarity parameters
- After: one deployment-authored `DeclaredArtifact` holding the five values the SDK declines to own plus the two ArtifactStore class names
- Why: the corpus's version identity is a property of graph state at a named boundary, not of the parameters document — a version derived from the parameters pin would be identical across two different boundaries (INV-CH7-27)
- Migration: gather these into one document and read them off `booted.artifacts`

## examples/external/00-hello-context/artifacts/focus.yaml

- Surface: examples/external/00-hello-context/artifacts/focus.yaml
- Public surface: false
- Change type: reshaped
- Before: the `focus:` block inside `product.yaml`
- After: its own `DeclaredArtifact`, `role: register`
- Why: `get_context` refuses every reference but this one, so it is a scope statement about what the front door may hand out — re-authoring it changes what the deployment was permitted to serve, and that belongs in replay dimension 2
- Migration: lift the block; decide its role by asking whether re-authoring it changes what was in force

## examples/external/00-hello-context/artifacts/decision.yaml

- Surface: examples/external/00-hello-context/artifacts/decision.yaml
- Public surface: false
- Change type: reshaped
- Before: the `decision:` block inside `controlplane.yaml`, parsed by a `_instant` helper that reattached UTC because PyYAML resolves `…Z` scalars to naive datetimes
- After: its own `DeclaredArtifact`, `role: load`; the artifact loader suppresses the timestamp resolver (D-02), so the instants arrive as text and are parsed by the field's own annotation
- Why: what instant one run asked about is not part of what the fabric was permitted to do; and the helper existed only to repair a loader the SDK already fixed
- Migration: lift the block and delete the `_instant` helper

## examples/external/00-hello-context/artifacts/expected.yaml

- Surface: examples/external/00-hello-context/artifacts/expected.yaml
- Public surface: false
- Change type: reshaped
- Before: the `expected:` block inside `product.yaml`, checked by a 25-line self-check inside `serve.py` that raised before the server announced READY
- After: its own `DeclaredArtifact`, `role: load`, read by `tests/examples/test_ext00_serve_output.py` and by nothing in the serving path
- Why: `make example-ext-00` proves the spine runs; `pytest` proves it is correct (D-09) — and keeping the expectation out of the serving path is what makes it an independent expectation rather than a propagation check
- Migration: lift the block and move the comparison to a test module

## examples/external/00-hello-context/artifacts/experience.yaml

- Surface: examples/external/00-hello-context/artifacts/experience.yaml
- Public surface: false
- Change type: reshaped
- Before: a root-shaped document with `server_name`, `auth`, `tools`, `tool_allowlist`, `agent_exposure` and `live_mode` at the top level, read with a plain YAML loader
- After: a deployment-authored `DeclaredArtifact` whose values sit under `declaration:`, `role: register`, parsed once by `load_and_boot`
- Why: one class, one document, and a real `$schema` header requires the envelope's shape. `role: register` because what a front door may advertise is exactly the kind of standing statement replay dimension 2 records — contrast `tokens.yaml` below
- Migration: wrap the values under `declaration:`, name the class, and read them off `booted.artifacts`

## examples/external/00-hello-context/artifacts/tokens.yaml

- Surface: examples/external/00-hello-context/artifacts/tokens.yaml
- Public surface: false
- Change type: reshaped
- Before: a bare `tokens:` list at the document root, re-read off disk by `ArtifactTokenSource` on every lookup
- After: a deployment-authored `DeclaredArtifact`, `role: load`, parsed once by `load_and_boot` and handed to the token source as entries
- Why: one class, one document — and one parse, so there is no second read of the file to drift from the first. `role: load` and never otherwise: registering it would content-hash credential material into the audit plane
- Migration: wrap the list under `declaration:` and pass the parsed entries in rather than a path

## examples/external/00-hello-context/serve.py

- Surface: examples/external/00-hello-context/serve.py
- Public surface: false
- Change type: reshaped
- Before: 773 lines, 132 mechanical — a `_load` YAML reader, an `_instant` timestamp repair, a `_resolution_spec` marshaller, an `_envelopes` marshaller, a 61-line `_operators` block, a 22-line registration prologue and an 8-line `boot` call — plus a 25-line domain self-check
- After: 699 lines, 13 mechanical: `load_and_boot` plus `build_operator_registry`, with `AssembledContext` now carrying the parsed artifact set so callers and tests read one parse rather than re-reading files
- Why: the marshalling was the SDK's job all along, and the self-check belonged where a runner can fail a build. What stays in deployment code stays deliberately: the MaxTTL registration that MINTS the pin Gate 3 compares against, the separately-sourced `engine_resolved` argument, and the `PolicyBinding` selection handed to `build_replay_record` (D-06)
- Migration: replace the loader and the registration prologue with a manifest and one call; keep the gate cluster

## examples/external/00-hello-context/run.py

- Surface: examples/external/00-hello-context/run.py
- Public surface: false
- Change type: reshaped
- Before: 766 lines, 36 mechanical — a 22-line hand-built operator registry in `HelloReplayEnvironment`, an 8-line `boot` and its registration prologue inside the D-16 assertion, and four `fabric._load(...)` reads reaching into `serve.py`'s private helpers
- After: 781 lines, 0 mechanical — one `load_and_boot` of the same manifest at the top of `main()`, whose result supplies both the artifact values every assertion reads and the graph PASS 8 replays against; `build_operator_registry` rebuilds the operators
- Why: the replica must be rebuilt from the artifacts the original ran on, and reaching into another module's private helpers to do it was a second, drift-prone description of the same deployment. The raw line count rose 15; see the section above for why, and for why the 22 relocatable print lines could not move
- Migration: boot your replica from the same manifest; do not import another module's private loaders

## tests/examples/test_ext00_serve_output.py

- Surface: tests/examples/test_ext00_serve_output.py
- Public surface: false
- Change type: added
- Before: absent — the served product's correctness was checked only inside `serve.py`, before READY, where no test runner could see it
- After: 15 tests over the assembled product, the replay record, what a client leg actually received over the authenticated wire, and the zero-import guard's own refusal, with each assertion labelled independent expectation / propagation check / SDK mechanism claim
- Why: an assertion that cannot fail a build is documentation; and the wire-fidelity claim this example exists to make had never been asserted at all
- Migration: n/a

## tests/examples/test_ext00_hardening.py

- Surface: tests/examples/test_ext00_hardening.py
- Public surface: false
- Change type: behavior
- Before: two private loader helpers read `tools` and `tool_allowlist` from the root of `experience.yaml`
- After: they read them from under `declaration:`, following the document onto the `DeclaredArtifact` envelope
- Why: unavoidable consequence of the reshape this plan mandates — the envelope route is the only honest `$schema` header available to a deployment-authored class. No assertion in the module changed; only where the two loaders index
- Migration: n/a
