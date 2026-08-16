---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 02
subsystem: products
tags: [refusal, envelope, d-28, exhaustiveness-gate, sabotage]
requires: []
provides:
  - ccf.products.refusal.RefusalEnvelope
  - ccf.products.refusal.RequestIdentity
  - ccf.products.refusal.envelope_for
  - ccf.products.refusal.REFUSAL_KINDS
  - ccf.products.refusal.NON_PRODUCT_REFUSALS
  - ccf.products.refusal.NON_VALUE_VIOLATIONS
affects: []
tech-stack:
  added: []
  patterns: [ast-walk-over-a-parameterised-source-root, set-equality-closure, sabotage-controls]
key-files:
  created:
    - src/ccf/products/refusal.py
    - tests/products/test_refusal_envelope.py
    - docs/surface-changes/17-02-refusal-envelope.md
    - .planning/phases/17-client-access-ccf-client-and-the-transport-agnostic-first-ex/deferred-items.md
  modified:
    - docs/SURFACE-CHANGES.md
decisions:
  - "The gate family root wins the `reason` promotion even on ProductMountRefusal, which declares both `gate` and `reason`; the type's own `reason` survives in `fields`."
  - "A refusal declaring neither `gate` nor `reason` reports its kind token as its reason — the third promotion rule, exercised only by MixingRefusal."
  - "GateRefusal is placed in the `gate` family (not `contract`), which is what makes leg 4's `__subclasses__`-excludes-self asymmetry real rather than decorative."
  - "envelope_for enforces D-09's split: offering a lineage alongside a pre-assembly refusal raises."
  - "A fourth comparison — totality — was added beyond the plan: a class in no family would otherwise fall through every other assertion."
metrics:
  duration: ~2h
  completed: 2026-08-15
  tasks: 3
  commits: 6
---

# Phase 17 Plan 02: The Canonical Refusal Envelope — Summary

One canonical refusal envelope now exists in `src/`, translating all **sixteen**
shipped refusal kinds without flattening, with the vocabulary closed by set
equality against a structural AST walk over **both** the `*Refusal` and
`*Violation` name families — nothing enters it by name, and seven sabotage
controls have been watched failing.

---

## The count, and the arithmetic that derives it

**16.** Re-measured on `phase-17` @ `f1969c5`, not assumed.

```
command grep -rn "^class .*Refusal("   src --include=*.py | wc -l   → 17
command grep -rn "^class .*Violation(" src --include=*.py | wc -l   → 6
```

```
17  ^class .*Refusal( in src
−3  NON_PRODUCT_REFUSALS (Control Plane / harness verdicts)
+2  CCFContract-based *Violation (ProductRequestViolation, PayloadSchemaViolation)
──
16  = len(REFUSAL_KINDS)
```

An AST walk (which is what the gate uses) finds **23** classes across the two
name families — 17 + 6, agreeing with `grep` exactly. All 23 are top-level, so
the `^class` anchoring in the plan's measurement missed nothing.

Family partition on the real tree, by resolved base:

| Family | Count | Contents |
|---|---|---|
| `gate` | 13 | `GateRefusal` + its 12 transitive subclasses |
| `contract` | 6 | the 3 vocabulary members + the 3 `NON_PRODUCT_REFUSALS` |
| `exception` | 4 | exactly `NON_VALUE_VIOLATIONS` |
| `unresolved` | 0 | asserted empty |

`(gate ∪ contract) − NON_PRODUCT_REFUSALS` = 13 + 6 − 3 = **16**. ✓

### The sixteen

| # | Kind | Token | Family |
|---|---|---|---|
| 1 | `GateRefusal` | `gate-refusal` | gate |
| 2 | `EmptyOperatorRefusal` | `empty-operator-refusal` | gate |
| 3 | `LineageMismatchRefusal` | `lineage-mismatch-refusal` | gate |
| 4 | `LineageAttributionRefusal` | `lineage-attribution-refusal` | gate |
| 5 | `TTLRefusal` | `ttl-refusal` | gate |
| 6 | `AttestationRefusal` | `attestation-refusal` | gate |
| 7 | `AdmissionRefusal` | `admission-refusal` | gate |
| 8 | `PayloadTooLargeRefusal` | `payload-too-large-refusal` | gate |
| 9 | `SignatureRefusal` | `signature-refusal` | gate |
| 10 | `ContractRefusal` | `contract-refusal` | gate |
| 11 | `PolicyBindingRefusal` | `policy-binding-refusal` | gate |
| 12 | `LineageContinuityRefusal` | `lineage-continuity-refusal` | gate |
| 13 | `ProductMountRefusal` | `product-mount-refusal` | gate |
| 14 | `ProductRequestViolation` | `product-request-violation` | contract |
| 15 | `PayloadSchemaViolation` | `payload-schema-violation` | contract |
| 16 | `MixingRefusal` | `mixing-refusal` | contract |

### The two allowlists

- `NON_PRODUCT_REFUSALS` (3): `RegistrationRefusal`, `EffectRefusal`,
  `GrantRefusal` — walked `*Refusal` family size **17**, of which 14 are
  vocabulary and 3 are these.
- `NON_VALUE_VIOLATIONS` (4): `TrustPolicyViolation`, `SnapshotScopeViolation`,
  `ProductEntitlementViolation`, `SingleWriterViolation` — walked `*Violation`
  family size **6**, of which 2 are vocabulary and 4 are these.

The three name sets are pairwise disjoint, asserted rather than assumed.

---

## Verification — every number measured

| Check | Result |
|---|---|
| `pytest tests/products/test_refusal_envelope.py -q` (narrow) | **36 passed** |
| `pytest tests -q -k "vocabulary_is_closed or hierarchy_agree or cold_and_warm or control_"` (wide collection) | **38 passed, 1 skipped** — the enumeration tests agree with the narrow run |
| `pytest tests/products -q` | **368 passed** |
| `make typecheck` (`mypy --strict`) | **Success: no issues found in 197 source files** |
| `.venv/bin/python -m tools.lints --all` | **exit 0** |
| `command grep -n "sqlite\|postgres\|neo4j\|mongo\|fluree" src/ccf/products/refusal.py` | **no match** (CINV-04 clean) |
| `make ci-core` | **3339 passed / 2 failed / 118 skipped** |

**Narrow and wide agree.** Both were run; both report the enumeration tests
green. This is the import-order property, checked rather than argued — and it is
additionally pinned in-suite by
`test_the_cold_and_warm_runs_agree_on_the_enumeration`, which re-runs the walk
in a cold subprocess and compares.

### The pass-count delta, derived

```
3303  baseline passed  (phase-17 @ f1969c5, clean tree — see the dispute below)
3339  after this plan
──────
  36  delta  ==  36 `def test_*` functions in tests/products/test_refusal_envelope.py
```

Counted by `ast.parse` of the module, not by grep.

---

## Dispute: the plan's baseline is wrong, and `0 failed` is unreachable

**The plan says:** *"`make ci-core` on `phase-17` @ `543eda0` … 3305 passed /
118 skipped / 0 failed"* and *"`make ci-core` must report 0 failed and a pass
count strictly greater than 3305."*

**The tree says otherwise at the branch tip.** Measured with **every 17-02 file
physically removed from the working tree**:

```
FAILED tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

The offending sites, byte-identical before and after this plan:

```
- tests/products/test_discovery_audiences.py:59 cites test_class_governance.py:127
- docs/superpowers/specs/2026-08-15-ccf-client-design.md:421 cites src/ccf/deployment/config.py:82-91
assert 2 <= 0
assert 14 == 13
```

So the real baseline is **3303 passed / 2 failed / 118 skipped**, and this plan
ends at **3339 passed / 2 failed / 118 skipped** — the same two failures, zero
new ones, +36 passed.

**Not fixed here, deliberately.** One offending citation lives in the *approved
Phase 17 design spec*; both ratchets state in their own failure text that
changing the constant is a ruling-scope decision belonging in a decision entry.
Full write-up and the two options a ruling must choose between:
`deferred-items.md` **DEF-17-01**. Every other `17-NN` plan inherits this and
should measure against 3303/2, not 3305/0.

---

## Sabotage controls (D-22) — seven, all observed firing

Each runs the **real** `discover_refusal_types` against a `tmp_path` copy of
`src/` and the **real** four assertions. `src/` is never edited — asserted by
`test_no_control_edits_the_real_source_tree`, which shells `git status
--porcelain -- src/`.

| # | Sabotage | Comparison(s) that fired | Observed |
|---|---|---|---|
| 1 | `class WidgetRefusal(GateRefusal)` | `vocabulary` | `actual − expected = ['WidgetRefusal']` |
| 2 | `class WidgetRefusal(AdmissionRefusal)` | `vocabulary` | `actual − expected = ['WidgetRefusal']` — **proves transitive base resolution**; a literal-`(GateRefusal)` match would miss it, exactly as the plan's first draft missed the seven `AdmissionRefusal`-based types |
| 3 | `class WidgetRefusal(CCFContract)` | `vocabulary` **and** `non-product-allowlist` | both `['WidgetRefusal']` |
| 4 | `REFUSAL_KINDS` narrowed (`TTLRefusal` dropped) | `vocabulary` | `actual − expected = ['TTLRefusal']` — the other direction; containment would have passed |
| 5 | `class WidgetViolation(CCFContract)` | `vocabulary` **and** `non-product-allowlist` | both `['WidgetViolation']` — **the control a hand-enumerated `*Violation` list could not have had** |
| 6 | `class WidgetViolation(LookupError)` | `non-value-allowlist` **only** | `['WidgetViolation']`; the vocabulary comparison is untouched, so the two halves of the name family stay separable by base |
| 7 | `class WidgetRefusal(SomeForeignBase)` | `totality` | `['WidgetRefusal']` |

**Correction to the plan's prediction.** The plan expected control 3 to trip two
comparisons and control 5 to trip *"assertion 1"* alone. Measured: **control 5
trips both**, for the same structural reason control 3 does — a contract-family
class outside the vocabulary is simultaneously claimed as vocabulary and absent
from the allowlist. Recorded as observed, not as predicted.

The unsabotaged gate was run in the same harness and **passes**, so the controls
are measuring a live guard rather than a permanently-red one.

### The guards were sabotaged too

The project's standing lesson is that defects land in verification code. Each
guard was broken deliberately and watched fire, then reverted with
`git checkout -- <one named file>`:

| Guard | Sabotage | Observed failure |
|---|---|---|
| `test_every_kind_has_its_own_test_function` | renamed `test_envelope_for_ttl_refusal` | `kinds with no test function naming them: ['ttl_refusal']` |
| `test_no_aggregate_assertion_stands_in_for_a_per_kind_one` | replaced a per-kind assert with `any(...)` | `aggregate assertion inside a per-kind test: ['test_envelope_for_ttl_refusal']` |
| `test_subclasses_is_confined_to_the_cross_check` | added a `__subclasses__` read to a per-kind test | `__subclasses__ read outside the cross-check: ['test_envelope_for_mixing_refusal']` |
| `test_nothing_enters_the_vocabulary_by_name` | `gate_base = GateRefusal.__name__` → `"GateRefusal"` | `discover_refusal_types names a vocabulary member as a literal: ['GateRefusal']` |
| `test_the_gate_assertions_are_equalities` | one gate `==` → `>=` | `a gate assertion is not an equality: ['test_the_refusal_vocabulary_is_closed_by_set_equality']` |
| `test_the_cold_and_warm_runs_agree_on_the_enumeration` | swapped the two load-bearing imports in `refusal.py` | `ImportError: cannot import name 'PayloadSchemaViolation' from partially initialized module` |

`test_the_gate_assertions_are_equalities` additionally earned its keep
**unprompted**: on first run it flagged a real non-equality — a loop's `if
current in seen` inside the cross-check. It is now scoped to `assert`
statements, which is what the acceptance criterion asked for.

### The `__subclasses__` measurement that justifies the design

The plan's claim was verified exactly:

```
with only ccf.products.gates imported   →  5 GateRefusal subclasses
after ccf.products.refusal is imported  → 12 GateRefusal subclasses
```

A gate built on `__subclasses__` would answer differently under a narrow
`pytest` invocation than under `make ci-core`. The AST walk cannot.

---

## Deviations from Plan

### 1. [Rule 3 — blocking] The worktree was stale and had no `.venv`

**Found during:** startup, before Task 1.
**Issue:** this worktree's branch sat at `6e95da0` (the phase-15.6 merge) — the
Phase 17 plan files did not exist in it — and `.venv` lives only in the main
checkout, so every `make` target and the documented `.venv/bin/python`
invocations were unrunnable.
**Fix:** fast-forwarded to `phase-17` @ `f1969c5` with `git merge --ff-only`
after confirming `6e95da0` is an ancestor (non-destructive; no reset), and
symlinked `.venv` → the main checkout's. Verified `PYTHONPATH=src:runtime`
resolves `ccf` to **this worktree's** `src/`, not the editable install's:
`ccf.__file__` → `.../agent-afa58d2f581395f98/src/ccf/__init__.py`. `.venv` is
already in `.gitignore`.

### 2. [Rule 2 — missing critical functionality] The public-surface gates required a declaration

**Found during:** after Task 1, in the first `ci-core`.
**Issue:** the plan treats this work as *"purely additive to `src/`"* with the
pass count as the only consequence. It is not: adding a module with `__all__`
moves the generated public-surface manifest, and two always-on gates refuse an
undeclared move — `test_every_diff_line_has_a_matching_public_log_entry` and
`test_the_curated_log_is_assembled_from_the_current_fragments`. Both were green
before this plan and went red on the Task 1 commit.
**Fix:** wrote `docs/surface-changes/17-02-refusal-envelope.md` declaring all
six names with the seven required fields, and regenerated the assembled log with
`make surface-changes`.
**Commit:** `705d579`

### 3. [Rule 3 — blocking] A pre-existing import cycle dictates the import order

**Found during:** Task 1, first import of the new module.
**Issue:** `import ccf.products.payload` raises `ImportError` when it is the
first entry into the tree (`payload → skills.catalog → agents → replay.record →
request → payload`). Pre-existing, independent of this plan, and invisible to
the suite because something always imports `request` first.
**Fix:** ordered `request` before `payload` in `refusal.py` with the reason at
the import site. Because relying on line order is fragile, the workaround is
**pinned, not trusted**:
`test_the_cold_and_warm_runs_agree_on_the_enumeration` imports the module in a
cold subprocess, and reversing the two lines fails it (verified by sabotage).
Not fixed at source — that needs an edit to an existing module, which this
plan's charter forbids. Logged as **DEF-17-02**.

### 4. Task-boundary adjustment: `envelope_for` in `__all__`

Task 1's acceptance criterion lists `envelope_for` among the exports, but Task 2
is the task that creates it. Task 1 therefore exported five names and Task 2
added the sixth. The end state satisfies the criterion exactly: `__all__` is
those six and nothing else.

### 5. Beyond plan: a fourth comparison (`totality`) and a seventh control

The plan specifies three set-equality comparisons plus the cross-check. A class
whose base resolves to none of the three roots would land in no family and
therefore appear in **none** of them — passing silently. That is the same shape
of hole as the hand-enumerated `*Violation` half the plan exists to close, one
level further out. Added `totality` (`unresolved == ∅`) and control 7 to prove
it fires.

### 6. Beyond plan: `envelope_for` *enforces* D-09's split

The plan asks the envelope to *carry* the pre/post-assembly distinction.
`envelope_for` additionally **refuses** a lineage offered alongside a
pre-assembly refusal (`ValueError`), so the distinction is structural rather
than conventional — a stored-but-wrong lineage would later read as evidence the
graph had been consulted. Kept private (`_PRE_ASSEMBLY_REFUSALS`) so the export
list stays at the specified six.

### 7. Beyond plan: dispatch is on the exact type

`envelope_for` looks up `type(refusal)` rather than walking an `isinstance`
chain, and a `GateRefusal` subclass outside the vocabulary raises. An
`isinstance` chain would report an unknown subclass as its *nearest known
ancestor* — a well-formed envelope carrying the wrong kind, which is the
flattening hardest to notice. Covered by
`test_envelope_for_raises_on_a_refusal_subclass_not_in_the_vocabulary`.

---

## Errors in the plan's inventory, found by reading the tree

The plan's re-measured 16-row table is correct on **which** types are in scope
and on both allowlists. Four smaller claims are not:

1. **`LineageContinuityRefusal` has three own fields, not two.** The plan lists
   `producer`, `consumer`; the class declares `producer`, `consumer`, **`merged`**
   (`src/ccf/peering/admission.py:349-351`). Reflection carries it anyway — the
   point of reflecting rather than transcribing — and
   `test_envelope_for_lineage_continuity_refusal` asserts all three.
2. **`MixingRefusal` has no `GateRefusal` base pair.** Task 2's behaviour spec
   says it *"preserves all five of its own fields plus the `GateRefusal` base
   pair"*. It derives from `CCFContract`, not `GateRefusal`
   (`src/ccf/products/composition.py:187`) — deliberately, since D-IMPL-31's
   rule is not a fourth gate. It declares `detail` and no `gate`. Asserted as
   the tree has it: five own fields in `fields`, `detail` promoted, and `reason`
   falling back to the kind token.
3. **`SignatureRefusal`'s base pair is promoted, not in `fields`.** Task 2 asks
   for the `GateRefusal` base pair *in addition to* the middle and leaf fields.
   `gate` and `detail` are promoted to `reason`/`detail` by the plan's own rule
   *"minus the members promoted"*. The substance — three inheritance levels,
   none collapsed — is asserted in full: five unpromoted fields across two
   levels, plus both promoted members checked.
4. **The `ProductLineage` citation is off by ~86 lines.** The plan cites
   `src/ccf/products/contract.py:686-698` for *"`ProductLineage`'s three fields"*;
   those lines are `ContextProductContract`'s thirteen fields. `ProductLineage`
   is at `contract.py:600-617`.

Nothing in the tree contradicted the **scope** ruling: every `GateRefusal`
subclass in `src/`, wherever it lives, is in the vocabulary, and no refusal type
was found that the inventory omitted or wrongly included.

---

## Commits

| Commit | What |
|---|---|
| `37d2d03` | `feat(17-02)` — the envelope, the request identity, the mapping, both allowlists |
| `bc9851c` | `test(17-02)` — RED: failing per-kind tests |
| `8c2b442` | `feat(17-02)` — GREEN: `envelope_for`, total over the sixteen |
| `705d579` | `docs(17-02)` — the public-surface fragment + regenerated log (deviation 2) |
| `b6c52eb` | `test(17-02)` — the exhaustiveness gate and seven controls |
| `e961b07` | `docs(17-02)` — `deferred-items.md`, three out-of-scope findings |

`git diff --stat src/` for this plan shows **one new file only**; no existing
module was modified. `src/ccf/products/request.py` — owned by `17-01` in this
wave — was not touched.

---

## Known Stubs

None. Every export is live and exercised; no placeholder, empty-value or
"coming soon" path exists in either file.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access and no
schema at a trust boundary. `T-17-04` (repudiation via flattening) is
**mitigated** as the register requires: `kind` is a required member sourced from
`REFUSAL_KINDS`, and the equality gate plus seven controls prove the mapping
tracks the live hierarchy. `T-17-05` and `T-17-06` remain **accepted** per the
register, unchanged.

## Self-Check: PASSED

Files verified present:

- `FOUND: src/ccf/products/refusal.py`
- `FOUND: tests/products/test_refusal_envelope.py`
- `FOUND: docs/surface-changes/17-02-refusal-envelope.md`
- `FOUND: .planning/phases/17-.../deferred-items.md`

Commits verified in `git log`: `37d2d03`, `bc9851c`, `8c2b442`, `705d579`,
`b6c52eb`, `e961b07` — all found.
