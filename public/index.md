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

## Where to go next

- **[Tutorial](tutorial/adopters-guide.md)** — a guided path from install to a
  governed, replayable deployment.
- **How-to guides** — task-shaped recipes, starting with
  [granting and revoking a skill](how-to/grant-and-revoke-a-skill.md).
- **Concepts** — the ideas behind the mechanism, including the
  [architectural invariants](concepts/invariants.md) and the
  [anatomy of a replay record](concepts/replay-anatomy.md).
- **Reference** — the [Protocol surface](reference/protocols/agents.md), the
  [definition artifact schemas](reference/artifacts/agent-definitions.md), and
  the [HTTP API](reference/http-api.md).
