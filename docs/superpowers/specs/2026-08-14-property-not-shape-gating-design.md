# Property-not-shape gating for the example suite

**Date:** 2026-08-14
**Author:** Dave, with Claude
**Status:** Design approved in brainstorming, section by section. The Gate 2
conditioning becomes `D-IMPL-137` before implementation.

---

## 1. Why

`phase-16` is red — 18 failures — and no example is defective. Both failing
gates encode *"every example must look like THIS"*, which is the rigidity
`D-IMPL-132` forbade for operators, applied to examples.

| Gate | Failures | What it hard-codes |
|---|---:|---|
| `tests/examples/test_spine_separation.py` | 16 | the filenames `spine.py`, `report.py`, `run.py`, `deployment.py` |
| `tests/products/test_gate_two_call_shape.py` | 2 | that every projecting body names `refuse_operator_set_divergence` |

HW-1 (`examples/s1-00-companies-over-revenue`) uses `produce.py` /
`deployment.py` / `consume.py` per `D-IMPL-127`, and authors one operator-set
document rather than two.

**The decisive measurement: HW-1 already satisfies every property the gates
claim to prove.** Only the string `spine.py` fails, and only the *premise* of
the binder demand is false. Nothing in HW-1 needs to change.

**Ruling: Option 1** — gate on properties, not filenames. Rewriting the two test
modules is accepted; reverting the example design is not.

**Scope is two modules, measured not assumed.** Of 20 files hard-coding example
filenames, only these two apply a *universal* rule. The other 18 are per-example
output tests naming the one example they test, which is correct.

## 2. Goal

Both gates assert the properties their own docstrings claim, over any example
that holds them, whatever its files are called. No new adopter-facing
convention beyond the one scope rule in §3.1. No example changes.

---

## 3. Gate 1 — the spine/deployment split

### 3.1 Scope: fabric-facing modules

The taxonomy applies to modules under `examples/s1-*` carrying at least one
`from ccf…` / `import ccf`.

This is forced by measurement. The walk is `rglob`, and HW-1 has a fourth
module below the top level:

| module | `ccf` imports | prints | marker regions |
|---|---:|---:|---:|
| `s1-00/produce.py` | 14 | 0 | 14 (7 open + 7 close) |
| `s1-00/deployment.py` | 11 | 0 | 0 |
| `s1-00/consume.py` | 2 | 17 | 0 |
| **`s1-00/scenario/provision.py`** | **0** | **1** | 0 |
| `s1-01/spine.py` | 15 | 0 | 14 |
| `s1-01/run.py` | 1 | 2 | 0 |
| `s1-01/deployment.py` | 12 | 0 | 0 |
| `s1-01/report.py` | 1 | 0 | 0 |
| `s1-01/source_estate.py` | 1 | 0 | 0 |

`scenario/provision.py` prints, so *"exactly one module prints"* is false for
HW-1 without a scope rule. It is also the only module in either example with
**zero** `ccf` imports — it fabricates a Postgres source system and its own
docstring says `THIS IS NOT CCF`. The rule therefore drops it on the principle
the gate already claims (this gate is about how *fabric calls* separate from
adopter code) rather than by naming it.

`s1-01/report.py` prints nothing. The property the current gate asserts of it —
carries no canonical region — is identical to every other non-spine module, so
the role has no distinct property and disappears.

### 3.2 Roles, discovered from content

| Role | Discovered by |
|---|---|
| the spine | the module carrying the seven `--8<--` marker regions |
| the driver | the module that prints |
| adopter code | fabric-facing, neither of the above |

### 3.3 The six properties

| # | Property | `s1-00` | `s1-01` |
|---|---|---|---|
| P1 | exactly one fabric-facing module carries canonical regions | `produce.py` | `spine.py` |
| P2 | that module opens all seven `D-07` names, in order | ✓ | ✓ |
| P3 | every region it opens, it closes; none interleave | ✓ | ✓ |
| P4 | no other module opens a canonical region | ✓ | ✓ |
| P5 | the region-carrying module is silent | 0 prints | 0 prints |
| P6 | exactly one fabric-facing module prints | `consume.py` | `run.py` |

P1 and P4 state one fact from both ends and both are kept: P1 fails when *zero*
modules carry regions, P4 when *two* do.

**Correction, found while planning: regions and printing take different
scopes.** P1–P4 scan **every** module in the example; P5–P6 scan the
**fabric-facing** ones. A `--8<--` region in a module that imports no `ccf` is
still published-snippet surface, so scoping the region properties would make a
marker in `provision.py` invisible — and §3.1's rule was forced by a *print*,
which is the only property it needs to govern. Neither example moves:
`provision.py` carries zero regions.

### 3.4 What changes in the module

**Removed:** `SPINE_MODULE`, `REPORT_MODULE`, `SILENT_MODULES`,
`PRINTING_MODULE` — every filename constant. With them go
`test_every_section_one_example_ships_a_report_module` (asserts a filename and
nothing more) and `test_the_report_module_opens_no_canonical_region` (subsumed
by P4).

**Kept unchanged:** the seven-name vocabulary and its ordering, the
balance/interleave parser, the two vacuity preconditions, the CWD-independence
test, and the aggregate `spine_problems(directory)` predicate — so the negative
controls keep exercising the same code the shipped tree is judged by.

### 3.5 Rulings

1. **The seven markers stay mandatory and ordered.** They are a publication
   contract — the site reads those snippet names — not a shape prejudice. HW-1
   omits four governance surfaces and still carries all seven, so requiring
   seven costs nothing today. Revisit when an example legitimately drops a
   stage.
2. **No `00-quickstart` carve-out.** The glob is `s1-*` and always was, so
   `00-quickstart/run.py` was never in scope. Section 1 of the brainstorm
   promised a carve-out; the correct answer is that none is needed, and dead
   carve-out code is worse than correcting the promise.
3. **The fabric-facing import test is the scope rule.** The alternatives —
   excluding subdirectories, or excluding `__main__`-guarded prints — are shape
   rules of exactly the kind being removed.

---

## 4. Gate 2 — the binder demand

### 4.1 The gate has no compliant state for HW-1

`test_every_projecting_example_body_names_the_binder` demands the call. If HW-1
makes it, `_binder_collapses` property (1) refuses it on the next line:

```python
plan = plan_class(required=tuple(scenario.product_class.required_operator_keys), …)
#                                 └───────────────── path A ─────────────────┘
refuse_operator_set_divergence(declared=scenario.product_class, plan=plan)
#                                       └──── path B ────┘
# B is a prefix of A → _shares_a_source → refused
```

Property (1)'s own message names the exit: *"Build the plan's `required=` from
the projection's OWN document."* That exit is not a code edit — it is
**authoring a second artifact**. The demand is therefore not *"call the
binder"*; it is *"adopt the two-document design."* A design mandate wearing a
call-site check's clothing.

### 4.2 The premise is a Control Plane fact and is readable there

| example with a projecting body | registers `ccf.projection-requirements` |
|---|---|
| 00, 01, 02, 03, 04, 06, 07, 08, `external/00`, `s1-01` | yes |
| **`s1-00` (HW-1)** | **no — the only one** |

Detected from any manifest in the deployment's artifact tree, not a fixed
filename: `04-cross-process` declares it in `producer-manifest.yaml`.

### 4.3 The conditioned rule

The same `_shares_a_source` predicate that decides property (1) decides the
premise, so the gate cannot contradict itself: the shape property (1) refuses
is exactly the shape that exempts a body from the demand.

| Row | registers the artifact | plan's `required=` shares a source with the class claim | Verdict |
|---|---|---|---|
| **A** | yes | no | **two documents** — binder required; properties (1)(2)(3) unchanged |
| **B** | no | yes | **one document** — no second operand exists; the demand does not fire |
| **C** | no | **no** | **refused** — a second operator set was authored somewhere the Control Plane does not know about |
| **D** | yes | yes | **refused** — property (1), unchanged |

Rows A and D are today's behaviour, untouched: every projecting body outside
HW-1 is in row A, across the ten other deployments. Row B is HW-1, and HW-1's
single projecting body is the only one that moves. **Row C is the point of the
design** — the exemption is
not *"no artifact → skip"*. It is earned by a positive assertion, read from the
AST, that the code really does read one source, while the absence is read from
the artifact tree. Two independent readings; disagreement is itself a finding.

**Correction, found while planning: properties (2) and (3) are conditioned
together; only (1) stays unconditional.** §7 note 4 originally conditioned the
coverage assertion and property (3) alone. That leaves HW-1 red. Property (2) —
*the plan bound is the plan run* — is implemented as
`any(call.handed == execution.plan … for call in calls)`, and with **zero**
binder calls `any([])` is `False`, so it fires on every execution. It is HW-1's
second current failure verbatim. Property (1) stays unconditional deliberately:
a row-B body that calls the binder anyway is still refused for the tautology,
which is what makes the exemption an absence of demand rather than a licence.

**Where "the class claim" is read from, in a body that does not call the
binder.** Row A reads it from the binder's own `declared=`. Rows B and C have no
binder call, so it is resolved from the body's
`ProductLineage(operators_invoked=…)` — the existing
`LINEAGE_DECLARED_KEYWORD`, already the module's anchor for the product's side
of Gate 2. A body with no readable class claim — the two replay environments'
`resolve_plan` methods construct a plan and return it, assembling no lineage —
**is subject to the demand**, the same fail-closed default as §4.4. Both such
bodies sit in two-document deployments, so the artifact signal already places
them in row A and nothing about them changes.

Row B verified for HW-1: the plan's `required=` resolves to
`scenario.product_class.required_operator_keys`, and the gate-side claim
`operators_invoked=frozenset(declared.required_operator_keys)` resolves through
`declared = scenario.product_class` to the identical path.

### 4.4 A body with no artifact tree is subject to the demand

**Fail-closed, and load-bearing.** `test_the_binder_tripwire_detects_a_projection_that_skips_it`
synthesizes its violating body in `tmp_path`, which registers nothing; a default
of *exempt* would silence that control on the day this lands while it still
reported green. Independently of the controls, a tree with no Control Plane must
not buy an exemption by having nothing registered. The exemption is claimable
only by a deployment that **has** artifacts and demonstrably lacks that one.

### 4.5 The exemption ceiling

`MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1`, no headroom, carrying the module's
existing `FLOOR_REMOVAL_INSTRUCTION` discipline. The module's floors stop
coverage shrinking silently; the exemption needs the same instrument inverted.
A second deployment claiming the exemption cannot arrive without an edit to that
constant in the same commit, so `git log` distinguishes a deliberate one from an
accidental one.

### 4.6 Rulings

1. **The premise detector is the conjunction, not either signal alone.**
   Artifact-only lets row C through silently. AST-only exempts a deployment that
   collapses its two documents in code while still registering both — `CR-2`'s
   shape.
2. **This is recorded as `D-IMPL-137`, a narrowing of `D-IMPL-86`.** The entry
   states that a one-document deployment is a legitimate shape, that the binder
   demand is conditioned on registration of the second document, and that row C
   stays refused. `D-IMPL-86` assumed design E2's two documents always exist;
   narrowing that inside a test module without a decision entry is how the gates
   became rigid in the first place.
3. **`MINIMUM_PROJECTING_BODIES` is re-measured at implementation.** It is a
   floor and HW-1 adding a body does not trip it, but the comment above it —
   *"nine that construct and execute, plus two `resolve_plan`"* — is already
   stale and is corrected in the same change.

---

## 5. Negative controls

Two ways this rewrite can silently disarm a control. Both are the substance of
this section, not caveats on it.

**Hazard 1 — gate 2's existing controls, addressed by §4.4.**

**Hazard 2 — the fabric-facing predicate can classify everything out.** If
`import ccf` detection matched nothing, P1–P6 would pass over an empty module
set. The existing vacuity preconditions catch an empty *directory* set, not an
empty *fabric-facing* set. This gets its own precondition and its own two-sided
control.

### 5.1 Gate 1

| Control | Disposition |
|---|---|
| refuses a renamed spine | **delete** — renaming is what was legalised |
| refuses a canonical marker in `report.py` | **delete** — names a file; subsumed |
| refuses out-of-order regions | keep (P2) |
| refuses an unclosed region | keep (P3) |
| refuses an eighth marker name | keep (P2 vocabulary) |
| refuses a region in a second module | keep, generalised to any second fabric-facing module (P1-two / P4) |
| refuses zero region-carrying modules | **new** — strip the markers from the copy; the direction the rename control used to cover |
| refuses a region-carrying module that prints | **new** (P5) — `D-11`'s actual content |
| refuses zero printers | **new** (P6) — the shape the 2026-08-13 ruling rejected |
| refuses two fabric-facing printers | **new** (P6) |
| the scope predicate, both halves | **new** — inject a print into a copy of `provision.py`: still passes. Add `import ccf` as well: now refused |

The scope-predicate control keeps both halves because a refusal-only control
passes just as happily against a predicate that classifies everything as
fabric-facing.

### 5.2 Gate 2

| Control | Disposition |
|---|---|
| detects a projection that skips the binder | keep — and now also proves the §4.4 fail-closed default |
| the binder-cannot-fail argument checks (row D) | keep, unchanged |
| row C: no registration, and `required=` reads an unrelated source | **new** — mutate a copy of HW-1, repointing `required=` away from the class claim |
| row B: the shipped HW-1 is exempt for the stated reason | **new** — assert the predicate returns *one document* on the real tree, pinning the exemption to its cause rather than to HW-1 happening to pass |
| the exemption ceiling fires at two | **new** — count over a synthesized root holding two exempt deployments |

The row-C control mutates a copy of HW-1 rather than synthesizing a fixture, for
the reason `_copied_example` exists in gate 1: a synthetic body proves the
predicate can refuse something, a mutated real one proves it refuses the shape
an author would actually write.

---

## 6. What this does not change

- **No example changes.** HW-1 and `s1-01` both pass P1–P6 unchanged, and HW-1
  lands in row B unchanged.
- **No new adopter-facing convention** beyond §3.1's scope rule, which is a test
  predicate and not something an adopter authors.
- **The authorship residual (`R-3`) stays open.** `D-IMPL-86` establishes it as
  AST-undetectable in principle. Nothing here narrows it, and `D-IMPL-137` must
  not be read as doing so.
- **Gate 2 proper is untouched.** The L6 comparison of
  `lineage.operators_invoked` against `engine_resolved` still does real work in
  a one-document deployment: those two sides are the declaration and the
  engine's resolution, which are two sources whatever the upstream document
  count is. HW-1 is green on tripwire (1) today.

## 7. Implementation notes

1. Rewrite `tests/examples/test_spine_separation.py` against P1–P6, keeping
   `spine_problems(directory)` as the aggregate predicate the controls exercise.
2. Add the fabric-facing precondition (non-empty fabric-facing set per example).
3. Add the premise detector to `tests/products/test_gate_two_call_shape.py`:
   deployment root → artifact tree → any manifest declaring
   `class_id: ccf.projection-requirements`; absent tree ⇒ subject to the demand.
4. Condition the coverage assertion and `_binder_collapses` properties **(2) and
   (3)** on the premise; leave property (1) unconditional. See §4.3's second
   correction for why (2) cannot be left out.
5. Add `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1` with the existing floor-removal
   instruction; re-measure `MINIMUM_PROJECTING_BODIES` and correct its comment.
6. Rewrite the controls per §5.
7. Record `D-IMPL-137` in `docs/DECISIONS.md`.

## 8. Target

`phase-16` green with no example modified, and two gates that refuse what they
claim to refuse rather than what the first example happened to look like.
