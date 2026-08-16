# Phase 17 — deferred items

Out-of-scope discoveries logged rather than fixed, per the executor scope
boundary (only defects *caused by* the current task are auto-fixed).

---

## DEF-17-01 — `tests/invariants/test_citation_coverage.py` is red on `phase-17` HEAD

**Found during:** plan `17-01`, Task 3 verification (`make ci-core`).
**Status:** pre-existing, **not** caused by `17-01`. Blocks the phase gate.

### The measurement

`make ci-core` on `phase-17` @ `f1969c5`, worktree clean, **before any `17-01`
commit** — extracted with `git archive f1969c5` into a scratch tree so the
measurement could not be contaminated by working-tree state:

```
2 failed, 3 passed in 5.46s
FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

The identical two failures are present after `17-01`'s three commits. Full
suite: **3303 passed / 2 failed / 118 skipped**, unchanged by this plan.

`17-01-PLAN.md` states a baseline of *3305 passed / 118 skipped / 0 failed*
measured at `543eda0`. That commit predates the three commits that introduced
the offending citations, so the plan's baseline was correct when taken and is
stale now.

### The two failures

1. **`test_the_unanchored_python_citation_population_cannot_regrow`** — ceiling
   0, found 2:
   - `tests/products/test_discovery_audiences.py:59` cites
     `test_class_governance.py:127` — added by `190d51b`
     (`feat(16-27): ProductDiscovery gains audiences, opaque and additive`)
   - `docs/superpowers/specs/2026-08-15-ccf-client-design.md:421` cites
     `src/ccf/deployment/config.py:82-91` — added by `f0467c1`
     (`docs(17): close the demo-data question`)

2. **`test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident`**
   — expects 13 held-back citations, finds 14. The additional host is
   `docs/surface-changes/16-24-experience-door-entitlement.md`, added by
   `0125c04` (`docs(16-24): satisfy the two ratchets this change tripped`).

None of these files is touched by `17-01`
(`git diff f1969c5..HEAD --name-only` lists only `tools/retirement_sweep.py`,
`docs/surface/examples/RETIREMENT-COUPLINGS.md` and the five `src/ccf/**`
docstring modules).

### Why `17-01` did not fix it

Both failures are **ruling-scope questions, not defects with a mechanical
fix** — the gate's own failure text says so. Closing (1) means either
converting each citation to the `path.py::Symbol` form `D-IMPL-114` ruled, or
raising a ceiling constant and naming the citation in the commit message;
closing (2) means changing a pinned count, which the gate says *"belongs in a
decision entry, not in this constant."* Choosing either without a ruling is
exactly the ratchet-weakening these tests exist to prevent, so this is a
Rule 4 / `D-IMPL-NN` matter for Dave rather than executor discretion.

### Consequence for the phase

`make ci` cannot go green until this is closed, and because `ci-core` is the
first prerequisite of `ci`, a red `ci-core` **aborts `make ci` before
`gate-tools` runs**. That directly shaped how `17-01` Task 3's sabotage control
had to be observed — see `17-01-SUMMARY.md`.

**Recommendation:** close before the Phase 17 gate, as its own plan or ruling.
Whichever plan closes it should state which of the two remedies each of the
three citations takes.
