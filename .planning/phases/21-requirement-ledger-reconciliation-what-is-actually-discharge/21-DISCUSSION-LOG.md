# Phase 21: Requirement-Ledger Reconciliation — What Is Actually Discharged - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `21-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-08-21
**Phase:** 21-requirement-ledger-reconciliation-what-is-actually-discharge
**Areas discussed:** Where verdicts and evidence live; What counts as proof of "discharged"; The ambiguous-basename hole; Compound rows that are half-true; What the phase hands back; The UAT debt

---

## Correction made during the session, before any question was asked

The phase was commissioned against **52** pending rows. A strict parse of the
traceability table during the codebase scout returned **54** not-`Complete` rows
out of 133. The two missed rows spell their status differently — `CPS-03`
(Phase 15.5) writes `**Pending**` in bold and `DCD-02` (Phase 15.6) reads
`**Partial**` — so `grep -c "| Pending |"` cannot see them.

The figure 52 had already reached `D-GATE-20`, the first draft of the Phase 21
ROADMAP entry, and the 2026-08-21 progress report. The ROADMAP's Success
Criteria were amended in-session, before any planning, and criterion 1 now
requires the strict parse by name. Fourteen criteria, verified as fourteen
parsed lines.

---

## Where verdicts and evidence live

| Option | Description | Selected |
|--------|-------------|----------|
| In the traceability table, Phase 15.6 style | Verdict + citations in the status cell, the way `DCD-02`..`DCD-12` already do it. One place to read; the format already exists in-tree; `.planning/REQUIREMENTS.md` is already inside the citation lint's gated trees with no exemption | ✓ |
| A separate `RECONCILIATION.md` | Table keeps a one-word status and points at a detail file. Keeps the 559-line ledger readable, but creates two things that can drift | |
| Both — verdict in the cell, evidence in the file | Most readable, most drift surface | |

**Notes:** The scout established that `.planning/REQUIREMENTS.md` sits in
`GATED_TREES` and carries no `HISTORICAL_RECORDS` exemption, so citations written
into it are resolved by existing machinery — criterion 3 needs no new resolver.
The ledger's two status channels (checkbox list and traceability table) were
measured at **0 drift** across all 133 ids, which is what makes a single-location
decision safe and what criterion 10 now protects.

---

## What counts as proof of "discharged"

| Option | Description | Selected |
|--------|-------------|----------|
| Citation required, named test where one exists | Every row cites a resolvable `path::symbol`; rows whose property a test guards also name that test | ✓ |
| A resolvable citation, nothing more | Cheapest, enforced free by the existing lint — but a tick only means someone looked once | |
| A named passing test, always | Strongest tick, but forces writing tests inside an audit phase for prose requirements with nothing testable behind them | |

**Notes:** The chosen option carries an explicit prohibition into CONTEXT.md
(D-05): **no test may be written in this phase to manufacture such a name.**
Without it, the incentive is to invent a weak test rather than report an honest
absence.

---

## The ambiguous-basename hole (`F-3` / `WR-08`)

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse bare basenames in ledger rows | Reconciliation citations must be full repo-relative paths, enforced by a standing check with its own sabotage control. Dodges the hole without opening the lint; leaves the repo-wide hole open and named | ✓ |
| Fix the lint properly, here | Closes `F-3` and `WR-08` repo-wide, but is tooling work inside an audit phase and will surface stale citations elsewhere | |
| Accept it and record it | Cheapest — and a false citation on a common filename would pass green, in the one phase whose whole subject is evidence | |

**Notes:** `tools/lints/citations.py::repo_index` maps basenames to every path
carrying them; an ambiguous basename is dropped rather than reported. Carried as
`F-3` at `D-GATE-19` and `WR-08` at `D-GATE-20` — and Phase 20 itself created
three ambiguous client filenames. The deferred fix is recorded in CONTEXT.md's
`<deferred>` section so it is not lost.

---

## Compound rows that are half-true

| Option | Description | Selected |
|--------|-------------|----------|
| Adopt Phase 15.6's vocabulary | Reuse `Partial` / `Complete as ruled` / `Complete over the ruled scope` — already in this ledger, already precedent. The three-verdict criterion is widened to match | ✓ |
| Three verdicts only; any unmet clause = not-built | Harshest and least ambiguous, but would re-open `DCD-02`, `DCD-09` and `DCD-10`, already ruled on, and would over-report the debt | |
| Three verdicts plus a mandatory clause breakdown | Most precise, most work — several requirements are four-clause sentences | |

**Notes:** The precedent was surfaced by the scout, not proposed from scratch:
`DCD-10` already reads `**Complete over the ruled scope** (plan 15.6-11,
D-IMPL-123) — 101 of 114; the 13 D-IMPL-114 names are held back by ruling`. The
answer to this question was in the tree.

---

## What the phase hands back for `Not built` rows

| Option | Description | Selected |
|--------|-------------|----------|
| Verdicts plus a scoped work list for Dave's ruling | Each not-built row gets a one-line statement of what closing it would mean, grouped so Dave can rule on what is worth a phase and what should be dropped. The phase builds nothing | ✓ |
| Verdicts only | Cleanest boundary, but Dave would rule on "DOCS-17 is not built" with no sense of what closing it costs | |
| Verdicts, plus draft the follow-on phase entry | Fastest to next work, but presumes the gaps should be closed before Dave has seen them | |

---

## The 24 `human_needed` verification items

| Option | Description | Selected |
|--------|-------------|----------|
| Out — name them, don't touch them | The phase records that they exist and which phases carry them, and stops. They need Dave at a keyboard, so an executor cannot discharge them | ✓ |
| In — audit them the same way | One place for v0.2's whole debt picture, but ~45% bigger phase and most verdicts would read "still needs Dave" | |
| Out, and open a separate phase for them | Keeps this phase on the ledger and puts the 24 into their own interactive phase | |

**Notes:** The third option was declined, so **no separate phase is
commissioned** for the 24 items. Recorded in `<deferred>` so the option survives
if the debt matters at milestone close.

---

## Claude's Discretion

- Plan decomposition — one sequential pass over the 54 rows, or waves by
  phase-lane (Phase 17's 21, Phase 16's 18, the remaining 15). Planner's call.
- Where the two standing checks live in the test tree, and whether one module or
  two.
- The exact status-cell grammar, provided it is recognisably the `DCD-` shape and
  a strict parse can read it.
- **Not discussed, decided by Claude and recorded as D-02:** the checkbox list
  and the traceability table must be asserted to agree, because a reconciliation
  editing one channel and not the other would introduce the first drift this
  ledger has ever had.

## Deferred Ideas

- Fixing the ambiguous-basename hole in `tools/lints/citations.py` (`F-3`,
  `WR-08`) — declined for this phase; wants its own scope.
- Building whatever the `Not built` verdicts identify — out of scope by
  construction; becomes a phase after Dave rules on the work list.
- A dedicated phase for the 24 `human_needed` items — offered and not taken.
- Reconciling the GSD plan counter, which reads `201/181 plans (100%)` because it
  matches SUMMARY files to PLAN files and cannot see a retired phase. A GSD
  tooling limitation, not a ledger row.
