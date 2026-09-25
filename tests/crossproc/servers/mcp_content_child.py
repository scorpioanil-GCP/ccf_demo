"""Child process: serve the covenant notes the parent's Π acquires at L4/L5.

Run as ``python tests/crossproc/servers/mcp_content_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — the readiness
handshake the shared fixture blocks on (D-16). No sleep anywhere in the
parent's path to that line.

**The notes exist only here.** Their text is read from
``tests/fixtures/banking/content_acquisition.yaml`` and served over MCP;
nothing in the parent's graph, envelopes, or ontology carries it. That is what
makes the parent's payload assertion a proof that the L4/L5 acquisition edge is
bound rather than an argument that a client library exists (D-21).

**This is a content source, not the fabric.** It serves opaque text under the
deployment's own ``acme-content://`` scheme — deliberately not
``ccf-product://`` (the L6 egress surface) and not ``ccf-artifact://`` (the
ArtifactStore). The three MCP roles are separate (D-03), and a child that
blurred them would let the parent's proof pass over the wrong edge.

Every domain value — tenants, scheme, selector shape, note text, server name —
comes from the fixture. Delete it and this file has nothing to serve.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

_TESTS_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _TESTS_ROOT.parent

# Spawned as a bare `python <file>`, so none of pytest's sys.path work applies
# and a relative PYTHONPATH would not survive a cwd change. Resolving from
# __file__ is what makes the child runnable from anywhere.
# The repo root too (last on the path): the shared test helpers import as
# `tests.composition`, which resolves only from there (D-IMPL-354).
for _root in (_REPO_ROOT, _REPO_ROOT / "src", _REPO_ROOT / "runtime", _TESTS_ROOT):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import yaml  # noqa: E402

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

FIXTURES = _TESTS_ROOT / "fixtures" / "banking"


def load_content_fixture() -> Any:
    """The one fixture both this child and the parent test read.

    Imported by the parent so the expected note and the served note cannot
    drift — two copies of a value, one serving and one asserting, agree right
    up until someone edits one of them.
    """
    return yaml.safe_load(
        (FIXTURES / "content_acquisition.yaml").read_text(encoding="utf-8")
    )


def build_server() -> FastMCP:
    """Register the templated covenant-note resource and return the server."""
    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415

    fixture = load_content_fixture()
    notes: dict[str, str] = dict(fixture["notes"])
    server = FastMCP(
        fixture["server_name"], stateless_http=True, json_response=True
    )

    @server.resource(fixture["resource_uri_template"])
    def covenant_note(tenant: str) -> str:
        """Return one tenant's note, or refuse.

        The refusal matters as much as the hit: a source that returned its one
        note for any tenant would make the parent's two-principal isolation
        assertion pass for the wrong reason.
        """
        if tenant not in notes:
            raise KeyError(tenant)
        return notes[tenant]

    return server


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import anyio  # noqa: PLC0415
    import uvicorn  # noqa: PLC0415

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
            # A 5 ms poll of *this process's own* server object — not the
            # parent-side sleep-and-hope D-16 prohibits: it observes a real
            # state flag, and the parent learns nothing until the flag flips.
            while not server.started:
                await anyio.sleep(0.005)
            print(f"READY {port}", flush=True)

        async with anyio.create_task_group() as group:
            group.start_soon(announce)
            await server.serve(sockets=[bound])

    anyio.run(serve)


if __name__ == "__main__":
    main()
