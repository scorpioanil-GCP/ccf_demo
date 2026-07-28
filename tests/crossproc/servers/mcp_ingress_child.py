"""Child process: publish the banking fixture payloads as MCP Resources.

Run as ``python tests/crossproc/servers/mcp_ingress_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — the readiness
handshake the shared parent fixture blocks on (D-16). Nothing here or in the
parent's path to that line sleeps.

**This child is a *source*, not a fabric.** The egress child
(``mcp_egress_child.py``) assembles a Context Product and serves it; this one
plays the opposite role — an external system the fabric knows nothing about,
front-ended by MCP, which is what CLAUDE.md §7.1 calls "MCP as ingress (L1)".
So it boots no graph, registers no ontology and imports no assembly code. It
publishes opaque JSON in the *source's* vocabulary and lets the parent's L1
adapter be the thing that normalizes.

**Every value comes from ``tests/fixtures/banking/``** — the payloads from
``events.yaml``, the URI scheme, authority and media type from
``mcp_source.yaml``. Delete the fixtures and this file has nothing to publish
(CLAUDE.md §6.4 applied to fixture code).
"""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# Spawned as a bare `python <file>`, so it inherits none of pytest's sys.path
# work. Resolving the roots from __file__ is what makes the child runnable
# from any cwd — a property the shared fixture depends on.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import yaml  # noqa: E402

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

FIXTURES = _TESTS_ROOT / "fixtures" / "banking"


def load(name: str) -> Any:
    """Load one banking fixture document."""
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def resource_uri(source: Any, name: str) -> str:
    """The URI this server publishes ``name`` under.

    An address *within* the server, assembled from the fixture's scheme and
    authority. The network address is nobody's business but the parent's,
    which binds it at an ephemeral loopback port.
    """
    return (
        f"{source['resource_uri_scheme']}://"
        f"{source['resource_uri_authority']}/{name}"
    )


def published_payloads() -> tuple[Any, dict[str, Any]]:
    """The fixture source config, and the payloads keyed by resource name.

    One resource per fixture event, named by the event's id. The payload keys
    are the *source systems'* vocabulary — the fabric's own vocabulary does
    not appear here, which is exactly what makes the parent's assertion that
    L1 did not interpret meaningful.
    """
    source = load("mcp_source.yaml")
    events = load("events.yaml")
    payloads = {
        item["envelope_id"]: dict(item["payload"])
        for item in events["envelopes"]
    }
    return source, payloads


def build_server() -> FastMCP:
    """Publish one JSON resource per fixture payload."""
    from mcp.server.fastmcp import FastMCP

    source, payloads = published_payloads()
    # `stateless_http=True` for the same reason the egress server uses it: the
    # shared client opens one session per call by design, and session affinity
    # would turn that into a failure mode (see `ccf.mcp.client`).
    server = FastMCP(
        name=source["system_id"], stateless_http=True, json_response=True
    )

    for name, payload in payloads.items():
        server.add_resource(_json_resource(source, name, payload))
    return server


def _json_resource(source: Any, name: str, payload: Any) -> Any:
    """One concrete, read-only JSON resource.

    Concrete rather than templated: a source system publishes the records it
    holds, so ``list_resources`` enumerating them is the honest shape here —
    the opposite of the L6 egress surface, which is templated because the
    fabric will not assemble every product it *could* in order to list them.
    """
    from mcp.server.fastmcp.resources import FunctionResource
    from pydantic import AnyUrl

    return FunctionResource(
        uri=AnyUrl(resource_uri(source, name)),
        name=name,
        mime_type=source["mime_type"],
        fn=lambda payload=payload: json.dumps(payload),
    )


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import anyio
    import uvicorn

    server_app = build_server()

    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(server_app.streamable_http_app(), log_level="error")
    )

    async def serve() -> None:
        async def announce() -> None:
            # A 5 ms poll of *this process's own* server object — a real state
            # flag, not the parent-side sleep-and-hope D-16 prohibits. The
            # parent learns nothing until the flag flips.
            while not server.started:
                await anyio.sleep(0.005)
            print(f"READY {port}", flush=True)

        async with anyio.create_task_group() as group:
            group.start_soon(announce)
            await server.serve(sockets=[bound])

    anyio.run(serve)


if __name__ == "__main__":
    main()
