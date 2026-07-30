"""Claude Agent SDK feasibility probe — the 07-13 go/no-go (D-IMPL-60 leg 3).

All four cross-AI reviewers rated the Claude leg the phase's largest blocking
risk, so this probe runs FIRST, before any full-leg investment. It answers
exactly one question — expressibility — and makes no conformance or
replay-equivalence claims:

Can a ``ClaudeSDKClient`` session

1. advance CCF workflow nodes via tool invocations (SDK-MCP ``tools/call``
   routed through the SDK's own control protocol into in-process tool
   handlers that call the ``OrchestrationProtocol`` reference adapter),
2. yield control at a hitl-gate through the hook surface (``HookCallback``
   dispatch + ``CanUseTool``) such that the CCF suspend handle is obtainable
   driver-side, and
3. continue the *same* session after an externally-supplied decision (a
   second ``client.query`` on the live session resumes the suspended CCF
   execution through the engine's own ``resume``)?

**No model, no network, no ``claude`` CLI** — the same D-09 discipline as the
harness conformance suite, asserted by the socket guard below. What makes
that possible without mocking the SDK is the SDK's own public seam:
``claude_agent_sdk.Transport`` is exported precisely for custom connections,
and ``ClaudeSDKClient(transport=...)`` runs the *real* client machinery —
control protocol, initialize handshake, hook-callback registration and
dispatch, SDK-MCP JSONRPC routing, message parsing, session continuation —
over a scripted in-process transport that plays only the wire's role. The
model would decide *when* to call the tools; the probe scripts that choice,
because expressibility of the driver seam, not model behavior, is what is
under test.

The probe drives the banking payment-release workflow from the conformance
fixtures through :class:`WorkflowEngineOrchestrationAdapter` — the engine
stays authoritative for state and audit throughout (T-07-33).
"""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from conftest import harness_unavailable

pytestmark = [pytest.mark.harness]

harness_unavailable("claude_agent_sdk", "claude-agent")

from claude_agent_sdk import (  # noqa: E402
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PermissionResultAllow,
    ResultMessage,
    Transport,
    create_sdk_mcp_server,
    tool,
)

from ccf_runtime.orchestration.reference import (  # noqa: E402
    WorkflowEngineOrchestrationAdapter,
)
from ccf_runtime.workflow.engine import (  # noqa: E402
    WorkflowCompleted,
    WorkflowSuspended,
)
from conformance.test_orchestration import World  # noqa: E402

#: The SDK-MCP server name the scripted transport addresses tool calls to.
SERVER_NAME = "ccf-probe"


@pytest.fixture(autouse=True)
def no_model_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the probe if anything opens a socket (D-09 discipline).

    The probe's claim is that the SDK's session machinery expresses the
    driver seam *in-process*. A probe that quietly reached a model or
    spawned the ``claude`` CLI would prove something else and cost money.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the Claude driver probe attempted network egress; it must drive"
            " SDK objects in-process with no model (D-09)"
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class ScriptedTransport(Transport):
    """The wire's role, scripted; every other participant is the real SDK.

    Plays the CLI/model side of the control protocol: answers the client's
    ``initialize`` (recording the hook callback ids the SDK registered),
    and, per user turn, issues the CLI-side control requests a live session
    would — ``can_use_tool``, SDK-MCP ``tools/call``, ``hook_callback`` —
    which the SDK dispatches into the probe's real handlers. The turn ends
    with a ``result`` frame, exactly as the CLI would end one.
    """

    def __init__(self) -> None:
        self._out: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._hook_ids: list[str] = []
        self._turns: list[asyncio.Task[None]] = []
        self._counter = 0

    # -- Transport ------------------------------------------------------------

    async def connect(self) -> None:  # noqa: D102 — Transport contract
        return None

    def is_ready(self) -> bool:  # noqa: D102 — Transport contract
        return True

    async def end_input(self) -> None:  # noqa: D102 — Transport contract
        return None

    async def close(self) -> None:  # noqa: D102 — Transport contract
        for task in self._turns:
            task.cancel()
        await self._out.put(None)

    async def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        while True:
            message = await self._out.get()
            if message is None:
                return
            yield message

    async def write(self, data: str) -> None:
        message = json.loads(data)
        kind = message.get("type")
        if kind == "control_request":
            # SDK -> "CLI" requests (initialize, interrupt, ...): acknowledge.
            request = message.get("request", {})
            if request.get("subtype") == "initialize":
                for matchers in (request.get("hooks") or {}).values():
                    for matcher in matchers:
                        self._hook_ids.extend(matcher.get("hookCallbackIds", []))
            await self._out.put(
                {
                    "type": "control_response",
                    "response": {
                        "subtype": "success",
                        "request_id": message["request_id"],
                        "response": {"commands": []},
                    },
                }
            )
        elif kind == "control_response":
            # The SDK's answer to a "CLI"-side request we issued.
            response = message.get("response", {})
            future = self._pending.pop(response.get("request_id", ""), None)
            if future is not None and not future.done():
                future.set_result(response)
        elif kind == "user":
            content = message["message"]["content"]
            instruction = json.loads(content)
            self._turns.append(
                asyncio.ensure_future(
                    self._turn(instruction, message.get("session_id", "default"))
                )
            )

    # -- the scripted "model" side --------------------------------------------

    async def _request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Issue one CLI-side control request and await the SDK's response."""
        self._counter += 1
        request_id = f"probe-req-{self._counter}"
        future: asyncio.Future[dict[str, Any]] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending[request_id] = future
        await self._out.put(
            {
                "type": "control_request",
                "request_id": request_id,
                "request": request,
            }
        )
        return await future

    async def _turn(self, instruction: dict[str, Any], session_id: str) -> None:
        """One session turn: permission check, tool call, gate hook, result."""
        tool_name = instruction["tool"]
        arguments = instruction["arguments"]
        qualified = f"mcp__{SERVER_NAME}__{tool_name}"

        # Attempted surface (2a): CanUseTool — the SDK's permission hook.
        permission = await self._request(
            {
                "subtype": "can_use_tool",
                "tool_name": qualified,
                "input": arguments,
                "tool_use_id": f"tool-{self._counter}",
            }
        )
        assert permission["response"]["behavior"] == "allow"

        # Attempted surface (1): SDK-MCP tools/call advancing a CCF node.
        called = await self._request(
            {
                "subtype": "mcp_message",
                "server_name": SERVER_NAME,
                "message": {
                    "jsonrpc": "2.0",
                    "id": self._counter,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
            }
        )
        text = called["response"]["mcp_response"]["result"]["content"][0]["text"]

        # Attempted surface (2b): HookCallback dispatch at the gate.
        if text == "suspended":
            for callback_id in self._hook_ids:
                await self._request(
                    {
                        "subtype": "hook_callback",
                        "callback_id": callback_id,
                        "input": {
                            "hook_event_name": "PostToolUse",
                            "tool_name": qualified,
                            "tool_input": arguments,
                        },
                        "tool_use_id": f"tool-{self._counter}",
                    }
                )

        await self._out.put(
            {
                "type": "result",
                "subtype": "success",
                "duration_ms": 0,
                "duration_api_ms": 0,
                "is_error": False,
                "num_turns": 1,
                "session_id": session_id,
                "result": text,
            }
        )


def test_the_claude_sdk_can_express_the_driver_seam(tmp_path: Path) -> None:
    """The go/no-go: all three load-bearing surfaces, one live session."""
    world = World(tmp_path)
    adapter = WorkflowEngineOrchestrationAdapter(engine=world.engine)
    workflow = world.workflow()

    outcomes: dict[str, Any] = {}
    hook_yielded: list[tuple[str, str]] = []
    permissions_checked: list[str] = []

    @tool("advance", "Advance the CCF workflow execution", {"execution_id": str})
    async def advance(args: dict[str, Any]) -> dict[str, Any]:
        outcome = await adapter.start_execution(
            workflow=workflow, execution_id=args["execution_id"]
        )
        outcomes["last"] = outcome
        text = "suspended" if isinstance(outcome, WorkflowSuspended) else "completed"
        return {"content": [{"type": "text", "text": text}]}

    @tool(
        "resume",
        "Resume the CCF workflow execution with a bound decision",
        {"execution_id": str, "decision": str},
    )
    async def resume(args: dict[str, Any]) -> dict[str, Any]:
        outcome = await adapter.resume_execution(
            workflow=workflow,
            execution_id=args["execution_id"],
            decision=args["decision"],
        )
        outcomes["last"] = outcome
        text = "suspended" if isinstance(outcome, WorkflowSuspended) else "completed"
        return {"content": [{"type": "text", "text": text}]}

    async def gate_hook(
        input_data: Any, tool_use_id: Any, context: Any
    ) -> dict[str, Any]:
        """The hook that yields the CCF suspend handle driver-side."""
        outcome = outcomes.get("last")
        if isinstance(outcome, WorkflowSuspended):
            hook_yielded.append((outcome.gate, outcome.event_key))
        return {}

    async def can_use(
        tool_name: str, tool_input: dict[str, Any], context: Any
    ) -> PermissionResultAllow:
        permissions_checked.append(tool_name)
        return PermissionResultAllow()

    options = ClaudeAgentOptions(
        mcp_servers={
            SERVER_NAME: create_sdk_mcp_server(
                name=SERVER_NAME, version="1.0.0", tools=[advance, resume]
            )
        },
        hooks={"PostToolUse": [HookMatcher(hooks=[gate_hook])]},
        can_use_tool=can_use,
    )

    async def drive() -> tuple[str, str]:
        client = ClaudeSDKClient(options=options, transport=ScriptedTransport())
        await client.connect()
        try:
            # (1) advance a CCF node via a tool invocation.
            await client.query(
                json.dumps(
                    {"tool": "advance", "arguments": {"execution_id": "exec-1"}}
                )
            )
            first = ""
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    first = str(message.result)

            # (2) the gate suspended; the hook yielded the suspend handle.
            suspended = outcomes["last"]
            assert isinstance(suspended, WorkflowSuspended)
            # The human action happens OUTSIDE the session, through the real
            # gate — then the same live session continues.
            world.approve(suspended)

            # (3) session continuation after the externally-bound decision.
            await client.query(
                json.dumps(
                    {
                        "tool": "resume",
                        "arguments": {
                            "execution_id": "exec-1",
                            "decision": "released",
                        },
                    }
                )
            )
            second = ""
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    second = str(message.result)
            return first, second
        finally:
            await client.disconnect()

    first, second = asyncio.run(drive())

    # Surface (1): both node advancements travelled as tool invocations.
    assert first == "suspended"
    assert second == "completed"
    assert world.bindings.ran == ["skill:verify-payment"]

    # Surface (2): CanUseTool consulted for each call; the hook yielded the
    # suspend handle, and it is the engine's own.
    assert permissions_checked == [
        f"mcp__{SERVER_NAME}__advance",
        f"mcp__{SERVER_NAME}__resume",
    ]
    (yielded,) = hook_yielded
    assert yielded[0] == "treasury-approval"

    # Surface (3): the resumed session drove the engine to its terminal
    # state — and the engine stayed authoritative throughout.
    outcome = outcomes["last"]
    assert isinstance(outcome, WorkflowCompleted)
    assert outcome.terminal_state == "released"
