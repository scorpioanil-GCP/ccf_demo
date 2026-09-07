# Phase 24.8 — known findings and discretion choices (do NOT re-derive)

Everything below is already recorded. **Spend no budget re-deriving it.** Your budget is for what is
**ADJACENT** to each item — the same defect class in a neighboring symbol, the seam a fix did not
reach, the alternative reading the code admits. Each item ends with the adjacent question actually
being asked.

The phase in one line: **the SDK held two meanings of traversal.** An edge endpoint carrying no
entity claim in the view (an *unresolved reference*) was traversable by the in-process operator walk
and not by the query tier. `D-IMPL-267` ruled the meaning; `D-IMPL-268` ruled the mechanism. One
function changed.

---

## K1 — The mechanism was RULED, not chosen by the executor

`D-IMPL-268`, Dave, verbatim: *"The in-process operator conforms by endpoint-closing its working edge
set against the claimed/admitted entity universe before `_bounded_walk` traverses it. The semantic
rule is shared across tiers; implementation reuse is not required. No new public helper or SDK
surface is introduced solely to share the predicate."*

Two alternatives were measured (42/42 rows each, `24.8-RESEARCH.md` § Priority 7) and **rejected by
ruling**:

- **(ii) a claimed-adjacency guard** — filter at the hop rather than at the edge set.
- **(iii) a shared private predicate, or promoting `fallback.py::_endpoint_closure` to a public
  helper both tiers import.**

`src/ccf/operators/categories.py` therefore does **not** import `ccf.graph.fallback`
(`grep -c` → 0), by design. Do not file "the closure logic is duplicated" as a finding — it is the
ruling.

**ADJACENT:** the two tiers now express the same rule in two places. Is there any *third* place in
`src/` that walks persisted edges over a view it did not close — the engine's survivor-cap branch,
`planner.py`'s compose/cache paths, any operator that consumes a raw `as_of` view in-process? Name
the symbol.

## K2 — `TARGET_CLASS` intermediates in-process vs `MID_CLASS` in the corpus

`tests/operators/test_traversal_unresolved_reference.py` builds its bypass with the intermediate
nodes carrying the *target* class; `tests/conformance/query_corpus.py::unresolved_reference_cases`
uses a distinct mid class. Deliberate: the in-process module is judging depth assignment with
`admitted=None`, where class does not filter; the corpus case must also exercise the admitted path.

**ADJACENT:** does any admitted-set question exist on this shape where the two conventions would give
different answers, and would either module notice?

## K3 — The curated case is ontology-oriented (`guarantees` B→X), not the research's A→X→B chain

`tests/fixtures/banking/edge_graphs.yaml`'s `unresolved-reference` case draws its edge from the
banking ontology's own relationship vocabulary rather than reproducing the research chain literally.
The corpus strategy *does* keep A→X→B (see K4).

**ADJACENT:** the curated set is what `test_composition.py`'s 25-ordered-pair law and
`test_staged_vs_direct.py` draw from. Does the ontology orientation exercise the same code path in
`_substitute` that the chain does?

## K4 — The corpus stores `X -> B` subject-first, deliberately unlike `chain_claims`

`chain_claims` uses `seed -> mid <- target`. Under that orientation a *forward* walk would stop at
the unresolved endpoint under every implementation, and the directed half of D-07 could not
discriminate. The new strategy stores `X -> B` forward. This is criterion 14's explicit requirement.

**ADJACENT:** are there other corpus strategies whose orientation makes one of the two directions
non-discriminating for the property they exist to test?

## K5 — The cycle test is non-discriminating under the shipped walk, and it has a sabotage for that

`test_the_cycle_answers_as_the_chain_does` compares G2 (G1 + `X -> A`) to G1. Because X is excluded,
G2 *is* G1 for traversal purposes — so the test would pass under any implementation that excludes X,
including one that got the depth story wrong. Its live-ness is carried by a planted-placeholder
sabotage, not by the assertion alone.

**ADJACENT:** which other assertion in these two modules is trivially true given the fix, and is its
liveness carried by a control?

## K6 — The twin-provenance check is trivially true today, because `mint_provenance` is view-independent

Criterion 9's silence proof compares `OperatorOutput.provenance` on the dangling graph to a
fully-claimed twin's, byte for byte under `canonical_bytes`. Provenance today is minted from
parameters, not from the view — so the equality holds for reasons that have nothing to do with the
fix. That is exactly why the annotate sabotage
(`test_control_a_provenance_annotation_is_not_silent`) was made *conditional* during planning
revision B-2: an unconditional annotation would have reddened the instrument in both states and
proven nothing.

**ADJACENT:** if provenance ever becomes view-dependent, this check starts measuring something
different without anyone noticing. Is there a cheaper invariant that would state the intent —
"exclusion emits nothing" — independently of how provenance is minted?

## K7 — The byte-level control operates at depth 3

`test_the_byte_check_is_byte_level` reorders the operator's output tuples in a scratch copy: the URI
sets stay equal and the bytes differ, so the differential must red. It is exercised at depth 3, where
the answer has enough members to reorder.

**ADJACENT:** does the differential's byte comparison have a depth or a shape at which two different
answers could canonicalize identically?

## K8 — The wave-1 instruments were committed STRICT-RED on purpose

Plans 01 and 02 committed failing tests (`12 failed, 18 passed, 21 skipped`; `11 failed, 262
passed`) against a tree whose `git diff 8567d683 -- src runtime` was **empty**. That is what makes
those reds observations about the *shipped* walk. The transient red between wave 1 and wave 2 is by
design, not a defect.

**ADJACENT:** nothing — this is process, and it is stated so a reviewer does not report a red commit
as a defect.

## K9 — The research roster missed three bare-`_walk` oracles, and named a fourth site that does not exist

Two separate roster defects, both found by measurement rather than by reading:

1. `24.8-RESEARCH.md` § F-2 named only
   `tests/operators/test_traversal_admission.py::test_the_fallback_walk_agrees_with_the_operator` as
   an oracle holding an operator to the bare `fallback.py::_walk`. `test_traversal_direction.py`
   carried **three more** (`:250`, `:308`, `:768`). Found by the plan checker; all four re-derived to
   `fallback.answer` in plan 05.
2. RESEARCH § Priority 6 item 4's nine "semantics version" sites name
   `src/ccf/graph/protocols.py:281` / the `TraversalSpec` docstring, classified as an *arrival note
   that stays true*. That docstring carries **no `semantics version` token at all**. The only such
   site in `protocols.py` is the **module docstring at `:35`**, and it is a *current-rendering*
   claim — *"render the normative vocabulary of `docs/GRAPH_QUERY_SEMANTICS.md` (semantics version
   1.0.0) as frozen values"* — now three amendments stale. Carried OPEN as `24.8-C-02`; criterion 19
   requires `protocols.py` to carry an empty diff, so it could not be fixed in-phase.

**ADJACENT — this is the question the panel is most wanted on:** does any **other** test in the tree
still hold an operator to something weaker than `fallback.answer` — a bare `_walk`, a hand-rolled
expectation, a set comparison where the differential wants bytes? And is there any **other** prose
site in `src/` making a *current-rendering* claim about a versioned document (not an arrival note)?
Name the symbol or the file and line.

## K10 — Two measured-vs-stated differences, reported and not adopted

- Plan 03 measured **393** line-anchored `GRAPH_QUERY_SEMANTICS.md:NNN` citations where research
  reasoned 392, and **244** below `:201` where research reasoned ~230. Reported as differences.
- The close record measured a **+38** citation delta on the merged tree (431 total) where the
  executor brief carried +26 (419). Re-measured, per-file breakdown summing to 38, recorded as a
  difference. All 38 are new cites in the phase's own six changed files.

**ADJACENT:** none for the panel; stated so a reviewer does not report the arithmetic as inconsistent.

## K11 — The amendment deliberately did NOT add a cross-reference to `GQ-11`

`GQ-11` is walk-start selection. The 1.3.0 amendment states the universe→close→walk rule in `GQ-10`,
`GQ-13` and `GQ-16` and leaves `GQ-11` alone, because criterion 2 requires the edit to be
**line-neutral** and `GQ-11` sits between `GQ-10` and `GQ-13`.

**ADJACENT:** read `GQ-11` as it stands (it is in the bundle at `:221`, cited from `_bounded_walk`'s
docstring). Does its seed-selection wording now need the unresolved-reference cross-reference the
amendment chose not to add — i.e. can `GQ-11` be read, alone, to permit a claim-less URI as a start?

## K12 — Carries, all OPEN, none fixed in-phase

- **`24.8-C-01`** — unresolved-reference observability (should the fabric expose that a traversal
  excluded references — a count, a Debt input, a replay dimension?). Deferred at the design sitting
  (`D-IMPL-267` Q4). Criterion 9 requires exclusion to be **silent** and criterion 20 forbids partial
  implementation, so any work here would have violated two locked criteria.
- **`24.8-C-02`** — the `protocols.py:35` stale rendering claim (K9.2).
- **The `CLAUDE.md` pin** — `test_determination_authority_disclosure_delivery.py::
  test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]` is RED and **pre-existing**: it
  pins `CLAUDE.md` against `1022ad59` (24.6's base) while `CLAUDE.md` last moved at `4683f245`
  (24.6's close). Criterion 20 forbids a `CLAUDE.md` edit here.

**ADJACENT:** none — these are Dave's to rule. Do not propose fixes for them.

---

## What the panel is NOT asked about

`.planning/` (criteria, plans, SUMMARYs, the close record), `examples/` and `tests/examples/` (frozen
under `D-IMPL-261`, diff-empty), generated `docs/schemas` and `docs/surface`, `archive/`, `public/`.
None is in the bundle; any finding about them is out of scope.
