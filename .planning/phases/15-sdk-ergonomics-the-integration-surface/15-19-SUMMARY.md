---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 19
subsystem: examples
tags: [ergonomics, artifacts, examples, hitl, orchestration, audit-by-construction, schema-headers]
requires:
  - ccf.deployment.load_and_boot
  - ccf.controlplane.registry.ControlPlaneRegistry.register_versioned
  - ccf.hitl.review_queue.ReviewQueue
  - ccf_runtime.workflow.engine.WorkflowEngine
  - tools/check_schema_headers.py
  - tools/measure_examples.py
provides:
  - the `_register_closure` ruling, recorded AND tested
  - the relocated workflow/HITL assertion module
  - the seventh `docs/surface/examples/after/` fragment
affects:
  - examples/05-workflow-hitl
  - public/tutorial/adopters-guide.md
  - public/how-to/compose-a-workflow-with-hitl.md
  - public/reference/artifacts/workflow-definitions.md
  - public/reference/artifacts/task-definitions.md
tech-stack:
  added: []
  patterns:
    - one artifact class, one document
    - author-versioned classes stay out of the manifest and keep their bump check
    - a governance ruling written as a test, not only as a comment
    - fail-closed evidence captured at the instant it means something
key-files:
  created:
    - examples/05-workflow-hitl/artifacts/manifest.yaml
    - examples/05-workflow-hitl/artifacts/resolution-spec.yaml
    - examples/05-workflow-hitl/artifacts/events.yaml
    - examples/05-workflow-hitl/artifacts/policy-bundle.yaml
    - examples/05-workflow-hitl/artifacts/agent-policy-regime.yaml
    - examples/05-workflow-hitl/artifacts/agent-debt-profile.yaml
    - examples/05-workflow-hitl/artifacts/task-skill.yaml
    - examples/05-workflow-hitl/artifacts/exception-handler.yaml
    - examples/05-workflow-hitl/artifacts/approval-policy.yaml
    - examples/05-workflow-hitl/artifacts/agent-definition.yaml
    - examples/05-workflow-hitl/artifacts/prompt-artifact.yaml
    - examples/05-workflow-hitl/artifacts/task-definition.yaml
    - examples/05-workflow-hitl/artifacts/workflow-definition.yaml
    - examples/05-workflow-hitl/artifacts/hitl-policy.yaml
    - examples/05-workflow-hitl/artifacts/scope-mapping.yaml
    - examples/05-workflow-hitl/artifacts/agent-registration.yaml
    - examples/05-workflow-hitl/artifacts/hitl-drive.yaml
    - examples/05-workflow-hitl/artifacts/replay-values.yaml
    - tests/examples/test_workflow_hitl_output.py
    - docs/surface-changes/15-19-example-05.md
    - docs/surface/examples/after/examples__05-workflow-hitl__run.json
  modified:
    - examples/05-workflow-hitl/run.py
    - examples/05-workflow-hitl/README.md
    - examples/05-workflow-hitl/artifacts/tokens.yaml
    - public/tutorial/adopters-guide.md
    - public/how-to/compose-a-workflow-with-hitl.md
    - public/reference/artifacts/workflow-definitions.md
    - public/reference/artifacts/task-definitions.md
decisions:
  - "`_register_closure` splits: its five `referenced_artifacts` documents fold into the manifest; the four author-versioned definition classes and the two non-addressable SDK classes stay in adopter code, because `load_and_boot` registers through `register_typed` and would silently drop the D-05 bump check"
  - the ruling is enforced by a test asserting those keys appear under `register_versioned` and never under `register_typed`, mutation-probed
  - "the fail-closed evidence is captured between the refusals and the admission; read afterwards it counts legitimate landings and goes green for a transport that admits everything — an eighth instance of the phase's 'a check that passes for a reason unrelated to what it claims to verify'"
  - the escalation assertion reads its expected handler from an authored drive value rather than from the workflow definition the engine resolved, so it is two statements agreeing rather than the engine agreeing with its own input
  - "example 05 now boots a real fabric: the replay record's dimension 1 names a graph the example ingested into, replacing a hand-built `GraphView` with no graph behind it"
  - "raw line count rose 858 → 866 while mechanical fell 28 → 4 and relocatable fell 112 → 0; reported separately per D-12 and never summed"
metrics:
  duration: ~3h
  completed: 2026-08-05
---

# Phase 15 Plan 19: Workflow/HITL Example Rewrite Summary

The suite's lowest-density example is over the streamlined surface with its 112
assert/print lines relocated intact, and the `_register_closure` question is
answered from verified source rather than from doctrine — the closure splits,
and the half that stays is now enforced by a test rather than by a comment.

---

## The `_register_closure` ruling

The plan asked 15-19 to decide from evidence. **It splits.**

**Folded into the manifest** — the five documents the closure walked out of
inline `referenced_artifacts:` blocks: the agent's policy regime and debt
profile, the task's skill, the exception handler, the approval policy. Each is
now its own `DeclaredArtifact` with a manifest entry keyed by the versioned-URI
ref it answers, so the ref and the registration are two independent statements
of one fact.

**Left in adopter code** — the four author-versioned SDK classes
(`ccf.agent-definition`, `ccf.prompt-artifact`, `ccf.task-definition`,
`ccf.workflow-definition`) and the two SDK classes a manifest cannot address
(`ccf.hitl-policy`, `ccf.scope-mapping`).

### The evidence, verified in source

The carried context asked me to check the facts myself rather than take them.
I did, and they hold:

| Claim | Where | Verified |
| --- | --- | --- |
| The closure used `register_versioned` for the three definition classes | `run.py@df074b0:295, :303, :312` | yes |
| `register_versioned` runs the D-05 bump check | `src/ccf/controlplane/registry.py:357-413` — the four-outcome table (`RefuseUnbumpedChange`, `RefuseEmptyBump`) | yes |
| `load_and_boot` routes everything through `register_typed` | `src/ccf/deployment/manifest.py:299` | yes |
| `register_typed` does not run that check | `src/ccf/controlplane/registry.py:307-355` — validates the class, content-hashes, appends | yes |
| The closure walked `referenced_artifacts` transitively | `run.py@df074b0:274-285` | yes |

So folding the definition classes into the manifest would have bought a shorter
file by **silently dropping governance**: a workflow's routing, a task's steps
or an agent's axis bindings could be re-authored under an unchanged
`artifact_version` and nothing would refuse it.

### On CLAUDE.md §8.1

§8.1 says workflow definitions "are Control Plane artifacts produced through the
Task Factory, not code." Read as "therefore the manifest should name it," that
contradicts the ruling. It does not, and the distinction is worth stating
because a later reader will hit the same sentence.

§8.1 is about **where the definition lives** — data, versioned, in the Control
Plane, never a routing table in a Python constant. Both readings agree on that,
and the definition does live there: `artifacts/workflow-definition.yaml`, whose
document root *is* the artifact. What §8.1 does not say is **which registration
path** puts it in force. That is a mechanism question, and the mechanism has a
governance property the manifest path does not carry. The ruling honours §8.1
fully and declines only the inference beyond it.

### The transitive walk did not need to survive

Worth noting because it was the closure's other justification. The walk existed
to register documents that were *nested inside* other documents. Once "one
artifact class, one document" is applied, they are top-level documents with
their own keys and nothing is nested — so there is nothing to walk. The walk was
a consequence of the bundle format, not a capability the manifest lacks.

### The ruling is tested, not only documented

`test_the_author_versioned_definitions_kept_their_bump_check` asserts the three
`register_versioned` keys appear in the audit log under that action and never
under `register_typed`, and that none of them is in the manifest's pin set. A
future edit that "tidied" them into the manifest flips the recorded action and
goes red.

Mutation-probed: swapping the workflow definition's registration to
`register_typed` fails that test and only that test (1 failed, 36 passed).

**If your reading of the source contradicts the above, it is stated here so you
can check it.** I found no contradiction.

---

## An eighth "passes for a reason unrelated to what it claims"

The phase's running finding gained one more instance, found while relocating
rather than while reviewing.

The pre-rewrite file asserted `transport.submissions(tenant=tenant) == ()` after
the four refusals — correct, and it fires only because nothing legitimate had
landed yet. Relocated naively to a test that reads the transport *after* the
run, the same assertion becomes `len(...) == 1` … then `== 2` once the
ReviewQueue release lands, and either form goes green for a transport that
admitted every refusal too, as long as the count happens to match. My first
draft did exactly this and failed with `assert 2 == 1`, which is how it
surfaced.

The fix is not a bigger number. The spine captures
`submissions_after_refusals` at the one instant the emptiness means something —
between the last refusal and the first admission — and the test asserts on that
capture plus a separate assertion that the admission *did* land, so emptiness is
a property of the refusals rather than of a transport that never records.

A second, smaller instance in the same file: the pre-rewrite escalation check
read the expected handler out of `workflow_doc["workflow_definition"]
["exception_refs"]` — the very document the engine resolved the handler from.
That compares the engine's resolution against the engine's own input and passes
for whatever the engine does with it. The relocated assertion reads
`drive.expected_exception_handler`, a new authored value in `hitl-drive.yaml`,
so it is two statements agreeing.

---

## Deviations from the plan text

Stale plan text is a known hazard this phase; these are the places execution
diverged, with the reason.

### 1. The example now boots a real fabric

The plan says "It builds no operator registry at all" and its acceptance
criteria require `run.py` to contain `load_and_boot` and not
`build_operator_registry`. Both hold. What the plan did not anticipate is that
`load_and_boot` **boots a fabric**: `DeploymentManifest` requires
`resolution_spec_key`, `policy_bundle_key` and `backend`, and `boot()` opens a
graph store and a writer.

Options were (a) skip `load_and_boot` and register from a manifest by hand —
which no SDK entry point supports and which fails the acceptance criterion; or
(b) author a resolution spec and a policy bundle and boot.

I took (b), and rather than leave the two new artifacts inert, the example
ingests a two-envelope loan batch through them. That turned out to be a net
honesty gain rather than scope growth: pre-rewrite, the replay record's
dimension 1 was a hand-built `GraphView(tenant_id=…, as_of=…)` with **no graph
behind it**. It is now `booted.handle.reader.as_of(...)` over a graph the
example wrote to. The projection stage stays fixture-shaped and
`replay-values.yaml` says so in its header — a fourth full L1–L6 pipeline in the
suite would teach nothing examples 00 and 06 do not.

Every other example in the suite boots through `load_and_boot`; example 05 was
the last holdout.

### 2. Snippet markers: 14 became 18

The plan says "re-point the 14 snippet markers." Seven pairs became nine. Two
new regions carry weight the rewrite created:

- `boot` — the one call that replaces the registration prologue, which every
  other rewritten example's guide section shows.
- `register-definitions` — the six explicit registrations. This is the ruling's
  visible form, and both the guide and the how-to now include it with prose
  explaining why those six are not in the manifest. Publishing the ruling only
  in a YAML comment would have hidden the most interesting thing this example
  now teaches.

Two new how-to steps (`review-queue`, `exception-path`) close a gap that
predates this plan: the page claimed to demonstrate four HITL primitives and
showed snippets for two.

### 3. Raw line count rose

858 → 866, while mechanical fell 28 → 4 and relocatable fell 112 → 0.

Stated plainly because D-12 forbids conflating the figures and this is the
example where the raw number does not flatter. What replaced the 112 relocated
lines is the typed result dataclass the test module reads (≈100 lines) plus the
docstrings recording the ruling. The driver's *work* did not shrink because this
example was never carrying much marshalling — 3.3% mechanical density is why the
plan scoped it as a relocation rather than an absorption. The two figures the
audit reports both moved the right way.

### 4. The two deferral markers 15-17 recorded are closed

15-17's fragment records `hitl-policy.yaml` and `scope-mapping.yaml` carrying
`# ccf-schema: deferred(15-21) …` first lines because `dump_schemas.py` emitted
nothing for those classes. The orchestrator-level `unaddressable_classes()` fix
closed that gap between waves. Both documents here carry real `$schema` headers;
**no document under `examples/05-workflow-hitl/artifacts/` carries a deferral
marker or the `# no-schema: DeclaredArtifact` escape hatch.** All nineteen name a
committed schema under `docs/schemas/`.

15-21's tree-wide gate should find nothing to rule on here, and 15-17's example
is presumably now closable the same way — flagged, not acted on, since it is
another plan's file.

---

## Measurement

| Figure | Before | After |
| --- | ---: | ---: |
| raw lines | 858 | 866 |
| mechanical (`removable`) | 28 | 4 |
| relocatable (asserts + prints) | 112 | 0 |
| helpers | 8 | 0 |
| inline operator block | 0 | 0 |
| registration prologue | 20 | 4 |
| boot | 0 | 0 |

Removal and relocation are reported separately and never summed (D-12).

Artifact documents went from 7 bundles to 19 typed documents (18 + manifest).

Relocated assertions: 94 statements across 37 tests, matching the pre-rewrite
94 `assert` count exactly; the parametrized refusal test expands 2 statements
into 8 executed assertions, so executed coverage exceeds the original. The 18
`print` lines are covered across the same tests (the printed summary named the
tenant, the gate, the derived approver, the two authz outcomes, the terminal
state, the review outcome and the escalation handler — each has an assertion).
16 pure `isinstance` narrowings are absorbed rather than relocated, named
line-by-line in the test module's docstring so the count reconciles; the spine
keeps a *raising* guard wherever proceeding past a wrong value would be unsafe,
which is stricter than an `assert` that vanishes under `python -O`.

---

## Tasks completed

| Task | Commit | What |
| --- | --- | --- |
| 1 | `c1b40ce` | Reshape artifacts to 19 typed documents with a manifest; absorb the closure's five ref-resolved documents; boot a real fabric; re-point 18 snippet markers; README; `after/` fragment |
| 2 | `24a38f3` | Relocate all 112 assert/print lines to `tests/examples/test_workflow_hitl_output.py`; fix the fail-closed and escalation self-satisfaction; surface-change fragment |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The relocated fail-closed assertion was self-satisfying**

- **Found during:** Task 2
- **Issue:** `transport.submissions(tenant=...) == ()` read after the run
  counts the legitimate approval and the review release. Any fixed count the
  test asserts would also pass for a transport that admitted all four refusals.
- **Fix:** The spine captures `submissions_after_refusals` between the last
  refusal and the first admission and returns it on the result; the test
  asserts on that capture, plus a separate assertion that the admission landed.
- **Files modified:** `examples/05-workflow-hitl/run.py`,
  `tests/examples/test_workflow_hitl_output.py`
- **Commit:** `24a38f3`

**2. [Rule 1 - Bug] The escalation assertion compared the engine against its own input**

- **Found during:** Task 2
- **Issue:** The pre-rewrite check read the expected handler out of the workflow
  definition document the engine had just resolved the handler from.
- **Fix:** Added `drive.expected_exception_handler` to `hitl-drive.yaml` as an
  independently authored expectation; the assertion reads that.
- **Files modified:** `examples/05-workflow-hitl/artifacts/hitl-drive.yaml`,
  `tests/examples/test_workflow_hitl_output.py`
- **Commit:** `24a38f3` (artifact landed in `c1b40ce`)

**3. [Rule 3 - Blocking] `load_and_boot` requires a fabric this example did not have**

- **Found during:** Task 1
- **Issue:** `DeploymentManifest` requires `resolution_spec_key`,
  `policy_bundle_key` and `backend`; example 05 constructed a
  `ControlPlaneRegistry` directly and booted nothing.
- **Fix:** Authored `resolution-spec.yaml`, `policy-bundle.yaml` and a
  two-envelope `events.yaml`, and booted through the manifest. See deviation 1
  above for why this is a net gain rather than scope growth.
- **Files modified:** three new artifacts, `examples/05-workflow-hitl/run.py`
- **Commit:** `c1b40ce`

### Deliberate departures from the plan text

**The plan's `files_modified` did not list `examples/05-workflow-hitl/artifacts/`
by document.** It named the directory. Seven bundles were deleted and eighteen
typed documents created, which is the recipe's R1 applied — the merge back to
`main` will need `ALLOW_BULK_DELETE=1`, and the replacement count (18) exceeds
the deletion count (6 deleted, 1 rewritten in place).

**No plan-scoped `--report` subset test was added**, per the phase-wide ruling.
`tools/dump_surface.py --report` reports the accumulated set since 15-01; this
plan adds no public Python surface at all, so every fragment entry is
`Public surface: false`.

**`public/tutorial/adopters-guide.md` was touched only in the sections naming
example 05.** Every other example's include lines are byte-identical.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The threat register's three mitigations all hold:

| Threat ID | Disposition | Where it landed |
| --- | --- | --- |
| T-15-19-01 (an unrecorded human action) | mitigated | Five dedicated tests assert approver identity, action time, the product seen by content hash, the annotation field's presence-and-emptiness, and byte-equal dimension-2 capture for both the approval and the review release; the module docstring names audit-by-construction as the invariant at stake |
| T-15-19-02 (suspend/resume semantics changed by a wiring rewrite) | mitigated | The state machine, gate, escalation path and suspend/resume flow are byte-unchanged; only the registration cluster, the result shape and the assertions moved |
| T-15-19-03 (a manifest field invented for a single-site registration) | mitigated | No manifest field was invented. The ruling is recorded with its evidence and enforced by a test |
| T-15-19-SC (package installs) | mitigated | No package installs in this plan |

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `pytest tests` | 1945 passed, 2 skipped |
| `make examples` | exit 0 — all ten |
| `make example-05` | exit 0 |
| `make docs-strict` | exit 0 |
| `make schema-headers` (tree-wide) | exit 0 — 9 directories |
| `pytest tests/examples/test_workflow_hitl_output.py` | 37 passed |
| surface manifest + frozen baseline | untouched (0 files) |

Test count moved 1908 → 1945 (+37).

Mutation probes (throwaway, not committed):

- `register_versioned` → `register_typed` on the workflow definition: fails
  `test_the_author_versioned_definitions_kept_their_bump_check` and only that
  test.
- `signed_binding_required: true` → `false`: the module errors at the fixture —
  the unsigned submission is admitted and the spine's single-submission unpack
  fails — so the refusal suite cannot go green under a policy that demands
  nothing.

## Self-Check: PASSED

All files claimed above exist on disk; both commit hashes resolve in `git log`.
