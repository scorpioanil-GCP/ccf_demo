# Pillar: Experience Layer

The front door. Whatever reaches the fabric — an external agent runtime, an
operator at a terminal, a service, a UI someone on your team is building —
comes through one of three surfaces.

## What the pillar is for

The Experience Layer exists to give a deployment a working front door on day
one without the SDK pretending to own anyone's user experience. That line is
drawn on purpose: three surfaces ship, and everything above them is a reference
integration users build.

## How the SDK realizes it

**MCP egress server.** Context Products as resources, agents as tools, HITL
queues exposed for human action. This is the surface an MCP-capable agent
runtime consumes without knowing anything about the fabric's internals, and it
is the same surface internal consumers use — there is no privileged back door.

**The `ccf` CLI.** A noun-verb command surface for interactive work: invoking
workflows, inspecting HITL queues, running replay queries, configuring the
Control Plane, declaring agents, granting and revoking skills, and inspecting
artifacts. It is a thin client over the HTTP API, with a local development mode
that talks to the Control Plane directly.

**HTTP API skeleton with an OpenAPI specification.** The surface for service
integration and for custom user interfaces. It reaches the Control Plane, the
product delivery layer, the replay engine, and the workflow primitive —
deliberately *not* signal ingestion, which is not a front-door concern.

Out of scope for v0: mobile SDKs, chat adapters, web UIs, and human-task
inboxes. The OpenAPI specification and example clients exist so building them
is a short exercise; shipping them would be the SDK taking a position on
someone else's product.

The diagram separates the three shipped surfaces from what users build on top,
and shows which parts of the fabric each front door actually reaches.

```mermaid
--8<-- "public/diagrams/pillar-experience.mmd"
```

## Where this lives

- [Runtime surfaces][runtime] — the MCP egress server and the CLI.
- [HTTP API][http] — endpoints, schemas, and the OpenAPI specification.

The security posture for exposing these surfaces — key handling, transport,
and deployment notes — is covered in the how-to guide on
[managing keys and secrets][sec].

[runtime]: ../../reference/protocols/runtime-surfaces.md
[http]: ../../reference/http-api.md
[sec]: ../../how-to/security-and-deployment.md
