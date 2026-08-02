---
phase: 12
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-08-02T13:15:00Z
plans_reviewed: [12-01-PLAN.md, 12-02-PLAN.md, 12-03-PLAN.md]
---

# Cross-AI Plan Review — Phase 12

## Gemini Review

# Phase 12 Implementation Plan Review: Synthetic-Data Demonstration

This review evaluates the three implementation plans for Phase 12 (`12-01-PLAN.md`, `12-02-PLAN.md`, `12-03-PLAN.md`). The phase focuses on delivering a deterministic, end-to-end "hero" demonstration of the CCF SDK using a banking fraud-detection scenario.

## 1. Summary
The implementation plans for Phase 12 are exceptionally thorough and rigorous, directly addressing the core value of "whitepaper fidelity" through an executed proof of L2 entity resolution. By requiring a baseline contrast run where raw data fails to detect a fraud ring that governed context successfully identifies, the plans move beyond simple "happy path" examples to a meaningful technical demonstration. The architectural discipline—specifically the "No-Hardcoding" rule, deterministic synthetic generation, and byte-compared console narration—ensures the demo is both a reliable CI gate and a stable teaching tool for the Phase 14 documentation site.

## 2. Strengths
*   **Executed Baseline Contrast:** Requirement **D-11** (executing detection on raw data vs. governed context) is the most critical part of the demo. It empirically proves the value of the fabric rather than just asserting it.
*   **Rigorous Determinism:** The plans borrow the "seed + logical checksum" discipline from the performance battery (Phase 11) but apply it to a story-driven domain. Using `SELECT ... ORDER BY` and sorted row tuples for checksums (Pitfall 2 mitigation) ensures CI stability across environments.
*   **Artifact-Driven Architecture:** Adherence to `CLAUDE.md §6.4` (No-Hardcoding) is absolute. The generator and `run.py` are pure interpreters; the entire "fraud ring" story, vocabulary, and success criteria live in `scenario.yaml` and `controlplane.yaml`.
*   **Staged Narration Assertion:** Byte-comparing the entire console output (D-16) is a high-signal validation technique. It ensures that the "story" told to the user remains exactly as intended, preventing "output rot" where logs change but the code still "passes."
*   **L2 Hero Moment:** The ontology rules specifically target the resolution of disjoint identifiers (Account # vs. Wire Name vs. KYC ID) through linking evidence (Tax ID/Address), which perfectly showcases the L1→L2 transition.

## 3. Concerns
*   **Brittleness of Byte-Compared Narration (LOW):** While a strength for consistency, byte-comparing long strings of console output can be brittle if absolute paths, timestamps, or library-specific version strings (e.g., SQLite version) accidentally leak into the buffer. 
    *   *Mitigation:* Task 12-02.3 explicitly warns that every banner fact must be deterministic and mentions avoiding paths/clocks.
*   **Complexity of `run.py` (LOW):** With six stages, a baseline contrast, agent/skill wiring, and a `--live` LLM branch, `run.py` could become a monolithic file.
    *   *Mitigation:* The plan uses a staged structure and helper functions (`_banner`, `_load`, etc.) mirrored from the `00-quickstart` pattern to keep it readable.
*   **Snippet Path Stability (MEDIUM):** The `docs/demo-walkthrough.md` relies on `pymdownx.snippets` with repo-root-relative paths. If the mkdocs configuration in Phase 14 changes the `base_path`, these includes will break.
    *   *Mitigation:* Task 12-03.2 includes a header comment for Phase 14 developers regarding this assumption.

## 4. Suggestions
*   **SQLite Visibility:** In `generator.py`, ensure the SQLite tables have clean schemas (explicit `CREATE TABLE` with types) so that when a user follows the README's suggestion to "open the .db files with the sqlite3 CLI," the experience is polished and professional.
*   **Cycle Detection Skill Robustness:** Ensure the cycle-detection logic handles the edge case of multiple disjoint cycles (though the scenario only plants one) to keep the "Analytics" part of the agent's archetype credible.
*   **LLM Provider Graceful Failure:** In the `--live` branch of `run.py`, ensure that if the LLM provider is not configured (e.g., missing API key), the script provides a helpful error message and exits gracefully rather than a raw stack trace, as this is a user-facing demo.

## 5. Risk Assessment: LOW
The risk is **LOW**. The plans are highly aligned with existing project invariants (`CLAUDE.md`), utilize proven patterns from previous examples, and include comprehensive automated verification at every step (checksums, pytest, and byte-comparison). The dependency chain is clear, and the "executed contrast" provides a definitive success signal that is difficult to fake or misinterpret.

**Justification:**
1.  **Requirement Coverage:** 100% of DEMO-01/02/03 are addressed with specific, testable tasks.
2.  **Invariant Protection:** The "No-Hardcoding" and "Deterministic CI" rules are enforced through automated lints and checksum pins.
3.  **Sustainability:** By wiring the demo into `make examples`, it becomes a permanent part of the regression suite, ensuring it won't break as the SDK evolves toward v0.2.

---

## Codex Review

**Summary**

The three plans are strong on phase-goal alignment: they decompose DEMO-01/02/03 cleanly, preserve the artifact-first No-Hardcoding invariant, and explicitly prove the headline claim through an executed baseline and governed-context contrast. The main follow-up risks are implementation brittleness from very broad `run.py` scope, dynamic artifact interpretation details, and CI determinism fragility. I could not inspect the workspace artifacts directly because shell commands failed in the sandbox, so this review is based on the submitted plans.

## Plan 12-01 — Scenario + Generator

**Strengths**

- Clear DEMO-01 mapping: deterministic SQLite store, three sources, planted ring, checksums, row counts.
- Good determinism posture: fixed seed, fixed epoch, logical-content checksums instead of SQLite file-byte checksums.
- Strong No-Hardcoding intent: domain values, ring identifiers, noise rules, expected values all live in `scenario.yaml`.
- Good separation from `perf/synth`: borrows discipline without importing its ontology.

**Concerns**

- **HIGH:** The SQL security mitigation says “parameterized queries only,” but table and column identifiers cannot be parameterized. If identifiers come from YAML, the plan needs explicit identifier validation/quoting rules.
- **MEDIUM:** “No source-name/table-name literals in generator.py” may push the generator toward an overly generic schema engine. That can make the demo harder to maintain than a thin, constrained interpreter.
- **MEDIUM:** Expected checksums are backfilled after first generation, but the plan does not define a reviewed regeneration workflow or helper command. Pin drift could become noisy.
- **MEDIUM:** No explicit bounds validation for scenario counts, table names, output paths, or infeasible ring/noise combinations beyond generic `ValueError`.
- **LOW:** The “no naive string overlap” criterion is good, but it needs a precise automated test, not just spot grep.

**Suggestions**

- Add a small `validate_scenario()` step that enforces allowed identifier regexes, row-count caps, unique ring IDs, valid timestamps, and output filenames.
- Add tests proving no raw source alone contains the cycle, and that the ring signature changes if any planted edge/member changes.
- Document the expected-checksum regeneration command and require tests to fail until pins are deliberately updated.
- Prefer a constrained interpreter for the three known source shapes over a fully generic database generator.

**Risk Assessment: MEDIUM**

The plan achieves DEMO-01 well, but dynamic SQL/schema interpretation and pin lifecycle need tightening to avoid fragile or unsafe artifact execution.

## Plan 12-02 — End-to-End Demo

**Strengths**

- Directly targets the phase’s core story: raw data fails, L2 resolution enables governed context, agent finds the ring.
- The baseline contrast is executed, not asserted, which is the strongest part of the design.
- Keeps detection deterministic and `--live` narration-only, preserving CI stability.
- Uses existing SDK surfaces: ingest worker, Context Product gates, AgentFactory, SkillCatalog, GrantLedger, replay.

**Concerns**

- **HIGH:** Scope is very large for one `run.py`: generation, raw SQL baseline, ingest, graph construction, operators, projection, product gating, agent skill dispatch, replay, byte comparison, and live narration. This is high brittleness for a showcase example.
- **HIGH:** The “same cycle-detection function” is used for baseline and governed skill. That is good for proof, but if it is implemented as a local helper in `run.py`, follow-up should ensure the governed path really exercises granted skill dispatch and not an ad hoc shortcut.
- **MEDIUM:** The plan depends on ontology rules linking deliberately planted evidence. It needs tests/validation that the rules are not overfit to the five planted members or producing false-positive merges in noise.
- **MEDIUM:** Byte-comparing full stdout is valuable but fragile if SDK object ordering, IDs, or repr output leak into banners.
- **MEDIUM:** `--live` provider/configuration mechanics are underspecified. Deferred imports are good, but missing config handling can create poor newcomer UX.
- **LOW:** The four-operator chain may be more than the demo story needs. If any operator is incidental, it may obscure L2 as the hero.

**Suggestions**

- Extract deterministic helpers inside `run.py` or adjacent private modules only if existing example discipline allows it: `load_raw_edges`, `detect_cycles`, `build_product_payload`, `render_narration`.
- Add explicit assertions that baseline detection over each source and over combined raw identifiers finds zero cycles.
- Add a noise validation test: known non-ring counterparties should not collapse into the ring canonical entities.
- Normalize every printed value before byte compare: sorted lists, stable IDs, no temp paths, no dynamic timestamps.
- Make `--live` fail with a clear message when config is absent, after deterministic assertions have already passed.

**Risk Assessment: MEDIUM-HIGH**

The plan satisfies DEMO-02 conceptually, but it concentrates many SDK surfaces in one example. Follow-up should focus on reducing brittleness and proving the resolution rules are general enough for the synthetic noise.

## Plan 12-03 — CI + README + Walkthrough

**Strengths**

- Correctly reuses existing example CI wiring instead of adding workflow complexity.
- Keeps README short and pushes teaching content into `docs/demo-walkthrough.md`.
- Literal-include requirement is well covered with path-resolution verification.
- Good discipline around excluding `--live` from always-on CI.

**Concerns**

- **MEDIUM:** The docs include check only verifies paths exist. It does not verify snippet syntax will work under Phase 14’s actual MkDocs/pymdownx configuration.
- **MEDIUM:** `make examples` could become materially slower with a 1k–5k entity demo plus full pipeline/replay. The plan lacks a runtime budget.
- **LOW:** The threat model says docs include only `examples/08-e2e-demo` paths, but the plan also mentions validation and internal planning files. Follow-up should ensure published docs do not expose `.planning` content.
- **LOW:** “No expected-output regeneration of examples 00–07” is good but should be checked by git diff or a targeted assertion in validation.

**Suggestions**

- Add a docs-build or snippet-render smoke test once Phase 14 tooling exists.
- Record runtime for `make example-08` and set a soft budget, e.g. CI target under a few seconds or a documented threshold.
- Add a validation check that walkthrough includes only publishable paths.
- Include `make example-08` in a targeted CI step if `make examples` failures become too broad to diagnose quickly.

**Risk Assessment: LOW-MEDIUM**

The CI/docs plan is practical and low-infrastructure. Main risk is docs-snippet compatibility and runtime growth once the demo is in the full examples suite.

## Overall Risk Assessment: MEDIUM

The phase plans are complete and well aligned with DEMO-01/02/03. The strongest design choices are deterministic execution, artifact-owned domain values, and the executed raw-vs-governed contrast. Follow-up should address three areas: validate dynamic YAML-driven SQL/schema inputs, prove L2 resolution is not overfit to the planted ring, and keep the end-to-end example stable enough for byte-compared CI.

---

## Cursor Review

# Cross-AI Plan Review — Phase 12: Synthetic-Data Demonstration

**As-built verdict:** The three plans correctly scoped DEMO-01..03, sequenced well, and shipped a working demo that meets the phase goal. Residual risk is mostly in **robustness of mechanism the docs invite users to reuse**, not in missing deliverables. Phase verification reports 12/12 truths green; code review already logged five warnings worth follow-up.

---

## Overall Assessment

| Dimension | Rating |
|-----------|--------|
| Goal alignment (DEMO-01..03) | Strong |
| Wave/dependency design | Strong |
| Invariant discipline (No-Hardcoding, single-writer, CI-deterministic) | Strong |
| Threat model completeness | Adequate on intent; incomplete on identifier/encoding edge cases |
| Follow-up risk | **MEDIUM** (mechanism hygiene + process close-out) |

---

## 12-01-PLAN.md — Scenario + Generator + Checksum Pins (DEMO-01)

### 1. Summary

A tight, well-bounded Wave 1 plan: scenario artifact as vocabulary source, pure-interpreter generator, three-way determinism pins. As-built matches intent (role-keyed interpretation, ~1.2k noise population, 5-member ring, pytest pin suite). The plan correctly separated “story ontology” from `perf/synth` and made the scenario the teaching centerpiece.

### 2. Strengths

- Clear No-Hardcoding contract: every domain value in `scenario.yaml`; generator as interpreter
- Determinism triad (seed + checksum/shape + later byte-compare) aligned with D-08 and v0.1 example discipline
- Explicit RESEARCH pitfalls (UTC timestamps, logical vs file checksums, disjoint identifiers)
- TDD task shape with concrete behaviors (regenerate-twice, pin match, ring signature)
- Threat note on parameterized value binds; single-writer boundary stated early

### 3. Concerns

- **MEDIUM — Identifier SQL quoting underspecified:** Plan mitigates T-12-01 as “parameterized queries,” but table/column names are artifact-interpolated. As-built uses `f'"{name}"'` without escaping embedded `"`. Docs invite users to author scenarios → incomplete mitigation (code review WR-03).
- **MEDIUM — Checksum encoding not specified:** Plan required “sha256 over sorted logical content” but not unambiguous field encoding. As-built `|`-join/`str()` is collision-prone for `|`/`\n`/NULL/`"None"` (WR-05). Drift alarm can miss real content changes.
- **LOW — Acceptance grep brittleness:** “No table name in generator.py” forced a mid-execution rename of noise keys (documented in 12-01-SUMMARY). Criterion was right; plan could have prescribed role-keyed count keys up front.
- **LOW — key_link over-specified:** Plan linked `yaml.safe_load` inside `generator.py`; as-built loads in the caller and passes a dict — stronger separation, but the plan’s pattern check would have been a false fail.

### 4. Suggestions (follow-up)

- Centralize `_ident()` with `"` escaping for all DDL/SELECT interpolations
- Switch checksum rows to `repr(tuple(row))` or length-prefixed fields
- Prefer “generator holds zero domain vocabulary via role keys” over brittle string greps in future plans

### 5. Risk Assessment

**LOW** for DEMO-01 delivery; **MEDIUM** for “change scenario.yaml to make your own demo” as a reusable interpreter.

---

## 12-02-PLAN.md — End-to-End `run.py` (DEMO-02)

### 1. Summary

The load-bearing plan. Stages, baseline contrast, factory/skill path, byte-compared narration, and `--live` narration-only are correctly specified and map 1:1 to D-09..D-16. As-built delivers the headline claim (baseline 0 / governed ring) with exit-0 and byte-stable stdout. Main plan gap: treating cycle detection as “thin glue” without specifying algorithmic edge cases — those gaps are now live in `run.py`.

### 2. Strengths

- **Executed contrast** as a first-class stage (not a prose claim) — strongest design choice in the phase
- Correct factory/skill/grant/ledger path; detection stays algorithmic; LLM deferred inside `--live`
- Single-writer enforced via `worker.ingest` only; mirrors quickstart/01/06 patterns from PATTERNS.md
- Staged narration buffer + committed `expected_output.txt` matches examples CI discipline
- Clear separation: `--live` never feeds assertions or always-on CI

### 3. Concerns

- **HIGH (latent) — Verification via bare `assert`:** Plan’s acceptance is “assertions present and passing,” which matches other examples, but every load-bearing check in `run.py` is `assert`. Under `python -O` / `PYTHONOPTIMIZE=1`, checks vanish while README claims “Exit code 0 means every assertion held” (WR-01). Latent in current CI; real if anyone optimizes the env.
- **MEDIUM — Cycle algorithm underspecified:** Plan required “same cycle-detection function” artifact-parameterized, but not zero/negative amounts, recursion bounds, or cycle-identity semantics. As-built: `/ previous` ZeroDivisionError / sign bug (WR-02); unbounded `_walk` recursion (WR-04); member-set dedupe undercounts distinct cycles (IN-02).
- **MEDIUM — Monolith size / test gap:** Plan `min_lines: 250`; as-built ~1076-line `run.py` with detection, ingest mapping, projection, agent, replay, and live branch. Only generator has unit tests; e2e correctness is one integration run. Fine for an example, weak if users copy the skill as mechanism.
- **LOW — No-Hardcoding vs algorithm-in-example:** Detection algorithm lives in example code (correct for mechanism), but walkthrough/README frame it as “change the scenario.” Users may reasonably expect the callable to tolerate adversarial/edge scenario values; plan never set that bar.
- **LOW — Scope adjacency:** Full L1→L6 + agent + skill + replay + live in one plan is large for three tasks; it worked, but left little room for extracting a tested cycle helper.

### 4. Suggestions (follow-up)

- Replace pin/narration checks with an unconditional `_require(...)` helper (keep `assert` only for type narrowing if desired)
- Harden `_extends` (abs denominator; zero-safe); convert `_walk` to iterative stack or capped path length from artifact
- Add a small unit test module for `_structured_cycles` covering zero amount, negative amount, deep graph, two cycles same members
- Optionally extract cycle detection to `examples/08-e2e-demo/cycle_detect.py` (still example-local, not `/src`) for testability
- Document member-set dedupe semantics in `skills.yaml` description

### 5. Risk Assessment

**MEDIUM** — DEMO-02 achieved; residual risk is silent verification under `-O` and fragile reuse of the detection helper.

---

## 12-03-PLAN.md — Makefile/CI + Walkthrough (DEMO-03)

### 1. Summary

Correctly minimal Wave 3: join existing `make examples` harness, short README, mkdocs-ready walkthrough with `--8<--` includes, validation close-out. As-built wires `example-08`, ships a 291-line walkthrough with 10 resolving includes. Process/docs hygiene left a few stale markers.

### 2. Strengths

- Zero new CI infrastructure — right call given D-13 and existing examples job
- Explicit “no live Makefile target” prevents regressing Phase-8 D-10 / D-IMPL-70
- Walkthrough Phase 14 `base_path` header is the right forward-compat contract
- Automated verify that every include path exists
- Validation map ties DEMO-01/02/03 to real commands

### 3. Concerns

- **MEDIUM — Full-file includes vs staged teaching:** Plan asked for stage-relevant includes (or section includes); acceptance only required ≥5 includes. As-built includes entire `run.py`, `generator.py`, and full YAMLs — correct for “never paste,” but dumps ~1.5k+ lines into the docs site and weakens “step-by-step” legibility (still the open human UAT item).
- **MEDIUM — REQUIREMENTS.md not in plan close-out:** DEMO-01..03 remain unchecked/`Pending` in `.planning/REQUIREMENTS.md` despite VERIFICATION claiming satisfaction. Phase bookkeeping drift.
- **LOW — Stale CI job label:** Plan said “no workflow edit,” so `ci.yml` still names the step “Run all **eight** examples” while Makefile runs nine. Harmless functionally; confusing for operators.
- **LOW — `make examples` as DEMO-03 verify:** Correct for CI inclusion, but expensive as the only DEMO-03 automated gate; walkthrough include check is the better unit of that requirement (already present).
- **LOW — Threat T-12-07:** Mitigate by path allowlist is good; plan did not require a CI grep that walkthrough includes stay under `examples/08-e2e-demo/` (easy Phase 14 safeguard).

### 4. Suggestions (follow-up)

- Switch large includes to pymdownx section snippets (ring block, Stage 2/5 functions) while keeping one “full scenario” include as the teaching centerpiece
- Flip REQUIREMENTS.md DEMO checkboxes / tracker to Satisfied as part of phase gate
- One-line `ci.yml` rename: eight → nine (or “all examples”)
- Add a tiny test/script: walkthrough `--8<--` paths ⊆ `examples/08-e2e-demo/`

### 5. Risk Assessment

**LOW** for CI wiring; **MEDIUM** for docs pedagogy / Phase 14 mount quality if full-file dumps ship unchanged.

---

## Cross-Cutting: Do the Plans Achieve the Phase Goals?

| Success criterion | Plan coverage | As-built |
|---|---|---|
| Deterministic multi-entity store; domain in artifacts | 12-01 | Met |
| L1→L6 + agent solves problem unreachable from raw data | 12-02 (baseline + governed) | Met — contrast executed |
| CI one command + walkthrough with literal includes | 12-03 | Met (`make example-08` / `make examples`) |
| No-Hardcoding / single-writer / live-never-in-CI | All three threat models + acceptance greps | Met |

**No dependency-order issues:** Wave 1 → 2 → 3 is correct; 12-02 correctly blocked on generator pins; 12-03 correctly blocked on green `run.py`.

**Scope creep:** Contained. Deferred items (`ccf demo` CLI, opt-in live CI job) stayed deferred. Discretion items (counts, ring size, slug `08-e2e-demo`) used appropriately.

**Performance:** ~1.2k population at low end of D-04; generator tests ~0.8s — plans got CI budget right. Full `make examples` remains the long pole (pre-existing).

**Security:** Synthetic-only PII posture is sound. Real gaps are interpreter hygiene (SQL idents, checksum encoding) and opt-in `--live` raw model print (IN-04) — acceptably local, still worth stripping controls.

---

## Priority Follow-Up Backlog (post-phase)

1. **HIGH (latent):** Unconditional verification helper instead of load-bearing `assert` in `run.py`
2. **MEDIUM:** Harden cycle detection (`_extends`, recursion/path cap) + unit tests
3. **MEDIUM:** Escape SQL identifiers + unambiguous checksum encoding in `generator.py`
4. **MEDIUM:** Section-scoped walkthrough includes for pedagogy / Phase 14 page weight
5. **LOW:** REQUIREMENTS.md DEMO status; CI job name “nine examples”; duplicate import; document cycle dedupe semantics

---

## Final Risk Call

**Overall plan quality: strong. Overall residual risk: MEDIUM.**

Plans were high quality for a demonstration phase: decisions mapped to tasks, invariants were explicit, waves were correct, and DEMO-01..03 are delivered. The material follow-up risk is not “demo missing,” but **teaching-surface robustness** — the plans (and docs) invite users to re-author `scenario.yaml` and reuse the interpreter/detection path, while underspecifying encoding, recursion, amount edge cases, and `-O`-safe verification. Address those before leaning on this example as the primary “how to build your own demo” template in Phase 14.

---

## Ollama Review (gpt-oss:120b)

# Review of Phase 12 – Synthetic‑Data Demonstration Plans  

**Overall assessment:**  
The three‑wave plan set (12‑01, 12‑02, 12‑03) is thorough, well‑structured and directly aligned with the success criteria (DEMO‑01 .. 03).  The authors have codified the “no‑hard‑coding” discipline, deterministic‑generation pattern, CI‑first wiring, and the required narrated walkthrough.  Most deliverables are sized appropriately for CI (≈1 k–5 k rows) and the dependency graph (wave 2 → wave 1, wave 3 → wave 2) is explicit.  The documentation of key links, threat‑model entries and verification commands shows a mature process.  A few gaps remain—mainly around error handling, checksum‑drift protection, CI‑time budgeting, and the robustness of the “baseline contrast” implementation.  Addressing these will tighten the delivery and reduce post‑mortem risk.

---

## 1️⃣  Strengths  

| Area | Positive points |
|------|-----------------|
| **Deterministic data generation** | Re‑use of the `perf/synth` seed+checksum discipline (fixed seed, explicit checksum assertions) is explicitly captured in both generator code and test `test_demo_generator.py`. |
| **No‑Hardcoding compliance** | All domain values live in `scenario.yaml`; generator is a pure interpreter; grep‑based checks are built into acceptance criteria. |
| **CI‑first wiring** | `make example-08` target added, aggregated into `make examples`; no new CI workflow files needed.  Expected‑output byte‑compare for both the demo run and the generator test mirrors the existing examples discipline. |
| **Clear artifact catalog** | Each plan lists every artifact (ontology, controlplane, skills, expected output, README, walkthrough) and ties them to the required truth statements. |
| **Risk modeling** | STRIDE table for each wave, with concrete mitigations (parameterized SQL, single‑writer ingest only). |
| **Narrated walkthrough** | Uses `pymdownx.snippets` literal includes, ensuring the doc stays in sync with code/artifacts and can be mounted unchanged for Phase 14. |
| **Baseline contrast** | The design explicitly runs the same cycle‑detection skill on raw rows first, then on governed context—a concrete proof that the problem is “unreachable from raw data”. |
| **Optional `--live` flag** | Live LLM narration is isolated behind a flag; imports are deferred, keeping deterministic CI runs free of external dependencies. |
| **Verification scaffolding** | Automated commands for each task (generator test, run.py execution, Makefile target, doc‑include sanity) are baked into the plans. |
| **Traceability** | `key_links` tables and `must_haves → truths` map requirements → artifacts → tests, making impact analysis trivial. |

---

## 2️⃣  Concerns  

| # | Concern | Severity | Why it matters |
|---|----------|----------|----------------|
| **C‑01 – Checksum drift on scenario changes** | **MEDIUM** | The `expected` block in `scenario.yaml` is populated after the first successful generation. If a developer later edits the scenario (e.g., adds an entity) but forgets to regenerate and commit new checksums, CI will silently accept a mismatched data store or, worse, fail with a cryptic checksum error. |
| **C‑02 – Lack of generator error handling** | **MEDIUM** | `generator.py` assumes the YAML schema is valid and that SQLite writes succeed. If the schema is malformed (missing a source or a required field), the generator will raise a raw exception, aborting the whole demo and obscuring the root cause. |
| **C‑03 – Baseline contrast implementation tight‑coupling** | **MEDIUM** | The baseline run re‑uses the same cycle‑detection callable but feeds it raw rows directly. If future changes to the skill signature (e.g., additional arguments) occur, the baseline code may diverge silently, breaking the “executed not asserted” guarantee. |
| **C‑04 – CI time budget** | **LOW** | Generating three SQLite DBs with ~5 k rows, ingesting, projecting, and replay serving adds non‑trivial work. While still “CI‑fast”, the exact runtime has not been quantified; on a heavily loaded CI runner it could exceed typical timeout limits (often ~10 min). |
| **C‑05 – Potential hidden hard‑coding** | **LOW** | Acceptance criteria rely on `grep` for a *sample* alias. A developer could inadvertently hard‑code other identifiers in `generator.py` or `run.py` and not be caught. |
| **C‑06 – Documentation path fragility** | **LOW** | The walkthrough uses repo‑root‑relative `--8<--` snippets. If the example directory is renamed or moved (e.g., to `examples/09-…`), the includes will break without detection unless the doc is regenerated. |
| **C‑07 – Security of SQLite file handling** | **LOW** | Files are written to a temporary directory but the path is not explicitly sandboxed; a malicious contributor could point `scenario.yaml` at an absolute path (via `out_dir` manipulation) and cause writes outside the repo. |
| **C‑08 – Over‑engineering of `--live` flag** | **LOW** | While optional, the flag introduces a second execution path that is not exercised in CI; future maintenance may diverge (e.g., adding default LLM imports) and breach the deterministic guarantee. |

---

## 3️⃣  Suggestions  

| Ref | Recommendation |
|-----|----------------|
| **S‑01 (C‑01)** | Add a **regeneration helper script** (e.g., `scripts/update_demo_checksums.py`) that runs the generator, recomputes all hashes, and **fails** if the `expected` block is already present but differs. Include it as a pre‑commit hook or CI step that only runs on PRs touching `scenario.yaml`. |
| **S‑02 (C‑02)** | Implement **schema validation** using `jsonschema` (or a handcrafted validator) at the start of `generator.py`. Raise a clear `ScenarioValidationError` with line numbers. Add a corresponding unit test for malformed scenarios. |
| **S‑03 (C‑03)** | Extract the **cycle‑detection logic** into a shared callable (`src/ccf/skills/detect_cycle.py`) that both the baseline and governed runs import. Write a small wrapper test that asserts both entry points produce the expected counts. |
| **S‑04 (C‑04)** | Benchmark the full demo locally (`time make example-08`) and record the runtime in the plan. If > 2 min, consider **down‑sampling** the noise (e.g., 800–1 200 entities) or parallelising SQLite inserts with `executemany`. Document the chosen CI timeout in `12-VALIDATION.md`. |
| **S‑05 (C‑05)** | Enhance acceptance criteria: run a **search for any literal string** that matches a regex of the identifiers list (e.g., `grep -E "ACC[0-9]{6}" -R examples/08-e2e-demo`). |
| **S‑06 (C‑06)** | In `docs/demo-walkthrough.md` add a **front‑matter comment** that records the current example slug and a reminder to update the includes if the slug changes. Optionally write a CI lint that parses the markdown for dangling include paths. |
| **S‑07 (C‑07)** | Ensure `generator.py` constructs all output paths **relative** to a sandboxed temp directory (`tempfile.TemporaryDirectory`) and explicitly **disallows** absolute paths in the scenario definition (validation rule). |
| **S‑08 (C‑08)** | Add a **unit test** that imports `run.py` with `--live` flag and asserts that no LLM client objects are instantiated unless the flag is set. This prevents accidental import leakage in future refactors. |
| **S‑09** | Document **failure‑mode expectations** in the walkthrough (e.g., “if the checksum test fails, run `scripts/update_demo_checksums.py`”). This aids downstream users who may encounter drift. |
| **S‑10** | Add a **metadata file** (e.g., `examples/08-e2e-demo/artifacts/metadata.json`) that records the generator version, seed, and artifact schema version. This bolsters traceability across releases. |

---

## 4️⃣  Risk Assessment  

**Overall risk level:** **MEDIUM**

**Justification:**  

*The core objectives (DEMO‑01 .. 03) are well‑covered and the deterministic approach greatly reduces the chance of flaky CI. The primary residual risk stems from *checksum drift* and *insufficient validation* of the scenario artifact, which could cause silent divergence between the documented expectations and the generated store. While these issues are not catastrophic, they can lead to post‑release defects that violate the top‑priority success criterion (white‑paper fidelity). The suggested mitigation (auto‑checksum regeneration guard and schema validation) would lower the risk to **LOW**.*

--- 

### Next Steps  

1. Implement the regeneration guard (S‑01) and schema validation (S‑02) **before** merging the PR.  
2. Add the shared cycle‑detection module (S‑03) to guarantee baseline/ governed parity.  
3. Run a local benchmark and set CI timeout limits (S‑04).  
4. Update the acceptance criteria and CI lint scripts to incorporate the additional checks (S‑05 – S‑08).  

Once these actions are completed, the Phase 12 deliverables should be solid, reproducible, and fully aligned with the overarching CCF SDK fidelity goals.

---

## Consensus Summary

Reviewed as-built (phase already executed). Risk calls: Gemini LOW, Codex MEDIUM, Cursor MEDIUM, Ollama MEDIUM.

### Agreed Strengths
- **Executed baseline contrast** (raw rows: 0 cycles vs governed context: planted ring) called out by all four reviewers as the strongest design choice — the phase's claim is proved, not asserted.
- **No-Hardcoding discipline** — all vocabulary/thresholds in artifacts; generator and run.py as pure interpreters (all four).
- **Determinism posture** — seed + logical checksums + byte-compared narration wired into CI (all four).
- **Correct wave ordering and minimal CI wiring** — reuse of `make examples`, no new workflow infrastructure (Codex, Cursor, Ollama).

### Agreed Concerns (2+ reviewers — highest priority)
1. **SQL identifier quoting/validation incomplete** (Codex HIGH, Cursor MEDIUM; matches code-review WR-03) — artifact-supplied table/column names are f-string quoted without escaping embedded quotes; docs invite user-authored scenarios.
2. **Cycle-detection edge cases** (Codex, Cursor; matches WR-02/WR-04) — zero/negative amounts in `_extends`, unbounded `_walk` recursion; needs a unit-test module.
3. **run.py monolith / bare-assert verification** (Cursor HIGH-latent, Codex HIGH scope concern; matches WR-01) — all load-bearing checks are `assert`, stripped under `python -O` while README claims exit-0 == verified.
4. **Checksum-pin lifecycle / encoding** (Codex, Cursor, Ollama; matches WR-05) — `|`-joined `str()` rows are collision-prone; no documented regeneration workflow for pin drift.
5. **Scenario schema validation missing** (Codex, Ollama) — no bounds/identifier/path validation before interpretation; malformed scenarios yield raw exceptions.
6. **Docs snippet fragility under Phase 14 mkdocs config** (Gemini MEDIUM, Codex MEDIUM, Cursor MEDIUM) — includes verified to resolve as paths, but not rendered under real pymdownx config; full-file includes weaken step-by-step pedagogy.

### Divergent Views
- **Overall risk**: Gemini rates LOW (invariants + automated verification sufficient); the other three rate MEDIUM, centered on reuse-surface robustness rather than delivery.
- **Cycle-detection placement**: Ollama suggests promoting it into `/src` as a shared skill module; Cursor explicitly keeps it example-local (`examples/08-e2e-demo/cycle_detect.py`) — the latter aligns with the SDK's mechanism-vs-example boundary.
- **Bookkeeping**: only Cursor flags REQUIREMENTS.md DEMO rows still Pending and the stale "eight examples" ci.yml label.
