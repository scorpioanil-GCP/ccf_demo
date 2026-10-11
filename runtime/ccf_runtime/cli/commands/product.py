# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
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
