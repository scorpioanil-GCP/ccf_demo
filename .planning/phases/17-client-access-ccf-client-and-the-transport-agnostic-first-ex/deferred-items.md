# Phase 17 — deferred items

Out-of-scope discoveries. Logged, not fixed, per the scope boundary: only
issues directly caused by the current plan's changes are auto-fixed.

---

## DEF-17-01 — the phase-17 baseline is **not** 0 failed; two citation-coverage tests are red on the branch tip

**Found during:** plan `17-02`, before any code was written.
**Status:** pre-existing on `phase-17` @ `f1969c5`. **Needs a ruling.**

Every plan in this phase carries the line *"Verified baseline: `make ci-core` →
3305 passed / 118 skipped / 0 failed, exit 0"*, measured at `543eda0`. That is
no longer true at the branch tip:

```
make ci-core   # on phase-17 @ f1969c5, clean tree
→ 4 failed, 3301 passed, 118 skipped
```

Two of the four were mine and are fixed in `17-02` (see the SUMMARY). The other
two are not, and reproduce with every `17-02` file removed from the tree:

```
FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

What they report, verbatim and unchanged before and after `17-02`:

```
2 unanchored citations of Python targets are in D-IMPL-123's scope, ceiling 0
  - tests/products/test_discovery_audiences.py:59 cites test_class_governance.py:127
  - docs/superpowers/specs/2026-08-15-ccf-client-design.md:421 cites src/ccf/deployment/config.py:82-91

D-IMPL-123 held back 13 citations ... 14 are here now
  (the extra host is docs/surface-changes/16-24-experience-door-entitlement.md)
```

**Why this is not `17-02`'s to fix.** One of the two offending citations lives
in `docs/superpowers/specs/2026-08-15-ccf-client-design.md` — the approved
Phase 17 design spec, an authored artifact. The other is a phase-16 test. Both
ratchets state in their own failure text that raising the constant is
indistinguishable from an accidental regression at the failure site, and that
a held-back-count change *"is a ruling-scope change and belongs in a decision
entry, not in this constant."* Editing either without a ruling is exactly what
those two tests exist to prevent.

**What a ruling needs to decide:**

1. Convert the two citations to the `path.py::Symbol` form `D-IMPL-114` ruled
   (preferred by the failure message), which touches the approved spec; **or**
2. Raise `MAXIMUM_UNANCHORED_PY_CITATIONS` from 0 to 2 and the held-back
   constant from 13 to 14, in one commit naming both citations — the escape
   hatch the message describes, with `git log` as the only thing separating a
   deliberate addition from a regression afterwards.

**Consequence for every other plan in this phase.** No `17-NN` plan can satisfy
its own written verification criterion *"`make ci-core` must report 0 failed"*
until this is ruled. Each should measure against **3303 passed / 2 failed** and
say so, rather than treating its own work as the cause.

---

## DEF-17-02 — `import ccf.products.payload` raises `ImportError` when it is the first entry into the tree

**Found during:** plan `17-02`, Task 1.
**Status:** pre-existing; independent of anything `17-02` added.

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
of the cycle before re-entering. So the defect is invisible to the test suite —
something always imports `request` (or a module that does) before `payload`.

**Why `17-02` did not fix it.** The fix belongs in `payload.py`, `catalog.py` or
`record.py`, all existing modules, and `17-02`'s charter is explicit that it
modifies no existing module. It is worked around instead, and the workaround is
**pinned rather than trusted**: `src/ccf/products/refusal.py` orders its
`request` import before its `payload` import with the reason at the import site,
and `tests/products/test_refusal_envelope.py::test_the_cold_and_warm_runs_agree_on_the_enumeration`
imports the module in a cold subprocess. Reversing those two lines fails that
test — verified by deliberate sabotage.

**Why it should still be fixed.** An adopter whose first line is
`from ccf.products.payload import refuse_payload` hits it immediately, and the
error names a circular import rather than anything they did.

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
