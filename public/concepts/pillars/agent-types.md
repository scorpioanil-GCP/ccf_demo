# Pillar: Core Agent Types

This pillar answers "what *is* an agent, in CCF terms?" — and the answer has
two halves that the SDK keeps deliberately apart.

## Archetypes are code; agents are artifacts

An **archetype** is a functional template the SDK ships. It bundles
mechanism-level patterns — execution shape, how that class of agent interacts
with the fabric, what it owes the replay record — and carries no identity, no
prompts, no skills, no policy bindings, and no domain values. Archetypes live
in the library and are never instantiated directly.

An **agent** is a declared, versioned artifact: a named unit of decisioning
produced by the factory from one or more archetypes plus a specialization
record plus skill bindings. Agents are Control Plane data, not code. Two
deployments running the identical SDK release can operate entirely different
agent populations without a line of diverging source.

Keeping them apart buys three things: agent identity and version become
answerable from the replay record alone; an agent is harness-neutral by
construction, because nothing in a definition names a harness; and the library
never accumulates anyone's domain values.

The SDK ships six archetypes — workflow/task, document intelligence, analytics
and insights, monitoring and surveillance, content generation, and context
assembly. They are functional categories, not an exclusive hierarchy: a
monitoring agent that also emits typed products for downstream consumers
composes both patterns.

## Two channels of specialization

**Channel 1 — specialization** is the identity-and-constraint channel, fixed in
the definition artifact and versioned with it. Changing any of its six axes
produces a new agent version: archetype binding, context contract, perspective,
policy regime, half-life and debt profile, and instruction bindings (references
to versioned prompt artifacts — never inline text).

**Channel 2 — skilling** is the capability channel. Skills are typed, governed
capabilities in a catalog; they bind to an agent by reference and can be
granted, upgraded, or revoked over its life *without re-declaring it*. The
policy regime from channel 1 defines what an agent *may* bind; skilling decides
what it *does* bind, and the Control Plane refuses a grant whose declared
requirements exceed that envelope.

The separation is what makes capability agility safe: identity stays stable for
audit, and the skill-set in force at decision time is part of the replay record
— so a decision replays against the skills the agent actually held, not the
ones it holds today.

The diagram places the mechanism on the left and the user's values on the
right, with the factory as the only construction path between them, and shows
both channels converging on the replay record.

```mermaid
--8<-- "public/diagrams/pillar-agent-types.mmd"
```

## The harness seam

CCF does not ship an agent loop and does not absorb one. The reasoning loop,
tool-calling, planning, and sub-agent semantics belong to whatever harness you
already use. What CCF supplies is what no harness provides: governed, typed,
replay-ready context going in, and policy-verified, lineage-preserving effects
coming out.

A conforming adapter binds four seams — context injection (typed products only,
never raw graph access), skill exposure (exactly the currently-bound set),
effect capture (routed back through assembly, so the harness never holds a
write handle), and replay hooks.

```mermaid
--8<-- "public/diagrams/seam-harness-adapter.mmd"
```

## Where this lives

- [Agents][agents] — the agent base, archetypes, and the factory.
- [Agent definitions][agentdef] — the channel-1 artifact schema.
- [Task definitions][taskdef] — task artifacts read by the same factory.
- [Prompt artifacts][prompts] — versioned instruction bindings.
- [Skill catalog][catalog] — typed capability registration.
- [Skill grants][grants] — the channel-2 grant and revocation records.
- [Harness adapter][harness] — the four-seam protocol and its reference
  adapters.

Related concepts: [invariants][invariants] covers the No-Hardcoding Rule and
the zero-harness-imports rule that make this pillar hold.

[agents]: ../../reference/protocols/agents.md
[harness]: ../../reference/protocols/harness-adapter.md
[agentdef]: ../../reference/artifacts/agent-definitions.md
[taskdef]: ../../reference/artifacts/task-definitions.md
[prompts]: ../../reference/artifacts/prompt-artifacts.md
[catalog]: ../../reference/artifacts/skill-catalog.md
[grants]: ../../reference/artifacts/skill-grants.md
[invariants]: ../invariants.md
