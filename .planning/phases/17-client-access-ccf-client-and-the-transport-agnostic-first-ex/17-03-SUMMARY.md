---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 03
subsystem: products
tags: [resolver, d-29, composition, no-hardcoding, src-boundary, sabotage]
requires:
  - ccf.products.refusal.RefusalEnvelope
  - ccf.products.refusal.RequestIdentity
  - ccf.products.refusal.envelope_for
provides:
  - ccf.products.resolver.ServedProductResolverProtocol
  - ccf.products.resolver.ResolverOutcome
  - ccf.products.resolver.ProductNotResolvable
  - ccf.products.resolver.GovernedResolver
  - ccf.products.resolver.ProjectionPlanFactoryProtocol
  - ccf.products.resolver.AssemblyDebtScorerProtocol
affects: []
tech-stack:
  added: []
  patterns:
    - ast-walk-over-a-parameterised-source-root
    - manifest-keys-rather-than-passed-objects
    - protocol-plus-reference-implementation
    - sabotage-controls
key-files:
  created:
    - src/ccf/products/resolver.py
    - tests/products/test_resolver_seam.py
    - tests/invariants/test_src_does_not_import_runtime.py
    - docs/surface-changes/17-03-served-product-resolver.md
  modified:
    - docs/SURFACE-CHANGES.md
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
    - .planning/phases/17-client-access-ccf-client-and-the-transport-agnostic-first-ex/deferred-items.md
decisions:
  - "Four of the thirteen constructor arguments are manifest KEYS read off the booted fabric's artifacts, not passed objects — so the declaration served is provably the one the manifest put in force."
  - "The temporal boundary and the decision instant are both `request.asked_at`; that is the field's documented meaning, so deriving them is mechanism rather than a default."
  - "The two TTL figures stay two independent constructor arguments; a single figure would have Gate 3 compare a ceiling against itself."
  - "`plan_id` is not a constructor argument — the plan the deployment's factory returns knows its own id, which is one fewer thing for an adopter to get right."
  - "Every governance field is forwarded off the declaration rather than left to `register_product_class`'s defaults; a declared policy silently replaced by a default is a policy the fabric never enforced."
  - "`request=None` is admitted by the Protocol and refused by this reference implementation, with `ProductNotResolvable` — a wiring defect, not a governed no."
  - "The request contract is read through `ProductRequestContract.from_declared` when the manifest authored it in an adopter namespace, which is the ordinary case."
metrics:
  duration: ~4h
  completed: 2026-08-15
  tasks: 3
  commits: 5
---

# Phase 17 Plan 03: The Served-Product Resolver Seam — Summary

The SDK now ships the composition it previously shipped only the parts of:
`ServedProductResolverProtocol` and `GovernedResolver`, both in `src/`, with the
`src ↛ runtime` boundary they rest on asserted over three AST shapes.

## READ THIS FIRST — the plan's baseline was wrong, and so is the orchestrator's

**Measured on `phase-17` @ `7d76205`, in a clean worktree, before any of this
plan's work:**

```
2 failed, 3339 passed, 118 skipped, 105 warnings in 390.71s
```

The plan states `3305 passed / 0 failed` @ `543eda0`. The orchestrator states
`3341 passed / 0 failed`. **Neither is reproducible, and the `0 failed` in both
is an artifact of a defect in the verification machinery**, not a property of
the tree.

The two failures are the citation-coverage ratchets. They pass in the main
checkout and fail in every worktree, at the same commit, and the reason is
mechanical: the sweep resolves a cited basename against an index of every file
under the repository root, drops the site when the basename is ambiguous, and
its skip-list omits `.claude`. The main checkout carries six agent worktrees, so
every basename resolves to seven paths, every citation is ambiguous, and every
site is dropped. Measured directly, in the main checkout, for the basename the
first failure names:

```
7 index entries — six under .claude/worktrees/, one real
```

**The orchestrator's 3341 reconciles exactly**: 3339 real passes plus the two
that pass vacuously where the worktrees pollute the index.

Two genuine Phase 16 defects were behind that green, and one of them had already
been dismissed in writing. Full write-up, including why `DEF-17-01`'s closing
claim is false and what the three repairs are, is **`DEF-17-04`** in
`deferred-items.md`. None was fixed here: two are Phase 16 files, one is
`tools/`, all three are outside this plan's declared `files_modified`, and the
third needs a ruling rather than an edit.

**This plan's delta is measured against the real baseline and adds no failure.**

| | passed | failed | skipped |
| --- | ---: | ---: | ---: |
| baseline (`7d76205`) | 3339 | 2 | 118 |
| after `17-03` (`448e51b`) | **3382** | **2** (the same two) | 118 |
| delta | **+43** | 0 | 0 |

**The +43 reconciles exactly**: 30 tests in `tests/products/test_resolver_seam.py`,
12 in `tests/invariants/test_src_does_not_import_runtime.py`, and **one new
parametrisation of an existing guard** —
`tests/products/test_gate_two_call_shape.py::test_no_call_site_fills_both_gate_arguments_from_one_source`
is parametrised over every `run_gates` call site, and `GovernedResolver` is a new
one. It passes, which is a real confirmation rather than noise: the composition
does not fill both Gate 2 arguments from one source, because the lineage claim
comes from the declaration and the engine's set comes from the execution.

## What shipped

### Task 1 — the Protocol (`3d4dcb2`)

`src/ccf/products/resolver.py`, declaring:

- **`ServedProductResolverProtocol`** — `@runtime_checkable`, one keyword-only
  `__call__`. The five arguments are copied from the egress door's resolver seam
  **argument for argument**: same names, same order, same keyword-only
  discipline, same nullability. Verified by printing both signatures.
- **`ResolverOutcome`** — the named union `ServedProduct | RefusalEnvelope`.
- **`ProductNotResolvable`** — the `src`-resident absence signal.

The return type widens in exactly the two ways research measured to be missing:
`ServedProduct` rather than `ServableProduct` (DIV-2 — carries `replay_ref`), and
a refusal in the union (DIV-4). The module docstring records, as a **named
divergence rather than a silence**, that both `runtime/` seams remain typed to
the narrower vessel and that unifying them is out of this phase's scope.

### Task 2 — the reference composition (`0555ba6` RED, `d6e6701` GREEN)

`GovernedResolver`, a frozen `kw_only` dataclass composing:

```
refuse_request → graph view at the boundary → build_operator_registry
→ ProjectionEngine.execute → register_product_class → run_gates
→ build_replay_record → serve
```

Written test-first. The RED commit is a collection failure — `GovernedResolver`
did not exist — and the GREEN commit turns 30 tests green.

### Task 3 — the boundary assertion (`c6cbed0`)

`tests/invariants/test_src_does_not_import_runtime.py`, built around
`find_runtime_imports(root: Path) -> list[str]`.

### Deviation fix (`448e51b`)

`docs/surface/examples/RETIREMENT-COUPLINGS.md` re-measured — see deviation 3.

## `GovernedResolver`'s constructor, with the evidence for each argument

Thirteen arguments, **none with a default**, all keyword-only. The evidence
column says why the SDK cannot supply the value.

| # | Argument | Type | Evidence it is the deployment's |
|---|---|---|---|
| 1 | `fabric` | `BootedFabric` | What `load_and_boot` returned. Supplies the L3 **reader**, the pins, the tenant and the parsed artifacts. Handing back what you were given is the adoption shape. |
| 2 | `control_plane` | `ControlPlaneProtocol` | `load_and_boot`'s own reasoning: a registry built behind the adopter's back splits the audit sequence, and the Control Plane is the audit plane, singular. |
| 3 | `product_class_key` | `str` | A manifest key. The SDK enumerates no product classes (CINV-01). |
| 4 | `request_contract_key` | `str` | A manifest key. The request surface is per class and adopter-authored. |
| 5 | `operator_parameter_keys` | `tuple[str, ...]` | However many the deployment declared — `D-IMPL-132`. No fixed set of four. |
| 6 | `policy_bundle_key` | `str` | The deployment names which bundle it admits; the SDK only looks the pin up (`D-IMPL-76`). Not on `BootedFabric`, so not derivable — checked. |
| 7 | `plan_factory` | `ProjectionPlanFactoryProtocol` | Π is deployment code. The SDK ships no projection and could not. |
| 8 | `debt_scorer` | `AssemblyDebtScorerProtocol` | What `D_c` is measured over is deployment policy — freshness over rows read vs rows survived gives different numbers. |
| 9 | `artifact_store` | `ArtifactStoreProtocol` | A substrate, pluggable by construction (CLAUDE.md §7.4). |
| 10 | `replay_record_class` | `str` | Deployment vocabulary; `ReplayWriter` already refuses to assume it. |
| 11 | `query_pin_class` | `str` | Same, for `QueryPinWriter`. |
| 12 | `max_ttl_seconds` | `int` | The class's ceiling. Registering it is what **mints** `max_ttl_version`, which is why the class document cannot declare it. |
| 13 | `product_ttl_seconds` | `int` | The product's own lifetime. **Independent of #12 deliberately** — one figure serving as both makes Gate 3 compare a ceiling against itself. |

### What was derived rather than taken, per the plan's instruction

The plan asked that any constructor argument derivable from the booted fabric's
own artifacts be derived and the derivation reported. Six were:

| Derived | From | Why it is better derived |
|---|---|---|
| the product class declaration | `fabric.artifacts[product_class_key]` | The declaration served is **provably the one the manifest put in force**, rather than one a caller assembled beside it. |
| the request contract | `fabric.artifacts[request_contract_key]`, through `ProductRequestContract.from_declared` when adopter-namespaced | Same governance property; and `D-IMPL-126` shipped that constructor precisely so no adopter hand-builds the four fields. |
| the operator parameter artifacts | `fabric.artifacts[key]` for each key | The adopter-side idiom `load_and_boot`'s own docstring recommends. |
| `required` operator keys | `declaration.required_operator_keys` | One authored operator set, so there is no second one for Gate 2 to diverge from. |
| `plan_id` | the plan the factory returns | The plan knows its own id; making it an argument would be a fourteenth thing to get right and a way to disagree with the plan. |
| `max_ttl_key` | `declaration.max_ttl_key` | Declared on the class, so passing it separately would be a way to pin the wrong ceiling. |
| the eight governance fields | the declaration | Forwarded rather than left to `register_product_class`'s defaults. A deployment that *declared* accepted lineage modes and had them silently replaced by a default would have written a policy the fabric never enforced. |

And the temporal boundary, the decision instant and `expires_at`:
`temporal_boundary = now = request.asked_at`, and
`expires_at = request.asked_at + product_ttl_seconds`. **This is mechanism, not a
default.** `asked_at` is documented as *"the instant the caller is asking as of,
supplied by the caller at serve time and by replay at replay time, through the
same code path"* — reading it is the field's meaning. The *number* added to it is
argument #13. Nothing here reads a clock, which is what keeps replay possible.

## Every module-level constant in `src/ccf/products/resolver.py`

The plan requires each to be justified as mechanism. There are four, enumerated
by AST rather than by eye:

| Constant | Value | Why it is mechanism |
|---|---|---|
| `__ccf_mode__` | `"algorithmic"` | The CINV-03 opt-in tag. Declares that no LLM client may be imported on this path — the gate sequence and the replay append are the algorithmic half of the Alternation. It is an assertion about this module, not a value about any domain. |
| `__all__` | six names | This module's own export list. |
| `_Artifact` | `TypeVar(bound=CCFContract)` | A type variable for the artifact-narrowing helper. Carries no value at runtime. |
| `ResolverOutcome` | `ServedProduct \| RefusalEnvelope` | A type alias over two SDK types. Named rather than inlined so a `match`, a decoder and a docstring spell one set. |

**No threshold, no product class, no policy value, no TTL, no artifact-class
token, no parameter name and no key appears anywhere in the module.** Measured:

```
$ command grep -nE "= *(True|False|[0-9]+|\"[a-z]) *(#|$)" src/ccf/products/resolver.py
(no output)
$ command grep -cE "ingest|CREATE TABLE|testcontainers|uuid4" src/ccf/products/resolver.py
0
$ command grep -c "sqlite\|postgres\|neo4j\|mongo\|fluree" src/ccf/products/resolver.py
0
```

## The `src ↛ runtime` boundary

`ccf_runtime` appears **five times** in `src/ccf/products/resolver.py`, every one
inside a docstring `:class:` cross-reference role, and **zero** as an import.
Verified by AST rather than by grep:

```
imports: ['__future__', 'dataclasses', 'datetime', 'typing',
          'ccf.artifacts.protocol', 'ccf.contracts.base',
          'ccf.controlplane.artifacts', 'ccf.controlplane.registry',
          'ccf.deployment', 'ccf.graph.protocols', 'ccf.halflife.debt',
          'ccf.products.contract', 'ccf.products.gates',
          'ccf.products.refusal', 'ccf.products.request',
          'ccf.projection.engine', 'ccf.projection.plan',
          'ccf.replay.record', 'ccf.replay.serve']
any ccf_runtime import: False
```

The five roles are: two naming `ProductResolverProtocol` (the seam mirrored, and
the divergence recorded), one naming `ExperienceProductResolverProtocol` (the
second unchanged seam), one naming `ProductNotServable` (the sibling absence
signal), and one in the module docstring's measurement paragraph.

### Was an existing lint already covering this? No — checked before writing

The plan asked this be established rather than assumed. `tools/lints` ships six
rule families, and `RULE_TREE_SCOPE` names them exhaustively:

```
{'no-hardcoding': ('src','runtime','examples','tests'),
 'harness-imports': ('src','runtime'), 'algorithmic': ('src','runtime'),
 'orchestration-imports': ('src','runtime'), 'backend-imports': ('src','runtime'),
 'substrate-names': ('src',)}
```

None says anything about `ccf_runtime`. The nearest existing assertion, in
`tests/skills/test_dispatch.py`, is scoped to **one module**. So the boundary
`D-29` rests on was, until this plan, asserted nowhere. A parallel test was
therefore the right shape, not a duplicate — recorded in the new module's
docstring so the next reader does not re-derive it.

### Scanned-module count

```
real src/ modules scanned: 128
real src/ findings: []
```

128 = the 127 measured at the baseline plus `resolver.py`. The count is asserted
non-zero by `test_the_walk_read_a_real_tree`, because a walk over nothing returns
an empty finding list and is indistinguishable from a healthy tree otherwise —
the "guard that never fired" failure mode this phase exists downstream of.

## Sabotage controls — six, all observed

Every control passes a **divergent subject into the real assertion function**,
which is the property the plan singled out. `find_runtime_imports` takes its root
as a parameter for exactly this reason: a control specified as "copy a module to
`tmp_path` and break it" against an assertion pinned to the real `src/` cannot
fire, because the copy is never what the assertion reads.

### The three boundary controls (Task 3), one per AST shape

Observed messages, verbatim:

```
top-level       REFUSED -> ccf/products/resolver.py line 1: from-import of 'ccf_runtime.mcp.egress'
function-body   REFUSED -> ccf/products/resolver.py line 2: from-import of 'ccf_runtime.mcp.egress'
TYPE_CHECKING   REFUSED -> ccf/products/resolver.py line 4: from-import of 'ccf_runtime.mcp.egress'
```

Three, not one, because three AST shapes: one control covering the top-level
shape would license the other two on nothing but the claim that `ast.walk` is
thorough, and that claim is what is under test. A deferred import is still an
import, and this tree defers imports deliberately in several places to break
cycles — so a deferred `runtime` import is the crossing most likely to be
written in good faith.

**No file under `src/` was modified to perform any of them.** Verified:
`git diff --name-only 7d76205..HEAD -- src/` returns exactly
`src/ccf/products/resolver.py`, and `git status --porcelain src/` is empty.
`test_the_controls_leave_the_real_tree_alone` re-checks this at run time by
comparing the real tree's scan before and after a control runs.

Four further controls guard the controls: a clean tree is admitted (so the walk
is not simply refusing everything), a name merely sharing the prefix
(`ccf_runtimex`) is admitted, a relative import is admitted, and the vacuity
guard trips on an empty root — measured, `modules_scanned: 0`.

### The three composition controls (Task 2)

Each was applied to `src/ccf/products/resolver.py`, observed failing, and
reverted; the file was then diffed byte-for-byte against a pre-sabotage backup
(`IDENTICAL`) and the suite re-run green.

| Sabotage | Test that fired | Observed |
|---|---|---|
| read the graph **before** refusing the request | `test_the_request_refusal_leg_never_reads_the_graph` | `AssertionError: ... the reader saw ['as_of']` / `assert ['as_of'] == []` |
| replace the payload with a constant, so the question does not reach the vessel | `test_two_parameter_values_produce_two_content_addresses` | `AssertionError: assert '61b346da…' != '61b346da…'` — two questions, one content address |
| **raise** a gate refusal instead of returning it | all three `gate_refusal` tests | `RuntimeError: sabotage: the gates refused this product: gate='ttl-bounds' …` |

The refusal-leg control has its own control:
`test_the_success_leg_does_read_the_graph`. Without it, a resolver that never
read the graph on *any* path would satisfy the refusal-leg assertion, and the
assertion would be measuring nothing.

## Deviations from plan

### 1. [Rule 3 — blocking] The venv is not in the worktree, and `make` uses a relative path

**Found during:** setup, before Task 1.
**Issue:** `.venv/bin/python` does not exist inside an agent worktree; the venv
lives in the main checkout. Every command in the plan and the Makefile
(`PYTHON := .venv/bin/python`) assumes the relative path.
**Fix:** symlinked `.venv` into the worktree, which `.gitignore` already covers,
so every documented command runs verbatim rather than being rewritten with an
absolute path. Nothing was committed.
**Files modified:** none.

### 2. [Rule 2 — missing critical functionality] The public-surface gates required a declaration

**Found during:** Tasks 1 and 2.
**Issue:** the plan's `files_modified` names three files. But a module with
`__all__` moves the generated public-surface manifest, and
`tests/test_surface_drift.py` refuses drift no fragment claims. Task 1 added
three names, Task 2 added three more.
**Fix:** wrote `docs/surface-changes/17-03-served-product-resolver.md` declaring
all six with the seven required fields, and regenerated `docs/SURFACE-CHANGES.md`
with `make surface-changes` — the same handling wave 1 used. The live manifest
`docs/surface/v0.2-surface.json` was **not** touched: the single-owner rule
reserves it for phase start and phase close.
**Files modified:** `docs/surface-changes/17-03-served-product-resolver.md`
(new), `docs/SURFACE-CHANGES.md`.
**Commits:** `3d4dcb2`, `d6e6701`.

### 3. [Rule 1 — bug] This plan made a committed measurement stale, and the staleness is informative

**Found during:** final verification, `make gate-tools`.
**Issue:** `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
went red. `docs/surface/examples/RETIREMENT-COUPLINGS.md` was current at the
baseline and was made stale by this plan — a two-row diff, and the rows matter:

```
- MINIMUM_GATE_CALL_SITES — floor 11, 11 witnesses, headroom 0; first break: wave 8 (16-15)
+ MINIMUM_GATE_CALL_SITES — floor 11, 12 witnesses, headroom 1; first break: wave 10 (16-17)
```

Every shipped `run_gates` call site lived inside a **retiring example tree**, so
the floor had **zero headroom** and the first example deletion would have broken
it. `GovernedResolver` is a twelfth witness in `src/`, which is not a retiring
path.

**This is the phase's own argument surfacing in the retirement inventory.** The
SDK shipping the composition means the SDK, rather than an example, witnesses
its own gate call — which is what "the missing resolver and the oversized example
are the same defect" looks like when a different tool measures it.
**Fix:** re-ran `tools/retirement_sweep.py --report`, which is what the failing
test's own message instructs. The diff is those two rows and nothing else.
**Ownership note, stated rather than assumed:** `D-31` gives the retirement
inventory an owner, and this file is outside this plan's `files_modified`.
Leaving it stale would have left `make gate-tools` red **because of this
commit**, which is worse than a two-row re-measurement. Flagging for the
inventory's owner.
**Files modified:** `docs/surface/examples/RETIREMENT-COUPLINGS.md`.
**Commit:** `448e51b`.

### 4. [Rule 3 — blocking] The plan's acceptance grep contradicted the plan's own action text

**Found during:** Task 2 acceptance checks.
**Issue:** the criterion requires
`command grep -c "ingest\|CREATE TABLE\|testcontainers\|uuid4"` to return 0, while
the action text requires "**Do not ingest. Do not provision.**" A docstring
*stating* that absence contains the token, so satisfying the second literally
violates the first. My first draft returned 1, from the sentence "It does not
ingest, does not create a store…".
**Fix:** restated the absence in terms of the mechanism rather than the word —
"hands no envelope to the L1 writer, creates no store, mints no schema and boots
nothing" — which is more precise anyway, since it names *what* ingesting is and
adds the structural reason (this type is constructed without a write handle and
cannot obtain one). The grep now returns 0 and nothing was weakened. `worker`
appears once in the file, in that sentence.
**Files modified:** `src/ccf/products/resolver.py`.
**Commit:** `d6e6701`.

### 5. [reported, not fixed] The citation ratchets and `DEF-17-01`

Covered in full at the head of this document and in `DEF-17-04`. Out of scope:
two Phase 16 files and one `tools/` module, none in this plan's declared files,
and one of the three repairs needs a ruling. **No ratchet constant was touched.**

### 6. Plan facts corrected against the tree

| Plan says | Tree says |
|---|---|
| baseline `3305 passed / 0 failed` @ `543eda0` | `3339 passed / 2 failed` @ `7d76205` — see above |
| the rejected example's `assemble_and_serve` is "357 lines" | the function spans 210 lines; the whole file is 412. The cited line range is right, the line count is not. The argument is unaffected. |
| `git status --porcelain src/` "shows only `src/ccf/products/resolver.py`" | it is **empty** — the file was committed at the end of each task, which is the stronger statement. The equivalent check is `git diff --name-only 7d76205..HEAD -- src/`, which shows exactly that one file. |
| acceptance asks `make ci-core` report "0 failed" | it cannot, on a tree whose baseline is 2-red through no act of this plan. Reported as a delta against the measured baseline instead. |

## Verification

| Command | Result |
|---|---|
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 198 source files` |
| `pytest tests/products/test_resolver_seam.py` | 30 passed |
| `pytest tests/invariants/test_src_does_not_import_runtime.py` | 12 passed |
| `pytest tests/invariants` | 168 passed, 2 failed (both pre-existing) |
| `make test` | **3382 passed, 2 failed** (both pre-existing), 118 skipped |
| `make gate-tools` | 144 passed (after deviation 3) |
| `pytest tests/test_surface_drift.py` | 9 passed |

## Success criteria

- [x] A resolver Protocol **and** its reference implementation both live in `src/`
- [x] The seam carries `replay_ref` and a refusal — the two things no shipped seam can carry
- [x] No `src → runtime` import, asserted over three AST shapes with a control for each
- [x] Every Control-Plane-owned value arrives from outside the composition; all four module-level constants justified above
- [x] Both `runtime/` seams unchanged, and the divergence recorded in the module docstring

## Threat model discharge

| Threat | Disposition | How |
|---|---|---|
| T-17-07 — the resolver acquiring a write handle to L3 | mitigated | It takes `BootedFabric` and reaches only `.reader`. `worker` appears once in the module, in the sentence saying it is never reached. Zero provisioning tokens. |
| T-17-08 — a product delivered without a persisted replay record | mitigated | The composition calls `serve`, never `deliver`; `DeliveryCapability` is minted solely by a completed append. `test_a_failed_replay_append_yields_no_served_product` asserts the negative half through the composition. |
| T-17-09 — a Control Plane value hard-coded into the composition | mitigated | Thirteen arguments, no defaults, enumerated with an exhaustiveness test; four module-level constants, each justified; all three greps clean. |
| T-17-10 — `src/` inheriting a door's trust posture | mitigated | Task 3, with three controls observed firing. |
| T-17-SC — package installs | accepted | None performed. |

## Self-Check: PASSED

Files:

```
FOUND: src/ccf/products/resolver.py
FOUND: tests/products/test_resolver_seam.py
FOUND: tests/invariants/test_src_does_not_import_runtime.py
FOUND: docs/surface-changes/17-03-served-product-resolver.md
```

Commits:

```
FOUND: 3d4dcb2  feat(17-03): declare the served-product resolver seam in src/
FOUND: 0555ba6  test(17-03): the resolver composition's behaviours, before it exists
FOUND: d6e6701  feat(17-03): ship the assemble to serve composition as SDK mechanism
FOUND: c6cbed0  test(17-03): assert the src-does-not-import-runtime boundary D-29 rests on
FOUND: 448e51b  chore(17-03): re-measure the retirement couplings the resolver moved
```

## TDD Gate Compliance

Task 2 carried `tdd="true"` and the gate sequence is in the log: `0555ba6` is the
`test(...)` RED commit (a collection failure — `GovernedResolver` did not exist),
`d6e6701` is the `feat(...)` GREEN commit after it. No REFACTOR commit: the
implementation needed no cleanup pass, and an empty one would be noise.
