"""Advisory A3's discharge: a real SDK-produced ``ResultMessage`` through seam 4.

The A3 advisory (``docs/PHASE_I4_GATE.md`` §5, standing since the I.3 gate):
the Claude *harness adapter's* seam-4 ``execution()`` in the conformance
suite is a hand-built ``ResultMessage`` — SDK-typed, but constructed by test
code rather than by the SDK's own session machinery. A hand-built message
proves the adapter reads the fields the *type* declares; it cannot prove the
adapter's ``HarnessTrace`` construction agrees with what a real session
actually emits — field names on the wire (``modelUsage``), optionality, and
parser behavior are all the SDK's, and only a message the SDK itself parsed
carries them authentically.

This module is the discharge (plan 08-10, D-02 — not deferred again):

* A real ``ClaudeSDKClient`` session runs over a custom in-process
  ``Transport`` (the SDK's own public seam for a scripted wire — the same
  machinery the I.4 orchestration leg proved). The transport plays only the
  wire's role: it answers the ``initialize`` handshake and ends the turn
  with a ``result`` frame, exactly as the CLI ends one. The SDK's **own
  message parser** constructs the ``ResultMessage`` the test captures.
* That SDK-constructed object is driven through
  :meth:`ClaudeAgentAdapter.replay_trace` — the seam-4 path with the
  ``isinstance`` gate — and the resulting
  :class:`~ccf.replay.record.HarnessTrace` is asserted to carry the real
  session's values (session id as the trace reference, ``model_usage`` keys
  as the reported model, the harness's own token counts), not the
  ``NO_HARNESS`` sentinels an unreported field falls back to.
* The regression half: a non-``ResultMessage`` object still raises the
  ``TypeError`` at the gate — discharging A3 must not have widened it.

``examples/03-harness-portability``'s Claude leg routes its replay hook
through this same real-message path, so the example is the second half of
the discharge evidence.

Everything deployment-shaped — the model identifiers, server names, session
id, token counts, result subtype — comes from
``tests/fixtures/banking/harnesses.yaml`` via the conformance suite's own
fixture reader (CLAUDE.md §6.4). This module holds mechanism only.
"""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator
from typing import Any

import pytest

from ccf.replay.record import NO_HARNESS, HarnessTrace

from conformance.test_harness_adapter import _harness_fixture
from conftest import harness_unavailable

pytestmark = [pytest.mark.conformance, pytest.mark.harness]

harness_unavailable("claude_agent_sdk", "claude-agent")

from claude_agent_sdk import (  # noqa: E402 - guarded by the skip above
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    Transport,
)

from ccf_runtime.adapters.claude_agent import (  # noqa: E402
    HARNESS_ID,
    ClaudeAgentAdapter,
)


@pytest.fixture(autouse=True)
def no_model_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the run if anything opens a socket (D-09).

    The discharge is only worth having if the "real session" costs nothing:
    the SDK machinery runs in-process over the scripted wire, and a change
    that quietly reached a model would fail here rather than bill CI.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the A3 discharge attempted network egress; the session must run"
            " in-process over the scripted transport with no model (D-09)"
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


class _ScriptedResultTransport(Transport):
    """The wire's role, scripted; every other participant is the real SDK.

    Answers the client's ``initialize`` control request and, on the user
    turn, emits the ``result`` frame a live session ends with, carrying the
    fixture deployment's reported usage. The frame's field names are the
    wire's own (``modelUsage``), which is precisely what a hand-built
    ``ResultMessage`` never exercised: the SDK's parser owns the mapping
    from wire field to constructor argument.
    """

    def __init__(self) -> None:
        self._values = dict(_harness_fixture()["claude-agent"])
        self._out: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def connect(self) -> None:
        return None

    def is_ready(self) -> bool:
        return True

    async def end_input(self) -> None:
        return None

    async def close(self) -> None:
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
        elif kind == "user":
            values = self._values
            await self._out.put(
                {
                    "type": "result",
                    "subtype": values["result_subtype"],
                    "duration_ms": 0,
                    "duration_api_ms": 0,
                    "is_error": False,
                    "num_turns": 1,
                    "session_id": message.get(
                        "session_id", values["session_id"]
                    ),
                    "usage": {
                        "input_tokens": values["input_tokens"],
                        "output_tokens": values["output_tokens"],
                    },
                    "modelUsage": {
                        values["reported_model"]: {
                            "inputTokens": values["input_tokens"],
                            "outputTokens": values["output_tokens"],
                        }
                    },
                }
            )


def _sdk_produced_result_message() -> ResultMessage:
    """A ``ResultMessage`` the SDK's own session machinery constructed.

    The real client connects, queries, and parses the result frame the
    scripted wire returned. Nothing here calls the ``ResultMessage``
    constructor: the object is the SDK parser's, which is the entire point
    of the discharge.
    """
    values = _harness_fixture()["claude-agent"]

    async def session() -> ResultMessage:
        client = ClaudeSDKClient(
            options=ClaudeAgentOptions(), transport=_ScriptedResultTransport()
        )
        await client.connect()
        try:
            await client.query(
                json.dumps({"turn": "a3-discharge"}),
                session_id=str(values["session_id"]),
            )
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    return message
        finally:
            await client.disconnect()
        raise AssertionError(
            "the scripted session ended without the SDK constructing a"
            " ResultMessage"
        )

    return asyncio.run(session())


def _adapter() -> ClaudeAgentAdapter:
    values = _harness_fixture()["claude-agent"]
    return ClaudeAgentAdapter(
        model=values["model"],
        mcp_server_name=values["mcp_server_name"],
        mcp_server_version=values["mcp_server_version"],
        effects="governed",
    )


def test_a_real_sdk_result_message_carries_real_values_through_seam_4() -> None:
    """The discharge: an SDK-constructed message, through the isinstance gate.

    Every asserted value is the fixture deployment's own reported value,
    read back out of the trace the adapter derived — and each is asserted
    non-sentinel explicitly, because the adapter's fallback for an
    unreported field *is* the sentinel, and a wire frame whose field names
    the parser did not recognize would leave exactly that fallback behind
    while a weaker assertion stayed green.
    """
    values = _harness_fixture()["claude-agent"]
    message = _sdk_produced_result_message()
    # The object under test is genuinely the SDK's, not this module's.
    assert isinstance(message, ResultMessage)
    assert message.session_id == values["session_id"]

    trace = _adapter().replay_trace(execution=message)
    assert isinstance(trace, HarnessTrace)
    assert trace.harness_id == HARNESS_ID
    # The session id the SDK message carried, not a sentinel.
    assert trace.trace_id == values["session_id"] != NO_HARNESS
    # The model the harness reported (model_usage keys), not a sentinel and
    # not the adapter's configured model.
    assert trace.model_version == values["reported_model"] != NO_HARNESS
    assert trace.model_version != values["model"]
    # The harness's own token accounting survived the parse and the seam.
    assert trace.input_tokens == values["input_tokens"] > 0
    assert trace.output_tokens == values["output_tokens"] > 0


def test_a_non_result_message_still_raises_at_the_isinstance_gate() -> None:
    """Regression: discharging A3 did not widen the seam-4 gate."""
    with pytest.raises(TypeError, match="ResultMessage"):
        _adapter().replay_trace(execution={"session_id": "not-a-message"})
