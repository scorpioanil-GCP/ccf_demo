---
phase: 05-phase-i-2-agent-specialization-framework
fixed_at: 2026-07-26T00:00:00Z
review_path: .planning/phases/05-phase-i-2-agent-specialization-framework/05-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 5 (I.2): Code Review Fix Report

**Fixed at:** 2026-07-26
**Source review:** `.planning/phases/05-phase-i-2-agent-specialization-framework/05-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (WR-01 … WR-05; `fix_scope: critical_warning`, 0 critical)
- Fixed: 5
- Skipped: 0

**Verification gate, run before every commit:** `pytest` (599 passed, 2 skipped
— up from 589 baseline, +10 regression tests), `mypy` strict (63 source files,
clean), `python -m tools.lints` (exit 0). Each fix was additionally confirmed to
*fail* its own regression test with the fix reverted, so no test passes
vacuously.

## Fixed Issues

### WR-01: Grant state machine could wedge in `requested` / `pending-approval`

**Files modified:** `src/ccf/skills/grants.py`, `tests/skills/sinks.py`, `tests/skills/test_grants.py`
**Commit:** `e1a3bc4`

Everything after the first state mutation in `GrantLedger.request` now runs
inside one exception guard, implemented by splitting the decided part of the run
into `GrantLedger._decide`. Any exception — `AmbiguousPinnedVersionError` from
policy-regime resolution inside tier 1, or an `ApprovalSink` that raises rather
than returning a verdict — settles the grant in the terminal `refused` state,
audits the refusal (`resolved=False`), and re-raises the original exception
unchanged.

Chose the general guard over the reviewer's alternative of hoisting regime
resolution above the mutation: hoisting closes path 1 only, leaving the sink —
arbitrary user Protocol code that nothing in the contract forbids from raising —
still able to strand a grant in `pending-approval`. The guard closes the whole
class.

Regression tests: `TestNoWedgedStates` — a raising sink (new `RaisingApprovalSink`
double) and an ambiguous pinned policy regime; both assert the terminal state,
the audited refusal, the unchanged re-raise, and that the grant moves neither
`effective_hashes` nor the D-07 set hash.

### WR-02: Documented remediation blocked by the D-05 empty-bump refusal

**Files modified:** `src/ccf/controlplane/registry.py`, `src/ccf/skills/grants.py`, `tests/skills/test_grants.py`
**Commit:** `9b93763`

Took the reviewer's option (a), implemented as an explicit call-site statement
rather than a class allowlist inside the registry: `register_versioned` gains
`reissuable: bool = False`, and the grant ledger passes `reissuable=True`. The
registry therefore holds no knowledge of which artifact classes are single-use
request documents versus evolving revisions — that reading stays where it
belongs, at the call site (CLAUDE.md §11, mechanism not values). Rejected option
(b) (`register_typed`) because it drops the unbumped-change protection for
grants and renames the audit action, and option (c) (documentation only) because
it leaves the only working retry as a rename that mints a second Control Plane
key for one request.

D-05's unbumped-change refusal is untouched: content still never changes under a
version already claimed, `reissuable` or not.

`GrantTransitionError`'s message and the `request` docstring now state the retry
semantics explicitly.

Regression tests: `test_a_rejected_grant_can_be_re_issued_with_a_bumped_version`
(reject → re-issue with bumped `artifact_version` → effective, two versions
under *one* key) and `test_an_unbumped_content_change_is_still_refused`.

### WR-03: `SkillCatalog.resolve` audited phantom resolutions

**Files modified:** `src/ccf/skills/catalog.py`, `tests/skills/test_catalog.py`
**Commit:** `dad888e`

Applied the reviewer's fix as written: the declared-version search probes
through the unaudited `peek`, and exactly one audited `resolve` fires — on the
entry actually returned. This is the WR-08 discipline already implemented by
`GrantLedger._resolve_policy_regime` and `factory._resolve_pinned`, now applied
to its sibling path. Docstring updated to state the one-audited-resolution
property.

Regression test: `test_resolution_audits_only_the_entry_actually_returned` —
two versions under one key, resolve the second, assert exactly one `resolve`
event naming the returned content version.

### WR-04: CINV-01c static attribute-alias hole

**Files modified:** `tools/lints/no_hardcoding.py`, `tests/lints/test_cinv01c_behavioral.py`
**Commit:** `50d3a08`

The alias pass now tracks attribute-valued assignments (`A = m.Agent`) alongside
bare-name assignments and import aliases, restoring the documented invariant
that the D-12 accepted residual is *dynamic* construction only — every static
one-line rename fires.

Regression tests (4): the `Agent` and `Task` attribute-alias bypasses both fire;
an unrelated attribute alias (`B = m.Backend`) does not; and the same alias
inside the allowlisted factory module stays exempt. The last two pin that the
widened pass did not over-fire.

### WR-05: `GrantLedger` state volatile while grant artifacts are durable

**Files modified:** `src/ccf/skills/grants.py`, `tests/skills/test_grants.py`, `docs/PHASE_I2_GATE.md`
**Commit:** `8d38e6a`, superseded by `fba5b2a`
**Status:** SUPERSEDED — fully closed in `fba5b2a`. The minimum below was taken
on a false premise and the deferral has been withdrawn.

> **Correction (2026-07-26).** The rationale recorded below asserts that
> D-IMPL-18 and D-IMPL-27 were open and that closing WR-05 would preempt
> Dave's rulings. Both were **RESOLVED on 2026-07-25** (`docs/DECISIONS.md`).
> Nothing was blocked. Worse, D-IMPL-27's mutability split and D-IMPL-18's
> "the Control Plane's storage seam" together *dictate* where grant state
> belongs, so the answer existed before the ledger was written.
>
> `fba5b2a` implements it: grant state moved onto a
> `ControlPlaneStateStore` seam with an in-memory reference impl, closing
> both the in-process divergence (two ledgers over one plane now agree, so
> `grant_set_hash` is reproducible on a fresh ledger per CLAUDE.md §6.2) and
> the durability question (a deployment supplies a durable store; no
> consumer changes). I.4 inherits the seam rather than the question.
>
> Lesson worth keeping: a deferral is a claim about the decision log, and
> claims about the decision log must be checked against it. Citing a
> *resolved* decision as an open blocker is the same error as guessing at an
> open one — it just looks like diligence.

Took "Minimum: document the volatility explicitly and pin the intended
semantics with a test," not "Better: derive state from the audit journal."
Rationale, recorded because it is a scope judgment rather than a coding one:
rehydrating grant state requires ruling *where* durable grant state lives and
how a suspended (`pending-approval`) grant survives a restart. That is the same
question D-IMPL-18 asks of suspended workflow state and D-IMPL-27 of the
artifact/native-storage split — both open, both Dave's to rule (CLAUDE.md §11:
surface gaps, do not paper over them; §3 Phase I does not redesign). Committing
an answer inside a review fix would preempt them. Note also that I.2's
synchronous sink never *produces* a durable `pending-approval` grant; I.4's
suspending `ApprovalGate` does, which is where the need actually bites.

The boundary is now stated on the `GrantLedger` class docstring (including the
explicit contrast with the catalog's registry-derived membership, IN-03), pinned
by `test_ledger_state_is_in_process_and_does_not_rehydrate` so it cannot move
silently, and carried into `docs/PHASE_I2_GATE.md` §5 as an I.4 handoff item.

## Invariant Check

No fix touched the No-Hardcoding Rule (§6.4 — no prompt, agent definition,
threshold, or skill grant entered code; the one new flag is a mechanism
parameter, and every test value still comes from `tests/fixtures/banking/`),
harness neutrality (§7.3 — no harness import added; `/src` untouched in that
respect), single-writer (§10 — no new write handle to L3), or
audit/replay-by-construction (§6.2, §8.2). WR-01 and WR-03 *strengthen* the
audit plane: the first ensures no failure path escapes an audit record, the
second removes records of reads that never happened.

## Note on the review's own text

The gate document claim WR-01 called overstated ("no wedged `requested` grants",
`PHASE_I2_GATE.md` §3) is now true as written — the guard closes the paths that
made it overstated. No edit to that claim was needed.

---

_Fixed: 2026-07-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
