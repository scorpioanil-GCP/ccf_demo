# examples/08-e2e-demo — the fraud ring raw data cannot see (DEMO-01..03)

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

## What it exercises

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

## The full story

The narrated, step-by-step walkthrough — how raw rows fold into context,
stage by stage, with every code and artifact excerpt literal-included —
is [docs/demo-walkthrough.md](../../docs/demo-walkthrough.md).
