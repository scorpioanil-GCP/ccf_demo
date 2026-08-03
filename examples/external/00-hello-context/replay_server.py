"""examples/external/00-hello-context — transport-level model-API replay (D-09).

CI determinism for the LLM client legs without a single code branch in
them: the legs' SDKs are pointed here via their own base-URL environment
variables (``ANTHROPIC_BASE_URL``, ``GOOGLE_GEMINI_BASE_URL``), and this
server answers each POST with a recorded fixture, verbatim. Live mode is
the same client code with the env vars unset — this server is then simply
not in the path.

Routing is by PATH SUFFIX, not exact path, because each SDK appends its
own route to the base URL:

* suffix ``/v1/messages``      -> Anthropic Messages-API fixtures
* suffix ``:generateContent``  -> Gemini generateContent fixtures

Fixtures are matched ordinal-per-path: the first matching request gets
fixture index 0, the next gets 1, and so on — adequate for a fixed, short
tool-use conversation, and simple enough to review. Fixture files live in
``fixtures/`` (``anthropic-00.json``, ``gemini-00.json``, …), each with a
sibling ``*-request.json`` recorded-request file. Before serving ordinal
N, a per-path fingerprint of the incoming body is compared against the
recorded request N (D-03): a drifted request is answered 500 with a JSON
diagnostic naming the path, the ordinal, and the ``expected`` vs
``actual`` fingerprints — fail loudly, never serve the wrong fixture. A
request past the last fixture for its path is likewise answered 500
naming the exhausted path — fail loudly, never loop.

No CCF imports: this is a stand-in for a vendor's model API, and the
fabric is not involved. Binds 127.0.0.1 on port 0 and prints
``READY <port>`` once started (the suite's handshake pattern), including
when ``fixtures/`` is empty or absent — plan 03 authors the fixtures.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import anyio
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

_EXAMPLE_ROOT = Path(__file__).resolve().parent
FIXTURES = _EXAMPLE_ROOT / "fixtures"

#: Path suffix -> fixture filename prefix. The whole routing table.
SUFFIXES: tuple[tuple[str, str], ...] = (
    ("/v1/messages", "anthropic"),
    (":generateContent", "gemini"),
)


def _load_fixtures() -> dict[str, list[dict[str, object]]]:
    """Load every fixture pair at startup, ordered by filename ordinal.

    Each entry pairs the recorded response with its sibling
    ``*-request.json`` recorded request (``None`` when a sibling is
    absent — the fingerprint check is then skipped for that ordinal). A
    missing or empty directory is a valid state (zero fixtures loaded);
    startup still succeeds.
    """
    loaded: dict[str, list[dict[str, object]]] = {
        prefix: [] for _, prefix in SUFFIXES
    }
    if not FIXTURES.is_dir():
        return loaded
    for _, prefix in SUFFIXES:
        for path in sorted(FIXTURES.glob(f"{prefix}-*.json")):
            if path.name.endswith("-request.json"):
                continue
            request_path = path.with_name(
                path.name.replace(".json", "-request.json")
            )
            recorded_request = (
                json.loads(request_path.read_text(encoding="utf-8"))
                if request_path.is_file()
                else None
            )
            loaded[prefix].append(
                {
                    "response": json.loads(
                        path.read_text(encoding="utf-8")
                    ),
                    "request": recorded_request,
                }
            )
    return loaded


def fingerprint(prefix: str, body: dict[str, object]) -> dict[str, object]:
    """Reduce a request body to the drift-detecting shape for its path.

    Anthropic (``/v1/messages``): model, sorted tool names, message
    count. Gemini (``:generateContent``): sorted function-declaration
    names, content count — the Gemini body carries NO model field (it
    rides in the URL path).
    """
    if prefix == "anthropic":
        tools = body.get("tools") or []
        return {
            "model": body.get("model"),
            "tool_names": sorted(
                t.get("name") for t in tools if isinstance(t, dict)
            ),
            "message_count": len(body.get("messages") or []),
        }
    declarations = []
    tools = body.get("tools") or []
    if tools and isinstance(tools[0], dict):
        declarations = tools[0].get("functionDeclarations") or []
    return {
        "function_names": sorted(
            d.get("name") for d in declarations if isinstance(d, dict)
        ),
        "content_count": len(body.get("contents") or []),
    }


def _build_app() -> Starlette:
    fixtures = _load_fixtures()
    cursors: dict[str, int] = {prefix: 0 for _, prefix in SUFFIXES}

    async def replay(request: Request) -> Response:
        path = request.url.path
        for suffix, prefix in SUFFIXES:
            if not path.endswith(suffix):
                continue
            ordinal = cursors[prefix]
            recorded = fixtures[prefix]
            if ordinal >= len(recorded):
                # Fail loudly, never loop: a fixture shortfall means the
                # conversation drifted from the recorded one, and the review
                # event is regeneration (D-10), not silent reuse.
                return JSONResponse(
                    {
                        "error": "fixtures exhausted",
                        "path": path,
                        "served": ordinal,
                    },
                    status_code=500,
                )
            try:
                body = await request.json()
            except Exception:
                # T-13.2-09: a malformed body gets the same loud 500
                # diagnostic shape, never an unhandled exception.
                return JSONResponse(
                    {
                        "error": "request body is not valid JSON",
                        "path": path,
                        "ordinal": ordinal,
                    },
                    status_code=500,
                )
            recorded_request = recorded[ordinal]["request"]
            if recorded_request is not None:
                expected = fingerprint(prefix, recorded_request)
                actual = fingerprint(prefix, body)
                if expected != actual:
                    # D-03: drift fails loudly with a diagnostic naming
                    # both fingerprints — never serve the wrong fixture.
                    return JSONResponse(
                        {
                            "error": "request fingerprint mismatch",
                            "path": path,
                            "ordinal": ordinal,
                            "expected": expected,
                            "actual": actual,
                        },
                        status_code=500,
                    )
            cursors[prefix] = ordinal + 1
            return JSONResponse(recorded[ordinal]["response"])
        return JSONResponse(
            {"error": "no fixture route for path", "path": path},
            status_code=500,
        )

    return Starlette(
        routes=[
            Route("/{rest:path}", replay, methods=["POST"]),
        ]
    )


def main() -> None:
    """Bind loopback port 0, host the replay app, announce READY."""
    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(_build_app(), log_level="error")
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
