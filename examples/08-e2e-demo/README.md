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
Exit code 0 means every assertion held — generation checksums, the
baseline zero, the pinned ring, and the byte-compared staged narration.

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
`artifacts/expected_output.txt`. The full narrated, step-by-step
walkthrough of this flow lives in the closing pointer at the end of this
README.

## Artifact-by-artifact

| Artifact | What it declares | Yours to edit vs mechanism |
| --- | --- | --- |
| `artifacts/scenario.yaml` | The entire synthetic world: source systems, schemas, noise rules, the ring's members, aliases, amounts, timestamps, generation checksums | `[ADAPT]`: the scenario. `[MECHANISM]`: the generator's schema keys and checksum pins |
| `artifacts/ontology.yaml` | Entity classes, relationship types, resolution rules | `[ADAPT]`: vocabulary. `[MECHANISM]`: rule field names |
| `artifacts/controlplane.yaml` | Policy bundle, operator parameters, product class | `[ADAPT]`: values. `[MECHANISM]`: key names |
| `artifacts/halflife.yaml` | Per-observation-type decay declarations | `[ADAPT]`: values. `[MECHANISM]`: key names |
| `artifacts/agent.yaml` | The declared `AnalyticsInsightsAgent` (six specialization axes) | `[ADAPT]`: axis values. `[MECHANISM]`: definition field names |
| `artifacts/skills.yaml` | The detection skill catalog entry and grant | `[ADAPT]`: skill vocabulary. `[MECHANISM]`: `skills`/`grant` structure |
| `artifacts/prompt.yaml` | The versioned prompt template for `--live` | `[ADAPT]`: template, endpoint. `[MECHANISM]`: field names |
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

The narrated, step-by-step walkthrough — how raw rows fold into context,
stage by stage, with every code and artifact excerpt literal-included —
is [public/tutorial/demo-walkthrough.md](../../public/tutorial/demo-walkthrough.md).
