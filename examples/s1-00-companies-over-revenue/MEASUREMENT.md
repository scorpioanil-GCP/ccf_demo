# How many files does a Context Product actually take?

Dave read `examples/s1-01-hello-context-product/artifacts/` and asked:

> *"I am becoming extremely concerned about what I'm seeing … Do I really
> require this many yaml files to construct my context product?"*

**No.** This document is the measurement, with the command beside every figure
so anyone can rerun it. `D-IMPL-131` and `D-IMPL-132` are the rulings that came
out of that reading; HW-1 is their first discharge.

**HW-1 converted to the single-file `ccf_config.yaml` form in commit
`51aae02`** (`D-IMPL-136`'s AMENDMENT, Dave, 2026-08-15 — plan `16-31`). Every
figure below is stated **before** (the ten-document form this deployment
shipped in through `16-30`) and **after** (what is committed today), so
neither number goes stale silently.

## The answer in one table

| Bucket | HW-1 files (before → after) | HW-1 lines (before → after) | s1-01 files | s1-01 lines | Reduction (after) |
| --- | :---: | :---: | ---: | ---: | ---: |
| **CCF-required config** | 10 → **2** | 99 → **58** | 15 | 281 | **4.8× fewer lines** |
| Scenario scaffolding (YAML/SQL) | 3 → 3 | 27 → 27 | 5 | 779 | 28.9× |
| All YAML/SQL together | 13 → **5** | 126 → **85** | 20 | 1060 | **12.5×** |
| Adopter Python (statements) | 3 → 3 | 253 → **252** | 5 | 707 | **2.8×** |
| Scenario Python (statements) | 1 → 1 | 55 → 55 | — | — | — |

**11 files in the whole example now** (was 19) — 9 of code and config (was
17), plus this document and the README. Of those 9, **2 are the ones you
would author for your own product** (was 10), 4 you would delete outright
(`scenario/`, unchanged), and 3 are Python (unchanged).

The `D-IMPL-131` limb-2 split is why two of those rows exist at all: s1-01 mixes
config and fixtures in one `artifacts/` directory, so its 1060 lines cannot be
told apart by looking. HW-1 puts what CCF requires at the deployment root
(`ccf_config.yaml`, `backends.yaml`) and what merely fabricates the
demonstration in `scenario/`.

## The commands

Non-comment YAML/SQL lines (comments are stripped **before** counting, so the
figure cannot be met by commenting things out):

```sh
command grep -hvE '^[[:space:]]*(#|--)' examples/s1-00-companies-over-revenue/ccf_config.yaml \
  examples/s1-00-companies-over-revenue/backends.yaml \
  | command grep -c '[^[:space:]]'
# 58

ls examples/s1-00-companies-over-revenue/ccf_config.yaml \
   examples/s1-00-companies-over-revenue/backends.yaml | wc -l
# 2
```

**Before `16-31`** (the ten-document multi-file form; reproducible today
against the frozen fixture, `tests/deployment/fixtures/s1-00-multifile/`,
which holds the nine manifest-enumerated documents — `backends.yaml` stayed
at the example root even before this plan and is unaffected by the freeze):

```sh
command grep -hvE '^[[:space:]]*#' tests/deployment/fixtures/s1-00-multifile/*.yaml \
  examples/s1-00-companies-over-revenue/backends.yaml \
  | command grep -c '[^[:space:]]'
# 99

{ ls tests/deployment/fixtures/s1-00-multifile/*.yaml; \
  ls examples/s1-00-companies-over-revenue/backends.yaml; } | wc -l
# 10
```

Python executable statements, docstrings excluded:

```sh
.venv/bin/python -c "import ast,sys; print(sum(1 for f in sys.argv[1:] for n in ast.walk(ast.parse(open(f).read())) if isinstance(n,ast.stmt) and not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))))" \
  examples/s1-00-companies-over-revenue/produce.py \
  examples/s1-00-companies-over-revenue/deployment.py \
  examples/s1-00-companies-over-revenue/consume.py
# 252
```

**One fewer statement than the pre-conversion 253**: `deployment.py` no
longer assigns a separate `CONFIG = HERE / "artifacts" / "config"` constant
— `MANIFEST` (kept under that name so `consume.py`'s `deployment.MANIFEST`
reference needs no edit) is assigned directly off `HERE`. Nothing else in
`produce.py`, `deployment.py` or `consume.py` changed statement-shape;
`produce.py`'s single edited line (the loader call, `load_and_boot` →
`load_config_and_boot`) is a one-for-one substitution.

The same two recipes over s1-01 return **1060** and **707**, reproducing
`D-IMPL-131`'s published figures — s1-01 is untouched by this plan; there is
still no bulk migration (`D-IMPL-136`).

## The floor, and why it is measured rather than asserted

**Before `16-31`,** the config set was built **up from nothing, one refusal at
a time**: start with `manifest.yaml` alone, boot, read the refusal, add
exactly the document that refusal demanded, repeat. That history is preserved
here because the refusals are still what the single-file form's own sections
answer — `ccf_config.yaml`'s `product_class:`, `resolution:`,
`request_contract:` and so on are the same commitments, restated as sections
of one document instead of ten separate files.

| Document (before) | Lines (before) | Becomes (after) | The refusal that demanded it |
| --- | ---: | --- | --- |
| `manifest.yaml` | 46 | *(deleted — the index `D-IMPL-136` removes)* | The entry point. `ArtifactLoadError: artifacts — Tuple should have at least 1 item after validation, not 0` |
| `resolution-spec.yaml` | 6 | `resolution:` section | `DeploymentManifest` declares `resolution_spec_key` as a **required field** |
| `policy-bundle.yaml` | 4 | `policy:` section | `ValueError: policy_bundle_key names 'policy-bundle', which is not declared as a 'register' artifact in this manifest; boot needs a pinned version for it` |
| `perspective.yaml` | 3 | `default_perspective:` section | `KeyError: 'perspective'` — `ProjectionEngine.execute(perspective=…)` takes it |
| `product-class.yaml` | 7 | `product_class:` section | `KeyError: 'product-class'` — `register_product_class` takes its six fields |
| `request-contract.yaml` | 11 | `request_contract:` section | `KeyError: 'request-contract'` — `refuse_request(declared=…)` takes it |
| `half-life-table.yaml` | 6 | `half_life:` section | `KeyError: 'half-life-table'` — `FreshnessScorer(table=…)` takes it |
| `debt-profile.yaml` | 4 | `debt_profile:` section | `KeyError: 'debt-profile'` — `assess_debt(profile=…)` takes it |
| `operator-parameters-temporal.yaml` | 2 | `operators:` section | **Gate 1**: `EmptyOperatorRefusal: product declares no operators; a product computed by nothing is not servable (INV-CH7-46)` |
| `backends.yaml` | 10 | `backends.yaml` (unchanged, relocated to the example root) | Not manifest-enumerated, by design. `PostgresGraphStore` needs a `dsn`, and a connection value in a content-hashed artifact is one persisted into the audit plane forever — so this document holds the variable's **name** and never its value |

**A document that was predicted and turned out not to be required was not
added.** Two were dropped this way: `projection-requirements.yaml` (design E2's
divergence guard compares two independently authored operator sets; this
deployment authors one, and an unused guard is not a missing one) and any
second, third or fourth `operator-parameters-*.yaml`.

## `ccf_config.yaml`'s own floor: 48 lines against the design spec's ~30

`docs/superpowers/specs/2026-08-14-ccf-config-consolidation-design.md`'s
stated target is *"roughly 30 lines against HW-1's current 99."* The
converted file measures **48** — a real gap, recorded rather than closed by
moving content out of the file. The line-by-line account, against the same
nine before-documents:

| Section | Lines | What it carries |
| --- | ---: | --- |
| top level (`semver`, `tenant_id`, `backend`) | 3 | unchanged from `manifest.yaml`'s own three top-level value fields |
| `product_class:` | 7 | header + the six fields `product-class.yaml` carried |
| `operators:` | 3 | header + operator id + the one field `operator-parameters-temporal.yaml` carried |
| `request_contract:` | 12 | header + **3 adopter-owned bookkeeping lines** (`class_id`, `role`, `registration` — `D-IMPL-138`(a)) + `schema_name`/`schema_version` (2 lines `request-contract.yaml`'s own `declaration:` carried, needed by `ProductRequestContract.from_declared`) + the 6-line `arguments:` block |
| `resolution:` | 6 | header + the five fields `resolution-spec.yaml` carried |
| `half_life:` | 5 | header + `company:` + the three fields `half-life-table.yaml` carried |
| `debt_profile:` | 4 | header + the three fields `debt-profile.yaml` carried |
| `policy:` | 5 | header + **3 adopter-owned bookkeeping lines** (`class_id`, `role`, `registration`) + the one field `policy-bundle.yaml` carried |
| `default_perspective:` | 3 | header + the two fields `perspective.yaml` carried |
| **Total** | **48** | |

**Where the eighteen-line gap against ~30 comes from, named rather than
absorbed into "overhead":**

1. **Six lines are `D-IMPL-138`(a)'s three-bookkeeping-line ruling**, applied
   to the two adopter-owned sections (`request_contract:`, `policy:`). The
   design spec's own §5.3/§5.7 worked examples show these sections with
   **zero** bookkeeping lines — the ruling that adopter-owned classes need
   `class_id`, `role` *and* `registration` stated (not derivable, per
   `D-IMPL-84`) postdates that illustration.
2. **Two lines are `request_contract:`'s `schema_name`/`schema_version`**,
   which the design spec's §5.3 snippet also omits. `produce.py`'s
   `ProductRequestContract.from_declared` call reads them straight off the
   registered artifact (the `16-22` papercut repair, `D-IMPL-126` item 1);
   HW-1's own committed `request-contract.yaml` already carried them under
   `declaration:` before this plan, so this is not new content, only content
   the abbreviated illustration did not show.
3. **The remaining ten lines are the compounding cost of eight section
   headers plus nested nesting** (`arguments:` → `properties:` →
   `revenue_threshold:` → `type:`/`description:`, `half_life:` → `company:`)
   that the design spec's per-section illustrations, shown as disconnected
   snippets, did not sum when combined into one continuous file.

**No line was moved out of `ccf_config.yaml` to make this number smaller.**
Every line above is a decision HW-1's author already made, restated once
instead of transcribed across ten files.

## One operator category, and it is measured

`D-IMPL-132`: *"Operators help me assemble it but I should not be forced into a
single format."* HW-1 declares **Temporal only**. Traversal, Policy and
Similarity are absent because this question is about a *set* rather than a
*path*, it admits one policy bundle by pin rather than by filtering a graph, and
it matches no text.

Two separate measurements establish that one is the **floor** rather than a
corner cut:

* `build_operator_registry(parameters={})` returns an **empty registry without
  complaint** — the builder demands no category at all.
* `run_gates` with `frozenset()` returns `EmptyOperatorRefusal`; with the single
  temporal key it returns a `ServableProduct`.

**No gate demanded a category this product does not need**, so there is no
defect to report against `D-IMPL-132`.

## What the reduction cost

An honest number has to say what it bought the reduction with. HW-1 does not
exercise these, and each is real:

* **Three operator categories.** No traversal means no walk, so nothing here
  demonstrates multi-hop assembly or seeded traversal.
* **`debt_evidence`** — what the debt points at (`D-IMPL-118`).
* **`source_refresh_recency`** — when the sources last published
  (`D-IMPL-112` gap 2).
* **`obligation_in_force`** — what the routing signal obliges the deployment to
  do (`D-IMPL-112` gap 3).
* **`refuse_operator_set_divergence`** — design E2's guard.
* **A meaningful S factor.** Semantic consistency is 1 because there is exactly
  one source, and a single source cannot disagree with itself. Debt only gets
  interesting once assembly spans sources that *do* disagree.
* **Entitlement variation.** One perspective, one principal, no Π filtering.

s1-01 exercises all of them, which is most of the distance between 281 config
lines and 58. The claim here is not that s1-01 is bloated — it is that **a first
example does not need to be s1-01**, and that the floor for a working, gated,
replay-ready Context Product is two documents and fifty-eight lines.
