# CCF SDK

The **Cognitive Context Fabric (CCF) SDK** is a general-purpose library and
runtime for constructing, governing, and serving decision-ready context to AI
agents — and for building, orchestrating, and operating specialized agents on
top of that fabric. It layers onto any agent harness as the trust-and-control
plane: it never absorbs the agent loop, and it does not ship one.

## The five Common Pillars

The SDK is organized around five pillars that match how teams actually build
agentic systems:

- **[Data and Context Layer](concepts/pillars/data-context.md)** — the fabric
  that derives typed, replay-ready Context Products from first-party,
  third-party, and agent-produced content.
- **[Orchestration Layer](concepts/pillars/orchestration.md)** — composing
  agents and steps into suspendable, replayable workflows.
- **[Core Agent Types](concepts/pillars/agent-types.md)** — six functional
  archetypes shipped as mechanism, from which agents are declared as
  versioned artifacts.
- **[Human in the Loop and Control](concepts/pillars/hitl.md)** — approval,
  escalation, override, and review, audited by construction.
- **[Experience Layer](concepts/pillars/experience.md)** — the front doors:
  MCP egress, the `ccf` CLI, and the HTTP API.

## Start here

If you are reading this for the first time, take one path and take it in
order:

1. Read the **[adopter's guide](tutorial/adopters-guide.md)** end to end — it
   goes from install to a governed, replayable deployment.
2. Read the **pillar you actually care about** from the five linked above.
3. Read the **Reference surface that realizes it** — the
   [Protocols](reference/protocols/agents.md) it is built from and the
   [definition artifacts](reference/artifacts/agent-definitions.md) you
   declare against it.

Everything else is reachable from the four sections below.

## The four sections

- **Tutorial** — learning-oriented, read in order. The
  [adopter's guide](tutorial/adopters-guide.md) is the guided path from
  install to a running deployment;
  [how data folds into context](tutorial/demo-walkthrough.md) walks the
  end-to-end demo signal by signal.
- **How-to guides** — task-shaped recipes for a specific job:
  [managing keys and secrets](how-to/security-and-deployment.md),
  [granting and revoking a skill](how-to/grant-and-revoke-a-skill.md),
  [running agents cross-process](how-to/run-agents-cross-process.md),
  [composing a workflow with HITL](how-to/compose-a-workflow-with-hitl.md),
  [swapping the artifact store](how-to/swap-the-artifact-store.md), and
  [binding a harness adapter](how-to/bind-a-harness-adapter.md).
- **Concepts** — the ideas behind the mechanism: one page per
  [pillar](concepts/pillars/data-context.md) (five in all), plus the
  [architectural invariants](concepts/invariants.md), the
  [anatomy of a replay record](concepts/replay-anatomy.md), and the
  [whitepaper cross-reference](concepts/whitepaper-index.md).
- **Reference** — the precise surface: twelve
  [Protocol pages](reference/protocols/storage-and-graph.md), eight
  [definition artifact schemas](reference/artifacts/agent-definitions.md), the
  [HTTP contract](reference/http-api.md), and the
  [performance envelope](reference/performance.md).
