# Phase 22: The Adoption Argument — What RAG, Hand-Rolled Assembly and a Semantic Layer Lack - Context

**Gathered:** 2026-08-23
**Status:** Ready for planning

<domain>
## Phase Boundary

**One published Concepts page, plus the standing gate that keeps it honest.** The
page names RAG over a vector store, hand-rolled context assembly, and a semantic
layer plus prompt templates, and states what each lacks **against cited shipped
mechanism** — with the UBO question as its worked demonstration and the
passage-anchor honesty caveat carried. Discharges `DOCS-15`.

**Dave's framing, verbatim, at the discuss sitting:** *"Phase 22 is still 'one page
+ the gate that keeps it honest,' not a tooling phase. That is consistent with a
focused DOCS-15 discharge."*

**Not in this phase:** `DOCS-12`, `DOCS-13`, `DOCS-14`, `DOCS-17`, `CLNT-17`,
`EXAM-02`. No SDK surface — `src/` and `runtime/` stay diff-empty. No example tree
is created, moved or removed. No repo-wide rhetoric linter.

</domain>

<decisions>
## Implementation Decisions

### Citation standard — what "cited shipped mechanism" means (settled FIRST, per Dave's order)

- **D-01: Literal snippet includes (`--8<--`) are the FLOOR for every code-backed
  claim**, the same pattern the adopter's guide uses. Prose that merely names a
  symbol is NOT enough for `DOCS-15`'s *"cited shipped mechanism"* — Dave: *"reviewers
  will reject as essay."* The floor is already proven live: `check_paths: true` in
  `mkdocs.yml` makes **both** a missing snippet file **and** a missing named section
  fail the strict build, and `tools/docs_tests/test_snippet_gate.py` is the negative
  control that exercises each failure mode separately (it exists because at the
  extension's default BOTH failures build clean at exit 0, emitting an empty code
  block — a silently blank page).

- **D-02: Every "what the alternative lacks" claim is RECAST as a checkable fact
  about the QUESTION, never asserted as a capability limit of a tool.** Dave's
  ruling: *"'No document in any source system states Jane's 30.0%' is verifiable
  against `events.yaml` and `source-estate.yaml` — includable. 'RAG can't do this'
  is not."* The page shows what the question demands and what CCF's gated path
  does; **the reader draws the inference.** Rationale on the record: an uncited
  "lacks" sentence is the same defect class as `DCD-02` — a strong-looking claim
  with nothing to open.
  - **Do:** include checkable facts from `s1-01` artifacts and spine; show CCF
    mechanism via `--8<--`; let structure imply the gap.
  - **Don't:** write *"RAG cannot…"* / *"a semantic layer lacks…"* as naked
    assertions; blend mechanism and contrast in one unmarked paragraph; rely on
    typography alone to carry uncited persuasion.

- **D-03: Paired contrast is a bounded FALLBACK, not the house style.** Where a
  contrast genuinely cannot be recast as a question-fact, it may sit adjacent to
  the shipped mechanism that provides the missing property, with the citation on
  the CCF half — **each such case called out, and it must not become the page's
  main pattern.**

- **D-04: A wording gate SHIPS WITH THE PAGE, in the
  `tools/docs_tests/test_gate_two_wording.py` shape.** One module, **two
  obligations**: (1) no sentence asserts a capability limit of an external approach
  without grounding — residual `D-03` pairings must still not read as naked *"X
  can't Y"*; (2) no published page claims CCF extracts passage anchors from
  documents (the `16-13` honesty caveat). **Non-vacuity floors and
  injected-violation controls are mandatory so the gate cannot pass by matching
  nothing.** Dave's reasoning, verbatim: *"A stretch goal means that standard is
  enforced only by reviewer diligence — the same pattern that let unevidenced
  Completes and vacuous checks ship for years. Phase 22 should not reintroduce it
  on the page that exists to model honest citation."* And: *"if the criterion
  matters, something can go red when it is violated."*

- **D-05: The gate is `public/`-scoped** (or the minimal path set the existing
  wording gate already walks). It does **not** expand into a repo-wide rhetoric
  linter.

- **D-06: A per-claim symbol-resolver test is STRETCH and NON-BLOCKING.** It is not
  a substitute for `D-04`. If the phase has room it lands; if not it is **named as
  owed rather than skipped silently.**

### Demo subject and the CLNT-17 coupling (settled SECOND)

- **D-07: The page cites `s1-01` for the UBO demonstration AND the client surface
  (`ccf.client`, the `hw1` two-transport example) for the hand-rolled-assembly
  contrast.** That contrast is about the **seam**, not the graph, and `s1-01` does
  not demonstrate it well. Both subjects are already gated; neither is in the
  `00`–`08` set condemned by `DOCS-17`.

- **D-08: NO new includes are added against `examples/00`–`08` or
  `examples/external/00-hello-context`.** Those trees already carry 111 references
  across 15 published pages, 102 of them snippet includes, and every one is
  re-cut work owed by `DOCS-17`. This page adds none.

- **D-09: The page is a declared `CLNT-17` DEPENDENCY.** `examples/s1-01-hello-context-product`
  cannot be removed until this page is re-pointed or its demonstration re-homed.
  This is recorded in writing **and** lands mechanically: `public/` is one of the
  three trees `tools/retirement_sweep.py` walks, so the page's references become
  coupling rows in `docs/surface/examples/RETIREMENT-COUPLINGS.md` owned by
  `17-08`, with no one having to remember. **Regenerate that report LAST after any
  `.planning/` or `public/` write.**

- **D-10: The client surface is cited in PROSE, not by snippet include — and that
  is a deliberate choice, not an oversight.** The `hw1` trees carry **zero snippet
  section markers**, so an include against them would have to be whole-file:
  `examples/hw1-companies-over-revenue/consume.py` is 79 lines and
  `examples/hw1-harness-clients/client_*.py` are 186 / 288 / 237 lines. Adding
  markers to `hw1` is example work and is **out of scope for this phase.** Prose
  citation of `src/ccf/client/…` symbols is already gated: `public` is in the
  citation lint's `GATED_TREES` (`tools/lints/citations.py:153-159`), so a cited
  path must exist and a cited symbol must resolve. **If the planner concludes an
  include against `hw1` is necessary, that is a scope question for Dave, not a
  quiet widening.**

### Where the page lives, and what it is called (settled THIRD)

- **D-11: It is a Concepts page.** Not a new top-level section, not folded into the
  65-line `public/index.md`, and not buried inside the 447-line adopter's guide.
  Dave's reasoning: *"First-time readers can hit Concepts without finishing the
  tutorial; a top-level 'Why CCF' is optional later if the page earns it."*

- **D-12: The title names the QUESTION, not the rival** — e.g. *"What a governed
  answer requires"* or *"Answers no document contains"*. A title naming RAG would
  promise exactly the naked assertion `D-02` bars the body from making, and the
  `D-04` gate would then be policing a claim the title had already made. Exact
  wording is the planner's, within this constraint.

- **D-13: The page is added to the `nav:` tree in `mkdocs.yml`** under Concepts.
  Placement within that section is the planner's.

### Coverage of the argument (locked to a DEFAULT by Dave, not discussed)

- **D-14: Exactly the THREE alternatives `DOCS-15` names.** No fourth unless
  `DOCS-15` is explicitly expanded — *"Revisit only if discuss surfaces a must-have
  fourth that changes the requirement row."* None did.

- **D-15: The staleness / forced-LLM claim rests ONLY on what `s1-01` already
  measures** — Context Debt rising with staleness and crossing this deployment's
  Forced-LLM band (0.035 `ok` → 0.221 `forced_llm`). **`examples/s1-02-freshness-and-debt`
  is NOT invented in this phase**; `16-08` intended it and it was never built. If
  `s1-01`'s measurement will not carry the claim, the claim is **narrowed or
  dropped** — not backed by new example work.

### Claude's Discretion

- Exact page title within the `D-12` constraint; the page's internal section
  order; which of `s1-01`'s seven spine regions and twenty artifacts are included
  and in what order; placement within the Concepts nav; the wording gate's exact
  pattern vocabulary and module name.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The requirement and its sequencing
- `.planning/REQUIREMENTS.md:40` — the `DOCS-15` row: the four things the page must
  do, and the measured basis of its `Not built` verdict (both greps over `public/`
  return zero).
- `docs/DECISIONS.md:508` — `D-IMPL-176`, Dave's four numbered sequencing points.
  Point 1 puts `DOCS-15` first; point 2 is replacements-before-removals; point 4
  frees `s3-` and frames `DOCS-12/13/14/15` as **one documentation workstream** —
  recorded and deferred, not taken up here.
- `.planning/phases/21-requirement-ledger-reconciliation-what-is-actually-discharge/21-FINDINGS.md` §2
  — the scoped work list, Group B: what closing `DOCS-15` means, in one line.
- `.planning/ROADMAP.md` — the Phase 22 entry (added by hand 2026-08-23 per `D-15`).

### The citation machinery this phase must conform to and extend
- `mkdocs.yml` — `check_paths: true` (the whole of `D-08`), and the `nav:` tree the
  new page joins.
- `tools/docs_tests/test_snippet_gate.py` — the negative control proving a missing
  file AND a missing named section each fail the strict build. **Read its module
  docstring before assuming includes are safe.**
- `tools/docs_tests/test_gate_two_wording.py` — **the shape `D-04` copies**:
  sentence-scoped negative assertion, positive characterization assertion, two
  non-vacuity floors, injected-violation controls, an unmodified-copy control, and
  a false-positive control proving a bare enumeration is not an offender.
- `tools/lints/citations.py:153-159` — `GATED_TREES` includes `public`; a cited
  path must exist as written and a cited symbol must resolve.
- `tools/docs_tests/test_no_stale_example_paths.py` — every prose path reference and
  every snippet include resolves on disk.
- `tools/docs_tests/test_documented_commands_exist.py` — every documented `make`
  target exists.

### The subject
- `examples/s1-01-hello-context-product/README.md` — the UBO demonstration in the
  author's own words, including the sentence this page is the published expansion
  of: *"It answers a question a vector store over chunked documents structurally
  cannot."*
- `examples/s1-01-hello-context-product/spine.py` — **seven snippet marker regions**
  (`boot, ingest, operators, project, gate, record, serve`), the same seven the
  adopter's guide includes from `00-quickstart`.
- `examples/s1-01-hello-context-product/artifacts/ubo-question.yaml` — the question's
  vocabulary as a Control Plane statement; its header argues the *callable, not
  configurable* point that separates CCF from a semantic layer plus prompt templates.
- `examples/s1-01-hello-context-product/artifacts/expected.yaml`,
  `events.yaml`, `source-estate.yaml` — the declared answers and the signal they
  follow from. **`expected.yaml`'s header states why it exists: so the output test
  has a source for its expectations other than itself.**
- `tests/examples/test_s1_01_output.py` — the assertions that keep the numbers true;
  the established pattern for citing a RESULT is to include the declared output and
  name the test that asserts it.
- `examples/hw1-companies-over-revenue/`, `examples/hw1-harness-clients/` — the
  client surface, and `public/how-to/run-agents-cross-process.md:197-202`, the one
  published page that references it today.

### The honesty caveat
- `docs/DECISIONS.md:81` — `D-IMPL-46`, the `PassageCitationProvider` Protocol: the
  **contract ships**.
- `.planning/phases/16-documentation-rewrite-the-deterministic-path-the-adoption-ar/abandoned/16-13-PLAN.md:241-245, 275`
  — the caveat's original wording and its gate shape. **Pattern 5 (unstructured
  ingestion) was never built, so no shipped pipeline produces passage anchors from
  documents.** The page must not say CCF extracts passage anchors from your
  documents. This is the one place a rival (RAG) has a genuine strength, and the
  page is most exposed exactly there.

### Project law
- `CLAUDE.md` §6.4 (No-Hardcoding Rule), §9 (examples discipline), §3.1 (the close
  protocol), §17 (how to talk to Dave).
- `docs/DECISIONS.md` — `D-15` (`.planning/STATE.md` and `.planning/ROADMAP.md` are
  hand-edited; no `state.*` / `roadmap.*` writer), `D-GATE-19` (Success Criteria
  exist before Wave 1, never authored retroactively), `D-27` (partial retirement
  forbidden), `D-IMPL-178` (the close panel reads the shipped tree, inlined).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`s1-01` was built to be included from and nothing has ever included from it.**
  Seven spine marker regions, twenty documented definition artifacts carrying
  `[ADAPT]` / `[MECHANISM]` markers, and an output test. **This page can be a pure
  `public/` addition with ZERO changes under `examples/`.**
- **The wording-gate shape is proven in-repo.** `test_gate_two_wording.py` is ~10
  tests and already solves the hard parts: sentence-scoping (a negation in a
  different sentence does not exonerate), non-vacuity, and false positives.
- **The result-citation pattern is established**: include the declared output
  artifact, name the test that asserts it (`public/tutorial/demo-walkthrough.md:84,
  300`; `public/tutorial/adopters-guide.md:202, 332, 367`).

### Established Patterns
- **Strict Diátaxis.** Tutorial / How-to / Concepts / Reference, and **none of the
  four is a home for persuasion** — which is why `D-11` and `D-12` matter: the page
  earns its place by being about the question, not about the rivals.
- **Publication is default-deny by existence** (`D-01`): `public/` is the only tree
  mkdocs reads.
- **Every published page currently sources its code from the condemned `00`–`08`
  trees** — 102 snippet includes across 15 pages — and **zero published pages
  mention `s1-00` or `s1-01`.** This page is the first to cite the `s1-*` trees, so
  it starts the replacement direction (`D-IMPL-176` point 2) rather than adding to
  the re-cut burden.

### Integration Points
- `mkdocs.yml` `nav:` — the Concepts section gains one entry.
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — regenerated LAST; the page's
  `s1-01` references become coupling rows owned by `17-08`. **Run the sweep with
  `.venv/bin/python`, never the system `python3`** (see Specifics).
- `.planning/REQUIREMENTS.md` — the `DOCS-15` row is verdicted at the close, and any
  new rows this phase mints are minted in wave 1 and verdicted **before** the close
  panel reads the tree, on the `RECON-` / `VAC-` precedent.

</code_context>

<specifics>
## Specific Ideas

- **A live trap found during this discussion, and the planner must not fall into
  it.** `tools/retirement_sweep.py` imports test modules and *executes* their scan
  functions to count witnesses, swallowing failure at **four** sites — `:789`
  (*"a module that will not import yields no rows"*), `:973` (`if module is None:
  continue`), `:982` (*"an unrunnable scan yields no row"*) and `:1111`/`:1124`
  (*"unmeasurable, not a witness"*). Run the sweep with the system `python3` and
  `joserfc` is missing, three modules fail to import, **six coupling rows vanish
  silently**, the tool prints a confident `238 coupling rows` and exits 0, and the
  staleness gate then reports the CORRECT committed report as stale. **Always
  `PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report`.**
  The tool cannot tell *"there is no coupling"* from *"I could not look"* — this
  project's own check-vacuity class, in a tool that decides what is safe to delete.
  **Recorded as a finding; fixing it is `CLNT-17`/`DOCS-17` machinery and is OUT OF
  SCOPE here.**
- The page's opening should be the UBO question itself, not a claim about CCF.
  `s1-01`'s README already has the sentence the page expands.
- Dave's success-criterion flavour, for the criteria author: *"Every empirical claim
  on the page is either a snippet include from a CI-gated source or a checkable
  statement about the UBO question's artifacts; no sentence asserts a capability
  limit of an external approach without that grounding."*

</specifics>

<deferred>
## Deferred Ideas

- **The one-documentation-workstream framing.** `D-IMPL-176` point 4: the published-pages
  limb across `DOCS-12/13/14/15` is *"one documentation workstream, not four
  independent pages projects — plan it as one surface for the examples that actually
  shipped."* Recorded; **Dave's point 1 sequences `DOCS-15` first and alone**, and this
  phase honours the sequencing. The remaining three are a future phase.
- **Snippet markers for the `hw1` trees** (`D-10`) — example work, would make the
  client surface includable rather than prose-cited. Belongs with `DOCS-14`/`EXAM-02`.
- **`examples/s1-02-freshness-and-debt`** (`D-15`) — `16-08`'s intended λ_c / D_c
  demonstration, never built.
- **A top-level "Why CCF" section** (`D-11`) — *"optional later if the page earns it."*
- **The retirement sweep's silent-drop defect** (see Specifics) — `CLNT-17` /
  `DOCS-17` machinery.
- **A per-claim symbol-resolver test** (`D-06`) — stretch within this phase; if it
  does not land it is named as owed.

</deferred>

---

*Phase: 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se*
*Context gathered: 2026-08-23*
