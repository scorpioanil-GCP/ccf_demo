---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 15
subsystem: examples
tags: [ergonomics, artifacts, examples, harness-neutrality, artifact-store, schema-headers]
requires:
  - ccf.deployment.load_and_boot
  - ccf.deployment.build_operator_registry
  - ccf.controlplane.artifacts.ProductClassDeclaration
  - ccf.controlplane.artifacts.DeploymentManifest
  - docs/schemas/ccf.agent-definition.json (committed by 15-14)
  - docs/schemas/ccf.prompt-artifact.json (committed by 15-14)
provides:
  - the two-harness equivalence proof, relocated to pytest and mutation-verified
  - the ArtifactStore "nothing else changes" claim, made structural
  - after/ fragments for examples 03 and 07
affects:
  - examples/03-harness-portability
  - examples/07-artifact-store-mcp
  - public/how-to/bind-a-harness-adapter.md
  - public/how-to/swap-the-artifact-store.md
tech-stack:
  added: []
  patterns:
    - one artifact class, one document (applied to agent documents too)
    - the artifact store is a call-site binding, never a manifest field
    - a claim about "nothing else changed" is checked from the source, not only from outputs
    - process-global guards installed by an example must be scoped, because the example now runs inside pytest
key-files:
  created:
    - examples/03-harness-portability/artifacts/manifest.yaml
    - examples/03-harness-portability/artifacts/agent-registration.yaml
    - examples/03-harness-portability/artifacts/agents/agent-definition.yaml
    - examples/03-harness-portability/artifacts/agents/policy-regime.yaml
    - examples/03-harness-portability/artifacts/agents/debt-profile.yaml
    - examples/07-artifact-store-mcp/artifacts/manifest.yaml
    - tests/examples/test_harness_portability_output.py
    - tests/examples/test_artifact_store_output.py
    - docs/surface-changes/15-15-examples-03-07.md
  modified:
    - examples/03-harness-portability/run.py
    - examples/03-harness-portability/legs/deterministic.py
    - examples/07-artifact-store-mcp/run.py
    - examples/07-artifact-store-mcp/mcp_store_child.py
    - public/how-to/bind-a-harness-adapter.md
    - public/how-to/swap-the-artifact-store.md
decisions:
  - the live legs keep their assertions in run.py, because relocating them would move them somewhere nothing runs them
  - the artifact store stays a call-site binding; a manifest store field would put a substrate in replay dimension 2
  - "nothing else changes" is checked structurally from the AST and the manifest, not only observationally
  - ccf.agent-definition and ccf.prompt-artifact stay out of SDK_ARTIFACT_CLASSES so register_versioned's D-05 bump check is kept
metrics:
  duration: ~4h
  completed: 2026-08-04
---

# Phase 15 Plan 15: Examples 03 and 07 Rewrite Summary

The two examples that carry mission-level claims now stand on a two-call
fabric prologue with both proofs intact and, in one case, materially stronger:
the two-harness equivalence assertion is relocated to `pytest` and
mutation-verified, and the ArtifactStore's "nothing else changes" property is
checked from the example's own source rather than only from its outputs.

---

## What the two proofs look like now

**Example 03 — harness neutrality.** One agent definition, three harnesses,
and two inherited assertions that carry the claim:

| Claim | Where it lives now | Mutation probe |
| --- | --- | --- |
| Context Product *consumption* equivalent | `test_the_same_context_product_reached_every_harness` | corrupt one leg's recovered bytes → detected |
| *Replay records* equivalent, field by field | `test_the_governed_replay_fields_are_equal_across_harnesses` | build one leg's record from a tampered product → detected, naming `content_generation_path` and both harnesses |
| The population is non-vacuous | `test_three_distinct_harnesses_actually_ran`, against `expected.yaml`'s declared `harness_leg_count` | drop to one leg → detected |

Neither equivalence assertion compares a value to itself: `drive_leg` recovers
each leg's product out of *that leg's own* carrier and builds *that leg's own*
record from it. The vacuity guard was added because "all legs agree" is
trivially true of one leg, and nothing previously asserted there were three.

**Example 07 — ArtifactStore pluggability.** The claim is now defended in two
independent directions, because "nothing else changed" is exactly the shape of
claim that passes because a test never looked:

- **Structurally, from the source.** `workload()` takes exactly one parameter
  (asserted from the AST), both runs boot from the same `MANIFEST` module
  constant, and the parsed manifest names no store under any spelling
  (asserted by walking the document). A behavioural test cannot distinguish
  "the two runs were identical" from "the two runs differed in ways that did
  not move the bytes"; these can.
- **Observationally, from the two runs.** Byte equality of the served product;
  the same artifact roles, checked against the deployment's declared
  `persisted_artifact_roles` so two empty sets cannot agree vacuously; the same
  versioned URIs and content addresses; and every recorded URI resolving on a
  *fresh* client at its exact address while the server child is still up.

Five mutation probes were run against the observational half; all five were
detected. The role-set probe is the one worth naming: dropping the policy
bundle from *both* runs passed the old pairwise check and fails the new one.

---

## Measurement

| Figure | 03 before | 03 after | 07 before | 07 after |
| --- | ---: | ---: | ---: | ---: |
| raw lines | 720 | 684 | 587 | 596 |
| mechanical (`removable`) | 145 | 23 | 132 | 13 |
| relocatable (asserts + prints) | 98 | 54 | 27 | 1 |
| helpers | 41 | 0 | 38 | 0 |
| inline operator block | 64 | 0 | 64 | 0 |
| boot | 8 | 0 | 8 | 0 |

Removal and relocation are reported separately and never summed (D-12).

Example 03's residual 54 relocatable lines and 07's residual 1 are **not**
unfinished work. All of 03's are inside `_live`, which is excluded from
`make ci` by design; 07's single line is the store child's stderr diagnostic.
See "Deliberate departures" below.

Artifact documents: example 03 went from 6 documents (2 fabric bundles + 4
agent/live files) to 20; example 07 from 5 to 15. That increase is what "one
class, one document" costs and what buys closed-world validation and an honest
`$schema` header per document.

---

## Tasks completed

| Task | Commit | What |
| --- | --- | --- |
| 1 | `67212c6` | Example 03: artifacts reshaped, `run.py` to the call spine, Gate 2 tautology fixed, assertions relocated, `after/` fragment |
| 2 | `ad89526` | Example 07 rewritten in full; example 03's agent documents reshaped per the orchestrator's 15-14 notice; surface-change fragment |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] the no-model guard leaked across the pytest session**

- **Found during:** Task 2 (`make test`, after task 1 was committed)
- **Issue:** `install_no_model_guard` patches `socket.socket.connect` and
  `socket.create_connection` process-globally and never restored them. Under
  `make example-03` that was harmless — the process existed to run one drive.
  Once the drive moved into `pytest` (D-09), the patch survived it and every
  later test needing a socket failed, including the Docker-backed Postgres
  suite. The failure reported itself in
  `tests/crossproc/…` with a message about the *portability drive*, which is
  the worst property a guard can have.
- **Fix:** Made `install_no_model_guard` a context manager that restores both
  originals in a `finally`, and scoped it around the drive.
  `test_the_no_model_guard_does_not_outlive_the_drive` now asserts the
  restoration, so the regression cannot return silently.
- **Files modified:** `examples/03-harness-portability/legs/deterministic.py`,
  `examples/03-harness-portability/run.py`,
  `tests/examples/test_harness_portability_output.py`
- **Commit:** `ad89526`

**2. [Rule 1 - Bug] a raw-text manifest check fired on a comment**

- **Found during:** Task 2
- **Issue:** `test_no_manifest_field_names_an_artifact_store` initially checked
  the manifest's raw text as well as its parsed form, and the raw check fired
  on the prose explaining *why* no store is named — a check failing for a
  reason unrelated to what it claims, in the direction of a false positive.
- **Fix:** Dropped the raw-text half. The parsed walk is both correct and
  stronger: comments configure nothing, and the walk covers keys and values at
  any depth under any spelling. Verified by mutation — injecting
  `artifact_store: file` into the parsed document is detected.
- **Files modified:** `tests/examples/test_artifact_store_output.py`
- **Commit:** `ad89526`

### Deliberate departures from the plan text

**The `grep -c "assert " run.py returns 0` criterion holds for example 07 and
is deliberately not met by example 03.** Example 03's `run.py` retains 10
`assert` statements, all inside `_live`. The plan's own scope boundary excludes
the live legs from the rewrite and D-11/D-12 exclude them from `make ci` —
relocating their assertions to `pytest` would move them somewhere *nothing runs
them*, which inverts D-09's reason for the move. The criterion's real intent is
"no assertion hides on a path no runner checks", so it is enforced in that form
instead: `test_no_assertion_survives_on_the_path_ci_actually_runs` parses
`run.py` and refuses any `assert` outside `_live`. Example 07 has zero, checked
the same way.

**The `# no-schema: DeclaredArtifact` escape hatch was not used.** Per the
orchestrator's mid-flight notice it does not exist in the tooling; 15-13's
envelope route supersedes it. No document in either example carries a deferral
marker.

**Example 03's agent documents were reshaped, which the plan did not
anticipate.** Task 1 shipped them with deferral markers, because
`ccf.agent-definition` and `ccf.prompt-artifact` had no committed schema. The
orchestrator's notice reported 15-14's fix, so task 2 replaced the markers with
real headers — which required each document to *be* one artifact class at its
root. `agents/order_insights.yaml` therefore split into `agent-definition.yaml`,
`policy-regime.yaml` and `debt-profile.yaml`; `prompt.yaml` lost its `keys:`
wrapper; and a new `agent-registration.yaml` (`role: load`) carries the Control
Plane keys, because a key is where a deployment *files* an artifact, not a
property of the artifact.

**`test_exactly_one_agent_definition_is_shared_by_every_leg` was strengthened
rather than ported.** The pre-rewrite check counted files in
`artifacts/agents/`, which stopped meaning anything the moment that directory
gained the definition's referenced artifacts. It now counts documents *the
agent-definition contract accepts*, over the whole artifact tree — a statement
about definitions rather than about a directory listing.

**Snippet marker `harness-governed-fields` moved rather than being deleted.**
The code it bracketed moved to `tests/`, which `publish_scan.py`'s include
allowlist correctly forbids publishing from. It now brackets
`GOVERNED_DIMENSIONS` / `GOVERNED_MODEL_VERSION_FIELDS` in
`legs/deterministic.py` — which is the honest thing for a section headed
"assert equivalence on what CCF governs" to show — and the page's prose names
the test module where the comparison runs.

---

## Blocking dependency for the merge — read before merging this branch

`make schema-headers DIR=examples/03-harness-portability/artifacts` **fails in
this worktree**, with:

```
examples/03-harness-portability/artifacts/prompt.yaml:
  `$schema=../../../docs/schemas/ccf.prompt-artifact.json` does not resolve
```

This is the known cross-plan ordering dependency the orchestrator described,
not a defect. Plan **15-14 must merge before 15-15**: it commits
`docs/schemas/ccf.agent-definition.json` and
`docs/schemas/ccf.prompt-artifact.json` via
`tools/dump_schemas.author_versioned_classes()`, and teaches
`check_schema_headers.py` to accept the author-versioned set. Per the notice,
this was **not** worked around by adding those classes to
`SDK_ARTIFACT_CLASSES` — doing so would route them through `register_typed` and
silently drop `register_versioned`'s D-05 hash-verified bump check.

What *was* verified locally, so only the resolution step remains: both
documents are accepted by the classes their headers name
(`load_artifact(prompt.yaml, PROMPT_ARTIFACT)` and
`load_artifact(agent-definition.yaml, AGENT_DEFINITION)` both succeed). Example
07's directory passes the header gate outright.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. Example 07's MCP auth block is unchanged in content; only
its nesting moved (`store:` → `declaration:`), and both the server child and the
client factory still read the same block, so the credential still cannot drift
into two values. The one guard change tightens rather than loosens: the
no-model guard now restores what it patched, and a new test asserts it.

## Known Stubs

None.

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `make test` | 1798 passed, 2 skipped |
| `make examples` | exit 0 — all ten |
| `make example-03` | exit 0 |
| `make example-07` | exit 0 |
| `make docs-strict` | exit 0 |
| `make schema-headers DIR=examples/07-artifact-store-mcp/artifacts` | exit 0 |
| `make schema-headers DIR=examples/03-harness-portability/artifacts` | **blocked on 15-14** — see above |
| `pytest tests/examples/test_harness_portability_output.py` | 15 passed |
| `pytest tests/examples/test_artifact_store_output.py` | 12 passed |
| `git diff` over `legs/live.py`, `legs/ollama_client.py` | empty |
| surface manifest + frozen baseline | untouched (0 files) |
| `STATE.md`, `ROADMAP.md` | untouched (orchestrator owns them) |
| `after/` fragments added | 7, all slugifying from examples/03-harness-portability/ or examples/07-artifact-store-mcp/ |

Mutation probes (throwaway, not committed): 3 for example 03's equivalence and
vacuity assertions, 5 for example 07's pluggability assertions, 1 for the
manifest store-field walk. All 9 detected their injected fault.

## Self-Check: PASSED

All files claimed above exist on disk; both commit hashes resolve in `git log`.
