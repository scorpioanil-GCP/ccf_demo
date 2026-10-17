# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Three questions an auditor asks of retained decisions: ``decisions``, ``why``, ``replay`` (`D-IMPL-383`).

SDK-defined (CLAUDE.md §8.3 "replay queries"). A launcher that opens a product
over an ``evidence_root`` adds these verbs with :func:`register` and runs one
with :func:`run`. They read only the opened product's evidence index and store:

- ``decisions`` lists decisions by when they were made and what they involved
  (an identifier — a facility, a legal-entity identifier — not a company name;
  the index matches a decision's subject and its exact parameter values);
- ``why`` explains one decision from its own record
  (:func:`~ccf.replay.inspection.explain_decision`) — the refusal sentence
  written when it refused, the policy versions and request inputs in force and
  who supplied each, and the graph snapshot it read;
- ``replay`` re-executes it from the retained evidence
  (:meth:`~ccf.products.product.OpenedProduct.replay_decision`) and reports
  whether it reproduced.

They need no running door, and never ask a new question. Nothing here reads an
environment variable: WHICH evidence root is the launcher's business.

Exit status: ``0`` answered; ``2`` the request was malformed; ``3`` the
evidence is unavailable; ``4`` the replay did not reproduce.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Final, TextIO

from ccf.replay.engine import RefusalReplayOutcome, ReplayDivergence, ReplayOutcome
from ccf.replay.evidence import EvidenceEntry, ReplayEvidenceUnavailable
from ccf.replay.inspection import DecisionExplanation, explain_decision

if TYPE_CHECKING:
    from ccf.products.product import OpenedProduct

__ccf_mode__ = "algorithmic"

__all__ = ["VERBS", "register", "run"]

#: The verbs :func:`register` adds.
VERBS: Final[tuple[str, ...]] = ("decisions", "why", "replay")

ANSWERED = 0
MALFORMED = 2
UNAVAILABLE = 3
DIVERGED = 4
#: The shortest record-address prefix accepted in place of the full address.
_MIN_PREFIX: Final[int] = 8


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    """Add ``decisions``, ``why`` and ``replay`` to a launcher's subcommands."""
    listing = subparsers.add_parser(
        "decisions",
        help="list retained decisions",
        description="List retained decisions, oldest first. Times print in UTC and in this machine's local time.",
    )
    listing.add_argument("--involving", metavar="ID", help="a facility id or legal-entity identifier (not a name)")
    listing.add_argument("--since", metavar="WHEN", help="a date (from its start) or ISO date-time; local time unless an offset is given")
    listing.add_argument("--until", metavar="WHEN", help="a date (to its end) or ISO date-time; local time unless an offset is given")
    listing.add_argument("--json", action="store_true", help="print the index entries as JSON")

    why = subparsers.add_parser("why", help="explain one decision from its record")
    why.add_argument("decision", help="the decision's record address, or a unique prefix of at least 8 characters")
    why.add_argument("--json", action="store_true", help="print the explanation as JSON")

    replay = subparsers.add_parser("replay", help="replay one decision from its retained evidence and verify it")
    replay.add_argument("decision", help="the decision's record address, or a unique prefix of at least 8 characters")


def run(args: argparse.Namespace, opened: OpenedProduct, *, out: TextIO) -> int:
    """Run the verb ``args.command`` names against ``opened``; the exit status."""
    try:
        if args.command == "decisions":
            return _decisions(args, opened, out)
        address = _address(opened, args.decision)
        if args.command == "why":
            return _why(args, opened, address, out)
        return _replay(opened, address, out)
    except _Malformed as malformed:
        print(f"REFUSED: {malformed}", file=out)
        return MALFORMED
    except ReplayEvidenceUnavailable as unavailable:
        print(f"UNAVAILABLE: {unavailable}", file=out)
        return UNAVAILABLE


class _Malformed(ValueError):
    pass


def _decisions(args: argparse.Namespace, opened: OpenedProduct, out: TextIO) -> int:
    since = _instant(args.since, end_of_day=False)
    until = _instant(args.until, end_of_day=True)
    found = opened.evidence.decisions(since=since, until=until, involving=args.involving)
    if args.json:
        print(json.dumps([entry.model_dump(mode="json") for entry in found], indent=2), file=out)
        return ANSWERED
    scope = f" involving {args.involving}" if args.involving else ""
    print(f"{len(found)} decision(s){scope}", file=out)
    for entry in found:
        print(_listing_line(entry), file=out)
    pending = opened.evidence.incomplete()
    if pending:
        print(f"{len(pending)} decision(s) began and never finished; they cannot be replayed.", file=out)
    return ANSWERED


def _listing_line(entry: EvidenceEntry) -> str:
    outcome = "served " if entry.outcome == "served" else "REFUSED"
    reason = f"  reason: {entry.refusal_reason}" if entry.refusal_reason else ""
    return f"  {_when(entry.decided_at)}  {outcome}  {entry.subject}  {entry.record_address}{reason}"


def _why(args: argparse.Namespace, opened: OpenedProduct, address: str, out: TextIO) -> int:
    explanation = explain_decision(store=opened.artifact_store, evidence=opened.evidence, record_address=address)
    if args.json:
        print(explanation.model_dump_json(indent=2), file=out)
    else:
        for line in _explained(explanation):
            print(line, file=out)
    return ANSWERED


def _explained(e: DecisionExplanation) -> list[str]:
    lines = [f"Decision {e.record_address}"]
    if e.outcome == "served":
        lines.append("  Outcome:   SERVED")
    else:
        lines.append(f"  Outcome:   REFUSED ({e.refusal_reason})")
        lines.append(f"  Why:       {e.refusal_detail}")
    lines.append(f"  Question:  {e.product_class} {e.product_version} about {e.subject}, asked as of {_utc(e.asked_at)}")
    lines.append(f"  Asked by:  {e.principal_id} (role {e.role}); decided {_when(e.decided_at)}")
    lines.append("  Inputs:")
    for p in e.parameters:
        origin = "from the caller" if p.authority == "caller" else f"{p.authority}, from {p.source} version {_short(p.source_version)}"
        lines.append(f"    {p.name} = {json.dumps(p.value)}  ({origin})")
    if not e.parameters:
        lines.append("    (the record holds no resolved inputs)")
    lines.append("  Policies in force:")
    lines.extend(f"    {p.key}  version {_short(p.version)}" for p in e.policies)
    if e.read_graph:
        lines.append(
            f"  Data read: graph snapshot {_short(e.graph_snapshot_id)} as of {_utc(e.as_of)}:"
            f" {e.entities_touched} entities, {e.relationships_touched} relationships"
        )
        lines.append(f"  Steps:     {', '.join(e.operators)}")
    else:
        lines.append("  Data read: none — the decision was refused before any data was read")
    if e.debt_signal is not None:
        lines.append(f"  Context Debt: {Decimal(e.debt or 'NaN'):.3f} (signal {e.debt_signal}; exact value in --json)")
    return lines


def _replay(opened: OpenedProduct, address: str, out: TextIO) -> int:
    try:
        outcome = opened.replay_decision(address)
    except ReplayDivergence as diverged:
        print(f"DID NOT REPRODUCE: {diverged}", file=out)
        return DIVERGED
    if isinstance(outcome, ReplayOutcome):
        print(
            f"REPRODUCED: decision {address} was re-executed from its retained evidence and produced the"
            f" same product (fingerprint {outcome.product_content_address}).",
            file=out,
        )
    elif isinstance(outcome, RefusalReplayOutcome):
        print(
            f"REPRODUCED: decision {address} was reconstructed from its retained evidence and refuses"
            " exactly as recorded.",
            file=out,
        )
    else:
        erased = ", ".join(member.content_address for member in outcome.erased_content)
        print(f"ERASED: decision {address} met content removed by a recorded erasure: {erased}", file=out)
    return ANSWERED


def _address(opened: OpenedProduct, given: str) -> str:
    """``given``, or the one retained decision whose record address starts with it."""
    if len(given) == 64:
        return given
    if len(given) < _MIN_PREFIX:
        raise _Malformed(f"give the record address, or at least {_MIN_PREFIX} of its first characters")
    matches = [e.record_address for e in opened.evidence.decisions() if e.record_address.startswith(given.lower())]
    if not matches:
        raise ReplayEvidenceUnavailable(record_address=given, detail="no retained decision starts with that prefix")
    if len(matches) > 1:
        raise _Malformed(f"{len(matches)} decisions start with {given}; give more characters")
    return matches[0]


def _instant(given: str | None, *, end_of_day: bool) -> datetime | None:
    """A bound for ``decided_at``: a bare date covers the whole local day; a naive time is local."""
    if given is None:
        return None
    try:
        day = date.fromisoformat(given)
    except ValueError:
        try:
            moment = datetime.fromisoformat(given)
        except ValueError:
            raise _Malformed(f"{given!r} is not a date (2026-10-13) or an ISO date-time") from None
        return moment if moment.tzinfo is not None else moment.astimezone()
    if end_of_day:
        return datetime.combine(day + timedelta(days=1), time()).astimezone() - timedelta(microseconds=1)
    return datetime.combine(day, time()).astimezone()


def _when(moment: datetime) -> str:
    local = moment.astimezone()
    return f"{_utc(moment)} [{local:%Y-%m-%d %H:%M:%S %Z}]"


def _utc(moment: datetime | None) -> str:
    return "unknown" if moment is None else f"{moment.astimezone(UTC):%Y-%m-%d %H:%M:%S} UTC"


def _short(digest: str | None) -> str:
    return "none" if digest is None else digest[:12]
