# Deferred items — phase 23

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary: an executor that closes a gap it discovers on the way past has turned
a planned wave into an unplanned one, and the fix ships without the decision it
needed.

## From plan `23-03`

**1. The `$schema` header gate is blind to a nested `artifacts/<subdir>/`, and
three shipped documents are in that blind spot today.**

`tools/check_schema_headers.py::ARTIFACT_GLOBS` matches one level under
`artifacts/`, so a document at `artifacts/<subdir>/*.yaml` is never discovered.
Measured on the pre-move tree:

```bash
# every file in the ten condemned trees whose FIRST line is a $schema header: 216
# of those, matched by examples/**/artifacts/*.yaml: 213
# NOT matched:
examples/03-harness-portability/artifacts/agents/agent-definition.yaml
examples/03-harness-portability/artifacts/agents/debt-profile.yaml
examples/03-harness-portability/artifacts/agents/policy-regime.yaml
```

All three carry `../../../../docs/schemas/…` headers and all three resolve
today, so nothing is currently wrong — but nothing is currently *checking*
either, and after the archive move all three need the same extra `../` as the
213 the gate does see, with the gate unable to say whether they got it.

- **Pre-existing.** Not caused by Phase 23; the glob has had this shape since
  plan `15-12`. Phase 23 only makes it consequential, because Wave 5's header
  repair will be gated by a check that cannot see three of its subjects.
- **Why it is not a one-character fix.** Deepening the pattern to
  `artifacts/**/*.yaml` puts `…/artifacts/agents` into
  `covered_artifact_directories`. Its parent is `…/artifacts`, which is not an
  example root (no `run.py`), so
  `tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root`
  goes red on a correct tree. Closing the gap therefore means deciding what
  the bijection's right side means for nested artifact directories — a design
  call, not a widening.
- **Carried to Wave 5 as a caveat, not as work**: `23-05`'s header repair
  should repair all **216**, and should record that the gate's green covers
  213 of them.

**2. A lowered count floor is visible to exactly one thing, and it is the
wrong signal.**

Sabotage `S-F3` set `MINIMUM_IMPLEMENTATIONS` to `0`. The module itself passed
(17 passed) as the plan predicted. What the plan did *not* predict is that
`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
FAILED — `tools/retirement_sweep.py::_floors` records each floor's value in the
coupling report, so lowering one makes the committed report stale.

- The detection is real but weak, and weak in a specific way: the message says
  *the report is stale*, not *a floor was lowered*. The reflex it invites is
  `retirement_sweep.py --report`, which turns it green and prints
  `floor 0, 14 witnesses, headroom 14` into a committed file nobody re-reads.
- **Not fixed here.** A gate that refuses a floor DECREASE would need to know
  the previous value, which means pinning floors in a second place — a real
  design decision about where the authority for a floor lives.

**3. The two scan roots in `tests/products/test_gate_two_call_shape.py` are
not as independent as their two constants suggest.**

`_plan_classes()` is derived from `SCANNED_TREES` and is consulted by
`_is_plan_construction`, so the binder scan — which reads
`BINDER_SCANNED_TREES` — depends on `SCANNED_TREES` as well. Measured under
sabotage `S-F2`: dropping `"examples"` from `SCANNED_TREES` alone cost the
binder scan one projecting body (14 → 13), even though `BINDER_SCANNED_TREES`
was untouched.

- **No defect today**, and no action owed by Phase 23: both constants were
  widened together, which is what the coupling requires. Recorded because a
  future reader widening one and not the other would get a partial result with
  no message saying why.
