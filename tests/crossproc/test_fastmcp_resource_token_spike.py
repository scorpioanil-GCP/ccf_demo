"""Spike A1 (10-01 Task 1): can a FastMCP *resource* handler see the token?

RESEARCH assumption A1: the MCP door's tool handler reads the verified
identity via ``mcp.server.auth.middleware.auth_context.get_access_token()``
(``hitl_server.py`` submit path), but the queue *resource* handler does no
identity work today — and plan 10-03 wants to enforce tenant authorization
on the queue read. This spike closes the assumption empirically: an
in-process MCP client reads resources against a real
``build_hitl_server(...)`` instance with the auth middleware bound (verifier
+ settings, exactly the D-26 pairing), over the server's own
streamable-HTTP ASGI app, and asserts that ``get_access_token()`` returns
the verified token *inside a resource handler*.

The instrumented handler is registered on the very ``FastMCP`` instance
``build_hitl_server`` returns, so the middleware stack under test is the
production server's, not a lookalike. In-process ASGI (no subprocess) is
deliberate: the auth context is request-scoped middleware state, and the
transport being loopback-vs-ASGI is irrelevant to whether the contextvar is
populated for resource reads.

Verdict recorded for plan 10-03: **get_access_token() IS available inside
resource handlers** on an authenticated ``build_hitl_server`` instance —
the queue-read door can use the same mechanism as the action tool.

Token value, client id, scope, tenant: test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import TextResourceContents
from pydantic import AnyHttpUrl, AnyUrl

from ccf.hitl.transport import PendingHitlEvent
from ccf.mcp.client import run_with_session
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.hitl_server import build_hitl_server, hitl_queue_uri

#: Test deployment vocabulary. The SDK ships none of these values.
SPIKE_TOKEN = "ccf-spike-token"
CLIENT_ID = "spike-caller-1"
SCOPE = "ccf:hitl"
TENANT = "spike-tenant"
#: Loopback with an explicit port, because FastMCP's DNS-rebinding
#: protection defaults allow ``127.0.0.1:*`` (host **with** a port) — even
#: over an in-process ASGI transport where no socket exists. The port
#: number itself is arbitrary: nothing binds it.
BASE_URL = "http://127.0.0.1:8123"

#: The instrumented resource this spike registers on the production server.
SPIKE_RESOURCE_URI = "ccf-hitl-queue://spike-token-visibility/probe"


def _build_spiked_server(tmp_path: Path) -> FastMCP:
    """A real authenticated HITL server plus one instrumented resource."""
    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
        {
            SPIKE_TOKEN: {
                "client_id": CLIENT_ID,
                "scopes": [SCOPE],
                "tenants": [TENANT],
            }
        }
    ),
        encoding="utf-8",
    )

    def queue_view(*, tenant: str) -> tuple[PendingHitlEvent, ...]:
        return ()

    def action_route(*, submission: Any) -> str:  # pragma: no cover
        raise AssertionError("the spike never submits an action")

    server = build_hitl_server(
        server_name="ccf-a1-spike",
        queue_view=queue_view,
        action_route=action_route,
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(path=token_file)
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{BASE_URL}/mcp"),
            required_scopes=[SCOPE],
        ),
    )

    @server.resource(SPIKE_RESOURCE_URI, mime_type="application/json")
    def token_visibility() -> str:
        """Report what ``get_access_token()`` yields in resource context."""
        token = get_access_token()
        return json.dumps(
            {
                "token_present": token is not None,
                "client_id": None if token is None else token.client_id,
                "scopes": [] if token is None else list(token.scopes),
            }
        )

    return server


def _read_resource(server: FastMCP, uri: str) -> str:
    """Read one resource over the server's own ASGI app, authenticated.

    ``httpx.ASGITransport`` does not drive the ASGI lifespan, and the
    FastMCP streamable-HTTP app starts its session manager *in* the
    lifespan — so the lifespan context is entered explicitly here, which
    is exactly what uvicorn does for the cross-process siblings.
    """
    app = server.streamable_http_app()

    async def operation(session: ClientSession) -> str:
        result = await session.read_resource(AnyUrl(uri))
        return "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    def client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {SPIKE_TOKEN}"},
        )

    async def with_lifespan() -> str:
        async with app.router.lifespan_context(app):
            return await run_with_session(
                url=f"{BASE_URL}/mcp",
                operation=operation,
                http_client_factory=client_factory,
            )

    return asyncio.run(with_lifespan())


def test_a1_resource_handlers_observe_the_verified_token(
    tmp_path: Path,
) -> None:
    """A1 closes: ``get_access_token()`` is non-None inside a resource
    handler on an authenticated ``build_hitl_server`` instance, and it is
    the *verified* identity — plan 10-03 can enforce queue-read authz with
    the exact mechanism the action tool already uses."""
    server = _build_spiked_server(tmp_path)

    body = json.loads(_read_resource(server, SPIKE_RESOURCE_URI))

    assert body["token_present"] is True
    assert body["client_id"] == CLIENT_ID
    assert body["scopes"] == [SCOPE]


def test_the_real_queue_resource_serves_under_the_same_middleware(
    tmp_path: Path,
) -> None:
    """The production ``hitl_queue`` resource answers through the same
    authenticated request pipeline the spike probed — the A1 verdict is
    about the very handler plan 10-03 will guard."""
    server = _build_spiked_server(tmp_path)

    body = json.loads(_read_resource(server, hitl_queue_uri(tenant=TENANT)))

    assert body == {"tenant": TENANT, "events": []}
