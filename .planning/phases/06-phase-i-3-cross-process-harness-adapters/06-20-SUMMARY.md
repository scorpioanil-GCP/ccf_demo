---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 20
subsystem: harness-conformance
tags: [harness, portability, replay, gap-closure, B3]
requires:
  - tests/conformance/test_harness_adapter.py (HarnessLeg, World, _drive material, HARNESS_PARAMS)
  - src/ccf/harness/protocol.py (HarnessAdapterProtocol, EffectRefusal, HarnessCapabilities)
  - src/ccf/replay/record.py (HarnessTrace, NO_HARNESS, NO_HARNESS_TRACE)
provides:
  - an observed failure mode for the seam-3 emission equality
  - an observed failure mode for the seam-4 trace axis, on every leg
  - an explicit, B3-traceable scope statement in the suite's own module docstring
  - the residual over-claim, named verbatim for 06-22 to narrow in the documents
affects:
  - .planning/phases/06-.../06-22-PLAN.md (consumes the residual-clause record below)
tech-stack:
  added: []
  patterns:
    - adversarial-wrapper leg: a Protocol-conforming delegate that perturbs one seam value
    - inversion pair (positive + neutered), the test_agent_slice.py wired/unwired idiom
key-files:
  created: []
  modified:
    - tests/conformance/test_harness_portability.py
decisions:
  - the perturbation is applied at the adapter boundary, never by editing shipped adapter code
  - both perturbation sources are drawn from tests/fixtures/banking (CINV-01), asserted non-identity
  - option (i) of the B3 triage is taken, and is acceptable only with the structural-triviality sentence stated plainly
metrics:
  duration: ~35m
  completed: 2026-07-27
requirements: [XPRC-03]
---

# Phase 06 Plan 20: Harness Portability — Evidence for Finding B3 Summary

Adversarial harness legs give the portability suite's seam-3 and seam-4 equalities real failure modes, and the module now states in its own docstring that `_drive` calls the four seams directly with no harness reasoning loop — with the residual over-claim named rather than left implicit.

## What Changed

`tests/conformance/test_harness_portability.py` only. No `/src` or `/runtime` change, and no shipped adapter was edited — the plan's constraint was that the perturbation is applied to the value crossing the seam, not to the adapter producing it.

**The machinery.** `AdversarialAdapter` is a `HarnessAdapterProtocol`-conforming wrapper that delegates all four seams to a real adapter obtained from a real `HarnessLeg`, and corrupts exactly one value on the way through: the payload handed into `capture_effect` (seam 3), the `HarnessTrace` returned from `replay_trace` (seam 4), or the trace dropped to the `NO_HARNESS_TRACE` sentinel. `_adversarial_leg` wraps a real leg's adapter factory and leaves everything else on the leg — execution builder, reported values, refusal driver — untouched, so the adversarial run differs from the honest one in the perturbation and nothing else. Adversarial legs are driven through the existing `_drive`, so the corrupted value is observed by the same code path the honest legs use; a bespoke assertion beside the wrapper would have proven nothing about `_drive`.

**The assertions were factored, not duplicated.** `_assert_one_governed_emission` and `_assert_the_trace_is_the_harness_own` now carry the equalities the honest tests make, so the adversarial cases fail *those* assertions rather than a re-spelling of them. `test_the_governed_emission_is_identical_across_the_three_harnesses` and `test_the_harness_trace_is_isolated_and_differs_per_harness` were rewritten onto the shared helpers with no weakening — the trace helper is strictly stronger than what it replaced, because it now compares against the leg's own declared `reported_model` and `trace_id` (the bar `test_harness_adapter.py::test_seam_4_records_what_the_harness_reported` already sets per-leg) rather than only checking non-sentinel and per-harness distinctness.

**Test count.** Pre-change `grep -c "def test_"` = **10**. Post-change = **15** (+5, against a required +2). The five: the seam-3 inversion, the neutered-wrapper inversion, the conforming-adapter pin, the corrupted-trace case, the dropped-trace case.

## Tasks Completed

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 | Seam-3 emission equality gains an observed failure mode | `bd34919` (RED), `24dbddb` (GREEN) | tests/conformance/test_harness_portability.py |
| 2 | Seam-4 teeth on every leg, and a scope statement that matches what runs | `b2cddf1` (RED), `8f6e1b5` (GREEN) | tests/conformance/test_harness_portability.py |

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/conformance/test_harness_portability.py -q` | 15 passed |
| `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance -q -rs` | **193 passed, zero skips** (was 191) |
| `python -m tools.lints --all` | exit 0 |
| `pytest -q` (full suite) | **945 passed, 2 skipped** — the 940/2 baseline plus exactly the five new tests; no regression |
| `grep -c "no harness reasoning loop"` | 1 |
| `grep -c "example 03"` | 1 |
| `grep -c "B3"` | 8 |

**The neutering check, observed rather than asserted on paper.** `AdversarialAdapter.capture_effect` was temporarily reduced to a pure delegate (`return self._inner.capture_effect(agent=agent, output=dict(output))`) and the suite re-run. Observed failure:

```
tests/conformance/test_harness_portability.py::test_a_leg_that_corrupted_the_governed_emission_turns_the_equality_red
E       Failed: DID NOT RAISE AssertionError
1 failed, 12 passed
```

The perturbation was then restored and the suite returned to green. So the new inversion is sensitive to the perturbation itself, not to some incidental effect of wrapping.

**RED gates observed.** Task 1 RED: `NameError: name '_adversarial_leg' is not defined`, 2 failed / 10 passed. Task 2 RED: `NameError: name '_foreign_trace_values' is not defined` and `NameError: name '_assert_the_trace_is_the_harness_own' is not defined`, 2 failed / 13 passed.

## The Narrowing — for 06-22 to consume

### The structural-triviality sentence, verbatim

> **All three shipped adapters' `capture_effect` remain delegations to `Agent.emit_effect`, so the honest three-leg emission equality still cannot fail. The adversarial leg proves the assertion is sensitive to perturbation, not that the three adapters are independent implementations.**

This sentence is now in the module docstring and is repeated here verbatim per the plan. Option (i) of the B3 triage — raise the evidence rather than only narrow the wording — is acceptable *only* with it stated plainly, and both statements exist.

### What this evidence now supports

`docs/PHASE_I3_GATE.md` §3.3, the row reading:

> | Portability demonstrated, not asserted | `tests/conformance/test_harness_portability.py::test_the_consumed_product_is_byte_identical_across_the_three_harnesses`, `::test_the_governed_replay_fields_are_exactly_equal_across_harnesses`, … | An agent definition naming a harness; or a "portability" proof that compared nothing, which the exhaustiveness and two-agent tests are there to prevent |

The "compared nothing" hazard in that row's *What would fail* column is now fully closed: every equality the module asserts has a demonstrated failure mode, on all three axes rather than on the consumption axis alone. Similarly, ROADMAP criterion 3's clause:

> bind all four seams (context injection, skill exposure of exactly the currently-bound skill-set, effect capture with no harness write handle, replay hooks)

is supported — the four seams are bound, and each of the three compared axes can now go red.

### The clause this evidence still does not support, verbatim

ROADMAP criterion 3 does not itself claim loop execution, so the residual over-claim lives in the two places that do. Named verbatim for 06-22:

1. **`CLAUDE.md` §7.3, the bullet:**

   > **Portability is demonstrated, not asserted.** The examples suite (§9) must show one agent definition running unmodified under at least two harnesses, producing equivalent Context Product consumption and replay records.

   The clause **"running unmodified under at least two harnesses"** is still unsupported by this module: no harness loop executes here. What runs is four direct seam calls per leg. §7.3 assigns this obligation to the examples suite, which is Phase 8 — so the honest reading is that the obligation is *outstanding*, not that this module discharges it.

2. **`docs/PHASE_I3_GATE.md` §3.3, the row label** `Portability demonstrated, not asserted` — supported in its seam-translation reading, unsupported in its loop-execution reading. The row needs the distinction written into it; 06-22 owns that edit.

3. **The residual on the emission axis specifically:** the honest three-leg emission equality is **structurally guaranteed**, per the verbatim sentence above. Any document that reads it as three independent implementations agreeing is over-claiming. The defensible reading — and the one the docstring now states — is *"the fabric, not the harness, decides what an effect is."*

**Where the unproven half lands:** loop-level execution under two real harness loops is `examples/03-harness-portability`'s obligation in Phase 8 (D-06). The docstring names it so the stronger claim is handed on rather than quietly dropped.

## Deviations from Plan

None — the plan executed as written. Two notes, neither a deviation in substance:

- The plan's `must_haves.key_links` expects the adversarial leg to be linked to `runtime/ccf_runtime/adapters/*/adapter.py` "via `capture_effect`". Realized as intended: `AdversarialAdapter` holds a real adapter instance produced by `HarnessLeg.adapter(...)` — which is the shipped `ClaudeAgentAdapter` / `AdkAdapter` / `LangGraphAdapter` — and its own `capture_effect` calls that object's `capture_effect`. The link is by delegation at runtime, which is stronger than a source reference.
- The acceptance criterion asked for the pre- and post-change `grep -c "def test_"` counts; both are recorded above (10 → 15).

## Advisory A3 status (partial)

The plan's Task 2 context names advisory A3 — Claude's seam-4 `execution()` is a hand-built `ResultMessage` while ADK and LangGraph push values through real harness machinery. **A3 is not closed by this plan and is not claimed closed.** What changed is that the seam-4 axis no longer rests on that one fixture echo alone: the corrupted-trace and dropped-trace cases give the axis a failure mode that is independent of how any single leg's `execution()` is built, and the trace assertion now checks attribution against the leg's own declared values on all three legs. Replacing Claude's hand-built `ResultMessage` with a real SDK-driven execution remains open and belongs to whoever picks A3 up.

## Threat Register Disposition

| Threat ID | Disposition | Evidence |
|-----------|-------------|----------|
| T-06-87 | mitigated | `test_a_leg_that_corrupted_the_governed_emission_turns_the_equality_red` (seam 3) and `test_a_leg_that_corrupted_its_reported_trace_is_detected` (seam 4) — a corrupting adapter is detected through the same `_drive` the honest legs use |
| T-06-88 | mitigated | `test_a_dropped_harness_trace_is_caught_by_liveness_not_by_absence` — the sentinel equality is asserted *and* shown insufficient, which is why the helper asserts liveness |
| T-06-89 | mitigated | the corrupted-trace case asserts `_governed_fields` is **unchanged** under the corruption, so harness-attributable values provably did not reach a governed field |

No new threat surface: the change is test-only, adds no network path, no dependency, and no `/src` or `/runtime` code.

## Known Stubs

None.

## Self-Check: PASSED

- `tests/conformance/test_harness_portability.py` — FOUND (modified, 15 test functions)
- Commit `bd34919` — FOUND
- Commit `24dbddb` — FOUND
- Commit `b2cddf1` — FOUND
- Commit `8f6e1b5` — FOUND

## TDD Gate Compliance

Both tasks ran RED → GREEN with the gate commits in order: `test(06-20)` then `feat(06-20)` for task 1 (`bd34919` → `24dbddb`), and again for task 2 (`b2cddf1` → `8f6e1b5`). Each RED was observed failing for the intended reason (recorded above) before the corresponding GREEN. No REFACTOR commit was needed — the shared-helper extraction was part of each GREEN, since the point of extracting them was to give the adversarial cases something to invert.
