---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 21
subsystem: phase-close
tags: [surface-record, audit, governance, standing-gates, review, checkpoint]
requires:
  - tools/dump_surface.py            # 15-01
  - docs/surface/v0.2-surface-baseline.json  # 15-01, frozen
  - tools/measure_examples.py        # 15-03 + the pre-wave-9 orchestrator fix
  - tools/check_schema_headers.py    # 15-12 + the post-wave-11 orchestrator fix
  - tests/examples/test_surface_audit.py::audit_report  # 15-03
  - docs/surface-changes/15-02..15-20  # every plan's fragment
provides:
  - the curated D-15B migration note, assembled and drift-gated
  - the executable bidirectional name-granular completeness guarantee (Criterion 6)
  - the criterion-1 measurement and the per-helper replay answer (Criteria 1 and 4)
  - three standing tree-wide gates — $schema headers, D-14 additivity, the G-B AST guard
  - the eight-instance ledger of the phase's running finding, counted from the SUMMARYs
affects:
  - docs/SURFACE-CHANGES.md
  - docs/SURFACE-AUDIT.md
  - docs/surface/v0.2-surface.json
  - .planning/REQUIREMENTS.md
tech-stack:
  added: []
  patterns:
    - assembler + exported serialize() + --check drift gate (the dump_openapi.py triad, third instance)
    - one parser for the curated log, shared by the assembler and the completeness test
    - a classification field closed in BOTH directions, so it cannot become an escape hatch
    - coverage pinned as a NAMED SET, never as a floor
    - a guard verified to refuse, with the limits of its refusal written down
key-files:
  created:
    - tools/assemble_surface_changes.py
    - docs/SURFACE-CHANGES.md
    - docs/SURFACE-AUDIT.md
    - tests/test_surface_completeness.py
    - tests/examples/test_artifact_schema_headers.py
    - tests/deployment/test_direct_construction.py
    - tests/products/test_required_operators_guard.py
  modified:
    - docs/surface/v0.2-surface.json
    - tests/test_surface_drift.py
    - tests/deployment/test_class_lookup.py
    - examples/08-e2e-demo/artifacts/scenario.yaml
    - Makefile
    - .planning/REQUIREMENTS.md
decisions:
  - "the phase's running finding stands at EIGHT numbered instances, counted from the SUMMARYs; the handoff said seven and the brief said eight-with-15-20-new, and 15-20's own SUMMARY explicitly declines a ninth — the discrepancy is recorded rather than smoothed"
  - "Gate 1 defers to tools/check_schema_headers.py rather than re-implementing the plan's weaker path-existence check; the plan's `# no-schema: DeclaredArtifact` marker does not exist in the tooling and never did"
  - "scenario.yaml's marker retagged deferred(15-21) -> deferred(permanent): 15-16 ruled it permanent, so naming a plan that has arrived and declined to close it was a false claim"
  - "15-06's plan-scoped subset test now diffs against the FROZEN baseline; reading the live manifest was correct for nineteen waves and became wrong the instant this plan regenerated it"
  - "tools/dump_surface.py was NOT modified — diff_surfaces() already returned fully-qualified names, so the plan's conditional edit was not needed"
  - "the ERGO-16 'every' reading is carried to Dave's gate as a ruling item, with all 152 residual lines accounted for by category, rather than resolved by the executor"
  - "the G-B guard's alias bypass, found by cross-AI review, was closed with fixed-point receiver aliasing and its limits written into the docstring rather than argued away"
metrics:
  duration: ~5h
  completed: 2026-08-05
---

# Phase 15 Plan 21: Phase Close Summary

The surface record's completeness is now proven by machine at name granularity
in both directions rather than asserted; the criterion-1 numbers are generated
from the executable audit with removal and relocation never summed; three
standing gates close ERGO-12, D-14 and G-B tree-wide; and the phase's strongest
non-ergonomic finding is written down as a checkable eight-row ledger.

**Status: PAUSED at Task 6, the blocking human checkpoint.** Tasks 1–5 are
complete and committed. `D-GATE-15` is not logged and nothing is merged.

---

## The finding, counted rather than quoted

The brief asked me to count the instances of *"a check that passes for a reason
unrelated to what it claims to verify"* from the SUMMARYs rather than trust the
carried list. I did, and the ledger is `docs/SURFACE-AUDIT.md` §4.1 — eight
numbered instances, one row per discovery with the SUMMARY that recorded it:
15-06 (a vacuous `__all__` scan), 15-13, 15-14, 15-15, 15-16 (Gate 2 tautologies
and an untested "nothing else changed"), **15-17** and **15-18** (the two
outright correctness defects), and 15-19 (fail-closed evidence read at the wrong
instant).

**Recorded discrepancy.** The handoff put the count at seven; the brief put it
at eight and attributed a new instance to 15-20. Neither matches the record.
15-19's SUMMARY numbers its own finding as *the eighth*, and **15-20's SUMMARY
explicitly states the running finding "did not gain a ninth instance here"** —
its two Gate 2 tautologies are a second *site* of an already-named pattern, and
15-20 says so deliberately. Two further second-site occurrences (15-19's
escalation check, 15-20's `run.py` replay environment) are documented in the
audit below the ledger, unnumbered for the same reason.

What 15-20 does contribute is the sharper lesson, and the audit carries it:
**a rewrite that fixes the tautology only where the plan text names it leaves
the replay path carrying it.**

---

## What the phase-close artifacts actually assert

### The curated log

`tools/assemble_surface_changes.py` joins the nineteen fragments into
`docs/SURFACE-CHANGES.md` — **267 entries, 54 public**. It refuses to build the
document from an entry missing any of the seven fields, from a `Change type`
outside the four, from a `Public surface` value that is not exactly
`true`/`false`, and from a public entry whose `Surface` is prose rather than a
fully-qualified name. All four refusals were probed and reverted.

`parse_entries()` is exported so the completeness test reads the log through
**the same parser that assembles it**. A second Markdown scraper would be a
second definition of what the log says.

### The completeness guarantee

The live manifest was regenerated **in place, exactly once** — the single-owner
rule — and `tools/dump_surface.py --check` exits 0 for the first time since
15-01, so the documented-drift gate has degenerated to plain bytes-equality
with nothing unclaimed. Verified directly: `unclaimed_drift(committed, live, "")`
returns `[]` with zero fragment text, because the bytes check short-circuits.

The diff is **52 added, 0 removed, 1 reshaped**, plus one `behavior` entry. Every
diff line is claimed and every public claim has a diff line.

`tests/test_surface_completeness.py` asserts six properties. Five falsification
probes were run and reverted, and the failure messages distinguish the three
cases that need different fixes:

| Probe | Result |
| --- | --- |
| delete the `ccf.deployment.load_and_boot` entry | `NO ENTRY`, naming it |
| retype it `added` → `removed` | `WRONG CHANGE TYPE. Found ['removed']…` from diff→log **and** a distinct log→diff failure |
| flip it to `Public surface: false` | `WRONG CLASSIFICATION`, **not** `NO ENTRY` |
| claim a name that does not exist | log→diff fails naming it |
| retype `load_artifact` `behavior` → `reshaped` | the required-behavior assertion fails naming that surface |

**`removed` is empty, and that is a finding rather than an omission.** D-15B
granted free rein on the public API pre-1.0 and the phase used none of it in the
removing direction.

### The three standing gates

- **ERGO-12 tree-wide.** `tests/examples/test_artifact_schema_headers.py` runs
  `tools/check_schema_headers.py` over the **exact named ten-directory set**
  inside the always-on `test` job, closing 15-12's one-example scope. Four
  probes fired: a deleted header, a header naming a nonexistent path, a header
  naming the wrong real schema (caught because the tool validates the *document*
  against the class), and an unauthorised deferral marker.
- **D-14 additivity.** `tests/deployment/test_direct_construction.py` builds
  `EntityResolutionSpec`, `SignalEnvelope`, all four `*Parameters` and `boot()`
  by hand. Its 22-line prologue **is** the pre-phase adopter code. It asserts the
  handle exposes no writer, and asserts from its own AST that it imports nothing
  from `ccf.deployment`.
- **G-B, structurally.** `tests/products/test_required_operators_guard.py` finds
  **11** `required_operators` implementations across `src/`, `runtime/` and
  `examples/` and refuses any that reads the operator registry's own keys.
  Verified to refuse: reintroducing the tautology in the quickstart fails naming
  file and line.

---

## The phase-close review (CLAUDE.md §3.1)

`/gsd-review --phase "Phase 15" --all` was run against the **deliverables**, not
the plan text — codex, cursor and gemini; `claude` excluded for independence.

| Reviewer | Verdict | Blocking | Advisory |
| --- | --- | ---: | ---: |
| codex | not ready to present | 2 | 2 |
| cursor | ready to present | 0 | 6 |
| gemini | ready to present | 0 | 2 |

**Both blocking findings are closed.** Full triage is `docs/SURFACE-AUDIT.md` §5.

**B-1 — the G-B guard was weaker than the audit claimed.** Codex found that
`ops = self._registry()` followed by `ops.keys()` passed, while the module
docstring claimed AST matching defeated rename bypasses. Correct, checkable, and
serious because the guard is presented as the structural closure of a fidelity
invariant. Closed: the refused-receiver set is computed to a **fixed point** over
assignments, walrus bindings and annotated assignments; `_receiver_name` sees
through `:=` and `await`; four alias probes added. The docstring now states what
the approach does **not** buy — receiver aliasing, not dataflow.

**B-2 — ERGO-16 says "every", the measurement says 152 remain.** The checkbox and
the number disagreed with nothing in between. Closed as far as an executor may:
§2.3 accounts for **all 152 lines** by category — 65 in files that are not
example drivers and are *required* untouched by ERGO-15/EXAM-04; 54 inside
example 03's `_live` leg, which `make ci` does not run and where relocation would
move assertions somewhere nothing executes them; 22 pinned by
`test_ext00_hardening.py`, which 15-20 was forbidden to modify; 4 process-protocol
handshakes; 6 the DEMO-03 narration that *is* the deliverable. **The reading of
"every" is carried to Dave's gate as a ruling item**, per §3.1's rule that an
unsurfaced decision is blocking and the response is to surface it.

Three advisory findings were cheap and strengthened a gate, so they were fixed
rather than carried: the schema gate now pins the **exact** directory set instead
of a floor; the baseline-provenance docstring no longer over-claims (it keys on
commit-subject text, not a pinned hash); and "the declared side of Gate 2" was
corrected everywhere — `required_operator_keys` is *upstream* of Gate 2's two
arguments, not one of them.

Eight advisory findings are carried forward in §5.3, including **both round-2
items open since mid-execution**:

- **Shared `public/` prose collisions** — closed by practice, carried as a gap.
  Every rewrite plan read each including section against its new target and
  three corrected prose the rewrite had falsified. No automated check for a
  mis-pointed include exists; building one belongs to Phase 16, which rewrites
  the prose anyway.
- **Stale plan text** — carried *deliberately*. This plan hit three instances
  itself and recorded each rather than editing history. A PLAN.md records what
  was intended; a SUMMARY records what was built. Rewriting the former to match
  the latter destroys the audit trail the discrepancies live in. The fix is a
  convention — an auditor reads SUMMARYs — and the audit now says so.

---

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 — Blocking] 15-06's subset test broke on regeneration**

- **Found during:** Task 5, by the full suite.
- **Issue:** `test_the_phases_fragments_claim_exactly_what_was_added` read the
  **live** manifest as its "before" side. Correct for nineteen waves, because
  the live manifest and the frozen baseline were byte-identical for all of them
  — and wrong the instant this plan regenerated the live manifest, since
  `diff(live, live)` is empty and the `claimed <= added` direction then fails
  for all 52 legitimately-claimed names.
- **Fix:** read the frozen baseline. Both sides of that comparison accumulate
  across the phase (its own docstring says the claims are a union), so the diff
  has to be the accumulated one. Behaviour-preserving for waves 2–13, and the
  baseline's immutability is itself asserted by digest and provenance.
- **Files modified:** `tests/deployment/test_class_lookup.py`
- **Commit:** `4a6e0ee`

**2. [Rule 1 — Bug] `scenario.yaml`'s deferral marker named a plan that would
never close it**

- **Found during:** Task 4.
- **Issue:** the marker read `deferred(15-21)`, but 15-16 ruled the deferral
  **permanent** — the document is `generator.py`'s input, not a CCF artifact,
  and it carries YAML floats the loader refuses by design. Leaving a plan number
  on it after that plan arrived and declined is a false claim about future work.
- **Fix:** retagged `deferred(permanent)` with the ruling cited. Comment-only;
  nothing hashes the file's bytes.
- **Files modified:** `examples/08-e2e-demo/artifacts/scenario.yaml`
- **Commit:** `c07eff0`

**3. [Rule 1 — Bug] the G-B guard's alias bypass** — see B-1 above.
- **Commit:** `38fcd00`

### Deliberate departures from the plan text

Stale plan text is this phase's named hazard; these are where execution
diverged, with the reason.

**1. Gate 1 defers to the existing tool rather than re-implementing it.** The
plan describes first-line presence plus "the path resolves to an existing file
under `docs/schemas/`". `tools/check_schema_headers.py` already checks four
strictly stronger things — editor-relative resolution, the schema's
`x-ccf-class-id`, that the class **accepts the document**, and a manifest
cross-check. Writing a weaker duplicate would have created a second definition
of "the header is right". The new module supplies what the tool cannot: always-on,
tree-wide, non-vacuous execution inside the `test` job.

**2. The plan's `# no-schema: DeclaredArtifact` exemption does not exist.** 15-16
and 15-17 both recorded hitting this. The implemented marker is
`# ccf-schema: deferred(<plan>) <reason>`. Rather than reproduce the plan's
conditional exemption, the gate pins the exemption set **by name** — which is
strictly stronger and is what the plan's "single documented exemption mechanism"
was reaching for. The tree carries exactly one, ruled permanent.

**3. `tools/dump_surface.py` was not modified.** The plan made the edit
conditional — "ideally none" — and `diff_surfaces()` as shipped in 15-01 already
returned fully-qualified added/removed/reshaped names. Dropped from the modified
set, as the plan instructed.

**4. The baseline has two commits, not one.** The plan's acceptance criterion
says `git log` shows "exactly one commit, 15-01's". It shows two — `6e6d3f5
feat(15-01)` and `c4e7ca4 fix(15-01)`, the second being 15-01's own in-plan
correction making the manifest import-order independent. The rule that matters —
written by 15-01 and never again by any other plan — holds, and that is what
`test_the_frozen_baseline_was_written_only_by_plan_15_01` asserts. The bytes at
`c4e7ca4` hash to the pinned digest.

**5. The "empty `docs/surface-changes/` still passes" check was scoped to the
drift assertion.** This plan also added a curated-log staleness gate to the same
module, which would legitimately fail with the fragments removed. The property
the criterion targets — that the standing gate is now genuinely bytes-equality
and not passing on fragment claims — was verified directly:
`unclaimed_drift(committed, live, "")` returns `[]`.

**6. Both `--check` probes on the assembler used a temporary fragment**, as the
plan directs, plus a third for an invalid `Change type`. All three reverted.

**7. `docs/SURFACE-CHANGES.md` stays in `docs/`.** Per the plan, not moved into
`public/`; raised at the checkpoint as an open question instead.

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `pytest tests` | **1999 passed, 2 skipped** (1960 → 1999, +39) |
| `make examples` | exit 0 — all ten |
| `make docs-strict` | exit 0 |
| `tools/dump_surface.py --check` | exit 0 — bytes-equality restored |
| `tools/assemble_surface_changes.py --check` | exit 0 |
| `make schema-headers --require-all` | exit 0 — 10 directories |
| `grep -rn "v0.2-surface-final" src runtime tools tests docs Makefile` | no match |
| frozen baseline sha256 | `cef0d469…`, unchanged; history is 15-01's only |
| `.planning/STATE.md`, `.planning/ROADMAP.md` | untouched (worktree mode) |

Measurement at the close: mechanical wiring **1425 → 134**, relocation
**737 → 152**, reported separately and never summed. Quickstart **451 → 350** raw
with mechanical **143 → 13**. Import lines **974 → 820** tree-wide.

---

## Tasks completed

| Task | Commit | What |
| --- | --- | --- |
| 1 | `8fe06d9` | The assembler, `docs/SURFACE-CHANGES.md` (267 entries), the drift gate, the Makefile target |
| 2 | `ed0d955` | Live manifest regenerated in place; `tests/test_surface_completeness.py`; SURFACE-AUDIT §1 |
| 3 | `878d7ff` | SURFACE-AUDIT §2–§4; REQUIREMENTS traceability for ERGO-01..17 |
| 4 | `c07eff0` | The three standing gates; the permanent-deferral retag |
| 5 | `4a6e0ee`, `38fcd00` | Full gate green; `/gsd-review`; both blocking findings closed; the review appendix |
| 6 | — | **Blocking checkpoint — awaiting Dave** |

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The register's five mitigations all hold:

| Threat ID | Disposition | Where it landed |
| --- | --- | --- |
| T-15-21-01 (an unrecorded public-surface change) | mitigated | `tests/test_surface_completeness.py`, both directions with change-type agreement; every one of the 53 diff lines is claimed |
| T-15-21-05 (a fragment claiming the wrong direction) | mitigated | the diff→log message distinguishes wrong-type from missing-entry from misclassified; probed |
| T-15-21-02 (an overstated reduction claim) | mitigated | generated from `audit_report()`; separate columns; the document contains no combined figure, and `test_audit_report_never_returns_a_combined_figure` parses its own source |
| T-15-21-03 (an incomplete migration note shipping) | mitigated | the assembler validates all seven fields and refuses; probed three ways |
| T-15-21-04 (phase completion without Dave's approval) | **open by design** | the plan stops at the blocking checkpoint; `D-GATE-15` is unlogged and nothing is merged |
| T-15-21-SC (package installs) | mitigated | no package installs in this plan |

## Self-Check: PASSED

Every file claimed above exists on disk; all six commit hashes resolve in
`git log`.
