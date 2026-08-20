---
phase: 19
kind: close-fixes
status: complete
base: b1c40f4
head_at_write: pending
gate: "make ci exit 0 — 4013 passed / 118 skipped / 0 failed, 400 lint, 154 docs, three validation gates pass"
---

# Phase 19 — close-review fixes

What the §3.1 close process found after execution, and what was done about it.
Dave's ruling, 2026-08-20: **fix the existing gate, test-file only, no production
code**; also close `WR-02`/`WR-03`; `WR-04`/`WR-05`/`WR-06` ride along if cheap or
are deferred with a note.

## The blocking finding, and why it mattered

`C-17`'s AST gate was ruled to prove that no module under `src/ccf/client/adapters/`
constructs the outcome. It did not do that. `_outcome_construction_sites` matched only
an `ast.Call` on an import-bound `ast.Name`, or an `ast.Attribute` literally named
`WireOutcome`/`DoorOutcome`. **Three in-tree spellings scored zero**, and the first was
reproduced end-to-end by the orchestrator before any fix was written:

```
BEFORE
  C-17 counts:        {'forging_adapter.py': 0}
  C-17 gate VERDICT:  PASSES (no adapter constructs)
  client raised:      NO            <-- both integrity checks passed
  Result.expires_at:  2099-09-09    <-- the forged sentinel
  caller got the OTHER question's answer, undetected: True
```

An adapter spelling `WireOutcome.model_validate({...})` passed the gate, passed
`mypy --strict` (it does return `bytes`), and handed the caller another question's
vessel silently. **`B0` was re-openable in-tree with the entire build green** — the
phase's own defect, in the phase's own new gate.

`WR-01` compounded it: the shipped prose credited *"`19-04`'s conformance obligation"*
as covering the `model_copy` re-labelling gap. Verified false — the tamper legs wrap the
subject's adapter and measure **the client's** reaction to corruption, never the
adapter's honesty, and both legs pass against a forging adapter. There was no
compensating control.

## What was fixed

| Finding | Before | After | Observed failing? |
|---|---|---|---|
| `CR-01` pydantic construction spellings | 0 sites, gate passes | **1 site, gate FAILS** | yes, end-to-end |
| `CR-02` relative import (`from ..wire import …`) | 0 | **1** | yes |
| `CR-02` subclassing (`class Forged(WireOutcome)`) | 0 | **1** | yes |
| `WR-03` vacuous timestamp assertion | `isoformat()` `+00:00` vs canonical `…000000Z` — never present | compares `canonical_timestamp` | yes |
| `WR-02` address sabotage control | reported non-discriminating | fixed in the same pass | yes |
| `WR-06` refusal identity | reported as a defect | **measured and REJECTED**; both paths now asserted | n/a |
| `WR-05` leg-coverage docstring | claimed *"a leg nobody has watched fail"* | narrowed to what it holds | n/a (prose) |

**The subset decision.** `PYDANTIC_MODEL_FORMS` has thirteen members and three of them
(`model_dump`, `model_dump_json`, `model_json_schema`) serialize rather than construct —
a gate firing on those would be weakened by the next person it inconveniences. The fix
derives `_CONSTRUCTING_FORMS = PYDANTIC_MODEL_FORMS - _SERIALIZING_FORMS`, naming only
what it **excludes**, so a fourteenth spelling added to the canonical frozenset is
counted automatically. A hand-written positive list is the drift shape that produced
this defect.

**`WR-01` is resolved by the fix rather than by prose.** `model_copy` is in
`PYDANTIC_MODEL_FORMS`, so the re-labelling gap is now closed in-tree by the primary
control, and the sentence crediting an inert compensating control was replaced with a
true one.

**`WR-06` was rejected on measurement, not deferred.** `_answer`'s `resolved_request`
does contradict the refusal being rendered, but the envelope path never reads it —
`door_refusal` passes `RefusalEnvelope.request` through untouched — so the refusal names
the question that actually caused it. Both paths are now asserted, and the bare
`GateRefusal` path doubles as the vacuity guard for the envelope assertion, which reads
`parameters == {}` and would otherwise be satisfied by a member that is always empty.

## Deferred, with the note Dave's ruling asks for

**`WR-04` — the declared single-copy axis count is understated. NOT CHEAP; DEFERRED,
and it likely needs a ruling.** `runtime/ccf_runtime/mcp/egress.py` says `asked_at` is
*"a value with no second copy anywhere"* in a passage that reads as though it is the only
such axis. Verified: the MCP product tool takes whitepaper §6.3's **four** axes —
`subject`, `intent`, `freshness`, `asked_at` — while `ccf.products.door.WireRequest`
carries only `product_id`, `parameters` and `temporal_boundary`. So the first three cross
the pipe exactly once and are not echoed either.

This was not taken as a ride-along because it is **not a docstring fix**. It widens
`C-10`'s *undetected* list, which `D-IMPL-156` records as having been deliberately
cross-checked at **four** items between two records (`codec.py`'s shipped list and the
decision entry). Changing it means changing both records and the ruled count, which is a
claim change rather than a correction — the class of thing this project logs a `D-IMPL`
for rather than absorbing into a fix pass.

**What is NOT claimed here:** that altering `subject`, `intent` or `freshness` in transit
is exploitable. Only that the shipped prose names one single-copy axis where there are
four, and that the gap between those two statements is unrecorded.

## Discipline

- **Test files only.** `git diff --stat` across the fix commits touches
  `tests/client/test_surface.py`, `tests/products/test_door_answer.py` and
  `tests/client/conformance/test_the_suite_fires.py`. Nothing under `src/` or `runtime/`.
- **The executor stalled**, at 600s, *waiting on `make ci`* (~10.5 min) after reporting
  "both limbs observed failing". The tree was checked for an unrestored sabotage first —
  the real hazard when a sabotage-verifying agent dies mid-run — and was clean; the one
  uncommitted change was legitimate additive work, committed by the orchestrator.
- **A vacuity caught in the verification code itself.** The orchestrator's first probe of
  `CR-01`'s sibling finding was vacuous: its attack leg and control produced byte-identical
  subjects, so it proved nothing until rebuilt with distinguishable vessels. Recorded
  because it is the same defect class the phase is about, occurring in the code written
  to test the phase.
