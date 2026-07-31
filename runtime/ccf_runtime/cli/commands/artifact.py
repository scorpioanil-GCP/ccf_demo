"""The ``artifact`` noun — inspect/put against the injected store (D-IMPL-22).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec, load_document

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _inspect(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(method="GET", path=f"/artifact/{args.content_address}"),
    )


def _put(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(method="POST", path="/artifact", json=load_document(args.file)),
    )


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the artifact noun and its ruled verbs."""
    noun = subparsers.add_parser("artifact", help="artifact store access")
    verbs = noun.add_subparsers(dest="verb", required=True)

    inspect = verbs.add_parser("inspect", help="bytes at a content address")
    inspect.add_argument("content_address")
    inspect.set_defaults(build=_inspect)

    put = verbs.add_parser("put", help="store a put-request document file")
    put.add_argument("--file", required=True, help="put request file")
    put.set_defaults(build=_put)
