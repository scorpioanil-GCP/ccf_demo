"""Leg 3 — a LangGraph client of the hw1 `mcp+stdio` door. Zero CCF imports.

This is `examples/hw1-harness-clients/client_adk.py` written a second way. Same
three inputs on `argv`, same encoded `request`, same stdout, same refusal
handling — a different harness holding the session. Read them side by side;
the diff is the harness and nothing else.

**What a model-free graph is, said plainly.** LangGraph exposes no agent loop
to hook, so the topology is the caller's. A compiled `StateGraph` whose node
binds the discovered MCP tool as a `langchain_core` `StructuredTool` and
invokes it *is* what "a LangGraph client registers the door as a tool, calls it
and prints the product" asks for — and it is the only reading available here,
because no langchain model provider is installed in this tree. Nothing was
skipped and nothing is stubbed.

**No third-party LangChain-to-MCP bridge package is used, and none is
installed.** Binding the discovered tool by hand costs about fifteen lines,
adds no dependency, and widens no supply-chain surface. That rationale was
measured rather than assumed, by the Phase 16 spike whose record is
`docs/surface/examples/SECTION-2-TRANSPORT.md`; the client it measured has
been retired out of `examples/` and is reachable only from that record. The
prebuilt tool-executing node primitive that ships with LangGraph is available
and is deliberately unused too: it drags `messages` state semantics that only
make sense with a model in the loop.

**The opaque argument, again.** Seven of the door's eight required arguments
are self-describing; the eighth, `request`, has the JSON Schema
`{"type": "string"}`. It carries the caller's own question, canonically
encoded — `product_id`, `parameters`, `temporal_boundary`, sorted keys, compact
separators. :func:`encoded_request` is that encode in full, and it is
character-identical to leg 1's, so the same `--question-json` produces the same
`request` string from either program. That identity is what makes "one
question, three harnesses, one content address" a claim about the fabric rather
than about three clients that happen to agree.

**No CCF import of any kind.** This program imports LangGraph, `langchain_core`,
an MCP client and the standard library. The tool's name and its arguments come
from `--question-json`; the door's location comes from `--server-command` and
`--server-arg`. Nothing here knows a fabric exists.

**Output contract: stdout only.** The spawned door logs to stderr. On stdout:
the content address on its own labelled line, then the Context Product itself.
Printing the address alone would be a smaller program answering a different
question.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, TypedDict

from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

#: The two node names of this leg's own topology. LangGraph has no loop of its
#: own to hook, so the caller builds the graph; these are the whole of it.
_DISCOVER_NODE = "discover"
_ASK_NODE = "ask"


class AskState(TypedDict, total=False):
    """The typed channels this leg's graph carries.

    Every channel is optional: the graph is entered with ``question`` alone and
    each node publishes its own.

    Attributes:
        question: The document handed on ``--question-json``.
        advertised: One entry per tool the door advertises — its name, its
            prose and its declared argument schema, exactly as ``tools/list``
            returned them. No fabric-side schema is restated here.
        answer: The door's one text block, undecoded.
    """

    question: dict[str, Any]
    advertised: tuple[dict[str, Any], ...]
    answer: str


def parse_args() -> argparse.Namespace:
    """The three inputs this program takes, and it takes no others."""
    parser = argparse.ArgumentParser(description="Ask one MCP door one question.")
    parser.add_argument("--server-command", required=True, help="Program to run.")
    parser.add_argument(
        "--server-arg", action="append", default=[], help="One argument; repeatable."
    )
    parser.add_argument(
        "--question-json", required=True, help="The tool name and its arguments."
    )
    return parser.parse_args()


def encoded_request(question: Mapping[str, Any]) -> str:
    """The opaque `request` argument, built with the standard library alone.

    Byte-identical to leg 1's for the same question document. The door parses
    this string rather than comparing its bytes, so matching the fabric's
    canonical rendering is courtesy rather than obligation — but matching it
    across the legs is what makes their agreement legible.
    """
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


@asynccontextmanager
async def connect(command: str, arguments: list[str]) -> AsyncIterator[ClientSession]:
    """One short-lived stdio session per call; the harness spawns the child.

    ``env=dict(os.environ)`` is explicit and load-bearing:
    ``mcp.client.stdio``'s default environment hands a child six variables and
    drops the rest, which has already cost this repository one defect.
    """
    parameters = StdioServerParameters(
        command=command, args=arguments, env=dict(os.environ)
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def build_graph(command: str, arguments: list[str]) -> Any:
    """Compile this leg's graph, both nodes closing over the door's location.

    ``discover`` asks the door what it offers; ``ask`` binds the one tool the
    question names as a `langchain_core` tool and invokes it. The door's
    location reaches them through this closure rather than through the state,
    so it is never a value the graph carries.
    """

    async def discover(state: AskState) -> AskState:
        """Ask the door what it offers. No schema is duplicated here."""
        async with connect(command, arguments) as session:
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

        The door's own declared JSON Schema goes straight onto ``args_schema``
        — a plain mapping is accepted, so no Pydantic model is written and no
        argument surface is restated. This is the whole of the "bridge" a
        package would have supplied.
        """

        async def call(**supplied: Any) -> str:
            async with connect(command, arguments) as session:
                result = await session.call_tool(descriptor["name"], supplied)
            if result.isError:
                raise RuntimeError(f"{descriptor['name']} refused: {result.content}")
            return "".join(getattr(block, "text", "") for block in result.content)

        return StructuredTool.from_function(
            coroutine=call,
            name=descriptor["name"],
            description=descriptor["description"],
            args_schema=dict(descriptor["schema"]),
        )

    async def ask(state: AskState) -> AskState:
        """Call the one tool the question names, with the arguments it names."""
        question = state["question"]
        wanted = question["tool"]
        descriptor = next(
            (item for item in state["advertised"] if item["name"] == wanted), None
        )
        if descriptor is None:
            names = [item["name"] for item in state["advertised"]]
            raise RuntimeError(
                f"this door advertises {names}, which does not include {wanted!r}"
            )
        supplied = dict(question["arguments"])
        supplied["request"] = encoded_request(question)
        return {"answer": await bind(descriptor).ainvoke(supplied)}

    builder: Any = StateGraph(AskState)
    builder.add_node(_DISCOVER_NODE, discover)
    builder.add_node(_ASK_NODE, ask)
    builder.add_edge(START, _DISCOVER_NODE)
    builder.add_edge(_DISCOVER_NODE, _ASK_NODE)
    builder.add_edge(_ASK_NODE, END)
    return builder.compile()


def report(outcome: Mapping[str, Any]) -> int:
    """Print what came back — the address, then the product itself."""
    refusal = outcome.get("refusal")
    if refusal is not None:
        print("refused")
        print(json.dumps(refusal, indent=2, sort_keys=True))
        return 1
    print(f"content address    {outcome['content_address']}")
    print("context product")
    print(json.dumps(json.loads(outcome["product_json"]), indent=2, sort_keys=True))
    return 0


async def main() -> int:
    """Run the graph once and print what the door served."""
    args = parse_args()
    question = json.loads(args.question_json)
    graph = build_graph(args.server_command, list(args.server_arg))
    final = await graph.ainvoke({"question": question})
    answer = final.get("answer")
    if not answer:
        raise SystemExit("the graph reached no answer")
    return report(json.loads(answer))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
