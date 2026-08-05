"""The ``schema`` noun — artifact-class JSON Schema export (D-IMPL-22).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _export(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    # No local generation path (D-IMPL-79): with --class-id this is one
    # GET against the same route any client uses, and without it the list
    # of class ids from the same router. The CLI acquires no privileged
    # path to the artifact classes, which is the whole point of routing a
    # purely-local-looking operation over HTTP.
    if args.class_id:
        return (RequestSpec(method="GET", path=f"/schema/{args.class_id}"),)
    return (RequestSpec(method="GET", path="/schema"),)


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the schema noun and its ruled verb."""
    noun = subparsers.add_parser("schema", help="artifact class JSON Schema")
    verbs = noun.add_subparsers(dest="verb", required=True)

    export = verbs.add_parser("export", help="export a class schema, or list")
    export.add_argument(
        "--class-id",
        help="artifact class id; omit to list the ids the SDK owns",
    )
    export.set_defaults(build=_export)
