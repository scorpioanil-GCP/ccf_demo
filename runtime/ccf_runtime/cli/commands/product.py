"""The ``product`` noun — retrieval only (D-IMPL-22; whitepaper §8.3 P3).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _get(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET",
            path=(
                f"/product/{args.tenant}/{args.product_class}/{args.version}"
            ),
        ),
    )


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the product noun and its one read verb."""
    noun = subparsers.add_parser("product", help="context product retrieval")
    verbs = noun.add_subparsers(dest="verb", required=True)

    get = verbs.add_parser("get", help="retrieve a gate-admitted product")
    get.add_argument("--tenant", required=True)
    get.add_argument("--product-class", required=True)
    get.add_argument("--version", required=True)
    get.set_defaults(build=_get)
