"""The co-lender's MCP egress door: its position, reached from ANOTHER ORGANIZATION.

[ADAPT] the ``door:`` section of ``ccf_config.yaml`` and the ``door:`` names in
``ccf_environment.yaml``. [MECHANISM] everything below — and there is almost
nothing below, which is the point.

**This is the whole cross-organizational surface.** The consumer never reaches
the peer's Postgres or the peer's Fluree; it reaches this door, at an endpoint
whose name it declares and whose value is its operator's. The identity this
door asserts — ``cp-20-peer-co-lender-position-egress`` under tenant
``cp-20-peer-demo`` — is what the consumer's registration holds every answer
to (`D-IMPL-340`, `CLD-G02`, `CLD-G03`).

Two transports, chosen by the caller: ``serve`` (stdio) and ``loopback`` (an
ephemeral ``127.0.0.1`` port with REAL bearer authentication, reached through
``run.py --door``, which prints the ``READY {port}`` line a harness reads).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
PEER = HERE.parent
REPO_ROOT = PEER.parent.parent
# Spawned as a bare `python`, none of pytest's or the Makefile's path setup
# applies; the door puts the SDK, the runtime and its own tree on the path
# itself so a subprocess boot cannot fail at import.
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", PEER):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser  # noqa: E402
from ccf_runtime.mcp.tenancy import ambient_stdio_identity  # noqa: E402
from ccf_runtime.mcp.product_door import open_door  # noqa: E402

import produce  # noqa: E402


def serve() -> None:
    """Open the peer's product, open its door, serve on stdio."""
    with tempfile.TemporaryDirectory(prefix="cp20-peer-door-") as scratch, produce.product(Path(scratch)) as opened:
        door = open_door(opened)
        door.serve_stdio(
            identity=AuthenticatedUser(
                ambient_stdio_identity(
                    credential=door.credential,
                    principal_id=door.principal_id,
                    scope=door.scope,
                    tenant=door.tenant_id,
                )
            )
        )


def loopback(*, announce: Callable[[int], None]) -> None:
    """Open the peer's product, open its door on an ephemeral loopback port, announce, serve."""
    with tempfile.TemporaryDirectory(prefix="cp20-peer-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_door(opened).serve_loopback(announce=announce)


def main(argv: list[str] | None = None) -> None:
    """The stdio entry point. The loopback harness mode is ``run.py --door``."""
    argparse.ArgumentParser(
        description="The co-lender's MCP egress door (stdio)."
    ).parse_args(argv)
    serve()


if __name__ == "__main__":  # pragma: no cover
    main()
