---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 01
subsystem: planning-record
status: complete
tags: [decisions, requirements, ergo-03, gate-2, criterion-10, assembly-mode]
requires:
  - .planning/phases/16-documentation-rewrite-the-deterministic-path-the-adoption-ar/16-CONTEXT.md  # D-02, D-13, D-14, D-15
  - .planning/phases/15.1-ergonomics-gap-closure/deferred-items.md  # the four Gate-2 residuals
  - src/ccf/replay/serve.py  # read to make the D-02 argument true against code
provides:
  - "D-IMPL-94 — the Phase 16 ruling package"
  - "DOCS-07..DOCS-18 — the Phase 16 requirement lane"
  - "docs/surface/examples/ERGO-03-FROZEN.md — ERGO-03's evidence, frozen"
  - "limb 1 — authority for plan 16-18 to re-floor four non-vacuity constants"
  - "limb 2 — authority for plan 16-15 to retire a single-witness assertion"
  - "D-13 carve-out — authority for plan 16-04's one src/ docstring edit"
affects:
  - "plans 16-02, 16-03, 16-04 (blocked on the checkpoint)"
  - "plans 16-06 (Q-7), 16-12 (Q-8), 16-15 (limb 2), 16-18 (limb 1), 16-19 (D-13 allowlist)"
tech-stack:
  added: []
  patterns:
    - "DECISIONS.md Shape B — one paragraph, inline bold sub-headers, no fenced block, Originates: tail"
    - "freeze-then-retire — capture scripted evidence at a named SHA before deleting the check that produced it"
key-files:
  created:
    - docs/surface/examples/ERGO-03-FROZEN.md
    - .planning/phases/16-documentation-rewrite-the-deterministic-path-the-adoption-ar/deferred-items.md
  modified:
    - docs/DECISIONS.md
    - .planning/REQUIREMENTS.md
    - docs/SURFACE-AUDIT.md
    - tools/measure_examples.py
  deleted:
    - tests/examples/test_surface_audit.py
decisions:
  - "assembly_mode on a product class describes the SUBSTRATE, not the delivered artifact (Q-2)"
  - "Mode 2 packaging attaches above serve(), never inside it (D-02)"
  - "criterion 10 carries one enumerated exception: ProductClassDeclaration's docstring (D-13)"
  - "the four Gate-2 tripwire residuals carry to Phase 17, bounded on two limbs (D-14)"
  - "ERGO-03's measurement is frozen at e7e1729; the running test is retired (D-15)"
metrics:
  tasks_completed: 2
  tasks_total: 3
  commits: 3
  duration: ~75 min
  completed: 2026-08-10
---

# Phase 16 Plan 01: Ruling Package, Requirement Ledger, ERGO-03 Freeze — Summary

`D-IMPL-94` rules Mode 2 packaging attaches above `serve()` and that
`assembly_mode` describes the substrate; twelve DOCS requirements are minted and
eight DEMO/EXAM rows re-homed; ERGO-03's Phase 15 measurement is frozen as
scripted output at a named SHA and its running check retired. No source file
changed.

**Status: complete.** Tasks 1 and 2 were committed, then Task 3's blocking
`checkpoint:human-verify` was put to Dave and **approved as recorded**
(2026-08-10). It was not self-approved by the executor. Plans 16-02, 16-03,
16-04 and 16-21 are unblocked.

## What was built

### Task 1 — `D-IMPL-94` (commit `e7e1729`)

One appended entry in `docs/DECISIONS.md`, in the Shape B house form
`D-IMPL-93` establishes: a single paragraph, inline bold sub-headers, no fenced
code block, an explicit date and approver, and an `Originates:` tail. `D-IMPL-94`
was verified as the next free id (highest at base was `D-IMPL-93`); no
correction was needed.

The seven sub-headers, in the ordered form the plan specified:

1. **The ruling.** Mode 2 (`llm_packaged`) attaches **above** `serve()`,
   consuming the `ServedProduct`, never inside it.
2. **What `assembly_mode` describes (Q-2).** The **substrate**.
3. **No code accompanies this ruling.**
4. **Criterion 10's one enumerated exception (D-13).**
5. **The four Gate-2 tripwire residuals are NOT in Phase 16 (D-14)** — with the
   two-limb bound.
6. **ERGO-03's measurement is frozen; the running test retires (D-15).**
7. **The three open questions this phase answers by disposition** — Q-6, Q-7,
   Q-8.

**The structural argument was re-derived from the module, not copied from the
plan.** The plan's `<interfaces>` block asserts `serve()` "contains no
rendering, no payload transformation, and no branch." Read at HEAD, the first
two are exactly true and the third is not literally true: `serve()` carries
three `QueryPinMismatch` guard branches. The entry therefore states the accurate
and stronger version — *its only branches are refusals raised before any store
write, so exactly one path reaches a return and that path runs through the
append* — which is what the Phase 04 decision actually claims and what a
packaging stage inside `serve()` would violate. Recorded as a deviation below.

**Whitepaper citation discipline held (T-16-01-01).** §7.6 is cited by section
number and title (*Context Products — System of Delivery*) with no body text, so
the sentence is safe to copy into `public/` when plan 16-13 does.

### Task 2 — requirement ledger and ERGO-03 freeze (commit `2c52b5f`)

**(a) The DOCS lane.** Twelve unchecked rows, `DOCS-07` through `DOCS-18`, one
sentence each, under the existing `### Documentation (DOCS)` heading. Twelve
matching traceability rows `| DOCS-NN | Phase 16 | Pending |`.

**(b) Re-homing, not retirement (`D-08`).** Each of DEMO-01..03 and EXAM-01..05
gains a bracketed `**[Phase 16 re-homing, D-08]**` sub-bullet naming its
receiving example or page. No duplicate id was minted and no Status column
moved. The minting note in the trailing prose block follows the SUBQ-12..14
precedent and records three things a later reader would otherwise reconstruct
wrongly: that Phase 16 mints under the inserted-phase precedent; that the eight
DEMO/EXAM rows re-home rather than retire; and that DOCS-01..06 stay Pending
against Phase 14 **deliberately**, because re-pointing them at 16 would erase
which phase built the pages this one replaces.

**The coverage sentence was counted, not remembered.** `56 → 68`, verified by
`grep -c "^| [A-Z]*-[0-9.]* | Phase "` before and after, and the sentence now
says it was counted from the table.

**(c) ERGO-03 frozen, then retired.** `docs/surface/examples/ERGO-03-FROZEN.md`
carries scripted output produced by running the shipped `audit_report()` over
the committed fragment directories **before** the module was deleted and before
any example change. `tools/measure_examples.py --check` exited 0 immediately
before the run, so every `after/` fragment matched a live re-measurement at the
moment of freezing.

The record states its date (2026-08-10), its tree SHA (`e7e1729`), that the
baseline was frozen at Phase 15's start, that the greenfield rewrite makes the
comparison meaningless going forward, and that `D-IMPL-94` rules the test
retired rather than re-baselined or deleted. **P-8 is satisfied by scoping
rather than by assertion**: the record marks which figures are scripted output
(the four totals, the per-file table, both fragment counts) and which prose is
narration.

Relocation and removal are reported as separate figures, per ERGO-03's own
wording and `D-12`'s no-combined-figure rule:

| Figure | Before | After | Delta |
|---|---:|---:|---:|
| Mechanical wiring (removed) | 1425 | 134 | −1291 |
| Assertions and prints (relocated) | 737 | 152 | −585 |

**One figure moved since `SURFACE-AUDIT.md` §2.2's 2026-08-05 record and is
stated rather than netted away:** the four headline figures are unchanged, but
the `raw` column rose tree-wide 11735 → **11793** (+58) — lines Phases 15.2,
15.3 and 15.4 added, none of them the mechanical boilerplate Criterion 1 set out
to remove.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] The `serve()` "no branch" claim was corrected before it was
recorded**
- **Found during:** Task 1, reading `src/ccf/replay/serve.py` as `<read_first>`
  instructs.
- **Issue:** the plan's `<interfaces>` block and `16-RESEARCH.md` §D.4 both state
  `serve()` "contains no rendering, no transformation of the product payload,
  and no branch." The third clause is false at HEAD: three `QueryPinMismatch`
  refusals branch before any store write.
- **Fix:** the entry states the accurate and load-bearing version instead — one
  return path, reached only through the replay append, with the guard branches
  named as pre-write refusals. The argument against a packaging stage inside
  `serve()` is unaffected and is arguably sharper for being exact.
- **Files modified:** `docs/DECISIONS.md`
- **Commit:** `e7e1729`

**2. [Rule 1 — Bug] Two `docs/SURFACE-AUDIT.md` citations would have gone red on
the deletion**
- **Found during:** Task 2, before deleting the module.
- **Issue:** `docs/SURFACE-AUDIT.md` is **not** in `tools/lints/citations.py`'s
  `HISTORICAL_RECORDS`, so it is gated. Its §2 Sources paragraph carried
  `tests/examples/test_surface_audit.py::audit_report()` — a `cite03-node-id`
  citation that resolves to nothing once the module is gone. §2.1 additionally
  claimed the check pins the numbers in the present tense.
- **Fix:** both moved to the past tense and forward to §2.5 and the frozen
  record, rather than being deleted — so the record of how the §2.2 table was
  produced survives its producer.
- **Files modified:** `docs/SURFACE-AUDIT.md`
- **Commit:** `2c52b5f`

**3. [Rule 1 — Bug] `tools/measure_examples.py`'s two pointers at the deleted
module became false**
- **Found during:** Task 2, sweeping for references before the deletion.
- **Issue:** the module docstring and the `AFTER_DIR` comment both describe the
  retired audit module in the present tense. The tool stays live —
  `make measure-examples` is a real target — so a live tool would have shipped
  false prose.
- **Fix:** both corrected to the past tense and pointed at
  `docs/surface/examples/ERGO-03-FROZEN.md`, with a short docstring section
  recording that the audit module retired and this tool did not.
- **Out-of-scope note:** `tools/measure_examples.py` is not in Task 2's
  `<files>` list. It is fixed here because the deletion in this commit is what
  falsified it, and because `tools/` is outside criterion 10's `src/ runtime/`
  scope so nothing is at risk. `git diff --stat -- src/ runtime/` is empty.
- **Files modified:** `tools/measure_examples.py`
- **Commit:** `2c52b5f`

### House-form departure, recorded rather than silently taken

The plan's `<read_first>` describes Shape B as carrying a `---` separator. **No
entry in `docs/DECISIONS.md`'s tail uses one** — `D-IMPL-91` through
`D-GATE-15.4 (addendum correction)` are separated by blank lines only, and the
last `^---$` in the file is at line 197. `D-IMPL-94` matches the tree rather
than the plan text, on the same principle the plan states for `serve()`: the
house form is what the file does. No acceptance criterion required the
separator.

### Deferred (logged, not fixed)

`.planning/phases/16-.../deferred-items.md` was created and carries two entries,
both discovered by the deletion:

1. **Two `tests/products/` docstrings** cross-reference the retired module as a
   live exemplar. Neither is a lint-visible *citation* (bare backticked paths,
   no `:NNN` or `::symbol`), so nothing is red — `tools.lints --all` exits 0
   with the module gone. Left for plans **16-15** and **16-18**, which already
   have those exact modules open; editing them from a wave-1 worktree would
   collide for no benefit. Both are docstring prose, so neither is touched by
   `D-14`'s mechanism carry-forward.
2. **`docs/SURFACE-CHANGES.md` and `docs/surface-changes/15-03-audit-baseline.md`**
   name the module. These are dated per-plan records of what plan 15-03 built;
   correcting them would falsify the record. Left for the stale-prose gate
   `DOCS-17` commissions, which has to decide the general rule.

## Verification

| Check | Result |
|---|---|
| `python -m tools.lints --all` | exit **0** (green at base and after both tasks) |
| `pytest tools/lints/tests -q` | **400 passed** |
| `pytest tests -q -m "not postgres and not chroma and not neo4j and not mongo and not fluree"` | **2378 passed, 2 skipped** — no collection error from the deleted module |
| `tools/measure_examples.py --check` | exit **0** before the freeze and after the deletion |
| `git diff --stat -- src/ runtime/` | **empty** across the whole plan |
| `grep -c "^\*\*D-IMPL-94 —" docs/DECISIONS.md` | **1** |
| all seven bold sub-headers + both limb headers present, in order | **yes** |
| four D-14 residuals named by id | R4-WR-03, R5-WR-01, augmented-assignment, attribute/subscript |
| limb-1 constants named with their two modules | `MINIMUM_GATE_CALL_SITES`, `MINIMUM_PROJECTING_BODIES`, `MINIMUM_RESOLVED_BINDER_SITES`, `MINIMUM_IMPLEMENTATIONS` |
| limb-2 preservation requirement present (not only the permission) | **yes** — "the retired assertion's measurement must be preserved in the module" |
| D-13 exception names exactly one symbol in one file | `ProductClassDeclaration` in `src/ccf/controlplane/artifacts.py` |
| no fenced code block in the `D-IMPL-94` entry | **0** |
| DOCS rows minted | **12** |
| `| DOCS-NN | Phase 16 | Pending |` traceability rows | **12** |
| traceability table row count | **68**, matching the coverage sentence |
| DEMO/EXAM rows carrying a re-homing note | **8 of 8** |
| `docs/surface/examples/ERGO-03-FROZEN.md` | exists; names `D-15` (×2) and SHA `e7e1729` |
| `tests/examples/test_surface_audit.py` | **gone** |
| `docs/SURFACE-AUDIT.md` retirement note citing `D-IMPL-94` | **yes** (§2.5) |

### Facts re-measured against the tree rather than inherited

- `D-IMPL-93` is the highest existing id — `D-IMPL-94` is genuinely free.
- `test_no_docstring_reproduces_whitepaper_body_text` fails with **20 shingle
  hits** against `ProductClassDeclaration`, and every other docstring is clean.
- `examples/03-harness-portability/run.py:694` carries the **only**
  `required=True` under `examples/` (the `add_argument` call node starts at
  `:693`, which is what the test's docstring cites).
- The four limb-1 constants read 9, 11, 11 and 9 in the tree today.
- `BackendRegistration` carries exactly the five fields Q-7's disposition names,
  and `BACKEND_ENTRY_POINT_GROUP == "ccf.graph_backends"`.

### Pre-existing failures, untouched and correctly out of scope

`pytest tools/docs_tests tools/publish_scan_tests` → **3 failed, 53 passed**.
All three are the pre-existing failures `16-RESEARCH.md` R-2 names and `DOCS-08`
owns: the docstring shingle leak (plan 16-04, authorised by `D-13`) and two
`test_snippet_gate.py` failures whose `SECTION = "ontology"` marker no longer
exists in `examples/00-quickstart/run.py` (plan 16-02 repoints
`SNIPPET_SOURCE`/`SECTION`). None was introduced here and none was papered over.

## Threat Model Disposition

| Threat | Disposition | How it was met |
|---|---|---|
| T-16-01-01 — whitepaper body text in `D-IMPL-94` | mitigated | §7.6 cited by number and title only; no body text, so the sentence survives being copied into `public/` |
| T-16-01-02 — repudiation via ERGO-03's retired test | mitigated | scripted output captured at SHA `e7e1729` **before** deletion; retirement carries a rationale in two places; ERGO-03 stays Complete |
| T-16-01-03 — criterion-10 carve-out widening | mitigated | one symbol, one file, stated as a literal enumeration and explicitly "not a category"; 16-19 enforces mechanically |
| T-16-01-SC — package installs | accepted | this plan installed nothing |

## Self-Check: PASSED

- `docs/DECISIONS.md` — FOUND, carries `D-IMPL-94`
- `.planning/REQUIREMENTS.md` — FOUND, carries `DOCS-18`
- `docs/surface/examples/ERGO-03-FROZEN.md` — FOUND, carries `D-15`
- `docs/SURFACE-AUDIT.md` — FOUND, carries `D-IMPL-94`
- `tests/examples/test_surface_audit.py` — correctly ABSENT
- commit `e7e1729` — FOUND
- commit `2c52b5f` — FOUND

## Task 3 — checkpoint cleared (2026-08-10)

Task 3 (`checkpoint:human-verify`, `gate="blocking"`) was put to Dave by the
orchestrator, not self-approved, and **approved as recorded**. All six
dispositions stand unchanged: the Q-2 substrate reading of `assembly_mode`; the
criterion-10 carve-out as one literal symbol/file pair; Q-7 left unruled with
`DI-15.4-05`/`DI-15.4-06` kept out of the published page; Q-8's three gate
suites joining `make ci`; `D-14`'s carry-forward bounded on both limbs; and the
twelve DOCS rows with the eight DEMO/EXAM re-homings.

**Orchestrator verification before presenting.** Three load-bearing claims in
the entry were re-checked against the tree rather than taken from the executor:
`serve.py` has three `QueryPinMismatch` guards and exactly one `return` (so the
plan's "no branch" wording was wrong and the entry's stronger claim is right);
`required=True` has exactly one witness under `examples/`
(`03-harness-portability/run.py:694`, n=1, as limb 2 asserts); and
`test_docstring_leaks.py` reports exactly 20 shingle hits on
`ProductClassDeclaration` with every other docstring clean.

**Post-merge suite:** 2423 passed, 81 skipped, exit 0. The 34-test drop from the
Phase 15.4 baseline of 2457 is exactly the retired `test_surface_audit.py`,
which collected 34. Nothing else regressed.

**Deviation accepted by Dave.** `tools/measure_examples.py` is not in this
plan's `files_modified` (it belongs to 16-18) but received a docstring-only
correction, because its prose described the deleted audit module in the present
tense. Two further stale cross-references in `tests/products/` were logged to
`deferred-items.md` rather than fixed, since those modules belong to plans 16-15
and 16-18 and editing them from a wave-1 worktree would collide at waves 8/11.
