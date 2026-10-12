# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The ``replay`` noun — query/resolve (D-IMPL-22/26).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _query(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET",
            path="/replay/decisions",
            params={"content_address": args.content_address},
        ),
    )


def _resolve(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET",
            path="/replay/resolutions",
            params={"uri": args.uri},
        ),
    )


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the replay noun and its ruled verbs."""
    noun = subparsers.add_parser("replay", help="decision replay records")
    verbs = noun.add_subparsers(dest="verb", required=True)

    query = verbs.add_parser("query", help="record at a content address")
    query.add_argument("--content-address", required=True)
    query.set_defaults(build=_query)

    resolve = verbs.add_parser("resolve", help="record at a versioned URI")
    resolve.add_argument("--uri", required=True)
    resolve.set_defaults(build=_resolve)
