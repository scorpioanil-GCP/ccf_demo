---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
plan: 04
subsystem: client-seam / conformance suite
tags: [conformance, C-12, P3, tamper-legs, involution, sabotage-control]
requires:
  - "ccf.client.wire.TransportAdapter.ask(WireRequest) -> bytes — the bytes seam 19-02 landed"
  - "ccf.client.codec.encode_outcome"
  - "ccf.client.codec.check_outcome — the echo comparison"
  - "ccf.client.codec.verify_content_address — the address recomputation"
provides:
  - "tests.client.conformance.suite._Tampering — the generic byte-corrupting decorator"
  - "tests.client.conformance.suite._cross_the_echo — an involutive echo tamper"
  - "tests.client.conformance.suite._alter_the_vessel — an involutive vessel tamper"
  - "tests.client.conformance.suite.assert_a_crossed_echo_is_caught"
  - "tests.client.conformance.suite.assert_an_altered_vessel_is_caught"
  - "tests.client.conformance.test_the_suite_fires._reversing_subject — the control mechanism"
affects:
  - "19-03 (runs in wave 4; it reads suite.py, which this plan grew by one section)"
  - "19-07 (corrective prose; the two new legs are the evidence codec.py's B0 block is amended against)"
  - "19-08 (the D-IMPL entry for C-12)"
tech-stack:
  added: []
  patterns:
    - "wrap every registered subject in a decorator the subject's author never writes"
    - "derive the crossed question from the echo already on the wire; never spell a second one"
    - "make each tamper an involution, so a control can neutralize it with the shipped edit"
    - "replace a tautological same-object assertion with an independently-built witness"
key-files:
  created: []
  modified:
    - "tests/client/conformance/suite.py"
    - "tests/client/conformance/test_inprocess_conformance.py"
    - "tests/client/conformance/test_mcp_conformance.py"
    - "tests/client/conformance/test_the_suite_fires.py"
    - "docs/surface/examples/RETIREMENT-COUPLINGS.md"
decisions:
  - "The exact-type check is spelled as a named boolean (`caught_the_wire_failure_itself = type(caught) is TransportError`) rather than `is not`, so the discipline is legible and greppable rather than implied by an `except` clause"
  - "The controls use the module's existing `_fails()` helper rather than an inline `pytest.raises`, because an inline copy of the helper is the copy-testing defect this module forbids one scope over"
  - "The `_reversing_subject` docstring states a MEASURED limit rather than the plan's claim: a non-involutive edit turns the control red, an edit that changed nothing at all would not"
metrics:
  duration: "~2h"
  tasks: 3
  commits: 4
  collected_delta: "4053 -> 4061 (+8)"
  completed: 2026-08-20
---

# Phase 19 Plan 04: The Tamper Legs Every Official Adapter Carries — Summary

Made *"the integrity checks are live"* an obligation the suite imposes rather
than a claim an adapter author makes, by wrapping every registered subject in a
byte-corrupting decorator it never writes and cannot opt out of — which is
possible **only** because `19-02` retyped the seam to bytes.

## What Was Built

**A decorator that is generic because the seam is bytes.**
`suite._Tampering(inner, edit).ask(request)` returns `edit(inner.ask(request))`
and nothing else. It satisfies `TransportAdapter` structurally and knows
nothing about any transport. Under the previous object seam no such class
could exist: a wrapper standing where this one stands could only have edited an
outcome the adapter built **from the request it was handed**, which is the
reconstruction `D-IMPL-151` finding `B0` names, not a tamper. That argument is
in the class docstring, because it is the whole reason this plan is possible.

**Two involutive edits, neither of which spells deployment vocabulary.**

- `suite._cross_the_echo` reads the echo already on the wire and suffixes its
  class name with a module-level synthetic marker, or strips the marker if it
  is already there. No product id and no parameter name enters the suite; the
  crossed question is *derived*, per the neutrality this module's own docstring
  claims and `test_the_suite_fires.py::test_the_suite_names_no_registered_scheme`
  asserts.
- `suite._alter_the_vessel` moves one space immediately inside the vessel
  text's opening brace and leaves `content_address` at the producer's value.
  The edited text is valid JSON and a valid contract in **both** directions, so
  the failure lands on `codec.verify_content_address` rather than on the parser
  or the contract check — `19-RESEARCH.md` Pitfall 3, avoided by construction.

**Two legs, each with three limbs, each per subject.** Neither leg compares two
subjects, so a suite with one subject bound is still non-vacuous (`C-11`, `P3`).
Per subject: the tampered wire must raise an exception whose **exact type** is
`TransportError` carrying the codec's own wording; the subject's factory must
be type-stable against an independently connected witness; and an untampered
client on the same question must **not** raise.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | The decorator, the two edits, the two legs | `cbb37a7` | `suite.py` |
| 2 | Bind both legs over every registered subject | `7d6409e` | `test_inprocess_conformance.py`, `test_mcp_conformance.py` |
| 3 | A control per leg — the reversing subject | `86cf3cd` | `test_the_suite_fires.py` |
| — | Refresh the retirement-couplings report (Rule 3) | `ad1a131` | `docs/surface/examples/RETIREMENT-COUPLINGS.md` |

## The Measured Arithmetic

### 8 → 10 per binding module — the `C-12` / `D-GATE-18` reconciliation

Measured with `--collect-only`, not assumed:

| Module | Before | After | Δ |
|--------|--------|-------|---|
| `test_inprocess_conformance.py` | 8 | **10** | **+2** |
| `test_mcp_conformance.py` | 8 | **10** | **+2** |
| `test_the_suite_fires.py` | 44 | **48** | **+4** |
| `tests/client/conformance` | 69 | **77** | **+8** |
| full default collection | 4053 | **4061** | **+8** |

Each binding module gained exactly **two call lines and two docstrings** and no
constant — `git diff | grep -E "^\+[A-Z_]+ *[:=]"` returns nothing for that
task. This is the arithmetic `C-12`'s reconciliation with `D-GATE-18`'s
zero-diff claim rests on: that claim was about binding a new **adapter**
without touching the suite, not about never adding a new **property**.

**The +4 in `test_the_suite_fires.py`, named against `P3`:**

1. `test_the_crossed_echo_leg_fires_when_the_tamper_is_not_caught` — `C-12`/`P3`,
   the crossed-echo half's `D-22` control.
2. `test_the_altered_vessel_leg_fires_when_the_tamper_is_not_caught` — `C-12`/`P3`,
   the address half's.
3. and 4. Two further parametrizations of the existing
   `test_every_leg_refuses_an_empty_collection_of_adapters`, which is
   parametrized over `LEG_CALLS` — so each new leg inherits the
   empty-collection control the day it is registered rather than the day
   somebody remembers.

The `+8` full-suite delta equals the `+8` conformance delta exactly: nothing
outside this directory moved.

## Every control was OBSERVED failing, then restored

The phase's own thesis is that a control which cannot fail is the defect under
repair. Four sabotages, all run in **untracked scratch modules** inside this
worktree, each removed immediately (`git status --short` clean after each). **No
tracked source file was edited and reverted.**

### 1. Both edits are involutions — measured, not asserted in prose

Against a real captured outcome's bytes from the fixture deployment (1736
bytes):

```
--- _cross_the_echo ---
  once != original outcome : True
  twice == original outcome: True
  twice bytes == raw       : True
--- _alter_the_vessel ---
  once != original outcome : True
  twice == original outcome: True
  twice bytes == raw       : True
```

Applying either edit twice restores the producer's bytes **byte-for-byte**, and
applying it once never does. Task 3's control is unsound without this, so it
was measured before the control was written.

### 2. The identity edit — both legs, EVERY subject separately

The plan asked for a scratch copy of `suite.py` outside the tree. **A stronger
method was used**: each leg's edit was monkeypatched to the identity on the
**shipped** module and each leg was driven with **one subject at a time**, so
both transports were observed red rather than only the first one the loop
reaches. 4 of 4 combinations went red:

```
### assert_a_crossed_echo_is_caught / inprocess:
`inprocess` did not raise `TransportError` on a crossed echo — a served product
came back instead, so this transport's client accepted an answer to a question
nobody asked. …

### assert_a_crossed_echo_is_caught / mcp+stdio:
`mcp+stdio` did not raise `TransportError` on a crossed echo — …

### assert_an_altered_vessel_is_caught / inprocess:
`inprocess` did not raise `TransportError` on an altered vessel — a served
product came back instead, so this transport's client accepted bytes that do
not hash to the address their own producer claimed for them. …

### assert_an_altered_vessel_is_caught / mcp+stdio:
`mcp+stdio` did not raise `TransportError` on an altered vessel — …
```

### 3. The exact-type limb can fail, and was watched failing

A subject whose adapter cannot bind (its binding document deleted) raises
`BindingError`, which **subclasses** `TransportError`. A bare
`except TransportError` would have counted that as a caught tamper. Observed:

```
`unbindable` answered a crossed echo with a `BindingError` rather than a
`TransportError` itself — `BindingError` subclasses `TransportError`, so this
leg checks the exact type and refuses to count a connection failure as a
caught tamper
```

### 4. The controls themselves fail safe — and the limit where they do not

Holding `_cross_the_echo` to a **non-involutive** edit (suffix every time,
never strip), the shipped control went red:

```
### CONTROL WENT RED: AssertionError: Regex pattern did not match.
  Expected regex: 'did not raise `TransportError` on a crossed echo'
  Actual message: '`honest-under-the-crossing` raised `TransportError` on an
  UNTAMPERED wire asking the same question, so this leg never showed that the
  tamper is what was caught — a transport where everything raises would
  otherwise have passed the check above'
```

That also proves the control's `match=` is **load-bearing**: the leg still
failed, but on the *wrong limb*, and the control refused it.

**The honest limit, measured:** with `_cross_the_echo` held to the identity,
the control **still passes** — identity composed with identity is still the
identity. The plan's claim that an edit which "stops changing anything at all"
turns the control red is **false**, and the `_reversing_subject` docstring now
says so and names where that case *is* caught: sabotage 2 above, in the two
binding modules, for every subject.

## The control mechanism, in one sentence

**The subject applies the leg's own shipped edit, the leg applies it again, and
the two compose to the identity because the edit is an involution** — so the
client sees the producer's untouched bytes, does not raise, and the leg's
**first** limb fires.

Both controls import `_Tampering` and the two edit functions from `suite.py`
**by name** and re-implement nothing, per this module's own rule that *"a
control that tests a copy proves only that the copy fires"*. Each asserts on a
substring unique to the first limb **and** asserts the vacuity wording
(`everything raises`) is **absent**, so neither can pass because the wrong limb
failed. Observed first-limb messages, both naming their subject:

```
`honest-under-the-crossing` did not raise `TransportError` on a crossed echo — …
`honest-under-the-alteration` did not raise `TransportError` on an altered vessel — …
```

The rejected alternative — giving the legs an internal seam a control could
substitute — was rejected in planning and stayed rejected: a seam that exists
only so a control can reach through it is a second path into the leg.

## The type stand-in is checkable, and no limb is an identity assertion

`assert_wire_failure_parity`'s `type(broken) is type(healthy)` is real because
`break_transport` is an **independent** hook that could have returned another
type. A wrapper has no such independence, so the obvious stand-in — *"assert
the wrapper's inner adapter **is** the object `connect` returned"* — is a
tautology no implementation could fail. **It is not present in either leg.**

Instead each leg connects a **second, independent** adapter from the same
factory over its own provisioned root (`witness`) and asserts
`type(inner) is type(witness)`, naming both types on failure. Both docstrings
state in one sentence that this is **weaker** than the break-hook check and
why: there the two objects come from two independent hooks and the check
measures a damaged substrate; here they come from two calls to one hook, so
what is pinned is factory type-stability.

**Stated for the record, per the plan's instruction: no limb in either leg is
an identity assertion.** Every limb has a state of the world in which it fails,
and three of the four distinct limb kinds were watched failing above. The
fourth — the witness limb — is the one whose failing state this plan did **not**
construct, because manufacturing a factory whose return type depends on the
root would mean building a subject that exists for no other purpose. It is
recorded here as the one limb asserted rather than observed.

## The must-have truths, each verified

1. **Every registered subject is wrapped and must raise** — both legs are bound
   over `SUBJECTS` in both binding modules; `test_mcp_conformance.py`'s tuple
   carries the in-process subject too, so both calls there exercise both
   transports. 77 passed.
2. **The decorator is generic and transport-blind** — `_Tampering` names no
   transport, takes `TransportAdapter`, and returns `bytes`. `suite.py` imports
   nothing from `ccf.client.adapters`
   (`test_the_suite_imports_no_adapter` green).
3. **Per subject, never a comparison between two** — neither leg calls
   `_assert_views_agree` or builds a cross-subject view; each drives one
   subject at a time and was observed red with a **single** subject bound.
4. **Each leg carries its vacuity guard** — the untampered limb, driven against
   its own provisioned root, and a `TransportError` there is converted to an
   `AssertionError` naming *"a transport where everything raises"*.
5. **The EXACT `D-10` type** — `caught_the_wire_failure_itself = type(caught) is
   TransportError` in each leg, and observed catching a `BindingError` (sabotage
   3). `grep -c "is TransportError" suite.py` = **2**, one per leg.
6. **The stand-in can actually fail** — the witness form, above; the
   tautological form is absent.
7. **Each new leg has a `D-22` control** — two, in
   `test_the_suite_fires.py`, both watched failing on the first limb.
8. **`suite.py` names no transport, no product id, no parameter** —
   `grep -cE "inprocess|mcp\+stdio"` = **0**, `grep -cE
   "widgets-over-score|minimum_score"` = **0**; the AST neutrality assertions
   are green; `make lint` (no-hardcoding scoped over `tests/`) exits **0**.
9. **`assert_decision_instant_is_auditable` stays green over both subjects** —
   `-k decision_instant` 5 passed; the function is **byte-identical** to its
   pre-task form, confirmed by `git diff` showing no lines inside it (only its
   `__all__` entry appears, as context).
10. **Not in tension with `D-GATE-18`** — the arithmetic above: two call lines
    per module, no constant, no fixture, no question.

## Source assertions

| Assertion | Required | Measured |
|-----------|----------|----------|
| `grep -c "def assert_a_crossed_echo_is_caught\|def assert_an_altered_vessel_is_caught"` | 2 | **2** |
| both in `__all__` | yes | yes, alphabetical |
| `grep -c "encode_outcome" suite.py` | ≥ 1 | **3** |
| `grep -cE "json\.dumps" suite.py` | 0 | **0** |
| `grep -c "model_validate_json" suite.py` | ≥ 1 | **2**, each with an adjacent comment saying why not `decode_outcome` |
| `grep -cE "^[A-Z_]+: Final\[str\]" suite.py` | ≥ +2 | 1 → **4** (+3) |
| `grep -c "everything raises" suite.py` | ≥ 2 | **4** |
| `grep -c "is TransportError" suite.py` | ≥ +2 | 0 → **2** |
| `grep -c "witness" suite.py` | ≥ 2 | **6** |
| new constants in the binding modules | none | **none** |

## Verification

| Step | Result |
|------|--------|
| `make conformance` | **exit 0** — 77 passed |
| `pytest tests/client/conformance -q` | 77 passed, 0 failed |
| per-module counts | 10 / 10 / 48 |
| neutrality (`-k "no_registered_scheme or imports_no_adapter"`) | 2 passed |
| `P5` (`-k decision_instant`) | 5 passed, over both subjects |
| `make lint` | **exit 0** |
| `make typecheck` | **exit 0** — 211 source files |
| `make gate-tools` | exit 0 — 400 + 154 passed |
| `make ci-core` | **exit 0** |

## Deviations from Plan

### Where the plan was measurably wrong

**1. Task 1's "passes with no failures" criterion was unsatisfiable, and the
gate that made it so is a good gate.** Adding the two names to `suite.__all__`
immediately turned `test_the_suite_fires.py::test_every_exported_leg_has_a_control_here`
red — it holds `suite.__all__`'s `assert_*` names to the `LEG_CALLS` mapping,
and `LEG_CALLS` lives in Task 3's file, which Task 1 may not touch. Measured
after Task 1: **1 failed, 68 passed**, and the failure named both new legs as
*"extra items in the left set"*. This is that control doing exactly its job —
*a leg added to the suite without a control is a leg nobody has watched fail* —
so it was left red for one commit rather than defused, and Task 3 closed it.
The alternative (edit Task 3's file during Task 1) would have hidden the one
moment in this plan when the new legs genuinely had no control.

**2. The `pytest.raises(AssertionError)` count criterion assumed an idiom this
module abandoned before the phase started.** Task 3's criterion says the count
must increase by at least 2. Measured at base `8020d67`: the literal appears
**once**, inside the `_fails(reason)` helper, and `_fails(` appears **22**
times — every existing control uses it. Satisfying the criterion literally
would have meant writing two inline copies of `_fails`, which is the
copy-testing defect this module's own docstring forbids one scope over. The
substantive requirement is met: `_fails` **is**
`pytest.raises(AssertionError, match=reason)`, and each new control passes a
substring unique to its leg's first limb. `_fails(` went 22 → **24**.

**3. The plan's "fails safe" claim was half false, and the false half is
recorded in the code rather than in this document only.** The plan states that
if an edit *"stops being an involution — or stops changing anything at all"*
the control goes red. The first clause is true and was observed (sabotage 4).
The second is **false**: an identity edit composed with itself is still the
identity, and the control keeps passing — also observed. The
`_reversing_subject` docstring now states both, and names the two binding
modules as where the identity case is actually caught. Repeating the plan's
sentence would have shipped an unfalsifiable claim in the phase whose subject
is unfalsifiable claims.

**4. Task 2's scratch-copy method was replaced with something stronger.** The
plan asked for an identity edit in *"a scratch copy of `suite.py` outside the
tree"*. A copy proves the copy fires. Instead the **shipped** module's edit was
monkeypatched inside an untracked scratch test, so the leg under observation
was the one that ships — and it was driven one subject at a time so **both**
transports were observed red, which a copy driven over the pair would not have
shown (the loop raises at the first subject). No tracked file was edited.

**5. Line citations in the plan's `<read_first>` blocks were stale, as `19-02`
predicted.** `suite.py::assert_wire_failure_parity` is not at `:576-641`,
`codec.py::decode_outcome` is not at `:265-304`. Symbol names were all correct
and were what found the code. Recorded because `D-IMPL-114` already rules that
prose cites `path.py::Symbol`, and a plan citing line ranges is the same defect
one document over — this is the third consecutive plan in this phase to hit it.

### Rule 3 — auto-fixed blocking issues

**`[Rule 3 - Blocking]` `make gate-tools` refused a stale generated document.**

- **Found during:** the plan-level `make ci-core`.
- **Issue:** `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
  — `docs/surface/examples/RETIREMENT-COUPLINGS.md` was stale. This plan added
  an import line and two `__all__` entries near the top of `suite.py` and an
  import block to `test_the_suite_fires.py`, which shifted three citation line
  numbers the report records.
- **Fix:** `tools/retirement_sweep.py --report`. The diff is **exactly three
  rows** (`suite.py` 377→380 and 410→413, `test_the_suite_fires.py` 199→206);
  row count is unchanged at **234 rows across 75 files**, the same figure
  `19-02` recorded, so no record was dropped.
- **Commit:** `ad1a131`
- **Note for the merge:** this file is outside this plan's `files_modified`. It
  is a *generated* record that this plan's own line shifts invalidated, and
  leaving it stale means `ci-core` red. If `19-05` or `19-06` also shift
  citations they will regenerate the same file, and the merge should resolve by
  **re-running `tools/retirement_sweep.py --report` after the merge** rather
  than by picking a side — the file is derived, so any hand-merge is guesswork.

### Environment note for the orchestrator

The worktree has no `.venv`, and every `Makefile` target hard-codes
`.venv/bin/python`. A **symlink** `.venv -> /home/parkave/ccf_code/.venv` was
created in the worktree root so `make lint`, `make typecheck`, `make
conformance`, `make gate-tools` and `make ci-core` could run at all. It is
untracked and matched by `.gitignore` line 15, so it is not in any commit and
will disappear with the worktree. Imports were verified to resolve to the
**worktree's** `src/` and `runtime/`, not the main repo's, before anything was
measured.

### Not done, and deliberately

- **`suite.py` is untouched by Task 3** — `git diff --stat` for that task names
  only `test_the_suite_fires.py`.
- **No single-transport control was added.** That is `19-03`'s, and it is a
  different property: a leg here fails with `AssertionError`, while `19-03`'s
  controls raise `TransportError` from one `ProductClient`. Conflating them is
  `19-RESEARCH.md` Pitfall 5.
- **`.planning/STATE.md` and `.planning/ROADMAP.md` were NOT written**, per the
  orchestrator's standing instruction.
- **The witness limb was not driven to failure** — see *The type stand-in* above,
  where the omission is named rather than implied.

## Known Stubs

None. Every name added is read by an assertion; both edits are exercised by
both a bound leg and a control; `_Tampering`'s two members are both read on
every `ask`.

## Threat Flags

None beyond the plan's own `<threat_model>`. `T-19-12` is mitigated: the suite
wraps every registered subject and an adapter author writes nothing. `T-19-13`
is mitigated: each leg's untampered limb is present and each leg has a control
observed failing on its first limb. `T-19-14` holds: the neutrality assertions
are green and the crossed question is derived from the wire. `T-19-SC` holds —
this plan installed no package and added no dependency.

## Self-Check: PASSED

Modified files, all present:
- FOUND: `tests/client/conformance/suite.py`
- FOUND: `tests/client/conformance/test_inprocess_conformance.py`
- FOUND: `tests/client/conformance/test_mcp_conformance.py`
- FOUND: `tests/client/conformance/test_the_suite_fires.py`
- FOUND: `docs/surface/examples/RETIREMENT-COUPLINGS.md`

Commits (all present in `git log`):
- FOUND: `cbb37a7` `test(19-04): a generic byte-corrupting decorator, and two legs it feeds`
- FOUND: `7d6409e` `test(19-04): bind both tamper legs over every registered subject`
- FOUND: `86cf3cd` `test(19-04): a control per tamper leg — the reversing subject`
- FOUND: `ad1a131` `docs(19-04): refresh the retirement-couplings report after the suite grew`

Artifacts and key links (all matched):
- `suite.py` → `def assert_an_altered_vessel_is_caught` — 1 match
- `suite.py` → `encode_outcome` — 3 matches
- `test_inprocess_conformance.py` → `assert_a_crossed_echo_is_caught` — 1 match
- `test_mcp_conformance.py` → `assert_an_altered_vessel_is_caught` — 1 match
- `test_mcp_conformance.py` → `suite.assert_a` — 2 matches
- `test_the_suite_fires.py` → `honest` — 20 matches
