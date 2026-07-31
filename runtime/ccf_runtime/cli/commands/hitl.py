"""The ``hitl`` noun — list/submit (D-IMPL-20/22); ``decide`` deprecated.

``submit`` submits a complete typed action document from a file; an
unattributed action dies at the route boundary by contract
(audit-by-construction, CLAUDE.md §8.2). The verb is **submit-only by
ruling (D-IMPL-62)**: the printed output is the route's
``HitlActionReceipt`` — status ``submitted``, never ``resolved`` — with
the honest queue/disposition state; resolution is the owning primitive's
act at the composition root. ``decide`` remains as a deprecated alias
per D-IMPL-66(d): it builds the identical request through the same
builder and emits a one-line deprecation notice on stderr.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse
import sys

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


def _decide(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    print(
        "warning: 'ccf hitl decide' is deprecated — use 'ccf hitl submit'"
        " (same request; the verb states the D-IMPL-62 submit-only"
        " semantics)",
        file=sys.stderr,
    )
    return _submit(args)


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

    decide = verbs.add_parser(
        "decide",
        help="(deprecated — use 'submit') submit a typed action document file",
    )
    decide.add_argument("--file", required=True, help="action document file")
    decide.set_defaults(build=_decide)
