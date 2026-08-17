---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 13
subsystem: products
tags: [debt, defaulting, d-impl-38, d-impl-47, amendment-a3, amendment-a4, claude-md-11, sabotage-controls]

requires:
  - phase: 17-11
    provides: "`ccf.products.debt_scorer.AssemblyDebtScorer` and `DeclaredFactor` — the reference this plan selects"
  - phase: 17-12
    provides: "`binding.yaml` as a data document with one permitted reference, and the composition in the in-process adapter that this plan lifts into a helper"
provides:
  - "`ccf.products.resolver.build_governed_resolver` — the seam where the SDK selects its own reference debt scorer when a caller passes none"
  - "`ccf.products.resolver.DEBT_SCORER_INPUTS` — the four values the reference needs, named once and enumerated by both refusals"
  - "The 2026-08-16 spec CLOSED: criteria 1, 2, 4, 5 and 3′ all satisfied; CLAUDE.md §11 no longer violated for `AssemblyDebtScorerProtocol`"
  - "A deployment-shape gate taking the ROOT as a parameter: one Python module, `plan:` IS a reference, nothing else is"
  - "The ruled-out keys proven refused END TO END through `ProductClient.ask`, not only at the loader"
  - "24 sabotage/refusal controls, every observed message recorded below"
affects: [17-14, 17-15]

tech-stack:
  added: []
  patterns:
    - "A default placed where it does not enlarge its own seam — the reference scorer needs four further inputs, so the helper defaults it and the class stays defaultless and auditable"
    - "Proving a default by EFFECT twice: the pins on a served product say which scorer ran, and a number that moves with its Control Plane artifact says it actually read one"
    - "Refusing both the empty argument shape and the over-full one, because silently ignoring four supplied arguments is how wiring comes to lie"
    - "An exported constant held to a function's own signature in both directions, so a positional pairing cannot go on running after a reorder"

key-files:
  created:
    - tests/products/test_resolver_defaults.py
    - tests/client/test_data_only_deployment.py
    - docs/surface-changes/17-13-resolver-defaults.md
  modified:
    - src/ccf/products/resolver.py
    - src/ccf/client/adapters/inprocess.py
    - docs/SURFACE-CHANGES.md

decisions:
  - "The default lives in `build_governed_resolver(...)`, NOT on `GovernedResolver`. Two measurements forced it: the reference is a construction needing four further inputs (defaulting on the class would grow it 13 → 17 arguments, four dead on the override path), and `test_no_constructor_argument_carries_a_default` already reads every field off the dataclass and requires no default — admitting the feature would have meant weakening a shipped assertion"
  - "The cost of that choice is stated rather than glossed: there are now two ways to obtain a resolver, and a reader finding only the class will not learn the SDK ships a scorer. Paid down at the class's own `debt_scorer` attribute doc and in the helper's docstring"
  - "17-12's `debt:` block SURVIVES intact, all four fields. None of the four is something a default may supply: the two keys name Control Plane artifacts and §6 forbids discovery machinery; the two factors have no SDK measurement at all. What changed is what a deployment must KNOW — it names no scorer and imports nothing from `ccf.products.debt_scorer`"
  - "Supplying both a scorer and the material is refused, not layered: an explicit scorer replaces the reference entirely, so the material would be read by nothing and a deployment would believe a λ_c key was in force when it was not"
  - "Supplying neither is refused, not defaulted: a resolver with no way to measure `D_c` could only serve an unscored product, which is exactly the spec's Risk 3"
  - "The adapter translates `ProductNotResolvable` into a `BindingError` naming `binding.yaml`, because at boot every key the helper could miss was written there; the original is chained so nothing about the manifest is lost"

metrics:
  duration: ~2 hours
  tasks: 3
  completed: 2026-08-16
---

# Phase 17 Plan 13: The Reference Debt Scorer as the Default Summary

`build_governed_resolver(...)` now selects `AssemblyDebtScorer` when a caller
passes no scorer, so a deployment that supplies only data plus its one
projection never learns `AssemblyDebtScorerProtocol` exists — and the selection
is proven by its **effect on a produced `DebtAssessment`**, twice over: the
`ScorerPin`s that reach the client's `Result`, and a freshness figure that moves
when the λ_c artifact behind it moves. `GovernedResolver` still has thirteen
arguments and not one default, and the test that says so was not touched.

The 2026-08-16 spec is closed. Waves 6 and 7 are unblocked.

## Measured verification

Every figure below was taken from an **unpiped** command with an explicit
`echo "EXIT=$?"`. None of it came through `| tail`.

| Gate | Result |
|---|---|
| `make ci-core` | **exit 0** — `3751 passed, 0 failed, 118 skipped` in 569.73s; `400 passed` lint tests; `144 passed` tools tests |
| `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all` | **exit 0** |
| `make docs-strict` | **exit 0** |
| `make typecheck` | **exit 0** — clean over 209 source files |
| `make surface-changes` | wrote `docs/SURFACE-CHANGES.md`; fragment `docs/surface-changes/17-13-resolver-defaults.md` present |
| `tools/dump_surface.py --report` | `added (2)`: `ccf.products.resolver.DEBT_SCORER_INPUTS`, `ccf.products.resolver.build_governed_resolver`; `removed (0)`; `reshaped (0)` |
| `pytest tests/products tests/client -q` | `749 passed` |

The orchestrator's pre-dispatch baseline on `f7c01c5` was `3711 passed / 118
skipped`. The delta is **+40**, and it is exactly this plan's two new modules:
`tests/products/test_resolver_defaults.py` (25) and
`tests/client/test_data_only_deployment.py` (15). No other test count moved.

> **Measured in a worktree.** Every number above was produced inside
> `/home/parkave/ccf_code/.claude/worktrees/agent-a2a279853c4d3e061`. Tree-walking
> gates measured in a worktree are not evidence about the branch (`DEF-17-04`),
> and this plan added one (the deployment-shape gate). The orchestrator should
> re-measure `make ci-core` after merge.

## THE DECISION: the helper, not the class — and what it cost

The spec left the location open (*"`GovernedResolver` — or a thin
`build_governed_resolver(...)` helper"*). Two measurements decided it, and
neither is a matter of taste.

**1. The default is not a value; it is a construction needing four more inputs
this class does not hold.** `AssemblyDebtScorer` takes a λ_c table, a debt
profile, and a `DebtFactorScorerProtocol` for each of `C` and `S`. Only the
first two are resolvable from the booted fabric, and only given the *keys* that
name them. Defaulting on the class would have grown it from **thirteen
arguments to seventeen** — four of them dead whenever an explicit scorer *is*
supplied — in order to give one argument a default. **A default that enlarges
its own seam is not a default.**

**2. A shipped assertion already forbids it.**
`tests/products/test_resolver_seam.py::test_no_constructor_argument_carries_a_default`
reads `default` and `default_factory` off every dataclass field and requires
both to be `MISSING`. Defaulting on the class would have required deleting or
narrowing it. **Weakening a shipped assertion to admit a feature is this
phase's signature defect**, and doing it in the plan whose whole subject is
"a default that nothing exercises" would have been the defect wearing the fix.

**What the choice costs, stated rather than glossed.** There are now **two ways
to obtain a resolver**, and a reader who finds only `GovernedResolver` will not
learn that the SDK ships a scorer. That is a real cost of the split and it is
paid down in two places rather than left for a support ticket: the class's own
`debt_scorer` attribute doc now names the helper as where the reference is
selected, and the module docstring carries both measurements above plus an
explicit instruction — *a second default should not be added without re-reading
them*, because the argument that selected a helper is about **this** Protocol's
shape and does not transfer for free.

`GovernedResolver`'s claim — *"Every value this composition needs that the SDK
cannot know arrives from outside it, and nothing has a default"* — survives
verbatim and under test.

## THE OTHER DECISION: what happened to `17-12`'s `debt:` block

`17-12` flagged it explicitly as this plan's call. **It survives intact, all
four fields**, and the reasoning is that *none of the four is something a
default may supply*:

| Field | Why a default cannot supply it |
|---|---|
| `half_life_key` | Names a **Control Plane artifact**. §6 forbids *"new discovery or registration machinery in this change"*, and a fabric holding two λ_c tables has no SDK-knowable right answer — picking the only one present is a rule that silently changes behaviour the day a second is registered |
| `debt_profile_key` | Same |
| `completeness` | **No SDK measurement exists.** `DebtFactors` records that position in its own docstring, and `17-11` rejected each candidate default in turn: `C = 1` is a number the SDK chose inside a delivered product's content address; `C = 0` fail-closes every deployment; deriving `C` from the table's breadth couples completeness to how many observation types a deployment happens to calibrate |
| `semantic_consistency` | Same |

So the honest answer to *"what does defaulting mean when two of three factors
are irreducibly the deployment's"* is: **the default is the machinery, never
the values.** After this plan a deployment declares `D_c`'s *inputs* and the SDK
supplies the `GraphView` → `DebtFactors` adapter, the decay computation, the
row-selection choice and the replay pinning. It names no scorer, imports nothing
from `ccf.products.debt_scorer`, and writes no adapter — which is exactly what
spec §6 asks for, and all of what is achievable. A test asserts the deployment's
one module names none of `AssemblyDebtScorer`, `DebtFactors`, `FreshnessScorer`
or `GovernedResolver`.

## How the default is proven USED, and why one property was not enough

**Property 1 — the reference produced the assessment.** The three `ScorerPin`s
on a **served product** are compared as a whole mapping against the shipped
constants (`FRESHNESS_SCORER_ID`, `DECLARED_FACTOR_SCORER_ID` and their
versions). Nothing inspects `resolver.debt_scorer`: that field is satisfied by
any callable at all, and the pins are the only record of which one ran.

**Property 2 — the λ_c artifact reached the number.** Two deployments differing
in **nothing but their half-life table** must produce different freshness
figures, in the direction decay predicts. This catches what a pin cannot: a
scorer correctly selected, correctly pinned, and reading none of the Control
Plane material it was handed. **A pin is a claim; a number that moves with its
input is a measurement.**

Measured on the fixture (one row observed exactly one half-life before the
question is asked):

| λ_c table | `F` | `D_c` | signal |
|---|---|---|---|
| `half_life_seconds: 3600` | `0.500000000000000000` | `0.5` | `forced_llm` |
| `half_life_seconds: 360` (ten half-lives) | `0.000976562500000000` | `~0.999` | `fail_closed` |

A third test pins `F == 0.5` exactly, because **both endpoints are what a scorer
that did nothing would report** — `1` for "assume fresh", `0` for the
empty-assembly branch — and either would satisfy a test that only checked pins.

**The override is proven by effect too**: a deployment-supplied scorer replaces
the reference entirely (asserted as an *absence* of the SDK's identities, not a
presence of the deployment's, because "honoured" and "not silently layered
underneath" are different claims), and the substitution **moves the served
product's content address** — so which scorer was in force is an auditable fact
about a delivered product rather than about a process nobody recorded.

## The fixture, across the three-plan sequence

The number Amendment A.3 asked for, measured with `git show`:

| | Before (`4deb099~1`) | After |
|---|---:|---:|
| Python in `tests/client/fixtures/deployment/` | **295** lines (`resolver.py`) | **127** lines (`projection.py`) |
| responsibilities in that module | five — a projection, a plan factory, a debt scorer, a connection factory, a question factory | **one** — a projection |

`17-13` changed neither figure, and that is the correct outcome: the file shrank
in `17-12`, and this plan's job was to make the *SDK* supply what the file
stopped supplying rather than to shrink it further. What `17-13` changed is that
the deployment no longer names a scorer **anywhere** — the composition it used
to imply now lives behind one function call.

## The spec's five success criteria, with 3′ in place of 3

| # | Criterion | Status |
|---|---|---|
| **1** | *`GovernedResolver` can be constructed and used with only fabric objects plus plain data* | **SATISFIED**, with the one exception Amendment A.3 grants in writing: the projection. `build_governed_resolver` takes two fabric objects, a store, plain data, and the single permitted `plan:` factory |
| **2** | *A deployment directory containing only `ccf_config.yaml` and a data-only `binding.yaml` produces a working gated product* | **SATISFIED as amended** — `tests/client/test_data_only_deployment.py` drives `CCF_BINDING` → `ProductClient.ask` → a `Result` carrying payload, measured debt, a 64-character content address and a resolvable `ccf-artifact://` replay reference |
| **3′** | *`ccf_config.yaml`, a data-only `binding.yaml`, and exactly one Python module — the projection; the loader refuses any other reference by name* | **SATISFIED** — the shape gate takes the root as a parameter and has six controls; both ruled-out keys and a smuggled reference are refused **through `ask`**, not only at the loader |
| **4** | *New tests prove the reference implementations are actually used as defaults — not merely that they exist* | **SATISFIED** — by effect, twice, with the inert-default control watched failing |
| **5** | *CLAUDE.md §11 is no longer violated for these two Protocols* | **SATISFIED** — `AssemblyDebtScorerProtocol` has a shipped reference **and it is now selected**. `ProjectionPlanFactoryProtocol` is discharged by Amendment A.2's ruling (*"§11 does not require the impossible"*), and this plan added no pass-through and no partial factory |

**Waves 6 and 7 are unblocked.**

## Sabotage controls — every observed failure message

Twenty-four controls across the two modules. Each hands a deliberately divergent
subject to the **shipped** assertion function; none re-implements an assertion.
Both modules run an honest-subject test **first**, so no control's expectation of
failure is satisfied by a fixture that never worked. These are messages as
observed, not paraphrases.

### `tests/products/test_resolver_defaults.py` — the selection

1. **The default made inert** (`AssemblyDebtScorer` substituted at the name the
   helper reaches for, so this tests the *selection* and not a different input):
   `the served product's debt was not produced by the SDK's reference scorer: pins {} != {'freshness': ('ccf.reference.freshness-from-decay', '1.0.0'), 'completeness': ('ccf.reference.declared-factor', '1.0.0'), 'semantic_consistency': ('ccf.reference.declared-factor', '1.0.0')}. …`
2. **THE EMPTY CASE — an assessment with no pins:** same message, `pins {}`.
   The comparison is a whole-mapping equality, so `{}` fails as loudly as a
   stranger; a per-pin loop would pass silently.
3. **A stale pinned version** (`D-IMPL-47`'s actual point):
   `… pins {'completeness': ('ccf.reference.declared-factor', '9.9.9'), 'freshness': ('ccf.reference.freshness-from-decay', '9.9.9'), 'semantic_consistency': ('ccf.reference.declared-factor', '9.9.9')} != {…'1.0.0'…}`

### … the measurement

4. **Two identical numbers** (a scorer that read no artifact):
   `the half-life artifact did not reach the measurement: the table declaring the faster decay reported freshness 0.500000000000000000 and the slower one reported 0.500000000000000000, and the faster must be the smaller. …`
5. **The ordering inverted** (why the assertion is `<` and not `!=`):
   `… the table declaring the faster decay reported freshness 0.500000000000000000 and the slower one reported 0.000976562500000000, and the faster must be the smaller. …`

### … the override

6. **A reference-produced subject fed to the override assertion:**
   `an explicit `debt_scorer` did not replace the SDK's reference: the served product's pins are [('completeness', 'ccf.reference.declared-factor'), ('freshness', 'ccf.reference.freshness-from-decay'), ('semantic_consistency', 'ccf.reference.declared-factor')], and the reference still accounts for ['completeness', 'freshness', 'semantic_consistency']. …`
7. **THE EMPTY CASE — an unpinned assessment:**
   `… the served product's pins are [], and the reference still accounts for []. An override replaces the reference entirely; a product carrying no pin at all names no producer for a number it delivers …`

### … the refusals

8. **A construction that succeeds, fed to the refusal assertion:**
   `the construction was accepted. A resolver built with no scorer and no material to build one has no way to measure `D_c`, so the only thing left for it to do is serve an unscored product — the failure the 2026-08-16 spec's Risk 3 names`
9. **A refusal that raises but says nothing:**
   `the refusal does not name ['half_life_key', 'debt_profile_key', 'declared_completeness', 'declared_semantic_consistency'] — an adopter told only that a construction is invalid has to guess which of four values to supply. The message was: no.`

### … and the shipped refusals themselves (observed, `TypeError`)

10. **Neither a scorer nor the material** — the load-bearing one:
    `this call supplies no `debt_scorer` and omits 'half_life_key', 'debt_profile_key', 'declared_completeness', 'declared_semantic_consistency', so there is nothing to measure `D_c` with. … A resolver built without them could only serve an unscored product, which is why this is refused rather than defaulted`
11. **Both a scorer and the material:**
    `this call supplies both `debt_scorer` and 'half_life_key', … and the two are alternatives rather than layers: an explicit scorer replaces the SDK's reference entirely, so the material for building the reference would be read by nothing. …`
    Four further controls parameterize over `DEBT_SCORER_INPUTS`, one per input
    omitted, so a fifth input gets its own control the day it is declared.

### … THE UNRESOLVABLE CASE, three legs

12. **A key naming no artifact** (`ProductNotResolvable`):
    `manifest key 'fixture/nothing-is-here' names no artifact on the booted fabric; the manifest declares ['fixture/debt-profile', 'fixture/half-life-table', 'fixture/half-life/account', …]`
13. **A key naming another class** — the mistake a presence check cannot see:
    `manifest key 'fixture/half-life/account' holds HalfLifeTable, and this resolver reads it as DebtProfile`
14. **An entity class with no declared half-life** (`MissingHalfLife`, `INV-CH7-58`):
    `no half-life declared for observation type 'account'; declare one in the Control Plane λ_c table (no default rate exists)`

### `tests/client/test_data_only_deployment.py` — the shape gate

15. **A second Python module:**
    `the deployment at /tmp/…/deployment holds 2 Python modules ['projection.py', 'scorer.py'], not exactly one — Amendment A.3 grants this deployment one module, the projection, and grants it nothing else`
16. **THE EMPTY CASE — zero modules:** `… holds 0 Python modules [], not exactly one — …`
17. **A reference in a data position:**
    `/tmp/…/binding.yaml carries a `<module-path>:<attribute>` reference in a data position: [('question.subject', 'projection.py:build_projection')]. …`
18. **The same, nested in a sequence** (where a flat scan misses it):
    `… [('operator_parameter_keys[0]', 'projection.py:build_projection')]. …`
19. **THE OTHER EMPTY CASE — the document names no projection.** This is the
    control that justifies the gate's *positive* limb: a document carrying no
    reference at all satisfies *"nothing else is a reference"* perfectly.
    `/tmp/…/binding.yaml states no `<module-path>:<attribute>` reference under ['plan'] — … A document carrying no reference at all would satisfy a 'nothing else is a reference' check perfectly while naming no projection, which is the empty case this limb exists to close`
20. **A document that is not a mapping:**
    `… parsed as `list`, not a mapping — a deployment whose wiring is not a document has no shape to hold to criterion 3′`

### … and the narrowing, driven END TO END through `ProductClient.ask`

21. **`resolver:`** — parameterized over `RULED_OUT_KEYS`, so a third ruled-out
    key gets its own end-to-end control the day it is named:
    `/tmp/…/binding.yaml states `resolver`, which `D-IMPL-141` **ruled out** rather than never defined: `resolver` — the SDK builds the resolver itself from the data keys below — a deployment supplies the projection through `plan:` and nothing else. See `docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md` Amendment A`
22. **`connection_factory:`** — same shape, naming *connection material is data
    under `connection:`, not a factory the loader imports and calls*.
23. **A reference smuggled into `question.intent`:**
    `` `question.intent: projection.py:build_projection` in /tmp/…/binding.yaml is a `<module-path>:<attribute>` reference in a **data** position. …``
24. **A `debt:` key naming no Control Plane section** — the translated voice:
    `` `debt:` in binding.yaml names a Control Plane key this deployment does not have — manifest key 'no-such-section' names no artifact on the booted fabric; the manifest declares ['debt_profile', 'default_perspective', 'half_life', 'policy', 'product_class', 'request_contract', 'resolution', 'temporal.as-of-boundary']``

A twenty-fifth test drives the **unmutated** deployment down the same path and
requires it to answer, so no refusal control above is satisfied by a fixture
that never worked.

## Deviations from Plan

### 1. [Measurement — the plan is wrong] "the eight data keys … the three fabric objects from boot"

- **Found during:** Task 1.
- **The plan said:** *"The construction path must take the eight data keys … the
  three fabric objects from boot."*
- **Measured:** the helper takes **two** fabric objects (`fabric`,
  `control_plane`) — `17-12` already measured that `BootedFabric` carries no
  artifact store, and the spec's §1 table (*"The booted fabric | 3"*) is still
  wrong on the tree. `artifact_store` is a **third argument**, typed to
  `ArtifactStoreProtocol` rather than to a path, so the helper stays
  substrate-agnostic and turning *this deployment's declared path* into *a
  file-backed store* remains the transport's act.
- And the data is **eight resolver keys plus four debt inputs**, not eight. The
  four are `DEBT_SCORER_INPUTS`, and they are the price of the default being a
  construction rather than a value.
- **Not a defect in the ruling** — §6 says the deployment must not have to know
  the *Protocol* exists, and it does not. It says nothing about the argument
  count of the helper.

### 2. [Measurement — the fixture cannot exercise debt as it stands] two missing artifacts and an unpopulated graph

- **Found during:** Task 2's first run, which reported `freshness 0` on **both**
  sides of the λ_c comparison.
- **Three measurements, none of which the plan anticipated:**
  1. `tests/deployment`'s λ_c table declares one row, `fixture-observation`,
     while its resolution spec produces entity class `account`. The reference
     scorer types an observation by the record's own `entity_class`, so that
     table covers nothing the fixture assembles.
  2. The fixture deployment declares **no `DebtProfile` at all**.
  3. The manifest's signal batch is `role: load` (`D-IMPL-80`) — booting parses
     the envelopes and **writes none of them**. An unpopulated graph takes the
     scorer's empty-assembly branch, where every factor is zero and **no pin is
     carried**, so the whole module would have been asserting things about a
     view nothing was measured over. That is the plan's premise ("boot the
     fixture and score it") being false, and it presented as a green-looking
     zero rather than an error.
- **Resolution:** the module writes two λ_c tables (3600s and 360s) keyed by
  `account`, a debt profile, and ingests the batch through `handle.worker`
  before any resolver exists. Each is documented at the point it is done.

### 3. [Rule 1 — Bug, self-found] the positional `zip` against `DEBT_SCORER_INPUTS`

- **Found during:** review of task 1 after `ci-core` came back green.
- **Issue:** `supplied` was computed by `zip(DEBT_SCORER_INPUTS, (…values…),
  strict=True)`. `strict=True` catches a length change and **nothing else** — a
  reorder of the exported constant would go on running and name the wrong
  argument in both refusal messages. A refusal that confidently names the wrong
  thing is worse than one that names nothing, and it is this phase's exact
  shape: a check that stops checking without going red.
- **Fix:** a name-keyed mapping, plus
  `test_the_named_inputs_are_this_helper_s_own_optional_parameters`, which reads
  `inspect.signature(build_governed_resolver)` and holds the constant and the
  signature to each other **in both directions** — a name added to one and not
  the other is now red rather than silent.
- **Commit:** `71a8891`

### 4. [Rule 2 — Correctness] the adapter's refusal voice would have been lost

- **Found during:** Task 1.
- **Issue:** moving the two λ_c/profile lookups behind the helper moves their
  refusal from `BindingError` (which names `binding.yaml`) to
  `ProductNotResolvable` (which names a *manifest* key). The message stays
  accurate and becomes incomplete: at boot, every key the helper could miss was
  written in `binding.yaml`, and the adopter would be left to infer which
  document to edit. It also changes the exception *class* an adopter catches —
  `BindingError` is a `TransportError`; `ProductNotResolvable` is a
  `LookupError`.
- **Fix:** `_boot` translates, chaining the original so nothing about the
  manifest is lost, and a test asserts the translated refusal is still a
  `TransportError`. A second lookup purely to preserve the voice was rejected:
  it would put the manifest read in two places, which is what `17-11` deferred
  to this plan to avoid.

### 5. [Discharged] `17-11`'s deferral

`17-11` deviation 2 recorded that reading the λ_c table and debt profile off
`BootedFabric.artifacts` by manifest key *"is where `17-13`'s
`build_governed_resolver(...)` helper belongs, since it already reads eight
other keys."* That is exactly what shipped. `GovernedResolver._artifact` was
lifted to a module-level `_artifact_on` and the method now delegates, so the
construction-time and call-time narrowings are **one check with one message**
rather than two that drift.

### 6. [Bookkeeping] the surface manifest was NOT regenerated

`docs/surface-changes/README.md` states the single-owner rule: *"Every other
plan leaves both files untouched"* and runs `dump_surface.py --report` instead.
`17-12` regenerated `docs/surface/v0.2-surface.json` because it **removed**
names and the drift gate is direction-blind; this plan only **adds** two, its
fragment claims them by fully-qualified name, and `tests/test_surface_drift.py`,
`tests/test_surface_completeness.py` and `tests/test_surface_shape_capture.py`
are all green (`39 passed`) without touching either file. Recorded because the
two plans did different things and a later reader would otherwise read an
inconsistency.

## What this plan deliberately did not do

- **No `ProjectionPlanFactory` reference implementation, no pass-through plan,
  and no partial version.** Amendment A.2 ruled one impossible as scoped and the
  pass-through was withdrawn during that exchange. The deployment's one Python
  module is still the projection.
- **No second `module:attribute` reference.** `REFERENCE_KEYS` still has one
  element, and neither of `17-12`'s two refusals — by name and by shape — was
  weakened to make anything pass. Both are now additionally proven **end to
  end**.
- **No default on `GovernedResolver`**, and no edit to the test that forbids
  one.
- **No new discovery or registration machinery.** §6 forbids it, so the two
  Control Plane keys are named rather than found. A helper that picked the only
  λ_c table present would be a rule that silently changes behaviour the day a
  second one is registered.
- **No change to the client surface, `WireOutcome`, or the refusal envelope**
  (spec §7).

## Known Stubs

None. The helper, the two refusals, the artifact narrowing and both test
modules are complete for the ruling they implement. `binding.yaml`'s `debt:`
block is a shipped mechanism — declared inputs with an identity in replay — not
a placeholder, and the reasoning for why it cannot shrink further is recorded
above and in the surface-change fragment.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access pattern
and no schema at a trust boundary. `build_governed_resolver` holds no graph
handle, opens no connection and reads no clock; it resolves two already-parsed
artifacts off a fabric the caller supplied.

One property worth naming for the record rather than as a flag: the reference
scorer measures over a possibly principal-scoped view, so the `D_c` figure a
product carries is **not comparable across principals**. `17-11` stated this at
the class docstring; defaulting the scorer means more deployments will now
inherit that property without choosing it, which is the ordinary cost of a
reference implementation and is why the statement lives at the seam.

## Self-Check: PASSED

Files claimed created, verified present:

- `tests/products/test_resolver_defaults.py` — FOUND
- `tests/client/test_data_only_deployment.py` — FOUND
- `docs/surface-changes/17-13-resolver-defaults.md` — FOUND

Commits claimed, verified in `git log`:

- `b76aaeb` — FOUND (`feat(17-13): the reference debt scorer is the default, in a helper`)
- `723e742` — FOUND (`test(17-13): the default is proven by effect, with every control watched failing`)
- `329eb59` — FOUND (`test(17-13): the data-only deployment, proven end to end from CCF_BINDING`)
- `c3f3cbb` — FOUND (`docs(17-13): surface-change fragment for the defaulted debt scorer`)
- `71a8891` — FOUND (`fix(17-13): the named inputs and the signature are held to each other`)

No modification to `.planning/STATE.md` or `.planning/ROADMAP.md`; no `state.*`
or `roadmap.*` SDK writer was invoked.
