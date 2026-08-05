# Workflow definition artifacts

A workflow definition is a state machine expressed as data: states, transitions, terminal
conditions, and the exception paths a node can yield to. It belongs to the Orchestration Layer
pillar. Because the definition is an artifact rather than code, a workflow can suspend on a
human gate, persist at the Control Plane boundary, and resume later — and its execution trace
lands in the replay record by construction. Author one when several agents or steps have to be
coordinated; reach for an external orchestrator only when durable execution at Temporal scale
is genuinely required.

::: ccf.workflow.definitions.WorkflowDefinition

::: ccf.workflow.definitions.WorkflowTransition

## Worked example

```yaml
--8<-- "examples/05-workflow-hitl/artifacts/workflow-definition.yaml"
```
