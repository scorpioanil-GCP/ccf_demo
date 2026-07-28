---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 22
subsystem: docs-claims-reconciliation
tags: [gap-closure, claim-narrowing, D-IMPL-57, D-IMPL-58, D-IMPL-59, D-21, B1, B2, B3, A1, A2, A4, A5]
requires:
  - 06-18 (GATE_LINEAGE_ATTRIBUTABILITY, the federated gate sequence)
  - 06-19 (AdmissionRecord, the replay resolution path, closure item 6's verbatim sentence)
  - 06-20 (adversarial harness legs; the capture_effect-delegation limit, verbatim)
  - 06-21 (row 6 replacement wording; row 3 eligible to strengthen)
  - 06-24 (the Peering rename — the old paths this plan had to correct)
  - 06-25 (the skill surface, the retired token, version-bump scoping)
provides:
  - docs/PHASE_I3_GATE.md rows and criterion prose matching the code after the wave
  - gate §3.2.1 (what the Peering re-description changed and did not)
  - gate §3.3.1 (what the portability evidence proves and does not)
  - gate §4.13 (citation-resolution sweep, generalizing A4)
  - 06-REVIEWS.md 10-row disposition table
affects:
  - 06-23 (re-presentation: every row this plan rewrote is a row 06-23 re-verifies)
tech-stack:
  added: []
  patterns:
    - "every narrowing carries `(closes <finding>)` inline, so the weaker sentence is traceable to the finding that weakened it"
    - "a retired over-claim is paraphrased, never reproduced verbatim, so it cannot be recovered by copy-paste"
    - "citation integrity as a mechanical sweep rather than as reviewer attention"
key-files:
  created: []
  modified:
    - docs/PHASE_I3_GATE.md
    - .planning/ROADMAP.md
    - .planning/phases/06-phase-i-3-cross-process-harness-adapters/06-REVIEWS.md
decisions:
  - "A4 raised §1.1's count from two gate-evidence integrity findings to three rather than being absorbed quietly"
  - "The retired row-6 phrasing is paraphrased, not quoted, resolving the tension between visible narrowing and the `== 0` criterion — 06-21's precedent"
  - "The new B1 row is numbered 21 and appended after row 20 rather than inserted mid-table"
  - "A3 is written as OPEN in three places (gate §3.3.1, gate §5, disposition table); nothing claims it closed"
metrics:
  duration: ~55m
  completed: 2026-07-27
  tasks: 3
  files: 3
requirements: [XPRC-01, XPRC-02, XPRC-03]
---

# Phase 06 Plan 22: Claim narrowing, traceable per finding — Summary

Every documented claim in `docs/PHASE_I3_GATE.md` and ROADMAP Phase 6 now matches
what the suite actually holds after the gap-closure wave, and **every narrowing is
visible in the document itself** — carrying the finding id that forced it, and the
cost the narrowing accepted.

## Verification path

Per the orchestrator's finding 1, and confirmed before anything was trusted: there is
no `.venv` in this worktree and **both** `ccf` and `ccf_runtime` are installed editable
against the main repo, so a bare invocation verifies the wrong tree. Every run used
`PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python`.

The declared-base reset **fired**, exactly as the orchestrator predicted: the worktree
spawned at merge-base `ba0088e` and was reset to `c2e0337`. Post-reset sanity check
passed before any work began — `src/ccf/peering/` present, `src/ccf/a2a/` absent, all
six gap-closure SUMMARYs (06-18/19/20/21/24/25) present.

## Results

| Check | Result |
|---|---|
| `pytest -q` baseline, before any edit | 987 passed, 2 skipped |
| `CCF_REQUIRE_HARNESSES=1 pytest -q` final | **987 passed, 2 skipped** — docs-only change, no regression |
| `mypy` | Success, 99 source files |
| `tools.lints --all` | exit 0 |
| `pytest tools/lints/tests -q` (A4's corrected path, run not assumed) | 49 passed |
| `git diff --diff-filter=D --name-only pre-peering -- src/ runtime/ tests/ tools/` | **no output** |
| `git diff --name-only CLAUDE.md` | **empty** — not edited |
| `git diff --name-only .planning/STATE.md` | **empty** — untouched |
| `git diff --name-only docs/DECISIONS.md` | **empty** — untouched |

## What Was Written

### Task 1 — the two blocking over-claims, plus B2 and the vocabulary (`db54701`)

**B1.** New **gate row 21**: the federated sequence checks *attribution, not
verification* — INV-CH7-47 is verifiable within a fabric and attributable across one.
What admission establishes is that the declared operator plan is covered by a signature
from a key the peer was entitled to use, and is therefore non-repudiable — **not that
the plan was run**. Dave's accepted consequence is carried across in his own words:
*a compromised or buggy peer can assert an operator plan it did not run, and the
consuming fabric will admit the product.* The row cites 06-18's tests, including the
end-to-end case driven through `admit` with signature verification asserted to have
*succeeded* first, and 06-18's measured counterfactual (old wiring → 3 of 6 fail).
ROADMAP criterion 2 states the same narrowing.

**B2.** **Row 14** rewritten to 06-19's sentence: lineage continuity is a property of
the Peering admission boundary, persisted as an immutable `AdmissionRecord` and
resolvable at an exact version — *not* a property of graph state, with `LineageEntry`
untouched. Its evidence cell cites the **persisted-state** test
(`::test_the_union_is_observed_in_persisted_state_through_the_replay_path`), not the
wrapper-level one, and its failure column names what B2 actually found: before 06-19
the union was a property of an object L2 discards.

**B3.** New **§3.3.1**, and the §3.3 row label changed from *"Portability demonstrated,
not asserted"* to *"Seam-level portability demonstrated at four seams; loop-level
portability outstanding"*. §3.3.1 states what the evidence proves, what it does not
(no harness loop runs; `_drive` calls the four seams directly), and carries 06-20's
limit verbatim — see below. Loop-level execution is **handed to `examples/03-harness-portability`
in Phase 8** rather than deleted. `CLAUDE.md` §7.3 is deliberately **not** edited; the
gate records the obligation as outstanding and makes no §6 amendment request.

**D-IMPL-59 vocabulary.** §3.2 retitled to *"XPRC-02 — Peering federation (A2A is the
reference transport, not the concept)"*, with a vocabulary preamble stating part 3 (MCP
is outside the seam: asymmetric, originates lineage rather than merging it). New
**§3.2.1** records what the re-description changed and what it deliberately did not —
no code deleted (checked against the `pre-peering` tag), A2A not withdrawn, transports
keeping their protocol names, `AdmittedProduct`/`ingest_admitted` already
transport-neutral. Part 4 is stated as a **verified property** citing
`tests/peering/test_peering_verdict.py` and 06-24's neutering counterfactual.

### Task 2 — the documentation-accuracy advisories (`fa3c98a`)

- **A4** — row 1 now cites `tools/lints/tests/test_harness_imports.py` and names its
  four boundary tests, verified by running them. **§1.1's heading went from "Two" to
  "Three" gate-evidence integrity findings**: a gate document that quietly absorbs a
  third instance of its own named defect class commits that defect a fourth time.
- **A2** — row 6 is now *"a type error on every unforced path"*, with the evidence cell
  naming that `_ADMISSION_TOKEN` is importable so forging requires naming a private
  member, and that both edges are asserted.
- **A1** — row 3 **strengthened** (traceable to 06-21, not invented): every transport
  `ccf_runtime.peering` ships is constructed and attribute-scanned, `LfA2AWire`
  included, discovered structurally with `TRANSPORT_BUILDERS` keyed by class, and the
  second count guard named with 06-21's measured failure message.
- **A5** — ROADMAP criterion 1 names the edges I.3 delivers and records the Experience
  MCP edge as Phase 7 scope. The gate's §3.1 deferral note — which said the criterion
  *"stands as written and is not amended"* — is itself amended, since that sentence was
  the gap.
- **New §4.13** generalizes A4 into a mechanical sweep (below).

### Task 3 — a disposition for every finding, carried ones included (`942dc7e`)

`06-REVIEWS.md` gains a **10-row disposition table** (B1, B2, B3, A1–A7). Its evidence
column spans **06-18 through 06-25**, because D-IMPL-59 named the structural cause
behind B1/B2/A2 while earlier plans closed the symptoms — a table stopping at 06-22
would omit the plans that closed the cause. Counts: 3 blocking all closed in-phase;
7 advisory — 4 closed, 3 carried **with consequences**:

| Carried | Target | Consequence stated |
|---|---|---|
| **A3** | Phase 8, example 03 | one of three seam-4 legs is a fixture echo, so trace-equivalence evidence is **two-legged in substance** |
| **A6** | `D-IMPL-56`, from Phase 7 | every future adapter re-derives description/schema; the first to derive them differently **silently breaks D-18 harness equivalence** |
| **A7** | Phase 7, against D-IMPL-17 | the one place the SDK authors execution shape; I.4 must not inherit `_build_graph` as a workflow engine |

Gate **§5** gains prerequisite-framed entries for A3 and A7 and names D-IMPL-56 as A6's
carry-forward target (cross-referenced, not restated). The closing Disposition paragraph
records that the wave **grew mid-flight** when D-IMPL-58 and D-IMPL-59 landed, that
`D-GATE-I.3` remains unlogged, and that the phase is re-presented to Dave by 06-23.

## The two verbatim hand-offs, honoured

**06-20's structural-triviality sentence, in the gate document (§3.3.1) and here:**

> **All three shipped adapters' `capture_effect` remain delegations to
> `Agent.emit_effect`, so the honest three-leg emission equality still cannot fail. The
> adversarial leg proves the assertion is sensitive to perturbation, not that the three
> adapters are independent implementations.**

**06-19's closure item 6 sentence,** now row 14's claim and ROADMAP criterion 2's:
lineage continuity is a property of the Peering admission boundary, persisted as an
immutable `AdmissionRecord` and resolvable at an exact version.

**A3 is written as OPEN in three places** — gate §3.3.1, gate §5, and the disposition
table. Nothing in this plan claims it closed.

## ROADMAP: exactly which lines changed (boundary check)

Per `<shared_artifact_ownership>`. Only claim/criteria **prose** was touched:

| Lines | What |
|---|---|
| 237 | criterion 1 — edges I.3 delivers; Experience MCP edge as Phase 7 scope (A5) |
| 238 | criterion 2 — Peering/`PeeringProtocol`; B1 and B2 narrowings |
| 239 | criterion 3 — B3 narrowing, loop execution handed to Phase 8 |
| 251–258 | criterion-evidence bullet 2 |
| 259–265 | criterion-evidence bullet 3 |

**Not touched, verified by reading the full diff:** line 243 `**Plans:** 23/25 plans
executed`, every plan checkbox (263–328), the Progress table row at line 395, and every
phase status/date field. `.planning/STATE.md` was not opened for writing.

## The `strict equality` enumeration (Task 1 acceptance criterion)

`grep -n "strict equality" docs/PHASE_I3_GATE.md` returns **zero hits**, both before and
after this plan. The enumeration the criterion asks for is therefore **empty** — there is
no remaining hit to justify as describing the local L6 path, and no unclosed B1 hiding in
one. The phrase never appeared in the gate document; B1 lived in the *code* docstring
(06-18 removed it: `grep -c "structurally vacuous"` = 0) and in the **unnarrowed
criterion prose**, which Task 1 rewrote.

## Deviations from Plan

### 1. [Rule 3 — Blocking] Task 2's `<verify>` command would have verified the wrong tree

- **Issue:** the block is `.venv/bin/python -m pytest tools/lints/tests -q`. There is no
  `.venv` here, and the main interpreter resolves both packages to the main repo.
- **Fix:** run as `PYTHONPATH=src:runtime /home/parkave/ccf_code/.venv/bin/python -m
  pytest tools/lints/tests -q` → 49 passed. Same defect the four preceding plans hit.

### 2. [Rule 3 — Blocking] Task 3's criterion `grep -c 'D-GATE-I.3' docs/DECISIONS.md == 0` is false against the inherited tree

- **Found during:** Task 3 verification.
- **Issue:** the count is **1**, and was already 1 at the plan's declared base
  (`git show c2e0337:docs/DECISIONS.md | grep -c` → 1). The hit is a **prose mention
  inside D-IMPL-58's own text** — "Phase I.3 cannot be honestly presented for
  `D-GATE-I.3`" — not a logged gate entry. (`grep` also treats the `.` as a wildcard.)
- **Fix:** the criterion's *intent* was verified instead, three ways: `docs/DECISIONS.md`
  shows **no diff** from this plan; there is **no gate-entry-shaped heading**
  (`grep -cE "^\*?\*?D-GATE-I\.3 —|^#+ .*D-GATE-I\.3"` = 0); and no plan in the wave
  logs it. The literal `== 0` cannot be satisfied without deleting a sentence from a
  decision-log entry, which would be a worse defect than the criterion it satisfies.
  **Nothing was edited to make the plan's literal text true.**

### 3. [Rule 1 — Direct conflict between a criterion and the "make narrowing visible" mandate] Row 6's retired phrasing is paraphrased, not quoted

- **Issue:** Task 2's criterion is `grep -c "a type error, not a discipline" == 0`. But
  the plan's governing mandate is that a narrowing must be *visible* — which invites
  quoting what was replaced. My first draft did quote it, and the count came back 1.
- **Fix:** 06-21's precedent applied — **reword rather than relax the criterion**. Row 6
  now names the retired form descriptively ("previously contrasted a type error against a
  mere discipline with no scope qualifier at all") and states explicitly that the retired
  phrasing is deliberately not reproduced, so the stronger claim cannot be recovered from
  this document by copy-paste. Narrowing stays visible; the string is gone. Count: 0.

### 4. [Interpretation] The new B1 row is numbered 21 and appended after row 20

The plan says "add or amend the gate row that names the federated gate sequence". No such
row existed, so one was added. It was first written immediately after row 14 (its
subject-matter neighbour), which left the table reading 14, 21, 15 — so it was moved to
after row 20. The §2 preamble sentence "**Every row names an existing, passing
`file::function` or lint rule id**" continues to hold, and was checked mechanically (§4.13).

### 5. [Rule 2 — Missing critical coverage] §4.13, the citation-resolution sweep, is not in the plan

A4 was a citation pointing at a directory that **existed and held different tests** — a
defect a reader cannot detect by following the link, because following it succeeds. Fixing
only row 1 leaves the class open. So the correction was generalized into a sweep over the
whole document: **47 backticked paths** (`test -e`) and **63 `file::function` citations**
(resolved to a `def` in the named module), zero unresolved. Four paths flagged and all four
adjudicated in the document: three were extraction artifacts of `ccf_runtime/...` (which
exist) and one — `examples/03-harness-portability` — **deliberately does not exist**, being
the Phase 8 forward reference §3.3.1 hands the loop-level obligation to. Recorded here
because it is scope the plan did not ask for.

### 6. [Informational] One residual named rather than fixed

`tools/lints/tests/test_harness_imports.py::test_a_harness_import_in_the_a2a_module_is_still_flagged`
still carries `a2a` in its **function name** while the module it feeds is
`ccf_runtime.peering.lf_a2a` (06-24 updated the fixture path string, not the label). The
assertion is correct; only the name lags. This plan's `files_modified` is docs-only, and
renaming a test is a code change — so it is **named in gate row 1** rather than silently
left, and is available to 06-23 or a later sweep.

### 7. [Informational] Upstream judgment calls recorded, not re-decided

Per the orchestrator's finding 5: 06-25's version-bump scoping (affected entries only,
major on both lanes) and 06-24's `a2a-*` → `peering-*` gate-id **value** rename are both
flagged in their own SUMMARYs as open to a reviewer preferring otherwise. This plan
**records** the value rename in gate §3.2.1's "changed" list so a reviewer can see it, and
does not re-open either.

## Threat Register Outcomes

| Threat ID | Disposition | Outcome |
|---|---|---|
| T-06-95 (repudiation — a claim narrowed without a trace) | mitigate | every narrowing carries `(closes <finding>)` inline; grep-asserted — `closes B1`/`B2`/`B3` = 2 each in the gate, all four of A1/A2/A4/A5 present across gate + ROADMAP |
| T-06-96 (info disclosure — a citation pointing at a file that does not exist) | mitigate | §4.13 sweep: 47 paths + 63 `file::function` citations, zero unresolved; A4's own correction verified by *running* the tests |
| T-06-97 (tampering — an advisory quietly dropped) | mitigate | 10-row disposition table asserted by count; each carried row asserted to carry a target **and** a consequence clause |

## Known Stubs

None. This plan writes prose; there is no data path to leave unwired.

## Threat Flags

None. No code, no network endpoint, no auth path, no schema change — three documentation
files.

## Out of Scope / Follow-on

- **`CLAUDE.md` §7.3 is untouched by design.** Its "running unmodified under at least two
  harnesses" clause is discharged by the §9 example-03 obligation, which the gate now
  names. Amending §7.3 would be a request in gate §6; none is made.
- **06-23** owns the row-by-row re-verification and the re-presentation. Every row this
  plan rewrote (1, 3, 6, 7, 14, 15, 16, 21) and every new section (§3.2.1, §3.3.1, §4.13)
  is in its scope.
- **`D-GATE-I.3` is not logged**, by design — approval authority is Dave's alone.

## Self-Check: PASSED

- `docs/PHASE_I3_GATE.md` — FOUND (modified)
- `.planning/ROADMAP.md` — FOUND (modified, criteria prose only)
- `.planning/phases/06-phase-i-3-cross-process-harness-adapters/06-REVIEWS.md` — FOUND (modified, 10-row table)
- commits `db54701`, `fa3c98a`, `942dc7e` — all present in `git log`
- `CLAUDE.md`, `.planning/STATE.md`, `docs/DECISIONS.md` — confirmed **no diff**
- no deletions vs `pre-peering` over `src/ runtime/ tests/ tools/` — CONFIRMED
- baseline 987 passed / 2 skipped, mypy 99 files clean, lints exit 0 — CONFIRMED
