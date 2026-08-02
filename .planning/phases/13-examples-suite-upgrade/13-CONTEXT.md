# Phase 13: Examples Suite Upgrade - Context

**Gathered:** 2026-08-02
**Status:** Ready for planning

<domain>
## Phase Boundary

The eight v0.1 examples (00–07) become self-teaching: every example gets a
detailed narrated README, its definition artifacts are enriched to exercise
materially more SDK surface, the suite stays CI-green with a single
documented command per example, and the code/artifact boundary is visible
everywhere. Requirements: EXAM-01, EXAM-02, EXAM-03. Example 08 (the demo)
is out of scope except where suite-wide consistency touches it.

</domain>

<decisions>
## Implementation Decisions

### README narration format
- **D-01:** Rich README only — no per-example walkthrough docs. Phase 14
  mounts the READMEs directly; one file per example to keep in sync.
- **D-02:** Fixed section template across all eight READMEs, identical
  order: What this demonstrates → Run it → The story → Artifact-by-artifact
  → Whitepaper/CLAUDE.md sections exercised → What to change first → What
  would fail.
- **D-03:** Content shown by path reference plus tiny excerpts (≤8 lines)
  only where narration needs them. No mkdocs include machinery (`--8<--`)
  in READMEs — they must render clean on GitHub today.
- **D-04:** Audience is an engineer new to CCF: general engineering terms
  (CI, YAML, SQLite) need no gloss; every CCF term (Context Product, L1–L6,
  half-life, replay, …) gets a one-line gloss on first use with a
  whitepaper-section link.

### Scenario enrichment strategy
- **D-05:** Keep each example's current domain and deepen it in place — no
  re-theming (preserves D-IMPL-52's horizontal mix; expected-output diffs
  stay attributable to enrichment alone).
- **D-06:** REQUIRED: example 01 (agent-basics) exercises all six channel-1
  specialization axes meaningfully — archetype binding, context contract,
  perspective, policy regime, half-life/debt profile, instruction bindings.
- **D-07:** Half-life/debt behavior, temporal operators, and HITL variants
  (OverrideBoundary, ReviewQueue) are opportunistic: the planner places them
  where a scenario absorbs them naturally; no forced scenarios.
- **D-08:** Artifacts-first enrichment. run.py files change only where a
  new artifact field needs interpreting — "richer demo without touching
  code" is itself the teaching point (No-Hardcoding boundary).

### Expected-output churn policy
- **D-09:** Per-example atomic commits: an example's enrichment and its
  regenerated expected output land in ONE commit whose body summarizes what
  changed in the output and why. Each regeneration is thereby a reviewed,
  deliberate event (EXAM-03).
- **D-10:** Every README documents the exact regeneration command for its
  expected output, with an explicit warning that regeneration is a reviewed
  event. No `make regen-*` targets — regeneration stays deliberate.

### Adaptation guidance format
- **D-11:** Dual delivery: each README ends with a concrete "Adapt it"
  section naming the exact artifact file + keys to edit for a new domain,
  AND artifacts carry brief header comments marking user-editable vocabulary
  vs structural keys (comments survive copy-paste).
- **D-12:** Boundary visibility verified by narration + existing
  enforcement: the artifact-by-artifact README section is a table with a
  "yours to edit vs mechanism" column; the existing No-Hardcoding CI lint
  remains the hard enforcement. No new tooling.

### Claude's Discretion
- Which specific examples absorb the opportunistic surfaces (D-07).
- Exact wording/ordering inside the fixed template sections, and how much
  excerpting each README needs (within the ≤8-line rule).
- Whether example 08's README gets a light retrofit to the same template
  for suite consistency (nice-to-have, not required).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification and invariants
- `CLAUDE.md` §6.2 (six specialization axes — D-06 target), §6.4
  (No-Hardcoding Rule — governs D-08/D-12), §9 (examples suite discipline:
  runnable end-to-end, code+artifacts side by side, README-per-example,
  horizontal domain mix per D-IMPL-52)
- `docs/CCF_Whitepaper_1-2.md` — section links cited in README glosses
  (D-04); §7.7 half-life/debt for D-07 scenarios

### Prior art to match
- `examples/08-e2e-demo/README.md` — the README quality bar this phase
  scales to 00–07 (structure inspiration; note D-03 forbids its walkthrough's
  include machinery in READMEs)
- `docs/demo-walkthrough.md` — narration style reference only
- `.planning/phases/12-synthetic-data-demonstration/12-REVIEWS.md` — cross-AI
  consensus: section-scoped excerpts over full-file dumps; documented
  regeneration workflow (feeds D-03/D-10)
- `.planning/phases/12-synthetic-data-demonstration/12-HUMAN-UAT.md` — UAT
  note on unexplained jargon (feeds D-04)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing READMEs (57–103 lines each) already have "Run it" + invariant
  tables — the template (D-02) extends rather than replaces their shape.
- `make example-NN` targets + `make examples` aggregate + expected-output
  byte-compare harness already exist for all examples; CI wiring needs no
  change (EXAM-03's "single documented command" is already true; Phase 13
  documents it per README).

### Established Patterns
- Byte-compared expected outputs per example — every artifact enrichment
  regenerates them (drives D-09).
- No-Hardcoding lint + harness-import lint + `@algorithmic` lint run in CI
  and enforce the real code/artifact boundary (D-12 leans on this).

### Integration Points
- Phase 14 (Documentation Suite) mounts these READMEs into mkdocs — D-01/
  D-03 keep them mount-ready without include machinery.

</code_context>

<specifics>
## Specific Ideas

- "The lesson is that the demo got richer without code changes" — D-08's
  framing should appear in READMEs where enrichment was artifact-only.
- UAT feedback from Phase 12: don't assume CCF context; the reader is an
  engineer thinking about the demo, not the repo's infrastructure. Glosses
  are cheap; confusion is not.

</specifics>

<deferred>
## Deferred Ideas

- Per-example walkthrough docs with literal includes (08-style) — revisit in
  Phase 14 if mkdocs wants deeper pages than the READMEs.
- `make regen-example-NN` convenience targets — rejected for now to keep
  regeneration deliberate (D-10); reconsider if churn becomes frequent.
- Worked before/after adaptation diffs per example — vivid but heavy; a
  candidate for one flagship example in Phase 14.
- README template-sections CI check (headings grep) — cheap insurance noted
  during discussion; planner MAY include it but it was not required.

</deferred>

---

*Phase: 13-examples-suite-upgrade*
*Context gathered: 2026-08-02*
