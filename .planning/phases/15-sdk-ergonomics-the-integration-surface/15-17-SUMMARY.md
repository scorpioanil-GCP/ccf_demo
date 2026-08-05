---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 17
subsystem: examples
tags: [ergonomics, artifacts, examples, decision-replay, schema-headers, pin-selection]
requires:
  - ccf.deployment.load_and_boot
  - ccf.deployment.build_operator_registry
  - ccf.deployment.pins.ResolvedPins
  - ccf.replay.record.build_replay_record
  - tools/check_schema_headers.py
  - tools/measure_examples.py
  - docs/schemas/ccf.agent-definition.json       # 15-14
  - docs/schemas/ccf.prompt-artifact.json        # 15-14
  - docs/schemas/ccf.skill-catalog-entry.json    # 15-14
  - docs/schemas/ccf.task-definition.json        # 15-14
  - docs/schemas/ccf.workflow-definition.json    # 15-14
provides:
  - the replay example's guarantee as a dimension-grouped test module
  - the pin-selection-stays-visible pattern applied at its sharpest point
  - the leaf-by-leaf record correlation with an exact-substitution confirmation
affects:
  - examples/06-decision-replay
  - public/tutorial/adopters-guide.md
tech-stack:
  added: []
  patterns:
    - one artifact class, one document — including the five author-versioned SDK classes
    - PolicyBinding built from an explicit pins.version_for lookup, never from pins itself
    - the Gate 2 declared side read from the artifact in BOTH the record phase and the replay environment
    - a spine that leaves its fabric handle open when the replay leg reads through it
key-files:
  created:
    - examples/06-decision-replay/artifacts/manifest.yaml
    - examples/06-decision-replay/artifacts/product-class.yaml
    - examples/06-decision-replay/artifacts/agent-registration.yaml
    - examples/06-decision-replay/artifacts/replay-probes.yaml
    - tests/examples/test_decision_replay_output.py
    - docs/surface-changes/15-17-example-06.md
    - docs/surface/examples/after/examples__06-decision-replay__run.json
  modified:
    - examples/06-decision-replay/run.py
    - examples/06-decision-replay/README.md
    - public/tutorial/adopters-guide.md
decisions:
  - the Gate 2 tautology existed at TWO sites in this example and both are fixed from one artifact — a correctness defect, not an ergonomics one
  - the deferred(15-21) markers on ccf.hitl-policy and ccf.scope-mapping are closed by the ORCHESTRATOR between Waves 11 and 12, not by 15-21 (Dave, at checkpoint)
  - ccf.hitl-policy and ccf.scope-mapping take a named deferral marker, not an envelope wrapper, because the documents genuinely ARE those SDK classes
  - run() leaves the fabric handle open and its caller closes it — the replay leg reads through the reader
  - the suspended workflow state's hash is captured at suspension, not re-derived after the resume
metrics:
  duration: ~3h
  completed: 2026-08-04
---

# Phase 15 Plan 17: Example 06 Rewrite Summary

The suite's most consequential file for replay is 163 mechanical lines lighter
with every pin still selected on the page — and the Gate 2 tautology it carried
at **two** sites, in the original decision and in its reproduction, is fixed from
one authored artifact.

---

## The correctness defect this rewrite uncovered (cite this from the 15-21 audit)

**Lineage strict equality (INV-CH7-47) was comparing a value against itself in
this example twice over: in the original decision, and again in the reproduction
that exists to prove that decision.**

Pre-rewrite, `GridLoadPlan(required=...)` was fed from `operators.keys()` in the
record phase (`run.py:668`) and from `self._registry().keys()` in
`GridReplayEnvironment.resolve_plan` (`run.py:486`). Gate 2 exists to catch a
producer misdeclaring what ran; with both ends sourced from the operator
registry, it could not. And because the replay environment reconstructed the plan
the same way, a forensic replay of this decision re-ran the same non-check — so
the file whose entire subject is audit-by-construction was, at this one seam,
auditing nothing.

This is a **correctness defect, not an ergonomics one**, and it was invisible
until `product-class.yaml` gave the declared side an authored source independent
of the engine's resolution. It is direct evidence that this phase's artifact
reshaping paid a correctness dividend beyond line counts: no measurement of
`removable` lines would have surfaced it, and no test could have caught it while
the only available "declaration" was the thing being declared about.

Mutation probes B and C below demonstrate the regression is now caught — probe C
in the precise shape 15-13 R6 warns is *not* detectable by editing the artifact
alone.

---

## Measurement

| Figure | Before | After |
| --- | ---: | ---: |
| mechanical (`removable`) | 175 | 12 |
| helpers | 49 | 0 |
| inline operator block | 77 | 0 |
| boot | 8 | 0 |
| registration prologue | 41 | 12 |
| relocatable (asserts + prints) | 130 | 0 |
| raw lines | 1320 | 1105 |

Removal and relocation are reported separately and never summed (D-12). The plan
predicted 176 mechanical lines removed; the achieved figure is 163, because 12
`reg` lines survive on purpose — the five author-versioned classes plus the two
SDK classes the manifest cannot address are registered by the driver, and the
MaxTTL/product-class pair is the D-15A line.

Artifact documents went from 11 files (nine of them multi-class bundles) to 28.

---

## The pin discipline, which was this plan's whole point

`ResolvedPins` is never handed to `build_replay_record`. Both record builders
construct their `PolicyBinding` from an explicit key lookup:

```python
policy_version = booted.pins.version_for("policy-bundle")
...
policy_bindings=(PolicyBinding(key="policy-bundle", version=policy_version),)
```

Verified by grep — `pins` appears as an argument to `build_operator_registry`
and to the replay environment (both need it to complete the policy operator's
admitted-bundle set under D-IMPL-76) and nowhere near the record builder — and
verified by mutation, below.

---

## The Gate 2 tautology was doubled here

Pre-rewrite, `GridLoadPlan(required=...)` was fed from `operators.keys()` in the
record phase (`:668`) **and** from `self._registry().keys()` in
`GridReplayEnvironment.resolve_plan` (`:486`). So lineage strict equality
compared a value against itself in the original decision *and* again in the
reproduction that exists to prove the original. Both now read
`required_operator_keys` off `product-class.yaml`.

That doubling is why this example's `resolve_plan` deliberately does not call its
own `resolve_operators`: the two are separate mechanisms and the replay engine
compares what they produce.

---

## Mutation probes

Each was injected, run, and reverted; none is committed.

| Probe | Injection | Caught by |
| --- | --- | --- |
| A | `expected.yaml` `entity_count: 2 → 3` | `test_the_served_payload_matches_the_declared_expectation` |
| B | `required=operators.keys()` in the record phase **and** a key dropped from `product-class.yaml` | `ReplayDivergence` from the SDK at fixture setup — the record ran four operators and the replay environment planned three |
| C | the tautology at **both** sites plus the dropped key | `test_every_declared_operator_actually_ran` — the artifact declares three, the engine resolved four |
| D | `pins.version_for("perspective")` instead of `"policy-bundle"` for dimension 2 | `ReplayUnresolvable` — a mis-selected pin makes the record unreplayable, which is the strongest possible answer |
| E | the "mutated" record copy left unmutated | `test_dimension_2_the_record_is_version_sensitive` |
| F | `override=None` — the human's substitution dropped from the record | `test_dimension_2_carries_both_override_values` and `test_the_override_resolved_as_the_artifact_directed` |

Probe C is the one that matters most: it is the exact shape 15-13 R6 warns is
NOT detectable by editing the artifact alone, and it is detected here because the
test compares the artifact's declaration against the engine's own resolution.

One assertion was **found wrong by probing and rewritten**, not merely confirmed.
`test_the_approver_signed_the_hash_of_what_they_were_shown` first hashed the
workflow state record live, and failed: the resume mutates that record, so it was
comparing the suspended event's hash against the *completed* workflow's. The
spine now captures `suspended_state_hash` at suspension. Left as written, it
would have been a check that fails for a reason unrelated to what it claims — and
after a lazy "fix" (dropping the comparison) it would have passed while proving
nothing.

---

## The replay record's content address moved, and here is the correlation

**No stored fixture was regenerated, because none exists.** There is no committed
expected-output file, no pinned checksum manifest and no stored replay record
under `examples/06-decision-replay/`; every address is produced into a per-run
temp dir and asserted within the same run. The addresses nonetheless moved, so
the correlation was done anyway — 15-16's method, not a diff read.

Both records were captured against the **same unchanged SDK** (`git diff
af19108..HEAD -- src runtime tools` is empty), one from the pre-rewrite example
materialised at the base commit, one from the rewrite, and diffed leaf by leaf.

Record address `348b3a67…` → `a2dad69e…`. **10 leaves moved, 36 unchanged, none
added or removed.**

| Moved leaf | Root cause |
| --- | --- |
| `policy_bindings.bindings[0].key` | the short manifest key `policy-bundle` replaces the long namespaced one (15-13 R3; Dave's ruling at 15-16's checkpoint) |
| `policy_bindings.bindings[0].version` | the policy bundle is now a `DeclaredArtifact` envelope document, not a bare mapping |
| `context_fabric_snapshot.store_watermark` | L2 stamps the in-force policy version onto every claim |
| `context_fabric_snapshot.graph_snapshot_id` | derived from the watermark |
| `steps[0].parameter_hash` (policy) | `permitted_policy_bundle_versions` carries the moved version, and the parameters now come from `ccf.operator-parameters.policy` |
| `steps[2].parameter_hash` (temporal) | the operator is built from the `ccf.operator-parameters.temporal` artifact rather than a hand-built `TemporalAsOfParameters` |
| `steps[3].parameter_hash` (traversal) | same, from the traversal artifact |
| `content_generation_path.product_content_address` | the product's `lineage.policy_bundle_versions` carries the moved version |
| `content_generation_path.workflow_step_sequence` | timestamps shift by 7 ticking-clock seconds: `load_and_boot` plus the driver's own registrations make more clock reads before the workflow's first transition than the old prologue did |
| `policy_bindings.hitl_actions` | contains those same action timestamps and the suspended state's hash, which follow from the line above |

**Untraceable leaves: none.**

**Approved at the blocking checkpoint (Dave, via the orchestrator).** The
orchestrator independently re-verified three claims before taking it to Dave and
all three held: that `git diff af19108..HEAD -- src runtime tools` is empty, so
both records came from the same SDK; that `pins` is never passed to
`build_replay_record`; and that the audit clock is artifact-seeded and monotone,
so the 7-tick shift is a counted consequence of more registrations rather than
wall-clock flakiness.

Two independent confirmations, worth more than the argument:

1. **Exact substitution.** Putting the pre-rewrite policy version back into the
   post-rewrite product's lineage reproduces `7d716742…` — the pre-rewrite
   product content address — **byte for byte**. So the product address's movement
   is explained by the policy version and by nothing else.
2. **Negative controls.** `steps[1].parameter_hash` (similarity) is
   byte-identical, because `build_operator_registry` constructs
   `SimilaritySelectParameters` explicitly rather than passing the artifact
   through — which is exactly why the other three moved and this one did not. So
   are `model_version.*` (all seven leaves), the whole of
   `perspective_conditioning` including `agent_definition_hash` and
   `grant_set_hash`, `operator_plan`, every `operator_key`/`category`,
   `temporal_boundary`, `touched_entities`, `recorded_at` and `tenant_id`.

---

## Deviations from Plan

### Deliberate departures, each reasoned

**1. `# ccf-schema: deferred(15-21) …` rather than the plan's
`# no-schema: DeclaredArtifact`.** The plan named a marker the tooling does not
implement; `check_schema_headers.py` recognises
`# ccf-schema: deferred(<plan>) <reason>`, and 15-16 hit the same thing one wave
ago. Used on `hitl-policy.yaml` and `scope-mapping.yaml`, and recorded in the
surface-change fragment on top of the marker as the plan requires.

The reason is a **real gap in the schema-export surface**, and it is the one
finding here that outlives this plan. `ccf.hitl-policy` and `ccf.scope-mapping`
are SDK-owned classes with no committed schema: absent from
`SDK_ARTIFACT_CLASSES` (so no manifest can name them) *and* absent from
`author_versioned_classes()` (so `dump_schemas.py` emits nothing). The
`DeclaredArtifact` envelope route is **not** an escape hatch for them — these
documents genuinely ARE their SDK classes, and wrapping them would hide each
class's own contract from the checker, which is the anti-pattern in reverse.
`ccf.scope-mapping` additionally lives in `/runtime`, so emitting it cannot
follow the `/src`-rooted route. Closing this needs a third emission bucket:
SDK-owned, registered through `register_typed`, not manifest-addressable.

**Closure is assigned to the ORCHESTRATOR, between Waves 11 and 12 — not to
15-21, and not to this plan** (Dave, at this plan's checkpoint). Two reasons were
given: a concurrent wave inventing a third bucket risks the ordering collision
15-14 and 15-15 already produced once, and 15-21 is a six-task checkpoint plan
that already owns the surface regeneration and the Criterion 1 audit, which is
exactly where deferred debt gets rushed.

So the markers name `15-21` as the closing plan because that is the string the
tooling requires and the wave the gate arms at — but **15-21's auditor should not
go looking for this work, and should not assume it was dropped.** It is the
orchestrator's, done after Wave 11 merges and before Wave 12 dispatches, the same
way the missing `after/` writer was fixed before Wave 9. Both markers and both
reasons stay exactly as committed.

**2. The negative probes stay in the spine as preparation and move to the test as
assertions.** The version-sensitivity probe's mutated copy is built and stored by
`run.py` (the guide publishes that block) and the refusal is asserted with
`pytest.raises(ReplayUnresolvable)` in the test. The moving-target probe moved
wholly to the test. The guide's prose was corrected accordingly — `docs-strict`
catches an orphaned include but not a mis-pointed one (15-13 R9), and the
version-sensitivity paragraph had become false.

**3. `run()` leaves the fabric handle OPEN**, unlike the quickstart's. The replay
leg reads through `booted.handle.reader`, and so does the test's own
`ReplayUnresolvable` probe. `main()` closes it; the test fixture closes it in a
`finally`.

**4. `_registry` was folded in, not kept.** The plan left this open. It became
`GridReplayEnvironment.resolve_operators` calling `build_operator_registry`
directly — nine lines to five, and it does nothing the manifest path does not.
What was *not* folded is `resolve_plan`'s independence from it; see above.

**5. Assertion count: 67 → 69, and the reconciliation is in the test docstring.**
The pre-rewrite file's 67 `assert` statements included 14 pure `isinstance`
narrowings over values whose types `load_artifact` and the result dataclass now
fix. Those are named individually in the module docstring as *absorbed*, not
lost, so the count reconciles rather than being asserted to.

### Auto-fixed issues

None. The rewrite ran clean on its first execution; the three test failures on
first run were in the new test module and are described under mutation probes
(one genuine assertion defect) and as two straightforward wiring fixes
(`resolve_latest` rather than `state_store.get` for the HITL policy, and a
leftover helper reference).

---

## What I did not touch

`docs/surface/v0.2-surface.json`, the frozen baseline, `make surface`,
`examples/04-cross-process/`, `public/how-to/run-agents-cross-process.md`, and
every include line in `adopters-guide.md` that names an example other than 06.
`make measure-examples` was always run with `ONLY=examples/06-decision-replay`;
`git status` confirms exactly one `after/` fragment changed and it slugifies from
this example's tree.

---

## Tasks completed

| Task | Commit | What |
| --- | --- | --- |
| 1 | `4dfe0ca` | Reshape 11 bundles into 28 typed per-class documents with a manifest; rewrite `run.py` to the call spine; fix the doubled Gate 2 tautology; re-point the guide's three snippet markers and correct the prose the rewrite falsified |
| 2 | `980d465` | Relocate 69 assertions into 33 dimension-grouped tests; write the surface-change fragment |
| 3 | this commit | Blocking checkpoint — **approved**. No fixture on disk was regenerated (none exists); the record-address movement was correlated leaf by leaf and every moved leaf traced. Both `deferred(15-21)` markers stay, with closure reassigned to the orchestrator |

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `pytest tests` | 1884 passed, 2 skipped |
| `pytest tests/examples/` | 202 passed |
| `pytest tests/examples/test_decision_replay_output.py` | 33 passed |
| `make examples` | exit 0 — all ten |
| `make example-06` | exit 0 |
| `make docs-strict` | exit 0 |
| `make schema-headers DIR=examples/06-decision-replay/artifacts` | exit 0 |
| `grep -cE "^def _(load\|instant\|resolution_spec\|envelopes\|operators)"` | 0 |
| `pins` passed to `build_replay_record` | 0 occurrences |
| surface manifest + frozen baseline | untouched |

The full-suite run initially failed `test_surface_audit.py` twice, because task
2 added lines to `run.py` after task 1's measurement. Re-measured with `ONLY`;
green.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. `ArtifactTokenSource` stopped re-reading the token file on
every lookup and now holds the entries `load_and_boot` parsed once — strictly
fewer reads of credential material, and one fewer opportunity for the table the
door authenticates against to drift from the table the manifest validated.

## Self-Check: PASSED

All files claimed above exist on disk; both commit hashes resolve in `git log`.
