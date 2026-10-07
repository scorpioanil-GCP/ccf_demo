"""The MCP egress door — the SDK's standard door over the opened product.

[ADAPT] the ``door:`` section of ``ccf_config.yaml`` and the ``door:`` names in
``ccf_environment.yaml``. [MECHANISM] everything below — and there is almost
nothing below, which is the point (`D-IMPL-343`). The specimen this tree
succeeds wrote 150 lines of door and a ``door.yaml``; this launcher writes
none of either, and the declared gate that guarded the specimen's door module
(`CSC-G12`) has no subject here (`CSCC-G12`).

The identity this door asserts, the prose its tool advertises and the scope it
requires are the ``door:`` section's; the principal and role it serves under
are the deployment's declared ``default_perspective``; the entitlement policy,
the token source, the recorder and the ``build_egress_server`` call are the
SDK's standard door over the opened product's own registry and own recorder.

Two transports, chosen by the caller: ``serve`` (stdio) and ``loopback`` (an
ephemeral ``127.0.0.1`` port with REAL bearer authentication, reached through
``run.py --door``, which prints the ``READY {port}`` line a harness reads).
The bearer credential is read from the variable the environment document
names, or minted per boot when it is unset.
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
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", EXAMPLE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser  # noqa: E402
from ccf_runtime.mcp.tenancy import ambient_stdio_identity  # noqa: E402
from ccf_runtime.mcp.product_door import open_door  # noqa: E402

import produce  # noqa: E402


def serve() -> None:
    """Open the product, open its door, serve on stdio."""
    with tempfile.TemporaryDirectory(prefix="cp06c-door-") as scratch, produce.product(Path(scratch)) as opened:
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
    with tempfile.TemporaryDirectory(prefix="cp06c-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_door(opened).serve_loopback(announce=announce)


def main(argv: list[str] | None = None) -> None:
    """The stdio entry point. The loopback harness mode is ``run.py --door``."""
    argparse.ArgumentParser(
        description="The canonical credit-risk.collateral-coverage producer's MCP egress door (stdio)."
    ).parse_args(argv)
    serve()


if __name__ == "__main__":  # pragma: no cover
    main()
