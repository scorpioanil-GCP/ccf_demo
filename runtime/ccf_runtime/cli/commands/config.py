"""The ``config`` noun — Control Plane introspection (D-IMPL-22).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _keys(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET",
            path="/config/keys",
            params={"class_id": args.class_id},
        ),
    )


def _versions(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET", path="/config/versions", params={"key": args.key}
        ),
    )


def _resolve(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="GET",
            path="/config/resolution",
            params={"key": args.key, "version": args.version},
        ),
    )


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the config noun and its ruled verbs."""
    noun = subparsers.add_parser("config", help="Control Plane configuration")
    verbs = noun.add_subparsers(dest="verb", required=True)

    keys = verbs.add_parser("keys", help="keys under an artifact class")
    keys.add_argument("--class-id", required=True)
    keys.set_defaults(build=_keys)

    versions = verbs.add_parser("versions", help="versions under a key")
    versions.add_argument("--key", required=True)
    versions.set_defaults(build=_versions)

    resolve = verbs.add_parser("resolve", help="resolve a pinned artifact")
    resolve.add_argument("--key", required=True)
    resolve.add_argument("--version", required=True)
    resolve.set_defaults(build=_resolve)
