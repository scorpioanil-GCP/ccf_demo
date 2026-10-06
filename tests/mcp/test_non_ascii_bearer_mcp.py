"""LOW-01 exploit test (MCP half) — a non-ASCII bearer is refused, never a 500.

The row (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
"LOW-01" and its MEASURED block, D-IMPL-372) measured
``hmac.compare_digest(str, str)`` in
``runtime/ccf_runtime/mcp/auth.py::FileTokenSource.grant_for`` and
``::StaticTokenSource.grant_for`` raising ``TypeError`` on a non-ASCII
operand. Two consequences, both tested here:

* a **presented** ``Authorization: Bearer ü`` reached Starlette's
  ``AuthenticationMiddleware`` as an exception and the MCP egress door answered
  ``500 text/plain``;
* a **stored** non-ASCII token (one line in a deployment's token file) made
  EVERY lookup raise, including an ASCII presentation — a whole-door outage.

``TokenSourceProtocol.grant_for`` promises ``None`` rather than an exception for
an unrecognized token. The repair keeps that promise, so the door's EXISTING
refusal branch (``mcp.server.auth.middleware.bearer_auth.RequireAuthMiddleware``)
answers, and the 401 is byte-identical to an unrecognized token's.

The NUL and over-8-KiB cases were already 401 on the unfixed tree: they are
regression controls, not exploit evidence. The hostile header is sent as BYTES,
because httpx refuses a non-ASCII ``str`` header before the server sees it.

What this does NOT assert: that no traceback is logged. In-process under
``httpx.ASGITransport`` there is no server to log one, so a ``caplog`` negative
would pass on the broken tree too; the status and body are the evidence.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
from typing import Any

import httpx
import pytest

from ccf_runtime.mcp import auth as mcp_auth
from ccf_runtime.mcp.auth import (
    FileTokenSource,
    SourceBackedTokenVerifier,
    StaticTokenSource,
    TokenGrant,
)
from tests.mcp import guarded_servers

#: Test deployment vocabulary; the SDK ships none of it.
VALID = "tok"
STORED_NON_ASCII = "tök-stored"

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "low01", "version": "0"},
    },
}


def _grant() -> TokenGrant:
    return TokenGrant(
        client_id=guarded_servers.PRINCIPAL,
        scopes=(guarded_servers.SCOPE,),
        tenants=frozenset({guarded_servers.TENANT}),
    )


def _file_source(tmp_path: pathlib.Path, tokens: tuple[str, ...]) -> FileTokenSource:
    path = tmp_path / "tokens.json"
    path.write_text(
        json.dumps({t: _grant().model_dump(mode="json") for t in tokens}),
        encoding="utf-8",
    )
    return FileTokenSource(path=path)


def _static_source(tokens: tuple[str, ...]) -> StaticTokenSource:
    return StaticTokenSource(grants={t: _grant() for t in tokens})


def _source(kind: str, tmp_path: pathlib.Path, tokens: tuple[str, ...]) -> Any:
    return _file_source(tmp_path, tokens) if kind == "file" else _static_source(tokens)


# --- the two sources, directly ----------------------------------------------


@pytest.mark.parametrize("kind", ["file", "static"])
@pytest.mark.parametrize(
    "presented",
    ["\u00fc", "t\u00f6k", "\u00fc" * 4096, "\udcff"],
    ids=["u-umlaut", "embedded-o-umlaut", "long-non-ascii", "lone-surrogate"],
)
def test_a_non_ascii_presentation_is_unrecognized_not_an_exception(
    kind: str, presented: str, tmp_path: pathlib.Path
) -> None:
    source = _source(kind, tmp_path, (VALID,))
    assert source.grant_for(token=presented) is None


@pytest.mark.parametrize("kind", ["file", "static"])
def test_a_stored_non_ascii_token_does_not_take_the_door_down(
    kind: str, tmp_path: pathlib.Path
) -> None:
    source = _source(kind, tmp_path, (STORED_NON_ASCII, VALID))
    assert source.grant_for(token=VALID) == _grant()
    assert source.grant_for(token="plainascii") is None
    assert source.grant_for(token=STORED_NON_ASCII) == _grant()


# --- the MCP egress door, in-process ----------------------------------------


async def _post(app: Any, authorization: bytes) -> httpx.Response:
    headers = [
        (b"authorization", authorization),
        (b"accept", b"application/json, text/event-stream"),
        (b"content-type", b"application/json"),
    ]
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://guard.invalid") as c:
        return await c.post("/mcp", content=json.dumps(_INIT).encode(), headers=headers)


def _drive(server: Any, values: list[bytes]) -> list[httpx.Response]:
    app = server.streamable_http_app()

    async def go() -> list[httpx.Response]:
        async with app.router.lifespan_context(app):
            return [await _post(app, value) for value in values]

    return asyncio.run(go())


def _same_refusal(got: httpx.Response, reference: httpx.Response) -> None:
    assert got.status_code == 401, (got.status_code, got.text[:200])
    assert got.content == reference.content
    assert got.headers.get("content-type") == reference.headers.get("content-type")
    assert got.headers.get("www-authenticate") == reference.headers.get("www-authenticate")


@pytest.mark.parametrize("kind", ["file", "static"])
def test_the_egress_door_refuses_a_non_ascii_bearer_as_it_refuses_a_wrong_one(
    kind: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(kind, tmp_path, (VALID,))
    monkeypatch.setattr(
        guarded_servers, "_verifier", lambda: SourceBackedTokenVerifier(source=source)
    )
    server = guarded_servers.build_for("egress", tmp_path)
    wrong, latin1, utf8, nul, long = _drive(
        server,
        [
            b"Bearer nope",
            "Bearer ü".encode("latin-1"),
            "Bearer ü".encode("utf-8"),
            b"Bearer ab\x00cd",  # control: already 401 on the unfixed tree
            b"Bearer " + b"a" * 8193,  # control: already 401 on the unfixed tree
        ],
    )
    assert wrong.status_code == 401
    for got in (latin1, utf8, nul, long):
        _same_refusal(got, wrong)


@pytest.mark.parametrize("kind", ["file", "static"])
def test_a_stored_non_ascii_token_leaves_the_egress_door_serving(
    kind: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(kind, tmp_path, (STORED_NON_ASCII, VALID))
    monkeypatch.setattr(
        guarded_servers, "_verifier", lambda: SourceBackedTokenVerifier(source=source)
    )
    server = guarded_servers.build_for("egress", tmp_path)
    valid, wrong = _drive(server, [f"Bearer {VALID}".encode(), b"Bearer nope"])
    assert valid.status_code == 200, (valid.status_code, valid.text[:200])
    assert wrong.status_code == 401, (wrong.status_code, wrong.text[:200])


def test_the_module_still_compares_in_constant_time() -> None:
    """The repair must not trade the TypeError for a timing oracle (``==``)."""
    import inspect

    text = inspect.getsource(mcp_auth)
    assert "hmac.compare_digest" in text
