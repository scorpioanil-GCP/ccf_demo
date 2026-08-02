---
phase: 11
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-08-02T03:55:00Z
plans_reviewed: [11-01-PLAN.md, 11-02-PLAN.md, 11-03-PLAN.md, 11-04-PLAN.md, 11-05-PLAN.md]
---

# Cross-AI Plan Review — Phase 11

## Gemini Review

# Phase 11: Performance Battery - Plan Review

This review covers the implementation plans (11-01 through 11-05) for the CCF SDK Performance Battery, assessing their alignment with project invariants, technical rigor, and risk profile.

## 1. Summary
The Phase 11 plans establish a robust, whitepaper-faithful performance engineering foundation. By decoupling timing capture (`pytest-benchmark`) from gating logic (`perf/gate.py`), the architecture adheres strictly to the **D-IMPL-70** governance model (Dave-gated re-baselines, repo-owned thresholds). The use of a deterministic synthetic generator ensures that performance curves are attributable to system changes rather than data variance. The strategy for proving the "year-scale replay" claim via log-log curve fitting is particularly sophisticated, providing empirical evidence without the prohibitive cost of literal long-duration runs.

## 2. Strengths
*   **Gating Integrity:** The "single pipeline" rule (report and gate read the same numbers) prevents discrepancies between what is reported to the user and what causes a CI failure.
*   **Empirical Replay Proof:** Using the power-law fit ($t = an^b$) and asserting $b \le 1.0$ is a mathematically sound way to validate the scalability of the replay engine across decades of history.
*   **Whitepaper Fidelity:** The synthetic generator constructs data exclusively through L2/Factory paths, ensuring that benchmarks measure the "real" system paths adopters will use, rather than idealized internal shortcuts.
*   **CI Efficiency:** The bitrot smoke test (`--benchmark-disable`) provides a cheap, always-on guard against code rot in the `perf/` tree without introducing the noise and cost of timing-dependent tests into the main CI loop.
*   **Pragmatic Scaling:** The decision to flex the scale ladder (reducing the top rung from 100k to 1k for ingestion) based on early measurements (5ms/envelope) shows healthy engineering reactivity to observed system limits.

## 3. Concerns
*   **GitHub Runner Noise (Medium):** Even with a 10% threshold and median gating, GitHub-hosted `ubuntu-24.04` runners exhibit significant variance. 
    *   *Risk:* A 10% threshold may lead to "false regression" noise that exhausts the "re-baseline ritual" frequency, leading to threshold fatigue.
*   **Ingestion Bottleneck (Medium):** The discovery that 1k entities take ~42s to ingest (limiting the scale curves) identifies a potential L2 throughput bottleneck.
    *   *Risk:* While not a defect of the *plan*, it suggests that the "Performance Battery" has already surfaced a performance issue that may require architectural attention in Phase 14.
*   **Baseline Schema Rigidity (Low):** The median-only baseline schema (`D-12`) is excellent for stability but masks tail-latency regressions (p99).
    *   *Risk:* A code change could significantly degrade p99 (causing real-world "stutter") while leaving the median untouched, passing the gate.
*   **O(n²) Population Fix (Low):** The `_bulk_write` bypass in Plan 11-04 (writing directly to disk to avoid index rewrites) is necessary but creates a slight drift between "benchmark population" and "production population."

## 4. Suggestions
*   **p95/p99 Reporting in Gate:** While gating is correctly pinned to the median (per D-03), ensure `gate.py` explicitly highlights delta percentages for p95/p99 in the terminal table to provide "early warning" of tail-latency drift even if the gate passes.
*   **cProfile Integration:** Consider adding a `--profile` flag to `make perf` targets that invokes `pytest --benchmark-histogram` or triggers a `cProfile` dump for the slowest round, facilitating immediate root-cause analysis when a regression is found.
*   **Rung Size Calibration:** As the SDK matures and ingestion is optimized, the `perf/README.md` should include a specific "Ladder Calibration" section to help adopters move the 1k limit back toward the 100k whitepaper target.

## 5. Risk Assessment
**Overall Risk: LOW**

The phase is exceptionally well-mitigated. The "opt-in" CI posture (`workflow_dispatch`) and the manual re-baseline ritual prevent the "flaky CI" syndrome that often kills performance automation projects. The technical strategy for determinism (fixed seeds, checksummed rungs) is rigorous. The primary remaining risk is environmental (shared runner noise), which the plans address via "looser-only" overrides and specific runner-class keying. The discovery of the ingestion bottleneck is a success of the battery, not a failure of the phase.

---

## Codex Review

## Overall Summary

The Phase 11 plan set is strong: it is decomposed cleanly by dependency wave, maps well to PERF-01..04, respects D-IMPL-70’s governance constraints, and repeatedly protects the important invariants: report-only missing baselines, no perf in always-on CI except deterministic smoke, L2/factory-only synthetic fixture construction, and a single report/gate number pipeline. The main risks are not conceptual but execution-hardening risks: benchmark ID stability, pytest-benchmark JSON assumptions, path safety around runner-class keys, smoke-test runtime, replay exponent mechanics, and the possibility that some suites measure fixture/setup cost or cached paths rather than the intended SDK behavior.

## 11-01 Foundation: Gate, Thresholds, Make Targets

**Strengths**

- Good first wave boundary: establishes dependency, Makefile surface, thresholds, and gate before benchmarks depend on them.
- Strong governance alignment with D-IMPL-70: manual baselines, report-only missing baselines, explicit runner class, reviewed thresholds.
- Unit-testing the gate on deterministic fixture JSON is the right always-on CI posture.
- Loosen-only override validation is a useful guard against quiet threshold churn.
- Threat model correctly identifies runner-class path traversal and silent baseline mutation.

**Concerns**

- **HIGH:** The plan says unknown runner key is report-only, but also says baselines live at `perf/baselines/<runner-class>.json`. If runner-class validation is not strict enough, this is a path traversal risk. The threat model mentions mitigation, but the task acceptance criteria do not explicitly require tests for invalid keys like `../foo`.
- **MEDIUM:** Pytest-benchmark raw JSON schema is treated as stable, especially `benchmarks[].stats.data`. If the package changes schema or omits raw timings under some options, `gate.py` may fail late.
- **MEDIUM:** Benchmark IDs from pytest are often verbose and include parametrization. Without a normalization policy, baseline keys may drift easily.
- **LOW:** `make -n ci` containing no `perf` token could false-positive if comments or unrelated strings include “perf”; useful check, but not sufficient as an invariant.

**Suggestions**

- Add explicit tests for invalid runner classes: `../x`, absolute paths, spaces, slashes, shell metacharacters.
- Freeze and document the benchmark ID format that `gate.py` reads from pytest-benchmark.
- Add a schema validation error path for malformed raw JSON, missing `stats.data`, empty timing lists, missing benchmark names, and non-numeric values.
- Make the Makefile checks assert target dependency structure, not just grep output.

**Risk Assessment: MEDIUM**

The design is sound, but `gate.py` becomes a phase-critical control point. Most risk is in schema assumptions and runner-class/path handling.

## 11-02 Synthetic Generator

**Strengths**

- Strong fidelity to PERF-02: deterministic seed, rung shapes, checksums, neutral ontology, graph construction through L2/factory paths.
- Good separation: generator in `perf/`, no `/src` fixture machinery.
- Pinned shape/checksum tests are exactly the right drift detector.
- The plan recognizes No-Hardcoding by placing synthetic vocabulary in YAML artifacts.
- Topology requirements are meaningful: skewed hubs, constant average degree, temporal histories.

**Concerns**

- **HIGH:** The acceptance criteria require no ontology strings in generator source, but example entity names are suggested in the task. This is easy to violate accidentally through tests, defaults, or fallback code.
- **HIGH:** The boot-and-ingest test for 1k in always-on CI may become expensive if L2 ingestion is nontrivial, especially once smoke tests are added in 11-05.
- **MEDIUM:** “SignalEnvelope-shaped emission data” is vague. If not actual `SignalEnvelope` objects, later suites may silently benchmark conversion/adaptation rather than real ingestion.
- **MEDIUM:** Checksums over sorted entity URIs and edge pairs may miss drift in observations, timestamps, or decision records unless those are explicitly included.
- **LOW:** The 100k rung is introduced before budget calibration. That is acceptable, but it creates pressure on later plans to flex rung sizes after IDs may already be pinned.

**Suggestions**

- Define the checksum payload precisely: entities, edges, observations, timestamps, and decision stream references.
- Keep always-on determinism tests cheap: checksum generation is fine; full fabric boot/ingest should be guarded carefully or limited to the smallest viable fixture.
- Use concrete return types in the generator API: actual `SignalEnvelope` objects or a named dataclass with a single conversion function.
- Add a test that generated decision records reference only generated entity IDs and also include observation/version references where applicable.

**Risk Assessment: MEDIUM**

The generator is central to multiple later suites. The approach is good, but runtime and checksum coverage need careful hardening.

## 11-03 Micro Benchmarks and Scale Curves

**Strengths**

- Good benchmark coverage against D-23/D-24: operator categories, composed chain, composed-vs-sequential, factories, validation gates, `run_coroutine_sync`.
- Correctly avoids absolute timing assertions and delegates timing judgment to `gate.py`.
- Uses pedantic mode for scale benchmarks, which is appropriate for slower callables.
- Explicitly separates generation/setup from timed projection.
- Includes wall-time budget acceptance criteria.

**Concerns**

- **HIGH:** Assembly benchmarking may still include too much setup or teardown cost if fresh boot happens inside or near the timed callable incorrectly. The plan says use `setup=fresh_boot`, but pytest-benchmark setup behavior must be implemented carefully.
- **HIGH:** Monotonic median assertions for scale curves can be flaky even in report-only perf, especially if rung sizes are close after flexing or if caching effects dominate.
- **MEDIUM:** Composed-vs-sequential may not be semantically equivalent if the engine applies normalization, caching, or graph-view materialization differently between the two paths.
- **MEDIUM:** Factory construction benchmarks may accidentally include artifact parsing/registration if fixture boundaries are not strict.
- **LOW:** Benchmark count target of 10-15 is useful, but it may incentivize fitting arbitrary tests into the count instead of preserving stable, meaningful benchmark IDs.

**Suggestions**

- Add explicit comments or helper names separating timed functions from setup functions.
- For monotonic curves, prefer a soft sanity check or wide tolerance rather than hard strict monotonicity.
- Add correctness equivalence checks for composed-vs-sequential outputs before timing comparison.
- Record benchmark IDs in a committed manifest or README so baseline drift is easier to review.
- For scale assembly, write one small non-benchmark test proving generation is excluded from the timed callable.

**Risk Assessment: MEDIUM**

The suite likely achieves PERF-01/PERF-02, but the main risk is accidentally measuring fixture/setup behavior or adding flaky curve assertions.

## 11-04 Cross-Process and Replay

**Strengths**

- Correctly insists on real subprocess transport over localhost, with READY handshake and no sleeps.
- Startup/warmup exclusion is well handled conceptually.
- Good subprocess teardown requirements: terminate, wait, kill fallback.
- Replay plan includes both byte-exact correctness and growth-shape evidence, which matches PERF-03 better than pure timing thresholds.
- Localhost binding and no `0.0.0.0` checks are appropriate.

**Concerns**

- **HIGH:** Replay exponent assertion `b <= 1.0 + EPS` can be unstable with only three data points, especially if timings are noisy or the smallest rung has fixed overhead.
- **HIGH:** Writing `perf/results/replay.curve.json` from inside a test introduces a side-effect outside pytest-benchmark’s normal output path. This can conflict with “single pipeline” unless `gate.py` explicitly incorporates it.
- **HIGH:** Cross-process suite may depend on example 04 wiring. If it reuses example artifacts, it risks violating the neutral-domain requirement; if it creates a perf-local child, that is additional implementation surface not listed in files_modified.
- **MEDIUM:** “Byte-exact replay per rung” could become expensive if applied too broadly. The plan says sampled decision in action text, while must_haves says per rung; that should be clarified.
- **MEDIUM:** Persistent client/bridge state may hide connection setup costs. That is likely intended for latency, but should be documented as steady-state round-trip latency.
- **LOW:** Grep checks for `sleep(` and `0.0.0.0` are useful but brittle.

**Suggestions**

- Treat replay exponent as a reported metric plus broad guard, not a brittle hard assertion, or use more rungs if feasible.
- Make `gate.py` explicitly ingest supplemental result metadata if replay curve output is part of Phase 14 evidence.
- Add a perf-local child script to files_modified if that approach is used.
- Document cross-process numbers as warmed steady-state latency.
- Add subprocess failure diagnostics: captured stdout/stderr, exit code, ports, timeout reason.

**Risk Assessment: HIGH**

This is the most complex plan. It probably reaches PERF-03, but replay curve fitting and cross-process subprocess behavior are the highest flake and measurement-validity risks.

## 11-05 Smoke, CI, README, Calibration

**Strengths**

- Correctly keeps timing-dependent perf out of always-on CI while adding deterministic bitrot coverage.
- `workflow_dispatch`-only perf workflow is aligned with D-IMPL-70.
- Runner class is explicit and stable: `gh-ubuntu-24.04`.
- README scope is strong: re-baseline ritual, thresholds, seed, runner keys, speed-up policy, lint/typecheck scope.
- Full-battery calibration is the right final hardening step.

**Concerns**

- **HIGH:** Smoke tests that execute all suite callables once can still be very expensive, especially cross-process and replay, even with `--benchmark-disable`.
- **HIGH:** `CCF_PERF_SMOKE=1` requires all suites to honor the knob. If added late, it can become a parallel execution mode with its own drift risk.
- **MEDIUM:** The YAML validation snippet uses `yaml.safe_load`; if PyYAML is not already guaranteed in dev dependencies, this check may be environment-sensitive.
- **MEDIUM:** `perf.yml` installs `.[dev]`, which includes `ccf[perf]`; this is fine if 11-01 landed correctly, but failure mode should be clear.
- **LOW:** README may drift quickly from actual suite IDs, rung flexes, and thresholds unless there is a follow-up maintenance habit.

**Suggestions**

- Make smoke mode a first-class fixture behavior from the start: smallest rung, minimal rounds, no external long loops.
- Put a strict total timeout around the entire smoke test file as well as individual subprocesses.
- Add a workflow syntax check that does not rely on PyYAML unless already in dev dependencies.
- Include benchmark ID/rung manifest in `perf/README.md` or a generated results summary.
- Ensure `make ci` runtime increase is measured and documented, not just “noticeable runtime blowup.”

**Risk Assessment: MEDIUM**

The CI/governance design is solid. The main residual risk is always-on CI runtime creep from smoke tests.

## Cross-Plan Concerns

- **HIGH:** Benchmark ID stability is not treated as a first-class artifact. Since baselines key by ID, pytest parametrization/name drift can silently turn gated checks into “NO BASELINE — NOT GATED.”
- **HIGH:** Replay and scale suites risk measuring setup, caching, or fixture construction rather than the intended operations.
- **MEDIUM:** The plans rely heavily on grep/source assertions. These help, but should not replace behavioral tests for path traversal, no baseline writes, localhost binding, and smoke-mode rung limiting.
- **MEDIUM:** `perf/` being outside lint/typecheck scope is documented but leaves substantial Python code less protected. At minimum, targeted tests should import all modules and exercise major error paths.
- **LOW:** Some acceptance criteria are operationally expensive: full `pytest tests/ -q`, `make lint typecheck`, and full `make perf` after multiple plans. Worth doing, but summaries should record skipped checks explicitly if execution time prevents them.

## Overall Risk Assessment: MEDIUM

The plans are complete enough to achieve Phase 11’s goals and show strong governance discipline. The risk is not that the phase misses its scope; it is that the resulting battery may be flaky, expensive, or partially report-only due to benchmark ID drift and missing baselines. Post-execution hardening should focus on ID stability, smoke runtime, invalid runner-class tests, replay curve robustness, and making sure every benchmark measures the intended surface.

---

## Cursor Review

# Phase 11 Plan Review — Performance Battery

## Overall Summary

The five plans are unusually strong for a measurement phase: CONTEXT decisions are locked into concrete tasks, RESEARCH pitfalls are named and mitigated, D-IMPL-70 governance is structurally enforced (no auto-baseline, opt-in CI, single report+gate pipeline), and wave ordering is sound. Execution largely delivered PERF-01–04 mechanistically. The main plan-quality gap was **under-specified scale feasibility**: Wave 2 assumed a 1k/10k/100k ladder would hold with only top-rung flex, but ingestion cost and generator topology forced a much smaller assembly ladder and a replicated replay history — weakening the empirical force of PERF-02/PERF-03 curve claims even though the machinery is correct. Post-execution hardening should focus on measurement validity and always-on CI cost, not on rewriting the gate/ritual design.

---

## Plan 11-01 — Foundation (gate + Makefile + pytest-benchmark)

### Summary
Best-of-class foundation plan: A1 resolved first, pure-function gate with deterministic unit tests, loosen-only thresholds, path-traversal hardening on runner keys, and explicit “perf never joins `ci`.” This is the load-bearing PERF-04 / D-IMPL-70 piece, and it is scoped correctly (no benchmarks yet).

### Strengths
- Single pipeline for report + gate (D-02/D-03) — no parallel number paths
- TDD on fixture JSON/TOML; always-on CI can verify gate without timing
- Explicit D-13 / T-11-03: no write path to `perf/baselines/`
- Threat model covers tampering, path traversal, repudiation
- Speed-up → WARN (not fail) closes RESEARCH Open Question 1 before code

### Concerns
- **MEDIUM** — “Unknown runner class” and “known class, missing baseline” both collapse to report-only; fine for D-10/D-13, but the plan does not require distinct messaging, so operators can misread “`local` is fine” when gating never arms
- **LOW** — `perf/` left outside lint/mypy by design; plan records it for 11-05 but never budgets a follow-up to typecheck `gate.py`
- **LOW** — Suite targets may fail until Wave 2; acceptable, but Wave 1 “done” is partially non-runnable end-to-end

### Suggestions
- Document distinct notices: invalid key vs missing baseline file vs report-only known key
- Clarify gated statistic when p50 ≠ `statistics.median` (even N) — report both, gate one, name it in the docstring/tests
- Add a tiny Makefile dry-run acceptance that does not require suite dirs (already partly covered by `make -n`)

### Risk Assessment
**LOW** — Correctly scoped; execution confirmed A1 and 18 deterministic gate tests.

---

## Plan 11-02 — Synthetic generator + fixtures

### Summary
Solid PERF-02 substrate plan: values-in-artifacts, L2-only ingest, seed+checksum drift alarm, dual output (events + decision stream). The topology rules (D-27–D-30) are clear. The plan underestimates always-on cost of a real 1k fabric boot and does not pre-check generator constraints at small rungs.

### Strengths
- No-Hardcoding discipline (ontology/controlplane YAML; no `ccf.graph` in generator)
- Determinism via sorted checksums (Pitfall 4)
- Importable `perf.synth` for Phase 12 (D-06)
- Explicit single-writer path via `handle.worker.ingest`
- T-11-04/05 address artifact tampering and writer bypass

### Concerns
- **HIGH** — No spike for “can we ingest 10k/100k inside D-25?” before locking `RUNGS = (1k, 10k, 100k)`. Execution found ~5 ms/envelope → 10k assembly ≈ minutes per round; ladder flexed to (500, 1000). Plan’s D-07 language allowed top-rung flex, not collapsing the whole decade ladder
- **MEDIUM** — Always-on determinism test boots/ingests 1k (~46 s in SUMMARY). Plan waves at “size-guard in 11-05” but 11-05 only smokes suites — the expensive L2 proof stays in `make ci`
- **MEDIUM** — Unique-edge sampler hang below ~400 entities was invisible until Wave 2; topology constraints should have been acceptance criteria in 11-02
- **LOW** — Verify command allows either `synth.generator` or `perf.synth.generator` import paths — foreshadows packaging ambiguity for Phase 12

### Suggestions
- Add a Wave-1 “rung cost probe” task: time generate+ingest for 1k/10k once; record before Wave 2 commits ladder
- Pin minimum viable rung given hub/tail edge sampling math in generator docs/tests
- Move full 1k ingest proof behind a marker / smoke-only path; keep checksum pins cheap in always-on CI

### Risk Assessment
**MEDIUM** — Mechanism correct; scale-claim substrate weaker than ROADMAP wording implied.

---

## Plan 11-03 — Micro + fabric-scale suites

### Summary
Good coverage of D-23–D-26 with the right pedantic-mode discipline for slow callables and a clear “no absolute-time asserts” rule. Budget acceptance (≤3.5 min scale) was realistic. Weakest design point: D-24 composed-vs-sequential did not require apples-to-apples call paths, so timing evidence for composition can mislead Phase 14.

### Strengths
- Explicit pedantic mode + setup callable so assembly times ingest only (Pitfall 3)
- Representative micro set matches CONTEXT lock-in, including `run_coroutine_sync` (D-05)
- Correctness sanity asserts in every benchmark (T-11-08)
- Stable parametrized IDs called out for baseline keys (Pitfall 6)
- Gate remains sole timing judge

### Concerns
- **HIGH** — Scale success criteria still speak in “log ladder / curve shape” language while the plan’s only escape hatch is discretionary flex; without a Wave-1 cost probe, PERF-02’s “across graph sizes” claim can pass with two close rungs (happened: 500/1000)
- **MEDIUM** — D-24: `(A∘B)(G)` via engine vs `A(B(G))` as two ops — plan does not forbid measuring planning/as_of overhead on one side only (execution: ~227 ms vs ~1.2 ms). That is not composition-cost evidence; it is path-mismatch evidence
- **MEDIUM** — Micro suite wall time includes session `fabric_1k` build (~40 s); plan attributes budget to benchmarks but fixture cost eats the D-25 micro slice
- **LOW** — Extra artifacts (`agent.yaml`, `task.yaml`, …) appear in SUMMARY but not in plan `files_modified` — mild planning incompleteness, not scope creep

### Suggestions
- Require D-24 to time the same engine entrypoint twice (composed plan vs sequential plan) or document that the pair measures engine-vs-direct, not algebraic overhead
- Treat “≥2 decades of entity count in scale curves” as a must-have, or explicitly re-scope PERF-02 in ROADMAP/README when flexing below 10k
- Pre-build shared fabrics once per `make perf` invocation to reclaim micro budget

### Risk Assessment
**MEDIUM** — PERF-01 delivered cleanly; PERF-02 curve strength depends on how aggressively flex is used.

---

## Plan 11-04 — Cross-process + replay-at-scale

### Summary
Strong PERF-03 shape: real subprocess, READY handshake, warm-up exclusion, byte-exact before timing, exponent bound as primary guard. The plan left too much discretion on history generation and store population; execution needed replication + a bulk writer — both threaten the “year-scale empirical support” story if not framed carefully.

### Strengths
- Copies proven `tests/crossproc` lifecycle (no sleep-based spawn; terminate→wait→kill)
- Localhost-only bind asserted (T-11-09)
- Byte-exact assert precedes timing (T-11-11)
- Exponent written to an artifact for Phase 14
- Looser 25% suite default for transport noise (D-18/D-20)

### Concerns
- **HIGH** — Plan says ladder of decision records from the synthetic workload (D-16/D-30) but does not define what `decision_stream(n)` costs or whether records must be unique/non-replicated. Replication of a 10k base to 100k can produce a near-flat latency curve (execution: b≈0.001) that proves index lookup more than history scaling
- **MEDIUM** — Preferring a perf-local child vs example-04 reuse is left open; example-04 reuse pulls example-domain artifacts into the measurement substrate, conflicting with the “domain-neutral synthetic” narrative even if functionally honest
- **MEDIUM** — No plan for ArtifactStore population complexity; FileArtifactStore `put()` O(n²) forced a bulk writer. Timed path stayed public, but population purity/documentation was unplanned debt
- **MEDIUM** — Curve assert `b <= 1.0 + 0.1` is very loose: almost any non-superlinear system passes; with flat medians it does not discriminate regressions in history-scan cost
- **LOW** — Crossproc suite is short (~2 s measured) vs 2-minute budget — fine, but few benchmarks (≥2) means little signal diversity for PERF-03 latency

### Suggestions
- Specify: unique decision IDs, no replication unless documented as D-07 flex with impact on claim language
- Require replay timed path to exercise history-size-dependent work (or document that store is O(1) keyed and the claim is “replay resolution stays flat”)
- Tighten shape guard: e.g. fail if `b < 0` (measurement noise / wrong path) or require monotonic non-decrease of medians within epsilon
- Prefer perf-local child loading `perf/synth/artifacts` so Phase 12/14 can cite a neutral measurement stack

### Risk Assessment
**MEDIUM–HIGH** for claim validity; **LOW** for engineering/safety of the subprocess fixture. The year-scale story needs careful wording in Phase 14 PERFORMANCE.md.

---

## Plan 11-05 — Smoke, perf.yml, README, calibration

### Summary
Correct closing plan for PERF-04 mechanism and D-04 bitrot: opt-in `workflow_dispatch`, pinned runner image/key, ritual docs, full-battery calibration. Honest that the first baseline is a human/Dave gate. Weakness: always-on smoke cost (~2+ min) and incomplete linkage from Wave-2 flexes into “phase success = 10-min make perf” without re-validating claim strength.

### Strengths
- Mirrors `live-legs.yml` opt-in pattern; no push/PR triggers (T-11-12)
- `CCF_PERF_SMOKE` smallest-rung knob prevents CI wedge (T-11-14)
- README ritual matches D-IMPL-70 (manual baseline, DECISIONS.md log)
- Calibration task produces phase-gate wall-time evidence
- A3 `--benchmark-disable` verification called out

### Concerns
- **MEDIUM** — Smoke runs every suite via subprocess (~136 s) on top of 11-02’s ~46 s fabric proof — plan says “cheap” but always-on CI grew by minutes; no budget envelope for `make ci` growth
- **MEDIUM** — Phase can “succeed” with empty `perf/baselines/` forever; gating never arms until the human step. Plan notes this, but ROADMAP success criterion 4 reads like gating exists — mechanism yes, enforcement no
- **LOW** — Calibration “≤ ~12 minutes” acceptance is looser than D-17’s ~10; fine as tolerance, but invites future suite growth without re-ruling
- **LOW** — Does not require a dry-run of the re-baseline JSON transform (results → median-only baseline schema) as an automated helper test — ritual remains error-prone by hand

### Suggestions
- Add a deterministic “results → baseline draft” helper (still never writes baselines in CI) exercised in `tests/perf_gate`
- Cap always-on perf-related time (e.g. smoke + synth ≤ 90 s) or mark heavy proofs optional
- Make Human Verification (first `gh-ubuntu-24.04` baseline) an explicit D-GATE-11 prerequisite in DECISIONS, not only VERIFICATION.md

### Risk Assessment
**LOW** for shipping the mechanism; **MEDIUM** until the first Dave-approved baseline exists (gating is dormant).

---

## Cross-Cutting Assessment

| Focus | Verdict |
| --- | --- |
| Achieves phase goals? | **Mostly yes** for harness/governance; **partially** for “three-decade scale curves” and “year-scale empirical proof” as originally worded |
| Dependency ordering | Wave 1 → 2 → 3 correct; 11-03 ∥ 11-04 appropriate |
| Scope creep | Low — stayed in `perf/`, no `/src` fixture machinery |
| Security | Good for a perf tree: localhost bind, charset-safe keys, no PR-triggered workflow, no baseline auto-write |
| Over-engineering | Low — stdlib gate, pytest-benchmark, no CodSpeed/external service |
| Missing edge cases | Runner-key UX; even-N median; small-rung topology; ArtifactStore write amplification; D-24 path mismatch |

### Top post-execution hardening priorities
1. **Re-scope or restore scale claims** — either invest in faster assembly / fewer rounds at 10k+, or update ROADMAP/PERF-02 language to the flexed (500, 1000) ladder and treat 10k/100k as Phase 12/14 follow-ons  
2. **Harden PERF-03 narrative** — document replication + O(1) store semantics; tighten curve asserts so “fake flat” still catches broken replay  
3. **Fix D-24 comparability** before PERFORMANCE.md cites composed-vs-sequential medians  
4. **Cut always-on cost** — checksum-only in default CI; keep full L2 ingest as opt-in/marked  
5. **Complete D-GATE** — dispatch `perf.yml`, record `gh-ubuntu-24.04` baseline under D-IMPL-70  

### Overall Risk Level
**MEDIUM**

Justification: Plans are high quality on governance, invariants, and engineering seams (the hard parts of D-IMPL-70). Residual risk is measurement validity and claim overstatement — exactly where discretionary flex and under-spiked scale costs hit during execution — plus dormant gating until the first human baseline. That is the right place to harden before Phase 12 reuses `perf/synth` and Phase 14 publishes PERFORMANCE.md.

---

## Ollama Review (gpt-oss:120b-cloud)

# Phase 11 – Performance Battery Review  

**Overall assessment:**  
The five‑wave implementation delivers a complete, reproducible performance‑measurement stack that satisfies all four performance requirements (PERF‑01 – PERF‑04) and adheres to the hard governance rules (D‑IMPL‑70, D‑04, D‑10‑D‑14).  The work is well‑structured, the deliverables are clearly split across make‑targets, pytest‑benchmark suites, a single gate pipeline, a deterministic synthetic data generator, and an opt‑in CI workflow.  Most of the documented decisions have been realized exactly as intended, and the “bit‑rot smoke” test guarantees that the perf tree stays import‑able even when the full benchmark suite is disabled.

Below we detail the strongest aspects, the remaining gaps, and concrete actions to harden the implementation before the next phase.

---

## 1. Strengths  

| Area | What was done well |
|------|--------------------|
| **Decision‑driven design** | Every major choice (benchmark harness, thresholds format, runner‑class key, synthetic‑data neutrality, cross‑process isolation) is captured as a D‑XX entry and the code follows it verbatim. |
| **Single‑pipeline gate** | `perf/gate.py` reads the raw pytest‑benchmark JSON, computes p50/p95/p99/median, applies suite‑level relative‑median thresholds, and writes a *single* results JSON – eliminating any “two‑pipeline” drift. |
| **Deterministic synthetic generator** | Seeded `random.Random`, fixed seed (`20260801`), checksum over sorted URIs & edges, and explicit shape pins in `tests/perf_synth`. No use of `datetime.now()`, no graph‑internal imports, and all ontology data lives in YAML artifacts (No‑Hardcoding). |
| **Cross‑process realism** | Real MCP server and A2A/peering processes spawned locally, handshake via a `READY` line, warm‑up round‑trips, and clean teardown (terminate → wait → kill). No network exposure beyond `127.0.0.1`. |
| **Replay‑at‑scale validation** | Byte‑exact replay verification plus a log‑log linear‑fit (`t = a·nᵇ`) with an explicit bound (`b ≤ 1.0 + 0.1`). The exponent is written into the results JSON for downstream Phase‑14 reporting. |
| **Opt‑in CI integration** | `perf.yml` mirrors the existing `live‑legs.yml` pattern (workflow‑dispatch only, pinned runner class, artifact upload). The always‑on CI suite includes a tiny “bit‑rot smoke” test that guarantees the perf tree remains importable. |
| **Documentation & ritual** | `perf/README.md` spells out the re‑baseline ritual, runner‑class list, threshold policy, and the 10‑minute budget, referencing the exact decisions that lock each parameter. |
| **Test coverage** | Unit tests for gate logic (8+ tests covering percentiles, thresholds, missing baseline, ID‑drift, speed‑up warnings), deterministic generator tests, and smoke tests ensure the code is exercised in the never‑failing CI path. |

---

## 2. Concerns  

| # | Concern | Severity | Why it matters |
|---|---------|----------|----------------|
| **C1 – Baseline schema validation** | `perf/gate.py` only *loads* `perf/baselines/<runner>.json` but does not validate the JSON schema (metadata fields, numeric median values). | **MEDIUM** | A malformed baseline could cause a silent pass (or crash) and hide regression. |
| **C2 – Cross‑Python reproducibility** | The synthetic generator uses `random.Random` which is stable *within* a Python version but may change across versions. The benchmark suite does not pin the interpreter version beyond the repo’s `pyproject.toml` `requires‑python`. | **MEDIUM** | A future bump of the interpreter could alter checksums and break the deterministic guarantees without a visible loss. |
| **C3 – Runner‑class sanitisation** | The gate reads `CCF_PERF_RUNNER_CLASS` and joins it directly into a file path (`perf/baselines/<key>.json`). No explicit whitelist of allowed characters is enforced in code (only documented). | **LOW** | Path‑traversal attacks are unlikely in a private repo but worth tightening. |
| **C4 – Subprocess resource leakage** | The cross‑process fixtures spawn a child process but do not set a resource‑limit (CPU time / memory). If the child hangs or allocates excessively, the CI job could exceed its timeout. | **LOW** | The smoke tests use a short warm‑up, but a malformed change to the child script could cause a hang. |
| **C5 – Threshold loosen‑only enforcement** | The parser for `perf/thresholds.toml` raises a generic `ValueError` if an override is tighter than the suite default. The error message is not user‑friendly, and there is no test that verifies the error is raised for every possible case. | **LOW** | Developers may inadvertently add a tighter override and receive an unhelpful stack trace, leading to debugging friction. |
| **C6 – Benchmark‑budget calibration drift** | The 10‑minute total budget is enforced only by manual observation during `make perf` runs. No automated guard (e.g., a “max‑wall‑time” check in the Makefile) exists; future additions could silently blow the budget. | **MEDIUM** | The budget is a core success criterion (PERF‑01, D‑25) – we need a hard guard. |
| **C7 – Missing “absolute‑time” guard in user‑benchmarks** | The policy “no absolute‑time asserts” is enforced by grep‑search in the acceptance criteria, but the code does not prevent a contributor from adding an `assert elapsed < …` that evades the grep (e.g., using a variable). | **LOW** | Undermines the “gate‑only” timing enforcement philosophy. |
| **C8 – No provenance for synthetic‑data YAML artifacts** | The ontology and control‑plane YAML files are committed, but there is no checksum or version‑tag recorded in `perf/README.md`. A downstream change could unintentionally modify the neutral ontology. | **LOW** | Violates the “deterministic generator” guarantee. |

---

## 3. Suggestions  

| Ref | Action |
|-----|--------|
| **S1 (C1)** | Add a lightweight JSON‑schema validator (e.g., using `jsonschema` or a hand‑rolled dataclass) that runs at the start of `gate.py`. The validator should enforce the presence of `"metadata"` with required keys (`date`, `commit`, `approved`) and `"benchmarks"` mapping ids → numeric medians. |
| **S2 (C2)** | Record the exact Python version used for baseline generation inside the baseline JSON (`metadata.python = "3.12.3"`). In CI, add a pre‑check that the running interpreter matches the version in the baseline, otherwise emit a clear “baseline‑version mismatch” warning and abort. |
| **S3 (C3)** | In `gate.py`, sanitize `CCF_PERF_RUNNER_CLASS` with a regex `^[A-Za-z0-9._-]+$`. Reject any other value with a deterministic “unknown runner class” message (already documented) but now guaranteed safe. |
| **S4 (C4)** | Use `subprocess.Popen(..., start_new_session=True)` and set a `resource.setrlimit` (CPU time, memory) before spawning the child in the cross‑process fixture. Add a timeout to the child‑process `wait()` call (e.g., 30 s) and fail the test if exceeded. |
| **S5 (C5)** | Replace the generic `ValueError` with a custom exception `ThresholdOverrideError` that prints a helpful message: “Override for benchmark `<id>` is tighter (`<value>`) than suite default (`<default>`); overrides may only loosen.” Add a unit test that deliberately creates a tighter override and asserts the specific exception type/message. |
| **S6 (C6)** | Extend the `Makefile` perf targets to capture the wall‑time (`/usr/bin/time -f "%e"`). After each suite run, parse the elapsed seconds and abort with a non‑zero code if the total exceeds the per‑suite budget (2 min, 3 min, 2 min, 3 min). This makes the 10‑minute budget an *enforced* invariant. |
| **S7 (C7)** | Provide a lint rule (e.g., a `ruff` plugin) that flags any `assert` whose operand contains the word `elapsed` or `duration`. Add it to the repo’s lint configuration for the `perf/` tree. |
| **S8 (C8)** | Compute a SHA‑256 checksum of each YAML artifact at generation time and embed those values in `perf/README.md` under a “Data‑artifact provenance” section. Update the checksum whenever the file changes (CI can assert the checksum matches the committed value). |
| **S9 (General)** | Add an explicit entry in `docs/DECISIONS.md` for the **baseline‑schema** and **runner‑class sanitisation** decisions (new D‑XX IDs) so that future reviewers see the rationale. |
| **S10 (Documentation)** | In `perf/README.md`, add a short FAQ: “What if my local Python version differs from the baseline?” and “How do I add a new benchmark without breaking the gate?”. This reduces onboarding friction. |

---

## 4. Risk Assessment  

| Risk Level | Justification |
|------------|----------------|
| **MEDIUM** | The implementation meets all functional success criteria, but the lack of hard validation for baseline files, interpreter version drift, and automated budget enforcement introduces a *medium* probability of regression or silent drift in future iterations. These risks are not show‑stoppers now (the current baseline exists and the suite passes), yet they could jeopardize the “reproducible performance battery” promise when the codebase evolves or when new contributors add benchmarks. Adding the mitigations listed in **S1–S6** would lower the risk to **LOW**. |

---

## 5. Closing Remarks  

Phase 11 delivers a high‑quality, decision‑aligned performance battery. The codebase is clean, the governance model is well‑documented, and the CI integration respects the “opt‑in only” rule. By tightening schema validation, enforcing the runtime budget programmatically, and adding a few safety nets around versioning and path sanitisation, the battery will become *future‑proof* and fully satisfy the hard‑coded success criteria for the next phase.

---

## Consensus Summary

Reviews ran post-execution (plans already executed); feedback informs post-execution hardening and Phases 12/14. Risk verdicts: Gemini LOW, Codex MEDIUM, Cursor MEDIUM, Ollama MEDIUM.

### Agreed Strengths
- Single report+gate pipeline with D-IMPL-70 governance (manual Dave-gated baselines, loosen-only thresholds, opt-in workflow_dispatch CI) — all four reviewers
- Deterministic seeded generator with checksum drift pins, No-Hardcoding via YAML artifacts, L2-only single-writer ingestion — all four
- Real-subprocess cross-process realism (READY handshake, warm-up exclusion, terminate→wait→kill teardown, 127.0.0.1-only) — Codex, Cursor, Ollama
- Byte-exact replay assert preceding timing plus power-law exponent evidence — Gemini, Cursor, Ollama
- Bitrot smoke keeps timing-dependent perf out of always-on CI — Gemini, Codex, Cursor

### Agreed Concerns (2+ reviewers — highest priority)
1. **Scale-claim strength after the D-07 rung flex (Codex HIGH, Cursor HIGH, Gemini MEDIUM).** The assembly ladder collapsed from 1k/10k/100k to (500, 1000) and the 100k replay rung is deterministic replication. Machinery is correct, but "three-decade curve" / "year-scale" claim language must be re-scoped (or ingestion made faster) before Phase 14 publishes PERFORMANCE.md. The ~5 ms/envelope L2 ingestion cost the battery surfaced is itself a finding worth architectural attention.
2. **Replay exponent bound too loose / potentially non-discriminating (Codex HIGH, Cursor MEDIUM).** With 3 rungs and a replicated history, b≈0.001 proves keyed lookup more than history scaling; the b ≤ 1.1 guard passes almost anything. Tighten shape guards and document store O(1) semantics.
3. **Always-on CI cost creep (Codex HIGH, Cursor MEDIUM).** The 1k fabric ingest proof (~46 s) plus smoke (~136 s) grew `make ci` by minutes; cap or mark heavy proofs.
4. **Gating dormant until first baseline (Cursor MEDIUM, Ollama implied).** Phase can "pass" with empty perf/baselines forever; the manual gh-ubuntu-24.04 dispatch is the arming step — tracked in 11-HUMAN-UAT.md.
5. **D-24 composed-vs-sequential path mismatch (Codex MEDIUM, Cursor MEDIUM).** 227 ms vs 1.2 ms measures engine as_of/dispatch overhead, not composition cost — must not be cited as algebra overhead in Phase 14.
6. **Baseline schema/ID robustness (Codex HIGH, Ollama MEDIUM).** Benchmark ID drift silently reverts to "NO BASELINE — NOT GATED"; baseline JSON lacks schema validation and interpreter-version provenance.

### Divergent Views
- Gemini rates overall risk LOW (governance defuses flake risk); the other three rate MEDIUM, weighting measurement-validity and claim-overstatement risk.
- Ollama suggests hard Makefile wall-time budget enforcement; Cursor prefers budget observation with explicit re-ruling — a governance-style choice for Dave.
- Codex flags grep-based assertions as needing behavioral-test replacements; Gemini treats them as adequate given the private-repo posture.

### Notes vs current state
Some findings were already addressed post-review-fixes before this cross-AI pass: typed ThresholdConfigError (Ollama C5/S5 = WR-04, fixed 02c3c16), runner-class regex sanitization in code (Ollama C3/S3 — already implemented, gate.py:62), subprocess process-group teardown (Ollama C4/S4 partial = WR-01/WR-02, fixed b3cb64b/9d22648), sampler feasibility guard (Cursor 11-02 concern = WR-03, fixed c78bf21).
