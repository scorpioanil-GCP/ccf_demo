"""Child process: the MCP-backed reference artifact server (CLAUDE.md §7.4).

Run as ``python examples/07-artifact-store-mcp/mcp_store_child.py``. Binds an
ephemeral loopback port itself, hands the bound socket to uvicorn, and prints
``READY {port}`` on stdout once the server reports started — the readiness
handshake ``run.py`` blocks on. Nothing on the parent's path to that line
sleeps, and no port number is configured anywhere.

**The substrate is a real ``FileArtifactStore``, in this process.** That is
what makes the example's second run a cross-process proof rather than a mock
exercise: the bytes, the naming index, and the write-once behaviour are the
file store's, and everything the parent asserts about them has crossed a
socket to get there. The server owns the index; clients hold none.

**Every deployment value is read from ``artifacts/store_mcp.yaml``** — the
same artifact the parent builds its authenticated client from, so the token
the client presents and the token this server recognises cannot drift into
two values (CLAUDE.md §6.4: this module is an interpreter of the artifact,
never the holder of its values).
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

_EXAMPLE_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _EXAMPLE_ROOT.parents[2]

# The child is spawned as a bare `python <file>`, so it inherits none of the
# parent's sys.path work. Resolving the roots from __file__ keeps it runnable
# from anywhere, which the READY handshake depends on.
for _root in (_REPO_ROOT / "src", _REPO_ROOT / "runtime"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import yaml  # noqa: E402
from mcp.server.auth.settings import AuthSettings  # noqa: E402
from pydantic import AnyHttpUrl  # noqa: E402

from ccf.artifacts.file_store import FileArtifactStore  # noqa: E402
from ccf_runtime.mcp.artifact_server import build_artifact_server  # noqa: E402
from ccf_runtime.mcp.auth import (  # noqa: E402
    FileTokenSource,
    SourceBackedTokenVerifier,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

STORE_CONFIG = _EXAMPLE_ROOT / "artifacts" / "store_mcp.yaml"


def load_auth_values() -> dict[str, Any]:
    """The deployment's auth block, from the store-config artifact."""
    declared = yaml.safe_load(STORE_CONFIG.read_text(encoding="utf-8"))
    auth: dict[str, Any] = declared["declaration"]["auth"]
    return auth


def write_token_file(*, workspace: Path, auth: dict[str, Any]) -> Path:
    """Write the token file the verifier reads; return its path."""
    token_file = workspace / "tokens.json"
    token_file.write_text(
        json.dumps(
            {
                auth["token"]: {
                    "client_id": auth["client_id"],
                    "scopes": [auth["scope"]],
                }
            }
        ),
        encoding="utf-8",
    )
    return token_file


def build_server(*, workspace: Path) -> FastMCP:
    """Build the authenticated artifact server over a file substrate."""
    auth = load_auth_values()
    return build_artifact_server(
        server_name=auth["server_name"],
        store=FileArtifactStore(root=workspace / "artifacts"),
        token_verifier=SourceBackedTokenVerifier(
            source=FileTokenSource(
                path=write_token_file(workspace=workspace, auth=auth)
            )
        ),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl(auth["issuer_url"]),
            resource_server_url=AnyHttpUrl(auth["resource_server_url"]),
            required_scopes=[auth["scope"]],
        ),
    )


def main() -> None:
    """Bind an ephemeral loopback port, serve, and announce readiness."""
    import anyio
    import uvicorn

    with tempfile.TemporaryDirectory(prefix="ccf-example07-store-") as workspace:
        server_app = build_server(workspace=Path(workspace))

        bound = socket.socket()
        bound.bind(("127.0.0.1", 0))
        bound.listen(64)
        port = bound.getsockname()[1]

        server = uvicorn.Server(
            uvicorn.Config(server_app.streamable_http_app(), log_level="error")
        )

        async def serve() -> None:
            async def announce() -> None:
                # A 5 ms poll of *this process's own* server object — it
                # observes a real state flag rather than guessing a duration,
                # and the parent learns nothing until the flag flips.
                while not server.started:
                    await anyio.sleep(0.005)
                print(f"READY {port}", flush=True)

            async with anyio.create_task_group() as group:
                group.start_soon(announce)
                await server.serve(sockets=[bound])

        anyio.run(serve)


if __name__ == "__main__":
    main()
