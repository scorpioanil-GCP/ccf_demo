---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 25
subsystem: examples
tags: [example, context-product, postgres, context-debt, measurement, D-IMPL-131, D-IMPL-132, D-IMPL-133]
requires: ["16-22"]
provides: ["examples/s1-00-companies-over-revenue", "make example-s1-00", "DOCS-22"]
affects: ["Makefile", "tests/examples"]
tech-stack:
  added: []
  patterns: ["artifacts/config vs scenario split (D-IMPL-131 limb 2)", "produce/consume split (D-IMPL-127)", "one-operator product (D-IMPL-132)", "required declared request parameter (D-IMPL-133)"]
key-files:
  created:
    - examples/s1-00-companies-over-revenue/ (19 files)
    - tests/examples/test_s1_00_output.py
  modified:
    - Makefile
decisions: ["one operator category declared; three deliberately omitted", "threshold carried as int, not Decimal, because Decimal does not survive the replay round trip", "decay measured from valid_from, not observed_at"]
metrics:
  duration: single session
  completed: 2026-08-14
status: BLOCKED AT CHECKPOINT — two shipped gates require Dave's ruling
---

# Phase 16 Plan 25: HW-1 — companies over a revenue threshold

**Base:** `BASE=8d249540d8d66002bc084a48c78f8387440b6b69` (phase-16 tip). Every
scope guard below is `git diff --stat $BASE..HEAD -- <path>`.

A very simple Context Product assembled from Postgres, consumed by an in-process
client that supplies its own revenue threshold as a **required** declared
parameter, with context debt driven by the source rows' `last_updated`.

---

## 1. THE NUMBER

| Bucket | HW-1 files | HW-1 lines | s1-01 files | s1-01 lines | Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| **CCF-required config** | **10** | **99** | 15 | 281 | **2.8×** |
| Scenario scaffolding (YAML/SQL) | 3 | 27 | 5 | 779 | 28.9× |
| All YAML/SQL together | 13 | 126 | 20 | 1060 | **8.4×** |
| Adopter Python (statements) | 3 | 253 | 5 | 707 | **2.8×** |
| Scenario Python (statements) | 1 | 55 | — | — | — |

**19 files in the whole example** (17 of code and config, plus `README.md` and
`MEASUREMENT.md`); **10 are the ones an adopter authors**, 4 are `scenario/`
scaffolding they delete outright, and 3 are Python.

Ceilings met: **≤12 config files (10)** and **≤100 non-comment config lines
(99)**. The recipe strips comments *before* counting, so neither is reachable by
commenting code out.

Commands (also in `MEASUREMENT.md` beside every figure):

```sh
ls examples/s1-00-companies-over-revenue/artifacts/config/*.yaml | wc -l          # 10
command grep -hvE '^[[:space:]]*(#|--)' examples/s1-00-companies-over-revenue/artifacts/config/*.yaml \
  | command grep -c '[^[:space:]]'                                                # 99
```

```sh
.venv/bin/python -c "import ast,sys; print(sum(1 for f in sys.argv[1:] for n in ast.walk(ast.parse(open(f).read())) if isinstance(n,ast.stmt) and not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))))" \
  examples/s1-00-companies-over-revenue/{produce,deployment,consume}.py           # 253
```

The same two recipes over s1-01 return **1060** and **707**, reproducing
`D-IMPL-131`'s published figures. The 281/779 split is this execution's own
measurement of s1-01's config-versus-fixture buckets, which s1-01 does not
separate structurally — that separation is exactly what `D-IMPL-131` limb 2
asks for and what `artifacts/config/` vs `scenario/` provides here.

## 2. THE FLOOR TABLE — one row per document, naming the refusal that demanded it

Built up **from nothing**, one refusal at a time: `manifest.yaml` alone → boot →
read the refusal → add exactly what it demanded → repeat. **10 rows, one per
config document.** Nothing is present because s1-01 has one.

| Document | Lines | The refusal that demanded it |
| --- | ---: | --- |
| `manifest.yaml` | 46 | `ArtifactLoadError: artifacts — Tuple should have at least 1 item after validation, not 0` |
| `resolution-spec.yaml` | 6 | `DeploymentManifest` declares `resolution_spec_key` a **required field** |
| `policy-bundle.yaml` | 4 | `ValueError: policy_bundle_key names 'policy-bundle', which is not declared as a 'register' artifact in this manifest; boot needs a pinned version for it` |
| `perspective.yaml` | 3 | `KeyError: 'perspective'` — `ProjectionEngine.execute(perspective=)` |
| `product-class.yaml` | 7 | `KeyError: 'product-class'` — `register_product_class` |
| `request-contract.yaml` | 11 | `KeyError: 'request-contract'` — `refuse_request(declared=)` |
| `half-life-table.yaml` | 6 | `KeyError: 'half-life-table'` — `FreshnessScorer(table=)` |
| `debt-profile.yaml` | 4 | `KeyError: 'debt-profile'` — `assess_debt(profile=)` |
| `operator-parameters-temporal.yaml` | 2 | **Gate 1** — `EmptyOperatorRefusal: product declares no operators; a product computed by nothing is not servable (INV-CH7-46)` |
| `backends.yaml` | 10 | Not manifest-enumerated by design; a connection value in a content-hashed artifact is one persisted into the audit plane forever |

**Two predicted documents turned out not to be required and were NOT added:**
`projection-requirements.yaml`, and any second/third/fourth
`operator-parameters-*.yaml`.

## 3. OPERATOR CATEGORIES — one declared, three omitted, no gate objected

**Declared: Temporal only** (`temporal.as-of-boundary`).
**Omitted: Traversal, Policy, Similarity.**

Two independent measurements establish that one is the **floor**, not a corner
cut:

- `build_operator_registry(parameters={})` returns an **empty registry without
  complaint** — the builder demands no category at all. (Contradicts the
  intuition that the builder is what forces four.)
- `run_gates` with `frozenset()` → `EmptyOperatorRefusal`; with the single
  temporal key → `ServableProduct`.

**No gate demanded a category this product does not need. There is no defect to
report against `D-IMPL-132`.**

## 4. HOW THE CLIENT-SUPPLIED THRESHOLD IS CARRIED

`revenue_threshold` is a **genuinely required** declared request parameter — in
`arguments.properties` *and* in `required`. Demonstrated:

```
refuse_request(request=…, parameters={}) ->
  reason='missing-required-parameter' key='revenue_threshold'
```

**Both required-parameter assertions were proved non-vacuous by making them go
red and reverting:**

1. Equalising the two thresholds turned `test_two_thresholds_are_two_products`
   red: `assert '040c02c2…' != '040c02c2…'`.
2. Moving `revenue_threshold` out of `required` turned
   `test_a_missing_threshold_is_refused_not_defaulted` red — and instructively:
   the door **admitted** the question and assembly then died inside Π with
   `KeyError: 'revenue_threshold'`. The governance check is load-bearing.

**Discharge of `deferred-items.md:83-104`,** which named this plan as owner of
the "both parameterised doors hard-code `parameters={}`" constraint: it is
**ruled by `D-IMPL-133` and implemented by plan `16-26`**, not carried as an open
constraint. HW-1 does **not** depend on `16-26` — its client is in-process and
passes `parameters` straight to the production side, never through a door. HW-2
will reuse this product unchanged and prove both halves of `D-IMPL-127`:
remoteness costs nothing, **and** the client owns the question.

## 5. BOTH RUNS, VERBATIM

```
$ make example-s1-00 MIN_REVENUE=1000000000

Q: which companies have revenue over 1000000000?
   asked as of 2026-08-01T00:00:00+00:00

   Contoso Manufacturing       1850000000   updated 2026-07-02
   Litware Systems             7750000000   updated 2025-09-30
   Lucerne Publishing          1500000000   updated 2024-08-09
   Northwind Traders           4200000000   updated 2026-07-20
   Tailspin Logistics         12400000000   updated 2026-03-01
   Wingtip Materials           2900000000   updated 2025-02-04

   6 of 10 companies

What a SELECT would not have told you:
   context debt D_c   0.3886  ->  forced_llm   (F=0.6114 from last_updated on 10 rows against the declared half-life)
   policy version     dd2c515f43012c7908ff9bd82289553be2b2f8d3900291c265e1cc5abeda0f5f
   content address    5cfee793e5fb686a82becac08cddf2ca187c3ef9ae26bd9a8fd41030656a6d36
   replay record      437d9b10dcc400426c17357567e4af5e7dd1336820ca3c4f469437f833fc8726
```

```
$ make example-s1-00 MIN_REVENUE=3000000000

Q: which companies have revenue over 3000000000?
   asked as of 2026-08-01T00:00:00+00:00

   Litware Systems             7750000000   updated 2025-09-30
   Northwind Traders           4200000000   updated 2026-07-20
   Tailspin Logistics         12400000000   updated 2026-03-01

   3 of 10 companies

What a SELECT would not have told you:
   context debt D_c   0.3886  ->  forced_llm   (F=0.6114 from last_updated on 10 rows against the declared half-life)
   policy version     dd2c515f43012c7908ff9bd82289553be2b2f8d3900291c265e1cc5abeda0f5f
   content address    81a04425285a82e7785926a7a4f5ee62e633fa587d6458de907e15fbaeebab52
   replay record      7cb72f1f973c92fd07763dd6c9bca658593e142d8d071275a37cdde8248d5345
```

**Two thresholds → two answers → two different content addresses.** D_c is
identical because freshness is measured over the rows **assembled** (all ten, at
the boundary) rather than the rows **selected** — a deliberate decision recorded
in `deployment.py::debt`, because `FreshnessScorer.score` refuses an empty
sequence and a threshold admitting nobody would otherwise raise instead of
answering.

Omitting the threshold:

```
$ .venv/bin/python examples/s1-00-companies-over-revenue/consume.py
usage: consume.py [-h] --min-revenue MIN_REVENUE [--as-of AS_OF] [--explain]
consume.py: error: the following arguments are required: --min-revenue
   (exit 2)
```

## 6. WHAT THE REDUCTION COST

Named, not hidden — a number achieved by dropping governance surfaces without
saying so would be the same defect in the other direction:

- **Three operator categories.** No traversal ⇒ nothing here demonstrates
  multi-hop assembly or seeded traversal.
- **`debt_evidence`** (`D-IMPL-118`), **`source_refresh_recency`**
  (`D-IMPL-112` gap 2), **`obligation_in_force`** (`D-IMPL-112` gap 3) — all
  three absent, and `produce.py`'s docstring names each absence.
- **`refuse_operator_set_divergence`** — design E2's guard. See §9-B.
- **A meaningful S factor.** Semantic consistency is fixed at 1 because there is
  one source and a single source cannot disagree with itself.
- **Entitlement variation.** One perspective, one principal, no Π filtering.

## 7. THE MYPY CAVEAT

`mypy --strict` is clean (`Success: no issues found in 195 source files`) — **and
that says nothing about this plan's code.** `[tool.mypy] files = ["src","runtime"]`,
so `examples/` is **not typechecked**. The coverage that does exist for this
plan's code is `tests/examples/test_s1_00_output.py` (9 tests, all behavioural)
and `tools.lints --all`.

## 8. NEEDS DAVE'S RULING — publication

HW-1 is **not wired into `public/`**. `D-IMPL-131` says it becomes *"the first
example shown"*, while the Section 1 docs plans (`16-07`..`16-20`) are the ones
that show examples. **Which plan owns wiring it in?**

## 9. BLOCKING — TWO SHIPPED GATES COLLIDE WITH PLAN-MANDATED DESIGN

**`make ci-core` is RED: 18 failed, 3162 passed, 118 skipped.** All 18 are caused
by this example existing. **None indicates a defect in HW-1's behaviour** — every
one is a naming-or-shape convention that predates a second Section-1 example.
Both fixes require editing files outside this plan's `files_modified`, and both
change what a gate *universally* enforces, so both are Dave's call rather than an
executor's.

Green: `tools.lints --all` (0), `mypy` (0), `make examples` (0),
`make docs-strict` (0), `tests/examples/test_s1_00_output.py` (9/9).

### A. `tests/examples/test_spine_separation.py` — 16 failures

The gate globs `examples/s1-*` and **hard-codes module names**: `SPINE_MODULE =
"spine.py"`, `REPORT_MODULE = "report.py"`, `PRINTING_MODULE = "run.py"`. HW-1
uses `produce.py` / `deployment.py` / `consume.py` per `D-IMPL-127` and this
plan's `files_modified`.

Eight failures are the `[s1-00-…]` parametrizations; the other eight are the
gate's own negative controls, which copy `split_examples(EXAMPLES_ROOT)[0]` —
and `s1-00` now sorts **before** `s1-01`, so every control copies HW-1 and trips
on `no spine.py in s1-00-companies-over-revenue`.

**HW-1 satisfies every substantive property the gate enforces.** Measured:

| Property | HW-1 |
| --- | --- |
| seven canonical regions, in order, all closed | ✅ `boot ingest operators project gate record serve` |
| no eighth marker name | ✅ |
| fabric-facing modules silent | ✅ `produce.py` 0 prints, `deployment.py` 0 prints |
| the driver prints | ✅ `consume.py`, 17 print sites |
| no canonical region in the printing module | ✅ 0 |
| no region spans two modules | ✅ |

**Recommended:** let a Section-1 example declare its own spine/printing module
names (defaulting to today's three), and make the negative controls select the
example that declares the default shape rather than `[0]`. Every property the
gate enforces is preserved; only the filename assumption is generalised.
Alternative rulings: rename HW-1's modules (contradicts `D-IMPL-127`'s visible
boundary and this plan's file list), or narrow the `s1-*` glob (weakens a
shipped gate).

### B. `tests/products/test_gate_two_call_shape.py` — 2 failures

`test_every_projecting_example_body_names_the_binder[…/produce.py]` and
`test_no_projecting_body_names_the_binder_without_binding_it[…/produce.py]`
require **every** projecting body under `examples/` to name
`refuse_operator_set_divergence`.

**The gate's own premise does not hold for HW-1.** Its failure message states
the reason it exists: *"The product class's `required_operator_keys` and the
projection's own `required_operator_keys` are **two separately authored
documents** (design E2, D-IMPL-86 element (2)); the binder is the only thing that
holds them in agreement."* HW-1 authors **one** — `produce.py` passes
`required=tuple(scenario.product_class.required_operator_keys)`, so the binder
would compare a value with itself.

This is exactly what the plan instructed: *"this example ships no
`projection-requirements.yaml` and makes no `refuse_operator_set_divergence`
call … An unused guard is not a missing one."* Adding the call to make the gate
pass is the "declare something so a gate passes" anti-pattern the plan forbids
twice, so **it was not added.** Adding a real second document would also breach
the ≤100-line config ceiling (99 → ~102).

**Recommended:** exempt a projecting body whose plan `required` is derived from
the product-class declaration in the same expression — or, more robustly, make
the gate's predicate "two authored operator sets exist ⇒ the binder is named".

## 10. TOOLING GAP FOUND, NOT FIXED

`tools/check_schema_headers.py:389` globs `examples/**/artifacts/*.yaml`, which
does **not** match `artifacts/config/*.yaml`. Measured:

```python
[p for p in Path('.').glob('examples/**/artifacts/*.yaml') if 's1-00' in str(p)]  # []
# 11 directories scanned; HW-1's config dir is not among them
```

Run explicitly, HW-1's headers are **clean**:

```sh
PYTHONPATH=.:src:runtime .venv/bin/python tools/check_schema_headers.py \
  examples/s1-00-companies-over-revenue/artifacts/config
# checked 1 artifact directories   (0 problems)
```

Nothing goes red, because the target is not part of `docs-strict` or `ci`. But
HW-1's config headers are unscanned by the aggregate run — as are
`examples/03-harness-portability/artifacts/agents/*.yaml` today.

**This is the same vacuous-gate class `16-22` just fixed**
(`tools/assemble_surface_changes.py:183` globbed `15*-*.md` and silently excluded
every phase-16 fragment until widened to `[0-9]*-*.md`). Recorded as an instance
of a recurring pattern; widening the glob belongs to whichever plan owns the tool.

## 11. OTHER FINDINGS (in `src/`, out of scope, not fixed)

1. **A `Decimal` request parameter does not survive the replay round trip.**
   `Decimal('100000000')` serialises and returns as the `str` `'100000000'`, and
   `refuse_request` then refuses the **replayed** request with `type-mismatch`
   against the very contract that admitted the original — the fabric recording a
   decision it cannot replay. `int` round-trips exactly, so HW-1's threshold is
   an `int`. Worth a ruling: money is naturally `Decimal`.

2. **Import-order fragility.** `import ccf.products.payload` as the *first* `ccf`
   import raises `ImportError: cannot import name 'PayloadSchemaViolation' from
   partially initialized module`. `import ccf.products.request` first works.
   Pre-existing; no shipped call site hits it.

3. **Bitemporal trap for adopters.** `SignalEnvelope.observed_time` lands in
   `claim.valid_from`, **not** `claim.observed_at`. Scoring decay off
   `observed_at` measures the age of the *run*: every row read a moment ago
   scores F=1.0, laundering a two-year-old estate into perfect freshness. Caught
   here because the printed output was visibly wrong; a deployment without a
   printed transcript would ship it silently. Documented at length in
   `deployment.py::debt`.

## 12. VERIFICATION LEDGER

| Check | Result |
| --- | --- |
| `git diff --stat $BASE..HEAD -- src/ runtime/` | **empty** |
| files changed outside `files_modified` | **none** (21 files, all listed) |
| `git diff $BASE..HEAD -- Makefile \| grep -c '^[-+]examples:'` | **0** |
| config files / non-comment lines | **10 / 99** (≤12, ≤100) |
| `pytest -m postgres --collect-only` | **9 collected** (non-zero asserted) |
| `pytest tests/examples/test_s1_00_output.py -m postgres` | **9 passed** |
| non-vacuity, content-hash test | **proved red, reverted** |
| non-vacuity, required-parameter test | **proved red, reverted** |
| `tools.lints --all` | **exit 0**, no CINV finding names `s1-00` |
| `mypy --strict` | **exit 0** (does not cover `examples/`) |
| `make examples` | **exit 0** |
| `make docs-strict` | **exit 0** |
| `make ci-core` | **RED — 18 failed / 3162 passed**, see §9 |
| domain vocabulary in `produce.py` | **0** |
| marker regions in `produce.py` | **7 start / 7 end**, ordered |
| `similarity_index_version\|seeds=` in `produce.py` | **0** |
| `from_declared` in `deployment.py` | **1** |
| connection values in artifacts/scenario | **0 matches** |
| `produce+deployment` statements | **200** (ceiling 200; s1-01 = 308) |
| README length | **138** (≤200) |

## 13. COMMITS

| Task | Commit | What |
| --- | --- | --- |
| 1 | `24681cf` | scenario + config floor measured by refusal |
| 2 | `6ab1e54` | production side; both assertions proved non-vacuous |
| 3 | `95e8c4f` | client, README, MEASUREMENT.md, make target |

## Self-Check: PASSED

Verified on `worktree-agent-a687369f976c702a7`:

- `find examples/s1-00-companies-over-revenue -type f` → **19 files**, matching
  the manifest of created files above.
- `tests/examples/test_s1_00_output.py` → present.
- `git log --oneline -3` → `95e8c4f`, `6ab1e54`, `24681cf`, all present.

One figure was corrected during this check rather than left to stand: an earlier
draft said "17 files in the whole example", which was a count taken before
`README.md` and `MEASUREMENT.md` were written. The config and line figures the
ceilings are judged against (10 files / 99 lines) were re-measured and are
unchanged.
