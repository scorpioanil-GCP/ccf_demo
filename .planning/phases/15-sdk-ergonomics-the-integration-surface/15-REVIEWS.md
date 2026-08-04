---
phase: 15
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-08-04T06:14:00-07:00
plans_reviewed: [15-01 … 15-21 (21 plans, 14 waves)]
self_excluded: claude (executing runtime — self-review is not independent)
---

# Cross-AI Plan Review — Phase 15: SDK Ergonomics — The Integration Surface

Four independent AI systems reviewed the full plan set (21 plans, 14 waves) together with
PROJECT.md, the ROADMAP Phase 15 section, ERGO-01..17, CONTEXT.md, RESEARCH.md, and the four
binding rulings D-IMPL-76/77/78/79. Gemini, Codex, and Cursor received the full ~467KB context;
Ollama received a condensed variant (frontmatter + objectives + must_haves) that fits its window.

## Gemini Review

# Phase 15 Plan Review: SDK Ergonomics — The Integration Surface

This plan set is an exceptionally well-structured and disciplined ergonomic overhaul. It successfully navigates the "abstraction vs. transparency" tension by grounding every helper in a strict "marshalling and wiring only" ruling (D-15A) and surrounding the new surfaces with aggressive, automated guards. The strategy for managing whole-tree manifest drift during parallel wave execution—the "Single-Owner Regeneration Rule"—is a standout piece of engineering management that should be adopted as a project standard.

## Strengths

- **Constitutional Guarding:** The decision to write the `run_gates` gate-independence guard (15-02 Task 2) and the `ccf.deployment` import ban (15-02 Task 3) *before* a single helper is written is a high-signal commitment to whitepaper fidelity. It turns a verbal agreement (D-15A) into an executable constraint that binds every subsequent plan.
- **Surface Integrity Triad:** The pair of a module-granular tripwire (15-01) and a name-granular, bidirectional completeness test (15-21 Task 2) is a robust solution to Success Criterion 6. Using JSON for the manifest to allow reviewable diffs while asserting on raw bytes for stability is a proven pattern from Phase 14 that is applied perfectly here.
- **Relocation Discipline:** The plan correctly identifies the risk of domain values escaping CINV-01 reach by moving to `tests/` and closes it structurally via D-IMPL-78 and 15-04 before any example is rewritten.
- **Structural Ordering:** The sequencing of the `EntityResolutionSpec` semver change (15-07) as an early, isolated "regeneration event" with its own checkpoint is excellent risk management. It prevents hash churn from muddying the diffs of later ergonomic changes.
- **Falsification Spikes:** Sizing subsequent plans based on measurement tasks (15-03 Task 3) rather than assumptions (A1, A3, A6) ensures the waves remain workable.

## Concerns

- **[MEDIUM] G-B Pattern-Level Drift:** Plan 15-13 Task 2 addresses the `required_operators() == operators.keys()` shortcut for the day-1 example, but this remains a pattern-level risk for adopters and future contributors. While 15-21 Section 4 records the status, there is no structural guard (like an AST check) to prevent other projection plans from adopting this shortcut, which makes the lineage gate tautological at the plan-declaration level.
- **[MEDIUM] Snippet Marker Bracketing:** The rewrite of all 10 examples will invalidate 92 snippet markers. While `make docs-strict` catches orphans, it cannot catch markers that bracket slightly wrong code relative to the surrounding prose in `public/`. The manual check in 15-21 Task 6 is necessary but places a high verification burden on the final gate.
- **[LOW] `load_and_boot` Connection Exhaustion:** 15-10 Task 2 implements `load_and_boot`. If an adopter uses this in a test loop or a multi-tenant utility without care, it could lead to backend connection leakage if the returned `FabricHandle` is not correctly disposed of. (Mitigated by the handle following the existing `boot()` contract).
- **[LOW] Schema Export UI:** 15-12 Task 2 implements `ccf schema export`. The dispatch matches the existing `RequestSpec` pattern perfectly (D-IMPL-79), but users might expect a "dump all" command to local files. This is effectively provided by `tools/dump_schemas.py` for developers, but less reachable for pure SDK adopters using only the CLI.

## Suggestions

- **[G-B Guard]** Add a specific test in `tests/products/test_gate_independence.py` that AST-scans modules containing `ContextProjection` implementations and flags any use of `operators.keys()` (or `registry.keys()`) inside the `required_operators()` method. This would close the "Shortcut G-B" hole structurally.
- **[Manifest Registry]** In plan 15-06, consider making `resolve_artifact_class` also accept a list of additional deployment-defined `ArtifactClass` objects. This would allow an adopter with specialized schemas to use the manifest path without falling back to the generic `DeclaredArtifact` envelope, while keeping the SDK's core lookup clean.
- **[Explicit Disconnect]** Extend `FabricHandle` (or the `load_and_boot` docstring) to explicitly recommend a `with` block or a `.close()` call, as the manifest path makes it much easier to "boot and forget" in a loop.

## Risk Assessment: LOW

The overall risk is **LOW** because of the aggressive front-loading of standing guards. By the time the first example is rewritten in Wave 9, the governing invariants are already enforced by:
1. An AST identifier guard (names).
2. A no-allowlist lint (imports).
3. A perturbation regression test (behavior).
4. A widened No-Hardcoding lint (tests).
5. A signature inspection test (types).

The plan set shows high maturity in its treatment of the "Single-Owner" manifest and the "separate relocation vs. removal" audit reporting. It is technically sound and achieves the ergonomics goal without compromising the SDK's core value of whitepaper fidelity.

---

## Codex Review

## Summary

The plan set is unusually rigorous on sequencing, governance framing, and CI-backed invariants. The D-15A risk is taken seriously: `run_gates`, pin selection, view-bound operator construction, and external client boundaries all get explicit tests or lints. However, there are several serious plan-level inconsistencies that would either make later gates fail or push implementation into architectural trouble. The biggest issue is the surface-change machinery: the curated log is asked to contain many non-public-surface and behavior/artifact-format changes, but the phase-close completeness test requires every non-`behavior` entry to match the generated public API diff. That is not satisfiable as written.

## Strengths

- The plans correctly front-load the phase-start surface baseline in `15-01` before `ccf.deployment` exists. That closes the previously found concurrency/baseline defect.
- The D-15A guard in `15-02` is well scoped: perturbation test, AST guard, and no-allowlist import ban against `ccf.deployment -> ccf.products.gates`.
- The single-owner rule for `docs/surface/v0.2-surface.json` is strong and clearly repeated. It avoids the stale-manifest-after-parallel-merge failure mode.
- The manifest design in `15-10` preserves the important substrate and replay properties: no globs, no `resolve_latest`, caller-supplied registry, backend kind only, no hidden DSN.
- The operator builder plan `15-11` recognizes the real temporal-boundary issue around `SimilaritySelect` and rejects lazy binding.
- The example rewrite plans consistently protect known boundaries: external client legs stay untouched, live harness legs stay untouched, replay pins stay explicit, and HITL assertions relocate with audit coverage.

## Concerns

### HIGH — Surface-change completeness test is incompatible with the planned log

Concrete failure: `15-21` Task 2 says every curated log entry whose `Change type` is not `behavior` must correspond to a public-surface diff line from `diff_surfaces(baseline, live)`. But many required fragments are not public API changes captured by `dump_surface.py`, for example:

- `15-04` records lint scope reshaped.
- `15-13` through `15-20` record example artifact-format changes.
- `15-03` records `tools/measure_examples.py` and `make measure-examples`.
- `15-12` records committed schemas and HTTP/OpenAPI changes, only some of which may be in `/runtime` `__all__`.

These entries will not appear in the `/src` and `/runtime` `__all__`-based surface manifest. The final `log -> diff` assertion will fail unless the log is split into public API entries versus migration/process/artifact-format entries, or the completeness test only enforces diff agreement for entries marked as public API.

### HIGH — `15-05` has impossible acceptance criteria for a behavior-only change

`15-05` Task 2 says `tools/dump_surface.py --report` must list “this plan’s new public names under added,” but the plan explicitly adds no public name and records a `behavior` change to `load_artifact`. If signatures and `__all__` are unchanged, the report should be empty. The acceptance criterion and verification narrative contradict the intended design.

### HIGH — `EntityResolutionSpec` inheriting `_VersionedArtifact` likely creates a circular import

`15-07` Task 1 instructs `src/ccf/assembly/worker.py` to import `_VersionedArtifact` from `ccf.controlplane.artifacts`, while `artifacts.py` must import `EntityResolutionSpec` to define `RESOLUTION_SPEC`. That is a likely import cycle between L2 assembly and controlplane artifacts.

The plan says to stop if layering lints object, but this may not be caught by lints; it can fail at import time. A safer design is needed before execution, such as moving the versioned artifact base/semver validator to a lower shared module, or using a wrapper only if `boot()` can still resolve the inner `EntityResolutionSpec` without changing its public contract.

### HIGH — Operator-parameter artifact design conflicts with `PolicyFilterParameters`

`15-08` says each artifact subclass should be directly usable as the existing `*Parameters` model, but then notes `PolicyFilterParameters.permitted_policy_bundle_versions` is not authored and must come from the pin set later. The plan proposes either a default `frozenset()` or later `model_copy(update=...)`.

Failure scenario: if the artifact contract inherits `PolicyFilterParameters` unchanged and the field is required, parsing the artifact fails before `15-11` can supply pins. If it defaults to empty, then the parsed artifact is directly usable but semantically unsafe if someone bypasses the builder. The plan needs one explicit contract shape: probably a separate artifact contract that is not itself a complete `PolicyFilterParameters`, plus a builder conversion, or a required pin-injection step with tests proving raw policy artifacts cannot be used directly as operators.

### HIGH — `SignalBatch` tenant model appears internally inconsistent

`15-09` defines `SignalBatch` with batch-level `tenant_id` and `envelopes: tuple[SignalEnvelope, ...]`, then says not to silently stamp tenant onto envelopes, and to reject disagreement. But `SignalEnvelope` requires `tenant_id`, so every envelope still has to carry tenant_id. That means batch-level `tenant_id` does not remove duplication unless the envelope contract changes or the batch uses an intermediate envelope item contract.

Concrete failure: example `events.yaml` either repeats `tenant_id` per envelope, making batch-level tenant mostly redundant, or omits it and fails Pydantic validation before the after-validator can stamp or compare. The plan should define the exact parsed shape.

### MEDIUM — `ResolvedPins.version_for(key)` may be under-specified for duplicate keys and class constraints

`15-10` requires deterministic `ResolvedPins`, but does not clearly require manifest duplicate key refusal. If a manifest lists the same key twice with different class IDs or documents, `version_for(key)` becomes ambiguous unless it refuses duplicates or defines ordering. Since pins feed boot and replay, duplicate keys should be refused at manifest validation or pin construction.

### MEDIUM — `load_and_boot` registers every manifest artifact before boot, including artifacts not needed for boot

This is probably intended, but it raises a rollback/partial-registration risk. If artifact N registers successfully and artifact N+1 fails, the registry now has partial state. Content-addressed idempotence makes this less dangerous, but audit logs may show failed deployment attempts as registrations. The plan should specify whether that is acceptable and test failure behavior.

### MEDIUM — Direct-construction additivity test in `15-21` may be too heavy or brittle

Calling `boot()` directly in `tests/deployment/test_direct_construction.py` requires a valid registry, DB path, resolution spec, and policy bundle pins. That is fine if fixtures exist, but the test says “no `ccf.deployment` import anywhere,” so it cannot reuse the manifest fixtures. It needs its own minimal setup plan, otherwise this becomes a late-phase fragile test.

### MEDIUM — Example rewrite plans repeatedly touch shared docs despite dependency edges only covering some conflicts

Several plans edit `public/tutorial/adopters-guide.md` or related public docs. Some dependencies serialize obvious collisions, but the plan set still has broad `public/...` edits in parallel waves. The instructions say each plan touches only its own include lines, but that is not mechanically enforced until `docs-strict`, and concurrent merge conflicts remain likely. This is manageable but should be called out as operational risk.

### LOW — AST/string checks can be bypassed by aliases or dynamic access

The `15-02` AST identifier guard is useful, but a future helper could avoid the literal identifiers with aliases, factory functions, or dynamic imports. The no-import lint on `ccf.products.gates` is stronger for `run_gates`, but the `ProductLineage` / `engine_resolved` collapse guard is still heuristic. This is acceptable if documented as heuristic, which the plan mostly does.

## Suggestions

1. Split `docs/SURFACE-CHANGES.md` entries into at least two categories: `public_surface: true/false`, or separate `docs/SURFACE-CHANGES.md` and `docs/MIGRATION-CHANGES.md`. Make `tests/test_surface_completeness.py` enforce name/direction agreement only for public-surface entries.
2. Fix `15-05` acceptance criteria: behavior-only drift should not require `dump_surface.py --report` to show added names. The fragment should be validated by the assembler, not by the signature diff.
3. Resolve the `_VersionedArtifact` import-cycle risk before `15-07`. Prefer moving semver/versioned artifact base to a neutral lower-level module if in-place inheritance is required.
4. Redesign policy operator artifacts explicitly: decide whether `PolicyFilterParametersArtifact` is a partial artifact converted by the builder, or a full parameter object only after pin injection. Do not leave the parser depending on a later `model_copy`.
5. Define `SignalBatch`’s exact event item shape. If batch-level `tenant_id` is meant to avoid per-envelope duplication, use a batch-local item contract and convert to `SignalEnvelope` in a validator.
6. Add duplicate manifest key/path tests in `15-10`: duplicate keys should fail, and duplicate paths under different keys should either be allowed deliberately or refused deliberately.
7. Add a partial-registration failure test or explicitly document that registry writes before a later manifest failure are acceptable because registration is content-addressed and auditable.
8. Add a small “shared public docs edits” checklist to each example rewrite summary: which include markers changed, and confirmation no other plan’s include lines moved.

## Risk Assessment

Overall risk: **MEDIUM-HIGH**.

The governance intent is strong and much better protected than a typical ergonomics phase. The main risk is not lack of rigor; it is that some of the rigor is aimed at incompatible artifacts. The public-surface completeness design will likely fail against the migration log as written, and the `EntityResolutionSpec`, policy-parameters, and signal-batch shapes have implementation-level contradictions that could block execution or force redesign mid-phase. Once those are corrected, the plan set drops closer to medium risk: broad file churn remains, but the sequencing and invariant tests are generally sound.

---

## Cursor Review

# Phase 15 Plan Review — Cursor

## 1. Summary

The plan set is unusually strong on governance risk: Wave 1 baseline ownership, D-15A guards before helpers, D-IMPL-76/77 regeneration isolation, single-owner surface regeneration, and a paired drift/completeness design that learned from three prior review failures. It will achieve the phase goal if a few **false or underspecified seams** are fixed before execution — most importantly a factual error about `SimilaritySelectParameters`, an undifferentiated “register everything in the manifest” path that can put L1 signal batches into Control Plane dimension 2, and an underspecified day-1 path from `load_and_boot` to ingest / `register_product_class`. Without those fixes, executors will either invent governance-adjacent behavior mid-wave or leave more mechanical code in examples than Success Criteria 2–3 claim.

## 2. Strengths

- **D-15A is treated as a standing constraint, not a docstring.** `15-02` lands perturbation + AST-identifier (not text) guards + a no-allowlist import ban before any helper exists. Correct ordering.
- **Surface-record design is sound as a pair.** `15-01`’s module-granular documented-drift tripwire + `15-21`’s name-level bidirectional completeness test with change-type agreement addresses the prior “prose completeness” failure. Qualifying the *frozen* baseline (`v0.2-surface-baseline.json`) so the live path never moves is the right naming.
- **Blast radius is sequenced.** `EntityResolutionSpec` semver churn is isolated in autonomous-false `15-07` with a human regeneration checkpoint; example `04` re-domain vs rewrite are separate commits (`15-18`); demo narration has its own checkpoint (`15-16`).
- **External / live-leg boundaries are explicit.** `15-15` / `15-20` protect zero-CCF client legs and opt-in live legs with `git diff` empty assertions.
- **D-09 + D-IMPL-78 ordering is correct.** Lint scope widens in `15-04` before assertion relocation; A6 falsification gates that change (`15-03` Task 4).
- **Requirements coverage maps cleanly** to the six ROADMAP success criteria; resolved D-IMPL-76..79 are wired into the right plans.

## 3. Concerns

### HIGH — `15-08` Task 1 states a false fact that breaks D-03 / `15-11`

> “`classification_attribute_by_class` and `similarity_corpus_attribute_by_class` are already fields of `PolicyFilterParameters` and `SimilaritySelectParameters` respectively”

Verified against `src/ccf/operators/params.py`: only `PolicyFilterParameters` has `classification_attribute_by_class`. `SimilaritySelectParameters` has `query`, `minimum_score_percent`, `ranked_entity_classes` only. The corpus map lives in `ontology.yaml` and is used solely to build `TokenOverlapIndex` (`run.py:248-256`), not as an operator invoke-time parameter.

**Failure scenario:** `15-08` inherits fields “verbatim” and forbids editing `params.py`. `15-11` then tries to read the corpus map from the similarity parameters artifact — attribute missing → executor either (a) edits `params.py` against acceptance criteria, (b) hardcodes corpus extraction in the builder from a side channel, or (c) leaves corpus wiring in every example. D-03’s split fails silently until `15-13`.

**Fix:** In `15-08`, add `similarity_corpus_attribute_by_class: Mapping[str, str]` on `SimilaritySelectParametersArtifact` only (extra artifact field, not on the L4 invoke contract), document that it exists for index construction, and have `15-11` read it from the artifact instance before constructing `SimilaritySelect`. Alternatively amend `SimilaritySelectParameters` itself under an explicit acceptance-criteria change — but do not claim the field already exists.

### HIGH — `15-10` registers every manifest entry into the Control Plane, including signal batches

Today’s quickstart registers resolution spec, policy bundle, half-life, debt profile — then **ingests** envelopes via L1. Operator params, perspective, MaxTTL/product class, and events are not Control Plane registrations in the same sense.

`15-10` Task 2 step 3: for **each** manifest entry, `register_typed`. Task 3 fixture includes a signal batch in that set. D-06’s rationale is that the artifact set in force is replay dimension 2.

**Failure scenario:** Day-1 manifest lists `events.yaml` as `ccf.signal-batch`. `load_and_boot` content-hashes the full event batch into the registry. `build_replay_record(policy_bindings=…)` now has a pin for raw signals, or adopters must carefully *exclude* those pins — either silent dimension-2 expansion or a footgun. Re-authoring events changes “what was in force” the same way a policy bump does.

**Fix:** Manifest entries need a role: `register` (Control Plane) vs `load` (return to caller, do not register). `BootedFabric` should carry loaded-but-not-registered artifacts (at least the signal batch). Surfacing this as a short Dave ruling is appropriate under C-10 — it touches replay dimension 2.

### HIGH — Day-1 path after `load_and_boot` underspecified (`15-10` / `15-13`)

`BootedFabric` returns `handle`, `pins`, `tenant_id` only. No envelopes, no parsed operator-parameter objects, no `RegisteredProductClass`.

**Failure scenarios:**
1. **Ingest:** Adopter must re-`load_artifact` the signal batch or resolve it from the registry (see above). Mechanical code remains; Criterion 3 is only half-met.
2. **Product class / MaxTTL:** `15-09` correctly refuses to put `max_ttl_version` in the artifact and forbids a `register_product_class` helper there. `15-10` never calls `register_product_class`. `15-13` deletes the registration prologue but never says how MaxTTL seconds are obtained or that the `MaxTTL` + `register_product_class` cluster (~90 lines suite-wide per research) stays explicit. Executors will either invent a helper that collapses Gate 3’s pin minting or leave a large unexplained residue in “streamlined” `run.py`.
3. **`build_operator_registry(parameters=…)`:** How the adopter builds the `Mapping` from pins/registry is unspecified. Risk of `isinstance` soup or class-id string filtering copied eight times — a new duplication class.

**Fix:** Specify in `15-10`/`15-13`: (a) what `BootedFabric` returns for non-CP loads; (b) the exact remaining adopter lines for MaxTTL + `register_product_class` (and that this residue is intentional for Gate 3); (c) a recommended pattern for assembling the `parameters` mapping from pins without new copy-paste.

### HIGH — `15-20` must_haves contradict Task 1

`must_haves`: “`run.py`, `replay_server.py`, and the fixture machinery are untouched except where the parent's rewrite forces it.”

Task 1: “`run.py` has 36 mechanical lines… Rewrite those to the streamlined surface as well.”

**Failure scenario:** Executor follows must_haves → external tree still has mechanical wiring (Criterion 5 incomplete). Or follows Task 1 → must_have lies and review/acceptance become ambiguous; also `files_modified` omits `run.py`.

**Fix:** Pick one. Prefer rewriting `run.py` fabric wiring (research counts it) and updating must_haves / `files_modified`, while keeping client legs / replay_server / fixtures untouched.

### MEDIUM — Documented-drift gate still allows mid-phase silent adds on an already-claimed module

By design (`15-01` Task 2): once any fragment names `ccf.controlplane.artifacts`, later plans can add exports there without a new fragment and still pass the standing gate until `15-21`.

**Failure scenario:** `15-08` forgets a fragment entry for one of four operator-parameter constants; standing CI stays green; only `15-21` completeness fails — at the most expensive point in the phase.

**Mitigation already planned** is good; strengthen by requiring each plan’s verify to assert `--report`’s `added` list is a **subset** of that plan’s fragment `Surface` fields (not merely “appears under added”). Several plans already say “confirm names appear”; make subset-equality an acceptance criterion.

### MEDIUM — `15-08` multiple inheritance + `permitted_policy_bundle_versions`

`PolicyFilterParameters.permitted_policy_bundle_versions` is required with no default (`params.py:59`). Artifact subclassing `_VersionedArtifact, PolicyFilterParameters` cannot omit it without a default/`model_copy` story. Plan says “choose one” but does not pin the choice or a round-trip document shape.

**Failure scenario:** Sample YAML in round-trip tests invents a fake version set, teaching the wrong authoring pattern; or Pydantic MRO/`model_fields` surprises break `isinstance(parsed, PolicyFilterParameters)`.

**Fix:** Pin D-IMPL-76 implementation: artifact field default `frozenset()` **or** exclude the field via a dedicated artifact model that is not a full subclass, then `model_copy` in `15-11`. Add an explicit round-trip document that omits the version set.

### MEDIUM — Private `_VersionedArtifact` cross-package inheritance (`15-07`)

D-IMPL-77 requires in-place inheritance. `_VersionedArtifact` is module-private; `assembly/worker.py` would import a private Control Plane type. `agents/definitions.py` already documents why definitions use a different versioning base.

**Failure scenario:** Later refactor makes `_VersionedArtifact` package-private / relocated; L2 breaks. Or layering review treats it as a smell and blocks mid-plan (plan says stop — good — but then the wave stalls).

**Fix:** Export a public `VersionedArtifact` (or alias) as part of `15-07`, or define semver on `EntityResolutionSpec` via the same `validate_semver` without inheriting the private base — still satisfying “semver in place” for `boot()`.

### MEDIUM — Shared `public/` / Makefile collision residual

`15-19` correctly serializes behind `15-17` for `adopters-guide.md`. Wave 10 (`15-14`/`15-15`/`15-16`) looks clean. `15-12` edits `Makefile` + `openapi.json` in parallel with `15-11` (no Makefile touch) — OK.

Residual: `15-14` lists many `public/reference/artifacts/*` pages; if marker re-points land in the same files `15-13` already touched, merge conflicts are likely. Acceptable if worktrees are sequential on docs; call it out in wave guidance.

### MEDIUM — `required_operators` from artifact (`15-13`) without artifact field

Plan requires `QuickstartPlan.required_operators()` to read from “the artifact,” not `operators.keys()`. No plan adds a typed field for required operator keys on product-class or a projection artifact.

**Failure scenario:** Executor invents a key in `controlplane.yaml` / product-class YAML without a schema, or leaves a hardcoded frozenset in `run.py` (No-Hardcoding / CINV-01 risk once patterns spread).

**Fix:** Name the artifact field and which class owns it in `15-09` or `15-13` Task 1.

### LOW — Behavior-class completeness still soft for D-02

`behavior` entries are exempt from log↔diff matching. Missing D-02 entry fails only human read / Task 1 acceptance prose.

**Fix:** `15-21` completeness test: require at least one `behavior` entry whose `Surface` is `ccf.controlplane.artifacts.load_artifact` (hardcoded allowlist of required behavior surfaces), not a free-form exempt class.

### LOW — Perf / fixture trees still carry `_instant` / ontology corpus maps

Research noted helpers outside `examples/`. Phase scope is examples + `/src`; acceptable. Note for Phase 16 / follow-up so D-02’s “13 helpers delete” claim is not over-claimed in the audit.

### LOW — Traceability table in the review brief still shows HARD/EXAM/DOCS as Pending

Process hygiene only; not a plan defect. `15-21` updates ERGO rows; older rows look stale in PROJECT.md.

## 4. Suggestions

1. **Patch `15-08` before any Wave 5 execution** — correct the similarity corpus field claim; specify artifact-only extra field; update `15-11` to match.
2. **Add a manifest entry role / `BootedFabric.loaded` (or similar) in `15-10`** — register Control Plane classes only; return signal batch (and any other data-plane docs) without `register_typed`. If Dave wants signal batches pinned, make that an explicit D-IMPL, not an accident.
3. **Write the post-`load_and_boot` quickstart skeleton in `15-13` Task 2** (10–20 lines of intended spine): load pins → ingest from returned batch → build view → `build_operator_registry` → project → explicit MaxTTL/`register_product_class` → lineage/`run_gates`/`build_replay_record`. Remove ambiguity.
4. **Reconcile `15-20` must_haves vs Task 1**; add `run.py` to `files_modified` if rewriting.
5. **Tighten per-plan surface verify:** `set(report.added) ⊆ set(fragment Surfaces)` (and optionally `⊇` for that plan’s claimed adds).
6. **Do not weaken** the `15-02` gates or the `ResolvedPins` no-bindings-helper rule — those are the right answers to the phase’s defining risk.
7. **Pin set / `build_replay_record`:** Keep requiring explicit `PolicyBinding(...)` construction in `15-17`; add a negative test that `ResolvedPins` has no `policy_bindings` / `bindings` attribute (partially in `15-10` Test 7 — good; keep it).

## 5. Risk Assessment

**Overall: MEDIUM** (would be LOW after the HIGH fixes; HIGH if `15-08`/`15-10` ship as written).

| Dimension | Rating | Why |
|-----------|--------|-----|
| D-15A / governance collapse | **LOW–MEDIUM** | Guards are excellent; residual risk is product-class/MaxTTL and pin-set convenience creeping in during example rewrites, not the core helpers as specified |
| Criterion 6 surface record | **LOW** | Pair is sound; mid-phase module-blind spot mitigated at close if `15-21` is non-skippable |
| Criterion 2–3 (loaders + wiring) | **HIGH until patched** | False similarity field; register-all; missing return path for envelopes / product-class residue |
| Example suite / EXAM boundaries | **LOW** | Sequencing and client/live-leg fences are clear; `15-20` internal contradiction is the main blot |
| Dependency / wave graph | **LOW** | Baseline-first and shared-doc serialization look correct after prior review rounds |
| Over-engineering | **LOW–MEDIUM** | 21 plans is heavy but mostly justified by blast-radius isolation; measurement tooling (`15-01`/`15-03`) is proportionate to D-11/D-12 |

**Bottom line:** Do not treat this as ready to execute Wave 5+ unchanged. Fix the `SimilaritySelectParameters` false claim, the manifest register-vs-load split (and `BootedFabric` return shape), and the `15-20` contradiction first. With those addressed, the set is one of the stronger phase plans in this repo for a fidelity-sensitive ergonomics change — and it does target the real problem (interpreters stranded in `/examples`) without inviting a tautological `run_gates`.

---

## Ollama Review

_(condensed context — frontmatter, objectives, and must_haves only)_

# Cross-AI Plan Review: Phase 15 SDK Ergonomics

## 1. Summary
The plan set for Phase 15 is exceptionally rigorous, characterized by a "defensive-first" engineering posture. It does not merely implement ergonomic helpers; it builds a high-fidelity instrumentation framework (surface manifests, drift gates, and AST-based line counters) to prove that the ergonomics do not degrade the governance invariants of the CCF whitepaper. The sequencing is logical, establishing the "standing guards" (D-15A) and the "baseline" (Success Criterion 6) before a single line of public API is modified.

## 2. Strengths
- **Governance Fidelity (D-15A):** The decision to land the `ccf.deployment` shell and the `test_gate_independence.py` guard in **15-02** *before* any helpers are written is a masterclass in preventing "convenience creep." By making the independence of the `run_gates` arguments an executable test early, the plan ensures no helper can accidentally collapse the two sources into a tautology.
- **Surface Management:** The two-file naming strategy (`v0.2-surface.json` vs `v0.2-surface-baseline.json`) elegantly solves the "stale manifest" problem encountered in previous review rounds. The use of fragment-based logging (`docs/surface-changes/`) ensures that changes are documented atomically with the plans that cause them.
- **Audit Integrity:** The use of an AST-based tool (`measure_examples.py` in **15-03**) to count "mechanical" lines prevents the "honesty gap" common in ergonomics reports, where authors manually exclude lines to inflate a win.
- **Dependency Chain:** The wave structure is sound. The baseline (Wave 1) $\rightarrow$ Guards (Wave 2) $\rightarrow$ Core Artifacts (Wave 3-6) $\rightarrow$ Wiring (Wave 7-8) $\rightarrow$ Example Rewrites (Wave 9-13) $\rightarrow$ Closure (Wave 14) sequence ensures that every rewrite in the later waves is targeting a stable, tested surface.

## 3. Concerns

### HIGH: The "Implicit Pin" Risk in Replay (15-17)
While **15-17** explicitly mentions the hazard of the `ResolvedPins` object being passed directly to the replay builder, the "must-have" truth states that pins are "read by the adopter... and passed explicitly." 
**Failure Scenario:** If the `ResolvedPins` object is a Pydantic model or a dataclass, and the `build_replay_record` function is updated to accept a `ResolvedPins` object as a type, the adopter might simply pass the object: `build_replay_record(pins=my_pins)`. While this looks "explicit," the *selection* of which specific pin values are used for the replay record is now hidden inside the `ResolvedPins` object. To satisfy the "two independent sources" spirit of D-15A, the replay builder should ideally require the specific pin values (e.g., `resolution_spec_version=pins.resolution_spec_version`) rather than the container.
**Verdict:** The plan recognizes the risk, but the "must-have" is slightly too permissive.

### MEDIUM: Schema-Header Drift (15-12 $\rightarrow$ 15-21)
Plan **15-12** generates the schemas and the CLI noun, but the tree-wide enforcement of `$schema` headers on all YAML artifacts in the `examples/` directory is deferred to **15-21**.
**Failure Scenario:** Between Wave 8 and Wave 13, a developer might rewrite an artifact in Example 00 or 08 but omit the `$schema` header or use a typoed one. Because the gate isn't live until the very end of the phase, these errors will accumulate, leading to a "cleanup storm" in the final plan.
**Verdict:** The gate is necessary in 15-21 for closure, but a "soft-warning" or per-example check should be moved earlier into the rewrite plans (15-13..20).

### LOW: The "Banking" Commit Split (15-18)
Plan **15-18** requires two separate commits: one for the surface rewrite and one for the re-domaining to banking. 
**Failure Scenario:** In a high-velocity environment, these may be squashed during a PR merge or combined by a developer. While this is a process risk rather than a technical one, it violates the "auditability" goal of the phase.
**Verdict:** Low risk, but requires explicit PR labels or a "no-squash" policy for this specific plan.

## 4. Suggestions
- **Refine 15-17 Must-Haves:** Explicitly forbid `build_replay_record` from accepting the `ResolvedPins` container object as a single argument. Require the explicit extraction of individual pin values in the example code to demonstrate the "selection" process.
- **Shift-Left Schema Validation:** In plans **15-13 through 15-20**, add a "must-have" that the specific artifacts modified in that plan are verified against the schemas generated in **15-12** using a local script, rather than waiting for the tree-wide gate in **15-21**.
- **D-14 Validation:** In **15-21**, ensure the `test_direct_construction.py` doesn't just check that constructors *exist*, but that they are *not deprecated* and maintain the same signature as the pre-ergonomic version.

## 5. Risk Assessment
**Overall Risk: LOW**

**Justification:** This is one of the most disciplined plan sets reviewed. The "adversarial" nature of the plan—where the author has already anticipated and mitigated the three most common failure modes of SDK ergonomics (silent invariant deletion, stale manifests, and inflated audit numbers)—reduces the residual risk significantly. The high-risk items are primarily related to the *interpretation* of "explicit" in the replay record, which is a governance nuance rather than a structural flaw.

---

## Consensus Summary

Risk ratings diverged sharply: **Gemini LOW · Ollama (implicit) LOW · Cursor MEDIUM (HIGH if
15-08/15-10 ship as written) · Codex MEDIUM-HIGH**. The divergence is explained by context depth,
not disagreement about facts — Gemini and Ollama assessed the *governance architecture* (which is
strong, and all four agree on that), while Codex and Cursor read the task bodies closely enough to
find implementation-level contradictions inside individual plans. The pessimistic reviewers are
right, and their findings were independently verified before this section was written.

### Agreed Strengths (2+ reviewers)

- **D-15A treated as a standing constraint, not a docstring.** All four cite 15-02 landing the
  perturbation test, AST-identifier guard, and no-allowlist import ban *before* any helper exists.
  Gemini calls it "a high-signal commitment to whitepaper fidelity"; Cursor calls the ordering
  "correct"; Codex calls the guard "well scoped."
- **The single-owner surface-manifest rule.** Gemini singles it out as "a standout piece of
  engineering management that should be adopted as a project standard." Codex: "strong and clearly
  repeated — avoids the stale-manifest-after-parallel-merge failure mode."
- **Blast-radius sequencing.** The `EntityResolutionSpec` semver churn isolated in 15-07 with its
  own checkpoint (Gemini: "excellent risk management"; Cursor: correct isolation), and example 04's
  re-domaining kept as separate commits.
- **Boundary discipline.** `examples/external/` client legs and `examples/03` live legs protected
  with `git diff`-empty assertions (Codex, Cursor).
- **D-09 / D-IMPL-78 ordering.** Lint scope widens before assertion relocation, with the A6
  falsification gating it (Cursor, Gemini).

### Agreed Concerns — VERIFIED (highest priority)

Each of the following was checked against source or plan text before being recorded here.

**C-1 [HIGH — Codex] The completeness test is unsatisfiable against the log as planned.**
`15-21:195` requires every log entry whose `Change type` is not `behavior` to match a line in the
`__all__`-derived public-API diff. `15-01:310` defines exactly four change types — `added`,
`reshaped`, `removed`, `behavior` — with `behavior` scoped narrowly to D-02's `load_artifact`.
But several plans are required to write fragments for changes that are *not* public API and will
never appear in the diff: 15-04 (lint scope), 15-03 (`tools/measure_examples.py`,
`make measure-examples`), 15-13..15-20 (example artifact-format changes), and parts of 15-12
(committed schemas). **VERIFIED.** As written, the reverse assertion fails at wave 14 — the most
expensive point in the phase. Fix: split the log into public-API vs migration/process entries (a
`public_surface: true|false` field, or two files), and scope the diff-agreement assertion to
public-API entries only.

**C-2 [HIGH — Cursor] 15-08 asserts a fact that is false.**
`15-08:100-101` states `classification_attribute_by_class` and
`similarity_corpus_attribute_by_class` "are already fields of `PolicyFilterParameters` and
`SimilaritySelectParameters` respectively." **VERIFIED FALSE for the second.**
`src/ccf/operators/params.py:64-79` gives `SimilaritySelectParameters` exactly three fields —
`query`, `minimum_score_percent`, `ranked_entity_classes`. The corpus map lives in `ontology.yaml`
and feeds `TokenOverlapIndex` construction, not operator invocation. Combined with 15-08's
"inherit fields verbatim" instruction and its prohibition on editing `params.py`, an executor hits
a missing attribute and improvises — editing `params.py` against acceptance criteria, hardcoding
corpus extraction in the 15-11 builder, or leaving corpus wiring in all nine examples (silently
defeating D-03).

**C-3 [HIGH — Codex + Cursor, independently] The policy operator-parameters artifact has no
workable shape.** `params.py:59` declares `permitted_policy_bundle_versions: frozenset[str]` —
**required, no default. VERIFIED.** Under D-IMPL-76 the adopter supplies it via the pin set at
build time, so an artifact subclassing `PolicyFilterParameters` cannot parse without it. 15-08
offers "a default `frozenset()` or a later `model_copy(update=…)`" without pinning either. Codex:
if required, parsing fails before 15-11 can inject; if defaulted, a raw artifact is directly
usable as an operator parameter set and is *semantically unsafe* when the builder is bypassed.
Both reviewers ask for one pinned contract shape plus a test proving raw policy artifacts cannot
be used directly as operators.

**C-4 [HIGH — Codex] `EntityResolutionSpec` inheriting `_VersionedArtifact` risks an import
cycle.** D-IMPL-77 requires in-place inheritance, so `src/ccf/assembly/worker.py` must import from
`ccf.controlplane.artifacts`, while `artifacts.py` must import `EntityResolutionSpec` to define
the `RESOLUTION_SPEC` constant. **VERIFIED the cycle closes:** `worker.py:51` already imports
`ccf.controlplane.registry`, and `registry.py:54` imports `ArtifactClass` from
`ccf.controlplane.artifacts`. Adding the reverse edge yields
`artifacts → worker → registry → artifacts`. This fails at import time, not at lint time, so
15-07's "stop if layering lints object" instruction will not catch it. Cursor raises the same
seam from a different angle (MEDIUM): `_VersionedArtifact` is module-private, so L2 would import
a private Control Plane type. Both fixes converge — move the versioned-artifact base / semver
validator to a neutral lower module, or export a public `VersionedArtifact`.

**C-5 [HIGH — Cursor] `load_and_boot` registers signal batches into the Control Plane.**
15-10 Task 2 step 3 calls `register_typed` for *every* manifest entry, and Task 3's fixture
includes a signal batch. Today's quickstart registers the resolution spec, policy bundle,
half-life table, and debt profile — then *ingests* envelopes through L1. Registering raw signals
content-hashes an event batch into replay dimension 2, so re-authoring events changes "what was in
force" the same way a policy bump does. Cursor's fix: manifest entries carry a role (`register`
vs `load`), with `BootedFabric` returning loaded-but-unregistered artifacts. **This touches replay
dimension 2 and is a decision for Dave, not a plan-level pick.**

**C-6 [HIGH — Cursor] 15-20 contradicts itself three ways.** must_haves (`:23`) says `run.py` is
"untouched except where the parent's rewrite forces it"; Task 1 (`:86`) says `run.py` has 36
mechanical lines and instructs "rewrite those"; and `files_modified` **omits `run.py` entirely**.
**VERIFIED.** Either the external tree keeps mechanical wiring (Criterion 5 incomplete) or the
executor edits a file the plan never declared.

**C-7 [HIGH — Codex] 15-05's acceptance criteria contradict its own design.** `15-05:151` states
"This plan adds no public name," while `:169` requires "`--report` lists this plan's new public
names under added" and `:200` requires it to "show this plan's additions." **VERIFIED.** D-02 is a
behavior change with no signature delta; the criterion is unsatisfiable.

**C-8 [MEDIUM — Cursor + Codex] The day-1 path after `load_and_boot` is underspecified.**
`BootedFabric` returns `handle`, `pins`, `tenant_id` only. Neither 15-10 nor 15-13 specifies how
the adopter obtains envelopes for ingest, how the `MaxTTL` + `register_product_class` cluster
(~90 lines suite-wide) is handled, or how the `parameters` mapping for `build_operator_registry`
is assembled. Cursor's warning is the sharp one: executors will either invent a helper that
collapses Gate 3's pin minting, or leave a large unexplained residue in a nominally streamlined
`run.py` — and a repeated `isinstance`-filtering idiom would be a *new* duplication class, the
exact thing the phase exists to remove.

**C-9 [MEDIUM — Cursor + Codex] Duplicate-key and partial-registration behavior unspecified in
15-10.** Duplicate manifest keys make `version_for(key)` ambiguous; a mid-sequence registration
failure leaves partial Control Plane state. Both feed replay, so both want explicit refusal or
explicit documented acceptance, with tests.

**C-10 [MEDIUM — Cursor] Tighten the per-plan surface verify to subset-equality.** Several plans
assert their new names "appear under added"; Cursor wants
`set(report.added) ⊆ set(fragment Surfaces)` so a *forgotten* fragment entry fails at its own
wave rather than at 15-21.

### Divergent Views

- **Overall risk.** Gemini rates LOW on the strength of the five front-loaded standing guards;
  Codex rates MEDIUM-HIGH because "some of the rigor is aimed at incompatible artifacts." Both are
  accurate about what they examined. The architecture is sound; several plan bodies are not yet
  executable as written.
- **`required_operators()` (G-B).** Gemini wants a *structural* AST guard flagging
  `operators.keys()` inside any `required_operators()` implementation, arguing 15-13's per-example
  fix leaves a pattern-level hole for future contributors. Cursor approaches the same shortcut from
  the opposite end: no plan defines *which artifact field* supplies the required-operator keys, so
  an executor may invent an unschema'd YAML key or hardcode a frozenset. Both are worth taking —
  they are complementary, not competing.
- **Snippet markers.** Gemini flags the 92 snippet markers invalidated by the rewrites as a MEDIUM
  verification burden landing on 15-21's manual check; no other reviewer raises it.
- **`ccf schema export` reachability.** Gemini notes adopters may expect a "dump all to local
  files" command, which D-IMPL-79's route-backed design does not provide. This is a consequence of
  a ruling already made, not a defect.

### Disposition

**Blocking for execution (must be fixed before the affected wave):** C-1, C-2, C-3, C-4, C-6, C-7.
All six are localized plan-text defects with clear fixes and none require revisiting a ruling.

**Requires a decision from Dave:** C-5 — the register-vs-load split touches Decision Replay
dimension 2 and is a governance boundary, which CLAUDE.md §15 and ruling D-15A both route to a
`D-IMPL-NN` rather than a plan-level pick.

**Fix in the same pass (advisory):** C-8, C-9, C-10, plus Gemini's G-B AST guard and Cursor's
requirement that the artifact field supplying `required_operators` be named.

**Do not weaken:** every reviewer that examined them endorsed the 15-02 gate guards and the
`ResolvedPins` no-bindings-helper rule. Cursor states it explicitly: "Do not weaken the 15-02
gates or the `ResolvedPins` no-bindings-helper rule — those are the right answers to the phase's
defining risk."
