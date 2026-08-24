"""Leg 2 — a textbook Anthropic-SDK agent with its own tool-use loop (D-05).

Pure ``anthropic`` SDK: the loop below is the vendor's documented tool-use
pattern, unmodified. CCF appears only as an MCP server the tools happen to
front — the ``mcp`` import here is generic client plumbing, not a CCF
import (D-06). Tool names, descriptions, and input schemas are discovered
from the server's own tools/list, so nothing fabric-side is duplicated.

Determinism in CI is transport-level only (D-09): ``ANTHROPIC_BASE_URL``
points the SDK at ``replay_server.py`` and ``ANTHROPIC_API_KEY=ci-replay``
satisfies the client's key requirement; live mode is this same file with
those variables unset. There is deliberately not a single CI/live branch.

Environment: ``CCF_MCP_URL``, ``CCF_TOKEN``, ``CCF_EXAMPLE_MODEL`` (model
names never appear in code), ``CCF_EXAMPLE_QUESTION`` (prompts never appear
in code — CLAUDE.md §6.4). All four are REQUIRED: a default here would be a
prompt in code that runs on the default path, which is what the deployment
declares in ``artifacts/experience.yaml`` and ``run.py`` passes.
"""

from __future__ import annotations

import asyncio
import os
import sys

import anthropic
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def mcp_call(url: str, token: str, request):
    """Short-lived MCP session per call; the CCF server is stateless."""
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await request(session)


def main() -> None:
    url = os.environ["CCF_MCP_URL"]
    token = os.environ["CCF_TOKEN"]
    model = os.environ["CCF_EXAMPLE_MODEL"]
    question = os.environ["CCF_EXAMPLE_QUESTION"]

    listed = asyncio.run(mcp_call(url, token, lambda s: s.list_tools())).tools
    tools = [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in listed
    ]

    client = anthropic.Anthropic()  # key and base URL from env only (A1)
    messages: list[dict] = [{"role": "user", "content": question}]
    while True:
        response = client.messages.create(
            model=model, max_tokens=1024, messages=messages, tools=tools
        )
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            outcome = asyncio.run(
                mcp_call(
                    url, token, lambda s: s.call_tool(block.name, block.input)
                )
            )
            assert not outcome.isError, f"{block.name} refused: {outcome.content}"
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "".join(
                        getattr(part, "text", "") for part in outcome.content
                    ),
                }
            )
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})

    decision = "".join(
        block.text for block in response.content if block.type == "text"
    )
    if not decision:
        sys.exit("the model returned no final text")
    print(decision)


if __name__ == "__main__":
    main()
