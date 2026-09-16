"""The MCP egress door: the governed corporate family, reached from another process.

[ADAPT] the ``door:`` section of ``ccf_config.yaml`` and the ``door:`` names in
``ccf_environment.yaml``. [MECHANISM] everything below — and there is almost
nothing below, which is the point (`D-IMPL-343`; CP-14 Gate 2 slice 2, the
second producer on the paved road).

**This door re-implements no part of the governed path, and no part of the
door either.** The identity it asserts, the prose its tool advertises and the
scope it requires are the ``door:`` section's; the principal and role it serves
under are the deployment's declared ``default_perspective``; the entitlement
policy, the token source, the recorder and the ``build_egress_server`` call are
the SDK's standard door over the opened product's own registry and own
recorder.

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
# Spawned as bare `python serve.py`, none of pytest's or the Makefile's path
# setup applies; the door puts the SDK, the runtime and its own tree on the
# path itself so a subprocess boot cannot fail at import.
for _path in (REPO_ROOT / "src", REPO_ROOT / "runtime", EXAMPLE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ccf_runtime.mcp.product_door import open_door  # noqa: E402

import produce  # noqa: E402


def serve() -> None:
    """Open the product, open its door, serve on stdio."""
    with tempfile.TemporaryDirectory(prefix="cp04c-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_door(opened).serve_stdio()


def loopback(*, announce: Callable[[int], None]) -> None:
    """Open the product, open its door on an ephemeral loopback port, announce, serve."""
    with tempfile.TemporaryDirectory(prefix="cp04c-door-") as scratch, produce.product(Path(scratch)) as opened:
        open_door(opened).serve_loopback(announce=announce)


def main(argv: list[str] | None = None) -> None:
    """The stdio entry point. The loopback harness mode is ``run.py --door``."""
    argparse.ArgumentParser(description="The canonical corporate-family producer's MCP egress door (stdio).").parse_args(argv)
    serve()


if __name__ == "__main__":  # pragma: no cover
    main()
