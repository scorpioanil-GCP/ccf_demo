"""LOW-01 exploit test (HTTP half) — a non-ASCII bearer is a 401, never a 500.

The HTTP API reaches the same two token sources as the MCP doors, through
``runtime/ccf_runtime/http_api/auth.py::BearerTokenAuth.grant_for_request``,
and ``runtime/ccf_runtime/http_api/gate.py::AuthorizationGate`` calls the hook
with no ``try`` — so the row's measured ``TypeError`` from
``hmac.compare_digest(str, str)`` reached Starlette's ``ServerErrorMiddleware``
and the API answered ``500 text/plain`` rather than its typed refusal shape
(``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
"LOW-01" MEASURED block, D-IMPL-372).

The repair is in the sources (``runtime/ccf_runtime/mcp/auth.py``), so the
gate's EXISTING unauthenticated branch answers and the body is byte-identical to
an unrecognized token's. The test drives the real application through
``tests/http_api/gate_fixtures.py::build_gate_app`` with each of the two shipped
sources substituted in at the one construction site, and covers the stored
non-ASCII token (a whole-API outage on the unfixed tree).

NUL and over-8-KiB bearers were already 401: regression controls. The hostile
header is sent as bytes; httpx refuses a non-ASCII ``str`` header itself.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
from collections.abc import Mapping
from typing import Any

import httpx
import pytest

from ccf_runtime.mcp.auth import FileTokenSource, StaticTokenSource, TokenGrant

from . import gate_fixtures

STORED_NON_ASCII = "tök-stored-http"


def _substitute(
    monkeypatch: pytest.MonkeyPatch, kind: str, tmp_path: pathlib.Path, *, extra: bool
) -> None:
    real = StaticTokenSource

    def build(*, grants: Mapping[str, TokenGrant]) -> Any:
        merged = dict(grants)
        if extra:
            merged[STORED_NON_ASCII] = next(iter(grants.values()))
        if kind == "static":
            return real(grants=merged)
        path = tmp_path / "tokens.json"
        path.write_text(
            json.dumps({t: g.model_dump(mode="json") for t, g in merged.items()}),
            encoding="utf-8",
        )
        return FileTokenSource(path=path)

    monkeypatch.setattr(gate_fixtures, "StaticTokenSource", build)


def _get(app: Any, authorization: bytes) -> httpx.Response:
    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://fabric.invalid"
        ) as client:
            return await client.get("/openapi.json", headers=[(b"authorization", authorization)])

    return asyncio.run(go())


@pytest.mark.parametrize("kind", ["file", "static"])
def test_the_api_refuses_a_non_ascii_bearer_as_it_refuses_a_wrong_one(
    kind: str, fabric: Any, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _substitute(monkeypatch, kind, tmp_path, extra=False)
    gate = gate_fixtures.build_gate_app(fabric, tmp_path)
    wrong = _get(gate.app, b"Bearer nope")
    assert wrong.status_code == 401
    for value in (
        "Bearer ü".encode("latin-1"),
        "Bearer ü".encode("utf-8"),
        b"Bearer ab\x00cd",  # control: already 401 on the unfixed tree
        b"Bearer " + b"a" * 8193,  # control: already 401 on the unfixed tree
    ):
        got = _get(gate.app, value)
        assert got.status_code == 401, (value[:20], got.status_code, got.text[:200])
        assert got.content == wrong.content
        assert got.headers.get("content-type") == wrong.headers.get("content-type")
        assert got.headers.get("www-authenticate") == wrong.headers.get("www-authenticate")


@pytest.mark.parametrize("kind", ["file", "static"])
def test_a_stored_non_ascii_token_leaves_the_api_serving(
    kind: str, fabric: Any, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _substitute(monkeypatch, kind, tmp_path, extra=True)
    gate = gate_fixtures.build_gate_app(fabric, tmp_path)
    valid = _get(gate.app, f"Bearer {gate.token_everything}".encode())
    assert valid.status_code == 200, (valid.status_code, valid.text[:200])
    assert _get(gate.app, b"Bearer nope").status_code == 401
