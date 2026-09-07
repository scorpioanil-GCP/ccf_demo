# Reviewer instruction — Phase 24.8 close-time panel (CLAUDE.md §3.1)

You are one of several independent AI reviewers. The subject is the **shipped code** of Phase 24.8 of
the CCF SDK — `phase-24.8` at commit `d7c4946b`, diff base `8567d683` — **not** its plans. The plans
were reviewed before execution (`c5586450`, plan-checker VERIFICATION PASSED). The source is
**INLINED** in the bundle you were given on stdin; do not assume you can read the repository, and do
not report what you cannot see in the bundle.

## Before anything else

1. Quote, **verbatim**, the `READ-PROOF …` line from the bundle you received (it appears at the top,
   mid-payload and at the end). A review without it is void.
2. Read `known-findings.md` (K1–K12). Those findings are already recorded. **Do not re-derive them.**
   Your budget is for what is **ADJACENT** to each — the same defect class in a neighboring symbol,
   the seam a fix did not reach, the alternative reading the code admits.

## The phase, in one paragraph

The SDK held **two meanings of traversal**. An edge endpoint carrying no entity claim in the view —
an *unresolved reference* — was traversable by the in-process operator walk and not by the query
tier. Measured across six backends: on a chain `A → X → B` at `depth_limit=2` with
`admitted_entity_classes=None` the operator tier answered `{A,B}` where the query tier answered
`{A}`; on a bypass graph the operator tier answered `{A,B,C,D}` at depth 2 against `{A,C,D}`. Ten of
42 (graph, question) pairs diverged while all six pushed adapters agreed with the fallback on 252/252
backend-rows.

`D-IMPL-267` ruled the meaning (persisted graph state and traversal membership are **not the same
universe**; traversal semantics are **execution-path invariant**; an unresolved reference is never a
walk start, never a hop, consumes no depth, closes no cycle, and nothing is manufactured for it, and
its exclusion is **silent**). `D-IMPL-268` ruled the mechanism: **(i) close-then-walk inside
`_bounded_walk`** — construct the admitted entity universe, endpoint-close the working edge set
against it, then walk. Shared *semantics*, not a shared helper; no predicate promoted to a public
surface. The document went to **semantics version 1.3.0** with a `GQ-35` amendment entry, and
`content_hash(GraphQuery)` does not move because no field was added.

The whole phase changed **two `src/` files** and, by AST with docstrings stripped, **one definition**
(`src/ccf/operators/categories.py::_bounded_walk`).

## What to judge against

CLAUDE.md §10–§11: single-writer (only L2 writes L3), composition-preservation `(A∘B)(G) = A(B(G))`,
the three validation gates, Algorithmic ⇄ Semantic alternation, audit-by-construction, the
No-Hardcoding Rule, zero harness imports in `src/`, `extra=forbid` at every boundary,
hash-transparency on every defaulted contract field, and mechanism-not-values (no domain constants in
`src/`). Plus whitepaper fidelity: `GQ-*` clauses are the normative vocabulary; INV-CH7-20 (edges are
first-class claims, never derived joins); INV-CH7-24 (bounded typed expansion); INV-CH7-40
(`_substitute` prunes to reached endpoints).

## What to produce

A list of findings. For each:

- **Citation:** `path.py::Symbol` — module path relative to the repo root, then the class, function
  or method. A finding whose cited symbol does not exist in the bundle is **VOID** and will be
  recorded as a fabricated citation. Do not cite line numbers alone; the bundle has no line numbers.
- **Class:** `blocking` (a violated invariant, a whitepaper-fidelity defect, a replay/audit hole, a
  correctness or security defect, an unsurfaced architectural decision) or `advisory` (style, naming,
  sequencing, deferred scope).
- **Claim:** one paragraph, concrete and falsifiable, with the input or the sequence that exhibits
  it. If your claim is about a graph shape, give the shape.
- **Adjacency:** which known finding (K-number) it sits beside, if any.

Order findings blocking first. **If you find nothing blocking, say so explicitly.** Do not pad. Do
not restate the known findings as your own. Do not review `examples/`, `tests/examples/`,
`.planning/`, generated docs or the criteria — they are not in the bundle and are not the subject.

## The three questions most wanted (from `known-findings.md`)

1. **K1 / K9.1** — is there any **other** place in `src/` that walks persisted edges over a view it
   did not endpoint-close, or any **other** test that holds an operator to something weaker than
   `fallback.answer`?
2. **K9.2** — is there any **other** prose site in `src/` making a *current-rendering* claim about a
   versioned document (as opposed to an arrival note recording when a field appeared)?
3. **K11** — read `GQ-11` (walk-start selection) as it stands in the bundle. Can it be read, alone,
   to permit a claim-less URI as a walk start — i.e. does it need the cross-reference the amendment
   deliberately did not add?

## Reading order (recommended)

`bundle-src` (the diffstat → `categories.py` whole → `fallback.py` whole → the document regions → the
diff) → `bundle-tests-part-1` (the two new modules whole) → `bundle-tests-part-2` (the five changed
modules as diffs). **Each part is self-contained and carries its own read-proof; review the part you
were given and cite only what it contains.**
