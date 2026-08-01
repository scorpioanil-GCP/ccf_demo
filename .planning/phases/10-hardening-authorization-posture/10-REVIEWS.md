---
phase: 10
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-08-01T22:30:00Z
plans_reviewed: [10-01-PLAN.md, 10-02-PLAN.md, 10-03-PLAN.md, 10-04-PLAN.md]
mode: retrospective (phase executed; 1451 tests green; CR-01/WR-01..06 fixed pre-review)
---

# Cross-AI Plan Review — Phase 10

## Gemini Review

# Phase 10: Hardening — Authorization & Posture - Plan Review

This review evaluates the implementation plans for Phase 10, which focused on per-tenant authorization at the HITL doors, signed-binding verification on primitive resolution, and insecure-default posture warnings.

## 1. Summary
The Phase 10 plans are of exceptional quality, demonstrating a rigorous adherence to the project's "Research -> Strategy -> Execution" lifecycle. The strategy of using Wave 0 spikes (A1 and A2) to validate technical assumptions before modifying core contracts was highly effective, particularly in preventing a regression in AuditEvent canonical-bytes stability. The plans successfully realized three major rulings (D-IMPL-68, D-IMPL-69, D-IMPL-73) while maintaining the structural integrity of the fabric's layers and its harness-neutrality invariants.

## 2. Strengths
*   **Empirical Verification of Stability (A2 Spike):** The proactive test of `AuditEvent` canonical serialization before modification was a critical "senior engineer" move. Identifying that additive fields would break pinned replay bytes and pivoting to a derived `AuthzDecisionAuditEvent` preserved system integrity.
*   **Context-Aware Enforcement Placement:** Correctly identifying that authorization must happen in-handler (Pitfall 1) rather than as a blanket router dependency ensures that tenant identifiers and door-declared action IDs are correctly matched.
*   **Adherence to "Mechanism, not Values":** The use of `ScopeMappingArtifact` for grammar matching while keeping actual scope/tenant strings in example artifacts (CINV-01) maintains the SDK's general-purposeness.
*   **Defense in Depth (D-13):** The implementation of idempotent verification in both the primitive and transport layers, without forgeable trust-markers, provides a robust security posture against resolution bypasses.
*   **Honest Failure Semantics (Pitfall 4):** Ordering verification before queue consumption in primitives ensures that a refused resolution (due to an invalid binding) leaves the event pending and resolvable by the correct principal.

## 3. Concerns
*   **Audit Correlation Ambiguity (Medium Severity):** Plan 10-01 records `authz_decision` events as standalone log entries. While necessary for denials (where no HITL action yet exists), for "allow" decisions, the correlation between the authz event and the subsequent `hitl_action` event relies on tenant/action/timestamp. In high-concurrency environments, this may lead to ambiguity. 
*   **JWS Verification Overhead on Resolve (Low Severity):** As noted in D-IMPL-69, primitives now perform JWS verification on every resolve call. Since primitives hold no locks, this is an acceptable cost for security, but it should be monitored during Phase 11 performance benchmarking.
*   **Example Manifest Maintenance (Low Severity):** The manual re-baselining of the example hash manifest for 05/06 is a documented regeneration, but it highlights the friction of manual manifest maintenance as the suite grows.

## 4. Suggestions
*   **Enhanced Audit Linkage:** Modify the `AuthzDecisionAuditEvent` to include an optional `submission_id` or `event_key` field. When an "allow" decision is made at the door for an action submission, capturing this ID would allow for absolute correlation in the audit log between the authorization and the resulting HITL action.
*   **Warning Category Visibility:** Ensure `CcfInsecureDefaultWarning` is documented in the `ccf_runtime` API docs so that adopters know exactly which category to escalate to errors in their own CI pipelines to enforce secure-by-default postures.

## 5. Risk Assessment
*   **Overall Risk Level: LOW**
*   **Justification:** The plans are heavily constrained by locked rulings and established in-repo patterns (e.g., mirroring the D-IMPL-67 auth hook seam). The successful resolution of the A1 and A2 spikes eliminated the primary technical risks associated with MCP resource handlers and replay stability. The inclusion of a cross-door x cross-action test matrix (8+ legs) ensures that the "deny-by-default" posture is empirically proven across all Experience Layer surfaces.

---

## Codex Review

## Summary

Overall, the Phase 10 plans are strong: they decompose the work cleanly, trace most tasks to Dave’s rulings, preserve harness neutrality, and include unusually good test gates for authorization, auditability, warning posture, and examples. The main residual risks are around a few semantic mismatches in the plan language: D-11 said authz decisions attach to the HITL action they gated, while Plan 10-01 deliberately models them as standalone audit events; the `ScopeMappingArtifact` placement in `runtime` may weaken Control Plane artifact consistency; and some “byte-identical” claims are broader than the planned tests can actually prove. Given 1451 tests are green, these are not likely implementation blockers, but they remain plan-quality risks worth documenting.

## Strengths

- Clear phase decomposition: foundation/authz artifact, primitive binding verification, door enforcement, then warning/examples.
- Strong traceability to D-IMPL-68, D-IMPL-69, and D-IMPL-73.
- Good deny-by-default posture with explicit allow/deny audit requirements.
- Cross-door × cross-action matrix is the right HARD-04 gate.
- Defense-in-depth is correctly planned for signed bindings: transport and primitive both verify.
- Good regression thinking: warning escalation, existing auth posture unchanged when unbound, replay canonical-byte checks.
- Examples 05/06 are updated as adoption demonstrations, not just tests.
- No new dependencies, which keeps the phase appropriately scoped.

## Concerns

- **HIGH:** Plan 10-01 partially conflicts with D-11 wording. The context says authz records attach to the HITL action they gated; the plan chooses standalone `authz_decision` events in the same log. That is defensible for queue-read denials, but it should have been escalated as a ruling interpretation, not silently normalized.
- **MEDIUM:** `ScopeMappingArtifact` living under `runtime/ccf_runtime/authz/` is pragmatic, but awkward. It is still a Control Plane policy artifact, so placing the artifact class outside core may create future registration/import asymmetry.
- **MEDIUM:** The audit tuple mapping is compact but lossy-looking. Tenant in `key`, decision in `resolved`, principal in `actor`, and version in `version` may satisfy D-09 technically, but it makes authz audit semantics implicit and could make replay/debug tooling less obvious.
- **MEDIUM:** Plan 10-02 does not clearly require auditing primitive-level signed-binding refusals. It mentions existing refusal-audited patterns, but acceptance criteria focus on exceptions and pending-event survival.
- **MEDIUM:** “Byte-identical” posture claims are broader than the tests. Adding optional kwargs changes signatures and introspection even if runtime behavior is unchanged.
- **LOW:** Plan 10-04’s `-W error::ccf_runtime.http_api.app.CcfInsecureDefaultWarning` syntax is likely fragile depending on warning filter parsing; the intent is good, but the exact invocation should be verified.
- **LOW:** The example hardcoding grep only checks selected strings. It may miss other tenant/scope/action values embedded in code.
- **LOW:** Per-request artifact re-resolution is correct per ruling, but the plans defer any performance consideration. That is acceptable for Phase 10, but should feed Phase 11 perf work.

## Suggestions

- Record an explicit retrospective decision note for the D-11 interpretation: standalone `authz_decision` events in the same audit log, with correlation fields, are the chosen representation because some denied door actions have no HITL action record.
- Consider adding explicit authz audit fields later: `authz_tenant`, `authz_decision`, `authz_principal`, and possibly `authz_scope`. Reusing generic `key/resolved/actor/version` is compact but less self-describing.
- Add a doc or invariant test clarifying why a runtime-defined Control Plane artifact is acceptable, or move only the schema/ArtifactClass into core while keeping interpretation/enforcement in runtime.
- Add tests for malformed or empty scope mappings: duplicate scope entries, empty `tenant_patterns`, empty `action_ids`, invalid semver, wrong artifact class, and no registered artifact.
- Add explicit signed-binding refusal audit assertions for all four primitives if audit-by-construction is meant to include failed human-action attempts.
- Add a negative test that refused HTTP/MCP requests do not touch transport or mutate queues.
- Add a security test ensuring denial payloads never echo token scopes, subject identifiers beyond what is intended, or mapping internals.
- Feed the per-request re-resolution cost into Phase 11 PERF-01/PERF-02 as a named benchmark case.

## Risk Assessment

**Overall risk: MEDIUM.**

The plans achieve the phase goals and are well-tested, but several risks are semantic rather than mechanical: audit modeling, artifact placement, and how much “unchanged posture” is actually proven. Because the implementation is complete and the suite is green, the residual risk is mostly future maintainability, audit interpretability, and ruling drift rather than immediate functional failure.

---

## Cursor Review

# Phase 10 Cross-AI Plan Review (Retrospective)

## Overall Summary

The four plans are high-quality execute plans: wave-ordered, ruling-faithful, TDD-gated, with STRIDE registers and clear must-haves. They achieved HARD-04/HARD-05 and left a green suite. As planning artifacts, the main gaps were security-boundary edge cases (bare `*`, dead-authorizer posture, near-miss audit hole), concurrency on the new hot path (`AuditLog` under door traffic), and soft reinterpretation of CONTEXT D-11 without an explicit decision note. Most of those surfaced in post-execution review and were fixed; residual advisory debt (door refusal ordering, audit tuple incompleteness, primitive consume races) remains.

**Overall plan-quality risk: MEDIUM** — goals met by construction; several HIGH security edge cases were under-specified and only caught after ship.

---

## Plan 10-01 — Authorization foundation

### Summary
Strong foundation plan: A1/A2 spikes, deny-by-default authorizer, D-01 grammar, audit extension, and a clean runtime-only seam (D-05). The A2 “STOP if pins break” gate correctly forced a better design (`AuthzDecisionAuditEvent` subclass) when additive base fields would have broken replay bytes. Weakest planning spots: incomplete D-01 negative cases, no concurrency threat on `AuditLog.append`, and a literal reading of “fields on `AuditEvent`” that the serializer made unsafe.

### Strengths
- Wave-0 assumption spikes (A1 FastMCP resource token; A2 canonical-byte pin) before door work — textbook risk reduction for 10-03
- Explicit D-11 reading for queue-read denials (standalone `authz_decision`, correlation by tenant/action/timestamp) — necessary because attach-to-`hitl_action` cannot cover read denials
- CINV-01 discipline locked: grammar/matching only; no scope vocabulary in SDK code
- Per-call `resolve_latest` (D-07) + deny-by-default + dual allow/deny audit baked into must_haves
- Threat model covers TOCTOU, repudiation, disclosure, replay drift

### Concerns
- **HIGH — Incomplete D-01 negative matrix.** Acceptance criteria reject `"*tenant"` / `"te*nt"` but never `"*"` or `""`. That is exactly WR-03: bare `*` became grant-all. Plans should have listed those as required refusals given “misconfiguration surface minimized.”
- **HIGH — No concurrency plan for audit on the request path.** Putting `authorize()` → `AuditLog.append` on every door request (T-10-03) without locking or a hammer test left CR-01 latent. Threat register mitigated repudiation, not Integrity under concurrent writers.
- **MEDIUM — Soft conflict with CONTEXT D-11.** CONTEXT said authz “attaches to the HITL action it gated”; the plan correctly chose standalone events. That reinterpretation should have been a named open question / Dave note, not only a docstring instruction.
- **MEDIUM — Near-miss / missing-mapping failure modes under-specified.** ControlPlaneMissing → deny was implied; wrong artifact class → `TypeError` before audit (WR-04) was not acceptance-tested.
- **LOW — Planned `AuditEvent` field addition vs serializer reality.** Research should have verified that `None` fields still serialize; the STOP gate saved it, but the plan’s preferred shape was wrong.

### Suggestions
- Add explicit grammar refusals: `"*"`, `""`, `"**"`, and require a non-empty literal prefix before trailing `*`
- Add a Wave-0 or Task-2 concurrency hammer for `AuditLog` whenever a new hot-path writer is introduced
- Specify TokenGrant ↔ scope-string match semantics with one worked fixture table (exact string membership only vs future URI scopes)
- Document the D-11 standalone-event reading in DECISIONS or CONTEXT, not only in plan prose

### Risk Assessment
**MEDIUM** — Foundation was sound; the missing grammar and audit-concurrency cases were real security/plan holes that escaped until post-ship review.

---

## Plan 10-02 — Signed-binding on primitive resolve

### Summary
Clean HARD-05 half: extract shared helpers, harden all four surfaces, verify-before-consume, reuse refusal types, idempotent double verification. Closely tracks D-IMPL-69 and Pitfalls 4/5. Main misses: optional-together kwarg integrity, and not treating concurrent resolve under door load as in-scope when adding CP resolve to primitives.

### Strengths
- Correct defense-in-depth: shared helpers, no forgeable verified-marker (D-13)
- Verify-before-consume + “event stays pending on refusal” as acceptance criteria — closes the dangerous failure mode
- Unbound kwargs regression called out — preserves pre-Phase-10 compositions
- Idempotency test across primitive + transport for at least two surfaces
- Threat model covers spoofing, forged markers, event destruction, lock-hold DoS

### Concerns
- **MEDIUM — Optional-together kwargs not validated.** Plan allows four new kwargs defaulting `None` but never requires “all bound or none” construction checks. Partial wiring (`control_plane` set, `trusted_keys` missing) can surface as `RuntimeError` at resolve time rather than construction fail-closed.
- **MEDIUM — Concurrency of primitive side-band state out of scope.** Adding CP resolve on authority-bearing paths increases concurrent door pressure; WR-02-style drain-and-requeue races were pre-existing and left as Info (IN-01), but the plan’s threat model only covered “no lock on JWS path,” not consume races.
- **LOW — Duplication tax accepted without a follow-up task.** Four copy-paste verification sites (and `_consume`/`_record`) increase fix cost; IN-01 later confirmed this.
- **LOW — Wave independence.** Parallel with 10-01 is fine; no false dependency. Good.

### Suggestions
- Add a construction invariant test: half-bound signed-binding kwargs refuse at `__init__`
- Explicitly defer (or schedule) atomic consume / shared helper extraction so HARD-05 does not leave four divergent copies
- Extend idempotency coverage to all four primitives in the plan text (execution may have done this; the plan only required ApprovalGate + ReviewQueue)

### Risk Assessment
**LOW–MEDIUM** — Ruling fidelity high; residual risk is operational/concurrency and wiring footguns, not bypass of the signed-binding class (once implemented as specified).

---

## Plan 10-03 — Door enforcement + matrix

### Summary
The phase-gate plan for HARD-04: optional authorizer binding, handler-local enforcement (Pitfall 1), shared error code, 2×2×allow/deny matrix, cross-door consistency. Depends correctly on 10-01/A1. Gaps: dead-authorizer silence under D-06, refusal-check order divergence across doors, and no MCP counterpart posture warning.

### Strengths
- Enforcement inside handlers with parsed tenant — avoids blanket-Depends tenant blindness
- Explicit route table (tenant source × action ID) — implementable without invention
- Matrix + cross-door consistency as acceptance criteria — matches ROADMAP criteria 1–2
- Authorizer-unbound regression kept green (T-07-24 posture)
- A1 SUMMARY handoff for MCP resource wiring — good plan coupling

### Concerns
- **HIGH (posture) — Authorizer bound + auth unbound = silent inert.** Plan correctly implements D-06 inertness and tests it, but never required a loud signal when the operator explicitly passed `authorizer=` — WR-05. That is a classic “I thought I was secure” deployment failure; D-IMPL-73 covered only `auth is None`, not this twin.
- **MEDIUM — Refusal ordering not specified.** HTTP authz-before-subject-conflict vs MCP identity/subject-before-authz (IN-02) produces divergent codes and divergent authz audit for the same bad request. D-08 “one vocabulary, two renderings” needed an ordered pipeline sketch.
- **MEDIUM — Matrix deny legs incomplete relative to grammar.** Plan lists wrong tenant / missing scope / empty artifact; does not require “registered grant-all typo” or “near-miss artifact class” door-level behavior (500 vs audited 403).
- **LOW — CLI not in the matrix.** CLI is a thin HTTP client, so HTTP coverage likely suffices — but the plan never stated that assumption, so Experience-layer completeness is implicit.
- **LOW — Performance.** Per-request Control Plane resolve on both doors is intentional (D-07) but not flagged for Phase 11 measurement.

### Suggestions
- Require a construction-time warning/error when `authorizer is not None and auth is None` (now shipped as `CcfDeadAuthorizerWarning` — should have been in 10-03 or 10-04 must_haves)
- Specify one canonical check order for both doors (identity → subject conflict → tenant authz → transport)
- Add matrix legs for empty/missing mapping and wrong artifact class at the door boundary
- One sentence: “CLI inherits HTTP door authz; no separate CLI authorizer”

### Risk Assessment
**MEDIUM** — Matrix design achieves the phase goal; the dead-authorizer and cross-door ordering gaps are the lasting plan defects (one fixed post-hoc, one still advisory).

---

## Plan 10-04 — Warning + examples + manifest

### Summary
Faithful D-IMPL-73 implementation plan plus D-16 example extension and conscious manifest re-baseline. Pitfall 6 (call-site sweep under `-W error`) is excellent CI hygiene. Scope stayed tight. Misses: dead-authorizer twin warning belonged here or in 10-03; example No-Hardcoding regression (WR-06) shows the “values only in YAML” grep was necessary but incomplete for dead branches.

### Strengths
- Dual emission (construction `warnings.warn` + once-only first-request log) with single kwarg suppression — matches ruling exactly
- Explicit ban on env-var suppression and on blanket `filterwarnings` ignore — preserves the CI hook the ruling intends
- Example values in YAML + authorizer binding + live 403 path — demonstrates HARD-04 without teaching insecure wiring
- Manifest re-baseline scoped to 05/06 only with D-16 header — good anti-drift discipline
- Full `make ci` as phase gate

### Concerns
- **MEDIUM — Warning scope only covers `auth is None`.** Plan correctly follows D-IMPL-73 but did not extend the posture story to “authorizer without auth” (WR-05). Closely related insecure configurations should be planned together.
- **LOW — No-Hardcoding grep incomplete.** Acceptance grepped `tenant-a` / `hitl.queue.read` in `run.py` but not other domain tenant literals in dead branches (WR-06 `sterling-mutual`). Broader artifact-vs-code value scan would have caught it.
- **LOW — MCP `build_hitl_server` has no insecure-default warning.** Out of D-IMPL-73 scope (HTTP-only), but Experience Layer has two doors; plan never recorded the asymmetry as deferred.
- **LOW — Task 2 file list under-enumerated.** Plan listed `test_routes`/`test_auth` but correctly required a tree-wide grep — good action text, weak `files_modified` foresight.

### Suggestions
- Pair D-IMPL-73 with dead-authorizer warning in the same plan’s must_haves
- Expand example value lint to “no tenant/scope string literals in `run.py` except via artifact load”
- Note MCP unauthenticated posture as explicit deferred / non-goal under D-IMPL-73

### Risk Assessment
**LOW** — Ruling fidelity high; residual gaps are posture completeness and lint coverage, not core warning mechanics.

---

## Cross-cutting: Did the plans achieve the phase goals?

| Goal | Plan coverage | Residual risk |
|------|---------------|---------------|
| HARD-04 deny-by-default typed 403 at both doors | 10-01 + 10-03 | LOW (after WR fixes) |
| Authz decisions audited with artifact version | 10-01 | LOW; granting *scope* still not in tuple (IN-04) |
| Cross-door × cross-action matrix | 10-03 | LOW; ordering divergence (IN-02) remains |
| HARD-05 all four resolve surfaces × signed binding | 10-02 | LOW for bypass class; MEDIUM for concurrent consume |
| D-IMPL-73 loud insecure default | 10-04 | LOW; dead-authorizer was a sibling miss (fixed) |
| Examples 05/06 demo allow + refuse | 10-04 | LOW |

**Verdict:** Plans were sufficient to ship HARD-04/HARD-05 and mostly complete. They were weaker as a security-edge-case checklist than as a ruling-implementation checklist — the post-execution review (CR-01, WR-03–WR-05) found what the plans should have acceptance-tested.

---

## Top remaining risks (carry-forward)

1. **MEDIUM — Door refusal-order divergence (IN-02)** — same bad request → different error codes / authz audit presence across HTTP vs MCP  
2. **MEDIUM — Primitive non-atomic consume under concurrent doors (WR-02 class / IN-01)** — still advisory; HARD-05 increased pressure on this path  
3. **LOW — Audit tuple missing granting scope (IN-04)** — forensics gap, not an authz bypass  
4. **LOW — MCP exception-shape inconsistency (IN-05)** — unstructured error if unverified-caller path ever fires  
5. **LOW — Per-request `resolve_latest` cost** — intentional; belongs in Phase 11 PERF notes

---

## Suggestions for future phase planning

- For any deny-by-default grammar: enumerate grant-all and empty-string as mandatory refusal cases  
- Whenever a new writer lands on a shared audit/log structure from door threads: plan a concurrency hammer in the same wave  
- When CONTEXT and implementability conflict (D-11 attach-vs-standalone): open a one-line decision note before execute  
- Treat “operator expressed security intent but config is inert” as its own warning class alongside insecure defaults  
- Specify cross-door check order once in PATTERNS, then reference it from both door plans

---

## Ollama Review (gpt-oss:120b)

## 1. Summary  

The Phase‑10 hardening work was executed cleanly: the new `ScopeMappingArtifact`, per‑tenant `TenantAuthorizerProtocol`, audit‑log extension, signed‑binding checks on all four HITL primitives, door‑level enforcement, and the insecure‑default warning were all added, integrated, and validated by the extensive test matrix (≈ 1 450 + green tests).  From a functional‑correctness perspective the phase meets its declarative goals (HARD‑04, HARD‑05, D‑IMPL‑68/69/73) and respects the “mechanism‑not‑values” and “harness‑neutrality” constraints.  However, a retrospective review uncovers a handful of residual gaps—mostly around robustness under failure, performance scalability, and future‑proofing—that could become blockers once the SDK is adopted in real‑world deployments.

---

## 2. Strengths  

- **Tight alignment with locked decisions.** Every D‑IMPL ruling (68, 69, 73) is implemented verbatim; the plan explicitly cites the ruling identifiers and the resulting code carries those citations in docstrings.  
- **Clear separation of concerns.**  
  - Authorization logic lives entirely in `runtime/ccf_runtime/authz/`, leaving `/src` untouched.  
  - Signed‑binding verification is factored out as shared helpers, then consumed by both transport and primitive layers.  
  - The insecure‑default warning is isolated to `create_app` with a single suppression kwarg, avoiding env‑var leakage.  
- **Comprehensive test matrix.** The cross‑door × cross‑action matrix (8 scenarios) and idempotency tests for signed‑binding verification give high confidence that the enforcement path cannot be bypassed.  
- **Additive audit extension.** The audit‑log changes are additive (optional fields, new `AuditAction` enum member) and the pre‑change canonical‑bytes pin (Task 1, A2) remains stable, preserving replay invariants.  
- **Zero new runtime dependencies.** All new code re‑uses existing Pydantic, FastAPI, and MCP utilities, preserving the “harness‑neutrality” contract.  
- **Documentation & manifest discipline.** The examples’ hash‑manifest re‑baseline is explicitly recorded, and every new module carries the required `__ccf_mode__ = "algorithmic"` marker.  

---

## 3. Concerns  

| # | Issue | Severity | Why it matters / Risk |
|---|-------|----------|------------------------|
| C1 | **Control‑Plane resolution failure handling** – the authorizer calls `control_plane.resolve_latest` on every request, but the plan does not define a fallback or explicit error handling if the CP is unavailable or the artifact cannot be parsed. | **HIGH** | A transient CP outage would cause *deny‑by‑default* (good for security) but also raise an un‑handled exception if the call fails catastrophically, potentially bubbling up as a 500 error or crashing the door process. |
| C2 | **Performance impact of per‑request artifact resolution** – repeated CP look‑ups may add latency, especially under high concurrent load (e.g., multi‑tenant SaaS). No performance benchmarks (PERF‑01‑03) were executed before release. | **MEDIUM** | Undetected latency could make the SDK unsuitable for low‑latency use‑cases; also CP load could become a DoS vector. |
| C3 | **Thread‑safety / multi‑process warning flag** – the “once‑only” log record for `CcfInsecureDefaultWarning` is implemented with a module‑level boolean flag. In a multi‑process server (e.g., Uvicorn workers) each process will emit its own warning, violating the “single loud warning” guarantee. | **MEDIUM** | Operators may see a flood of warnings in production, undermining the signal‑to‑noise ratio of the insecure‑default posture alert. |
| C4 | **Scope‑pattern validation edge‑cases** – D‑01 permits only exact match or trailing `*`. The validator does not explicitly reject the pattern `"*"` (a lone wildcard) or an empty string, which could be interpreted as “match all” and unintentionally widen access. | **LOW** | Accidental “allow‑all” artifact could be shipped, breaking the deny‑by‑default security posture. |
| C5 | **Potential double‑audit entries** – both the authorizer and the primitive/door layers may log an `authz_decision` event (authorizer logs, and later the door’s audit path may also log a generic HITL action). The plan assumes a single record; the implementation must ensure no duplication. | **LOW** | Duplicate audit rows inflate storage and may confuse downstream analysis tools. |
| C6 | **Future‑action expansion not covered** – the door‑level enforcement is hard‑coded for two actions (`hitl.queue.read` & `hitl.action.submit`). Adding new HITL actions later will require manual code changes; there is no generic “action registry → authorizer” hook. | **LOW** | Developers may forget to extend both doors, creating a silent authorization gap. |
| C7 | **Lack of observability for authorizer failures** – if `authorize` raises an exception (e.g., malformed grant) the plan does not describe emitting a distinct audit event or metrics. | **LOW** | Operational teams lose visibility into why a request was denied, hindering root‑cause analysis. |
| C8 | **Example manifest re‑baseline process** – the hash manifest re‑baseline is manual. No CI guard ensures that future example changes do not unintentionally drift other files. | **LOW** | Accidental drift could be mistaken for a regression later. |
| C9 | **Audit schema versioning** – adding optional fields is additive, but downstream consumers that deserialize old audit bytes must be tolerant of missing fields. No explicit compatibility test was added for older consumers. | **LOW** | Potential breaking change for external replay or analytics pipelines. |

---

## 4. Suggestions  

1. **Graceful CP outage handling**  
   - Wrap `control_plane.resolve_latest` in a try/except that catches `ControlPlaneError` (or generic `Exception`) and returns a *deny‑by‑default* `AuthzDecision` with a distinct `artifact_version = None` and logs a warning. This keeps the door from raising 500 errors.  
2. **Add performance micro‑benchmark suite** (PERF‑01) now that the feature is in production. Benchmark the per‑request `authorize` path under varying concurrent loads and document the measured p50/p95/p99. If latency exceeds a configurable threshold, consider caching the artifact for a short TTL (while preserving version auditability).  
3. **Make the insecure‑default warning process‑wide safe**  
   - Replace the module‑level boolean with a per‑process `logging` handler that uses `logging.LoggerAdapter` and a `once` filter, or store the flag in a `multiprocessing.Value` / `os.getenv` set by the first process. Document the limitation for multi‑worker deployments.  
4. **Tighten scope‑pattern validator**  
   - Explicitly reject `"*"` and empty strings, and add a unit test for these edge cases.  
5. **Deduplicate audit entries**  
   - Ensure the authorizer’s `audit_log.append` is the sole place where `authz_decision` is recorded. Door handlers should *not* call `audit_log.append` again for the same request. Add a regression test that asserts exactly one `authz_decision` event per request.  
6. **Future‑action extensibility**  
   - Introduce a small registry mapping `action_id → authorizer` (or a generic `authorize_action(request, action_id)`) and use it in both doors. Provide a utility function so new actions can be added without editing the handlers.  
7. **Observability for authorizer failures**  
   - Emit a dedicated `authz_error` audit event (or a metric) when `authorize` raises an unexpected exception, distinct from the normal deny path.  
8. **Automate example manifest checks**  
   - Add a CI step that diffs the current manifest against the version‑controlled file, failing if any line outside the allowed 05/06 range changes.  
9. **Backward‑compatibility test for audit consumers**  
   - Create a minimal consumer that deserializes an older audit record (without the new fields) and verify it still parses. Run this test as part of `tests/replay`.  

---

## 5. Risk Assessment  

**Overall Risk: MEDIUM**

- **Security posture:** The core security requirements (per‑tenant deny‑by‑default, signed‑binding verification, audit‑by‑construction) are satisfied, so the immediate risk of a critical vulnerability is low.  
- **Operational robustness:** The lack of explicit CP‑outage handling and the multi‑process warning flag introduce *medium‑severity* operational risks that could surface in production (unexpected 500 errors, warning spam).  
- **Scalability:** Absence of performance verification means there is a *medium* risk that the per‑request CP resolve will become a bottleneck under load.  

Addressing the high‑severity concern (C1) and medium‑severity concerns (C2, C3) in a follow‑up sprint will lower the overall risk to **low** and strengthen the SDK’s readiness for real‑world adoption.

---

## Consensus Summary

Four independent reviewers (Gemini, Codex, Cursor, Ollama/gpt-oss-120b) assessed the executed
Phase 10 plans retrospectively. Risk verdicts: Gemini LOW, Codex MEDIUM, Cursor MEDIUM,
Ollama MEDIUM — converging on "goals achieved, residual risk is semantic/operational, not
functional."

### Agreed Strengths (2+ reviewers)
- **Wave-0 assumption spikes (A1/A2)** de-risked the phase; the A2 byte-pin STOP gate forced the
  correct `AuthzDecisionAuditEvent` subclass design and preserved replay stability (all four).
- **Deny-by-default with dual allow/deny audit** at exact artifact version, matrix-tested across
  both doors (all four).
- **Defense-in-depth signed binding** — independent verification in primitive and transport, no
  forgeable trust marker, refusal-leaves-pending semantics (Gemini, Codex, Cursor).
- **Ruling fidelity** — D-IMPL-68/69/73 implemented verbatim with citations; mechanism-not-values
  and harness-neutrality preserved (Codex, Cursor, Ollama).
- **In-handler enforcement (not blanket Depends)** correctly matches parsed tenant to door action
  (Gemini, Cursor).

### Agreed Concerns (2+ reviewers — highest priority)
1. **D-11 reinterpretation without a decision note** (Codex HIGH, Cursor MEDIUM, Gemini MEDIUM):
   CONTEXT said authz records "attach to the HITL action they gated"; plans chose standalone
   `authz_decision` events correlated by tenant/action/timestamp. Defensible (queue-read denials
   have no HITL action), but it should be recorded as an explicit decision — and correlation
   fields (submission_id/event_key) would remove audit ambiguity under concurrency.
2. **Per-request `resolve_latest` cost unmeasured** (all four): intentional per D-07, but must be
   a named benchmark case in Phase 11 (PERF-01/02).
3. **Security edge cases under-specified in plans, caught only post-ship** (Cursor HIGH, Ollama):
   bare `"*"`/`""` grammar acceptance (WR-03), AuditLog concurrency on the new hot path (CR-01),
   dead-authorizer silence (WR-05) — all fixed, but plans should have acceptance-tested them.
4. **Audit tuple compactness** (Codex MEDIUM, Cursor LOW/IN-04): tenant-in-key/decision-in-resolved
   mapping is lossy-looking; granting scope absent from the tuple — forensics gap, not a bypass.
5. **Cross-door refusal-ordering divergence** (Cursor MEDIUM/IN-02, Codex implied): HTTP checks
   authz-before-subject-conflict; MCP the reverse — same bad request can yield different codes
   and different audit presence. Should be one canonical pipeline order.

### Divergent Views
- **Gemini rated overall risk LOW** (rulings + spikes eliminated the real risks); the other three
  rated MEDIUM, weighting the post-ship-caught edge cases and operational unknowns more heavily.
- **Ollama flagged Control-Plane outage handling (C1, HIGH)** — un-handled resolve failure could
  500 instead of audited-deny; no other reviewer raised it. Worth a targeted test.
- **Ollama flagged multi-process warning duplication** (once-only flag is per-process under
  multi-worker Uvicorn); others considered the warning mechanism exact per ruling.
- **Codex questioned `ScopeMappingArtifact` placement in runtime** vs core as a Control Plane
  artifact consistency concern; Cursor implicitly accepted the D-05 runtime-only seam.

### Carry-forward items (proposed for Phase 11+ / backlog)
- Name the per-request authorize path as a Phase 11 benchmark case (unanimous).
- Record the D-11 standalone-event interpretation in DECISIONS.md.
- Canonicalize door check order (identity → subject conflict → tenant authz → transport) in PATTERNS.
- Targeted tests: CP outage during authorize (audited deny, not 500); optional-together
  signed-binding kwargs fail-closed at construction; audit-consumer backward compatibility.
- Consider correlation field (submission_id) + granting scope on AuthzDecisionAuditEvent.
