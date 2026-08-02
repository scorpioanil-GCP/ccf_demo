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
sibling ``*-request.json`` recorded-request file kept for review diffing;
this server never validates against them. A request past the last fixture
for its path is answered 500 naming the exhausted path — fail loudly,
never loop.

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
    """Load every response fixture at startup, ordered by filename ordinal.

    ``*-request.json`` siblings are recorded requests kept for review
    diffing and are deliberately skipped. A missing or empty directory is
    a valid state (zero fixtures loaded); startup still succeeds.
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
            loaded[prefix].append(
                json.loads(path.read_text(encoding="utf-8"))
            )
    return loaded


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
            cursors[prefix] = ordinal + 1
            return JSONResponse(recorded[ordinal])
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
