"""The ``skill`` noun — list/grant/revoke (D-IMPL-22; CLAUDE.md §6.2 ch. 2).

Grant and revoke route through the same governed ledger path any client's
would; the grant request is an artifact file, never inline fields. The
D-18 importer verb lives in :mod:`.skill_import` and registers here.

**The audit actor is not the caller's to name (SEC-012).** Both verbs
write to the grant ledger, whose entries are replay-relevant, and both
previously let whoever ran the command type the acting principal — a
``--actor`` flag on revoke, an ``actor:`` key in the grant request file.
Neither travels now: the principal is the identity the request's
credential authenticates (:mod:`ccf_runtime.cli.credential`), so the
ledger records who acted rather than who said they did.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import (
    CommandRefused,
    RequestSpec,
    load_document,
)

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _list(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (RequestSpec(method="GET", path="/skill/catalog"),)


def _grant(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    document = load_document(args.file)
    if "actor" in document:
        # Refused rather than dropped (SEC-012). Dropping it would leave
        # the operator believing they had named the ledger's principal,
        # which is the belief the finding is about.
        raise CommandRefused(
            f"{args.file!r} names an `actor`. The principal written to"
            " the grant ledger is the identity the request's credential"
            " authenticates, never a value the caller types — the ledger"
            " is replay-relevant and a typed actor makes it a record of"
            " what someone claimed. Remove the `actor` key."
        )
    return (
        RequestSpec(method="POST", path="/skill/grants", json=document),
    )


def _revoke(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    # No actor travels: the revoking principal is whoever the credential
    # on this request authenticates (SEC-012).
    return (
        RequestSpec(
            method="POST",
            path="/skill/revocations",
            json={"grant_hash": args.grant_hash},
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
    # There is deliberately no --actor: see `_revoke` (SEC-012).
    revoke.set_defaults(build=_revoke)

    from ccf_runtime.cli.commands import skill_import

    skill_import.register(verbs)
