---
phase: 15
round: 2
context: mid-execution (plans 15-01..15-06 complete; 15-07 paused at human gate)
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-08-04T21:50:37Z
plans_reviewed: [15-01..15-21]
supersedes: none — round 1 (planning-time) is preserved in 15-REVIEWS.md
---

# Cross-AI Plan Review (Round 2, mid-execution) — Phase 15

Round 1 (`15-REVIEWS.md`) reviewed the plans before execution. This round was run
after wave 3, with plans 15-01..15-06 merged and 15-07 paused at its human gate.
Reviewers were given the completed plans' SUMMARY.md files as execution status and
told to weight unexecuted plans (15-08..15-21) most heavily.

**Self-review skipped:** `claude` was excluded for independence (this orchestrator
runs inside Claude Code).

---

## Gemini Review

# Phase 15 Plan Review: SDK Ergonomics — The Integration Surface

## 1. Summary
The implementation plans for Phase 15 are exceptionally well-structured, demonstrating a sophisticated "defense in depth" approach to ergonomics. By prioritizing **standing guards** (15-02) and **executable audit baselines** (15-03) before building the high-level helpers, the plans ensure that "simplification" never comes at the cost of whitepaper fidelity. The strict adherence to **D-15A (Marshalling/Wiring only)** is enforced not just by prose, but by AST-based structural tests that prevent the "governance collapse" where a helper might accidentally swallow a validation gate. The sequencing correctly builds the typed artifact foundation (15-07..15-09) before the high-level manifest loader (15-10) and operator builder (15-11), ensuring a robust, closed-world integration surface.

## 2. Strengths
*   **Guard-First Implementation**: Landing the gate-independence guard (15-02) and the widened No-Hardcoding lint (15-04) before any ergonomics helper exists is a mature engineering pattern that treats architectural invariants as non-negotiable.
*   **D-15A Boundary Rigor**: The plans for `load_and_boot` (15-10) and `build_operator_registry` (15-11) are surgically designed to stay on the correct side of the abstraction line. Specifically, keeping the pin selection (Decision Replay Dimension 2) and the `run_gates` inputs (Gate 2) explicit in adopter code is a critical success factor.
*   **Falsification-Driven Planning**: Plan 15-03's spike into assumptions A1, A3, and A6 is a high-signal move that de-risked the sizing of the most expensive plans (15-07, 15-12, 15-04) before they executed.
*   **Replay Record Integrity**: The introduction of **D-IMPL-80 (role-based manifest entries)** in plan 15-10 is a brilliant solution to the "Signal-Batch-in-Replay" trap, ensuring raw data never content-hashes into the Control Plane by accident.
*   **Executable Surface Audit**: Moving from the ROADMAP's estimated line counts to a reproducible AST measurement (15-03, 15-21) provides honest, auditable proof of the ergonomic win.

## 3. Concerns
*   **HIGH: Import Cycle Complexity (15-07)**: The plan to relocate the versioned base to `artifact_base.py` to break the `artifacts -> worker -> registry -> artifacts` cycle is sound, but this is a high-friction architectural shift. Any deviation in implementation here could break the cold-interpreter import guarantee (C-12).
*   **MEDIUM: High-Churn Wave 11 (15-17, 15-18)**: Plans 15-17 and 15-18 are the "danger zone." 15-17 handles the most complex replay assertions, and 15-18 performs a simultaneous surface rewrite and domain change. The requirement for separate commits is critical but requires high reviewer vigilance at the checkpoints.
*   **LOW: Snippet Marker Drift**: The 92 snippet markers being re-pointed across the suite (15-13..15-20) are a significant maintenance burden. While `make docs-strict` catches orphans, it cannot catch markers that bracket the *wrong* logical block.
*   **LOW: CLI Invariant (15-12)**: While D-IMPL-79 preserves the "no privileged paths" posture, it forces a local generation task (schema export) through an HTTP route. This is correct for fidelity but adds complexity to the runtime.

## 4. Suggestions
*   **15-07 (Resolution Spec)**: Since this change triggers a suite-wide expected-output regeneration, consider adding a temporary "regeneration sanity check" script that diffs the old and new pins to ensure *only* resolution-spec hashes changed, and no other pin was disturbed.
*   **15-11 (Operator Builder)**: The docstring should explicitly cite **INV-CH7-26 (Policy-after-Similarity)** to explain why the builder refuses to let callers declare operator categories. This educates adopters on the underlying CCF algebra.
*   **15-21 (Phase Close)**: In the "Required Behavior Surface" test (Assertion 5), consider extending the required list to include any artifact format that underwent a major translation (like `ccf.signal-batch`), ensuring the curated log remains the authoritative migration guide.
*   **Example Rewrites**: For 15-14 through 15-20, ensure the `after/` fragments are generated *after* the `$schema` headers and docstring updates are applied, as those lines contribute to the `raw` and `imports` counts.

## 5. Risk Assessment
*   **Overall Risk: LOW**
*   **Justification**: The phase is exceptionally well-instrumented. The potential for architectural regression is capped by the 15-01 baseline and the 15-02 guards. The blast radius of the highest-impact change (15-07 `semver`) is isolated with a dedicated regeneration checkpoint. The plans are grounded in actual repository measurements (15-03) and follow established patterns (15-PATTERNS), making the likelihood of a major design mismatch very low. The primary remaining risk is execution-time "fatigue" during the volume of example rewrites, which the "recipe" approach (15-13) effectively mitigates.

---

## Codex Review

## Summary

The phase plan is unusually rigorous and mostly coherent after the completed 15-01..15-06 work. The remaining plan chain correctly protects the main Phase 15 goal: absorb marshalling and wiring without hiding governance decisions. The biggest risks are not conceptual drift but a few concrete execution gaps in 15-07..15-21: incomplete surface-log accounting, schema-header validation that may prove too weak, possible overconstraint in `required_operator_keys`, and `load_and_boot` ordering around failure paths.

## Strengths

- The dependency chain is mostly sound, especially the strict `artifacts.py` sequence: `15-07 -> 15-08 -> 15-09 -> 15-10`.
- The completed 15-01..15-06 work leaves the remaining plans coherent: drift fragments, test-scope linting, timestamp behavior, and class lookup are all usable foundations.
- D-15A is treated seriously. The plans repeatedly keep `run_gates`, replay pin selection, MaxTTL registration, and `required_operators` independence visible in adopter code.
- The single-owner manifest regeneration rule is well designed and prevents mid-phase merge churn.
- The example rewrite plans preserve domain/artifact ownership and explicitly protect high-value demonstrations: harness portability, HITL audit capture, replay, A2A admission, and external zero-import clients.

## Concerns

- **HIGH — 15-07 surface-change accounting appears internally inconsistent.** Task 4 says to write “two entries,” but the planned public diff likely includes `RESOLUTION_SPEC`, `EntityResolutionSpec` reshape, new `ccf.controlplane.artifact_base.*` exports, and possibly `ccf.controlplane.artifacts.VersionedArtifact` / `validate_semver` re-exports. If not corrected before 15-07 completes, 15-21’s completeness test will fail late.

- **HIGH — 15-09 `required_operator_keys: min_length=1` may overconstrain valid deployments.** Plans 15-14/15-19 explicitly rely on examples with partial or no operator sets. A product/projection requiring zero operators should still be representable if the gate compares declared vs resolved empty sets. Consider allowing an empty tuple unless the whitepaper requires at least one operator.

- **HIGH — 15-10 should preflight backend arguments before registration.** The plan tests malformed documents register nothing, but a manifest declaring `postgres` without `postgres_dsn` could still parse and register artifacts before failing at boot unless explicitly checked first. That leaves Control Plane state from a fabric that never booted. Validate backend kind + required connection argument before any registration, and assert the registry/audit log is unchanged on this refusal path.

- **MEDIUM — 15-12/15-21 schema header tests may prove only path existence, not correctness.** A YAML file could point to an existing but wrong schema. The tree-wide gate should cross-check each manifest entry: artifact path -> declared `class_id` -> expected `docs/schemas/<class-id>.json` header. Also confirm the header path is editor-resolvable from the YAML file location, not just repo-root-resolvable in tests.

- **MEDIUM — public behavior of `resolve_artifact_class` changes repeatedly but may not be logged as behavior.** 15-07..15-10 add SDK class ids to `SDK_ARTIFACT_CLASSES`; the signature manifest may not see constant-value changes. The added artifact class entries may be enough for humans, but the curated log should explicitly say those class ids now resolve to typed contracts rather than `DeclaredArtifact`.

- **MEDIUM — 15-11’s “indices differ” corpus-boundary test may be brittle.** If equality is identity-based or the second ingest does not affect token material, the test can mislead. Prefer asserting observable query results or index corpus contents/counts tied to the changed boundary.

- **MEDIUM — 15-21 embeds cross-project credential instructions.** Referencing `/home/parkave/homecams_v2/.env` in a phase plan is brittle and increases secret-handling risk. The plan should name required env vars and authentication steps, but not a specific unrelated project path.

- **LOW — assertion relocation checks lean on assertion counts.** “At least as many assertions” can be gamed with weak assertions. The docstring provenance mapping helps, but the highest-risk examples should also preserve named semantic checks: replay dimensions, HITL audit fields, A2A refusal, two-harness equivalence.

## Suggestions

- Fix 15-07 before leaving the human gate: run `dump_surface.py --report`, list every added/reshaped public name, and make the fragment match exactly.
- Relax or justify `ProductClassDeclaration.required_operator_keys` cardinality in 15-09.
- In 15-10, validate tenant/backend/connection invariants before reading/registering artifacts; add refusal-path tests that registry audit remains empty.
- Strengthen 15-21 schema-header gate to verify headers against manifest-declared `class_id`, not just file existence.
- Add behavior entries or explicit migration text for `resolve_artifact_class` whenever new SDK-owned ids stop falling through to `DeclaredArtifact`.
- Replace the 15-11 corpus inequality assertion with a result-level assertion proving the later boundary sees newly ingested corpus material.
- Move `/gsd-review` credential sourcing out of the plan text and into environment setup docs or local operator notes.

## Risk Assessment

**Overall: MEDIUM.** The architecture and sequencing are strong, and completed plans 15-01..15-06 did not leave the remaining work incoherent. The remaining risks are concrete and fixable, but several are late-failure risks: surface-log incompleteness, schema header mismatch, and partial registration on boot refusal would likely emerge only in later integration or 15-21 closeout unless addressed now.

---

## Cursor Review

## Summary

Plans 15-01–15-06 left a coherent foundation (surface drift, D-15A guard, audit baseline, lint scope, timestamps, class lookup). The remaining chain 15-07→15-11 is well-aligned with D-15A/D-01–D-08 and the decided D-IMPL-76/77/79/80 rulings, and the example rewrite recipe (15-13+) correctly keeps gate/pin/HITL governance in adopter code. The highest actionable risks sit at the 15-07 gate and just after it: required `semver` on `EntityResolutionSpec` has a much wider call-site blast radius than `files_modified` admits; 15-07’s surface-fragment acceptance criteria under-count exports; and rewrite plans tell executors to emit `after/` fragments via `make measure-examples`, but that tool today only writes `before/`. Fix those before continuing past the human gate; otherwise the phase design still achieves ERGO-01–17.

## Strengths

- D-15A is enforced early and mechanically (15-02 perturbation + AST + lint), then restated on `load_and_boot` / `build_operator_registry` so helpers stay wiring-only.
- Policy pin posture (15-08 incomplete artifact + 15-11 adopter-passed `ResolvedPins`) correctly implements D-IMPL-76 and avoids a silent empty-admission fail-open.
- D-IMPL-80 `role: register|load` is threaded consistently through 15-09/15-10/15-13 and into 15-21’s audit narrative.
- Artifact chain ordering (15-07→08→09→10) and single-owner surface regeneration (15-01 / 15-21) are sound concurrency design.
- Example rewrite recipe (15-13) is explicit about what must stay in adopter code (`run_gates`, MaxTTL/`register_product_class`, pin→`build_replay_record`) and why.
- Parallel rewrite waves use path-disjoint `after/` ownership and (mostly) serialize shared `public/tutorial/adopters-guide.md` edits via depends_on.
- Phase close (15-21) pairs documented-drift with name-level bidirectional completeness, plus tree-wide `$schema`, D-14, and G-B AST gates — the right endgame for Criterion 6.

## Concerns

- **[HIGH] 15-07 — `semver` blast radius understated.** Making `EntityResolutionSpec` a required-`semver` `VersionedArtifact` breaks every current constructor (~9 examples, several tests, `perf/conftest.py`) immediately. `files_modified` omits those sites; Task 3’s “expected-output regeneration” does not cover “add `semver=` to every constructor.” Without an explicit call-site update task (or a scoped CI-green path), the plan stalls red before the hash checkpoint, or executors improvise.

- **[HIGH] 15-07 Task 4 — fragment/acceptance mismatch.** Action text requires claiming `RESOLUTION_SPEC`, `EntityResolutionSpec` reshape, and `artifact_base` exports (`VersionedArtifact`, `validate_semver`, `ArtifactClass`), but acceptance says “two entries.” Under-claiming fails 15-21’s subset cross-check; over-claiming without `--report` agreement fails the standing drift contract. Fix the fragment checklist to match `--report` exactly before leaving the gate.

- **[HIGH] 15-13..15-20 — `after/` emission path missing.** `tools/measure_examples.py` only writes `docs/surface/examples/before/`. Rewrite plans instruct `make measure-examples` to produce `after/` fragments. As written, Criterion 1’s after-side is unimplemented. Need an `--after`/path-filter mode (or a dedicated writer) in 15-13 (or a tiny pre-13 fix), and rewrite plans must write only their own slugs to avoid concurrent overwrite.

- **[MEDIUM] 15-08 — Pydantic multiple-inheritance risk.** `*ParametersArtifact(OperatorParametersArtifact, *Parameters)` diamonds two `CCFContract` bases. Likely fine, but worth an early smoke in Task 1 before docstring/docs-strict work; a MRO/`model_fields` surprise would block the whole operator-parameters wave.

- **[MEDIUM] 15-07 A3 carry-forward vs registry bump check.** 15-03’s note that “D-05 bump check needs `artifact_version`” conflates `register_versioned` (author `artifact_version`) with SDK `semver` + `register_typed` (content-hash only). Choosing `VersionedArtifact.semver` is correct for resolution-spec; the plan should say so explicitly so executors do not add a second version field or call `register_versioned` by mistake in 15-10.

- **[MEDIUM] Shared `public/` edit collisions.** 15-13 touches several reference pages; wave-10 plans also touch how-tos. `adopters-guide.md` is serialized for 17→19, but 15-13 vs later include re-points still rely on “touch only your markers.” Easy to silently break Phase 16 includes if a plan rewrites shared prose.

- **[MEDIUM] 15-12 schemas freeze timing.** Schemas commit at wave 8 from `SDK_ARTIFACT_CLASSES`. That is fine if 15-07..10 are truly done first; any late artifact-class tweak after 15-12 forces a second schema regeneration nobody owns until 15-21. Prefer an explicit “no new ArtifactClass after 15-10” note, or have 15-21 re-run `make schemas`.

- **[MEDIUM] 15-11 corpus extraction underspecified.** Quickstart builds corpus with a concrete comprehension over `view.entities`. The plan says “read the corpus out of `view` using `similarity_corpus_attribute_by_class`” but does not pin missing-attribute / missing-class behavior. Silent skip vs refuse-never-repair should be stated so nine examples do not diverge.

- **[LOW] 15-08 Task 2 `make docs-strict`.** Couples operator-parameters landing to the docs toolchain while DOCS-* is still pending. Prefer `make typecheck` + docstring assert for 15-08; keep docs-strict for rewrite waves.

- **[LOW] Completed 15-02 plan text vs execution.** Plan required `Public surface: true` for empty `__all__`; execution correctly chose `false`. Not worth rework; do update any stale planner copy that still asserts the old criterion so 15-21 reviewers do not chase a ghost.

- **[LOW] 15-19 `_register_closure` left open.** Correct stop-and-decide posture, but it can pause wave 12 mid-flight. Pre-decide “manifest-register vs leave in adopter code” against CLAUDE.md §8.1 before starting 15-19.

## Suggestions

1. **Before resuming 15-07:** add an explicit Task (or expand Task 3) to update every `EntityResolutionSpec(...)` with `semver=...`, list those paths in `files_modified`, and separate “constructor churn” from “pin/hash regeneration” in the human review diff.
2. **Rewrite 15-07 Task 4 acceptance** to: claim every `--report` added/reshaped FQ name; assert `ArtifactClass` not under `removed`; drop the contradictory “two entries” line.
3. **Extend `measure_examples` in 15-13 Task 0** with `after/` output and optional path prefix; require rewrite verifies to assert only owned slugs under `after/`.
4. **In 15-10 docstring/tests:** state `register_typed` (not `register_versioned`) for SDK `semver` artifacts; keep D-05 author-version path for agent/prompt classes.
5. **In 15-11:** specify corpus builder semantics (skip vs refuse) and assert them in test 2/3b.
6. **Add 15-21 (or 15-12 follow-up) `make schemas` refresh** so schema drift from any late class tweak is owned.
7. **Pre-rule 15-19 workflow-definition registration** so the plan is autonomous as labeled.

## Risk Assessment

**Overall: MEDIUM** (locally **HIGH** until 15-07 call-site + fragment criteria and the `after/` measurement gap are fixed).

Justification: governance design, dependency order, and D-IMPL rulings are strong and match what 15-01–15-06 already shipped. The phase can still hit ERGO goals. The near-term failure modes are executable-plan defects (incomplete blast radius, broken measurement instruction, fragment under-claim), not conceptual ones — and they sit exactly on the critical path of the paused 15-07 gate and the first rewrite wave.

---

## Ollama Review (qwen3.5:397b-cloud)

# Phase 15 Cross-AI Plan Review — MID-EXECUTION

## Summary

Phase 15 is a well-structured ergonomics phase with strong governance discipline. The completed plans (15-01–15-06) establish solid foundations: surface drift detection, the `ccf.deployment` package shell with D-15A guards, audit baselines, lint scope widening, timestamp handling, and class-ID lookup. The remaining plans (15-08–15-21) are coherent with what's built, though several dependency risks exist in the artifact-class chain and example-rewrite wave. The phase's greatest strength is its executable completeness guarantees; its greatest risk is the tight coupling between 15-07's content-hash churn and all downstream plans.

---

## Strengths

- **Executable completeness guarantees** — `tests/test_surface_completeness.py` (15-21) provides bidirectional, name-granular cross-checks between the curated log and generated diff. This is rare rigor.
- **D-15A abstraction line is mechanically enforced** — 15-02's AST guard + import ban on `ccf.deployment` → `ccf.products.gates` prevents the most likely governance collapse before any helper exists.
- **Single-owner regeneration rule** — Only 15-01 and 15-21 write `docs/surface/v0.2-surface.json`, preventing stale manifests across 11 concurrent waves.
- **Behavior-change classification** — The `behavior` change type (15-01 README) captures signature-invisible changes like D-02's timestamp handling, which a pure diff would miss.
- **Per-file measurement fragments** — 15-03's `docs/surface/examples/before/` and `after/` structure allows parallel example rewrites without collision.
- **Two-commit separation for 15-18** — Surface rewrite and re-domaining are separate commits, preventing rewrite defects from hiding inside domain changes at the A2A trust boundary.

---

## Concerns

### HIGH

1. **15-07 content-hash churn cascades through all downstream plans** — Adding `semver` to `EntityResolutionSpec` changes `content_hash(spec)`, therefore every `resolution_spec_version` pin, therefore every replay record carrying one. Plans 15-08 through 15-20 all depend on 15-07's regeneration being complete and correct. If 15-07's Task 3 checkpoint (human-verify) finds non-hash changes in the diff, the entire phase blocks.
   - *Mitigation in plan:* Task 3 is a blocking checkpoint. However, no rollback plan exists if the diff reveals semantic changes.

2. **15-10 manifest → 15-11 operator builder dependency is tight** — 15-11's `build_operator_registry` requires `ResolvedPins` from 15-10's `load_and_boot`. If 15-10's pin-set structure changes (e.g., `version_for` gains a second accessor), 15-11 breaks. The plans acknowledge this but have no contract test between them.
   - *Missing:* A shared fixture or interface test that 15-10's `ResolvedPins` satisfies 15-11's expectations.

3. **15-12 schema headers delegated to example rewrites (15-14–15-20) with tree-wide gate only at 15-21** — If an example rewrite plan forgets the `$schema` header or points it at a nonexistent path, the failure is caught only at 15-21 Task 4, the phase's most expensive point. Each rewrite plan has its own acceptance criterion, but no per-plan gate.
   - *Risk:* A plan could pass its own verification but fail the tree-wide gate, requiring rework after all other plans are merged.

### MEDIUM

4. **15-08 policy artifact incompleteness is structural but untested end-to-end** — `PolicyFilterParametersArtifact` deliberately omits `permitted_policy_bundle_versions`, making it unusable as an operator parameter set without 15-11's builder. Plan 15-08 Task 3 tests this in isolation, but there's no integration test proving the full path: manifest → `load_and_boot` → `build_operator_registry` → working `PolicyFilter`.
   - *Gap:* The integration test exists in 15-11, but 15-08's test suite doesn't verify the builder actually completes the artifact correctly.

5. **15-09 signal-batch `role: load` distinction relies on docstring + 15-10 enforcement** — D-IMPL-80 requires `role` to be explicit with no default. 15-09's `SignalBatch` docstring states it's a `role: load` artifact, but nothing prevents an adopter from marking it `role: register` in their manifest. 15-10 Task 3 test 9 asserts the fixture's signal batch is not registered, but doesn't assert that marking it `role: register` would be a *mistake* (vs. merely allowed).
   - *Risk:* An adopter could register a signal batch, content-hashing raw event data into replay dimension 2, without any CI failure.

6. **15-13 through 15-20 all share `public/tutorial/adopters-guide.md`** — Five plans re-point snippet includes in the same Markdown file. The plans note this and serialize via dependency ordering (15-13 → 15-14/15/16 → 15-17 → 15-19), but concurrent worktrees could still conflict if the dependency graph isn't enforced at merge time.
   - *Mitigation in plan:* Each plan touches "only the include lines naming its own example." However, `make docs-strict` catches orphaned includes, not mis-pointed ones.

7. **15-21 Task 4 Gate 3 (`required_operators` guard) scans `examples/` but rewritten examples should have zero violations** — The guard asserts it finds "at least nine `required_operators` implementations." After 15-13 through 15-20 rewrite all examples to use `ProductClassDeclaration.required_operator_keys`, the guard might find fewer implementations (some projections may be artifact-only now). The vacuity threshold needs updating.
   - *Risk:* The guard could fail vacuously if the rewrites reduce the number of Python-based projections.

### LOW

8. **15-05 timestamp handling has no migration test for existing callers** — D-02 changes `load_artifact`'s behavior: timestamp-shaped scalars now arrive as `str` instead of `datetime`. Plan 15-05 Task 2 tests the new behavior but doesn't test that existing callers (e.g., example code using untyped fields) fail gracefully or migrate cleanly.
   - *Mitigation:* The surface-change fragment (15-05) documents the migration, but no test asserts the error message is actionable.

9. **15-06 class-lookup anti-drift test scans module attributes, not `__all__`** — This was a necessary deviation (the two shipped `ArtifactClass` instances aren't in `__all__`), but it means the test could pass while `__all__` drifts from the hand-maintained mapping. The vacuity guard asserts at least two constants are found, but doesn't assert `__all__` is the source of truth.
   - *Risk:* Future plans adding `ArtifactClass` constants might add them to the mapping but forget `__all__`, or vice versa.

10. **15-16 demo narration regeneration is a blocking checkpoint but has no automated diff validator** — Task 3 requires human review of the narration diff, confirming every changed line traces to a code change. This is necessary but subjective; a tired reviewer could miss a narration edit that "makes a comparison pass" rather than reflecting a real change.
    - *Gap:* No automated check that narration changes correlate with code changes (e.g., line-number mapping).

---

## Suggestions

1. **Add a 15-07 → 15-11 integration test** — Create a minimal test in 15-11 that boots a fabric via 15-10's `load_and_boot`, builds an operator registry via 15-11's builder, and asserts the `PolicyFilter` operator has the correct `permitted_policy_bundle_versions` from the pin set. This closes the gap in concern #4.

2. **Move 15-12's schema-header test to per-plan verification** — Instead of waiting for 15-21 Task 4, add a `make check-schema-headers` target that each example-rewrite plan (15-14–15-20) runs in its verify step. This catches missing headers at wave 10–13 instead of wave 14.

3. **Add a 15-10 test that `role: register` on a signal batch is warned or documented as a mistake** — Either add a lint rule that flags `role: register` on `ccf.signal-batch` entries, or add a test that asserts the manifest parser emits a warning (not an error, since it's technically valid) when a load-role artifact is marked for registration.

4. **Update 15-21 Task 4 Gate 3 vacuity threshold dynamically** — Instead of asserting "at least nine" `required_operators` implementations, assert "at least one per example directory that has a projection module." This adapts if rewrites reduce Python-based projections.

5. **Add a 15-05 migration smoke test** — Create a test that loads an artifact with an untyped timestamp field and asserts it receives a `str`, with a clear error if the caller tries to use it as a `datetime`. This proves the migration path is visible.

6. **Add 15-06 a sync test for `__all__`** — Extend the anti-drift test to assert that every public attribute of `ccf.controlplane.artifacts` that is an `ArtifactClass` instance is also in `__all__`. This closes the gap in concern #9.

7. **Add 15-16 a narration-diff correlation check** — Create a simple script that extracts line numbers from narration snippets and asserts they map to changed lines in the code diff. This doesn't replace human review but flags obvious mismatches.

---

## Risk Assessment: **MEDIUM**

**Justification:**

The phase is well-designed with strong mechanical guarantees (surface drift gates, AST guards, completeness cross-checks). The completed plans (15-01–15-06) are solid and leave the remaining plans coherent. However:

- **15-07's content-hash churn is a single point of failure** — If the regeneration checkpoint reveals non-hash changes, the entire phase blocks. This is the highest-risk dependency.
- **Schema-header delegation to example rewrites without per-plan gates** — Failures are caught only at 15-21, the most expensive point.
- **Tight coupling between 15-10 and 15-11** — No contract test ensures the pin-set structure satisfies the builder's expectations.

These are manageable risks with the mitigations already in place (blocking checkpoints, human gates), but they warrant attention during execution. The phase's strength — its executable guarantees — also means failures will be caught loudly rather than silently, which reduces overall risk.

**Recommendation:** Proceed with remaining plans, but prioritize the suggestions above (especially #1, #2, and #3) to reduce downstream rework risk.

---

## Consensus Summary

Risk verdicts: **gemini LOW · codex MEDIUM · cursor MEDIUM (locally HIGH at the
15-07 gate) · ollama MEDIUM.**

### Agreed Strengths (2+ reviewers)

- **Guard-first sequencing.** Landing the D-15A gate-independence guard (15-02),
  the widened lint (15-04), and the executable audit baseline (15-03) *before*
  any ergonomics helper exists. All four reviewers named this.
- **D-15A boundary rigor.** `load_and_boot` (15-10) and `build_operator_registry`
  (15-11) keep `run_gates`, replay-pin selection, MaxTTL registration, and
  `required_operators` independence visible in adopter code rather than absorbing
  them. (gemini, codex, cursor)
- **Single-owner surface regeneration** (15-01 at start, 15-21 at close) as sound
  concurrency design across parallel waves. (codex, cursor, ollama)
- **Executable bidirectional completeness** at 15-21 — name-granular, both
  directions, paired with the cheap standing gate. (gemini, cursor, ollama)
- **D-IMPL-80 `role: register|load`** threading, keeping raw signal data from
  content-hashing into replay dimension 2. (gemini, cursor, ollama)
- **The completed 15-01..15-06 work left the remaining plans coherent.** Stated
  explicitly by codex, cursor, and ollama.

### Agreed Concerns (2+ reviewers) — with verification status

| # | Concern | Raised by | Verified status |
|---|---|---|---|
| A | **15-07 surface fragment under-claims** the public diff; 15-21's completeness test would fail late | codex (HIGH), cursor (HIGH) | **ALREADY RESOLVED.** The in-flight 15-07 fragment claims **8** entries and explicitly asserts `ArtifactClass` is not under `removed`. Reviewers read the *plan text* ("two entries"), not the execution. Plan text was wrong; execution is right. |
| B | **15-07 `semver` blast radius understated** — every `EntityResolutionSpec(...)` constructor breaks; `files_modified` omits those sites | cursor (HIGH), ollama (HIGH) | **ALREADY RESOLVED.** 15-07 absorbed 19 files across `perf/`, `examples/`, `tests/` (+15 semver-wiring sites), committed separately as blast-radius absorption. |
| C | **`after/` emission path does not exist** — 15-13..15-20 instruct `make measure-examples` to write `docs/surface/examples/after/`, but `tools/measure_examples.py` defines only `BEFORE_DIR` | cursor (HIGH) | **REAL AND OPEN.** Verified: no `after/` writer, no `--after` flag. Criterion 1's after-side is currently unimplementable as instructed. |
| D | **Schema-header correctness is only gated tree-wide at 15-21** — a rewrite plan can pass its own verify and fail at the most expensive point | codex (MEDIUM), ollama (HIGH) | **REAL AND OPEN.** Both propose a per-plan gate; codex additionally wants headers cross-checked against manifest-declared `class_id`, not mere path existence. |
| E | **Shared `public/` prose collisions** across rewrite waves — `adopters-guide.md` touched by five plans; `docs-strict` catches orphaned includes, not mis-pointed ones | gemini (LOW), cursor (MEDIUM), ollama (MEDIUM) | **REAL AND OPEN.** Dependency ordering serializes some, not all. |
| F | **15-11 corpus/index assertions are brittle** — "indices differ" can pass without proving the boundary saw new material | codex (MEDIUM), cursor (MEDIUM) | **REAL AND OPEN.** Both want a result-level assertion; cursor additionally wants missing-attribute behavior pinned (skip vs refuse). |

### Divergent Views

- **Overall risk.** Gemini alone says **LOW**, reasoning that instrumentation
  caps the blast radius. The other three say MEDIUM, and cursor says locally
  HIGH. The divergence is largely explained by concern C: gemini did not notice
  the missing `after/` writer, which is the one finding that blocks a whole wave.
- **Whether 15-07's churn is a single point of failure.** Ollama calls it the
  phase's highest risk with "no rollback plan." Codex and gemini treat it as
  well-isolated by the dedicated checkpoint. The executed reality supports the
  calmer reading: zero committed expected outputs required regeneration, because
  every pin is runtime-computed rather than a committed literal.
- **`required_operator_keys` cardinality (15-09).** Codex flags `min_length=1` as
  possibly overconstraining deployments with zero operators; no other reviewer
  raised it. Worth a ruling before 15-09 executes.

### Recommended actions before continuing past the 15-07 gate

1. **Fix concern C first — it blocks wave 9 onward.** Extend
   `tools/measure_examples.py` with an `after/` output mode and an optional path
   filter, so each rewrite plan writes only its own slugs. Cursor suggests
   folding this into 15-13 Task 0; a small pre-13 fix is equally viable.
2. **Rule on 15-09 `required_operator_keys` cardinality** (codex) before 15-09.
3. **Add a per-plan schema-header check** (concern D) rather than deferring all
   header validation to 15-21.
4. **Pre-decide 15-19's `_register_closure`** so the plan is autonomous as
   labeled (cursor) — otherwise wave 12 pauses mid-flight.
5. **Note for the record:** concerns A and B are stale plan-text defects that
   execution already corrected. The *plan files* still contain the wrong
   guidance; if 15-21's reviewers read plan text rather than summaries, they
   will chase both. Cursor flagged the same pattern for 15-02's stale
   `Public surface: true` criterion.
