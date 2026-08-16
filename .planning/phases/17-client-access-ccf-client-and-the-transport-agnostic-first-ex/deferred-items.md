# Phase 17 — deferred items

Out-of-scope discoveries. Logged, not fixed, per the scope boundary: only
issues directly caused by the current plan's changes are auto-fixed.

---

## DEF-17-01 — citation-coverage ratchets red on the branch tip — **RESOLVED**

**Found during:** plans `17-01` and `17-02` **independently**, both before any
of their own work. Both executors refused to touch the ratchet constants.
**Status: CLOSED** by the orchestrator at `phase-17`, commit
`fix(17): cite a symbol, not a line range, per D-IMPL-114`.

### What was wrong

`make ci-core` was red on `phase-17` @ `f1969c5` with two failures in
`tests/invariants/test_citation_coverage.py`:

```
test_the_unanchored_python_citation_population_cannot_regrow
test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

The offending site was in the **approved Phase 17 design spec** — an artifact
written during this session. Amendment 1 cited the deployment-config module
with a **line range** (lines 82 through 91) instead of a symbol.

`D-IMPL-114` ruled that prose cites `path.py::Symbol`, because **a line anchor
is wrong the moment code moves**.

> **The literal citation text is deliberately not reproduced anywhere in this
> file.** See the note at the end of this entry — the sweep cannot tell a
> citation from a quotation of one, so writing the offending string here
> re-trips the ratchet that the entry exists to describe.

### Why both executors were right to refuse

Both correctly identified that the two remedies visible at the failure site —
raising `MAXIMUM_UNANCHORED_PY_CITATIONS`, or changing the pinned held-back
count — are ruling-scope by the gate's own text (*"belongs in a decision entry,
not in this constant"*). Taking either unilaterally is precisely the
ratchet-weakening those tests exist to prevent. Refusing was correct executor
behaviour and is recorded here as such.

### How it was closed

Neither ruling-scope remedy was needed: the gate's failure text names a third
option it *prefers* — **convert the citation**. The spec now cites
`src/ccf/deployment/config.py::_RESERVED_SECTIONS` and states the reasoning
inline (no `signal_batch` among the eight reserved names; registering one would
content-hash raw event data into Decision Replay dimension 2, `D-IMPL-80`).
The same defect in `17-CONTEXT.md` was fixed in the same commit — that file is
unswept, so it was not failing, but it carried the identical error.

**No ratchet constant was changed. No ruling was required.**

### The lesson, recorded because it generalises

The defect was in **an artifact authored this session**, and it reached the
branch because documentation commits are not run through `make ci-core` before
being pushed. Every `17-NN` plan carries the baseline *3305 passed / 0 failed*
measured at `543eda0`; three doc commits after that point made it stale.
**A plan's baseline is a measurement with a timestamp, not a fact.**

### The count discrepancy, explained — and it is a real property of the sweep

`17-01` and `17-02` each reported **2** unanchored citations; the main checkout
reported **1**. The difference was **each executor's own `deferred-items.md`**,
which quoted the offending citation strings verbatim while documenting them.

**The sweep cannot distinguish a citation from a quotation of one.** Writing
*"file X cites module Y at lines N–M"* in prose, using the literal
`module.py:N-M` form, registers as a citation from the documenting file. So a
faithful write-up of a citation defect *reproduces* that defect — and this
entry re-tripped the ratchet on its first draft, at which point the mechanism
became obvious.

This is not a bug to fix; a sweep that parsed intent would be a worse sweep.
It is a **writing constraint** on anything that documents a citation defect:
describe the location in words, or cite the symbol form. This file now does the
former deliberately, which is why no `path.py:line` string appears above.

The second site the executors named — a phase-16 test file citing another test
file with a line anchor — was an artifact of exactly this effect, not an
independent defect.

---

## DEF-17-02 — `import ccf.products.payload` raises `ImportError` when it is the first entry into the tree

**Found during:** plan `17-02`, Task 1.
**Status:** pre-existing; independent of anything `17-02` added.
**RULED (Dave, 2026-08-15): this gets an owner NOW — plan `17-03b`, wave 2.**

> *"In a phase whose explicit goal is the adopter's first experience, an import
> that fails when it is the first import into the tree is a real defect, not an
> internal curiosity. The workaround may stay only until the real fix lands; it
> must not become permanent."*

**Consequence for `17-02`'s workaround:** the import-order line in
`src/ccf/products/refusal.py` and its cold-subprocess pin are **temporary**.
`17-03b` removes the need for them; the cold-subprocess test **stays** (it is
the regression pin for the real fix), but its passing must no longer depend on
import ordering inside `refusal.py`.

```
PYTHONPATH=src:runtime .venv/bin/python -c "import ccf.products.payload"
→ ImportError: cannot import name 'PayloadSchemaViolation' from partially
  initialized module 'ccf.products.payload' (most likely due to a circular import)
```

The cycle:

```
ccf.products.payload:78  → ccf.skills.catalog
ccf.skills.catalog:703   → ccf.agents.definitions
ccf.agents.agent:62      → ccf.replay.record
ccf.replay.record:851    → ccf.products.request
ccf.products.request:710 → ccf.products.payload   (partially initialized → boom)
```

`import ccf.products.request` first succeeds, because it completes the far side
of the cycle before re-entering. So the defect is **invisible to the test
suite** — something always imports `request` (or a module that does) before
`payload`.

**Why `17-02` did not fix it.** The fix belongs in `payload.py`, `catalog.py`
or `record.py`, all existing modules, and `17-02`'s charter is explicit that it
modifies no existing module. It is worked around instead, and the workaround is
**pinned rather than trusted**: `src/ccf/products/refusal.py` orders its
`request` import before its `payload` import with the reason at the import
site, and
`tests/products/test_refusal_envelope.py::test_the_cold_and_warm_runs_agree_on_the_enumeration`
imports the module in a cold subprocess. Reversing those two lines fails that
test — verified by deliberate sabotage.

**Why it should still be fixed.** An adopter whose first line is
`from ccf.products.payload import refuse_payload` hits it immediately, and the
error names a circular import rather than anything they did. **This is an
adoption defect in a phase whose entire subject is the adopter's first
experience** — it deserves an owner before the phase gate.

---

## DEF-17-03 — measurement hazard: `.pyc` staleness can survive a `git checkout` revert

**Found during:** plan `17-02`, Task 3 guard sabotage. **Not a code defect** —
recorded because it produced a convincing false failure and cost time.

Sabotaging `src/ccf/products/refusal.py` by **swapping two adjacent import
lines** leaves the file byte-count identical. Reverting with
`git checkout -- <file>` within the same wall-clock second therefore restores a
file whose `(mtime, size)` pair matches the cached `__pycache__/*.pyc` compiled
from the *sabotaged* source — so Python keeps serving the sabotaged bytecode and
the tree looks broken while `git status` is clean.

**Remedy when a revert appears not to take:**

```
find src -name "__pycache__" -type d -exec rm -rf {} +
```

Any future sabotage control that reorders or substitutes equal-length source
should clear bytecode as part of its revert, not rely on mtime invalidation.

---

## DEF-17-04 — the citation-coverage ratchets are red again, and it is **not** DEF-17-01

**Found during:** plan `17-04`, before writing a line of its own code.
**Status:** pre-existing on the branch tip. Not fixed — the two visible
remedies are ruling-scope by the gate's own text, exactly as `17-01` and
`17-02` correctly refused for DEF-17-01.

> **No `path.py:line` string appears in this entry**, per the writing
> constraint DEF-17-01 established: the sweep cannot distinguish a citation
> from a quotation of one, so documenting the defect that way reproduces it.

### The measurement

Measured on a **pristine detached worktree** of `phase-17` @ `7d76205` — no
`17-04` file present, nothing of mine on disk:

```
2 failed, 3339 passed, 118 skipped   (396.86s)

FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

Both assert `14 == 13`.

**This contradicts the baseline `17-04` was handed** (*"3341 passed / 0 failed
… Citation ratchets green"*). The plan's own written baseline was staler still
(*3305 / 0*). A plan's baseline is a measurement with a timestamp, not a fact —
the DEF-17-01 lesson, recurring.

### Why it is a different defect from DEF-17-01

DEF-17-01's offending site was in the Phase 17 design spec under
`docs/superpowers/specs/`, and it was genuinely converted to the symbol form.
That site is gone; the fix held.

The present population is entirely different. All fourteen held-back sites are
in `docs/surface-changes/` fragments and in the assembled `docs/SURFACE-CHANGES.md`.
`HELD_BACK_HOSTS` holds a **glob** over that fragment directory, so every
fragment carrying a line-anchored Python citation counts. The pinned total is
thirteen — described in the gate's own failure text as *eleven across five
landed fragments plus two in the assembled file*. The tree now holds **twelve
across six fragments** plus the same two. The sixth is a **Phase 16** fragment
(the experience-door entitlement one, whose own commit message says it
*"satisfied the two ratchets this change tripped"*).

So the count moved when Phase 16 landed a sixth fragment, and the constant was
not moved with it.

### Why `17-04` did not fix it

1. **Out of scope by the scope boundary.** `17-04` touches
   `src/ccf/client/`, `tests/client/`, and its own surface-change fragment.
   It modified no fragment in the counted population and no ratchet constant.
   Verified: `17-04`'s own fragment contributes **zero** sites to the
   held-back list, and `docs/SURFACE-CHANGES.md` has the **same seven** raw
   Python line-anchored citations before and after `17-04`'s regeneration.
2. **Both visible remedies are ruling-scope**, by the gate's own words —
   *"that is a ruling-scope change and belongs in a decision entry, not in
   this constant."* Raising the ceiling or re-pinning the held-back count
   unilaterally is the ratchet-weakening these tests exist to prevent.
3. **The third remedy the gate prefers — convert the citation — is not
   available here.** DEF-17-01 was closable that way because its site was in a
   spec being actively authored. These sites are in **landed plan fragments**,
   and the held-back list exists precisely because *"a later editor should not
   silently revise one to chase a line number."* Converting them is the one
   thing the ruling forbids.

### What a ruling would decide

Whether the pinned count moves to fourteen (recording that a sixth landed
fragment joined the held-back population, which is the ruling's own logic
applied to a new fragment), or whether landed fragments stop being globbed and
are enumerated instead so a new one cannot silently join.

**Recommend surfacing at the Phase 17 gate**, not later: the phase closes on
`make ci-core` being green, and this makes it red for a reason no plan in the
phase caused.
