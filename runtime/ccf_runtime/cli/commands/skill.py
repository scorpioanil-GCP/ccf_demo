"""The ``skill`` noun — list/grant/revoke (D-IMPL-22; CLAUDE.md §6.2 ch. 2).

Grant and revoke route through the same governed ledger path any client's
would; the grant request is an artifact file, never inline fields. The
D-18 importer verb lives in :mod:`.skill_import` and registers here.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec, load_document

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _list(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (RequestSpec(method="GET", path="/skill/catalog"),)


def _grant(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="POST", path="/skill/grants", json=load_document(args.file)
        ),
    )


def _revoke(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (
        RequestSpec(
            method="POST",
            path="/skill/revocations",
            json={"grant_hash": args.grant_hash, "actor": args.actor},
        ),
    )


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the skill noun and its ruled verbs."""
    noun = subparsers.add_parser("skill", help="skill catalog and grants")
    verbs = noun.add_subparsers(dest="verb", required=True)

    verbs.add_parser("list", help="list the skill catalog").set_defaults(
        build=_list
    )

    grant = verbs.add_parser(
        "grant", help="request a grant from a request artifact file"
    )
    grant.add_argument("--file", required=True, help="grant request file")
    grant.set_defaults(build=_grant)

    revoke = verbs.add_parser("revoke", help="revoke an effective grant")
    revoke.add_argument("--grant-hash", required=True)
    revoke.add_argument("--actor", required=True)
    revoke.set_defaults(build=_revoke)
