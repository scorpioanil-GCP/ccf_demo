# Task definition artifacts

A task definition declares a procedural unit of work as data: an ordered step sequence the Task
Factory interprets, never a routine anyone writes in code. Tasks belong to the Core Agent Types
pillar and are the unit an orchestration node most often invokes. Author one when the work has
deterministic structure worth pinning and replaying, rather than being left to a harness loop
to improvise.

::: ccf.agents.definitions.TaskDefinition

::: ccf.agents.definitions.TaskStep

## Worked example

```yaml
--8<-- "archive/examples/05-workflow-hitl/artifacts/task-definition.yaml"
```
