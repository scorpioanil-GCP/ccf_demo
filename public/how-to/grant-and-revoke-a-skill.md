# Grant and revoke a skill

Give a running agent a new capability through the Control Plane, use it, and
take it away again — without editing the agent's definition artifact and
without redeploying anything.

This is channel 2 of the two-channel specialization model (CLAUDE.md §6.2).
Channel 1 — the six specialization axes — fixes *who the agent is*, and every
change to it mints a new agent version. Skilling governs *what the agent can
currently do*, and it moves independently. The single assertion worth
carrying away from this page is that the agent's definition artifact is
byte-identical before and after a full grant/exercise/refuse/revoke cycle:
capability changed four times, identity never moved.

Everything below is literal-included from `archive/examples/02-skilling`, which runs
in CI on every commit.

## Before you start

You need a booted fabric with a factory-constructed agent — the
[adopter's guide](../tutorial/adopters-guide.md) walks that part. You also
need a policy regime on the agent that states which capability scopes it is
*permitted* to bind. That envelope is specialization axis 4, and it is the
thing the governance check tests every grant against.

Run the worked example at any point with:

```sh
PYTHONPATH=src:runtime python archive/examples/02-skilling/run.py
```

Exit 0 means every assertion held, including the refusal — the example fails
if the governance check does not fire.

## Step 1 — declare the catalog

A skill is a typed, governed entry in a catalog, never a Python callable
someone imported. Four kinds ship: a tool, a local callable, an MCP resource,
and a peering endpoint serving a remote Context Product. Each entry declares
the requirement scopes it needs; those scopes are opaque identifiers that a
policy regime either permits or does not. The
[skill catalog reference](../reference/artifacts/skill-catalog.md) documents
the typed shape:

```yaml
--8<-- "archive/examples/02-skilling/artifacts/skill-catalog-enrollment-metrics.yaml"
```

The driver registers what the artifact declared. Note that registration binds
nothing — a catalog entry is an offer, not a capability:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-catalog"
```

## Step 2 — grant

A grant is an audited Control Plane action that binds a catalog entry to a
named agent at a pinned version. Before the bind takes effect, the tier-1
compatibility check compares the skill's declared requirement scopes against
the agent's permitted envelope. See the
[skill grants reference](../reference/artifacts/skill-grants.md) for the
grant document's fields and the
[agent Protocols](../reference/protocols/agents.md) for the surface the
factory produces:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-grant"
```

## Step 3 — exercise it

Once bound, the skill is invocable through the agent, and the invocation is
governed context in, governed effect out — the same posture a harness adapter
exposes at its skill-exposure seam:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-exercise"
```

## Step 4 — watch an impermissible grant get refused

This is the part worth reading twice. A skill whose declared scopes exceed
the agent's policy envelope is refused, and the refusal is a *typed returned
value* naming the exact excess scopes — not an exception, not a log line, and
not something a caller can waive:

```py
--8<-- "archive/examples/02-skilling/run.py:skill-refusal"
```

Widening the envelope to admit that skill is an axis-4 change, which means a
new agent version. That is the channel separation made concrete: you cannot
get the capability by asking harder at the skilling layer.

## Step 5 — revoke, and check the replay record

Revocation is the mirror action, equally audited. What matters for audit is
that the skill-set in force at decision time is captured in the Decision
Replay record, so a past decision replays against the skills the agent
actually held then, not the ones it holds now — see
[replay anatomy](../concepts/replay-anatomy.md) and the
[HITL and audit Protocols](../reference/protocols/hitl.md):

```py
--8<-- "archive/examples/02-skilling/run.py:skill-revoke"
```

## What to change first

`artifacts/skills.yaml` is your capability surface. Add your own catalog
entries under `skills:` — the requirement scopes are yours to name, and your
policy regimes decide which of them are reachable. Nothing binds until you
add a grant document under `grants:`.

Then widen or narrow `skill_governance.permitted_scopes` in
`artifacts/agent.yaml` and re-run. Widening it far enough to admit the
example's deliberately-impermissible skill will fail the run, because the
example *requires* the refusal to fire — update the expectation blocks in the
same commit, as a reviewed change.

Finally, set `grant_requires_approval: true` to route grants through a tier-2
approval sink of your own. That turns skilling itself into a human-gated
action; see
[compose a workflow with HITL](compose-a-workflow-with-hitl.md) for the gate
machinery.
