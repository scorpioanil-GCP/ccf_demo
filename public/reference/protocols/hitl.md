# HITL Protocols

These are the approval, escalation, override and review surfaces a workflow yields to. Their
defining property is audit-by-construction: no path through this surface produces an unrecorded
human action, because the replay write is structural rather than an opt-in hook. Delivery to
actual humans is a transport concern the SDK leaves pluggable — it exposes the events and ships
no inbox.

A transport a `WorkflowEngine` is composed over must also offer
`bind_approver_eligibility(control_plane)` (dated 2026-10-12). The method is not a member of
`HITLTransportProtocol`, and a transport used without an engine need not offer it. The engine
binds its own Control Plane through it at construction and refuses, with `WorkflowWiringError`,
a transport that offers none. Offering it is not enough: at `submit`, the transport judges every
`approve` or `reject` on an approval-gate event that names an approval policy against each bound
plane with `ccf.hitl.transport.check_approver_eligibility`, before recording it. The engine
cannot see whether a third-party transport does this, and no conformance test checks it. See
[security and deployment, §4.13](../../how-to/security-and-deployment.md).

::: ccf.hitl.transport.HITLTransportProtocol

::: ccf.hitl.webhook.WebhookDeliveryProtocol

::: ccf.hitl.approval_gate

::: ccf.hitl.escalation

::: ccf.hitl.override

::: ccf.hitl.review_queue

::: ccf.hitl.principal
