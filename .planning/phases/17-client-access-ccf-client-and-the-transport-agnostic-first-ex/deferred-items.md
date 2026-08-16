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
written during this session:

```
docs/superpowers/specs/2026-08-15-ccf-client-design.md:421
  cites src/ccf/deployment/config.py:82-91
```

`D-IMPL-114` ruled that prose cites `path.py::Symbol`, because **a line anchor
is wrong the moment code moves**. Amendment 1 cited a line range.

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

### Note on the count discrepancy

`17-01` and `17-02` each reported **2** unanchored citations; the main checkout
reported **1** (the spec site alone), and the gate went fully green — 5 passed —
after that single conversion. The second site both executors named
(`tests/products/test_discovery_audiences.py:59`) is not reproducible on the
main checkout at the same commit. Recorded rather than explained; if it
resurfaces, it is a real sweep-scope question.

---

## DEF-17-02 — `import ccf.products.payload` raises `ImportError` when it is the first entry into the tree

**Found during:** plan `17-02`, Task 1.
**Status:** pre-existing; independent of anything `17-02` added. **OPEN.**

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
