"""The ``hitl`` noun — list/submit (D-IMPL-20/22); submit is the one verb.

``submit`` submits a complete typed action document from a file; an
unattributed action dies at the route boundary by contract
(audit-by-construction, CLAUDE.md §8.2). The verb is **submit-only by
ruling (D-IMPL-62)**: the printed output is the route's
``HitlActionReceipt`` — status ``submitted``, never ``resolved`` — with
the honest queue/disposition state; resolution is the owning primitive's
act at the composition root. The former ``decide`` alias was removed in
Phase 8 per D-15 (docs/DECISIONS.md): v0 ships one verb.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec, load_document

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _list(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET", path="/hitl/queue", params={"tenant": args.tenant}
        ),
    )


def _submit(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="POST", path="/hitl/actions", json=load_document(args.file)
        ),
    )


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the hitl noun and its ruled verbs."""
    noun = subparsers.add_parser("hitl", help="HITL queue and actions")
    verbs = noun.add_subparsers(dest="verb", required=True)

    pending = verbs.add_parser("list", help="pending events for a tenant")
    pending.add_argument("--tenant", required=True)
    pending.set_defaults(build=_list)

    submit = verbs.add_parser(
        "submit",
        help=(
            "submit a typed action document — submission only; resolution"
            " is the owning primitive's act"
        ),
    )
    submit.add_argument("--file", required=True, help="action document file")
    submit.set_defaults(build=_submit)
