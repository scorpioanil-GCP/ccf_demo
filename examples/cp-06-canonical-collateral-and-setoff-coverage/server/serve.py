# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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

**Where the door's scratch lives** (`D-IMPL-383`, Dave, 2026-10-15 20:27). With
``--evidence-dir`` the scratch is that folder — absolute, a directory, owned by
the account running the door, mode ``700`` and writable, or the door refuses
before it opens. The per-question graphs, the replay store and the evidence
index then outlive the door, so every decision it answered replays after a
restart (:meth:`~ccf.products.product.OpenedProduct.replay_decision`). Nothing
deletes them: retained evidence consumes disk and must be backed up. The bank
launcher (``packaging/bank-controlled/launch.sh``) always passes it. Without it
the scratch is a temporary directory, deleted when the door stops — the
development behavior, kept.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import stat
import sys
import tempfile
from collections.abc import Callable, Iterator
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


@contextlib.contextmanager
def door_scratch(evidence_dir: Path | None) -> Iterator[Path]:
    """The door's scratch: the private evidence folder, or a temporary directory.

    Raises:
        SystemExit: ``evidence_dir`` is not absolute, does not exist, is not a
            directory, is not owned by this account with mode ``700``, or is
            not writable — refused before anything is opened over it.
    """
    if evidence_dir is None:
        with tempfile.TemporaryDirectory(prefix="cp06c-door-") as scratch:
            yield Path(scratch)
        return

    def refuse(why: str) -> SystemExit:
        return SystemExit(f"REFUSED: the evidence folder {evidence_dir} {why} (D-IMPL-383)")

    if not evidence_dir.is_absolute():
        raise refuse("must be an absolute path")
    try:
        held = evidence_dir.stat()
    except FileNotFoundError:
        raise refuse("does not exist") from None
    if not stat.S_ISDIR(held.st_mode):
        raise refuse("is not a directory")
    if held.st_uid != os.geteuid() or stat.S_IMODE(held.st_mode) != 0o700:
        raise refuse("must be owned by the account running the door, with mode 700")
    if not os.access(evidence_dir, os.W_OK | os.X_OK):
        raise refuse("is not writable by the account running the door")
    yield evidence_dir


def serve(*, evidence_dir: Path | None = None) -> None:
    """Open the product, open its door, serve on stdio."""
    with door_scratch(evidence_dir) as scratch, produce.product(scratch) as opened:
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


def loopback(*, announce: Callable[[int], None], evidence_dir: Path | None = None) -> None:
    """Open the product, open its door on an ephemeral loopback port, announce, serve."""
    with door_scratch(evidence_dir) as scratch, produce.product(scratch) as opened:
        open_door(opened).serve_loopback(announce=announce)


def main(argv: list[str] | None = None) -> None:
    """The stdio entry point. The loopback harness mode is ``run.py --door``."""
    parser = argparse.ArgumentParser(
        description="The canonical credit-risk.collateral-coverage producer's MCP egress door (stdio)."
    )
    parser.add_argument(
        "--evidence-dir", type=Path, default=None,
        help="a private (mode 700) folder that keeps every decision's replay evidence across restarts",
    )
    serve(evidence_dir=parser.parse_args(argv).evidence_dir)


if __name__ == "__main__":  # pragma: no cover
    main()
