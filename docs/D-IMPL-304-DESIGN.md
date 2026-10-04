# D-IMPL-304 — design: a governed refusal must not escape as a runtime failure

**Status: design only (2026-09-18), awaiting the implementation GO. No SDK code, no
example code and no CP-14 assembly work in this package.** Baseline: `main @ c5aaba0d`
(the verified implementation baseline), state at `75377e11`. The decision of record is
`docs/DECISIONS.md` `D-IMPL-304` (2026-09-09, a carry). This document does what the
2026-09-18 instruction asked and nothing more: the precise path, the smallest correction
at the layer that owns the refusal, the tests and sabotages that keep genuine failures
distinct, the compatibility impact and the scoped verification plan.

## 1 · The decision and its two reproductions

`D-IMPL-304` records: over MCP, a malformed numeric value is judged **correctly** by the
SDK's request-contract machinery (`type-mismatch` naming the parameter, the declared
type and the presented type), but it arrives as a `RequestRefused` **exception**, which
the door reports as `ccf-runtime-failure` — no governed refusal envelope, **no replay
record**. The entry also records why it was carried rather than fixed: cp-05's low road
must resolve the effective request BEFORE acquisition (the walk cannot know its depth
until it knows what was effectively asked), and Dave ruled acquisition ordering out of
scope for that migration.

Two executable reproductions exist on `main`, and they are the design's controls:

| where | what it asserts today |
|---|---|
| `tests/examples/test_cp_05_mcp_door.py::test_a_malformed_number_is_judged_correctly_but_records_nothing` | the frozen specimen's OWN pre-`D-IMPL-340` door: a malformed `debt_tolerance` returns `ccf-runtime-failure`, and three calls leave exactly two decision records |
| `tests/examples/test_door_cp_05_exposure.py::test_a_pre_resolution_refusal_is_a_recorded_governed_refusal_not_a_runtime_failure` (at the design's date, `…_reads_as_a_runtime_failure_the_known_carry`; renamed by the implementation when it flipped) | the SDK's standard door over the wrapper adapter: `materiality` above the regime's policy ceiling reached the paved consumer as a row reading `producer-unavailable` with no child replay reference |

The second is the one that flips when the correction lands. The first is a statement
about a frozen tree's own door and stays true (§6).

## 2 · The precise path

Every hop, on `main @ c5aaba0d`, for the wrapper reproduction:

1. The consumer's child resolver calls the producer's MCP tool with the wire question.
2. The egress tool handler builds the typed `ProductRequest` verbatim from the wire and
   calls the resolver it was built with — `resolver(...)` at
   `runtime/ccf_runtime/mcp/egress.py::_answer_question`.
3. The resolver is the wrapper adapter's `resolve`
   (`examples/door-cp-05-credit-exposure-rollup/adapter.py::ExposureProducer.resolve`), which, after its own
   two recorded pre-assembly refusals and the instant guard, calls the frozen specimen's
   low road: `prod.produce_governed(...)` at `adapter.py:209`.
4. `produce_governed` (`examples/cp-05-credit-exposure-rollup/produce.py:136`) calls the
   specimen's `deployment.effective_request`, which assembles the four inputs from the
   specimen's documents and hands them to the SDK's own resolution seam —
   `resolve_effective_request` at `src/ccf/products/constraints.py::resolve_effective_request`.
5. That seam returns a `ResolutionOutcome` (`src/ccf/products/constraints.py::ResolutionOutcome`): a
   `refusal` — here a `ConstraintRefusal` (`src/ccf/products/constraints.py::ConstraintRefusal`)
   carrying the bound and its authority (`policy`) — **paired with the partial
   `EffectiveRequest` evidence** (`D-IMPL-264` D-07/D-08: what resolution established
   on the way to a refusal is dimension-2 evidence and must not be erased).
6. The frozen specimen converts that returned value into an exception:
   `raise RequestRefused(...)` at `produce.py:246`, a `ValueError` subclass
   (`produce.py:84`). The partial evidence is dropped at this hop: the exception
   carries `.refusal` only.
7. The exception propagates through the adapter untouched.
8. The door's failure clause catches it — `except (ValueError, TypeError, LookupError,
   OSError)` at `runtime/ccf_runtime/mcp/egress.py:1254` — and `_opaque_failure`
   (`runtime/ccf_runtime/mcp/egress.py::_opaque_failure`) logs it under a fresh id and raises
   `ToolError("ccf-runtime-failure:<id>")`. By that function's own docstring this is the
   right treatment for *"CCF or its runtime failed"*; it is the wrong treatment for a
   determination the fabric made.
9. The consumer's child resolver reads the tool error as the producer having given no
   governed answer and records the row as `producer-unavailable`
   (`src/ccf/products/child_resolver.py::GrantBoundChildResolver._admit`).

**The contrast that locates the gap.** The SDK's canonical resolver runs the same
resolution seam and, on a refusal, RECORDS it through the one recorder with
`resolution=` the partial evidence and returns the envelope as data
(`src/ccf/products/resolver.py::GovernedResolver._record_refusal` — the record call whose docstring quotes
`D-IMPL-264` amendment 1: no layer may manufacture the not-applicable marker from
omission). And the paved road resolves the effective request BEFORE it calls the
deployment's acquisition seam (`src/ccf/products/resolver.py::GovernedResolver.__call__`), so a paved product
never resolves by hand and never reaches this path.

**So, precisely, where the SDK gap is — and where it is not.**

- It is **not** in the resolution machinery: `resolve_effective_request` returns a
  refusal as a value, with its evidence, exactly as ruled.
- It is **not** in paved products: `open_product` deployments cannot hit it.
- It **is** in two SDK-owned places, both at the boundary where a governed determination
  is handed upward:
  1. **No typed channel for a raised governed refusal.** The door's contract with a
     resolver is: return a `ServedProduct` or a recorded `RefusalEnvelope`; raise for a
     fault. The only typed exception the door governs is `ProductNotServable`
     (`runtime/ccf_runtime/mcp/egress.py::ProductNotServable`, caught at `:1233` and turned into a
     recorded determination by `govern_absence` at
     `runtime/ccf_runtime/authz/delivery_boundary.py::govern_absence`). A low-road composition root
     or adapter that holds a refusal value in a place from which it cannot *return* it
     (inside a producer's own spine, as here) has no SDK-typed way to raise it that the
     door will recognize as governed.
  2. **The door's failure clause treats every `ValueError` as a fault.** That is the
     correct posture for arbitrary exceptions (`D-IMPL-253` Q20) and must stay; it is
     what makes item 1 the defect rather than the clause.

The layer that owns the refusal is therefore the **delivery boundary** — the same layer
that already owns the typed-absence conversion — and the correction is the same shape.

## 3 · The smallest correction, at that layer

### 3.1 One typed exception in the SDK (interface change)

Add to `ccf.products.refusal` (and its `__all__`):

```
class GovernedRefusalRaised(Exception):
    """A governed determination that could not be RETURNED from where it was made.

    Raised only by code that HOLDS a refusal value the fabric produced — a member
    of REFUSAL_KINDS or an envelope built from one — and the resolution evidence
    that accompanied it. Deliberately not a ValueError, TypeError, LookupError or
    OSError: a delivery boundary that catches those treats them as faults, and
    this type must never be mistaken for one. Nothing in the SDK raises it on a
    caller's behalf; raising it is an explicit statement.
    """
    refusal: RefusalKind | RefusalEnvelope
    resolution: EffectiveRequest | ResolutionNotApplicable
    request: RequestIdentity | None   # the pre-assembly identity, when the raiser holds it
```

`resolution` is **required**, in `D-IMPL-264` amendment 1's words: the raiser states
the effective (partial) resolution it holds, or the explicit not-applicable marker; no
layer manufactures the marker from omission. `ResolutionNotApplicable` already exists
(`src/ccf/replay/record.py::ResolutionNotApplicable`).

### 3.2 The door converts exactly that type, before its failure clause

In the egress tool handler, immediately before the generic clause at
`runtime/ccf_runtime/mcp/egress.py::_answer_question`:

```
except GovernedRefusalRaised as raised:
    resolved = govern_raised_refusal(   # delivery_boundary, beside govern_absence
        raised, tenant=..., product_class=..., product_version=..., parameters=asked.parameters,
        asked_at=asked_at, surface=surface, address=address, perspective=decided,
        entitlement_source=entitlement_source, refusal_recorder=recorder,
    )
    return door_answer(resolved, echo=question, resolved_request=asked, producer=producer)
```

`govern_raised_refusal` mirrors `govern_absence` line for line: build the envelope with
`envelope_for(raised.refusal, request=identity, provenance=<the evidence when it is an
EffectiveRequest>)` unless an envelope was raised; record it through the ONE recorder
(`ReplayRefusalRecorder.record`, `src/ccf/products/resolver.py:1107`) with
`recorded_at=asked.asked_at` — the question's instant, as the SDK's own pre-resolution
refusals are stamped — and `resolution=raised.resolution`; return what the recorder
returned. `door_answer` then delivers it through the one emission site, and the existing
guard in `door_refusal` (an envelope at `NO_REPLAY_REFERENCE` is refused as ungoverned)
stays the backstop.

**If recording fails, it is still a failure.** A store that raises inside
`govern_raised_refusal` propagates as it does today: *a failure to record is a failure to
serve*, and a refusal released without its record would be the repudiation the recorder
exists to prevent. The typed catch never produces an unrecorded refusal.

The MCP resource surfaces carry no question and are not in this path. The HTTP API
router (`runtime/ccf_runtime/http_api/`) is enumerated in §6 for the same catch if it
holds an equivalent generic clause; the reproduction is on the MCP tool.

### 3.3 The same channel at the in-process seam — proposed, separately adoptable

The paved road hands the deployment's `acquire(context)` the effective request and
nothing can refuse there today except by raising; `CP13C-F-03` records the covenant
successor's two acquisition exceptions (`UnknownCovenantSource`, `ScopeNotEntitled`)
propagating through `opened.answer` for exactly that reason. The same typed exception,
caught by `GovernedResolver` around the acquisition seam (`src/ccf/products/resolver.py::GovernedResolver.__call__`)
and recorded with `resolution=` the effective request it already holds, would give a
deployment a way to say *this is a refusal* from inside acquisition without the SDK
guessing.

**This is the one place I take a position for Dave to weigh.** The mechanism is the
same type and the same recording rule, so I would land the resolver-side catch in the
same change — one channel, two boundaries, no second vocabulary. What I would NOT do in
304 is change any deployment to raise it: the covenant successor's contract (an
exception, as the frozen specimen raised) was preserved by ruling, and converting it is
a business-meaning change for that product with its own ruling. If Dave prefers 304 to
be door-only, §3.3 is dropped without touching §3.1–3.2.

### 3.4 Adoption at the reproduction site — the wrapper, not the frozen tree

`examples/door-cp-05-credit-exposure-rollup/adapter.py` resolves the effective request
through the specimen's own `deployment.effective_request` BEFORE calling
`produce_governed`; on `outcome.refusal`, it raises
`GovernedRefusalRaised(refusal=outcome.refusal, resolution=outcome.evidence,
request=identity)` — dimension 2 then carries the partial resolution the SDK established,
which the frozen `RequestRefused` had dropped. On success the frozen tree resolves a
second time inside `produce_governed`; the duplication is deterministic (same inputs,
same seam) and is the measured cost of a wrapper over a frozen spine, recorded beside
`CP05D-F-01`. Frozen cp-05 is not edited; its own door keeps raising `ValueError`.

**What is explicitly not done.** No `except Exception`. No conversion of `ValueError`,
`TypeError`, `LookupError` or `OSError`. No reordering of acquisition. No change to
`REFUSAL_KINDS`, to `envelope_for`, to disclosure, or to any existing outcome kind.

## 4 · Tests and sabotages

### 4.1 SDK-level controls (no estate; fixture resolvers through `build_egress_server`)

| # | control | asserts |
|---|---|---|
| T1 | a fixture resolver raises `GovernedRefusalRaised(ConstraintRefusal(...), resolution=<partial EffectiveRequest>)` | the tool returns a governed refusal body (`refusal.kind == "constraint-refusal"`, the bound's authority in `fields`, a `replay_ref`); exactly ONE decision record appended; its dimension 2 carries the raised evidence, not the marker; `recorded_at` is the question's instant |
| T2 | the same with `resolution=ResolutionNotApplicable(...)` | recorded with the explicit marker; a raise with no `resolution` is refused at construction |
| T3 | the same with an already-recorded `RefusalEnvelope` | passed through, not re-recorded (one record) |
| T4 | **distinctness — programming failure**: a fixture resolver raises `TypeError` / a bare `ValueError` | `ccf-runtime-failure`; zero records |
| T5 | **distinctness — configuration failure**: the resolver raises `EnvironmentMissing` (`src/ccf/deployment/environment.py:99`, a `LookupError`) | `ccf-runtime-failure`; zero records |
| T6 | **distinctness — persistence failure**: the recorder's store raises `OSError` while recording a `GovernedRefusalRaised` | `ccf-runtime-failure`; no refusal crosses; zero records |
| T7 | **distinctness — transport failure**: the consumer's child resolver against a door that is not listening | `producer-unavailable`, as today; no governed row is invented |
| T8 | the typed absence (`ProductNotServable`) still governs as before | unchanged outcome |

### 4.2 Example-level proofs (estate)

| # | control | asserts |
|---|---|---|
| E1 | `test_door_cp_05_exposure.py`: the carry test becomes `…_is_a_recorded_governed_refusal` — `materiality="0.10"` under `internal-appetite` | the paved consumer's row reads `ineligible`, the retained detail names `constraint-refusal` with `authority: policy` and the ceiling; the producer's record exists in the wrapper's store with dimension 2 = the partial resolution; `producer-unavailable` does not appear |
| E2 | the four CP-14 slices, the covenant successor, the wrapper's other nine | unchanged counts (the memo never asks a materiality) |
| E3 | `tests/examples/test_cp_05_mcp_door.py` (env-gated, the FROZEN door) | unchanged: still `ccf-runtime-failure`, still two records — the frozen door predates the correction and is the specimen of the defect (§6) |

### 4.3 Sabotages, run by hand and restored

| sabotage | expected red |
|---|---|
| S1 — widen the door's typed catch to `except ValueError` | T4 (a programming failure becomes a governed refusal) |
| S2 — skip the recorder in `govern_raised_refusal` | T1 (no `replay_ref`) and the `door_refusal` guard raising `UngovernedResolverResult` |
| S3 — manufacture `ResolutionNotApplicable` when evidence was raised | T1's dimension-2 assertion |
| S4 — make `GovernedRefusalRaised` a `ValueError` subclass | T1 (it reaches the failure clause first) |
| S5 — in the adapter, raise on any `produce_governed` exception | E1 stays green but T4-shaped adapter control goes red (a wrapper must not broaden either) |

## 5 · Compatibility impact

- **Additive.** One new public name in `ccf.products.refusal`, one function in
  `ccf_runtime.authz.delivery_boundary`, one `except` clause per door. No existing
  return type, refusal kind, envelope field, disclosure rule or record field changes.
  The public-surface manifest gains one name (`make surface`).
- **Existing resolvers are unaffected**: nothing raises the new type unless it chooses
  to. The generic failure clause is unchanged in membership and position.
- **Consumers of adapters that adopt it** see a governed `ineligible` row with the
  producer's refusal identity where they saw `producer-unavailable`. That is the point,
  and it is a behavior change on the consumer's record for those producers only.
- **Frozen trees untouched**; the frozen cp-05 door's carry assertion stays a true
  statement about that door.
- **`D-IMPL-342` is not repaired here**: the per-row child reason and the child's replay
  reference remain 342's; 304 only makes the producer's own refusal a recorded
  determination on the producer's side and a governed row on the consumer's.
- **`D-IMPL-341` untouched.**

## 6 · Scoped verification plan

1. `tests/products/` and `tests/runtime/` unit controls T1–T8 (fixture door, no estate).
2. Sabotages S1–S5 run by hand on the candidate, restored by copy, recorded in the
   decision entry with what went red.
3. `tests/examples/test_door_cp_05_exposure.py` (E1 flipped; 10 tests), the four CP-14
   slices (27), `tests/examples/test_cp_13_canonical_output.py` (26), and the env-gated
   `tests/examples/test_cp_05_mcp_door.py` for the frozen door (unchanged) — against the
   estate.
4. `make lint` (citations included), `make typecheck`, `make surface` regenerated and
   its suites measured before and after by node id, `make product-gates`, the docs
   import gate.
5. The HTTP API router checked for an equivalent generic failure clause; if one exists,
   the same typed catch and a T1/T4 pair for that surface; if none, recorded as such.
6. Full suite: NOT part of this scoped plan; a claim about it needs a run.

## 7 · What this design does not do

No broadening of exception handling. No change to acquisition ordering. No edit to
frozen cp-05 or its tests. No implementation of the `F-35` ruling (tracked within 342).
No change to the covenant successor's exception contract. No CP-14 assembly work.

## 8 · Perspective, surfaced for the ruling

1. The escape is real, and it is the one an adopter hits only on the **low road** — a
   composition root or adapter that holds a refusal it cannot return. Paved products
   cannot reach it. The correction is worth making because the low road is a supported
   path and the door's failure contract is otherwise correct; it should not be read as a
   defect in the resolution machinery or the paved road.
2. I recommend landing §3.3 (the resolver-side catch around acquisition) in the same
   change as §3.1–3.2, without changing any deployment to use it. If the ruling is
   door-only, nothing in §3.1–3.2 changes.
3. The frozen cp-05 MCP test's docstring says a fix "must move" its assertion. It will
   not, because the frozen door is not corrected; the closure is proven on the SDK door
   with fixtures and on the wrapper against the estate. I propose stating that in 304's
   close rather than editing the frozen test.
