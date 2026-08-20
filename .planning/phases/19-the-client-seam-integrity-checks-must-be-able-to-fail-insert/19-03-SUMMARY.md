---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
plan: 03
subsystem: client-seam / single-transport controls / codec controls
tags: [C-11, C-18, C-04, C-15, P1, P2, P4, single-transport, sabotage-control, ordering-guard]
requires:
  - "ccf.client.wire.TransportAdapter.ask(WireRequest) -> bytes — the bytes seam 19-02 landed"
  - "ccf.products.door.door_answer — the producer-minted echo 19-01 landed"
  - "ccf.client.codec.decode_outcome / check_outcome / verify_content_address"
  - "runtime/ccf_runtime/mcp/egress.py — the C-18 asked_at cross-check 19-01 landed"
provides:
  - "tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py — the phase's success sentence as a passing test"
  - "assert_a_crossed_question_is_caught / assert_an_altered_vessel_is_caught — single-transport assertions"
  - "tests/client/conformance/test_the_mcp_binding_fires._DecidesOtherwise — the divergence a parity leg still needs"
  - "tests/client/test_codec.assert_the_echo_check_precedes_the_refusal_branch — C-04's ordering precondition"
affects:
  - "19-07 (corrective prose; C-18's residual and C-10's undetected list are now measurements this plan names)"
  - "19-08 (the D-IMPL entries for C-11, C-18 and the declared as_of=None residual)"
tech-stack:
  added: []
  patterns:
    - "prove a check can fail with ONE subject; never let the failure mode be 'the two disagreed'"
    - "a shared assertion taking already-built subjects, so a control can hand it an honest one"
    - "assert the discrimination guard rather than argue it — the address check runs BEFORE the contract parse"
    - "assert a declared residual as a passing measurement rather than describing it as a caveat"
key-files:
  created:
    - "tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py"
  modified:
    - "tests/client/conformance/test_the_mcp_binding_fires.py"
    - "tests/client/test_codec.py"
decisions:
  - "Deleting the 19-02 re-label destroys BOTH of test_the_mcp_binding_fires.py's parity controls, measured — so `_DecidesOtherwise` was written to keep them alive: a door honest about the question and divergent in the answer, which is the divergence a single client structurally cannot catch and therefore the one parity is still for"
  - "The refused-half echo leg passes a DIFFERENT `sent` against a captured refusal rather than re-encoding an outcome with a crossed echo — nothing is forged, and the mismatch is exactly 'a governed no attributed to a question nobody asked'"
  - "The C-18 residual asserts WHICH instant answered (graph_snapshot_at equals the instant the transport substituted), not merely that nothing raised"
metrics:
  duration: "~2h30m"
  tasks: 3
  commits: 3
  collected_delta: "4082 -> 4099 (+17)"
  completed: 2026-08-20
---

# Phase 19 Plan 03: The Phase's Success Sentence, Discharged Single-Transport — Summary

Proved both client-seam integrity checks can fail with **one** client, **one**
adapter and **one** deployment — never with a parity diff — and observed every
control failing under sabotage before writing any of this down.

## What Was Built

**A module whose every assertion names one subject.**
`tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py`
holds nine tests and no comparison between two transports. Three hostile
subjects, each subclassing or wrapping the **shipped** adapter:

- `_InProcessAnswersAnotherQuestion` and `_McpAnswersAnotherQuestion` — one
  expression each, `super().ask(request.model_copy(update={"parameters": …}))`.
  Under the bytes seam there is nothing else to write, and **that there is
  nothing else to write is the property**: before `19-01`/`19-02` this class had
  to re-label the echo from client state to be a crossing at all.
- `_McpMovesTheDoorsInstant` — overrides `_call`, not `ask`, because `ask` is
  what builds the `arguments` mapping and this control must move **one entry of
  it** (`asked_at`, by one microsecond) while leaving the encoded `request`
  byte-identical. The delegation names `McpStdioAdapter._call` explicitly, per
  the plan: `_call` is a `staticmethod`, and zero-argument `super()` inside one
  resolves against the first positional argument (`program: Path`).
- `_Editing` — a generic wrapper over either shipped adapter, applying a byte
  edit to what came back and **recording it**, so the discrimination guard
  asserts against what the client actually refused.

**Two shared assertions, each with three limbs in the same order.**
`assert_a_crossed_question_is_caught` and `assert_an_altered_vessel_is_caught`
take already-built adapters, so the control on each can hand it an honest one
in the `hostile` slot. Per call: the exact `D-10` type (`TransportError`, not
the `BindingError` subclass), **no `Result` produced at all** (a sentinel bound
before the `raises` block), and the honest subject served on the same question
against its own provisioned root.

**`C-18`'s residual, asserted rather than described.** The declared limit is a
**passing** test carrying no expected-failure marker, and it asserts more than
*"nothing raised"*: the served vessel's `lineage.graph_snapshot_at` **equals the
instant the hostile transport substituted**. The client resolved the clock
(`C-15`), so the instant crosses the pipe once and the client holds nothing that
could contradict the transport. `C-02`'s as-asked echo is asserted beside it
(`temporal_boundary is None`) because that is precisely *why* there is no second
operand.

**Seven codec controls, all over shipped functions.** Two post-encoding byte
edits handed straight to `decode_outcome`; the refused-half echo leg against a
refusal **captured from the fixture deployment**; the ordering guard as an AST
scan fed `inspect.getsource(ccf.client.codec)`; two controls on that guard; and
`P4`'s guard-liveness control with its vacuity twin.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | A crossed question is caught by one client — `P1`, both transports independently | `6b24783` | `test_a_crossed_question_is_caught_on_one_transport.py`, `test_the_mcp_binding_fires.py` |
| 2 | An altered vessel is caught by one client — `P2`(a), with its discrimination guard | `8a0fd42` | `test_a_crossed_question_is_caught_on_one_transport.py` |
| 3 | The codec's own controls — byte sabotage, the refused half, the ordering guard, `P4` | `99fa0dd` | `tests/client/test_codec.py` |

No Rule-1/2/3 deviations were needed: this plan touches only `tests/`, adds no
public name, and left no generated record stale. `make ci-core` was green on the
first run of the plan-level check.

## The Measured Arithmetic — every increment named against a property

| Scope | Before | After | Δ |
|-------|--------|-------|---|
| `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py` | 0 | **9** | **+9** |
| `tests/client/conformance/test_the_mcp_binding_fires.py` | 3 | **4** | **+1** |
| `tests/client/conformance` | 77 | **87** | **+10** |
| `tests/client/test_codec.py` | 34 | **41** | **+7** |
| full default collection | 4082 | **4099** | **+17** |
| `make ci-core` passed | 3964 | **3981** | **+17** |

`34 + N` with **N = 7**, as the criterion required. The `+17` decomposes
exactly, with no unnamed increment:

| # | Test | Property |
|---|------|----------|
| 1 | `..._crossed_question_is_caught_over_the_in_process_transport` | `P1`, single-transport |
| 2 | `..._crossed_question_is_caught_over_the_mcp_transport` | `P1`, single-transport, independently |
| 3 | `test_control_the_assertion_fails_when_it_is_handed_an_honest_adapter` | `P1`'s control on the control (`D-22`) |
| 4 | `..._door_answering_at_another_instant_is_caught_when_the_boundary_is_concrete` | `C-18`'s cross-check, live |
| 5 | `test_the_unmutated_adapter_serves_the_same_concrete_question` | `C-18`'s vacuity guard |
| 6 | `test_an_absent_boundary_leaves_the_moved_instant_undetectable` | `C-18`'s declared residual (`C-15`) |
| 7 | `..._altered_vessel_is_caught_over_the_in_process_transport` | `P2`(a), single-transport |
| 8 | `..._altered_vessel_is_caught_over_the_mcp_transport` | `P2`(a), single-transport, independently |
| 9 | `test_control_the_vessel_assertion_fails_when_it_is_handed_an_honest_adapter` | `P2`'s control on the control |
| 10 | `test_a_crossed_question_no_longer_reaches_the_parity_comparison` | `C-05`/`C-11`'s consequence for the parity module |
| 11 | `..._byte_edit_inside_the_vessel_is_caught_by_the_address_check` | `P2`(b), no transport at all |
| 12 | `..._byte_edit_inside_the_echo_is_caught_by_the_question_comparison` | `P2`(b), the other operand |
| 13 | `..._refusal_echoing_a_question_nobody_asked_is_a_transport_failure` | `C-04`'s refused half, as a measurement |
| 14 | `test_the_shipped_decoder_compares_the_echo_before_it_returns_a_refusal` | the ordering guard, over the real module |
| 15 | `test_control_the_ordering_guard_fires_on_a_reordered_decoder` | the ordering guard's `D-22` control |
| 16 | `test_control_the_ordering_guard_refuses_a_scan_that_found_nothing` | the ordering guard's silent-success control |
| 17 | `test_the_parameter_guard_is_what_prevents_a_false_wire_failure` | `P4`, with its vacuity twin in the same test |

### The sentence the plan asked for, stated

> **`P1` is discharged by 2 single-transport assertions, none of which names a
> second subject** — one over `inprocess` and one over `mcp+stdio`, each with
> its own vacuity guard and a shared control that was watched failing.

And more generally: **no assertion added by this plan compares two subjects.**
Confirmed by reading every one of the seventeen, and by grep — the only `==`
between two runtime values in the new module is
`served.lineage.graph_snapshot_at == _McpMovesTheDoorsInstant.substituted[-1]`,
which holds one subject's answer against what that same subject's transport
did, never against another transport.

## Every control was OBSERVED failing, then restored

The phase's thesis is that a control which cannot fail is the defect under
repair, so nothing here is asserted on the strength of having passed. Sabotages
ran in **untracked scratch modules** and in **out-of-tree copies of `src/` and
`runtime/`** reached by `PYTHONPATH`; every scratch module was deleted
immediately and `git status --short` was clean after each. **No tracked source
file was edited and reverted.**

| # | Limb under observation | Sabotage | Observed |
|---|------------------------|----------|----------|
| 1 | `P1`, both transports | `if outcome.request != sent:` **deleted** from an out-of-tree `codec.py` | both legs red; `2 failed, 4 passed` |
| 2 | `P1`'s control on the control | shipped — it *is* the observation | `Failed: DID NOT RAISE TransportError`, vacuity wording absent |
| 3 | `C-18`'s cross-check | hostile `_call` held to the **identity** (no microsecond move) | `Failed: DID NOT RAISE TransportError` |
| 4 | `C-18`'s cross-check | the door's own `temporal_boundary is not None` block **deleted** from an out-of-tree `egress.py` | `Failed: DID NOT RAISE TransportError` — the guard is what catches it |
| 5 | `C-18`'s vacuity guard | the question swapped for the deployment's refusing one | `AssertionError: assert not True` |
| 6 | `C-18`'s residual, equality limb | the hostile `_call` made to **record the un-moved instant** while still moving the door's | `AssertionError: …048883 == …048882` |
| 7 | `P2`(a), both transports | the vessel edit held to the identity | both red, `Failed: DID NOT RAISE TransportError` |
| 8 | `P2`(a), both transports | `verify_content_address`'s comparison neutralised out-of-tree | both red |
| 9 | `P2`(a)'s discrimination guard | the edit made to break the vessel's JSON | **the leg stayed green** and only the guard went red |
| 10 | `P2`(a)'s control on the control | shipped | `Failed: DID NOT RAISE TransportError` |
| 11 | `P2`(b) vessel byte leg | `verify_content_address` neutralised out-of-tree | red |
| 12 | `P2`(b) echo byte leg | echo comparison deleted out-of-tree | red |
| 13 | `P2`(b)'s discrimination guard | a byte edit that unbalances the vessel's quoting | leg green, guard red |
| 14 | `C-04`'s refused-half leg | echo comparison deleted | red |
| 15 | `C-04`'s refused-half leg | the two statements **swapped** in an out-of-tree `codec.py` | red **while every served leg stayed green** |
| 16 | the ordering guard, shipped call | the same swap | red — so it reads the real module, not a synthetic string |
| 17 | the ordering guard, shipped call | echo comparison deleted entirely | red on its *found-nothing* limb, over the **real** module |
| 18 | the ordering guard's two controls | each handed the **healthy** source | both `Failed: DID NOT RAISE AssertionError` |
| 19 | `P4` | echo comparison deleted | red |

### Two of these are worth stating on their own

**Sabotage 15 is the measurement `C-04` never had.** Swapping the echo
comparison and the `product_json is None` return in `check_outcome` turned
**exactly two** tests red — the refused-half leg and the ordering guard — and
left all thirty-nine others green, including every served-half leg in the
module. That is the silent uncovering the ordering guard exists for, watched
happening.

**Sabotage 9/13 is `19-RESEARCH.md` Pitfall 3, demonstrated live rather than
argued.** When the tamper is made to corrupt the vessel into unparseability,
the leg *still* raises `TransportError` with the same `content address`
wording — because `check_outcome` recomputes the address **before** it parses
the contract — so the leg passes while proving that the parser fires. Only the
discrimination guard notices. That is why it is an assertion in this plan and
not a paragraph.

### Limbs asserted rather than observed — stated plainly

Two, and no more:

1. **The `P4` vacuity twin's non-raising half** (the `str`-rendered value that
   round-trips). Its failing state would be a canonicalizer that mangles a
   wire-stable spelling, which is a different module's property; it is asserted,
   not observed.
2. **`_assert_the_tamper_stayed_well_formed`'s "recorded no edited bytes"
   limb** — the branch that fires if the wrapper never applied its edit. It is
   a guard on the guard and its failing state was not manufactured.

Everything else in the table above was watched going red.

## The must-have truths, each verified

1. **A transport that answered a different question is caught by ONE
   `ProductClient`, on ONE adapter, against ONE deployment.** Tests 1 and 2;
   no second subject appears in either. Observed red when the comparison is
   removed (sabotage 1).
2. **The same on BOTH shipped transports, as two independent proofs.** Two
   separate test functions, each provisioning its own pair of roots. Neither
   mentions the other and neither's failure mode is *"the two disagreed"*.
3. **An altered vessel is caught by one client on one adapter, and separately
   by `decode_outcome` over tampered bytes with no transport at all.** Tests 7,
   8 (through a client) and 11 (pure function over bytes).
4. **The tampered bytes stay WELL-FORMED and CONTRACT-VALID.** Asserted, not
   argued, in both places (`_assert_the_tamper_stayed_well_formed`,
   `_assert_the_tamper_is_attributable`), and both guards observed red on an
   unattributable tamper while their legs stayed green.
5. **Every sabotage carries a vacuity guard.** `P1` and `P2`(a) carry theirs
   inside the shared assertions; `P2`(b)'s two byte legs each decode the
   untampered bytes and assert a served outcome; `C-18`'s is its own test;
   `C-04`'s is `check_outcome(captured, sent=refusing) is None`; `P4`'s is the
   admitted spelling in the same test.
6. **`check_outcome`'s echo comparison runs BEFORE the refusal branch, asserted
   rather than assumed.** `assert_the_echo_check_precedes_the_refusal_branch`
   over `inspect.getsource(ccf.client.codec)`, with a pre-assertion that the
   source it is about to read defines `check_outcome` — because a count of
   calls proves nothing about what they were handed. Observed red on real
   reordered source (sabotage 16) and on real source where the statement is
   absent (sabotage 17).
7. **`WireRequest._parameters_survive_the_wire` is demonstrably what prevents a
   FALSE failure.** `model_construct` bypasses it, a `Decimal` parameter then
   renders as text, and the decoder reports a `TransportError` on an exchange
   in which nothing went wrong. Observed red when the comparison is removed.
8. **`C-18` is exercised by a control that alters `asked_at` ALONE, and its
   residual is a measurement.** The `_call` override mutates exactly one entry
   of the `arguments` mapping — confirmed by reading; the `request` argument
   `ask` built is untouched, which is what makes the echo match perfectly and
   the door's own cross-check the only thing that can catch it. The residual
   test carries no expected-failure marker and asserts *which* instant answered.

## Source assertions

| Assertion | Required | Measured |
|-----------|----------|----------|
| new module collects | ≥ 6 | **9** |
| `grep -c "asked_at"` (new module) | ≥ 1 | **4** |
| `grep -c "xfail"` (new module) | 0 | **0** |
| `grep -c "is TransportError"` (new module) | ≥ 1 | **1** (plus two `is not TransportError` exact-type refusals) |
| `grep -cE "[0-9a-f]{64}"` (new module) | 0 | **0** — no digest is asserted anywhere |
| `grep -c "ContextProductContract.model_validate_json"` (new module) | ≥ 1 | **1**, inside the guard both altered-vessel tests call |
| `grep -c "encode_outcome"` (new module) | ≥ 1 | **2** |
| `grep -cE "json\.dumps"` (new module) | 0 | **0** |
| `grep -cE "\.replace\(b"` (`test_codec.py`) | ≥ 2 | **2** |
| `grep -c "assert_the_echo_check_precedes_the_refusal_branch"` | ≥ 3 | **4** |
| `grep -cE "inspect\.getsource\(ccf\.client\.codec\)"` | ≥ 1 | **1** |
| `grep -c "model_construct"` | ≥ 1 | **2** |
| `grep -c "RefusalEnvelope("` | unchanged | **0**, unchanged |
| the two legs' `match=` strings | disjoint | `"different question"` vs `"content address"`, neither in the other's assertion |
| `make lint` | exit 0 | **exit 0** |

## Verification

| Step | Result |
|------|--------|
| `pytest tests/client -q` | **415 passed, 0 failed** |
| `pytest tests/client/conformance -q` | **87 passed** |
| `pytest tests/client/test_codec.py -q` | **41 passed** |
| new module alone | 9 passed |
| `make lint` | **exit 0** (no-hardcoding over `tests/` included) |
| `make typecheck` | exit 0 — 211 source files |
| `make test` | **3981 passed, 118 skipped, 0 failed** |
| `make gate-tools` | 400 + 154 passed |
| **`make ci-core`** | **exit 0** |

## Deviations from Plan

### 1. Deleting the re-label destroys BOTH parity controls — measured, and repaired

The plan told this task to delete the echo re-label from
`test_the_mcp_binding_fires.py::_AnswersAnotherQuestion` and *"retarget the
module's existing assertion about that class"*. It did not anticipate that
**two** tests depend on that class, nor what deletion does to them. Measured in
an untracked scratch module before anything was changed:

```
SERVED PARITY: TransportError the outcome echoes a different question …
ONE INSTANT:   TransportError the outcome echoes a different question …
```

Both `suite.assert_served_parity` and `suite.assert_one_instant_is_one_decision`
now raise `TransportError` out of the **client**, before either leg compares
anything. Simply retargeting them to `pytest.raises(TransportError)` would have
left `D-IMPL-149`'s cross-adapter control — *"a real second door inside the
comparison"* — asserting nothing about the comparison at all. That is a control
losing its ability to fail, in the phase whose subject is controls that cannot
fail.

**Repair:** `_DecidesOtherwise` was written — a door that is **honest about the
question and divergent in the answer**: the door's own echo untouched, the
vessel altered (a synthetic marker on `plan_id`, so no deployment vocabulary
enters a control module), and the `content_address` **recomputed** over the
altered vessel so the producer's claim about its own bytes is true. Nothing in
`check_outcome` can object, and only a comparison across transports can catch
it — which is the sharpest available statement of why parity still earns its
keep after this phase, and it is now in that module's docstring.

Consequences to record:

- **The module collects 4, not the 3 the criterion names.** The fourth is
  `test_a_crossed_question_no_longer_reaches_the_parity_comparison`, which is
  the retargeted assertion about `_AnswersAnotherQuestion` and is *not* a
  duplicate of the new module's MCP leg: it asserts what the seam change did to
  **this module**, so a later reader does not have to re-derive why the class
  stopped being usable here.
- **`grep -A3 "class _AnswersAnotherQuestion"` shows no re-label, and the string
  `model_copy(update={"request"` still appears once — in that class's
  docstring.** The plan's criterion (*"anywhere"*) and its instruction (*"do not
  delete the class or its history"*) are in direct conflict here. The history
  won, per the standing amend-never-delete rule: the docstring records what the
  class used to do, why it did it, and what deleting it proved.

### 2. The questions are imported, not re-derived

The plan said to read `PRODUCT_ID`, the parameter name and the two values off
the deployment's documents *"exactly as `test_inprocess_conformance.py` does"*.
They are instead **imported from that module**, on the rule
`test_mcp_conformance.py` already states: *the same question* is then literally
the same object and cannot drift into two. The No-Hardcoding Rule is satisfied
at the one place the vocabulary enters, which is stricter than two derivations,
not looser.

### 3. `_Editing` and `_alter_the_vessel` are local, per the plan, and the reason is stated in code

`suite.py` ships `_Tampering` and `_alter_the_vessel` for the `C-12` legs. The
plan instructed this module not to import them; the local versions carry the
independence argument in their docstring, on the precedent `19-05` set when it
mirrored rather than imported `count_result_construction_sites` — a change to
one must not silently change the other, and the suite's are private members of a
module whose own legs fail with `AssertionError` from inside the suite while
everything here fails with `TransportError` out of one client.

### 4. Where the plan's own text was measurably wrong

- **`grep -c "xfail" == 0` was unsatisfiable as first written.** The plan's
  action text tells the residual's docstring to say it is *"not an `xfail`"*,
  and its criterion forbids the token. Reworded to *"carries no
  expected-failure marker"*; the criterion now holds and the sentence still
  says what it meant.
- **Every line citation in the `read_first` blocks was stale**, as `19-02`,
  `19-04` and `19-05` each recorded before this. `codec.py::check_outcome` is
  not at `:226-244`, `decode_outcome` is not at `:290-304`,
  `suite.py::assert_wire_failure_parity` is not at `:576-641`, and
  `mcp_stdio.py::_call` is not at `:368-371`. Every symbol **name** was correct
  and was what found the code. This is the **fourth consecutive plan in this
  phase** to hit it, and `D-IMPL-114` already rules that prose cites
  `path.py::Symbol` for exactly this reason.
- **`test_codec.py` has no fixture-deployment access at its own level, and did
  not need one added.** The plan cited `test_the_suite_fires.py`'s
  `refusal_template` fixture (which lives under `conformance/conftest.py`); the
  parent `tests/client/conftest.py` already publishes `seeded_root` and
  `config_document`, so the capture is three lines and no new fixture directory.

### 5. Choices taken that are stronger than the plan's instruction

- **The refused-half leg forges nothing.** The plan said to *"encode it as an
  outcome whose `request` names a different question than `sent`"*. Instead the
  **captured outcome is passed through untouched** and a *different* `sent` is
  handed to `check_outcome`. Nothing about the producer's answer is altered, and
  the mismatch is exactly the situation `C-04` describes: a governed "no"
  reaching a caller who asked something else.
- **The `C-18` residual asserts which instant answered.** The plan asked only
  that it *"does not raise and returns a served `Result`"*. The hostile class
  records the instant it substituted, and the test asserts
  `served.lineage.graph_snapshot_at` **equals** it — so the residual is a
  statement about what the transport got away with, not merely about silence.
  Observed red when the recording is made to lie (sabotage 6).
- **The ordering guard's found-nothing limb was observed on the real module,
  not only on a synthetic string.** Deleting the echo statement from an
  out-of-tree `codec.py` fires it (sabotage 17), which is a stronger
  demonstration than the shipped control's `"x = 1"`.
- **A first draft of the residual asserted `served.temporal_boundary is not
  None` and failed loudly**, because `C-02` makes the echo *as asked* and the
  caller sent `None`. Recorded because it is the phase's own design being
  enforced against this plan's author by an existing green leg.

### 6. Not done, deliberately

- **`suite.py` is untouched.** The `C-12` legs are `19-04`'s and this plan reads
  them only for shape.
- **No `xfail`, no skip, no marker anywhere in this plan.**
- **`.planning/STATE.md` and `.planning/ROADMAP.md` were NOT written**, per the
  orchestrator's standing instruction that the `state.*`/`roadmap.*` SDK writers
  are known-destructive on this repo. The orchestrator owns those writes.
- **No surface fragment was filed**, because this plan adds no public name in
  `src/` or `runtime/`. `make ci-core` confirms: no surface gate fired and no
  generated record went stale.

## Known Stubs

None. Every helper added is called by an assertion, every constant is read, and
every hostile subject is driven through the real `ProductClient`.

## Threat Flags

None beyond the plan's own `<threat_model>`. `T-19-08`, `T-19-09`, `T-19-10`
and `T-19-11` are each mitigated by a control that was **observed failing** when
the property it guards was broken. `T-19-08b` is mitigated **where checkable**
and its residual is now a passing assertion rather than a sentence, exactly as
`C-18` requires. `T-19-SC` holds — this plan installed no package and added no
dependency.

## Self-Check: PASSED

Created files:
- FOUND: `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py`

Commits (all present in `git log`):
- FOUND: `6b24783` `test(19-03): a crossed question is caught by ONE client, on each transport`
- FOUND: `8a0fd42` `test(19-03): an altered vessel is caught by ONE client, with its discrimination guard`
- FOUND: `99fa0dd` `test(19-03): the codec's own controls — byte sabotage, the refused half, ordering, P4`

Key links (all matched):
- new module → `ccf.client.client.ProductClient.ask` via a hostile subclass of a shipped adapter; `pytest.raises\(TransportError` — 3 matches
- `tests/client/test_codec.py` → `ccf.client.codec.decode_outcome` over tampered bytes; `decode_outcome\(` — 14 matches
