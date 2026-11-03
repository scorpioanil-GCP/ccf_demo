# Agents, Harnesses, and Orchestration

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

CCF does not absorb the agent loop. It supplies governed context, skills, artifacts, workflow/HITL and harness adapter seams.

## Harness adapters

Reference runtime adapters include:

- Google ADK;
- Claude Agent SDK;
- LangGraph.

## Claude Agent SDK hardening

Current `ClaudeAgentAdapter` has explicit deployment controls for:

- `child_environment`;
- `cwd`;
- `max_turns`.

The module also exposes:

- `AllowlistedEnvironmentTransport`;
- `DEFAULT_CHILD_ENVIRONMENT`;
- `PromptFileRefused`.

The governed adapter path does not inherit the fabric process's full environment or the host's Claude tool/settings configuration by default.

The carrier is deliberately closed around the governed path:

- `tools=[]` disables the CLI's built-in tool set;
- `setting_sources=[]` prevents host/project Claude settings from widening permissions;
- `strict_mcp_config=True` prevents undeclared MCP servers from joining the session;
- `cwd` is deployment-declared or a per-call owner-only directory;
- the vendor's default transport is made fail-closed; use `adapter.transport(carrier)` so the child is spawned from the declared environment allowlist.

The assembled system prompt is carried by an owner-only `0600` file inside an owner-only `0700` directory rather than on the child process argv. `PromptFileRefused` rejects a missing, planted, symlinked, wrongly owned or wrongly permissioned prompt path before a session starts.

Those prompt directories contain the complete assembled prompt at rest. The adapter does not run a background cleaner; after the dependent sessions end, the deployment should call `adapter.remove_prompt_directories()`.

## Harness tool exposure and dispatch authority

Harness exposure is narrower than the complete bound skill set.

`ccf.skills.toolsurface.HARNESS_EXPOSABLE_SKILL_TYPES` contains exactly:

- `tool`;
- `mcp`;
- `local_callable`.

A bound `procedure`, `peering`, or `mcp_product` skill is not rendered as an ordinary harness tool. Procedures remain instruction/context inputs, while peering and MCP-product paths retain their governed admission semantics rather than becoming direct model-callable tools.

The reference ADK, Claude Agent SDK and LangGraph adapters also recheck authority at the callable boundary. A read-only adapter binding (`effects` other than `governed`) or a skill that is no longer bound at call time is refused **before dispatch**. Callback-level permission checks remain defense in depth; they are not the only enforcement point.

## Skill argument boundary

`ccf.skills.wire_arguments` provides the common fail-closed rule for framework/wire argument maps:

- undeclared arguments;
- missing required arguments;
- mistyped arguments.

The canonical fabric-side check is `Agent.invoke_skill(..., arguments=...)`: it validates the presented mapping against the currently bound entry's declared `argument_schema` before dispatch. Harness adapters preserve the model's raw argument types until this check rather than pre-stringifying them.

Adapters may enforce the same rule at their own edge so they can return a harness-native refusal, but dispatch is outside that narrow validation handler. An `ArgumentRefused` raised by the skill implementation itself is therefore not mislabeled as the harness tool's input-validation refusal.

## Workflow

`WorkflowDefinition` now carries `gate_routes` in addition to transitions, gate policies and exception refs.

Gate routing/approval authority is therefore a declared workflow concern rather than only a caller-provided resume decision.

## HITL

For current signed-action and approval-policy surfaces, see [HITL](HITL.md).

## Agent-internal CCF

CP-22 remains the reference that an external agent protocol can stay small while CCF context/debt/lineage remains internal to the agent that consumes the Context Product.

## Context Skills and bank agents

A Context Skill is a versioned catalog entry plus grant authorizing a composing agent to ask a Context Product. The supported YAML path derives `mcp_product`, which correctly exposes no model tool. Use [Context Skills](CONTEXT_SKILLS.md) and [SK-01](../02-context-product-producer/examples/SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md) for declaration, admission, record identity and current limitations. Harness instructions alone grant no CCF authority.
