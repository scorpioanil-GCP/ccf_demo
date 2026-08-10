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

---

## DI-15.4-03 — `CINV-04` names two different invariants — **OPEN, needs Dave's ruling**

**Found during:** the phase code review (finding WR-11), closed out in the
review-fix pass.

**What.** The repository's established `CINV-04` is
**replay-by-construction** — `docs/FEASIBILITY.md`, `docs/PHASE_I1_GATE.md`,
`docs/PHASE_I4_GATE.md`, `docs/PHASE_I5_GATE.md`,
`tests/invariants/test_replay_by_construction.py`, `src/ccf/hitl/__init__.py`,
and `src/ccf/hitl/approval_gate.py` all use it that way. This phase minted
`CINV-04 — no substrate name in core` for an unrelated rule, and registered the
rule ids `cinv04-substrate-name` / `cinv04-substrate-prose` under that badge. An
invariant identifier that resolves to two invariants makes every gate table,
traceability row and `D-GATE` citation using it ambiguous.

**One correction to the finding as written.** It suggests
`tests/invariants/test_single_writer_boot.py:1` is a *third* meaning. It is
not: `tests/invariants/test_replay_by_construction.py` names single-writer as
one of CINV-04's own legs, so that module's "CINV-04, single-writer leg" is the
established meaning used correctly. There are two meanings, not three.

**Why it was not fixed in the review-fix pass.** The code change is small — the
two rule ids and about a dozen prose lines across `tools/lints/` and
`docs/15.4-GATE-PACKAGE.md`. What is not small is that the identifier appears
in the gate tables Dave signs and in every one of this phase's twelve plans and
summaries, `.planning/ROADMAP.md`, and `15.4-VALIDATION.md`. Renaming it in the
gate package alone would hand Dave a document whose rule ids disagree with the
whole record behind it, and rewriting the record is not something a fix pass
should do to a phase's history. Allocating an invariant id is also a naming
decision on a list `CLAUDE.md` §3.1 enumerates.

**The fix, when Dave rules.** Allocate the next free id — `CINV-05` is free and
unambiguous — and change, in one commit: the rule ids in
`tools/lints/substrate_names.py`, the badge lines in `tools/lints/__init__.py`
and `tools/lints/__main__.py`, the two mentions in `tools/lints/allowlist.yaml`,
and `docs/15.4-GATE-PACKAGE.md`. Leave the phase's plans and summaries as the
dated record they are, and note the renumbering in the gate package so a reader
of the older documents can follow it. **Zero behavioural effect either way** —
this is identifier hygiene, and nothing about what the rule checks changes.

---

## DI-15.4-04 — `load_and_boot` runs adapter discovery three times and validates the connection twice — **OPEN**

**Found during:** the phase code review (finding IN-01).

**What.** `_preflight_adapter` calls `declared_names()` (one full metadata plus
directory scan) and then `resolve(declared)` (a second), and `boot()` calls
`resolve(backend)` again — so a manifest boot runs discovery three times and
the adapter's config-model validators twice.

**One thing already improved.** The CR-03 fix removed a *fourth* scan: `resolve`
used to re-read the entry-point set and index `[0]` into the matches, and now
uses the declaration `_declared()` already resolved.

**Why it is only Info.** Correctness-neutral: adapter config validators are pure
functions over a mapping. What it costs is the literal truth of "the adapter's
contract is validated once at the boundary", and an adapter with a
side-effecting validator would observe the repetition.

**Why it was not fixed.** The fix is a signature change — `boot()` accepting an
already-resolved `ResolvedBackend` and a validated config, or a second internal
entry point that does. That is public API surface, freshly broken once in this
phase under D-15B with a migration note owed and written. Breaking it a second
time in a review-fix pass, after the gate package was assembled, is worse than
carrying a repeated pure computation.

**The fix, when someone takes it.** Thread the resolved record and the validated
config from `_preflight_adapter` into `boot` through an internal entry point,
leaving the public `boot(backend=...)` signature alone.
