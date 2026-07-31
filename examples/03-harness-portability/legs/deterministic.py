"""The three deterministic harness legs — real loop machinery, no model (D-02).

One agent definition, three harnesses (CLAUDE.md §7.3 — *portability is
demonstrated, not asserted*). Each leg binds the SAME
:class:`~ccf.agents.agent.Agent` object through that harness's own
`HarnessAdapterProtocol` adapter and drives the four seams, with the seam-4
execution produced by **real harness loop machinery over a scripted/no-model
transport**:

* **Claude Agent SDK** — a real ``ClaudeSDKClient`` session runs over a
  custom in-process ``Transport`` (the SDK's own public seam for exactly
  this): initialize handshake, message parsing, and the result frame are all
  the real SDK's, so the ``ResultMessage`` handed to the adapter's seam-4
  path is genuinely SDK-constructed — this leg is advisory A3's example-side
  discharge evidence.
* **Google ADK** — a real ``Runner`` drives the adapter's own execution
  vehicle over an ``InMemorySessionService``; the reported model and token
  counts travel through ADK's own session-state machinery.
* **LangGraph** — the adapter's real compiled graph is invoked with the
  reported values merged into the run configuration's metadata under
  LangChain's own tracing keys.

A missing harness import is a *failure*, not a skip — this module imports
all three SDKs unconditionally, mirroring ``CCF_REQUIRE_HARNESSES=1``: a
portability proof over a subset of the adapters is not the proof.

This module is mechanism only. Every domain and deployment value — model
identifiers, server names, session/thread identifiers, reported trace
fields — arrives via the ``values`` mapping loaded from
``artifacts/harnesses.yaml`` (No-Hardcoding Rule, CLAUDE.md §6.4).
"""

from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any, NamedTuple

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, Transport
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as adk_types

from ccf.agents.agent import Agent, EmittedEffect
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.contract import ContextProductContract
from ccf.replay.record import DecisionReplayRecord, HarnessTrace, NO_HARNESS
from ccf_runtime.adapters.adk import (
    MODEL_STATE_KEY,
    USAGE_STATE_KEY,
    AdkAdapter,
)
from ccf_runtime.adapters.claude_agent import ClaudeAgentAdapter
from ccf_runtime.adapters.langgraph import (
    MODEL_METADATA_KEY,
    USAGE_METADATA_KEY,
    LangGraphAdapter,
)

__all__ = [
    "GOVERNED_DIMENSIONS",
    "LegRun",
    "build_legs",
    "dimension_count",
    "drive_leg",
    "governed_fields",
    "install_no_model_guard",
]

#: Top-level record fields D-18 governs — every dimension except the one that
#: carries the harness block. Compared for exact byte equality across the
#: three harnesses.
GOVERNED_DIMENSIONS = (
    "context_fabric_snapshot",
    "policy_bindings",
    "perspective_conditioning",
    "content_generation_path",
)

#: Dimension 3's own governed fields; ``harness_trace`` is excluded and
#: asserted to differ per harness instead (D-18).
GOVERNED_MODEL_VERSION_FIELDS = ("assembly_mode", "model_version")


def install_no_model_guard() -> None:
    """Fail the run if anything opens a socket (D-02, T-08-25).

    Deterministic mode provably makes no network call: the guard is
    process-global, installed before any leg runs, and the driver asserts it
    actually fires before trusting it.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "the deterministic portability drive attempted network egress; it"
            " must run real harness machinery in-process with no model (D-02)"
        )

    socket.socket.connect = refuse  # type: ignore[method-assign, assignment]
    socket.create_connection = refuse  # type: ignore[assignment]


# --- generic carrier recovery (same probe idea as the conformance suite) ------


def _carrier_values(carrier: object, *, _depth: int = 0) -> Any:
    """Every value reachable inside a harness-native carrier, generically."""
    if _depth > 4:
        return
    yield carrier
    children: list[object] = []
    if isinstance(carrier, Mapping):
        children = [*carrier.keys(), *carrier.values()]
    elif isinstance(carrier, (list, tuple, set, frozenset)):
        children = list(carrier)
    elif hasattr(carrier, "__dataclass_fields__") and not isinstance(carrier, type):
        children = [
            getattr(carrier, name, None) for name in carrier.__dataclass_fields__
        ]
    elif hasattr(carrier, "__dict__") and not isinstance(carrier, type):
        children = list(vars(carrier).values())
    for child in children:
        yield from _carrier_values(child, _depth=_depth + 1)


def recovered_products(carrier: object) -> tuple[bytes, ...]:
    """Every Context Product document reachable on a harness's context surface.

    Recovered the way a *harness* would meet it — as JSON documents inside
    the strings the adapter placed there — so an adapter that interpolated,
    truncated, or re-serialized what it delivered turns the byte comparison
    red instead of passing a comparison against the product the driver
    already holds.
    """
    decoder = json.JSONDecoder()
    found: list[bytes] = []
    for value in _carrier_values(carrier):
        if not isinstance(value, str):
            continue
        for index, character in enumerate(value):
            if character != "{":
                continue
            try:
                document, end = decoder.raw_decode(value, index)
            except ValueError:
                continue
            if isinstance(document, dict) and "schema_name" in document:
                found.append(value[index:end].encode("utf-8"))
    return tuple(dict.fromkeys(found))


# --- the Claude leg's scripted wire -------------------------------------------


class _ScriptedResultTransport(Transport):
    """The wire's role, scripted; every other participant is the real SDK.

    Answers the client's ``initialize`` control request and, on the user
    turn, emits the ``result`` frame a live session would end with — carrying
    the usage and per-model accounting this deployment's harness reports
    (``artifacts/harnesses.yaml``). The SDK's own message parser constructs
    the ``ResultMessage`` from that frame, which is what makes the seam-4
    input genuinely SDK-produced rather than hand-built (advisory A3).
    """

    def __init__(self, *, values: Mapping[str, Any]) -> None:
        self._values = dict(values)
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
                    "result": str(values["drive_turn"]),
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


def _claude_execution(values: Mapping[str, Any]) -> Callable[[object], object]:
    """A real ``ClaudeSDKClient`` session over the adapter's own carrier.

    The carrier seam 1 built — the ``ClaudeAgentOptions`` holding the
    injected product, the agent's tool surface, and the permission gate — is
    exactly what the session runs under, so the ``ResultMessage`` this
    returns came out of the same configuration the harness would live under.
    """

    def execute(carrier: object) -> object:
        assert isinstance(carrier, ClaudeAgentOptions), type(carrier).__name__

        async def session() -> ResultMessage:
            client = ClaudeSDKClient(
                options=carrier, transport=_ScriptedResultTransport(values=values)
            )
            await client.connect()
            try:
                await client.query(
                    str(values["drive_turn"]), session_id=str(values["session_id"])
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

    return execute


def _adk_execution(values: Mapping[str, Any]) -> Callable[[object], object]:
    """A real ADK ``Runner`` run of the adapter's own execution vehicle.

    No model is configured anywhere: the adapter's vehicle is a ``BaseAgent``
    subclass yielding events — ADK's own sanctioned way to run something that
    is not a model call. The reported model and token counts are seeded onto
    ADK's session state, which is where the harness's own session machinery
    carries them into the run.
    """

    def execute(carrier: object) -> object:
        state = {
            **carrier.session_state,  # type: ignore[attr-defined]
            MODEL_STATE_KEY: values["reported_model"],
            USAGE_STATE_KEY: {
                "input_tokens": values["input_tokens"],
                "output_tokens": values["output_tokens"],
            },
        }

        async def run() -> tuple[object, ...]:
            sessions = InMemorySessionService()
            await sessions.create_session(
                app_name=str(values["app_name"]),
                user_id=str(values["user_id"]),
                session_id=str(values["session_id"]),
                state=state,
            )
            runner = Runner(
                agent=carrier.runnable,  # type: ignore[attr-defined]
                app_name=str(values["app_name"]),
                session_service=sessions,
            )
            return tuple(
                [
                    event
                    async for event in runner.run_async(
                        user_id=str(values["user_id"]),
                        session_id=str(values["session_id"]),
                        new_message=adk_types.Content(
                            role="user", parts=[adk_types.Part(text="")]
                        ),
                    )
                ]
            )

        return asyncio.run(run())

    return execute


def _langgraph_execution(values: Mapping[str, Any]) -> Callable[[object], object]:
    """A real run of the adapter's own compiled graph, no model.

    The reported model and token counts are merged into the run
    configuration's metadata under LangChain's own tracing keys — where a
    chat model would have written them — and read back only out of the run's
    final state.
    """

    def execute(carrier: object) -> object:
        config = dict(carrier.config)  # type: ignore[attr-defined]
        config["metadata"] = {
            **config["metadata"],
            MODEL_METADATA_KEY: values["reported_model"],
            USAGE_METADATA_KEY: {
                "input_tokens": values["input_tokens"],
                "output_tokens": values["output_tokens"],
            },
        }
        result: object = carrier.graph.invoke(  # type: ignore[attr-defined]
            carrier.state,  # type: ignore[attr-defined]
            config,
        )
        return result

    return execute


# --- the legs -----------------------------------------------------------------


class HarnessLeg(NamedTuple):
    """One harness's entry into the drive."""

    harness_id: str
    adapter: Any
    execute: Callable[[object], object]
    reported_model: str
    trace_id: str


def build_legs(harnesses: Mapping[str, Mapping[str, Any]]) -> tuple[HarnessLeg, ...]:
    """All three D-IMPL-24 legs at once — which is what portability *is*.

    Deployment values come from ``artifacts/harnesses.yaml``; the mechanism
    identifiers (which adapter class binds which block) are the only thing
    this function owns.
    """
    claude = dict(harnesses["claude-agent"])
    adk = dict(harnesses["adk"])
    langgraph = dict(harnesses["langgraph"])
    claude_adapter = ClaudeAgentAdapter(
        model=str(claude["model"]),
        mcp_server_name=str(claude["mcp_server_name"]),
        mcp_server_version=str(claude["mcp_server_version"]),
        effects="governed",
    )
    adk_adapter = AdkAdapter(
        model=str(adk["model"]),
        agent_name=str(adk["agent_name"]),
        session_id=str(adk["session_id"]),
        effects="governed",
    )
    langgraph_adapter = LangGraphAdapter(
        model=str(langgraph["model"]),
        thread_id=str(langgraph["thread_id"]),
        run_tags=tuple(langgraph["run_tags"]),
        effects="governed",
    )
    return (
        HarnessLeg(
            harness_id=claude_adapter.capabilities().harness_id,
            adapter=claude_adapter,
            execute=_claude_execution(claude),
            reported_model=str(claude["reported_model"]),
            trace_id=str(claude["session_id"]),
        ),
        HarnessLeg(
            harness_id=adk_adapter.capabilities().harness_id,
            adapter=adk_adapter,
            execute=_adk_execution(adk),
            reported_model=str(adk["reported_model"]),
            trace_id=str(adk["session_id"]),
        ),
        HarnessLeg(
            harness_id=langgraph_adapter.capabilities().harness_id,
            adapter=langgraph_adapter,
            execute=_langgraph_execution(langgraph),
            reported_model=str(langgraph["reported_model"]),
            trace_id=str(langgraph["thread_id"]),
        ),
    )


class LegRun(NamedTuple):
    """One harness's pass through the seams, and everything it is judged on."""

    harness_id: str
    product_bytes: bytes
    record: DecisionReplayRecord
    emission_address: str
    trace: HarnessTrace


def drive_leg(
    leg: HarnessLeg,
    *,
    agent: Agent,
    product: ContextProductContract,
    instructions: tuple[str, ...],
    build_record: Callable[
        [ContextProductContract, HarnessTrace], DecisionReplayRecord
    ],
) -> LegRun:
    """Run the same fabric-side operation under one harness, through its adapter.

    Every value the resulting :class:`LegRun` is judged on is derived from
    *this* harness's own pass through the seams — the product is recovered
    from the carrier seam 1 built, the harness block from a real execution
    driven through that harness's own loop machinery, the emission from
    seam 3. Nothing is copied in from a shared record.
    """
    # Seam 1 — and the product comes back out of the carrier, not off the shelf.
    carrier = leg.adapter.inject_context(
        agent=agent, products=(product,), instructions=instructions
    )
    delivered = recovered_products(carrier)
    assert len(delivered) == 1, (
        f"{leg.harness_id} delivered {len(delivered)} recoverable Context"
        " Product documents to its context surface, not exactly one"
    )
    recovered = ContextProductContract.model_validate_json(delivered[0])

    # Seam 3 — the governed emission, as this adapter produced it.
    emitted = leg.adapter.capture_effect(agent=agent, output=dict(product.payload))
    assert isinstance(emitted, EmittedEffect), emitted

    # Seam 4 — what this harness reported, from a real loop execution.
    trace = leg.adapter.replay_trace(execution=leg.execute(carrier))
    assert isinstance(trace, HarnessTrace)
    assert trace.harness_id == leg.harness_id != NO_HARNESS
    assert leg.reported_model in trace.model_version
    assert trace.trace_id == leg.trace_id != NO_HARNESS
    assert trace.input_tokens > 0 and trace.output_tokens > 0

    record = build_record(recovered, trace)
    return LegRun(
        harness_id=leg.harness_id,
        product_bytes=delivered[0],
        record=record,
        emission_address=content_hash(emitted),
        trace=trace,
    )


def governed_fields(record: DecisionReplayRecord) -> dict[str, bytes]:
    """Every field D-18 governs, canonically serialized, keyed by name.

    Keyed by name so a divergence *names itself* — a bare "the records
    differ" is not an actionable failure for a claim this load-bearing.
    """
    governed = {
        name: canonical_bytes(getattr(record, name)) for name in GOVERNED_DIMENSIONS
    }
    governed.update(
        {
            f"model_version.{name}": canonical_bytes(
                getattr(record.model_version, name)
            )
            for name in GOVERNED_MODEL_VERSION_FIELDS
        }
    )
    governed["tenant_id"] = canonical_bytes(record.tenant_id)
    return governed


def dimension_count(record: DecisionReplayRecord) -> int:
    """The dimensions this live record actually carries (INV-CH7-80).

    Dimensions are the fields whose value is itself a typed contract; the
    metadata fields are scalars and are excluded by shape, not by name.
    """
    return sum(
        1
        for name in DecisionReplayRecord.model_fields
        if isinstance(getattr(record, name), CCFContract)
    )
