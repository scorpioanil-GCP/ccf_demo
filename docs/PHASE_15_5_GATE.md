# Phase 15.5 — The Context Product Surface: Gate Package

**Phase:** 15.5 (Vessel · Assembler · Debt · Entitlement) · **Branch:** `phase-16` · **Assembled:** 2026-08-11
**Protocol:** CLAUDE.md §3.1 — execution → cross-AI panel → single-agent review → verify every
finding against the tree → fix blocking findings in-phase → present to Dave → `D-GATE-15.5`.
**Gate bar:** the D-17 pattern carried from I.1 — one evidence row per ROADMAP success criterion,
each carrying a runnable command, a `file:line` or a test name. No numeric coverage gate.

> **Status: AWAITING DAVE'S RULING.** `D-GATE-15.5` is **not** logged. `/gsd-review` passing is
> necessary, never sufficient; approval authority is Dave's alone (§2, §3.1 step 3).
>
> **This package carries its own code review.** Phase 15.1's approval was *withdrawn* because the
> code review ran after the gate, so a human was asked to approve a phase before any code review of
> it existed. `.planning/phases/15.5-…/15.5-CLOSE-REVIEWS.md` is the close-time panel on **shipped
> code**, kept distinct from the pre-execution plan review.

---

## 0. The one-line answer to the question that commissioned the phase

Dave read `examples/s1-01-hello-context-product` and asked *"today I would put an MCP server in
front of the fluree database and run a query and return the results. What is the benefit of using
CCF?"* — and the honest answer at the time was *none*, because the example **aggregated**: subject,
temporal boundary and `now` were literals in artifacts, one company, one frozen instant, one answer.

`make example-s1-01` now answers three declared questions — two companies at one instant, and one
company at a later instant — with the question it answered pinned into the replay record, the debt
it was assembled under on the wire, and the caller's entitlement and role checked before Π ever ran.

---

## 1. Gate figures — recorded, not asserted

A gate package saying "green" without numbers is the thing this project's review protocol exists to
prevent. Every figure below was produced on the machine of record at this plan's HEAD.

| Gate | Command | Result |
|---|---|---|
| Full pipeline | `make ci` | **exit 0** — see §7 for the final run's counts |
| Test suite | (inside `make ci`) | **2869 passed, 81 skipped**, 105 warnings, 352.75 s |
| Types | `make typecheck` (inside `ci-core`) | `Success: no issues found in 195 source files` |
| Invariant lints | `python -m tools.lints --all` | **exit 0** |
| Examples | `make examples` | **eleven examples**, all OK, `s1-01` leading |
| Docs gate | `make docs-strict` | pre-build scan + strict build + site scan, **0 findings** |
| Micro-benchmarks | `make perf-micro` | **exit 0**, twelve of twelve PASS |
| Committed schemas | `make schemas` then `git diff` | **no diff** (26 schemas) |
| HTTP contract | `make openapi` then `git diff` | **no diff** |
| Surface manifest | `tools/dump_surface.py` + `tests/test_surface_completeness.py` | 84 added, 0 removed, 21 reshaped; **14 passed**, both directions |

### 1.1 The four anti-leakage lints, named individually

Criterion 9 is **exactly these four and carries no diff-size bound.** `D-IMPL-96` revoked the
"no fabric changed" constraint and recorded why: *"a constraint needing carve-outs to permit correct
work is measuring the wrong thing."* A plan whose verification is a diff size is that reflex
reappearing under a new name, and this gate does not do it.

| Lint | Flag | Exit |
|---|---|---|
| Zero harness imports in `src/` (CINV-02) | `--harness-imports` | **0** |
| No LLM client in an `@algorithmic` module (CINV-03) | `--algorithmic` | **0** |
| No prompt or threshold literal outside an artifact (CINV-01) | `--no-hardcoding` | **0** |
| No substrate name outside the backend registry (CINV-04) | `--substrate-names` | **0** |

### 1.2 Micro-benchmarks — the band was not exceeded and nothing was re-baselined

`make perf-micro` is **not** part of `make ci`, which is why it was run deliberately here.
Runner class `local`, against `perf/baselines/local.json`, 10% relative band.

| Benchmark | Median | Baseline | Δ | Verdict |
|---|---|---|---|---|
| `test_gates.py::test_gate_empty_operator_guard` | 8.00006e-07 | 8.00006e-07 | **0.00%** | PASS |
| `test_gates.py::test_gate_lineage_strict_equality` | 1.79198e-06 | 1.824e-06 | **−1.76%** | PASS |
| `test_gates.py::test_gate_ttl_bounds` | 4.55999e-06 | 4.592e-06 | **−0.70%** | PASS |
| `test_dispatch.py::test_run_coroutine_sync_overhead` | 2.95531e-05 | 2.928e-05 | **+0.93%** | PASS |
| `test_operators.py::test_composed_chain` | 0.375303 | 0.368903 | **+1.73%** | PASS |
| (seven others) | | | all inside band | PASS |

The three `test_gates.py` rows are the load-bearing ones: they are the benchmarks a new hashed
contract field or the payload bind would move, and they moved by less than 2%.

**Two figures deserve Dave's eye, because both were red when the phase began.** `test_composed_chain`
was **+231.87%** at `3df4e91` and is now +1.73% — a real regression, really repaired in-phase under
`D-IMPL-107`. `test_run_coroutine_sync_overhead` was **+11.48%** at the same commit and is now
+0.93%, with no change to the code it measures; that is a benchmark whose variance exceeds its band
rather than a regression. **No baseline was re-based**, which plans `15.5-07` and `15.5-09` both
forbade.

---

## 2. Success-Criteria Evidence Map — ten of ten

One row per ROADMAP Phase 15.5 success criterion. Every evidence cell is a command you can run or a
`file:line` you can read — not a sentence.

| # | Criterion | Evidence |
|---|---|---|
| **1** | Every Context Product carries its Context Debt; no delivery path drops it | `tests/invariants/test_replay_by_construction.py:307` — parametrized over `PRODUCT_DOOR_MODULES`, asserting both that the vessel carries `debt` and that every enumerated door serializes the **whole** vessel. `:337` is the adversarial companion, running the *same predicate* against a door engineered to serialize around the vessel. `:363` asserts there is only one door enumeration in the suite |
| **2** | All **nine** §6.3 elements present, each by executable assertion | `tests/products/test_contract_elements.py:261` (nine), `:277` (each borne by a named field), `:319` (the pending set is empty — the ratchet's terminal state), `:359` (no field bears two elements), `:388` (every whitepaper anchor resolves), `:451` (the module docstring names only fields that exist) |
| **3** | `register_product_class` accepts a declared payload schema; a violating payload is refused | Declaration: `src/ccf/products/contract.py`, `tests/products/test_payload_schema.py`. Refusal: `src/ccf/products/bind.py:145`, `tests/products/test_payload_bind.py`, reusing `refuse_payload` rather than a second comparison. **Partially met — see residual R1.** No shipped door calls the refusal; `CPS-03` is left **Pending** |
| **4** | Perspective derived from the verified identity at every door; `execute()` still takes one | `tests/invariants/test_mcp_role_separation.py:845` (no door discards what `entitled_perspective` returned — an AST walk for the shipped defect's exact shape) and `:879` (the authorized perspective is asserted **by value** against what the resolver received, not by parameter presence — a test checking only that the parameter exists would pass against a door forwarding a freshly-constructed one) |
| **5** | Per-product-class entitlement gates the egress door | All **three** doors, not one: `tests/authz/test_product_entitlement_door.py`, `tests/http_api/test_product_entitlement.py`, `tests/crossproc/test_experience_edge.py`. `docs/schemas/ccf.product-entitlement-policy.json` — `additionalProperties: false` at both levels, both grant sets `required` and undefaulted, so no field can express a bypass. Absent policy denies (`product_entitlement.py:278-288`); empty grants deny |
| **6** | The assembler is a Protocol whose implementation is a declared agent | `src/ccf/agents/assembler.py:242` (`ContextAssemblerProtocol`), `:292` (`DeterministicAssembler`, mechanism-only), declared from the `context_assembly` archetype. `tests/agents/test_consumption_discipline.py` bounds the widening it required |
| **7** | A product answers a runtime request; the question is pinned in replay | `tests/products/test_request_contract.py`; `tests/examples/test_s1_01_output.py:691` — a later instant pins a *different* question, and the guard that used to fail if two subjects ever stopped pinning alike now fails if they ever **start** again (inverted, not deleted). `ContentGenerationPath.request` carries the `ProductRequest` verbatim (`D-IMPL-111`, both limbs) |
| **8** | Aggregate products compose lineage by union and implement `D-IMPL-31`'s refusal | `src/ccf/products/composition.py:322` (`compose_expiry`), `:327` (`refuse_mixing`); `tests/properties/test_aggregate_composition_laws.py:131-236` — every constituent's entries survive, order never matters on the set axes, a new entry strictly grows the composite, a composite never expires later than any constituent, and any floor breach anywhere in the set produces a refusal. **See §4.1 for the third term this phase added to the ruled formula** |
| **9** | The four anti-leakage lints stay green | §1.1 above, each run individually and under `--all`, all exit 0. **Exactly four; no diff-size bound** (`D-IMPL-96`) |
| **10** | `s1-01` demonstrates an agent asking about any company at any time | `make example-s1-01` (`Makefile:89`) — three declared questions in `artifacts/questions.yaml`, two companies at one instant plus one company at a later instant. It **leads** the eleven-member `examples:` aggregate, so it runs in CI (`DI-15.5-02`, closed) |

---

## 3. The review, and its triage

Full record: `.planning/phases/15.5-…/15.5-CLOSE-REVIEWS.md`.

**Three reviewers ran against shipped code.** Codex (3 findings), Cursor (5 findings plus an
explicit verified-clean section), Gemini (**5 findings, all five rejected as fabricated**).

| ID | Finding | Verdict | Disposition |
|---|---|---|---|
| P1 | The entitlement lookup key's tenant is never compared to the resolved policy's own `tenant_id` | **BLOCKING — verified** | **Fixed in-phase**, `7453e87` |
| P2 / C2 | The AGNT-01 capability check is blind to `ast.Attribute` and `getattr` | **BLOCKING — verified**, reached independently by both | **Fixed in-phase**, `c6693f4` |
| C4 | The perspective-discard guard matches only an `ast.Name` callee | ADVISORY — verified | **Fixed in-phase**, `c6693f4` |
| P3 / C1 / C3 | `refuse_bound_payload` and `refuse_request` ship with no calling code path | ADVISORY — verified | **Residual R1 — wants Dave's ruling** |
| C5 | `openapi.json` is outside the publish scan, as `docs/schemas/` is | ADVISORY — verified | **Residual R2** |
| G1–G5 | Gemini | **REJECTED — fabricated** | See below |

**No blocking finding required a decision Dave has not made,** so no `D-IMPL` stop was triggered.
`make ci` is green after the fixes.

### 3.1 Why P1 was blocking

`ControlPlaneProductEntitlementSource.authorize` resolved a policy under
`ccf.product-entitlement-policy/<tenant>` and never checked the artifact's own `tenant_id`. The key
and the field are supplied **independently** at all seven registration sites, and nothing upstream
bound them — so a policy whose content says tenant B, registered under tenant A's key, authorized
A's door with B's grants, and every downstream refusal leg passed because the artifact was
internally consistent.

It is blocking rather than advisory because `ProductEntitlementPolicy`'s docstring claims
tenant-scoping holds *"not by convention, but because there is no shared object for it to leak
through."* That argument is about content addressing and is true of the **artifact**; it was not
true of the **lookup**. A docstring stating that something is enforced where it is not is the exact
defect class this phase exists to correct — `contract.py` claiming all four class-level §6.3
elements *"live"* on `RegisteredProductClass`, where only `assembly_mode` did.

### 3.2 Gemini's output was rejected in full, and the rejection is on the record

Its harness never successfully read a file — repeated sub-agent read failures in the transcript, a
`400 INVALID_ARGUMENT` routing loop in stderr — and it emitted five confident, well-formatted
findings anyway, **two of them marked BLOCKING**. Every one cites a symbol that does not exist:
`DebtAssessment.timestamp` (the type has exactly four fields, none a datetime),
`CompositeProductAssembler`, `ProductEntitlementGate`, `VesselAssembler`,
`validate_vessel_conformity`, `tests/invariants/test_import_invariants.py`.

**This is the second fabricated-citation reviewer output on this project.** Phase 15.1 rejected one
for the same reason. The §3.1 rule that every finding is verified against the tree before being
recorded or acted on is what caught both, and the rejections are recorded as rejections rather than
dropped so the pattern stays visible.

### 3.3 The panel briefing worked, and it is worth keeping

The panel was handed the seven already-known findings and told **not to re-derive them** — to spend
its budget on what is *adjacent* to each. The two highest-value findings (P2/C2) are the same
finding reached independently, and it is precisely the class `DI-15.5-06` names for the surface
manifest: *a check whose subject can be rewritten without changing what the check observes.* Neither
reviewer was asked about AST completeness. This mirrors 15.4, where the same briefing found a
harness-neutrality lint hole that predated the phase.

---

## 4. Discretionary in-phase decisions — recorded as decisions, not omissions

These are executor calls on ruled surfaces. None is a new `D-IMPL`; all belong in front of Dave.

### 4.1 A third term was added to `D-IMPL-31`'s formula

`D-IMPL-31` ruled `expires_at = min(class MAX_TTL ceiling, derivation over constituent validities)`.
The shipped `compose_expiry` (`src/ccf/products/composition.py:322-326`) computes
`min(ceiling, derivation(validities), min(validities))` — a **third** term, so that *"no fresher
than its stalest constituent"* holds regardless of what derivation a class configures.

Under the reference default (`derivation=min`) the third term is an **identity**; under any less
conservative derivation it is **strictly tighter**. Verified independently by the close-time panel
against `tests/products/test_aggregate_composition.py:184-193`. Recorded rather than slipped: it is
a strengthening of a ruling, and a strengthening is still a change to a ruled surface.

### 4.2 The `AGNT-01` import invariant was widened, with its own bound

Plan `15.5-10` widened AGNT-01 with a **per-module** allowlist — three prefixes for `assembler.py`
alone, argued one module at a time rather than added to the package-wide surface — plus a new claim
that the widened module names none of six fabric capability symbols. Its own executor flagged this
as *"the one change here that deserves a reviewer's eye"*, and it got one: both panelists found the
bounding claim incomplete, and it was hardened at close (`c6693f4`). **The widening stands; the
check behind it is what changed.**

### 4.3 Three plans independently made a negative commitment executable

No plan asked for this and it is the pattern most worth carrying forward. Plan `15.5-09` asserts
that `run_gates` takes **no** payload parameter. Plan `15.5-12` asserts that `compose_debt` is
**absent** *and* that its `D-IMPL-104` citation is present. Plan `15.5-11` wrote an adversarial twin
proving a debt-dropping rehydrator is detected. Negative commitments — *"we deliberately did not
build X"* — are what decay silently between phases, because nothing fails when they do. These three
cannot.

### 4.4 The `15.5-01` spike module was retired, not re-pointed

`tests/spikes/test_contract_field_addition_cost.py` named this plan as its retiring owner and
required the choice to be recorded. **Retired** (`7665431`). Its figures survive in
`docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md` (the 29/26 and 18/12 populations, the four-placement Q3
verdict table with observed content addresses, the Q5 nesting costs, the A8 headroom); the eight
questions they priced are ruled; eight plans have moved the tree it measured. Its five
positive-sentinel assertions are independently made by four other suites, checked rather than
assumed, so no coverage left with it. It cost ~3.2 s of every `ci-core` run to re-count call sites
nobody reads any more.

### 4.5 The HTTP door in the ungoverned posture now refuses

`D-IMPL-109` already rules this, and it is repeated here because it is the one **behaviour change**
an adopter would notice: the ungoverned HTTP product door can name no perspective, so it returns
503 `product-door-ungoverned` rather than serving. This supersedes T-07-24's preservation of that
posture. The two-line restoration is in `docs/surface-changes/15.5-15-resolver-seam.md`.

---

## 5. Residuals — every open item, with an owner

| ID | Item | Owner |
|---|---|---|
| **R1** | **`refuse_bound_payload` and `refuse_request` ship with no calling code path.** One caller between them outside their own tests, and it is an example; zero in `runtime/`. `CPS-03` is **Pending** because of it. Convention-not-enforcement — the second instance of that class Phase 16 already carries | **Dave, at this gate.** The question is narrow: does a shipped door call the bind, or is the bind an adopter's obligation the SDK documents and does not enforce? Either answer closes it; the current state is neither. Not fixed by the executor because wiring it into the doors is adjacent to `D-IMPL-102` limb 3's "no fourth gate". `DI-15.5-05` |
| **R2** | **The D-20 publish scanner reads `site/` only.** `docs/schemas/*.json` and `openapi.json` embed source docstrings as `description` fields, so whitepaper prose can be republished into a committed artifact with no gate firing. This *happened* this phase and was found only as a side effect of fixing a docs page | Unassigned — **recommend Phase 17** with `DI-15.5-06`, both being gate-coverage gaps. Swept manually for this close: 27 files, 638 description strings, **0 findings**. A manual sweep is not a gate |
| **R3** | **Line-number citations rot on any edit above them.** Three stale `replay/engine.py:449-455` citations remain, deliberately, in an append-only ruling record, a generated artifact and a landed plan's fragment | **Dave.** Both remedies are decisions: widen `cite02-anchor` to verify bare ranges (it would have to know what a range is *supposed* to contain), or rule that prose cites `path::Symbol`. `DI-15.5-08` |
| **R4** | **The surface-drift manifest cannot see a `Protocol.__call__`.** 56 manifest entries record the information-free `(*args, **kwargs)`, 30 of them `*Protocol`, against 54 Protocol classes | **Phase 17**, ruled by `D-IMPL-110`. Carried, not re-litigated |
| **R5** | `ProductEntitlementPolicy`'s docstring makes a content-addressing argument that is true of the artifact and was never the lookup's guarantee. Left unedited rather than reworded, because editing it moves a committed schema's `description` bytes for a precision gain | Phase 16's documentation rewrite |
| **R6** | `make perf-micro`'s `test_run_coroutine_sync_overhead` has variance exceeding its 10% band (+11.48% then +0.93%, same code) | **Phase 17 perf pass**, with `DI-15.5-04`'s unconditional `IntermediateCache` hash — both are PERF-04 work against the same machine-specific baseline. `DI-15.5-01` |
| **R7** | `DI-15.5-04` — `IntermediateCache` computes a content hash for a cache unreachable **by construction**, ~0.20 s of a 0.41 s benchmark | **Phase 17 perf pass**, per Dave's 2026-08-11 ruling. Unchanged |

### 5.1 What you are being asked to accept as known-stale or known-blind

Three things, stated plainly rather than smoothed over:

1. **The regenerated surface manifest is NOT evidence of surface stability for this phase.**
   `D-IMPL-110` already says so and it must not be cited as such here. The phase's largest
   adopter-facing break — `ProductResolverProtocol` and `ExperienceProductResolverProtocol` going
   from three arguments to five, breaking every adopter supplying a resolver — produces **no
   manifest line**, and I confirmed by name that neither appears among the 21 reshaped symbols. It
   is narrated in `docs/surface-changes/15.5-15-resolver-seam.md` and nowhere else mechanical.
2. **Two plans classified a reshape as `behavior` because `reshaped` was unrepresentable** for a
   name the manifest never moves (`15.5-11`, `15.5-15`). That stands as precedent a later author
   will reasonably copy. Phase 17 should expect to reclassify both.
3. **`CPS-03` is Pending, and it is the only Pending row in the lane.** The mechanism refuses; no
   door calls it. That is R1.

---

## 6. Branch and merge story

Work is on **`phase-16`**, which also carries Phase 16 at **6/21, parked**. Phase 16 was parked
mid-flight precisely so the documentation rewrite would document the corrected surface rather than
the defect — `ROADMAP.md` records that as this phase's reason for existing.

- **What merges:** `phase-16` to `main`, `--no-ff`, at Dave's `D-GATE-15.5` — carrying Phase 15.5's
  15 plans **and** Phase 16's completed 6, since they share the branch.
- **What Phase 16 resumes against:** the corrected surface — a callable product with a typed request
  contract, nine borne §6.3 elements, debt on the wire and in replay, entitlement and
  grant-derived Perspective at all three doors, and `s1-01` as the shape every later example copies
  (criterion 10).
- **Phase 16's 15 remaining plans** should be re-read against this surface before they execute; at
  least the ones documenting the product contract and the delivery doors describe a surface that no
  longer exists.

---

## 7. What Dave is asked to decide

1. **`D-GATE-15.5` — approve or reject.** Ten criteria with evidence in §2; the review and its
   triage in §3; the figures in §1.
2. **Residual R1 (`DI-15.5-05`) — the one substantive open question.** Does a shipped delivery door
   call `refuse_bound_payload` / `refuse_request`, or is the bind an adopter's obligation the SDK
   documents and does not enforce? `CPS-03` stays Pending until this is answered. Two panelists
   independently called it blocking; the executor declined to decide it because the placement is
   `D-IMPL-102`'s and the change is adjacent to limb 3's "no fourth gate".
3. **Residual R3 (`DI-15.5-08`) — the citation convention.** Widen `cite02-anchor` to verify bare
   ranges, or rule that prose cites `path::Symbol` and stop citing ranges.
4. **`D-IMPL-109`'s ungoverned-door refusal** — already ruled, re-surfaced in §4.5 because it is the
   behaviour change an adopter would notice and it supersedes T-07-24.
5. **Confirmation that §4.1's third term** — the strengthening of `D-IMPL-31`'s formula — is
   accepted as a strengthening rather than a deviation.

Nothing in this phase re-opened `D-IMPL-30`, `D-IMPL-31`, `D-IMPL-96` or `D-IMPL-97`. `D-IMPL-31`
was **implemented** for the first time (criterion 8 was implementation of a standing ruling) and
strengthened as recorded in §4.1.
