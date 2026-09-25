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

Everything below is literal-included from `archive/examples/05-workflow-hitl`, which
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
PYTHONPATH=src:runtime python archive/examples/05-workflow-hitl/run.py
```

## Step 1 — declare the process

Steps, transitions, terminal states, and exception routing all live in a
workflow artifact. Each step is a skill invocation, an agent invocation, or a
HITL gate; an agent step names an agent *definition*, never a harness, so
which runtime executes it is resolved later at the adapter binding. The
[workflow definitions reference](../reference/artifacts/workflow-definitions.md)
documents the fields:

```yaml
--8<-- "archive/examples/05-workflow-hitl/artifacts/workflow-definition.yaml"
```

Who may approve at a gate is a *separate* artifact, so the approver role and the
quorum move without touching the process shape — and the two changes are
separately versioned and separately audited:

```yaml
--8<-- "archive/examples/05-workflow-hitl/artifacts/approval-policy.yaml"
```

Whether a signed principal binding is required at all is a third, separate
statement. Flip it and the transport's behaviour changes on the next
submission, with no code edit:

```yaml
--8<-- "archive/examples/05-workflow-hitl/artifacts/hitl-policy.yaml"
```

## Step 2 — boot the fabric and construct the workflow

One call over the deployment manifest parses every artifact the manifest names,
registers the ones it marks `role: register`, and boots the fabric on the
resulting pins. The four author-versioned definition classes are outside *this*
manifest by the example's choice, not by necessity: a manifest may name them as
`registration: versioned`, and `load_and_boot` then registers them through
`register_versioned` with its bump check — what it refuses, at preflight, is
`registration: typed` for such a class. The driver keeps the four calls so that
check stays visible at the call site:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:boot"
```

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:register-definitions"
```

The engine is then constructed with its injected seams and the workflow comes
from the factory. See the
[orchestration and workflow Protocols](../reference/protocols/orchestration-and-workflow.md)
for the surface, including the adapter seam for external engines when you
outgrow the in-fabric one:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:workflow-construct"
```

## Step 3 — run until it suspends

Execution advances through the state machine and stops at the gate. Suspension
is a persisted state at the Control Plane boundary, not a blocked thread — the
process can wait as long as a human takes:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:workflow-suspend"
```

## Step 4 — record the approval

The approval carries the approver's identity, the time, the Context Product
the approver actually saw, and any annotations. Those four together are what
make the action replayable rather than merely logged. The
[HITL Protocols](../reference/protocols/hitl.md) document the typed decision
values:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-approval"
```

Then watch the refusals. An approval from an unauthorized principal, or one
that fails its binding check, is refused as a typed value — the fail-closed
path is exercised deliberately, because a gate that has never refused is not
evidence of anything. The spine drives all four and hands back the responses;
the assertions that each one is the *right* refusal, and that none of them
reached the authority path, live in
`tests/examples/test_workflow_hitl_output.py`:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-refusals"
```

And the admitted case, for contrast:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-admitted"
```

## Step 5 — resume

Resumption picks the suspended state back up and runs to a terminal state.
**The human action is a precondition, not a convention:** the engine reads the
HITL authority path and refuses to leave a gate unless a recorded action for
that exact suspension is on it, so the decision string names the route and
never supplies the permission. Exception paths are ordinary transitions here,
not error handling bolted on afterwards, so an escalation route is as
inspectable as the happy path:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:workflow-resume"
```

## Step 6 — find the human in the replay record

The workflow trace extends the record's perspective-conditioning and
generation-path dimensions, and the human action lands with it. Replaying the
decision replays it against the approval that was actually given — see
[replay anatomy](../concepts/replay-anatomy.md):

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:hitl-replay"
```

## Step 7 — review before release, and escalate on failure

The other two HITL primitives the example exercises follow the same shape. A
review queue holds generated content, with its passage-level lineage attached,
until a second named human releases it; the release lands on dimension 2 exactly
as the approval did:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:review-queue"
```

An exception path is an ordinary transition, so a failing node routes to the
handler its definition declares and the transition is traced and audited like
any other:

```py
--8<-- "archive/examples/05-workflow-hitl/run.py:exception-path"
```

## What to change first

Work in this order.

First `artifacts/workflow-definition.yaml` and `artifacts/task-definition.yaml`
— the step names, transitions, terminal states, and exception routing of your
own process. Then update the `drive` block in `artifacts/hitl-drive.yaml` so the
expected gate, resume decision, and failing step match what you just declared,
and point `artifacts/manifest.yaml` at any artifact you renamed.

Second `artifacts/hitl-drive.yaml` itself — your approver and reviewer
identities, and the pinned item a reviewer sees — plus
`artifacts/approval-policy.yaml` for who may approve. Flip
`signed_binding_required` in `artifacts/hitl-policy.yaml` and re-run to watch
behaviour change with no code edit at all.

Third `artifacts/tokens.yaml` and `artifacts/scope-mapping.yaml` — your token
table and authorization statement. Add a scope to the mapping and re-run to
watch the refusal leg change, which proves the refusal comes from the
artifact rather than from the driver.

If you need durable execution at the scale of a dedicated workflow engine,
implement the orchestration adapter Protocol against it rather than growing
this primitive; that boundary is deliberate.
