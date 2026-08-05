---
phase: 15
reviewers: [gemini, codex, cursor, ollama]
reviewed_at: 2026-08-05T18:10:00Z
scope: shipped code + plans (post-merge design review, not a plan review)
note: claude excluded for independence (review ran inside Claude Code)
---

# Cross-AI Design Review — Phase 15 (post-gate)

Commissioned by Dave after D-GATE-15, on discomfort with the shipped state.
Headline question put to all four: **is this a sound design approach?**

## Verdicts

| Reviewer | Verdict | Should it have shipped? | Risk |
| --- | --- | --- | --- |
| gemini | Sound | Yes | LOW |
| codex | Sound with reservations | Yes, "as a cautious SDK surface, not a triumphant ergonomics phase" | MEDIUM |
| cursor | Sound with reservations | Yes | MEDIUM |
| ollama | Sound | Yes | see below |

## Confirmed defects (verified empirically by the orchestrator, not taken on report)

### CR-1 — author-versioned classes can bypass the D-05 bump check via the manifest (HIGH, blocking)

Raised by codex and cursor independently; gemini raised the same split as its only HIGH.
Codex stated the falsifiable test: "If adopters can put workflow/task/agent definitions in
the manifest with role: register and thereby use register_typed, the design is unsound."

Verified: `SDK_ARTIFACT_ROLES` fixes exactly one class, `ccf.signal-batch`.
`refuse_role_the_sdk_fixes` accepts `role: register` for `ccf.workflow-definition`,
`ccf.agent-definition` and `ccf.task-definition`, all of which then route through
`register_typed` — which does not run the hash-verified bump check.

The 15-19 ruling is therefore a **convention the shipped examples follow**, not an enforced
invariant. `test_the_author_versioned_definitions_kept_their_bump_check` proves the examples
do it right; nothing proves the manifest refuses the wrong thing.

### CR-2 — Gate 2 is self-satisfying in every example (HIGH, blocking) — a NINTH instance

Raised by cursor alone. Verified across 9 files: every example constructs
`ProductLineage(operators_invoked=execution.operators_invoked, ...)` and then calls
`run_gates(candidate, engine_resolved=execution.operators_invoked)` — the same value on
both sides of lineage strict equality (INV-CH7-47).

Files: 00-quickstart, 01-agent-basics, 02-skilling, 03-harness-portability,
04-cross-process/producer_child, 06-decision-replay, 07-artifact-store-mcp, 08-e2e-demo,
external/00-hello-context/serve.

This is the phase's own signature finding, tree-wide, in the adoption contract.
The phase closed the *upstream* `required_operators()` collapse and numbered around this one.
`test_gate_independence.py` admits callers outside `ccf.deployment` may pass the same value twice.

## The fix all three substantive reviewers converged on, independently

Per-entry registration mode in the manifest — `registration: typed | versioned`.
`load_and_boot` dispatches to `register_versioned` for author-versioned classes and refuses
any manifest registering them through `register_typed`. Everything lives in the manifest;
one mental model; governance enforced rather than conventional.

Gemini: `version_policy: strict_bump`. Codex: full field list plus "tests proving
workflow/task/agent definitions cannot bypass bump checks through the manifest."
Cursor: "Same ergonomics win without the split."

Both codex and cursor called the split **backwards**: the more governance-sensitive the
artifact, the *less* declarative the phase made it.

## Agreed strengths (2+ reviewers)

- The abstraction line is real, not decorative: `ccf.deployment` is barred from importing
  the gates, does not construct lineage, does not run gates, does not mint MaxTTL.
- The generated bidirectional public-surface diff is called out by gemini as "the most
  impressive part of this phase" and by cursor as "strong."
- The self-satisfying-check finding is real and generalizable, not post-hoc narrative
  (codex and cursor both explicit).
- CINV-01 widened to `tests/` with zero allowlist entries.
- Measurement discipline that structurally cannot sum removal with relocation.

## Agreed concerns (2+ reviewers)

- CR-1, the registration split (all three).
- New AST gates are **tripwires, not walls** — they catch known patterns, and should not be
  described as structural enforcement on par with single-writer DI (codex and cursor).
- `BootedFabric.artifacts` exposing both roles blurs "parsed" vs "in force" (codex, cursor).
- D-IMPL-81 open means the manifest — the document that assigns roles — is itself unpinned,
  so "no replay dimension hidden" is incomplete (codex, cursor).
- Erosion pressure: the next convenience PR will try to cross the line drawn in negative space.

## Divergent views

- **Risk level.** Gemini LOW; codex and cursor MEDIUM. Gemini did not find CR-2.
- **Process weight.** Cursor: 21 plans was too many, the surface machinery could have ridden
  a smaller close-out plan. Gemini: the volume was justified.
- **The finding count.** Cursor asserts the Gate 2 call-site pattern is a ninth shape the
  phase numbered around — verified above. The audit's "eight" is an undercount.

## Cursor's closing note on the gate itself

> Dave already approved (D-GATE-15). This review is whether that approval was earned.
> It was — with the HIGH items above still unpaid debt, not closed by the gate.

---

## GEMINI Review

The design approach of Phase 15 is **sound**, but it succeeds by narrow margins that create a new class of "shadow configuration" risk. By centralizing the mechanical wiring of a deployment into the `ccf.deployment` package and moving artifact registration into a manifest-driven path, you have significantly lowered the barrier to adoption (Condition 4) without violating the No-Hardcoding rule (CINV-01). However, the "split registration" ruling is a leaky abstraction that forces adopters to understand the internal plumbing of versioning just to decide which file goes in which list.

### 1. Verdict on the design approach
**Sound.** The phase correctly identified that "No-Hardcoding" was being paid for by "Hard-Wiring"—boilerplate code that manually marshalled artifacts. The move to a declarative `DeploymentManifest` is the right architectural evolution. It treats the *assembly* of the fabric as a first-class, recordable event, which actually strengthens Whitepaper Fidelity (Condition 1) by making the boot-time configuration an artifact itself.

### 2. Should this phase have shipped at all?
**Yes.** 21 plans of ergonomics might look like scope creep, but it was a necessary "refactoring to the surface." Without it, the SDK was a collection of powerful primitives that required a PhD in the whitepaper to stitch together. The 90% reduction in mechanical wiring in `examples/` is not just "convenience"—it's the difference between a library and a product. It serves Condition 4 (Adoptability) without trading off Condition 1 (Fidelity), as evidenced by the new standing gates that prevent convenience from swallowing invariants.

### 3. The abstraction line
The claim that no governance decision or replay dimension is hidden is **defensible but fragile**. 
- **The Attack:** `load_and_boot` hides the *order* of registration and the *selection* of which artifacts are "load" vs "register" inside the manifest's YAML. If an adopter misconfigures a role in the manifest, the "governance decision" is buried in a config file rather than being explicit in the integration code.
- **The Defense:** The "marshalling and wiring only" boundary is held by the `cinv02-deployment-gates` lint. By refusing to let the deployment package import the gates, you've ensured the *validation* of the fabric remains an adopter responsibility. This is the correct "uncomfortable" line: the SDK makes it easy to build the machine, but it won't let you skip the safety inspection.

### 4. The self-satisfying-check finding
**It is a real finding, but the narrative is slightly over-sold.** 
The discovery that `lineage.operators_invoked` was being compared against itself is a classic "shadowing" bug. Typed artifacts made this visible because they forced the *source* of the truth (the artifact) to be distinct from the *observation* of the truth (the runtime execution). 
- **Is it generalizable?** Yes. Whenever a system provides a "helper" that produces both the expectation and the result from the same input, it creates a tautology.
- **Do the new gates over-claim?** Likely. The `test_gate_independence.py` ensures the *package* can't call the gates, but it doesn't prevent an adopter from writing a single "convenience" function in *their own* code that collapses the two. The SDK has protected its own house, but it hasn't (and perhaps shouldn't) protect the adopter from their own shortcuts.

### 5. Concerns

*   **HIGH: The Registration Split.** The ruling that "author-versioned" classes (Workflows, Agents) stay in explicit adopter code while others move to the manifest is inconsistent. If a Workflow is a "Control Plane artifact," it belongs in the manifest. Forcing it out just to preserve a manual `register_versioned` call suggests the manifest implementation is incomplete, not that the Workflow is "special."
*   **MEDIUM: Manifest Directory Locality.** `load_and_boot` resolves paths relative to the manifest file. This is good for portability, but it creates a "hidden state" where the directory structure *is* the configuration. If an artifact is moved without updating the manifest, the error is clear, but the "source of truth" for the file tree is now split between the OS and the YAML.
*   **LOW: CINV-03 "Algorithmic" Loophole.** Tagging the deployment package as "algorithmic" while doing heavy I/O is technically allowed by your lint, but it stretches the spirit of "no raw signal." A manifest *is* signal—it's the signal that configures the fabric.

### 6. What I would do differently
I would eliminate the "Registration Split." The `DeploymentManifest` should support a `version_policy` field for each entry. If `version_policy: strict_bump`, the `load_and_boot` call should perform the hash-check and refuse to boot if the content changed without a version increment. This would allow *all* artifacts to move into the manifest, providing a single, unified mental model for "what is in force."

### 7. Anything else
The most impressive part of this phase isn't the code—it's the **generated public-surface diff**. By asserting bidirectional completeness at FQN granularity, you've turned the "public API" into a governed artifact itself. This is a level of rigor rarely seen in ergonomics refactors and is the strongest evidence that this phase was executed with Whitepaper Fidelity in mind.

**Overall Risk Assessment: LOW.** The architectural boundaries are well-guarded by CI, and the reduction in boilerplate significantly reduces the "surface area for adopter error." The inconsistencies in registration are minor compared to the gains in clarity.

---

## CODEX Review

**1. Verdict**

**Sound with reservations.** The broad design approach should exist: moving hand-written YAML marshalling and deployment wiring into a typed, declarative SDK seam serves adoptability without obviously absorbing the agent loop or weakening harness neutrality. The strongest evidence is that `load_and_boot()` still returns pins/artifacts/handle and refuses to project, run gates, construct lineage, or build replay records. But the design is not fully clean. The manifest/explicit-registration split for versioned artifacts is conceptually awkward, and `register_typed` inside `load_and_boot()` is a sharp edge unless role/class constraints make bypass impossible.

**2. Should It Have Shipped?**

Yes, but it should have shipped as a cautious SDK surface, not as a triumphant ergonomics phase.

This was not mere scope creep. The phase attacked a real adoption defect: examples were teaching adopters to hand-write mechanical artifact marshalling, which is exactly the sort of SDK tax that causes divergent deployments. Declarative parsing through one `parse_artifact`/`load_artifact` seam improves fidelity because authored artifacts now have typed contracts instead of example-local translation code.

It also appears to serve the priority order:

1. **Whitepaper fidelity:** improved if typed artifacts expose authored-vs-observed distinctions.
2. **General-purposeness:** mostly preserved; the new package wires artifacts, not domain policy.
3. **Harness neutrality:** preserved if `/src/ccf/deployment` has no harness imports.
4. **Adoptability:** clearly improved.

The reservation: 21 plans / 14 waves is a lot of surface area for “ergonomics.” That is acceptable only because the phase also added standing gates, schema discovery, public-surface accounting, and example rewrites. Without those, this would look like convenience churn.

**3. The Abstraction Line**

“Marshalling and wiring only” is coherent, but fragile.

`load_and_boot()` does several things that are acceptable SDK mechanism:

- parse a manifest;
- resolve artifact classes;
- parse all artifacts before registering any;
- register `role: register` entries;
- return `ResolvedPins`;
- call `boot()` with explicit pinned bindings.

That boundary is defensible because it does **not** execute operators, project a product, build lineage, run gates, or synthesize replay dimensions beyond returning the registered pins.

Where helpers could hide governance decisions:

- choosing artifact versions implicitly;
- selecting policy bundles or resolution specs by convention;
- constructing `ProductLineage`;
- deriving both declared lineage and observed execution from one object;
- registering TTL ceilings and then using the same source to validate TTL;
- building replay records from live registry state rather than explicit returned pins;
- silently treating `role: load` artifacts as replay-relevant;
- hiding operator parameters behind registry defaults.

The current docstring is unusually explicit about these dangers, which is good. But docstrings are not the boundary. Tests and lints are. The most important hard line is: `ccf.deployment` must not import `ccf.products.gates`, must not construct `ProductLineage`, and must not accept `ProjectionExecution` and return lineage.

**The manifest split:** I do not love it.

The ruling is defensible in a lawyerly way: “where a definition lives” and “which registration path puts it in force” are different questions. But for adopters, it creates two mental models:

- most artifacts are listed in the manifest and registered by `load_and_boot()`;
- some especially important control-plane artifacts must stay in adopter code because they require `register_versioned`.

That is backwards ergonomically. The more governance-sensitive artifacts should be *more* declarative, not less.

The better design would be for the manifest to express registration semantics explicitly, for example:

```yaml
role: register
registration: versioned
expected_version: 3
content_hash: ...
```

Then `load_and_boot()` could dispatch to `register_versioned()` for author-versioned classes. If that is impossible today, the split is acceptable only if `refuse_role_the_sdk_fixes()` makes it impossible to accidentally register author-versioned artifacts through the unverified path.

If adopters can put workflow/task/agent definitions in the manifest with `role: register` and thereby use `register_typed`, the design is unsound.

**4. The Self-Satisfying-Check Finding**

The finding is real, not just post-hoc narrative.

The lineage defect is exactly the kind of bug a typed authored artifact model reveals: a check only matters when the “declared” and “observed” sides come from independent sources. Comparing a value to itself is worse than no check because it advertises an invariant that is not being enforced.

The cross-organization entitlement example is also real: reading the producer’s own file twice proves nothing about consumer admission.

This is generalizable. In this project, many invariants appear to depend on source independence:

- declared lineage vs engine-observed operators;
- declared TTL vs independently registered max TTL;
- replay record pins vs current registry contents;
- admitted entitlement vs producer-authored entitlement;
- generated public-surface diff vs independently maintained expectations;
- schema headers in artifacts vs schema generated from the same code under test.

There are probably more instances.

The new gates are directionally right, but any gate generated by the same mechanism it verifies deserves suspicion. The rename-bypass issue you mention is a warning sign: if a lint claims semantic protection but only matches local syntax, its docstring is over-claiming. That does not make the lint useless; it means it should advertise itself as a guardrail against known patterns, not proof of invariant preservation.

**5. Concerns**

- **HIGH:** `register_typed` inside `load_and_boot()` is dangerous for author-versioned artifacts unless class/role refusal makes bypass impossible. This is the biggest design risk.

- **HIGH:** The manifest split gives adopters an inconsistent model: “declare deployment artifacts here, except the governance-sensitive ones you must register manually.” That will be misunderstood.

- **HIGH:** Generated surface-diff completeness can become self-confirming if both sides are discovery-driven. Bidirectional FQN checks help, but they do not replace human review of semantic surface changes.

- **MEDIUM:** `BootedFabric.artifacts` returns both `register` and `load` artifacts. The docstring explains that visibility is not replay relevance, but adopters may still treat parsed loaded artifacts as “in force.”

- **MEDIUM:** `load_and_boot()` registers entries sequentially and accepts partial registration on backend failure. The stated rationale is plausible, but this is still operationally surprising.

- **MEDIUM:** The expanded No-Hardcoding lint is good, but zero allowlist entries can create a false sense of completeness. Static rules usually miss aliases, indirection, generated constants, and data smuggled through fixtures.

- **LOW:** The package is heavily documented. That is useful now, but long doctrinal docstrings can drift from enforcement. Critical claims should be executable tests.

**6. What I Would Do Differently**

I would make manifest registration semantics explicit instead of splitting responsibility between manifest and adopter code.

Concretely:

- add a manifest field for registration mode: `typed` vs `versioned`;
- require author-versioned artifact classes to use `versioned`;
- make `load_and_boot()` call `register_versioned()` where appropriate;
- reject any manifest that tries to register those classes through `register_typed`;
- include the version/hash bump evidence in the returned `ResolvedPins` or adjacent audit structure;
- add tests proving workflow/task/agent definitions cannot bypass bump checks through the manifest.

I would also create an “independence matrix” for every invariant gate:

```text
Invariant | Declared source | Observed source | Test proving they can diverge
```

Every gate should have at least one test where the two sides differ and the gate fails.

**7. Anything Else**

The biggest unframed risk is that “ergonomics” becomes the place where governance policy quietly accumulates because it feels like harmless glue.

The current phase mostly avoided that. But `ccf.deployment` is now a privileged conceptual layer: it decides how deployments become live fabrics. That package needs stricter design rules than ordinary helper code. In particular, every future convenience added there should be reviewed against this question:

> Does this helper combine two facts that an invariant needs to remain independent?

If yes, it probably does not belong there.

**Overall Risk: MEDIUM**

The approach is basically sound and likely worth shipping. The risk is not that SDK ergonomics are bad; they are necessary. The risk is that the registration split and convenience boundary are subtle enough that future contributors or adopters may collapse governance distinctions while believing they are just reducing boilerplate. The design is acceptable if the versioned-artifact bypass is impossible in code. If it is possible, this should be treated as a blocking correctness defect.

---

## CURSOR Review

# Cross-AI Design Review — Phase 15

## 1. Verdict on the design approach

**Sound with reservations.** Absorbing YAML→typed marshalling and boot wiring into `ccf.deployment`, while refusing to absorb gate execution, replay-binding selection, MaxTTL minting, and lineage construction, is the right abstraction line for this SDK. The package docstrings and the shipped refusals (`cinv02-deployment-gates`, `ResolvedPins` with exactly one accessor, D-IMPL-76 keeping admitted policy versions in adopter code) show the authors understood the failure mode: a helper that collapses two independent sources into one leaves the invariant green and dead. That is a real design, not a line-count project with governance stickers. The reservations are about residual adopter cliffs (typed vs versioned registration), one overclaimed independence story around Gate 2, and process bloat relative to the core insight.

## 2. Should this phase have shipped at all?

**Yes.** Not because 21 plans of ergonomics is naturally “phase-sized,” but because the alternative — leave every deployment hand-marshalling artifacts while CI asserts whitepaper fidelity — was actively hostile to success condition 4 and was starting to undermine 1 and 2 via example-as-spec rot.

Priority order:

| Condition | Effect of Phase 15 |
|---|---|
| Whitepaper fidelity | Net positive. Did not change gate/replay contracts; *surfaced* defects in examples that claimed those contracts. |
| General-purposeness | Strengthened: CINV-01 into `tests/` with zero allowlist (D-IMPL-78); domain values stay in artifacts. |
| Harness neutrality | Untouched (correct). |
| Adoptability | The actual goal; mechanical wiring −90.6% is real, measured, not vibes. |

Was it scope creep? Partly in *volume* (surface instrumentation, 21 fragments, bidirectional FQN completeness) — that tooling is valuable but was not required to ship `load_and_boot`. The *substance* was not creep: the No-Hardcoding Rule had pushed values into YAML and then abandoned adopters at the seam. Shipping without fixing that seam would have been the worse call.

What would have been wrong: absorbing `run_gates`, auto-selecting policy bindings, or registering signal batches into dimension 2. Those were declined (D-IMPL-80, D-15A). That judgment is why the phase earns its keep.

## 3. The abstraction line — attack the claim

Claim: hid no governance decision and no replay dimension.

**What holds**

- `load_and_boot` changes *who produces pins*, not what `boot` requires (`manifest.py`). Manifest enumerates; globs refused.
- `role: load` vs `register` is explicit, required, SDK-fixed for `ccf.signal-batch` (`SDK_ARTIFACT_ROLES`). That prevents raw events entering dimension 2 — a real fidelity landmine an earlier plan draft nearly stepped on.
- `ResolvedPins.version_for` is lookup-only; a `policy_bindings()` helper was correctly refused.
- Gate execution stays in adopter code; `ccf.deployment` may not import `ccf.products.gates`.

**Where the claim is soft**

1. **Gate 2 call sites still teach a collapse.** `ProductLineage` says a field the engine filled in makes INV-CH7-47 vacuous (`contract.py`). Every rewritten example does exactly that:

```261:273:examples/00-quickstart/run.py
            lineage=ProductLineage(
                operators_invoked=execution.operators_invoked,
                ...
            ),
        match run_gates(
            candidate,
            engine_resolved=execution.operators_invoked,
```

Same pattern in 01–08 and external. The phase prevented *helpers* from collapsing the two arguments while *codifying* the collapse in adopter-facing spines. `test_gate_independence.py` admits it: callers outside `ccf.deployment` may pass the same value twice. Rhetorical independence (“separate keyword”) is not source independence. The honest Gate 2 construction is producer claim (e.g. authored required keys / plan intent) vs `execution.operators_invoked`. The suite still does not demonstrate that.

2. **`BootedFabric.artifacts` returns register-role artifacts too.** Amendment is defensible (avoid `isinstance` filtering), but it blurs “what was in force” vs “what was parsed.” Adopters can confuse parse results with pin set. Role governs registration; visibility does not — subtle (A-8).

3. **Manifest itself is not pinned (D-IMPL-81 OPEN).** Constituents are in dimension 2; the document that chose roles and membership is not. A `role` reassignment that drops something from the pin set can be invisible to replay under today’s record. The phase correctly refused to invent fabric behavior mid-ergonomics — but then “no dimension hidden” is incomplete: the new authoring surface is not yet a replay dimension.

4. **Erosion pressure is real.** Next conveniences writing themselves: “build candidate + run gates,” “mint MaxTTL from product-class,” “assemble `policy_bindings` from all pins.” The standing guards buy time; they do not freeze the line. “Marshalling and wiring only” is coherent *today* because the authors declined the next steps and wrote negative docstrings. It will erode the first time someone optimizes day-1 past the MaxTTL / Gate 2 cluster that intentionally remains in `run.py` (~lines 219–301).

## 4. The self-satisfying-check finding

**Real, not post-hoc narrative — with an overclaim.**

The ledger in `SURFACE-AUDIT.md` §4.1 is concrete. Two defects are load-bearing:

- **15-17:** Gate 2 / plan declaration from registry keys in both record *and* replay environments in the example whose subject is audit-by-construction.
- **15-18:** A2A entitlement compared two reads of the producer’s file.

Those are not “we deleted lines and also found bugs.” Typed artifacts forced an authored left-hand side; that is a generalizable mechanism for finding tautologies. Vacuous `__all__` scans, relocated fail-closed checks reading after the fact, escalation expected values taken from the engine’s own input — same family.

**Likely more exist.** The Gate 2 call-site pattern above is a ninth shape the phase numbered around. Any test that reads expected values from the same artifact the SUT loads (A-4’s “propagation checks”) is another. Consumer-side independence (15-18 style) is rarer than the suite implies.

**New gates:** mostly sound after B-1. The G-B guard’s fixed-point aliasing is honest about not being dataflow — good. Schema-header exact directory set — good. Surface completeness bidirectional — strong. Residual overclaim risk: AST convention lists feel like walls; they are tripwires. A registry named `ops_reg` or arriving via a helper still walks past. Do not treat them as CINV-class structural enforcement equivalent to single-writer DI.

## 5. Concerns

- **HIGH — Gate 2 call-site tautology taught tree-wide.** Contract and `gates.py` require producer vs engine independence; examples fill both from `execution.operators_invoked`. Phase celebrated closing upstream `required_operators()` collapse while leaving the gate itself self-satisfied in the adoption contract.
- **HIGH — Split registration path is a standing mental-model tax.** Manifest → `register_typed` (no D-05); agent/task/workflow/prompt → explicit `register_versioned` in adopter code (`examples/05-workflow-hitl/run.py` prologue). Defense (“DESIGN says *where*, not *which path*”) is legally correct and pedagogically weak. Adopters will put workflow defs in the manifest, lose bump checks, and think they followed the docs. That is an ergonomics phase leaving an ergonomics cliff on the classes that matter most for audit.
- **MEDIUM — D-IMPL-81 open.** Manifest roles are governance; unpinned wiring document undercuts “dimension 2 is complete.”
- **MEDIUM — Day-1 still ~350 lines.** Mechanical win is real (143→13); remaining spine (MaxTTL, product class, lineage, gates, replay) is correctly left out — but published docs still describe pre-15 surface (A-3). Adoptability claim is ahead of the documentation.
- **MEDIUM — Schema HTTP route vs committed schemas mismatch** (`deferred-items.md`): six author-versioned schemas 404 from the route that enumerates `SDK_ARTIFACT_CLASSES`. Consistency trap for Phase 16.
- **LOW — Additive-only public API (0 removals).** Pre-1.0 freedom unused for cleanup; dual FQNs inflate the surface (A-1).
- **LOW — Process weight.** 21 plans + generated surface theater is justified for this phase’s risk class, but sets a precedent that every ergonomics pass needs the same apparatus.

## 6. What I would have done differently

1. **Ship the core in fewer plans:** `parse_artifact` classes → `load_and_boot` + D-IMPL-80 → operator builder → example rewrite of 00 + one complex example → then suite. Surface-diff machinery could ride a smaller close-out plan.
2. **Fix Gate 2 construction in examples** while rewriting: lineage from authored declaration (product-class / plan keys), `engine_resolved` from `execution`. One mutation test proving Gate 2 fails when they diverge.
3. **Unify registration under the manifest** with a per-class registration mode (`typed` | `versioned`) instead of “manifest can’t see author-versioned classes.” Same ergonomics win without the split.
4. **Pin or explicitly defer D-IMPL-81 before calling the abstraction line closed** on replay dimensions.
5. **Don’t claim “eight tautologies” as the strongest finding without saying the suite still self-satisfies Gate 2 at every `run_gates` call.** Honesty there would match the phase’s best discipline (A-4’s narrow claims).

## 7. Anything else

The phase’s real achievement is methodological: it treated “green tests” as hostile witnesses and built instrumentation that *cannot* sum removal with relocation. That discipline belongs in the project permanently.

The unease you should keep: **ergonomics succeeded by making governance seams more visible and more numerous** (`role`, typed vs versioned, pins vs artifacts, MaxTTL minting left in code). Visibility is good; cognitive load is the adoption tax now. Phase 16 docs either make that map legible in one page or adopters will invent helpers that erase it.

Also: Dave already approved (`D-GATE-15`). This review is whether that approval was earned. It was — with the HIGH items above still unpaid debt, not closed by the gate.

---

**Overall risk: MEDIUM**

Sound approach, real fidelity side-effects, measured adoptability win, and deliberate refusals where a bad ergonomics phase would have deleted INV-CH7-47. Risk stays medium because (a) Gate 2 independence is still example-broken, (b) the typed/versioned split will produce silent governance loss in the wild, and (c) the next convenience PR will try to cross the line the phase drew carefully in negative space.

---

## OLLAMA Review

### 1. Verdict on the Design Approach
**Sound.** 

The design is a disciplined exercise in "mechanical reduction." It targets the exact point where the *No-Hardcoding Rule* created a friction tax: the manual marshalling of artifacts into typed objects. By introducing `ccf.deployment` as a purely algorithmic wiring layer, the SDK has reduced the "day-1" integration noise without absorbing the governance logic (the gates) or the stateful transitions (the agent loop). It preserves the critical "independence of sources" required for the replay record and lineage checks.

### 2. Should this phase have shipped at all?
**Yes.** 

While 21 plans for "ergonomics" typically screams scope creep, the evidence justifies it. The project had a contradiction: it demanded high-fidelity, typed artifacts (Whitepaper Fidelity) but forced the adopter to write the glue code to realize those types in every single example (Adoptability). 

The phase did not trade fidelity for convenience; it traded *boilerplate* for *infrastructure*. By moving assertions and print summaries from examples into a dedicated test suite and automating the YAML-to-type path, it clarified what is actually "deployment code" versus "SDK overhead." This makes the SDK's surface area honest.

### 3. The Abstraction Line
The claim that it hid "NO governance decision" is **defensible**.

The "line" is drawn at the boundary between **assembling the machine** and **running the machine**. 
*   **Assembling:** Loading a manifest, pinning versions, and booting a handle. (Now in `ccf.deployment`).
*   **Running:** Executing operators, projecting context, and running validation gates. (Still in adopter code).

The specific prohibition of `ccf.products.gates` imports in the deployment package is the critical safeguard. If a helper like `load_and_boot` had also returned a "ValidatedProduct," it would have been forced to compute the lineage itself. This would have collapsed the observer and the observed into one call, making `lineage strict equality` a tautology. By returning a `BootedFabric` (which is just a bag of handles and pins), the SDK forces the adopter to still explicitly call the gates, preserving the "Two-Source" requirement for audit.

### 4. The Self-Satisfying-Check Finding
**Real and generalizable.**

This is the strongest justification for the phase. The "self-satisfying check" (comparing a value against itself) is a classic failure mode in security and audit systems. 

When artifacts were hand-marshalled in examples, the "declared" value and the "actual" value often originated from the same local variable in a 400-line script. The a-priori structure of `load_and_boot`—which separates the `parsed` artifacts (the declaration) from the `booted` fabric (the reality)—makes it impossible to accidentally use the same object for both sides of a gate.

Regarding the "over-claiming" gate (the rename-style bypass): this is a standard iterative refinement. The fact that the phase's own review process caught a local alias bypassing a rename-guard suggests the adversarial mindset was actually active, not just performative.

### 5. Concerns

*   **MEDIUM: The Registration Split.** The ruling to split `register_typed` (no bump check) and `register_versioned` (bump check) based on "nested vs. author-versioned" artifacts creates a cognitive fork. While the defense is that this is about *registration path* not *storage location*, a new adopter will ask: "Why does my Agent Definition need a manual version bump check but my Task Definition (also a Control Plane artifact) doesn't?" This is a leak in the mental model.
*   **LOW: Partial Registration State.** `load_and_boot` accepts that a failure mid-loop can leave partial state in the Control Plane. While the author argues that "rollback is worse than a retry," this could lead to "ghost" versions in the audit log that never actually participated in a successful boot.
*   **LOW: `BootedFabric.artifacts` visibility.** Returning all artifacts (including `role: load`) in the `artifacts` mapping is a convenience that slightly blurs the line between what is "pinned for replay" and what is "merely available." The docstring mitigates this, but it's a point of potential confusion.

### 6. What I would do differently
I would unify the registration paths. Instead of a "split ruling" based on artifact type, I would implement a `RegistrationPolicy` attached to the `ArtifactClass`. The `ManifestEntry` should simply trigger the class's own registration contract (either "Strict Version" or "Implicitly Versioned"). This removes the "mental model" inconsistency by making the behavior a property of the *type* rather than a choice of the *SDK's wiring function*.

### 7. Final Risk Assessment
**Overall Risk: LOW.**

The phase successfully removed a massive amount of "noise" from the adopter's path without introducing "magic" that obscures the whitepaper's invariants. The use of CI-enforced lints (`cinv02-deployment-gates`) to prevent the erosion of the abstraction line is the correct engineering response to the risk of "ergonomic creep." The project is now more adoptable without being less governed.

---

