# Pillar: Orchestration Layer

The Orchestration Layer is how several agents, several steps, and the humans
between them are managed as one governed unit of work.

## What the pillar is for

A single agent invocation is rarely the whole job. Real deployments chain a
retrieval step to an analysis step to a drafting step, pause for someone to
approve the draft, and route to a specialist when a threshold is breached. The
Orchestration Layer is where that composition lives, and its job is to make the
composition *auditable* — not merely to make it run.

The SDK's posture here is deliberately narrow. It ships a minimal workflow
primitive sufficient for in-fabric coordination, plus a protocol for handing
off to a heavyweight engine when durable execution at enterprise scale is what
you actually need. Reimplementing a durable-execution engine is explicitly out
of scope (CLAUDE.md §8.1); the escape hatch is a protocol, not a fork.

## How the SDK realizes it

The workflow primitive is a state machine with four properties that are
load-bearing rather than incidental:

- **Three node kinds.** A step is a skill invocation, an agent invocation, or a
  human gate. Agent nodes name an agent *definition*, never a harness — which
  harness executes the node is resolved at binding time, so a workflow is
  portable for the same reason an agent is.
- **Definitions are artifacts.** Workflow shapes are Control Plane artifacts
  produced through the task factory, not code constants. The No-Hardcoding Rule
  applies here as everywhere else.
- **Suspension is normal.** Execution state persists at the Control Plane
  boundary, so a workflow parked at an approval gate or waiting on a monitoring
  trigger resumes later with its trace intact.
- **Exception paths are transitions.** Yielding to an escalation is a
  first-class state transition, not error handling bolted on afterwards.

Every execution extends the replay record — the calling chain lands in the
perspective dimension and the step sequence in the generation-path dimension —
so a workflow re-runs identically under the same inputs and the same Control
Plane state.

The diagram shows the definition artifact flowing from the task factory into
the state machine, the three node kinds and where each hands off, the external
orchestrator escape hatch, and the two write-throughs to persistence: execution
state at suspend points, and the replay record itself.

```mermaid
--8<-- "public/diagrams/pillar-orchestration.mmd"
```

## Where this lives

- [Orchestration and workflow][orch] — the workflow primitive and the external
  orchestrator protocol.
- [Workflow definitions][wfdef] — the definition artifact schema for workflow
  shapes.

Adjacent pillars: gates hand off to [Human in the Loop and Control][hitl], and
agent nodes execute [Core Agent Types][agents]. The trace obligations are
described in [replay anatomy][replay].

[orch]: ../../reference/protocols/orchestration-and-workflow.md
[wfdef]: ../../reference/artifacts/workflow-definitions.md
[hitl]: hitl.md
[agents]: agent-types.md
[replay]: ../replay-anatomy.md
