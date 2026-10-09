"""A real MCP client session to a built server, over in-memory streams, with every JSON-RPC message kept.

Test infrastructure for the D3b subject-match tests (``D-IMPL-378``, Dave's 16:40 MST item 5). The client is
``mcp.ClientSession`` and the server is the built ``FastMCP``'s own low-level server, so every request and every
answer is the JSON-RPC message the library serializes for the wire: a refusal is the ``CallToolResult`` the
low-level server makes of an exception, and a blob is the base64 member a ``bytes`` handler produces. Only the
transport differs from a deployment's (memory streams, not streamable HTTP), so the bearer middleware does not run:
the caller's verified grant is placed in the auth context exactly as the middleware would place it, and the
guard (``ccf_runtime.mcp.tenancy.TenantGuardedServer``) decides on it as it does on every transport.

Tenant, principal and scope names are test deployment vocabulary (CINV-01 applied to test data).
"""

from __future__ import annotations

import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage

import ccf.artifacts.mcp_store as mcp_store_module
from ccf_runtime.mcp.auth import TokenGrant
from tests.mcp import test_artifact_server_authorized as authorized_server

_T = TypeVar("_T")

CLIENT_TO_SERVER = "client->server"
SERVER_TO_CLIENT = "server->client"


@dataclass
class Wire:
    """Every JSON-RPC message that crossed, in order, as ``(direction, serialized message)``."""

    messages: list[tuple[str, str]] = field(default_factory=list)

    def haystack(self) -> bytes:
        """Everything that crossed: each message's text, and every base64 ``blob`` member decoded beside it."""
        parts: list[bytes] = []
        for _direction, text in self.messages:
            parts.append(text.encode("utf-8"))
            parts.extend(_decoded_blobs(json.loads(text)))
        return b"\n".join(parts)

    def requests(self, method: str) -> list[dict[str, Any]]:
        """Every client request of ``method``, parsed."""
        return [
            parsed
            for direction, text in self.messages
            if direction == CLIENT_TO_SERVER and (parsed := json.loads(text)).get("method") == method
        ]

    def answers(self, method: str) -> list[str]:
        """The server's message answering each request of ``method``, exactly as serialized, in order."""
        ids = [request["id"] for request in self.requests(method)]
        by_id = {
            json.loads(text).get("id"): text
            for direction, text in self.messages
            if direction == SERVER_TO_CLIENT and "id" in json.loads(text)
        }
        return [by_id[identifier] for identifier in ids]


def _decoded_blobs(node: Any) -> list[bytes]:
    if isinstance(node, dict):
        found = []
        blob = node.get("blob")
        if isinstance(blob, str):
            found.append(base64.b64decode(blob))
        for value in node.values():
            found.extend(_decoded_blobs(value))
        return found
    if isinstance(node, list):
        return [decoded for item in node for decoded in _decoded_blobs(item)]
    return []


async def captured_session(
    server: FastMCP,
    grant: TokenGrant | None,
    wire: Wire,
    body: Callable[[ClientSession], Awaitable[_T]],
) -> _T:
    """Run ``body`` on a ``ClientSession`` connected to ``server`` as ``grant`` (``None``: no identity), keeping the wire."""
    client_send, server_receive = anyio.create_memory_object_stream[SessionMessage | Exception](32)
    server_send, client_receive = anyio.create_memory_object_stream[SessionMessage | Exception](32)
    tapped_send, tapped_receive = anyio.create_memory_object_stream[SessionMessage | Exception](32)
    answered_send, answered_receive = anyio.create_memory_object_stream[SessionMessage | Exception](32)

    async def tee(source: Any, sink: Any, direction: str) -> None:
        async with sink:
            async for item in source:
                if isinstance(item, SessionMessage):
                    wire.messages.append(
                        (direction, item.message.model_dump_json(by_alias=True, exclude_none=True))
                    )
                await sink.send(item)

    reset = authorized_server._as_grant(grant) if grant is not None else None
    try:
        low = server._mcp_server
        async with anyio.create_task_group() as group:
            group.start_soon(tee, server_receive, tapped_send, CLIENT_TO_SERVER)
            group.start_soon(tee, client_receive, answered_send, SERVER_TO_CLIENT)
            group.start_soon(
                lambda: low.run(
                    tapped_receive, server_send, low.create_initialization_options(), raise_exceptions=False
                )
            )
            async with ClientSession(read_stream=answered_receive, write_stream=client_send) as session:
                await session.initialize()
                result = await body(session)
            group.cancel_scope.cancel()
        return result
    finally:
        if reset is not None:
            auth_context_var.reset(reset)


def call(server: FastMCP, grant: TokenGrant | None, tool: str, arguments: dict[str, Any], wire: Wire) -> Any:
    """One ``tools/call`` of ``tool`` over a fresh captured session; returns the ``CallToolResult``."""

    async def body(session: ClientSession) -> Any:
        return await session.call_tool(tool, arguments)

    return anyio.run(captured_session, server, grant, wire, body)


def route_store_through(
    monkeypatch: pytest.MonkeyPatch, server: FastMCP, grant: TokenGrant, wire: Wire
) -> None:
    """Every ``McpArtifactStore`` session-per-call runs over a captured in-memory session to ``server`` as ``grant``."""

    async def run_with_session(*, url: str, operation: Any, http_client_factory: Any) -> Any:
        return await captured_session(server, grant, wire, operation)

    monkeypatch.setattr(mcp_store_module, "run_with_session", run_with_session)
