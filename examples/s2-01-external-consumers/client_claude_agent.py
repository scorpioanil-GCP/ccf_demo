"""A Claude Agent SDK consumer of the CCF MCP front door — zero CCF imports.

A real ``ClaudeSDKClient`` session whose entire tool surface is the CCF
experience server, bound as a Streamable-HTTP MCP server on
``ClaudeAgentOptions``. The harness discovers ``get_context`` (and the rest)
from the server's own ``tools/list``, so no tool schema is duplicated here.
Zero CCF imports; the only CCF knowledge is ``CCF_MCP_URL`` and ``CCF_TOKEN``.

**Not ``client_anthropic.py``.** That leg drives the raw ``anthropic`` SDK and
runs its own tool-use loop against an ``mcp`` client. This one hands the loop to
the harness: ``claude-agent-sdk`` owns the turns, owns the MCP connection, and
calls the CCF tools itself. The ``mcp`` import below is generic client plumbing
used for ONE thing — asking the server which tools it advertises, so that
``allowed_tools`` is the server's own answer rather than a list restated here.

**The tool surface is exactly CCF's, by construction.** ``tools=[]`` withdraws
every built-in the harness would otherwise offer, ``skills=[]`` and
``setting_sources=[]`` withdraw anything the ambient machine might contribute,
and ``strict_mcp_config=True`` refuses MCP servers this process did not name.
What remains is the allowlisted CCF tools and nothing else — which is what makes
the server's registration-time ``tool_allowlist`` the whole of the boundary.

**Determinism in CI is transport-level only, and the transport is the CLI.**
``claude-agent-sdk`` ships no MCP client of its own and speaks no HTTP to a
model: its transport is the Claude Code CLI it bundles, and the CLI is what
connects to the MCP server and what reaches the model API. So the redirect that
determinizes this leg is the one the CLI honours — ``ANTHROPIC_BASE_URL``
pointed at a replay server, with the vendor's own credential variable set to a
placeholder — exactly the ``client_anthropic.py`` posture, one process further
out. Live mode is this same file with those variables unset. There is
deliberately not a single CI/live branch, and no credential variable is read
below.

**Written against ``claude-agent-sdk==0.2.128``** (``ClaudeSDKClient``,
``ClaudeAgentOptions``, ``McpHttpServerConfig``-shaped ``mcp_servers`` entries)
and ``mcp==1.28.1``.

Environment: ``CCF_MCP_URL``, ``CCF_TOKEN``, ``CCF_EXAMPLE_MODEL`` (model names
never appear in code), ``CCF_EXAMPLE_QUESTION`` (prompts never appear in code —
CLAUDE.md §6.4), ``CCF_EXAMPLE_SERVER`` (the MCP namespace the harness sees).

Process protocol: one ``[<tool>] <body>`` line per tool result the harness
surfaced, then one ``[result] <text>`` line — the same ``[label] body`` contract
``examples/external/00-hello-context/client_bare.py`` publishes. This leg
asserts nothing; the assertions belong to whoever drives it.
"""

from __future__ import annotations

import asyncio
import os
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# --8<-- [start:mcp-connect]
async def advertised_tools(url: str, token: str) -> tuple[str, ...]:
    """The tool names the server advertises, over one short-lived session."""
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = (await session.list_tools()).tools
    return tuple(tool.name for tool in listed)
# --8<-- [end:mcp-connect]


# --8<-- [start:mcp-discover]
def qualified(server: str, tool: str) -> str:
    """The name the harness sees for a tool on a bound MCP server.

    The Claude Agent SDK namespaces MCP tools as ``mcp__{server}__{tool}`` and
    matches ``allowed_tools`` against that namespaced form, so the two are
    composed here rather than spelled at each call site.
    """
    return f"mcp__{server}__{tool}"


def session_options(
    *, url: str, token: str, server: str, model: str, tools: tuple[str, ...]
) -> ClaudeAgentOptions:
    """The harness-native carrier: the CCF door as the session's whole world.

    ``allowed_tools`` is derived from what the server actually advertised, so a
    tool the deployment's allowlist omitted is never named here — the server's
    registration-time omission stays the only exposure control there is.
    """
    return ClaudeAgentOptions(
        model=model,
        mcp_servers={
            server: {
                "type": "http",
                "url": url,
                "headers": {"Authorization": f"Bearer {token}"},
            }
        },
        allowed_tools=[qualified(server, tool) for tool in tools],
        tools=[],
        skills=[],
        setting_sources=[],
        strict_mcp_config=True,
        max_turns=len(tools) + 1,
    )
# --8<-- [end:mcp-discover]


# --8<-- [start:mcp-resource]
async def consume(options: ClaudeAgentOptions, question: str) -> None:
    """Run one session and republish what crossed the MCP boundary.

    Tool results arrive on the harness's own message stream as
    ``ToolResultBlock``s — the Context Product as the *harness* received it,
    not as this process fetched it. That is the whole point of the leg: the
    fabric reached the model's context through the harness's tool surface.
    """
    client = ClaudeSDKClient(options=options)
    await client.connect()
    try:
        await client.query(question)
        calls: dict[str, str] = {}
        async for message in client.receive_response():
            if isinstance(message, (AssistantMessage, UserMessage)):
                blocks = message.content if isinstance(message.content, list) else []
                for block in blocks:
                    if isinstance(block, ToolUseBlock):
                        calls[block.id] = block.name
                    if isinstance(block, ToolResultBlock):
                        body = block.content
                        if isinstance(body, list):
                            body = "".join(
                                part.get("text", "")
                                for part in body
                                if isinstance(part, dict)
                            )
                        print(f"[{calls.get(block.tool_use_id, 'tool')}] {body}")
            if isinstance(message, ResultMessage):
                if message.is_error:
                    sys.exit(f"the session ended in error: {message.result}")
                print(f"[result] {message.result or ''}")
                return
    finally:
        await client.disconnect()
    sys.exit("the session ended without a result")
# --8<-- [end:mcp-resource]


async def main() -> None:
    url = os.environ["CCF_MCP_URL"]
    token = os.environ["CCF_TOKEN"]
    server = os.environ["CCF_EXAMPLE_SERVER"]
    model = os.environ["CCF_EXAMPLE_MODEL"]
    question = os.environ["CCF_EXAMPLE_QUESTION"]

    tools = await advertised_tools(url, token)
    if not tools:
        sys.exit("the server advertised no tools; there is nothing to bind")
    await consume(
        session_options(
            url=url, token=token, server=server, model=model, tools=tools
        ),
        question,
    )


if __name__ == "__main__":
    asyncio.run(main())
