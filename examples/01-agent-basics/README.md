# 01 — Agent Basics: archetype/agent separation, all six axes

Declare an agent from the `AnalyticsInsightsAgent` archetype via a
definition artifact, construct it through the **Agent Factory** — the only
supported construction path — and run it against a small field-service
fabric's served Context Product, keyless and model-free on SQLite and the
file-backed ArtifactStore.

The archetype is SDK mechanism; the agent (`response-time-analytics`) is a
declared, versioned Control Plane artifact in `artifacts/agent.yaml`. No
agent exists in code anywhere in this directory (CLAUDE.md §6.1).

## Run it

```sh
make example-01
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/01-agent-basics/run.py
```

The driver is an asserted program: exit code 0 means every invariant below
held; any failure exits nonzero. CI treats nonzero as red.

## What it demonstrates

| Invariant | What would fail here |
| --- | --- |
| archetype/agent separation (§6.1) | an agent defined in code — identity would not derive from the definition artifact's content hash |
| factory-only construction (§6.4) | a direct `Agent(...)` call, or a definition resolved outside Control Plane resolution at pinned versions |
| axis 1 — archetype binding (D-IMPL-19) | the composed components would not realize the declared archetype list, in order |
| axis 2 — context contract | the served `work-order-context` product would be refused at `consume`, or an off-contract product admitted |
| axis 3 — perspective | dimension 4's role would diverge from the definition's declared Π role |
| axes 4/5 — policy regime, half-life/debt profile | an unresolvable or unpinned (latest-tagged) ref would fail construction at the front door |
| axis 6 — instruction bindings (D-13) | a prompt-parameter mismatch against the resolved artifact would fail construction; an inline prompt in code would fail CINV-01 |
| replay dimension 4 (D-06) | the record would not answer *which agent, which version, which composition* from the store alone |
| deterministic LLM seam (D-12) | a model call or an API key — the scripted analyst's content is artifact data |

## What it exercises

- **Whitepaper:** Ch. 3 (agents as consumers of the fabric), §7.6 (Context
  Product Contract), §7.10.1 (Decision Replay dimension 4).
- **CLAUDE.md:** §6.1 (archetypes vs agents), §6.2 (the six specialization
  axes, channel 1), §6.3 (`AnalyticsInsightsAgent`), §6.4 (Agent Factory +
  the No-Hardcoding Rule).

## Domain rationale (D-09)

This example is a **field-service / logistics** scenario (a dispatch
analyst's view over a technician, urgent and routine work orders, and a
restricted site): a scheduling/telemetry domain exercising temporal
analysis far from banking (00-quickstart) — per D-IMPL-52, the suite
deliberately crosses unrelated domains. All domain values live in
`artifacts/`; the data is synthetic and fictional.

## The No-Hardcoding Rule, made visible

`run.py` contains no prompt text, no agent definition, no threshold and no
expected result — the agent's six axes live in `artifacts/agent.yaml`, the
prompt template in `artifacts/prompt.yaml`, the fabric's values in the
other artifacts, and the scripted analyst's canned outputs in
`artifacts/analysis_output.yaml`. Delete `artifacts/` and the driver has
nothing meaningful to run (CLAUDE.md §6.4).

## What to change first

`artifacts/agent.yaml` **is** the specialization surface:

- change any of the six axes and the artifact's content hash — the agent's
  identity — changes with it (a new agent version, D-05);
- point `context_contract` at your own product class and re-author the
  fabric artifacts (`ontology.yaml`, `events.yaml`, `controlplane.yaml`)
  to serve it;
- bind your own prompt artifact under axis 6 — the parameters must match
  its declaration or construction fails (D-13).

Skilling (channel 2) deliberately does not appear here — that is
`examples/02-skilling`.
