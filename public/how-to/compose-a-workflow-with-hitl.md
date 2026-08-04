# Compose a workflow with a human-in-the-loop gate

Run a multi-step process across several agents, suspend it on a human
approval gate, resume it when the approval arrives, and find the human's
action in the Decision Replay record afterwards.

Two SDK extensions carry this page. The Orchestration Layer (CLAUDE.md §8.1)
gives you a workflow that is a state machine with explicit states,
transitions, terminal conditions, and exception paths that are ordinary
transitions rather than error handling — and whose
definition is a Control Plane artifact, not code. The HITL primitives
(CLAUDE.md §8.2) give you the approval gate, the escalation route, the
override boundary, and the review queue, each of which writes to the replay
record by construction rather than by an opt-in hook. There is no path
through the HITL surface that produces an unrecorded human action.

Everything below is literal-included from `examples/05-workflow-hitl`, which
runs in CI.

## Before you start

You need a fabric serving at least one typed Context Product, and an agent
whose output is worth gating. You also need to decide who the approver is —
identity binding is a deployment question, and the SDK does not ship an
approver directory. See
[manage keys and secrets](security-and-deployment.md) for the signed-binding
posture.

Run the worked example with:

```sh
make example-05
```

## Step 1 — declare the process

Steps, transitions, terminal states, and exception routing all live in a
workflow artifact. Each step is a skill invocation, an agent invocation, or a
HITL gate; an agent step names an agent *definition*, never a harness, so
which runtime executes it is resolved later at the adapter binding. The
[workflow definitions reference](../reference/artifacts/workflow-definitions.md)
documents the fields:

```yaml
--8<-- "examples/05-workflow-hitl/artifacts/workflow.yaml"
```

The approval policy is a separate artifact, so who may approve what — and
whether a signed binding is required at all — moves without touching the
process shape:

```yaml
--8<-- "examples/05-workflow-hitl/artifacts/hitl.yaml"
```

## Step 2 — construct the workflow

The driver reads those artifacts and hands them to the orchestration
primitive. See the
[orchestration and workflow Protocols](../reference/protocols/orchestration-and-workflow.md)
for the surface, including the adapter seam for external engines when you
outgrow the in-fabric one:

```py
--8<-- "examples/05-workflow-hitl/run.py:workflow-construct"
```

## Step 3 — run until it suspends

Execution advances through the state machine and stops at the gate. Suspension
is a persisted state at the Control Plane boundary, not a blocked thread — the
process can wait as long as a human takes:

```py
--8<-- "examples/05-workflow-hitl/run.py:workflow-suspend"
```

## Step 4 — record the approval

The approval carries the approver's identity, the time, the Context Product
the approver actually saw, and any annotations. Those four together are what
make the action replayable rather than merely logged. The
[HITL Protocols](../reference/protocols/hitl.md) document the typed decision
values:

```py
--8<-- "examples/05-workflow-hitl/run.py:hitl-approval"
```

Then watch the refusals. An approval from an unauthorized principal, or one
that fails its binding check, is refused as a typed value — the fail-closed
path is exercised deliberately, because a gate that has never refused is not
evidence of anything:

```py
--8<-- "examples/05-workflow-hitl/run.py:hitl-refusals"
```

And the admitted case, for contrast:

```py
--8<-- "examples/05-workflow-hitl/run.py:hitl-admitted"
```

## Step 5 — resume

Resumption picks the suspended state back up and runs to a terminal state.
Exception paths are ordinary transitions here, not error handling bolted on
afterwards, so an escalation route is as inspectable as the happy path:

```py
--8<-- "examples/05-workflow-hitl/run.py:workflow-resume"
```

## Step 6 — find the human in the replay record

The workflow trace extends the record's perspective-conditioning and
generation-path dimensions, and the human action lands with it. Replaying the
decision replays it against the approval that was actually given — see
[replay anatomy](../concepts/replay-anatomy.md):

```py
--8<-- "examples/05-workflow-hitl/run.py:hitl-replay"
```

## What to change first

Work in this order.

First `artifacts/workflow.yaml` and `artifacts/task.yaml` — the step names,
transitions, terminal states, and exception routing of your own process. Then
update the drive block in `artifacts/hitl.yaml` so the expected gate, resume
decision, and failing step match what you just declared.

Second `artifacts/hitl.yaml` itself — your approver and reviewer identities,
and the pinned item a reviewer sees. Flip `signed_binding_required` and re-run
to watch behaviour change with no code edit at all.

Third `artifacts/tokens.yaml` and `artifacts/scope_mapping.yaml` — your token
table and authorization statement. Add a scope to the mapping and re-run to
watch the refusal leg change, which proves the refusal comes from the
artifact rather than from the driver.

If you need durable execution at the scale of a dedicated workflow engine,
implement the orchestration adapter Protocol against it rather than growing
this primitive; that boundary is deliberate.
