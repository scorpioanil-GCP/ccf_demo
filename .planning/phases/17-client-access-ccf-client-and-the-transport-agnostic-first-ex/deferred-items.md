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

### The count discrepancy — the orchestrator's first explanation was WRONG

**Superseded by `DEF-17-04`. Read that entry; this section records the error so
the reasoning that produced it is visible.**

The orchestrator explained the executors' 2-vs-1 discrepancy as a
self-reference effect: each executor's own `deferred-items.md` quoted the
offending citation strings while documenting them, and the sweep cannot
distinguish a citation from a quotation of one. That effect **is real** — this
entry did re-trip the ratchet on its first draft, which is why no
`path.py:line` string appears above, and the writing constraint stands.

**But it was the wrong diagnosis for the second site, and it was used to
dismiss a correct executor finding.** Three executors reported the branch as
2-red; the orchestrator measured green three times, including a full-suite run,
and concluded the worktree measurements were the unreliable ones.

The truth is the reverse. `17-03` measured the mechanism:
`tools/lints/citations.py::repo_index` walks the whole repo root and its
`SKIP_DIRS` omitted `.claude`. With six agent worktrees live, one basename
resolved to **seven** paths; an ambiguous basename is **dropped from the sweep
rather than checked**. So the main checkout passed *vacuously* — and the
orchestrator's "3375 passed / 0 failed" was itself a vacuous measurement.

**The executors were right, and right for the right reason.** They measured in
trees with no worktrees inside them, where the sweep resolves basenames
uniquely and actually checks the sites.

### What this cost, and the rule it produces

Two genuine Phase 16 citation defects sat behind a green run for the length of
a wave, and a correct finding was talked down three times.

**The rule: when a gate and an executor disagree, the gate is a suspect too.**
This project's standing lesson is that defects land in verification machinery
rather than mechanism. A green run is a claim, not a fact — and a green run
that contradicts three independent measurements is a claim with evidence
against it. The orchestrator re-measuring on the main checkout was the right
instinct applied to the wrong question: it established *that* the results
differed, and stopped before asking *why*.

---

## DEF-17-02 — `import ccf.products.payload` raises `ImportError` when it is the first entry into the tree — **RESOLVED**

**Found during:** plan `17-02`, Task 1.
**Status:** pre-existing; independent of anything `17-02` added.
**RULED (Dave, 2026-08-15): this gets an owner NOW — plan `17-03b`, wave 2.**
**CLOSED by plan `17-03b`, 2026-08-15.** The original write-up is preserved
below unchanged; what `17-03b` did, and how it was proven, is at the end of
this entry under *Resolution*.

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

### Resolution — plan `17-03b`, 2026-08-15

**The cycle was re-derived before it was touched**, on `phase-17` @ `7d76205`,
and it stood exactly as reported above — same five edges, same modules.

**What changed: one edge, in one module.** `ccf.products.request` needed two
names from `ccf.products.payload`, and on inspection neither justified a
module-scope import:

| Name | How it was used | Where it went |
|---|---|---|
| `PayloadSchemaViolation` | one parameter annotation on `request.py::_translate`, a plain function, under `from __future__ import annotations` | `TYPE_CHECKING` — nothing resolves it at runtime |
| `refuse_payload` | a *value*, called once inside `request.py::refuse_request` | a call-time import in that function |

The bottom-of-module import of `ccf.skills.catalog` stays, and has to:
`SkillArgumentSchema` is a **field type** of `ProductRequestContract`, so
`model_rebuild()` needs the class itself and `TYPE_CHECKING` cannot serve it.
That is the D-IMPL-56 pattern working as ruled, and it was left alone.

**The edge is gone rather than reordered.** No entry point loses, which is the
difference between this and the workaround it replaces.

**The workaround is removed.** `ccf.products.refusal` now imports `payload`
before `request` — sorted order, and the exact order that used to raise — with
the fourteen-line comment deleted.

#### How it was proven

| Measurement | Before | After |
|---|---|---|
| `ccf.*` modules failing as a **cold first import** (126 walked, one subprocess each) | **2** — `ccf.products.payload`, `ccf.products.bind` | **0** |
| `ccf_runtime.*` modules failing (69 walked) | 0 | 0 |
| The pin `tests/products/test_refusal_envelope.py::test_the_cold_and_warm_runs_agree_on_the_enumeration` with the two `refusal` imports **deliberately reversed** | fails (`17-02` verified this by sabotage) | **passes** — 36/36 in the module, and `import ccf.products.payload` still clean |
| The same pin, imports in sorted order | n/a | passes |

The third row is the one that matters: the pin stays, and it now passes for a
reason that has nothing to do with which line comes first.

**Sabotage control on the new guard.** The module-scope edge was restored in
`ccf.products.request`, bytecode cleared, and
`tests/invariants/test_cold_import.py` run: it failed naming **three** modules
(`payload`, `bind`, and now `refusal`, since `refusal` no longer orders around
the defect). Reverted from a byte-for-byte copy rather than with
`git checkout --`, per **DEF-17-03**.

#### The guard that replaces the workaround

`tests/invariants/test_cold_import.py` — a **module walk**, not a list of five,
because a list pins the cycle that was found rather than the property that
matters. It carries four guards on itself: the walk is cross-checked
file-for-file against a filesystem glob; a broken sub-package must propagate
out of the walk instead of truncating it; a planted two-module cycle must be
reported by the real probe; and its cycle-free twin must be clean.

It is scoped to `src/ccf`. CLAUDE.md §7.3's *zero harness imports in core* is
what makes an unconditional probe there sound — nothing in `src/` can fail for
want of an optional extra. The runtime's adapter and orchestration modules
import their harness at module scope, correctly, so the same probe over
`runtime/` would make the optional `adk` and `langgraph` extras a hard
dependency of an always-on invariant test. `ccf_runtime` was measured clean
anyway; covering it belongs behind the `harness` marker.

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

## DEF-17-04 — the citation-coverage ratchets pass **vacuously** in the main checkout, and `DEF-17-01` was closed on that reading

**Found during:** plan `17-03`, before any of its own work, while measuring the
baseline. **Out of scope for `17-03`** — the two offending sites are Phase 16
artifacts and the sweep defect is in `tools/`, none of them in that plan's
declared files. Recorded here rather than fixed.

### The measurement

On `phase-17` at the branch tip, in a clean worktree:

```
2 failed, 3339 passed, 118 skipped
```

Both failures are in `tests/invariants/test_citation_coverage.py`. In the main
checkout the identical commit reports `5 passed`. The two trees are the same
commit, so one of the two readings is wrong.

### Why the readings differ, and which one is right

The sweep resolves a cited **basename** against an index of every file in the
repository, and drops the site when the basename resolves ambiguously. The
index builder walks the entire repo root and its skip-list — `__pycache__`,
`.git`, `.venv`, `venv`, `build`, `dist`, `site`, `.mypy_cache`,
`.pytest_cache`, `node_modules` — **does not contain `.claude`**.

The main checkout carries six agent worktrees under `.claude/worktrees/`, each
a full copy of the tree. So in the main checkout a cited basename resolves to
**seven** paths, is ambiguous, and is dropped from the sweep. In a worktree it
resolves to one and is measured.

Measured, in the main checkout, for the basename the first failure names: seven
index entries, six of them under `.claude/worktrees/`, one real.

**The worktree reading is the correct one.** The main checkout's green is a
guard that stops measuring the moment a parallel wave is running — which is
precisely when the most code is landing.

### The two genuine defects it was hiding

Both are Phase 16 artifacts, neither is a quotation artifact:

1. A `tests/products/` module added in `16-27` carries, in a docstring, a
   line-anchored citation of another test module. `D-IMPL-114` rules that prose
   cites the symbol form. The string appears nowhere in this file, so the
   quotation effect `DEF-17-01` documents does not explain it.
2. A `docs/surface-changes/` fragment from `16-24` carries a line-anchored
   citation of the experience door module, which is the fourteenth held-back
   site against a pinned thirteen.

### What this means for `DEF-17-01`

That entry is marked **RESOLVED**, and its closing paragraph states that *"the
second site the executors named — a phase-16 test file citing another test file
with a line anchor — was an artifact of exactly this effect, not an independent
defect."* That reading is **false**, and disproving it took one grep. `17-01`
and `17-02` were right that there were two sites; the third executor to measure
the tree found the same two.

The generalisable point, and it is the sharper one: the reason a defect could be
closed on a wrong reading is that the **verification machinery** was reporting a
green it had not earned. This project's ledger already says defects land in
verification code rather than in mechanism. Here the ratchet, the entry closing
it, and the count reconciliation were all downstream of one unskipped directory.

### The three repairs, for whoever owns them

- Add `.claude` to the sweep's skip set, so the ratchet measures the repository
  rather than the repository times the number of live agents. This alone turns
  the main checkout red, which is correct.
- Convert the `16-27` docstring citation to the symbol form.
- Rule on the fourteenth held-back site — convert it, or raise the pinned count
  in a decision entry, which is what the gate's own text demands.

**None was done in `17-03`:** the first is `tools/` and the other two are Phase
16 files, all outside that plan's declared `files_modified`, and the third needs
a ruling rather than an edit. `17-03` measured its own delta against the
2-failing baseline and added no new failure.

---

## DEF-17-05 — worktrees spawn stale, and every executor pays the same opening cost

**Found during:** plans `17-02`, `17-03b` (and noted by `17-01`). **Three
confirmed instances.** Not a code defect; an execution-environment property.

Each `isolation: "worktree"` agent spawned at an ancestor commit rather than the
branch tip — one at 103 commits behind, one at the phase 15.6 merge with no
Phase 17 files at all — and none had a `.venv`. Every executor independently
diagnosed it, fast-forwarded (strict ancestor, clean tree, no local commits) and
symlinked the interpreter before it could begin.

The cost is real but bounded and self-correcting. Recorded so the next executor
recognises it in one step instead of three, and so it is not mistaken for a
defect in the branch.

---

## DEF-17-06 — the `.claude` skip makes the citation coverage ratchet fail inside every worktree

**Found during:** plan `17-05`, while measuring the baseline. **Out of scope for
that plan** — the file is `tools/`, and the defect predates it.

`DEF-17-03`'s repair (add `.claude` to `SKIP_DIRS`) is correct in the main
checkout and **inverts inside a worktree**. `tools/lints/citations.py` filters on
`path.parts` — the parts of an *absolute* path — so every file in a worktree
rooted at `…/.claude/worktrees/agent-…/` carries `.claude` among its parts and is
skipped. The walk therefore reads **zero** files.

Measured on `phase-17` @ `c742e07`, in a worktree, with no `17-05` file on disk:

```
3 failed, 3421 passed, 118 skipped in 375.26s

FAILED tests/invariants/test_citation_coverage.py::test_the_citation_walk_is_not_vacuous
FAILED tests/invariants/test_citation_coverage.py::test_the_citation_scan_matched_something
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

with `The citation walk read 0 gated files, 953 expected.` The same three pass in
the main checkout, where the orchestrator measured 3424 passed / 0 failed / 118
skipped — the same 3424 total, partitioned differently.

**The direction is the safe one, and that is why it is deferred rather than
urgent.** It fails *closed*: the ratchet fires loudly rather than reporting a
green it did not earn. `python3 -m tools.lints --citations` itself is unaffected
and exits 0 in both places, because the ratchet is a coverage floor rather than
a finding count.

**The repair is one line** — filter on `path.relative_to(base).parts` in both
`iter_scanned_files` and `repo_index`, so the skip set describes the repository
rather than wherever the repository happens to be checked out. That makes the
gate correct in both places instead of correct in one.

**Consequence for anyone reading a worktree executor's numbers:** a `make
ci-core` run inside a worktree cannot be green until this lands, and every
`17-05`-era delta is stated against a 3-failing baseline for that reason.

---

## DEF-17-07 — a served `Result` does not expose the server's resolved instant — **DEFERRED TO WAVE 5 BY RULING**

**Found during:** plan `17-05`, raised as a deviation rather than decided.
**Status: OPEN, deliberately. Ruled by Dave 2026-08-15 to be settled in wave 5
(the conformance suite), not before.**

### The observation

A caller who passes `as_of=None` receives an answer but cannot read, from the
top level of `Result`, which instant the server actually resolved. `17-05` left
it out rather than adding it, because `D-08` enumerates **exactly six** guarded
post-assembly fields and a seventh would move a ruled boundary.

### Dave's ruling, and the reasoning

> *"Defer to Wave 5. Do not expand the ruled field set now."*

1. The six guarded fields are **a ruled boundary**. Adding a seventh is a design
   change, not a gap fill.
2. **The information is not missing.** The temporal boundary the product was
   assembled against is already carried inside the result the client receives.
   The open question is whether it needs a *first-class top-level field* — a
   question of surfacing, not of carrying.
3. The conformance suite is exactly where *"what every adapter must expose
   identically"* gets mechanized. Deciding it there keeps the decision tied to
   the **parity invariant** rather than adding an ad-hoc field under time
   pressure.

### The bar for reopening it

> *"If, during Wave 5, the suite (or real adapter work) shows that callers
> cannot reliably audit the decision instant without a dedicated field, we
> reopen it then with evidence. Until then the ruled boundary stays closed."*

So wave 5 must actively answer one question and record the answer either way:
**can a caller audit which clock answered, using only what a `Result` already
exposes?** If yes, this entry closes as "surfacing not required." If no, it
reopens with the measurement as its evidence.

---

## DEF-17-06 — the surface-manifest walk fails **silently** inside a worktree

**Found:** plan `17-06` execution, 2026-08-15. **Severity:** advisory for the
shipped tool, blocking for anyone measuring surface drift from a worktree.
**Status:** recorded, not fixed — the fix is a one-line `onerror=` and it is a
change to shared tooling that no plan in this phase owns.

**What was measured.** `tools/dump_surface.py --report` reported `added (0)`
in this worktree while two new `__all__`-bearing modules
(`ccf.client.adapters.binding_document`, `ccf.client.adapters.inprocess`) sat
in the tree. Forcing `PYTHONPATH=src:runtime` on the same command reported
`added (12)`.

**Why.** `iter_public_modules()` walks with
`pkgutil.walk_packages(search_path, prefix=...)` and **no `onerror`
callback**, so an `ImportError` raised while recursing into a subpackage is
**swallowed and the entire subtree is dropped**. The venv's editable install
resolves `ccf` to `/home/parkave/ccf_code/src/ccf` — the **main checkout** —
so from a worktree, `importlib.import_module("ccf.client.adapters")` fails for
any package the main checkout does not yet have. The walk finds the directory
on disk, cannot import it, and silently reports a smaller surface.

**Why it matters beyond convenience.** This is the phase's recurring defect
class in a new place: *a walk that skips what it cannot resolve, and goes quiet
exactly when the tree gets complicated.* `test_surface_drift.py` and
`test_surface_completeness.py` both consume this walk, so in a worktree they
pass **vacuously** over any newly added subpackage. Three surface gates
reported green in this worktree against a tree that had 12 undocumented public
names in it.

**What `17-06` did about it.** Measured with `PYTHONPATH` forced for every
surface operation, wrote the fragment against the 12 real names, and
regenerated `docs/surface/v0.2-surface.json` the same way — so the committed
manifest is correct in the main checkout, which is where it is read.

**The fix, when someone owns it.** Pass an `onerror` to `walk_packages` that
**raises**. A surface tool that cannot import a module in its own tree should
fail loudly; there is no case where "silently publish a smaller surface" is the
right answer. A control would plant an unimportable module under a `tmp_path`
package root and assert the walk raises rather than returning a short list.
