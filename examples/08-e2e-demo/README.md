# examples/08-e2e-demo — the fraud ring raw data cannot see (DEMO-01..03)

## What this demonstrates

Three synthetic **banking** systems of record — a core-banking ledger, a
wire/payments log, and a counterparty/KYC registry — are generated
deterministically from a scenario artifact, then run through the fabric.
A planted five-member fraud ring hides behind different identifiers in
each source. The headline claim is **executed, not asserted**: the same
structured-cycle detection runs twice — over the raw per-source rows
(finds **0** cycles) and, as a governed skill granted to a factory-built
`AnalyticsInsightsAgent`, over the typed Context Product (finds **exactly
the ring**). **L2 entity resolution is the hero**: the layer raw data
literally lacks is the only thing that changed between the two passes.

## Run it

```
make example-08
```

(or `PYTHONPATH=src:runtime python examples/08-e2e-demo/run.py`).
Exit code 0 means the **spine ran**. It no longer means the run was
correct: per D-09, `run.py` asserts nothing and every check — generation
checksums, the baseline zero, the pinned ring, and the byte-compared
staged narration — lives in `tests/examples/test_e2e_demo_output.py`,
where a runner can fail a build:

```
PYTHONPATH=src:runtime pytest tests/examples/test_e2e_demo_output.py
```

Optional: `--live` renders the prompt artifact against the deterministic
detection outcome and prints a model-written investigation summary
(Ollama-style endpoint, configured in `artifacts/prompt.yaml`). Detection
stays deterministic and identical in both modes; `--live` never runs in
always-on CI.

Regeneration is a reviewed event: change `artifacts/scenario.yaml`,
re-pin the scenario generation checksums, and regenerate
`artifacts/expected_output.txt` from the run — landed in the same
commit as the scenario change.

## The story

The synthetic world is generated deterministically from
`artifacts/scenario.yaml` by a pure-interpreter generator, ingested
through L1 (`worker.ingest` is the only write path — single-writer),
resolved at L2, and served as a typed Context Product. The detection
skill then runs over both representations — raw rows and product — and
the staged narration of that contrast is byte-compared against
`artifacts/expected_output.txt` by the test module. The full narrated, step-by-step
walkthrough of this flow lives in the closing pointer at the end of this
README.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/scenario.yaml` | The entire synthetic world: source systems, schemas, noise rules, the ring's members, aliases, amounts, timestamps, generation checksums | `[ADAPT]`: the scenario. `[MECHANISM]`: the generator's schema keys and checksum pins |
| `artifacts/manifest.yaml` | **Read this first.** Every fabric artifact this deployment puts in force or loads, by `path`, `key`, `class_id` and `role` | `[ADAPT]`: keys and paths. `[MECHANISM]`: the entry shape and the `role` values |
| `artifacts/resolution-spec.yaml` | Entity classes, identity keys, relationship rules — the L2 hero | `[ADAPT]`: vocabulary. `[MECHANISM]`: rule field names |
| `artifacts/ingest-spec.yaml` | The L1 mapping: which source, table and columns become which payload keys, all selected by role | `[ADAPT]`: the mapping. `[MECHANISM]`: the role key names |
| `artifacts/policy-bundle.yaml` | The regime stamped onto every claim at assembly | `[ADAPT]`: the bundle. `[MECHANISM]`: envelope keys |
| `artifacts/operator-parameters-*.yaml` | One document per canonical operator category | `[ADAPT]`: values. `[MECHANISM]`: field names |
| `artifacts/perspective.yaml` | The Π role-conditioning the product is served under | `[ADAPT]`: principal and role. `[MECHANISM]`: field names |
| `artifacts/product-class.yaml` | The served class, its TTL key, and `required_operator_keys` — the authored side of Gate 2 | `[ADAPT]`: names and keys. `[MECHANISM]`: field names |
| `artifacts/product-governance.yaml` | TTL ceiling, product lifetime, corpus index version, plan id, replay record class | `[ADAPT]`: values. `[MECHANISM]`: envelope keys |
| `artifacts/half-life-table.yaml` / `debt-profile.yaml` | Per-observation-type decay and the D_c bands | `[ADAPT]`: values. `[MECHANISM]`: row shape |
| `artifacts/decision.yaml` | This run's instants and the freshness demonstration (`role: load`) | `[ADAPT]`: instants. `[MECHANISM]`: envelope keys |
| `artifacts/expected.yaml` | Both pinned detection outcomes and the payload shape (`role: load`) | `[ADAPT]`: expectations. `[MECHANISM]`: envelope keys |
| `artifacts/agent-policy-regime.yaml` / `agent-debt-profile.yaml` | The agent's axis-4 and axis-5 declarations, under the keys its refs name | `[ADAPT]`: values. `[MECHANISM]`: envelope keys |
| `artifacts/agent-definition.yaml` | The declared `AnalyticsInsightsAgent` (six specialization axes) | `[ADAPT]`: axis values. `[MECHANISM]`: definition field names |
| `artifacts/skill-catalog-entry.yaml` | The detection skill and its declared argument schema | `[ADAPT]`: skill vocabulary. `[MECHANISM]`: entry field names |
| `artifacts/skill-dispatch.yaml` | The grant request, the requesting actor, and the argument values the callable interprets | `[ADAPT]`: values. `[MECHANISM]`: envelope keys |
| `artifacts/prompt-artifact.yaml` | The versioned prompt template for `--live` | `[ADAPT]`: template text. `[MECHANISM]`: field names |
| `artifacts/live-narration.yaml` | `--live` provider endpoint, model and timeouts | `[ADAPT]`: values. `[MECHANISM]`: envelope keys |
| `artifacts/agent-registration.yaml` | Which Control Plane keys the three author-versioned documents file under (`role: load`) | `[ADAPT]`: the keys. `[MECHANISM]`: envelope keys |
| `artifacts/expected_output.txt` | The byte-compared golden narration | Regenerated only as a reviewed event (see Run it) |

## Whitepaper / CLAUDE.md sections exercised

- CLAUDE.md §6.1–§6.2 (archetype/agent separation; specialization +
  skilling with governed grant admission and replay capture)
- CLAUDE.md §6.4 (No-Hardcoding — every domain value, threshold, and
  detection parameter lives in `artifacts/`, never in code)
- CLAUDE.md §9 (examples discipline) and §10 (L1→L6 flow; `worker.ingest`
  is the only write path — single-writer)
- Whitepaper §7.3–§7.6 (graph, operators, projection, gated product),
  §7.10 (decision replay record)

## What to change first

`artifacts/scenario.yaml` — the entire synthetic world (source systems,
schemas, noise rules, the ring's members, aliases, amounts, and
timestamps) is that one versioned artifact; the generator is a pure
interpreter. Change the scenario to make your own demo, re-pin the
checksums, and regenerate `artifacts/expected_output.txt` as a reviewed
event.

## What would fail

| Invariant | What would fail here |
| --- | --- |
| Deterministic generation | The scenario generation checksums pinned in `artifacts/scenario.yaml` not matching the generated rows |
| The headline is executed, not asserted | The raw-rows pass finding anything but 0 cycles, or the product pass finding anything but exactly the planted ring |
| Single-writer (CLAUDE.md §10) | Any write path into the graph other than `worker.ingest` |
| No-Hardcoding (CLAUDE.md §6.4) | A domain value, threshold, or detection parameter appearing in code instead of `artifacts/` |
| Reviewed regeneration | `artifacts/expected_output.txt` differing from the staged narration — the byte-compare fails rather than silently regenerating |
| One artifact class, one document | A `*.yaml` under `artifacts/` carrying two classes: no honest `$schema` header exists for it, and `make schema-headers DIR=examples/08-e2e-demo/artifacts` says so |
| Author-versioned governance (D-05) | An agent definition, prompt artifact or skill catalog entry named by `manifest.yaml`: `load_and_boot` would register it through `register_typed`, silently skipping the hash-verified `artifact_version` bump check |

The narrated, step-by-step walkthrough — how raw rows fold into context,
stage by stage, with every code and artifact excerpt literal-included —
is [public/tutorial/demo-walkthrough.md](../../public/tutorial/demo-walkthrough.md).
