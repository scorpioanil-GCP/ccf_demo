# Phase 15.4 — Deferred Items (live hand-off contract)

Maintained file: citations here are held true of the current tree by the
citation gate (`MAINTAINED_RECORDS` in `tools/lints/citations.py`). Amend in
place; inheriting plans and Phase 16 read this as authoritative.

Phase 15.4 carried its own debt in `docs/15.4-GATE-PACKAGE.md` §8. This file
holds the items found *during* execution that were out of the finding plan's
scope and therefore logged rather than fixed.

---

## DI-15.4-01 — The duplicated Fluree admit prefixes — **OPEN**

**Found during:** plan 15.4-03 (the writer split).

**What:** the entity and relationship admit-key prefixes are declared twice —
once in `src/ccf/graph/backends/fluree.py` and again, privately, in
`src/ccf/graph/backends/fluree_write.py`. Structurally the same shape as WR-01,
which D-14 ruled fixed in this phase, with a worse failure mode: a drifted
prefix makes the reachability walk's `all(...)` predicate false for every path,
so the symptom is an empty reached set returned with a 200 rather than an
error.

**Why it was not fixed here.** D-14 ruled on the policy key only, and plan
15.4-03's own discipline was that everything not named in the plan moves
verbatim — a 2,230-line relocation is exactly where an unannounced behaviour
change hides.

**What holds meanwhile.** The pair is held equal by a live server-reading test,
`tests/graph/test_fluree_backend.py::test_the_write_path_materializes_exactly_the_admit_keys_the_walk_pushes`,
whose docstring records that D-14 collapsed one pair and left this one.

**The fix, when someone takes it.** Import the two constants from the reader
the way `policy_key` is now imported. The write module already imports its
reader, so there is no cycle and no lint consequence.

---

## DI-15.4-02 — Line-anchored citation drift is wider than any one plan's scope — **OPEN**

**Found during:** plan 15.4-12 (the phase close), while repairing the citations
this phase moved.

**What, measured.** 45 line-anchored citations in gated (non-exempt) documents
name a source file phase 15.4 modified. Nineteen of those sit in the four
documents plan 15.4-12 owned and were measured against the phase base:

| Category | Count |
|---|---|
| Correct and unaffected by this phase | 5 |
| Shifted one line, still inside the symbol the citation names | 1 |
| Correct at the phase base, moved **by this phase** | 6 |
| Already stale **before** this phase began | 7 |

The six this phase moved are the quickstart plan / binder / `.execute(` triple,
cited twice in `.planning/REQUIREMENTS.md` — each moved down two lines when
D-10's `connection=` mapping replaced the per-database keyword in every
example. Three of the six were repaired in plan 15.4-12; the other three sit in
a bullet that a later bullet in the same document explicitly supersedes and
declares stale, so they were left as the dated record they are.

**Why this is a finding and not a lint failure.** The citation gate is green
and correctly so. It checks *anchored* citations — a backticked span adjacent
to the citation, or a `::`-qualified symbol reference. An unanchored citation
that names only a path and a line number gets arithmetic only: the line exists.
That limit is stated in the checker's own docstring; this measurement is what it
looks like when it bites, at scale.

**Why it was not fixed here.** Plan 15.4-12's declared scope is four documents,
and 7 of the 19 anchors in those four were already stale before phase 15.4
began — pre-existing drift, out of scope under the executor's own scope
boundary. The remaining 26 sit in documents no plan in this phase owns
(`docs/SURFACE-AUDIT.md`, several `tests/` modules, and two earlier phases'
`deferred-items.md`).

**The fix, when someone takes it.** Not a sweep of line numbers — that
regenerates the same debt on the next refactor. The durable move is the one
plan 15.1-19 started and plans 15.4-05 and 15.4-12 continued: migrate
line-anchored citations into source files to the `::`-qualified symbol form,
which `cite03-node-id` checks and which does not rot under a line shift. Plan
15.4-12's four migrations moved the checker's "checked and passing" count from
217 to 221 and its "anchor not resolvable" count from 14 to 12, so the
migration is measurable as it proceeds.

**One discipline note for whoever takes it.** Phase 15.2's own deferred-items
file records that a naive edit inserting lines near the top of a heavily-cited
document produced 124 citation-guard findings in one commit. Edit
line-number-neutrally, or migrate the citations first.
