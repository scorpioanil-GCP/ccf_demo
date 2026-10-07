"""The MCP egress door over frozen cp-05 — the SDK's standard door, nothing else.

[ADAPT] ``artifacts/door.yaml`` and the ``door:`` names in ``ccf_environment
.yaml``. [MECHANISM] everything below. The frozen specimen's own
``server/serve.py`` wrote 150 lines of door before `D-IMPL-340` and asserted no
producer identity, which is why CP-14's exposure slot could not reach it
(`CP14-F-26`); this launcher opens the SDK's standard door over the adapter
beside it and asserts the identity ``door.yaml`` declares.

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
EXAMPLE = HERE.parent
REPO_ROOT = EXAMPLE.parent.parent
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", EXAMPLE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser  # noqa: E402
from ccf_runtime.mcp.tenancy import ambient_stdio_identity  # noqa: E402
from ccf_runtime.mcp.product_door import open_door  # noqa: E402

import adapter  # noqa: E402


def serve() -> None:
    """Open the adapter, open its door, serve on stdio."""
    with tempfile.TemporaryDirectory(prefix="cp05-door-") as scratch:
        producer = adapter.ExposureProducer(root=Path(scratch))
        door = open_door(producer, entitlement_source=producer.entitlement_source)
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
    """Open the adapter, open its door on an ephemeral loopback port, announce, serve."""
    with tempfile.TemporaryDirectory(prefix="cp05-door-") as scratch:
        producer = adapter.ExposureProducer(root=Path(scratch))
        open_door(producer, entitlement_source=producer.entitlement_source).serve_loopback(announce=announce)


def main(argv: list[str] | None = None) -> None:
    """The stdio entry point. The loopback harness mode is ``run.py --door``."""
    argparse.ArgumentParser(
        description="Frozen cp-05's credit-risk.exposure-rollup producer, reached through the SDK's standard MCP egress door (stdio)."
    ).parse_args(argv)
    serve()


if __name__ == "__main__":  # pragma: no cover
    main()
