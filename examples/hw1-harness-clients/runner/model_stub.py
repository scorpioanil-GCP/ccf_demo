"""The leg-2-only determinism seam — a fail-loud Messages-API stand-in.

**Why this file exists at all.** Leg 2 is the one leg with a model in its path.
`claude_agent_sdk` routes everything — its MCP client included — through the
`claude` CLI subprocess, so the only place leg 2 can be determinized is the
model API the CLI talks to. This module is that API, on loopback, answering a
declared conversation and nothing else.

**It is a COPY, for the one leg that needs it (`H-08`, ROADMAP ruling 5).** What
is copied is `examples/external/00-hello-context/replay_server.py`'s *fail-loud
discipline*, not its bytes, and nothing here is imported by anything outside
this example:

  * **Paired declarations, checked before `READY`.** A declared exchange missing
    its `request:` or its `response:` refuses startup naming the exchange, the
    way that server's `require_paired_fixtures` refuses an unpaired fixture. So
    there is no ordinal that serves without a fingerprint comparison.
  * **Fingerprint the request before answering.** Each POST is reduced to a
    small shape and compared to the declared exchange's own reduction; a
    mismatch refuses *by name*, printing both reductions. It never answers the
    nearest thing.
  * **Refuse on exhaustion.** A request past the last declared exchange is an
    error, never a repeat of the last answer.
  * **Refuse-but-record on an unrouted path.** The CLI probes its base URL
    before it talks to it, so an unrouted path is answered `404` and recorded
    rather than crashed on.

**What is deliberately NOT copied, and why this is a copy-with-a-change.**
`examples/external/00-hello-context/replay_server.py::build_app` answers with
`JSONResponse`. The `claude` CLI always sends `"stream": true`, so a JSON body
is not an acceptable answer to it — measured, and stated in those words by the
prior spike. Responses here are therefore **server-sent events**, in the frame
sequence that spike proved drives the CLI. `H-08` asks for the harness to be
copied for the leg that needs it; it is, and the response shape is the one
difference the measurement forced. Recording the departure here is the point:
a ruling that quietly stops meaning what it said is worse than one amended out
loud.

That server's second-vendor branch, its URL-model helper and its model-label
environment seam are **not** carried. This stand-in answers one vendor's API
for one leg; a member nothing reads is the `C-10` pattern this project
refuses.

**The conversation is a document, not constants.** `model-conversation.yaml`
beside this file declares the model label, the prompt leg 2 sends and the two
exchanges. The tool ARGUMENTS emitted below are not authored there either: they
come from the question address the runner hands this process on `argv`, so one
address drives all three legs and this stand-in cannot answer a question the
other legs were not asked.

No CCF import. This is a stand-in for a vendor's model API, and the fabric is
not involved.

Run by `examples/hw1-harness-clients/runner/drive.py`, which spawns it, waits
for its `READY <port>` line and reaps it in a `finally`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import socket
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import anyio
import uvicorn
import yaml
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

#: The declared conversation this stand-in answers, beside the module that
#: reads it. Its own header states why it is a document rather than constants.
DECLARED_CONVERSATION_DOCUMENT = (
    pathlib.Path(__file__).resolve().parent / "model-conversation.yaml"
)

#: The vendor's route. A wire-protocol fact, not a deployment value: Anthropic
#: fixes it, no operator reconfigures it, and this module stands in for the
#: vendor rather than for the fabric. Same judgment `replay_server.py` records
#: for its own routing table under CLAUDE.md §6.4.
MESSAGES_ROUTE = "/v1/messages"

#: The two halves every declared exchange must carry. An exchange missing
#: either is an orphan and refuses startup — the `find_orphans` posture, over
#: one document instead of two files.
EXCHANGE_HALVES: tuple[str, str] = ("request", "response")

#: The keys a declared request reduction may carry. Enumerated so a typo in the
#: document is a startup error rather than a key that silently never compares.
REDUCTION_KEYS: tuple[str, ...] = (
    "messages",
    "door_tools",
    "other_tools",
    "tool_results",
)


def offline_cli_environment(base_url: str, home: pathlib.Path) -> dict[str, str]:
    """The environment that makes the bundled `claude` CLI drive offline.

    **The extraction this plan exists to make before the spike is deleted.**
    This recipe was worked out and measured green in
    `tests/examples/test_s2_client_transport_spike.py`, which is the only place
    in the tree it existed; that module is retired by a later plan, so the
    recipe lives here now, named, beside the stand-in it points at.

    Every variable suppresses one thing the CLI would otherwise do on a network
    it must not touch, or one piece of state it would otherwise read or write
    in the developer's own home directory.
    """
    return {
        # Where the model lives. Loopback, this process, for the default path.
        "ANTHROPIC_BASE_URL": base_url,
        # Non-empty and never validated offline: the CLI declines to start
        # without a credential, and this stand-in does not authenticate.
        "ANTHROPIC_AUTH_TOKEN": "offline",
        # The CLI's state, out of the developer's home and into a temp dir.
        "HOME": str(home),
        "CLAUDE_CONFIG_DIR": str(home / "config"),
        # No version handshake against the vendor's release endpoint.
        "CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK": "1",
        # No telemetry, no crash reporting, no self-update, and none of the
        # incidental model calls the CLI makes around a session.
        "DISABLE_TELEMETRY": "1",
        "DISABLE_ERROR_REPORTING": "1",
        "DISABLE_AUTOUPDATER": "1",
        "DISABLE_NON_ESSENTIAL_MODEL_CALLS": "1",
    }


def declared_conversation(path: pathlib.Path) -> Mapping[str, Any]:
    """Parse the declared conversation document."""
    return dict(yaml.safe_load(path.read_text(encoding="utf-8")))


def find_orphans(exchanges: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every declared exchange missing one of its two halves, both directions.

    A declared request with no response would be a turn the stand-in
    fingerprints and then cannot answer; a response with no request would be a
    turn it answers without fingerprinting. Both are half-declarations, so both
    are reported.
    """
    orphans: list[str] = []
    for index, exchange in enumerate(exchanges):
        for half in EXCHANGE_HALVES:
            if exchange.get(half) is None:
                orphans.append(f"exchange {index} ({exchange.get('name')!r}): {half}")
    return orphans


def require_paired_exchanges(exchanges: Sequence[Mapping[str, Any]]) -> None:
    """Refuse to start when any declared exchange is half-declared.

    Called before `READY` is announced, so the runner's bounded readline sees
    the child die rather than a stand-in that would skip the comparison for the
    orphaned turn.
    """
    if not exchanges:
        print(
            "the declared conversation has no exchanges; a stand-in with"
            " nothing declared refuses every request rather than serving"
            " silently",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
    orphans = find_orphans(exchanges)
    if orphans:
        print(
            "half-declared exchanges — every exchange needs both a 'request:'"
            " and a 'response:': " + "; ".join(orphans),
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
    for index, exchange in enumerate(exchanges):
        unknown = sorted(set(exchange["request"]) - set(REDUCTION_KEYS))
        if unknown:
            print(
                f"exchange {index} ({exchange.get('name')!r}) declares"
                f" {unknown} under 'request:', which this stand-in never"
                f" compares; the compared keys are {list(REDUCTION_KEYS)}",
                file=sys.stderr,
                flush=True,
            )
            raise SystemExit(1)


def door_tools(names: Sequence[str], tool: str) -> list[str]:
    """The advertised names that are the CCF door's own tool.

    The harness namespaces an MCP tool as `mcp__<server>__<tool>`, so the bare
    name the question document carries is a suffix of what the model is shown.
    Matching on the suffix is what lets this stand-in check the tool surface
    without being told the server label the client chose.
    """
    return [name for name in names if name == tool or name.endswith(f"__{tool}")]


def reduction(body: Mapping[str, Any], tool: str) -> dict[str, int]:
    """Reduce one Messages-API request to its drift-detecting shape.

    Four counts, and each is a claim leg 2 makes. `door_tools` and
    `other_tools` together are *the whole tool surface the model saw was the
    CCF door's own tool* — the assertion `tools=[]`, `skills=[]`,
    `setting_sources=[]` and `strict_mcp_config=True` on the client are there
    to make true, observable only from this side. `messages` and `tool_results`
    are where the conversation is in its declared arc.

    Deliberately coarse, and the residual is stated rather than fixed: two
    requests with the same counts and different message text reduce alike. The
    conversation being pinned to two turns is what makes that adequate here.
    """
    advertised = sorted(
        str(entry.get("name", "")) for entry in (body.get("tools") or [])
    )
    ours = door_tools(advertised, tool)
    history = body.get("messages") or []
    results = sum(
        1
        for message in history
        for block in (
            message.get("content") if isinstance(message.get("content"), list) else []
        )
        if isinstance(block, Mapping) and block.get("type") == "tool_result"
    )
    return {
        "messages": len(history),
        "door_tools": len(ours),
        "other_tools": len(advertised) - len(ours),
        "tool_results": results,
    }


def tool_input(question: Mapping[str, Any]) -> dict[str, Any]:
    """The tool arguments this stand-in emits, from the question on `argv`.

    Not authored in the declared conversation: leg 2's model must ask the door
    the SAME question legs 1 and 3 ask, or the content-address comparison at
    the end of the run compares two different questions and passes for the
    wrong reason. The opaque `request` argument is the canonical three-field
    encode every client of this door performs — sorted keys, compact
    separators — done here with the standard library alone, because the model
    is what fills a tool's arguments in.
    """
    arguments = dict(question["arguments"])
    arguments["request"] = json.dumps(
        {
            "product_id": arguments["product_class"],
            "parameters": arguments["parameters"],
            "temporal_boundary": question["temporal_boundary"],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return arguments


def sse(model: str, blocks: Sequence[Mapping[str, Any]], stop_reason: str) -> bytes:
    """One Messages-API streaming answer, as server-sent events.

    **The one place this file is not a copy.** The CLI always sends
    `"stream": true`, so `replay_server.py`'s `JSONResponse` is not an
    acceptable answer to it and a verbatim copy would fail on the first
    request. The frame sequence below is the shape measured to drive the CLI.
    """
    frames: list[tuple[str, dict[str, Any]]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_offline",
                    "type": "message",
                    "role": "assistant",
                    "model": model,
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
            },
        )
    ]
    for index, block in enumerate(blocks):
        if block["type"] == "text":
            frames.append(
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": index,
                        "content_block": {"type": "text", "text": ""},
                    },
                )
            )
            frames.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "text_delta", "text": block["text"]},
                    },
                )
            )
        else:
            frames.append(
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": index,
                        "content_block": {
                            "type": "tool_use",
                            "id": block["id"],
                            "name": block["name"],
                            "input": {},
                        },
                    },
                )
            )
            frames.append(
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": json.dumps(block["input"]),
                        },
                    },
                )
            )
        frames.append(
            ("content_block_stop", {"type": "content_block_stop", "index": index})
        )
    frames.append(
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": 1},
            },
        )
    )
    frames.append(("message_stop", {"type": "message_stop"}))
    return "".join(
        f"event: {event}\ndata: {json.dumps(data)}\n\n" for event, data in frames
    ).encode("utf-8")


def answer_blocks(
    declared: Mapping[str, Any], advertised: Sequence[str], question: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The content blocks one declared response emits.

    A `tool_use` block names the door tool **the request actually advertised**,
    not a name restated in the document: a model calls what it was shown. Its
    input comes from the question address on `argv`.
    """
    blocks: list[dict[str, Any]] = []
    for index, block in enumerate(declared["blocks"]):
        if block["type"] == "text":
            blocks.append({"type": "text", "text": block["text"]})
            continue
        blocks.append(
            {
                "type": "tool_use",
                "id": f"toolu_offline_{index}",
                "name": advertised[0],
                "input": tool_input(question),
            }
        )
    return blocks


def build_app(
    exchanges: Sequence[Mapping[str, Any]],
    model: str,
    question: Mapping[str, Any],
    seen: list[dict[str, Any]],
) -> Starlette:
    """Host the declared conversation, refusing anything that is not it."""
    tool = question["tool"]
    cursor = {"served": 0}

    async def messages(request: Request) -> Response:
        ordinal = cursor["served"]
        if ordinal >= len(exchanges):
            # Fail loudly, never repeat: a request past the last declared
            # exchange means the conversation drifted from the declared one.
            return JSONResponse(
                {
                    "error": "declared exchanges exhausted",
                    "served": ordinal,
                    "declared": len(exchanges),
                },
                status_code=500,
            )
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse(
                {"error": "request body is not valid JSON", "ordinal": ordinal},
                status_code=500,
            )

        exchange = exchanges[ordinal]
        actual = reduction(body, tool)
        expected = {key: int(exchange["request"][key]) for key in REDUCTION_KEYS}
        actual_model = str(body.get("model", ""))
        seen.append({"ordinal": ordinal, "model": actual_model, **actual})
        if actual_model != model:
            return JSONResponse(
                {
                    "error": "the request did not carry the pinned model label",
                    "ordinal": ordinal,
                    "exchange": exchange.get("name"),
                    "expected": model,
                    "actual": actual_model,
                },
                status_code=500,
            )
        if expected != actual:
            # Never answer the nearest thing: both reductions ride the refusal
            # so the operator reads what drifted rather than that something did.
            return JSONResponse(
                {
                    "error": "request reduction mismatch",
                    "ordinal": ordinal,
                    "exchange": exchange.get("name"),
                    "expected": expected,
                    "actual": actual,
                },
                status_code=500,
            )

        advertised = door_tools(
            sorted(str(entry.get("name", "")) for entry in (body.get("tools") or [])),
            tool,
        )
        blocks = answer_blocks(exchange["response"], advertised, question)
        cursor["served"] = ordinal + 1
        return StreamingResponse(
            iter([sse(model, blocks, str(exchange["response"]["stop_reason"]))]),
            media_type="text/event-stream",
        )

    async def unrouted(request: Request) -> Response:
        # The CLI probes its base URL before it talks to it. Answered rather
        # than crashed on, and recorded so a reader can see the probe happened.
        seen.append({"unrouted": f"{request.method} {request.url.path}"})
        return JSONResponse({"error": "unrouted"}, status_code=404)

    return Starlette(
        routes=[
            Route(MESSAGES_ROUTE, messages, methods=["POST"]),
            Route(
                "/{rest:path}",
                unrouted,
                methods=["GET", "HEAD", "POST", "PUT", "DELETE"],
            ),
        ]
    )


def parse_args() -> argparse.Namespace:
    """The two inputs this stand-in takes."""
    parser = argparse.ArgumentParser(description="A fail-loud model stand-in.")
    parser.add_argument(
        "--question-json",
        required=True,
        help="The same question address every leg is handed.",
    )
    parser.add_argument(
        "--declarations",
        default=str(DECLARED_CONVERSATION_DOCUMENT),
        help="The declared conversation document to answer.",
    )
    return parser.parse_args()


def main() -> None:
    """Check the declarations, bind loopback port 0, announce `READY <port>`."""
    args = parse_args()
    conversation = declared_conversation(pathlib.Path(args.declarations))
    exchanges = list(conversation.get("exchanges") or [])
    # Before anything else, and before READY.
    require_paired_exchanges(exchanges)

    question = json.loads(args.question_json)
    seen: list[dict[str, Any]] = []
    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(
            build_app(exchanges, str(conversation["model"]), question, seen),
            log_level="error",
        )
    )

    async def host() -> None:
        async def announce() -> None:
            while not server.started:
                await anyio.sleep(0.005)
            print(f"READY {port}", flush=True)

        async def serve() -> None:
            await server.serve(sockets=[bound])

        async with anyio.create_task_group() as group:
            group.start_soon(announce)
            group.start_soon(serve)

    anyio.run(host)


if __name__ == "__main__":
    main()
