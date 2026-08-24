# Phase 23: The Archive Move — Retiring the Ten Condemned Example Trees Without Deleting Them - Context

**Gathered:** 2026-08-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The **ten** example trees `DOCS-17` condemns move **intact** to an archive
location outside `examples/`, out of the `examples:` aggregate and its ten
`make` targets, with every published snippet include and prose path re-pointed
so `make docs-strict` stays green. **NOTHING IS DELETED.** The paired tests
stay under `tests/` and are re-pointed, so the suite baseline does not move.
On completion `DOCS-17` is verdicted `Partial` for the first time.

**`CLNT-17` and the `s1` pair are NOT in this phase.** `CLNT-17` stays
`Not built` and no `s1` tree is moved, renamed or re-pointed.

**PHASE 23 MUST NOT INVENT A `CLNT-17` DISPOSITION.** Dave, at the scope lock
2026-08-24: *"Phase 23 should not invent a CLNT-17 disposition. Plan and execute
the archive move only."* This is a hard boundary, not a preference. The row's
framing is unresolved — its `refuse_request` blocker premise is FALSE on the
tree, and it may not be an example-retirement obligation at all — and that
question is Dave's and is to be settled BEFORE any attempt to close `CLNT-17`.
A plan, a test, a ledger cell or a commit message in this phase that assigns
`CLNT-17` any verdict, limb or disposition is a scope breach.

The sixteen Success Criteria are in the ROADMAP entry and were **LOCKED at this
sitting, before planning and before Wave 1** (`D-GATE-19`, `D-IMPL-174`).
</domain>

<decisions>
## Implementation Decisions

All six are Dave's rulings from this sitting, logged as `D-IMPL-190` and
`D-IMPL-191` in `docs/DECISIONS.md`. Two of them AMEND `D-IMPL-189`, and each
amendment names the old clause and the new one per the standing policy
`D-GATE-22` set for `D-IMPL-188`.

### Scope
- **D-01 (`D-IMPL-190` r1):** **Ten trees, not twelve.** `CLNT-17` and the `s1` pair are excluded and `CLNT-17` stays `Not built`. The entry as first drafted carried twelve; Dave's challenge — *"Isn't the s1 pair what we just completed, client side examples?"* — falsified it. The client-side pair is `hw1-*`. Three measurements decided it, and the argument is **not** cost-versus-benefit: (a) benefit is **zero**, both `s1` trees are already outside the `examples:` aggregate; (b) archiving `s1-01` would make a `D-IMPL-189` commitment false, since all 7 published `s1` references are to `s1-01` on the page Phase 22 shipped; (c) both trees are live fixtures for **core** suites — `tests/deployment`, `tests/products`, `tests/replay`, `tests/halflife` — not example tests.

### The paired tests
- **D-02 (`D-IMPL-190` r2):** **The paired tests STAY under `tests/`; only the sources move.** AMENDS `D-IMPL-189` point 1. **OLD:** *"their paired tests moved with them"*. **NEW:** they remain under `tests/` and are re-pointed. `pyproject.toml:142` sets `testpaths = ["tests"]`, so moving them removes 515 tests from the suite and drops the baseline from **4105/118** to roughly 3590 — a baseline four gates cite as proof of no behaviour change — to achieve a *documentation* archive. `D-IMPL-189`'s clause predates anyone checking `testpaths`.

### Archive shape
- **D-03 (`D-IMPL-191` r1):** **The archive lives OUTSIDE `examples/`**, so `examples/` keeps meaning *things we teach with*. Mechanically neutral — `pymdownx.snippets` resolves `base_path` against the repo root, not `public/`. **The path is PINNED to `archive/examples/…` by Dave 2026-08-24 at the scope-lock**; it is no longer the planner's to choose. This is a concretion WITHIN ruling 1, not a change to it, so no new `D-IMPL` entry is minted.
- **D-04 (`D-IMPL-191` r2):** **The archive stays RUNNABLE but ships NO `make` targets.** It must stay executable regardless, because two condemned-tree tests execute rather than read. All ten `example-0N`-family targets are **deleted, not renamed** — a target is an invitation to run, and these are no longer the teaching path.

### The sweep
- **D-05 (`D-IMPL-191` r3):** **Re-point the `Retirement` table; archived paths STILL count as couplings.** `tools/retirement_sweep.py:131-167` hardcodes the twelve trees against owners `16-15`/`16-17`/`16-18` (a RETIRED phase) and `17-08` (blocked at task 3) — nobody owns those rows today. The ten moved trees re-point to Phase 23 plans; the `s1` pair's `17-08` rows are left alone. Deletion is still owed, so an archived coupling is still a real obligation; a sweep blind to the archive would reproduce the exact defect Phase 22.1 was commissioned to fix.

### What the verdict may claim
- **D-06 (`D-IMPL-191` r4):** **The done-limb says "out of the `examples:` aggregate", NOT "out of live CI".** AMENDS `D-IMPL-189` point 3. After the move the trees leave the aggregate but **do not leave CI**: under D-02 the tests stay, so 25 of 31 `tests/examples` files still READ the archived sources and 2 still EXECUTE them. A cell reading *"out of live CI"* would be false on the day it is written — the `RECON-09` failure, the difference between a verdict and a hope. The cell must NAME what still exercises them.

### The four permitted `src/`/`runtime/` edits
- **D-07 (`D-IMPL-192`):** **Criterion 14 is AMENDED to permit EXACTLY FOUR path-string-only citation updates, and nothing else** under `src/`, `runtime/` or `pyproject.toml`. **OLD:** those three are diff-empty. **NEW:** diff-empty except the four below. They are `path::symbol` NODE IDS — the checked citation form — in shipped library docstrings, and they name condemned trees this phase moves:

| # | File | Line | Old → new |
|---|---|---|---|
| 1 | `src/ccf/products/bind.py` | 74 | `examples/04-cross-process/producer_child.py::resolve` → `archive/examples/04-cross-process/producer_child.py::resolve` |
| 2 | `runtime/ccf_runtime/mcp/egress.py` | 306 | same `04-cross-process` target |
| 3 | `runtime/ccf_runtime/mcp/experience.py` | 334 | same `04-cross-process` target |
| 4 | `runtime/ccf_runtime/mcp/experience.py` | 483 | `examples/external/00-hello-context/serve.py::context_provider` → `archive/examples/external/00-hello-context/serve.py::context_provider` |

  **Why this was blocking, measured by sabotage rather than argued:** `bind.py:74` was repointed at a non-existent `archive/...` path and `python -m tools.lints --all` **exited 0 with zero mentions** of the rule, the file or the bad path (restored byte-identical). `cite03-node-id` treats a node id whose PATH does not resolve as UNCHECKED; Phase 22's `test_every_published_node_id_resolves` closes that hole for `public/` **only**. Without the amendment the phase ships four citations pointing at nothing and **no gate can say so**.
  **Hard limits.** A **fifth** edit under any of the three members is a **scope breach**. Each of the four is proven **PATH-STRING-ONLY** — no symbol, signature, behaviour or surrounding prose altered — with the unmoved **4105 / 118** baseline as the mechanical proof. **The five `s1-01` citations are NOT touched** (`egress.py:304`, `experience.py:332`, `bind.py:76`, `request.py:365`, `request.py:558`), because `s1-01` is not moving.
  **A numbering correction, recorded because the ruling was requested against the wrong ordinal:** the exchange called this *"criterion 13"*; on the tree it is **criterion 14**. Criterion 13 is `CLNT-17`'s byte-identical protection — the one thing the same sitting said not to weaken. Dave's ruling names the criterion by CONTENT, which is unambiguous. **Criterion 13 is untouched and verified byte-identical against `HEAD`.**

### Claude's Discretion
- The archive's INTERNAL layout beneath `archive/examples/`, provided every include resolves. **The root path itself is NOT discretionary — it is pinned to `archive/examples/` (D-03).**
- How the include re-point is mechanized (path substitution vs. per-page edit), provided criterion 5's RED-before-GREEN control holds.
- Plan and wave decomposition.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The rulings that govern this phase
- `docs/DECISIONS.md` — `D-IMPL-189` (authorizes archive-with-repoint as an allowed intermediate state; **points 1 and 3 are AMENDED** — read `D-IMPL-190`/`191` before quoting it)
- `docs/DECISIONS.md` — `D-IMPL-190` (ten trees not twelve; paired tests stay)
- `docs/DECISIONS.md` — `D-IMPL-191` (archive outside `examples/`; runnable, no targets; sweep ownership; what `Partial` may claim)
- `docs/DECISIONS.md` — `D-IMPL-188` and its amendment (the standing policy: a pin moves only by an explicit entry naming old pin, new pin and why)
- `docs/DECISIONS.md` — `D-27` (forbids partial retirement; its `00`–`08` half is **undecided and Dave's**), `D-IMPL-176` point 2 (replacements before removals), `D-IMPL-145` limb 2 (the original quarantine), `D-IMPL-152` (Phase 16 retired)
- `CLAUDE.md` §3.1 — the close protocol: execution → cross-AI panel on the SHIPPED tree → single-agent depth pass → verify every finding → fix blockers in-phase → then Dave

### The requirement rows
- `.planning/REQUIREMENTS.md` — `DOCS-17` (this phase's row), `CLNT-17` (**excluded**; its `refuse_request` blocker premise is wrong on the tree — see the ROADMAP entry's findings)
- `.planning/ROADMAP.md` §Phase 23 — the sixteen LOCKED Success Criteria

### The machinery this phase touches
- `tools/retirement_sweep.py:131-167` — the `Retirement` table to re-point
- `tools/docs_tests/test_retirement_sweep.py` — `test_the_committed_report_is_current`
- `tools/docs_tests/test_no_stale_example_paths.py` — asserts every prose path AND every include resolves on disk
- `docs/surface/examples/RETIREMENT-COUPLINGS.md` — generated; regenerate **LAST**, in the venv, after every `.planning/` and `public/` write
- `mkdocs.yml` — `docs_dir: public`, `pymdownx.snippets` with `check_paths: true` and `base_path` resolved against the repo root
- `Makefile:256` — the eleven-member `examples:` aggregate
- `pyproject.toml:142` — `testpaths = ["tests"]`, the constraint behind D-02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The strict build is the primary witness.** `check_paths: true` makes a dangling include fatal, and `test_no_stale_example_paths.py` checks the same property independently. A half-finished repoint cannot go green. No new gate is needed for the core property — criterion 5 only has to prove the two witnesses are genuinely independent.
- **The fail-closed sweep (Phase 22.1)** can be trusted to say what is coupled; that is why this phase is sequenced after `D-GATE-22.1`.

### Established Patterns
- **Controls watched RED before GREEN, never argued.** Every recent phase proves each guard by sabotage and records predictions, including wrong ones.
- **Per-member pathspec diffs with a tracked-file guard** (`VAC-01`): a misspelled member diffs empty exactly like a clean one, so `ls-files > 0` is what separates them.
- **Foreground test chunks.** Background jobs on this host die at ~10 minutes and a killed run is indistinguishable from a pass; chunk coverage is proven by set-equality and disjointness, not assumed.

### Integration Points
- **The `D-11` scope fence is SAFE and needs no repair.** `D-IMPL-188` bounded the untouched-tree assertions to `base..951eb4a`, so this phase's 265-file write under `examples/` falls after the ceiling and is invisible to them. Verified: `test_requirement_ledger.py` scope/fence tests pass today. Phase 22 was bitten here only because the window was then `..HEAD`.
- **Side effect worth noting:** once this phase writes under `examples/`, that limb of the fence becomes self-proving in the way `public/` already is — closing part of `D-IMPL-188`'s open residual (*nothing asserts the bounded assertion READS the pin*) without targeting it.

</code_context>

<specifics>
## Specific Ideas

- The concrete benefit is stated as a figure, not an adjective: the always-on `examples:` job is **ten of eleven** condemned trees — 91% — and the sole survivor is `example-hw1-harness-clients`.
- `D-IMPL-189`'s own scope figures (*"99 snippet includes and 108 prose paths"*) **do not match the tree** and must not be quoted into any plan. The tree says **102 includes + 9 prose = 111**, which is `D-08`'s pinned figure and `21-04`'s re-measure. Named rather than silently corrected.

</specifics>

<deferred>
## Deferred Ideas

- **`CLNT-17`'s stated blocker is wrong on the tree** — its cell claims deleting `s1-01` strands *"the last shipped `examples/` call site of `refuse_request`"*, which is why `17-08-SUMMARY.md` reads `blocked-at-task-3`. There are **three** `.py` call sites and two are in `s1-00`. **Raised, expressly not ruled; no plan in this phase may act on it.**
- **`CLNT-17` may be mis-framed as an example-retirement row at all**, given that both `s1` trees are core-suite fixtures. If so, *"retire these example trees"* is the wrong obligation and will keep reading as owed work nobody can safely do. **Dave's ruling, not an executor's.**
- **BACKLOG (`D-IMPL-192`): a standing check that every `path::symbol` node id under `src/` and `runtime/` RESOLVES** — the counterpart to Phase 22's `tools/docs_tests/test_adoption_wording.py::test_every_published_node_id_resolves`, which covers the published tree only. This is the durable fix for the class `D-07` works around; until it exists, the workaround is a workaround. **Rejected as Phase 23 scope** — it is `D-06`'s twin and real work, not an archive move.
- **The `00`–`08` half of `D-27`** (deletion) remains undecided and Dave's.
- **`DOCS-14` / `EXAM-02`** still owe the replacement surface; `D-IMPL-176` point 2 sequences them before any removal.
- **The 27-item human-verification packet** is delivered and awaiting Dave (`D-20`); ten of nineteen decision items are live.
- **The archived pages teach the pre-Phase-15 integration surface** (Phase 14's `G-01`). The move relabels that; it does not close it.

</deferred>

---

*Phase: 23-the-archive-move-retiring-the-ten-condemned-example-trees-wi*
*Context gathered: 2026-08-24*
