"""Leg 1 — a Google ADK client of the hw1 `mcp+stdio` door. Zero CCF imports.

**What an adopter is looking at.** The whole of this program's CCF surface is
one MCP tool registration and one tool call. It imports Google ADK, an MCP
client and the standard library, and **nothing from `ccf`**. It does not know
what a Context Product is, where the fabric keeps its graph, or that a fabric
exists at all. It knows two things it was handed on `argv`: how to start a
program, and what to ask it.

**Both arrive as inputs, never as knowledge.** `--server-command` plus repeated
`--server-arg` are an ordinary program invocation — the shape any MCP server is
configured with, which is the point — and `--question-json` carries the tool's
name and the arguments it takes. Every deployment fact (tenant, product class,
registered version, subject, intent, freshness, boundary, request parameters)
lives in that document rather than in this file, because those are the
deployment's values and CLAUDE.md §6.4/§9 keeps a deployment's values out of
code.

**The one thing tool discovery cannot teach you.** Seven of the door's eight
required arguments are self-describing. The eighth, `request`, has the JSON
Schema `{"type": "string"}` — opaque. It carries the caller's own question,
canonically encoded: a three-field mapping of `product_id`, `parameters` and
`temporal_boundary` with sorted keys and compact separators.
:func:`encoded_request` below **is** that encode, in full, in the standard
library. The door parses the string rather than comparing its bytes, so
`json.dumps` is the entire client-side burden and `json.loads` the entire
decode. A reader will trip on this argument and on nothing else.

**No model, and no agent loop.** `McpToolset` is a toolset, not an agent: it
owns its session manager, `get_tools()` spawns the child and lists what the
door offers, and `run_async` calls one of them. No `LlmAgent`, no `Runner` —
this leg reaches a governed Context Product with no inference in the path.

**A refusal is not a failure of this program.** The fabric refusing is the
fabric working, and what a foreign harness sees is a printable refusal
envelope. It is printed as what it is and the process exits non-zero.

**Output contract: stdout only.** ADK emits `UserWarning: [EXPERIMENTAL] …`
lines and the spawned door logs to stderr; nothing here promises a clean
stderr. On stdout: the content address on its own labelled line, then the
Context Product itself.

Driven by `examples/hw1-harness-clients/runner/drive.py`; see that module for
where the two inputs are resolved from.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Mapping
from typing import Any

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

#: How long ADK waits on the spawned door. A bound rather than a preference:
#: an unbounded wait turns a door that never starts into a hung run.
DOOR_TIMEOUT_SECONDS = 30.0


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

    Sorted keys and compact separators are the canonical rendering the fabric
    uses everywhere; matching it is courtesy rather than obligation, because
    the door parses this string. `ensure_ascii=False` keeps a non-ASCII value
    itself rather than an escape of itself.
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


def outcome_text(result: object) -> str:
    """The door's one text block, or a loud failure.

    **ADK 2.5.0 converts a tool error into a mapping carrying `"error"` rather
    than raising** (its `_MCP_GRACEFUL_ERROR_HANDLING` feature). Branching on
    that key is not defensive coding: without it a failed call reaches the
    printer as if it had succeeded.

    The shape assertions below are the mitigation for the other measured
    hazard — `run_async` is annotated `tool_context: ToolContext` and this
    program passes `None`, which works today and which a future ADK could
    tighten. Asserting on what came back makes such a change loud on the next
    run rather than silent. (`google-adk` is pinned in `pyproject.toml`;
    constructing a real `ToolContext` would require an invocation context, a
    session service, a session and an agent, and the private
    `_execute_with_session` is not a teaching example.)
    """
    if not isinstance(result, Mapping):
        raise SystemExit(f"the tool returned {type(result).__name__}, not a mapping")
    if "error" in result:
        raise SystemExit(f"the door answered with an error: {result['error']}")
    blocks = result.get("content") or ()
    text = "".join(
        block.get("text", "") for block in blocks if isinstance(block, Mapping)
    )
    if not text:
        raise SystemExit(f"the tool returned no text content: {result!r}")
    return text


def report(outcome: Mapping[str, Any]) -> int:
    """Print what came back — the address, then the product itself.

    Printing the address alone would be a smaller program that answered a
    different question. What the door served is the product, so the product is
    what a client of it prints.
    """
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
    """Register the door as a tool, call it once, print what it served."""
    args = parse_args()
    question = json.loads(args.question_json)

    toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=args.server_command,
                args=list(args.server_arg),
                # Explicit, and load-bearing. `mcp.client.stdio`'s default
                # environment hands a child six variables and drops the rest,
                # which has already cost this repository one defect.
                env=dict(os.environ),
            ),
            timeout=DOOR_TIMEOUT_SECONDS,
        )
    )
    try:
        # `get_tools()` is what spawns the child and asks it what it offers.
        # The name to look for is in the question document, not in this file.
        tools = await toolset.get_tools()
        wanted = question["tool"]
        selected = next((tool for tool in tools if tool.name == wanted), None)
        if selected is None:
            raise SystemExit(
                f"this door advertises {[tool.name for tool in tools]},"
                f" which does not include {wanted!r}"
            )
        arguments = dict(question["arguments"])
        arguments["request"] = encoded_request(question)
        result = await selected.run_async(args=arguments, tool_context=None)
    finally:
        await toolset.close()

    return report(json.loads(outcome_text(result)))


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
