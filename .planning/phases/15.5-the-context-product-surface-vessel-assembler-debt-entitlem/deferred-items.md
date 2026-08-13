# Phase 15.5 — deferred items

Out-of-scope discoveries logged rather than fixed, per the executor scope
boundary (only issues *directly caused by* a task's own changes are auto-fixed).

---

## Dispositions at phase close (plan `15.5-14`, 2026-08-11)

Every entry has one. None is carried into Phase 16 without a stated owner.

| Entry | Disposition |
|---|---|
| `DI-15.5-01` | **OPEN — handed to the Phase 17 perf pass**, with `DI-15.5-04`. Ruled below rather than left unassigned |
| `DI-15.5-02` | **CLOSED** by plan `15.5-13` — `make example-s1-01` exists (`Makefile:89`) and leads the eleven-member `examples:` aggregate |
| `DI-15.5-03` | **CLOSED** by plan `15.5-15` (`D-IMPL-108`), commit `c244400` |
| `DI-15.5-04` | **OPEN — Phase 17 perf pass**, per Dave's 2026-08-11 ruling. Unchanged |
| `DI-15.5-05` | **CLOSED** by plan `15.6-09` (`D-IMPL-121`, Dave, 2026-08-12) — `D-IMPL-113` extends to `refuse_request`; the seam obligation is discharged and asserted. **Its recorded population was WRONG WHEN WRITTEN, not stale**; corrected in place below |
| `DI-15.5-06` | **SCOPED** by plan `15.6-09` (`D-IMPL-122`, Dave, 2026-08-12) and owned by plan `15.6-10`: frozen baseline stays frozen, `__call__`-only capture, type aliases in scope. **The measured inventory did NOT stand** — re-measured at `4b407e0` as 80/34/56 against the recorded 56/30/54, and the `__call__` fix reaches 12 of 51 Protocols rather than *"every Protocol entry"*. **39 multi-method Protocols stay information-free, descoped with reason** |
| `DI-15.5-07` | **CLOSED** by plan `15.5-13`'s continuation (`D-IMPL-111`, both limbs) |
| `DI-15.5-08` | **SCOPED** by plan `15.6-09` (`D-IMPL-123`, Dave, 2026-08-12) and owned by plan `15.6-11`: sweep 101 of the 114 unanchored `.py`-target citations, holding back the 13 in the records `D-IMPL-114` names. Re-measured at `4b407e0`; the carried figure of 125 across 31 files was 114 across 27 |

### `DI-15.5-01` — the ruling

**Handed to the Phase 17 perf pass, jointly with `DI-15.5-04`.** Not retained
by this plan, and the reasoning is on the record rather than a shrug.

Measured at phase close, `make perf-micro` **exits 0** and all twelve
benchmarks PASS:

| Benchmark | Median | Baseline | Δ | At phase base |
|---|---|---|---|---|
| `test_dispatch.py::test_run_coroutine_sync_overhead` | 2.95531e-05 s | 2.928e-05 s | **+0.93%** | +11.48% |
| `test_operators.py::test_composed_chain` | 0.375303 s | 0.368903 s | **+1.73%** | +231.87% |

`test_composed_chain` was **fixed in-phase** under `D-IMPL-107` — a real
regression, really repaired. `test_run_coroutine_sync_overhead` was never a
regression: it swung from +11.48% to +0.93% with no change to the code it
measures, which is the definition of a benchmark whose variance exceeds its
band. That is a **PERF-04 re-baseline-or-widen decision**, owned by whoever
runs the battery on the machine of record, and it is not a Context Product
question. Both remaining items — this and `DI-15.5-04`'s unconditional
`IntermediateCache` hash — are perf-pass work against the same
machine-specific `perf/baselines/local.json`, so they travel together.

The contradiction the orchestrator recorded at wave-1 close — that `15.5-07`
and `15.5-09` put `make perf-micro` inside `<automated>` blocks requiring
exit 0 while their prose permitted recording an excess — **dissolved rather
than being resolved**: the gate is green, so both readings agree. No
re-baseline was performed, which both plans forbade.

### `DI-15.5-08` — the ruling

**Put to Dave as gate residual R3.** Both available remedies are decisions, not
fixes: widen `cite02-anchor` to verify bare `path:START-END` ranges (which
requires the checker to know what a range is *supposed* to contain — the reason
it does not today), or rule that prose cites `path::Symbol` and stop citing
ranges at all. An executor picking one at phase close would be choosing a
project-wide citation convention on Dave's behalf.

The three stale citations of `src/ccf/replay/engine.py:449-455` (now `:472-477`)
in `docs/DECISIONS.md` (D-IMPL-100), `docs/SURFACE-CHANGES.md` and
`docs/surface-changes/15.5-11-debt-delivery.md` are **deliberately still
stale**: an append-only ruling record, a generated artifact, and a landed
plan's historical fragment. Editing any of the three to chase a line number is
the failure mode, not the repair. A fourth instance of the same rot was
observed at this close and is on the record — `tools/retirement_sweep.py`
reported `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md` moving from line 161 to 162,
where nothing about the citation changed except what was above it.

---

## DI-15.5-05 — two binder refusals ship with no calling code path

**Found during:** the phase-close cross-AI panel (plan `15.5-14`), independently
by two reviewers (`15.5-CLOSE-REVIEWS.md`, findings P3, C1 and C3). Written at
close because the entry number was referenced in the phase's handoff notes and
no entry existed behind it.

> **CORRECTED 2026-08-12 by plan `15.6-09`. The table below was WRONG WHEN
> WRITTEN, not stale by drift, and it is corrected visibly rather than
> replaced — the original claim stays legible because the process finding is
> the useful part.** Read the correction block after the table before using
> any figure here. **Disposition: RULED — `D-IMPL-121` (Dave, 2026-08-12),**
> extending `D-IMPL-113` to `refuse_request`. This entry is CLOSED.

**What.** Two shipped refusal functions have no caller on any shipped delivery
path:

| Function | Shipped at | Callers outside its own tests |
|---|---|---|
| `refuse_bound_payload` | `src/ccf/products/bind.py:145` | **one** — `examples/04-cross-process/producer_child.py:697`. Zero in `runtime/` |
| `refuse_request` | `src/ccf/products/request.py:404` | **zero**. Its docstring at `:408-415` says *"Called by the door"* |

### The correction, re-measured at `4b407e0` (plan `15.6-09`)

**The population, as it stands in the tree.** Measured by `git grep` across
`src runtime tests examples tools perf`, hand-classified into *invocation*
versus *mention*:

| Function | Defined at | Invocations outside its own tests | Invocations in `runtime/` |
|---|---|---|---|
| `refuse_bound_payload` | `src/ccf/products/bind.py::refuse_bound_payload` | **one** — `examples/04-cross-process/producer_child.py::resolve` | **zero** |
| `refuse_request` | `src/ccf/products/request.py::refuse_request` | **one** — `examples/s1-01-hello-context-product/spine.py::assemble_and_serve` | **zero** |

The correct statement is narrower than the original table and narrower than
the phrase *"no caller on any shipped delivery path"*: **no `runtime/` door
calls either function; one shipped, CI-run example calls each.** Under
`D-IMPL-121` those two call sites are the ruling's worked demonstration, not
counterexamples to it.

**Correction 1 — `refuse_request`'s "zero" was false at the moment it was
written, and git says so.** The call site landed in commit `e4db82c` at
**2026-08-11 11:46:21 -0700** (*feat(15.5-13): the subject and both instants
become request arguments*). The entry claiming zero landed in commit `9fd6c12`
at **2026-08-11 20:54:59 -0700** (*docs(15.5-14): give every deferred item a
disposition, and write the missing DI-15.5-05*). The gap is **9 h 08 m 38 s,
the same day, inside the same phase.**

**Why that distinction is recorded rather than quietly fixed.** Drift is
normal, expected, and is what `D-IMPL-114` addresses. A figure that was
**false when authored** is a different thing: it means the close-time sweep
recorded a population it had not measured against the tree it was closing, and
any plan built on the figure re-commits the error. Phase 15.6 exists partly to
close defects of this class, and this is its cleanest specimen.

**Correction 2 — two of this entry's own line anchors have rotted, which is
`DI-15.5-08` demonstrated inside `DI-15.5-05`.** Measured at `4b407e0`:

| Cited above as | Where it actually is | Drift |
|---|---|---|
| `bind.py:145` | `src/ccf/products/bind.py::refuse_bound_payload` begins at line 164 | the lines have since moved by 19 |
| `contract.py:662-664` (the wired sibling) | the call in `src/ccf/products/contract.py::register_product_class` is at lines 753-755 | the lines have since moved by 91 |
| `request.py:404` | still accurate | none |
| `runtime/ccf_runtime/http_api/routes/product.py:323-331` | still accurate — `ProductRequest(` at `:323`, `parameters={}` at `:330` | none |

The `refuse_request` docstring cited above as `:408-415` — *"Called by the
door"* — was **false as written** and has been corrected under `D-IMPL-121` to
say what is true: it is called by the deployment's own resolver.

**The disposition.** `D-IMPL-121` (Dave, 2026-08-12) extends `D-IMPL-113` to
`refuse_request`: both request-time refusals are adopter obligations the SDK
states **at the seam** and does not enforce. The obligation `D-IMPL-113`
created — and which, measured at `4b407e0`, was still entirely undischarged,
since `git grep` for either refusal name across all of `runtime/` returned
**zero hits of any kind** — is now discharged at both
`runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol` and
`runtime/ccf_runtime/mcp/experience.py::ExperienceProductResolverProtocol`,
and asserted by `tools/docs_tests/test_resolver_seam_obligations.py`.
`CPS-03` remains **Pending by design** and its row now names both rulings.

Concretely: `runtime/ccf_runtime/http_api/routes/product.py:323-331` builds a
`ProductRequest` with `parameters={}` unconditionally, so a class whose request
contract declares required parameters crosses that door with an empty parameter
map and never meets the conformity function. The reference MCP egress child
runs `run_gates` and returns the `ServableProduct` with no bind call, and
`examples/s1-01-hello-context-product/` names neither bind nor a payload
schema. Example 04 records the gap in its own comment:
*"`refuse_bound_payload`, shipped unwired by plan `15.5-09`"*.

Its sibling leg **is** wired: `refuse_request_contract_pin`, the
*registration-time* check, is called at `src/ccf/products/contract.py:662-664`.
The unwired legs are request-time only.

**Why it is deferred rather than fixed.** The placement is `D-IMPL-102`'s and
is stated deliberately in `bind.py:40-48` — the module *"takes neither a
request nor a door"* and the join is *"one call from the bound path"*, i.e. the
deployment's own assembler. Wiring it into the three SDK doors makes each door
resolve a `RegisteredProductClass` per serve and render a new refusal, and puts
a **deployment-declared** verdict inside the SDK's delivery path, which is
adjacent to the line limb 3 draws ("no fourth gate"; `run_gates` stays
structural because every one of its verdicts depends only on the product's own
shape). That is a design decision with Dave's name on it, not an executor's
auto-fix.

**Why it matters anyway.** This is convention-not-enforcement, and it is the
**second instance of that class Phase 16 already carries**. A declared payload
schema that nothing on a shipped path checks is indistinguishable, from an
adopter's seat, from no schema at all — and `CPS-03`'s second clause ("a
payload violating that declaration **is refused**") is left **Pending** at
phase close because of it.

**Owner:** Dave, at the Phase 15.5 gate — residual R1. The question is narrow:
does a shipped door call the bind, or is the bind an adopter's obligation the
SDK documents and does not enforce? Either answer closes it; the current state
is neither.

## DI-15.5-01 — `make perf-micro` gate is red at the phase's base commit

**Found during:** plan `15.5-01`, task 2 (assumption A8, the pre-change perf
baseline).
**Discovered at:** `3df4e91` (`chore(15.5): mark phase execution started`), on a
worktree that changed no `src/`, `runtime/` or `perf/` file.

`make perf-micro CCF_PERF_RUNNER_CLASS=local` exits 1. Two benchmarks fail
against `perf/baselines/local.json`, and **neither is on the Context Product
surface**:

| Benchmark | Median | Baseline | Δ | Band |
|---|---|---|---|---|
| `suites/micro/test_dispatch.py::test_run_coroutine_sync_overhead` | 3.264e-05 s | 2.928e-05 s | **+11.48%** | 10% |
| `suites/micro/test_operators.py::test_composed_chain` | 1.22429 s | 0.368903 s | **+231.87%** | 10% |

All three `test_gates.py` benchmarks — the ones a fourth validation gate or a
new vessel field would move — **PASS** with headroom (see
`docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md` § Q5/A8).

**Why it is deferred rather than fixed:** the `local` runner-class baseline is a
machine-specific committed artifact (`perf/baselines/local.json`), and
re-baselining it is a reviewed event under PERF-04 owned by whoever runs the
battery on the machine of record. Plan `15.5-01` is forbidden to touch `src/`,
`runtime/` or `examples/`, changed no operator, and did not cause either
regression.

**Consequence the phase must carry:** plans `15.5-07` and `15.5-09` are
instructed to measure their post-field / post-gate medians against this
baseline. They must read the *per-benchmark* verdicts for
`suites/micro/test_gates.py::*` rather than the gate's exit code, because the
exit code is already 1 for reasons that predate the phase. A plan that treats
`make perf-micro` exiting 0 as its acceptance criterion will never pass on this
machine.

**Verified by the orchestrator at wave-1 close:** both `15.5-07` and `15.5-09`
carry `make perf-micro` *inside* their `<automated>` verification blocks, which
require exit 0, while their prose success criteria permit recording and
escalating an excess. The two readings contradict each other. Carried into the
`15.5-05` ruling package rather than resolved by re-baselining, because both
plans explicitly forbid a silent re-baseline.

**Owner:** unassigned. Candidate: plan `15.5-14`'s close-out sweep, which
already owns the retirement decision for the `15.5-01` spike module.

## DI-15.5-02 — `make example-s1-01` does not exist

- **Found during:** plan `15.5-04`, task 1 (reading the example's docstrings).
- **What:** `examples/s1-01-hello-context-product/run.py` tells the reader to
  run the example with `make example-s1-01`, and plan `15.5-13`'s checkpoint
  task 4 uses `make example-s1-01` as its automated verification. No such target
  exists in the `Makefile` — `grep -n "s1" Makefile` returns nothing. The
  aggregate `examples` target (`example-00` … `example-08`, `example-ext-00`)
  does not include `s1-01` either, so the example runs in no CI job.
- **Why deferred:** adding the target and wiring it into `examples` changes what
  `make ci` runs, which is outside plan `15.5-04`'s three-file scope (an example
  added to the always-on aggregate is a CI-surface change, not a deletion).
- **Owner:** plan `15.5-13` rewrites this example and needs the target for its
  own verification step; it is the natural place to add it. If `15.5-13` is
  descoped, this becomes a phase-close finding.

## DI-15.5-03 — the entitled `Perspective` stops at the door

- **Found during:** plan `15.5-06`, tasks 1 and 3.
- **What:** all three exposed product doors now resolve a `Perspective` from
  the verified grant and refuse a caller not entitled to the requested class or
  to that role. What they do **not** do is forward the resolved perspective
  into the assemble-and-gate path: `ProductResolverProtocol` and
  `ExperienceProductResolverProtocol` are three-string seams
  (`tenant, product_class, version`), so the deployment's resolver constructs
  its own `Perspective` behind them. The door therefore guarantees the
  *refusal* leg but not that the served product was shaped under the
  perspective the door authorized.
- **Why deferred:** closing it reshapes both resolver Protocols to carry a
  `Perspective`, which touches `ApiDependencies`, `runtime/ccf_runtime/cli/local.py`,
  three doors, two crossproc test children, three examples and the HTTP test
  fixtures — roughly twenty call sites. Plan `15.5-06` does not scope it: its
  own `<interfaces>` block quotes the resolver seam unchanged at all three
  doors, and its success criterion ("Perspective is derived from the verified
  grant and never asserted by the caller") is met by the door-side resolution
  and refusal. Doing it inside `15.5-06` would also have collided with the
  `perspective`-shaped work in sibling wave-2 plans.
- **Where it is recorded in code:** the `context_product` handler docstrings in
  `runtime/ccf_runtime/mcp/egress.py` and `runtime/ccf_runtime/mcp/experience.py`
  both state where the value stops and why.
- **Owner:** **CLOSED AS UNOWNED — now owned by plan `15.5-15`** (`D-IMPL-108`,
  Dave, 2026-08-11). The seam is widened exactly once, carrying both the typed
  request contract and the authorized `Perspective`, rather than being reshaped
  twice. Dave named this *"the highest-priority structural debt for the later
  waves"* on 2026-08-11.
- **STATUS: CLOSED** by plan `15.5-15`, closing commit `c244400`
  (`feat(15.5-15): widen the product resolver seam once, carrying perspective
  and request`), with the supplying call sites in `685cbf0` and the structural
  assertions in `74ab80b`.

  What closed it, in the order the assertions run:

  1. Both Protocols carry `perspective: Perspective` and
     `request: ProductRequest | None`, keyword-only and **neither defaulted**.
     A default would have recreated the ambiguity one layer down — a resolver
     handed nothing and constructing its own is indistinguishable from one
     honouring the door's — so the seam requires the value.
  2. All three doors bind what `entitled_perspective` returns and pass it.
     `tests/invariants/test_mcp_role_separation.py` walks each door's AST for
     the shipped defect's exact shape (a bare `entitled_perspective(...)`
     expression statement) and fails on it.
  3. The property is asserted **by value**, not by parameter: the authenticated
     egress server is stood up in process, one product is read as a verified
     and entitled caller, and what the resolver received is compared against
     what that deployment's perspective seam returned for that grant. A test
     that only checked the parameter existed would have passed against a door
     forwarding a freshly-constructed perspective, which is a different
     security property and identical in every byte a consumer sees.

  One behaviour change rode with it and is **not** a side effect but the
  deferred item's own consequence: the HTTP door in the ungoverned posture can
  name no perspective, so it refuses (503, `product-door-ungoverned`) rather
  than serving. See `docs/surface-changes/15.5-15-resolver-seam.md` for the
  trade and the two-line restoration. This supersedes T-07-24's preservation of
  that posture and **wants Dave's ruling at the phase gate**.

## DI-15.5-04 — `IntermediateCache` computes a key for a cache that cannot hit

- **Found during:** the `D-IMPL-107` perf investigation (wave 3), while profiling
  `perf/suites/micro/test_operators.py::test_composed_chain`.
- **What:** `ProjectionEngine.execute` invokes each operator key **exactly once**,
  so `IntermediateCache` can never hit — the cache is unreachable *by
  construction*, not by configuration. Yet `IntermediateCache.run` computes
  `content_hash(view)` on **every** invocation purely to build the lookup key.
  Measured at roughly **0.20 s of the benchmark's remaining 0.41 s** — about half
  the remaining time, spent constructing a key nothing will ever look up.
- **Why deferred (Dave's ruling, 2026-08-11):** making the hash lazy is
  behaviour-identical and the win is real, but the key's composition is
  `D-IMPL-36`'s and is documented as *"everything `Operator.apply` can observe"*.
  Narrowing **when** that key is computed is still a change to a ruled contract
  even though the final value is identical. Nothing in Phase 15.5 depends on the
  performance win, and `make perf-micro` is green as of wave 3. Taking it now
  would be an unnecessary mid-phase edit to a ruled surface.
- **The two facts a later reader needs:** the cache is currently **unreachable by
  construction**, and the hash is computed **unconditionally**. Either could
  change independently — if a future engine change makes the cache reachable, the
  unconditional hash stops being waste and this entry stops applying.
- **Owner:** a later performance pass. Low risk, well bounded, explicitly not
  Phase 15.5's.

## DI-15.5-06 — the drift manifest cannot see a call-Protocol's signature

- **Found during:** plan `15.5-15`, task 4, while classifying the two widened
  resolver seams in `docs/surface-changes/15.5-15-resolver-seam.md`.
- **What:** `tools/dump_surface.py` records a `Protocol` class as
  `{"kind": "class", "shape": "(*args, **kwargs)"}` — that is its `__init__`,
  and every `Protocol` in the tree shares it. The `__call__` member is never
  captured. So **no change to a call-Protocol's signature can produce a
  manifest diff line**, and the D-15 drift gate that exists to make a reshaped
  export reviewable is structurally blind to the one shape whose entire public
  contract lives in that member.

  This is not hypothetical: `ProductResolverProtocol` and
  `ExperienceProductResolverProtocol` went from three arguments to five in this
  plan, a breaking change for every adopter supplying a resolver, and the
  manifest is byte-identical across it. The same is true of every
  `…Protocol` this SDK ships as a seam — `PerspectiveResolverProtocol`,
  `HarnessAdapterProtocol`, `ArtifactStoreProtocol`, `WireProtocol` — which is
  most of the pluggable surface CLAUDE.md §11 says to prefer Protocols for.
- **Consequence already visible in the record:** two entries in this plan's
  fragment are classified `Change type: behavior` where `reshaped` is the
  truthful word, because `reshaped` is unrepresentable for a name the manifest
  never moves and fails `tests/test_surface_completeness.py`. Plan `15.5-11`
  hit the same wall for `ReplayEnvironment` and made the same choice. Two plans
  reaching for the exempt class to describe a signature change is the signal.
- **Why deferred:** teaching `dump_surface.py` to record `__call__` for
  `Protocol` subclasses would move **every** Protocol entry in
  `docs/surface/v0.2-surface.json` in one commit, which is a drift-gate event
  of its own and would collide with the concurrent wave-5 plans. It also needs
  a ruling on whether the frozen Phase-15 baseline is rewritten or the diff
  reconciled, the same question `test_every_public_log_entry_has_a_matching_diff_line`
  already carries one narrow reconciliation for.
- **Owner:** **PHASE 17** (`D-IMPL-110`, Dave, 2026-08-11). Recorded as debt
  rather than fixed in 15.5, on the grounds that the blind spot predates this
  phase and was not caused by it. What this plan did instead is pin the two
  seams with a dedicated invariant
  (`tests/invariants/test_mcp_role_separation.py`), which is a per-seam
  substitute for a gate and does not generalize.

- **Measured inventory, taken by the orchestrator at `4d16cb9`** so Phase 17
  inherits a number rather than an impression. Verified independently against
  `docs/surface/v0.2-surface.json`, not accepted on the plan's report:

  | Measure | Count |
  |---|---|
  | Manifest entries recording `"(*args, **kwargs)"` | **56** |
  | …of which are named `*Protocol` | **30** |
  | Total `Protocol` classes across `src/` + `runtime/` | **54** |

  Confirmed blind, by name: `ArtifactStoreProtocol`, `ControlPlaneProtocol`,
  `HarnessAdapterProtocol`, `OrchestrationProtocol`, `HITLTransportProtocol`,
  `WebhookDeliveryProtocol`, `LLMClientProtocol`, `DebtFactorScorerProtocol`,
  plus the two resolver seams and `ReplayEnvironment`.

- **The two consequences of deferring, recorded so they are not rediscovered:**
  1. **Phase 15.5 ships a breaking Protocol change its own drift gate cannot
     see.** The surface manifest is therefore *not* evidence of surface
     stability for this phase and must not be cited as such at the gate.
  2. **The `behavior`-instead-of-`reshaped` classification stands as
     precedent.** A later author reading the `15.5-11` and `15.5-15` fragments
     will reasonably copy it. Phase 17 should expect to reclassify both entries
     once the tooling can see them.

- **Recommendation on record:** the orchestrator recommended fixing in-phase via
  `15.5-14`, which already owns the surface-manifest sweep. Dave ruled defer.
  The recommendation is preserved rather than dropped, per `D-IMPL-110`.

## DI-15.5-02 — CLOSED by plan `15.5-13`

`make example-s1-01` now exists (`Makefile:89`) and leads the `examples:`
aggregate, so the example runs in CI. This **changes what `make ci` runs**,
which was the reason `15.5-04` deferred it rather than a side effect discovered
afterwards. `make examples` exits 0 with the new member; verified 2026-08-11.

## DI-15.5-07 — CLOSED by plan `15.5-13`'s continuation (`20fff85`, `956abed`)

Ruled as **D-IMPL-111** (Dave, 2026-08-11), **both limbs**, and both landed.

- **Limb (a)** — `ProjectionEngine.execute` gained `seeds`, threaded to every
  pushable segment carrying a traverse family, and the s1-01 spine passes
  `request_seeds(request)`. Questions 1 and 2 now pin **differently**; their
  first pin is still shared, because that segment carries no walk for an anchor
  to start (`GQ-03`). All four property suites green, unweakened.
- **Limb (b)** — `ContentGenerationPath.request` carries the
  `ProductRequest` verbatim on dimension 5, so `intent` and `freshness` are
  recorded rather than absent. 0 forced repairs across 32 call sites in 28
  files, under the positive sentinel.
- **The two are one mechanism.** Limb (a) makes the pins depend on the
  question, which makes them unreproducible unless replay can re-derive the
  seeds; limb (b) is what lets it, through the same `request_seeds` reading.
- **The record content address moved** and is proven reconstructible on the real
  serve path after four months of later state
  (`tests/replay/test_engine_rehydration.py::test_the_question_the_decision_answered_replays_byte_exactly`),
  with an adversarial twin that diverges when the recorded subject is swapped.
  One recorded address regenerated: `examples/08-e2e-demo/artifacts/expected_output.txt`.
- **The guard was inverted, not deleted.** The test that failed loudly if
  questions 1 and 2 ever stopped pinning alike now fails loudly if they ever
  start again, and its README caveat is corrected.

The original entry follows, unedited, because what it recorded was true when it
was recorded and the ruling exists because of it.

## DI-15.5-07 (original entry) — the replay record pins the graph question, not the product question

- **Found during:** plan `15.5-13`, task 2 (writing the two-subject pin
  assertion the plan's `<behavior>` block asked for, and finding it false).
- **What:** the plan's second behaviour reads *"Two different subjects produce
  two different pinned query sequences — the pin distinguishes the questions
  rather than the answers."* Measured, it does not. Questions 1 and 2 of
  `examples/s1-01-hello-context-product/artifacts/questions.yaml` differ only in
  subject and pin **identically**, because the subject enters at Π and is not
  compiled into the graph query — `compile_segment_query` is called with
  `seeds=None`, so both questions read the same typed neighbourhood and differ
  only in what is projected out of it. Two different *instants* do pin
  differently, because the boundary is inside the compiled query.
- **Consequence:** `ContentGenerationPath.graph_query_sequence` answers *"what
  did this decision ask the graph?"*. It does not answer *"which question did
  this decision answer?"* — the `ProductRequest` is not carried in any of the
  five dimensions. The product question is *recoverable* (the served payload
  names its subject and dimension 1 carries the boundary) but the request's
  `intent` and `freshness` are recorded nowhere, and recovery-by-inference is
  not the same property as a pin.
- **Why not fixed here:** two candidate fixes and both are out of this plan's
  scope. (a) Seed the traversal from the request's subject, which is an operator
  and query-compilation change with composition-preservation consequences.
  (b) Carry the `ProductRequest` into the replay record, which is a
  five-dimension shape change and therefore a `D-IMPL` ruling, not an executor's
  call (CLAUDE.md §11, *surface gaps; do not paper over them*).
- **What plan `15.5-13` did instead:** asserted what is true and said why in the
  test itself
  (`tests/examples/test_s1_01_output.py::test_a_later_instant_pins_a_different_question_to_the_graph`),
  including a guard that fails loudly if questions 1 and 2 ever stop pinning
  alike, so the caveat cannot silently rot into a false claim. The README states
  the same caveat beside the same claim.
- **Owner:** Dave, as a `D-IMPL` entry on whether the request surface joins the
  replay record. Raised at plan `15.5-13`'s checkpoint.

## DI-15.5-08 — line-number citations rot on any edit to the file they cite

- **Found during:** plan `15.5-13`'s continuation, when adding eleven lines to
  `src/ccf/replay/engine.py` made `cite02-anchor` fail on
  `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md:125` — a citation that was accurate
  when written.
- **What:** the tree cites source by `path:START-END` in prose. Any insertion
  above a cited range silently invalidates every citation below it. The
  `cite02-anchor` lint catches only the subset that pairs a range with a
  **symbol name**; a bare range that now points at the wrong lines is invisible
  to it.
- **What this plan did:** refreshed the four live citations of
  `src/ccf/replay/engine.py:449-455` (now `:472-477`) in
  `docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md`, `src/ccf/products/contract.py` and
  `tests/spikes/test_contract_field_addition_cost.py`, and re-cited the
  lint-flagged one in the `path::Symbol` form the checker itself recommends.
  **Deliberately not touched:** the same range in `docs/DECISIONS.md`
  (D-IMPL-100), `docs/SURFACE-CHANGES.md` and
  `docs/surface-changes/15.5-11-debt-delivery.md` — an append-only ruling
  record, an assembled artifact, and a landed plan's historical fragment. Those
  three now point at the wrong lines.
- **Owner:** phase close. Either widen `cite02-anchor` to verify bare ranges
  (it would have to know what a range is *supposed* to contain, which is why it
  does not today), or rule that prose cites `path::Symbol` and stop citing
  ranges. Both are decisions rather than fixes.
