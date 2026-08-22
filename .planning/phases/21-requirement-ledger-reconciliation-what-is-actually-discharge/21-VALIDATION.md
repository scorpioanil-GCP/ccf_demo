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
| Wave 1 (`21-01`) | every citation present is a full, existing, `.py`-for-`::` path | yes — vacuously at zero verdicts, and after each one |
| Wave 1 (`21-01`) | the two channels agree | yes — 0 drift today, preserved by each edit |
| Wave 1 (`21-01`) | every verdict token present is in the six-word vocabulary | yes |
| Wave 1 (`21-01`) | no cell carries two verdict tokens | yes |
| Wave 1 (`21-01`) | `src/`, `runtime/`, the scope fence and the nine UAT records are untouched | yes |
| Wave 6 (`21-06`) | the 54-row completeness count | **no — red until the last row lands** |
| Wave 6 (`21-06`) | `tests/` untouched (criterion 6's mechanical limb) | yes, but grouped with criterion 1 |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | RECON-08 | T-21-04 / T-21-05 | an unresolvable diff base raises rather than returning an empty string that reads like a clean tree | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ❌ W1 creates | ⬜ pending |
| 21-01-02 | 01 | 1 | RECON-06, RECON-01 | T-21-03 / T-21-02 | a status written to one channel and not the other is refused, naming the id | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ❌ W1 creates | ⬜ pending |
| 21-01-03 | 01 | 1 | RECON-03 | T-21-01 / T-21-02 | a bare, ambiguous, nonexistent or non-`.py`-`::` cited path is refused, and a zero-citation parse raises | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ❌ W1 creates | ⬜ pending |
| 21-02-01 | 02 | 2 | RECON-02 | T-21-07 / T-21-08 | every `CLNT-01`..`08` citation resolves as written and names its guarding test | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q && PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations` | ✅ | ⬜ pending |
| 21-02-02 | 02 | 2 | RECON-02 | T-21-07 / T-21-10 | gate-reachability claims cite the `Makefile`/workflow lines with a tokenish anchor the lint checks | integration | same as 21-02-01 | ✅ | ⬜ pending |
| 21-02-03 | 02 | 2 | RECON-01, RECON-02 | T-21-11 | the generated coupling inventory is regenerated after the last `.planning/` write and committed | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-03-01 | 03 | 3 | RECON-02, RECON-04 | T-21-14 / T-21-16 | no qualifying clause carries a `HISTORICITY_MARKERS` phrase that would exempt its own evidence | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q && PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --citations` | ✅ | ⬜ pending |
| 21-03-02 | 03 | 3 | RECON-02 | T-21-15 / T-21-17 | documentation rows cite the guarding gate, not the document, and no test is written to supply a name | integration | same as 21-03-01 | ✅ | ⬜ pending |
| 21-03-03 | 03 | 3 | RECON-01, RECON-02 | T-21-13 / T-21-11 | `CPS-03` cites both rulings and carries the by-design clause; the report is regenerated last | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-04-01 | 04 | 4 | RECON-05, RECON-04 | T-21-19 / T-21-20 | every side-B/C section names an absence a reader can check by looking | inspection + gate | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ✅ | ⬜ pending |
| 21-04-02 | 04 | 4 | RECON-01, RECON-05 | T-21-22 / T-21-23 | no id is dropped; the parse still reports 133 rows and 133 checkbox ids | integration | same as 21-04-01 plus `-m tools.lints --citations` | ✅ | ⬜ pending |
| 21-04-03 | 04 | 4 | RECON-01, RECON-05 | T-21-21 / T-21-11 | `examples/00`-`08` are named as an absence and NOT retired; the report is regenerated last | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-05-01 | 05 | 5 | RECON-04, RECON-07 | T-21-30 | the nine `*-VERIFICATION.md` paths all exist and are shown untouched against the pinned base | gate | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ✅ | ⬜ pending |
| 21-05-02 | 05 | 5 | RECON-10 | T-21-25 / T-21-26 / T-21-28 | each counter edit is a hand-edit with a backup and a diff, and the table still parses to 133 | integration | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py tools/docs_tests/test_retirement_sweep.py -q && make ci-core` | ✅ | ⬜ pending |
| 21-06-01 | 06 | 6 | RECON-01, RECON-02 | T-21-32 / T-21-33 / T-21-34 | 54 roster ids carry a verdict, none carries two, none is missing, and `tests/` is untouched | unit | `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests/test_requirement_ledger.py -q` | ✅ | ⬜ pending |
| 21-06-02 | 06 | 6 | RECON-09 | T-21-35 | `STATE.md`/`ROADMAP.md` hand-edited; the fourteen criteria still parse one per line | integration | `gsd-sdk query roadmap.get-phase 21 --raw` | ✅ | ⬜ pending |
| 21-06-03 | 06 | 6 | RECON-09 | T-21-36 / T-21-37 | `make ci` exit 0 with the report regenerated last; `fetch-depth: 0` still present | e2e | `make ci` | ✅ | ⬜ pending |
| 21-07-01 | 07 | 7 | RECON-09 | T-21-39 / T-21-40 / T-21-42 / T-21-43 | every finding verified against the tree; every blocker fixed with a standing control | e2e | `make ci` | ✅ | ⬜ pending |
| 21-07-02 | 07 | 7 | RECON-09 | T-21-41 | the phase closes only on Dave's ruling, logged as `D-GATE-21` | manual | human-check | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Landed by plan `21-01` (wave 1), because the phase has no wave 0:

- [ ] `tools/docs_tests/test_requirement_ledger.py` — the shared strict parser, Check A
      (criteria 3, 4, 5), Check B (criterion 2's vocabulary limb and criterion 10), the pinned-base
      helper and the untouched-tree assertions (criteria 11, 12), with CONTROLS 1-9 and A-C.
      **The completeness count (criterion 1) is deliberately NOT here.**
- [ ] `.planning/phases/21-*/21-BASE-COMMIT.txt` — the pinned 40-hex SHA plus the comment naming
      what reads it.
- [ ] No framework install. No new package. No `pyproject.toml` change.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A named test genuinely GUARDS the row's property | RECON-02 (criterion 6, semantic limb) | that a test guards a stated property is a judgement no assertion can make; the mechanical limb (the named test exists and is collected, and `tests/` is untouched) IS asserted | spot-check three rows: open the cited test, confirm it fails if the row's property regresses |
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
