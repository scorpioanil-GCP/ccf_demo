# Agent and archetype surface

Archetypes are SDK mechanism; agents are declared, versioned Control Plane artifacts. The
separation is the point — nothing on this page is an agent, and an agent found in library code
would be a defect. The factory surfaces below are the only supported route from a definition
artifact to a running agent, and the composition surface is how several archetypes combine
without a hierarchy for adopters to navigate.

::: ccf.agents.archetypes.ArchetypeComponent

::: ccf.agents.archetypes.ReplayObligation

::: ccf.agents.archetypes.ConfigurationDefault

::: ccf.agents.factory.AgentFactory

::: ccf.agents.factory.TaskFactory

::: ccf.agents.factory.Task

::: ccf.agents.factory.TaskIdentity

::: ccf.agents.agent.Agent

::: ccf.agents.agent.AgentIdentity

::: ccf.agents.agent.EmittedEffect

::: ccf.agents.composition

::: ccf.agents.prompts

::: ccf.agents.errors
