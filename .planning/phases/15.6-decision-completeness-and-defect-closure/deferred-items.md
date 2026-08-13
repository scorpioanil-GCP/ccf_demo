# Phase 15.6 — deferred items

Out-of-scope discoveries logged rather than fixed, per the executor scope
boundary (only issues *directly caused by* a task's own changes are auto-fixed).

---

## Dispositions at phase close (plan `15.6-12` task 4, 2026-08-13)

Every entry has one. **None is carried into Phase 16 without a stated owner** —
Dave's requirement at the `D-GATE-15.6` gate, applied to every row below
including the ones he ruled on directly.

| Entry | Disposition | Owner |
|---|---|---|
| `DI-15.6-01` (a) — four inherited `tools/` failures | **ACCEPTED AS INHERITED**, verified identical at `9905e8f`. Known residual, **not** a 15.6 defect (Dave, 2026-08-13) | Phase 16 |
| `DI-15.6-01` (b) — the two scanners disagree about the same tree | **OPEN — a real coverage hole, not a false positive on either side** (Dave, 2026-08-13). Required follow-up stated below | Phase 16 |
| `DI-15.6-02` — the citation ratchet's floors sit outside `COUNT_COUPLING_TREES` | **OPEN — recorded disposition, no ruling sought.** Accepted as stated (Dave, 2026-08-13) | Phase 16, jointly with `DI-15.6-01` (same report regeneration) |
| `DI-15.6-03` — the retired spike's reproduction break | **RECORDED, document deliberately NOT edited** (Dave, 2026-08-13). Dated note below, verbatim | closed by this entry; no further work |
| `DI-15.6-04` — `D-IMPL-99`'s two remaining rotted anchors | **LEFT IN PLACE as known residual** (Dave, 2026-08-13). The shipped ruling is not edited | carried under `D-IMPL-99`; any repair is Dave's |
| `DI-15.6-05` — narrowing the `ccf.` reservation | **FUTURE ITEM — do NOT narrow this phase** (Dave, 2026-08-13). Must budget the address moves | unassigned until a concrete harm appears; opening it is Dave's |
| `DI-15.6-06` — `test_task_factory_construct` straddles its band | **OBSERVED at the gate re-baseline, deliberately NOT re-baselined** | the next PERF-04 event, which is Dave's under `D-IMPL-70` |
| Shape B zero-span residual (panel advisory A1) | **NO TIGHTENING THIS PHASE** (Dave, 2026-08-13): *"a measurement edge case, not a new oracle. Leave it; revisit only if a concrete consumer is harmed"* | revisit trigger only; no standing owner |
| Deferred-cache view retention (panel advisory A2) | **CORRECTED DELTA ACCEPTED; no remeasurement for gate close** (Dave, 2026-08-13). The negative result — identical hashes, hits and apply counts — already established safety | the next PERF-04 event |
| `CanonicalizationError` surfacing later (panel advisory A3) | **NO ACTION** — already recorded in `docs/surface-changes/15.6-02-intermediate-cache-key.md` in almost the same words; the panel rediscovered a documented narrowing | none |
| Citation ratchet floors inherit the coupling-tree hazard (panel advisory A4) | **Already open** as `DI-15.6-02` | as `DI-15.6-02` |
| Docstring cross-reference drift in `src/ccf/graph/backends/fluree.py` (panel advisory A5) | **CLEANUP-GRADE**, noted against the `15.6-11` sweep; not fixed, not blocking | Phase 16, with the `DI-15.6-01` report pass |
| The five recorded dispositions in `docs/15.6-GATE-PACKAGE.md` § 6 | **ACCEPTED AS STATED** (Dave, 2026-08-13): *"No ruling sought; no objection."* | each names its own owner in the entry below |

**Carried into Phase 16:** `DI-15.6-01` (a) and (b), `DI-15.6-02`, advisory A5,
and disposition 4 below (`DI-15.5-06` is narrowed, not closed). Everything else
is either closed, ruled to stay, or has no standing owner by ruling.

---

## DI-15.6-01 — four `tools/` gates are red, and were red before this phase touched them

- **Found during:** plan `15.6-09`, task 3, running
  `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/ -q`
  as that task's own verification step. A fourth failure joined the record
  later, from a different sub-package.
- **Established as pre-existing by measurement, not by assumption.** A
  throwaway detached worktree was created at plan `15.6-09`'s base commit
  `4b407e0`, the same command was run there, and it produced **the identical
  three failures** — `3 failed, 83 passed`. The worktree was removed
  afterwards. The full four-failure set was then verified **identical at
  `9905e8f`**, this phase's base, before Dave ruled on it.
- **Observed again at the gate HEAD** (2026-08-13):
  `PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/ -q` →
  **4 failed, 540 passed**, the same four, with the same shingle counts.
- **The four:**

  | Failing test | What it reports |
  |---|---|
  | `tools/docs_tests/test_documented_commands_exist.py::test_every_composed_example_target_is_documented` | `example-s1-01` runs in CI but no published page under `public/` names it — *"maintained, tested, and unfindable"* |
  | `tools/docs_tests/test_documented_commands_exist.py::test_the_gate_refuses_an_undocumented_composed_example` | the same gate's own control, failing for the same reason |
  | `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` | `docs/surface/examples/RETIREMENT-COUPLINGS.md` is stale — committed at **163 rows across 47 files**, the sweep now measures **181 across 52** |
  | `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` | five `src/` files reproduce whitepaper body text: `binder.py` 7 shingle hits, `assessment.py` 15, `debt.py` 14, `composition.py` 3, `request.py` 1 |

- **Why it went unnoticed.** `pyproject.toml` sets `testpaths = ["tests"]`, so
  the whole `tools/` package does **not** run under `make ci-core`. It runs in
  CI as its own step. A plan that verifies with `make ci-core` alone will
  report green over a red package, which is one of the two process findings
  already carried from the 15.1 close and is the reason plan `15.6-09` ran it
  explicitly and separately.

### (a) The four failures themselves — Dave's ruling, 2026-08-13

> *"Accept as inherited (verified identical at `9905e8f`). They predate the
> phase and were not caused by it. Record them as known residual; do not treat
> them as 15.6 defects."*

- **Disposition:** ACCEPTED AS INHERITED. Known residual. Not 15.6 defects.
- **Owner:** **Phase 16.** Named because Phase 16 owns both halves of the fix:
  `public/` authoring, which the first two failures want, and the example
  retirement schedule, which is what moved the retirement report the third
  reports as stale. Assigned in this record at the gate, under Dave's standing
  requirement that nothing is carried without a named owner.

### (b) The governance question underneath them — *"the real issue"*

Dave: *"Treat the disagreement as a real coverage hole, not a false positive on
either side."*

**Two scanners disagree about the same tree.** `docs-strict` passes —
plan `15.6-03`'s `docs/schemas/` scan root reports **0 findings over 26
files** — while `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text`
finds five `src/` files reproducing whitepaper prose. The mechanism that lets
both be true at once is that `tools/dump_schemas.py::emit` copies docstrings
**verbatim** into schema `description` fields: the same text is a docstring to
one scanner and a schema description to the other, and only one of the two is
inside the gate that blocks.

**The positive result, which Dave asked be kept.** *"The positive result
(Track B's heavy docstring work did not move shingle counts) is worth
keeping."* `src/ccf/halflife/assessment.py` and `src/ccf/halflife/debt.py` are
the two modules Track B rewrote most heavily across four waves, adding many
docstrings — and their shingle counts (15 and 14) **did not move at all**
between `9905e8f` and the gate HEAD.

**Required follow-up, in Dave's words:**

> *"either extend the D-20 / docs-strict surface to cover the schema-description
> channel, or make `test_docstring_leaks` (or an equivalent) part of the
> required CI surface so the two scanners cannot silently diverge. Leaving
> `tools/` outside `testpaths` is the mechanism that allowed the inherited
> failures to persist; **that should be named explicitly**."*

**Named explicitly, as required:** the mechanism is `testpaths = ["tests"]` in
`pyproject.toml`. It is what keeps every test under `tools/` — including both
scanners' own tests — out of `make ci-core`, and it is why a red package
survived at least one phase boundary while every plan in that phase reported a
green gate.

- **Disposition:** OPEN. A real coverage hole. One of the two remedies above is
  required; picking which is inside the follow-up, not a new ruling.
- **Owner:** **Phase 16**, same assignment and same reason as (a). To be
  discharged before Phase 16 closes, since Phase 16 is the phase that rewrites
  the published surface both scanners guard.

---

## `DI-15.6-02` — the citation ratchet's two floors are outside `COUNT_COUPLING_TREES`

- **Raised by:** plan `15.6-11` (the citation sweep and its ratchet), 2026-08-12.
- **What.** `tests/invariants/test_citation_coverage.py` carries two
  `MINIMUM_*` floors — `tests/invariants/test_citation_coverage.py::MINIMUM_SCANNED_CITATION_HOSTS`
  (954) and `tests/invariants/test_citation_coverage.py::MINIMUM_CITATIONS_READ`
  (797). Both are shaped so `tools/retirement_sweep.py::_floors` recognises them,
  and **it does**: run against the module it reports both, each paired with the
  scan function feeding it, and `count_coupling_rows(roots=[tests/invariants])`
  emits **four live rows** owned by `16-18`. What the sweep's *default* walk does
  not reach is the tree: `tools/retirement_sweep.py::COUNT_COUPLING_TREES` is
  `("tests/products",)`.
- **The coupling those four rows report, which is real and is why this is
  recorded rather than dropped.** Both scans walk `examples/`, so
  `MINIMUM_SCANNED_CITATION_HOSTS` has **headroom 0** and **first breaks at
  wave 8**, when `16-15` retires `examples/03-harness-portability` (27 hosts).
  `MINIMUM_CITATIONS_READ` has headroom 6 against
  `tests/examples/test_ext00_serve_output.py`.
- **Why plan `15.6-11` did not widen it.** Widening is one line of data — the
  sweep's own docstring invites exactly that (*"Data, so a later plan widens
  the search without editing the detector"*) — but it changes
  `docs/surface/examples/RETIREMENT-COUPLINGS.md`, which
  `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
  already reports **stale at this phase's base** under `DI-15.6-01`.
  Regenerating it inside that plan would silently discharge a deferred item
  owned elsewhere and fold an 18-row pre-existing drift into a citation-sweep
  commit.
- **What closing it costs.** Add `"tests/invariants"` to `COUNT_COUPLING_TREES`,
  re-run `python tools/retirement_sweep.py --report`, commit the regenerated
  report. Measured: **4 new rows, all owned by `16-18` from the schedule**, so
  `test_the_committed_report_carries_no_unowned_row` stays green.
- **Disposition at close:** OPEN. Recorded to Dave in `docs/15.6-GATE-PACKAGE.md`
  § 6 as a disposition with no ruling sought; accepted as stated, 2026-08-13.
- **Owner:** **Phase 16**, jointly with `DI-15.6-01`, since both want the same
  report regenerated in the same commit.

---

## `DI-15.6-03` — the retired spike's reproduction instruction now points at nothing

- **Raised by:** plan `15.6-12` task 1, 2026-08-12, on retiring
  `tests/spikes/test_debt_evidence_placement_cost.py` under plan `15.6-01`'s own
  retiring-owner clause. Three of its four measured placements became
  counterfactual once `qa-toplevel` was ruled.
- **The break.** Plan `15.6-01` kept the instrument in-tree specifically *"so a
  later reader can re-run them"*, and `docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md`
  still instructs a reader to run it.
- **Dave's ruling, 2026-08-13 — record the break, do NOT edit the protected
  document.** *"Leave the evidence document untouched."*

**Dave's dated note, verbatim (2026-08-13):**

> "The reproduction command at line 389 refers to a spike retired in 15.6-01;
> the recorded figures remain the authoritative result. Re-running is no longer
> possible."

**And his framing, verbatim:**

> "Retirement converts 'here is how to reproduce this' into 'trust the recorded
> figure.' That conversion is now explicit rather than silent."

- **Disposition:** RECORDED, and closed by the recording. The evidence document
  is not edited — editing it falsifies the record the rulings were made against,
  which is the reason every wave of this phase was forbidden to touch it.
- **Owner:** none required; the note above and its twin in
  `docs/15.6-GATE-PACKAGE.md` are the whole remedy.

---

## `DI-15.6-04` — `D-IMPL-99`'s two remaining rotted line anchors

- **Raised by:** plan `15.6-11`, which repaired **one** anchor in `D-IMPL-99`
  under a narrow authorization and **deliberately left two**, because the
  authorization named one.
- **What is rotted.** The line ranges `D-IMPL-99` cites for
  `src/ccf/halflife/assessment.py::DebtAssessment`'s field list and for
  `src/ccf/halflife/debt.py::FreshnessScorer`'s scoring method. The stale ranges
  themselves are **not reproduced here**: this file is inside the scan root of
  the ceiling plan `15.6-11` shipped
  (`tests/invariants/test_citation_coverage.py::MAXIMUM_UNANCHORED_PY_CITATIONS`,
  now 0), and quoting a line-anchored citation in order to complain about
  line-anchored citations is exactly how the population regrows. It is also not
  reachable by the checker in the ruling's own file: `docs/DECISIONS.md` is a
  `HISTORICAL_RECORDS` exemption in `tools/lints/citations.py`, because a record
  whose discipline forbids editing an entry cannot be gated on citation
  freshness.
- **Dave's ruling, 2026-08-13:** *"Do not edit the shipped ruling. Carry the two
  rotted anchors forward as known residual under `D-IMPL-99`, with the same
  discipline used for other deliberately-left drift this phase."*
- **Disposition:** KNOWN RESIDUAL, left in place by ruling. Same discipline as
  the three deliberately-stale citations `D-GATE-15.5` recorded.
- **Owner:** carried under `D-IMPL-99` itself. Any repair is a Dave
  authorization, as the one repaired anchor was.

---

## `DI-15.6-05` — narrowing the `ccf.` reservation is a ruling with address-move consequences

- **Raised by:** the single-agent review's WR-01 residual, 2026-08-13. The
  `ccf.` namespace reservation shipped by the close-panel B1 fix false-positives
  on domain-shaped identifiers (`ccf.example.com/entity/42`) and does not fold
  script confusables — a Cyrillic-es `сcf.` is accepted, with a test pinning
  that limit so it cannot drift silently.
- **Dave's ruling, 2026-08-13 — DO NOT narrow this phase.** *"Narrowing changes
  sentinel values that already sit inside shipped content addresses. That is a
  ruling with address-move consequences, not a repair. If confusables or
  `ccf.example.com/…` false positives become painful, open a future item that
  explicitly budgets the address moves."*
- **Disposition:** FUTURE ITEM, explicitly not this phase. Any future item
  opened against it must budget the content-address moves it causes — this
  phase moved the product address four times and each move regenerated an
  artifact, so the cost is known rather than speculative.
- **Owner:** unassigned by ruling; the trigger is a concrete harm, and opening
  the item is Dave's.

---

## `DI-15.6-06` — a third micro benchmark straddles its band

- **Found during:** plan `15.6-12` task 4, 2026-08-13, running the four-run
  `make perf-micro CCF_PERF_RUNNER_CLASS=local` battery for the Dave-approved
  re-baseline.
- **What.** `suites/micro/test_factory.py::test_task_factory_construct` reports
  a speed-up of **10.1%, 10.5%, 9.8% (PASS) and 10.3%** across four consecutive
  runs on a quiet machine — it crosses and re-crosses the `[suite.micro]`
  default of 10% with no code change between runs. That is the same *shape* as
  `DI-15.5-01`'s dispatch benchmark: variance comparable to the band, not a
  regression. It is on the speed-up side, so it warns and never fails.
- **Why it was not re-baselined.** Dave's PERF-04 approval at this gate names
  **two** ids — `test_composed_chain` and `test_composed_ab` — and a third is
  its own PERF-04 event under `D-IMPL-70`, not an executor's extension of an
  approval. `perf/baselines/local.json` therefore still carries this
  benchmark's 2026-08-03 approved median, unchanged.
- **Disposition:** OPEN, observed and recorded rather than acted on.
- **Owner:** the next PERF-04 re-baseline event, which is **Dave's** under
  `D-IMPL-70` — the same owner class that authorized the two ids revised here.

---

## The five recorded dispositions — accepted as stated (Dave, 2026-08-13)

Put to Dave in `docs/15.6-GATE-PACKAGE.md` § 6 with no ruling sought. His
answer, verbatim: *"Accepted as stated. No ruling sought; no objection."*

| # | Disposition | Standing owner |
|---|---|---|
| 1 | `DI-15.6-02` — the citation ratchet's floors sit outside `COUNT_COUPLING_TREES` | Phase 16 (see the entry above) |
| 2 | `docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md` shows as unclassified in the census sweep. It is not a pin site and must not be regenerated; **the classification is the defect, not the document** | Phase 16, with the `DI-15.6-01` report pass |
| 3 | **Shape B moved a check from the SDK to the adopter.** Deleting the per-source map removed the SDK's duplicate-reference refusal, because the SDK can no longer see the set. The refusal now lives in the deployment's parse step — the last party able to notice, since `min`/`max` would absorb a duplicate silently | the adopter, by construction under `D-IMPL-124`; no SDK owner |
| 4 | **`DI-15.5-06` is narrowed, not closed** (`D-IMPL-122`). 39 multi-method Protocols remain information-free, including all seven `D-IMPL-110` names. The manifest still must not be cited as evidence of surface stability for them. Recorded in three places | carried forward; Phase 16 must not cite the manifest as stability evidence for those names |
| 5 | **`debt_evidence` ships as a paid-for carrier holding a sentinel and no pointers.** The phase paid `qa-toplevel`'s full replay cost — a dimension-5 member plus 7 rehydrator edits — for a field that is currently empty. That is `D-IMPL-118` and `D-IMPL-119` limb 3(b) working **as intended together**, not a defect: the carrier and its replay plumbing exist, so a later phase that adds principal scoping fills a slot rather than rebuilding one | a later phase that makes the assembly path principal-scoped, per `D-IMPL-119` |
