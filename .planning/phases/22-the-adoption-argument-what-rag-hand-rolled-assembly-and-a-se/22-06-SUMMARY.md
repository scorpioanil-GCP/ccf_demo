---
phase: 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se
plan: 06
subsystem: phase close — the §3.1 gate
tags: [close-gate, cross-ai-panel, D-GATE-22, retroactive, criterion-10, phase-23.1]
status: complete
authorship: RETROACTIVE
authored: 2026-08-25
authored-by: "Phase 23.1 plan 23.1-05, under ROADMAP criterion 10"
authored-from:
  - .planning/phases/22-*/22-CLOSE-REVIEWS.md (the close record, 375 lines at HEAD, 284 when first written)
  - docs/DECISIONS.md — the D-GATE-22 entry
  - the seven Phase 22 close commits, 50ad5ec .. 589763d (five attributable to this plan)
requires:
  - .planning/phases/22-*/22-05-SUMMARY.md (the phase-record write this plan gates on)
  - 951eb4a (the phase base — Phase 21.1's close)
provides:
  - the close-gate verification section of 22-CLOSE-REVIEWS.md (eight checks, machine-readable)
  - docs/DECISIONS.md — the D-GATE-22 entry, logged only after Dave's ruling
affects:
  - docs/surface/examples/RETIREMENT-COUPLINGS.md (regenerated twice; 589763d is the phase's last commit)
tech-stack:
  added: []
  patterns: [close-gate-machine-readable-checks, panel-floor-at-least-one-reviewer-resolves, regenerate-report-last]
key-files:
  created: []
  modified:
    - .planning/phases/22-*/22-CLOSE-REVIEWS.md
    - docs/DECISIONS.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
decisions:
  - "The plan VERIFIED the §3.1 close rather than performing it; running the reviewers is §3.1 step 1 and belonged to the close session"
  - "Check 7 was recorded as STOP on its first run and the STOP was left in the file's history rather than overwritten; the triage gap it named was then closed and the check re-measured"
  - "D-GATE-22 was written only after Dave's ruling, in a commit of its own"
metrics:
  duration: unrecorded — reconstructed after the fact
  completed: 2026-08-23
  tasks: 3
  commits: 5 (four attributable to this plan by content; see the attribution note)
---

# Phase 22 Plan 06: The Close Gate — Summary

> ## THIS SUMMARY IS RETROACTIVE
>
> **It was written on 2026-08-25, during Phase 23.1, not at the time of the
> work.** Phase 22's close plan `22-06-PLAN.md` ran on 2026-08-23 and its
> summary was never written; `D-GATE-22` was logged and the phase closed
> without it. Phase 23.1's ROADMAP criterion 10 required that gap to be
> settled, and this file settles it by **Outcome A — written from the Phase 22
> close record.**
>
> **What it was written FROM, so a reader can check every claim against the
> same sources:** `22-CLOSE-REVIEWS.md` in this directory (the close record,
> including its own machine-readable close-gate verification section), the
> `D-GATE-22` entry in `docs/DECISIONS.md`, and the five Phase 22 close
> commits `50ad5ec`, `faa4347`, `efe668c`, `d5dcf27`, `538fbe2`, `c786faf` and
> `589763d`. **Nothing here is written that is not traceable to one of those.**
>
> **What it therefore does NOT contain:** a duration, a task-by-task narration
> of what the executing session saw, the deviations it encountered, or
> anything about the run that only a contemporaneous writer could know. Those
> are absent because they are unknowable now, and an invented account of them
> would be worse than their absence.
>
> **The plan counter was not the reason this file was written.** Criterion 10
> names *"a summary written to make a counter agree"* as RED. Measured after
> this write, the tree holds **225** `*-PLAN.md` files of which **221** have a
> matching `*-SUMMARY.md` — still four short, because Phase 23.1's own plans
> `23.1-05` through `23.1-08` are in flight. The counter does not become clean
> from this write and was never going to. The reason is the one criterion 10
> gives: the close record supports an honest account, so the honest account
> gets written.

---

## What the plan was for

`22-06` existed to **stop the phase**. Plans `22-01` through `22-05` were all
`autonomous: true` and none of them ended in anything that blocks, so Phase 22
could otherwise have been reported complete with the `CLAUDE.md` §3.1 close
never having run. The plan's own objective says it: *"Prose is a handoff; it is
not a gate. This plan is the gate."*

**It did not run the panel.** §3.1's step 1 belongs to the session executing the
close (`D-IMPL-178`). This plan verified that the panel had run, on the right
subject, with its findings verified; presented to Dave; stopped; and logged the
gate afterwards.

## What shipped

| Task | Name | Commit | Files |
| --- | --- | --- | --- |
| 1 | Verify the §3.1 close ran, in its order, on the shipped tree | `efe668c` | `22-CLOSE-REVIEWS.md` (+34) |
| 1 (follow-up) | Regenerate the coupling report | `d5dcf27` | `RETIREMENT-COUPLINGS.md` (1/1) |
| 1 (repair) | Close the triage gap check 7 stopped on | `538fbe2` | `22-CLOSE-REVIEWS.md` (+59/−2) |
| 2 | Present to Dave — the phase gate | *(checkpoint; no commit)* | — |
| 3 | Log `D-GATE-22` after approval | `c786faf` | `docs/DECISIONS.md` (+2) |
| 3 (last) | Regenerate the report LAST, after every `.planning/` write | `589763d` | `RETIREMENT-COUPLINGS.md` (1/1) |

**Attribution note, because it is inferred rather than stated.** `efe668c`,
`d5dcf27` and `c786faf` carry the `22-06` scope in their own subject lines.
`538fbe2` and `589763d` are prefixed `docs(22)` / `chore(22)` and are attributed
to this plan **by content** — the first closes the triage gap check 7 named, the
second is the regenerate-last action task 3 required. That attribution is an
inference from the commit contents and is marked as one.

## The close gate — eight checks, and the one that stopped

The plan required each check recorded on its own line in the machine-readable
form `Check <N>: PASS — <evidence>` or `Check <N>: STOP — <reason>`.

| Measurement | Figure | Control |
| --- | --- | --- |
| `^Check N: PASS` lines at `efe668c` (first run) | **7** | the same reader asked for `PASSS` returns **0** |
| `^Check N: STOP` lines at `efe668c` | **1** — check 7 | — |
| `^Check N: PASS` lines at HEAD (after the repair) | **8** | as above |
| `^Check N: STOP` lines at HEAD | **0** | — |
| `22-CLOSE-REVIEWS.md` length | 284 lines at `50ad5ec` → 318 at `efe668c` → **375** at `538fbe2` and unchanged since | — |

**Check 7 stopped on incomplete triage, and the STOP was not overwritten.** The
record states it in the file: *"The STOP this check raised on its first run was
correct and is preserved above in this file's history rather than overwritten
silently."* Two cursor findings had not been dispositioned; `538fbe2`
dispositioned them — finding 5 ACCEPTED as a false-red limitation deliberately
not fixed, finding 6's accepted half carried to the gate as ROADMAP criterion 2
having no standing gate — and the check was re-measured to PASS.

**The floor that makes the checks non-vacuous.** The plan required at least one
reviewer's citations to resolve against the tree, because a record honestly
reading *"codex FAILED, cursor FAILED, gemini FAILED"* would otherwise satisfy
every process check while proving nothing — the check-vacuity class inside the
gate written to prevent it. The record's own panel table:

| Reviewer | Exit | Findings | Citations resolve? | Verdict |
| --- | --- | --- | --- | --- |
| codex (API-key auth) | 0 | 4 | Yes — all four confirmed by measurement | REVIEWED |
| cursor | 0 | 6 | Yes | REVIEWED |
| gemini | 0 | 5 | Symbols yes, **line numbers drift** | REVIEWED, with a recorded reliability caveat |

`claude` was excluded for independence as the executing model. No reviewer was
recorded FAILED, so the floor held with margin.

## What the close found, which is why the gate was worth having

The close found **eight blocking defects in the phase's own gate**, all fixed
in-phase, each watched RED before green. The division of labour is recorded
because it is the argument for running both halves of §3.1:

- **The panel found the vocabulary holes** — the AW-2 denial limb exempting
  overclaims in four measured join forms; bare plural `lack` missing from
  `LIMIT_VERB` while `lacks` and `lacking` were present, when `DOCS-15`'s own
  text reads *"states what each lacks"*; and the page's house spelling
  `passage_anchor` invisible to the negative predicate.
- **The additive single-agent depth pass found what no panel reviewer reached**
  — that AW-1 had **no jurisdiction over the body of any comparison
  subsection** (four candidate paragraphs, three of them headings), and that
  the page stated two things that were false about tests it cited.

**Two findings were REJECTED and recorded as rejected with refuting evidence**,
one of them (gemini finding 3) rejected *as written* while its underlying
mechanism was confirmed by a corrected probe and fixed — recorded in both
halves rather than as a flat accept or reject.

## The gate state the close left

| Leg | Before close | After close |
| --- | --- | --- |
| `tools/docs_tests` + `tools/publish_scan_tests` | 291 passed | **298 passed, 0 failed** |
| `test_adoption_wording.py` | 24 tests | **31 tests** |
| `make gate-tools` / `make lint` / `make docs-strict` | — | exit 0 each |
| `RETIREMENT-COUPLINGS.md` | 264 / 81 | **267 / 81**, regenerated in the venv |

`src/`, `runtime/` and `examples/` remained diff-empty for the whole phase.

## Dave's ruling

`D-GATE-22` — *"Phase 22 … is APPROVED"* — logged 2026-08-23, Approver: Dave,
in `c786faf`, a commit that touches `docs/DECISIONS.md` and nothing else.
Approval authority is Dave's alone; the panel passing is necessary and never
sufficient. **Five items were carried to him for a ruling rather than absorbed**
(close record §8), and §9 states in terms that nothing known was carried into
the next phase without one.

## Deviations from Plan

**Reconstructed from the record; not observed.** The one departure visible in
the artefacts is that task 1's verification recorded a **STOP** on its first
run rather than eight PASSes, which the plan's own automated verify would have
refused. The response was the one §3.1 requires — the gap was closed in-phase
(`538fbe2`) and the check re-measured — rather than the check being relaxed.
The STOP was left readable in the file's history.

**Whether the executing session encountered any other deviation is unknowable
from the record, and none is claimed.**

## Self-Check

Every artefact this summary names was verified to exist at the stated commit
before this file was written:

- `22-CLOSE-REVIEWS.md` — present, 375 lines, 8 `PASS` / 0 `STOP`.
- `docs/DECISIONS.md` — `D-GATE-22` present, dated 2026-08-23, Approver: Dave.
- `efe668c`, `d5dcf27`, `538fbe2`, `c786faf`, `589763d` — all resolve, with the
  file stats quoted above taken from `git show --stat`.

**Self-Check: PASSED.**
