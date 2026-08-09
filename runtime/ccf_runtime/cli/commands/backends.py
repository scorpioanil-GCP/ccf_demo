"""The ``backends`` noun — which adapter names this deployment accepts.

SDK-defined (D-IMPL-22). One verb, ``ccf backends list``, translating to a
single ``GET /backends``.

**What this answers, and what it replaced.** Plan 15.4-06 removed the
deployment manifest's six-name ``backend`` ``Literal``, and with it the
``enum`` an adopter's editor completed the field from. This is the
replacement, and it answers a better question: an enum could only ever say
what someone hard-coded, while the route reads the registry and says what is
**installed here**, third-party adapters included.

**No local generation path** (D-IMPL-79). The obvious implementation asks
the registry for its declared adapter names right here — it is in-process,
it holds no fabric handle, and it would work. It is not done, because the
CLI's whole posture is that every command travels the same routes any client
uses and holds no privileged path (T-07-27), and the first exception to that
is the one that makes the second easy. ``ccf schema export`` made this
argument and paid this price; the cost is one route module, and the
alternative cost is the invariant.

That posture is asserted against this file's *source*, not only against its
behaviour, so the registry's accessor is named nowhere above — described
instead, on the precedent ``ccf.deployment.manifest`` set when a comment
that spelled its forbidden token would have failed the grep it existed to
support.

The consequence worth naming: because this module returns a
:class:`~ccf_runtime.cli.commands.RequestSpec` and nothing else, the route's
fail-closed ``503`` on a packaging conflict — and the distribution name it
carries — arrives here over the same path any client sees, under ``--local``
too, since ``--local`` runs the app in-process rather than around it. Nothing
here re-derives that refusal, and if this command is ever changed to call the
registry directly, it owes the same typed refusal itself.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _list(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (RequestSpec(method="GET", path="/backends"),)


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the backends noun and its ruled verb."""
    noun = subparsers.add_parser(
        "backends", help="adapter names this deployment accepts"
    )
    verbs = noun.add_subparsers(dest="verb", required=True)

    listing = verbs.add_parser(
        "list", help="list the adapter names the deployment has installed"
    )
    listing.set_defaults(build=_list)
