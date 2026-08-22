# Phase 21: Requirement-Ledger Reconciliation — What Is Actually Discharged - Research

**Researched:** 2026-08-21
**Domain:** Repository-internal audit — ledger parsing, citation machinery, standing checks
**Confidence:** HIGH (everything below was measured in this session against the tree at `9455fc2`, branch `phase-21`)

> **Scope fence honoured.** This document reports the SHAPE of the work, never its ANSWERS.
> No requirement row is given a verdict here. No tracked file was modified. Two probes wrote
> to the tree and were reverted; `git status --porcelain` is empty at the time of writing.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Verdicts and their evidence go **in the traceability table's status cell**, in the
  shape Phase 15.6's `DCD-02`..`DCD-12` rows already use — bolded verdict, citations in
  parentheses, qualifying clause after an em dash. Not a separate `RECONCILIATION.md`.
- **D-02:** The ledger's **two status channels must stay in agreement** — the
  `- [ ] **ID**: …` checkbox list and the traceability table. A standing check asserts the
  agreement (criterion 10).
- **D-03:** A row may read `Complete` (or a 15.6-vocabulary variant) only with a
  **resolvable `path::symbol` citation** in its status cell. A citation the lint cannot
  resolve is not evidence.
- **D-04:** Where an existing test already guards the row's property, that test is **named
  alongside the citation**.
- **D-05:** **No test is written in this phase to manufacture such a name.**
- **D-06:** Reconciliation citations must be **full repo-relative paths**; a bare basename in
  a requirement row is **REFUSED by a standing check**.
- **D-07:** The lint is **not fixed here**. The repo-wide `F-3`/`WR-08` hole stays open and
  stays named; only this phase's own rows are placed out of its reach.
- **D-08:** The refusal in D-06 carries a **named sabotage control**: a row given a
  deliberately false or ambiguous citation is observably RED, as a standing test and not as a
  probe recorded in a SUMMARY (`D-IMPL-170`).
- **D-09:** Vocabulary is `Complete`, `Complete as ruled`, `Complete over the ruled scope`,
  `Partial`, extended by `Not built` and `Orphaned`.
- **D-10:** Every `Not built` and `Orphaned` verdict **names the specific absence** it rests on.
- **D-11:** `Not built` rows are delivered as a **scoped work list**. **Nothing on that list is
  built in this phase.**
- **D-12:** Phase 16's eighteen `DOCS-` rows are reported as a **two-sided split**, **left
  unflipped and undropped** pending Dave's ruling.
- **D-13:** The **24 `human_needed` verification items** across 9 phases are **named with their
  phases and left untouched**.
- **D-14:** The ten phases with no `D-GATE` entry are **not backfilled** — `D-IMPL-171`.
- **D-15:** `.planning/STATE.md` and `.planning/ROADMAP.md` are **hand-edited with a backup and
  a diff**, not written through `gsd-sdk query state.*` / `roadmap.*` handlers.
- **D-16:** Work happens on branch **`phase-21`**, not on `main`.

### Claude's Discretion

- Plan decomposition — one sequential pass or waves by phase-lane. The planner decides.
- Where the two standing checks live in the test tree, and whether they are one module or two.
- The exact status-cell grammar, provided it is recognisably the `DCD-` shape and a strict
  parse can read it.

### Deferred Ideas (OUT OF SCOPE)

- Fixing the ambiguous-basename hole in `tools/lints/citations.py` (`F-3`, `WR-08`).
- Building whatever the `Not built` verdicts identify.
- A dedicated phase for the 24 `human_needed` verification items.
- Reconciling the `progress:` block in `.planning/STATE.md` and the GSD plan counter.
</user_constraints>

---

## Project Constraints (from CLAUDE.md)

These are directives the planner must not plan around. Extracted verbatim in substance.

| § | Directive | Relevance to Phase 21 |
|---|-----------|----------------------|
| §2.2 | `main` is the approved-state branch; phase work on a phase branch; merge at `D-GATE-<Phase>`; **no force-push to `main`, ever** | D-16. Branch is `phase-21`; `main` is at `d15c1bf` [VERIFIED: `git rev-parse --short main`] |
| §2.2 | Commit at deliverable boundaries with a message naming the section or `D-IMPL-NN` it serves | Plan-level commit discipline |
| §3.1 | Execution → cross-AI panel (`/gsd-review --all`) → single-agent code review → verify every finding → fix blocking in-phase → **then** present to Dave. Close panel reviews the **shipped** artifact, written to `21-CLOSE-REVIEWS.md` | Criterion 14; the phase does not close on execution completing |
| §3.1 | **Verify every finding against the tree before recording or acting on it, and record rejected ones as rejected** | Reviewers in this project have produced confident false findings |
| §6.4 | No-Hardcoding Rule — no prompt/agent/task/threshold literal in `/src`, `/runtime`, `/examples` | Not engaged: this phase writes no such code |
| §11 | Every gate carries a sabotage control watched go red | D-08, criteria 5 and 12 |
| §11 | Zero harness imports in `/src`; `@algorithmic` purity | Not engaged, but `make lint` runs them and must stay green |
| §17 | **Plain English, short, no jargon, get to the point** when talking to Dave | The D-11 work list and the D-12 split are *for Dave*. One line per row, not an essay |

**Project skills:** `.claude/skills/` does not exist [VERIFIED: `ls`]. No project-local skill files to account for.

---

<phase_requirements>
## Phase Requirements

The phase mints its own `RECON-NN` at planning. **Recommended set — nine rows for fourteen
criteria, clustered by obligation rather than 1:1.** This follows the `CLNT-23`..`CLNT-32`
precedent, where `.planning/REQUIREMENTS.md` records that "the mapping to the ten Phase 20
Success Criteria is deliberately **not** 1:1 and must not be forced to be."

| ID | Obligation | ROADMAP criteria carried |
|----|-----------|--------------------------|
| **RECON-01** | Every one of the 54 not-`Complete` rows carries exactly one verdict, drawn from the six-word vocabulary, counted by a structural parse of the traceability table rather than a substring match | 1, 2 |
| **RECON-02** | Every non-`Not built`/`Orphaned` verdict cites a full repo-relative `path::symbol` the citation lint resolves, and names the guarding test where one already exists — with no test written to manufacture a name | 3, 6 |
| **RECON-03** | A bare basename, an ambiguous basename, or a path that does not exist as written in a requirement row is REFUSED by a standing check, carrying named sabotage controls that are observably red | 4, 5 |
| **RECON-04** | Every `Not built` and `Orphaned` verdict names the specific absence it rests on, and the `Not built` rows are delivered as a scoped work list with a one-line cost statement each | 7, 8 |
| **RECON-05** | Phase 16's eighteen `DOCS-` rows are reported as a two-sided split with evidence on both sides, left unflipped and undropped | 9 |
| **RECON-06** | The checkbox list and the traceability table agree on all 133 ids, asserted by a standing check with a non-vacuity control | 10 |
| **RECON-07** | The 24 `human_needed` items are named with their phases, stated as out of scope with the reason, and mechanically shown untouched | 11 |
| **RECON-08** | `src/` and `runtime/` are untouched against a base pinned before execution, with a control proving the diff assertion is not vacuous | 12 |
| **RECON-09** | The phase closes clean: `make ci` exit 0, `RETIREMENT-COUPLINGS.md` regenerated last, close panel + single-agent review run and triaged, `D-GATE-21` logged | 13, 14 |
</phase_requirements>

---

## Summary

The strict parse reproduces CONTEXT.md's figures exactly — **133 rows, 77 `Complete`,
53 `Pending`, 1 `Partial`, 1 `Complete as ruled`, 1 `Complete over the ruled scope`** — and the
54 that need a verdict are precisely the `Pending` ∪ `Partial` set, distributed across eight
phase lanes exactly as CONTEXT.md states. The two channels are at **0 drift across all 133
ids**, independently confirmed. **No planning-blocking finding on the count.** One definitional
correction is needed (§1): the literal string "not-`Complete`" yields **56**, not 54, because
`DCD-09` and `DCD-10` carry `Complete <qualifier>` verdicts already ruled by Dave; the 54 is
the *needs-a-verdict* set, and the checkbox channel independently confirms that reading by
having both those rows checked `[x]`.

The bigger finding is about evidence, not counting. **The citation lint has two silent-drop
holes, not one**, and both were reproduced in this session against the shipped `check_source`.
The known one is the ambiguous basename (`F-3`/`WR-08`). The second — undocumented in the phase
context — is that **a citation to a path that does not exist at all is also silently dropped,
not flagged**. Both are closed by one assertion the new standing check can make without opening
the lint: *the cited path must exist as written at repo root*. That makes `resolve_cited`'s
direct branch fire and the ambiguity branch structurally unreachable. Separately and more
consequentially: **`path::symbol` only works for `.py` files** — `NODE_ID`'s regex is anchored
to `\.py` — so for the twenty-four documentation rows in the Phase 14 and Phase 16 lanes there
is *no* checkable `path::symbol` form for the document itself. Those rows must cite the test
that guards the doc, which is a `.py::symbol` and is checked, or fall back to an anchored line
citation with a dot/kebab-namespaced anchor, which is the only markdown form the lint verifies.

The phase's real cost is not the audit. It is that `.planning/REQUIREMENTS.md` sits inside three
always-on machines at once: the citation lint (a bad citation turns `make lint` red mid-phase),
the retirement sweep (a citation naming a retiring path shifts a *generated* report and turns
`make ci` red — reproduced empirically here), and `make ci-core`, which "MUST stay green from
Wave 1 onward". A completeness assertion written in Wave 1 is red until the last row lands. The
plan sequence has to account for all three.

**Primary recommendation:** three lanes of audit work (Phase 17's 21 CLNT rows, Phase 16's 18
DOCS rows, the remaining 15) preceded by a Wave-0 plan that lands the shared structural parser
and the *invariant* halves of the two standing checks, and followed by a close plan that lands
the completeness count, regenerates `RETIREMENT-COUPLINGS.md` last, and asserts the pinned-base
fabric diff.

---

## Architectural Responsibility Map

This phase is an audit of planning documents. There is no runtime tier. The equivalent map is
by *machine that reads the file being edited*:

| Capability | Primary owner | Secondary | Rationale |
|------------|--------------|-----------|-----------|
| Verdict + evidence storage | `.planning/REQUIREMENTS.md` status cell | — | D-01; one place cannot drift from itself |
| Citation resolution | `tools/lints/citations.py` (unchanged) | — | D-07; the resolver already ships, the phase adds a refusal on top |
| Bare-basename / nonexistent-path refusal | new standing check, `tools/docs_tests/` | — | D-06; must be reached by `make gate-tools` |
| Two-channel agreement | same new standing check | — | D-02, criterion 10 |
| Generated coupling inventory | `tools/retirement_sweep.py --report` → `docs/surface/examples/RETIREMENT-COUPLINGS.md` | `tools/docs_tests/test_retirement_sweep.py` | Walks `.planning/`; must run LAST |
| Fabric-untouched proof | `git diff --stat <pinned base>..HEAD -- src/ runtime/` + a non-vacuity control | `21-BASE-COMMIT.txt` | Phase 20 precedent |
| Approval | Dave, `D-GATE-21` in `docs/DECISIONS.md` | — | CLAUDE.md §3.1 |

---

## 1. The Strict Parse — measured, not estimated

### The parse, as text (do NOT commit this as a tool; it is the algorithm the plan reimplements)

```python
# Read .planning/REQUIREMENTS.md. Locate the traceability table by its header line:
#     "| Requirement | Phase | Status |"
# Rows are the CONTIGUOUS run of lines starting with "|" after the separator row.
# Split each row on "|", strip, require EXACTLY 3 cells.
# Verdict token = the leading alphabetic run of the status cell after stripping "**",
#   cut at the first "(", "—" or "-":
#     re.match(r'^([A-Za-z][A-Za-z ]*?)(?=\s*[\(\—\-]|$)', cell.replace('**',''))
# The checkbox channel is every line matching:
#     r'^- \[([ xX])\] \*\*([A-Z]+-\d+)\*\*'
```

### What it returns, today, at `9455fc2`

| Measurement | Value | Source |
|---|---|---|
| Traceability table header | line **264** | [VERIFIED: parse] |
| Separator row | line **265** | [VERIFIED: parse] |
| Table rows | lines **266–398**, contiguous, **133 rows**, every one exactly 3 cells | [VERIFIED: parse] |
| Checkbox channel rows | lines **11–244**, **133 ids** | [VERIFIED: parse] |
| Id sets | **identical** — 0 ids in one channel and not the other | [VERIFIED: set difference both ways] |
| `Complete` | **77** | [VERIFIED] |
| `Pending` | **53** | [VERIFIED] |
| `Partial` | **1** (`DCD-02`, line 356) | [VERIFIED] |
| `Complete as ruled` | **1** (`DCD-09`, line 363) | [VERIFIED] |
| `Complete over the ruled scope` | **1** (`DCD-10`, line 364) | [VERIFIED] |
| **Total** | **133** ✅ | |
| **Rows needing a verdict** (`Pending` ∪ `Partial`) | **54** ✅ | [VERIFIED] |
| Channel drift, under `checked ⇔ status.startswith('Complete')` | **0** | [VERIFIED] |

**CONTEXT.md's figures are confirmed in full.** The lane breakdown is confirmed too (§2).

### The one correction, and it matters for criterion 1's wording

CONTEXT.md and ROADMAP criterion 1 both say **"not-`Complete`"**. Read literally — as a string
inequality against `"Complete"` — that set has **56** members, not 54, because it also contains
`DCD-09` (`Complete as ruled`) and `DCD-10` (`Complete over the ruled scope`).

The **54 is the correct working set**, and there are two independent reasons:

1. CONTEXT.md's own arithmetic intends it: `53 Pending + 1 Partial = 54`, and the by-phase
   breakdown it states (which includes exactly **1** for Phase 15.6, not 3) can only be produced
   by excluding `DCD-09` and `DCD-10`.
2. **The checkbox channel settles it independently.** Both rows are checked `[x]` in the
   checkbox list [VERIFIED: parse]. If they were "not Complete", the two channels would be at
   drift 2, and they are at drift 0. The project already treats a `Complete <qualifier>` row as
   Complete.
3. **D-09 forbids re-opening them by name**: *"a strict three-verdict scheme would re-open
   `DCD-02`, `DCD-09` and `DCD-10`, which Dave has already ruled on."*

**Not planning-blocking, but the plan must state the predicate.** Recommendation: the standing
parse defines the working set as *"the verdict token is not one of `Complete`, `Complete as
ruled`, `Complete over the ruled scope`"* — a **membership test against the Complete family**,
not a string inequality. That yields 54 and is stable if a fourth Complete-flavour ever appears.
Say this in the plan and in the SUMMARY, because a later reader running `grep -vc "| Complete |"`
will get 56 and think a row was skipped.

### Two adjacent stale counters the parse will expose (not this phase's criteria)

- `.planning/REQUIREMENTS.md` line ~437: *"Coverage: 94/94 v0.2 requirements mapped"* — the
  table has **133** rows.
- `.planning/ROADMAP.md` §Coverage: *"All **42** v0.2 requirements mapped"* — same.
- `.planning/ROADMAP.md` line 47 and the Phase 21 goal/rationale prose still say **52** in four
  places and list only six lanes (omitting Phase 15.5 and Phase 15.6), while criterion 1 says
  **54**. **The commissioning prose disagrees with the criterion it commissioned.** CONTEXT.md
  notes the criteria were amended in-session; the surrounding prose was not.

None of these is inside the fourteen criteria. Flag them to Dave with the audit rather than
fixing them silently — a phase about honest counters that quietly edits three counters without
saying so is the same defect one level up. If Dave wants them corrected, it is a hand-edit under
D-15 with a backup and a diff.

---

## 2. The Lanes — verified against the table

| Lane | n | Prefix | Ids | Kind of claim | Evidence cost per row |
|---|---|---|---|---|---|
| **Phase 17** | **21** | `CLNT` | `CLNT-01`..`14`, `16`..`22` | Testable behaviour + structural. Each row names its originating `D-NN` ruling and reads like an acceptance test ("exports exactly four names", "asserted by an equality on `__all__` rather than a membership check") | **LOW–MEDIUM.** Highest evidence density in the phase. Most rows almost certainly have an owning test in `tests/client/` or `tests/examples/`. Volume, not difficulty |
| **Phase 16** | **18** | `DOCS` | `DOCS-07`..`21`, `23`..`25` | Mixed: prose-about-docs (`DOCS-13`..`16`), structural-about-the-tree (`DOCS-10`, `-11`, `-17`), fabric behaviour (`DOCS-19`, `-23`..`-25`), and process (`DOCS-07`) | **HIGH.** Requires the D-12 split reasoning per row (§6), and `path::symbol` is unavailable for the prose ones (§4). The expensive lane |
| **Phase 14** | **6** | `DOCS` | `DOCS-01`..`06` | Prose-about-docs, plus one build claim (`DOCS-06`: `make docs --strict` in always-on CI) | **MEDIUM.** `DOCS-06`'s second limb is mechanically checkable; the rest are pedagogical-adequacy claims with the same problem the 24 `human_needed` items have |
| **Phase 9** | **3** | `HARD` | `HARD-01`..`03` | 1 process/ruling (`HARD-01` — a ruling batch surfaced to Dave), 2 testable behaviour (`HARD-02` thread-safe HITL transports + stress test; `HARD-03` loop-safe ADK driver + parity tests) | **LOW–MEDIUM.** `HARD-01`'s evidence is in `docs/DECISIONS.md`, which is `HISTORICAL_RECORDS`-exempt — a citation *into* it from REQUIREMENTS.md is still checked, but only in the anchored-line form (§4) |
| **Phase 13** | **3** | `EXAM` | `EXAM-01`..`03` | Structural-about-the-tree, each carrying an explicit `[Phase 16 re-homing, D-08]` sub-bullet that re-points the obligation at a different example | **MEDIUM.** The re-homing note means the row's subject moved; verdict must be against the *re-homed* target, not the original |
| **Phase 15.5** | **1** | `CPS` | `CPS-03` | Already carries a ~1500-word ruled evidence paragraph in the checkbox channel, closed by `D-IMPL-113` + `D-IMPL-121` | **LOWEST**, but see the open question in §11 — its ruled state is "Pending by design", which is **not in D-09's six-word vocabulary** |
| **Phase 15.6** | **1** | `DCD` | `DCD-02` | Already `**Partial**` with citations, ruled under `D-IMPL-119` limb 3(b) | **LOWEST.** Already in the target format and in vocabulary. Likely needs only confirmation |
| **Phase 18** | **1** | `CLNT` | `CLNT-15` | Testable behaviour — MCP product door carries client-supplied parameters, adapter passes the same conformance suite | **LOW.** Phase 18 is `D-GATE-18` approved; evidence is `tests/client/test_mcp_stdio_adapter.py` + the conformance suite |
| | **54** | | | | |

**Wave-sizing read.** Three natural lanes, and they are not equal-cost. The 21 CLNT rows are
volume against a dense evidence surface; the 18 DOCS rows are the intellectual work; the
remaining 15 split into 6 medium (Phase 14) and 9 cheap-to-medium (Phases 9, 13, 15.5, 15.6, 18).
Recommend the DOCS-16 lane get its own plan or two, and that it run *after* the CLNT lane, so
the executor has calibrated what a good citation looks like before hitting the hard rows.

---

## 3. Where Evidence Lives — the search surface, per lane

Directories and modules a verdict would most likely cite. **No row is resolved here.**

### Phase 17 lane (`CLNT-01`..`14`, `16`..`22`)

| Surface | What it holds |
|---|---|
| `src/ccf/client/` | `__init__.py`, `client.py`, `binding.py`, `codec.py`, `errors.py`, `result.py`, `wire.py`, `adapters/` [VERIFIED: `ls`] |
| `tests/client/` | `test_client.py`, `test_binding.py`, `test_binding_document.py`, `test_codec.py`, `test_result_guard.py`, `test_surface.py`, `test_wire.py`, `test_inprocess_adapter.py`, `test_mcp_stdio_adapter.py`, `test_no_provisioning.py`, `test_data_only_deployment.py`, `conformance/` [VERIFIED: `ls`] |
| `tests/examples/` | `test_client_example_purity.py`, `test_client_example_budget.py`, `test_hw1_two_transports.py` |
| `examples/hw1-companies-over-revenue/` | the `consume.py` + opaque `deployment/` example `CLNT-13` names |
| `tools/retirement_sweep.py` + `tools/docs_tests/test_retirement_sweep.py` | `CLNT-16`'s sweep-green claim |
| `Makefile`, `.github/workflows/ci.yml` | `CLNT-14`/`CLNT-16` gate-reachability claims |

### Phase 16 lane (`DOCS-07`..`21`, `23`..`25`)

| Surface | What it holds |
|---|---|
| `.planning/phases/16-*/RETIRED.md` | **authoritative for the split** (§6) |
| `.planning/phases/16-*/16-{01..06,21..25,27..31}-SUMMARY.md` | the 16 plans Phase 16 *did* execute — six pre-retirement, ten after. Grep shows they name `DOCS-17`, `-19`, `-20`, `-21`, `-22`, `-23`, `-24`, `-25` [VERIFIED: grep] |
| `.planning/phases/16-*/abandoned/16-{07..20}-PLAN.md` | the 14 unexecuted plans. **Readable as history, never as a work queue** (RETIRED.md) |
| `.planning/phases/{15.1,15.2,15.4,15.5,15.6,15,16,17,18.1}/deferred-items.md` | nine files, the live phase-to-phase hand-off contract [VERIFIED: `ls`]. `MAINTAINED_RECORDS` pulls them back into the citation gate |
| `examples/` | `00-quickstart` … `08-e2e-demo` **all nine still present**, plus `external/`, `hw1-*`, `s1-00`, `s1-01` [VERIFIED: `ls`] |
| `public/` | `tutorial/`, `concepts/`, `how-to/`, `reference/`, `diagrams/`, `charter.md`, `index.md` |
| `docs/schemas/`, `docs/surface/`, `docs/retired/16-external-consumers/` | schema, surface and retired-consumer artefacts |
| `src/ccf/deployment/`, `src/ccf/products/` | `DOCS-19`'s four `D-IMPL-126` papercuts; `DOCS-23`..`25`'s `ccf_config.yaml` work |
| `runtime/ccf_runtime/mcp/` | `DOCS-20` (parameterised tool), `DOCS-21` (Experience server handlers) |

### Phase 14 lane (`DOCS-01`..`06`)

`public/tutorial/adopters-guide.md`, `public/concepts/`, `public/how-to/`, `public/reference/`;
`mkdocs.yml`; `tools/docs_tests/` (`test_mkdocstrings_gate.py`, `test_diagram_coverage.py`,
`test_documented_commands_exist.py`, `test_snippet_gate.py`, `test_openapi_drift_control.py`);
`Makefile::docs-strict`; `docs/PERFORMANCE.md`; `.github/workflows/`.

### Phase 9 lane (`HARD-01`..`03`)

`docs/DECISIONS.md` (`HARD-01`'s ruling batch); `src/ccf/hitl/` + `tests/hitl/` (`HARD-02`);
`runtime/ccf_runtime/adapters/adk/` + `tests/harness/` + `tests/workflow/` (`HARD-03`).

### Phase 13 lane (`EXAM-01`..`03`)

`examples/*/README.md`; `examples/s3-02-agentic-skills` (the `EXAM-02` re-homing target);
`Makefile`'s `example-s*` targets (the `EXAM-03` re-homing target); `tests/examples/`.

### Phases 15.5 / 15.6 / 18 singletons

`CPS-03` → `src/ccf/products/bind.py`, `src/ccf/products/request.py`,
`runtime/ccf_runtime/mcp/egress.py`, `tools/docs_tests/test_resolver_seam_obligations.py`,
`examples/s1-01-hello-context-product/spine.py` — all already cited in the row's own prose.
`DCD-02` → already cited (plans `15.6-05`, `15.6-06`).
`CLNT-15` → `src/ccf/client/adapters/`, `tests/client/test_mcp_stdio_adapter.py`,
`tests/client/conformance/`.

---

## 4. The Citation Lint's Actual Behaviour — read AND reproduced

All line citations below are against `tools/lints/citations.py` at `9455fc2`.

### (a) How a `path::symbol` citation is resolved

1. `NODE_ID` (`citations.py:251-253`) matches
   `(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.py)::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)`.
   **The path group is hard-anchored to `\.py`.** There is no `::symbol` form for any other
   suffix.
2. `check_source` (`citations.py:596-618`) iterates `NODE_ID.finditer(line)` and calls
   `resolve_cited(cited, base, index)` (`citations.py:429-449`).
3. `resolve_cited` returns `(path, ambiguous)`:
   - `base / cited` is a file → `(direct, False)` — **resolved outright, index never consulted**.
   - otherwise treat as a suffix; `candidates = [c for c in index[basename] if c == cited or
     c.endswith("/" + cited)]`; **exactly one** → `(base / candidates[0], False)`.
   - **zero or ≥ two candidates** → `(None, len(candidates) > 1)`.
4. If `target is None`, `check_source` bumps `ambiguous_path` or `unresolved_path` and
   **`continue`s — no finding** (`citations.py:601-605`, with the docstring comment saying an
   unresolvable path in a symbol citation "is unchecked rather than a finding").
5. Otherwise `symbol in cache.spans(target)` → `checked`, else a `cite03-node-id` **finding**.
   `symbol_spans` (`citations.py:475`) is an AST walk over `def`/`class`/module-level bindings.

### (b) Where an ambiguous basename is silently dropped — and a second hole

Reproduced against the shipped `check_source` with the real repo index:

| Citation written into a status cell | Result | Verdict |
|---|---|---|
| `` `src/ccf/client/client.py::ProductClient` `` | `findings=0, tally={'total':1,'checked':1}` | ✅ checked and clean — **the target form** |
| `` `src/ccf/client/client.py::NoSuchThing` `` | `findings=1` (`cite03-node-id`) | ✅ **RED** — a wrong symbol on a real path is caught |
| `` `client.py::NoSuchThing` `` | `findings=0, tally={'ambiguous_path':1}` | ❌ **silently dropped** — `client.py` has 2 paths. This is `F-3`/`WR-08` |
| `` `spine.py::NoSuchThing` `` | `findings=1` | a *unique* bare basename **is** checked — only ambiguous ones drop |
| `` `src/ccf/nope/nope.py::x` `` | `findings=0, tally={'unresolved_path':1}` | ❌ **silently dropped** — **SECOND HOLE, not named in CONTEXT.md**: a path that does not exist at all is not a finding |
| `` `public/tutorial/adopters-guide.md` `` (bare, no `:NN`) | `tally={}` — matches **neither** regex | ❌ **entirely invisible** |
| `` `intro` `public/tutorial/adopters-guide.md:3` `` (plain-word anchor) | `tally={'unusable_anchor':1}` | ❌ unchecked |
| `` `ccf.no-such-token` `public/tutorial/adopters-guide.md:3` `` | `findings=1` (`cite02-anchor`) | ✅ **RED** — a *tokenish* anchor (contains `.` or `-`) IS checked against markdown |
| `` `intro` `public/tutorial/adopters-guide.md:99999` `` | `findings=1` (`cite01-resolves`) | ✅ RED — out-of-range lines are caught regardless of anchor |

**Anchor rules** (`_anchor_verdict`, `citations.py:547-567`): for a `.py` target a `_SYMBOLISH`
anchor is checked against the symbol's span; for **any** target a `_TOKENISH` anchor
(`^[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)+$` — dot- or kebab-namespaced) is checked as a literal
substring of the cited lines; **everything else returns `None` and is silently unchecked**.
`anchor_before` (`citations.py:459-473`) requires the backticked span to sit immediately before
the citation with only punctuation and `_GAP_WORDS` between.

**Tree-wide census today** [VERIFIED: `python -m tools.lints --citations --report`]:
`1042 matched in 1105 files (592 exempt)`; `checked 623`; `findings 0`; `historical 42`;
`no anchor 336`; `anchor not resolvable 13`; **`path ambiguous 15`**; **`path unresolvable 13`**.

**Ambiguity census in the trees this phase will cite**: **47** ambiguous `.py` basenames
(`__init__.py` 90 paths, `conftest.py` 13, `adapter.py` 4, `agent.py`/`artifact.py`/`config.py` 3,
`client.py`/`client_adk.py`/`client_anthropic.py`/`client_langgraph.py`/`consume.py`/`base.py`/…
2 each) [VERIFIED].

### (c) What `GATED_TREES` / `HISTORICAL_RECORDS` / `MAINTAINED_RECORDS` mean for `.planning/REQUIREMENTS.md`

| Constant | Line | Effect on `.planning/REQUIREMENTS.md` |
|---|---|---|
| `GATED_TREES` (`citations.py:153-166`) | includes `".planning"` | **walked** |
| `SCANNED_SUFFIXES` (`:203`) | includes `.md` | **read** |
| `HISTORICAL_RECORDS` (`:172-193`) | the only `.planning` pattern is `.planning/phases/*` | **does NOT match** `.planning/REQUIREMENTS.md` |
| `MAINTAINED_RECORDS` (`:200`) | `.planning/phases/*/deferred-items.md` | irrelevant here; pulls the nine `deferred-items.md` back in |
| `exemption_reason(".planning/REQUIREMENTS.md")` | `:337-344` | returns **`None`** [VERIFIED: called it] |
| In `iter_scanned_files` output | `:347-363` | **`True`** [VERIFIED: called it] |

**Confirmed: citations written into `.planning/REQUIREMENTS.md` are gated by machinery that
already ships.** Current state of that file: **39 citations, 35 checked, 0 findings**, 2
historical, 2 unusable-anchor. The 35 checked are all `NODE_ID` (`.py::symbol`); there are only
4 line citations in the whole file [VERIFIED]. **The ledger's existing evidence discipline is
already exactly what D-03 mandates, and it works.**

### (d) What the NEW standing check must assert, without touching the lint

> **For every citation-shaped token inside a traceability-table status cell, the cited path
> must exist as written at repo root — `(REPO_ROOT / cited).is_file()` must be `True`.**

That single predicate closes **both** silent-drop holes at once, because:

- a path that exists as written makes `resolve_cited` return at its **direct** branch
  (`citations.py:432-434`) before the index is consulted, so the ambiguity branch is
  **structurally unreachable** for this file's citations — D-06 satisfied without D-07 violated;
- a nonexistent path is refused here rather than counted as `unresolved_path` and dropped.

Three companion assertions the same check should carry, none of which touches the lint:

1. **Suffix discipline.** A `::symbol` citation must name a `.py` path, because `NODE_ID`
   cannot match anything else. A `docs/foo.md::heading` would be invisible; refuse it by name.
2. **Vacuity guard.** Refuse when the parse finds **zero** rows or **zero** citations. An
   "every citation is a full path" assertion over an empty set passes trivially — the exact
   shape Phase 20's `CONTROL 6` was written to catch.
3. **The check is a function of its argument**, not of the tracked file. It takes the document
   text (or a path) so a control can hand it a doctored table. Copy the `client_surface_diff`
   design at `tests/examples/test_hw1_harness_clients_readme.py:468-500`, whose docstring says
   exactly why.

---

## 5. How the Two Standing Checks Should Be Built

### Where they belong

`make gate-tools` (`Makefile:188-190`) is two legs [VERIFIED: both run green]:

```
$(ENV_DOCS) $(PYTHON) -m pytest tools/lints/tests -q                       # 406 passed
$(ENV_DOCS) $(PYTHON) -m pytest tools/publish_scan_tests tools/docs_tests -q # 154 passed
```

`ENV_DOCS := PYTHONPATH=.:src:runtime` (`Makefile:23`) and `PYTHON := .venv/bin/python`
(`Makefile:10`). **Both are required** — system `python3` cannot import `ccf_runtime` and
leg 2 fails to collect. `gate-tools` is inside both `ci-core` (`Makefile:138`) and `ci`
(`Makefile:172`), so anything landed in either leg runs in always-on CI.

**Recommendation: `tools/docs_tests/test_requirement_ledger.py`, one module carrying both
checks.** Reasons: `tools/lints/tests/` tests the `tools/lints/*` *modules*, and there is no
lint module behind a ledger check; `tools/docs_tests/` already holds document-shaped gates that
read tracked files (`test_documented_commands_exist.py`, `test_no_stale_example_paths.py`,
`test_gate_two_wording.py`, `test_retirement_sweep.py`, `test_advisory_discharge.py`
[VERIFIED: `ls`]). And both checks need **the same structural parser**; a shared parser in one
module is one thing that can drift instead of two. This is Claude's discretion per CONTEXT.md —
the planner may split, but should not duplicate the parser.

**No existing REQUIREMENTS.md parser to reuse** — `grep -rln 'REQUIREMENTS.md' tools/ tests/`
returns only `citations.py` and `test_citations.py`, both prose mentions [VERIFIED]. Greenfield.

### What the existing tests look like structurally

From `tools/lints/tests/test_citations.py` [VERIFIED: read]:

- Module docstring names **what the check was written for** and states that *"The first test in
  the file is the **watched-to-fail** case … That pair is what makes the check a discriminator
  rather than a tripwire that is always red or always green."*
- `from __future__ import annotations`, stdlib `pathlib`, then a flat import of the public
  names under test.
- Small module-level helpers: `_write(base, rel, text) -> pathlib.Path`, `_rules(findings)`.
- Module-level fixture constants named for their role: `_CITED_BEFORE`, `_CITED_AFTER`, `_CITER`,
  with `#:` comments explaining the single difference between them.
- Section banners: `# --- the watched-to-fail pair ---`.
- **Test names are sentences**: `test_the_citation_is_clean_before_the_docstring_edit`,
  `test_a_door_that_serialized_around_the_vessel_would_be_detected`. Every test carries a
  docstring saying which half of the discrimination proof it is.
- Real two-file trees under `tmp_path` rather than string fixtures, "because a citation is a
  claim about a *second* file".

The new module should read like this.

### How each sabotage control is written so it is a STANDING test (D-08, `D-IMPL-170`)

`D-IMPL-170`, in Dave's words: *"A control is something the suite can still run and that can
still go red. A narrative measurement in a SUMMARY is evidence that someone looked once; it is
not enforcement."* The required shape is a standing test that is *observably red when the
property is broken*, **not solely a paragraph in a plan SUMMARY**.

The mechanism that makes this possible without a red suite: **the checker is a pure function of
a document, and the control calls it with a DOCTORED document.** The shipped assertion calls it
with the real file. Both are green in CI; the control is green *because* it observed the
refusal fire. This is exactly `client_surface_diff`'s design.

**Check A — bare-basename / unresolvable-path refusal (criteria 4, 5)**

```
def cited_paths(document_text) -> list[Citation]      # parse status cells → citations
def refuse_unresolvable(document_text) -> list[str]   # the refusals, as messages
```

| Test | Subject | Asserts |
|---|---|---|
| shipped assertion | the real `.planning/REQUIREMENTS.md` | `refuse_unresolvable(...) == []` |
| CONTROL 1 | table with `` `client.py::ask` `` (a **two-path** basename) | refused, and the message names the ambiguity |
| CONTROL 2 | table with `` `spine.py::ask` `` (a **unique** basename) | refused too — D-06 is *full paths*, not *unambiguous paths*; a unique basename becomes ambiguous the day someone adds a second file |
| CONTROL 3 | table with `` `src/ccf/nope/nope.py::x` `` (does not exist) | refused — closes hole two |
| CONTROL 4 | table with `` `docs/foo.md::heading` `` | refused — `::symbol` on a non-`.py` path is invisible to `NODE_ID` |
| CONTROL 5 (vacuity) | a document with the table header and **no rows**; and a document with rows and **no citations** | **raises/refuses**, does not return `[]`. Without this the whole check passes on a parse that silently found nothing |
| positive control | table with `` `src/ccf/client/client.py::ProductClient` `` | **not** refused — proves the check is not red-on-everything |

**Check B — two-channel agreement (criterion 10)**

```
def parse_checkbox_channel(text) -> dict[str, bool]
def parse_traceability_table(text) -> dict[str, Verdict]
def channel_disagreements(text) -> list[str]
```

| Test | Subject | Asserts |
|---|---|---|
| shipped assertion | the real file | 133 ids each side, **identical id sets**, `checked ⇔ verdict ∈ Complete-family`, disagreements `== []` |
| CONTROL 6 | doctored: one row flipped to `Complete` in the table, `[ ]` in the list | **refused, naming the id** |
| CONTROL 7 | doctored: an id present in the table and absent from the list | refused |
| CONTROL 8 (vacuity) | a document whose table header is misspelled, so the table parse returns `{}` | **refused**, not "0 disagreements, clean" |
| CONTROL 9 | doctored: a verdict token outside the six-word vocabulary | refused (this also carries criterion 2 mechanically, for free) |

### ⚠️ The sequencing constraint the planner must not miss

`Makefile:138` — `ci-core: … ## Mid-phase verification sweep — **MUST stay green from Wave 1
onward**`.

A standing assertion that *"all 54 rows carry a verdict"* is **RED from the moment it lands
until the last row is written**. Landing it in Wave 0 breaks `ci-core` for the whole phase.

**Recommendation — split by tense:**

| Lands | Property | True throughout the phase? |
|---|---|---|
| **Wave 0** | every citation present is a full, existing, `.py`-for-`::` path | ✅ yes — vacuously true at zero verdicts, and true after each one |
| **Wave 0** | the two channels agree | ✅ yes — held at 0 drift today, and each edit must preserve it |
| **Wave 0** | every verdict token present is in the six-word vocabulary | ✅ yes |
| **Wave 0** | no cell carries two verdict tokens | ✅ yes |
| **Final plan** | the 54-row completeness count | ❌ **red until the last row** — land it last |

This also means Wave 0's checks *actively guard the audit while it happens* rather than only
grading it at the end, which is strictly better.

---

## 6. The `DOCS-07`..`NN` Split (criterion 9 / D-12)

`.planning/phases/16-*/RETIRED.md` is authoritative and is unambiguous about the distinction.

> **"THE PLAN SET IS RETIRED. THE OBLIGATIONS ARE NOT DISCHARGED."** … *"Retiring the phase
> retires **the approach**, not **the need**."* … *"When each becomes current it must be
> **re-derived against the surface that exists then**, not lifted from `abandoned/`."*

### The criterion the executor applies

Not "was the plan executed" — the plans are irrelevant. **"Does the obligation the row states
have a satisfied referent in the tree as it stands today?"** Three outcomes, not two:

| Side | Test | Verdict | Evidence surface |
|---|---|---|---|
| **A — re-derived and satisfied** | The obligation's *substance* was carried forward and shipped by a later phase against the surface that now exists | `Complete` / `Complete as ruled` / `Complete over the ruled scope` | The later phase's tree: `src/ccf/client/`, `examples/hw1-*`, `runtime/ccf_runtime/mcp/`, `tests/`, `public/`; the later phase's SUMMARYs; `deferred-items.md` chains |
| **B — still owed, referent exists** | The obligation is coherent against today's surface and simply has not been done | `Not built` — and it goes on Dave's work list (D-11) | The **named absence**: the file that is not there, the test that does not exist, the directory that was to be retired and is not |
| **C — orphaned** | The obligation is *about* the rejected surface and has no referent now — satisfying it would mean rebuilding something the project deliberately walked away from | `Orphaned` — with the specific absence named (D-10) | `RETIRED.md`'s "Why the plans cannot simply be resumed"; the abandoned plan text as *history*; the rejected artefacts under `docs/retired/` |

**A row can be split across sides and must then say so** — the `Partial` verdict exists for
exactly this, and `DCD-02` is the in-tree model.

### The measured evidence surfaces

- **`RETIRED.md`'s obligation table** maps each abandoned plan to the obligation it carried:
  `16-07` backend-from-configuration-artifact; `16-08` staleness/half-life in the adoption
  argument; `16-09` harness portability across three harnesses (§9 example 03); `16-10`
  cross-process over MCP **and A2A** (§9 example 04); `16-11` archetype → agent artifact →
  factory → skill catalog → grant/revoke (§9 examples 01–02); `16-12` `make ci`'s documented
  claim made true; `16-13`–`16-20` adopters guide, examples migration, docs gates, review
  protocol. **This table is the starting index for side A/C, not the answer.**
- **Phase 16 executed 16 plans, not 6.** `16-01`..`06` (pre-retirement, through 2026-08-10) and
  `16-21`..`25`, `16-27`..`31` (through 2026-08-15) [VERIFIED: `ls` + `git log`]. Their SUMMARYs
  name `DOCS-17`, `-19`, `-20`, `-21`, `-22`, `-23`, `-24`, `-25` [VERIFIED: grep]. Only
  `DOCS-22` is ticked. **Eight of the eighteen have in-phase executed work that was never
  reflected in the ledger** — that is the single densest side-A lead in the phase.
  *(`RETIRED.md`'s "executed 6 of 21" is true as of 2026-08-17 for the original plan set;
  ROADMAP's "16/16 executed" counts the later ten. Both are right about different sets. The
  executor should not read either as a contradiction.)*
- **The nine `deferred-items.md` files** are the live hand-off contract and are inside the
  citation gate via `MAINTAINED_RECORDS` — an obligation that travelled forward left a trace
  there.
- **The counter-evidence is in `examples/`**: all nine of `00-quickstart` … `08-e2e-demo` are
  **still present**, alongside `external/` [VERIFIED: `ls`]. `DOCS-17` requires their retirement.

### The `path::symbol` problem, restated for this lane

Roughly half of these eighteen rows are prose-about-documentation. Per §4(a), `NODE_ID` matches
**`.py` only**, so `public/foo.md::heading` is not a citation at all. Criterion 3 is satisfiable
for these rows in exactly three ways, in preference order:

1. **Cite the guarding test** — `tools/docs_tests/test_x.py::test_y` or
   `tests/examples/test_z.py::test_w`. A `.py::symbol`, fully checked, and it also discharges
   D-04. *This should be the default for every doc row that has one.*
2. **Cite the document with an anchored line citation** where the anchor is a dot- or
   kebab-namespaced token that literally appears in those lines (§4(b) row 8). Checkable, but
   fragile and only works when such a token exists.
3. **`Not built` / `Orphaned` with a named absence** (D-10). No citation obligation.

**What is forbidden:** writing a test so a row can cite one (D-05). If a doc row has no guarding
test and no tokenish anchor, the honest outcome is option 3 or a `Partial` that says so.

---

## 7. The 24 `human_needed` Items (criterion 11 / D-13)

`gsd-sdk query audit-uat --raw` returns `{"results": [...], "summary": {...}}`.
**Confirmed: 24 items across 9 phases** [VERIFIED].

| Phase | Items | File path — cite these verbatim, do not re-derive |
|---|---|---|
| 11 | 1 | `.planning/phases/11-performance-battery/11-VERIFICATION.md` |
| 13 | 1 | `.planning/phases/13-examples-suite-upgrade/13-VERIFICATION.md` |
| 14 | 2 | `.planning/phases/14-documentation-suite/14-VERIFICATION.md` |
| 15.1 | 2 | `.planning/phases/15.1-ergonomics-gap-closure/15.1-VERIFICATION.md` |
| 15.2 | 2 | `.planning/phases/15.2-substrate-adapters-and-query-pushdown/15.2-VERIFICATION.md` |
| 15.3 | 5 | `.planning/phases/15.3-fluree-adapter-tier-1-substrate-inserted/15.3-VERIFICATION.md` |
| 15.4 | 5 | `.planning/phases/15.4-backend-registration-seam-the-substrate-stops-naming-its-ada/15.4-VERIFICATION.md` |
| 18.1 | 3 | `.planning/phases/18.1-simplify-the-mcp-example-separate-the-server-from-the-client/18.1-VERIFICATION.md` |
| 19 | 3 | `.planning/phases/19-the-client-seam-integrity-checks-must-be-able-to-fail-insert/19-VERIFICATION.md` |
| | **24** | **9 files** |

Matches D-13's list exactly (11, 13, 14, 15.1–15.4, 18.1, 19).

⚠️ **Data-quality caveat:** Phase 15.1's two items return `name`, `expected` and `why_human` all
as the literal string `">-"` [VERIFIED] — a YAML folded-scalar artefact in the query, not in the
source. **Read `15.1-VERIFICATION.md` directly for those two**; do not paste `">-"` into the
phase record.

**The "left untouched" limb is mechanically assertable for free** — reuse the criterion-12 diff
helper over these nine paths: `git diff --stat <pinned base>..HEAD -- <the nine>` prints
nothing. Recommend it; it costs one line and turns an inspection claim into an observation.

---

## 8. The Untouched-Fabric Proof (criterion 12)

Phase 20's criterion 7 is the model and it is directly reusable.

### How the base is pinned

`.planning/phases/20-*/20-BASE-COMMIT.txt` [VERIFIED: read] — the SHA alone on line 1, followed
by comment lines naming what reads it:

```
9e4bd0e5c54c22133f32c108b96de3aebbf6dfae
# The Phase 20 diff base. Read by plan 20-08's criterion-7 assertion:
#   git diff --stat $(head -1 <this file>)..HEAD -- src/ccf/client/
# must print nothing. Pinned here at plan 20-01 rather than resolved at close
# time from a branch name, because a base that does not resolve makes the
# assertion vacuous rather than failing it.
```

Written at **plan 20-01** (the first plan), not at close. `D-GATE-20` records the reason
verbatim. The SHA is validated by `git cat-file -t` resolving as `commit`.

### How the control proves the assertion is not vacuous

`tests/examples/test_hw1_harness_clients_readme.py:468-500` ships `client_surface_diff(base,
paths) -> str` — **a function of its arguments**, with three refusals rather than a quiet empty
string: empty base, empty path list, and non-zero `git` exit. Its docstring states the problem
plainly: *"an empty string from a failed command is indistinguishable from an empty string from
a clean tree."*

Two controls, both observed red by mutating the **shipped function** and restoring from backup:

| Control | Subject | Mutation | Observed |
|---|---|---|---|
| CONTROL 6 | base `9e4bd0e`, path `examples/` — a pair that **genuinely differs** (17 stat lines) | `return completed.stdout` → `return ""` | test FAILED **while both shipped emptiness assertions still PASSED** |
| CONTROL 7 | base = 40 zeros (unresolvable) | `if completed.returncode != 0:` → `if False:` | test FAILED |

`20-08-SUMMARY.md` records why CONTROL 6 earned its place: under its mutation pytest reported
`1 failed, 2 passed` — *"Without CONTROL 6 the phase would have closed on two green assertions
over a comparison that never happened, which is the exact shape this project has recorded across
Phases 17, 18.1 and 19."*

### For Phase 21

- Write `.planning/phases/21-*/21-BASE-COMMIT.txt` **in the first plan**, holding the SHA at
  which execution starts (today HEAD is `9455fc2`; `main` is `d15c1bf`; `git diff --stat
  main..HEAD -- src/ runtime/` is already **empty** [VERIFIED]).
- Copy the `client_surface_diff` shape as e.g. `fabric_diff(base, paths)`, with the same three
  refusals.
- **Widen the paths to `src/ runtime/`** — criterion 12 names both, where Phase 20's criterion 7
  named only `src/ccf/client/`.
- Reuse the same helper for the criterion-11 nine-file untouched assertion (§7).
- ⚠️ **`fetch-depth: 0`.** `D-GATE-20` records that the `tests` CI job ran on a **shallow
  clone**, so a pinned base did not resolve and the assertions reading it *could not run*. Fixed
  at `921e3b9`. The fix is on `main`; verify it is still there before relying on the assertion in CI.

---

## 9. The Generated-Report Hazard (criterion 13)

**Confirmed and reproduced.**

- `tools/retirement_sweep.py:216` — `REPORT_PATH = REPO_ROOT / "docs" / "surface" / "examples" /
  "RETIREMENT-COUPLINGS.md"`.
- `tools/retirement_sweep.py:199` — `(".planning/", "the phase's own planning tree — not
  shipped, not published")` sits in **`EXCLUDED_FROM_ASSIGNMENT`**, whose docstring says
  *"measured but deliberately not assigned an owner … **Their hit counts are reported so the
  exclusion is visible rather than silent**."* So `.planning/` **is walked and its counts do
  appear in the report** — the entry is an ownership exclusion, not a walk exclusion.
- The committed report today carries `` | `.planning/REQUIREMENTS.md` | **15** | … | ``
  (`docs/surface/examples/RETIREMENT-COUPLINGS.md:309`) [VERIFIED].
- `tools/docs_tests/test_retirement_sweep.py:839
  ::test_the_committed_report_is_current` asserts `REPORT_PATH.read_text() == render(head())`.
  It runs inside `make gate-tools` leg 2, therefore inside `ci-core` **and** `ci`.

**The empirical probe** (run and reverted; tree left clean):

```
# baseline: report current, git status clean
echo "probe: examples/00-quickstart/run.py" >> .planning/REQUIREMENTS.md
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
git diff --stat -- docs/surface/examples/RETIREMENT-COUPLINGS.md
#  → docs/surface/examples/RETIREMENT-COUPLINGS.md | 2 +-
#    1 file changed, 1 insertion(+), 1 deletion(-)
git checkout -- .planning/REQUIREMENTS.md && <regenerate>   # restored, status clean
```

**One added mention of one retiring path in `.planning/REQUIREMENTS.md` moves the generated
report.** `DOCS-17` is *about* `examples/00`–`08`; its verdict and its named absence will almost
certainly name those paths.

### The exact command and where it must run

```bash
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
git diff --stat -- docs/surface/examples/RETIREMENT-COUPLINGS.md   # then COMMIT the result
```

**Rules for the plan sequence:**

1. Run it **LAST** in any plan that edits `.planning/`, after the final `.planning/` write.
2. Run it **again in the final close plan**, after `STATE.md` and `ROADMAP.md` are hand-edited
   (D-15) — those are `.planning/` files too, and `ROADMAP.md` already contributes 14 hits.
3. **Commit the regenerated file.** Regenerating and not committing leaves the tree dirty and
   the gate red on the next run.
4. ⚠️ **`--report` is a WRITE, not a read** — `D-IMPL-154` (Dave, 2026-08-19): the flag name
   contradicts its own behaviour and a `18.1-04` executor mutated a tracked file while intending
   only to measure. Check `git status` after every invocation.

---

## 10. Common Pitfalls

### Pitfall 1: the executor closes a gap it discovers
**What goes wrong:** the audit finds `DOCS-17` undone, and it is a twenty-minute `git rm`.
**Why it happens:** every row that reads `Not built` is an invitation, and the fix is often
smaller than the write-up.
**How to avoid:** D-11 and the ROADMAP's out-of-scope paragraph are explicit — *"An executor
that starts closing gaps it discovered has turned an audit into an unplanned implementation
phase."* Criterion 12's diff assertion catches fabric changes but **not** an `examples/`, `docs/`
or `public/` change. **Recommend widening the plan's own must-have to a diff over
`src/ runtime/ examples/ public/ docs/` minus the two files the phase is allowed to touch**
(`.planning/REQUIREMENTS.md`, and the new test module), so the fence is mechanical rather than
attentional.
**Warning signs:** a plan task whose verb is "add", "retire", "move" or "fix".

### Pitfall 2: a verdict lands in one channel and not the other
**What goes wrong:** the table cell gets the verdict, the checkbox stays `[ ]` — the first drift
in a ledger measured at 0.
**Why it happens:** the two channels are 250 lines apart and the verdict work happens in the
table.
**How to avoid:** the criterion-10 check lands in **Wave 0**, so a mid-phase `make ci-core` goes
red on the first mismatch rather than at close. This is the single highest-leverage sequencing
decision in the phase.

### Pitfall 3: a citation that resolves today and names a symbol that later moves
**What goes wrong:** the citation lint catches a symbol *rename* (`cite03-node-id`, verified
red in §4(b)) but **does not** catch a file *move* — the path becomes unresolvable and is
silently dropped, not flagged.
**How to avoid:** the new check's existence assertion is what catches the move. That is a second
reason it exists, beyond D-06. Say so in the module docstring.

### Pitfall 4: `make ci` red from a stale generated report
See §9. **The likeliest single cause of a red build in this phase**, because the phase's entire
output is `.planning/` edits and the report is a function of `.planning/`.

### Pitfall 5: a badly-formed verdict turns the build red mid-phase
`.planning/REQUIREMENTS.md` is inside `GATED_TREES` with **no** exemption. A `path::symbol`
citation with a correct path and a wrong symbol is an immediate `cite03-node-id` finding and
`make lint` exits non-zero (§4(b) row 2). This is *desirable* — it is criterion 3 enforcing
itself — but it means **`make lint` must be run per-plan, not per-phase**. Recommend every audit
plan's verification block include `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints
--citations` (fast: the whole tree scanned in seconds).

### Pitfall 6: an accidental historicity marker exempts a citation
`HISTORICITY_MARKERS` (`citations.py:277-284`) exempts a *line* citation whose **sentence**
contains `it stood`, `written against`, `has/have (since) moved`, `correct/accurate/true as of`,
`at commit`, or **a backticked 7–40 hex commit sha**. A status cell that qualifies a verdict with
"the line numbers have since moved" or cites a commit like `` `7453e87` `` — which the `CPS-05`
row already does — silently exempts every line citation in that sentence. `NODE_ID` citations
are **not** affected. **Another reason to prefer `.py::symbol` over line citations throughout.**

### Pitfall 7: the completeness assertion lands early and reddens `ci-core`
See §5. Split by tense.

### Pitfall 8: the executor uses a GSD state/roadmap writer
D-15 and `D-IMPL-154`/`-155`: **every** such handler in this repository has corrupted the file
it wrote. Hand-edit with a backup and a diff; the diff must show insertions only, or the
intended replacement and nothing else. `20-01-SUMMARY.md` records the discipline: *"The edit was
made with the Edit tool only. No `state.*` and no `roadmap.*` GSD SDK writer was invoked at any
point in this plan."*

### Pitfall 9: presenting the work list as an essay
CLAUDE.md §17, and Dave's own framing: he rules *what is worth a phase and what should be
dropped*. **One line per row.** A twelve-page report is a report he cannot rule on.

### Pitfall 10: a live agent worktree makes every basename ambiguous
`citations.py:220-234` records this measured hazard (`DEF-17-04`, 2026-08-15: six worktrees put
seven entries under one basename and hid two real unanchored citations behind a green run).
`.claude` is in `SKIP_DIRS`, and `git worktree list` shows only the main checkout today
[VERIFIED]. **The new check must prune the same `SKIP_DIRS`** if it walks the tree, or reuse
`citations.repo_index`. Do not hand-roll a bare `rglob`.

---

## 11. Open Questions

1. **`CPS-03`'s ruled state has no word in the vocabulary.**
   - What we know: `CPS-03` is `Pending` and is ruled **"Pending by DESIGN under `D-IMPL-113`
     AND `D-IMPL-121`, not by omission"**, with `D-IMPL-113` instructing that *"the requirement
     row must say which, or a later reader will read an unmet requirement as an oversight."* The
     mechanism ships and is tested; enforcement was deliberately declined.
   - What's unclear: D-09's six words are `Complete`, `Complete as ruled`, `Complete over the
     ruled scope`, `Partial`, `Not built`, `Orphaned`. **None of them says "Pending by design."**
     `Complete as ruled` is the closest (`DCD-09` uses it for exactly this shape — descoped with
     a recorded reason), but choosing it is a judgement about a Dave-ruled row.
   - Recommendation: **do not silently pick.** Put it in the phase's report as one line for
     Dave, next to the D-12 split. Alternatively the planner proposes `Complete as ruled` with
     the reasoning stated, and flags it as proposed-not-decided. Either way the vocabulary
     check (§5, CONTROL 9) must accept whatever is chosen.

2. **Does criterion 3's "path::symbol" bind literally, given that markdown has no such form?**
   - What we know: §4(a) proves `NODE_ID` is `.py`-only. Roughly 24 of the 54 rows are about
     documentation.
   - Recommendation: read criterion 3 as *"a citation the lint resolves"*, with `path::symbol`
     the preferred form and the anchored-tokenish line citation the fallback (§6). State the
     reading in the plan so it is not read later as a relaxation. This is a reading, not a change
     — the criterion's own final clause is *"that the citation lint resolves."*

3. **Do the three stale counters get corrected here?** (§1: `94/94`, `All 42`, and the ROADMAP
   Phase 21 prose's four instances of `52`.) They are adjacent to criterion 1 and not inside it.
   Recommendation: report, do not fix, unless Dave rules otherwise. Under D-15 the ROADMAP fix
   is a hand-edit with a backup and a diff.

4. **Is `DEMO-03`'s re-homing target present?** `DEMO-03` is ticked `[x]` and its re-homing note
   points at `public/tutorial/hello-ccf.md`. `ls public/tutorial/` returns `adopters-guide.md`
   and `demo-walkthrough.md` only [VERIFIED]. **This concerns a row OUTSIDE the 54** and is not
   this phase's to flip. Recommendation: note it in the report as an observation. Do not act.

---

## 12. Runtime State Inventory

Not a rename/refactor/migration phase. Included because the phase mutates a file that three
machines read, and each is a form of derived state.

| Category | Items found | Action required |
|---|---|---|
| Stored data | **None** — no database, no cache, no index holds requirement rows. Verified: `grep -rln 'REQUIREMENTS.md' tools/ tests/` returns only two files, both prose mentions | none |
| Live service config | **None** — no external service reads the ledger | none |
| OS-registered state | **None** | none |
| Secrets / env vars | **None** in scope. `PYTHONPATH=.:src:runtime` and `PYTHON=.venv/bin/python` are Makefile-supplied and must be used verbatim | none |
| **Generated artifacts** | **`docs/surface/examples/RETIREMENT-COUPLINGS.md`** — generated by `tools/retirement_sweep.py --report`, walks `.planning/`, currently carries a `.planning/REQUIREMENTS.md` count of **15**. **Empirically shown to move on a one-line `.planning/` edit.** A stale copy turns `make gate-tools` (and therefore `ci-core` and `ci`) red | **regenerate LAST after every `.planning/` write, and commit it** (§9) |
| Derived/parsed state | `gsd-sdk query roadmap.get-phase 21` parses **14 criteria as 14 lines** [VERIFIED] — the `roadmap-success-criteria-parse-one-per-line` hazard is **not** present. Do not reflow those lines | none, but **do not rewrap** the criteria |

---

## 13. Environment Availability

| Dependency | Required by | Available | Version / note | Fallback |
|---|---|---|---|---|
| `git` | criteria 12, 13; base pinning | ✓ | branch `phase-21` at `9455fc2`; `main` at `d15c1bf`; one worktree | — |
| `.venv/bin/python` | every `make` target | ✓ | **required** — system `python3` cannot import `ccf_runtime`, leg 2 of `gate-tools` fails to collect | none |
| `PYTHONPATH=.:src:runtime` | `gate-tools`, `docs-strict` | ✓ | `ENV_DOCS`, `Makefile:23` | none |
| `pytest` | both `gate-tools` legs | ✓ | leg 1 **406 passed** (7.2s); leg 2 **154 passed** (37.7s) — 560 total, matching CONTEXT.md | — |
| `tools.lints` CLI | criterion 3 enforcement | ✓ | `python -m tools.lints --citations --report` → 1042 matched, 0 findings | — |
| `tools/retirement_sweep.py` | criterion 13 | ✓ | committed report **currently in sync** (regenerating produced no diff) | — |
| `gsd-sdk query audit-uat` | criterion 11 | ✓ | 24 items / 9 phases; **15.1's two items return `">-"`** — read the file directly | read the nine files |
| `gsd-sdk query roadmap.get-phase 21` | criteria wording | ✓ | 14 criteria, one per line | — |
| Network / external services | — | n/a | **none needed** — the whole phase is repo-local | — |

**Missing dependencies with no fallback:** none.

---

## Validation Architecture

Framework: **pytest**, `.venv/bin/python -m pytest`, config `pyproject.toml`
(`testpaths` deliberately excludes `tools/`, which is why `gate-tools` exists as a separate
target).

| Property | Value |
|---|---|
| Quick run (per task commit) | `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations` *(seconds — catches a bad verdict citation immediately)* |
| Wave merge | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` then `make ci-core` |
| Phase gate | `make ci` exit 0, with `RETIREMENT-COUPLINGS.md` regenerated last |

### Criterion-by-criterion: the observation, and the control that proves it is not vacuous

**Honest labelling.** Criteria **1, 4, 5, 10, 12** carry real controls. Criterion **13** inherits
one that already ships. Criteria **2** and **11** each have a limb that is mechanizable **for
free** off machinery the phase already needs — recommend taking both. The remainder are
**attested by inspection**, and D-05 forbids inventing tests to change that.

| # | Criterion | Observation that proves it | Control proving the observation is not vacuous | Kind |
|---|---|---|---|---|
| **1** | 54 rows carry a verdict, by strict parse, none missed, none doubled | `verdicts_written == needs_verdict_count == 54`; `≤ 1` verdict token per cell | **REAL.** (a) parser handed a document whose table header is misspelled → **refuses**, does not report `0 == 0` clean; (b) parser handed a table with 53 verdicts → red naming the missing id; (c) a cell with two verdict tokens → red | **test** — land in the FINAL plan (red until then) |
| **2** | Verdicts use the six-word vocabulary in the `DCD-` shape | every parsed verdict token ∈ the six-word set | **REAL, free** — a doctored cell with `Done` is refused (CONTROL 9). *The "`DCD-` shape" limb (bolded verdict, parenthesised citations, em-dash clause) is inspection* | **test (vocabulary) + inspection (shape)** |
| **3** | Every non-`Not built`/`Orphaned` verdict cites a full repo-relative form the lint resolves | `python -m tools.lints --citations` exit 0 **and** the §5 Check-A refusal list is empty | **REAL** — Check A's CONTROL 1–5. *Note: the lint alone is NOT sufficient evidence — §4(b) proves it is silent on ambiguous and nonexistent paths. **Check A is what makes criterion 3 true**, the lint only catches wrong symbols* | **test** |
| **4** | A bare basename is REFUSED by a standing check | Check A returns `[]` on the real file | **REAL** — CONTROL 1 (ambiguous), CONTROL 2 (unique basename), CONTROL 3 (nonexistent path), CONTROL 4 (`::` on non-`.py`) | **test** |
| **5** | That refusal carries a named sabotage control, standing, not a SUMMARY probe (`D-IMPL-170`) | the CONTROL tests exist, are collected by `make gate-tools`, and pass **because they observed the refusal fire** | **REAL, and it is the criterion.** Plus CONTROL 5 (vacuity): the checker refuses a zero-row or zero-citation parse rather than returning clean | **test** |
| **6** | Rows whose property an existing test guards name that test; no test written to manufacture a name | the named test exists and is collected — mechanizable as *"every `tests/**::name` cited in a status cell is a collected test id"* | **PARTIAL.** That a test *guards the row's property* is a judgement no assertion can make. Recommend the weaker mechanical limb (existence + collection) plus inspection for the semantic limb. **The "no test written" limb IS mechanical:** `git diff --stat <base>..HEAD -- tests/` empty except the new ledger module | **inspection + partial test** |
| **7** | `Not built`/`Orphaned` verdicts name a checkable absence | each such cell contains a concrete path, symbol or directory name a reader can look for | **INSPECTION.** A regex could require *a* path-shaped token, which would be a shape check masquerading as a substance check — the project's own recorded defect class. **Do not fake it** | **inspection** |
| **8** | `Not built` rows delivered as a scoped work list, one line each, nothing built | the list exists; and criterion 12's diff (widened to `examples/ public/ docs/`) is empty | **PARTIAL** — the "nothing built" limb inherits criterion 12's control; the list's quality is inspection | **inspection + inherited control** |
| **9** | Phase 16's eighteen reported as a two-sided split, unflipped and undropped | the split document exists with evidence on both sides; **all 18 ids still present** in both channels and none reads `Complete` | **PARTIAL** — "still present, still not Complete" is mechanical off the same parser; the split's correctness is inspection and is Dave's to rule (D-12) | **inspection + partial test** |
| **10** | Both channels agree on all 133 ids, by standing check | `channel_disagreements(real_file) == []`, 133 ids each side, id sets identical | **REAL** — CONTROL 6 (flipped row), CONTROL 7 (missing id), CONTROL 8 (misparsed table returns `{}` → refused, not "clean") | **test — land in WAVE 0** |
| **11** | 24 `human_needed` items named with phases, left untouched, out-of-scope stated | the nine paths + counts appear in the phase record; `fabric_diff(base, <the nine paths>)` empty | **PARTIAL, and take the free half** — the untouched limb reuses criterion 12's control. The naming limb is inspection | **test (untouched) + inspection (named)** |
| **12** | `src/` and `runtime/` untouched vs a pinned base | `fabric_diff(base, ["src/","runtime/"]) == ""` | **REAL, Phase 20's exact pattern.** CONTROL A: same function, a base+path pair that genuinely differs → non-empty. CONTROL B: unresolvable base (40 zeros) → **raises**, not empty. CONTROL C: empty path list → raises. **Recommend widening the shipped assertion to `examples/ public/ docs/` too** (Pitfall 1) | **test** |
| **13** | `make ci` exit 0 at close, `RETIREMENT-COUPLINGS.md` regenerated LAST | `make ci` exit 0; `git status --porcelain` empty after the final regenerate | **INHERITED, already shipping** — `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` compares the committed bytes against `render(head())`. Its non-vacuity is the sweep's own suite | **test (inherited)** |
| **14** | `D-GATE-21` logged on Dave's approval; the phase does not close without it | the entry exists in `docs/DECISIONS.md`, dated, with Dave as approver | **INSPECTION, and correctly so** — approval authority is Dave's alone (CLAUDE.md §2, §3.1) and no test can assert it. A test asserting the *string* `D-GATE-21` exists would be exactly the check-that-cannot-fail shape this project keeps recording | **inspection** |

### Wave 0 gaps

- [ ] `tools/docs_tests/test_requirement_ledger.py` — the shared structural parser, Check A
      (criteria 3, 4, 5) and Check B (criteria 2-vocabulary, 10), with CONTROLS 1–9.
      **The completeness count (criterion 1) is deliberately NOT here.**
- [ ] `.planning/phases/21-*/21-BASE-COMMIT.txt` — the pinned SHA plus the comment naming what
      reads it. Written in the **first** plan.
- [ ] `fabric_diff(base, paths)` — the criterion-12 helper with three refusals, plus CONTROLS
      A/B/C. May live in the same module.

*Framework install: none needed. No new package. No `pyproject.toml` change.*

---

## Security Domain

Not applicable in the usual sense — this phase adds no runtime surface, no endpoint, no data
path, and installs no package. The one security-adjacent property is **supply-chain: zero new
dependencies**, which is asserted for free by criterion 12's diff if `pyproject.toml` is added
to the path list. Recommend adding it, as Phase 20 did (`git diff --stat <base>..HEAD --
pyproject.toml .github/workflows/` empty).

The ASVS categories (V2 Authentication, V3 Session, V4 Access Control, V5 Input Validation,
V6 Cryptography) are **not engaged** by this phase: no input crosses a trust boundary, no
credential is read, no crypto is used. Stated explicitly rather than omitted.

---

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** No `pip install`, no
`pyproject.toml` change, no new import outside the standard library and the repo's own modules.
The recommended standing checks use `pathlib`, `re`, `subprocess` and `pytest`, all already
present. Criterion 12's diff assertion is the mechanical proof that this stayed true.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | The 54 is `Pending ∪ Partial` and `DCD-09`/`DCD-10` are out of scope | §1 | LOW — three independent confirmations (CONTEXT arithmetic, the lane breakdown, the checkbox channel), but the *predicate wording* is Claude's proposal and should be stated in the plan |
| A2 | `tools/docs_tests/` is the right home for the new checks | §5 | LOW — explicitly Claude's discretion per CONTEXT.md; both candidate directories are inside `make gate-tools` |
| A3 | The RECON-01..09 clustering | phase_requirements | LOW — the planner mints the real set; this is a recommendation |
| A4 | Splitting the checks by tense (invariants in Wave 0, completeness last) | §5 | MEDIUM if ignored — `ci-core` "MUST stay green from Wave 1 onward" is a Makefile-stated constraint, and the alternative is a red suite for the whole phase |
| A5 | Reading criterion 3's `path::symbol` as "a citation the lint resolves" | §11 Q2 | MEDIUM — a literal reading makes ~24 doc rows unsatisfiable. Should be confirmed with Dave or stated as a reading in the plan |
| A6 | `CPS-03` maps to `Complete as ruled` | §11 Q1 | MEDIUM — it is a Dave-ruled row and the choice is a judgement. **Recommended to surface, not to decide** |
| A7 | Widening criterion 12's paths to `examples/ public/ docs/ pyproject.toml` | §10 P1, Validation | LOW — strictly stronger than the criterion, and it makes the D-11 fence mechanical |
| A8 | Phase-lane waves in the order CLNT → remaining-15 → DOCS-16 | §2 | LOW — the planner's call; the reasoning is calibration before the hardest lane |

---

## Sources

### Primary (HIGH confidence — measured in this session)

- `.planning/REQUIREMENTS.md` — strict parse; 133 rows at lines 266–398; checkbox channel at
  lines 11–244; status distribution; 0 channel drift; 39 citations / 35 checked.
- `tools/lints/citations.py` — read in full; `check_source` exercised against seven doctored
  citation shapes with the real `repo_index`.
- `tools/retirement_sweep.py` + `docs/surface/examples/RETIREMENT-COUPLINGS.md` — `.planning/`
  walk confirmed at `:199`, report line 309, and the one-line-edit hazard reproduced end-to-end.
- `Makefile` — `gate-tools` (`:188-190`), `ci-core` (`:138`), `ci` (`:172`), `ENV_DOCS` (`:23`),
  `PYTHON` (`:10`); both `gate-tools` legs run green (406 + 154).
- `tests/examples/test_hw1_harness_clients_readme.py:468-500` — `client_surface_diff` and its
  three refusals.
- `.planning/phases/20-*/20-BASE-COMMIT.txt`, `20-08-SUMMARY.md`, `20-01-SUMMARY.md` — the
  pinned-base pattern and CONTROL 6/7.
- `.planning/phases/16-*/RETIRED.md` — the obligation table and the retire-the-approach rule.
- `docs/DECISIONS.md` — `D-IMPL-154`, `D-IMPL-155`, `D-IMPL-170`, `D-IMPL-171`, `D-GATE-20`.
- `gsd-sdk query audit-uat --raw` — 24 items, 9 phases, exact paths.
- `gsd-sdk query roadmap.get-phase 21 --raw` — 14 criteria parsed as 14 lines.

### Secondary (MEDIUM)

- `.planning/phases/20-*/20-REVIEW.md:581` — `WR-08`'s measurement of the three ambiguous client
  basenames, independently reconfirmed here against the live `repo_index`.
- `.planning/phases/16-*/16-2*-SUMMARY.md` — the `DOCS-` ids the ten post-retirement plans name.

### Tertiary (LOW)

- None. Every claim in this document was checked against the tree in this session. No web
  search, no Context7, no training-data claim about any library — the domain is this repository.

---

## Metadata

**Confidence breakdown:**

- Strict parse and lane breakdown: **HIGH** — reproduced CONTEXT.md's five figures and its
  eight-lane split exactly, plus the 0-drift claim, from the file.
- Citation-lint behaviour: **HIGH** — read AND executed against seven doctored inputs; the
  second silent-drop hole was found by execution, not by reading.
- Standing-check design: **HIGH** on placement and shape (measured against 560 running tests and
  a shipped precedent); **MEDIUM** on the exact module split, which is Claude's discretion.
- The D-12 split criterion: **HIGH** — `RETIRED.md` states it in its own words; the third
  outcome (`Not built` vs `Orphaned`) is Claude's reading of D-09's vocabulary against it.
- Pitfalls: **HIGH** — 8 of 10 are reproduced or citable to a `D-IMPL` ruling; 2 are reasoned.

**Research date:** 2026-08-21
**Valid until:** the next commit to `.planning/REQUIREMENTS.md`, `tools/lints/citations.py`,
`tools/retirement_sweep.py` or the `Makefile`. Every count in §1 and §4 is a measurement of
`9455fc2`; re-measure before relying on one.
