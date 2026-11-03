# Consume a Context Product from an MCP-capable harness

> **Source and execution:** dated snippets below retain their original source baseline. For current SDK `v1.0.2@5f85b389`, use [setup and configuration](../../examples/CONFIGURATION.md) and the [current developer guide](../../05-reference/README.md).

## The important idea

If your agent framework already speaks MCP, consuming a Context Product does **not** require your client program to import CCF.

The approved harness-neutral example demonstrates the same Context Product through the same MCP door using:

- Google ADK;
- Claude Agent SDK;
- LangGraph;
- a reference non-harness client.

All are expected to reach the same governed product. The product is the constant; the harness is the variable.

## Evidence baseline

`drcastillo/ccf_code@374a36007bb2fda3e968a83c2ead7d84993c0b23`

Primary example:

`examples/hw1-harness-clients/`

The reader-visible client programs are:

- `client_adk.py`
- `client_anthropic.py`
- `client_langgraph.py`

The example's purity tests assert that those programs import their harness, MCP support, and the standard library — **not `ccf`**.

The excerpts below are intentionally small enough to teach the seam. The authoritative, runnable source remains the pinned files above; do not copy these excerpts forward as a second source of truth if the SDK example changes.

## The question document

All three harness clients are given the door location and a question document. Deployment values do not live in the client code.

Conceptually, the question document contains:

```json
{
  "tool": "<door tool name>",
  "temporal_boundary": "2026-08-01T00:00:00+00:00",
  "arguments": {
    "product_class": "hw1.companies-over-revenue",
    "parameters": {
      "revenue_threshold": 1000000
    }
  }
}
```

The exact values come from the example runner/deployment. The client only carries the question.

## The one MCP argument discovery cannot fully teach

Seven of the product door's required arguments are self-describing through MCP tool discovery. The remaining argument, `request`, is declared only as a string, so the client must know the JSON carried inside it.

Both the ADK and LangGraph examples use this exact encoding shape:

```python
import json


def encoded_request(question):
    arguments = question["arguments"]
    return json.dumps(
        {
            "product_id": arguments["product_class"],
            "parameters": arguments["parameters"],
            "temporal_boundary": question["temporal_boundary"],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
```

This is not a CCF Python import. It is ordinary JSON placed on the MCP wire.

---

# Google ADK — direct MCP session in the caller process

The ADK client imports ADK + MCP and nothing from `ccf`:

```python
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
```

The essential call path is:

```python
toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=server_command,
            args=server_args,
            env=dict(os.environ),
        ),
        timeout=30.0,
    )
)

try:
    tools = await toolset.get_tools()
    wanted = question["tool"]
    selected = next(tool for tool in tools if tool.name == wanted)

    arguments = dict(question["arguments"])
    arguments["request"] = encoded_request(question)

    result = await selected.run_async(
        args=arguments,
        tool_context=None,
    )
finally:
    await toolset.close()
```

The full example adds fail-loud result-shape checks, refusal handling, and output formatting. The important architectural point is visible above: **discover one MCP tool, call it once, no CCF client import.**

Authoritative source:

`ccf_code/examples/hw1-harness-clients/client_adk.py`

---

# LangGraph — MCP tool inside a graph workflow

The LangGraph leg likewise imports LangGraph, `langchain_core`, MCP, and the standard library — not `ccf`:

```python
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
```

Its graph has two nodes:

1. discover the door's tools;
2. bind the selected MCP tool and invoke it.

The essential binding looks like this:

```python
def bind(descriptor):
    async def call(**supplied):
        async with connect(command, arguments) as session:
            result = await session.call_tool(
                descriptor["name"],
                supplied,
            )
        if result.isError:
            raise RuntimeError(
                f"{descriptor['name']} refused: {result.content}"
            )
        return "".join(
            getattr(block, "text", "")
            for block in result.content
        )

    return StructuredTool.from_function(
        coroutine=call,
        name=descriptor["name"],
        description=descriptor["description"],
        args_schema=dict(descriptor["schema"]),
    )
```

The ask node adds the shared wire request and invokes the tool:

```python
supplied = dict(question["arguments"])
supplied["request"] = encoded_request(question)
answer = await bind(descriptor).ainvoke(supplied)
```

The graph itself is ordinary LangGraph:

```python
builder = StateGraph(AskState)
builder.add_node("discover", discover)
builder.add_node("ask", ask)
builder.add_edge(START, "discover")
builder.add_edge("discover", "ask")
builder.add_edge("ask", END)
graph = builder.compile()
```

Again, the MCP door is the integration surface. The graph knows how to discover and invoke a tool; it does not know how the Context Product was assembled.

Authoritative source:

`ccf_code/examples/hw1-harness-clients/client_langgraph.py`

---

# Claude Agent SDK — the agent runtime owns the MCP session

The Claude Agent SDK example is intentionally different. The Python process does **not** open the MCP session itself. It gives the MCP server configuration to the agent runtime:

```python
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
)
from claude_agent_sdk.types import McpStdioServerConfig
```

The essential session configuration is:

```python
options = ClaudeAgentOptions(
    model=model,
    mcp_servers={
        "ccf": McpStdioServerConfig(
            type="stdio",
            command=server_command,
            args=server_args,
            env=dict(os.environ),
        )
    },
    allowed_tools=[f"mcp__ccf__{question['tool']}"],
    tools=[],
    skills=[],
    setting_sources=[],
    strict_mcp_config=True,
    max_turns=2,
)
```

Then the harness runs the session:

```python
client = ClaudeSDKClient(options=options)
await client.connect()
try:
    await client.query(prompt)
    async for message in client.receive_response():
        # Recover the ToolResultBlock carrying the MCP tool result.
        ...
finally:
    await client.disconnect()
```

The full example deliberately requires its prompt/model/base URL through declared runtime inputs and includes the code that unwraps the MCP result envelope and prints the served product or refusal.

The important difference is ownership of the MCP session:

- ADK: your process owns it;
- LangGraph: your process owns it;
- Claude Agent SDK: the configured agent runtime owns it.

The CCF contract does not change.

Authoritative source:

`ccf_code/examples/hw1-harness-clients/client_anthropic.py`

---

## What you install as a consumer

Outside the SDK repository, the consumer installs the harness and MCP client they already use.

There is no requirement for the harness-side application to install CCF merely to call a Context Product through MCP.

That does not mean CCF disappears from the system. CCF remains on the producer/runtime side behind the MCP door. It means producer implementation does not leak into the consumer program.

## What comes back

The three reader-visible examples ultimately handle the same two governed outcomes.

A served result carries the product:

```python
print(outcome["content_address"])
product = json.loads(outcome["product_json"])
```

A governed refusal remains a governed answer:

```python
if outcome.get("refusal") is not None:
    print(outcome["refusal"])
```

The harness mechanics differ; the product/refusal contract does not.

## What stays identical across harnesses

The adoption lesson is not that ADK, Claude Agent SDK, and LangGraph use the same API. They do not.

The lesson is that they can consume the same governed Context Product without changing:

- the product class;
- the MCP door;
- the product's contract;
- the governed payload/refusal semantics;
- the content identity of the answer.

The approved example verifies all three harnesses against the same reference answer and content address.

## Where this belongs in the portal

This page should sit **after** the basic `ProductClient` / `Result` mental model.

A reader should understand what a governed Context Product outcome means before learning the harness-specific mechanics that carry it.

## What this page does not teach

- how to implement the MCP door;
- how to deploy the runner;
- how to seed the example estate;
- how the Context Product is assembled;
- how to author a new transport adapter.

Those are producer/platform or advanced adapter-author topics, not normal consumer prerequisites.

## Consumer takeaway

**If the harness already speaks MCP, CCF can remain behind the protocol boundary.**

And the source now demonstrates that directly: three materially different harness clients, one product, one door, zero `ccf` imports in the reader-visible client programs.
