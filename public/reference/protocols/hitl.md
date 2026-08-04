# HITL Protocols

These are the approval, escalation, override and review surfaces a workflow yields to. Their
defining property is audit-by-construction: no path through this surface produces an unrecorded
human action, because the replay write is structural rather than an opt-in hook. Delivery to
actual humans is a transport concern the SDK leaves pluggable — it exposes the events and ships
no inbox.

::: ccf.hitl.transport.HITLTransportProtocol

::: ccf.hitl.webhook.WebhookDeliveryProtocol

::: ccf.hitl.approval_gate

::: ccf.hitl.escalation

::: ccf.hitl.override

::: ccf.hitl.review_queue

::: ccf.hitl.principal
