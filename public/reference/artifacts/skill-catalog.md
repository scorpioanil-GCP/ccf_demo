# Skill catalog entries

A catalog entry declares a capability and, crucially, what that capability *requires* — the
scopes and Context Products it needs in order to run. Registration is discovery, not
permission: the catalog is deliberately wider than any single agent's bound set, and the
governance check that decides whether an agent may bind an entry happens at grant time against
the agent's policy regime. This is the Core Agent Types pillar's capability channel.

Five binding types cover how a skill is actually reached — a local callable, a harness tool, an
MCP resource, a peer endpoint, or a declared procedure. They are a discriminated union
selected by the entry's skill type, so a catalog entry carries exactly one of them and the
binding's own fields are validated against that choice.

::: ccf.skills.catalog.SkillCatalogEntry

::: ccf.skills.catalog.SkillRequirements

::: ccf.skills.catalog.SkillArgumentSchema

::: ccf.skills.catalog.SkillArgumentProperty

::: ccf.skills.catalog.LocalCallableBinding

::: ccf.skills.catalog.ToolBinding

::: ccf.skills.catalog.McpBinding

::: ccf.skills.catalog.PeeringBinding

::: ccf.skills.catalog.ProcedureBinding

## Worked example

One catalog entry, whose declared requirements sit inside the agent's governance envelope. Two
more sit beside it in that example: one permitted but never granted, and one whose requirements
exceed the envelope so the compatibility check refuses the grant. Every entry is one document.

```yaml
--8<-- "archive/examples/02-skilling/artifacts/skill-catalog-enrollment-metrics.yaml"
```
