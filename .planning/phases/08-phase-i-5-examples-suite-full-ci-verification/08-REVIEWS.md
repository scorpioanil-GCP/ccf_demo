---
phase: 8
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-07-30T22:33:18-07:00
plans_reviewed: [08-01-PLAN.md, 08-02-PLAN.md, 08-03-PLAN.md, 08-04-PLAN.md, 08-05-PLAN.md, 08-06-PLAN.md, 08-07-PLAN.md, 08-08-PLAN.md, 08-09-PLAN.md, 08-10-PLAN.md, 08-11-PLAN.md, 08-12-PLAN.md, 08-13-PLAN.md]
---

# Cross-AI Plan Review — Phase 8

## Gemini Review

This review covers the 13 implementation plans for **Phase 8: Phase I.5 — Examples Suite & Full CI Verification**.

### 1. Summary
The Phase I.5 plan set is an exceptionally well-structured conclusion to the SDK implementation lifecycle. It successfully bridges the gap between a proven library/runtime and a demonstrable product by transforming the "adoption contract" into a suite of asserted programs. The sequencing is highly disciplined, clearing inherited hardening obligations (D-14, D-15, D-16, A3) in Wave 2 before constructing the examples that must demonstrate those hardened paths. By leveraging proven patterns from the conformance and cross-process test suites, the plans ensure that the examples are robust, reproducible, and strictly compliant with the No-Hardcoding Rule. The introduction of a dual-track CI (deterministic always-on + opt-in live legs) and a comprehensive Makefile provides the production-grade verification surface required for the Phase I gate.

### 2. Strengths
*   **Inherited Hardening Priority (Wave 2):** Ensuring that D-14/15/16 and R1 land first allows Examples 05 and 06 to demonstrate the "hardened" HITL surface (auth-bound, derived principals, signed-binding requiredness) as a core capability rather than a regression risk.
*   **Example-as-Test Discipline:** Each `run.py` is designed to end in explicit assertions and exit nonzero on failure. This enables the Makefile and CI to treat the entire example suite as a first-class verification leg without needing separate test wrappers.
*   **A3 Advisory Discharge (Plan 08-10):** Successfully incorporates the discharge of advisory A3 (driving real SDK messages through the Claude adapter's seam-4) into the portability proof, closing a long-standing deferred item.
*   **Structural equivalence for Live Legs (Plan 08-11):** Correctly identifies that live LLM outputs cannot be byte-asserted and instead implements the D-04 structural assertions (checking for the five dimensions and correct lineage identity).
*   **Domain Mix (D-IMPL-52):** The plans effectively distribute seven distinct domains (banking, field-service, clinical-trials, e-commerce, property-intelligence, energy, and logistics) to satisfy the horizontal-mix requirement while strictly prohibiting Homecams code reuse.
*   **Lint Posture Integrity (Plan 08-01):** Explicitly locks the lint posture (CINV-01 in for examples, CINV-02 out for example 03) via a behavioral test, preventing silent enforcement gaps.

### 3. Concerns
*   **Push Authorization for CI (MEDIUM):** As noted in RESEARCH Open Question 1, the Actions pipeline cannot be fully verified without authorization to push to `origin`. While the plan correctly uses local `make ci` as interim evidence, the Phase I success criterion for "running in CI" remains blocked by this environmental constraint until the Task 13 checkpoint.
*   **ADK Migration Uncertainty (LOW):** There is a known possibility that ADK 2.5.0 does not yet offer a usable replacement for `SequentialAgent`. Plan 08-04 handles this honestly with the "suppression + recorded rationale" fallback, but it remains a minor technical debt risk for the ADK leg.
*   **Live-Leg Runner Performance (LOW):** Running Ollama with even a small model on CPU-only GitHub-hosted runners will be slow. Plan 08-12's decision to make this `workflow_dispatch` and promote local execution as the primary path is an appropriate mitigation.

### 4. Suggestions
*   **Makefile Ergonomics:** Add a `.DEFAULT_GOAL := help` and a `help` target to the Makefile in Plan 08-01 that uses `grep` or a simple awk script to list and describe the `example-NN` targets. This significantly improves the "Adoptability" of the SDK for first-time users.
*   **Example 06 Mutation Evidence:** In Plan 08-08 Task 2, explicitly suggest mutating a field in the *replay record* (e.g., the policy-bundle version string) as the negative test. This vividly demonstrates version-sensitivity for audit reproduction.
*   **Token Table Artifacts:** For Examples 05 and 06, ensure the `token-table` artifact includes at least one "expired" or "revoked" token entry so the `run.py` can demonstrate a 401 refusal path without hardcoding a bad token string.

### 5. Risk Assessment
**Overall Risk: LOW**

The implementation risk for this phase is low because the vast majority of the logic is already proven by the 1315-test baseline. The genuinely new code (Ollama client, signed-binding requiredness) is surgical and follows established Protocol patterns. The primary risks are environmental (Actions push authorization) and documentation-related, both of which are correctly identified and gated in the final Phase I gate protocol (Plan 08-13).

**Verdict:** The plan set is ready for execution. No re-ordering or further research is required.

---

## Codex Review

## Summary

The plan set is strong and unusually complete: it ties Phase 8 work directly to EXAM-01..09, carries forward the named Phase 7 obligations, keeps examples artifact-driven, and preserves the phase gate ordering. The main risks are not missing intent; they are execution risks: a few dependency edges are under-specified, D-16 may be larger than the plan assumes, and example 03 live legs could become the hardest technical unknown because “three harnesses × Ollama/Anthropic” may not be uniformly supported by the pinned harness SDKs without extra provider packages.

## Strengths

- Clear phase decomposition: scaffold, hardening, examples, live legs, CI, gate.
- Good fidelity to Dave decisions: D-14 through D-17 are explicitly carried.
- Strong No-Hardcoding posture: examples are consistently artifact-first.
- CI/local parity is well-designed through `Makefile` targets.
- Security-sensitive examples 05/06 correctly require auth-bound HITL, signed bindings, typed refusals, and replay evidence.
- The plan treats examples as asserted programs, which is appropriate for EXAM-09.
- Gate ordering is correct: review, Dave approval, D-GATE-I, merge, tag.

## Concerns

- **HIGH — 08-11 live harness portability may be technically overcommitted.**  
  Requiring all three harnesses to run live against Ollama and Anthropic may not be possible with the pinned SDKs without adding `litellm`, provider-specific adapters, or bypassing native harness model paths. The plan says to stop if packages are needed, but EXAM-04 completion depends on this.

- **HIGH — 08-03 D-16 may be broader than “transport seam” work.**  
  Adding `signed_binding` to `HitlActionSubmission`, enforcing Control Plane policy, and including bindings in audit/replay can ripple into HTTP routes, MCP doors, workflow resume logic, serializers, replay records, and examples 05/06. The plan’s files list may be too narrow.

- **HIGH — 08-03 should depend on 08-02.**  
  It references typed HTTP error constants “if that plan has merged,” while examples 05/06 depend on both. Since Wave 2 has parallel hardening plans, this creates ambiguity. Make `08-03` depend on `08-02`, or split transport exceptions from HTTP mapping explicitly.

- **MEDIUM — `make ci` target timing is awkward.**  
  08-01 defines `ci = lint + typecheck + test + examples` before examples exist. That is acceptable if nobody runs it until 08-12, but later plans mention `make ci` or full sweeps. Add a temporary `ci-core` target or document that `make ci` is not valid until 08-12.

- **MEDIUM — 08-07 and 08-09 subprocess examples risk flakiness.**  
  READY handshakes are good, but the plans should require stderr capture, timeout diagnostics, child process cleanup on assertion failure, and port collision handling. Otherwise CI failures will be hard to debug.

- **MEDIUM — 08-08 example 06 is very large.**  
  It combines replay exactness, HITL auth, signed binding, skill-set capture, workflow approval, negative `@latest`, and policy mutation checks. This is valuable, but high blast radius for one plan. It may need an intermediate reusable replay fixture/helper inside the example directory.

- **MEDIUM — lint tests may be brittle.**  
  08-01 proposes asserting internals like `LINTED_TREES` and synthetic prompt-shaped strings. If the lint implementation changes, tests may lock implementation details rather than behavior. Prefer black-box CLI tests with temp trees where feasible.

- **MEDIUM — 08-04 ADK migration depends on current ADK internals.**  
  The fallback suppression is pragmatic, but acceptance should require the suppression is narrowly scoped and covered by a `-W error` test. The plan says this, which is good, but the risk remains.

- **LOW — repeated domain authoring has scope creep risk.**  
  Every example authors fresh ontology/events/controlplane/policy/prompt artifacts. This preserves fidelity, but could consume disproportionate time. Keep artifacts intentionally minimal.

- **LOW — README citation burden may slow delivery.**  
  The citation requirements are correct, but the plans should avoid hand-writing too much explanatory material that can drift from actual code.

## Suggestions

- Add explicit dependency: `08-03 depends_on: [08-01, 08-02]`.
- Add a small preflight spike before 08-11 to verify each harness’s live model seam with pinned versions, especially Claude Agent SDK + Ollama.
- In 08-03, expand expected touched surfaces to include HTTP/MCP/workflow/replay paths if signed binding enforcement reaches them.
- Add `ci-core` in 08-01 and reserve `make ci` full semantics for 08-12, or clearly mark `make ci` as intentionally red until all examples land.
- Require every subprocess example to log child stderr/stdout on failure and kill process groups in `finally`.
- For 08-08, consider splitting example 06 into record/replay helper functions with explicit artifact resolution checks, while keeping all helpers inside `examples/06-decision-replay`.
- Add a final automated “README contract” check in 08-12 or 08-13: every example README contains command, whitepaper citation, CLAUDE.md citation, and domain rationale.
- Add a machine check that every example has code plus artifacts side by side and fails when `artifacts/` is absent.

## Risk Assessment

**Overall risk: MEDIUM-HIGH.**  
The plan quality is high and the phase goals are well covered, but execution risk is substantial because the phase combines hardening changes, eight asserted examples, cross-process processes, live provider integrations, CI wiring, and the v0 gate. The highest-risk items are D-16 signed-binding composition and example 03 live legs. If those are spiked early and dependency ordering is tightened, the plan becomes much more manageable.

---

## Cursor Review

# Cross-AI Plan Review — Phase 8 (I.5 Examples Suite & Full CI Verification)

## 1. Summary

The 13-plan set is a strong, gate-aligned package for Phase I.5: hardening (D-14–D-16) before HITL examples, D-IMPL-52 domain mix locked correctly, Makefile/CI as the single command surface, and a §3.1-ordered v0 gate with a human checkpoint before merge/tag. Plans are concrete (read_first, acceptance greps, STRIDE registers, TDD where mechanism changes). The phase goals (EXAM-01..09, carried obligations, A3, CI, `D-GATE-I`) are covered end-to-end. Residual risk concentrates in three places: (1) D-16 composition stopping at the transport seam while example 05 asserts HTTP `error_code` refusals without a plan that maps transport exceptions at the door; (2) Wave 3 packing six example plans in parallel with soft convention dependence on `00`; (3) example 03 live legs (Claude↔Ollama seam, zero-new-deps gate, structural-only assertions). Overall the plans achieve the phase if those gaps are closed before execution.

## 2. Strengths

- **Wave discipline matches CONTEXT:** Wave 1 scaffold → Wave 2 hardening → Wave 3 examples → Wave 4 live 03 → Wave 5 CI → Wave 6 gate. HITL examples correctly `depends_on: [08-02, 08-03]`; ADK-sensitive example 03 correctly `depends_on: [08-04]`.
- **No-Hardcoding / lint posture first (08-01):** Pinning CINV-01 over `examples/` and scoping CINV-02 off example harness imports before any example code is the right sequencing; Pitfall 1 is real given current `harness_imports` deny-everywhere-outside-adapters behavior.
- **Examples as asserted programs:** Artifact-deletion checks, negative admission/auth cases, `@latest` refusal, byte-equal replay, single-workload store swap — matches §9 discipline, not demos.
- **Domain rails honored:** ≥4 domains; banking@00 + property-intelligence@04 locked; 05 banking non-adjacent to 00; 07 logistics non-adjacent to 01; D-07 zero-Homecams-porting enforced with grep acceptance.
- **D-14 absorption into 05 *and* 06 (08-08):** Live auth-bound door + replay of principal/binding is stronger than “test-only hardening” and matches the named I.4.1 obligation.
- **Harness proof design (08-10/11):** Deterministic three-harness byte-equality + A3 discharge; live structural (D-04); httpx-only Ollama client; stop-and-audit if a new package appears unavoidable.
- **CI/local identity (08-12):** `make examples` in always-on CI, no `continue-on-error`, opt-in live-legs workflow, local `make ci` as interim evidence without unauthorized push.
- **Gate ordering (08-13):** `autonomous: false`, human checkpoint before `D-GATE-I` → merge `--no-ff` → tag on main — Pitfall 6 respected.
- **Threat models are phase-appropriate:** Fail-closed TokenGrant, signed-binding repudiation, A2A admission, CI secrets, single-writer across store/adapter boundaries.

## 3. Concerns

### HIGH

- **D-16 door/error-code composition gap (08-03 ↔ 08-08):** 08-03 explicitly does *not* touch HTTP/MCP doors and treats typed transport exceptions as sufficient. 08-08 acceptance requires unsigned submissions refused against an **error-code constant from 08-02**. Today `routes/hitl.py` returns prose `detail=` strings with no `error_code` field, and nothing in 08-02/03 maps a new signed-binding refusal exception into that payload. Example 05 will either invent client-side exception catching (weak demo) or fail until door wiring is added mid-example — unplanned scope.
- **Claude live-Ollama seam is unresolved at plan time (08-11):** D-03 requires Ollama as default live provider for *all three* harnesses. The plan correctly anticipates that `claude-agent-sdk` may not target Ollama and allows routing via the CCF LLM seam — but that resolution is deferred to execution. If the fallback collapses “real harness loop” for Claude, EXAM-04/D-02 live completeness is at risk; if it needs a new package, the package gate stops the plan. This is the phase’s largest unknowns cluster.

### MEDIUM

- **`make ci` includes `examples` from Wave 1:** Until 08-05..11 land, `make ci` is red by design. Easy footgun for executors and for 08-04/02 verifies that say “full suite + make lint” but not `make ci`. Drift risk between “green enough to proceed” and the final gate command.
- **Wave 3 parallel authoring without hard depends on 08-05:** 08-06/07/09 soft-reference `00` conventions (“if merged”). Six plans can diverge on driver shape, assertion style, README skeleton, and artifact versioning — expensive to normalize in 08-12.
- **08-08 density:** Two of the hardest examples (auth-bound workflow+HITL + exact-version replay with HITL-in-record) in one plan. High blast radius if D-16 door wiring or replay APIs need fixes; little room to land half-green.
- **CINV-01 vs LLM stubs / canned strings (08-06, possibly 08-10):** Scripted `LLMClientProtocol` stubs “returning canned analysis” in `run.py` can look prompt-shaped to No-Hardcoding lint. Plans assert lint green but don’t prescribe how canned outputs live (artifact refs vs mechanism-only tokens).
- **CINV-02 vs Anthropic live path (08-11):** Vendor `anthropic` is denied outside `ccf.llm` / `ccf_runtime.llm`. Native Anthropic harness paths must not import `anthropic` from `examples/`; only harness internals or the LLM adapter path are safe. Plan greps keys/URLs but not this import rule.
- **MCP HITL door left out of D-16/R1 story:** Fail-closed + was-called + signed-binding are HTTP-centric in plans; Phase 7 also hardened MCP `submit_hitl_action`. Examples use HTTP (OK for demo), but parity gaps can remain at the gate if review scopes “hardened HITL surface” broadly.
- **Phase I criterion 5 verification is back-loaded:** Composition-preservation for every shipped operator pair and whitepaper-fidelity spot check appear mainly as 08-13 gate checklist items. If either is stale/red, discovery is at the last wave with maximum merge pressure.
- **Subprocess examples (04, 07) in CI:** READY-handshake is the right pattern; GitHub-hosted runners + uvicorn + dual ports still flake without hard timeouts, teardown-on-failure, and job-level time budgets called out in 08-12 (only child smoke verifies use `timeout 60`).

### LOW

- **EXAM-09 text still says “one coherent neutral domain”** in the requirements block while plans correctly follow D-IMPL-52. Documentation drift only; gate note already exists in ROADMAP.
- **01 “field-service/logistics” vs 07 “logistics”:** Domain-family reuse is allowed and non-adjacent; READMEs should state they are the same family under D-06 to avoid a D-06 nit at review.
- **Version bump before Dave approval (08-13 Task 1):** `0.1.0` on the branch before Task 3 is fine if rejection reverts; slightly at odds with “v0 declaration = tag after approval” optics — tag ordering is correct, package version is early.
- **ADK `SequentialAgent` suppression path (08-04):** Honest fallback, but a scoped `filterwarnings` can hide unrelated ADK deprecations if the filter is too broad; acceptance uses `-W error::DeprecationWarning` which helps.
- **Editable-install / `.venv` in Makefile:** Hard-coding `.venv/bin/python` is fine for this repo; CI jobs use system Python after `pip install -e`. 08-12 must keep Makefile vs Actions command strings identical *after* interpreter differences — risk of “same target, different python” drift.

## 4. Suggestions

- **Add an explicit door-mapping task (extend 08-03 or insert a thin 08-03b):** When transport raises the D-16 typed refusal, HTTP (and preferably MCP) maps to the same `error_code` constants as 08-02; include unsigned/invalid-signature cases in `tests/http_api`. Then 08-08’s acceptance is grounded.
- **Export a signed-binding refusal code in 08-02’s errors module** (or 08-03) up front — e.g. `ERROR_SIGNED_BINDING_REQUIRED` / `ERROR_SIGNED_BINDING_INVALID` — so examples don’t invent strings.
- **Serialize Wave 3 lightly:** Land 08-05 first (or mark `depends_on: [08-01, 08-05]` for 08-06+), or extract a one-page “example driver contract” (exit codes, artifact layout, README sections, assertion helpers) into `08-PATTERNS.md` and require read_first.
- **Split 08-08** into `08-08a` (example 05) and `08-08b` (example 06, depends on 08-08a for auth-binding patterns) to reduce all-or-nothing risk on the D-14 absorption pair.
- **Makefile staging:** Until 08-12, either omit `examples` from `ci`, or provide `ci-core` / `ci` where only the latter includes examples — keep D-10’s final identity without mid-phase red `make ci`.
- **08-11 Claude+Ollama decision table in the plan (not only README):** Three explicit allowed outcomes — (A) native Ollama endpoint, (B) real loop + CCF LLM seam injection, (C) stop for Dave — with a conformance assertion that seam-1..4 still run under (B).
- **Lint-aware stub guidance:** Require deterministic LLM outputs to live in artifacts (or as non-prompt structured fixtures) so CINV-01 stays mechanical; add a grep acceptance that `run.py` has no triple-quoted instruction blocks.
- **08-12 examples job:** Add `timeout-minutes`, ensure harness extras via `.[dev]` (already true), and document child-process cleanup; consider `pytest`-style timeouts only if examples stay Makefile-driven.
- **Pull §3.1 spot checks earlier:** A short Wave 5 task (or 08-12 Task 2 bullet) that runs composition-preservation suite + records ≥5 docstring fidelity samples into the sweep summary, so 08-13 is assembly not discovery.
- **Align MCP fail-closed/R1** with HTTP in 08-02/03 if the gate’s “hardened HITL surface” language is door-agnostic — even if examples only exercise HTTP.

## 5. Risk Assessment

**Overall: MEDIUM**

Justification: Scope and sequencing are sound; EXAM coverage is complete; hardening-before-demo and gate protocol are correctly designed; CI/harness install path is already proven in the existing workflow (`CCF_REQUIRE_HARNESSES` + `[dev]`). The rating is not LOW because D-16’s demonstration path has a missing door/error_code wire, Wave 3 concurrency + 08-08 density can create late integration churn, and example 03’s live matrix still depends on an unresolved Claude↔Ollama integration choice under a hard zero-new-deps constraint. None of these are phase-goal killers if fixed in-plan before Wave 3 HITL/live work; left unaddressed they become HIGH at 08-08/08-11/08-13.

---

### Per-plan quick verdicts

| Plan | Verdict | Note |
|------|---------|------|
| **08-01** | Strong | Scaffold + lint posture correctly first; soften `ci→examples` coupling until suite exists. |
| **08-02** | Strong | D-15 + fail-closed + error codes; ensure MCP parity considered; tree-wide `decide` grep is good. |
| **08-03** | Needs door follow-through | Transport-only D-16 underserves 08-08 HTTP assertions; R1 was-called is well-scoped. |
| **08-04** | Strong | Migrate-or-suppress honesty + doc obligations; conformance 25/25 as behavior gate. |
| **08-05** | Strong | Correct EXAM-01 / banking / fresh artifacts; good template candidate for other examples. |
| **08-06** | Strong | Dual-channel story clear; watch CINV-01 on stubs; prefer hard depend on 08-05. |
| **08-07** | Strong | Cross-process + admission negative case; Homecams ban enforceable; CI flake hygiene needed later. |
| **08-08** | Highest example risk | Correct obligation absorption; split recommended; blocked on D-16 door mapping. |
| **08-09** | Strong | Config-only swap + single workload function is the right §7.4 proof. |
| **08-10** | Strong | Three-harness deterministic + A3 discharge; mission-critical and well-anchored to conformance. |
| **08-11** | Highest integration risk | Live matrix + zero deps; pre-decide Claude/Ollama seam; watch `anthropic` import lint. |
| **08-12** | Strong | D-10/D-11 shape correct; don’t push; harden timeouts; run fidelity/composition in sweep. |
| **08-13** | Strong | §3.1 sequence + human gate correct; packaging matches D-17; keep tag post-approval. |

---

## Ollama Review (gpt-oss:120b-cloud)

## Phase 8 (I.5) – Examples Suite & Full CI Verification  
**Cross‑AI Review – Summary, Strengths, Concerns & Recommendations**

---

### 1. Summary  
The eight‑plan set provides a concrete, step‑by‑step roadmap for delivering the final **examples‑suite** and the associated **hardening wave** that unlocks the v0.1.0 release.  The plans are well‑structured, each with clear *objective*, *tasks*, *verification* and *acceptance criteria*.  They collectively cover the required EXAM‑01 → EXAM‑09 deliverables, the removal of the deprecated `ccf hitl decide` verb, the fail‑closed TokenGrant branch, typed error‑code constants, SignedPrincipalBinding requiredness, ADK deprecation handling, lint‑scope adjustments, CI workflow extensions and v0 packaging.  If executed in the prescribed order (01 → 02/03 → 04 → 05‑09 → 10‑13) the work should satisfy the Phase I gate.

However, a few **critical gaps** remain that could cause the gate to fail, introduce regressions, or expose security/performance risks.  These gaps fall into three buckets:

1. **Missing integration & regression checks** (e.g., lint scope for `CINV‑02`, error‑code propagation, Control‑Plane config loading).  
2. **Unclear fallback paths** for optional components (ADK migration, SignedBinding policy, Ollama on GitHub‑hosted runners).  
3. **Operational hygiene** (process cleanup, deterministic‑mode guarantees, documentation consistency).

Below are detailed strengths, concerns and concrete suggestions to close the gaps before the final merge.

---

### 2. Strengths  

| # | What the plan does well |
|---|--------------------------|
| **S1** | **Granular wave decomposition** – hardening (08‑02/03/04) is isolated from example authoring (08‑05‑09) which prevents accidental cross‑contamination. |
| **S2** | **TDD‑first approach** on every hardening item (removing `decide`, fail‑closed branch, signed‑binding matrix, was‑called derivation) – guarantees regression testing before shipping. |
| **S3** | **Clear artifact‑first policy** – each example explicitly creates fresh YAML/Jinja2 artifacts; No‑Hardcoding rule is verified via lint test (08‑01). |
| **S4** | **CI parity via Makefile** – `make ci` mirrors the GitHub Actions pipeline, satisfying D‑10 and providing local evidence when pushes are not yet authorized. |
| **S5** | **Domain‑mix compliance** – D‑IMPL‑52 rails are honoured, with a documented mapping that satisfies the “horizontal mix” requirement. |
| **S6** | **Live‑leg opt‑in design** – the live‑model legs are gated behind a separate workflow (`live‑legs.yml`) and secret checks, respecting D‑11. |
| **S7** | **Documentation hooks** – every example README must cite the white‑paper and CLAUDE sections, and a top‑level README is added at the end (08‑13). |
| **S8** | **Security‑by‑design** – secrets are only read from the environment, no hard‑coded keys, and the new error‑code constants avoid string‑parsing. |
| **S9** | **Phase‑gate procedural compliance** – explicit tasks for `/gsd‑review`, triage, Dave’s approval, D‑GATE‑I logging and ordered tagging (08‑13). |

Overall, the plan set demonstrates a mature engineering process that aligns tightly with the governing artifacts (`CLAUDE.md`, `DECISIONS.md`, `PHASE_I4_GATE.md`).

---

### 3. Concerns  

| # | Issue | Severity | Impact if Unaddressed |
|---|-------|----------|----------------------|
| **C1** | **Lint scope for CINV‑02** – `tools/lints` originally guards `/src` only; the new test (08‑01) only *asserts* that the rule ignores examples, but does not *enforce* the exemption in the linter config. | HIGH | Harness imports in `examples/03` could trigger a lint failure on CI, breaking the pipeline and violating the “zero‑harness‑imports in core” invariant. |
| **C2** | **Error‑code propagation** – Plan 08‑02 adds new constants but does not show wiring to the HTTP response bodies for all HITL routes (e.g., `submit`, `GET /hitl/decision`). | MEDIUM | Refusals may still return generic 400/500 messages, breaking the “typed refusal” test and possibly leaking implementation details. |
| **C3** | **Signed‑binding requiredness policy source** – No artifact/schema is described for the Control‑Plane flag `hitl.signed_binding_required`. The test harness (08‑03) reads the flag but the runtime may raise a `KeyError` if the flag is missing. | HIGH | Example 05/06 could abort with an uncaught exception, causing CI failures and violating D‑16. |
| **C4** | **ADK SequentialAgent migration** – The plan leaves the decision to “migrate if a usable API exists, else suppress”. No concrete decision is recorded, so the final state is ambiguous. | MEDIUM | If the suppression path is taken, the deprecation warning will still appear in downstream builds (or be missed), causing drift from the white‑paper contract. |
| **C5** | **Ollama on GitHub‑hosted runners** – The live‑leg workflow assumes a “small model” can be pulled, but no size limit or timeout is enforced. Also the local‑run default (`gpt‑oss:120b-cloud`) is cloud‑relayed, which violates the “key‑less local model” design. | MEDIUM | The `live‑ollama` job may OOM or time out, causing a flaky CI job and delaying releases. |
| **C6** | **Cross‑process example (04) cleanup** – The plan spawns a child process but does not describe a robust termination strategy (e.g., handling SIGTERM, ensuring child is killed on test failure). | MEDIUM | Zombie processes may linger on CI runners, consuming resources and causing nondeterministic failures. |
| **C7** | **MCP store child in example 07** – No health‑check or retry logic before the parent attempts to connect. If the child fails to start, the parent will raise a connection error that masks the intended assertion. | LOW | Example 07 could fail for unrelated startup issues, obscuring the pluggability test. |
| **C8** | **Version bump & tag ordering** – The plan mentions “push only after Dave authorises” but does not embed a guard in the CI workflow to prevent accidental pushes from local developers. | LOW | Accidental early push could break the “no‑force‑push” invariant and expose unfinished examples. |
| **C9** | **Replay‑exact‑version test (example 06)** – The plan asserts that `@latest` is never used, but does not create a negative test that deliberately passes an `@latest` string and expects a refusal. | MEDIUM | Without the negative test, a subtle regression could re‑introduce `@latest` handling without detection. |
| **C10** | **Documentation drift** – Multiple README templates are created in parallel; there is no single source of truth for the “example‑suite table” in the top‑level README. | LOW | The top‑level README could become out‑of‑sync with the actual example commands, confusing users. |

---

### 4. Suggestions  

| # | Recommendation |
|---|----------------|
| **SUG1** | **Lock lint exemption** – In `tools/lints/__main__.py` (or its config file) explicitly add `examples/**` to the `CINV‑02` ignore list and update the test in 08‑01 to import the linter and assert the path is excluded. This guarantees CI compliance. |
| **SUG2** | **Wire error‑code constants** – Extend `runtime/ccf_runtime/http_api/routes/hitl.py` (and any other HITL endpoints) to use the new constants from `errors.py` for all refusal branches (`UNAUTHENTICATED`, `SUBJECT_CONFLICT`, `INVALID_GRANT`, `SIGNED_BINDING_REQUIRED`). Add a small helper `error_response(code: str, detail: str)` to centralise the JSON payload. |
| **SUG3** | **Provide Control‑Plane policy artifact** – Add a minimal `hitl_policy.yaml` artifact (under `examples/05` and `06`) that contains `{hitl: {signed_binding_required: true}}`. Update the signed‑binding test to load this artifact via the existing `PolicyStore` rather than hard‑coding a dict. |
| **SUG4** | **Decide ADK migration now** – Run a quick REPL (`python -c "import google.adk; print(google.adk.__version__); help(google.adk.Workflow)"`) to confirm the replacement API (`Workflow` or `AgentGraph`). If the API exists, perform the migration now and record the change in `DECISIONS.md`. If not, add a formal D‑IMPL entry stating “ADK 2.5.0 deprecation not migratable; suppression applied” and document the exact warning filter line. |
| **SUG5** | **Ollama CI job safeguards** – In `live‑legs.yml`, add a step that checks the model file size (`du -sh $model_dir`) before pulling, aborting if > 500 MiB. Also set a timeout (`timeout-minutes: 15`) and provide a fallback to skip the job with a clear “model too large for runner” notice. |
| **SUG6** | **Robust child‑process handling** – In `examples/04/run.py`, use Python’s `subprocess.Popen` with `preexec_fn=os.setsid` and a `finally` block that sends `SIGTERM` to the whole process group. Add a small watchdog thread that kills the child after a hard timeout (e.g., 30 s). |
| **SUG7** | **MCP child health check** – After spawning `mcp_store_child.py`, have the parent poll `http://localhost:{port}/health` with a short retry loop (max 5 attempts, 1 s interval). If the health check fails, raise a clear error and abort the example. |
| **SUG8** | **Prevent accidental pushes** – Add a git hook (`pre‑push`) in the repo that checks for the presence of the `phase‑i5` branch name and aborts unless an env variable `ALLOW_PHASE_PUSH=1` is set. Document the hook in `docs/CONTRIBUTING.md`. |
| **SUG9** | **Negative `@latest` test for replay** – In `examples/06` add a small unit test that attempts to resolve a product using the URI `ccf-artifact://my.graph@latest` and asserts a `ValueError` (or the SDK‑specific exception). This will catch any regression that re‑enables `@latest`. |
| **SUG10** | **Synchronise README tables** – Create a small script `tools/gen_example_table.py` that scans `examples/*/README.md` for the “## Example” header and the documented command, then rewrites the top‑level README table. Run this script as part of the `make lint` target to ensure consistency. |
| **SUG11** | **Add explicit CI step ordering** – In `ci.yml`, make the `examples` job depend on the `test` job (`needs: test`) to guarantee that the full test suite passes before the examples are run. Conversely, keep the `live‑legs` workflow independent. |
| **SUG12** | **Run static code analysis for secret leakage** – Add `detect-secrets` or a similar tool to the lint job to guarantee that no secret (e.g., `ANTHROPIC_API_KEY`) is accidentally committed in examples. |

---

### 5. Risk Assessment  

| Overall Risk | Rationale |
|--------------|-----------|
| **MEDIUM** | The majority of the work is **packaging, demonstration and hardening** – no new core functionality is introduced, which limits systemic risk.  However, **several high‑severity gaps** (C1, C2, C3) could cause the Phase I gate to fail or introduce security regressions.  Addressing the concerns above brings the risk down to **Low**. |

**If all suggestions are implemented**, the phase will meet the white‑paper fidelity, CI invariants, domain‑mix policy, and packaging requirements, enabling a clean v0.1.0 release.  

--- 

**Next steps**:  

1. Prioritise the high‑severity items (C1‑C3) – update lint config, propagate error codes, and provide the signed‑binding policy artifact.  
2. Resolve the ADK migration decision (SUG4) before merging any example that depends on it.  
3. Add the robustness enhancements for child processes (SUG6‑SUG7) and CI safeguards for Ollama (SUG5).  
4. Run the full local sweep (`make ci`) after each wave to confirm parity with GitHub Actions.  
5. Once all automated checks pass, perform the gated review (Task 3 in 08‑13) and obtain Dave’s approval before merging and tagging.  

With these adjustments, the phase should close cleanly and the SDK will be ready for adoptable, general‑purpose use.

---

## Consensus Summary

Risk verdicts: Gemini LOW · Cursor MEDIUM · Ollama MEDIUM · Codex MEDIUM-HIGH.

### Agreed Strengths (2+ reviewers)
- Hardening-before-examples wave ordering (all four): D-14/15/16 + ADK land in Wave 2 so examples 05/06 demonstrate the hardened HITL surface rather than regress it.
- Examples-as-asserted-programs discipline (all four): run.py ends in assertions, exits nonzero, artifact-deletion proves No-Hardcoding; Makefile/CI parity satisfies D-10.
- Domain-mix rails honored (Gemini, Cursor, Ollama): 7 domains within D-06 rails, zero-Homecams-porting enforced with greps.
- Gate ordering correct (all four): review → triage → Dave approval → D-GATE-I → merge → tag; human checkpoint is autonomous:false.
- Live-leg opt-in design and structural (not byte) equivalence for live outputs (Gemini, Cursor, Ollama).

### Agreed Concerns (2+ reviewers — highest priority)
1. **D-16 door/error_code wiring gap (Codex HIGH, Cursor HIGH, Ollama C2/C3 HIGH-MEDIUM).** 08-03 stops at the transport seam, but 08-08's example 05 acceptance asserts an HTTP refusal carrying an error_code constant. Nothing in 08-02/03 maps the signed-binding refusal exception into the HTTP (and MCP) response payload, and no Control-Plane policy artifact schema for signed_binding_required is specified. Fix: extend 08-03 (or a thin 08-03b) to map transport refusals to 08-02's error-code constants at the HTTP door (MCP parity noted), export ERROR_SIGNED_BINDING_* constants, and specify the HITL policy artifact examples 05/06 load.
2. **Example 03 live legs / Claude↔Ollama seam unresolved at plan time (Codex HIGH, Cursor HIGH, Gemini LOW-note, Ollama C5).** The claude-agent-sdk may not target Ollama natively under the zero-new-packages gate. Fix: pre-decide a three-outcome decision table in 08-11 (native endpoint / real loop + CCF LLM seam injection with seam-1..4 conformance assertion / stop for Dave), plus runner-size + timeout safeguards on the live workflow.
3. **make ci red-by-design until 08-12 (Codex MEDIUM, Cursor MEDIUM).** ci target includes examples from Wave 1 before examples exist. Fix: add ci-core (lint+typecheck+test) in 08-01 and reserve full make ci semantics for 08-12.
4. **08-08 density / all-or-nothing risk (Codex MEDIUM, Cursor MEDIUM).** Two hardest examples (05 auth-bound HITL + 06 exact-version replay with HITL-in-record) in one plan. Fix: split into 08-08a/08-08b or extract shared record/replay helpers inside the example dirs.
5. **Subprocess flakiness in examples 04/07 on CI (Codex MEDIUM, Cursor MEDIUM, Ollama C6/C7).** Fix: process-group kill in finally, stderr capture on failure, health-check retry for the MCP child, timeout-minutes on the CI job.
6. **Wave 3 convention drift (Codex suggestion, Cursor MEDIUM).** Six example plans in parallel with only soft reference to 00's conventions. Fix: hard-depend 08-06+ on 08-05, or codify a one-page example-driver contract in PATTERNS.md as required read_first.
7. **CINV lint edge cases (Cursor MEDIUM, Ollama C1 HIGH).** Canned LLM stub outputs may look prompt-shaped to CINV-01; the anthropic import rule (CINV-02) must be respected on the live Anthropic path; the examples-exemption should be enforced in linter config, not only asserted in a test.

### Divergent Views
- Overall risk: Gemini rates LOW (mostly proven mechanism, surgical new code); Codex rates MEDIUM-HIGH driven by D-16 breadth and the live-leg matrix. The spread narrows to LOW if consensus concerns 1–2 are fixed in-plan before execution.
- 08-03 dependency: Codex wants an explicit depends_on 08-02 edge; Cursor treats it as a door-wiring scope problem rather than an ordering problem.
- ADK migration: Gemini accepts the migrate-or-suppress fallback as honest; Ollama wants the decision forced now via API inspection and recorded in DECISIONS.md.

---

# Post-Execution Cross-AI Review — Phase 8 (2026-07-31)

Reviewers: gemini, codex (API-key auth), cursor, ollama (gpt-oss:120b-cloud). Claude skipped (executing runtime). Scope: plan objectives + all 13 execution SUMMARYs + docs/PHASE_I5_GATE.md.

## Gemini Review

# Phase 8 (Phase I.5) — Examples Suite & Full CI Verification: Review Report

## 1. Summary
Phase 8 has been executed with exceptional rigor, successfully delivering the "v0 declaration" of the CCF SDK. The implementation of the eight-example suite (EXAM-01..08) across seven distinct domains provides empirical proof of the SDK's general-purposeness and harness-neutrality. The hardening wave (D-14, D-15, D-16) effectively closes the security and non-repudiation gaps identified in previous reviews, specifically through the introduction of `SignedPrincipalBinding` and fail-closed authentication at the HITL doors. The "Replay-by-Construction" invariant is now demonstrated end-to-end, including complex auth-bound approvals and cross-process A2A federation. While the lack of observed GitHub Actions runs (due to push-authorization constraints) remains a final verification hurdle, the command-identical local sweep (`make ci`) and the comprehensive `PHASE_I5_GATE.md` provide a high-confidence baseline for the v0.1.0 release.

## 2. Strengths
*   **Harness Neutrality Proof:** Example 03's successful execution of a single agent definition under Claude SDK, Google ADK, and LangGraph with byte-level product equivalence (deterministic) and structural equivalence (live) is a premier demonstration of §7.3 architectural claims.
*   **Hardened Security Posture:** The implementation of D-16 (Signed Bindings) and D-15 (HITL verb consolidation) transforms the HITL surface from a functional prototype into a defensible authority path.
*   **Domain Breadth:** Spanning seven domains (Banking, Field Service, Clinical Trials, Property Intelligence, Grid Ops, Logistics, E-commerce) without leaking domain logic into `/src` validates the "mechanism, never domain values" mandate.
*   **Linter Discipline:** Extending CINV-01 (No-Hardcoding) to the `/examples` tree via `RULE_TREE_SCOPE` ensures that the examples themselves remain "specialization artifacts" rather than hardcoded hacks.
*   **Whitepaper Fidelity:** The spot-check evidence in §3 of the Gate Package confirms that public surfaces (λ_c tables, Projection Engine, etc.) are grounded in the canonical specification, with SDK extensions clearly labeled.

## 3. Concerns
*   **CI Visibility Gap (MEDIUM):** Although `make ci` is command-identical to the Actions pipeline, the new `examples` job and `live-legs.yml` remain unverified in the actual GitHub environment. Hidden runner-specific issues (e.g., resource limits during 20-minute subprocess runs) may still surface upon the first push.
*   **Ollama Compatibility Dependency (LOW):** The Claude/Ollama "Outcome A" (native endpoint) depends on Ollama's continued adherence to the Anthropic `/v1/messages` wire format. While currently functional, any drift in Ollama's emulation would break the Claude live-leg example without a CCF code change.
*   **Single-Writer Performance (LOW):** The single-writer enforcement across the ArtifactStore and A2A boundaries is architecturally sound for v0, but the examples do not yet push the limits of WAL-based contention in the "full deployment" (Example 04) scenario.

## 4. Suggestions
*   **Model Fallback Documentation:** In `examples/03-harness-portability/README.md`, add a brief note on how to point the Ollama leg at a different model if `qwen3:0.6b` (the CI default) is unavailable in a user's local environment.
*   **Artifact Store Cleanup:** Consider adding a `make clean-artifacts` target to the root `Makefile` to quickly purge the `.tmp` and `artifacts/` output folders generated by local example runs, preventing accidental cross-contamination or repo bloat.
*   **Release Tagging:** Proceed with the `v0.1.0` tag immediately upon Dave's approval of the `D-GATE-I` entry, as the current state of `main` is the most stable and verified in the project's history.

## 5. Risk Assessment: LOW
The risk is **LOW**. The phase goals have been met with high fidelity to the roadmap and whitepaper. The 1339-test sweep, combined with the successful execution of eight heterogeneous examples and the closure of all standing hardening obligations (D-14..16), indicates that the SDK core is stable and the boundaries are well-defined. The identified concerns are either procedural (CI push) or external (Ollama compatibility) rather than structural defects in the CCF implementation.

**Final Verdict:** The delivered work is sound, complete, and ready for the Phase I Gate.

---

## Codex Review

## Summary

Phase 8 looks substantially delivered against the plan: the eight-example suite exists conceptually end-to-end, invariant linting now covers examples for CINV-01, hardened HITL/auth work was exercised in examples 05/06, example 03 provides a meaningful three-harness portability demonstration, and the gate document is unusually explicit about caveats. I would not call the phase fully gated yet, though: the “full CI verification” claim remains short of observed GitHub Actions evidence, and the signed-binding/HITL workflow composition has a remaining integration smell where the examples treat the HTTP door submission as the authority landing rather than making the workflow gate itself signed-binding-aware.

## Strengths

- Clear phase discipline: every plan has scoped outputs, summaries, verification, deviations, and known-stub accounting.

- Good examples posture: examples are asserted programs with artifacts beside code, not passive demos. That is the right shape for adoptability and CI enforcement.

- CINV-01 over `/examples` is a strong choice. It prevents examples from becoming a hidden hardcoding escape hatch.

- HITL hardening improved materially: `ccf hitl decide` removed, fail-closed grant handling added, typed refusal codes introduced, signed-binding requiredness enforced at the transport path, and HTTP/MCP doors map refusals consistently.

- Example 03 is strong evidence for harness neutrality: deterministic three-harness execution plus live-model legs with structural equivalence is much better than adapter-only unit tests.

- The gate document is honest about important limits: no Actions run yet, local `make ci` is not a perfect mirror of Actions, composition coverage depends on a maintained registry, and post-v0 residuals are named.

## Concerns

- **HIGH — CI verification is not complete until Actions run.**  
  The phase title includes “Full CI Verification,” but the new always-on examples job and `live-legs.yml` have not run in GitHub Actions because the branch has not been pushed. The local sweep is valuable, but it does not cover Actions-only behavior such as service containers, workflow setup, runner timeouts, dependency resolution, cache behavior, and secret-gated live jobs.

- **MEDIUM — Signed-binding workflow composition still appears manual at the example layer.**  
  The 08-08 deviation is significant: `ApprovalGate.resolve` cannot itself land a signed-binding-required submission, so the examples use the verified HTTP door submission as the authority landing and then have the driver build the `HitlActionRecord`. That may be defensible under D-IMPL-62, but it leaves a risk that signed-binding-required HITL is not naturally composable through the workflow gate abstraction itself.

- **MEDIUM — Default unauthenticated HTTP posture remains a v0 security residual.**  
  The examples bind `BearerTokenAuth`, and the auth hook exists, but the default unauthenticated posture is still standing. For an SDK, that can be acceptable if loudly documented, but it is a real footgun for adopters copying runtime setup outside the examples.

- **MEDIUM — Key management is documented but not operationally enforced.**  
  The key-management note and env-only discipline are good, but rotation, trust-store lifecycle, and production key sourcing remain operator responsibilities. That is reasonable for v0, but non-repudiation depends heavily on users implementing those seams correctly.

- **LOW/MEDIUM — Composition-preservation coverage is registry-bound.**  
  The gate correctly narrowed the claim after review, but the risk remains: adding a fifth shipped operator requires someone to update the test registry. This should become a guarded maintenance invariant.

- **LOW — Examples are executable but apparently outside strict typing.**  
  The summaries state mypy checks 156 source files and examples are excluded by design. Runtime execution catches much, but the examples are now a major adoption surface, so untyped drift there could accumulate.

## Suggestions

- Require one observed GitHub Actions run before approving the Phase I gate, or explicitly rename the current state to “CI wiring complete, local verification green.”

- Add a focused test or small core helper proving the intended signed-binding workflow path, so examples 05/06 do not have to hand-compose pending event + door submission + record construction.

- Make the unauthenticated HTTP default impossible to miss in README/runtime docs, preferably with a production warning near `create_app()` usage.

- Add a CI check that every shipped operator category/class is represented in the composition test registry, if the codebase has a reliable source of shipped operators.

- Consider lightweight static checking for examples later, even if not full strict mypy.

## Risk Assessment

**Overall risk: MEDIUM.** The delivered work appears broad, coherent, and mostly complete against the phase plans, with strong local verification and good documentation honesty. The main blocker to a low-risk gate is external CI evidence: until Actions runs successfully, “full CI verification” is not actually proven. The remaining security/design risk is the HITL signed-binding workflow composition gap, which is probably acceptable for v0 if documented, but should be tracked because it sits directly on the non-repudiation story.

---

## Cursor Review

# Cross-AI Phase Review — Phase 8 (I.5, post-execution)

## 1. Summary

Phase 8 delivers what it claims as an adoption-contract phase: eight asserted examples across seven domains, Makefile/`ci.yml` command surfaces, HITL hardening (D-14/15/16), ADK deprecation migration, A3 discharge, and a gate package that is largely honest about scoping and the Actions gap. Spot checks against the tree corroborate the load-bearing claims (no harness imports in `/src`, `decide` gone, signed-binding refusals on HTTP+MCP, `ApprovalGate.resolve` still unsigned, door-as-authority composition in examples 05/06, `RULE_TREE_SCOPE`, version `0.1.0`, README, `D-GATE-I` correctly unwritten). The phase goal is **substantively achieved for Dave’s gate decision**; remaining risk is concentrated in (a) Actions never observed, (b) HITL primitive APIs that cannot satisfy `signed_binding_required` without the example workaround, and (c) EXAM-09 marked “Complete” while only local-sweep evidence exists.

---

## 2. Strengths

- **Plan coverage is complete through 08-12.** All eight `examples/*/run.py` + READMEs exist; hardening plans 08-02..04 land real mechanism; packaging artifacts for 08-13 (README, `0.1.0`, `PHASE_I5_GATE.md`) are staged without prematurely logging `D-GATE-I` or tagging.
- **Examples are asserted programs, not demos.** Expected views in Control Plane artifacts, refusal constants imported (not prose-parsed), artifact-deletion / byte-identity / admission-refusal negatives are the right adoption-contract shape for CLAUDE.md §9 / §6.4.
- **Horizontal domain mix is real.** Banking, field-service, clinical-trials, e-commerce, property-intelligence, grid-ops, logistics — exceeds the ≥4-domain bar; Homecams zero-porting posture is documented without pulling Homecams code into artifacts.
- **HITL hardening is mechanism-grade.** Shared `ERROR_*` constants, fail-closed `isinstance(grant, TokenGrant)`, transport-level D-16 with distinct refusals, HTTP+MCP door mapping from one source, R1 was-called spies — all greppable and example-exercised in 05/06.
- **Harness-neutrality evidence is stronger than the §3.1 floor.** Three harnesses, deterministic byte/field equivalence, live Ollama recorded green, A3 closed with a real SDK-parsed `ResultMessage` under a socket guard.
- **CI wiring matches the ruled posture.** Always-on `examples` job, `CCF_REQUIRE_HARNESSES=1`, `timeout-minutes`, no `continue-on-error`, live legs opt-in/`workflow_dispatch`, Anthropic fail-fast on missing secret.
- **Gate discipline is good.** X-1/X-2/X-3 wording fixes, Actions caveat explicit, packaging/order (approve → `D-GATE-I` → merge → tag) correct, fidelity sample labels SDK extensions.

---

## 3. Concerns

### HIGH

- **Actions evidence for EXAM-09 is still missing.** Wiring and local `make ci` are present; the always-on `examples` job and `live-legs.yml` have never run on `origin`. That is correctly flagged for Dave, but REQUIREMENTS marks EXAM-09 **Complete** while the gate itself only claims “discharged at the wiring level.” Until push + green Actions (or an explicit Dave acceptance of local-only evidence), calling EXAM-09 complete overstates CI verification.

### MEDIUM

- **`ApprovalGate.resolve` (and sibling primitives) cannot compose with `signed_binding_required: true`.** `ApprovalGate.resolve` still builds an unsigned `HitlActionSubmission` and never accepts `signed_binding`. Under D-16 policy, that path always refuses at transport. Examples 05/06 correctly work around this via D-IMPL-62 door-submit + owning-composition `HitlActionRecord` construction — but that means the **demonstrated** hardened path is door+driver composition, not the primitive’s `resolve` API. Adopters who call `ApprovalGate.resolve` under a required-binding policy will hit a hard wall. Same pattern likely in override / escalation / review_queue (no `signed_binding` in those modules). This is rule-aligned for v0 doors, but it is an **incomplete composition story** for the HITL pillar and deserves a follow-up D-IMPL or an explicit “do not call `resolve` when D-16 is on; use the door” adoption note in gate/security docs (today it lives mainly in example summaries).

- **Anthropic live success path is weakly evidenced.** Key-absence refusal is verified; a green `make example-03-live-anthropic` with a real key is not claimed in the sweep. Matrix cell “Anthropic × three harnesses” is implemented but not fully proven end-to-end in the recorded evidence.

- **Default HTTP auth posture residual (T-07-24) still stands.** Examples bind `BearerTokenAuth`; the unauthenticated default remains. Fine as a standing residual, but v0 adopters can still stand up an authority-bearing door without auth unless they copy the example pattern.

### LOW

- **Composition-registry docstring still overclaims.** Gate row 4 was narrowed after X-1, but `shipped_operators()` still says pairs are “automatically” covered so an unregistered ship “is not reachable” — comment drift that can reintroduce the overclaim in future reviews.

- **Example 03 README shape inconsistency (X-4).** D-09 rationale present but not under the shared `## Domain rationale (D-09)` heading — contract check passes; suite teaching consistency does not.

- **First allowlist use exposed a path-matching bug.** Fixed and reviewed; residual risk is that other allowlist entries could have been silently inert before. Worth a one-time audit that every entry still matches under absolute reported paths (likely already true for the two ADK entries).

- **Live-leg CI model (`qwen3:0.6b`) ≠ local recorded model (`qwen3-vl:8b`).** Intentional for CPU runners; still a fidelity gap between “local green” and “what Actions will actually run” once pushed.

---

## 4. Suggestions

1. **On approval, treat push authorization as part of closing EXAM-09**, or amend REQUIREMENTS/gate language to “Complete (local sweep; Actions pending)” until the first green `examples` job.
2. **Log a post-v0 / mini-cycle item:** extend HITL `resolve` APIs (or a shared submit helper) to accept optional `SignedPrincipalBinding`, so D-16 requiredness is usable without every composition root reimplementing the 05/06 door pattern. Alternatively, document the door-only path as the ruled v0 contract in `docs/security-notes.md` / DECISIONS next to D-16/D-IMPL-62.
3. **Once a key is available, record one green Anthropic live run** (or dispatch `live-legs.yml` after push) so D-03/D-04 provider coverage is symmetric.
4. **Tighten EXAM-09 wording** in REQUIREMENTS to match the gate’s caveat so claims and evidence stay aligned.
5. **Refresh the `shipped_operators()` docstring** to match the gate’s honest “test-maintained registry” scope.
6. **Optional:** normalize example 03’s D-09 heading for suite consistency (advisory only).

---

## 5. Risk Assessment

**Overall risk: LOW–MEDIUM** (closer to **LOW** for “approve Phase I content”; **MEDIUM** until Actions is observed).

| Dimension | Verdict |
|-----------|---------|
| Completeness vs plans 08-01..12 | Strong — deliverables present and summaries match tree |
| Claims vs evidence | Mostly honest after gate triage; EXAM-09 “Complete” is the main mismatch |
| Security (HITL/auth/bindings/keys) | Hardened surface demonstrated; default-auth residual and resolve/D-16 composition gap remain |
| CI | Local sweep + wiring solid; remote pipeline unproven |
| Replay / portability | Deterministic example 03 + example 06 byte-equal replay look sound on inspection |
| Phase I gate readiness | **Ready for Dave’s (a)/(b) decisions** — not yet “v0 declared” until approval, `D-GATE-I`, merge, tag |

**Bottom line:** The phase goal (v0 examples suite + CI wiring + Phase I gate package) is **genuinely achieved as a presentable gate**. Approve on local evidence with eyes open on the Actions caveat and the HITL `resolve` ↔ D-16 composition gap; do not treat EXAM-09 or `v0.1.0` as fully closed until Dave rules on push and the post-approval merge/tag sequence runs.

---

## Ollama Review

# Cross‑AI Phase‑8 Review (Phase I.5 – Examples Suite & Full CI Verification)

**Overall Assessment:**  
The team delivered all planned artefacts, adhered to the white‑paper contracts, and closed every D‑14 / D‑15 / D‑16 hardening item. The eight‑example suite compiles, runs, and asserts the required invariants; the CI scaffolding (Makefile, lint/post‑commit, GitHub‑Actions jobs) mirrors the local `make ci` command exactly, and all tests pass locally (1339 ✔︎). The only outstanding gating condition is Dave’s final approval / push‑authorization, which means the Actions workflow has not yet been exercised in the hosted runner environment. Apart from this, the phase meets the success criteria, but a few residual concerns remain around security‑key handling, a minor documentation drift, and the robustness of the live‑leg CI jobs.

---

## Strengths  

| ✅ | Description |
|---|---|
| **White‑paper fidelity** – Spot‑check of six public surfaces shows contracts are implemented exactly as specified; extensions are clearly marked as CLAUDE‑MD additions. |
| **Hardening wave completed** – D‑15 verb removal, fail‑closed `TokenGrant` branch, typed refusal error‑codes, signed‑binding requiredness (D‑16) and R1 was‑called assertions are all present, covered by TDD and green tests. |
| **ADK migration** – `SequentialAgent` fully removed, driver now uses `google.adk.workflow.Workflow` at the existing pin; lint‑allowlist bug fixed and documented. |
| **Examples suite** – All eight examples compile, run, and exit 0; each contains a READMEs with invariant tables, domain‑rationale (D‑09) and “change‑first” guidance. The examples touch **seven distinct domains**, satisfying the charter’s horizontal coverage. |
| **Portability proof** – Example 03 deterministic leg runs the same agent definition under three harnesses; live‑leg jobs (Ollama, Anthropic) demonstrate structural equivalence (D‑04). |
| **Replay determinism** – Example 06 reproduces a decision byte‑for‑byte from the ArtifactStore, confirming the five‑dimensional replay contract. |
| **CI scaffolding** – `Makefile` provides a single source of truth (`make ci` = lint + type‑check + test + examples). The CI workflow (`.github/workflows/ci.yml`) runs the identical command set; the new `live‑legs.yml` dispatch jobs are correctly gated by secrets and time‑outs. |
| **Lint posture** – CINV‑01 no‑hard‑coding rule is now scoped to `/examples`; tests enforce the rule and the linter configuration (`RULE_TREE_SCOPE`) is exercised. |
| **Security notes** – `docs/security-notes.md` records key‑sourcing, rotation responsibilities, and CI‑secret discipline. Signed‑binding verification uses a standard JWS library (`joserfc`). |
| **Documentation & Gate artifacts** – Phase‑gate package (README, pyproject bump, D‑GATE‑I placeholder) is ready for final sign‑off. |

---

## Concerns  

| ⚠️ Severity | Issue | Impact / Reason |
|---|---|---|
| **MEDIUM** | **GitHub‑Actions not yet exercised** – The `examples` job and the `live‑legs.yml` jobs have only been verified locally. Differences in runner resources (CPU, I/O, network latency) could cause time‑outs or flaky subprocess handling (e.g., the cross‑process example, live‑leg health‑checks). | The phase gate requires **full CI verification**; local sweep is a proxy but not a guarantee. |
| **MEDIUM** | **Key‑management & secret handling** – Signed‑binding verification and MCP authentication rely on environment variables (`CCF_EXAMPLE07_KEY_DIR`, `ANTHROPIC_API_KEY`, etc.). The code explicitly avoids committing keys, but no automated audit ensures the env never leaks (e.g., through accidental `print` statements or logging). | Potential leakage of signing keys would compromise non‑repudiation guarantees and break the “harness‑neutral” claim. |
| **LOW** | **Documentation drift** – The `CCFContract` docstring cites “eight‑element contract” while the white‑paper defines nine elements (Section 6.3). The discrepancy is noted in a D‑IMPL‑30 comment but the public docstring remains inaccurate. | Minor confusion for downstream users; may indicate a lapse in the “single source of truth” discipline. |
| **LOW** | **Allow‑list matching broadened** – The fix to `AllowlistEntry.matches` now accepts suffix‑matches for repo‑relative paths. While necessary for the ADK allow‑list, the change expands the allow‑list’s acceptance surface, potentially allowing unintended paths if future entries are mis‑specified. | Increases the risk of lint‑rule circumvention if reviewers are not vigilant. |
| **LOW** | **Live‑leg timeout handling** – The Ollama health‑check probe added after a blocking fix introduces an extra network call; if the Ollama service is slow to start, the overall live‑leg job could hit the 15‑minute limit. | May cause unnecessary CI failures on slower runners. |
| **LOW** | **Replay‑by‑construction test scope** – The replay determinism test (example 06) verifies byte‑equality for a single recorded decision. It does not explore corner cases like out‑of‑order replay, expired tokens, or partial store failures. | Future extensions may uncover gaps; not a current blocker but worth noting. |

---

## Suggestions  

| ✔️ | Recommendation |
|---|---|
| **Run the CI jobs on GitHub Actions** before final gate. Push the `phase-i5` branch to the remote (with a temporary tag) and observe the `examples` and `live‑legs` workflows. If any job fails, iterate locally until they are green in the hosted environment. |
| **Add a CI‑level secret‑leak test** – a simple workflow step that runs `grep -R \"ANTHROPIC_API_KEY\" -n .` (or similar) after the build to prove no secret appears in logs or built artefacts. |
| **Update the `CCFContract` docstring** to reflect the nine‑element contract, or add a clear “extension” note if the SDK deliberately omits an element. |
| **Lock the allow‑list format** – add a unit test that asserts every allow‑list entry matches the exact repository‑relative path *and* that suffix‑matching is only permitted for the specific pattern used by the ADK case. Document the rationale in `tools/lints/allowlist.yaml`. |
| **Add retry back‑off for Ollama start‑up** – increase the health‑check loop retries with a small back‑off (e.g., exponential) to avoid false‑negative time‑outs on slower runners. |
| **Extend replay determinism coverage** – add a parametric test that records a decision, mutates a non‑essential artifact (e.g., adds a comment to a YAML file), and asserts the replay still fails the content‑address check. This will prove the replay is truly content‑addressed and not accidentally tolerant of irrelevant changes. |
| **Document the “push‑authorization” state** – in the gate README, include a checklist entry that the branch has been pushed and CI‑actions have run green. This will make the final sign‑off unambiguous for Dave. |

---

## Risk Assessment  

**Overall Risk: MEDIUM**

*Justification:*  
All functional requirements and invariants have been demonstrated locally, and the majority of the hardening and portability objectives are satisfied. The remaining open risk centers on **external CI execution** (unproven runner behaviour, possible time‑outs, and environment differences) and **key‑secret handling** (no automated assurance that secrets never surface in logs). These issues could cause a gate failure after the push, but they are not indicative of fundamental design flaws. Addressing the suggestions above will reduce the risk to **LOW** and pave the way for a clean Phase I gate approval.

---

## Consensus Summary (post-execution)

Risk verdicts: Gemini LOW · Codex MEDIUM · Cursor LOW–MEDIUM · Ollama MEDIUM. All four judge the phase substantively delivered and the gate package presentable; no reviewer found a structural defect in the delivered mechanism.

### Agreed Strengths (2+ reviewers)
- Eight asserted examples across seven domains prove general-purposeness; examples are programs with negatives, not demos (all four).
- HITL hardening (D-15 verb removal, fail-closed TokenGrant, typed refusal codes, D-16 signed-binding at transport with door mapping) is mechanism-grade and example-exercised (all four).
- Example 03 three-harness byte/structural equivalence is strong harness-neutrality evidence; A3 discharged with a real SDK-parsed message (Gemini, Codex, Cursor, Ollama).
- Gate document is honest about caveats — Actions gap, registry-bound composition coverage, residuals (Codex, Cursor, Ollama).
- CINV-01 extension over /examples prevents examples becoming a hardcoding escape hatch (Gemini, Codex).

### Agreed Concerns (2+ reviewers)
1. **Actions evidence missing (Codex HIGH; Cursor HIGH; Gemini/Ollama MEDIUM).** The examples job and live-legs.yml have never run on a hosted runner; "full CI verification" is proven only as command-identical local sweep. Cursor adds: REQUIREMENTS marks EXAM-09 Complete while the gate claims only wiring-level discharge — a claims/evidence mismatch to fix or have Dave explicitly accept.
2. **ApprovalGate.resolve cannot compose with signed_binding_required (Codex MEDIUM; Cursor MEDIUM).** The demonstrated hardened path is door+driver composition per D-IMPL-62; adopters calling resolve under D-16 policy hit a refusal wall. Needs a post-v0 D-IMPL (optional SignedPrincipalBinding on resolve/submit helper) or an explicit door-only adoption note in security-notes/DECISIONS.
3. **Default-unauthenticated create_app posture residual (Codex MEDIUM; Cursor MEDIUM).** Examples bind BearerTokenAuth but the default remains a footgun; make it loud near create_app docs.
4. **Key management operator-dependent (Codex MEDIUM; Ollama MEDIUM).** Documented but not enforced; non-repudiation depends on users implementing key sourcing/rotation correctly.

### Divergent Views
- Gemini rates the phase LOW risk and gate-ready as-is; Codex would rename the state "CI wiring complete, local verification green" until an observed Actions run; Cursor splits the verdict (approve content now; treat EXAM-09/v0.1.0 as open until push+green Actions).
- Ollama uniquely flags secret-leak auditing in CI logs and allowlist suffix-matching breadth; Cursor uniquely flags the stale shipped_operators() docstring overclaim and the Anthropic live leg's unproven success path.

### Disposition
Consensus items 1–4 are gate-presentation items, not in-phase defects: item 1 resolves through Dave's push-authorization ruling (already requested at the 08-13 checkpoint, with an EXAM-09 wording tighten as an advisory fix); items 2–4 are candidates for post-v0 D-IMPL entries / documentation notes. Advisory singles (docstring refresh, EXAM-09 wording, D-09 heading normalization, allowlist audit) can land as advisory fixes without reopening plans.
