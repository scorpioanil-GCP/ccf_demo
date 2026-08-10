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

## DI-15.4-03 — `CINV-04` names two different invariants — **RULED, RENAME DEFERRED**

> **D-GATE-15.4 (Dave, 2026-08-09): the split is approved — allocate `CINV-05`
> for the no-substrate-name rule. The rename itself is deliberately deferred to
> a single coordinated pass across code *and* record**, for exactly the reason
> given under "Why it was not fixed in the review-fix pass" below: renaming the
> code alone leaves a document whose rule ids disagree with the history behind
> it. The decision is now settled and only the execution is outstanding, so the
> next pass has no ruling to wait on — it has a scope to cover. See "The fix,
> when Dave rules" below for that scope; it stands as written, with the addition
> that `.planning/ROADMAP.md` and `15.4-VALIDATION.md` get a pointer note rather
> than a rewrite, and that this gate entry and `D-GATE-15.4` are the two places
> a reader of the older documents will be sent.

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

---

## DI-15.4-05 — An out-of-tree adapter cannot be written from the public surface — **OPEN DESIGN ITEM (D-GATE-15.4)**

**Found during:** plan 15.4-10 (the out-of-tree adapter), reported as finding 1
and deliberately not fixed there.

**Ruled at the gate.** Dave, 2026-08-09: this stays open as a **design item for
a later cycle**, not a defect to close inside a gate. It is the one thing in
this phase that is a real gap rather than a rough edge, and wedging a fix into
the phase close would have papered over it.

**What.** `tests/fixtures/ccf-demo-adapter` — the distribution that proves the
whole phase — reaches for six names that are not exported:

| Name | Module | Why it is not avoidable |
| --- | --- | --- |
| `materialize_view` | `ccf.graph.reader` | no public equivalent |
| `_ordered_view` | `ccf.graph.reader` | cannot be replaced without forking the ordering convention the helper exists to hold |
| `_entity_records` | `ccf.graph.reader` | no public counterpart, so `entity_history` is unimplementable from public names |
| `_relationship_records` | `ccf.graph.reader` | same, for `relationship_history` |
| `_LineageRowsFor` | `ccf.graph.reader` | same |
| `_GraphTxn` | `ccf.graph._writer` | the write seam every adapter satisfies |

**The two true statements, and how they bound each other.** `D-11`'s claim holds
**exactly as written** — no line of `src/ccf` changed for the adapter to work,
measured with `git diff --quiet` over the arrival window and shown falsifiable.
*And* the surface an adapter must reach for is not the public surface. The
second does not contradict the first; it bounds how much the first proves. Zero
substrate cost was demonstrated. A supported authoring path was not.

**What was done instead of fixing it.** `public/how-to/write-a-graph-backend-adapter.md`
states the gap plainly rather than implying the public surface suffices. That is
the honest interim posture: an author who follows the guide will not be
surprised, and the guide does not make a promise the SDK cannot keep.

**Why it is genuinely a design question.** The public `BaseGraphReader` is
SQL-shaped, which is why a dict-backed store cannot use it — so "export the six
names" is the wrong framing. The real question is what the *supported* adapter
authoring surface should be: a reader base that is not SQL-shaped, a documented
Protocol set with the ordering convention expressed rather than inherited, or a
narrower published subset. That is a Phase D shape, with `D-IMPL-NN` entries,
not an export list.

**Interacts with:** `DI-15.4-01` (the Fluree admit prefixes are the same
question one layer down — knowledge an adapter needs that has no owner) and the
PyPI naming collision recorded in `docs/15.4-GATE-PACKAGE.md` §11.2, which
blocks the natural `dependencies = ["ccf"]` an adapter author would write.

**Narrowed, not closed — 2026-08-09, by the close-fix for finding F6.** The
gap had a second direction the entry above does not name: as well as six
*private* names an adapter must reach for, there was one *public* name that
under-declared what the runtime requires. `ccf.graph.protocols.GraphWriter`
declared two upserts and no `close()`, while the composition root calls
`close()` on shutdown and only a `BaseGraphWriter`'s `close` releases the
graph. An author writing to the documented public Protocol therefore produced
a writer that booted once and left the graph unbootable for the process
lifetime. F6 closed that one instance from both sides: `GraphWriter` now
declares `close()` with its lifecycle obligation, and
`ccf.graph._writer.adopt_writer` refuses a returned writer that is not a
`BaseGraphWriter` — so the declaration and the enforcement agree.

**What that changes for this item, stated precisely so it is not read as more
than it is.** The six-name table above is untouched; every one of those names
is still private and still unavoidable. What changed is the *class* of the
remaining gap. It is now entirely "private names an adapter must reach for",
with no remaining case of "a public name that says less than the runtime
requires" known. The design question — what the supported authoring surface
should be — is unchanged and still open.
