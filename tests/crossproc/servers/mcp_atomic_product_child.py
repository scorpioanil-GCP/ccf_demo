"""Child process: an atomic Context Product, produced and served ELSEWHERE.

`D-IMPL-336` **Amendment 5 §5**, the provider-independence demonstration.
Dave: *"An atomic Context Product may already be registered elsewhere and
serve other use cases… The composite must not need the atomic provider's
assembler, source credentials, database handles, or boot context."*

This process is that elsewhere. It **boots its own fabric**, over **its own
SQLite database**, registers **its own product class**, runs **its own**
:class:`~ccf.products.resolver.GovernedResolver`, and serves the answer as
:func:`~ccf.products.door.door_answer` bytes over MCP.

**What the parent does not get, and that is the point.** No assembler, no
graph handle, no artifact store, no Control Plane registry, no connection
string — nothing but the logical `{server, resource}` names its skill binding
selects, and the typed bytes that come back. The composite in the parent
process declares the same ``requires`` and runs the same roll-up whether the
child is produced in-process or here.

Run as ``python tests/crossproc/servers/mcp_atomic_product_child.py``: binds an
ephemeral loopback port, hands the socket to uvicorn, and prints ``READY
{port}`` once the server reports started — the `D-16` handshake, no sleep in
the parent's path.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# Spawned as a bare `python <file>`, so none of pytest's sys.path work applies.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT, _REPO_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

#: The logical names the parent's skill binding selects. Values, declared in
#: one place and imported by the parent so the two cannot drift.
SERVER_NAME = "atomic-product-provider"
RESOURCE_URI = "acme-product://fixture.child-product/latest"


def build_server(workspace: Path) -> FastMCP:
    """Boot a fabric, produce the atomic product, and serve its door bytes."""
    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415

    from tests.products.provider_boot import serve_atomic_child  # noqa: PLC0415

    answer = serve_atomic_child(workspace)
    server = FastMCP(SERVER_NAME, stateless_http=True, json_response=True)

    @server.resource(RESOURCE_URI)
    def atomic_product() -> str:
        """The governed answer, on the wire, exactly as any door emits it.

        Produced once at boot and served verbatim. A Context Product is
        assembled per request in general; what this child demonstrates is
        PROVIDER INDEPENDENCE rather than per-request assembly, and rebuilding
        it on every read would add a moving part the demonstration does not
        need. The parent's assertions are about the composite, not about this
        provider's caching policy — which is exactly the point: the provider
        decides, and the composite cannot tell.
        """
        return answer

    return server


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import tempfile  # noqa: PLC0415

    import anyio  # noqa: PLC0415
    import uvicorn  # noqa: PLC0415

    workspace = Path(tempfile.mkdtemp(prefix="atomic-provider-"))
    server_app = build_server(workspace)

    bound = socket.socket()
    bound.bind(("127.0.0.1", 0))
    bound.listen(64)
    port = bound.getsockname()[1]

    server = uvicorn.Server(
        uvicorn.Config(server_app.streamable_http_app(), log_level="error")
    )

    async def serve() -> None:
        async def announce() -> None:
            while not server.started:
                await anyio.sleep(0.005)
            print(f"READY {port}", flush=True)

        async with anyio.create_task_group() as group:
            group.start_soon(announce)
            await server.serve(sockets=[bound])

    anyio.run(serve)


if __name__ == "__main__":
    main()
