"""Leg 2 — an Anthropic Agent SDK client of the hw1 `mcp+stdio` door.

Zero CCF imports.

**Read this leg for the asymmetry, and it is the lesson rather than the
embarrassment (`H-07`).** Legs 1 and 3 put the MCP client *in this process*:
they open the session, list the door's tools and call one. This leg cannot,
and the reason is structural rather than stylistic — `claude_agent_sdk` routes
everything it does, its MCP client included, through the `claude` CLI
subprocess it bundles. So this program never holds an MCP session. It hands the
door over as **configuration** — `ClaudeAgentOptions(mcp_servers={...:
McpStdioServerConfig(command=..., args=[...])})` — and the agent binary spawns
the door, speaks to it, and carries the answer back onto this process's message
stream.

*Who holds the MCP session differs by harness.* What does not differ is CCF:
one tool registration, one call, in all three legs, against the same door,
producing the same content address. An adopter choosing a harness is better off
knowing that before they choose than after.

**Both inputs arrive as inputs, never as knowledge.** `--server-command` plus
repeated `--server-arg` are an ordinary program invocation — the shape any MCP
server is configured with — and `--question-json` carries the tool's name and
its arguments. Every deployment fact lives in that document rather than in this
file (CLAUDE.md §6.4/§9). One difference from the siblings: this leg does not
build the tool's arguments at all, because the *model* fills a tool call in.

**The whole tool surface is the door's own tool.** `tools=[]` withdraws every
built-in the harness would offer, `skills=[]` and `setting_sources=[]` withdraw
anything the ambient machine might contribute, `strict_mcp_config=True` refuses
MCP servers this process did not name, and `allowed_tools` names exactly the
one namespaced CCF tool — composed from the server label and the tool name the
question document carries, neither half spelled twice.

**No prompt in this file, and no fallback that would put one here (CLAUDE.md
§6.4).** `ClaudeSDKClient.query(...)` needs instruction text, and the three
argv flags carry the door and the question, not the instruction. It is read
from the environment, **required**, never with a fallback: a defaulted
environment read is a prompt in code wearing an environment variable as a hat,
and the default is the branch that runs the day the variable goes missing. The
runner supplies the value from a declared document beside it.

**No live model by accident.** `ANTHROPIC_BASE_URL` decides where the CLI's
model lives, and this program refuses to start when it is unset rather than
letting the CLI fall back to a vendor endpoint. Under the runner's `--live` the
variable is not injected, so **an operator running `--live` must set it
themselves** — that refusal is the feature, not a defect.

**Output contract: stdout only.** The content address on its own labelled line,
then the Context Product itself — the two lines legs 1 and 3 print, so a runner
parses one shape rather than three.

Driven by `examples/hw1-harness-clients/runner/drive.py`; see that module for
where the inputs are resolved from.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Mapping
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    ToolResultBlock,
    UserMessage,
)
from claude_agent_sdk.types import McpStdioServerConfig

#: The namespace this process gives the door when it configures it. This
#: program's own naming of a server it is about to declare — not a deployment
#: value and not something a caller chooses, which is why it is here and not on
#: `argv`. It is half of the namespaced tool name the model sees.
SERVER_LABEL = "ccf"

#: Where the instruction comes from. Required, and read with no default: see
#: the module docstring.
PROMPT_VARIABLE = "CCF_HARNESS_PROMPT"

#: The model label this leg pins on every request. Model names never appear in
#: code; the runner reads this one from the same declared document the model
#: stand-in reads, so both sides of the pin come from one declaration.
MODEL_VARIABLE = "CCF_HARNESS_MODEL"

#: The variable that decides where the CLI's model lives. Checked rather than
#: passed: this program does not speak to the model API — the agent binary
#: does, inheriting this process's environment — so the only honest thing this
#: program can do about it is refuse to start when it is unset.
BASE_URL_VARIABLE = "ANTHROPIC_BASE_URL"

#: The key MCP's own tool-result envelope carries the door's answer under.
#: A wire fact of the protocol, not a deployment value.
MCP_RESULT_KEY = "result"

#: One turn to call the door, one to report. A bound rather than a preference:
#: an agent binary left to loop would turn a drifted conversation into a hang.
MAXIMUM_TURNS = 2


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


def required(name: str, why: str) -> str:
    """Read one required environment variable, or refuse naming it.

    Subscripted rather than defaulted, deliberately. A defaulted read puts the
    value back in this file for the case that actually runs, and for the prompt
    variable that is precisely the No-Hardcoding violation this leg exists to
    not commit.
    """
    if name not in os.environ or not os.environ[name]:
        raise SystemExit(f"{name} is not set; {why}")
    return os.environ[name]


def qualified(server: str, tool: str) -> str:
    """The name the harness shows the model for a tool on a bound MCP server.

    Composed once, from the label this process chose and the tool name the
    question document carries, so neither half is spelled at a call site.
    """
    return f"mcp__{server}__{tool}"


def session_options(
    *, command: str, arguments: list[str], tool: str, model: str
) -> ClaudeAgentOptions:
    """The door as the session's whole world.

    `mcp_servers` is where the asymmetry lives: the door is described here and
    spawned by the agent binary, so this process passes a command and never
    holds a session. Its `env` is explicit for the same reason it is in the
    siblings — a child handed a trimmed environment has already cost this
    repository one defect.
    """
    return ClaudeAgentOptions(
        model=model,
        mcp_servers={
            SERVER_LABEL: McpStdioServerConfig(
                type="stdio",
                command=command,
                args=arguments,
                env=dict(os.environ),
            )
        },
        allowed_tools=[qualified(SERVER_LABEL, tool)],
        tools=[],
        skills=[],
        setting_sources=[],
        strict_mcp_config=True,
        max_turns=MAXIMUM_TURNS,
    )


def result_text(block: ToolResultBlock) -> str:
    """The text of one tool result, whichever shape the harness surfaced it in."""
    body = block.content
    if isinstance(body, list):
        return "".join(
            part.get("text", "") for part in body if isinstance(part, dict)
        )
    return str(body or "")


def unwrapped(text: str) -> Mapping[str, Any]:
    """The door's answer, out of the MCP envelope the harness surfaced it in.

    A tool result reaches this process twice-wrapped: MCP's own envelope
    around the door's JSON answer. The siblings never see the outer layer
    because they call the tool themselves; this leg does, because the agent
    binary called it. Unwrapped by name rather than by shape-guessing, and a
    missing key refuses loudly — a harness that changed the envelope must not
    look like a door that answered oddly.
    """
    envelope = json.loads(text)
    if not isinstance(envelope, Mapping) or MCP_RESULT_KEY not in envelope:
        raise SystemExit(
            f"the tool result is not an MCP {MCP_RESULT_KEY!r} envelope:"
            f" {text[:200]}"
        )
    return json.loads(envelope[MCP_RESULT_KEY])


def report(outcome: Mapping[str, Any]) -> int:
    """Print what came back — the address, then the product itself.

    Printing the address alone would be a smaller program answering a different
    question, and this leg is where that is easiest to miss: the product crosses
    an agent binary and a model before it reaches this printer, which is exactly
    where a summarised answer would slip through an address-only check.
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


async def ask(options: ClaudeAgentOptions, prompt: str) -> Mapping[str, Any]:
    """Run one session and recover what crossed the MCP boundary.

    The door's answer arrives as a `ToolResultBlock` on the harness's own
    message stream — the Context Product as the *harness* received it, not as
    this process fetched it. It is wrapped once by MCP's own text envelope, so
    it is unwrapped once and parsed.
    """
    client = ClaudeSDKClient(options=options)
    await client.connect()
    try:
        await client.query(prompt)
        served: dict[str, Any] | None = None
        async for message in client.receive_response():
            if isinstance(message, (AssistantMessage, UserMessage)):
                blocks = message.content if isinstance(message.content, list) else []
                for block in blocks:
                    if isinstance(block, ToolResultBlock) and served is None:
                        served = unwrapped(result_text(block))
            if isinstance(message, ResultMessage):
                if message.is_error:
                    raise SystemExit(f"the session ended in error: {message.result}")
                break
    finally:
        await client.disconnect()
    if served is None:
        raise SystemExit(
            "the session ended without a tool result; the agent never reached"
            " the door"
        )
    return served


async def main() -> int:
    """Configure the door as an MCP server, run one session, print the product."""
    args = parse_args()
    question = json.loads(args.question_json)
    required(
        BASE_URL_VARIABLE,
        "it decides where this leg's model lives, and a client that defaulted"
        " to the vendor's endpoint would reach a live model whenever a variable"
        " went missing. The runner injects it on the default path; under"
        " `--live` the runner deliberately does not, and the operator supplies"
        " it — a real endpoint, or a proxy",
    )
    prompt = required(
        PROMPT_VARIABLE,
        "it carries this leg's instruction, which is a declared document the"
        " runner reads and never a literal in this file (CLAUDE.md §6.4)",
    )
    model = required(
        MODEL_VARIABLE, "it pins the model label this leg sends on every request"
    )

    return report(
        await ask(
            session_options(
                command=args.server_command,
                arguments=list(args.server_arg),
                tool=question["tool"],
                model=model,
            ),
            prompt,
        )
    )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
