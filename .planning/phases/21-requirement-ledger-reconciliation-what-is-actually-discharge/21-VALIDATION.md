---
phase: 21
slug: requirement-ledger-reconciliation-what-is-actually-discharge
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-21
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest, via `.venv/bin/python -m pytest` |
| **Config file** | `pyproject.toml` — `testpaths = ["tests"]`, which deliberately EXCLUDES `tools/`; that is why `make gate-tools` exists as a separate target and why the new module is reached by `Makefile:188-190` leg 2 |
| **Quick run command** | `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations` |
| **Full suite command** | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q && make ci-core` |
| **Estimated runtime** | citation lint ~5s · ledger module <5s · `make gate-tools` ~45s · `make ci-core` several minutes |

**Both env prefixes are required.** System `python3` cannot import `ccf_runtime` and leg 2 of
`gate-tools` fails to collect. `ENV_DOCS := PYTHONPATH=.:src:runtime` (`Makefile:23`),
`PYTHON := .venv/bin/python` (`Makefile:10`).

---

## Sampling Rate

- **After every task commit:** `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations`
  — seconds, and it catches a badly-formed verdict citation immediately. `.planning/REQUIREMENTS.md`
  is inside `GATED_TREES` with no exemption, so a wrong symbol on a real path is an immediate
  `cite03-node-id` finding and `make lint` exits non-zero.
- **After every task that edits the ledger:**
  `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q`
- **After every plan wave:** `make ci-core` — it MUST stay green from Wave 1 onward (`Makefile:138`)
- **Before the close:** `make ci` exit 0 with `RETIREMENT-COUPLINGS.md` regenerated LAST
- **Max feedback latency:** 5 seconds for the citation lint, under 60 seconds for the ledger module

---

## The sequencing constraint

`ci-core` must stay green throughout. A completeness assertion is RED from the moment it lands
until the last row is written. The checks are therefore split by tense:

| Lands | Property | True of a partially-filled ledger? |
|-------|----------|-----------------------------------|
| Wave 1 (`21-01`) | every citation present is a full, existing, `.py`-for-`::` path | yes — and **vacuously so at wave 1**, because there are ZERO citation-shaped tokens in any status cell at the pinned base (measured with the lint's own `NODE_ID` and line-citation patterns: 0 matches, both). Vacuous is the CORRECT wave-1 behaviour for the refusal; it becomes load-bearing the instant `21-02` writes the first citation |
| Wave 1 (`21-01`) | the parse raises on ZERO ROWS | yes — false today (the table is non-empty; 143 rows as MEASURED, not as asserted — `D-21`), so the guard is honest on landing |
| ~~Wave 1~~ **Wave 2 (`21-02`)** | the parse raises on ZERO CITATIONS, and a precondition proves the real file yields citations | **no at wave 1 — both would FAIL on landing and redden `ci-core` for five waves.** Relocated to `21-02` task 1, immediately after the first eight citations are written. Relocated, not weakened |
| Wave 1 (`21-01`) | the two channels agree | yes — 0 drift today, preserved by each edit |
| Wave 1 (`21-01`) | every verdict token present is in the six-word vocabulary (`Pending` admitted while the phase runs) | yes |
| Wave 1 (`21-01`) | no cell carries two verdict tokens — **with CONTROL 11, its negative twin, in the SAME wave** | yes. CONTROL 11 doctors an in-memory cell and needs no written verdicts, so nothing justified deferring it; a gate shipped five waves before its refusal is ever watched fire is the thing this phase exists to name |
| Wave 1 (`21-01`) | `src/`, `runtime/`, the scope fence, `tools/lints/citations.py` and the **eleven** UAT records are untouched | yes |
| Wave 1 (`21-01`) | both channels parse NON-EMPTY and agree id-for-id on every id the ledger contains, with no row count carried (`D-21`) | yes, from task 2 forward. 133 rows at the pinned base and 143 after the mint are HISTORY recorded in a `#:` comment; no assertion reads either figure |
| Wave 6 (`21-06`) | the 54-row completeness count | **no — red until the last row lands** |
| Wave 6 (`21-06`) | the ten `RECON-` rows carry verdicts | **no — red until `21-06` writes them**, which is before the close panel and the gate |
| Wave 6 (`21-06`) | `tests/` untouched (criterion 6's mechanical limb) | yes, but grouped with criterion 1 |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | RECON-08 | T-21-04 / T-21-05 / T-21-06a / T-21-06b | the CI `docs` job (the one that runs `tools/docs_tests`) has full history so the pinned base resolves; an unresolvable base raises rather than returning an empty string that reads like a clean tree; `tools/lints/citations.py` is byte-identical to the base (D-07); the UAT roster is eleven paths, re-parsed not queried (D-20) | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ❌ W1 creates | ⬜ pending |
| 21-01-02 | 01 | 1 | RECON-06, RECON-01 | T-21-03 / T-21-02 / T-21-06c | the ten `RECON-` rows are minted `Pending` in both channels, and the channels are asserted to agree id-for-id on every id the ledger contains with no count carried (`D-21`); a status written to one channel and not the other is refused, naming the id; a doubled verdict cell is refused, with CONTROL 11 in the same wave | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ❌ W1 creates | ⬜ pending |
| 21-01-03 | 01 | 1 | RECON-03 | T-21-01 / T-21-02 | a bare, ambiguous, nonexistent or non-`.py`-`::` cited path is refused, and a zero-ROW parse raises (the zero-CITATION guard is `21-02`'s, where citations exist); the coupling report is regenerated after the SUMMARY | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ❌ W1 creates | ⬜ pending |
| 21-02-01 | 02 | 2 | RECON-02, RECON-03 | T-21-07 / T-21-08 / T-21-12a | every `CLNT-01`..`08` citation resolves as written and names its guarding test; the relocated zero-CITATION guard, its precondition and CONTROL 5b land here and are watched go red | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q && PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations` | ✅ | ⬜ pending |
| 21-02-02 | 02 | 2 | RECON-02 | T-21-07 / T-21-10 | gate-reachability claims cite the `Makefile`/workflow lines with a tokenish anchor the lint checks | integration | same as 21-02-01 | ✅ | ⬜ pending |
| 21-02-03 | 02 | 2 | RECON-01, RECON-02 | T-21-11 | the generated coupling inventory is regenerated after the last `.planning/` write and committed | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-03-01 | 03 | 3 | RECON-02, RECON-04 | T-21-14 / T-21-16 | no qualifying clause carries a `HISTORICITY_MARKERS` phrase that would exempt its own evidence | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q && PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations` | ✅ | ⬜ pending |
| 21-03-02 | 03 | 3 | RECON-02 | T-21-15 / T-21-17 | documentation rows cite the guarding gate, not the document, and no test is written to supply a name | integration | same as 21-03-01 | ✅ | ⬜ pending |
| 21-03-03 | 03 | 3 | RECON-01, RECON-02 | T-21-13 / T-21-11 | `CPS-03` cites both rulings and carries the by-design clause; the report is regenerated last | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-04-01 | 04 | 4 | RECON-05, RECON-04 | T-21-19 / T-21-20 | every side-B/C section names an absence a reader can check by looking | inspection + gate | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ✅ | ⬜ pending |
| 21-04-02 | 04 | 4 | RECON-01, RECON-05 | T-21-22 / T-21-23 | no id is dropped; the parse still reports an identical id set in both channels with zero disagreements and every frozen roster unchanged (`D-21`) | integration | same as 21-04-01 plus `-m tools.lints --citations` | ✅ | ⬜ pending |
| 21-04-03 | 04 | 4 | RECON-01, RECON-05 | T-21-21 / T-21-11 | `examples/00`-`08` are named as an absence and NOT retired; the report is regenerated last | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-05-01 | 05 | 5 | RECON-04, RECON-07 | T-21-30 / T-21-30b | all ELEVEN `*-VERIFICATION.md` paths exist, are re-derived by parse rather than by `audit-uat`, sum to 27 items, and are shown untouched against the pinned base; the 24-vs-27 delta and its cause are stated (D-20) | gate | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ✅ | ⬜ pending |
| 21-05-02 | 05 | 5 | RECON-10 | T-21-25 / T-21-26 / T-21-28 / T-21-28b | each counter edit is a hand-edit with a backup and a diff; each counter's line is re-resolved at execution time rather than trusted from the plan; the table still parses with both channels agreeing id-for-id and no carried count (`D-21`), and `roadmap.get-phase 21` still to 14 criteria one per line | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-06-01 | 06 | 6 | RECON-01, RECON-02 | T-21-32 / T-21-33 / T-21-34 / T-21-37b | the ten `RECON-` rows are verdicted (before the close panel); 54 roster ids carry a verdict, none carries two, none is missing; `tests/` is untouched | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ✅ | ⬜ pending |
| 21-06-02 | 06 | 6 | RECON-09 | T-21-35 | `STATE.md`/`ROADMAP.md` hand-edited; the fourteen criteria still parse one per line | integration | `gsd-sdk query roadmap.get-phase 21 --raw` | ✅ | ⬜ pending |
| 21-06-03 | 06 | 6 | RECON-09 | T-21-36 / T-21-37 | `make ci` exit 0 with the report regenerated last; `fetch-depth: 0` still present on the **`docs`** job (the one running `tools/docs_tests`) as well as the **`test`** job (singular — `.github/workflows/ci.yml:47`), checked with a range form that EXCLUDES the start line: `awk '/^  docs:/{f=1;next} f&&/^  [a-z_-]+:/{f=0} f' .github/workflows/ci.yml | grep -c "fetch-depth: 0"` >= 1, plus the file-scoped `grep -c "fetch-depth: 0" .github/workflows/ci.yml` >= 2. The form `awk '/^  docs:/,/^  [a-z]/'` collapses to the single line `  docs:` and returns 0 for a correct workflow | e2e | `make ci` | ✅ | ⬜ pending |
| 21-07-01 | 07 | 7 | RECON-09 | T-21-39 / T-21-40 / T-21-42 / T-21-43 | every finding verified against the tree; every blocker fixed with a standing control; the panel reads the same ledger Dave approves — this plan adds no rows | e2e | `make ci` | ✅ | ⬜ pending |
| 21-07-02 | 07 | 7 | RECON-09 | T-21-41 | the phase closes only on Dave's ruling, logged as `D-GATE-21` | manual | human-check | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Landed by plan `21-01` (wave 1), because the phase has no wave 0:

- [ ] `.github/workflows/ci.yml` — `fetch-depth: 0` on the `docs` job's checkout, landed FIRST,
      before the module. That job runs `pytest tools/publish_scan_tests tools/docs_tests -q`; at
      `fetch-depth: 1` every pinned-base assertion in the new module resolves a SHA absent from
      the clone, `git` exits non-zero, `fabric_diff` raises by design, and the job is red from
      wave 1 while passing locally. Same defect class as the `D-GATE-20` shallow-clone fix, in a
      second job. `.github/` is outside the `FENCE` tuple, so this is not a scope-fence breach.
- [ ] `tools/docs_tests/test_requirement_ledger.py` — the shared strict parser, Check A
      (criteria 3, 4, 5) minus the zero-CITATION guard, Check B (criterion 2's vocabulary limb and
      criterion 10), the pinned-base helper and the untouched-tree assertions (criteria 11, 12,
      plus `PINNED_FILES` for D-07), with CONTROLS 1-5, 6-9, 9b, 11 and A-C.
      **The completeness count (criterion 1) is deliberately NOT here.**
      **The zero-CITATION guard and `test_the_scan_finds_citations_to_check` are deliberately NOT
      here** — measured zero citations at the pinned base; they land in `21-02` task 1.
- [ ] `.planning/REQUIREMENTS.md` — the ten `RECON-01`..`RECON-10` rows minted as `Pending` in
      both channels, taking the table from 133 rows to 143. Their verdicts land in `21-06`, before
      the close panel.
- [ ] `.planning/phases/21-*/21-BASE-COMMIT.txt` — the pinned 40-hex SHA plus the comment naming
      what reads it.
- [ ] No framework install. No new package. No `pyproject.toml` change.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A named test genuinely GUARDS the row's property | RECON-02 (criterion 6, semantic limb) | that a test guards a stated property is a judgement no assertion can make; the mechanical limb (the named test exists and is collected, and `tests/` is untouched) IS asserted | spot-check three rows: open the cited test, confirm it fails if the row's property regresses |
| A `RECON-` verdict is proportionate to what the phase actually discharged | RECON-01..10 | whether `Partial` or `Complete` is right for the phase's own row is a judgement the parser cannot make; the mechanical limb (a vocabulary token, not a bare `Pending`, in both channels) IS asserted by `test_every_phase_own_row_carries_a_verdict` + CONTROL 14 | the close panel is asked specifically whether any `RECON-` row claims `Complete` for a criterion not yet discharged |
| A `Not built`/`Orphaned` absence is checkable by looking | RECON-04 (criterion 7) | a regex requiring *a* path-shaped token would be a shape check masquerading as a substance check — this project's own recorded defect class. Do not fake it | read each such cell, look for the named file or directory, confirm it is absent or present as stated |
| The work list is rulable | RECON-04 (criterion 8) | quality of a decision aid is a judgement | Dave reads `21-FINDINGS.md` section 2 and rules |
| The Phase 16 split is correct | RECON-05 (criterion 9) | the split's correctness is Dave's to rule (D-12); "still present, still not `Complete`" IS mechanical off the parser | Dave reads `21-DOCS-16-SPLIT.md`'s summary table |
| `D-GATE-21` is logged on Dave's approval | RECON-09 (criterion 14) | approval authority is Dave's alone (CLAUDE.md §2, §3.1). A test asserting the STRING `D-GATE-21` exists would be exactly the check-that-cannot-fail shape this project keeps recording | inspection of `docs/DECISIONS.md` after the gate |

---

## Validation Sign-Off

- [ ] All tasks have an `<automated>` verify or are the one blocking human checkpoint
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 1 covers every MISSING reference (there is no wave 0; `21-01` is the scaffold)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for the per-task command
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
