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

**Where the door's evidence lives** (`D-IMPL-383`, Dave, 2026-10-16). The door's
scratch is always a temporary directory, deleted when the door stops. With
``CCF_REPLAY_EVIDENCE_ROOT`` set, that folder is the door's ``evidence_root`` —
absolute, a real directory and not a symlink, owned by the account running the
door, mode ``700`` and writable, or the door refuses before it opens. The
per-question graphs, the replay store and the evidence index then outlive the
door, so every decision it answered replays after a restart
(:meth:`~ccf.products.product.OpenedProduct.replay_decision`). Nothing deletes
them: retained evidence consumes disk and must be backed up. The bank launcher
(``packaging/bank-controlled/launch.sh``) always sets it. Unset, the evidence
goes with the temporary scratch — the development behavior, kept. This launcher
is the ONLY reader of the variable; the SDK takes the folder as an argument.

**Asking the retained evidence** (Dave, 2026-10-16). ``serve.py decisions``,
``serve.py why <decision>`` and ``serve.py replay <decision>`` open the same
evidence root and answer from it — which decisions were made, when and about
what; why one refused, and which policies and inputs were in force; whether it
reproduces — without serving and without asking a new question
(:mod:`ccf_runtime.cli.evidence`).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import stat
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
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
from ccf_runtime.cli import evidence as inspection  # noqa: E402

import produce  # noqa: E402

#: The one setting that keeps the door's replay evidence across restarts.
EVIDENCE_ROOT_VARIABLE = "CCF_REPLAY_EVIDENCE_ROOT"


@contextlib.contextmanager
def door_roots(environ: Mapping[str, str] | None = None) -> Iterator[tuple[Path, Path | None]]:
    """The door's ``(scratch, evidence_root)``: always a temporary scratch; the evidence root when configured.

    ``environ`` is where :data:`EVIDENCE_ROOT_VARIABLE` is read from; the
    process's environment when omitted. Unset, the evidence root is ``None``
    and the evidence lives and dies with the temporary scratch.

    Raises:
        SystemExit: the variable names a folder that is not absolute, is a
            symlink, does not exist, is not a directory, is not owned by this
            account with mode ``700``, or is not writable — refused before
            anything is opened over it.
    """
    configured = (os.environ if environ is None else environ).get(EVIDENCE_ROOT_VARIABLE)
    evidence_root = None if configured is None else _private_evidence_folder(Path(configured))
    with tempfile.TemporaryDirectory(prefix="cp06c-door-") as scratch:
        yield Path(scratch), evidence_root


def _private_evidence_folder(evidence_dir: Path) -> Path:
    """``evidence_dir``, once it is a private, writable, real directory; refused otherwise."""

    def refuse(why: str) -> SystemExit:
        return SystemExit(f"REFUSED: the evidence folder {evidence_dir} {why} (D-IMPL-383)")

    if not evidence_dir.is_absolute():
        raise refuse("must be an absolute path")
    if evidence_dir.is_symlink():
        raise refuse("is a symlink; the evidence must live in the folder named, not wherever a link points")
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
    return evidence_dir


def serve() -> None:
    """Open the product, open its door, serve on stdio."""
    with door_roots() as (scratch, evidence_root), produce.product(scratch, evidence_root=evidence_root) as opened:
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
    with door_roots() as (scratch, evidence_root), produce.product(scratch, evidence_root=evidence_root) as opened:
        open_door(opened).serve_loopback(announce=announce)


def inspect(args: argparse.Namespace) -> int:
    """Answer ``decisions``, ``why`` or ``replay`` from the retained evidence; asks no new question.

    Opens the product over the configured evidence root exactly as the door
    does — the same validation, a fresh temporary scratch — and hands it to the
    SDK's evidence verbs. Without :data:`EVIDENCE_ROOT_VARIABLE` nothing was
    retained, so there is nothing to inspect, and that is said rather than an
    empty answer given.
    """
    with door_roots() as (scratch, evidence_root):
        if evidence_root is None:
            raise SystemExit(
                f"REFUSED: {EVIDENCE_ROOT_VARIABLE} is not set, so no decision was retained to inspect (D-IMPL-383)"
            )
        with produce.product(scratch, evidence_root=evidence_root) as opened:
            return inspection.run(args, opened, out=sys.stdout)


def main(argv: list[str] | None = None) -> None:
    """The stdio entry point, and the evidence verbs. The loopback harness mode is ``run.py --door``."""
    parser = argparse.ArgumentParser(
        description="The canonical credit-risk.collateral-coverage producer's MCP egress door (stdio)."
        " With a command, answers from the retained evidence instead of serving.",
        epilog=f"Set {EVIDENCE_ROOT_VARIABLE} to a private (mode 700) folder to keep every decision's"
        " replay evidence across restarts (D-IMPL-383); the commands read that folder.",
    )
    inspection.register(parser.add_subparsers(dest="command", metavar="{decisions,why,replay}"))
    args = parser.parse_args(argv)
    if args.command is None:
        serve()
        return
    raise SystemExit(inspect(args))


if __name__ == "__main__":  # pragma: no cover
    main()
