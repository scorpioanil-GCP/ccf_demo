---
phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi
plan: 06
subsystem: library-citations
tags: [citations, criterion-14, D-IMPL-192, resolver-seam, DOCS-17]
requires:
  - "the ten trees at archive/examples/ (plan 23-04, ef336f3)"
  - "the widened EXAMPLE_PREFIX in the resolver-seam gate (plan 23-03)"
  - "the archive's relocated children resolving the repo root (plan 23-05)"
provides:
  - "four library-docstring node ids that name the archive and resolve on disk"
  - "the resolver seam GREEN on both of its assertions"
  - "a measured record that a dangling node id under src/ is caught by NO gate"
affects:
  - "23-12 (criterion 14's discharge, criterion 7's accounted delta)"
tech-stack:
  added: []
  patterns:
    - "prove path-string-only by STRIPPING the insertion and demanding byte-identity, not by counting changed lines"
    - "for an edit with no gate, verify by reading the shipped docstring and resolving the cited path on disk"
    - "revert-and-observe in BOTH directions to establish which half of a claim is true"
key-files:
  created: []
  modified:
    - src/ccf/products/bind.py
    - runtime/ccf_runtime/mcp/egress.py
    - runtime/ccf_runtime/mcp/experience.py
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "The four edits were committed BEFORE any sabotage, because `git checkout --` destroys an uncommitted fix while `git diff --quiet` reports success"
  - "`D-IMPL-192`'s 'no gate' claim is corrected as HALF right, not two-thirds — the fraction in `23-RESEARCH.md` §7.3 does not survive a re-measure"
metrics:
  duration: "~50m"
  completed: 2026-08-24
---

# Phase 23 Plan 06: The Four Permitted Citations Summary

Four path strings under `src/` and `runtime/` now name the archive, each proven
path-string-only by stripping the insertion rather than by claiming it; nothing
else under `src/`, `runtime/` or `pyproject.toml` moved. The resolver seam went
from **2 failed / 14 passed** to **16 passed**. Two of the four edits had no
gate at all, before or after, and this summary says which two rather than
implying four were gate-verified.

---

## The Four Edits

Located by SYMBOL per `D-IMPL-114`; `D-IMPL-123` holds the unanchored-Python
citation population at a ceiling of zero, so nothing here is line-anchored.

| # | Symbol | Before | After |
|---|---|---|---|
| 1 | `src/ccf/products/bind.py` — the MODULE docstring | `examples/04-cross-process/producer_child.py::resolve` | `archive/examples/04-cross-process/producer_child.py::resolve` |
| 2 | `runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol` | `examples/04-cross-process/producer_child.py::resolve` | `archive/examples/04-cross-process/producer_child.py::resolve` |
| 3 | `runtime/ccf_runtime/mcp/experience.py::ExperienceProductResolverProtocol` | `examples/04-cross-process/producer_child.py::resolve` | `archive/examples/04-cross-process/producer_child.py::resolve` |
| 4 | `runtime/ccf_runtime/mcp/experience.py::ContextProviderProtocol` | `examples/external/00-hello-context/serve.py::context_provider` | `archive/examples/external/00-hello-context/serve.py::context_provider` |

Committed at **`2256526`**. The enclosing symbol was confirmed for each before
editing: `bind.py`'s module docstring spans the file's opening triple-quote to
its terminator and the citation sits inside it; the other three were confirmed
against the file's `^class` declarations, and `git diff`'s own hunk headers
independently name `ProductResolverProtocol`, `ExperienceProductResolverProtocol`
and `ContextProviderProtocol`.

### Path-string-only, proven mechanically

```
git diff -U0 $PHASE_BASE -- src runtime | grep -c '^+[^+]'   ->  4
git diff -U0 $PHASE_BASE -- src runtime | grep -c '^-[^-]'   ->  4
```

Then, for each of the four pairs, the single 8-character `archive/` insertion is
stripped from the new line and the result compared to the base line:

```
[1] strip-and-compare: IDENTICAL   inserted chars: 8
[2] strip-and-compare: IDENTICAL   inserted chars: 8
[3] strip-and-compare: IDENTICAL   inserted chars: 8
[4] strip-and-compare: IDENTICAL   inserted chars: 8
PATH-STRING-ONLY: PROVEN
```

**The changed-line count alone would not have proven this**, and `S-C3` below is
the demonstration: a prose word altered on one of the four lines leaves the
count at exactly 4.

### The five `s1-01` citations are untouched

```
src/ccf/products/bind.py                  s1 OK (1 citation)
runtime/ccf_runtime/mcp/egress.py         s1 OK (1 citation)
runtime/ccf_runtime/mcp/experience.py     s1 OK (1 citation)
src/ccf/products/request.py               s1 OK (2 citations)
total across the four files: 5
```

Each compared line-for-line against `PHASE_BASE`. `src/ccf/products/request.py`
is additionally **byte-identical in full** (`git diff --quiet` clean; sha256
`b1a2b8e33c24ba24…` on both sides) and appears in no diff — it is not in this
plan's `files_modified`.

---

## How Each Edit Was Verified — and Which Two Had No Gate

This is the part the wave's brief insisted be stated plainly rather than
averaged into "four edits verified".

| # | Verified by | Evidence |
|---|---|---|
| 1 | **READING + on-disk resolution.** No gate. | The shipped `__doc__` was imported and its cited paths resolved with the seam gate's own `_resolves` rule; `archive/examples/04-cross-process/producer_child.py` returned `True`, and `def resolve(` exists in it |
| 2 | **A GATE, RED before GREEN.** | `test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.egress.ProductResolverProtocol]` |
| 3 | **A GATE, RED before GREEN.** | `test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.experience.ExperienceProductResolverProtocol]` |
| 4 | **READING + on-disk resolution.** No gate. | Same method; `archive/examples/external/00-hello-context/serve.py` resolved `True`, and `def context_provider(` exists in it |

**Two of the four edits were gate-verified. Two were not, and no exit code in
this repository would have told me if I had got them wrong.**

### The resolver seam: RED before, GREEN after

```
BEFORE  .venv/bin/python -m pytest tools/docs_tests/test_resolver_seam_obligations.py -q
        2 failed, 14 passed
        FAILED ...test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.egress.ProductResolverProtocol]
        FAILED ...test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.experience.ExperienceProductResolverProtocol]

AFTER   16 passed
```

`test_both_seams_cite_both_call_sites` passes, which is the assertion plan
`23-03`'s widening of `EXAMPLE_PREFIX` exists to keep meaningful: with a single
prefix the two re-pointed citations would stop being recognised as citations at
all and the `>= 2` assertion would fail on a tree that is entirely correct.

---

## The Green Gate That Is Lying — Re-Confirmed on Today's Tree

**Measured before any edit was made**, with all four citations naming the old
paths and both old paths confirmed absent from disk:

```
test -e examples/04-cross-process/producer_child.py      -> ABSENT
test -e examples/external/00-hello-context/serve.py      -> ABSENT

.venv/bin/python -m tools.lints --citations   -> exit 0, 0 lines of output
.venv/bin/python -m tools.lints --all         -> exit 0, 0 lines of output
grep for the rule / the files / the bad paths -> ZERO MENTIONS
```

`resolve_cited`'s suffix fallback resolves the stale path to the archived file
and reports the citation **checked and passing**. This is the stronger form of
`D-IMPL-192`'s hole: that one leaves a citation UNCHECKED, this one leaves it
GREEN AND FALSE. A green lint was treated as evidence of nothing throughout this
wave, before or after the edits.

---

## Sabotage — Every Guard Watched RED

The four edits were **committed first**, at `2256526`, and only then sabotaged.
Wave 2's hazard is that `git checkout --` silently destroys an uncommitted fix
while `git diff --quiet` reports success. Every restore was followed by a
**positive** grep for the restored content, not by an absence check.

| # | Mutation | Prediction | Outcome |
|---|---|---|---|
| **S-C1** | Re-point the `s1-01` citation in `egress.py` to `archive/…` as a fifth edit | the `s1-01` byte-comparison fails; the seam test may also fail | **CORRECT, on all three limbs.** Byte-comparison reported `CHANGED runtime/ccf_runtime/mcp/egress.py`; the seam went `1 failed, 15 passed`; and the changed-line count rose to **5** |
| **S-C2** | Re-point `bind.py`'s node id at `archive/examples/04-cross-process/nonexistent.py::resolve` | `--all` exits 0 with zero mentions | **CORRECT.** See below — and it is worse than predicted |
| **S-C3** | Alter a word of surrounding prose on one of the four lines (`Both are` → `Both were`) | the strip-and-compare fails | **CORRECT**, and the second limb matters: the changed-line count stayed at **4**, so strip-and-compare was the ONLY check that caught it |
| **S-C4 / S-V2** | Append a whitespace-only line to `pyproject.toml` | the per-member diff is non-empty | **CORRECT.** `pyproject.toml tracked=1 changed=[pyproject.toml]` |
| **S-V1** | Run the per-member loop with a misspelled member (`srcc`) | `tracked=0`, the floor fires | **CORRECT.** `srcc tracked=0 changed=[]` — the floor is what separates a clean member from a fictional one |

### S-C2 in full, because it is a required record

The dangling node id was planted under `src/` and the target confirmed absent:

```
src/ccf/products/bind.py -> archive/examples/04-cross-process/nonexistent.py::resolve
test -e archive/examples/04-cross-process/nonexistent.py   -> ABSENT

.venv/bin/python -m tools.lints --citations  -> exit 0,  0 lines
.venv/bin/python -m tools.lints --all        -> exit 0,  0 lines
grep cite03 | bind.py | nonexistent | 04-cross-process     -> ZERO MENTIONS
tests/invariants/test_citation_coverage.py                 -> 5 passed
tools/docs_tests (whole package)                           -> 8 failed, 268 passed
```

**I went further than the plan asked, because eight failures is not a result you
can read at a glance.** The failing node ids were captured with the sabotage in
place, the sabotage removed, and the package re-run:

```
diff <sabotaged failures> <clean failures>   ->  IDENTICAL FAILURE SETS
grep for nonexistent | products/bind in the failure output  ->  0
```

The same eight fail either way — `test_mkdocstrings_gate` ×3,
`test_no_stale_example_paths` ×4, `test_requirement_ledger` ×1 — all of them
pre-existing and all of them named in this plan's own "expected to be STILL RED"
list. **A `path::symbol` node id under `src/` that points at nothing is caught by
NOTHING in this repository: not the lints, not `tools/docs_tests`, not
`tests/invariants/test_citation_coverage.py`.**

This is `D-IMPL-192`'s measured hole, re-confirmed on today's tree. The durable
fix — *a standing check that every `path::symbol` node id under `src/` and
`runtime/` RESOLVES*, the counterpart to Phase 22's
`tools/docs_tests/test_adoption_wording.py::test_every_published_node_id_resolves`
— is **BACKLOG, explicitly rejected as Phase 23 scope** by `D-IMPL-192`. It was
**not built here.** Until it exists, criterion 14's amendment is a workaround
and is known to be one.

---

## Criterion 14's Per-Member Diff, with the `VAC-01` Floor

Three independent measurements, never one combined pathspec, each with a
tracked-file floor beside it because a misspelled member diffs empty exactly
like a clean one:

```
src            tracked=142   changed=[src/ccf/products/bind.py]
runtime        tracked=71    changed=[runtime/ccf_runtime/mcp/egress.py runtime/ccf_runtime/mcp/experience.py]
pyproject.toml tracked=1     changed=[]
```

Every member proven to name tracked files. `pyproject.toml` is diff-empty and
**proven to be a real member** — its one example row names
`tests/examples/test_ext00_fixture_schemas.py`, which is not moving, so it
genuinely needed no edit.

---

## The Correction to `D-IMPL-192`, Verified by Revert-and-Observe

`D-IMPL-192` states the phase *"would ship four citations in library code
pointing at nothing, with no gate able to say so."* Both directions were
measured against today's tree.

**Direction A — revert ONLY edits 2 and 3.** Prediction: the seam gate goes RED
on exactly those two ids.

```
2 failed, 14 passed
FAILED ...test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.egress.ProductResolverProtocol]
FAILED ...test_the_seam_cites_a_shipped_example_that_exists[ccf_runtime.mcp.experience.ExperienceProductResolverProtocol]
```
**CORRECT.** The "no gate" claim is FALSE for these two.

**Direction B — revert ONLY edits 1 and 4**, leaving two citations naming paths
confirmed absent from disk. Prediction: every gate stays green.

```
resolver seam                              -> 16 passed
tools.lints --all                          -> exit 0, 0 lines
tests/invariants/test_citation_coverage.py -> 5 passed
```
**CORRECT.** The "no gate" claim is TRUE for these two.

### A wrong figure, recorded as a correction rather than smoothed

`23-RESEARCH.md` §7.3 — and this plan quoting it — call the "no gate" claim
**"two-thirds right"**. That fraction does not survive the re-measure. Of the
**four** citations the entry is about, **two** are gated and **two** are not:
the claim is **HALF right, not two-thirds**. The direction of the correction is
confirmed and the ruling is unaffected — all four edits were still needed, and
`D-IMPL-192` remains correct that no gate covers the population as a whole. Only
the fraction is wrong, and it is stated here rather than repeated.

---

## Criterion 7 — The Accounted Delta (`D-IMPL-196`)

**This wave adds ZERO test node ids and removes ZERO.**

```
git show 2256526 --name-only | grep -c '^tests/'   ->  0
git show 2256526 | grep -c '^+ *def test_'          ->  0
git show 2256526 | grep -c '^- *def test_'          ->  0

.venv/bin/python -m pytest --collect-only -q   (before)  ->  4223 tests collected
.venv/bin/python -m pytest --collect-only -q   (after)   ->  4223 tests collected
```

Collection is unmoved at **4223**. There is no addition to name and no id lost
against `PHASE_BASE`. The wave's only functional witness,
`tools/docs_tests/test_resolver_seam_obligations.py`, is a **pre-existing**
module under `tools/`, which `testpaths = ["tests"]` does not collect — it is
not part of the 4223 in either measurement.

---

## Deviations from Plan

None affecting scope. Two orderings were chosen deliberately and are recorded
rather than left implicit:

1. **The four edits were committed before any sabotage** (the plan places the
   sabotage inside task 1). Wave 2's hazard is that `git checkout --` destroys an
   uncommitted fix while `git diff --quiet` reports success. Committing first
   makes every restore recoverable.
2. **S-C2 was extended** beyond running `--all`: the whole `tools/docs_tests`
   package and the citation invariant were run both with and without the
   sabotage, and the failure sets diffed. Running only `--all` would have
   established that ONE checker is blind; the set-diff establishes that
   **nothing** in the tree sees it, which is the claim `D-IMPL-192` actually
   makes.

## Findings Carried Forward

- **An ungated surface, not a clean sweep.** `python -m tools.lints --citations`
  cannot be made to fail on a stale `path::symbol` node id under `src/`, whether
  the stale path resolves by suffix (green and false) or does not resolve at all
  (unchecked). A control that cannot be made to fail is a finding. It is the
  `D-IMPL-192` backlog item, re-confirmed, and deliberately not fixed here.
- **The `--citations` lint's suffix fallback is the sharper half of that hole**
  and is not what `D-IMPL-192` describes. `D-IMPL-192` documents *unchecked*;
  what the archive move produces is *checked, green, and wrong*. Worth naming
  when the backlog item is eventually scheduled.

## Boundaries Held

- No fifth edit under `src/`, `runtime/` or `pyproject.toml`. Three files
  changed, four lines, four inserted prefixes.
- `.planning/STATE.md` and `.planning/ROADMAP.md` untouched (`D-10`, `D-15`).
- No Success Criterion authored, renumbered or edited.
- `examples/s1-*` and `examples/hw1-*` neither moved nor re-pointed.
- No line-anchored Python citation anywhere in this summary or in the commits;
  `tests/invariants/test_citation_coverage.py` run as its own step, output read,
  **before** committing — 5 passed.
- No package installed.

---

## Self-Check: PASSED

Every file this summary claims, and every commit hash, verified present:

```
FOUND: src/ccf/products/bind.py
FOUND: runtime/ccf_runtime/mcp/egress.py
FOUND: runtime/ccf_runtime/mcp/experience.py
FOUND: docs/surface/examples/RETIREMENT-COUPLINGS.md
FOUND: .planning/phases/23-.../23-06-SUMMARY.md
FOUND: commit 2256526   (the four edits)
```

Final state against `PHASE_BASE`, re-measured at the close:

```
src            tracked=142   changed=[src/ccf/products/bind.py]
runtime        tracked=71    changed=[runtime/ccf_runtime/mcp/egress.py runtime/ccf_runtime/mcp/experience.py]
pyproject.toml tracked=1     changed=[]
added lines under src/ and runtime/               -> 4
src/ccf/products/request.py in any diff           -> 0 files
STATE.md / ROADMAP.md in EITHER of my commits     -> 0 files
unexpected working-tree paths                     -> 0
```

`ROADMAP.md` does differ from `PHASE_BASE`, at `a6d7367` — the `D-IMPL-196`
criterion-7 amendment committed before this wave began. Neither of this plan's
commits touches it. Named here so the difference is not read as a `D-10` breach
by a later reader diffing the phase as a whole.
