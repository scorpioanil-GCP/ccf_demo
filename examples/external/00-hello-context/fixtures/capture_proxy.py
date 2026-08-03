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

Recording spec (D-09/D-10, 13.3):

* **Forward** the request path AND query string verbatim, so a capture is
  faithful to the call the SDK actually made (``?alt=sse`` selects a
  different response shape).
* **Record only a 200 carrying JSON.** Every other upstream answer — a
  429, a 500, an SSE stream, an HTML error page — is returned to the
  caller byte-for-byte and consumes NO fixture ordinal, so a transient
  vendor failure cannot renumber the real turns.
* **A request body that is not a JSON object is refused with 400**
  before anything is forwarded, for the same reason: it can never be
  recorded, so it must never claim an ordinal (and must never spend
  vendor credit on a call whose capture is impossible).

Security posture (T-13.2-06/T-13.3-04): API keys ride in HTTP headers, so
headers are NEVER written to disk in either direction. The outbound key is
injected at forward time from ``ANTHROPIC_API_KEY`` / ``GOOGLE_API_KEY``
in the process environment. Only request and response BODIES are
recorded, plus — when the request carried one — the query string under a
reserved key with ``key`` / ``api_key`` values replaced by a placeholder,
since Gemini also accepts the key as a query parameter.

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
from urllib.parse import parse_qsl, urlencode

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

#: Query parameters that can carry key material and are therefore never
#: persisted with their value (D-10).
REDACTED_QUERY_PARAMS = frozenset({"key", "api_key"})

#: Placeholder written in place of a redacted query value.
REDACTED = "REDACTED"

#: Reserved key under which a non-empty, redacted request query is
#: recorded in the request fixture. Absent when the request had no query,
#: which is why the committed (query-less) 13.2 fixtures are unaffected.
QUERY_KEY = "__request_query__"


def redact_query(query: str) -> str:
    """Replace every key-bearing query value with the placeholder (D-10).

    Gemini accepts ``?key=`` as an alternative to the header, so a
    faithfully-captured query can carry live key material. Parsed and
    re-encoded rather than string-spliced, so an escaped or repeated
    parameter cannot slip a secret past the filter.
    """
    return urlencode(
        [
            (name, REDACTED if name in REDACTED_QUERY_PARAMS else value)
            for name, value in parse_qsl(query, keep_blank_values=True)
        ]
    )


def build_app(
    out_dir: Path, transport: httpx.BaseTransport | None = None
) -> Starlette:
    """Host the capture proxy, writing fixture pairs into ``out_dir``.

    ``transport`` is the injection seam the tests use to stand in a fake
    upstream; production capture leaves it ``None`` and httpx dials the
    real vendor.
    """
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
            # D-09 ordinal conservation: a request whose body cannot be
            # recorded is not a capturable turn, so it is refused BEFORE
            # anything is forwarded and BEFORE an ordinal is claimed. Doing
            # the parse after the ordinal claim spent an ordinal on an
            # unhandled 500 — the exact renumbering hazard D-09 exists to
            # prevent.
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = None
            if not isinstance(parsed, dict):
                return JSONResponse(
                    {
                        "error": "request body is not a JSON object; "
                        "nothing forwarded, no ordinal consumed",
                        "path": path,
                    },
                    status_code=400,
                )
            request_doc: dict[str, object] = parsed
            headers = {key_header: key}
            for name in FORWARDED_REQUEST_HEADERS:
                if name in request.headers:
                    headers[name] = request.headers[name]
            # D-10: path AND query, verbatim. Dropping the query made the
            # capture unfaithful to the call the SDK actually made
            # (``?alt=sse`` selects a different response shape entirely).
            query = request.url.query
            target = f"{base}{path}" + (f"?{query}" if query else "")
            async with httpx.AsyncClient(
                timeout=120.0, transport=transport
            ) as client:
                upstream = await client.post(
                    target, content=body, headers=headers
                )
            # D-09: only a 200 carrying JSON is a recordable turn. Anything
            # else — a 429, a 500, an SSE stream, an HTML error page — goes
            # back to the caller byte-for-byte and consumes NO ordinal, so a
            # transient failure cannot shift the real turns' numbering.
            try:
                response_doc = (
                    upstream.json() if upstream.status_code == 200 else None
                )
            except ValueError:
                response_doc = None
            if response_doc is None:
                return Response(
                    content=upstream.content,
                    status_code=upstream.status_code,
                    media_type=upstream.headers.get("content-type"),
                )
            ordinal = counters[prefix]
            counters[prefix] = ordinal + 1
            # BODIES ONLY, both directions — headers carry key material and
            # are never serialized, in either direction (T-13.2-06). The one
            # non-body datum recorded is the request query, and only when
            # present, under a reserved key, with key-bearing params redacted
            # (D-10/T-13.3-04) — so a captured `?alt=` stays reviewable while
            # a captured `?key=` cannot reach the fixture tree. The body was
            # parsed and shape-checked before the ordinal was claimed.
            if query:
                request_doc[QUERY_KEY] = redact_query(query)
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
        uvicorn.Config(build_app(out_dir), log_level="error")
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
