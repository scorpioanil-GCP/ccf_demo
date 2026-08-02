# Phase 13: Examples Suite Upgrade - Research

**Researched:** 2026-08-02
**Domain:** Documentation + definition-artifact enrichment of the existing v0.1 examples suite (00–07)
**Confidence:** HIGH (all findings verified against the local codebase; no external dependencies)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**README narration format**
- **D-01:** Rich README only — no per-example walkthrough docs. Phase 14 mounts the READMEs directly; one file per example to keep in sync.
- **D-02:** Fixed section template across all eight READMEs, identical order: What this demonstrates → Run it → The story → Artifact-by-artifact → Whitepaper/CLAUDE.md sections exercised → What to change first → What would fail.
- **D-03:** Content shown by path reference plus tiny excerpts (≤8 lines) only where narration needs them. No mkdocs include machinery (`--8<--`) in READMEs — they must render clean on GitHub today.
- **D-04:** Audience is an engineer new to CCF: general engineering terms (CI, YAML, SQLite) need no gloss; every CCF term (Context Product, L1–L6, half-life, replay, …) gets a one-line gloss on first use with a whitepaper-section link.

**Scenario enrichment strategy**
- **D-05:** Keep each example's current domain and deepen it in place — no re-theming (preserves D-IMPL-52's horizontal mix; expected-output diffs stay attributable to enrichment alone).
- **D-06:** REQUIRED: example 01 (agent-basics) exercises all six channel-1 specialization axes meaningfully — archetype binding, context contract, perspective, policy regime, half-life/debt profile, instruction bindings.
- **D-07:** Half-life/debt behavior, temporal operators, and HITL variants (OverrideBoundary, ReviewQueue) are opportunistic: the planner places them where a scenario absorbs them naturally; no forced scenarios.
- **D-08:** Artifacts-first enrichment. run.py files change only where a new artifact field needs interpreting — "richer demo without touching code" is itself the teaching point (No-Hardcoding boundary).

**Expected-output churn policy**
- **D-09:** Per-example atomic commits: an example's enrichment and its regenerated expected output land in ONE commit whose body summarizes what changed in the output and why. Each regeneration is thereby a reviewed, deliberate event (EXAM-03).
- **D-10:** Every README documents the exact regeneration command for its expected output, with an explicit warning that regeneration is a reviewed event. No `make regen-*` targets — regeneration stays deliberate.

**Adaptation guidance format**
- **D-11:** Dual delivery: each README ends with a concrete "Adapt it" section naming the exact artifact file + keys to edit for a new domain, AND artifacts carry brief header comments marking user-editable vocabulary vs structural keys (comments survive copy-paste).
- **D-12:** Boundary visibility verified by narration + existing enforcement: the artifact-by-artifact README section is a table with a "yours to edit vs mechanism" column; the existing No-Hardcoding CI lint remains the hard enforcement. No new tooling.

### Claude's Discretion
- Which specific examples absorb the opportunistic surfaces (D-07).
- Exact wording/ordering inside the fixed template sections, and how much excerpting each README needs (within the ≤8-line rule).
- Whether example 08's README gets a light retrofit to the same template for suite consistency (nice-to-have, not required).

### Deferred Ideas (OUT OF SCOPE)
- Per-example walkthrough docs with literal includes (08-style) — revisit in Phase 14 if mkdocs wants deeper pages than the READMEs.
- `make regen-example-NN` convenience targets — rejected to keep regeneration deliberate (D-10).
- Worked before/after adaptation diffs per example — candidate for one flagship example in Phase 14.
- README template-sections CI check (headings grep) — planner MAY include it but it was not required.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXAM-01 | Every v0.1 example (00–07) has a detailed narrated README — what it demonstrates, artifact-by-artifact explanation, whitepaper/CLAUDE.md sections exercised, "what to change first" | Current-state audit below (README lengths 57–103 lines; existing shape already partially matches the D-02 template). Example 08's README is the quality bar; template mapping documented in Architecture Patterns. |
| EXAM-02 | Scenarios enriched to exercise more SDK surface through richer definition artifacts; code stays thin per No-Hardcoding | Per-example surface inventory below identifies which axes/surfaces each example already exercises and where enrichment headroom lives (D-06 target for 01; D-07 opportunistic placements). OverrideBoundary and ReviewQueue exist in `src/ccf/hitl/` and are currently unexercised by any example. |
| EXAM-03 | Suite stays CI-green with single documented command per example; expected-output change is a reviewed event | Verified: `make example-NN` targets exist for 00–08 plus `make examples` aggregate; `ci = ci-core + examples`. CRITICAL nuance: only example 08 has a byte-compared `expected_output.txt`; examples 00–07 assert against `expected` blocks embedded in their own artifacts (see Pitfall 1). |
</phase_requirements>

## Summary

This phase is documentation-and-artifact work on an existing, green, fully wired examples suite. No new libraries, no new tooling (D-12 forbids it), no infrastructure change. The research questions were entirely codebase-archaeology: what does the suite look like today, what does each example already exercise, where does the "expected output" actually live, and what does the 08 quality bar consist of. All answers were obtained by direct inspection — confidence is HIGH throughout and the Assumptions Log is empty.

The single most planning-relevant discovery: the CONTEXT.md claim of a suite-wide "expected-output byte-compare harness" is precise only for example 08 (`artifacts/expected_output.txt`, regenerated via the run itself). Examples 00–07 instead carry `expected:` blocks inside their own YAML artifacts (mostly `controlplane.yaml`, plus `skills.yaml`/`hitl.yaml`/`scenario.yaml`) and `run.py` asserts against them at runtime. So D-09/D-10 "regeneration" for 00–07 means *hand-updating the `expected` block in the same artifact commit as the enrichment* — the README's documented "regeneration command" is really "run `make example-NN`, read the assertion failure, update the `expected` block deliberately." Plans must not invent a byte-compare harness for 00–07; that would be new tooling (D-12) and out of scope.

**Primary recommendation:** Plan one task per example (eight tasks, parallelizable), each producing README rewrite + artifact enrichment + updated `expected` blocks in one atomic commit (D-09), preceded by one shared task that fixes the exact README template skeleton and gloss vocabulary so all eight land consistent, and followed by a suite-wide `make ci` verification task.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| README narration (EXAM-01) | Docs (`examples/NN/README.md`) | — | D-01: single file per example, GitHub-renderable, Phase-14 mount-ready |
| Scenario enrichment (EXAM-02) | Definition artifacts (`examples/NN/artifacts/*.yaml`) | `run.py` only where a new artifact field needs interpreting (D-08) | No-Hardcoding Rule: values in artifacts, interpreters in code |
| Expected-output integrity (EXAM-03) | Artifacts (`expected:` blocks; 08's `expected_output.txt`) | `run.py` assertions (unchanged) | Existing harness; no new tooling per D-12 |
| CI green | Existing `Makefile` targets + CI wiring | — | Already complete; phase only *documents* commands per README |
| Boundary enforcement | Existing CI lints (No-Hardcoding, harness-import, `@algorithmic`) | README "yours to edit vs mechanism" table (D-12) | Narration is soft surface; lints are hard enforcement |

## Current-State Inventory (verified by inspection)

### Suite shape [VERIFIED: codebase]

| Example | README lines | Artifacts | Where `expected` lives | Extra code files |
|---------|-------------|-----------|------------------------|------------------|
| 00-quickstart | 82 | controlplane, events, halflife, ontology | `controlplane.yaml` | — |
| 01-agent-basics | 81 | agent, analysis_output, controlplane, events, ontology, prompt | `controlplane.yaml` | — |
| 02-skilling | 80 | agent, controlplane, events, ontology, skills | `controlplane.yaml`, `skills.yaml` | — |
| 03-harness-portability | 103 | agents/order_insights, controlplane, events, harnesses, live, ontology, prompt | `controlplane.yaml` | `legs/` (deterministic, live, ollama_client) |
| 04-cross-process | 81 | a2a, agent, controlplane, events, ontology, prompt | `controlplane.yaml` | `producer_child.py` |
| 05-workflow-hitl | 80 | agent, hitl, prompt, scope_mapping, task, tokens, workflow | `hitl.yaml` (`expected_gate`) | — |
| 06-decision-replay | 86 | agent, controlplane, events, hitl, ontology, prompt, scope_mapping, skills, task, tokens, workflow | `controlplane.yaml`, `skills.yaml`, `hitl.yaml` | — |
| 07-artifact-store-mcp | 57 | controlplane, events, ontology, store_file, store_mcp | `controlplane.yaml` | `mcp_store_child.py` |
| 08-e2e-demo | 54 | agent, controlplane, expected_output.txt, halflife, ontology, prompt, scenario, skills | `expected_output.txt` (byte-compared) + `scenario.yaml` checksums | `generator.py` |

### Run commands [VERIFIED: Makefile]

- `make example-NN` for each (03 runs `--mode deterministic`; live legs `example-03-live-ollama`/`-anthropic` are opt-in, never CI).
- `make examples` runs all nine in order, stopping on first failure. `make ci` = `ci-core + examples` and is the phase gate (Makefile comment cites plan 08-12, D-10/D-12 of that phase).
- EXAM-03's "single documented command per example" is already TRUE mechanically; the phase work is *documenting it in each README* with the D-10 regeneration warning.

### Existing SDK surface available for D-07 opportunistic enrichment [VERIFIED: src/]

- `src/ccf/hitl/override.py` (OverrideBoundary) and `src/ccf/hitl/review_queue.py` (ReviewQueue) exist with tests (`tests/hitl/test_review_queue.py`) but are exercised by **no example** — natural landing spots: 05 (workflow already has ApprovalGate + ExceptionEscalation) or 06 (replay already captures HITL).
- Half-life/debt: `halflife.yaml` exists only in 00 and 08; example 01's agent already binds a debt-profile ref (`forced_llm_threshold`, `fail_closed_threshold`) — headroom to make the profile *observably matter* in 01's run, satisfying D-06 "meaningfully."
- Example 01's `agent.yaml` already declares all six axes structurally with per-axis comments — D-06's gap is *meaningful exercise* (each axis visibly changes behavior/output) and README narration, not artifact scaffolding.
- Example 05/06 already carry Phase-10 tenant-authorization surface (`scope_mapping.yaml`, `tokens.yaml`, deny-by-default 403) — READMEs must narrate this per the phase dependency note.

## Standard Stack

No new packages. **Package Legitimacy Audit: not applicable — this phase installs nothing.** Existing tooling in use: Python 3.12, Make, pytest, the repo's own CI lints. Slopcheck protocol skipped for that reason.

## Architecture Patterns

### README template (D-02, fixed order)

```markdown
# examples/NN-name — one-line hook (EXAM/req tag)
## What this demonstrates        # incl. CCF-term glosses w/ whitepaper links (D-04)
## Run it                        # `make example-NN` + raw python fallback + regen warning (D-10)
## The story                     # narrated flow; ≤8-line excerpts only, path refs otherwise (D-03)
## Artifact-by-artifact          # TABLE with "yours to edit vs mechanism" column (D-12)
## Whitepaper / CLAUDE.md sections exercised
## What to change first          # a.k.a. "Adapt it" — exact file + keys (D-11)
## What would fail               # which assertion/gate/lint fires if you break the boundary
```

Note: existing READMEs (e.g., 05, 08) already open with a hook paragraph, have "Run it", "What it exercises", "What to change first" — the template *extends* their shape (per CONTEXT code-context). 08's README is the prose-quality bar but its final section links `docs/demo-walkthrough.md`; per D-01 the upgraded 00–07 READMEs must be self-contained, no walkthrough companion.

### Artifact header-comment convention (D-11)

Example 01's `agent.yaml` already models the style: header comments citing CLAUDE.md sections and D-IMPL numbers, plus per-axis inline comments. Extend with an explicit editable/structural marker, e.g.:

```yaml
# [ADAPT] domain vocabulary — safe to change for your domain
# [MECHANISM] structural keys interpreted by the factory — do not rename
```

(Exact marker wording is Claude's discretion; keep it consistent across all eight examples.)

### Enrichment workflow per example (drives task structure)

1. Enrich artifacts (new fields/values within current domain, D-05).
2. Run `make example-NN`; assertion failures reveal which `expected` blocks changed.
3. Update `expected` blocks deliberately; re-run green.
4. Rewrite README to template; add artifact header markers.
5. One commit: artifacts + expected + README, body summarizing output delta (D-09).

### Anti-Patterns to Avoid

- **Building a byte-compare harness for 00–07** — new tooling, violates D-12; the `expected`-block pattern is the existing harness.
- **Re-theming an example's domain** — violates D-05 and makes output diffs unattributable.
- **Inline prompt or domain value sneaking into run.py during "interpreting a new field"** — No-Hardcoding lint will fire; D-08 permits only interpreter code.
- **mkdocs `--8<--` includes or >8-line excerpts in READMEs** — violates D-03.
- **Adding `make regen-*` targets** — explicitly rejected (D-10, deferred list).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Output verification | New snapshot/byte-compare framework | Existing `expected` blocks + run.py assertions; 08's expected_output.txt | D-12: no new tooling |
| Boundary enforcement | README-lint or artifact schema checker | Existing No-Hardcoding / harness-import / `@algorithmic` CI lints | Already enforced; narration is additive |
| HITL variants for D-07 | New primitives | `src/ccf/hitl/override.py`, `review_queue.py` (shipped, tested, unexercised) | Exercising existing mechanism IS the requirement |

## Common Pitfalls

### Pitfall 1: Assuming a uniform byte-compare harness
**What goes wrong:** Plans written against CONTEXT's "expected-output byte-compare harness ... for all examples" would create regen commands that don't exist for 00–07.
**Reality:** Only 08 byte-compares a file. 00–07 assert against `expected:` YAML blocks inside their artifacts at runtime.
**How to avoid:** Each README's D-10 "regeneration" section names the example's actual mechanism: for 00–07, "edit the `expected` block in `<file>` after reviewing the run's assertion output"; for 08, the checksum re-pin + expected_output.txt regeneration already documented.
**Warning signs:** A plan task saying "regenerate golden files" for examples 00–07.

### Pitfall 2: Enrichment breaking cross-example or test coupling
**What goes wrong:** `tests/examples/test_demo_generator.py` and conformance tests (`tests/conformance/test_harness_portability.py`) consume example artifacts/outputs; artifact enrichment can break tests outside the example's own run.
**How to avoid:** Phase-gate verification runs `make ci` (ci-core + examples), not just `make examples`. Per-example tasks should run the full `make ci` before their atomic commit, or at minimum grep tests for references to the example's artifacts.

### Pitfall 3: D-06 satisfied structurally but not "meaningfully"
**What goes wrong:** Example 01 already declares all six axes; a plan could mark D-06 done without behavior change.
**How to avoid:** For each axis, the run's narration/output must show the axis *doing something* (e.g., perspective changing the projection view; debt threshold visibly gating). Success test: README's "What would fail" names a concrete failure per axis if it were removed/misconfigured.

### Pitfall 4: Gloss inconsistency across eight READMEs
**What goes wrong:** Eight independently written READMEs gloss "Context Product" or "half-life" eight slightly different ways, and cite different whitepaper sections.
**How to avoid:** A shared Wave-0 task fixes the template skeleton AND a gloss table (term → one-line gloss → whitepaper §) that all example tasks copy from. This also enables parallel per-example execution without drift.

### Pitfall 5: Example 03's live legs and pycache noise
**What goes wrong:** Enriching 03 could accidentally touch the live-leg path (never CI) or commit `__pycache__` files (currently present in the tree under examples/03, 04, 08).
**How to avoid:** 03 enrichment targets the deterministic leg only; check `.gitignore` covers `__pycache__` before committing example directories.

## Code Examples

Existing style exemplars, all in-repo (no external sources needed):
- README quality bar: `examples/08-e2e-demo/README.md` (hook → run → exercised → change-first structure).
- Artifact commenting bar: `examples/01-agent-basics/artifacts/agent.yaml` (per-axis comments citing CLAUDE.md §6.1/§6.2, D-IMPL refs).
- Narration style: `docs/demo-walkthrough.md` (style reference only — do not replicate include machinery, D-03).
- Expected-block pattern: `examples/00-quickstart/artifacts/controlplane.yaml` `expected:` key consumed at `run.py:352–359`.

## Project Constraints (from CLAUDE.md)

- **No-Hardcoding Rule (§6.4):** no prompts/agent definitions/thresholds in code — applies to `/examples`; enrichment is artifacts-only per D-08. CI lint enforces.
- **§9 examples discipline:** runnable end-to-end with a single documented command, code + artifacts side by side, README per example, horizontal domain mix (D-IMPL-52) — D-05 preserves domains.
- **Whitepaper citations:** READMEs cite whitepaper sections for CCF-defined mechanism and CLAUDE.md sections for SDK extensions; where the two disagree, the whitepaper wins.
- **Phase discipline:** this is Phase-I-adjacent work under gsd; commits at deliverable boundaries (one per example, D-09). No force-push to main; `commit_docs: true`.
- **Fable 5 high effort** is the CLAUDE.md model directive for research/design phases.
- Example 08 is out of scope except suite-consistency touches (phase boundary; its README retrofit is discretionary).

## State of the Art

Not applicable — no external ecosystem. The relevant "state of the art" is the repo's own Phase 12 output: 12-REVIEWS.md consensus (section-scoped excerpts over full-file dumps; documented regeneration workflow) and 12-HUMAN-UAT.md (gloss unexplained jargon), both already folded into D-03/D-04/D-10.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (empty — all claims verified against the local codebase) | | |

## Open Questions

1. **Does any example beyond 08 need an actual regeneration *command* vs an edit workflow?**
   - What we know: 00–07 have no generated output files; 08 regenerates expected_output.txt via its own run.
   - Recommendation: READMEs for 00–07 document the edit-the-expected-block workflow with the D-10 warning; only 08's README documents a literal regeneration command. Planner should phrase D-10 compliance per-example accordingly.
2. **Which examples absorb OverrideBoundary / ReviewQueue (D-07, Claude's discretion)?**
   - Recommendation: ReviewQueue fits 05 (a ContentGeneration-adjacent review step) or 06 (adds a fourth HITL dimension to replay); OverrideBoundary fits 06 best (original output + override both in the replay record is the replay example's whole point). Planner decides during task design; do not force both into one example.
3. **Deferred-but-permitted README headings CI check** — planner MAY add a trivial headings grep to `ci-core`; cheap insurance for template drift across eight files. Optional.

## Environment Availability

Skipped — no external dependencies. The phase edits Markdown and YAML and runs the existing Python 3.12 suite already exercised by CI (`make ci` verified present in Makefile).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, `tests/` tree) + Make-driven example runs |
| Config file | existing repo config (no change) |
| Quick run command | `make example-NN` (per touched example) |
| Full suite command | `make ci` (= ci-core + all nine examples) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXAM-01 | README present with all seven D-02 sections, per example | manual review (+ optional headings grep) | `grep -c '^## ' examples/NN/README.md` style check | optional new — planner discretion |
| EXAM-02 | Enriched artifacts run green; code unchanged except interpreters | smoke | `make example-NN` per example; No-Hardcoding lint via `make lint`/`ci-core` | ✅ existing |
| EXAM-03 | Suite green, single command documented, expected changes reviewed | e2e | `make ci`; commit-per-example review (D-09) is process, manual | ✅ existing |

### Sampling Rate
- **Per task commit:** `make example-NN` + `make lint` for the touched example.
- **Per wave merge:** `make examples`.
- **Phase gate:** `make ci` green before `/gsd:verify-work`.

### Wave 0 Gaps
- None in test infrastructure. Recommended Wave 0 *content* task (not a test gap): shared README template skeleton + CCF gloss table (term → gloss → whitepaper §) so eight parallel example tasks stay consistent (Pitfall 4).

## Security Domain

Minimal footprint — no new inputs, endpoints, or dependencies. Two touchpoints:
- Examples 05/06 carry the Phase-10 hardened auth posture (bearer tokens, D-16 signed principal binding, tenant-scope mapping, deny-by-default 403). Enrichment must NOT weaken these fixtures; READMEs should narrate them as demonstrated security posture (phase dependency note: "hardened postures demonstrated").
- `artifacts/tokens.yaml` files contain example credentials — keep them obviously synthetic; never introduce real-looking secrets while enriching (CLAUDE.md §2.2: never a secret in the tree).

ASVS categories otherwise not applicable (documentation phase; V5 input validation is handled by existing artifact schema validation, unchanged).

## Sources

### Primary (HIGH confidence — direct codebase inspection, 2026-08-02)
- `examples/00`–`08` file trees, READMEs, `run.py` assertion code, `agent.yaml`/`controlplane.yaml` contents
- `Makefile` example targets and `ci` composition
- `src/ccf/hitl/` module listing (override.py, review_queue.py present)
- `.planning/phases/13-examples-suite-upgrade/13-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/config.json`
- `CLAUDE.md` (§6.2, §6.4, §9, §2.2)

## Metadata

**Confidence breakdown:**
- Current-state inventory: HIGH — every file verified by inspection
- Enrichment placement recommendations: HIGH mechanism-existence, MEDIUM placement (discretionary per D-07)
- Pitfalls: HIGH — Pitfall 1 (expected-block vs byte-compare) confirmed against run.py source

**Research date:** 2026-08-02
**Valid until:** stable — valid until any example or Makefile change lands (revalidate `expected`-block locations then)
