---
phase: 5
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-07-26T22:50:00Z
review_type: retrospective (post-gate)
plans_reviewed: [05-01, 05-02, 05-03, 05-04, 05-05, 05-06, 05-07, 05-08, 05-09, 05-10]
---

# Cross-AI Plan Review — Phase 5 (Phase I.2 — Agent Specialization Framework)

> **Retrospective review.** Phase 5 was executed, verified (4/4 must-haves),
> approved at `D-GATE-I.2` (Dave, 2026-07-26), and merged to `main` before this
> review ran. CLAUDE.md §3.1 step 1 calls for `/gsd-review --phase <Phase> --all`
> *before* presentation to Dave; Phase I.2's gate used `/gsd-code-review` instead.
> This run closes that protocol gap after the fact. **No finding here reopens the
> gate.** Findings are advisories carried into Phase I.3 planning.
>
> Reviewers were given the plans **plus the recorded outcome** (gate document and
> verification report) and asked to judge whether the outcome actually satisfies
> the roadmap Success Criteria — not just whether the plans looked sound.
>
> `claude` was skipped for independence (this session is Claude Code).

## Gemini Review

# Retrospective Plan Review: Phase 5 (Phase I.2 — Agent Specialization Framework)

## 1. Summary
Phase 5 (I.2) represents a high-water mark for architectural rigor in the CCF SDK. The implementation successfully realizes the Agent Specialization Framework by strictly separating SDK-owned **archetypes** from user-defined **agent artifacts**, enforced by a robust factory-only construction pattern. The most impressive aspect of this phase is the "by-construction" capture of decision-ready context, where agent identity (D-06) and the governed skill-set in force (D-07) are mechanically serialized into Decision Replay dimension 4. The iterative gap-closure process (plans 05-08 through 05-10) addressed critical fidelity risks—most notably the per-agent scoping of grant-set hashes and the transition of volatile ledger state to the Control Plane state seam—ensuring that the "forensic defensibility" promised by the whitepaper is a structural property of the code rather than a caller convention.

## 2. Strengths
*   **Mechanical Identity (D-05/06/07):** Using `content_hash` over canonical bytes for agent versions and grant-set identities ensures that replay is immune to insertion order or naming drift.
*   **Factory-Only Construction (D-12):** The use of a CINV-01c lint with exact-path allowlisting and static-alias tracking effectively makes factory bypass a build-blocking event, protecting the integrity of the specialized agent lifecycle.
*   **Governance Robustness:** The Grant State Machine (D-09) is exceptionally well-hardened against "wedging" (WR-01 fix) and includes a thoughtful "reissuable" artifact path (WR-02 fix) that respects the D-05 versioning discipline while allowing retries of rejected requests.
*   **State Seam Integrity (D-18/27):** Moving `GrantLedger` state from volatile instance dicts to the `ControlPlaneStateStore` ensures that multiple ledgers over one registry cannot disagree on the effective skill-set, a prerequisite for reliable distributed operation.
*   **High-Fidelity Replay Extensions:** The extension of `PerspectiveConditioning` to include the delegation chain, archetype composition, and grant-set hash in a single contract change (Pitfall 1) avoids replay-hash churn.

## 3. Concerns
*   **Arbitrary Code Execution (IN-06):** **[HIGH]** `local_callable` dispatch uses `importlib` to execute code named in artifacts. While accepted as a tenant-trust precondition for I.2, this is a massive elevation-of-privilege risk the moment MCP or A2A admit external artifacts in Phase I.3.
*   **Audit Sequence Dependency (WR-07):** **[MEDIUM]** The singular audit plane property relies on composition-root discipline (injecting the same `AuditLog` into both the registry and the ledger). While the `SplitAuditPlaneError` (IN-03) prevents *different* logs, it does not strictly force the *shared* log property if a registry is used without a ledger or vice versa.
*   **Direct Agent Construction in Tests (IN-07):** **[LOW]** The deviation in `test_agent.py` to allow direct constructor testing for validation guards is a necessary pragmatic choice but creates a small blind spot for the CINV-01c lint that must be manually guarded during review.
*   **Missing Mode Marker (ADV-01):** **[LOW]** `src/ccf/controlplane/state.py` claims to be algorithmic in its docstring but lacks the `__ccf_mode__` dunder, meaning CINV-03 does not actually inspect its imports.

## 4. Suggestions
*   **I.3 Threat Modeling:** Before enabling MCP/A2A artifact sources, the project should implement a "Skill Admission Policy" in the Control Plane that allows only specifically allowlisted modules/callables for `local_callable` dispatch.
*   **State Store Opacity:** Consider making `ControlPlaneStateStore` records carry a mandatory `schema_version` to prevent future schema drift in suspended workflow or grant state from breaking long-lived durable stores.
*   **Audit Sequence Hardening:** Modify `GrantLedger.__init__` to always derive its audit log from `control_plane.audit_log`, making the `audit` parameter either strictly internal or removing it to enforce the "singular audit plane" property by construction.

## 5. Risk Assessment
**Overall Risk: LOW**

The phase achieved all Roadmap Success Criteria and satisfied requirements AGNT-01 through AGNT-03 with extreme fidelity to the whitepaper. The "Algorithm ⇄ Semantic Alternation" was preserved (no LLM rendering in I.2), and the single-writer invariant was successfully extended across the agent and skill boundaries. The high number of gap closures (17 distinct findings addressed) indicates a very high level of scrutiny and a stable foundation for Phase 6. The primary residual risks (SSTI in Jinja2 and arbitrary code execution in skills) are correctly identified and documented for Phase I.3.

---

## Codex Review

## Summary

Phase I.2 appears to have achieved the roadmap success criteria at the gate level: AGNT-01/02/03 are covered by staged implementation, gap-closure plans 05-08..05-10 addressed the major SC3 failures, and the final verification report records a clean suite, strict typing, and lints. The plans are unusually strong on traceability and invariant mapping. The main residual risk is not missing feature coverage; it is that several “by construction” claims are still partly enforced by convention, lint scope, or disciplined call sites rather than by unrepresentable states. Those should be carried into Phase I.3/I.4 as explicit architectural hardening items, especially around executable artifact callables, mutable Control Plane state, and factory-bypass guarantees.

## Strengths

- The wave ordering is coherent: 05-01 establishes schemas/version/replay contracts, 05-02 proves the vertical slice, 05-03/05-04 widen archetypes and factories, 05-05/05-06 add skills/governance/replay, and 05-08..05-10 close review findings before the final gate.

- The plans consistently bind work to named decisions and invariants: D-IMPL-11/12/19/28/29, D-05/D-06/D-07/D-10/D-12/D-13, CINV-01..04, and ROADMAP success criteria are all explicitly represented.

- Gap closure was substantive, not cosmetic. CR-01, WR-01, WR-03, WR-06, WR-07, WR-08, IN-03, and IN-08 are the right kinds of issues to catch before a gate: per-agent grant-set identity, false `NO_GRANTS` claims, alias bypasses, ambiguous pinned refs, and volatile discovery were all real correctness risks.

- The final verification report does not merely repeat the gate package; it re-verifies post-pass-2 code, including `ccf.controlplane.state` and `ccf.controlplane.resolution`, and records advisories rather than hiding them.

- The phase stayed mostly inside scope: no agent loop, no task execution, no prompt rendering, no MCP/A2A dispatch binding, and no real ApprovalGate. Those deferrals match the phase boundary.

## Concerns

- **HIGH — Public mutable Control Plane state can still bypass audit discipline.**  
  The verification report says `ControlPlaneRegistry` exposes `state_store` as a read-only property, but that only makes the property binding read-only; the returned `ControlPlaneStateStore` still has `put`. ADV-02 already notes grant auditing is paired-call convention rather than structural. In Phase I.4, a durable state store plus suspended approval/workflow state will make unaudited mutation materially riskier. The affected surfaces are `src/ccf/controlplane/state.py`, `src/ccf/controlplane/registry.py`, and `src/ccf/skills/grants.py`.

- **HIGH — Artifact-declared `local_callable` dispatch is arbitrary code execution by design, and I.3 changes the trust boundary.**  
  The gate handoff correctly identifies this, but it is the largest security carry-forward. `src/ccf/skills/dispatch.py` resolving `callable_ref` through `importlib.import_module` is acceptable only while artifacts are in-repo/trusted. Once MCP artifact stores, A2A federation, or cross-process adapters arrive, the current posture becomes unsafe without an admission policy, callable registry, or import allowlist.

- **MEDIUM — “Only producer is `GrantLedger.bound_view`” is probably a convention, not a structural guarantee.**  
  Plan 05-09 introduces `BoundSkillView` to type the seam, but if `BoundSkillView` is public/exported and normally constructible, a caller can still forge one and pass it to `AgentFactory.construct`. That is stronger than a raw dict, but weaker than the gate wording implies. The next phase should verify whether the constructor is actually inaccessible or provenance-checked.

- **MEDIUM — Factory bypass prevention remains lint-scoped and statically incomplete by policy.**  
  D-12 deliberately chose lint-only enforcement and rejected a construction token. 05-10 improves CINV-01c alias handling and factory-path allowlisting, but runtime construction remains possible because `Agent` is public. This is acceptable as a ruled tradeoff, but future gate language should avoid “no path” phrasing unless scoped to “no supported/lint-clean path in `/src`, `/runtime`, `/examples`.”

- **MEDIUM — CINV-03 has an enforcement hole in `src/ccf/controlplane/state.py`.**  
  ADV-01 is small but meaningful: the module docstring claims “Algorithmic module (CINV-03)” while lacking `__ccf_mode__ = "algorithmic"`, and the lint skips untagged modules. The risk is low today because the file imports only `typing`, but the invariant mechanism is weaker than the documentation claims.

- **MEDIUM — The AGNT-01 consumption allowlist is direct-import only.**  
  ADV-03 says `tests/agents/test_consumption_discipline.py` walks one module’s AST and does not enforce transitive closure. The verifier found the new `ccf.controlplane.resolution` closure clean, which is good, but the invariant claim “no path from Agent to L1-L5 internals” is stronger than the test. This matters as adapter modules are added.

- **LOW — Gate document status appears stale relative to the retrospective framing.**  
  `docs/PHASE_I2_GATE.md` says “AWAITING REVIEW” and says Dave approval, `D-GATE-I.2`, and merge happen after the document. The user prompt says the phase has already been executed, verified, and approved. If this is the final retained gate artifact, it should be reconciled or accompanied by a post-approval note.

- **LOW — Direct `Agent` construction in `tests/agents/test_agent.py` weakens the “tests construct agents the same way” norm.**  
  The gate package records IN-07 as advisory, which is the right classification. It should not block this phase, but future phases should avoid letting this exception become the precedent for broader direct construction.

## Suggestions

- Make `ControlPlaneStateStore` mutation capability private to authorized services, or require an audit-bearing mutation method. For example, expose read/query from `ControlPlaneRegistry.state_store`, but route writes through typed Control Plane services that append audit events atomically.

- Before Phase I.3 admits non-in-repo artifacts, replace free-form `local_callable` import strings with one of: a registered callable table, an import allowlist enforced at Control Plane admission, or a signed/provenance-checked callable policy.

- Strengthen `BoundSkillView` provenance. If Python privacy is the only guard, add an internal factory marker, opaque token, or constructor-time origin check so a user cannot forge an effective skill view and pass it through the supported factory API.

- Add the missing `__ccf_mode__ = "algorithmic"` to `src/ccf/controlplane/state.py`, and update CINV-03 so modules claiming CINV-03 in docstrings but lacking the dunder are lint findings.

- Rename or reword future evidence-map claims from absolute architectural claims to scoped claims where appropriate: “lint-enforced in shipped surfaces,” “audited by current GrantLedger implementation,” or “direct import clean,” unless the state is truly unrepresentable.

- In Phase I.3, add a threat-model gate specifically for prompt rendering and callable dispatch before the first `.render(...)` or remote artifact source ships. This should be a blocking checklist item, not a passive handoff note.

## Risk Assessment

**Overall risk: MEDIUM.** The phase’s required functional surface appears complete and well verified, and the major discovered SC3 defects were closed before the final verification pass. The remaining risks are architectural hardening risks carried into the next phases: mutable state/audit enforcement, executable artifact security, lint-only factory discipline, and direct-vs-transitive invariant checks. None of those invalidate the Phase I.2 gate retrospectively, but they are exactly the areas most likely to become defects when Phase I.3 introduces cross-process adapters and less trusted artifact sources.

---

## Cursor Review

# Phase I.2 Retrospective Plan Review

## 1. Summary

Phase I.2 meets its roadmap success criteria and AGNT-01/02/03 after a necessary gap-closure loop: plans 05-01–05-07 delivered the right architecture (six-axis artifacts, factory-only construction, four-type catalog, two-tier grants, dimension-4 capture), but 05-06 under-specified D-07 as ledger-wide “active grants,” which broke SC3 until 05-08–05-10 fixed per-agent identity, false-claim refusal, lint holes, and gate prose. The outcome is gate-worthy; the plans were strong on sequencing and invariants, weak on stating *whose* skill-set the hash identifies. Carry into I.3: treat remote artifact admission as a hard threat gate (callable ACE + Jinja2 SSTI), and stop calling replay capture “by construction” where a caller can still pass an arbitrary `grant_set_hash` string.

## 2. Strengths

- **Slice-first, pillar-ordered waves (D-01–D-04)** — 05-02 proves artifact → factory → agent → fabric → dim-4 before widening; 05-03→05-06 matches the ruled (a)/(b)/(c)/(d) split.
- **Contracts landed once (05-01)** — six-axis schema, D-05 four-outcome bump, full D-06 dimension-4 field set including `delegation_chain` and `NO_GRANTS_SET_HASH` avoided replay-hash churn (Pitfall 1).
- **Explicit deferrals with typed seams** — D-08 `NotYetBound`, D-09 `ApprovalSink` conformance suite, D-11 Task schema-only, D-13 parse-only Jinja2; I.3/I.4 handoffs are concrete.
- **Invariant verification culture** — D-17 checklist naming `file::function` / lint ids; CINV-01c behavioral fixtures; CINV-04 flip coupled to grant+replay in the same plan (D-10).
- **Gap-closure quality** — CR-01 two-agent regression, WR-01 required hash + `FalseGrantClaimError`, WR-07 `SplitAuditPlaneError`, WR-06 explicit factory-path allowlist, state seam with non-vacuous cross-ledger tests — these turn review findings into structural properties.
- **No-Hardcoding discipline held** — domain values stay in `tests/fixtures/banking/`; sole `Agent(` in `/src` is `factory.py`; D-12 respected (no construction token reintroduced).

## 3. Concerns

- **[HIGH] Plans 05-06 under-specified D-07 agent scope** — Must-have and test text say `content_hash(frozenset(active grant hashes))` with no “filter by `agent_definition_hash`.” That is exactly CR-01: multi-agent ledgers poisoned dim-4. CONTEXT D-06/D-07 implied per-decision identity but never forced a two-agent must_have. **Planning defect**, not just an implementation bug. I.3 must write multi-principal / multi-agent cases into plan must_haves for any set-identity over shared Control Plane state.

- **[HIGH] `local_callable` is artifact-driven ACE; mitigation is a precondition** — `dispatch.py` `importlib.import_module` + `getattr` (IN-06 / T-05-18). Acceptable only while catalog entries are in-repo fixtures. I.3 MCP/A2A artifact admission **invalidates** that precondition. Gate §5 names this; I.3 plans must treat control selection (allowlist / registered-callable indirection / provenance check) as a **blocking** threat item before the first non-fixture catalog source, not a follow-up.

- **[HIGH] Dim-4 grant capture is still partly caller discipline** — WR-01 closes false `NO_GRANTS_SET_HASH` when skills are bound. `perspective_conditioning(..., grant_set_hash: str)` still accepts any other string (stale hash, another agent’s hash, invented hash). Gate/verification “by construction” language overstates this. Structural close would be: Agent captures from an injected ledger at call time, or a typed `GrantSetHash` token only the ledger can mint.

- **[MEDIUM] Audit-on-state-transition is paired-call convention (ADV-02)** — Every `_put_state` in `grants.py` is followed by `_record`, but `ControlPlaneStateStore.put` neither audits nor requires a token. INV-CH7-71 holds by reviewable discipline. I.4 workflow suspend/resume on the same seam will multiply call sites; one missed pair = silent state with no audit.

- **[MEDIUM] `BoundSkillView` “module-private constructor” is docstring-only** — Public `__init__(ledger, agent_definition_hash)` is callable from anywhere. Factory typing helps; it does not make foreign construction unrepresentable. Same class as D-12’s accepted lint-only residual.

- **[MEDIUM] Gate package header stale vs approval state** — `docs/PHASE_I2_GATE.md` still says “AWAITING REVIEW” / “no `D-GATE-I.2` yet,” while `docs/DECISIONS.md` already has **D-GATE-I.2**. Evidence sections also mix pre/post gap-closure counts (568 → 577 → 615). Harmless for code; harmful for anyone treating the gate doc as the single source of gate truth.

- **[MEDIUM] Initial gate prose overclaimed mechanisms (IN-01)** — Rows 6–7 claimed “by construction” / singular audit plane before WR-01/WR-07/CR-01. Verification catch + 05-10 rewrite worked; next phase should draft gate checklist rows from *passing tests that fail under the broken implementation*, not from plan intent.

- **[MEDIUM] D-12 / IN-07: tests construct `Agent` directly** — `tests/agents/test_agent.py` uses `Agent(**values)`. Documented and scoped correctly for constructor-guard tests, but it normalizes a §6.4 exception. No CI rule distinguishes “allowed unit-test construction” from “fixture bypass.” Residual of Dave’s lint-only ruling.

- **[LOW] Consumption allowlist is direct-import only (ADV-03)** — Transitive reach into fabric types via `ccf.replay.record` is inherent and pre-existing; the test cannot claim “no path to L1–L5” in the transitive sense. Keep the claim scoped to *agents package import edges*.

- **[LOW] ADV-01 (`state.py` missing `__ccf_mode__`) appears closed in tree** — Current `state.py:52` has `__ccf_mode__ = "algorithmic"`. Do not re-carry as open; treat verification pass-3 advisory as fixed unless a fresh grep says otherwise.

- **[LOW] Plan count / wave budget** — Roadmap “10/10” included unplanned 05-08–05-10. Healthy response; for I.3 budget a post-verify gap wave explicitly so SC failures don’t look like process failure.

## 4. Suggestions (carry into Phase I.3 / I.4)

1. **I.3 plan must_haves (blocking):** Before MCP ArtifactStore or A2A-admitted catalog entries: (a) `callable_ref` control decided and tested; (b) Jinja2 render sandbox / render-context provenance threat model; (c) multi-agent / multi-tenant grant-set and resolution tests as first-wave must_haves, not review findings.
2. **Close remaining grant-hash caller gap:** Prefer ledger-minted identity (method on Agent that takes `GrantLedger`, or opaque `CapturedGrantSet` type) so dim-4 cannot accept an arbitrary `str`.
3. **Harden audit on the state seam for I.4:** Either `put` requires an audit token, or a single `transition(state, audit_event)` helper is the only writer — so suspend/resume cannot forget `_record`.
4. **Tighten `BoundSkillView`:** Factory function + name-mangled / module-level constructor, or `@typing.final` + lint forbidding `BoundSkillView(` outside `grants.py` (mirror CINV-01c).
5. **Gate doc hygiene:** On `D-GATE-*` approval, rewrite status header and pin one verification count table; keep gap-closure history in an appendix, not as conflicting “current” numbers.
6. **Plan language for set-identities:** Every hash-over-collection must_have names the partition key (`per agent_definition_hash`, `per tenant`, …) and requires a two-entity regression in the same plan.

## 5. Risk Assessment

**Overall: MEDIUM** (for next-phase inheritance) · **LOW** (for “did I.2 achieve its own goals?”)

**Justification:** Recorded outcome satisfies all four Phase 5 success criteria and AGNT-01/02/03; independent verification pass 3 is credible; gap-closure addressed the SC3 failure that would have blocked the gate. Residual risk is concentrated at the I.3 trust boundary (ACE + SSTI) and at invariants still enforced by caller/paired-call convention (`grant_set_hash` string, audit-after-put, public `BoundSkillView`). Those are advisories for Phase 6/7 planning, not reasons to reopen I.2 given `D-GATE-I.2` already logged.

---

### Verdict on plans vs outcome

| Success criterion | Plans predicted it? | Outcome satisfies? |
|---|---|---|
| SC1 six archetypes + composition | Yes (05-02/05-03) | Yes |
| SC2 factory + no-bypass lint | Yes (05-04); WR-06 hardened later | Yes |
| SC3 catalog + grant/revoke + replay | Partially — D-07 agent scope missing until 05-08 | Yes (after gap-closure) |
| SC4 six-axis versioning in replay | Yes (05-01/05-04) | Yes |

**Bottom line:** Approve the retrospective as phase-complete; treat HIGH items as **I.3 planning constraints**, not I.2 reopeners.

---

## Ollama Review (gpt-oss:120b-cloud)

# Phase I.2 – Agent Specialization Framework  
**Retrospective Review (Post‑gate)**  

## 1. Summary  
The Phase I.2 implementation delivers the core “agent as a mechanism” pillar: a unified `Agent` base, the six archetype bundles, a strict factory‑only construction path, a six‑axis definition schema, a version‑controlled artifact registry, a full skill‑catalog, two‑tier grant governance, deterministic grant‑set hashing, and active replay‑by‑construction for the skill‑set. All automated test suites, mypy strict type‑checking and the custom CINV lints report green, and the gate document (PHASE_I2_GATE.md) maps the required evidence to the success criteria. However, several invariants are only enforced by convention (e.g., the no‑bypass lint without a runtime token), a few structural markers are missing (`__ccf_mode__` in `state.py`), and the security boundary around `local_callable` dispatch remains deferred to later phases. Consequently, while the phase meets its *recorded* success criteria, a handful of hidden gaps and over‑reliance on lint‑time checks leave the SDK vulnerable to future regressions.

---  

## 2. Strengths  

| Area | What was done well |
|------|--------------------|
| **Plan granularity** | The wave‑by‑wave breakdown (01‑10) kept scope tight, allowed early TDD on the six‑axis schema, prompt parsing and hash‑verified registration before moving on to composition and governance. |
| **White‑paper fidelity** | All white‑paper primitives (D‑IMPL‑11/19/26/28/29) are represented in code and exercised by unit tests (e.g., `test_composition.py`, `test_schema_export.py`). |
| **Deterministic replay** | Dimension‑4 (`PerspectiveConditioning`) now carries a full, immutable tuple of fields (definition hash, versioned URI, archetype list, grant‑set hash, delegation chain) and is validated by invariant `skill-set-capture`. |
| **Version discipline** | The hash‑verified bump logic (D‑05) is exercised for all six axes, with refusal‑value contracts and audit events. |
| **Grant‑set hashing** | The per‑agent `grant_set_hash` uses `content_hash(frozenset(active_grant_hashes))`; tests confirm order‑insensitivity and that revocation restores the prior hash. |
| **Composition rules** | D‑IMPL‑19 conflict handling (dedupe, order‑wins with warning, hard‑contradiction error) is fully unit‑tested and exercised via the slice fixtures. |
| **Linter coverage** | CINV‑01a/b (prompt‑shaped literals & numeric tables) and CINV‑01c (factory‑bypass) are proven to fire on synthetic bypass modules. |
| **Audit‑plane unification** | Registry and `GrantLedger` now share a single `AuditLog`, satisfying §7.8.2 of the whitepaper. |
| **Documentation & traceability** | Every wave’s `must_haves` table, as‑well‑as the final gate evidence map, makes the trace from requirement → code → test explicit. |

---  

## 3. Concerns  

| # | Concern (severity) | Evidence / Location | Why it matters |
|---|-------------------|---------------------|-----------------|
| **C1 – Runtime bypass guard missing** | **HIGH** | `tools/lints/no_hardcoding.py` (CINV‑01c) – lint only; no runtime token (see D‑12 decision). | A developer can construct `Agent(...)` or `Task(...)` in production code (e.g., via a hot‑patch) and the lint will not run. The whitepaper expects the *mechanism* to be the only path; relying on a static analysis rule is fragile. |
| **C2 – `state.py` lacks `__ccf_mode__`** | **MEDIUM** | Advisory **ADV‑01** – file contains only a docstring, no algorithmic tag. | The `CINV‑03` algorithmic‑vs‑semantic check scans for the module attribute; missing it means the file is invisible to the check, potentially allowing future algorithmic code to slip in unnoticed. |
| **C3 – Direct `Agent` construction in tests** | **MEDIUM** | Advisory **IN‑07** – `tests/agents/test_agent.py` builds `Agent` directly for constructor‑validation. | The same code path is *excluded* from the factory‑bypass lint (because it lives under `src/ccf/agents`), creating an inconsistency: production code cannot bypass the factory, but tests can. Future contributors may mistakenly adopt this pattern. |
| **C4 – `local_callable` dispatch executes arbitrary code** | **HIGH** | `src/ccf/skills/dispatch.py` resolves dotted‑path callables and calls them directly. Threat model defers mitigation to I.3, but the SDK already ships this capability. | If a malicious artifact (e.g., from a third‑party catalog) registers a callable referencing `os.system`, the agent can execute arbitrary OS commands. This is a classic elevation‑of‑privilege/SSTI‑style risk. |
| **C5 – Registry‑only discovery for skill catalog** | **LOW** | `SkillCatalog.discover` now derives from `ControlPlaneRegistry`. No test for caching invalidation when the registry is mutated after catalog creation. | If a catalog instance is retained and the registry later registers a new skill, the existing catalog may not see the new entry (depends on caching strategy). Could cause stale view bugs in long‑running agents. |
| **C6 – Ambiguity error for pinned semver only raised during resolution** | **MEDIUM** | `AmbiguousPinnedVersionError` added (WR‑08). Resolution now raises, but registration still accepts both artifacts. | Two distinct contents under the same declared version remain in the store, consuming storage and potentially causing nondeterministic behaviour for other callers that **skip** resolution (e.g., admin scripts). |
| **C7 – Audit‑log injection path not type‑checked** | **LOW** | `ControlPlaneRegistry.__init__` now accepts optional `audit_log` but the parameter is not part of the public contract (no `Protocol`/type alias). | Downstream code could accidentally pass a mismatched log, breaking the “single‑audit‑plane” guarantee. |
| **C8 – False‑claim handling in `Agent.perspective_conditioning`** | **MEDIUM** | The `grant_set_hash` argument is now required, and a `FalseGrantClaimError` is raised when `NO_GRANTS_SET_HASH` is supplied while `bound_skills` is non‑empty. | Existing client code (outside the SDK) that relied on the default sentinel may now break with a `TypeError` or custom error, which is acceptable but must be documented in the public API. |
| **C9 – Lint‑only detection of import alias bypass** | **MEDIUM** | Updated alias tracking in `no_hardcoding.py` (WR‑06) but only covers top‑level `ImportFrom`/`Import`. Nested aliasing (e.g., `Alias = Agent`; `Alias = Alias`) is not covered. | Sophisticated bypasses could still evade detection, weakening the no‑bypass guarantee. |
| **C10 – Incomplete gating of task‑step class** | **LOW** | `TaskFactory` now checks that `agent` steps resolve to `AgentDefinition` (IN‑08). No explicit check for `skill` steps referencing a `SkillCatalogEntry` class; those are validated earlier but not defensive against a future change where the catalog entry type is altered. | Future schema changes could allow a task step to reference a non‑skill artifact without error. |

---  

## 4. Suggestions  

| # | Recommendation |
|---|----------------|
| **S1 – Add a runtime construction token** (or a `@factory_only` decorator) to `Agent.__init__` and `Task.__init__` that raises if called outside the factory. This makes the no‑bypass guarantee *enforced* at runtime, not just by lint. |
| **S2 – Insert `__ccf_mode__ = "algorithmic"` into `src/ccf/controlplane/state.py`** (and any other new modules) and add a unit test that verifies the `CINV‑03` algorithmic‑mode linter flags any module missing the attribute. |
| **S3 – Consolidate the “direct constructor in tests” pattern**: either move those unit tests into a dedicated `tests/_factory_tests/` package that imports the factory, or add a comment in `Agent.__init__` indicating that construction is allowed for test‑only purposes *only* and will be stripped in production builds. |
| **S4 – Harden `local_callable` dispatch**: introduce a whitelist of allowed packages (e.g., `my_company.skills.*`) configured via the Control Plane, and reject any callable outside that list with a typed `CallableNotAllowedError`. Add tests for whitelist enforcement. |
| **S5 – Make `SkillCatalog.discover` a live view**: store a reference to the registry instead of a cached key set; implement an `invalidate_cache` method and ensure that all catalog instances retrieve entries on each call. Add a regression test that registers a new skill after a catalog has been instantiated and confirms the new entry appears. |
| **S6 – Reject ambiguous semver registration**: modify `register_versioned` to refuse the *registration* of two different contents under the same declared version (instead of only refusing during resolve). This keeps the store clean and avoids hidden duplicates. |
| **S7 – Tighten `ControlPlaneRegistry` audit‑log injection**: expose the `audit_log` via a read‑only `@property` and annotate the constructor argument with `audit_log: AuditLog | None = None`. Add a mypy‑type test that verifies a mismatched type raises a static‑type error. |
| **S8 – Document breaking change in `Agent.perspective_conditioning`**: bump the public version (e.g., minor bump) and add a migration guide for SDK users that previously relied on the default `NO_GRANTS_SET_HASH`. |
| **S9 – Extend `no_hardcoding` alias detection** to follow chained assignments (`A = Agent; B = A; B(...)`) by performing a simple name‑resolution pass over the module AST. Add a test case that verifies the lint fires on a two‑step alias. |
| **S10 – Add a “grant‑artifact registration guard”**: the `GrantLedger.request` should be the *only* method that creates a `SkillGrant` record; disallow direct `register_versioned` of `SkillGrant` artifacts by making `SkillGrant` a private contract class (prefixed with `_`) and exposing a factory in `grants.py`. This prevents bypass of tier‑1 checks by manual artifact registration. |
| **S11 – Emit a formal security‑review note** in the gate doc that the `local_callable` surface is a known elevation risk, and that any production deployment must enable the I.3 sandbox or import‑allowlist before enabling agents in the wild. |

---  

## 5. Risk Assessment  

**Overall Risk: MEDIUM**

*Justification*  

- **Compliance:** All documented success criteria are met; the test suite, lints, and mypy pass, and the gate evidence map is complete.  
- **Structural Gaps:** The most critical security gap (unrestricted `local_callable` execution) is deferred to a later phase, but the capability already exists in the shipped SDK and could be abused if a malicious skill artifact is inadvertently introduced.  
- **Invariant Enforcement:** Several invariants (no‑bypass, algorithmic mode) rely solely on static analysis rather than runtime enforcement, exposing the system to regression if linting is disabled or the code base evolves.  
- **Mitigations in place:** The per‑agent grant‑set hash, audit‑log unification, and version discipline are solid and reduce tampering risk. The identified gaps are isolated and have concrete remediation paths (see suggestions).  

If the deferred security surface (S4) and runtime bypass guard (S1) are addressed before the SDK is exposed to external artifact stores (Phase I.3/I.4), the risk drops to **LOW**. Until then, the current posture is **MEDIUM**.  

---  

**Next Steps for the upcoming Phase I.3 (Cross‑Process & Harness Adapters)**  

1. Implement the sandboxed rendering pipeline for Jinja2 and tighten `local_callable` whitelist.  
2. Propagate the shared `AuditLog` into the harness adapters so audit remains single‑plane across all layers.  
3. Provide migration tooling for the now‑required `grant_set_hash` argument in `Agent.perspective_conditioning`.  

These actions will close the remaining high‑severity concerns and solidify the SDK’s security and correctness guarantees.

---

## Consensus Summary

Four independent reviewers agree Phase I.2 **achieved its own goals**. Risk
ratings for the phase itself: Gemini LOW, Cursor LOW ("did I.2 achieve its
goals?"), Codex MEDIUM, Ollama MEDIUM — where both MEDIUM ratings are explicitly
about *inheritance into I.3*, not about I.2's delivered surface. Cursor states
the disposition all four converge on: *"Approve the retrospective as
phase-complete; treat HIGH items as I.3 planning constraints, not I.2
reopeners."*

The unanimous theme is not missing functionality. It is that several claims
worded as **"by construction"** are in fact enforced by lint scope, paired-call
discipline, or docstring convention — i.e. *reviewable* rather than
*unrepresentable*. That gap is tolerable while artifacts are in-repo and
single-process. Phase I.3 removes both of those conditions.

### Agreed Strengths

- **Mechanical identity** (4/4) — content-hash agent versions and grant-set
  identities make replay immune to ordering and naming drift (D-05/06/07).
- **Substantive gap closure** (4/4) — 17 findings closed across 05-08..05-10 were
  real correctness risks (per-agent grant-set identity, false `NO_GRANTS` claims,
  alias bypasses, ambiguous pinned refs), not cosmetic.
- **Traceability** (3/4) — plans bind work to named decisions and invariants
  throughout; Codex calls this "unusually strong."
- **Scope discipline** (2/4) — no agent loop, no task execution, no prompt
  rendering, no MCP/A2A dispatch. Deferrals match the phase boundary.
- **State seam integrity** (2/4) — moving `GrantLedger` state to
  `ControlPlaneStateStore` so ledgers cannot disagree (WR-05 closure).

### Agreed Concerns

**A1 — `local_callable` is artifact-driven arbitrary code execution, and I.3
invalidates its precondition. [HIGH — 4/4 reviewers, unanimous]**
`dispatch.py` resolves `callable_ref` via `importlib.import_module` + `getattr`.
The T-05-18 trust posture is a *precondition on the input* (artifacts are in-repo
fixtures), not a property of the dispatch path. MCP artifact stores and A2A
federation make `callable_ref` remote-influenced. Ollama gives the concrete
attack: a third-party catalog entry referencing `os.system`. **All four say the
control must be selected before the first non-fixture catalog source — Cursor and
Codex both say it must be a blocking checklist item in I.3, not a passive
handoff note.** Candidate controls named: registered-callable table, Control-Plane
admission allowlist, provenance/signature check.

**A2 — Mutable Control Plane state can be written without audit. [HIGH/MEDIUM —
3/4]** `ControlPlaneStateStore.put` neither audits nor requires a token; every
`_put_state` in `grants.py` happens to be paired with `_record`, but that is
convention (this is ADV-02, which the verifier also logged independently). Codex
notes the `state_store` property being read-only only freezes the *binding* — the
returned store is still mutable. Cursor's escalation is the sharp one: **I.4
workflow suspend/resume lands on this same seam and multiplies the call sites; one
missed pair is silent state with no audit.** Suggested: route writes through
audit-bearing Control Plane services rather than exposing raw `put`.

**A3 — Several "by construction" claims are convention-strength. [MEDIUM — 4/4]**
Three named instances: (a) `BoundSkillView.__init__` is public and callable
anywhere, so a forged view can be passed to `AgentFactory.construct` — Codex and
Cursor both flag this; (b) `perspective_conditioning(..., grant_set_hash: str)`
accepts any string, including a stale or another agent's hash (Cursor); (c)
factory-bypass prevention is lint-scoped, so runtime construction remains possible
(Codex, Ollama). Codex's recommendation, which Cursor echoes: **scope the wording**
— "lint-enforced in shipped surfaces" rather than "no path" — unless the state is
genuinely unrepresentable. Cursor adds a process fix: draft gate checklist rows
from *tests that fail under the broken implementation*, not from plan intent.

**A4 — `state.py` claims CINV-03 without the `__ccf_mode__` tag. [MEDIUM/LOW —
3/4]** The lint skips untagged modules, so the file is invisible to the check it
claims. **Already fixed in `1bfe7de`** — the reviewers were given the pre-fix
snapshot. Retained here because three reviewers independently found it, which
argues for the systemic fix Codex proposes: make a docstring CINV-03 claim without
the dunder *itself* a lint finding.

**A5 — Gate document is stale against approval state. [MEDIUM/LOW — 2/4]**
`docs/PHASE_I2_GATE.md:8-12` still reads "Status: AWAITING REVIEW" and
"deliberately contains no `D-GATE-I.2` entry yet," while `docs/DECISIONS.md`
records D-GATE-I.2 approved. Cursor also notes the evidence sections mix
pre/post-gap-closure counts (568 → 577 → 615). **Verified directly and true.**
Harmless to code, harmful to anyone treating the gate doc as the source of gate
truth.

**A6 — AGNT-01 consumption allowlist is direct-import only. [MEDIUM — 1/4 + verifier]**
`test_consumption_discipline.py` walks one module's AST without transitive
closure, so the invariant claim is stronger than the test. Raised by Codex, and
independently logged as ADV-03 by the phase verifier. Matters more as adapter
modules arrive in I.3.

**A7 — Direct `Agent` construction in tests. [LOW — 3/4]** IN-07 is correctly
classified as advisory, but three reviewers note it normalizes a §6.4 exception
and no CI rule distinguishes "allowed unit-test construction" from "fixture
bypass."

### Divergent Views

- **Overall risk: LOW vs MEDIUM.** Gemini says LOW, reasoning that the phase met
  every Success Criterion and the residual risks are correctly documented for I.3.
  Codex and Ollama say MEDIUM, reasoning from what happens *if* those items are
  inherited unaddressed. Cursor resolves the disagreement explicitly by splitting
  the question: **LOW for "did I.2 achieve its goals," MEDIUM for "what I.3
  inherits."** That split is the honest reading, and the two ratings are not in
  conflict.
- **Was CR-01 a planning defect or an implementation bug?** Cursor alone argues
  it was a **planning** defect [HIGH]: plan 05-06's must-haves specified
  `content_hash(frozenset(active grant hashes))` with no per-agent filter, so no
  two-agent test was ever required. Its prescription — *write multi-principal
  cases into plan must_haves for any set-identity over shared Control Plane
  state* — is a concrete I.3 planning constraint the other three did not surface.
- **Registration of ambiguous pinned versions.** Ollama alone (C6) notes that
  `AmbiguousPinnedVersionError` fires at *resolution* while *registration* still
  accepts both contents, so two artifacts share a declared version in the store
  and a caller who skips resolution sees nondeterminism. Not raised by the others;
  worth a look.
- **Audit-log sharing.** Gemini notes `SplitAuditPlaneError` prevents *different*
  logs but does not force the *shared* log when a registry is used without a
  ledger. Its suggestion — drop the `audit` parameter entirely and always derive
  from `control_plane.audit_log` — goes further than the IN-03 fix that shipped.

### Disposition

All findings are **advisory** — the gate is closed and cannot be reopened by a
retrospective. Recommended routing into Phase I.3:

| Finding | Routing |
|---|---|
| A1 `local_callable` ACE | **Blocking checklist item** in the I.3 A2A/MCP wave, before the first non-fixture catalog source. Already named in `06-CONTEXT.md` canonical refs as required reading. |
| A2 unaudited state writes | I.3/I.4 design item — audit-bearing write path on the state seam before workflow state multiplies call sites. |
| A3 convention-strength claims | Wording fix now; structural fixes (provenance-checked `BoundSkillView`, minted `GrantSetHash` token) as I.3 hardening. |
| A4 CINV-03 tag | Fixed (`1bfe7de`). Systemic lint upgrade optional. |
| A5 stale gate doc | Fix immediately — pure documentation accuracy. |
| A6 transitive allowlist | I.3, when adapter modules enter the import graph. |
| A7 test construction | Watch; do not let it broaden. |
| Cursor's must_have rule | Adopt as an I.3 planning constraint. |
