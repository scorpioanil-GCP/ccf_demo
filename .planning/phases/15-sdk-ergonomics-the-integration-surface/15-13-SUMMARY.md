---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 13
subsystem: examples
tags: [ergonomics, artifacts, examples, gate-independence, schema-headers]
requires:
  - ccf.deployment.load_and_boot
  - ccf.deployment.build_operator_registry
  - ccf.controlplane.artifacts.ProductClassDeclaration
  - ccf.controlplane.artifacts.DeploymentManifest
  - tools/check_schema_headers.py
  - tools/measure_examples.py
provides:
  - the rewrite recipe plans 15-14..15-20 copy
  - the deployment-authored `$schema` envelope route
  - the first `docs/surface/examples/after/` fragment
affects:
  - examples/00-quickstart
  - public/tutorial/adopters-guide.md
  - public/reference/artifacts/
tech-stack:
  added: []
  patterns:
    - one artifact class, one document
    - deployment-authored documents annotate with the DeclaredArtifact envelope
    - required_operator_keys as the authored declared side of Gate 2
key-files:
  created:
    - examples/00-quickstart/artifacts/manifest.yaml
    - examples/00-quickstart/artifacts/product-governance.yaml
    - examples/00-quickstart/artifacts/decision.yaml
    - examples/00-quickstart/artifacts/expected.yaml
    - tests/examples/test_quickstart_output.py
    - docs/schemas/ccf.declared-artifact.json
    - docs/surface-changes/15-13-example-00.md
    - docs/surface/examples/after/examples__00-quickstart__run.json
  modified:
    - examples/00-quickstart/run.py
    - examples/00-quickstart/README.md
    - tools/dump_schemas.py
    - tools/check_schema_headers.py
    - tests/cli/test_schema_export.py
    - public/tutorial/adopters-guide.md
decisions:
  - deployment-authored documents point `$schema` at the committed DeclaredArtifact envelope and carry their own `class_id` field
  - the envelope schema is committed but is NOT a member of SDK_ARTIFACT_CLASSES
  - manifest keys are short, unnamespaced names; Control Plane keys that are not manifest keys stay namespaced
  - `expected.yaml` and `decision.yaml` are `role: load` — an expectation and a run's inputs are not permissions
  - propagation checks and independent expectations are distinct, and the test module says which is which
metrics:
  duration: ~2h
  completed: 2026-08-04
---

# Phase 15 Plan 13: Quickstart Rewrite Summary

The day-1 example is now the call spine an adopter would write — 451 lines to
350, mechanical wiring 143 to 13, relocatable assertions 40 to 0 — with the
Gate 2 tautology fixed at its origin and every governance decision still
written where an adopter can see it.

---

## THE RECIPE — read this before rewriting 15-14 through 15-20

Seven downstream rewrites copy what is established here. Each numbered item is
a rule, not a suggestion; where a rule was a genuine choice, the reasoning is
given so a later executor can tell whether their example differs.

### R1. One artifact class, one document. A file is not an artifact.

Every `*.yaml` under `<example>/artifacts/` is exactly one artifact class. This
is what makes an honest `$schema` header possible at all: a bundle carrying two
classes cannot be annotated, because either header marks the other class's keys
as errors. That is precisely why 15-12 had to defer rather than guess.

Concretely, in this example: `ontology.yaml` became `resolution-spec.yaml`
(rules only — D-03), `halflife.yaml` split into `half-life-table.yaml` and
`debt-profile.yaml`, and `controlplane.yaml` split into nine documents.

**Where a value goes when its bundle splits:** to the artifact whose *consumer*
reads it. `classification_attribute_by_class` went to the policy parameters
document, `similarity_corpus_attribute_by_class` to the similarity one. Do not
create a "misc" document to avoid deciding.

### R2. `$schema` headers — two routes, and the second one is new

**SDK-owned class** → point at that class's committed schema:

```yaml
# yaml-language-server: $schema=../../../docs/schemas/ccf.perspective.json
```

**Deployment-authored class** (a policy bundle, a deployment's own values) →
point at the committed `DeclaredArtifact` envelope and declare `class_id`:

```yaml
# yaml-language-server: $schema=../../../docs/schemas/ccf.declared-artifact.json
semver: "1.0.0"
class_id: <your-namespace>.<your-class>
declaration:
  ...
```

This route did not exist before this plan and is the plan's one piece of
tooling work. It was **blocking**: `check_schema_headers.py` rejected any header
naming a class outside `SDK_ARTIFACT_CLASSES`, and the SDK deliberately commits
no schema for classes it does not own — so a policy bundle (which every example
must have, since `policy_bundle_key` must be a `role: register` entry) had *no*
honest header available. The only alternatives were a deferral marker naming no
real closing plan, or hiding the file from the gate. Both are the anti-pattern.

What was added, and what was deliberately not:

- `docs/schemas/ccf.declared-artifact.json` is committed, emitted by
  `tools/dump_schemas.py`.
- It is **not** in `SDK_ARTIFACT_CLASSES`. Adding it would let a manifest name
  the envelope as a class and would break the "an unknown class id *is* a
  deployment-authored schema" design. `test_the_envelope_is_not_an_owned_class`
  pins this.
- The checker refuses an envelope header over an SDK-owned class (that would
  silence every constraint the real class declares), refuses a document with no
  `class_id`, and still runs the envelope contract over the document.
- The manifest cross-check compares the entry's `class_id` against the
  *document's* `class_id` field for envelope-headed documents, so the
  two-independent-statements property survives the indirection.

Six standing tests in `tests/cli/test_schema_export.py` cover these, and each
was mutation-probed to confirm it fails for the reason it names.

Verify with `make schema-headers DIR=examples/NN-name/artifacts`.

### R3. The manifest, and how to choose `role`

One `manifest.yaml` per example, enumerating every other document by `path`,
`key`, `class_id`, `role`. `role` is required on every entry (D-IMPL-80).

The rule that resolves it, stated once so it is not re-derived seven times:

> **`role: register` means "this is part of what the fabric was permitted to
> do".** Registering content-hashes the document into Control Plane state and
> therefore into Decision Replay dimension 2. Ask: *if I re-authored this file,
> should that read back as a change to what was in force?* Yes → `register`.
> No → `load`.

Applied here:

| Document | Role | Why |
| --- | --- | --- |
| resolution spec, policy bundle, half-life table, debt profile, four operator-parameters, perspective, product class, product governance | `register` | All are standing statements of what the fabric may do |
| `events.yaml` | `load` | Raw observations, not permissions. **The SDK fixes this one** via `SDK_ARTIFACT_ROLES`; writing `register` is refused before anything is read |
| `decision.yaml` | `load` | This run's instants. What one run asked about is not governance |
| `expected.yaml` | `load` | An expectation is not a permission |

The last two are *the deployment's* call, made deliberately — the SDK fixes only
`ccf.signal-batch`. Downstream examples with their own load-role documents
should apply the same test and record the answer in the YAML comment, as this
manifest does.

**Manifest keys are short and unnamespaced** here (`policy-bundle`, `traversal`)
because `run.py` names them as literals and they are the day-1 example's own
vocabulary. Control Plane keys that are *not* manifest keys stay namespaced —
`product-class.yaml`'s `max_ttl_key` is
`meridian-bank/product/payment-context-summary/max-ttl`. Either style is
admissible; be consistent within an example.

### R4. The post-`load_and_boot` spine, in order

```python
booted = load_and_boot(MANIFEST, registry=registry, database_path=...)
# 2. ingest      — for envelope in booted.artifacts["events"].envelopes: ...
# 3. view        — booted.handle.reader.as_of(tenant_id=..., at=boundary)
# 4. parameters  — {key: cast(...) for key in ("traversal", "temporal", ...)}
# 5. operators   — build_operator_registry(parameters=, view=, pins=, ...)
# 6. project     — ProjectionEngine(...).execute(plan=QuickstartPlan(...))
# 7. MaxTTL + register_product_class          <- STAYS IN ADOPTER CODE
# 8. ProductLineage + run_gates + build_replay_record   <- STAYS IN ADOPTER CODE
```

Steps 1–6 are wiring. Steps 7–8 are the D-15A abstraction line and must stay
visible, with the comment explaining why (this file's comment on step 7 names
Gate 3 and the two-independent-values reason; copy that reasoning, not the
prose).

### R5. The parameters mapping — name manifest keys, never filter by type

```python
parameters: Mapping[str, OperatorParametersArtifact] = {
    key: cast(OperatorParametersArtifact, booted.artifacts[key])
    for key in ("traversal", "temporal", "policy", "similarity")
}
```

Not `isinstance`, not a class-id string match. Those are type introspection, and
copied nine times they are a new duplication class — the opposite of this
phase's point. `cast` is honest here: `load_and_boot` already validated each
document against the class the manifest declared for it.

### R6. Fix the Gate 2 tautology — and know what your test actually proves

`QuickstartPlan(required=declared.required_operator_keys)`, read off the
`ccf.product-class` artifact. **Never** `operators.keys()` or
`self._registry().keys()`. 15-21 ships an AST guard that makes the shortcut a
red build tree-wide.

`run_gates` keeps `engine_resolved=execution.operators_invoked` as a separate
argument.

**The part that is easy to get wrong.** `execution.operators_invoked` is
`frozenset(outputs)` — what the engine observed itself running, planned from
`plan.required_operators()`. So a test comparing `required_operator_keys`
against `operators_invoked` cannot be broken by editing the artifact: both ends
move together. That does **not** make the assertion worthless, but it does mean
it proves something narrower than it looks. Verified by mutation:

- Editing `product-class.yaml` alone → **not detected** (both ends move).
- Re-introducing `required=operators.keys()` *and* dropping a key from the
  artifact → **detected**. That is the regression the assertion actually
  guards, and it is the right one.

State this honestly in your test module rather than implying independence you
do not have.

### R7. Relocating assertions — two categories, labelled

`tests/examples/test_<example>_output.py`, loading the example by file path.

**The example's entry point must return its state.** Split `main()` (creates a
temp dir, returns `int`) from `run(*, root: Path) -> <Result>` (does the work).
The test calls `run(root=tmp_path)` so the ArtifactStore is still readable when
assertions run.

**Gotcha that cost time:** register the module in `sys.modules` *before*
`exec_module`. The example uses `from __future__ import annotations`, so
`@dataclass` resolves field annotations through `sys.modules[cls.__module__]`
and fails with an opaque `AttributeError: 'NoneType' object has no attribute
'__dict__'` otherwise. `test_ext00_hardening.py`'s loader does not do this
because it defines no dataclass.

**Every domain expectation is read from an artifact.** But distinguish:

| Category | Source | Fails when | Example |
| --- | --- | --- | --- |
| **Independent expectation** | `expected.yaml` | either side changes alone | entity count, entity classes, relationship types |
| **Propagation check** | an artifact read by *both* `run.py` and the test | the **wiring** is wrong, not the artifact | temporal boundary, perspective role, schema name, required operator set |
| **SDK mechanism claim** | asserted directly | the SDK changes | `model_version == "none"`, address == `content_hash(record)` |

Only the first is a statement about whether the fabric computed the right
answer. Mutation-probe both categories before claiming coverage — the wiring
probes for propagation checks are worth the ten minutes.

The module docstring maps each relocated assertion to its pre-rewrite line, so
the "nothing lost" claim is auditable.

### R8. Measurement

```bash
make measure-examples ONLY=examples/NN-name
```

**Always pass `ONLY`.** Without it, parallel rewrite worktrees overwrite each
other's fragments. Commit the fragment under `docs/surface/examples/after/`.
`test_no_rewritten_example_has_silently_regressed` then pins the achieved
number.

### R9. Docs, and the two traps

- `make docs-strict` catches an **orphaned** include but not a **mis-pointed**
  one. Open every page that includes your snippets and read the surrounding
  prose: this plan's `ontology` and `assemble` markers still *resolved* after
  the rewrite while bracketing code that no longer existed, and the guide's
  sentence "the driver's job is to translate that declaration" had become false.
- **PUB-01 rejects verbatim whitepaper text in published output.** Adding
  `::: ccf.controlplane.artifacts.ProductClassDeclaration` to a reference page
  turned the build red, because that docstring quotes §7.6 verbatim (correctly —
  it is the 15-09 citation). A YAML comment quoting the same sentence tripped it
  too. Paraphrase in anything published; do not touch the source docstring.

Touch only the include lines and sections naming **your own** example.

### R10. What not to do

- Do not touch `docs/surface/v0.2-surface.json` or the frozen baseline, and do
  not run `make surface`. Write a `docs/surface-changes/15-NN-<slug>.md`
  fragment. Artifact-format changes are `Public surface: false`.
- Do not write a plan-scoped fragment/`--report` subset test — that assertion
  exists phase-wide.
- `tools/dump_surface.py --report` prints the **accumulated** set since 15-01.
  For this plan it showed nothing added, so every fragment entry is
  `Public surface: false`. Claim only your own.

---

## Measurement

| Figure | Before | After |
| --- | ---: | ---: |
| raw lines | 451 | 350 |
| mechanical (`removable`) | 143 | 13 |
| relocatable (asserts + prints) | 40 | 0 |
| helpers | 45 | 0 |
| inline operator block | 64 | 0 |
| registration prologue | 26 | 13 |
| boot | 8 | 0 |

Removal and relocation are reported separately and never summed (D-12).

Artifact documents went from 4 bundles to 15 typed documents (14 + manifest).
That is a deliberate increase in file count: it is what "one class, one
document" costs, and it buys closed-world validation and an honest `$schema`
header per document.

---

## Tasks completed

| Task | Commit | What |
| --- | --- | --- |
| 1 | `6d83f37` | Reshape artifacts to typed per-class documents; add manifest; add the DeclaredArtifact envelope schema route |
| 2 | `3f3276b` | Rewrite `run.py` to the call spine; fix the Gate 2 tautology; re-point snippet markers and guide prose |
| 3 | `e9525d3` | Relocate assertions to `tests/`; README; `after/` fragment; surface-change fragment |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Deployment-authored classes had no `$schema` target**

- **Found during:** Task 1
- **Issue:** `check_schema_headers.py` accepts only headers naming a member of
  `SDK_ARTIFACT_CLASSES`, and `dump_schemas.py` deliberately emits no schema for
  classes the SDK does not own. Every example must carry a policy bundle
  (`policy_bundle_key` must be a `role: register` entry) and a policy bundle is
  a deployment-authored class — so the plan's requirement that every document
  carry a real header was unsatisfiable as the tooling stood.
- **Fix:** Committed the `DeclaredArtifact` envelope schema as
  `docs/schemas/ccf.declared-artifact.json`, emitted explicitly by
  `dump_schemas.emit()` without joining `SDK_ARTIFACT_CLASSES`. Taught the
  checker the envelope route with three refusals (no `class_id`, an SDK-owned
  `class_id`, a document the envelope rejects) and redirected the manifest
  cross-check to the document's own `class_id` field.
- **Why not the alternatives:** A deferral marker would have named no real
  closing plan. Placing the documents in a subdirectory would have hidden them
  from the gate's non-recursive glob — the anti-pattern in reverse.
- **Files modified:** `tools/dump_schemas.py`,
  `tools/check_schema_headers.py`, `tests/cli/test_schema_export.py`,
  `docs/schemas/ccf.declared-artifact.json`
- **Commit:** `6d83f37`

**2. [Rule 1 - Bug] importlib module loading broke on the example's dataclass**

- **Found during:** Task 3
- **Issue:** All nine relocated tests errored with
  `AttributeError: 'NoneType' object has no attribute '__dict__'` from
  `dataclasses.py`. The example uses `from __future__ import annotations`, so
  `@dataclass` resolves field annotations via `sys.modules[cls.__module__]`,
  which `spec.loader.exec_module` alone does not populate.
- **Fix:** Register the module in `sys.modules` before `exec_module`, with the
  reason in the loader's docstring so the next seven executors do not rediscover
  it.
- **Files modified:** `tests/examples/test_quickstart_output.py`
- **Commit:** `e9525d3`

**3. [Rule 1 - Bug] PUB-01 tripped on published whitepaper text**

- **Found during:** Task 2
- **Issue:** `make docs-strict` failed with fourteen
  `pub01-whitepaper-shingle` findings after adding a mkdocstrings directive for
  `ProductClassDeclaration` to `product-registration.md`, and after a YAML
  comment in `product-class.yaml` quoted §7.6 verbatim.
- **Fix:** Removed the directive (the source docstring's verbatim citation is
  correct and stays) and paraphrased the YAML comment.
- **Files modified:** `public/reference/artifacts/product-registration.md`,
  `examples/00-quickstart/artifacts/product-class.yaml`
- **Commit:** `3f3276b`

### Deliberate departures from the plan text

**Snippet markers: 16 became 14, and `ontology`/`assemble` became `boot`.**
The plan asked for each of 16 markers to be re-pointed or deleted with its
include. The `ontology` marker bracketed `_resolution_spec` and `assemble`
bracketed the registration prologue — both deleted, and both replaced by the
same single `load_and_boot` call. Keeping two markers over one call would have
published the same three lines twice, so they collapse into one `boot` marker
and the guide's two paragraphs become one. The other six pairs are re-pointed
in place.

**`match` rather than `assert isinstance` on the gate result.** The acceptance
criteria require zero `assert ` and zero `isinstance(` in `run.py`. A refused
product must not be proceeded past, so the gate result is discriminated with a
`match`/`case ServableProduct()` and a refusal raises. This is stricter than the
old `assert`, which vanished under `python -O`.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The one tooling change tightens a gate rather than
loosening it: the envelope route adds three refusals and preserves the manifest
cross-check.

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `make test` | 1771 passed, 2 skipped |
| `make examples` | exit 0 — all ten |
| `make example-00` | exit 0 |
| `make docs-strict` | exit 0 |
| `make schema-headers DIR=examples/00-quickstart/artifacts` | exit 0 |
| `pytest tests/examples/test_quickstart_output.py` | 14 passed |
| surface manifest + frozen baseline | untouched (0 files) |

Mutation probes (throwaway, not committed): 2 independent expectations detected
artifact edits; 3 propagation checks detected wiring faults; 4 envelope-header
failure modes each fired with their own message.

## Self-Check: PASSED

All files claimed above exist on disk; all three commit hashes resolve in
`git log`.
