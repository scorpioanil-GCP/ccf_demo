# Phase 13 — Shared README Template, Gloss Table, Marker Convention

**Status:** Phase-internal reference (planning material — never shipped).
Wave-2 executors copy headings, glosses, markers, and regeneration
phrasing from this file **verbatim**. Nothing here is re-derived
downstream; if a wording change is needed, it changes here first and
propagates to all eight examples in the same wave.

Decisions realized: D-02 (fixed section template), D-03 (path refs +
excerpts of 8 lines or fewer, no include machinery), D-04 (gloss every
CCF term),
D-10 (regeneration is a reviewed event, no `make regen-*`), D-11
(artifact header markers), D-12 (yours-to-edit vs mechanism visibility).

---

## Part 1 — Template skeleton (D-02)

Title line, exact form:

```markdown
# examples/NN-name — <one-line hook>
```

Then **exactly these seven `##` headings, verbatim, in this order** —
these are verbatim-copy targets, character for character:

```markdown
## What this demonstrates
## Run it
## The story
## Artifact-by-artifact
## Whitepaper / CLAUDE.md sections exercised
## What to change first
## What would fail
```

**Hard rule: exactly seven `##` headings per README, no additions and no
omissions.** Any extra content an example wants (a further-reading
pointer, a domain rationale, a security note) is plain prose under one
of the seven existing sections — never a new `##` heading. Downstream
verify commands assert `grep -c '^## ' examples/NN-name/README.md`
equals 7; an eighth heading is a verification failure, not a style
choice. (`###` sub-headings are permitted inside a section if needed,
but prefer prose and tables.)

Per-section guidance:

- **What this demonstrates** — 1–2 paragraphs. Names the mechanism the
  example proves, not the domain story. Every CCF term gets its
  one-line gloss from Part 2 on first use, with the section link
  (D-04). General engineering terms (CI, YAML, SQLite) need no gloss.
- **Run it** — the `make example-NN` command in a fenced block, the raw
  fallback `PYTHONPATH=src:runtime python examples/NN-name/run.py`, what
  exit code 0 means, and the per-example regeneration warning paragraph
  from Part 4 (D-10).
- **The story** — the narrated flow of the run: what the artifacts
  declare, what the code interprets, what the fabric does, in order.
  Content is shown by **path reference** (e.g., "see
  `artifacts/controlplane.yaml`, key `product_class`") plus excerpts of
  **8 lines or fewer** only where the narration needs the literal text.
  No mkdocs include machinery (no snippet-include directives of any
  kind) — READMEs must render clean on GitHub today (D-03).
- **Artifact-by-artifact** — a table, one row per artifact file, with
  exactly these columns (D-12):

  ```markdown
  | Artifact | What it declares | Yours to edit vs mechanism |
  ```

  The third column states, per file, which keys are `[ADAPT]` (domain
  vocabulary, safe to change) and which are `[MECHANISM]` (structural
  keys the factory interprets — do not rename), matching the header
  markers inside the artifact (Part 3).
- **Whitepaper / CLAUDE.md sections exercised** — a short bullet list.
  Whitepaper sections for CCF-defined mechanism; CLAUDE.md sections for
  SDK extensions, marked "SDK extension". Use only section numbers that
  exist (see the verified cites in Part 2).
- **What to change first** — the "Adapt it" section (D-11): the exact
  artifact file(s) and the exact keys to edit to move the example to a
  new domain, and what the reader should expect to see change on the
  next run.
- **What would fail** — a two-column table per the examples/05 pattern:

  ```markdown
  | Invariant | What would fail here |
  ```

  One row per invariant the example enforces; the second column names
  the concrete assertion, gate, or lint that fires if the boundary is
  broken.

---

## Part 2 — CCF gloss table (D-04)

Copy the gloss **verbatim** on a term's first use in a README, with the
cite as a parenthetical. All whitepaper section numbers below were
verified against `docs/CCF_Whitepaper_1-2.md` on 2026-08-02. The
whitepaper numbers headings at the `§N.N` level only; where CLAUDE.md
cites finer-grained numbers (e.g., §7.10.1), this table cites the
verified `§N.N` heading, naming the subsection where useful. Terms that
exist only in CLAUDE.md cite CLAUDE.md and are marked **SDK extension**.

| Term | One-line gloss | Cite |
| --- | --- | --- |
| Context Product | A typed, validated, replay-ready unit of decision context the fabric derives and serves — a contract, not a stored record | whitepaper §6.3 (specification), §7.6 (delivery) |
| Context Graph | The fabric's typed state `G(E, R, T, P, Π, L)` — entities, relationships, time, policy, projection, and lineage as one governed graph | whitepaper §5.2 (definition), §7.3 (mechanism) |
| L1–L6 layers | The fabric's six layers: L1 signal ingestion → L2 assembly (the only writer) → L3 graph → L4 operators → L5 projection → L6 product delivery | whitepaper §7.1 |
| Context Operators | Typed, composable, read-only functions over the graph in four categories — Traversal, Temporal, Policy, Similarity | whitepaper §7.4 |
| Projection (Π) | The role-conditioned transformation that turns graph state into the view a given consumer is entitled to see | whitepaper §7.5 |
| Context Half-life (λ_c) | A per-observation-type decay rate declaring how fast context goes stale — a Control Plane value, never code | whitepaper §7.7 |
| Context Debt (D_c) | The quantified shortfall when freshness or completeness drops below threshold; elevated debt gates Forced-LLM and Fail-Closed behavior | whitepaper §7.7 ("`D_c` Formulas") |
| Decision Replay record | The five-dimension record (fabric snapshot, policy bindings, model version, perspective conditioning, generation path) that lets a decision be reproduced exactly | whitepaper §7.10 ("The Five-Dimension Replay Record") |
| Control Plane / Data Plane | The Control Plane declares what the fabric may do (versioned config, policy, artifacts — also the audit plane); the Data Plane executes within those constraints | whitepaper §7.8 |
| MCP integration | Model Context Protocol as an integration surface — Pattern 3 in the whitepaper; bidirectional (ingress and egress) in the SDK | whitepaper §8.3 (Pattern 3); CLAUDE.md §7.1 (SDK extension: bidirectional) |
| A2A federation | Agent-to-Agent exchange of Context Products across process or organizational boundaries, with Control Plane admission verification on the consumer side | whitepaper §8.3 (Pattern 4); CLAUDE.md §7.2 (SDK extension: first-class in v0) |
| Archetype vs agent | An archetype is a functional template the SDK ships as code; an agent is a declared, versioned Control Plane artifact the Agent Factory produces from one | CLAUDE.md §6.1 — SDK extension |
| Specialization axes / skilling | Channel 1 fixes who the agent is (six axes: archetype, context contract, perspective, policy regime, half-life/debt profile, instruction bindings); channel 2 — skilling — governs what it can currently do | CLAUDE.md §6.2 — SDK extension |
| No-Hardcoding Rule | No prompts, agent definitions, thresholds, or routing values in code — code is interpreters and factories; everything specific lives in versioned artifacts, CI-lint enforced | CLAUDE.md §6.4 — SDK extension |
| ApprovalGate | The HITL primitive that suspends a workflow until a named human approves or rejects — the action lands in the replay record by construction | CLAUDE.md §8.2 — SDK extension |
| ExceptionEscalation | The HITL primitive that routes a workflow state to a designated human role when a condition (e.g., a `D_c` breach) is met | CLAUDE.md §8.2 — SDK extension |
| OverrideBoundary | The HITL primitive at which a human substitutes a value the agent would have produced — original output and override both land in replay | CLAUDE.md §8.2 — SDK extension |
| ReviewQueue | The HITL primitive for asynchronous human review of generated content before release, integrated with passage-level lineage | CLAUDE.md §8.2 — SDK extension |
| ArtifactStore | The Protocol-based persistence surface for CCF artifacts (snapshots, products at rest, replay records, Control Plane bundles), with file-backed and MCP-backed reference implementations | CLAUDE.md §7.4 — SDK extension |

Citation rule for the "sections exercised" README section: whitepaper
cites are `whitepaper §N.N`; SDK-extension cites are `CLAUDE.md §N.N`.
Where the two describe the same surface, cite both, whitepaper first —
where they disagree, the whitepaper wins.

---

## Part 3 — Artifact header-marker convention (D-11)

Every enriched artifact file carries these two marker comment lines in
its header block, **with this exact wording, identical across all eight
examples**:

```yaml
# [ADAPT] domain vocabulary — safe to change for your domain
# [MECHANISM] structural keys interpreted by the factory — do not rename
```

Rules:

- Markers are YAML comments only — they survive copy-paste and are
  invisible to every parser and schema validator.
- The header block states the convention once; individual keys or
  sections may additionally be tagged inline with `# [ADAPT]` or
  `# [MECHANISM]` where the boundary is not obvious from the header.
- The README's Artifact-by-artifact table (Part 1) mirrors the same
  split in its third column, so the boundary is visible in both places
  (D-12). The hard enforcement remains the existing No-Hardcoding CI
  lint — the markers are narration, not tooling.

---

## Part 4 — Per-example regeneration warning phrasing (D-10)

**No `make regen-*` targets exist, and none will be added.** The string
`make regen` must appear in a README only inside a statement that such
targets do not exist (or not at all). Regeneration stays deliberate.

### (a) Examples 00–07 — the edit-the-expected-block workflow

Examples 00–07 have no generated golden files. Their expected outcomes
live in `expected:` blocks inside their own definition artifacts, and
`run.py` asserts against them at runtime. Canonical paragraph — copy
into each README's "Run it" section, substituting `NN` and the file
name(s) from the table below:

> **Expected-output changes are a reviewed event.** If you enrich the
> artifacts, run `make example-NN`, review the assertion output, then
> deliberately edit the `expected:` block in `<file>` to match what you
> reviewed — regeneration is a reviewed event, landed in the same
> commit as the enrichment, with the commit body summarizing what
> changed in the output and why.

Which artifact file(s) hold the `expected` blocks, per example:

| Example | `expected`-block file(s) |
| --- | --- |
| 00-quickstart | `artifacts/controlplane.yaml` |
| 01-agent-basics | `artifacts/controlplane.yaml` |
| 02-skilling | `artifacts/controlplane.yaml`, `artifacts/skills.yaml` |
| 03-harness-portability | `artifacts/controlplane.yaml` |
| 04-cross-process | `artifacts/controlplane.yaml` |
| 05-workflow-hitl | `artifacts/hitl.yaml` (`expected_gate`) |
| 06-decision-replay | `artifacts/controlplane.yaml`, `artifacts/skills.yaml`, `artifacts/hitl.yaml` |
| 07-artifact-store-mcp | `artifacts/controlplane.yaml` |

### (b) Example 08 only — literal regeneration workflow

Example 08 is the one example with a byte-compared golden file. Its
README keeps the workflow already documented there: change
`artifacts/scenario.yaml`, re-pin the scenario generation checksums,
and regenerate `artifacts/expected_output.txt` from the run — as a
reviewed event, landed in the same commit as the scenario change. Do
not retrofit the 00–07 paragraph onto 08, and do not invent a
byte-compare harness for 00–07 (that would be new tooling, D-12).
