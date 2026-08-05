---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 16
subsystem: examples
tags: [ergonomics, artifacts, examples, narration-regeneration, schema-headers]
requires:
  - ccf.deployment.load_and_boot
  - ccf.deployment.build_operator_registry
  - tools/check_schema_headers.py
  - tools/measure_examples.py
  - docs/schemas/ccf.agent-definition.json      # from 15-14, merged to main
  - docs/schemas/ccf.prompt-artifact.json       # from 15-14, merged to main
  - docs/schemas/ccf.skill-catalog-entry.json   # from 15-14, merged to main
provides:
  - the demo's narration guarantee as an owned test assertion
  - the correlated-diff method for reviewing a narration regeneration
  - the author-versioned-stays-out-of-the-manifest pattern applied to an example
affects:
  - examples/08-e2e-demo
  - public/tutorial/demo-walkthrough.md
tech-stack:
  added: []
  patterns:
    - one artifact class, one document — including SDK classes whose root must BE the artifact
    - author-versioned classes get schemas but not manifest addressability
    - a grant REQUEST is authorable; a grant is not, because it carries a derived hash
    - narration regeneration reviewed by leaf-by-leaf correlation, not by reading a diff
key-files:
  created:
    - examples/08-e2e-demo/artifacts/manifest.yaml
    - examples/08-e2e-demo/artifacts/resolution-spec.yaml
    - examples/08-e2e-demo/artifacts/ingest-spec.yaml
    - examples/08-e2e-demo/artifacts/agent-definition.yaml
    - examples/08-e2e-demo/artifacts/skill-catalog-entry.yaml
    - examples/08-e2e-demo/artifacts/skill-dispatch.yaml
    - tests/examples/test_e2e_demo_output.py
    - docs/surface-changes/15-16-example-08.md
    - docs/surface/examples/after/examples__08-e2e-demo__run.json
  modified:
    - examples/08-e2e-demo/run.py
    - examples/08-e2e-demo/artifacts/expected_output.txt
    - examples/08-e2e-demo/README.md
    - public/tutorial/demo-walkthrough.md
decisions:
  - the short unnamespaced `policy-bundle` manifest key stays, and the replay address regenerates with it (Dave, at checkpoint)
  - author-versioned classes stay out of the manifest so `register_versioned`'s D-05 bump check is not silently dropped
  - `skill-dispatch.yaml` is a deployment-authored grant REQUEST, not a `ccf.skill-grant`, because the class requires a derived hash
  - `scenario.yaml` is permanently deferred from `$schema` annotation, not deferred as debt
  - `_mapped_rows` and the inline envelope loop stay — this example ingests from live source systems, so no `ccf.signal-batch` exists to absorb them
metrics:
  duration: ~5h
  completed: 2026-08-04
---

# Phase 15 Plan 16: Example 08 Rewrite Summary

The capstone demo runs over the streamlined surface with its 431-line
generator untouched — mechanical wiring 161 lines to 13, three helpers and a
63-line operator block gone — and its real guarantee, the byte-compared
narration, is now an assertion with a name instead of a side effect of an exit
code.

---

## What changed

| Figure | Before | After |
| --- | ---: | ---: |
| mechanical (`removable`) | 161 | 13 |
| helpers | 49 | 0 |
| inline operator block | 63 | 0 |
| boot | 8 | 0 |
| registration prologue | 41 | 13 |
| relocatable (asserts + prints) | 6 | 6 |
| raw lines | 1141 | 1104 |

Removal and relocation are reported separately and never summed (D-12). The
`relocatable` count is unchanged because it counts `print` calls, and this
example's prints *are* its deliverable — the staged narration. What moved is the
sixteen `_require` checks, which the pre-rewrite measurement never counted as
`asserts` because they were function calls rather than `assert` statements.

Artifact documents went from 8 files (six of them multi-class bundles) to 25.
That increase is what "one class, one document" costs and what it buys: every
document but one now carries a `$schema` header that a checker validates the
whole document against.

---

## The narration regeneration (the blocking checkpoint)

One line of the 49-line transcript changed: the Stage 6 replay record content
address, `708ad1df…` → `b4337163…`.

I did not review this by reading the diff. I ran the pre-rewrite example
(materialised from the plan's base commit) against the same unchanged SDK,
captured both replay records, and diffed them leaf by leaf:

| Record leaf that moved | Root cause |
| --- | --- |
| `policy_bindings.bindings[0].key` | the short manifest key `policy-bundle` replaces the long namespaced one (15-13 R3) |
| `policy_bindings.bindings[0].version` | the policy bundle is now a `DeclaredArtifact` envelope document, not a bare mapping |
| `context_fabric_snapshot.store_watermark` | L2 stamps the in-force policy version onto every claim |
| `context_fabric_snapshot.graph_snapshot_id` | derived from the watermark |
| `steps[policy].parameter_hash` | `permitted_policy_bundle_versions` carries the moved version; parameters now come from the artifact |
| `steps[temporal].parameter_hash` | operator built from `ccf.operator-parameters.temporal` rather than a hand-built model |
| `steps[traversal].parameter_hash` | same, from `ccf.operator-parameters.traversal` |
| `content_generation_path.product_content_address` | the product's `lineage.policy_bundle_versions` carries the moved version |

**Untraceable leaves: none.** Two independent confirmations were worth more than
the argument: substituting the pre-rewrite policy version back into the current
product's lineage reproduces `b4f006a5…` exactly, the pre-rewrite value; and
`steps[similarity].parameter_hash`, `model_version`, `perspective_conditioning`,
`recorded_at` and `tenant_id` are all byte-identical, as is the demo's other
printed hash (`skill-set in force 6592ac14…`).

Two intermediate attempts at this correlation were **wrong and said so**. The
first restored only the dimension-2 binding and did not reproduce the old
address; the second checked whether the product was embedded in the record (it
is not). Only the third — the full record capture from both commits — actually
answered the question. Worth recording, because "restore the one obvious input
and see if the hash comes back" is the check a reviewer would naturally reach
for, and it is not sufficient.

Dave approved the regeneration and declined the offered alternative of reverting
to the long namespaced key, on consistency grounds: examples 00–03 and 07 all use
the short key, and diverging here to avoid one line of expected output would
leave 15-17/15-18 inheriting the inconsistency.

---

## Deviations from Plan

### Deliberate departures, each approved or reasoned

**1. `_envelopes` and `_mapped_rows` kept rather than absorbed into `ccf.signal-batch`.**
The plan asked me to confirm the batch shape absorbs the 20-line `_envelopes`.
It does not, and the reason is structural: this example ingests from three
*live* SQLite databases the generator writes at run time, so the events do not
exist until the run creates them and there is no static batch document to name.
What *was* declarable is the mapping, and it is now `artifacts/ingest-spec.yaml`
(`role: register` — re-authoring it changes what the fabric admits). `_envelopes`
is gone as a name; its body is 12 inline lines in the spine. Accepted at the
checkpoint.

**2. `# ccf-schema: deferred(…)` rather than the plan's `# no-schema: DeclaredArtifact`.**
The plan named a marker the tooling does not implement — `check_schema_headers.py`
recognises `# ccf-schema: deferred(<plan>) <reason>`, which passes both the
auto-armed and the `--require-all` tree-wide form. Rather than invent tooling in
a wave where two other plans touch the same tree, I used the existing marker. At
the checkpoint this applied to four documents; after Ruling 2 it applies to one.

**3. Three documents split further than the plan anticipated (Ruling 2).**
The coordinator directed me to repoint `agent.yaml`, `skills.yaml` and
`prompt.yaml` at 15-14's newly committed schemas. That could not be done by
adding a header line: the checker validates the *whole document* against the
class it names, so each document's root had to become its artifact. The split:

| New document | Class | In manifest? |
| --- | --- | --- |
| `agent-definition.yaml` | `ccf.agent-definition` | no — author-versioned |
| `prompt-artifact.yaml` | `ccf.prompt-artifact` | no — author-versioned |
| `skill-catalog-entry.yaml` | `ccf.skill-catalog-entry` | no — author-versioned |
| `agent-registration.yaml` | deployment-authored | yes, `role: load` |
| `skill-dispatch.yaml` | deployment-authored | yes, `role: load` |
| `live-narration.yaml` | deployment-authored | yes, `role: load` |

The split did **not** perturb the replay record — `b4337163…` and `6592ac14…`
are identical before and after it — so the approved one-line regeneration was
unaffected by work done after the approval.

**4. `skill-dispatch.yaml` is not a `ccf.skill-grant`, despite that class having
a committed schema.** The coordinator asked me to say so if it applied, and it
does, with a sharper reason than "no schema exists". `SkillGrant` requires
`agent_definition_hash`, which is derived identity computed at request time — a
hash is never an artifact value. A standalone document of that class cannot be
authored, so a `ccf.skill-grant` header would be one its own class rejects. What
is authorable is the grant *request*, and `run.py` completes it by supplying the
hash. This is the same shape as `max_ttl_version`'s deliberate absence from
`product-class.yaml`.

**5. `scenario.yaml` stays deferred, permanently.** Not a CCF artifact class at
all — it is `generator.py`'s input, describing the synthetic world that exists
before any fabric does — and it carries YAML floats (the noise amount bands) the
artifact loader refuses by design. No envelope can accept it without changing
the data and every pinned checksum with it. Confirmed as legitimate, not debt.

### Auto-fixed issues

**[Rule 1 — Bug] The seed-class banner label depended on set iteration order.**
The pre-rewrite code read `control["operator_parameters"]["traversal"]["seed_entity_classes"][0]`
from a YAML list. The artifact exposes a set, so `[0]` was not available and
naive iteration would have made a byte-compared banner line depend on set
ordering. Replaced with `sorted(...)[0]` and the reason recorded inline. Found by
reading, not by a failing test — with one seed class the bug would not have
surfaced until someone added a second.

---

## What I could not verify on this branch alone

**`make schema-headers` fails on this branch in isolation, and passes in the
merged state.** Reported rather than resolved, per instruction.

Three headers point at `docs/schemas/ccf.agent-definition.json`,
`ccf.prompt-artifact.json` and `ccf.skill-catalog-entry.json`, which exist on
`main` (plan 15-14) but not on this worktree's base commit `76fdb63`. Accepting
those headers also requires 15-14's changes to `tools/check_schema_headers.py`
and `tools/dump_schemas.py`.

What I did: brought main's six schema files and two tool files into the worktree,
ran the full verification in that configuration — **`make schema-headers` exit 0,
1789 passed, all examples green** — then removed them again so this commit
contains no other plan's work. On this branch alone the gate reports:

```
agent-definition.yaml: `$schema=…/ccf.agent-definition.json` describes
  'ccf.agent-definition', which is not an SDK artifact class
```

…and two identical lines for the other two. That resolves on merge with `main`.
I deliberately did not commit 15-14's files to make my branch self-consistent:
that would have put another plan's tooling under my authorship and risked a
conflict in files I do not own.

No collision with 15-14 or 15-15 otherwise: this plan touches only
`examples/08-e2e-demo/`, its two `after/` fragments, its own surface-change
fragment, `tests/examples/test_e2e_demo_output.py`, and the sections of
`public/tutorial/demo-walkthrough.md` that name example 08.

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `pytest tests` | 1789 passed, 2 skipped |
| `make examples` | exit 0 — all ten |
| `make example-08` | exit 0 |
| `make docs-strict` | exit 0 |
| `make schema-headers DIR=examples/08-e2e-demo/artifacts` | exit 0 **with 15-14's merged tooling**; red on this branch alone (see above) |
| `grep -cE "^def _(load\|instant\|resolution_spec\|envelopes)"` | 0 |
| `git diff` on `generator.py` | empty across all three commits |
| surface manifest + frozen baseline | untouched |
| `after/` fragments | both slugify from `examples/08-e2e-demo/`; no other example's fragment touched |

Snippet markers: this example has none. The DEMO-03 walkthrough literal-includes
whole files, so every include was checked by opening the rendered page and
reading the surrounding prose against the new target. Four includes were
repointed (`ontology.yaml` → `resolution-spec.yaml` + `ingest-spec.yaml`,
`controlplane.yaml` → `manifest.yaml` + `policy-bundle.yaml`, `halflife.yaml` →
`half-life-table.yaml` + `debt-profile.yaml`, `agent.yaml`/`skills.yaml`/
`prompt.yaml` → their split successors) and three prose passages that had become
false were corrected — most importantly §8's "loading, mapping, and asserting",
since the driver no longer asserts.

Mutation probes (throwaway, not committed): editing `expected.yaml`'s
`entity_count` failed the independent expectation; re-introducing
`required=operators.keys()` together with a dropped key from
`product-class.yaml` failed `test_every_declared_operator_actually_ran`. Each
failed for the reason it names — which matters here because that second
assertion is the one this phase has repeatedly over-claimed, and its module
docstring now says plainly that editing the artifact alone moves both ends and
is **not** detected.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The `--live` leg remains opt-in and outside `make ci`
(D-10/D-12), and the tier-2 approval sink still raises if consulted.

## Self-Check: PASSED

All files claimed above exist on disk; all three commit hashes resolve in
`git log`.
