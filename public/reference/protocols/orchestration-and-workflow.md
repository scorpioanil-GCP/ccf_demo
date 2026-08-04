# Orchestration and workflow Protocols

The SDK ships a minimal in-fabric workflow primitive — enough to compose multi-agent steps with
human gates and to suspend on one — plus a Protocol for delegating to an external orchestrator
when a deployment needs durable execution at Temporal or Step-Functions scale. Workflow
definitions are Control Plane artifacts interpreted by the factory, never code.

::: ccf.orchestration.protocol.OrchestrationProtocol

::: ccf.workflow.factory.WorkflowFactory

::: ccf.workflow.definitions.WorkflowDefinition
