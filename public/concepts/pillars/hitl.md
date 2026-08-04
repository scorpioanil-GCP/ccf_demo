# Pillar: Human in the Loop and Control

Approval, exception handling, override, escalation — the places where a person
is in the path, and where the record of their being there has to be as good as
the record of the machine's reasoning.

## What the pillar is for

In a regulated setting the interesting audit question is rarely "what did the
model output?" It is "who signed off, on what basis, seeing what?" This pillar
exists so that question is answerable from the same record that answers the
machine-side questions — not from a separate ticketing system whose
relationship to the decision is a timestamp and a hope.

The commitment is stated as *audit by construction*: there is no path through
the HITL surface that produces an unrecorded human action. The replay write
precedes the state transition, so an action that was not recorded is an action
that did not take effect.

## How the SDK realizes it

Four primitives cover the four shapes a human intervention takes:

- **ApprovalGate** — a workflow step that suspends until someone approves or
  rejects. What lands in the record is the approver's identity, the time, the
  product they were shown, and their annotations.
- **ExceptionEscalation** — routing to a designated human role when a condition
  fires; typically a debt-threshold breach or an agent escalating explicitly.
- **OverrideBoundary** — a typed point at which a person substitutes a value
  the agent would otherwise have produced. Both the original output and the
  override are retained.
- **ReviewQueue** — asynchronous review of generated content before release,
  integrated with passage-level lineage so a reviewer can see what each claim
  is anchored to.

All four reach humans through one transport protocol whose typed queue is the
sole ingress and egress for actions. MCP endpoints are the primary surface;
webhooks are notify-only, and any action they prompt still returns through the
queue. Approver identity is bound through an identity provider rather than
being a free-text field.

What the SDK does *not* ship is a workflow inbox. HITL events are exposed
through protocols precisely so they can be wired into whatever human-task
system a deployment already runs.

The diagram traces a human action end to end: the three trigger sources, the
four primitives, the single queue they all funnel through, the identity binding
that stamps the actor, and the four heavy edges into the replay record that the
audit-by-construction commitment consists of.

```mermaid
--8<-- "public/diagrams/pillar-hitl.mmd"
```

## Where this lives

- [HITL][hitl] — the primitives, the transport protocol, and the identity
  binding.
- [Runtime surfaces][runtime] — the MCP endpoints and CLI commands through
  which queues are reached.

Related: gates are placed by the [Orchestration Layer][orch]; what a human
action looks like inside the record is covered in
[replay anatomy][replay].

[hitl]: ../../reference/protocols/hitl.md
[runtime]: ../../reference/protocols/runtime-surfaces.md
[orch]: orchestration.md
[replay]: ../replay-anatomy.md
