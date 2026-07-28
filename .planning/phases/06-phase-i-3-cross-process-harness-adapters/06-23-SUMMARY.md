---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 23
subsystem: gate-re-presentation
tags: [gap-closure, verification-sweep, gate-package, D-IMPL-57, D-IMPL-58, D-IMPL-59, B1, B2, B3, A1, A2, A3, A4, A5, A6, A7]
status: checkpoint-blocking-human
requires:
  - 06-18 (GATE_LINEAGE_ATTRIBUTABILITY, the federated gate sequence)
  - 06-19 (AdmissionRecord, the generalized replay resolution path)
  - 06-20 (adversarial harness legs; the capture_effect-delegation limit)
  - 06-21 (transport instance scan + count guard; the scoped AdmittedProduct claim)
  - 06-24 (the Peering seam rename, D-IMPL-59 parts 1-4)
  - 06-25 (the skilling and agent-surface Peering rename)
  - 06-22 (the claim narrowings and disposition table this plan re-verifies)
provides:
  - docs/PHASE_I3_GATE.md §1 rewritten from a post-closure sweep (987/2, 193 conformance)
  - docs/PHASE_I3_GATE.md §1.2 five retired-form greps + two positive naming-ruling checks
  - docs/PHASE_I3_GATE.md §1.6 the wave finding-by-finding, plan-by-plan, commit-by-commit
  - docs/PHASE_I3_GATE.md §2.1 row-by-row re-verification record
  - docs/PHASE_I3_GATE.md §6 rewritten for the second presentation
  - 06-VALIDATION.md gap-closure per-plan verification map + path-vocabulary note
affects:
  - Dave's gate decision (Task 3 — blocking human checkpoint, NOT self-approved)
tech-stack:
  added: []
  patterns:
    - "a gate's evidence must postdate its own fixes: the pre-closure run is named as superseded baseline, never averaged"
    - "a citation sweep must re-run after the last edit, and its flagged set enumerated rather than counted, because adjudicating an item re-flags it"
    - "a `== 0` criterion that diverges from its property loses to the property; verify the property elsewhere and record the divergence"
key-files:
  created: []
  modified:
    - docs/PHASE_I3_GATE.md
    - .planning/phases/06-phase-i-3-cross-process-harness-adapters/06-VALIDATION.md
    - .planning/ROADMAP.md
decisions:
  - "06-22's one carried residual is WITHDRAWN, not fixed: the a2a-named CINV-02 boundary test is accurate, because the module it feeds really is lf_a2a.py"
  - "The plan's own class_id location criterion is recorded as mis-cited and its property verified at the real location, rather than satisfied by moving code into an import cycle"
  - "§4.13's totals are declared non-comparable across runs, with the flagged set enumerated instead"
  - "No gate row was added: 06-22 wrote them; 06-23 establishes they are true"
metrics:
  duration: ~50m
  completed: 2026-07-27
  tasks: 2 of 3 (Task 3 is a blocking human checkpoint)
  files: 3
requirements: [XPRC-01, XPRC-02, XPRC-03]
---

# Phase 06 Plan 23: Post-closure verification sweep and gate re-presentation — Summary

The full verification sweep was re-run **after** the gap-closure wave, every row of
`docs/PHASE_I3_GATE.md` was re-verified by running the command it names, and the gate
package is **READY for Dave's review**. It is **not approved**, and `D-GATE-I.3` is
**not logged** — Task 3 is a blocking human checkpoint and this plan stops at it.

## Verification path — the single most important thing in this summary

Per the orchestrator's finding 1, and asserted before anything was trusted: there is no
`.venv` in this worktree and **both** `ccf` and `ccf_runtime` are installed editable
against the main repo, so a bare invocation verifies the wrong tree. Since this plan's
entire deliverable *is* a verification sweep, a wrong-tree run would have made the gate
package worthless. Both `__file__`s were printed first and both resolve inside the
worktree:

```
ccf:         /home/parkave/ccf_code/.claude/worktrees/agent-ae9a80ff99f11df07/src/ccf/__init__.py
ccf_runtime: /home/parkave/ccf_code/.claude/worktrees/agent-ae9a80ff99f11df07/runtime/ccf_runtime/__init__.py
```

Every leg ran as `PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python`.

The declared-base reset **fired**, as the orchestrator predicted: the worktree spawned at
merge-base `ba0088e` (an ancestor of the declared base) and was reset to `cf8395d`.
Post-reset sanity check passed before any work began — `src/ccf/peering/` present,
`src/ccf/a2a/` absent, and **all seven** SUMMARYs (06-18/19/20/21/22/24/25) present.

## Results — the post-closure sweep

| Leg | Result |
|---|---|
| `pytest -q -rs` | **987 passed, 2 skipped** |
| `CCF_REQUIRE_HARNESSES=1 pytest -q -rs` | **987 passed, 2 skipped**, exit 0, zero harness skips |
| `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance -q -rs` | **193 passed** (was 188 — 06-20 added five) |
| `pytest tools/lints/tests -q` | **49 passed** |
| `tools.lints --all` | **exit 0** |
| `mypy` | **Success, 99 source files** |
| `pip check` | No broken requirements |
| Harness SDKs | `0.2.128` / `1.2.9` / `2.5.0` — all three legs execute |
| `git diff --diff-filter=D --name-only pre-peering -- src/ runtime/ tests/ tools/` | **no output** |
| `git diff --diff-filter=D --name-only main...HEAD -- src/ runtime/ tests/` | **no output** |
| `git diff -M --name-status pre-peering HEAD` | **16 renames**, zero deletions |
| `git diff --name-only .planning/STATE.md` | **empty** — untouched |
| `git diff --name-only docs/DECISIONS.md` / `CLAUDE.md` | **empty** — untouched |

**The 2 skips are the tracked Phase I.4 CINV-04 deferrals**, `hitl-action-capture` and
`workflow-trace-capture` (`tests/invariants/test_replay_by_construction.py:188`). Each
names its unblocking phase and the CLAUDE.md commitment it will enforce in its own `-rs`
skip reason. **They are tracked deferrals, not missing coverage.**

The pre-closure numbers (940 / 188) are recorded in §1 as **superseded baseline, not
averaged** — the plan's own T-06-98 threat.

## Row-by-row re-verification

Every checklist row's module was **re-run**, not re-read, in two batches under
`CCF_REQUIRE_HARNESSES=1`:

- **202 passed** — `tools/lints/tests`, `test_peering_single_writer.py`,
  `test_adapter_single_writer.py`, `test_mcp_role_separation.py`,
  `test_peering_exchange.py`, `tests/peering/`, `test_callables.py` (rows 1–8, 13–15,
  §3.2's verdict row)
- **271 passed** — `tests/conformance`, `test_federated_gates.py`,
  `test_lineage_union.py`, `tests/crossproc`, `test_agent_slice.py`,
  `test_acquisition.py` (rows 9–12, 14, 16–21, all of §3.1/§3.3)

Rows 2, 8, 16, 17 are lint- or grep-carried and were covered by `tools.lints --all` and
the §1.2 re-runs. **No row was found whose breakage column is reasoning rather than an
observed failure** — the four measured counterfactuals rows 3/6/21 and §3.2's part-4 row
rest on (06-18's 3-of-6, 06-20's `DID NOT RAISE AssertionError`, 06-21's
`2 transport(s) are constructed but 1 were discovered`, 06-24's neutered-token
`DID NOT RAISE`) are cited in §2.1.

**No gate row was added.** 06-22 wrote the rows the wave earned; 06-23's job was to
establish they are true of the tree as it now stands, and they are.

## Every closed finding re-verified as still holding

| Closure | Re-verified how | Holds |
|---|---|---|
| **06-18 / B1** — attributability gate; `engine_resolved` and "structurally vacuous" gone | `test_federated_gates.py` + `test_admission_attributability.py` run; both greps → 0 | ✅ |
| **06-19 / B2** — `AdmissionRecord` persisted and resolvable at an exact version | `test_admission_record.py` incl. the persisted-state case; `class_id="ccf.admission-record"` → exactly 1; `"admission_record"` → 0 | ✅ |
| **06-20 / B3** — adversarial legs give the seam-3/seam-4 equalities a failure mode | `tests/conformance` 193 passed | ✅ (A3 still OPEN) |
| **06-21 / A1, A2** — instance scan + count guard; scoped claim; `unforgeable` absent | `test_peering_single_writer.py`, `test_peering_exchange.py` run | ✅ |
| **06-24 / D-IMPL-59 part 4** — a Peering declares trust inputs, never the verdict | `test_peering_verdict.py` 6 cases; `class PeeringProtocol` → 1; unsuffixed `Peering` → 0; `ccf.a2a`/`ccf_runtime.a2a` → 0 files | ✅ |
| **06-25** — catalog/dispatcher speak `peering`; `_BINDING_CONTRACTS` present | `tests/skills` 86 passed | ✅ |
| **06-22** — narrowings, §3.2.1/§3.3.1/§4.13, 10-row disposition table | §4.13 re-swept; A4's corrected path **run** (49 passed) | ✅ |

Nothing was quietly patched. Nothing was re-litigated.

## Open advisories — presented as OPEN, with consequences

| Advisory | Status | Consequence |
|---|---|---|
| **A3** — the Claude leg's seam-4 `execution()` is a hand-built `ResultMessage` | **OPEN**, Phase 8 `examples/03-harness-portability` | trace-equivalence evidence is **two-legged in substance**, not three |
| **A6** — `SkillCatalogEntry` declares no tool description or argument schema | **OPEN**, target `D-IMPL-56` | every future adapter re-derives both; the first to derive them differently **silently breaks D-18 harness equivalence** |
| **A7** — the LangGraph adapter's `_build_graph` topology | **OPEN**, Phase 7 against `D-IMPL-17` | the one place the SDK authors execution shape; I.4 must not inherit it as a workflow engine |

Also presented as outstanding, not discharged: **CLAUDE.md §7.3's "one agent definition
running unmodified under at least two harnesses"** — I.3 delivers seam-level portability
and the mechanism; loop-level execution is example 03's Phase 8 obligation (§3.3.1).

## Deviations from Plan

### 1. [Rule 3 — Blocking] Every `<verify>` and criterion command in the plan would have verified the wrong tree

- **Issue:** the plan specifies `.venv/bin/python -m pytest` etc. throughout. There is no
  `.venv` here, and the main interpreter resolves both packages to the main repo.
- **Fix:** every leg run as `PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python`,
  with both `__file__`s asserted inside the worktree first. **Sixth consecutive plan to hit
  this defect.**

### 2. [Rule 3 — Blocking] Task 1's `class_id` location criterion is false against the tree

- **Issue:** the criterion is `grep -c 'class_id="ccf.admission-record"'
  src/ccf/controlplane/artifacts.py == 1`. The file exists, but the registration **cannot**
  live there: `products.contract → controlplane.registry → controlplane.artifacts` is an
  import cycle, which is why 06-19 placed `ADMISSION_RECORD` beside the contract it declares.
  This is the **third** appearance of the same mis-citation (06-19 and 06-24 carried it too),
  exactly as the orchestrator's finding 3 predicted.
- **Fix:** the **property** was verified instead and wins over the proxy —
  `grep -rn 'class_id="ccf.admission-record"' src runtime tests` returns exactly **one** hit,
  at `src/ccf/peering/admission.py:471`. Recorded as a quoted correction inside gate §1.2 so
  the third instance is not silent. **No code was moved to make the plan's literal text true**;
  doing so would have introduced an import cycle to satisfy a grep.

### 3. [Rule 1 — Finding corrected] 06-22's one carried residual is WITHDRAWN — it was never a residual

- **Found during:** Task 2, on reading the code rather than the finding.
- **Issue:** the orchestrator's finding 5 and gate §3.2.1 carried
  `test_a_harness_import_in_the_a2a_module_is_still_flagged` as a lagging label, on the
  reading that `a2a` was left over from the retired `ccf_runtime.a2a` package. It is not: the
  module the test feeds is `runtime/ccf_runtime/peering/lf_a2a.py`, so **"the a2a module"
  names `lf_a2a` accurately.**
- **Fix:** **no rename.** Renaming to "the peering module" would be a *regression in
  precision* — two transports live under `ccf_runtime.peering`, and this test is specifically
  about the A2A one (a sibling test covers the lookalike case). This is §3.2.1's own rule —
  *a transport is correctly named for the wire it speaks*, D-IMPL-59 part 2 — applied to a test
  name. Gate row 1 and §3.2.1 both corrected to say the name is right and nothing is
  outstanding. This is the orchestrator's explicit "decide it is out of scope, say so
  explicitly" branch, resolved on the stronger ground that it is not a defect at all.

### 4. [Rule 2 — Missing critical accuracy] Three stale ROADMAP prose items the plan did not name

Criterion 4 and evidence bullet 4 still said **"the A2A boundary"** — 06-22 narrowed criteria
1–3 to the D-IMPL-59 vocabulary and left criterion 4 behind. And the evidence preamble said
**"20-row checklist"** when 06-22 appended row 21. A criterion whose vocabulary predates the
ruling it is presented under is the same class as evidence that predates its fixes, so all
three were corrected. Strictly in-scope per `<shared_artifact_ownership>` (claim prose and
criterion-evidence bullets).

### 5. [Rule 2] §4.13's counts cannot be compared across runs, and the document now says so

Re-running the sweep after my own edits gave 56 paths / 66 citations against 06-22's 47 / 63.
The rise is **inherent**: naming `runtime/mcp/egress.py` in a cell that explains it is an
extraction artifact adds an occurrence for the next sweep to flag. Rather than quietly
report a bigger number, §4.13 now **enumerates the flagged set in three adjudicated classes**
(extraction artifacts, globs, one deliberate forward reference) and declares the totals
non-comparable, with **zero genuinely unresolved** as the invariant. Six flagged citations
were all *extractor* faults — two are the prose phrase "`file::function`" itself and four were
mis-attributed by path carry-over; all four real names were confirmed by
`grep -rn "def <name>"`.

### 6. [Rule 2] `06-VALIDATION.md` had 12 dead paths; a mapping note was added rather than 12 rewrites

Rows `06-07-*`..`06-10-*` and note (c) cite pre-rename paths (`src/ccf/a2a/`,
`tests/crossproc/test_a2a_exchange.py`). Those were accurate when executed, so rewriting them
would falsify the historical record — but leaving them is A4's exact defect (a link a reader
cannot follow). Resolved with a **path-vocabulary note** giving the five-row mapping once,
plus the `grep → 0 files` proof that the old names are gone from the code.

### 7. [Informational] §1.1 said "both" where the count is three

06-22 raised the finding count from two to three and left the following sentence reading
"because **both** are cases of". Corrected, and flagged inline as the same residual class row 1
names.

## The approval boundary — held

- **`D-GATE-I.3` is NOT logged.** The Gate Log in `docs/DECISIONS.md` ends at `D-GATE-I.2`;
  `grep -cE "^\*?\*?D-GATE-I\.3 —|^#+ .*D-GATE-I\.3"` → **0**. `docs/DECISIONS.md` shows **no
  diff** from this plan. The literal `grep -c "D-GATE-I.3"` is **1** — a prose mention inside
  D-IMPL-58's own text, already present at the base, deliberately left alone per the
  orchestrator's finding and 06-22's precedent.
- **The gate package is recorded as READY for Dave's review, never as approved**, in both
  `docs/PHASE_I3_GATE.md` (§6, and the unchanged `Status: AWAITING REVIEW` banner) and
  `06-VALIDATION.md`'s gap-closure sign-off.
- **`phase-i3` is not merged.**
- **`.planning/STATE.md` was never opened for writing.** **`CLAUDE.md` untouched** — §7.3's
  clause is discharged by the Phase 8 example-03 obligation, and no §6 amendment request is
  made.

## ROADMAP: exactly which lines changed (boundary check)

Per `<shared_artifact_ownership>`. Three prose hunks, verified by reading the full diff:

| Line(s) | What |
|---|---|
| 240 | criterion 4 — "A2A boundary" → **Peering** boundary (D-IMPL-59); notes the typed door |
| 245–249 | criterion-evidence preamble — "20-row" → **21-row**; names 06-23's post-wave re-run |
| 269–272 | criterion-evidence bullet 4 — Peering vocabulary; WAL-inclusive digest + its guard |

**Not touched:** `**Plans:** 24/25 plans executed` (line 243), every plan checkbox, the
Progress table, and every phase status/date field. Asserted mechanically —
`git diff .planning/ROADMAP.md | grep -E "^[-+]" | grep -icE "plans:|\[x\]|\[ \]|Progress|Status.*:|Completed"` → **0**.

## Threat Register Outcomes

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-06-98 (tampering — gate evidence predating the fixes it describes) | mitigate | §1 rewritten from a sweep executed in this plan, after every wave commit; the 940/188 baseline is named as **superseded**, not carried or averaged; §1.6 pins the wave's commits so the ordering is checkable |
| T-06-99 (elevation of privilege — a plan logging `D-GATE-I.3` on Dave's behalf) | mitigate | asserted absent three ways (no diff, no entry-shaped heading, Gate Log ends at I.2); approval left as a blocking human checkpoint; this plan **stops** |

## Known Stubs

None. This plan writes prose and runs commands; there is no data path to leave unwired.

## Threat Flags

None. Three documentation files. No code, no endpoint, no auth path, no schema change.

## Out of Scope / Follow-on

- **Task 3 is Dave's.** The gate package is presented; the response is not this plan's to
  record beyond noting that it was not given.
- **`D-IMPL-56` is open** and Dave is asked to rule on it (gate §6 step 6). It does not block
  the gate but accrues adapter-side derivations (A6).
- **A3, A6, A7** carried forward with consequences, targets named in gate §5.
- **On approval — and only then** — `D-GATE-I.3` is appended with the date and `phase-i3` is
  merged `--no-ff` referencing it (CLAUDE.md §2.2, §3.1 step 4). Phase 7 begins after both.

## Self-Check: PASSED

- `docs/PHASE_I3_GATE.md` — FOUND (modified)
- `.planning/phases/.../06-VALIDATION.md` — FOUND (modified)
- `.planning/ROADMAP.md` — FOUND (modified, prose only)
- commits `5c99b0c`, `afa4248`, `306f267` — all present in `git log`
- 987 passed / 2 skipped with `CCF_REQUIRE_HARNESSES=1`; lints exit 0; mypy 99 files — CONFIRMED
- both `__file__`s inside the worktree — CONFIRMED
- no deletions vs `pre-peering` **and** vs `main...HEAD` — CONFIRMED
- `STATE.md`, `docs/DECISIONS.md`, `CLAUDE.md` — no diff — CONFIRMED
- `D-GATE-I.3` not logged — CONFIRMED
