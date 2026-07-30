"""The ``agent`` noun — declare/list/show/versions (D-IMPL-22).

``declare`` takes an artifact file and nothing else: no inline definition
flag exists to parse (T-07-29; No-Hardcoding, CLAUDE.md §6.4).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec, load_document

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _declare(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="POST",
            path="/agent/declarations",
            json={"key": args.key, "definition": load_document(args.file)},
        ),
    )


def _list(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (RequestSpec(method="GET", path="/agent/declarations"),)


def _show(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET",
            path="/agent/declaration",
            params={"key": args.key, "version": args.version},
        ),
    )


def _versions(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET", path="/agent/versions", params={"key": args.key}
        ),
    )


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the agent noun and its ruled verbs."""
    noun = subparsers.add_parser("agent", help="agent declarations")
    verbs = noun.add_subparsers(dest="verb", required=True)

    declare = verbs.add_parser(
        "declare", help="register an agent definition artifact file"
    )
    declare.add_argument("--key", required=True, help="Control Plane key")
    declare.add_argument(
        "--file", required=True, help="agent definition artifact file"
    )
    declare.set_defaults(build=_declare)

    verbs.add_parser("list", help="list declared agent keys").set_defaults(
        build=_list
    )

    show = verbs.add_parser("show", help="resolve one pinned declaration")
    show.add_argument("--key", required=True)
    show.add_argument("--version", required=True)
    show.set_defaults(build=_show)

    versions = verbs.add_parser("versions", help="versions under a key")
    versions.add_argument("--key", required=True)
    versions.set_defaults(build=_versions)
