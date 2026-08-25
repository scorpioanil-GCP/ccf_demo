"""Leg 1 — a bare MCP client, no LLM, no CCF imports (D-05, D-06).

The whole integration surface is two environment variables: ``CCF_MCP_URL``
and ``CCF_TOKEN``. Everything else — tool names, argument schemas, resource
URIs — is discovered from the server itself, which is the point: an external
consumer needs nothing from the fabric's codebase to consume it.

Sequence: list tools; call every advertised tool, filling declared arguments
from ``CCF_EXAMPLE_TENANT`` / ``CCF_EXAMPLE_ENTITY`` (argv 1 and 2 override);
read the first listed product resource (``CCF_EXAMPLE_RESOURCE_URI``
overrides). The lineage and replay-record tools are among those called, so
this leg carries the D-15 client-side retrieval demonstration. Any refusal
or missing content exits non-zero.
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# --8<-- [start:mcp-connect]
@asynccontextmanager
async def connect(url: str, token: str):
    """Short-lived session per call — the server is stateless."""
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
# --8<-- [end:mcp-connect]


# --8<-- [start:mcp-discover]
async def main() -> None:
    url = os.environ["CCF_MCP_URL"]
    token = os.environ["CCF_TOKEN"]
    values = {
        "tenant": sys.argv[1] if len(sys.argv) > 1 else os.environ["CCF_EXAMPLE_TENANT"],
        "entity": sys.argv[2] if len(sys.argv) > 2 else os.environ["CCF_EXAMPLE_ENTITY"],
    }

    async with connect(url, token) as session:
        tools = (await session.list_tools()).tools
    for tool in tools:
        properties = (tool.inputSchema or {}).get("properties", {})
        if any(name not in values for name in properties):
            continue  # e.g. agent-invocation tools this leg has no values for
        arguments = {name: values[name] for name in properties}
        async with connect(url, token) as session:
            result = await session.call_tool(tool.name, arguments)
        assert not result.isError, f"{tool.name} refused: {result.content}"
        text = "".join(getattr(block, "text", "") for block in result.content)
        assert text, f"{tool.name} returned no content"
        print(f"[{tool.name}] {text}")
    # --8<-- [end:mcp-discover]

    # --8<-- [start:mcp-resource]
    uri = os.environ.get("CCF_EXAMPLE_RESOURCE_URI")
    if not uri:
        async with connect(url, token) as session:
            uri = str((await session.list_resources()).resources[0].uri)
    async with connect(url, token) as session:
        contents = (await session.read_resource(uri)).contents
    body = "".join(getattr(block, "text", "") for block in contents)
    assert body, f"resource {uri} returned no content"
    print(f"[resource {uri}] {body}")
# --8<-- [end:mcp-resource]


if __name__ == "__main__":
    asyncio.run(main())
