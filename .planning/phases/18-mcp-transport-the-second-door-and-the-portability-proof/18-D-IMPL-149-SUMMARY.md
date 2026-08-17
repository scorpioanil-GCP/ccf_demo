# Phase 18 — `D-IMPL-149`: split the decision-instant leg

**In-phase fix of a blocking finding**, per `CLAUDE.md` §3.1. Authorized by
`D-IMPL-149` (Dave, 2026-08-17), which lifts `17-10`'s standing prohibition on
editing `tests/client/conformance/suite.py` **for this leg only**. `D-IMPL-148`
— the suite is not weakened to admit an adapter — remains in force, and nothing
else in `suite.py` was touched.

Not a plan execution. `17-10` is complete 4/4 and merged; none of it was re-done.

---

## What the defect was

`assert_decision_instant_is_auditable` opened by *refusing* a question that
named its own instant, so it necessarily asked with `as_of=None` — and then
ended at `_assert_views_agree(recovered, leg="decision instant")`, comparing the
recovered instants **across** subjects. Those two requirements contradict: under
`as_of=None` each subject resolves its instant from **its own clock**. Two
in-process deployments were measured 116 ms apart. The demand was unsatisfiable
in principle for any two subjects and was green only because one subject had
ever been bound, which made `_assert_views_agree` compare one thing with itself.

Signature defect of this phase family, twelfth recorded instance: an assertion
that passes because it compares nothing.

## What was done — Dave's three parts

**(1) The per-subject property is KEPT, unchanged in force.** Ask with
`as_of=None`, read the resolved instant off `result.lineage.graph_snapshot_at`,
re-ask pinned to it, require the identical content address. Every non-vacuity
guard stays: the refusal of a pre-pinned question, the `temporal_boundary is
not None` check, the naive-datetime check, and the refusing-question leg
requiring `refusal.request.temporal_boundary`. The only edits to this function
are the docstring and the removal in (3).

**(2) A separate cross-adapter leg was ADDED** —
`suite.assert_one_instant_is_one_decision`, which runs **only** under a question
whose `as_of` the test pinned and **refuses** an unpinned one by name. The
precondition is the mechanism: a cross-subject comparison means something
exactly when the instant is an *input* rather than an *output*, and the refusal
is the mirror image of the one in the leg it was split from. The two refusals
together are what stop the split collapsing back into the defect.

It asserts two things:

- **Per subject, against the input** — the answer echoes the pinned instant in
  `temporal_boundary` and is anchored to it in `lineage.graph_snapshot_at`.
  This is *correctness*, not agreement, and no other leg checks it:
  `assert_served_parity` requires transports to agree, and two transports both
  answering as of the wrong moment agree perfectly. This is why the leg is
  **non-vacuous with one subject** — stated in the docstring, following the
  `assert_served_parity` precedent rather than refusing a single subject.
- **Across subjects** — the audit view (echoed instant, graph anchor, address
  answered at that instant) is identical. The address is in the view
  deliberately: without it the comparison would hold two values that both had
  to equal `question.as_of` to get there, which is a cross-subject comparison
  that cannot fail — the exact shape `D-IMPL-149` was raised about. The overlap
  with `assert_served_parity` on the address is stated in the docstring rather
  than avoided.

**(3) The unsatisfiable demand was REMOVED** — the trailing
`_assert_views_agree(recovered, ...)` and the `recovered` accumulation that
existed solely to feed it. **The removal is recorded, not silent:** a paragraph
in `assert_decision_instant_is_auditable`'s docstring names what was removed,
records the 116 ms measurement, states that it was *unsatisfiable* rather than
merely failing, cites `D-IMPL-149`, and points at where the cross-adapter half
now lives. *Keep the reasoning, change the behaviour* — the discipline applied
in this phase to the egress `parameters={}` paragraph, the byte-identity
assertion, and the `D-IMPL-146` banner.

## Controls (`D-22`) — every new guard observed failing

Four new controls, all passing a divergent subject **into the shipped
assertion**. No `tmp_path` copy of a module the assertion never reads; no file
edited and reverted.

| Control | Where | What it proves |
| --- | --- | --- |
| `test_one_instant_refuses_a_question_that_names_no_instant` | `test_the_suite_fires.py` | The precondition is enforced, not conventional |
| `test_one_instant_fires_on_one_subject_that_answered_at_another_instant` | `test_the_suite_fires.py` | Non-vacuous with **one** subject — the anchor is held to the input |
| `test_one_instant_fires_when_two_transports_disagree_at_one_instant` | `test_the_suite_fires.py` | Non-vacuous with **two** — same instant, same anchor, different decision |
| `test_one_instant_fires_on_an_mcp_door_deciding_otherwise_at_that_instant` | `test_the_mcp_binding_fires.py` | The **real** second door is inside the comparison, not merely beside it |

The two cross-subject controls use divergences that move the *answer* and not
the *instant* (`plan_id` re-mint; a door answering another threshold), so the
per-subject half passes and the cross-subject half is what goes red. Each
asserts `"graph state anchored at" not in message` — a control that fired on the
per-subject check would prove nothing about the comparison across subjects.

`test_the_suite_fires.py::test_every_exported_leg_has_a_control_here` holds
`LEG_CALLS` to `suite.__all__`, so the new leg could not be added without a
control entry; the empty-collection control covers it automatically.

**Sabotage-verified, not assumed.** Each of the three new guards was disabled in
turn and the suite re-run:

| Guard disabled | Result |
| --- | --- |
| `_assert_views_agree(views, leg="one instant")` | both cross-subject controls FAIL (2 failed, 61 passed) |
| the per-subject anchor check | the one-subject control FAILS (1 failed, 62 passed) |
| the unpinned-question refusal | the refusal control FAILS — and the message it produced instead (`asked at None and read graph state anchored at …`) is why the refusal exists |

## Call sites

- `test_inprocess_conformance.py` — new `test_one_instant_is_one_decision` over
  `SUBJECTS` with the pinned `QUESTION`; the `UNPINNED_QUESTION` comment now
  records that the two legs take the two questions and neither can be handed the
  other's without going red.
- `test_mcp_conformance.py` — **the single-subject workaround is gone.**
  `test_the_decision_instant_is_auditable` now takes `SUBJECTS` (both
  transports) rather than `(MCP,)`, and the new leg takes both under the pinned
  question. The module docstring's "the last leg takes the MCP subject alone,
  and that is a finding rather than a dodge" paragraph was rewritten in the past
  tense: it now records what the finding was, that `D-IMPL-149` split the leg,
  and that both legs run over the full pair. The `MCP` constant's comment
  ("this transport alone, for the one leg that cannot compare two") was corrected.

## Verification

Every run used `PYTHONPATH=src:runtime` — without it the venv's editable install
resolves `ccf` to the main checkout and grades code this worktree did not write.
All logs written outside the repository (`/tmp/d149-*.log`).

| Gate | Baseline (base commit) | Now |
| --- | --- | --- |
| `make conformance` | exit 0, 56 passed | exit 0, **63 passed** |
| `make ci-core` (pytest leg) | 3832 passed, 118 skipped | **3839 passed, 118 skipped, 0 failed** |
| `make ci-core` | exit 0 | exit 0 |
| `make docs-strict` | exit 0 | exit 0 |

**Test count is up by 7, none removed:** 2 new binding tests (in-process, MCP),
3 new controls in `test_the_suite_fires.py`, 1 new control in
`test_the_mcp_binding_fires.py`, and 1 from the parameterized
empty-collection control gaining a leg.

**One deviation, mechanical (Rule 3).** The first `ci-core` failed at
`gate-tools` on `test_the_committed_report_is_current`: adding one line to
`suite.py`'s `__all__` shifted two coupling line numbers recorded in
`docs/surface/examples/RETIREMENT-COUPLINGS.md` (376→377, 409→410). Regenerated
with `python tools/retirement_sweep.py --report`, which is what that test
instructs. Two lines changed, both line numbers. This file is not the
single-owner `docs/surface/v0.2-surface.json`.

## Scope held

No other leg of `suite.py` was weakened, narrowed, or otherwise edited — the
diff against the pre-existing function is a docstring paragraph, a corrected
`Raises:` clause, and the removal Dave ordered. `_assert_views_agree`,
`_require_subjects`, `_ask`, `_ask_each`, `result_fields` and the six other legs
are untouched.

`STATE.md` and `ROADMAP.md` were not modified.
