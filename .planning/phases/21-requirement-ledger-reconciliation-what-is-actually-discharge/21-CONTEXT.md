# Phase 21: Requirement-Ledger Reconciliation — What Is Actually Discharged - Context

**Gathered:** 2026-08-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Give every not-`Complete` row in `.planning/REQUIREMENTS.md` a verdict backed by
evidence in the tree, so that a tick means something and v0.2 can be closed
against a ledger that matches reality.

**The phase FINDS and RECORDS. It does not build.** An executor that starts
closing gaps it discovered has converted an audit into an unplanned
implementation phase. What the audit surfaces becomes a scoped work list for
Dave to rule on, and a later phase to execute.

**The count is 54, not 52.** Measured 2026-08-21 by a strict parse of the
traceability table (133 rows total: 77 `Complete`, 53 `Pending`, 1 `Partial`,
1 `Complete as ruled`, 1 `Complete over the ruled scope`). The figure "52" that
appears in `D-GATE-20`, in the first draft of this phase's ROADMAP entry, and in
the 2026-08-21 progress report came from `grep -c "| Pending |"`, which misses
`CPS-03` (Phase 15.5, spelled `**Pending**` in bold) and `DCD-02` (Phase 15.6,
`**Partial**`). **The phase's own subject arrived before the phase did:** a count
produced by a naive substring match, silently disagreeing with a strict one.
Criterion 1 now requires the strict parse explicitly.

By phase: 21 Phase 17, 18 Phase 16, 6 Phase 14, 3 Phase 9, 3 Phase 13,
1 Phase 15.5, 1 Phase 15.6, 1 Phase 18.

</domain>

<decisions>
## Implementation Decisions

### Where verdicts and evidence live

- **D-01:** Verdicts and their evidence go **in the traceability table's status
  cell**, in the shape Phase 15.6's `DCD-02`..`DCD-12` rows already use —
  bolded verdict, citations in parentheses, qualifying clause after an em dash.
  Not a separate `RECONCILIATION.md`. Rationale: the format already exists
  in-tree and is readable; one place cannot drift from itself; and
  `.planning/REQUIREMENTS.md` is **already inside the citation lint's
  `GATED_TREES` with no `HISTORICAL_RECORDS` exemption**, so citations written
  there are resolved by machinery that already ships.

- **D-02:** The ledger's **two status channels must stay in agreement** — the
  `- [ ] **ID**: …` checkbox list (lines 7–246) and the traceability table
  (lines 262–559). Measured at 0 drift on 2026-08-21 across all 133 ids; a
  reconciliation that edits one channel and not the other would introduce the
  first. A standing check asserts the agreement (criterion 10). *Claude's call,
  not discussed — recorded so the planner does not treat it as optional.*

### What counts as evidence

- **D-03:** A row may read `Complete` (or a 15.6-vocabulary variant) only with a
  **resolvable `path::symbol` citation** in its status cell. A citation the lint
  cannot resolve is not evidence.

- **D-04:** Where an existing test already guards the row's property, that test
  is **named alongside the citation**. Then the tick means "found, and it goes
  red if this regresses" rather than "someone looked once."

- **D-05:** **No test is written in this phase to manufacture such a name.** Many
  requirements are prose about documentation or structure with nothing testable
  behind them; forcing a test would turn an audit into implementation and would
  reward inventing a weak test over reporting an honest absence.

### The ambiguous-basename hole (`F-3` / `WR-08`)

- **D-06:** Reconciliation citations must be **full repo-relative paths**; a bare
  basename in a requirement row is **REFUSED by a standing check**. This dodges
  the hole for this phase's rows without opening the lint.

- **D-07:** The lint is **not fixed here**. `tools/lints/citations.py` silently
  drops citations whose basename is ambiguous — carried as `F-3` at `D-GATE-19`
  and as `WR-08` at `D-GATE-20`, and this phase made three client filenames
  ambiguous. Fixing it is tooling work inside an audit phase and would surface
  stale citations elsewhere that then need their own fixes. **The repo-wide hole
  stays open and stays named**; only this phase's own rows are placed out of its
  reach.

- **D-08:** The refusal in D-06 carries a **named sabotage control**: a row given
  a deliberately false or ambiguous citation is observably RED, as a standing
  test and not as a probe recorded in a SUMMARY (`D-IMPL-170`). A phase about
  evidence whose own evidence-check cannot fail would be this project's defect
  class one level up, again.

### Verdict vocabulary

- **D-09:** Adopt the vocabulary **Phase 15.6 already established in this
  ledger** — `Complete`, `Complete as ruled`, `Complete over the ruled scope`,
  `Partial` — extended by `Not built` and `Orphaned`. The original
  three-verdict criterion is overridden. Rationale: a strict three-verdict
  scheme would re-open `DCD-02`, `DCD-09` and `DCD-10`, which Dave has already
  ruled on, and would over-report the debt.

- **D-10:** Every `Not built` and `Orphaned` verdict **names the specific
  absence** it rests on, in a form a reader can check by looking rather than by
  trusting. An absence asserted is not an absence shown.

### What the phase hands back

- **D-11:** `Not built` rows are delivered as a **scoped work list** — each with
  a one-line statement of what closing it would mean — grouped for Dave's ruling
  on what is worth a phase and what should be dropped. **Nothing on that list is
  built in this phase.**

- **D-12:** Phase 16's eighteen `DOCS-` rows are reported as a **two-sided split**
  — already satisfied by later work vs genuinely orphaned with the retired
  approach — with evidence on both sides, and are **left unflipped and
  undropped** pending Dave's ruling. Deferred at the Phase 20 sitting in his
  words: *"tell me after the audit."*

- **D-13:** The **24 `human_needed` verification items** across 9 phases (11, 13,
  14, 15.1–15.4, 18.1, 19) are **named with their phases and left untouched**.
  They require Dave at a keyboard — a live GitHub Actions dispatch, a
  credentialed run — so an executor cannot discharge them. The phase record
  states plainly that they are out of scope and why.

### Locked upstream — not this phase's to re-decide

- **D-14:** The ten phases with no `D-GATE` entry (9, 10, 11, 12, 13, 13.1, 13.2,
  13.3, 14, 16) are gated by their ROADMAP completion rows and are **not
  backfilled** — `D-IMPL-171` (Dave, 2026-08-21). This phase does nothing about
  them beyond not quietly re-opening the question.

- **D-15:** `.planning/STATE.md` and `.planning/ROADMAP.md` are **hand-edited with
  a backup and a diff**, not written through `gsd-sdk query state.*` /
  `roadmap.*` handlers. This is a deliberate divergence from GSD's universal
  anti-pattern #15: in this repository every such handler has corrupted the file
  it wrote — five distinct handlers observed, recorded at `D-IMPL-154`/`-155`.
  The diff after each hand-edit must show insertions only, or the intended
  replacement and nothing else.

- **D-16:** Work happens on branch **`phase-21`**, not on `main`. `main` is the
  approved-state branch (`CLAUDE.md` §2.2); the merge happens at the
  `D-GATE-21` entry.

### Ruled at the 2026-08-21 planning sitting (after research, before plans)

Three questions the research surfaced that a planner would otherwise have had to
default on. Dave ruled on all three. Each becomes a `D-IMPL-NN` entry in
`docs/DECISIONS.md` during execution.

- **D-17:** Criterion 3's `path::symbol` **binds as a reading, not as a literal
  form** — the operative clause is the criterion's own final one, *"that the
  citation lint resolves."* `path::symbol` stays the preferred form and is
  required wherever the evidence is Python. Where the evidence is a document,
  an **anchored line citation the lint resolves** is admissible. Forced by the
  tree: `tools/lints/citations.py:252` anchors the `::` pattern to `\.py`, so a
  markdown document has no `path::symbol` form at all, and roughly 24 of the 54
  rows are about documentation. **The plan and the SUMMARY must state this
  reading explicitly**, so a later reader does not mistake it for a relaxation
  granted to make the criterion reachable. D-06 is unchanged and still binds:
  the path is full and repo-relative, and a bare basename is REFUSED.

- **D-18:** `CPS-03` takes the verdict **`Complete as ruled`**, citing
  `D-IMPL-113` **and** `D-IMPL-121` — both, per `D-IMPL-113`'s own instruction
  that the row must say which. The vocabulary **stays at D-09's six words**; no
  seventh is minted. Rationale: `DCD-09` already uses `Complete as ruled` for
  exactly this shape — descoped against a recorded ruling — and the row is
  closed by Dave's decision rather than open by omission. The row's status cell
  must carry the "by design, not by omission" clause so the word is not read as
  a claim that enforcement shipped.

- **D-19:** The **three stale counters are corrected in this phase**, not merely
  reported: `.planning/REQUIREMENTS.md:423` (*"Coverage: 94/94 v0.2 requirements
  mapped"*), `.planning/ROADMAP.md` §Coverage (*"All **42** v0.2 requirements
  mapped"* — cited by section, not by line: it was line 1946 when D-19 was written
  and moved to 1959 when the plans were committed, which is the citation-drift
  hazard this phase exists to name), and the ROADMAP's Phase 21 entry, which says **54 not-`Complete`
  rows** and *"each of the 52 gets a verdict"* **in the same paragraph**
  (`:47`, and `:1888`/`:1890` in the phase body). Constraints: (a) the replacement
  figures are **produced by the strict parse, never assumed** — 133 is the table's
  row count and is not automatically the right number for a sentence about *v0.2
  requirements mapped*, which may be a defined subset; if the parse cannot settle
  what a counter is counting, the counter is reported rather than guessed, and
  that is said; (b) every edit is a **hand-edit under D-15** with a backup and a
  diff showing insertions only or the intended replacement and nothing else;
  (c) the phase record **names each correction and its old value**, because a
  phase about honest counters that silently edits three counters would be its own
  defect one level up.

  Adjacent, and NOT covered by this ruling: `DEMO-03`'s re-homing note points at
  `public/tutorial/hello-ccf.md`, which is not in the tree (`public/tutorial/`
  holds `adopters-guide.md` and `demo-walkthrough.md` only). That row is ticked
  and sits **outside the 54**. It is reported as an observation and not flipped.

- **D-20:** Success criterion 11 is **AMENDED from "the 24 `human_needed`
  verification items ... across 9 phases" to "all 27 across 11 phase records"**
  (Dave, 2026-08-21, after the plan-checker measured it). The 24 came from
  `gsd-sdk query audit-uat`, which **filters on each record's frontmatter
  `status:`** and therefore drops two records that carry undischarged
  `human_verification:` blocks under a different status: Phase 12
  (`status: passed`, 1 item — whose own prose reads *"**Status:** human_needed
  (all automated checks passed; one subjective legibility check remains)"*) and
  Phase 18 (`status: gaps_found`, 2 items). **This is the 52-vs-54 miscount a
  third time**, in a third tool: a query that appears to report all of something
  and reports only the subset its filter admits.

  Binding consequences: (a) the roster is **re-derived by parsing every
  `.planning/phases/*/[0-9]*-VERIFICATION.md` for a `human_verification:` block**,
  never by trusting `audit-uat`; (b) the phase record **states the delta and its
  cause** — 24 by the query, 27 in the files, and why — rather than silently
  shipping the larger number; (c) any roster the phase freezes for the
  untouched-diff assertion covers **all eleven** records, so Phase 12's and
  Phase 18's cannot be edited without going red. `audit-uat`'s filter is **not
  fixed here** — same reasoning as D-07 for the citation lint: tooling repair
  inside an audit phase. It is named, not fixed.

- **D-21:** Success criterion 10 is **AMENDED to drop its hardcoded row count**
  (Dave, 2026-08-21). It read *"agree on every one of the **133** requirement
  ids"*; it now reads *"agree on EVERY requirement id the ledger contains — 133
  at the pinned base and 143 once this phase mints its own ten `RECON-` rows in
  wave 1"*, and the standing check **reads the count from the ledger rather than
  carrying one**.

  Why it had to move: the revision that closed the plan-checker's `B-4` mints
  this phase's own ten `RECON-` rows in wave 1, so **the phase's first action
  falsifies its own criterion 10**. This is criterion 11's defect exactly
  (`D-20`) and the **fourth count problem this phase has surfaced** — after
  52-vs-54 in the commissioning prose, GSD's UI detector matching `form` inside
  *"in a form a reader can check"*, and `audit-uat`'s 24-vs-27. Dave chose to
  remove the brittle number rather than replace it, so a future row-minting
  phase does not falsify it a fifth time.

  Binding consequence: **no standing check in this phase hardcodes a row count.**
  A count is measured from the subject at assertion time. Where a fixed set is
  genuinely needed — the 54-member working set, the eleven `human_verification`
  records, the ten `RECON-` rows — it is a **frozen roster of named ids taken at
  the pinned base**, never a number, so that adding a row cannot silently satisfy
  or silently break it.

### Claude's Discretion

- Plan decomposition — whether the 54 rows are audited in one sequential pass or
  split into waves by phase-lane (Phase 17's 21, Phase 16's 18, and the
  remaining 15 are natural lanes). The planner decides.
- Where the two standing checks (D-06 refusal, D-02 channel agreement) live in
  the test tree, and whether they are one module or two.
- The exact status-cell grammar, provided it is recognisably the `DCD-` shape and
  a strict parse can read it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The ledger and its shape
- `.planning/REQUIREMENTS.md` — the subject of the phase. Two status channels:
  the checkbox list (§`v0.2 Requirements`) and the traceability table
  (§`Traceability`). The `DCD-02`..`DCD-12` rows are the format D-01 adopts.
- `.planning/ROADMAP.md` — the Phase 21 entry, its fourteen Success Criteria
  (amended 2026-08-21 at this session), and the progress table.

### The citation machinery this phase leans on
- `tools/lints/citations.py` — `GATED_TREES` (includes `.planning`),
  `HISTORICAL_RECORDS` (exempts `.planning/phases/*`, **not**
  `.planning/REQUIREMENTS.md`), `MAINTAINED_RECORDS`, and `repo_index`, which is
  where the ambiguous-basename drop lives.
- `tools/lints/tests/test_citations.py` — the existing control surface for that
  lint; the new refusal check should read like it.

### The rulings in force
- `docs/DECISIONS.md` — `D-IMPL-171` (the gate gap, ruled and closed),
  `D-GATE-20` (records this ledger debt rather than absorbing it),
  `D-IMPL-170` (a control is a standing test, never a SUMMARY probe),
  `D-IMPL-152` (Phase 16's retirement), `D-IMPL-154`/`D-IMPL-155` (the tooling
  hazards, and why the state handlers are not used).
- `CLAUDE.md` §2.2 (branch discipline), §3.1 (the close protocol and the
  `D-GATE-21` obligation), §17 (how to talk to Dave).

### The retired approach whose obligations are in question
- `.planning/phases/16-documentation-rewrite-the-deterministic-path-the-adoption-ar/RETIRED.md`
  — what is retired (the approach) and what is not (the obligations several of
  those plans carried). Authoritative for the D-12 split.
- `.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md` — the live
  phase-to-phase hand-off contract, and the one `.planning/phases/*` file the
  citation lint pulls back into the gate.

### The verification debt named but not touched
- `.planning/phases/*/[0-9]*-VERIFICATION.md` — the nine files carrying the 24
  `human_needed` items. Reachable as a set via `gsd-sdk query audit-uat --raw`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`tools/lints/citations.py`** — already resolves `path::symbol` citations and
  already walks `.planning/REQUIREMENTS.md` with no exemption. Criterion 3 needs
  no new resolver; the phase adds a *refusal* (D-06) on top of it, not a
  replacement.
- **Phase 15.6's `DCD-` rows** — a working precedent for verdict-plus-evidence in
  a status cell, including qualified verdicts. The format is copied, not invented.
- **`tools/lints/tests/`** — 406 passing lint-tool tests; the shape a new
  standing check and its sabotage control should follow.
- **`tools/retirement_sweep.py --report`** — regenerates
  `docs/surface/examples/RETIREMENT-COUPLINGS.md`, which walks `.planning/` and
  therefore goes stale on **every** planning commit. Must run LAST in any mixed
  pass (criterion 13).

### Established Patterns
- **Every gate carries a sabotage control that is watched go red** (`CLNT-12`,
  `D-IMPL-170`). Not negotiable, and it is why D-08 exists.
- **A strict parse beats a substring match** — the 52-vs-54 miscount is the
  in-phase demonstration. Any tooling this phase writes parses the table
  structurally.
- **Append-only decision log** — `docs/DECISIONS.md` is corrected by appending a
  new dated entry, never by editing. Line citations inside it are dated
  snapshots, which is why it is exempt from the citation lint.

### Integration Points
- The two standing checks land in the test tree and must be reached by
  `make gate-tools` (406 lint-tool + 154 publish/docs today), so they run in
  always-on CI rather than only by hand.
- Nothing connects to `src/` or `runtime/` — criterion 12 asserts both are
  untouched against a base pinned before execution.

</code_context>

<specifics>
## Specific Ideas

- The status-cell format is not a matter of taste: **copy `DCD-10`'s shape**
  verbatim as the model —
  `| ID | Phase N | **Complete over the ruled scope** (plan `x`, `D-IMPL-nn`) — 101 of 114; the 13 names held back by ruling |`
- Dave's framing of the not-built list: he rules **what is worth a phase and what
  should be dropped**. The list exists to make that ruling possible, so a
  one-line cost statement per row is the deliverable, not an essay.

</specifics>

<deferred>
## Deferred Ideas

- **Fixing the ambiguous-basename hole in `tools/lints/citations.py`** (`F-3`,
  `WR-08`) — considered and explicitly declined for this phase (D-07). It is
  repo-wide tooling work that will surface stale citations elsewhere. Wants its
  own phase, or a plan inside whichever phase next touches that lint.
- **Building whatever the `Not built` verdicts identify** — out of scope by
  construction (D-11). Becomes a scoped phase after Dave rules on the work list.
- **A dedicated phase for the 24 `human_needed` verification items** (D-13) —
  Dave chose "out, name them" over "out, and open a separate phase", so the
  separate phase is *not* commissioned. Recorded here so the option is not lost
  if the debt matters at milestone close.
- **Reconciling the `progress:` block in `.planning/STATE.md` and the GSD plan
  counter** — the counter reads `201/181 plans (100%)` because it matches SUMMARY
  files to PLAN files and cannot see that Phase 16 was retired. Out of this
  phase's scope; it is a GSD tooling limitation, not a ledger row.

</deferred>

---

*Phase: 21-requirement-ledger-reconciliation-what-is-actually-discharge*
*Context gathered: 2026-08-21*
