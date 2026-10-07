"""The MCP egress door: the governed spread, reached from another process.

[ADAPT] the ``door:`` section of ``ccf_config.yaml`` and the ``door:`` names in
``ccf_environment.yaml``. [MECHANISM] everything below — and there is almost
nothing below, which is the point (`D-IMPL-343`).

**This door re-implements no part of the governed path, and no part of the
door either.** The identity it asserts, the prose its tool advertises and the
scope it requires are the ``door:`` section's; the principal and role it
serves under are the deployment's declared ``default_perspective``, read from
the same document and never restated; the entitlement policy, the token
source, the recorder and the ``build_egress_server`` call are the SDK's
standard door over the opened product's own registry and own recorder. A
served and a refused decision therefore land in ONE store under ONE class,
and an address this door does not serve is refused by the product itself —
``class-mismatch``, as data, with a record — rather than by a hand-built
envelope in this file (the drift `CP03C-F-07` measured in a sibling cannot
happen here: nothing here constructs one).

Two transports, chosen by the caller:

* ``serve`` — stdio, for an MCP client that spawns this program. The issuer
  and resource-server addresses are read from the environment by the names
  ``ccf_environment.yaml`` declares (inert on stdio, required by the builder).
* ``loopback`` — bind an ephemeral ``127.0.0.1`` port, announce it once the
  server is up, and serve streamable HTTP with REAL bearer authentication at
  the address it bound. Reached through ``run.py --door``, which prints the
  ``READY {port}`` line a harness reads; this module writes to no terminal.

The bearer credential is read from the variable the environment document
names, or minted per boot when it is unset — the one way a parent that spawned
this process learns the credential without a side channel is to set it.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO_ROOT = EXAMPLE.parent.parent
# Spawned as bare `python serve.py`, none of pytest's or the Makefile's path
# setup applies; the door puts the SDK, the runtime and its own tree on the
# path itself so a subprocess boot cannot fail at import and surface through
# the handshake as "did not announce readiness".
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", EXAMPLE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser  # noqa: E402
from ccf_runtime.mcp.tenancy import ambient_stdio_identity  # noqa: E402
from ccf_runtime.mcp.product_door import open_door  # noqa: E402

import produce  # noqa: E402


def serve() -> None:
    """Open the product, open its door, serve on stdio."""
    with tempfile.TemporaryDirectory(prefix="cp03c-door-") as scratch, produce.product(Path(scratch)) as opened:
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
    """Open the product, open its door on an ephemeral loopback port, announce, serve."""
    with tempfile.TemporaryDirectory(prefix="cp03c-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_door(opened).serve_loopback(announce=announce)


def main(argv: list[str] | None = None) -> None:
    """The stdio entry point. The loopback harness mode is ``run.py --door``."""
    argparse.ArgumentParser(description="The canonical credit-risk.spread producer's MCP egress door (stdio).").parse_args(argv)
    serve()


if __name__ == "__main__":  # pragma: no cover
    main()
