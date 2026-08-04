# Prompt and instruction artifacts

Prompts live here and nowhere else. The No-Hardcoding Rule makes an inline instruction string in
library, runtime or example code a defect, so every instruction an agent runs under is a
versioned artifact referenced by URI from the agent definition's instruction bindings. The
payoff is replay: a decision reproduces against the exact prompt version in force at the time,
which a literal buried in a source file could never offer. This artifact class belongs to the
Core Agent Types pillar; you author one alongside each agent definition.

::: ccf.agents.definitions.PromptArtifact

## Worked example

```yaml
--8<-- "examples/01-agent-basics/artifacts/prompt.yaml"
```
