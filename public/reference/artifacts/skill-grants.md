# Skill grants

A grant binds a catalog entry to an agent. It is the second specialization channel in its
entirety: capability changes over an agent's life travel through grants and revocations, and
the agent definition itself never changes. The governance model sits beside it — a policy
regime declares the envelope of what agents under that regime may bind, and a grant whose
declared requirements exceed the envelope is refused rather than narrowed. Every grant and
every revocation is an audited Control Plane action, and the skill-set in force at decision
time is part of the replay record, so a decision replays against the skills the agent actually
had rather than the skills it has now.

::: ccf.skills.grants.SkillGrant

::: ccf.skills.grants.PolicyRegimeGovernance

::: ccf.skills.grants.GrantStateRecord

## Worked example

The governance envelope in context — the policy-regime artifact an agent definition names on its
axis-4 reference, declaring the one requirement scope agents under that regime may bind and
deliberately excluding another.

```yaml
--8<-- "examples/02-skilling/artifacts/agent-policy-regime.yaml"
```
