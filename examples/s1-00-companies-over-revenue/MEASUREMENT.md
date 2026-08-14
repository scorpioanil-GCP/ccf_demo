# How many files does a Context Product actually take?

Dave read `examples/s1-01-hello-context-product/artifacts/` and asked:

> *"I am becoming extremely concerned about what I'm seeing … Do I really
> require this many yaml files to construct my context product?"*

**No.** This document is the measurement, with the command beside every figure
so anyone can rerun it. `D-IMPL-131` and `D-IMPL-132` are the rulings that came
out of that reading; HW-1 is their first discharge.

## The answer in one table

| Bucket | HW-1 files | HW-1 lines | s1-01 files | s1-01 lines | Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| **CCF-required config** | **10** | **99** | 15 | 281 | **2.8× fewer lines** |
| Scenario scaffolding (YAML/SQL) | 3 | 27 | 5 | 779 | 28.9× |
| All YAML/SQL together | 13 | 126 | 20 | 1060 | **8.4×** |
| Adopter Python (statements) | 3 | 253 | 5 | 707 | **2.8×** |
| Scenario Python (statements) | 1 | 55 | — | — | — |

**17 files in the whole example**, of which **10 are the ones you would author
for your own product** and 3 more you would delete outright.

The `D-IMPL-131` limb-2 split is why two of those rows exist at all: s1-01 mixes
config and fixtures in one `artifacts/` directory, so its 1060 lines cannot be
told apart by looking. HW-1 puts what CCF requires in `artifacts/config/` and
what merely fabricates the demonstration in `scenario/`.

## The commands

Non-comment YAML/SQL lines (comments are stripped **before** counting, so the
figure cannot be met by commenting things out):

```sh
command grep -hvE '^[[:space:]]*(#|--)' examples/s1-00-companies-over-revenue/artifacts/config/*.yaml \
  | command grep -c '[^[:space:]]'
# 99

ls examples/s1-00-companies-over-revenue/artifacts/config/*.yaml | wc -l
# 10
```

Python executable statements, docstrings excluded:

```sh
.venv/bin/python -c "import ast,sys; print(sum(1 for f in sys.argv[1:] for n in ast.walk(ast.parse(open(f).read())) if isinstance(n,ast.stmt) and not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))))" \
  examples/s1-00-companies-over-revenue/produce.py \
  examples/s1-00-companies-over-revenue/deployment.py \
  examples/s1-00-companies-over-revenue/consume.py
# 253
```

The same two recipes over s1-01 return **1060** and **707**, reproducing
`D-IMPL-131`'s published figures.

## The floor, and why it is measured rather than asserted

The config set was built **up from nothing, one refusal at a time**: start with
`manifest.yaml` alone, boot, read the refusal, add exactly the document that
refusal demanded, repeat. Nothing here is present because s1-01 has one.

| Document | Lines | The refusal that demanded it |
| --- | ---: | --- |
| `manifest.yaml` | 46 | The entry point. `ArtifactLoadError: artifacts — Tuple should have at least 1 item after validation, not 0` |
| `resolution-spec.yaml` | 6 | `DeploymentManifest` declares `resolution_spec_key` as a **required field** |
| `policy-bundle.yaml` | 4 | `ValueError: policy_bundle_key names 'policy-bundle', which is not declared as a 'register' artifact in this manifest; boot needs a pinned version for it` |
| `perspective.yaml` | 3 | `KeyError: 'perspective'` — `ProjectionEngine.execute(perspective=…)` takes it |
| `product-class.yaml` | 7 | `KeyError: 'product-class'` — `register_product_class` takes its six fields |
| `request-contract.yaml` | 11 | `KeyError: 'request-contract'` — `refuse_request(declared=…)` takes it |
| `half-life-table.yaml` | 6 | `KeyError: 'half-life-table'` — `FreshnessScorer(table=…)` takes it |
| `debt-profile.yaml` | 4 | `KeyError: 'debt-profile'` — `assess_debt(profile=…)` takes it |
| `operator-parameters-temporal.yaml` | 2 | **Gate 1**: `EmptyOperatorRefusal: product declares no operators; a product computed by nothing is not servable (INV-CH7-46)` |
| `backends.yaml` | 10 | Not manifest-enumerated, by design. `PostgresGraphStore` needs a `dsn`, and a connection value in a content-hashed artifact is one persisted into the audit plane forever — so this document holds the variable's **name** and never its value |

**A document that was predicted and turned out not to be required was not
added.** Two were dropped this way: `projection-requirements.yaml` (design E2's
divergence guard compares two independently authored operator sets; this
deployment authors one, and an unused guard is not a missing one) and any
second, third or fourth `operator-parameters-*.yaml`.

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
lines and 99. The claim here is not that s1-01 is bloated — it is that **a first
example does not need to be s1-01**, and that the floor for a working, gated,
replay-ready Context Product is ten documents and ninety-nine lines.
