# Runtime surfaces

These are the seams the runtime exposes above the fabric: the Experience Layer surfaces an MCP
server resolves against, the authentication and tenant-authorization seams the HTTP API sits
on, the bindings a workflow engine node resolves through, and the three reference harness
adapters. Everything here is replaceable; the runtime holds the wiring, not the policy.

## Experience Layer

::: ccf_runtime.mcp.experience.ExperienceProductResolverProtocol

::: ccf_runtime.mcp.experience.AgentDirectoryProtocol

::: ccf_runtime.mcp.experience.AgentInvokerProtocol

::: ccf_runtime.mcp.experience.ContextProviderProtocol

::: ccf_runtime.mcp.experience.LineageProviderProtocol

::: ccf_runtime.mcp.experience.ReplayRecordReaderProtocol

## Authentication and authorization

::: ccf_runtime.http_api.auth.HttpAuthProtocol

::: ccf_runtime.authz.protocol.TenantAuthorizerProtocol

## Workflow engine bindings

::: ccf_runtime.workflow.engine.SkillNodeBinding

::: ccf_runtime.workflow.engine.AgentNodeBinding

::: ccf_runtime.workflow.engine.DebtAssessmentBinding

## Reference harness adapters

::: ccf_runtime.adapters.adk.adapter

::: ccf_runtime.adapters.claude_agent.adapter

::: ccf_runtime.adapters.langgraph.adapter
