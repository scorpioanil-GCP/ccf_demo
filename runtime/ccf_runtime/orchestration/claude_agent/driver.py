"""`ClaudeAgentWorkflowDriver` — CCF workflows driven through the Claude Agent SDK.

SDK-defined (CLAUDE.md §8.1; D-IMPL-17/60 — the third of the three driver
legs; the 07-13 feasibility probe answered GO before this module existed).
Implements :class:`~ccf.orchestration.protocol.OrchestrationProtocol` by
driving a ``ClaudeSDKClient`` session whose tools and hooks advance CCF
workflow nodes through the engine's **public** surface — ``execute`` and
``resume`` on WorkflowFactory-built handles — and nothing else. The session
choreography here is this module's own (A7, D-19): nothing is read from,
shared with, or imported out of the harness-adapter tree, and the
``d06-orchestration-split`` lint holds that boundary structurally. The
adapter's ResultMessage seam-4 obligation (advisory A3) is Phase 8's and is
deliberately not claimed here.

**The CCF engine is authoritative for state and audit (T-07-33).** The
suspended :class:`~ccf_runtime.workflow.state.WorkflowStateRecord` lives on
the Control Plane store, written through the engine's audited write surface;
the execution trace writes through to the ArtifactStore; the typed outcomes
the driver returns are the engine's own, verbatim. What the SDK session
machinery holds is **transcript position only** — session identity and the
scalar turn results — and the conformance suite asserts that nothing
CCF-typed is in it (:meth:`ClaudeAgentWorkflowDriver.session_transcript` is
the introspection seam it asserts through).

**How the SDK expresses the drive** (the three surfaces the probe proved):
node advancement travels as SDK-MCP **tool invocations** — the SDK's own
control protocol routes ``tools/call`` into in-process handlers that call
the engine; the hitl-gate yields through the **hook surface** —
``CanUseTool`` gates every call and a ``PostToolUse`` ``HookCallback``
surfaces the engine's suspend handle driver-side; and a resume carries the
**same session identity** (the same ``session_id``) — each turn runs a
fresh client over a fresh scripted transport; the engine, not the session,
holds the continuity — and its tool
turn hands the externally-bound decision to the engine's own ``resume`` —
routing stays the workflow artifact's statement (CINV-01), interpreted by
the engine, never by the session.

**No model, no network, no ``claude`` CLI (D-09).** The Claude Agent SDK
has no first-class DAG and its default transport spawns the CLI toward a
live model. The SDK's public seam for exactly this situation is
``claude_agent_sdk.Transport``: ``ClaudeSDKClient(transport=...)`` runs the
real client machinery — initialize handshake, hook registration and
dispatch, permission callbacks, SDK-MCP JSONRPC routing, message parsing —
over this module's in-process transport, which plays only the wire's role.
The model would decide *when* to invoke the tools; the driver scripts that
choice deterministically, because a workflow drive is not a model decision
and replay equivalence (T-07-34) forbids one.

Not an algorithmic module: it imports an orchestrator SDK, which is exactly
what the CINV-02 carve-out for ``ccf_runtime.orchestration`` exists to
permit here and nowhere else.

**Loop-safety (WR-03; Phase-9 CONTEXT D-10/D-11).** Outcome lookups raise
the shared typed hierarchy
(:class:`~ccf_runtime.orchestration.common.SegmentNotExecutedError`), never
a bare ``KeyError``; the sync introspection seam holds no direct
``asyncio.run``, so callers hosted inside a running event loop work as-is.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookContext,
    HookMatcher,
    PermissionResult,
    PermissionResultAllow,
    ResultMessage,
    ToolPermissionContext,
    Transport,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import HookInput, HookJSONOutput

from ccf.contracts.base import CCFContract
from ccf.workflow.factory import Workflow
from ccf_runtime.orchestration.common import (
    SegmentNotExecutedError,
    WorkflowDriverError,
)
from ccf_runtime.workflow.engine import WorkflowEngine, WorkflowSuspended

__all__ = ["ClaudeAgentWorkflowDriver"]

#: The SDK-MCP server the driver's node-advancement tools live on — driver
#: plumbing, not deployment vocabulary: it never leaves the session.
_SERVER_NAME = "ccf-orchestration"

#: Tool names for the two engine advancements a drive is made of.
_ADVANCE_TOOL = "advance_workflow"
_RESUME_TOOL = "resume_workflow"


class _ScriptedSessionTransport(Transport):
    """The wire's role, scripted; every other participant is the real SDK.

    Plays the CLI side of the SDK's control protocol: answers the client's
    ``initialize`` (recording the hook callback ids the SDK registered) and,
    per user turn, issues the CLI-side control requests a live session would
    — ``can_use_tool``, SDK-MCP ``tools/call``, and ``hook_callback`` when
    the engine suspended — which the SDK dispatches into the driver's real
    handlers. The turn ends with a ``result`` frame, as the CLI ends one.
    """

    def __init__(self) -> None:
        self._out: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._hook_ids: list[str] = []
        self._turns: list[asyncio.Task[None]] = []
        self._counter = 0

    # -- Transport ------------------------------------------------------------

    async def connect(self) -> None:
        return None

    def is_ready(self) -> bool:
        return True

    async def end_input(self) -> None:
        return None

    async def close(self) -> None:
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
            # SDK -> "CLI" requests (initialize, interrupt, ...): acknowledge,
            # recording the hook callback ids initialize registered.
            request = message.get("request", {})
            if request.get("subtype") == "initialize":
                for matchers in (request.get("hooks") or {}).values():
                    for matcher in matchers:
                        self._hook_ids.extend(
                            matcher.get("hookCallbackIds", [])
                        )
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
            # The SDK's answer to a CLI-side request this transport issued.
            response = message.get("response", {})
            future = self._pending.pop(response.get("request_id", ""), None)
            if future is not None and not future.done():
                future.set_result(response)
        elif kind == "user":
            instruction = json.loads(message["message"]["content"])
            self._turns.append(
                asyncio.ensure_future(
                    self._guarded_turn(
                        instruction, message.get("session_id", "default")
                    )
                )
            )

    # -- the scripted CLI side -------------------------------------------------

    async def _request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Issue one CLI-side control request and await the SDK's response."""
        self._counter += 1
        request_id = f"ccf-orch-req-{self._counter}"
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

    async def _guarded_turn(
        self, instruction: dict[str, Any], session_id: str
    ) -> None:
        """`_turn` with its failure mode made visible (Phase-9 review WR-02).

        Turns are launched fire-and-forget from :meth:`write`, so an
        exception inside :meth:`_turn` would otherwise never be observed —
        no ``result`` frame reaches ``self._out`` and the client's
        ``receive_response`` awaits forever. Any scripted-protocol drift
        must fail fast instead: catch everything, emit an ``is_error``
        result frame carrying the cause, and let ``_drive`` raise it typed.
        """
        try:
            await self._turn(instruction, session_id)
        except Exception as error:  # noqa: BLE001 — the wire must not hang
            await self._out.put(
                {
                    "type": "result",
                    "subtype": "error_during_execution",
                    "duration_ms": 0,
                    "duration_api_ms": 0,
                    "is_error": True,
                    "num_turns": 1,
                    "session_id": session_id,
                    "result": f"{type(error).__name__}: {error}",
                }
            )

    async def _turn(
        self, instruction: dict[str, Any], session_id: str
    ) -> None:
        """One turn: permission check, tool call, gate hook, result frame."""
        tool_name = str(instruction["tool"])
        arguments = dict(instruction["arguments"])
        qualified = f"mcp__{_SERVER_NAME}__{tool_name}"

        permission = await self._request(
            {
                "subtype": "can_use_tool",
                "tool_name": qualified,
                "input": arguments,
                "tool_use_id": f"tool-{self._counter}",
            }
        )
        if permission["response"].get("behavior") != "allow":
            raise RuntimeError(
                f"the driver's own permission callback denied {qualified!r}"
            )

        called = await self._request(
            {
                "subtype": "mcp_message",
                "server_name": _SERVER_NAME,
                "message": {
                    "jsonrpc": "2.0",
                    "id": self._counter,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
            }
        )
        content = called["response"]["mcp_response"]["result"]["content"]
        text = str(content[0]["text"])

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


class ClaudeAgentWorkflowDriver:
    """The Claude Agent SDK leg of `OrchestrationProtocol` (D-IMPL-60 leg 3).

    Args:
        engine: The CCF workflow engine this driver drives. Injected, never
            constructed here; its wiring is the composition root's business,
            and its authority over state and audit is the whole point.
    """

    def __init__(self, *, engine: WorkflowEngine) -> None:
        self._engine = engine
        #: The engine's typed outcomes, held driver-side keyed by
        #: ``(tenant, execution_id)`` — deliberately NEVER handed to the
        #: session, so nothing CCF-typed reaches the SDK's machinery.
        self._outcomes: dict[tuple[str, str], CCFContract] = {}
        #: Scalar session transcript per execution: session identity and
        #: turn results — the SDK-side "position" the suite asserts over.
        self._transcripts: dict[tuple[str, str], list[str]] = {}

    def _outcome(self, tenant: str, execution_id: str) -> CCFContract:
        """The engine's typed outcome for one execution — typed on absence.

        Phase-9 CONTEXT D-10/D-11 (WR-03): a never-executed segment is a
        driver condition, not a dict accident —
        :class:`SegmentNotExecutedError`, never a bare ``KeyError``. The
        same helper shape on every driver leg, parity-asserted.
        """
        try:
            return self._outcomes[(tenant, execution_id)]
        except KeyError:
            raise SegmentNotExecutedError(
                f"no executed segment for tenant {tenant!r},"
                f" execution {execution_id!r}"
            ) from None

    # -- the session choreography, authored against the engine's surface ------

    def _options(
        self, workflow: Workflow, key: tuple[str, str]
    ) -> ClaudeAgentOptions:
        """One session's options: the two node-advancement tools, the gate
        hook, and the permission callback — all closing over the engine's
        public surface and this driver's scalar transcript, nothing else."""

        def _park(outcome: CCFContract) -> str:
            self._outcomes[key] = outcome
            return (
                "suspended"
                if isinstance(outcome, WorkflowSuspended)
                else "completed"
            )

        @tool(_ADVANCE_TOOL, "Advance one CCF workflow run", {"execution_id": str})
        async def advance(args: dict[str, Any]) -> dict[str, Any]:
            outcome = await self._engine.execute(
                workflow, execution_id=str(args["execution_id"])
            )
            return {"content": [{"type": "text", "text": _park(outcome)}]}

        @tool(
            _RESUME_TOOL,
            "Resume a suspended CCF workflow run",
            {"execution_id": str, "decision": str},
        )
        async def resume(args: dict[str, Any]) -> dict[str, Any]:
            outcome = await self._engine.resume(
                workflow,
                execution_id=str(args["execution_id"]),
                decision=str(args["decision"]),
            )
            return {"content": [{"type": "text", "text": _park(outcome)}]}

        async def gate_hook(
            input_data: HookInput,
            tool_use_id: str | None,
            context: HookContext,
        ) -> HookJSONOutput:
            """The gate yield: record the parked gate, scalars only."""
            outcome = self._outcomes.get(key)
            if isinstance(outcome, WorkflowSuspended):
                self._transcripts.setdefault(key, []).append(
                    f"gate:{outcome.gate}"
                )
            return {}

        async def allow(
            tool_name: str,
            tool_input: dict[str, Any],
            context: ToolPermissionContext,
        ) -> PermissionResult:
            return PermissionResultAllow()

        return ClaudeAgentOptions(
            mcp_servers={
                _SERVER_NAME: create_sdk_mcp_server(
                    name=_SERVER_NAME,
                    version="1.0.0",
                    tools=[advance, resume],
                )
            },
            hooks={"PostToolUse": [HookMatcher(hooks=[gate_hook])]},
            can_use_tool=allow,
        )

    async def _drive(
        self,
        workflow: Workflow,
        execution_id: str,
        instruction: dict[str, Any],
    ) -> CCFContract:
        """One session turn against the engine; the SDK machinery is real."""
        tenant = workflow.definition.tenant
        key = (tenant, execution_id)
        session_id = f"{tenant}/{execution_id}"
        client = ClaudeSDKClient(
            options=self._options(workflow, key),
            transport=_ScriptedSessionTransport(),
        )
        await client.connect()
        try:
            await client.query(json.dumps(instruction), session_id=session_id)
            async for message in client.receive_response():
                if isinstance(message, ResultMessage):
                    if message.is_error:
                        raise WorkflowDriverError(
                            f"scripted session turn failed for"
                            f" {session_id!r}: {message.result}"
                        )
                    self._transcripts.setdefault(key, []).append(
                        f"{message.session_id}:{message.result}"
                    )
        finally:
            await client.disconnect()
        return self._outcome(tenant, execution_id)

    # -- OrchestrationProtocol -------------------------------------------------

    async def start_execution(
        self, *, workflow: Workflow, execution_id: str
    ) -> CCFContract:
        """Drive the session's advance turn; if the engine suspends, the
        gate hook records the park and the session yields control back to
        CCF; the engine's own typed outcome comes back verbatim."""
        return await self._drive(
            workflow,
            execution_id,
            {
                "tool": _ADVANCE_TOOL,
                "arguments": {"execution_id": execution_id},
            },
        )

    async def resume_execution(
        self, *, workflow: Workflow, execution_id: str, decision: str
    ) -> CCFContract:
        """Continue under the same session identity (same ``session_id``)
        with the resume turn — a fresh client over a fresh scripted
        transport; continuity lives in the engine: the externally-bound
        decision goes to the engine's own resume surface, and the session
        parks again on a later gate if the engine suspends."""
        return await self._drive(
            workflow,
            execution_id,
            {
                "tool": _RESUME_TOOL,
                "arguments": {
                    "execution_id": execution_id,
                    "decision": decision,
                },
            },
        )

    # -- introspection for the conformance suite -------------------------------

    def session_transcript(
        self, *, workflow: Workflow, execution_id: str
    ) -> tuple[object, ...]:
        """Every value the session machinery carried for one execution.

        The conformance suite's T-07-33 assertion runs over this: session
        identity, turn results, and parked-gate names — scalar strings all
        the way down, no CCF workflow state.
        """
        return tuple(
            self._transcripts.get(
                (workflow.definition.tenant, execution_id), ()
            )
        )
