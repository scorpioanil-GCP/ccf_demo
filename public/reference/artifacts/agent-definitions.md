# Agent definition artifacts

An agent is not code. It is a declared, versioned Control Plane artifact that the Agent Factory
interprets — which is why two deployments on the same SDK release can operate entirely
different agent populations without a line of diverging code. This is the Core Agent Types
pillar's primary authoring surface, and it is where the six specialization axes are fixed:
archetype binding, context contract, perspective, policy regime, half-life and debt profile,
and instruction bindings. Changing any axis produces a new agent version. Capability changes
travel through the separate skilling channel instead.

You author one of these first, before anything else in the agent pillar.

::: ccf.agents.definitions.AgentDefinition

::: ccf.agents.definitions.ContextContract

::: ccf.agents.definitions.ConsumedProduct

::: ccf.agents.definitions.PerspectiveBinding

::: ccf.agents.definitions.InstructionBinding

::: ccf.agents.definitions.VersionedRef

## Worked example

A complete agent definition from the examples suite. Every key the factory requires is present;
nothing is elided, because a partial artifact teaches the wrong shape.

```yaml
--8<-- "examples/01-agent-basics/artifacts/agent-definition.yaml"
```
