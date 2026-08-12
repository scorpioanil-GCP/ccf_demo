"""A LangGraph consumer of the CCF MCP front door — zero CCF imports.

A LangGraph node drives an ``mcp.ClientSession`` over ``streamablehttp_client``
directly and binds every tool the server advertises as a ``langchain_core``
``StructuredTool`` by hand. Nothing here knows what a Context Product is: the
tool names, their prose, and their argument schemas are all discovered from the
server's own ``tools/list``, so no fabric-side schema is duplicated. Zero CCF
imports; the only CCF knowledge is ``CCF_MCP_URL`` and ``CCF_TOKEN``.

**No adapter, and deliberately so.** ``ccf_runtime.adapters.langgraph`` is the
inverse of this file: it imports ``ccf`` because it binds the four
harness-adapter seams from the fabric side. This leg is what an external team
writes when all it has is a URL and a bearer token, which is the claim the
example exists to demonstrate.

**Written against ``langgraph==1.2.9`` and ``langchain-core==1.5.1``**, using
``langgraph.graph.StateGraph`` with a ``TypedDict`` state schema and
``langchain_core.tools.StructuredTool.from_function``. Those are named because
there is no other LangGraph client leg in the tree to fall back on, and because
``StructuredTool.from_function(args_schema=<JSON Schema dict>)`` — accepting a
raw JSON-Schema mapping rather than a Pydantic model — is the API this file
leans on hardest. No third-party LangChain-to-MCP bridge package is used:
binding the discovered tools by hand costs about fifteen lines, adds no
dependency, and widens no supply-chain surface.

Determinism is transport-level only: this leg reaches no model, so pointing it
at a server is the whole of its configuration. There is deliberately not a
single CI/live branch.

Environment: ``CCF_MCP_URL``, ``CCF_TOKEN``. Argument values for the advertised
tools arrive as ``name=value`` command-line arguments; a tool whose declared
arguments are not all supplied is skipped rather than guessed at.

Process protocol: one ``[<tool>] <body>`` line per successful read on stdout —
the same contract ``examples/external/00-hello-context/client_bare.py``
publishes — and a non-zero exit with a message on stderr otherwise. This leg
asserts nothing; the assertions belong to whoever drives it.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Any, TypedDict

from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

#: The adapter-free node names of this leg's own two-node topology. LangGraph
#: has no loop of its own to hook, so the caller builds the graph; these are
#: the whole of it.
_DISCOVER_NODE = "discover"
_READ_NODE = "read"


class ConsumerState(TypedDict, total=False):
    """The typed state channels this leg's graph carries.

    Every channel is optional (``total=False``): the graph is entered with
    ``values`` alone and each node publishes its own channel.

    Attributes:
        values: Argument values the caller supplied, by argument name.
        advertised: One entry per tool the server advertises — its name, its
            prose, and its declared argument schema, exactly as ``tools/list``
            returned them.
        reads: ``(tool name, body)`` for every tool this leg actually called.
    """

    values: dict[str, str]
    advertised: tuple[dict[str, Any], ...]
    reads: tuple[tuple[str, str], ...]


# --8<-- [start:mcp-connect]
@asynccontextmanager
async def connect(url: str, token: str) -> AsyncIterator[ClientSession]:
    """Short-lived session per call — the server is stateless."""
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
# --8<-- [end:mcp-connect]


def build_graph(url: str, token: str) -> Any:
    """Compile this leg's own graph, with both nodes closing over the endpoint.

    LangGraph exposes no agent loop to hook, so the topology is the caller's:
    ``discover`` asks the server what it offers and ``read`` binds each offer
    as a LangChain tool and calls it. Both nodes drive a real MCP session; the
    endpoint and the credential reach them through this closure rather than
    through the state, so neither is ever a value the graph carries.
    """

    # --8<-- [start:mcp-discover]
    async def discover(state: ConsumerState) -> ConsumerState:
        """Ask the server what it offers. No schema is duplicated here."""
        async with connect(url, token) as session:
            listed = (await session.list_tools()).tools
        return {
            "advertised": tuple(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "schema": tool.inputSchema or {},
                }
                for tool in listed
            )
        }

    def bind(descriptor: Mapping[str, Any]) -> StructuredTool:
        """One LangChain tool per advertised MCP tool, bound by hand.

        The declared JSON Schema goes straight onto ``args_schema``, so the
        tool's argument surface is the server's own declaration rather than a
        restatement of it. Every invocation opens its own session, which is
        what makes a revoked token take effect on the next call rather than
        the next process.
        """

        async def call(**arguments: str) -> str:
            async with connect(url, token) as session:
                result = await session.call_tool(descriptor["name"], arguments)
            if result.isError:
                raise RuntimeError(f"{descriptor['name']} refused: {result.content}")
            return "".join(getattr(block, "text", "") for block in result.content)

        return StructuredTool.from_function(
            coroutine=call,
            name=descriptor["name"],
            description=descriptor["description"],
            args_schema=dict(descriptor["schema"]),
        )
    # --8<-- [end:mcp-discover]

    # --8<-- [start:mcp-resource]
    async def read(state: ConsumerState) -> ConsumerState:
        """Call every advertised tool whose declared arguments are supplied.

        A tool naming an argument the caller did not supply is skipped, never
        guessed at — that is how an agent-invocation tool this leg has no
        values for stays uncalled without the leg knowing what it is.
        """
        values = state["values"]
        reads: list[tuple[str, str]] = []
        for descriptor in state["advertised"]:
            properties = dict(descriptor["schema"]).get("properties", {})
            if any(name not in values for name in properties):
                continue
            tool = bind(descriptor)
            body = await tool.ainvoke({name: values[name] for name in properties})
            if not body:
                raise RuntimeError(f"{descriptor['name']} returned no content")
            reads.append((descriptor["name"], body))
        return {"reads": tuple(reads)}
    # --8<-- [end:mcp-resource]

    builder: Any = StateGraph(ConsumerState)
    builder.add_node(_DISCOVER_NODE, discover)
    builder.add_node(_READ_NODE, read)
    builder.add_edge(START, _DISCOVER_NODE)
    builder.add_edge(_DISCOVER_NODE, _READ_NODE)
    builder.add_edge(_READ_NODE, END)
    return builder.compile()


def supplied_values(arguments: Sequence[str]) -> dict[str, str]:
    """Parse ``name=value`` command-line arguments into an argument mapping."""
    values: dict[str, str] = {}
    for argument in arguments:
        name, separator, value = argument.partition("=")
        if not separator or not name:
            sys.exit(f"expected name=value arguments, got {argument!r}")
        values[name] = value
    return values


async def main() -> None:
    url = os.environ["CCF_MCP_URL"]
    token = os.environ["CCF_TOKEN"]
    values = supplied_values(sys.argv[1:])

    final = await build_graph(url, token).ainvoke({"values": values})

    reads = final.get("reads") or ()
    if not reads:
        sys.exit("the graph called no tool; supply the declared argument values")
    for name, body in reads:
        print(f"[{name}] {body}")


if __name__ == "__main__":
    asyncio.run(main())
