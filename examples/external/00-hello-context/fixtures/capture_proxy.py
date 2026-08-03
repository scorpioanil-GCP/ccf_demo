"""Recording forward-proxy for one-time fixture capture (13.2 D-01a/D-02).

An ephemeral tool — not wired into the Makefile or CI. It reuses the same
base-URL seam the replay server does (``ANTHROPIC_BASE_URL`` /
``GOOGLE_GEMINI_BASE_URL``, D-09): point the client legs here instead of
at ``../replay_server.py`` and each request is forwarded to the real
vendor API while its body is teed to disk in the committed fixture naming
scheme (``<prefix>-NN-request.json`` / ``<prefix>-NN.json``).

Routing is by path suffix, exactly as in ``replay_server.py``:

* suffix ``/v1/messages``      -> forwarded to api.anthropic.com,
                                  recorded as ``anthropic-NN``
* suffix ``:generateContent``  -> forwarded to
                                  generativelanguage.googleapis.com,
                                  recorded as ``gemini-NN``

Security posture (T-13.2-06): API keys ride in HTTP headers, so headers
are NEVER written to disk in either direction. The outbound key is
injected at forward time from ``ANTHROPIC_API_KEY`` / ``GOOGLE_API_KEY``
in the process environment; only request and response BODIES are recorded.

Binds 127.0.0.1 on port 0 and prints ``READY <port>`` once started (the
suite's handshake pattern). Recordings land in an output directory given
as ``argv[1]`` (default: this ``fixtures/`` directory — review the diff
before committing, per README.md).
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

import anyio
import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

_FIXTURES_DIR = Path(__file__).resolve().parent

#: Path suffix -> (fixture filename prefix, upstream base, key env var,
#: key header name). Same routing table shape as replay_server.SUFFIXES.
ROUTES: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "/v1/messages",
        "anthropic",
        "https://api.anthropic.com",
        "ANTHROPIC_API_KEY",
        "x-api-key",
    ),
    (
        ":generateContent",
        "gemini",
        "https://generativelanguage.googleapis.com",
        "GOOGLE_API_KEY",
        "x-goog-api-key",
    ),
)

#: Request headers copied upstream. Auth headers are injected separately
#: from env; everything else (including any inbound Authorization or
#: x-api-key from the client) is dropped and re-derived.
FORWARDED_REQUEST_HEADERS = ("content-type", "anthropic-version", "accept")


def _build_app(out_dir: Path) -> Starlette:
    out_dir.mkdir(parents=True, exist_ok=True)
    counters: dict[str, int] = {prefix: 0 for _, prefix, *_ in ROUTES}

    async def capture(request: Request) -> Response:
        path = request.url.path
        for suffix, prefix, base, key_env, key_header in ROUTES:
            if not path.endswith(suffix):
                continue
            key = os.environ.get(key_env)
            if not key:
                return JSONResponse(
                    {"error": f"{key_env} not set in proxy environment"},
                    status_code=500,
                )
            body = await request.body()
            headers = {key_header: key}
            for name in FORWARDED_REQUEST_HEADERS:
                if name in request.headers:
                    headers[name] = request.headers[name]
            async with httpx.AsyncClient(timeout=120.0) as client:
                upstream = await client.post(
                    f"{base}{path}", content=body, headers=headers
                )
            ordinal = counters[prefix]
            counters[prefix] = ordinal + 1
            # BODIES ONLY, both directions — headers carry key material
            # and are never serialized (T-13.2-06).
            request_doc = json.loads(body)
            response_doc = upstream.json()
            (out_dir / f"{prefix}-{ordinal:02d}-request.json").write_text(
                json.dumps(request_doc, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (out_dir / f"{prefix}-{ordinal:02d}.json").write_text(
                json.dumps(response_doc, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            return JSONResponse(
                response_doc, status_code=upstream.status_code
            )
        return JSONResponse(
            {"error": "no capture route for path", "path": path},
            status_code=500,
        )

    return Starlette(
        routes=[Route("/{rest:path}", capture, methods=["POST"])]
    )


def main() -> None:
    """Bind loopback port 0, host the capture app, announce READY."""
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else _FIXTURES_DIR

    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(_build_app(out_dir), log_level="error")
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
