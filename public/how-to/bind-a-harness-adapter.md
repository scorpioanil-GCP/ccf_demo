# Bind a harness adapter

Take one agent definition and run it unmodified under a second agent harness,
getting equivalent Context Product consumption and equivalent governed replay
records from both.

This is the load-bearing claim of CLAUDE.md §7.3. CCF layers onto whatever
harness you already use as the trust-and-control plane; it does not absorb the
reasoning loop and it does not ship one. The loop, the planning behaviour, and
the sub-agent semantics stay with the harness. What CCF supplies is what no
harness provides: governed, typed, replay-ready context going in, and
policy-verified, lineage-preserving effects coming out. No module in the SDK
core imports a harness — a CI lint enforces it — so harness code exists only
behind the adapter Protocol.

Everything below is literal-included from `archive/examples/03-harness-portability`,
which drives real loop machinery from three harnesses in CI and asserts
byte-level equivalence.

## Before you start

You need an agent definition and the fabric it consumes from. You do not need
model credentials: the CI leg runs real harness machinery over scripted,
no-model transports, with a guard that fails the run if anything opens a
socket. A live leg exists and is opt-in.

Run the worked example with:

```sh
PYTHONPATH=src:runtime python archive/examples/03-harness-portability/run.py --mode deterministic
```

## The four seams

A conforming adapter binds four seams, and it is worth naming them before
looking at code, because everything below is one of the four:

1. **Context injection** — typed Context Products into whatever the harness
   uses for context assembly, without the harness ever touching the graph or
   raw signal.
2. **Skill exposure** — the agent's *currently bound* skill-set surfaced as
   the harness's tools. A skill the agent has not been granted does not exist
   from the harness's point of view; see
   [grant and revoke a skill](grant-and-revoke-a-skill.md).
3. **Effect capture** — harness outputs routed back through governed emission
   or assembly write-back. A harness never acquires a write handle to the
   graph, so the single-writer invariant holds across the adapter boundary.
4. **Replay hooks** — model version, prompt-artifact version, and execution
   trace captured into the five-dimension record.

The [harness adapter Protocols](../reference/protocols/harness-adapter.md)
page documents the typed surface for each.

## Step 1 — write one definition that names no harness

The definition carries the six specialization axes and nothing harness-shaped.
That is what makes it portable: there is nothing in it to change when the
runtime changes. The
[agent definitions reference](../reference/artifacts/agent-definitions.md)
documents the schema:

```yaml
--8<-- "archive/examples/03-harness-portability/artifacts/agents/agent-definition.yaml"
```

Per-harness deployment values — session vocabulary, reported model
identifiers — live in their own artifact, well away from the agent's identity:

```yaml
--8<-- "archive/examples/03-harness-portability/artifacts/harnesses.yaml"
```

## Step 2 — construct the agent once

One factory call, one agent object, handed to every adapter. The instructions
are rendered exactly once by the fabric, so no leg can quietly receive
different text. See the
[agent Protocols](../reference/protocols/agents.md):

```py
--8<-- "archive/examples/03-harness-portability/run.py:harness-agent"
```

## Step 3 — wire the replay hook

Seam 4. The record's product address is derived from the product recovered out
of *this leg's own carrier*, not from what the fabric handed over — so an
adapter that corrupted what it delivered moves the address and the comparison
goes red naming the field:

```py
--8<-- "archive/examples/03-harness-portability/run.py:harness-replay-hook"
```

## Step 4 — drive every leg with the same inputs

Each leg runs the harness's genuine loop machinery over the same agent, the
same product, and the same rendered instructions. Everything a leg is judged on
is recovered from *that leg's own* carrier, so the values being compared in the
next step are three independently produced values rather than one shared one:

```py
--8<-- "archive/examples/03-harness-portability/run.py:harness-legs"
```

## Step 5 — assert equivalence on what CCF governs

The equivalence assertions are executed by `pytest`, in
`tests/examples/test_harness_portability_output.py`, not by the driver — a
printed summary nobody reads was never a guarantee. Two of them carry the
claim:

- **Consumption.** The Context Product recovered from each harness's native
  carrier is byte-identical across all legs, and identical to what the fabric
  admitted. That is seam 1 in evidence.
- **Replay.** The governed replay fields are compared field by field, and the
  divergence message names the field and both harnesses.

Seam 3 rides along: every effect went through governed emission, so there is
one emission address whichever harness drove it. Harness attribution
deliberately stays *out* of the governed set and is asserted to differ per leg —
the point is that what CCF governs is identical while the harnesses stay
distinguishable. This is the set the comparison covers:

```py
--8<-- "archive/examples/03-harness-portability/legs/deterministic.py:harness-governed-fields"
```

## What to change first

Point the agent definition at your own product schema and policy regime, swap
`artifacts/resolution-spec.yaml` and `artifacts/events.yaml` for your domain,
and put your deployment's model identifiers and session vocabulary in
`artifacts/harnesses.yaml`. Every document in force is enumerated by
`artifacts/manifest.yaml`, so a new artifact is not in force until it is named
there. On the next run expect the served payload to change; review it and
update `artifacts/expected.yaml` in the same commit.

The driver and the leg modules are mechanism and should not need editing. If
you are adding a *new* harness rather than adapting an existing one, implement
the adapter Protocol under the runtime adapter tree — never in the core — and
add a leg here so your harness is covered by the same equivalence assertions.

A harness that already speaks MCP needs no adapter merely to *consume*
products; see [run agents cross-process](run-agents-cross-process.md). The
adapter earns its keep on seams 2, 3, and 4.
